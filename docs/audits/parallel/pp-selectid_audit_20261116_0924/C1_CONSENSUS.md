# C1 CONSENSUS — pp-selectid audit 20261116_0924 (RULING 118 (4): story-first line-ups)

FIRST ATTEMPT (kept as C1first_*): SEATS ANSWERED 1 of 3: qwen at effort none looped to its 16,000-token cap; mimo was cut
off at 32,000. gemma's one P1 ("check_angles(..., cleared, 1, ...): the third argument is min_moments; 1 lets a 1-2 moment
angle through") MISREADS the unchanged guard: its signature is check_angles(obj, by_id, k=MAX_ANGLES, hooks=None)
(package.py:1058), k being how many angles the object may hold ("exactly {'angles': [1-k items]}"); the 3-8 moments rule
is inside it, unconditionally (package.py:1073: "if not 3 <= len(ms) <= 8"). Not a defect. A test now pins it: a story with
two cleared moments gives no angle, "not an angle: angle 1: 3-8 distinct offered ids" (in cycle 2's diff).

CYCLE 1 RE-ASKED on the same diff plus that test, with qwen at effort medium and gpt-oss-20b at medium in mimo's seat (as
the integrator's audits answer): SEATS ANSWERED 2 of 3 (gpt-oss cut off at 24,000 with no answer). P1_OR_WORSE: qwen 0,
gemma 0. Cycle 1, both attempts: $0.0325 of Heimdall, not capped.

P3 noted, not changed (qwen): an empty-string moment_id is read (it can never be in the cleared pool, so it can never
enter a line-up); out["stories"]["angles"] holds one row a story, with the angle it gave or why not (a record name);
load_candidate's story lambda re-reads the record's angles list (a few items, once a record).

Suites: 40 files, 828 tests. Mutations S1-S18 after a control run: 18 of 18 killed.
