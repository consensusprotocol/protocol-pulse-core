"""pipeline/ingest/providers.py: ONE provider interface for every model role (law L-x: NO SINGLE MODEL, ULTRON FIRST).

A role (mine, judge) is an ordered chain of interchangeable back-ends named in providers.json, the only place a vendor
or a model name appears. Router.run() tries the chain in order and returns the first reply that passes the role's
validator. Per back-end: bounded in-flight requests (and a global cap), queue-aware backoff on HTTP 429 / 503
provider_overloaded (Retry-After honoured), a circuit breaker on failures, malformed replies and slowness, and a daily
dollar budget. A reply is validated strictly and never repaired (law L-l); every attempt, accepted or not, goes to
on_attempt with its raw content.

SPEND FREEZE (orchestrator 05:30 ET 2026-11-12): every back-end names its vendor; a vendor listed in the config's
spend_freeze is never called by any role, whatever its chain, `only`, or `enabled` say (a stored validated reply costs
nothing and may still be reused). The spend meter only NOTIFIES (orchestrator 02:45; integrator B1): while it is not
'ok' the metered back-ends move to the end of every chain, so the others go first where any are available; they are
never taken out. AllBackendsFailed.outage tells a chain that was down or refusing (the caller waits, no try used) from
one whose back-ends answered and were rejected.

Keys are read by NAME from the env file named in the config, inside code; never logged, never in an exception (error
text is redacted of every key value before it is recorded), never sent after a redirect.
"""
import hashlib
import json
import os
import random
import socket
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field

from . import config


class BackendError(Exception):
    """kind: network | timeout | http_429 | overloaded | server | empty  (retried on the same back-end with backoff)
             routing | redirect | http_auth | http_4xx | refusal | disabled   (not retried: next back-end)
    REJECTED kinds are about this request (the back-end answered and refused or gave nothing usable): they count as a
    failed try of the work. Every other kind is the back-end being unavailable: the work waits."""
    RETRY = frozenset({"network", "timeout", "http_429", "overloaded", "server", "empty"})
    REJECTED = frozenset({"http_4xx", "refusal", "empty"})

    def __init__(self, kind, detail="", retry_after=None, http_status=None, latency_s=None, usage=None,
                 cost_usd=None, raw=None):
        super().__init__(f"{kind}: {detail}"[:500])
        self.kind, self.detail, self.retry_after, self.http_status = kind, str(detail)[:500], retry_after, http_status
        self.latency_s, self.usage, self.cost_usd, self.raw = latency_s, usage or {}, cost_usd, raw

    @property
    def retryable(self):
        return self.kind in self.RETRY


class Invalid(Exception):
    """A reply that is not exactly what the role asked for (law L-l): rejected, never repaired."""


class AllBackendsFailed(RuntimeError):
    """tried: [(back-end, status, why)]; status: skipped (not called: frozen, disabled, budget, circuit open),
    unavailable (called; down, overloaded, refusing access), rejected (called; its replies were rejected), unknown.
    outage: no back-end answered and was rejected; the work waits and retries, it never counts as a failed try."""

    def __init__(self, tried):
        super().__init__("every back-end failed or refused: " + "; ".join(f"{b} {s} ({w})" for b, s, w in tried))
        self.tried = tried
        self.outage = all(s != "rejected" for _, s, _ in tried)


@dataclass
class Reply:
    content: str
    model: str
    provider: object
    latency_s: float
    usage: dict
    cost_usd: float
    cost_basis: str
    finish_reason: object = None
    http_status: object = None
    request_id: object = None


@dataclass
class Outcome:
    obj: object
    backend: str
    model: str
    provider: object
    content: str
    attempt: int
    cached: bool
    prompt_sha256: str
    reply_sha256: str
    tried: list = field(default_factory=list)


