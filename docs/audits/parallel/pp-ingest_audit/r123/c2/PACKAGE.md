# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 37150995
# The change under review: git diff HEAD (working tree) of pipeline/ingest, tools/ingest_watch.py, tests/ingest

## GOVERNING LAWS (this code MUST comply with every law below: flag any violation)
Standing order (PBX 02:30 / orchestrator 02:45 ET 2026-11-12) and laws this code must obey:
- BUILD: continuous ingest of every registered partner channel (RSS first, yt-dlp metadata fallback, ~10 min, ETag /
  backoff, last-seen ledger, re-upload / duplicate detection, Shorts and live-in-progress handled explicitly, durable
  queue); captions into the SAME transcript store format via the store's writer, in a staging copy, never the main
  tree; first-pass mining by sentence ids on Heimdall (bounded concurrency, queue-aware backoff on 429/503, <= ~20 in
  flight, spend tracked vs the $460 cap with a 90 % tripwire that NOTIFIES and falls back, never halts); an
  append-only moment ledger matching pp-selectid's pp.moment/1 contract and an adapter "best unused moments since T";
  a daily coverage check; a blind A/B of back-ends (generator and judge different models).
- L-x NO SINGLE MODEL, ULTRON FIRST: every model role behind ONE provider interface with >= 2 interchangeable
  back-ends; the run continues when any one vendor is down or out of credit; no vendor / model name outside the
  provider config; the local model on Ultron is the default where it meets the bar (it runs only under the GPU0
  lease, which this builder never holds: no GPU use at all here).
- L-l a model reply counts only whole: strict schema, ids validated, NOTHING REPAIRED; a failed call is never a
  default, a pass or an agreement. L-j / L-m: fail closed; nothing measured is never a pass.
