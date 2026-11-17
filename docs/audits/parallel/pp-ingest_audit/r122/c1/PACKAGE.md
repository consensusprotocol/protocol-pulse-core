# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 9df2df43
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
# r122: a stub can be a moment's answer for a real video (Nov 17, 07:4x ET)

## Why
r121 (live since 19:42 ET Nov 16) files a probe that yt-dlp answers with its stub (none of live_status, duration,
timestamp, release_timestamp, upload_date) as UNAVAILABLE "no metadata", and gave it up after NO_METADATA_MAX_TRIES (6)
counted on the row's `tries`. CoinDesk yHuY9r30Oug ("CoinDesk Live at Solana Breakpoint 2026 Day 1 | Replay") was
live 01:08-02:08 ET Nov 17 (four re-probes, each a try), then yt-dlp answered two probes with a stub (02:28, 03:28):
`tries` reached 6 and it was given up. The pipeline's transcript ingest Whispered it at 07:00 (112 min of audio) and a
probe at 07:4x gave every fact again (post_live, 6,728 s, release_timestamp): the stub was a moment's answer (around a
premiere's end), and the watcher would never have mined a video the pipeline had transcribed.

## The change (pipeline/ingest/fetch.py)
- "no metadata" is given up only once the video is past its moments' life (config.EXPIRY_H from its publish, else its
  discovery), never on a count of tries (which holds its live re-probes); inside it, tried again every
  NO_METADATA_RETRY_S, now 900 s (a stub can pass in minutes; a dead video costs one probe a quarter hour, 48 at most).
- fetch.pipeline_sweep also makes due an UNAVAILABLE video whose reason is "no metadata: ..." once the pipeline's store
  holds its record (the pipeline saw it, so it exists); any other UNAVAILABLE (private, removed, age-gated: answered by
  YouTube) is never touched. fetch.process then probes it: facts -> the usual paths (r120 for a stream over); a stub
  again -> UNAVAILABLE again.
- tests/ingest/test_r121.py follows the new give-up rule.

## What to check
- A video YouTube really refuses (private, removed: UNAVAILABLE_MARKS) is never retried more than before.
- A stub never waits as a stall (UNAVAILABLE is outside stall.WAITING) and is given up past 12 h.
- The sweep's new clause takes only "no metadata" rows with a record, inside 12 h.

Suite: tests/ingest 437 passed (3 new in test_r122.py). Mutations M44-M50: 7 of 7 killed.


