# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 186.9 s, $0.005, finish stop)

# PROTOCOL PULSE CODE AUDIT: pp-ingest r123 (37150995)

## SECTION 1: CORRECTNESS

**Main flow: `OllamaLocalBackend.complete()` -> `lease_client().chat_gpu1()` -> `gpu0.ollama_call()`**

**Step 1: `enabled()` check - CORRECT**
`providers.py:493-494` `return bool(cfg.get("enabled")) and os.path.isfile(LEASE_CLIENT)` - Pure check, no load, no lease. Compliant with B3.

**Step 2: `lease_client()` loading - CORRECT with one subtlety**
`providers.py:488-510` Loads via `spec_from_file_location` under private name `pp_ingest_gpu_lease_client`. Validates `Gpu1Unavailable` is a `BaseException` subclass and `chat_gpu1` signature via `inspect.signature().bind()`. Caches in `sys.modules`. On failure, does NOT cache (correct - next call retries). The `ImportError` on missing spec/loader is correct.

**Step 3: Yield logic - CORRECT**
`providers.py:502-505`:
```python
wait = self._free_at - self._clock()
if wait > 0:
    self._sleep(wait)
```
`t0, reached = self._clock(), True` then `finally: if reached: self._free_at = self._clock() + self.yield_s`. 
- `reached` starts `True`, set `False` only on `Gpu1Unavailable`. So: success, HTTPError, timeout, network, server all set `reached=True` -> yield. Only `busy` (card never reached) skips yield. This matches spec: "after a request that reached the card".
- Clock/sleep are injectable (`self._clock`, `self._sleep`) for testing. Production uses `time.time`/`time.sleep`.

**Step 4: Exception handling - CORRECT, critical BaseException safety**
`providers.py:512-530`:
- `client.Gpu1Unavailable` -> `BackendError("busy")` with `from None` - Renames the `BaseException` (Gpu0Stop family) before it can escape to `Router.run:919` which re-raises `BaseException`. **This is the core fix of r123.**
- `HTTPError` -> `_http_error(e, t0)` - Correct, preserves 429/503 handling.
- `socket.timeout, TimeoutError` -> `timeout`
- `URLError, ConnectionError, OSError` -> `network`
- `Exception` -> `server` - Catches everything else as retryable server error.
- No `BaseException` can escape except via `lease_client()` failure path which raises `BackendError("disabled")` wrapping it as `Exception` - safe.

**Step 5: Router integration - CORRECT**
`providers.py:41-44` `busy` added to non-RETRY set. `Router._try:1014` `r.retryable and transport_left > 0` - `busy` is not in `RETRY`, so no transport retry loop. `1020` `kind in REJECTED else "unavailable"` - `busy` not in `REJECTED`, so `outage=True` (work waits). `downsignal.py:178-182` vendor `ultron-gpu1` != gateway, never noted.

**Step 6: Concurrency - CORRECT**
`providers.py:819` `BoundedSemaphore(min(max_inflight, global))` with `max_inflight=1` ensures one thread at a time in `complete()`. `_free_at` is only touched inside `complete()` which is semaphore-protected, so no race on `_free_at`. `_client_lock` protects `lease_client()` singleton init.

**Step 7: `release()` - CORRECT**
Base no-op. Nothing held between requests. No model to unload (GPU1 lease released inside `ollama_call`).

**Edge cases verified:**
- Empty DB / no videos: Not in diff scope, unchanged.
- API timeout: `timeout_s=300` passed to `chat_gpu1(timeout=)`, caught as `BackendError("timeout")` -> RETRY.
- Bad input / empty response: `providers.py:532-533` `not text.strip()` -> `BackendError("empty")` -> RETRY.
- `lease_client()` absent/corrupt: `complete():500-501` catches `Exception` -> `BackendError("disabled")` -> next backend (none, so `AllBackendsFailed` with `outage=False`? Actually `disabled` is not RETRY, not REJECTED -> `unavailable` -> `outage=True`. Correct - work waits for config fix.)
- `LEASE_CLIENT` file missing: `enabled()` returns False, `complete()` still tries `lease_client()` and gets `disabled`.

