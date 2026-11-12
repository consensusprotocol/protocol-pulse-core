#!/usr/bin/env python3
"""pipeline/oracle/providers.py — ONE provider interface for every model role (law L-x: no single model, Ultron first).

BACKENDS  every back-end this package may call: the ONLY place a vendor, an endpoint or a model name appears.
ROLES     role -> ordered chain of back-ends. The local model on Ultron comes first in every chain (L-x default); a
          role answers from the first back-end that is available and does not fail on the vendor side. Whether local
          meets the bar for a role is decided by the blind A/B on saved data (tools/backtest_oracle.py ab), re-run as
          the local model improves; the A/B file of record is named per role in DECIDED_BY.
call(role, system, user, schema, ledger, tag, avoid_vendors=())
          a back-end is skipped when: its key is missing; its vendor is in avoid_vendors (the generator and its blind
          judge are never the same vendor); it is the local GPU0 model and this process was not started inside the
          GPU0 lease (PP_GPU0_LEASE_HELD=1, set only by the integrator's lease wrapper: builders never touch GPU0);
          it is Heimdall and Heimdall usage is at >= 90 % of its credits (a NOTIFY file is written and the chain
          falls through: never a halt). A vendor-side failure (out of credit, rate limit, 5xx, network) moves to the
          next back-end; the answer records the back-end, vendor and model that produced it. No back-end answering
          raises AllBackendsFailed (the role records ORACLE_FAILED / JUDGE_FAILED: never NONE, never a pass).
Spend: frontier calls are priced into the run's ledger (llm.Ledger, the order's guard); Heimdall calls record tokens
and the gateway's own credit counter is checked before each call; local calls cost nothing.
Prices (USD per 1M tokens, 2026-11-12): gpt-6.1-sol $2 / $10, $4 / $15 above 272K prompt tokens (third-party trackers;
OpenAI's page unreachable); claude-fable-5-2 $8 / $40 (Claude API reference); grok-4.7 $2 / $6 (xAI
/v1/language-models: 20000 / 60000 per 100M tokens in cents).
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request

from pipeline.oracle import llm

HEIMDALL_BASE = "https://api-staging.heimdallm.com/api/v1"
BACKENDS = {
    "local-gemma3-27b": {"kind": "ollama", "vendor": "ultron", "model": "gemma3:27b", "host": "127.0.0.1:11434",
                         "num_ctx": 131072, "max_tokens": 16000, "gpu0": True},
    # max_chars_per_token: 1.25 x the largest ratio measured on this instrument's stored prompts (2026-11-12); a reply
    # that counted fewer prompt tokens than len(prompt) / that ratio read a cut prompt (ContextTooLong).
    "gpt-6.1-sol": {"kind": "openai", "vendor": "openai", "model": "gpt-6.1-sol", "key": "OPENAI_API_KEY",
                    "max_tokens": 100_000, "reasoning_effort": "high", "max_chars_per_token": 3.8,
                    "price": {"in": 2.0, "out": 10.0, "in_long": 4.0, "out_long": 15.0, "long_above": 272_000}},
    # max_tokens 96,000 for every call until 2026-11-12 03:31 ET, then 32,000: its largest reply in 293 calls was
    # 8,129 tokens (judge 4,931), and the spend guard reserves the full budget of every call in flight. A reply that
    # reaches the cap has no text and fails closed (JUDGE_FAILED / WITNESS_FAILED), never a pass.
    "claude-fable-5-2": {"kind": "anthropic", "vendor": "anthropic", "model": "claude-fable-5-2",
                         "key": "ANTHROPIC_API_KEY", "max_tokens": 32_000, "effort": "high", "max_chars_per_token": 2.6,
                         "price": {"in": 8.0, "out": 40.0}},
    "grok-4.7": {"kind": "openai", "vendor": "xai", "model": "grok-4.7", "key": "XAI_API_KEY_MEDLEY",
                 "base_url": "https://api.x.ai/v1", "max_tokens": 128_000, "no_tools": True, "max_chars_per_token": 3.7,
                 "price": {"in": 2.0, "out": 6.0}},
    # Heimdall bills per call (usage.cost); its largest call tonight cost 0.034 USD. A call reserves the larger of
    # reserve_usd and (estimated prompt + reply budget) tokens at reserve_usd_per_mtok while in flight, and is charged
    # that worst case if the gateway reports no cost.
    "heimdall-deepseek-v4.1-flash": {"kind": "openai", "vendor": "heimdall", "model": "deepseek/deepseek-v4.1-flash",
                                     "key": "HEIMDALL_API_KEY", "base_url": HEIMDALL_BASE, "max_tokens": 32_000,
                                     "reserve_usd": 0.25, "reserve_usd_per_mtok": 2.0, "max_chars_per_token": 4.4},
    "heimdall-glm-5.3-flash": {"kind": "openai", "vendor": "heimdall", "model": "z-ai/glm-5.3-flash",
                               "key": "HEIMDALL_API_KEY", "base_url": HEIMDALL_BASE, "max_tokens": 32_000,
                               "reserve_usd": 0.25, "reserve_usd_per_mtok": 2.0, "max_chars_per_token": 5.2},
    "heimdall-qwen3.8-27b": {"kind": "openai", "vendor": "heimdall", "model": "qwen/qwen3.8-27b",
                             "key": "HEIMDALL_API_KEY", "base_url": HEIMDALL_BASE, "max_tokens": 32_000,
                             "reserve_usd": 0.25, "reserve_usd_per_mtok": 2.0, "max_chars_per_token": 3.8},
}
ROLES = {
    "writer": ["local-gemma3-27b", "gpt-6.1-sol", "grok-4.7", "heimdall-deepseek-v4.1-flash"],
    "judge": ["local-gemma3-27b", "claude-fable-5-2", "grok-4.7", "heimdall-glm-5.3-flash"],
    "grouping": ["local-gemma3-27b", "claude-fable-5-2", "grok-4.7", "heimdall-glm-5.3-flash"],
    "witness": ["local-gemma3-27b", "claude-fable-5-2", "grok-4.7", "heimdall-glm-5.3-flash"],
}
DECIDED_BY = {r: "pending: the local A/B runs under the GPU0 lease (integrator); see BACKTEST_SUPPLY_REPORT.md section 9"
              for r in ROLES}
DECIDED_BY["judge"] = ("measured 2026-11-12 (integrator, GPU0 lease, REQUESTS R5): the local model agreed with the "
                       "reference on 10 of 25 items, passed 6 of 8 development swaps and 1 line-up the reference "
                       "failed, and failed 6 the reference passed (5 on a false altcoin reading): below the bar, so "
                       "the judge's default stays the frontier back-end (ab/local/AB_judge.json)")
DECIDED_BY["writer"] = ("measured by size, 2026-11-12: every saved universe's writer prompt is 115,595-219,172 tokens "
                        "and the local context holds 131,072 including the reply budget, so the context guard skips the "
                        "local writer on all 10 (a cut prompt is never sent); the frontier writes until a reduction "
                        "step exists. Quality A/B of the alternatives: BACKTEST_SUPPLY_REPORT.md section 9")
# L-x: the local back-end becomes a role's default only once its own A/B passed (flip with the file named in
# DECIDED_BY); until then a role's default chain skips it (an explicit chain, e.g. the A/B harness, still reaches it).
LOCAL_VALIDATED = {r: False for r in ROLES}
HEIMDALL_NOTIFY_AT = 0.90
NOTIFY_FILE = "HEIMDALL_SPEND_AT_90.txt"


class AllBackendsFailed(RuntimeError):
    def __init__(self, msg, tried):
        super().__init__(msg)
        self.tried = tried


DEFAULT_RESERVE_USD = 1.0       # a remote back-end without a price or reserve_usd reserves this per call
MAX_CHARS_PER_TOKEN = 6.0        # for a back-end with no measured ratio (its own max_chars_per_token wins)


class ContextTooLong(RuntimeError):
    """The prompt plus the reply budget does not fit this back-end's context window. A local server cuts such a prompt
    silently (the model then answers about part of the input), so it is never sent; the role moves to the next."""


def sent_system(b, system):
    """The system text this back-end is actually sent (a no_tools back-end also gets llm.NO_TOOLS): every size
    estimate, reservation and cut-prompt check counts this text, never a shorter one."""
    return system + (llm.NO_TOOLS if b.get("no_tools") else "")


def fits(name, system, user):
    """(ok, estimated prompt tokens) against the back-end's declared context (num_ctx); no declared context: ok."""
    b = BACKENDS[name]
    est = llm.est_tokens(sent_system(b, system), user)
    return (not b.get("num_ctx") or est + b["max_tokens"] <= b["num_ctx"]), est


