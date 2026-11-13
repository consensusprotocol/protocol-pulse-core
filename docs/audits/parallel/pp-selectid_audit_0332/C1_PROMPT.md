# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0332
# Branch: pp-selectid
# Generated: 2026-11-13 03:29 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0332/C1_STEP.diff (556 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 1b97ff09..16f2c18f 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -17,15 +17,16 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
   6 |    - word_pass_index() reads that list. window_source() checks every claim before use: the file's sha256 is the row's
   7 |      record_sha256, the segments sha, words_sha256, the words spell the segments, the YouTube clock, nothing still
   8 |      unpunctuated, and the ledger row's span inside the window.
   9 | -  - One window per video: the best-ranked row whose window record passes every check (a row whose own record fails
  10 | -    is passed over with why). The video's other rows re-anchor in it, or are counted out.
  11 | +  - One window per MOMENT (audit 0208): each row re-anchors in its own window record when that record passes every
  12 | +    check (a row whose record fails is counted with why); the same speech in two windows is one moment.
  13 |    - L-s context comes from the caption record the ledger mined the moment from (caption_source(): its segments sha
  14 |      is the row's transcript_sha256), cut by time (context_integrity.caption_parts). Without one, the context is
  15 |      unavailable and L-s fails closed.
  16 |  - RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  17 | -  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  18 | -  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  19 | -  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
  20 | +  row's caption-clock times only narrow the search. The span then snaps OUTWARD to that record's WHOLE sentences
  21 | +  (ruling 32), when the snapped span is at most SNAP_MAX_S long and holds no caption speaker marker. Otherwise the row
  22 | +  is dropped, and why is recorded; a row whose text does not anchor at all stays out. The moment's text becomes the
  23 | +  word record's own words, verbatim, the words the render locks on.
  24 |  - RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  25 |    row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  26 |  -> build_inputs(...) = (moments, sources, report).
  27 | @@ -41,15 +42,17 @@ import select_by_id as S
  28 |  import sentence_law as SL
  29 |  import transcript_store as ts
  30 |  
  31 | -SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
  32 | -SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
  33 | -                                      r"hardly|scarcely|barely|rarely|seldom|"
  34 | -                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
  35 | -                                      r"\w+n't)$|\d", __import__("re").I)
  36 | -                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
  37 | -                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1; the
  38 | -                          # near-negations "hardly" ... "seldom": qwen C3)
  39 | -APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}   # a typographic apostrophe is read as ' by the guard
  40 | +SNAP_MAX_S = 20.0         # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  41 | +                          # is SNAPPED OUTWARD to the word record's whole sentences, instead of dropped, when the
  42 | +                          # snapped span stays inside the clip length limit (= package.SEG_MAX_S, L-u) and shows no
  43 | +                          # speaker change. The added words are the speaker's own, so nothing is changed by omission;
  44 | +                          # the snapped span is judged as usual: step A (L-s), the exclusion verdict (every L-u risk),
  45 | +                          # L-v 2 (every number and negation both ways, exactly one speaker measured) and usable() (time
  46 | +                          # words). It replaces SNAP_WORDS = 3 and SNAP_GUARD (audit 2315 C1), whose concern was words
  47 | +                          # the ledger never judged: those gates judge them. Its price predictions: snap_risk().
  48 | +SPEAKER_MARKERS = (">>", "&gt;&gt;")   # a caption speaker change (pp-ingest contract.SPEAKER_MARKERS)
  49 | +MARKER_EDGE_S = 1.0       # caption token times may be interpolated across a cue: a marker this close to a snapped edge
  50 | +                          # is not placed inside it here, and L-v 2 measures the speaker on the audio
  51 |  SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]. Captions
  52 |                            # and word records share the full-video clock, and a caption cue starts or ends a few
  53 |                            # seconds off the words; the window only keeps a phrase said again elsewhere in the video
  54 | @@ -343,8 +346,33 @@ def word_source(row, ctx, store=STORE):
  55 |      return None, None, passed_over
  56 |  
  57 |  
  58 | -def reanchor(row, src):
  59 | -    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
  60 | +def marker_inside(cap, a, b):
  61 | +    """The time of a caption speaker marker ('>>', stored '&gt;&gt;') more than MARKER_EDGE_S inside [a, b] (seconds on
  62 | +    the media clock): a MEASURED speaker change. None otherwise: no marker, or no caption record, is not a measurement
  63 | +    (L-m), and L-v 2 measures the speaker on the audio before the moment can be used."""
  64 | +    for t in (getattr(cap, "tokens", None) or []):
  65 | +        if str(t.get("word") or "").lstrip().startswith(SPEAKER_MARKERS):
  66 | +            s = t.get("start")
  67 | +            if isinstance(s, (int, float)) and a + MARKER_EDGE_S < float(s) < b - MARKER_EDGE_S:
  68 | +                return float(s)
  69 | +    return None
  70 | +
  71 | +
  72 | +def snap_risk(text, info, risk):
  73 | +    """Ruling 32: the miner flagged price predictions on the ROW's text, so a SNAPPED moment's are counted on its
  74 | +    snapped text (a future price per vo_fidelity.price_mentions), for the per-video cap (L-u). -> a new risk list."""
  75 | +    import vo_fidelity as VF
  76 | +    out = list(risk or [])
  77 | +    if any((info or {}).get("snapped_words") or []) and "price_prediction" not in out and \
  78 | +            any(kind == "future" for _, kind in VF.price_mentions(text or "")):
  79 | +        out.append("price_prediction")
  80 | +    return out
  81 | +
  82 | +
  83 | +def reanchor(row, src, cap=None):
  84 | +    """The row's TEXT located in the word record and SNAPPED OUTWARD to its whole sentences (ruling 32) -> (E.Span,
  85 | +    info) or (None, why). cap: the caption record the row was mined from, read for its speaker markers (default: a
  86 | +    window Source's context_source)."""
  87 |      def num(x):
  88 |          try:
  89 |              return float(x)
  90 | @@ -363,18 +391,21 @@ def reanchor(row, src):
  91 |      k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
  92 |      if k0 is None or k1 is None:
  93 |          return None, "the anchored words fall outside the record's sentences"
  94 | -    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
  95 | -    if left > SNAP_WORDS or right > SNAP_WORDS:
  96 | -        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
  97 | -                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
  98 | -    added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
  99 | -             for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
 100 | -    # a typographic apostrophe reads as ' here (glm C2 N-3; none of the store's 66 word records holds one today)
 101 | -    risky = [w for w in added if SNAP_GUARD.search(w)]
 102 | -    if risky:
 103 | -        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
 104 | -    sp = E.Span(src, k0, k1)
 105 | +    (s0, _), (_, s1) = src.sentences[k0], src.sentences[k1]
 106 | +    left, right = i0 - s0, s1 - i1
 107 |      info = {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 108 | +    if left or right:
 109 | +        snap = f"snapped outward to whole sentences ({left} word(s) before the anchored text, {right} after)"
 110 | +        a, b = num(src.tokens[s0].get("start")), num(src.tokens[s1].get("end"))
 111 | +        if a is None or b is None:
 112 | +            return None, f"{snap}, its length is not measured (a word time is missing)"
 113 | +        if b - a > SNAP_MAX_S:
 114 | +            return None, f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32: the clip length limit)"
 115 | +        t = marker_inside(cap if cap is not None else getattr(src, "context_source", None), a, b)
 116 | +        if t is not None:
 117 | +            return None, f"{snap} it holds a caption speaker marker at {t:.2f} s: a measured speaker change (ruling 32)"
 118 | +        info["added"] = {"before": E.spoken(src.tokens[s0:i0]), "after": E.spoken(src.tokens[i1 + 1:s1 + 1])}
 119 | +    sp = E.Span(src, k0, k1)
 120 |      a, b = num(src.tokens[i0].get("start")), num(src.tokens[i1].get("end"))
 121 |      # the hit against the row's own caption times: a phrase said twice inside the window shows here (glm C3 P1-3);
 122 |      # when it cannot be measured, it says so (glm C4 P2-8)
 123 | @@ -413,7 +444,7 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
 124 |      def make(i, r, sp, info, src):
 125 |          try:
 126 |              m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 127 | -                 "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 128 | +                 "risk": snap_risk(sp.text, info, r.get("risk")), "topics": list(r.get("topics") or []),
 129 |                   "reason": r.get("reason") or ""}
 130 |              mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 131 |                           ledger_text=r.get("text"))
 132 | @@ -445,8 +476,12 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
 133 |              if passed_over:
 134 |                  report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 135 |              report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 136 | -            for i, r in irs:
 137 | -                sp, info = reanchor(r, src)
 138 | +            caps_v = {}                              # the caption record a row was mined from, once per sha: its
 139 | +            for i, r in irs:                         # speaker markers for a snapped span (ruling 32)
 140 | +                sha = r.get("transcript_sha256")
 141 | +                if sha not in caps_v:
 142 | +                    caps_v[sha] = caption_source(r, ctx, store, ledger_store)[0]
 143 | +                sp, info = reanchor(r, src, cap=caps_v[sha])
 144 |                  if sp is None:
 145 |                      report["not_anchored"][r["moment_id"]] = info
 146 |                      continue
 147 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 148 | new file mode 100644
 149 | index 00000000..79606880
 150 | --- /dev/null
 151 | +++ b/tests/package/funnel.py
 152 | @@ -0,0 +1,247 @@
 153 | +#!/usr/bin/env python3
 154 | +"""The FUNNEL TABLE of one ledger build record (orchestrator 02:45 item 1): per stage, the moments lost per exact
 155 | +reason, with one example moment text per reason. No vendor call: it reads the record (inputs.json, package.json,
 156 | +step_a.json, package.log), the ledger for row texts, and recomputes the CUTTABLE edges from the RECORDED scribe replies
 157 | +(Router replay=True: a reply not recorded raises, it is never fetched).
 158 | +usage: tests/package/funnel.py <build dir>"""
 159 | +import collections
 160 | +import json
 161 | +import os
 162 | +import re
 163 | +import sys
 164 | +
 165 | +D = sys.argv[1]
 166 | +REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 167 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 168 | +LEDGER = "/home/ultron/worktrees/pp-ingest/data/editorial/moments/moment_ledger.jsonl"
 169 | +REPLIES = os.path.join(REPO, "tests", "package", "fixtures", "replies")
 170 | +LV2 = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad/lv2"
 171 | +inp = json.load(open(os.path.join(D, "inputs.json")))
 172 | +pk = json.load(open(os.path.join(D, "package.json")))
 173 | +sa = json.load(open(os.path.join(D, "step_a.json"))) if os.path.exists(os.path.join(D, "step_a.json")) else {}
 174 | +rep, moments = inp["inputs"], inp["moments"]
 175 | +by = {m["moment_id"]: m for m in moments}
 176 | +texts = {}
 177 | +for line in open(LEDGER):
 178 | +    try:
 179 | +        r = json.loads(line)
 180 | +    except ValueError:
 181 | +        continue
 182 | +    if isinstance(r, dict) and r.get("moment_id"):
 183 | +        texts[r["moment_id"]] = r.get("text") or ""
 184 | +
 185 | +
 186 | +def q(t, n=140):
 187 | +    t = " ".join(str(t or "").split()).replace("|", "/")
 188 | +    return t if len(t) <= n else t[:n - 1] + "…"
 189 | +
 190 | +
 191 | +def tx(mid):
 192 | +    return by.get(mid, {}).get("text") or texts.get(mid) or ""
 193 | +
 194 | +
 195 | +def emit(title, rows, head=("lost", "exact reason", "one example (moment text)")):
 196 | +    print(f"\n**{title}**\n")
 197 | +    print("| " + " | ".join(head) + " |")
 198 | +    print("|" + "---|" * len(head))
 199 | +    for r in rows:
 200 | +        print("| " + " | ".join(str(c) for c in r) + " |")
 201 | +
 202 | +
 203 | +def grouped(items):
 204 | +    """items: [(reason, mid)] -> rows [count, reason, example] by count, the example the first moment of the reason."""
 205 | +    g = collections.OrderedDict()
 206 | +    for why, mid in items:
 207 | +        g.setdefault(why, []).append(mid)
 208 | +    return [[len(ms), why, f'"{q(tx(ms[0]))}"' if ms[0] else "n/a"] for why, ms in
 209 | +            sorted(g.items(), key=lambda kv: -len(kv[1]))]
 210 | +
 211 | +
 212 | +def flags_rows(per_moment, describe, example_note=None):
 213 | +    """per_moment: {mid: [flag, ...]} -> rows [moments carrying it, of them it ALONE keeps out, flag, example]."""
 214 | +    carry, alone = collections.Counter(), collections.Counter()
 215 | +    ex = {}
 216 | +    for mid, fl in per_moment.items():
 217 | +        for f in fl:
 218 | +            carry[f] += 1
 219 | +            ex.setdefault(f, mid)
 220 | +            if len(set(fl)) == 1:
 221 | +                alone[f] += 1
 222 | +                ex[f] = ex[f] if len(set(per_moment[ex[f]])) == 1 else mid      # prefer an example it alone rejects
 223 | +    rows = []
 224 | +    for f, n in carry.most_common():
 225 | +        note = (example_note(ex[f], f) if example_note else "")
 226 | +        rows.append([n, alone[f], f"`{f}`: {describe(f)}", f'"{q(tx(ex[f]))}"' + (f" ({note})" if note else "")])
 227 | +    return rows
 228 | +
 229 | +
 230 | +print(f"Build `{os.path.basename(D)}`: code {pk.get('code')}, render clock {pk.get('now')}.")
 231 | +ar = inp.get("adapter_report") or {}
 232 | +print(f"Adapter (pp-ingest, before the ledger rows): excluded {json.dumps(ar.get('excluded'))}.")
 233 | +
 234 | +# ---- stage 0: ledger rows -> moments
 235 | +s0 = []
 236 | +for why, n in (rep.get("no_word_record_why") or {}).items():
 237 | +    s0 += [(f"SUPPLY: no word record yet ({why})", None)] * int(n)
 238 | +s0 += [("SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row)", None)] * \
 239 | +    int(rep.get("window_waiting") or 0)
 240 | +s0 += [("its window record failed a check", None)] * int(rep.get("window_failed") or 0)
 241 | +na = rep.get("not_anchored") or {}
 242 | +ws_rows = {}
 243 | +for mid, why in na.items():
 244 | +    m = re.search(r"\((\d+) word\(s\) before (?:it|the anchored text),? and (\d+) after", why)
 245 | +    if m:
 246 | +        ws_rows[mid] = (int(m.group(1)), int(m.group(2)), why)
 247 | +    s0.append(("does not re-anchor: " + re.sub(r"\d+(\.\d+)?", "N", re.sub(r"searched [\d.]+-[\d.]+ s",
 248 | +                                                                       "searched around the row's time", why)), mid))
 249 | +s0 += [("duplicate: the same speech as a kept moment (time overlap in the same video)", mid)
 250 | +       for mid in (rep.get("duplicates_of") or {})]
 251 | +s0 += [(f"malformed: {why}", mid) for mid, why in (rep.get("malformed") or {}).items()]
 252 | +s0 += [("its video's rows name two channels", None) for _ in (rep.get("channel_conflict") or {})]
 253 | +emit(f"Stage 0: {rep.get('rows')} ledger rows -> {len(moments)} moments ({len(s0)} not moments)", grouped(s0))
 254 | +if ws_rows:
 255 | +    print("\nThe rows that are not whole sentences of the word record, exactly (words of the edge sentences outside "
 256 | +          "the anchored text, before / after, and why each stays out):")
 257 | +    for mid, (l, r, why) in sorted(ws_rows.items(), key=lambda kv: kv[1][0] + kv[1][1]):
 258 | +        print(f"- {l} before / {r} after: \"{q(texts.get(mid), 90)}\" (why: {q(why, 140)})")
 259 | +
 260 | +# ---- stage 1: moments -> usable
 261 | +DESC = {"opener": "opens on a pronoun or reply word that needs what came before (stand_alone.opener)",
 262 | +        "no_bitcoin": "does not name Bitcoin: regex `\\b(bitcoins?|btcs?)\\b` (T11, the old story selector's subject "
 263 | +                      "screen; 'Bitcoiners', 'sats', 'Satoshi' do not count)",
 264 | +        "too_many_sentences": "more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3)",
 265 | +        "layout_ineligible": "the channel has a burned-in chyron (registry has_chyron, DEC-12d)",
 266 | +        "not_statement": "ends on a question",
 267 | +        "hook_lead": "hook only: transcript gap before the first word < 80 ms",
 268 | +        "start_case": "starts lower-case", "fragment": "not a sentence start / end", "too_short": "< 5 words",
 269 | +        "no_content": "interjections only", "unpunctuated": "boundary in an unpunctuated stretch",
 270 | +        "duration": "no word timestamps", "not_sentence_ready": "no sentence-ready word record"}
 271 | +un = pk.get("unusable") or {}
 272 | +clipflags, other = {}, []
 273 | +for mid, why in un.items():
 274 | +    m = re.match(r"not eligible on screen: (.*)$", why)
 275 | +    if m:
 276 | +        roles = dict(p.split(": ", 1) for p in m.group(1).split("; ") if ": " in p)
 277 | +        clipflags[mid] = [f.strip() for f in roles.get("clip", "").split(",") if f.strip()]
 278 | +    else:
 279 | +        other.append((re.sub(r"^[\d.]+ s:", "N s:", why), mid))
 280 | +print(f"\n**Stage 1: {len(moments)} moments -> {pk.get('usable')} usable** (package.usable; {len(un)} lost)")
 281 | +print("\nA moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the "
 282 | +      "binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).")
 283 | +emit(f"Stage 1a: not eligible on screen ({len(clipflags)} moments)",
 284 | +     flags_rows(clipflags, lambda f: DESC.get(f, f)), head=("moments", "alone", "exact reason (clip role)",
 285 | +                                                             "one example"))
 286 | +if other:
 287 | +    emit(f"Stage 1b: the other usable() reasons ({len(other)} moments)", grouped(other))
 288 | +
 289 | +# ---- stage 2: usable -> cleared step A
 290 | +pre = pk.get("prescreen") or {}
 291 | +failed = pre.get("failed") or {}
 292 | +sa_by = {}
 293 | +for k, v in sa.items():
 294 | +    if isinstance(v, dict):
 295 | +        sa_by[k.split(":")[0]] = v
 296 | +
 297 | +
 298 | +def a_note(mid, rule):
 299 | +    a = next((v for lb, v in sa_by.items() if mid.startswith(lb)), None)
 300 | +    if not a:
 301 | +        return ""
 302 | +    if rule == "REFERENT_OUTSIDE":
 303 | +        rs = [r for r in a.get("referents") or [] if isinstance(r, dict) and r.get("inside") is not True]
 304 | +        return "; ".join(f"'{r.get('word')}' -> '{q(r.get('refers_to'), 50)}', changes the assertion: "
 305 | +                         f"{r.get('changes_assertion')}" for r in rs[:2])
 306 | +    if rule == "NOT_OWN_SINCERE":
 307 | +        return f"view: {a.get('view')}"
 308 | +    if rule == "STALE_TIME":
 309 | +        return f"time_ok: {a.get('time_ok')}"
 310 | +    if rule == "CONDITION_OUTSIDE":
 311 | +        return "; ".join(f"'{q((c or {}).get('text'), 60)}'" for c in a.get("conditions") or [])
 312 | +    if rule == "SPEAKER_CHANGE":
 313 | +        return f"speaker_changes_inside: {a.get('speaker_changes_inside')}"
 314 | +    if rule == "UNCERTAIN":
 315 | +        return f"certainty: {a.get('certainty')}"
 316 | +    if rule == "RETRACTION":
 317 | +        return f"retraction: {q(a.get('retraction'), 60)}"
 318 | +    return ""
 319 | +
 320 | +
 321 | +SDESC = {"REFERENT_OUTSIDE": "a word refers to something outside the clip AND resolving it could change the assertion "
 322 | +                             "(anything but an explicit 'no' fails, L-m)",
 323 | +         "NOT_OWN_SINCERE": "not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...)",
 324 | +         "STALE_TIME": "time words stale on the show date (L-v 3)", "CONDITION_OUTSIDE": "a condition outside the clip",
 325 | +         "SPEAKER_CHANGE": "a speaker change inside", "RETRACTION": "retracted or corrected later",
 326 | +         "UNCERTAIN": "the judge is not certain", "CONTEXT_UNAVAILABLE": "no source context to judge"}
 327 | +print(f"\n**Stage 2: {pk.get('usable')} usable -> {pre.get('cleared')} cleared step A** (L-s on the moment's own "
 328 | +      f"context; {pre.get('screened')} screened, {len(failed)} failed)")
 329 | +emit(f"Stage 2: step A rules ({len(failed)} moments)",
 330 | +     flags_rows(failed, lambda f: SDESC.get(f, f), a_note), head=("moments", "alone", "exact reason", "one example"))
 331 | +
 332 | +# ---- stage 3: cleared -> L-v 2 + CUTTABLE (edges recomputed from the recorded scribe replies, offline)
 333 | +sp = pre.get("second_pass") or {}
 334 | +lost3 = [mid for mid, v in sp.items() if v != "PASS"]
 335 | +detail = {}
 336 | +try:
 337 | +    import providers as P
 338 | +    import transcript_truth as TT
 339 | +    rt = P.Router(record_dir=REPLIES, replay=True)
 340 | +    for mid in lost3:
 341 | +        m = by[mid]
 342 | +        try:
 343 | +            t = TT.verify_segment(rt, m["video_id"], float(m["start"]), float(m["end"]), m["text"], LV2)
 344 | +            e = t.get("edges") or {}
 345 | +            if not t.get("ok"):
 346 | +                bits = []
 347 | +                if not t.get("transcript_ok"):
 348 | +                    bits.append(f"the two recognisers disagree on {json.dumps(t.get('disagree'))[:160]}")
 349 | +                if t["speakers"].get("turn_change_inside") is not False:
 350 | +                    bits.append(f"speakers measured inside: {t['speakers'].get('labels')}")
 351 | +                detail[mid] = ("L-v 2 FAIL", "; ".join(bits))
 352 | +            else:
 353 | +                bad = [f"{k.upper()}: {e[k].get('why')}" for k in ("in", "out") if not (e.get(k) or {}).get("ok")]
 354 | +                detail[mid] = ("not CUTTABLE: " + " + ".join(b.split(":")[0] for b in bad) + " edge", "; ".join(bad))
 355 | +        except Exception as ex:                              # noqa: BLE001
 356 | +            detail[mid] = (sp[mid], f"(edge detail not recomputed offline: {type(ex).__name__}: {str(ex)[:120]})")
 357 | +except Exception as ex:                                      # noqa: BLE001
 358 | +    print(f"(stage-3 detail not recomputed: {type(ex).__name__}: {ex})")
 359 | +rows3 = []
 360 | +g3 = collections.OrderedDict()
 361 | +for mid in lost3:
 362 | +    k = detail.get(mid, (sp[mid], ""))[0]
 363 | +    g3.setdefault(k, []).append(mid)
 364 | +for k, ms in sorted(g3.items(), key=lambda kv: -len(kv[1])):
 365 | +    rows3.append([len(ms), k, f'"{q(tx(ms[0]))}" ({q(detail.get(ms[0], ("", ""))[1], 200)})'])
 366 | +emit(f"Stage 3: {pre.get('cleared')} cleared -> {pre.get('cuttable')} pass L-v 2 + CUTTABLE ({len(lost3)} lost)", rows3)
 367 | +if len(lost3) > 1:
 368 | +    print("\nEvery stage-3 loss, exactly:")
 369 | +    for mid in lost3:
 370 | +        k, d = detail.get(mid, (sp[mid], ""))
 371 | +        print(f"- {by[mid].get('channel_name')}: {k}: {q(d, 260)}")
 372 | +
 373 | +# ---- stage 4: cuttable -> can open
 374 | +ho = pre.get("hook_onset") or {}
 375 | +lost4 = [(v, mid) for mid, v in ho.items() if v != "PASS"]
 376 | +emit(f"Stage 4: {pre.get('cuttable')} cuttable -> {sum(v == 'PASS' for v in ho.values())} can open a medley (G17a; "
 377 | +     f"the others stay in play as non-hook clips)", grouped(lost4) or [[0, "-", "-"]])
 378 | +
 379 | +# ---- stage 5: -> angle -> line-ups
 380 | +print(f"\n**Stage 5: the angle step and the line-ups.** why_none: {pk.get('why_none')!r}; angles: "
 381 | +      f"{len(pk.get('angles') or [])} from {pk.get('angle_backend')}")
 382 | +cl = [mid for mid, v in sp.items() if v == "PASS"]
 383 | +print("\nThe moments offered to the angle step:")
 384 | +for mid in cl:
 385 | +    m = by.get(mid, {})
 386 | +    print(f"- {m.get('channel_name')} ({m.get('video_id')}), {m.get('duration_s')} s, can open: "
 387 | +          f"{ho.get(mid) == 'PASS'}: \"{q(m.get('text'), 150)}\"")
 388 | +print(f"\nTogether {round(sum(float(by[m]['duration_s']) for m in cl if m in by), 2)} s from "
 389 | +      f"{len({by[m]['channel_id'] for m in cl if m in by})} channels.")
 390 | +for a in pk.get("angles") or []:
 391 | +    print(f"- angle: \"{q(a.get('angle'), 200)}\" moments {len(a.get('moments') or [])}")
 392 | +log = open(os.path.join(D, "package.log")).read().splitlines()
 393 | +k = next((i for i, l in enumerate(log) if re.search(r"angles? from|no readable angles|readable angle", l)), None)
 394 | +if k is not None:
 395 | +    print("\nThe build's own log from the angle step on:")
 396 | +    print("```")
 397 | +    for l in log[k:]:
 398 | +        print(l.rstrip()[:240])
 399 | +    print("```")
 400 | diff --git a/tests/package/funnel_pre_edge.py b/tests/package/funnel_pre_edge.py
 401 | new file mode 100644
 402 | index 00000000..07418222
 403 | --- /dev/null
 404 | +++ b/tests/package/funnel_pre_edge.py
 405 | @@ -0,0 +1,35 @@
 406 | +"""For each stage-3 'no word before it' loss in a build: what is in the audio before the clip? Offline (recorded scribe
 407 | +replies, replay=True) + the cached L-v 2 WAV, CPU only. usage: tests/package/funnel_pre_edge.py <build dir>"""
 408 | +import json, os, sys, wave
 409 | +import numpy as np
 410 | +REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 411 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 412 | +import providers as P, transcript_truth as TT
 413 | +D = sys.argv[1]
 414 | +LV2 = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad/lv2"
 415 | +inp = json.load(open(os.path.join(D, "inputs.json"))); pk = json.load(open(os.path.join(D, "package.json")))
 416 | +by = {m["moment_id"]: m for m in inp["moments"]}
 417 | +rt = P.Router(record_dir=os.path.join(REPO, "tests/package/fixtures/replies"), replay=True)
 418 | +for mid, v in (pk["prescreen"].get("second_pass") or {}).items():
 419 | +    if v == "PASS":
 420 | +        continue
 421 | +    m = by[mid]; s, e = float(m["start"]), float(m["end"])
 422 | +    wav, a = TT.audio_window(m["video_id"], s, e, LV2)
 423 | +    sec, _ = TT.second_pass(rt, wav)
 424 | +    edg = TT.edges(sec, a, s, e, m["text"])
 425 | +    w = wave.open(wav); n = w.getnframes(); sr = w.getframerate()
 426 | +    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
 427 | +    off = s - a
 428 | +    fr = int(0.05 * sr)
 429 | +    def db(seg):
 430 | +        r = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
 431 | +        return -120.0 if r <= 0 else 20 * np.log10(r)
 432 | +    pre = [round(db(x[i:i + fr]), 1) for i in range(0, int(off * sr), fr)]
 433 | +    words = [(round(float(w_["start"]), 2), w_.get("text"), w_.get("speaker")) for w_ in sec.get("words") or []
 434 | +             if w_.get("start") is not None][:6]
 435 | +    print(f"\n{m['channel_name']} {m['video_id']} clip {s:.2f}-{e:.2f}, window from {a:.2f} (pad {off:.2f} s); "
 436 | +          f"IN: {edg['in'].get('why')} | OUT: {edg['out'].get('why')}")
 437 | +    print("  recogniser's first words (s into the window, text, speaker):", words)
 438 | +    print("  pre-clip RMS dBFS per 50 ms:", pre)
 439 | +    print("  clip's first 0.5 s RMS dBFS per 50 ms:", [round(db(x[i:i + fr]), 1) for i in range(int(off * sr), int((off + 0.5) * sr), fr)])
 440 | +    print("  primary (store) text starts:", repr(m["text"][:70]))
 441 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 442 | index b99d2ddc..75e4993b 100644
 443 | --- a/tests/package/test_ledger_build.py
 444 | +++ b/tests/package/test_ledger_build.py
 445 | @@ -46,31 +46,64 @@ class TestReanchor(unittest.TestCase):
 446 |          self.assertEqual(info["snapped_words"], [0, 0])
 447 |          self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 448 |  
 449 | -    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 450 | -        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
 451 | +    def test_a_caption_text_snaps_outward_to_the_records_whole_sentences(self):
 452 | +        """Ruling 32 (02:45 ET Nov 13): any number of the speaker's own words is added, within 20 s, no speaker
 453 | +        change; the added words are recorded."""
 454 | +        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short
 455 |          self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
 456 | -        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
 457 | -        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
 458 | -        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
 459 | -        self.assertIsNone(sp)
 460 | -        self.assertIn("not whole sentences", why)
 461 | -
 462 | -    def test_a_snap_never_adds_a_negation_or_a_number(self):
 463 | -        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
 464 | -        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
 465 | -        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
 466 | -                           ("Bitcoin started as a quiet experiment.", "2009")):
 467 | -            sp, why = LB.reanchor(row(text), self.src)
 468 | -            self.assertIsNone(sp, text)
 469 | -            self.assertIn(word, why)
 470 | -
 471 | -    def test_a_snap_never_adds_a_near_negation(self):
 472 | -        """qwen C3: 'Hardly anyone can stop Bitcoin' flips 'anyone can stop Bitcoin'."""
 473 | -        for word in ("Hardly", "Scarcely", "Barely", "Rarely", "Seldom"):
 474 | +        self.assertEqual(info["added"], {"before": "Bitcoin", "after": ""})
 475 | +        sp, info = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused before 32
 476 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [4, 0]))
 477 | +        self.assertEqual(info["added"]["before"], "That is the whole")
 478 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 479 | +
 480 | +    def test_a_snap_adds_the_speakers_own_negation_or_number_and_records_it(self):
 481 | +        """Ruling 32 retires SNAP_GUARD (audit 2315 C1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin'
 482 | +        restores what the speaker said. Step A, the exclusion verdict and L-v 2 judge the snapped span; the added
 483 | +        words are on the record."""
 484 | +        for text, before in (("can stop Bitcoin from settling a payment.", "Nobody"),
 485 | +                             ("Bitcoin started as a quiet experiment.", "In 2009")):
 486 | +            sp, info = LB.reanchor(row(text), self.src)
 487 | +            self.assertIsNotNone(sp, text)
 488 | +            self.assertEqual(info["added"]["before"], before)
 489 | +        for word in ("Hardly", "Don\u2019t"):
 490 |              src = source([f"{word} anyone can stop Bitcoin from settling a payment.", "That is the plan."])
 491 | -            sp, why = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 492 | -            self.assertIsNone(sp, word)
 493 | -            self.assertIn(word, why)
 494 | +            sp, info = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 495 | +            self.assertEqual(info["added"]["before"], word)
 496 | +
 497 | +    def test_a_snap_longer_than_20_s_stays_out(self):
 498 | +        long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."             # 75 words, 0.3 s each
 499 | +        src = source([long_, "That is the plan."])
 500 | +        a, b = src.sentences[0]
 501 | +        self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], LB.SNAP_MAX_S)
 502 | +        sp, why = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 503 | +        self.assertIsNone(sp)
 504 | +        self.assertIn("> 20 s (ruling 32", why)
 505 | +        sp, info = LB.reanchor(row(long_), src)                       # whole sentences: no snap, usable() measures it
 506 | +        self.assertEqual(info["snapped_words"], [0, 0])
 507 | +
 508 | +    def test_a_caption_speaker_marker_inside_the_snapped_span_keeps_the_row_out(self):
 509 | +        a = self.src.tokens[self.src.sentences[1][0]]["start"]
 510 | +        b = self.src.tokens[self.src.sentences[1][1]]["end"]
 511 | +        cap = lambda *ts: type("Cap", (), {"tokens": [{"word": "&gt;&gt;", "start": x} for x in ts]})()
 512 | +        text = "can stop Bitcoin from settling a payment."
 513 | +        sp, why = LB.reanchor(row(text), self.src, cap=cap((a + b) / 2))
 514 | +        self.assertIsNone(sp)
 515 | +        self.assertIn("caption speaker marker", why)
 516 | +        self.assertIsNone(LB.reanchor(row(text), self.src, cap=type("C", (), {"tokens": [
 517 | +            {"word": ">>", "start": (a + b) / 2}]})())[0])                                # the raw form too
 518 | +        for c in (cap(a + 0.5), cap(b - 0.5), None, cap()):        # at an edge, no record, no marker: L-v 2 decides
 519 | +            self.assertIsNotNone(LB.reanchor(row(text), self.src, cap=c)[0])
 520 | +        self.assertIsNotNone(LB.reanchor(row(SENTS[1]), self.src, cap=cap((a + b) / 2))[0])   # no snap: no read
 521 | +
 522 | +    def test_a_snapped_moment_counts_its_own_price_prediction(self):
 523 | +        info = {"snapped_words": [4, 0]}
 524 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030. It is coming.", info, []),
 525 | +                         ["price_prediction"])
 526 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", {"snapped_words": [0, 0]}, []), [])
 527 | +        self.assertEqual(LB.snap_risk("Bitcoin is at 70,000 today.", info, ["time_sensitive"]), ["time_sensitive"])
 528 | +        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", info, ["price_prediction"]),
 529 | +                         ["price_prediction"])
 530 |  
 531 |      def test_the_hit_is_measured_against_the_rows_own_caption_times(self):
 532 |          """glm C3 P1-3: a phrase said twice inside the search window would anchor on the earliest longest match; the
 533 | @@ -82,18 +115,10 @@ class TestReanchor(unittest.TestCase):
 534 |          self.assertEqual(LB.reanchor(row(SENTS[1]), self.src)[1]["offset_s"],      # glm C4 P2-8: said, not absent
 535 |                           "unmeasured: the row has no readable caption times")
 536 |  
 537 | -    def test_a_typographic_apostrophe_does_not_hide_a_negation(self):
 538 | -        """glm C2 N-3: 'Don\u2019t' (U+2019) is the negation 'Don't' to the guard."""
 539 | -        for apostrophe in ("\u2019", "'"):
 540 | -            src = source([f"Don{apostrophe}t sell your Bitcoin to anyone today.", "That is the plan."])
 541 | -            sp, why = LB.reanchor(row("sell your Bitcoin to anyone today."), src)
 542 | -            self.assertIsNone(sp, apostrophe)
 543 | -            self.assertIn("negation", why)
 544 | -
 545 | -    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 546 | -        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 547 | -        self.assertIsNone(sp)
 548 | -        self.assertIn("not whole sentences", why)
 549 | +    def test_text_cut_at_both_edges_snaps_and_text_that_is_not_there_is_dropped_with_why(self):
 550 | +        sp, info = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 551 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((1, 2), [4, 5]))
 552 | +        self.assertEqual(info["added"], {"before": "Nobody can stop Bitcoin", "after": "and it works every day."})
 553 |          sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 554 |          self.assertIsNone(sp)
 555 |          self.assertIn("does not anchor", why)
 556 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
