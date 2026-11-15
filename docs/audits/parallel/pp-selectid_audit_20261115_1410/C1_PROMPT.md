# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1410
# Branch: pp-selectid
# Generated: 2026-11-15 14:12 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1410/C1_STEP.diff (1551 lines)
```
   1 | diff --git a/pipeline/hook_bar.py b/pipeline/hook_bar.py
   2 | new file mode 100644
   3 | index 0000000..463b324
   4 | --- /dev/null
   5 | +++ b/pipeline/hook_bar.py
   6 | @@ -0,0 +1,134 @@
   7 | +"""RULING 115 (orchestrator 13:24 ET Nov 15): THE HOOK BAR IS DEFINED BY PBX'S APPROVALS.
   8 | +
   9 | +The hook job (package.hook_ratings) asks each candidate ALONE, at production's seed, on the calibrated rater (Grok).
  10 | +A hook passes when EACH of its three parts (scroll, alone, setup) is at least that part's FLOOR. A floor is the lowest
  11 | +value the part took across PBX's approved hooks, under that same asking (the source: tests/package/proof/hook113/
  12 | +ALONE_TEST.json). No floor is set below 3: the order stops a lower one at 3, and the builder reports it.
  13 | +
  14 | +The floors live in ONE calibration file, pipeline/hook_calibration.json, with its sha256. It is valid only for its
  15 | +rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for 24 h after it was
  16 | +measured (ruling 113 (2): again on any change, and once a day). An invalid or stale file passes NO hook, and the
  17 | +build says why in one line (fail closed, law L-m).
  18 | +A package sealed on this bar says so in its record (NOTE). PBX's approve or reject of it is appended to the file
  19 | +(add_example), so the approved set grows.
  20 | +"""
  21 | +import copy
  22 | +import hashlib
  23 | +import json
  24 | +import os
  25 | +from datetime import datetime, timedelta, timezone
  26 | +
  27 | +PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_calibration.json")
  28 | +PARTS = ("scroll", "alone", "setup")
  29 | +FLOOR_MIN = 3                       # the order: "If any floor comes out below 3, stop at 3 for that part and tell me."
  30 | +VALID_H = 24.0                      # ruling 113 (2): "once a day"
  31 | +NOTE = "hook passed on the calibrated bar"
  32 | +
  33 | +
  34 | +def body_sha(cal):
  35 | +    """The sha256 of the calibration's canonical JSON without its own "sha256" key."""
  36 | +    b = {k: v for k, v in cal.items() if k != "sha256"}
  37 | +    return hashlib.sha256(json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
  38 | +
  39 | +
  40 | +def floors_from(approved):
  41 | +    """{part: the lowest value it takes across the approved hooks' parts, never below FLOOR_MIN} and the parts that
  42 | +    came out below FLOOR_MIN (the order wants those told)."""
  43 | +    fl, low = {}, []
  44 | +    for p in PARTS:
  45 | +        vals = [a.get(p) for a in approved]
  46 | +        if not vals or any(type(v) is not int for v in vals):
  47 | +            raise ValueError(f"an approved hook has no integer {p!r}: the floors cannot be measured")
  48 | +        fl[p] = min(vals)
  49 | +        if fl[p] < FLOOR_MIN:
  50 | +            low.append(f"{p} {fl[p]} (stopped at {FLOOR_MIN})")
  51 | +            fl[p] = FLOOR_MIN
  52 | +    return fl, low
  53 | +
  54 | +
  55 | +def load(path=PATH):
  56 | +    """The calibration as written, or None with why (missing, unreadable, or its sha does not match its body)."""
  57 | +    try:
  58 | +        with open(path) as f:
  59 | +            cal = json.load(f)
  60 | +    except (OSError, ValueError) as e:
  61 | +        return None, f"the hook calibration cannot be read ({type(e).__name__}: {str(e)[:120]})"
  62 | +    if not isinstance(cal, dict) or cal.get("sha256") != body_sha(cal):
  63 | +        return None, "the hook calibration's sha256 does not match its body (edited by hand?)"
  64 | +    return cal, None
  65 | +
  66 | +
  67 | +def bar(rater, question_version, seed, now=None, path=PATH):
  68 | +    """The live bar: {"floors", "sha256", "rater", ...} when the calibration is valid for exactly this question
  69 | +    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is under
  70 | +    VALID_H old; else (None, why), and no hook passes."""
  71 | +    cal, why = load(path)
  72 | +    if cal is None:
  73 | +        return None, why
  74 | +    for k, want in (("rater", rater), ("question_version", question_version), ("seed", seed), ("asking", "alone")):
  75 | +        if k == "rater" and want is None:
  76 | +            continue
  77 | +        if cal.get(k) != want:
  78 | +            return None, f"the hook calibration is for {k} {cal.get(k)!r}, not {want!r}: no hook passes until it is re-run"
  79 | +    try:
  80 | +        at = datetime.fromisoformat(str(cal["measured_at"]))
  81 | +        fl = {p: int(cal["floors"][p]) for p in PARTS}
  82 | +    except (KeyError, TypeError, ValueError):
  83 | +        return None, "the hook calibration has no readable measured_at or floors"
  84 | +    if (now or datetime.now(timezone.utc)) - at > timedelta(hours=VALID_H):
  85 | +        return None, f"the hook calibration is over {VALID_H:g} h old (measured {cal['measured_at']}): re-run it"
  86 | +    if any(v < FLOOR_MIN for v in fl.values()):
  87 | +        return None, f"a floor under {FLOOR_MIN} in the hook calibration: refused"
  88 | +    return {"floors": fl, "sha256": cal["sha256"], "rater": cal["rater"], "question_version": cal["question_version"],
  89 | +            "seed": cal["seed"], "measured_at": cal["measured_at"]}, None
  90 | +
  91 | +
  92 | +def passes(rec, live):
  93 | +    """(passes, why) for one hook rating record {"scroll", "alone", "setup", "backend", ...} on the live bar."""
  94 | +    if live is None:
  95 | +        return False, "no valid hook calibration"
  96 | +    if rec.get("backend") != live["rater"]:
  97 | +        return False, f"rated by {rec.get('backend')}, but the bar is calibrated on {live['rater']}"
  98 | +    short = [f"{p} {rec.get(p)} < {live['floors'][p]}" for p in PARTS
  99 | +             if type(rec.get(p)) is not int or rec[p] < live["floors"][p]]
 100 | +    return (not short), ("; ".join(short) or None)
 101 | +
 102 | +
 103 | +def text(live):
 104 | +    """The bar in one line, for every build line and record."""
 105 | +    if live is None:
 106 | +        return "no valid hook calibration: no hook passes"
 107 | +    f = live["floors"]
 108 | +    return (f"the calibrated hook bar (ruling 115): scroll >= {f['scroll']}, alone >= {f['alone']}, setup >= "
 109 | +            f"{f['setup']}, on {live['rater']} asked alone at seed {live['seed']} (calibration {live['sha256'][:12]})")
 110 | +
 111 | +
 112 | +def write(cal, path=PATH):
 113 | +    """Seal and write a calibration (its sha256 over its body), .tmp then rename."""
 114 | +    cal = dict(cal)
 115 | +    cal["sha256"] = body_sha(cal)
 116 | +    tmp = path + ".tmp"
 117 | +    with open(tmp, "w") as f:
 118 | +        json.dump(cal, f, indent=1, sort_keys=True)
 119 | +        f.write("\n")
 120 | +    os.replace(tmp, path)
 121 | +    return cal
 122 | +
 123 | +
 124 | +def add_example(story_id, verdict, hook, reason=None, path=PATH, now=None):
 125 | +    """RULING 115 (2): PBX's approve or reject of a package sealed on this bar, appended as an example (approved =
 126 | +    positive, rejected = negative with his reason). The floors are NOT re-derived here: a new floor comes from the
 127 | +    next calibration run, which asks every approved hook again. -> the calibration as written."""
 128 | +    if verdict not in ("approved", "rejected"):
 129 | +        raise ValueError("verdict is 'approved' or 'rejected'")
 130 | +    if verdict == "rejected" and not reason:
 131 | +        raise ValueError("a rejection carries PBX's reason")
 132 | +    cal, why = load(path)
 133 | +    if cal is None:
 134 | +        raise ValueError(why)
 135 | +    cal = copy.deepcopy(cal)
 136 | +    cal.setdefault("examples", []).append({
 137 | +        "story_id": story_id, "verdict": verdict, "reason": reason,
 138 | +        "hook": {k: hook.get(k) for k in ("moment_id", "text", "channel", *PARTS, "backend")},
 139 | +        "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")})
 140 | +    return write(cal, path)
 141 | diff --git a/pipeline/hook_calibration.json b/pipeline/hook_calibration.json
 142 | new file mode 100644
 143 | index 0000000..f035986
 144 | --- /dev/null
 145 | +++ b/pipeline/hook_calibration.json
 146 | @@ -0,0 +1,85 @@
 147 | +{
 148 | + "approved": [
 149 | +  {
 150 | +   "alone": 4,
 151 | +   "approved": "the protected preview (references/pulse_preview_2026-11-11, PBX 2026-11-11)",
 152 | +   "backend": "xai:grok-4.20-0309-reasoning",
 153 | +   "channel": "DataDash",
 154 | +   "how": "asked alone at seed 7",
 155 | +   "ref": "ref-preview",
 156 | +   "scroll": 3,
 157 | +   "setup": 3,
 158 | +   "text": "Bitcoin has now seen a 16 % decline from the overall high from $88 ,000, touching down towards about $73 ,400, $500, give or take.",
 159 | +   "video_id": "RXTVaDsN11M",
 160 | +   "why": "lacks dramatic punch in first seconds"
 161 | +  },
 162 | +  {
 163 | +   "alone": 5,
 164 | +   "approved": "moments-fresh_20261112_050611-37c5b5f5",
 165 | +   "backend": "xai:grok-4.20-0309-reasoning",
 166 | +   "channel": "Saifedean Ammous",
 167 | +   "how": "asked alone at seed 7",
 168 | +   "ref": "ref-37c5b5f5",
 169 | +   "scroll": 3,
 170 | +   "setup": 4,
 171 | +   "text": "Bitcoin does not have any authority that allows people to take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that.",
 172 | +   "video_id": "vgsSZ4mAHfQ",
 173 | +   "why": "first 2-3s lack punch to stop scroll"
 174 | +  },
 175 | +  {
 176 | +   "alone": 5,
 177 | +   "approved": "moments-fresh_20261112_050611-41f29b1f",
 178 | +   "backend": "xai:grok-4.20-0309-reasoning",
 179 | +   "channel": "Natalie Brunell",
 180 | +   "how": "asked alone at seed 7",
 181 | +   "ref": "ref-41f29b1f",
 182 | +   "scroll": 3,
 183 | +   "setup": 4,
 184 | +   "text": "Bitcoin imposes a global free market for the first time ever.",
 185 | +   "video_id": "wdk5JZ9hPzs",
 186 | +   "why": "first seconds lack strong grab to halt scroll"
 187 | +  },
 188 | +  {
 189 | +   "alone": 5,
 190 | +   "approved": "moments-ledger_20261113_183302-0c68b589",
 191 | +   "backend": "xai:grok-4.20-0309-reasoning",
 192 | +   "channel": "Simply Bitcoin",
 193 | +   "how": "asked alone at seed 7 once more, unrecorded: the first answer was out of contract",
 194 | +   "ref": "ref-0c68b589",
 195 | +   "scroll": 3,
 196 | +   "setup": 4,
 197 | +   "text": "A CEO makes a personal mistake in shareholders pay. A government mismanages its currencies. and its savers pay. Bitcoin's rules aren't kept by a single executive or a single central bank. They're enforced by thousands of independent computers running the same code. No CEO, no compromise, no committee to debate.",
 198 | +   "video_id": "DcUbBkyeh9M",
 199 | +   "why": "first seconds too dry to halt scrolls"
 200 | +  },
 201 | +  {
 202 | +   "alone": 5,
 203 | +   "approved": "moments-ledger_20261113_215708-13949b7c",
 204 | +   "backend": "xai:grok-4.20-0309-reasoning",
 205 | +   "channel": "Simply Bitcoin",
 206 | +   "how": "asked alone at seed 7 once more, unrecorded: the first answer was out of contract",
 207 | +   "ref": "ref-13949b7c",
 208 | +   "scroll": 3,
 209 | +   "setup": 4,
 210 | +   "text": "Currencies are often born for political reasons, but fail for economic reasons. Bitcoin launched in January of 2009. It's never been renamed. It's never gone into another currency. It's never been redenominated or reissued.",
 211 | +   "video_id": "DcUbBkyeh9M",
 212 | +   "why": "dry academic opener lacks scroll-stopping punch"
 213 | +  }
 214 | + ],
 215 | + "asking": "alone",
 216 | + "examples": [],
 217 | + "floors": {
 218 | +  "alone": 4,
 219 | +  "scroll": 3,
 220 | +  "setup": 3
 221 | + },
 222 | + "floors_below_3": [],
 223 | + "measured_at": "2026-11-15T18:07:52+00:00",
 224 | + "question_version": "bfdf74078d5e",
 225 | + "rater": "xai:grok-4.20-0309-reasoning",
 226 | + "rule": "a hook passes when EACH of scroll / alone / setup is at least its floor; a floor is the lowest value the part takes across the approved hooks under this asking, never below 3",
 227 | + "ruling": "115 (orchestrator 13:24 ET Nov 15): the hook bar is defined by PBX's approvals",
 228 | + "seed": 7,
 229 | + "sha256": "a39b4c720c1d2b8186c31bcfb80259872e6bd16a52597781351134a8ee8392f8",
 230 | + "source": "tests/package/proof/hook113/ALONE_TEST.json"
 231 | +}
 232 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
 233 | index 535c340..c071828 100644
 234 | --- a/pipeline/model_providers.json
 235 | +++ b/pipeline/model_providers.json
 236 | @@ -370,9 +370,6 @@
 237 |      "heimdall:deepseek/deepseek-v4.1-flash"
 238 |     ],
 239 |     "coherence_verdict:hook": [
 240 | -    "heimdall:qwen/qwen3.8-27b",
 241 | -    "heimdall:z-ai/glm-5.3-flash",
 242 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 243 |      "xai:grok-4.20-0309-reasoning"
 244 |     ],
 245 |     "coherence_verdict:clips_alone": [
 246 | @@ -393,6 +390,9 @@
 247 |      "anthropic:claude-opus-5-5",
 248 |      "local_judge:gemma3:27b"
 249 |     ],
 250 | +   "coherence_verdict:hook": [
 251 | +    "xai:grok-4.20-0309-reasoning"
 252 | +   ],
 253 |     "coherence_verdict": [
 254 |      "xai:grok-4.20-0309-reasoning",
 255 |      "google:gemini-2.5-pro",
 256 | @@ -457,9 +457,13 @@
 257 |      "xai:grok-4.20-0309-reasoning",
 258 |      "heimdall:deepseek/deepseek-v4.1-flash",
 259 |      "heimdall:z-ai/glm-5.3-flash"
 260 | +   ],
 261 | +   "coherence_verdict:hook": [
 262 | +    "xai:grok-4.20-0309-reasoning"
 263 |     ]
 264 |    },
 265 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
 266 | +  "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
 267 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
 268 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
 269 |    "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
 270 | diff --git a/pipeline/package.py b/pipeline/package.py
 271 | index 08c0035..72e5946 100644
 272 | --- a/pipeline/package.py
 273 | +++ b/pipeline/package.py
 274 | @@ -9,8 +9,9 @@ usable()      moments a package may use: on screen eligible (word timing, law L-
 275 |  prescreen()   step A of law L-s on EVERY usable moment's own context (ruling 58), ONCE per moment (package-independent):
 276 |                this build's ledger (`store`) and the step-A cache every build shares (`cache`: moment id + text sha +
 277 |                context sha + the step-A prompt); never recomputed
 278 | -hook_ratings() RULING 59: the hook question of ruling 52 on every cleared, cuttable moment that can open, ONE batched
 279 | -              call, cached; only a hook rated >= HOOK_MIN opens, and the angles are written FOR the passing hooks
 280 | +hook_ratings() RULING 59: the hook question of ruling 52 on every cleared, cuttable moment that can open, cached;
 281 | +              RULING 115: each candidate asked ALONE (one call each) and only a hook on the calibrated bar (hook_bar:
 282 | +              every part at least its floor, by the calibrated rater) opens; the angles are written FOR the passing hooks
 283 |  ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
 284 |                channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
 285 |  lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
 286 | @@ -82,7 +83,8 @@ SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is
 287 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 288 |  WRITES = 2
 289 |  COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
 290 | -HOOK_MIN = COHERENCE_MIN           # RULING 59 (b): only a moment rated >= 4 on the hook's own job may open a line-up
 291 | +HOOK_MIN = COHERENCE_MIN           # RULING 59 (b), until ruling 115: a moment rated >= 4 on the hook's own job opened a
 292 | +#   line-up; ruling 115's calibrated bar decides now (hook_own "passes"). replay85's agreement rule still reads it.
 293 |  BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
 294 |  BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
 295 |  BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
 296 | @@ -857,17 +859,28 @@ the opener of a video; the candidates are not compared with each other and never
 297 |  For EACH candidate: """ + HOOK_QUESTION + """
 298 |  Give "why": a few words on the candidate's weakest part.
 299 |  Return ONLY this JSON object: {{"hooks": {{{keys}}}}}"""   # ruling 59 (a): ruling 52's ONE hook question, per candidate
 300 | -HOOK_VERSION = hashlib.sha256(HOOKS_PROMPT.encode()).hexdigest()[:12]   # a cached rating is for exactly this question
 301 | -
 302 | -
 303 | -def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
 304 | -    """RULING 59 (a): the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked of EVERY
 305 | -    given moment ALONE, in ONE batched call (coherence_verdict, never the writers' vendor or family), each rating
 306 | -    DERIVED as the lowest part (HOOK_RULE). Cached (`cache`, shared by every build) by the moment id, the sha256 of its
 307 | -    text and the question's version: a moment is rated once, by a back-end off the writers. A reply out of contract
 308 | -    moves on to the next model of the chain (providers.call_parsed, ruling 82 as the 20:33 order extends it). ->
 309 | -    ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the error or None).
 310 | -    A moment the call did not rate has no rating (law L-m: never a pass)."""
 311 | +HOOK_ASKING = "alone: one candidate a call (ruling 115)"   # ruling 115: the hook job asks each candidate ALONE
 312 | +HOOK_VERSION = hashlib.sha256((HOOKS_PROMPT + "\n" + HOOK_ASKING).encode()).hexdigest()[:12]   # a cached rating is for
 313 | +#   exactly this question AND this asking: the batched ratings of before (dd497beb6930) never answer
 314 | +HOOK_SEED = 7                      # production's seed for the hook job (the calibration law's seed, ruling 113 (2))
 315 | +
 316 | +
 317 | +def hook_live_bar():
 318 | +    """RULING 115: the calibrated hook bar for this question version and seed (hook_bar.bar), or (None, why)."""
 319 | +    import hook_bar as HB
 320 | +    return HB.bar(None, HOOK_VERSION, HOOK_SEED)
 321 | +
 322 | +
 323 | +def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=HOOK_SEED):
 324 | +    """RULING 59 (a) / RULING 115: the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked
 325 | +    of EVERY given moment ALONE: ONE call per candidate (ruling 115: the asking the calibration measured; a batch moved
 326 | +    single ratings, 41f29b1f's from 3 alone to 5 among the approved hooks), on coherence_verdict's hook list (ruling
 327 | +    115: Grok; never the writers' vendor or family). Cached (`cache`, shared by every build) by the moment id, the
 328 | +    sha256 of its text and the question version (HOOK_VERSION carries the asking): a moment is rated once, by a back-end
 329 | +    off the writers. A reply out of contract moves on to the next model of the chain (providers.call_parsed, ruling 82
 330 | +    as the 20:33 order extends it). Whether a rated hook may open is hook_own's: the calibrated floors (ruling 115).
 331 | +    -> ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the first error or None).
 332 | +    A moment no call rated has no rating (law L-m: never a pass)."""
 333 |      import providers as P
 334 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 335 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
 336 | @@ -883,12 +896,8 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 337 |              todo.append(m)
 338 |      if not todo:
 339 |          return out, None
 340 | -    ids = [m["moment_id"] for m in todo]
 341 | -    cands = "\n".join(f'CANDIDATE id="{m["moment_id"]}" (on screen: {CI._q(_name(m, ctx), 80)}): '
 342 | -                      f'"{CI._q(m["text"], 900)}"' for m in todo)
 343 | -    keys = ", ".join(f'"{i}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}' for i in ids)
 344 |  
 345 | -    def parse(text):
 346 | +    def parse(text, ids):
 347 |          v = json.loads(text.strip())
 348 |          h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 349 |          if not isinstance(h, dict) or set(h) != set(ids) or any(
 350 | @@ -896,21 +905,25 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 351 |                  any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 352 |              raise ValueError("hook ratings out of contract")
 353 |          return h
 354 | -    try:                                         # the 20:33 order: an answer out of contract moves on to the next
 355 | -        r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), parse,
 356 | -                             600 + 150 * len(ids), seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 357 | -                             kind="hook")                                # ruling 88: the hook rating's own list
 358 | -    except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # (it was one re-ask of the same
 359 | -        return out, f"{type(e).__name__}: {str(e)[:200]}"     # model) unavailable, all out of contract, or the guard
 360 | -    new = {}
 361 | -    for m in todo:
 362 | -        x = h[m["moment_id"]]
 363 | +    new, err = {}, None
 364 | +    for m in todo:                               # RULING 115: ALONE, one candidate a call (the calibration's asking)
 365 | +        mid = m["moment_id"]
 366 | +        cand = f'CANDIDATE id="{mid}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 367 | +        keys = f'"{mid}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}'
 368 | +        try:                                     # the 20:33 order: an answer out of contract moves on to the next
 369 | +            r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cand, keys=keys),
 370 | +                                 lambda t, i=(mid,): parse(t, i), 600 + 150, seed, avoid_vendor=writer_vendor,
 371 | +                                 avoid_family=writer_family, kind="hook")   # ruling 88: the hook rating's own list
 372 | +        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # this candidate has no rating
 373 | +            err = err or f"{type(e).__name__}: {str(e)[:200]}"       # (law L-m); the others are still asked
 374 | +            continue
 375 | +        x = h[mid]
 376 |          rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 377 | -               "backend": r.backend, "rule": HOOK_OWN_RULE}           # ruling 61: scroll / alone
 378 | -        out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 379 | +               "backend": r.backend, "rule": HOOK_OWN_RULE}           # the rating orders hooks; hook_own decides
 380 | +        out[mid] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 381 |          new[key(m)] = {r.backend: rec}
 382 |      _cache_put(cache, new)
 383 | -    return out, None
 384 | +    return out, err
 385 |  
 386 |  TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
 387 |                   "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
 388 | @@ -1380,15 +1393,45 @@ def no_role_on_screen(m):
 389 |                                          "with no clip scorer at the pin stage") + f": {c_why}; {h_why}")
 390 |  
 391 |  
 392 | +_LIVE = {}
 393 | +
 394 | +
 395 | +def _live_bar():
 396 | +    """The calibrated bar, read once per state of the calibration file (its mtime), so a build reads it once."""
 397 | +    import hook_bar as HB
 398 | +    try:
 399 | +        k = os.stat(HB.PATH).st_mtime_ns
 400 | +    except OSError:
 401 | +        k = None
 402 | +    if k not in _LIVE:
 403 | +        _LIVE.clear()
 404 | +        _LIVE[k] = hook_live_bar()
 405 | +    return _LIVE[k]
 406 | +
 407 | +
 408 | +def hook_bar_mark():
 409 | +    """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
 410 | +    the plain line for the Telegram note, the floors and the calibration's sha."""
 411 | +    import hook_bar as HB
 412 | +    live, why = _live_bar()
 413 | +    return {"note": HB.NOTE, "bar": HB.text(live), "floors": (live or {}).get("floors"),
 414 | +            "calibration_sha256": (live or {}).get("sha256"), "ruling": "115"}
 415 | +
 416 | +
 417 |  def hook_own(m):
 418 | -    """RULING 61 (12:00): a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
 419 | -    "alone", "rating": the lower of the two, "source", "rule"}. 'Sets up what follows' is not part of it: it is judged
 420 | -    at the hook -> clip_01 join. None when the moment carries no complete rating (then it never opens, law L-m)."""
 421 | +    """RULING 61 / RULING 115: a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
 422 | +    "alone", "setup", "rating": the lower of scroll and alone (it ORDERS hooks), "passes": RULING 115, every part at
 423 | +    least its calibrated floor, rated by the calibrated rater (hook_bar.passes), "short": why not, "bar": the bar in one
 424 | +    line, "source", "rule"}. None when the record lacks a part (then it never opens, law L-m)."""
 425 | +    import hook_bar as HB
 426 |      r = (m or {}).get("hook_rating") or {}
 427 | -    parts = {k: r.get(k) for k in HOOK_OWN}
 428 | +    parts = {k: r.get(k) for k in HOOK_PARTS}
 429 |      if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
 430 |          return None
 431 | -    return dict(parts, rating=min(parts.values()), source="the hook's cached own-job rating (ruling 61)",
 432 | +    live, why = _live_bar()
 433 | +    ok, short = HB.passes(dict(parts, backend=r.get("backend")), live)
 434 | +    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok, short=why if live is None else short,
 435 | +                bar=HB.text(live), source="the hook's cached own-job rating (ruling 61), on the calibrated bar (ruling 115)",
 436 |                  rule=HOOK_OWN_RULE)
 437 |  
 438 |  
 439 | @@ -1417,8 +1460,9 @@ def third_opener(m):
 440 |  def _can_open(m, pending_verdict=False):
 441 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
 442 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
 443 | -    59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
 444 | -    (an unmeasured rating is never a pass, law L-m). A moment without the key is judged as before ruling 59."""
 445 | +    59: build() sets "hook_rating" on every cleared moment before any line-up), passing the calibrated hook bar on the
 446 | +    hook's own job (ruling 115: hook_own "passes"; an unmeasured rating is never a pass, law L-m). A moment without
 447 | +    the key is judged as before ruling 59."""
 448 |      import stand_alone as SA
 449 |      v = verdict_of(m)                                    # RULING 94 (b): the scorer's verdict on its current text
 450 |      sc = (v["score"], v["fault"]) if v else (None, None)
 451 | @@ -1432,8 +1476,8 @@ def _can_open(m, pending_verdict=False):
 452 |          return False
 453 |      if "hook_rating" not in m:
 454 |          return True                                      # not rated yet: judged as before ruling 59
 455 | -    own = hook_own(m)                                    # ruling 61: scroll / alone, the cached own-job rating
 456 | -    return own is not None and own["rating"] >= HOOK_MIN
 457 | +    own = hook_own(m)                                    # ruling 115: every part at least its calibrated floor
 458 | +    return own is not None and own["passes"]
 459 |  
 460 |  
 461 |  def hook_order(ms):
 462 | @@ -1522,7 +1566,7 @@ def placement(m):
 463 |      eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
 464 |      short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
 465 |      and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook). RULING 59:
 466 | -    "may open" is can_open(): once the pool's hooks are rated, only a hook rated >= HOOK_MIN opens."""
 467 | +    "may open" is can_open(): once the pool's hooks are rated, only a hook on the calibrated bar opens (ruling 115)."""
 468 |      opens = can_open(m)
 469 |      if m["duration_s"] < SHORT_CLIP_S:
 470 |          return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
 471 | @@ -1688,8 +1732,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 472 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 473 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 474 |                                                       "fail closed"})
 475 | -    ok = own is not None and _line_ok(v["through_line"]) and \
 476 | -        min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
 477 | +    ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 478 | +        min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN   # ruling 115:
 479 | +    #   the hook's slot is its calibrated bar, every clip after it and the VO point COHERENCE_MIN, as before
 480 |      return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 481 |  
 482 |  
 483 | @@ -1749,22 +1794,26 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 484 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 485 |                                                       "fail closed"})
 486 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
 487 | -    ok = own is not None and _line_ok(v["through_line"]) and min(v["clips"].values()) >= COHERENCE_MIN and \
 488 | -        len(flagged) <= LY_MAX_BRIDGES
 489 | +    ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 490 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 491 | +    #   ruling 115: the hook's slot is its calibrated bar; every clip after it COHERENCE_MIN, as before
 492 |      return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 493 |                      replayed=bool(getattr(r, "replayed", False)), cached=bool(getattr(r, "cached", False)))
 494 |  
 495 |  
 496 |  def last_clip_only(segs, med):
 497 |      """RULING 62 (12:00): whether a clips-alone failure is its LAST clip's alone: measured, the through-line stated,
 498 | -    every other rating (the hook's cached one included) >= COHERENCE_MIN, the last clip's under it, and no more than
 499 | -    LY_MAX_BRIDGES flagged joins once the join into the last clip goes with it."""
 500 | +    the hook passing its calibrated bar (ruling 115: hook_own of the line-up's own hook, as medley() judges it), every
 501 | +    clip after it but the last >= COHERENCE_MIN, the last clip's under it, and no more than LY_MAX_BRIDGES flagged
 502 | +    joins once the join into the last clip goes with it."""
 503 |      labs = labels(len(segs))
 504 |      cl = med.get("clips") or {}
 505 |      if not med.get("measured") or not _line_ok(med.get("through_line")) or labs[-1] not in cl or labs[0] not in cl:
 506 |          return False
 507 |      rest = [j for j in med.get("flagged") or [] if j != joins(labs)[-1]]
 508 | -    return [lb for lb, x in cl.items() if x < COHERENCE_MIN] == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 509 | +    own = hook_own(segs[0])                              # ruling 115: the hook passes by its calibrated bar
 510 | +    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < COHERENCE_MIN] \
 511 | +        == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 512 |  
 513 |  
 514 |  def reorder(segs, bad_pairs, judged, repeat_ok=False):
 515 | @@ -2422,8 +2471,9 @@ def load_candidate(record, index=None, source=""):
 516 |  
 517 |  def candidate_lineup(router, candidate, cleared, now):
 518 |      """RULING 66: the candidate's line-up as THIS build's pool holds it, or why it is closed. Every clip must still be
 519 | -    cleared (a clip delivered, aged out or failing a gate closes it), its hook must still open (its cached rating >=
 520 | -    HOOK_MIN, G17a), and exactly its clips, in its order, must still form a line-up under lineup_for's own rules
 521 | +    cleared (a clip delivered, aged out or failing a gate closes it), its hook must still open (its cached rating on
 522 | +    the calibrated bar, ruling 115; G17a), and exactly its clips, in its order, must still form a line-up under
 523 | +    lineup_for's own rules
 524 |      (the seconds, the channels, price predictions, short clips, trims, the render's STAND_ALONE).
 525 |      -> (segs, None) or (None, why)."""
 526 |      ids = list(candidate["lineup"])
 527 | @@ -2433,7 +2483,7 @@ def candidate_lineup(router, candidate, cleared, now):
 528 |      if gone:
 529 |          return None, f"no longer cleared in this pool (delivered, aged out, or a gate fails): {gone}"
 530 |      if not can_open(cleared[ids[0]]):
 531 | -        return None, f"its hook no longer opens (rating >= {HOOK_MIN} and G17a): {ids[0]}"
 532 | +        return None, f"its hook no longer opens (the calibrated hook bar and G17a): {ids[0]}"
 533 |      segs = lineup_for(dict(candidate["angle"], moments=ids), cleared, clips=(len(ids) - 1, len(ids) - 1),
 534 |                        repeat_ok=candidate.get("supply_exception") is not None, need_onset=True,
 535 |                        need_stand_alone=True, now=now, hook_only=True)
 536 | @@ -2456,11 +2506,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 537 |      scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 538 |      render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 539 |      RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 540 | -    own job in one batched call (hook_ratings); only a hook rated >= HOOK_MIN opens; with none, the build stops there
 541 | -    ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 542 | +    own job (hook_ratings; ruling 115: each alone); only a hook on the calibrated bar opens; with none, the build stops
 543 | +    there ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 544 |      writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
 545 |      freshness next), each line-up opens on its angle's own hook and never swaps it.
 546 | -    RULING 70, THE VISUAL CHECK (visual_pin): every hook rated >= HOOK_MIN is seen right after the ratings, before any
 547 | +    RULING 70, THE VISUAL CHECK (visual_pin): every hook on the bar is seen right after the ratings, before any
 548 |      angle is asked (a hook whose sheet shows a third person while its words make a negative claim, or that is not
 549 |      measured, may not open: can_open); every clip of a line-up that passes the clips-alone verdict is seen before any
 550 |      write (not measured: dropped and re-lined, law L-m). Findings are sealed as FLAGS on the segment, never a reject by
 551 | @@ -2642,7 +2692,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 552 |          m.pop("hook_rating", None)                                       # cache's), never one carried in
 553 |      openers = {mid: m for mid, m in cleared.items() if can_open(m)}      # RULING 59 (a): every one that can open,
 554 |      rated, hook_err = hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
 555 | -        ({}, None)                                                        # one batched call, cached
 556 | +        ({}, None)                                                        # each alone (ruling 115), cached
 557 |      for mid, m in cleared.items():                                       # (b): the rating gates every opening now
 558 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
 559 |                                                                        "cannot open (hook eligibility, G17a or the "
 560 | @@ -2663,16 +2713,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 561 |              + (f" ({'; '.join(f'{k}: {v[:90]}' for k, v in blocked.items())})" if blocked else "")
 562 |              + f" ({time.time() - t0:.0f} s)")
 563 |      best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]
 564 | -    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
 565 | +    import hook_bar as HB
 566 | +    live, live_why = _live_bar()                         # RULING 115: the calibrated bar, named in every build line
 567 | +    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "bar": HB.text(live),
 568 | +                        "bar_floors": (live or {}).get("floors"), "bar_sha256": (live or {}).get("sha256"),
 569 | +                        "bar_invalid": live_why,
 570 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
 571 |                          "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
 572 |                          "visual_blocked": blocked}
 573 | -    log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} rated >= "
 574 | -        f"{HOOK_MIN} on the hook's own job" + (f"; NOT RATED: {hook_err}" if hook_err else "") +
 575 | -        f" ({time.time() - t0:.0f} s)")
 576 | +    log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} pass "
 577 | +        f"{HB.text(live)}" + (f" [{live_why}]" if live_why else "") + (f"; NOT RATED: {hook_err}" if hook_err else "")
 578 | +        + f" ({time.time() - t0:.0f} s)")
 579 |      if not out["hook_pool"]["passing"]:                                  # (d): no line-up is paid for
 580 |          out["why_none"] = ("no hook in the pool (ruling 59 d): " + (
 581 | -            f"none of the {len(openers)} moments that can open rates >= {HOOK_MIN} on the hook's own job" +
 582 | +            f"none of the {len(openers)} moments that can open passes {HB.text(live)}" +
 583 |              (f" ({len(openers) - len(rated)} not rated: {hook_err})" if hook_err else "") + "; the best: " +
 584 |              "; ".join(f"{b['channel']} {b['rating']} (scroll {b['scroll']}, alone {b['alone']}, setup {b['setup']}): "
 585 |                        f"{b['why']}" for b in best) if openers else
 586 | @@ -2702,7 +2756,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 587 |          return out
 588 |      passing = hook_order([m for m in cleared.values() if can_open(m)])    # ruling 59: the passing hooks still
 589 |      if not passing:                                                        # cleared after the second screen
 590 | -        out["why_none"] = ("no hook in the pool (ruling 59 d): every hook rated >= " + str(HOOK_MIN) + " failed the "
 591 | +        out["why_none"] = ("no hook in the pool (ruling 59 d): every hook that passed the calibrated bar failed the "
 592 |                             "second vendor's step A: " + "; ".join(out["prescreen"]["second_vendor"].get(mid, "?")
 593 |                                                                      for mid in out["hook_pool"]["passing"]))
 594 |          return out
 595 | @@ -3458,6 +3512,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 596 |              if out["packages"] or out.get("budget_stop") or out.get("lock_stop") or over_budget(ai):
 597 |                  break
 598 |      out["package"] = out["packages"][0] if out["packages"] else None
 599 | +    if out["package"]:                                   # RULING 115 (2): a package sealed on the calibrated bar says so
 600 | +        out["package"]["hook_bar"] = hook_bar_mark()
 601 |      if candidate is not None:                             # RULING 66: what became of the candidate
 602 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 603 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 604 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 605 | index 1f409cf..03990bc 100644
 606 | --- a/pipeline/package_pin.py
 607 | +++ b/pipeline/package_pin.py
 608 | @@ -495,6 +495,8 @@ def to_pin(pk, run_name):
 609 |                                      "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 610 |                                     if spot else {}),
 611 |                                  "gates": pk["gates"],
 612 | +                                **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 613 | +                                #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 614 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 615 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 616 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 617 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 618 | index 36ca761..5e2c2cb 100644
 619 | --- a/pipeline/providers.py
 620 | +++ b/pipeline/providers.py
 621 | @@ -1213,24 +1213,29 @@ class Router:
 622 |                      self.down[n] = was
 623 |          return ok
 624 |  
 625 | -    def _shadow_of(self, role):
 626 | -        return self.shadow.get(role) or self.shadow.get("*")
 627 | +    def _shadow_of(self, role, kind=None):
 628 | +        """RULING 86, and RULING 115 for a verdict type: "<role>:<kind>" first (the hook job's qwen), then the role,
 629 | +        then "*"."""
 630 | +        return (self.shadow.get(f"{role}:{kind}") if kind else None) or self.shadow.get(role) or self.shadow.get("*")
 631 |  
 632 | -    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding):
 633 | +    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding, kind=None):
 634 |          """RULING 86: ask the role's shadow back-end the same prompt, in a thread; one JSON line to shadow_log per
 635 | -        verdict with both answers. Never raises into the build and never decides."""
 636 | +        verdict with both answers. Never raises into the build and never decides. A verdict type's own shadow (RULING
 637 | +        115) is asked on a chain of its own ("shadow86:<role>:<kind>"), so it never takes another shadow's chain."""
 638 |          import threading
 639 | -        name = self._shadow_of(role)
 640 | -        self.chains.setdefault(f"shadow86:{role}", [name])
 641 | +        name = self._shadow_of(role, kind)
 642 | +        own = f"shadow86:{role}:{kind}" if kind and self.shadow.get(f"{role}:{kind}") else f"shadow86:{role}"
 643 | +        self.chains.setdefault(own, [name])
 644 |  
 645 |          def run():
 646 | -            rec = {"role": role, "prompt": prompt_text(prompt), "images": len(prompt["images"]) if is_vision(prompt)
 647 | +            rec = {"role": role, "kind": kind, "prompt": prompt_text(prompt),
 648 | +                   "images": len(prompt["images"]) if is_vision(prompt)
 649 |                     else 0, "max_tokens": max_tokens, "seed": seed, "system": system,
 650 |                     "deciding": {"backend": deciding.backend, "vendor": deciding.vendor, "text": deciding.text,
 651 |                                  "cached": bool(getattr(deciding, "cached", False))}}
 652 |              t0 = time.time()
 653 |              try:
 654 | -                r = self.call(f"shadow86:{role}", prompt, max_tokens, seed, system=system)
 655 | +                r = self.call(own, prompt, max_tokens, seed, system=system)
 656 |                  rec["shadow"] = {"backend": r.backend, "text": r.text, "seconds": round(time.time() - t0, 2),
 657 |                                   "cached": bool(getattr(r, "cached", False)),
 658 |                                   "usd_reported": (r.usage or {}).get("usd_reported"), "usd_estimate": r.usd}
 659 | @@ -1314,8 +1319,8 @@ class Router:
 660 |                      rec = json.load(f)
 661 |                  out = Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 662 |                              rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 663 | -                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 664 | -                    self._shadow_ask(role, prompt, max_tokens, seed, system, out)  # ruling 86: a recorded verdict too
 665 | +                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
 666 | +                    self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: recorded too
 667 |                  return out
 668 |              if self.replay:
 669 |                  tried.append((name, "replay: not recorded"))
 670 | @@ -1410,8 +1415,8 @@ class Router:
 671 |                  recorded = path
 672 |              out = Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 673 |                          recorded)
 674 | -            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 675 | -                self._shadow_ask(role, prompt, max_tokens, seed, system, out)     # ruling 86: asked, never deciding
 676 | +            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
 677 | +                self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: never deciding
 678 |              return out
 679 |          if self.replay:
 680 |              raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
 681 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 682 | index c945ced..e8a7f9e 100644
 683 | --- a/pipeline/spotlight.py
 684 | +++ b/pipeline/spotlight.py
 685 | @@ -55,7 +55,7 @@ RUNTIME_S = PP.SPOT_RUNTIME_S          # ruling 90: total 28 to 50 s (the render
 686 |  SNAP_TO_S = round(max(SPOT_S[0], RUNTIME_S[0] - P.FINAL_TAIL_S), 2)
 687 |  #   13.7 s: the factory's tail (sign-off, credits card, outro, edges) is 14.3 s, so with no closing line (ruling 91's
 688 |  #   default) a shorter clip cannot reach 28 s. A moment shorter than this is snapped; it is never padded.
 689 | -HOOK_MIN = 4                           # ruling 90: >= 4 on the hook's own job (package.hook_own: scroll / alone)
 690 | +#   The opener's own job: ruling 90's ">= 4" (HOOK_MIN) is ruling 115's calibrated bar now (package.hook_own "passes").
 691 |  ALONE_MIN = 4.0                        # ruling 90: >= 4 standing alone, by the ALONE scorer (its scale is 1-5)
 692 |  CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
 693 |  COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
 694 | @@ -738,10 +738,12 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 695 |                            by_rule="ruling 90: the visual check clean (no ruling-70 flag, not blocked as a hook, and "
 696 |                                    "eligible on its frames under ruling 93; a ruling-93 burned_in flag is listed)")
 697 |      own, hr = P.hook_own(m), m.get("hook_rating") or {}
 698 | -    rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 699 | +    rows["hook_own"] = _row(own is not None and own["passes"], hr.get("backend"),
 700 |                              bool(hr.get("replayed", False)), measured=own is not None,
 701 |                              rating=(own or {}).get("rating"), scroll=hr.get("scroll"), alone=hr.get("alone"),
 702 | -                            why=hr.get("why"), min=HOOK_MIN, rule="ruling 90: >= 4 on the hook's own job (ruling 61)")
 703 | +                            setup=hr.get("setup"), why=hr.get("why"), bar=(own or {}).get("bar"),
 704 | +                            rule="ruling 115: every part (scroll, alone, setup) at least its calibrated floor, rated "
 705 | +                                 "by the calibrated rater")
 706 |      sv = P.verdict_of(m)
 707 |      rows["stands_alone"] = _row(sv is not None and float(sv["score"]) >= ALONE_MIN,
 708 |                                  f"the ALONE scorer ({(sv or {}).get('model')}, the render's stand_alone scorer as the "
 709 | @@ -818,8 +820,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 710 |      stage and why it stopped), "finalists", "near", "why_none", ...}. The stages run cheapest first, each on what the
 711 |      one before passed; every verdict is the medley's own and cached or recorded across builds: step A
 712 |      (package.prescreen), L-v 2 and CUTTABLE (truth_for), G17a (hook_onset_for), the render's hook rules and the hook's
 713 | -    own-job rating (package._can_open, hook_ratings: >= HOOK_MIN), the visual check clean (visual_pin: measured, no
 714 | -    flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 715 | +    own-job rating (package._can_open, hook_ratings: ruling 115's calibrated bar), the visual check clean
 716 | +    (visual_pin: measured, no flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 717 |      (a moment with no rating yet waits up to wait_s for the integrator's pass, polling the verdicts file), ruling 92's
 718 |      source test; then, best first (rank_key), up to `finalists` moments: the exclusion verdict, the render's lock
 719 |      pre-check (lock_check; no verdict stops the search, as in a medley build) and package_for(). lock_check None: no
 720 | @@ -907,10 +909,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 721 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": f"not rated: {herr}"}
 722 |          own = P.hook_own(m)
 723 |          rec[mid]["hook_own"] = (own or {}).get("rating")
 724 | -        if own is not None and own["rating"] >= HOOK_MIN:
 725 | +        if own is not None and own["passes"]:              # ruling 115: the calibrated bar
 726 |              strong[mid] = m
 727 |          else:
 728 | -            stop(mid, f"the hook's own job rates {(own or {}).get('rating')} (needs {HOOK_MIN}): "
 729 | +            stop(mid, f"the hook's own job: {(own or {}).get('short') or 'not rated'} ({(own or {}).get('bar')}): "
 730 |                        f"{m['hook_rating'].get('why')}")
 731 |      passed(strong, 4)
 732 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
 733 | @@ -988,7 +990,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 734 |      ranked = sorted(ok_src, key=rank_key)
 735 |      out["finalists"] = [m["moment_id"] for m in ranked]
 736 |      log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
 737 | -        f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
 738 | +        f"pass the calibrated hook bar as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
 739 |          f"{ALONE_MIN:g}, {len(ranked)} from a conversation ({time.time() - t0:.0f} s)")
 740 |      exc_cache = {}
 741 |      for m in ranked[:finalists]:
 742 | @@ -1020,6 +1022,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 743 |          if pk is not None:
 744 |              pk["seconds"] = round(time.time() - t0, 1)
 745 |              out["package"] = pk
 746 | +            pk["hook_bar"] = P.hook_bar_mark()          # RULING 115 (2): sealed on the calibrated bar, said so
 747 |              rec[mid]["out"] = "PACKAGE"
 748 |              break
 749 |          stop(mid, why_p)
 750 | diff --git a/tests/package/conftest.py b/tests/package/conftest.py
 751 | new file mode 100644
 752 | index 0000000..0e67912
 753 | --- /dev/null
 754 | +++ b/tests/package/conftest.py
 755 | @@ -0,0 +1,32 @@
 756 | +"""RULING 115: THE RIGS' HOOK BAR. Every test under tests/package judges hooks on a calibrated bar whose floors are
 757 | +PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (scroll 3, alone 4, setup 3), for the
 758 | +rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
 759 | +verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
 760 | +tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
 761 | +class that needs production's calibration file sets `real_hook_bar = True`."""
 762 | +import os
 763 | +import sys
 764 | +
 765 | +import pytest
 766 | +
 767 | +HERE = os.path.dirname(os.path.abspath(__file__))
 768 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
 769 | +import package as PK  # noqa: E402
 770 | +
 771 | +RIG_RATER = "xai:grok"
 772 | +RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}
 773 | +
 774 | +
 775 | +def rig_bar():
 776 | +    return {"floors": dict(RIG_FLOORS), "sha256": "t" * 64, "rater": RIG_RATER,
 777 | +            "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}
 778 | +
 779 | +
 780 | +@pytest.fixture(autouse=True)
 781 | +def _rig_hook_bar(request, monkeypatch):
 782 | +    if getattr(request.cls, "real_hook_bar", False):
 783 | +        yield
 784 | +        return
 785 | +    bar = rig_bar()
 786 | +    monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
 787 | +    yield
 788 | diff --git a/tests/package/hook112.py b/tests/package/hook112.py
 789 | index 61686b4..6d1a84a 100644
 790 | --- a/tests/package/hook112.py
 791 | +++ b/tests/package/hook112.py
 792 | @@ -388,11 +388,16 @@ def ref_moments(refs=REFS):
 793 |      return out
 794 |  
 795 |  
 796 | -def heimdall_hook_chain(router):
 797 | -    """Ruling 88's hook list as production reads it, with every non-Heimdall back-end removed (the order: Heimdall
 798 | +RULING_96_HOOK = ("heimdall:qwen/qwen3.8-27b", "heimdall:z-ai/glm-5.3-flash", "heimdall:deepseek/deepseek-v4.1-flash")
 799 | +#   ruling 96's hook list without Grok: the Heimdall list ruling 112 measured. Production's hook list is Grok ALONE since
 800 | +#   ruling 115 (the calibrated rater), so the driver names its Heimdall list instead of reading production's.
 801 | +
 802 | +
 803 | +def heimdall_hook_chain(router, names=None):
 804 | +    """`names` (default: the router's own hook list) with every non-Heimdall back-end removed, in order (Heimdall
 805 |      only). Refused when none is left."""
 806 | -    chain = [n for n in router.chain("coherence_verdict", "hook")   # a Heimdall back-end's vendor is "heimdall/<family>"
 807 | -             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]
 808 | +    chain = [n for n in (names or router.chain("coherence_verdict", "hook"))   # a Heimdall back-end's vendor is
 809 | +             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]   # "heimdall/<family>"
 810 |      if not chain:
 811 |          raise RuntimeError("refused: ruling 88's hook list has no Heimdall back-end")
 812 |      return chain
 813 | @@ -405,13 +410,15 @@ def registry(path=os.path.join(REPO, "pipeline", "channels.json")):
 814 |          return json.load(f)
 815 |  
 816 |  
 817 | -def build_router(spend_path=SPEND, record_dir=None):
 818 | +def build_router(spend_path=SPEND, record_dir=None, hook_chain=RULING_96_HOOK):
 819 | +    """The driver's router: Heimdall only for the hook job (`hook_chain`, filtered to Heimdall), ruling 48's ledger
 820 | +    on reported spend under LIMIT_USD."""
 821 |      import deadline_table as DT
 822 |      import providers as P
 823 |      import replay85 as R
 824 |      r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 825 |                   limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))
 826 | -    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)
 827 | +    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r, list(hook_chain))
 828 |      return r
 829 |  
 830 |  
 831 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 832 | index 2f200ba..881884a 100644
 833 | --- a/tests/package/proof_ledger.py
 834 | +++ b/tests/package/proof_ledger.py
 835 | @@ -70,6 +70,7 @@ import shadow86 as SH  # noqa: E402
 836 |  import ledger_build as LB  # noqa: E402
 837 |  import moments as M  # noqa: E402
 838 |  import package as PK  # noqa: E402
 839 | +import hook_bar as HB  # noqa: E402
 840 |  import package_pin  # noqa: E402
 841 |  import proof_ly as PL  # noqa: E402
 842 |  import proof_saved_runs as PS  # noqa: E402
 843 | @@ -155,6 +156,19 @@ def open_work(res, sp):
 844 |      return held + no_verdict + int(vis.get("unmeasured") or 0)
 845 |  
 846 |  
 847 | +HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding
 848 | +
 849 | +
 850 | +def build_shadow(routing, rt, streak):
 851 | +    """The build's shadow back-ends: RULING 86, Grok (routing.shadow) on the first heimdall_first pins, until
 852 | +    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first); RULING 115,
 853 | +    qwen on every hook, in every build. Recorded, never deciding."""
 854 | +    shadow = None
 855 | +    if routing == "heimdall_first" and streak() < int(rt.get("shadow_until_clean_pins") or 3):
 856 | +        shadow = rt.get("shadow") or None
 857 | +    return dict(shadow or {}, **HOOK_SHADOW)
 858 | +
 859 | +
 860 |  def nothing_new(proof_dir, out_dir, fp):
 861 |      """RULING 107 (1): the newest earlier FINISHED build (its FINGERPRINT.json) when its fingerprint is this build's and
 862 |      it left nothing undone; else None. A build that stopped early writes none, and neither does a --from-candidate
 863 | @@ -431,12 +445,13 @@ def main(argv=None):
 864 |          return 0
 865 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
 866 |      routing = a.routing or rt.get("mode") or "today"
 867 | -    shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 868 | -    if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 869 | -        shadow = rt.get("shadow") or None
 870 | +    shadow = build_shadow(routing, rt, SH.clean_streak)   # RULING 86 (Grok) / RULING 115 (qwen on every hook)
 871 |      router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 872 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 873 | -        + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 874 | +        + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
 875 | +    live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 876 | +    say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
 877 | +        + (f" [{live_why}]" if live_why else ""))
 878 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 879 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 880 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 881 | diff --git a/tests/package/test_hook112.py b/tests/package/test_hook112.py
 882 | index 57161c8..3a5a376 100644
 883 | --- a/tests/package/test_hook112.py
 884 | +++ b/tests/package/test_hook112.py
 885 | @@ -215,7 +215,10 @@ class TestTheCalibration(unittest.TestCase):
 886 |          chain = r.chain("coherence_verdict", "hook")
 887 |          self.assertTrue(chain and all(r.backends[n].vendor.split("/")[0] == "heimdall" for n in chain), chain)
 888 |          self.assertNotIn("xai:grok-4.20-0309-reasoning", chain)
 889 | -        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 88's order, Grok removed
 890 | +        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 96's order, Grok removed
 891 | +        with tempfile.TemporaryDirectory() as d:                      # production's list (Grok alone, ruling 115)
 892 | +            with self.assertRaises(RuntimeError):                     # has no Heimdall back-end: refused, never Grok
 893 | +                H.build_router(spend_path=os.path.join(d, "SPEND.json"), hook_chain=("xai:grok-4.20-0309-reasoning",))
 894 |          self.assertEqual((r.limit_usd, r.limit_basis), (H.LIMIT_USD, "reported"))
 895 |  
 896 |      def test_heimdall_only_and_refused_without_one(self):
 897 | diff --git a/tests/package/test_hook_bar.py b/tests/package/test_hook_bar.py
 898 | new file mode 100644
 899 | index 0000000..5637ae4
 900 | --- /dev/null
 901 | +++ b/tests/package/test_hook_bar.py
 902 | @@ -0,0 +1,211 @@
 903 | +#!/usr/bin/env python3
 904 | +"""RULING 115 (orchestrator 13:24 ET Nov 15): THE CALIBRATED HOOK BAR (pipeline/hook_bar.py). A hook passes when each of
 905 | +scroll / alone / setup is at least the LOWEST value that part takes across PBX's approved hooks under the same asking
 906 | +(ALONE, production's seed, Grok); no floor under 3; one sealed calibration file, valid for its rater, question version,
 907 | +seed and asking, for 24 h; a package sealed on it says so; PBX's verdicts on such packages are appended as examples.
 908 | +The live file is checked against its source and against production's hook job."""
 909 | +import copy
 910 | +import json
 911 | +import os
 912 | +import sys
 913 | +import tempfile
 914 | +import unittest
 915 | +from datetime import datetime, timedelta, timezone
 916 | +
 917 | +HERE = os.path.dirname(os.path.abspath(__file__))
 918 | +REPO = os.path.dirname(os.path.dirname(HERE))
 919 | +for _p in ("pipeline", "tests/package"):
 920 | +    sys.path.insert(0, os.path.join(REPO, _p))
 921 | +import hook_bar as HB  # noqa: E402
 922 | +import package as PK  # noqa: E402
 923 | +import package_pin as PP  # noqa: E402
 924 | +
 925 | +AT = datetime(2026, 11, 15, 18, 7, 52, tzinfo=timezone.utc)
 926 | +G = "xai:grok-4.20-0309-reasoning"
 927 | +Q = "heimdall:qwen/qwen3.8-27b"
 928 | +
 929 | +
 930 | +def approved(*parts):
 931 | +    return [{"ref": f"ref-{i}", "scroll": s, "alone": a, "setup": u, "backend": G} for i, (s, a, u) in enumerate(parts)]
 932 | +
 933 | +
 934 | +def cal(parts=((3, 4, 3), (3, 5, 4), (4, 5, 4)), **kw):
 935 | +    ap = approved(*parts)
 936 | +    fl, low = HB.floors_from(ap)
 937 | +    return dict({"rater": G, "asking": "alone", "seed": 7, "question_version": "qv", "measured_at": AT.isoformat(),
 938 | +                 "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 939 | +
 940 | +
 941 | +class TestFloors(unittest.TestCase):
 942 | +    def test_each_floor_is_its_parts_lowest_value_across_the_approved_hooks(self):
 943 | +        self.assertEqual(HB.floors_from(approved((3, 4, 3), (3, 5, 4), (4, 5, 4))),
 944 | +                         ({"scroll": 3, "alone": 4, "setup": 3}, []))
 945 | +        self.assertEqual(HB.floors_from(approved((5, 5, 5), (4, 5, 5))), ({"scroll": 4, "alone": 5, "setup": 5}, []))
 946 | +
 947 | +    def test_a_floor_under_3_stops_at_3_and_is_told(self):
 948 | +        fl, low = HB.floors_from(approved((2, 5, 4), (3, 1, 4)))
 949 | +        self.assertEqual(fl, {"scroll": 3, "alone": 3, "setup": 4})
 950 | +        self.assertEqual(low, ["scroll 2 (stopped at 3)", "alone 1 (stopped at 3)"])
 951 | +
 952 | +    def test_a_part_missing_or_not_an_integer_measures_nothing(self):
 953 | +        for bad in ([{"scroll": 3, "alone": 4}], [{"scroll": 3, "alone": 4, "setup": 3.0}],
 954 | +                    [{"scroll": True, "alone": 4, "setup": 3}], []):
 955 | +            with self.assertRaises(ValueError):
 956 | +                HB.floors_from(bad)
 957 | +
 958 | +
 959 | +class TestTheFile(unittest.TestCase):
 960 | +    def setUp(self):
 961 | +        self.d = tempfile.TemporaryDirectory()
 962 | +        self.path = os.path.join(self.d.name, "hook_calibration.json")
 963 | +
 964 | +    def tearDown(self):
 965 | +        self.d.cleanup()
 966 | +
 967 | +    def bar(self, now=AT + timedelta(hours=1), **kw):
 968 | +        a = dict(dict(rater=None, question_version="qv", seed=7), **kw)
 969 | +        return HB.bar(a["rater"], a["question_version"], a["seed"], now=now, path=self.path)
 970 | +
 971 | +    def test_written_sealed_and_read_back_as_the_live_bar(self):
 972 | +        c = HB.write(cal(), self.path)
 973 | +        self.assertEqual(c["sha256"], HB.body_sha(c))
 974 | +        live, why = self.bar()
 975 | +        self.assertIsNone(why)
 976 | +        self.assertEqual((live["floors"], live["rater"], live["sha256"]),
 977 | +                         ({"scroll": 3, "alone": 4, "setup": 3}, G, c["sha256"]))
 978 | +        self.assertIn(f"scroll >= 3, alone >= 4, setup >= 3, on {G} asked alone at seed 7 (calibration "
 979 | +                      f"{c['sha256'][:12]})", HB.text(live))
 980 | +
 981 | +    def test_a_hand_edit_breaks_the_seal_and_no_hook_passes(self):
 982 | +        HB.write(cal(), self.path)
 983 | +        with open(self.path) as f:
 984 | +            c = json.load(f)
 985 | +        c["floors"]["alone"] = 3                                          # edited, not re-sealed
 986 | +        with open(self.path, "w") as f:
 987 | +            json.dump(c, f)
 988 | +        live, why = self.bar()
 989 | +        self.assertIsNone(live)
 990 | +        self.assertIn("sha256 does not match", why)
 991 | +        self.assertEqual(HB.passes({"scroll": 5, "alone": 5, "setup": 5, "backend": G}, live),
 992 | +                         (False, "no valid hook calibration"))
 993 | +        self.assertEqual(HB.text(live), "no valid hook calibration: no hook passes")
 994 | +
 995 | +    def test_missing_or_unreadable_is_no_bar(self):
 996 | +        live, why = self.bar()
 997 | +        self.assertIsNone(live)
 998 | +        self.assertIn("cannot be read", why)
 999 | +        with open(self.path, "w") as f:
1000 | +            f.write("{not json")
1001 | +        self.assertIsNone(self.bar()[0])
1002 | +
1003 | +    def test_valid_only_for_its_question_version_seed_asking_and_rater(self):
1004 | +        HB.write(cal(), self.path)
1005 | +        self.assertIsNotNone(self.bar(rater=G)[0])
1006 | +        for kw in ({"question_version": "another"}, {"seed": 8}, {"rater": Q}):
1007 | +            live, why = self.bar(**kw)
1008 | +            self.assertIsNone(live, kw)
1009 | +            self.assertIn("no hook passes until it is re-run", why)
1010 | +        HB.write(cal(asking="batched"), self.path)                         # the batch moved single ratings
1011 | +        self.assertIsNone(self.bar()[0])
1012 | +
1013 | +    def test_once_a_day_a_stale_calibration_passes_nothing(self):
1014 | +        HB.write(cal(), self.path)
1015 | +        self.assertIsNotNone(self.bar(now=AT + timedelta(hours=23, minutes=59))[0])
1016 | +        live, why = self.bar(now=AT + timedelta(hours=24, minutes=1))
1017 | +        self.assertIsNone(live)
1018 | +        self.assertIn("over 24 h old", why)
1019 | +
1020 | +    def test_a_floor_under_3_in_the_file_is_refused(self):
1021 | +        HB.write(cal(floors={"scroll": 2, "alone": 4, "setup": 3}), self.path)
1022 | +        live, why = self.bar()
1023 | +        self.assertIsNone(live)
1024 | +        self.assertIn("a floor under 3", why)
1025 | +
1026 | +
1027 | +class TestPasses(unittest.TestCase):
1028 | +    LIVE = {"floors": {"scroll": 3, "alone": 4, "setup": 3}, "rater": G, "sha256": "s" * 64, "seed": 7}
1029 | +
1030 | +    def ok(self, s, a, u, b=G):
1031 | +        return HB.passes({"scroll": s, "alone": a, "setup": u, "backend": b}, self.LIVE)
1032 | +
1033 | +    def test_every_part_at_least_its_floor_by_the_calibrated_rater(self):
1034 | +        self.assertEqual(self.ok(3, 4, 3), (True, None))                  # at every floor
1035 | +        self.assertEqual(self.ok(5, 5, 5), (True, None))
1036 | +        self.assertEqual(self.ok(2, 4, 3), (False, "scroll 2 < 3"))
1037 | +        self.assertEqual(self.ok(3, 3, 3), (False, "alone 3 < 4"))
1038 | +        self.assertEqual(self.ok(3, 4, 2), (False, "setup 2 < 3"))
1039 | +        self.assertEqual(self.ok(2, 3, 2), (False, "scroll 2 < 3; alone 3 < 4; setup 2 < 3"))
1040 | +        self.assertEqual(self.ok(5, 5, 5, Q), (False, f"rated by {Q}, but the bar is calibrated on {G}"))
1041 | +        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "backend": G}, self.LIVE)[0])           # a part missing
1042 | +        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "setup": True, "backend": G}, self.LIVE)[0])
1043 | +
1044 | +
1045 | +class TestExamples(unittest.TestCase):
1046 | +    """RULING 115 (2): PBX's approve or reject of a package sealed on the bar is appended as an example."""
1047 | +
1048 | +    def test_approved_and_rejected_with_his_reason_appended_sealed_and_the_floors_unchanged(self):
1049 | +        with tempfile.TemporaryDirectory() as d:
1050 | +            path = os.path.join(d, "c.json")
1051 | +            HB.write(cal(), path)
1052 | +            hook = {"moment_id": "m1", "text": "Bitcoin t.", "channel": "A", "scroll": 3, "alone": 4, "setup": 3,
1053 | +                    "backend": G, "extra": 1}
1054 | +            HB.add_example("story-1", "approved", hook, path=path, now=AT)
1055 | +            c = HB.add_example("story-2", "rejected", hook, reason="the opener is mid-sentence", path=path, now=AT)
1056 | +            self.assertEqual([(e["story_id"], e["verdict"], e["reason"]) for e in c["examples"]],
1057 | +                             [("story-1", "approved", None), ("story-2", "rejected", "the opener is mid-sentence")])
1058 | +            self.assertNotIn("extra", c["examples"][0]["hook"])
1059 | +            self.assertEqual(HB.load(path)[0], c)                          # sealed
1060 | +            self.assertEqual(c["floors"], cal()["floors"])                  # a new floor comes from the next run
1061 | +            for verdict, reason in (("rejected", None), ("maybe", "r")):    # a rejection carries his reason
1062 | +                with self.assertRaises(ValueError):
1063 | +                    HB.add_example("story-3", verdict, hook, reason=reason, path=path)
1064 | +            self.assertEqual(len(HB.load(path)[0]["examples"]), 2)
1065 | +
1066 | +
1067 | +class TestTheMark(unittest.TestCase):
1068 | +    """RULING 115 (2): a package sealed on the bar says so in its record and in its pin, in one plain line, outside
1069 | +    the seal (the integrator prints it in the Telegram note)."""
1070 | +
1071 | +    def test_the_pin_carries_the_line_outside_the_seal(self):
1072 | +        import test_angles as TA
1073 | +        base = TA.TestPinAndTruth.pk(None)
1074 | +        plain = PP.to_pin(copy.deepcopy(base), "r")
1075 | +        self.assertNotIn("hook_bar", plain["moments_package"])
1076 | +        pin = PP.to_pin(dict(copy.deepcopy(base), hook_bar=PK.hook_bar_mark()), "r")
1077 | +        mp = pin["moments_package"]
1078 | +        self.assertEqual((mp["hook_bar"]["note"], mp["hook_bar"]["floors"], mp["hook_bar"]["ruling"]),
1079 | +                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}, "115"))
1080 | +        self.assertEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])   # outside the seal
1081 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
1082 | +
1083 | +
1084 | +class TestTheLiveCalibration(unittest.TestCase):
1085 | +    """The calibration production reads (pipeline/hook_calibration.json): its floors are derived from their source
1086 | +    (tests/package/proof/hook113/ALONE_TEST.json: Grok asked alone at seed 7; the two out-of-contract first answers
1087 | +    asked once more), and it is for production's question version, seed and hook list."""
1088 | +    real_hook_bar = True
1089 | +
1090 | +    def test_its_floors_are_its_sources_lowest_parts(self):
1091 | +        c, why = HB.load()
1092 | +        self.assertIsNone(why)
1093 | +        with open(os.path.join(REPO, "tests", "package", "proof", "hook113", "ALONE_TEST.json")) as f:
1094 | +            src = json.load(f)
1095 | +        grok = dict(src["models"][c["rater"]], **src["retries"])          # a retry answers for an out-of-contract ask
1096 | +        self.assertEqual(sorted(a["ref"] for a in c["approved"]), sorted(grok))
1097 | +        for a in c["approved"]:
1098 | +            self.assertEqual({p: a[p] for p in HB.PARTS}, {p: grok[a["ref"]][p] for p in HB.PARTS}, a["ref"])
1099 | +            self.assertEqual(grok[a["ref"]]["backend"], c["rater"])
1100 | +        self.assertEqual(HB.floors_from(c["approved"]), (c["floors"], c["floors_below_3"]))
1101 | +        self.assertEqual((c["seed"], c["asking"]), (src["seed"], "alone"))
1102 | +
1103 | +    def test_it_is_for_productions_question_seed_and_hook_list(self):
1104 | +        import providers as P
1105 | +        c, _ = HB.load()
1106 | +        self.assertEqual((c["question_version"], c["seed"]), (PK.HOOK_VERSION, PK.HOOK_SEED))
1107 | +        for routing in P.ROUTINGS:
1108 | +            r = P.Router(env_path="/nonexistent", routing=routing)
1109 | +            self.assertEqual(r.chain("coherence_verdict", "hook"), [c["rater"]], routing)
1110 | +
1111 | +
1112 | +if __name__ == "__main__":
1113 | +    unittest.main()
1114 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
1115 | index 5a109eb..2a117a7 100644
1116 | --- a/tests/package/test_ledger_build.py
1117 | +++ b/tests/package/test_ledger_build.py
1118 | @@ -903,6 +903,24 @@ class TestRuling85NoXai(unittest.TestCase):
1119 |                  return name
1120 |          return None
1121 |  
1122 | +    def test_ruling_115_qwen_shadows_every_hook_in_every_build(self):
1123 | +        """RULING 115: qwen answers every hook in shadow (recorded, never deciding), with ruling 86's Grok shadow on the
1124 | +        first heimdall_first pins and without it after; the streak is read only under heimdall_first."""
1125 | +        import proof_ledger as PLG
1126 | +        X, Q = "xai:grok-4.20-0309-reasoning", "heimdall:qwen/qwen3.8-27b"
1127 | +        rt = {"shadow": {"*": X}, "shadow_until_clean_pins": 3}
1128 | +        hook = {"coherence_verdict:hook": Q}
1129 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 0), {"*": X, **hook})
1130 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 3), hook)
1131 | +
1132 | +        def never():
1133 | +            raise AssertionError("the streak is read under heimdall_first only")
1134 | +        self.assertEqual(PLG.build_shadow("today", rt, never), hook)
1135 | +        r = self.pl().P.Router(env_path="/nonexistent", routing="heimdall_first",
1136 | +                               shadow=PLG.build_shadow("heimdall_first", rt, lambda: 0))
1137 | +        self.assertEqual((r._shadow_of("coherence_verdict", "hook"), r._shadow_of("coherence_verdict", "coherence")),
1138 | +                         (Q, X))                                       # the router reads them as ruled
1139 | +
1140 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
1141 |          """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
1142 |          rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
1143 | @@ -918,12 +936,15 @@ class TestRuling85NoXai(unittest.TestCase):
1144 |          #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
1145 |          self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
1146 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
1147 | -        self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
1148 | +        self.assertEqual(ch["coherence_verdict:hook"], [X])                        # RULING 115 (amends 88 (b) / 96 for
1149 | +        #   the hook): Grok ALONE, the rater the calibrated floors are measured on (qwen in shadow, never deciding)
1150 |          self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
1151 |          self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
1152 |          self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
1153 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
1154 |          self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
1155 | +        self.assertEqual((today["coherence_verdict:hook"], PL.plan_b_chains()["coherence_verdict:hook"]), ([X], [X]))
1156 | +        #   RULING 115: the hook is Grok's alone in every routing (no uncalibrated rating is ever cached as a hook's)
1157 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
1158 |          for n in [n for n in r.backends if n.startswith("xai")]:
1159 |              r.down[n] = "xAI answers nothing (the test)"
1160 | @@ -934,7 +955,8 @@ class TestRuling85NoXai(unittest.TestCase):
1161 |              ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
1162 |          self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
1163 |                                 ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
1164 | -                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
1165 | +                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): None,   # ruling 115:
1166 | +                               #   no other model decides a hook while Grok is out (no rating = no hook, law L-m)
1167 |                                 ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
1168 |                                 ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
1169 |          r.down[GEM] = "Gemini answers nothing (the test)"
1170 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1171 | index 5e7aa2f..6dd1c07 100644
1172 | --- a/tests/package/test_medley.py
1173 | +++ b/tests/package/test_medley.py
1174 | @@ -156,8 +156,8 @@ class TestMedleyLineup(unittest.TestCase):
1175 |  
1176 |  
1177 |  class TestClipsAloneVerdict(unittest.TestCase):
1178 | -    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2}), pm("x", "B", 14.0),
1179 | -            pm("y", "C", 13.0)]
1180 | +    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"}),
1181 | +            pm("x", "B", 14.0), pm("y", "C", 13.0)]   # ruling 115: rated by the rigs' calibrated rater (conftest)
1182 |      LABS = ["hook", "clip_01", "clip_02"]
1183 |  
1184 |      def run_it(self, reply):
1185 | @@ -190,7 +190,10 @@ class TestClipsAloneVerdict(unittest.TestCase):
1186 |          self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
1187 |          self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])
1188 |  
1189 | -    def test_ruling_61_the_hook_is_rated_once_its_cached_own_job_rating_stands(self):
1190 | +    def test_ruling_61_115_the_hook_is_rated_once_and_passes_by_its_calibrated_bar(self):
1191 | +        """Ruling 61: the hook is not rated in the line-up's verdict; its cached own-job rating stands. Ruling 115:
1192 | +        it passes when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4, setup 3), rated by
1193 | +        the calibrated rater; its slot is judged by that bar, never by COHERENCE_MIN; the clips keep their bar."""
1194 |          prompts = []
1195 |          r = Canned(coherence_verdict=[reply(self.LABS)])
1196 |          call = r.call
1197 | @@ -198,15 +201,25 @@ class TestClipsAloneVerdict(unittest.TestCase):
1198 |          ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1199 |          self.assertTrue(ok)
1200 |          self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})   # min(scroll 5, alone 4), cached
1201 | -        self.assertEqual((v["hook_own"]["scroll"], v["hook_own"]["alone"], v["hook_own"]["rating"]), (5, 4, 4))
1202 | +        self.assertEqual(tuple(v["hook_own"][k] for k in ("scroll", "alone", "setup", "rating", "passes")),
1203 | +                         (5, 4, 3, 4, True))
1204 |          self.assertNotIn(PK.HOOK_QUESTION, prompts[0])                         # never re-asked per line-up
1205 |          self.assertIn("NOT rated here", prompts[0])
1206 |          self.assertIn('"hook -> clip_01"', prompts[0])                         # 'sets up': the hook's own join
1207 |          self.assertNotIn('"hook": 1', prompts[0])
1208 |          self.assertIn('"clip_01": 1, "clip_02": 1', prompts[0])
1209 | -        low = [dict(self.SEGS[0], hook_rating={"scroll": 3, "alone": 5, "setup": 5}), *self.SEGS[1:]]
1210 | -        ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), low, E.Context(NOW, REG), set())
1211 | -        self.assertFalse(ok)                                                   # its cached rating is under the bar
1212 | +        run = lambda hr: PK.medley(Canned(coherence_verdict=[reply(self.LABS)]),
1213 | +                                   [dict(self.SEGS[0], hook_rating=hr), *self.SEGS[1:]], E.Context(NOW, REG), set())
1214 | +        ok, v = run({"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"})   # every part AT its floor
1215 | +        self.assertEqual((ok, v["clips"]["hook"], v["hook_own"]["passes"]), (True, 3, True))   # 3 < COHERENCE_MIN
1216 | +        for hr in ({"scroll": 2, "alone": 5, "setup": 5, "backend": "xai:grok"},   # one part under its floor
1217 | +                   {"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
1218 | +                   {"scroll": 5, "alone": 5, "setup": 2, "backend": "xai:grok"},   # setup counts (ruling 115)
1219 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"},   # not the rater
1220 | +                   {"scroll": 5, "alone": 5, "backend": "xai:grok"}):              # a part missing: fail closed
1221 | +            ok, v = run(hr)
1222 | +            self.assertFalse(ok, hr)
1223 | +            self.assertIs(v["hook_own"].get("passes", False), False)
1224 |          ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), [pm("h", "A", 12.0), *self.SEGS[1:]],
1225 |                            E.Context(NOW, REG), set())
1226 |          self.assertFalse(ok)                                                   # no cached rating: fail closed
1227 | @@ -238,7 +251,7 @@ class TestCoherenceHookRatedOnce(unittest.TestCase):
1228 |             "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
1229 |                          {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
1230 |                          {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
1231 | -    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2})
1232 | +    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"})
1233 |  
1234 |      def reply(self, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
1235 |          return {"through_line": line, "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
1236 | @@ -264,6 +277,14 @@ class TestCoherenceHookRatedOnce(unittest.TestCase):
1237 |          self.assertFalse(self.run_it(self.reply(vo=3))[0])
1238 |          self.assertFalse(self.run_it(self.reply(), hook=pm("h", "A", 12.0))[0])   # no cached rating: fail closed
1239 |          self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 5}))[0])
1240 | +        G = "xai:grok"                                        # ruling 115: the hook's slot is its calibrated bar
1241 | +        ok, v, _, _ = self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 4,
1242 | +                                                                                     "setup": 3, "backend": G}))
1243 | +        self.assertEqual((ok, v["clips"]["hook"]), (True, 3))
1244 | +        for hr in ({"scroll": 5, "alone": 5, "setup": 2, "backend": G}, {"scroll": 5, "alone": 3, "setup": 5,
1245 | +                                                                         "backend": G},
1246 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}):
1247 | +            self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating=hr))[0], hr)
1248 |  
1249 |      def test_out_of_contract_is_not_measured(self):
1250 |          good = self.reply()
1251 | @@ -1299,8 +1320,9 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
1252 |  
1253 |  class TestRuling59HookFirst(unittest.TestCase):
1254 |      """RULING 59 (11:00): HOOK FIRST. Every cleared, cuttable moment that can open is rated on the hook's own job (ruling
1255 | -    52's question) in one batched call, cached; only a hook rated >= 4 opens; the angles are written FOR the passing
1256 | -    hooks and tried best hook first; with no passing hook the build stops before any line-up, listing the best three."""
1257 | +    52's question), cached; the angles are written FOR the passing hooks and tried best hook first; with no passing
1258 | +    hook the build stops before any line-up, listing the best three. RULING 115: each candidate is asked ALONE (one
1259 | +    call a candidate), and a hook passes when each of its parts is at least its calibrated floor (the rigs': conftest)."""
1260 |  
1261 |      def canned(self, *replies):
1262 |          c = Canned(coherence_verdict=list(replies))
1263 | @@ -1308,37 +1330,63 @@ class TestRuling59HookFirst(unittest.TestCase):
1264 |          c.backends = {"fake:coherence_verdict": B("fake", "fake")}
1265 |          return c
1266 |  
1267 | -    def test_one_batched_call_rates_every_hook_and_the_rating_is_derived_and_cached(self):
1268 | -        import tempfile
1269 | +    def test_each_candidate_is_asked_alone_one_call_each_and_the_rating_is_derived_and_cached(self):
1270 | +        from unittest import mock
1271 |          ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1272 | -        reply = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"},
1273 | -                           "b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
1274 | +        ra = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"}}}
1275 | +        rb = {"hooks": {"b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
1276 |          with tempfile.TemporaryDirectory() as d:
1277 |              cache = os.path.join(d, "HOOK_CACHE.json")
1278 | -            c = self.canned(reply)
1279 | +            c = self.canned(ra, rb)
1280 |              got, err = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1281 |              self.assertIsNone(err)
1282 | -            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # ONE call, off the writers
1283 | -            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # the lowest part (ruling 52)
1284 | -            self.assertEqual(got["b"]["why"], "needs what came before")
1285 | +            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})] * 2)   # ONE call EACH (ruling
1286 | +            #   115: the asking the calibration measured), off the writers
1287 | +            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # scroll / alone: it ORDERS hooks
1288 | +            self.assertEqual((got["a"]["setup"], got["b"]["why"]), (5, "needs what came before"))   # every part kept
1289 |              again, err = PK.hook_ratings(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1290 |              self.assertEqual((err, again["a"]["rating"], again["a"]["cached"]), (None, 4, True))   # no call at all
1291 |              new = [dict(ms[0], text="Bitcoin is a new text now."), ms[1]]
1292 |              c = self.canned({"hooks": {"a": {"scroll": 3, "alone": 3, "setup": 3, "why": "w"}}})
1293 |              got, _ = PK.hook_ratings(c, new, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1294 |              self.assertEqual((len(c.calls), got["a"]["rating"], got["b"]["cached"]), (1, 3, True))   # its new text only
1295 | +            with mock.patch.object(PK, "HOOK_VERSION", "another-asking"):   # a rating cached under another question
1296 | +                c = self.canned(ra, rb)                                      # or asking never answers (the batched
1297 | +                got, _ = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # ratings of before)
1298 | +                self.assertEqual((len(c.calls), got["a"]["cached"], got["b"]["cached"]), (2, False, False))
1299 | +
1300 | +    def test_a_candidate_left_unrated_never_stops_the_others_being_asked(self):
1301 | +        """RULING 115: one call a candidate; a candidate whose chain is spent has no rating (law L-m), the others are
1302 | +        still asked, and the first error is returned."""
1303 | +        import providers as P
1304 | +        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1305 | +        c = self.canned()
1306 | +        asked = []
1307 | +
1308 | +        def call(role, prompt, *a, **k):
1309 | +            asked.append(re.findall(r'CANDIDATE id="(\w+)"', prompt))
1310 | +            if 'CANDIDATE id="a"' in prompt:
1311 | +                raise P.ProviderError("coherence_verdict: every back-end unavailable")
1312 | +            return P.Reply(json.dumps({"hooks": {"b": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}),
1313 | +                           "fake:coherence_verdict", "fake")
1314 | +        c.call = call
1315 | +        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
1316 | +        self.assertEqual((asked, sorted(got), got["b"]["rating"]), ([["a"], ["b"]], ["b"], 4))
1317 | +        self.assertIn("ProviderError: coherence_verdict: every back-end unavailable", err)
1318 |  
1319 |      def test_the_prompt_asks_ruling_52s_question_of_each_candidate_alone(self):
1320 |          ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1321 |          prompts = []
1322 | -        c = self.canned({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"} for k in "ab"}})
1323 | +        c = self.canned(*({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"}}} for k in "ab"))
1324 |          call = c.call
1325 |          c.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1326 |          PK.hook_ratings(c, ms, ctx(), set(), set())
1327 | -        self.assertIn(PK.HOOK_QUESTION, prompts[0])                       # ONE definition of the hook's job
1328 | -        self.assertIn('CANDIDATE id="a"', prompts[0])
1329 | -        self.assertIn('CANDIDATE id="b"', prompts[0])
1330 | -        self.assertIn("Judge each one ALONE", prompts[0])
1331 | +        self.assertEqual(len(prompts), 2)                                 # ruling 115: ONE candidate a call
1332 | +        for p, me, other in ((prompts[0], "a", "b"), (prompts[1], "b", "a")):
1333 | +            self.assertIn(PK.HOOK_QUESTION, p)                            # ONE definition of the hook's job
1334 | +            self.assertIn(f'CANDIDATE id="{me}"', p)
1335 | +            self.assertNotIn(f'CANDIDATE id="{other}"', p)
1336 | +            self.assertIn("Judge each one ALONE", p)
1337 |  
1338 |      def chained(self, *replies):
1339 |          """A canned chain: each call is answered by the next model (fake:1, fake:2, ...), and a model the caller
1340 | @@ -1375,27 +1423,40 @@ class TestRuling59HookFirst(unittest.TestCase):
1341 |          self.assertEqual(got, {})
1342 |          self.assertIn("ProviderError", err)
1343 |  
1344 | -    def test_only_a_hook_rated_4_or_more_opens(self):
1345 | +    def test_only_a_hook_on_its_calibrated_bar_opens(self):
1346 | +        """RULING 115: a rated hook opens when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4,
1347 | +        setup 3) and the calibrated rater rated it; with no valid calibration no rated hook opens (fail closed)."""
1348 | +        from unittest import mock
1349 |          m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
1350 |          self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
1351 | -        for (sc, al, se), ok in (((4, 4, 1), True), ((5, 4, 5), True), ((3, 5, 5), False), ((5, 3, 5), False)):
1352 | -            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se})
1353 | -            self.assertEqual(PK.can_open(r), ok, (sc, al, se))           # ruling 61: scroll / alone, never setup
1354 | +        G = "xai:grok"
1355 | +        for (sc, al, se), ok in (((3, 4, 3), True), ((5, 4, 5), True), ((2, 5, 5), False), ((5, 3, 5), False),
1356 | +                                 ((5, 5, 2), False)):                     # setup counts now (ruling 115)
1357 | +            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se, "backend": G})
1358 | +            self.assertEqual(PK.can_open(r), ok, (sc, al, se))
1359 |              self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
1360 | -        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5}, {"scroll": 5.0, "alone": 5}):
1361 | +        top = dict(m, hook_rating={"scroll": 5, "alone": 5, "setup": 5, "backend": G})
1362 | +        self.assertFalse(PK.can_open(dict(top, hook_rating=dict(top["hook_rating"],
1363 | +                                                                backend="heimdall:qwen/qwen3.8-27b"))))   # off the rater
1364 | +        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5, "setup": 5, "backend": G},
1365 | +                    {"scroll": 5.0, "alone": 5, "setup": 5, "backend": G}, {"scroll": 5, "alone": 5, "backend": G}):
1366 |              self.assertFalse(PK.can_open(dict(m, hook_rating=bad)), bad)
1367 | -        self.assertFalse(PK.can_open(dict(m, text="And Bitcoin is money.")))   # the render's hook rule
1368 | -        low = dict(m, hook_rating={"scroll": 3, "alone": 4, "setup": 4})
1369 | +        self.assertFalse(PK.can_open(dict(top, text="And Bitcoin is money.")))   # the render's hook rule
1370 | +        low = dict(m, hook_rating={"scroll": 5, "alone": 3, "setup": 4, "backend": G})
1371 |          self.assertFalse(PK.lineup_ok([low, pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
1372 | +        with mock.patch.object(PK, "_live_bar", lambda: (None, "the hook calibration is over 24 h old: re-run it")):
1373 | +            self.assertFalse(PK.can_open(top))                             # no valid calibration: no hook passes
1374 | +            self.assertEqual(PK.hook_own(top)["short"], "the hook calibration is over 24 h old: re-run it")
1375 |  
1376 |      def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
1377 | -        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5})
1378 | +        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5,
1379 | +                                                                                 "backend": "xai:grok"})
1380 |                for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
1381 |          by = {m["moment_id"]: m for m in ms}
1382 |          by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
1383 |          segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
1384 |          self.assertEqual(segs[0]["moment_id"], "a")
1385 | -        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 3, "alone": 5, "setup": 5}))
1386 | +        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"}))
1387 |          self.assertIsNone(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True, hook_only=True))
1388 |          self.assertEqual(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True)[0]["moment_id"], "b")
1389 |          self.assertEqual(PK.swap_lineup(segs, {"a"}, by, keep_hook=True), (None, None))
1390 | @@ -1408,13 +1469,15 @@ class TestRuling59HookFirst(unittest.TestCase):
1391 |      def test_no_hook_in_the_pool_stops_before_the_second_screen_and_lists_the_best_three(self):
1392 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1393 |          rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
1394 | -                  hooks={"h": (3, 4, 4), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})
1395 | +                  hooks={"h": (3, 4, 2), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})   # each under ONE floor
1396 |          out = rig.run()
1397 |          self.assertIsNone(out["package"])
1398 |          self.assertTrue(out["why_none"].startswith("no hook in the pool (ruling 59 d): none of the 4 moments"))
1399 | -        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["h", "y", "x"])
1400 | +        self.assertIn("passes the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, setup >= 3", out["why_none"])
1401 | +        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["y", "h", "x"])   # rating, then parts
1402 |          self.assertEqual([b["rating"] for b in out["hook_pool"]["best"]], [3, 3, 2])
1403 | -        self.assertIn("A 3 (scroll 3, alone 4, setup 4): why h", out["why_none"])
1404 | +        self.assertIn("A 3 (scroll 3, alone 4, setup 2): why h", out["why_none"])   # setup alone held h back
1405 | +        self.assertEqual(out["hook_pool"]["bar_floors"], {"scroll": 3, "alone": 4, "setup": 3})
1406 |          self.assertEqual(rig.medley_calls, [])
1407 |          self.assertNotIn("angle_write", rig.events)                     # no angle, no line-up paid for
1408 |          self.assertEqual(len(rig.screens), 1)                            # and no second screen
1409 | @@ -1426,7 +1489,7 @@ class TestRuling59HookFirst(unittest.TestCase):
1410 |      def test_the_writer_is_given_the_passing_hooks_and_the_best_hook_goes_first(self):
1411 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1412 |          rig = Rig(ms, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)], [None],
1413 | -                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 4, 5)})
1414 | +                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 3, 5)})
1415 |          out = rig.run()
1416 |          p = next(p for r, p in rig.prompts if r == "angle_write")
1417 |          self.assertIn("THE HOOKS", p)
1418 | @@ -1438,6 +1501,8 @@ class TestRuling59HookFirst(unittest.TestCase):
1419 |          self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
1420 |          self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
1421 |          self.assertIsNotNone(out["package"])
1422 | +        self.assertEqual((out["package"]["hook_bar"]["note"], out["package"]["hook_bar"]["floors"]),   # ruling 115 (2)
1423 | +                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}))
1424 |  
1425 |      def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
1426 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1427 | @@ -1688,6 +1753,19 @@ class TestRulings6264Search(unittest.TestCase):
1428 |          self.assertIn("ruling 62", out["tried"][0]["why"])
1429 |          self.assertIsNotNone(out["package"])
1430 |  
1431 | +    def test_ruling_62_only_with_a_hook_on_its_calibrated_bar(self):
1432 | +        """RULING 115: 'only the last clip fails' needs the line-up's own hook on its calibrated bar (its slot is never
1433 | +        COHERENCE_MIN's: a scroll-3 hook at every floor counts as passing)."""
1434 | +        segs = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
1435 | +                pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 9.0)]
1436 | +        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_03": 2}), measured=True, flagged=[])
1437 | +        self.assertTrue(PK.last_clip_only(segs, med))
1438 | +        for hr in ({"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
1439 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}, None):
1440 | +            bad = [dict(segs[0], hook_rating=hr), *segs[1:]]
1441 | +            self.assertFalse(PK.last_clip_only(bad, med), hr)                 # the hook fails: never "only the last"
1442 | +        self.assertFalse(PK.last_clip_only(segs, dict(med, clips=dict(med["clips"], clip_01=3))))   # two clips fail
1443 | +
1444 |      def test_ruling_62_under_the_floor_swaps_as_now(self):
1445 |          ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 10.0), self.fresh("y", "C", 10.0),
1446 |                self.fresh("z", "D", 9.0)]                                    # without z: 32 s, under 36.7
1447 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
1448 | index 64517b8..28ebadb 100644
1449 | --- a/tests/package/test_spotlight.py
1450 | +++ b/tests/package/test_spotlight.py
1451 | @@ -65,7 +65,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
1452 |      m.update(text=text, channel_name=channel, published_at=(NOW - timedelta(hours=2)).isoformat(),
1453 |               hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
1454 |               hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
1455 | -                          "backend": "fake:xai", "replayed": False},
1456 | +                          "backend": "xai:grok", "replayed": False},   # the conftest's calibrated rater (ruling 115)
1457 |               visual={"version": VP.VERSION, "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
1458 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
1459 |                                        "finding": "none"}, "on_screen_text": [],
1460 | @@ -618,6 +618,24 @@ class TestPackageFor(unittest.TestCase):
1461 |              self.assertEqual(asked[-1], None, name)                         # the package without it is judged
1462 |              self.assertFalse(pk["spotlight"]["closing"]["kept"], name)
1463 |  
1464 | +    def test_ruling_115_the_hook_own_row_is_the_calibrated_bar(self):
1465 | +        """RULING 115: the opener's row passes when each part is at least its calibrated floor (the rigs': scroll 3,
1466 | +        alone 4, setup 3), by the calibrated rater; ruling 90's ">= 4" (the scroll-and-alone rating) no longer decides."""
1467 | +        def row(scroll, alone, setup, backend="xai:grok"):
1468 | +            m = moment(hook_rating={"scroll": scroll, "alone": alone, "setup": setup, "rating": min(scroll, alone),
1469 | +                                    "why": "w", "backend": backend, "replayed": False})
1470 | +            return SPOT.inventory(*package()[0:1], m, FID_OK, [], True, [], CX_OK, two()[0], two(),
1471 | +                                  {"verdict": "keep", "measured": True, "replayed": False},
1472 | +                                  {"ok": True, "edges": {"cuttable": True}}, pre_of(m), m["spotlight_source"],
1473 | +                                  {"now": NOW, "day": "d", "never_delivered": True,
1474 | +                                   "one_per_channel_day": True})["hook_own"]
1475 | +        r = row(3, 4, 3)                                                    # rating 3: ruling 90 failed it
1476 | +        self.assertEqual((r["status"], r["rating"], r["setup"]), ("PASS", 3, 3))
1477 | +        self.assertIn("scroll >= 3, alone >= 4, setup >= 3", r["bar"])
1478 | +        for parts in ((5, 3, 5), (5, 5, 2), (2, 5, 5)):
1479 | +            self.assertEqual(row(*parts)["status"], "FAIL", parts)
1480 | +        self.assertEqual(row(5, 5, 5, "heimdall:qwen/qwen3.8-27b")["status"], "FAIL")   # off the calibrated rater
1481 | +
1482 |      def test_the_precheck_row_needs_one_verdict_on_this_clip(self):
1483 |          m = moment()
1484 |          rows = lambda pre: SPOT.inventory(*package()[0:1], m, FID_OK, [], True, [], CX_OK, two()[0], two(),
1485 | @@ -681,7 +699,7 @@ class TestBuild(unittest.TestCase):
1486 |  
1487 |          def hook_ratings(router, ms_, *a, **k):
1488 |              return {m["moment_id"]: {"scroll": ratings[m["moment_id"]], "alone": 5, "setup": 3,
1489 | -                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "fake:xai"}
1490 | +                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "xai:grok"}
1491 |                      for m in ms_}, None
1492 |  
1493 |          def second(router, cleared, a_by, *a, **k):
1494 | @@ -723,11 +741,19 @@ class TestBuild(unittest.TestCase):
1495 |      def test_the_best_qualifying_moment_goes_to_the_package(self):
1496 |          ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
1497 |                moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
1498 | -        out, calls = self.run_build(ms, {"a": 3, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1499 | +        out, calls = self.run_build(ms, {"a": 2, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1500 |          self.assertEqual(calls["package_for"], ["b"])                      # c opens best but stands alone at 3
1501 | -        self.assertIn("hook's own job rates 3", out["moments"]["a"]["out"])
1502 | +        self.assertIn("the hook's own job: scroll 2 < 3 (the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, "
1503 | +                      "setup >= 3", out["moments"]["a"]["out"])               # ruling 115: under ONE part's floor
1504 |          self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
1505 |          self.assertIsNotNone(out["package"])
1506 | +        self.assertEqual(out["package"]["hook_bar"]["note"], "hook passed on the calibrated bar")   # ruling 115 (2)
1507 | +
1508 | +    def test_ruling_115_an_opener_at_every_floor_goes_to_the_package(self):
1509 | +        """Scroll 3, alone 5, setup 3: under ruling 90 (rating >= 4) it stopped; on the calibrated bar it passes."""
1510 | +        out, calls = self.run_build([moment(mid="a", channel="A")], {"a": 3})
1511 | +        self.assertEqual(calls["package_for"], ["a"])
1512 | +        self.assertIsNotNone(out["package"])
1513 |  
1514 |      def test_ruling_92_amended_zero_changes_near_the_clip_stops_before_any_vision_call(self):
1515 |          """09:03 Nov 14: the markers refuse alone only when the episode is marked and shows ZERO speaker changes in the
1516 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1517 | index 7d9e0a6..d27acc2 100644
1518 | --- a/tests/providers/test_providers.py
1519 | +++ b/tests/providers/test_providers.py
1520 | @@ -672,5 +672,30 @@ class TestRuling86Shadow(TestRuling85Routing):
1521 |              with self.assertRaises(ValueError):
1522 |                  P.Router(self.cfg(d), env_path="/nonexistent", shadow={"*": "xai:nope"})
1523 |  
1524 | +    def test_ruling_115_a_verdict_types_own_shadow_asked_on_a_chain_of_its_own(self):
1525 | +        """RULING 115: the hook job (Grok decides) is shadowed by qwen, keyed "<role>:<kind>", on a chain of its own;
1526 | +        every other verdict of the role keeps the role's ("*") shadow; each record names its kind."""
1527 | +        import tempfile
1528 | +        with tempfile.TemporaryDirectory() as d:
1529 | +            r = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first",
1530 | +                         shadow={"*": "xai:grok", "coherence_verdict:hook": "heimdall:qwen"},
1531 | +                         shadow_log=os.path.join(d, "SHADOW.jsonl"), chains={"coherence_verdict:hook": ["xai:grok"]})
1532 | +            fs = self.fakes()
1533 | +            for b in fs:
1534 | +                if b.vendor == "heimdall":
1535 | +                    b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1536 | +            r.backends = {b.name: b for b in fs}
1537 | +            self.assertEqual(r.call("coherence_verdict", "the hook", 500, 7, kind="hook").backend, "xai:grok")
1538 | +            self.assertEqual(r.call("coherence_verdict", "a line-up", 500, 7, kind="coherence").backend,
1539 | +                             "heimdall:deepseek")
1540 | +            self.assertEqual(r.shadow_wait(5), 0)
1541 | +            got = sorted((x["kind"], x["prompt"], x["deciding"]["backend"], x["shadow"]["backend"])
1542 | +                         for x in self.lines(d))
1543 | +            self.assertEqual(got, [("coherence", "a line-up", "heimdall:deepseek", "xai:grok"),
1544 | +                                   ("hook", "the hook", "xai:grok", "heimdall:qwen")])
1545 | +            self.assertEqual((r.chain("shadow86:coherence_verdict:hook"), r.chain("shadow86:coherence_verdict")),
1546 | +                             (["heimdall:qwen"], ["xai:grok"]))
1547 | +            self.assertEqual((r.backends["heimdall:qwen"].calls, r.backends["xai:grok"].calls), (1, 2))
1548 | +
1549 |  if __name__ == "__main__":
1550 |      unittest.main()
1551 | 
```

