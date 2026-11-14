# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0041
# Branch: pp-selectid
# Generated: 2026-11-14 00:41 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0041/C1_STEP.diff (535 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index 65c73c4..213a069 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -436,7 +436,7 @@ def _span(span, ctx, role):
   6 |      if conj:
   7 |          targets.append(f"opens on the conjunction{'s' if len(conj) > 1 else ''} {' '.join(conj)!r}")
   8 |      if rest:                       # pronoun / reply-word openers are not in L-o: still hard, after any conjunction too
   9 | -        sc = (ctx.scorer or {}).get(span.key) if role == "clip" else None
  10 | +        sc = (ctx.scorer or {}).get(span.key) if role in ("clip", "hook") else None   # ruling 94 (b): the hook too
  11 |          ok, why = stand_alone.opener(role, rest, *(sc if sc else (None, None)))
  12 |          if not ok:
  13 |              R("opener", why + (f" (after {' '.join(conj)!r})" if conj else ""))
  14 | diff --git a/pipeline/package.py b/pipeline/package.py
  15 | index 07c997d..aed90c6 100644
  16 | --- a/pipeline/package.py
  17 | +++ b/pipeline/package.py
  18 | @@ -1167,7 +1167,8 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, ex
  19 |          left = [(m, no_role_on_screen(m), no_topic(m)) for m in
  20 |                  ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
  21 |          ask = [m for m, o, t in left if o and not t] + \
  22 | -            [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
  23 | +            [v for m, o, t in left if o or t or hook_trim(m) for v in [trim_variant(m, sources)] if v] + \
  24 | +            [m for m, o, t in left if not o and not t and third_opener(m)]      # ruling 94 (a), (b): the hook's
  25 |          have = {(m["moment_id"], text_sha(m["text"])) for m in ask}
  26 |          for m in extra or ():                            # ruling 90: once each (same id and text)
  27 |              k = (m["moment_id"], text_sha(m["text"]))
  28 | @@ -1221,14 +1222,37 @@ def can_open(m):
  29 |      return _can_open(m)
  30 |  
  31 |  
  32 | -def _can_open(m):
  33 | +def hook_trim(m):
  34 | +    """RULING 94 (a): the moment opens on a conjunction or reply word that ruling 33's ONE-word trim may cut
  35 | +    (TRIM_WORDS): its trim variant is what may open, whatever its clip role."""
  36 | +    import stand_alone as SA
  37 | +    w = SA._words(m.get("text") or "")[:1]
  38 | +    return bool(w) and w[0] in TRIM_WORDS
  39 | +
  40 | +
  41 | +def third_opener(m):
  42 | +    """RULING 94 (b): the moment opens on a third-person or demonstrative pronoun: as a hook it needs the clip scorer's
  43 | +    affirmation (stand_alone.THIRD)."""
  44 | +    import stand_alone as SA
  45 | +    w = SA._words(m.get("text") or "")[:1]
  46 | +    return bool(w) and w[0] in SA.THIRD
  47 | +
  48 | +
  49 | +def _can_open(m, pending_verdict=False):
  50 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
  51 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
  52 |      59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
  53 |      (an unmeasured rating is never a pass, law L-m). A moment without the key is judged as before ruling 59."""
  54 |      import stand_alone as SA
  55 | -    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True
  56 | -            and SA.opener("hook", m.get("text") or "")[0]):
  57 | +    v = verdict_of(m)                                    # RULING 94 (b): the scorer's verdict on its current text
  58 | +    sc = (v["score"], v["fault"]) if v else (None, None)
  59 | +    if pending_verdict and v is None and third_opener(m):
  60 | +        sc = (5, None)                                   # the spotlight's ALONE >= 4 decides it later (never sealed
  61 | +    hook = (m.get("eligibility") or {}).get("hook") or {}  # without a verdict: stand_alone_check reads the real one)
  62 | +    elig = hook.get("ok") or (set(hook.get("reasons") or []) == {"opener"} and   # the ledger had no verdict to read
  63 | +                              SA.opener("hook", m.get("text") or "", *sc, moments=True)[0])
  64 | +    if not (elig and (m.get("hook_onset") or {}).get("pass") is True and
  65 | +            SA.opener("hook", m.get("text") or "", *sc, moments=True)[0]):
  66 |          return False
  67 |      if "hook_rating" not in m:
  68 |          return True                                      # not rated yet: judged as before ruling 59
  69 | @@ -2253,11 +2277,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  70 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  71 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  72 |      admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
  73 | -    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms if m["moment_id"] in no_role
  74 | -             for v in [trim_variant(m, sources)] if v}
  75 | +    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms
  76 | +             if m["moment_id"] in no_role or hook_trim(m)                   # ruling 94 (a): a hook's trim variant
  77 | +             for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
  78 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
  79 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
  80 | -    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
  81 | +    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42);
  82 | +    #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
  83 | +    #   video at most once, L-y 4)
  84 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  85 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  86 |      wv, wf = _writers(router)
  87 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  88 | index effb73e..3a0a61d 100644
  89 | --- a/pipeline/spotlight.py
  90 | +++ b/pipeline/spotlight.py
  91 | @@ -60,6 +60,8 @@ CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
  92 |  COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
  93 |  COMMENT_MAX_WORDS = 30
  94 |  MARKER_TOL_S = 1.0                     # = ledger_build.MARKER_EDGE_S: a caption marker this close to an edge is not in
  95 | +TRIM_MARGIN_S = 1.0                    # RULING 94 (a): a moment to be trimmed is snapped this much further, so the
  96 | +                                       # ONE trimmed word never takes it back under SNAP_TO_S
  97 |  LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
  98 |  LAYOUT_OK = ("conversation", "first_hand")
  99 |  CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 100 | @@ -106,7 +108,7 @@ def record_spotlit(path, row):
 101 |      os.replace(path + ".tmp", path)
 102 |  
 103 |  
 104 | -def snap(m, sources, ctx, captions_for=None):
 105 | +def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
 106 |      """RULING 90 with ruling 32's snap: a moment shorter than SNAP_TO_S is snapped OUTWARD to the speaker's whole
 107 |      thought: whole sentences of the SAME word record, the next ones first (the speaker going on), then the ones before
 108 |      it, until it lasts SNAP_TO_S, never past SPOT_S[1] and never across a caption speaker-change marker (ruling 69's
 109 | @@ -145,10 +147,10 @@ def snap(m, sources, ctx, captions_for=None):
 110 |      dur, why = measure(a, b)
 111 |      if dur is None:
 112 |          return None, f"the moment itself: {why}"
 113 | -    if dur >= SNAP_TO_S:
 114 | +    if dur >= target:
 115 |          return m, None                                 # long enough: no snap, the moment as it is
 116 |      blocked = []
 117 | -    while dur < SNAP_TO_S:
 118 | +    while dur < target:
 119 |          step = None
 120 |          for na, nb, side in ((a, b + 1, "the next sentence"), (a - 1, b, "the sentence before")):
 121 |              if na < 0 or nb >= n:
 122 | @@ -203,11 +205,11 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
 123 |          if m["channel_id"] in taken:
 124 |              why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
 125 |              continue
 126 | -        v = m
 127 | -        if float(m["duration_s"]) < SNAP_TO_S:
 128 | -            v, w = snap(m, sources, ctx, captions_for)
 129 | +        v, target = m, SNAP_TO_S + (TRIM_MARGIN_S if P.hook_trim(m) else 0.0)
 130 | +        if float(m["duration_s"]) < target:
 131 | +            v, w = snap(m, sources, ctx, captions_for, target=target)
 132 |              if v is None:
 133 | -                why[mid] = f"ruling 90: {m['duration_s']} s is under {SNAP_TO_S:g} s and the snap fails: {w}"
 134 | +                why[mid] = f"ruling 90: {m['duration_s']} s is under {target:g} s and the snap fails: {w}"
 135 |                  continue
 136 |              ok, w2 = P.usable([v], ctx, delivered, optout, seg_max=SPOT_S[1])
 137 |              if not ok:
 138 | @@ -217,9 +219,18 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
 139 |          if v["moment_id"] in seen:
 140 |              why[mid] = f"the same span as {v['moment_id']}, already in the pool"
 141 |              continue
 142 | +        if P.hook_trim(v):                             # RULING 94 (a): ruling 33's one-word trim variant is what
 143 | +            t = P.trim_variant(v, sources)             # opens; the trim must cut cleanly (build: hook_onset's trim
 144 | +            if t is None:                              # record) and the ALONE scorer must affirm it
 145 | +                why[mid] = f"ruling 94 (a): it opens on {SA._words(v.get('text') or '')[:1]} and has no trim variant"
 146 | +                continue
 147 | +            if t["duration_s"] < SNAP_TO_S:
 148 | +                why[mid] = f"ruling 94 (a): trimmed, {t['duration_s']} s is under {SNAP_TO_S:g} s"
 149 | +                continue
 150 | +            v = t
 151 |          ok, w = SA.opener("hook", v.get("text") or "")
 152 | -        if not ok:
 153 | -            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"
 154 | +        if not ok and not P.third_opener(v):           # RULING 94 (b): a third-person opener is judged by the ALONE
 155 | +            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"   # scorer (>= 4)
 156 |              continue
 157 |          top = P.no_topic(v)
 158 |          if top:
 159 | @@ -269,6 +280,43 @@ def source_test(turns, layout):
 160 |                                        if (turns or {}).get("measured") else "; captions unmarked")
 161 |  
 162 |  
 163 | +def next_attempt(rows, word_pass, now, captions_for=None):
 164 | +    """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 165 | +    could arrive. The NEWEST conversation upload among the adapter's rows: caption turns from pp-ingest's `episode`
 166 | +    (mine-hook/2 rows), else episode_turns(), at least CONVERSATION_TPM a minute (an unmarked episode is not counted:
 167 | +    unknown). Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 168 | +    waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 169 | +    "newest_upload": {...} or None}."""
 170 | +    from datetime import datetime, timedelta, timezone
 171 | +    import package_pin as PPN
 172 | +    by_vid = {}
 173 | +    for r in rows or ():
 174 | +        if isinstance(r, dict) and r.get("video_id"):
 175 | +            by_vid.setdefault(r["video_id"], []).append(r)
 176 | +
 177 | +    def state(vid, rs):
 178 | +        pub = P.utc_z(rs[0].get("published_at"))
 179 | +        ep = next((r.get("episode") for r in rs if isinstance(r.get("episode"), dict)), None)
 180 | +        tpm, frm = (ep or {}).get("turns_per_min"), "pp-ingest episode"
 181 | +        if not isinstance(tpm, (int, float)) and not (ep or {}).get("unmarked"):
 182 | +            t = episode_turns(vid, captions_for)
 183 | +            tpm, frm = t.get("turns_per_min"), "the caption record (recount)"
 184 | +        passes = {}
 185 | +        for r in rs:
 186 | +            k = f"{(r.get('mined') or {}).get('pass')}/{(r.get('mined') or {}).get('prompt_version')}"
 187 | +            passes[k] = passes.get(k, 0) + 1
 188 | +        ready = sum(1 for r in rs if (word_pass.get(r.get("moment_id")) or {}).get("sentence_ready"))
 189 | +        exp = (datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) +
 190 | +               timedelta(hours=PPN.WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None
 191 | +        return {"video_id": vid, "channel": rs[0].get("channel_name"), "published_at": pub, "expires_at": exp,
 192 | +                "turns_per_min": tpm, "turns_from": frm, "rows": len(rs), "passes": passes,
 193 | +                "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 194 | +    sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 195 | +    conv = [x for x in sts if isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] >= CONVERSATION_TPM]
 196 | +    return {"conversation": conv[0] if conv else None, "newest_upload": sts[0] if sts else None,
 197 | +            "rule": f"the newest upload with >= {CONVERSATION_TPM:g} caption turns a minute (ruling 95)"}
 198 | +
 199 | +
 200 |  LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 201 |  bottom. The clip's words, as spoken: "{text}"
 202 |  From the frames only, classify the SOURCE's format:
 203 | @@ -748,8 +796,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 204 |          m["hook_onset"] = P.hook_onset_for(m, sources, work_dir, hk)
 205 |          m.pop("hook_rating", None)                       # a rating is this build's own (its cache's)
 206 |          m.pop("visual_hook_block", None)
 207 | -        if P._can_open(m):
 208 | -            openers[mid] = m
 209 | +        trim = (m["hook_onset"] or {}).get("trim") or {}
 210 | +        if m.get("trimmed_leading") and trim.get("pass") is not True:          # RULING 94 (a): the trim cuts cleanly
 211 | +            stop(mid, f"ruling 94 (a): the trimmed cut is not clean: {trim.get('why') or 'not measured'}")
 212 | +        elif P._can_open(m, pending_verdict=True):     # ruling 94 (b): a third-person opener waits for the ALONE
 213 | +            openers[mid] = m                           # scorer, which must give >= 4 below
 214 |          else:
 215 |              stop(mid, f"it cannot open cold: hook eligibility, G17a ({(m['hook_onset'] or {}).get('why')}) or the "
 216 |                        f"render's hook rule")
 217 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 218 | index a8b2f45..b15cb36 100644
 219 | --- a/pipeline/stand_alone.py
 220 | +++ b/pipeline/stand_alone.py
 221 | @@ -21,6 +21,8 @@ CONJUNCTIONS = {"and", "but", "or", "so", "because", "cause", "which", "also", "
 222 |                  "although", "whereas", "nor", "yet"}          # = editorial_select.CONTINUATION_OPENERS
 223 |  PRONOUNS = {"i", "me", "my", "it", "its", "this", "that", "these", "those", "they", "them", "their", "he", "him",
 224 |              "his", "she", "her", "we", "us", "our", "you", "your", "there"}
 225 | +FIRST_SECOND = {"i", "me", "my", "we", "us", "our", "you", "your"}   # RULING 94 (b): never a cold-open fault
 226 | +THIRD = PRONOUNS - FIRST_SECOND        # RULING 94 (b): a hook fault unless the clip scorer affirms it stands alone
 227 |  REPLY_FRAGMENTS = {"yeah", "yes", "yep", "no", "nope", "right", "exactly", "absolutely", "totally", "sure", "okay",
 228 |                     "ok", "oh", "well", "um", "uh", "agreed", "true", "correct", "indeed", "anyway", "anyways"}
 229 |  BACKREF = {"it", "its", "this", "that", "these", "those", "they"}
 230 | @@ -77,10 +79,20 @@ def opener(kind, text, score=None, fault=None, moments=False):
 231 |      if not ws:
 232 |          return False, "empty segment"
 233 |      w = ws[0]
 234 | -    if kind == "hook":
 235 | -        for group, name in ((PRONOUNS, "pronoun"), (CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
 236 | -            if w in group:
 237 | +    if kind == "hook":                 # RULING 94 (orchestrator 00:40 ET Nov 14)
 238 | +        for group, name in ((CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
 239 | +            if w in group:             # (a): only ruling 33's one-word trim variant may open (trimmed_opener)
 240 |                  return False, f"hook opens on the {name} {w!r}: nothing is heard before a hook"
 241 | +        if w in FIRST_SECOND:          # (b): "I will bet you one Bitcoin that..." is a fine first line
 242 | +            return True, f"opens on the first/second-person {w!r} (ruling 94: not a cold-open fault)"
 243 | +        if w in THIRD:                 # (b): a referent outside the clip is the fault; the clip scorer judges it
 244 | +            if score is None:
 245 | +                return False, (f"hook opens on the third-person or demonstrative {w!r} and no clip-scorer verdict is "
 246 | +                               f"available (fail closed, ruling 94)")
 247 | +            if affirmed(score, fault, moments):
 248 | +                return True, (f"hook opens on {w!r}; the clip scorer affirms it stands alone ({score}, fault {fault}; "
 249 | +                              f"ruling 94)")
 250 | +            return False, f"hook opens on {w!r}; the clip scorer does not affirm it stands alone ({score}, fault {fault})"
 251 |          return True, f"opens on {w!r}"
 252 |      if w in CONJUNCTIONS or w in REPLY_FRAGMENTS:
 253 |          if score is None:
 254 | @@ -164,15 +176,17 @@ def trimmed_opener(word, score, fault, moments=False):
 255 |  
 256 |  def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None, moments=False):
 257 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 258 | -    clips opening on a conjunction / reply fragment (the clip scorer) and for every segment whose lock trims a leading
 259 | -    word (ruling 33 part 2, the hook included); without it they fail closed.
 260 | +    clips opening on a conjunction / reply fragment (the clip scorer), for every segment whose lock trims a leading
 261 | +    word (ruling 33 part 2, the hook included), and for a hook opening on a third-person or demonstrative pronoun
 262 | +    (ruling 94 b); without it they fail closed.
 263 |      screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 264 |      and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 265 |      speaker's own words. screen None: every segment names the subject, as before (the story path).
 266 |      moments (ruling 60, a moments pin): the scorer's verdict is read with affirmed(..., moments=True), the score alone."""
 267 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 268 |      need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
 269 | -            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))]
 270 | +            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)) or
 271 | +            (kind == "hook" and _words(s.get("text"))[:1] and _words(s["text"])[0] in THIRD)]   # ruling 94 (b)
 272 |      scores, rate_error = {}, None
 273 |      if need and rate is not None:
 274 |          try:
 275 | diff --git a/pipeline/test_stand_alone.py b/pipeline/test_stand_alone.py
 276 | index cdb3ce3..972272f 100644
 277 | --- a/pipeline/test_stand_alone.py
 278 | +++ b/pipeline/test_stand_alone.py
 279 | @@ -23,16 +23,28 @@ DATADASH = ("Bitcoin has now seen a 16 % decline from the overall high from $88
 280 |  
 281 |  class TestOpener(unittest.TestCase):
 282 |      def test_hook_must_fail(self):
 283 | -        for text in (RUN6_HOOK, "I don't check it on an hourly basis. It seemed to have bounced.",
 284 | -                     "It seemed to have bounced very nicely at $74,000.", "Yeah, Bitcoin is down 16 %.",
 285 | -                     "So Bitcoin is down.", "We've seen Bitcoin lose 16 %."):
 286 | +        for text in (RUN6_HOOK, "It seemed to have bounced very nicely at $74,000.", "Yeah, Bitcoin is down 16 %.",
 287 | +                     "So Bitcoin is down.", "They sold it all at the bottom."):
 288 |              ok, why = S.opener("hook", text)
 289 |              self.assertFalse(ok, (text, why))
 290 |  
 291 |      def test_hook_must_pass(self):
 292 | -        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin."):
 293 | +        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin.",
 294 | +                     "I don't check it on an hourly basis. It seemed to have bounced.",      # RULING 94 (b): first or
 295 | +                     "We've seen Bitcoin lose 16 %.", "I will bet you one Bitcoin that it gets there."):   # second person
 296 |              self.assertTrue(S.opener("hook", text)[0], text)
 297 |  
 298 | +    def test_ruling_94_a_third_person_hook_needs_the_scorer(self):
 299 | +        text = "This is ultimately a bipartisan issue."
 300 | +        self.assertFalse(S.opener("hook", text)[0])                                  # no verdict: fail closed
 301 | +        self.assertTrue(S.opener("hook", text, 4.0, "none", moments=True)[0])
 302 | +        self.assertFalse(S.opener("hook", text, 3.0, "none", moments=True)[0])
 303 | +        self.assertEqual(S.PRONOUNS, S.FIRST_SECOND | S.THIRD)
 304 | +        edl = {"hook": {"channel": "H", "text": text}, "clips": []}
 305 | +        r = S.check_edl(edl, rate=lambda ps: {p["pid"]: (4.0, "r", "none") for p in ps}, moments=True)
 306 | +        self.assertTrue(r["rows"][0]["opener"]["pass"], r["rows"][0])                # the hook is rated (check_edl)
 307 | +        self.assertFalse(S.check_edl(edl, rate=None, moments=True)["rows"][0]["opener"]["pass"])
 308 | +
 309 |      def test_clip_conjunction_needs_the_scorer(self):
 310 |          self.assertTrue(S.opener("clip", RUN6_CLIP01, 5.0, "none")[0])
 311 |          self.assertFalse(S.opener("clip", RUN6_CLIP01, 3.0, "starts_mid_thought")[0])
 312 | @@ -102,7 +114,8 @@ class TestAutoSelectionScreen(unittest.TestCase):
 313 |      def test_selection_uses_the_same_rule(self):
 314 |          import editorial_select as es
 315 |          subj = S.subject_terms("Binance exchange", "Binance hacked for six billion dollars")
 316 | -        self.assertFalse(es._stand_alone_ok("hook", "We just had, of course, Binance with $6 .3 billion in hacks.", subj)[0])
 317 | +        self.assertFalse(es._stand_alone_ok("hook", "They just had, of course, Binance with $6 .3 billion in hacks.",
 318 | +                                            subj)[0])                # ruling 94 (b): a third-person opener, no verdict
 319 |          self.assertTrue(es._stand_alone_ok("hook", "Binance confirmed the hack this morning. It means six billion "
 320 |                                                     "dollars of customer money left the exchange.", subj)[0])
 321 |          self.assertFalse(es._stand_alone_ok("clip", RUN6_CLIP02, S.subject_terms("Bitcoin / US spot Bitcoin ETFs"))[0])
 322 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 323 | index cd89e2d..583fe06 100644
 324 | --- a/tests/eligibility/test_eligibility.py
 325 | +++ b/tests/eligibility/test_eligibility.py
 326 | @@ -194,6 +194,14 @@ class TestSource(unittest.TestCase):
 327 |          self.assertIs(E.eligible(nobody, ctx("evidence")).facts["layout_eligible"], False)
 328 |          self.assertIn("layout_ineligible", E.eligible(nobody, ctx("clip")).names())
 329 |  
 330 | +    def test_ruling_94_pronoun_openers_on_the_hook(self):
 331 | +        first = source(["I will bet you one Bitcoin that it gets back to the highs before the end of next year."])
 332 | +        self.assertNotIn("opener", E.eligible(E.Span(first, 0, 0), ctx("hook")).names())    # (b): no fault
 333 | +        third = source(["They sold every Bitcoin they had at the very bottom of the market last week."])
 334 | +        r = E.eligible(E.Span(third, 0, 0), ctx("hook"))
 335 | +        self.assertIn("opener", r.names())                         # no verdict at the ledger: the pin stage decides
 336 | +        self.assertIn("no clip-scorer verdict", r.why())
 337 | +
 338 |      def test_on_screen_needs_a_sentence_ready_word_record(self):
 339 |          seg = source([HOOK_TXT], timing="segment", method="yt_auto:en")
 340 |          self.assertTrue(E.eligible(seg, ctx("evidence")).ok)
 341 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 342 | index 1a1371b..74013a1 100644
 343 | --- a/tests/package/proof_ledger.py
 344 | +++ b/tests/package/proof_ledger.py
 345 | @@ -257,6 +257,10 @@ def main(argv=None):
 346 |                      spotlit=spotlit)
 347 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
 348 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
 349 | +    try:                                                 # RULING 95: when the next qualifying episode could arrive
 350 | +        res["next_attempt"] = SPOT.next_attempt(rows, wp, now)
 351 | +    except Exception as e:                               # noqa: BLE001  a report, never the build
 352 | +        res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
 353 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 354 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 355 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 356 | @@ -313,6 +317,11 @@ def main(argv=None):
 357 |              res["spotlight_pin_refused"] = f"{type(e).__name__}: {e}"
 358 |              say(f"SPOTLIGHT PIN REFUSED: {e}")
 359 |      else:
 360 | +        na = (res.get("next_attempt") or {}).get("conversation") or {}
 361 | +        say(f"  RULING 95: the newest conversation upload: {na.get('channel')} {na.get('video_id')} published "
 362 | +            f"{na.get('published_at')} (expires {na.get('expires_at')}), {na.get('turns_per_min')} turns a minute, "
 363 | +            f"rows {na.get('passes')}, word pass {na.get('word_pass_ready')} ready / {na.get('word_pass_waiting')} "
 364 | +            f"waiting" if na else "  RULING 95: no conversation upload in the window")
 365 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 366 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 367 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 368 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 369 | index f1f2942..0497719 100644
 370 | --- a/tests/package/test_medley.py
 371 | +++ b/tests/package/test_medley.py
 372 | @@ -14,6 +14,8 @@ import json
 373 |  import re
 374 |  import os
 375 |  import sys
 376 | +import shutil
 377 | +import tempfile
 378 |  import unittest
 379 |  from datetime import timedelta
 380 |  
 381 | @@ -1090,6 +1092,65 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 382 |          self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 383 |  
 384 |  
 385 | +class TestRuling94HookOpeners(unittest.TestCase):
 386 | +    """RULING 94 (00:40 ET Nov 14): (a) a hook opening on a conjunction or reply word opens as ruling 33's one-word trim
 387 | +    variant, whatever its clip role (the trim cuts cleanly, the scorer affirms it); (b) a first/second-person opener is
 388 | +    no fault; a third-person or demonstrative one needs the clip scorer's affirmation."""
 389 | +
 390 | +    def opener(self, text, reasons=(), verdict=None):
 391 | +        m = dict(pm("o", "O", 13.0), text=text, hook_onset={"pass": True, "measured": True})
 392 | +        m["eligibility"] = {"hook": {"ok": not reasons, "reasons": list(reasons)}, "clip": {"ok": True}}
 393 | +        return dict(m, scorer_verdict=verdict) if verdict else m
 394 | +
 395 | +    def test_first_and_second_person_open_and_third_person_needs_the_scorer(self):
 396 | +        self.assertTrue(PK._can_open(self.opener("I will bet you one Bitcoin that it gets there.")))
 397 | +        self.assertTrue(PK._can_open(self.opener("You know, Bitcoin is not done.")))
 398 | +        t = "This is ultimately a bipartisan issue for Bitcoin."
 399 | +        self.assertTrue(PK.third_opener({"text": t}))
 400 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener"])))                         # no verdict: closed
 401 | +        self.assertTrue(PK._can_open(self.opener(t, ["opener"], sv(t, 4.0))))              # affirmed: open
 402 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener"], sv(t, 3.0))))
 403 | +        self.assertTrue(PK._can_open(self.opener(t, ["opener"]), pending_verdict=True))   # the spotlight waits
 404 | +        self.assertFalse(PK._can_open(self.opener(t, ["opener", "hook_lead"], sv(t, 4.0))))   # another reason holds
 405 | +        self.assertFalse(PK._can_open(self.opener("So Bitcoin is down.")))                 # (a): only the trim opens
 406 | +        self.assertTrue(PK.hook_trim({"text": "So Bitcoin is down."}))
 407 | +        self.assertFalse(PK.hook_trim({"text": "Because Bitcoin is down."}))               # not a ruled trim word
 408 | +
 409 | +    def test_the_scorer_is_asked_for_a_hook_trim_and_a_third_person_opener(self):
 410 | +        d = tempfile.mkdtemp()
 411 | +        try:
 412 | +            src = source(["So Bitcoin has rarely seen six negative weeks back to back in its whole history."],
 413 | +                         vid="vS")
 414 | +            a, b = src.sentences[0]
 415 | +            so = dict(pm("s", "S", 0.0, vid="vS"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
 416 | +                      start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
 417 | +            so = dict(so, scorer_verdict=sv(so["text"], 4.0))          # its CLIP role is affirmed as it is
 418 | +            this = dict(pm("t", "T", 12.0), text="This is ultimately a bipartisan issue for Bitcoin.")
 419 | +            plain = dict(pm("p", "P", 12.0), text="Bitcoin is the hardest money there is.")
 420 | +            PK.scorer_pass([so, this, plain], {"vS": src}, E.Context(NOW, REG), None,
 421 | +                           os.path.join(d, "c.json"), "b")
 422 | +            asked = [c["pid"] for c in json.load(open(os.path.join(d, "c.json")))["candidates"]]
 423 | +            self.assertIn("s~trim", asked)                              # (a): its hook trim variant
 424 | +            self.assertIn("t", asked)                                   # (b): the third-person opener itself
 425 | +            self.assertNotIn("p", asked)
 426 | +        finally:
 427 | +            shutil.rmtree(d, ignore_errors=True)
 428 | +
 429 | +    def test_a_hook_trim_variant_joins_the_pool_beside_its_affirmed_original(self):
 430 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 431 | +              dict(pm("s", "E", 13.0), text="So Bitcoin x.")]
 432 | +        v = dict(ms[4], moment_id="s~trim", text="Bitcoin x.", trimmed_leading="So", untrimmed_start=0.0)
 433 | +        saved = PK.trim_variant
 434 | +        try:
 435 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "s" else None
 436 | +            ok = {"s": fv("So Bitcoin x.", 4.0), "s~trim": fv("Bitcoin x.", 4.0)}   # the clip role affirmed as it is
 437 | +            out = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=ok).run()
 438 | +        finally:
 439 | +            PK.trim_variant = saved
 440 | +        self.assertEqual(out["trimmed"], {"s": "s~trim"})               # ruling 94 (a): not only for no_role ones
 441 | +        self.assertIsNotNone(out["package"])
 442 | +
 443 | +
 444 |  class TestRuling58StepAEveryCandidate(unittest.TestCase):
 445 |      """RULING 58 (11:00): EVERY candidate is screened at step A, the miner's best first, and a verdict is cached by the
 446 |      moment id + its text sha (and the exact context step A reads), so a moment is paid for once, not once per build."""
 447 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 448 | index 438d123..f54e108 100644
 449 | --- a/tests/package/test_spotlight.py
 450 | +++ b/tests/package/test_spotlight.py
 451 | @@ -389,7 +389,7 @@ class TestPool(unittest.TestCase):
 452 |          caps = lambda vid: (None, None)
 453 |          long_ok = moment(mid="l", dur=30.0, channel="A")
 454 |          too_long = moment(mid="t", dur=36.0, channel="B", text=TEXT.replace("money", "asset"))
 455 | -        conj = moment(mid="c", channel="C", text="And " + TEXT.replace("money", "thing"))
 456 | +        conj = moment(mid="c", channel="C", text="Because " + TEXT.replace("money", "thing"))   # not a trim word
 457 |          got, why = SPOT.pool([long_ok, too_long, conj], {}, ctx, spotlit=[], captions_for=caps)
 458 |          self.assertEqual([m["moment_id"] for m in got], ["l"])               # 30 s: a medley's 20 s does not bind
 459 |          self.assertIn("35.0 s", why["t"])
 460 | @@ -411,6 +411,55 @@ class TestPool(unittest.TestCase):
 461 |                  os.remove(p)
 462 |  
 463 |  
 464 | +class TestRuling94And95(unittest.TestCase):
 465 | +    def test_a_conjunction_opener_is_trimmed_and_a_third_person_one_waits_for_the_alone_scorer(self):
 466 | +        so = "So Bitcoin keeps moving and people keep watching it closely right now in every single market we follow."
 467 | +        m, srcs, ctx, caps = snap_rig([S5, so, S20, S5], 1)
 468 | +        got, why = SPOT.pool([m], srcs, ctx, spotlit=[], captions_for=caps)
 469 | +        self.assertEqual(len(got), 1, why)
 470 | +        v = got[0]
 471 | +        self.assertEqual(v["trimmed_leading"], "So")                    # ruling 94 (a): the variant opens
 472 | +        self.assertTrue(v["moment_id"].endswith("~trim"))
 473 | +        self.assertGreaterEqual(v["duration_s"], SPOT.SNAP_TO_S)       # snapped with the margin, then trimmed
 474 | +        this = moment(mid="t", channel="T", text="This is ultimately a bipartisan issue for Bitcoin and for every "
 475 | +                                                   "holder of it, whatever their politics, as far as I can tell.")
 476 | +        got, why = SPOT.pool([this], {}, E.Context(NOW, REG), spotlit=[], captions_for=lambda vid: (None, None))
 477 | +        self.assertEqual([x["moment_id"] for x in got], ["t"])          # (b): the ALONE scorer decides later
 478 | +        they = moment(mid="u", channel="U", text="And " + TEXT)             # no word record: no trim variant
 479 | +        got, why = SPOT.pool([they], {}, E.Context(NOW, REG), spotlit=[], captions_for=lambda vid: (None, None))
 480 | +        self.assertIn("ruling 94 (a)", why["u"])
 481 | +
 482 | +    def test_an_unclean_trim_cut_is_stopped(self):
 483 | +        b = TestBuild()
 484 | +        ms = [moment(mid="a~trim", channel="A", trimmed_leading="So", untrimmed_start=0.0)]
 485 | +        out, calls = b.run_build(ms, {"a~trim": 5}, onset={"pass": True, "measured": True,
 486 | +                                                         "trim": {"pass": False, "why": "it bleeds"}})
 487 | +        self.assertIn("ruling 94 (a): the trimmed cut is not clean: it bleeds", out["moments"]["a~trim"]["out"])
 488 | +        self.assertNotIn("package_for", calls)
 489 | +
 490 | +    def test_ruling_95_the_newest_conversation_upload_and_its_mining_state(self):
 491 | +        rows = [{"video_id": "old", "channel_name": "Talk", "published_at": "2026-11-13T18:00:00+00:00",
 492 | +                 "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 493 | +                                                                                "prompt_version": "mine-hook/2"}},
 494 | +                {"video_id": "new", "channel_name": "Solo", "published_at": "2026-11-13T22:00:00+00:00",
 495 | +                 "moment_id": "n1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "moment",
 496 | +                                                                                "prompt_version": "mine/2"}},
 497 | +                {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 498 | +                 "moment_id": "m1", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "hook",
 499 | +                                                                                "prompt_version": "mine-hook/2"}},
 500 | +                {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 501 | +                 "moment_id": "m2", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "moment",
 502 | +                                                                                "prompt_version": "mine/2"}}]
 503 | +        na = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW)
 504 | +        c = na["conversation"]
 505 | +        self.assertEqual((c["video_id"], c["published_at"], c["expires_at"]),
 506 | +                         ("mid", "2026-11-13T20:00:00Z", "2026-11-14T08:00:00Z"))
 507 | +        self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_waiting"]), (2, 1, 1))
 508 | +        self.assertEqual(c["passes"], {"hook/mine-hook/2": 1, "moment/mine/2": 1})
 509 | +        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but not a conversation
 510 | +        self.assertIsNone(SPOT.next_attempt([], {}, NOW)["conversation"])
 511 | +
 512 | +
 513 |  class TestPackageFor(unittest.TestCase):
 514 |      def test_the_closing_line_ships_only_with_every_gate(self):
 515 |          pk, why, router, asked, fids = package()
 516 | @@ -495,7 +544,8 @@ class TestPackageFor(unittest.TestCase):
 517 |  class TestBuild(unittest.TestCase):
 518 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 519 |  
 520 | -    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None):
 521 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None,
 522 | +                  onset=None):
 523 |          ctx = E.Context(NOW, REG)
 524 |          calls = {}
 525 |  
 526 | @@ -521,7 +571,7 @@ class TestBuild(unittest.TestCase):
 527 |          stubs = [(SPOT.P, "prescreen", prescreen), (SPOT.P, "hook_ratings", hook_ratings),
 528 |                   (SPOT.P, "second_screen", second), (SPOT, "package_for", package_for),
 529 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 530 | -                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
 531 | +                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: onset or {"pass": True, "measured": True}),
 532 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 533 |                   (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 534 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 535 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that another
session renders into short Bitcoin videos). Only state what you can verify from the diff; if uncertain, say so; do
not guess. Be specific: file:line and a concrete input that breaks it.

