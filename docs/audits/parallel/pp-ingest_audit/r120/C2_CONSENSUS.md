# r120: a stream over (post_live) takes the pipeline's record (Nov 16), cycle 2: consensus

Reviewers (Heimdall, diff-scoped): qwen3.8-27b: "P0 CRITICAL: None. P1 HIGH: None ... Production ready? Yes" (its
conditions: C1-1 applied and its test passing: both true); muse-spark-open: "Nothing new that is P0/P1 ... Production
ready? Yes, with no conditions". Cycle 2: $0.0046. The audit: $0.0117 of its $1.00 cap (COST.json).

## Agreed by both (verified)
- C1-1 (the record read once per probe of a stream over, handed to the take) is fixed and tested; muse's partial-update
  P1 is refuted (one statement, isolation_level=None: atomic).

## Recorded (P2, neither blocks)
- muse: the duration taken from the record is also written on the row when a refused copy sends the video back to
  LIVE ("correct: we want the row to have the duration"); the sweep still reads each candidate's record once a minute
  (bounded by the transcript waits inside 12 h).

Suite: tests/ingest 431 passed; mutations M36-M43, 8 of 8 killed. Verdict: no P0 or P1 open; r120 goes live at the
next restart.
