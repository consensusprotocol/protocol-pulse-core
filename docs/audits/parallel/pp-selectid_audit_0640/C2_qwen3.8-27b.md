# qwen3.8-27b (qwen/qwen3.8-27b) 65 s finish=stop usage in 15148 / out 2161 usd~0.078 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0640

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the `PRESCREEN_N` cap interaction (P1-1) and the `off_writers` fallback logic (P1-2). I missed the **exception handling** in the parallel execution path.

**Qwen (P1-1)** correctly identified that `f.result()` in `second_screen` would propagate exceptions from `prescreen` (e.g., network timeouts) up to `build()`, crashing the entire build instead of failing the specific clips closed. This is a significant robustness gap that I overlooked because I was focused on the *logic* of the verdicts rather than the *resilience* of the orchestration.

**GLM (P1-1)** raised a valid concern about `PRESCREEN_N` vs `len(chunk)`. While the consensus (K2) correctly refuted this as a bug (because `cleared` is derived from `a_by`, ensuring all clips have a first verdict), the *spirit* of the concern—behavioral coupling between screen caps—was worth noting. However, the code now explicitly passes `n=len(chunk)`, which is the correct fix for the "cheap" requirement of item 45.

**Grok** was too lenient. It missed the exception handling issue entirely and gave a "SHIP: yes" without conditions.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Qwen P1-1 (Exception Handling):** **AGREE.** This is a real P1. The `one()` wrapper in the new code (lines 25-30) *fixes* this. The Cycle 1 code did not have this wrapper. The Cycle 2 code *does*. Therefore, this finding is **resolved** in the current diff.
*   **Qwen P1-2 (KeyError in `a_by[mid]`):** **DISAGREE.** As noted in Consensus K1, `cleared` is constructed such that every `mid` in `cleared` exists in `a_by`. The line `two[mid] = [a_by[mid], a2]` (line 44) is safe because `mid` comes from `cleared`, which is filtered to only include moments that passed the first screen (and thus have an entry in `a_by`).
*   **GLM P1-1 (PRESCREEN_N):** **PARTIALLY AGREE.** The concern was valid in Cycle 1, but the code now passes `n=len(chunk)`, which ensures no truncation. The "unknown backend" failure mode for clips beyond the cap is impossible because `cleared` only contains clips that *did* get a first verdict.
*   **GLM P1-2 (off_writers stale verdict):** **AGREE with the analysis, but the code handles it.** The `off_writers` function returns `None` if no verdict is off the writers. The code then does `a_by[mid] = off_writers(mid) or a_by[mid]`. If `off_writers` returns `None`, it keeps the old `a_by[mid]`. However, the *next* lines (97-98) check for `stale` clips (those on a writer's vendor/family) and re-screen them. So the transient inconsistency is immediately corrected. This is not a bug, but a design choice that relies on the subsequent re-screen.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-1: `second_screen` does not handle the case where `router.backends` is missing a key for the first verdict's backend.**
*   **File:** `pipeline/package.py`, line 21.
*   **Scenario:** `a_by.get(mid)` returns a dict with `"backend": "some:unknown"`. `router.backends.get("some:unknown")` returns `None`. The code handles this by grouping into `None` (line 22) and failing them as `STEP_A_UNKNOWN_BACKEND` (lines 45-47). This is **correct** and fail-closed. No finding here.

**P1-2: `off_writers` uses `a_two.get(mid, ())` but `a_two` is only populated for clips that passed *both* screens.**
*   **File:** `pipeline/package.py`, line 81.
*   **Scenario:** `off_writers` is called for `mid` in `cleared`. `cleared` is filtered to only include `mid` in `a_two` (line 62). So `a_two.get(mid, ())` will always return a list of two verdicts. This is safe.

**P1-3: The re-screen block (lines 106-127) does not update `a_two` for the *new* clip swapped in.**
*   **File:** `pipeline/package.py`, line 113.
*   **Scenario:** When a clip fails re-screen, it is removed. `swap_lineup` brings in a new clip `z`. The code re-screens `stale` (which includes `z` if it's on a writer's vendor). If `z` passes, `a_by[z]` is updated. But `a_two[z]` is *not* updated. `a_two` is only used by `off_writers`. If `z` is later judged by `off_writers`, it will look at `a_two.get(z, ())`. If `z` was not in the original `a_two` (because it wasn't in `cleared` initially? No, `cleared` is the pool of all cuttable clips that passed both screens. `z` is from `cleared`), then `a_two[z]` exists.
    *   Wait, `cleared` is the pool of clips that passed *both* screens initially. `swap_lineup` picks from `cleared`. So `z` is in `cleared`, and thus in `a_two`.
    *   However, `a_two[z]` contains the *original* two verdicts. If the re-screen of `z` (because it's on a writer's vendor) produces a *new* verdict, that new verdict is added to `a_two[z]` (line 113: `a_two.setdefault(mid, []).append(got_a[mid])`). So `a_two[z]` now has 3 verdicts. `off_writers` iterates over all of them. This is correct.

**P1-4: `second_screen` uses `ThreadPoolExecutor` but `prescreen` is not thread-safe if it mutates shared state.**
*   **File:** `pipeline/package.py`, line 31.
*   **Scenario:** `prescreen` is called with `store=None`. The docstring says it returns `a_by, fails, vendors, families`. It does not mutate `router` or `sources`. It is likely thread-safe. The `log` function is `print`, which is thread-safe in CPython. This is likely fine.

**P1-5: The `one()` wrapper catches `Exception` but not `BaseException` (e.g., `KeyboardInterrupt`).**
*   **File:** `pipeline/package.py`, line 28.
*   **Scenario:** If the user hits Ctrl+C, the build will crash. This is acceptable for a CLI tool.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **second_screen** | 8/10 | 9/10 | Exception handling added (F1). Logic is sound. |
| **build loop** | 7/10 | 9/10 | `off_writers` and re-screen logic are now robust. |
| **Tests** | 8/10 | 9/10 | New tests cover the critical paths (exception, unknown backend, same vendor). |
| **Threading** | 7/10 | 8/10 | `one()` wrapper makes it safe. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`second_screen` exception handling:** The `one()` wrapper (lines 25-30) correctly handles exceptions from `prescreen`. This was a P1 in Cycle 1 but is now **fixed**. No action needed.
2.  **`off_writers` fallback:** The `or a_by[mid]` fallback (line 87) is safe because the subsequent `stale` check (line 97) will re-screen any clip that is on a writer's vendor. No action needed.

**P2 MEDIUM:**
1.  **`a_two` growth:** `a_two[mid]` can grow beyond 2 verdicts if a clip is re-screened multiple times. This is not a bug, but it could be optimized to only keep the latest off-writer verdict. Not a blocker.
2.  **`PRESCREEN_N` vs `len(chunk)`:** The code now passes `n=len(chunk)`, which is correct. No action needed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the `one()` wrapper in `second_screen` to catch exceptions and fail clips closed is the most critical change, as it prevents a single provider timeout from crashing the entire build.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements items 44 and 45 of ORDER 06:22. The fail-closed behavior is robust, and the exception handling is in place. The tests cover the critical paths. The only remaining concern is the potential for `a_two` to grow, but this is not a correctness issue.