**One minor correctness note (not a bug):**
`providers.py:498` `spec.loader.exec_module(m)` - If this raises `BaseException` (e.g., `SystemExit` from stand-in), it propagates as `BaseException` out of `lease_client()`, then caught by `complete():500` `except Exception` - **MISSES BaseException**. However `conftest.py:55` stand-in raises `SystemExit` which IS a `BaseException`, not `Exception`. This would escape `complete()` and hit `Router.run:919` `except BaseException: record breaker; raise`. In production this cannot happen (real client file never raises `BaseException` on import). In tests, `lease_client()` is never called via file load (cached mock), so safe. **Theoretical gap, not production-reaching.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest** | **COMPLIANT** | Unchanged. Diff only touches local backend. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.py:493` `enabled()` checks config+file, no vendor name in code. `providers.json:12` `vendor: ultron-gpu1`, `model: gemma3:27b` only in config. `providers.py:510` model from `self.model` (config). `downsignal.py:178-182` local vendor never feeds outage clock. `max_inflight:1` respects bounded concurrency. |
| **L-l strict schema, nothing repaired** | **COMPLIANT** | Unchanged. `complete()` returns `Reply(text,...)` with raw text, validation is caller's job. |
| **L-j/L-m fail closed** | **COMPLIANT** | `BackendError("busy")` -> `unavailable` -> `outage=True` -> work waits, never passes. |
| **L-h/L-k transcript canonical form** | **COMPLIANT** | Not in diff scope. |
| **L-e word timing** | **COMPLIANT** | Not in diff scope. |
| **L-u hard exclusions** | **COMPLIANT** | Not in diff scope. |
| **L-v no span speaker change** | **COMPLIANT** | Not in diff scope. |
| **L-r EVERY GPU HAS ONE OWNER** | **COMPLIANT** | `providers.py:502-510` Uses `gpu0.ollama_call(GPU1,...)` via lease client. Per-request lease, `keep_alive 0`, unload confirmed. `release()` no-op, nothing held. `yield_s` respects other owners. |
| **Secrets: env file, never logged** | **COMPLIANT** | No secrets in diff. `providers.json:12` `price: local 0.0` - no key needed. |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:12` `enabled: true` for local only (free). No paid vendor enabled. Chain `mine: heimdall_* + local_gemma` - Heimdall then local only. `test_providers.py:258-262` verifies frozen vendors never called. |
| **Integrator B3: no env string for custody** | **COMPLIANT** | `providers.py:493` `os.path.isfile()` check only. `test_r123.py:128-145` explicitly tests no env string, no load on `enabled()`. Old `PP_INGEST_GPU0_LEASE_HELD` test removed. |

**No violations found.**

---

## SECTION 3: SECURITY

- **SQL injection:** No SQL in diff. No user input reaches DB. **PASS.**
- **Authentication bypass:** No routes in diff. `chat_gpu1` uses local Ollama on `127.0.0.1:11435` (from `gpu0.py:674`), no auth needed (local). **PASS.**
- **Rate limiting:** `max_inflight:1` + `BoundedSemaphore` + `yield_s:3` prevents local GPU exhaustion. Heimdall backends have `max_inflight` caps. No user can trigger arbitrary calls (ingest is internal pipeline). **PASS.**
- **Secrets in code:** No keys, tokens, passwords in diff. `providers.json` has `price: 0.0` for local. `LEASE_OWNER` is a label string, not a secret. `Keyring` not used for local. **PASS.**
- **Unvalidated input -> filesystem/shell:** `LEASE_CLIENT` is `os.path.join(config.MAIN_TREE, "services", "gpu_lease_client.py")` - constructed from config constant, not user input. `spec_from_file_location` loads it. No shell calls. `prompt` goes to Ollama via JSON body, not shell. **PASS.**
- **Path traversal:** `LEASE_CLIENT` path is fixed, not user-controlled. `sys.modules` key is fixed constant `pp_ingest_gpu_lease_client`. No `sys.path` mutation (explicitly avoided per spec). **PASS.**
- **One observation:** `providers.py:498` `spec.loader.exec_module(m)` executes arbitrary Python from `MAIN_TREE/services/gpu_lease_client.py`. If that file were compromised, it runs with full privileges. This is by design (trusted main tree) and unchanged in risk from prior `import gpu0` / `import story_semantics` pattern. Not a new attack surface.

---

## SECTION 4: FRONTEND QUALITY

**Not applicable.** This diff is `pipeline/ingest` + `tests/ingest` only. No frontend code. No UI spec to match.

---

## SECTION 5: BACKEND QUALITY

- **DB operations with rollback:** Not in diff scope. No DB writes in `providers.py`.
- **External API calls - timeout+retry+graceful degradation:** **EXCELLENT.**
  - `timeout_s:300` on every `chat_gpu1` call (`providers.json:14`, `providers.py:510`).
  - `lease_wait_s:60` bounds GPU wait (`providers.json:13`, `providers.py:510`).
  - Retry: `busy` not retried (correct - card not free), `server/timeout/network/empty` retried via `Router._try:1014` with backoff.
  - Graceful degradation: `busy` -> `AllBackendsFailed(outage=True)` -> videos queue for later, never lost. `downsignal.py` excludes local from outage clock.
- **Cron job failure handling:** Watcher `mine chain` failure queues videos, never crashes service. `Router.run:919` `except BaseException: record breaker; re-raise` ensures GPU stops don't silently vanish but also don't crash the process (caught at thread level).
- **Memory leaks:** No large objects per-request. `Reply` is small. `lease_client()` singleton cached once. No model held in memory between requests (unlike old `LocalLLM` which held `self._llm`). **Improved over prior.**
- **Logging:** `BackendError` records `kind`, `detail[:300]`, `latency_s` for every failure. `Router._try:997` records per-backend. `AllBackendsFailed.tried` preserves full chain for debugging. `LEASE_OWNER` string identifies caller in lease file for ops.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

This is infrastructure code (ingest pipeline), not user-facing product. Judged as such:

