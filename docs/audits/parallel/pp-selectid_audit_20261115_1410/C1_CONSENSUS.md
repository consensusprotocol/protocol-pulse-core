# C1 CONSENSUS — pp-selectid audit 20261115_1410 (ruling 115 (1)+(2), the calibrated hook bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1); glm-5.3-flash ran out of its 24,000 output tokens before its last line
(finish=length: no P1 count), so the driver asked Grok (P1_OR_WORSE: 1). Cycle 1: $0.0757 vendor-reported.

THE P1s:
1. qwen [P1] "a calibration whose measured_at lies in the future stays valid past its 24 h (now - at is negative)".
   FIXED: bar() refuses a measured_at more than SKEW_MIN (5) minutes ahead of now ("is in the future: refused").
   AND, found while fixing it (glm raised it too, as a P2): a measured_at with NO timezone made `now - at` raise
   TypeError outside the parse's try, so bar() would have crashed a build instead of failing closed. FIXED: refused
   with a reason ("has no timezone"). One new test covers both (a 4-minute skew still passes; 6 minutes does not; a
   naive time is refused and never raises). Mutations B10 / B11 killed.
2. Grok [P1] "the order says nothing else about the hook path changes; the hook's slot in the two verdicts and in
   ruling 62 changed". This is the reading the QUESTION named for the reviewers. It is kept and goes to the
   orchestrator on STATE line 1 as the reading taken: with a scroll floor of 3, a hook that PASSES the calibrated bar
   would fail every line-up if its own rating (3) still sat inside the min >= COHERENCE_MIN (4); the bar would then
   pass hooks that can never open a medley. The clips AFTER the hook and the VO point keep COHERENCE_MIN; the
   may-open rules, G17a, step A and CUTTABLE are untouched. Not a code defect.

glm's findings (from the part of its review that came back), the ones acted on:
3. glm "a rating cached by one model answers for the moment whatever the hook list says: after a calibration onto a
   new rater with the same question, every cached rating fails the rater check and is never asked again (no hook
   could ever pass)". FIXED: hook_ratings serves a cached rating ONLY from a back-end on today's hook list
   (router.chain("coherence_verdict", "hook")); a rating by any other model is asked again by today's rater. A
   stand-in router without chain() keeps the old behaviour. New test (on the list: served; off it: asked again);
   mutation P13 killed.
4. glm "the seed is not in the cache key". FIXED: HOOK_VERSION now hashes the question, the asking AND the seed
   (HOOKS_PROMPT + HOOK_ASKING + "seed 7"), and hook_ratings uses the cache only at production's seed (another seed
   neither reads nor writes it). The calibration's question_version is relabelled to the new value (e3cba8d92551,
   with a note; re-sealed, sha fb964eb15a24...): the measured asking is the same bytes (HOOKS_PROMPT, one candidate,
   seed 7). New test; mutations P10b / P14 killed.
5. glm "the spotlight's pin path: does it carry the mark?". It does: proof_ledger writes SPOTLIGHT_PIN.json through
   package_pin.write_pin -> to_pin (package_pin.py:511), the same to_pin, whose `spot` branch is the spotlight's.
   NEW TEST: a spotlight package's pin carries moments_package["hook_bar"], and its seal is unchanged.
6. glm "the spotlight's moment record keeps the rating, not the pass". FIXED: rec["hook_passes"] beside it (tested).
7. glm "the bar is cached on the file's mtime only". FIXED (ours, while reading it again): the cache key is the
   file's mtime AND the minute, so a calibration that ages past its 24 h mid-build stops passing hooks within the
   minute. hook_live_bar passes HB.PATH explicitly (bar()'s default path is bound at definition time). New test;
   mutation P15 killed.

NOT CHANGED, with the reason:
8. glm "hook_pool['min'] removed": no consumer reads it (grep over pipeline/, tests/ and the main tree's .py: none).
9. glm "replay85 still reads HOOK_MIN": replay85 measures model AGREEMENT at a fixed threshold (ruling 85); it is not
   the production bar, and its tables stay comparable with their history. Its comment says so.
10. glm "every unrated candidate's why names the first error": as ordered (the first error is returned); each
    candidate's own failure is in the build log line.
11. Grok [P2] "rater=None in bar() is asymmetric with passes()": bar() checks a NAMED rater; production names none
    and passes() checks each rating's own back-end against the file's rater, so a rating by any other model fails.
12. Grok [P2] "a cached Grok decision suppresses the qwen shadow": a rating served from HOOK_CACHE.json makes no call,
    so there is nothing to shadow; every FRESH hook rating is shadowed (Router.call, both the live and the recorded
    branch).
13. qwen's and glm's other self-resolved items: no change.

TESTS: tests/package + tests/providers pass (cycle 2's run is in its consensus). 38 of 38 mutations killed after a
control run (the 31 of the QUESTION, P10 re-aimed at the new version line, + B10 / B11 / P10b / P13 / P14 / P15 / S4).
