# r122: a stub can be a moment's answer for a real video (Nov 17, 07:4x ET)

## Why
r121 (live since 19:42 ET Nov 16) files a probe that yt-dlp answers with its stub (none of live_status, duration,
timestamp, release_timestamp, upload_date) as UNAVAILABLE "no metadata", and gave it up after NO_METADATA_MAX_TRIES (6)
counted on the row's `tries`. CoinDesk yHuY9r30Oug ("CoinDesk Live at Solana Breakpoint 2026 Day 1 | Replay") was
live 01:08-02:08 ET Nov 17 (four re-probes, each a try), then yt-dlp answered two probes with a stub (02:28, 03:28):
`tries` reached 6 and it was given up. The pipeline's transcript ingest Whispered it at 07:00 (112 min of audio) and a
probe at 07:4x gave every fact again (post_live, 6,728 s, release_timestamp): the stub was a moment's answer (around a
premiere's end), and the watcher would never have mined a video the pipeline had transcribed.

## The change (pipeline/ingest/fetch.py)
- "no metadata" is given up only once the video is past its moments' life (config.EXPIRY_H from its publish, else its
  discovery), never on a count of tries (which holds its live re-probes); inside it, tried again every
  NO_METADATA_RETRY_S, now 900 s (a stub can pass in minutes; a dead video costs one probe a quarter hour, 48 at most).
- fetch.pipeline_sweep also makes due an UNAVAILABLE video whose reason is "no metadata: ..." once the pipeline's store
  holds its record (the pipeline saw it, so it exists); any other UNAVAILABLE (private, removed, age-gated: answered by
  YouTube) is never touched. fetch.process then probes it: facts -> the usual paths (r120 for a stream over); a stub
  again -> UNAVAILABLE again.
- tests/ingest/test_r121.py follows the new give-up rule.

## What to check
- A video YouTube really refuses (private, removed: UNAVAILABLE_MARKS) is never retried more than before.
- A stub never waits as a stall (UNAVAILABLE is outside stall.WAITING) and is given up past 12 h.
- The sweep's new clause takes only "no metadata" rows with a record, inside 12 h.

Suite: tests/ingest 437 passed (3 new in test_r122.py). Mutations M44-M50: 7 of 7 killed.