class VendorDown(RuntimeError):
    """A vendor-side failure: the chain moves on (out of credit, rate limit, 5xx, network)."""


def _status(e):
    for s in (getattr(e, "status_code", None), getattr(getattr(e, "response", None), "status_code", None),
              getattr(e, "code", None)):                 # urllib's HTTPError carries .code
        if isinstance(s, int):
            return s
    return None


def _vendor_error(e):
    """A failure on the vendor's side (down, out of credit, rate-limited, 5xx, network): the role moves on."""
    status = _status(e)
    if status is not None:
        return status in (401, 402, 403, 408, 409, 429) or status >= 500
    if isinstance(e, (urllib.error.URLError, OSError)):  # local server down, connection reset, timeout
        return True
    return type(e).__name__ in ("APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError",
                                "RemoteDisconnected", "IncompleteRead", "VendorDown")


def _maybe_billed(e):
    """The request may have been processed (and billed) although no reply arrived: a timeout or a dropped
    connection, with no HTTP status (a status means the vendor refused it unbilled). The OpenAI SDK wraps every
    transport failure as APIConnectionError, a connection dropped mid-reply included: only one whose cause is a
    failure to connect at all proves nothing was sent."""
    if _status(e) is not None:
        return False
    if type(e).__name__ == "APIConnectionError":
        return type(e.__cause__).__name__ not in ("ConnectError", "ConnectTimeout")
    return isinstance(e, (TimeoutError, ConnectionError)) or type(e).__name__ in (
        "APITimeoutError", "ReadTimeout", "RemoteDisconnected", "IncompleteRead")


