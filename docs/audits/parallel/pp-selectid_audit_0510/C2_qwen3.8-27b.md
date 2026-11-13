# qwen3.8-27b (qwen/qwen3.8-27b) 69 s finish=stop usage in 16097 / out 2102 usd~0.080 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0510

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the loop termination logic and the budget split. However, the consensus (specifically **K3** and **glm P1-3**) correctly identified a subtle ordering issue in `swap_lineup` that I initially glossed over: the interaction between `SWAP_TOP` truncation and the "short clip only last" rule.

While I noted that `lineup_ok` is the final arbiter, I did not explicitly verify that the *candidate generation* in `swap_lineup` respects the positional constraints *before* applying the `SWAP_TOP` cap. If `SWAP_TOP` were applied to a list of candidates that included short clips for a non-last position, and the valid long clips were ranked lower than `SWAP_TOP`, the swap would fail to find a valid candidate even if one existed in the pool. The code *does* handle this correctly (line 73: `i == len(segs) - 1 or m["duration_s"] >= SHORT_CLIP_S` is in the filter *before* the sort and cap), but this was a critical verification point that required careful reading of the diff lines 66-75.

Additionally, **Grok** and **Qwen** correctly flagged the need to verify that `lineup_for`'s internal logic and `lineup_ok` are perfectly aligned. I verified this in Cycle 1 but did not explicitly cross-reference the `repeat_ok` logic in `lineup_ok` (lines 39-40) against the `supply_exception` usage in `build` (line 176, 184).

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **K1 (Loop Termination):** **Agree.** The `dropped` set is updated *before* `swap_lineup` is called (line 208). `swap_lineup` excludes `avoid` (which includes `dropped`) from its `free` pool (line 64). If `swap_lineup` fails, `lineup_for` is called with the updated `dropped` set. Since `lineup_for` excludes `dropped` moments, it cannot return the same line-up. The loop is bounded by `total < lineups` (8). No infinite loop.
*   **K2 (Hook in Weak Set):** **Agree.** Line 200-201 now includes the hook in the `weak` set calculation (`lb in by_lab and x < COHERENCE_MIN`). The old code had `lb != "hook"`. This is the core of Ruling 41.
*   **K3 (SWAP_TOP vs. Place Rules):** **Agree.** The code correctly filters candidates by the place's own rules (short clip only last) *before* sorting and capping by `SWAP_TOP`. This ensures that a valid long clip ranked 11th is not missed if 10 short clips are ranked higher but invalid for that position.
*   **K4 (Budget Clock Start):** **Agree.** `line = (time.time(), _spent(spend))` is set at line 193, *before* `medley()` is called. `package_over` uses this `line` as the start time. This matches the ruling "counted from the moment its own line-up's clips-alone verdict is asked." The search budget (`over_budget`) uses `t0` (build start). This split is correct.
*   **Grok's "SHIP: yes":** **Agree.** The code is robust.
*   **Qwen's "P0" (Infinite Loop):** **Disagree.** As established in K1, the loop is bounded. Qwen's own analysis eventually concluded this, but the initial "P0" label was misleading.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: `supply_exception` is called for swapped line-ups, but the exception text might be stale or misleading if the swap *removed* the duplicate channel.**
In `build`, if `swapped` is not None, `exception = supply_exception(segs, ctx)` is called (line 176). `supply_exception` checks for duplicate channels in the *new* `segs`. If the swap resolved the duplicate channel issue (e.g., swapped a clip from Channel A to Channel B, making all channels unique), `supply_exception` returns `None`. This is correct. However, if the swap *introduced* a duplicate (unlikely, as `lineup_ok` enforces one-per-channel unless `repeat_ok`), it would be caught. The logic is sound.

**P2-2: `out["search"]` reporting.**
Lines 242-246 add `out["search"]` with `lineups`, `limit`, `usd_reported`, `usd_estimate`, and `seconds`. This is a new field. It is correctly populated. The log line at 245-246 is also correct.

**P2-3: `rec["why"]` for failed writes.**
Lines 233-236 add a `rec["why"]` if no package was produced and no `why` was already set. This handles the case where all writes failed their gates. This is a good observability improvement.

**P2-4: `total` increment.**
Line 192: `total += 1` is inside the `while` loop, after `lineup_for` succeeds and before `medley` is called. This means `total` counts every line-up that is *judged* (i.e., sent to `medley`). This matches the ruling "up to 8 line-ups per build." If `lineup_for` returns `None`, the loop breaks (line 189-190) and `total` is not incremented. This is correct: a line-up that cannot be formed is not a "judged" line-up.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Loop Safety | 9/10 | 10/10 | Verified `dropped` update order and `lineup_for` exclusion. No loop risk. |
| Budget Split | 8/10 | 10/10 | Verified `line` timestamp and `package_over` usage. Correctly separates search vs. package budget. |
| Swap Logic | 7/10 | 10/10 | Verified `SWAP_TOP` interaction with place rules. Correctly filters before capping. |
| Hook Handling | 8/10 | 10/10 | Verified hook is now in `weak` set and swapped by `hook_first_2s`. |
| Observability | 7/10 | 9/10 | `out["search"]` and `rec["why"]` for failed writes are good additions. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/package.py:176`**: `supply_exception` is called for swapped line-ups. Ensure that if the swap *resolves* a previous supply exception (by making channels unique), the `exception` variable is correctly set to `None`. The code does this (line 176 assigns the result of `supply_exception`, which returns `None` if no duplicates). This is correct, but worth noting that the `exception` variable is reused.
2.  **`pipeline/package.py:233-236`**: The new `rec["why"]` for failed writes uses `last.get("violations")`. Ensure that `violations` is always a list of dicts with a `"rule"` key. If `violations` is empty or malformed, `rules` will be empty, and the message will be generic. This is acceptable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The separation of the **search budget** (`over_budget`, $3.00/40min) from the **package budget** (`package_over`, $1.50/15min) is the highest-leverage change. It allows the build to explore up to 8 line-ups without being constrained by the tight per-package budget, while still ensuring that any *delivered* package adheres to the strict ruling 5 limits. This directly implements Ruling 41's intent to "search" more effectively.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements Ruling 41:
1.  **Line-up Search:** Up to 8 line-ups per build (`LINEUPS_PER_BUILD = 8`).
2.  **Swap Logic:** Weak segments (including the hook) are swapped at their place for the next best candidate from the whole pool, respecting place rules and `SWAP_TOP`.
3.  **Budget Split:** Search budget ($3.00) vs. Package budget ($1.50) are correctly separated and enforced.
4.  **Loop Safety:** The `dropped` set ensures no re-judging of failed moments, and the loop is bounded by `total < 8`.
5.  **Observability:** `out["search"]` and detailed `rec["why"]` messages provide good visibility into the search process.

All tests pass, and the logic is sound.