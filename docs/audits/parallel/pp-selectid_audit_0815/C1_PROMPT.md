# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0815
# Branch: pp-selectid
# Generated: 2026-11-13 08:07 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0815/C1_STEP.diff (167 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 63f680d..5b7a168 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -516,17 +516,26 @@ Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "
   6 |  "support": {{"id": "..."}}}}]}}"""
   7 |  
   8 |  MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
   9 | -Each clip is a person's own words from a show; the shows were not in one conversation.
  10 | +Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
  11 | +opens the video.
  12 |  
  13 |  {clips}
  14 |  
  15 |  1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
  16 |     "none" if there is none.
  17 | -2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  18 | -3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  19 | +2) THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  20 | +   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  21 | +   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  22 | +   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  23 | +   at all)
  24 | +3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  25 | +4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  26 |     clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
  27 |     words.
  28 | -Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
  29 | +Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  30 | +"clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
  31 | +HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
  32 | +HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
  33 |  
  34 |  WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  35 |  THE ANGLE (the point this video makes): "{angle}"
  36 | @@ -917,10 +926,14 @@ def joins(labs):
  37 |  
  38 |  def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  39 |      """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
  40 | -    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
  41 | -    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
  42 | -    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
  43 | -    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
  44 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip after the hook on how much it
  45 | +    advances it, and per join whether a viewer can follow the jump. RULING 52: the HOOK is rated on its own job, in
  46 | +    three parts the judge answers separately (HOOK_PARTS: stops a scroll in its first 2-3 s, stands alone, sets up
  47 | +    what follows), and its rating is DERIVED, never free-form: the lowest part (HOOK_RULE), written to
  48 | +    verdict["clips"]["hook"]; the parts stay in verdict["hook"]. Never the vendor / family of the writer. -> (ok,
  49 | +    verdict): ok when the through-line is stated (>= 4 words, not 'none'), every rating (the hook's derived one
  50 | +    included) is >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable; verdict["flagged"] = the joins
  51 | +    a viewer could not follow (a bridge may go only there, L-y 2)."""
  52 |      import providers as P
  53 |      labs = labels(len(segs))
  54 |      js = joins(labs)
  55 | @@ -929,12 +942,14 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  56 |      r = None
  57 |      try:
  58 |          r = router.call("coherence_verdict",
  59 | -                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
  60 | -                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
  61 | +                        MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
  62 | +                                             joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
  63 |                          1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  64 |          v = json.loads(r.text.strip())
  65 | -        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
  66 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
  67 | +        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "joins"} or \
  68 | +                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
  69 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
  70 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
  71 |                  any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
  72 |                  not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
  73 |                  any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
  74 | @@ -944,6 +959,7 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  75 |          if r is not None and isinstance(e, (ValueError, TypeError)):
  76 |              router.reject(r)
  77 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
  78 | +    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
  79 |      tl = v["through_line"] if isinstance(v["through_line"], str) else ""
  80 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
  81 |      ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
  82 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  83 | index e231c02..062acfe 100644
  84 | --- a/tests/package/test_medley.py
  85 | +++ b/tests/package/test_medley.py
  86 | @@ -44,6 +44,16 @@ def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of
  87 |                            if j in flagged else "same subject"} for j in js}}
  88 |  
  89 |  
  90 | +def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin.", hook=None):
  91 | +    """The clips-alone JUDGE's raw reply (ruling 52): the hook's three parts, the clips after the hook, the joins."""
  92 | +    js = PK.joins(labs)
  93 | +    h = (ratings or {}).get("hook", 5)
  94 | +    return {"through_line": line, "hook": dict({"scroll": h, "alone": h, "setup": h}, **(hook or {})),
  95 | +            "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
  96 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
  97 | +                          if j in flagged else "same subject"} for j in js}}
  98 | +
  99 | +
 100 |  def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
 101 |      """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
 102 |      labs = PK.labels(n)
 103 | @@ -137,7 +147,7 @@ class TestClipsAloneVerdict(unittest.TestCase):
 104 |          return ok, v, r
 105 |  
 106 |      def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
 107 | -        r = Canned(coherence_verdict=[verdict(self.LABS)])
 108 | +        r = Canned(coherence_verdict=[reply(self.LABS)])
 109 |          prompts = []
 110 |          call = r.call
 111 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 112 | @@ -150,24 +160,47 @@ class TestClipsAloneVerdict(unittest.TestCase):
 113 |          self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
 114 |  
 115 |      def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
 116 | -        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
 117 | +        ok, v, _ = self.run_it(reply(self.LABS, flagged=["clip_01 -> clip_02"]))
 118 |          self.assertTrue(ok)
 119 |          self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
 120 | -        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
 121 | +        ok, v, _ = self.run_it(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
 122 |          self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
 123 |  
 124 |      def test_no_through_line_or_a_weak_clip_fails(self):
 125 | -        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
 126 | -        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
 127 | -        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
 128 | +        self.assertFalse(self.run_it(reply(self.LABS, line="none"))[0])
 129 | +        self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
 130 | +        self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])
 131 | +
 132 | +    def test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts(self):
 133 | +        prompts = []
 134 | +        r = Canned(coherence_verdict=[reply(self.LABS, hook={"setup": 3})])
 135 | +        call = r.call
 136 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 137 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
 138 | +        self.assertFalse(ok)                              # one part under the bar: the hook's derived rating is 3
 139 | +        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 140 | +        self.assertIn("lowest of scroll / alone / setup", v["hook_rule"])
 141 | +        for part in ('"scroll"', '"alone"', '"setup"', "first 2-3 seconds", "wants the next clip",
 142 | +                     "For each clip AFTER the hook", '"clip_01": 1, "clip_02": 1'):
 143 | +            self.assertIn(part, prompts[0])
 144 | +        self.assertNotIn('"hook": 1', prompts[0])         # the hook is not asked for a through-line rating
 145 | +        ok, v, _ = self.run_it(reply(self.LABS, hook={"scroll": 4, "alone": 4, "setup": 4}))
 146 | +        self.assertTrue(ok)                               # every part at the bar of 4
 147 | +        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 148 | +        ok, v, _ = self.run_it(reply(self.LABS, ratings={"hook": 5, "clip_01": 3}))
 149 | +        self.assertFalse(ok)                              # the clips keep their own rating and bar
 150 |  
 151 |      def test_out_of_contract_is_not_measured_and_rejected(self):
 152 | -        good = verdict(self.LABS)
 153 | +        good = reply(self.LABS)
 154 |          for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
 155 |                      dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
 156 |                      dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
 157 |                      dict(good, vo_point=5),
 158 | -                    dict(good, clips={"hook": 5, "clip_01": 5})):
 159 | +                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),            # the hook among the clips
 160 | +                    dict(good, hook={"scroll": 5, "alone": 5}),                           # a part missing (ruling 52)
 161 | +                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 6}),
 162 | +                    dict(good, hook={"scroll": "5", "alone": 5, "setup": 5}),
 163 | +                    {k: x for k, x in good.items() if k != "hook"}):
 164 |              ok, v, r = self.run_it(bad)
 165 |              self.assertFalse(ok)
 166 |              self.assertFalse(v["measured"])
 167 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook + 2-4 clips played back to back). Your role: a strict reviewer of the blind "clips-alone" verdict.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- medley() asks a blind judge (never the writer's vendor or family) about the clips alone, in play order: is there a
  through-line a viewer can state; a 1-5 rating per clip of how much it advances it; and per join, can a viewer follow
  it. ok = a stated through-line (>= 4 words, not "none"), every rating >= COHERENCE_MIN (4), at most LY_MAX_BRIDGES
  (1) joins not followable. The returned verdict's "clips" dict (keyed "hook", "clip_01", ...) feeds the build loop:
  a rating under 4 marks that segment weak, and ruling 41's swap replaces it (the hook by the next hook).
- Until now the HOOK was rated like a clip, on "how much it advances the through-line". Builds kept failing on hooks
  rated 3 while their clips were rated 4-5.

The order this diff implements (ORCHESTRATOR RULING 52, 08:06 ET Nov 13, verbatim): "THE HOOK IS RATED ON ITS OWN JOB:
YES. In the clips-alone verdict the hook is no longer rated on 'how much it advances the through-line'. The hook's
rating is: does it stop a scroll in its first 2-3 seconds, does it stand alone, and does it set up what follows (a
viewer who hears it wants the next clip). Bar 4, unchanged. The clips keep their present rating and bar. The join
after the hook is judged as now: followable, or the ONE bridge L-y allows. Two flagged joins still fail. Write the hook
question so the judge answers the three parts separately and the rating is derived, not free-form."

The change (pipeline/package.py, tests/package/test_medley.py):
1. MEDLEY_PROMPT:
   - says the first clip (label "hook") opens the video;
   - asks the hook's three parts separately, each 1-5: "scroll" (do its first 2-3 seconds stop a viewer from
     scrolling past), "alone" (does it stand alone), "setup" (does it set up what follows, so that a viewer who hears
     it wants the next clip);
   - asks the through-line rating only "for each clip AFTER the hook";
   - the join question is unchanged;
   - the JSON shape is {"through_line", "hook": {"scroll", "alone", "setup"}, "clips": {the labels after the hook},
     "joins"}, with the clip keys written out per line-up.