_heimdall_lock = threading.Lock()


def heimdall_usage():
    """(total_usage, total_credits) from the gateway's own counter."""
    req = urllib.request.Request(f"{HEIMDALL_BASE}/credits", headers={
        "Authorization": "Bearer " + llm.env_key("HEIMDALL_API_KEY"), "User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]
    return float(d["total_usage"]), float(d["total_credits"])


def available(name, avoid_vendors=(), notify_dir=None):
    """(ok, why) for one back-end in this process, without calling it."""
    b = BACKENDS[name]
    if b["vendor"] in avoid_vendors:
        return False, f"vendor {b['vendor']} produced what this role judges"
    if b.get("gpu0") and os.environ.get("PP_GPU0_LEASE_HELD") != "1":
        return False, "local GPU0 model: this process does not hold the GPU0 lease (integrator runs it)"
    if b.get("key"):
        try:
            llm.env_key(b["key"])
        except (KeyError, OSError):
            return False, f"{b['key']} not set"
    if b["vendor"] == "heimdall":
        try:
            with _heimdall_lock:
                used, credits = heimdall_usage()
        except Exception as e:
            return False, f"heimdall credit check failed: {type(e).__name__}"
        if not credits or credits <= 0:
            return False, "heimdall reports no credits"
        if used >= HEIMDALL_NOTIFY_AT * credits:
            if notify_dir:
                with open(os.path.join(notify_dir, NOTIFY_FILE), "w", encoding="utf-8") as f:
                    f.write(f"HEIMDALL SPEND AT 90%: {used:.2f} of {credits:.2f} USD at {time.ctime()}\n")
            return False, f"HEIMDALL SPEND AT 90% ({used:.2f} of {credits:.2f}): falling back"
    return True, "ok"


def _ollama(b, system, user, schema):
    body = {"model": b["model"], "stream": False, "format": schema,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "num_ctx": b["num_ctx"], "num_predict": b["max_tokens"]}}
    req = urllib.request.Request(f"http://{b['host']}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    raw = json.loads(urllib.request.urlopen(req, timeout=3600).read())
    if raw.get("prompt_eval_count", 0) + raw.get("eval_count", 0) >= b["num_ctx"]:
        raise ContextTooLong(f"prompt + reply reached the context limit {b['num_ctx']}: the input may have been cut")
    return (raw.get("message") or {}).get("content") or "", raw, {
        "tokens_in": raw.get("prompt_eval_count", 0), "tokens_out": raw.get("eval_count", 0),
        "seconds": round(time.time() - t0, 1), "usd": 0.0}


def _openai_compat(b, system, user, schema):
    from openai import OpenAI
    client = OpenAI(api_key=llm.env_key(b["key"]), base_url=b.get("base_url"), timeout=3600, max_retries=0)
    kw = {"response_format": {"type": "json_schema", "json_schema": {"name": "reply", "strict": True,
                                                                     "schema": schema}}}
    if b.get("reasoning_effort"):
        kw["reasoning_effort"] = b["reasoning_effort"]
    sysmsg = sent_system(b, system)
    lim ={"max_completion_tokens": b["max_tokens"]} if b["vendor"] == "openai" else {"max_tokens": b["max_tokens"]}
    t0 = time.time()
    resp = client.chat.completions.create(model=b["model"], messages=[{"role": "system", "content": sysmsg},
                                                                      {"role": "user", "content": user}], **lim, **kw)
    raw = resp.model_dump()
    u = raw.get("usage") or {}
    det = u.get("completion_tokens_details") or {}
    out = u.get("completion_tokens", 0) + ((det.get("reasoning_tokens") or 0) if b["vendor"] == "xai" else 0)
    text = (raw["choices"][0]["message"].get("content") or "") if raw.get("choices") else ""
    return text, raw, {"tokens_in": u.get("prompt_tokens", 0), "tokens_out": out, "seconds": round(time.time() - t0, 1),
                       "reasoning_tokens": det.get("reasoning_tokens"), "usd_reported": u.get("cost"),
                       "finish_reason": raw["choices"][0].get("finish_reason") if raw.get("choices") else None}


def _anthropic(b, system, user, schema):
    import anthropic
    client = anthropic.Anthropic(api_key=llm.env_key(b["key"]), timeout=3600, max_retries=0)
    t0 = time.time()
    with client.messages.stream(model=b["model"], max_tokens=b["max_tokens"], system=system,
                                output_config={"effort": b["effort"], "format": {"type": "json_schema", "schema": schema}},
                                messages=[{"role": "user", "content": user}]) as stream:
        msg = stream.get_final_message()
    raw = msg.model_dump()
    u = raw.get("usage") or {}
    text = "".join(x.get("text", "") for x in raw.get("content", []) if x.get("type") == "text") \
        if raw.get("stop_reason") == "end_turn" else ""
    return text, raw, {"tokens_in": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                       + (u.get("cache_read_input_tokens") or 0), "tokens_out": u.get("output_tokens") or 0,
                       "seconds": round(time.time() - t0, 1), "stop_reason": raw.get("stop_reason")}


_KIND = {"ollama": _ollama, "openai": _openai_compat, "anthropic": _anthropic}


_CONTEXT_WORDS = ("context length", "context_length", "maximum context", "context window", "too long", "too many tokens",
                  "exceeds the context", "prompt is too long", "input is too long")


def _context_error(e):
    status = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
    return status in (400, 413) and any(w in str(e).lower() for w in _CONTEXT_WORDS)


def call_backend(name, system, user, schema, ledger, tag, notify_dir=None):
    """One call on one named back-end: (text, raw, usage_row incl. backend / vendor / model / usd). Never sent: a
    prompt that does not fit the declared context, a Heimdall call past its 90 % tripwire (checked on EVERY call), any
    call the spend guard refuses (priced: its worst case is reserved until it settles; unpriced: refused once the cap
    is reached). A context-length refusal, or a remote reply that counted far fewer prompt tokens than the prompt can
    hold (a gateway that cut it), is ContextTooLong. The GPU0 lease is checked here too, for every caller."""
    b = BACKENDS[name]
    if b.get("gpu0"):                               # never only in call()'s chain walk: a direct caller is gated too
        ok, why = available(name)
        if not ok:
            raise VendorDown(why)
    ok, est = fits(name, system, user)
    if not ok:
        raise ContextTooLong(f"{name}: prompt ~{est} tokens + {b['max_tokens']} reply > context {b['num_ctx']}")
    if b["vendor"] == "heimdall":
        ok, why = available(name, notify_dir=notify_dir)
        if not ok:
            raise VendorDown(why)
    price, remote = b.get("price"), b["vendor"] != "ultron"
    sysmsg = sent_system(b, system)                 # what is actually sent: the estimate and the cut check count it
    est = llm.est_tokens(sysmsg, user)
    worst = (llm.cost(price, est, b["max_tokens"]) if price
             else max(b.get("reserve_usd", DEFAULT_RESERVE_USD),
                      round((est + b["max_tokens"]) / 1e6 * b.get("reserve_usd_per_mtok", 0.0), 4)) if remote else 0.0)
    token = ledger.reserve(worst, name) if remote else None       # every remote call holds its worst case
    try:
        text, raw, row = _KIND[b["kind"]](b, system, user, schema)
    except BaseException as e:
        if not isinstance(e, Exception):                          # Ctrl-C / exit mid-call: maybe billed, settle it
            if token is not None:
                ledger.settle(token, tag=tag, backend=name, vendor=b["vendor"], model=b["model"], usd=worst,
                              usd_source="interrupted mid-call: worst case", tokens_in=None, tokens_out=None)
            raise
        if token is not None:
            if _maybe_billed(e):                                  # charged at worst case, never silently free
                ledger.settle(token, tag=tag, backend=name, vendor=b["vendor"], model=b["model"], usd=worst,
                              usd_source="failed after sending: worst case", tokens_in=None, tokens_out=None,
                              error=llm.redact(f"{type(e).__name__}: {e}")[:200])
            else:
                ledger.release(token)
        if _context_error(e):
            raise ContextTooLong(f"{name}: the vendor refused the prompt as too long ({llm.redact(e)[:200]})") from e
        raise
    reported = row.pop("usd_reported", None)
    if price:                                       # frontier: the config's price table
        row.update(usd=llm.cost(price, row["tokens_in"], row["tokens_out"]), usd_source="price table")
    elif reported is not None:                      # a gateway that bills per call says what it charged
        row.update(usd=round(float(reported), 6), usd_source="gateway-reported")
    elif remote:                                    # a gateway that said nothing: its worst case, never free
        row.update(usd=worst, usd_source="unreported: worst case")
    else:
        row.update(usd=0.0, usd_source="local")
    row.update(tag=tag, backend=name, vendor=b["vendor"], model=(raw.get("model") if isinstance(raw, dict) else None)
               or b["model"])
    ledger.settle(token, **row)
    chars = len(sysmsg) + len(user)
    if remote and not row.get("tokens_in"):         # no count, no proof the whole prompt was read (fail closed)
        raise ContextTooLong(f"{name}: the reply carries no prompt-token count; a cut prompt cannot be ruled out")
    ceiling = b.get("max_chars_per_token", MAX_CHARS_PER_TOKEN)
    if remote and row["tokens_in"] < chars / ceiling:
        raise ContextTooLong(f"{name}: the reply counted {row['tokens_in']} prompt tokens for {chars} characters "
                             f"(fewer than 1 per {ceiling:g}): the input was cut")
    return text, raw, row


def call(role, system, user, schema, ledger, tag, avoid_vendors=(), chain=None, notify_dir=None):
    """The role's answer from the first available back-end that does not fail on the vendor side."""
    tried = []
    for name in chain or ROLES[role]:
        ok, why = available(name, avoid_vendors, notify_dir)
        if not ok:
            tried.append({"backend": name, "skipped": why})
            continue
        if chain is None and BACKENDS[name].get("gpu0") and not LOCAL_VALIDATED.get(role):
            tried.append({"backend": name, "skipped": f"local back-end not yet validated for the {role} role "
                                                      f"(its A/B: {DECIDED_BY[role][:80]})"})
            continue
        try:
            text, raw, row = call_backend(name, system, user, schema, ledger, f"{role} {tag}", notify_dir)
        except llm.SpendStop:
            raise                                          # the order's guard: never fall through it
        except ContextTooLong as e:                        # this input cannot go to this back-end whole
            tried.append({"backend": name, "skipped": llm.redact(e)[:300]})
            continue
        except Exception as e:
            tried.append({"backend": name, "error": llm.redact(f"{type(e).__name__}: {e}")[:300]})
            if _vendor_error(e):
                continue                                   # out of credit / rate limit / 5xx / network: next one
            raise
        row["tried"] = tried
        return text, raw, row
    raise AllBackendsFailed(f"{role}: no back-end answered ({tried})", tried)


def paired_calls(writer_chain=None, judge_chain=None, notify_dir=None, judge_role="judge"):
    """(writer_call, judge_call): the judge avoids the vendor that ACTUALLY answered the writer's last call (after
    any failover), not the vendor the writer chain starts with."""
    used = {}

    def writer(system, user, schema, ledger, tag):
        text, raw, row = call("writer", system, user, schema, ledger, tag, chain=writer_chain, notify_dir=notify_dir)
        used["vendor"] = row["vendor"]
        return text, raw, row

    def judge(system, user, schema, ledger, tag):
        if "vendor" not in used:                     # nothing written yet: there is nothing to judge
            raise RuntimeError("judge called before any writer reply")
        return call(judge_role, system, user, schema, ledger, tag, avoid_vendors={used["vendor"]},
                    chain=judge_chain, notify_dir=notify_dir)
    return writer, judge


def role_call(role, avoid_vendors=(), chain=None, notify_dir=None):
    """A call(system, user, schema, ledger, tag) bound to one role, the shape run.py / witness.py take."""
    def fn(system, user, schema, ledger, tag):
        return call(role, system, user, schema, ledger, tag, avoid_vendors, chain, notify_dir)
    return fn


def vendor_of_model(model):
    """The vendor of a model name recorded in an artefact (artefacts written before L-x carry only the model)."""
    return next((b["vendor"] for b in BACKENDS.values() if b["model"] == model), None)
