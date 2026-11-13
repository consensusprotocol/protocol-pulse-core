# pp-selectid audit 1207 (RULINGS 61-64 and the budget): final consensus after cycle 2

- **Cycle 2:**
  - grok: no P0, "SHIP: yes with conditions".
  - qwen: no P0.
  - glm: no P0 ("Every Cycle-1 P0 was refuted with evidence (R1, R2); I concur").
- No P0 or P1 holds in either cycle, and nothing changes in the code.
- The conditions all three repeat (grep for other callers of coherence) were met in cycle 1 (A1): one other caller, the
  05:35 one-off tool run_given_package.py, which now fails closed with ruling 61's stated reason.

## REFUTED (cycle 2, with evidence)

| # | claim | the code |
|---|---|---|
| R7 | grok P1: `repeat_ok=exception is not None` in ruling 62's branch reads an undefined `exception` | `exception` is set at the top of every pass of the line-up loop, before the verdict: from a swap (`exception = supply_exception(segs, ctx)`) or from lineup_for (`segs, exception = lineup_for(...), None`), and again for the repeat / pool-fill paths. It is the current line-up's L-y 4 supply exception, and repeat_ok follows it exactly as the existing swap path does. |
| R8 | qwen P1 / glm N5: `lineups` in the guard `spins > 4 * lineups` is undefined, or a shrinking remainder | It is build()'s parameter, `lineups=LINEUPS_PER_BUILD` (8), a constant for the build. The existing loop condition `while total < lineups` reads the same name. The guard is 32 iterations. |
| R9 | glm N1: ruling 62's and 63's `continue` paths set `swapped` directly and could skip bookkeeping the swap path performs | The swap path's own bookkeeping is `dropped |= weak`, `swapped, swaps = swap_lineup(...)`, `rec["why"] = ...`, `continue`. Ruling 62 does `dropped.add(last)`, `swapped = segs[:-1]`, `rec["why"]` and `continue`. Ruling 63 drops nothing, by the ruling ("before dropping anything"). n_lineup, total and the package budget are counted where a line-up is judged, at the top of the next pass, for every path alike. |
| R10 | grok: add avoid kwargs to the follow-up angle call | Cycle 1 R5: angle_write is a writer role; no verdict sees an angle sentence. |

## Recorded (P2, no change; with cycle 1's G1-G5)

- glm N3: the cache read admits a bool where hook_own refuses it. A cached record is only ever written from a reply
  that passed `type(x) is int`.
- glm N2: the allotment record's equality dedup. Cosmetic (cycle 1 G4).
- glm N4: the memo and reorder() key line-ups the same way, by the hook-first moment-id tuple. Consistent.

## Verification

- test_medley 119 OK; all 11 suites OK on the scratch copy (dev20, base 2e33ee4f).
- regression_test.sh is run on the worktree before the commit.
