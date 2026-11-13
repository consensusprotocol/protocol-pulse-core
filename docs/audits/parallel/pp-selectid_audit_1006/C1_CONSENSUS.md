# pp-selectid audit 1006 (RULING 57: prefer line-ups with the newest clips): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- glm: "yes with conditions";
- qwen: "SHIP: NO", on one P1 that holds (glm found it too).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P1 / glm P1-2: "counts as the oldest" was max(known ages) + 1 h, so a line-up whose ages are ALL unknown read as 1 h old, the NEWEST | A fixed sentinel, UNKNOWN_AGE_H = 1e6 h: a clip with no readable time is the oldest there is, in every line-up. Tested: an all-unknown line-up ranks below one aged 50-70 h. |

## Answered (verified from the code)

| # | claim | the code |
|---|---|---|
| A1 | glm P1-1: first_fresh() calls lineup_for without dropped / doomed | It runs right after the angle call, before any line-up, so nothing is dropped or doomed yet (both start empty in the loop). The line-up it computes is the one the loop's first lineup_for returns. |
| A2 | glm P1-3: age_hours' semantics | eligibility.age_hours(published_at, now) = (now - the parsed time) in hours, or None when the time cannot be parsed (_parse_time). An unparseable time is therefore never fresh (F1). |
| A3 | qwen P2-2: the extra lineup_for call per angle | Recorded, no change: the cleared pool after both screens is 5-13 moments; one more call per angle (3 at most) is milliseconds. |
| A4 | qwen P2-5 / glm: no test of pool_fill with now | Recorded: pool_fill passes now straight to lineup_for, whose preference is tested. |

## Verification

- test_medley 92 OK; every other suite OK.
