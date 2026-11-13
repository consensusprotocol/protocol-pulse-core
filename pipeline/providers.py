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

    def upper_usd(self, prompt, max_tokens, system=None):
        """The call's spend upper bound: every prompt character a token (a safe over-estimate) + the output cap."""
        return self.usd({"in": len(prompt) + len(system or "") + 200, "out": self.max_out(max_tokens)})

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


def _num(x):
    import math
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def _reported(usd):
    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
    the price-table estimate for it, labelled as an estimate)."""
    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}


class HeimdallBackend(OpenAIBackend):
    """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
    vendor = "heimdall"

    def _base(self):
        if not self.spec.get("base_url"):
            raise Unavailable("heimdall: no base_url in the config")
        return self.spec["base_url"].rstrip("/")

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key("HEIMDALL_API_KEY")
        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
                "temperature": self.spec.get("temperature", 0),
                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
                             {"role": "user", "content": prompt}]}
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


VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
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
                 local_llm=None, chains=None):
        with open(config) as f:
            self.config = json.load(f)
        self.env_path = env_path or ENV_PATH
        self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
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

    def _reserve(self, b, upper):
        """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
        SpendLimit when spent + reserved + this call's upper bound would pass the limit."""
        if not self.spend_path or b.free():
            return None
        with self._lock():
            d = self._ledger()
            held = sum(float(x) for x in d["reserved"].values())
            if d["usd_estimate"] + held + upper > self.limit_usd:
                raise SpendLimit(f"spend estimate {d['usd_estimate']:.2f} USD + reserved {held:.2f} + this call's upper "
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
             avoid_family=None):
        av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
        tried, notices = [], []
        for name in self.chain(role):
            b = self.backends.get(name)
            why = self._skip(name, b, av, am, af)
            if why is None and isinstance(b, STTBackend):
                why = "a transcription back-end (Router.transcribe)"
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
            key = self._reserve(b, b.upper_usd(prompt, max_tokens, system))
            if b.vendor == "heimdall":
                n = self.heimdall_tripwire()
                if n:
                    notices.append(n)
            try:
                text, usage, secs = b.complete(prompt, max_tokens, seed, system)
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
            if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
                tried.append((name, "refused this request: an empty reply"))
                continue
            recorded = ""
            if path and isinstance(text, str) and text.strip():
                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
                                    "max_tokens": max_tokens, "system": system, "prompt": prompt, "text": text,
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
