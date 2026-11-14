### The order (orchestrator 06:13 ET Nov 14, RULING 98, verbatim)
"ORCHESTRATOR RULING 06:13 to PP-INGEST, your open question. THE MINER'S PLAN B (ruling 98): PBX's fail-safe (21:08
Nov 13) covers the miner too: "if [Heimdall] ever fails to respond for more than perhaps 10 to 20 minutes ... use Groc
mainly or whatever other AI tokens we have". So: Heimdall down by ruling 87's signal for 20 minutes -> the miner mines
NEW uploads only (published in the last 6 h, newest first, conversations first; no backfill, no hook-pass re-runs) on
the paid route: Grok first, then the Gemini key (fenced to this pipeline: allowed), others only if a probe shows
credit. Cap $2.00 vendor-reported per day on this route, then queue and wait as now. Every row mined this way carries
miner_route so its labels can be re-checked on Heimdall when it returns. Back to Heimdall after 3 good probes. Every
switch on STATE line 1 in capitals. The spend freeze of Nov 12 is lifted for this one route and this cap only. Audit
as one change, then it is live."

### Background
Ruling 87's shared signal is live in this watcher (pp-ingest_audit/r87/, r87claim/): the builder's module
(pp-selectid pipeline/heimdall_health.py at 11ed255f) keeps mode heimdall_first / plan_b (plan_b after 15 min of no
answer from any Heimdall family; back after 3 good probes) and failing_since_utc (the start of the current run of no
answers, cleared by any answer). Until this change the miner's Plan B was queue and wait (the spend freeze).

### The readings (STATE assumptions A27-A32)
- A27 "Heimdall down by ruling 87's signal for 20 minutes": the shared state says plan_b AND its failure clock
  (failing_since_utc) is at least 20 min old: no Heimdall family has answered for 20 min running (PBX: "fails to
  respond for more than perhaps 10 to 20 minutes"). The route closes when the signal is back (3 good probes). A signal
  not read opens nothing, closes nothing and spends nothing.
- A28 "no hook-pass re-runs": the hook pass is not run on the paid route at all (the hook role stays on Heimdall; its
  passes wait during the outage and catch up inside their 12 h when Heimdall is back).
- A29 "others only if a probe shows credit": no other paid vendor is wired (it would need a credit probe). Grok, then
  Gemini; when both fail or the cap is reached, the videos queue and wait.
- A30 The cap: $2.00 per ET day across the route's back-ends, counted from each call's recorded cost (xAI's own
  usage.cost_in_usd_ticks; Gemini reports none, so its price-table estimate counts, an upper bound), with $0.25 held
  for every call in flight, so no call starts past the cap.
- A31 "so its labels can be re-checked on Heimdall when it returns": every new row carries miner_route (the role that
  mined it); when the signal is back, each video the paid route mined that is still inside 12 h (its moments' life) is
  mined again on the mine role, once; every moment both passes found carries both models' flags (ledger.carry_forward:
  a flag either set stands); a moment only the paid route found keeps its labels and miner_route, and the second-model
  check (ruling 40 P1) still asks Heimdall about its imperative / single-source flags.
- A32 "conversations first": the caption turn measure of ruling 92 (turns per minute >= 1.0, the split its report
  used); "newest first" within each group.

### The change (diff since 56f6eac7)
- providers.json: role mine_paid (xai_frontier, gemini_frontier; freeze_lifted names ruling 98; daily_cap_usd 2.0;
  cap_reserve_usd 0.25); paid_route {role, after_down_s 1200, new_within_s 21600, recheck_within_s 43200,
  conversation_tpm 1.0, label}.
- providers.py: validate_config (freeze_lifted needs a cap; paid_route needs down_signal and a capped role); RoleCaps
  (per ET day, loader from the queue, reservations); Router.run reserves before each call of a capped role and
  releases after; available/_try/effective let a frozen vendor through ONLY for a role with freeze_lifted.
- queue.py: columns mine_route, recheck_ts; role_spend_since; recheck_due.
- mine.py: every row's miner_route (the role).
- downsignal.py: view (the shared state as last read); _route_tick (open / close / cap reached, each a STATE line-1
  head, an evidence line, an event); paid_open (read by the mine loop); signal_back(); the Plan B head's tail and
  miner_plan_b now say ruling 98; snapshot paid_route.
- spend.py: SWITCH_PATTERN takes the route's heads.
- service.py: mine_once (paid: _paid_due: new uploads only, conversations first, then newest; dispatch on the paid
  role) or (not paid: _queue_rechecks when the signal is back, then the normal order); mine_video(v, role); _settle
  records mine_route; the router gets role_spend.
- tests/ingest/test_paid_route.py (6); the suite 277.

### Questions for the reviewers (file:line)
1. The opening (plan_b + failure clock >= 20 min) and closing (signal up) rules; an answer that clears the clock while
   still plan_b (the route does not open; once open it stays open until the signal is back).
2. The cap: can a call start past it (reservations, the ET day's roll, the loader at a restart)? The overshoot bound.
3. The freeze lift: any path where another role reaches a frozen vendor?
4. The re-mine: once per video (recheck_ts), only when the signal is back; any path where a paid row's flags are lost?
5. The mine loop on the paid route: only <= 6 h videos, conversations first; older videos wait; no hook pass.
6. Threads: paid_open written by the signal thread, read by the mine thread; RoleCaps under its lock.
7. STATE: the route's heads (on, off, cap reached once a day) on line 1 with the signal's switches.
