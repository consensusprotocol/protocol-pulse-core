"""A BLIND frontier baseline for the moments-first exam: one frontier model judges each case from the law text and
the blinded case only (no expected verdict, no class, no provenance). It is an adapter in the exam's protocol
(tests/adversarial/moments_exam.py), so the same runner and tables apply:

    PP_BASELINE_VENDOR=anthropic|openai PP_MOMENTS_ALLOW_NETWORK=1 \
      python3 tests/adversarial/moments_exam.py --gates baselines.frontier_blind --jobs 6 --report <out.json>

It measures how hard the exam is before the real gates sit it; it is not a gate. Keys are read by name from the
project's secrets file inside this process and never printed. Every call's cost (from the reply's usage) is
appended to SPEND.jsonl next to this file; a call whose estimated cost would take the cumulative spend over
$PP_BASELINE_BUDGET_USD (default 15) is refused (an ERROR row, reported), so the guard holds across both vendors."""
import contextlib
import fcntl
import json
import os
import re
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ENV_FILE = "/home/ultron/protocol_pulse/.env"
SPEND = os.path.join(HERE, "SPEND.jsonl")          # pinned: one ledger, so no run can start a budget of its own
BUDGET = float(os.environ.get("PP_BASELINE_BUDGET_USD", "15"))
VENDOR = os.environ.get("PP_BASELINE_VENDOR", "anthropic")
MODELS = {   # prices USD per 1M tokens (in, out): claude-api skill models.md (Opus 5.5 $4 / $20);
             # gpt-6.1-sol as pp-selectid's model_providers.json declares it ($15 / $120)
    "anthropic": {"model": "claude-opus-5-5", "price": (4.0, 20.0), "effort": "medium", "max_out": 8000},
    "openai": {"model": "gpt-6.1-sol", "price": (15.0, 120.0), "effort": "low", "max_out": 4000},
    # second vendor after OpenAI's credits ran out mid-run (04:2x ET): Google's current Pro model as this key lists
    # it; priced above its published preview rate ($2 / $12) so the guard errs high
    "google": {"model": "gemini-3.1-pro-preview", "price": (2.5, 15.0), "effort": "default", "max_out": 8000},
}
PER_CASE_USD = {"anthropic": 0.016, "openai": 0.035, "google": 0.012}   # measured averages of the earlier runs


def preflight(counts):
    """Called by moments_exam before the run: refuse a run whose expected cost would take the ledger over the
    budget, rather than truncating it into ERROR rows."""
    n = sum(counts.values())
    need = n * PER_CASE_USD.get(VENDOR, 0.05) * 1.25
    spent = _spent()
    if spent + need > BUDGET:
        raise BudgetExhausted(f"{n} cases need about ${need:.2f}; spent ${spent:.2f} of ${BUDGET:.2f}")
IDENTITY = {"vendor": VENDOR, **{k: v for k, v in MODELS.get(VENDOR, {}).items() if k != "max_out"}}   # in the report
THREAD_SAFE = True             # moments_exam --jobs: the SDK clients are thread-safe; spend is guarded by _locked()
_TLOCK = threading.Lock()
_CLIENT = {}


