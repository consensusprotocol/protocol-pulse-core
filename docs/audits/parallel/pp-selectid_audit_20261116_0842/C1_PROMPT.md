# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_0842
# Branch: pp-selectid
# Generated: 2026-11-16 08:42 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_0842/C1_STEP.diff (170 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index fc9cd76..c377dff 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1300,6 +1300,7 @@ def scorer_verdicts(path, code_sha):
   6 |      without a numeric score, with an error, or whose "affirmed" disagrees with the render's own moments rule
   7 |      (stand_alone.affirmed(score, fault, moments=True): the score alone) is no verdict."""
   8 |      import stand_alone as SA
   9 | +    import package_pin as PPN
  10 |      num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
  11 |      stage, sc = "open", None
  12 |      try:
  13 | @@ -1332,7 +1333,11 @@ def scorer_verdicts(path, code_sha):
  14 |          if (v.get("affirmed") is True) != rule:
  15 |              disagree.append(pid)
  16 |              continue
  17 | -        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"), "affirmed": rule,
  18 | +        floor = not rule and str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER) and \
  19 | +            v["score"] >= PPN.STAND_ALONE_FLOOR          # RULING 119 (1): the candidates path's calibrated floor
  20 | +        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"),
  21 | +                         "affirmed": rule or floor, "affirmed_render": rule,
  22 | +                         **({"bar": "calibrated", "floor": PPN.STAND_ALONE_FLOOR} if floor else {}),
  23 |                           "text_sha256": v["text_sha256"], "prompt_sha256": v.get("prompt_sha256"),
  24 |                           "model": sc.get("model"), "kind": sc["kind"], "event": None, "rubric": sc.get("rubric"),
  25 |                           "rule": sc.get("rule"), "scorer_sha": sc["scorer_sha"], "threshold": sc["threshold"],
  26 | @@ -1341,6 +1346,7 @@ def scorer_verdicts(path, code_sha):
  27 |                   "candidates_generated_at": d.get("candidates_generated_at"), "model": sc.get("model"),
  28 |                   "kind": sc["kind"], "rubric": sc.get("rubric"), "scorer_sha": sc["scorer_sha"],
  29 |                   "threshold": sc["threshold"], "verdicts": len(out), "affirmed": sum(v["affirmed"] for v in out.values()),
  30 | +                 "affirmed_on_the_floor": sum(v.get("bar") == "calibrated" for v in out.values()),
  31 |                   "disagree_with_the_rule": disagree}
  32 |  
  33 |  
  34 | @@ -1500,6 +1506,18 @@ def lineup_bar_mark(med, coh):
  35 |              "calibration_sha256": med.get("calibration_sha256"), "ruling": "116"}
  36 |  
  37 |  
  38 | +def stand_alone_mark(segments):
  39 | +    """RULING 119 (1): what a package carries in its record and pin (outside the seal) when the clip scorer affirmed one
  40 | +    of its segments ONLY on the candidates path's calibrated floor: the plain line for the Telegram note, the floor, the
  41 | +    scorer it was measured on and those segments' places. None when every affirmation met the render's own bar."""
  42 | +    import package_pin as PPN
  43 | +    on = [i for i, s in enumerate(segments) if (s.get("scorer_verdict") or {}).get("bar") == "calibrated"]
  44 | +    if not on:
  45 | +        return None
  46 | +    return {"note": PPN.STAND_ALONE_NOTE, "floor": PPN.STAND_ALONE_FLOOR, "scorer_sha": PPN.STAND_ALONE_FLOOR_SCORER,
  47 | +            "segments": on, "ruling": "119"}
  48 | +
  49 | +
  50 |  def hook_bar_mark(live=None):
  51 |      """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
  52 |      the plain line for the Telegram note, the floors and the calibration's sha. `live`: the bar the build judged its
  53 | @@ -3808,6 +3826,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  54 |          lm = lineup_bar_mark(*(lambda c: (c.get("medley"), c.get("coherence")))(out["package"].get("checks") or {}))
  55 |          if lm:                                           # RULING 116 (Q3): and its line-up, when both verdicts were
  56 |              out["package"]["lineup_bar"] = lm            # judged on the calibrated line-up bar
  57 | +        sm = stand_alone_mark(out["package"].get("segments") or [])
  58 | +        if sm:                                           # RULING 119 (1): a clip the scorer affirmed only on the
  59 | +            out["package"]["stand_alone_bar"] = sm       # calibrated floor
  60 |      if candidate is not None:                             # RULING 66: what became of the candidate
  61 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
  62 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
  63 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  64 | index 99f6cae..7ad6dd0 100644
  65 | --- a/pipeline/package_pin.py
  66 | +++ b/pipeline/package_pin.py
  67 | @@ -155,6 +155,12 @@ TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): pack
  68 |                                                             # must never pull package.py into that process
  69 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
  70 |  SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
  71 | +STAND_ALONE_FLOOR = 3.0                # RULING 119 (1) (orchestrator 08:25 ET Nov 16): the candidates path's calibrated
  72 | +STAND_ALONE_FLOOR_SCORER = "edd54964a5ab"   # floor, rulings 115/116's way: the lowest score an approved clip takes
  73 | +STAND_ALONE_NOTE = "stand-alone affirmed on the calibrated floor (3.0)"   # asked ALONE (2.0), never under 3. Measured
  74 | +#   (the integrator's run, docs/audits/ruling119/APPROVED_CLIPS_SCORER.json, 9216cdb9) on this scorer code only: under
  75 | +#   any other scorer_sha the floor is the render's own SCORER_MIN. The render's validate (all clips together, 3.5) is
  76 | +#   unchanged and still checks every pin.
  77 |  
  78 |  
  79 |  WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
  80 | @@ -250,10 +256,13 @@ def affirmed_verdict(s):
  81 |      v = s.get("scorer_verdict")
  82 |      num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
  83 |      text = s["approved_text"] if "approved_text" in s else s.get("text")
  84 | -    return isinstance(v, dict) and v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and \
  85 | -        v["event"] is None and num(v.get("score")) and v.get("threshold") == SCORER_MIN and v["score"] >= SCORER_MIN \
  86 | -        and bool(v.get("scorer_sha")) and isinstance(text, str) and \
  87 | -        v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
  88 | +    if not (isinstance(v, dict) and num(v.get("score"))):
  89 | +        return False
  90 | +    on_floor = v.get("bar") == "calibrated" and v.get("floor") == STAND_ALONE_FLOOR and \
  91 | +        v["score"] >= STAND_ALONE_FLOOR and str(v.get("scorer_sha") or "").startswith(STAND_ALONE_FLOOR_SCORER)
  92 | +    return v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and v["event"] is None and \
  93 | +        v.get("threshold") == SCORER_MIN and (v["score"] >= SCORER_MIN or on_floor) and bool(v.get("scorer_sha")) \
  94 | +        and isinstance(text, str) and v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
  95 |  
  96 |  
  97 |  def scorer_problems(segments):
  98 | @@ -499,6 +508,8 @@ def to_pin(pk, run_name):
  99 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 100 |                                  **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 101 |                                  #   the line-up's, when both its verdicts passed on the calibrated bar (outside the seal)
 102 | +                                **({"stand_alone_bar": pk["stand_alone_bar"]} if pk.get("stand_alone_bar") else {}),
 103 | +                                #   ruling 119 (1): a clip affirmed only on the calibrated floor (outside the seal)
 104 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 105 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 106 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 107 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 108 | index 1adf4a6..fe50d6a 100644
 109 | --- a/tests/package/test_medley.py
 110 | +++ b/tests/package/test_medley.py
 111 | @@ -1725,6 +1725,58 @@ class TestRuling116LineupBar(unittest.TestCase):
 112 |          self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 113 |  
 114 |  
 115 | +class TestRuling119StandAloneFloor(unittest.TestCase):
 116 | +    """RULING 119 (1) (orchestrator 08:25 ET Nov 16): the clip scorer asked ALONE (the candidates path) refused four of
 117 | +    PBX's approved clips (the integrator's run: 2.0 and 3.0); the candidates path's calibrated floor is the lowest an
 118 | +    approved clip takes, never under 3: 3.0, for the scorer code it was measured on only. A clip affirmed only on that
 119 | +    floor marks the package and its pin, outside the seal; the render's own validate (3.5) is unchanged."""
 120 | +
 121 | +    SHA = "edd54964a5ab" + "0" * 52
 122 | +    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."       # TestRuling56Scorer's opener
 123 | +
 124 | +    def file(self, verdicts, sha):
 125 | +        return TestRuling56Scorer.file(self, verdicts, scorer_sha=sha)
 126 | +
 127 | +    def test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on(self):
 128 | +        vs = {"a": fv(self.OPENER, 3.0), "b": fv("Bitcoin b.", 3.4), "c": fv("Bitcoin c.", 2.9), "d": fv("Bitcoin d.", 4.0)}
 129 | +        idx, rec = PK.scorer_verdicts(self.file(vs, self.SHA), self.SHA)
 130 | +        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": True, "b": True, "c": False, "d": True})
 131 | +        self.assertEqual({k: idx[k].get("bar") for k in "abcd"}, {"a": "calibrated", "b": "calibrated", "c": None,
 132 | +                                                                  "d": None})
 133 | +        self.assertEqual((idx["a"]["affirmed_render"], idx["a"]["floor"], idx["d"]["affirmed_render"]), (False, 3.0, True))
 134 | +        self.assertEqual((rec["affirmed"], rec["affirmed_on_the_floor"]), (3, 2))
 135 | +        other = "s" * 64                                                 # other scorer code: the render's own 3.5
 136 | +        idx, rec = PK.scorer_verdicts(self.file(vs, other), other)
 137 | +        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": False, "b": False, "c": False, "d": True})
 138 | +        self.assertEqual(rec["affirmed_on_the_floor"], 0)
 139 | +
 140 | +    def test_the_pin_check_accepts_a_floor_affirmation_only_whole(self):
 141 | +        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0)}, self.SHA), self.SHA)
 142 | +        seg = {"text": self.OPENER, "scorer_verdict": idx["a"]}
 143 | +        self.assertTrue(package_pin.affirmed_verdict(seg))
 144 | +        self.assertEqual(package_pin.scorer_problems([{"text": "Bitcoin."}, seg]), [])
 145 | +        for k, val in (("bar", None), ("floor", 2.5), ("score", 2.9), ("scorer_sha", "s" * 64), ("threshold", 3.0)):
 146 | +            v = dict(idx["a"], **{k: val}) if val is not None else {x: y for x, y in idx["a"].items() if x != k}
 147 | +            self.assertFalse(package_pin.affirmed_verdict(dict(seg, scorer_verdict=v)), k)
 148 | +
 149 | +    def test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal(self):
 150 | +        import copy
 151 | +        import test_angles as TA
 152 | +        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0), "d": fv("Bitcoin d.", 4.0)}, self.SHA),
 153 | +                                    self.SHA)
 154 | +        segs = [{"text": "Bitcoin d.", "scorer_verdict": idx["d"]}, {"text": self.OPENER, "scorer_verdict": idx["a"]}]
 155 | +        m = PK.stand_alone_mark(segs)
 156 | +        self.assertEqual((m["note"], m["floor"], m["segments"], m["ruling"]),
 157 | +                         ("stand-alone affirmed on the calibrated floor (3.0)", 3.0, [1], "119"))
 158 | +        self.assertIsNone(PK.stand_alone_mark(segs[:1]))                # every affirmation on the render's own bar
 159 | +        base = TA.TestPinAndTruth.pk(None)
 160 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")["moments_package"]
 161 | +        marked = package_pin.to_pin(dict(copy.deepcopy(base), stand_alone_bar=m), "r")["moments_package"]
 162 | +        self.assertNotIn("stand_alone_bar", plain)
 163 | +        self.assertEqual(marked["stand_alone_bar"]["note"], "stand-alone affirmed on the calibrated floor (3.0)")
 164 | +        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal
 165 | +
 166 | +
 167 |  class TestRuling117JoinSearch(unittest.TestCase):
 168 |      """RULING 117 (orchestrator 16:24 ET Nov 15), SEARCH, DO NOT LOOSEN: the join table (the clips-alone verdict's own
 169 |      join question once per ordered pair of an angle's moments, Grok, cached) and the line-ups chosen BY SEARCH over it
 170 | 
```

---

pp-selectid: RULING 119 (1) (orchestrator 08:25 ET Nov 16), the stand-alone scorer's calibrated floor on the CANDIDATES
path. Files: pipeline/package.py (scorer_verdicts, stand_alone_mark, the mark in build()), pipeline/package_pin.py
(affirmed_verdict; the floor's constants; the mark carried outside the seal), tests/package/test_medley.py.

THE ORDER, verbatim: "If any approved clip is refused, say so plainly and propose the calibrated floor the same way as
rulings 115/116 (the lowest score an approved clip takes under the same asking, never under 3), with DEFAULT IN 20 MIN:
APPLY, audit-first, marked on the pin and in the Telegram note in one plain line."
THE MEASURE (the integrator's run on GPU0, production's scorer code unchanged, scorer_sha edd54964a5ab, three askings per
clip, docs/audits/ruling119/APPROVED_CLIPS_SCORER.json in the main tree): asked ALONE (each clip in its own asking: the
candidates path the builds read), four approved clips are refused: the preview's clip_01 and clip_02 (2.0) and 41f29b1f's
clip_01 and clip_02 (3.0); all clips together (the render's validate) every approved clip is affirmed (lowest 4.0). The
lowest an approved clip takes alone is 2.0; never under 3: THE FLOOR IS 3.0 (from the render's 3.5).

THE CHANGE:
- package_pin: STAND_ALONE_FLOOR = 3.0, STAND_ALONE_FLOOR_SCORER = "edd54964a5ab" (the measured scorer code),
  STAND_ALONE_NOTE (the plain line). affirmed_verdict accepts a verdict at the render's own SCORER_MIN (3.5) as before, OR
  one marked bar "calibrated" with floor == 3.0, score >= 3.0 and a scorer_sha of the measured code; every other check
  (affirmed true, kind "moments", event null, threshold == SCORER_MIN, the text's sha) is unchanged.
- package.scorer_verdicts: the integrator's "affirmed" must still agree with the render's own rule (3.5) or the verdict is
  no verdict (unchanged); a verdict is affirmed on the floor when the render's rule refuses it, its scorer_sha is the
  measured code and its score >= 3.0: "affirmed" true, "affirmed_render" false, bar "calibrated", floor 3.0; the record
  counts affirmed_on_the_floor. Under any other scorer_sha the floor is never applied.
- package.stand_alone_mark(segments) and build(): a sealed package with a segment affirmed only on the floor carries
  moments_package.stand_alone_bar {note, floor, scorer_sha, segments, ruling}; package_pin.to_pin carries it OUTSIDE the
  seal (package_sha256 unchanged). The integrator's Telegram note prints its note (their side, told separately).

UNCHANGED GUARDS (not in the diff): the render's validate (stand_alone.check_edl, all clips together, 3.5) still checks
every pin at render; scorer_verdicts' file checks (kind moments, no event, scorer_sha == the render's code now, threshold ==
CLIP_MIN_SCORE); package_pin.scorer_problems (an opener needs an affirmation); trim_refused (a trimmed text needs one).

TESTS (test_medley TestRuling119StandAloneFloor, 3): the floor affirms 3.0-3.5 only on the measured scorer (2.9 refused;
another scorer_sha: 3.5 only); the pin check accepts a floor affirmation only whole (no bar, another floor, 2.9, another
sha, another threshold: refused); the mark on a package with a floor-affirmed segment, none without, and the pin carries it
outside the seal. Mutations F1-F6 after a control run: 6 of 6 killed. All suite files.

PLEASE CHECK: (1) that nothing under 3.0 and nothing from another scorer code is ever affirmed; (2) that the render's own
bar and checks are untouched; (3) that the mark is outside the seal; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
