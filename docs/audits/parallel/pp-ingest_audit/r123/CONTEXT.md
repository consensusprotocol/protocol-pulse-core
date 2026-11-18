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
