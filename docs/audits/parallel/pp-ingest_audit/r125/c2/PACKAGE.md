# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at cfd3bb9a0
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
# r125: a stream last seen live takes the pipeline's record within the sweep, not at its 20-min re-probe (Nov 18)

## Why (found by r119's own measure)
The orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its transcript". On Nov 18 the
measure (transcript_lag_s) showed Fox Business J0UvqtdsBmc at 462 s: a scheduled live show, probed is_live at 09:20
ET; the pipeline's transcript ingest Whispered it at 09:32 (acquired_at 14:32:43Z: it transcribes a stream only once its
own probe sees it over: transcript_store.acquire skips is_live / is_upcoming); fetch.pipeline_sweep (every 60 s)
looked at transcript waits and, since r120, at post_live rows, but never at a row whose last probe said is_live
(r120's invariant: "the sweep never touches an is_live row"), so the record waited for the 09:40 re-probe
(config.LIVE_REPROBE_S = 1200). Inside the bound this time; by design this path could wait up to ~20 min. Of 229
videos with a measured lag, 4 took over 300 s, 2 were LATE: both live rows, on the paths r120 and r122 fixed.

## The change (pipeline/ingest/fetch.py)
- pipeline_sweep also selects a row in live_waiting whose stored live_status is is_live, and makes it due ONCE: only
  when its pipeline record's acquired_at is LATER than the row's state_at (the time of its last probe). Every probe
  of a live row ends in Queue.set_state, which rewrites state_at (queue.py:166 `state_at=config.iso()`), so after the
  probe the same record is no longer newer: no loop of probes. fetch.process is unchanged: a probe that still says
  is_live sets it LIVE again (never taken, no caption download, no meta); post_live takes the record (r120); was_live /
  not_live take it before captions (r118).
- _zoned(s): a time with its zone ('Z' read as UTC), else None (as service.transcript_lag reads acquired_at); a time
  without its zone never makes a live row due (it waits for its re-probe as before).
- Every other wait keeps its rule (any record makes it due): probe_retry, captions_pending, post_live (r120), and an
  unavailable "no metadata" stub (r122).
- tests/ingest/test_r120.py: its sweep test's still-live row now has a record OLDER than its probe (so r125 leaves it,
  as r120 did); the case r125 adds is test_r125's.

## Unchanged code the change relies on (not in the diff)
- queue.py:162-169 Queue.set_state: `f = dict(f, state=state, state_at=config.iso(), next_at=...)` on every call;
  queue.py:171-177 claim() also sets state_at.
- fetch.py process(): `found = pipeline_transcript(vid, ...) if live == "post_live" else None` and `if live ==
  "is_live" or (live == "post_live" and found is None): q.set_state(vid, Q.LIVE, next_at=now_ts + LIVE_REPROBE_S, ...)`
  (a stream still live is never taken).
- The pipeline's records carry acquired_at as ISO 8601 with its zone (e.g. "2026-11-18T14:32:43.041518+00:00").

## What to check
- A stream YouTube still calls live can never be taken, nor probed more than once per new record.
- The other waits' rule is unchanged.
- A missing or zoneless time fails closed (no extra probe).

Suite: tests/ingest 449 passed (5 new in test_r125.py). Mutations M69-M73: 5 of 5 killed; test_r125 passes unmutated
under the mutation runs' guarded environment.