```diff
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index 059181a9..acb59294 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -35,8 +35,9 @@ UNAVAILABLE_RETRY_S = 6 * 3600
 UNAVAILABLE_MAX_TRIES = 4
 PROBE_RETRY_S = (300, 900, 1800, 3600)
 FACT_KEYS = ("live_status", "duration", "timestamp", "release_timestamp", "upload_date")   # r121: what a real probe gives
-NO_METADATA_RETRY_S = 3600          # r121: a probe answered with no fact at all (removed, private or not public yet)
-NO_METADATA_MAX_TRIES = 6           # is tried hourly, then given up: never counted as waiting (stall.WAITING)
+NO_METADATA_RETRY_S = 900           # r121/r122: a probe answered with no fact at all (removed, private, not public
+                                    # yet, or a moment's stub: CoinDesk yHuY9r30Oug, Nov 17) is tried every 15 min
+                                    # inside its moments' life, then given up; never counted as waiting
 CAPTION_THROTTLED_RETRY_S = 600     # a caption 429: tried again this soon (the pipeline's store is looked at first)
 PIPELINE_RECHECK_S = 1800           # a VOD without English captions inside its moments' life: looked at this often
                                     # (the pipeline's transcript ingest runs every 30 min)
@@ -235,9 +236,10 @@ def pipeline_sweep(q, now_ts):
     pipeline's store (pipeline_transcript: every check) is made due now, whatever its own retry time; the fetch step
     then probes it and takes the record (a stream still live never: fetch.process). No YouTube request here (one glob, and a
     read of a record that is there). Returns the ids made due; each is a queue event."""
-    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE (state IN (?, ?) OR (state = ? AND live_status = ?)) "
-                  "AND next_at > ? AND COALESCE(published_ts, discovered_ts) >= ?",
-                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", now_ts, now_ts - config.EXPIRY_H * 3600))
+    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE (state IN (?, ?) OR (state = ? AND live_status = ?) "
+                  "OR (state = ? AND reason LIKE ?)) AND next_at > ? AND COALESCE(published_ts, discovered_ts) >= ?",
+                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", Q.UNAVAILABLE, "no metadata:%", now_ts,
+                   now_ts - config.EXPIRY_H * 3600))   # r122: the pipeline's record proves a stub's video exists
     due = []
     for r in rows:
         try:
@@ -246,8 +248,9 @@ def pipeline_sweep(q, now_ts):
         except ValueError:                            # an id transcript_store refuses: never a path, never due here
             continue
     if due:
-        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?, ?) AND video_id IN "
-            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE) + tuple(due))
+        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?, ?, ?) AND video_id IN "
+            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, Q.UNAVAILABLE)
+            + tuple(due))
         for vid in due:
             q.event("pipeline_transcript_due", vid, None)
     return due
@@ -270,8 +273,9 @@ def process(q, gate, v, chan, optout, now_ts=None):
             q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + 10 ** 9, tries=tries + 1,
                         reason=f"age-gated (needs a signed-in session): {detail[-200:]}")
             return Q.UNAVAILABLE
-        if kind == "no_metadata":                  # r121: off the waiting count; tried hourly, then given up
-            final = tries + 1 >= NO_METADATA_MAX_TRIES
+        if kind == "no_metadata":                  # r121: off the waiting count; r122: given up only past its
+            seen = v.get("published_ts") or v.get("discovered_ts") or now_ts    # moments' life (a count of tries
+            final = now_ts - float(seen) > config.EXPIRY_H * 3600                 # holds its live re-probes too)
             q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10 ** 9 if final else NO_METADATA_RETRY_S),
                         tries=tries + 1, reason=f"no metadata: {detail}")
             return Q.UNAVAILABLE
diff --git a/tests/ingest/test_r121.py b/tests/ingest/test_r121.py
index 966a9cb6..018e0332 100644
--- a/tests/ingest/test_r121.py
+++ b/tests/ingest/test_r121.py
@@ -4,7 +4,8 @@ Found at the 19:31 ET stall of Nov 16: Yahoo Finance nlRpMRMq2bc ("The Daily Wol
 had sat in probe_retry since 12:05 ET as "no publish time measured": `yt-dlp -J --ignore-no-formats-error` answers them
 with a stub (title "youtube video #<id>", no live_status, duration, timestamps or captions: removed, private or not
 public yet). Retried every hour forever, they kept the self-check's stall line up overnight. Now such a probe is
-UNAVAILABLE ("no metadata"), tried hourly, given up after NO_METADATA_MAX_TRIES, and never counted as waiting.
+UNAVAILABLE ("no metadata"), tried again every NO_METADATA_RETRY_S, given up only once the video is past its moments'
+life (r122, test_r122.py: a count of tries gave up a real stream), and never counted as waiting.
 """
 import pytest
 
@@ -21,16 +22,21 @@ def stub(v):
                         release_timestamp=None, media_type="video", automatic_captions={}, channel_id=None)
 
 
-def test_a_stub_probe_is_no_metadata_tried_hourly_then_given_up(q):
+def test_a_stub_probe_is_no_metadata_retried_inside_its_moments_life_then_given_up(q):
+    from pipeline.ingest import config
     v = H.vid("S")
     gate = H.FakeGate(probes={v: stub(v)})
     assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
     row = q.video(v)
-    assert row["next_at"] == NOW + fetch.NO_METADATA_RETRY_S == NOW + 3600
+    assert row["next_at"] == NOW + fetch.NO_METADATA_RETRY_S == NOW + 900
     assert row["reason"].startswith("no metadata: yt-dlp returned no fact")
-    q.x("UPDATE videos SET tries=?, next_at=0", (fetch.NO_METADATA_MAX_TRIES - 1,))
-    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
-    assert q.video(v)["next_at"] >= NOW + 10 ** 9 - 1                      # given up
+    q.x("UPDATE videos SET tries=99, next_at=0")                            # r122: tries never give it up
+    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + 3600) == Q.UNAVAILABLE
+    assert q.video(v)["next_at"] == NOW + 3600 + 900
+    later = NOW + (config.EXPIRY_H + 1) * 3600                               # past its moments' life: given up
+    q.x("UPDATE videos SET next_at=0")
+    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=later) == Q.UNAVAILABLE
+    assert q.video(v)["next_at"] >= later + 10 ** 9 - 1
 
 
 def test_a_probe_with_any_fact_is_not_a_stub(q):
diff --git a/tests/ingest/test_r122.py b/tests/ingest/test_r122.py
new file mode 100644
index 00000000..4e170329
--- /dev/null
+++ b/tests/ingest/test_r122.py
@@ -0,0 +1,61 @@
+"""tests/ingest/test_r122.py: a stub probe can be a moment's answer for a real video.
+
+Nov 17: CoinDesk yHuY9r30Oug ("Solana Breakpoint Day 1 | Replay") was live 01:08-02:08 ET (four re-probes), then
+yt-dlp answered two probes with a stub (02:28, 03:28); r121 gave it up on a count of tries that held the live
+re-probes, while the pipeline transcribed it at 07:00 and a probe at 07:4x gave every fact again (post_live, 6,728 s).
+Now a stub is given up only past its moments' life, and the sweep makes a "no metadata" video due once the
+pipeline's store holds its record (the pipeline saw it: it exists).
+"""
+import helpers as H
+from pipeline.ingest import fetch
+from pipeline.ingest import queue as Q
+from test_r118 import add, downloads, pipeline_record, q  # noqa: F401 (q: the queue fixture)
+from test_r120 import post_live
+from test_r121 import stub
+
+NOW = 1794470000.0
+
+
+def test_a_stream_live_for_an_hour_then_answered_with_a_stub_is_not_given_up(q):
+    v = H.vid("C")
+    gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_live", media_type="livestream", duration=None,
+                                              release_timestamp=NOW - 3600)})
+    add(q, v)
+    for k in range(4):                                                   # four live re-probes
+        q.x("UPDATE videos SET next_at=0")
+        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + k * 1200) == Q.LIVE
+    gate.probes[v] = stub(v)
+    for k in range(2):                                                   # then two stubs
+        q.x("UPDATE videos SET next_at=0")
+        t = NOW + 4800 + k * 3600
+        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=t) == Q.UNAVAILABLE
+        assert q.video(v)["next_at"] == t + fetch.NO_METADATA_RETRY_S     # never given up inside its 12 h
+
+
+def test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record(q):
+    for v, rec, age in (("stub0000001", True, 3600), ("stub0000002", False, 3600), ("stub0000003", True, 13 * 3600)):
+        q.add_video(v, H.CHAN["channel_id"], "t", "rss")
+        q.x("UPDATE videos SET state=?, reason=?, next_at=?, discovered_ts=?, published_ts=? WHERE video_id=?",
+            (Q.UNAVAILABLE, "no metadata: yt-dlp returned no fact about it", NOW + 900, NOW - age, NOW - age, v))
+        if rec:
+            pipeline_record(v)
+    q.add_video("gone0000001", H.CHAN["channel_id"], "t", "rss")       # unavailable for another reason: untouched
+    q.x("UPDATE videos SET state=?, reason=?, next_at=?, discovered_ts=? WHERE video_id='gone0000001'",
+        (Q.UNAVAILABLE, "yt-dlp: Private video", NOW + 900, NOW - 3600))
+    pipeline_record("gone0000001")
+    assert fetch.pipeline_sweep(q, NOW) == ["stub0000001"]
+    assert q.video("stub0000001")["next_at"] == NOW
+    assert q.video("stub0000002")["next_at"] == q.video("stub0000003")["next_at"] == NOW + 900
+    assert q.video("gone0000001")["next_at"] == NOW + 900
+
+
+def test_a_stub_whose_video_answers_again_takes_the_pipelines_record(q, monkeypatch):
+    v = H.vid("R")
+    pipeline_record(v)
+    downloads(monkeypatch)
+    gate = H.FakeGate(probes={v: stub(v)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
+    assert fetch.pipeline_sweep(q, NOW + 60) == [v]                       # the pipeline holds its record
+    gate.probes[v] = post_live(v)                                          # YouTube answers it again
+    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + 61) == Q.TRANSCRIBED
+    assert q.video(v)["transcript_method"] == "whisper"

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

