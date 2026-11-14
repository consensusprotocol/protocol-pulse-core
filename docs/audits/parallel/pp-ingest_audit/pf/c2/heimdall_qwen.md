# heimdall_qwen (qwen/qwen3.8-27b, 343.6 s, $0.010, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the `watch.py` logic and the `providers.py` router. I missed several critical details that the other models (specifically GLM and Muse) caught:

1.  **The `cycles.py` Crash Safety (Minimax/GLM insight):** I did not review `cycles.py` in Cycle 1 because it wasn't explicitly highlighted in the diff summary as a "core" file, but the diff shows significant changes. GLM and Minimax noted that `video_entry` could crash if `mined` or `hook_ts` were `None` in certain edge cases, or if the string formatting failed. The Cycle 2 diff adds a `try/except` around `video_entry` in `compose` (line 109-112) and fixes the `max()` call to handle `None` values (line 72). I missed this potential crash vector in the reporting layer.
2.  **The `stats.py` `by_source` Logic (Muse insight):** I noted the new metric but didn't verify the SQL query change. Muse correctly identified that `discovered_via` was added to the `SELECT` clause in `stats.py` (line 31) to support the new `by_source` function. I missed verifying that the SQL query actually retrieves the column needed for the new metric.
3.  **The `spend.py` Ordering Logic (GLM insight):** I missed the subtle change in `_rewrite_top` in `spend.py` (lines 58-60). The logic now explicitly orders the `CYCLES_PREFIX` line to sit *immediately after* the `SWITCH_RE` line. I assumed the order was preserved by insertion, but the code now actively re-sorts the block. This is a critical detail for the STATE file's readability and compliance with the "standing order."
4.  **The `watch.py` Error Detail Asymmetry (GLM/Muse insight):** I noted the error accumulation but didn't explicitly flag that RSS errors *drop* the detail string while Playlist errors *keep* it. GLM and Muse both identified this asymmetry (line 211 in `watch.py`). I considered it "correct" based on old behavior but failed to explicitly call out that the *new* code path makes this asymmetry less obvious to future maintainers.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM/Muse on `watch.py` Error Handling:** The logic `err = f"{err + '; ' if err else ''}{e.kind}" + (f": {e.detail[:160]}" if get is playlist else "")` is correct but fragile. If `rss_mode` is False and `playlist_first` is True, and the playlist fails, we get `playlist_unreadable: <detail>`. If we then try RSS (which is skipped), we stop. If `playlist_first` is False, and RSS is skipped, and Playlist fails, we get `playlist_unreadable: <detail>`. The behavior is consistent with the old code, but the single-line implementation is harder to audit.
*   **Agree with Muse on `stats.py`:** The addition of `publish_to_discovered_min_by_source` is a high-value metric. It directly measures the "6-minute gain" claimed in the design doc. The implementation is sound: it filters for `live_m` (live discoveries) and groups by `discovered_via`.
*   **Disagree with Qwen (Self) on `providers.py` Cache/Frozen Logic:** In Cycle 1, I raised a "Bug" about frozen backends using cache. I now agree with the Cycle 1 Consensus and GLM/Muse that this is **compliant**. The design explicitly states: "A frozen vendor's back-end is never called... its stored validated replies cost nothing and may be re-read." The code at `providers.py:851` checks `enabled` (config) but *not* `frozen` before checking cache. This is correct because a frozen backend is still "enabled" in the config sense (it exists), just not callable. The cache hit bypasses the call entirely.
*   **Agree with GLM on `cycles.py` Fix:** The change from `max(t for t in ...)` to `max([t for t in ...] or [None])` is a necessary fix to prevent `ValueError` when both `mined` and `hook_ts` are `None`.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`cycles.py` Line 72: `None` Handling in `max`:**
    The code `return text, max([t for t in (mined, v["hook_ts"]) if t] or [None]) if (mined or v["hook_ts"]) else None` is robust. However, if `mined` is a timestamp and `hook_ts` is `None`, it returns `mined`. If both are `None`, it returns `None`. This is correct. The `try/except` in `compose` (line 109) ensures that if `video_entry` *still* crashes (e.g., due to a bad `v` dict), the whole line doesn't fail. This is a good defensive pattern.

2.  **`watch.py` Line 205: `if get is rss and not rss_mode: continue`**
    This check happens *inside* the loop. If `playlist_first` is `True`, the loop is `(playlist, rss)`.
    - Iteration 1: `get` is `playlist`. `get is rss` is `False`. Proceeds to `try`.
    - Iteration 2: `get` is `rss`. `get is rss` is `True`. If `rss_mode` is `False`, `continue`.
    This is correct. It prevents calling RSS if the canary says it's down.

3.  **`stats.py` Line 31: SQL Column Addition**
    The query now selects `discovered_via`. This column exists in the `videos` table (defined in `queue.py` line 36). The `by_source` function uses `m["discovered_via"]`. This is correct.

4.  **`spend.py` Line 58-60: Block Reordering**
    The code:
    ```python
    cyc = lambda h: h.startswith(CYCLES_PREFIX + " TO ")
    block = ([h for h in block if SWITCH_RE.match(h)] + [h for h in block if cyc(h)] +
             [h for h in block if not SWITCH_RE.match(h) and not cyc(h)])
    ```
    This ensures the Switch line is first, the Cycles line is second, and everything else is third. This is a strict ordering requirement for the STATE file. The logic is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **watch.py** | 9/10 | 9/10 | Logic is sound. Error asymmetry is a minor readability issue, not a bug. |
| **providers.py** | 8/10 | 9/10 | Clarified that cache/frozen logic is compliant. No bugs found. |
| **stats.py** | 8/10 | 9/10 | New metric is well-implemented and valuable. |
| **cycles.py** | N/A | 9/10 | Crash safety improvements are robust. |
| **spend.py** | N/A | 9/10 | Ordering logic is correct and necessary. |
| **Overall** | 8.5/10 | 9.2/10 | High confidence in correctness. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`watch.py:211` Error Detail Asymmetry:** While not a bug, the fact that RSS errors drop detail while Playlist errors keep it is a maintenance hazard. **Recommendation:** Add a comment explaining why RSS detail is dropped (e.g., "RSS errors are usually HTTP codes, detail is redundant").
2.  **`cycles.py:109` Exception Handling:** The `try/except` around `video_entry` is good, but the error message `f"{e['video_id']}: its row could not be read ({type(x).__name__})"` might be too generic. **Recommendation:** Log the full traceback to the service log for debugging, even if the STATE line is sanitized.

**P2 MEDIUM:**
1.  **`stats.py:155` `by_source` Function:** The function name is generic. **Recommendation:** Rename to `publish_to_discovered_by_source` for clarity.
2.  **`spend.py:58` Lambda in Loop:** The `cyc` lambda is defined inside `_rewrite_top`. **Recommendation:** Move it to a module-level constant or function for performance (negligible here, but cleaner).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of `publish_to_discovered_min_by_source` in `stats.py` is the highest-leverage change. It provides the **empirical evidence** needed to validate the "Playlist First" strategy. Without this metric, the 6-minute gain is a claim; with it, it is a measured fact that can be monitored for regression.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `cycles.py` crash safety fix is verified by the test suite (361 tests passed).
2.  The `stats.py` new metric is visible in `live.json` and matches the expected "6-minute gain" in the A/B test data.
3.  The `spend.py` ordering logic is verified to place the Cycles line immediately after the Switch line in the STATE file.

The code is robust, well-tested, and the changes are minimal and focused. The "Playlist First" strategy is sound, and the fallback logic is correct. The error handling is defensive, and the metrics are valuable. I recommend shipping.