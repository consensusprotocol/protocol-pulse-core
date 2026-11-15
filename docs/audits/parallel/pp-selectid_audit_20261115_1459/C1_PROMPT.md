# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1459
# Branch: pp-selectid
# Generated: 2026-11-15 14:59 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1459/C1_STEP.diff (176 lines)
```
   1 | diff --git a/pipeline/hook_bar.py b/pipeline/hook_bar.py
   2 | index d29c497..e798a72 100644
   3 | --- a/pipeline/hook_bar.py
   4 | +++ b/pipeline/hook_bar.py
   5 | @@ -6,9 +6,11 @@ value the part took across PBX's approved hooks, under that same asking (the sou
   6 |  ALONE_TEST.json). No floor is set below 3: the order stops a lower one at 3, and the builder reports it.
   7 |  
   8 |  The floors live in ONE calibration file, pipeline/hook_calibration.json, with its sha256. It is valid only for its
   9 | -rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for 24 h after it was
  10 | -measured (ruling 113 (2): again on any change, and once a day). An invalid or stale file passes NO hook, and the
  11 | -build says why in one line (fail closed, law L-m).
  12 | +rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for as long as the FILE
  13 | +says: "valid_h" hours after it was measured, or null for no expiry. Ruling 115's interim bar is null: its floors come
  14 | +from ONE fixed source (ALONE_TEST.json), and ruling 113 (2)'s once-a-day law is measured against ruling 115 (3)'s
  15 | +question version, not this one; a calibration under that law will carry its 24. A file that names no "valid_h" is
  16 | +refused. An invalid or stale file passes NO hook, and the build says why in one line (fail closed, law L-m).
  17 |  A package sealed on this bar says so in its record (NOTE). PBX's approve or reject of it is appended to the file
  18 |  (add_example), so the approved set grows.
  19 |  """
  20 | @@ -21,7 +23,6 @@ from datetime import datetime, timedelta, timezone
  21 |  PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_calibration.json")
  22 |  PARTS = ("scroll", "alone", "setup")
  23 |  FLOOR_MIN = 3                       # the order: "If any floor comes out below 3, stop at 3 for that part and tell me."
  24 | -VALID_H = 24.0                      # ruling 113 (2): "once a day"
  25 |  SKEW_MIN = 5.0                      # a measured_at at most this many minutes ahead of now (clock skew) is accepted
  26 |  NOTE = "hook passed on the calibrated bar"
  27 |  
  28 | @@ -61,8 +62,8 @@ def load(path=PATH):
  29 |  
  30 |  def bar(rater, question_version, seed, now=None, path=PATH):
  31 |      """The live bar: {"floors", "sha256", "rater", ...} when the calibration is valid for exactly this question
  32 | -    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is under
  33 | -    VALID_H old; else (None, why), and no hook passes."""
  34 | +    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is within
  35 | +    its own "valid_h" (null: no expiry); else (None, why), and no hook passes."""
  36 |      cal, why = load(path)
  37 |      if cal is None:
  38 |          return None, why
  39 | @@ -79,14 +80,20 @@ def bar(rater, question_version, seed, now=None, path=PATH):
  40 |      if at.tzinfo is None:                # a naive time cannot be compared with now (audit 20261115_1410)
  41 |          return None, "the hook calibration's measured_at has no timezone: refused"
  42 |      age = (now or datetime.now(timezone.utc)) - at
  43 | -    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch the 24 h (audit 1410 C1, qwen)
  44 | +    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch its validity (audit 1410 C1, qwen)
  45 |          return None, f"the hook calibration's measured_at ({cal['measured_at']}) is in the future: refused"
  46 | -    if age > timedelta(hours=VALID_H):
  47 | -        return None, f"the hook calibration is over {VALID_H:g} h old (measured {cal['measured_at']}): re-run it"
  48 | +    if "valid_h" not in cal:                 # explicit: never a calibration valid forever by an omission
  49 | +        return None, "the hook calibration names no valid_h (hours, or null for none): refused"
  50 | +    vh = cal["valid_h"]
  51 | +    if vh is not None:
  52 | +        if type(vh) not in (int, float) or vh <= 0:
  53 | +            return None, f"the hook calibration's valid_h {vh!r} is not a positive number of hours: refused"
  54 | +        if age > timedelta(hours=vh):
  55 | +            return None, f"the hook calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
  56 |      if any(v < FLOOR_MIN for v in fl.values()):
  57 |          return None, f"a floor under {FLOOR_MIN} in the hook calibration: refused"
  58 |      return {"floors": fl, "sha256": cal["sha256"], "rater": cal["rater"], "question_version": cal["question_version"],
  59 | -            "seed": cal["seed"], "measured_at": cal["measured_at"]}, None
  60 | +            "seed": cal["seed"], "measured_at": cal["measured_at"], "valid_h": vh}, None
  61 |  
  62 |  
  63 |  def passes(rec, live):
  64 | diff --git a/pipeline/hook_calibration.json b/pipeline/hook_calibration.json
  65 | index 4c606ad..5668fb3 100644
  66 | --- a/pipeline/hook_calibration.json
  67 | +++ b/pipeline/hook_calibration.json
  68 | @@ -81,6 +81,8 @@
  69 |   "rule": "a hook passes when EACH of scroll / alone / setup is at least its floor; a floor is the lowest value the part takes across the approved hooks under this asking, never below 3",
  70 |   "ruling": "115 (orchestrator 13:24 ET Nov 15): the hook bar is defined by PBX's approvals",
  71 |   "seed": 7,
  72 | - "sha256": "fb964eb15a242b3ee7e385ce383546baa74e303d5009529eeab3cc18f313320b",
  73 | - "source": "tests/package/proof/hook113/ALONE_TEST.json"
  74 | + "sha256": "6978392df37e5abff8594c6fc293e29cf761718fc0530cd87ed6b3892c3fafd6",
  75 | + "source": "tests/package/proof/hook113/ALONE_TEST.json",
  76 | + "valid_h": null,
  77 | + "valid_h_note": "ruling 115 (1): the interim bar's floors come from ONE fixed source (tests/package/proof/hook113/ALONE_TEST.json), so it does not expire; ruling 113 (2)'s once-a-day law is measured against ruling 115 (3)'s question version (ruling 115 (3)), whose calibration will carry its 24."
  78 |  }
  79 | diff --git a/pipeline/package.py b/pipeline/package.py
  80 | index d96a7cd..5bbda7a 100644
  81 | --- a/pipeline/package.py
  82 | +++ b/pipeline/package.py
  83 | @@ -1407,7 +1407,7 @@ _LIVE = {}
  84 |  
  85 |  def _live_bar():
  86 |      """The calibrated bar, read once per state of the calibration file (its mtime) and per minute: a build reads it a
  87 | -    few times, and a calibration that ages past its 24 h mid-build stops passing hooks within the minute."""
  88 | +    few times, and a calibration that ages past its own valid_h mid-build stops passing hooks within the minute."""
  89 |      import hook_bar as HB
  90 |      try:
  91 |          k = (os.stat(HB.PATH).st_mtime_ns, int(time.time() // 60))
  92 | diff --git a/tests/package/test_hook_bar.py b/tests/package/test_hook_bar.py
  93 | index 793a5f9..3b2404b 100644
  94 | --- a/tests/package/test_hook_bar.py
  95 | +++ b/tests/package/test_hook_bar.py
  96 | @@ -2,7 +2,8 @@
  97 |  """RULING 115 (orchestrator 13:24 ET Nov 15): THE CALIBRATED HOOK BAR (pipeline/hook_bar.py). A hook passes when each of
  98 |  scroll / alone / setup is at least the LOWEST value that part takes across PBX's approved hooks under the same asking
  99 |  (ALONE, production's seed, Grok); no floor under 3; one sealed calibration file, valid for its rater, question version,
 100 | -seed and asking, for 24 h; a package sealed on it says so; PBX's verdicts on such packages are appended as examples.
 101 | +seed and asking, for as long as the file says (valid_h hours, or null: ruling 115's interim bar); a package sealed on it
 102 | +says so; PBX's verdicts on such packages are appended as examples.
 103 |  The live file is checked against its source and against production's hook job."""
 104 |  import copy
 105 |  import json
 106 | @@ -33,7 +34,7 @@ def cal(parts=((3, 4, 3), (3, 5, 4), (4, 5, 4)), **kw):
 107 |      ap = approved(*parts)
 108 |      fl, low = HB.floors_from(ap)
 109 |      return dict({"rater": G, "asking": "alone", "seed": 7, "question_version": "qv", "measured_at": AT.isoformat(),
 110 | -                 "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 111 | +                 "valid_h": 24, "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 112 |  
 113 |  
 114 |  class TestFloors(unittest.TestCase):
 115 | @@ -108,15 +109,29 @@ class TestTheFile(unittest.TestCase):
 116 |          HB.write(cal(asking="batched"), self.path)                         # the batch moved single ratings
 117 |          self.assertIsNone(self.bar()[0])
 118 |  
 119 | -    def test_once_a_day_a_stale_calibration_passes_nothing(self):
 120 | -        HB.write(cal(), self.path)
 121 | +    def test_a_calibration_lasts_as_long_as_its_own_valid_h_says(self):
 122 | +        """valid_h hours (a standing-law calibration: ruling 113 (2)'s once a day), or null for none (ruling 115's
 123 | +        interim bar: one fixed source); a file that names no valid_h, or a bad one, passes nothing."""
 124 | +        HB.write(cal(), self.path)                                          # valid_h 24
 125 |          self.assertIsNotNone(self.bar(now=AT + timedelta(hours=23, minutes=59))[0])
 126 |          live, why = self.bar(now=AT + timedelta(hours=24, minutes=1))
 127 |          self.assertIsNone(live)
 128 |          self.assertIn("over 24 h old", why)
 129 | +        HB.write(cal(valid_h=None), self.path)                              # the interim bar: no expiry
 130 | +        live, why = self.bar(now=AT + timedelta(days=30))
 131 | +        self.assertEqual((live["floors"], live["valid_h"], why), ({"scroll": 3, "alone": 4, "setup": 3}, None, None))
 132 | +        c = cal()
 133 | +        del c["valid_h"]
 134 | +        HB.write(c, self.path)                                              # never valid forever by an omission
 135 | +        live, why = self.bar()
 136 | +        self.assertIsNone(live)
 137 | +        self.assertIn("names no valid_h", why)
 138 | +        for bad in (0, -1, "24", True):
 139 | +            HB.write(cal(valid_h=bad), self.path)
 140 | +            self.assertIsNone(self.bar()[0], bad)
 141 |  
 142 |      def test_a_future_or_naive_measured_at_passes_nothing(self):
 143 | -        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its 24 h; a time with no
 144 | +        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its validity; a time with no
 145 |          timezone cannot be compared with now (it must never raise into a build)."""
 146 |          HB.write(cal(), self.path)
 147 |          self.assertIsNotNone(self.bar(now=AT - timedelta(minutes=4))[0])  # clock skew inside 5 min
 148 | @@ -204,7 +219,7 @@ class TestTheMark(unittest.TestCase):
 149 |  
 150 |  class TestTheLiveCache(unittest.TestCase):
 151 |      """package._live_bar: the bar is read once per state of the file and per minute (so a calibration that ages past
 152 | -    its 24 h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
 153 | +    its valid_h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
 154 |      real_hook_bar = True
 155 |  
 156 |      def test_read_once_a_minute_and_again_when_the_file_changes(self):
 157 | @@ -236,9 +251,17 @@ class TestTheLiveCache(unittest.TestCase):
 158 |  class TestTheLiveCalibration(unittest.TestCase):
 159 |      """The calibration production reads (pipeline/hook_calibration.json): its floors are derived from their source
 160 |      (tests/package/proof/hook113/ALONE_TEST.json: Grok asked alone at seed 7; the two out-of-contract first answers
 161 | -    asked once more), and it is for production's question version, seed and hook list."""
 162 | +    asked once more), and it is for production's question version, seed and hook list. Ruling 115's interim bar does
 163 | +    not expire: its floors come from that one fixed source."""
 164 |      real_hook_bar = True
 165 |  
 166 | +    def test_the_interim_bar_does_not_expire(self):
 167 | +        c, why = HB.load()
 168 | +        self.assertIsNone(why)
 169 | +        at = datetime.fromisoformat(c["measured_at"])
 170 | +        live, why = HB.bar(None, c["question_version"], c["seed"], now=at + timedelta(days=30))
 171 | +        self.assertEqual((live is not None, why), (True, None))
 172 | +
 173 |      def test_its_floors_are_its_sources_lowest_parts(self):
 174 |          c, why = HB.load()
 175 |          self.assertIsNone(why)
 176 | 
```

