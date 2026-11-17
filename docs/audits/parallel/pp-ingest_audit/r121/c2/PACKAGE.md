# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 5c9ce2b6
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
# r121: a probe answered with yt-dlp's stub is "no metadata", never "waiting" (Nov 16, 19:4x ET)

## Why
The self-check (r118, the orchestrator's 10:50 order (4)) fired at 19:31 ET with 6 videos waiting. 2 of them, Yahoo
Finance nlRpMRMq2bc ("The Daily Wolf with Scott Melker (12:00...") and QSHyMFr-i04, had sat in probe_retry since 12:05
ET as "no publish time measured". One `yt-dlp -J --skip-download --ignore-no-formats-error` read of nlRpMRMq2bc at 19:3x
ET returned the stub yt-dlp emits for a page with no player data: title "youtube video #nlRpMRMq2bc", live_status,
duration, timestamp, release_timestamp, upload_date all None, no captions: a video removed, private or not public
yet. fetch.probe returned it as a probe (its id matches); fetch.process then retried it as "no publish time measured"
every hour forever (PROBE_RETRY_S caps at 3600 s), and stall.check counted it as waiting: it would have raised the
stall line every 30 minutes without mining overnight until the video left the 12 h window.

## The change (pipeline/ingest/fetch.py only)
- fetch.probe: a JSON whose id matches but which carries none of FACT_KEYS (live_status, duration, timestamp,
  release_timestamp, upload_date) is ("no_metadata", ...), not a probe.
- fetch.process: "no_metadata" is UNAVAILABLE (reason "no metadata: ..."), tried again every NO_METADATA_RETRY_S
  (3600 s: as often as before, so a video that turns public is still seen within the hour) and given up after
  NO_METADATA_MAX_TRIES (6). UNAVAILABLE is in Q.FETCH_DUE (retried at its next_at) and not in stall.WAITING
  (unchanged code), so a stub never raises the stall line.
- Any probe with one fact keeps its old path (an upcoming stream: is_upcoming with its start; a VOD missing its
  timestamp: "no publish time measured" as before).

## What to check
- No real video can be read as a stub (each kind of real answer carries at least one of FACT_KEYS).
- A stub is never waiting, never mined, retried no more often than before, and given up.

Suite: tests/ingest 434 passed (3 new in test_r121.py). Mutations M44-M47: 4 of 4 killed.


```diff
diff --git a/pipeline/ingest/fetch.py b/pipeline/ingest/fetch.py
index 7f9c14c2..059181a9 100644
--- a/pipeline/ingest/fetch.py
+++ b/pipeline/ingest/fetch.py
@@ -34,6 +34,9 @@ UNAVAILABLE_MARKS = ("Private video", "Video unavailable", "This video has been
 UNAVAILABLE_RETRY_S = 6 * 3600
 UNAVAILABLE_MAX_TRIES = 4
 PROBE_RETRY_S = (300, 900, 1800, 3600)
+FACT_KEYS = ("live_status", "duration", "timestamp", "release_timestamp", "upload_date")   # r121: what a real probe gives
+NO_METADATA_RETRY_S = 3600          # r121: a probe answered with no fact at all (removed, private or not public yet)
+NO_METADATA_MAX_TRIES = 6           # is tried hourly, then given up: never counted as waiting (stall.WAITING)
 CAPTION_THROTTLED_RETRY_S = 600     # a caption 429: tried again this soon (the pipeline's store is looked at first)
 PIPELINE_RECHECK_S = 1800           # a VOD without English captions inside its moments' life: looked at this often
                                     # (the pipeline's transcript ingest runs every 30 min)
@@ -126,7 +129,7 @@ def text_fingerprint(rec):
 
 
 def probe(gate, video_id):
-    """(json, None) or (None, (kind, detail)). kind: age_gated | unavailable | rate_limited | error."""
+    """(json, None) or (None, (kind, detail)). kind: age_gated | unavailable | no_metadata | rate_limited | error."""
     try:
         r = gate.run(["-J", "--skip-download", "--ignore-no-formats-error",
                       f"https://www.youtube.com/watch?v={video_id}"], timeout=120)
@@ -135,6 +138,8 @@ def probe(gate, video_id):
     try:
         j = json.loads(r.stdout)
         if isinstance(j, dict) and j.get("id") == video_id:
+            if not any(j.get(k) for k in FACT_KEYS):      # r121: yt-dlp's stub ("youtube video #<id>", every fact
+                return None, ("no_metadata", "yt-dlp returned no fact about it (removed, private or not public yet)")
             return j, None
     except ValueError:
         pass
@@ -265,6 +270,11 @@ def process(q, gate, v, chan, optout, now_ts=None):
             q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + 10 ** 9, tries=tries + 1,
                         reason=f"age-gated (needs a signed-in session): {detail[-200:]}")
             return Q.UNAVAILABLE
+        if kind == "no_metadata":                  # r121: off the waiting count; tried hourly, then given up
+            final = tries + 1 >= NO_METADATA_MAX_TRIES
+            q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10 ** 9 if final else NO_METADATA_RETRY_S),
+                        tries=tries + 1, reason=f"no metadata: {detail}")
+            return Q.UNAVAILABLE
         if kind == "unavailable":
             final = tries + 1 >= UNAVAILABLE_MAX_TRIES
             q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10 ** 9 if final else UNAVAILABLE_RETRY_S),
diff --git a/tests/ingest/test_r121.py b/tests/ingest/test_r121.py
new file mode 100644
index 00000000..966a9cb6
--- /dev/null
+++ b/tests/ingest/test_r121.py
@@ -0,0 +1,53 @@
+"""tests/ingest/test_r121.py: a probe answered with yt-dlp's stub (every fact empty) is "no metadata", not waiting.
+
+Found at the 19:31 ET stall of Nov 16: Yahoo Finance nlRpMRMq2bc ("The Daily Wolf with Scott Melker") and QSHyMFr-i04
+had sat in probe_retry since 12:05 ET as "no publish time measured": `yt-dlp -J --ignore-no-formats-error` answers them
+with a stub (title "youtube video #<id>", no live_status, duration, timestamps or captions: removed, private or not
+public yet). Retried every hour forever, they kept the self-check's stall line up overnight. Now such a probe is
+UNAVAILABLE ("no metadata"), tried hourly, given up after NO_METADATA_MAX_TRIES, and never counted as waiting.
+"""
+import pytest
+
+import helpers as H
+from pipeline.ingest import fetch, stall
+from pipeline.ingest import queue as Q
+from test_r118 import add, q  # noqa: F401 (q: the queue fixture)
+
+NOW = 1794470000.0
+
+
+def stub(v):
+    return H.probe_json(v, title=f"youtube video #{v}", live_status=None, duration=None, timestamp=None,
+                        release_timestamp=None, media_type="video", automatic_captions={}, channel_id=None)
+
+
+def test_a_stub_probe_is_no_metadata_tried_hourly_then_given_up(q):
+    v = H.vid("S")
+    gate = H.FakeGate(probes={v: stub(v)})
+    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
+    row = q.video(v)
+    assert row["next_at"] == NOW + fetch.NO_METADATA_RETRY_S == NOW + 3600
+    assert row["reason"].startswith("no metadata: yt-dlp returned no fact")
+    q.x("UPDATE videos SET tries=?, next_at=0", (fetch.NO_METADATA_MAX_TRIES - 1,))
+    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
+    assert q.video(v)["next_at"] >= NOW + 10 ** 9 - 1                      # given up
+
+
+def test_a_probe_with_any_fact_is_not_a_stub(q):
+    up, vod = H.vid("U"), H.vid("V")
+    gate = H.FakeGate(probes={up: H.probe_json(up, live_status="is_upcoming", release_timestamp=NOW + 3600,
+                                               duration=None),
+                              vod: H.probe_json(vod, timestamp=None, duration=None, upload_date="20261112",
+                                                automatic_captions={})})
+    assert fetch.process(q, gate, add(q, up), H.CHAN, set(), now_ts=NOW) == Q.UPCOMING
+    assert fetch.process(q, gate, add(q, vod), H.CHAN, set(), now_ts=NOW) == Q.PROBE_RETRY   # its old path
+    assert q.video(vod)["reason"] == "no publish time measured"
+
+
+def test_a_stub_is_never_counted_as_waiting(q):
+    v = H.vid("W")
+    gate = H.FakeGate(probes={v: stub(v)})
+    fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW)
+    q.x("UPDATE videos SET discovered_ts=? WHERE video_id=?", (NOW - 3600, v))
+    chk = stall.check(q, NOW)
+    assert chk["waiting"] == [] and chk["stalled"] is False

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

