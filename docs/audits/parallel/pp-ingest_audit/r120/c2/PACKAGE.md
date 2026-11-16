# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 49fec073
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
# r120: a stream that is over but still processing (post_live) takes the pipeline's record (Nov 16)

## Why (found by r119's own measure)
The orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its transcript". r119 measures
each mined video's seconds from its transcript record to its rows. At 14:26 ET it flagged Yahoo Finance kh3U_15pFZc
LATE: 3,205 s. YouTube kept that finished livestream in live_status "post_live" (the stream over, its video still
processing) from 12:26 to 14:26 ET; the pipeline's transcript ingest Whispered it at 13:33 (its acquire() skips only
is_live / is_upcoming: pp-selectid pipeline/transcript_store.py:454); the watcher's fetch.process treated post_live like
is_live (LIVE, re-probed every 20 min, meta.json not written) and r119's sweep looks only at probe_retry and
captions_pending, so the record waited until YouTube said was_live.

## The change
1. fetch.process: a stream still live (is_live) is LIVE as before, never taken. A post_live video with no record in the
   pipeline's store is LIVE as before (re-probed every 20 min, no caption download, no meta.json). A post_live video
   WITH a record goes on through every remaining check of the probe (publish time, age, duration, too long, title
   duplicate) and takes the record (take_pipeline_transcript, every r118 check) like a VOD; its duration, when the
   probe gives none yet, is the length the pipeline recorded. If the take is refused (the copy differs), it waits LIVE
   as before (no caption download while post_live).
2. fetch.pipeline_sweep also makes due a LIVE row whose stored live_status is post_live (never one still is_live).
3. stall.py counts such a row as waiting ("STREAM OVER, ITS VIDEO STILL PROCESSING") and its act may make it due.

## Facts checked before building
- Nothing downstream treats post_live: pp-ingest's ledger, contract and miner never read live_status (it rides in the
  row's source as information); the builder's code reads live_status only in transcript_store (skip is_live /
  is_upcoming), so the pipeline itself transcribes post_live.