---

pp-selectid: RULING 115 (1), a follow-up to the landed calibrated hook bar (da7b1160, audit 20261115_1410): THE
CALIBRATION'S EXPIRY IS THE FILE'S OWN, and ruling 115's interim bar does not expire. Files: pipeline/hook_bar.py,
pipeline/hook_calibration.json, pipeline/package.py (one docstring), tests/package/test_hook_bar.py.

WHY: the landed code expired every calibration 24 h after it was measured (VALID_H, "ruling 113 (2): once a day").
Read again, the orders do not ask that of the interim bar. Ruling 115 (1): "A hook passes when EACH of its three parts
(scroll, alone, setup) is at least the LOWEST value that part takes across the five approved hooks under that same
asking (ALONE_TEST.json is the source; write the three floors into one calibration file with its sha ...)": ONE fixed
source. Ruling 115 (3): "The standing law of ruling 113 (2) is then measured against that version" (the new question
version with examples), so the once-a-day law belongs to THAT version's calibration. With the 24 h, every build from
13:07 ET Nov 16 would have stopped at "no hook in the pool" (the bar invalid), with no committed tool to re-measure.

THE CHANGE:
- hook_bar.bar(): the expiry is the calibration file's own "valid_h": a positive number of hours after measured_at,
  or null for no expiry. A file with NO "valid_h" key is refused (never valid forever by an omission); a valid_h that
  is not a positive int/float (0, -1, "24", true) is refused. Every other check is unchanged: the sha seal, the rater
  / question version / seed / asking, a timezone on measured_at, not in the future beyond SKEW_MIN, no floor under 3.
  The live bar carries "valid_h". VALID_H (the module constant) is gone.
- hook_calibration.json: "valid_h": null and a "valid_h_note" citing ruling 115 (1) and (3); re-sealed (sha
  6978392df37e...). The floors, rater, question version (e3cba8d92551), seed and measured_at are unchanged.
- package._live_bar's docstring: "its own valid_h" for "its 24 h".

UNCHANGED GUARDS: load() refuses a body whose sha256 does not match (pipeline/hook_bar.py:51-58); passes() requires the
rating's back-end to be the calibration's rater (:96-104); package._live_bar re-reads the file on any mtime change and
once a minute (pipeline/package.py:1406-1418).

TESTS: test_hook_bar.py: a calibration lasts as long as its own valid_h says (24: valid at 23:59, refused at 24:01;
null: valid 30 days later; no key: refused; 0 / -1 / "24" / true: refused); the live file's interim bar does not
expire (valid 30 days after measured_at). tests/package + the medley and spotlight suites pass (274). Mutations (after
a control run): a valid_h that never expires, an omitted valid_h accepted, a bad valid_h accepted, null treated as a
number: 4 of 4 killed.

PLEASE CHECK: (1) that no calibration can be valid forever except by an explicit null; (2) that every other check of
bar() is unchanged; (3) the reading of rulings 115 (1) and (3) above; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
