# heimdall_qwen (qwen/qwen3.8-27b, 209.6 s, $0.008, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on concurrency (race conditions) and the logic of `carry_forward`, but I missed several critical implementation details and edge cases that the other models identified:

1.  **The `altcoin` Logic Inversion (MUSE C1):** I analyzed the `altcoin` logic in `carry_forward` and concluded it was "effectively OR with None treated as True (fail closed)." I was **wrong**. MUSE correctly identified that `fx.get("altcoin") is not False` evaluates to `True` when the key is **missing** (`None`). This means a missing flag in the *new* line would be treated as `True` (altcoin) if the *old* line was also missing or `True`. More critically, if the new line explicitly had `altcoin: False` but the old line was missing, the result would be `True` (because `False is not False` is `False`, but `None is not False` is `True`, so `False or True` is `True`). This violates the "fail closed" principle for negative flags. The code in the diff (lines 200-203 of `ledger.py`) has been **fixed** in the working tree provided for this review to handle `None` explicitly:
    ```python
    fx["altcoin"] = True if True in (a_new, a_old) else (False if a_new is False else None)
    ```
    My Cycle 1 analysis was based on the *pre-fix* logic or a misreading of the Python semantics. I missed that `None` (missing) is distinct from `False`.

2.  **Hook Duration Measurement Bias (GLM BUG 5):** I verified that `duration_estimate_s` is used for segments and concluded it was "Correct." GLM correctly pointed out that for segment-timed captions, the `end` time of the last token often includes trailing silence or padding, making the measured duration systematically longer than the spoken duration. This causes valid 4-14s hooks to be dropped if the segment padding pushes them over 14s. While the consensus noted this was measured and found to be "approximate both ways," it is still a P1 risk for hook yield.

3.  **Cost Query Double-Counting (GLM BUG 3 / MUSE C3):** I missed that `hook_cost_usd` is a cumulative sum of *all* hook calls for a video, not just the current pass. The log message in `service.py` (line 357) says "for the video's hook passes so far," which is accurate, but the `live.json` stats and the `hooks` command output might mislead operators into thinking it's the cost of the *last* pass. This is a cosmetic/clarity issue, not a crash, but it was missed in my initial review.

4.  **Purge Fail-Closed Path (GLM / MUSE):** I did not deeply audit the `purge.py` changes in Cycle 1. The other models correctly identified that the previous code had a fail-open path where unreadable delivered records or `/proc` issues could lead to deletion. The new code (lines 118-150, 226-250 in `purge.py`) correctly adds `problems` and refuses to delete if the delivered set or process list is unreadable. I missed this improvement in my initial scan.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Reviewer | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **`altcoin` logic inversion** | MUSE (C1) | **AGREE** | The original logic `is not False` treats `None` as `True`. The fix in the diff (`True if True in ... else (False if ... is False else None)`) is correct and fail-closed. |
| **Hook duration bias** | GLM (BUG 5) | **PARTIALLY AGREE** | It is a real measurement artifact. However, the consensus notes that the builder re-judges with word timing, and the dropped lengths are now logged. It is a P1 for yield, not a P0 for safety. |
| **Cost double-counting** | GLM (BUG 3) | **AGREE** | It is cumulative. The log message is updated to reflect this. It is a clarity issue, not a bug. |
| **Race condition in `_append`** | QWEN (Self, C1) | **AGREE** | `wlock` serializes read-modify-write within the process. `fcntl` in `append` protects against multi-process (though design says single-process). Correct. |
| **`hook_due` NULL `published_ts`** | QWEN (Self, C1) | **AGREE** | `MINED` videos always have `published_ts` due to `fetch.py` logic. Correct. |
| **Purge fail-closed** | GLM/MUSE | **AGREE** | The new code correctly refuses to delete if `problems` are found in `delivered()` or `open_paths()`. |
| **`role_hint` inheritance** | QWEN (Self, C1) | **AGREE** | A later pass should not remove a `hook` hint from an earlier pass. The `carry_forward` logic correctly preserves it. |

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`hook_video` Crash Handler and `hook_inflight` (P2):**
    In `service.py` (lines 380-382), the `finally` block discards the video from `hook_inflight`. However, if `self.hooks.submit` raises an exception (e.g., executor shutdown), the video is added to `hook_inflight` (line 395) but the `finally` block in `hook_video` is never reached because `hook_video` was never called. The video remains in `hook_inflight` forever, blocking that slot.
    *   **Impact:** Low. `submit` only raises on shutdown. But it is a latent leak.
    *   **Fix:** Wrap `submit` in a try/except in `hook_once` to discard on failure.

