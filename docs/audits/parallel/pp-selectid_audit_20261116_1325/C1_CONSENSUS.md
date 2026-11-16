# C1 CONSENSUS — pp-selectid audit 20261116_1325 (the story-first id defect)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 1. Cycle 1 $0.0053 of Heimdall, not capped.

mimo's P1 ("a read stories file that translates to ZERO matches is silent again"): RIGHT ABOUT THE SILENCE, and taken in a
loud form, not a HOLD. A file-wide zero of CLEARED matches is normal (story moments held at step A, refused, not
cuttable: today's S-533ed7f7 has Fox not cuttable and What Bitcoin Did held), and story-first is an extra angle source
beside the writer's: a HOLD would stop builds the file has nothing to do with. What signals an id mismatch is a zero in
the WHOLE POOL. CHANGED (in cycle 2's diff): stories.matched gives each story's ids found in this build's pool at all
(in_pool, through mined.ledger_moment_id or the duplicates alias) beside those cleared; when a read file with stories has
in_pool 0 for every story, stories.warning says "NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL: an id
mismatch? story-first cannot fire" and the build log prints it (builds 41-57 would have said so at 09:59). Tests: a file
naming build ids: warning, in_pool 0; the file's ledger ids: in_pool 3, cleared 3, no warning. Mutation T4 (the warning
silent).
mimo's P2 (a parent and its trimmed variant share a ledger id; both indexed): both may be in a story's pool, never in one
line-up: every segment needs its own video (lineup_for, package.py:1764, unchanged: len of the video ids == clips + 1), and a
variant shares its parent's video. Not changed.
mimo's P2 (ledger_aliases omitted by a caller): proof_ledger is the only caller that passes stories_path; the record now
says stories.aliases = how many, or "not supplied" (tested). mimo's P3 (inputs None): build_inputs returns its report
dict always (ledger_build.py:598); not changed. qwen's P2 (order): file order, then the pool's insertion order:
deterministic; not changed.
