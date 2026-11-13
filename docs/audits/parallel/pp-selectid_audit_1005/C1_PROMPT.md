# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1005
# Branch: pp-selectid
# Generated: 2026-11-13 09:55 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1005/C1_STEP.diff (145 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c1d391f..9ba7ed7 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -518,6 +518,12 @@ words on what it adds and why it follows the clip before it (an internal note).
   6 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
   7 |  "support": {{"id": "..."}}}}]}}"""
   8 |  
   9 | +HOOK_QUESTION = """THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  10 | +   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  11 | +   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  12 | +   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  13 | +   at all)"""                    # ruling 52 + the 09:59 answer: ONE definition of the hook's job, in both verdicts
  14 | +
  15 |  MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
  16 |  Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
  17 |  opens the video.
  18 | @@ -526,11 +532,7 @@ opens the video.
  19 |  
  20 |  1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
  21 |     "none" if there is none.
  22 | -2) THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  23 | -   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  24 | -   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  25 | -   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  26 | -   at all)
  27 | +2) """ + HOOK_QUESTION + """
  28 |  3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  29 |  4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  30 |     clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
  31 | @@ -579,15 +581,17 @@ picked).
  32 |  """
  33 |  
  34 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
  35 | -different person's own words).
  36 | +different person's own words; the first clip, label "hook", opens the video).
  37 |  
  38 |  {package}
  39 |  
  40 |  1) State the video's through-line in ONE sentence, or "none" if it has none.
  41 | -2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  42 | -3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  43 | +2) """ + HOOK_QUESTION + """
  44 | +3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  45 | +4) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  46 |     1 = no point, or a point the clips do not support).
  47 | -Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "vo_point": 1}}"""
  48 | +Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  49 | +"clips": {{{clip_keys}}}, "vo_point": 1}}"""
  50 |  
  51 |  
  52 |  def current_levels(sources, ctx, hours=24.0):
  53 | @@ -1041,22 +1045,29 @@ NO_LINE = re.compile(r"^\W*(none|no\b|n/?a\b|unclear|nothing|there is no)", re.I
  54 |  
  55 |  def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
  56 |      """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
  57 | -    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7)."""
  58 | +    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
  59 | +    Ruling 52, as the orchestrator answered at 09:59 Nov 13: the HOOK is rated on its own job here too (HOOK_QUESTION,
  60 | +    the same three parts as the clips-alone verdict), and its rating is DERIVED as the lowest part (HOOK_RULE), written
  61 | +    to verdict["clips"]["hook"]; the clips after the hook and vo_point are rated as before."""
  62 |      import providers as P
  63 |      r = None
  64 | +    labs = [sg["label"] for sg in pk["segments"]]
  65 |      try:
  66 | -        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
  67 | -                        avoid_vendor=writer_vendor, avoid_family=writer_family)
  68 | +        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
  69 | +                            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
  70 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  71 |          v = json.loads(r.text.strip())
  72 | -        labs = [sg["label"] for sg in pk["segments"]]
  73 | -        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
  74 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
  75 | +        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "vo_point"} or \
  76 | +                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
  77 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
  78 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
  79 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
  80 |              raise ValueError("coherence verdict out of contract")
  81 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
  82 |          if r is not None and isinstance(e, (ValueError, TypeError)):
  83 |              router.reject(r)
  84 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
  85 | +    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
  86 |      tl = v["through_line"] if isinstance(v["through_line"], str) else ""
  87 |      ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
  88 |          min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
  89 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  90 | index 814be17..f2374ca 100644
  91 | --- a/tests/package/test_medley.py
  92 | +++ b/tests/package/test_medley.py
  93 | @@ -209,6 +209,51 @@ class TestClipsAloneVerdict(unittest.TestCase):
  94 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
  95 |  
  96 |  
  97 | +class TestCoherenceHookRating(unittest.TestCase):
  98 | +    """The orchestrator's answer (09:59): ruling 52's hook rating applies to the coherence verdict after the takeaway as
  99 | +    well. ONE definition of the hook's job (HOOK_QUESTION) in both verdicts; the hook's rating derived, never free-form."""
 100 | +    PK_ = {"title": "Nobody bends the rules", "caption": "three clips",
 101 | +           "vo": {"intro": None, "bridges": ["No ruler, just rules."], "bridges_after_clip": [2], "signoff": "S"},
 102 | +           "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
 103 | +                        {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
 104 | +                        {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
 105 | +
 106 | +    def reply(self, hook=None, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
 107 | +        return {"through_line": line, "hook": dict({"scroll": 5, "alone": 5, "setup": 5}, **(hook or {})),
 108 | +                "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
 109 | +
 110 | +    def run_it(self, reply):
 111 | +        r = Canned(coherence_verdict=[reply])
 112 | +        prompts = []
 113 | +        call = r.call
 114 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 115 | +        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"})
 116 | +        return ok, v, r, prompts
 117 | +
 118 | +    def test_the_hook_is_rated_on_its_own_job_and_derived(self):
 119 | +        ok, v, _, prompts = self.run_it(self.reply(hook={"setup": 3}))
 120 | +        self.assertFalse(ok)
 121 | +        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 122 | +        self.assertIn(PK.HOOK_QUESTION, prompts[0])                 # the one definition, as in the clips-alone verdict
 123 | +        self.assertIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
 124 | +        self.assertIn("For each clip AFTER the hook", prompts[0])
 125 | +        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
 126 | +        ok, v, _, _ = self.run_it(self.reply(hook={"scroll": 4, "alone": 4, "setup": 4}))
 127 | +        self.assertTrue(ok)
 128 | +        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 129 | +        self.assertFalse(self.run_it(self.reply(clips={"clip_02": 3}))[0])      # clips and vo_point as before
 130 | +        self.assertFalse(self.run_it(self.reply(vo=3))[0])
 131 | +
 132 | +    def test_out_of_contract_is_not_measured(self):
 133 | +        good = self.reply()
 134 | +        for bad in ({k: x for k, x in good.items() if k != "hook"}, dict(good, hook={"scroll": 5, "alone": 5}),
 135 | +                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}), dict(good, hook={"scroll": 5, "alone": 5,
 136 | +                                                                                               "setup": 0})):
 137 | +            ok, v, r, _ = self.run_it(bad)
 138 | +            self.assertEqual((ok, v["measured"]), (False, False))
 139 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 140 | +
 141 | +
 142 |  class TestWriteTakeaway(unittest.TestCase):
 143 |      SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 144 |  
 145 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips, then ONE host
takeaway line). Your role: a strict reviewer of a blind verdict's contract.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- Ruling 52 (committed at 88aa6d9c) changed the CLIPS-ALONE verdict (MEDLEY_PROMPT / medley()). The HOOK is rated on
  its own job in three parts the judge answers separately, each 1-5: "scroll" (its first 2-3 seconds stop a scroll),
  "alone" (it stands alone), "setup" (it sets up what follows). Its rating is DERIVED as the lowest part (HOOK_RULE),
  written to verdict["clips"]["hook"]. The clips after the hook keep their through-line rating; the bar is 4.
- The COHERENCE verdict that runs after the takeaway is written (COHERENCE_PROMPT / coherence()) still rated EVERY
  clip, the hook included, on "how much it advances the through-line", plus vo_point. ok = a stated through-line and
  min(all clip ratings + vo_point) >= 4.
- THE ORCHESTRATOR'S ANSWER (09:59 ET Nov 13, verbatim): "YES. Ruling 52's hook rating (the hook judged on its own job:
  stops the scroll, stands alone, sets up what follows) applies to the coherence verdict after the takeaway as well.
  One definition of the hook's job everywhere it is rated."

The change:
1. HOOK_QUESTION: the hook's three-part question, ONE text, defined before both prompts.
   - MEDLEY_PROMPT now embeds it. Verified: the formatted MEDLEY_PROMPT is BYTE-IDENTICAL to the committed one, so the
     clips-alone verdict is unchanged.
   - COHERENCE_PROMPT embeds the same text. It says the first clip ("hook") opens the video, asks the through-line
     rating "for each clip AFTER the hook", keeps vo_point, and writes the clip keys out per package.
2. coherence():
   - the contract requires exactly {"through_line", "hook" (the three parts, ints 1-5), "clips" (the labels after the
     hook), "vo_point"}; anything else is not measured, rejected, never a pass;
   - the hook's rating is derived as the lowest part and written to verdict["clips"]["hook"], as in medley();
   - the pass rule is unchanged.
   Downstream readers are unchanged: the takeaway-redo branch reads min(coh["clips"]) and vo_point; the weak-clip
   drop reads segments[1:] only.
3. tests/package/test_medley.py:
   - one hook part at 3 fails, all parts at 4 pass, and the derived rating is recorded;
   - the prompt carries HOOK_QUESTION, which is also in MEDLEY_PROMPT;
   - a clip at 3 or vo_point 3 still fails;
   - out-of-contract replies are not measured and are rejected.
- test_medley 92 OK; every other suite OK.

Check in particular:
- that the hook's job has exactly one definition, used by both verdicts;
- that the clips-alone verdict did not change;
- that the coherence verdict's clips and vo_point are judged exactly as before;
- that a malformed reply is never a pass;
- that the derived hook rating feeds the same pass rule.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

