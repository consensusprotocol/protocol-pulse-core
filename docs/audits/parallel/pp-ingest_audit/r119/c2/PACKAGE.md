# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 87b3efeb
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
# r119: mined within 10 minutes of its transcript, Bitcoin channels first (the orchestrator's 13:05 ET ruling, Nov 16)

## The ruling (verbatim)
"ORCHESTRATOR RULING 13:05 ET Nov 16: your 12:45 question R13: YES. I have ordered the integrator to release the GPU0
lease between scoring calls (or let the pipeline's ingest use GPU1 when GPU0 is leased), builds first. Mine each video
within 10 minutes of its transcript, Bitcoin channels first. Longer term, design (do not build yet) a second caption
source that does not depend on this machine's YouTube quota, and say what the 429s correlate with."

## Where it stands (r118, live since 11:53 ET, 9125517f)
While YouTube refuses captions (HTTP 429 since 07:47 ET), a new upload's transcript is the main tree's own Whisper
record (pipeline/transcript_ingest.py, cron */30), which r118's fetch step takes (fetch.take_pipeline_transcript, read
only, every check, write-once) when the video is next tried. That next try is the video's own retry time: 10 min after
a caption 429, up to 30 min for a VOD without English captions (fetch._caption_retry_at), the gate's pause plus 5 min
for a probe the gate held back. So a record could land and wait up to 30 minutes before it was taken. The queue took due
videos newest first, whatever the channel.

## The change
1. fetch.pipeline_sweep(q, now): every video waiting on a transcript (probe_retry, captions_pending) inside its
   moments' life (config.EXPIRY_H, 12 h) whose next try is later and whose record is in the pipeline's store
   (fetch.pipeline_transcript: every r118 check) is due NOW; one queue event each. No YouTube request (a glob per
   waiting video, and a read of a record that is there). An id transcript_store refuses is skipped.
2. service.fetch_once runs the sweep before claiming due videos, at most every fetch.PIPELINE_SWEEP_S (60 s), and
   never while the yt-dlp gate is open (no probe can run then; the sweep runs once it shuts). The probe that follows is
   the one r118 makes before any take (it decides Short / live / upcoming / age / length / duplicate; unchanged:
   fetch.process, pipeline/ingest/fetch.py:249). So a record is taken within about a minute of landing, and the miner
   (its loop every 5 s, 3 videos at once) mines it at once: inside the ruling's 10 minutes.
3. Bitcoin channels first: Queue.due(states, limit, first=()) and Queue.hook_due(horizon, limit, first=()) order the
   videos of `first` (channel ids) before every other, newest first in each (no `first`: the old order exactly).
   service._first(): the channel ids of the registry's tiers up to config.BITCOIN_TIER_MAX (2): tier 1 Bitcoin-native
   (What Bitcoin Did, Bitcoin Magazine, TFTC, ...), tier 2 Bitcoin and crypto companies, media and podcasts (Scott
   Melker, DataDash, Strategy, Simply Bitcoin, CoinDesk, ...); tier 3 is mainstream finance and news (Bloomberg, CNBC,
   Fox Business, Yahoo Finance, WSJ, FT, ...). The registry has no other beat field; the pipeline's own transcript
   ingest already orders by tier (transcript_ingest.py:97). Read from the fetch round's own registry read, else at most
   once a minute; a registry that cannot be read keeps the last set (an order hint never stops a loop). Used by the
   fetch round (FETCH_DUE), the miner (MINE_DUE) and the hook pass (hook_due). The dormant paid route (ruling 118
   removed its config) keeps its own order.
