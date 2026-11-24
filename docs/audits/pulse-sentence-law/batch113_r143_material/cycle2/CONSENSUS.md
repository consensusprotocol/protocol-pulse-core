# Batch 113 (ruling 143), cycle 2 consensus

Run 16:12 ET Nov 17 (qwen27b 27,452 chars of reasoning; gpt-oss-20b 3,731 chars). Both said FAIL:
- qwen F1 (critical): the same ticker-regex claim as cycle 1. DISPROVED as there.
- gpt-oss F1 (high), "as_spoken holds when a material word is present though the two audio readings agree":
  DISPROVED.
  - as_spoken compares the LOCK text (already settled by adjudicate_lock: where the run decode and the second
    recogniser agree on a material word, the lock takes their reading) with the second reading.
  - A material difference that survives that comparison is the second recogniser disagreeing with the settled
    reading, i.e. the two audio readings disagree. Ruling 143 (3) says HOLD.

Tests and mutations (the Nov 17 build, scratchpad b113/):
- the touched suites green;
- the new tests fail on the live code (MUST_FAIL_OLD_CODE.log);
- mutations 9 of 10 killed.
- T10 ("fillers stay in the second reading") SURVIVED. On Nov 18 a test was written for it (a filler that the
  transcript and the second recogniser both write never enters the sealed text). It passes with and without T10.
  Traced: canon.same_words drops filler-only pairs before the per-pair vote, and an insertion in the second reading
  changes neither the alignment of the other words nor audio_share (its extra words never lower it). So T10 is an
  equivalent mutant: removing fillers from the second reading changes no outcome. The line stays for clarity
  (ruling 135 (d)).

Nov 18: the branch was merged with the release branch (batch 114; RULES now "+ ruling 143 + ruling 146").
- Batch 113 + 114's suites pass on it: 257 passed.
- One suite not run on Nov 17, test_trimmed_leading, had a case written for ruling 84 (b) ('this' / 'these': the
  decode's word kept, alternatives recorded). Ruling 143 (2) supersedes it (two of three), and it was rewritten in
  batch 116's commit.

Decision: batch 113 lands with batch 116 (ruling 139, the render lock) in ONE decoder lockstep.
