# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1531
# Branch: pp-selectid
# Generated: 2026-11-17 15:31 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1531/C1_STEP.diff (111 lines)
```
   1 | diff --git a/pipeline/canon.py b/pipeline/canon.py
   2 | index c12c8a1..043464d 100644
   3 | --- a/pipeline/canon.py
   4 | +++ b/pipeline/canon.py
   5 | @@ -254,6 +254,8 @@ def canon_spans(words):
   6 |          if w.strip() in ("-", "+", "\u2212") and j < len(words) and re.match(r"^\s*\$?\d", words[j] or "") and \
   7 |                  (w.strip() != "-" or not i or not re.search(r"[\d.,%]\s*$", words[i - 1] or "")):
   8 |              w, j = w.strip() + (words[j] or "").strip(), j + 1        # '-' '5%' = '-5%'; '70' '-' '75' stays a range
   9 | +        if i and re.match(r"^\s*-\d", w) and re.search(r"\d$", (words[i - 1] or "").rstrip()):
  10 | +            w = w.replace("-", "", 1)        # ruling 142 (1), word by word as in the text: '24' '-7,' reads '24' '7'
  11 |          while j < len(words) and (re.match(r"^\s*[.,][0-9A-Za-z]", words[j] or "") or (     # '$81' ',000'
  12 |                  re.fullmatch(r"\$?\d{1,3}(\d{3})*", w.strip()) and re.fullmatch(r"\d{3}[.,!?]*", (words[j] or "").strip()))):
  13 |              w, j = w + (words[j] or "").strip(), j + 1                                      # '74' '000'
  14 | @@ -316,8 +318,14 @@ def word_form(x, y):
  15 |      """Ruling 142 (2) (orchestrator 2026-11-17 '14:32'): two readings that differ ONLY by a possessive or plural ending
  16 |      on ONE word ('bitcoin' / "bitcoin's" / 'bitcoins' / "bitcoins'"): a word-form pair, decided like any other differing
  17 |      pair by ruling 131 (A)'s two of three (the sealed text takes that reading; all three different still holds). Never
  18 | -    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's)."""
  19 | +    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's). The same "'s" written as a contraction is
  20 | +    the same pair (the ruling's own case, Natalie Brunell feb4b72f: "Bitcoin's a responsibility" against "Bitcoin is a
  21 | +    responsibility"): [t + "'s"] against [t, 'is'] or [t, 'has']."""
  22 |      x, y = list(x or []), list(y or [])
  23 | +    for a, b in ((x, y), (y, x)):                             # the contraction, either way round
  24 | +        if len(a) == 1 and len(b) == 2 and b[1] in ("is", "has") and a[0] == b[0] + "'s" \
  25 | +                and not re.search(r"\d", a[0]):
  26 | +            return True
  27 |      if len(x) != len(y) or not x:
  28 |          return False
  29 |      diff = [(a, b) for a, b in zip(x, y) if a != b]
  30 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  31 | index 01138c8..43b30d8 100644
  32 | --- a/pipeline/lock_precheck.py
  33 | +++ b/pipeline/lock_precheck.py
  34 | @@ -61,7 +61,7 @@ RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 10
  35 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  36 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  37 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  38 | -DECODER = "fe809cb4e680"                      # side): the render's own cut placement joins the pre-check (a passing
  39 | +DECODER = "fc204e4a4385"                      # side): the render's own cut placement joins the pre-check (a passing
  40 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  41 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  42 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  43 | @@ -78,6 +78,9 @@ DECODER = "fe809cb4e680"                      # side): the render's own cut plac
  44 |  #   b52c9354d604ab2303a91e6e6e5f926990987d46448992579684934f62e9392d
  45 |  #   RULING 142 (canon's '24 -7' and canon.word_form, adjudicate_lock's word-form exemption; the integrator's branch
  46 |  #   r141-sign f02dd73c, audited; lockstep as with 135): fe809cb4e680a3bc5df49e4c397e79f6cf2277650ea02c05cf88b34ecc573ebd
  47 | +#   RULING 142, the integrator's batches 111 (the post_live fallback, acquisition-side) + 112 (canon_spans reads '24' '-7,'
  48 | +#   as '24' '7'; word_form takes the contraction [t + "'s"] / [t, 'is' | 'has']; branch r142-postlive 70e78551; one
  49 | +#   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
  50 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  51 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  52 |                          "lock_requests")      # this worktree's; the service only reads it
  53 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
  54 | index 17514ac..34476f1 100644
  55 | --- a/tests/package/test_lock_precheck.py
  56 | +++ b/tests/package/test_lock_precheck.py
  57 | @@ -60,7 +60,7 @@ class TestRequest(Dirs):
  58 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
  59 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
  60 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
  61 | -                         "DcUbBkyeh9M.216.054-228.674.fe809cb4e680.json")             # ruling 142's decoder
  62 | +                         "DcUbBkyeh9M.216.054-228.674.fc204e4a4385.json")             # batches 111 + 112's decoder
  63 |  
  64 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
  65 |          segs = LP.segments_of([HOOK, CLIP])
  66 | @@ -422,6 +422,31 @@ class TestRuling142(unittest.TestCase):
  67 |          self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
  68 |          self.assertEqual(self.decide(self.APP, self.THIRD, None)["verdict"], "hold")    # all three differ
  69 |  
  70 | +    def test_the_contraction_is_the_same_word_form_pair(self):
  71 | +        """Batch 112 (the ruling's own case, Natalie Brunell feb4b72f): "Bitcoin's a responsibility" against "Bitcoin is
  72 | +        a responsibility": [t + "'s"] against [t, 'is' | 'has'], either way round, no digit in t."""
  73 | +        self.assertTrue(C.word_form(["bitcoin's"], ["bitcoin", "is"]))
  74 | +        self.assertTrue(C.word_form(["bitcoin", "has"], ["bitcoin's"]))
  75 | +        for x, y in ((["1990's"], ["1990", "is"]), (["bitcoin's"], ["bitcoin", "was"]), (["bitcoin's"], ["ether", "is"])):
  76 | +            self.assertFalse(C.word_form(x, y), (x, y))
  77 | +        app = "Holding your own keys means Bitcoin's a responsibility that nobody else can carry for you in the end."
  78 | +        run = "Holding your own keys means Bitcoin is a responsibility that nobody else can carry for you in the end."
  79 | +        third = "Holding your own keys means Bitcoin was a responsibility that nobody else can carry for you in the end."
  80 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
  81 | +
  82 | +        def decide(spoken, second, took):
  83 | +            adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": run, "approved": app,
  84 | +                   "second_recogniser": second,
  85 | +                   "pairs": [{"run": "bitcoin is", "approved": "bitcoin's", "took": took, "edge_distance": 5}]}
  86 | +            return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken, adjudication=adj))
  87 | +        self.assertEqual(decide(app, app, "approved")["verdict"], "pass")
  88 | +        self.assertEqual(decide(run, run, "run")["verdict"], "adopt")
  89 | +        self.assertEqual(decide(app, third, None)["verdict"], "hold")
  90 | +
  91 | +    def test_canon_spans_reads_the_hyphen_word_by_word(self):
  92 | +        self.assertEqual([t for t, _, _ in C.canon_spans(["24", "-7,", "365"])], ["24", "7", "365"])
  93 | +        self.assertIn("minus", [t for t, _, _ in C.canon_spans(["it", "fell", "-5%"])])
  94 | +
  95 |      def test_a_name_that_is_no_word_form_still_holds(self):
  96 |          app = self.APP.replace("Bitcoin's", "Ethereum's")
  97 |          adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": app,
  98 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
  99 | index ecccdfc..0a732d6 100644
 100 | --- a/tests/package/test_ruling_105.py
 101 | +++ b/tests/package/test_ruling_105.py
 102 | @@ -40,7 +40,7 @@ BLOCKWARE = record()
 103 |  class TestTheRules(Dirs):
 104 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 105 |          self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 106 | -        self.assertEqual(LP.DECODER, "fe809cb4e680")                                 # ruling 142 moved it
 107 | +        self.assertEqual(LP.DECODER, "fc204e4a4385")                                 # batches 111 + 112 moved it
 108 |          s = LP.segments_of([HOOK])[0]
 109 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 110 |                            at="2026-11-14T21:00:00Z"))
 111 | 
```

