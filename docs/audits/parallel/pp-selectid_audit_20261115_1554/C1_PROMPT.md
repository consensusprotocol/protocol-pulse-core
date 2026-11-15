# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1554
# Branch: pp-selectid
# Generated: 2026-11-15 15:54 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1554/C1_STEP.diff (999 lines)
```
   1 | diff --git a/pipeline/lineup_bar.py b/pipeline/lineup_bar.py
   2 | new file mode 100644
   3 | index 0000000..b95489e
   4 | --- /dev/null
   5 | +++ b/pipeline/lineup_bar.py
   6 | @@ -0,0 +1,99 @@
   7 | +"""RULING 116 (orchestrator 15:30 ET Nov 15; Q3 on STATE 15:34, ruling 106's default APPLY): THE LINE-UP VERDICTS ON
   8 | +A CALIBRATED BAR, the hook's method (ruling 115).
   9 | +
  10 | +Today's clips-alone verdict (package.medley) and coherence verdict (package.coherence) failed PBX's own approved
  11 | +line-ups on ONE rating of 3 (tests/package/proof/clips116/: the four approved line-ups, seeds 7, 8, 9, Grok, today's
  12 | +prompts). A rating's FLOOR is the lowest value it took across them, never under 3: clips-alone, every clip after the
  13 | +hook; coherence, every clip after the hook and the VO point. The through-line stays required and the flagged joins
  14 | +stay at the law's one bridge (L-y 2): no approved line-up needed more.
  15 | +
  16 | +The floors live in ONE sealed file, pipeline/lineup_calibration.json (hook_bar's seal), valid only for its rater, the
  17 | +two prompts' versions (package.MEDLEY_VERSION, COHERENCE_VERSION) and its own valid_h (null: one fixed source). They
  18 | +apply ONLY to a verdict the calibrated rater gave. Any other model's verdict, and every verdict while the file is
  19 | +invalid, is judged on the STANDARD bar (package.COHERENCE_MIN), which is stricter: the calibrated bar passes no more
  20 | +than PBX's approvals show passing. A package whose two verdicts both passed on it says so in its record and pin
  21 | +(NOTE)."""
  22 | +import os
  23 | +from datetime import datetime, timedelta, timezone
  24 | +
  25 | +import hook_bar as HB
  26 | +
  27 | +PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineup_calibration.json")
  28 | +VERDICTS = {"clips_alone": ("clip",), "coherence": ("clip", "vo_point")}   # each verdict's calibrated parts
  29 | +FLOOR_MIN = HB.FLOOR_MIN            # 3: ruling 115's rule, applied the same way (ruling 116 (4))
  30 | +NOTE = "line-up passed on the calibrated bar"
  31 | +
  32 | +
  33 | +def floors_from(runs):
  34 | +    """{verdict: {part: the lowest value it took across the runs, never under FLOOR_MIN}} and the parts stopped at
  35 | +    FLOOR_MIN. runs: {verdict: [{"clips": {label: rating}, "vo_point": n (coherence)}, ...]} (the hook not among the
  36 | +    clips). A run without its ratings measures nothing: ValueError."""
  37 | +    fl, low = {}, []
  38 | +    for verdict, parts in VERDICTS.items():
  39 | +        rs = runs.get(verdict) or []
  40 | +        if not rs:
  41 | +            raise ValueError(f"no {verdict} run: the floors cannot be measured")
  42 | +        fl[verdict] = {}
  43 | +        for p in parts:
  44 | +            vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]
  45 | +            if len(vals) != len(rs) or any(type(v) is not int for v in vals):
  46 | +                raise ValueError(f"a {verdict} run has no integer {p!r}: the floors cannot be measured")
  47 | +            fl[verdict][p] = min(vals)
  48 | +            if fl[verdict][p] < FLOOR_MIN:
  49 | +                low.append(f"{verdict} {p} {fl[verdict][p]} (stopped at {FLOOR_MIN})")
  50 | +                fl[verdict][p] = FLOOR_MIN
  51 | +    return fl, low
  52 | +
  53 | +
  54 | +def bar(versions, now=None, path=None):
  55 | +    """The live bar: {"rater", "sha256", "clips_alone": {...}, "coherence": {...}} when the calibration is sealed, for
  56 | +    exactly these prompt versions ({"clips_alone": v, "coherence": v}), not dated in the future, within its own valid_h,
  57 | +    and no floor under FLOOR_MIN; else (None, why): every verdict is then judged on the standard bar."""
  58 | +    cal, why = HB.load(path or PATH)
  59 | +    if cal is None:
  60 | +        return None, why.replace("hook calibration", "line-up calibration")
  61 | +    if not isinstance(cal.get("rater"), str) or not cal["rater"]:
  62 | +        return None, "the line-up calibration names no rater: refused"
  63 | +    for verdict, want in versions.items():
  64 | +        if (cal.get("question_versions") or {}).get(verdict) != want:
  65 | +            return None, (f"the line-up calibration is for {verdict}'s question version "
  66 | +                          f"{(cal.get('question_versions') or {}).get(verdict)!r}, not {want!r}: standard bar until it "
  67 | +                          f"is re-run")
  68 | +    try:
  69 | +        at = datetime.fromisoformat(str(cal["measured_at"]))
  70 | +        fl = {v: {p: int(cal["floors"][v][p]) for p in parts} for v, parts in VERDICTS.items()}
  71 | +    except (KeyError, TypeError, ValueError, OverflowError):
  72 | +        return None, "the line-up calibration has no readable measured_at or floors"
  73 | +    if at.tzinfo is None:
  74 | +        return None, "the line-up calibration's measured_at has no timezone: refused"
  75 | +    age = (now or datetime.now(timezone.utc)) - at
  76 | +    if age < -timedelta(minutes=HB.SKEW_MIN):
  77 | +        return None, f"the line-up calibration's measured_at ({cal['measured_at']}) is in the future: refused"
  78 | +    if "valid_h" not in cal:
  79 | +        return None, "the line-up calibration names no valid_h (hours, or null for none): refused"
  80 | +    vh = cal["valid_h"]
  81 | +    if vh is not None:
  82 | +        if type(vh) not in (int, float) or not 0 < vh <= HB.MAX_VALID_H:
  83 | +            return None, f"the line-up calibration's valid_h {vh!r} is not a number of hours in range: refused"
  84 | +        if age > timedelta(hours=vh):
  85 | +            return None, f"the line-up calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
  86 | +    if any(x < FLOOR_MIN for f in fl.values() for x in f.values()):
  87 | +        return None, f"a floor under {FLOOR_MIN} in the line-up calibration: refused"
  88 | +    return dict(fl, rater=cal["rater"], sha256=cal["sha256"], valid_h=vh), None
  89 | +
  90 | +
  91 | +def floors_for(verdict, backend, live, standard):
  92 | +    """(floors, "calibrated" | "standard") for one verdict given by `backend`: the calibrated floors only when the
  93 | +    calibrated rater gave it and the bar is live; else the standard floors."""
  94 | +    if live is not None and backend == live["rater"]:
  95 | +        return dict(live[verdict]), "calibrated"
  96 | +    return dict(standard[verdict]), "standard"
  97 | +
  98 | +
  99 | +def text(live):
 100 | +    if live is None:
 101 | +        return "no valid line-up calibration: the standard bar for every verdict"
 102 | +    c, k = live["clips_alone"], live["coherence"]
 103 | +    return (f"the calibrated line-up bar (ruling 116): clips-alone every clip >= {c['clip']}; coherence every clip >= "
 104 | +            f"{k['clip']} and the VO point >= {k['vo_point']}; on {live['rater']} only (calibration "
 105 | +            f"{live['sha256'][:12]})")
 106 | diff --git a/pipeline/lineup_calibration.json b/pipeline/lineup_calibration.json
 107 | new file mode 100644
 108 | index 0000000..205e249
 109 | --- /dev/null
 110 | +++ b/pipeline/lineup_calibration.json
 111 | @@ -0,0 +1,314 @@
 112 | +{
 113 | + "approved": {
 114 | +  "0c68b589": {
 115 | +   "clips_alone": [
 116 | +    {
 117 | +     "clips": {
 118 | +      "clip_01": 4,
 119 | +      "clip_02": 4
 120 | +     },
 121 | +     "flagged": [],
 122 | +     "passed_today": true,
 123 | +     "seed": 7,
 124 | +     "through_line": "Bitcoin provides financial freedom and security as a decentralized alternative to banks and governments that can mismanage or seize funds."
 125 | +    },
 126 | +    {
 127 | +     "clips": {
 128 | +      "clip_01": 4,
 129 | +      "clip_02": 4
 130 | +     },
 131 | +     "flagged": [],
 132 | +     "passed_today": true,
 133 | +     "seed": 8,
 134 | +     "through_line": "Bitcoin provides financial freedom and security by removing centralized control from governments, banks, and executives."
 135 | +    },
 136 | +    {
 137 | +     "clips": {
 138 | +      "clip_01": 4,
 139 | +      "clip_02": 4
 140 | +     },
 141 | +     "flagged": [],
 142 | +     "passed_today": true,
 143 | +     "seed": 9,
 144 | +     "through_line": "Bitcoin provides financial freedom and security by removing centralized control and risks from banks, governments, and single points of failure."
 145 | +    }
 146 | +   ],
 147 | +   "coherence": [
 148 | +    {
 149 | +     "clips": {
 150 | +      "clip_01": 5,
 151 | +      "clip_02": 3
 152 | +     },
 153 | +     "passed_today": false,
 154 | +     "seed": 7,
 155 | +     "through_line": "Bitcoin is not a partisan issue because no single owner or CEO controls its rules which are instead enforced by thousands of independent computers, providing financial freedom and liberty.",
 156 | +     "vo_point": 3
 157 | +    },
 158 | +    {
 159 | +     "clips": {
 160 | +      "clip_01": 4,
 161 | +      "clip_02": 3
 162 | +     },
 163 | +     "passed_today": false,
 164 | +     "seed": 8,
 165 | +     "through_line": "Bitcoin provides financial freedom and liberty because no single owner controls the network, with rules enforced by thousands of independent computers instead of a CEO, committee, or government.",
 166 | +     "vo_point": 3
 167 | +    },
 168 | +    {
 169 | +     "clips": {
 170 | +      "clip_01": 4,
 171 | +      "clip_02": 3
 172 | +     },
 173 | +     "passed_today": false,
 174 | +     "seed": 9,
 175 | +     "through_line": "No single owner controls the bitcoin network, making it a non-partisan provider of financial freedom and liberty unlike centralized banks.",
 176 | +     "vo_point": 4
 177 | +    }
 178 | +   ],
 179 | +   "label": "the published medley",
 180 | +   "pin": "ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
 181 | +   "story_id": "moments-ledger_20261113_183302-0c68b589"
 182 | +  },
 183 | +  "13949b7c": {
 184 | +   "clips_alone": [
 185 | +    {
 186 | +     "clips": {
 187 | +      "clip_01": 3,
 188 | +      "clip_02": 4
 189 | +     },
 190 | +     "flagged": [
 191 | +      "hook -> clip_01"
 192 | +     ],
 193 | +     "passed_today": false,
 194 | +     "seed": 7,
 195 | +     "through_line": "Bitcoin shows economic resilience compared to traditional assets and attracts flowing capital."
 196 | +    },
 197 | +    {
 198 | +     "clips": {
 199 | +      "clip_01": 4,
 200 | +      "clip_02": 3
 201 | +     },
 202 | +     "flagged": [
 203 | +      "hook -> clip_01"
 204 | +     ],
 205 | +     "passed_today": false,
 206 | +     "seed": 8,
 207 | +     "through_line": "Bitcoin shows economic resilience versus traditional assets by holding value better and attracting capital flows."
 208 | +    },
 209 | +    {
 210 | +     "clips": {
 211 | +      "clip_01": 4,
 212 | +      "clip_02": 4
 213 | +     },
 214 | +     "flagged": [],
 215 | +     "passed_today": true,
 216 | +     "seed": 9,
 217 | +     "through_line": "Bitcoin demonstrates economic resilience by outperforming traditional assets and attracting capital flows from stocks, treasuries, and industry."
 218 | +    }
 219 | +   ],
 220 | +   "coherence": [
 221 | +    {
 222 | +     "clips": {
 223 | +      "clip_01": 5,
 224 | +      "clip_02": 4
 225 | +     },
 226 | +     "passed_today": true,
 227 | +     "seed": 7,
 228 | +     "through_line": "Bitcoin is a maturing asset whose durability and resilience in surviving market cycles better than tech stocks earns trust and draws capital flows.",
 229 | +     "vo_point": 4
 230 | +    },
 231 | +    {
 232 | +     "clips": {
 233 | +      "clip_01": 5,
 234 | +      "clip_02": 4
 235 | +     },
 236 | +     "passed_today": true,
 237 | +     "seed": 8,
 238 | +     "through_line": "Bitcoin demonstrates maturation as a durable asset by showing greater resilience than tech stocks in market drops while attracting capital flows from treasuries and the industry.",
 239 | +     "vo_point": 4
 240 | +    },
 241 | +    {
 242 | +     "clips": {
 243 | +      "clip_01": 5,
 244 | +      "clip_02": 4
 245 | +     },
 246 | +     "passed_today": true,
 247 | +     "seed": 9,
 248 | +     "through_line": "Bitcoin demonstrates maturation as a resilient asset by outlasting tech stock volatility and attracting capital flows from treasuries and industry.",
 249 | +     "vo_point": 4
 250 | +    }
 251 | +   ],
 252 | +   "label": "the sealed medley (approved 17:14 ET Nov 13)",
 253 | +   "pin": "ledger_20261113_215708/MOMENTS_PIN_LEDGER.json",
 254 | +   "story_id": "moments-ledger_20261113_215708-13949b7c"
 255 | +  },
 256 | +  "37c5b5f5": {
 257 | +   "clips_alone": [
 258 | +    {
 259 | +     "clips": {
 260 | +      "clip_01": 4,
 261 | +      "clip_02": 5
 262 | +     },
 263 | +     "flagged": [],
 264 | +     "passed_today": true,
 265 | +     "seed": 7,
 266 | +     "through_line": "Bitcoin operates independently of government authorities, enabling a true global free market."
 267 | +    },
 268 | +    {
 269 | +     "clips": {
 270 | +      "clip_01": 4,
 271 | +      "clip_02": 5
 272 | +     },
 273 | +     "flagged": [],
 274 | +     "passed_today": true,
 275 | +     "seed": 8,
 276 | +     "through_line": "Bitcoin operates independently of government authority and politics, enabling a true global free market."
 277 | +    },
 278 | +    {
 279 | +     "clips": {
 280 | +      "clip_01": 4,
 281 | +      "clip_02": 5
 282 | +     },
 283 | +     "flagged": [],
 284 | +     "passed_today": true,
 285 | +     "seed": 9,
 286 | +     "through_line": "Bitcoin operates independently of government and political authority, enabling a voluntary global free market."
 287 | +    }
 288 | +   ],
 289 | +   "coherence": [
 290 | +    {
 291 | +     "clips": {
 292 | +      "clip_01": 5,
 293 | +      "clip_02": 4
 294 | +     },
 295 | +     "passed_today": true,
 296 | +     "seed": 7,
 297 | +     "through_line": "Bitcoin has no authority by design rather than flaw, enabling a rulerless global free market with fixed rules that cannot be bent.",
 298 | +     "vo_point": 4
 299 | +    },
 300 | +    {
 301 | +     "clips": {
 302 | +      "clip_01": 5,
 303 | +      "clip_02": 4
 304 | +     },
 305 | +     "passed_today": true,
 306 | +     "seed": 8,
 307 | +     "through_line": "Bitcoin has no authority by design rather than as a flaw, enabling a rulerless system with unbending rules and a global free market.",
 308 | +     "vo_point": 4
 309 | +    },
 310 | +    {
 311 | +     "clips": {
 312 | +      "clip_01": 5,
 313 | +      "clip_02": 4
 314 | +     },
 315 | +     "passed_today": true,
 316 | +     "seed": 9,
 317 | +     "through_line": "Bitcoin is designed without any central authority or ruler, which is a feature not a flaw as it enables unbending rules and a global free market independent of politicians.",
 318 | +     "vo_point": 4
 319 | +    }
 320 | +   ],
 321 | +   "label": "the moments reference",
 322 | +   "pin": "fresh_20261112_050611/MOMENTS_PIN.json",
 323 | +   "story_id": "moments-fresh_20261112_050611-37c5b5f5"
 324 | +  },
 325 | +  "41f29b1f": {
 326 | +   "clips_alone": [
 327 | +    {
 328 | +     "clips": {
 329 | +      "clip_01": 4,
 330 | +      "clip_02": 3
 331 | +     },
 332 | +     "flagged": [],
 333 | +     "passed_today": false,
 334 | +     "seed": 7,
 335 | +     "through_line": "Bitcoin enables a global free market independent of politics and is highly undervalued."
 336 | +    },
 337 | +    {
 338 | +     "clips": {
 339 | +      "clip_01": 4,
 340 | +      "clip_02": 4
 341 | +     },
 342 | +     "flagged": [],
 343 | +     "passed_today": true,
 344 | +     "seed": 8,
 345 | +     "through_line": "Bitcoin enables a global free market by operating independently of political control and is significantly undervalued."
 346 | +    },
 347 | +    {
 348 | +     "clips": {
 349 | +      "clip_01": 4,
 350 | +      "clip_02": 3
 351 | +     },
 352 | +     "flagged": [],
 353 | +     "passed_today": false,
 354 | +     "seed": 9,
 355 | +     "through_line": "Bitcoin enables a global free market by operating independently of governments and is highly undervalued."
 356 | +    }
 357 | +   ],
 358 | +   "coherence": [
 359 | +    {
 360 | +     "clips": {
 361 | +      "clip_01": 4,
 362 | +      "clip_02": 3
 363 | +     },
 364 | +     "passed_today": false,
 365 | +     "seed": 7,
 366 | +     "through_line": "Bitcoin's overlooked value comes from creating a free global market that no government owns or can control, making political factors irrelevant and the asset undervalued.",
 367 | +     "vo_point": 4
 368 | +    },
 369 | +    {
 370 | +     "clips": {
 371 | +      "clip_01": 4,
 372 | +      "clip_02": 4
 373 | +     },
 374 | +     "passed_today": true,
 375 | +     "seed": 8,
 376 | +     "through_line": "Bitcoin's overlooked value stems from it being a free global market priced by everyone but controlled by no government, making political drama irrelevant and the asset highly undervalued.",
 377 | +     "vo_point": 4
 378 | +    },
 379 | +    {
 380 | +     "clips": {
 381 | +      "clip_01": 5,
 382 | +      "clip_02": 4
 383 | +     },
 384 | +     "passed_today": true,
 385 | +     "seed": 9,
 386 | +     "through_line": "Bitcoin's overlooked value comes from creating a free global market that no government owns or can control, making it independent of political drama and significantly undervalued.",
 387 | +     "vo_point": 4
 388 | +    }
 389 | +   ],
 390 | +   "label": "the protected medley",
 391 | +   "pin": "fresh_20261112_050611/MOMENTS_PIN_LY.json",
 392 | +   "story_id": "moments-fresh_20261112_050611-41f29b1f"
 393 | +  }
 394 | + },
 395 | + "floors": {
 396 | +  "clips_alone": {
 397 | +   "clip": 3
 398 | +  },
 399 | +  "coherence": {
 400 | +   "clip": 3,
 401 | +   "vo_point": 3
 402 | +  }
 403 | + },
 404 | + "floors_below_3": [],
 405 | + "how": "package.medley / package.coherence as production asks them, on the four approved line-ups as sealed in their pins, the hook on its calibrated bar (ruling 115), seeds 7, 8, 9",
 406 | + "joins_note": "at most one flagged join stays (L-y 2: one bridge); no approved line-up had more",
 407 | + "measured_at": "2026-11-15T20:31:20+00:00",
 408 | + "question_versions": {
 409 | +  "clips_alone": "0d410578ad75",
 410 | +  "coherence": "39e821a734ec"
 411 | + },
 412 | + "rater": "xai:grok-4.20-0309-reasoning",
 413 | + "seeds": [
 414 | +  7,
 415 | +  8,
 416 | +  9
 417 | + ],
 418 | + "sha256": "02440fd4e0c570fdd539938e141ec1cb0ef6549c9d37efbb8cb673387123fa11",
 419 | + "source": [
 420 | +  "tests/package/proof/clips116/CALIBRATION.json",
 421 | +  "tests/package/proof/clips116/COHERENCE.json"
 422 | + ],
 423 | + "valid_h": null,
 424 | + "valid_h_note": "ruling 116 (Q3, applied the hook's way, ruling 115): the floors come from ONE fixed source, tests/package/proof/clips116/ (CALIBRATION.json, COHERENCE.json), so they do not expire"
 425 | +}
 426 | diff --git a/pipeline/package.py b/pipeline/package.py
 427 | index 1afb4a7..86d702f 100644
 428 | --- a/pipeline/package.py
 429 | +++ b/pipeline/package.py
 430 | @@ -1011,6 +1011,11 @@ rated here, its own job was judged on its own).
 431 |  3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
 432 |     1 = no point, or a point the clips do not support).
 433 |  Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "vo_point": 1}}"""
 434 | +MEDLEY_VERSION = hashlib.sha256(MEDLEY_PROMPT.encode()).hexdigest()[:12]         # RULING 116: the line-up bar is
 435 | +COHERENCE_VERSION = hashlib.sha256(COHERENCE_PROMPT.encode()).hexdigest()[:12]   # valid for exactly these questions
 436 | +STANDARD_LINEUP = {"clips_alone": {"clip": COHERENCE_MIN}, "coherence": {"clip": COHERENCE_MIN,
 437 | +                                                                         "vo_point": COHERENCE_MIN}}
 438 | +#   the standard bar: every verdict not given by the calibrated rater, and every verdict while the file is invalid
 439 |  
 440 |  
 441 |  def current_levels(sources, ctx, hours=24.0):
 442 | @@ -1439,6 +1444,43 @@ def _live_bar():
 443 |      return _LIVE[k]
 444 |  
 445 |  
 446 | +_LIVE_LINEUP = {}
 447 | +
 448 | +
 449 | +def _live_lineup_bar():
 450 | +    """RULING 116: the calibrated line-up bar (lineup_bar.bar for this build's two prompt versions), read once per state
 451 | +    of its file and per minute, like the hook's."""
 452 | +    import lineup_bar as LB
 453 | +    try:
 454 | +        k = (os.stat(LB.PATH).st_mtime_ns, int(time.time() // 60))
 455 | +    except OSError:
 456 | +        k = (None, int(time.time() // 60))
 457 | +    if k not in _LIVE_LINEUP:
 458 | +        _LIVE_LINEUP.clear()
 459 | +        _LIVE_LINEUP[k] = LB.bar({"clips_alone": MEDLEY_VERSION, "coherence": COHERENCE_VERSION})
 460 | +    return _LIVE_LINEUP[k]
 461 | +
 462 | +
 463 | +def lineup_floors(verdict, backend):
 464 | +    """RULING 116: (floors, which bar, the calibration's sha or None) for one line-up verdict given by `backend`: the
 465 | +    calibrated floors only when the calibrated rater gave it; else the standard bar (STANDARD_LINEUP)."""
 466 | +    import lineup_bar as LB
 467 | +    live, _ = _live_lineup_bar()
 468 | +    fl, which = LB.floors_for(verdict, backend, live, STANDARD_LINEUP)
 469 | +    return fl, which, (live or {}).get("sha256") if which == "calibrated" else None
 470 | +
 471 | +
 472 | +def lineup_bar_mark(med, coh):
 473 | +    """RULING 116 (Q3): what a package whose clips-alone AND coherence verdicts both passed on the calibrated bar carries
 474 | +    in its record and pin (outside the seal): the plain line, each verdict's floors and the calibration's sha, as they
 475 | +    were when it was judged. None when either verdict was judged on the standard bar."""
 476 | +    import lineup_bar as LB
 477 | +    if (med or {}).get("bar") != "calibrated" or (coh or {}).get("bar") != "calibrated":
 478 | +        return None
 479 | +    return {"note": LB.NOTE, "floors": {"clips_alone": med.get("floors"), "coherence": coh.get("floors")},
 480 | +            "calibration_sha256": med.get("calibration_sha256"), "ruling": "116"}
 481 | +
 482 | +
 483 |  def hook_bar_mark(live=None):
 484 |      """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
 485 |      the plain line for the Telegram note, the floors and the calibration's sha. `live`: the bar the build judged its
 486 | @@ -1764,10 +1806,12 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 487 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 488 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 489 |                                                       "fail closed"})
 490 | +    fl, which, csha = lineup_floors("coherence", r.backend)    # RULING 116: the calibrated rater's floors, or standard
 491 |      ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 492 | -        min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN   # ruling 115:
 493 | -    #   the hook's slot is its calibrated bar, every clip after it and the VO point COHERENCE_MIN, as before
 494 | -    return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 495 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and v["vo_point"] >= fl["vo_point"]
 496 | +    #   ruling 115: the hook's slot is its calibrated bar; the clips after it and the VO point the line-up bar's
 497 | +    return ok, dict(v, backend=r.backend, measured=True, bar=which, floors=fl, calibration_sha256=csha,
 498 | +                    replayed=bool(getattr(r, "replayed", False)))
 499 |  
 500 |  
 501 |  def _lineup_block(segs, ctx, a_by):
 502 | @@ -1826,11 +1870,13 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 503 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 504 |                                                       "fail closed"})
 505 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
 506 | +    fl, which, csha = lineup_floors("clips_alone", r.backend)   # RULING 116: the calibrated rater's floors, or standard
 507 |      ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 508 | -        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 509 | -    #   ruling 115: the hook's slot is its calibrated bar; every clip after it COHERENCE_MIN, as before
 510 | -    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 511 | -                    replayed=bool(getattr(r, "replayed", False)), cached=bool(getattr(r, "cached", False)))
 512 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and len(flagged) <= LY_MAX_BRIDGES
 513 | +    #   ruling 115: the hook's slot is its calibrated bar; every clip after it the line-up bar's floor (ruling 116)
 514 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True, bar=which, floors=fl,
 515 | +                    calibration_sha256=csha, replayed=bool(getattr(r, "replayed", False)),
 516 | +                    cached=bool(getattr(r, "cached", False)))
 517 |  
 518 |  
 519 |  def last_clip_only(segs, med):
 520 | @@ -1844,7 +1890,8 @@ def last_clip_only(segs, med):
 521 |          return False
 522 |      rest = [j for j in med.get("flagged") or [] if j != joins(labs)[-1]]
 523 |      own = hook_own(segs[0])                              # ruling 115: the hook passes by its calibrated bar
 524 | -    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < COHERENCE_MIN] \
 525 | +    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]   # ruling 116: the verdict's own bar
 526 | +    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < floor] \
 527 |          == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 528 |  
 529 |  
 530 | @@ -3167,8 +3214,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 531 |                          rec["why"] = (f"ruling 62: only the last clip fails ({cl.get(labs[-1])}): retried without it, "
 532 |                                        f"the seconds floor still met, before any swap")
 533 |                          continue
 534 | +                    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]   # ruling 116
 535 |                      if med.get("measured") and _line_ok(med.get("through_line")) and labs[0] in cl and \
 536 | -                            min(cl.values()) >= COHERENCE_MIN and len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 537 | +                            (med.get("hook_own") or {}).get("passes") is True and \
 538 | +                            min(x for lb, x in cl.items() if lb != labs[0]) >= floor and \
 539 | +                            len(med.get("flagged") or []) > LY_MAX_BRIDGES:   # ruling 115: the hook's slot is its bar
 540 |                          order = reorder(segs, bad_pairs, judged, repeat_ok=exception is not None)
 541 |                          if order is not None:                 # RULING 63: joins before swaps
 542 |                              swapped = order
 543 | @@ -3176,10 +3226,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 544 |                                            f"flagged: the same clips reordered, before any swap")
 545 |                              continue
 546 |                      weak = {by_lab[lb]["moment_id"] for lb, x in cl.items()
 547 | -                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 61: the hook's is its cached rating
 548 | +                            if lb in by_lab and x < floor}      # ruling 116: the verdict's own floor
 549 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 550 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 551 | -                    hook_weak = segs[0]["moment_id"] in weak
 552 | +                    hook_weak = (med.get("hook_own") or {}).get("passes") is not True   # ruling 115: its own bar
 553 |                      weak.discard(segs[0]["moment_id"])    # ruling 59 (c): the line-up is built AROUND its hook
 554 |                      if not med.get("measured") or not weak:
 555 |                          rec["why"] = ("the hook carries no own-job rating at the bar (ruling 61); the angle is written "
 556 | @@ -3480,9 +3530,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 557 |                                              last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 558 |                      if not ok_c:
 559 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 560 | +                        cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 561 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 562 | -                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 563 | -                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 564 | +                                coh["vo_point"] < cfl["vo_point"] and (coh.get("hook_own") or {}).get("passes") is True \
 565 | +                                and min(x for lb, x in coh["clips"].items() if lb != "hook") >= cfl["clip"] and \
 566 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):   # ruling 115: the hook's slot
 567 |                              take_failed += 1                  # the takeaway's point failed its coherence gate
 568 |                              extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 569 |                                              f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 570 | @@ -3493,7 +3545,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 571 |                              t_alone, last_fid, last_rw65 = True, fid, bool(att.get("rewrite"))
 572 |                              continue                          # the clips hold; only the takeaway's point is weak
 573 |                          weak = {sg["moment_id"] for sg in pk["segments"][1:]
 574 | -                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 575 | +                                if (coh.get("clips") or {}).get(sg["label"], cfl["clip"]) < cfl["clip"]}
 576 |                          dropped |= weak
 577 |                          relined = bool(weak)
 578 |                          rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 579 | @@ -3546,6 +3598,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 580 |      out["package"] = out["packages"][0] if out["packages"] else None
 581 |      if out["package"]:                                   # RULING 115 (2): a package sealed on the calibrated bar says so
 582 |          out["package"]["hook_bar"] = hook_bar_mark(live)   # the bar its hooks were judged on (the hook stage's)
 583 | +        lm = lineup_bar_mark(*(lambda c: (c.get("medley"), c.get("coherence")))(out["package"].get("checks") or {}))
 584 | +        if lm:                                           # RULING 116 (Q3): and its line-up, when both verdicts were
 585 | +            out["package"]["lineup_bar"] = lm            # judged on the calibrated line-up bar
 586 |      if candidate is not None:                             # RULING 66: what became of the candidate
 587 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 588 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 589 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 590 | index 03990bc..99f6cae 100644
 591 | --- a/pipeline/package_pin.py
 592 | +++ b/pipeline/package_pin.py
 593 | @@ -497,6 +497,8 @@ def to_pin(pk, run_name):
 594 |                                  "gates": pk["gates"],
 595 |                                  **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 596 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 597 | +                                **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 598 | +                                #   the line-up's, when both its verdicts passed on the calibrated bar (outside the seal)
 599 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 600 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 601 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 602 | diff --git a/tests/package/conftest.py b/tests/package/conftest.py
 603 | index 0e67912..09cdbb7 100644
 604 | --- a/tests/package/conftest.py
 605 | +++ b/tests/package/conftest.py
 606 | @@ -3,7 +3,9 @@ PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (sc
 607 |  rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
 608 |  verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
 609 |  tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
 610 | -class that needs production's calibration file sets `real_hook_bar = True`."""
 611 | +class that needs production's calibration file sets `real_hook_bar = True`. RULING 116: the same for the line-up bar
 612 | +(package._live_lineup_bar): RIG_LINEUP's floors (every clip after the hook >= 3, the VO point >= 3) for the rigs'
 613 | +rater, so a rig verdict given as "xai:grok" is judged on the calibrated bar and any other back-end on the standard."""
 614 |  import os
 615 |  import sys
 616 |  
 617 | @@ -15,6 +17,7 @@ import package as PK  # noqa: E402
 618 |  
 619 |  RIG_RATER = "xai:grok"
 620 |  RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}
 621 | +RIG_LINEUP = {"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}}   # RULING 116's floors, pinned
 622 |  
 623 |  
 624 |  def rig_bar():
 625 | @@ -22,11 +25,16 @@ def rig_bar():
 626 |              "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}
 627 |  
 628 |  
 629 | +def rig_lineup_bar():
 630 | +    return dict({k: dict(v) for k, v in RIG_LINEUP.items()}, rater=RIG_RATER, sha256="l" * 64, valid_h=None)
 631 | +
 632 | +
 633 |  @pytest.fixture(autouse=True)
 634 |  def _rig_hook_bar(request, monkeypatch):
 635 |      if getattr(request.cls, "real_hook_bar", False):
 636 |          yield
 637 |          return
 638 | -    bar = rig_bar()
 639 | +    bar, lbar = rig_bar(), rig_lineup_bar()
 640 |      monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
 641 | +    monkeypatch.setattr(PK, "_live_lineup_bar", lambda: (lbar, None))   # ruling 116: the rigs' line-up bar
 642 |      yield
 643 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 644 | index 881884a..e4d2206 100644
 645 | --- a/tests/package/proof_ledger.py
 646 | +++ b/tests/package/proof_ledger.py
 647 | @@ -452,6 +452,9 @@ def main(argv=None):
 648 |      live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 649 |      say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
 650 |          + (f" [{live_why}]" if live_why else ""))
 651 | +    import lineup_bar as LNB                     # RULING 116: the line-up bar, named in every build line too
 652 | +    lbar, lbar_why = PK._live_lineup_bar()
 653 | +    say(f"  RULING 116: {LNB.text(lbar)}" + (f" [{lbar_why}]" if lbar_why else ""))
 654 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 655 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 656 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 657 | diff --git a/tests/package/test_lineup_bar.py b/tests/package/test_lineup_bar.py
 658 | new file mode 100644
 659 | index 0000000..86a63d3
 660 | --- /dev/null
 661 | +++ b/tests/package/test_lineup_bar.py
 662 | @@ -0,0 +1,158 @@
 663 | +#!/usr/bin/env python3
 664 | +"""RULING 116 (Q3, ruling 106's default APPLY): THE CALIBRATED LINE-UP BAR (pipeline/lineup_bar.py). Each verdict's
 665 | +parts (clips-alone: every clip after the hook; coherence: every clip after the hook and the VO point) are at least the
 666 | +lowest value they took on PBX's four approved line-ups (seeds 7, 8, 9, Grok), never under 3; ONLY for a verdict the
 667 | +calibrated rater gave; every other verdict, and every verdict while the file is invalid, stays on the standard bar."""
 668 | +import copy
 669 | +import json
 670 | +import os
 671 | +import sys
 672 | +import tempfile
 673 | +import unittest
 674 | +from datetime import datetime, timedelta, timezone
 675 | +
 676 | +HERE = os.path.dirname(os.path.abspath(__file__))
 677 | +REPO = os.path.dirname(os.path.dirname(HERE))
 678 | +for _p in ("pipeline", "tests/package"):
 679 | +    sys.path.insert(0, os.path.join(REPO, _p))
 680 | +import hook_bar as HB  # noqa: E402
 681 | +import lineup_bar as LB  # noqa: E402
 682 | +import package as PK  # noqa: E402
 683 | +import package_pin as PP  # noqa: E402
 684 | +
 685 | +AT = datetime(2026, 11, 15, 20, 33, 0, tzinfo=timezone.utc)
 686 | +G = "xai:grok-4.20-0309-reasoning"
 687 | +V = {"clips_alone": "mv", "coherence": "cv"}
 688 | +
 689 | +
 690 | +def runs(ca=((4, 3), (4, 4)), co=(((5, 3), 3), ((4, 4), 4))):
 691 | +    return {"clips_alone": [{"clips": {"clip_01": a, "clip_02": b}} for a, b in ca],
 692 | +            "coherence": [{"clips": {"clip_01": a, "clip_02": b}, "vo_point": v} for (a, b), v in co]}
 693 | +
 694 | +
 695 | +def cal(**kw):
 696 | +    fl, low = LB.floors_from(runs())
 697 | +    return dict({"rater": G, "question_versions": dict(V), "measured_at": AT.isoformat(), "valid_h": None,
 698 | +                 "floors": fl, "floors_below_3": low}, **kw)
 699 | +
 700 | +
 701 | +class TestFloors(unittest.TestCase):
 702 | +    def test_each_part_is_its_lowest_value_never_under_3(self):
 703 | +        self.assertEqual(LB.floors_from(runs()), ({"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}},
 704 | +                                                  []))
 705 | +        fl, low = LB.floors_from(runs(ca=((4, 4), (5, 4)), co=(((5, 4), 4), ((4, 4), 5))))
 706 | +        self.assertEqual(fl, {"clips_alone": {"clip": 4}, "coherence": {"clip": 4, "vo_point": 4}})
 707 | +        fl, low = LB.floors_from(runs(ca=((2, 4),), co=(((4, 4), 1),)))
 708 | +        self.assertEqual((fl["clips_alone"]["clip"], fl["coherence"]["vo_point"]), (3, 3))
 709 | +        self.assertEqual(low, ["clips_alone clip 2 (stopped at 3)", "coherence vo_point 1 (stopped at 3)"])
 710 | +
 711 | +    def test_a_run_without_its_ratings_measures_nothing(self):
 712 | +        for bad in ({"clips_alone": [], "coherence": runs()["coherence"]},
 713 | +                    dict(runs(), coherence=[{"clips": {"clip_01": 4}}]),
 714 | +                    dict(runs(), clips_alone=[{"clips": {}}])):
 715 | +            with self.assertRaises(ValueError):
 716 | +                LB.floors_from(bad)
 717 | +
 718 | +
 719 | +class TestTheFile(unittest.TestCase):
 720 | +    def setUp(self):
 721 | +        self.d = tempfile.TemporaryDirectory()
 722 | +        self.path = os.path.join(self.d.name, "lineup_calibration.json")
 723 | +
 724 | +    def tearDown(self):
 725 | +        self.d.cleanup()
 726 | +
 727 | +    def test_valid_only_sealed_for_its_versions_and_rater_and_within_its_validity(self):
 728 | +        HB.write(cal(), self.path)
 729 | +        live, why = LB.bar(V, now=AT + timedelta(days=30), path=self.path)          # valid_h null: no expiry
 730 | +        self.assertEqual((live["clips_alone"], live["coherence"], live["rater"], why),
 731 | +                         ({"clip": 3}, {"clip": 3, "vo_point": 3}, G, None))
 732 | +        self.assertIn("clips-alone every clip >= 3; coherence every clip >= 3 and the VO point >= 3", LB.text(live))
 733 | +        for k, v in (("clips_alone", "another"), ("coherence", "another")):
 734 | +            live, why = LB.bar(dict(V, **{k: v}), now=AT, path=self.path)
 735 | +            self.assertIsNone(live)
 736 | +            self.assertIn("standard bar until it is re-run", why)
 737 | +        bad = (cal(rater=""), cal(valid_h=24), cal(measured_at="2026-11-15T20:33:00"),
 738 | +               cal(floors={"clips_alone": {"clip": 2}, "coherence": {"clip": 3, "vo_point": 3}}))
 739 | +        for c in bad:
 740 | +            HB.write(c, self.path)
 741 | +            self.assertIsNone(LB.bar(V, now=AT + timedelta(days=2), path=self.path)[0], c.get("valid_h"))
 742 | +        c = cal()
 743 | +        del c["valid_h"]
 744 | +        HB.write(c, self.path)
 745 | +        self.assertIn("names no valid_h", LB.bar(V, now=AT, path=self.path)[1])
 746 | +        HB.write(cal(), self.path)
 747 | +        live, why = LB.bar(V, now=AT - timedelta(minutes=6), path=self.path)
 748 | +        self.assertIn("in the future", why)
 749 | +        with open(self.path) as f:
 750 | +            body = json.load(f)
 751 | +        body["floors"]["clips_alone"]["clip"] = 2                                 # a hand edit: the seal breaks
 752 | +        with open(self.path, "w") as f:
 753 | +            json.dump(body, f)
 754 | +        self.assertIsNone(LB.bar(V, now=AT, path=self.path)[0])
 755 | +
 756 | +    def test_the_floors_only_for_the_calibrated_raters_own_verdict(self):
 757 | +        HB.write(cal(), self.path)
 758 | +        live, _ = LB.bar(V, now=AT, path=self.path)
 759 | +        std = PK.STANDARD_LINEUP
 760 | +        self.assertEqual(LB.floors_for("coherence", G, live, std), ({"clip": 3, "vo_point": 3}, "calibrated"))
 761 | +        self.assertEqual(LB.floors_for("coherence", "heimdall:deepseek/deepseek-v4.1-flash", live, std),
 762 | +                         ({"clip": 4, "vo_point": 4}, "standard"))
 763 | +        self.assertEqual(LB.floors_for("clips_alone", G, None, std), ({"clip": 4}, "standard"))   # no valid bar
 764 | +
 765 | +
 766 | +class TestTheMark(unittest.TestCase):
 767 | +    """Q3: a package whose two verdicts both passed on the calibrated bar says so in its record and pin, outside the
 768 | +    seal; one judged on the standard bar carries no mark."""
 769 | +
 770 | +    def test_both_verdicts_calibrated_or_no_mark_and_the_pin_carries_it_outside_the_seal(self):
 771 | +        import test_angles as TA
 772 | +        med = {"bar": "calibrated", "floors": {"clip": 3}, "calibration_sha256": "l" * 64}
 773 | +        coh = {"bar": "calibrated", "floors": {"clip": 3, "vo_point": 3}, "calibration_sha256": "l" * 64}
 774 | +        m = PK.lineup_bar_mark(med, coh)
 775 | +        self.assertEqual((m["note"], m["floors"], m["ruling"]),
 776 | +                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
 777 | +                                                                   "coherence": {"clip": 3, "vo_point": 3}}, "116"))
 778 | +        self.assertIsNone(PK.lineup_bar_mark(dict(med, bar="standard"), coh))
 779 | +        self.assertIsNone(PK.lineup_bar_mark(med, None))
 780 | +        base = TA.TestPinAndTruth.pk(None)
 781 | +        plain = PP.to_pin(copy.deepcopy(base), "r")["moments_package"]
 782 | +        marked = PP.to_pin(dict(copy.deepcopy(base), lineup_bar=m), "r")["moments_package"]
 783 | +        self.assertNotIn("lineup_bar", plain)
 784 | +        self.assertEqual(marked["lineup_bar"]["note"], "line-up passed on the calibrated bar")
 785 | +        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal
 786 | +
 787 | +
 788 | +class TestTheLiveCalibration(unittest.TestCase):
 789 | +    """The file production reads (pipeline/lineup_calibration.json): its floors derive from their source
 790 | +    (tests/package/proof/clips116/), it is valid for production's two prompts, its rater is the first of both
 791 | +    verdicts' production lists, and it does not expire."""
 792 | +    real_hook_bar = True
 793 | +
 794 | +    def test_its_floors_are_its_sources_lowest_ratings(self):
 795 | +        c, why = HB.load(LB.PATH)
 796 | +        self.assertIsNone(why)
 797 | +        proof = os.path.join(REPO, "tests", "package", "proof", "clips116")
 798 | +        with open(os.path.join(proof, "CALIBRATION.json")) as f:
 799 | +            ca = json.load(f)
 800 | +        with open(os.path.join(proof, "COHERENCE.json")) as f:
 801 | +            co = json.load(f)
 802 | +        src = {"clips_alone": [r for x in ca["lineups"].values() for r in x["runs"]],
 803 | +               "coherence": [r for x in co["packages"].values() for r in x["runs"]]}
 804 | +        self.assertTrue(all(r.get("backend") == c["rater"] for v in src.values() for r in v))
 805 | +        self.assertEqual(LB.floors_from(src), (c["floors"], c["floors_below_3"]))
 806 | +        self.assertEqual(max(len(r["flagged"]) for r in src["clips_alone"]), PK.LY_MAX_BRIDGES)   # joins: the law's
 807 | +
 808 | +    def test_it_is_live_for_production_and_does_not_expire(self):
 809 | +        import providers as P
 810 | +        c, _ = HB.load(LB.PATH)
 811 | +        versions = {"clips_alone": PK.MEDLEY_VERSION, "coherence": PK.COHERENCE_VERSION}
 812 | +        live, why = LB.bar(versions, now=datetime.fromisoformat(c["measured_at"]) + timedelta(days=30))
 813 | +        self.assertEqual((live is not None, why), (True, None))
 814 | +        r = P.Router(env_path="/nonexistent", routing="heimdall_first")
 815 | +        for kind in ("clips_alone", "coherence"):
 816 | +            self.assertEqual(r.chain("coherence_verdict", kind)[0], c["rater"], kind)
 817 | +
 818 | +
 819 | +if __name__ == "__main__":
 820 | +    unittest.main()
 821 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 822 | index 33db082..62c59db 100644
 823 | --- a/tests/package/test_medley.py
 824 | +++ b/tests/package/test_medley.py
 825 | @@ -552,8 +552,9 @@ class Rig:
 826 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 827 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 828 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 829 | -                 real_value=False, caption=None):
 830 | +                 real_value=False, caption=None, coherences=None):
 831 |          import providers as P
 832 | +        self.coherences = list(coherences or [])         # RULING 116: (ok, every clip's rating, the VO point) in order
 833 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 834 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 835 |          self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
 836 | @@ -630,14 +631,33 @@ class Rig:
 837 |                                     "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 838 |          return out, None
 839 |  
 840 | +    def coherence(self, router, pk, *a, **k):
 841 | +        """As the real coherence() answers: the clips after the hook and the VO point (self.coherences, default all 5
 842 | +        and a pass), the hook's slot its own rating, and the line-up bar it was judged on (ruling 116)."""
 843 | +        own = PK.hook_own(k.get("hook"))
 844 | +        ok, clip, vo = self.coherences.pop(0) if self.coherences else (True, 5, 5)
 845 | +        fl, which, csha = PK.lineup_floors("coherence", "xai:grok")
 846 | +        segs = pk["segments"]
 847 | +        return ok, {"through_line": "Nobody gets to bend the rules.",
 848 | +                    "clips": dict({segs[0]["label"]: (own or {}).get("rating")}, **{sg["label"]: clip for sg in segs[1:]}),
 849 | +                    "vo_point": vo, "backend": "xai:grok", "measured": True, "replayed": False,
 850 | +                    "hook_own": own or {"rating": None}, "floors": fl, "bar": which, "calibration_sha256": csha}
 851 | +
 852 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 853 | +        """As the real medley() answers: the verdict, its flagged joins, the hook's own-job record (ruling 115) and
 854 | +        the line-up bar it was judged on (ruling 116: the rigs' rater, so the calibrated floors)."""
 855 |          self.medley_calls.append([m["moment_id"] for m in segs])
 856 |          self.seeds.append(("medley", seed))
 857 |          ok, flagged, ratings, line = self.medleys.pop(0)
 858 |          labs = PK.labels(len(segs))
 859 |          v = verdict(labs, flagged, ratings, line)
 860 | +        own = PK.hook_own(segs[0])
 861 | +        if "hook" not in (ratings or {}):                  # the hook's slot holds its own rating, as medley() writes it
 862 | +            v["clips"]["hook"] = (own or {}).get("rating")
 863 | +        fl, which, csha = PK.lineup_floors("clips_alone", "xai:grok")
 864 |          return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False,
 865 | -                        cached=self.cached)
 866 | +                        cached=self.cached, hook_own=own or {"rating": None},
 867 | +                        bar=which, floors=fl, calibration_sha256=csha)
 868 |  
 869 |      def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 870 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
 871 | @@ -709,10 +729,7 @@ class Rig:
 872 |              "hook_onset_for": self.onset,
 873 |              "hook_ratings": self.rate_hooks,
 874 |              "takeaway_value": self.value,                  # ruling 91 (medley half)
 875 | -            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 876 | -                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
 877 | -                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
 878 | -                                                             "replayed": False}),
 879 | +            "coherence": self.coherence,
 880 |          }
 881 |          if self.real_value:                                # ruling 91: the real verdict, on the fake router
 882 |              del stubs["takeaway_value"]
 883 | @@ -1583,6 +1600,115 @@ class TestRuling59HookFirst(unittest.TestCase):
 884 |          self.assertEqual(rig.medley_calls, [])
 885 |  
 886 |  
 887 | +class TestRuling116LineupBar(unittest.TestCase):
 888 | +    """RULING 116 (Q3, ruling 106's default APPLY): the clips-alone and coherence verdicts judged on the calibrated
 889 | +    line-up bar (the rigs': every clip after the hook >= 3, the VO point >= 3) when the calibrated rater gave them, on
 890 | +    the standard bar (>= 4) otherwise; the hook's slot is its own bar everywhere (ruling 115)."""
 891 | +    LABS = ["hook", "clip_01", "clip_02"]
 892 | +    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
 893 | +            pm("x", "B", 14.0), pm("y", "C", 13.0)]
 894 | +
 895 | +    @staticmethod
 896 | +    def router(reply, backend):
 897 | +        import providers as P
 898 | +        r = Canned(coherence_verdict=[reply])
 899 | +        call = r.call
 900 | +
 901 | +        def as_backend(role, *a, **k):
 902 | +            x = call(role, *a, **k)
 903 | +            return P.Reply(x.text, backend, backend.split(":")[0])
 904 | +        r.call = as_backend
 905 | +        return r
 906 | +
 907 | +    def test_clips_alone_a_clip_at_3_passes_only_on_the_calibrated_raters_verdict(self):
 908 | +        rep = reply(self.LABS, ratings={"clip_02": 3})
 909 | +        ok, v = PK.medley(self.router(rep, "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 910 | +        self.assertEqual((ok, v["bar"], v["floors"], v["clips"]["hook"]), (True, "calibrated", {"clip": 3}, 3))
 911 | +        ok, v = PK.medley(self.router(rep, "google:gemini-2.5-pro"), self.SEGS, E.Context(NOW, REG), set())
 912 | +        self.assertEqual((ok, v["bar"], v["floors"]), (False, "standard", {"clip": 4}))     # Plan B: the standard bar
 913 | +        ok, v = PK.medley(self.router(reply(self.LABS, ratings={"clip_02": 2}), "xai:grok"), self.SEGS,
 914 | +                          E.Context(NOW, REG), set())
 915 | +        self.assertFalse(ok)                                                             # under the floor
 916 | +        ok, v = PK.medley(self.router(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]),
 917 | +                                      "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 918 | +        self.assertFalse(ok)                                                             # joins: the law's one
 919 | +        ok, v = PK.medley(self.router(reply(self.LABS, line="none"), "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 920 | +        self.assertFalse(ok)                                                             # a through-line, always
 921 | +
 922 | +    def test_coherence_a_clip_or_vo_point_at_3_passes_only_on_the_calibrated_raters_verdict(self):
 923 | +        pk = {"title": "t", "caption": "c", "vo": {"intro": None, "bridges": ["No ruler, just rules."],
 924 | +                                                  "bridges_after_clip": [2], "signoff": "S"},
 925 | +              "segments": [{"label": lb, "channel": ch, "text": f"Bitcoin {lb}."}
 926 | +                           for lb, ch in zip(self.LABS, "ABC")]}
 927 | +        rep = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 3, "clip_02": 4},
 928 | +               "vo_point": 3}
 929 | +        ok, v = PK.coherence(self.router(rep, "xai:grok"), pk, set(), hook=self.SEGS[0])
 930 | +        self.assertEqual((ok, v["bar"], v["floors"]), (True, "calibrated", {"clip": 3, "vo_point": 3}))
 931 | +        ok, v = PK.coherence(self.router(rep, "heimdall:deepseek/deepseek-v4.1-flash"), pk, set(), hook=self.SEGS[0])
 932 | +        self.assertEqual((ok, v["bar"]), (False, "standard"))
 933 | +        ok, v = PK.coherence(self.router(dict(rep, vo_point=2), "xai:grok"), pk, set(), hook=self.SEGS[0])
 934 | +        self.assertFalse(ok)
 935 | +
 936 | +    def test_ruling_62_reads_the_verdicts_own_floor(self):
 937 | +        segs = self.SEGS + [pm("z", "D", 9.0)]
 938 | +        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_01": 3, "clip_02": 3, "clip_03": 2}),
 939 | +                   measured=True, flagged=[], floors={"clip": 3})
 940 | +        self.assertTrue(PK.last_clip_only(segs, med))                                   # only the last under 3
 941 | +        self.assertFalse(PK.last_clip_only(segs, dict(med, floors={"clip": 4})))        # the standard bar: all fail
 942 | +        self.assertFalse(PK.last_clip_only(segs, {k: x for k, x in med.items() if k != "floors"}))   # no floors: 4
 943 | +
 944 | +    def test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors(self):
 945 | +        """The hook's own rating (3, at its floors) never blocks ruling 63: the clips after it pass and two joins
 946 | +        are flagged, so the same clips are reordered (before ruling 115 / 116 the hook's 3 sat in the min)."""
 947 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 948 | +        from unittest import mock
 949 | +        for bar in ("calibrated", "standard"):            # the standard bar's floor 4 is where the hook's 3 blocked
 950 | +            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
 951 | +                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
 952 | +                rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
 953 | +                                                (True, [], None, Rig.LINE)], [None], hooks={"h": (3, 4, 3)})
 954 | +                out = rig.run()
 955 | +            self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "x"]], bar)
 956 | +            self.assertIn("ruling 63", out["tried"][0]["why"], bar)
 957 | +            self.assertIsNotNone(out["package"], bar)
 958 | +
 959 | +    def test_the_takeaway_alone_is_rewritten_when_only_its_point_is_weak_with_a_hook_at_its_floors(self):
 960 | +        """Coherence fails on the VO point alone (2), the clips pass the calibrated floor and the hook sits at its
 961 | +        floors (rating 3): the takeaway is written again (it was the next angle while the hook's 3 sat in the min)."""
 962 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 963 | +        from unittest import mock
 964 | +        for bar, clip in (("calibrated", 3), ("standard", 4)):   # the standard bar's 4: the hook's 3 blocked it
 965 | +            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
 966 | +                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
 967 | +                rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None, None], hooks={"h": (3, 4, 3)},
 968 | +                          coherences=[(False, clip, 2), (True, 4, 4)])
 969 | +                out = rig.run()
 970 | +            self.assertEqual(len(rig.write_calls), 2, bar)                               # the takeaway again
 971 | +            self.assertIsNotNone(out["package"], bar)
 972 | +
 973 | +    def test_after_a_failed_verdict_only_the_clips_under_its_own_floor_are_swapped(self):
 974 | +        """A clip at 3 passes the calibrated floor: when the line-up fails on another clip (2), only that one is
 975 | +        dropped and swapped, never the clip at 3."""
 976 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 977 | +        rig = Rig(ms, ["h", "x", "y"], [(False, [], {"clip_01": 3, "clip_02": 2}, Rig.LINE)], [None])
 978 | +        out = rig.run()
 979 | +        self.assertIn("dropped ['y']", out["tried"][0]["why"])
 980 | +
 981 | +    def test_the_mark_on_a_package_whose_two_verdicts_passed_on_the_calibrated_bar(self):
 982 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 983 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
 984 | +        out = rig.run()
 985 | +        self.assertEqual((out["package"]["lineup_bar"]["note"], out["package"]["lineup_bar"]["floors"]),
 986 | +                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
 987 | +                                                                   "coherence": {"clip": 3, "vo_point": 3}}))
 988 | +        from unittest import mock
 989 | +        with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "no valid line-up calibration")):
 990 | +            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
 991 | +            out = rig.run()
 992 | +        self.assertIsNotNone(out["package"])
 993 | +        self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 994 | +
 995 | +
 996 |  class TestRuling56Scorer(unittest.TestCase):
 997 |      """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 998 |      about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
 999 | 
```