pipeline/ledger_build.py turns the moment LEDGER's rows into moments:
- a row is a moment the miner found in a caption record: its text, its caption times, its risk flags, its scores;
- the row's TEXT is located (re-anchored) in a sentence-ready, word-timed WORD record of the same video;
- the moment becomes that record's own whole sentences, verbatim.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 32 (02:45 ET Nov 13, restated at 03:12: "32 stands as written; the 20 s limit decides the
long snaps"): "a moment whose anchored text is not whole sentences is SNAPPED OUTWARD to the whole sentences of the
word record instead of dropped, when the snapped span is still inside the clip length limits and the same single
speaker. ... Snapping outward adds the speaker's own words, so it cannot change meaning by omission; step A / L-s
then judge the snapped span as usual. Rows where the text does not anchor at all stay out."
- Before: up to SNAP_WORDS = 3 words could be added at either edge, and SNAP_GUARD refused a snap that ADDED a negation
  or a digit (audit 2315 C1: "it could flip or add a claim the ledger's scores and risks never saw").
- The 02:37 build lost 12 rows this way (0/6, 0/9, 9/0, 0/11, 0/11, 2/12, 16/0, 0/32, 0/39, 0/47, 0/47, 0/57 words
  before / after).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. This change is the orchestrator's own ruling;
  check that it does exactly that and no more;
