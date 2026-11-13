# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0500
# Branch: pp-selectid
# Generated: 2026-11-13 04:57 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0500/C1_STEP.diff (122 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index f2e898ba..adb3d406 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -407,8 +407,8 @@ def _span(span, ctx, role):
   6 |      last = toks[w1].get("word")
   7 |      if not sentence_law.is_terminal(last):
   8 |          R("fragment", f"ends on {last!r}: no terminal punctuation")
   9 | -    elif not ends_statement(last):
  10 | -        R("not_statement", "ends on a question")
  11 | +    elif not ends_statement(last) and role != "hook":   # RULING 37 (03:12 ET Nov 13): a question may end the HOOK only;
  12 | +        R("not_statement", "ends on a question")         # the clips-alone verdict judges the join after it (package.py)
  13 |      # T5 lexical evidence at both boundaries (E-FAIL-013: an unpunctuated stretch has no boundary)
  14 |      for k in ([w0 - 1] if w0 > 0 else []) + [w1]:
  15 |          if not sentence_law.is_punctuated(toks, k):
  16 | diff --git a/pipeline/package.py b/pipeline/package.py
  17 | index 31ffb345..ac10906d 100644
  18 | --- a/pipeline/package.py
  19 | +++ b/pipeline/package.py
  20 | @@ -828,6 +828,12 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  21 |                     type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
  22 |  
  23 |  
  24 | +def question_hook(segs):
  25 | +    """Ruling 37: the hook ends on a question (its text ends with '?', the render's R1 test). Such a hook is allowed; the
  26 | +    clips-alone verdict must find the join after it followable, since no bridge may follow a question."""
  27 | +    return bool(segs) and str(segs[0].get("text") or "").rstrip().endswith("?")
  28 | +
  29 | +
  30 |  def ly_shape(pk):
  31 |      """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
  32 |      last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
  33 | @@ -862,6 +868,9 @@ def ly_shape(pk):
  34 |      med = pk.get("medley") or {}
  35 |      if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
  36 |          fails.append("the clips-alone verdict was not measured (L-y 3)")
  37 | +    elif question_hook(segs) and js and js[0] in med["flagged"]:
  38 | +        fails.append(f"ruling 37: a hook ending on a question takes no bridge after it, so {js[0]} must be followable "
  39 | +                     f"(the render's R1 reads the sealed clips-alone verdict)")
  40 |      elif sorted(bridged) != sorted(med["flagged"]):
  41 |          fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
  42 |                       f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
  43 | @@ -1276,6 +1285,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  44 |                      dropped |= weak
  45 |                      rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
  46 |                      continue
  47 | +                if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
  48 | +                    dropped.add(segs[1]["moment_id"])
  49 | +                    rec["why"] = (f"ruling 37: the join after the question hook must be followable without a bridge, and "
  50 | +                                  f"the clips alone flag {joins(labs)[0]}: re-lined")
  51 | +                    continue
  52 |                  join = None
  53 |                  if med["flagged"]:
  54 |                      k = joins(labs).index(med["flagged"][0])
  55 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
  56 | index afffc2c0..17896e45 100644
  57 | --- a/tests/eligibility/test_eligibility.py
  58 | +++ b/tests/eligibility/test_eligibility.py
  59 | @@ -401,8 +401,11 @@ class TestSpan(unittest.TestCase):
  60 |          src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="Bitcoin Magazine",
  61 |                       age_h=100)
  62 |          r = E.eligible(E.Span(src, 0, 0), ctx("hook", story=statements(E.Span(src, 0, 0))))
  63 | -        for n in ("not_current", "layout_ineligible", "not_sentence_ready", "not_statement", "start_case", "duration"):
  64 | +        for n in ("not_current", "layout_ineligible", "not_sentence_ready", "start_case", "duration"):
  65 |              self.assertIn(n, r.names())
  66 | +        self.assertNotIn("not_statement", r.names())                   # ruling 37: a question may end the HOOK
  67 | +        rc = E.eligible(E.Span(src, 0, 0), ctx("clip", story=statements(E.Span(src, 0, 0))))
  68 | +        self.assertIn("not_statement", rc.names())                     # ... never a clip
  69 |          self.assertTrue(any("conjunction" in t for t in r.facts["targets_missed"]))             # L-o: ranked
  70 |  
  71 |  
  72 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  73 | index 15b1d5a1..0422f1e0 100644
  74 | --- a/tests/package/test_medley.py
  75 | +++ b/tests/package/test_medley.py
  76 | @@ -726,6 +726,45 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
  77 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
  78 |  
  79 |  
  80 | +class TestRuling37QuestionHook(unittest.TestCase):
  81 | +    """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
  82 | +    which must be followable with no bridge (no bridge may follow a question; the render's R1 reads the sealed
  83 | +    gates.medley flagged list)."""
  84 | +
  85 | +    Q = "Why does Bitcoin keep falling every time Nvidia does?"
  86 | +
  87 | +    def ms(self):
  88 | +        return [dict(pm("h", "A", 12.0), text=self.Q), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]
  89 | +
  90 | +    def test_the_question_hook_test(self):
  91 | +        self.assertTrue(PK.question_hook([{"text": self.Q + "  "}]))
  92 | +        self.assertFalse(PK.question_hook([{"text": "Bitcoin is money."}]))
  93 | +        self.assertFalse(PK.question_hook([]))
  94 | +
  95 | +    def test_a_flagged_join_after_a_question_hook_re_lines_without_that_clip(self):
  96 | +        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["hook -> clip_01"], None, Rig.LINE),
  97 | +                                                    (True, [], None, Rig.LINE)], [None])
  98 | +        out = rig.run()
  99 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])          # x dropped, never bridged
 100 | +        self.assertIn("ruling 37", out["tried"][0]["why"])
 101 | +        self.assertIsNotNone(out["package"])
 102 | +        self.assertEqual(out["package"]["segments"][0]["text"], self.Q)
 103 | +
 104 | +    def test_a_flagged_join_between_clips_is_bridged_as_usual(self):
 105 | +        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)],
 106 | +                  [{"text": "Next, a show on chips.", "cites": ["y"], "why": "no referent"}])
 107 | +        out = rig.run()
 108 | +        self.assertEqual(rig.write_calls[0][1][0], 1)                                     # the bridge after clip 1
 109 | +        self.assertIsNotNone(out["package"])
 110 | +
 111 | +    def test_ly_shape_refuses_a_question_hook_whose_first_join_was_flagged(self):
 112 | +        pk = medley_pk(bridge="hook -> clip_01", after=0, flagged=["hook -> clip_01"], intro="Next, on chips.")
 113 | +        pk["segments"][0]["text"] = self.Q
 114 | +        ok, why = PK.ly_shape(pk)
 115 | +        self.assertFalse(ok)
 116 | +        self.assertTrue(any("ruling 37" in w for w in why), why)
 117 | +
 118 | +
 119 |  class TestRuling34Screen(unittest.TestCase):
 120 |      """Ruling 34 (render side merged at 55315124): the topic test is the miner's about-Bitcoin screen the pin seals;
 121 |      the hook must pass it itself, a clip may complete the previous claim, and the MEDLEY must name Bitcoin once."""
 122 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
pins; the integrator renders them. The pin stage must never seal a line-up the render would refuse.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 37 (03:12 ET Nov 13): "not_statement: a clip that ends on a question is allowed in the HOOK
role only; the clips-alone verdict and coherence check judge the join after it as usual. Not as a middle or last
clip." The integrator is changing the render's edl_rules R1 to match. It accepts a hook ending on "?" when the sealed
clips-alone verdict (gates.medley) is PASS, not replayed, and its "flagged" list does NOT contain "hook -> clip_01",
and gates.coherence is PASS. A flagged join takes a bridge, and the render's bridge rule refuses a bridge after a
clip that ends on a question.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (the relaxation is the orchestrator's ruling).

The change:
1. pipeline/eligibility.py: the "not_statement" reason (the span ends on a question) is no longer raised for the HOOK
   role; it stays for every other role (clip, evidence).
2. pipeline/package.py:
   - question_hook(segs): the hook's text ends with "?" (the render's R1 test);
   - in build()'s line-up loop, right after the clips-alone verdict passes: if the hook is a question and the verdict
     flags the join after it, clip_01 is dropped and the angle re-lined (no bridge may follow a question);
   - ly_shape(pk), the sealed L-y shape gate: refuses a package whose question hook's first join was flagged.
3. Tests:
   - eligibility: a hook ending on "?" carries no not_statement; a clip still does;
   - the predicate;
   - a flagged join after a question hook re-lines without that clip and then packages;
   - a flagged join between clips is bridged as before;
   - ly_shape refuses the question-hook case.

Check in particular:
- that a question can now end ONLY the hook, never a middle or last clip;
- that the join after a question hook can never carry a bridge in a sealed pin;
- that the re-line cannot loop forever (dropped grows);
- that nothing else changes.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

