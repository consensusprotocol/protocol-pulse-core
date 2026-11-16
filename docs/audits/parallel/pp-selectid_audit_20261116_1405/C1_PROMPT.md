# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_1405
# Branch: pp-selectid
# Generated: 2026-11-16 14:05 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_1405/C1_STEP.diff (154 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 52c1dfe..038c3c9 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1552,6 +1552,15 @@ def hook_own(m):
   6 |                  rule=HOOK_OWN_RULE)
   7 |  
   8 |  
   9 | +def opens_16x9(m):
  10 | +    """RULING 123 (2): this moment opens a package sealed formats ['16x9']: the build found no hook for both formats
  11 | +    and its own frames are refused only by ruling 93's 9:16 crop (visual_pin.crop_only), still so on its sealed record.
  12 | +    Only as the HOOK: as a clip its ruling-93 refusal stands."""
  13 | +    import visual_pin as VP
  14 | +    v = m.get("visual") or {}
  15 | +    return bool(m.get("sixteen_nine_only")) and v.get("formats") == ["16x9"] and bool(VP.crop_only(v))
  16 | +
  17 | +
  18 |  def can_open(m):
  19 |      if m.get("visual_hook_block"):                       # RULING 70: its picture may not open the medley
  20 |          return False
  21 | @@ -3088,6 +3097,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  22 |          #   ruling 93: its own frames, per clip; both reasons when both hold (audit 0003 C1, glm)
  23 |          if why_v:
  24 |              m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
  25 | +    sixteen = {}
  26 | +    if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]:   # RULING 123 (2): no hook opens
  27 | +        for m in rated_open:                                                          # both formats: one refused ONLY
  28 | +            why_c = VP.crop_only(m.get("visual"))                                     # by ruling 93's 9:16 crop opens
  29 | +            if why_c:                                                                 # a package sealed 16:9 only
  30 | +                m.pop("visual_hook_block", None)
  31 | +                blocked.pop(m["moment_id"], None)
  32 | +                m["visual"] = dict(m["visual"], formats=["16x9"])                     # sealed: package_pin.formats
  33 | +                m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
  34 |      out["visual"] = out_visual
  35 |      if rated_open:
  36 |          log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
  37 | @@ -3101,7 +3119,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  38 |                          "bar_invalid": live_why,
  39 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
  40 |                          "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
  41 | -                        "visual_blocked": blocked}
  42 | +                        "visual_blocked": blocked,
  43 | +                        **({"sixteen_nine_only": {"hooks": sixteen, "note": "no hook passes for both formats: a hook "
  44 | +                            "refused only by ruling 93's 9:16 crop opens a package sealed formats ['16x9'] (ruling "
  45 | +                            "123 (2))"}} if sixteen else {})}
  46 |      log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} pass "
  47 |          f"{HB.text(live)}" + (f" [{live_why}]" if live_why else "") + (f"; NOT RATED: {hook_err}" if hook_err else "")
  48 |          + f" ({time.time() - t0:.0f} s)")
  49 | @@ -3386,7 +3407,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  50 |                                    if value is not None else {})}}
  51 |          see(order)                                        # RULING 70: the added clip is seen too
  52 |          vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  53 | -                if VP.layout_block(m.get("visual"))}                                 # included, law L-m)
  54 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  55 |          if vbad:
  56 |              note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  57 |              return None
  58 | @@ -3652,7 +3673,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  59 |                  see(segs)                                   # RULING 70: every clip seen before any write is paid
  60 |                  vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  61 |                              "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
  62 | -                        for m in segs if VP.layout_block(m.get("visual"))}                 # included); the cause named
  63 | +                        for m in segs if VP.layout_block(m.get("visual"))                  # included); the cause named
  64 | +                        and not (m is segs[0] and opens_16x9(m))}          # ruling 123 (2): the 16:9-only HOOK only
  65 |                  if vbad or segs[0].get("visual_hook_block"):
  66 |                      vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  67 |                      dropped |= set(vbad)
  68 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
  69 | index a3d31e6..e3f501f 100644
  70 | --- a/pipeline/visual_pin.py
  71 | +++ b/pipeline/visual_pin.py
  72 | @@ -309,6 +309,24 @@ def layout_block(rec):
  73 |      return (f"ruling 93 ({len(why)} item(s)): " + "; ".join(why))[:600] if why else None   # (audit 0003 C2)
  74 |  
  75 |  
  76 | +def crop_only(rec):
  77 | +    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): the reason a measured record's ONLY refusal is ruling 93's 9:16 crop
  78 | +    (a lower third or bug wholly inside the 16:9, not over the speaker, that the 9:16 crop would cut through mid-word),
  79 | +    or None. Such a clip shows whole in 16:9: as a HOOK, when no hook passes for both formats, it may open a package
  80 | +    sealed formats ['16x9'] (package.build). A ticker or crawl, a part outside the 16:9, a speaker covered, a third
  81 | +    person (ruling 70) or an unmeasured or older record: None."""
  82 | +    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
  83 | +            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or \
  84 | +            (formats(rec) and not RENDER_16X9_ONLY):
  85 | +        return None
  86 | +    why = [burned_block(x) for x in rec["burned_in"]]
  87 | +    cut = [x for x, w in zip(rec["burned_in"], why) if w]
  88 | +    if not cut or any(x["kind"] in RUNNING or x["kind"] == CAPTION or not x["whole_in_16x9"] or x["in_9x16"] != "cut"
  89 | +                      or x["covers_speaker"] for x in cut):
  90 | +        return None
  91 | +    return "; ".join(w for w in why if w)
  92 | +
  93 | +
  94 |  def hook_block(rec):
  95 |      """Why this clip may not be the HOOK (ruling 70), or None."""
  96 |      if not (rec or {}).get("measured"):
  97 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  98 | index 4e1f1b8..5f0180f 100644
  99 | --- a/tests/package/test_medley.py
 100 | +++ b/tests/package/test_medley.py
 101 | @@ -4672,5 +4672,52 @@ class TestRuling118StoryFirst(unittest.TestCase):
 102 |              PK.load_candidate(rec)
 103 |  
 104 |  
 105 | +class TestRuling123SixteenNineHook(unittest.TestCase):
 106 | +    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): when no hook passes for both formats, a hook whose ONLY refusal is
 107 | +    ruling 93's 9:16 crop (a lower third the crop would cut mid-word) opens a package sealed formats ['16x9']; a
 108 | +    both-format hook always wins; as a clip its refusal stands."""
 109 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 110 | +    CUT = {"burned_in": [{"kind": "lower_third", "text": "IN THIS EPISODE...", "whole_in_16x9": True, "in_9x16": "cut",
 111 | +                          "covers_speaker": False}]}
 112 | +
 113 | +    def rec(self, **kw):
 114 | +        base = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": self.CUT["burned_in"]}
 115 | +        return dict(base, **kw)
 116 | +
 117 | +    def test_only_a_crop_refusal_qualifies(self):
 118 | +        lt = self.CUT["burned_in"][0]
 119 | +        self.assertTrue(VP.crop_only(self.rec()).startswith("a lower_third the 9:16 crop would cut through mid-word"))
 120 | +        for bad in (dict(lt, kind="ticker"), dict(lt, covers_speaker=True), dict(lt, whole_in_16x9=False)):
 121 | +            self.assertIsNone(VP.crop_only(self.rec(burned_in=[bad])), bad)
 122 | +        self.assertIsNone(VP.crop_only(self.rec(burned_in=[dict(lt, in_9x16="whole")])))    # nothing refused at all
 123 | +        self.assertIsNone(VP.crop_only(self.rec(version="visual-2")))
 124 | +        self.assertIsNone(VP.crop_only(self.rec(measured=False)))
 125 | +        tp = {"kind": "third_person", "text": "a still of a CEO", "why": "w"}
 126 | +        self.assertIsNone(VP.crop_only(self.rec(flags=[tp])))                                # ruling 70 still refuses
 127 | +
 128 | +    def test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only(self):
 129 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT}).run()
 130 | +        self.assertIn("h", out["hook_pool"]["sixteen_nine_only"]["hooks"])
 131 | +        self.assertEqual(out["hook_pool"]["passing"], ["h"])
 132 | +        self.assertIsNotNone(out["package"])
 133 | +        self.assertEqual(out["package"]["segments"][0]["moment_id"], "h")
 134 | +        import package_pin
 135 | +        self.assertEqual(package_pin.formats_of(out["package"]["segments"]), ["16x9"])        # sealed 16:9 only
 136 | +
 137 | +    def test_a_both_format_hook_always_wins(self):
 138 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT},
 139 | +                  hooks={"x": (5, 5, 5)}).run()
 140 | +        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
 141 | +        self.assertEqual(out["hook_pool"]["passing"], ["x"])
 142 | +        self.assertIn("h", out["hook_pool"]["visual_blocked"])
 143 | +
 144 | +    def test_as_a_clip_its_refusal_stands(self):
 145 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)] * 3, [None, None],
 146 | +                  visuals={"y": self.CUT}).run()
 147 | +        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
 148 | +        self.assertTrue(out["package"] is None or "y" not in [s["moment_id"] for s in out["package"]["segments"]])
 149 | +        self.assertTrue(any("y: ruling 93" in (r.get("why") or "") for r in out["tried"]), out["tried"])
 150 | +
 151 | +
 152 |  if __name__ == "__main__":
 153 |      unittest.main()
 154 | 
