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
    that cannot answer raises Unavailable, with the reason."""
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
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
            last = type(e).__name__
            if wait is not None:
                time.sleep(wait)
                continue
            raise Unavailable(last) from None
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

    def upper_usd(self, prompt, max_tokens, system=None):
        """The call's spend upper bound: its prompt tokens (prompt_tokens_upper) + the output cap."""
        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": self.max_out(max_tokens)})

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
        return max(int(self.spec.get("min_out", 8000)), max_tokens * 8)       # a reasoning model thinks inside it

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
           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}


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
                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0):
        with open(config) as f:
            self.config = json.load(f)
        self.env_path = env_path or ENV_PATH
        self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
        if limit_basis not in ("estimate", "reported"):
            raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
        self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
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

    def chain(self, role):
        if role in self.chains:
            return list(self.chains[role])
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

    def _basis_total(self, d):
        """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
        bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
        estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
        its deadline, booked at its prompt tokens (ruling 83 (a), 20:33 Nov 13) until a late answer replaces it)."""
        if self.limit_basis == "reported":
            if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
                raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
                                 "cannot be read (fail closed; audit 0707 C1, glm P1-2)")
            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
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
        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late."""
        if not self.spend_path or b.free():
            return None
        with self._lock():
            d = self._ledger()
            held = sum(float(x) for x in d["reserved"].values())
            spent = self._basis_total(d)
            if spent + held + upper > self.limit_usd:
                raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's upper "
                                 f"bound {upper:.2f} > the limit {self.limit_usd} USD")
            key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
            d["reserved"][key] = round(upper, 6)
            self._save(d)
        return key

    def _settle(self, key, backend=None, usage=None, usd=0.0, role=""):
        """Release a reservation and account the call that answered (a free one too, when the ledger is readable)."""
        if not self.spend_path or (key is None and backend is None):
            return
        with self._lock():
            try:
                d = self._ledger()
            except SpendLimit:
                if key is None:
                    return                             # a free call: nothing to guard, nothing to write
                raise
            d["reserved"].pop(key, None)
            if backend is not None:
                usage = usage or {}
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
                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
                             reported_calls=b.get("reported_calls", 0) + 1)
                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
                else:                                  # no vendor figure: the estimate stands for this call
                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
            self._save(d)

    def _late(self, ab, value, error):
        """RULING 83 (a): an abandoned call that ended after its deadline (in its own thread). An answer is accounted
        as an on-time one would have been, in place of its prompt-token booking: the vendor's reported figure, or,
        with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
        line goes to the deadline log (item 55). The answer's text is never used or recorded."""
        b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
        rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
               "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": booked}
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
                if self.spend_path:
                    try:
                        self._replace_booking(b, role, booked, usage, usd, rep)
                        rec["replaced"] = True
                    except Exception as e:             # noqa: BLE001 (audit 2048 C1: on record; the prompt-token
                        rec.update(replaced=False,     # booking stands, the ledger written whole or not at all)
                                   ledger_error=f"{type(e).__name__}: {str(e)[:200]}")
        else:
            rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
        self._log_slow(rec)

    def _replace_booking(self, b, role, booked, usage, usd, rep):
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
            d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
            if _num(rep):
                bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
                          reported_calls=bb.get("reported_calls", 0) + 1)
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

    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
             avoid_family=None, deadline_s=None):
        av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
        tried, notices = [], []
        for name in self.chain(role):
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
            path = self._path(role, name, prompt, max_tokens, seed, system) if self.record_dir else None
            if path and os.path.exists(path):
                with open(path) as f:
                    rec = json.load(f)
                return Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
                             rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
            if self.replay:
                tried.append((name, "replay: not recorded"))
                continue
            upper = b.upper_usd(prompt, max_tokens, system)
            key = self._reserve(b, upper)
            if b.vendor == "heimdall":
                n = self.heimdall_tripwire()
                if n:
                    notices.append(n)

            def abandon(b=b, key=key, name=name):      # RULING 83 (a): booked at its PROMPT tokens (input rate), an
                booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
                                "deadline_s": deadline_s, "seconds": deadline_s,
                                "prompt_chars": len(prompt_text(prompt)),
                                "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
                self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
            try:
                if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system),
                                                on_abandon=abandon, on_late=self._late)
                else:
                    text, usage, secs = b.complete(prompt, max_tokens, seed, system)
            except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
                booked = b.prompt_usd(prompt, system)  # abandon()
                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
                                    "ruling 83 (a))"))
                continue
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
            usd = b.usd(usage)
            self._settle(key, b, usage, usd, role)
            if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
                self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
                                "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
                                "in": (usage or {}).get("in"),
                                "out": (usage or {}).get("out")})
            if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
                tried.append((name, "refused this request: an empty reply"))
                continue
            recorded = ""
            if path and isinstance(text, str) and text.strip():
                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
                                    "max_tokens": max_tokens, "system": system, "prompt": prompt_text(prompt),
                                    "text": text,
                                    "usage": usage, "usd": usd, "seconds": round(secs, 2)})
                recorded = path
            return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
                         recorded)
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
