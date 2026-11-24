#!/usr/bin/env python3
"""pipeline/providers.py — ONE provider interface for every model role (law L-x, orchestrator 2026-11-12 '02:45':
"no single model, Ultron first").

Every role (mining, angle + writing, fidelity verdict, context verdict, viewer takeaway, trend brief, story selection,
check verdict) calls Router.call(role, prompt, ...). The role's back-end CHAIN comes from pipeline/model_providers.json;
no vendor or model name appears in any role's code. A back-end that cannot answer now (out of credit, rate-limited after
backoff, server error, transport failure, not configured, the local model without its GPU0 lease) raises Unavailable and
the chain moves on, so the run continues when any one vendor is down (tonight OpenAI ran dry mid-run). A role whose whole
chain is unavailable raises ProviderError: a failed role, never a pass (law L-m).

Verdict roles never run on the writer's vendor or model family (law L-s: "a model from a different vendor than the
writer"; law L-x: generator and judge are different models): Router.call(..., avoid_vendor=<vendors>,
avoid_family=<families>) skips those back-ends; both accept one value or a set (the angle and every writer attempt).

Replies are text only; strict parsing stays with the caller (no repair here, law L-l). Every exchange can be recorded
(record_dir) and replayed offline (replay=True): the recorded back-end name travels with the reply, so every artefact
names the model that produced it. A recording served in a LIVE run is `cached` (the same model's reply to the same
bytes); one served offline is `replayed` (never deliverable, law L-j). A reply its caller finds out of contract is
dropped from the recordings (Router.reject), so it is asked again next time instead of served again.

A back-end that refuses ONE request (RequestRejected: a bad request, over its context, an empty reply) is skipped for
that call only; one that cannot answer at all (Unavailable: account, auth, rate limit after backoff, server, transport)
is down for the rest of the run. Spend is priced per back-end at the config's upper-bound USD per 1M tokens (per minute
for transcription) into one ledger with a guard: each paid call RESERVES its upper bound under the ledger lock before it
runs and settles after; an unreadable ledger stops every paid call (fail closed); a free back-end is never stopped
(SpendLimit). Heimdall's account is read from its /credits endpoint and the 90% tripwire NOTIFIES (Reply.notices and
Router.notices), it never halts (PBX 02:45).

Keys are read by name from the env file inside code; never printed or logged.
"""
import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "model_providers.json")
ENV_PATH = os.path.join("/home/ultron/protocol_pulse", ".env")   # the order's key file (read by name inside code only)
BACKOFF_S = (10, 30, 90)            # rate limits / server errors / transport; an exhausted account is final at once
PER_REQUEST_CODES = (400, 413, 422)  # the request itself was refused: skip this back-end for THIS call only


class Unavailable(Exception):
    """This back-end cannot answer now: the chain moves to the next one, and it is down for the rest of the run."""


class RequestRejected(Exception):
    """This back-end refused THIS request (bad request, over its context, empty reply): the chain moves on for this
    call only; the back-end stays available to other calls."""


class ProviderError(Exception):
    """No back-end of the role's chain answered: the role failed (never a pass)."""


class SpendLimit(Exception):
    """The session's spend guard is reached: no further model call."""


class ReplayMiss(Exception):
    """Offline replay has no recorded exchange for this call."""


IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
RESERVE_CHARS_PER_TOKEN = 3          # RULING 121 (1) (orchestrator 11:25 ET Nov 16): the reserve counts a prompt's tokens
RESERVE_MARGIN = 1.25                # as its characters / 3 (a deliberate over-count; English runs near 4), at list
#   price, with the output cap the call is really sent (max_out), times 1.25; checked against every recorded Grok step-A
#   call: no reported cost beats it (tests/providers TestRuling121Reserve)
RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
                                     # the model's own reported rate once it has this many reported calls
RESERVE_POLL_S = 1.0                 # BATCH 3 (Nov 14): how often a call waiting for room under the limit re-reads
                                     # the ledger (Router reserve_wait_s, Router._reserve)


def is_vision(prompt):
    """RULING 70: a VISION prompt is {"text": str, "images": [base64 JPEG, ...]}; only a back-end with vision = True
    is asked it (the others are skipped for that call)."""
    return isinstance(prompt, dict) and isinstance(prompt.get("text"), str) and isinstance(prompt.get("images"), list) \
        and all(isinstance(i, str) and i for i in prompt["images"])


def prompt_text(prompt):
    """The prompt as text, for the spend estimate, the logs and the recordings: a vision prompt's text with each image
    as its sha256 (a recording never stores the image; its key still covers the image bytes)."""
    if not is_vision(prompt):
        return prompt
    return prompt["text"] + "".join(f"\n[image sha256={hashlib.sha256(i.encode()).hexdigest()}]"
                                    for i in prompt["images"])


@dataclass
class Reply:
    text: str
    backend: str                                  # "vendor:model", the model that produced this text
    vendor: str
    seconds: float = 0.0
    usage: dict = field(default_factory=dict)     # {"in": n, "out": n} (reasoning tokens counted as out)
    usd: float = 0.0
    replayed: bool = False                        # served OFFLINE from a recording (never deliverable, law L-j)
    tried: list = field(default_factory=list)     # [(backend, why unavailable)] before this one answered
    notices: list = field(default_factory=list)
    family: str = ""                              # the model family (law L-x: generator and judge differ)
    cached: bool = False                          # a live run served this model's recorded reply to the same bytes
    record_path: str = ""                         # where the exchange is recorded (Router.reject removes it)
    lx_soft: dict = None                          # RULING 154 (1): a stand-in judge's answer (Router.call's fallback)


def env_value(path, name):
    """One key's value from an env file, read by name inside code (never printed or logged)."""
    try:
        with open(path) as f:
            for line in f:
                k, sep, v = line.strip().partition("=")
                k = k.strip()
                k = k[len("export "):].strip() if k.startswith("export ") else k
                if sep and k == name:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def _http_json(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json",
                                                                              **headers})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def _with_backoff(fn, final_codes=()):
    """fn() with BACKOFF_S retries on 429 / 5xx / transport; HTTP codes in final_codes, an exhausted account and any
    other 4xx are final. A refusal of the request itself (PER_REQUEST_CODES) raises RequestRejected; anything else
    that cannot answer raises Unavailable, with the reason. Transport includes a reply cut mid-body
    (http.client.IncompleteRead) and a bad status line (a dropped connection): both retried. Any other
    http.client.HTTPException (InvalidURL, ImproperConnectionState, ...) cannot answer however often it is asked:
    Unavailable at once. Neither is an OSError: until 00:46 ET Nov 15 they escaped as themselves (Heimdall cut a reply
    43,669 bytes in and ended ruling 110's replay of one model)."""
    last = None
    for wait in BACKOFF_S + (None,):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read() or b"{}")
            except (ValueError, OSError):
                err = {}
            e_obj = err.get("error") if isinstance(err.get("error"), dict) else {}
            code = str(e_obj.get("code") or e_obj.get("type") or err.get("type") or "")
            last = f"HTTP {e.code} {code}".strip()
            if e.code in final_codes or "insufficient_quota" in code or "credit" in code or "billing" in code:
                raise Unavailable(last + " (final: account)") from None
            if (e.code == 429 or e.code >= 500) and wait is not None:
                time.sleep(wait)
                continue
            if e.code in PER_REQUEST_CODES:
                raise RequestRejected(last) from None
            raise Unavailable(last) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError, http.client.IncompleteRead,
                http.client.BadStatusLine) as e:
            last = type(e).__name__
            if wait is not None:
                time.sleep(wait)
                continue
            raise Unavailable(last) from None
        except http.client.HTTPException as e:         # no retry helps: it cannot answer
            raise Unavailable(f"{type(e).__name__} (final)") from None
    raise Unavailable(last or "unavailable")


# ── back-ends ──

