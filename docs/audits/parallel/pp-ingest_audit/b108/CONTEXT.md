### The orders this change answers (verbatim where quoted)

ORCHESTRATOR 21:22 ET Nov 14 (after PBX 21:09: "apply these new cost efficient methods ... and begin a brand new
batch"): "NEW BATCH, 'BATCH 3', STARTS NOW and runs to 21:10 ET Nov 15." "RULING 108, BATCH 3's MONEY, ALL-IN, one
ledger for everything every session spends on this pipeline (builds, sealing, shadow, AUDITS, probes, scribe, mining,
flag checks; vendor-reported, abandoned calls at the model's own rate): CAP $8.00 for the 24 hours. ... Budget inside
it: builds + sealing $4.50, audits $2.50, mining and checks $1.00; a session that needs another's share asks on line 1
with its default." "audits Heimdall-first, diff-scoped, capped $0.30 / $1.00 (ruling 107 (2))." "Your spend (mining,
hook pass, flag checks, calibration, audits) goes to the builder's batch ledger hourly: 'BATCH 3 ingest spend: $x'
first on STATE line 1." "Tomorrow is Sunday: uploads will be light; say on line 1 when 3 hours pass with nothing
Bitcoin."
RULING 107 (2) (20:20 Nov 14): reviewers Heimdall-first, two Heimdall families (qwen + glm); a third only when the
two disagree on a critical / high point or one is down; under 60 changed lines one reviewer set, two cycles, capped
$0.30 (else $1.00); each review's vendor-reported cost recorded. Ruling 107's basis for an abandoned call: the model's
vendor-reported dollars per prompt token x the prompt sent; the list price until the model has 3 reported calls.
Standing: ruling 87 (every switch of the shared Heimdall signal goes on STATE line 1, in capitals); ruling 106 (d)
(pp-ingest raises "ALARM FOR PBX: <one sentence>. Waiting since <time>." on its line 1; the integrator sends it);
ruling 98 (the miner's paid route, the one exception to pp-ingest's spend freeze, capped $2.00 an ET day); ruling 106
(b): when two readings are possible, the STRICTER one for a number or money hold.

### What the change does

1. STATE line 1 (spend.py): ONE physical line holding, in this order, the batch spend ("BATCH <n> ingest spend: ..."),
   an alarm ("ALARM FOR PBX: ...") and ruling 87's switch line (every switch head, newest first), joined by " | ".
   `_segments` splits line 1 back into its notices (the batch and alarm writers refuse any "|" or newline, so the
   split is exact); `_place` orders the leading block: line 1, then the cycles line, then every other notice (as
   before). New writers: write_batch_notice, write_alarm_notice. Before this change the switch line was always the
   first line; a hand-written first line would have broken the notice block (the head parse stops at the first
   non-notice line), which is why the batch line had to be known to the code.
2. batch.py + batch.json: the batch (name, 24 h window in ET, pp-ingest's share "mining and checks" $1.00), read again
   when the file changes (a new batch is a data change). `notice()` gives the line: the watcher's spend from the
   batch's start to its latest whole hour (21:10, 22:10, ...) from its call records (the queue's calls table; cache
   hits skipped), by use (mining, hook pass, flag checks with calibration, probes), at the recorded cost (vendor-
   reported where providers.json says the back-end's replies carry one: cost_from_usage / the new cost_reported on the
   one paid back-end that reports cost ticks), an abandoned call (kind 'timeout' with no cost) at the model's own rate
   (ruling 107; read only from calls before the hour's end so a past hour's figure never moves), pp-ingest's audits
   from their cost ledger, and the cycles' 3-hour quiet head. `share_left()`: the share minus the watcher's spend in
   the batch to now; 0 outside a batch or when the file cannot be read (fail closed: the paid route spends nothing
   until the next batch's money is set).
3. Ruling 98's paid route inside the share: providers.RoleCaps.reserve_why also checks `share()` (set by the service)
   with every capped call in flight held against it; a share that cannot be read lets no call start. The run()
   message names which limit refused. downsignal: the opening head names the share; `_cap_check` says once per share
   when no paid call fits ("MINER PAID ROUTE CAP REACHED (<share>: $x LEFT): QUEUE AND WAIT").
4. service.health_once calls `_batch_notice` (after the cycles line): composes and writes the batch line; a failure is
   logged once per cause and line 1 keeps its last figure.
5. cycles.quiet_head: the 3-hour note's head alone, '' when no cycle ran in the window or a window had Bitcoin.
6. tests/ingest/xllm_audit.py (the audit driver, ruling 107 (2)): the package is the laws + this context + the diff
   (no whole files, no design document); reviewers qwen + glm by default (a third family by --only; the paid frontier
   reviewers stay out under pp-ingest's freeze); the cap ($0.30 under 60 changed lines, else $1.00, both cycles
   together, from COST.json) is checked BEFORE any call against an estimate of the next cycle; after the cycle every
   review is booked (reported, a failed call's own figure, or an abandoned review at the model's own rate) to COST.json
   and one record per review to the watcher's audit ledger (config.paths()["audit_spend"]), which batch.py reads.

### Unchanged code the diff relies on (not in the hunks)
- providers.py:699 RoleCaps._roll calls the loader (the queue) under RoleCaps.lock; the documented lock order is
  RoleCaps.lock then the queue's lock; `share()` (batch.share_left -> q.rows) follows the same order. Nothing calls
  RoleCaps while holding the queue's lock.
- providers.py:897 the reservation is released in `finally` after the call; RoleCaps.add books the call's recorded
  cost (an abandoned paid call books None -> 0 in the daily cap; the batch share books it at the model's own rate).
- providers.py:904 min_call_cost: the cheapest paid back-end's priced worst case (at least cap_reserve_usd).
- downsignal.py:309 _route_switch uppercases the head and appends " |"; heads are written in order, kept until written.
- spend.py:68 every STATE rewrite is under an flock on state_doc.lock and an os.replace (spend.py:91); a STATE file
  that exists and cannot be read raises (never rewritten from nothing).
- queue.py:239 Queue.call stamps ts = the service clock at insert (a call is counted in the hour it ended).
- service.py:740 health_once runs every 60 s on the health thread.

### Questions for the reviewers
1. Can any sequence of writers (batch, alarm, switch, cycles, outage, purge, signal, meter) lose or duplicate a notice,
   or leave line 1 in a form `_segments` splits wrongly?
2. Can a paid call start past the batch's share (concurrent reservations, a share that raises, NaN, outside a batch)?
3. Is the hourly figure final once its hour is out (late records, the abandoned booking's history)? Is anything
   booked as $0 that is not known to be $0?
4. The driver: can a cycle spend past its cap, or can a review's cost be lost or double counted (re-runs, failures)?
Only report issues you can verify from the code provided. If uncertain, say so; do not guess. Cite file:line.
