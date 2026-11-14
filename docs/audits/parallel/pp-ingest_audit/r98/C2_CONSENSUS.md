# Ruling 98 (the miner's Plan B, the paid route), cycle 2 (cross-validation): consensus

Reviewers (Heimdall): glm-5.3-flash (261 s, $0.005): "P0 CRITICAL - none ... P1 HIGH - none ... Production ready: yes,
with one condition"; muse-spark-open (397 s, $0.030): every cycle-1 fix verified "FIXED"; "Production ready: yes, with
conditions"; qwen3.8-27b (311 s, $0.009): withdrew its cycle-1 "RoleCaps race" ("the reserve / release pattern under a
single lock actually prevents the specific race I described"); its "Production ready: No" lists as conditions the two
fixes cycle 1 already made (the zone check, the priced worst-case reservation: in the code, each with its test) and
"run the tests" (282 pass): refuted with that evidence. Cycle 2: $0.044; the audit, both cycles: $0.092 (Heimdall).

## The conditions: IMPLEMENTED (tests/ingest/test_paid_route.py, the last test)
- glm N1: the "CAP REACHED" head was checked only while the route stayed open, so a cap crossed in the tick the signal
  came back was never said. The day's cap is now checked before the route closes too.
- muse P1: the head's threshold was the flat cap_reserve_usd while the calls are held to their priced worst case. It
  now fires when the day's spend plus the CHEAPEST back-end's priced worst case passes the cap (no call of the route
  can start any more): `Router.min_call_cost`.
- muse P2: the lock order (RoleCaps.lock, then the queue's lock in the loader; nothing calls RoleCaps while holding the
  queue's lock) is written at `RoleCaps._roll`.

## Recorded
- glm N3: if the one Heimdall re-mine of a paid-route video meets another outage, the video continues on the normal
  partial-retry path (MINED_PARTIAL is mined again every 6 h on the mine role, flags unioned): no loss.
- glm N4: "newest first, conversations first" is read as conversations first, then newest (A32); if the orchestrator
  meant newest first with conversations breaking ties, it is the order of one sort key (service._paid_due).
- muse P2 (a midnight test with an in-flight reservation; transcript reads on the first tick) and qwen P2 (the
  conversation cache's eviction): recorded; the reservation is released in run()'s finally whatever the day, and only
  new uploads are measured.

Tests: tests/ingest 282 passed (11 in test_paid_route.py).
Verdict: no P0 or P1 in either cycle after verification; every condition in. Deploy.