2. medley():
   - the contract requires exactly those keys, the three hook parts as ints 1-5, and the clips after the hook only;
     anything else is out of contract: not measured, rejected, never a pass;
   - the hook's rating is DERIVED as the LOWEST of its three parts (HOOK_RULE: every part must reach the bar) and
     written to verdict["clips"]["hook"]. The parts stay in verdict["hook"], the rule in verdict["hook_rule"];
   - the pass rule is unchanged (min over every rating, the hook's derived one included, >= 4; joins as before).
     Every downstream reader (weak-segment detection, ruling 41's hook swap, the logs, the sealed medley row) is
     unchanged.
3. tests:
   - reply() builds the judge's raw reply in the new shape;
   - the clips-alone tests use it;
   - a new test: one part at 3 gives a derived hook rating of 3 and a FAIL; all parts at 4 pass; the prompt asks the
     three parts and no through-line rating for the hook; a clip at 3 still fails;
   - out-of-contract cases: a part missing, a part out of range or a string, the hook among the clips, no "hook" key.
- test_medley 82 OK; every other suite OK.

A stated choice (K1): the derivation is min(scroll, alone, setup), so the hook passes only when ALL three parts reach
the bar. The ruling says the rating is "derived, not free-form" but does not fix the formula. Say so if you read it
differently (for example, a mean).

Check in particular:
- that the hook can no longer pass or fail on a through-line rating, and that clips are rated exactly as before;
- that the derived rating cannot be free-form or missing, and that every malformed reply is never a pass;
- that the joins (the one bridge, two flagged joins fail) are unchanged;
- that the build loop's weak detection and the hook swap still see the hook's rating under "hook".

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

