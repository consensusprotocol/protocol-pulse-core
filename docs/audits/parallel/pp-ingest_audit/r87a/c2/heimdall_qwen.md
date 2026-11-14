# heimdall_qwen (qwen/qwen3.8-27b, 345.8 s, $0.010, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified a "critical race condition" regarding unbounded `join()` and a `KeyError` risk in the probe logic. **I was partially wrong about the severity and the mechanism, and I missed the actual fix that was applied in the diff under review.**

1.  **The Unbounded Join (My P0):** I correctly identified that `a.join()` without a timeout could hang the probe thread indefinitely if a backend hung. However, I failed to notice that the **diff under review (a6921162)** *already fixes this*. The code now uses `end = time.monotonic() + wait` and `a.join(max(0.0, end - time.monotonic()))`. I reviewed the *fixed* code but described the *bug* as if it were still present or only partially addressed. The other models (GLM, Muse) correctly noted that the bounded join is the key fix for the "hung family" scenario.
2.  **The KeyError (My P1):** I identified that if a thread died silently (e.g., `SystemExit`), `outs[bid]` would be missing, causing a `KeyError` in `run()`. The diff **fixes this** by checking `if b in outs` and falling back to a default tuple `(False, ..., None)` or `(None, ..., None)` based on `a.is_alive()`. I missed that this specific edge case was handled in the new logic.
3.  **Spend Meter (My P1):** I flagged potential under-reporting. GLM and Muse correctly identified that the spend meter logic is *correct* for the shared fleet context and that `local_since` accumulation is intentional. My concern was based on a misreading of the "shared key" implication.

**What I missed entirely:**
*   **The `families` keyword argument propagation:** The diff adds `families` to `probe_kw` only if the module's `probe_due` signature accepts it. I did not explicitly verify the backward compatibility path for older modules in my Cycle 1 notes, though I implied it was safe. Muse and GLM explicitly verified this.
*   **The `note_family` logic:** The diff adds `family` to `note()` calls only if the module's `note` signature accepts it. I did not trace this path in Cycle 1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **Bounded Join Fixes Hang** | GLM, Muse | **Agree** | The code `a.join(max(0.0, end - time.monotonic()))` ensures the probe thread cannot hang indefinitely. The `wait` is calculated from the max backend timeout + margin. This is correct. |
| **KeyError Prevention** | GLM, Muse | **Agree** | The list comprehension `got = [outs[b] if b in outs else ...]` prevents `KeyError` if a thread dies without writing to `outs`. This is a robust fix. |
| **Latest Answer Time** | GLM, Muse | **Agree** | `at = [ts for a, _, ts in got if a is True]` and `t = max(at) if at else self.clock()` correctly uses the latest *successful* answer's timestamp. If no answers, it uses the current time (when the probe finished), which is the correct fallback for the "no answer" case. |
| **Family Ordering** | GLM | **Agree** | `_flush` sorts families by time and prepends the familyless failure if it is earlier. This ensures the clock starts at the earliest failure, which is the correct semantic for "down" detection. |
| **Spend Meter Correctness** | GLM, Muse | **Agree** | The meter is designed for a shared fleet. `measured_spend` is the total delta, `local_since` is the local delta since last measure. The logic is sound. My Cycle 1 concern was unfounded. |
| **Backward Compatibility** | Muse | **Agree** | The use of `_takes(fn, name)` to check signatures before passing `family` or `families` ensures older modules are not broken. This is a clean pattern. |

**Disagreement:**
*   **None.** The other models' findings are accurate and align with the code in the diff. My Cycle 1 concerns were valid for the *pre-diff* code but are resolved by the *current* diff.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **Probe Thread Daemon Status:** The probe threads are `daemon=True`. If the main process exits, these threads are killed. This is acceptable for a probe, but if a probe is in flight during a graceful shutdown, the `probe_out` might not be set. However, `_report_probe` is called in `tick`, and the service loop joins threads on stop. The `probe_thread` is joined in `tick(wait=True)` if `wait` is set, but the main `run()` loop does not explicitly join the probe thread on shutdown. **Risk:** Low. The probe is a best-effort health check. If it's killed, the next start will re-probe.
2.  **`time.monotonic()` vs `self.clock()`:** The join timeout uses `time.monotonic()`, while the probe outcome timestamp uses `self.clock()` (which is `time.time` by default). This is correct: `monotonic` is for durations, `time` is for wall-clock timestamps. No issue.
3.  **`sorted(self.router.chain(self.probe_role))`:** The chain is sorted by backend ID. This ensures deterministic ordering of the `got` list, which is important for the `zip(chain, asks)` logic. If the chain order changed between calls, the `zip` would misalign. Sorting prevents this. **Good practice.**
4.  **`PROBE_WAIT_MARGIN_S = 15.0`:** This margin is added to the max backend timeout. If a backend has a 60s timeout, the probe waits 75s. This is reasonable to allow for network jitter or slow responses that are still within the "answered" category.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 7/10 | 9/10 | The critical race condition and KeyError are fixed in the diff. The logic for latest answer time and family ordering is correct. |
| **Law Compliance** | 9/10 | 9/10 | No changes. L-x, L-l, L-m are still compliant. |
| **Robustness** | 6/10 | 8/10 | The bounded join and KeyError prevention significantly improve robustness against hung backends and thread crashes. |
| **Maintainability** | 8/10 | 8/10 | The code is well-commented and the backward compatibility checks are clear. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The previous P0 (unbounded join) is fixed.

**P1 HIGH:**
1.  **Probe Thread Shutdown Handling:** Ensure the probe thread is joined or cancelled on service shutdown to avoid orphaned threads or partial state. *File: `pipeline/ingest/service.py` (shutdown logic) / `downsignal.py`.*
    *   *Mitigation:* The probe is daemon, so it won't block exit. But `probe_out` might be stale. Acceptable for a health check.

**P2 MEDIUM:**
1.  **`PROBE_WAIT_MARGIN_S` Tuning:** 15s is a heuristic. Consider making it configurable or based on the backend's `timeout_s` percentage. *File: `downsignal.py`.*
2.  **Logging for Probe Outcomes:** The `why` string is logged, but the individual backend outcomes are not. Adding a debug log for each backend's probe result would aid troubleshooting. *File: `downsignal.py`.*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The bounded join with `time.monotonic()` and the `KeyError`-safe outcome collection in `_start_probe` is the highest-leverage change.** It transforms the probe from a potential single point of failure (one hung backend stalls the entire health check) into a resilient, parallel health check that always reports within a predictable deadline. This directly addresses the "false outage" issue that motivated the amendment.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The shared module (`heimdall_health.py`) must be updated to the amended version (3cf4c42f) to support `probe_result(True)` clearing the clock and the `family`/`families` keywords. The watcher code is backward compatible, but the *benefit* of the amendment (resetting the clock on probe answer) requires the new module.
2.  The `providers.json` must be deployed with the new `heimdall_muse_probe` backend and the updated `probe` role chain.
3.  The service must be restarted to load the new module and config.

**Risk Assessment:**
*   **Low Risk:** The changes are isolated to the probe logic and config. The mining pipeline is unaffected.
*   **Fail-Safe:** If the probe fails or hangs, the bounded join ensures it doesn't block the service. If the module is old, the watcher falls back to the previous behavior (no family keywords).
*   **Verification:** The tests in `test_signal.py` cover the new logic, including the bounded join and family ordering.

**Conclusion:** The code is production-ready. The previous concerns are resolved. The amendment correctly implements the orchestrator's ruling.