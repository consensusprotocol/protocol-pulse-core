# C2 CONSENSUS — pp-selectid audit 20261115_1632 (RULING 117 (2)+(3): the join table and the search)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens again (no answer), so Grok was asked
(0: it accepts cycle 1's answers on M1, the import and the call count). Cycle 2: $0.0391; the audit $0.0881
vendor-reported. No third cycle: cycle 2 found no real defect.

P2s noted, not changed:
- qwen "ext may hold moments not in by_id": ext's moments are drawn from `cleared` itself (jids), and the search is
  given `cleared` as by_id; a moment outside it cannot enter.
- qwen "the ratings update and odd verdict shapes": a rating is kept only when it is an int; the hook's slot is not
  read; an unmeasured verdict skips the block (med["measured"]).
- Grok "the search runs twice when the first finds nothing": by design (one segment per channel first, then L-y 4's
  supply exception, as lineup_for); CPU only, about a second for 8 moments.
- Grok "a moment without rank_score": it sorts as 0 with its id as the tie-break, so the order is deterministic.
- Grok P3 "others is capped at 7 after the hook": the same cap as the table's, so the search never meets a pair the
  table was not asked.

Mutations: 15 of 15 killed after a control run (J15, the table only the writer's picks, after the widening). Suites:
all 40 files, 810 tests. FINAL DIFF: FINAL.diff (written at landing).