class Backend:
    vendor = "?"
    vision = False                   # ruling 70: True only where complete() takes a vision prompt

    def __init__(self, name, spec, env_path):
        self.name, self.spec, self.env_path = name, spec, env_path
        self.model = spec["model"]
        self.family = spec.get("family") or self.model.split("/")[-1].split(":")[0].split("-")[0]
        self.price = tuple(spec.get("price_usd_per_1m") or (0.0, 0.0))
        self.timeout = float(spec.get("timeout_s", 600))

    def usd(self, usage):
        return round(usage.get("in", 0) * self.price[0] / 1e6 + usage.get("out", 0) * self.price[1] / 1e6, 6)

    def free(self):
        return not any(self.price)

    def max_out(self, max_tokens):
        """The most output tokens this back-end may bill for one call (its own floor applied)."""
        return max(int(self.spec.get("min_out", 0)), max_tokens)

    @staticmethod
    def prompt_tokens_upper(prompt, system=None):
        """A prompt's input tokens, counted from above: every character a token (a safe over-estimate), + 200 for the
        message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
        return len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img

    @staticmethod
    def prompt_tokens_reserve(prompt, system=None):
        """RULING 121 (1): a prompt's input tokens for the spend guard's reserve: its characters / RESERVE_CHARS_PER_TOKEN,
        rounded up, + 200 for the message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
        return -(-(len(text) + len(system or "")) // RESERVE_CHARS_PER_TOKEN) + 200 + IMAGE_TOKENS_UPPER * n_img

    def upper_usd(self, prompt, max_tokens, system=None):
        """The spend guard's reserve for one call (RULING 121 (1)): its prompt tokens (prompt_tokens_reserve) and the
        output cap it is really sent (max_out), at list price, times RESERVE_MARGIN."""
        return round(RESERVE_MARGIN * self.usd({"in": self.prompt_tokens_reserve(prompt, system),
                                                "out": self.max_out(max_tokens)}), 6)

    def prompt_usd(self, prompt, system=None):
        """RULING 83 (a) (orchestrator 20:33 Nov 13): what a call abandoned at its deadline is booked at: its PROMPT
        tokens at the listed input rate, no output. A call that never answered has no vendor token count, so the
        prompt is counted from above (prompt_tokens_upper): never an under-booking."""
        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": 0})

    def key(self, name):
        k = env_value(self.env_path, name)
        if not k:
            raise Unavailable(f"{name} not configured")
        return k

    def complete(self, prompt, max_tokens, seed, system=None):
        raise NotImplementedError


class LocalBackend(Backend):
    """gemma3:27b (or the configured local model) on Ultron's GPU0 Ollama through story_semantics.LocalLLM: its GPU0
    placement guard, digest and temperature 0 kept. Only a STARTED LocalLLM handed in by the caller that holds the GPU0
    lease (law L-r) makes this back-end available; without one it is Unavailable (this builder session never uses a GPU)."""
    vendor = "local"

    def __init__(self, name, spec, env_path, llm=None):
        super().__init__(name, spec, env_path)
        self.llm = llm

    def complete(self, prompt, max_tokens, seed, system=None):
        if self.llm is None:
            raise Unavailable("local model needs a started LocalLLM under the GPU0 lease (law L-r)")
        import http.client
        import story_semantics as sm
        if len(prompt) / 2.5 + max_tokens > sm.LLM_CTX:       # Ollama keeps the tail and drops the instructions
            raise RequestRejected(f"prompt over the local context {sm.LLM_CTX}")
        p = (system + "\n\n" + prompt) if system else prompt
        t0 = time.time()
        try:
            text = self.llm._post(p, max_tokens, seed)
        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as e:
            raise Unavailable(f"ollama: {type(e).__name__}") from None
        return text, {"in": 0, "out": 0}, time.time() - t0


class OpenAIBackend(Backend):
    """OpenAI chat/completions; JSON mode (the word JSON is put in the system message, as json_object requires)."""
    vendor = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key("OPENAI_API_KEY")
        body = {"model": self.model, "max_completion_tokens": max(int(self.spec.get("min_out", 0)), max_tokens),
                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object."},
                             {"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}, "seed": seed}
        if self.spec.get("reasoning_effort"):
            body["reasoning_effort"] = self.spec["reasoning_effort"]
        t0 = time.time()
        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout))
        u = j.get("usage") or {}
        try:
            text = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise RequestRejected("openai: no choices") from None
        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0


class GeminiBackend(Backend):
    """Google Gemini generateContent. RULING 87 (21:18 Nov 13): PLAN B ONLY. The key (key_name, default
    GEMINI_API_KEY_MEDLEY) is fenced to this pipeline. It is sent in a header, never in the URL. JSON is asked for in
    words and by responseMimeType. The reply's usageMetadata gives the tokens (thinking counted as output). Gemini
    reports no cost, so the price-table estimate stands for each call, labelled as one."""
    vendor = "google"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def complete(self, prompt, max_tokens, seed, system=None):
        if is_vision(prompt):
            raise RequestRejected("gemini: no image input on this back-end")
        key = self.key(self.spec.get("key_name") or "GEMINI_API_KEY_MEDLEY")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": self.max_out(max_tokens), "temperature": 0, "seed": seed,
                                     "responseMimeType": "application/json"}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        t0 = time.time()
        j = _with_backoff(lambda: _http_json(self.URL.format(model=self.model), body, {"x-goog-api-key": key},
                                             self.timeout))
        u = j.get("usageMetadata") or {}
        try:
            parts = j["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
        except (KeyError, IndexError, TypeError):
            raise RequestRejected("gemini: no candidates") from None
        return text, {"in": int(u.get("promptTokenCount") or 0),
                      "out": int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)}, \
            time.time() - t0


class LocalJudgeBackend(Backend):
    """RULING 87 (21:18 Nov 13): the integrator's GPU0 judge service (gemma3:27b). PLAN B ONLY: step A's verdict when
    only one outside family answers. The integrator's contract (its message of 21:4x Nov 13):
    - a request file in this worktree's tests/package/proof/judge_requests/<request_id>.json (written .tmp, then
      renamed; read-only there, answered once per name and content), body {request_id, family "step_a", prompt,
      max_tokens, seed}, ONE call per request;
    - the answer in RESULTS/<request_id>.<prompt_id>.json, prompt_id = sha256(json.dumps([prompt, max_tokens,
      seed]))[:20] (the integrator's local_judge.prompt_id; live 22:26:30 Nov 13, judge_sha c62a1e12088c), with
      {request_id, family, prompt_id, model, digest, seed, max_tokens, text, error, seconds, waited_s, at, judge_sha}.
      Only that exact file is read: an answer is this prompt's by its own sha.
    A render always comes first, so the wait allows WAIT_S (40 min). No answer in time, an error, or a file that
    cannot be read is no verdict (Unavailable for this call). The reply's contract is checked by the caller, as for a
    vendor's. Local: free, no spend."""
    vendor = "local_judge"
    REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
                            "judge_requests")
    RESULTS = "/home/ultron/protocol_pulse/data/local_judge/results"      # the integrator's; read only
    WAIT_S, POLL_S = 2400.0, 10.0

    def complete(self, prompt, max_tokens, seed, system=None):
        if is_vision(prompt) or system:
            raise RequestRejected("local judge: a text prompt without a system message only")
        rid = f"pp-selectid.{time.strftime('%Y%m%dT%H%M%S')}.{uuid.uuid4().hex[:8]}"
        pid = hashlib.sha256(json.dumps([prompt, int(max_tokens), int(seed)]).encode()).hexdigest()[:20]
        os.makedirs(self.REQUESTS, exist_ok=True)
        tmp, final = os.path.join(self.REQUESTS, rid + ".tmp"), os.path.join(self.REQUESTS, rid + ".json")
        with open(tmp, "x") as f:
            json.dump({"request_id": rid, "family": "step_a", "prompt": prompt, "max_tokens": int(max_tokens),
                       "seed": int(seed)}, f)
        os.rename(tmp, final)
        t0 = time.time()
        answer = os.path.join(self.RESULTS, f"{rid}.{pid}.json")
        while True:
            rec, torn = None, None
            if os.path.exists(answer):
                try:
                    with open(answer) as f:
                        rec = json.load(f)
                except (OSError, ValueError) as e:      # audit 0108 C1 (glm): a file read while it is being written
                    torn = f"{type(e).__name__}"        # is polled again until the deadline, never taken as final
            if rec is not None:
                if not isinstance(rec, dict) or rec.get("request_id") != rid or rec.get("prompt_id") != pid or \
                        rec.get("error") or not isinstance(rec.get("text"), str):
                    raise RequestRejected(f"local judge: no verdict ({str((rec or {}).get('error'))[:200]})")
                return rec["text"], {"in": 0, "out": 0, **{k: rec.get(k) for k in ("judge_sha", "digest",
                                                                                    "waited_s")}}, time.time() - t0
            if time.time() - t0 >= self.WAIT_S:
                raise Unavailable(f"local judge: no answer within {self.WAIT_S:.0f} s (a render comes first)" +
                                  (f"; the answer file could not be read ({torn})" if torn else ""))
            time.sleep(self.POLL_S)


