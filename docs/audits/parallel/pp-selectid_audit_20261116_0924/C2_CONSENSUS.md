# C2 CONSENSUS — pp-selectid audit 20261116_0924 (RULING 118 (4): story-first line-ups)

Seats (Heimdall only): qwen3.8-27b (effort medium), gemma-4-31b-it, gpt-oss-20b (effort medium). SEATS ANSWERED: 2 of 3
(gpt-oss cut off at 24,000 tokens again, no answer). P1_OR_WORSE: qwen 0, gemma 0. The whole audit $0.0458 of Heimdall,
not capped. No P1 in either cycle (cycle 1's first attempt: gemma's one P1 was a misreading of check_angles' k, see C1).
CLEARED.

P3s agreed by both seats, not changed (the code stands as audited): an empty moment_id is read but can never be in the
cleared pool, so it never reaches a line-up; out["stories"]["angles"] is the record of each story's attempt (a name);
load_candidate's story lambda re-reads a short list. None changes a result.

LANDING: rebased on 77abe7c1 (ruling 120's floor, which also edits package.py and test_medley.py, in other places):
the rebased diff equals this audit's diff line for line, but for hunk line numbers (git apply, no conflict); suites and
mutations rerun on the rebased code before it lands.
