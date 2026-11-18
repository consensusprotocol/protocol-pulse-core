# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_0957
# Branch: pp-selectid
# Generated: 2026-11-18 09:57 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_0957/C1_STEP.diff (100 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index 690d09a..cca269f 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -98,7 +98,7 @@ def carry_class(r, p, op, texts):
   6 |      return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"
   7 |  
   8 |  
   9 | -def class_84(spoken, approved):
  10 | +def class_84(spoken, approved, approved_tokens=None):
  11 |      """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
  12 |      it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
  13 |      against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
  14 | @@ -107,9 +107,17 @@ def class_84(spoken, approved):
  15 |      2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
  16 |      3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
  17 |      4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
  18 | -    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text."""
  19 | +    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text.
  20 | +    approved_tokens (RULING 148 (3)): the approved side's canon tokens as they are (class_131's merged reading), never
  21 | +    tokenised again from a joined string: canon reads digits, a space and three digits as one number ('24 7 365' ->
  22 | +    ['24', '7365']), so a re-read join can differ from its own tokens (build 149: Yahoo Finance f0a51c45 held on '7 365'
  23 | +    against '7365', which the render's lock adopts). approved stays the text the critical-word test reads."""
  24 |      texts = (spoken, approved)
  25 | -    r, p, ops = diff(spoken, approved)
  26 | +    if approved_tokens is None:
  27 | +        r, p, ops = diff(spoken, approved)
  28 | +    else:
  29 | +        r, p = canon.canon_tokens(spoken), list(approved_tokens)
  30 | +        ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
  31 |      drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
  32 |      out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
  33 |      r2 = [t for i, t in enumerate(r) if i not in drop]
  34 | @@ -263,7 +271,8 @@ def class_131(spoken, approved, adj):
  35 |      if sp != merged and sp != spill_trimmed(merged, s):  # ruling 72 adopts only the second recogniser's own reading
  36 |          out.append(held("the spoken text is neither the merged reading nor the second recogniser's own reading of the "
  37 |                          "span (ruling 72 adopts only its reading)"))
  38 | -    for x in class_84(spoken, " ".join(merged)):        # ruling 72 on top of the merged reading, as today
  39 | +    for x in class_84(spoken, " ".join(merged), merged):   # ruling 72 on top of the merged reading, as today; RULING
  40 | +        #   148 (3): compared as its tokens, never re-read from the join ('24 7 365' would read ['24', '7365'])
  41 |          out.append(dict(x, took="ruling 72", edge_distance=None, **(
  42 |              {"why": "the spoken text differs from the merged reading outside ruling 84's class"} if x["class"] is None
  43 |              else {})))
  44 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
  45 | index 957d68e..a70ed0c 100644
  46 | --- a/tests/package/test_lock_precheck.py
  47 | +++ b/tests/package/test_lock_precheck.py
  48 | @@ -387,6 +387,51 @@ class TestRuling135(unittest.TestCase):
  49 |          self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
  50 |  
  51 |  
  52 | +class TestRuling148TheMergedReadingKeepsItsTokens(unittest.TestCase):
  53 | +    """RULING 148 (3) (orchestrator 09:38 ET Nov 18): build 149 lost Yahoo Finance f0a51c45 to this side's own re-check,
  54 | +    not to the render's lock, which adopts the clip under ruling 131 (A). class_131 joined the merged reading's canon
  55 | +    tokens with spaces and class_84 tokenised the join again; canon reads digits, a space and three digits as one number
  56 | +    (spaced thousands), so '24 7 365' became ['24', '7365'] against the spoken ['24', '7', '365'] and held as a number
  57 | +    (law L-v 2). The readings below are the render's lock record (F536pi4mr7Y 461.650-478.940, decoder 50fa01b400bd)."""
  58 | +    RUN = ("But if you're wondering why having decentralized money that's available 24 -7, 365, that has no CEO and is "
  59 | +           "mined by a decentralized network around the world, like Bitcoin, is important. Well, when you want access "
  60 | +           "to your money with Bitcoin, you have it.")
  61 | +    APP = ("But, you know, if you're wondering why having decentralized money that's available 24 -7, 365, that has no "
  62 | +           "CEO in his mind by a decentralized network. around the world, like Bitcoin is important. Well, when you want "
  63 | +           "access to your money with Bitcoin, you have it.")
  64 | +    SEC = ("is. But, you know, if you're wondering why having decentralized money that's available 24/7/365, uh, that "
  65 | +           "has no CEO and is mined by a decentralized network around the world, like Bitcoin, is important, well, when "
  66 | +           "you want access to your money, with Bitcoin, you have it. Now,")
  67 | +    SPOKEN = APP.replace("in his mind", "and is mined")
  68 | +    PAIRS = [{"run": "", "approved": "you know", "second_reads": "approved", "took": "approved",
  69 | +              "agreed": ["approved", "second"], "edge_distance": 1},
  70 | +             {"run": "and is mined", "approved": "in his mind", "second_reads": "run", "took": "run",
  71 | +              "agreed": ["run", "second"], "edge_distance": 17}]
  72 | +
  73 | +    def adj(self):
  74 | +        return {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": self.APP,
  75 | +                "second_recogniser": self.SEC, "pairs": self.PAIRS}
  76 | +
  77 | +    def test_the_cause_a_join_is_not_its_tokens(self):
  78 | +        self.assertEqual(C.canon_tokens("24 7 365"), ["24", "7365"])
  79 | +        self.assertEqual(C.canon_tokens("24 -7, 365"), ["24", "7", "365"])
  80 | +
  81 | +    def test_the_render_locks_adoption_is_this_sides_too(self):
  82 | +        self.assertEqual([r for r in AT.class_131(self.SPOKEN, self.APP, self.adj()) if r["class"] is None], [])
  83 | +        s = LP.segments_of([{"video_id": "F536pi4mr7Y", "start": 461.65, "end": 478.94, "text": self.APP}])[0]
  84 | +        d = LP.decide(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
  85 | +        self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
  86 | +
  87 | +    def test_a_number_that_differs_still_holds(self):
  88 | +        for spoken in (self.SPOKEN.replace("365", "366"), self.SPOKEN.replace("24 -7", "25 -7")):
  89 | +            self.assertTrue([r for r in AT.class_131(spoken, self.APP, self.adj()) if r["class"] is None], spoken)
  90 | +
  91 | +    def test_class_84_reads_given_tokens_as_they_are(self):
  92 | +        self.assertEqual([x for x in AT.class_84("24 -7, 365 days", "24 7 365 days") if x["class"] is None],
  93 | +                         [{"spoken": "7 365", "approved": "7365", "class": None}])    # the join, re-read
  94 | +        self.assertEqual(AT.class_84("24 -7, 365 days", "24 7 365 days", ["24", "7", "365", "days"]), [])
  95 | +
  96 | +
  97 |  class TestRuling142(unittest.TestCase):
  98 |      """RULING 142 (orchestrator 14:32 ET Nov 17), the integrator's batch 110 mirrored (its canon.py byte-identical, its
  99 |      adjudicate_lock hunk in attest.class_131): (1) a hyphen right after a number and a space, before a digit, is never
 100 | 
```

---

pp-selectid: RULING 148 (3) / 149 (orchestrator 09:56 ET Nov 18): ONE RULE IN ONE FILE (pipeline/attest.py).
THE DEFECT (build 149, 09:34 ET): this side's re-check of the render lock's adoption (attest.class_131, step 5) held Yahoo
Finance f0a51c45 although the render's own lock adopts it under ruling 131 (A). class_131 builds the merged reading as
CANON TOKENS (merged), then called class_84(spoken, " ".join(merged)): class_84 tokenises that join AGAIN, and canon reads
digits, a space and three digits as ONE number (its spaced-thousands rule, canon.py _SPACED_THOUSANDS, unchanged:
'74 000' = 74000). So the merged tokens ['24', '7', '365'] re-read as ['24', '7365'] against the spoken text's
['24', '7', '365'] ('24 -7, 365'): a number difference, held (law L-v 2). The record's own readings agree word for word.
THE CHANGE: class_84(spoken, approved, approved_tokens=None). Given approved_tokens, it compares canon_tokens(spoken)
against those tokens AS THEY ARE (the same SequenceMatcher opcodes diff() makes); approved stays the text the critical-
word test reads (texts = (spoken, approved), unchanged). class_131 passes merged as approved_tokens. Every other caller
passes none: unchanged.
TESTS (tests/package/test_lock_precheck.py, TestRuling148TheMergedReadingKeepsItsTokens): the render lock's record of
f0a51c45 (its three readings and two pairs, verbatim) -> class_131 holds nothing and LP.decide adopts under ruling 131
(A); a real number difference (366 for 365, 25 for 24) still holds; class_84 with tokens reads them as they are, and
the join re-read shows the defect. Mutations: 2 of 2 killed (the old join-only call; class_84 ignoring the tokens);
control passes; suites 42 files / 938 passed, exit 0.
PLEASE CHECK: (1) can approved_tokens let a genuine number / name / negation difference through? (2) is the merged
reading's critical-word test (texts) still the same as before? (3) anything else this changes.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