class DeadlineExceeded(Exception):
    """A back-end gave no answer within the caller's deadline (orchestrator 22:40 ruling 5: one writer call never waits
    more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""


def _within(seconds, fn, on_abandon=None, on_late=None):
    """fn() in a daemon thread, waited for at most `seconds`. -> its value, or its own exception re-raised, or
    DeadlineExceeded. At the deadline on_abandon() runs (it books the abandoned call) BEFORE DeadlineExceeded is
    raised, under a lock the thread takes when it ends, so the booking always comes first. An abandoned thread finishes
    (or times out) on its own; then on_late(on_abandon's value, fn's value or None, fn's exception or None) runs in
    it (ruling 83 (a): a late answer's own figure replaces the booking). Its text is dropped unrecorded. An exception
    from on_late is dropped (it runs where nobody can catch it); the booking then stands."""
    import threading
    box, done, lock = {}, threading.Event(), threading.Lock()

    def run():
        try:
            box["value"] = fn()
        except BaseException as e:            # handed back to the caller below
            box["error"] = e
        with lock:
            done.set()
            late = "abandoned" in box
        if late and on_late is not None:
            try:
                on_late(box["abandoned"], box.get("value"), box.get("error"))
            except Exception:                 # noqa: BLE001 (no caller is left; the booking stands)
                pass
    threading.Thread(target=run, daemon=True, name="pp-deadline").start()
    if not done.wait(seconds):
        with lock:
            if not done.is_set():             # still running: abandoned (an answer at the deadline is used below)
                box["abandoned"] = on_abandon() if on_abandon is not None else None
                raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
    if "error" in box:
        raise box["error"]
    return box["value"]


def _num(x):
    import math
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def _reported(usd):
    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
    the price-table estimate for it, labelled as an estimate)."""
    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}


class HeimdallBackend(OpenAIBackend):
    """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire. A vision
    prompt (ruling 70) goes as chat-completions content parts: the text, then each image as an image_url data URL, the
    form pipeline/visual_check.py uses with these image models."""
    vendor = "heimdall"
    vision = True

    def _base(self):
        if not self.spec.get("base_url"):
            raise Unavailable("heimdall: no base_url in the config")
        return self.spec["base_url"].rstrip("/")

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key("HEIMDALL_API_KEY")
        content = prompt if not is_vision(prompt) else \
            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
                "temperature": self.spec.get("temperature", 0),
                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
                             {"role": "user", "content": content}]}
        if self.spec.get("plain") and not system:     # RULING 162 (1): a back-end that asks the render's way
            body["messages"] = [{"role": "user", "content": content}]    # (owner_rules.HeimdallText): the user
        if isinstance(self.spec.get("reasoning"), dict):                  # message only, its reasoning effort
            body["reasoning"] = dict(self.spec["reasoning"])
        t0 = time.time()
        base = self._base()
        j = _with_backoff(lambda: _http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
                                             self.timeout), final_codes=(401, 402, 403))
        u = j.get("usage") or {}
        try:
            text = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise RequestRejected("heimdall: no choices") from None
        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
                          **_reported(u.get("cost"))), time.time() - t0

    def credits(self):
        """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
        try:
            key = self.key("HEIMDALL_API_KEY")
            req = urllib.request.Request(self._base() + "/credits", headers={"Authorization": "Bearer " + key})
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
            d = d.get("data", d)
            return float(d["total_usage"]), float(d["total_credits"])
        except Exception:
            return None


class XAIBackend(Backend):
    """xAI chat/completions; a judge runs at temperature 0 with the attempt's seed (production parity with LocalLLM).
    Told it has no tools and must answer in one message (orchestrator 02:00)."""
    vendor = "xai"
    URL = "https://api.x.ai/v1/chat/completions"
    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."

    def max_out(self, max_tokens):
        n = max(int(self.spec.get("min_out", 8000)), max_tokens * 8)          # a reasoning model thinks inside it
        cap = self.spec.get("max_out_cap")    # RULING 121: the most output it is sent, whatever the role asks (12,000:
        return min(n, int(cap)) if cap else n  # step A's 4,000 x 8 was 32,000 and reserved $0.80 of Grok output alone)

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
        body = {"model": self.model, "max_tokens": self.max_out(max_tokens),
                "temperature": self.spec.get("temperature", 0), "seed": seed,
                "messages": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
                             {"role": "user", "content": prompt}]}
        t0 = time.time()
        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
                          final_codes=(401, 402, 403))
        u = j.get("usage") or {}
        reasoning = int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
        try:
            text = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise RequestRejected("xai: no choices") from None
        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning},
                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0


class AnthropicBackend(Backend):
    """Anthropic Messages (streaming; adaptive thinking at the configured effort)."""
    vendor = "anthropic"

    def complete(self, prompt, max_tokens, seed, system=None):
        try:
            import anthropic
        except ImportError:
            raise Unavailable("anthropic SDK not installed") from None
        client = anthropic.Anthropic(api_key=self.key("ANTHROPIC_API_KEY"), max_retries=3, timeout=self.timeout)
        kw = {"model": self.model, "max_tokens": self.max_out(max_tokens),
              "messages": [{"role": "user", "content": prompt}],
              "system": (system or "") + " Reply with one JSON object only, no prose, no code fence."}
        if self.spec.get("effort"):
            kw["output_config"] = {"effort": self.spec["effort"]}
            kw["thinking"] = {"type": "adaptive"}
        t0 = time.time()
        try:
            with client.messages.stream(**kw) as s:
                msg = s.get_final_message()
        except anthropic.APIStatusError as e:
            if e.status_code in PER_REQUEST_CODES:
                raise RequestRejected(f"anthropic HTTP {e.status_code}") from None
            raise Unavailable(f"anthropic HTTP {e.status_code}") from None
        except anthropic.APIError as e:
            raise Unavailable(f"anthropic {type(e).__name__}") from None
        text = "".join(b.text for b in msg.content if b.type == "text")
        return text, {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}, time.time() - t0


class XAISearchBackend(Backend):
    """xAI Responses API with live X and web search tools (x_search, web_search), for the trend brief only. The
    reply text is returned as written; the caller validates it into the closed taxonomy (law L-w 4)."""
    vendor = "xai_search"
    URL = "https://api.x.ai/v1/responses"

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
        body = {"model": self.model, "max_output_tokens": max_tokens,
                "input": [{"role": "system", "content": system or "Answer with one JSON object only."},
                          {"role": "user", "content": prompt}],
                "tools": [{"type": t} for t in self.spec.get("tools", ("x_search", "web_search"))]}
        t0 = time.time()
        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
                          final_codes=(401, 402, 403))
        text = j.get("output_text") or ""
        if not text:
            for item in j.get("output") or []:
                for part in (item.get("content") or []) if isinstance(item, dict) else []:
                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
                        text += part.get("text") or ""
        u = j.get("usage") or {}
        return text, {"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
                      "out": int(u.get("output_tokens") or u.get("completion_tokens") or 0)}, time.time() - t0


class XAIVisionBackend(Backend):
    """RULING 70: xAI's Responses API with image input (docs.x.ai, image understanding: "type": "input_image", a data
    URL, "detail": "high"; "store": false, since a server-side record can make image requests fail). Only a vision
    prompt is asked here. Its cost is the vendor's own figure when the reply carries one (cost_in_usd_ticks)."""
    vendor = "xai_vision"
    vision = True
    URL = "https://api.x.ai/v1/responses"
    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."

    def max_out(self, max_tokens):
        return max(int(self.spec.get("min_out", 8000)), max_tokens * 4)        # a reasoning model thinks inside it

    def complete(self, prompt, max_tokens, seed, system=None):
        if not is_vision(prompt):
            raise RequestRejected("xai_vision takes a vision prompt only")
        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
        parts = [{"type": "input_text", "text": prompt["text"]}] + [
            {"type": "input_image", "image_url": "data:image/jpeg;base64," + i, "detail": "high"}
            for i in prompt["images"]]
        body = {"model": self.model, "max_output_tokens": self.max_out(max_tokens), "store": False,
                "temperature": self.spec.get("temperature", 0),
                "input": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
                          {"role": "user", "content": parts}]}
        t0 = time.time()
        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
                          final_codes=(401, 402, 403))
        text = j.get("output_text") or ""
        if not text:
            for item in j.get("output") or []:
                for part in (item.get("content") or []) if isinstance(item, dict) else []:
                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
                        text += part.get("text") or ""
        u = j.get("usage") or {}
        reasoning = int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
        out = int(u.get("output_tokens") or u.get("completion_tokens") or 0)
        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
        return text, dict({"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
                           "out": out + (reasoning if reasoning > out else 0)},
                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0


# ── transcription back-ends (law L-v 2's second recognition pass; role "transcribe") ──

def _multipart(fields, file_field, path, content_type="audio/wav"):
    boundary = uuid.uuid4().hex
    body = b"".join(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
                    for k, v in fields.items())
    with open(path, "rb") as f:
        data = f.read()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
             f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {content_type}\r\n\r\n").encode() + data + \
        f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def _wav_seconds(path):
    import wave
    try:
        with wave.open(path) as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, OSError, EOFError):
        return 600.0                                   # not measurable: priced as ten minutes (an upper bound)


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class STTBackend(Backend):
    """A transcription back-end: transcribe(wav) -> ({"text", "segments": [{"speaker", "start", "end", "text"}]},
    seconds), times in seconds from the start of the audio. Priced per minute of audio (price_usd_per_min)."""

    def usd(self, usage):
        return round(float(usage.get("seconds", 0.0)) / 60.0 * float(self.spec.get("price_usd_per_min", 0.0)), 6)

    def free(self):
        return not float(self.spec.get("price_usd_per_min", 0.0))

    def upper_usd(self, wav, max_tokens=0, system=None):
        return self.usd({"seconds": _wav_seconds(wav) + 5.0})

    def _post(self, url, body, headers):
        req = urllib.request.Request(url, data=body, headers=headers)
        return json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())

    def transcribe(self, wav):
        raise NotImplementedError


class OpenAITranscribe(STTBackend):
    """OpenAI's transcription API (diarised JSON when the config says diarize)."""
    vendor = "openai"
    URL = "https://api.openai.com/v1/audio/transcriptions"

    def transcribe(self, wav):
        key = self.key("OPENAI_API_KEY")
        fields = {"model": self.model, "response_format": "diarized_json" if self.spec.get("diarize") else "json"}
        if self.spec.get("diarize"):
            fields["chunking_strategy"] = "auto"
        body, ctype = _multipart(fields, "file", wav)
        t0 = time.time()
        d = _with_backoff(lambda: self._post(self.URL, body, {"Authorization": "Bearer " + key, "Content-Type": ctype}),
                          final_codes=(401, 402, 403))
        segs = [{"speaker": s.get("speaker"), "start": s.get("start"), "end": s.get("end"), "text": s.get("text") or ""}
                for s in d.get("segments") or [] if isinstance(s, dict)]
        return {"text": d.get("text") or " ".join(s["text"] for s in segs), "segments": segs}, time.time() - t0


