# r119: within 10 minutes of its transcript, Bitcoin channels first (13:05 ET ruling, Nov 16), cycle 2: consensus

Reviewers (Heimdall, diff-scoped): qwen3.8-27b ($0.0016 reported): "P0 CRITICAL: None ... Production ready? Yes with
conditions" (the condition below, already met); muse-spark-open (118 s, $0.003 reported): "P0 CRITICAL: None ... P1
HIGH: None remaining ... All conditions satisfied on r119. Ship it." Cycle 2: $0.0046. The audit: $0.0139 of its
$1.00 cap (COST.json).

## Agreed by both (verified)
- C1-1 (the transcript-to-rows measure) is fixed and tested; both cycle-1 P1s left (the sweep's except, the LIMIT) are
  refuted with the evidence in C1_CONSENSUS.md; the queue's binding order is right (muse traced it: states, clock, the
  `first` ids, the limit).

## qwen's condition (met, with its evidence)
- "acquired_at may be NULL: a TypeError in transcript_lag_s": service.transcript_lag(acquired, now) parses
  str(acquired) inside a try; None, a missing key (rec.get), an unparsable text or a time without its zone all return
  None, and the row and the line then say nothing (test_transcript_lag_reads_only_a_time_with_its_zone asserts None
  for None, a naive time and "not a time"; M35 killed). `rec` is the record the miner just read (mining fails before
  this line without one).

## Recorded (P2, neither blocks)
- A lock around the Bitcoin-set cache (each loop runs in its own single thread; a race costs one registry read).
- `_last_sweep` set before the sweep: a sweep that raised waits a minute (intended: no busy loop); the LATE measure
  would show any delay. A strict tier-1-before-tier-2 order if the orchestrator wants it.

Suite: tests/ingest 422 passed; mutations M22-M35, 14 of 14 killed. Verdict: no P0 or P1 open; r119 goes live at the
next restart.
