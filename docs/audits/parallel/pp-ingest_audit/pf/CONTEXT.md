### What this answers
- L-aa (the laws): "time savers are automatic once measured and audited". The orchestrator's standing job for
  pp-ingest: "every new upload mined within minutes". The watcher listed each channel by RSS first (the uploads
  playlist only when RSS failed), and its publish -> seen lag was 13-28 min on RSS (INGEST-FAIL-07: the feed is a
  15-minute cache).

### The measurement (read-only; nothing written to the watcher's store)
- An A/B, Nov 14, 3 h from 08:31 ET: 6 busy channels (Bloomberg Television, CNBC Television, Fox Business, Yahoo
  Finance, Bitcoin Magazine, Simply Bitcoin) listed by RSS and by the uploads playlist every 2 min, recording when each
  source FIRST listed each video: 25 new uploads listed by both; RSS later by a median 6 min (up to 18; 2 in the same
  round); 1 listed by the playlist only, 0 by RSS only; 0 errors (about 540 playlist listings).
- The watcher's own log: 102 watch cycles on the playlist (RSS down, between 19:33 ET Nov 12 and 03:20 ET Nov 14,
  about 6,500 listings): a cycle took 76 s on average (at most 253 s; 7 s on RSS), through the 3-slot yt-dlp gate it
  shares with the probe and the captions; no rate limit or bot check (the gate's breaker never opened).

### The change under review (98a57406 against a49aac40)
- config.PLAYLIST_FIRST = True.
- watch.poll_channel(..., playlist_first=None): the uploads playlist first, then RSS while the canary says RSS answers;
  playlist_first False: RSS first, the playlist second (the order before). The listing code of each source is
  unchanged (moved into two local functions); the error text joins both sources' reasons as before.
- The publish time of a video is not the listing's: fetch measures it from yt-dlp's own metadata per video (RSS's
  exact time when RSS listed it, else yt-dlp's timestamp), so the latency figures stay measured.
- tests: the playlist used first and RSS never asked; the playlist failing -> RSS while it answers, else the
  channel's error and backoff; the two RSS-path tests pinned to the old order. Two mutations, each caught.
- design 3.

### Questions for the reviewers
1. Does any path lose a video, double-count one, or change what the queue records (via, ETag, newest_published)?
2. The cost: 64 yt-dlp listings a cycle through the shared 3-slot gate (captions wait behind it): is the trade sound?
3. Anything that would make the yt-dlp breaker (a rate limit) more likely to trip and stall the captions?
