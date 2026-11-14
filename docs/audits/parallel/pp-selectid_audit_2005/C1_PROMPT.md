# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2005
# Branch: pp-selectid
# Generated: 2026-11-13 20:05 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2005/C1_STEP.diff (285 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 487cacb..073e0e6 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -318,9 +318,11 @@ def check(router, package, sources, writer_vendor, seed=7):
   6 |      return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
   7 |  
   8 |  
   9 | -def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
  10 | +def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False):
  11 |      """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
  12 | -    Raises ValueError / ProviderError when it cannot be had or read."""
  13 | +    Raises ValueError / ProviderError when it cannot be had or read. RULING 82 (20:02 Nov 13): deadline_s bounds each
  14 | +    call (the router moves to the next model at it and logs the miss, item 55); failover=True also moves on when a
  15 | +    model's answer is out of contract, each model once, until the chain is spent (then ProviderError: no verdict)."""
  16 |      labels = list(contexts)
  17 |      for lb in labels:
  18 |          if len(contexts[lb]["text"]) > EXCERPT_MAX:
  19 | @@ -330,17 +332,23 @@ def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
  20 |            f'"{_q(contexts[lb].get("title") or "", 160)}" published="{contexts[lb].get("published") or "unknown"}" '
  21 |            f'show_date="{contexts[lb].get("show_date") or "unknown"}">{contexts[lb]["text"]}</excerpt>'
  22 |            for lb in labels]
  23 | -    ra = router.call("context_verdict", STEP_A.format(excerpts="\n".join(ex)), 4000, seed, avoid_vendor=writer_vendor,
  24 | -                     avoid_family=writer_family)
  25 | -    try:
  26 | -        A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  27 | -        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  28 | -        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
  29 | -            raise ValueError(f"step A must answer exactly the labels {labels}")
  30 | -    except (ValueError, TypeError):
  31 | -        if hasattr(router, "reject"):
  32 | -            router.reject(ra)
  33 | -        raise
  34 | +    prompt, skip = STEP_A.format(excerpts="\n".join(ex)), set()
  35 | +    while True:
  36 | +        ra = router.call("context_verdict", prompt, 4000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
  37 | +                         **({"avoid_model": set(skip)} if skip else {}),
  38 | +                         **({"deadline_s": deadline_s} if deadline_s else {}))
  39 | +        try:
  40 | +            A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  41 | +            a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  42 | +            if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
  43 | +                raise ValueError(f"step A must answer exactly the labels {labels}")
  44 | +            break
  45 | +        except (ValueError, TypeError):
  46 | +            if hasattr(router, "reject"):
  47 | +                router.reject(ra)
  48 | +            if not failover or ra.backend in skip:
  49 | +                raise
  50 | +            skip.add(ra.backend)                         # ruling 82: the next model in the chain
  51 |      for lb in labels:
  52 |          a_by[lb] = dict(a_by[lb], backend=ra.backend, replayed=bool(getattr(ra, "replayed", False)),
  53 |                          speaker_verified=speaker_verified(a_by[lb], contexts[lb]["text"]))
  54 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
  55 | index 8ca333d..11238b1 100644
  56 | --- a/pipeline/model_providers.json
  57 | +++ b/pipeline/model_providers.json
  58 | @@ -143,6 +143,19 @@
  59 |     "family": "scribe",
  60 |     "price_usd_per_min": 0.012,
  61 |     "timeout_s": 300
  62 | +  },
  63 | +  "heimdall:z-ai/glm-5.3-flash": {
  64 | +   "vendor": "heimdall",
  65 | +   "model": "z-ai/glm-5.3-flash",
  66 | +   "price_usd_per_1m": [
  67 | +    3,
  68 | +    15
  69 | +   ],
  70 | +   "temperature": 0,
  71 | +   "min_out": 16000,
  72 | +   "family": "glm",
  73 | +   "base_url": "https://api-staging.heimdallm.com/api/v1",
  74 | +   "measured": "ruling 82 (orchestrator 20:02 Nov 13): pp-ingest measured it 24/24 on calibration (default reasoning)"
  75 |    }
  76 |   },
  77 |   "roles": {
  78 | @@ -179,9 +192,12 @@
  79 |      "xai:grok-4.20-0309-reasoning",
  80 |      "anthropic:claude-opus-5-5",
  81 |      "heimdall:deepseek/deepseek-v4.1-flash",
  82 | +    "heimdall:z-ai/glm-5.3-flash",
  83 | +    "heimdall:qwen/qwen3.8-27b",
  84 |      "local:gemma3:27b"
  85 |     ],
  86 | -   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor"
  87 | +   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor",
  88 | +   "ruling_82": "orchestrator 20:02 Nov 13: the second-vendor step A has a failover chain, deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s per call"
  89 |    },
  90 |    "viewer_takeaway": {
  91 |     "chain": [
  92 | diff --git a/pipeline/package.py b/pipeline/package.py
  93 | index 3f69be7..68384f1 100644
  94 | --- a/pipeline/package.py
  95 | +++ b/pipeline/package.py
  96 | @@ -72,6 +72,8 @@ PRESCREEN_N = None                 # RULING 58 (11:00 Nov 13): EVERY candidate i
  97 |                                     # miner's best first; a number keeps the old cap (the re-screens pass their own)
  98 |  PRESCREEN_BATCH = 8                # excerpts per step-A call
  99 |  PRESCREEN_WORKERS = 6              # ruling 58: the step-A batches run in parallel (about 19 batches at 72 h)
 100 | +SECOND_VERDICT_DEADLINE_S = 120.0  # RULING 82 (20:02 Nov 13): each second-vendor / off-writer step-A call; at it the next
 101 | +SECOND_VERDICT_BATCH = 2           # model (deepseek -> glm-5.3-flash -> qwen3.8-27b); small batches so one fits in it
 102 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
 103 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
 104 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 105 | @@ -486,7 +488,7 @@ def src_of(x, sources):
 106 |  
 107 |  
 108 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 109 | -              store=None, log=print, cache=None):
 110 | +              store=None, log=print, cache=None, deadline_s=None):
 111 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 112 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 113 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 114 | @@ -538,7 +540,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 115 |      def screen(i, chunk):
 116 |          try:
 117 |              return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
 118 | -                             seed=7 + i * batch, writer_family=writer_family), None
 119 | +                             seed=7 + i * batch, writer_family=writer_family, deadline_s=deadline_s,
 120 | +                             failover=deadline_s is not None), None          # ruling 82: the chain, per call
 121 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 122 |              return None, e
 123 |      with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
 124 | @@ -581,12 +584,13 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 125 |      for mid, m in cleared.items():
 126 |          b = router.backends.get((a_by.get(mid) or {}).get("backend"))
 127 |          groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
 128 | -    jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
 129 | -            for i in range(0, len(g), PRESCREEN_BATCH)]
 130 | +    jobs = [(k, g[i:i + SECOND_VERDICT_BATCH]) for k, g in groups.items() if k is not None
 131 | +            for i in range(0, len(g), SECOND_VERDICT_BATCH)]
 132 |      def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
 133 |          try:
 134 |              return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
 135 | -                             cache=cache)                    # ruling 58: a second verdict is paid for once too
 136 | +                             cache=cache, batch=SECOND_VERDICT_BATCH,    # ruling 58: a second verdict is paid once;
 137 | +                             deadline_s=SECOND_VERDICT_DEADLINE_S)       # ruling 82: the chain, 120 s a call
 138 |          except Exception as e:
 139 |              return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 140 |                          for m in chunk}, set(), set()
 141 | @@ -2813,6 +2817,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 142 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
 143 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 144 |                          got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 145 | +                                                         batch=SECOND_VERDICT_BATCH,      # ruling 82: off the writer,
 146 | +                                                         deadline_s=SECOND_VERDICT_DEADLINE_S,   # the chain, 120 s
 147 |                                                           n=len(stale), store=None, cache=step_a_cache)
 148 |                          bad = {}
 149 |                          for m in stale:
 150 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 151 | index b85c1f4..99f713c 100644
 152 | --- a/tests/package/test_ledger_build.py
 153 | +++ b/tests/package/test_ledger_build.py
 154 | @@ -762,6 +762,18 @@ class TestDriverRefuses(unittest.TestCase):
 155 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 156 |                           before)
 157 |  
 158 | +    def test_ruling_82_the_context_verdict_chain(self):
 159 | +        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the three Heimdall
 160 | +        models in the ruled order; glm-5.3-flash is a Heimdall back-end of its own family."""
 161 | +        sys.path.insert(0, HERE)
 162 | +        import proof_ly as PL
 163 | +        self.assertEqual(PL.chains()["context_verdict"], ["xai:grok-4.20-0309-reasoning",
 164 | +                                                          "heimdall:deepseek/deepseek-v4.1-flash",
 165 | +                                                          "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b"])
 166 | +        with open(os.path.join(REPO, "pipeline", "model_providers.json")) as f:
 167 | +            glm = json.load(f)["backends"]["heimdall:z-ai/glm-5.3-flash"]
 168 | +        self.assertEqual((glm["vendor"], glm["family"], glm["model"]), ("heimdall", "glm", "z-ai/glm-5.3-flash"))
 169 | +
 170 |      def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
 171 |          """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
 172 |          carry the approved text, for the same-speech rule."""
 173 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 174 | index 63732d9..b9e6fd5 100644
 175 | --- a/tests/package/test_medley.py
 176 | +++ b/tests/package/test_medley.py
 177 | @@ -562,7 +562,7 @@ class Rig:
 178 |          self.write_avoid = []
 179 |  
 180 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 181 | -                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None):
 182 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None):
 183 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 184 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 185 |          av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
 186 | @@ -1115,7 +1115,7 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 187 |          import context_integrity as CI
 188 |          from test_gates import a_item
 189 |  
 190 | -        def step_a(router_, contexts, wv, seed=7, writer_family=None):
 191 | +        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False):
 192 |              calls.append((sorted(contexts), seed))
 193 |              if set(contexts) & set(fail):
 194 |                  raise RuntimeError("the batch reply was out of contract")
 195 | @@ -2345,7 +2345,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 196 |                    a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
 197 |          out = rig.run()
 198 |          self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
 199 | -        self.assertEqual(rig.screens[1], ("heimdall:deepseek", ["h", "x", "y", "z"]))  # the second, off xai
 200 | +        self.assertEqual(rig.screens[1:3], [("heimdall:deepseek", ["h", "x"]),          # the second, off xai, in
 201 | +                                            ("heimdall:deepseek", ["y", "z"])])         # ruling 82's chunks of 2
 202 |          self.assertLess(rig.events.index("step_a:heimdall:deepseek"), rig.events.index("angle_write"))
 203 |          sv = out["prescreen"]["second_vendor"]
 204 |          self.assertEqual(sv["h"], "PASS (heimdall:deepseek)")
 205 | @@ -2373,7 +2374,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 206 |          self.assertEqual(set(rig.a_seen[0].values()), {"heimdall:deepseek"})
 207 |          self.assertEqual(rig.write_avoid, [{"heimdall"}])          # and every write avoids Heimdall, so with the two
 208 |          # real vendors the writers never span both and a verdict off them always exists (audit 0640 C1, glm cond. 1)
 209 | -        self.assertEqual(len(rig.screens), 2)                      # and no re-screen was needed after the write
 210 | +        self.assertEqual(len(rig.screens), 3)                      # (the second screen in two chunks of 2) and no
 211 | +        #   re-screen was needed after the write
 212 |          self.assertIsNotNone(out["package"])
 213 |  
 214 |      def test_a_clip_that_fails_its_re_screen_is_swapped_out_alone_and_the_line_up_carries_on(self):
 215 | @@ -2389,8 +2391,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 216 |          self.assertIn("swapped {'y': 'z'}", out["tried"][0]["why"])
 217 |          self.assertIn("(out for good)", out["tried"][0]["why"])
 218 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 219 | -        self.assertEqual(rig.screens[2], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 220 | -        self.assertEqual(rig.screens[3], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 221 | +        self.assertEqual(rig.screens[3], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 222 | +        self.assertEqual(rig.screens[4], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 223 |  
 224 |      def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
 225 |          """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
 226 | @@ -2435,10 +2437,12 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 227 |          ms = {m["moment_id"]: m for m in self.MS}
 228 |          a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
 229 |                  "z": {"backend": "heimdall:deepseek"}}
 230 | -        seen = []
 231 | +        seen, calls = [], []
 232 |  
 233 | -        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None):
 234 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
 235 | +                 deadline_s=None):
 236 |              seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
 237 | +            calls.append((batch, deadline_s))
 238 |              name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
 239 |              return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
 240 |          saved = PK.prescreen
 241 | @@ -2451,6 +2455,43 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 242 |          self.assertEqual(sorted(two), ["h", "x"])
 243 |          self.assertTrue(fail["y"][0].startswith("STEP_A_UNKNOWN_BACKEND: the first verdict's back-end 'nowhere:model'"))
 244 |          self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 245 | +        self.assertEqual(set(calls), {(PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S)})   # ruling 82
 246 | +        self.assertEqual((PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S), (2, 120.0))
 247 | +
 248 | +    def test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain(self):
 249 | +        """RULING 82 (20:02 Nov 13): off the first verdict's vendor (xAI), deepseek -> glm-5.3-flash -> qwen3.8-27b,
 250 | +        each call bounded by 120 s; a model that is down, past the deadline, or answers out of contract hands over to
 251 | +        the next; all three failing is no verdict (never cached, never a pass)."""
 252 | +        import tempfile
 253 | +        import context_integrity as CI
 254 | +        sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
 255 | +        from test_providers import Fake, router as mk_router
 256 | +        from test_gates import CTX, a_item
 257 | +        good = json.dumps({"excerpts": [a_item(lb) for lb in CTX]})
 258 | +        with tempfile.TemporaryDirectory() as d:
 259 | +            x = Fake("xai:grok", "xai", answer=good, family="grok")
 260 | +            ds = Fake("heimdall:deepseek", "heimdall", fail="503 from the gateway", family="deepseek")
 261 | +            glm = Fake("heimdall:glm", "heimdall", answer="not one JSON object", family="glm")
 262 | +            qw = Fake("heimdall:qwen", "heimdall", answer=good, family="qwen")
 263 | +            r = mk_router(d, [x, ds, glm, qw], {"context_verdict": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
 264 | +                                                                      "heimdall:qwen"]})
 265 | +            asked = []
 266 | +            inner = r.call
 267 | +            r.call = lambda role, prompt, *a, **k: (asked.append(k.get("deadline_s")), inner(role, prompt, *a, **k))[1]
 268 | +            got, backend = CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
 269 | +            self.assertEqual((backend, x.calls, ds.calls, glm.calls, qw.calls), ("heimdall:qwen", 0, 1, 1, 1))
 270 | +            self.assertEqual(set(asked), {120.0})                      # every call of the chain bounded
 271 | +            self.assertEqual(sorted(got), sorted(CTX))
 272 | +            with self.assertRaises(ValueError):                        # without failover: as before, the bad answer
 273 | +                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"})    # raises (the first verdict's path)
 274 | +            qw.answer = "still not JSON"
 275 | +            with self.assertRaises(P_ProviderError()):                 # all three spent: no verdict (law L-m)
 276 | +                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
 277 | +
 278 | +
 279 | +def P_ProviderError():
 280 | +    import providers
 281 | +    return providers.ProviderError
 282 |  
 283 |  
 284 |  class TestRuling53Reposted(unittest.TestCase):
 285 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). Only state what