**Already excellent:**
- The GPU lease protocol (`ollama_call` with `keep_alive 0` + unload confirmation + `yield_s`) is production-grade resource sharing. Bloomberg Terminal-level rigor for shared hardware.
- The `busy` vs `rejected` vs `retryable` trichotomy is well-designed. Most pipelines conflate "busy" with "failed".
- Test isolation (`conftest.py` refusing stand-in, `test_r123.py` with real client file + stand-in gpu0) is thorough. 14/14 mutations killed.

**Material gaps (infrastructure perspective):**

1. **No observability on GPU wait time.** `lease_wait_s=60` - if GPU1 is consistently busy, videos queue silently. No metric/log for "waited X seconds for GPU1" vs "got it immediately". A Bloomberg-grade pipeline would emit `gpu1_wait_s` histogram. Currently only `latency_s` on success/failure, which conflates wait+inference.

2. **No circuit breaker for local backend.** If GPU1 is down for hours (Ollama crash), every mine attempt pays 60s `lease_wait_s` timeout before failing. 6 Heimdall backends fail fast, then 60s stall on local. Should have a consecutive-failure breaker (like `downsignal.py` for gateway) that short-circuits local for N minutes after K consecutive `busy`/`server` failures.

3. **`yield_s=3` is fixed, not adaptive.** `gpu0.lease` polls every 0.2s, `ollama_call` every 1s. 3s is generous for handoff but wasteful when no one is waiting. A more sophisticated design would check lease file before sleeping (if no waiter, skip yield). Minor - 3s overhead per video is acceptable at ~10min ingest cadence.

4. **No `num_ctx` validation against actual model.** `num_ctx=16384` is set from `gpu0.REQUIREMENT_MIB` measurement, but if Ollama model was loaded with different `num_ctx`, prompt truncation is silent. Should log actual `num_ctx` from Ollama response headers if available.

**Not gaps (correctly out of scope):**
- No frontend to critique. Pipeline correctly has no UI.
- No DB N+1 - ingest is queue-driven, not query-driven.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **96/100** | Exception handling is airtight. Yield logic correct. One theoretical `BaseException` gap in `lease_client()` import path (-4). |
| **Frontend/UI** | **N/A** | No frontend in scope. |
| **Error handling** | **97/100** | Every error kind mapped. `busy` correctly distinguished. `BaseException` renamed. `from None` suppresses misleading chains. Missing: `BaseException` during `exec_module` not caught as `Exception` (-3). |
| **Security** | **98/100** | No secrets, no injection, no auth bypass. Fixed path, no `sys.path` pollution. Private module name. (-2 for `exec_module` on file path - inherent, not fixable). |
| **Performance** | **92/100** | `max_inflight=1` + `yield_s=3` correct for shared GPU. `lease_wait_s=60` bounded. No leaks. (-8 for no circuit breaker on sustained GPU1 outage - 60s stall per video). |
| **Law compliance** | **100/100** | Every law verified compliant. L-r, L-x, B3, spend freeze all satisfied with cited lines. |
| **World-class gap** | **88/100** | Core design is excellent. Missing: GPU wait observability, circuit breaker, adaptive yield. |
| **OVERALL** | **95/100** | Production-ready. One P2 fix recommended, rest is polish. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | - | No production-breaking issues found.

P1 HIGH     | (none) | - | No high-severity degradation found.

P2 MEDIUM   | Add BaseException catch in lease_client() wrapper | providers.py:500 | lease_client() exec_module raising BaseException (SystemExit/KeyboardInterrupt) escapes complete()'s `except Exception` and hits Router.run's BaseException re-raise, killing the miner thread instead of reporting "disabled"
P2 MEDIUM   | Add circuit breaker for local backend consecutive failures | providers.py:OllamaLocalBackend | Sustained GPU1 outage (Ollama crash) causes 60s stall per video after 6 Heimdall failures; should short-circuit after K consecutive busy/server
P2 MEDIUM   | Emit gpu1_wait_s metric separately from inference latency | providers.py:502-510 | Ops cannot distinguish "GPU busy 55s + inference 5s" from "inference 60s" - needed for capacity planning

P3 LOW      | Make yield_s adaptive (check lease file before sleeping) | providers.py:502-505 | Fixed 3s yield wastes throughput when no waiter exists; minor at 10min cadence
P3 LOW      | Log actual num_ctx from Ollama response | providers.py:508 | Silent truncation if model loaded with different context window
P3 LOW      | Add timeout_s to providers.json note for local_gemma | providers.json:14 | Note documents num_ctx basis but not timeout_s=300 rationale (model load + inference bound)
```

---

## SECTION 9: THE ONE THING

**Catch `BaseException` in `complete()`'s `lease_client()` call path — a `SystemExit` during `exec_module` currently kills the miner thread instead of gracefully reporting the backend as disabled.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The r123 rewrite correctly fixes the dead-code local backend by moving from GPU0 (never held) to GPU1 (per-request lease via `ollama_call`), with airtight `BaseException` renaming, correct `busy` semantics, and thorough test isolation. Ship it; address the `BaseException` edge case and consider a circuit breaker in the next iteration.
