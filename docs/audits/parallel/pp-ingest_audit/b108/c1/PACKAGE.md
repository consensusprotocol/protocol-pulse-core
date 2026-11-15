# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 9b8a5136
# The change under review: git diff HEAD (working tree) of pipeline/ingest, tools/ingest_watch.py, tests/ingest

## GOVERNING LAWS (this code MUST comply with every law below: flag any violation)
Standing order (PBX 02:30 / orchestrator 02:45 ET 2026-11-12) and laws this code must obey:
- BUILD: continuous ingest of every registered partner channel (RSS first, yt-dlp metadata fallback, ~10 min, ETag /
  backoff, last-seen ledger, re-upload / duplicate detection, Shorts and live-in-progress handled explicitly, durable
  queue); captions into the SAME transcript store format via the store's writer, in a staging copy, never the main
  tree; first-pass mining by sentence ids on Heimdall (bounded concurrency, queue-aware backoff on 429/503, <= ~20 in
  flight, spend tracked vs the $460 cap with a 90 % tripwire that NOTIFIES and falls back, never halts); an
  append-only moment ledger matching pp-selectid's pp.moment/1 contract and an adapter "best unused moments since T";
  a daily coverage check; a blind A/B of back-ends (generator and judge different models).
- L-x NO SINGLE MODEL, ULTRON FIRST: every model role behind ONE provider interface with >= 2 interchangeable
  back-ends; the run continues when any one vendor is down or out of credit; no vendor / model name outside the
  provider config; the local model on Ultron is the default where it meets the bar (it runs only under the GPU0
  lease, which this builder never holds: no GPU use at all here).
- L-l a model reply counts only whole: strict schema, ids validated, NOTHING REPAIRED; a failed call is never a
  default, a pass or an agreement. L-j / L-m: fail closed; nothing measured is never a pass.