- The timeline: the pipeline's post_live record of kh3U_15pFZc runs 1,066-1,070 s, the final video 1,080 s; word-level
  timing is the pipeline's job at cut time, on the video's own audio (INGEST_DESIGN: "word-level timing stays the
  pipeline's job at cut time"), as for the pipeline's own post_live records.
- INGEST-FAIL-01 (a meta written while live froze 46 videos) is about a meta read later as "still live": here the video
  is transcribed and then mined at once (terminal), and no later step reads its meta's live_status.

## What to check
- A stream still live can never be taken or have its meta written; every other probe check still runs for post_live.
- No caption download for a post_live video on any path.
- The sweep and the self-check never touch an is_live row.

Suite: tests/ingest 430 passed (8 new in test_r120.py). Mutations M36-M42: 7 of 7 killed.


```diff
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index 53a79d29..7f9c14c2 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -184,11 +184,12 @@ def pipeline_transcript(vid, channel_id, root=None):
     return (best[1], best[2]) if best else None
 
 
-def take_pipeline_transcript(q, vid, channel_id, root=None):
-    """The pipeline's own transcript (pipeline_transcript) copied into this store byte for byte, write-once, the copy
-    checked again before it is linked in: True when this store holds it (a record of that method already here is
-    kept, never replaced). Said in the video's attempts log and as a queue event."""
-    found = pipeline_transcript(vid, channel_id, root)
+def take_pipeline_transcript(q, vid, channel_id, root=None, found=None):
+    """The pipeline's own transcript (pipeline_transcript, or `found`: what the caller's own call returned) copied into
+    this store byte for byte, write-once, the copy checked again before it is linked in: True when this store holds it
+    (a record of that method already here is kept, never replaced). Said in the video's attempts log and as a queue
+    event."""
+    found = found or pipeline_transcript(vid, channel_id, root)
     if found is None:
         return False
     src, rec = found
@@ -224,13 +225,14 @@ def take_pipeline_transcript(q, vid, channel_id, root=None):
 
 def pipeline_sweep(q, now_ts):
     """The orchestrator's 13:05 ruling of Nov 16 ("mine each video within 10 minutes of its transcript"): every video
-    waiting on a transcript (probe_retry, captions_pending) inside its moments' life (config.EXPIRY_H) whose next try
-    is later and whose record is in the pipeline's store (pipeline_transcript: every check) is made due now, whatever
-    its own retry time; the fetch step then probes it and takes the record. No YouTube request here (one glob, and a
+    waiting on a transcript (probe_retry, captions_pending, and r120: a stream over, live_waiting with live_status
+    post_live) inside its moments' life (config.EXPIRY_H) whose next try is later and whose record is in the
+    pipeline's store (pipeline_transcript: every check) is made due now, whatever its own retry time; the fetch step
+    then probes it and takes the record (a stream still live never: fetch.process). No YouTube request here (one glob, and a
     read of a record that is there). Returns the ids made due; each is a queue event."""
-    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE state IN (?, ?) AND next_at > ? AND "
-                  "COALESCE(published_ts, discovered_ts) >= ?",
-                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, now_ts, now_ts - config.EXPIRY_H * 3600))
+    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE (state IN (?, ?) OR (state = ? AND live_status = ?)) "
+                  "AND next_at > ? AND COALESCE(published_ts, discovered_ts) >= ?",
+                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", now_ts, now_ts - config.EXPIRY_H * 3600))
     due = []
     for r in rows:
         try:
@@ -239,8 +241,8 @@ def pipeline_sweep(q, now_ts):
         except ValueError:                            # an id transcript_store refuses: never a path, never due here
             continue
     if due:
-        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?) AND video_id IN "
-            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING) + tuple(due))
+        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?, ?) AND video_id IN "
+            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE) + tuple(due))
         for vid in due:
             q.event("pipeline_transcript_due", vid, None)
     return due
@@ -291,10 +293,11 @@ def process(q, gate, v, chan, optout, now_ts=None):
         nxt = max(float(start) + 900, now_ts + 600) if isinstance(start, (int, float)) else now_ts + config.UPCOMING_REPROBE_S
         q.set_state(vid, Q.UPCOMING, next_at=nxt, tries=tries + 1, reason=f"upcoming (scheduled {pub})", **common)
         return Q.UPCOMING
-    if live in ("is_live", "post_live"):
-        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1,
+    found = pipeline_transcript(vid, chan["channel_id"]) if live == "post_live" else None   # read once (audit r120 c1)
+    if live == "is_live" or (live == "post_live" and found is None):
+        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1,      # r120: a stream over
                     reason=f"{live}: re-probed every {config.LIVE_REPROBE_S // 60} min (meta.json not written)", **common)
-        return Q.LIVE
+        return Q.LIVE                    # (post_live) whose record the pipeline has goes on, through every check below
     if pub_ts is None:
         q.set_state(vid, Q.PROBE_RETRY, next_at=_retry_at(now_ts, tries), tries=tries + 1,
                     reason="no publish time measured", **common)
@@ -304,6 +307,9 @@ def process(q, gate, v, chan, optout, now_ts=None):
                     reason=f"published {pub}: older than the {BACKFILL_H} h window", **common)
         return Q.SEEN_OLD
     dur = j.get("duration")
+    if live == "post_live" and not (isinstance(dur, (int, float)) and dur > 0):    # r120: a stream over, its VOD
+        dur = common["duration"] = found[1].get("duration")                          # still processing: its length
+                                                                                       # as the pipeline recorded it
     if not isinstance(dur, (int, float)) or dur <= 0:
         q.set_state(vid, Q.PROBE_RETRY, next_at=_retry_at(now_ts, tries), tries=tries + 1,
                     reason="no duration measured", **common)
@@ -318,8 +324,13 @@ def process(q, gate, v, chan, optout, now_ts=None):
         q.set_state(vid, Q.DUPLICATE, next_at=now_ts + 10 ** 9, duplicate_of=dup, title_canon=tc,
                     reason=f"re-upload of {dup}: {why}", **common)
         return Q.DUPLICATE
-    if take_pipeline_transcript(q, vid, chan["channel_id"]):    # the pipeline's own transcript: no caption download
+    if take_pipeline_transcript(q, vid, chan["channel_id"], found=found):   # the pipeline's own transcript: no caption
         return _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries)
+    if live == "post_live":                  # r120: its record was not taken (the copy differed): wait for the VOD
+        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1, title_canon=tc,
+                    reason=f"post_live: re-probed every {config.LIVE_REPROBE_S // 60} min (meta.json not written)",
+                    **common)
+        return Q.LIVE
     manual, auto = captions_listed(j)
     if not (any(k.startswith("en") for k in manual) or auto):
         if now_ts - pub_ts > config.CAPTION_DEADLINE_H * 3600:
diff --git a/pipeline/ingest/stall.py b/pipeline/ingest/stall.py
index 7dab6f71..6af4eb58 100644
--- a/pipeline/ingest/stall.py
+++ b/pipeline/ingest/stall.py
@@ -3,7 +3,8 @@ waiting and nothing has been mined for 30 minutes, write it on line 1 and act; d
 
 WAITING  a video inside its moments' life (config.EXPIRY_H from its publish, or from its discovery while the publish
          time is not measured yet) in a state that leads to mining: discovered, probing, probe_retry, captions_pending,
-         transcribed, mining, mine_waiting. An upcoming or live stream is not waiting (nothing to mine before its VOD);
+         transcribed, mining, mine_waiting; and (r120) a stream that is over but still processing (live_waiting with
+         live_status post_live). An upcoming stream or one still live is not waiting (nothing to mine before it ends);
          a Short, a duplicate or any other terminal state never is.
 STALLED  something waits and nothing was mined for STALL_S: the later of the newest mined video's time and the oldest
          waiting video's discovery is at least STALL_S old (a video that came in a minute ago is no stall).
@@ -24,7 +25,8 @@ from .spend import STALL_PREFIX
 
 STALL_S = 1800
 WAITING = (Q.DISCOVERED, Q.PROBING, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING, Q.MINE_WAIT)
-RETRYABLE = (Q.DISCOVERED, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.MINE_WAIT)   # never one in flight (probing, mining)
+RETRYABLE = (Q.DISCOVERED, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.MINE_WAIT, Q.LIVE)   # never one in flight; LIVE
+                                                                                   # rows here are post_live ones only
 ET = ZoneInfo("America/New_York")
 
 
@@ -47,6 +49,8 @@ def why(state, reason):
         return "TRANSCRIBED, BEING MINED"
     if state == Q.MINE_WAIT:
         return "NO MODEL OF THE CHAIN ANSWERED" if r.startswith("OUTAGE") else "MINING TO RETRY"
+    if state == Q.LIVE:
+        return "STREAM OVER, ITS VIDEO STILL PROCESSING"
     return state.upper()
 
 
@@ -54,8 +58,9 @@ def check(q, now, expiry_h=None, stall_s=STALL_S):
     """{'stalled', 'waiting' (rows), 'since' (when the stall clock started; None when nothing waits), 'last_mined'}."""
     horizon = now - float(config.EXPIRY_H if expiry_h is None else expiry_h) * 3600
     marks = ",".join("?" * len(WAITING))
-    rows = q.rows(f"SELECT video_id, state, reason, next_at, discovered_ts FROM videos WHERE state IN ({marks}) AND "
-                  "COALESCE(published_ts, discovered_ts) >= ?", tuple(WAITING) + (horizon,))
+    rows = q.rows(f"SELECT video_id, state, reason, next_at, discovered_ts FROM videos WHERE (state IN ({marks}) OR "
+                  "(state = ? AND live_status = ?)) AND COALESCE(published_ts, discovered_ts) >= ?",
+                  tuple(WAITING) + (Q.LIVE, "post_live", horizon))
     last = q.rows("SELECT MAX(mined_ts) AS t FROM videos WHERE state IN (?, ?)", (Q.MINED, Q.MINED_PARTIAL))[0]["t"]
     if not rows:
         return {"stalled": False, "waiting": [], "since": None, "last_mined": last}
diff --git a/tests/ingest/test_r120.py b/tests/ingest/test_r120.py
new file mode 100644
index 00000000..c96db8eb
--- /dev/null
+++ b/tests/ingest/test_r120.py
@@ -0,0 +1,124 @@
+"""tests/ingest/test_r120.py: a stream that is over but still processing (YouTube's live_status post_live).
+
+Found by r119's own measure on Nov 16: Yahoo Finance kh3U_15pFZc was mined 3,205 s after its transcript; YouTube kept
+it post_live from 12:26 to 14:26 ET while the pipeline had Whispered it at 13:33, and the watcher treated post_live as
+live (re-probed every 20 min, outside the sweep). Now a post_live video whose record the pipeline has goes on through
+every other probe check and takes it; the sweep and the self-check cover it. A stream still live never is taken.
+"""
+import json
+import os
+import shutil
+
+import pytest
+
+import helpers as H
+from pipeline.ingest import config, fetch, stall
+from pipeline.ingest import queue as Q
+from test_r118 import add, downloads, pipeline_record, q, staged  # noqa: F401 (q: the queue fixture)
+
+NOW = 1794470000.0
+
+
+def post_live(v, **over):
+    j = dict(live_status="post_live", media_type="livestream", duration=1080, release_timestamp=NOW - 7200,
+             timestamp=NOW - 7200)
+    j.update(over)
+    return H.probe_json(v, **j)
+
+
+def test_a_stream_over_takes_the_pipelines_record_after_every_check(q, monkeypatch):
+    v = H.vid("P")
+    src, rec = pipeline_record(v)
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    row = q.video(v)
+    assert made == [] and row["transcript_method"] == "whisper" and row["live_status"] == "post_live"
+    meta = json.load(open(os.path.join(config.ts()._vdir(v), "meta.json")))
+    assert meta["live_status"] == "post_live" and meta["written_by"] == "pipeline.ingest.fetch"
+
+
+def test_a_stream_over_without_a_record_waits_as_before(q, monkeypatch):
+    v = H.vid("W")
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
+    row = q.video(v)
+    assert made == [] and row["next_at"] == NOW + config.LIVE_REPROBE_S and row["reason"].startswith("post_live")
+    assert not os.path.exists(os.path.join(config.ts()._vdir(v), "meta.json"))
+
+
+def test_a_stream_still_live_is_never_given_its_record(q, monkeypatch):
+    v = H.vid("L")
+    pipeline_record(v)
+    downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v, live_status="is_live", duration=None)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
+    assert not os.path.exists(staged(v)) and q.video(v)["transcript_method"] is None
+
+
+def test_a_stream_over_with_no_length_yet_takes_the_length_the_pipeline_recorded(q, monkeypatch):
+    v = H.vid("D")
+    src, rec = pipeline_record(v, tamper=lambda r: r.update(duration=1066))
+    downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v, duration=None)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    assert q.video(v)["duration"] == 1066
+
+
+@pytest.mark.parametrize("over,state", [(dict(release_timestamp=NOW - 80 * 3600, timestamp=NOW - 80 * 3600), Q.SEEN_OLD),
+                                        (dict(duration=7 * 3600), Q.TOO_LONG)])
+def test_a_stream_over_still_meets_every_other_check(q, monkeypatch, over, state):
+    v = H.vid("C")
+    pipeline_record(v)
+    downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v, **over)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == state
+    assert not os.path.exists(staged(v))
+
+
+def test_a_stream_over_whose_copy_is_refused_waits_for_its_video(q, monkeypatch):
+    v = H.vid("R")
+    pipeline_record(v)
+    real = shutil.copyfile
+
+    def swap(a, b):
+        real(a, b)
+        r = json.load(open(b))
+        r["segments"][0]["text"] = "swapped"
+        json.dump(r, open(b, "w"))
+    monkeypatch.setattr(fetch.shutil, "copyfile", swap)
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: post_live(v)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
+    assert made == [] and not os.path.exists(staged(v))                     # no caption download while post_live
+
+
+def test_the_sweep_and_the_self_check_cover_a_stream_over_never_one_still_live(q):
+    later = NOW + 1200
+    for v, status in (("over0000001", "post_live"), ("live0000001", "is_live")):
+        q.add_video(v, H.CHAN["channel_id"], "t", "rss")
+        q.x("UPDATE videos SET state=?, live_status=?, next_at=?, discovered_ts=?, published_ts=? WHERE video_id=?",
+            (Q.LIVE, status, later, NOW - 2400, NOW - 2400, v))
+        pipeline_record(v)
+    assert fetch.pipeline_sweep(q, NOW) == ["over0000001"]
+    assert q.video("over0000001")["next_at"] == NOW and q.video("live0000001")["next_at"] == later
+    q.x("UPDATE videos SET next_at=? WHERE video_id='over0000001'", (later,))
+    chk = stall.check(q, NOW)
+    assert [r["video_id"] for r in chk["waiting"]] == ["over0000001"] and chk["stalled"]
+    assert "1 STREAM OVER, ITS VIDEO STILL PROCESSING" in stall.line(chk, NOW)
+    assert stall.act(q, chk, NOW) == 1 and q.video("over0000001")["next_at"] == NOW
+    assert q.video("live0000001")["next_at"] == later
+
+
+def test_a_stream_over_reads_the_pipelines_record_once(q, monkeypatch):
+    """Audit r120 c1 (both reviewers): the record is read and hashed once per probe of a stream over, not three times
+    (the live check, the length, the take); the copy is still checked again before it is linked in."""
+    v = H.vid("O")
+    pipeline_record(v)
+    downloads(monkeypatch)
+    real, calls = fetch.pipeline_transcript, []
+    monkeypatch.setattr(fetch, "pipeline_transcript", lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1])
+    gate = H.FakeGate(probes={v: post_live(v, duration=None)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
+    assert calls == [v]

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