2.  **`carry_forward` `about_bitcoin` Logic (P1):**
    The fix in `ledger.py` (line 203) is:
    ```python
    fx["about_bitcoin"] = False if False in (b_new, b_old) else (True if b_new is True else None)
    ```
    This is **correct** for fail-closed: if either says `False`, it's `False`. If both say `True`, it's `True`. If one is `None` and the other is `True`, it's `True` (wait, `b_new is True` is `True`, so it becomes `True`). If one is `None` and the other is `False`, it's `False`. If both are `None`, it's `None`.
    *   **Edge Case:** If `b_new` is `None` and `b_old` is `True`, the result is `True`. This is correct (the earlier pass said it was about Bitcoin, the new pass didn't measure it, so we keep the earlier positive).
    *   **Edge Case:** If `b_new` is `True` and `b_old` is `None`, the result is `True`. Correct.
    *   **Verdict:** The logic is sound.

3.  **`hook_due` Index (P2):**
    The query `SELECT * FROM videos WHERE state IN (?, ?) AND hook_ts IS NULL AND ...` uses `state` and `published_ts`. The index `videos_hook (state, published_ts)` is created. This is good. However, `hook_ts IS NULL` is not in the index. For a large table, this might still be slow. But given the scale (videos per day), it is acceptable.

4.  **`mine_video` `role` Parameter (P2):**
    In `mine.py` (line 389), `role = role or KINDS[kind]["role"]`. If a caller passes `role="mine"` with `kind="hook"`, the prompt is the hook prompt, but the role is `mine`. The validator uses `k["key"]` which is `hooks`. The router uses `role` to pick the chain. If `role="mine"`, it uses the `mine` chain. This is a latent trap. Currently, `service.py` passes `kind="hook"` and no `role`, so `role` becomes `hook`. Correct. But the API is fragile.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 9/10 | The `altcoin` fix is verified. The purge fail-closed path is solid. The hook duration bias is a known limitation, not a bug. |
| **Concurrency** | 9/10 | 9/10 | `wlock` and `hlock` are correctly used. The `hook_inflight` leak is minor. |
| **Security** | 9/10 | 9/10 | Prompt injection defenses (`_untrusted`, `SECURITY` blocks) are robust. Key redaction is correct. |
| **Maintainability** | 8/10 | 8/10 | The `KINDS` dict and parameterized `validator`/`schema` are clean. The `role` parameter in `mine_video` is slightly confusing. |
| **Performance** | 8/10 | 8/10 | The `hook_due` index helps. The `carry_forward` read is bounded by `since`. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The code is safe to ship.

**P1 HIGH:**
1.  **Hook Duration Bias:** The 4-14s gate on segment-timed captions may drop valid hooks due to trailing padding. *Mitigation:* The dropped lengths are logged (`dropped_s`), so this can be monitored. No code change required, but the builder should be aware.
2.  **`hook_inflight` Leak:** If `self.hooks.submit` raises, the video stays in `hook_inflight`. *Fix:* Add a try/except in `hook_once` to discard on submit failure.

**P2 MEDIUM:**
1.  **Cost Clarity:** `hook_cost_usd` is cumulative. The log message is updated, but `live.json` might mislead. *Fix:* Add a comment or rename the field in `stats.py` to `hook_cost_usd_cumulative`.
2.  **`mine_video` Role Parameter:** The `role` parameter can override the `kind`'s role. *Fix:* Remove the `role` parameter from `mine_video` and always use `KINDS[kind]["role"]`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The `carry_forward` logic fix for `altcoin` and `about_bitcoin` is the most critical change.** It ensures that the ledger's fail-closed discipline is maintained across passes, preventing a missing flag in a new pass from incorrectly overriding a measured flag in an earlier pass. This is the foundation of the data integrity for the hook pass.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  Monitor the `dropped_s` logs for the hook pass to ensure the 4-14s gate is not systematically dropping valid hooks due to segment timing bias.
2.  Verify that the `hook_inflight` set does not grow unbounded over time (it should be bounded by `HOOK_VIDEOS`).
3.  Ensure that the `purge.json` spec is valid and the `delivered` set is readable, as the purge will refuse to run if not.

The code is production-grade, with robust fail-closed logic, correct concurrency handling, and clear audit trails. The Ruling 80 hook pass is correctly implemented and integrated into the service loop.