- L-h / L-k: transcript text is read as spoken (entities decoded, split tokens joined) through the repo's canonical
  form; stored records are never rewritten. L-e: word timing for anything heard (the packager's job at cut time).
- L-u hard exclusions (accusation, partner attack, buy/sell imperative, guaranteed return, single-source breaking, ad
  read, third-party media) are flagged and excluded before ranking; L-v: a moment never spans a speaker change;
  re-uploads excluded; time-sensitive language needs the original publish time.
- Secrets: keys read by name from the env file inside code; never printed, logged or written.
- SPEND FREEZE (orchestrator 05:30 ET Nov 12, until told otherwise): paid frontier vendors (OpenAI, Anthropic, xAI;
  Google by the builder's assumption) are never called by any role; the watcher's mine chain is Heimdall then the
  local interface ONLY; if both are down the videos queue and are mined later, never on a paid frontier model; Heimdall
  mining continues; the 90 % tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of STATE), never a halt.
Only report issues you can verify from the code provided. Do not speculate. Cite file:line.

## THE CHANGE UNDER REVIEW: its orders and design
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


```diff
diff --git a/pipeline/ingest/batch.json b/pipeline/ingest/batch.json
new file mode 100644
index 00000000..67988eac
--- /dev/null
+++ b/pipeline/ingest/batch.json
@@ -0,0 +1,9 @@
+{
+  "_note": "Ruling 108 (orchestrator 21:22 ET Nov 14, after PBX 21:09): BATCH 3's money, all-in, one ledger for everything every session spends on the pipeline (the builder keeps it): cap $8.00 for the 24 hours; inside it builds + sealing $4.50, audits $2.50, mining and checks $1.00 (pp-ingest's share). pp-ingest's spend goes to that ledger every hour as 'BATCH 3 ingest spend: $x' first on STATE line 1 (batch.py). A new batch is a data change: the watcher reads this file again when it changes. Outside start_et..end_et the paid route spends nothing (no batch money is set).",
+  "name": "BATCH 3",
+  "start_et": "2026-11-14 21:10",
+  "end_et": "2026-11-15 21:10",
+  "share_usd": 1.00,
+  "share_of": "mining and checks",
+  "cap_usd": 8.00
+}
diff --git a/pipeline/ingest/batch.py b/pipeline/ingest/batch.py
new file mode 100644
index 00000000..33291a47
--- /dev/null
+++ b/pipeline/ingest/batch.py
@@ -0,0 +1,208 @@
+"""pipeline/ingest/batch.py: ruling 108 (orchestrator 21:22 ET Nov 14), the batch's money on pp-ingest's side.
+
+One ledger holds everything every session spends on the pipeline (the builder keeps it). pp-ingest's spend goes to it
+every hour as 'BATCH <n> ingest spend: $x (...)' FIRST on STATE line 1 (spend.write_batch_notice). The batch (its
+name, its 24 h and pp-ingest's share, "mining and checks") is batch.json, read again whenever it changes: a new batch
+is a data change, with no restart. Counted, from the batch's start to its latest whole hour (21:10, 22:10, ...: line 1
+changes once an hour):
+- every call the watcher made, from its call records (the queue's calls: mining, the hook pass, the flag checks with
+  their calibration, ruling 87's probes, ruling 98's paid route; a cached reply is free), at the vendor's own figure
+  where its replies carry one (providers.json cost_from_usage / cost_reported), else at the price table (said apart);
+- an ABANDONED call (a timeout, or a call cut off after CUT_S in flight with no answer, a dropped connection: nothing
+  booked) at the model's own rate (ruling 107: the model's reported dollars per prompt token x the prompt, the role's
+  average on that model; the list price of the prompt until the model has 3 reported calls); an error the vendor
+  answered (an HTTP status) books what it reported;
+- pp-ingest's audits, from their cost ledger (tests/ingest/xllm_audit.py appends one record per review).
+Ruling 98's paid route is held inside the share: share_left() is what the router's RoleCaps checks before a paid call
+starts, counted to NOW (the check is live; only line 1's figure waits for the hour: audit b108 c1). Outside a batch (or with the batch file unreadable) nothing is left: the paid route spends nothing until the
+next batch's money is set (the stricter reading of a money hold, ruling 106 (b)).
+"""
+import json
+import math
+import os
+import re
+import threading
+from datetime import datetime
+from zoneinfo import ZoneInfo
+
+ET = ZoneInfo("America/New_York")
+SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch.json")
+NAME_RE = re.compile(r"BATCH \d+")
+USE = {"mine": "mining", "mine_paid": "mining", "hook": "hook pass", "spotlight": "hook pass",
+       "flagcheck": "flag checks and calibration", "probe": "probes"}
+ORDER = ("mining", "hook pass", "flag checks and calibration", "probes", "other")
+MIN_REPORTED = 3                     # ruling 107: the list price of the prompt until the model has 3 reported calls
+CUT_S = 30.0                         # a call that failed after this long in flight with no answer may have been billed
+HOUR_S = 3600
+
+_lock = threading.Lock()
+_cache = {}
+
+
+def _et_ts(s):
+    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=ET).timestamp()
+
+
+def _hm(ts, fmt="%H:%M ET"):
+    return datetime.fromtimestamp(ts, ET).strftime(fmt)
+
+
+def load(path=None):
+    """The batch: {name, t0, t1, share_usd, share_of}; read again when the file changes. Raises (OSError, ValueError,
+    KeyError, TypeError) when it cannot be read or holds no batch: every caller fails closed (nothing left to spend)."""
+    path = path or SPEC
+    st = os.stat(path)
+    key = (path, st.st_mtime_ns, st.st_size)
+    with _lock:
+        if _cache.get("key") == key:
+            return _cache["spec"]
+    with open(path) as f:
+        j = json.load(f)
+    name, share = j["name"], float(j["share_usd"])
+    t0, t1 = _et_ts(j["start_et"]), _et_ts(j["end_et"])
+    if not (isinstance(name, str) and NAME_RE.fullmatch(name)) or not t1 > t0 or not (math.isfinite(share) and
+                                                                                       share >= 0):
+        raise ValueError(f"{path} holds no batch (a name 'BATCH <n>', an end after the start, a finite share >= 0)")
+    spec = {"name": name, "t0": t0, "t1": t1, "share_usd": share,
+            "share_of": str(j.get("share_of") or "mining and checks")}
+    with _lock:
+        _cache.update(key=key, spec=spec)
+    return spec
+
+
+def _reports_cost(bcfg):
+    """A back-end whose replies carry their own cost (providers.json: cost_from_usage, or cost_reported)."""
+    return bool(bcfg.get("cost_from_usage") or bcfg.get("cost_reported"))
+
+
+def abandoned_usd(q, model, role, price, until):
+    """Ruling 107: an abandoned call at the model's own rate: its reported dollars per prompt token (over every call of
+    the model that booked a cost) x the prompt (the role's average on the model, else the role's on any model, else the
+    model's); at the list price of the prompt (price in_per_mtok) until the model has MIN_REPORTED such calls. Only the
+    calls recorded before `until` (the end of the hour counted) are read, so an hour's figure never moves once it is
+    out. None when no prompt size is known at all (said on the line, never read as $0)."""
+    r = q.rows("SELECT SUM(cost_usd) AS c, SUM(prompt_tokens) AS p, COUNT(*) AS k FROM calls WHERE model=? AND "
+               "cost_usd > 0 AND prompt_tokens > 0 AND ts < ?", (model, until))[0]
+    avg = None
+    for sql, args in (("model=? AND role=?", (model, role)), ("role=?", (role,)), ("model=?", (model,))):
+        avg = q.rows(f"SELECT AVG(prompt_tokens) AS a FROM calls WHERE {sql} AND prompt_tokens > 0 AND ts < ?",
+                     args + (until,))[0]["a"]
+        if avg is not None:
+            break
+    if avg is None:
+        return None
+    if (r["k"] or 0) >= MIN_REPORTED and r["p"]:
+        rate = float(r["c"]) / float(r["p"])
+    else:
+        rate = float((price or {}).get("in_per_mtok") or 0.0) / 1e6
+    return float(avg) * rate
+
+
+def abandoned(r):
+    """A call with no cost booked that may have been billed: abandoned at its deadline (a timeout), or cut off after
+    CUT_S in flight with no answer (no HTTP status: a dropped connection); the stricter reading of ruling 108's basis
+    (ruling 106 (b)). An error the vendor answered (a status) is what it reported."""
+    return r["cost_usd"] is None and (r["kind"] == "timeout" or (r["http_status"] is None and
+                                                                 float(r["latency_s"] or 0.0) >= CUT_S))
+
+
+def watcher_spend(q, t0, t1, cfg):
+    """The watcher's spend in [t0, t1) from its call records (cache hits are free and skipped): {"by": {use: usd},
+    "reported", "estimated", "abandoned": usd, "abandoned_n", "unpriced_n", "calls": counts}."""
+    be = cfg.get("backends") or {}
+    out = {"by": {}, "reported": 0.0, "estimated": 0.0, "abandoned": 0.0, "abandoned_n": 0, "unpriced_n": 0,
+           "calls": 0}
+    memo = {}
+    for r in q.rows("SELECT role, backend, model, kind, cost_usd, http_status, latency_s FROM calls WHERE ts >= ? AND "
+                    "ts < ? AND COALESCE(kind, '') != 'cache'", (t0, t1)):
+        use = USE.get(r["role"], "other")
+        if abandoned(r):
+            k = (r["model"], r["role"])
+            if k not in memo:
+                memo[k] = abandoned_usd(q, r["model"], r["role"], (be.get(r["backend"]) or {}).get("price"), t1)
+            usd = memo[k]
+            if usd is None:
+                out["unpriced_n"] += 1
+                usd = 0.0
+            else:
+                out["abandoned"] += usd
+                out["abandoned_n"] += 1
+        else:
+            usd = float(r["cost_usd"] or 0.0)
+            out["reported" if _reports_cost(be.get(r["backend"]) or {}) else "estimated"] += usd
+        out["by"][use] = out["by"].get(use, 0.0) + usd
+        out["calls"] += 1
+    return out
+
+
+def audit_spend(path, t0, t1):
+    """pp-ingest's audits in [t0, t1) from their cost ledger (one JSON record per review: ts, usd, ...) -> (usd,
+    reviews, unreadable records). A missing ledger is no audit yet."""
+    usd, n, bad = 0.0, 0, 0
+    try:
+        f = open(path)
+    except FileNotFoundError:
+        return 0.0, 0, 0
+    with f:
+        for line in f:
+            if not line.strip():
+                continue
+            try:
+                r = json.loads(line)
+                ts, u = float(r["ts"]), float(r["usd"])
+                if not (math.isfinite(ts) and math.isfinite(u) and u >= 0):
+                    raise ValueError(line[:80])
+            except (ValueError, KeyError, TypeError):
+                bad += 1
+                continue
+            if t0 <= ts < t1:
+                usd += u
+                n += 1
+    return usd, n, bad
+
+
+def notice(q, now, cfg, audit_path, quiet="", spec_path=None):
+    """'BATCH <n> ingest spend: $x (...)' for STATE line 1: the spend from the batch's start to its latest whole hour,
+    closed at its end; quiet: the cycles' 3-hour note, said on line 1 too (the orchestrator's 21:22 order). Raises when
+    the batch file cannot be read (the caller logs it; line 1 keeps its last figure)."""
+    b = load(spec_path)
+    tail = f"; {quiet}" if quiet else ""
+    if now < b["t0"]:
+        return f"{b['name']} ingest spend: $0.0000 (the batch starts {_hm(b['t0'], '%H:%M ET %b %d')}){tail}"
+    mark = min(b["t1"], b["t0"] + int((now - b["t0"]) // HOUR_S) * HOUR_S)
+    closed = mark >= b["t1"]
+    w = watcher_spend(q, b["t0"], mark, cfg)
+    au, an, bad = audit_spend(audit_path, b["t0"], mark)
+    mc = sum(w["by"].values())
+    uses = ", ".join(f"{u} ${w['by'][u]:.4f}" for u in ORDER if u in w["by"])
+    span = f"{_hm(b['t0'], '%H:%M ET %b %d')} to {_hm(mark, '%H:%M ET %b %d' if closed else '%H:%M ET')}"
+    basis = ["vendor-reported"]
+    if w["abandoned_n"]:
+        basis.append(f"${w['abandoned']:.4f} booked for {w['abandoned_n']} abandoned call(s) at the model's own rate")
+    if w["estimated"]:
+        basis.append(f"${w['estimated']:.4f} priced from the table (its vendor reports no cost)")
+    if w["unpriced_n"]:
+        basis.append(f"{w['unpriced_n']} abandoned call(s) NOT PRICED (no prompt size known)")
+    if bad:
+        basis.append(f"{bad} audit cost record(s) UNREADABLE (not counted)")
+    text = (f"{b['name']} ingest spend: ${mc + au:.4f} ({'CLOSED, ' if closed else ''}{span}: {b['share_of']} "
+            f"${mc:.4f} of the ${b['share_usd']:.2f} share" + (f" ({uses})" if uses else "") +
+            f", {w['calls']} model call(s); audits ${au:.4f}, {an} review(s); " + "; ".join(basis) + ")")
+    if closed:
+        text += (f"; NO BATCH OPEN SINCE {_hm(b['t1'], '%H:%M ET %b %d')}: the paid route spends nothing until the "
+                 "next batch's money is set")
+    return text + tail
+
+
+def share_left(q, now, cfg, spec_path=None):
+    """Ruling 108 for ruling 98's paid route: (dollars left of the batch's share for mining and checks, what it is),
+    counted to now. Outside a batch, or with the batch file unreadable: (0.0, why): the paid route spends nothing."""
+    try:
+        b = load(spec_path)
+    except Exception as e:                                # noqa: BLE001 (fail closed: no money is set)
+        return 0.0, f"the batch file cannot be read ({type(e).__name__}): no batch money is set"
+    if not b["t0"] <= now < b["t1"]:
+        return 0.0, (f"no batch open ({b['name']} runs {_hm(b['t0'], '%H:%M ET %b %d')} to "
+                     f"{_hm(b['t1'], '%H:%M ET %b %d')})")
+    w = watcher_spend(q, b["t0"], now + 1.0, cfg)
+    return b["share_usd"] - sum(w["by"].values()), f"{b['name']}'s ${b['share_usd']:.2f} share for {b['share_of']}"
diff --git a/pipeline/ingest/config.py b/pipeline/ingest/config.py
index e78c45ba..5c85e480 100644
--- a/pipeline/ingest/config.py
+++ b/pipeline/ingest/config.py
@@ -104,6 +104,7 @@ def paths(root=None):
         "work": os.path.join(ing, "work"),
         "purge": os.path.join(ing, "purge"),
         "signal": os.path.join(ing, "down_signal.jsonl"),         # ruling 87: this watcher's evidence file
+        "audit_spend": os.path.join(ing, "audit_spend.jsonl"),    # ruling 108: one record per audit review's cost
     }
 
 
diff --git a/pipeline/ingest/cycles.py b/pipeline/ingest/cycles.py
index 0f152c9c..74af5f58 100644
--- a/pipeline/ingest/cycles.py
+++ b/pipeline/ingest/cycles.py
@@ -155,3 +155,13 @@ def _quiet(q, t0, names, ncycles):
              f"NOTHING BITCOIN AMONG THE {len(known)} MINED IN THE LAST 3 H ({queued} NOT MINED YET)")   # head says so
     return (f"{title}: {len(seen)} upload(s) seen{f' ({kinds})' if kinds else ''}, none of the {len(known)} mined with a "
             f"Bitcoin term in any window{tail}")
+
+
+def quiet_head(q, now_ts, window_h=WINDOW_H):
+    """The 3-hour note's head alone ("NOTHING BITCOIN IN THE LAST 3 H", or "... AMONG THE K MINED ..."), for STATE line 1
+    (ruling 108's batch line; the orchestrator's 21:22 order: Sunday's light uploads, said on line 1); '' when the
+    window had Bitcoin, or when no cycle ran in it (the watcher stopped: nothing measured is never read as quiet)."""
+    t0 = now_ts - window_h * 3600
+    if not q.rows("SELECT 1 AS x FROM events WHERE kind='watch_cycle' AND ts >= ? LIMIT 1", (t0,)):
+        return ""
+    return _quiet(q, t0, {}, 0).split(":", 1)[0]
diff --git a/pipeline/ingest/downsignal.py b/pipeline/ingest/downsignal.py
index d0d3052e..4c8f5e32 100644
--- a/pipeline/ingest/downsignal.py
+++ b/pipeline/ingest/downsignal.py
@@ -259,10 +259,12 @@ class DownSignal:
             if v.get("mode") == DOWN and fs_t is not None and now - fs_t >= float(pr["after_down_s"]):
                 st = {"open": True, "since": _iso(now)}
                 cap = float(self.roles[pr["role"]]["daily_cap_usd"])
+                left, what = self._share()
+                inside = "" if what is None else f", INSIDE {what} (${max(left, 0.0):.2f} LEFT)"   # ruling 108
                 self._route_switch(st, f"MINER ON THE PAID ROUTE ({pr['label']}: NO {self.label} ANSWER FOR "
                                        f"{int((now - fs_t) // 60)} MINUTES, SINCE {fs}; NEW UPLOADS OF THE LAST "
                                        f"{int(pr['new_within_s'] // 3600)} H ONLY, CONVERSATIONS FIRST; CAP "
-                                       f"${cap:.2f} A DAY, ET)", "paid_route_open")
+                                       f"${cap:.2f} A DAY, ET{inside})", "paid_route_open")
         elif v.get("mode") == self.up:
             self._cap_check(now)                     # the day's cap is said before the route closes (audit r98 c2)
             st = {"open": False, "since": _iso(now)}
@@ -274,9 +276,22 @@ class DownSignal:
             self.route_why = None
             self._cap_check(now)
 
+    def _share(self):
+        """Ruling 108: (dollars left of the batch's share, what it is) from the router's RoleCaps, (None, None) when no
+        share is set; a share that cannot be read is nothing left (as RoleCaps reads it: no paid call starts)."""
+        sh = self.router.caps.share
+        if sh is None:
+            return None, None
+        try:
+            left, what = sh()
+            return float(left), str(what)
+        except Exception as e:                       # noqa: BLE001
+            return 0.0, f"the batch's share (not read: {type(e).__name__})"
+
     def _cap_check(self, now):
         """The cap reached, said once per ET day: when no call of the route can start any more (the day's spend plus
-        its cheapest back-end's priced worst case passes the cap: audit r98 c2)."""
+        its cheapest back-end's priced worst case passes the cap: audit r98 c2). Ruling 108: the same when the batch's
+        share has no room for that call, said once per share (a new batch may say it again)."""
         role = self.paid["role"]
         cap, spent = float(self.roles[role]["daily_cap_usd"]), self.router.caps.today(role)
         day = datetime.fromtimestamp(now, ET).date().isoformat()
@@ -284,6 +299,12 @@ class DownSignal:
             self.q.kv_set("paid_cap_day", day)
             self._route_switch(None, f"MINER PAID ROUTE CAP REACHED (${spent:.2f} OF ${cap:.2f} TODAY, ET): "
                                      "QUEUE AND WAIT", "paid_route_cap")
+        left, what = self._share()
+        if what is not None and not self.router.min_call_cost(role) <= left and \
+                self.q.kv_get("paid_share_said") != what:
+            self.q.kv_set("paid_share_said", what)
+            self._route_switch(None, f"MINER PAID ROUTE CAP REACHED ({what}: ${max(left, 0.0):.2f} LEFT): QUEUE AND "
+                                     "WAIT", "paid_route_cap")
 
     def _route_switch(self, st, words, kind):
         now = self.clock()
diff --git a/pipeline/ingest/providers.json b/pipeline/ingest/providers.json
index 105e2a1e..26abe209 100644
--- a/pipeline/ingest/providers.json
+++ b/pipeline/ingest/providers.json
@@ -63,7 +63,7 @@
     "xai_frontier": {
       "kind": "openai_compat", "vendor": "xai", "enabled": true, "base_url": "https://api.x.ai/v1",
       "model": "grok-4.20-0309-reasoning", "key_env": "XAI_API_KEY_MEDLEY",
-      "json_schema": true, "max_inflight": 4, "timeout_s": 300,
+      "json_schema": true, "max_inflight": 4, "timeout_s": 300, "cost_reported": true,
       "note": "the vendor reports each call's cost (usage.cost_in_usd_ticks, 1 USD = 1e10 ticks): that is the recorded cost; the price table is only the budget guard's fallback (2026-11-12: it over-estimated the A/B judge 7x)",
       "price": {"in_per_mtok": 5.0, "out_per_mtok": 25.0, "basis": "estimate"},
       "daily_budget_usd": 10.0
diff --git a/pipeline/ingest/providers.py b/pipeline/ingest/providers.py
index ea8394b7..68b62cdd 100644
--- a/pipeline/ingest/providers.py
+++ b/pipeline/ingest/providers.py
@@ -687,10 +687,12 @@ ET = ZoneInfo("America/New_York")
 class RoleCaps:
     """Ruling 98: a role's daily spend cap, per ET day, counted from every call's recorded cost (the vendor's own where
     it reports one, else the price-table estimate), with a reservation held for every call in flight so no call starts
-    past the cap. loader(role, since_ts) -> dollars already spent (the queue's calls) at the first use of a day."""
+    past the cap. loader(role, since_ts) -> dollars already spent (the queue's calls) at the first use of a day.
+    share (ruling 108): None, or a callable -> (dollars left of the batch's share, what it is): a capped call must also
+    fit under it, with every capped call in flight held against it (the paid route stays inside pp-ingest's share)."""
 
-    def __init__(self, loader=None, clock=time.time):
-        self.loader, self.clock = loader, clock
+    def __init__(self, loader=None, clock=time.time, share=None):
+        self.loader, self.clock, self.share = loader, clock, share
         self.lock = threading.Lock()
         self.day, self.spent, self.reserved = {}, {}, {}
 
@@ -703,13 +705,29 @@ class RoleCaps:
             self.day[role], self.spent[role] = d, float(self.loader(role, start) or 0.0) if self.loader else 0.0
 
     def reserve(self, role, amount, cap):
+        return self.reserve_why(role, amount, cap) is None
+
+    def reserve_why(self, role, amount, cap):
+        """None when the call's priced worst case is held (released by the caller); else why it may not start: the
+        role's daily cap, or the batch's share (ruling 108; a share that cannot be read lets no call start)."""
         with self.lock:
             self._roll(role)
             r = self.reserved.get(role, 0.0)
             if self.spent[role] + r + amount > cap + 1e-9:
-                return False
+                return (f"the role's daily cap ${float(cap):.2f} is reached (${self.spent[role]:.2f} today, ET; this "
+                        f"call may cost ${amount:.2f})")
+            if self.share is not None:              # lock order as the loader's: RoleCaps, then the queue's
+                try:
+                    left, what = self.share()
+                    left = float(left)
+                except Exception as e:              # noqa: BLE001 (fail closed: an unread share spends nothing)
+                    return f"the batch's share could not be read ({type(e).__name__}): no paid call starts"
+                held = sum(self.reserved.values())
+                if not held + amount <= left + 1e-9:                # NaN never passes
+                    return (f"{what} is spent (${max(left, 0.0):.4f} left, ${held:.4f} held by calls in flight; "
+                            f"this call may cost ${amount:.4f})")
             self.reserved[role] = r + amount
-            return True
+            return None
 
     def release(self, role, amount):
         with self.lock:
@@ -860,10 +878,9 @@ class Router:
                 continue
             need = max(reserve, self._worst_cost(bid, prompt, mt, int(rc.get("attempts", 3)))) if cap is not None \
                 else 0.0                                      # audit r98 c1: the call's priced worst case is held
-            if cap is not None and not self.caps.reserve(role, need, float(cap)):
-                tried.append((bid, "skipped", f"the role's daily cap ${float(cap):.2f} is reached "
-                                              f"(${self.caps.today(role):.2f} today, ET; this call may cost "
-                                              f"${need:.2f})"))
+            refused = self.caps.reserve_why(role, need, float(cap)) if cap is not None else None
+            if refused is not None:                           # the day's cap or the batch's share (ruling 108)
+                tried.append((bid, "skipped", refused))
                 continue
             try:
                 out = self._try(bid, role, prompt, schema, validate, tag, int(rc.get("attempts", 3)), mt)
diff --git a/pipeline/ingest/service.py b/pipeline/ingest/service.py
index c56c1fb5..64e4e214 100644
--- a/pipeline/ingest/service.py
+++ b/pipeline/ingest/service.py
@@ -50,7 +50,8 @@ import traceback
 from concurrent.futures import ThreadPoolExecutor
 from datetime import datetime, timedelta, timezone
 
-from . import config, coverage, cycles, downsignal, fetch, flagcheck, ledger, mine, providers, purge, spend, stats, watch
+from . import batch, config, coverage, cycles, downsignal, fetch, flagcheck, ledger, mine, providers, purge, spend, stats, \
+    watch
 from . import queue as Q
 from .contract import ContractUnavailable
 
@@ -126,6 +127,7 @@ class Service:
         self.meter = spend.CreditMeter(mc, self.router.backends[mc["backend"]], clock=clock,
                                        on_change=self._meter_change)
         self.router.meter = self.meter
+        self.router.caps.share = self._batch_share       # ruling 108: the paid route stays inside the batch's share
         self.executor = ThreadPoolExecutor(max_workers=int(self.cfg["global"]["max_inflight"]),
                                            thread_name_prefix="win")
         self.videos = ThreadPoolExecutor(max_workers=3, thread_name_prefix="vid")
@@ -140,6 +142,7 @@ class Service:
         self.check_allowed, self.check_calibrated = None, 0.0
         self.check_recal_s = CHECK_RECALIBRATE_S        # the wait before the next calibration (set by each one)
         self.cycles_error = None                         # the cycles line's last failure (logged once per cause)
+        self.batch_error = None                          # ruling 108: the batch line's last failure (logged once)
         self._reuse_tried = False                       # the start's one look at the stored live calibration
         self.stop = threading.Event()
         self.rss_mode, self.rss_checked = False, 0.0
@@ -748,6 +751,7 @@ class Service:
                              signal=self.hsig.snapshot() if self.hsig is not None else None)
         self._outage_notice(now)
         self._cycles_notice(now)
+        self._batch_notice(now)
         day = config.iso()[:10]
         hour = datetime.now(timezone.utc).hour
         if force_coverage or (hour >= COVERAGE_HOUR_UTC and self.q.kv_get("coverage_day") != day and
@@ -778,6 +782,26 @@ class Service:
                 self.log(f"the cycles line could not be written: {why}")
             self.cycles_error = why
 
+    def _batch_share(self):
+        """Ruling 108, for the router's RoleCaps: (dollars left of the batch's share for mining and checks, what it is);
+        nothing left outside a batch or when the batch file cannot be read (batch.share_left)."""
+        return batch.share_left(self.q, self.clock(), self.cfg)
+
+    def _batch_notice(self, now):
+        """Ruling 108 (orchestrator 21:22 ET Nov 14): pp-ingest's spend in the batch FIRST on STATE line 1, to the
+        batch's latest whole hour (the builder books it every hour), with the cycles' 3-hour note when it holds (the
+        same order: Sunday's light uploads, said on line 1). Rewritten only when the text changes; a failure is logged
+        once per cause, keeps the last figure on line 1 and never stops the health loop."""
+        try:
+            line = batch.notice(self.q, now, self.cfg, self.p["audit_spend"], quiet=cycles.quiet_head(self.q, now))
+            spend.write_batch_notice(line, notify_path=self.p["notify"])
+            self.batch_error = None
+        except Exception as e:                       # noqa: BLE001 (a report line never stops the watcher)
+            why = f"{type(e).__name__}: {str(e)[:200]}"
+            if why != self.batch_error:
+                self.log(f"ruling 108: the batch line could not be written: {why}")
+            self.batch_error = why
+
     def _purge_blocked(self, why):
         """A purge that cannot run safely: once it has lasted PURGE_NOTICE_S, a line at the top of STATE (audit r77
         c1, muse P1); cleared by the first pass that runs."""
diff --git a/pipeline/ingest/spend.py b/pipeline/ingest/spend.py
index 0084ca1f..e95d2df6 100644
--- a/pipeline/ingest/spend.py
+++ b/pipeline/ingest/spend.py
@@ -25,20 +25,47 @@ SWITCH_PATTERN = (r"\d\d:\d\d ET: (?:SWITCHED TO PLAN B|BACK TO [A-Z0-9_-]+-FIRS
                   r"MINER (?:ON|OFF) THE PAID ROUTE|MINER PAID ROUTE CAP REACHED)")       # ruling 98: the miner's route
 SWITCH_RE = re.compile("^" + SWITCH_PATTERN)
 SIGNAL_RE = re.compile(r"^[A-Z0-9_-]+ " + SIGNAL_SUFFIX)    # any label's: only the signal writes this notice
+BATCH_PATTERN = r"BATCH \d+ ingest spend: "   # ruling 108: pp-ingest's spend in the batch, FIRST on STATE line 1
+BATCH_RE = re.compile("^" + BATCH_PATTERN)
+ALARM_PREFIX = "ALARM FOR PBX: "              # ruling 106 (d): on line 1, after the batch spend; the integrator sends it
+SEP = " | "                                   # line 1's notices, joined: the batch spend, an alarm, the switch line
 NOTICE_RE = re.compile(r"^(?:[A-Z0-9_-]+ SPEND (?:AT 90%|UNMEASURED)|" + OUTAGE_PREFIX + "|" + PURGE_PREFIX + "|" +
                        CYCLES_PREFIX + " TO |" + r"[A-Z0-9_-]+ " + SIGNAL_SUFFIX + "|" + SWITCH_PATTERN + ")")
+LINE1_RE = re.compile("^(?:" + BATCH_PATTERN + "|" + re.escape(ALARM_PREFIX) + ")")   # only ever the first line: a
+                                                                                       # session line that happens to
+                                                                                       # start so is never a notice
 
 
 def notice_prefixes(label):
     return (f"{label} SPEND AT 90%", f"{label} SPEND UNMEASURED")
 
 
+def _segments(h):
+    """STATE line 1 as its notices: the batch spend and an alarm at its front (in any order: a hand edit too, audit
+    b108 c1), then ruling 87's switch line, joined by SEP. The batch and alarm notices never hold a '|' (their
+    writers refuse one), so each ends at the first SEP; the rest is the switch line; any other first line is one
+    notice."""
+    out, rest = [], h
+    while rest and (BATCH_RE.match(rest) or rest.startswith(ALARM_PREFIX)):
+        seg, _, rest = rest.partition(SEP)
+        out.append(seg)
+    return out + ([rest] if rest else [])
+
+
+def _place(h):
+    """The order of the leading block: line 1 (the batch spend, an alarm, the switches: ruling 108, ruling 106 (d),
+    ruling 87), then the cycles line (the 08:15 order: right under line 1, audit cyc c2), then every other notice."""
+    return (0 if BATCH_RE.match(h) else 1 if h.startswith(ALARM_PREFIX) else 2 if SWITCH_RE.match(h) else
+            3 if h.startswith(CYCLES_PREFIX + " TO ") else 4)
+
+
 def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
     """The STATE file's leading block of notice lines (NOTICE_RE): this writer's lines (mine) are replaced by `line`
     (None: removed; one of them kept where keep(h); a callable: line(this writer's lines) -> the line), every other
-    notice stays; ruling 87's switch line is always the first. Rewritten only when the text changes, under an flock.
-    Only a MISSING file starts empty: a STATE file that exists and cannot be read raises (OSError) and is never
-    rewritten from nothing (audit r87 C1-5: it would have lost the whole file)."""
+    notice stays. Line 1 is ONE physical line holding the batch spend, an alarm and ruling 87's switch line, in that
+    order (_segments / _place: ruling 108 puts the batch spend FIRST on it, ruling 87 every switch on it). Rewritten
+    only when the text changes, under an flock. Only a MISSING file starts empty: a STATE file that exists and cannot
+    be read raises (OSError) and is never rewritten from nothing (audit r87 C1-5: it would have lost the whole file)."""
     with open(lock_path, "a") as lk:
         fcntl.flock(lk, fcntl.LOCK_EX)
         try:
@@ -47,17 +74,17 @@ def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
         except FileNotFoundError:
             text = ""
         lines = text.split("\n") if text else []
-        head = []
+        head = [lines.pop(0)] if lines and (NOTICE_RE.match(lines[0]) or LINE1_RE.match(lines[0])) else []
         while lines and NOTICE_RE.match(lines[0]):
             head.append(lines.pop(0))
+        head = _segments(head[0]) + head[1:] if head else []
         if callable(line):
             line = line([h for h in head if mine(h)])
         kept = [h for h in head if mine(h) and keep(h)][:1]
         others = [h for h in head if not mine(h)]
-        block = ([line] if line else []) + kept + others
-        cyc = lambda h: h.startswith(CYCLES_PREFIX + " TO ")                 # noqa: E731 (the standing order's line
-        block = ([h for h in block if SWITCH_RE.match(h)] + [h for h in block if cyc(h)] +   # right under the switch
-                 [h for h in block if not SWITCH_RE.match(h) and not cyc(h)])                 # line: audit cyc c2)
+        block = sorted(([line] if line else []) + kept + others, key=_place)     # stable: each kind keeps its order
+        first = [h for h in block if _place(h) <= 2]
+        block = ([SEP.join(first)] if first else []) + [h for h in block if _place(h) > 2]
         new = "\n".join(block + lines)
         if new != text:
             tmp = f"{doc}.{os.getpid()}.{threading.get_ident()}.tmp"
@@ -66,9 +93,38 @@ def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
             os.replace(tmp, doc)
 
 
+def write_batch_notice(line, doc=None, notify_path=None):
+    """Ruling 108 (orchestrator 21:22 ET Nov 14): 'BATCH <n> ingest spend: $x ...', FIRST on STATE line 1 (the builder
+    books it in the batch's one ledger every hour); None removes it. One notice of line 1: never a '|' or a newline
+    (the split of line 1 relies on it)."""
+    if line is not None and (not BATCH_RE.match(line) or "\n" in line or "|" in line):
+        raise ValueError("not a batch line")
+    doc = doc or config.STATE_DOC
+    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
+    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
+    _rewrite_top(doc, lock_path, lambda h: bool(BATCH_RE.match(h)), line)
+    return line
+
+
+def write_alarm_notice(sentence, since, doc=None, notify_path=None):
+    """Ruling 106 (d): 'ALARM FOR PBX: <one sentence>. Waiting since <time ET>.' on STATE line 1, after the batch spend
+    (the integrator reads it and sends it; pp-ingest never sends one); sentence None removes it. One notice of line 1:
+    never a '|' or a newline."""
+    line = None
+    if sentence is not None:
+        line = f"{ALARM_PREFIX}{str(sentence).strip().rstrip('.')}. Waiting since {since}."
+        if not str(sentence).strip() or not since or "\n" in line or "|" in line:
+            raise ValueError("an alarm is one sentence and its time, on one line, without '|'")
+    doc = doc or config.STATE_DOC
+    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
+    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
+    _rewrite_top(doc, lock_path, lambda h: h.startswith(ALARM_PREFIX), line)
+    return line
+
+
 def write_cycles_notice(line, doc=None, notify_path=None):
     """The watcher's per-cycle line (cycles.compose: the orchestrator's 08:15 order of Nov 14) at the top of STATE,
-    after ruling 87's switch line; None removes it. Rewritten only when its text changes (_rewrite_top)."""
+    right under line 1; None removes it. Rewritten only when its text changes (_rewrite_top)."""
     if line is not None and ("\n" in line or not line.startswith(CYCLES_PREFIX + " TO ")):
         raise ValueError("not a cycles line")
     doc = doc or config.STATE_DOC
@@ -213,9 +269,9 @@ def write_purge_notice(why, since, doc=None, notify_path=None):
 
 def write_switch_head(head, doc=None, notify_path=None):
     """Ruling 87: one switch of the shared Heimdall signal, whoever made it ("HH:MM ET: SWITCHED TO PLAN B (...) |"),
-    prepended to the one physical line at the start of STATE line 1 that holds every earlier switch, newest first; that
-    line stays the first whatever other notice comes or goes. Under the notices' own lock (never a lock file beside the
-    STATE file)."""
+    prepended to the switch line that holds every earlier switch, newest first; that line stays on STATE line 1
+    (after the batch spend and an alarm: _rewrite_top) whatever other notice comes or goes. Under the notices' own
+    lock (never a lock file beside the STATE file)."""
     if not SWITCH_RE.match(head or ""):
         raise ValueError(f"not a switch head: {head!r}")
     doc = doc or config.STATE_DOC
diff --git a/tests/ingest/conftest.py b/tests/ingest/conftest.py
index 8e8a2d43..1dbe64f0 100644
--- a/tests/ingest/conftest.py
+++ b/tests/ingest/conftest.py
@@ -25,3 +25,17 @@ def _state_doc_in_tmp(tmp_path, monkeypatch):
     STATE_DOC still does (its monkeypatch comes later)."""
     from pipeline.ingest import config
     monkeypatch.setattr(config, "STATE_DOC", str(tmp_path / "STATE_of_this_test.md"))
+
+
+@pytest.fixture(autouse=True)
+def _batch_in_tmp(tmp_path_factory, monkeypatch):
+    """Ruling 108: every test reads its own batch file, never pipeline/ingest/batch.json (the real batch's window and
+    share would decide the paid route by the day the suite runs). The default is a batch around every clock the tests
+    use with a share no older test reaches (ruling 98's daily cap stays what they test); test_batch sets its own."""
+    import json
+    from pipeline.ingest import batch
+    p = tmp_path_factory.mktemp("batch") / "batch_of_this_test.json"    # beside the test's own files, not among them
+    p.write_text(json.dumps({"name": "BATCH 9", "start_et": "2026-01-01 00:00", "end_et": "2027-12-31 00:00",
+                             "share_usd": 1000.0, "share_of": "mining and checks"}))
+    monkeypatch.setattr(batch, "SPEC", str(p))
+    return p
diff --git a/tests/ingest/test_audit_driver.py b/tests/ingest/test_audit_driver.py
new file mode 100644
index 00000000..f81a2742
--- /dev/null
+++ b/tests/ingest/test_audit_driver.py
@@ -0,0 +1,149 @@
+"""Ruling 107 (2) on pp-ingest's audit driver (tests/ingest/xllm_audit.py), in force for batch 3 by ruling 108: the
+package is the diff, two Heimdall families review it, the audit is capped before any call, every review's cost is
+booked (an abandoned one at the model's own rate) to COST.json and to the ledger ruling 108's batch line reads. No test
+here reaches the network: urlopen and the back-end factory refuse unless a test hands its own fake."""
+import json
+import os
+import sys
+import urllib.request
+
+import pytest
+
+import xllm_audit as XA
+from pipeline.ingest import batch, config, providers
+
+
+@pytest.fixture(autouse=True)
+def no_network(monkeypatch):
+    def refuse(*a, **k):
+        raise AssertionError("a driver test reached the network")
+    monkeypatch.setattr(urllib.request, "urlopen", refuse)
+    monkeypatch.setattr(XA.providers, "make_backend", refuse)
+    monkeypatch.setattr(XA.providers, "Keyring", lambda path: None)        # the key file is never opened here
+
+
+def fake_git(monkeypatch, diff="diff --git a/pipeline/ingest/x.py b/pipeline/ingest/x.py\n+the new line\n",
+             numstat="10\t5\tpipeline/ingest/x.py\n"):
+    def out(cmd, cwd=None, text=None):
+        if cmd[:2] == ["git", "rev-parse"]:
+            return "abc1234\n"
+        if cmd[:3] == ["git", "diff", "--numstat"]:
+            return numstat
+        if cmd[:2] == ["git", "diff"]:
+            return diff
+        raise AssertionError(cmd)
+    monkeypatch.setattr(XA.subprocess, "check_output", out)
+
+
+def test_the_package_is_the_diff_and_its_context_never_the_whole_files(monkeypatch, tmp_path):
+    fake_git(monkeypatch)
+    ctx = tmp_path / "CONTEXT.md"
+    ctx.write_text("the orders this change answers")
+    pkg = XA.package("base0", str(ctx))
+    assert "+the new line" in pkg and "the orders this change answers" in pkg and "git diff base0" in pkg
+    assert "### File:" not in pkg and "WHAT THIS FEATURE DOES" not in pkg     # no whole file, no design document
+    assert XA.changed_lines("base0") == 15
+    fake_git(monkeypatch, diff=" \n")
+    with pytest.raises(SystemExit, match="nothing to review"):
+        XA.package("base0")
+
+
+def test_the_reviewers_are_two_heimdall_families_and_a_third_only_by_name():
+    assert XA.chosen(None) == (["heimdall_qwen", "heimdall_glm"], {})
+    assert XA.chosen({"heimdall_muse"})[0] == ["heimdall_muse"]
+    run, skipped = XA.chosen({"grok", "heimdall_glm"})                         # pp-ingest's freeze holds
+    assert run == ["heimdall_glm"] and "spend freeze" in skipped["grok"]
+    with pytest.raises(SystemExit):
+        XA.chosen({"nobody"})
+
+
+class Fake:
+    def __init__(self, rid):
+        self.rid = rid
+
+    def complete(self, prompt, schema, max_tokens):
+        if self.rid == "heimdall_glm":
+            raise providers.BackendError("timeout", "read timed out")          # abandoned: no cost reported
+        return providers.Reply("P0: none", "m", "p", 1.0, {"prompt_tokens": 9000, "completion_tokens": 900}, 0.002,
+                               "usage.cost", "stop")
+
+
+def run_main(monkeypatch, out, *extra, cycle=1):
+    monkeypatch.setattr(sys, "argv", ["xllm_audit.py", "--cycle", str(cycle), "--base", "base0", "--out", str(out)] +
+                        list(extra))
+    XA.main()
+
+
+def test_a_cycle_that_could_pass_the_cap_is_refused_before_any_call(monkeypatch, tmp_path):
+    fake_git(monkeypatch)                                                     # 15 changed lines: the $0.30 cap
+    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (1e-5, 30), "heimdall_glm": (1e-5, 30)})
+    (tmp_path / "audit").mkdir()
+    (tmp_path / "audit" / "COST.json").write_text(json.dumps({"total_usd": 0.29, "cycles": {}}))
+    with pytest.raises(SystemExit, match=r"REFUSED: this audit has spent \$0.2900 of its \$0.30 cap"):
+        run_main(monkeypatch, tmp_path / "audit" / "c2")                     # make_backend refuses: no call was made
+    assert not (tmp_path / "audit" / "c2" / "results.json").exists()
+
+
+def test_every_review_is_booked_and_the_batch_line_reads_the_same_dollars(monkeypatch, tmp_path):
+    fake_git(monkeypatch)
+    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (2e-7, 30), "heimdall_glm": (4e-8, 31)})
+    monkeypatch.setattr(XA.providers, "make_backend", lambda rid, cfg, kr: Fake(rid))
+    led = config.paths()["audit_spend"]
+    if os.path.exists(led):
+        os.remove(led)
+    run_main(monkeypatch, tmp_path / "audit" / "c1")
+    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
+    rev = cost["cycles"]["c1"]["reviews"]
+    assert rev["heimdall_qwen"] == {"usd": 0.002, "basis": "reported"}
+    assert rev["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)           # its own rate x the prompt the other
+    assert rev["heimdall_glm"]["basis"].startswith("abandoned: the model's own rate (31 reported reviews) x 9000")
+    assert cost["total_usd"] == pytest.approx(0.002 + 4e-8 * 9000) and cost["cap_usd"] == 0.30
+    usd, n, bad = batch.audit_spend(led, 0, 4e9)                              # ruling 108's line: the same dollars
+    assert (round(usd, 6), n, bad) == (round(cost["total_usd"], 6), 2, 0)
+    (tmp_path / "audit" / "C1_CONSENSUS.md").write_text("consensus")
+    run_main(monkeypatch, tmp_path / "audit" / "c2", "--c1", str(tmp_path / "audit" / "c1"), "--consensus",
+             str(tmp_path / "audit" / "C1_CONSENSUS.md"), cycle=2)          # cycle 2 adds to the same audit
+    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
+    assert set(cost["cycles"]) == {"c1", "c2"} and cost["total_usd"] == pytest.approx(2 * (0.002 + 4e-8 * 9000))
+    run_main(monkeypatch, tmp_path / "audit" / "c1", "--only", "heimdall_qwen")   # a leg run again costs again
+    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
+    assert len(cost["cycles"]["c1"]["reviews"]) == 3 and cost["total_usd"] == pytest.approx(
+        3 * 0.002 + 2 * 4e-8 * 9000)
+
+
+def test_an_abandoned_review_is_at_the_list_price_of_its_prompt_until_3_reported_reviews():
+    booked = XA.book({"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}},
+                     {"heimdall_glm": "timeout"}, {"heimdall_glm": {"kind": "timeout", "cost_usd": None}},
+                     {"heimdall_glm": "x" * 300}, {"heimdall_glm": (4e-8, 2)})
+    model = XA.REVIEWERS["heimdall_glm"]["model"]
+    price = [b["price"]["in_per_mtok"] for b in providers.load_config()["backends"].values() if b.get("model") == model]
+    assert booked["heimdall_glm"]["usd"] == pytest.approx(price[0] / 1e6 * 9000)
+    assert "the list price of the prompt (fewer than 3 reported reviews)" in booked["heimdall_glm"]["basis"]
+    failed = XA.book({}, {"heimdall_glm": "server"}, {"heimdall_glm": {"kind": "server", "cost_usd": 0.0004}}, {}, {})
+    assert failed["heimdall_glm"] == {"usd": 0.0004, "basis": "reported (failed: server)"}
+
+
+def test_the_caps_estimate_is_a_worst_case_the_whole_reply_budget_at_list_price():
+    """Audit b108 c1: qwen's reported $0.009 passed the doubled own-rate guess ($0.006: a long reply). The check now
+    holds each reviewer's prompt and whole reply budget at its model's list price."""
+    prompt = "x" * 96929
+    est = XA.estimate(lambda rid: prompt, None, {"heimdall_qwen": (9.6e-8, 33), "heimdall_glm": (4e-8, 31)})
+    floor = sum((len(prompt) / 3.0 * XA._price(rid)["in_per_mtok"] + XA.max_out(XA.REVIEWERS[rid]) *
+                 XA._price(rid)["out_per_mtok"]) / 1e6 for rid in XA.DEFAULT)
+    assert est >= floor and est >= 0.009 + 0.001                       # above the reported cycle 1 of b108
+
+
+def test_a_review_cut_off_in_flight_is_booked_and_a_quick_failure_says_it_is_not():
+    """b108 c1: glm's connection was dropped after 420 s and the record said 'failed before any cost'. A review cut
+    off after 30 s in flight with no answer is booked at the model's own rate; a quick or answered failure says it is
+    not booked."""
+    ok = {"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}}
+    cut = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": {"kind": "network", "cost_usd": None, "seconds": 420.3,
+                                                               "http_status": None}}, {}, {"heimdall_glm": (4e-8, 31)})
+    assert cut["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)
+    assert cut["heimdall_glm"]["basis"].startswith("cut off after 420.3 s in flight (network): the model's own rate")
+    for ec in ({"kind": "network", "seconds": 0.2, "http_status": None},
+               {"kind": "server", "seconds": 60.0, "http_status": 502}):
+        quick = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": dict(ec, cost_usd=None)}, {},
+                        {"heimdall_glm": (4e-8, 31)})
+        assert quick["heimdall_glm"]["usd"] == 0.0 and quick["heimdall_glm"]["basis"].endswith(": not booked")
diff --git a/tests/ingest/test_batch.py b/tests/ingest/test_batch.py
new file mode 100644
index 00000000..180dcccc
--- /dev/null
+++ b/tests/ingest/test_batch.py
@@ -0,0 +1,262 @@
+"""Ruling 108 (orchestrator 21:22 ET Nov 14), BATCH 3's money: pp-ingest's spend goes to the builder's one ledger every
+hour as 'BATCH <n> ingest spend: $x' FIRST on STATE line 1 (batch.py; spend.write_batch_notice). Line 1 also holds an
+alarm (ruling 106 (d)) and ruling 87's switches, in that order; ruling 98's paid route stays inside the batch's share;
+an abandoned call is booked at the model's own rate (ruling 107)."""
+import json
+import os
+from datetime import datetime
+
+import pytest
+
+from pipeline.ingest import batch, providers, spend
+from pipeline.ingest import queue as Q
+from test_paid_route import fakes, paid_cfg
+
+T0 = datetime(2026, 11, 14, 21, 10, tzinfo=batch.ET).timestamp()         # the batch's start
+RATE = 2e-6                                                                 # m-h's own dollars per prompt token
+CFG = {"backends": {"hb": {"vendor": "hv", "cost_from_usage": True, "price": {"in_per_mtok": 0.5}},
+                    "hn": {"vendor": "hv", "cost_from_usage": True, "price": {"in_per_mtok": 0.5}},
+                    "pg": {"vendor": "gv", "price": {"in_per_mtok": 5.0}}}}
+
+
+def write_batch(path, name="BATCH 3", start="2026-11-14 21:10", end="2026-11-15 21:10", share=1.0, raw=None):
+    with open(path, "w") as f:
+        f.write(raw if raw is not None else json.dumps({"name": name, "start_et": start, "end_et": end,
+                                                        "share_usd": share, "share_of": "mining and checks"}))
+    st = os.stat(path)
+    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000_000))   # a later write is a new file to load()
+
+
+@pytest.fixture
+def bq(tmp_path, monkeypatch):
+    spec = tmp_path / "batch.json"
+    write_batch(spec)
+    monkeypatch.setattr(batch, "SPEC", str(spec))
+    t = [T0 - 3600]
+    q = Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: t[0])
+    return q, t, spec
+
+
+def call(q, t, at, role="mine", backend="hb", model="m-h", kind="ok", cost=None, pt=1000):
+    t[0] = at
+    q.call({"role": role, "backend": backend, "model": model, "kind": kind,
+            "cost_usd": (RATE * pt if pt else None) if cost == "rate" else cost,
+            "usage": {"prompt_tokens": pt, "completion_tokens": 10} if pt else {}})
+
+
+def ledger(path, *recs):
+    with open(path, "w") as f:
+        for r in recs:
+            f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")
+    return str(path)
+
+
+# ── the figure ──
+
+def test_the_figure_runs_to_the_latest_whole_hour_by_use_with_an_abandoned_call_at_the_models_own_rate(bq, tmp_path):
+    q, t, _ = bq
+    for i in range(3):                                                     # history before the batch: m-h's rate
+        call(q, t, T0 - 600 + i, cost="rate", pt=1000)
+    call(q, t, T0 + 60, cost="rate", pt=600)                                # mining $0.0012
+    call(q, t, T0 + 61, role="hook", cost="rate", pt=1000)                  # hook pass $0.0020
+    call(q, t, T0 + 62, role="flagcheck", cost="rate", pt=250)              # flag checks $0.0005
+    call(q, t, T0 + 63, role="probe", cost="rate", pt=50)                   # probes $0.0001
+    call(q, t, T0 + 64, kind="cache", cost=0.0, pt=0)                       # a stored reply: free, not a call
+    call(q, t, T0 + 100, kind="timeout", cost=None, pt=None)                # abandoned: 900 prompt tokens (mine's
+    call(q, t, T0 + 3605, cost=0.03, pt=5000)                               # average on m-h) x RATE = $0.0018;
+    led = ledger(tmp_path / "audit_spend.jsonl",                            # the next hour's call waits for 23:10
+                 {"ts": T0 - 100, "usd": 1.0}, {"ts": T0 + 200, "usd": 0.003}, {"ts": T0 + 3700, "usd": 0.5})
+    assert batch.notice(q, T0 + 3599, CFG, led).startswith(
+        "BATCH 3 ingest spend: $0.0000 (21:10 ET Nov 14 to 21:10 ET: ")    # the figure moves only on the hour
+    line = batch.notice(q, T0 + 3610, CFG, led, quiet="NOTHING BITCOIN IN THE LAST 3 H")
+    assert line == ("BATCH 3 ingest spend: $0.0086 (21:10 ET Nov 14 to 22:10 ET: mining and checks $0.0056 of the "
+                    "$1.00 share (mining $0.0030, hook pass $0.0020, flag checks and calibration $0.0005, probes $0.0001), 5 model "
+                    "call(s); audits $0.0030, 1 review(s); vendor-reported; $0.0018 booked for 1 abandoned call(s) "
+                    "at the model's own rate); NOTHING BITCOIN IN THE LAST 3 H")
+    assert "|" not in line and "\n" not in line                            # one notice of line 1
+    left, what = batch.share_left(q, T0 + 3610, CFG)                       # the paid route counts to now: the
+    rate_now = (3 * 0.002 + 0.0012 + 0.002 + 0.0005 + 0.0001 + 0.03) / (3 * 1000 + 600 + 1000 + 250 + 50 + 5000)
+    spent = 0.0012 + 0.0020 + 0.0005 + 0.0001 + 0.03 + rate_now * (3 * 1000 + 600 + 5000) / 5   # the next hour's
+    assert abs(left - (1.0 - spent)) < 1e-9 and what == "BATCH 3's $1.00 share for mining and checks"   # call, at
+                                                                           # its own rate, moves the share, never the
+                                                                           # hour already out
+
+
+def test_an_abandoned_call_is_at_the_list_price_of_its_prompt_until_the_model_has_3_reported_calls(bq):
+    q, t, _ = bq
+    for i in range(2):
+        call(q, t, T0 + i, backend="hn", model="m-new", cost=0.01, pt=1000)
+    call(q, t, T0 + 10, backend="hn", model="m-new", kind="timeout", cost=None, pt=None)
+    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)
+    assert abs(w["abandoned"] - 0.5e-6 * 1000) < 1e-12 and w["abandoned_n"] == 1     # in_per_mtok 0.5 x 1000
+    call(q, t, T0 + 20, backend="hn", model="m-new", cost=0.01, pt=1000)              # a third reported call:
+    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)                                     # its own rate, 1e-5 a token
+    assert abs(w["abandoned"] - 1e-5 * 1000) < 1e-12
+
+
+def test_an_abandoned_call_with_no_prompt_size_known_is_said_never_read_as_nothing(bq, tmp_path):
+    q, t, _ = bq
+    call(q, t, T0 + 5, role="newrole", backend="hn", model="m-none", kind="timeout", cost=None, pt=None)
+    line = batch.notice(q, T0 + 3600, CFG, str(tmp_path / "none.jsonl"))
+    assert "1 abandoned call(s) NOT PRICED (no prompt size known)" in line
+
+
+def test_a_cost_priced_from_the_table_and_an_unreadable_audit_record_are_said_apart(bq, tmp_path):
+    q, t, _ = bq
+    call(q, t, T0 + 5, role="mine_paid", backend="pg", model="m-g", cost=0.02, pt=1000)
+    led = ledger(tmp_path / "a.jsonl", {"ts": T0 + 9, "usd": 0.001}, "{torn", {"ts": T0 + 9, "usd": float("nan")})
+    line = batch.notice(q, T0 + 3600, CFG, led)
+    assert "$0.0200 priced from the table (its vendor reports no cost)" in line
+    assert "audits $0.0010, 1 review(s)" in line and "2 audit cost record(s) UNREADABLE (not counted)" in line
+
+
+# ── the batch's file ──
+
+def test_a_closed_batch_says_so_and_outside_a_batch_the_paid_route_has_nothing_left(bq, tmp_path):
+    q, t, _ = bq
+    call(q, t, T0 + 5, cost=0.25, pt=1000)
+    end = T0 + 24 * 3600
+    line = batch.notice(q, end + 7200, CFG, str(tmp_path / "none.jsonl"))
+    assert line.startswith("BATCH 3 ingest spend: $0.2500 (CLOSED, 21:10 ET Nov 14 to 21:10 ET Nov 15: ")
+    assert line.endswith("; NO BATCH OPEN SINCE 21:10 ET Nov 15: the paid route spends nothing until the next batch's "
+                         "money is set")
+    assert batch.share_left(q, end + 1, CFG)[0] == 0.0 and batch.share_left(q, T0 - 1, CFG)[0] == 0.0
+    assert batch.share_left(q, T0 + 60, CFG)[0] == pytest.approx(0.75)
+
+
+def test_a_new_batch_is_read_without_a_restart_and_an_unreadable_one_fails_closed(bq, tmp_path):
+    q, t, spec = bq
+    assert batch.load()["name"] == "BATCH 3"
+    write_batch(spec, name="BATCH 4", start="2026-11-15 21:10", end="2026-11-16 21:10", share=0.5)
+    assert batch.load()["name"] == "BATCH 4" and batch.load()["share_usd"] == 0.5
+    for raw in ("{not json", json.dumps({"name": "BATCH 5", "start_et": "2026-11-15 21:10",
+                                         "end_et": "2026-11-15 21:10", "share_usd": 1.0})):    # no time between
+        write_batch(spec, raw=raw)
+        left, why = batch.share_left(q, T0 + 60, CFG)
+        assert left == 0.0 and "cannot be read" in why                    # no paid call starts
+        with pytest.raises((ValueError, KeyError)):
+            batch.notice(q, T0 + 60, CFG, str(tmp_path / "none.jsonl"))   # the service logs it; line 1 keeps its
+                                                                           # last figure
+
+
+@pytest.mark.parametrize("share", ["Infinity", "NaN", "-1"])
+def test_a_share_that_is_not_a_finite_amount_is_no_batch(bq, share):
+    q, t, spec = bq
+    write_batch(spec, raw='{"name": "BATCH 3", "start_et": "2026-11-14 21:10", "end_et": "2026-11-15 21:10", '
+                          f'"share_usd": {share}}}')
+    with pytest.raises(ValueError):
+        batch.load()
+    assert batch.share_left(q, T0 + 60, CFG)[0] == 0.0
+
+
+# ── STATE line 1 ──
+
+SWITCHES = ("10:18 ET: BACK TO HV-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW) | 10:12 ET: SWITCHED TO PLAN B (NO "
+            "ANSWER FOR 15 MINUTES) |")
+
+
+def test_line_1_holds_the_batch_spend_first_then_an_alarm_then_every_switch(tmp_path):
+    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
+    doc.write_text(SWITCHES + "\nPP-INGEST CYCLES TO 20:03 ET (x): y\n09:00 ET: the session line\n# body\n")
+    kw = {"doc": str(doc), "notify_path": str(notify)}
+    spend.write_batch_notice("BATCH 3 ingest spend: $0.0000 (a)", **kw)
+    assert doc.read_text().split("\n")[:3] == ["BATCH 3 ingest spend: $0.0000 (a) | " + SWITCHES,
+                                               "PP-INGEST CYCLES TO 20:03 ET (x): y", "09:00 ET: the session line"]
+    spend.write_alarm_notice("A real outage has stopped mining", "03:12 ET", **kw)
+    spend.write_switch_head("10:40 ET: SWITCHED TO PLAN B (NEW) |", **kw)              # a switch: on line 1 still
+    spend.write_cycles_notice("PP-INGEST CYCLES TO 20:13 ET (x): z", **kw)
+    spend.write_batch_notice("BATCH 3 ingest spend: $0.0123 (b)", **kw)                 # the next hour: replaced
+    lines = doc.read_text().split("\n")
+    assert lines[0] == ("BATCH 3 ingest spend: $0.0123 (b) | ALARM FOR PBX: A real outage has stopped mining. Waiting "
+                        "since 03:12 ET. | 10:40 ET: SWITCHED TO PLAN B (NEW) | " + SWITCHES)
+    assert lines[1:4] == ["PP-INGEST CYCLES TO 20:13 ET (x): z", "09:00 ET: the session line", "# body"]
+    spend.write_alarm_notice(None, None, **kw)
+    spend.write_batch_notice(None, **kw)
+    assert doc.read_text().split("\n")[0] == "10:40 ET: SWITCHED TO PLAN B (NEW) | " + SWITCHES
+
+
+def test_line_1_without_a_switch_and_a_bar_or_newline_in_its_notices_refused(tmp_path):
+    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
+    doc.write_text("09:00 ET: the session line\n")
+    kw = {"doc": str(doc), "notify_path": str(notify)}
+    spend.write_cycles_notice("PP-INGEST CYCLES TO 20:13 ET (x): z", **kw)
+    spend.write_batch_notice("BATCH 3 ingest spend: $0.0001 (c)", **kw)
+    assert doc.read_text() == ("BATCH 3 ingest spend: $0.0001 (c)\nPP-INGEST CYCLES TO 20:13 ET (x): z\n"
+                               "09:00 ET: the session line\n")
+    before = doc.read_text()
+    for bad in ("BATCH 3 ingest spend: $1 | 10:00 ET: SWITCHED TO PLAN B", "BATCH 3 ingest spend: $1\nx",
+                "SPEND $1"):
+        with pytest.raises(ValueError):
+            spend.write_batch_notice(bad, **kw)
+    for sentence, since in (("one | two", "03:00 ET"), ("one\ntwo", "03:00 ET"), ("", "03:00 ET"), ("x", "")):
+        with pytest.raises(ValueError):
+            spend.write_alarm_notice(sentence, since, **kw)
+    assert doc.read_text() == before
+
+
+# ── ruling 98's paid route inside the share ──
+
+def test_no_paid_call_starts_past_the_share_with_the_calls_in_flight_held_against_it():
+    left = [0.0035]
+    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=fakes(),
+                         sleep=lambda s: None, role_spend=lambda role, since: 0.0)
+    r.caps.share = lambda: (left[0], "BATCH 3's $1.00 share for mining and checks")
+    assert r.caps.reserve("mine_paid", 0.002, 1.0) is True                 # one call in flight holds $0.002
+    why = r.caps.reserve_why("mine_paid", 0.002, 1.0)                      # a second would pass $0.0035
+    assert why == ("BATCH 3's $1.00 share for mining and checks is spent ($0.0035 left, $0.0020 held by calls in "
+                   "flight; this call may cost $0.0020)")
+    r.caps.release("mine_paid", 0.002)
+    with pytest.raises(providers.AllBackendsFailed) as e:
+        left[0] = 0.001                                                    # less than one call's worst case
+        r.run("mine_paid", "p", None, lambda c: c, use_cache=False)
+    assert all(s == "skipped" and "share for mining and checks is spent" in w for _, s, w in e.value.tried)
+    left[0] = 1.0
+    assert r.run("mine_paid", "p", None, lambda c: c, use_cache=False).backend == "px"
+
+
+def test_a_share_that_cannot_be_read_lets_no_paid_call_start():
+    b = fakes()
+    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=b,
+                         sleep=lambda s: None, role_spend=lambda role, since: 0.0)
+    r.caps.share = lambda: 1 / 0
+    with pytest.raises(providers.AllBackendsFailed) as e:
+        r.run("mine_paid", "p", None, lambda c: c, use_cache=False)
+    assert all("the batch's share could not be read (ZeroDivisionError)" in w for _, _, w in e.value.tried)
+    assert b["px"].calls == [] and b["pg"].calls == []
+
+
+def test_a_session_line_that_starts_like_the_batch_line_is_never_taken_for_a_notice(tmp_path):
+    """Only line 1 can hold the batch spend or an alarm: a session line right under the notices that happens to start
+    with 'BATCH 3 ingest spend:' (pp-ingest wrote its figure there before the watcher could) stays as it is."""
+    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
+    session = "BATCH 3 ingest spend: $0.0000 (by hand) | 21:21 ET: the session line | # pp-ingest: STATE"
+    doc.write_text(SWITCHES + "\nPP-INGEST CYCLES TO 20:03 ET (x): y\n" + session + "\n# body\n")
+    spend.write_batch_notice("BATCH 3 ingest spend: $0.0042 (the watcher)", doc=str(doc), notify_path=str(notify))
+    assert doc.read_text().split("\n")[:4] == ["BATCH 3 ingest spend: $0.0042 (the watcher) | " + SWITCHES,
+                                               "PP-INGEST CYCLES TO 20:03 ET (x): y", session, "# body"]
+
+
+def test_a_call_cut_off_in_flight_is_booked_like_an_abandoned_one_and_an_answered_error_is_not(bq):
+    """The stricter reading of ruling 108's basis (ruling 106 (b)): a call that failed after 30 s or more in flight with
+    no answer (no HTTP status: a dropped connection) may have been billed, so it is booked at the model's own rate; an
+    error the vendor answered (a 502 with its body) and a refused connection are what they reported: nothing."""
+    q, t, _ = bq
+    for i in range(3):
+        call(q, t, T0 + i, cost="rate", pt=1000)
+    for kind, status, lat in (("network", None, 45.0), ("server", 502, 60.0), ("network", None, 0.01)):
+        t[0] += 1
+        q.call({"role": "mine", "backend": "hb", "model": "m-h", "kind": kind, "cost_usd": None,
+                "http_status": status, "latency_s": lat})
+    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)
+    assert w["abandoned_n"] == 1 and abs(w["abandoned"] - RATE * 1000) < 1e-12
+
+
+def test_a_hand_edited_line_1_with_the_alarm_before_the_batch_spend_still_splits_exactly(tmp_path):
+    """Audit b108 c1 (qwen): the batch spend and an alarm are taken from the front of line 1 in any order, so a hand
+    edit cannot fold the switch line into the batch notice (the next hour's figure would have replaced it)."""
+    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
+    doc.write_text("ALARM FOR PBX: x. Waiting since 03:00 ET. | BATCH 3 ingest spend: $0.1 (old) | " + SWITCHES +
+                   "\n# body\n")
+    spend.write_batch_notice("BATCH 3 ingest spend: $0.2 (new)", doc=str(doc), notify_path=str(notify))
+    assert doc.read_text().split("\n")[0] == ("BATCH 3 ingest spend: $0.2 (new) | ALARM FOR PBX: x. Waiting since "
+                                              "03:00 ET. | " + SWITCHES)
diff --git a/tests/ingest/test_cycles.py b/tests/ingest/test_cycles.py
index bbbb0f6e..83906dbf 100644
--- a/tests/ingest/test_cycles.py
+++ b/tests/ingest/test_cycles.py
@@ -218,3 +218,19 @@ def test_no_test_writes_the_real_state_file():
     """conftest redirects config.STATE_DOC for every test (the health loop now writes the cycles line)."""
     real = os.path.join(config.REPO, "docs", "audits", "parallel", "pp-ingest_STATE.md")
     assert os.path.realpath(config.STATE_DOC) != os.path.realpath(real)
+
+
+def test_the_quiet_head_goes_to_line_1_only_when_a_cycle_ran_and_found_nothing_bitcoin(tmp_path):
+    """Ruling 108's batch line carries the 3-hour note's head (the orchestrator's 21:22 order: Sunday, said on line
+    1); nothing is said when no cycle ran (nothing measured is never quiet) or when a window had Bitcoin."""
+    q, t = queue(tmp_path)
+    assert cycles.quiet_head(q, T) == ""
+    a, b = H.vid("a"), H.vid("b")
+    cycle(q, t, [(a, Q.DISCOVERED), (b, Q.SHORT)])
+    mined(q, a, T - 60, T + 1, T + 20, 0, 2, 2)
+    assert cycles.quiet_head(q, T + 30) == "NOTHING BITCOIN IN THE LAST 3 H"
+    c = H.vid("c")
+    cycle(q, t, [(c, Q.DISCOVERED)])
+    assert cycles.quiet_head(q, T + 40) == "NOTHING BITCOIN AMONG THE 1 MINED IN THE LAST 3 H (1 NOT MINED YET)"
+    mined(q, c, T - 60, T + 5, T + 50, 3, 2, 0)
+    assert cycles.quiet_head(q, T + 60) == ""
diff --git a/tests/ingest/test_paid_route.py b/tests/ingest/test_paid_route.py
index b99e05a8..65b84c56 100644
--- a/tests/ingest/test_paid_route.py
+++ b/tests/ingest/test_paid_route.py
@@ -138,7 +138,8 @@ def test_the_paid_route_opens_after_20_minutes_down_says_its_cap_once_and_closes
     assert hs.paid_open is True and s.q.kv_get("paid_route")["open"] is True
     assert doc.read_text().startswith(
         "02:20 ET: MINER ON THE PAID ROUTE (PX, THEN PG: NO HV ANSWER FOR 20 MINUTES, SINCE 2026-11-14T07:00:00Z; NEW "
-        "UPLOADS OF THE LAST 6 H ONLY, CONVERSATIONS FIRST; CAP $0.01 A DAY, ET) | 02:15 ET: SWITCHED TO PLAN B")
+        "UPLOADS OF THE LAST 6 H ONLY, CONVERSATIONS FIRST; CAP $0.01 A DAY, ET, INSIDE BATCH 9'S $1000.00 SHARE FOR "
+        "MINING AND CHECKS ($1000.00 LEFT)) | 02:15 ET: SWITCHED TO PLAN B")       # ruling 108: the share it is in
     good = (tmp / "HH.json").read_text()
     (tmp / "HH.json").write_text("{not json")                         # a signal not read: no spend, the route kept
     t[0] += 5
@@ -301,3 +302,34 @@ def test_the_cap_is_said_when_no_back_end_of_the_route_can_start_a_call_and_befo
     assert heads.startswith("02:00 ET: MINER OFF THE PAID ROUTE") and \
         "| 02:00 ET: MINER PAID ROUTE CAP REACHED ($0.01 OF $0.01 TODAY, ET): QUEUE AND WAIT |" in heads
     assert s.hsig.paid_open is False
+
+
+def test_the_route_says_once_when_the_batchs_share_stops_it_and_no_paid_call_starts(paid):
+    """Ruling 108: the paid route stays inside the batch's share for mining and checks (pp-ingest's $1.00 of $8.00):
+    when no call fits, line 1 says so once per share and the videos queue and wait; the opening says the share."""
+    from pipeline.ingest import batch
+    with open(batch.SPEC, "w") as f:
+        json.dump({"name": "BATCH 4", "start_et": "2026-11-14 00:00", "end_et": "2026-11-15 00:00",
+                   "share_usd": 0.0}, f)
+    make, t, doc, tmp, msgs = paid
+    s, b = make(probe_fn=lambda p: BackendError("network", "down"))
+    hs = s.hsig
+    hs.noted({"role": "mine", "backend": "hv1", "kind": "timeout"})
+    hs.tick(wait=True)
+    t[0] = T0 + 15 * 60
+    hs.noted({"role": "mine", "backend": "hv1", "kind": "timeout"})
+    hs.tick(wait=True)
+    t[0] = T0 + 20 * 60
+    hs.tick(wait=True)
+    assert hs.paid_open is True
+    head = doc.read_text().split("\n")[0]
+    assert head.startswith("02:20 ET: MINER PAID ROUTE CAP REACHED (BATCH 4'S $0.00 SHARE FOR MINING AND CHECKS: "
+                           "$0.00 LEFT): QUEUE AND WAIT | 02:20 ET: MINER ON THE PAID ROUTE (")
+    assert "CAP $0.01 A DAY, ET, INSIDE BATCH 4'S $0.00 SHARE FOR MINING AND CHECKS ($0.00 LEFT))" in head
+    with pytest.raises(providers.AllBackendsFailed) as e:
+        s.router.run("mine_paid", "p", None, lambda c: c, use_cache=False)
+    assert all("share for mining and checks is spent" in w for _, _, w in e.value.tried)
+    assert b["px"].calls == [] and b["pg"].calls == []
+    t[0] += 120
+    hs.tick(wait=True)
+    assert doc.read_text().count("SHARE FOR MINING AND CHECKS: $0.00 LEFT") == 1          # said once per share
diff --git a/tests/ingest/test_service.py b/tests/ingest/test_service.py
index d9fad4c2..5187ca92 100644
--- a/tests/ingest/test_service.py
+++ b/tests/ingest/test_service.py
@@ -390,8 +390,9 @@ def test_the_health_loop_writes_the_cycles_line_and_a_failure_never_stops_it(svc
     run_once(s)
     s.health_once()
     text = open(config.STATE_DOC).read()
-    assert text.startswith("PP-INGEST CYCLES TO ") and f"{vids[0]} Test Channel \"" in text.split("\n")[0] and \
-        ": mined yes " in text.split("\n")[0]
+    line1, line2 = text.split("\n")[:2]                    # ruling 108: line 1 is the batch spend, the cycles line next
+    assert line1.startswith("BATCH 9 ingest spend: $") and line2.startswith("PP-INGEST CYCLES TO ") and \
+        f"{vids[0]} Test Channel \"" in line2 and ": mined yes " in line2
     msgs = []
     s.log = msgs.append
     monkeypatch.setattr(service.cycles, "compose", lambda *a, **k: 1 / 0)
@@ -904,3 +905,31 @@ def test_the_hook_rerun_is_idempotent_per_question_version(svc, monkeypatch):
     while s.hook_once(wait=True):
         pass
     assert s.q.video(vids[0])["hook_version"] == mine.HOOK_PROMPT_VERSION
+
+
+def test_the_health_loop_writes_the_batch_spend_first_on_line_1_and_a_failure_never_stops_it(svc, monkeypatch):
+    """Ruling 108: the watcher's own spend in the batch, to the batch's latest whole hour, first on STATE line 1 (the
+    test's own file: conftest), every call it made counted; a failure is logged once and line 1 keeps its figure."""
+    from datetime import datetime
+    from pipeline.ingest import batch
+    start = (int(__import__("time").time()) // 60 - 1) * 60                     # a minute boundary before the calls
+    with open(batch.SPEC, "w") as f:
+        json.dump({"name": "BATCH 7", "start_et": datetime.fromtimestamp(start, batch.ET).strftime("%Y-%m-%d %H:%M"),
+                   "end_et": "2027-12-31 00:00", "share_usd": 1.0}, f)
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
+    run_once(s)
+    spent = s.q.rows("SELECT SUM(COALESCE(cost_usd, 0)) AS u, COUNT(*) AS n FROM calls WHERE kind != 'cache'")[0]
+    assert spent["n"] > 0
+    s.clock = lambda: start + 3600 + 30                                          # the batch's first hour is out
+    s.health_once()
+    line1 = open(config.STATE_DOC).read().split("\n")[0]
+    assert line1.startswith(f"BATCH 7 ingest spend: ${spent['u']:.4f} (") and \
+        f"mining and checks ${spent['u']:.4f} of the $1.00 share" in line1 and f"{spent['n']} model call(s)" in line1
+    msgs = []
+    s.log = msgs.append
+    monkeypatch.setattr(service.batch, "notice", lambda *a, **k: 1 / 0)
+    s.health_once()
+    s.health_once()
+    assert [m for m in msgs if "batch line" in m] == [
+        "ruling 108: the batch line could not be written: ZeroDivisionError: division by zero"]
+    assert open(config.STATE_DOC).read().split("\n")[0] == line1
diff --git a/tests/ingest/xllm_audit.py b/tests/ingest/xllm_audit.py
index 49312365..46a0f96a 100644
--- a/tests/ingest/xllm_audit.py
+++ b/tests/ingest/xllm_audit.py
@@ -11,13 +11,24 @@ name inside code (pipeline.ingest.providers.Keyring) and never printed. The cons
 (C1_CONSENSUS.md / C2_CONSENSUS.md): consensus = the same file, function and root cause from >= 2 reviewers, or one
 reviewer's finding verified against the code; refutations are recorded with evidence.
 
-  python3 tests/ingest/xllm_audit.py --cycle 1 --out docs/audits/parallel/pp-ingest_audit/c1
-  python3 tests/ingest/xllm_audit.py --cycle 2 --c1 docs/audits/parallel/pp-ingest_audit/c1 \
-      --consensus docs/audits/parallel/pp-ingest_audit/C1_CONSENSUS.md --out docs/audits/parallel/pp-ingest_audit/c2
+  A=docs/audits/parallel/pp-ingest_audit/<change>
+  python3 tests/ingest/xllm_audit.py --cycle 1 --base <rev> --context $A/CONTEXT.md --out $A/c1
+  python3 tests/ingest/xllm_audit.py --cycle 2 --base <rev> --context $A/CONTEXT.md --c1 $A/c1 \
+      --consensus $A/C1_CONSENSUS.md --out $A/c2
 
 SPEND FREEZE (orchestrator 05:30 ET Nov 12): a reviewer whose vendor is in providers.json spend_freeze is never called
-(skipped, and said so); the Heimdall-served reviewers of other model families stand in. --base / --context add the
-diff of a later change and its orders to the package (the change is reviewed in full files plus its diff).
+(skipped, and said so); the Heimdall-served reviewers of other model families stand in.
+
+RULING 107 (2) (orchestrator 20:20 ET Nov 14; in force for batch 3 by ruling 108, 21:22): the package is the DIFF (git
+diff --base of the watcher's code and its tests; a new file needs `git add -N`), the laws and the change's own context
+(--context), never the whole files; the reviewers are two Heimdall families, qwen + glm (DEFAULT); a third family
+(THIRD, by --only) only when the two disagree on a P0 / P1 or one of them is down (the paid frontier reviewers stay
+out under pp-ingest's freeze). The audit is capped, vendor-reported, both cycles together: $0.30 for a change under 60
+changed lines, else $1.00; a cycle that could pass the cap is refused before any call. Each review's cost goes to
+COST.json in the audit folder and, one record per review, to the watcher's audit ledger (config.paths()
+["audit_spend"]: ruling 108's batch line counts it); an abandoned review (a timeout, no cost reported) is booked at
+the model's own rate (ruling 107: its reported dollars per prompt token in this audit history x the prompt; the list
+price of the prompt until it has 3 reported reviews).
 """
 import argparse
 import json
@@ -31,17 +42,9 @@ REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)
 sys.path.insert(0, REPO)
 sys.path.insert(0, os.path.join(REPO, "utils"))
 
-from pipeline.ingest import providers  # noqa: E402
+from pipeline.ingest import config, providers  # noqa: E402
 
 ENV = "/home/ultron/protocol_pulse/.env"
-BASE_REV = "c1451047"
-FILES = ["pipeline/ingest/__init__.py", "pipeline/ingest/config.py", "pipeline/ingest/contract.py",
-         "pipeline/ingest/providers.py", "pipeline/ingest/providers.json", "pipeline/ingest/spend.py",
-         "pipeline/ingest/queue.py", "pipeline/ingest/watch.py", "pipeline/ingest/fetch.py", "pipeline/ingest/mine.py",
-         "pipeline/ingest/ledger.py", "pipeline/ingest/coverage.py", "pipeline/ingest/stats.py",
-         "pipeline/ingest/service.py", "pipeline/ingest/ab.py", "pipeline/ingest/flagcheck.py",
-         "pipeline/ingest/purge.py", "pipeline/ingest/purge.json", "pipeline/ingest/downsignal.py",
-         "tools/ingest_watch.py"]
 HEIMDALL = {"kind": "openai_compat", "vendor": "heimdall", "base_url": "https://api-staging.heimdallm.com/api/v1",
             "key_env_prefix": "HEIMDALL_API_KEY", "timeout_s": 900, "cost_from_usage": True}
 REVIEWERS = {
@@ -66,6 +69,15 @@ REVIEWERS = {
    # excluded by the order (incoherent on long prompts / always 429)
 
 
+DEFAULT = ("heimdall_qwen", "heimdall_glm")       # ruling 107 (2): two Heimdall families
+THIRD = "heimdall_muse"                           # the third family: a P0 / P1 disagreement, or one of the two down
+DIFF_PATHS = ["pipeline/ingest", "tools/ingest_watch.py", "tests/ingest"]
+SMALL_LINES, SMALL_CAP, BIG_CAP = 60, 0.30, 1.00  # ruling 107 (2): per audit, both cycles, vendor-reported
+MIN_REPORTED = 3                                  # ruling 107: list price until a model has 3 reported reviews
+CUT_S = 30.0                                      # a review cut off after this long in flight may have been billed
+AUDIT_ROOT = os.path.join(REPO, "docs/audits/parallel/pp-ingest_audit")
+
+
 def frozen():
     return providers.frozen_vendors(providers.load_config())
 
@@ -93,51 +105,40 @@ LAWS = """Standing order (PBX 02:30 / orchestrator 02:45 ET 2026-11-12) and laws
   Google by the builder's assumption) are never called by any role; the watcher's mine chain is Heimdall then the
   local interface ONLY; if both are down the videos queue and are mined later, never on a paid frontier model; Heimdall
   mining continues; the 90 % tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of STATE), never a halt.
-- The integrator's merge audit (cycle 1) BLOCKING findings B1-B4 and its non-blocking list are in the change context
-  below; the change must answer each without weakening any check.
 Only report issues you can verify from the code provided. Do not speculate. Cite file:line."""
 
 
-def package(files, extra="", base=None, context=None):
+def changed_lines(base):
+    """Added + deleted lines of the change (git diff --numstat; a binary file counts 0)."""
+    out = subprocess.check_output(["git", "diff", "--numstat", base, "--"] + DIFF_PATHS, cwd=REPO, text=True)
+    return sum(int(a) + int(d) for a, d, _ in (l.split("\t", 2) for l in out.splitlines() if l.strip())
+               if a.isdigit() and d.isdigit())
+
+
+def package(base, context=None):
+    """Ruling 107 (2): the laws, the change's own context and its diff (never the whole files)."""
     import cross_llm_audit as tool
     head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
-    parts = []
-    for f in files:
-        txt = open(os.path.join(REPO, f)).read()
-        lines = txt.split("\n")
-        parts.append(f"\n### File: {f} ({len(lines)} lines)\n```\n" +
-                     "\n".join(f"{i + 1:4d} | {l}" for i, l in enumerate(lines)) + "\n```")
-    tests = subprocess.run([sys.executable, "-m", "pytest", "tests/ingest", "--collect-only", "-q"], cwd=REPO,
-                           capture_output=True, text=True).stdout
-    design = open(os.path.join(REPO, "docs/audits/INGEST_DESIGN.md")).read()
-    if base:
-        diff = subprocess.check_output(["git", "diff", base, "--", "pipeline/ingest", "tools/ingest_watch.py"],
-                                       cwd=REPO, text=True)
-        extra = (extra + f"\n\n## THE CHANGE UNDER REVIEW: git diff {base} (working tree)\n"
-                 + (open(context).read() if context else "") + f"\n```diff\n{diff}\n```\n")
-    return f"""# PROTOCOL PULSE — CODE AUDIT PACKAGE
-# Feature: pp-ingest (continuous ingest + first-pass moment mining)
-# Branch: pp-ingest (base {BASE_REV}, working tree at {head} + the uncommitted files below = the ACTUAL diff: all new)
-# Purpose: Pre-merge quality gate. Several independent AI models review this same code.
-
-## WHAT THIS FEATURE DOES
-{design}
-
-## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
-{LAWS}
+    diff = subprocess.check_output(["git", "diff", base, "--"] + DIFF_PATHS, cwd=REPO, text=True)
+    if not diff.strip():
+        raise SystemExit(f"nothing to review: git diff {base} is empty (a new file needs git add -N)")
+    ctx = open(context).read() if context else ""
+    return f"""# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
+# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at {head}
+# The change under review: git diff {base} (working tree) of {", ".join(DIFF_PATHS)}
 
