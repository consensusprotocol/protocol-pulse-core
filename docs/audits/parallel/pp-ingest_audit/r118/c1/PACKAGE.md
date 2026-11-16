# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 44ddac29
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
# r118: the stalled miner (the orchestrator's 10:50 ET order of Nov 16), rulings 118 and 119 (3)

## The order (verbatim, the parts this change answers)

"(1) NOW: find why those 14 are not mined (transcripts not fetched or not transcribed? the miner waiting on a route? a
job that only runs on a timer? the GPU0 lease? the false Plan B switches leaving it between routes?) and mine them,
newest conversations first, ON HEIMDALL. Say the cause in one line on line 1 of your STATE as soon as you know it, then
fix it properly, audit-first on Heimdall only.
(2) THE TERMS HAVE CHANGED (ruling 118, PBX 05:25 ET today): outside vendors are capped at $1.00 A DAY for the whole
pipeline and $0.58 is already spent, so the miner's PAID ROUTE IS CLOSED: Plan B for mining is no longer Grok or Gemini.
It is the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the
local model on a free card under the lease. Heimdall is free and effectively unlimited for us; a video may wait
minutes, never hours. glm is out of every chain (ruling 119 (3)).
(3) NO MORE FALSE OUTAGES: the outage clock is fed only by YOUR OWN mining and probe calls, never by another session's
deadline misses, and any answered call or probe resets it (ruling 87 as amended). Land that with (1).
(4) SELF-CHECK: if videos are waiting and nothing has been mined for 30 minutes, write it on line 1 and act; do not sit
idle at the prompt."

## The cause (measured, Nov 16)

- From 07:47 ET YouTube answered HTTP 429 ("Unable to download video subtitles ... Too Many Requests") to EVERY caption
  download from this machine: 12 tries 07:47-10:37 ET, none ok (the last ok 07:18 ET). The main tree's own transcript
  ingest (cron */30, pipeline/transcript_ingest.py: captions, else Whisper on GPU0) got the same 429s (its breaker file
  data/editorial/state/caption_circuit.json: "HTTP 429 on lcYYuefFMQA" at 10:00 ET) and transcribed most of the same
  videos with Whisper.
- The watcher has no transcript path but captions (no Whisper, no GPU), and fetch._store_captions TRIPPED THE WHOLE
  yt-dlp GATE (watch.YouTubeGate, 10 / 20 / 40 / 60 min) on every caption refusal, even a refusal made by
  transcript_store's own 30-minute caption breaker with NO request (fetch_captions returns "throttled" at once while
  caption_circuit_open(), pipeline/transcript_store.py:208 and :249-261). So the probes, which YouTube still answered
  (the uploads-playlist listing too: 59-64 channels listed in the same cycles), stopped as well: 9 videos sat in
  probe_retry ("rate_limited: yt-dlp breaker open for 389 s") and 5 in captions_pending. Nothing reached the miner from
  07:18 ET. Not the miner (Heimdall qwen answered at 06:37 ET), not its route, not the GPU lease, not a switch (none since
  Nov 14).
- Done at 10:53 ET by hand (a one-off with the watcher stopped, the watcher's own fetch.process): the pipeline's 7
  Whisper records were copied in, the videos probed and mined on Heimdall qwen at once (5 moments: Strategy 2, Fox
  Business 3; the other 5 had no Bitcoin-bearing window).

## The change

1. fetch.py: THE PIPELINE'S OWN TRANSCRIPT. After the probe's checks (channel, Short, upcoming, live, publish time, age,
   duration, title duplicate) and BEFORE the caption check: pipeline_transcript() reads the main tree's store
   (config.MAIN_STORE/transcripts/<id>/transcript.*.json, READ ONLY; fetch.PIPELINE_STORE) and takes the best record by
   transcript_store.METHOD_RANK that names this video and this channel, is filed under its own method's name, has
   segments, and whose segments hash to its transcript_sha256. take_pipeline_transcript() copies it byte for byte into
   this store (tmp file, re-read and re-hashed, then os.link: write-once; a record of that method already here is kept),
   logs an attempt and a queue event; _store_captions then finds it (canonical_transcript) and marks the video
   transcribed without any download. Also when a VOD lists no English captions (BLOy6SetrUs, Yahoo Finance).
2. fetch.py: A CAPTION 429 STOPS THE CAPTIONS ALONE. No gate.trip on a caption refusal (the gate stays tripped by a
   probe's or a listing's own 429 / bot check: watch.YouTubeGate.run, pipeline/ingest/watch.py:60-71, unchanged); the
   video is tried again in CAPTION_THROTTLED_RETRY_S (600 s, was 1800), the pipeline's store looked at first. While the
   PIPELINE's caption breaker is open (its ingest was refused in the last 30 min: same machine, same IP), no download is
   tried here either (pipeline_captions_refused, its file read only). Inside the moments' life (config.EXPIRY_H, 12 h) a
   VOD without English captions is looked at every 30 min at most (_caption_retry_at), the pipeline's ingest period.
3. downsignal.py + config.py: THE OUTAGE CLOCK IS THE WATCHER'S OWN. The builder's module (pp-selectid
   pipeline/heimdall_health.py: note :141, the 15-minute rule _down_rule :176, probe_due :204, probe_result :230,
   unchanged and used through its API only) now runs on config.paths()["signal_state"]
   (data/editorial/ingest/down_signal_state.json), never its shared STATE: only this watcher's own calls are noted, only
   its own probes claim slots, only its own switches reach STATE line 1. probe_due is called without `families` (no other
   prober shares the file, so a slot left "to the prober that can ask a failed family" would never be taken: the clock
   would run to 15 min on an answering gateway). The probe role asks one back-end per family the watcher calls (as since
   10:05 Nov 14): qwen, deepseek, minimax, gemma, gpt-oss, mimo, muse; any answer resets the clock (the module, unchanged).
4. providers.json: RULING 118 / 119 (3). mine, hook and spotlight chains: qwen, deepseek 4.1, minimax, gemma, gpt-oss,
   mimo (all served by the Heimdall gateway, vendor "heimdall"), then local_gemma (still "enabled": false; available only
   while this process holds the GPU0 lease: OllamaLocalBackend.enabled, pipeline/ingest/providers.py:494, unchanged). The
   paid route (paid_route, the mine_paid role) removed: service.mine_once and downsignal._route_tick already do nothing
   without paid_route. glm's two back-ends "enabled": false and in no chain; the flag check is muse then deepseek
   (ruling 40's per-row rule, flagcheck.checkers, pipeline/ingest/flagcheck.py:244, unchanged: never the miner of the
   row's video, by back-end and by model; deepseek answers only once the watcher's live calibration passes it).
5. stall.py + spend.py + service.py: THE SELF-CHECK. A video inside its 12 h in a state that leads to mining
   (discovered, probing, probe_retry, captions_pending, transcribed, mining, mine_waiting; never upcoming or live) is
   waiting; a stall is something waiting and nothing mined for 30 min (the later of the newest mined_ts and the oldest
   waiting discovery is 30 min old). The health loop then writes "MINING STALLED SINCE HH:MM ET: n VIDEO(S) WAITING ...:
   <counts by what each waits on>; ACTED HH:MM ET: m MADE DUE NOW ..." at the front of STATE line 1 (after the batch
   spend and an alarm, before the switch line; one segment, its writer refuses '|' and newlines; text stable while the
   stall lasts) and ACTS: every waiting video in a retry state whose next try is later is made due now (never one in
   flight), when found and again every 30 min; the line goes when the stall ends.
6. tests/ingest/xllm_audit.py: this audit's reviewers are qwen + muse (glm excluded by name: ruling 119 (3)); the third
   family is mimo.

## Live check of the new chain (Nov 16 ~11:30 ET, the watcher's own mining question and validator, 1 window each of
Vu0XZSz-aj4 and DO6iIRbccIg, no stored replies): minimax 2/2 valid (57 s), mimo 2/2 valid (25 s), gpt-oss 1/2 (one
reply's reason over 160 characters: invalid, the router's next attempt), deepseek and gemma no answer within their 300 /
240 s deadlines at the time (the chain moves on; their breakers open after 5 failures).

## What to check (the laws below apply)

- The main tree is never written: the pipeline's store and its breaker file are only read (open for reading, glob,
  shutil.copyfile FROM them). A record is never taken without every check; the bytes linked in are the bytes checked.
- No video skips the probe's checks (Short, live, upcoming, too old, too long, duplicate) because a record exists.
- The gate still stops every yt-dlp call on a probe's or a listing's 429; a caption 429 can no longer stop the probes.
- The watcher's clock can no longer be started or moved by another session; its own failure still starts it and any
  answer (call or probe) resets it; a slot is never left unclaimed on its own file.
- No glm in any chain; no muse in mine / hook / spotlight; no paid route; no frozen vendor callable.
- The stall line: never on line 1 when nothing waits or something was mined in the last 30 min; never splits or folds
  the switch line; the act never touches a video in flight and acts at most every 30 min.
- Tests never read the real main-tree store (conftest points fetch.PIPELINE_STORE / PIPELINE_CIRCUIT at a temp dir).

Suite: tests/ingest 414 passed. Mutations (scratch copy, files restored from backups): 17 of 18 killed; M17 (no early
return when a record of that method is already here) is equivalent: the write-once os.link refuses it the same way.