- L-h / L-k: transcript text is read as spoken (entities decoded, split tokens joined) through the repo's canonical
  form; stored records are never rewritten. L-e: word timing for anything heard (the packager's job at cut time).
- L-u hard exclusions (accusation, partner attack, buy/sell imperative, guaranteed return, single-source breaking, ad
  read, third-party media) are flagged and excluded before ranking; L-v: a moment never spans a speaker change;
  re-uploads excluded; time-sensitive language needs the original publish time.
- Secrets: keys read by name from the env file inside code; never printed, logged or written.
- SPEND FREEZE (orchestrator 05:30 ET Nov 12, until told otherwise): paid frontier vendors (OpenAI, Anthropic, xAI;
  Google by the builder's assumption) are never called by any role; the watcher's mine chain is Heimdall then the
  local interface ONLY; if both are down the videos queue and are mined later, never on a paid frontier model; Heimdall
  mining continues; the 90 % tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of STATE), never a halt.
Only report issues you can verify from the code provided. Do not speculate. Cite file:line.

## THE CHANGE UNDER REVIEW: its orders and design
# r123: the miner's last fallback, the local model on a free card under the lease (Nov 17, 21:xx ET)

## Why (the order and the law)
- The orchestrator's 10:50 ET order of Nov 16 (2), ruling 118: "Plan B for mining ... is the next Heimdall model (qwen,
  then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model on a free card under the
  lease." The chains have ended with the local back-end since r118, but it could never be called: it was "available"
  only while this process already held the GPU0 lease (gpu0.held()), and this watcher never takes one (nor has
  pipeline/gpu0.py in its worktree), so it was dead code.
- Law L-r (main pipeline/gpu0.py, PBX 2026-11-12): EVERY GPU HAS ONE OWNER AT A TIME. GPU0 = renders and the gates that
  need render-side models; GPU1 = everything else (the word-pass worker, the website's fallback, the watchdog / morning
  brief / stage broadcast models). A caller that only asks a GPU's model server (loads nothing itself) uses
  gpu0.ollama_call(gpu, ...). Code outside a run reaches GPU1 through the main tree's services/gpu_lease_client.py.
- Builds come first on GPU0 (the 13:05 ET ruling of Nov 16, R13). So: GPU1 only.
- Integrator B3 (Nov 13): no environment string stands in for custody; availability is a check, never an acquisition.

## The change
- pipeline/ingest/providers.py: OllamaLocalBackend rewritten. enabled() = the config's "enabled" AND the client file
  exists (a check: no load, no lease). complete(): loads the main tree's client by file path under a private module
  name (lease_client(): checked for Gpu1Unavailable and chat_gpu1's signature; never kept when not that API), leaves
  the card free for yield_s after the previous request that reached it, then chat_gpu1(model, [user prompt], LEASE_OWNER,
  options {temperature 0, seed 7, num_ctx, num_predict = the role's max_tokens}, fmt "json", wait_s = lease_wait_s,
  timeout = timeout_s). client.Gpu1Unavailable -> BackendError("busy") (a new kind: not retried, not REJECTED, so the
  router reports "unavailable" and the work waits); the request's own errors as for the HTTP back-ends (HTTPError ->
  _http_error, timeout, network), anything else "server". release() is the base no-op (nothing is held between
  requests).
- pipeline/ingest/providers.json: local_gemma enabled, vendor ultron-gpu1, lease_wait_s 60, yield_s 3, num_ctx 16384
  (the pipeline LocalLLM's setting, at which gpu0.REQUIREMENT_MIB was measured), timeout_s 300, max_inflight 1.
- tests/ingest/conftest.py: an autouse guard: every test's lease client is a refusing stand-in cached under the private
  module name, and LEASE_CLIENT names a stand-in file whose import raises SystemExit; no test can take a real lease.
- tests/ingest/test_r123.py (new) and test_providers.py (the GPU0-era tests of the local back-end removed; the cache
  test follows the new design; the real config's effective chain now includes the local back-end).

## Unchanged code the change relies on (not in the diff)
- pipeline/ingest/providers.py:976-1020 Router._try: `except BackendError as e` (997) records the kind; `except
  Exception` (999) turns an unexpected exception into BackendError("server") (retryable); `r.retryable and
  transport_left > 0` (1014) retries RETRY kinds only; (1020) "rejected" if kind in REJECTED else "unavailable".
  Router.run (887) `except BaseException` (919) records the breaker and RE-RAISES: a BaseException from complete()
  would leave the chain and the miner's thread, which is why the GPU stops must be renamed before they reach it.
- pipeline/ingest/providers.py:819 one BoundedSemaphore per back-end of min(max_inflight, global): with max_inflight 1
  one thread at a time is inside OllamaLocalBackend.complete().
- pipeline/ingest/downsignal.py:178-182 Signal.noted: a back-end whose vendor is not the gateway's is never noted (the
  local back-end never feeds the outage clock).
- /home/ultron/protocol_pulse/pipeline/word_pass_worker.py:67,368: LEASE_WAIT_S = 1800; `gpu0.lease(OWNER,
  wait_s=LEASE_WAIT_S)` (gpu0.lease's poll_s default 0.2, gpu0.py:232).
- The main tree's client, verbatim from its imports on (/home/ultron/protocol_pulse/services/gpu_lease_client.py:10-49,
  main fb973fd0; cycle 1's excerpt began one line late, at `import os`):
```python
import importlib.util
import os
import sys

_GPU0_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline", "gpu0.py")
GPU1 = 1


class Gpu1Unavailable(RuntimeError):
    """GPU1 could not be used for this call (its lease stayed busy, a foreign user stayed, memory never came free)."""


def gpu0():
    m = sys.modules.get("pp_gpu0")
    if m is None:
        spec = importlib.util.spec_from_file_location("pp_gpu0", _GPU0_PATH)
        m = importlib.util.module_from_spec(spec)
        sys.modules["pp_gpu0"] = m
        try:
            spec.loader.exec_module(m)
        except BaseException:
            sys.modules.pop("pp_gpu0", None)
            raise
    return m


def chat_gpu1(model, messages, owner, options=None, fmt=None, wait_s=600.0, timeout=120):
    """The content of one /api/chat reply from `model` on GPU1's Ollama ('' when the reply has none). `owner` names the
    caller in the lease file. Raises Gpu1Unavailable, or the request's own error."""
    g = gpu0()
    body = {"messages": messages, "stream": False}
    if options:
        body["options"] = options
    if fmt:
        body["format"] = fmt
    try:
        r = g.ollama_call(GPU1, model, "/api/chat", body, owner, wait_s=wait_s, timeout=timeout)
    except g.Gpu0Stop as e:
        raise Gpu1Unavailable(f"GPU1 {type(e).__name__}: {e}") from None
    return ((r or {}).get("message") or {}).get("content", "") or ""
```
- gpu0.ollama_call, verbatim (/home/ultron/protocol_pulse/pipeline/gpu0.py:674-701):
```python
def ollama_call(gpu, model, path, body, owner, wait_s=600.0, timeout=300):
    """One request to GPU `gpu`'s Ollama for a caller that loads nothing itself (the watchdog, the morning brief, the
    stage broadcast, the website): law L-r, every GPU has one owner at a time. One call per GPU per process at a time
    (an in-process lock: the website serves several threads); GPU `gpu`'s lease is taken, waiting up to wait_s for its
    holder to leave (the word-pass worker leaves between batches); swap_to proves the memory free and waits a foreign
    user out (then a Gpu0Foreign naming it); the request runs with keep_alive 0; the model is confirmed gone from that
    Ollama before the lease is released, so the GPU is left as found. Nothing of this process on another GPU is
    touched. Returns the reply's JSON; raises a Gpu0Stop (LeaseBusy, Gpu0Foreign, Gpu0NotFree, ...) or the request's
    own error."""
    key = f"ollama:{model}"
    with _on(gpu):
        if not _call_locks[gpu].acquire(timeout=max(0.0, float(wait_s))):
            raise LeaseBusy(f"{owner}: another call of this process has held GPU{gpu} for longer than {wait_s}s")
        prev_bound = getattr(_tls, "foreign_wait_s", None)
        _tls.foreign_wait_s = float(wait_s)                              # and the foreign wait-out
        try:
            with lease(owner, wait_s=wait_s, poll_s=1.0):
                swap_to(key, wait_s=min(WAIT_S, float(wait_s)))          # the caller's bound covers the memory wait too
                try:
                    reply = _ollama(path, dict(body, model=model, keep_alive=0), timeout=timeout)
                except BaseException:
                    _leave_ollama(model, quiet=True)             # never masks the request's own error (audit 45 c2 A)
                    raise
                _leave_ollama(model, quiet=False)                # keep_alive 0 asked; this confirms it on /api/ps
                return reply
        finally:
            _tls.foreign_wait_s = prev_bound
            _call_locks[gpu].release()
```

## What to check
- No GPU stop (BaseException) can leave OllamaLocalBackend.complete(), and no other BaseException is swallowed.
- A card not free is never retried on the card (no transport retry loop of 60 s waits) and never counts as a rejected
  try of the work (AllBackendsFailed.outage stays True).
- The yield: after a request that reached the card, the next one waits out yield_s; after a refusal, no wait.
- enabled() never loads the client or takes a lease; the startup line's "callable now" is honest.
- Nothing of the main tree is written; the client is loaded by path, never put on sys.path.
- The tests can never take a real lease or reach the real model server.
- Law L-x: no vendor or model name in the package's code (the model comes from providers.json).

Suite: tests/ingest 439 passed (437 before: 3 GPU0-era tests removed, 5 new in test_r123.py). Mutations M51-M64: 14 of
14 killed (each run with the lease files redirected to scratch files and urlopen refused), the unmutated control
passed.


```diff
diff --git a/pipeline/ingest/providers.json b/pipeline/ingest/providers.json
index 0dc704b2..ce90e3d0 100644
--- a/pipeline/ingest/providers.json
+++ b/pipeline/ingest/providers.json
@@ -10,9 +10,10 @@
   "env_file": "/home/ultron/protocol_pulse/.env",
   "backends": {
     "local_gemma": {
-      "kind": "ollama_local", "vendor": "ultron-gpu0", "model": "gemma3:27b", "enabled": false, "requires": "gpu0_lease",
-      "note": "Ultron GPU0 through story_semantics.LocalLLM (gpu0.require + swap_to on every request, main 4867a74a). Available only while this process holds the GPU0 lease (gpu0.held); the integrator enables it under the lease; this session uses no GPU.",
-      "max_inflight": 1, "timeout_s": 600,
+      "kind": "ollama_local", "vendor": "ultron-gpu1", "model": "gemma3:27b", "enabled": true, "requires": "gpu1_lease",
+      "lease_wait_s": 60, "yield_s": 3, "num_ctx": 16384,
+      "note": "Ruling 118 (orchestrator 10:50 ET Nov 16 (2)): the local model on a free card under the lease, the last of the mine, hook and spotlight chains. Ultron GPU1 (law L-r's layout, PBX 2026-11-12: GPU0 renders and their gates, GPU1 everything else) through the main tree's lease client (services/gpu_lease_client.py, gpu0.ollama_call; main fb973fd0): per request the GPU1 lease within lease_wait_s, the memory proven free and a foreign user waited out within the same bound, keep_alive 0, the unload confirmed before the lease is released. A card not free within the bound is 'busy' (not retried; the videos wait). After each request that reached the card it is left free for yield_s (gpu0.lease polls every 0.2 s, ollama_call every 1 s). num_ctx: the pipeline's LocalLLM setting, at which gpu0.REQUIREMENT_MIB was measured; the longest mine prompt measured is 2,643 tokens (Nov 16-17), the role's reply budget 4,000. timeout_s: the request (the model's load and the reply).",
+      "max_inflight": 1, "timeout_s": 300,
       "price": {"in_per_mtok": 0.0, "out_per_mtok": 0.0, "basis": "local"}
     },
     "heimdall_qwen27b": {
@@ -198,7 +199,7 @@
   "roles": {
     "mine": {"chain": ["heimdall_qwen27b", "heimdall_deepseek", "heimdall_minimax", "heimdall_gemma", "heimdall_gptoss", "heimdall_mimo", "local_gemma"],
              "attempts": 3, "max_tokens": 4000,
-             "note": "ruling 118 (orchestrator 10:50 ET Nov 16): outside vendors are capped at $1.00 a day for the whole pipeline, so the miner's paid route is closed; its Plan B is the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model on a free card under the lease (local_gemma: only while this process holds the GPU lease)"},
+             "note": "ruling 118 (orchestrator 10:50 ET Nov 16): outside vendors are capped at $1.00 a day for the whole pipeline, so the miner's paid route is closed; its Plan B is the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model on a free card under the lease (local_gemma: GPU1, its lease taken per request when the card is free)"},
     "judge": {"chain": ["xai_frontier", "gemini_frontier", "anthropic_frontier"], "attempts": 2, "max_tokens": 8000},
     "hook": {"chain": ["heimdall_qwen27b", "heimdall_deepseek", "heimdall_minimax", "heimdall_gemma", "heimdall_gptoss", "heimdall_mimo", "local_gemma"], "attempts": 3, "max_tokens": 3000,
              "note": "ruling 80 (2026-11-13 18:42 ET): the hook pass, a second mining question over the same windows (mine.HOOK_PROMPT); the mine role's chain under the spend freeze"},
diff --git a/pipeline/ingest/providers.py b/pipeline/ingest/providers.py
index 68b62cdd..facc37c5 100644
--- a/pipeline/ingest/providers.py
+++ b/pipeline/ingest/providers.py
@@ -18,11 +18,14 @@ Keys are read by NAME from the env file named in the config, inside code; never
 text is redacted of every key value before it is recorded), never sent after a redirect.
 """
 import hashlib
+import importlib.util
+import inspect
 import json
 import os
 import random
 import socket
 import statistics
+import sys
 import threading
 import time
 import urllib.error
@@ -38,7 +41,8 @@ from . import config
 
 class BackendError(Exception):
     """kind: network | timeout | http_429 | overloaded | server | empty  (retried on the same back-end with backoff)
-             routing | redirect | http_auth | http_4xx | refusal | disabled   (not retried: next back-end)
+             routing | redirect | http_auth | http_4xx | refusal | disabled | busy   (not retried: next back-end;
+             busy: the local back-end's GPU was not free within its bound)
     REJECTED kinds are about this request (the back-end answered and refused or gave nothing usable): they count as a
     failed try of the work. Every other kind is the back-end being unavailable: the work waits."""
     RETRY = frozenset({"network", "timeout", "http_429", "overloaded", "server", "empty"})
@@ -471,65 +475,93 @@ class GeminiBackend(Backend):
                      (self.cfg.get("price") or {}).get("basis", "estimate"), None, 200, None)
 
 
+# Ruling 118 (the 10:50 order of Nov 16 (2)): "then the local model on a free card under the lease". Law L-r (main
+# gpu0.py, PBX 2026-11-12): every GPU has one owner at a time; GPU0 = renders and their gates, GPU1 = everything else;
+# code outside a run asks GPU1's model server only through the main tree's lease client (main fb973fd0).
+LEASE_CLIENT = os.path.join(config.MAIN_TREE, "services", "gpu_lease_client.py")
+LEASE_CLIENT_MODULE = "pp_ingest_gpu_lease_client"      # a private name: the main tree's modules never go on sys.path
+LEASE_OWNER = "pp-ingest watcher: the miner's local fallback (ruling 118)"   # what the lease file names to others
+_client_lock = threading.Lock()
+
+
+def lease_client():
+    """The main tree's GPU1 lease client, loaded once by its file path (it loads the main tree's gpu0.py the same way)
+    and checked for the API used here. Raises (ImportError, OSError, ...) when it is absent or not that API."""
+    with _client_lock:
+        m = sys.modules.get(LEASE_CLIENT_MODULE)
+        if m is not None:
+            return m
+        spec = importlib.util.spec_from_file_location(LEASE_CLIENT_MODULE, LEASE_CLIENT)
+        if spec is None or spec.loader is None:
+            raise ImportError(f"no module at {LEASE_CLIENT}")
+        m = importlib.util.module_from_spec(spec)
+        spec.loader.exec_module(m)
+        refused = getattr(m, "Gpu1Unavailable", None)
+        if not (isinstance(refused, type) and issubclass(refused, BaseException)):
+            raise ImportError(f"{LEASE_CLIENT}: no Gpu1Unavailable exception class")
+        inspect.signature(m.chat_gpu1).bind("model", [], LEASE_OWNER, options={}, fmt="json", wait_s=1.0,
+                                            timeout=1.0)          # TypeError / AttributeError: not the API used here
+        sys.modules[LEASE_CLIENT_MODULE] = m
+        return m
+
+
 class OllamaLocalBackend(Backend):
-    """The local model on Ultron GPU0 through story_semantics.LocalLLM. Available only when enabled in the config AND
-    this process holds the GPU0 lease: gpu0.held() is a check, never an acquisition (integrator B3); LocalLLM._post
-    itself calls gpu0.require() and swap_to on every request (law L-r, main 4867a74a). Where pipeline/gpu0.py is absent
-    the back-end is never available. release() unloads this run's model (LocalLLM.stop) at the end of a cycle."""
+    """The local model on GPU1 under its lease, the last of a chain (ruling 118). Each request goes through the main
+    tree's lease client (lease_client, gpu0.ollama_call): the GPU1 lease taken within lease_wait_s, the memory proven
+    free and a foreign user waited out within the same bound, the request with keep_alive 0, the model's unload
+    confirmed before the lease is released, so the card is left as found; this process never holds it between
+    requests. A card not free within the bound (its lease held, a foreign user, the memory) is 'busy': unavailable,
+    never retried on this back-end, the work waits (AllBackendsFailed.outage). After every request that reached the
+    card, the card is left free for yield_s before this back-end's next one, so an owner waiting for it (gpu0.lease
+    polls every 0.2 s, ollama_call every 1 s) takes its turn. enabled() reads the config and the client's file: a
+    check, never a load or a lease (integrator B3: nothing stands in for custody; the lease is taken per request)."""
 
     def __init__(self, bid, cfg, keyring):
         super().__init__(bid, cfg, keyring)
-        self._llm = None
-        self._llm_lock = threading.Lock()
-        self._busy = 0                                # requests in flight: release() never stops the model under one
-
-    @staticmethod
-    def _gpu0():
-        try:
-            import gpu0
-            return gpu0
-        except ImportError:
-            return None
+        self.lease_wait_s = float(cfg.get("lease_wait_s", 60))
+        self.yield_s = float(cfg.get("yield_s", 3))
+        self.num_ctx = int(cfg.get("num_ctx", 16384))
+        self._free_at = 0.0                           # the next request starts no earlier (the yield)
+        self._clock, self._sleep = time.time, time.sleep
 
     def enabled(self):
-        if not self.cfg.get("enabled"):
-            return False
-        g = self._gpu0()
-        return bool(g is not None and g.held())
+        return bool(self.cfg.get("enabled")) and os.path.isfile(LEASE_CLIENT)
 
     def complete(self, prompt, schema, max_tokens):
         if not self.cfg.get("enabled"):
             raise BackendError("disabled", "local back-end disabled in providers.json")
-        if not self.enabled():
-            raise BackendError("disabled", "GPU0 lease not held by this process (or pipeline/gpu0.py absent): the "
-                                           "local back-end runs only under the lease (law L-r)")
-        import story_semantics as sm
-        t0 = time.time()                              # a cold load is part of this call's latency (glm c2 N1)
-        with self._llm_lock:
-            if self._llm is None:
-                self._llm = sm.LocalLLM(model=self.model).start()
-            llm = self._llm
-            self._busy += 1
         try:
-            text = llm._post(prompt, int(max_tokens), seed=7)
-        except Exception as e:                        # a GPU0 stop (BaseException) is never renamed: it propagates
-            raise BackendError("server", f"{type(e).__name__}: {e}"[:300], latency_s=time.time() - t0)
+            client = lease_client()
+        except Exception as e:                        # absent, or not the API used here: never available
+            raise BackendError("disabled", f"the GPU lease client cannot be used: {type(e).__name__}: {e}"[:300])
+        wait = self._free_at - self._clock()
+        if wait > 0:
+            self._sleep(wait)
+        t0, reached = self._clock(), True
+        try:
+            text = client.chat_gpu1(self.model, [{"role": "user", "content": prompt}], LEASE_OWNER,
+                                    options={"temperature": 0, "seed": 7, "num_ctx": self.num_ctx,
+                                             "num_predict": int(max_tokens)},
+                                    fmt="json", wait_s=self.lease_wait_s, timeout=self.timeout)
+        except client.Gpu1Unavailable as e:          # every GPU stop, renamed by the client: the card is not free
+            reached = False
+            raise BackendError("busy", str(e)[:300], latency_s=self._clock() - t0) from None
+        except urllib.error.HTTPError as e:           # the request's own errors, as for every other back-end
+            raise _http_error(e, t0) from None
+        except (socket.timeout, TimeoutError) as e:
+            raise BackendError("timeout", f"{type(e).__name__}", latency_s=self._clock() - t0) from None
+        except (urllib.error.URLError, ConnectionError, OSError) as e:
+            raise BackendError("network", f"{type(e).__name__}: {getattr(e, 'reason', e)}"[:300],
+                               latency_s=self._clock() - t0) from None
+        except Exception as e:
+            raise BackendError("server", f"{type(e).__name__}: {e}"[:300], latency_s=self._clock() - t0) from None
         finally:
-            with self._llm_lock:
-                self._busy -= 1
-        lat = time.time() - t0
+            if reached:
+                self._free_at = self._clock() + self.yield_s
+        lat = self._clock() - t0
         if not isinstance(text, str) or not text.strip():
             raise BackendError("empty", "no content", latency_s=lat)
-        return Reply(text, f"{self.model}@{getattr(llm, 'digest', None)}", self.cfg.get("vendor"), lat, {}, 0.0,
-                     "local", None, 200, None)
-
-    def release(self):
-        with self._llm_lock:
-            if self._busy:                            # a request is running: released at the next idle cycle
-                return
-            llm, self._llm = self._llm, None
-        if llm is not None and hasattr(llm, "stop"):
-            llm.stop()
+        return Reply(text, self.model, self.cfg.get("vendor"), lat, {}, 0.0, "local", None, 200, None)
 
 
 class Overrides:
diff --git a/tests/ingest/conftest.py b/tests/ingest/conftest.py
index d4af192b..c3161d37 100644
--- a/tests/ingest/conftest.py
+++ b/tests/ingest/conftest.py
@@ -2,6 +2,7 @@
 import os
 import sys
 import tempfile
+import types
 
 REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 if REPO not in sys.path:
@@ -41,6 +42,30 @@ def _batch_in_tmp(tmp_path_factory, monkeypatch):
     return p
 
 
+class NoGpuInTests(RuntimeError):
+    """What every test's GPU1 lease client raises: the local back-end reads it as a card that is not free."""
+
+
+@pytest.fixture(autouse=True)
+def _no_gpu_lease_in_tests(tmp_path_factory, monkeypatch):
+    """Ruling 118's local back-end takes the REAL GPU1 lease through the main tree's lease client (and loads a model on
+    GPU1): no test ever reaches it. Every test's client is this refusing one (providers.lease_client returns the
+    module cached under its private name, so the real file is never loaded), and the client's file is a stand-in
+    that exists, so enabled() is the same on every machine. A test of the local back-end installs its own."""
+    from pipeline.ingest import providers
+    calls = []
+
+    def chat_gpu1(*a, **k):
+        calls.append((a, k))
+        raise NoGpuInTests("tests never take a GPU lease (tests/ingest/conftest.py)")
+    stand_in = tmp_path_factory.mktemp("lease_client") / "gpu_lease_client.py"
+    stand_in.write_text("raise SystemExit('the tests stand-in lease client is never loaded')\n")
+    monkeypatch.setattr(providers, "LEASE_CLIENT", str(stand_in))
+    monkeypatch.setitem(sys.modules, providers.LEASE_CLIENT_MODULE,
+                        types.SimpleNamespace(Gpu1Unavailable=NoGpuInTests, chat_gpu1=chat_gpu1, calls=calls))
+    return calls
+
+
 @pytest.fixture(autouse=True)
 def _pipeline_store_in_tmp(tmp_path_factory, monkeypatch):
     """The 10:50 order (1) of Nov 16: the fetch step reads the pipeline's own transcript store and caption breaker (the
diff --git a/tests/ingest/test_providers.py b/tests/ingest/test_providers.py
index 21665a5a..ef691a9f 100644
--- a/tests/ingest/test_providers.py
+++ b/tests/ingest/test_providers.py
@@ -218,52 +218,6 @@ def test_a_disabled_back_end_with_a_cache_is_not_used(tmp_path):
     assert r.run("mine", "p", None, validate_obj).backend == "b"
 
 
-def test_the_local_back_end_needs_the_real_gpu0_lease_never_an_environment_string(monkeypatch):
-    """Integrator B3: availability is gpu0.held() (a check, never an acquisition); without pipeline/gpu0.py the
-    back-end is never available; no environment string stands in for custody."""
-    cfg = {"kind": "ollama_local", "vendor": "local", "model": "local-model", "enabled": True}
-    monkeypatch.setitem(sys.modules, "gpu0", None)                 # absent (as in this worktree before the merge)
-    b = providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent"))
-    assert not b.enabled()
-    with pytest.raises(BackendError) as e:
-        b.complete("p", None, 100)
-    assert e.value.kind == "disabled" and "lease" in e.value.detail
-    held = {"v": False}
-    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: held["v"]))
-    monkeypatch.setenv("PP_INGEST_GPU0_LEASE_HELD", "1")            # the old string means nothing now
-    assert not b.enabled()
-    held["v"] = True
-    assert b.enabled()
-    assert not providers.OllamaLocalBackend("local", dict(cfg, enabled=False), providers.Keyring("/x")).enabled()
-
-
-def test_the_local_model_is_released_at_the_end_of_a_cycle(monkeypatch):
-    stopped = []
-
-    class LLM:
-        def __init__(self, model):
-            self.digest = "d"
-
-        def start(self):
-            return self
-
-        def _post(self, prompt, max_tokens, seed):
-            return OK
-
-        def stop(self):
-            stopped.append(True)
-    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: True))
-    monkeypatch.setitem(sys.modules, "story_semantics", types.SimpleNamespace(LocalLLM=LLM))
-    cfg = H.router_cfg(["local"])
-    cfg["backends"]["local"] = {"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True}
-    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"), sleep=lambda s: None)
-    assert r.run("mine", "p", None, validate_obj).backend == "local"
-    r.release()
-    assert stopped == [True] and r.backends["local"]._llm is None
-    r.release()                                    # idempotent
-    assert stopped == [True]
-
-
 def test_keys_never_appear_in_repr_or_errors(tmp_path):
     env = tmp_path / ".env"
     env.write_text("SECRET_KEY=sk-test-123456\nHEIMDALL_API_KEY_2='hk-abc'\nHEIMDALL_API_KEY=hk-def\n")
@@ -304,7 +258,9 @@ def test_the_real_config_under_the_spend_freeze():
     for bid in cfg["backends"]:
         if cfg["backends"][bid]["vendor"] in fz:
             assert r.frozen(bid) and r.available(bid)[0] is False
-    assert r.effective("mine") == mine_chain[:-1]          # this session: no GPU0 lease, so the gateway's six
+    local = cfg["backends"][mine_chain[-1]]                # ruling 118: the local model on GPU1 under its lease,
+    assert local["enabled"] is True and local["vendor"] not in fz   # taken per request (tests: the conftest's client)
+    assert r.effective("mine") == mine_chain
 
 
 def test_a_frozen_vendor_is_never_called_whatever_the_chain_only_or_enabled_say(tmp_path):
@@ -548,68 +504,32 @@ def test_an_interrupt_during_a_probe_frees_the_probe_without_counting_a_failure(
     assert snap.probing is False and snap.consec == 0
 
 
-def test_the_local_model_is_never_stopped_under_a_running_request(monkeypatch):
-    import threading
-    started, finish, stopped = threading.Event(), threading.Event(), []
-
-    class LLM:
-        def __init__(self, model):
-            self.digest = "d"
-
-        def start(self):
-            return self
-
-        def _post(self, prompt, max_tokens, seed):
-            started.set()
-            finish.wait(5)
-            return OK
-
-        def stop(self):
-            stopped.append(True)
-    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: True))
-    monkeypatch.setitem(sys.modules, "story_semantics", types.SimpleNamespace(LocalLLM=LLM))
-    b = providers.OllamaLocalBackend("local", {"kind": "ollama_local", "vendor": "local", "model": "m",
-                                               "enabled": True}, providers.Keyring("/nonexistent"))
-    th = threading.Thread(target=b.complete, args=("p", None, 10))
-    th.start()
-    started.wait(5)
-    b.release()                                      # a request is running: not stopped
-    assert stopped == [] and b._llm is not None
-    finish.set()
-    th.join(5)
-    b.release()
-    assert stopped == [True]
-
-
 def test_a_stored_reply_is_reused_when_the_back_end_is_enabled_but_not_callable_now(tmp_path, monkeypatch):
-    """Freeze audit c2 (muse N2): the reply cache was gated on enabled(), which for the local back-end means the GPU0
-    lease: a validated reply stored under the lease could not be re-read without it (it costs nothing, uses no GPU)."""
-    held = {"v": True}
-
-    class LLM:
-        def __init__(self, model):
-            self.digest = "d"
-
-        def start(self):
-            return self
-
-        def _post(self, prompt, max_tokens, seed):
-            return OK
-
-        def stop(self):
-            pass
-    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: held["v"]))
-    monkeypatch.setitem(sys.modules, "story_semantics", types.SimpleNamespace(LocalLLM=LLM))
+    """Freeze audit c2 (muse N2): the reply cache was gated on enabled(); a validated reply stored by the local back-end
+    is re-read while its card is not free (it costs nothing, uses no GPU). Ruling 118: the card is GPU1, its lease
+    taken per request through the main tree's lease client (here a stand-in that answers, then refuses)."""
+    free = {"v": True}
+
+    class Busy(RuntimeError):
+        pass
+
+    def chat_gpu1(model, messages, owner, **k):
+        if not free["v"]:
+            raise Busy("GPU1 LeaseBusy: the GPU1 lease is held by another owner")
+        return OK
+    monkeypatch.setitem(sys.modules, providers.LEASE_CLIENT_MODULE,
+                        types.SimpleNamespace(Gpu1Unavailable=Busy, chat_gpu1=chat_gpu1))
     cfg = H.router_cfg(["local"])
-    cfg["backends"]["local"] = {"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True}
+    cfg["backends"]["local"] = {"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True, "yield_s": 0}
     r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"), sleep=lambda s: None,
                          cache_dir=str(tmp_path))
     assert r.run("mine", "p", None, validate_obj).cached is False
-    held["v"] = False                                 # the lease is gone: no call, but the stored reply answers
+    free["v"] = False                                 # the card is not free: no answer, but the stored reply answers
     out = r.run("mine", "p", None, validate_obj)
     assert out.cached is True and out.backend == "local"
-    with pytest.raises(providers.AllBackendsFailed):
-        r.run("mine", "another prompt", None, validate_obj)        # nothing stored: not callable without the lease
+    with pytest.raises(providers.AllBackendsFailed) as e:
+        r.run("mine", "another prompt", None, validate_obj)        # nothing stored: the work waits
+    assert e.value.outage and e.value.tried[0][1] == "unavailable" and "busy" in e.value.tried[0][2]
 
 
 def test_a_back_ends_own_key_is_redacted_whatever_its_length(tmp_path):
diff --git a/tests/ingest/test_r123.py b/tests/ingest/test_r123.py
new file mode 100644
index 00000000..4330539d
--- /dev/null
+++ b/tests/ingest/test_r123.py
@@ -0,0 +1,173 @@
+"""tests/ingest/test_r123.py: the local model on a free card under the lease (ruling 118; the 10:50 order of Nov 16 (2)).
+
+The last back-end of the mine, hook and spotlight chains is the local model on GPU1 (law L-r's layout, PBX 2026-11-12:
+GPU0 renders and their gates, GPU1 everything else). Each request goes through the main tree's lease client
+(services/gpu_lease_client.py, gpu0.ollama_call): the GPU1 lease taken within a bound, the memory proven free, the
+request with keep_alive 0, the unload confirmed before the lease is released. A card not free within the bound is
+'busy': not retried on the card; the work waits. After a request that reached the card, the card is left free for
+yield_s, so another owner takes its turn. No test takes a real lease: tests/ingest/conftest.py gives every test a
+refusing client; these tests install their own, and the one that runs the main tree's real client file gives it a
+stand-in for gpu0.
+"""
+import io
+import json
+import os
+import sys
+import types
+import urllib.error
+
+import pytest
+
+import helpers as H
+from pipeline.ingest import config, providers
+from pipeline.ingest.providers import BackendError
+
+OK = json.dumps({"ok": True})
+REAL_CLIENT = os.path.join(config.MAIN_TREE, "services", "gpu_lease_client.py")
+
+
+def validate_obj(content):
+    obj = json.loads(content)
+    if obj != {"ok": True}:
+        raise providers.Invalid("not ok")
+    return obj
+
+
+def local(**over):
+    cfg = dict({"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True, "lease_wait_s": 45,
+                "yield_s": 0, "num_ctx": 8192, "timeout_s": 120}, **over)
+    return providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent"))
+
+
+class Client:
+    """A stand-in for the lease client: replies (str) or exceptions, in order; every call recorded."""
+
+    class Gpu1Unavailable(RuntimeError):
+        pass
+
+    def __init__(self, *script):
+        self.script, self.calls = list(script), []
+
+    def chat_gpu1(self, model, messages, owner, options=None, fmt=None, wait_s=600.0, timeout=120):
+        self.calls.append(dict(model=model, messages=messages, owner=owner, options=options, fmt=fmt, wait_s=wait_s,
+                               timeout=timeout))
+        r = self.script.pop(0) if self.script else OK
+        if isinstance(r, BaseException):
+            raise r
+        return r
+
+
+@pytest.fixture
+def client(monkeypatch):
+    def install(*script):
+        c = Client(*script)
+        monkeypatch.setitem(sys.modules, providers.LEASE_CLIENT_MODULE, c)
+        return c
+    return install
+
+
+def test_the_local_model_is_asked_only_after_every_gateway_model_failed_and_as_the_pipeline_asks_it(client):
+    c = client(OK)
+    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
+    b = H.FakeBackend("b", fn=lambda p: BackendError("timeout", "slow"))
+    r = H.make_router([a, b, local()])
+    out = r.run("mine", "the window's question", None, validate_obj)
+    assert out.backend == "local" and out.obj == {"ok": True} and out.model == "m" and a.calls and b.calls
+    assert c.calls == [dict(model="m", messages=[{"role": "user", "content": "the window's question"}],
+                            owner=providers.LEASE_OWNER,
+                            options={"temperature": 0, "seed": 7, "num_ctx": 8192, "num_predict": 1000},
+                            fmt="json", wait_s=45.0, timeout=120.0)]          # num_predict: the role's reply budget
+    a.fn = lambda p: OK                                                      # the gateway answers: the card is not asked
+    assert r.run("mine", "another", None, validate_obj).backend == "a" and len(c.calls) == 1
+
+
+def test_a_card_not_free_is_busy_asked_once_and_the_work_waits_through_the_real_lease_client(monkeypatch):
+    """The main tree's own client file, run with a stand-in gpu0 (never the real lease): a GPU stop (a BaseException;
+    LeaseBusy here) is renamed by the client and read as 'busy': one request, no retry on the card, nothing out of the
+    chain but AllBackendsFailed with outage (the videos wait)."""
+    assert os.path.isfile(REAL_CLIENT), "the main tree's lease client (main fb973fd0) is the local back-end's only way"
+
+    class Gpu0Stop(BaseException):
+        pass
+
+    class LeaseBusy(Gpu0Stop):
+        pass
+    asked = []
+
+    def ollama_call(gpu, model, path, body, owner, wait_s=600.0, timeout=300):
+        asked.append(dict(gpu=gpu, model=model, path=path, body=body, owner=owner, wait_s=wait_s, timeout=timeout))
+        raise LeaseBusy("the GPU1 lease is held by word-pass worker (integrator, GPU1) (pid 1)")
+    monkeypatch.setitem(sys.modules, "pp_gpu0", types.SimpleNamespace(Gpu0Stop=Gpu0Stop, ollama_call=ollama_call))
+    monkeypatch.delitem(sys.modules, providers.LEASE_CLIENT_MODULE)        # the conftest's: the real file loads
+    monkeypatch.setattr(providers, "LEASE_CLIENT", REAL_CLIENT)
+    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
+    r = H.make_router([a, local()])
+    with pytest.raises(providers.AllBackendsFailed) as e:
+        r.run("mine", "q", None, validate_obj)
+    assert sys.modules[providers.LEASE_CLIENT_MODULE].__file__ == REAL_CLIENT
+    assert e.value.outage and e.value.tried[-1][:2] == ("local", "unavailable")
+    assert e.value.tried[-1][2].startswith("busy: GPU1 LeaseBusy: the GPU1 lease is held by word-pass worker")
+    assert len(asked) == 1 and asked[0]["gpu"] == 1 and asked[0]["path"] == "/api/chat" and asked[0]["model"] == "m"
+    assert asked[0]["body"] == {"messages": [{"role": "user", "content": "q"}], "stream": False, "format": "json",
+                                "options": {"temperature": 0, "seed": 7, "num_ctx": 8192, "num_predict": 1000}}
+    assert asked[0]["owner"] == providers.LEASE_OWNER and asked[0]["wait_s"] == 45.0 and asked[0]["timeout"] == 120.0
+
+
+def test_the_card_is_left_free_after_every_request_that_reached_it_never_after_a_refusal(client):
+    t, slept = [100.0], []
+    b = local(yield_s=3)
+
+    def sleep(s):
+        slept.append(s)
+        t[0] += s
+    b._clock, b._sleep = (lambda: t[0]), sleep
+    busy = Client.Gpu1Unavailable("GPU1 Gpu0Foreign: a foreign GPU1 user, still there after a 45.0s wait")
+    down = urllib.error.HTTPError("http://127.0.0.1:11435/api/chat", 500, "Internal Server Error", {},
+                                  io.BytesIO(b"the model runner stopped"))
+    c = client(OK, busy, down, OK)
+    assert b.complete("p", None, 10).content == OK and slept == []          # nothing to wait for before the first
+    with pytest.raises(BackendError) as e:
+        b.complete("p", None, 10)
+    assert e.value.kind == "busy" and slept == [3.0]                        # waited: the card was left free 3 s
+    with pytest.raises(BackendError) as e:
+        b.complete("p", None, 10)
+    assert e.value.kind == "server" and slept == [3.0]                      # the refusal never reached the card
+    t[0] += 1.0
+    assert b.complete("p", None, 10).content == OK and slept == [3.0, 2.0]  # the failed request did: 3 s from its end
+    assert len(c.calls) == 4
+
+
+def test_enabled_reads_the_config_and_the_clients_file_and_never_loads_it(tmp_path, monkeypatch):
+    """Integrator B3 (nothing stands in for custody): enabled() is a check, never a load or a lease; the client is
+    loaded at the first request, checked for the API used here, and never kept when it is not that API."""
+    mark = tmp_path / "loaded"
+    f = tmp_path / "gpu_lease_client.py"
+    f.write_text(f"open({str(mark)!r}, 'w').write('loaded')\n")             # loading it is visible; it has no API
+    monkeypatch.delitem(sys.modules, providers.LEASE_CLIENT_MODULE)
+    monkeypatch.setattr(providers, "LEASE_CLIENT", str(f))
+    assert local().enabled() and not local(enabled=False).enabled()
+    with pytest.raises(BackendError) as e:
+        local(enabled=False).complete("p", None, 10)
+    assert e.value.kind == "disabled" and not mark.exists()                 # nothing loaded, no lease
+    with pytest.raises(BackendError) as e:
+        local().complete("p", None, 10)
+    assert e.value.kind == "disabled" and "Gpu1Unavailable" in e.value.detail and mark.exists()
+    assert providers.LEASE_CLIENT_MODULE not in sys.modules                 # not kept: a fixed file loads next time
+    monkeypatch.setattr(providers, "LEASE_CLIENT", str(tmp_path / "absent.py"))
+    assert not local().enabled()
+    with pytest.raises(BackendError) as e:
+        local().complete("p", None, 10)
+    assert e.value.kind == "disabled"
+
+
+def test_no_test_reaches_the_real_lease_client():
+    """The suite's guard (tests/ingest/conftest.py): the real config's local back-end, asked in any test, is refused
+    as a card that is not free, and the real client file is never the one named."""
+    cfg = providers.load_config()
+    bid = cfg["roles"]["mine"]["chain"][-1]
+    b = providers.make_backend(bid, cfg["backends"][bid], providers.Keyring("/nonexistent"))
+    assert isinstance(b, providers.OllamaLocalBackend) and b.enabled()
+    with pytest.raises(BackendError) as e:
+        b.complete("p", None, 10)
+    assert e.value.kind == "busy" and "tests never take a GPU lease" in e.value.detail
+    assert providers.LEASE_CLIENT != REAL_CLIENT

```

You see the diff, not the whole files: when a finding needs code outside it, say which function you need instead of
guessing.

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