---

pp-selectid: RULING 115 (orchestrator 13:24 ET Nov 15) (1) + (2), THE CALIBRATED HOOK BAR. Production code: a new
pipeline/hook_bar.py and pipeline/hook_calibration.json; pipeline/package.py, spotlight.py, package_pin.py,
providers.py and model_providers.json; the build driver tests/package/proof_ledger.py; ruling 112's driver
tests/package/hook112.py. Tests: a new tests/package/conftest.py and test_hook_bar.py, and updated test_medley,
test_spotlight, test_ledger_build, test_hook112 and tests/providers/test_providers.py.

THE ORDER, verbatim in its parts:
(1) "INTERIM BAR, LIVE AS SOON AS AUDITED, BOTH PATHS (medley hook and spotlight opener): the hook job is asked ALONE
    at production's seed by GROK (qwen in shadow). A hook passes when EACH of its three parts (scroll, alone, setup)
    is at least the LOWEST value that part takes across the five approved hooks under that same asking (ALONE_TEST.json
    is the source; write the three floors into one calibration file with its sha, and name them in every build line).
    Nothing else about the hook path changes (may-open rules, G17a, step A, CUTTABLE stay). If any floor comes out
    below 3, stop at 3 for that part and tell me."
(2) "MARK IT: a package sealed on the interim bar says so in its record and in the Telegram note in one plain line
    ("hook passed on the calibrated bar"); PBX's approve or reject of it is appended to the calibration file as a new
    example (approved = positive, rejected = negative with his reason)."
