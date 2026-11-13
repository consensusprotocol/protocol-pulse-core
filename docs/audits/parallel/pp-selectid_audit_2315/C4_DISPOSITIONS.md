# pp-selectid audit of the ledger build path, ROUND 2: cycle 4 dispositions (synthesis by the pp-selectid session, 23:53 ET Nov 12)

**Run.** Cycle 4 cross-reviews the fixed diff (C4_STEP.diff, 50,335 bytes; prompt 77,094 bytes) with the cycle-3
reviews and C3_CONSENSUS.md. Every reviewer: SHIP yes with conditions. No P0, and the only P1s are qwen's.
- grok-4.20-0309-reasoning (xAI), 26 s: two P2s. Conditions: the integrator confirms that empty delivered_ids stay
  right; a future window-record path keeps the counting.
- qwen/qwen3.8-27b (Heimdall, effort none), 131 s: P1s. A record that is not an object, a segment that is not an
  object, or scores that are not an object crash the build. P2s: the 1 ms tolerance; the since documentation.
- z-ai/glm-5.3-flash (Heimdall, effort none), 117 s: "P1 HIGH: none". P2s: duplicates are not named; the Source's
  channel is never cross-checked against the store; offset_s is silently absent; the env var's use is unverifiable.
  Its conditions are the first two of these.

**Spend:** about $0.39 at the config's upper-bound prices. All four cycles together: about $1.4 (an upper bound).

## Consensus

Cycle 4 agrees on no new defect. Its two shared points are already answered:
- **K7 (grok, glm):** delivered_ids. The evidence is in C3_CONSENSUS (package.usable's any-overlap check, tested with
  an Oct 1 pin). grok's condition, that the integrator confirm empty delivered_ids stay right long-term, goes to the
  integrator with this commit.
- **since (qwen P2, glm agrees it is documented):** proof_ledger.py's docstring states the choice, and the run log
  prints which since was used. Nothing to change.

## Unique findings, implemented (each verified first; each has a test that fails on the cycle-4 code)

| finding | verification | fix and test |
|---|---|---|
| qwen P1: a record that is not an object, or a segment that is not an object, crashes word_source / words_off_segments | `rec.get` on a JSON list raises AttributeError; a string under segments raises inside segments_sha256 | Each is now a named why in passed_over: not a record; segments cannot be hashed; words or segments not a list of objects. Test: test_a_corrupt_record_is_passed_over_never_a_crash (ERROR on the cycle-4 code, the crash itself) |
| glm P2-1 / condition 2: the Source's channel is never cross-checked against the store record's own channel_id | On the ledger's videos: 20 records name the row's channel, 0 contradict it, 3 name none (older records). word_source on the ledger's 14 videos with a record: 12 read, 2 not sentence-ready, 0 contradictions | A record that names a channel other than the row's is passed over: a measured contradiction. A record that names none keeps the row's channel, which the adapter checks against the registry; the docstring says so. Test: test_a_record_that_names_another_channel_is_passed_over |
| glm P2-5 / condition 1: a duplicate-span drop is counted, not named | `seen` was a set | report.duplicates_of names the moment that lost to the one that kept the span. Test: rows L1/L2 give {"L2": "L1"} |
| glm P2-8: offset_s is silently absent when it cannot be measured | it was set only when all four times were readable | offset_s is always set: [start, end] offsets, or "unmeasured: <why>" (L-m: say so, never leave it out). Test updated |

## Refuted or kept, with the reason

- **qwen P1** (non-object scores crash build_inputs): REFUTED. `dict([1, 2, 3])` raises TypeError inside the try at
  build_inputs, so the row is counted in report.malformed. A missing scores is already tested the same way.
- **qwen P2** (tol = 1 ms is too tight for mixed precision): KEPT.
  - Over 35,697 segments the store's segment edges equal their words' times exactly (max deviation 0.000 s). The
    store rounds segments to ms, which is at most 0.5 ms from the word.
  - A store change that broke this would refuse records loudly (named in passed_over), never silently: fail closed.
- **glm P2-4** (PP_SELECTID_PIPELINE may be unread): REFUTED. pp-ingest pipeline/ingest/contract.py:60 reads it to
  locate the selector's definitions for its contract fingerprint.
- **grok P2** (the WORD_RECORDS test does not hold a _v2 and a canonical file together): KEPT. The slots are read by
  name, so a _v2 file is never read. The test proves that by renaming the punctuated record.
- **glm P2-2** (word_records lists records read): KEPT, as commented in cycle 3.
- **glm residual** (SNAP_GUARD misses "infrequently", "un-", "non-"): KEPT.
  - A snap adds at most 3 words of the record's own edge sentence, and every gate judges the snapped text.
  - A prefix is part of a word, not an added negation.

## Verification

- tests/package/test_ledger_build.py has 20 tests. The 4 that cover this cycle's items fail on the cycle-4 code (1
  FAIL, 3 ERROR), which was rebuilt from C4_STEP.diff.
- All 9 offline suites pass: 201 tests OK.
- regression_test.sh in the worktree: 26 PASS | 0 FAIL | 5 WARN.
- word_source on every ledger video with a store word record: the new checks refuse none of today's records.
