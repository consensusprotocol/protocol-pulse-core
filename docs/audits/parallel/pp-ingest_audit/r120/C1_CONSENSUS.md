# r120: a stream over (post_live) takes the pipeline's record (Nov 16), cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse): qwen3.8-27b: "This code is ready for production. It correctly implements
the logic to handle post_live videos", one P1 (performance). muse-spark-open: "P0 CRITICAL: (none) ... This code is
ready for production. It correctly fixes the 53-minute post_live mining delay with minimal, well-tested changes that
preserve all existing invariants (no caption download for post_live, is_live never taken, all probe checks still
run)", two P1s. Cycle 1: $0.0071 of the $1.00 cap (COST.json).

## Agreed by both (verified)
- is_live is never taken and its meta never written; post_live without a record waits as before (no caption download,
  no meta); post_live with a record runs every remaining probe check before the take; the sweep and the self-check
  never touch an is_live row.

## Fixed (with a test that fails without it)
- C1-1 (both P1): fetch.process read and hashed the pipeline's record up to three times for one probe of a stream over
  (the live check, the length, the take). It is read once (`found`) and handed to take_pipeline_transcript(found=),
  which still copies, re-reads and re-hashes the copy before os.link. Test:
  test_a_stream_over_reads_the_pipelines_record_once (one call); M43 killed; M36-M38 re-pointed at the new lines and
  killed again.

## Refuted
- muse P1 "q.x() could leave partial next_at updates with no rollback": the sweep's UPDATE is one statement (queue.py
  opens SQLite with isolation_level=None: each statement its own transaction, atomic), so it changes all its rows or
  none.

Suite: tests/ingest 431 passed. Mutations M36-M43: 8 of 8 killed.
