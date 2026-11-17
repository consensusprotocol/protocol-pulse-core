# r122: a stub can be a moment's answer for a real video (Nov 17), cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse): qwen3.8-27b: "The code is ready for production, provided that the
pipeline_sweep function correctly checks the pipeline's store for a record before marking a 'no metadata' video as
due"; muse-spark-open: "P0 CRITICAL: None ... This code is ready for production. It correctly fixes the premature
give-up of real streams that transiently return stubs, and the pipeline_sweep promotion is narrowly scoped to 'no
metadata' rows with pipeline records inside 12h. Ship it". Cycle 1: $0.0069 of the $1.00 cap (COST.json).

## Refuted (with the evidence)
- qwen P1 "verify the sweep checks the pipeline's store for a record before making a 'no metadata' video due": it does,
  in code this diff does not change: pipeline/ingest/fetch.py:246, `if pipeline_transcript(r["video_id"], r["channel_id"])
  is not None: due.append(...)`, for every row the SELECT returns, the new "no metadata" clause's rows included; the
  test test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record has a stub without a record (stub0000002) that
  is NOT made due (M49 / M50 killed).
- muse P1 "add a LIMIT to the sweep's SELECT (10k rows)" and "wrap the loop body in a broad except": refuted with their
  evidence in r119's C1_CONSENSUS.md (the same code): the rows are the transcript waits inside 12 h (a few dozen at
  most); pipeline_transcript catches OSError, ValueError, KeyError, TypeError and AttributeError per record file
  (fetch.py:184) and the sweep's own except is for transcript_store's id check.

Nothing to fix. Suite: tests/ingest 437 passed; mutations M44-M50 7 of 7 killed.
