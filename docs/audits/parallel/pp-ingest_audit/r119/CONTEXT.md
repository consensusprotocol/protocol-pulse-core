# r119: mined within 10 minutes of its transcript, Bitcoin channels first (the orchestrator's 13:05 ET ruling, Nov 16)

## The ruling (verbatim)
"ORCHESTRATOR RULING 13:05 ET Nov 16: your 12:45 question R13: YES. I have ordered the integrator to release the GPU0
lease between scoring calls (or let the pipeline's ingest use GPU1 when GPU0 is leased), builds first. Mine each video
within 10 minutes of its transcript, Bitcoin channels first. Longer term, design (do not build yet) a second caption
source that does not depend on this machine's YouTube quota, and say what the 429s correlate with."

## Where it stands (r118, live since 11:53 ET, 9125517f)
While YouTube refuses captions (HTTP 429 since 07:47 ET), a new upload's transcript is the main tree's own Whisper
record (pipeline/transcript_ingest.py, cron */30), which r118's fetch step takes (fetch.take_pipeline_transcript, read
only, every check, write-once) when the video is next tried. That next try is the video's own retry time: 10 min after
a caption 429, up to 30 min for a VOD without English captions (fetch._caption_retry_at), the gate's pause plus 5 min
for a probe the gate held back. So a record could land and wait up to 30 minutes before it was taken. The queue took due
videos newest first, whatever the channel.

## The change
1. fetch.pipeline_sweep(q, now): every video waiting on a transcript (probe_retry, captions_pending) inside its
   moments' life (config.EXPIRY_H, 12 h) whose next try is later and whose record is in the pipeline's store
   (fetch.pipeline_transcript: every r118 check) is due NOW; one queue event each. No YouTube request (a glob per
   waiting video, and a read of a record that is there). An id transcript_store refuses is skipped.
2. service.fetch_once runs the sweep before claiming due videos, at most every fetch.PIPELINE_SWEEP_S (60 s), and
   never while the yt-dlp gate is open (no probe can run then; the sweep runs once it shuts). The probe that follows is
   the one r118 makes before any take (it decides Short / live / upcoming / age / length / duplicate; unchanged:
   fetch.process, pipeline/ingest/fetch.py:249). So a record is taken within about a minute of landing, and the miner
   (its loop every 5 s, 3 videos at once) mines it at once: inside the ruling's 10 minutes.
3. Bitcoin channels first: Queue.due(states, limit, first=()) and Queue.hook_due(horizon, limit, first=()) order the
   videos of `first` (channel ids) before every other, newest first in each (no `first`: the old order exactly).
   service._first(): the channel ids of the registry's tiers up to config.BITCOIN_TIER_MAX (2): tier 1 Bitcoin-native
   (What Bitcoin Did, Bitcoin Magazine, TFTC, ...), tier 2 Bitcoin and crypto companies, media and podcasts (Scott
   Melker, DataDash, Strategy, Simply Bitcoin, CoinDesk, ...); tier 3 is mainstream finance and news (Bloomberg, CNBC,
   Fox Business, Yahoo Finance, WSJ, FT, ...). The registry has no other beat field; the pipeline's own transcript
   ingest already orders by tier (transcript_ingest.py:97). Read from the fetch round's own registry read, else at most
   once a minute; a registry that cannot be read keeps the last set (an order hint never stops a loop). Used by the
   fetch round (FETCH_DUE), the miner (MINE_DUE) and the hook pass (hook_due). The dormant paid route (ruling 118
   removed its config) keeps its own order.
4. The take's attempt line and queue event carry the record's acquired_at (when the pipeline's Whisper finished), so
   the transcript-to-mined latency is measured from the records.
5. tests/ingest/test_paid_route.py: a stub of Queue.due takes the new keyword.

## What to check (the laws below apply)
- No video skips the probe's checks because of the sweep (it only moves next_at; fetch.process decides everything).
- The sweep never touches a video in flight (probing, mining) or in any state but the two transcript waits, never one
  past its 12 h, and never makes a request to YouTube; while the gate is open it does not run (no busy loop).
- With no Bitcoin channel set, every order is exactly the old one; the SQL stays parameterised.
- Tier as "Bitcoin channel": is tier 2 right to count (Bitcoin and crypto companies, media, podcasts)?

Suite: tests/ingest 420 passed (6 new in test_r119.py). Mutations (scratch copy, files restored from backups): 10 of 10
killed (M22-M31).
