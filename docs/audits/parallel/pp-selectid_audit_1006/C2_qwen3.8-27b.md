# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 8811 / out 1438 usd~0.048 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1006

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the `first_fresh` divergence (P1-1) and the `fresh_key` all-unknown bug (P1-2). However, I **missed the specific mechanism** of the all-unknown bug that Qwen and GLM highlighted with concrete numerical examples. I noted the docstring/code disagreement but did not explicitly calculate that an all-unknown line-up would rank as *newer* (1.0h) than a 70h-old line-up. The fix (`UNKNOWN_AGE_H = 1.0e6`) addresses this, but I should have been more explicit about the severity of the inversion in Cycle 1.

I also **underestimated the impact of the `first_fresh` call** in `build()`. I flagged it as a potential divergence but didn't fully trace that `dropped` and `doomed` are empty at that point, meaning the `lineup_for` call in `first_fresh` is actually *identical* to the first `lineup_for` call in the main loop. This means the "divergence" I feared in Cycle 1 (P1-1) is actually **non-existent** for the first pass, but the cost is real (double computation).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Position | Reasoning |
| :--- | :--- | :--- |
| **GLM P1-1** (`first_fresh` without `dropped`/`doomed`) | **Disagree (Non-Issue)** | As verified in the consensus (A1), `dropped` and `doomed` are empty when `first_fresh` runs. The line-up computed is the same as the first one in the loop. No divergence. |
| **GLM P1-2 / Qwen P1** (All-unknown age bug) | **Agree (Fixed)** | The fix `UNKNOWN_AGE_H = 1.0e6` correctly ensures unknown ages rank as oldest. The test at line 121 verifies this. |
| **Grok P2** (Extra `lineup_for` cost) | **Agree (P2)** | The cost is real but negligible for 3 angles. The consensus (A3) correctly notes this is milliseconds. |
| **Qwen P2-3** (Hook in mean age) | **Agree (Intended)** | K2 states the hook is included. The code matches the ruling. |
| **Qwen P2-4** (Test coverage gap) | **Agree (Fixed)** | The new test at line 120-121 covers the all-unknown case. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: `first_fresh` is redundant computation.**
`pipeline/package.py:1528-1531`
`first_fresh` calls `lineup_for` to determine if an angle has a fresh clip. Then, in the main loop (line 1681-1683), `lineup_for` is called *again* for the same angle with the same parameters (since `dropped`/`doomed` are empty). This is a pure performance waste. While negligible, it is architecturally sloppy. The result of `first_fresh` could be cached or the angle sorting could be deferred until after the first `lineup_for` call in the loop.

**P2-2: `fresh_key` is called on `[h] + order` in `lineup_for`, but `first_fresh` calls it on `segs`.**
`pipeline/package.py:1529` vs `pipeline/package.py:1017`
In `lineup_for`, `fresh_key` is called on `[h] + order` (the full line-up including hook). In `first_fresh`, `fresh_key` is called on `segs` (which is the return of `lineup_for`, i.e., `[h] + order`). This is consistent. No issue.

**P2-3: `pool_fill` passes `now` but `pool_fill` is only called if `segs is None` in the main loop.**
`pipeline/package.py:1687`
If `lineup_for` returns `None` (no valid line-up), `pool_fill` is called. `pool_fill` calls `lineup_for` with `now`. This is correct. However, if `lineup_for` returns a non-fresh line-up, `pool_fill` is *not* called. This is correct per the ruling (preference, not gate).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **fresh_key** | P1 | P2 | The all-unknown bug is fixed. The remaining issue is only the cost of the extra call. |
| **lineup_for** | P2 | P2 | No change. The key ordering is correct. |
| **build()** | P1 | P2 | The `first_fresh` divergence is non-existent. The cost is P2. |
| **Tests** | P2 | P2 | The new tests cover the critical cases. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
None.

**P1 HIGH**
None.

**P2 MEDIUM**
1. **`pipeline/package.py:1528-1531`**: `first_fresh` performs a redundant `lineup_for` call. Consider caching the result or deferring the sort.
2. **`pipeline/package.py:1017`**: `fresh_key` is called on `[h] + order`. Ensure that `h` (the hook) is always included in the mean age calculation. This is correct per K2, but worth a comment.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fix to `UNKNOWN_AGE_H` is the most critical change, as it prevents a silent inversion of the freshness preference for line-ups with missing publish times.

## 7. PRODUCTION READY?

**Yes.**

The code is correct, the tests are comprehensive, and the performance impact is negligible. The only remaining issue is a minor performance optimization (P2-1) that does not affect correctness.