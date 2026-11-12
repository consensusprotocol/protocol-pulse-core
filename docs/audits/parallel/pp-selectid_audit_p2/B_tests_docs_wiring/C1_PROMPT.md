# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-p2
# Branch: pp-selectid
# Generated: 2026-11-12 04:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_p2/B_tests_docs_wiring/STEP.diff (1574 lines)
```
   1 | diff --git a/docs/audits/MOMENTS_FIRST_DESIGN.md b/docs/audits/MOMENTS_FIRST_DESIGN.md
   2 | new file mode 100644
   3 | index 00000000..9b2e35a3
   4 | --- /dev/null
   5 | +++ b/docs/audits/MOMENTS_FIRST_DESIGN.md
   6 | @@ -0,0 +1,245 @@
   7 | +# MOMENTS FIRST, THEN PACKAGE — design (pp-selectid phase 2, 2026-11-12)
   8 | +
   9 | +Orders and laws:
  10 | +- Orchestrator phase-2 order (01:55 ET Nov 12) and its addition (trend brief; "vo check needs to be real 100%").
  11 | +- Orchestrator notes 02:00 (model roles), 02:30 (laws L-s..L-w), 02:35 (PBX decisions), 02:45 (law L-x) and 03:00
  12 | +  (exam by pipeline_pp_tests; yield against the oracle).
  13 | +- Laws L-n, L-o (amended), L-p, L-q, L-r (PIPELINE_LAWS.md).
  14 | +
  15 | +New modules only:
  16 | +- pipeline/providers.py and model_providers.json;
  17 | +- pipeline/trend_brief.py, moments.py, package.py, vo_fidelity.py, context_integrity.py;
  18 | +- pipeline/moments_gate_adapter.py (the exam adapter).
  19 | +
  20 | +No existing pipeline file is edited. The wiring is an exact patch in docs/audits/parallel/pp-selectid_REQUESTS.md (R7).
  21 | +
  22 | +## 1. The cycle
  23 | +
  24 | +```
  25 | +ingest (pipeline_pp_ingest: new uploads -> store -> word pass)            -> moment ledger (append-only, pp.moment/1)
  26 | +trend_brief: local_baseline (free) + one live-search call (SHADOW, weight 0)
  27 | +moments.mine: pre-filter (code) -> one batched mining pass by id (role "mine") -> eligibility per moment -> rank (code)
  28 | +package.build: usable (code) -> candidate sets + runtime arithmetic (code) -> writer (role "angle_write")
  29 | +               -> vo_fidelity (code + blind verdict) -> context_integrity (blind steps A, B, C + code)
  30 | +               -> regenerate once / plain VO / drop a moment and repack
  31 | +               -> pp.package/1
  32 | +integrator: word pass for the segments (if a moment came from captions) -> sentence lock -> render -> gates ->
  33 | +            release authorisation over BOTH files + the title + caption (L-t) -> Telegram REVIEW ONLY (first one)
  34 | +```
  35 | +
  36 | +## 2. Provider interface (law L-x)
  37 | +
  38 | +- Every role calls `providers.Router.call(role, prompt, ...)`. The chain of back-ends per role lives only in
  39 | +  pipeline/model_providers.json.
  40 | +- Back-ends:
  41 | +  - local: gemma3:27b through story_semantics.LocalLLM; only with a started LocalLLM under the GPU0 lease, law L-r;
  42 | +  - OpenAI chat/completions;
  43 | +  - Anthropic Messages (streaming);
  44 | +  - xAI chat/completions at temperature 0 with the attempt's seed;
  45 | +  - xAI Responses with x_search / web_search (the trend brief);
  46 | +  - Heimdall (OpenAI-compatible).
  47 | +- A back-end that cannot answer (credit, 401 / 402 / 403, 429 or 5xx after backoff, transport, no lease) raises
  48 | +  Unavailable. The chain moves on and skips it for the rest of the run. A role whose whole chain fails raises
  49 | +  ProviderError: a failed role, never a pass.
  50 | +- Verdict roles take `avoid_vendor` = the writer's vendor, so the judge is never the writer's vendor (L-s; note 02:00).
  51 | +- Every exchange is recorded by (role, back-end, prompt, max_tokens, seed, system) and replayable offline. The Reply
  52 | +  names the back-end that produced the text, and every artefact keeps it.
  53 | +- Spend is priced per back-end (upper-bound USD per 1M tokens in the config) into one ledger with a guard.
  54 | +- Heimdall's GET /credits feeds the 90% tripwire: a NOTIFY, never a halt (PBX 02:45).
  55 | +- Initial order (decided 02:44, NOT yet measured):
  56 | +  - mine, story and check: local first;
  57 | +  - angle_write: a frontier model first (L-w 1, PBX 02:35);
  58 | +  - verdict roles: a non-writer vendor first;
  59 | +  - every role: >= 2 back-ends.
  60 | +- The blind A/B per role (tests/providers/ab_roles.py) re-decides the order. The integrator runs the local legs.
  61 | +
  62 | +## 3. Mining (moments.py)
  63 | +
  64 | +- Pre-filter (code): sources in the window (new since the last cycle plus a recent window); not opted out
  65 | +  (pipeline/optout.json, PBX 02:35); eligible as a source. Rows are punctuated, injection-free, never an ad read, and
  66 | +  within one sentence of a Bitcoin mention. Rows go round-robin across videos, on-screen-capable videos first, in
  67 | +  context-budget tables.
  68 | +- One batched pass: the model answers ids only, `{"moments": [{"range", "scores": 7 axes 0-5, "names_person",
  69 | +  "risk", "topics", "reason"}]}`.
  70 | +  - The reply contract is strict and never repaired (L-l): exact keys, integer scores, closed enums (risk: L-u's
  71 | +    list; topics: trend_brief.TAXONOMY), ranges of existing consecutive ids of one video, no overlap. Anything else is
  72 | +    re-asked with the reason.
  73 | +  - Each moment is then judged by eligibility on its own: a moment is its own statement, and L-s judges what it
  74 | +    leaves out. A failure is recorded on the moment and never edited.
  75 | +- Ranking (code, L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone, minus 2 x
  76 | +  contempt_outrage, minus soft-risk penalties, plus a trend weight that is 0 in SHADOW. A named figure is a fact,
  77 | +  never an axis. Hard risks never rank. Ties go by moment_id.
  78 | +- Durations come from word timing only. Caption timing is a flagged estimate (`duration_estimate_s`), never used for
  79 | +  the runtime.
  80 | +- The `reason` is forensic only.
  81 | +
  82 | +## 4. Packaging (package.py)
  83 | +
  84 | +- usable (code):
  85 | +  - on screen eligible (L-e);
  86 | +  - no hard exclusion (L-u);
  87 | +  - not delivered in 24 h (L-p novelty);
  88 | +  - not opted out;
  89 | +  - <= 20 s per source video (L-u);
  90 | +  - time-sensitive words only from a source <= 24 h old (L-v 3);
  91 | +  - no measured speaker change inside (L-v 1).
  92 | +- Candidate sets (code):
  93 | +  - a hook and 2-3 clips, every segment from a DIFFERENT channel (L-u: one clip per channel per video);
  94 | +  - segments + VO + fixed seconds inside 60-70 s, with the VO as the slack (L-w 1):
  95 | +    - fixed seconds: FIXED_S = TAIL_S - an 18-word sign-off at WPS, about 7.4 s;
  96 | +    - WPS = 2.6 words a second, an ASSUMPTION until a render measures it;
  97 | +  - at most one price prediction (L-u);
  98 | +  - scored by the moments' rank scores, topic diversity and the hook's first-2-seconds score. Sets are distinct.
  99 | +- Writer (role angle_write):
 100 | +  - picks one set; type `story` (every segment states one development: L-w 3's preferred type) or `moments`;
 101 | +  - writes the order (hook first), the angle, the intro and bridges within code-computed word budgets, ONE title
 102 | +    (<= 70) and ONE caption (<= 220) (L-t); every line cites moment ids;
 103 | +  - the reply contract is strict;
 104 | +  - the sign-off is code: the credit set, hook first (L-a).
 105 | +- Gates: VO fidelity, then context integrity. Both are hard. The runtime estimate must lie in 60-70 s.
 106 | +- On failure:
 107 | +  - a VO failure with context passing: regenerate once with the violations, then the plain factual VO (L-w 2: "Here's
 108 | +    <show> on <topic>." / "Next, <show> on <topic>.", our taxonomy labels, the credit list);
 109 | +  - a context or exclusion failure: drop the moment and repack from the next set.
 110 | +  - The package is never shipped failing.
 111 | +
 112 | +## 4b. Angle first (orchestrator review 03:40: "select by angle, not by score")
 113 | +
 114 | +The first package (03:25) passed every safety gate and failed the product: four unrelated quotes joined by
 115 | +"Next, <show> on <topic>.", a title that misled about the present, and a clip that repeated the title. package.build is
 116 | +now angle first:
 117 | +
 118 | +1. **Step A** screens each candidate moment's own context once (package-independent). Only cleared moments go on.
 119 | +2. **ANGLES** (role angle_write, frontier):
 120 | +   - up to 5 angles, each ONE sentence a viewer could repeat;
 121 | +   - each backed by 4-8 cleared moments from >= 3 channels (L-u: one clip per channel);
 122 | +   - a hook chosen to grab the first two seconds AND set up the angle.
 123 | +   The contract is strict.
 124 | +3. **Line-up per angle** (code): the hook, then 2-3 clips from distinct channels, in the proposer's order, inside the
 125 | +   runtime arithmetic. A clip under 8 s plays only last, as the punchline.
 126 | +4. **Writer** (role angle_write): the VO makes the angle's point ONLY with what the cited clips state.
 127 | +   - On a fidelity / DUPLICATE / PRICE_NOW reject, it rewrites up to 3 times, given the exact rejected claims and
 128 | +     reasons.
 129 | +   - Then the plain VO is used, labelled "plain VO" and ranked below every written VO.
 130 | +5. **Integrity gates** (hard): VO fidelity, DUPLICATE, PRICE_NOW, context integrity B / C, runtime.
 131 | +6. **COHERENCE** (role coherence_verdict, blind, never the writer's vendor) gives the through-line in one sentence, each
 132 | +   clip 1-5 on advancing it, and the VO's point 1-5. Below 4, or no through-line, moves to the next angle. This is a
 133 | +   quality gate, separate from integrity.
 134 | +7. **Law L-v 2** (pipeline/transcript_truth.py): a second, independent recognition pass on the SOURCE audio of every
 135 | +   segment with a number or negation, plus diarisation. A disagreement or a speaker change drops the moment and
 136 | +   rebuilds the line-up.
 137 | +8. Packages are ranked by coherence (the lowest rating first, then the sum). The top package goes first, then up to 2
 138 | +   alternatives on other angles.
 139 | +
 140 | +New deterministic rules:
 141 | +- **PRICE_NOW** (vo_fidelity.price_now with package.current_levels): a headline line (intro, title, caption) stating a
 142 | +  price level or move must read as history, or match a level this universe states as current (present-tense
 143 | +  sentences from sources <= 24 h old). The case was sent to pipeline_pp_tests (REQUESTS R8).
 144 | +- **DUPLICATE** (package.duplicates): the VO line right before a clip, and the title, never carry a run of >= 5 of
 145 | +  that clip's canonical tokens.
 146 | +
 147 | +Measured false rejects, fixed (no rule loosened):
 148 | +- NAME read sentence-initial capitals and Title Case titles as names. It now skips them; real names are caught by
 149 | +  mid-sentence capitals, ATTRIBUTION and the verdict. A 9-case check passes both ways.
 150 | +- NUMBER read 'one thing' as 1. Number words <= 10 without a unit are counts.
 151 | +- The verdict could not support a cross-clip point. A claim may now cite several segments, each with verbatim words.
 152 | +- Production facts (the credited channels, links below, the show, the date) are a citable "manifest" segment.
 153 | +- Step A read a cleft "it" and a generic "we" as outside referents (NOTE-PS12).
 154 | +
 155 | +## 5. VO fidelity (vo_fidelity.py): "real 100%"
 156 | +
 157 | +(a) Deterministic, on every VO line, the title and the caption, through canon (L-k):
 158 | +
 159 | +| rule | what it checks |
 160 | +|---|---|
 161 | +| NEEDS_SOURCE | a line with a fact cites a segment |
 162 | +| NUMBER | value and unit, in the cited sentences; in the attributed speaker's own sentences when attributed |
 163 | +| NAME | in a cited segment, or production metadata: credited channels, the show, the date, the package's own counts |
 164 | +| QUOTE | a verbatim run of a cited segment |
 165 | +| ATTRIBUTION | a verb bound to a cited segment of that speaker |
 166 | +| RELATION | agree / answer / rebut / ... only inside one source video |
 167 | +| FRAMING | destroys / slams / exposes / admits / confirms / caught only if the source says it |
 168 | +| IMPERATIVE | no second-person buy / sell / leverage advice |
 169 | +| TIME | today / this week / just hit ... only if a cited segment says it |
 170 | +
 171 | +(b) Blind verdict (role fidelity_verdict, never the writer's vendor):
 172 | +- The judge sees only the segments' words and the lines.
 173 | +- It lists every claim, implied ones included (agreement, sequence, certainty, cause), each yes / no / uncertain with
 174 | +  the supporting words COPIED.
 175 | +- Code decides: every claim "yes" with words that are a verbatim run of that segment; otherwise fail. Uncertain
 176 | +  fails.
 177 | +
 178 | +(c) The exam is pipeline_pp_tests' (03:00: no own must-fail corpus beyond unit fixtures). The gate runs under its
 179 | +harness through pipeline/moments_gate_adapter.py, with recorded replies (the harness has no network).
 180 | +
 181 | +## 6. Context integrity (context_integrity.py, law L-s)
 182 | +
 183 | +- Window per moment: >= 90 s before (back to the question it answers, when one ends within 180 s) to >= 60 s after.
 184 | +  Whole sentences; the moment is marked inside the window.
 185 | +- A (context only; package hidden; context_verdict, never the writer's vendor): speaker change inside; the view (own
 186 | +  sincere / attributed / hypothetical / conditional / sarcastic / question / reading aloud / ad read / joke /
 187 | +  uncertain); every referent with "inside the selection"; conditions with "inside"; retraction; the proposition;
 188 | +  certainty.
 189 | +- B (package only; viewer_takeaway): what a viewer concludes each speaker asserts, certainty, polarity; implied
 190 | +  relations between speakers.
 191 | +- C (context_verdict): A entails B? same polarity? B more certain?
 192 | +- PASS (code) only if all hold:
 193 | +  - no speaker change;
 194 | +  - own sincere;
 195 | +  - every referent and condition inside;
 196 | +  - no retraction;
 197 | +  - certainty known;
 198 | +  - entails, same polarity, not stronger;
 199 | +  - no relation between different source videos, and no "uncertain" anywhere.
 200 | +- Repair is extension by whole sentences or dropping the moment. The VO never carries the missing context.
 201 | +
 202 | +## 7. Trend brief (trend_brief.py)
 203 | +
 204 | +- A closed taxonomy of 18 Bitcoin topics, each with our own label and pattern.
 205 | +- `local_baseline`: the share of partner channels per topic in the last 24 h. Free.
 206 | +- One live-search call per cycle (xAI Responses, x_search + web_search, < 6k out), cached per 4 h cycle.
 207 | +  - The reply is validated into the taxonomy; strict.
 208 | +  - Raw post text never leaves the module or enters a prompt.
 209 | +  - Persons may boost only a moment whose VERIFIED speaker is that person.
 210 | +  - Failure means no boost.
 211 | +- SHADOW: TREND_WEIGHT = 0 until it measurably helps. When enabled, the weight is capped at ~10-15%.
 212 | +- Titles never take trend phrasing (L-t).
 213 | +
 214 | +## 8. Open items (named, not hidden)
 215 | +
 216 | +- **L-v 1 (speaker turns by diarisation) and L-v 2 (a second recognition pass against the SOURCE audio for the
 217 | +  selected sentences).** The module and API exist (OpenAI gpt-4o-transcribe-diarize / gpt-transcribe; this session
 218 | +  is CPU and API only). Until they run on a package, Step A's "speaker change inside" is the only speaker
 219 | +  measurement, and no person is NAMED in VO or title: every attribution is to the show (credited channel).
 220 | +- **The runtime estimate's WPS (2.6) and FIXED_S (7.4 s).** Assumptions until a moments-first render measures them.
 221 | +  The release gates measure the final.
 222 | +- **The trend brief's search call** has never run; it is shadow and not on the critical path.
 223 | +- Sections 9-10 (proof, yield against the oracle, A/B, dollars per video and per day) are filled from the runs.
 224 | +
 225 | +## 9. Measured so far (2026-11-12, saved universes; CPU and API only)
 226 | +
 227 | +- **Mining, gpt-6.1-sol, word-timed sources** (the 10 saved universes): every call accepted at the first attempt.
 228 | +
 229 | +| universe | moments mined | usable on screen |
 230 | +|---|---|---|
 231 | +| fresh_20261106_213852 | 12 | 9 |
 232 | +| fresh_20261107_065702 | 12 | 11 |
 233 | +| fresh_20261107_080503 | 12 | 10 |
 234 | +| fresh_20261110_093150 | 24 | 16 |
 235 | +| fresh_20261111_190259 | 71 | 62 |
 236 | +| fresh_20261111_192645 | 70 | 65 |
 237 | +| fresh_20261111_213954 | 69 | 61 |
 238 | +| fresh_20261112_001448 | 59 | 52 |
 239 | +| fresh_20261112_013452 | 59 | 54 |
 240 | +| fresh_20261112_050611 (tonight) | 62 | 58 |
 241 | +
 242 | +- **Mining A/B** (blind, judged by claude-opus-5-5, tests/providers/ab/mine_fresh_20261112_050611.json):
 243 | +
 244 | +| back-end | calls accepted | latency | spend (upper bound) | blind verdict |
 245 | +|---|---|---|---|---|
 246 | +| gpt-6.1-sol | 6 / 6 | 300.5 s | $2.17 | better |
 247 | +| Heimdall qwen3.8-27b | 5 / 6 | 2,067 s | $1.63 | worse |
 248 | +
 249 | +  local gemma3:27b: the integrator's leg (GPU0 lease).
 250 | +- **Law L-v 2 on tonight's first package**: the second pass (gpt-4o-transcribe-diarize) agreed on every number,
 251 | +  name and negation of all 4 segments, with one speaker inside each.
 252 | diff --git a/docs/audits/parallel/pp-selectid_REQUESTS.md b/docs/audits/parallel/pp-selectid_REQUESTS.md
 253 | index db8f8873..1af6301e 100644
 254 | --- a/docs/audits/parallel/pp-selectid_REQUESTS.md
 255 | +++ b/docs/audits/parallel/pp-selectid_REQUESTS.md
 256 | @@ -585,6 +585,128 @@ block is unchanged. `_run_transcript` is then unused.
 257 |     - no model name in the code.
 258 |     The `select_by_id.Model` interface is the seam, and no change to select_by_id's contract is needed.
 259 |  
 260 | +## R7 MOMENTS-FIRST WIRING (phase 2; laws L-q, L-s..L-x): the package rendered by the SAME factory
 261 | +
 262 | +The route is the existing PINNED entry point. A moments-first package becomes the pinned decision, and every
 263 | +downstream stage stays shared and unchanged: validate (edl_rules, editorial gate, stand-alone, layout), cut, sentence
 264 | +law, voice, prepare, layout, render 16:9 and 9:16, gates, verify, release authorisation.
 265 | +
 266 | +1. **`pipeline/pinned.py` (exact patch below, `git apply --check` clean on c1451047; tests/package/smoke_r7.py: SMOKE
 267 | +   R7 PASS on a temporary patched copy).**
 268 | +   - `build_edl` takes the VO from the pin's `moments_package` (written by pipeline/package_pin.py): the package's
 269 | +     intro, and one bridge after each clip but the last (`after_clip`, the renderer's placement, render_vertical.py
 270 | +     :821-872). There is none between the hook and the first clip.
 271 | +   - The EDL also carries the ONE title and caption (law L-t) and the package's sha256 and gate verdicts.
 272 | +   - It refuses (PinError) a bridge the renderer cannot place, or a package whose VO-fidelity and context-integrity
 273 | +     gates did not BOTH pass.
 274 | +   - A pin without a package is unchanged: no body VO, Editorial Law 2's default.
 275 | +2. **TONIGHT** (orchestrator: "the integrator renders it"): apply item 1, then run run_fresh.py with
 276 | +   `--pinned` and the MOMENTS_PIN.json named at the top of pp-selectid_STATE.md.
 277 | +   - The pin's segments carry `approved_text` = the moments' exact words, and `machine_cuts: true`, so the sentence law
 278 | +     locates them BY TEXT in the acquired transcript, as for a machine PIN today.
 279 | +   - Its `approved_by` names the machine and REVIEW ONLY. No human approved it (law L-q: the first moments-first
 280 | +     delivery is REVIEW ONLY, with its duration deviations listed per L-o).
 281 | +   - stage_review (local gemma) still writes its own independent review of the VO jobs. The editorial gate's Law 2
 282 | +     then needs each body-VO line affirmed: intro = "context", each bridge = "connection".
 283 | +3. **Moments mode in `pipeline/run_fresh.py` (the integrator's code; every step is a function here).**
 284 | +   - A stage "moments":
 285 | +     - `moments.mine(providers.Router(local_llm=<the LocalLLM started under the gpu0 lease>), <the cycle's word
 286 | +       Sources>, ctx, trend_brief.TOPICS, since=<the last cycle's start>)`;
 287 | +     - `package.build(router, mined["moments"], sources, ctx, delivered=<moment ids delivered in 24 h>,
 288 | +       optout=moments.optout_ids())`;
 289 | +     - `package_pin.write_pin(pk, run_name, run.dir)`.
 290 | +   - Then `stage_pinned(run, pin_path)`. "No package" is a HOLD naming `why_none` / `tried`.
 291 | +   - The cycle's word Sources are pipeline_pp_ingest's: the moment ledger plus the store's sentence-ready records,
 292 | +     law L-e.
 293 | +4. **Gates for moments-first runs ONLY** (law L-q CHECK, '01:58').
 294 | +   - The same-event / topic gates are replaced by the package's recorded verdicts: VO fidelity (deterministic and the
 295 | +     blind verdict) and context integrity (L-s). The release authorisation must require both, from
 296 | +     `edl["moments_checks"]`.
 297 | +   - stand_alone's topic check stays: its subject for a Bitcoin package is Bitcoin, and every segment names it by rule.
 298 | +   - Every other integrity gate is unchanged.
 299 | +   - L-t: the title and caption are bound into the release authorisation (release_auth's attested set, with both
 300 | +     finals). Any change after the gates re-runs them.
 301 | +5. **The windows still applied downstream** (R6 item 2: edl_rules R5 8-25 s, select_passages:333, stand_alone at
 302 | +   validate) must follow law L-o.
 303 | +   - The packager keeps every segment at <= 20 s (L-u). A hook under 8 s HOLDs at R5 until R6 item 2 lands.
 304 | +6. **L-x.** Every role resolves through pipeline/model_providers.json, so no model name lives in code.
 305 | +   - The integrator runs the local legs of tests/providers/ab_roles.py under the GPU0 lease (`--local`), and re-orders
 306 | +     a role's chain only on that measurement.
 307 | +   - The Heimdall 90 % tripwire notifies, never halts (providers.Router.heimdall_tripwire).
 308 | +
 309 | +<!-- PATCH R7 BEGIN -->
 310 | +```diff
 311 | +--- a/pipeline/pinned.py
 312 | ++++ b/pipeline/pinned.py
 313 | +@@ -311,20 +311,45 @@
 314 | +     for i, c in enumerate(clips, 1):
 315 | +         c["index"] = i
 316 | +     channels = sorted({x["channel"] for x in segs})
 317 | ++    mp = pin.get("moments_package")            # pp-selectid R7: a moments-first package (law L-q) as the decision
 318 | ++    vo = _generate_vo_script(pin["label"], hook["text"], clips, channels)
 319 | ++    if isinstance(mp, dict):
 320 | ++        vo = moments_vo(mp, clips)
 321 | +     edl = {
 322 | +         "topic": pin["label"],
 323 | +         "angle": f"Pinned: {pin.get('headline') or pin['label']}",
 324 | +         "hook": hook,
 325 | +         "clips": clips,
 326 | +-        "vo": _generate_vo_script(pin["label"], hook["text"], clips, channels),
 327 | ++        "vo": vo,
 328 | +         "total_clip_duration": round(hook["duration"] + sum(c["duration"] for c in clips), 2),
 329 | +         "mode": "pinned",
 330 | +         "pinned_story_id": pin["story_id"],
 331 | +     }
 332 | ++    if isinstance(mp, dict):                   # law L-t: the ONE title and caption travel with the EDL to release
 333 | ++        edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
 334 | ++                   moments_checks=mp.get("checks"))
 335 | +     overrides = build_vertical_overrides(hook, clips, registry)
 336 | +     return edl, overrides, report
 337 | + 
 338 | + 
 339 | ++def moments_vo(mp, clips):
 340 | ++    """The package's VO, checked by its VO-fidelity and context-integrity gates (pipeline/package.py): the intro and
 341 | ++    one bridge after each clip but the last, in the EDL's shape ({"text", "after_clip"}). Fail closed on any shape
 342 | ++    the renderer cannot place (a bridge after the hook, after the last clip, or after a missing clip)."""
 343 | ++    v = mp.get("edl_vo") or {}
 344 | ++    intro = v.get("intro")
 345 | ++    bridges = v.get("bridges") or []
 346 | ++    idx = {c["index"] for c in clips}
 347 | ++    for b in bridges:
 348 | ++        if not isinstance(b, dict) or not str(b.get("text") or "").strip() or b.get("after_clip") not in idx or                 b["after_clip"] == max(idx):
 349 | ++            raise PinError(f"moments_package bridge {b!r}: needs text and after_clip in 1..{max(idx) - 1}")
 350 | ++    if intro is not None and not str(intro).strip():
 351 | ++        raise PinError("moments_package intro is empty")
 352 | ++    if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):
 353 | ++        raise PinError("moments_package: the VO-fidelity and context-integrity gates did not both pass")
 354 | ++    return {"intro": intro, "bridges": [{"text": b["text"], "after_clip": b["after_clip"]} for b in bridges]}
 355 | ++
 356 | ++
 357 | + def prepare(pin_path, run_dir, log=print):
 358 | +     """Validate + acquire + build. Writes edl.json, vertical_overrides.json, PINNED_DECISION.json.
 359 | +     Returns the PINNED_DECISION record. Raises PinError."""
 360 | +```
 361 | +<!-- PATCH R7 END -->
 362 | +
 363 | +## R8 FOR pipeline_pp_tests (the exam): cases this session found (orchestrator 03:40: "send the case to pipeline_pp_tests")
 364 | +
 365 | +1. **title_misleads_about_now** (vo_fidelity corpus, a new fail class; laws L-v 3 / L-t). REAL case, fresh_20261112_050611:
 366 | +   - The candidate title, caption and VO intro were "Bitcoin ran from 16K to 126K" (Simply Bitcoin, Noq6txZU91c
 367 | +     399.15-405.25, verbatim).
 368 | +   - The universe's own current level that night was about $73,000: Bitcoin falling and testing its 200-day average.
 369 | +   - Every word is in a clip, and the line is still misleading as a headline.
 370 | +   - Must FAIL: a headline line (title / caption / intro) stating a price level or move that is neither marked as
 371 | +     history ("from the 2022 low ...") nor within tolerance of a level the universe states as current.
 372 | +   - Must PASS: the same numbers marked as history; today's level stated as today's.
 373 | +   - This session's gate: vo_fidelity PRICE_NOW with package.current_levels.
 374 | +2. **clip_repeats_the_line_before_it** (a package-structure fail class). Same night: the intro and the title repeated
 375 | +   clip_03's words, which then played as a 6.1 s clip that added nothing.
 376 | +   - Must FAIL: a VO line right before a clip, or the title, carrying a run of >= 5 canonical tokens of that clip.
 377 | +   - This session's gate: package.duplicates.
 378 | +3. **cleft_it / generic_we** (context_integrity must-PASS near misses, NOTE-PS12): "It's not Bitcoin that's getting
 379 | +   hacked. It's other intermediaries." (What Bitcoin Did) and "we are going to have a new internet" (Natalie Brunell).
 380 | +   A referent rule that rejects these is a false reject.
 381 | +
 382 |  ## R5 BIBLE
 383 |  
 384 |  Fold docs/audits/parallel/pp-selectid_BIBLE_ADDITIONS.md (E-FAIL-PS1..PS4, NOTE-PS5, NOTE-PS6) into
 385 | diff --git a/tests/moments/proof_moments.py b/tests/moments/proof_moments.py
 386 | new file mode 100644
 387 | index 00000000..27be9816
 388 | --- /dev/null
 389 | +++ b/tests/moments/proof_moments.py
 390 | @@ -0,0 +1,95 @@
 391 | +#!/usr/bin/env python3
 392 | +"""Phase-2 proof driver, step 1 (MINE) on saved universes. CPU only; read-only inputs (the run's universe, the store's
 393 | +records by the recorded sha, as tests/select_by_id/proof_saved_runs.py reads them); every model reply recorded under
 394 | +tests/moments/fixtures/replies (offline replay); spend in tests/moments/proof/SPEND.json with the phase-2 $40 guard.
 395 | +
 396 | +Mining scope here: the videos with a sentence-ready word record in the store (on-screen capable, law L-e). A
 397 | +caption-only video can be mined in production after the cycle's word pass (pipeline_pp_ingest); in this CPU replay it is
 398 | +reported as awaiting the word pass, never mined from caption timing for the screen.
 399 | +
 400 | +Usage: python3 tests/moments/proof_moments.py --runs fresh_20261112_050611 [--replay] [--recent-h 72]
 401 | +"""
 402 | +import argparse
 403 | +import json
 404 | +import os
 405 | +import sys
 406 | +import time
 407 | +from datetime import datetime, timezone
 408 | +
 409 | +HERE = os.path.dirname(os.path.abspath(__file__))
 410 | +REPO = os.path.dirname(os.path.dirname(HERE))
 411 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 412 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 413 | +import eligibility as E  # noqa: E402
 414 | +import moments as M  # noqa: E402
 415 | +import providers as P  # noqa: E402
 416 | +import proof_saved_runs as PS  # noqa: E402
 417 | +import trend_brief as TB  # noqa: E402
 418 | +
 419 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
 420 | +OUT = os.path.join(HERE, "proof")
 421 | +SPEND = os.path.join(OUT, "SPEND.json")
 422 | +LIMIT_USD = 40.0                   # the phase-2 guard, counted from 01:55 ET Nov 12 (orchestrator)
 423 | +
 424 | +
 425 | +def universe_sources(run):
 426 | +    """(word Sources of the run's universe, caption-only video ids, ctx) from the saved run, read-only."""
 427 | +    saved = json.load(open(os.path.join(PS.RUNS, run, "TOPIC_SELECTION.json")))
 428 | +    started = datetime.fromisoformat(saved["started"])
 429 | +    assert started.tzinfo is not None
 430 | +    now = started.astimezone(timezone.utc)
 431 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 432 | +    words, captions = [], []
 433 | +    for u in saved.get("universe") or []:
 434 | +        if not u.get("transcript_sha256") or u["video_id"] in E.V2F_VIDEO_IDS:
 435 | +            continue
 436 | +        w = PS.word_source(u, ctx)
 437 | +        if w is not None:
 438 | +            words.append(w)
 439 | +        else:
 440 | +            captions.append(u["video_id"])
 441 | +    return words, captions, ctx, saved
 442 | +
 443 | +
 444 | +def run_one(run, router, recent_h, log=print):
 445 | +    words, captions, ctx, saved = universe_sources(run)
 446 | +    t0 = time.time()
 447 | +    base = TB.local_baseline(words, ctx, hours=24.0)
 448 | +    out = M.mine(router, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=log, cycle=f"proof:{run}",
 449 | +                 recent_h=recent_h)
 450 | +    for m in out["moments"]:
 451 | +        m["trend"] = TB.trend_match(m, None, base)
 452 | +    rec = {"run": run, "now": ctx.now.isoformat(), "seconds": round(time.time() - t0, 1),
 453 | +           "scope": {"word_sources": len(words), "caption_only_awaiting_word_pass": len(captions)},
 454 | +           "baseline": base, "rows": out["rows"], "sources_in_window": out["sources"], "skipped": out["skipped"],
 455 | +           "calls": [{k: v for k, v in c.items() if k != "attempts"} | {"attempts": [
 456 | +               {k2: v2 for k2, v2 in a.items() if k2 in ("attempt", "rejected", "declined", "model_error", "accepted",
 457 | +                                                        "meta", "prompt_sha256")} for a in c["attempts"]]}
 458 | +               for c in out["calls"]],
 459 | +           "moments": out["moments"]}
 460 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
 461 | +    json.dump(rec, open(os.path.join(OUT, run, "moments.json"), "w"), indent=1, default=str)
 462 | +    usable = [m for m in out["moments"] if m["on_screen_ok"] and not m["excluded"]]
 463 | +    log(f"{run}: {len(words)} word sources ({len(captions)} caption-only), rows {out['rows']}, calls "
 464 | +        f"{[c['status'] for c in out['calls']]}, moments {len(out['moments'])}, usable on screen {len(usable)} "
 465 | +        f"({rec['seconds']} s)")
 466 | +    return rec
 467 | +
 468 | +
 469 | +def main(argv=None):
 470 | +    ap = argparse.ArgumentParser()
 471 | +    ap.add_argument("--runs", nargs="+", required=True)
 472 | +    ap.add_argument("--replay", action="store_true")
 473 | +    ap.add_argument("--recent-h", type=float, default=72.0, help="the first cycle of a saved universe: its whole 72 h")
 474 | +    ap.add_argument("--chain", nargs="*", help="pin the mine role's chain (config names), e.g. for the A/B")
 475 | +    a = ap.parse_args(argv)
 476 | +    router = P.Router(env_path=PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=SPEND, limit_usd=LIMIT_USD,
 477 | +                      chains={"mine": a.chain} if a.chain else None)
 478 | +    for run in a.runs:
 479 | +        run_one(run, router, a.recent_h)
 480 | +    if router.notices:
 481 | +        print("NOTICES:", router.notices)
 482 | +
 483 | +
 484 | +if __name__ == "__main__":
 485 | +    main()
 486 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 487 | new file mode 100644
 488 | index 00000000..a2762d4d
 489 | --- /dev/null
 490 | +++ b/tests/moments/test_moments.py
 491 | @@ -0,0 +1,156 @@
 492 | +#!/usr/bin/env python3
 493 | +"""pipeline/moments.py + pipeline/package.py (deterministic parts): the miner's reply contract is strict and never
 494 | +repaired; ranking is deterministic with contempt as a penalty; the packager's sets keep L-u fairness (one segment per
 495 | +channel, <= 20 s per source video), the runtime arithmetic (60-70 s with the VO as slack) and at most one price
 496 | +prediction; the sign-off names exactly the credit set (L-a). Offline: no model call."""
 497 | +import json
 498 | +import os
 499 | +import sys
 500 | +import unittest
 501 | +from datetime import datetime, timedelta, timezone
 502 | +
 503 | +HERE = os.path.dirname(os.path.abspath(__file__))
 504 | +REPO = os.path.dirname(os.path.dirname(HERE))
 505 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 506 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 507 | +import eligibility as E  # noqa: E402
 508 | +import moments as M  # noqa: E402
 509 | +import package as PK  # noqa: E402
 510 | +import select_by_id as SB  # noqa: E402
 511 | +import trend_brief as TB  # noqa: E402
 512 | +from test_eligibility import CID, HOOK_TXT, CLIP_TXT, CLIP2_TXT, NOW, REG, source  # noqa: E402
 513 | +
 514 | +
 515 | +def reply(**kw):
 516 | +    return json.dumps(kw)
 517 | +
 518 | +
 519 | +SCORES = {"hook_first_2s": 4, "quotable": 3, "surprising_fact": 2, "stance": 3, "stakes": 2, "stands_alone": 4,
 520 | +          "contempt_outrage": 0}
 521 | +
 522 | +
 523 | +def mom(rng, **kw):
 524 | +    d = {"range": rng, "scores": dict(SCORES), "names_person": False, "risk": [], "topics": ["price_action"],
 525 | +         "reason": "a clean statement"}
 526 | +    d.update(kw)
 527 | +    return d
 528 | +
 529 | +
 530 | +class TestMineContract(unittest.TestCase):
 531 | +    def setUp(self):
 532 | +        self.a = source([HOOK_TXT, CLIP_TXT], channel="DataDash", vid="A")
 533 | +        self.b = source([CLIP2_TXT], channel="Natalie Brunell", vid="B")
 534 | +        self.t = SB.Table([(self.a, 0, False), (self.a, 1, False), (self.b, 0, False)])
 535 | +
 536 | +    def check(self, obj):
 537 | +        return M.check_moments(obj, self.t, TB.TOPICS)
 538 | +
 539 | +    def test_a_valid_reply_and_an_empty_one(self):
 540 | +        got = self.check({"moments": [mom([1, 2]), mom([3, 3])]})
 541 | +        self.assertEqual([(sp.source.video_id, sp.k0, sp.k1) for sp, _ in got], [("A", 0, 1), ("B", 0, 0)])
 542 | +        self.assertEqual(self.check({"moments": []}), [])
 543 | +
 544 | +    def test_rejected_never_repaired(self):
 545 | +        bad = [({"moments": [mom([1, 3])]}, "cross-source"),
 546 | +               ({"moments": [mom([1, 2]), mom([2, 2])]}, "overlaps"),
 547 | +               ({"moments": [mom([9, 9])]}, "fabricated"),
 548 | +               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=6))]}, "integer 0-5"),
 549 | +               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=3.0))]}, "integer 0-5"),
 550 | +               ({"moments": [mom([1, 1], scores={k: v for k, v in SCORES.items() if k != "stakes"})]}, "exactly"),
 551 | +               ({"moments": [mom([1, 1], risk=["libel"])]}, "'risk'"),
 552 | +               ({"moments": [mom([1, 1], topics=["altcoins"])]}, "'topics'"),
 553 | +               ({"moments": [mom([1, 1], topics=[])]}, "'topics'"),
 554 | +               ({"moments": [mom([1, 1], reason="")]}, "'reason'"),
 555 | +               ({"moments": [mom([1, 1], names_person="no")]}, "'names_person'"),
 556 | +               ({"moments": [dict(mom([1, 1]), headline="Bitcoin finds support")]}, "keys must be exactly"),
 557 | +               ({"moments": [mom([1, 1])] * 13}, "at most 12")]
 558 | +        for obj, why in bad:
 559 | +            with self.assertRaises(SB.Rejected) as cm:
 560 | +                self.check(obj)
 561 | +            self.assertIn(why, str(cm.exception), obj)
 562 | +
 563 | +    def test_ranking_is_deterministic_and_contempt_is_a_penalty(self):
 564 | +        calm = {"scores": dict(SCORES), "risk": [], "topics": ["price_action"]}
 565 | +        angry = {"scores": dict(SCORES, contempt_outrage=4), "risk": [], "topics": ["price_action"]}
 566 | +        pred = {"scores": dict(SCORES), "risk": ["price_prediction"], "topics": ["price_action"]}
 567 | +        self.assertGreater(M.rank_score(calm), M.rank_score(angry))
 568 | +        self.assertGreater(M.rank_score(calm), M.rank_score(pred))
 569 | +        self.assertEqual(M.rank_score(calm, trend={"price_action": 1.0}), M.rank_score(calm))   # SHADOW: weight 0
 570 | +
 571 | +    def test_ad_reads_are_never_offered_and_the_optout_registry_is_honoured(self):
 572 | +        ad = source(["This episode is brought to you by Swan Bitcoin, use code PULSE for a discount on Bitcoin.",
 573 | +                     HOOK_TXT], channel="DataDash", vid="AD")
 574 | +        self.assertNotIn(0, M.candidate_rows(ad))
 575 | +        self.assertIn(1, M.candidate_rows(ad))
 576 | +        ctx = E.Context(NOW, REG)
 577 | +        keep, skipped = M.window_sources([self.a, self.b], ctx, optout=frozenset({CID["DataDash"]}))
 578 | +        self.assertEqual([s.video_id for s in keep], ["B"])
 579 | +        self.assertIn("opted out", skipped["A"])
 580 | +
 581 | +
 582 | +def pm(mid, channel, dur, rank=10.0, hook=True, clip=True, risk=(), topics=("price_action",), vid=None):
 583 | +    return {"moment_id": mid, "channel_id": channel, "channel_name": channel, "video_id": vid or f"v{mid}",
 584 | +            "duration_s": dur, "rank_score": rank, "scores": dict(SCORES), "risk": list(risk), "topics": list(topics),
 585 | +            "eligibility": {"hook": {"ok": hook}, "clip": {"ok": clip}}, "on_screen_ok": True, "excluded": [],
 586 | +            "published_at": (NOW - timedelta(hours=6)).isoformat(), "speaker": {"turn_change_inside": None},
 587 | +            "text": "Bitcoin x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 588 | +            "transcript_sha256": "s"}
 589 | +
 590 | +
 591 | +class TestPackageArithmetic(unittest.TestCase):
 592 | +    def test_sets_keep_one_segment_per_channel_and_the_runtime(self):
 593 | +        ms = [pm("h1", "A", 10.0, rank=20), pm("c1", "B", 15.0), pm("c2", "C", 15.0), pm("c3", "A", 16.0, rank=30),
 594 | +              pm("c4", "D", 14.0)]
 595 | +        sets = PK.candidate_sets(ms)
 596 | +        self.assertTrue(sets)
 597 | +        lo, hi = PK.content_range()
 598 | +        for s in sets:
 599 | +            chans = [m["channel_id"] for m in s["segments"]]
 600 | +            self.assertEqual(len(chans), len(set(chans)))                     # L-u: one segment per channel
 601 | +            self.assertTrue(lo <= s["content_s"] <= hi)
 602 | +            self.assertTrue(3 <= len(s["segments"]) <= 4)
 603 | +
 604 | +    def test_over_20_s_unmeasured_excluded_and_stale_time_words_are_unusable(self):
 605 | +        ctx = E.Context(NOW, REG)
 606 | +        long_ = pm("l", "A", 21.0)
 607 | +        unmeasured = dict(pm("u", "B", 10.0), duration_s=None)
 608 | +        stale = dict(pm("s", "C", 12.0, risk=("time_sensitive",)), published_at=(NOW - timedelta(hours=30)).isoformat())
 609 | +        fresh = pm("f", "D", 12.0, risk=("time_sensitive",))
 610 | +        excluded = dict(pm("x", "E", 12.0), excluded=["accusation"])
 611 | +        ok, why = PK.usable([long_, unmeasured, stale, fresh, excluded], ctx)
 612 | +        self.assertEqual([m["moment_id"] for m in ok], ["f"])
 613 | +        self.assertIn("20.0 s", why["l"])
 614 | +        self.assertIn("L-v 3", why["s"])
 615 | +        self.assertIn("accusation", why["x"])
 616 | +
 617 | +    def test_at_most_one_price_prediction_per_video(self):
 618 | +        ms = [pm("h", "A", 10.0, risk=("price_prediction",)), pm("c1", "B", 16.0, risk=("price_prediction",)),
 619 | +              pm("c2", "C", 16.0)]
 620 | +        for s in PK.candidate_sets(ms):
 621 | +            self.assertLessEqual(sum("price_prediction" in m["risk"] for m in s["segments"]), 1)
 622 | +
 623 | +    def test_the_signoff_names_exactly_the_credit_set_hook_first(self):
 624 | +        ctx = E.Context(NOW, REG)
 625 | +        segs = [pm("h", CID["DataDash"], 10.0), pm("c1", CID["Natalie Brunell"], 15.0),
 626 | +                pm("c2", CID["Yahoo Finance"], 15.0)]
 627 | +        self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
 628 | +                                                "Go follow them for more. Links are below.")
 629 | +
 630 | +    def test_the_writer_contract_is_strict(self):
 631 | +        ms = [pm("h1", "A", 10.0), pm("c1", "B", 15.0), pm("c2", "C", 15.0)]
 632 | +        sets = [{"ids": ["h1", "c1", "c2"], "segments": ms, "score": 1, "content_s": 40.0}]
 633 | +        line = lambda t, c: {"text": t, "cites": c}
 634 | +        good = {"set": 1, "order": ["h1", "c2", "c1"], "type": "moments", "angle": "a",
 635 | +                "intro": line("Here's A.", ["h1"]), "bridges": [line("Next, B.", ["c1"])],
 636 | +                "title": line("Bitcoin: A, B and C", ["h1"]), "caption": line("Clips from A, B, C.", ["h1"])}
 637 | +        PK.check_written(good, sets)
 638 | +        for k, v, why in (("order", ["c1", "h1", "c2"], "hook first"), ("set", 2, "offered set"),
 639 | +                          ("bridges", [line("x", ["c2"]), line("y", ["c1"])], "'bridges' must hold 1"),
 640 | +                          ("title", line("x" * 71, ["h1"]), "title <= 70"), ("intro", line("x", ["zz"]), "cites")):
 641 | +            with self.assertRaises(ValueError) as cm:
 642 | +                PK.check_written(dict(good, **{k: v}), sets)
 643 | +            self.assertIn(why, str(cm.exception))
 644 | +
 645 | +
 646 | +if __name__ == "__main__":
 647 | +    unittest.main()
 648 | diff --git a/tests/package/proof_packages.py b/tests/package/proof_packages.py
 649 | new file mode 100644
 650 | index 00000000..ab36e1d8
 651 | --- /dev/null
 652 | +++ b/tests/package/proof_packages.py
 653 | @@ -0,0 +1,88 @@
 654 | +#!/usr/bin/env python3
 655 | +"""Phase-2 proof driver, step 2 (PACKAGE) on saved universes: reads tests/moments/proof/<run>/moments.json, builds the
 656 | +package through both gates (pipeline/package.py), records every reply (tests/package/fixtures/replies), spends into the
 657 | +phase-2 ledger (tests/moments/proof/SPEND.json, $40 guard), writes tests/package/proof/<run>/package.json and prints the
 658 | +package in full. CPU only; read-only inputs.
 659 | +
 660 | +Usage: python3 tests/package/proof_packages.py --runs fresh_20261112_050611 [--replay]
 661 | +"""
 662 | +import argparse
 663 | +import json
 664 | +import os
 665 | +import sys
 666 | +import time
 667 | +
 668 | +HERE = os.path.dirname(os.path.abspath(__file__))
 669 | +REPO = os.path.dirname(os.path.dirname(HERE))
 670 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 671 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 672 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 673 | +import moments as M  # noqa: E402
 674 | +import package as PK  # noqa: E402
 675 | +import proof_moments as PM  # noqa: E402
 676 | +import providers as P  # noqa: E402
 677 | +
 678 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
 679 | +OUT = os.path.join(HERE, "proof")
 680 | +
 681 | +
 682 | +def show(pk):
 683 | +    coh = (pk.get("checks") or {}).get("coherence") or {}
 684 | +    lines = [f"ANGLE: {pk['angle']}", f"VO {pk['vo_kind']} | runtime estimate {pk['runtime_s_estimate']} s "
 685 | +             f"({pk['runtime_note']})",
 686 | +             f"COHERENCE (blind, {coh.get('backend')}): through-line \"{coh.get('through_line')}\" | clips "
 687 | +             f"{coh.get('clips')} | VO point {coh.get('vo_point')}",
 688 | +             f"TITLE: {pk['title']}", f"CAPTION: {pk['caption']}", f"VO intro: {pk['vo']['intro']}"]
 689 | +    after = dict(zip(pk["vo"].get("bridges_after_clip") or [], pk["vo"]["bridges"]))
 690 | +    for i, s in enumerate(pk["segments"]):
 691 | +        lines.append(f"  [{s['label']}] {s['channel']} {s['video_id']} {s['start']:.2f}-{s['end']:.2f} "
 692 | +                     f"({s['duration_s']} s): \"{s['text']}\"")
 693 | +        if after.get(i):
 694 | +            lines.append(f"VO bridge: {after[i]}")
 695 | +    lines.append(f"VO sign-off: {pk['vo']['signoff']}")
 696 | +    lines.append(f"models: {pk.get('models')}")
 697 | +    return "\n".join(lines)
 698 | +
 699 | +
 700 | +def run_one(run, router, log=print, want=1, truth_dir=None):
 701 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
 702 | +    words, captions, ctx, saved = PM.universe_sources(run)
 703 | +    sources = {s.video_id: s for s in words}
 704 | +    t0 = time.time()
 705 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log, want=want,
 706 | +                   truth_dir=truth_dir)
 707 | +    res["seconds"] = round(time.time() - t0, 1)
 708 | +    res["run"] = run
 709 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
 710 | +    json.dump(res, open(os.path.join(OUT, run, "package.json"), "w"), indent=1, default=str)
 711 | +    if res["package"]:
 712 | +        import package_pin
 713 | +        for i, pk in enumerate(res["packages"] or [res["package"]]):
 714 | +            path, _ = package_pin.write_pin(pk, run, os.path.join(OUT, run))
 715 | +            if i:
 716 | +                os.replace(path, path.replace("MOMENTS_PIN.json", f"MOMENTS_PIN_alt{i}.json"))
 717 | +                path = path.replace("MOMENTS_PIN.json", f"MOMENTS_PIN_alt{i}.json")
 718 | +            log(f"{run}: {'PACKAGE' if i == 0 else f'ALTERNATIVE {i}'} ({res['seconds']} s) pin {path}\n" + show(pk))
 719 | +    else:
 720 | +        log(f"{run}: no package ({res.get('why_none')}); usable moments {res['usable']}; tried "
 721 | +            f"{json.dumps(res['tried'], default=str)[:1500]}")
 722 | +    return res
 723 | +
 724 | +
 725 | +def main(argv=None):
 726 | +    ap = argparse.ArgumentParser()
 727 | +    ap.add_argument("--runs", nargs="+", required=True)
 728 | +    ap.add_argument("--replay", action="store_true")
 729 | +    ap.add_argument("--want", type=int, default=1, help="packages per universe (the top + alternatives)")
 730 | +    ap.add_argument("--truth-dir", help="run law L-v 2's second recognition pass (audio windows go here)")
 731 | +    a = ap.parse_args(argv)
 732 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=PM.SPEND,
 733 | +                      limit_usd=PM.LIMIT_USD)
 734 | +    for run in a.runs:
 735 | +        run_one(run, router, want=a.want, truth_dir=a.truth_dir)
 736 | +    if router.notices:
 737 | +        print("NOTICES:", router.notices)
 738 | +
 739 | +
 740 | +if __name__ == "__main__":
 741 | +    main()
 742 | diff --git a/tests/package/run_exam_record.py b/tests/package/run_exam_record.py
 743 | new file mode 100644
 744 | index 00000000..bfb3ccad
 745 | --- /dev/null
 746 | +++ b/tests/package/run_exam_record.py
 747 | @@ -0,0 +1,77 @@
 748 | +#!/usr/bin/env python3
 749 | +"""Record this session's gate replies for pipeline_pp_tests' exam (tests/adversarial/corpora, format v1), so that the
 750 | +exam's harness, which forbids network connections, replays them offline (PP_GATES_REPLAY=1).
 751 | +
 752 | +Each case is stripped EXACTLY as the harness strips it before the gate sees it: "expected", "provenance", "origin",
 753 | +any nested "provenance", and the real id (replaced by case-<12 hex>). This script never reads an answer. It writes
 754 | +nothing but the recorded replies (pipeline/moments_gate_adapter.py's record dir) and a verdict log keyed by the
 755 | +blinded id. The confusion table is the harness's to compute.
 756 | +
 757 | +Usage: python3 tests/package/run_exam_record.py --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora
 758 | +       [--chain ROLE=BACKEND ...]   (pin a leg of the L-x A/B; default: pipeline/model_providers.json)
 759 | +"""
 760 | +import argparse
 761 | +import hashlib
 762 | +import json
 763 | +import os
 764 | +import sys
 765 | +
 766 | +HERE = os.path.dirname(os.path.abspath(__file__))
 767 | +REPO = os.path.dirname(os.path.dirname(HERE))
 768 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 769 | +import moments_gate_adapter as A  # noqa: E402
 770 | +import providers as P  # noqa: E402
 771 | +
 772 | +GATES = (("context_integrity", "context_integrity"), ("vo_fidelity", "vo_fidelity"), ("exclusions", "exclusion"))
 773 | +
 774 | +
 775 | +def blind(case):
 776 | +    def strip(x):
 777 | +        if isinstance(x, dict):
 778 | +            return {k: strip(v) for k, v in x.items() if k not in ("provenance", "origin", "expected")}
 779 | +        if isinstance(x, list):
 780 | +            return [strip(v) for v in x]
 781 | +        return x
 782 | +    c = strip(case)
 783 | +    c["id"] = "case-" + hashlib.sha256(str(case.get("id")).encode()).hexdigest()[:12]
 784 | +    return c
 785 | +
 786 | +
 787 | +def main(argv=None):
 788 | +    ap = argparse.ArgumentParser()
 789 | +    ap.add_argument("--corpus", required=True)
 790 | +    ap.add_argument("--chain", nargs="*", default=[], help="ROLE=BACKEND (config names), one per role to pin")
 791 | +    ap.add_argument("--out", default=os.path.join(HERE, "exam"))
 792 | +    a = ap.parse_args(argv)
 793 | +    chains = {}
 794 | +    for x in a.chain:
 795 | +        role, backend = x.split("=", 1)
 796 | +        chains.setdefault(role, []).append(backend)
 797 | +    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND, limit_usd=40.0, chains=chains or None)
 798 | +    os.makedirs(a.out, exist_ok=True)
 799 | +    log = []
 800 | +    for corpus, gate in GATES:
 801 | +        d = os.path.join(a.corpus, corpus)
 802 | +        if not os.path.isdir(d):
 803 | +            continue
 804 | +        for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
 805 | +            case = blind(json.load(open(os.path.join(d, f))))
 806 | +            try:
 807 | +                v = getattr(A, gate)(case)
 808 | +            except P.SpendLimit as e:
 809 | +                log.append({"gate": gate, "case": case["id"], "stopped": str(e)})
 810 | +                print("SPEND GUARD:", e)
 811 | +                json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
 812 | +                return 2
 813 | +            except Exception as e:
 814 | +                v = {"verdict": "error", "why": f"{type(e).__name__}: {str(e)[:200]}"}
 815 | +            log.append({"gate": gate, "case": case["id"], "verdict": v["verdict"]})
 816 | +            print(gate, case["id"], v["verdict"], flush=True)
 817 | +    json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
 818 | +    if A._router.notices:
 819 | +        print("NOTICES:", A._router.notices)
 820 | +    return 0
 821 | +
 822 | +
 823 | +if __name__ == "__main__":
 824 | +    sys.exit(main())
 825 | diff --git a/tests/package/smoke_r7.py b/tests/package/smoke_r7.py
 826 | new file mode 100644
 827 | index 00000000..bef45520
 828 | --- /dev/null
 829 | +++ b/tests/package/smoke_r7.py
 830 | @@ -0,0 +1,98 @@
 831 | +#!/usr/bin/env python3
 832 | +"""Smoke test of REQUESTS R7's pinned.py patch (a moments-first package as the PINNED decision): the patch applied to
 833 | +a TEMPORARY copy of pipeline/, then pinned.build_edl run on a pin made by pipeline/package_pin.py with a faked
 834 | +acquisition (the transcript words of each range; no download, no Whisper, no GPU, no network).
 835 | +
 836 | +Checks:
 837 | +- the EDL carries the package's VO (intro, and bridges with the renderer's after_clip), its ONE title and caption
 838 | +  (law L-t) and the package sha;
 839 | +- a bridge the renderer cannot place, or a package whose gates did not both pass, is refused (PinError);
 840 | +- a pin without a package keeps today's VO (none: Editorial Law 2's default).
 841 | +Usage: python3 tests/package/smoke_r7.py PATCH_FILE"""
 842 | +import copy
 843 | +import json
 844 | +import os
 845 | +import shutil
 846 | +import subprocess
 847 | +import sys
 848 | +import tempfile
 849 | +
 850 | +HERE = os.path.dirname(os.path.abspath(__file__))
 851 | +REPO = os.path.dirname(os.path.dirname(HERE))
 852 | +
 853 | +
 854 | +def fake_acq(pin):
 855 | +    acq = {}
 856 | +    for s in pin["segments"]:
 857 | +        words, t = [], float(s["start"])
 858 | +        for w in s["approved_text"].split():
 859 | +            words.append({"word": w, "start": round(t, 3), "end": round(t + 0.3, 3)})
 860 | +            t += 0.32
 861 | +        acq[s["video_id"]] = {"transcript": {"words": words, "segments": []}, "transcript_path": __file__,
 862 | +                              "offset": 0.0, "provenance": {"kind": "smoke"}}
 863 | +    return acq
 864 | +
 865 | +
 866 | +def main(argv=None):
 867 | +    patch = (argv or sys.argv[1:])[0]
 868 | +    tmp = tempfile.mkdtemp(prefix="pp_r7_smoke_")
 869 | +    try:
 870 | +        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
 871 | +                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
 872 | +        r = subprocess.run(["patch", "-p1", "-d", tmp, "-i", os.path.abspath(patch)], capture_output=True, text=True)
 873 | +        if r.returncode:
 874 | +            raise SystemExit("PATCH DOES NOT APPLY: " + r.stdout + r.stderr)
 875 | +        sys.path.insert(0, os.path.join(tmp, "pipeline"))
 876 | +        import pinned
 877 | +        import package_pin
 878 | +        assert os.path.dirname(pinned.__file__) == os.path.join(tmp, "pipeline")
 879 | +        pk = {"schema": "pp.package/1", "type": "moments", "title": "Bitcoin: three voices", "caption": "Clips from A, B, C.",
 880 | +              "hook_first_words": "Bitcoin is", "runtime_s_estimate": 64.0, "models": {"writer": "x"},
 881 | +              "vo": {"intro": "Here's DataDash on Bitcoin.", "bridges": ["Next, Yahoo Finance on Bitcoin."],
 882 | +                     "bridges_after_clip": [1], "signoff": "Clips today from ..."},
 883 | +              "segments": [{"video_id": v, "channel": ch, "start": 10.0, "end": 20.0, "url_30s_before": "u",
 884 | +                            "text": f"Bitcoin is the subject of sentence {i} spoken by {ch} here today."}
 885 | +                           for i, (v, ch) in enumerate((("aaaaaaaaaaa", "DataDash"), ("bbbbbbbbbbb", "Natalie Brunell"),
 886 | +                                                        ("ccccccccccc", "Yahoo Finance")))]}
 887 | +        pin = package_pin.to_pin(pk, "smoke")
 888 | +        pin["moments_package"]["checks"].update(vo_fidelity_ok=True, context_integrity_ok=True)
 889 | +        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
 890 | +                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
 891 | +                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
 892 | +                                              "end_file": s["end"], "source_duration": 999.0,
 893 | +                                              "words": a["transcript"]["words"], "transcript_word_straddles_boundary": False,
 894 | +                                              "edge_words_from": "smoke", "approved_text_similarity": 1.0}
 895 | +        pinned.L.make_lock = lambda *a, **k: {"smoke": True}
 896 | +        pinned.L.sha256_file = lambda p: "0" * 64
 897 | +        edl, ov, rep = pinned.build_edl(pin, fake_acq(pin))
 898 | +        assert edl["vo"] == {"intro": "Here's DataDash on Bitcoin.",
 899 | +                             "bridges": [{"text": "Next, Yahoo Finance on Bitcoin.", "after_clip": 1}]}, edl["vo"]
 900 | +        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], edl
 901 | +        assert edl["moments_package_sha256"] == pin["moments_package"]["package_sha256"]
 902 | +        bad = copy.deepcopy(pin)
 903 | +        bad["moments_package"]["edl_vo"]["bridges"] = [{"text": "x", "after_clip": 2}]      # after the last clip
 904 | +        try:
 905 | +            pinned.build_edl(bad, fake_acq(bad))
 906 | +            raise SystemExit("FAIL: a bridge after the last clip was accepted")
 907 | +        except pinned.PinError:
 908 | +            pass
 909 | +        bad2 = copy.deepcopy(pin)
 910 | +        bad2["moments_package"]["checks"]["context_integrity_ok"] = False
 911 | +        try:
 912 | +            pinned.build_edl(bad2, fake_acq(bad2))
 913 | +            raise SystemExit("FAIL: a package whose context gate did not pass was accepted")
 914 | +        except pinned.PinError:
 915 | +            pass
 916 | +        plain = copy.deepcopy(pin)
 917 | +        plain.pop("moments_package")
 918 | +        edl2, _, _ = pinned.build_edl(plain, fake_acq(plain))
 919 | +        assert edl2["vo"] == {"intro": None, "bridges": []} and "title" not in edl2, edl2
 920 | +        print("SMOKE R7 PASS: the package's VO / title / caption reach the EDL; unplaceable or ungated packages are refused;"
 921 | +              " a plain pin is unchanged")
 922 | +        return 0
 923 | +    finally:
 924 | +        shutil.rmtree(tmp, ignore_errors=True)
 925 | +
 926 | +
 927 | +if __name__ == "__main__":
 928 | +    sys.exit(main())
 929 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 930 | new file mode 100644
 931 | index 00000000..3dd1861d
 932 | --- /dev/null
 933 | +++ b/tests/package/test_angles.py
 934 | @@ -0,0 +1,85 @@
 935 | +#!/usr/bin/env python3
 936 | +"""pipeline/package.py angle-first parts (orchestrator review 03:40), deterministic: the angle contract; the line-up for
 937 | +an angle (one segment per channel, the runtime arithmetic, a short clip only as the punchline); a clip must add
 938 | +something (DUPLICATE); PRICE_NOW against the universe's current levels. Offline."""
 939 | +import os
 940 | +import sys
 941 | +import unittest
 942 | +from datetime import timedelta
 943 | +
 944 | +HERE = os.path.dirname(os.path.abspath(__file__))
 945 | +REPO = os.path.dirname(os.path.dirname(HERE))
 946 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 947 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 948 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 949 | +import eligibility as E  # noqa: E402
 950 | +import package as PK  # noqa: E402
 951 | +import vo_fidelity as VF  # noqa: E402
 952 | +from test_eligibility import NOW, REG, source  # noqa: E402
 953 | +from test_moments import pm  # noqa: E402
 954 | +
 955 | +
 956 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
 957 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
 958 | +
 959 | +
 960 | +class TestAngles(unittest.TestCase):
 961 | +    def setUp(self):
 962 | +        self.by = {m["moment_id"]: m for m in (pm("a", "A", 9.0), pm("b", "B", 16.0), pm("c", "C", 15.0),
 963 | +                                                pm("d", "D", 6.0), pm("e", "A", 14.0))}
 964 | +
 965 | +    def test_the_angle_contract_is_strict(self):
 966 | +        ok = {"angles": [angle(["a", "b", "c"], "a")]}
 967 | +        self.assertEqual(len(PK.check_angles(ok, self.by)), 1)
 968 | +        for bad, why in (({"angles": [angle(["a", "b"], "a")]}, "3-8"),
 969 | +                         ({"angles": [angle(["a", "e", "zz"], "a")]}, "3-8"),
 970 | +                         ({"angles": [angle(["a", "e", "b"], "a")]}, ">= 3 channels"),
 971 | +                         ({"angles": [angle(["a", "b", "c"], "d")]}, "hook"),
 972 | +                         ({"angles": [dict(angle(["a", "b", "c"], "a"), title="x")]}, "keys"),
 973 | +                         ({"angles": []}, "angles")):
 974 | +            with self.assertRaises(ValueError) as cm:
 975 | +                PK.check_angles(bad, self.by)
 976 | +            self.assertIn(why, str(cm.exception))
 977 | +
 978 | +    def test_a_lineup_per_angle_keeps_the_rules(self):
 979 | +        seg = PK.lineup_for(angle(["a", "b", "c", "e"], "a"), self.by)
 980 | +        self.assertIsNotNone(seg)
 981 | +        self.assertEqual(seg[0]["moment_id"], "a")                               # the proposer's hook
 982 | +        chans = [m["channel_id"] for m in seg]
 983 | +        self.assertEqual(len(chans), len(set(chans)))                            # L-u: one segment per channel
 984 | +        lo, hi = PK.content_range()
 985 | +        self.assertTrue(lo <= sum(m["duration_s"] for m in seg) <= hi)
 986 | +
 987 | +    def test_a_short_clip_only_as_the_punchline(self):
 988 | +        seg = PK.lineup_for(angle(["a", "d", "b", "c"], "a"), self.by)
 989 | +        if seg and any(m["moment_id"] == "d" for m in seg):
 990 | +            self.assertEqual(seg[-1]["moment_id"], "d")                          # 6 s: last, never in the middle
 991 | +
 992 | +    def test_a_clip_must_add_something(self):
 993 | +        pk = {"segments": [{"label": "hook", "text": "Bitcoin ran from 16K to 126K. That move is about an 8x."},
 994 | +                           {"label": "clip_01", "text": "Nobody can take your Bitcoin without your keys, that is the point."},
 995 | +                           {"label": "clip_02", "text": "The hacks hit the exchanges and the intermediaries, never Bitcoin itself."}],
 996 | +              "vo": {"bridges": ["Next, the hacks hit the exchanges and the intermediaries, never Bitcoin itself."],
 997 | +                     "bridges_after_clip": [1]},
 998 | +              "lines": [{"slot": "intro", "text": "Bitcoin ran from 16K to 126K."},
 999 | +                        {"slot": "title", "text": "Who controls Bitcoin?"}]}
