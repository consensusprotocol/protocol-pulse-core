# qwen3.8-27b (qwen/qwen3.8-27b) 50 s finish=stop usage in 30128 / out 2339 usd~0.125 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok-4.20** correctly identified the `par["used"]` edge case where a first-screen exception leaves `used=0` in the report. While the build fails (so no "successful" report is printed), the `finally` block still executes `ahead.result()`, meaning the parallel thread's spend is tallied and the exception propagates. This is fail-safe, but the logic is subtle.

**GLM-5.3-Flash** (M5) caught a potential `AttributeError` in `_Tally.call` if `rep.usage` is a non-dict truthy value (e.g., a list). The code `u.get("usd_reported")` would crash. The current diff (line 213) uses `isinstance(u, dict)`, which **fixes** this. I missed that the Cycle 1 code might have been different or that I should have verified this specific guard.

**Qwen3.8-27B** hallucinated a "critical race condition" on the cache, but its own trace conceded the `CACHE_LOCK` makes it safe. It correctly identified the "wasted spend" on moments that fail the first screen, which is the intended behavior of Ruling 101 (reported as extra spend).

**My Cycle 1 Miss:** I did not explicitly verify that `effective_deadline` (the new function in `providers.py`) correctly handles the case where `deadline_s` is passed by the caller (the first screen's 120s) vs. when it falls back to `role_deadline`. The diff shows `dl = deadline_s or self.role_deadline(role, b)`. If `deadline_s` is 120 (truthy), it uses 120. Then it checks if the role is a verdict role and if the table has a row. If so, it replaces `dl` with the table's value. This is correct.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok's "wait=0" condition:** **Agree.** If the leading leg is Grok (no Heimdall family available), `step_a_plan` returns `parallel: False` because `heim` is False. The estimate is irrelevant because it's sequential. If a Heimdall leg leads but has no deadline row (unlikely, as `effective_deadline` falls back to gateway 120s), `dl` would be 120, not 0. The only way `dl` is 0/None is if `effective_deadline` returns None. `effective_deadline` returns None only if no deadline applies (Grok with no caller deadline, or writer). But `step_a_plan` only considers legs that are *not* writers and *not* down. If the leading leg is Grok, `heim` is False, so `parallel` is False. If the leading leg is Heimdall, `effective_deadline` will return at least the gateway's 120s (or the table's row). So `wait` will never be 0 for a Heimdall leg. **Disagree with Grok's concern that this is a bug; it's a non-issue because Grok leading forces sequential.**
*   **GLM's M1 (p90 interpolation):** **Agree.** It's a cosmetic issue. The deadline is clamped.
*   **GLM's M4 (Breaker opens mid-build):** **Agree.** The plan is made at `step_a_plan` time. If the breaker opens later, the estimate is stale. This is acceptable; the build still completes, just slower than estimated.
*   **Qwen's "Critical" Race:** **Disagree.** The cache is protected by `CACHE_LOCK`. The "waste" is intentional and reported.

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding 1: `step_a_plan` uses `router.chain("context_verdict", kind="step_a_first")`**
In `package.py:243`, `step_a_plan` iterates over `router.chain(...)`. The `Router.chain` method (unchanged code) returns the list of backend names for that role and kind. Under `heimdall_first`, the chain for `step_a_first` is `[glm, deepseek, Grok]`. The code filters out writers, down, and breaker-open. It picks the first one. This is correct.

**Finding 2: `confirm_ahead` passes `deadline_s=None`**
In `package.py:268`, `confirm_ahead` calls `prescreen` with `deadline_s=None`. This means the second screen (Grok) will use `effective_deadline` with `deadline_s=None`. `effective_deadline` will then call `role_deadline`. For Grok (non-Heimdall gateway), `role_deadline` returns None (unless the gateway has a configured deadline, which Grok does not in the standard config). So Grok's confirm-ahead calls are **unbounded**. This matches Ruling 88(c) ("Grok's own batch... and no deadline"). This is correct.

**Finding 3: `prewarm_used` logic**
In `package.py:285`, `prewarm_used` checks `b2.vendor != b1.vendor and b2.family != b1.family`.
*   `b1` is the backend of the first verdict (from `a_by`).
*   `b2` is the backend of the confirm-ahead verdict (from `pre_by`).
*   If the first verdict was from Heimdall (e.g., DeepSeek), and the confirm-ahead was from Grok, `b1.vendor` is "heimdall/deepseek", `b2.vendor` is "xai". They differ. `b1.family` is "deepseek", `b2.family` is "grok". They differ. So `prewarm_used` counts it.
*   If the first verdict was from Grok (e.g., because Heimdall was down), and the confirm-ahead was from Grok (wait, `confirm_ahead` excludes Heimdall, so it *must* be Grok or another non-Heimdall). If the first verdict was Grok, `b1.vendor` is "xai". `b2.vendor` is "xai". They are the same. So `prewarm_used` does NOT count it. This is correct: "a moment whose first verdict came from Grok itself is screened off it as before."

**Finding 4: `effective_deadline` and Writers**
`effective_deadline` (providers.py:1070) checks `if dl and role in set(...)`. It does **not** check if the backend is a writer. However, `Router.call` (providers.py:1246) calls `effective_deadline`. If a writer call is made, `role` is likely `angle_write` or similar, which is **not** in `verdict_roles`. So `dl` remains the caller's or `role_deadline`'s value. `role_deadline` for a writer (non-verdict role) returns None (unless the gateway has a deadline, which writers don't). So writers are unbounded, as before. Correct.

**Finding 5: `deadline_table.load` and `record_dir`**
`load` (deadline_table.py:113) takes `record_dir`. If `record_dir` is None, it computes an empty table and **does not save** (line 126-127). This prevents overwriting a good table with an empty one if the record dir is missing. Correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Deadline Table** | 9/10 | 9/10 | Robust. Clamping works. Staleness handled. |
| **Router Integration** | 8/10 | 9/10 | `effective_deadline` is clean. No regressions for writers/probes. |
| **Parallel Plan** | 7/10 | 8/10 | Logic is sound. Estimate staleness is acceptable. |
| **Confirm Ahead** | 8/10 | 9/10 | Thread safety verified. Spend tallying is correct. |
| **Reporting** | 8/10 | 9/10 | `ruling_101_line` is honest. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`package.py:252`**: `wait = rounds * dl if dl else 0.0`. If `dl` is 0.0 (falsy), wait is 0.0. `effective_deadline` returns `None` or a positive float. It never returns 0.0. So this is safe.
2.  **`deadline_table.py:104`**: The `p90` stored in the row is unclamped, but `deadline_s` is clamped. `text()` prints `p90`. This is cosmetic.
3.  **`package.py:213`**: `_Tally.call` uses `isinstance(u, dict)`. If `u` is a list, `rep_usd` is None, and it falls back to `rep.usd`. This is safe.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `effective_deadline` in `providers.py` is the highest-leverage change. It cleanly separates the "gateway default" (120s) from the "model-specific" (table row), ensuring that the breaker measures against the correct deadline without breaking the existing `role_deadline` contract for non-verdict roles.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `DEADLINE_TABLE.json` file must be writable by the build process (or the build must run in an environment where `record_dir` is valid). If it cannot be written, the table is computed in-memory and not saved, which is fail-safe.
2.  The `CACHE_LOCK` must be held during `_cache_put` (verified in unchanged code).
3.  The `ThreadPoolExecutor` for `confirm_ahead` must be shut down (verified in `finally` block).

The code is robust, the rulings are implemented faithfully, and the edge cases (Grok leading, breaker opening mid-build, stale estimates) are handled with fail-safe defaults.