class ElevenLabsTranscribe(STTBackend):
    """ElevenLabs speech-to-text with diarisation: word timings with speaker ids, grouped into speaker runs."""
    vendor = "elevenlabs"
    URL = "https://api.elevenlabs.io/v1/speech-to-text"

    def transcribe(self, wav):
        key = self.key("ELEVENLABS_API_KEY")
        body, ctype = _multipart({"model_id": self.model, "diarize": "true", "timestamps_granularity": "word",
                                  "tag_audio_events": "false"}, "file", wav)
        t0 = time.time()
        d = _with_backoff(lambda: self._post(self.URL, body, {"xi-api-key": key, "Content-Type": ctype}),
                          final_codes=(401, 402, 403))
        segs, words = [], []
        for w in d.get("words") or []:
            if not isinstance(w, dict) or w.get("type", "word") != "word":
                continue
            words.append({"text": w.get("text") or "", "start": w.get("start"), "end": w.get("end"),
                          "speaker": w.get("speaker_id")})
            if segs and segs[-1]["speaker"] == w.get("speaker_id"):
                segs[-1]["end"] = w.get("end")
                segs[-1]["text"] += " " + (w.get("text") or "")
            else:
                segs.append({"speaker": w.get("speaker_id"), "start": w.get("start"), "end": w.get("end"),
                             "text": w.get("text") or ""})
        return {"text": d.get("text") or " ".join(s["text"] for s in segs), "segments": segs, "words": words}, \
            time.time() - t0


VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "xai_vision": XAIVisionBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe,
           "google": GeminiBackend, "local_judge": LocalJudgeBackend}


ROUTINGS = ("today", "heimdall_first")    # RULING 85 (21:15 Nov 13): the switch (model_providers.json "routing")
LX_SOFT_NEVER = ("angle_write", "probe87:", "coherence_panel")
LX_SOFT_NEVER_KINDS = ("value", "closing")   # ITEM 2 (orchestrator 09:20 / 09:35 ET Nov 24): our closing line's judges
#   (its value grade, kind "value"; fidelity over a package that carries it, kind "closing") are never a stand-in: "No
#   judge from another family awake means no line"   # RULING 154 (1): a writer, a probe and a panel seat
#   (each asked by name: package.coherence_by_panel fills its own seats, ruling 152 (2)) never take a stand-in judge
SHADOW_ROLES = ("context_verdict", "coherence_verdict", "fidelity_verdict", "exclusion_verdict", "speaker_verdict",
                "viewer_takeaway", "visual_check")      # RULING 86: the verdicts a shadow back-end is asked again


def gateway(b):
    """The vendor a back-end is reached through: "heimdall" for every Heimdall model, whatever its routing makes of
    b.vendor (ruling 85: under heimdall_first, a Heimdall family is its own maker, b.vendor == "heimdall/<family>")."""
    return getattr(b, "gateway", b.vendor)


def call_parsed(router, role, prompt, parse, max_tokens=2000, seed=7, system=None, avoid_vendor=None,
                avoid_model=None, avoid_family=None, deadline_s=None, kind=None):
    """The 20:33 order (ruling 82's chain on every verdict): the role's chain, where an answer OUT OF CONTRACT also
    moves on to the next model, each model once. parse(text) raises ValueError / TypeError / KeyError for an answer
    out of contract; that reply is rejected (its recording dropped, so it is asked again another time) and its model
    skipped. -> (reply, parse(reply.text)). The chain spent: ProviderError (no verdict; nothing is cached by the
    caller). Errors of the back-ends themselves (down, refused, past the deadline, empty) move on inside Router.call.
    Works with any router that has call() (and reject(), when it has one)."""
    skip, why = set(_as_set(avoid_model)), []
    while True:
        kw = {k: v for k, v in (("system", system), ("avoid_vendor", avoid_vendor), ("avoid_family", avoid_family),
                                ("deadline_s", deadline_s), ("kind", kind)) if v is not None}
        try:
            r = router.call(role, prompt, max_tokens, seed, **kw, **({"avoid_model": frozenset(skip)} if skip else {}))
        except ProviderError as e:
            if why:
                raise ProviderError(f"{e}; answers out of contract: {why}") from e
            raise
        if r.backend in skip:                      # never a loop: a model told to skip answered again (no verdict)
            raise ProviderError(f"{role}: {r.backend} answered again though skipped; answers out of contract: {why}")
        try:
            return r, parse(r.text)
        except (ValueError, TypeError, KeyError) as e:
            if hasattr(router, "reject"):
                router.reject(r)
            why.append((r.backend, f"{type(e).__name__}: {str(e)[:120]}"))
            skip.add(r.backend)


def _as_set(x):
    if not x:
        return frozenset()
    return frozenset(v for v in x if v) if isinstance(x, (set, frozenset, list, tuple)) else frozenset([x])


# ── the router ──

