# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0614
# Branch: pp-selectid
# Generated: 2026-11-14 06:14 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0614/C1_STEP.diff (121 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 2991c47..c5466cc 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -324,7 +324,6 @@
   6 |     "context_verdict": [
   7 |      "heimdall:z-ai/glm-5.3-flash",
   8 |      "heimdall:deepseek/deepseek-v4.1-flash",
   9 | -    "heimdall:qwen/qwen3.8-27b",
  10 |      "xai:grok-4.20-0309-reasoning"
  11 |     ],
  12 |     "coherence_verdict": [
  13 | @@ -356,12 +355,10 @@
  14 |     "context_verdict:step_a_first": [
  15 |      "heimdall:z-ai/glm-5.3-flash",
  16 |      "heimdall:deepseek/deepseek-v4.1-flash",
  17 | -    "heimdall:qwen/qwen3.8-27b",
  18 |      "xai:grok-4.20-0309-reasoning"
  19 |     ],
  20 |     "context_verdict:step_a_second": [
  21 |      "xai:grok-4.20-0309-reasoning",
  22 | -    "heimdall:qwen/qwen3.8-27b",
  23 |      "heimdall:z-ai/glm-5.3-flash",
  24 |      "heimdall:deepseek/deepseek-v4.1-flash"
  25 |     ],
  26 | @@ -378,12 +375,12 @@
  27 |     ],
  28 |     "coherence_verdict:clips_alone": [
  29 |      "xai:grok-4.20-0309-reasoning",
  30 | -    "heimdall:qwen/qwen3.8-27b",
  31 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  32 | +    "google:gemini-2.5-pro"
  33 |     ],
  34 |     "coherence_verdict:coherence": [
  35 |      "xai:grok-4.20-0309-reasoning",
  36 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  37 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  38 | +    "heimdall:z-ai/glm-5.3-flash"
  39 |     ]
  40 |    },
  41 |    "plan_b": {
  42 | @@ -461,6 +458,7 @@
  43 |     ]
  44 |    },
  45 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  46 | -  "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement."
  47 | +  "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  48 | +  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and ruling 96's deepseek (94 % on the replay, one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. Every other list is ruling 96's, unchanged."
  49 |   }
  50 |  }
  51 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
  52 | index b88bad7..3c96174 100644
  53 | --- a/tests/package/test_ledger_build.py
  54 | +++ b/tests/package/test_ledger_build.py
  55 | @@ -829,10 +829,11 @@ class TestDriverRefuses(unittest.TestCase):
  56 |  
  57 |  class TestRuling85NoXai(unittest.TestCase):
  58 |      """RULINGS 85 + 88 (22:15 Nov 13), on the real config and the real Router's skip rule (no model is called):
  59 | -    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type but
  60 | -    one still has a Heimdall family off the writer, and step A's two verdicts come from two families. The one gap:
  61 | -    coherence keeps Grok with deepseek alone behind it (88 (d): glm out; (e): qwen never decides it), so when deepseek
  62 | -    writes and xAI is down, coherence has no family and the package fails closed."""
  63 | +    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type
  64 | +    still has a family off the writer, and step A's two verdicts come from two families. The gap ruling 96 left
  65 | +    (coherence had Grok with deepseek alone behind it, so with deepseek writing and xAI down it had no family) is
  66 | +    closed by the orchestrator's 06:12 rulings: glm is coherence's LAST fallback; clips-alone has NO Heimdall fallback
  67 | +    (Grok, then Plan B's other outside family, Gemini, else it fails closed); qwen is struck from step A."""
  68 |  
  69 |      @staticmethod
  70 |      def pl():
  71 | @@ -850,19 +851,23 @@ class TestRuling85NoXai(unittest.TestCase):
  72 |          return None
  73 |  
  74 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
  75 | -        """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure."""
  76 | +        """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
  77 | +        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
  78 |          PL = self.pl()
  79 |          X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
  80 |                         "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
  81 | +        GEM = "google:gemini-2.5-pro"
  82 |          ch = PL.chains("heimdall_first")
  83 |          self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
  84 |          self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
  85 | -        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, Q, X])        # 96: glm first (speed), deepseek
  86 | +        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
  87 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, G, DS])          # (c) Grok confirms; 06:12 (2)
  88 | +        self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
  89 | +        self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
  90 |          self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
  91 | -        self.assertEqual(ch["context_verdict:step_a_second"][0], X)               # (c): Grok confirms
  92 |          self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
  93 | -        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # (d) / (e): no glm, no qwen
  94 | -        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, Q, DS])         # (d): no glm
  95 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
  96 | +        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
  97 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
  98 |          self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
  99 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
 100 | @@ -876,12 +881,17 @@ class TestRuling85NoXai(unittest.TestCase):
 101 |          self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
 102 |                                 ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
 103 |                                 ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
 104 | -                               ("coherence_verdict", "clips_alone"): Q,
 105 | -                               ("coherence_verdict", "coherence"): None})          # THE GAP (fails closed)
 106 | +                               ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
 107 | +                               ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
 108 | +        r.down[GEM] = "Gemini answers nothing (the test)"
 109 | +        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="clips_alone"))   # closed
 110 | +        r.down[G] = "glm answers nothing (the test)"
 111 | +        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="coherence"))     # closed
 112 | +        del r.down[G], r.down[GEM]
 113 |          first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
 114 |          fb = r.backends[first]
 115 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 116 | -        self.assertEqual((first, second), (G, Q))                                  # two Heimdall families, Grok down
 117 | +        self.assertEqual((first, second), (G, DS))                                 # two Heimdall families, Grok down
 118 |          r.down.clear()
 119 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 120 |          self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
 121 | 
```

---

You are auditing a SMALL configuration change on branch pp-selectid (Protocol Pulse's moments-first video builder).
Only state what you can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete
input that breaks it.

BACKGROUND (static):
- Every model verdict goes through providers.Router. Under routing "heimdall_first" (the routing every build uses),
  each verdict type has an ordered list in pipeline/model_providers.json routing.heimdall_first ("<role>" or
  "<role>:<kind>"); the router tries the list in order, skipping a back-end that is down or whose vendor / model family
  wrote the text being judged (law L-x). proof_ly.chains() drops the frozen legs (local:, anthropic:, openai:,
  openai_stt:). An out-of-contract answer moves on to the next model (providers.call_parsed); when the list is spent
  there is no verdict, which never passes (fail closed). Writers are Heimdall deepseek -> qwen -> Grok.
- Ruling 96 (01:40 ET Nov 14) set the lists from a replay of 884 verdicts against Grok (Grok's self-agreement: step A
  85 %, clips-alone 79 %). It left a gap: coherence was Grok -> deepseek, so with xAI down and deepseek writing,
  coherence had no family.

THE ORCHESTRATOR'S RULINGS (06:12 ET Nov 14), verbatim:
(1) "THE COHERENCE GAP: glm IS coherence's last fallback, after Grok (94 % on the replay, one anchor failure in the
    whole table); an out-of-contract glm answer is no verdict; after glm, fail closed. Clips-alone has NO Heimdall
    fallback (52-62 %): with Grok down it goes to Plan B's other outside family, else fails closed."
(2) "QWEN ON STEP A: STRUCK. Step A's Heimdall filter is glm -> deepseek; qwen (mostly errors, 9 of 43 refusals let
    through) is out of step A entirely."

THE CHANGE (the diff follows):
- context_verdict:step_a_first  glm -> deepseek -> qwen -> Grok   =>  glm -> deepseek -> Grok
- context_verdict:step_a_second Grok -> qwen -> glm -> deepseek   =>  Grok -> glm -> deepseek
- context_verdict (the role's default; every step-A call names its kind, so no live caller) => glm -> deepseek -> Grok
- coherence_verdict:coherence   Grok -> deepseek                  =>  Grok -> deepseek -> glm
- coherence_verdict:clips_alone Grok -> qwen -> deepseek          =>  Grok -> google:gemini-2.5-pro (Plan B's
  coherence list is Grok -> Gemini -> OpenAI -> Anthropic; OpenAI / Anthropic are frozen legs under heimdall_first)
- a "ruling_0612" note; tests/package/test_ledger_build.py pins every list and, with xAI down and deepseek writing,
  checks coherence -> glm, clips-alone -> Gemini, each failing closed when that last model is down too, and step A's
  two verdicts from two families (glm, then deepseek).

ATTACK:
(a) Does each list match the rulings exactly? Is "glm last, after Grok" right as Grok -> deepseek -> glm (deepseek kept
    second from ruling 96), or should glm replace deepseek?
(b) Is any qwen left on a step-A path (any list a step-A call can reach)?
(c) Clips-alone: is Gemini the right reading of "Plan B's other outside family", and does anything else (the shadow,
    Plan B's own lists, the default "coherence_verdict" list the spotlight's and the medley's value verdicts use) need
    the same change? The value verdicts are deliberately left on the default list (Grok -> deepseek): no replay data.
(d) Can the change make a verdict LOOSER anywhere (a weaker model deciding where a stronger one did)?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".

