# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 702 s finish=length usage in 19040 / out 32000 usd_reported=0.003604 usd~0.537 (upper-bound price)

# CODE AUDIT — pp-selectid (RULING 118 (4))

## Check (1): Can a story angle ever take a hook or clip from outside its story?

**No — verified across every pool-consuming path in the per-angle loop.**

- `sel = story_pool(angle, cleared, by_story)` is computed at the top of each loop iteration (C1_STEP.diff line 250). For a story angle it returns only `{x: cleared[x] for x in by_story[story] if x in cleared}`; for any other angle it returns `cleared` unchanged.
- `join_moments(angle, sel, doomed)` (line 256) — join table restricted to the story.
- `pool_fill(angle, sel, …)` (line 265) — fill restricted to the story.
- `swap_lineup(segs, weak, sel, …)` (line 274) and `swap_lineup(segs, set(bad), sel, …)` (line 283) — both swaps restricted to the story.
- `ext = dict(angle, moments=jids)` where `jids` comes from `join_moments(angle, sel, …)` — `search_lineups` and `lineup_for` therefore only see story moments (confirmed by the unchanged-guard note and the test at line 471–473).
- `angle["moments"]` itself is built in `story_angles` from `ids = [x for x in s["moment_ids"] if x in cleared]` — always a subset of the story.
- The hook membership check `angle["hook"] in cleared` (line 254) is a boolean test, not a pool read; the hook is guaranteed in `sel` because `story_angles` only picks hooks from `ids`.

**No path leaks outside the story. ✓**

## Check (2): Nothing changes when there is no file, no 3-channel story, or a candidate

| Scenario | `s_angles` | `by_story` | `sel` | `writers_v/f` | Result |
|---|---|---|---|---|---|
| No `stories_path` | `[]` | `{}` | `cleared` | unchanged | Identical to before ✓ |
| File missing / unreadable | `[]` (record says why) | `{}` | `cleared` | unchanged | Identical (extra `out["stories"]` record key only) ✓ |
| Story < 3 channels | `[]` (`check_angles` refuses) | `{}` (no angle created) | `cleared` | unchanged | Identical ✓ |
| Candidate | `[]` (block skipped: `candidate is None` guard) | `{}` | `cleared` (candidate angles have no `story` key) | unchanged | Identical ✓ |

Tests at lines 485–498 and 384–394 confirm all four. ✓

## Check (3): Every gate unchanged

No gate function, threshold, or acceptance criterion is touched in the diff. The only behavioural change to verdict inputs is the union of `s