you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- Step A is a context verdict on each clip (role context_verdict). The router (providers.Router.call) tries the
  role's chain in order. It skips a back-end on the vendor or family to avoid, or marked down. It moves on when a
  back-end is unavailable, refuses, misses the call's deadline_s (logged to the Heimdall evidence file, item 55), or
  answers empty. It raises ProviderError when the chain is spent.
- Step A's FIRST verdict is xAI's (grok). ORDER 06:22 item 45: every cuttable clip also gets a SECOND verdict off the
  first verdict's vendor and family (second_screen), BEFORE the angle step. Whichever vendor then writes, a verdict
  off the writer exists (law L-x: a generator never judges its own text). After a write, a clip whose usable verdict
  is on the writer's vendor or family is re-screened off it (the off-writer re-screen).
- Frozen vendors (openai, anthropic, local) are removed from every chain (tests/package/proof_ly.chains). So the
  second screen, which avoids xAI, had ONE model: Heimdall deepseek-v4.1-flash.
- On 19:23 / 19:4x Nov 13, a batch of step-A calls there spent its whole output budget with an empty answer. The
  chain was spent, 6 of 14 clips got no second verdict, and the build died at line-up formation.

The order, RULING 82 (orchestrator 20:02 Nov 13): "THE SECOND-VENDOR STEP A HAS A FAILOVER CHAIN. Off-writer verdict
order: Heimdall deepseek-v4.1-flash, then Heimdall z-ai/glm-5.3-flash (pp-ingest measured it 24/24 on calibration
today), then Heimdall qwen3.8-27b. Per-call deadline 120 s, not 300: at the deadline go to the next model at once,
record the miss in the Heimdall evidence file (item 55). The rule that matters is unchanged: the second verdict must
come from a model family different from the FIRST verdict's (xAI) and, for a clip the writer quotes, different from the
writer's. An outage verdict is never cached (as now)."

