# r120: a stream that is over but still processing (post_live) takes the pipeline's record (Nov 16)

## Why (found by r119's own measure)
The orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its transcript". r119 measures
each mined video's seconds from its transcript record to its rows. At 14:26 ET it flagged Yahoo Finance kh3U_15pFZc
LATE: 3,205 s. YouTube kept that finished livestream in live_status "post_live" (the stream over, its video still
processing) from 12:26 to 14:26 ET; the pipeline's transcript ingest Whispered it at 13:33 (its acquire() skips only
is_live / is_upcoming: pp-selectid pipeline/transcript_store.py:454); the watcher's fetch.process treated post_live like
is_live (LIVE, re-probed every 20 min, meta.json not written) and r119's sweep looks only at probe_retry and
captions_pending, so the record waited until YouTube said was_live.

## The change
1. fetch.process: a stream still live (is_live) is LIVE as before, never taken. A post_live video with no record in the
   pipeline's store is LIVE as before (re-probed every 20 min, no caption download, no meta.json). A post_live video
   WITH a record goes on through every remaining check of the probe (publish time, age, duration, too long, title
   duplicate) and takes the record (take_pipeline_transcript, every r118 check) like a VOD; its duration, when the
   probe gives none yet, is the length the pipeline recorded. If the take is refused (the copy differs), it waits LIVE
   as before (no caption download while post_live).
2. fetch.pipeline_sweep also makes due a LIVE row whose stored live_status is post_live (never one still is_live).
3. stall.py counts such a row as waiting ("STREAM OVER, ITS VIDEO STILL PROCESSING") and its act may make it due.

## Facts checked before building
- Nothing downstream treats post_live: pp-ingest's ledger, contract and miner never read live_status (it rides in the
  row's source as information); the builder's code reads live_status only in transcript_store (skip is_live /
  is_upcoming), so the pipeline itself transcribes post_live.
- The timeline: the pipeline's post_live record of kh3U_15pFZc runs 1,066-1,070 s, the final video 1,080 s; word-level
  timing is the pipeline's job at cut time, on the video's own audio (INGEST_DESIGN: "word-level timing stays the
  pipeline's job at cut time"), as for the pipeline's own post_live records.
- INGEST-FAIL-01 (a meta written while live froze 46 videos) is about a meta read later as "still live": here the video
  is transcribed and then mined at once (terminal), and no later step reads its meta's live_status.

## What to check
- A stream still live can never be taken or have its meta written; every other probe check still runs for post_live.
- No caption download for a post_live video on any path.
- The sweep and the self-check never touch an is_live row.

Suite: tests/ingest 430 passed (8 new in test_r120.py). Mutations M36-M42: 7 of 7 killed.
