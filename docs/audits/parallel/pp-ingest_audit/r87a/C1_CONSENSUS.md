# RULING 87 AMENDED, THE WATCHER'S SIDE (orchestrator 10:05 ET Nov 14), cycle 1: consensus

Reviewers (Heimdall): glm-5.3-flash (651 s, $0.007): "No production-breaking defect" (P0 none); muse-spark-open (507 s,
$0.032): "ready for production" (P0 none; two P1s); qwen3.8-27b (400 s, $0.011): "production-ready ... once [the
probe join] is addressed" (one P0, one P1). minimax-m3.1-flash: no review (an empty reply at its output limit; not
re-run). Cycle 1: $0.050. Diff reviewed: a6921162 against 2ec81efc.

## Agreed (verified)
- Each family once, at its first failure after the latest answer, in time order; an answer clears the pending
  families (a failure before it is answered for); with an older module the calls are exactly as before.
- The latest-answer time: never later than a real answer; the amended module's time check then decides.

## Fixed (each with a test that fails without it: mutation-checked)
- C1-1 (qwen P0, in substance): the probe joined its family threads without a bound, so one hung family (glm's runaway
  replies of today: 391 s for one word at the builder's probe) held back the answer that resets the clock. The probe
  now reports by its longest back-end deadline + PROBE_WAIT_MARGIN_S (15 s) at the latest, with what answered by then;
  a family still asking counts as not answered. Test: a family that hangs; the probe reports with the other's answer
  in well under a second (the unbounded join stalls it 30 s and fails).
- C1-2 (qwen P1): a family thread that ended without an outcome (an exception its handler does not catch) made
  run() raise KeyError, losing the probe; it is now not counted, and the others' answers are reported. Test: a
  SystemExit in one family's call.
- C1-3 (muse P1, its useful half): the family path is now tested against the builder's REAL amended module and its
  file lock (the other signal tests already ran on it): a failure of a family this watcher's probe cannot ask is in
  failing_families and the watcher leaves the slot; once a family it can ask fails too, it claims, asks, and the
  answer clears the clock and the families. (Skipped only if the module at the builder's path predates the amendment.)

## Refuted or recorded
- muse P1 "the two false outages were module/watcher interaction bugs fake-based tests missed": refuted; they were the
  ruling as then written (a probe answer did not stop the clock), on the real module, and the amendment changed it.
- muse P1 "the staging base URL in providers.json": pre-existing, the gateway's own address; each back-end has
  base_url_env (PP_INGEST_HEIMDALL_BASE) to move it. Recorded.
- glm F31: a family that fails inside a probe another family answered is not a failed CALL (the amended rule counts
  answers; a failed probe never starts the clock): by design. glm F22: muse's probe at 512 tokens may end on its
  reasoning (then its leg fails; the others answer). glm #4: passing the answering families to probe_result needs the
  builder's API (its module clears every failed family on any answer). Recorded.
- glm: check_next grows with every moment ever checked; loop-thread liveness: outside this change, recorded.

Suite: tests/ingest 342 passed (the builder's amended module 3cf4c42f at its path).
