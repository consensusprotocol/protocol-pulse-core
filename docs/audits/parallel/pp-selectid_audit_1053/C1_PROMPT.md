# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1053
# Branch: pp-selectid
# Generated: 2026-11-13 10:54 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1053/C1_STEP.diff (864 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index a3bc8fc..85204a9 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -82,11 +82,18 @@ SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE de
   6 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   7 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   8 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
   9 | -TRIM_SCORER_PENDING = True         # ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the
  10 | -                                   # pin stage may not use) must affirm every trimmed segment. RULING 49 (07:02 Nov 13):
  11 | -                                   # YES, a trimmed clip is sealed with that verdict PENDING AT THE RENDER (stage_validate
  12 | -                                   # runs before any render; a refusal there costs no GPU), stated in the sealed row and
  13 | -                                   # per clip in the pin (scorer_pending: true). False: the render's check with no scorer
  14 | +# Ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the pin stage may not use itself) must
  15 | +# affirm every trimmed segment. RULING 49 (07:02 Nov 13) let a trimmed clip be sealed with that verdict pending at the
  16 | +# render, and said "If you can call the same scorer ... do that instead". RULING 56 (09:59): the integrator's pin-stage
  17 | +# service asks that same scorer; "seal only what it affirms". The pending form is retired: a trimmed clip is sealed
  18 | +# only with the scorer's affirmation of its trimmed text, and package_pin refuses scorer_pending.
  19 | +SCORER_VERDICTS = "/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json"   # ruling 56: the
  20 | +SCORER_EVENT = "Pinned: bitcoin"   # integrator's verdicts (read only), asked with validate's event for a moments pin
  21 | +RENDER_SCORER_CODE = tuple(f"/home/ultron/protocol_pulse/pipeline/{f}" for f in ("stand_alone.py", "story_semantics.py"))
  22 | +                                   # ^ read only: the render's scorer code; the integrator's scorer_sha is a sha256 over
  23 | +                                   # these two files in this order, so a verdict under other code is not the render's now
  24 | +SCORER_CANDIDATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "audits",
  25 | +                                 "parallel", "pp-selectid_SCORER_CANDIDATES.json")   # ruling 56: what I ask it next
  26 |  TRIMMED_PER_LINEUP_MAX = 1         # ruling 49 (b): at most ONE trimmed clip per line-up until the first trimmed clip has
  27 |                                     # been affirmed at validate once (the integrator says when): one refusal cannot sink a
  28 |                                     # line-up twice. package_pin.TRIMMED_PER_PIN_MAX holds the pin to the same number
  29 | @@ -311,10 +318,10 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  30 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  31 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  32 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  33 | -                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"],
  34 | -                            "scorer_pending": bool(TRIM_SCORER_PENDING)}   # ruling 49 (a): the clip scorer's verdict
  35 | -                           if m.get("trimmed_leading") else {})}   # on the trimmed text is pending at the render
  36 | -                                                                   # (strict: False, which the pin refuses)
  37 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  38 | +                           if m.get("trimmed_leading") else {}),
  39 | +                        **({"scorer_verdict": verdict_of(m)}  # ruling 56: "seal only what it affirms" (the pin
  40 | +                           if (verdict_of(m) or {}).get("affirmed") is True else {})}   # refuses any other)
  41 |                         for lb, m in zip(labels(len(segs)), segs)],
  42 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  43 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  44 | @@ -640,30 +647,30 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
  45 |  def stand_alone_check(segs):
  46 |      """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) on one line-up, at the pin stage
  47 |      (the integrator held pin d2657bbe on it, 03:00 ET Nov 13): the hook, then the clips in play order (clip_01, ...), the
  48 | -    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and NO clip scorer.
  49 | -    The render's scorer is a local model on GPU0, which this stage may not use, so a clip that opens on a conjunction or
  50 | -    a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
  51 | -    check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
  52 | -    scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
  53 | -    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1).
  54 | +    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and as the clip
  55 | +    scorer the verdicts the integrator's pin-stage service gave on each segment's CURRENT text (ruling 56: the render's
  56 | +    own scorer, on GPU0, which this stage may not use itself). A clip that opens on a conjunction or a reply fragment,
  57 | +    and a trimmed segment (its lock's marker, as the render sets it), pass only with an affirming verdict and fail
  58 | +    closed without one, as check_edl does. check_edl's verdict reads only each segment's text, the subject and rate
  59 | +    (channel and duration feed only the scorer's passages, which rate answers from the sealed verdicts; the labels
  60 | +    come from the order). The subject is fixed because package_pin.to_pin labels every moments pin 'bitcoin' (audit
  61 | +    0310 C1, glm P1-1 / qwen P1-1).
  62 |      RULING 34 (the render's side merged at 55315124): the topic test is the miner's about-Bitcoin screen that every
  63 |      moments pin seals (eligibility.BTC_SCREEN, moments_package.btc_screen), and the MEDLEY must name Bitcoin in at
  64 |      least one segment (out["medley_names_bitcoin"], part of out["ok"]): check_edl(..., screen=...), as the render."""
  65 |      import stand_alone as SA
  66 |      def seg(m, extra):
  67 | -        lock = {} if TRIM_SCORER_PENDING or not m.get("trimmed_leading") else \
  68 | +        lock = {} if not m.get("trimmed_leading") else \
  69 |              {"selection_lock": {"trimmed_leading": {"word": m["trimmed_leading"]}}}    # the render's own marker
  70 |          return dict(extra, text=m["text"], channel=m.get("channel_name"), **lock)
  71 | -    edl = {"hook": seg(segs[0], {}),
  72 | +    by_label = dict(zip(labels(len(segs)), segs))
  73 | +
  74 | +    def rate(passages):                      # ruling 56: the render's own clip scorer, as its verdicts on each
  75 | +        return {p["pid"]: (v["score"], v["reason"], v["fault"]) for p in passages     # segment's current text; a
  76 | +                for v in [verdict_of(by_label.get(p["pid"]))] if v}                     # segment without one fails
  77 | +    edl = {"hook": seg(segs[0], {}),                                                    # closed, as check_edl does
  78 |             "clips": [seg(m, {"index": i, "duration": m.get("duration_s")}) for i, m in enumerate(segs[1:], 1)]}
  79 | -    r = SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  80 | -    r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs)
  81 | -                           if m.get("trimmed_leading") and TRIM_SCORER_PENDING]            # ruling 33 (b), item 42
  82 | -    for row in r["rows"]:              # the sealed row STATES the divergence, not only the labels (audit 0530 C2, glm)
  83 | -        if row["segment"] in r["scorer_pending"]:
  84 | -            row["opener"]["why"] += ("; the clip scorer's verdict on the trimmed text is PENDING AT THE RENDER (GPU0; "
  85 | -                                     "ruling 33 part 2)")
  86 | -    return r
  87 | +    return SA.check_edl(edl, rate=rate, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  88 |  
  89 |  
  90 |  def ad_read_out(ms, sources):
  91 | @@ -693,7 +700,8 @@ def trim_variant(m, sources):
  92 |      place under the render's STAND_ALONE as trimmed (no_role_on_screen and no_topic both None on the trimmed text).
  93 |      Then it is judged like any moment: step A on the trimmed span (ruling 33 c), L-v 2 with the trimmed word heard right
  94 |      before the clip (transcript_truth.edges), and the acoustic onset rule on the trimmed cut (ruling 33 a, build()).
  95 | -    The clip scorer's verdict (ruling 33 b) is the render's, on GPU0: pending at the render (stand_alone_check). -> the
  96 | +    The clip scorer's verdict on the trimmed text (ruling 33 b) is the render's own scorer's, given at the pin stage
  97 | +    by the integrator's service (ruling 56): build() keeps the variant only with its affirmation (trim_refused). -> the
  98 |      variant, or None."""
  99 |      import canon
 100 |      try:
 101 | @@ -833,6 +841,134 @@ def reposted_once(ms, sources):
 102 |      return out, dup
 103 |  
 104 |  
 105 | +def text_sha(text):
 106 | +    """The sha256 of a text's UTF-8 bytes: the integrator's text_sha256 (ruling 56)."""
 107 | +    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
 108 | +
 109 | +
 110 | +def render_scorer_sha(paths=RENDER_SCORER_CODE):
 111 | +    """RULING 56: the integrator's scorer_sha recomputed from the render's scorer code as it is NOW (read only): a
 112 | +    sha256 over the files' bytes, in order. None when one cannot be read (then no verdict is used)."""
 113 | +    h = hashlib.sha256()
 114 | +    try:
 115 | +        for p in paths:
 116 | +            with open(p, "rb") as f:
 117 | +                h.update(f.read())
 118 | +    except OSError:
 119 | +        return None
 120 | +    return h.hexdigest()
 121 | +
 122 | +
 123 | +def scorer_verdicts(path, code_sha):
 124 | +    """RULING 56: the integrator's pin-stage verdicts of the render's own clip scorer (read only). -> ({pid: verdict},
 125 | +    the record of the read). Fail closed, nothing used: a missing, unreadable or malformed file; another event than
 126 | +    SCORER_EVENT; a scorer_sha other than code_sha (the render's scorer code now, render_scorer_sha); another threshold
 127 | +    than stand_alone.CLIP_MIN_SCORE. A verdict without a numeric score, with an error, or whose "affirmed" disagrees with
 128 | +    the render's own rule (stand_alone.opener: score >= threshold and fault not starts_mid_thought) is no verdict."""
 129 | +    import stand_alone as SA
 130 | +    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
 131 | +    try:
 132 | +        with open(path) as f:
 133 | +            d = json.load(f)
 134 | +        sc, vs = d["scorer"], d["verdicts"]
 135 | +        why = ("another event" if sc.get("event") != SCORER_EVENT else
 136 | +               "the render's scorer code could not be read" if not code_sha else
 137 | +               "a scorer_sha that is not the render's scorer code now" if sc.get("scorer_sha") != code_sha else
 138 | +               "another threshold" if not num(sc.get("threshold")) or sc["threshold"] != SA.CLIP_MIN_SCORE else
 139 | +               "no verdicts" if not isinstance(vs, dict) else None)
 140 | +    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
 141 | +        return {}, {"read": False, "why": f"{type(e).__name__}: {str(e)[:160]}"}
 142 | +    if why:
 143 | +        return {}, {"read": False, "why": why, "event": sc.get("event"), "scorer_sha": sc.get("scorer_sha"),
 144 | +                    "render_scorer_sha": code_sha, "threshold": sc.get("threshold")}
 145 | +    out, disagree = {}, []
 146 | +    for pid, v in vs.items():
 147 | +        if not (isinstance(v, dict) and isinstance(v.get("text_sha256"), str) and num(v.get("score")) and
 148 | +                not v.get("error")):
 149 | +            continue
 150 | +        rule = v["score"] >= SA.CLIP_MIN_SCORE and v.get("fault") != "starts_mid_thought"
 151 | +        if (v.get("affirmed") is True) != rule:
 152 | +            disagree.append(pid)
 153 | +            continue
 154 | +        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"), "affirmed": rule,
 155 | +                         "text_sha256": v["text_sha256"], "prompt_sha256": v.get("prompt_sha256"),
 156 | +                         "model": sc.get("model"), "event": sc["event"], "scorer_sha": sc["scorer_sha"],
 157 | +                         "threshold": sc["threshold"], "rated_at": d.get("rated_at")}
 158 | +    return out, {"read": True, "rated_at": d.get("rated_at"), "build": d.get("build"),
 159 | +                 "candidates_generated_at": d.get("candidates_generated_at"), "model": sc.get("model"),
 160 | +                 "event": sc["event"], "scorer_sha": sc["scorer_sha"], "threshold": sc["threshold"],
 161 | +                 "verdicts": len(out), "affirmed": sum(v["affirmed"] for v in out.values()),
 162 | +                 "disagree_with_the_rule": disagree}
 163 | +
 164 | +
 165 | +def verdict_of(m):
 166 | +    """RULING 56: the clip scorer's verdict attached to a moment when it is for the moment's CURRENT text, else None."""
 167 | +    v = (m or {}).get("scorer_verdict")
 168 | +    return v if isinstance(v, dict) and v.get("text_sha256") == text_sha((m or {}).get("text")) else None
 169 | +
 170 | +
 171 | +def with_verdict(m, index):
 172 | +    """The moment with the scorer's verdict for its id attached when that verdict is for its current text (ruling 56);
 173 | +    any other verdict it carries is dropped (a trimmed variant never inherits its original's)."""
 174 | +    m = {k: x for k, x in m.items() if k != "scorer_verdict"}
 175 | +    v = index.get(m["moment_id"])
 176 | +    return dict(m, scorer_verdict=v) if v and v["text_sha256"] == text_sha(m.get("text")) else m
 177 | +
 178 | +
 179 | +def trim_refused(v):
 180 | +    """RULING 56: why a trimmed variant is left out before any vendor call, else None: no clip-scorer verdict on its
 181 | +    trimmed text, or one that does not affirm it ("seal only what it affirms")."""
 182 | +    s = verdict_of(v)
 183 | +    if s is None:
 184 | +        return (f"{v.get('trimmed_leading')!r} trimmed and no clip-scorer verdict on the trimmed text yet (ruling 56: "
 185 | +                f"sealed only when the scorer affirms it)")
 186 | +    if not s["affirmed"]:
 187 | +        return (f"{v.get('trimmed_leading')!r} trimmed; the clip scorer does not affirm the trimmed text stands alone "
 188 | +                f"({s['score']}, fault {s['fault']})")
 189 | +    return None
 190 | +
 191 | +
 192 | +def write_candidates(path, ms, ctx, build_name):
 193 | +    """RULING 56: the next pass's request in the integrator's contract ({generated_at, build, event_expected,
 194 | +    candidates: [{pid, video_id, channel, duration, text, text_sha256, trimmed_leading}]}), written atomically (.tmp,
 195 | +    then rename), and only when its set of (pid, text_sha256) differs from the file's: a new generated_at starts a
 196 | +    pass, and rated texts are reused there. -> True when written."""
 197 | +    from datetime import datetime, timezone
 198 | +    cands = [{"pid": m["moment_id"], "video_id": m["video_id"], "channel": _name(m, ctx), "duration": m["duration_s"],
 199 | +              "text": m["text"], "text_sha256": text_sha(m["text"]), "trimmed_leading": m.get("trimmed_leading")}
 200 | +             for m in ms]
 201 | +    try:
 202 | +        with open(path) as f:
 203 | +            old = {(c["pid"], c["text_sha256"]) for c in json.load(f)["candidates"]}
 204 | +    except (OSError, ValueError, KeyError, TypeError):
 205 | +        old = None
 206 | +    if old == {(c["pid"], c["text_sha256"]) for c in cands}:
 207 | +        return False
 208 | +    doc = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "build": build_name,
 209 | +           "event_expected": SCORER_EVENT, "candidates": cands}
 210 | +    with open(path + ".tmp", "w") as f:
 211 | +        json.dump(doc, f, indent=1)
 212 | +    os.replace(path + ".tmp", path)
 213 | +    return True
 214 | +
 215 | +
 216 | +def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
 217 | +    """RULING 56, once per build, before any verdict is attached. (1) The integrator's verdicts (scorer_verdicts, fail
 218 | +    closed). (2) The next pass's candidates (write_candidates): every moment the render's STAND_ALONE leaves out as an
 219 | +    opener the clip scorer would have to affirm (no_role_on_screen fires, the topic rule does not: no verdict could
 220 | +    give a moment that fails the topic rule a place), and the trimmed variant of every moment left out (ruling 33 part
 221 | +    2), each with its text exactly as it would be locked. -> {"index": {pid: verdict}, "record": {...}}."""
 222 | +    index, rec = scorer_verdicts(verdicts_path, render_scorer_sha()) if verdicts_path else \
 223 | +        ({}, {"read": False, "why": "no verdicts file given"})
 224 | +    if candidates_path:
 225 | +        left = [(m, no_role_on_screen(m), no_topic(m)) for m in
 226 | +                ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
 227 | +        ask = [m for m, o, t in left if o and not t] + \
 228 | +            [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
 229 | +        rec = dict(rec, candidates=len(ask), candidates_written=write_candidates(candidates_path, ask, ctx, build_name))
 230 | +    return {"index": index, "record": rec}
 231 | +
 232 | +
 233 |  def no_topic(m):
 234 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
 235 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
 236 | @@ -844,13 +980,16 @@ def no_topic(m):
 237 |  
 238 |  
 239 |  def no_role_on_screen(m):
 240 | -    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
 241 | -    opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
 242 | -    it), else None. build() leaves such moments out before any vendor call."""
 243 | +    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule (it opens on a conjunction
 244 | +    or a reply fragment: the clip role fails closed without an affirming clip-scorer verdict, the hook role fails on
 245 | +    it), else None. RULING 56: the clip role reads the render's own scorer's verdict on the moment's CURRENT text when
 246 | +    one is attached (verdict_of); the hook role never does. build() leaves such moments out before any vendor call."""
 247 |      import stand_alone as SA
 248 | -    c_ok, c_why = SA.opener("clip", m["text"])          # a moment without text fails fast (audit 0310 C2, qwen)
 249 | +    v = verdict_of(m)
 250 | +    c_ok, c_why = SA.opener("clip", m["text"], *((v["score"], v["fault"]) if v else ()))   # (audit 0310 C2, qwen)
 251 |      h_ok, h_why = SA.opener("hook", m["text"])
 252 | -    return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
 253 | +    return None if (c_ok or h_ok) else ("the render's STAND_ALONE " + ("with the clip scorer's verdict" if v else
 254 | +                                        "with no clip scorer at the pin stage") + f": {c_why}; {h_why}")
 255 |  
 256 |  
 257 |  def lineup_ok(segs, crange=None, repeat_ok=False):
 258 | @@ -923,9 +1062,12 @@ def placement(m):
 259 |      """RULING 54: a clip's placement limits as the angle proposer is told them, exactly lineup_for's rules. Without hook
 260 |      eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
 261 |      short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
 262 | -    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook)."""
 263 | +    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook). RULING 56: a
 264 | +    moment the clip scorer's verdict admits (it opens on a conjunction or a reply fragment) never opens: the render's
 265 | +    hook rule refuses it, as stand_alone_check does inside lineup_for."""
 266 | +    import stand_alone as SA
 267 |      opens = bool((m.get("eligibility") or {}).get("hook", {}).get("ok")) and \
 268 | -        (m.get("hook_onset") or {}).get("pass") is True
 269 | +        (m.get("hook_onset") or {}).get("pass") is True and SA.opener("hook", m.get("text") or "")[0]
 270 |      if m["duration_s"] < SHORT_CLIP_S:
 271 |          return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
 272 |      return "" if opens else " | cannot open (never the hook)"
 273 | @@ -1437,22 +1579,31 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 274 |  
 275 |  
 276 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 277 | -          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD):
 278 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, scorer_verdicts_path=None,
 279 | +          scorer_candidates_path=None, build_name=""):
 280 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 281 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 282 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 283 |      one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 284 |      work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 285 |      spend: a callable returning the ledger's USD (dollars per package).
 286 | +    scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 287 | +    render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 288 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 289 |      t0 = time.time()
 290 |      usd0 = _spent(spend)
 291 |      ms, why = usable(moments, ctx, delivered, optout)
 292 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 293 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 294 | +    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name)   # ruling 56
 295 | +    ms = [with_verdict(m, scorer["index"]) for m in ms]
 296 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
 297 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
 298 | -    trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
 299 | +    admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
 300 | +    trims = {m["moment_id"]: with_verdict(v, scorer["index"]) for m in ms if m["moment_id"] in no_role
 301 | +             for v in [trim_variant(m, sources)] if v}
 302 | +    trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
 303 | +    trims = {k: v for k, v in trims.items() if k not in trim_out}
 304 |      ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
 305 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
 306 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 307 | @@ -1463,6 +1614,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 308 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 309 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 310 |             "reposted": reposted,
 311 | +           "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 312 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 313 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 314 |             "package": None}
 315 | @@ -1471,6 +1623,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 316 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 317 |          f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 318 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 319 | +    sc = out["scorer"]
 320 | +    log(f"  the clip scorer's verdicts (ruling 56): " + (
 321 | +        f"{sc['verdicts']} read, {sc['affirmed']} affirmed (rated {sc['rated_at']}, scorer {str(sc['scorer_sha'])[:12]})"
 322 | +        if sc.get("read") else f"none used ({sc.get('why')})") +
 323 | +        f"; {len(admitted)} opener(s) admitted as clips, {len(trims)} trimmed variant(s) affirmed, {len(trim_out)} left "
 324 | +        f"out without an affirmation" + (f"; candidates {sc['candidates']} ("
 325 | +                                         f"{'written' if sc['candidates_written'] else 'unchanged'})"
 326 | +                                         if "candidates" in sc else ""))
 327 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 328 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 329 |          return out
 330 | @@ -2019,10 +2179,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 331 |                                 lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 332 |             if hook is not None else {}),
 333 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 334 | -                                    "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 335 | +                                    "stage, with the render's clip scorer's verdicts as the integrator's service gave "
 336 | +                                    "them (ruling 56); without an affirming one a conjunction, reply-fragment or "
 337 | +                                    "trimmed opener fails closed)"),
 338 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 339 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 340 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 341 | -                                scorer_pending=stand.get("scorer_pending") or [])}
 342 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 343 |             if stand is not None else {}),
 344 |      }
 345 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 346 | index dfbb94f..32a1deb 100644
 347 | --- a/pipeline/package_pin.py
 348 | +++ b/pipeline/package_pin.py
 349 | @@ -68,12 +68,15 @@ def recency_problems(segments):
 350 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
 351 |                  "speaker",                                 # the 00:05 ET Nov 13 order, item 3
 352 |                  "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
 353 | -                "scorer_pending")                          # is trimmed, so every other pin seals as before (ruling 49 a)
 354 | +                "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 355 | +                                                           # retired by ruling 56: kept so its pins still recompute)
 356 | +                "scorer_verdict")                          # ruling 56: the clip scorer's affirmation, only when sealed
 357 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 358 |                                                             # separate constant (a test holds them equal): the
 359 |                                                             # integrator's check_pin_only imports this module, which
 360 |                                                             # must never pull package.py into that process
 361 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
 362 | +SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
 363 |  
 364 |  
 365 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 366 | @@ -100,12 +103,45 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 367 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 368 |  
 369 |  
 370 | +def affirmed_verdict(s):
 371 | +    """RULING 56: True when the segment carries the render's own clip scorer's AFFIRMATION of exactly its text
 372 | +    (approved_text in a pin, text in a package): scorer_verdict with affirmed true, threshold SCORER_MIN, a numeric
 373 | +    score at or over it, a fault other than starts_mid_thought (stand_alone.affirmed), a scorer_sha and an event, and
 374 | +    text_sha256 = the sha256 of the text's UTF-8 bytes."""
 375 | +    v = s.get("scorer_verdict")
 376 | +    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
 377 | +    text = s["approved_text"] if "approved_text" in s else s.get("text")
 378 | +    return isinstance(v, dict) and v.get("affirmed") is True and num(v.get("score")) and \
 379 | +        v.get("threshold") == SCORER_MIN and v["score"] >= SCORER_MIN and v.get("fault") != "starts_mid_thought" and \
 380 | +        bool(v.get("scorer_sha")) and bool(v.get("event")) and isinstance(text, str) and \
 381 | +        v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
 382 | +
 383 | +
 384 | +def scorer_problems(segments):
 385 | +    """[why] for segments that need the clip scorer and do not carry its affirmation (ruling 56: "seal only what it
 386 | +    affirms"): every clip after the hook whose first word is a conjunction or a reply fragment (the render's
 387 | +    stand_alone.check_edl asks its scorer for exactly these), and any segment carrying a scorer_verdict that is not an
 388 | +    affirmation of exactly its text. A trimmed clip's affirmation is trim_problems'."""
 389 | +    import stand_alone as SA
 390 | +    out = []
 391 | +    for i, s in enumerate(segments):
 392 | +        text = s["approved_text"] if "approved_text" in s else s.get("text")
 393 | +        w = SA._words(text)[:1]
 394 | +        needs = i > 0 and bool(w) and (w[0] in SA.CONJUNCTIONS or w[0] in SA.REPLY_FRAGMENTS)
 395 | +        if needs and not affirmed_verdict(s):
 396 | +            out.append(f"segment {i}: opens on {w[0]!r}: the clip scorer's affirmation of its text must be sealed "
 397 | +                       f"(ruling 56)")
 398 | +        elif "scorer_verdict" in s and not affirmed_verdict(s):
 399 | +            out.append(f"segment {i}: carries a clip-scorer verdict that does not affirm exactly its text (ruling 56)")
 400 | +    return out
 401 | +
 402 | +
 403 |  def trim_problems(segments):
 404 |      """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
 405 |      refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
 406 | -    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49: (a) every trimmed clip says
 407 | -    scorer_pending: true (the clip scorer's verdict is pending at the render) and no other clip carries the key;
 408 | -    (b) at most TRIMMED_PER_PIN_MAX trimmed clips."""
 409 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49 (b): at most TRIMMED_PER_PIN_MAX
 410 | +    trimmed clips. RULING 56 ("seal only what it affirms", retiring 49 a's pending form): every trimmed clip carries
 411 | +    the clip scorer's affirmation of its trimmed text (affirmed_verdict), and no segment carries scorer_pending."""
 412 |      import canon
 413 |      out = []
 414 |      n = sum("trimmed_leading" in s or "untrimmed_start" in s for s in segments)
 415 | @@ -114,13 +150,14 @@ def trim_problems(segments):
 416 |                     f"(ruling 49 b)")
 417 |      for i, s in enumerate(segments):
 418 |          has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
 419 | +        if "scorer_pending" in s:
 420 | +            out.append(f"segment {i}: scorer_pending is no longer sealed (ruling 56: seal only what the scorer "
 421 | +                       f"affirms)")
 422 |          if not has_w and not has_s:
 423 | -            if "scorer_pending" in s:
 424 | -                out.append(f"segment {i}: scorer_pending belongs to a trimmed clip only (ruling 49 a)")
 425 |              continue
 426 | -        if s.get("scorer_pending") is not True:
 427 | -            out.append(f"segment {i}: a trimmed clip must say scorer_pending: true (ruling 49 a: the clip scorer's "
 428 | -                       f"verdict on the trimmed text is pending at the render)")
 429 | +        if not affirmed_verdict(s):
 430 | +            out.append(f"segment {i}: a trimmed clip must carry the clip scorer's affirmation of its trimmed text "
 431 | +                       f"(ruling 56)")
 432 |          if has_w != has_s:
 433 |              out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 434 |              continue
 435 | @@ -231,7 +268,7 @@ def to_pin(pk, run_name):
 436 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 437 |                                                                       for x in line_problems(pk)] + \
 438 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 439 | -        screen_problems(pk) + trim_problems(pk.get("segments") or [])
 440 | +        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or [])
 441 |      if problems:
 442 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 443 |      segs = []
 444 | @@ -241,7 +278,7 @@ def to_pin(pk, run_name):
 445 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 446 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 447 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 448 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_pending") if k in s},
 449 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict") if k in s},
 450 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 451 |      edl_vo = {"intro": pk["vo"]["intro"],
 452 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 453 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 454 | index 1ea63a0..fb31df2 100644
 455 | --- a/tests/package/proof_ledger.py
 456 | +++ b/tests/package/proof_ledger.py
 457 | @@ -134,7 +134,8 @@ def main(argv=None):
 458 |      t0 = time.time()
 459 |      res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 460 |                     work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 461 | -                   spend=lambda: (own["est"], own["best"]))
 462 | +                   spend=lambda: (own["est"], own["best"]), scorer_verdicts_path=PK.SCORER_VERDICTS,   # ruling 56
 463 | +                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 464 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 465 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 466 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 467 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 468 | index 04cb0a1..f766c47 100644
 469 | --- a/tests/package/test_medley.py
 470 | +++ b/tests/package/test_medley.py
 471 | @@ -70,6 +70,19 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
 472 |  
 473 |  
 474 |  
 475 | +def sv(text, score, fault="none"):
 476 | +    """A clip-scorer verdict on exactly `text` as build() attaches it (package.scorer_verdicts' shape, ruling 56)."""
 477 | +    return {"score": score, "reason": "r", "fault": fault, "affirmed": score >= 3.5 and fault != "starts_mid_thought",
 478 | +            "text_sha256": PK.text_sha(text), "prompt_sha256": "p" * 64, "model": "gemma3:27b",
 479 | +            "event": "Pinned: bitcoin", "scorer_sha": "s" * 64, "threshold": 3.5, "rated_at": "2026-11-13T15:35:10Z"}
 480 | +
 481 | +
 482 | +def fv(text, score, fault="none"):
 483 | +    """One verdict as the integrator's verdicts file holds it (their contract, ruling 56), on exactly `text`."""
 484 | +    return {"text_sha256": PK.text_sha(text), "score": score, "reason": "r", "fault": fault,
 485 | +            "affirmed": score >= 3.5 and fault != "starts_mid_thought", "prompt_sha256": "p" * 64}
 486 | +
 487 | +
 488 |  def spk(pk):
 489 |      """speakers.attribute's record on every segment, as the real flow attaches it before the pin is sealed (the
 490 |      00:05 ET Nov 13 order, item 3): an unknown speaker, measured, no person named."""
 491 | @@ -505,12 +518,13 @@ class Rig:
 492 |  
 493 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 494 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 495 | -                 trim_fail=()):
 496 | +                 trim_fail=(), verdicts=None):
 497 |          import providers as P
 498 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 499 |          self.takeaways, self.spend = list(takeaways or []), spend
 500 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 501 |          self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
 502 | +        self.verdicts = verdicts                           # ruling 56: {pid: verdict} in the integrator's file shape
 503 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 504 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 505 |          self.screens, self.events, self.a_seen = [], [], []
 506 | @@ -607,15 +621,27 @@ class Rig:
 507 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 508 |                                                               "replayed": False}),
 509 |          }
 510 | +        kw, path = {}, None
 511 | +        if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 512 | +            import tempfile
 513 | +            fd, path = tempfile.mkstemp(suffix=".json")
 514 | +            with os.fdopen(fd, "w") as f:
 515 | +                json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "test", "scorer": {
 516 | +                    "model": "gemma3:27b", "threshold": 3.5, "event": PK.SCORER_EVENT, "scorer_sha": "s" * 64},
 517 | +                    "verdicts": self.verdicts}, f)
 518 | +            kw["scorer_verdicts_path"] = path
 519 | +            stubs["render_scorer_sha"] = lambda *a, **k: "s" * 64       # the render's scorer code, as it is now
 520 |          saved = {k: getattr(PK, k) for k in stubs}
 521 |          try:
 522 |              for k, v in stubs.items():
 523 |                  setattr(PK, k, v)
 524 |              return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
 525 | -                            spend=self.spend)
 526 | +                            spend=self.spend, **kw)
 527 |          finally:
 528 |              for k, v in saved.items():
 529 |                  setattr(PK, k, v)
 530 | +            if path:
 531 | +                os.remove(path)
 532 |  
 533 |  
 534 |  class TestBuildLoop(unittest.TestCase):
 535 | @@ -858,7 +884,8 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 536 |      """Ruling 33 part 2 (render merged 11e361cc), used per the 04:58 order's item 42: a moment opening on ONE of
 537 |      but/and/so/well/now/yeah, left out by the render's STAND_ALONE opener rule, may be cut one word in. The variant is
 538 |      judged like any moment (step A, L-v 2 with the trimmed word heard, the acoustic onset rule at the trimmed cut); the
 539 | -    clip scorer's verdict is pending at the render; the pin seals trimmed_leading and untrimmed_start."""
 540 | +    clip scorer must affirm the trimmed text (ruling 56: the integrator's pin-stage verdicts; ruling 49 a's pending form
 541 | +    is retired); the pin seals trimmed_leading, untrimmed_start and the affirmation."""
 542 |  
 543 |      def moment(self, sentence, mid="t"):
 544 |          src = source([sentence], vid="vT")
 545 | @@ -890,24 +917,25 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 546 |          m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
 547 |          self.assertIsNone(PK.trim_variant(m, srcs))
 548 |  
 549 | -    def test_pending_at_the_render_by_ruling_49_and_strict_on_the_switch(self):
 550 | +    def test_ruling_56_a_trimmed_clip_passes_only_with_the_scorers_affirmation(self):
 551 |          m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 552 |          v = PK.trim_variant(m, srcs)
 553 | -        line = [{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}]
 554 | -        self.assertTrue(PK.TRIM_SCORER_PENDING)                       # ruling 49 (07:02): YES
 555 | -        r = PK.stand_alone_check(line)
 556 | -        self.assertTrue(r["ok"], r["rows"])
 557 | -        self.assertEqual(r["scorer_pending"], ["clip_01"])
 558 | -        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 559 | -        saved = PK.TRIM_SCORER_PENDING
 560 | -        try:                                                          # the strict switch: the render's check with
 561 | -            PK.TRIM_SCORER_PENDING = False                            # no scorer fails closed, never sealed
 562 | -            r = PK.stand_alone_check(line)
 563 | -        finally:
 564 | -            PK.TRIM_SCORER_PENDING = saved
 565 | +        hook, last = {"text": "Bitcoin is the hardest money ever made."}, {"text": "Bitcoin wins."}
 566 | +        self.assertFalse(hasattr(PK, "TRIM_SCORER_PENDING"))          # ruling 49 (a)'s pending form is retired
 567 | +        r = PK.stand_alone_check([hook, v, last])                     # no verdict: fails closed, as at validate
 568 |          self.assertFalse(r["ok"])
 569 |          self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 570 | -        self.assertEqual(r["scorer_pending"], [])
 571 | +        self.assertNotIn("scorer_pending", r)
 572 | +        r = PK.stand_alone_check([hook, dict(v, scorer_verdict=sv(v["text"], 4.0)), last])
 573 | +        self.assertTrue(r["ok"], r["rows"])
 574 | +        self.assertIn("the clip scorer affirms the trimmed text", r["rows"][1]["opener"]["why"])
 575 | +        self.assertEqual(r["rows"][1]["scorer"]["score"], 4.0)        # the verdict used is in the sealed row
 576 | +        for bad in (sv(v["text"], 3.0, "ends_mid_thought"), sv(v["text"], 4.0, "starts_mid_thought"),
 577 | +                    sv(m["text"], 4.0)):                              # the untrimmed text's verdict is not its own
 578 | +            self.assertFalse(PK.stand_alone_check([hook, dict(v, scorer_verdict=bad), last])["ok"], bad)
 579 | +        self.assertIn("no clip-scorer verdict on the trimmed text yet", PK.trim_refused(v))
 580 | +        self.assertIsNone(PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 4.0))))
 581 | +        self.assertIn("does not affirm", PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 3.0, "other"))))
 582 |  
 583 |      def test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin(self):
 584 |          self.assertEqual(PK.TRIMMED_PER_LINEUP_MAX, package_pin.TRIMMED_PER_PIN_MAX)
 585 | @@ -923,10 +951,12 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 586 |                 {"trimmed_leading": "So", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True}]
 587 |          self.assertIn("2 trimmed clips", package_pin.trim_problems(two)[0])
 588 |  
 589 | -    def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 590 | +    def test_the_pin_seals_the_trim_with_its_affirmation_and_refuses_a_malformed_one(self):
 591 | +        import copy
 592 | +        x_text = "Bitcoin keeps every promise it ever made to me."
 593 |          segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 594 | -                dict(pm("x", "B", 14.0), text="Bitcoin keeps every promise it ever made to me.",
 595 | -                     trimmed_leading="But", untrimmed_start=0.0, start=0.3),
 596 | +                dict(pm("x", "B", 14.0), text=x_text, trimmed_leading="But", untrimmed_start=0.0, start=0.3,
 597 | +                     scorer_verdict=sv(x_text, 4.0)),
 598 |                  dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
 599 |          by = {m["moment_id"]: m for m in segs}
 600 |          fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 601 | @@ -935,32 +965,41 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 602 |          pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 603 |          self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
 604 |          pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 605 | -        pin = package_pin.to_pin(spk(pk), "test")
 606 | +        pin = package_pin.to_pin(copy.deepcopy(spk(pk)), "test")
 607 |          s1 = pin["segments"][1]
 608 | -        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"], s1["scorer_pending"]), ("But", 0.0, True))
 609 | -        self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 610 | -        self.assertNotIn("scorer_pending", pin["segments"][0])                    # ruling 49 (a): per trimmed clip
 611 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 612 | +        self.assertTrue(package_pin.affirmed_verdict(s1))                         # ruling 56: sealed, on its text
 613 | +        self.assertNotIn("scorer_pending", s1)
 614 | +        for k in ("trimmed_leading", "scorer_verdict", "scorer_pending"):         # untrimmed segments: unchanged
 615 | +            self.assertNotIn(k, pin["segments"][0])
 616 |          mp = pin["moments_package"]
 617 |          args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 618 |          self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 619 | -        other = [dict(x) for x in pin["segments"]]
 620 | +        other = copy.deepcopy(pin["segments"])
 621 |          other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 622 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 623 | -        other[1]["trimmed_leading"], other[1]["scorer_pending"] = "But", False      # and so is scorer_pending
 624 | +        other = copy.deepcopy(pin["segments"])
 625 | +        other[1]["scorer_verdict"]["score"] = 5.0                                 # and so is the affirmation
 626 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 627 |          for bad in ({"trimmed_leading": "Because"}, {"trimmed_leading": "But so"}, {"trimmed_leading": "and/or"},
 628 |                      {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
 629 | -                    {"scorer_pending": False}):                                       # ruling 49 (a) in plain words
 630 | -            p = spk(pk)
 631 | +                    {"scorer_pending": True},                                     # ruling 56: never sealed
 632 | +                    {"scorer_verdict": sv(x_text, 3.0, "ends_mid_thought")},      # a refusal
 633 | +                    {"scorer_verdict": sv("But " + x_text, 4.0)}):                # another text's verdict
 634 | +            p = copy.deepcopy(spk(pk))                                            # each case on its own
 635 |              p["segments"][1] = dict(p["segments"][1], **bad)
 636 | -            with self.assertRaises(package_pin.PinRefused):
 637 | +            with self.assertRaises(package_pin.PinRefused, msg=str(bad)):
 638 |                  package_pin.to_pin(p, "test")
 639 | -        p = spk(pk)
 640 | -        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # only on a trimmed clip
 641 | +        p = copy.deepcopy(spk(pk))
 642 | +        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "scorer_verdict"}   # no affirmation
 643 | +        with self.assertRaises(package_pin.PinRefused):
 644 | +            package_pin.to_pin(p, "test")
 645 | +        p = copy.deepcopy(spk(pk))
 646 | +        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # not on any segment
 647 |          with self.assertRaises(package_pin.PinRefused):
 648 |              package_pin.to_pin(p, "test")
 649 |          self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
 650 | -        p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
 651 | +        p = copy.deepcopy(spk(pk))                                        # ^ refused, never raised (glm P0-8)
 652 |          p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 653 |          with self.assertRaises(package_pin.PinRefused):                          # both keys or neither
 654 |              package_pin.to_pin(p, "test")
 655 | @@ -972,9 +1011,10 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 656 |          saved = PK.trim_variant
 657 |          try:
 658 |              PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 659 | -            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"})
 660 | +            ok = {"b~trim": fv("Bitcoin x.", 4.0)}                  # ruling 56: the scorer affirms the trimmed text
 661 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"}, verdicts=ok)
 662 |              out = rig.run()
 663 | -            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 664 | +            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"}, verdicts=ok)
 665 |              out2 = rig2.run()
 666 |          finally:
 667 |              PK.trim_variant = saved
 668 | @@ -987,6 +1027,195 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 669 |          self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 670 |  
 671 |  
 672 | +class TestRuling56Scorer(unittest.TestCase):
 673 | +    """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 674 | +    about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
 675 | +    sealed. Their verdicts file is read only and fail closed."""
 676 | +
 677 | +    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."
 678 | +
 679 | +    def file(self, verdicts=None, **scorer):
 680 | +        import tempfile
 681 | +        fd, path = tempfile.mkstemp(suffix=".json")
 682 | +        with os.fdopen(fd, "w") as f:
 683 | +            json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "b", "candidates_generated_at": "g",
 684 | +                       "scorer": dict({"model": "gemma3:27b", "threshold": 3.5, "event": "Pinned: bitcoin",
 685 | +                                       "scorer_sha": "s" * 64}, **scorer), "verdicts": verdicts or {}}, f)
 686 | +        self.addCleanup(os.remove, path)
 687 | +        return path
 688 | +
 689 | +    def test_the_verdicts_file_is_used_only_when_every_check_holds(self):
 690 | +        good = {"a": fv(self.OPENER, 4.0), "b": fv("Bitcoin b.", 3.0, "ends_mid_thought")}
 691 | +        idx, rec = PK.scorer_verdicts(self.file(good), "s" * 64)
 692 | +        self.assertEqual(sorted(idx), ["a", "b"])
 693 | +        self.assertEqual((rec["read"], rec["verdicts"], rec["affirmed"]), (True, 2, 1))
 694 | +        self.assertEqual((idx["a"]["affirmed"], idx["b"]["affirmed"]), (True, False))
 695 | +        self.assertEqual((idx["a"]["event"], idx["a"]["scorer_sha"], idx["a"]["threshold"]),
 696 | +                         ("Pinned: bitcoin", "s" * 64, 3.5))
 697 | +        for scorer, code, why in (({"event": "Pinned: gold"}, "s" * 64, "another event"),
 698 | +                                  ({}, "t" * 64, "a scorer_sha that is not the render's scorer code now"),
 699 | +                                  ({}, None, "the render's scorer code could not be read"),
 700 | +                                  ({"threshold": 3.0}, "s" * 64, "another threshold"),
 701 | +                                  ({"threshold": True}, "s" * 64, "another threshold")):
 702 | +            idx, rec = PK.scorer_verdicts(self.file(good, **scorer), code)
 703 | +            self.assertEqual((idx, rec["read"], rec["why"]), ({}, False, why))
 704 | +        idx, rec = PK.scorer_verdicts("/nonexistent/latest.json", "s" * 64)
 705 | +        self.assertEqual((idx, rec["read"]), ({}, False))
 706 | +        bad = self.file()
 707 | +        with open(bad, "w") as f:
 708 | +            f.write("{not json")
 709 | +        self.assertEqual(PK.scorer_verdicts(bad, "s" * 64)[0], {})
 710 | +        odd = {"e": dict(fv("x", 4.0), error="not rated"), "n": dict(fv("x", 4.0), score=None),
 711 | +               "t": dict(fv("x", 4.0), score=True), "d": dict(fv("x", 3.0), affirmed=True),
 712 | +               "s": dict(fv("x", 4.0), text_sha256=None)}
 713 | +        idx, rec = PK.scorer_verdicts(self.file(odd), "s" * 64)
 714 | +        self.assertEqual(idx, {})                                       # none of them is a verdict
 715 | +        self.assertEqual(rec["disagree_with_the_rule"], ["d"])          # "affirmed" against the render's own rule
 716 | +
 717 | +    def test_the_scorer_sha_is_recomputed_from_the_renders_code(self):
 718 | +        import hashlib
 719 | +        import tempfile
 720 | +        self.assertEqual(PK.RENDER_SCORER_CODE, ("/home/ultron/protocol_pulse/pipeline/stand_alone.py",
 721 | +                                                 "/home/ultron/protocol_pulse/pipeline/story_semantics.py"))
 722 | +        with tempfile.TemporaryDirectory() as d:
 723 | +            a, b = os.path.join(d, "a.py"), os.path.join(d, "b.py")
 724 | +            for path, data in ((a, b"one"), (b, b"two")):
 725 | +                with open(path, "wb") as f:
 726 | +                    f.write(data)
 727 | +            self.assertEqual(PK.render_scorer_sha((a, b)), hashlib.sha256(b"onetwo").hexdigest())
 728 | +            self.assertIsNone(PK.render_scorer_sha((a, os.path.join(d, "missing.py"))))
 729 | +
 730 | +    def test_a_verdict_attaches_only_to_its_own_text(self):
 731 | +        m = dict(pm("a", "A", 12.0), text=self.OPENER)
 732 | +        got = PK.with_verdict(m, {"a": sv(self.OPENER, 4.0)})
 733 | +        self.assertIs(PK.verdict_of(got), got["scorer_verdict"])
 734 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"a": sv("Another text.", 4.0)}))
 735 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"b": sv(self.OPENER, 4.0)}))
 736 | +        trimmed = dict(got, moment_id="a~trim", text=self.OPENER[len("And "):])   # carries the key, not the verdict
 737 | +        self.assertIsNone(PK.verdict_of(trimmed))
 738 | +        self.assertNotIn("scorer_verdict", PK.with_verdict(trimmed, {"a": sv(self.OPENER, 4.0)}))
 739 | +
 740 | +    def test_an_affirmed_opener_plays_as_a_clip_never_as_the_hook(self):
 741 | +        m = dict(pm("a", "A", 12.0), text=self.OPENER, hook_onset={"pass": True})
 742 | +        self.assertIn("with no clip scorer", PK.no_role_on_screen(m))
 743 | +        ok = dict(m, scorer_verdict=sv(self.OPENER, 4.0))
 744 | +        self.assertIsNone(PK.no_role_on_screen(ok))
 745 | +        why = PK.no_role_on_screen(dict(m, scorer_verdict=sv(self.OPENER, 3.0, "ends_mid_thought")))
 746 | +        self.assertIn("with the clip scorer's verdict", why)
 747 | +        self.assertIn("does not affirm", why)
 748 | +        self.assertTrue(ok["eligibility"]["hook"]["ok"])               # hook-eligible (L-o: a conjunction is a target)
 749 | +        self.assertEqual(PK.placement(ok), " | cannot open (never the hook)")   # but the render's hook rule refuses
 750 | +        self.assertEqual(PK.placement(dict(ok, duration_s=6.0)), " | under 8 s: only the LAST clip")
 751 | +        hook, x = dict(pm("h", "B", 12.0), hook_onset={"pass": True}), dict(pm("x", "C", 13.0), hook_onset={"pass": True})
 752 | +        r = PK.stand_alone_check([hook, ok, x])
 753 | +        self.assertTrue(r["ok"], r["rows"])
 754 | +        self.assertIn("the clip scorer affirms it stands alone", r["rows"][1]["opener"]["why"])
 755 | +        self.assertFalse(PK.stand_alone_check([ok, hook, x])["ok"])    # never the hook
 756 | +        by = {y["moment_id"]: y for y in (ok, hook, x, dict(pm("y", "D", 13.0), hook_onset={"pass": True}))}
 757 | +        segs = PK.lineup_for(angle(["a", "h", "x", "y"], "a"), by, need_onset=True, need_stand_alone=True)
 758 | +        self.assertNotEqual(segs[0]["moment_id"], "a")                  # the proposer's hook gives way ...
 759 | +        self.assertIn("a", [y["moment_id"] for y in segs])             # ... and it plays as a clip
 760 | +
 761 | +    def test_the_build_admits_only_what_the_scorer_affirms(self):
 762 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), dict(pm("b", "E", 13.0), text=self.OPENER)]
 763 | +        rig = Rig(ms, ["h", "b", "x", "y"], [(True, [], None, Rig.LINE)], [None], verdicts={"b": fv(self.OPENER, 4.0)})
 764 | +        out = rig.run()
 765 | +        self.assertNotIn("b", out["no_role"])
 766 | +        self.assertEqual((out["scorer"]["read"], out["scorer"]["admitted"]), (True, ["b"]))
 767 | +        self.assertIn("id=b | E | 13.0 s | cannot open (never the hook) | ",
 768 | +                      next(p for r, p in rig.prompts if r == "angle_write"))
 769 | +        seg = next(s for s in out["package"]["segments"] if s["moment_id"] == "b")      # it plays, as a clip,
 770 | +        self.assertTrue(package_pin.affirmed_verdict(seg))                                # its affirmation sealed
 771 | +        self.assertNotEqual(out["package"]["segments"][0]["moment_id"], "b")
 772 | +        refused = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None],
 773 | +                      verdicts={"b": fv(self.OPENER, 3.0, "ends_mid_thought")}).run()
 774 | +        self.assertIn("with the clip scorer's verdict", refused["no_role"]["b"])
 775 | +        self.assertEqual(refused["scorer"]["admitted"], [])
 776 | +        none = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None]).run()     # no verdicts: as before 56
 777 | +        self.assertIn("with no clip scorer", none["no_role"]["b"])
 778 | +        self.assertEqual(none["scorer"]["why"], "no verdicts file given")
 779 | +
 780 | +    def test_a_trimmed_variant_needs_the_affirmation_before_any_vendor_call(self):
 781 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 782 | +              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
 783 | +        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
 784 | +        saved, outs = PK.trim_variant, {}
 785 | +        try:
 786 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 787 | +            for k, vs in (("none", None), ("refused", {"b~trim": fv("Bitcoin x.", 3.0, "ends_mid_thought")}),
 788 | +                          ("affirmed", {"b~trim": fv("Bitcoin x.", 4.0)})):
 789 | +                rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=vs)
 790 | +                outs[k] = (rig, rig.run())
 791 | +        finally:
 792 | +            PK.trim_variant = saved
 793 | +        for k in ("none", "refused"):
 794 | +            rig, out = outs[k]
 795 | +            self.assertEqual(out["trimmed"], {}, k)
 796 | +            self.assertFalse(any("b~trim" in ids for _, ids in rig.screens), k)     # never sent to step A
 797 | +        self.assertIn("no clip-scorer verdict on the trimmed text yet", outs["none"][1]["scorer"]["trims_out"]["b"])
 798 | +        self.assertIn("does not affirm", outs["refused"][1]["scorer"]["trims_out"]["b"])
 799 | +        rig, out = outs["affirmed"]
 800 | +        self.assertEqual((out["trimmed"], out["scorer"]["trims_affirmed"]), ({"b": "b~trim"}, ["b"]))
 801 | +        self.assertTrue(any("b~trim" in ids for _, ids in rig.screens))
 802 | +
 803 | +    def test_the_candidates_file_asks_about_every_opener_left_out_and_changes_only_with_its_set(self):
 804 | +        import tempfile
 805 | +        but, srcs = TestRuling33TrimAtThePinStage().moment(
 806 | +            "But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 807 | +        opener = dict(pm("o", "B", 12.0), text=self.OPENER)
 808 | +        gold = dict(pm("g", "C", 12.0), text="And gold is the hardest money ever made, which is why it wins.")
 809 | +        plain = pm("p", "D", 12.0)
 810 | +        with tempfile.TemporaryDirectory() as d:
 811 | +            path = os.path.join(d, "candidates.json")
 812 | +
 813 | +            def load():
 814 | +                with open(path) as f:
 815 | +                    return json.load(f)
 816 | +            r = PK.scorer_pass([but, opener, gold, plain], srcs, ctx(), None, path, "ledger_test")
 817 | +            self.assertEqual((r["index"], r["record"]["read"], r["record"]["candidates_written"]), ({}, False, True))
 818 | +            doc = load()
 819 | +            self.assertEqual((doc["build"], doc["event_expected"]), ("ledger_test", "Pinned: bitcoin"))
 820 | +            got = {c["pid"]: c for c in doc["candidates"]}
 821 | +            self.assertEqual(sorted(got), ["o", "t", "t~trim"])           # gold fails the topic rule: never asked
 822 | +            for pid, c in got.items():
 823 | +                self.assertEqual(c["text_sha256"], PK.text_sha(c["text"]), pid)
 824 | +                self.assertEqual(set(c), {"pid", "video_id", "channel", "duration", "text", "text_sha256",
 825 | +                                          "trimmed_leading"})
 826 | +            self.assertEqual((got["t~trim"]["trimmed_leading"], got["o"]["trimmed_leading"]), ("But", None))
 827 | +            self.assertTrue(got["t~trim"]["text"].startswith("Bitcoin has rarely"))
 828 | +            gen = doc["generated_at"]
 829 | +            r = PK.scorer_pass([but, dict(opener, scorer_verdict=sv(self.OPENER, 4.0)), gold, plain], srcs, ctx(),
 830 | +                               None, path, "ledger_test2")                # a verdict attached changes nothing asked
 831 | +            self.assertFalse(r["record"]["candidates_written"])
 832 | +            self.assertEqual(load()["generated_at"], gen)
 833 | +            r = PK.scorer_pass([but, plain], srcs, ctx(), None, path, "ledger_test3")
 834 | +            self.assertTrue(r["record"]["candidates_written"])
 835 | +            self.assertEqual(sorted(c["pid"] for c in load()["candidates"]), ["t", "t~trim"])
 836 | +            self.assertFalse(os.path.exists(path + ".tmp"))
 837 | +        self.assertTrue(PK.SCORER_CANDIDATES.endswith("docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json"))
 838 | +
 839 | +    def test_the_pin_holds_the_affirmation_to_its_text(self):
 840 | +        import stand_alone as SA
 841 | +        self.assertEqual(package_pin.SCORER_MIN, SA.CLIP_MIN_SCORE)
 842 | +        s = {"approved_text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}
 843 | +        self.assertTrue(package_pin.affirmed_verdict(s))
 844 | +        self.assertTrue(package_pin.affirmed_verdict({"text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}))
 845 | +        for bad in (dict(sv(self.OPENER, 4.0), affirmed=False), sv(self.OPENER, 3.0),
 846 | +                    sv(self.OPENER, 4.0, "starts_mid_thought"), dict(sv(self.OPENER, 4.0), threshold=3.0),
 847 | +                    dict(sv(self.OPENER, 4.0), score="4"), dict(sv(self.OPENER, 4.0), scorer_sha=""),
 848 | +                    dict(sv(self.OPENER, 4.0), event=None), sv(self.OPENER + " ", 4.0), None, "affirmed"):
 849 | +            self.assertFalse(package_pin.affirmed_verdict(dict(s, scorer_verdict=bad)), bad)
 850 | +        segs = [{"approved_text": "Bitcoin is money."}, {"approved_text": self.OPENER},
 851 | +                {"approved_text": "Yeah, Bitcoin is money."},
 852 | +                {"approved_text": "Bitcoin x.", "scorer_verdict": sv("Bitcoin y.", 4.0)}]
 853 | +        self.assertEqual([x.split(":")[0] for x in package_pin.scorer_problems(segs)],
 854 | +                         ["segment 1", "segment 2", "segment 3"])
 855 | +        for i, t in ((1, self.OPENER), (2, "Yeah, Bitcoin is money."), (3, "Bitcoin x.")):
 856 | +            segs[i]["scorer_verdict"] = sv(t, 4.0)
 857 | +        self.assertEqual(package_pin.scorer_problems(segs), [])
 858 | +        self.assertEqual(package_pin.scorer_problems([{"approved_text": self.OPENER}]), [])   # a hook: the gate's
 859 | +
 860 | +
 861 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 862 |      """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 863 |      after a write swaps out that clip only, and the line-up carries on."""
 864 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels, sealed in a pin that the integrator renders). Your role: a strict reviewer of a fail-closed admission path.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- The render's STAND_ALONE check (stand_alone.check_edl, run at validate before any render) judges each segment's
  opener:
  - a HOOK that opens on a pronoun, a conjunction or a reply fragment always fails;
  - a CLIP that opens on a conjunction or a reply fragment passes only when the render's clip scorer affirms it: score
    >= CLIP_MIN_SCORE 3.5 and fault != "starts_mid_thought";
  - a segment whose lock trims ONE leading word (ruling 33 part 2: selection_lock.trimmed_leading) passes only when the
    scorer affirms the trimmed text;
  - check_edl calls rate(passages) -> {pid: (score, reason, fault)} for exactly those segments; without a rating they
    fail closed.
- The scorer is a local model (gemma3:27b) on GPU0, which this builder may not use. So the builder left out every
  moment that opens on a conjunction or reply fragment (no_role_on_screen), and since ruling 33 part 2 it offers a
  variant with ONE leading word trimmed (trim_variant).
- Ruling 49 (07:02) let a trimmed clip be sealed with the scorer's verdict "pending at the render"
  (scorer_pending: true), and added "If you can call the same scorer ... do that instead". Ruling 49 (b) allows at
  most ONE trimmed clip per line-up until the first one is affirmed AT VALIDATE.
- The integrator now runs a pin-stage service that asks the render's own scorer (the same code path as validate) and
  writes a verdicts file. Their contract, adopted by both sides:
  - I write a candidates file: {generated_at, build, candidates: [{pid, video_id, channel, duration, text,
    text_sha256, trimmed_leading}]}. A new generated_at starts a pass, and texts already rated are reused.
  - They write verdicts/latest.json: {rated_at, build, candidates_generated_at, scorer: {model, threshold 3.5, event
    "Pinned: bitcoin", scorer_sha}, verdicts: {pid: {text_sha256, score, reason, fault, affirmed, prompt_sha256} |
    {text_sha256, error}}}.
  - scorer_sha = sha256 over the render's pipeline/stand_alone.py + pipeline/story_semantics.py bytes. A verdict
    under another scorer_sha is not the render's code.
  - "Admit only pid + text_sha256 matches with affirmed true. Check scorer.event and scorer.scorer_sha." Validate
    re-asks at render with its own event.
- The integrator's pin check imports pipeline/package_pin.py from this worktree and recomputes seal(). A field added
  to the seal body must enter it only when a segment carries it (SEALED_LATER), so that every earlier pin recomputes.

The order this diff implements (ORCHESTRATOR RULING 56, 09:59 ET Nov 13): "You will get a pin-stage way to ask the
render's own STAND_ALONE scorer (gemma3:27b on GPU0) about the ~105 moments you leave out as 'an opener the clip
scorer would have to affirm'. Submit them all, untrimmed and trimmed variants; seal only what it affirms."

The change (pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py, tests/package/test_medley.py):

1. scorer_verdicts(path, code_sha), read only. It uses nothing at all on:
   - a missing, unreadable or malformed file;
   - an event other than "Pinned: bitcoin";
   - a scorer_sha other than code_sha. render_scorer_sha() recomputes code_sha from the render's two files, read only;
     None when unreadable;
   - a threshold other than stand_alone.CLIP_MIN_SCORE.
   A single verdict is no verdict when it lacks a numeric score, carries an error, or its "affirmed" disagrees with the
   render's own rule.
2. with_verdict / verdict_of: a verdict attaches to a moment only when its text_sha256 is the sha256 of the moment's
   CURRENT text. A copied key on a trimmed variant is never its verdict.
3. no_role_on_screen: the CLIP role reads the attached verdict (stand_alone.opener with its score and fault); the
   hook role never does.
4. stand_alone_check:
   - check_edl gets a rate() answered from the attached verdicts;
   - a trimmed segment always carries the render's lock marker, so trimmed_opener judges it, as at validate;
   - the scorer_pending list and its row text are removed.
5. placement(): a moment whose text the render's hook rule refuses is told "cannot open", even when it is
   hook-eligible. Such a moment is a conjunction opener admitted by a verdict; eligibility treats a conjunction as a
   target under law L-o.
6. build(scorer_verdicts_path, scorer_candidates_path, build_name), via scorer_pass():
   - It reads the verdicts and attaches them before the STAND_ALONE rules. out["scorer"]["admitted"] lists the openers
     that took a clip place.
   - A trimmed variant without an affirmation is left out BEFORE step A (trim_refused); out["scorer"]["trims_out"]
     records why.
   - It writes the next pass's candidates: the moments no_role_on_screen leaves out whose topic rule passes, plus the
     trimmed variant of every moment left out. The set is computed before any verdict attaches. The write is atomic
     (.tmp, then rename) and happens only when the (pid, text_sha256) set changed.
7. The package's rows seal "scorer_verdict" only when it affirms. scorer_pending is no longer produced:
   TRIM_SCORER_PENDING is removed.
8. package_pin:
   - "scorer_verdict" joins SEALED_LATER. "scorer_pending" stays there, so pins sealed with it still recompute.
   - SCORER_MIN 3.5 (a test holds it equal to stand_alone.CLIP_MIN_SCORE).
   - affirmed_verdict(s): affirmed true, threshold == SCORER_MIN, a numeric score >= it, fault != starts_mid_thought,
     a scorer_sha and an event, and text_sha256 == the sha256 of approved_text (pin) or text (package).
   - scorer_problems: any clip after the hook that opens on a conjunction or reply fragment must carry an affirmation;
     any carried verdict must affirm exactly its text.
   - trim_problems: every trimmed clip must carry an affirmation, and scorer_pending is refused on any segment.
   - to_pin runs scorer_problems.
9. The stand_alone inventory row's "by" text names the verdicts. Its empty scorer_pending field is gone.
10. proof_ledger passes the integrator's latest.json, the candidates file path and the record's name.
11. Tests: 8 new (TestRuling56Scorer). The ruling-49 tests of the pending form are rewritten for the verdict path.
    test_medley 102 OK; every other suite OK, including "every earlier pin still recomputes".

Stated readings (say so if you read the rulings differently):
- K1: "seal only what it affirms" retires ruling 49 (a)'s pending form, and 49 itself said "If you can call the same
  scorer ... do that instead". The integrator also wrote "nothing sealed pending". So a trimmed variant without an
  affirmation never reaches a vendor, and the pin refuses scorer_pending.
- K2: an affirmed opener is admitted for the CLIP role only. A hook is never rescued by the scorer at the render.
- K3: a moment that also fails the topic rule is not submitted, because no verdict can give it a place. Its trimmed
  variant is submitted when the trimmed text passes both rules (trim_variant already requires that).
- K4: TRIMMED_PER_LINEUP_MAX stays 1. Ruling 49 (b) waits for an affirmation AT VALIDATE, which a pin-stage verdict
  is not.
- K5: the scorer_sha check recomputes the render's code sha at build time (read only). A service restarted on newer
  code, or a newer render tree, therefore makes old verdicts unusable until they are re-rated. That fails closed, by
  the integrator's own definition.

Evidence (dry run of this code on the real verdicts file and the last build's moments, read only):
- 145 verdicts read, 0 affirmed, 0 that disagree with the rule; the scorer_sha matches the render's code now.
- 0 openers admitted; 57 trimmed variants, all left out (52 refused, 5 not yet rated).
- 123 candidates: 112 identical to the current file, 11 new, 33 dropped. The 33 are untrimmed moments that also fail
  the topic rule.

Check in particular:
- every fail-closed path;
- the sha matching (a trimmed variant never inherits);
- that an admitted opener can never open a line-up;
- the pin's three checks and the seal's backward compatibility;
- the atomic, only-on-change write;
- any remaining reader of scorer_pending or TRIM_SCORER_PENDING;
- that no check accepts more than before except through an affirmation, by the render's own scorer, of exactly the
  text that is sealed.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

