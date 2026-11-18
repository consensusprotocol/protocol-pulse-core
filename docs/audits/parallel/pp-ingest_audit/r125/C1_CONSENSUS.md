# r125: a stream last seen live takes the pipeline's record within the sweep, cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse). qwen3.8-27b (184 s, $0.002 reported): "Verdict: CORRECT ... ready for
production ... The only gap is observability", one P1, one P2, one P3. muse-spark-open (237 s, $0.004 reported): "P0
CRITICAL: None ... ready for production ... Required before ship: Nothing blocking", two P1s, three P2s, two P3s.
Cycle 1: $0.0060 of the $1.00 cap.

## Agreed by both (verified)
- A stream YouTube still calls live is never taken (fetch.process unchanged) and is probed at most once per new record
  (every probe rewrites state_at, queue.py:166); the other waits keep their rule; a missing or zoneless time fails
  closed.

## Fixed (with a test that fails without it)
- Both P1 "observability of the r125 path": the sweep's queue event for such a row (pipeline_transcript_due) now
  carries live_status is_live, acquired_at and probed_at (the two times it compared); the service already logs every
  made-due id (service.py:272-275). test_a_stream_last_seen_live_is_made_due_once_and_never_taken_while_still_live
  reads the event; M74 (the event without them) is killed.

## Refuted (with the evidence)
- muse P1 "pipeline_transcript() can raise OSError on a corrupt file and crash the whole sweep": it catches OSError,
  ValueError, KeyError, TypeError and AttributeError per record file (fetch.py:184), and glob of an unreadable
  directory returns []: refuted the same way at r119 c1. The sweep's own `except ValueError` is transcript_store's id
  check.
- muse P2 "clock skew between state_at and acquired_at": both are written by processes on this one machine
  (the watcher's config.iso() and the pipeline's transcript ingest), from the same clock.
- muse P2 "verify claim() atomicity": one UPDATE ... WHERE video_id=? AND state IN (...) under the queue's lock
  (queue.py:171-177, in the context); the sweep only moves next_at.
- muse P3 "a 24/7 stream could cause a probe storm": the pipeline transcribes a stream only once its probe sees it
  over (transcript_store skips is_live), so a stream still live gets no record; a re-transcription is one probe.
- qwen P3 "parallelise the sweep": a few dozen rows at most, one glob each (r119 c1's measure).

## Recorded
- qwen P2 a warning when state_at is missing (it never is: add_video, set_state and claim all set it; a missing one
  fails closed). muse P2 batch the store reads (small counts; r119 recorded the same). muse P3 log the ValueError skips
  (an id transcript_store refuses: no such video folder can exist).

Suite after the fix: tests/ingest 449 passed. Mutations M69-M74: 6 of 6 killed; test_r125 passes unmutated in the
guarded environment.