-## TECHNOLOGY STACK
-- Python 3.10, stdlib sqlite3 / urllib / threads; yt-dlp subprocesses; the Anthropic SDK and google-genai for two
-  back-ends; no GPU. Runs as one long-lived process (tmux), not cron.
+## GOVERNING LAWS (this code MUST comply with every law below: flag any violation)
+{LAWS}
 
-## THE CODE (every new file of the diff; tests are listed by name after the code)
-{''.join(parts)}
+## THE CHANGE UNDER REVIEW: its orders and design
+{ctx}
 
-### Test inventory (tests/ingest, {tests.strip().splitlines()[-1] if tests.strip() else 'not collected'})
+```diff
+{diff}
 ```
-{tests.strip()}
-```
-{extra}
+
+You see the diff, not the whole files: when a finding needs code outside it, say which function you need instead of
+guessing.
 
 ---
 
@@ -145,11 +146,124 @@ def package(files, extra="", base=None, context=None):
 """
 
 
+def _rates(root=AUDIT_ROOT):
+    """Each reviewer's own rate (ruling 107): its reported dollars per prompt token over every review in the audit
+    history -> {reviewer: (dollars per token, reviews)}."""
+    import glob
+    agg = {}
+    for path in glob.glob(os.path.join(root, "**", "results.json"), recursive=True):
+        try:
+            with open(path) as f:
+                res = json.load(f).get("results") or {}
+        except (OSError, ValueError):
+            continue
+        for rid, r in res.items():
+            pt = (r.get("usage") or {}).get("prompt_tokens")
+            if isinstance(r.get("cost_usd"), (int, float)) and r["cost_usd"] > 0 and isinstance(pt, int) and pt > 0:
+                c, p, n = agg.get(rid, (0.0, 0, 0))
+                agg[rid] = (c + r["cost_usd"], p + pt, n + 1)
+    return {rid: (c / p, n) for rid, (c, p, n) in agg.items()}
+
+
+def _rate(rid, rates):
+    """(dollars per prompt token, basis): the reviewer's own once it has MIN_REPORTED reviews, else the list price of
+    the prompt (providers.json, the same model), else None (unpriced)."""
+    own = rates.get(rid)
+    if own and own[1] >= MIN_REPORTED:
+        return own[0], f"the model's own rate ({own[1]} reported reviews)"
+    model = REVIEWERS[rid].get("model")
+    for b in providers.load_config()["backends"].values():
+        if b.get("model") == model and (b.get("price") or {}).get("in_per_mtok") is not None:
+            return float(b["price"]["in_per_mtok"]) / 1e6, "the list price of the prompt (fewer than 3 reported reviews)"
+    return None, "UNPRICED (no rate known)"
+
+
+def book(results, errors, error_costs, prompts, rates):
+    """Every review's cost: reported (the reply's or the failed call's own figure), or, for an abandoned review (a
+    timeout, or a review cut off after CUT_S in flight with no answer: a dropped connection; the stricter reading,
+    ruling 106 (b)), at the model's own rate x its prompt (the answered reviews' prompt tokens, else 3 characters a
+    token); a quick failure or an error the vendor answered with no cost is not booked, and says so ->
+    {reviewer: {usd, basis}}. (b108 c1: glm's connection dropped after 420 s was first written 'failed before any
+    cost'.)"""
+    answered = [((r.get("usage") or {}).get("prompt_tokens") or 0) for r in results.values()]
+    answered = [t for t in answered if t > 0]
+    out = {}
+    for rid, r in results.items():
+        out[rid] = {"usd": float(r.get("cost_usd") or 0.0), "basis": "reported"}
+    for rid in errors:
+        ec = error_costs.get(rid) or {}
+        if isinstance(ec.get("cost_usd"), (int, float)):
+            out[rid] = {"usd": float(ec["cost_usd"]), "basis": f"reported (failed: {ec.get('kind')})"}
+        elif ec.get("kind") == "timeout" or (ec.get("http_status") is None and
+                                             float(ec.get("seconds") or 0.0) >= CUT_S):
+            rate, basis = _rate(rid, rates)
+            tokens = sum(answered) / len(answered) if answered else len(prompts.get(rid) or "") / 3.0
+            what = ("abandoned" if ec.get("kind") == "timeout" else
+                    f"cut off after {ec.get('seconds')} s in flight ({ec.get('kind')})")
+            out[rid] = ({"usd": rate * tokens, "basis": f"{what}: {basis} x {int(tokens)} prompt tokens"}
+                        if rate is not None else {"usd": 0.0, "basis": f"{what}: {basis}"})
+        else:
+            out[rid] = {"usd": 0.0, "basis": f"failed in {ec.get('seconds')} s with no cost reported "
+                                             f"({ec.get('kind') or 'no reply'}, status {ec.get('http_status')}): "
+                                             "not booked"}
+    return out
+
+
+def cost_path(out):
+    return os.path.join(os.path.dirname(os.path.abspath(out)), "COST.json")
+
+
+def cap_check(out, cap, estimate):
+    """The audit's spend so far (COST.json beside the cycle folders); raises SystemExit when the next cycle's estimate
+    could pass the cap (ruling 107 (2)): nothing is sent."""
+    spent = 0.0
+    if os.path.exists(cost_path(out)):
+        with open(cost_path(out)) as f:
+            spent = float(json.load(f).get("total_usd") or 0.0)
+    if spent + estimate > cap:
+        raise SystemExit(f"REFUSED: this audit has spent ${spent:.4f} of its ${cap:.2f} cap (ruling 107 (2)) and the "
+                         f"next cycle may cost ${estimate:.4f}: nothing sent")
+    return spent
+
+
+def record(out, cycle, booked, cap, lines, ledger=None, now=None):
+    """COST.json (the audit folder's cycles, each review's cost and basis, the total) and one ledger record per review
+    (ruling 108's batch line reads the ledger)."""
+    now = time.time() if now is None else now
+    path = cost_path(out)
+    rec = {"cap_usd": cap, "changed_lines": lines, "cycles": {}}
+    if os.path.exists(path):
+        with open(path) as f:
+            rec = json.load(f)
+    cyc = rec["cycles"].setdefault(f"c{cycle}", {"reviews": {}})
+    for rid, b in booked.items():
+        key, k = rid, 1
+        while key in cyc["reviews"]:                  # a leg run again costs again: kept beside the first
+            k += 1
+            key = f"{rid} (run {k})"
+        cyc["reviews"][key] = b
+    cyc["usd"] = round(sum(b["usd"] for b in cyc["reviews"].values()), 6)
+    rec["total_usd"] = round(sum(c["usd"] for c in rec["cycles"].values()), 6)
+    rec["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
+    tmp = f"{path}.{os.getpid()}.tmp"              # whole or not at all (audit b108 c1, qwen): a torn COST.json would
+    with open(tmp, "w") as f:                      # stop every later cycle of the audit (cap_check cannot read it)
+        json.dump(rec, f, indent=1)
+    os.replace(tmp, path)
+    ledger = ledger or config.paths()["audit_spend"]
+    os.makedirs(os.path.dirname(ledger), exist_ok=True)
+    audit = os.path.relpath(os.path.dirname(os.path.abspath(out)), REPO)
+    with open(ledger, "a") as f:
+        for rid, b in booked.items():
+            f.write(json.dumps({"ts": now, "at": rec["updated_utc"], "audit": audit, "cycle": cycle,
+                                "reviewer": rid, "usd": round(b["usd"], 6), "basis": b["basis"]}) + "\n")
+    return rec
+
+
 def call(rid, cfg, prompt, results, errors, kr, error_costs=None):
     b = providers.make_backend(rid, dict(cfg, enabled=True), kr)
     t0 = time.time()
     try:
-        r = b.complete(prompt, None, max(16000, int(cfg.get("max_tokens_floor", 0))))
+        r = b.complete(prompt, None, max_out(cfg))
         results[rid] = {"model": r.model, "content": r.content, "usage": r.usage, "cost_usd": r.cost_usd,
                         "seconds": round(time.time() - t0, 1), "finish_reason": r.finish_reason}
         print(f"  [{rid}] done {time.time() - t0:.0f} s, {len(r.content)} chars, ${r.cost_usd:.3f}", flush=True)
@@ -157,21 +271,32 @@ def call(rid, cfg, prompt, results, errors, kr, error_costs=None):
         errors[rid] = f"{type(e).__name__}: {e}"[:500]
         if error_costs is not None and isinstance(e, providers.BackendError):     # a failed call is spend too
             error_costs[rid] = {"usage": e.usage, "cost_usd": e.cost_usd, "kind": e.kind,
-                                "seconds": round(time.time() - t0, 1)}
+                                "http_status": e.http_status, "seconds": round(time.time() - t0, 1)}
         print(f"  [{rid}] ERROR {errors[rid][:200]}", flush=True)
 
 
+def chosen(only=None):
+    """The reviewers of this cycle: --only, else ruling 107 (2)'s two families; a frozen vendor's are skipped."""
+    want = set(only) if only else set(DEFAULT)
+    fz = frozen()
+    skipped = {rid: f"spend freeze: vendor {REVIEWERS[rid]['vendor']!r}" for rid in want
+               if rid in REVIEWERS and REVIEWERS[rid]["vendor"] in fz}
+    unknown = sorted(want - set(REVIEWERS))
+    if unknown:
+        raise SystemExit(f"unknown reviewer(s) {unknown}")
+    return [rid for rid in REVIEWERS if rid in want and rid not in skipped], skipped
+
+
 def fire(prompt_for, out, only=None):
     kr = providers.Keyring(ENV)
     results, errors = {}, {}
-    fz = frozen()
-    skipped = {rid: f"spend freeze: vendor {cfg['vendor']!r}" for rid, cfg in REVIEWERS.items()
-               if cfg["vendor"] in fz and (not only or rid in only)}
+    run, skipped = chosen(only)
     for rid, why in skipped.items():
         print(f"  [{rid}] SKIPPED ({why})", flush=True)
     error_costs = {}
-    th = [threading.Thread(target=call, args=(rid, cfg, prompt_for(rid), results, errors, kr, error_costs))
-          for rid, cfg in REVIEWERS.items() if (not only or rid in only) and rid not in skipped]
+    prompts = {rid: prompt_for(rid) for rid in run}
+    th = [threading.Thread(target=call, args=(rid, REVIEWERS[rid], prompts[rid], results, errors, kr, error_costs))
+          for rid in run]
     for t in th:
         t.start()
     for t in th:
@@ -200,7 +325,41 @@ def fire(prompt_for, out, only=None):
     rec["skipped"].update(skipped)
     with open(path, "w") as f:
         json.dump(rec, f, indent=1)
-    return results, errors
+    return results, errors, error_costs, prompts
+
+
+def max_out(cfg):
+    """A review's reply budget in tokens."""
+    return max(16000, int(cfg.get("max_tokens_floor", 0)))
+
+
+def _price(rid):
+    """The list price of the reviewer's model (providers.json, the same model): {in_per_mtok, out_per_mtok} or None."""
+    model = REVIEWERS[rid].get("model")
+    for b in providers.load_config()["backends"].values():
+        p = b.get("price") or {}
+        if b.get("model") == model and p.get("in_per_mtok") is not None and p.get("out_per_mtok") is not None:
+            return p
+    return None
+
+
+def estimate(prompt_for, only, rates):
+    """The most the next cycle can cost, for the cap's check before any call: each reviewer's prompt (3 characters a
+    token, over-counting code) and its whole reply budget at its model's list price, with half again for the
+    tokenizer; a reviewer without a list price at 4 x its own rate (else the highest rate known) on the prompt and the
+    reply budget. (Cycle 1 of b108: qwen's reported $0.009 passed the doubled own-rate guess of $0.006: a long reply.)"""
+    run, _ = chosen(only)
+    top = max([r for r, _ in rates.values()] or [0.0])
+    total = 0.0
+    for rid in run:
+        tokens, out = len(prompt_for(rid)) / 3.0, max_out(REVIEWERS[rid])
+        p = _price(rid)
+        if p is not None:
+            total += 1.5 * (tokens * float(p["in_per_mtok"]) + out * float(p["out_per_mtok"])) / 1e6
+        else:
+            rate, _ = _rate(rid, rates)
+            total += 4.0 * (rate if rate is not None else top) * (tokens + out)
+    return total
 
 
 def main():
@@ -209,17 +368,19 @@ def main():
     ap.add_argument("--out", required=True)
     ap.add_argument("--c1")
     ap.add_argument("--consensus")
-    ap.add_argument("--only", help="comma-separated reviewer ids (re-run failed legs)")
-    ap.add_argument("--base", help="review the change since this revision: its diff is added to the package")
-    ap.add_argument("--context", help="a text file with the orders / findings the change answers")
+    ap.add_argument("--only", help="comma-separated reviewer ids (a failed leg again, or the third family)")
+    ap.add_argument("--base", required=True, help="the change since this revision: its diff is the package")
+    ap.add_argument("--context", help="a text file with the orders / design the change answers")
     a = ap.parse_args()
     only = set(a.only.split(",")) if a.only else None
+    lines = changed_lines(a.base)
+    cap = SMALL_CAP if lines < SMALL_LINES else BIG_CAP
+    pkg = package(a.base, a.context)
+    os.makedirs(a.out, exist_ok=True)
+    open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)
     if a.cycle == 1:
-        pkg = package(FILES, base=a.base, context=a.context)
-        os.makedirs(a.out, exist_ok=True)
-        open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)
-        print(f"package {len(pkg)} chars")
-        fire(lambda rid: pkg, a.out, only)
+        def prompt_for(rid):
+            return pkg
     else:
         import cross_llm_audit as tool
         c1 = {}
@@ -227,15 +388,20 @@ def main():
             if f.endswith(".md") and f != "PACKAGE.md":
                 c1[f[:-3]] = open(os.path.join(a.c1, f)).read()
         consensus = open(a.consensus).read()
-        pkg = package(FILES, base=a.base, context=a.context)
-        os.makedirs(a.out, exist_ok=True)
-        open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)
 
         def prompt_for(rid):
             p = tool.build_cycle2_prompt("pp-ingest", pkg, c1, consensus)
             mine = c1.get(rid)
             return p.replace("[See below — you wrote this]", (mine or "(you did not answer in cycle 1)")[:6000])
-        fire(prompt_for, a.out, only)
+    rates = _rates()
+    est = estimate(prompt_for, only, rates)
+    spent = cap_check(a.out, cap, est)
+    print(f"package {len(pkg)} chars; {lines} changed lines: cap ${cap:.2f}; spent ${spent:.4f}; this cycle at most "
+          f"${est:.4f} (list price, the whole reply budget)", flush=True)
+    results, errors, error_costs, prompts = fire(prompt_for, a.out, only)
+    rec = record(a.out, a.cycle, book(results, errors, error_costs, prompts, rates), cap, lines)
+    print(f"cycle {a.cycle}: ${rec['cycles'][f'c{a.cycle}']['usd']:.4f}; the audit ${rec['total_usd']:.4f} of its "
+          f"${cap:.2f} cap ({cost_path(a.out)})", flush=True)
 
 
 if __name__ == "__main__":

```

You see the diff, not the whole files: when a finding needs code outside it, say which function you need instead of
guessing.

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

