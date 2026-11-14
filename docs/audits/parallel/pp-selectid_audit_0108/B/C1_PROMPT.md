# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0108B
# Branch: pp-selectid
# Generated: 2026-11-14 01:08 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0108/B/C1_STEP.diff (1491 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index c30f043..3f32a94 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -318,7 +318,7 @@ def check(router, package, sources, writer_vendor, seed=7):
   6 |      return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
   7 |  
   8 |  
   9 | -def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False):
  10 | +def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
  11 |      """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
  12 |      Raises ValueError / ProviderError when it cannot be had or read. RULING 82 (20:02 Nov 13): deadline_s bounds each
  13 |      call (the router moves to the next model at it and logs the miss, item 55); failover=True also moves on when a
  14 | @@ -336,7 +336,8 @@ def step_a(router, contexts, writer_vendor, seed=7, writer_family=None, deadline
  15 |      while True:
  16 |          ra = router.call("context_verdict", prompt, 4000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
  17 |                           **({"avoid_model": set(skip)} if skip else {}),
  18 | -                         **({"deadline_s": deadline_s} if deadline_s is not None else {}))
  19 | +                         **({"deadline_s": deadline_s} if deadline_s is not None else {}),
  20 | +                         **({"kind": kind} if kind else {}))      # ruling 88: step_a_first / step_a_second
  21 |          try:
  22 |              A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
  23 |              a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
  24 | @@ -485,7 +486,7 @@ def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None,
  25 |      try:
  26 |          if a_by is None:
  27 |              a_by, out["backends"]["A"] = step_a(router, {lb: contexts[lb] for lb in labels}, writer_vendor, seed,
  28 | -                                                writer_family)
  29 | +                                                writer_family, kind="step_a_first")
  30 |          else:
  31 |              missing = [lb for lb in labels if not isinstance(a_by.get(lb), dict) or set(A_KEYS) - set(a_by[lb])]
  32 |              if missing:
  33 | @@ -493,45 +494,56 @@ def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None,
  34 |              a_by = {lb: a_by[lb] for lb in labels}
  35 |              out["backends"]["A"] = {lb: a_by[lb].get("backend") or "precomputed (unnamed)" for lb in labels}
  36 |          lab_list = ", ".join(all_labels)
  37 | -        r0 = router.call("viewer_takeaway", STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
  38 | -                         3000, seed)
  39 | -        out["backends"]["B0"] = r0.backend
  40 | -        B0 = _strict(r0.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  41 | +
  42 | +        def parse_b0(text):
  43 | +            B0 = _strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  44 | +                                                            "relations": ("labels", "relation")})
  45 | +            b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
  46 | +            if not set(labels) <= set(b0_by):
  47 | +                raise ValueError(f"step B (clips alone) must answer at least {labels}")
  48 | +            return b0_by
  49 | +
  50 | +        def parse_b(text):
  51 | +            B = _strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  52 |                                                             "relations": ("labels", "relation")})
  53 | -        b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
  54 | -        if not set(labels) <= set(b0_by):
  55 | -            raise ValueError(f"step B (clips alone) must answer at least {labels}")
  56 | -        rb = router.call("viewer_takeaway", STEP_B.format(package=package_view(package), labels=lab_list), 3000, seed,
  57 | -                         avoid_vendor=writer_vendor, avoid_family=writer_family)
  58 | +            b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
  59 | +            if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
  60 | +                raise ValueError(f"step B must answer at least {labels}")
  61 | +            pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
  62 | +            got = []
  63 | +            for rel in B["relations"]:
  64 | +                labs = rel.get("labels")
  65 | +                if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
  66 | +                        labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
  67 | +                    raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
  68 | +                got.append(frozenset(labs))
  69 | +            if len(got) != len(set(got)) or set(got) != pairs_want:
  70 | +                raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
  71 | +                                 f"{len(set(got))} distinct of {len(got)})")
  72 | +            return B, b_by
  73 | +        # the 20:33 order: an answer out of contract moves on to the next model (providers.call_parsed)
  74 | +        r0, b0_by = P.call_parsed(router, "viewer_takeaway",
  75 | +                                  STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
  76 | +                                  parse_b0, 3000, seed)
  77 | +        out["backends"]["B0"] = r0.backend
  78 | +        rb, (B, b_by) = P.call_parsed(router, "viewer_takeaway",
  79 | +                                      STEP_B.format(package=package_view(package), labels=lab_list), parse_b, 3000,
  80 | +                                      seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  81 |          out["backends"]["B"] = rb.backend
  82 | -        B = _strict(rb.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
  83 | -                                                          "relations": ("labels", "relation")})
  84 | -        b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
  85 | -        if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
  86 | -            raise ValueError(f"step B must answer at least {labels}")
  87 | -        pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
  88 | -        got = []
  89 | -        for rel in B["relations"]:
  90 | -            labs = rel.get("labels")
  91 | -            if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
  92 | -                    labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
  93 | -                raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
  94 | -            got.append(frozenset(labs))
  95 | -        if len(got) != len(set(got)) or set(got) != pairs_want:
  96 | -            raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
  97 | -                             f"{len(set(got))} distinct of {len(got)})")
  98 |          text_of = {sg["label"]: sg["text"] for sg in segs}
  99 |          pairs = "\n".join(f'<pair label="{lb}"><A>{_q(a_by[lb]["proposition"], 400)} (certainty: '
 100 |                            f'{a_by[lb]["certainty"]})</A><CLIP>{_q(text_of[lb], 900)}</CLIP><B>{_q(b_by[lb]["asserts"], 400)}'
 101 |                            f' (certainty: {b_by[lb]["certainty"]})</B></pair>' for lb in labels)
 102 | -        rc = router.call("context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), 2000, seed,
 103 | -                         avoid_vendor=writer_vendor, avoid_family=writer_family)
 104 | +        def parse_c(text):
 105 | +            C = _strict(text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 106 | +                                                    "stronger_certainty", "raising_words")})
 107 | +            c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 108 | +            if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 109 | +                raise ValueError(f"step C must answer exactly the labels {labels}")
 110 | +            return c_by
 111 | +        rc, c_by = P.call_parsed(router, "context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), parse_c,
 112 | +                                 2000, seed, avoid_vendor=writer_vendor, avoid_family=writer_family, kind="step_c")
 113 |          out["backends"]["C"] = rc.backend
 114 | -        C = _strict(rc.text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 115 | -                                                   "stronger_certainty", "raising_words")})
 116 | -        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 117 | -        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 118 | -            raise ValueError(f"step C must answer exactly the labels {labels}")
 119 |      except (P.ProviderError, P.SpendLimit, ValueError, KeyError, TypeError) as e:
 120 |          for r_ in (r0, rb, rc):
 121 |              if r_ is not None and isinstance(e, (ValueError, KeyError, TypeError)) and hasattr(router, "reject"):
 122 | diff --git a/pipeline/moments.py b/pipeline/moments.py
 123 | index cfed885..7d55d31 100644
 124 | --- a/pipeline/moments.py
 125 | +++ b/pipeline/moments.py
 126 | @@ -378,21 +378,19 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
 127 |      if why:
 128 |          return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
 129 |                  "replayed": False}
 130 | -    r = None
 131 | -    try:
 132 | -        r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
 133 | -                                                                     moment=quote_data(moment_text, 1500),
 134 | -                                                                     after=quote_data(after_text, 3000)), 800, seed,
 135 | -                        avoid_model=avoid_model)
 136 | -        obj = json.loads(r.text.strip())
 137 | +    def parse(text):
 138 | +        obj = json.loads(text.strip())
 139 |          if not isinstance(obj, dict) or set(obj) != {"risks", "about_bitcoin", "why"} or \
 140 |                  not isinstance(obj["risks"], list) or any(not isinstance(x, str) or x not in HARD_RISKS
 141 |                                                            for x in obj["risks"]) or \
 142 |                  obj["about_bitcoin"] not in ("yes", "no", "uncertain"):
 143 |              raise ValueError("the verdict does not match its contract")
 144 | +        return obj
 145 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 146 | +        r, obj = P.call_parsed(router, "exclusion_verdict", EXCLUSION_PROMPT.format(
 147 | +            before=quote_data(before_text, 3000), moment=quote_data(moment_text, 1500),
 148 | +            after=quote_data(after_text, 3000)), parse, 800, seed, avoid_model=avoid_model)
 149 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 150 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 151 | -            router.reject(r)
 152 |          return {"verdict": "exclude", "why": f"no readable verdict ({type(e).__name__}: {str(e)[:160]})",
 153 |                  "risks": [], "backend": None, "measured": False, "replayed": False}
 154 |      meas = {"measured": True, "replayed": bool(getattr(r, "replayed", False))}
 155 | diff --git a/pipeline/package.py b/pipeline/package.py
 156 | index 4736b4f..a996c3b 100644
 157 | --- a/pipeline/package.py
 158 | +++ b/pipeline/package.py
 159 | @@ -489,7 +489,7 @@ def src_of(x, sources):
 160 |  
 161 |  
 162 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 163 | -              store=None, log=print, cache=None, deadline_s=None):
 164 | +              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None):
 165 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 166 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 167 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 168 | @@ -542,7 +542,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 169 |          try:
 170 |              return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
 171 |                               seed=7 + i * batch, writer_family=writer_family, deadline_s=deadline_s,
 172 | -                             failover=deadline_s is not None), None          # ruling 82: the chain, per call
 173 | +                             failover=(deadline_s is not None) if failover is None else failover,   # ruling 82
 174 | +                             kind=kind), None
 175 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 176 |              return None, e
 177 |      with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
 178 | @@ -571,6 +572,23 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 179 |      return a_by, fails, vendors, families
 180 |  
 181 |  
 182 | +def first_bounds(router):
 183 | +    """The kwargs of step A's FIRST screen. RULING 85: under heimdall_first the first verdict is a Heimdall family's,
 184 | +    2 clips and 120 s a call (Heimdall needs a median 268 s on 8 clips); today it keeps its batches with no deadline.
 185 | +    One helper for both builds (the medley's and the spotlight's)."""
 186 | +    return {"batch": SECOND_VERDICT_BATCH, "deadline_s": SECOND_VERDICT_DEADLINE_S} \
 187 | +        if getattr(router, "routing", "today") == "heimdall_first" else {}
 188 | +
 189 | +
 190 | +def _second_bounds(router):
 191 | +    """(batch, deadline_s) of step A's second verdict. Today it is a Heimdall family's (ruling 82: 2 clips, 120 s a
 192 | +    call). RULING 88 (c), under heimdall_first, it is Grok confirming a Heimdall pass: Grok's own batch (8 clips) and no
 193 | +    deadline, since the per-clip cost falls with the batch."""
 194 | +    if getattr(router, "routing", "today") == "heimdall_first":
 195 | +        return PRESCREEN_BATCH, None
 196 | +    return SECOND_VERDICT_BATCH, SECOND_VERDICT_DEADLINE_S
 197 | +
 198 | +
 199 |  def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 200 |      """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
 201 |      known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
 202 | @@ -585,13 +603,14 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 203 |      for mid, m in cleared.items():
 204 |          b = router.backends.get((a_by.get(mid) or {}).get("backend"))
 205 |          groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
 206 | -    jobs = [(k, g[i:i + SECOND_VERDICT_BATCH]) for k, g in groups.items() if k is not None
 207 | -            for i in range(0, len(g), SECOND_VERDICT_BATCH)]
 208 | +    batch, dl = _second_bounds(router)
 209 | +    jobs = [(k, g[i:i + batch]) for k, g in groups.items() if k is not None
 210 | +            for i in range(0, len(g), batch)]
 211 |      def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
 212 |          try:
 213 |              return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
 214 | -                             cache=cache, batch=SECOND_VERDICT_BATCH,    # ruling 58: a second verdict is paid once;
 215 | -                             deadline_s=SECOND_VERDICT_DEADLINE_S)       # ruling 82: the chain, 120 s a call
 216 | +                             cache=cache, batch=batch, deadline_s=dl,    # ruling 58: a second verdict is paid once;
 217 | +                             kind="step_a_second", failover=True)        # ruling 82 / 88 (c): the chain
 218 |          except Exception as e:
 219 |              return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 220 |                          for m in chunk}, set(), set()
 221 | @@ -709,35 +728,30 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 222 |      cands = "\n".join(f'CANDIDATE id="{m["moment_id"]}" (on screen: {CI._q(_name(m, ctx), 80)}): '
 223 |                        f'"{CI._q(m["text"], 900)}"' for m in todo)
 224 |      keys = ", ".join(f'"{i}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}' for i in ids)
 225 | -    err = None
 226 | -    for s in (seed, seed + 1):
 227 | -        r = None
 228 | -        try:
 229 | -            r = router.call("coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), 600 + 150 * len(ids), s,
 230 | -                            avoid_vendor=writer_vendor, avoid_family=writer_family)
 231 | -            v = json.loads(r.text.strip())
 232 | -            h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 233 | -            if not isinstance(h, dict) or set(h) != set(ids) or any(
 234 | -                    not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
 235 | -                    any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 236 | -                raise ValueError("hook ratings out of contract")
 237 | -        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:
 238 | -            if r is not None and isinstance(e, (ValueError, TypeError, KeyError)):
 239 | -                router.reject(r)
 240 | -            err = f"{type(e).__name__}: {str(e)[:200]}"
 241 | -            if isinstance(e, (ValueError, TypeError, KeyError)):
 242 | -                continue                                 # out of contract: one re-ask
 243 | -            break                                        # unavailable or the spend guard: no verdict (law L-m)
 244 | -        new = {}
 245 | -        for m in todo:
 246 | -            x = h[m["moment_id"]]
 247 | -            rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 248 | -                   "backend": r.backend, "rule": HOOK_OWN_RULE}       # ruling 61: scroll / alone
 249 | -            out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 250 | -            new[key(m)] = {r.backend: rec}
 251 | -        _cache_put(cache, new)
 252 | -        return out, None
 253 | -    return out, err
 254 | +
 255 | +    def parse(text):
 256 | +        v = json.loads(text.strip())
 257 | +        h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 258 | +        if not isinstance(h, dict) or set(h) != set(ids) or any(
 259 | +                not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
 260 | +                any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 261 | +            raise ValueError("hook ratings out of contract")
 262 | +        return h
 263 | +    try:                                         # the 20:33 order: an answer out of contract moves on to the next
 264 | +        r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), parse,
 265 | +                             600 + 150 * len(ids), seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 266 | +                             kind="hook")                                # ruling 88: the hook rating's own list
 267 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # (it was one re-ask of the same
 268 | +        return out, f"{type(e).__name__}: {str(e)[:200]}"     # model) unavailable, all out of contract, or the guard
 269 | +    new = {}
 270 | +    for m in todo:
 271 | +        x = h[m["moment_id"]]
 272 | +        rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 273 | +               "backend": r.backend, "rule": HOOK_OWN_RULE}           # ruling 61: scroll / alone
 274 | +        out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 275 | +        new[key(m)] = {r.backend: rec}
 276 | +    _cache_put(cache, new)
 277 | +    return out, None
 278 |  
 279 |  TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
 280 |                   "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
 281 | @@ -1492,21 +1506,22 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 282 |      `hook`) is written to verdict["clips"]["hook"]; without one the verdict fails closed (law L-m). The clips after the
 283 |      hook and vo_point are rated as before; the judge sees the hook's text for context."""
 284 |      import providers as P
 285 | -    r = None
 286 |      labs = [sg["label"] for sg in pk["segments"]]
 287 |      own = hook_own(hook)
 288 | -    try:
 289 | -        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
 290 | -                            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 291 | -                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 292 | -        v = json.loads(r.text.strip())
 293 | +
 294 | +    def parse(text):
 295 | +        v = json.loads(text.strip())
 296 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 297 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 298 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 299 |              raise ValueError("coherence verdict out of contract")
 300 | +        return v
 301 | +    try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 302 | +        r, v = P.call_parsed(router, "coherence_verdict", COHERENCE_PROMPT.format(
 303 | +                                 package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 304 | +                             parse, 1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 305 | +                             kind="coherence")                           # ruling 88: coherence's own list
 306 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 307 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 308 | -            router.reject(r)
 309 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
 310 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 311 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 312 | @@ -1549,13 +1564,8 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 313 |      own = hook_own(segs[0]) if segs else None
 314 |      clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 315 |                        for lb, m in zip(labs, segs))
 316 | -    r = None
 317 | -    try:
 318 | -        r = router.call("coherence_verdict",
 319 | -                        MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
 320 | -                                             joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 321 | -                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 322 | -        v = json.loads(r.text.strip())
 323 | +    def parse(text):
 324 | +        v = json.loads(text.strip())
 325 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 326 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 327 |                  any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 328 | @@ -1563,9 +1573,15 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 329 |                  any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 330 |                      or not isinstance(x["why"], str) for x in v["joins"].values()):
 331 |              raise ValueError("clips-alone verdict out of contract")
 332 | +        return v
 333 | +    try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 334 | +        r, v = P.call_parsed(router, "coherence_verdict",
 335 | +                             MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
 336 | +                                                  joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}'
 337 | +                                                                  for j in js)),
 338 | +                             parse, 1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 339 | +                             kind="clips_alone")                         # ruling 88: clips-alone's own list
 340 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 341 | -        if r is not None and isinstance(e, (ValueError, TypeError)):
 342 | -            router.reject(r)
 343 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 344 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 345 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 346 | @@ -2289,7 +2305,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 347 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 348 |      wv, wf = _writers(router)
 349 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 350 | -                                                   cache=step_a_cache)          # ruling 58: every candidate, once
 351 | +                                                   cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 352 | +                                                   **first_bounds(router))
 353 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 354 |      levels = current_levels(sources.values(), ctx)
 355 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 356 | @@ -2493,8 +2510,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 357 |          return None
 358 |      for mid in cleared:
 359 |          a_by[mid] = off_writers(mid) or a_by[mid]
 360 | -    writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
 361 | -        {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
 362 | +    import providers as P
 363 | +    ab = router.backends.get(angle_reply.backend)       # every write stays on the angle's GATEWAY (ruling 85: under
 364 | +    writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
 365 | +        {P.gateway(ab) if ab is not None else angle_reply.vendor}   # heimdall_first a family is its own maker, and
 366 | +    # a write may still fail over deepseek -> qwen as today); the verdicts avoid every writer's maker and family
 367 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)" if candidate is None else
 368 |          f"  ruling 66: the candidate {candidate.get('source')} tried[{candidate.get('index')}] (angle "
 369 |          f"{candidate['ai'] + 1} line-up {candidate['n_lineup']}), as judged: its angle from {angle_reply.backend}, "
 370 | @@ -2857,10 +2877,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 371 |                      stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
 372 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
 373 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 374 | +                        rb, rdl = _second_bounds(router)
 375 |                          got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 376 | -                                                         batch=SECOND_VERDICT_BATCH,      # ruling 82: off the writer,
 377 | -                                                         deadline_s=SECOND_VERDICT_DEADLINE_S,   # the chain, 120 s
 378 | -                                                         n=len(stale), store=None, cache=step_a_cache)
 379 | +                                                         batch=rb, deadline_s=rdl,        # ruling 82: off the writer,
 380 | +                                                         n=len(stale), store=None, cache=step_a_cache,
 381 | +                                                         kind="step_a_second", failover=True)   # ruling 88 (c)
 382 |                          bad = {}
 383 |                          for m in stale:
 384 |                              mid = m["moment_id"]
 385 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
 386 | index c479135..77c3efb 100644
 387 | --- a/pipeline/speakers.py
 388 | +++ b/pipeline/speakers.py
 389 | @@ -340,10 +340,10 @@ def attribute(router, seg, src, meta, seed=7, caps=None, lower_third=None):
 390 |      prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip(),
 391 |                             turn=turn["text"] if turn else f"(none: {turn_why})")
 392 |      r = None
 393 | -    try:
 394 | -        r = router.call("speaker_verdict", prompt, 900, seed)
 395 | -        v = _json(r.text)
 396 | -        rec = check(v, lines, clip, f"{before} {after}")
 397 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 398 | +        r, (v, rec) = P.call_parsed(router, "speaker_verdict", prompt,
 399 | +                                    lambda t: (lambda v: (v, check(v, lines, clip, f"{before} {after}")))(_json(t)),
 400 | +                                    900, seed)
 401 |          ev = check_turn(v.get("turn"), rec["people"], turn["text"] if turn else "")
 402 |          rec = decide(rec, ev, rec["people"], lower_third)
 403 |          rec["turn"] = {"read": turn is not None, "why": turn_why, **({"source": cap_src, "start": turn["start"],
 404 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 405 | index 88ae8ad..d2bb3d4 100644
 406 | --- a/pipeline/spotlight.py
 407 | +++ b/pipeline/spotlight.py
 408 | @@ -776,7 +776,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 409 |      out["scorer"] = srec
 410 |      ms = [P.with_verdict(m, idx) for m in ms]
 411 |      wv, wf = P._writers(router)
 412 | -    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache)
 413 | +    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache,
 414 | +                                    kind="step_a_first", **P.first_bounds(router))   # as the medley's (rulings 85, 88)
 415 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 416 |      for m in ms:
 417 |          if m["moment_id"] not in cleared:
 418 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 419 | index af4ccc1..d0bb83c 100644
 420 | --- a/pipeline/vo_fidelity.py
 421 | +++ b/pipeline/vo_fidelity.py
 422 | @@ -728,16 +728,13 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 423 |      import providers as P
 424 |      det = check_deterministic(segments, lines, manifest, current_levels)
 425 |      out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False, "seed": seed}
 426 | -    r = None
 427 | -    try:
 428 | -        r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
 429 | -                        avoid_vendor=writer_vendor, avoid_family=writer_family)
 430 | +    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 431 | +        r, out["verdict"] = P.call_parsed(router, "fidelity_verdict", verdict_prompt(segments, lines, manifest),
 432 | +                                          lambda t: check_verdict(t, segments, lines, manifest), 2500, seed,
 433 | +                                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 434 |          out["backend"], out["replayed"] = r.backend, bool(getattr(r, "replayed", False))
 435 | -        out["verdict"] = check_verdict(r.text, segments, lines, manifest)
 436 |          out["measured"] = True
 437 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 438 | -        if r is not None and isinstance(e, (ValueError, TypeError)) and hasattr(router, "reject"):
 439 | -            router.reject(r, str(e))
 440 |          out["verdict"] = {"ok": False, "claims": [], "violations": [{"slot": "-", "rule": "VERDICT_UNAVAILABLE",
 441 |                                                                        "detail": f"{type(e).__name__}: {str(e)[:200]}"}]}
 442 |      out["violations"] = det["violations"] + out["verdict"]["violations"]
 443 | diff --git a/tests/package/replay85.py b/tests/package/replay85.py
 444 | new file mode 100644
 445 | index 0000000..0644b02
 446 | --- /dev/null
 447 | +++ b/tests/package/replay85.py
 448 | @@ -0,0 +1,670 @@
 449 | +#!/usr/bin/env python3
 450 | +"""RULING 85.1 (orchestrator 21:15 Nov 13): THE REPLAY. Every recorded Grok verdict since the first ledger build is
 451 | +re-asked, with the SAME prompt, of Heimdall's model families: deepseek-v4.1-flash, z-ai/glm-5.3-flash, qwen3.8-27b.
 452 | +No new Grok spend: Grok's answers are read from the recordings (tests/package/fixtures/replies). Each answer is
 453 | +reduced to the pipeline's own DECISION with the pipeline's own parsers and bars, and compared with Grok's:
 454 | +- step A (context_verdict, <excerpt>): per clip, context_integrity.a_failures ([] passes). REFERENT_OUTSIDE is
 455 | +  counted on its own;
 456 | +- step C (context_verdict, <pair>): per clip, entails == "yes". This is a PROXY: the full rule also reads the
 457 | +  context window, which the prompt does not carry;
 458 | +- clips-alone (coherence_verdict, joins): the through-line stated, every clip >= COHERENCE_MIN, flagged joins <=
 459 | +  LY_MAX_BRIDGES; the flagged joins are compared too;
 460 | +- coherence (coherence_verdict, vo_point): the through-line, every rating >= COHERENCE_MIN;
 461 | +- hook rating (coherence_verdict, CANDIDATE): per hook, the lowest of scroll / alone >= HOOK_MIN (ruling 61);
 462 | +- fidelity (fidelity_verdict): per line, every claim "supported": "yes", or commentary with no test "yes". This is a
 463 | +  PROXY: the full check (verbatim supports) needs the package's inputs;
 464 | +- exclusion (exclusion_verdict): keep (no risk, about Bitcoin "yes") or exclude;
 465 | +- speaker (speaker_verdict): the speaker's name or "unknown". Naming no one where Grok named someone is "stricter".
 466 | +- step B (viewer_takeaway) has no decision of its own (it feeds step C): its contract and its time are reported.
 467 | +- The visual sheets (xai_vision) need their images. They are not in the recordings and come in a second pass.
 468 | +Stricter: Heimdall fails what Grok passed. Looser: Heimdall passes what Grok failed. An answer out of contract is
 469 | +"no verdict" (counted, never a pass). The anchors (the verdicts behind the delivered pins 0c68b589, 41f29b1f,
 470 | +37c5b5f5) must still pass; the step-A REFERENT_OUTSIDE refusals must still be refused.
 471 | +
 472 | +Spend: ruling 48's ledger (SPEND_LY.json, the order's $20 cap), roles "replay85_<model>", a reservation per call as
 473 | +always. Replies are recorded under tests/package/proof/replay85/replies, so a re-run is free. A call is abandoned at
 474 | +--deadline (300 s: production cuts at 120 s) and is then a timeout, with no decision; past-120 s answers are counted. RESULTS.jsonl is appended per (record, model); a re-run resumes.
 475 | +Usage: python3 -B tests/package/replay85.py [--workers 2] [--models deepseek,glm,qwen] [--types ...] [--limit N]
 476 | +                                            [--table-only]"""
 477 | +import argparse
 478 | +import glob
 479 | +import json
 480 | +import os
 481 | +import re
 482 | +import statistics
 483 | +import sys
 484 | +import threading
 485 | +import time
 486 | +from concurrent.futures import ThreadPoolExecutor
 487 | +
 488 | +HERE = os.path.dirname(os.path.abspath(__file__))
 489 | +REPO = os.path.dirname(os.path.dirname(HERE))
 490 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 491 | +sys.path.insert(0, HERE)
 492 | +import context_integrity as CI  # noqa: E402
 493 | +import package as PK  # noqa: E402
 494 | +import providers as P  # noqa: E402
 495 | +import speakers as SP  # noqa: E402
 496 | +
 497 | +WT = "/home/ultron/worktrees/pp-selectid"
 498 | +REPLIES = os.path.join(WT, "tests", "package", "fixtures", "replies")
 499 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay85")
 500 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_LY.json")
 501 | +ENV = "/home/ultron/protocol_pulse/" + "." + "env"
 502 | +FIRST_LEDGER = "2026-11-13T07:37:38Z"          # ledger_20261113_073738: the first ledger build (UTC stamp)
 503 | +LIMIT_USD, LIMIT_BASIS = 20.0, "reported"      # ruling 83 (b): the order's cap, on the same ledger
 504 | +DEADLINE_S = 120.0                             # ruling 82's per-call deadline: answers past it are counted
 505 | +MODELS = {"deepseek": "heimdall:deepseek/deepseek-v4.1-flash", "glm": "heimdall:z-ai/glm-5.3-flash",
 506 | +          "qwen": "heimdall:qwen/qwen3.8-27b"}
 507 | +ANCHOR_PINS = {                                # the delivered pins (ruling 85.1's anchors)
 508 | +    "0c68b589": "tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
 509 | +    "41f29b1f": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json",
 510 | +    "37c5b5f5": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json",
 511 | +}
 512 | +TYPES = ("step_a", "step_c", "clips_alone", "coherence", "hook", "fidelity", "exclusion", "speaker", "step_b")
 513 | +DECIDING = tuple(t for t in TYPES if t != "step_b")      # step B has no decision of its own: not asked by default
 514 | +
 515 | +
 516 | +def kind(rec):
 517 | +    """The verdict type of a recorded call, from its role and its prompt's own template markers."""
 518 | +    role, pr = rec.get("role"), rec.get("prompt") or ""
 519 | +    if role == "context_verdict":
 520 | +        return "step_a" if '<excerpt label="' in pr else "step_c" if '<pair label="' in pr else None
 521 | +    if role == "coherence_verdict":
 522 | +        if 'CANDIDATE id="' in pr:
 523 | +            return "hook"
 524 | +        return "clips_alone" if '"followable"' in pr else "coherence" if '"vo_point"' in pr else None
 525 | +    return {"fidelity_verdict": "fidelity", "exclusion_verdict": "exclusion", "speaker_verdict": "speaker",
 526 | +            "viewer_takeaway": "step_b", "visual_check": "visual"}.get(role)
 527 | +
 528 | +
 529 | +def _json(text):
 530 | +    return json.loads(text.strip()) if isinstance(text, str) else None
 531 | +
 532 | +
 533 | +def decide(k, text, prompt):
 534 | +    """The DECISION a verdict's answer makes, by the pipeline's parsers and bars -> {unit: decision}; a decision is
 535 | +    True (pass / keep), False (fail / exclude), or a string (a name, for the speaker). Raises ValueError / TypeError /
 536 | +    KeyError for an answer out of contract (no verdict)."""
 537 | +    if k == "step_a":
 538 | +        labels = re.findall(r'<excerpt label="([^"]+)"', prompt)
 539 | +        A = CI._strict(text, {"excerpts"}, {"excerpts": CI.A_KEYS})
 540 | +        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
 541 | +        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
 542 | +            raise ValueError("step A must answer exactly the prompt's labels")
 543 | +        return {lb: tuple(sorted(CI.a_failures(a_by[lb]))) for lb in labels}
 544 | +    if k == "step_c":
 545 | +        labels = re.findall(r'<pair label="([^"]+)"', prompt)
 546 | +        C = CI._strict(text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 547 | +                                                   "stronger_certainty", "raising_words")})
 548 | +        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 549 | +        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 550 | +            raise ValueError("step C must answer exactly the prompt's labels")
 551 | +        return {lb: c_by[lb]["entails"] == "yes" for lb in labels}
 552 | +    if k in ("clips_alone", "coherence"):
 553 | +        # the prompt's own template names the clip keys; an older template ('"<label>": 1') rated every CLIP label,
 554 | +        # the hook included, and an older contract also carried a top-level "hook" rating (both before ruling 61)
 555 | +        named = re.findall(r'"(clip_\d+)": 1\b', prompt)
 556 | +        labels = re.findall(r'CLIP label="([^"]+)"', prompt)
 557 | +        allowed = [set(named)] if named else [set(labels), set(labels) - {"hook"}]
 558 | +        v = _json(text)
 559 | +        want = {"through_line", "clips", "joins"} if k == "clips_alone" else {"through_line", "clips", "vo_point"}
 560 | +        if not isinstance(v, dict) or set(v) - {"hook"} != want or not isinstance(v["clips"], dict) or \
 561 | +                set(v["clips"]) not in allowed or any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()):
 562 | +            raise ValueError(f"{k} out of contract")
 563 | +        extra = []
 564 | +        if "hook" in v:
 565 | +            hv = v["hook"]
 566 | +            extra = [hv] if type(hv) is int else [x for x in hv.values() if type(x) is int] if isinstance(hv, dict) else []
 567 | +            if not extra or any(not 1 <= x <= 5 for x in extra):
 568 | +                raise ValueError(f"{k}: the hook's rating out of contract")
 569 | +            extra = [min(extra)]
 570 | +        if k == "coherence":
 571 | +            if type(v["vo_point"]) is not int or not 1 <= v["vo_point"] <= 5:
 572 | +                raise ValueError("coherence out of contract")
 573 | +            return {"package": PK._line_ok(v["through_line"]) and
 574 | +                    min(list(v["clips"].values()) + [v["vo_point"]] + extra) >= PK.COHERENCE_MIN}
 575 | +        joins = re.findall(r'"([^"]+ -> [^"]+)": \{"followable"', prompt)
 576 | +        if not isinstance(v["joins"], dict) or set(v["joins"]) != set(joins) or any(
 577 | +                not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 578 | +                for x in v["joins"].values()):
 579 | +            raise ValueError("clips-alone joins out of contract")
 580 | +        flagged = tuple(sorted(j for j in joins if v["joins"][j]["followable"] is False))
 581 | +        ok = PK._line_ok(v["through_line"]) and min(list(v["clips"].values()) + extra) >= PK.COHERENCE_MIN and \
 582 | +            len(flagged) <= PK.LY_MAX_BRIDGES
 583 | +        return {"lineup": ok, "flagged": flagged}
 584 | +    if k == "hook":
 585 | +        ids = re.findall(r'CANDIDATE id="([^"]+)"', prompt)
 586 | +        v = _json(text)
 587 | +        h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 588 | +        if not isinstance(h, dict) or set(h) != set(ids) or any(
 589 | +                not isinstance(x, dict) or any(type(x.get(p)) is not int or not 1 <= x[p] <= 5 for p in PK.HOOK_PARTS)
 590 | +                for x in h.values()):
 591 | +            raise ValueError("hook ratings out of contract")
 592 | +        return {i: min(h[i][p] for p in PK.HOOK_OWN) >= PK.HOOK_MIN for i in ids}
 593 | +    if k == "exclusion":
 594 | +        o = _json(text)
 595 | +        if not isinstance(o, dict) or set(o) != {"risks", "about_bitcoin", "why"} or not isinstance(o["risks"], list) \
 596 | +                or o["about_bitcoin"] not in ("yes", "no", "uncertain"):
 597 | +            raise ValueError("exclusion out of contract")
 598 | +        return {"moment": not o["risks"] and o["about_bitcoin"] == "yes"}
 599 | +    if k == "fidelity":
 600 | +        o = _json(text)
 601 | +        if not isinstance(o, dict) or set(o) != {"claims"} or not isinstance(o["claims"], list):
 602 | +            raise ValueError("fidelity out of contract")
 603 | +        by = {}
 604 | +        for c in o["claims"]:
 605 | +            if not isinstance(c, dict) or not isinstance(c.get("line"), str) or \
 606 | +                    c.get("supported") not in ("yes", "no", "uncertain", "n/a") or not isinstance(c.get("tests"), dict):
 607 | +                raise ValueError("fidelity claim out of contract")
 608 | +            ok = c["supported"] == "yes" or (c.get("class") == "commentary" and
 609 | +                                             not any(t == "yes" for t in c["tests"].values()))
 610 | +            by[c["line"]] = by.get(c["line"], True) and ok
 611 | +        return by
 612 | +    if k == "speaker":
 613 | +        v = SP._json(text)
 614 | +        if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
 615 | +            raise ValueError("speaker out of contract")
 616 | +        n = SP._norm(v["speaker"].get("name") or "")
 617 | +        return {"speaker": n if n and n != SP.UNKNOWN else SP.UNKNOWN}
 618 | +    if k == "step_b":
 619 | +        labels = re.findall(r'"label": "([^"]+)"', prompt) or []
 620 | +        CI._strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
 621 | +                                                      "relations": ("labels", "relation")})
 622 | +        return {"contract": True}
 623 | +    raise ValueError(f"no decision rule for {k}")
 624 | +
 625 | +
 626 | +def compare(k, g, h):
 627 | +    """Grok's decision g against Heimdall's h for one unit -> "agree" | "stricter" | "looser" | "different"."""
 628 | +    if g == h:
 629 | +        return "agree"
 630 | +    if k == "speaker":
 631 | +        if h == SP.UNKNOWN:
 632 | +            return "stricter"
 633 | +        return "looser" if g == SP.UNKNOWN else "different"
 634 | +    if k == "step_a":                                  # a tuple of failures: [] passes
 635 | +        if bool(g) == bool(h):
 636 | +            return "agree"                             # both fail (for possibly different rules): the decision agrees
 637 | +        return "stricter" if h else "looser"
 638 | +    if isinstance(g, tuple):                           # the flagged joins: compared as a set
 639 | +        return "different"
 640 | +    return "stricter" if g is True and h is False else "looser" if g is False and h is True else "different"
 641 | +
 642 | +
 643 | +def records(since=FIRST_LEDGER, anchors=()):
 644 | +    """Every recorded Grok verdict (xAI text back-end) since `since`, plus older ones whose prompt carries an anchor
 645 | +    pin's clip text. -> [(path, rec, kind, anchor names)]."""
 646 | +    out = []
 647 | +    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
 648 | +        try:
 649 | +            with open(p) as f:
 650 | +                r = json.load(f)
 651 | +        except (OSError, ValueError):
 652 | +            continue
 653 | +        if not str(r.get("backend", "")).startswith("xai:"):
 654 | +            continue
 655 | +        k = kind(r)
 656 | +        if k is None:
 657 | +            continue
 658 | +        pr = _norm(r.get("prompt") or "")
 659 | +        hit = sorted({name for name, texts in anchors for t in texts if t and t in pr})
 660 | +        if str(r.get("recorded_at", "")) >= since:
 661 | +            out.append((p, r, k, hit))
 662 | +        elif hit:                                      # an older anchor record: only where Grok's answer still reads
 663 | +            try:
 664 | +                decide(k, r["text"], r.get("prompt") or "")
 665 | +                out.append((p, r, k, hit))
 666 | +            except (ValueError, TypeError, KeyError):
 667 | +                pass
 668 | +    seen, uniq = {}, []                                # the same prompt asked again (another seed): asked once here
 669 | +    for x in out:
 670 | +        key = (x[1].get("role"), x[1].get("prompt"), x[1].get("system"), x[1].get("max_tokens"))
 671 | +        if key in seen:
 672 | +            seen[key][3].extend(a for a in x[3] if a not in seen[key][3])
 673 | +            continue
 674 | +        seen[key] = x
 675 | +        uniq.append(x)
 676 | +    return uniq
 677 | +
 678 | +
 679 | +def _norm(t):
 680 | +    """Lower case letters and digits, single spaces: a prompt quotes a clip through quote_data (escaping)."""
 681 | +    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(t).lower()).split())
 682 | +
 683 | +
 684 | +def anchor_texts():
 685 | +    """[(pin name, [its segments' approved texts, normalised, 60 characters from the 10th])]: a prompt that carries
 686 | +    one of them judged that clip."""
 687 | +    out = []
 688 | +    for name, rel in ANCHOR_PINS.items():
 689 | +        try:
 690 | +            with open(os.path.join(WT, rel)) as f:
 691 | +                pin = json.load(f)
 692 | +        except (OSError, ValueError):
 693 | +            out.append((name, []))
 694 | +            continue
 695 | +        segs = pin.get("segments") or (pin.get("package") or {}).get("segments") or []
 696 | +        out.append((name, [_norm(s.get("approved_text") or s.get("text") or "")[10:70] for s in segs
 697 | +                           if isinstance(s, dict)]))
 698 | +    return out
 699 | +
 700 | +
 701 | +def run(args):
 702 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 703 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 704 | +    done = set()
 705 | +    if os.path.exists(res_path):
 706 | +        with open(res_path) as f:
 707 | +            for line in f:
 708 | +                try:
 709 | +                    x = json.loads(line)
 710 | +                    done.add((x["record"], x["model"]))
 711 | +                except (ValueError, KeyError):
 712 | +                    pass
 713 | +    anchors = anchor_texts()
 714 | +    recs = [x for x in records(anchors=anchors) if x[2] in args.types]
 715 | +    if args.limit:
 716 | +        recs = recs[:args.limit]
 717 | +    models = [m for m in args.models if m in MODELS]
 718 | +    chains = {f"replay85_{m}": [MODELS[m]] for m in models}
 719 | +    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
 720 | +                      limit_basis=LIMIT_BASIS, chains=chains)
 721 | +    lock = threading.Lock()
 722 | +    # round-robin by verdict type, the records since the first ledger build first, so an early table covers them all
 723 | +    order, by_type = [], {}
 724 | +    for x in sorted(recs, key=lambda x: str(x[1].get("recorded_at", "")) < FIRST_LEDGER):
 725 | +        by_type.setdefault(x[2], []).append(x)
 726 | +    while any(by_type.values()):
 727 | +        for k in list(by_type):
 728 | +            if by_type[k]:
 729 | +                order.append(by_type[k].pop(0))
 730 | +    jobs = [(p, r, k, hit, m) for (p, r, k, hit) in order for m in models
 731 | +            if (os.path.relpath(p, WT), m) not in done]
 732 | +    print(f"replay85: {len(recs)} Grok records, {len(models)} models, {len(jobs)} calls to make "
 733 | +          f"({len(done)} already in RESULTS)", flush=True)
 734 | +
 735 | +    def one(job):
 736 | +        p, r, k, hit, m = job
 737 | +        row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "anchors": hit,
 738 | +               "grok_recorded_at": r.get("recorded_at"), "grok_seconds": r.get("seconds"),
 739 | +               "grok_usd_reported": (r.get("usage") or {}).get("usd_reported")}
 740 | +        try:
 741 | +            row["grok"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in decide(k, r["text"], r["prompt"]).items()}
 742 | +        except (ValueError, TypeError, KeyError) as e:
 743 | +            row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
 744 | +        t0 = time.time()
 745 | +        router.down.pop(MODELS[m], None)               # a rate limit is never a verdict: each call is tried afresh
 746 | +        try:
 747 | +            rep = router.call(f"replay85_{m}", r["prompt"], int(r.get("max_tokens") or 2000), int(r.get("seed") or 7),
 748 | +                              system=r.get("system"), deadline_s=args.deadline or None)
 749 | +            row.update(seconds=round(rep.seconds or (time.time() - t0), 2), cached=bool(rep.cached),
 750 | +                       usd_reported=(rep.usage or {}).get("usd_reported"), usd_estimate=rep.usd)
 751 | +            try:
 752 | +                h = decide(k, rep.text, r["prompt"])
 753 | +                row["heimdall"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in h.items()}
 754 | +            except (ValueError, TypeError, KeyError) as e:
 755 | +                row["heimdall"], row["heimdall_error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:160]}"
 756 | +                router.reject(rep)
 757 | +        except (P.ProviderError, P.SpendLimit) as e:
 758 | +            if "HTTP 429" in str(e):                   # rate limited (after the router's own backoff): no row, so a
 759 | +                time.sleep(30)                         # resume asks it again; never counted as the model's answer
 760 | +                return None
 761 | +            row.update(seconds=round(time.time() - t0, 2), heimdall=None,
 762 | +                       heimdall_error=f"{type(e).__name__}: {str(e)[:200]}")
 763 | +        if row.get("grok") is not None and row.get("heimdall") is not None:
 764 | +            row["compare"] = {u: compare(k, tuple(g) if isinstance(g, list) else g,
 765 | +                                         tuple(row["heimdall"].get(u)) if isinstance(row["heimdall"].get(u), list)
 766 | +                                         else row["heimdall"].get(u))
 767 | +                              for u, g in row["grok"].items()}
 768 | +        with lock:
 769 | +            with open(res_path, "a") as f:
 770 | +                f.write(json.dumps(row) + "\n")
 771 | +        return row
 772 | +
 773 | +    n_done = [0]
 774 | +
 775 | +    def per_model(m):                                  # one pool per model: a slow model never starves the others
 776 | +        mine = [j for j in jobs if j[4] == m]
 777 | +        with ThreadPoolExecutor(max_workers=args.per_model.get(m, args.workers)) as ex:
 778 | +            for _ in ex.map(one, mine):
 779 | +                with lock:
 780 | +                    n_done[0] += 1
 781 | +                    if n_done[0] % 10 == 0 or n_done[0] == len(jobs):
 782 | +                        print(f"  {n_done[0]}/{len(jobs)} at {time.strftime('%H:%M:%S')}", flush=True)
 783 | +    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
 784 | +    for t in ts:
 785 | +        t.start()
 786 | +    for t in ts:
 787 | +        t.join()
 788 | +    table()
 789 | +
 790 | +
 791 | +def grok_self():
 792 | +    """The baseline: Grok against GROK on the same prompt asked again (another seed, another build), from every
 793 | +    recorded Grok answer. -> {type: {"pairs": n, "agree": n}} by the same decide / compare."""
 794 | +    by = {}
 795 | +    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
 796 | +        try:
 797 | +            with open(p) as f:
 798 | +                r = json.load(f)
 799 | +        except (OSError, ValueError):
 800 | +            continue
 801 | +        if not str(r.get("backend", "")).startswith("xai:"):
 802 | +            continue
 803 | +        k = kind(r)
 804 | +        if k not in DECIDING:
 805 | +            continue
 806 | +        try:
 807 | +            d = decide(k, r["text"], r.get("prompt") or "")
 808 | +        except (ValueError, TypeError, KeyError):
 809 | +            continue
 810 | +        by.setdefault((k, r.get("role"), r.get("prompt"), r.get("max_tokens")), []).append(d)
 811 | +        if k == "step_a":                              # the same excerpt inside OTHER batches too (its own block)
 812 | +            for lb, blk in re.findall(r'<excerpt label="([^"]+)"(.*?)</excerpt>', r.get("prompt") or "", re.S):
 813 | +                if lb in d:
 814 | +                    by.setdefault(("step_a_excerpt", lb, blk), []).append({lb: d[lb]})
 815 | +    out = {}
 816 | +    for (k, *_), ds in by.items():
 817 | +        for i in range(len(ds)):
 818 | +            for j in range(i + 1, len(ds)):
 819 | +                for u, g in ds[i].items():
 820 | +                    if u not in ds[j]:
 821 | +                        continue
 822 | +                    o = out.setdefault(k, {"pairs": 0, "agree": 0})
 823 | +                    o["pairs"] += 1
 824 | +                    o["agree"] += compare("step_a" if k == "step_a_excerpt" else k, g, ds[j][u]) == "agree"
 825 | +    if (out.get("step_a_excerpt") or {}).get("pairs", 0) > (out.get("step_a") or {}).get("pairs", 0):
 826 | +        out["step_a_identical_prompt"] = out.get("step_a")
 827 | +        out["step_a"] = out["step_a_excerpt"]            # the bar for step A: the same excerpt, any batch
 828 | +    return out
 829 | +
 830 | +
 831 | +_PROMPTS = {}
 832 | +
 833 | +
 834 | +def anchor_units(row, anchors):
 835 | +    """The units of a row that are an anchor's OWN decision (a delivered pin's clip let through):
 836 | +    - step A, step C, hook: the unit whose own block (<excerpt>, <pair>, CANDIDATE line) quotes an anchor clip;
 837 | +    - clips-alone, coherence, fidelity: every unit, only when the prompt quotes ALL clips of one anchor pin (its own
 838 | +      line-up);
 839 | +    - exclusion, speaker: the one unit when the prompt quotes an anchor clip.
 840 | +    -> {unit: [pin names]}."""
 841 | +    if not row.get("anchors"):
 842 | +        return {}
 843 | +    pr = _PROMPTS.get(row["record"])
 844 | +    if pr is None:
 845 | +        try:
 846 | +            with open(os.path.join(WT, row["record"])) as f:
 847 | +                pr = _PROMPTS[row["record"]] = json.load(f).get("prompt") or ""
 848 | +        except (OSError, ValueError):
 849 | +            return {}
 850 | +    k, out = row["type"], {}
 851 | +    if k in ("step_a", "step_c", "hook"):
 852 | +        pat = {"step_a": r'<excerpt label="([^"]+)"(.*?)</excerpt>', "step_c": r'<pair label="([^"]+)"(.*?)</pair>',
 853 | +               "hook": r'CANDIDATE id="([^"]+)"([^\n]*)'}[k]
 854 | +        for u, blk in re.findall(pat, pr, re.S):
 855 | +            hit = [n for n, ts in anchors for t in ts if t and t in _norm(blk)]
 856 | +            if hit:
 857 | +                out[u] = sorted(set(hit))
 858 | +        return out
 859 | +    npr = _norm(pr)
 860 | +    if k in ("clips_alone", "coherence", "fidelity"):
 861 | +        whole = [n for n, ts in anchors if ts and all(t in npr for t in ts if t)]
 862 | +        return {u: whole for u in (row.get("grok") or {})} if whole else {}
 863 | +    hit = [n for n, ts in anchors for t in ts if t and t in npr]
 864 | +    return {u: sorted(set(hit)) for u in (row.get("grok") or {})} if hit else {}
 865 | +
 866 | +
 867 | +def table():
 868 | +    """TABLE.md from RESULTS.jsonl: per verdict type and model, with Grok's agreement with itself as the baseline."""
 869 | +    rows = []
 870 | +    with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
 871 | +        for line in f:
 872 | +            try:
 873 | +                rows.append(json.loads(line))
 874 | +            except ValueError:
 875 | +                pass
 876 | +    out = ["# Ruling 85.1: the replay of Grok's recorded verdicts on Heimdall's families", "",
 877 | +           f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. A unit is one decision "
 878 | +           "(a clip, a line-up, a hook, a line, a moment). Stricter: Heimdall fails what Grok passed. Looser: Heimdall "
 879 | +           "passes what Grok failed. Different: another name, or other flagged joins with the same decision.", "",
 880 | +           "| type | model | records | answered | no verdict | units | agree | stricter | looser | different | "
 881 | +           "agree % | median s | > 120 s | timeouts | errors | usd reported |", "|" + "---|" * 16]
 882 | +    for k in TYPES:
 883 | +        for m in MODELS:
 884 | +            rs = [r for r in rows if r["type"] == k and r["model"] == m]
 885 | +            if not rs:
 886 | +                continue
 887 | +            ans = [r for r in rs if r.get("heimdall") is not None]
 888 | +            nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
 889 | +            tmo = [r for r in rs if r.get("heimdall") is None and "abandoned at the deadline" in
 890 | +                   str(r.get("heimdall_error"))]
 891 | +            err = [r for r in rs if r.get("heimdall") is None and r not in nov and r not in tmo]
 892 | +            cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
 893 | +            n = {x: cmp_.count(x) for x in ("agree", "stricter", "looser", "different")}
 894 | +            secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
 895 | +            usd = sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported")) and not r.get("cached"))
 896 | +            out.append(f"| {k} | {m} | {len(rs)} | {len(ans)} | {len(nov)} | {len(cmp_)} | {n['agree']} | "
 897 | +                       f"{n['stricter']} | {n['looser']} | {n['different']} | "
 898 | +                       f"{(100 * n['agree'] / len(cmp_)) if cmp_ else 0:.0f} | "
 899 | +                       f"{statistics.median(secs) if secs else 0:.0f} | {sum(1 for s in secs if s > DEADLINE_S)} | "
 900 | +                       f"{len(tmo)} | {len(err)} | {usd:.4f} |")
 901 | +    base = grok_self()
 902 | +    out += ["", "## The baseline: Grok against Grok (the same prompt asked again: another seed or build)", "",
 903 | +            "| type | unit pairs | agree | agree % |", "|---|---|---|---|"]
 904 | +    for k in DECIDING + ("step_a_excerpt",):
 905 | +        b = base.get(k)
 906 | +        if b:
 907 | +            out.append(f"| {k} | {b['pairs']} | {b['agree']} | {100 * b['agree'] / b['pairs']:.0f} |")
 908 | +    anchors = anchor_texts()
 909 | +    out += ["", "## Anchors: the delivered pins' own decisions that Grok passed must still pass", ""]
 910 | +    for m in MODELS:
 911 | +        units = bad = nov = 0
 912 | +        ex = []
 913 | +        for r in rows:
 914 | +            if r["model"] != m:
 915 | +                continue
 916 | +            au = anchor_units(r, anchors)
 917 | +            for u in au:
 918 | +                g = (r.get("grok") or {}).get(u)
 919 | +                if g is None or (r["type"] == "step_a" and g) or g is False:
 920 | +                    continue                           # Grok did not pass it: not a decision that let a clip through
 921 | +                units += 1
 922 | +                if r.get("heimdall") is None:
 923 | +                    nov += 1
 924 | +                    ex.append(f"{r['type']} {u} {au[u]}: no Heimdall verdict")
 925 | +                elif (r.get("compare") or {}).get(u) == "stricter":
 926 | +                    bad += 1
 927 | +                    ex.append(f"{r['type']} {u} {au[u]}: FAILED ({r['record'][-24:]})")
 928 | +        out.append(f"- {m}: {units} anchor decisions Grok passed; {bad} failed by {m}; {nov} without a verdict" +
 929 | +                   (": " + "; ".join(ex[:10]) if ex else ""))
 930 | +    out += ["", "## Step A's REFERENT_OUTSIDE refusals (Grok's) must still be refused", ""]
 931 | +    for m in MODELS:
 932 | +        tot = kept = ro = 0
 933 | +        for r in rows:
 934 | +            if r["model"] != m or r["type"] != "step_a" or not r.get("grok") or r.get("heimdall") is None:
 935 | +                continue                               # only the answered rows: no answer is no verdict either way
 936 | +            for u, g in r["grok"].items():
 937 | +                if "REFERENT_OUTSIDE" in (g or []):
 938 | +                    tot += 1
 939 | +                    h = (r.get("heimdall") or {}).get(u)
 940 | +                    kept += bool(h)
 941 | +                    ro += "REFERENT_OUTSIDE" in (h or [])
 942 | +        out.append(f"- {m}: Grok refused {tot} clips for REFERENT_OUTSIDE; Heimdall refuses {kept} of them "
 943 | +                   f"({ro} for REFERENT_OUTSIDE itself)")
 944 | +    vp = os.path.join(OUT, "VISUAL.jsonl")
 945 | +    if os.path.exists(vp):                             # the visual sheets (run_visual): the set of flags per sheet
 946 | +        with open(vp) as f:
 947 | +            vis = [json.loads(x) for x in f if x.strip()]
 948 | +        out += ["", "## The visual sheets (nemotron and qwen against Grok's flags)", "",
 949 | +                "| model | sheets | answered | agree | stricter | looser | different | median s | usd reported |",
 950 | +                "|---|---|---|---|---|---|---|---|---|"]
 951 | +        for m in VISION:
 952 | +            vs = [v for v in vis if v.get("model") == m]
 953 | +            if not vs:
 954 | +                continue
 955 | +            c = [v.get("compare") for v in vs if v.get("compare")]
 956 | +            secs = [v["seconds"] for v in vs if isinstance(v.get("seconds"), (int, float))]
 957 | +            out.append(f"| {m} | {len(vs)} | {len(c)} | {c.count('agree')} | {c.count('stricter')} | "
 958 | +                       f"{c.count('looser')} | {c.count('different')} | "
 959 | +                       f"{statistics.median(secs) if secs else 0:.0f} | "
 960 | +                       f"{sum(float(v.get('usd_reported') or 0) for v in vs):.4f} |")
 961 | +        skipped = [v for v in vis if v.get("skipped")]
 962 | +        if skipped:
 963 | +            out.append(f"- {len(skipped)} sheet(s) skipped: " + "; ".join(v["skipped"] for v in skipped)[:300])
 964 | +        sheets = {v["sheet"] for v in vis if v.get("sheet") and not v.get("skipped")}
 965 | +        flagged = {v["sheet"] for v in vis if v.get("grok")}
 966 | +        out.append(f"- Grok flagged {len(flagged)} of the {len(sheets)} sheets compared; agreement on unflagged sheets "
 967 | +                   f"says little about a model's eye for a flag.")
 968 | +    out += propose(rows, base)
 969 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 970 | +        f.write("\n".join(out) + "\n")
 971 | +    print("\n".join(out), flush=True)
 972 | +
 973 | +
 974 | +ROLES = {"context_verdict": ("step_a", "step_c"), "coherence_verdict": ("clips_alone", "coherence", "hook"),
 975 | +         "fidelity_verdict": ("fidelity",), "exclusion_verdict": ("exclusion",), "speaker_verdict": ("speaker",)}
 976 | +MIN_UNITS = 10
 977 | +
 978 | +
 979 | +def passes(rows, base, k, m):
 980 | +    """The PROPOSED rule (the orchestrator rules it): -> (pass, [reasons it fails])."""
 981 | +    rs = [r for r in rows if r["type"] == k and r["model"] == m]
 982 | +    cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
 983 | +    why = []
 984 | +    if len(cmp_) < MIN_UNITS:
 985 | +        why.append(f"only {len(cmp_)} decisions (< {MIN_UNITS})")
 986 | +    anchors = anchor_texts()
 987 | +    if any((r.get("compare") or {}).get(u) == "stricter" for r in rs for u in anchor_units(r, anchors)):
 988 | +        why.append("an anchor decision Grok passed is failed")
 989 | +    if k == "step_a":
 990 | +        miss = sum(1 for r in rs if r.get("grok") and r.get("heimdall") is not None for u, g in r["grok"].items()
 991 | +                   if "REFERENT_OUTSIDE" in (g or []) and not r["heimdall"].get(u))
 992 | +        if miss:
 993 | +            why.append(f"{miss} REFERENT_OUTSIDE refusal(s) let through")
 994 | +    agree = 100 * cmp_.count("agree") / len(cmp_) if cmp_ else 0
 995 | +    b = base.get(k) or {}
 996 | +    bar = 100 * b["agree"] / b["pairs"] if b.get("pairs", 0) >= 5 else 75.0
 997 | +    if agree < bar:
 998 | +        why.append(f"agreement {agree:.0f}% < the bar {bar:.0f}%")
 999 | +    ans = [r for r in rs if r.get("heimdall") is not None]
1000 | +    nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
1001 | +    if ans and len(ans) / max(1, len(ans) + len(nov)) < 0.9:
1002 | +        why.append(f"{len(nov)} of {len(ans) + len(nov)} answers out of contract")
1003 | +    secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
1004 | +    if secs and statistics.median(secs) > DEADLINE_S:
1005 | +        why.append(f"median {statistics.median(secs):.0f} s > {DEADLINE_S:.0f} s")
1006 | +    return not why, why, agree, (statistics.median(secs) if secs else None)
1007 | +
1008 | +
1009 | +def propose(rows, base):
1010 | +    """The proposed Heimdall-first list per role: the families that pass EVERY type of the role, best agreement
1011 | +    first; Grok last; a role with fewer than two passing families keeps Grok as its second family."""
1012 | +    out = ["", "## The proposed routing (the rule is the orchestrator's to rule)", ""]
1013 | +    for role, types in ROLES.items():
1014 | +        ok, notes = [], []
1015 | +        for m in MODELS:
1016 | +            res = [(k, passes(rows, base, k, m)) for k in types]
1017 | +            if all(x[1][0] for x in res):
1018 | +                ok.append((m, min(x[1][2] for x in res)))
1019 | +            notes.append(f"{m}: " + ("PASSES" if all(x[1][0] for x in res) else
1020 | +                                     "; ".join(f"{k}: {', '.join(x[1])}" for k, x in res if not x[0])))
1021 | +        order = [m for m, _ in sorted(ok, key=lambda x: -x[1])]
1022 | +        tail = "Grok last" if len(order) >= 2 else "Grok as the second family (fewer than two Heimdall families pass)"
1023 | +        out.append(f"- {role} ({', '.join(types)}): {' -> '.join(order) or 'none'}; {tail}")
1024 | +        out += [f"  - {n}" for n in notes]
1025 | +    return out
1026 | +
1027 | +
1028 | +VISION = {"nemotron": "heimdall:nvidia/nemotron-3.5-super-vl", "qwen": "heimdall:qwen/qwen3.8-27b"}
1029 | +
1030 | +
1031 | +def run_visual(args):
1032 | +    """The visual sheets (ruling 85.1: "and nemotron for the visual sheets"). Every sheet Grok judged is in
1033 | +    tests/package/proof/VISUAL_CACHE.json, with its path, sha256 and frame times. The prompt is rebuilt exactly as
1034 | +    visual_pin.visual_for builds it (PROMPT.format(n, text) and the sheet image), and asked of nemotron and qwen. The
1035 | +    decision is visual_pin.flags of the verdict (the set of flags), compared with Grok's. A sheet whose bytes changed,
1036 | +    or whose moment text cannot be found, is skipped and said so."""
1037 | +    import base64
1038 | +    import hashlib
1039 | +    import visual_pin as VP
1040 | +    with open(os.path.join(WT, "tests", "package", "proof", "VISUAL_CACHE.json")) as f:
1041 | +        cache = json.load(f)
1042 | +    texts = {}
1043 | +    for p in sorted(glob.glob(os.path.join(WT, "tests", "package", "proof", "ledger_*", "inputs.json"))):
1044 | +        try:
1045 | +            with open(p) as f:
1046 | +                for m in json.load(f).get("moments") or []:
1047 | +                    texts.setdefault(m.get("moment_id"), m.get("text"))
1048 | +        except (OSError, ValueError):
1049 | +            continue
1050 | +    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
1051 | +                      limit_basis=LIMIT_BASIS, chains={f"replay85v_{m}": [n] for m, n in VISION.items()})
1052 | +    rows = []
1053 | +    for k, g in cache.items():
1054 | +        sh, mid = g.get("sheet") or {}, k.split(":")[0]
1055 | +        path = sh.get("path") or ""
1056 | +        try:
1057 | +            with open(path, "rb") as f:
1058 | +                raw = f.read()
1059 | +        except OSError:
1060 | +            rows.append({"sheet": k, "skipped": f"the sheet is not on disk: {path}"})
1061 | +            continue
1062 | +        if hashlib.sha256(raw).hexdigest() != sh.get("sha256") or texts.get(mid) is None:
1063 | +            rows.append({"sheet": k, "skipped": "the sheet's bytes changed, or its moment's text is not found"})
1064 | +            continue
1065 | +        prompt = {"text": VP.PROMPT.format(n=len(sh.get("times") or []), text=str(texts[mid]).replace('"', "'")),
1066 | +                  "images": [base64.b64encode(raw).decode()]}
1067 | +        grok = sorted(g.get("flags") or [])
1068 | +        for m in VISION:
1069 | +            t0 = time.time()
1070 | +            row = {"sheet": k, "model": m, "grok": grok}
1071 | +            try:
1072 | +                r = router.call(f"replay85v_{m}", prompt, 1500, 7)
1073 | +                row.update(seconds=round(r.seconds or (time.time() - t0), 2),
1074 | +                           usd_reported=(r.usage or {}).get("usd_reported"))
1075 | +                try:
1076 | +                    row["heimdall"] = sorted(VP.flags(VP.check(VP._json(r.text))))
1077 | +                    h, gg = set(row["heimdall"]), set(grok)
1078 | +                    row["compare"] = "agree" if h == gg else "stricter" if h > gg else "looser" if h < gg \
1079 | +                        else "different"
1080 | +                except (ValueError, TypeError, KeyError) as e:
1081 | +                    row["heimdall"], row["error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:120]}"
1082 | +                    router.reject(r)
1083 | +            except (P.ProviderError, P.SpendLimit) as e:
1084 | +                row.update(heimdall=None, error=f"{type(e).__name__}: {str(e)[:160]}",
1085 | +                           seconds=round(time.time() - t0, 2))
1086 | +            rows.append(row)
1087 | +            print(json.dumps(row)[:300], flush=True)
1088 | +    with open(os.path.join(OUT, "VISUAL.jsonl"), "w") as f:
1089 | +        f.write("".join(json.dumps(r) + "\n" for r in rows))
1090 | +    return rows
1091 | +
1092 | +
1093 | +def main():
1094 | +    ap = argparse.ArgumentParser()
1095 | +    ap.add_argument("--workers", type=int, default=2, help="calls in flight per model")
1096 | +    ap.add_argument("--models", default="deepseek,glm,qwen")
1097 | +    ap.add_argument("--per-model", default="", help="calls in flight per model, e.g. deepseek=12,glm=8")
1098 | +    ap.add_argument("--deadline", type=float, default=300.0,
1099 | +                    help="seconds a call may take (abandoned past it: a timeout; production cuts at 120 s)")
1100 | +    ap.add_argument("--types", default=",".join(DECIDING))
1101 | +    ap.add_argument("--limit", type=int, default=0)
1102 | +    ap.add_argument("--table-only", action="store_true")
1103 | +    ap.add_argument("--visual", action="store_true", help="the visual sheets only (nemotron and qwen)")
1104 | +    a = ap.parse_args()
1105 | +    a.models, a.types = a.models.split(","), a.types.split(",")
1106 | +    a.per_model = {k: int(v) for k, v in (x.split("=") for x in a.per_model.split(",") if x)}
1107 | +    if a.table_only:
1108 | +        table()
1109 | +        return 0
1110 | +    if a.visual:
1111 | +        run_visual(a)
1112 | +        return 0
1113 | +    run(a)
1114 | +    return 0
1115 | +
1116 | +
1117 | +if __name__ == "__main__":
1118 | +    sys.exit(main())
1119 | diff --git a/tests/package/shadow86.py b/tests/package/shadow86.py
1120 | new file mode 100644
1121 | index 0000000..13b2ea7
1122 | --- /dev/null
1123 | +++ b/tests/package/shadow86.py
1124 | @@ -0,0 +1,143 @@
1125 | +#!/usr/bin/env python3
1126 | +"""RULING 86 (orchestrator 21:18 Nov 13): THE SHADOW'S SIDE-BY-SIDE. A heimdall_first build writes SHADOW86.jsonl in
1127 | +its build directory: one line per verdict Heimdall decided, with Grok's answer to the SAME prompt (asked in shadow,
1128 | +never deciding: providers.Router). This reads it with the replay's decision rules (replay85.kind / decide / compare)
1129 | +and writes SHADOW86.md there:
1130 | +- every decision where Heimdall and Grok differ, and which side was stricter;
1131 | +- whether the pin would have sealed under Grok: a verdict on the pin's clips where Grok fails what Heimdall passed
1132 | +  would have stopped it. This is read from the verdicts themselves; the gates that depend on them are not re-run;
1133 | +- verdict types without a decision rule (the visual sheets, step B) are listed as "not compared".
1134 | +tests/package/proof/SHADOW86.json keeps the pins in order and the streak of pins with no decision-changing
1135 | +difference; the build driver stops asking the shadow when the streak reaches routing.shadow_until_clean_pins (3).
1136 | +Usage: python3 -B tests/package/shadow86.py <build dir>   (re-reads a build's SHADOW86.jsonl, rewrites its report)"""
1137 | +import json
1138 | +import os
1139 | +import sys
1140 | +import time
1141 | +
1142 | +HERE = os.path.dirname(os.path.abspath(__file__))
1143 | +sys.path.insert(0, HERE)
1144 | +import replay85 as R  # noqa: E402
1145 | +
1146 | +STATE = os.path.join(HERE, "proof", "SHADOW86.json")
1147 | +
1148 | +
1149 | +def _load(path=STATE):
1150 | +    try:
1151 | +        with open(path) as f:
1152 | +            d = json.load(f)
1153 | +        return d if isinstance(d, dict) and isinstance(d.get("pins"), list) else {"pins": [], "clean_streak": 0}
1154 | +    except (OSError, ValueError):
1155 | +        return {"pins": [], "clean_streak": 0}
1156 | +
1157 | +
1158 | +def clean_streak(path=STATE):
1159 | +    """The pins in a row with no decision-changing difference (0 when nothing is recorded or the file cannot be read:
1160 | +    the shadow then keeps running, which is the safe side)."""
1161 | +    return int(_load(path).get("clean_streak") or 0)
1162 | +
1163 | +
1164 | +def pin_texts(res):
1165 | +    """The SEALED pins' clip texts, normalised as replay85 matches prompts: the medley's (res["pin"], set by the pin
1166 | +    stage, with res["package"] as sealed, adopted texts included) and the spotlight's (RULING 90: res["spotlight_pin"],
1167 | +    with res["spotlight"]["package"]). None sealed (no package, or the pin stage refused it): []."""
1168 | +    pks = ([res.get("package") or {}] if res.get("pin") else []) + \
1169 | +        ([(res.get("spotlight") or {}).get("package") or {}] if res.get("spotlight_pin") else [])
1170 | +    return [R._norm(s.get("text") or "")[10:70] for pk in pks for s in pk.get("segments") or [] if isinstance(s, dict)]
1171 | +
1172 | +
1173 | +def compare_lines(lines, texts=()):
1174 | +    """-> rows: one per (shadow line, unit): {type, unit, heimdall, grok, compare, on_pin, deciding, shadow}."""
1175 | +    rows, skipped = [], []
1176 | +    for x in lines:
1177 | +        k = R.kind({"role": x.get("role"), "prompt": x.get("prompt") or ""})
1178 | +        sh = x.get("shadow") or {}
1179 | +        if k is None or k not in R.DECIDING or "text" not in sh:
1180 | +            skipped.append({"role": x.get("role"), "type": k, "why": sh.get("error") or "no decision rule"})
1181 | +            continue
1182 | +        pr = x.get("prompt") or ""
1183 | +        on_pin = bool(texts) and any(t and t in R._norm(pr) for t in texts)
1184 | +        try:
1185 | +            h = R.decide(k, (x.get("deciding") or {}).get("text"), pr)
1186 | +        except (ValueError, TypeError, KeyError) as e:
1187 | +            skipped.append({"role": x.get("role"), "type": k, "why": f"Heimdall's answer unreadable: {e}"})
1188 | +            continue
1189 | +        try:
1190 | +            g = R.decide(k, sh["text"], pr)
1191 | +        except (ValueError, TypeError, KeyError) as e:
1192 | +            g = None
1193 | +            rows.append({"type": k, "unit": "*", "heimdall": "answered", "grok": f"out of contract: {e}"[:120],
1194 | +                         "compare": "grok no verdict", "on_pin": on_pin,
1195 | +                         "deciding": (x.get("deciding") or {}).get("backend"), "shadow": sh.get("backend")})
1196 | +        if g is None:
1197 | +            continue
1198 | +        for u, hv in h.items():
1199 | +            gv = g.get(u)
1200 | +            rows.append({"type": k, "unit": u, "heimdall": hv, "grok": gv, "compare": R.compare(k, gv, hv),
1201 | +                         "on_pin": on_pin, "deciding": (x.get("deciding") or {}).get("backend"),
1202 | +                         "shadow": sh.get("backend")})
1203 | +    return rows, skipped
1204 | +
1205 | +
1206 | +def report(out_dir, res, missing=0, path=STATE, update_streak=True):
1207 | +    """SHADOW86.md for one build, and (update_streak) the pins' streak updated when it sealed one. -> a summary."""
1208 | +    lines = []
1209 | +    p = os.path.join(out_dir, "SHADOW86.jsonl")
1210 | +    if os.path.exists(p):
1211 | +        with open(p) as f:
1212 | +            for ln in f:
1213 | +                try:
1214 | +                    lines.append(json.loads(ln))
1215 | +                except ValueError:
1216 | +                    pass
1217 | +    texts = pin_texts(res)
1218 | +    rows, skipped = compare_lines(lines, texts)
1219 | +    diff = [r for r in rows if r["compare"] != "agree"]
1220 | +    pin_diff = [r for r in diff if r["on_pin"]]
1221 | +    would_seal = None if not texts else not any(r["compare"] in ("looser", "grok no verdict") for r in pin_diff)
1222 | +    usd = sum(float((x.get("shadow") or {}).get("usd_reported") or 0) for x in lines
1223 | +              if not (x.get("shadow") or {}).get("cached"))
1224 | +    summ = {"verdicts": len(lines), "compared_units": len(rows), "differ": len(diff), "on_pin_differ": len(pin_diff),
1225 | +            "not_compared": len(skipped), "missing": int(missing), "shadow_usd_reported": round(usd, 4),
1226 | +            "pin": bool(texts), "would_seal_under_grok": would_seal}
1227 | +    summ["summary"] = (f"{len(lines)} verdicts shadowed, {len(rows)} decisions compared, {len(diff)} differ "
1228 | +                       f"({len(pin_diff)} on the pin's clips); {len(skipped)} not compared; {int(missing)} still "
1229 | +                       f"running; shadow cost ${usd:.4f} reported" +
1230 | +                       ("" if would_seal is None else f"; the pin WOULD {'' if would_seal else 'NOT '}have sealed "
1231 | +                                                      f"under Grok"))
1232 | +    out = ["# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)", "",
1233 | +           f"Build {os.path.basename(out_dir)}, written {time.strftime('%Y-%m-%d %H:%M %Z')}. {summ['summary']}.", "",
1234 | +           "Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed "
1235 | +           "(on the pin's clips, Grok would have stopped it).", "",
1236 | +           "| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |", "|---|---|---|---|---|---|---|"]
1237 | +    for r in diff:
1238 | +        out.append(f"| {r['type']} | {r['unit']} | {r['heimdall']} | {r['grok']} | {r['compare']} | "
1239 | +                   f"{'yes' if r['on_pin'] else ''} | {r['deciding']} |")
1240 | +    if skipped:
1241 | +        out += ["", "## Not compared", ""] + [f"- {s['role']} ({s['type']}): {s['why']}" for s in skipped]
1242 | +    with open(os.path.join(out_dir, "SHADOW86.md"), "w") as f:
1243 | +        f.write("\n".join(out) + "\n")
1244 | +    if texts and update_streak:                  # a sealed pin: the streak moves (once, by the build itself)
1245 | +        st = _load(path)
1246 | +        changed = bool(pin_diff) or bool(missing)
1247 | +        st["pins"].append({"build": os.path.basename(out_dir), "decision_changing": len(pin_diff),
1248 | +                           "missing": int(missing), "would_seal_under_grok": would_seal,
1249 | +                           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
1250 | +        st["clean_streak"] = 0 if changed else int(st.get("clean_streak") or 0) + 1
1251 | +        tmp = f"{path}.{os.getpid()}.tmp"
1252 | +        with open(tmp, "w") as f:
1253 | +            json.dump(st, f, indent=1)
1254 | +        os.replace(tmp, path)
1255 | +        summ["clean_streak"] = st["clean_streak"]
1256 | +    return summ
1257 | +
1258 | +
1259 | +def main():
1260 | +    d = sys.argv[1]
1261 | +    with open(os.path.join(d, "package.json")) as f:
1262 | +        res = json.load(f)
1263 | +    print(json.dumps(report(d, res, update_streak=False), indent=1))     # a re-read never moves the streak
1264 | +
1265 | +
1266 | +if __name__ == "__main__":
1267 | +    main()
1268 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
1269 | index 71cc033..c0a2d96 100644
1270 | --- a/tests/package/test_gates.py
1271 | +++ b/tests/package/test_gates.py
1272 | @@ -22,7 +22,7 @@ class Canned:
1273 |          self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []
1274 |  
1275 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
1276 | -             avoid_family=None, deadline_s=None):
1277 | +             avoid_family=None, deadline_s=None, kind=None):
1278 |          self.calls.append((role, avoid_vendor, avoid_family))
1279 |          q = self.answers.get(role)
1280 |          if not q:
1281 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1282 | index 0497719..af3a02d 100644
1283 | --- a/tests/package/test_medley.py
1284 | +++ b/tests/package/test_medley.py
1285 | @@ -564,7 +564,8 @@ class Rig:
1286 |          self.write_avoid = []
1287 |  
1288 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
1289 | -                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None):
1290 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None, kind=None,
1291 | +                  failover=None):
1292 |          self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
1293 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
1294 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
1295 | @@ -1177,7 +1178,7 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
1296 |          import context_integrity as CI
1297 |          from test_gates import a_item
1298 |  
1299 | -        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False):
1300 | +        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
1301 |              calls.append((sorted(contexts), seed))
1302 |              if set(contexts) & set(fail):
1303 |                  raise RuntimeError("the batch reply was out of contract")
1304 | @@ -1293,14 +1294,35 @@ class TestRuling59HookFirst(unittest.TestCase):
1305 |          self.assertIn('CANDIDATE id="b"', prompts[0])
1306 |          self.assertIn("Judge each one ALONE", prompts[0])
1307 |  
1308 | -    def test_a_reply_out_of_contract_is_asked_once_more_then_nothing_is_rated(self):
1309 | +    def chained(self, *replies):
1310 | +        """A canned chain: each call is answered by the next model (fake:1, fake:2, ...), and a model the caller
1311 | +        skips (avoid_model) is never asked."""
1312 | +        c = self.canned(*replies)
1313 | +        call, n = c.call, [0]
1314 | +
1315 | +        def nxt(role, prompt, *a, avoid_model=None, **k):
1316 | +            r = call(role, prompt, *a, **k)
1317 | +            n[0] += 1
1318 | +            name = f"fake:{n[0]}"
1319 | +            assert name not in (avoid_model or ()), "a skipped model was asked"
1320 | +            c.asked_skip = getattr(c, "asked_skip", []) + [sorted(avoid_model or ())]
1321 | +            import providers as P
1322 | +            return P.Reply(r.text, name, "fake")
1323 | +        c.call = nxt
1324 | +        return c
1325 | +
1326 | +    def test_a_reply_out_of_contract_moves_on_to_the_next_model_then_nothing_is_rated(self):
1327 | +        """The 20:33 order (ruling 82's chain on every verdict): an answer out of contract moves on to the NEXT model
1328 | +        (it was one re-ask of the same model); the chain spent is no verdict (law L-m)."""
1329 |          ms = [pm("a", "A", 12.0)]
1330 |          ok = {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}
1331 | -        c = self.canned({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
1332 | +        c = self.chained({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
1333 |          got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
1334 | -        self.assertEqual((err, got["a"]["rating"], len(c.calls), len(c.rejected)), (None, 4, 2, 1))
1335 | +        self.assertEqual((err, got["a"]["rating"], got["a"]["backend"], len(c.calls), c.rejected),
1336 | +                         (None, 4, "fake:2", 2, ["fake:1"]))
1337 | +        self.assertEqual(c.asked_skip, [[], ["fake:1"]])                   # the second ask skips the first model
1338 |          for bad in ({"hooks": {}}, {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4}}}, {"x": 1}, "no json"):
1339 | -            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
1340 | +            got, err = PK.hook_ratings(self.chained(bad, bad), ms, ctx(), set(), set())
1341 |              self.assertEqual(got, {})
1342 |              self.assertIn("Error", err)
1343 |          got, err = PK.hook_ratings(self.canned(), ms, ctx(), set(), set())   # unavailable: no verdict (law L-m)
1344 | @@ -2482,6 +2504,51 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
1345 |          self.assertEqual(rig.screen_deadlines, [None, 120.0, 120.0, 120.0, 120.0])   # audit 2005 C1: the first screen
1346 |          #   unbounded as before; the second screen's two chunks and both off-writer re-screens at ruling 82's 120 s
1347 |  
1348 | +    def test_ruling_85_the_first_screen_is_bounded_under_heimdall_first(self):
1349 | +        """RULING 85: under heimdall_first the FIRST step-A verdict is a Heimdall family's, so it gets ruling 82's
1350 | +        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before."""
1351 | +        batches = []
1352 | +        for routing in ("today", "heimdall_first"):
1353 | +            rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
1354 | +                      angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
1355 | +            rig.router.routing = routing
1356 | +            pre = rig.prescreen
1357 | +
1358 | +            def spy(*a, batch=PK.PRESCREEN_BATCH, **k):
1359 | +                batches.append((routing, batch))
1360 | +                return pre(*a, batch=batch, **k)
1361 | +            rig.prescreen = spy
1362 | +            rig.run()
1363 | +            self.assertEqual(rig.screen_deadlines[0], None if routing == "today" else PK.SECOND_VERDICT_DEADLINE_S)
1364 | +        self.assertEqual([b for r, b in batches if r == "heimdall_first"][0], PK.SECOND_VERDICT_BATCH)
1365 | +        self.assertEqual([b for r, b in batches if r == "today"][0], PK.PRESCREEN_BATCH)
1366 | +
1367 | +    def test_ruling_88_grok_confirms_in_its_own_batches_under_heimdall_first(self):
1368 | +        """RULING 88 (c): under heimdall_first the second step-A verdict is Grok confirming Heimdall's passes: Grok's own
1369 | +        batch (8) and no deadline, the move-on rule kept; under today it stays a Heimdall family's (2 clips, 120 s)."""
1370 | +        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "today"})()),
1371 | +                         (PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S))
1372 | +        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "heimdall_first"})()), (PK.PRESCREEN_BATCH, None))
1373 | +        got = []
1374 | +
1375 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
1376 | +                 deadline_s=None, kind=None, failover=None):
1377 | +            got.append((len(chunk), batch, deadline_s, kind, failover))
1378 | +            return {m["moment_id"]: {"backend": "xai:grok"} for m in chunk}, {m["moment_id"]: [] for m in chunk}, \
1379 | +                set(), set()
1380 | +        router = type("R", (), {"routing": "heimdall_first", "backends": {
1381 | +            "heimdall:qwen": type("B", (), {"vendor": "heimdall/qwen", "family": "qwen"})(),
1382 | +            "xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}})()
1383 | +        ms = [dict(m, moment_id=f"m{i}") for i, m in enumerate(self.MS * 3)][:9]
1384 | +        saved = PK.prescreen
1385 | +        PK.prescreen = fake
1386 | +        try:
1387 | +            PK.second_screen(router, {m["moment_id"]: m for m in ms}, {m["moment_id"]: {"backend": "heimdall:qwen"}
1388 | +                                                                       for m in ms}, {}, ctx())
1389 | +        finally:
1390 | +            PK.prescreen = saved
1391 | +        self.assertEqual(sorted(got), [(1, 8, None, "step_a_second", True), (8, 8, None, "step_a_second", True)])
1392 | +
1393 |      def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
1394 |          """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
1395 |          flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
1396 | @@ -2528,7 +2595,7 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
1397 |          seen, calls = [], []
1398 |  
1399 |          def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
1400 | -                 deadline_s=None):
1401 | +                 deadline_s=None, kind=None, failover=None):
1402 |              seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
1403 |              calls.append((batch, deadline_s))
1404 |              name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
1405 | diff --git a/tests/package/test_shadow86.py b/tests/package/test_shadow86.py
1406 | new file mode 100644
1407 | index 0000000..efd07d8
1408 | --- /dev/null
1409 | +++ b/tests/package/test_shadow86.py
1410 | @@ -0,0 +1,80 @@
1411 | +#!/usr/bin/env python3
1412 | +"""RULING 86 (orchestrator 21:18 Nov 13): the shadow's side-by-side (tests/package/shadow86.py). Offline: a
1413 | +synthetic SHADOW86.jsonl in a temporary build directory and a temporary streak file."""
1414 | +import json
1415 | +import os
1416 | +import sys
1417 | +import tempfile
1418 | +import unittest
1419 | +
1420 | +HERE = os.path.dirname(os.path.abspath(__file__))
1421 | +sys.path.insert(0, HERE)
1422 | +import shadow86 as SH  # noqa: E402
1423 | +
1424 | +CLIP = "Bitcoin only dropped like five, six percent while tech stocks fell much further that week."
1425 | +PROMPT = ('Judge this moment. <before>...</before> <moment>"' + CLIP + '"</moment> Return {"risks": [], '
1426 | +          '"about_bitcoin": "yes|no|uncertain", "why": "..."}')
1427 | +
1428 | +
1429 | +def line(h, g, prompt=PROMPT):
1430 | +    return {"role": "exclusion_verdict", "prompt": prompt, "deciding": {"backend": "heimdall:z-ai/glm-5.3-flash",
1431 | +            "text": json.dumps(h)}, "shadow": {"backend": "xai:grok", "text": json.dumps(g), "usd_reported": 0.01}}
1432 | +
1433 | +
1434 | +KEEP = {"risks": [], "about_bitcoin": "yes", "why": "w"}
1435 | +EXCL = {"risks": ["imperative"], "about_bitcoin": "yes", "why": "w"}
1436 | +
1437 | +
1438 | +class TestShadow(unittest.TestCase):
1439 | +    def setUp(self):
1440 | +        self.d = tempfile.TemporaryDirectory()
1441 | +        self.state = os.path.join(self.d.name, "SHADOW86.json")
1442 | +
1443 | +    def tearDown(self):
1444 | +        self.d.cleanup()
1445 | +
1446 | +    def build(self, name, lines, pin):
1447 | +        b = os.path.join(self.d.name, name)
1448 | +        os.makedirs(b)
1449 | +        with open(os.path.join(b, "SHADOW86.jsonl"), "w") as f:
1450 | +            f.write("".join(json.dumps(x) + "\n" for x in lines))
1451 | +        res = {"package": {"segments": [{"text": CLIP}]}, "pin": {"path": "x"}} if pin else \
1452 | +            {"package": {"segments": [{"text": CLIP}]}}           # a package the pin stage refused is no pin
1453 | +        return b, res
1454 | +
1455 | +    def test_a_pin_grok_would_have_stopped_and_the_streak(self):
1456 | +        b, res = self.build("b1", [line(KEEP, KEEP), line(KEEP, EXCL)], pin=True)
1457 | +        s = SH.report(b, res, path=self.state)
1458 | +        self.assertEqual((s["differ"], s["on_pin_differ"], s["would_seal_under_grok"], s["clean_streak"]),
1459 | +                         (1, 1, False, 0))
1460 | +        md = open(os.path.join(b, "SHADOW86.md")).read()
1461 | +        self.assertIn("| exclusion | moment | True | False | looser | yes |", md)   # Heimdall passed what Grok failed
1462 | +        for i in range(3):                                                           # three clean pins in a row
1463 | +            b, res = self.build(f"c{i}", [line(KEEP, KEEP)], pin=True)
1464 | +            self.assertEqual(SH.report(b, res, path=self.state)["clean_streak"], i + 1)
1465 | +        self.assertEqual(SH.clean_streak(self.state), 3)
1466 | +        b, res = self.build("n", [line(KEEP, EXCL)], pin=False)                      # no pin: the streak stays
1467 | +        self.assertIsNone(SH.report(b, res, path=self.state)["would_seal_under_grok"])
1468 | +        self.assertEqual(SH.clean_streak(self.state), 3)
1469 | +
1470 | +    def test_unreadable_answers_and_missing_shadows_are_counted_never_clean(self):
1471 | +        bad = dict(line(KEEP, KEEP), shadow={"backend": "xai:grok", "error": "Unavailable: xAI down"})
1472 | +        b, res = self.build("b", [bad, line(KEEP, KEEP)], pin=True)
1473 | +        s = SH.report(b, res, missing=1, path=self.state)
1474 | +        self.assertEqual((s["not_compared"], s["missing"], s["clean_streak"]), (1, 1, 0))
1475 | +        self.assertEqual(SH.clean_streak(os.path.join(self.d.name, "none.json")), 0)
1476 | +
1477 | +    def test_a_sealed_spotlight_is_a_pin_too(self):
1478 | +        """RULING 90: a spotlight pin is judged by the shadow like a medley pin (ruling 86's "the first pin sealed")."""
1479 | +        seg = [{"text": CLIP}]
1480 | +        self.assertEqual(SH.pin_texts({"pin": None, "spotlight_pin": {"story_id": "s"},
1481 | +                                       "spotlight": {"package": {"segments": seg}}}),
1482 | +                         SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg}}))
1483 | +        self.assertEqual(len(SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg},
1484 | +                                           "spotlight_pin": {"story_id": "s"},
1485 | +                                           "spotlight": {"package": {"segments": seg}}})), 2)
1486 | +        self.assertEqual(SH.pin_texts({"spotlight": {"package": {"segments": seg}}}), [])   # not sealed: no pin
1487 | +
1488 | +
1489 | +if __name__ == "__main__":
1490 | +    unittest.main()
1491 | 
```

---

You are auditing PACKAGE B of a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). It
is the verdict call sites, the shadow's side-by-side report and the replay driver. Package A (the router, the
Heimdall health state, the provider config, the build driver) is audited separately. Only state what you can verify
from the diff; if uncertain, say so; do not guess.

Background (static):
- providers.Router.call(role, ...) tries the role's chain of back-ends. It moves on when a back-end is down, refuses,
  misses its deadline or answers empty. The chain spent raises ProviderError (no verdict, never a pass). Before this
  change, a verdict whose answer was OUT OF CONTRACT (unreadable JSON, wrong keys) was rejected (its recording
  dropped) and gave no verdict. The hook ratings re-asked the SAME model once with another seed.
- providers.call_parsed(router, role, prompt, parse, ...) (package A) calls the chain, and on an answer out of
  contract (parse raises ValueError / TypeError / KeyError) rejects it and asks the NEXT model, each model once.
- Under the new routing "heimdall_first" (package A), Heimdall's families decide every verdict and Grok is last.
  Grok's answers are then asked "in shadow" and recorded, never deciding.

The orders (verbatim excerpts):
- 20:33 Nov 13: "Ruling 82's chain (deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s a call, an out-of-contract answer
  moves on, an outage is never a verdict) applies to every step that today has one Heimdall model as its only route
  when xAI is the writer or is down: the fidelity verdict, coherence / clips-alone / hook ratings, step B, the speaker
  and exclusion verdicts."
- RULING 85.1 (21:15): "REPLAY, no new Grok spend: every recorded Grok verdict since the first ledger build (prompt +
  answer are in your records ...) is re-asked, same prompt, of Heimdall's model families: deepseek-v4.1-flash,
  z-ai/glm-5.3-flash, qwen3.8-27b ... Report per verdict type and per model: agreement with Grok on the DECISION
  (pass / fail, flagged join, rating at or above the bar), the disagreements split into 'Heimdall stricter' and
  'Heimdall looser', median seconds, timeouts, cost. The delivered videos are the anchor: every verdict that let
  0c68b589, 41f29b1f and 37c5b5f5's clips through must still pass, and the ... REFERENT_OUTSIDE refusals must still be
  refused."
- RULING 86 (21:18): the shadow. "every decision where they differ, which was stricter, and whether the pin would have
  sealed under Grok. ... After three pins with no decision-changing difference, the shadow stops."
- RULING 85 (21:15): the first step-A verdict becomes a Heimdall family's under heimdall_first.

- RULING 88 (22:15): "(c) STEP A stays two families with Grok as one of them, but the ORDER changes: the Heimdall
  verdict is asked FIRST; a clip Heimdall refuses is refused and Grok is never asked; only a clip Heimdall passes goes
  to Grok to confirm." The types get their own lists: each call names its kind.

The change (package B):
1. Every verdict call site now uses providers.call_parsed, so an answer out of contract moves on to the next model:
   - vo_fidelity.check (fidelity);
   - moments exclusion (exclusion);
   - speakers (speaker);
   - package.hook_ratings (the hook ratings; the same-model seed re-ask is gone);
   - package.coherence;
   - package.medley (clips-alone);
   - context_integrity: step B twice (step B's relations check is now inside its parser, so a bad relation also moves
     on) and step C.
   Each parse function is the old inline contract check, moved unchanged. The except clauses keep their old outcomes:
   no verdict; never a pass.
2. RULING 88: every call names its kind (prescreen kind="step_a_first" for the first screen, "step_a_second" for the
   second screen and the off-writer re-screen; step C "step_c"; the hook ratings "hook"; clips-alone "clips_alone";
   coherence "coherence"). Under heimdall_first, package._second_bounds gives the second screen (Grok confirming)
   Grok's own batch (8) and no deadline, with the move-on rule kept (prescreen failover=True); under today it stays
   2 clips and 120 s.
3. package.build:
   - the writes avoid the other writers by GATEWAY (providers.gateway), so a Heimdall write may still fail over
     deepseek -> qwen when each Heimdall family is its own maker (heimdall_first);
   - under heimdall_first, the FIRST step-A screen runs SECOND_VERDICT_BATCH (2) clips per call with
     SECOND_VERDICT_DEADLINE_S (120 s): Heimdall needs a median 268 s on 8 clips.
4. tests/package/replay85.py (new): the replay.
   - Each recorded Grok answer is reduced to the pipeline's DECISION with the pipeline's parsers and bars (step A:
     context_integrity.a_failures; clips-alone and coherence: _line_ok, COHERENCE_MIN, LY_MAX_BRIDGES; hooks: the
     lowest of scroll / alone >= HOOK_MIN; exclusion; speaker name; step C and fidelity by stated proxies).
   - The same prompt is then asked of each Heimdall family (its own recordings; ruling 48's ledger; resumable), and
     the decisions compared (agree / stricter / looser / different).
   - Anchors are matched by the delivered pins' clip texts in a prompt.
   - The output is TABLE.md.
5. tests/package/shadow86.py (new): the side-by-side.
   - It reads a build's SHADOW86.jsonl with the replay's decide / compare and writes SHADOW86.md: the differences,
     which side was stricter, and whether the pin would have sealed under Grok (a decision on the pin's clips where
     Heimdall passed and Grok failed).
   - The streak in SHADOW86.json counts pins with no decision-changing difference. A pin with a missing shadow or an
     unreadable one is never clean. A re-read never moves the streak.
6. Tests:
   - test_medley: Grok confirms in its own batches under heimdall_first; the hook ratings move on to the next model; the first screen's bounds under each routing.
   - test_shadow86: a pin Grok would have stopped; the streak to 3; no pin leaves it; unreadable or missing shadows.

Check, against the diff:
- that every parse function is the old contract check, unchanged, and that no out-of-contract answer can become a
  verdict;
- that an outage is never a verdict and nothing is cached from a failed call;
- that the except clauses of every call site still catch what call_parsed can raise;
- that the replay's decision functions match the pipeline's own rules (and where they are proxies, that this is said);
- that the shadow report cannot call a pin clean when a shadow is missing or unreadable;
- the "would have sealed under Grok" logic.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

ADDENDUM (00:4x ET Nov 14): this change is now rebased onto the branch's newer HEAD 07321410. That HEAD adds the
SPOTLIGHT pin kind (rulings 90-92: pipeline/spotlight.py, package_pin's spotlight contract) and RULING 93 (DEC-12d per
clip: visual_pin's burned-in text question). Both were audited separately (2322, 0003). The merge points, to check:
- package.first_bounds(router): one helper for step A's FIRST screen. Under heimdall_first it is 2 clips and 120 s a
  call; under today, {}. The medley build and spotlight.build both call prescreen(..., kind="step_a_first",
  **first_bounds(router)).
- proof_ledger.py keeps both module constants (SPOTLIGHTS for ruling 90; STATE_MD for ruling 87). The spotlight runs
  on the same Router after the medley search, so its calls are shadowed (ruling 86) and noted for Plan B (ruling 87)
  like the medley's.
- shadow86.pin_texts covers a sealed spotlight pin (res["spotlight_pin"] with res["spotlight"]["package"]) as well as
  the medley pin, so ruling 86's "first pin sealed under Heimdall-first" holds whatever the pin's kind.
- The spotlight's value verdict (ruling 91) stays ONE call with no move-on ("one write, one verdict; anything short of
  a clear yes means no line"); its layout verdict (ruling 92) is one vision call, and failing it means not measured.

ADDENDUM 2 (01:1x ET Nov 14):
- The change is now rebased onto HEAD 2f081cba, which adds RULINGS 94 and 95 (audited separately, 0041):
  - stand_alone's hook opener rule (first/second-person pronouns free, third-person ones need the scorer);
  - package._can_open's re-check with the verdict and its spotlight-only deferral;
  - hook trim variants;
  - spotlight.next_attempt.
  The merge was mechanical (git merge-file, no conflict). The one hand-applied line is spotlight.build's step-A call:
  kind="step_a_first" with package.first_bounds(router), as the medley's.
- THE REPLAY IS COMPLETE (884 rows; tests/package/proof/replay85/TABLE.md). Ruling 88 (b) was conditional on the
  full table:
  - it holds for the HOOK rating: qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %. model_providers.json's
    heimdall_first "coherence_verdict:hook" is now qwen -> glm -> deepseek -> Grok (Grok was first);
  - it does not hold for STEP C: glm 97 %, deepseek 96 %, and qwen's 98 % is barred by (e). Step C stays Grok first.
  routing.ruling_88's note records both.