1000 | +        d = PK.duplicates(pk)
1001 | +        self.assertEqual({(x["slot"], x["rule"]) for x in d},
1002 | +                         {("before hook", "DUPLICATE"), ("before clip_02", "DUPLICATE")})
1003 | +
1004 | +    def test_price_now_against_the_current_levels(self):
1005 | +        src = source(["Bitcoin is trading at seventy three thousand dollars right now.",
1006 | +                      "Back in 2022 Bitcoin was at sixteen thousand dollars."], age_h=3.0)
1007 | +        levels = PK.current_levels([src], E.Context(NOW, REG))
1008 | +        self.assertEqual(levels, [73000.0])                                      # history is never a current level
1009 | +        self.assertEqual(VF.price_now("Bitcoin ran from 16K to 126K", levels), [16000.0, 126000.0])
1010 | +        self.assertEqual(VF.price_now("Bitcoin holds $73,000", levels), [])
1011 | +        self.assertEqual(VF.price_now("From the 2022 low, Bitcoin ran from 16K to 126K", levels), [])
1012 | +        segs = {"m": {"speaker": "S", "names": ["S"], "video_id": "v", "text": "Bitcoin ran from 16K to 126K."}}
1013 | +        r = VF.check_deterministic(segs, [{"slot": "title", "text": "Bitcoin ran from 16K to 126K", "cites": ["m"]}],
1014 | +                                   current_levels=levels)
1015 | +        self.assertIn("PRICE_NOW", {v["rule"] for v in r["violations"]})
1016 | +
1017 | +
1018 | +if __name__ == "__main__":
1019 | +    unittest.main()
1020 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
1021 | new file mode 100644
1022 | index 00000000..b37f5efe
1023 | --- /dev/null
1024 | +++ b/tests/package/test_gates.py
1025 | @@ -0,0 +1,168 @@
1026 | +#!/usr/bin/env python3
1027 | +"""pipeline/context_integrity.py (law L-s) and pipeline/vo_fidelity.py (law L-o 11 / L-t): the DECISION RULES, with
1028 | +canned model replies on a fake router (unit fixtures; the exam corpus is pipeline_pp_tests'). Offline."""
1029 | +import json
1030 | +import os
1031 | +import sys
1032 | +import unittest
1033 | +
1034 | +HERE = os.path.dirname(os.path.abspath(__file__))
1035 | +REPO = os.path.dirname(os.path.dirname(HERE))
1036 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1037 | +import context_integrity as CI  # noqa: E402
1038 | +import providers as P  # noqa: E402
1039 | +import vo_fidelity as VF  # noqa: E402
1040 | +
1041 | +
1042 | +class Canned:
1043 | +    """A router stand-in: answers each role from a queue; records (role, avoid_vendor)."""
1044 | +
1045 | +    def __init__(self, **answers):
1046 | +        self.answers, self.calls = {k: list(v) for k, v in answers.items()}, []
1047 | +
1048 | +    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None):
1049 | +        self.calls.append((role, avoid_vendor))
1050 | +        q = self.answers.get(role)
1051 | +        if not q:
1052 | +            raise P.ProviderError(f"{role}: no canned answer")
1053 | +        text = q.pop(0)
1054 | +        return P.Reply(text if isinstance(text, str) else json.dumps(text), f"fake:{role}", "fake")
1055 | +
1056 | +
1057 | +PKG = {"segments": [{"label": "hook", "video_id": "v1", "channel": "Coin Bureau", "text": "Bitcoin held its 200-day average."},
1058 | +                    {"label": "clip_01", "video_id": "v2", "channel": "Natalie Brunell", "text": "ETF outflows hit $1.3 billion."}],
1059 | +       "vo": {"intro": "Here's Coin Bureau.", "bridges": ["Next, Natalie Brunell."], "signoff": "Clips today from ..."},
1060 | +       "title": "Bitcoin: Coin Bureau and Natalie Brunell", "caption": "Clips from Coin Bureau, Natalie Brunell."}
1061 | +CTX = {lb: {"text": f"before <selected>{s['text']}</selected> after", "title": "t", "channel": s["channel"]}
1062 | +       for lb, s in (("hook", PKG["segments"][0]), ("clip_01", PKG["segments"][1]))}
1063 | +
1064 | +
1065 | +def a_item(label, **kw):
1066 | +    d = {"label": label, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [], "conditions": [],
1067 | +         "retraction": "none", "time_ok": "yes", "proposition": "p", "certainty": "certain"}
1068 | +    d.update(kw)
1069 | +    return d
1070 | +
1071 | +
1072 | +def run(a=None, b=None, c=None, relations=None):
1073 | +    A = {"excerpts": a or [a_item("hook"), a_item("clip_01")]}
1074 | +    B = {"takeaways": b or [{"label": lb, "asserts": "p", "certainty": "certain", "polarity": "neutral"}
1075 | +                            for lb in ("hook", "clip_01")],
1076 | +         "relations": relations if relations is not None else [{"labels": ["hook", "clip_01"], "relation": "none"}]}
1077 | +    C = {"pairs": c or [{"label": lb, "entails": "yes", "same_polarity": "yes", "stronger_certainty": "no"}
1078 | +                        for lb in ("hook", "clip_01")]}
1079 | +    r = Canned(context_verdict=[A, C], viewer_takeaway=[B])
1080 | +    return CI.check_contexts(r, PKG, CTX, writer_vendor="openai"), r
1081 | +
1082 | +
1083 | +class TestContextDecision(unittest.TestCase):
1084 | +    def test_a_clean_package_passes_and_no_step_runs_on_the_writers_vendor(self):
1085 | +        res, r = run()
1086 | +        self.assertTrue(res["ok"], res["violations"])
1087 | +        self.assertTrue(all(v == "openai" for _, v in r.calls))           # avoid_vendor passed on every step
1088 | +
1089 | +    def test_every_failure_class_fails(self):
1090 | +        cases = [
1091 | +            ({"a": [a_item("hook", view="attributed"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
1092 | +            ({"a": [a_item("hook", view="sarcastic"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
1093 | +            ({"a": [a_item("hook", speaker_changes_inside="uncertain"), a_item("clip_01")]}, "SPEAKER_CHANGE"),
1094 | +            ({"a": [a_item("hook", referents=[{"word": "it", "refers_to": "the ETF", "inside": False}]),
1095 | +                    a_item("clip_01")]}, "REFERENT_OUTSIDE"),
1096 | +            ({"a": [a_item("hook", conditions=[{"text": "if the Fed cuts", "inside": False}]), a_item("clip_01")]},
1097 | +             "CONDITION_OUTSIDE"),
1098 | +            ({"a": [a_item("hook", retraction="later says he misspoke"), a_item("clip_01")]}, "RETRACTION"),
1099 | +            ({"a": [a_item("hook", certainty="uncertain"), a_item("clip_01")]}, "UNCERTAIN"),
1100 | +            ({"a": [a_item("hook", time_ok="no"), a_item("clip_01")]}, "STALE_TIME"),
1101 | +            ({"a": [a_item("hook", time_ok="uncertain"), a_item("clip_01")]}, "STALE_TIME"),
1102 | +            ({"c": [{"label": "hook", "entails": "no", "same_polarity": "yes", "stronger_certainty": "no"},
1103 | +                    {"label": "clip_01", "entails": "yes", "same_polarity": "yes", "stronger_certainty": "no"}]},
1104 | +             "NOT_ENTAILED"),
1105 | +            ({"c": [{"label": "hook", "entails": "yes", "same_polarity": "uncertain", "stronger_certainty": "no"},
1106 | +                    {"label": "clip_01", "entails": "yes", "same_polarity": "yes", "stronger_certainty": "no"}]},
1107 | +             "POLARITY"),
1108 | +            ({"c": [{"label": "hook", "entails": "yes", "same_polarity": "yes", "stronger_certainty": "yes"},
1109 | +                    {"label": "clip_01", "entails": "yes", "same_polarity": "yes", "stronger_certainty": "no"}]},
1110 | +             "STRONGER"),
1111 | +            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "answering"}]}, "FALSE_RELATION"),
1112 | +            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "uncertain"}]}, "FALSE_RELATION"),
1113 | +        ]
1114 | +        for kw, rule in cases:
1115 | +            res, _ = run(**kw)
1116 | +            self.assertFalse(res["ok"], rule)
1117 | +            self.assertIn(rule, {v["rule"] for v in res["violations"]}, (rule, res["violations"]))
1118 | +
1119 | +    def test_an_unreadable_or_missing_step_fails_never_passes(self):
1120 | +        r = Canned(context_verdict=["not json"], viewer_takeaway=[])
1121 | +        res = CI.check_contexts(r, PKG, CTX, writer_vendor="openai")
1122 | +        self.assertFalse(res["ok"])
1123 | +        self.assertEqual(res["violations"][0]["rule"], "CONTEXT_UNAVAILABLE")
1124 | +        res, _ = run(a=[a_item("hook")])                                   # step A skipped a segment
1125 | +        self.assertFalse(res["ok"])
1126 | +
1127 | +    def test_a_relation_inside_one_video_is_allowed(self):
1128 | +        same = dict(PKG, segments=[dict(PKG["segments"][0]), dict(PKG["segments"][1], video_id="v1")])
1129 | +        A = {"excerpts": [a_item("hook"), a_item("clip_01")]}
1130 | +        B = {"takeaways": [{"label": lb, "asserts": "p", "certainty": "certain", "polarity": "neutral"}
1131 | +                           for lb in ("hook", "clip_01")],
1132 | +             "relations": [{"labels": ["hook", "clip_01"], "relation": "same_conversation"}]}
1133 | +        C = {"pairs": [{"label": lb, "entails": "yes", "same_polarity": "yes", "stronger_certainty": "no"}
1134 | +                       for lb in ("hook", "clip_01")]}
1135 | +        res = CI.check_contexts(Canned(context_verdict=[A, C], viewer_takeaway=[B]), same, CTX, "openai")
1136 | +        self.assertTrue(res["ok"], res["violations"])
1137 | +
1138 | +
1139 | +class TestFidelityVerdict(unittest.TestCase):
1140 | +    SEGS = {"m1": {"speaker": "Coin Bureau", "names": ["Coin Bureau"], "video_id": "v1",
1141 | +                   "text": "Bitcoin dropped to $73,000 and found support at its 200-day moving average."},
1142 | +            "m2": {"speaker": "Stephan Livera", "names": ["Stephan Livera"], "video_id": "v2",
1143 | +                   "text": "I think Bitcoin is by far the most undervalued asset in the entire financial system."}}
1144 | +    LINES = [{"slot": "intro", "text": "Coin Bureau says Bitcoin found support at its 200-day moving average.",
1145 | +              "cites": ["m1"]}]
1146 | +
1147 | +    def verdict(self, claims, lines=None):
1148 | +        r = Canned(fidelity_verdict=[{"claims": claims}])
1149 | +        return VF.check(r, self.SEGS, lines or self.LINES, writer_vendor="openai"), r
1150 | +
1151 | +    def test_supported_with_verbatim_words_passes(self):
1152 | +        res, r = self.verdict([{"line": "intro", "claim": "support at the 200-day average", "supported": "yes",
1153 | +                                "support": [{"segment": "m1", "words": "found support at its 200-day moving average"}]}])
1154 | +        self.assertTrue(res["ok"], res["violations"])
1155 | +        self.assertEqual(r.calls, [("fidelity_verdict", "openai")])
1156 | +
1157 | +    def test_a_point_drawn_from_two_clips_needs_both_verbatim(self):
1158 | +        lines = [{"slot": "intro", "text": "One voice calls Bitcoin undervalued while it found support.",
1159 | +                  "cites": ["m1", "m2"]}]
1160 | +        both = [{"segment": "m1", "words": "found support at its 200-day moving average"},
1161 | +                {"segment": "m2", "words": "Bitcoin is by far the most undervalued asset"}]
1162 | +        res, _ = self.verdict([{"line": "intro", "claim": "undervalued while it found support", "supported": "yes",
1163 | +                                "support": both}], lines)
1164 | +        self.assertTrue(res["ok"], res["violations"])
1165 | +        half = [both[0], {"segment": "m2", "words": "Bitcoin is cheap"}]          # one part is not their words
1166 | +        res, _ = self.verdict([{"line": "intro", "claim": "c", "supported": "yes", "support": half}], lines)
1167 | +        self.assertIn("VERDICT_UNVERIFIED", {v["rule"] for v in res["violations"]})
1168 | +
1169 | +    def test_production_facts_support_manifest_language(self):
1170 | +        lines = [{"slot": "caption", "text": "Clips from Coin Bureau and Stephan Livera. Links below.", "cites": []}]
1171 | +        res, _ = self.verdict([{"line": "caption", "claim": "clips from these channels; links below", "supported": "yes",
1172 | +                                "support": [{"segment": "manifest", "words": "Links to every source are below"}]}], lines)
1173 | +        self.assertTrue(res["ok"], res["violations"])
1174 | +
1175 | +    def test_unverifiable_support_no_and_uncertain_fail(self):
1176 | +        for claims, rule in (
1177 | +                ([{"line": "intro", "claim": "c", "supported": "yes",
1178 | +                   "support": [{"segment": "m1", "words": "found strong support"}]}], "VERDICT_UNVERIFIED"),
1179 | +                ([{"line": "intro", "claim": "c", "supported": "yes", "support": []}], "VERDICT_UNVERIFIED"),
1180 | +                ([{"line": "intro", "claim": "c", "supported": "no", "support": []}], "VERDICT_NO"),
1181 | +                ([{"line": "intro", "claim": "c", "supported": "uncertain", "support": []}], "VERDICT_UNCERTAIN")):
1182 | +            res, _ = self.verdict(claims)
1183 | +            self.assertFalse(res["ok"])
1184 | +            self.assertIn(rule, {v["rule"] for v in res["violations"]})
1185 | +
1186 | +    def test_no_verdict_is_a_failure(self):
1187 | +        res = VF.check(Canned(), self.SEGS, self.LINES, writer_vendor="openai")
1188 | +        self.assertFalse(res["ok"])
1189 | +        self.assertEqual(res["verdict"]["violations"][0]["rule"], "VERDICT_UNAVAILABLE")
1190 | +
1191 | +
1192 | +if __name__ == "__main__":
1193 | +    unittest.main()
1194 | diff --git a/tests/package/yield_table.py b/tests/package/yield_table.py
1195 | new file mode 100644
1196 | index 00000000..3c00c85b
1197 | --- /dev/null
1198 | +++ b/tests/package/yield_table.py
1199 | @@ -0,0 +1,69 @@
1200 | +#!/usr/bin/env python3
1201 | +"""Yield per saved universe against the backtest's blind oracle (orchestrator 03:00; law L-n): the oracle's
1202 | +moments-first line-ups judged to pass (/home/ultron/heimdall_probe/pp_redteam/oracle/<day>/moments/JUDGE_L*.json,
1203 | +read-only) beside this session's miner + packager (tests/moments/proof/<run>/moments.json,
1204 | +tests/package/proof/<run>/package.json). A universe where the oracle has a line-up that passes and this pipeline has no
1205 | +package is a DEFECT to fix before DONE. Note the rules differ: the oracle judged caption-line timing without the
1206 | +02:30 laws (one clip per channel L-u, context integrity L-s, layout DEC-12d); this pipeline applies them all.
1207 | +Writes docs/audits/parallel/pp-selectid_YIELD.md."""
1208 | +import glob
1209 | +import json
1210 | +import os
1211 | +
1212 | +HERE = os.path.dirname(os.path.abspath(__file__))
1213 | +REPO = os.path.dirname(os.path.dirname(HERE))
1214 | +ORACLE = "/home/ultron/heimdall_probe/pp_redteam/oracle"
1215 | +OUT = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_YIELD.md")
1216 | +RUNS = ("fresh_20261106_213852", "fresh_20261107_065702", "fresh_20261107_080503", "fresh_20261110_093150",
1217 | +        "fresh_20261111_190259", "fresh_20261111_192645", "fresh_20261111_213954", "fresh_20261112_001448",
1218 | +        "fresh_20261112_013452", "fresh_20261112_050611")
1219 | +
1220 | +
1221 | +def oracle_counts(run):
1222 | +    day = run.replace("fresh_", "")
1223 | +    d = os.path.join(ORACLE, day, "moments")
1224 | +    passed = 0
1225 | +    for f in glob.glob(os.path.join(d, "JUDGE_L*.json")):
1226 | +        if (json.load(open(f)).get("verdict") or "").upper() == "LEGAL":
1227 | +            passed += 1
1228 | +    story = 0
1229 | +    for f in glob.glob(os.path.join(ORACLE, day, "JUDGE_L*.json")):
1230 | +        if (json.load(open(f)).get("verdict") or "").upper() == "LEGAL":
1231 | +            story += 1
1232 | +    return passed, story
1233 | +
1234 | +
1235 | +def main():
1236 | +    rows = ["| universe | oracle: moments-first line-ups that pass / story-first | moments mined / usable | package | "
1237 | +            "title | gates | defect? |", "|---|---|---|---|---|---|---|"]
1238 | +    defects = 0
1239 | +    for run in RUNS:
1240 | +        mp, sp = oracle_counts(run)
1241 | +        mf = os.path.join(REPO, "tests", "moments", "proof", run, "moments.json")
1242 | +        pf = os.path.join(HERE, "proof", run, "package.json")
1243 | +        m = json.load(open(mf)) if os.path.exists(mf) else None
1244 | +        p = json.load(open(pf)) if os.path.exists(pf) else None
1245 | +        mined = f"{len(m['moments'])} / {sum(1 for x in m['moments'] if x['on_screen_ok'] and not x['excluded'])}" \
1246 | +            if m else "not mined"
1247 | +        pk = (p or {}).get("package")
1248 | +        if pk:
1249 | +            pkg, title = f"YES ({pk['type']}, {len(pk['segments'])} segments, ~{pk['runtime_s_estimate']} s)", pk["title"]
1250 | +            gates = "VO fidelity PASS, context integrity PASS"
1251 | +        else:
1252 | +            pkg = "no" if p else "not run"
1253 | +            title = "-"
1254 | +            gates = (p or {}).get("why_none") or "; ".join(
1255 | +                f"#{t.get('attempt')}: " + (t.get("writer_error") or ", ".join(sorted({v['rule'] for v in t.get('violations', [])})))
1256 | +                for t in (p or {}).get("tried", []))[:200] or "-"
1257 | +        defect = "DEFECT (L-n)" if mp and not pk else ""
1258 | +        defects += bool(defect)
1259 | +        rows.append(f"| {run} | {mp} / {sp} | {mined} | {pkg} | {title.replace('|', '/')} | {gates.replace('|', '/')} | "
1260 | +                    f"{defect} |")
1261 | +    text = "# pp-selectid — phase-2 yield against the blind oracle (generated by tests/package/yield_table.py)\n\n" + \
1262 | +        "\n".join(rows) + f"\n\nDefects (oracle has a passing line-up, this pipeline none): {defects}\n"
1263 | +    open(OUT, "w").write(text)
1264 | +    print(text)
1265 | +
1266 | +
1267 | +if __name__ == "__main__":
1268 | +    main()
1269 | diff --git a/tests/providers/ab_roles.py b/tests/providers/ab_roles.py
1270 | new file mode 100644
1271 | index 00000000..1bcd69e4
1272 | --- /dev/null
1273 | +++ b/tests/providers/ab_roles.py
1274 | @@ -0,0 +1,164 @@
1275 | +#!/usr/bin/env python3
1276 | +"""Blind A/B per model role (law L-x, orchestrator 02:45: "for each role report a blind A/B on saved data: local
1277 | +gemma3:27b vs frontier vs Heimdall: quality verdict, failures, latency, dollars"). The integrator runs the LOCAL leg
1278 | +under the GPU0 lease (--local: a started story_semantics.LocalLLM is handed to the router); builders run the rest.
1279 | +Generator and judge are always different models: the quality judge is a back-end outside the compared set.
1280 | +
1281 | +Roles:
1282 | +  mine        moments.mine on a saved universe with the role's chain pinned to ONE back-end per leg; quality: a blind
1283 | +              pairwise judge sees the source rows and two anonymised moment lists (order shuffled by seed) and says
1284 | +              which list holds better moments for a 60-second Bitcoin video (A / B / tie, with reasons); failures =
1285 | +              rejected / model_error calls; latency = model seconds; dollars from the spend ledger.
1286 | +  verdicts    fidelity_verdict, context_verdict, viewer_takeaway, exclusion_verdict: the pp-tests exam corpora
1287 | +              (format v1) through pipeline/moments_gate_adapter.py with the chain pinned per leg; quality = the
1288 | +              confusion table against the exam's answers (read only AFTER the gate answered, by this harness, never
1289 | +              by the gate).
1290 | +Usage:
1291 | +  python3 tests/providers/ab_roles.py mine --run fresh_20261112_050611 --legs heimdall:qwen/qwen3.8-27b openai:gpt-6.1-sol [--local]
1292 | +  python3 tests/providers/ab_roles.py verdicts --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora --legs ...
1293 | +Output: tests/providers/ab/<role>_<name>.json and a printed table.
1294 | +"""
1295 | +import argparse
1296 | +import json
1297 | +import os
1298 | +import random
1299 | +import sys
1300 | +import time
1301 | +
1302 | +HERE = os.path.dirname(os.path.abspath(__file__))
1303 | +REPO = os.path.dirname(os.path.dirname(HERE))
1304 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1305 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1306 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1307 | +import providers as P  # noqa: E402
1308 | +
1309 | +OUT = os.path.join(HERE, "ab")
1310 | +REPLIES = os.path.join(REPO, "tests", "moments", "fixtures", "replies")    # shared: a leg already mined replays
1311 | +SPEND = os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
1312 | +ENV = "/home/ultron/protocol_pulse/" + "." + "env"
1313 | +
1314 | +JUDGE_PROMPT = """Two editors each picked MOMENTS (verbatim quotes) for 60-second Bitcoin videos from the same
1315 | +transcripts. Judge which LIST is better material: moments that grab attention in the first seconds, are quotable,
1316 | +state something surprising or clear, stand alone without context, are about Bitcoin, and avoid accusations, advice,
1317 | +ads and outrage. Ignore list length beyond the best 8.
1318 | +
1319 | +LIST A:
1320 | +{a}
1321 | +
1322 | +LIST B:
1323 | +{b}
1324 | +
1325 | +Return ONLY this JSON object: {{"better": "A" | "B" | "tie", "why": "two sentences at most"}}"""
1326 | +
1327 | +
1328 | +def _router(chains, local=None):
1329 | +    return P.Router(env_path=ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=40.0, chains=chains,
1330 | +                    local_llm=local)
1331 | +
1332 | +
1333 | +def _local_llm():
1334 | +    import story_semantics as sm
1335 | +    return sm.LocalLLM().start()                 # proves the GPU0-only Ollama listener (law L-r: the caller's lease)
1336 | +
1337 | +
1338 | +def leg_mine(run, backend, local=None):
1339 | +    import moments as M
1340 | +    import proof_moments as PM
1341 | +    import trend_brief as TB
1342 | +    words, captions, ctx, saved = PM.universe_sources(run)
1343 | +    r = _router({"mine": [backend]}, local)
1344 | +    t0 = time.time()
1345 | +    out = M.mine(r, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=lambda s: None,
1346 | +                 cycle=f"ab:{run}:{backend}", recent_h=72.0)
1347 | +    secs = round(time.time() - t0, 1)
1348 | +    statuses = [c["status"] for c in out["calls"]]
1349 | +    usd = sum((a.get("meta") or {}).get("usd", 0.0) for c in out["calls"] for a in c["attempts"])
1350 | +    return {"backend": backend, "calls": len(statuses), "accepted": statuses.count("accepted"),
1351 | +            "failures": {s: statuses.count(s) for s in set(statuses) if s != "accepted"}, "seconds": secs,
1352 | +            "usd": round(usd, 4), "moments": out["moments"]}
1353 | +
1354 | +
1355 | +def judge_pair(judge_backend, a, b, seed):
1356 | +    def fmt(lst):
1357 | +        return "\n".join(f"- [{m['channel_name']}] \"{m['text'][:400]}\"" for m in lst[:8]) or "(none)"
1358 | +    r = _router({"ab_judge": [judge_backend]})
1359 | +    rng = random.Random(seed)
1360 | +    flip = rng.random() < 0.5
1361 | +    x, y = (b, a) if flip else (a, b)
1362 | +    rep = r.call("ab_judge", JUDGE_PROMPT.format(a=fmt(x), b=fmt(y)), 600, seed)
1363 | +    v = json.loads(rep.text.strip())
1364 | +    if not isinstance(v, dict) or v.get("better") not in ("A", "B", "tie"):
1365 | +        raise ValueError("judge reply out of contract")
1366 | +    better = v["better"] if v["better"] == "tie" else (("B" if v["better"] == "A" else "A") if flip else v["better"])
1367 | +    return {"better": better, "why": v.get("why"), "judge": rep.backend}
1368 | +
1369 | +
1370 | +def ab_mine(args):
1371 | +    legs = [leg_mine(args.run, b) for b in args.legs]
1372 | +    if args.local:
1373 | +        legs.append(leg_mine(args.run, "local:gemma3:27b", _local_llm()))
1374 | +    cfg = json.load(open(P.CONFIG))
1375 | +    compared = {l["backend"] for l in legs}
1376 | +    judge = args.judge or next(b for b in cfg["backends"] if b not in compared and cfg["backends"][b]["vendor"]
1377 | +                               not in {cfg["backends"][c]["vendor"] for c in compared if c in cfg["backends"]})
1378 | +    pairs = []
1379 | +    for i in range(len(legs)):
1380 | +        for j in range(i + 1, len(legs)):
1381 | +            try:
1382 | +                v = judge_pair(judge, legs[i]["moments"], legs[j]["moments"], seed=7 + i * 10 + j)
1383 | +            except Exception as e:
1384 | +                v = {"better": None, "why": f"judge failed: {type(e).__name__}: {str(e)[:160]}", "judge": judge}
1385 | +            pairs.append({"A": legs[i]["backend"], "B": legs[j]["backend"], **v})
1386 | +    rec = {"role": "mine", "run": args.run, "judge": judge,
1387 | +           "legs": [{k: v for k, v in l.items() if k != "moments"} | {"n_moments": len(l["moments"])} for l in legs],
1388 | +           "pairs": pairs}
1389 | +    os.makedirs(OUT, exist_ok=True)
1390 | +    json.dump(rec, open(os.path.join(OUT, f"mine_{args.run}.json"), "w"), indent=1, default=str)
1391 | +    print(json.dumps(rec, indent=1, default=str)[:4000])
1392 | +
1393 | +
1394 | +def ab_verdicts(args):
1395 | +    import moments_gate_adapter as A
1396 | +    rows = []
1397 | +    for backend in args.legs:
1398 | +        for gate, corpus, role in (("context_integrity", "context_integrity", ("context_verdict", "viewer_takeaway")),
1399 | +                                   ("vo_fidelity", "vo_fidelity", ("fidelity_verdict",)),
1400 | +                                   ("exclusion", "exclusions", ("exclusion_verdict",))):
1401 | +            d = os.path.join(args.corpus, corpus)
1402 | +            if not os.path.isdir(d):
1403 | +                continue
1404 | +            A._router = _router({r: [backend] for r in role})
1405 | +            conf, secs = {}, 0.0
1406 | +            for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
1407 | +                case = json.load(open(os.path.join(d, f)))
1408 | +                expected = case.pop("expected", {}).get("verdict")
1409 | +                case.pop("provenance", None)
1410 | +                t0 = time.time()
1411 | +                try:
1412 | +                    got = getattr(A, gate)(case)["verdict"]
1413 | +                except Exception as e:
1414 | +                    got = f"error:{type(e).__name__}"
1415 | +                secs += time.time() - t0
1416 | +                conf[(expected, got)] = conf.get((expected, got), 0) + 1
1417 | +            rows.append({"backend": backend, "gate": gate, "confusion": {f"{k[0]}->{k[1]}": v for k, v in conf.items()},
1418 | +                         "seconds": round(secs, 1)})
1419 | +    os.makedirs(OUT, exist_ok=True)
1420 | +    json.dump(rows, open(os.path.join(OUT, "verdicts.json"), "w"), indent=1)
1421 | +    for r in rows:
1422 | +        print(r)
1423 | +
1424 | +
1425 | +def main(argv=None):
1426 | +    ap = argparse.ArgumentParser()
1427 | +    ap.add_argument("role", choices=("mine", "verdicts"))
1428 | +    ap.add_argument("--run")
1429 | +    ap.add_argument("--corpus")
1430 | +    ap.add_argument("--legs", nargs="+", required=True)
1431 | +    ap.add_argument("--local", action="store_true", help="add the local gemma3:27b leg (the integrator, GPU0 lease)")
1432 | +    ap.add_argument("--judge")
1433 | +    a = ap.parse_args(argv)
1434 | +    (ab_mine if a.role == "mine" else ab_verdicts)(a)
1435 | +
1436 | +
1437 | +if __name__ == "__main__":
1438 | +    main()
1439 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1440 | new file mode 100644
1441 | index 00000000..34013184
1442 | --- /dev/null
1443 | +++ b/tests/providers/test_providers.py
1444 | @@ -0,0 +1,129 @@
1445 | +#!/usr/bin/env python3
1446 | +"""pipeline/providers.py (law L-x): one interface, a chain per role, the run continues when a vendor is down, verdicts
1447 | +never on the writer's vendor, every exchange recorded and replayable, spend guarded. Offline: fake back-ends only."""
1448 | +import json
1449 | +import os
1450 | +import sys
1451 | +import tempfile
1452 | +import unittest
1453 | +
1454 | +HERE = os.path.dirname(os.path.abspath(__file__))
1455 | +REPO = os.path.dirname(os.path.dirname(HERE))
1456 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1457 | +import providers as P  # noqa: E402
1458 | +
1459 | +
1460 | +class Fake(P.Backend):
1461 | +    def __init__(self, name, vendor, answer=None, fail=None, usage=None):
1462 | +        super().__init__(name, {"model": name.split(":", 1)[1], "price_usd_per_1m": [10, 100]}, "/nonexistent")
1463 | +        self.vendor, self.answer, self.fail, self.calls = vendor, answer, fail, 0
1464 | +        self._usage = usage or {"in": 1000, "out": 100}
1465 | +
1466 | +    def complete(self, prompt, max_tokens, seed, system=None):
1467 | +        self.calls += 1
1468 | +        if self.fail:
1469 | +            raise P.Unavailable(self.fail)
1470 | +        return self.answer, dict(self._usage), 0.01
1471 | +
1472 | +
1473 | +def router(tmp, backends, roles, **kw):
1474 | +    cfg = os.path.join(tmp, "cfg.json")
1475 | +    json.dump({"schema": "pp.providers/1",
1476 | +               "backends": {b.name: {"vendor": "openai", "model": b.model} for b in backends},
1477 | +               "roles": {r: {"chain": c} for r, c in roles.items()}}, open(cfg, "w"))
1478 | +    r = P.Router(cfg, env_path="/nonexistent", **kw)
1479 | +    r.backends = {b.name: b for b in backends}
1480 | +    return r
1481 | +
1482 | +
1483 | +class TestRouter(unittest.TestCase):
1484 | +    def test_the_chain_fails_over_and_names_the_model_that_answered(self):
1485 | +        with tempfile.TemporaryDirectory() as d:
1486 | +            a = Fake("openai:x", "openai", fail="HTTP 429 insufficient_quota (final: account)")
1487 | +            b = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
1488 | +            r = router(d, [a, b], {"write": ["openai:x", "anthropic:y"]})
1489 | +            rep = r.call("write", "p")
1490 | +            self.assertEqual((rep.text, rep.backend, rep.vendor), ('{"ok": 1}', "anthropic:y", "anthropic"))
1491 | +            self.assertEqual(rep.tried[0][0], "openai:x")
1492 | +            r.call("write", "p2")
1493 | +            self.assertEqual(a.calls, 1)                    # down for the rest of the run: not asked again
1494 | +
1495 | +    def test_a_verdict_never_runs_on_the_writers_vendor(self):
1496 | +        with tempfile.TemporaryDirectory() as d:
1497 | +            a = Fake("openai:x", "openai", answer="{}")
1498 | +            b = Fake("xai:z", "xai", answer='{"v": 1}')
1499 | +            r = router(d, [a, b], {"verdict": ["openai:x", "xai:z"]})
1500 | +            rep = r.call("verdict", "p", avoid_vendor="openai")
1501 | +            self.assertEqual(rep.backend, "xai:z")
1502 | +            self.assertEqual(a.calls, 0)
1503 | +            with self.assertRaises(P.ProviderError):
1504 | +                router(d, [a], {"verdict": ["openai:x"]}).call("verdict", "p", avoid_vendor="openai")
1505 | +
1506 | +    def test_every_backend_down_is_a_failed_role_never_a_pass(self):
1507 | +        with tempfile.TemporaryDirectory() as d:
1508 | +            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503"), Fake("xai:z", "xai", fail="URLError")],
1509 | +                       {"mine": ["openai:x", "xai:z", "heimdall:missing"]})
1510 | +            with self.assertRaises(P.ProviderError) as cm:
1511 | +                r.call("mine", "p")
1512 | +            self.assertIn("HTTP 503", str(cm.exception))
1513 | +            self.assertIn("not in config backends", str(cm.exception))
1514 | +            with self.assertRaises(P.ProviderError):
1515 | +                r.call("unknown_role", "p")
1516 | +
1517 | +    def test_record_then_replay_offline_with_the_backend_named(self):
1518 | +        with tempfile.TemporaryDirectory() as d:
1519 | +            a = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
1520 | +            r = router(d, [a], {"write": ["anthropic:y"]}, record_dir=os.path.join(d, "rec"))
1521 | +            r.call("write", "p", seed=7)
1522 | +            rp = router(d, [Fake("anthropic:y", "anthropic", fail="must not be called")], {"write": ["anthropic:y"]},
1523 | +                        record_dir=os.path.join(d, "rec"), replay=True)
1524 | +            rep = rp.call("write", "p", seed=7)
1525 | +            self.assertEqual((rep.text, rep.backend, rep.replayed), ('{"ok": 1}', "anthropic:y", True))
1526 | +            with self.assertRaises(P.ReplayMiss):
1527 | +                rp.call("write", "p", seed=8)               # another attempt is its own exchange
1528 | +
1529 | +    def test_the_spend_guard_stops_further_calls(self):
1530 | +        with tempfile.TemporaryDirectory() as d:
1531 | +            a = Fake("openai:x", "openai", answer="{}", usage={"in": 1_000_000, "out": 0})   # $10 per call
1532 | +            r = router(d, [a], {"write": ["openai:x"]}, spend_path=os.path.join(d, "SPEND.json"), limit_usd=15)
1533 | +            r.call("write", "p1")
1534 | +            r.call("write", "p2")
1535 | +            with self.assertRaises(P.SpendLimit):
1536 | +                r.call("write", "p3")
1537 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
1538 | +            self.assertEqual((led["calls"], led["by_role"]["write"]["calls"]), (2, 2))
1539 | +            self.assertAlmostEqual(led["usd_estimate"], 20.0)
1540 | +
1541 | +    def test_the_local_backend_without_its_gpu_lease_is_unavailable(self):
1542 | +        b = P.LocalBackend("local:gemma3:27b", {"model": "gemma3:27b"}, "/nonexistent", llm=None)
1543 | +        with self.assertRaises(P.Unavailable):
1544 | +            b.complete("p", 10, 7)
1545 | +
1546 | +    def test_the_shipped_config_gives_every_role_two_backends_and_names_models_only_there(self):
1547 | +        cfg = json.load(open(P.CONFIG))
1548 | +        for role, spec in cfg["roles"].items():
1549 | +            if role == "trend_brief":
1550 | +                self.assertIn("fallback", spec)              # the free local baseline is its second back-end
1551 | +                continue
1552 | +            self.assertGreaterEqual(len(spec["chain"]), 2, role)
1553 | +            for b in spec["chain"]:
1554 | +                self.assertIn(b, cfg["backends"], (role, b))
1555 | +        self.assertEqual(cfg["roles"]["mine"]["chain"][0], "local:gemma3:27b")      # Ultron first (L-x)
1556 | +        for role in ("fidelity_verdict", "context_verdict", "viewer_takeaway"):
1557 | +            writer_first = cfg["backends"][cfg["roles"]["angle_write"]["chain"][0]]["vendor"]
1558 | +            first = cfg["backends"][cfg["roles"][role]["chain"][0]]["vendor"]
1559 | +            self.assertNotEqual(first, writer_first, role)
1560 | +
1561 | +    def test_role_model_maps_failures_into_select_by_id(self):
1562 | +        import select_by_id as SB
1563 | +        with tempfile.TemporaryDirectory() as d:
1564 | +            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503")], {"story": ["openai:x"]})
1565 | +            with self.assertRaises(SB.ModelError):
1566 | +                P.RoleModel(r, "story").complete("p", 10, 7)
1567 | +            ok = router(d, [Fake("xai:z", "xai", answer='{"story": [], "claim": null}')], {"story": ["xai:z"]})
1568 | +            text, meta = P.RoleModel(ok, "story").complete("p", 10, 7)
1569 | +            self.assertEqual(meta["backend"], "xai:z")
1570 | +
1571 | +
1572 | +if __name__ == "__main__":
1573 | +    unittest.main()
1574 | 
```

---

## YOUR REVIEW TASK: MOMENTS FIRST, THEN PACKAGE, BEHIND ONE PROVIDER INTERFACE (Python pipeline, no UI, no DB)

Context: Protocol Pulse makes 60-70 s Bitcoin videos made of other channels' own words (a hook + 2-3 clips, one clip
per channel) with a PBX MAX voice-over (VO) that makes a point. Nothing is published without a human. New modules:
- pipeline/providers.py + model_providers.json: ONE interface for every model role; a back-end chain per role (local
  gemma first); failover when a vendor is down; verdict roles never on the writer's vendor; record / replay; spend guard.
- pipeline/moments.py: mines MOMENTS by sentence id (strict reply contract, never repaired), judges each by the
  eligibility predicate, ranks deterministically; an exclusion verdict (accusations, ads, imperatives...).
- pipeline/package.py: angle first: step-A context prescreen -> angles (frontier) -> line-up per angle (code: one clip
  per channel, <= 20 s, 60-70 s runtime arithmetic) -> writer -> HARD integrity gates (vo_fidelity, DUPLICATE,
  PRICE_NOW, context_integrity) -> up to 3 rewrites with the exact rejected claims -> blind COHERENCE quality verdict
  -> law L-v 2 second recognition pass (transcript_truth.py) -> a package; plain VO only as the last resort.
- pipeline/vo_fidelity.py: deterministic rules (numbers, names, quotes, attribution, relation words, framing verbs,
  imperatives, time words, PRICE_NOW) + a blind verdict whose supporting words must be verbatim runs (code-checked).
- pipeline/context_integrity.py: step A (source context only), step B (the package only), step C (entailment), the
  decision rule in code; any "uncertain" fails.
- pipeline/trend_brief.py (shadow, weight 0), transcript_truth.py, moments_gate_adapter.py (the exam's adapter),
  package_pin.py (a package as the existing PINNED decision); REQUESTS R7 (exact pinned.py patch) / R8.

The only file is the exact diff under review. Review that diff, nothing else. Only state what you can verify from the
diff shown. If uncertain, say so. Do not guess. Cite diff lines (file + the code you quote).

### Q1: FAIL-OPEN IN THE GATES
Can a package be produced (returned as "package") while ANY hard gate failed, could not run, or ran on nothing: VO
fidelity (deterministic or verdict), DUPLICATE, PRICE_NOW, context integrity (A, B, C), runtime, the second
recognition pass? Can an unreadable / partial / "uncertain" model reply ever count as a pass? Can an exception inside a
gate be swallowed into a pass? Can the plain-VO fallback ship while failing a gate?

### Q2: VENDOR SEPARATION AND L-x
Can a verdict (fidelity, context A / B / C, coherence) ever run on the SAME vendor as the writer of the text it judges
(including after a failover, a rewrite by a fallback writer, or a precomputed step A)? Does any role hard-code a
vendor or model outside model_providers.json? Does the router's failover ever turn a contract violation into "use the
next back-end silently"?

### Q3: VERBATIM AND MODEL TEXT
Can text a model wrote (a miner's reason, an angle sentence, a verdict's reason, the trend brief) reach a clip's text,
the title, the caption or the VO without passing the fidelity gate? Is every clip the source sentences verbatim?

### Q4: THE DETERMINISTIC RULES
For each rule in vo_fidelity.check_deterministic and package.duplicates / price_now / current_levels: a false PASS
(something misleading that gets through) or a false REJECT (an honest line refused)? Name concrete inputs.

### Q5: TESTS AND THE WIRING (R7)
Do the tests fail for the right reason? Any vacuous assertion? Does R7's pinned.py patch refuse an ungated or
unplaceable package, and keep a plain pin unchanged?

Output: a scored list per question (0-100), then FINDINGS: P0 / P1 / P2 with file + quoted code + a concrete failing
input, then the single highest-leverage change.