```

---

pp-selectid: RULING 123 (2) (orchestrator 14:05 ET Nov 16), A 16:9-ONLY HOOK. Files: pipeline/visual_pin.py (crop_only),
pipeline/package.py (the hook pool's exception; opens_16x9; the two per-segment layout checks), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) THE HOOK YOU ALREADY HAVE: What Bitcoin Did 44a6d503 passes the calibrated bar and is refused as
an opener only because the 9:16 crop would cut a lower third. Ruling 93 as amended already lets a clip with burned-in text
go 16:9-ONLY. Apply the same to a hook: when no hook passes for both formats, a hook whose only refusal is ruling 93's 9:16
crop may open a package sealed formats ['16x9'], marked, exactly as the Blockware spotlight was (PBX posted that one in
16:9 and was content). A both-format hook always wins over a 16:9-only one. If this needs code, audit-first."
WHY CODE: ruling 93 as amended makes a burned CAPTION cut by the 9:16 16:9-only (visual_pin.formats, unchanged); a lower
third or bug the 9:16 crop would cut is still a refusal in any role (visual_pin.burned_block, layout_block, unchanged).
The integrator confirms a pin sealed formats ["16x9"] renders 16:9 only through its existing path (batch 86, the
Blockware spotlight) and needs nothing new.

THE CHANGE:
- visual_pin.crop_only(rec): the reason when a measured, current-version record's ONLY refusal is ruling 93's 9:16 crop
  (every refusing burned-in item a lower third or bug wholly inside the 16:9, not over the speaker, cut by the 9:16), no
  ruling-70 third person (hook_block None), else None.
- build(): after the rated openers' frames are judged, ONLY when none of them may open (every one has
  visual_hook_block), each whose refusal crop_only names loses its block, its record gains formats ["16x9"] (so
  package_pin.formats_of seals the pin ["16x9"], unchanged) and sixteen_nine_only; hook_pool records them with a note.
- opens_16x9(m): that flag, the record's ["16x9"], and crop_only still naming it. The two per-segment layout checks
  (the no-voice order's and the line-up's, before any write) skip ruling 93 for that moment ONLY as the hook (order[0],
  segs[0]); as a clip its refusal stands.

UNCHANGED GUARDS: the hook bar, G17a, the opener rule (can_open); hook_block (ruling 70) still refuses; the visual gate
row (inventory: every clip measured); package_pin.formats_of; the render's own checks.

TESTS: crop_only (a crop-cut lower third qualifies; a ticker, a speaker covered, a part outside the 16:9, nothing refused,
an older or unmeasured record, a third person: none); a build with no both-format hook opens on the 16:9-only hook and
seals ["16x9"]; a both-format hook wins (the other stays refused); as a clip the moment is still refused. Mutations
W1-W6 after a control run.

PLEASE CHECK: (1) that the exception fires only when no both-format hook exists; (2) that only the hook is excused, and
only for the 9:16 crop; (3) that the seal says 16:9 only; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
