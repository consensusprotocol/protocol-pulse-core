# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1937
# Branch: pp-selectid
# Generated: 2026-11-15 19:37 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1937/C1_STEP.diff (49 lines)
```
   1 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
   2 | index 080be63..138301d 100644
   3 | --- a/tests/package/proof_ly.py
   4 | +++ b/tests/package/proof_ly.py
   5 | @@ -17,8 +17,8 @@ is out too. What is left:
   6 |  - the second recogniser is ElevenLabs scribe_v1.
   7 |  CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
   8 |  
   9 | -SPEND: a ledger of this order's own (tests/package/proof/SPEND_B3.json since ruling 108; SPEND_LY.json is the closed
  10 | -$20 order's) holds the price-table estimate beside the
  11 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_B4.json for BATCH 4, the orchestrator's 19:40 ET Nov 15
  12 | +order; SPEND_B3.json is batch 3's and SPEND_LY.json the $20 order's, both closed) holds the price-table estimate beside the
  13 |  vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
  14 |  its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
  15 |  (Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.
  16 | @@ -47,9 +47,10 @@ import speakers as SP  # noqa: E402
  17 |  
  18 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
  19 |  OUT = os.path.join(HERE, "proof")
  20 | -SPEND = os.path.join(OUT, "SPEND_B3.json")   # RULING 108 (orchestrator 21:20 ET Nov 14): BATCH 3 (to 21:10 ET Nov 15)
  21 | -#   keeps its own ledger. The $20 order's SPEND_LY.json is CLOSED at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
  22 | -LY_LIMIT_USD = 4.50                # RULING 108: builds + sealing's share of batch 3's $8.00 ALL-IN cap (audits $2.50,
  23 | +SPEND = os.path.join(OUT, "SPEND_B4.json")   # BATCH 4 (orchestrator 19:40 ET Nov 15: 21:10 ET Nov 15 to 21:10 ET Nov
  24 | +#   16, batch 3's terms) keeps its own ledger, as batch 3 did (ruling 108). CLOSED: batch 3's SPEND_B3.json at 21:10 ET
  25 | +#   Nov 15; the $20 order's SPEND_LY.json at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
  26 | +LY_LIMIT_USD = 4.50                # RULING 108, batch 4 on its terms: builds + sealing's share of the $8.00 cap (audits $2.50,
  27 |  LY_LIMIT_BASIS = "reported"        # mining and checks $1.00), VENDOR-REPORTED; an abandoned call at the model's own
  28 |  LY_STOP_USD = 4.00                 # rate (ruling 107 Q1). No build starts at or over $4.00 (a build runs $0.15-0.50, so
  29 |                                     # none ends over $4.50: each paid call still RESERVES its upper bound while in
  30 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
  31 | index eccb74d..0889c09 100644
  32 | --- a/tests/package/test_ruling_102.py
  33 | +++ b/tests/package/test_ruling_102.py
  34 | @@ -306,11 +306,12 @@ class TestOnThePinAndOnState(unittest.TestCase):
  35 |  
  36 |      def test_no_build_starts_at_the_stop_and_one_starts_below(self):
  37 |          """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 108
  38 | -        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share."""
  39 | +        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share; batch 4 (19:40 Nov 15) on the same terms."""
  40 |          self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (4.00, 4.50))
  41 |          self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
  42 |          self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)   # one build's headroom (C1, glm)
  43 | -        self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))          # never the closed $20 ledger again
  44 | +        self.assertEqual(os.path.basename(PLG.PL.SPEND), "SPEND_B4.json")   # batch 4's own; never a closed ledger
  45 | +        self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))
  46 |          self.assertIsNone(PLG.start_refused(3.99))
  47 |          why = PLG.start_refused(4.0)
  48 |          self.assertIn("at or over the $4.00 stop: no build starts", why)
  49 | 
```

---

pp-selectid: BATCH 4's own build ledger (orchestrator 19:40 ET Nov 15). Files: tests/package/proof_ly.py (SPEND and
its comments), tests/package/test_ruling_102.py.

THE ORDER, verbatim: "batch 3 closes at 21:10 ET ... BATCH 4 starts 21:10 ET Nov 15 and runs to 21:10 ET Nov 16 on
the same terms: all-in cap $8.00 (tell at $6, alarm at $7.50), every ruling to 117 in force, the calibrated bars, the
join search, the 30-minute fallback poll."

THE CHANGE: proof_ly.SPEND, the ledger the ledger build's router charges (tests/package/proof_ledger.py:221,
spend_path=PL.SPEND, the only code that reads it), moves from SPEND_B3.json to SPEND_B4.json, exactly as ruling 108
moved it from SPEND_LY.json to SPEND_B3.json for batch 3 (audit 20261114_2114). LY_LIMIT_USD 4.50, LY_STOP_USD 4.00,
LY_LIMIT_BASIS "reported" and RESERVE_WAIT_S are unchanged ("the same terms"). It LANDS AT 21:10 ET, when batch 3
closes, so no build that starts before then charges batch 4. A missing SPEND_B4.json starts at $0 (the Router's own
ledger creation, unchanged). The batch-4 STATE figure is kept outside this code, as batch 3's was.

UNCHANGED GUARDS (not in the diff): proof_ledger.start_refused (no build starts at or over LY_STOP_USD); the Router's
limit (limit_usd=PL.LY_LIMIT_USD, limit_basis=PL.LY_LIMIT_BASIS, tests/package/proof_ledger.py:221-227); ruling 41's
per-build cap; ruling 107 (1)'s fingerprint.

TESTS: test_ruling_102 test_no_build_starts_at_the_stop_and_one_starts_below: the ledger is SPEND_B4.json and never a
closed one (SPEND_LY.json, SPEND_B3.json); the stop, the limit and its basis unchanged. All suite files pass.

PLEASE CHECK: (1) that nothing but the ledger's file name moves; (2) that no other code path still writes
SPEND_B3.json; (3) the test.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
