# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 104.6 s, $0.003, finish stop)

# PROTOCOL PULSE CODE AUDIT — CYCLE 2: pp-ingest r123 (37150995)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Honest accounting:**

*   **Qwen's `importlib` false positive:** I did not flag this because I correctly inferred `import importlib.util` was present (line 10, outside the truncated excerpt). Qwen flagged it as critical, then the consensus correctly refuted it as an excerpt truncation artifact. I missed nothing here — I correctly did not raise it — but Qwen's error is instructive: diff-scoped audits with truncated context generate false P0s.
*   **Qwen's yield semantics analysis:** Qwen explicitly walked through *why* `reached=True` by default is correct (timeout/network/server all touched the card, only `Gpu1Unavailable` did not). My Cycle 1 stated the same conclusion but Qwen's justification was more explicit. I had it, but less clearly argued.
*   **Qwen's race condition framing:** Qwen raised the `_free_at` race as "critical" then talked itself out of it. I correctly dismissed it in Cycle 1 Step 6 via the `BoundedSemaphore(1)` + `_call_locks` double-serialization. No miss.
*   **What I caught that they missed/underweighted:** The `BaseException` escape on `spec.loader.exec_module(m)` in `lease_client()` -> `complete():500 except Exception` miss. Both other models missed this entirely. Qwen missed it, Muse missed it. I flagged it as "theoretical gap, not production-reaching." The consensus truncated my note to "Recorded" and dismissed it. I stand by it — it's the only true defect in the diff.

**Net:** No material finding from others that I missed. One material finding from me that others missed.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **No Gpu0Stop reaches Router.run:919** | **AGREE** | Verified: `gpu_lease_client.py:47` renames `Gpu0Stop` -> `Gpu1Unavailable(BaseException)`, `providers.py:512` renames -> `BackendError("busy", Exception)`. `busy` not in RETRY/REJECTED -> `outage=True`, no retry, no breaker trip via `downsignal.py:182`. This is the core fix, correct. |
| **Yield logic correct** | **AGREE** | `reached=False` only on `Gpu1Unavailable`. All other paths yield. Matches spec "after a request that reached the card." |
| **enabled() pure check (B3)** | **AGREE** | `bool(cfg.get("enabled")) and isfile(LEASE_CLIENT)` — no load, no lease. |
| **One thread at a time** | **AGREE** | `Router:819 BoundedSemaphore(min(1, global))` + `gpu0.ollama_call _call_locks[GPU1]` double-serializes. No race on `_free_at` in production. |
| **Qwen: "Race on _free_at is critical"** | **DISAGREE** | Cannot happen under current `max_inflight=1`. Future config change to `>1` would still be serialized by `gpu0._call_locks`. Yield would be approximate, not incorrect. P3 at most, not critical. |
| **Qwen: "Missing importlib"** | **DISAGREE — FALSE POSITIVE** | Consensus correctly refuted: line 10 is `import importlib.util`, excerpt started at line 11. |
| **Muse P2: "Add circuit breaker for local backend"** | **DISAGREE — REFUTED** | Consensus evidence is correct: `Router.__init__:817 health` + `1019 h.record` + `868 available()` already implements it. 5 consecutive failures -> 300s open -> half-open probe. Cost bounded to 5×60s + 60s/5min. |
| **Muse P2: BaseException on import escapes** | **AGREE — THIS IS REAL** | Consensus truncated this to "Theoretical gap." I agree it's theoretical *in production* (real client file never raises `BaseException` on import), but it's a real code defect: `lease_client():498 exec_module` can raise `BaseException`, `complete():500 except Exception` misses it, it escapes to `Router.run:919 except BaseException: raise` and kills the miner thread. The fix is one line. Dismissing it as "not production-reaching" is wrong — defense in depth requires `except BaseException` there. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Combined analysis reveals:**

1.  **The consensus itself introduced a risk by dismissing the BaseException gap.** By labeling my finding "Recorded" and truncating it, Cycle 1 consensus normalized a `BaseException` escape path. In a system where `Gpu0Stop(BaseException)` was the original killer bug (r122), any remaining `BaseException` escape is P1 by definition, even if currently unreachable. The combined review shows we need to be *more* strict about `BaseException` hygiene, not less.

