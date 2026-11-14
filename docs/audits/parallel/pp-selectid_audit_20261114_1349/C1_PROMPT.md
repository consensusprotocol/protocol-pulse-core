# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_1349
# Branch: pp-selectid
# Generated: 2026-11-14 13:59 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_1349/C1_STEP.diff (918 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index ede12b2..535c340 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -168,14 +168,14 @@
   6 |     ],
   7 |     "min_out": 8000,
   8 |     "timeout_s": 300,
   9 | -   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled."
  10 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled. RULING 102 (13:02 Nov 14): also step A's second family after Heimdall's deepseek and glm, reached without declaring Heimdall down (probed 12:5x ET Nov 14: answered in 2.2 s)."
  11 |    },
  12 |    "local_judge:gemma3:27b": {
  13 |     "vendor": "local_judge",
  14 |     "model": "gemma3:27b",
  15 |     "family": "gemma",
  16 |     "deadline_floor_s": 2400,
  17 | -   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min."
  18 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min. RULING 102 (13:02 Nov 14): also the LAST leg of step A's second family (ruling 87's last resort), reached without declaring Heimdall down; recorded as such on the pin and on STATE line 1."
  19 |    }
  20 |   },
  21 |   "roles": {
  22 | @@ -359,8 +359,10 @@
  23 |     ],
  24 |     "context_verdict:step_a_second": [
  25 |      "xai:grok-4.20-0309-reasoning",
  26 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  27 |      "heimdall:z-ai/glm-5.3-flash",
  28 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  29 | +    "google:gemini-2.5-pro",
  30 | +    "local_judge:gemma3:27b"
  31 |     ],
  32 |     "context_verdict:step_c": [
  33 |      "xai:grok-4.20-0309-reasoning",
  34 | @@ -459,6 +461,7 @@
  35 |    },
  36 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  37 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  38 | -  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged."
  39 | +  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
  40 | +  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
  41 |   }
  42 |  }
  43 | diff --git a/pipeline/package.py b/pipeline/package.py
  44 | index 7825b27..395f35a 100644
  45 | --- a/pipeline/package.py
  46 | +++ b/pipeline/package.py
  47 | @@ -444,6 +444,38 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
  48 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
  49 |  
  50 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
  51 | +HELD = "STEP_A_HELD (ruling 102)"   # RULING 102 (13:02 Nov 14): no leg ANSWERED: held for THIS build, never refused, never
  52 | +LAST_RESORT = "local_judge:"       # cached, retried next build. The local judge's verdicts: ruling 87's last resort,
  53 | +#                                    recorded as such on the pin (last_resort_note: the medley's context_a row, the
  54 | +#                                    spotlight's step_a_two_families row) and on STATE line 1 (the build's line)
  55 | +
  56 | +
  57 | +def held_why(e):
  58 | +    """RULING 102: the reason a step-A call that gave no verdict leaves on its moments: HELD for this build, retried
  59 | +    next build (every leg unavailable, past its deadline, breaker-open, refused or out of contract; ruling 48's cap; any
  60 | +    error of the call), never a refusal. The one exception is the moment's own context: CONTEXT_TOO_LONG (law L-s never
  61 | +    truncates a window, so no retry can answer it) -> STEP_A_REFUSED."""
  62 | +    if isinstance(e, ValueError) and str(e).startswith("CONTEXT_TOO_LONG"):
  63 | +        return f"STEP_A_REFUSED: {str(e)[:200]}"
  64 | +    return f"{HELD}: no step-A verdict ({type(e).__name__}: {str(e)[:160]}); held for this build, retried next build"
  65 | +
  66 | +
  67 | +def is_held(why):
  68 | +    """RULING 102: a moment's step-A reasons say HELD (no answer), not a verdict's refusal."""
  69 | +    return bool(why) and all(str(w).startswith(HELD) for w in why)
  70 | +
  71 | +
  72 | +def last_resort_of(verdicts):
  73 | +    """RULING 102: the back-ends among `verdicts` (A items) that are the local judge's (ruling 87's last resort)."""
  74 | +    return sorted({str(a.get("backend")) for a in verdicts or () if isinstance(a, dict)
  75 | +                   and str(a.get("backend")).startswith(LAST_RESORT)})
  76 | +
  77 | +
  78 | +def last_resort_note(by):
  79 | +    """RULING 102: the pin's record of the local judge's step-A verdicts ({label or moment id: back-end}), or None."""
  80 | +    return {"rule": "ruling 87's last resort (ruling 102): no faster leg of step A's second family answered, so the "
  81 | +                    "local gemma3:27b on GPU0 (the integrator's judge service) gave this step-A verdict",
  82 | +            "verdicts": dict(sorted(by.items()))} if by else None
  83 |  
  84 |  
  85 |  def _load_store(store):
  86 | @@ -556,9 +588,9 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  87 |          res = list(ex.map(lambda ic: screen(*ic), enumerate(chunks)))   # map keeps the chunks' order: zipped below
  88 |      new = {}
  89 |      for chunk, (got, e) in zip(chunks, res):
  90 | -        if got is None:
  91 | +        if got is None:                                 # ruling 102: no answer is HELD, never a refusal, never cached
  92 |              for m in chunk:
  93 | -                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:160]}"]
  94 | +                fails[m["moment_id"]] = [held_why(e)]
  95 |              continue
  96 |          items, backend = got
  97 |          b = router.backends.get(backend)
  98 | @@ -618,6 +650,28 @@ def _heimdall(b):
  99 |      return P.gateway(b) == "heimdall"
 100 |  
 101 |  
 102 | +CONFIRM_VENDOR = "xai"             # RULING 101: "Grok's confirm", the one vendor the confirm-ahead asks (ruling 102's
 103 | +#                                    Gemini and the local judge are the second screen's fallbacks, never asked ahead)
 104 | +
 105 | +
 106 | +def _usable(router, name, wv, wf):
 107 | +    """A leg a live call could take now: in the router, off the writers, not down this run, not breaker-open."""
 108 | +    b = router.backends.get(name)
 109 | +    return b is not None and b.vendor not in set(wv) and b.family not in set(wf) and \
 110 | +        name not in getattr(router, "down", {}) and not (hasattr(router, "breaker_open") and router.breaker_open(name))
 111 | +
 112 | +
 113 | +def _confirm_leg(router, wv, wf):
 114 | +    """RULING 101 (glm, audit 20261114_1246 C2 H1): the leg Grok's confirm-ahead would ask: the step_a_second chain's
 115 | +    first xAI back-end that is usable now; None when there is none (Grok writes, is down or breaker-open), and then a
 116 | +    confirm-ahead could ask nothing: the plan is sequential."""
 117 | +    for name in router.chain("context_verdict", kind="step_a_second"):
 118 | +        b = router.backends.get(name)
 119 | +        if b is not None and b.vendor == CONFIRM_VENDOR and _usable(router, name, wv, wf):
 120 | +            return name
 121 | +    return None
 122 | +
 123 | +
 124 |  def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **first):
 125 |      """RULING 101 (12:16 Nov 14): does step A ask the Heimdall filter and Grok's confirm IN PARALLEL? Yes when more than
 126 |      STEP_A_PARALLEL_NEW moments are NEW to the first screen (no verdict in this build's ledger or the shared cache) AND
 127 | @@ -625,25 +679,30 @@ def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **firs
 128 |      PRESCREEN_WORKERS) x the deadline of the filter's leading leg (the step_a_first chain's first back-end off the
 129 |      writers, not down and not breaker-open, at ruling 100's deadline for it: Router.effective_deadline). The filter is
 130 |      Heimdall's: when no Heimdall family leads (Grok leads: every family is the writer's, down or breaker-open), the first
 131 | -    verdicts are Grok's own, which a confirm off Heimdall could never serve: sequential, whatever the wait.
 132 | -    -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg"}."""
 133 | +    verdicts are Grok's own, which a confirm off Heimdall could never serve: sequential, whatever the wait. So it is
 134 | +    when no confirm leg is usable (_confirm_leg). -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg",
 135 | +    "confirm", "why"} (why: the reason it is sequential, None when parallel)."""
 136 |      new = prescreen(router, ms, sources, ctx, wv, wf, store=store, cache=cache, plan_only=True,
 137 |                      **{k: v for k, v in first.items() if k in ("batch", "kind")})
 138 |      if len(new) <= STEP_A_PARALLEL_NEW:                  # under the line: sequential whatever the wait
 139 | -        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None}
 140 | +        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None, "confirm": None,
 141 | +                "why": f"not over {STEP_A_PARALLEL_NEW} new moments"}
 142 |      leg, dl, heim = None, None, False
 143 |      for name in router.chain("context_verdict", kind="step_a_first"):
 144 |          b = router.backends.get(name)
 145 | -        if b is None or b.vendor in set(wv) or b.family in set(wf) or name in getattr(router, "down", {}) or \
 146 | -                (hasattr(router, "breaker_open") and router.breaker_open(name)):
 147 | +        if not _usable(router, name, wv, wf):
 148 |              continue
 149 |          leg, dl, heim = name, router.effective_deadline("context_verdict", b, first.get("deadline_s")), _heimdall(b)
 150 |          break
 151 |      batch = first.get("batch") or PRESCREEN_BATCH
 152 |      rounds = math.ceil(math.ceil(len(new) / batch) / PRESCREEN_WORKERS) if new else 0
 153 |      wait = rounds * dl if dl else 0.0
 154 | -    return {"parallel": heim and len(new) > STEP_A_PARALLEL_NEW and wait > STEP_A_PARALLEL_WAIT_S, "new": new,
 155 | -            "n_new": len(new), "est_wait_s": round(wait, 1), "leg": leg}
 156 | +    confirm = _confirm_leg(router, wv, wf)
 157 | +    why = ("no Heimdall family leads the filter" if not heim else
 158 | +           f"the filter's wait is not over {STEP_A_PARALLEL_WAIT_S / 60:.0f} min" if wait <= STEP_A_PARALLEL_WAIT_S
 159 | +           else "no confirm leg (Grok writes, is down or breaker-open)" if confirm is None else None)
 160 | +    return {"parallel": why is None and len(new) > STEP_A_PARALLEL_NEW, "new": new, "n_new": len(new),
 161 | +            "est_wait_s": round(wait, 1), "leg": leg, "confirm": confirm, "why": why}
 162 |  
 163 |  
 164 |  def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 165 | @@ -652,8 +711,8 @@ def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 166 |      (it then reuses the verdict off the first's vendor; 'a clip passes only if BOTH pass' is unchanged, and a moment
 167 |      whose first verdict came from Grok itself is screened off it as before). -> {"asked", "verdicts", "usd", "calls",
 168 |      "by": {moment id: back-end}}: the spend is reported per build (a verdict the second screen cannot use is extra)."""
 169 | -    hv = {b.vendor for b in router.backends.values() if _heimdall(b)}
 170 | -    hf = {b.family for b in router.backends.values() if _heimdall(b)}
 171 | +    hv = {b.vendor for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}    # ruling 102: Grok only, never
 172 | +    hf = {b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}    # Gemini or the local judge
 173 |      tally = _Tally(router)
 174 |      try:
 175 |          got, _fails, _, _ = prescreen(tally, new, sources, ctx, set(wv) | hv, set(wf) | hf, n=len(new), store=None,
 176 | @@ -710,8 +769,7 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 177 |                               cache=cache, batch=batch, deadline_s=dl,    # ruling 58: a second verdict is paid once;
 178 |                               kind="step_a_second", failover=True)        # ruling 82 / 88 (c): the chain
 179 |          except Exception as e:
 180 | -            return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 181 | -                        for m in chunk}, set(), set()
 182 | +            return {}, {m["moment_id"]: [held_why(e)] for m in chunk}, set(), set()
 183 |      with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as ex:
 184 |          res = list(ex.map(lambda j: one(*j), jobs))          # Executor.map keeps the order of jobs: zipped below
 185 |      two, fail = {}, {}
 186 | @@ -719,8 +777,9 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 187 |          for m in chunk:
 188 |              mid, a2 = m["moment_id"], got.get(m["moment_id"])
 189 |              b2 = router.backends.get((a2 or {}).get("backend"))
 190 | -            if fails.get(mid) or a2 is None:
 191 | -                fail[mid] = list(fails.get(mid) or ["STEP_A_UNAVAILABLE: no second verdict (law L-m)"])
 192 | +            if fails.get(mid) or a2 is None:            # ruling 102: no verdict at all is HELD, retried next build
 193 | +                fail[mid] = list(fails.get(mid) or [f"{HELD}: no second verdict (law L-m); held for this build, "
 194 | +                                                    f"retried next build"])
 195 |              elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
 196 |                  fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
 197 |                               f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
 198 | @@ -2486,7 +2545,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 199 |      ahead_pool = ThreadPoolExecutor(max_workers=1) if plan["parallel"] else None
 200 |      ahead = ahead_pool.submit(confirm_ahead, router, plan["new"], sources, ctx, wv, wf, log, step_a_cache) \
 201 |          if ahead_pool is not None else None              # Grok's confirm beside the Heimdall filter, at once
 202 | -    par = {**{k: plan[k] for k in ("parallel", "n_new", "est_wait_s", "leg")}, "used": 0}
 203 | +    par = {**{k: plan.get(k) for k in ("parallel", "n_new", "est_wait_s", "leg", "confirm", "why")}, "used": 0}
 204 |      try:
 205 |          a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 206 |                                                         cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 207 | @@ -2503,7 +2562,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 208 |             "reposted": reposted,
 209 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 210 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 211 | -                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par},
 212 | +                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par,
 213 | +                         "held_102": {"first": sorted(mid for mid, f in fails.items() if is_held(f)), "second": []},
 214 | +                         "last_resort_87": {}},                  # RULING 102: held, never refused; the local judge
 215 |             "angles": [], "takeaways": [],
 216 |             "package": None}
 217 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 218 | @@ -2599,8 +2660,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 219 |      a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log,
 220 |                                      cache=step_a_cache)                  # ORDER 06:22 item 45
 221 |      out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
 222 | -                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
 223 | +                                         ("HELD: " if is_held(off_fail.get(mid)) else "FAIL: ") +
 224 | +                                         "; ".join(off_fail.get(mid) or ["no second verdict"])
 225 |                                           for mid in cleared}
 226 | +    out["prescreen"]["held_102"]["second"] = sorted(mid for mid in cleared if is_held(off_fail.get(mid)))
 227 | +    out["prescreen"]["last_resort_87"] = {mid: last_resort_of(a_two[mid]) for mid in sorted(a_two)    # RULING 102
 228 | +                                          if last_resort_of(a_two[mid])}
 229 | +    h = out["prescreen"]["held_102"]
 230 | +    if h["first"] or h["second"] or out["prescreen"]["last_resort_87"]:
 231 | +        log(f"  RULING 102: held for this build (no leg answered; retried next build): {len(h['first'])} at the first "
 232 | +            f"screen, {len(h['second'])} at the second {h['second']}; the local judge (ruling 87's last resort) gave "
 233 | +            f"{len(out['prescreen']['last_resort_87'])} step-A verdict(s): {sorted(out['prescreen']['last_resort_87'])}")
 234 |      cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
 235 |      log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
 236 |          f"a verdict off it exists) ({time.time() - t0:.0f} s)")
 237 | @@ -2689,6 +2759,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 238 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 239 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 240 |  
 241 | +    def pin_last_resort(pk):
 242 | +        """RULING 102: the pin's record of the local judge's step-A verdicts on its clips (either screen's), by label."""
 243 | +        return last_resort_note({sg["label"]: ", ".join(last_resort_of(a_two.get(sg["moment_id"])))
 244 | +                                 for sg in pk["segments"] if last_resort_of(a_two.get(sg["moment_id"]))})
 245 | +
 246 |      def off_writers(mid):
 247 |          """ORDER 06:22 item 45: the moment's passing step-A verdict from a back-end off every writer's vendor and
 248 |          family so far, else None (the re-screen after a write decides, item 44). The FIRST qualifying one in a_two's
 249 | @@ -2874,7 +2949,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 250 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 251 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 252 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 253 | -                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 254 | +                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 255 | +                                last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 256 |          import package_pin
 257 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 258 |          if problems:
 259 | @@ -3126,16 +3202,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 260 |                                  a_by[mid] = got_a[mid]
 261 |                                  a_two.setdefault(mid, []).append(got_a[mid])
 262 |                              else:                              # no verdict off the writers is never a pass (L-m)
 263 | -                                bad[mid] = list(fails_a.get(mid) or ["STEP_A_UNAVAILABLE: no verdict off the writers "
 264 | -                                                                     "(law L-m)"])
 265 | +                                bad[mid] = list(fails_a.get(mid) or [f"{HELD}: no verdict off the writers (law L-m);"
 266 | +                                                                     f" held for this build, retried next build"])
 267 |                          if bad:                                # ORDER 06:22 item 44: only these clips go, for good,
 268 |                              dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 269 |                              doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 270 |                              out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 271 |                              swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed),
 272 |                                                           keep_hook=True)
 273 | -                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
 274 | -                                          f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 275 | +                            held = sorted(k for k, v in bad.items() if is_held(v))    # ruling 102: no answer
 276 | +                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails "
 277 | +                                          f"{sorted(set(bad) - set(held))} (out for good)"
 278 | +                                          + (f", gives no answer for {held} (HELD, ruling 102: out of this build "
 279 | +                                             f"only, retried next build)" if held else "") + ": " +
 280 | +                                          (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 281 |                                                          if swapped is not None else
 282 |                                                          "no swap fits the line-up rules: re-lined"))
 283 |                              relined = True
 284 | @@ -3288,7 +3368,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 285 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 286 |                                              stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 287 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 288 | -                                            value=val)                       # ruling 91: the takeaway earned its place
 289 | +                                            value=val,                       # ruling 91: the takeaway earned its place
 290 | +                                            last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 291 |                      if not ok_c:
 292 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 293 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 294 | @@ -3386,7 +3467,7 @@ def _spent(spend):
 295 |  
 296 |  
 297 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 298 | -              hook=None, stand=None, visual=None, value=None):
 299 | +              hook=None, stand=None, visual=None, value=None, last_resort=None):
 300 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 301 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 302 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 303 | @@ -3421,9 +3502,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 304 |          "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 305 |                                f"{FINAL_TAIL_S} s tail)"),
 306 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 307 | -        "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 308 | -                         sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 309 | -                         n=len(a_rows)),
 310 | +        "context_a": dict(row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 311 | +                              sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 312 | +                              n=len(a_rows)),
 313 | +                          **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 314 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 315 |                                measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 316 |          "context_c": dict(row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
 317 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 318 | index 1b9a14b..336f0fe 100644
 319 | --- a/pipeline/providers.py
 320 | +++ b/pipeline/providers.py
 321 | @@ -1260,8 +1260,14 @@ class Router:
 322 |              if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
 323 |                  import heimdall_health as HH
 324 |                  self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
 325 | +                try:
 326 | +                    plan_b = self.mode() == "plan_b"
 327 | +                except ProviderError:                           # an unreadable health state: the ruling-102 words
 328 | +                    plan_b = False
 329 |                  HH.announce(self.state_md, "PLAN B WITH ONE OUTSIDE FAMILY: STEP A'S VERDICT IS ASKED OF THE LOCAL "
 330 | -                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)")
 331 | +                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)" if plan_b else
 332 | +                            "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED, SO ITS VERDICT IS ASKED OF "
 333 | +                            "THE LOCAL GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE): RULING 87'S LAST RESORT")
 334 |  
 335 |              def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 336 |                  booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 337 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 338 | index 2d4ce7b..84ef788 100644
 339 | --- a/pipeline/spotlight.py
 340 | +++ b/pipeline/spotlight.py
 341 | @@ -735,7 +735,9 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 342 |                                         fams, None if any(not isinstance(a.get("replayed"), bool) for a in a_two or [])
 343 |                                         else any(a.get("replayed") for a in a_two or []),
 344 |                                         measured=len(a_two or []) == 2,
 345 | -                                       rule="ruling 90: step A from both families as routed (package.second_screen)")
 346 | +                                       rule="ruling 90: step A from both families as routed (package.second_screen)",
 347 | +                                       **({"last_resort": P.last_resort_note({m["moment_id"]: ", ".join(
 348 | +                                           P.last_resort_of(a_two))})} if P.last_resort_of(a_two) else {}))   # 102
 349 |      rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 350 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 351 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 352 | @@ -907,8 +909,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 353 |      for mid, m in clean.items():
 354 |          if mid in two:
 355 |              both[mid] = m
 356 | +        elif P.is_held(off_fail.get(mid)):              # RULING 102: no leg answered: held, retried next build
 357 | +            stop(mid, "HELD (ruling 102), step A from the second family gave no answer: " + "; ".join(off_fail[mid]))
 358 |          else:
 359 |              stop(mid, "step A from the second family: " + "; ".join(off_fail.get(mid) or ["no verdict (law L-m)"]))
 360 | +    out["held_102"] = sorted(mid for mid in clean if P.is_held(off_fail.get(mid)))       # RULING 102
 361 | +    out["last_resort_87"] = {mid: P.last_resort_of(v) for mid, v in sorted(two.items()) if P.last_resort_of(v)}
 362 |      passed(both, 6)
 363 |      waited = 0.0
 364 |      if both and scorer_verdicts_path and wait_s > 0 and \
 365 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 366 | index b6bd9ae..d2b60dd 100644
 367 | --- a/tests/package/proof_ledger.py
 368 | +++ b/tests/package/proof_ledger.py
 369 | @@ -131,6 +131,32 @@ def applied(router):
 370 |      return applies
 371 |  
 372 |  
 373 | +def start_refused(spent0):
 374 | +    """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
 375 | +    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
 376 | +    if spent0 >= PL.LY_STOP_USD:
 377 | +        return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 378 | +                f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator "
 379 | +                f"decides (13:02 Nov 14: SAY IT ON STATE LINE 1 IN CAPITALS)")
 380 | +    return None
 381 | +
 382 | +
 383 | +def ruling_102_line(pre, sp):
 384 | +    """RULING 102 (13:02 Nov 14): the build's line, for STATE line 1: the moments HELD for this build (no leg answered;
 385 | +    never refused, never cached, retried next build) and every step-A verdict the local judge gave (ruling 87's last
 386 | +    resort, recorded as such on the pin). -> str or "" (nothing held, no local verdict)."""
 387 | +    pre, sp = pre or {}, sp or {}
 388 | +    h = pre.get("held_102") or {}
 389 | +    first, second, spot = list(h.get("first") or []), list(h.get("second") or []), list(sp.get("held_102") or [])
 390 | +    last = sorted(set(pre.get("last_resort_87") or {}) | set(sp.get("last_resort_87") or {}))
 391 | +    if not (first or second or spot or last):
 392 | +        return ""
 393 | +    return (f"  RULING 102: HELD for this build, retried next build (no leg answered; never refused): {len(first)} at "
 394 | +            f"step A's first screen, {len(second)} at the medley's second screen {second}, {len(spot)} at the "
 395 | +            f"spotlight's {spot}; THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE {len(last)} STEP-A VERDICT(S)"
 396 | +            + (f": {last}" if last else ""))
 397 | +
 398 | +
 399 |  def ruling_101_line(par):
 400 |      """RULING 101 (12:16 Nov 14): the build's line on step A's order, with the extra spend when Grok's confirm ran in
 401 |      parallel (its verdicts the second screen could not use: the dollars sequential would have saved). -> str or ""."""
 402 | @@ -146,8 +172,8 @@ def ruling_101_line(par):
 403 |                  f"saved" + (f"; {par['error']}" if par.get("error") else ""))
 404 |      wait = par.get("est_wait_s")
 405 |      return (f"  RULING 101: step A sequential ({par.get('n_new')} new moments" +
 406 | -            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')})" if isinstance(wait, (int, float))
 407 | -             else f", not over {PK.STEP_A_PARALLEL_NEW})"))
 408 | +            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')}" if isinstance(wait, (int, float))
 409 | +             else f", not over {PK.STEP_A_PARALLEL_NEW}") + (f": {par['why']})" if par.get("why") else ")"))
 410 |  
 411 |  
 412 |  def main(argv=None):
 413 | @@ -248,9 +274,9 @@ def main(argv=None):
 414 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 415 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 416 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 417 | -    if spent0 >= PL.LY_STOP_USD:
 418 | -        say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 419 | -            f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator decides")
 420 | +    refused = start_refused(spent0)
 421 | +    if refused:
 422 | +        say(refused)
 423 |          logf.close()
 424 |          return 3
 425 |      say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
 426 | @@ -387,6 +413,9 @@ def main(argv=None):
 427 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 428 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 429 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 430 | +    line102 = ruling_102_line(res.get("prescreen"), sp)  # RULING 102: held, never refused; the local judge's verdicts
 431 | +    if line102:
 432 | +        say(line102)
 433 |      hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries;
 434 |      #   `moments` is the adapter's pool from LB.build_inputs, BEFORE usable() filters it (audit 1810 C3)
 435 |      res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
 436 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 437 | index 702160b..154aa11 100644
 438 | --- a/tests/package/proof_ly.py
 439 | +++ b/tests/package/proof_ly.py
 440 | @@ -49,8 +49,10 @@ OUT = os.path.join(HERE, "proof")
 441 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 442 |  LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
 443 |  LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
 444 | -LY_STOP_USD = 16.0                 # the estimate counts only where a vendor reports none. At $16 no build starts.
 445 | -                                   # Each paid call still RESERVES its price-table upper bound while in flight.
 446 | +LY_STOP_USD = 19.0                 # the estimate counts only where a vendor reports none. The orchestrator 13:02 Nov
 447 | +                                   # 14: the $16 stop passed with leave; at $19 no build starts and STATE line 1 says
 448 | +                                   # so in capitals; no build may end over $20 (the cap: each paid call still RESERVES
 449 | +                                   # its price-table upper bound while in flight, and none passes the limit).
 450 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 451 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
 452 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
 453 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 454 | index 2f4a7a3..cc9b1e8 100644
 455 | --- a/tests/package/test_ledger_build.py
 456 | +++ b/tests/package/test_ledger_build.py
 457 | @@ -871,7 +871,8 @@ class TestRuling85NoXai(unittest.TestCase):
 458 |          self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
 459 |          self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
 460 |          self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
 461 | -        self.assertEqual(ch["context_verdict:step_a_second"], [X, G, DS])          # (c) Grok confirms; 06:12 (2)
 462 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, G, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 463 | +        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
 464 |          self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
 465 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
 466 |          self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
 467 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 468 | index 2943c94..9d8e2ca 100644
 469 | --- a/tests/package/test_medley.py
 470 | +++ b/tests/package/test_medley.py
 471 | @@ -588,7 +588,7 @@ class Rig:
 472 |              mid = m["moment_id"]
 473 |              v = self.router.backends[name].vendor if name else None
 474 |              if name is None or (v, mid) in self.unavailable:
 475 | -                fails[mid] = ["STEP_A_UNAVAILABLE: ProviderError"]
 476 | +                fails[mid] = [PK.held_why(self.P.ProviderError("context_verdict: every back-end unavailable"))]
 477 |                  continue
 478 |              got[mid] = dict(self.A_OK, backend=name)
 479 |              fails[mid] = list(self.a_fail.get((v, mid), []))
 480 | @@ -1287,7 +1287,8 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 481 |              cache = os.path.join(d, "c.json")
 482 |              a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 483 |              self.assertEqual(len(a_by), 2)                                # the other batch (2) only
 484 | -            self.assertEqual(fails["m09"], ["STEP_A_UNAVAILABLE: RuntimeError: the batch reply was out of contract"])
 485 | +            self.assertEqual(fails["m09"], [f"{PK.HELD}: no step-A verdict (RuntimeError: the batch reply was out of "
 486 | +                                            f"contract); held for this build, retried next build"])   # ruling 102
 487 |              with open(cache) as f:
 488 |                  self.assertEqual(len(json.load(f)), 2)                    # a failure is never remembered
 489 |              calls.clear()
 490 | @@ -2513,7 +2514,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 491 |          rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
 492 |                    unavailable={("heimdall", "y")})
 493 |          out = rig.run()
 494 | -        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith("FAIL: STEP_A_UNAVAILABLE"))
 495 | +        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith(f"HELD: {PK.HELD}"))      # ruling 102
 496 | +        self.assertEqual(out["prescreen"]["held_102"], {"first": [], "second": ["y"]})
 497 |          self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 498 |  
 499 |      def test_the_verdict_used_is_the_one_off_the_writers_vendor(self):
 500 | @@ -2591,8 +2593,9 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 501 |                  self.open_ = set(open_)
 502 |  
 503 |              def chain(self, role, kind=None):
 504 | -                assert (role, kind) == ("context_verdict", "step_a_first")
 505 | -                return ["heimdall:glm", "heimdall:ds", "xai:grok"]
 506 | +                assert role == "context_verdict"
 507 | +                return {"step_a_first": ["heimdall:glm", "heimdall:ds", "xai:grok"],
 508 | +                        "step_a_second": ["xai:grok", "heimdall:ds", "heimdall:glm"]}[kind]
 509 |  
 510 |              def effective_deadline(self, role, b, deadline_s=None):
 511 |                  assert (role, deadline_s) == ("context_verdict", PK.SECOND_VERDICT_DEADLINE_S)   # the first screen's
 512 | @@ -2612,7 +2615,19 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 513 |          p = plan(21, R(open_={"heimdall:glm"}))           # glm's breaker open: deepseek leads, 2 x 300 s = 10 minutes
 514 |          self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 600.0, "heimdall:ds"))   # not OVER 10
 515 |          p = plan(37, R(open_={"heimdall:glm"}))           # 19 batches, 4 rounds x 300 s = 20 minutes
 516 | -        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (True, 1200.0, "heimdall:ds"))
 517 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"], p["confirm"], p["why"]),
 518 | +                         (True, 1200.0, "heimdall:ds", "xai:grok", None))
 519 | +        p = plan(37, R(open_={"heimdall:glm", "xai:grok"}))   # glm C2 H1: Grok breaker-open, no confirm leg
 520 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["confirm"]), (False, 1200.0, None))
 521 | +        self.assertIn("no confirm leg", p["why"])
 522 | +        p = plan(37, R(open_={"heimdall:glm"}), wv={"xai"})   # Grok writes: a confirm ahead could ask nothing
 523 | +        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (False, "heimdall:ds", None))
 524 | +        down = R()
 525 | +        down.down = {"heimdall:glm": "HTTP 503"}               # glm down this run: deepseek leads, as breaker-open
 526 | +        p = plan(37, down)
 527 | +        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (True, "heimdall:ds", "xai:grok"))
 528 | +        down.down = {"heimdall:glm": "HTTP 503", "xai:grok": "HTTP 503"}   # Grok down: no confirm leg
 529 | +        self.assertEqual(plan(37, down)["confirm"], None)
 530 |          p = plan(37, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # the writer's family: Grok leads,
 531 |          self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 472.4, "xai:grok"))   # 4 x 118.1 s
 532 |          p = plan(80, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # 40 batches, 7 rounds: over 10 minutes
 533 | @@ -2677,8 +2692,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 534 |          self.assertEqual((par["parallel"], par["n_new"], par["asked"], par["leg"]),
 535 |                           (True, len(self.MS), len(self.MS), "heimdall:glm"))
 536 |          main = threading.get_ident()
 537 | -        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm"}]   # off every
 538 | -        # Heimdall family and the writers
 539 | +        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm", "openai"}]
 540 | +        # off every vendor but Grok's (ruling 102: never Gemini or the local judge ahead) and off the writers
 541 |          self.assertEqual(len(ahead), 1)                                   # Grok's confirm: once,
 542 |          self.assertNotEqual(ahead[0], main)                               # on its own thread,
 543 |          self.assertIn(("step_a_first", {"heimdall"}, main), seen)         # beside the filter on the build's thread
 544 | @@ -2729,7 +2744,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 545 |                    [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
 546 |          out = rig.run()
 547 |          self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 548 | -        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith("STEP_A_UNAVAILABLE"))
 549 | +        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith(PK.HELD))           # ruling 102
 550 | +        self.assertIn("gives no answer for ['y'] (HELD, ruling 102", out["tried"][0]["why"])
 551 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 552 |  
 553 |      def test_when_no_swap_fits_the_line_up_re_lines_and_the_clip_stays_out(self):     # audit 0640 C1, glm P2-9
 554 | @@ -2756,7 +2772,7 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 555 |              PK.prescreen = saved
 556 |          self.assertEqual(two, {})
 557 |          self.assertEqual(sorted(fail), ["h", "x", "y", "z"])
 558 | -        self.assertTrue(all(f[0].startswith("STEP_A_UNAVAILABLE: RuntimeError") for f in fail.values()))
 559 | +        self.assertTrue(all(f[0].startswith(f"{PK.HELD}: no step-A verdict (RuntimeError") for f in fail.values()))
 560 |  
 561 |      def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
 562 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 563 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
 564 | new file mode 100644
 565 | index 0000000..8be2c53
 566 | --- /dev/null
 567 | +++ b/tests/package/test_ruling_102.py
 568 | @@ -0,0 +1,321 @@
 569 | +#!/usr/bin/env python3
 570 | +"""RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family after
 571 | +Grok: Heimdall deepseek -> Heimdall glm -> Gemini -> the local gemma3:27b (ruling 87's last resort, recorded as such on
 572 | +the pin and on STATE line 1). The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once,
 573 | +is never a refusal and is never cached; only when no leg answers is the clip HELD for this build, retried next build.
 574 | +
 575 | +Offline: a real providers.Router over fake legs, the real context_integrity.step_a, package.prescreen and
 576 | +package.second_screen; a temporary step-A cache."""
 577 | +import json
 578 | +import os
 579 | +import re
 580 | +import sys
 581 | +import tempfile
 582 | +import unittest
 583 | +from unittest import mock
 584 | +
 585 | +HERE = os.path.dirname(os.path.abspath(__file__))
 586 | +REPO = os.path.dirname(os.path.dirname(HERE))
 587 | +for _p in ("pipeline", "tests/package", "tests/providers", "tests/eligibility"):
 588 | +    sys.path.insert(0, os.path.join(REPO, _p))
 589 | +import package as PK  # noqa: E402
 590 | +import providers as P  # noqa: E402
 591 | +import proof_ledger as PLG  # noqa: E402
 592 | +import spotlight as SPOT  # noqa: E402
 593 | +import test_angles as TA  # noqa: E402
 594 | +import test_medley as TM  # noqa: E402
 595 | +import test_spotlight as TS  # noqa: E402
 596 | +from test_gates import a_item  # noqa: E402
 597 | +
 598 | +X, DS, G = "xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash"
 599 | +GEM, LJ = "google:gemini-2.5-pro", "local_judge:gemma3:27b"
 600 | +LEGS = (X, DS, G, GEM, LJ)
 601 | +VENDOR = {X: ("xai", "grok", None), DS: ("heimdall/deepseek", "deepseek", "heimdall"),
 602 | +          G: ("heimdall/glm", "glm", "heimdall"), GEM: ("google", "gemini", None), LJ: ("local_judge", "gemma", None)}
 603 | +
 604 | +
 605 | +def answer(prompt):
 606 | +    """A step-A reply in contract for exactly the excerpts the prompt carries (each passes: test_gates.a_item)."""
 607 | +    return json.dumps({"excerpts": [a_item(lb) for lb in re.findall(r'<excerpt label="([^"]+)"', prompt)]})
 608 | +
 609 | +
 610 | +class Leg(P.Backend):
 611 | +    """One leg of the chain: answers in contract, or fails with `fail` (an exception), or answers out of contract."""
 612 | +
 613 | +    def __init__(self, name, fail=None, out_of_contract=False):
 614 | +        vendor, family, gw = VENDOR[name]
 615 | +        super().__init__(name, {"model": name.split(":", 1)[1], "family": family, "price_usd_per_1m": [1, 1]},
 616 | +                         "/nonexistent")
 617 | +        self.vendor, self.fail, self.ooc, self.calls = vendor, fail, out_of_contract, 0
 618 | +        if gw:
 619 | +            self.gateway = gw
 620 | +
 621 | +    def complete(self, prompt, max_tokens, seed, system=None):
 622 | +        self.calls += 1
 623 | +        if self.fail is not None:
 624 | +            raise self.fail
 625 | +        return ("this is not JSON" if self.ooc else answer(prompt)), {"in": 10, "out": 10}, 0.01
 626 | +
 627 | +
 628 | +class Judge(P.LocalJudgeBackend):
 629 | +    """The local judge (a LocalJudgeBackend: the Router's announcement), answering at once."""
 630 | +
 631 | +    def __init__(self):
 632 | +        super().__init__(LJ, {"model": "gemma3:27b", "family": "gemma"}, "/nonexistent")
 633 | +        self.calls = 0
 634 | +
 635 | +    def complete(self, prompt, max_tokens, seed, system=None):
 636 | +        self.calls += 1
 637 | +        return answer(prompt), {"in": 0, "out": 0}, 0.01
 638 | +
 639 | +
 640 | +def router(d, legs, **kw):
 641 | +    cfg = os.path.join(d, "cfg.json")
 642 | +    with open(cfg, "w") as f:
 643 | +        json.dump({"schema": "pp.providers/1",
 644 | +                   "backends": {b.name: {"vendor": "openai", "model": b.model} for b in legs},
 645 | +                   "roles": {"context_verdict": {"chain": [b.name for b in legs]}},
 646 | +                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
 647 | +                               "verdict_deadline_s": {"heimdall": 120},
 648 | +                               "heimdall_first": {"context_verdict:step_a_second": list(LEGS)}}}, f)
 649 | +    r = P.Router(cfg, env_path="/nonexistent", routing="heimdall_first", **kw)
 650 | +    r.backends = {b.name: b for b in legs}
 651 | +    return r
 652 | +
 653 | +
 654 | +def pool(n=2):
 655 | +    return TM.TestRuling58StepAEveryCandidate.pool(None, n)
 656 | +
 657 | +
 658 | +class TestTheSecondFamily(unittest.TestCase):
 659 | +    """package.second_screen on the moments whose FIRST verdict is Grok's (the two hook-4 candidates' case)."""
 660 | +
 661 | +    def setUp(self):
 662 | +        self.d = tempfile.TemporaryDirectory()
 663 | +        self.addCleanup(self.d.cleanup)
 664 | +        self.cache = os.path.join(self.d.name, "STEP_A_CACHE.json")
 665 | +        self.ms, self.srcs = pool(2)
 666 | +        self.cleared = {m["moment_id"]: m for m in self.ms}
 667 | +
 668 | +    def screen(self, legs, first=X):
 669 | +        r = router(self.d.name, legs)
 670 | +        a_by = {mid: dict(a_item(mid), backend=first) for mid in self.cleared}
 671 | +        return PK.second_screen(r, self.cleared, a_by, self.srcs, TM.ctx(), log=lambda *_: None, cache=self.cache)
 672 | +
 673 | +    def cached(self):
 674 | +        if not os.path.exists(self.cache):
 675 | +            return {}
 676 | +        with open(self.cache) as f:
 677 | +            return {k: sorted(v) for k, v in json.load(f).items()}
 678 | +
 679 | +    def test_every_faster_leg_unavailable_the_local_judge_answers_and_is_the_last_resort(self):
 680 | +        legs = [Leg(X), Leg(DS, P.Unavailable("HTTP 503")), Leg(G, P.Unavailable("HTTP 503")),
 681 | +                Leg(GEM, P.Unavailable("HTTP 429")), Leg(LJ)]
 682 | +        two, fail = self.screen(legs)
 683 | +        self.assertEqual(fail, {})
 684 | +        self.assertEqual({mid: [a["backend"] for a in v] for mid, v in two.items()},
 685 | +                         {mid: [X, LJ] for mid in self.cleared})                 # off Grok: the last leg answered
 686 | +        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])               # in order, each once, never Grok
 687 | +        self.assertEqual({mid: PK.last_resort_of(v) for mid, v in two.items()}, {mid: [LJ] for mid in self.cleared})
 688 | +
 689 | +    def test_the_order_is_deepseek_glm_gemini_the_judge(self):
 690 | +        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), LJ)):
 691 | +            legs = [Leg(n, P.Unavailable("down") if n in down else None) for n in LEGS]
 692 | +            two, fail = self.screen(legs)
 693 | +            self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 694 | +            os.path.exists(self.cache) and os.remove(self.cache)
 695 | +        legs = [Leg(n) for n in LEGS]                         # a first verdict from glm: Grok confirms, as before
 696 | +        two, _ = self.screen(legs, first=G)
 697 | +        self.assertEqual({v[1]["backend"] for v in two.values()}, {X})
 698 | +
 699 | +    def test_a_leg_out_of_contract_or_past_its_deadline_moves_on_at_once_and_is_never_a_refusal(self):
 700 | +        legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G, P.DeadlineExceeded("no answer within 60 s")),
 701 | +                Leg(GEM, P.RequestRejected("refused this request")), Leg(LJ)]
 702 | +        two, fail = self.screen(legs)
 703 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {LJ}))
 704 | +        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])
 705 | +
 706 | +    def test_no_leg_answers_the_clip_is_held_never_cached_and_retried_next_build(self):
 707 | +        legs = [Leg(X)] + [Leg(n, P.Unavailable("down")) for n in (DS, G, GEM, LJ)]
 708 | +        two, fail = self.screen(legs)
 709 | +        self.assertEqual(two, {})
 710 | +        self.assertEqual(sorted(fail), sorted(self.cleared))
 711 | +        self.assertTrue(all(PK.is_held(f) for f in fail.values()), fail)          # HELD, not a refusal
 712 | +        self.assertTrue(all("retried next build" in f[0] for f in fail.values()))
 713 | +        self.assertEqual(self.cached(), {})                                        # nothing remembered
 714 | +        legs = [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G), Leg(GEM), Leg(LJ)]   # the next build: glm is back
 715 | +        two, fail = self.screen(legs)
 716 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {G}))   # retried and answered
 717 | +        self.assertEqual(set(sum(self.cached().values(), [])), {G})                # only an answer is cached
 718 | +
 719 | +    def test_a_verdict_that_fails_the_clip_is_a_refusal_not_held(self):
 720 | +        legs = [Leg(n) for n in LEGS]
 721 | +        with mock.patch.object(PK.CI, "a_failures", lambda a: ["REFERENT_OUTSIDE"]):
 722 | +            two, fail = self.screen(legs)
 723 | +        self.assertEqual(two, {})
 724 | +        self.assertFalse(any(PK.is_held(f) for f in fail.values()))
 725 | +        self.assertEqual(set(map(tuple, fail.values())), {("REFERENT_OUTSIDE",)})
 726 | +
 727 | +
 728 | +class TestInTheBuild(unittest.TestCase):
 729 | +    """package.build (the rig: every model stubbed): HELD moments are recorded per screen, and a pin whose clips were
 730 | +    judged by the local judge carries the record (ruling 87's last resort) in its sealed context_a row."""
 731 | +    MS = TM.TestBuildLoop.MS
 732 | +
 733 | +    def test_a_moment_held_at_the_first_screen_is_recorded_as_held(self):
 734 | +        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None], unavailable={("xai", "z")})
 735 | +        out = rig.run()
 736 | +        self.assertEqual(out["prescreen"]["held_102"], {"first": ["z"], "second": []})
 737 | +        self.assertTrue(PK.is_held(out["prescreen"]["failed"]["z"]))
 738 | +        self.assertIsNotNone(out["package"])                      # the build goes on without it
 739 | +
 740 | +    def test_a_pin_judged_by_the_local_judge_says_so(self):
 741 | +        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None])
 742 | +        rig.router.backends[LJ] = type("B", (), {"vendor": "local_judge", "family": "gemma"})()
 743 | +        pre = rig.prescreen
 744 | +
 745 | +        def judged(router_, ms, *a, kind=None, **k):          # the second family: only the local judge answers
 746 | +            if k.get("plan_only"):                              # ruling 101's plan: nothing asked
 747 | +                return pre(router_, ms, *a, kind=kind, **k)
 748 | +            got, fails, v, f = pre(router_, ms, *a, kind=kind, **k)
 749 | +            if kind == "step_a_second":
 750 | +                got = {mid: dict(a, backend=LJ) for mid, a in got.items()}
 751 | +            return got, fails, v, f
 752 | +        rig.prescreen = judged
 753 | +        out = rig.run()
 754 | +        segs = out["package"]["segments"]
 755 | +        self.assertEqual(out["prescreen"]["last_resort_87"], {mid: [LJ] for mid in sorted(out["prescreen"]
 756 | +                                                                                         ["last_resort_87"])})
 757 | +        self.assertTrue({sg["moment_id"] for sg in segs} <= set(out["prescreen"]["last_resort_87"]))
 758 | +        row = out["package"]["gates"]["context_a"]
 759 | +        self.assertEqual(row["last_resort"]["verdicts"], {sg["label"]: LJ for sg in segs})
 760 | +        self.assertEqual(row["status"], "PASS")
 761 | +
 762 | +    def test_a_re_screen_off_the_writers_with_no_verdict_and_no_reason_is_held(self):
 763 | +        """The writers' re-screen (order 06:22 item 44): a clip it returns nothing at all for is HELD (its default
 764 | +        reason), out of this build only, never a refusal."""
 765 | +        rig = TM.Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)],
 766 | +                     [None, None], angle_from=("xai:grok", "xai", "grok"))
 767 | +        pre = rig.prescreen
 768 | +
 769 | +        def silent(router_, ms, sources_, ctx_, writer_vendor, *a, **k):
 770 | +            res = pre(router_, ms, sources_, ctx_, writer_vendor, *a, **k)
 771 | +            if k.get("plan_only") or not {"xai", "heimdall"} <= P._as_set(writer_vendor):
 772 | +                return res
 773 | +            got, fails, v, f = res                              # the writers' re-screen: y gets nothing at all
 774 | +            return {m: x for m, x in got.items() if m != "y"}, {m: x for m, x in fails.items() if m != "y"}, v, f
 775 | +        rig.prescreen = silent
 776 | +        out = rig.run()
 777 | +        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 778 | +        self.assertTrue(PK.is_held(out["prescreen"]["rescreen_failed"]["y"]))
 779 | +        self.assertIn("no verdict off the writers", out["prescreen"]["rescreen_failed"]["y"][0])
 780 | +
 781 | +    def test_the_default_no_second_verdict_is_held(self):
 782 | +        ms, srcs = pool(1)
 783 | +        mid = ms[0]["moment_id"]
 784 | +        r = type("R", (), {"backends": {X: Leg(X), DS: Leg(DS)}, "routing": "heimdall_first"})()
 785 | +        with mock.patch.object(PK, "prescreen", lambda *a, **k: ({}, {}, set(), set())):   # no verdict, no reason
 786 | +            two, fail = PK.second_screen(r, {mid: ms[0]}, {mid: dict(a_item(mid), backend=X)}, srcs, TM.ctx(),
 787 | +                                         log=lambda *_: None)
 788 | +        self.assertEqual(two, {})
 789 | +        self.assertTrue(PK.is_held(fail[mid]), fail)
 790 | +
 791 | +
 792 | +class TestHeldWhy(unittest.TestCase):
 793 | +    def test_no_verdict_is_held_except_a_context_law_l_s_will_never_shorten(self):
 794 | +        for e in (P.ProviderError("context_verdict: every back-end unavailable"), P.SpendLimit("over $20"),
 795 | +                  RuntimeError("anything")):
 796 | +            why = PK.held_why(e)
 797 | +            self.assertTrue(PK.is_held([why]), e)
 798 | +            self.assertIn(type(e).__name__, why)
 799 | +        why = PK.held_why(ValueError("CONTEXT_TOO_LONG: m1's window is 9000 characters (> 6000); never truncated"))
 800 | +        self.assertTrue(why.startswith("STEP_A_REFUSED: CONTEXT_TOO_LONG"))
 801 | +        self.assertFalse(PK.is_held([why]))
 802 | +        self.assertFalse(PK.is_held([]))
 803 | +        self.assertFalse(PK.is_held([PK.held_why(RuntimeError("x")), "REFERENT_OUTSIDE"]))   # one refusal: refused
 804 | +
 805 | +
 806 | +class TestOnThePinAndOnState(unittest.TestCase):
 807 | +    def test_the_medley_pin_records_the_local_judge_and_a_pin_without_it_is_unchanged(self):
 808 | +        base = TA.TestInventory.base(None)
 809 | +        plain = PK.inventory(**base)
 810 | +        self.assertNotIn("last_resort", plain["context_a"])                          # every other pin as before
 811 | +        g = PK.inventory(**base, last_resort=PK.last_resort_note({"clip_01": LJ}))
 812 | +        self.assertEqual(g["context_a"]["last_resort"]["verdicts"], {"clip_01": LJ})
 813 | +        self.assertIn("ruling 87's last resort (ruling 102)", g["context_a"]["last_resort"]["rule"])
 814 | +        self.assertEqual({k: v for k, v in g["context_a"].items() if k != "last_resort"}, plain["context_a"])
 815 | +
 816 | +    def test_the_spotlight_pin_records_the_local_judge(self):
 817 | +        m = TS.moment()
 818 | +
 819 | +        def row(a_two):
 820 | +            return SPOT.inventory(*TS.package()[0:1], m, TS.FID_OK, [], True, [], TS.CX_OK, a_two[0], a_two,
 821 | +                                  {"verdict": "keep", "measured": True, "replayed": False},
 822 | +                                  {"ok": True, "edges": {"cuttable": True}}, TS.pre_of(m), m["spotlight_source"],
 823 | +                                  {"now": TS.NOW, "day": "d", "never_delivered": True,
 824 | +                                   "one_per_channel_day": True})["step_a_two_families"]
 825 | +        self.assertNotIn("last_resort", row(TS.two()))
 826 | +        judged = [TS.two()[0], dict(TS.two()[1], backend=LJ)]
 827 | +        r = row(judged)
 828 | +        self.assertEqual((r["status"], r["last_resort"]["verdicts"]), ("PASS", {m["moment_id"]: LJ}))
 829 | +
 830 | +    def test_state_line_1_is_told_once_in_the_ruling_s_words_and_plan_b_keeps_its_own(self):
 831 | +        for plan_b, words in ((False, "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED"),
 832 | +                              (True, "PLAN B WITH ONE OUTSIDE FAMILY")):
 833 | +            with tempfile.TemporaryDirectory() as d:
 834 | +                state = os.path.join(d, "STATE.md")
 835 | +                with open(state, "w") as f:
 836 | +                    f.write("line one\nline two\n")
 837 | +                judge = Judge()
 838 | +                r = router(d, [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G, P.Unavailable("down")),
 839 | +                               Leg(GEM, P.Unavailable("down")), judge], state_md=state)
 840 | +                r.mode = lambda: "plan_b" if plan_b else "heimdall_first"
 841 | +                ms, srcs = pool(2)
 842 | +                a_by = {m["moment_id"]: dict(a_item(m["moment_id"]), backend=X) for m in ms}
 843 | +                for _ in range(2):                                           # two screens: one announcement
 844 | +                    PK.second_screen(r, {m["moment_id"]: m for m in ms}, a_by, srcs, TM.ctx(), log=lambda *_: None,
 845 | +                                     cache=None)
 846 | +                with open(state) as f:
 847 | +                    first = f.read().split("\n")[0]
 848 | +                self.assertEqual(first.count(words), 1, first)
 849 | +                self.assertTrue(first.endswith("| line one"), first)
 850 | +                self.assertEqual(judge.calls, 2)
 851 | +
 852 | +    def test_the_build_line(self):
 853 | +        self.assertEqual(PLG.ruling_102_line({"held_102": {"first": [], "second": []}, "last_resort_87": {}}, {}), "")
 854 | +        line = PLG.ruling_102_line({"held_102": {"first": ["a"], "second": ["b"]}, "last_resort_87": {"c": [LJ]}},
 855 | +                                   {"held_102": ["d"], "last_resort_87": {"e": [LJ]}})
 856 | +        self.assertIn("HELD for this build, retried next build", line)
 857 | +        self.assertIn("1 at step A's first screen, 1 at the medley's second screen ['b'], 1 at the spotlight's ['d']",
 858 | +                      line)
 859 | +        self.assertIn("THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE 2 STEP-A VERDICT(S): ['c', 'e']", line)
 860 | +
 861 | +    def test_no_build_starts_at_19_dollars_and_one_starts_below(self):
 862 | +        """The orchestrator 13:02 Nov 14: the $16 stop passed with leave; at $19 stop and say so in capitals."""
 863 | +        self.assertIsNone(PLG.start_refused(18.99))
 864 | +        why = PLG.start_refused(19.0)
 865 | +        self.assertIn("at or over the $19.00 stop: no build starts", why)
 866 | +        self.assertIn("SAY IT ON STATE LINE 1 IN CAPITALS", why)
 867 | +
 868 | +
 869 | +class TestTheConfirmAheadIsGrokOnly(unittest.TestCase):
 870 | +    """RULING 101 beside 102: Grok's confirm-ahead never asks Gemini or the local judge (the second family's
 871 | +    fallbacks are the second screen's, asked only when it needs them)."""
 872 | +
 873 | +    def test_every_vendor_but_grok_s_is_avoided_ahead(self):
 874 | +        legs = {n: Leg(n) for n in LEGS}
 875 | +        got = {}
 876 | +
 877 | +        def fake(router_, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
 878 | +            got.update(wv=set(wv), wf=set(wf), kind=kind)
 879 | +            return {}, {}, set(), set()
 880 | +        r = type("R", (), {"backends": legs})()
 881 | +        with mock.patch.object(PK, "prescreen", fake):
 882 | +            PK.confirm_ahead(r, [{"moment_id": "a"}], {}, None, {"heimdall/deepseek"}, {"deepseek"})
 883 | +        self.assertEqual(got["wv"], {"heimdall/deepseek", "heimdall/glm", "google", "local_judge"})
 884 | +        self.assertEqual(got["wf"], {"deepseek", "glm", "gemini", "gemma"})
 885 | +        self.assertEqual(got["kind"], "step_a_second")
 886 | +
 887 | +
 888 | +if __name__ == "__main__":
 889 | +    unittest.main()
 890 | diff --git a/tests/providers/test_deadline_table.py b/tests/providers/test_deadline_table.py
 891 | index ac2cb87..e1e770a 100644
 892 | --- a/tests/providers/test_deadline_table.py
 893 | +++ b/tests/providers/test_deadline_table.py
 894 | @@ -140,6 +140,11 @@ class TestRouter(unittest.TestCase):
 895 |          self.assertEqual(self.router(None).effective_deadline("context_verdict", r.backends[DS]), 120.0)   # no table
 896 |          self.assertEqual(r.role_deadline("context_verdict", r.backends[DS]), 120.0)   # the gateway's number, as before
 897 |          self.assertIsNone(r.role_deadline("context_verdict", r.backends[GROK]))
 898 | +        table = {"rows": dict(self.TABLE["rows"], **{f"{DS}|shadow86:context_verdict": {"deadline_s": 300.0},
 899 | +                                                    f"{DS}|probe87:{DS}": {"deadline_s": 300.0}})}
 900 | +        r = self.router(table)                       # glm, audit 20261114_1246 C2 M2: a shadow or a probe is no verdict
 901 | +        self.assertEqual(r.effective_deadline("shadow86:context_verdict", r.backends[DS], 120.0), 120.0)
 902 | +        self.assertEqual(r.effective_deadline(f"probe87:{DS}", r.backends[DS], 60.0), 60.0)
 903 |  
 904 |      def test_a_live_call_waits_its_own_deadline_and_the_breaker_measures_against_it(self):
 905 |          """Router.call itself: the deadline the call is held to (and the breaker's miss is measured against: ruling 99)
 906 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
 907 | index 139c4b1..fb1d0f4 100644
 908 | --- a/tests/providers/test_heimdall_health.py
 909 | +++ b/tests/providers/test_heimdall_health.py
 910 | @@ -403,6 +403,7 @@ class TestLocalJudge(unittest.TestCase):
 911 |          open(md, "w").write("21:50 ET: line one.\n")
 912 |          r = P.Router(cfg, env_path="/nonexistent", state_md=md)
 913 |          r.backends["local_judge:gemma3:27b"] = self.b
 914 | +        r.mode = lambda: "plan_b"           # Plan B's words (ruling 102's, outside Plan B: test_ruling_102)
 915 |          seen = {}
 916 |          orig = P._within
 917 |  
 918 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- STEP A (law L-s) screens each moment's own context twice. The FIRST screen (package.prescreen, kind step_a_first,
  chain [glm, deepseek, Grok], 2 clips a call) runs on every usable moment. Later, the SECOND screen
  (package.second_screen, kind step_a_second, 8 clips a call) runs on the moments that cleared, were cuttable and
  passed the hook rules; it asks for a verdict OFF the first verdict's vendor and family. A clip passes only if BOTH
  pass. Each Heimdall family is its own vendor under heimdall_first ("heimdall/deepseek", "heimdall/glm").
- Verdicts are cached across builds in a shared step-A cache, per back-end.
- At 12:24 and 12:40 ET two spotlight candidates with hooks rated 4 (Blockware Solutions 06d34e15, Strategy 933f9d33)
  died at the second screen with "STEP_A_UNAVAILABLE". Their first verdict was Grok's, so Grok was excluded; glm's and
  deepseek's breakers were open. Ruling 100 (committed e87f4c3f) gave deepseek its own 300 s deadline.
- RULING 87 (Nov 13): Plan B (Heimdall declared down) uses outside families, with the local judge last: the
  integrator's gemma3:27b on GPU0, reached through request files; it waits up to 40 min because a render comes first.
  Ruling 87 also says the local judge's use is announced on STATE line 1.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.Router.call walks the chain:
  - a breaker-open leg is skipped (providers.py:1249);
  - DeadlineExceeded books a miss and moves on (:1287);
  - RequestRejected moves on (:1294);
  - Unavailable marks the leg down for the run and moves on (:1299);
  - when every leg fails it raises ProviderError("<role>: every back-end unavailable: ...") (:1338).
- context_integrity.step_a (context_integrity.py:321): with failover=True, an answer out of contract skips that model
  and asks the next (:355), each model once, until the chain is spent.
- package.prescreen (package.py:525): only a PARSED verdict is written to the cache (_cache_put(cache, new), :608). A
  failed batch writes nothing. second_screen (:748) calls it with failover=True and kind step_a_second.
- Router.chain (providers.py:780) uses the routing's "<role>:<kind>" list. Plan B's lists apply only while the shared
  health says Heimdall is down.
- Router.call announces the local judge on STATE line 1 the first time it asks it (heimdall_health.announce; once per
  router).
- providers.LocalJudgeBackend (providers.py:288): WAIT_S 2400 s (:305). No answer, an error or an unreadable file is
  Unavailable. It is free.
- google:gemini-2.5-pro uses the fenced GEMINI_API_KEY_MEDLEY. It already sits in heimdall_first's
  coherence_verdict:clips_alone list (ruling 06:12 (1)). It was probed once at 12:5x ET (answered in 2.2 s).
- package_pin.seal (package_pin.py:188) hashes the gates dict as it stands. gate_problems (:347) checks only each
  required row's status and replayed. Pins already sealed carry no new key and recompute unchanged.

THE ORCHESTRATOR'S RULING (13:02 ET Nov 14), verbatim:
"102. STEP_A_UNAVAILABLE MUST NEVER END A CLIP (two hook-4 candidates, Blockware Solutions 06d34e15 and Strategy
933f9d33, died of it twice). Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) ->
Heimdall glm -> GEMINI through the fenced key (probe it once; it is a different family from xAI and from Heimdall's
models, and PBX named it for exactly this) -> the local gemma3:27b on GPU0 through the integrator's judge service
(ruling 87's last resort, recorded as such on the pin and on STATE line 1). The first of these that ANSWERS gives the
second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if all four give no
answer is the clip held for THIS build (not refused), and retried next build. Do this BEFORE the next build if it is
small (the chain already exists for Plan B; this is the same chain reached without declaring Heimdall down)."
The same message: "THE $16 STOP: PASSED WITH MY LEAVE. Build on to the $20.00 cap ... At $19 stop and tell me on line 1
in capitals; do not start a build that would end over $20."

THE CHANGE (the diff follows):
1. model_providers.json: heimdall_first's context_verdict:step_a_second becomes [Grok, deepseek, glm,
   google:gemini-2.5-pro, local_judge:gemma3:27b], from [Grok, glm, deepseek].
   - Grok stays first: ruling 88 (c) has Grok confirm a Heimdall pass; for a Grok first verdict it is skipped as the
     first's vendor.
   - Plus the ruling's text, and notes on the two back-ends.
2. package.held_why(e) / is_held / HELD:
   - A step-A call that gives no verdict leaves "STEP_A_HELD (ruling 102): no step-A verdict (<error>); held for this
     build, retried next build" on its moments. This covers prescreen's failed batch (either screen), second_screen's
     raising chunk, its "no second verdict" default, and the writers' re-screen.
   - The one exception is CONTEXT_TOO_LONG, a ValueError that step_a raises before any call (law L-s never truncates):
     STEP_A_REFUSED.
   - A verdict that FAILS the clip is unchanged (a refusal, cached as a verdict).
   - The build records out.prescreen.held_102 {first, second}; second_vendor says "HELD: ...". The writers' re-screen
     says the held moments are out of this build only. The spotlight stops a held moment with "HELD (ruling 102) ..."
     and records held_102.
3. The local judge, recorded as such:
   - last_resort_of(verdicts) finds the back-ends named "local_judge:...".
   - out.prescreen.last_resort_87 and the spotlight's last_resort_87 record them.
   - On the pin: the medley's sealed context_a row and the spotlight's step_a_two_families row carry
     "last_resort": {rule, verdicts} ONLY when the local judge gave one of the pin's step-A verdicts. Every other pin is
     byte-identical in shape.
   - STATE line 1: the Router's first-use announcement names ruling 102 outside Plan B (Plan B keeps its words). The
     build prints a RULING 102 line (proof_ledger.ruling_102_line) in capitals for the local judge.
4. Ruling 101 beside 102 (carried from audit 20261114_1246 C2, glm H1):
   - confirm_ahead asks Grok only. Every vendor and family but xAI's is added to its writer sets, so Gemini and the
     local judge are never asked ahead.
   - step_a_plan is parallel only when a confirm leg is usable now (_confirm_leg: the step_a_second chain's first xAI
     back-end off the writers, not down, not breaker-open).
   - The plan reports why it is sequential.
5. glm M2 (same audit): a test that a shadow86:/probe87: role takes no deadline row (no code change).
6. The $19 stop: proof_ly.LY_STOP_USD 16.0 -> 19.0. proof_ledger.start_refused(spent0) is the start check; its line
   says to put it on STATE line 1 in capitals. The per-call cap is unchanged.
7. Tests: test_ruling_102.py (new, 16). It uses a real providers.Router over fake legs with the real step_a,
   prescreen and second_screen, and covers:
   - the chain order;
   - unavailable, past-deadline, refused and out-of-contract legs moving on;
   - held, never cached, and retried next build;
   - a failing verdict still a refusal;
   - the pin rows, the announcement, the build line and the $19 stop;
   - Grok-only confirm-ahead;
   - the writers' re-screen's default reason (no verdict, no reason) is HELD.
   Other suites updated: test_medley, test_ledger_build, test_deadline_table, test_heimdall_health (its ruling-87
   announcement test now names Plan B mode, since outside Plan B the words are ruling 102's). 31 mutations.

ATTACK:
(a) Can a moment still END (be refused, or have a failure cached) because no leg answered? Can a refusal by a real
    verdict now be mislabelled HELD and silently retried forever?
(b) The chain: can the second verdict come from the first verdict's own vendor or family? Is the order exactly the
    ruling's? Can a leg be skipped that should be asked, or asked twice?
(c) The local judge: can its verdict reach a pin without the record? Can the record change an existing pin's seal?
    Can the build hang on it longer than ruling 87 allows?
(d) Ruling 101 beside it: can the confirm-ahead now ask Gemini or the local judge? Can the plan go parallel with no
    usable confirm leg?
(e) The $19 stop and the $20 cap: can a build start at or over $19? Can one end over $20?
(f) Anything else that could seal a wrong pin, starve a build, or spend past ruling 48's cap.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

