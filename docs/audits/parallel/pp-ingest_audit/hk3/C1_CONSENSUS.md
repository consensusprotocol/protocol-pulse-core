# The hook pass mine-hook/3 (the orchestrator's 08:15 ruling 2: ruling 92 (b) + (c)), cycle 1: consensus

Reviewers (Heimdall): qwen3.8-27b (268 s, $0.024): "ready for production"; glm-5.3-flash (688 s, $0.007): "production-
ready ... Ship it" (P0 none); muse-spark-open (548 s, $0.033): "ready for production ... Ship it" (P0 none). Each
finding checked against the code. Cycle 1: $0.064. Diff reviewed: ef431ff5 against 197b35ec.

## Agreed by all three (verified)
- The conversation gate: `is_conversation` is measured, fail-closed (unmarked, unmeasured, a bool or a string are not
  conversations); `mine_video` measures the episode before any window is sent, so one call's prompt, validator and
  max_n always agree (5 in a conversation, 3 elsewhere; 2 spotlights); no 6-hook or 3-spotlight reply passes.
- The solo hook prompt is byte-identical (same cache key): a solo re-run replays from the reply cache.
- Spotlight rows carry every integrity field a moment carries (risk flags, eligibility, expiry, miner_route, the
  episode, the speaker measure); duration and the OPENER rule are applied; the adapter treats them like any row.
- carry_forward: any hint travels; a later line's own hint wins.

## Fixed (each with a test)
- C1-1 (glm P1): `check_roles` named only the mining questions' roles; a missing `flagcheck` role would make the
  calibration crash-loop (fail closed, with backoff) instead of stopping the start. It now also needs flagcheck.ROLE.
  Test: test_service test_every_mining_question_needs_its_role_to_start (the flagcheck case fails on ef431ff5).
- C1-2 (glm P2): after the spotlight question was added, a pass's note and event said "N window(s) failed" without
  which question. The note, the log line and the event now split it (hook N, spotlight M; failed_hook /
  failed_spotlight). Test: test_service test_the_hook_note_says_which_question_failed (fails on ef431ff5).
- C1-3 (muse P1): no test followed a spotlight row through the packager's read. The conversation test now reads the
  adapter (best_unused_moments) and requires every spotlight row without a measured speaker change to come back (a
  regression guard: a future adapter filter on role_hint would fail it). The test's spotlight spans now start on a
  '>>' sentence (one speaker inside), as the prompt asks.
- C1-4 (glm P3): design section 15 listed miner_route as mine | mine_paid | hook; it now names spotlight too.

## Refuted or recorded
- muse P1 "run the hook and spotlight questions concurrently": both fan out over the same 4-slot window executor
  (HOOK_WINDOWS, which keeps the moment pass's slots free: audit r80 c1); a conversation's windows fill it already, so
  running the two at once changes the order of calls, not the time; declined.
- muse P2 "hook the soonest-expiring video first": contradicts ruling 77 (newest uploads first); refuted.
- muse P2 "spot_rows DEFAULT 0": NULL means "not a conversation, not asked"; 0 means "asked, none"; kept.
- qwen 1 "2 spotlights a window dilutes 'ONE passage'": ruling 90's one is the VIDEO's (one moment per spotlight);
  candidates per window are supply, the builder picks one; kept at 2 (A38).
- glm 1.1(a) a crash between the two questions re-asks the hook question on retry: from the reply cache, free; kept.
- glm 1.1(g) among several earlier hints, the first carries: hints are advisory; recorded.
- Pre-existing, outside this change (recorded for a later change, none blocks this one): glm P1 the paid-route cap's
  accounting rests on the calls table alone (a lost insert is unseen spend); glm P1 a latency notice (p90 publish ->
  mined / hooked) on STATE; glm P2 the A/B judge prompt's <transcript> block is not _untrusted; glm P2 yt-dlp's timeout
  inside transcript_store (not this repo's code); glm P2 check_next is never pruned; glm P3 the ET / UTC day split
  between RoleCaps and SpendBook; muse P2 spotlight drop reasons in live.json (the event and the log carry them); muse
  P2 a disk alert on reported_not_purged; qwen P1 structured logs.

Suite after the fixes: tests/ingest 305 passed.