@contextlib.contextmanager
def _locked():
    """Thread lock + an exclusive lock on SPEND.jsonl.lock: two vendor runs in parallel share one budget. Always
    taken in this order (thread lock, then file lock) and never nested, so the two cannot deadlock."""
    with _TLOCK, open(SPEND + ".lock", "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


class BudgetExhausted(Exception):
    pass


def _key(name):
    with open(ENV_FILE) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, v = s.partition("=")
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    raise KeyError(f"{name} not set in the project's secrets file")


def _client():
    with _TLOCK:
        if VENDOR not in _CLIENT:
            if VENDOR == "anthropic":
                import anthropic
                _CLIENT[VENDOR] = anthropic.Anthropic(api_key=_key("ANTHROPIC_API_KEY"), max_retries=3)
            elif VENDOR == "openai":
                import openai
                _CLIENT[VENDOR] = openai.OpenAI(api_key=_key("OPENAI_API_KEY"), max_retries=3)
            elif VENDOR == "google":
                from google import genai
                _CLIENT[VENDOR] = genai.Client(api_key=_key("GEMINI_API_KEY_MEDLEY"))
            else:
                raise ValueError(f"PP_BASELINE_VENDOR={VENDOR!r}")
        return _CLIENT[VENDOR]


def _spent():
    if not os.path.exists(SPEND):
        return 0.0
    with open(SPEND) as f:
        return sum(json.loads(line)["usd"] for line in f if line.strip())


def _call(system, user, case_id):
    cfg = MODELS[VENDOR]
    p_in, p_out = cfg["price"]
    # reserve the worst case (input at 2.5 characters a token, the full max_out) so the guard holds even when every
    # call in flight runs to its limit; the settle line returns the difference
    est = (len(system) + len(user)) / 2.5 * p_in / 1e6 + cfg["max_out"] * p_out / 1e6
    with _locked():                                   # reserve-then-settle keeps concurrent calls under the budget
        spent = _spent()
        if spent + est > BUDGET:
            raise BudgetExhausted(f"spent ${spent:.2f} + estimate ${est:.2f} > budget ${BUDGET:.2f}")
        with open(SPEND, "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "vendor": VENDOR, "model": cfg["model"],
                                "case": case_id, "kind": "reserve", "usd": round(est, 6)}) + "\n")
    t0 = time.time()
    try:
        if VENDOR == "anthropic":
            msg = _client().messages.create(model=cfg["model"], max_tokens=cfg["max_out"], system=system,
                                            messages=[{"role": "user", "content": user}],
                                            extra_body={"output_config": {"effort": cfg["effort"]}})
            if msg.stop_reason == "refusal":
                raise RuntimeError("model refused")
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            tin, tout, model = msg.usage.input_tokens, msg.usage.output_tokens, msg.model
        elif VENDOR == "openai":
            resp = _client().responses.create(model=cfg["model"], instructions=system, input=user,
                                              reasoning={"effort": cfg["effort"]},
                                              max_output_tokens=cfg["max_out"])
            text = resp.output_text or ""
            tin, tout, model = resp.usage.input_tokens, resp.usage.output_tokens, resp.model
        else:
            from google.genai import types
            resp = _client().models.generate_content(
                model=cfg["model"], contents=user,
                config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=cfg["max_out"]))
            text = resp.text or ""
            u = resp.usage_metadata
            tin = u.prompt_token_count or 0
            tout = (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
            model = cfg["model"]
        usd = tin * p_in / 1e6 + tout * p_out / 1e6
    except BaseException as e:
        # a call the vendor refused before processing it (quota, auth, bad request: HTTP 4xx other than 408/409) is
        # not billed and releases its reservation; anything else (a timeout, a dropped stream) keeps it
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        refused = isinstance(status, int) and 400 <= status < 500 and status not in (408, 409)
        usd, tin, tout, model, text = (0.0 if refused else est), None, None, cfg["model"], None
        raise
    finally:
        with _locked():
            with open(SPEND, "a") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "vendor": VENDOR, "model": model,
                                    "case": case_id, "kind": "settle", "in": tin, "out": tout,
                                    "seconds": round(time.time() - t0, 2),
                                    "usd": round(usd - est, 6)}) + "\n")   # settle = actual - reserved
    return text


def _verdict(text, allowed):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError(f"no JSON object in the reply: {(text or '')[:200]!r}")
    obj = json.loads(m.group(0))
    if obj.get("verdict") not in allowed:
        raise ValueError(f"verdict {obj.get('verdict')!r} not in {allowed}")
    why = str(obj.get("why", ""))
    if obj.get("bad_line") is not None:
        why = f"[bad_line {obj['bad_line']}] {why}"
    return {"verdict": obj["verdict"], "why": why}


def _partners():
    with open(os.path.join(REPO, "config", "partner_channels.json")) as f:
        return [c["name"] for c in json.load(f)["channels"]]


COMMON = ("You review material for 'Pulse Check', a short Bitcoin news video assembled from verbatim clips of other "
          "people's videos plus a short voice-over (VO), one title and one caption. You judge ONE case. Only state "
          "what you can verify from the material given. If you are uncertain, answer \"uncertain\" (it counts as a "
          "rejection). Reply with one JSON object and nothing else.")

CI_RULES = """CONTEXT INTEGRITY. The clip marked MOMENT is shown inside its source window (about 90 s before and 60 s after, with
caption speaker labels where the source has them). PASS only if ALL of these hold:
1. It is the speaker's own sincere assertion: not a quotation or paraphrase of someone else, not the other side's
   argument voiced for the sake of argument, not sarcasm or a joke, not a hypothetical or worked example, not a tweet,
   post or ad read aloud, not a question, not an interviewer's paraphrase presented as the guest's words.
2. Every referent ('he', 'it', 'this', 'that', 'today', 'right now') is resolved inside the clip, or by the package
   correctly.
3. No condition outside the clip governs it, and nothing in the window retracts, corrects or reverses it.
4. What a viewer of the finished package (title, caption, VO, clip order) would take away has the same polarity and
   no stronger certainty than what the speaker meant in context, with the right speaker, and a time word ('today',
   'right now') is not presented as current when the show date is later than the publish date.
5. The package implies no relation (reply, agreement, rebuttal, dialogue) between speakers of different videos,
   and the title adds no thesis that no clip states.
Reply: {"verdict": "pass" | "fail" | "uncertain", "why": "<one or two sentences>"}"""