Ruling 113 (2), which (1) builds on: the calibration "runs before a rater takes the job, again on any change of
model, question version or seed, and once a day; a rater that fails it does not rate, and the build says so in one
line".

WHAT THE CHANGE DOES:
- hook_bar.py: floors_from (each part's minimum over the approved hooks; a floor under 3 is stopped at 3 and listed);
  write / load (the file sealed by the sha256 of its canonical body; a hand edit fails the seal); bar (valid only for
  its question version, seed, asking "alone", rater when named, and under 24 h old; else None and why: NO hook
  passes); passes (each part >= its floor AND the rating's back-end is the calibrated rater); text (the bar in one
  line); add_example ((2): approved, or rejected with a reason; the floors are not re-derived there).
- hook_calibration.json: Grok (xai:grok-4.20-0309-reasoning), asked alone at seed 7, question version bfdf74078d5e
  (= package.HOOK_VERSION), measured 18:07:52 UTC. The five approved hooks' parts from ALONE_TEST.json (the two
  whose first answer was out of contract: the retry asked once more, alone, seed 7). Floors scroll 3, alone 4,
  setup 3; none under 3.
- package.hook_ratings: ONE call per candidate (was one batched call), max_tokens 750, seed HOOK_SEED 7. This is the
  calibration's own asking: hook112.calibrate called hook_ratings with ONE reference per call, so the prompt (HOOKS_PROMPT
  with one CANDIDATE and its one key), max_tokens (600 + 150 x 1) and seed are the same bytes. HOOK_VERSION now
  hashes HOOKS_PROMPT + HOOK_ASKING, so no batched rating cached before answers. A candidate whose chain is spent has
  no rating; the others are still asked; the first error is returned.