```diff
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index acb592948..cef0ec5fa 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -229,30 +229,52 @@ def take_pipeline_transcript(q, vid, channel_id, root=None, found=None):
     return True
 
 
+def _zoned(s):
+    """A time with its zone (ISO 8601, 'Z' read as UTC), else None: a time without its zone is no time."""
+    try:
+        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
+    except (TypeError, ValueError):
+        return None
+    return d if d.tzinfo is not None else None
+
+
 def pipeline_sweep(q, now_ts):
     """The orchestrator's 13:05 ruling of Nov 16 ("mine each video within 10 minutes of its transcript"): every video
     waiting on a transcript (probe_retry, captions_pending, and r120: a stream over, live_waiting with live_status
     post_live) inside its moments' life (config.EXPIRY_H) whose next try is later and whose record is in the
     pipeline's store (pipeline_transcript: every check) is made due now, whatever its own retry time; the fetch step
     then probes it and takes the record (a stream still live never: fetch.process). No YouTube request here (one glob, and a
-    read of a record that is there). Returns the ids made due; each is a queue event."""
-    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE (state IN (?, ?) OR (state = ? AND live_status = ?) "
-                  "OR (state = ? AND reason LIKE ?)) AND next_at > ? AND COALESCE(published_ts, discovered_ts) >= ?",
-                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", Q.UNAVAILABLE, "no metadata:%", now_ts,
-                   now_ts - config.EXPIRY_H * 3600))   # r122: the pipeline's record proves a stub's video exists
-    due = []
+    read of a record that is there). Returns the ids made due; each is a queue event.
+    r125: a stream whose last probe still said is_live is made due ONCE when a record acquired after that probe (its
+    row's state_at) lands: the pipeline transcribes a stream only once its own probe sees it over, so the fetch step
+    probes it now instead of at its 20-min re-probe (Fox Business J0UvqtdsBmc, Nov 18: 462 s). Every probe rewrites
+    state_at, so a stream still live is probed once per record, never in a loop, and never taken."""
+    rows = q.rows("SELECT video_id, channel_id, state, live_status, state_at FROM videos WHERE (state IN (?, ?) OR "
+                  "(state = ? AND live_status IN (?, ?)) OR (state = ? AND reason LIKE ?)) AND next_at > ? AND "
+                  "COALESCE(published_ts, discovered_ts) >= ?",
+                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", "is_live", Q.UNAVAILABLE, "no metadata:%",
+                   now_ts, now_ts - config.EXPIRY_H * 3600))   # r122: the pipeline's record proves a stub's video exists
+    due, why = [], {}
     for r in rows:
         try:
-            if pipeline_transcript(r["video_id"], r["channel_id"]) is not None:
-                due.append(r["video_id"])
+            found = pipeline_transcript(r["video_id"], r["channel_id"])
         except ValueError:                            # an id transcript_store refuses: never a path, never due here
             continue
+        if found is None:
+            continue
+        if r["state"] == Q.LIVE and r["live_status"] == "is_live":     # r125: a record newer than the live probe
+            got, probed = _zoned(found[1].get("acquired_at")), _zoned(r["state_at"])
+            if got is None or probed is None or got <= probed:
+                continue
+            why[r["video_id"]] = {"live_status": "is_live", "acquired_at": got.isoformat(),   # audit r125 c1: the
+                                  "probed_at": probed.isoformat()}                          # two times, on its event
+        due.append(r["video_id"])
     if due:
         q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?, ?, ?) AND video_id IN "
             f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, Q.UNAVAILABLE)
             + tuple(due))
         for vid in due:
-            q.event("pipeline_transcript_due", vid, None)
+            q.event("pipeline_transcript_due", vid, None, **why.get(vid, {}))
     return due
 
 
diff --git a/tests/ingest/test_r120.py b/tests/ingest/test_r120.py
index c96db8eb0..13f63bb1e 100644
--- a/tests/ingest/test_r120.py
+++ b/tests/ingest/test_r120.py
@@ -100,7 +100,8 @@ def test_the_sweep_and_the_self_check_cover_a_stream_over_never_one_still_live(q
         q.add_video(v, H.CHAN["channel_id"], "t", "rss")
         q.x("UPDATE videos SET state=?, live_status=?, next_at=?, discovered_ts=?, published_ts=? WHERE video_id=?",
             (Q.LIVE, status, later, NOW - 2400, NOW - 2400, v))
-        pipeline_record(v)
+        pipeline_record(v, tamper=None if status == "post_live" else      # r125: a still-live row's record older
+                        (lambda r: r.update(acquired_at="2026-01-01T00:00:00+00:00")))   # than its probe: never due
     assert fetch.pipeline_sweep(q, NOW) == ["over0000001"]
     assert q.video("over0000001")["next_at"] == NOW and q.video("live0000001")["next_at"] == later
     q.x("UPDATE videos SET next_at=? WHERE video_id='over0000001'", (later,))
diff --git a/tests/ingest/test_r125.py b/tests/ingest/test_r125.py
new file mode 100644
index 000000000..7ea372be8
--- /dev/null
+++ b/tests/ingest/test_r125.py
@@ -0,0 +1,85 @@
+"""tests/ingest/test_r125.py: a stream last seen live takes the pipeline's record within the sweep, not at its re-probe.
+
+Found by r119's own measure on Nov 18: Fox Business J0UvqtdsBmc (a scheduled live show) was probed is_live at 09:20 ET;
+the pipeline's transcript ingest Whispered it at 09:32 (it transcribes a stream only once its own probe sees it over);
+the sweep never looked at an is_live row, so the record waited for the 09:40 re-probe: 462 s from its transcript (the
+re-probe is every 20 min, so this path could have passed the 13:05 ruling's 10 minutes). Now the sweep makes such a row
+due ONCE when a record acquired after its last probe (state_at) lands; the probe decides (a stream still live is never
+taken) and rewrites state_at, so it is never made due again for the same record.
+"""
+import json
+from datetime import datetime, timedelta, timezone
+
+import helpers as H
+from pipeline.ingest import config, fetch
+from pipeline.ingest import queue as Q
+from test_r118 import downloads, pipeline_record, q, staged  # noqa: F401 (q: the queue fixture)
+
+NOW = 1794470000.0
+REAL = datetime.now(timezone.utc)                    # state_at is wall time (Queue.set_state: config.iso())
+
+
+def iso(dt):
+    return dt.isoformat()
+
+
+def live_row(q, v, live="is_live", state=Q.LIVE, probed=REAL - timedelta(hours=1)):
+    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
+    q.x("UPDATE videos SET state=?, live_status=?, next_at=?, discovered_ts=?, published_ts=?, state_at=? "
+        "WHERE video_id=?", (state, live, NOW + 1200, NOW - 2400, NOW - 2400, iso(probed), v))
+
+
+def record(v, acquired):
+    return pipeline_record(v, tamper=lambda r: r.update(acquired_at=acquired))
+
+
+def test_a_stream_last_seen_live_is_made_due_once_and_never_taken_while_still_live(q, monkeypatch):
+    v = H.vid("L")
+    live_row(q, v)
+    record(v, iso(REAL - timedelta(minutes=50)))          # landed after the probe that said live
+    assert fetch.pipeline_sweep(q, NOW) == [v] and q.video(v)["next_at"] == NOW
+    ev = [json.loads(d) for (d,) in q.db.execute("SELECT detail FROM events WHERE video_id=? AND kind=?",
+                                                 (v, "pipeline_transcript_due"))]
+    assert ev == [{"live_status": "is_live", "acquired_at": iso(REAL - timedelta(minutes=50)),        # audit r125
+                   "probed_at": iso(REAL - timedelta(hours=1))}]                                      # c1: why
+    made = downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_live", media_type="livestream", duration=None,
+                                              release_timestamp=NOW - 2400, timestamp=NOW - 2400)})
+    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.LIVE      # YouTube still says live
+    assert made == [] and q.video(v)["transcript_method"] is None
+    assert fetch.pipeline_sweep(q, NOW + 60) == []        # the probe rewrote state_at: once per record, no loop
+    assert q.video(v)["next_at"] == NOW + config.LIVE_REPROBE_S
+
+
+def test_a_record_no_newer_than_the_live_probe_never_makes_it_due(q):
+    v = H.vid("O")
+    live_row(q, v, probed=REAL - timedelta(minutes=10))
+    record(v, iso(REAL - timedelta(minutes=40)))          # the probe at -10 min already saw the stream after it
+    assert fetch.pipeline_sweep(q, NOW) == [] and q.video(v)["next_at"] == NOW + 1200
+
+
+def test_a_time_without_its_zone_never_makes_a_live_stream_due(q):
+    a, b = H.vid("A"), H.vid("B")
+    live_row(q, a)
+    record(a, (REAL - timedelta(minutes=50)).replace(tzinfo=None).isoformat())          # the record's time: no zone
+    live_row(q, b, probed=(REAL - timedelta(hours=1)).replace(tzinfo=None))            # the probe's time: no zone
+    record(b, iso(REAL - timedelta(minutes=50)))
+    assert fetch.pipeline_sweep(q, NOW) == []
+
+
+def test_a_z_time_is_read_as_utc(q):
+    v = H.vid("Z")
+    live_row(q, v)
+    record(v, (REAL - timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ"))
+    assert fetch.pipeline_sweep(q, NOW) == [v]
+
+
+def test_the_other_waits_keep_their_rule_any_record_makes_them_due(q):
+    """r119 / r120 unchanged: a transcript wait, or a stream over (post_live), is made due by any record, whatever its
+    time; even a probe_retry row whose stored live_status is is_live."""
+    over, retry = H.vid("P"), H.vid("R")
+    live_row(q, over, live="post_live", probed=REAL)
+    record(over, iso(REAL - timedelta(hours=2)))
+    live_row(q, retry, state=Q.PROBE_RETRY, probed=REAL)
+    record(retry, iso(REAL - timedelta(hours=2)))
+    assert sorted(fetch.pipeline_sweep(q, NOW)) == sorted([over, retry])

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

