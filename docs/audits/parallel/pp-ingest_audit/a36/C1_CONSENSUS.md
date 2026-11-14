# A36 WIDEN (the orchestrator's 09:02 ruling, mine-hook/4), cycle 1: consensus

Reviewers (Heimdall): qwen3.8-27b (226 s, $0.023): "ready for production"; muse-spark-open (571 s, $0.032): "This diff
is ready to merge" (P0 none); glm-5.3-flash: its first call failed (the gateway's 503 "the marketplace is restarting");
re-run alone (811 s, $0.008), cut at its output limit after section 3, its findings summary complete (no P0 / P1 on
the diff). Cycle 1: $0.063. Diff reviewed: c1141fff against af298eb9.

## Agreed by all three (verified)
- `is_conversation` implements "skip only a marked episode under 0.3" on every input: no markers -> asked; a marked
  episode with an unmeasurable rate -> asked; a bool count or rate is never taken for a number (Python's bool-is-int
  trap excluded first); None / {} -> asked. episode_measure always gives an int count and a float or None rate.
- The version bump re-queues the window through `hooks --rerun`; a solo episode's prompt is unchanged (same cache key).
- `spotlight_asked_videos` (spot_rows IS NOT NULL) counts the passes that asked, better than the old threshold proxy.

## Fixed (with a test)
- C1-1 (muse P3, glm P2 on its package): live.json `hooks_12h.rows_by_episode` still bucketed at 1.0 turns a minute.
  It now buckets by the hook pass's own threshold and says what happened: ">= 0.3 turns / min (asked)", "< 0.3 turns
  / min (a marked solo episode)", "unmarked captions (asked)", "marked, its rate not measured (asked)". The
  conversation service test asserts the two buckets its videos fall in.
- C1-2 (glm P3): design 13 says the rate is rounded to 2 decimals (0.295 reads as 0.3).

## Refuted or recorded
- muse P1 "validate the video id before the yt-dlp call (flag injection)": the id is inside an https://... URL
  argument (never a leading '-'), passed as a list (no shell), and listings are id-validated; refuted.
- glm P3 "spotlight_asked_videos misses a pass whose spotlight question crashed": it is marked "(spotlight crashed)"
  and counted once `hooks --rerun` asks it again; recorded.
- Pre-existing, outside this diff (recorded): glm P2 SWITCH_RE expects an "*-FIRST" up mode (ruling 87's module);
  glm P3 mine_cost_usd after a paid then Heimdall re-mine keeps the last route's cost; glm P3 the cap's brief
  double count (by design, conservative); glm P3 handoff's os.link race; muse P1 state + event in one transaction;
  muse P2 queue-depth and latency alerts, purge's per-file publish lookups, a yt-dlp canary; qwen P2 structured logs.

Suite: tests/ingest 311 passed.
