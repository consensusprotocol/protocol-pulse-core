# RULING 87 AMENDED, THE WATCHER'S SIDE, cycle 2: consensus

Reviewers (Heimdall): glm-5.3-flash (236 s, $0.005): "Yes, with conditions" (P0 / P1 none); muse-spark-open (267 s,
$0.030): no new P0 / P1, "none that change the ship decision"; qwen3.8-27b (346 s, $0.010): "Yes" (P0 none; its P1,
the probe thread at shutdown, it calls acceptable itself: daemon threads); minimax-m3.1-flash (420 s, $0.010, cut at
its output limit after its findings): both cycle 1 fixes "real and correctly implemented", new findings P2 / P3 only.
Cycle 2: $0.055 (both cycles $0.105). Diff reviewed: the working tree at the cycle 1 commit against 2ec81efc.

## Agreed by all four (verified)
- C1-1 (the bounded join) and C1-2 (no KeyError on a dead family thread) are real fixes, each pinned by a test.
- With the amended module clearing failing_since_utc on any answer in both modes, the paid route's 20-minute read
  follows the amended definition unchanged (glm re-read _route_tick).

## Conditions taken (each with a test that fails without it, or a text-only change)
- C2-1 (glm N2 / its condition 2, minimax N5): the probe's wait came from config alone, so a probe back-end with a long
  timeout_s could stretch a probe past the module's 120 s probe interval (its slot claimed by another prober, its
  answer stale). The wait is now capped: min(longest probe back-end deadline + 15 s, the module's PROBE_EVERY_S - 15
  s) (_probe_wait). Test: 60 s gives 75; a 600 s back-end gives 105, under 120 (the uncapped version fails it).
- C2-2 (glm condition 3): live.json `down_signal.probe_wait_s`; design 14 names the starved-family case (a call
  waiting on the throttle or the router's global slots behind mining counts as not answered: conservative), the up
  to 3 probe calls, and failures_noted counting family notes (minimax N7, N8).
- C2-3 (minimax N6): a family still asking at the deadline is recorded as "no answer by the probe's N s deadline
  (still asking)", not "no answer within" (it may still answer later; the evidence says what was known).

## Recorded, not changed
- minimax N3 / N4: a throttled or hung probe leg holds its back-end slot until its own HTTP deadline (daemon threads,
  never cancelled); the next probe counts that family as not answered: conservative, bounded by the transport timeout.
- muse: the strict `<` for a familyless first failure (same-second ties start the clock at the same time); the staging
  base URL (pre-existing, base_url_env moves it).
- qwen P2: the margin as config; per-family debug logging (the evidence line already names each family's outcome).

Suite: tests/ingest 343 passed (the builder's amended module 3cf4c42f at its path). Verdict: four of four ship; live at
the next watcher restart (it asks no calibration quote: the 10:53 live one is under a day old).
