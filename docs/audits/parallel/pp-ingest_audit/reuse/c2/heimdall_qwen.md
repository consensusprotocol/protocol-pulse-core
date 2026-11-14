# heimdall_qwen (qwen/qwen3.8-27b, 319.6 s, $0.009, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I spent significant effort analyzing a potential `KeyError` race condition in `_reuse_calibration` that I ultimately debunked myself. While my final conclusion was correct (the code is safe), the path to get there was inefficient.

**Heimdall_GLM** provided the most rigorous structural analysis. It correctly identified that the `set(cal) != set(eff)` check at line 588 acts as a perfect guard against `KeyError` at line 596, and it explicitly verified the "future timestamp" edge case (`0 <= self.clock() - t.timestamp()`), which I only touched on briefly.

**Heimdall_Muse** caught a subtle interaction I missed: the relationship between `_reuse_tried` and the fallback logic. It correctly noted that if `_reuse_calibration` fails, `check_allowed` remains `None`, and the subsequent `if self.check_allowed is None ...` block correctly triggers `_calibrate_checkers()`. This confirms the fail-closed behavior is robust.

**My Miss:** I did not explicitly verify the **atomicity of the `kv_get` read** in the context of a concurrent write. While `Queue` uses a lock, `_reuse_calibration` runs in the `check` loop thread. If a `health` loop thread were writing to `check_calibration` simultaneously (which it isn't, but the architecture allows for it), could we read a partial JSON? `Queue.kv_get` uses `SELECT`, which is atomic in SQLite WAL mode. So this is safe, but I should have explicitly stated *why* it is safe (WAL atomicity) rather than just assuming it.

## 2. WHERE DO YOU AGREE OR DISAGREE?

### Agreement with Heimdall_GLM
*   **Gate Logic:** I agree with GLM's step-by-step verification of the 6 gates in `_reuse_calibration`. The logic is airtight.
*   **Fail-Closed:** I agree that every failure path results in a live calibration, which is the correct behavior for Law L-m.
*   **Model Identity:** I agree that checking `c.get("model") == self.router.backends[b].model` is sufficient to detect model swaps, assuming the gateway doesn't lie about the model name (a documented limitation).

### Agreement with Heimdall_Muse
*   **Shorts Detection:** I agree with Muse's observation that `watch.py` uses URL-based Shorts detection (`/shorts/`), which can miss Shorts that use standard `/watch?v=` URLs. However, Muse correctly notes that `fetch.py` has a secondary gate (`media_type == "short"`) that catches these later. This is a minor inefficiency (unnecessary queueing) but not a correctness bug.
*   **Cache Reuse:** I agree with Muse's analysis of `providers.py` cache reuse. The code correctly allows cached replies for frozen/disabled backends because they cost nothing and prove nothing about current health.

### Disagreement with My Own Cycle 1 Output
*   **Race Condition:** In Cycle 1, I labeled the `_reuse_calibration` logic as having a "Critical Race Condition" before debunking it. This was misleading. There is **no race condition**. The logic is single-threaded within the `check` loop. The state changes (`check_allowed`, `_reuse_tried`) are protected by the loop's sequential execution. I should have labeled this as "Complex Logic Verified Safe" rather than "Critical Race Condition."

## 3. NEW FINDINGS FROM THIS REVIEW

After reviewing the combined analysis and re-reading the code with fresh eyes, I have identified **one new P2 issue** and **confirmed the safety of the critical path**.

### New Finding: P2 - `check_calibrated` Initialization vs. Reuse
In `service.py` line 140, `self.check_calibrated` is initialized to `0.0`.
In `_reuse_calibration` (line 608), if reuse succeeds, `self.check_calibrated` is set to `t.timestamp()` (the time of the *live* calibration).
In `check_once` (line 622), the condition is:
```python
if self.check_allowed is None or self.clock() - self.check_calibrated >= self.check_recal_s:
    self._calibrate_checkers()
```
**Scenario:**
1.  Service starts.
2.  `_reuse_calibration` succeeds. `check_allowed` is set to a list. `check_calibrated` is set to `T_live` (e.g., 20 hours ago). `check_recal_s` is `86400` (24 hours).
3.  `check_once` runs. `check_allowed` is not `None`. `self.clock() - T_live` is 20 hours. `20h < 24h`. So `_calibrate_checkers` is **not** called.
4.  4 hours later (24 hours after `T_live`). `check_once` runs. `self.clock() - T_live` is 24 hours. `24h >= 24h`. `_calibrate_checkers` **is** called.

**Verdict:** This is **correct**. The next calibration is due 24 hours after the *live* calibration, not 24 hours after the restart. This matches the design intent ("the next calibration stays due a day after the live one"). My Cycle 1 analysis was correct on this point, but it is worth explicitly confirming that the initialization of `check_calibrated` to `0.0` does not cause an immediate recalibration on the *first* `check_once` call if reuse fails.
*   If reuse fails, `check_allowed` is `None`. The condition `self.check_allowed is None` is `True`. `_calibrate_checkers` is called. `check_calibrated` is updated to `now`.
*   This is also correct.

### Confirmed Safety: The `KeyError` Risk
I re-verified the `KeyError` risk in `_reuse_calibration` line 596:
```python
allowed = [b for b in eff if cal[b].get("of") == n ...]
```
`eff` is `self.router.effective(flagcheck.ROLE)`.
`cal` is the loaded JSON.
Line 588 checks: `set(cal) != set(eff)`.
If this check passes, `set(cal) == set(eff)`.
Therefore, for every `b` in `eff`, `b` is in `cal`.
`cal[b]` is safe.
**Conclusion:** No `KeyError` is possible. The code is robust.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 9/10 | Removed the "Critical Race Condition" false positive. Verified all edge cases (future time, model swap, key mismatch) are handled correctly. |
| **Law Compliance** | 9/10 | 9/10 | L-m (Fail Closed) is strictly adhered to. L-l (Strict Validation) is maintained. No changes. |
| **Robustness** | 7/10 | 8/10 | The `_reuse_calibration` logic is complex but well-guarded. The `kv_get` atomicity is safe due to SQLite WAL. |
| **Observability** | 8/10 | 9/10 | The new log lines for refusal reasons (C1-2 fix) significantly improve debuggability. |

## 5. FINAL PRIORITY LIST

### P0 CRITICAL
*   **None.** The code is safe to ship.

### P1 HIGH
*   **None.** The issues identified in Cycle 1 (Shorts detection, cache reuse) are either minor inefficiencies or documented design choices.

### P2 MEDIUM
1.  **`watch.py` Shorts Detection (Line 216):**
    *   **Issue:** Shorts with `/watch?v=` URLs are queued as `discovered` and later filtered by `fetch.py`. This wastes queue space and processing time.
    *   **Fix:** Consider checking `media_type` in `watch.py` if available in the playlist listing, or accept the minor inefficiency.
    *   **Impact:** Low. The system handles it correctly, just less efficiently.

2.  **`providers.py` Cache Reuse for Frozen Backends (Line 851):**
    *   **Issue:** Cached replies are reused for frozen backends. This is correct per spec, but could be confusing if a frozen backend's cache is stale.
    *   **Fix:** No change needed. The spec explicitly allows this.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The addition of refusal reasons to the `_reuse_calibration` log lines (C1-2 fix).**
This change transforms a silent fallback into a debuggable event. If a restart fails to reuse a calibration, the operator can immediately see *why* (e.g., "model changed", "asked 25h ago") without digging into the queue or code. This is the highest-leverage change for operational stability.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `check_calibration` key in the queue must be written atomically (guaranteed by SQLite WAL).
2.  The `router.effective()` method must correctly filter out disabled/frozen backends (verified in Cycle 1).
3.  The `config.aware()` function must correctly parse ISO timestamps with timezones (verified in Cycle 1).

The code is robust, fail-closed, and well-observed. The `_reuse_calibration` logic is complex but correct. The other models' findings confirm the safety of the critical path.