4. The take's attempt line and queue event carry the record's acquired_at (when the pipeline's Whisper finished), so
   the transcript-to-mined latency is measured from the records.
5. tests/ingest/test_paid_route.py: a stub of Queue.due takes the new keyword.

## What to check (the laws below apply)
- No video skips the probe's checks because of the sweep (it only moves next_at; fetch.process decides everything).
- The sweep never touches a video in flight (probing, mining) or in any state but the two transcript waits, never one
  past its 12 h, and never makes a request to YouTube; while the gate is open it does not run (no busy loop).
- With no Bitcoin channel set, every order is exactly the old one; the SQL stays parameterised.
- Tier as "Bitcoin channel": is tier 2 right to count (Bitcoin and crypto companies, media, podcasts)?

Suite: tests/ingest 420 passed (6 new in test_r119.py). Mutations (scratch copy, files restored from backups): 10 of 10
killed (M22-M31).


```diff
diff --git a/pipeline/ingest/config.py b/pipeline/ingest/config.py
index 5b96f446..a7ab16cd 100644
--- a/pipeline/ingest/config.py
+++ b/pipeline/ingest/config.py
@@ -36,6 +36,9 @@ PLAYLIST_FIRST = True        # list the uploads playlist first, RSS the fallback
 VOD_MAX_S = 6 * 3600         # captions cost nothing to fetch; the selector keeps its own 3 h ceiling
 CAPTION_DEADLINE_H = 48      # no English captions 48 h after publish: no_captions (the pipeline's Whisper can do it)
 CAPTION_RETRY_S = (600, 1200, 2400, 4800)    # then every 2 h
+BITCOIN_TIER_MAX = 2         # the orchestrator's 13:05 ruling of Nov 16, "Bitcoin channels first": the registry's own
+                             # tiers (1 Bitcoin-native; 2 Bitcoin and crypto companies, media, podcasts; 3 mainstream
+                             # finance and news) up to this one are fetched, mined and hook-passed before the rest
 LIVE_REPROBE_S = 1200
 UPCOMING_REPROBE_S = 1800
 DUP_DURATION_TOL_S = 2.0
diff --git a/pipeline/ingest/cycles.py b/pipeline/ingest/cycles.py
index 74af5f58..9a4fe31a 100644
--- a/pipeline/ingest/cycles.py
+++ b/pipeline/ingest/cycles.py
@@ -14,6 +14,7 @@ from . import queue as Q
 
 ET = ZoneInfo("America/New_York")
 WINDOW_H = 3.0
+TRANSCRIPT_LAG_S = 600       # the 13:05 ruling of Nov 16: "mine each video within 10 minutes of its transcript"
 MAX_CHARS = 12000             # the line's ceiling: the window's oldest cycles beyond it are counted, not listed
 TITLE_CHARS = 40              # a video's title, shortened (a video id alone is not something a reader recognizes)
 WAITING = (Q.DISCOVERED, Q.PROBE_RETRY, Q.PROBING, Q.UPCOMING, Q.LIVE, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING,
@@ -67,6 +68,9 @@ def video_entry(v, name, via):
     lag = (f"seen {seen - pub:.0f} s after publish via {via or v['discovered_via']}, mined {mined - seen:.0f} s after"
            if pub and seen and mined else "publish time not measured")
     to = f"{mined - pub:.0f} s publish -> " if pub and mined else ""
+    tlag = v["transcript_lag_s"] if "transcript_lag_s" in v.keys() else None   # the 13:05 ruling (Nov 16)
+    if tlag is not None:
+        to += f"{tlag:.0f} s transcript{' (LATE)' if tlag > TRANSCRIPT_LAG_S else ''} -> "
     partial = " (partial)" if st == Q.MINED_PARTIAL else ""
     if v["moments"]:
         text = f"{head}: mined yes{partial} {at}, {v['moments']} moments, {hooks}, {to}rows ({lag})"
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index d9c9a221..53a79d29 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -37,6 +37,8 @@ PROBE_RETRY_S = (300, 900, 1800, 3600)
 CAPTION_THROTTLED_RETRY_S = 600     # a caption 429: tried again this soon (the pipeline's store is looked at first)
 PIPELINE_RECHECK_S = 1800           # a VOD without English captions inside its moments' life: looked at this often
                                     # (the pipeline's transcript ingest runs every 30 min)
+PIPELINE_SWEEP_S = 60               # the 13:05 ruling (Nov 16): each waiting video's record in the pipeline's store is
+                                    # looked for this often, whatever its next try (pipeline_sweep)
 PIPELINE_STORE = os.path.join(config.MAIN_STORE, "transcripts")     # the pipeline's own transcripts: READ ONLY
 PIPELINE_CIRCUIT = os.path.join(config.MAIN_STORE, "state", "caption_circuit.json")   # its caption 429 breaker: read
                                     # only (both ingests download captions from this one machine)
@@ -213,12 +215,37 @@ def take_pipeline_transcript(q, vid, channel_id, root=None):
         if os.path.exists(tmp):
             os.unlink(tmp)
     ts._log_attempt(vid, step="transcript", status="taken_from_pipeline_store", source=src,
-                    method=rec["transcript_method"], transcript_sha256=rec["transcript_sha256"], writer="pipeline.ingest")
+                    method=rec["transcript_method"], transcript_sha256=rec["transcript_sha256"],
+                    acquired_at=rec.get("acquired_at"), writer="pipeline.ingest")
     q.event("pipeline_transcript", vid, channel_id, source=src, method=rec["transcript_method"],
-            transcript_sha256=rec["transcript_sha256"])
+            transcript_sha256=rec["transcript_sha256"], acquired_at=rec.get("acquired_at"))
     return True
 
 
+def pipeline_sweep(q, now_ts):
+    """The orchestrator's 13:05 ruling of Nov 16 ("mine each video within 10 minutes of its transcript"): every video
+    waiting on a transcript (probe_retry, captions_pending) inside its moments' life (config.EXPIRY_H) whose next try
+    is later and whose record is in the pipeline's store (pipeline_transcript: every check) is made due now, whatever
+    its own retry time; the fetch step then probes it and takes the record. No YouTube request here (one glob, and a
+    read of a record that is there). Returns the ids made due; each is a queue event."""
+    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE state IN (?, ?) AND next_at > ? AND "
+                  "COALESCE(published_ts, discovered_ts) >= ?",
+                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, now_ts, now_ts - config.EXPIRY_H * 3600))
+    due = []
+    for r in rows:
+        try:
+            if pipeline_transcript(r["video_id"], r["channel_id"]) is not None:
+                due.append(r["video_id"])
+        except ValueError:                            # an id transcript_store refuses: never a path, never due here
+            continue
+    if due:
+        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?) AND video_id IN "
+            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING) + tuple(due))
+        for vid in due:
+            q.event("pipeline_transcript_due", vid, None)
+    return due
+
+
 def process(q, gate, v, chan, optout, now_ts=None):
     """Advance one due video by one step. Returns the new state."""
     now_ts = now_ts or q.clock()
diff --git a/pipeline/ingest/queue.py b/pipeline/ingest/queue.py
index dbffcca5..c7ee568c 100644
--- a/pipeline/ingest/queue.py
+++ b/pipeline/ingest/queue.py
@@ -64,7 +64,8 @@ VIDEO_FIELDS = ("title", "published_at", "published_ts", "published_source", "me
                 "reason", "transcript_sha256", "transcript_method", "transcribed_at", "transcribed_ts", "mined_at",
                 "mined_ts", "miners", "moments", "windows", "windows_screened", "windows_failed", "mine_cost_usd",
                 "duplicate_of", "title_canon", "text_fp", "tries", "mine_tries", "listing_url",
-                "mine_route", "recheck_ts")     # ruling 98: the role that last mined the video; its Heimdall re-mine
+                "mine_route", "recheck_ts",     # ruling 98: the role that last mined the video; its Heimdall re-mine
+                "transcript_lag_s")             # the 13:05 ruling (Nov 16): seconds from its transcript to its rows
 
 
 HOOK_COLUMNS = (("hook_ts", "REAL"), ("hook_rows", "INTEGER"), ("hook_cost_usd", "REAL"), ("hook_next_ts", "REAL"),
@@ -73,6 +74,7 @@ HOOK_COLUMNS = (("hook_ts", "REAL"), ("hook_rows", "INTEGER"), ("hook_cost_usd",
                 ("hook_version", "TEXT"),    # the hook question a completed pass asked (audit r92 c2, glm: --rerun)
                 ("spot_rows", "INTEGER"))    # the 08:15 ruling 2 (c): the spotlight rows the pass wrote (conversations)
 ROUTE_COLUMNS = (("mine_route", "TEXT"), ("recheck_ts", "REAL"))   # ruling 98: the miner's paid route
+LAG_COLUMNS = (("transcript_lag_s", "REAL"),)   # the 13:05 ruling (Nov 16): "within 10 minutes of its transcript"
 
 
 class Queue:
@@ -89,7 +91,7 @@ class Queue:
             cols = {r[1] for r in self.db.execute("PRAGMA table_info(videos)").fetchall()}
             if "first_sight" not in cols:          # queues created before the column (2026-11-12 03:26 ET)
                 self.db.execute("ALTER TABLE videos ADD COLUMN first_sight INTEGER NOT NULL DEFAULT 0")
-            for c, t in HOOK_COLUMNS + ROUTE_COLUMNS:   # ruling 80 (2026-11-13): the hook pass's state, per video;
+            for c, t in HOOK_COLUMNS + ROUTE_COLUMNS + LAG_COLUMNS:   # ruling 80: the hook pass's state, per video;
                 if c not in cols:                       # ruling 98: the mining route
                     self.db.execute(f"ALTER TABLE videos ADD COLUMN {c} {t}")
             self.db.execute("CREATE INDEX IF NOT EXISTS videos_hook ON videos(state, published_ts)")   # hook_due
@@ -174,11 +176,14 @@ class Queue:
                                   (to_state, config.iso(), vid) + tuple(from_states))
             return cur.rowcount == 1
 
-    def due(self, states, limit=50):
-        q = ",".join("?" * len(states))
+    def due(self, states, limit=50, first=()):
+        """Due videos in `states`, newest first; the videos of `first` (channel ids: the 13:05 ruling of Nov 16,
+        Bitcoin channels first) before every other, newest first among them."""
+        q, f = ",".join("?" * len(states)), tuple(first or ())
+        order = f"CASE WHEN channel_id IN ({','.join('?' * len(f))}) THEN 0 ELSE 1 END, " if f else ""
         return self.rows(f"SELECT * FROM videos WHERE state IN ({q}) AND next_at <= ? "
-                         "ORDER BY COALESCE(published_ts, listing_ts, discovered_ts) DESC LIMIT ?",
-                         tuple(states) + (self.clock(), limit))
+                         f"ORDER BY {order}COALESCE(published_ts, listing_ts, discovered_ts) DESC LIMIT ?",
+                         tuple(states) + (self.clock(),) + f + (limit,))
 
     def role_spend_since(self, role, since_ts):
         """Ruling 98: dollars recorded for one role's calls since a time (every attempt's cost): the paid route's
@@ -193,13 +198,15 @@ class Queue:
                          "published_ts >= ? ORDER BY published_ts DESC LIMIT ?",
                          (MINED, MINED_PARTIAL, route, self.clock() - horizon_s, limit))
 
-    def hook_due(self, horizon_s, limit=50):
+    def hook_due(self, horizon_s, limit=50, first=()):
         """Ruling 80: mined videos published inside the last `horizon_s` (12 h) whose hook pass has not run, newest
-        first; a pass that waited on an outage is due again at hook_next_ts."""
-        now = self.clock()
+        first (the videos of `first`, Bitcoin channels, before the rest: the 13:05 ruling of Nov 16); a pass that
+        waited on an outage is due again at hook_next_ts."""
+        now, f = self.clock(), tuple(first or ())
+        order = f"CASE WHEN channel_id IN ({','.join('?' * len(f))}) THEN 0 ELSE 1 END, " if f else ""
         return self.rows(f"SELECT * FROM videos WHERE state IN (?, ?) AND hook_ts IS NULL AND COALESCE(hook_next_ts, 0) "
-                         "<= ? AND published_ts >= ? ORDER BY published_ts DESC LIMIT ?",
-                         (MINED, MINED_PARTIAL, now, now - horizon_s, limit))
+                         f"<= ? AND published_ts >= ? ORDER BY {order}published_ts DESC LIMIT ?",
+                         (MINED, MINED_PARTIAL, now, now - horizon_s) + f + (limit,))
 
     def set_hook(self, vid, **kw):
         bad = [k for k in kw if k not in dict(HOOK_COLUMNS)]
diff --git a/pipeline/ingest/service.py b/pipeline/ingest/service.py
index 401f5d42..3f2a263b 100644
--- a/pipeline/ingest/service.py
+++ b/pipeline/ingest/service.py
@@ -84,6 +84,19 @@ class ServiceBusy(RuntimeError):
     """Another pp-ingest service holds this store."""
 
 
+TRANSCRIPT_LAG_S = 600         # the 13:05 ruling (Nov 16): "mine each video within 10 minutes of its transcript"
+
+
+def transcript_lag(acquired, now):
+    """Seconds from a transcript record's own time (its acquired_at: when its captions were stored or the pipeline's
+    Whisper finished) to now; None when the record carries no readable time with its zone."""
+    try:
+        d = datetime.fromisoformat(str(acquired).replace("Z", "+00:00"))
+    except (TypeError, ValueError):
+        return None
+    return max(0.0, now - d.timestamp()) if d.tzinfo is not None else None
+
+
 def check_roles(cfg):
     """Every mining question (mine.KINDS) and the second-model check (flagcheck.ROLE) need their role in the provider
     config; a missing one stops the start (the 08:15 ruling 2 added the spotlight question: asked without its role,
@@ -144,6 +157,8 @@ class Service:
         self.cycles_error = None                         # the cycles line's last failure (logged once per cause)
         self.batch_error = None                          # ruling 108: the batch line's last failure (logged once)
         self.stall_error = None                          # the 10:50 order (4): the stall line's last failure (once)
+        self._first_ids, self._first_at = frozenset(), None   # the 13:05 ruling: the Bitcoin channels (registry tiers)
+        self._last_sweep = None                          # the 13:05 ruling: the last look in the pipeline's store
         self._reuse_tried = False                       # the start's one look at the stored live calibration
         self.stop = threading.Event()
         self.rss_mode, self.rss_checked = False, 0.0
@@ -250,6 +265,14 @@ class Service:
             return 0
         reg, chans = watch.registry()
         by = {c["channel_id"]: c for c in chans}
+        first = self._first(chans)
+        now = self.clock()
+        if (self._last_sweep is None or now - self._last_sweep >= fetch.PIPELINE_SWEEP_S) and not self.gate.open_for():
+            self._last_sweep = now                       # (with the gate open no probe can run: looked at once it shuts)
+            made = fetch.pipeline_sweep(self.q, now)
+            if made:
+                self.log(f"fetch: {len(made)} waiting video(s) with a transcript in the pipeline's store made due: "
+                         f"{', '.join(made)}")
 
         def one(v):
             try:
@@ -267,7 +290,7 @@ class Service:
             if st in (Q.TRANSCRIBED, Q.SHORT, Q.LIVE, Q.NO_CAPTIONS, Q.DUPLICATE, Q.TOO_LONG):
                 self.log(f"fetch {v['video_id']} ({by.get(v['channel_id'], {}).get('display_name')}): {st}")
             return st
-        claimed = [v for v in self.q.due(Q.FETCH_DUE, limit)
+        claimed = [v for v in self.q.due(Q.FETCH_DUE, limit, first=first)
                    if not self.stop.is_set() and self.q.claim(v["video_id"], (v["state"],), Q.PROBING)]
         with ThreadPoolExecutor(max_workers=config.YTDLP_CONCURRENCY, thread_name_prefix="fetch") as ex:
             list(ex.map(one, claimed))           # the yt-dlp gate bounds YouTube at YTDLP_CONCURRENCY processes
@@ -298,7 +321,7 @@ class Service:
                                          datetime.now(timezone.utc), self.cycle, extra_source=src, role=route)
             cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND "
                                "COALESCE(role, 'mine')=?", (vid, route))[0]["usd"]
-            self._settle(v, chan, lines, rep, cost, t0, route=route)
+            self._settle(v, chan, lines, rep, cost, t0, route=route, acquired=rec.get("acquired_at"))
         except ContractUnavailable as e:
             self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S, reason=f"contract unavailable: {e}")
             self.log(f"mine {vid}: contract unavailable: {e}")
@@ -334,9 +357,12 @@ class Service:
         since = datetime.fromtimestamp(float(v.get("discovered_ts") or self.clock()) - 86400, timezone.utc)
         return len(ledger.video_moment_ids(self.p["ledger"], v["video_id"], since))
 
-    def _settle(self, v, chan, lines, rep, cost, t0, route="mine"):
-        """The video's state after one mining pass (see the module docstring); route: the role that mined it."""
+    def _settle(self, v, chan, lines, rep, cost, t0, route="mine", acquired=None):
+        """The video's state after one mining pass (see the module docstring); route: the role that mined it;
+        acquired: its transcript record's own time (the 13:05 ruling of Nov 16: "within 10 minutes of its transcript",
+        said with every video mined and kept on its row; past TRANSCRIPT_LAG_S, LATE)."""
         vid, now = v["video_id"], self.clock()
+        lag = transcript_lag(acquired, now)
         failed = rep["failed"]
         rejected = [f for f in failed if not f["outage"]]
         passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)
@@ -349,6 +375,10 @@ class Service:
         what = (f"{len(lines)} moments, windows {rep['windows']} (screened {rep['screened']}, failed {len(failed)}: "
                 f"{len(rejected)} rejected, {len(failed) - len(rejected)} outage), miners {rep['miners']}, "
                 f"${(cost or 0):.4f}, {now - t0:.0f} s")
+        if lag is not None:
+            common["transcript_lag_s"] = round(lag, 1)
+            what += f", {lag:.0f} s from its transcript" + (" (LATE: past the 13:05 ruling's 10 minutes)"
+                                                            if lag > TRANSCRIPT_LAG_S else "")
         if not failed:
             self._append(v, lines)                        # a partial video's earlier lines appear again: the latest
                                                           # wins, carrying every earlier flag (ruling 80)
@@ -483,7 +513,7 @@ class Service:
             free = HOOK_VIDEOS - len(self.hook_inflight)
         if free <= 0:
             return 0
-        for v in self.q.hook_due(HOOK_HORIZON_S, HOOK_VIDEOS * 2):
+        for v in self.q.hook_due(HOOK_HORIZON_S, HOOK_VIDEOS * 2, first=self._first()):
             with self.hlock:
                 if v["video_id"] in self.hook_inflight or len(self.hook_inflight) >= HOOK_VIDEOS:
                     continue
@@ -690,7 +720,7 @@ class Service:
                 self.router.release()                     # idle: the local model (if any) leaves GPU0 (B3)
             return 0
         self._last_mining = self.clock()
-        for v in (self._paid_due(pr, free) if paid else self.q.due(Q.MINE_DUE, free)):
+        for v in (self._paid_due(pr, free) if paid else self.q.due(Q.MINE_DUE, free, first=self._first())):
             if not self.q.claim(v["video_id"], Q.MINE_DUE, Q.MINING):
                 continue
             with self.ilock:
@@ -804,6 +834,23 @@ class Service:
                 self.log(f"ruling 108: the batch line could not be written: {why}")
             self.batch_error = why
 
+    def _first(self, chans=None):
+        """The orchestrator's 13:05 ruling of Nov 16, "Bitcoin channels first": the channel ids of the registry's tiers
+        up to config.BITCOIN_TIER_MAX, taken from `chans` (the fetch step's own read) or the registry at most once a
+        minute; a registry that cannot be read keeps the last set (the order, never the work, depends on it)."""
+        now = self.clock()
+        if chans is None and self._first_at is not None and now - self._first_at < 60:
+            return self._first_ids
+        try:
+            if chans is None:
+                chans = watch.registry()[1]
+            ids = frozenset(c["channel_id"] for c in chans
+                            if isinstance(c.get("tier"), int) and c["tier"] <= config.BITCOIN_TIER_MAX)
+        except Exception:                            # noqa: BLE001 (an order hint never stops a loop)
+            return self._first_ids
+        self._first_ids, self._first_at = ids, now
+        return ids
+
     def _stall_notice(self, now):
         """The orchestrator's 10:50 ET order of Nov 16 (4), the self-check (stall.py): videos waiting and nothing mined
         for stall.STALL_S: said at the front of STATE line 1 and acted on (the waiting videos made due now) when found
diff --git a/tests/ingest/test_paid_route.py b/tests/ingest/test_paid_route.py
index 0a073c8e..d640b3bf 100644
--- a/tests/ingest/test_paid_route.py
+++ b/tests/ingest/test_paid_route.py
@@ -175,7 +175,7 @@ def test_the_paid_route_mines_new_uploads_only_conversations_first(paid, monkeyp
     rows = [{"video_id": "solo1h", "published_ts": now - 3600}, {"video_id": "conv2h", "published_ts": now - 7200},
             {"video_id": "old8h", "published_ts": now - 8 * 3600},
             {"video_id": "conv5h", "published_ts": now - 5 * 3600}]
-    monkeypatch.setattr(s.q, "due", lambda states, limit=50: rows[:limit])
+    monkeypatch.setattr(s.q, "due", lambda states, limit=50, first=(): rows[:limit])
 
     class TS:
         @staticmethod
diff --git a/tests/ingest/test_r119.py b/tests/ingest/test_r119.py
new file mode 100644
index 00000000..2b6782f4
--- /dev/null
+++ b/tests/ingest/test_r119.py
@@ -0,0 +1,204 @@
+"""tests/ingest/test_r119.py: the orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its
+transcript, Bitcoin channels first".
+
+- pipeline_sweep: every video waiting on a transcript whose record lands in the pipeline's store is due at once,
+  whatever its own retry time (each fetch round, at most every fetch.PIPELINE_SWEEP_S, never while the gate is open).
+- Queue.due / hook_due: the Bitcoin channels (the registry's tiers up to config.BITCOIN_TIER_MAX) before the rest,
+  newest first among each.
+"""
+import json
+import os
+
+import pytest
+
+import helpers as H
+from pipeline.ingest import config, fetch, ledger, watch
+from pipeline.ingest import queue as Q
+from test_service import svc  # noqa: F401 (the service fixture: fake back-ends, fake gate, its own store)
+
+NOW = 1794470000.0
+BTC, MAIN = H.CHAN["channel_id"], "UC" + "m" * 22
+
+
+@pytest.fixture
+def q(tmp_path):
+    return Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: NOW)
+
+
+def row(q, v, cid, state, published, next_at=NOW - 1, discovered=None, reason=None):
+    q.add_video(v, cid, f"t {v}", "rss")
+    q.x("UPDATE videos SET state=?, published_ts=?, next_at=?, discovered_ts=?, reason=? WHERE video_id=?",
+        (state, published, next_at, discovered if discovered is not None else published, reason, v))
+
+
+def pipeline_record(v, cid=BTC, tamper=None):
+    rec, _ = H.caption_record(v, channel=dict(H.CHAN, channel_id=cid))
+    rec = dict(rec, transcript_method="whisper", transcript_model="test model")
+    if tamper:
+        tamper(rec)
+    d = os.path.join(fetch.PIPELINE_STORE, v)
+    os.makedirs(d, exist_ok=True)
+    with open(os.path.join(d, "transcript.whisper.json"), "w") as f:
+        json.dump(rec, f)
+    return rec
+
+
+# ── Bitcoin channels first ──
+
+def test_due_takes_the_bitcoin_channels_first_then_the_newest():
+    import tempfile
+    q = Q.Queue(os.path.join(tempfile.mkdtemp(), "q.sqlite"), clock=lambda: NOW)
+    row(q, "b_old000001", BTC, Q.TRANSCRIBED, NOW - 3000)
+    row(q, "b_new000001", BTC, Q.TRANSCRIBED, NOW - 1000)
+    row(q, "m_new000001", MAIN, Q.TRANSCRIBED, NOW - 100)
+    row(q, "m_old000001", MAIN, Q.TRANSCRIBED, NOW - 4000)
+    ids = lambda rows: [r["video_id"] for r in rows]
+    assert ids(q.due(Q.MINE_DUE, 10)) == ["m_new000001", "b_new000001", "b_old000001", "m_old000001"]   # as before
+    assert ids(q.due(Q.MINE_DUE, 10, first={BTC})) == ["b_new000001", "b_old000001", "m_new000001", "m_old000001"]
+    assert ids(q.due(Q.MINE_DUE, 1, first={BTC})) == ["b_new000001"]                    # one free slot: Bitcoin
+    q.x("UPDATE videos SET state=?", (Q.CAPTIONS_PENDING,))
+    assert ids(q.due(Q.FETCH_DUE, 2, first={BTC})) == ["b_new000001", "b_old000001"]
+    q.x("UPDATE videos SET state=?, hook_ts=NULL", (Q.MINED,))
+    assert ids(q.hook_due(12 * 3600, 10, first={BTC})) == ["b_new000001", "b_old000001", "m_new000001", "m_old000001"]
+    assert ids(q.hook_due(12 * 3600, 10)) == ["m_new000001", "b_new000001", "b_old000001", "m_old000001"]
+
+
+def test_the_bitcoin_channels_are_the_registrys_tiers_up_to_two(svc, monkeypatch):
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
+    chans = [dict(H.CHAN, channel_id="UC" + c * 22, tier=t) for c, t in (("a", 1), ("b", 2), ("c", 3))] + \
+        [dict(H.CHAN, channel_id="UC" + "d" * 22, tier=None)]
+    assert s._first(chans) == {"UC" + "a" * 22, "UC" + "b" * 22} and config.BITCOIN_TIER_MAX == 2
+    monkeypatch.setattr(watch, "registry", lambda: (_ for _ in ()).throw(OSError("registry unreadable")))
+    s._first_at = None
+    assert s._first() == {"UC" + "a" * 22, "UC" + "b" * 22}           # a registry not read keeps the last set
+
+
+def test_the_watcher_mines_a_bitcoin_channels_video_before_a_newer_mainstream_one(svc, monkeypatch):
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=2)
+    main = dict(H.CHAN, channel_id=MAIN, slug="main", tier=3)
+    monkeypatch.setattr(watch, "registry", lambda: ([H.CHAN, main], [H.CHAN, main]))
+    s.watch_once()
+    while s.fetch_once(limit=20):
+        pass
+    older, newer = vids
+    s.q.x("UPDATE videos SET published_ts=published_ts - 600 WHERE video_id=?", (older,))
+    s.q.x("UPDATE videos SET channel_id=? WHERE video_id=?", (MAIN, newer))     # the newer one: mainstream
+    s.q.x("UPDATE videos SET state=?, next_at=0", (Q.TRANSCRIBED,))
+    order = []
+    real = s.mine_video
+    monkeypatch.setattr(s, "mine_video", lambda v, role=None: (order.append(v["video_id"]), real(v, role))[1])
+    s.inflight = {"x", "y"}                                            # one free slot
+    s.mine_once(wait=True)
+    assert order == [older]
+
+
+# ── within minutes of its transcript ──
+
+def _broken(r):
+    r["segments"][0]["text"] += " (edited)"
+
+
+def test_the_sweep_makes_due_only_a_waiting_video_whose_transcript_is_in_the_pipelines_store(q):
+    later = NOW + 3600
+    for v, state, pub, rec in (("w1aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, True),
+                               ("w2aaaaaaaaa", Q.PROBE_RETRY, NOW - 600, True),
+                               ("w3aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, False),       # no record yet
+                               ("w4aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, "broken"),    # fails its checks
+                               ("w5aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 13 * 3600, True),  # past its 12 h
+                               ("w6aaaaaaaaa", Q.MINING, NOW - 600, True),                  # in flight
+                               ("w7aaaaaaaaa", Q.UPCOMING, NOW - 600, True)):               # not a transcript wait
+        row(q, v, BTC, state, pub, next_at=later)
+        if rec:
+            pipeline_record(v, tamper=_broken if rec == "broken" else None)
+    row(q, "w8aaaaaaaaa", BTC, Q.CAPTIONS_PENDING, NOW - 600, next_at=NOW - 5)                # already due
+    pipeline_record("w8aaaaaaaaa")
+    assert sorted(fetch.pipeline_sweep(q, NOW)) == ["w1aaaaaaaaa", "w2aaaaaaaaa"]
+    nxt = {r["video_id"]: r["next_at"] for r in q.rows("SELECT video_id, next_at FROM videos")}
+    assert nxt["w1aaaaaaaaa"] == nxt["w2aaaaaaaaa"] == NOW
+    assert all(nxt[v] == later for v in ("w3aaaaaaaaa", "w4aaaaaaaaa", "w5aaaaaaaaa", "w6aaaaaaaaa", "w7aaaaaaaaa"))
+    assert sorted(r["video_id"] for r in q.rows("SELECT video_id FROM events WHERE kind='pipeline_transcript_due'")) \
+        == ["w1aaaaaaaaa", "w2aaaaaaaaa"]
+    assert fetch.pipeline_sweep(q, NOW) == []                          # due now: nothing more to do
+
+
+def test_a_transcript_landing_in_the_pipelines_store_is_mined_at_the_next_fetch_round(svc, monkeypatch):
+    """A video put off 30 min by a caption 429: its Whisper record lands; the next fetch round (the sweep: at most
+    fetch.PIPELINE_SWEEP_S apart) takes it and the miner mines it, long before its own retry."""
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
+    v = vids[0]
+    ts = config.ts()
+    monkeypatch.setattr(ts, "fetch_captions", lambda meta, work: ("throttled", None))
+    s.watch_once()
+    s.fetch_once(limit=20)
+    row0 = s.q.video(v)
+    assert row0["state"] == Q.CAPTIONS_PENDING and row0["next_at"] > s.clock() + 500
+    rec = pipeline_record(v)
+    s._last_sweep = s.clock() - fetch.PIPELINE_SWEEP_S                 # the next sweep is due
+    s.fetch_once(limit=20)
+    assert s.q.video(v)["state"] == Q.TRANSCRIBED and s.q.video(v)["transcript_sha256"] == rec["transcript_sha256"]
+    while s.mine_once(wait=True):
+        pass
+    assert s.q.video(v)["state"] == Q.MINED
+    lines, bad = ledger.read(s.p["ledger"])
+    assert not bad and {l["video_id"] for l in lines} == {v}
+    ev = s.q.rows("SELECT detail FROM events WHERE kind='pipeline_transcript' AND video_id=?", (v,))
+    assert json.loads(ev[0]["detail"])["acquired_at"] == rec["acquired_at"]  # the pipeline's own time: the latency
+
+
+def test_no_sweep_while_the_gate_is_open_and_at_most_one_a_minute(svc, monkeypatch):
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
+    calls = []
+    monkeypatch.setattr(fetch, "pipeline_sweep", lambda q, now: (calls.append(now), [])[1])
+    monkeypatch.setattr(s.gate, "open_for", lambda: 300.0, raising=False)
+    s.fetch_once(limit=1)
+    assert calls == []                                                 # no probe can run: looked at once it shuts
+    monkeypatch.setattr(s.gate, "open_for", lambda: 0.0, raising=False)
+    s.fetch_once(limit=1)
+    s.fetch_once(limit=1)                                              # the same minute: not again
+    assert len(calls) == 1
+    s._last_sweep -= fetch.PIPELINE_SWEEP_S
+    s.fetch_once(limit=1)
+    assert len(calls) == 2
+
+
+# ── the measure (audit r119 c1): seconds from its transcript to its rows, LATE past 10 minutes ──
+
+def test_transcript_lag_reads_only_a_time_with_its_zone():
+    from datetime import datetime, timezone
+    from pipeline.ingest import service
+    at = datetime.fromtimestamp(NOW - 800, timezone.utc)
+    assert service.transcript_lag(at.isoformat(), NOW) == pytest.approx(800.0)
+    assert service.transcript_lag(at.strftime("%Y-%m-%dT%H:%M:%SZ"), NOW) == pytest.approx(800.0)
+    naive = at.replace(tzinfo=None).isoformat()
+    assert service.transcript_lag(None, NOW) is None and service.transcript_lag(naive, NOW) is None
+    assert service.transcript_lag("not a time", NOW) is None
+    assert service.transcript_lag("2030-01-01T00:00:00+00:00", NOW) == 0.0          # never negative
+
+
+def test_a_video_mined_past_10_minutes_from_its_transcript_is_said_late_in_the_log_and_on_the_cycles_line(svc,
+                                                                                                        monkeypatch):
+    import time as _time
+    from datetime import datetime, timezone
+    from pipeline.ingest import cycles
+    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
+    logs = []
+    s.log = logs.append
+    v = vids[0]
+    monkeypatch.setattr(config.ts(), "fetch_captions", lambda meta, work: ("throttled", None))
+    s.watch_once()
+    s.fetch_once(limit=20)
+    old = datetime.fromtimestamp(_time.time() - 700, timezone.utc).isoformat()
+    pipeline_record(v, tamper=lambda r: r.update(acquired_at=old))   # the pipeline's Whisper, 700 s ago
+    s._last_sweep = None
+    s.fetch_once(limit=20)
+    while s.mine_once(wait=True):
+        pass
+    row = s.q.video(v)
+    assert row["state"] == Q.MINED and 695 <= row["transcript_lag_s"] <= 760
+    said = [m for m in logs if m.startswith(f"mine {v} ")]
+    assert said and "s from its transcript (LATE: past the 13:05 ruling's 10 minutes)" in said[-1]
+    line = cycles.compose(s.q, _time.time())
+    assert f"{row['transcript_lag_s']:.0f} s transcript (LATE) -> rows" in line
+    s.q.x("UPDATE videos SET transcript_lag_s=42 WHERE video_id=?", (v,))
+    line = cycles.compose(s.q, _time.time())
+    assert "42 s transcript -> rows" in line and "(LATE)" not in line

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