class Router:
    """Role -> back-end chain from the config. call() tries the chain in order (skipping back-ends this run already
    found unavailable, and any on avoid_vendor), records every exchange when record_dir is set, prices it into the
    spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""

    def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
                 breakers=None, deadlines=None, reserve_wait_s=0.0, uncapped=()):
        with open(config) as f:
            self.config = json.load(f)
        rt = self.config.get("routing") or {}
        self.routing = routing or rt.get("mode") or "today"     # RULING 85: "today" or "heimdall_first"
        if self.routing not in ROUTINGS:
            raise ValueError(f"routing must be one of {ROUTINGS}, not {self.routing!r}")
        self.env_path = env_path or ENV_PATH
        self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
        if limit_basis not in ("estimate", "reported"):
            raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
        self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
        self.uncapped = tuple(uncapped)           # RULING 118 (b): vendors recorded in the ledger but never capped
        self.spend_refused = []                   # RULING 107 (1): the back-end of every paid call _reserve refused for
        #   money (list.append: one per refusal, from any worker thread); a build records them as work left undone
        self.reserve_wait_s = float(reserve_wait_s)   # _reserve: 0 (the default) refuses at once, as every caller had
        self.reserve_poll_s = RESERVE_POLL_S          # it; a batch build that may wait for calls in flight opts in
        import threading
        self.deadline_log, self.slow_log_s = deadline_log, slow_log_s     # order 08:06 item 55: the evidence file
        self._log_lock = threading.Lock()
        self.down, self.notices = {}, []
        self.backends = {}
        for name, spec in self.config["backends"].items():
            cls = VENDORS[spec["vendor"]]
            self.backends[name] = cls(name, spec, self.env_path, local_llm) if cls is LocalBackend else \
                cls(name, spec, self.env_path)
        self.chains = dict(chains or {})          # tests / the A/B harness may pin a role's chain (still by config name)
        # RULING 86 (21:18 Nov 13): {role or "*": back-end} asked the SAME prompt of every verdict another back-end
        # decided (recorded to shadow_log, never deciding); its role is "shadow86:<role>", so its recordings and its
        # spend (ruling 48's ledger) are its own
        self.shadow, self.shadow_log, self._shadows = dict(shadow or {}), shadow_log, []
        for r_, name_ in self.shadow.items():
            if name_ not in self.backends:
                raise ValueError(f"the shadow back-end {name_!r} is not in the config")
        # RULING 87 (21:18 Nov 13): PLAN B. health: the shared state file (pipeline/heimdall_health.py); every
        # Heimdall verdict or writer call's outcome is noted there, and while it says "plan_b" the roles named in
        # plan_b_chains (frozen legs already out) run on them: Grok mainly, then any other outside key that answers.
        # A probe thread asks each Heimdall family a one-word question every 2 minutes while calls fail.
        self.health, self.plan_b_chains, self.state_md = health, dict(plan_b_chains or {}), state_md
        self._probe = None
        # RULING 99 (10:48 Nov 14): the circuit breaker's state file (pipeline/circuit_breaker.py). A model that misses
        # its deadline twice in a row, or runs past twice the cap it was sent, is skipped by every list for 30 minutes
        # (live calls only: a recorded reply, replay, probes and shadow calls never touch it)
        self.breakers, self.breaker_events = breakers, []
        # RULING 100 (12:16 Nov 14): the per-(model, verdict type) deadlines (pipeline/deadline_table.py's table)
        self.deadlines = deadlines
        if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
            for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
                if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
                    b.gateway, b.vendor = b.vendor, f"{b.vendor}/{b.family}"

    def mode(self):
        """RULING 87: "plan_b" while the shared health state says Heimdall is down, else this router's routing."""
        if not self.health:
            return self.routing
        import heimdall_health as HH
        try:
            m = HH.mode(self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
        except HH.HealthUnreadable as e:          # audit 0108 C1 (glm): never guessed, and never an exception the
            raise ProviderError(f"the Heimdall health state cannot be read: {e}") from None   # call sites miss: no
        return "plan_b" if m == "plan_b" else self.routing                                    # verdict (law L-m)

    def chain(self, role, kind=None):
        """The back-ends a call of `role` tries, in order. RULING 88 (22:15 Nov 13): a verdict TYPE may have its own
        list, keyed "<role>:<kind>" (step_a_first, step_a_second, step_c, hook, clips_alone, coherence); without one,
        the role's. Plan B's lists first while Heimdall is down (ruling 87); then this router's overrides; then the
        routing's lists (ruling 85, not under "today"); then the role's configured chain."""
        keys = ([f"{role}:{kind}"] if kind else []) + [role]
        if self.health and any(k in self.plan_b_chains for k in keys) and self.mode() == "plan_b":
            return list(next(self.plan_b_chains[k] for k in keys if k in self.plan_b_chains))   # ruling 87
        for k in keys:
            if k in self.chains:
                return list(self.chains[k])
            routed = ((self.config.get("routing") or {}).get(self.routing) or {}).get(k)
            if routed:                            # RULING 85 / 88: this routing's own list (today: per type only)
                return list(routed)
        try:
            return list(self.config["roles"][role]["chain"])
        except KeyError:
            raise ProviderError(f"role {role!r} has no chain in {os.path.basename(CONFIG)}") from None

    # recording
    def _path(self, role, backend, prompt, max_tokens, seed, system):
        k = hashlib.sha256(json.dumps([role, backend, prompt, max_tokens, seed, system or ""]).encode()).hexdigest()
        return os.path.join(self.record_dir, k[:2], k + ".json")

    # the spend ledger: reserve the upper bound before a paid call, settle after (fail closed)
    def _lock(self):
        import fcntl
        os.makedirs(os.path.dirname(os.path.abspath(self.spend_path)), exist_ok=True)
        lk = open(self.spend_path + ".lock", "w")
        fcntl.flock(lk, fcntl.LOCK_EX)
        return lk

    def _ledger(self):
        """The ledger (a missing file is an empty one). An unreadable ledger is a SpendLimit: no paid call runs on a
        spend total nobody can read (fail closed). Reservations of processes that are gone are released."""
        if not os.path.exists(self.spend_path):
            return {"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}, "reserved": {}}
        try:
            with open(self.spend_path) as f:
                d = json.load(f)
            if not isinstance(d, dict) or not isinstance(d.get("usd_estimate", 0.0), (int, float)):
                raise ValueError("not a ledger")
        except (OSError, ValueError) as e:
            raise SpendLimit(f"the spend ledger {self.spend_path} is unreadable ({type(e).__name__}): no paid call "
                             "until it is repaired") from None
        for k, v in (("calls", 0), ("by_backend", {}), ("by_role", {}), ("reserved", {})):
            d.setdefault(k, v)
        live = {}
        for k, v in d["reserved"].items():
            try:
                os.kill(int(str(k).split(":")[0]), 0)
                live[k] = v
            except PermissionError:
                live[k] = v                            # another user's live process
            except (ValueError, ProcessLookupError, OSError):
                pass
        d["reserved"] = live
        return d

    def _save(self, d):
        tmp = f"{self.spend_path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, indent=1)
        os.replace(tmp, self.spend_path)

    def _spent(self):
        """The ledger's total (raises SpendLimit when it cannot be read)."""
        if not self.spend_path:
            return 0.0
        with self._lock():
            return float(self._ledger()["usd_estimate"])

    def _log_slow(self, rec):
        """Order 08:06 item 55: one JSON line per call that missed its deadline or answered in >= slow_log_s, appended
        to deadline_log (the evidence the Heimdall team gets). Evidence, never a gate: a write that fails becomes a
        notice and the call goes on."""
        if not self.deadline_log:
            return
        line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        try:
            with self._log_lock:
                os.makedirs(os.path.dirname(os.path.abspath(self.deadline_log)), exist_ok=True)
                with open(self.deadline_log, "a") as f:
                    f.write(line + "\n")
        except OSError as e:
            self.notices.append(f"the deadline log could not be written: {type(e).__name__}: {e}")

    def _capped(self, name):
        """RULING 118 (orchestrator 05:40 ET Nov 16): (a) the OUTSIDE vendors' dollars are capped; (b) Heimdall's are
        free: a back-end of an `uncapped` vendor (the name's part before ':', as the ledger keys it) is recorded in the
        ledger like any other, but never reserved and never counted toward limit_usd. No `uncapped`: every back-end."""
        return name.split(":", 1)[0] not in self.uncapped

    def _basis_total(self, d):
        """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
        bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
        estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
        its deadline, booked at its prompt tokens (ruling 83 (a), 20:33 Nov 13) until a late answer replaces it)."""
        if self.limit_basis == "reported":
            if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
                raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
                                 "cannot be read (fail closed; audit 0707 C1, glm P1-2)")
            if self.uncapped:                    # RULING 118: the capped vendors' own figures; the unreported estimate
                return sum(float(v.get("usd_reported", 0.0) or 0.0)     # keeps no vendor split, so all of it
                           for k, v in (d.get("by_backend") or {}).items()     # counts (the stricter reading)
                           if self._capped(k)) + float(d.get("usd_unreported_estimate", 0.0))
            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
        if self.uncapped:
            return sum(float(v.get("usd_estimate", 0.0) or 0.0)
                       for k, v in (d.get("by_backend") or {}).items() if self._capped(k))
        return float(d["usd_estimate"])

    def spent(self):
        """The ledger's total on this router's limit basis (0.0 with no ledger; raises SpendLimit when unreadable)."""
        if not self.spend_path:
            return 0.0
        with self._lock():
            return self._basis_total(self._ledger())

    def _reserve(self, b, upper):
        """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
        SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
        reservations stay at list price whatever the basis; since RULING 121 (1) each is the call's reserve
        (upper_usd: characters / 3 as its prompt tokens, its real output cap, x 1.25), checked against every recorded
        Grok step-A call rather than counted from above.
        With reserve_wait_s > 0 (a batch build's opt-in; the default 0 keeps the refusal at once that every other
        caller, the render's among them, relies on): when spent + this call's upper bound fits and only the reservations
        of calls IN FLIGHT stand in the way, the call waits for them to settle (each ends in an answer, an error or an
        abandonment, and releases its reservation), sleeping outside the ledger lock and re-reading the ledger every
        reserve_poll_s, and reserves once it fits; still kept out after reserve_wait_s, it is refused (fail closed).
        Spend alone over the limit is refused at once. The wait runs before the call's own deadline starts: only a
        caller with no time budget of its own should opt in. Batch 3's builds 1 and 2 (Nov 14) held
        65 moments at step A, medley and spotlight (90 holds in all), without this wait: six step-A workers, each
        reserving about $0.85, under a $4.50 limit with $0.27 spent; four fit, and the other workers were refused batch
        after batch while those four ran."""
        if not self.spend_path or b.free() or not self._capped(b.name):     # ruling 118 (b): Heimdall is free
            return None
        try:
            return self._reserve_capped(b, upper)
        except SpendLimit:                        # RULING 107 (1) (build 134, 12:57 ET Nov 17): a call refused for
            self.spend_refused.append(b.name)     # money is work left undone, never "nothing new"
            raise

    def _reserve_capped(self, b, upper):
        """_reserve for a capped paid back-end: reserve `upper` or raise SpendLimit (its docstring)."""
        t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
        while True:
            with self._lock():
                d = self._ledger()
                held = sum(float(x) for x in d["reserved"].values())
                spent = self._basis_total(d)
                if spent + held + upper <= self.limit_usd:
                    key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
                    d["reserved"][key] = round(upper, 6)
                    self._save(d)
                    return key
                if spent + upper > self.limit_usd or time.time() >= t_end:
                    raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's "
                                     f"upper bound {upper:.2f} > the limit {self.limit_usd} USD" +
                                     (f" (still, after waiting {self.reserve_wait_s:g} s for the calls in flight)"
                                      if waited else ""))
            waited = True
            time.sleep(max(0.01, float(self.reserve_poll_s)))

    def reported_rate(self, name):
        """RULING 107 Q1 (orchestrator 20:40 ET Nov 14): the model's own recorded vendor cost per PROMPT token: its
        vendor-reported dollars over the prompt tokens of the calls that carried a figure ("in_reported"; a ledger kept
        before it counts every call's prompt tokens, "in"). None (list price applies) until the model has
        RATE_MIN_REPORTED reported calls, or with no tokens, no ledger, or an unreadable one."""
        if not self.spend_path:
            return None
        try:
            with self._lock():
                rows = self._ledger()["by_backend"]
            b = rows.get(name) if isinstance(rows, dict) else None
            n = int(b.get("reported_calls") or 0) if isinstance(b, dict) else 0
        except (SpendLimit, OSError, TypeError, ValueError):   # anything unreadable: list price, the higher booking
            return None                                          # (glm, audit 20261114_2043 C1 F1)
        if not isinstance(b, dict) or not _num(b.get("usd_reported")):
            return None
        toks = b.get("in_reported", b.get("in"))
        if n < RATE_MIN_REPORTED or not _num(toks) or toks <= 0:
            return None
        return float(b["usd_reported"]) / float(toks)

    def booking_usd(self, b, prompt, system=None):
        """What a call abandoned at its deadline is booked at on the cap's basis (ruling 48's unreported estimate):
        RULING 107 Q1, the model's own reported rate x the prompt sent (counted from above, prompt_tokens_upper: never
        an under-count of the prompt); before RATE_MIN_REPORTED reported calls, list price (ruling 83 (a),
        Backend.prompt_usd). -> (usd, "reported_rate" or "list").
        The rate is read under the ledger lock and the booking written under a second one (_settle): a reported call
        that lands between them moves the rate by one call. The ledger stays balanced, since a late answer removes the
        booking as it was stored (on_cap), never a recomputed one (glm, audit 20261114_2043 C1 F3). The rate applies
        only while the call is abandoned: a late answer with no vendor figure is accounted, as ruling 83 (a) says, at
        the estimate from its own token counts (list price) in place of the booking (C1 F14)."""
        rate = self.reported_rate(b.name)
        if rate is None:
            return b.prompt_usd(prompt, system), "list"
        return round(rate * b.prompt_tokens_upper(prompt, system), 8), "reported_rate"

    def _reserve_fraction(self, b):
        """RULING 123 (1) (orchestrator 14:05 ET Nov 16): a back-end whose spec names reserve_list_fraction (Grok: 0.25)
        is reserved at that fraction of its list-price reserve, until a call of it bills above that fraction of the list
        price of what it used: then the day's ledger records the trip (reserve_tripped) and it is reserved at list for
        the rest of that ledger's day (proof_ly.day_ledger: a ledger a day). -> the fraction, or None (list)."""
        f = b.spec.get("reserve_list_fraction")
        if not _num(f) or not self.spend_path:
            return None
        with self._lock():
            d = self._ledger()
        return None if (d.get("reserve_tripped") or {}).get(b.name) else float(f)

    def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
        """Release a reservation and account the call that answered (a free one too, when the ledger is readable).
        `unreported` (an abandoned call's booking, ruling 107 Q1) is what the cap's unreported estimate takes in place
        of `usd`, which stays the list-price figure of usd_estimate."""
        if not self.spend_path or (key is None and backend is None):
            return
        with self._lock():
            try:
                d = self._ledger()
            except SpendLimit:
                if key is None:
                    return                             # a free call: nothing to guard, nothing to write
                raise
            held = d["reserved"].pop(key, None)
            if backend is not None:
                usage = usage or {}
                f = backend.spec.get("reserve_list_fraction")      # RULING 123 (1): the tripwire, after every call
                bill = float(usage["usd_reported"]) if _num(usage.get("usd_reported")) else None
                over_list = bill is not None and _num(f) and bill > float(f) * usd
                over_held = bill is not None and _num(f) and _num(held) and bill > float(held)   # RULING 130 (3): a
                #   bill above what was RESERVED for the call trips too (a vision reply's usage runs past its output
                #   cap, so its bill is a small share of the list price of its usage and the first test never fires)
                if (over_list or over_held) and not (d.get("reserve_tripped") or {}).get(backend.name):
                    trip = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "role": role,
                            "billed": round(bill, 6), "list": round(usd, 6),
                            "fraction": float(f), "reserved": held,
                            "why": (f"billed above {float(f):.0%} of list" if over_list else
                                    f"billed above its reserve (${float(held):.4f})") +
                                   ": reserved at list for the rest of the day (rulings 123 (1) / 130 (3))"}
                    d.setdefault("reserve_tripped", {})[backend.name] = trip
                    self.notices.append(f"RESERVE BACK TO LIST: {backend.name} {trip['why']}: billed "
                                        f"${trip['billed']:.4f}, list ${trip['list']:.4f}")
                b = d["by_backend"].setdefault(backend.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
                                                              "price_usd_per_1m": list(backend.price)})
                b.update(calls=b["calls"] + 1, usd_estimate=round(b["usd_estimate"] + usd, 6),
                         **{"in": b["in"] + int(usage.get("in", 0)), "out": b["out"] + int(usage.get("out", 0))})
                if usage.get("seconds"):
                    b["audio_s"] = round(b.get("audio_s", 0.0) + float(usage["seconds"]), 2)
                r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
                r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
                d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
                if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
                    rep = float(usage["usd_reported"])
                    n_in = int(usage.get("in", 0))     # ruling 107 Q1: the reported calls' prompt tokens (a ledger
                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),      # kept before it starts
                             reported_calls=b.get("reported_calls", 0) + 1,                # from every earlier
                             in_reported=b.get("in_reported", b["in"] - n_in) + n_in)      # call's)
                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
                else:                                  # no vendor figure: the estimate stands for this call
                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) +
                                                         (usd if unreported is None else unreported), 6)
            self._save(d)

    def _late(self, ab, value, error):
        """RULING 83 (a): an abandoned call that ended after its deadline (in its own thread). An answer is accounted
        as an on-time one would have been, in place of its prompt-token booking: the vendor's reported figure, or,
        with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
        line goes to the deadline log (item 55). The answer's text is never used or recorded."""
        b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
        on_cap = float(ab.get("usd_unreported", booked))   # ruling 107 Q1: what the cap's basis was booked at
        rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
               "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": on_cap,
               "booked_basis": ab.get("basis", "list")}
        if error is None:
            try:
                _text, usage, _secs = value
                usage = dict(usage or {})
            except (TypeError, ValueError):
                usage = None
            if usage is None:
                rec.update(kind="late_error", error="no (text, usage, seconds) from the back-end")
            else:
                usd, rep = b.usd(usage), usage.get("usd_reported")
                rec.update({"in": usage.get("in"), "out": usage.get("out"), "usd_estimate": usd,
                            "usd_reported": float(rep) if _num(rep) else None})
                n_out, cap = usage.get("out"), ab.get("max_out")
                if _num(n_out) and _num(cap) and n_out > self._runaway_x() * cap:   # ruling 99: a late runaway
                    self._breaker(role, b.name, "runaway", deadline_s=ab.get("deadline_s"), seconds=rec["seconds"],
                                  tokens=n_out, max_out=cap)
                if self.spend_path:
                    try:
                        self._replace_booking(b, role, booked, usage, usd, rep, on_cap)
                        rec["replaced"] = True
                    except Exception as e:             # noqa: BLE001 (audit 2048 C1: on record; the prompt-token
                        rec.update(replaced=False,     # booking stands, the ledger written whole or not at all)
                                   ledger_error=f"{type(e).__name__}: {str(e)[:200]}")
        else:
            rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
        self._log_slow(rec)

    def _replace_booking(self, b, role, booked, usage, usd, rep, booked_unreported=None):
        """RULING 83 (a): a late answer's accounting in place of its prompt-token booking, in one ledger write: its
        own token counts, its estimate (usd) for the estimate basis, and on the reported basis the vendor's figure
        (rep) or, with none, the estimate. The call was counted when it was booked; it is not counted again."""
        with self._lock():
            d = self._ledger()
            bb = d["by_backend"].setdefault(b.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
                                                     "price_usd_per_1m": list(b.price)})
            r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
            delta = usd - booked
            bb.update(usd_estimate=round(bb["usd_estimate"] + delta, 6),
                      **{"in": bb["in"] + int(usage.get("in", 0)), "out": bb["out"] + int(usage.get("out", 0))})
            r["usd_estimate"] = round(r["usd_estimate"] + delta, 6)
            d["usd_estimate"] = round(d["usd_estimate"] + delta, 6)
            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) -
                                                 (booked if booked_unreported is None else booked_unreported), 6)
            if _num(rep):
                n_in = int(usage.get("in", 0))         # ruling 107 Q1: as _settle counts them
                bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
                          reported_calls=bb.get("reported_calls", 0) + 1,
                          in_reported=bb.get("in_reported", bb["in"] - n_in) + n_in)
                d["usd_reported"] = round(d.get("usd_reported", 0.0) + float(rep), 8)
            else:
                d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
            d["late_answers"] = d.get("late_answers", 0) + 1
            self._save(d)

    def reject(self, reply, why=""):
        """The caller found this reply out of its contract: drop its recording, so the exchange is asked again next
        time instead of served again (fable C1 U1). Offline replay keeps its recordings. -> True if one was dropped."""
        if self.replay or reply is None or not getattr(reply, "record_path", ""):
            return False
        try:
            os.remove(reply.record_path)
            return True
        except OSError:
            return False

    def role_deadline(self, role, b):
        """The 20:33 order (ruling 82's chain on the verdicts): a call of a verdict role on a back-end whose gateway
        names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets it when the
        caller sets none. -> seconds or None. (Ruling 100's per-model deadline: effective_deadline.)"""
        rt = self.config.get("routing") or {}
        bounded = set(rt.get("verdict_roles") or ())
        if self.routing == "today":                   # step A's first screen and step C keep no deadline today:
            bounded -= set(rt.get("today_unbounded") or ())   # ruling 82 bounded only the second screen (8 clips a
        if role not in bounded:                       # call cannot answer in 120 s on Heimdall)
            return None
        d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
        return float(d) if _num(d) and d > 0 else None

    def effective_deadline(self, role, b, deadline_s=None):
        """RULING 100 (12:16 Nov 14): DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. The deadline a live call of `role` on
        `b` gets: where one applies (the caller's, else the role's: role_deadline), a verdict role takes the pair's own
        row of the deadline table instead (p90 of its recorded answers x 1.5, 60-300 s), so step A's first screen keeps a
        bound on every leg (deepseek 300 s, glm 60 s, Grok its own); without a row, the number that applied. Where no
        deadline applies (a Heimdall-less second screen's Grok, any writer), none does now either. -> seconds or None."""
        dl = deadline_s or self.role_deadline(role, b)
        if dl and role in set((self.config.get("routing") or {}).get("verdict_roles") or ()):
            import deadline_table as DT
            own = DT.deadline(self.deadlines, b.name, role)
            if own is not None:
                dl = own
        return dl

    def _breaker_live(self, role):
        """RULING 99: the breaker counts and skips only this builder's LIVE calls (never replay, a probe or a shadow)."""
        return bool(self.breakers) and not self.replay and not role.startswith(("probe87:", "shadow86:"))

    @staticmethod
    def _runaway_x():
        import circuit_breaker as CB
        return CB.RUNAWAY_X

    def _breaker_allow(self, role, name, deadline_s=None):
        """RULING 99 -> why `name` is skipped now (its breaker is open, or its one trial is in flight), or None. A trial
        is held for this call's own deadline + 60 s. A state that cannot be read skips nothing (a notice): the breaker
        saves minutes, it never stops a verdict."""
        if not self._breaker_live(role):
            return None
        import circuit_breaker as CB
        try:
            ok, why = CB.allow(name, self.breakers, hold_s=deadline_s + 60.0 if _num(deadline_s) else None)
        except (CB.BreakerUnreadable, OSError) as e:
            n = f"RULING 99: the circuit breaker's state cannot be read, so it skips nothing: {e}"
            if n not in self.notices:
                self.notices.append(n)
            return None
        return None if ok else why

    def breaker_open(self, name):
        """RULING 99, read only (ruling 101's wait estimate): whether a live call would skip `name` now."""
        if not self.breakers:
            return False
        import circuit_breaker as CB
        return CB.is_open(name, self.breakers)

    def _breaker(self, role, name, outcome, **kw):
        """RULING 99: one live call's outcome to the breaker; an open or a close is one line in the evidence file."""
        if not self._breaker_live(role):
            return
        import circuit_breaker as CB
        try:
            ev = CB.record(name, outcome, self.breakers, **kw)
        except (CB.BreakerUnreadable, OSError) as e:
            n = f"RULING 99: the circuit breaker's state cannot be read or written: {e}"
            if n not in self.notices:
                self.notices.append(n)
            return
        if ev:
            self.breaker_events.append(ev)
            self._log_slow(dict(ev, role=role))

    def _note(self, role, b, answered):
        """RULING 87: a Heimdall verdict or writer call's outcome, to the shared health state (never a gate here: a
        state file that cannot be written is a notice). The probe thread starts at the first failure."""
        rt = self.config.get("routing") or {}
        if not self.health or not isinstance(b, HeimdallBackend) or \
                role not in set(rt.get("verdict_roles") or ()) | {"angle_write"}:
            return
        import heimdall_health as HH
        try:
            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid",
                    family=b.family)              # ruling 87 amended: the family a probe must ask
        except (HH.HealthUnreadable, OSError) as e:
            n = f"RULING 87: the Heimdall health state cannot be read or written: {e}"
            if n not in self.notices:
                self.notices.append(n)
        if not answered:
            self.start_probe()

    def start_probe(self, every_s=30.0):
        """RULING 87: the probe thread (one per router): while HH.probe_due, ask each Heimdall family a one-word
        question (60 s each, on ruling 48's ledger as role "probe87"); any answer is a probe answer."""
        import threading
        if self._probe is not None or not self.health:
            return
        import heimdall_health as HH
        fams = [n for n, b in self.backends.items() if isinstance(b, HeimdallBackend) and n.startswith("heimdall:")
                and b.family in ("deepseek", "glm", "qwen")]

        def loop():
            while True:
                try:
                    if HH.probe_due(self.health, who="pp-selectid probe",      # claims the slot (one prober each),
                                    families=sorted({self.backends[n].family for n in fams})):   # 87 amended
                        HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
                                        state_md=self.state_md, who="pp-selectid probe")
                except Exception:                      # noqa: BLE001 (the probe never stops a build)
                    pass
                time.sleep(every_s)
        self._probe = threading.Thread(target=loop, daemon=True, name="pp-probe87")
        self._probe.start()

    def probe_once(self, names):
        """RULING 87: one probe round: each Heimdall family asked a one-word question (60 s, never recorded nor served
        from a recording). A family this run marked down is probed all the same: its mark is lifted for the probe and
        stays lifted when it answers (it may serve again), restored when it does not. -> True if any family answered."""
        ok = False
        for n in names:
            self.chains.setdefault(f"probe87:{n}", [n])
            was = self.down.pop(n, None)
            try:
                r = self.call(f"probe87:{n}", "Reply with the single word OK.", 64, 7, deadline_s=60.0)
                ok = ok or bool(r.text.strip())
            except Exception:                          # noqa: BLE001 (a probe that fails is a probe that failed)
                if was is not None and n not in self.down:
                    self.down[n] = was
        return ok

    def _shadow_of(self, role, kind=None):
        """RULING 86, and RULING 115 for a verdict type: "<role>:<kind>" first (the hook job's qwen), then the role,
        then "*"."""
        return (self.shadow.get(f"{role}:{kind}") if kind else None) or self.shadow.get(role) or self.shadow.get("*")

    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding, kind=None):
        """RULING 86: ask the role's shadow back-end the same prompt, in a thread; one JSON line to shadow_log per
        verdict with both answers. Never raises into the build and never decides. A verdict type's own shadow (RULING
        115) is asked on a chain of its own ("shadow86:<role>:<kind>"), so it never takes another shadow's chain."""
        import threading
        name = self._shadow_of(role, kind)
        own = f"shadow86:{role}:{kind}" if kind and self.shadow.get(f"{role}:{kind}") else f"shadow86:{role}"
        self.chains.setdefault(own, [name])

        def run():
            rec = {"role": role, "kind": kind, "prompt": prompt_text(prompt),
                   "images": len(prompt["images"]) if is_vision(prompt)
                   else 0, "max_tokens": max_tokens, "seed": seed, "system": system,
                   "deciding": {"backend": deciding.backend, "vendor": deciding.vendor, "text": deciding.text,
                                "cached": bool(getattr(deciding, "cached", False))}}
            t0 = time.time()
            try:
                r = self.call(own, prompt, max_tokens, seed, system=system)
                rec["shadow"] = {"backend": r.backend, "text": r.text, "seconds": round(time.time() - t0, 2),
                                 "cached": bool(getattr(r, "cached", False)),
                                 "usd_reported": (r.usage or {}).get("usd_reported"), "usd_estimate": r.usd}
            except Exception as e:                     # noqa: BLE001 (a shadow never stops a build)
                rec["shadow"] = {"backend": name, "error": f"{type(e).__name__}: {str(e)[:300]}",
                                 "seconds": round(time.time() - t0, 2)}
            if self.shadow_log:
                line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
                try:
                    with self._log_lock:
                        os.makedirs(os.path.dirname(os.path.abspath(self.shadow_log)), exist_ok=True)
                        with open(self.shadow_log, "a") as f:
                            f.write(line + "\n")
                except OSError as e:
                    self.notices.append(f"the shadow log could not be written: {type(e).__name__}: {e}")
        t = threading.Thread(target=run, daemon=True, name="pp-shadow86")
        self._shadows.append(t)
        t.start()

    def shadow_wait(self, timeout_s=900.0):
        """RULING 86: wait for every shadow call of this router (a build's side-by-side needs them all). -> the number
        still running when the time ran out (their lines are then missing from shadow_log, and the report says so)."""
        end = time.time() + timeout_s
        for t in list(self._shadows):
            t.join(max(0.0, end - time.time()))
        return sum(t.is_alive() for t in self._shadows)

    def heimdall_tripwire(self, at=0.9):
        """NOTIFY when Heimdall's account usage reaches `at` of its credits (PBX 02:45: never a halt)."""
        h = next((b for b in self.backends.values() if isinstance(b, HeimdallBackend)), None)
        got = h.credits() if h else None
        if got and got[1] > 0 and got[0] / got[1] >= at:
            msg = f"HEIMDALL SPEND AT {int(at * 100)}%: {got[0]:.2f} of {got[1]:.2f} USD"
            if msg not in self.notices:
                self.notices.append(msg)
            return msg
        return None

    def _skip(self, name, b, av, am, af):
        """Why this back-end may not answer this call, or None."""
        if b is None:
            return "not in config backends"
        if b.vendor in av:
            return f"same vendor as the text it judges ({b.vendor}): skipped"
        if name in am:
            return "same model as the generator: skipped"
        if b.family in af:
            return f"same model family as the generator ({b.family}): skipped"
        if name in self.down:
            return f"down this run: {self.down[name]}"
        return None

    def _record(self, path, rec):
        import threading
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"      # the gates call concurrently (05:25 item 5)
        with open(tmp, "w") as f:
            json.dump(dict(rec, recorded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), f, indent=1)
        os.replace(tmp, path)

    def _lx_steps(self, role, kind, av, af):
        """RULING 154 (1) (orchestrator 20:36 ET Nov 23; with 152 (2), 19:36: "L-x soft: a Heimdall panel with a
        flag"): the stand-in judges, in the ruled order, for a verdict whose own chain gave no answer: (1) a Heimdall
        family that did not write, (2) any Heimdall family, (3) the paid model. The Heimdall families are those of the
        role's own list, then of the writer chain (proof_ly.WRITERS), glm excepted (ruling 119 keeps it out of every
        verdict); the paid legs those lists hold off Heimdall. -> [(step, names, avoid_vendor, avoid_family)]."""
        heim, paid, seen = [], [], set()
        for name in list(self.chain(role, kind)) + list(self.chains.get("angle_write") or []):
            b = self.backends.get(name)
            if b is None or name in seen or getattr(b, "family", "") == "glm":
                continue
            seen.add(name)
            (heim if gateway(b) == "heimdall" else paid).append(name)
        return [(1, heim, av, af), (2, heim, None, None), (3, paid, None, None)]

    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
             avoid_family=None, deadline_s=None, kind=None, _names=None):
        try:
            return self._call(role, prompt, max_tokens, seed, system, avoid_vendor, avoid_model, avoid_family,
                              deadline_s, kind, _names)
        except (ProviderError, ReplayMiss) as e:
            av, af = _as_set(avoid_vendor), _as_set(avoid_family)
            if _names is not None or not getattr(self, "lx_soft", False) or not (av or af) or \
                    role.startswith(LX_SOFT_NEVER) or str(kind or "") in LX_SOFT_NEVER_KINDS:
                raise
            first = e                                 # RULING 154 (1): never "every back-end unavailable ... same
        stand_ins, steps = [], self._lx_steps(role, kind, av, af)
        if role == "context_verdict" and str(kind or "").startswith("step_a"):   # step A's two families are a law of
            steps = steps[:1]          # their own (package.second_screen): only a family that did not judge or write
            #   may stand in; the writer's or the first screen's own family would be refused there as
            #   STEP_A_SAME_VENDOR, where no verdict is HELD and retried next build (ruling 102)
        for step, names, v, f in steps:                                # vendor" in the never-empty pass: the stand-in
            try:                                                       # judges, the reply marked (ONE flag on the pin)
                r = self._call(role, prompt, max_tokens, seed, system, v, avoid_model, f, deadline_s, kind, names)
            except (ProviderError, ReplayMiss) as e:
                stand_ins.append(f"step {step}: {str(e)[:200]}")
                continue
            r.lx_soft = {"step": step, "judge": r.backend, "why": str(first)[:240]}
            return r
        raise type(first)(f"{role}: NO JUDGE ANSWERED, the stand-in judges included (ruling 154 (1)): no verdict, so "  # audit
                          f"nothing is judged (never a pass); its own list: {str(first)[:300]}; the stand-ins: " +   # C:
                          "; ".join(stand_ins)[:700]) from first          # never silent, never 'same vendor' alone

    def _call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
              avoid_family=None, deadline_s=None, kind=None, _names=None):
        av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
        tried, notices = [], []
        for name in (self.chain(role, kind) if _names is None else _names):   # ruling 88: the verdict type's own list
            b = self.backends.get(name)
            why = self._skip(name, b, av, am, af)
            if why is None and isinstance(b, STTBackend):
                why = "a transcription back-end (Router.transcribe)"
            if why is None and is_vision(prompt) and not b.vision:
                why = "no image input (ruling 70)"
            if why is None and not is_vision(prompt) and isinstance(b, XAIVisionBackend):
                why = "a vision back-end (ruling 70)"
            if why:
                tried.append((name, why))
                continue
            path = self._path(role, name, prompt, max_tokens, seed, system) \
                if self.record_dir and not role.startswith("probe87:") else None      # ruling 87: a probe is live
            if path and os.path.exists(path):
                with open(path) as f:
                    rec = json.load(f)
                out = Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
                            rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
                    self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: recorded too
                return out
            if self.replay:
                tried.append((name, "replay: not recorded"))
                continue
            dl = self.effective_deadline(role, b, deadline_s)   # the caller's, else the role's (20:33): ruling 100's
            if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
                dl = max(dl, float(b.spec["deadline_floor_s"]))
            bwhy = self._breaker_allow(role, name, dl)          # ruling 99: an open breaker skips it; the next leads
            if bwhy:
                tried.append((name, bwhy))
                continue
            upper = b.upper_usd(prompt, max_tokens, system)
            frac = self._reserve_fraction(b)          # RULING 123 (1): Grok at 25 % of list until a call bills over it
            key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)
            if isinstance(b, HeimdallBackend):
                n = self.heimdall_tripwire()
                if n:
                    notices.append(n)

            if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
                import heimdall_health as HH
                self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
                try:
                    plan_b = self.mode() == "plan_b"
                except ProviderError:                           # an unreadable health state: the ruling-102 words
                    plan_b = False
                HH.announce(self.state_md, "PLAN B WITH ONE OUTSIDE FAMILY: STEP A'S VERDICT IS ASKED OF THE LOCAL "
                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)" if plan_b else
                            "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED, SO ITS VERDICT IS ASKED OF "
                            "THE LOCAL GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE): RULING 87'S LAST RESORT")

            def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
                listed = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it;
                booked, basis = self.booking_usd(b, prompt, system)   # RULING 107 Q1: at the model's own reported rate
                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
                                "deadline_s": deadline_s, "seconds": deadline_s,
                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
                                "booked_usd": booked, "booked_basis": basis})   # evidence first (audit 2048 C1)
                self._settle(key, b, {"in": 0, "out": 0}, listed, role, unreported=booked)   # an unreadable ledger
                return {"backend": b, "role": role, "usd": listed, "usd_unreported": booked, "basis": basis,  # raises
                        "deadline_s": deadline_s, "t0": time.time(),
                        "max_out": b.max_out(max_tokens)}             # ruling 99: a late runaway is measured on it
            try:
                if dl:                                 # ruling 5 (22:40): fail over instead of waiting
                    text, usage, secs = _within(dl, lambda: b.complete(prompt, max_tokens, seed, system),
                                                on_abandon=abandon, on_late=self._late)
                else:
                    text, usage, secs = b.complete(prompt, max_tokens, seed, system)
            except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
                self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
                self._breaker(role, name, "miss", deadline_s=dl, seconds=dl, max_out=b.max_out(max_tokens))
                booked, basis = self.booking_usd(b, prompt, system)
                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f} at "
                                    f"{'its own reported rate' if basis == 'reported_rate' else 'list price'}, "
                                    "rulings 83 (a) / 107)"))
                continue
            except RequestRejected as e:
                self._settle(key)
                self._note(role, b, False)
                tried.append((name, f"refused this request: {e}"))
                continue
            except Unavailable as e:
                self._settle(key)
                self._note(role, b, False)
                self.down[name] = str(e)
                tried.append((name, str(e)))
                continue
            except BaseException:
                self._settle(key)
                raise
            usd = b.usd(usage)
            self._settle(key, b, usage, usd, role)
            if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
                self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
                                "vendor": b.vendor, "deadline_s": dl, "seconds": round(secs, 2),
                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
                                "in": (usage or {}).get("in"),
                                "out": (usage or {}).get("out")})
            if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
                self._note(role, b, False)
                tried.append((name, "refused this request: an empty reply"))
                continue
            self._note(role, b, True)                  # ruling 87: a Heimdall family answered inside its deadline
            cap, n_out = b.max_out(max_tokens), (usage or {}).get("out")
            self._breaker(role, name, "runaway" if _num(n_out) and n_out > self._runaway_x() * cap else "answer",
                          deadline_s=dl, seconds=round(secs, 2), tokens=n_out, max_out=cap)       # ruling 99
            recorded = ""
            if path and isinstance(text, str) and text.strip():
                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
                                    "max_tokens": max_tokens, "system": system, "prompt": prompt_text(prompt),
                                    "text": text,
                                    "usage": usage, "usd": usd, "seconds": round(secs, 2)})
                recorded = path
            out = Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
                        recorded)
            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
                self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: never deciding
            return out
        if self.replay:
            raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
        raise ProviderError(f"{role}: every back-end unavailable: {tried}")

    def transcribe(self, role, wav):
        """The role's TRANSCRIPTION chain on one audio file (law L-v 2) -> (result, Reply naming the back-end); the
        same down / record / replay / spend rules as call(). Recorded by the audio's sha256."""
        tried = []
        audio = _sha_file(wav)
        for name in self.chain(role):
            b = self.backends.get(name)
            why = self._skip(name, b, frozenset(), frozenset(), frozenset())
            if why is None and not isinstance(b, STTBackend):
                why = "not a transcription back-end"
            if why:
                tried.append((name, why))
                continue
            path = self._path(role, name, "audio:" + audio, 0, 0, None) if self.record_dir else None
            if path and os.path.exists(path):
                with open(path) as f:
                    rec = json.load(f)
                return rec["result"], Reply(json.dumps(rec["result"]), name, b.vendor, rec.get("seconds", 0.0),
                                            rec.get("usage") or {}, rec.get("usd", 0.0), self.replay, tried, [],
                                            b.family, not self.replay, path)
            if self.replay:
                tried.append((name, "replay: not recorded"))
                continue
            key = self._reserve(b, b.upper_usd(wav))
            try:
                result, secs = b.transcribe(wav)
            except RequestRejected as e:
                self._settle(key)
                tried.append((name, f"refused this request: {e}"))
                continue
            except Unavailable as e:
                self._settle(key)
                self.down[name] = str(e)
                tried.append((name, str(e)))
                continue
            except BaseException:
                self._settle(key)
                raise
            usage = {"seconds": round(_wav_seconds(wav), 2)}
            usd = b.usd(usage)
            self._settle(key, b, usage, usd, role)
            recorded = ""
            if path:
                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor,
                                    "audio_sha256": audio, "result": result, "usage": usage, "usd": usd,
                                    "seconds": round(secs, 2)})
                recorded = path
            return result, Reply(json.dumps(result), name, b.vendor, round(secs, 2), usage, usd, False, tried, [],
                                 b.family, False, recorded)
        if self.replay:
            raise ReplayMiss(f"{role}: no recorded transcription ({tried})")
        raise ProviderError(f"{role}: every transcription back-end unavailable: {tried}")


class RoleModel:
    """A select_by_id.Model over a role (law L-x for the story-first selector, REQUESTS R6 item 7): complete() ->
    (text, meta) with the answering back-end in meta; ProviderError becomes select_by_id.ModelError."""

    def __init__(self, router, role, avoid_vendor=None):
        self.router, self.role, self.avoid_vendor = router, role, avoid_vendor
        self.name = f"role:{role}"

    def complete(self, prompt, max_tokens, seed):
        import select_by_id as SB
        try:
            r = self.router.call(self.role, prompt, max_tokens, seed, avoid_vendor=self.avoid_vendor)
        except ProviderError as e:
            raise SB.ModelError(str(e)[:300]) from None
        except ReplayMiss as e:
            raise SB.ReplayMiss(str(e)[:300]) from None
        except SpendLimit as e:
            raise SB.SpendLimit(str(e)) from None
        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "replayed": r.replayed,
                        "tried": r.tried}