---

pp-selectid: RULING 116 (orchestrator 15:30 ET Nov 15) (4), STATE Q3 (15:34 ET; ruling 106's default APPLY at 15:54):
THE LINE-UP VERDICTS ON A CALIBRATED BAR. New: pipeline/lineup_bar.py, pipeline/lineup_calibration.json,
tests/package/test_lineup_bar.py. Changed: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py,
tests/package/conftest.py, tests/package/test_medley.py.

THE ORDER (ruling 116 (4)), verbatim: "IF (1) shows approved line-ups failing: propose the calibrated floors the same
way as ruling 115 (each part at least the lowest value across PBX's approved line-ups under the same asking), and put
the question to me with DEFAULT IN 20 MIN: APPLY the calibrated floors, audit-first, marked in the pin and in the
Telegram note in one plain line like the hook's, then rebuild."
(1) showed it (tests/package/proof/clips116/REPORT.md, committed 7a5c0362): today's clips-alone verdict fails the
protected 41f29b1f at seeds 7 and 9 and the sealed 13949b7c at 7 and 8; today's coherence verdict fails the PUBLISHED
0c68b589 at all three seeds and 41f29b1f at 7; every failure is one rating of 3; no approved line-up had more than one
flagged join; every asking stated a through-line.

THE CHANGE:
- lineup_bar.floors_from: each verdict's parts (clips-alone: the lowest clip after the hook; coherence: the lowest clip
  after the hook and the VO point) at their lowest across the approved runs, never under 3 (ruling 115's rule). The
  flagged-join allowance is NOT calibrated: it stays the law's one bridge (L-y 2; LY_MAX_BRIDGES), and no approved
  line-up needed more. The through-line stays required.
- lineup_calibration.json: rater Grok; the two prompts' versions (package.MEDLEY_VERSION / COHERENCE_VERSION: sha256
  of MEDLEY_PROMPT / COHERENCE_PROMPT); the approved runs as measured (pins, seeds, ratings, flagged joins,
  through-lines); floors clips-alone clip 3, coherence clip 3 and VO point 3; valid_h null (one fixed source, like
  the hook's); sealed with hook_bar's seal (hook_bar.write / load).
- lineup_bar.bar(versions): valid only sealed, naming a rater, for exactly these two versions, measured_at with a
  timezone and not in the future, its own valid_h, no floor under 3; else (None, why).
- lineup_bar.floors_for(verdict, backend, live, standard): the calibrated floors ONLY for a verdict the calibrated
  rater gave; every other back-end (Plan B's Gemini for clips-alone, deepseek / glm for coherence) and every verdict
  while the file is invalid gets the STANDARD bar (package.STANDARD_LINEUP: COHERENCE_MIN 4), which is stricter.
- package.medley / coherence: ok uses that verdict's floors (the clips after the hook; the VO point); the hook's slot is
  its own bar (ruling 115), unchanged; each verdict records "bar", "floors" and "calibration_sha256".
- Every place that judges those ratings reads the VERDICT'S OWN floors and leaves the hook's slot to its bar:
  last_clip_only (ruling 62); build()'s ruling-63 reorder (it read min(cl.values()) with the hook's own rating inside:
  a hook at its floors, rating 3, blocked a reorder: the ruling-115 site I missed); the weak clips swapped after a
  failed verdict; the takeaway-only rewrite after a failed coherence verdict (it read min(coh["clips"].values()) with
  the hook's 3 inside: the second missed site) and the weak clips there.
- The mark: lineup_bar_mark(med, coh) -> {"note": "line-up passed on the calibrated bar", "floors",
  "calibration_sha256", "ruling": "116"} ONLY when both verdicts of the package were judged on the calibrated bar (from
  what each verdict recorded when it was judged), set on the built package; package_pin.to_pin carries it OUTSIDE the
  seal, like hook_bar.
- proof_ledger names the line-up bar in every build line.

UNCHANGED GUARDS: hook_bar.load / write (the seal, pipeline/hook_bar.py:51-58, 120-129); hook_own (the hook's own
bar, pipeline/package.py); providers.Router.chain (the clips-alone list heimdall_first is Grok -> Gemini; coherence's
Grok -> deepseek -> glm: model_providers.json routing.heimdall_first, unchanged); package_pin.seal's arguments
(package_pin.py:200: the mark is not among them).

TESTS: test_lineup_bar (7): floors (lowest, stopped at 3, a run without ratings refused); the file (sealed, versions,
rater, valid_h, future, a hand edit); floors_for (the rater's verdict only); the mark (both verdicts, or none) and the
pin (outside the seal); the LIVE file's floors derived from proof/clips116 and live for production's versions, its
rater the first of both verdicts' production lists. test_medley TestRuling116LineupBar (7): clips-alone and coherence
on the calibrated rater's verdict vs another back-end's; ruling 62 on the verdict's own floor; ruling 63 reorders a
line-up whose hook sits at its floors (on BOTH bars: the standard bar's 4 is where the hook's 3 used to block); the
takeaway-only rewrite with such a hook (both bars); after a failed verdict only the clips under its floor are
swapped; the mark on a calibrated package and none on a standard one. The rig now answers as production does (the
hook's slot its own rating; the bar and floors in each verdict; coherence results configurable). All 40 suite files
pass (796 tests before the last test, 797 with it). Mutations after a control run: 13 of 13 killed.

PLEASE CHECK: (1) that the floors apply only to the calibrated rater's own verdicts and that everything else stays on
the stricter standard bar; (2) that no site still judges a line-up on COHERENCE_MIN with the hook's own rating inside;
(3) that the floors in the file are the source's minimums and the joins allowance the law's; (4) the mark: both
verdicts calibrated, outside the seal; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
