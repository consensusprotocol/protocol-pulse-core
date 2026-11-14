# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1008
# Branch: pp-selectid
# Generated: 2026-11-14 10:18 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation at a place a listener hears as the break between the two
  words (DEC-10, 2026-11-11: no minimum pause; the 01:50 order's 80 ms is recalibrated to the approved v2f
  reference, whose edges measure 0-10 ms; pipeline/sentence_law.py states every constant with its
  measurement). An unpunctuated transcript stretch has NO boundary
  (fail closed). Punctuation is added at transcription time only from a second, prompted ASR decode of
  the same audio, onto aligned verbatim words; the words never change (pipeline/punctuation.py). No
  language model decides a boundary (the per-gap adjudicator called 19/19 gaps sentence ends; removed).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the heard gap between the chosen sentence and its neighbour
  (the previous word's offset .. the next word's onset, at speech - 6 dB); it may never add or drop a word.
  A short gap is cut at the envelope minimum between the two words, never rejected for its length (DEC-10 d);
  its fade sits inside the gap (L-b: 2 video frames = 83 ms when it fits, down to 10 ms).
- NEIGHBOUR (DEC-10 c-ii): NO audible part of the neighbouring word: every frame the cut keeps on the
  neighbour's side of that minimum stays below the valley threshold (local speech - 12 dB) after the fade.
  A window is rejected for its edges only if this, the 85 % edge-word rule or sentence-completeness fails.
- ONSET/TAIL: edge words keep >= 85 % of their duration in the render (a floor for timestamp noise, never
  permission to trim: L-b below). The START OF PLAYBACK keeps the D1
  rule unchanged: a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine
  sub-speech audio before the first onset or a declared room-tone lead-in pad; codec zero/padding is not
  room tone. Inside the video there is no lead / tail minimum (DEC-10: v2f's approved edges: 0 ms).
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12 / G15 measure the brand-red rings the renderer
  draws and G15 checks each disc is the credited channel's registered avatar (DEC-11).
- L-a SIGN-OFF NAMES ALL (PBX, 2026-11-11): the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical.
  Check: run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f.
- L-b EDGE WORDS WHOLE (PBX, 2026-11-11): a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay.
  Check: sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges.
- L-c DISSENT IS RIGHT UNTIL DISPROVED (PBX, 2026-11-11): a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise.
  Check: run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G16's neighbour_clear passes and G17c, MEASURED ON THE FINAL FILE OF THAT FORMAT (sentence_law.edges_on_final: the bytes being approved, their constant gain removed, every frame of the edge word compared), passes for that edge; a proof from the prepared clip is never accepted (amended by the orchestrator addendum 2026-11-11 '22:00', GPT-cut F03). Test: test_release_auth / test_word_diff TestSpanMatches; sentence_law.edge_word_fidelity refuses an alignment that leaves a word frame uncompared (GPT-cut F07).
- L-d PROTECTED PREVIEW (PBX, 2026-11-11): the PBX-approved preview of 2026-11-11 is a protected reference.
  Check: pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS).
- L-e PUNCTUATED BEFORE READ (2026-11-11): Every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read.
  Check: transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py.
- L-f CHANNELS FIRST (DEC-13, orchestrator 2026-11-11 18:00): Story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted.
  Check: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py.
- L-g WRITTEN FORMS (2026-11-11): A check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way.
  Check: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
- L-h TEXT READ AS SPOKEN (2026-11-12): Transcript text is read as the words it stands for before any chunk, quote check or model sees it: caption HTML entities are decoded ('S&amp;P' = 'S&P') and a Whisper word split into tokens is read whole ('$81 ,000' = '$81,000'); the stored record is never rewritten.
  Check: transcript_store.read_text builds every chunk's text; story_semantics._norm decodes entities and joins split tokens for quote checks; the embedding cache is versioned (t2) so vectors match the read text. Must-fail / must-pass: Altcoin Daily's 'S&P 500' quote and Natalie Brunell's '$81,000' quote against their real excerpts (pipeline/test_caption_entities.py).
