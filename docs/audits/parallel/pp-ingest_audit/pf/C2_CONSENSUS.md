# PLAYLIST FIRST, RSS THE FALLBACK, cycle 2: consensus

Reviewers (Heimdall): glm-5.3-flash (185 s, $0.005): "Yes, with two conditions" (P2); muse-spark-open (276 s, $0.030):
"Nothing new that changes the ship decision"; minimax-m3.1-flash (337 s, $0.010): "Yes with conditions" (no P0; two P1s,
P2s); qwen3.8-27b (344 s, $0.010): "Yes". Cycle 2: $0.054 (both cycles $0.103). Diff reviewed: the working tree at the
cycle 1 commit against a49aac40.

## Agreed by all four (verified)
- No video lost, double-counted or mis-recorded; the old order intact behind playlist_first=False; the cycle 1
  fallback (a rate-limited playlist -> RSS, no backoff) and the per-source live figure are in, with tests.

## Conditions taken (each with a test that fails without it: three mutations, each caught)
- C2-1 (minimax N1, P1): the listing now makes 64 yt-dlp calls a cycle through the 3-slot gate it shares with the
  probe and the captions; a slow YouTube (each listing up to its 120 s timeout) could hold every slot and starve the
  captions, the critical path. The listing now holds at most YTDLP_LIST_SLOTS = 2 of the 3 at once (LIST_SLOTS in
  watch.playlist_list): one slot is always free for the probe and the captions. Test: six concurrent listings never
  hold more than two.
- C2-2 (glm condition 2, muse): RSS is now the fallback, so its failure detail is kept in last_error too (it was kind
  only). Test: both sources failing name each one's reason.
- C2-3 (glm condition 1): the per-source figure is computed over every live discovery with a measured publish time
  (not only the mined ones); (minimax N6) a video listed before it went public (an upcoming stream) counts 0, never a
  negative. Test (an upcoming row; the unclamped version fails).
- C2-4 (minimax N1b, N2, N8; text only): design 3 states that the fallback protects the listing only (the probe and the
  captions still wait out the breaker), that the per-source figure is each source's own discoveries (not the paired
  A/B), and that the publish time is now yt-dlp's own timestamp almost always.

## Recorded, not changed
- minimax N3 (each add_video its own transaction): pre-existing; the overnight playlist cycles (same volume) ran at
  76 s mean. minimax N4 (the coverage check lists RSS-first): kept independent of the watcher's listing on purpose
  (its verdict matches on video ids). minimax N5 (an env kill switch): the old order is one constant away and either
  way needs a restart.

Suite: tests/ingest 363 passed.