---

pp-selectid: RULING 142, the BUILDER'S MIRROR of the integrator's batches 111 + 112 (one decoder lockstep; its branch
r142-postlive 70e78551, audited on its side). The previous lockstep (batch 110 / my 45ad6040) is live. The re-judges under
it still held: f0a51c45 because pinned._majority_text maps tokens back to words with canon.canon_spans word by word, and
the word "-7," alone still read "minus 7"; feb4b72f because its "Bitcoin's" is the CONTRACTION of "Bitcoin is" (a 2-token
against 1-token pair, outside 110's one-token word_form). Files: pipeline/canon.py (copied BYTE-IDENTICAL from the
integrator's staged file, sha256 90f23312a02d402b40daaaf58d89556ecdd2ee526795cd74113b778eb3fbf2a5),
pipeline/lock_precheck.py (DECODER only), tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py.

THE CHANGE:
(a) canon.canon_spans: a word "-<digit>..." right after a word ending in a digit loses its hyphen (the word-by-word form
    of 110's _NUM_HYPHEN; '24' '-7,' reads '24' '7'); a sign after a word ('fell' '-5%') stays 'minus'.
(b) canon.word_form also takes the contraction [t + "'s"] against [t, 'is'] or [t, 'has'], either way round, with no
    digit in t. attest.class_131's critical check already calls canon.word_form (my 45ad6040, unchanged here), so the
    contraction pair reaches ruling 131 (A)'s two of three with the copy: the approved words when the second recogniser
    reads them, the run's reading only at an edge >= 3, all three different still holds.
(c) lock_precheck.DECODER fc204e4a4385 (full sha in the comment). RULES unchanged (ruling 142 covers it). The post_live
    fallback and its offset guard are the integrator's acquisition code (not in my files).

TESTS (test_lock_precheck TestRuling142, 2 new; the decoder pins updated): the contraction both ways round, and what is
not one (a digit, 'was', another word); feb4b72f's shape decided two of three both ways and held when all three differ;
canon_spans reads '24' '-7,' as '24' '7' and keeps 'fell' '-5%' a sign. Mutations: 6 of 6 killed.

PLEASE CHECK: (1) can the contraction rule exempt anything the ruling did not (a number, another verb, another word)?
(2) does the canon_spans change ever drop a real sign? (3) the decoder and the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