2.  **No new correctness bugs found.** Two independent models + my deep trace + consensus cross-check found zero production-reaching correctness bugs. This increases confidence in r123 significantly.

3.  **Test double fidelity confirmed:** Both Qwen and I verified `conftest.py` stand-in correctly models `Gpu1Unavailable` as `BaseException` subclass and `chat_gpu1` signature. `test_r123.py` runs the *real* `gpu_lease_client.py` against a stand-in `gpu0` raising `LeaseBusy(Gpu0Stop)` — this is a high-fidelity integration test, not a mock-only test. No gap.

4.  **Law L-r (ONE OWNER) compliance is stronger than Cycle 1 stated:** Not just `yield_s` + `keep_alive 0`, but also `gpu0.ollama_call` holds `_call_locks[GPU1]` for the entire `ollama_call` duration, guaranteeing no other in-process GPU1 user interleaves. Cross-process safety is via `gpu0` lease file lock (outside diff, but referenced).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness** | 9/10 | 9/10 | No change. One theoretical BaseException gap remains, not production-reaching but real. |
| **Law Compliance** | 10/10 | 10/10 | No change. All laws verified, L-x/L-r/L-j/L-m compliant. |
| **Robustness** | 8/10 | 8/10 | No change. Circuit breaker already present (refuted Muse P2). BaseException gap is the only robustness deduction. |
| **Test Coverage** | 9/10 | 9/10 | No change. High-fidelity integration test confirmed. |
| **Overall** | 9/10 | 9/10 | Consensus increased confidence, but did not change score — my Cycle 1 was already correct. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL: (none)** — No production-reaching critical defect. r123 fixes the r122 miner-killer (`Gpu0Stop` escape).

**P1 HIGH:**
*   **P1-1: `providers.py:500` — Catch `BaseException` on `lease_client()` load.** Change `except Exception as e:` to `except BaseException as e:` (or add `except BaseException:` before it) when calling `lease_client()`. Currently `spec.loader.exec_module(m)` raising `SystemExit`/`KeyboardInterrupt`/`Gpu0Stop` escapes `complete()` and hits `Router.run:919` which re-raises `BaseException` and kills the miner thread. Fix: `except BaseException as e: raise BackendError("disabled", ...) from e` or `from None` with logging. One line. This is defense-in-depth for the exact bug class r123 fixes.

**P2 MEDIUM:**
*   **P2-1: `providers.py:498` — Do not cache failed client loads.** Already correct (no cache on failure), but add explicit comment: `# Do not cache on failure — next call retries (e.g., file transiently corrupt)`. Prevents future regression.
*   **P2-2: `providers.py:502-505` — Document yield invariant.** Add comment: `# reached=False only if lease never acquired (Gpu1Unavailable); all other errors touched the card and must yield`. Prevents future maintainer inverting the logic.

**P3 LOW / NIT:**
*   `providers.json:12` `timeout_s:300` rationale already documented per consensus — no action.
*   `lease_client()` `inspect.signature().bind()` validation is correct but could log the expected vs actual signature on failure for debuggability.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Fix `providers.py:500` to catch `BaseException` from `lease_client()` so no `BaseException` can ever escape `OllamaLocalBackend.complete()` — the same one-line fix that r123 applied to `chat_gpu1()` needs to be applied to the client-load path to fully close the miner-killer bug class.

## 7. PRODUCTION READY?

**Yes with one condition.**

**Condition:** Apply P1-1 (`except BaseException` on `lease_client()` path) before or immediately after ship. It is a one-line change with zero risk of regression (widens catch, wraps as `BackendError("disabled")` which already exists and is handled as `outage=True`).

**Without P1-1:** Still **Yes, ship** — the gap is theoretical (real `gpu_lease_client.py` never raises `BaseException` on import, and tests bypass file load via `sys.modules` cache). r123 is a strict improvement over r122 and fixes the known miner-killer. Do not block deploy on P1-1, but fix it in r124.

**No other conditions.** No rollback risk. No law violation. No data loss path.