- clips are verbatim whole sentences of a word-timed record;
- at most 20 s per clip (L-u, package.SEG_MAX_S);
- at most one price prediction per video (L-u), counted from the moment's risk flags.

What judges a snapped span downstream (unchanged, outside this diff):
- package.usable(): the 20 s limit, and time-sensitive words in the moment's text;
- step A (L-s, context_integrity): the moment's own view, its referents and conditions, a speaker change inside;
- the exclusion verdict (moments.exclusion_verdict, a hard gate in every pin): it screens the MOMENT TEXT for every
  L-u hard risk (accusation, partner_attack, imperative, guaranteed_return, single_source_breaking, ad_read,
  third_party_media) and for about-Bitcoin;
- L-v 2 (transcript_truth.verify_segment): every number and negation both ways against an independent recogniser, and
  exactly one speaker measured inside.

The change:
1. pipeline/ledger_build.py:
   - SNAP_WORDS, SNAP_GUARD and APOSTROPHES are removed. SNAP_MAX_S = 20.0.
   - reanchor(row, src, cap=None): a hit that is not whole sentences snaps outward to sentences k0..k1. It stays out
     when:
     (a) a word time at the snapped span's edges is missing (its length is not measured);
     (b) the snapped span runs more than 20 s;
     (c) marker_inside(cap, a, b) finds a caption speaker marker (">>" or "&gt;&gt;") on a caption token whose time is
         more than MARKER_EDGE_S = 1.0 s inside the span. cap is the caption record the row was mined from (default:
         the window Source's context_source).
     A marker within 1.0 s of an edge, no marker, or no caption record is not a measurement at this stage; L-v 2
     decides on the audio. The added words are recorded in info["added"].
   - snap_risk(text, info, risk): for a SNAPPED moment, "price_prediction" is added to its risk when its text holds a
     future price (vo_fidelity.price_mentions), because the miner flagged only the row's text.
   - build_inputs: the full-video path now looks up the row's caption record (caption_source, once per sha) and passes
     it to reanchor. The window path already attached it.
   - The docstrings are updated, including a stale "one window per video" line (it is one per moment since audit
     0208).
2. tests/package/test_ledger_build.py:
   - the old SNAP_GUARD tests now assert that the snap restores the speaker's own words and records them;
   - new: the 20 s limit; a caption marker inside the span vs at an edge vs none vs no record; snap_risk.
3. tests/package/funnel.py and tests/package/funnel_pre_edge.py: the offline funnel tools behind the 02:45 FUNNEL
   TABLE.
   - They read a build record.
   - They recompute the edges from RECORDED recogniser replies (Router replay=True: a miss raises and nothing is
     fetched).
   - Stage 0 groups reasons with their numbers taken out.
   - No pipeline code depends on them.

Check in particular:
- whether removing SNAP_GUARD leaves any risk that NO downstream gate judges, for words the ledger never saw;
- the edge times a / b and the marker window;
- that a row whose text does not anchor still stays out;
- that a snapped moment's text, start, end and words come from the word record;
- that the dedup and the window path are unchanged;
- that snap_risk cannot remove a flag.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