- L-i THE CLAIM IS THE EVENT (DEC-13 a) (2026-11-12): A channel cluster's claim is the event its coverage is judged against: its query is derived from the claim alone and the model never re-reads it as another event.
  Check: story_semantics.derive_story_query: a transcript_cluster item is derived from the claim with CLUSTER_NOTE (no label summary) and its underlying_event is the claim verbatim (the model's reading kept as underlying_event_derived); wire items byte-identical. Test: test_caption_entities TestClusterClaimIsTheEvent; real model (DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off / ETF-outflow claim.
- L-j RELEASE IS AUTHORISED ON THESE BYTES (red-team order 2026-11-11 '21:55', A): 'all release gates passed' means every REQUIRED gate ran, on samples, unwaived, on exactly the bytes that are sent.
  Check: pipeline/release_auth.py is the one authorisation every send path uses: exact gate inventory v1 (REQUIRED rows exactly 'PASS' with evidence executed and samples >= 1; MONITORING rows present with an exact verdict, reported, not deciding: addendum '22:15' item 4; any other or missing row = blocker); run_fresh writes ATTESTATION.json last (holds anywhere = HOLD; executed code at the launch revision; the finals and manifests must be the bytes the gates measured); authorise() re-hashes both finals, EDL, manifests, gate report, verification pack and sheets before the first send; telegram.deliver_run checks each file's digest again before its send, checkpoints every message, never resends an unknown outcome; the legacy send_telegram_preview is removed; replays are never deliverable. Tests: test_release_auth.py (the fail-closed mutation family), test_telegram_delivery.py, test_failure_blocks.py.
- L-k ONE CANONICAL FORM (orchestrator 2026-11-11 '21:10'): every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does.
  Check: canon.canon_tokens / canon_aligned / same (entities, unicode, split tokens, numbers as values, currency and percent spoken order, signs, apostrophes kept); routed into quote verification, selection anchors, edge words, G3 / G3b, G18 (word_diff keeps units and signs; a repeat-only difference is decided by the audio, sentence_law.span_matches: GPT-cut F04 / F05), G20, G1 / G13 (token runs, never substrings), PIN approved text. Tests: test_canon.py (200 real sentences x mutations equal; real differences unequal; TestSites fails any ad-hoc normaliser outside canon.py).
- L-l A MODEL REPLY COUNTS ONLY WHOLE (red-team order 2026-11-11 '21:55', B): a local-model reply feeds a decision only when every field that decision reads is present, of its exact type, inside its enumerated values and ranges; anything else is a failed call (INCONCLUSIVE / unrated / not producible), never a pass, an agreement or a default.
  Check: pipeline/story_semantics._field / _str_list and the validators _v_derive, _v_adj, _v_sup, _v_react, _v_label, _v_rate run inside LocalLLM.chat_json (bounded retries, then LLMParseError; a cached reply is re-validated on read and asked again when it fails); verify_support counts SUPPORTS only when same_actor_action_object is exactly True and presented_as is exactly 'current' ('unclear' = INCONCLUSIVE; GPT-select F01); every passage is rated exactly once with a 1-5 number and a known fault, never clamped (GPT-select F12); a positive adjudication carries its chunk ids and quote; harmless variations the prompt allows are accepted (an integral float as an int, enum case / whitespace, an absent optional reason, null aliases). Tests: test_editorial_robust.py (one defect per deciding field = a failed call; through the real call = INCONCLUSIVE, never counted; harmless variations accepted), test_dec13_clusters TestLLMCache.
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1008/C1_STEP.diff (307 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | index f76a69e..7509287 100644
   3 | --- a/pipeline/heimdall_health.py
   4 | +++ b/pipeline/heimdall_health.py
   5 | @@ -1,11 +1,17 @@
   6 |  """RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
   7 |  (verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.
   8 |  
   9 | -- Heimdall is DOWN when NO Heimdall family answers a verdict or writer call inside its deadline for DOWN_AFTER_S (15
  10 | -  minutes) running: note(False) starts the clock (failing_since), any note(True) stops it. One model down is not
  11 | -  'down': that is ruling 82's chain, and any family's answer stops the clock.
  12 | -- While calls are failing, and while in Plan B, a cheap probe (probe_due / probe_result) runs every PROBE_EVERY_S
  13 | -  (2 minutes).
  14 | +- RULING 87 AMENDED (orchestrator 10:06 Nov 14, after the false outage of 09:16-09:22: one 502 on a calibration call,
  15 | +  then silence, and the clock ran while every probe was answering): Heimdall is DOWN when there is NO SUCCESSFUL
  16 | +  ANSWER OF ANY KIND for DOWN_AFTER_S (15 minutes) running. note(False) starts the clock (failing_since); an answered
  17 | +  call (note(True)) OR an answered probe (probe_result(True) while heimdall_first) resets it to zero. One model down is
  18 | +  not 'down': that is ruling 82's chain, and any family's answer resets the clock.
  19 | +- While the clock runs, and while in Plan B, the probe (probe_due / probe_result) goes every PROBE_EVERY_S (2
  20 | +  minutes), so one failed call followed by one good probe is never 'down'. A probe is a REAL model call on the family
  21 | +  that failed and one other, never a ping (the caller makes it: providers.Router.probe_once asks each of its Heimdall
  22 | +  families). note(False, family=...) records the failed family (failing_families, cleared by any answer); while the
  23 | +  clock runs, a prober that names its families (probe_due(families=...)) and can ask none of the failed ones leaves
  24 | +  the slot to the prober that can (the builder and pp-ingest call different families). In plan_b any prober claims.
  25 |  - Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  26 |    BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
  27 |  - Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  28 | @@ -13,7 +19,7 @@
  29 |    physical line).
  30 |  
  31 |  The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
  32 | -"probe_streak", "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  33 | +"probe_streak", "failing_families": [...], "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  34 |  'up' or 'down' by guess: note() / mode() raise HealthUnreadable (fail closed: the caller decides, and says so).
  35 |  CPU only; no model call here (the caller makes the probe call and reports it)."""
  36 |  import fcntl
  37 | @@ -132,10 +138,11 @@ def _prepend(state_md, head):
  38 |          pass
  39 |  
  40 |  
  41 | -def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False):
  42 | +def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False, family=None):
  43 |      """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
  44 |      refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
  45 |      drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
  46 | +    family: the Heimdall family the call went to; a failure records it in failing_families (ruling 87 amended).
  47 |      An answer while all is well is written at most once per HEARTBEAT_S per process (a failure is always written)."""
  48 |      import time as _time
  49 |      now, mono = _now(now), _time.monotonic()
  50 | @@ -150,9 +157,12 @@ def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", d
  51 |              return s["mode"]
  52 |          s["notes"] = int(s.get("notes") or 0) + 1
  53 |          if answered:
  54 | -            s["last_answer_utc"], s["failing_since_utc"] = _iso(now), None
  55 | -        elif not s.get("failing_since_utc"):
  56 | -            s["failing_since_utc"] = _iso(now)
  57 | +            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
  58 | +        else:
  59 | +            if not s.get("failing_since_utc"):
  60 | +                s["failing_since_utc"], s["failing_families"] = _iso(now), []
  61 | +            if family:
  62 | +                s["failing_families"] = sorted(set(_families(s)) | {str(family)})
  63 |          _down_rule(s, now, evidence, state_md, who)
  64 |          _save(path, s)
  65 |          with _SEEN_LOCK:
  66 | @@ -166,14 +176,15 @@ def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", d
  67 |  def _down_rule(s, now, evidence, state_md, who):
  68 |      fs = _t(s.get("failing_since_utc"))
  69 |      if s["mode"] == "heimdall_first" and fs is not None and (now - fs).total_seconds() >= DOWN_AFTER_S:
  70 | -        _switch(s, "plan_b", f"no Heimdall family answered inside its deadline for "
  71 | +        _switch(s, "plan_b", f"no answer of any kind (no call and no probe answered) for "
  72 |                               f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
  73 |                  state_md, who)
  74 |          s["probe_streak"] = 0
  75 |  
  76 |  
  77 |  def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
  78 | -    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches). -> mode."""
  79 | +    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches: no call and no
  80 | +    probe answered for 15 minutes; the probe goes every 2 minutes while the clock runs). -> mode."""
  81 |      now = _now(now)
  82 |      with _Locked(path):
  83 |          s = _load(path)
  84 | @@ -184,19 +195,30 @@ def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
  85 |          return s["mode"]
  86 |  
  87 |  
  88 | -def probe_due(path=STATE, now=None, who=""):
  89 | +def _families(s):
  90 | +    """The failed families on the running clock (a malformed field reads as none: no prober is kept out by it)."""
  91 | +    f = s.get("failing_families")
  92 | +    return [x for x in f if isinstance(x, str)] if isinstance(f, list) else []
  93 | +
  94 | +
  95 | +def probe_due(path=STATE, now=None, who="", families=None):
  96 |      """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
  97 |      A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
  98 |      builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
  99 |      row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). The next probe is due PROBE_EVERY_S after the
 100 |      later stamp: probe_result re-stamps last_probe_utc when the probe reports (answer-anchored), and a claimer that
 101 |      never reports leaves the slot spent from its claim (claim-anchored) (audit 0230 C1, glm). who names the claimer
 102 | -    (pp-ingest's watcher passes it from its next restart; "" until then)."""
 103 | +    (pp-ingest's watcher passes it from its next restart; "" until then). RULING 87 AMENDED (10:06 Nov 14): a probe is a
 104 | +    real model call on the family that failed: while the clock runs in heimdall_first, a prober whose `families` include
 105 | +    none of failing_families does not claim (the prober that can ask them does); families=None claims as before."""
 106 |      now = _now(now)
 107 |      with _Locked(path):
 108 |          s = _load(path)
 109 |          if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
 110 |              return False
 111 | +        failed = set(_families(s))
 112 | +        if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families):
 113 | +            return False
 114 |          lp = _t(s.get("last_probe_utc"))
 115 |          if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
 116 |              return False
 117 | @@ -206,17 +228,23 @@ def probe_due(path=STATE, now=None, who=""):
 118 |  
 119 |  
 120 |  def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
 121 | -    """A probe's outcome (any Heimdall family answering it counts). BACK_AFTER answers in a row while in plan_b:
 122 | -    back to heimdall_first (the failure clock cleared). While not yet down, a probe answer is no verdict answer: the
 123 | -    15-minute clock runs on (the ruling counts verdict and writer calls). -> the mode after it."""
 124 | +    """A probe's outcome (any Heimdall family answering it counts). RULING 87 AMENDED (10:06 Nov 14): an answered probe
 125 | +    is an answer like an answered call, in both modes: it resets the clock (failing_since_utc, failing_families) and
 126 | +    stamps last_answer_utc (pp-ingest's ruling-98 route reads the clock as "no answer of any kind"). A probe answer
 127 | +    timed before the failure that started the clock (a report that arrives late) does not reset that clock. A failed
 128 | +    probe never starts the clock (note(False) does). plan_b closes on BACK_AFTER answers in a row, as before.
 129 | +    -> the mode after it."""
 130 |      now = _now(now)
 131 |      with _Locked(path):
 132 |          s = _load(path)
 133 |          s["last_probe_utc"] = _iso(now)
 134 |          s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
 135 | +        fs = _t(s.get("failing_since_utc"))
 136 | +        if answered and (fs is None or now >= fs):     # not a late report from before the clock started
 137 | +            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
 138 |          if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
 139 |              _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
 140 |                      state_md, who)
 141 | -            s["failing_since_utc"], s["probe_streak"] = None, 0
 142 | +            s["failing_since_utc"], s["failing_families"], s["probe_streak"] = None, [], 0
 143 |          _save(path, s)
 144 |          return s["mode"]
 145 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 146 | index 1161323..6dc0aee 100644
 147 | --- a/pipeline/providers.py
 148 | +++ b/pipeline/providers.py
 149 | @@ -1015,7 +1015,8 @@ class Router:
 150 |              return
 151 |          import heimdall_health as HH
 152 |          try:
 153 | -            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
 154 | +            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid",
 155 | +                    family=b.family)              # ruling 87 amended: the family a probe must ask
 156 |          except (HH.HealthUnreadable, OSError) as e:
 157 |              n = f"RULING 87: the Heimdall health state cannot be read or written: {e}"
 158 |              if n not in self.notices:
 159 | @@ -1036,7 +1037,8 @@ class Router:
 160 |          def loop():
 161 |              while True:
 162 |                  try:
 163 | -                    if HH.probe_due(self.health, who="pp-selectid probe"):     # claims the slot (one prober each)
 164 | +                    if HH.probe_due(self.health, who="pp-selectid probe",      # claims the slot (one prober each),
 165 | +                                    families=sorted({self.backends[n].family for n in fams})):   # 87 amended
 166 |                          HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
 167 |                                          state_md=self.state_md, who="pp-selectid probe")
 168 |                  except Exception:                      # noqa: BLE001 (the probe never stops a build)
 169 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
 170 | index de1ce34..0a52b50 100644
 171 | --- a/tests/providers/test_heimdall_health.py
 172 | +++ b/tests/providers/test_heimdall_health.py
 173 | @@ -45,7 +45,8 @@ class TestHealth(unittest.TestCase):
 174 |              self.assertEqual([json.loads(x)["kind"] for x in f], ["switch"])
 175 |          first = open(self.md).read().split("\n")[0]
 176 |          self.assertTrue(first.endswith("| 21:00 ET: line one as it was."), first)     # one physical line, prepended
 177 | -        self.assertIn("ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED", first)
 178 | +        self.assertIn("ET: SWITCHED TO PLAN B (NO ANSWER OF ANY KIND (NO CALL AND NO PROBE ANSWERED) FOR 15 MINUTES",
 179 | +                      first)
 180 |  
 181 |      def test_one_answer_stops_the_clock(self):
 182 |          HH.note(False, **self.kw(T0))
 183 | @@ -54,6 +55,91 @@ class TestHealth(unittest.TestCase):
 184 |          self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=34))), "heimdall_first")
 185 |          self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=35))), "plan_b")   # idle: the clock still runs
 186 |  
 187 | +    def test_ruling_87_amended_an_answered_probe_resets_the_clock(self):
 188 | +        """RULING 87 AMENDED (10:06 Nov 14), the false outage of 09:16-09:22 replayed: one 502 at 14:01:08Z, then probes
 189 | +        answering every 2 minutes and no real call. 'Down' is no answer of ANY kind for 15 minutes."""
 190 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
 191 | +        HH.note(False, **k(0))                                           # one failed call starts the clock
 192 | +        for m in range(2, 22, 2):
 193 | +            self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=m)) or m > 2)
 194 | +            self.assertEqual(HH.probe_result(True, **k(m)), "heimdall_first")
 195 | +            self.assertEqual(HH.mode(**k(m + 1)), "heimdall_first")
 196 | +        st = json.load(open(self.state))
 197 | +        self.assertIsNone(st["failing_since_utc"])                       # reset by the first good probe
 198 | +        self.assertEqual(st["last_answer_utc"], "2026-11-14T02:20:00Z")   # an answer of any kind
 199 | +        self.assertEqual(st["switches"], [])
 200 | +        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=30)))     # no clock: no probe
 201 | +        self.assertEqual(open(self.md).read().split("\n")[0], "21:00 ET: line one as it was.")   # no switch line
 202 | +
 203 | +    def test_one_failed_call_then_one_good_probe_then_silence_is_never_down(self):
 204 | +        HH.note(False, **self.kw(T0))
 205 | +        self.assertEqual(HH.probe_result(True, **self.kw(T0 + timedelta(minutes=2))), "heimdall_first")
 206 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(hours=3))), "heimdall_first")
 207 | +
 208 | +    def test_failing_probes_leave_the_clock_running_and_a_failed_probe_never_starts_it(self):
 209 | +        self.assertEqual(HH.probe_result(False, **self.kw(T0)), "heimdall_first")
 210 | +        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # only note(False) starts the clock
 211 | +        HH.note(False, **self.kw(T0))
 212 | +        for m in range(2, 16, 2):
 213 | +            self.assertEqual(HH.probe_result(False, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
 214 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=15))), "plan_b")   # zero answers for 15 minutes
 215 | +        self.assertIn("NO ANSWER OF ANY KIND", open(self.md).read().split("\n")[0])
 216 | +
 217 | +    def test_a_late_probe_report_does_not_reset_a_newer_clock(self):
 218 | +        """pp-ingest reports a probe at its next tick with the probe's own time (up to PROBE_EVERY_S late): an answer
 219 | +        timed before the failure that started the clock proves nothing about after it."""
 220 | +        HH.note(False, **self.kw(T0 + timedelta(minutes=10)))
 221 | +        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=9)))       # answered at 9, reported after the 10 failure
 222 | +        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:10:00Z")
 223 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=25))), "plan_b")
 224 | +        HH.note(False, **self.kw(T0 + timedelta(minutes=40)))
 225 | +        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=41)))      # in plan_b: one answer is a streak of 1,
 226 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=42))), "plan_b")   # back only after 3 (as before)
 227 | +
 228 | +    def test_in_plan_b_an_answered_probe_resets_the_clock_and_plan_b_still_needs_3_in_a_row(self):
 229 | +        """pp-ingest's ruling-98 route opens on plan_b AND failing_since_utc 20 minutes old (read as 'no answer of any
 230 | +        kind'): a probe answer at minute 17 of plan_b restarts that clock; closing plan_b stays at 3 answers in a row."""
 231 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
 232 | +        HH.note(False, **k(0))
 233 | +        self.assertEqual(HH.mode(**k(15)), "plan_b")
 234 | +        HH.note(False, **k(16))                                          # still failing inside plan_b
 235 | +        self.assertEqual(HH.probe_result(True, **k(17)), "plan_b")
 236 | +        st = json.load(open(self.state))
 237 | +        self.assertEqual((st["failing_since_utc"], st["last_answer_utc"], st["probe_streak"]),
 238 | +                         (None, "2026-11-14T02:17:00Z", 1))
 239 | +        self.assertEqual(HH.probe_result(False, **k(19)), "plan_b")      # a miss: the streak is 0, the clock stays off
 240 | +        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # (a failed probe never starts it)
 241 | +        HH.note(False, **k(20))                                           # a failed call starts it again
 242 | +        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:20:00Z")
 243 | +        self.assertEqual([HH.probe_result(True, **k(m)) for m in (21, 23, 25)], ["plan_b", "plan_b", "heimdall_first"])
 244 | +
 245 | +    def test_the_probe_asks_the_family_that_failed(self):
 246 | +        """RULING 87 AMENDED: a probe is a real model call on the family that failed. The builder's probe asks deepseek,
 247 | +        glm and qwen; pp-ingest's asks qwen, glm and muse. While the clock runs, a prober that can ask none of the
 248 | +        failed families leaves the slot to the one that can; in plan_b any prober claims (plan_b can always close)."""
 249 | +        at = lambda m: T0 + timedelta(minutes=m)
 250 | +        mine, theirs = ["deepseek", "glm", "qwen"], ["glm", "muse", "qwen"]
 251 | +        HH.note(False, family="muse", **self.kw(at(0)))                  # pp-ingest's muse 502
 252 | +        self.assertEqual(json.load(open(self.state))["failing_families"], ["muse"])
 253 | +        self.assertFalse(HH.probe_due(self.state, at(2), who="pp-selectid", families=mine))   # cannot ask muse
 254 | +        self.assertTrue(HH.probe_due(self.state, at(2), who="pp-ingest", families=theirs))
 255 | +        HH.note(False, family="deepseek", **self.kw(at(3)))              # then the builder's deepseek fails too
 256 | +        self.assertEqual(json.load(open(self.state))["failing_families"], ["deepseek", "muse"])
 257 | +        self.assertTrue(HH.probe_due(self.state, at(4), who="pp-selectid", families=mine))    # it can ask one
 258 | +        HH.probe_result(True, **self.kw(at(4)))                          # any answer: the clock and the families reset
 259 | +        st = json.load(open(self.state))
 260 | +        self.assertEqual((st["failing_since_utc"], st["failing_families"]), (None, []))
 261 | +        self.assertFalse(HH.probe_due(self.state, at(8), families=mine))  # no clock: no probe
 262 | +        HH.note(False, family="muse", **self.kw(at(10)))
 263 | +        self.assertTrue(HH.probe_due(self.state, at(12)))                # families not named: claims as before
 264 | +        HH.note(False, family="muse", **self.kw(at(25)))                 # nobody answered for 15 minutes: plan_b
 265 | +        self.assertEqual(HH.mode(**self.kw(at(25))), "plan_b")
 266 | +        self.assertTrue(HH.probe_due(self.state, at(26), who="pp-selectid", families=mine))   # plan_b: any prober
 267 | +        st = json.load(open(self.state))
 268 | +        st["mode"], st["failing_families"], st["failing_since_utc"] = "heimdall_first", "muse", "2026-11-14T02:30:00Z"
 269 | +        json.dump(st, open(self.state, "w"))                             # a malformed field keeps no prober out
 270 | +        self.assertTrue(HH.probe_due(self.state, at(31), families=mine))
 271 | +
 272 |      def test_the_probe_every_2_minutes_and_back_after_3_answers_in_a_row(self):
 273 |          k = lambda m: self.kw(T0 + timedelta(minutes=m))
 274 |          self.assertFalse(HH.probe_due(self.state, T0))                  # healthy: no probe
 275 | @@ -181,6 +267,23 @@ class TestRouterPlanB(unittest.TestCase):
 276 |          self.assertIn("heimdall:deepseek", r.down)                       # still down: marked as before
 277 |          self.assertFalse(os.path.exists(os.path.join(self.d.name, "rec")))   # a probe is never recorded
 278 |  
 279 | +    def test_the_probe_thread_names_its_families_to_the_slot_claim(self):
 280 | +        """RULING 87 AMENDED: the builder's probe asks its own Heimdall families, and says which to probe_due."""
 281 | +        import time as _t
 282 | +        from unittest import mock
 283 | +        r, seen = self.router(), []
 284 | +
 285 | +        def due(path, now=None, who="", families=None):
 286 | +            seen.append((who, families))
 287 | +            return False
 288 | +        with mock.patch.object(HH, "probe_due", due):
 289 | +            P.Router.start_probe(r, every_s=3600.0)       # one look, then an hour asleep (a daemon thread)
 290 | +            for _ in range(200):
 291 | +                if seen:
 292 | +                    break
 293 | +                _t.sleep(0.01)
 294 | +        self.assertEqual(seen, [("pp-selectid probe", ["deepseek"])])
 295 | +
 296 |      def test_a_failing_heimdall_call_is_noted_as_not_answered(self):
 297 |          r = self.router()
 298 |  
 299 | @@ -191,6 +294,7 @@ class TestRouterPlanB(unittest.TestCase):
 300 |          st = json.load(open(self.state))
 301 |          self.assertIsNotNone(st["failing_since_utc"])
 302 |          self.assertIsNone(st["last_answer_utc"])
 303 | +        self.assertEqual(st["failing_families"], ["deepseek"])          # ruling 87 amended: the family to probe
 304 |  
 305 |  
 306 |  
 307 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence of calls that breaks it.

BACKGROUND (static):
- pipeline/heimdall_health.py keeps ONE shared "Heimdall down" signal in a JSON state file under an flock, for two
  processes: this builder's model router (providers.Router) and another team's miner (pp-ingest's watcher, which loads
  this module BY PATH from this worktree and calls only note, mode, probe_due, probe_result). Heimdall is a model gateway
  with several model families (deepseek, glm, qwen, ...). "plan_b" sends the builder's verdict calls to outside vendors
  (Grok first); "heimdall_first" uses Heimdall's families first.
- The clock: note(False) (a call that failed) starts it (failing_since_utc); note(True) (an answered call) clears it.
  mode() and note() apply _down_rule: when the clock has run DOWN_AFTER_S (15 min), the mode switches to plan_b and the
  switch is written to the state, an evidence file, and STATE line 1. In plan_b, probe_result counts answers in a row;
  BACK_AFTER (3) in a row switches back to heimdall_first. probe_due() returns True (and claims the 2-minute slot) only
  while the clock runs or the mode is plan_b.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- heimdall_health._Locked (class at :82) serialises every read-modify-write of the state with fcntl.flock; _load (:61)
  raises HealthUnreadable on an unreadable state (:72), never a guess.
- heimdall_health._t parses an ISO time and returns None for a time without a zone; _iso writes "%Y-%m-%dT%H:%M:%SZ".
- providers.Router._note (providers.py:1009) notes ONLY HeimdallBackend calls of the verdict roles and "angle_write";
  their chains use only the families deepseek, glm and qwen (nemotron appears only in visual_check, not a noted role).
  On a failure it starts the probe thread (start_probe, :1026).
- providers.Router.start_probe / probe_once (:1026-:1066): while HH.probe_due(...) (:1039) claims a slot, it asks EACH
  of its Heimdall families deepseek, glm and qwen (:1033) a real one-word model call ("Reply with the single word OK.",
  60 s each, never served from a recording) and reports HH.probe_result(any answered) (:1040) at the current time.
- pp-ingest's watcher (pipeline/ingest/downsignal.py in its own worktree) reports a finished probe at its next tick
  with the probe's OWN time: probe_result(answered, now=<probe finish time>, ...) (downsignal.py:338), up to
  PROBE_EVERY_S late; its notes too carry their own times (:297).

THE ORCHESTRATOR'S RULING (10:06 ET Nov 14), verbatim:
"RULING 87 AMENDED (the false outage of 09:16-09:22: one 502 on a calibration call, then silence, and the clock ran while
every probe was answering). 'Down' means NO SUCCESSFUL ANSWER of any kind for 15 minutes: any answered call OR answered
probe resets the clock to zero. While the clock is running the probe goes every 2 minutes, so a single failed call
followed by one good probe is never 'down'. A probe must be a real model call on the family that failed (and one
other), not a ping. Plan B opens only when the clock reaches 15 minutes with zero answers; it closes on 3 good probes as
now. Every switch still goes on line 1 in capitals; a switch later found false is marked so, as pp-ingest did (well
reported). The clock lives in your module: fix it there (audited, small), tell pp-ingest when it is live."

THE CHANGE (the diff follows):
1. probe_result: an ANSWERED probe is an answer like an answered call, IN BOTH MODES: it resets the clock
   (failing_since_utc None, failing_families []) and stamps last_answer_utc. pp-ingest's watcher opens its paid route
   (its ruling 98) on mode == plan_b AND failing_since_utc 20 minutes old, reading that field as "no answer of any kind",
   so a probe answer inside plan_b must restart it. A probe answer timed BEFORE the failure that started the clock (a
   late report) does not reset that clock. A failed probe never starts the clock (only note(False) does), as before.
   plan_b still closes only on 3 answers in a row. Before this change, a probe answer did not count while heimdall_first
   (the clock ran on: the false outages of 09:16 and 10:12 ET).
2. "A probe must be a real model call on the family that failed (and one other)": note(False, family=...) records the
   failed family in the state (failing_families: the families whose failures are on the running clock; a new clock
   starts the list afresh; any answer clears it). probe_due(families=[...]): while the clock runs in heimdall_first, a
   prober that can ask NONE of the failed families does not claim the slot, so the prober that can (the other process)
   does; families=None claims as before; in plan_b any prober claims (plan_b can always close). A malformed
   failing_families field reads as none (no prober is kept out by it). The builder calls deepseek, glm and qwen; pp-ingest
   calls qwen, glm and muse: each side's probe asks every family it calls.
3. providers.Router passes family=b.family to note() and families=<its probe's families> to probe_due().
4. The switch reason now reads "no answer of any kind (no call and no probe answered) for N minutes (since T)".
5. Tests: the 09:16 outage replayed (probes answering every 2 minutes); one failed call then one good probe then 3 hours
   of silence; failing probes leave the clock running; a late report does not reset a newer clock; inside plan_b an
   answered probe resets the clock and plan_b still needs 3 in a row; the failed family steers the slot claim (and plan_b
   lets any prober claim; a malformed field keeps no prober out); the Router passes its family and its probe's families.
   20 tests pass; 14 mutations, each killed.

ATTACK:
(a) Can a single failed call followed by one good probe still end in plan_b? Can 15 minutes of failed calls AND failed
    probes fail to open plan_b?
(b) The late-report guard (now >= failing_since): can it drop a genuine answer, or let a stale one reset a newer clock?
    Equal times? A state whose failing_since_utc cannot be parsed?
(c) Any interaction with plan_b's 3-in-a-row rule, the probe slot claim (probe_due), the heartbeat cache in note()
    (_SEEN), or the two processes writing the same file?
(d) Does anything here let the builder or pp-ingest read 'up' or 'down' by guess, or change what pp-ingest's calls do?
(e) "A probe must be a real model call on the family that failed (and one other)": can a slot be spent on a probe that
    asks none of the failed families while a prober that can ask them is alive? Can the families rule leave plan_b, or
    a running clock, with no prober at all? What must pp-ingest's side do?
(f) An older state file (no failing_families key) or pp-ingest's current calls (no family, no families): unchanged?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

