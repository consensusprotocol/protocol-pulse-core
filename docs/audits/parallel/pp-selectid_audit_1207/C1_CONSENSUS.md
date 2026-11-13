# pp-selectid audit 1207 (RULINGS 61-64 and the budget): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes with conditions": one "P0" and two P1.
  - qwen: "SHIP: No", on a "P0" and a P1.
  - glm: no P0; 13 numbered "P1" items, most of which close themselves.
- **Every P0 is refuted below.** The one consensus item (grok P1 = glm P1-1, other callers of coherence) is answered by
  the grep both asked for.
- Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | grok P0: reorder() calls itertools.permutations but the diff adds no import | package.py:50, unchanged and outside the diff, reads `import itertools`. The same module already used itertools.combinations in lineup_for and itertools.product in swap_lineup. The new reorder tests run the function (test_reorder_avoids_the_known_unfollowable_pairs_and_moves_least and test_ruling_63_two_flagged_joins_reorder_the_same_clips_first). |
| R2 | qwen P0 (its items 1, 2, 17, 19, 20): can_open() is True for a moment without "hook_rating", so such a moment can enter `passing` and crash hrank / hooks_txt (hook_own(m) is None) | build() sets "hook_rating" on EVERY cleared moment (ruling 59's block, right after the hook ratings): `for mid, m in cleared.items(): m["hook_rating"] = rated.get(mid) or {"rating": None, ...}`. That runs before `passing` is first computed and before the second screen. The second screen only narrows the same dicts (`cleared = {mid: m ... if mid in a_two}`). So every moment in `passing` carries the key, and can_open is True only when hook_own(m) is not None with a rating >= 4: hrank and hooks_txt never meet None. The "not rated yet" branch serves callers outside build() (unit tests, reading K5). |
| R3 | qwen P1 / glm P1-2 (2): ruling 62's `len(segs) - 1 > LY_CLIPS[0]` blocks a valid drop to the minimum clip count | segs is the hook PLUS its clips, so len(segs) - 1 is the number of CLIPS. Dropping the last leaves len(segs) - 2. The condition holds exactly when that is >= LY_CLIPS[0] (2): a line-up of hook + 3 clips may drop to hook + 2. A hook + 2 clips line-up (len(segs) = 3) would drop to 1 clip, under the medley's minimum. The tests show it: the floor-met case judges ["h","x","y","z"] then ["h","x","y"]. lineup_ok enforces the same minimum (`LY_CLIPS[0] <= len(clips)`). |
| R4 | glm P1-2 (1): lineup_ok's repeat_ok might relax the seconds floor | It does not. lineup_ok checks `lo <= dur <= hi` for every call (package.py, lineup_ok). repeat_ok only admits L-y 4's one repeated channel from two videos. |
| R5 | grok P1: the follow-up angle_write call has no avoid_vendor / avoid_family | angle_write is a WRITER role, not a verdict. The first angle call (unchanged) never passed them: the writer chain is Heimdall first, Grok on its failure. No verdict sees an angle sentence. CI.package_view shows the title, caption, clips and VO, and those come from the write call, whose vendor every verdict avoids (writers_v / writers_f). |
| R6 | glm P1-3: reorder's "fewest moved" compares against the original order | It compares against `clips = list(segs[1:])`, the order of the line-up just judged, which is the current order. Identity comparison is correct because the permutations reuse the same moment dicts. |

## Answered (the consensus item)

| # | finding | the answer |
|---|---|---|
| A1 | grok P1 / glm P1-1: coherence(..., hook=None) now fails closed for a caller that does not pass the hook; grep for other callers | Grepped pipeline/, tests/ and utils/. The build (package.py, one call, passes hook=segs[0]) and ONE other caller: tests/package/run_given_package.py:323, the one-off tool of the orchestrator's 05:35 order (last changed at 0e777c34). No build runs it. Re-run now, its coherence verdict fails closed with the stated reason ("the hook carries no cached own-job rating (ruling 61): fail closed"). That is ruling 61 as written: the hook's rating is the cached own-job one, and a package without one is not measured (law L-m). No code change. |

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-5: the follow-up asks for at most k2 angles in all, so when fewer slots remain than hooks left out, some stay without one | The angle budget (3) is ruling 41's. The hooks are offered best first, so the best ones are asked for first. |
| G2 | glm P1-7: the cached-record recompute's isinstance(int) admits a bool | A cached rating is written only from a reply that passed `type(x) is int` (hook_ratings' contract), and hook_own() itself refuses bools. |
| G3 | glm P1-11: the memo reuses a verdict judged with another seed | Intended: "cached verdicts for an identical line-up are free" (12:00). Re-asking the same line-up is the noise ruling 61 removes. |
| G4 | glm P1-13: angle_allotment's "dropped" list compares by dict equality, so identical repeated angles are not listed | Recording only. The count kept is correct (allot); the record is a P2 nit. |
| G5 | glm P1-4 / P1-6 / P1-8 / P1-9 / P1-10 / P1-12 | They close themselves in glm's own text: the joins key format is joins(labs), "<a> -> <b>"; `lineups` is ruling 41's budget parameter; the no-key branch is reading K5; the own-None paths fail closed; last_clip_only's discount is the join INTO the last clip. |

## Verification

- test_medley 119 OK; all 11 suites OK on the scratch copy (dev20, base 2e33ee4f).
