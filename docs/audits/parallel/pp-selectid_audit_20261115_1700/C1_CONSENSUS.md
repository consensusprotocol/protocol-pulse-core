# C1 CONSENSUS — pp-selectid audit 20261115_1700 (RULING 117 (2)'s set: join_moments)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens (finish=length, no answer), so Grok
was asked (P1_OR_WORSE: 0). glm's breaker is open. Cycle 1: $0.0272 vendor-reported. No P1.

P2s, each checked against the code, NOT changed:
- qwen "join_moments relies on its caller's `cleared` holding only the order's pool (step A from both vendors, the
  second pass, CUTTABLE)": it is build()'s own `cleared`, unchanged, the same dict the landed inline fill read and the
  search reads (build() passes it to search_lineups as by_id, pipeline/package.py:3319 and 3403); the docstring names
  the contract. Not a regression.
- Grok "can() repeats lineup_ok's clip-eligibility and video checks; the two could drift": every line-up still goes
  through lineup_ok in the search (pipeline/package.py:2057), so a drift never loosens a line-up in either direction:
  were lineup_ok ever looser, the table would hold fewer moments than it could (a candidate missed, never a looser
  line-up); were it stricter, the table would hold moments the search cannot use (the cost this fix removes, never a
  pass). A shared helper would move code inside lineup_ok, an unchanged guard used at three sites (lineup_for,
  swap_lineup, search_lineups); the smallest diff (M1) keeps it where it is.

P3s noted: the docstring's length; the nested eligibility expression (lineup_ok's own truthy test, None-safe); the long
test names; an empty `own` (covered: join_moments with doomed={"x"} leaves the writer no other moment -> ["h", "q"]).

CHANGED AFTER CYCLE 1 (in cycle 2's diff): ONE TEST, no code. The full mutation run, finished after cycle 1's diff was
taken, showed K9 ("build() calls join_moments without doomed") SURVIVED: no test put a moment doomed in an earlier
angle before a later angle's table. New: test_a_moment_doomed_in_an_earlier_angle_never_joins_a_later_angles_table
(angle 1 dooms x through the exclusion gate; angle 1's table is h, x, y, w, z; angle 2's is h, z, w, y, never x).
16 tests in TestRuling117JoinSearch. Mutations after a control run: 23 of 23 killed (J1-J14 and K1-K9: the hook's own
video allowed, a clip-ineligible moment allowed, rank only, a new channel's second moment counted as new, a doomed
moment allowed, the writer's picks unfiltered, no cap, the build's old fill, the build passing no doomed).