The change:
1. pipeline/model_providers.json:
   - a new back-end heimdall:z-ai/glm-5.3-flash (vendor heimdall, family glm);
   - context_verdict's chain is now xai, anthropic (frozen), heimdall deepseek, heimdall glm, heimdall qwen, local
     (frozen). With the frozen legs out: xai -> deepseek -> glm -> qwen.
2. context_integrity.step_a(..., deadline_s=None, failover=False):
   - deadline_s bounds each call (the router moves on and logs the miss);
   - failover=True also moves to the next model when an answer is OUT OF CONTRACT (each model once, via avoid_model).
     The router alone moves on only on errors and empty answers. When the chain is spent: ProviderError, so no
     verdict.
   - Without failover (the first verdict's path), a bad answer still raises, as before.
3. package.py:
   - SECOND_VERDICT_DEADLINE_S = 120 and SECOND_VERDICT_BATCH = 2;
   - prescreen(..., deadline_s) passes deadline_s and failover=(deadline_s is not None) to step_a;
   - second_screen chunks by 2 and passes the deadline;
   - the off-writer re-screen passes batch 2 and the deadline.
   Batches of 2 keep one call inside 120 s: deepseek took 284-304 s for 8 excerpts. Every verdict is still cached per
   moment (ruling 58), so no moment is paid for twice. A call that fails is never cached (unchanged).
4. Tests:
   - test_medley: the chain fails over (deepseek down, then glm out of contract, then qwen answers; every call
     asked with 120 s); without failover a bad answer raises; all three failing raises (no verdict). The second screen
     passes batch 2 and 120 s. Stubs accept the new arguments, and three tests' call counts follow the chunks of 2.
   - test_ledger_build: the frozen-out chain is exactly xai -> deepseek -> glm -> qwen; glm is family "glm".
   - Mutation runs: removing the failover, the deadline, or the batch / deadline in second_screen each fails a test.
   - 15 suites OK.

Known cost, by design: ruling 48's ledger books an ABANDONED call's upper bound (about $0.24 for a Heimdall call with
16000 output tokens) as spent, because no vendor report exists for it. Batches of 2 are meant to keep calls inside the
deadline.

Check, against the diff:
- the family rule: no second verdict can come from xAI (the first verdict's vendor), and none from the writer's family
  for a clip it quotes;
- that no answer out of contract can ever be a verdict, and the failover loop terminates;
- that the first verdict's path is unchanged (no failover there, no deadline);
- that nothing is cached from a call that failed;
- that the batch / deadline wiring reaches every second-vendor and off-writer call.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