- package.hook_own: adds "setup", "passes" (hook_bar.passes on the live bar), "short", "bar". The rating
  (min(scroll, alone)) still ORDERS hooks (hook_order); "passes" decides: _can_open, medley(), coherence(),
  last_clip_only (ruling 62) and the spotlight's opener stage and its "hook_own" gate row.
- In medley() and coherence() the hook's own rating used to sit INSIDE the min >= COHERENCE_MIN (4) over the clips.
  With a scroll floor of 3, a hook that passes the bar would then fail every line-up, so the hook's slot is judged by
  the calibrated bar and the min runs over the clips AFTER the hook (and the VO point) as before. This is the one
  reading of "nothing else changes" we took; please say if you read it otherwise.
- The hook list "coherence_verdict:hook" is Grok ALONE in every routing (heimdall_first, today, plan_b): the floors
  are Grok's, so a failover model's rating could never pass (and, cached, would answer for that moment). Grok down =
  no rating = no hook (law L-m), asked again next build. qwen answers every hook in SHADOW (proof_ledger.build_shadow;
  providers._shadow_of / _shadow_ask look up "<role>:<kind>" first and ask it on a chain of its own).
- (2) the mark: package.hook_bar_mark() -> {"note": "hook passed on the calibrated bar", "bar", "floors",
  "calibration_sha256", "ruling": "115"}, set on a built medley package and a built spotlight package, and carried
  into the pin's moments_package OUTSIDE the seal (package_pin.to_pin), for the integrator's Telegram note.

