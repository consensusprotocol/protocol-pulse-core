# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1632
# Branch: pp-selectid
# Generated: 2026-11-15 16:33 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1632/C1_STEP.diff (536 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index c071828..57c2e64 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -372,6 +372,9 @@
   6 |     "coherence_verdict:hook": [
   7 |      "xai:grok-4.20-0309-reasoning"
   8 |     ],
   9 | +   "coherence_verdict:joins": [
  10 | +    "xai:grok-4.20-0309-reasoning"
  11 | +   ],
  12 |     "coherence_verdict:clips_alone": [
  13 |      "xai:grok-4.20-0309-reasoning",
  14 |      "google:gemini-2.5-pro"
  15 | @@ -393,6 +396,9 @@
  16 |     "coherence_verdict:hook": [
  17 |      "xai:grok-4.20-0309-reasoning"
  18 |     ],
  19 | +   "coherence_verdict:joins": [
  20 | +    "xai:grok-4.20-0309-reasoning"
  21 | +   ],
  22 |     "coherence_verdict": [
  23 |      "xai:grok-4.20-0309-reasoning",
  24 |      "google:gemini-2.5-pro",
  25 | @@ -460,9 +466,13 @@
  26 |     ],
  27 |     "coherence_verdict:hook": [
  28 |      "xai:grok-4.20-0309-reasoning"
  29 | +   ],
  30 | +   "coherence_verdict:joins": [
  31 | +    "xai:grok-4.20-0309-reasoning"
  32 |     ]
  33 |    },
  34 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  35 | +  "ruling_117": "RULING 117 (orchestrator 16:24 ET Nov 15): the JOIN TABLE (package.join_table: the clips-alone verdict's join question once per ordered pair of an angle's moments) is asked of GROK alone, the calibrated rater, in every routing (no other model fills it; a pair with no answer counts as flagged in the search).",
  36 |    "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
  37 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  38 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 6be44e4..bfd9d42 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -1015,6 +1015,25 @@ MEDLEY_VERSION = hashlib.sha256(MEDLEY_PROMPT.encode()).hexdigest()[:12]
  44 |  COHERENCE_VERSION = hashlib.sha256(COHERENCE_PROMPT.encode()).hexdigest()[:12]   # valid for exactly these questions
  45 |  STANDARD_LINEUP = {"clips_alone": {"clip": COHERENCE_MIN}, "coherence": {"clip": COHERENCE_MIN,
  46 |                                                                           "vo_point": COHERENCE_MIN}}
  47 | +JOIN_QUESTION = ("could a viewer follow the jump with no narration, i.e. is the next clip's subject or referent clear "
  48 | +                 "coming from the previous clip's ending?")   # RULING 117: the clips-alone verdict's own join question
  49 | +JOINS_PROMPT = """You judge JOINS between clips of 60-second videos made of other channels' own words (each clip is a
  50 | +person's own words from a show; the shows were not in one conversation). In each PAIR, clip A plays and clip B follows
  51 | +it at once, with NO narration between them. Judge each pair ALONE: the pairs are not one video, and nothing else plays
  52 | +before or between A and B.
  53 | +
  54 | +THE CLIPS:
  55 | +{clips}
  56 | +
  57 | +THE PAIRS (A -> B):
  58 | +{pairs}
  59 | +
  60 | +For EACH pair, the join question (the previous clip is A, the next clip is B): """ + JOIN_QUESTION + """ Answer
  61 | +"followable": true or false, and "why": a few words.
  62 | +Return ONLY this JSON object: {{"pairs": {{{keys}}}}}"""
  63 | +JOINS_VERSION = hashlib.sha256(JOINS_PROMPT.encode()).hexdigest()[:12]   # a cached join is for exactly this question
  64 | +JOIN_MOMENTS_MAX = 8                 # ruling 117: the hook and its angle's other moments, at most 8 an angle
  65 | +JOIN_PAIRS_PER_CALL = 25             # pairs a call (one item a pair)
  66 |  #   the standard bar: every verdict not given by the calibrated rater, and every verdict while the file is invalid
  67 |  
  68 |  
  69 | @@ -1917,6 +1936,109 @@ def reorder(segs, bad_pairs, judged, repeat_ok=False):
  70 |      return best[1] if best else None
  71 |  
  72 |  
  73 | +def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
  74 | +    """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
  75 | +    pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
  76 | +    pair an item, JOIN_PAIRS_PER_CALL pairs a call, on coherence_verdict's "joins" list (Grok, the calibrated rater),
  77 | +    never the writers' vendor or family. Cached (`cache`, shared by every build) by the two texts and JOINS_VERSION;
  78 | +    only a back-end on today's joins list answers from it. A reply out of contract moves on (providers.call_parsed).
  79 | +    -> ({(a id, b id): {"followable", "why", "backend", "cached"}}, the first error or None). A pair no call answered has
  80 | +    no entry: the search counts it as flagged (law L-m)."""
  81 | +    import providers as P
  82 | +    ms = list(ms)[:JOIN_MOMENTS_MAX]
  83 | +    if len(ms) < 2:
  84 | +        return {}, None
  85 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  86 | +    off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  87 | +    try:
  88 | +        listed = set(router.chain("coherence_verdict", "joins"))
  89 | +    except AttributeError:                       # a stand-in router without chain(): any back-end off the writers
  90 | +        listed = None
  91 | +    except P.ProviderError:                      # no joins list: no cached join answers (fail closed)
  92 | +        listed = set()
  93 | +    key = lambda a, b: f"{text_sha(a['text'])}:{text_sha(b['text'])}:{JOINS_VERSION}"
  94 | +    cdb, out, todo = _load_cache(cache), {}, []
  95 | +    for a in ms:
  96 | +        for b in ms[1:]:
  97 | +            if a is b:
  98 | +                continue
  99 | +            rec = next((x for name, x in sorted((cdb.get(key(a, b)) or {}).items())
 100 | +                        if isinstance(x, dict) and off(name) and x.get("backend") == name and
 101 | +                        (listed is None or name in listed) and type(x.get("followable")) is bool), None)
 102 | +            if rec is not None:
 103 | +                out[(a["moment_id"], b["moment_id"])] = dict(rec, cached=True)
 104 | +            else:
 105 | +                todo.append((a, b))
 106 | +    new, err = {}, None
 107 | +    for i in range(0, len(todo), JOIN_PAIRS_PER_CALL):
 108 | +        chunk = todo[i:i + JOIN_PAIRS_PER_CALL]
 109 | +        involved = list(dict.fromkeys(m["moment_id"] for ab in chunk for m in ab))
 110 | +        cid = {mid: f"c{k + 1}" for k, mid in enumerate(involved)}
 111 | +        by = {m["moment_id"]: m for ab in chunk for m in ab}
 112 | +        clips = "\n".join(f'CLIP id="{cid[mid]}" (on screen: {CI._q(_name(by[mid], ctx), 80)}): '
 113 | +                          f'"{CI._q(by[mid]["text"], 900)}"' for mid in involved)
 114 | +        pids = {f"p{k + 1}": ab for k, ab in enumerate(chunk)}
 115 | +        pairs = "\n".join(f'PAIR id="{p}": {cid[a["moment_id"]]} -> {cid[b["moment_id"]]}' for p, (a, b) in pids.items())
 116 | +        keys = ", ".join(f'"{p}": {{"followable": true, "why": "..."}}' for p in pids)
 117 | +
 118 | +        def parse(text, want=frozenset(pids)):
 119 | +            v = json.loads(text.strip())
 120 | +            h = v["pairs"] if isinstance(v, dict) and set(v) == {"pairs"} else None
 121 | +            if not isinstance(h, dict) or set(h) != set(want) or any(
 122 | +                    not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 123 | +                    or not isinstance(x["why"], str) for x in h.values()):
 124 | +                raise ValueError("join table out of contract")
 125 | +            return h
 126 | +        try:
 127 | +            r, h = P.call_parsed(router, "coherence_verdict", JOINS_PROMPT.format(clips=clips, pairs=pairs, keys=keys),
 128 | +                                 parse, 400 + 60 * len(chunk), seed, avoid_vendor=writer_vendor,
 129 | +                                 avoid_family=writer_family, kind="joins")
 130 | +        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # these pairs have no entry
 131 | +            err = err or f"{type(e).__name__}: {str(e)[:200]}"
 132 | +            continue
 133 | +        for p, (a, b) in pids.items():
 134 | +            rec = {"followable": h[p]["followable"], "why": h[p]["why"][:200], "backend": r.backend}
 135 | +            out[(a["moment_id"], b["moment_id"])] = dict(rec, cached=False)
 136 | +            new[key(a, b)] = {r.backend: rec}
 137 | +    _cache_put(cache, new)
 138 | +    return out, err
 139 | +
 140 | +
 141 | +def search_lineups(angle, by_id, table, dropped=frozenset(), judged=(), bad_pairs=frozenset(), ratings=None,
 142 | +                   floor=None, repeat_ok=False):
 143 | +    """RULING 117 (2): the line-ups of `angle` chosen BY SEARCH over the join table, no model call. Hook first (the
 144 | +    angle's own, ruling 59 c), then 2-4 of its other moments (not dropped; at most JOIN_MOMENTS_MAX in all) in EVERY
 145 | +    order, under every line-up rule as now (lineup_ok: can open, clip-eligible, one per channel or the supply exception,
 146 | +    price predictions, a short clip only last, the seconds, the render's STAND_ALONE), not judged yet, and at most
 147 | +    LY_MAX_BRIDGES flagged joins: a join is flagged when the table finds it unfollowable, when the table has no answer
 148 | +    for it, or when a verdict of this build flagged it (bad_pairs). Best first: the fewest flagged joins, then the
 149 | +    highest clip ratings (`ratings`: each clip's clips-alone rating in this angle's verdicts so far; a clip not rated
 150 | +    yet counts at `floor`): the lowest, then the mean; then the writer's play order kept. -> [segs, ...]."""
 151 | +    h = by_id.get(angle["hook"])
 152 | +    if h is None or angle["hook"] in dropped:
 153 | +        return []
 154 | +    ratings, floor = ratings or {}, COHERENCE_MIN if floor is None else floor
 155 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 156 | +    others = [by_id[m] for m in angle["moments"] if m != angle["hook"] and m in by_id and m not in dropped]
 157 | +    others = others[:JOIN_MOMENTS_MAX - 1]
 158 | +    flagged = lambda a, b: (a, b) in bad_pairs or (table.get((a, b)) or {}).get("followable") is not True
 159 | +    cands = []
 160 | +    for n in range(LY_CLIPS[0], LY_CLIPS[1] + 1):
 161 | +        for perm in itertools.permutations(others, n):
 162 | +            segs = [h, *perm]
 163 | +            ids = tuple(m["moment_id"] for m in segs)
 164 | +            if ids in judged:
 165 | +                continue
 166 | +            nf = sum(flagged(a, b) for a, b in zip(ids, ids[1:]))
 167 | +            if nf > LY_MAX_BRIDGES or not lineup_ok(segs, repeat_ok=repeat_ok)[0]:
 168 | +                continue
 169 | +            rs = [ratings.get(m["moment_id"], floor) for m in perm]
 170 | +            moves = sum(abs(pos.get(m["moment_id"], 99) - k) for k, m in enumerate(perm, 1))
 171 | +            cands.append(((nf, -min(rs), -sum(rs) / len(rs), moves), segs))
 172 | +    cands.sort(key=lambda x: x[0])
 173 | +    return [s for _, s in cands]
 174 | +
 175 | +
 176 |  def allot(angles, per):
 177 |      """RULING 64 (12:00): at most `per` angles per hook, in the writer's order (the excess is dropped, recorded)."""
 178 |      seen, out = {}, []
 179 | @@ -2574,6 +2696,7 @@ def candidate_lineup(router, candidate, cleared, now):
 180 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 181 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 182 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 183 | +          join_cache=None,
 184 |            visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
 185 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 186 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 187 | @@ -2582,6 +2705,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 188 |      work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 189 |      spend: a callable returning the ledger's USD (dollars per package).
 190 |      step_a_cache / hook_cache (rulings 58 / 59): the verdict caches every build shares (None: this build's only).
 191 | +    join_cache (RULING 117): the join table's cache, shared the same way. RULING 117, SEARCH, DO NOT LOOSEN: each angle's
 192 | +    join table (join_table: the join question once per ordered pair of its moments, Grok) is built before its first
 193 | +    line-up; the line-ups are then chosen BY SEARCH over it (search_lineups: hook first, 2-4 clips in every order, the
 194 | +    rules as now, at most one flagged join), the first and, after each failed verdict, the next; the clips-alone and
 195 | +    coherence verdicts still decide every line-up. With no table (the call failed or no entry) or no line-up left in
 196 | +    the search, the line-up is chosen as before (lineup_for, then rulings 62 / 63 / 41).
 197 |      scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 198 |      render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 199 |      RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 200 | @@ -3136,6 +3265,18 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 201 |      with ThreadPoolExecutor(max_workers=8) as pool:
 202 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 203 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 204 | +            jt, a_ratings = {}, {}                        # RULING 117: this angle's join table; its clips' ratings
 205 | +            if candidate is None:
 206 | +                jms = [cleared[m] for m in [angle["hook"], *[x for x in angle["moments"] if x != angle["hook"]]]
 207 | +                       if m in cleared and m not in doomed][:JOIN_MOMENTS_MAX]
 208 | +                jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
 209 | +                out.setdefault("join_tables", []).append(
 210 | +                    {"angle": ai + 1, "moments": [m["moment_id"] for m in jms], "error": jt_err,
 211 | +                     "pairs": {f"{a} -> {b}": {"followable": x["followable"], "why": x["why"], "cached": x["cached"]}
 212 | +                               for (a, b), x in jt.items()}})
 213 | +                log(f"  angle {ai + 1}: join table (ruling 117) {len(jt)} pair(s) of {len(jms)} moments, "
 214 | +                    f"{sum(x['followable'] is not True for x in jt.values())} not followable"
 215 | +                    + (f"; NOT ASKED: {jt_err}" if jt_err else "") + f" ({time.time() - t0:.0f} s)")
 216 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 217 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 218 |              while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 219 | @@ -3148,6 +3289,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 220 |                      segs, swapped = swapped, None
 221 |                      exception = supply_exception(segs, ctx)
 222 |                  else:
 223 | +                    segs, filled = None, None
 224 | +                    if jt:                                # RULING 117: chosen by search over the join table
 225 | +                        found = search_lineups(angle, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 226 | +                                               a_ratings, lineup_floors("clips_alone", None)[0]["clip"]) or \
 227 | +                            search_lineups(angle, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 228 | +                                           a_ratings, lineup_floors("clips_alone", None)[0]["clip"], repeat_ok=True)
 229 | +                        segs = found[0] if found else None
 230 | +                        exception = supply_exception(segs, ctx) if segs is not None else None
 231 | +                if swapped is None and segs is None:      # no table, or the search has nothing: as before
 232 |                      segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 233 |                                                   need_stand_alone=True, now=ctx.now, hook_only=True), None
 234 |                      if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
 235 | @@ -3194,6 +3344,19 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 236 |                      judged[key] = (ok_m, med)
 237 |                      total += 0 if med.get("replayed") or med.get("cached") else 1   # 12:00: JUDGED line-ups
 238 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 239 | +                if jt and med.get("measured"):            # RULING 117 (3): the table's joins against the verdict's
 240 | +                    ids_ = [m["moment_id"] for m in segs]
 241 | +                    cmp_ = {j: {"table": (jt.get((a, b)) or {}).get("followable"),
 242 | +                                "verdict": (med.get("joins") or {}).get(j, {}).get("followable")}
 243 | +                            for j, (a, b) in zip(joins(labels(len(segs))), zip(ids_, ids_[1:]))}
 244 | +                    rec["join_table_vs_verdict"] = cmp_
 245 | +                    ag = out.setdefault("join_agreement", {"joins": 0, "agree": 0, "table_unanswered": 0})
 246 | +                    for x in cmp_.values():
 247 | +                        if x["table"] is None:
 248 | +                            ag["table_unanswered"] += 1
 249 | +                        else:
 250 | +                            ag["joins"] += 1
 251 | +                            ag["agree"] += x["table"] == x["verdict"]
 252 |                  labs_ = labels(len(segs))
 253 |                  bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
 254 |                                for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}   # ruling 63
 255 | @@ -3204,6 +3367,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 256 |                  if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
 257 |                      rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
 258 |                      break
 259 | +                if not ok_m and jt and med.get("measured"):   # RULING 117: the search over the table picks the next
 260 | +                    floor_ = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
 261 | +                    for lb_, mm in zip(labs[1:], segs[1:]):
 262 | +                        x = (med.get("clips") or {}).get(lb_)
 263 | +                        if type(x) is int:
 264 | +                            a_ratings[mm["moment_id"]] = max(x, a_ratings.get(mm["moment_id"], 0))
 265 | +                            if x < floor_:                # a clip under this verdict's floor leaves the search
 266 | +                                dropped.add(mm["moment_id"])
 267 | +                    found = search_lineups(angle, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs,
 268 | +                                           a_ratings, floor_) or \
 269 | +                        search_lineups(angle, cleared, jt, frozenset(dropped | doomed), judged, bad_pairs, a_ratings,
 270 | +                                       floor_, repeat_ok=True)
 271 | +                    if found:
 272 | +                        swapped = found[0]
 273 | +                        rec["why"] = (f"ruling 117: the clips alone fail ({med.get('clips')}, flagged "
 274 | +                                      f"{med.get('flagged')}): the join table's search gives the next line-up "
 275 | +                                      f"{[m['moment_id'] for m in swapped]}")
 276 | +                        continue
 277 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 278 |                      by_lab = dict(zip(labs, segs))
 279 |                      cl = med.get("clips") or {}
 280 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 281 | index e4d2206..7f683f5 100644
 282 | --- a/tests/package/proof_ledger.py
 283 | +++ b/tests/package/proof_ledger.py
 284 | @@ -474,6 +474,7 @@ def main(argv=None):
 285 |                spend=lambda: (own["est"], own["best"]),
 286 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 287 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 288 | +              join_cache=os.path.join(HERE, "proof", "JOIN_CACHE.json"),          # ruling 117: cached
 289 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 290 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 291 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 292 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 293 | index 62c59db..9eda8aa 100644
 294 | --- a/tests/package/test_medley.py
 295 | +++ b/tests/package/test_medley.py
 296 | @@ -552,8 +552,9 @@ class Rig:
 297 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 298 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 299 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 300 | -                 real_value=False, caption=None, coherences=None):
 301 | +                 real_value=False, caption=None, coherences=None, joins=None):
 302 |          import providers as P
 303 | +        self.joins, self.join_calls = joins, []           # RULING 117: {(a, b): followable}; None = no table (as before)
 304 |          self.coherences = list(coherences or [])         # RULING 116: (ok, every clip's rating, the VO point) in order
 305 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 306 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 307 | @@ -631,6 +632,20 @@ class Rig:
 308 |                                     "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 309 |          return out, None
 310 |  
 311 | +    def join_table(self, router, ms, ctx_, wv, wf=None, cache=None, seed=7):
 312 | +        """Ruling 117 as the real join_table answers: every ordered pair of `ms` (the hook never B) the rig knows
 313 | +        (self.joins), followable or not; a pair it does not know is not answered. None: no table at all."""
 314 | +        self.join_calls.append([m["moment_id"] for m in ms])
 315 | +        if self.joins is None:
 316 | +            return {}, None
 317 | +        out = {}
 318 | +        for a in ms:
 319 | +            for b in ms[1:]:
 320 | +                if a is not b and (a["moment_id"], b["moment_id"]) in self.joins:
 321 | +                    out[(a["moment_id"], b["moment_id"])] = {"followable": self.joins[(a["moment_id"], b["moment_id"])],
 322 | +                                                             "why": "w", "backend": "xai:grok", "cached": False}
 323 | +        return out, None
 324 | +
 325 |      def coherence(self, router, pk, *a, **k):
 326 |          """As the real coherence() answers: the clips after the hook and the VO point (self.coherences, default all 5
 327 |          and a pass), the hook's slot its own rating, and the line-up bar it was judged on (ruling 116)."""
 328 | @@ -728,6 +743,7 @@ class Rig:
 329 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 330 |              "hook_onset_for": self.onset,
 331 |              "hook_ratings": self.rate_hooks,
 332 | +            "join_table": self.join_table,
 333 |              "takeaway_value": self.value,                  # ruling 91 (medley half)
 334 |              "coherence": self.coherence,
 335 |          }
 336 | @@ -1709,6 +1725,199 @@ class TestRuling116LineupBar(unittest.TestCase):
 337 |          self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 338 |  
 339 |  
 340 | +class TestRuling117JoinSearch(unittest.TestCase):
 341 | +    """RULING 117 (orchestrator 16:24 ET Nov 15), SEARCH, DO NOT LOOSEN: the join table (the clips-alone verdict's own
 342 | +    join question once per ordered pair of an angle's moments, Grok, cached) and the line-ups chosen BY SEARCH over it
 343 | +    (hook first, 2-4 clips in every order, the rules as now, at most one flagged join); the verdicts still decide."""
 344 | +
 345 | +    def canned(self, *replies):
 346 | +        c = Canned(coherence_verdict=list(replies))
 347 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 348 | +        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
 349 | +        return c
 350 | +
 351 | +    @staticmethod
 352 | +    def all_pairs(prompt, followable=True):
 353 | +        ids = re.findall(r'PAIR id="(p\d+)"', prompt)
 354 | +        return {"pairs": {p: {"followable": followable, "why": "w"} for p in ids}}
 355 | +
 356 | +    def test_the_question_is_the_clips_alone_verdicts_own(self):
 357 | +        self.assertIn(PK.JOIN_QUESTION, " ".join(PK.MEDLEY_PROMPT.split()))   # ONE join question
 358 | +        self.assertIn(PK.JOIN_QUESTION, PK.JOINS_PROMPT)
 359 | +
 360 | +    def test_once_per_ordered_pair_the_hook_never_second_batched_and_cached(self):
 361 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 362 | +        prompts = []
 363 | +        c = self.canned()
 364 | +        import providers as P
 365 | +
 366 | +        def call(role, prompt, *a, **k):
 367 | +            prompts.append(prompt)
 368 | +            c.calls.append((role, k.get("avoid_vendor"), k.get("avoid_family"), k.get("kind")))
 369 | +            return P.Reply(json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake")
 370 | +        c.call = call
 371 | +        with tempfile.TemporaryDirectory() as d:
 372 | +            cache = os.path.join(d, "JOIN_CACHE.json")
 373 | +            got, err = PK.join_table(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 374 | +            self.assertIsNone(err)
 375 | +            self.assertEqual(sorted(got), [("h", "x"), ("h", "y"), ("x", "y"), ("y", "x")])   # 4 pairs, no (.., h)
 376 | +            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"}, "joins")])   # one call
 377 | +            self.assertIn(PK.JOIN_QUESTION, prompts[0])
 378 | +            again, err = PK.join_table(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 379 | +            self.assertEqual((err, len(again), all(x["cached"] for x in again.values())), (None, 4, True))   # no call
 380 | +            prompts.clear()
 381 | +            c.calls.clear()
 382 | +            new = [ms[0], dict(ms[1], text="Bitcoin is a new text now."), ms[2]]
 383 | +            got, _ = PK.join_table(c, new, ctx(), set(), set(), cache=cache)
 384 | +            self.assertEqual(len(re.findall(r'PAIR id=', prompts[0])), 3)       # only the pairs with the new text
 385 | +        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(9)]
 386 | +        prompts.clear()
 387 | +        c.calls.clear()
 388 | +        got, _ = PK.join_table(c, big, ctx(), set(), set())
 389 | +        self.assertEqual((len(got), len(prompts)), (49, 2))                     # 8 moments: 49 pairs in 25 + 24
 390 | +
 391 | +    def test_a_chunk_out_of_contract_has_no_entries_and_the_others_are_still_asked(self):
 392 | +        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(8)]
 393 | +        import providers as P
 394 | +        c, n = self.canned(), [0]
 395 | +
 396 | +        def call(role, prompt, *a, **k):
 397 | +            n[0] += 1
 398 | +            if n[0] == 1:
 399 | +                raise P.ProviderError("coherence_verdict: every back-end unavailable")
 400 | +            return P.Reply(json.dumps(self.all_pairs(prompt, False)), "fake:coherence_verdict", "fake")
 401 | +        c.call = call
 402 | +        got, err = PK.join_table(c, big, ctx(), set(), set())
 403 | +        self.assertEqual((len(got), "ProviderError" in err), (24, True))       # the second chunk only
 404 | +        self.assertTrue(all(x["followable"] is False for x in got.values()))
 405 | +
 406 | +    def moments(self):
 407 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
 408 | +        return {m["moment_id"]: m for m in (h, pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 6.0))}
 409 | +
 410 | +    def test_the_search_every_order_the_rules_and_at_most_one_flagged_join(self):
 411 | +        by = self.moments()
 412 | +        a = angle(["h", "x", "y", "z"], "h")
 413 | +        T = lambda ok: {"followable": ok}
 414 | +        table = {(p, q): T(True) for p in "hxyz" for q in "xyz" if p != q}
 415 | +        table[("h", "x")] = T(False)
 416 | +        table[("x", "y")] = T(False)                                          # the writer's order: two flagged
 417 | +        got = PK.search_lineups(a, by, table)
 418 | +        self.assertTrue(got)
 419 | +        best = [m["moment_id"] for m in got[0]]
 420 | +        self.assertEqual(best[0], "h")                                       # the hook first
 421 | +        ids = [[m["moment_id"] for m in s] for s in got]
 422 | +        self.assertNotIn(["h", "x", "y", "z"], ids)                          # two flagged: never offered
 423 | +        for s in ids:
 424 | +            self.assertLessEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:])), 1)
 425 | +            self.assertTrue(PK.lineup_ok([by[i] for i in s])[0])              # the rules as now
 426 | +            self.assertNotIn("z", s[1:-1])                                    # z is short (6 s): only last
 427 | +        self.assertEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(best, best[1:])), 0)
 428 | +        del table[("y", "z")]                                                # no answer counts as flagged
 429 | +        self.assertTrue(all(sum((p, q) == ("y", "z") or table.get((p, q), {}).get("followable") is not True
 430 | +                                for p, q in zip(s, s[1:])) <= 1 for s in
 431 | +                            [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table)]))
 432 | +        judged = {tuple(best)}
 433 | +        self.assertNotIn(best, [[m["moment_id"] for m in s] for s in PK.search_lineups(a, by, table, judged=judged)])
 434 | +        self.assertFalse([s for s in PK.search_lineups(a, by, table, dropped=frozenset({"x", "y"}))])   # 1 clip left
 435 | +        bp = {("h", "y")}                                                    # a verdict flagged it: it counts
 436 | +        for s in [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table, bad_pairs=bp)]:
 437 | +            n_bad = sum((p, q) in bp or table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:]))
 438 | +            self.assertLessEqual(n_bad, 1)
 439 | +
 440 | +    def test_an_unanswered_pair_and_a_verdicts_flag_each_count_as_flagged(self):
 441 | +        by = dict(self.moments(), z=pm("z", "D", 13.0))
 442 | +        a = angle(["h", "x", "y", "z"], "h")
 443 | +        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
 444 | +        ids = lambda got: [[m["moment_id"] for m in s] for s in got]
 445 | +        self.assertEqual(ids(PK.search_lineups(a, by, table))[0], ["h", "x", "y"])   # the writer's order first
 446 | +        t2 = dict(table)
 447 | +        t2[("h", "x")] = {"followable": False}
 448 | +        del t2[("x", "y")]                                                   # no answer for x -> y
 449 | +        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, t2)))       # flagged + unanswered: 2
 450 | +        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, table, bad_pairs={("h", "x"), ("x", "y")})))
 451 | +
 452 | +    def test_the_search_prefers_higher_known_ratings(self):
 453 | +        by = dict(self.moments(), z=pm("z", "D", 13.0))                      # z long enough to stand in for y
 454 | +        a = angle(["h", "x", "y", "z"], "h")
 455 | +        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
 456 | +        got = PK.search_lineups(a, by, table, ratings={"x": 5, "y": 2}, floor=3)
 457 | +        self.assertNotIn("y", [m["moment_id"] for m in got[0]])              # a 2 ranks below the unknown z
 458 | +
 459 | +    def test_a_build_asks_the_searchs_line_up_first_and_records_the_agreement(self):
 460 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 461 | +        joins = {("h", "x"): False, ("x", "y"): False, ("h", "y"): True, ("y", "x"): True}
 462 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
 463 | +        out = rig.run()
 464 | +        self.assertEqual(rig.medley_calls, [["h", "y", "x"]])                  # the table's order, not the writer's
 465 | +        self.assertEqual(rig.join_calls, [["h", "x", "y"]])
 466 | +        self.assertEqual(out["tried"][0]["join_table_vs_verdict"],
 467 | +                         {"hook -> clip_01": {"table": True, "verdict": True},
 468 | +                          "clip_01 -> clip_02": {"table": True, "verdict": True}})
 469 | +        self.assertEqual(out["join_agreement"], {"joins": 2, "agree": 2, "table_unanswered": 0})
 470 | +        self.assertEqual(out["join_tables"][0]["moments"], ["h", "x", "y"])
 471 | +        self.assertIsNotNone(out["package"])
 472 | +
 473 | +    def test_after_a_failed_verdict_the_search_gives_the_next_line_up(self):
 474 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 475 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 476 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
 477 | +                                             (True, [], None, Rig.LINE)], [None], joins=joins)
 478 | +        out = rig.run()
 479 | +        first, second = rig.medley_calls                                      # the search's shortest first: h x y
 480 | +        self.assertEqual(first, ["h", "x", "y"])
 481 | +        self.assertIn("ruling 117", out["tried"][0]["why"])
 482 | +        flagged = {("h", "x"), ("x", "y")}                                    # the verdict's flags count as flagged
 483 | +        self.assertEqual(sum(p in flagged for p in zip(second, second[1:])), 0)   # the next has neither
 484 | +        self.assertIsNotNone(out["package"])
 485 | +
 486 | +    def test_the_cache_answers_only_for_todays_joins_list(self):
 487 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0)]
 488 | +        import providers as P
 489 | +        c = self.canned()
 490 | +        c.call = lambda role, prompt, *a, **k: (c.calls.append(role), P.Reply(
 491 | +            json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake"))[1]
 492 | +        c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
 493 | +        with tempfile.TemporaryDirectory() as d:
 494 | +            cache = os.path.join(d, "JOIN_CACHE.json")
 495 | +            PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 496 | +            c.calls.clear()
 497 | +            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 498 | +            self.assertEqual((c.calls, got[("h", "x")]["cached"]), ([], True))     # on the list: served
 499 | +            c.chain = lambda role, kind=None: ["xai:another-rater"]
 500 | +            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
 501 | +            self.assertEqual((len(c.calls), got[("h", "x")]["cached"]), (1, False))   # off it: asked again
 502 | +
 503 | +    def test_a_clip_under_the_verdicts_floor_leaves_the_search(self):
 504 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 505 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 506 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
 507 | +                  [None], joins=joins)
 508 | +        out = rig.run()
 509 | +        first, second = rig.medley_calls
 510 | +        self.assertEqual(first[1], "x")                                      # x rated 2 on the calibrated bar
 511 | +        self.assertNotIn("x", second)                                         # out of every later line-up
 512 | +        self.assertIn("ruling 117", out["tried"][0]["why"])
 513 | +
 514 | +    def test_clips_under_a_verdicts_floor_never_come_back_when_the_search_runs_out(self):
 515 | +        """x, then y, rated 2: each leaves the search; with neither, no line-up of 2-4 clips is left, so no third
 516 | +        verdict is asked (with them kept, the search would ask a line-up holding a clip already rated 2)."""
 517 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 518 | +        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
 519 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (False, [], {"clip_01": 2}, Rig.LINE),
 520 | +                                             (True, [], None, Rig.LINE)], [None], joins=joins)
 521 | +        rig.run()
 522 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])
 523 | +
 524 | +    def test_no_table_or_an_empty_one_is_the_build_as_before(self):
 525 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 526 | +        for joins in (None, {}):
 527 | +            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
 528 | +            out = rig.run()
 529 | +            self.assertEqual(rig.medley_calls, [["h", "x", "y"]])              # the writer's order
 530 | +            self.assertNotIn("join_agreement", out)
 531 | +
 532 | +
 533 |  class TestRuling56Scorer(unittest.TestCase):
 534 |      """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 535 |      about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
 536 | 
```

---

pp-selectid: RULING 117 (orchestrator 16:24 ET Nov 15), THE JOINS: SEARCH, DO NOT LOOSEN (2)+(3). Files:
pipeline/package.py (join_table, search_lineups, JOIN_QUESTION / JOINS_PROMPT, build()'s angle loop),
pipeline/model_providers.json (the joins list), tests/package/proof_ledger.py (the join cache), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) BUILD THE JOIN TABLE: for the moments that can be in a line-up for an angle (the hook and the
clips that passed step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle), ask ONCE per ordered
pair 'coming from the end of A, is B's subject or referent clear with no narration' (the join question as it stands,
one pair per item, batched in one call where the contract allows; Grok, the calibrated rater; cached by the two texts).
Then choose the order BY SEARCH over the table: hook first, 2-4 clips, the seconds and channel rules as now, at most one
flagged join, highest clip ratings first. No model call in the search. (3) THE FULL VERDICT STILL DECIDES: the chosen
line-up goes through the clips-alone and coherence verdicts unchanged (calibrated bars); the table only picks what to
ask them. Report how often the table's joins and the full verdict's joins agree." The join law does NOT move (one
bridge).

THE CHANGE:
- JOIN_QUESTION: the clips-alone verdict's own join sentence (a test checks it is in MEDLEY_PROMPT, white space
  normalized; MEDLEY_PROMPT itself is unchanged, so the line-up calibration's version stands). JOINS_PROMPT: the
  moments once ("CLIP id=c1 ..."), the pairs ("PAIR id=p1: c1 -> c3"), the question per pair, one item a pair:
  {"pairs": {"p1": {"followable": bool, "why": str}}}.
- join_table(router, ms, ...): ms = the angle's hook then its other moments that are in `cleared` (cleared = the
  build's moments that passed step A from both vendors, the second pass and CUTTABLE) and not doomed, at most 8. Every
  ordered pair with the hook never second (8 moments: 49 pairs), 25 pairs a call, coherence_verdict kind "joins"
  (Grok ALONE in every routing: model_providers.json), off the writers. Cached by the two texts' sha and JOINS_VERSION
  (JOIN_CACHE.json), served only from a back-end on today's joins list; an out-of-contract chunk moves on
  (call_parsed) and leaves its pairs unanswered; the others are still asked.
- search_lineups(angle, by_id, table, dropped, judged, bad_pairs, ratings, floor, repeat_ok): the angle's own hook
  first, then 2-4 of its other moments in EVERY order; kept only when lineup_ok passes (the rules as now: can open,
  clip-eligible, one per channel or the supply exception, price predictions, trimmed clips, a clip under 8 s only
  last, the seconds window, the render's STAND_ALONE), not judged yet, and at most LY_MAX_BRIDGES flagged joins, where
  a join is flagged when the table says not followable, when the table has NO answer for it, or when a verdict of
  this build flagged it. Best first: fewest flagged joins, then the clips' known ratings (lowest, then mean; a clip not
  rated yet counts at the floor), then the writer's play order (fewest moves). No model call.
- build(): per angle (not for a ruling-66 candidate), the table is asked once, before its first line-up, and recorded
  (out["join_tables"]). A fresh line-up is the search's best (one channel per segment first, then the supply
  exception); after a failed clips-alone verdict, its clips' ratings are kept, a clip under THAT verdict's floor leaves
  the angle (dropped), and the search's next line-up is asked (rec["why"] names ruling 117). With no table (the call
  failed, or no pair answered) or nothing left in the search, the build goes on exactly as before (lineup_for, then
  rulings 62 / 63 / 41). Every judged line-up records its joins as the table had them against the verdict
  (rec["join_table_vs_verdict"]); out["join_agreement"] counts agree / joins / unanswered.

UNCHANGED GUARDS: medley() / coherence() decide every line-up (their prompts, floors and marks unchanged);
LINEUPS_PER_BUILD (8 judged line-ups a build) and the spins guard bound the loop; lineup_ok
(pipeline/package.py, "def lineup_ok"); _load_cache / _cache_put (None: neither read nor written); call_parsed.

TESTS (test_medley TestRuling117JoinSearch, 12): the question is the verdict's own; once per ordered pair, the hook
never second, one call, off the writers, kind "joins", cached by texts (a changed text re-asks only its pairs); 49
pairs in 2 calls; a failed chunk leaves only its pairs unanswered; the cache only for today's joins list; the search:
every order under lineup_ok, never two flagged, a short clip only last, judged / dropped excluded, an unanswered pair
and a verdict's flag each count as flagged, known ratings rank; the build asks the search's line-up first, records
the agreement, takes the search's next after a failure, drops a clip under the verdict's floor (and asks no third
verdict once the search runs out), and with no table or an empty one is the build as before. All 40 suite files pass
(805 + 4 tests). Mutations after a control run: 14 of 14 killed.

PLEASE CHECK: (1) that nothing about the join law or the verdicts moved (one bridge; the verdicts decide); (2) that
the search applies exactly lineup_for's rules (via lineup_ok) and counts unanswered pairs as flagged; (3) the
build's fallbacks (no table, no candidates) keep today's behaviour; (4) the cache and the contract; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
