# Ruling 87 (the shared Heimdall-down signal), cycle 2 (cross-validation): consensus

Reviewers: glm-5.3-flash (358 s, $0.005): "P0 CRITICAL - none. P1 HIGH - none ... Production ready: yes, with one
condition" (N1); muse-spark-open-816b (309 s, $0.028): "P0 CRITICAL - none in this diff. All 6 C1 defects are fixed
and verified ... Production ready: yes, with conditions"; qwen3.8-27b (318 s, $0.023): agreed with all six cycle-1
fixes and with the refutation of glm's D1, then its reply looped (the same agreement lines repeated to the end; no
final verdict of its own). Each reviewer checked the fixes in the working tree. Cycle 2: $0.057; the audit, both
cycles: $0.118 (Heimdall).

## The conditions
- glm's one condition, N1: IMPLEMENTED (C2-1). A probe whose `probe_result` call failed (the shared state unreadable
  at that moment) was counted as delivered and its outcome lost. Now the outcome is kept for the next tick while it is
  younger than the module's probe interval (`PROBE_EVERY_S`, 120 s); no new probe starts while it waits; an older one
  is dropped and counted (`counts.probe_reports_lost`), never reported late (an old answer proves nothing about now).
  Its evidence line is written once. Test: `test_a_probe_the_shared_state_did_not_take_is_kept_while_fresh_then_dropped`.
- muse (1) "mine.py:481: include the risk penalty in the overlap rank": NOT CHANGED; the disagreement is recorded.
  It is outside this diff (the mining's overlap dedup; "the better one" was decided at the original build's audit c2).
  glm in this cycle: "P3 polish, not a defect: the comparison is symmetric ... the rank used everywhere else (the
  adapter's sort) passes the full line and is unaffected". Cycle 1's reasoning stands: the merged line's flags are the
  union of both observations, so each observation's own penalty would favour the observation that saw FEWER flags.
- muse (2) "watch live.json `down_signal` for the first 48 h (`counts.probes_not_made` 0 outside drills; `not_read`
  null)": adopted as an operating note in STATE.
- muse (3) "do not lift the spend freeze": it is not lifted; the miner's Plan B stays queue and wait.

## Also from cycle 2
- glm N5: `tools/ingest_watch.py status` now shows the watcher's `down_signal` block (read from live.json, with that
  file's age). Test: `test_status_shows_the_watchers_view_of_the_signal`.
- glm D3 / N6 (P2, latency): `providers.Overrides.get` runs its `on_change` (one event, one log line) inside its lock
  on the calling thread; older than this change, now also reached from `noted()`. It runs only when overrides.json
  changes (a drill) and never touches the shared lock (A24 holds). Recorded, not changed.
- glm N11: `counts.drill_notes` counts drill notes (one per flush with any drill outcome), as the module's `drills`
  does; outcomes inside one flush are not counted separately. Recorded.
- glm N2: a crash in the middle of announcing a switch can repeat its evidence line and event (not its STATE head:
  C1-1); the same at-least-once shape as C1-1, informational. Recorded.
- glm N4: the probe's two 60 s deadlines sum to the probe interval: a doubly hanging probe uses its whole slot. Do not
  lengthen the 60 s without lengthening the interval.
- The questions, answered across both cycles: 4xx and 429 count as not answered (the signal measures whether the fleet
  gets through: glm N7; muse); the 5 s flush, the module's 30 s heartbeat and the 15-minute rule absorb note-ordering
  noise (glm N8; muse); two processes probing in one slot cost one redundant probe (glm N9: "more independent evidence,
  a claim primitive would add a failure mode"; muse: the module's semantics). REQUESTS R12 stays a non-blocking
  proposal to the builder.

Tests: tests/ingest 268 passed (24 in test_signal.py).
Verdict: no P0 or P1 in either cycle after verification; every condition implemented or recorded with its reason.
Deployed after this commit (see STATE).