UNCHANGED GUARDS THE CHANGE LEANS ON (outside the hunks; line numbers in the changed tree):
- package._can_open (package.py:1460-1481): hook eligibility, G17a (hook_onset "pass"), stand_alone.opener; only
  then the rating. "hook_rating" absent = not rated yet (before the build rates).
- package.build (package.py:2691-2699): every cleared moment's carried rating is popped, the openers are rated, and
  EVERY cleared moment then gets "hook_rating": the rating, or {"rating": None, "why": "not rated: ..."}; hook_own of
  that is None, so an unrated hook never opens. spotlight.build does the same (spotlight.py:905-917).
- _load_cache(None) is {} (package.py:499-507: open(None) raises TypeError, caught); _cache_put(None, ...) returns
  at once (package.py:510-513).
- providers.call_parsed (providers.py:690-716): an answer out of contract moves on to the next model; with a
  one-model list the chain is then spent: ProviderError, caught per candidate in hook_ratings.
- providers.Router.chain (providers.py:794-811): this router's overrides, then the routing's per-type list, then the
  role's chain. proof_ledger builds with --routing heimdall_first (proof_ly.chains, tests/package/proof_ly.py:76).
- Router._shadow_ask runs in a thread and never raises into the build; the shadow never decides (providers.py:1221+).
- package_pin.seal (package_pin.py:200) takes segments, edl_vo, signoff, title, caption, gates, btc_screen, shape,
  first_comment, ...: not "hook_bar", so the mark is outside the seal (to_pin :469).

TESTS: 687 pass in tests/package + tests/providers; all 37 suite files of the handoff pass, one process each. 31 of 31
mutations killed after a control run (the unmutated copy passes): the rater check, a part AT its floor, min vs max,
the stop at 3, staleness, the question version, the seal, a rejection's reason, a floor under 3 in the file; the old
bar in _can_open, the hook back in either min, either verdict ignoring the bar, ruling 62, one error stopping the
others, the mark (medley, spotlight, pin), the invalid calibration's why, the version without the asking, a batch,
setup left out; the spotlight's opener and gate row on the old bar; the three hook lists; the kind's shadow (lookup
and chain); hook112's driver reading production's Grok-only list; no qwen shadow in a build.

PLEASE CHECK: (1) that a hook passes ONLY with every part at least its floor, rated by the calibrated rater, under
a valid (sealed, matching, fresh) calibration, on both paths; (2) that the floors in hook_calibration.json are the
source's minimums and that production's asking is byte-for-byte the calibration's; (3) the reading of "nothing else
changes" above (the hook's slot in the two verdicts and in ruling 62); (4) that no other model can rate a hook, and
that qwen's shadow can never decide; (5) the mark: on a sealed package and its pin only, outside the seal; (6) the
tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