def sha256(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()


def validate_config(cfg):
    """Strict: every back-end names its vendor (the spend freeze is per vendor), a freeze lists vendor names."""
    if cfg.get("schema") != "pp.providers/1":
        raise ValueError(f"providers config schema {cfg.get('schema')!r}")
    for bid, b in cfg["backends"].items():
        if type(b.get("vendor")) is not str or not b["vendor"]:
            raise ValueError(f"back-end {bid}: no 'vendor' (every back-end names its vendor: the spend freeze)")
    fz = cfg.get("spend_freeze")
    if fz is not None and (type(fz) is not dict or type(fz.get("vendors")) is not list
                           or not all(type(v) is str and v for v in fz["vendors"])):
        raise ValueError("spend_freeze must be an object with a 'vendors' list of vendor names")
    for role, r in cfg["roles"].items():
        for b in r["chain"]:
            if b not in cfg["backends"]:
                raise ValueError(f"role {role}: unknown back-end {b}")
    return cfg


def load_config(path=None):
    with open(path or config.PROVIDERS_PATH) as f:
        return validate_config(json.load(f))


def frozen_vendors(cfg):
    return frozenset((cfg.get("spend_freeze") or {}).get("vendors") or ())


def override_allowed(url, configured):
    """A runtime base-URL override may point only at this machine (drills) or at the configured host: the bearer key
    goes wherever the base points."""
    try:
        u, c = urllib.parse.urlsplit(url), urllib.parse.urlsplit(configured or "")
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    return u.hostname in ("127.0.0.1", "localhost", "::1") or (u.hostname == c.hostname and u.scheme == c.scheme)


class Keyring:
    """Values of named variables in the env file; never printed. name = exact, prefix = every NAME starting with it
    (deduplicated by value, in file order)."""

    def __init__(self, path):
        self._vals = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k.startswith("export "):
                        k = k[7:].strip()
                    v = v.strip().strip('"').strip("'")
                    if v:
                        self._vals.append((k, v))
        except OSError:
            pass

    def get(self, name=None, prefix=None):
        out = []
        for k, v in self._vals:
            if (name and k == name) or (prefix and k.startswith(prefix)):
                if v not in out:
                    out.append(v)
        return out

    def __repr__(self):
        return f"Keyring({len(self._vals)} values)"

    def redact(self, s):
        """s with every key value of the env file replaced (error text from a vendor is recorded; a key never is)."""
        if not isinstance(s, str) or not s:
            return s
        for _, v in self._vals:
            if len(v) >= 8 and v in s:
                s = s.replace(v, "[redacted]")
        return s


# ── back-ends ──

class Backend:
    def __init__(self, bid, cfg, keyring):
        self.id, self.cfg = bid, cfg
        self.model = cfg["model"]
        self.timeout = float(cfg.get("timeout_s", 240))
        self.max_inflight = int(cfg.get("max_inflight", 4))
        names = [cfg[k] for k in ("key_env",) if cfg.get(k)]
        self._keys = keyring.get(name=names[0]) if names else (
            keyring.get(prefix=cfg["key_env_prefix"]) if cfg.get("key_env_prefix") else [])
        self._ki = 0
        self._klock = threading.Lock()
        self._keyring = keyring

    def __repr__(self):
        return f"{type(self).__name__}({self.id}, {self.model})"

    def redact(self, s):
        return self._keyring.redact(s) if self._keyring is not None else s

    def release(self):
        """End of a cycle: free what this back-end holds (the local model unloads; HTTP back-ends hold nothing)."""

    @property
    def model_label(self):
        return f"{self.id}:{self.model}"

    def enabled(self):
        return bool(self.cfg.get("enabled", True))

    def _key(self):
        if not self._keys:
            raise BackendError("disabled", f"no key named in the config is present in the env file ({self.id})")
        with self._klock:
            k = self._keys[self._ki % len(self._keys)]
            self._ki += 1
        return k

    def price_cost(self, usage):
        """Dollars from the price table. Output counts hidden reasoning too: some vendors report it only inside
        total_tokens (2026-11-12: completion 314, total 9,697 on a 2,371-token prompt)."""
        p = self.cfg.get("price") or {}
        i = float(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        o = float(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        tot = usage.get("total_tokens")
        if isinstance(tot, (int, float)) and tot - i > o:
            o = float(tot - i)
        return (i * float(p.get("in_per_mtok", 0)) + o * float(p.get("out_per_mtok", 0))) / 1e6

    def complete(self, prompt, schema, max_tokens):
        raise NotImplementedError


def _http_error(e, t0):
    status = e.code
    try:
        body = e.read()[:4000].decode("utf-8", "replace")
    except Exception:
        body = ""
    ra = e.headers.get("Retry-After") if e.headers else None
    try:
        ra = float(ra) if ra is not None else None
    except ValueError:
        ra = None
    lat = time.time() - t0
    etype = ""
    try:
        j = json.loads(body)
        err = j.get("error") if isinstance(j, dict) else None
        etype = (err or {}).get("error_type") or (err or {}).get("type") or "" if isinstance(err, dict) else ""
        if not etype and isinstance(j, dict):
            etype = j.get("error_type") or ""
    except ValueError:
        pass
    low = body.lower()
    if 300 <= status < 400:
        return BackendError("redirect", f"HTTP {status} redirect refused (the key never follows a redirect)", ra,
                            status, lat)
    if status in (401, 402, 403):
        return BackendError("http_auth", body[:300], ra, status, lat)
    if status == 429:
        return BackendError("http_429", body[:300], ra, status, lat)
    if status == 503 and (etype == "routing_error" or "no endpoints" in low or "unsupported" in low):
        return BackendError("routing", body[:300], ra, status, lat)
    if status == 503 and (etype == "provider_overloaded" or "too many requests waiting" in low):
        return BackendError("overloaded", body[:300], ra, status, lat)
    if status == 529:
        return BackendError("overloaded", body[:300], ra, status, lat)
    if status >= 500:
        return BackendError("server", body[:300], ra, status, lat)
    return BackendError("http_4xx", body[:300], ra, status, lat)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None                     # urllib would re-send the Authorization header to the new location


_OPENER = urllib.request.build_opener(_NoRedirect)


class OpenAICompatBackend(Backend):
    """OpenAI-compatible chat completions (OpenRouter-style gateways included): POST {base}/chat/completions.
    base: the runtime override file (Overrides, the service's outage drills and endpoint moves without a restart), else
    the config's base_url_env variable, else base_url."""
    overrides = None

    @property
    def base(self):
        o = self.overrides.get(self.id, "base_url") if self.overrides else None
        if o and not override_allowed(o, self.cfg.get("base_url")):
            o = None                    # refused (the service logs the refusal when the override file changes)
        env = self.cfg.get("base_url_env")
        return (o or (os.environ.get(env) if env else None) or self.cfg["base_url"]).rstrip("/")

    def _request(self, path, body=None, timeout=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method="POST" if data else "GET", headers={
            "Authorization": "Bearer " + self._key(), "Content-Type": "application/json",
            "User-Agent": "pp-ingest/1"})
        t0 = time.time()
        try:
            with _OPENER.open(req, timeout=timeout or self.timeout) as r:
                return r.status, r.read(), dict(r.headers), time.time() - t0
        except urllib.error.HTTPError as e:
            raise _http_error(e, t0)
        except (socket.timeout, TimeoutError) as e:
            raise BackendError("timeout", f"{type(e).__name__}", latency_s=time.time() - t0)
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            raise BackendError("network", f"{type(e).__name__}: {getattr(e, 'reason', e)}",
                               latency_s=time.time() - t0)

    def get_json(self, path, timeout=30):
        status, raw, _, _ = self._request(path, timeout=timeout)
        return json.loads(raw)

    def complete(self, prompt, schema, max_tokens):
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                "max_tokens": int(max_tokens), "temperature": 0}
        if self.cfg.get("json_schema") and schema:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "reply", "strict": True, "schema": schema}}
        body.update(self.cfg.get("extra_body") or {})
        status, raw, headers, lat = self._request("/chat/completions", body)
        try:
            j = json.loads(raw)
            ch = j["choices"][0]
            msg = ch.get("message") or {}
            content = msg.get("content")
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise BackendError("server", f"unreadable response body: {type(e).__name__}", http_status=status,
                               latency_s=lat, raw=raw[:2000].decode("utf-8", "replace"))
        usage = j.get("usage") or {}
        if self.cfg.get("cost_from_usage") and isinstance(usage.get("cost"), (int, float)):
            cost, basis = float(usage["cost"]), "usage.cost"
        elif isinstance(usage.get("cost_in_usd_ticks"), (int, float)):      # vendor-reported; 1 USD = 1e10 ticks
            cost, basis = float(usage["cost_in_usd_ticks"]) / 1e10, "usage.cost_in_usd_ticks"
        else:
            cost, basis = self.price_cost(usage), (self.cfg.get("price") or {}).get("basis", "price table")
        if not isinstance(content, str) or not content.strip():
            raise BackendError("empty", f"no content (finish_reason {ch.get('finish_reason')})", http_status=status,
                               latency_s=lat, usage=usage, cost_usd=cost)
        return Reply(content, j.get("model") or self.model, j.get("provider"), lat, usage, cost, basis,
                     ch.get("finish_reason"), status, headers.get("x-request-id") or j.get("id"))