VO_RULES = """VO FIDELITY. Each line (VO intro / bridge / signoff, title, caption) must be supported by the clips it cites:
same stance; no stronger certainty (could / might -> will); every number exactly as spoken (no rounding, no swapping);
every person named appears in the clips; no agreement, reply or relation claimed between speakers of different
videos; no fact absent from the clips, even a true one; none of the framing verbs destroys / slams / exposes /
admits / confirms / caught unless the source itself uses the word; no second-person financial imperative. Lines built
only from the manifest (channel names, the show name, the date, 'two voices', ordering words) are allowed.
Reply: {"verdict": "pass" | "fail" | "uncertain", "bad_line": <index of the first failing line or null>,
"why": "<one or two sentences>"}  (pass only if every line passes)"""


def EX_RULES():
    return f"""HARD EXCLUSIONS (applied before any scoring; the law's own words). Never auto-selected:
- accusations of crime / fraud / insolvency / dishonesty against a named person or company;
- one partner attacking another (partners: {', '.join(_partners())});
- buy / sell / leverage imperatives and guaranteed-return claims;
- single-source 'breaking' factual claims;
- ad reads and sponsor segments;
- third-party media played inside a partner's video;
- altcoin content (the show is Bitcoin-only).
Everything else is kept.
Reply: {{"verdict": "keep" | "exclude" | "uncertain", "why": "<one or two sentences>"}}"""


def _sent(s, mark=""):
    who = s.get("speaker") or (f"turn {s['turn']}" if s.get("turn") is not None else "")
    return f"{mark}[{s['start']:.1f}-{s['end']:.1f}{' ' + who if who else ''}] {s['text']}"


def _source(src):
    return (f"SOURCE: channel {src.get('channel')!r}; title {src.get('title')!r}; published {src.get('published_at')}"
            + (f"; description: {src['description'][:300]!r}" if src.get("description") else ""))


def context_integrity(case):
    w, p = case["window"], case["package"]
    a, b = w["selected"]
    win = "\n".join(_sent(s, "MOMENT>> " if a <= s["n"] <= b else "") for s in w["sentences"])
    segs = []
    for i, s in enumerate(p["segments"]):
        segs.append(f"CLIP {s['label']} ({s['role']}; {s['channel']}; published {s['published_at']}): {s['text']}")
        if i < len(p["vo"]["bridges"]) and i < len(p["segments"]) - 1:
            segs.append(f"VO bridge: {p['vo']['bridges'][i]}")
    user = (f"{_source(case['source'])}\nWINDOW ({w['timing']} timing):\n{win}\n\nPACKAGE (show date {p.get('date')}):\n"
            f"TITLE: {p['title']}\nCAPTION: {p['caption']}\nVO intro: {p['vo']['intro']}\n" + "\n".join(segs)
            + f"\nVO signoff: {p['vo']['signoff']}")
    return _verdict(_call(f"{COMMON}\n\n{CI_RULES}", user, case["id"]), ("pass", "fail", "uncertain"))


def vo_fidelity(case):
    segs = "\n".join(f"CLIP {s['label']} ({s['channel']}; published {s['published_at']}): "
                     + " ".join(x["text"] for x in s["sentences"]) for s in case["segments"])
    lines = "\n".join(f"{i}. [{ln['slot']}; cites {', '.join(ln['cites']) or '-'}] {ln['text']}"
                      for i, ln in enumerate(case["lines"]))
    m = case["manifest"]
    user = f"MANIFEST: show {m['show']!r}; date {m['date']}; channels {m['channels']}\n{segs}\nLINES:\n{lines}"
    return _verdict(_call(f"{COMMON}\n\n{VO_RULES}", user, case["id"]), ("pass", "fail", "uncertain"))


def exclusion(case):
    ctx = case["context"]
    user = (f"{_source(case['source'])}\nCONTEXT BEFORE:\n" + "\n".join(_sent(s) for s in ctx["before"])
            + "\nMOMENT:\n" + "\n".join(_sent(s, "MOMENT>> ") if s.get("start") is not None
                                        else f"MOMENT>> {s['text']}" for s in case["moment"]["sentences"])
            + "\nCONTEXT AFTER:\n" + "\n".join(_sent(s) for s in ctx["after"]))
    return _verdict(_call(f"{COMMON}\n\n{EX_RULES()}", user, case["id"]), ("keep", "exclude", "uncertain"))