Background (static):
- A pin's HOOK opens the video cold. The render's STAND_ALONE (stand_alone.py, the same rule on the render's side and
  this builder's pin stage) refused a hook whose first word is a conjunction, a reply word or any pronoun. A CLIP
  opening on a conjunction or reply word passes only with the render's clip scorer's affirmation (the "ALONE scorer":
  verdicts on exactly the text, read through package.verdict_of).
- Ruling 33 part 2: a moment opening on ONE of TRIM_WORDS (but, and, so, well, now, yeah) may be cut one word in (a
  "~trim" variant carrying trimmed_leading / untrimmed_start). The variant is judged like any moment, its trimmed cut
  must open cleanly (hook_onset's "trim" record), and the scorer must affirm the trimmed text (trim_refused /
  check_edl's trimmed_opener). Until now the medley built trim variants only for moments with no on-screen role.
- The medley build rates hooks (hook_ratings) only for moments that can open (package._can_open: hook eligibility from
  the ledger, G17a, the opener rule). The spotlight (pipeline/spotlight.py) is a one-clip pin that needs, among
  others, the ALONE scorer >= 4 on its text.
- Law L-m: nothing measured is never a pass. Fail closed.

The order (verbatim): "94. Of the 23 Bitcoin Magazine interview moments, 13 never reach a judge because they open on
a conjunction or a pronoun. For SPOTLIGHT and for a medley HOOK alike: (a) a leading conjunction or reply word gets
ruling 33's ONE-word trim variant and that variant is what is rated as an opener (the trim must cut cleanly and the
ALONE scorer must affirm it, as for a clip); (b) a first-person or second-person pronoun opener ('I', 'we', 'you',
'my', 'our') is NOT a cold-open fault at all: 'I will bet you one Bitcoin that...' is a fine first line; only a
THIRD-person or demonstrative pronoun with no referent in the clip ('he', 'they', 'it', 'this', 'that') is, and the
ALONE scorer + step A already judge exactly that. ... This touches the render's hook opener rule too: agree the change
with the integrator, one audited change each side." and "95. When a build ends with no medley and no spotlight, STATE
line 1 carries the three nearest ...; Add the time the next qualifying episode could arrive (the newest conversation
upload's publish time + its mining state)."
The integrator AGREED (01:0x ET) the hook rule below, with check_edl rating a third-person hook; its side is audited
separately.

The change:
1. stand_alone.py: FIRST_SECOND = {i, me, my, we, us, our, you, your}; THIRD = PRONOUNS - FIRST_SECOND. opener("hook"):
   a conjunction or reply word is still a fault (only a trim variant opens); FIRST_SECOND is ok; THIRD is ok only
   with an affirming scorer verdict (affirmed(score, fault, moments)), else a fault. check_edl asks the scorer about a
   hook whose first word is in THIRD.
2. eligibility.py: the hook role, like the clip role, reads the scorer verdict when the ledger has one (it does not:
   a third-person hook fails "opener" at the ledger and is decided at the pin stage).
3. package.py: hook_trim(m) and third_opener(m); _can_open re-checks a hook whose ONLY failing eligibility reason is
   "opener" with the verdict now attached (pending_verdict=True lets the spotlight defer a third-person opener to its
   ALONE >= 4 gate); scorer_pass asks for the trim variant of every hook_trim moment and for every third-person
   opener; build() adds a trim variant for every hook_trim moment (the original keeps its own place as a clip; a
   line-up never takes one video twice).
4. spotlight.py: pool() snaps a moment to be trimmed TRIM_MARGIN_S further, then takes its trim variant (refused when
   none exists or it ends under 13.7 s); a third-person opener enters the pool for the ALONE scorer to decide; build()
   stops a trimmed moment whose trimmed cut is not clean and opens with _can_open(m, pending_verdict=True).
   next_attempt() (ruling 95): the newest upload with >= 1.0 caption turns a minute among the adapter's rows, its
   publish time, its expiry (12 h), its rows by mining pass and its word-pass windows ready / waiting; the driver
   records and logs it.
5. Tests: the hook rule's cases (stand_alone and eligibility), _can_open, the scorer's candidates, a hook trim variant
   beside its affirmed original in a medley build, the spotlight's trim and third-person paths and the unclean trim
   cut, next_attempt.

Check: that no third-person hook can open, or be sealed, without an affirming verdict on its exact text (and that
pending_verdict cannot leak into the medley or into a sealed pin); that a trimmed hook is only ever the variant (never
the untrimmed original) and is sealed with its affirmation; that a first/second-person opener is the only new pass
without a verdict; that the margin keeps a trimmed spotlight at or over 13.7 s; that next_attempt reports only measured
facts. Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".