class AnthropicBackend(Backend):
    """The Anthropic Messages API through the official SDK; structured output (output_config.format) as the schema."""

    def complete(self, prompt, schema, max_tokens):
        import anthropic
        client = anthropic.Anthropic(api_key=self._key(), max_retries=0, timeout=self.timeout)
        oc = {"effort": self.cfg.get("effort", "low")}
        if schema:
            oc["format"] = {"type": "json_schema", "schema": schema}
        kw = dict(model=self.model, max_tokens=int(max_tokens), output_config=oc,
                  messages=[{"role": "user", "content": prompt}])
        fb = self.cfg.get("server_fallbacks")
        t0 = time.time()
        try:
            if fb:
                resp = client.beta.messages.create(**kw, betas=[fb["beta"]], extra_body={"fallbacks": fb["value"]})
            else:
                resp = client.messages.create(**kw)
        except anthropic.RateLimitError as e:
            ra = e.response.headers.get("retry-after") if getattr(e, "response", None) is not None else None
            raise BackendError("http_429", str(e)[:300], float(ra) if ra else None, 429, time.time() - t0)
        except anthropic.APITimeoutError as e:
            raise BackendError("timeout", str(e)[:200], latency_s=time.time() - t0)
        except anthropic.APIConnectionError as e:
            raise BackendError("network", str(e)[:200], latency_s=time.time() - t0)
        except anthropic.APIStatusError as e:
            code = getattr(e, "status_code", 0) or 0
            kind = "overloaded" if code == 529 else ("server" if code >= 500 else "http_4xx")
            raise BackendError(kind, str(e)[:300], http_status=code, latency_s=time.time() - t0)
        lat = time.time() - t0
        u = resp.usage
        usage = {"input_tokens": getattr(u, "input_tokens", 0) or 0,
                 "output_tokens": getattr(u, "output_tokens", 0) or 0,
                 "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
        cost = self.price_cost({"input_tokens": usage["input_tokens"] + usage["cache_creation_input_tokens"]
                                + usage["cache_read_input_tokens"], "output_tokens": usage["output_tokens"]})
        if resp.stop_reason == "refusal":
            raise BackendError("refusal", str(getattr(resp, "stop_details", "")), latency_s=lat, usage=usage,
                               cost_usd=cost)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if not text.strip():
            raise BackendError("empty", f"no text (stop_reason {resp.stop_reason})", latency_s=lat, usage=usage,
                               cost_usd=cost)
        return Reply(text, resp.model, self.cfg.get("vendor"), lat, usage, cost,
                     (self.cfg.get("price") or {}).get("basis", "price table"), resp.stop_reason, 200,
                     getattr(resp, "_request_id", None) or resp.id)


class GeminiBackend(Backend):
    def complete(self, prompt, schema, max_tokens):
        from google import genai
        from google.genai import errors as gerr
        client = genai.Client(api_key=self._key(), http_options={"timeout": int(self.timeout * 1000)})
        t0 = time.time()
        conf = {"max_output_tokens": int(max_tokens), "temperature": 0}
        if schema:                         # JSON only when the role asks for it, constrained by the role's schema
            conf.update(response_mime_type="application/json", response_json_schema=schema)
        try:
            resp = client.models.generate_content(model=self.model, contents=prompt, config=conf)
        except gerr.APIError as e:
            code = getattr(e, "code", 0) or 0
            kind = "http_429" if code == 429 else ("server" if code >= 500 else "http_4xx")
            raise BackendError(kind, str(e)[:300], http_status=code, latency_s=time.time() - t0)
        except Exception as e:
            raise BackendError("network", f"{type(e).__name__}: {e}"[:300], latency_s=time.time() - t0)
        lat = time.time() - t0
        um = getattr(resp, "usage_metadata", None)
        usage = {"prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
                 "completion_tokens": (getattr(um, "candidates_token_count", 0) or 0)
                 + (getattr(um, "thoughts_token_count", 0) or 0)}
        cost = self.price_cost(usage)
        text = getattr(resp, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise BackendError("empty", "no text", latency_s=lat, usage=usage, cost_usd=cost)
        return Reply(text, getattr(resp, "model_version", None) or self.model, self.cfg.get("vendor"), lat, usage, cost,
                     (self.cfg.get("price") or {}).get("basis", "estimate"), None, 200, None)


class OllamaLocalBackend(Backend):
    """The local model on Ultron GPU0 through story_semantics.LocalLLM. Available only when enabled in the config AND
    this process holds the GPU0 lease: gpu0.held() is a check, never an acquisition (integrator B3); LocalLLM._post
    itself calls gpu0.require() and swap_to on every request (law L-r, main 4867a74a). Where pipeline/gpu0.py is absent
    the back-end is never available. release() unloads this run's model (LocalLLM.stop) at the end of a cycle."""

    def __init__(self, bid, cfg, keyring):
        super().__init__(bid, cfg, keyring)
        self._llm = None
        self._llm_lock = threading.Lock()

    @staticmethod
    def _gpu0():
        try:
            import gpu0
            return gpu0
        except ImportError:
            return None

    def enabled(self):
        if not self.cfg.get("enabled"):
            return False
        g = self._gpu0()
        return bool(g is not None and g.held())

    def complete(self, prompt, schema, max_tokens):
        if not self.cfg.get("enabled"):
            raise BackendError("disabled", "local back-end disabled in providers.json")
        if not self.enabled():
            raise BackendError("disabled", "GPU0 lease not held by this process (or pipeline/gpu0.py absent): the "
                                           "local back-end runs only under the lease (law L-r)")
        import story_semantics as sm
        with self._llm_lock:
            if self._llm is None:
                self._llm = sm.LocalLLM(model=self.model).start()
            llm = self._llm
        t0 = time.time()
        try:
            text = llm._post(prompt, int(max_tokens), seed=7)
        except Exception as e:                        # a GPU0 stop (BaseException) is never renamed: it propagates
            raise BackendError("server", f"{type(e).__name__}: {e}"[:300], latency_s=time.time() - t0)
        lat = time.time() - t0
        if not isinstance(text, str) or not text.strip():
            raise BackendError("empty", "no content", latency_s=lat)
        return Reply(text, f"{self.model}@{getattr(llm, 'digest', None)}", self.cfg.get("vendor"), lat, {}, 0.0,
                     "local", None, 200, None)

    def release(self):
        with self._llm_lock:
            llm, self._llm = self._llm, None
        if llm is not None and hasattr(llm, "stop"):
            llm.stop()


class Overrides:
    """{back-end id: {"base_url": ...}} from a JSON file, re-read when its mtime changes; on_change(old, new) is
    called on every change (the service records it as an event). A missing or unreadable file = no overrides. A base
    URL is honoured only for this machine or the configured host (override_allowed)."""

    def __init__(self, path, on_change=None):
        self.path, self.on_change = path, on_change
        self.mtime, self.data = None, {}
        self.lock = threading.Lock()

    def get(self, bid, key):
        with self.lock:
            try:
                m = os.path.getmtime(self.path)
            except OSError:
                m = None
            if m != self.mtime:
                try:
                    with open(self.path) as f:
                        new = json.load(f) if m is not None else {}
                    new = new if isinstance(new, dict) else {}
                except (OSError, ValueError):
                    new = {}
                old, self.data, self.mtime = self.data, new, m
                if old != new and self.on_change:
                    self.on_change(old, new)
            v = self.data.get(bid)
            return v.get(key) if isinstance(v, dict) else None


KINDS = {"openai_compat": OpenAICompatBackend, "anthropic": AnthropicBackend, "gemini": GeminiBackend,
         "ollama_local": OllamaLocalBackend}


def make_backend(bid, cfg, keyring):
    return KINDS[cfg["kind"]](bid, cfg, keyring)


# ── health, throttle, spend ──

class Health:
    """Circuit breaker: OPEN after N consecutive failures, or a failure fraction over the last calls inside a time
    window, or a slow median latency; one half-open probe after open_s."""

    def __init__(self, cfg, clock=time.time):
        self.c, self.clock = cfg, clock
        self.events = deque(maxlen=50)
        self.consec = 0
        self.open_until = 0.0
        self.probing = False
        self.opened = 0
        self.why = ""
        self.lock = threading.Lock()

    def allow(self):
        with self.lock:
            now = self.clock()
            if self.open_until == 0.0:
                return True, ""
            if now < self.open_until:
                return False, f"circuit open ({self.why}) for {self.open_until - now:.0f} s"
            if self.probing:
                return False, "circuit half-open: a probe is in flight"
            self.probing = True
            return True, "half-open probe"

    def record(self, ok, latency_s=None, kind=""):
        """Failure rules are judged on a failure, the latency rule on a success; a success that closes the circuit
        starts a fresh window (the outage's failures never re-open a recovered back-end)."""
        with self.lock:
            now = self.clock()
            if ok and self.open_until:
                self.open_until, self.probing, self.why = 0.0, False, ""
                self.events.clear()
            self.events.append((now, bool(ok), latency_s, kind))
            if not ok and self.open_until and self.probing:
                self._open(now, f"half-open probe failed ({kind})")
                return
            recent = [e for e in self.events if now - e[0] <= self.c["window_s"]][-self.c["window"]:]
            if ok:
                self.consec = 0
                lats = [e[2] for e in recent if e[1] and e[2] is not None]
                if len(lats) >= self.c["window"] and statistics.median(lats) > self.c["slow_median_s"]:
                    self._open(now, f"median latency {statistics.median(lats):.0f} s")
                return
            self.consec += 1
            fails = sum(1 for e in recent if not e[1])
            if self.consec >= self.c["consecutive_failures"]:
                self._open(now, f"{self.consec} consecutive failures, last {kind}")
            elif len(recent) >= self.c["window"] and fails / len(recent) >= self.c["failure_fraction"]:
                self._open(now, f"{fails}/{len(recent)} failures, last {kind}")

    def _open(self, now, why):
        self.open_until, self.probing, self.why = now + self.c["open_s"], False, why
        self.opened += 1

    def snapshot(self):
        with self.lock:
            return {"open": bool(self.open_until), "why": self.why, "consecutive_failures": self.consec,
                    "opened_count": self.opened, "recent": len(self.events)}


class Throttle:
    """Queue-aware backoff shared by every thread of one back-end: a 429 / overloaded answer pauses them all."""

    def __init__(self, cfg, clock=time.time, sleep=time.sleep):
        self.first, self.max = float(cfg["first_s"]), float(cfg["max_s"])
        self.delay, self.until = self.first, 0.0
        self.clock, self.sleep = clock, sleep
        self.lock = threading.Lock()
        self.hits = 0

    def wait(self):
        while True:
            with self.lock:
                left = self.until - self.clock()
            if left <= 0:
                return
            self.sleep(min(left, 5.0))

    def hit(self, retry_after=None):
        with self.lock:
            self.hits += 1
            d = float(retry_after) if retry_after else self.delay
            self.delay = min(max(self.delay * 2, self.first), self.max)
            self.until = max(self.until, self.clock() + min(d, self.max) * (1 + random.random() * 0.25))

    def ok(self):
        with self.lock:
            self.delay = self.first


class SpendBook:
    """Dollars per back-end per UTC day (from every attempt's cost)."""

    def __init__(self, loader=None, clock=time.time):
        self.clock, self.lock = clock, threading.Lock()
        self.day, self.spent = None, {}
        self.loader = loader

    def _roll(self):
        day = time.strftime("%Y-%m-%d", time.gmtime(self.clock()))
        if day != self.day:
            self.day, self.spent = day, dict(self.loader(day) if self.loader else {})

    def add(self, bid, usd):
        if not usd:
            return
        with self.lock:
            self._roll()
            self.spent[bid] = self.spent.get(bid, 0.0) + float(usd)

    def today(self, bid):
        with self.lock:
            self._roll()
            return self.spent.get(bid, 0.0)


# ── the router ──

class Router:
    def __init__(self, cfg=None, keyring=None, spend=None, meter=None, on_attempt=None, cache_dir=None,
                 clock=time.time, sleep=time.sleep, backends=None, overrides=None):
        self.cfg = validate_config(cfg or load_config())
        self.keyring = keyring or Keyring(self.cfg["env_file"])
        self.backends = backends or {bid: make_backend(bid, c, self.keyring)
                                     for bid, c in self.cfg["backends"].items()}
        for b in self.backends.values():
            if isinstance(b, OpenAICompatBackend) and overrides is not None:
                b.overrides = overrides
        self.health = {bid: Health(self.cfg["health"], clock) for bid in self.backends}
        self.throttle = {bid: Throttle(self.cfg["throttle"], clock, sleep) for bid in self.backends}
        self.sems = {bid: threading.BoundedSemaphore(min(b.max_inflight, self.cfg["global"]["max_inflight"]))
                     for bid, b in self.backends.items()}
        self.gsem = threading.BoundedSemaphore(int(self.cfg["global"]["max_inflight"]))
        self.spend = spend or SpendBook(clock=clock)
        self.meter, self.on_attempt, self.cache_dir = meter, on_attempt, cache_dir
        self.clock, self.sleep = clock, sleep

    def chain(self, role):
        return list(self.cfg["roles"][role]["chain"])

    def vendor(self, bid):
        return (self.cfg["backends"].get(bid) or {}).get("vendor")

    def frozen(self, bid):
        """True when the back-end's vendor is under the spend freeze (or it names none: fail closed)."""
        v = self.vendor(bid)
        return v is None or v in frozen_vendors(self.cfg)

    def _metered(self, bid):
        return bool((self.cfg["backends"].get(bid) or {}).get("spend_meter"))

    def order(self, role):
        """The role's chain as tried now. While the spend meter is not 'ok' (90 % of the cap, or unmeasured) the
        metered back-ends go last: the others first where any are available; the metered ones are never removed."""
        ch = self.chain(role)
        if self.meter is not None and self.meter.state() != "ok":
            ch = [b for b in ch if not self._metered(b)] + [b for b in ch if self._metered(b)]
        return ch

    def effective(self, role):
        """The back-ends of the role that may be called at all (not frozen, enabled), in order."""
        return [b for b in self.order(role) if b in self.backends and not self.frozen(b) and
                self.backends[b].enabled()]

    def available(self, bid):
        b = self.backends[bid]
        if self.frozen(bid):
            return False, f"spend freeze: vendor {self.vendor(bid)!r} is frozen (providers.json spend_freeze)"
        if not b.enabled():
            return False, "disabled"
        budget = b.cfg.get("daily_budget_usd")
        if budget is not None and self.spend.today(bid) >= float(budget):
            return False, f"daily budget ${budget} used (${self.spend.today(bid):.2f})"
        return self.health[bid].allow()

    def release(self):
        """End of a cycle: every back-end frees what it holds (the local model is unloaded)."""
        for b in self.backends.values():
            rel = getattr(b, "release", None)
            if rel is not None:
                rel()

    def _cache_path(self, bid, key):
        return os.path.join(self.cache_dir, bid, key[:2], key + ".json") if self.cache_dir else None

    def _emit(self, rec):
        if self.on_attempt:
            try:
                self.on_attempt(rec)
            except Exception:
                pass                   # logging never decides a call; the caller's stats show the gap

    def run(self, role, prompt, schema, validate, tag=None, only=None, use_cache=True):
        """The first back-end of the role's chain (or `only`) whose reply passes validate(content) -> obj."""
        rc = self.cfg["roles"][role]
        chain = [only] if only else self.order(role)
        tried = []
        max_tokens = int(rc.get("max_tokens", 4000))
        for bid in chain:
            if bid not in self.backends:
                tried.append((bid, "unknown", "not in providers.json"))
                continue
            mt = max(max_tokens, int(self.backends[bid].cfg.get("max_tokens_floor", 0)))
            if use_cache and self.backends[bid].enabled():       # a stored validated reply costs nothing and
                out = self._cached(bid, role, prompt, schema, validate, tag, mt)   # proves nothing about health
                if out is not None:
                    out.tried = tried + [(bid, "ok", "cache")]
                    return out
            ok, why = self.available(bid)
            if not ok:
                tried.append((bid, "skipped", why))
                continue
            try:
                out = self._try(bid, role, prompt, schema, validate, tag, int(rc.get("attempts", 3)), mt)
            except BaseException:
                self.health[bid].record(False, None, "crash")      # a half-open probe is never left in flight
                raise
            if isinstance(out, Outcome):
                out.tried = tried + [(bid, "ok", f"attempt {out.attempt}")]
                return out
            tried.append((bid,) + out)
        raise AllBackendsFailed(tried)

    def _key(self, bid, prompt, schema, max_tokens):
        return sha256(json.dumps([bid, self.backends[bid].model, sha256(prompt), json.dumps(schema, sort_keys=True),
                                  max_tokens]))

    def _cached(self, bid, role, prompt, schema, validate, tag, max_tokens):
        path = self._cache_path(bid, self._key(bid, prompt, schema, max_tokens))
        if not (path and os.path.exists(path)):
            return None
        try:
            with open(path) as f:
                c = json.load(f)
            obj = validate(c["content"])
        except Exception:
            return None                 # unreadable or no longer valid under today's validator: ask again
        psha = sha256(prompt)
        self._emit({"role": role, "backend": bid, "model": c["model"], "provider": c.get("provider"), "tag": tag,
                    "attempt": 0, "kind": "cache", "prompt_sha256": psha, "base_prompt_sha256": psha,
                    "reply_sha256": sha256(c["content"]), "cost_usd": 0.0, "latency_s": 0.0})
        return Outcome(obj, bid, c["model"], c.get("provider"), c["content"], c.get("attempt", 1), True,
                       psha, sha256(c["content"]))

    def _try(self, bid, role, prompt, schema, validate, tag, attempts, max_tokens):
        """An Outcome, or (status, why): status 'rejected' (this request: replies invalid, refused, empty, a 4xx) or
        'unavailable' (the back-end: down, overloaded, refusing access)."""
        if self.frozen(bid):                                     # never reached through run(); a second lock
            return "unavailable", f"spend freeze: vendor {self.vendor(bid)!r} is frozen"
        b, h, th = self.backends[bid], self.health[bid], self.throttle[bid]
        psha = sha256(prompt)
        path = self._cache_path(bid, self._key(bid, prompt, schema, max_tokens))
        transport_left = int(self.cfg["throttle"]["transport_retries"])
        attempt, why = 0, ""
        p = prompt
        while attempt < attempts:
            th.wait()
            rec = {"role": role, "backend": bid, "model": b.model, "tag": tag, "attempt": attempt + 1,
                   "prompt_sha256": sha256(p), "base_prompt_sha256": psha}
            with self.sems[bid], self.gsem:          # back-end slot first: a queue on one back-end never holds the
                try:                                  # global slots the others need
                    r = b.complete(p, schema, max_tokens)
                except BackendError as e:
                    r = e
                except Exception as e:                # an unexpected client exception is a failed call, named
                    r = BackendError("server", f"unexpected {type(e).__name__}: {e}")
            if isinstance(r, BackendError):
                red = getattr(b, "redact", None)
                if red is not None:
                    r.detail, r.raw = red(r.detail), red(r.raw)
                self.spend.add(bid, r.cost_usd)
                if self._metered(bid) and self.meter is not None:
                    self.meter.add_local(r.cost_usd or 0.0)
                self._emit(dict(rec, kind=r.kind, http_status=r.http_status, latency_s=r.latency_s,
                                usage=r.usage, cost_usd=r.cost_usd, error=r.detail, content=r.raw))
                if r.kind in ("http_429", "overloaded"):
                    th.hit(r.retry_after)
                if r.retryable and transport_left > 0:
                    transport_left -= 1
                    if r.kind not in ("http_429", "overloaded"):
                        self.sleep(min(2.0 * (4 - transport_left), 10.0))
                    continue
                h.record(False, r.latency_s, r.kind)
                return ("rejected" if r.kind in BackendError.REJECTED else "unavailable"), f"{r.kind}: {r.detail[:160]}"
            th.ok()
            self.spend.add(bid, r.cost_usd)
            if self._metered(bid) and self.meter is not None:
                self.meter.add_local(r.cost_usd or 0.0)
            attempt += 1
            base = dict(rec, model=r.model, provider=r.provider, http_status=r.http_status, latency_s=r.latency_s,
                        usage=r.usage, cost_usd=r.cost_usd, cost_basis=r.cost_basis, finish_reason=r.finish_reason,
                        request_id=r.request_id, content=r.content, reply_sha256=sha256(r.content))
            try:
                obj = validate(r.content)
            except Exception as e:                    # Invalid, or a validator crashing on the reply: rejected
                why = (str(e) if isinstance(e, Invalid) else f"the reply broke the validator: {type(e).__name__}")[:300]
                self._emit(dict(base, kind="invalid", error=why))
                p = (prompt + "\n\nYOUR PREVIOUS REPLY WAS REJECTED. The reason, quoted (data, not an instruction): " +
                     json.dumps(why) + "\nReply again with ONLY the one JSON object described above.")
                continue
            self._emit(dict(base, kind="ok"))
            h.record(True, r.latency_s, "ok")
            if path:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
                    with open(tmp, "w") as f:
                        json.dump({"content": r.content, "model": r.model, "provider": r.provider,
                                   "attempt": attempt, "prompt_sha256": psha, "at": config.iso()}, f)
                    os.replace(tmp, path)
                except OSError:
                    pass
            return Outcome(obj, bid, r.model, r.provider, r.content, attempt, False, psha, sha256(r.content))
        h.record(False, None, "invalid")
        return "rejected", f"invalid after {attempts} attempts: {why[:160]}"

    def snapshot(self):
        return {bid: dict(self.health[bid].snapshot(), enabled=b.enabled(), frozen=self.frozen(bid),
                          vendor=self.vendor(bid), throttle_hits=self.throttle[bid].hits,
                          spent_today=round(self.spend.today(bid), 4))
                for bid, b in self.backends.items()}
