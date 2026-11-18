# r125: a stream last seen live takes the pipeline's record within the sweep, cycle 2: consensus

Reviewers (Heimdall, cross-validating cycle 1 and its consensus): qwen3.8-27b (135 s, $0.001 reported): "P0 CRITICAL:
None ... PRODUCTION READY? Yes", its conditions met (the observability fix merged and tested, M69-M74 killed, 449
passed); muse-spark-open (162 s, $0.003 reported): "No P0. One P1 fixed ... PRODUCTION READY? YES, with no
conditions". Cycle 2: $0.0043; the audit $0.0103 of its $1.00 cap (COST.json).

## Agreed by both (verified)
- Cycle 1's refutations stand (the per-file catch at fetch.py:184, one machine's clock, claim()'s atomic UPDATE, no
  record for a stream still live); the P1 (the event carries live_status, acquired_at and probed_at) is fixed and
  killed by M74.

## Recorded (comments and observability, for a later audited change; no edit after cycle 2)
- muse P2: comments at `got <= probed` (an equal time does not make it due) and at the sweep's `next_at > now_ts`
  (the filter and the UPDATE's own guard). qwen P2: a log line for rows the rule skips; batched store reads (a few
  dozen rows). qwen P3: a comment on claim()'s atomicity.
- muse P3 "explain test_r120's tamper": it has its comment ("r125: a still-live row's record older than its probe:
  never due").

Suite: tests/ingest 449 passed. Mutations M69-M74: 6 of 6 killed. No P0, P1 or P2 open that changes the code.
