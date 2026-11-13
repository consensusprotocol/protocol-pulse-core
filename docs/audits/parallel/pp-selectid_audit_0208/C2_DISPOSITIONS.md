# pp-selectid audit of one window per moment: cycle 2 dispositions (synthesis by the pp-selectid session, 02:20 ET Nov 13)

**Run.** Cycle 2 cross-reviews the fixed diff (C2_STEP.diff, 26,392 bytes). No P0, no P1 from any reviewer; every
reviewer says SHIP yes with conditions, and every condition is P2.

## Implemented (each verified)

- **glm N4** (row accounting): a row whose own window record fails, in a video that still gave window moments, was in
  no counted bucket. It is now counted in report.window_failed, with its why in window_passed_over.
- **glm N2 / qwen** (report semantics): "videos" counts the videos that gave moments, "sources" their records (one
  per window moment), and window_records is {video: [records]}. The build_inputs docstring states this. The report
  is read only by the driver's log line and saved as proof.
- **glm / grok** (source_key collision): two moments with the same key share one Source, which is the same record.
  The worker writes one file per video and 3-decimal window bounds (record_path), write-once. Documented.
- **grok** (an import inside a function in speakers.py): context_integrity is now imported at module level. There is
  no cycle; context_integrity imports eligibility only. Checked.

## Answered

- **glm N1** (speakers with src=None): speakers.attribute returns "no word record for the clip's context", measured
  false, BEFORE any call when src is None ("if src is None or 'k0' not in seg"). So the missing-key path cannot claim
  a name, and cannot dereference None.
- **qwen** (circular imports): none. context_integrity imports eligibility only; package and speakers import it.

## Verification

- 11 offline suites, 234 tests OK; regression_test.sh 26 PASS | 0 FAIL | 5 WARN.
- The FRESH builds on this code:
  - 02:08: 74 rows gave 32 moments (41 windows);
  - 02:18, after the worker's third cycle: 74 rows gave 47 moments on 6 videos (69 windows, every caption record
    found). Then 15 usable, 7 cleared step A, 4 passed L-v 2 + CUTTABLE, 3 can open: no line-up (too few seconds
    from too few channels). Supply, not the code.
