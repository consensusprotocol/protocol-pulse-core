# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_0826
# Branch: pp-selectid
# Generated: 2026-11-16 08:26 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_0826/C1_STEP.diff (229 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 57c2e64..061a9f0 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -203,7 +203,6 @@
   6 |      "xai:grok-4.20-0309-reasoning",
   7 |      "anthropic:claude-opus-5-5",
   8 |      "heimdall:deepseek/deepseek-v4.1-flash",
   9 | -    "heimdall:z-ai/glm-5.3-flash",
  10 |      "heimdall:qwen/qwen3.8-27b",
  11 |      "local:gemma3:27b"
  12 |     ],
  13 | @@ -214,7 +213,6 @@
  14 |      "xai:grok-4.20-0309-reasoning",
  15 |      "anthropic:claude-opus-5-5",
  16 |      "heimdall:deepseek/deepseek-v4.1-flash",
  17 | -    "heimdall:z-ai/glm-5.3-flash",
  18 |      "heimdall:qwen/qwen3.8-27b",
  19 |      "local:gemma3:27b"
  20 |     ],
  21 | @@ -226,7 +224,6 @@
  22 |      "anthropic:claude-opus-5-5",
  23 |      "xai:grok-4.20-0309-reasoning",
  24 |      "heimdall:deepseek/deepseek-v4.1-flash",
  25 | -    "heimdall:z-ai/glm-5.3-flash",
  26 |      "heimdall:qwen/qwen3.8-27b",
  27 |      "local:gemma3:27b"
  28 |     ],
  29 | @@ -263,7 +260,6 @@
  30 |      "xai:grok-4.20-0309-reasoning",
  31 |      "anthropic:claude-opus-5-5",
  32 |      "heimdall:deepseek/deepseek-v4.1-flash",
  33 | -    "heimdall:z-ai/glm-5.3-flash",
  34 |      "heimdall:qwen/qwen3.8-27b"
  35 |     ],
  36 |     "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
  37 | @@ -273,7 +269,6 @@
  38 |      "anthropic:claude-opus-5-5",
  39 |      "xai:grok-4.20-0309-reasoning",
  40 |      "heimdall:deepseek/deepseek-v4.1-flash",
  41 | -    "heimdall:z-ai/glm-5.3-flash",
  42 |      "heimdall:qwen/qwen3.8-27b",
  43 |      "local:gemma3:27b"
  44 |     ],
  45 | @@ -284,7 +279,6 @@
  46 |      "xai:grok-4.20-0309-reasoning",
  47 |      "anthropic:claude-opus-5-5",
  48 |      "heimdall:deepseek/deepseek-v4.1-flash",
  49 | -    "heimdall:z-ai/glm-5.3-flash",
  50 |      "heimdall:qwen/qwen3.8-27b",
  51 |      "local:gemma3:27b"
  52 |     ],
  53 | @@ -322,7 +316,6 @@
  54 |    },
  55 |    "heimdall_first": {
  56 |     "context_verdict": [
  57 | -    "heimdall:z-ai/glm-5.3-flash",
  58 |      "heimdall:deepseek/deepseek-v4.1-flash",
  59 |      "xai:grok-4.20-0309-reasoning"
  60 |     ],
  61 | @@ -331,42 +324,35 @@
  62 |      "heimdall:deepseek/deepseek-v4.1-flash"
  63 |     ],
  64 |     "fidelity_verdict": [
  65 | -    "heimdall:z-ai/glm-5.3-flash",
  66 |      "heimdall:qwen/qwen3.8-27b",
  67 |      "xai:grok-4.20-0309-reasoning"
  68 |     ],
  69 |     "exclusion_verdict": [
  70 | -    "heimdall:z-ai/glm-5.3-flash",
  71 |      "heimdall:deepseek/deepseek-v4.1-flash",
  72 |      "xai:grok-4.20-0309-reasoning"
  73 |     ],
  74 |     "speaker_verdict": [
  75 |      "xai:grok-4.20-0309-reasoning",
  76 |      "heimdall:deepseek/deepseek-v4.1-flash",
  77 | -    "heimdall:z-ai/glm-5.3-flash",
  78 |      "heimdall:qwen/qwen3.8-27b"
  79 |     ],
  80 |     "viewer_takeaway": [
  81 |      "xai:grok-4.20-0309-reasoning",
  82 |      "heimdall:deepseek/deepseek-v4.1-flash",
  83 | -    "heimdall:z-ai/glm-5.3-flash",
  84 |      "heimdall:qwen/qwen3.8-27b"
  85 |     ],
  86 |     "context_verdict:step_a_first": [
  87 | -    "heimdall:z-ai/glm-5.3-flash",
  88 |      "heimdall:deepseek/deepseek-v4.1-flash",
  89 |      "xai:grok-4.20-0309-reasoning"
  90 |     ],
  91 |     "context_verdict:step_a_second": [
  92 |      "xai:grok-4.20-0309-reasoning",
  93 |      "heimdall:deepseek/deepseek-v4.1-flash",
  94 | -    "heimdall:z-ai/glm-5.3-flash",
  95 |      "google:gemini-2.5-pro",
  96 |      "local_judge:gemma3:27b"
  97 |     ],
  98 |     "context_verdict:step_c": [
  99 |      "xai:grok-4.20-0309-reasoning",
 100 | -    "heimdall:z-ai/glm-5.3-flash",
 101 |      "heimdall:deepseek/deepseek-v4.1-flash"
 102 |     ],
 103 |     "coherence_verdict:hook": [
 104 | @@ -381,8 +367,7 @@
 105 |     ],
 106 |     "coherence_verdict:coherence": [
 107 |      "xai:grok-4.20-0309-reasoning",
 108 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 109 | -    "heimdall:z-ai/glm-5.3-flash"
 110 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 111 |     ]
 112 |    },
 113 |    "plan_b": {
 114 | @@ -461,8 +446,7 @@
 115 |     ],
 116 |     "context_verdict:step_c": [
 117 |      "xai:grok-4.20-0309-reasoning",
 118 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 119 | -    "heimdall:z-ai/glm-5.3-flash"
 120 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 121 |     ],
 122 |     "coherence_verdict:hook": [
 123 |      "xai:grok-4.20-0309-reasoning"
 124 | @@ -476,6 +460,7 @@
 125 |    "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
 126 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
 127 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
 128 | -  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
 129 | +  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build.",
 130 | +  "ruling_119": "RULING 119 (3) (orchestrator 08:25 ET Nov 16): glm-5.3-flash is overloaded on the gateway (the Heimdall team confirmed a worker shortage): OUT OF EVERY CHAIN until the orchestrator says; each list closes up, so the next member takes glm's place (no model is added: qwen stays struck from step A by the 06:12 Nov 14 rulings, and ruling 96's other lists are kept as they stand). A held moment moves to the next member at once inside the router (a missed deadline or an open breaker is never a refusal); step A's first screen is now deepseek -> Grok."
 131 |   }
 132 |  }
 133 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 134 | index 091079d..8364c0a 100644
 135 | --- a/tests/package/test_ledger_build.py
 136 | +++ b/tests/package/test_ledger_build.py
 137 | @@ -816,13 +816,14 @@ class TestDriverRefuses(unittest.TestCase):
 138 |                           before)
 139 |  
 140 |      def test_ruling_82_the_context_verdict_chain(self):
 141 | -        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the three Heimdall
 142 | -        models in the ruled order; glm-5.3-flash is a Heimdall back-end of its own family."""
 143 | +        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the Heimdall models in
 144 | +        the ruled order; RULING 119 (08:25 Nov 16): glm out of every chain, the list closes up. glm-5.3-flash stays a
 145 | +        Heimdall back-end of its own family (the orchestrator may put it back)."""
 146 |          sys.path.insert(0, HERE)
 147 |          import proof_ly as PL
 148 |          self.assertEqual(PL.chains()["context_verdict"], ["xai:grok-4.20-0309-reasoning",
 149 |                                                            "heimdall:deepseek/deepseek-v4.1-flash",
 150 | -                                                          "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b"])
 151 | +                                                          "heimdall:qwen/qwen3.8-27b"])
 152 |          with open(os.path.join(REPO, "pipeline", "model_providers.json")) as f:
 153 |              glm = json.load(f)["backends"]["heimdall:z-ai/glm-5.3-flash"]
 154 |          self.assertEqual((glm["vendor"], glm["family"], glm["model"]), ("heimdall", "glm", "z-ai/glm-5.3-flash"))
 155 | @@ -927,26 +928,28 @@ class TestRuling85NoXai(unittest.TestCase):
 156 |  
 157 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
 158 |          """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
 159 | -        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
 160 | +        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A.
 161 | +        RULING 119 (08:25 ET Nov 16): glm out of EVERY chain (overloaded), each list closing up; nothing is added."""
 162 |          PL = self.pl()
 163 |          X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
 164 |                         "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
 165 |          GEM = "google:gemini-2.5-pro"
 166 |          ch = PL.chains("heimdall_first")
 167 | -        self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
 168 | -        self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
 169 | -        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
 170 | -        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, G, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 171 | -        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
 172 | -        self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
 173 | +        self.assertEqual(ch["fidelity_verdict"], [Q, X])                          # 96 without glm: qwen -> Grok
 174 | +        self.assertEqual(ch["exclusion_verdict"], [DS, X])                         # 96 without glm: deepseek -> Grok
 175 | +        self.assertEqual(ch["context_verdict:step_a_first"], [DS, X])              # 06:12 (2) without glm; no qwen
 176 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 177 | +        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, Gemini, the local judge (ruling 87's last resort)
 178 | +        self.assertEqual(ch["context_verdict"], [DS, X])                           # the role's default: no qwen either
 179 | +        self.assertNotIn(G, [b for v in list(ch.values()) + list(PL.chains("today").values()) for b in v])   # 119
 180 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
 181 |          self.assertEqual(ch["coherence_verdict:hook"], [X])                        # RULING 115 (amends 88 (b) / 96 for
 182 |          #   the hook): Grok ALONE, the rater the calibrated floors are measured on (qwen in shadow, never deciding)
 183 | -        self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
 184 | -        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
 185 | +        self.assertEqual(ch["context_verdict:step_c"], [X, DS])                    # (b) / (e): no qwen; 119: no glm
 186 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # 06:12 (1)'s last fallback glm: out
 187 |          self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
 188 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
 189 | -        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
 190 | +        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS]))
 191 |          self.assertEqual((today["coherence_verdict:hook"], PL.plan_b_chains()["coherence_verdict:hook"]), ([X], [X]))
 192 |          #   RULING 115: the hook is Grok's alone in every routing (no uncalibrated rating is ever cached as a hook's)
 193 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
 194 | @@ -957,24 +960,22 @@ class TestRuling85NoXai(unittest.TestCase):
 195 |              ("fidelity_verdict", None), ("exclusion_verdict", None), ("speaker_verdict", None),
 196 |              ("viewer_takeaway", None), ("context_verdict", "step_c"), ("coherence_verdict", "hook"),
 197 |              ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
 198 | -        self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
 199 | -                               ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
 200 | -                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): None,   # ruling 115:
 201 | -                               #   no other model decides a hook while Grok is out (no rating = no hook, law L-m)
 202 | +        self.assertEqual(got, {("fidelity_verdict", None): Q, ("exclusion_verdict", None): None,   # RULING 119: glm
 203 | +                               ("speaker_verdict", None): Q, ("viewer_takeaway", None): Q,         # out, deepseek
 204 | +                               ("context_verdict", "step_c"): None, ("coherence_verdict", "hook"): None,   # writes,
 205 | +                               #   Grok is down: no leg is a fail-closed no verdict (law L-m), never another model
 206 |                                 ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
 207 | -                               ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
 208 | +                               ("coherence_verdict", "coherence"): None})         # glm, its last fallback, is out
 209 |          r.down[GEM] = "Gemini answers nothing (the test)"
 210 |          self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="clips_alone"))   # closed
 211 | -        r.down[G] = "glm answers nothing (the test)"
 212 | -        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="coherence"))     # closed
 213 | -        del r.down[G], r.down[GEM]
 214 | +        del r.down[GEM]
 215 | +        self.assertIsNone(self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first"))   # held
 216 | +        #   (ruling 102): deepseek writes and Grok is down, so step A's first screen has no leg for THIS build
 217 | +        r.down.clear()
 218 |          first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
 219 |          fb = r.backends[first]
 220 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 221 | -        self.assertEqual((first, second), (G, DS))                                 # two Heimdall families, Grok down
 222 | -        r.down.clear()
 223 | -        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 224 | -        self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
 225 | +        self.assertEqual((first, second), (X, DS))                                 # Grok's first, deepseek's off it
 226 |  
 227 |  if __name__ == "__main__":
 228 |      unittest.main()
 229 | 
```

---

pp-selectid: RULING 119 (3) (orchestrator 08:25 ET Nov 16): glm out of every chain. Files: pipeline/model_providers.json
(the chains; one note), tests/package/test_ledger_build.py (the two tests that pin the lists).

THE ORDER, verbatim: "(3) glm-5.3-flash is overloaded on the gateway (the Heimdall team confirmed a worker shortage) and held
a moment at step A's first screen twice this morning: take glm out of every chain until I say; the next healthy member takes
its place. A held moment is retried on the next member at once, not after the breaker."

THE CHANGE: heimdall:z-ai/glm-5.3-flash is removed from EVERY chain in the config (16 lists: the roles' default chains and
the heimdall_first / today routing lists); each list closes up, so the next member takes glm's place. NOTHING IS ADDED:
qwen stays struck from step A (the orchestrator's 06:12 Nov 14 rulings: "QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43
refusals let through)"), and ruling 96's other lists stand as they are without glm. The back-end's own definition stays
(the orchestrator may put it back). Lists after the change (heimdall_first): step A's first screen deepseek -> Grok; step
A's second Grok -> deepseek -> Gemini -> the local judge; context_verdict deepseek -> Grok; fidelity qwen -> Grok;
exclusion deepseek -> Grok; speaker and viewer_takeaway Grok -> deepseek -> qwen; step C Grok -> deepseek; coherence Grok
-> deepseek; today's step C Grok -> deepseek.

"RETRIED ON THE NEXT MEMBER AT ONCE": unchanged code already does it: Router.call moves to the chain's next member at once
when one misses its deadline, is breaker-open (Router._skip / breaker_open) or answers out of contract
(providers.call_parsed); ruling 102 holds a moment only when no member answers. The moment held this morning
(c03abcbc, builds 39-40) was held because glm missed its deadline, deepseek is the writer's family (skipped by L-x), and
Grok's step-A upper bound ($0.83) does not fit the day's dollar left (ruling 118's cap: SpendLimit, recorded in its
package). After this change, while deepseek writes and the day's dollar is short, step A's first screen still holds new
moments (deepseek skipped, Grok capped): that is stated, not hidden; the free panel (ruling 118) is the fix for it.

UNCHANGED GUARDS (not in the diff): providers.Router._skip (pipeline/providers.py, "def _skip": the writer's vendor /
family); Router.call's failover; package.prescreen's ruling-102 hold (pipeline/package.py "def held_why" / "def
is_held"); ruling 118's cap (Router._reserve).

TESTS: test_ledger_build test_ruling_82_the_context_verdict_chain (the 'today' context chain Grok -> deepseek -> qwen) and
test_ruling_96s_lists_and_xai_answering_nothing (every heimdall_first and today list as above; glm in NO list; with Grok down
and deepseek writing, the router's own picks: fidelity, speaker, takeaway -> qwen; exclusion, step C, the hook, coherence ->
no leg (fail closed); clips-alone -> Gemini; step A's first screen -> no leg (held); with Grok up: Grok first, deepseek
second off it). Mutations C1-C3 (glm back in step A's first screen; qwen put in glm's place in step A; glm back first for
fidelity) after a control run. All suite files.

PLEASE CHECK: (1) that glm is in no chain and nothing was added; (2) that no list breaks a standing ruling (06:12: no qwen
in step A; 96; 102; 115: the hook Grok alone); (3) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
