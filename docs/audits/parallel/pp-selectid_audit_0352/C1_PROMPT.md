# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0352
# Branch: pp-selectid
# Generated: 2026-11-13 04:11 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0352/C1_STEP.diff (161 lines)
```
   1 | diff --git a/pipeline/moments.py b/pipeline/moments.py
   2 | index eb78ab32..5d0130c5 100644
   3 | --- a/pipeline/moments.py
   4 | +++ b/pipeline/moments.py
   5 | @@ -355,6 +355,16 @@ naming a company neutrally is not an accusation.
   6 |  Return ONLY this JSON object: {{"risks": [], "about_bitcoin": "yes", "why": "..."}}"""
   7 |  
   8 |  
   9 | +def ad_read_marker(moment_text, before_text=""):
  10 | +    """The exclusion screen's DETERMINISTIC part: an ad-read marker in the moment, or in the sentence right before it
  11 | +    (an ad read runs on) -> the reason, else None. exclusion_verdict() and package.build() (before step A) share it."""
  12 | +    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
  13 | +    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
  14 | +        if AD_MARKERS.search(txt):
  15 | +            return f"ad-read marker '{AD_MARKERS.search(txt).group(0)}' in {where}"
  16 | +    return None
  17 | +
  18 | +
  19 |  def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
  20 |      """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
  21 |      screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
  22 | @@ -363,11 +373,10 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
  23 |      is also NOT measured (the exam adapter reports it as such)."""
  24 |      import providers as P
  25 |      from story_semantics import quote_data
  26 | -    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
  27 | -    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
  28 | -        if AD_MARKERS.search(txt):
  29 | -            return {"verdict": "exclude", "why": f"ad-read marker '{AD_MARKERS.search(txt).group(0)}' in {where}",
  30 | -                    "risks": ["ad_read"], "backend": "deterministic", "measured": True, "replayed": False}
  31 | +    why = ad_read_marker(moment_text, before_text)
  32 | +    if why:
  33 | +        return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
  34 | +                "replayed": False}
  35 |      r = None
  36 |      try:
  37 |          r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
  38 | diff --git a/pipeline/package.py b/pipeline/package.py
  39 | index c18ce11e..156338fd 100644
  40 | --- a/pipeline/package.py
  41 | +++ b/pipeline/package.py
  42 | @@ -569,6 +569,24 @@ def stand_alone_check(segs):
  43 |      return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  44 |  
  45 |  
  46 | +def ad_read_out(ms, sources):
  47 | +    """{moment id: why} for the moments the exclusion screen's DETERMINISTIC part refuses (moments.ad_read_marker: an
  48 | +    ad-read marker in the moment or in the sentence right before it, the same context exclusion_for() reads). The same
  49 | +    rule refuses them at the package stage; run first, the angles are never built around them. A moment with no
  50 | +    Source or no context is left to the package stage, which refuses it (fail closed)."""
  51 | +    import moments as M
  52 | +    out = {}
  53 | +    for m in ms:
  54 | +        try:
  55 | +            before, _ = CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
  56 | +        except KeyError:
  57 | +            continue
  58 | +        why = M.ad_read_marker(m["text"], before) if before is not None else None
  59 | +        if why:
  60 | +            out[m["moment_id"]] = why
  61 | +    return out
  62 | +
  63 | +
  64 |  def no_role_on_screen(m):
  65 |      """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  66 |      opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  67 | @@ -1024,17 +1042,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  68 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  69 |      no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  70 |      ms = [m for m in ms if m["moment_id"] not in no_role]
  71 | +    ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  72 | +    ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  73 |      wv, wf = _writers(router)
  74 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
  75 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  76 |      levels = current_levels(sources.values(), ctx)
  77 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  78 | -           "no_role": no_role,
  79 | +           "no_role": no_role, "ad_read": ad_read,
  80 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  81 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  82 |             "package": None}
  83 |      log(f"  {n_usable} usable, {len(no_role)} of them left out (they open on a conjunction or reply fragment, which "
  84 | -        f"the render's STAND_ALONE fails with no clip scorer), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  85 | +        f"the render's STAND_ALONE fails with no clip scorer), {len(ad_read)} on an ad-read marker (the exclusion "
  86 | +        f"screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  87 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  88 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
  89 |          return out
  90 | @@ -1402,6 +1423,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  91 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
  92 |                  break
  93 |      out["package"] = out["packages"][0] if out["packages"] else None
  94 | +    if out["package"] is None and not out.get("why_none"):       # every angle ended without a package: say why
  95 | +        out["why_none"] = ("no angle gave a package: " + "; ".join(f"angle {t.get('angle')}: {t.get('why')}"
  96 | +                                                                 for t in out["tried"]))[:900] if out["tried"] else \
  97 | +            "no angle gave a line-up to try"
  98 |      out["seconds"] = round(time.time() - t0, 1)
  99 |      out["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 100 |      return out
 101 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 102 | index c6316620..b79bf9aa 100644
 103 | --- a/tests/package/test_medley.py
 104 | +++ b/tests/package/test_medley.py
 105 | @@ -506,6 +506,8 @@ class TestBuildLoop(unittest.TestCase):
 106 |          self.assertIsNone(out["package"])
 107 |          self.assertEqual(rig.write_calls, [])
 108 |          self.assertIn("no through-line", out["tried"][0]["why"])
 109 | +        self.assertTrue(out["why_none"].startswith("no angle gave a package: angle 1: the clips alone have no "
 110 | +                                                   "through-line"), out["why_none"])     # never None (03:39 build)
 111 |  
 112 |      def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
 113 |          rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
 114 | @@ -723,6 +725,46 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 115 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 116 |  
 117 |  
 118 | +class TestAdReadBeforeTheAngle(unittest.TestCase):
 119 | +    """The exclusion screen's deterministic part (moments.ad_read_marker) runs before step A, so no angle is built
 120 | +    around a moment the package stage would refuse. The 03:39 build lost its line-up's hook to it after the write."""
 121 | +
 122 | +    def test_the_marker_in_the_moment_or_the_sentence_before_it(self):
 123 | +        import moments as M
 124 | +        self.assertEqual(M.ad_read_marker("Bitcoin is money.", "Use my code at checkout. Link in the description."),
 125 | +                         "ad-read marker 'Link in the description' in the sentence before it")
 126 | +        self.assertEqual(M.ad_read_marker("This episode is sponsored by a wallet. Bitcoin is money.", ""),
 127 | +                         "ad-read marker 'sponsored' in the moment")
 128 | +        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", "Link in the description. Bitcoin rose today."))
 129 | +        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", None))
 130 | +
 131 | +    def test_ad_read_out_reads_the_same_context_as_the_exclusion_screen(self):
 132 | +        import context_integrity as CI
 133 | +        ctxs = {"a": ("Grab it now. Link in the description.", "x"), "b": ("Bitcoin rose today.", "x"),
 134 | +                "c": (None, None)}
 135 | +        saved = CI.context_around
 136 | +        try:
 137 | +            CI.context_around = lambda src, *a: ctxs[src]
 138 | +            ms = [dict(pm(k, k.upper(), 12.0), sentences=[0, 0], words=[0, 1]) for k in ("a", "b", "c", "d")]
 139 | +            got = PK.ad_read_out(ms, {"va": "a", "vb": "b", "vc": "c"})       # d has no Source: left to the package
 140 | +        finally:
 141 | +            CI.context_around = saved
 142 | +        self.assertEqual(got, {"a": "ad-read marker 'Link in the description' in the sentence before it"})
 143 | +
 144 | +    def test_build_leaves_an_ad_read_moment_out_before_the_angle(self):
 145 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 146 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 147 | +        saved = PK.ad_read_out
 148 | +        try:
 149 | +            PK.ad_read_out = lambda ms_, sources: {"q": "ad-read marker 'promo code' in the moment"}
 150 | +            out = rig.run()
 151 | +        finally:
 152 | +            PK.ad_read_out = saved
 153 | +        self.assertEqual(out["ad_read"], {"q": "ad-read marker 'promo code' in the moment"})
 154 | +        self.assertFalse(any("id=q " in p for role, p in rig.prompts if role == "angle_write"))
 155 | +        self.assertIsNotNone(out["package"])
 156 | +
 157 | +
 158 |  class TestNoVoiceRealGates(unittest.TestCase):
 159 |      """Audit 2240 C2 (glm N8): a no-voice package through the REAL VO-fidelity and context-integrity decisions (canned
 160 |      model replies, no stubbed gate): every required row, the medley rows included, exactly PASS, and the pin is
 161 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
package.build() turns moments into a sealed package, in this order:
1. usable();
2. the render's STAND_ALONE opener filter (no_role_on_screen);
3. step A (L-s context, a paid verdict per batch of 8 moments);
4. L-v 2 + CUTTABLE (a second recogniser per moment);
5. the hook onset;
6. the ANGLE step (one paid writer call proposes up to 3 angles, each a set of moments in play order);
7. per angle, line-ups, writes, and the per-clip gates. One of those gates is the exclusion screen: package.exclusion_for
   calls moments.exclusion_verdict on each segment's moment text and the context before it.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the 03:39 ET build's angle 1, line-up 1 passed the clips-alone verdict, and its takeaway passed the cheap checks.
Then the exclusion screen's DETERMINISTIC part refused the HOOK ("ad-read marker 'link in the description' in the
sentence before it"). The angle was re-lined; no angle could form another line-up; the build ended with no package.
And its record said why_none = None ("no package (None)"), because no code path names the reason when every angle ends
without a package. Both are flagged defects (law K2: flag, do not silently delete).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. This change must refuse exactly what the package
  stage already refuses, only EARLIER, and must not pass anything new.

The change:
1. pipeline/moments.py: ad_read_marker(moment_text, before_text) holds exclusion_verdict's deterministic screen (an
   AD_MARKERS match in the moment, or in the last sentence of the context before it) and returns the reason, else None.
   exclusion_verdict calls it, with the same return record as before. The model verdict after it is unchanged.
2. pipeline/package.py:
   - ad_read_out(ms, sources): for each moment, the SAME context exclusion_for reads (CI.context_around on the
     moment's Source, by source_key else video_id). A moment ad_read_marker refuses is recorded with its reason.
   - A moment with no Source (KeyError) or no context (None) is skipped here and left to the package stage, which
     refuses a moment without context (exclusion_for: "no context" -> exclude).
   - build() leaves those moments out right after the STAND_ALONE opener filter, before step A. They are recorded in
     out["ad_read"] and on the log line. out["usable"] is unchanged in meaning.
   - build(): when no package was made and nothing else set why_none, why_none names every tried angle's own why:
     "no angle gave a package: angle N: <why>; ...", or "no angle gave a line-up to try".
3. tests/package/test_medley.py:
   - the marker in the moment or the sentence before, and no marker earlier in the context;
   - ad_read_out reads the same context, and skips a moment with no Source or no context;
   - build() leaves an ad-read moment out of the angle prompt and still packages the rest;
   - why_none is named when every angle fails.

Check in particular:
- that ad_read_out refuses exactly what exclusion_verdict's deterministic part would refuse at the package stage, on
  the same text and the same context, and nothing more;
- that the exclusion verdict at the package stage is unchanged (its deterministic part and its model verdict);
- that a moment skipped here (no Source, no context) still cannot pass the package stage;
- that why_none never hides a reason another path already set.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

