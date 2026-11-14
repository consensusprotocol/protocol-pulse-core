# Ruling 98 (the miner's Plan B, the paid route), cycle 1: consensus

Reviewers (Heimdall): qwen3.8-27b (337 s, $0.010), muse-spark-open (491 s, $0.031): "ready for production ... No P0",
glm-5.3-flash (812 s, $0.007). Each finding checked against the code. Cycle 1: $0.048.

## Fixed (a test each in tests/ingest/test_paid_route.py)
- C1-1 (qwen P0 "RoleCaps race", glm P1; the same defect, not a race: reserve and add are each under the lock): the
  flat $0.25 held per call was smaller than one call can cost (Gemini: 2 attempts x its 16,000-token floor at the
  price table's $25 / MTok, ~$0.83), so the day could end past $2.00. Each call now holds its PRICED WORST CASE (every
  attempt at its full reply budget, the prompt at ~3 characters a token; at least cap_reserve_usd): no call starts
  unless its worst case fits under the cap, so $2.00 is a ceiling (the route may stop a little short of it).
- C1-2 (glm P0): a failure clock without its time zone would read as local (ET) time and open the route 5 h late. A
  zoneless time is no clock (the builder's module's own rule): the route does not open, live.json says why.
- C1-3 (glm P1): a route head the STATE file did not take was lost (the signal's own switches are retried). Route heads
  are now kept in order and written at the next tick (logged once while they wait; live.json `heads_waiting`).
- C1-4 (muse P2): a video mined on the paid route in a SECOND outage inside its 12 h would never be re-checked
  (recheck_ts already set). Mining on the paid route now clears recheck_ts, so its Heimdall re-mine is due again.
- C1-5 (glm P2): live.json `paid_route.why_not_open` (the signal not read; plan_b with N of 20 min; no failure clock;
  the signal up); a transcript whose turns cannot be measured is logged (it is mined after the conversations).
- C1-6 (glm P2, muse P1): `paid_route` at the top of live.json and of `ingest_watch.py status` (the spend today, the
  cap, open or not, why).

## Refuted or recorded
- muse P1 "an out-of-band alert (Telegram / PagerDuty) when the route opens": this session must never send to
  Telegram or publish (its standing orders); the ruling's channel is STATE line 1 ("every switch on STATE line 1 in
  capitals"), which the route uses.
- muse P2 "a reservation leaks across ET midnight": every reservation is released in run()'s finally whatever the day;
  a call that starts before midnight and ends after counts once, on the day it ended.
- muse P2 "a stale failing_since opens the route spuriously": a clock that old means no family has answered since;
  the module clears it at any answer.
- muse P2 "transcript reads in the sort": only the new uploads (<= 6 h) are measured, once each (cached).
- glm P1 "stratify ruling 40's precision study by miner_route": that study is an offline measurement (done Nov 13),
  not this change; rows now carry miner_route, so a later study can split by it. Recorded.
- qwen P1 (ledger.offset_before speed) and P1 (the conversation cache's size): outside this change or immaterial
  (the cache holds only new uploads seen on the paid route).

Tests: tests/ingest 281 passed (10 in test_paid_route.py).
