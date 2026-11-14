# PLAYLIST FIRST, RSS THE FALLBACK (L-aa, a measured time saver), cycle 1: consensus

Reviewers (Heimdall): glm-5.3-flash (331 s, $0.006): "Ready for production" (P0 none; two P1s); muse-spark-open (460 s,
$0.033): "ready for production ... Ship it" (P0 none; two P1s); qwen3.8-27b (417 s, $0.011): "production-ready" (its P1:
a metrics endpoint, outside this change). minimax-m3.1-flash: no review (an empty reply at its output limit; not
re-run). Cycle 1: $0.049. Diff reviewed: 98a57406 against a49aac40.

## Agreed by all three (verified)
- No video lost or counted twice; the queue records the same (via, ETag kept, newest_published); the old order kept
  behind playlist_first=False; the error text joins both sources' reasons as before.

## Taken (each with a test that fails without it: mutation-checked)
- C1-1 (glm P1, its half that concerns this change): while the yt-dlp breaker is open the gate raises 'rate_limited'
  at once (it never blocks), so a playlist-first channel falls back to RSS and is never backed off as long as RSS
  answers. Pinned by a test (with the fallback removed it backs off and fails). The per-channel backoff on a rate
  limit remains only when RSS is down too: the path that existed before this change (recorded).
- C1-2 (muse P1): live.json `publish_to_discovered_min_by_source` (p50 / p90 / n per listing source, live
  discoveries with a publish time), so the 6-minute gain is measured in production and a regression is visible.

## Refuted or recorded
- muse P1 "BACKFILL_H with the playlist's approximate date can mark a 71 h old video seen_old": only at a channel's
  FIRST listing, and only at the 72 h edge; any video older than 12 h is past the moments' expiry (rulings 76/77), so
  no usable row is lost. Refuted as without effect.
- glm P1 "rotate the channel order across cycles (the 253 s tail)": the mean cycle is 76 s against a 10-minute period;
  the back of the registry waits about a minute more than the front, well inside the 6-minute gain. Recorded, with
  the per-source live figure (C1-2) to show whether it matters.
- qwen: the gate's calm() on any success shortens a later pause (by design); a metrics endpoint (outside this change).

Suite: tests/ingest 361 passed.
