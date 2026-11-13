# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 14792 / out 1355 usd~0.108 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0510 (Ruling 41 line-up search)**

1. WHAT DID THEY CATCH THAT YOU MISSED?  
GLM caught the exact placement of `package_over(line)` (now at 222) relative to the first write and the docstring vs. code timing of the per-package clock (line 193 vs. docstring). Qwen initially surfaced the “swap fails then continue without immediate total+=1” path and the hook-in-weak change. Grok correctly noted that `lineup_ok` exactly extracts the rules from `lineup_for`’s docstring and that tests exercise the new constants. I had not explicitly verified the `SWAP_TOP` candidate cap coming *after* the place’s own rule (`duration_s >= SHORT_CLIP_S` test at 73) nor the factored `supply_exception` now being used for swapped line-ups.

2. WHERE DO YOU AGREE OR DISAGREE?  
- K1 (loop / re-judge): fully agree — `dropped |= weak` before the swap call, `lineup_for(..., frozenset(dropped | doomed))`, and the explicit `ms = [by_id[m] for m in angle["moments"] if m not in dropped]` (visible in diff) make re-selection of a dropped moment impossible; `total` is incremented on every successful `lineup_for` so the 8-line-up bound holds.  
- K2 (hook rating/label map): agree — `weak` now includes the hook (line 202), `by_lab = dict(zip(labs, segs))` matches the labels `medley` returns, tests swap a hook rated 3.  
- K3 (SWAP_TOP ordering): agree — candidate list now filters the place’s own rule *before* slicing to `SWAP_TOP` (lines 72-74); test at 334-335 confirms a full clip can be chosen over 12 higher-ranked short clips in a non-last slot.  
- K4 (budget docstring): agree the code is stricter than the ruling (clock starts before `medley`) but still compliant; the new `package_over` docstring at 137 now accurately reflects “counted from the moment its own line-up’s clips-alone verdict is asked”.  
- GLM P1-1 / P1-3 and Qwen “P0”: agree they are resolved by the added helper functions and tests. Grok’s “SHIP: yes” after verifying test coverage is correct.

3. NEW FINDINGS FROM THIS REVIEW  
None that rise above P2. The combined Cycle-1 analysis plus the final diff shows `swap_lineup` never returns a line-up that would fail `lineup_ok` (it calls it directly at 84). The search budget (`over_budget`) is checked before every `lineup_for` and every write; the per-package budget is checked before every write (line 222) and cannot be dodged once a package has started writing. `total` counts every judged line-up across angles (lines 160, 192). No path re-judges a dropped moment. The only residual observation is that `swap_lineup(..., crange=None)` relies on `medley_content_range()` inside `lineup_ok`; this matches the `lineup_for` calls that also omit an explicit crange in the diff, but the contract is not visible.

4. REVISED SCORES  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| Line-up search & swap | P1     | P2     | Consensus + explicit `lineup_ok` + tests eliminate loop/re-judge risk; hook now correctly swapped. |
| Budget enforcement | P1     | P2     | `package_over` now sits at every write boundary; docstring aligned; search vs. package distinction verified in rewritten test. |
| Rule fidelity      | P2     | P2     | `lineup_ok` exactly mirrors `lineup_for` rules; unchanged bar and gates confirmed. |
| Test coverage      | P2     | P1     | New `TestRuling41Search` exercises every stated behavior of Ruling 41 (including 8-line-up limit across angles). |

5. FINAL PRIORITY LIST  
**P0 CRITICAL** — none verifiable from diff.  
**P1 HIGH** — none.  
**P2 MEDIUM** —  
- pipeline/package.py:193 (`line = (time.time(), _spent(spend))` before `medley`): includes the verdict call itself in the package budget; matches the stricter reading of Ruling 5 but creates a tiny docstring/code mismatch with the phrase “from the moment its own line-up’s clips-alone verdict is asked”.  
- pipeline/package.py:210 (`swap_lineup(..., frozenset(dropped | doomed))`): `dropped` already contains `weak`; the avoid set is therefore correct but the call site duplicates the union already performed at 208 — minor readability issue.  
- tests/package/test_medley.py:283-289: the package-budget test correctly shows search continuing after one line-up’s package budget is exceeded, but does not exercise a write that itself crosses the $1.50 line after partial writes have already succeeded.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE  
The paired `lineup_ok` + `swap_lineup` (lines 25-86) plus the cross-angle `total` counter (lines 154, 160, 192) turns an ad-hoc 2-line-up-per-angle retry into a bounded, rule-preserving search that actually swaps weak hooks and clips from the whole pool while still obeying every standing law.

7. PRODUCTION READY?  
Yes with conditions: (a) the minor docstring timing phrase at line 137 must be tightened to “counted from the moment the clips-alone verdict for that line-up is requested (including that call)” or the clock must move immediately after the `medley` call; (b) confirm in a follow-up that `medley_content_range()` is identical for `lineup_for` and `swap_lineup` paths (not visible in diff). With those two wording/test tweaks the feature matches Ruling 41, preserves all prior gates, and cannot loop or dodge budgets.

**P0** none  
**P1** none  
**P2** only the two docstring/readability items above (package.py:193, :210)  

SHIP: yes with conditions