```diff
diff --git a/pipeline/ingest/config.py b/pipeline/ingest/config.py
index 5c85e480..5b96f446 100644
--- a/pipeline/ingest/config.py
+++ b/pipeline/ingest/config.py
@@ -104,6 +104,7 @@ def paths(root=None):
         "work": os.path.join(ing, "work"),
         "purge": os.path.join(ing, "purge"),
         "signal": os.path.join(ing, "down_signal.jsonl"),         # ruling 87: this watcher's evidence file
+        "signal_state": os.path.join(ing, "down_signal_state.json"),   # its OWN outage clock (the 10:50 order (3))
         "audit_spend": os.path.join(ing, "audit_spend.jsonl"),    # ruling 108: one record per audit review's cost
     }
 
diff --git a/pipeline/ingest/downsignal.py b/pipeline/ingest/downsignal.py
index e99ac710..3ad8c1b0 100644
--- a/pipeline/ingest/downsignal.py
+++ b/pipeline/ingest/downsignal.py
@@ -1,6 +1,15 @@
-"""pipeline/ingest/downsignal.py: RULING 87 (orchestrator 21:18 Nov 13), this watcher's side of the ONE shared
-'Heimdall down' signal (pp-selectid pipeline/heimdall_health.py, the builder's module, used through its API only; its
-state file under its own flock).
+"""pipeline/ingest/downsignal.py: RULING 87 (orchestrator 21:18 Nov 13), this watcher's 'Heimdall down' signal: the
+builder's module (pp-selectid pipeline/heimdall_health.py, used through its API only, its state file under its own
+flock) run on THIS WATCHER'S OWN state file.
+
+OWN   RULING 87 AS AMENDED BY THE ORCHESTRATOR'S 10:50 ET ORDER OF NOV 16 (3): "the outage clock is fed only by YOUR
+      OWN mining and probe calls, never by another session's deadline misses, and any answered call or probe resets
+      it". Until then the watcher and the builder shared one state file, and the builder's own deadline misses
+      started the watcher's clock (the false outages of Nov 14 09:16 and 10:12 ET). The state file is now the
+      watcher's own (config.paths()["signal_state"]; a test may pass another): only its own calls are noted there,
+      only its own probes claim a slot, and only the switches made on it go to STATE line 1. Its probe claims every
+      slot it is due (no `families`: no other prober shares the file to leave a slot to). The miner's Plan B is
+      ruling 118's: the mine chain as it is (the next model of the chain), else the videos wait; no paid route.
 
 NOTE  every real call of this watcher to a back-end of the signal's vendor (providers.json down_signal) is one outcome:
       answered (ok, invalid: the gateway answered inside the back-end's deadline) or not (any other kind of a real call:
@@ -51,8 +60,9 @@ ANSWERED = frozenset({"ok", "invalid"})              # the gateway answered insi
 NO_CALL = frozenset({"cache", "disabled"})           # nothing was asked of the gateway
 ET = ZoneInfo("America/New_York")
 DOWN = "plan_b"                                      # the module's down mode; its other mode is the up one (MODES)
-MINER_PLAN_B = ("queue and wait: the 05:30 Nov 12 spend freeze binds the miner until the orchestrator answers the "
-                "Plan B question (the mine chain as it is, else the videos wait)")
+MINER_PLAN_B = ("ruling 118 (orchestrator 10:50 ET Nov 16): no paid route; the mine chain as it is (the next model "
+                "of the chain; the local model only under the GPU lease), else the videos wait")
+PLAN_B_TAIL = "; THE MINER'S PLAN B (RULING 118): THE NEXT MODEL OF ITS CHAIN, ELSE THE VIDEOS WAIT"
 
 
 def load_module(path):
@@ -92,7 +102,7 @@ def _any_text(c):
     return c
 
 
-def head(rec, seen_ts, up, plan_b_tail="; THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE)"):
+def head(rec, seen_ts, up, plan_b_tail=PLAN_B_TAIL):
     """STATE line 1's head for one switch record {"utc", "to", "why", "by"} (the module's words: "SWITCHED TO PLAN B",
     "BACK TO <UP MODE>", plus who made it and what the miner does), IN CAPITALS, one physical line. None: not a switch
     between the module's two modes (up: the mode that is not DOWN)."""
@@ -125,7 +135,7 @@ class DownSignal:
         pr = self.paid
         self.plan_b_tail = (f"; THE MINER'S PLAN B (RULING 98): NEW UPLOADS ON {pr['label']} AFTER "
                             f"{int(pr['after_down_s'] // 60)} MINUTES DOWN, CAPPED" if pr else
-                            "; THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE)")
+                            PLAN_B_TAIL)
         self.miner_plan_b = (f"ruling 98: after {int(pr['after_down_s'] // 60)} minutes down, new uploads (the last "
                              f"{int(pr['new_within_s'] // 3600)} h, conversations first) on {pr['role']} "
                              f"({pr['label']}), capped at ${float(self.roles[pr['role']]['daily_cap_usd']):.2f} a "
@@ -143,7 +153,8 @@ class DownSignal:
         self.probe_kw, self.note_family = {}, False
         try:
             self.hh = load_module(self.module_path)
-            self.state_path = state_path or self.hh.STATE
+            self.state_path = state_path or paths["signal_state"]    # the watcher's own (the 10:50 order (3)),
+                                                                     # never the module's shared STATE
             self.up = next(m for m in self.hh.MODES if m != DOWN)
             try:                                     # the builder's probe_due CLAIMS its slot and names the claimer
                 takes_who = "who" in inspect.signature(self.hh.probe_due).parameters   # (pp-selectid 11ed255f,
@@ -152,9 +163,8 @@ class DownSignal:
             # probe_kw: the name this watcher's claims carry (the state's last_probe_by names whoever won the latest
             # slot). Without it the fallback is said once (audit r87claim c2, its condition), never silent.
             self.probe_kw = {"who": WHO + " probe"} if takes_who else {}
-            fams = sorted({f for f in map(self._family, self.router.chain(self.probe_role)) if f})
-            if fams and _takes(self.hh.probe_due, "families"):   # RULING 87 AMENDED (pp-selectid audit 1008): the
-                self.probe_kw["families"] = fams                  # families this watcher's probe asks
+            # no `families` (pp-selectid audit 1008 kept a slot for the prober that could ask a failed family): the
+            # state file is this watcher's own, so no other prober would take a slot left to it (the 10:50 order (3))
             self.note_family = _takes(self.hh.note, "family")    # each failure noted with its family
             if not takes_who:
                 self.log("RULING 87: the shared module's probe_due takes no `who`: this watcher's probes are not "
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index bf7d6d73..7407de55 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -2,13 +2,26 @@
 
 Captions go into the staging store through transcript_store's own writer (fetch_captions -> _make_record -> _store,
 attempts via _log_attempt), so the record format is the pipeline's by construction. meta.json is written once, ONLY
-when the video is a VOD with English captions listed (INGEST-FAIL-01: a meta written while live froze 46 videos);
-meta_record() has every key transcript_store.ensure_meta writes (tests/ingest/test_fetch.py checks parity) and dates a
-livestream VOD by its stream start (INGEST-FAIL-03). No Whisper, no GPU.
+when the video is a VOD with English captions listed or with the pipeline's own transcript (INGEST-FAIL-01: a meta
+written while live froze 46 videos); meta_record() has every key transcript_store.ensure_meta writes
+(tests/ingest/test_fetch.py checks parity) and dates a livestream VOD by its stream start (INGEST-FAIL-03). No Whisper,
+no GPU.
+
+THE PIPELINE'S OWN TRANSCRIPT (the orchestrator's 10:50 ET order of Nov 16, (1)): from 07:47 ET that day YouTube
+answered HTTP 429 to every caption download from this machine, so no video reached the miner for three hours, while
+the main tree's own transcript ingest (cron, every 30 min: captions, else Whisper on its GPU) had already transcribed
+most of them. Before any caption download, and when a VOD lists no English captions, the video's record in the
+pipeline's store (config.MAIN_STORE, READ ONLY) is taken when one passes every check (it names this video and this
+channel; its segments hash to its transcript_sha256): copied byte for byte into this store, write-once, the copy
+checked again. A caption 429 stops the captions only (transcript_store's own 30-minute caption breaker): the probe and
+the listing, which YouTube still answered, go on, and a throttled video is tried again in CAPTION_THROTTLED_RETRY_S,
+the pipeline's store looked at first each time.
 """
+import glob
 import hashlib
 import json
 import os
+import shutil
 from datetime import datetime, timezone
 
 from . import config
@@ -21,6 +34,22 @@ UNAVAILABLE_MARKS = ("Private video", "Video unavailable", "This video has been
 UNAVAILABLE_RETRY_S = 6 * 3600
 UNAVAILABLE_MAX_TRIES = 4
 PROBE_RETRY_S = (300, 900, 1800, 3600)
+CAPTION_THROTTLED_RETRY_S = 600     # a caption 429: tried again this soon (the pipeline's store is looked at first)
+PIPELINE_RECHECK_S = 1800           # a VOD without English captions inside its moments' life: looked at this often
+                                    # (the pipeline's transcript ingest runs every 30 min)
+PIPELINE_STORE = os.path.join(config.MAIN_STORE, "transcripts")     # the pipeline's own transcripts: READ ONLY
+PIPELINE_CIRCUIT = os.path.join(config.MAIN_STORE, "state", "caption_circuit.json")   # its caption 429 breaker: read
+                                    # only (both ingests download captions from this one machine)
+
+
+def pipeline_captions_refused(now_ts):
+    """True while the pipeline's own caption breaker is open (its ingest was answered HTTP 429 in the last 30 min):
+    YouTube refuses this machine, so no caption download is tried here either. A file missing or unreadable: False."""
+    try:
+        with open(PIPELINE_CIRCUIT) as f:
+            return float(json.load(f).get("open_until", 0)) > now_ts
+    except (OSError, ValueError, TypeError, AttributeError):
+        return False
 
 
 def _dt(epoch):
@@ -112,9 +141,74 @@ def _retry_at(now_ts, tries):
 
 
 def _caption_retry_at(now_ts, published_ts, tries):
-    if tries < len(config.CAPTION_RETRY_S):
-        return now_ts + config.CAPTION_RETRY_S[tries]
-    return now_ts + 7200
+    """+10, +20, +40, +80 min, then every 2 h; inside the video's moments' life (config.EXPIRY_H) at most
+    PIPELINE_RECHECK_S apart, so the pipeline's own transcript is taken within one run of its ingest."""
+    d = config.CAPTION_RETRY_S[tries] if tries < len(config.CAPTION_RETRY_S) else 7200
+    if published_ts is not None and now_ts - published_ts < config.EXPIRY_H * 3600:
+        d = min(d, PIPELINE_RECHECK_S)
+    return now_ts + d
+
+
+def pipeline_transcript(vid, channel_id, root=None):
+    """The video's best record in the pipeline's own transcript store (READ ONLY; transcript_store's rank: Whisper over
+    manual over automatic captions) that names this video and this channel, is filed under its own method and whose
+    segments hash to its transcript_sha256: (path, record), or None. A record failing any check is never taken."""
+    ts = config.ts()
+    ts._vdir(vid)                                     # the id's own check (ValueError): no path outside the store
+    best = None
+    for p in sorted(glob.glob(os.path.join(root or PIPELINE_STORE, vid, "transcript.*.json"))):
+        try:
+            with open(p) as f:
+                rec = json.load(f)
+            method = rec.get("transcript_method") if isinstance(rec, dict) else None
+            ok = (isinstance(method, str) and os.path.basename(p) == f"transcript.{method.split(':')[0]}.json"
+                  and rec.get("video_id") == vid and rec.get("channel_id") == channel_id
+                  and isinstance(rec.get("segments"), list) and len(rec["segments"]) > 0
+                  and ts.segments_sha256(rec["segments"]) == rec.get("transcript_sha256"))
+        except (OSError, ValueError, KeyError, TypeError, AttributeError):
+            ok = False
+        if ok:
+            rank = ts.METHOD_RANK.get(method.split(":")[0], 0)
+            if best is None or rank > best[0]:
+                best = (rank, p, rec)
+    return (best[1], best[2]) if best else None
+
+
+def take_pipeline_transcript(q, vid, channel_id, root=None):
+    """The pipeline's own transcript (pipeline_transcript) copied into this store byte for byte, write-once, the copy
+    checked again before it is linked in: True when this store holds it (a record of that method already here is
+    kept, never replaced). Said in the video's attempts log and as a queue event."""
+    found = pipeline_transcript(vid, channel_id, root)
+    if found is None:
+        return False
+    src, rec = found
+    ts = config.ts()
+    dst = os.path.join(ts._vdir(vid), os.path.basename(src))
+    if os.path.exists(dst):
+        return True
+    os.makedirs(os.path.dirname(dst), exist_ok=True)
+    tmp = f"{dst}.{os.getpid()}.tmp"
+    try:
+        shutil.copyfile(src, tmp)
+        with open(tmp) as f:
+            got = json.load(f)
+        if got.get("transcript_sha256") != rec["transcript_sha256"] or \
+                ts.segments_sha256(got["segments"]) != rec["transcript_sha256"]:
+            ts._log_attempt(vid, step="transcript", status="pipeline_store_copy_refused", source=src,
+                            writer="pipeline.ingest")
+            return False                              # the bytes copied are not the record checked: not taken
+        try:
+            os.link(tmp, dst)
+        except FileExistsError:
+            return True
+    finally:
+        if os.path.exists(tmp):
+            os.unlink(tmp)
+    ts._log_attempt(vid, step="transcript", status="taken_from_pipeline_store", source=src,
+                    method=rec["transcript_method"], transcript_sha256=rec["transcript_sha256"], writer="pipeline.ingest")
+    q.event("pipeline_transcript", vid, channel_id, source=src, method=rec["transcript_method"],
+            transcript_sha256=rec["transcript_sha256"])
+    return True
 
 
 def process(q, gate, v, chan, optout, now_ts=None):
@@ -189,6 +283,8 @@ def process(q, gate, v, chan, optout, now_ts=None):
         q.set_state(vid, Q.DUPLICATE, next_at=now_ts + 10 ** 9, duplicate_of=dup, title_canon=tc,
                     reason=f"re-upload of {dup}: {why}", **common)
         return Q.DUPLICATE
+    if take_pipeline_transcript(q, vid, chan["channel_id"]):    # the pipeline's own transcript: no caption download
+        return _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries)
     manual, auto = captions_listed(j)
     if not (any(k.startswith("en") for k in manual) or auto):
         if now_ts - pub_ts > config.CAPTION_DEADLINE_H * 3600:
@@ -222,15 +318,21 @@ def _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries):
             q.set_state(vid, Q.CAPTIONS_PENDING, next_at=now_ts + wait + 60, title_canon=tc,
                         reason=f"captions: the yt-dlp breaker is open for {wait:.0f} s", **common)
             return Q.CAPTIONS_PENDING
-        with gate.sem:
-            status, rec = ts.fetch_captions(meta, os.path.join(paths["work"], "captions_tmp"))
-        ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest")
-        if status == "throttled" and getattr(gate, "trip", None):
-            gate.trip("captions: throttled")       # a caption download's rate limit stops every yt-dlp call
-        if status != "ok":
-            nxt = now_ts + 1800 if status == "throttled" else _caption_retry_at(now_ts, common["published_ts"], tries)
+        if pipeline_captions_refused(now_ts):      # the pipeline's ingest was just refused: no request from here
+            status, rec = "throttled", None
+            ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest",
+                            why="the pipeline's own caption breaker is open (HTTP 429): no download tried")
+        else:
+            with gate.sem:
+                status, rec = ts.fetch_captions(meta, os.path.join(paths["work"], "captions_tmp"))
+            ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest")
+        if status != "ok":                         # a 429 stops the captions alone (transcript_store's own breaker):
+            throttled = status == "throttled"      # never the probe's and the listing's gate (the 10:50 order (1))
+            nxt = now_ts + CAPTION_THROTTLED_RETRY_S if throttled else \
+                _caption_retry_at(now_ts, common["published_ts"], tries)
             q.set_state(vid, Q.CAPTIONS_PENDING, next_at=nxt, tries=tries + 1, title_canon=tc,
-                        reason=f"captions {status}", **common)
+                        reason="captions throttled (HTTP 429; the pipeline's own transcript is looked for at each "
+                               "retry)" if throttled else f"captions {status}", **common)
             return Q.CAPTIONS_PENDING
         if not os.path.exists(mpath):
             ts._write_once(mpath, meta)
diff --git a/pipeline/ingest/providers.json b/pipeline/ingest/providers.json
index 26abe209..c8ec71be 100644
--- a/pipeline/ingest/providers.json
+++ b/pipeline/ingest/providers.json
@@ -5,7 +5,7 @@
   "spend_freeze": {
     "vendors": ["openai", "anthropic", "xai", "google"],
     "since": "2026-11-12T05:30:00-05:00",
-    "order": "orchestrator 05:30 ET Nov 12: SPEND FREEZE on paid frontier vendors (OpenAI, Anthropic, xAI) until told otherwise; the watcher's chain is Heimdall then the local interface only; if both are down the videos queue and are mined later, never on a paid frontier model. Google (Gemini) is frozen as a paid frontier vendor too (STATE assumption A10). A frozen vendor's back-end is never called by any role (providers.Router); a stored validated reply costs nothing and may be reused. Lift: remove the vendor here and restart the watcher."
+    "order": "orchestrator 05:30 ET Nov 12: SPEND FREEZE on paid frontier vendors (OpenAI, Anthropic, xAI) until told otherwise; the watcher's chain is Heimdall then the local interface only; if both are down the videos queue and are mined later, never on a paid frontier model. Google (Gemini) is frozen as a paid frontier vendor too (STATE assumption A10). A frozen vendor's back-end is never called by any role (providers.Router); a stored validated reply costs nothing and may be reused. Lift: remove the vendor here and restart the watcher. Ruling 118 (orchestrator 10:50 ET Nov 16, from PBX 05:25 ET): outside vendors are capped at $1.00 a day for the whole pipeline, so ruling 98's paid route for the miner (Grok, then Gemini) is CLOSED: removed from this file (paid_route, the mine_paid role)."
   },
   "env_file": "/home/ultron/protocol_pulse/.env",
   "backends": {
@@ -26,7 +26,8 @@
       "price": {"in_per_mtok": 0.0465, "out_per_mtok": 0.713, "basis": "GET /models pricing 2026-11-12"}
     },
     "heimdall_glm53flash": {
-      "kind": "openai_compat", "vendor": "heimdall", "family": "glm", "enabled": true,
+      "kind": "openai_compat", "vendor": "heimdall", "family": "glm", "enabled": false,
+      "disabled_by": "ruling 119 (3) (orchestrator 10:50 ET Nov 16): glm is out of every chain",
       "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
       "model": "z-ai/glm-5.3-flash", "key_env_prefix": "HEIMDALL_API_KEY",
       "note": "a model family other than the miner's, for checks of the miner's labels (ruling 40, 2026-11-13); short prompts only. Its default reasoning: 24/24 on the flag-check calibration quotes (about 300 reply tokens, median 26 s); at effort none 21/24 (a yes to a speaker's own purchase, a historical fact and a prediction), at effort low 22/24 (2026-11-13). On a 111k-token review package its default reasoning used a whole 16k reply budget (freeze audit c1: empty content). Timeout 300 s: at 8 in flight its replies took p50 5 s but p90 74 s, and a quarter of the first 110 questions ran past 120 s (a timed-out request restarts from zero and, at temperature 0, reasons the same way again).",
@@ -45,13 +46,53 @@
       "price": {"in_per_mtok": 0.186, "out_per_mtok": 0.744, "basis": "GET /models pricing 2026-11-13"}
     },
     "heimdall_deepseek": {
-      "kind": "openai_compat", "vendor": "heimdall", "family": "deepseek", "enabled": false,
+      "kind": "openai_compat", "vendor": "heimdall", "family": "deepseek", "enabled": true,
       "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
       "model": "deepseek/deepseek-v4.1-flash", "key_env_prefix": "HEIMDALL_API_KEY",
       "extra_body": {"reasoning": {"effort": "low"}},
-      "json_schema": false, "max_inflight": 6, "timeout_s": 300,
+      "note": "ruling 118 (orchestrator 10:50 ET Nov 16): the miner's Plan B is the next Heimdall model of the chain (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model under the lease: the chain's second model",
+      "json_schema": true, "max_inflight": 6, "timeout_s": 300,
       "cost_from_usage": true, "spend_meter": true,
-      "price": {"in_per_mtok": 0.3, "out_per_mtok": 1.2, "basis": "estimate"}
+      "price": {"in_per_mtok": 0.062, "out_per_mtok": 0.186, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_minimax": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "minimax", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "minimax/minimax-m3.1-flash", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 118 (orchestrator 10:50 ET Nov 16): the miner's Plan B is the next Heimdall model of the chain (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model under the lease: the chain's third model",
+      "json_schema": true, "max_inflight": 6, "timeout_s": 300,
+      "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.0465, "out_per_mtok": 0.186, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_gemma": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "gemma", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "google/gemma-4-31b-it", "key_env_prefix": "HEIMDALL_API_KEY",
+      "note": "ruling 118 (orchestrator 10:50 ET Nov 16): the miner's Plan B is the next Heimdall model of the chain (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model under the lease: the chain's fourth model (served by Heimdall: not a frozen vendor)",
+      "json_schema": true, "max_inflight": 6, "timeout_s": 240,
+      "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.031, "out_per_mtok": 0.124, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_gptoss": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "gpt-oss", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "openai/gpt-oss-20b", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 118 (orchestrator 10:50 ET Nov 16): the miner's Plan B is the next Heimdall model of the chain (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model under the lease: the chain's fifth model (served by Heimdall: not a frozen vendor)",
+      "json_schema": true, "max_inflight": 6, "timeout_s": 240,
+      "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.031, "out_per_mtok": 0.124, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_mimo": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "mimo", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "xiaomi/mimo-v2.6-flash-rl", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 118 (orchestrator 10:50 ET Nov 16): the miner's Plan B is the next Heimdall model of the chain (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model under the lease: the chain's sixth model",
+      "json_schema": true, "max_inflight": 6, "timeout_s": 300,
+      "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.0434, "out_per_mtok": 0.0868, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
     },
     "anthropic_frontier": {
       "kind": "anthropic", "vendor": "anthropic", "enabled": true, "model": "claude-opus-5-5", "key_env": "ANTHROPIC_API_KEY",
@@ -84,8 +125,53 @@
       "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
       "price": {"in_per_mtok": 0.0465, "out_per_mtok": 0.713, "basis": "GET /models pricing 2026-11-12"}
     },
+    "heimdall_deepseek_probe": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "deepseek", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "deepseek/deepseek-v4.1-flash", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 87's probe only (the probe role): the mine chain's second family (ruling 118), 60 s deadline, one in flight",
+      "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.062, "out_per_mtok": 0.186, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_minimax_probe": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "minimax", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "minimax/minimax-m3.1-flash", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 87's probe only (the probe role asks one back-end per family this watcher calls): a family of the mine chain (ruling 118), 60 s deadline, one in flight",
+      "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.0465, "out_per_mtok": 0.186, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_gemma_probe": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "gemma", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "google/gemma-4-31b-it", "key_env_prefix": "HEIMDALL_API_KEY",
+      "note": "ruling 87's probe only (the probe role asks one back-end per family this watcher calls): a family of the mine chain (ruling 118), 60 s deadline, one in flight",
+      "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.031, "out_per_mtok": 0.124, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_gptoss_probe": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "gpt-oss", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "openai/gpt-oss-20b", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 87's probe only (the probe role asks one back-end per family this watcher calls): a family of the mine chain (ruling 118), 60 s deadline, one in flight",
+      "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.031, "out_per_mtok": 0.124, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
+    "heimdall_mimo_probe": {
+      "kind": "openai_compat", "vendor": "heimdall", "family": "mimo", "enabled": true,
+      "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
+      "model": "xiaomi/mimo-v2.6-flash-rl", "key_env_prefix": "HEIMDALL_API_KEY",
+      "extra_body": {"reasoning": {"effort": "low"}},
+      "note": "ruling 87's probe only (the probe role asks one back-end per family this watcher calls): a family of the mine chain (ruling 118), 60 s deadline, one in flight",
+      "max_inflight": 1, "timeout_s": 60, "cost_from_usage": true, "spend_meter": true,
+      "price": {"in_per_mtok": 0.0434, "out_per_mtok": 0.0868, "basis": "GET /models pricing 2026-11-15 (pp-selectid replay110 GATEWAY_MODELS.json)"}
+    },
     "heimdall_glm53flash_probe": {
-      "kind": "openai_compat", "vendor": "heimdall", "family": "glm", "enabled": true,
+      "kind": "openai_compat", "vendor": "heimdall", "family": "glm", "enabled": false,
+      "disabled_by": "ruling 119 (3) (orchestrator 10:50 ET Nov 16): glm is out of every chain",
       "base_url": "https://api-staging.heimdallm.com/api/v1", "base_url_env": "PP_INGEST_HEIMDALL_BASE",
       "model": "z-ai/glm-5.3-flash", "key_env_prefix": "HEIMDALL_API_KEY",
       "note": "ruling 87's probe only (the probe role): a second Heimdall family, 60 s deadline, one in flight",
@@ -102,31 +188,24 @@
       "price": {"in_per_mtok": 0.186, "out_per_mtok": 0.744, "basis": "GET /models pricing 2026-11-13"}
     }
   },
-  "paid_route": {
-    "role": "mine_paid", "after_down_s": 1200, "new_within_s": 21600, "recheck_within_s": 43200,
-    "conversation_tpm": 1.0, "label": "GROK, THEN GEMINI",
-    "note": "ruling 98 (orchestrator 06:13 ET Nov 14, PBX's fail-safe of 21:08 Nov 13 'if [Heimdall] ever fails to respond for more than perhaps 10 to 20 minutes ... use Groc mainly or whatever other AI tokens we have'): when the shared signal (down_signal) says plan_b AND no family of its vendor has answered for after_down_s (20 min) running, the miner mines NEW uploads only (published in the last new_within_s, 6 h; conversations first (caption turns per minute >= conversation_tpm), then newest; no backfill; no hook pass) on the role above, until the signal is back (3 good probes). Every row carries miner_route (the role that mined it). When the signal is back, a video mined on the paid route and published within recheck_within_s (12 h, its moments' life) is mined again on the mine role, and every moment both found carries the flags of both (ledger.carry_forward)."
-  },
   "down_signal": {
     "vendor": "heimdall", "probe_role": "probe", "label": "HEIMDALL",
     "module": "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py",
-    "note": "ruling 87 (orchestrator 21:18 Nov 13): ONE shared 'Heimdall down' signal for the builder and this watcher (pp-selectid pipeline/heimdall_health.py, its state file under an flock). Every call of this watcher to a back-end of this vendor is noted there (answered: ok or invalid; not answered: every other outcome of a real call; a stored reply, a missing key or a probe call is no note; a back-end under a runtime base_url override is a drill: drill=True, never counted). The probe role is asked while the shared state says a probe is due (any answer counts). The miner's Plan B under the 05:30 Nov 12 spend freeze: queue and wait (the mine chain as it is)."
+    "note": "ruling 87 as amended by the orchestrator's 10:50 ET order of Nov 16 (3): the outage clock is fed only by this watcher's OWN mining and probe calls, never by another session's deadline misses, and any answered call or probe resets it: the builder's module (pp-selectid pipeline/heimdall_health.py, its API only) runs on this watcher's own state file (config.paths()['signal_state'], under the module's flock), no longer the one file shared with the builder (ruling 87 of 21:18 Nov 13). Every call of this watcher to a back-end of this vendor is noted there (answered: ok or invalid; not answered: every other outcome of a real call; a stored reply, a missing key or a probe call is no note; a back-end under a runtime base_url override is a drill: drill=True, never counted). The probe role is asked while its state says a probe is due (any answer counts). The miner's Plan B (ruling 118): the mine chain as it is (the next Heimdall model, then the local model under the lease), else the videos wait; no paid route."
   },
   "roles": {
-    "mine": {"chain": ["heimdall_qwen27b", "local_gemma"],
-             "attempts": 3, "max_tokens": 4000},
+    "mine": {"chain": ["heimdall_qwen27b", "heimdall_deepseek", "heimdall_minimax", "heimdall_gemma", "heimdall_gptoss", "heimdall_mimo", "local_gemma"],
+             "attempts": 3, "max_tokens": 4000,
+             "note": "ruling 118 (orchestrator 10:50 ET Nov 16): outside vendors are capped at $1.00 a day for the whole pipeline, so the miner's paid route is closed; its Plan B is the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the local model on a free card under the lease (local_gemma: only while this process holds the GPU lease)"},
     "judge": {"chain": ["xai_frontier", "gemini_frontier", "anthropic_frontier"], "attempts": 2, "max_tokens": 8000},
-    "hook": {"chain": ["heimdall_qwen27b", "local_gemma"], "attempts": 3, "max_tokens": 3000,
+    "hook": {"chain": ["heimdall_qwen27b", "heimdall_deepseek", "heimdall_minimax", "heimdall_gemma", "heimdall_gptoss", "heimdall_mimo", "local_gemma"], "attempts": 3, "max_tokens": 3000,
              "note": "ruling 80 (2026-11-13 18:42 ET): the hook pass, a second mining question over the same windows (mine.HOOK_PROMPT); the mine role's chain under the spend freeze"},
-    "spotlight": {"chain": ["heimdall_qwen27b", "local_gemma"], "attempts": 3, "max_tokens": 3000,
+    "spotlight": {"chain": ["heimdall_qwen27b", "heimdall_deepseek", "heimdall_minimax", "heimdall_gemma", "heimdall_gptoss", "heimdall_mimo", "local_gemma"], "attempts": 3, "max_tokens": 3000,
                   "note": "the orchestrator's 08:15 ruling 2 (2026-11-14; ruling 92 (c)): the spotlight question (mine.SPOT_PROMPT), asked in the hook pass of conversation episodes only; the hook role's chain"},
-    "flagcheck": {"chain": ["heimdall_glm53flash", "heimdall_muse"], "attempts": 2, "max_tokens": 4000,
+    "flagcheck": {"chain": ["heimdall_muse", "heimdall_deepseek"], "attempts": 2, "max_tokens": 4000,
+                  "ruling_119": "glm out of every chain (ruling 119 (3), 10:50 ET Nov 16): muse first (calibrated), deepseek second (answers only once the watcher's live calibration passes it)",
                   "note": "ruling 40 (2026-11-13): a second model, never one that mined the row's video, answers one narrow question per hard flag (pipeline/ingest/flagcheck.py). A measurement: the adapter's exclusions do not read it."},
-    "mine_paid": {"chain": ["xai_frontier", "gemini_frontier"], "attempts": 2, "max_tokens": 4000,
-                  "freeze_lifted": "ruling 98 (orchestrator 06:13 ET Nov 14): the miner's Plan B; the Nov 12 spend freeze is lifted for this one route and this cap only",
-                  "daily_cap_usd": 2.0, "cap_reserve_usd": 0.25,
-                  "note": "ruling 98: Grok first, then the Gemini key (fenced to this pipeline: allowed); others only if a probe shows credit (none wired). Used only while paid_route is open. The cap is per ET day across both back-ends, counted from each call's recorded cost (xAI's own usage.cost_in_usd_ticks; Gemini reports none: its price-table estimate counts), with cap_reserve_usd held for every call in flight so the calls never start past it; then the videos queue and wait."},
-    "probe": {"chain": ["heimdall_qwen27b_probe", "heimdall_glm53flash_probe", "heimdall_muse_probe"], "attempts": 1,
+    "probe": {"chain": ["heimdall_qwen27b_probe", "heimdall_deepseek_probe", "heimdall_minimax_probe", "heimdall_gemma_probe", "heimdall_gptoss_probe", "heimdall_mimo_probe", "heimdall_muse_probe"], "attempts": 1,
               "max_tokens": 512, "transport_retries": 0, "breaker": false,
               "note": "ruling 87, amended by the orchestrator at 10:05 ET Nov 14 (a probe is a real model call on the family that failed and one other, never a ping; any answered probe resets the clock): the cheap probe while Heimdall calls fail (and in Plan B): EVERY back-end here (one per family this watcher calls) is asked at once, one call each, any answer is the probe's answer, and an answered probe is noted as an answer; never from a stored reply (use_cache False), never held back by a breaker (breaker false: it is the breaker's evidence, not its patient), no transport retry (each back-end's 60 s deadline is the probe's). 512 tokens: room for the second family's default reasoning."}
   },
diff --git a/pipeline/ingest/service.py b/pipeline/ingest/service.py
index 64e4e214..2a5f183b 100644
--- a/pipeline/ingest/service.py
+++ b/pipeline/ingest/service.py
@@ -50,8 +50,8 @@ import traceback
 from concurrent.futures import ThreadPoolExecutor
 from datetime import datetime, timedelta, timezone
 
-from . import batch, config, coverage, cycles, downsignal, fetch, flagcheck, ledger, mine, providers, purge, spend, stats, \
-    watch
+from . import batch, config, coverage, cycles, downsignal, fetch, flagcheck, ledger, mine, providers, purge, spend, \
+    stall, stats, watch
 from . import queue as Q
 from .contract import ContractUnavailable
 
@@ -143,6 +143,7 @@ class Service:
         self.check_recal_s = CHECK_RECALIBRATE_S        # the wait before the next calibration (set by each one)
         self.cycles_error = None                         # the cycles line's last failure (logged once per cause)
         self.batch_error = None                          # ruling 108: the batch line's last failure (logged once)
+        self.stall_error = None                          # the 10:50 order (4): the stall line's last failure (once)
         self._reuse_tried = False                       # the start's one look at the stored live calibration
         self.stop = threading.Event()
         self.rss_mode, self.rss_checked = False, 0.0
@@ -752,6 +753,7 @@ class Service:
         self._outage_notice(now)
         self._cycles_notice(now)
         self._batch_notice(now)
+        self._stall_notice(now)
         day = config.iso()[:10]
         hour = datetime.now(timezone.utc).hour
         if force_coverage or (hour >= COVERAGE_HOUR_UTC and self.q.kv_get("coverage_day") != day and
@@ -802,6 +804,41 @@ class Service:
                 self.log(f"ruling 108: the batch line could not be written: {why}")
             self.batch_error = why
 
+    def _stall_notice(self, now):
+        """The orchestrator's 10:50 ET order of Nov 16 (4), the self-check (stall.py): videos waiting and nothing mined
+        for stall.STALL_S: said at the front of STATE line 1 and acted on (the waiting videos made due now) when found
+        and every STALL_S while it lasts; removed when it ends. A failure is logged once per cause and never stops the
+        health loop."""
+        try:
+            chk = stall.check(self.q, now)
+            if chk["stalled"]:
+                if self.q.kv_get("stall_since") != repr(chk["since"]):
+                    self.q.kv_set("stall_since", repr(chk["since"]))
+                    self.q.kv_set("stall_acted", "")
+                    self.q.event("stall", None, None, since=chk["since"], waiting=len(chk["waiting"]))
+                acted = self.q.kv_get("stall_acted") or ""
+                if not acted or now - float(acted) >= stall.STALL_S:
+                    n = stall.act(self.q, chk, now)
+                    self.q.kv_set("stall_acted", repr(now))
+                    self.q.kv_set("stall_acted_n", str(n))
+                    self.q.event("stall_act", None, None, waiting=len(chk["waiting"]), made_due=n)
+                    self.log(f"the 10:50 order (4): {len(chk['waiting'])} video(s) waiting and nothing mined since "
+                             f"{chk['since']:.0f}: {n} made due now")
+                line = stall.line(chk, now, float(self.q.kv_get("stall_acted")), int(self.q.kv_get("stall_acted_n")))
+                spend.write_stall_notice(line, notify_path=self.p["notify"])
+            else:
+                if self.q.kv_get("stall_since"):
+                    self.q.event("stall_over", None, None, since=self.q.kv_get("stall_since"))
+                    self.log("the 10:50 order (4): the stall is over (mined again, or nothing waits)")
+                spend.write_stall_notice(None, notify_path=self.p["notify"])   # STATE first, then the record (a
+                self.q.kv_set("stall_since", "")                              # file not written is tried again)
+            self.stall_error = None
+        except Exception as e:                       # noqa: BLE001 (a report line never stops the watcher)
+            why = f"{type(e).__name__}: {str(e)[:200]}"
+            if why != self.stall_error:
+                self.log(f"the 10:50 order (4): the stall line could not be written: {why}")
+            self.stall_error = why
+
     def _purge_blocked(self, why):
         """A purge that cannot run safely: once it has lasted PURGE_NOTICE_S, a line at the top of STATE (audit r77
         c1, muse P1); cleared by the first pass that runs."""
diff --git a/pipeline/ingest/spend.py b/pipeline/ingest/spend.py
index e95d2df6..c8a7cc29 100644
--- a/pipeline/ingest/spend.py
+++ b/pipeline/ingest/spend.py
@@ -28,35 +28,45 @@ SIGNAL_RE = re.compile(r"^[A-Z0-9_-]+ " + SIGNAL_SUFFIX)    # any label's: only
 BATCH_PATTERN = r"BATCH \d+ ingest spend: "   # ruling 108: pp-ingest's spend in the batch, FIRST on STATE line 1
 BATCH_RE = re.compile("^" + BATCH_PATTERN)
 ALARM_PREFIX = "ALARM FOR PBX: "              # ruling 106 (d): on line 1, after the batch spend; the integrator sends it
-SEP = " | "                                   # line 1's notices, joined: the batch spend, an alarm, the switch line
+STALL_PREFIX = "MINING STALLED SINCE "        # the 10:50 order (4) of Nov 16: on line 1, after the batch spend and an alarm
+SEP = " | "                                   # line 1's notices, joined: the batch spend, an alarm, the stall, the switches
 NOTICE_RE = re.compile(r"^(?:[A-Z0-9_-]+ SPEND (?:AT 90%|UNMEASURED)|" + OUTAGE_PREFIX + "|" + PURGE_PREFIX + "|" +
                        CYCLES_PREFIX + " TO |" + r"[A-Z0-9_-]+ " + SIGNAL_SUFFIX + "|" + SWITCH_PATTERN + ")")
-LINE1_RE = re.compile("^(?:" + BATCH_PATTERN + "|" + re.escape(ALARM_PREFIX) + ")")   # only ever the first line: a
-                                                                                       # session line that happens to
-                                                                                       # start so is never a notice
+LINE1_RE = re.compile("^(?:" + BATCH_PATTERN + "|" + re.escape(ALARM_PREFIX) + "|" + re.escape(STALL_PREFIX) + ")")
+# LINE1_RE: only ever the first line: a session line that happens to start so is never a notice
 
 
 def notice_prefixes(label):
     return (f"{label} SPEND AT 90%", f"{label} SPEND UNMEASURED")
 
 
+def _front(h):
+    """A notice that is one segment at the front of line 1: the batch spend, an alarm, the stall (its writer refuses a
+    '|', so each ends at the first SEP)."""
+    return bool(BATCH_RE.match(h)) or h.startswith(ALARM_PREFIX) or h.startswith(STALL_PREFIX)
+
+
 def _segments(h):
-    """STATE line 1 as its notices: the batch spend and an alarm at its front (in any order: a hand edit too, audit
-    b108 c1), then ruling 87's switch line, joined by SEP. The batch and alarm notices never hold a '|' (their
-    writers refuse one), so each ends at the first SEP; the rest is the switch line; any other first line is one
-    notice."""
+    """STATE line 1 as its notices: the batch spend, an alarm and the stall at its front (in any order: a hand edit
+    too, audit b108 c1), then ruling 87's switch line, joined by SEP. Those three never hold a '|' (their writers
+    refuse one), so each ends at the first SEP; the rest is the switch line; any other first line is one notice."""
     out, rest = [], h
-    while rest and (BATCH_RE.match(rest) or rest.startswith(ALARM_PREFIX)):
+    while rest and _front(rest):
         seg, _, rest = rest.partition(SEP)
         out.append(seg)
     return out + ([rest] if rest else [])
 
 
+LINE1_LAST = 3                                 # _place of the last kind on line 1 (the switch line)
+
+
 def _place(h):
-    """The order of the leading block: line 1 (the batch spend, an alarm, the switches: ruling 108, ruling 106 (d),
-    ruling 87), then the cycles line (the 08:15 order: right under line 1, audit cyc c2), then every other notice."""
-    return (0 if BATCH_RE.match(h) else 1 if h.startswith(ALARM_PREFIX) else 2 if SWITCH_RE.match(h) else
-            3 if h.startswith(CYCLES_PREFIX + " TO ") else 4)
+    """The order of the leading block: line 1 (the batch spend, an alarm, the stall, the switches: ruling 108, ruling
+    106 (d), the 10:50 order (4) of Nov 16, ruling 87), then the cycles line (the 08:15 order: right under line 1,
+    audit cyc c2), then every other notice."""
+    return (0 if BATCH_RE.match(h) else 1 if h.startswith(ALARM_PREFIX) else 2 if h.startswith(STALL_PREFIX) else
+            LINE1_LAST if SWITCH_RE.match(h) else LINE1_LAST + 1 if h.startswith(CYCLES_PREFIX + " TO ") else
+            LINE1_LAST + 2)
 
 
 def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
@@ -83,8 +93,8 @@ def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
         kept = [h for h in head if mine(h) and keep(h)][:1]
         others = [h for h in head if not mine(h)]
         block = sorted(([line] if line else []) + kept + others, key=_place)     # stable: each kind keeps its order
-        first = [h for h in block if _place(h) <= 2]
-        block = ([SEP.join(first)] if first else []) + [h for h in block if _place(h) > 2]
+        first = [h for h in block if _place(h) <= LINE1_LAST]
+        block = ([SEP.join(first)] if first else []) + [h for h in block if _place(h) > LINE1_LAST]
         new = "\n".join(block + lines)
         if new != text:
             tmp = f"{doc}.{os.getpid()}.{threading.get_ident()}.tmp"
@@ -122,6 +132,19 @@ def write_alarm_notice(sentence, since, doc=None, notify_path=None):
     return line
 
 
+def write_stall_notice(line, doc=None, notify_path=None):
+    """The orchestrator's 10:50 ET order of Nov 16 (4): 'MINING STALLED SINCE <time>: ...' (stall.line) on STATE line
+    1, after the batch spend and an alarm, while videos wait and nothing is mined; None removes it. One notice of line
+    1: never a '|' or a newline."""
+    if line is not None and (not line.startswith(STALL_PREFIX) or "\n" in line or "|" in line):
+        raise ValueError("not a stall line")
+    doc = doc or config.STATE_DOC
+    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
+    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
+    _rewrite_top(doc, lock_path, lambda h: h.startswith(STALL_PREFIX), line)
+    return line
+
+
 def write_cycles_notice(line, doc=None, notify_path=None):
     """The watcher's per-cycle line (cycles.compose: the orchestrator's 08:15 order of Nov 14) at the top of STATE,
     right under line 1; None removes it. Rewritten only when its text changes (_rewrite_top)."""
diff --git a/pipeline/ingest/stall.py b/pipeline/ingest/stall.py
new file mode 100644
index 00000000..7dab6f71
--- /dev/null
+++ b/pipeline/ingest/stall.py
@@ -0,0 +1,89 @@
+"""pipeline/ingest/stall.py: THE SELF-CHECK (the orchestrator's 10:50 ET order of Nov 16, (4)): "if videos are
+waiting and nothing has been mined for 30 minutes, write it on line 1 and act; do not sit idle at the prompt".
+
+WAITING  a video inside its moments' life (config.EXPIRY_H from its publish, or from its discovery while the publish
+         time is not measured yet) in a state that leads to mining: discovered, probing, probe_retry, captions_pending,
+         transcribed, mining, mine_waiting. An upcoming or live stream is not waiting (nothing to mine before its VOD);
+         a Short, a duplicate or any other terminal state never is.
+STALLED  something waits and nothing was mined for STALL_S: the later of the newest mined video's time and the oldest
+         waiting video's discovery is at least STALL_S old (a video that came in a minute ago is no stall).
+LINE     "MINING STALLED SINCE HH:MM ET: n VIDEO(S) WAITING, NOTHING MINED FOR 30 MIN OR MORE: k <why>, ...; ACTED HH:MM
+         ET: m MADE DUE NOW ..." at the front of STATE line 1 (spend.write_stall_notice, after the batch spend and an
+         alarm), its text stable while the stall lasts; removed when it ends.
+ACT      when the stall is found, and again every STALL_S while it lasts: every waiting video in a retry state whose
+         next try is later is made due now (the fetch step looks in the pipeline's own transcript store first, then
+         probes; the miner takes what is transcribed). Each act is an event and a log line (Service._stall_notice).
+"""
+from collections import Counter
+from datetime import datetime
+from zoneinfo import ZoneInfo
+
+from . import config
+from . import queue as Q
+from .spend import STALL_PREFIX
+
+STALL_S = 1800
+WAITING = (Q.DISCOVERED, Q.PROBING, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING, Q.MINE_WAIT)
+RETRYABLE = (Q.DISCOVERED, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.MINE_WAIT)   # never one in flight (probing, mining)
+ET = ZoneInfo("America/New_York")
+
+
+def why(state, reason):
+    """What one waiting video waits on, in a few words (from its state and the reason the queue recorded)."""
+    r = reason or ""
+    if state == Q.CAPTIONS_PENDING:
+        if r.startswith("captions throttled"):
+            return "CAPTIONS REFUSED BY YOUTUBE (HTTP 429)"
+        if r.startswith("captions: the yt-dlp breaker"):
+            return "CAPTIONS BEHIND THE YT-DLP BREAKER"
+        if r.startswith("VOD without English captions"):
+            return "NO ENGLISH CAPTIONS YET"
+        return "CAPTIONS TO RETRY"
+    if state == Q.PROBE_RETRY:
+        return "PROBE BEHIND THE YT-DLP BREAKER" if r.startswith("rate_limited") else "PROBE TO RETRY"
+    if state in (Q.DISCOVERED, Q.PROBING):
+        return "NOT PROBED YET"
+    if state in (Q.TRANSCRIBED, Q.MINING):
+        return "TRANSCRIBED, BEING MINED"
+    if state == Q.MINE_WAIT:
+        return "NO MODEL OF THE CHAIN ANSWERED" if r.startswith("OUTAGE") else "MINING TO RETRY"
+    return state.upper()
+
+
+def check(q, now, expiry_h=None, stall_s=STALL_S):
+    """{'stalled', 'waiting' (rows), 'since' (when the stall clock started; None when nothing waits), 'last_mined'}."""
+    horizon = now - float(config.EXPIRY_H if expiry_h is None else expiry_h) * 3600
+    marks = ",".join("?" * len(WAITING))
+    rows = q.rows(f"SELECT video_id, state, reason, next_at, discovered_ts FROM videos WHERE state IN ({marks}) AND "
+                  "COALESCE(published_ts, discovered_ts) >= ?", tuple(WAITING) + (horizon,))
+    last = q.rows("SELECT MAX(mined_ts) AS t FROM videos WHERE state IN (?, ?)", (Q.MINED, Q.MINED_PARTIAL))[0]["t"]
+    if not rows:
+        return {"stalled": False, "waiting": [], "since": None, "last_mined": last}
+    since = max(float(last or 0.0), min(float(r["discovered_ts"]) for r in rows))
+    return {"stalled": now - since >= stall_s, "waiting": rows, "since": since, "last_mined": last}
+
+
+def act(q, chk, now):
+    """Every waiting video in a retry state whose next try is later: due now. Returns how many."""
+    ids = [r["video_id"] for r in chk["waiting"] if r["state"] in RETRYABLE and float(r["next_at"] or 0) > now]
+    if ids:
+        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN ({','.join('?' * len(RETRYABLE))}) AND "
+            f"video_id IN ({','.join('?' * len(ids))})", (now, now) + tuple(RETRYABLE) + tuple(ids))
+    return len(ids)
+
+
+def _hm(t, now):
+    d = datetime.fromtimestamp(t, ET)
+    same_day = d.date() == datetime.fromtimestamp(now, ET).date()
+    return d.strftime("%H:%M ET") + ("" if same_day else d.strftime(" %b %d").upper())
+
+
+def line(chk, now, acted_at=None, acted_n=0, stall_s=STALL_S):
+    """The STATE line-1 notice for a stall (stable while it lasts: no running count of minutes)."""
+    n = len(chk["waiting"])
+    parts = ", ".join(f"{k} {w}" for w, k in sorted(Counter(why(r["state"], r["reason"]) for r in chk["waiting"])
+                                                    .items(), key=lambda kv: (-kv[1], kv[0])))
+    acted = (f"; ACTED {_hm(acted_at, now)}: {acted_n} MADE DUE NOW (THE PIPELINE'S OWN TRANSCRIPTS LOOKED FOR FIRST)"
+             if acted_at is not None else "")
+    return (f"{STALL_PREFIX}{_hm(chk['since'], now)}: {n} VIDEO(S) WAITING, NOTHING MINED FOR {int(stall_s // 60)} MIN "
+            f"OR MORE: {parts}{acted}")
diff --git a/tests/ingest/conftest.py b/tests/ingest/conftest.py
index 1dbe64f0..d4af192b 100644
--- a/tests/ingest/conftest.py
+++ b/tests/ingest/conftest.py
@@ -39,3 +39,15 @@ def _batch_in_tmp(tmp_path_factory, monkeypatch):
                              "share_usd": 1000.0, "share_of": "mining and checks"}))
     monkeypatch.setattr(batch, "SPEC", str(p))
     return p
+
+
+@pytest.fixture(autouse=True)
+def _pipeline_store_in_tmp(tmp_path_factory, monkeypatch):
+    """The 10:50 order (1) of Nov 16: the fetch step reads the pipeline's own transcript store and caption breaker (the
+    main tree's, READ ONLY). Every test reads its own empty ones, never the main tree's (a real video id there would
+    decide a test by the day it runs); a test that needs a record writes it here (fetch.PIPELINE_STORE)."""
+    from pipeline.ingest import fetch
+    d = tmp_path_factory.mktemp("pipeline_store")
+    monkeypatch.setattr(fetch, "PIPELINE_STORE", str(d / "transcripts"))
+    monkeypatch.setattr(fetch, "PIPELINE_CIRCUIT", str(d / "state" / "caption_circuit.json"))
+    return d
diff --git a/tests/ingest/test_audit_driver.py b/tests/ingest/test_audit_driver.py
index e7aaa997..d8d570fb 100644
--- a/tests/ingest/test_audit_driver.py
+++ b/tests/ingest/test_audit_driver.py
@@ -49,10 +49,10 @@ def test_the_package_is_the_diff_and_its_context_never_the_whole_files(monkeypat
 
 
 def test_the_reviewers_are_two_heimdall_families_and_a_third_only_by_name():
-    assert XA.chosen(None) == (["heimdall_qwen", "heimdall_glm"], {})
-    assert XA.chosen({"heimdall_muse"})[0] == ["heimdall_muse"]
-    run, skipped = XA.chosen({"grok", "heimdall_glm"})                         # pp-ingest's freeze holds
-    assert run == ["heimdall_glm"] and "spend freeze" in skipped["grok"]
+    assert XA.chosen(None) == (["heimdall_qwen", "heimdall_muse"], {})        # glm out (ruling 119 (3))
+    assert XA.chosen({"heimdall_mimo"})[0] == ["heimdall_mimo"]
+    run, skipped = XA.chosen({"grok", "heimdall_glm", "heimdall_qwen"})        # pp-ingest's freeze holds
+    assert run == ["heimdall_qwen"] and "spend freeze" in skipped["grok"] and "119 (3)" in skipped["heimdall_glm"]
     with pytest.raises(SystemExit):
         XA.chosen({"nobody"})
 
@@ -62,7 +62,7 @@ class Fake:
         self.rid = rid
 
     def complete(self, prompt, schema, max_tokens):
-        if self.rid == "heimdall_glm":
+        if self.rid == "heimdall_muse":
             raise providers.BackendError("timeout", "read timed out")          # abandoned: no cost reported
         return providers.Reply("P0: none", "m", "p", 1.0, {"prompt_tokens": 9000, "completion_tokens": 900}, 0.002,
                                "usage.cost", "stop")
@@ -76,7 +76,7 @@ def run_main(monkeypatch, out, *extra, cycle=1):
 
 def test_a_cycle_that_could_pass_the_cap_is_refused_before_any_call(monkeypatch, tmp_path):
     fake_git(monkeypatch)                                                     # 15 changed lines: the $0.30 cap
-    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (1e-5, 30), "heimdall_glm": (1e-5, 30)})
+    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (1e-5, 30), "heimdall_muse": (1e-5, 30)})
     (tmp_path / "audit").mkdir()
     (tmp_path / "audit" / "COST.json").write_text(json.dumps({"total_usd": 0.29, "cycles": {}}))
     with pytest.raises(SystemExit, match=r"REFUSED: this audit has spent \$0.2900 of its \$0.30 cap"):
@@ -86,7 +86,7 @@ def test_a_cycle_that_could_pass_the_cap_is_refused_before_any_call(monkeypatch,
 
 def test_every_review_is_booked_and_the_batch_line_reads_the_same_dollars(monkeypatch, tmp_path):
     fake_git(monkeypatch)
-    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (2e-7, 30), "heimdall_glm": (4e-8, 31)})
+    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (2e-7, 30), "heimdall_muse": (4e-8, 31)})
     monkeypatch.setattr(XA.providers, "make_backend", lambda rid, cfg, kr: Fake(rid))
     led = config.paths()["audit_spend"]
     if os.path.exists(led):
@@ -95,17 +95,17 @@ def test_every_review_is_booked_and_the_batch_line_reads_the_same_dollars(monkey
     cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
     rev = cost["cycles"]["c1"]["reviews"]
     assert rev["heimdall_qwen"] == {"usd": 0.002, "basis": "reported"}
-    assert rev["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)           # its own rate x the prompt the other
-    assert rev["heimdall_glm"]["basis"].startswith("abandoned: the model's own rate (31 reported reviews) x 9000")
+    assert rev["heimdall_muse"]["usd"] == pytest.approx(4e-8 * 9000)           # its own rate x the prompt the other
+    assert rev["heimdall_muse"]["basis"].startswith("abandoned: the model's own rate (31 reported reviews) x 9000")
     assert cost["total_usd"] == pytest.approx(0.002 + 4e-8 * 9000) and cost["cap_usd"] == 0.30
     usd, n, bad, booked = batch.audit_spend(led, 0, 4e9)                      # ruling 108's line: the same dollars
     assert (round(usd, 6), n, bad) == (round(cost["total_usd"], 6), 2, 0)
-    assert booked == pytest.approx(4e-8 * 9000)                                # glm's, at its own rate
+    assert booked == pytest.approx(4e-8 * 9000)                                # muse's, at its own rate
     (tmp_path / "audit" / "C1_CONSENSUS.md").write_text("consensus")
     run_main(monkeypatch, tmp_path / "audit" / "c2", "--c1", str(tmp_path / "audit" / "c1"), "--consensus",
              str(tmp_path / "audit" / "C1_CONSENSUS.md"), cycle=2)          # cycle 2 adds to the same audit
     cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
-    g2 = cost["cycles"]["c2"]["reviews"]["heimdall_glm"]                       # its own cycle 2 prompt (its own c1
+    g2 = cost["cycles"]["c2"]["reviews"]["heimdall_muse"]                       # its own cycle 2 prompt (its own c1
     assert g2["usd"] > 0 and g2["basis"].startswith("abandoned: the model's own rate")   # review in it)
     assert set(cost["cycles"]) == {"c1", "c2"} and cost["total_usd"] == pytest.approx(
         0.002 + 4e-8 * 9000 + 0.002 + g2["usd"], abs=2e-6)                       # COST.json rounds to 6 places
@@ -117,21 +117,21 @@ def test_every_review_is_booked_and_the_batch_line_reads_the_same_dollars(monkey
 
 def test_an_abandoned_review_is_at_the_list_price_of_its_prompt_until_3_reported_reviews():
     booked = XA.book({"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}},
-                     {"heimdall_glm": "timeout"}, {"heimdall_glm": {"kind": "timeout", "cost_usd": None}},
-                     {"heimdall_glm": "x" * 27000, "heimdall_qwen": "x" * 27000}, {"heimdall_glm": (4e-8, 2)})
-    model = XA.REVIEWERS["heimdall_glm"]["model"]
+                     {"heimdall_muse": "timeout"}, {"heimdall_muse": {"kind": "timeout", "cost_usd": None}},
+                     {"heimdall_muse": "x" * 27000, "heimdall_qwen": "x" * 27000}, {"heimdall_muse": (4e-8, 2)})
+    model = XA.REVIEWERS["heimdall_muse"]["model"]
     price = [b["price"]["in_per_mtok"] for b in providers.load_config()["backends"].values() if b.get("model") == model]
-    assert booked["heimdall_glm"]["usd"] == pytest.approx(price[0] / 1e6 * 9000)
-    assert "the list price of the prompt (fewer than 3 reported reviews)" in booked["heimdall_glm"]["basis"]
-    failed = XA.book({}, {"heimdall_glm": "server"}, {"heimdall_glm": {"kind": "server", "cost_usd": 0.0004}}, {}, {})
-    assert failed["heimdall_glm"] == {"usd": 0.0004, "basis": "reported (failed: server)"}
+    assert booked["heimdall_muse"]["usd"] == pytest.approx(price[0] / 1e6 * 9000)
+    assert "the list price of the prompt (fewer than 3 reported reviews)" in booked["heimdall_muse"]["basis"]
+    failed = XA.book({}, {"heimdall_muse": "server"}, {"heimdall_muse": {"kind": "server", "cost_usd": 0.0004}}, {}, {})
+    assert failed["heimdall_muse"] == {"usd": 0.0004, "basis": "reported (failed: server)"}
 
 
 def test_the_caps_estimate_is_a_worst_case_the_whole_reply_budget_at_list_price():
     """Audit b108 c1: qwen's reported $0.009 passed the doubled own-rate guess ($0.006: a long reply). The check now
     holds each reviewer's prompt and whole reply budget at its model's list price."""
     prompt = "x" * 96929
-    est = XA.estimate(lambda rid: prompt, None, {"heimdall_qwen": (9.6e-8, 33), "heimdall_glm": (4e-8, 31)})
+    est = XA.estimate(lambda rid: prompt, None, {"heimdall_qwen": (9.6e-8, 33), "heimdall_muse": (4e-8, 31)})
     floor = sum((len(prompt) / 3.0 * XA._price(rid)["in_per_mtok"] + XA.max_out(XA.REVIEWERS[rid]) *
                  XA._price(rid)["out_per_mtok"]) / 1e6 for rid in XA.DEFAULT)
     assert est >= floor and est >= 0.009 + 0.001                       # above the reported cycle 1 of b108
@@ -142,23 +142,23 @@ def test_a_review_cut_off_in_flight_is_booked_and_a_quick_failure_says_it_is_not
     off after 30 s in flight with no answer is booked at the model's own rate; a quick or answered failure says it is
     not booked."""
     ok = {"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}}
-    cut = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": {"kind": "network", "cost_usd": None, "seconds": 420.3,
+    cut = XA.book(ok, {"heimdall_muse": "x"}, {"heimdall_muse": {"kind": "network", "cost_usd": None, "seconds": 420.3,
                                                                "http_status": None}},
-                  {"heimdall_qwen": "x" * 27000, "heimdall_glm": "x" * 27000}, {"heimdall_glm": (4e-8, 31)})
-    assert cut["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)
-    assert cut["heimdall_glm"]["basis"].startswith("cut off after 420.3 s in flight (network): the model's own rate")
+                  {"heimdall_qwen": "x" * 27000, "heimdall_muse": "x" * 27000}, {"heimdall_muse": (4e-8, 31)})
+    assert cut["heimdall_muse"]["usd"] == pytest.approx(4e-8 * 9000)
+    assert cut["heimdall_muse"]["basis"].startswith("cut off after 420.3 s in flight (network): the model's own rate")
     for ec in ({"kind": "network", "seconds": 0.2, "http_status": None},
                {"kind": "server", "seconds": 60.0, "http_status": 502}):
-        quick = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": dict(ec, cost_usd=None)}, {},
-                        {"heimdall_glm": (4e-8, 31)})
-        assert quick["heimdall_glm"]["usd"] == 0.0 and quick["heimdall_glm"]["basis"].endswith(": not booked")
+        quick = XA.book(ok, {"heimdall_muse": "x"}, {"heimdall_muse": dict(ec, cost_usd=None)}, {},
+                        {"heimdall_muse": (4e-8, 31)})
+        assert quick["heimdall_muse"]["usd"] == 0.0 and quick["heimdall_muse"]["basis"].endswith(": not booked")
 
 
 def test_an_abandoned_reviews_prompt_is_its_own_at_the_measured_tokens_per_character():
     """Audit b108 c2: cycle 2 prompts differ by reviewer (each carries its own cycle 1 review), so an abandoned review
     is priced on ITS prompt, at the tokens per character measured on the reviews that answered."""
     ok = {"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}}
-    b = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": {"kind": "timeout", "cost_usd": None}},
-                {"heimdall_qwen": "x" * 36000, "heimdall_glm": "x" * 48000}, {"heimdall_glm": (4e-8, 31)})
-    assert b["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 48000 * 9000 / 36000)      # 12,000 tokens
-    assert "x 12000 prompt tokens" in b["heimdall_glm"]["basis"]
+    b = XA.book(ok, {"heimdall_muse": "x"}, {"heimdall_muse": {"kind": "timeout", "cost_usd": None}},
+                {"heimdall_qwen": "x" * 36000, "heimdall_muse": "x" * 48000}, {"heimdall_muse": (4e-8, 31)})
+    assert b["heimdall_muse"]["usd"] == pytest.approx(4e-8 * 48000 * 9000 / 36000)      # 12,000 tokens
+    assert "x 12000 prompt tokens" in b["heimdall_muse"]["basis"]
diff --git a/tests/ingest/test_flagcheck.py b/tests/ingest/test_flagcheck.py
index dd840e4e..a1407cce 100644
--- a/tests/ingest/test_flagcheck.py
+++ b/tests/ingest/test_flagcheck.py
@@ -157,13 +157,18 @@ def test_option_b_is_simulated_on_a_copy_and_the_ledger_is_never_written(tmp_pat
     assert sorted(x.name for x in tmp_path.iterdir()) == ["moment_ledger.jsonl"]        # the copy is removed
 
 
-def test_the_role_is_in_the_provider_config_with_two_unfrozen_back_ends_none_of_them_the_miner():
+def test_the_role_is_in_the_provider_config_with_two_unfrozen_back_ends_none_of_them_the_first_miner():
+    """Ruling 118 (10:50 ET Nov 16) puts six Heimdall families in the mine chain, and ruling 119 (3) takes glm out of
+    every chain: a second checker beside muse is a family of the mine chain, never its first (the model that mines
+    nearly every row); ruling 40's per-row rule (checkers(): never the miner of the row's video, by back-end and by
+    model) keeps it off any video it mined (test_the_checker_is_never_a_model_or_back_end_that_mined_the_video)."""
     cfg = providers.load_config()
     chain = cfg["roles"][FC.ROLE]["chain"]
     fz = providers.frozen_vendors(cfg)
     assert len(chain) >= 2 and not [b for b in chain if cfg["backends"][b]["vendor"] in fz]
-    miners = {cfg["backends"][b]["model"] for b in cfg["roles"]["mine"]["chain"]}
-    assert not [b for b in chain if cfg["backends"][b]["model"] in miners]
+    first = cfg["backends"][cfg["roles"]["mine"]["chain"][0]]["model"]
+    assert not [b for b in chain if cfg["backends"][b]["model"] == first]
+    assert len({cfg["backends"][b]["model"] for b in chain}) == len(chain)
 
 
 def test_the_calibration_set_is_balanced_and_counted_per_back_end():
diff --git a/tests/ingest/test_providers.py b/tests/ingest/test_providers.py
index 28d1e3fc..21665a5a 100644
--- a/tests/ingest/test_providers.py
+++ b/tests/ingest/test_providers.py
@@ -286,14 +286,25 @@ def test_the_real_config_under_the_spend_freeze():
     fz = providers.frozen_vendors(cfg)
     assert {"openai", "anthropic", "xai"} <= fz
     mine_chain = cfg["roles"]["mine"]["chain"]
-    assert [cfg["backends"][b]["kind"] for b in mine_chain] == ["openai_compat", "ollama_local"]
+    # ruling 118 (orchestrator 10:50 ET Nov 16): the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma,
+    # gpt-oss, mimo; never glm or muse), then the local model under the lease; no paid route (ruling 98's is closed)
+    assert [cfg["backends"][b].get("family") for b in mine_chain[:-1]] == \
+        ["qwen", "deepseek", "minimax", "gemma", "gpt-oss", "mimo"]
+    assert [cfg["backends"][b]["kind"] for b in mine_chain] == ["openai_compat"] * 6 + ["ollama_local"]
+    assert {cfg["backends"][b]["vendor"] for b in mine_chain[:-1]} == {cfg["down_signal"]["vendor"]}
+    for role in ("mine", "hook", "spotlight"):
+        assert cfg["roles"][role]["chain"] == mine_chain, role
+    assert "paid_route" not in cfg and "mine_paid" not in cfg["roles"]
+    assert not [(r, b) for r, rc in cfg["roles"].items() for b in rc["chain"]       # ruling 119 (3): glm in no chain
+                if cfg["backends"][b].get("family") == "glm"]
+    assert not [b for b in mine_chain if cfg["backends"][b].get("family") in ("glm", "muse")]
     assert cfg["backends"][mine_chain[0]].get("spend_meter") is True
     assert not [b for b in mine_chain if cfg["backends"][b]["vendor"] in fz]
     r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"))
     for bid in cfg["backends"]:
         if cfg["backends"][bid]["vendor"] in fz:
             assert r.frozen(bid) and r.available(bid)[0] is False
-    assert r.effective("mine") == [mine_chain[0]]          # this session: no GPU0 lease, so the gateway alone
+    assert r.effective("mine") == mine_chain[:-1]          # this session: no GPU0 lease, so the gateway's six
 
 
 def test_a_frozen_vendor_is_never_called_whatever_the_chain_only_or_enabled_say(tmp_path):
diff --git a/tests/ingest/test_r118.py b/tests/ingest/test_r118.py
new file mode 100644
index 00000000..1b39a276
--- /dev/null
+++ b/tests/ingest/test_r118.py
@@ -0,0 +1,380 @@
+"""tests/ingest/test_r118.py: the orchestrator's 10:50 ET order of Nov 16.
+
+(1) The pipeline's own transcript (the main tree's transcript ingest, READ ONLY) is taken before any caption download
+    and when a VOD lists no English captions; a record failing a check never is; a caption 429 stops the captions
+    alone (the gate is tested in test_watch_fetch), and the pipeline's own caption breaker stops this ingest's
+    downloads too.
+(3) The outage clock runs on the watcher's OWN state file: another session's deadline misses never move it.
+(4) The self-check: videos waiting and nothing mined for 30 minutes, on STATE line 1 and acted on.
+Ruling 118's chain and ruling 119 (3) are checked on the real config in test_providers and test_signal.
+"""
+import hashlib
+import json
+import os
+import shutil
+import types
+from datetime import datetime, timezone
+
+import pytest
+
+import helpers as H
+from pipeline.ingest import config, fetch, service, spend, stall
+from pipeline.ingest import queue as Q
+
+NOW = 1794470000.0          # 2026-11-12 ~08:33 UTC
+MODULE = "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py"     # the builder's, read only
+
+
+@pytest.fixture
+def q(tmp_path):
+    return Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: NOW)
+
+
+def add(q, v, **kw):
+    q.add_video(v, H.CHAN["channel_id"], "Bitcoin test video", "uploads_playlist", **kw)
+    return q.video(v)
+
+
+def pipeline_record(v, method="whisper", tamper=None, name=None, raw=None):
+    """A record of the pipeline's own transcript ingest in this test's pipeline store (conftest: fetch.PIPELINE_STORE)."""
+    rec, _ = H.caption_record(v)
+    rec = dict(rec, transcript_method=method, transcript_model="test model")
+    if tamper:
+        tamper(rec)
+    d = os.path.join(fetch.PIPELINE_STORE, v)
+    os.makedirs(d, exist_ok=True)
+    p = os.path.join(d, name or f"transcript.{method.split(':')[0]}.json")
+    with open(p, "w") as f:
+        f.write(raw if raw is not None else json.dumps(rec, indent=1))
+    return p, rec
+
+
+def downloads(monkeypatch, status="throttled"):
+    """Every caption download this ingest would make, answered `status` (none should be made where a test says so)."""
+    ts, made = config.ts(), []
+    monkeypatch.setattr(ts, "fetch_captions", lambda meta, work: (made.append(meta["video_id"]), (status, None))[1])
+    return made
+
+
+def sha(p):
+    return hashlib.sha256(open(p, "rb").read()).hexdigest()
+
+
+def staged(v, method="whisper"):
+    return os.path.join(config.ts()._vdir(v), f"transcript.{method}.json")
+
+
+def attempts(v):
+    p = os.path.join(config.ts()._vdir(v), "attempts.jsonl")
+    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []
+
+
+# ── (1) the pipeline's own transcript ──
+
+def test_the_pipelines_own_transcript_is_taken_byte_for_byte_and_no_caption_is_downloaded(q, monkeypatch):
+    v = H.vid("W")
+    src, rec = pipeline_record(v)
+    before = sha(src)
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    row = q.video(v)
+    assert made == [] and row["transcript_method"] == "whisper" and row["transcript_sha256"] == rec["transcript_sha256"]
+    assert sha(staged(v)) == before == sha(src)                       # the bytes the pipeline wrote; its file untouched
+    assert config.ts().canonical_transcript(v)["transcript_sha256"] == rec["transcript_sha256"]
+    meta = json.load(open(os.path.join(config.ts()._vdir(v), "meta.json")))
+    assert meta["written_by"] == "pipeline.ingest.fetch" and meta["captions_auto_en"] == ["en", "en-orig"]
+    a = [x for x in attempts(v) if x.get("step") == "transcript"]
+    assert a and a[-1]["status"] == "taken_from_pipeline_store" and a[-1]["source"] == src
+    assert [e["video_id"] for e in q.rows("SELECT video_id FROM events WHERE kind='pipeline_transcript'")] == [v]
+    assert row["next_at"] == NOW                                     # due to the miner at once
+
+
+def test_a_vod_without_english_captions_takes_the_pipelines_transcript(q, monkeypatch):
+    """BLOy6SetrUs (Yahoo Finance, Nov 16): no English captions on YouTube, a Whisper record in the pipeline's store."""
+    made = downloads(monkeypatch)
+    a, b = H.vid("N"), H.vid("N")
+    pipeline_record(a)
+    gate = H.FakeGate(probes={x: H.probe_json(x, timestamp=NOW - 3600, automatic_captions={}, title=f"Episode {x}")
+                              for x in (a, b)})
+    assert fetch.process(q, gate, add(q, a), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    assert fetch.process(q, gate, add(q, b), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING   # none there: waits
+    assert made == [] and q.video(a)["transcript_method"] == "whisper"
+
+
+def _tamper_text(r):
+    r["segments"][0]["text"] += " (edited)"
+
+
+def _other_channel(r):
+    r["channel_id"] = "UC" + "z" * 22
+
+
+def _other_video(r):
+    r["video_id"] = "zzzzzzzzzzz"
+
+
+def _empty(r):
+    r["segments"] = []
+    r["transcript_sha256"] = config.ts().segments_sha256([])
+
+
+@pytest.mark.parametrize("how", ["text", "channel", "video", "name", "empty", "garbage"])
+def test_a_record_failing_any_check_is_never_taken(q, monkeypatch, how):
+    v = H.vid("F")
+    kw = {"text": dict(tamper=_tamper_text), "channel": dict(tamper=_other_channel),
+          "video": dict(tamper=_other_video), "name": dict(name="transcript.yt_auto.json"),
+          "empty": dict(tamper=_empty), "garbage": dict(raw="{not json")}[how]
+    pipeline_record(v, **kw)
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
+    assert made == [v] and not os.path.exists(staged(v)) and not os.path.exists(staged(v, "yt_auto"))
+    assert fetch.pipeline_transcript(v, H.CHAN["channel_id"]) is None
+
+
+def test_the_best_record_by_the_stores_rank_is_taken_and_one_already_here_is_kept(q, monkeypatch):
+    v = H.vid("B")
+    pipeline_record(v, method="yt_auto:en-orig")
+    src, rec = pipeline_record(v, method="whisper")
+    assert fetch.pipeline_transcript(v, H.CHAN["channel_id"])[0] == src
+    downloads(monkeypatch)
+    os.makedirs(os.path.dirname(staged(v)), exist_ok=True)
+    shutil.copyfile(src, staged(v))                                  # taken before (an earlier try): kept, not copied
+    os.chmod(staged(v), 0o444)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    assert q.video(v)["transcript_method"] == "whisper" and not os.path.exists(staged(v, "yt_auto"))
+
+
+def test_a_copy_that_differs_from_the_record_checked_is_never_linked_in(q, monkeypatch):
+    v = H.vid("K")
+    pipeline_record(v)
+    real = shutil.copyfile
+
+    def swap(a, b):                                                  # the file changed between the check and the copy
+        real(a, b)
+        r = json.load(open(b))
+        r["segments"][0]["text"] = "swapped"
+        json.dump(r, open(b, "w"))
+    monkeypatch.setattr(fetch.shutil, "copyfile", swap)
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
+    assert made == [v] and not os.path.exists(staged(v))
+    assert [x["status"] for x in attempts(v) if x.get("step") == "transcript"] == ["pipeline_store_copy_refused"]
+    assert not [f for f in os.listdir(config.ts()._vdir(v)) if f.endswith(".tmp")]
+
+
+@pytest.mark.parametrize("probe,state", [(dict(media_type="short", duration=58), Q.SHORT),
+                                         (dict(live_status="is_live", media_type="livestream", duration=None,
+                                               release_timestamp=NOW - 1800), Q.LIVE),
+                                         (dict(live_status="is_upcoming", release_timestamp=NOW + 3600,
+                                               duration=None), Q.UPCOMING)])
+def test_a_short_a_live_or_an_upcoming_stream_is_never_given_a_transcript(q, monkeypatch, probe, state):
+    v = H.vid("S")
+    pipeline_record(v)
+    downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600, **probe)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == state
+    assert not os.path.exists(staged(v)) and q.video(v)["transcript_method"] is None
+
+
+def test_while_the_pipelines_caption_breaker_is_open_no_download_is_tried_here(q, monkeypatch):
+    """Both ingests download captions from this one machine: a 429 the pipeline's ingest was given stops this one's
+    downloads too (its breaker file, read only); a closed or unreadable one does not."""
+    v = H.vid("P")
+    made = downloads(monkeypatch)
+    os.makedirs(os.path.dirname(fetch.PIPELINE_CIRCUIT), exist_ok=True)
+    with open(fetch.PIPELINE_CIRCUIT, "w") as f:
+        json.dump({"open_until": NOW + 900, "reason": "HTTP 429 on x"}, f)
+    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
+    row = q.video(v)
+    assert made == [] and row["reason"].startswith("captions throttled") and row["next_at"] == NOW + 600
+    assert "the pipeline's own caption breaker is open" in attempts(v)[-1]["why"]
+    for body in ('{"open_until": %f}' % (NOW - 1), "{broken"):
+        with open(fetch.PIPELINE_CIRCUIT, "w") as f:
+            f.write(body)
+        q.x("UPDATE videos SET next_at=0, state=?", (Q.CAPTIONS_PENDING,))
+        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
+    assert made == [v, v]
+
+
+def test_inside_the_moments_life_a_video_without_captions_is_looked_at_every_30_minutes():
+    inside, outside = NOW - 3600, NOW - (config.EXPIRY_H + 1) * 3600
+    assert [fetch._caption_retry_at(NOW, inside, n) - NOW for n in range(6)] == [600, 1200, 1800, 1800, 1800, 1800]
+    assert [fetch._caption_retry_at(NOW, outside, n) - NOW for n in range(6)] == [600, 1200, 2400, 4800, 7200, 7200]
+    assert fetch._caption_retry_at(NOW, None, 3) - NOW == 4800
+
+
+# ── (3) the outage clock: the watcher's own file ──
+
+@pytest.fixture
+def own(monkeypatch, tmp_path):
+    """A service wired to a copy of the builder's module whose shared STATE is a file of this test (never the real
+    one), with no state path given: the watcher's default."""
+    if not os.path.exists(MODULE):
+        pytest.skip("the builder's module is not at its path")
+    src = open(MODULE).read()
+    shared = tmp_path / "SHARED_HEIMDALL_HEALTH.json"
+    mod = tmp_path / "hh_copy.py"
+    mod.write_text(src + f"\nSTATE = {str(shared)!r}\n")
+    p = config.paths()
+    for k in ("ingest", "moments"):
+        shutil.rmtree(p[k], ignore_errors=True)
+    doc = tmp_path / "STATE.md"
+    doc.write_text("# STATE\nbody\n")
+    monkeypatch.setattr(config, "STATE_DOC", str(doc))
+    from test_signal import probe_cfg, T0
+    t, made = [T0], []
+
+    def make():
+        cfg = probe_cfg(chain=("hv_p1", "hv_p2"))
+        cfg["backends"]["hv1"] = {"kind": "openai_compat", "vendor": "hv", "model": "model-hv1", "enabled": True}
+        cfg["backends"]["local"] = {"kind": "openai_compat", "vendor": "lv", "model": "model-local", "enabled": True}
+        for r in ("mine", "hook", "flagcheck", "judge"):
+            cfg["roles"][r]["chain"] = ["hv1", "local"]
+        cfg["spend_meter"]["backend"] = "hv1"
+        cpath = tmp_path / "providers.json"
+        cpath.write_text(json.dumps(cfg))
+        b = {x: H.FakeBackend(x, fn=lambda p: "OK") for x in ("hv1", "local", "hv_p1", "hv_p2")}
+        s = service.Service(providers_path=str(cpath), backends=b, gate=H.FakeGate(), log=lambda m: None,
+                            keyring=__import__("pipeline.ingest.providers", fromlist=["Keyring"]).Keyring("/x"),
+                            sleep=lambda x: None, clock=lambda: t[0], signal_module=str(mod))
+        made.append(s)
+        return s, b
+    yield make, t, shared, doc, T0
+    for s in made:
+        s.close()
+
+
+def test_another_sessions_running_clock_never_moves_the_watchers_own(own):
+    """The false outages of Nov 14 (09:16, 10:12 ET): the builder's deadline misses started the clock of the ONE shared
+    file and the watcher announced its switch. Now the shared file may say a clock has run 20 minutes (and even
+    plan_b): the watcher reads and writes only its own file, which no call of its own has failed on."""
+    make, t, shared, doc, T0 = own
+    iso = lambda x: datetime.fromtimestamp(x, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+    shared.write_text(json.dumps({"mode": "heimdall_first", "last_answer_utc": iso(T0 - 3600),
+                                  "failing_since_utc": iso(T0 - 1200), "last_probe_utc": None, "probe_streak": 0,
+                                  "failing_families": ["builders"], "switches": [], "notes": 5}))
+    before = sha(shared)
+    s, b = make()
+    hs = s.hsig
+    assert hs.state_path == config.paths()["signal_state"] != hs.hh.STATE == str(shared)
+    for _ in range(3):
+        hs.tick(wait=True)
+        t[0] += 31
+    assert sha(shared) == before                                     # never read as ours, never written
+    if os.path.exists(hs.state_path):                                # (the module writes its file at a first note)
+        own_state = json.load(open(hs.state_path))
+        assert own_state["mode"] == "heimdall_first" and not own_state.get("failing_since_utc")
+    assert hs.mode in (None, "heimdall_first") and "SWITCHED TO PLAN B" not in doc.read_text()
+    assert b["hv_p1"].calls == [] and b["hv_p2"].calls == []          # no failure of its own: no probe either
+    hs.noted({"backend": "hv1", "kind": "timeout", "role": "mine"})  # its own failed call starts its own clock
+    hs.tick(wait=True)
+    own_state = json.load(open(hs.state_path))
+    assert len(b["hv_p1"].calls) == 1 and own_state["failing_since_utc"] is None      # probed, answered: reset
+    assert sha(shared) == before
+
+
+# ── (4) the self-check ──
+
+def waiting(q, v, state, reason, discovered, next_at=NOW + 3600, published=None):
+    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
+    q.x("UPDATE videos SET state=?, reason=?, discovered_ts=?, next_at=?, published_ts=? WHERE video_id=?",
+        (state, reason, discovered, next_at, published, v))
+
+
+def mined(q, v, at):
+    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
+    q.x("UPDATE videos SET state=?, mined_ts=?, discovered_ts=?, published_ts=? WHERE video_id=?",
+        (Q.MINED, at, at - 600, at - 900, v))
+
+
+def test_a_stall_is_found_only_when_something_waits_and_nothing_was_mined_for_30_minutes(q):
+    mined(q, "m0000000001", NOW - 7200)
+    assert stall.check(q, NOW)["stalled"] is False                                   # nothing waits
+    waiting(q, "w0000000001", Q.UPCOMING, "upcoming", NOW - 5000)
+    waiting(q, "w0000000002", Q.LIVE, "is_live", NOW - 5000)
+    waiting(q, "w0000000003", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 20 * 3600,
+            published=NOW - 20 * 3600)                                               # outside its moments' life
+    assert stall.check(q, NOW)["stalled"] is False
+    waiting(q, "w0000000004", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 600)
+    chk = stall.check(q, NOW)
+    assert chk["stalled"] is False and chk["since"] == NOW - 600                     # it came in 10 minutes ago
+    assert stall.check(q, NOW + 1200)["stalled"] is True                             # 30 minutes on: a stall
+    mined(q, "m0000000002", NOW + 900)
+    assert stall.check(q, NOW + 1200)["stalled"] is False                            # mined 5 minutes ago
+
+
+def test_the_stall_line_says_what_each_waits_on_and_the_act_makes_them_due_now(q):
+    mined(q, "m0000000001", NOW - 7200)
+    waiting(q, "w0000000001", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2400)
+    waiting(q, "w0000000002", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2000)
+    waiting(q, "w0000000003", Q.PROBE_RETRY, "rate_limited: yt-dlp breaker open for 389 s", NOW - 2000)
+    waiting(q, "w0000000004", Q.CAPTIONS_PENDING, "VOD without English captions yet", NOW - 1900)
+    waiting(q, "w0000000005", Q.MINING, None, NOW - 1900, next_at=NOW + 50)          # in flight: never touched
+    chk = stall.check(q, NOW)
+    assert chk["stalled"] and chk["since"] == NOW - 2400 and len(chk["waiting"]) == 5
+    assert stall.act(q, chk, NOW) == 4
+    nxt = {r["video_id"]: r["next_at"] for r in q.rows("SELECT video_id, next_at FROM videos")}
+    assert [nxt[f"w000000000{i}"] for i in range(1, 6)] == [NOW] * 4 + [NOW + 50]
+    line = stall.line(chk, NOW, NOW, 4)
+    assert line.startswith(spend.STALL_PREFIX) and "|" not in line and "\n" not in line
+    assert "5 VIDEO(S) WAITING, NOTHING MINED FOR 30 MIN OR MORE: 2 CAPTIONS REFUSED BY YOUTUBE (HTTP 429), " \
+           "1 NO ENGLISH CAPTIONS YET, 1 PROBE BEHIND THE YT-DLP BREAKER, 1 TRANSCRIBED, BEING MINED; ACTED" in line
+    assert line == stall.line(stall.check(q, NOW + 600), NOW + 600, NOW, 4)          # stable while it lasts
+
+
+def test_the_watcher_says_the_stall_after_the_batch_spend_acts_every_30_minutes_and_clears_it(q, tmp_path):
+    doc = tmp_path / "STATE.md"
+    sw = "10:18 ET: MINER OFF THE PAID ROUTE (BACK ON HEIMDALL) |"
+    doc.write_text(f"BATCH 3 ingest spend: $0.1637 (CLOSED) | {sw}\nPP-INGEST CYCLES TO 10:34 ET (x)\n# STATE\n")
+    (tmp_path / "ingest").mkdir()
+    logs, clock = [], [NOW]
+    me = types.SimpleNamespace(q=q, p={"notify": str(tmp_path / "ingest" / "NOTIFY.txt")}, log=logs.append,
+                               stall_error=None)
+    import pipeline.ingest.config as C
+    old = C.STATE_DOC
+    C.STATE_DOC = str(doc)
+    try:
+        mined(q, "m0000000001", NOW - 7200)
+        waiting(q, "w0000000001", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2400)
+        service.Service._stall_notice(me, NOW)
+        first, second = doc.read_text().split("\n")[:2]
+        segs = first.split(spend.SEP)
+        assert segs[0].startswith("BATCH 3") and segs[1].startswith(spend.STALL_PREFIX) and segs[2] == sw
+        assert second.startswith("PP-INGEST CYCLES TO") and me.stall_error is None
+        assert q.video("w0000000001")["next_at"] == NOW
+        q.x("UPDATE videos SET next_at=? WHERE video_id='w0000000001'", (NOW + 5000,))   # tried, put off again
+        service.Service._stall_notice(me, NOW + 300)                 # 5 minutes on: no second act
+        assert q.video("w0000000001")["next_at"] == NOW + 5000
+        service.Service._stall_notice(me, NOW + 1801)                # 30 minutes on: acted again
+        assert q.video("w0000000001")["next_at"] == NOW + 1801
+        assert len(q.rows("SELECT id FROM events WHERE kind='stall_act'")) == 2
+        mined(q, "m0000000002", NOW + 1900)
+        service.Service._stall_notice(me, NOW + 1960)
+        first = doc.read_text().split("\n")[0]
+        assert spend.STALL_PREFIX not in doc.read_text() and first.split(spend.SEP)[1] == sw
+        assert q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='stall_over'")[0]["n"] == 1
+    finally:
+        C.STATE_DOC = old
+
+
+def test_line_1_holds_the_stall_after_the_batch_spend_and_an_alarm_in_any_hand_edited_order(tmp_path):
+    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
+    st = spend.STALL_PREFIX + "10:05 ET: 1 VIDEO(S) WAITING"
+    doc.write_text(f"{st} | ALARM FOR PBX: x. Waiting since 10:00 ET. | BATCH 3 ingest spend: $1 | "
+                   "10:12 ET: SWITCHED TO PLAN B (y) |\nPP-INGEST CYCLES TO 10:34 ET (x)\nbody\n")
+    spend.write_batch_notice("BATCH 3 ingest spend: $2", doc=str(doc), notify_path=str(notify))
+    first = doc.read_text().split("\n")[0].split(spend.SEP)
+    assert first == ["BATCH 3 ingest spend: $2", "ALARM FOR PBX: x. Waiting since 10:00 ET.", st,
+                     "10:12 ET: SWITCHED TO PLAN B (y) |"]
+    for bad in (st + " | x", st + "\nx", "MINING IS FINE"):
+        with pytest.raises(ValueError):
+            spend.write_stall_notice(bad, doc=str(doc), notify_path=str(notify))
+    spend.write_stall_notice(None, doc=str(doc), notify_path=str(notify))
+    assert doc.read_text().split("\n")[0].split(spend.SEP) == ["BATCH 3 ingest spend: $2",
+                                                               "ALARM FOR PBX: x. Waiting since 10:00 ET.",
+                                                               "10:12 ET: SWITCHED TO PLAN B (y) |"]
diff --git a/tests/ingest/test_signal.py b/tests/ingest/test_signal.py
index afda1313..21370fd2 100644
--- a/tests/ingest/test_signal.py
+++ b/tests/ingest/test_signal.py
@@ -286,8 +286,8 @@ def test_fifteen_minutes_with_no_answer_of_any_kind_switch_to_plan_b_and_three_p
     hs.tick(wait=True)
     st = state(tmp)
     assert st["mode"] == "plan_b" and st["switches"][-1]["by"] == "pp-ingest" and hs.mode == "plan_b"
-    switched = " ".join(f"02:15 ET: SWITCHED TO PLAN B ({st['switches'][-1]['why']}; BY PP-INGEST); THE MINER'S "
-                        "PLAN B: QUEUE AND WAIT (SPEND FREEZE) |".upper().split())
+    switched = " ".join(f"02:15 ET: SWITCHED TO PLAN B ({st['switches'][-1]['why']}; BY PP-INGEST)"
+                        f"{downsignal.PLAN_B_TAIL} |".upper().split())     # ruling 118's Plan B, no paid route
     assert "2026-11-14T07:00:00Z" in switched and doc.read_text() == switched + "\n# STATE\nbody\n"
     t[0] += 5
     hs.tick(wait=True)                                                # seen once: no second head
@@ -702,14 +702,14 @@ def fake_module(tmp, amended=True):
 FAMS = {"hv1": "fam_a", "hv2": "fam_b", "hv_p1": "fam_a", "hv_p2": "fam_b"}
 
 
-def test_each_family_that_failed_is_noted_once_at_its_first_failure_and_the_probe_names_its_families(sig):
-    """The amended module records the failed families (note(False, family=)) so a slot whose failed families a prober
-    cannot ask goes to the prober that can (probe_due(families=)): each family once, at its first failure after the
-    latest answer, in time order; the families this watcher's probe asks (its probe back-ends') on probe_due."""
+def test_each_family_that_failed_is_noted_once_at_its_first_failure_and_the_probe_names_no_family(sig):
+    """The amended module records the failed families (note(False, family=)): each family once, at its first failure
+    after the latest answer, in time order. The 10:50 order (3) of Nov 16: the state file is this watcher's own, so
+    its probe names no families (probe_due(families=) left a slot to another prober, and none shares the file)."""
     make, t, doc, tmp, msgs = sig
     s, b = make(module=fake_module(tmp), families=FAMS)
     hs = s.hsig
-    assert hs.note_family is True and hs.probe_kw == {"who": "pp-ingest probe", "families": ["fam_a", "fam_b"]}
+    assert hs.note_family is True and hs.probe_kw == {"who": "pp-ingest probe"}
     hs.noted(rec(kind="ok"))                                          # an answer, then failures after it
     t[0] += 1
     hs.noted(rec(backend="hv2", kind="timeout"))
@@ -720,8 +720,8 @@ def test_each_family_that_failed_is_noted_once_at_its_first_failure_and_the_prob
     hs.tick(wait=True)
     notes = [c for c in hs.hh.CALLS if c[0] == "note"]
     assert notes == [("note", True, T0, None), ("note", False, T0 + 1, "fam_b"), ("note", False, T0 + 2, "fam_a")]
-    assert ("probe_due", "pp-ingest probe", ["fam_a", "fam_b"]) in hs.hh.CALLS
-    assert hs.n["failures_noted"] == 2 and hs.snapshot()["probe_families"] == ["fam_a", "fam_b"]
+    assert ("probe_due", "pp-ingest probe", None) in hs.hh.CALLS        # the slot claimed with no families named
+    assert hs.n["failures_noted"] == 2 and hs.snapshot()["probe_families"] is None
 
 
 def test_a_first_failure_without_a_family_still_starts_the_clock(sig):
@@ -820,26 +820,21 @@ def test_a_family_whose_probe_thread_dies_is_not_counted_and_breaks_nothing(sig)
         hs.last_probe["why"] and hs.n["probes"] == 1
 
 
-def test_with_the_builders_module_a_slot_goes_to_the_prober_that_can_ask_a_failed_family(sig):
-    """Audit r87a c1 (muse P1): the family path against the builder's real amended module and its file lock. A failure
-    of a family this watcher's probe cannot ask (fam_x) is in failing_families and the watcher leaves the slot; once a
-    family it can ask (fam_a) fails too, it claims, asks, and the answer clears the clock and the families."""
+def test_on_its_own_file_a_failure_its_probe_cannot_ask_is_probed_at_once_and_answered(sig):
+    """The 10:50 order (3) of Nov 16, against the builder's real amended module and its file lock: on the watcher's
+    own state file no other prober exists, so a failure of a family its probe does not ask (fam_x) is probed in the
+    same slot (families= would have left the slot to a prober that never comes, and the clock would have run to 15
+    minutes: a false outage); any family's answer clears the clock and the families."""
     make, t, doc, tmp, msgs = sig
     s, b = make(families={"hv1": "fam_x", "hv2": "fam_a", "hv_p1": "fam_a", "hv_p2": "fam_b"})
     hs = s.hsig
     if not amended(hs):
         pytest.skip("the module at the builder's path predates ruling 87 amended")
-    assert hs.note_family is True and hs.probe_kw["families"] == ["fam_a", "fam_b"]
+    assert hs.note_family is True and "families" not in hs.probe_kw
     hs.noted(rec(kind="timeout"))
     hs.tick(wait=True)
     st = state(tmp)
-    assert st["failing_families"] == ["fam_x"] and st["failing_since_utc"] == iso(T0)
-    assert b["hv_p1"].calls == [] and b["hv_p2"].calls == []           # the slot left to a prober that can ask fam_x
-    t[0] += 31
-    hs.noted(rec(backend="hv2", kind="timeout"))
-    hs.tick(wait=True)
-    st = state(tmp)
-    assert len(b["hv_p1"].calls) == 1 and len(b["hv_p2"].calls) == 1
+    assert len(b["hv_p1"].calls) == 1 and len(b["hv_p2"].calls) == 1    # probed at once, though fam_x is not asked
     assert st["failing_since_utc"] is None and st["failing_families"] == [] and st["probe_streak"] == 1
 
 
diff --git a/tests/ingest/test_watch_fetch.py b/tests/ingest/test_watch_fetch.py
index f5822a1d..dabbb440 100644
--- a/tests/ingest/test_watch_fetch.py
+++ b/tests/ingest/test_watch_fetch.py
@@ -321,10 +321,14 @@ class TestYouTubeGateAgeGate:
 
 
 class TestCaptionsRespectTheBreaker:
-    """Freeze audit c1 (glm C37): caption downloads held a yt-dlp slot but ignored the breaker, and a throttled
-    caption answer never tripped it."""
-
-    def test_no_caption_download_while_the_breaker_is_open_and_throttled_trips_it(self, q, monkeypatch):
+    """Freeze audit c1 (glm C37): caption downloads held a yt-dlp slot but ignored the breaker. The 10:50 ET order of
+    Nov 16 (1): a throttled caption answer no longer trips it: from 07:47 ET that day YouTube refused every caption
+    download (HTTP 429) while it still answered every probe and listing, and each refusal shut the whole gate for 10 to
+    60 minutes, so the probes stopped too and nothing reached the miner for three hours. A 429 stops the captions alone
+    (transcript_store's own 30-minute breaker); the gate is tripped only by a probe or a listing that is refused."""
+
+    def test_no_caption_download_while_the_breaker_is_open_and_a_throttled_caption_never_trips_it(self, q,
+                                                                                                    monkeypatch):
         ts = config.ts()
         v = H.vid("c")
         q.add_video(v, H.CHAN["channel_id"], "Bitcoin t", "playlist", listing_ts=NOW - 600)
@@ -343,7 +347,11 @@ class TestCaptionsRespectTheBreaker:
                 self.until = 1.0
         g = Gate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
         st = fetch.process(q, g, q.video(v), H.CHAN, set(), now_ts=NOW)
-        assert st == Q.CAPTIONS_PENDING and fetched == [1] and trips == ["captions: throttled"]
+        assert st == Q.CAPTIONS_PENDING and fetched == [1] and trips == []           # the gate stays closed
+        row = q.video(v)
+        assert row["next_at"] == NOW + fetch.CAPTION_THROTTLED_RETRY_S == NOW + 600
+        assert row["reason"].startswith("captions throttled")
+        g.trip("a probe was refused")                    # a probe's or a listing's 429 opens it (watch.YouTubeGate)
         q.x("UPDATE videos SET next_at=0")
         st = fetch.process(q, g, q.video(v), H.CHAN, set(), now_ts=NOW)
         assert st == Q.CAPTIONS_PENDING and fetched == [1]           # breaker open: no second download
diff --git a/tests/ingest/xllm_audit.py b/tests/ingest/xllm_audit.py
index 63a31955..0ae9a939 100644
--- a/tests/ingest/xllm_audit.py
+++ b/tests/ingest/xllm_audit.py
@@ -21,7 +21,7 @@ SPEND FREEZE (orchestrator 05:30 ET Nov 12): a reviewer whose vendor is in provi
 
 RULING 107 (2) (orchestrator 20:20 ET Nov 14; in force for batch 3 by ruling 108, 21:22): the package is the DIFF (git
 diff --base of the watcher's code and its tests; a new file needs `git add -N`), the laws and the change's own context
-(--context), never the whole files; the reviewers are two Heimdall families, qwen + glm (DEFAULT); a third family
+(--context), never the whole files; the reviewers are two Heimdall families, qwen + muse (DEFAULT; glm is out of every chain, ruling 119 (3)); a third family
 (THIRD, by --only) only when the two disagree on a P0 / P1 or one of them is down (the paid frontier reviewers stay
 out under pp-ingest's freeze). The audit is capped, vendor-reported, both cycles together: $0.30 for a change under 60
 changed lines, else $1.00; a cycle that could pass the cap is refused before any call. Each review's cost goes to
@@ -64,13 +64,16 @@ REVIEWERS = {
     "heimdall_muse": dict(HEIMDALL, model="meta-models/muse-spark-open-816b-a42b", timeout_s=1800,
                           extra_body={"reasoning": {"effort": "none"}}),
     "heimdall_minimax": dict(HEIMDALL, model="minimax/minimax-m3.1-flash", extra_body={"reasoning": {"effort": "none"}}),
+    "heimdall_mimo": dict(HEIMDALL, model="xiaomi/mimo-v2.6-flash-rl", extra_body={"reasoning": {"effort": "low"}},
+                          max_tokens_floor=24000),   # r118: the third family once glm is out (ruling 119 (3))
 }  # Heimdall qwen at effort none. deepseek-v4.1-flash dropped after c1: empty content twice (effort low, then none; its
    # hidden reasoning took the whole budget on the 64k-token package); the abliterated deepseek and ling-3.0-flash are
    # excluded by the order (incoherent on long prompts / always 429)
 
 
-DEFAULT = ("heimdall_qwen", "heimdall_glm")       # ruling 107 (2): two Heimdall families
-THIRD = "heimdall_muse"                           # the third family: a P0 / P1 disagreement, or one of the two down
+DEFAULT = ("heimdall_qwen", "heimdall_muse")      # ruling 107 (2): two Heimdall families (glm out: ruling 119 (3))
+THIRD = "heimdall_mimo"                           # the third family: a P0 / P1 disagreement, or one of the two down
+EXCLUDED = {"heimdall_glm": "ruling 119 (3) (orchestrator 10:50 ET Nov 16): glm is out of every chain"}
 DIFF_PATHS = ["pipeline/ingest", "tools/ingest_watch.py", "tests/ingest"]
 SMALL_LINES, SMALL_CAP, BIG_CAP = 60, 0.30, 1.00  # ruling 107 (2): per audit, both cycles, vendor-reported
 MIN_REPORTED = 3                                  # ruling 107: list price until a model has 3 reported reviews
@@ -285,6 +288,7 @@ def chosen(only=None):
     fz = frozen()
     skipped = {rid: f"spend freeze: vendor {REVIEWERS[rid]['vendor']!r}" for rid in want
                if rid in REVIEWERS and REVIEWERS[rid]["vendor"] in fz}
+    skipped.update({rid: why for rid, why in EXCLUDED.items() if rid in want})
     unknown = sorted(want - set(REVIEWERS))
     if unknown:
         raise SystemExit(f"unknown reviewer(s) {unknown}")

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

