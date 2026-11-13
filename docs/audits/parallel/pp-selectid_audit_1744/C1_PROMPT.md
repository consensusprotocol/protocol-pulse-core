# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1744
# Branch: pp-selectid
# Generated: 2026-11-13 17:44 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1744/C1_STEP.diff (770 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | new file mode 100644
   3 | index 0000000..a0c6b42
   4 | --- /dev/null
   5 | +++ b/pipeline/lock_precheck.py
   6 | @@ -0,0 +1,232 @@
   7 | +"""RULING 68 (orchestrator 14:02 Nov 13) and RULING 72 (live 17:17 Nov 13 on the integrator's side): the render's own
   8 | +ruling-17 lock, asked BEFORE any write is paid for a line-up and before its pin is sealed. Ruling 68: "When it exists,
   9 | +your approved text comes from it."
  10 | +
  11 | +The integrator's service runs the render's acquisition, decode and lock (pinned.acquire, validate_range,
  12 | +pinned.segment_lock) on the segments of a request. Under ruling 72 it compares the second recogniser with the lock on
  13 | +every span.
  14 | +
  15 | +Requests: this worktree's tests/package/proof/lock_requests/ (<name>.tmp, then rename). The service only reads there,
  16 | +and answers each name and content once.
  17 | +
  18 | +Results: read only, in /home/ultron/protocol_pulse/data/lock_precheck/results/
  19 | +<video_id>.<start %.3f>-<end %.3f>.<decoder[:12]>.json. Each file is a list. The answer is the newest entry (by "at")
  20 | +that meets all of these:
  21 | +- rules == "ruling 17 + ruling 72";
  22 | +- its window is the segment's [start, end];
  23 | +- its role, approved_text, trimmed_leading and untrimmed_start equal the request's.
  24 | +Entries without "rules" are ruling 68's, from before, and are never read.
  25 | +
  26 | +Outcomes:
  27 | +- no_difference, adopted, two_readings: pass. The approved text stands.
  28 | +- adopt_spoken: the text to seal is "spoken_text", already through the render's validate_range + segment_lock. It is
  29 | +  adopted only when this side's own check agrees that every difference is in ruling 67's carry-over class
  30 | +  (attest.carry_class: a function word, or the speaker's own immediate repetition; never a number, a name or a
  31 | +  negation). Otherwise it is a hold (fail closed).
  32 | +- hold: the clip may not be used with that text. The reason says why.
  33 | +- error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
  34 | +  is sent again rather than reusing an error.
  35 | +
  36 | +The text a pin seals is the approved text, or the adopted spoken text with an "attested" record
  37 | +(package_pin.SEALED_LATER), as ruling 67's re-seal records it."""
  38 | +import json
  39 | +import os
  40 | +import re
  41 | +import time
  42 | +from datetime import datetime, timezone
  43 | +
  44 | +import attest as AT
  45 | +
  46 | +RULES = "ruling 17 + ruling 72"
  47 | +DECODER = "25cd6f15e6c9"                      # the integrator's decoder_sha[:12] (unchanged by ruling 72)
  48 | +RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  49 | +REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  50 | +                        "lock_requests")      # this worktree's; the service only reads it
  51 | +PASS = frozenset(("no_difference", "adopted", "two_readings"))
  52 | +TRIM = ("trimmed_leading", "untrimmed_start")
  53 | +ID_RE = re.compile(r"[A-Za-z0-9_.:~-]{1,120}")
  54 | +TIMEOUT_S = 1200.0                            # a fresh line-up takes about 2-2.5 min; the service yields to renders
  55 | +POLL_S = 10.0
  56 | +OLDEST = datetime.min.replace(tzinfo=timezone.utc)
  57 | +
  58 | +
  59 | +def segments_of(segs):
  60 | +    """The request's segments, exactly as package_pin.to_pin will carry them from this line-up: role (the hook first),
  61 | +    start and end rounded to the millisecond, the moment's text as approved_text, and both trim fields when the
  62 | +    moment is trimmed (package._package copies them then)."""
  63 | +    out = []
  64 | +    for i, m in enumerate(segs):
  65 | +        s = {"video_id": str(m["video_id"]), "start": round(float(m["start"]), 3), "end": round(float(m["end"]), 3),
  66 | +             "role": "hook" if i == 0 else "clip", "approved_text": m["text"]}
  67 | +        if m.get("trimmed_leading"):
  68 | +            s.update({k: m[k] for k in TRIM})
  69 | +        out.append(s)
  70 | +    return out
  71 | +
  72 | +
  73 | +def result_file(seg, results_dir=RESULTS, decoder=DECODER):
  74 | +    return os.path.join(results_dir, f"{seg['video_id']}.{seg['start']:.3f}-{seg['end']:.3f}.{decoder[:12]}.json")
  75 | +
  76 | +
  77 | +def _at(s):
  78 | +    try:
  79 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  80 | +    except (TypeError, ValueError):
  81 | +        return OLDEST
  82 | +    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
  83 | +
  84 | +
  85 | +def _matches(e, seg):
  86 | +    w = e.get("window")
  87 | +    try:
  88 | +        win = [round(float(w[0]), 3), round(float(w[1]), 3)] if isinstance(w, list) and len(w) == 2 else None
  89 | +    except (TypeError, ValueError):
  90 | +        win = None
  91 | +    return (e.get("rules") == RULES and win == [seg["start"], seg["end"]] and e.get("role") == seg["role"] and
  92 | +            e.get("approved_text") == seg["approved_text"] and all(e.get(k) == seg.get(k) for k in TRIM))
  93 | +
  94 | +
  95 | +def answer(seg, results_dir=RESULTS, request_id=None):
  96 | +    """The newest matching entry (by "at", then file order), only `request_id`'s when given; None when there is none
  97 | +    or the file cannot be read (no answer is never a pass)."""
  98 | +    try:
  99 | +        with open(result_file(seg, results_dir)) as f:
 100 | +            entries = json.load(f)
 101 | +    except (OSError, ValueError):
 102 | +        return None
 103 | +    best = None
 104 | +    for k, e in enumerate(entries if isinstance(entries, list) else []):
 105 | +        if isinstance(e, dict) and _matches(e, seg) and (request_id is None or e.get("request_id") == request_id):
 106 | +            key = (_at(e.get("at")), k)
 107 | +            if best is None or key >= best[0]:
 108 | +                best = (key, e)
 109 | +    return best[1] if best else None
 110 | +
 111 | +
 112 | +def send(segments, request_id, requests_dir=REQUESTS):
 113 | +    """Write the WHOLE line-up as one request: <request_id>.tmp, then renamed to <request_id>.json. Never over an
 114 | +    existing request (the service answers each name and content once)."""
 115 | +    if not isinstance(request_id, str) or not ID_RE.fullmatch(request_id):
 116 | +        raise ValueError(f"a request_id is 1-120 of [A-Za-z0-9_.:~-]: {request_id!r}")
 117 | +    os.makedirs(requests_dir, exist_ok=True)
 118 | +    final = os.path.join(requests_dir, request_id + ".json")
 119 | +    tmp = os.path.join(requests_dir, request_id + ".tmp")
 120 | +    if os.path.exists(final) or os.path.exists(tmp):
 121 | +        raise FileExistsError(f"{final} (or its .tmp) exists: a request is never written over")
 122 | +    with open(tmp, "x") as f:
 123 | +        json.dump({"request_id": request_id, "segments": segments}, f, indent=1)
 124 | +    os.rename(tmp, final)
 125 | +    return final
 126 | +
 127 | +
 128 | +def decide(seg, e):
 129 | +    """One segment's verdict from its answer -> {"verdict": "pass" | "adopt" | "hold" | "error", "outcome", "why",
 130 | +    and for an adoption "spoken_text" and "differences"}."""
 131 | +    if e is None:
 132 | +        return {"verdict": "error", "outcome": None, "why": "no answer from the render's lock in time (law L-m)"}
 133 | +    out, why = e.get("outcome"), str(e.get("reason") or "")[:400]
 134 | +    if out in PASS:
 135 | +        return {"verdict": "pass", "outcome": out, "why": why}
 136 | +    if out == "hold":
 137 | +        return {"verdict": "hold", "outcome": out, "why": why or "held (no reason given)"}
 138 | +    if out != "adopt_spoken":
 139 | +        return {"verdict": "error", "outcome": out, "why": f"no verdict: outcome {out!r} {why}".strip()}
 140 | +    spoken, approved = e.get("spoken_text"), seg["approved_text"]
 141 | +    if not isinstance(spoken, str) or not spoken.strip():
 142 | +        return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 143 | +    r, p, ops = AT.diff(spoken, approved)
 144 | +    if not ops:                                       # the same canonical words: the approved text stands
 145 | +        return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 146 | +    classes = [AT.carry_class(r, p, o, (spoken, approved)) for o in ops]
 147 | +    diffs = [{"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 148 | +             for (_, a, b, c, d), k in zip(ops, classes)]
 149 | +    if None in classes:                               # this side's ruling-67 check disagrees: fail closed
 150 | +        return {"verdict": "hold", "outcome": out, "differences": diffs,
 151 | +                "why": "adopt_spoken, but by this side's attest.carry_class a difference is outside ruling 67's "
 152 | +                       "class: " + str([[x["spoken"], x["approved"]] for x in diffs if x["class"] is None])[:300]}
 153 | +    return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs}
 154 | +
 155 | +
 156 | +def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_s=TIMEOUT_S, poll_s=POLL_S,
 157 | +          clock=time.time, sleep=time.sleep, log=print):
 158 | +    """The render's lock for this line-up. An answer already on file is used (never an error), else the whole line-up
 159 | +    is sent and its answers awaited. -> {"ok": every segment passes or is adopted, "request_id": the one sent or None,
 160 | +    "segments": [request segment + decide() + the answer's "entry" ref], "error": why no verdict, or None}."""
 161 | +    req = segments_of(segs)
 162 | +    got = [answer(s, results_dir) for s in req]
 163 | +    sent = None
 164 | +    if any(e is None or e.get("outcome") not in PASS | {"adopt_spoken", "hold"} for e in got):
 165 | +        sent = request_id
 166 | +        send(req, request_id, requests_dir)
 167 | +        log(f"    ruling 72: the lock pre-check asked ({request_id}, {len(req)} segment(s))")
 168 | +        deadline = clock() + timeout_s
 169 | +        while True:
 170 | +            got = [answer(s, results_dir, request_id) for s in req]
 171 | +            if all(e is not None for e in got) or clock() >= deadline:
 172 | +                break
 173 | +            sleep(poll_s)
 174 | +    rows = []
 175 | +    for s, e in zip(req, got):
 176 | +        d = decide(s, e)
 177 | +        rows.append(dict(s, **d, entry=None if e is None else {
 178 | +            "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
 179 | +            "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
 180 | +            "file": os.path.basename(result_file(s, results_dir))}))
 181 | +    errs = [f"{x['video_id']} {x['start']}-{x['end']}: {x['why']}" for x in rows if x["verdict"] == "error"]
 182 | +    return {"ok": all(x["verdict"] in ("pass", "adopt") for x in rows), "request_id": sent, "segments": rows,
 183 | +            "error": "; ".join(errs)[:600] or None}
 184 | +
 185 | +
 186 | +def attested(row, run_rule="ruling 72 (live 17:17 Nov 13): adopt_spoken, in ruling 67's carry-over class"):
 187 | +    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 188 | +    return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 189 | +            "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 190 | +                       "ruling 67's carry-over class (checked on this side too), and no line quotes the changed words",
 191 | +            "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 192 | +
 193 | +
 194 | +def quoting_lines(lines, row):
 195 | +    """The lines that quote an adopted segment's changed words (ruling 67: such a line is re-gated first)."""
 196 | +    r, p, ops = AT.diff(row["spoken_text"], row["approved_text"])
 197 | +    return AT.quotes(lines, r, p, ops)
 198 | +
 199 | +
 200 | +def apply(pk, pre):
 201 | +    """The package as it will be sealed, from this line-up's pre-check: each adopted segment's text is the spoken text
 202 | +    with its "attested" record, and the hook's first words follow its text. Refuses (ValueError) unless the pre-check
 203 | +    passed and covers exactly the package's segments (video, start, end, approved text, in order), and when a line
 204 | +    quotes an adopted segment's changed words (ruling 67: re-gated first). -> pk (its segments are its own)."""
 205 | +    rows, segs = pre.get("segments") or [], pk["segments"]
 206 | +    if pre.get("ok") is not True:
 207 | +        raise ValueError(f"the render's lock pre-check did not pass: {pre.get('error') or 'a segment holds'}")
 208 | +    if len(rows) != len(segs) or any(
 209 | +            r["video_id"] != s["video_id"] or r["start"] != round(float(s["start"]), 3) or
 210 | +            r["end"] != round(float(s["end"]), 3) or r["approved_text"] != s["text"] for r, s in zip(rows, segs)):
 211 | +        raise ValueError("the lock pre-check does not cover exactly this package's segments")
 212 | +    lines = [x["text"] for x in pk.get("lines") or []]
 213 | +    for r, s in zip(rows, segs):
 214 | +        if r["verdict"] == "adopt":
 215 | +            q = quoting_lines(lines, r)
 216 | +            if q:
 217 | +                raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
 218 | +            s["text"], s["attested"] = r["spoken_text"], attested(r)
 219 | +    pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
 220 | +    pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
 221 | +                      "segments": [{k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
 222 | +                                                          "entry")} for r in rows]}
 223 | +    return pk
 224 | +
 225 | +
 226 | +def pin_problems(pk):
 227 | +    """The pin stage's own check (ruling 68): a package is sealed only with a passing pre-check that covers exactly its
 228 | +    segments as they now stand (an adopted text included). -> [why]."""
 229 | +    pre = pk.get("precheck") or {}
 230 | +    rows, segs = pre.get("segments") or [], pk.get("segments") or []
 231 | +    if pre.get("ok") is not True:
 232 | +        return ["ruling 68: no passing lock pre-check on this package"]
 233 | +    if len(rows) != len(segs) or any(r.get("video_id") != s.get("video_id") or
 234 | +                                     r.get("start") != round(float(s.get("start")), 3) or
 235 | +                                     r.get("end") != round(float(s.get("end")), 3) or
 236 | +                                     r.get("verdict") not in ("pass", "adopt") for r, s in zip(rows, segs)):
 237 | +        return ["ruling 68: the lock pre-check does not cover this package's segments"]
 238 | +    return []
 239 | diff --git a/pipeline/package.py b/pipeline/package.py
 240 | index a0c1526..9aa656b 100644
 241 | --- a/pipeline/package.py
 242 | +++ b/pipeline/package.py
 243 | @@ -2119,7 +2119,7 @@ def candidate_lineup(router, candidate, cleared, now):
 244 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 245 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 246 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 247 | -          visual_cache=None, registered=None):
 248 | +          visual_cache=None, registered=None, lock_check=None):
 249 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 250 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 251 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 252 | @@ -2151,11 +2151,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 253 |      line-up the search forms that is registered is recorded ("registered") and neither judged nor written, and the angle
 254 |      ends there, as it ends after a passing line-up whose line fails; ruling 3's no-voice fallback never adds the clip
 255 |      that would form one (audit 1655). A build from a candidate ignores it.
 256 | +    RULING 68 / 72 (lock_check, lock_precheck.check through the driver): "your approved text comes from" the render's own
 257 | +    ruling-17 lock. A line-up whose clips pass is asked BEFORE any write is paid:
 258 | +      - a clip the render would hold is out (doomed), and the line-up is re-lined;
 259 | +      - no verdict (an error, or no answer in time) is never a pass: nothing is written, the search stops, and the
 260 | +        line-up stays a candidate (its class is "budget");
 261 | +      - a package keeps the approved texts, or seals an adopted spoken text with its "attested" record
 262 | +        (lock_precheck.apply, checked again at the pin stage).
 263 | +    The no-voice line-up is asked too. lock_check None: no pre-check (the tests' rigs); the driver always passes it.
 264 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 265 |      t0 = time.time()
 266 |      usd0 = _spent(spend)
 267 |      held_map = dict(registered or {}) if candidate is None else {}   # ruling 66: the registry's line-ups, by moment ids
 268 |      import visual_pin as VP                            # ruling 70
 269 | +    import lock_precheck as LP                         # rulings 68 / 72
 270 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
 271 |      out_visual = {"calls": 0, "cached": 0, "usd_reported": 0.0, "usd_estimate": 0.0, "estimated_calls": 0,
 272 |                    "unmeasured": 0, "flags": 0}   # ruling 70: the vendor's figure and the estimate never mixed
 273 | @@ -2488,6 +2497,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 274 |          if vbad:
 275 |              note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
 276 |              return None
 277 | +        nv_pre = lock_check(order) if lock_check is not None else None     # RULINGS 68 / 72: its own line-up
 278 | +        if nv_pre is not None and not nv_pre.get("ok"):
 279 | +            note["why_not"] = f"ruling 68 / 72: the render's lock: {nv_pre.get('error') or 'a clip holds'}"[:400]
 280 | +            return None
 281 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 282 |          pk["medley"] = nv_med
 283 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 284 | @@ -2527,6 +2540,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 285 |          pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 286 |          pk["seconds"] = round(time.time() - t0, 1)
 287 |          pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 288 | +        if nv_pre is not None:                            # rulings 68 / 72: the texts it seals
 289 | +            try:
 290 | +                pk = LP.apply(pk, nv_pre)
 291 | +            except (ValueError, KeyError, TypeError) as e:
 292 | +                note["why_not"] = f"ruling 68 / 72: {e}"[:400]
 293 | +                return None
 294 |          note["result"] = "PACKAGE"
 295 |          log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
 296 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 297 | @@ -2540,7 +2559,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 298 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 299 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 300 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 301 | -            while total < lineups and not out["packages"] and not out.get("budget_stop"):
 302 | +            while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 303 | +                    not out.get("lock_stop"):
 304 |                  if candidate is not None and n_lineup >= candidate["n_lineup"]:
 305 |                      break                                 # RULING 66: the candidate alone, never re-lined or swapped
 306 |                  if over_budget(ai):
 307 | @@ -2662,6 +2682,26 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 308 |                      doomed |= set(vbad)
 309 |                      rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 310 |                      relined, w_used = True, writes      # no write is paid
 311 | +                pre = None
 312 | +                if not relined and lock_check is not None:  # RULINGS 68 / 72: the render's own lock, before any write
 313 | +                    pre = lock_check(segs)
 314 | +                    rec["precheck"] = {"request_id": pre.get("request_id"), "ok": pre.get("ok"),
 315 | +                                       "segments": [{k: x.get(k) for k in ("video_id", "start", "end", "verdict",
 316 | +                                                                          "outcome", "why")} for x in pre["segments"]]}
 317 | +                    log(f"    ruling 72: the render's lock: " + ", ".join(
 318 | +                        f"{x['video_id']} {x['verdict']}" for x in pre["segments"]) + f" ({time.time() - t0:.0f} s)")
 319 | +                    held = {segs[i]["moment_id"]: x["why"] for i, x in enumerate(pre["segments"])
 320 | +                            if x["verdict"] == "hold"}
 321 | +                    if pre.get("error") or not pre["segments"]:      # no verdict is never a pass (law L-m): nothing
 322 | +                        rec["why"] = f"ruling 68 / 72: no lock verdict: {pre.get('error')}"[:500]   # is written, the
 323 | +                        rec["budget"], out["lock_stop"] = True, rec["why"]   # search stops, the line-up stays a
 324 | +                        w_used = writes                                     # candidate (class "budget")
 325 | +                    elif held:                             # the render would hold these clips: out, re-lined
 326 | +                        dropped |= set(held)
 327 | +                        doomed |= set(held)
 328 | +                        rec["why"] = ("ruling 72: the render's lock holds " +
 329 | +                                      "; ".join(f"{k}: {v}" for k, v in held.items()))[:500] + ": re-lined"
 330 | +                        relined, w_used = True, writes
 331 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 332 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 333 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 334 | @@ -2889,12 +2929,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 335 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 336 |                      pk["seconds"] = round(time.time() - t0, 1)
 337 |                      pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 338 | +                    if lock_check is not None:            # rulings 68 / 72: the texts it seals come from the lock
 339 | +                        try:
 340 | +                            pk = LP.apply(pk, pre)
 341 | +                        except (ValueError, KeyError, TypeError) as e:
 342 | +                            rec["why"] = f"ruling 68 / 72: {e}"[:400]
 343 | +                            w_used = writes
 344 | +                            break
 345 |                      out["packages"].append(pk)
 346 |                      rec["result"] = "PACKAGE"
 347 |                      break
 348 |                  rec["relined"] = relined                    # ruling 66: a clip was dropped (or a line-up rule)
 349 |                  if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 350 | -                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
 351 | +                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop") \
 352 | +                        and not out.get("lock_stop"):
 353 |                      nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 354 |                      if nv is not None:
 355 |                          out["packages"].append(nv)
 356 | @@ -2907,7 +2955,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 357 |                                    (f" ({', '.join(rules)})" if rules else ""))
 358 |                  if out["packages"] or not relined:
 359 |                      break
 360 | -            if out["packages"] or out.get("budget_stop") or over_budget(ai):
 361 | +            if out["packages"] or out.get("budget_stop") or out.get("lock_stop") or over_budget(ai):
 362 |                  break
 363 |      out["package"] = out["packages"][0] if out["packages"] else None
 364 |      if candidate is not None:                             # RULING 66: what became of the candidate
 365 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 366 | index 19330af..a846a1c 100644
 367 | --- a/pipeline/package_pin.py
 368 | +++ b/pipeline/package_pin.py
 369 | @@ -281,7 +281,8 @@ def to_pin(pk, run_name):
 370 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 371 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 372 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 373 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual")
 374 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 375 | +                                          "attested")      # rulings 68 / 72: an adopted spoken text, sealed
 376 |                          if k in s},
 377 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 378 |      edl_vo = {"intro": pk["vo"]["intro"],
 379 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 380 | index 02585be..38e802b 100644
 381 | --- a/tests/package/proof_ledger.py
 382 | +++ b/tests/package/proof_ledger.py
 383 | @@ -58,6 +58,7 @@ import proof_ly as PL  # noqa: E402
 384 |  import proof_saved_runs as PS  # noqa: E402
 385 |  import providers as P  # noqa: E402
 386 |  import speakers as SP  # noqa: E402
 387 | +import lock_precheck as LP  # noqa: E402
 388 |  
 389 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 390 |  
 391 | @@ -175,7 +176,9 @@ def main(argv=None):
 392 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 393 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 394 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 395 | -              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"))       # ruling 70
 396 | +              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 397 | +              lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 398 | +                  segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 399 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 400 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 401 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 402 | @@ -220,6 +223,9 @@ def main(argv=None):
 403 |      if res["package"]:
 404 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 405 |          try:
 406 | +            lock = LP.pin_problems(res["package"])       # ruling 68: sealed only with a passing lock pre-check
 407 | +            if lock:
 408 | +                raise package_pin.PinRefused("; ".join(lock))
 409 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 410 |                                                name="MOMENTS_PIN_LEDGER.json")
 411 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 412 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 413 | new file mode 100644
 414 | index 0000000..b7c4f3b
 415 | --- /dev/null
 416 | +++ b/tests/package/test_lock_precheck.py
 417 | @@ -0,0 +1,224 @@
 418 | +#!/usr/bin/env python3
 419 | +"""RULINGS 68 / 72 (orchestrator 14:02 Nov 13; live on the integrator's side 17:17 Nov 13): the render's own ruling-17
 420 | +lock, asked before a line-up is written and before its pin is sealed (pipeline/lock_precheck.py). Offline: the
 421 | +requests and results directories are temporary, the clock and the sleep are the test's."""
 422 | +import json
 423 | +import os
 424 | +import sys
 425 | +import tempfile
 426 | +import unittest
 427 | +
 428 | +HERE = os.path.dirname(os.path.abspath(__file__))
 429 | +REPO = os.path.dirname(os.path.dirname(HERE))
 430 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 431 | +import lock_precheck as LP  # noqa: E402
 432 | +
 433 | +HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 434 | +        "text": "Bitcoin launched in January of 2009. It's never been renamed."}
 435 | +CLIP = {"moment_id": "x", "video_id": "MqVqfEDXgLo", "start": 937.971, "end": 957.291,
 436 | +        "text": "I think Bitcoin only dropped like 5, 6%."}
 437 | +TRIM = dict(CLIP, moment_id="t", video_id="HWuMai_mAug", start=1691.139, end=1698.069, trimmed_leading="And",
 438 | +            untrimmed_start=1690.9, text="treasury companies will also bleed to Bitcoin.")
 439 | +
 440 | +
 441 | +def entry(seg, outcome="no_difference", at="2026-11-13T22:30:00Z", rid="r1", **kw):
 442 | +    e = {"rules": LP.RULES, "request_id": rid, "video_id": seg["video_id"], "start": seg["start"], "end": seg["end"],
 443 | +         "window": [seg["start"], seg["end"]], "role": seg["role"], "approved_text": seg["approved_text"],
 444 | +         "trimmed_leading": seg.get("trimmed_leading"), "untrimmed_start": seg.get("untrimmed_start"),
 445 | +         "outcome": outcome, "reason": None, "lock": {"sha256": "ab" * 32}, "at": at}
 446 | +    e.update(kw)
 447 | +    return e
 448 | +
 449 | +
 450 | +class Dirs(unittest.TestCase):
 451 | +    def setUp(self):
 452 | +        self.tmp = tempfile.TemporaryDirectory()
 453 | +        self.req, self.res = os.path.join(self.tmp.name, "req"), os.path.join(self.tmp.name, "res")
 454 | +        os.makedirs(self.res)
 455 | +
 456 | +    def tearDown(self):
 457 | +        self.tmp.cleanup()
 458 | +
 459 | +    def put(self, seg, *entries):
 460 | +        p = LP.result_file(seg, self.res)
 461 | +        old = []
 462 | +        if os.path.exists(p):
 463 | +            with open(p) as f:
 464 | +                old = json.load(f)
 465 | +        with open(p, "w") as f:
 466 | +            json.dump(old + list(entries), f)
 467 | +
 468 | +
 469 | +class TestRequest(Dirs):
 470 | +    def test_the_segments_are_the_pins_own(self):
 471 | +        s = LP.segments_of([HOOK, CLIP, TRIM])
 472 | +        self.assertEqual([x["role"] for x in s], ["hook", "clip", "clip"])
 473 | +        self.assertEqual((s[0]["start"], s[0]["end"]), (216.054, 228.674))              # to the millisecond
 474 | +        self.assertEqual(s[0]["approved_text"], HOOK["text"])
 475 | +        self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 476 | +        self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 477 | +        self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 478 | +                         "DcUbBkyeh9M.216.054-228.674.25cd6f15e6c9.json")
 479 | +
 480 | +    def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 481 | +        segs = LP.segments_of([HOOK, CLIP])
 482 | +        p = LP.send(segs, "pp-selectid.ledger_x.1", self.req)
 483 | +        self.assertEqual(os.listdir(self.req), ["pp-selectid.ledger_x.1.json"])           # no .tmp left
 484 | +        with open(p) as f:
 485 | +            self.assertEqual(json.load(f), {"request_id": "pp-selectid.ledger_x.1", "segments": segs})
 486 | +        with self.assertRaises(FileExistsError):
 487 | +            LP.send(segs, "pp-selectid.ledger_x.1", self.req)
 488 | +        for bad in ("", "a b", "x" * 121, "../x"):
 489 | +            with self.assertRaises(ValueError):
 490 | +                LP.send(segs, bad, self.req)
 491 | +
 492 | +
 493 | +class TestAnswer(Dirs):
 494 | +    def test_the_newest_matching_entry_of_ruling_72_and_only_it(self):
 495 | +        s = LP.segments_of([HOOK])[0]
 496 | +        self.put(s, entry(s, "hold", at="2026-11-13T22:00:00Z"), entry(s, "no_difference", at="2026-11-13T22:05:00Z"),
 497 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), rules=None),        # ruling 68's: never read
 498 | +                 entry(dict(s, approved_text="other words"), "adopted", at="2026-11-13T23:00:00Z"),
 499 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), window=[216.0, 228.674]),
 500 | +                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), role="clip"))
 501 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 502 | +        self.put(s, entry(s, "hold", at="2026-11-13T22:05:00Z", rid="r2"))                 # same time: the later one
 503 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "hold")
 504 | +        self.assertEqual(LP.answer(s, self.res, request_id="r1")["outcome"], "no_difference")
 505 | +        self.assertIsNone(LP.answer(s, self.res, request_id="r9"))
 506 | +        t = LP.segments_of([TRIM])[0]
 507 | +        self.put(t, dict(entry(t), untrimmed_start=1690.0))                               # the trim must match
 508 | +        self.assertIsNone(LP.answer(t, self.res))
 509 | +        with open(LP.result_file(LP.segments_of([CLIP])[0], self.res), "w") as f:
 510 | +            f.write("{not json")
 511 | +        self.assertIsNone(LP.answer(LP.segments_of([CLIP])[0], self.res))                  # unreadable: no answer
 512 | +
 513 | +
 514 | +class TestDecide(unittest.TestCase):
 515 | +    s = LP.segments_of([CLIP])[0]
 516 | +
 517 | +    def test_the_outcomes(self):
 518 | +        for out in ("no_difference", "adopted", "two_readings"):
 519 | +            self.assertEqual(LP.decide(self.s, entry(self.s, out))["verdict"], "pass")
 520 | +        self.assertEqual(LP.decide(self.s, entry(self.s, "hold", reason="ruling 72: at ['x']"))["why"],
 521 | +                         "ruling 72: at ['x']")
 522 | +        for e in (None, entry(self.s, "error"), entry(self.s, "decoded"), entry(self.s, "adopt_spoken"),
 523 | +                  entry(self.s, "adopt_spoken", spoken_text="  ")):
 524 | +            self.assertEqual(LP.decide(self.s, e)["verdict"], "error", e and e.get("outcome"))
 525 | +
 526 | +    def test_adopt_spoken_only_inside_ruling_67s_class_by_this_sides_check(self):
 527 | +        rep = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think I think Bitcoin only dropped like "
 528 | +                                                                          "5, 6%."))
 529 | +        self.assertEqual((rep["verdict"], rep["differences"][0]["class"]), ("adopt", "immediate repetition"))
 530 | +        fw = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think the Bitcoin only dropped like 5, 6%."))
 531 | +        self.assertEqual(fw["verdict"], "adopt")
 532 | +        for spoken in ("I think Bitcoin only dropped like 7, 6%.", "I think Ethereum only dropped like 5, 6%.",
 533 | +                       "I think Bitcoin never dropped like 5, 6%."):                      # a number, a name, a negation
 534 | +            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 535 | +            self.assertEqual(d["verdict"], "hold", spoken)
 536 | +            self.assertIn("outside ruling 67's class", d["why"])
 537 | +        same = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="i think bitcoin only dropped like 5 6%"))
 538 | +        self.assertEqual(same["verdict"], "pass")                                          # no canonical difference
 539 | +
 540 | +
 541 | +class TestCheck(Dirs):
 542 | +    def run_check(self, segs, appear=None, timeout=60.0):
 543 | +        t = [0.0]
 544 | +        sleeps = []
 545 | +
 546 | +        def sleep(s):
 547 | +            sleeps.append(s)
 548 | +            t[0] += s
 549 | +            if appear and len(sleeps) == 1:
 550 | +                appear()
 551 | +        rep = LP.check(segs, "pp-selectid.ledger_x.1", self.req, self.res, timeout_s=timeout, poll_s=10.0,
 552 | +                       clock=lambda: t[0], sleep=sleep, log=lambda m: None)
 553 | +        return rep, sleeps
 554 | +
 555 | +    def test_answers_on_file_are_used_and_nothing_is_asked(self):
 556 | +        segs = LP.segments_of([HOOK, CLIP])
 557 | +        for s in segs:
 558 | +            self.put(s, entry(s))
 559 | +        rep, sleeps = self.run_check([HOOK, CLIP])
 560 | +        self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
 561 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.25cd6f15e6c9.json")
 562 | +
 563 | +    def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
 564 | +        segs = LP.segments_of([HOOK, CLIP])
 565 | +        self.put(segs[0], entry(segs[0]))                                                  # one answered before
 566 | +        self.put(segs[1], entry(segs[1], "error"))                                         # an error: asked again
 567 | +
 568 | +        def appear():
 569 | +            for s in segs:
 570 | +                self.put(s, entry(s, rid="pp-selectid.ledger_x.1", at="2026-11-13T23:00:00Z"))
 571 | +        rep, sleeps = self.run_check([HOOK, CLIP], appear)
 572 | +        self.assertEqual((rep["ok"], rep["request_id"], len(sleeps)), (True, "pp-selectid.ledger_x.1", 1))
 573 | +        with open(os.path.join(self.req, "pp-selectid.ledger_x.1.json")) as f:
 574 | +            req = json.load(f)
 575 | +        self.assertEqual(len(req["segments"]), 2)                                          # the WHOLE line-up
 576 | +
 577 | +    def test_no_answer_in_time_is_no_verdict_never_a_pass(self):
 578 | +        rep, sleeps = self.run_check([HOOK, CLIP], timeout=30.0)
 579 | +        self.assertFalse(rep["ok"])
 580 | +        self.assertIn("no answer from the render's lock in time", rep["error"])
 581 | +        self.assertEqual(sleeps, [10.0, 10.0, 10.0])
 582 | +
 583 | +    def test_a_hold_is_not_ok_and_is_not_an_error(self):
 584 | +        segs = LP.segments_of([HOOK, CLIP])
 585 | +        self.put(segs[0], entry(segs[0], "hold", reason="PinError: edge"))
 586 | +        self.put(segs[1], entry(segs[1]))
 587 | +        rep, _ = self.run_check([HOOK, CLIP])
 588 | +        self.assertEqual((rep["ok"], rep["error"], rep["segments"][0]["verdict"]), (False, None, "hold"))
 589 | +
 590 | +
 591 | +class TestApply(Dirs):
 592 | +    def pk(self):
 593 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 594 | +                             for m in (HOOK, CLIP)],
 595 | +                "lines": [{"slot": "takeaway", "text": "Durability matters more than speed."}],
 596 | +                "hook_first_words": " ".join(HOOK["text"].split()[:8])}
 597 | +
 598 | +    def pre(self, hook_spoken=None):
 599 | +        segs = LP.segments_of([HOOK, CLIP])
 600 | +        self.put(segs[0], entry(segs[0], "adopt_spoken", spoken_text=hook_spoken) if hook_spoken else entry(segs[0]))
 601 | +        self.put(segs[1], entry(segs[1]))
 602 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 603 | +
 604 | +    def test_an_adopted_text_is_sealed_with_its_record_and_the_hook_words_follow(self):
 605 | +        spoken = "Bitcoin launched in in January of 2009. It's never been renamed."      # 'in' said twice
 606 | +        pk = LP.apply(self.pk(), self.pre(spoken))
 607 | +        s = pk["segments"][0]
 608 | +        self.assertEqual(s["text"], spoken)
 609 | +        self.assertEqual(s["attested"]["was"], HOOK["text"])
 610 | +        self.assertIn(s["attested"]["differences"][0]["class"], ("immediate repetition", "function word"))
 611 | +        self.assertEqual(pk["hook_first_words"], "Bitcoin launched in in January of 2009. It's")
 612 | +        named = "Bitcoin Bitcoin launched in January of 2009. It's never been renamed."   # a name is critical
 613 | +        with self.assertRaises(ValueError):                                                # (L-v 2): held
 614 | +            LP.apply(self.pk(), self.pre(named))
 615 | +        self.assertEqual(LP.pin_problems(pk), [])
 616 | +        self.assertNotIn("attested", pk["segments"][1])
 617 | +
 618 | +    def test_apply_refuses_what_does_not_cover_or_pass_or_is_quoted(self):
 619 | +        pre = self.pre()
 620 | +        other = self.pk()
 621 | +        other["segments"][1]["end"] = 958.0
 622 | +        with self.assertRaises(ValueError):
 623 | +            LP.apply(other, pre)                                                          # not these segments
 624 | +        with self.assertRaises(ValueError):
 625 | +            LP.apply(self.pk(), dict(pre, ok=False))
 626 | +        spoken = "Bitcoin launched in January of 2009. It's it's never been renamed."
 627 | +        quoting = self.pk()
 628 | +        quoting["lines"] = [{"slot": "takeaway", "text": "It's it's never been renamed, and that matters."}]
 629 | +        with self.assertRaises(ValueError):
 630 | +            LP.apply(quoting, self.pre(spoken))
 631 | +
 632 | +    def test_the_pin_stage_needs_a_passing_pre_check_on_these_segments(self):
 633 | +        self.assertIn("no passing lock pre-check", LP.pin_problems(self.pk())[0])
 634 | +        pk = LP.apply(self.pk(), self.pre())
 635 | +        self.assertEqual(LP.pin_problems(pk), [])
 636 | +        pk["segments"][0]["start"] = 216.2
 637 | +        self.assertIn("does not cover", LP.pin_problems(pk)[0])
 638 | +
 639 | +
 640 | +if __name__ == "__main__":
 641 | +    unittest.main()
 642 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 643 | index d084147..3a7d86f 100644
 644 | --- a/tests/package/test_medley.py
 645 | +++ b/tests/package/test_medley.py
 646 | @@ -524,7 +524,7 @@ class Rig:
 647 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 648 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 649 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 650 | -                 cached=False, candidate=None, visuals=None, registered=None):
 651 | +                 cached=False, candidate=None, visuals=None, registered=None, lock_check=None):
 652 |          import providers as P
 653 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 654 |          self.takeaways, self.spend = list(takeaways or []), spend
 655 | @@ -535,6 +535,7 @@ class Rig:
 656 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 657 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 658 |          self.registered = registered                        # ruling 66: the registry's line-ups (candidates.registered)
 659 | +        self.lock_check = lock_check                        # rulings 68 / 72: the render's lock (lock_precheck.check)
 660 |          self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 661 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 662 |          self.screens, self.events, self.a_seen = [], [], []
 663 | @@ -667,6 +668,8 @@ class Rig:
 664 |          kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
 665 |          if self.registered is not None:
 666 |              kw["registered"] = self.registered
 667 | +        if self.lock_check is not None:
 668 | +            kw["lock_check"] = self.lock_check
 669 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 670 |              import tempfile
 671 |              fd, path = tempfile.mkstemp(suffix=".json")
 672 | @@ -2040,6 +2043,97 @@ class TestRuling66Amended(unittest.TestCase):
 673 |                                               cx("the real productivity story"))[1], False)        # a clip's own
 674 |  
 675 |  
 676 | +def lock_stub(verdicts=None, error=False, calls=None):
 677 | +    """lock_precheck.check as the build calls it: each moment's outcome from `verdicts` ({moment id: (outcome,
 678 | +    spoken_text)}, default no_difference), decided by the real lock_precheck.decide; error: no answer at all."""
 679 | +    import lock_precheck as LP
 680 | +
 681 | +    def check(segs):
 682 | +        req = LP.segments_of(segs)
 683 | +        if calls is not None:
 684 | +            calls.append([m["moment_id"] for m in segs])
 685 | +        if error:
 686 | +            return {"ok": False, "request_id": "r", "error": "no answer from the render's lock in time",
 687 | +                    "segments": [dict(s, verdict="error", outcome=None, why="no answer", entry=None) for s in req]}
 688 | +        rows = []
 689 | +        for m, s in zip(segs, req):
 690 | +            out, spoken = (verdicts or {}).get(m["moment_id"], ("no_difference", None))
 691 | +            e = {"outcome": out, "reason": "PinError: the edge word" if out == "hold" else None,
 692 | +                 "spoken_text": spoken, "request_id": "r", "at": "2026-11-13T23:00:00Z", "lock": {"sha256": "ab" * 32}}
 693 | +            rows.append(dict(s, **LP.decide(s, e), entry={"request_id": "r", "outcome": out}))
 694 | +        return {"ok": all(r["verdict"] in ("pass", "adopt") for r in rows), "request_id": "r", "segments": rows,
 695 | +                "error": None}
 696 | +    return check
 697 | +
 698 | +
 699 | +class TestRuling72Lock(unittest.TestCase):
 700 | +    """RULINGS 68 / 72 (14:02; live 17:17 Nov 13): the render's own lock, asked for a line-up whose clips pass, BEFORE
 701 | +    any write: a held clip is out and the line-up re-lined; no verdict stops the search with nothing written; a package
 702 | +    seals the approved texts, or an adopted spoken text with its "attested" record; the pin stage checks it again."""
 703 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]   # every line-up >= 39 s
 704 | +
 705 | +    def test_a_held_clip_is_out_and_the_line_up_is_re_lined_before_any_write(self):
 706 | +        calls = []
 707 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 708 | +                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
 709 | +        out = rig.run()
 710 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
 711 | +        self.assertEqual(rig.write_calls, [(["h", "y", "z"], None)])               # nothing written for the held one
 712 | +        self.assertIn("ruling 72: the render's lock holds x: PinError: the edge word", out["tried"][0]["why"])
 713 | +        self.assertEqual(out["tried"][0]["precheck"]["segments"][1]["verdict"], "hold")
 714 | +        self.assertIsNotNone(out["package"])
 715 | +        import lock_precheck as LP
 716 | +        self.assertEqual(LP.pin_problems(out["package"]), [])                       # the pin stage's own check
 717 | +
 718 | +    def test_no_verdict_writes_nothing_and_stops_the_search(self):
 719 | +        rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
 720 | +                  lock_check=lock_stub(error=True))
 721 | +        out = rig.run()
 722 | +        self.assertIsNone(out["package"])
 723 | +        self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))       # no write, no second angle
 724 | +        self.assertTrue(out["tried"][0]["budget"])
 725 | +        self.assertIn("no lock verdict", out["lock_stop"])
 726 | +        c = PK.load_candidate(TestRuling66Candidate().record(), source="proof/ledger_x")
 727 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 728 | +                  lock_check=lock_stub(error=True)).run()
 729 | +        self.assertEqual(out["candidate"]["class"], "budget")                      # it stays as it was
 730 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 731 | +                  lock_check=lock_stub({"y": ("hold", None)})).run()
 732 | +        self.assertEqual(out["candidate"]["class"], "clip")                        # a clip fails a gate: closed
 733 | +
 734 | +    def test_an_adopted_spoken_text_is_sealed_with_its_record(self):
 735 | +        import lock_precheck as LP
 736 | +        spoken = self.MS[0]["text"].replace(" ", " the ", 1)                      # one function word more
 737 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 738 | +                  lock_check=lock_stub({"h": ("adopt_spoken", spoken)}))
 739 | +        pk = rig.run()["package"]
 740 | +        self.assertEqual(pk["segments"][0]["text"], spoken)
 741 | +        self.assertEqual(pk["segments"][0]["attested"]["was"], self.MS[0]["text"])
 742 | +        self.assertEqual(pk["hook_first_words"], " ".join(spoken.split()[:8]))
 743 | +        self.assertEqual(LP.pin_problems(pk), [])
 744 | +        pin = package_pin.to_pin(spk(pk), "test")
 745 | +        self.assertEqual(pin["segments"][0]["approved_text"], spoken)
 746 | +        self.assertEqual(pin["segments"][0]["attested"]["was"], self.MS[0]["text"])   # sealed (SEALED_LATER)
 747 | +        mp = pin["moments_package"]
 748 | +        self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"],
 749 | +                                          mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
 750 | +        bare = dict(pin["segments"][0])
 751 | +        bare.pop("attested")
 752 | +        self.assertNotEqual(package_pin.seal([bare] + pin["segments"][1:], mp["edl_vo"], mp["signoff_expected"],
 753 | +                                             mp["title"], mp["caption"], mp["gates"], mp.get("btc_screen")),
 754 | +                            mp["package_sha256"])                                 # the record is in the seal
 755 | +
 756 | +    def test_the_no_voice_line_up_asks_the_lock_too(self):
 757 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 758 | +        calls = []
 759 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 760 | +                  [None, None], takeaways=bad, lock_check=lock_stub({"z": ("hold", None)}, calls=calls))
 761 | +        out = rig.run()
 762 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y", "z"]])          # its own line-up, the added clip
 763 | +        self.assertIsNone(out["package"])
 764 | +        self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 765 | +
 766 | +
 767 |  class TestRuling65Caption(unittest.TestCase):
 768 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 769 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 770 | 
```

---

You are auditing a change to the medley pin builder on branch pp-selectid (Protocol Pulse: the builder of sealed medley
pins that an integrator renders). Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- A pin seals each clip's approved_text. At the render, ruling 17 locks the approved text to the render's own decode
  of the audio; a difference HOLDS the render.
- RULING 67: when the texts differ only by function words or the speaker's own immediate repetitions (attest.carry_class;
  never a number, a name or a negation: critical tokens), the pin may be re-sealed with the attested text and the
  verdicts carry over, recorded as "attested" (a sealed field: package_pin.SEALED_LATER). Lines that quote the changed
  words are re-gated first.
- RULING 68 (orchestrator 14:02): the integrator's pin-stage ruling-17 pre-check: "When it exists, your approved text
  comes from it."
- RULING 72 (now live on the integrator's side, 17:17), the contract they gave:
  - requests go to tests/package/proof/lock_requests/*.json (<name>.tmp, then rename). The service only reads there
    and answers each name + content once. Send the WHOLE line-up in one request, start/end exactly as the pin carries
    them.
  - results (read only): /home/ultron/protocol_pulse/data/lock_precheck/results/<video_id>.<start %.3f>-<end %.3f>.
    25cd6f15e6c9.json, a list. Take the newest entry with rules == "ruling 17 + ruling 72" whose window and role /
    approved_text / trimmed fields match yours; entries without "rules" are ruling 68's, ignore them.
  - outcomes: no_difference / adopted / two_readings = pass. adopt_spoken: "spoken_text" is the text to seal (already
    through the render's validate_range + segment_lock), every difference being in ruling 67's class. hold: the reason.
    error: no verdict, never a pass, never reused.
  - their advice: send the candidate texts BEFORE the paid verdicts.

The change:
1. pipeline/lock_precheck.py (new):
   - segments_of mirrors package_pin.to_pin: role, ms-rounded start/end, the moment's text, the trim fields only
     when trimmed;
   - answer(): the newest matching entry, optionally only a given request_id's;
   - send(): .tmp, then rename; never over an existing request;
   - decide(): adopt_spoken is adopted only when THIS side's attest.carry_class agrees; otherwise a hold;
   - check(): answers already on file are reused (never an error); else the whole line-up is sent and its own
     answers awaited (timeout 1200 s, poll 10 s); no answer = error;
   - apply(): the package's adopted texts plus the "attested" record and hook_first_words. It refuses unless the
     check passed and covers exactly the package's segments, and when a line quotes changed words;
   - pin_problems(): the pin stage's own check.
2. package.build(lock_check=) asks it for a line-up whose clips pass, BEFORE any write:
   - a held clip is dropped and doomed, and the line-up re-lined;
   - an error writes nothing and stops the search (out["lock_stop"], rec["budget"], so a candidate's class is
     "budget" and it stays as it was). Two guards stop it, the inner loop's condition and the angle loop's; either
     alone suffices;
   - a package goes through LP.apply before it is appended;
   - the no-voice line-up (its added clip) asks too.
   lock_check None (the test rigs): unchanged.
3. package_pin.to_pin copies "attested" into the pin segment (already sealed when present: SEALED_LATER). seal() is
   not changed. The integrator imports this file live for its seal recompute.
4. The driver passes lock_check to every build (request ids "pp-selectid.<build dir>.<n>"), and before write_pin
   refuses a package whose pin_problems() is non-empty.
5. Tests:
   - test_lock_precheck (12): the request's segments, matching and newest, request-id filtering, unreadable files,
     every outcome, this side's carry-class veto (a number, a name, a negation), reuse vs asking, the timeout,
     apply's refusals, the pin-stage check;
   - test_medley TestRuling72Lock (4): hold, then re-line; no verdict, then no write and the search stops (a
     candidate's class: budget; a held clip: clip); adoption sealed with its record and the seal recomputes; the
     no-voice line-up asks.
   Mutation runs: each wiring point removed fails a test. The two stop guards fail only together, by design.

Check, against the diff:
- that no pin can be sealed with a text the render's lock did not pass or adopt (the build gate, apply, and the
  driver's pin_problems);
- that an adopted text is only ever within ruling 67's class by THIS side's check, and is recorded and sealed;
- that "no verdict" is never a pass, and never closes a line-up as if it failed;
- the matching rules (newest, the ruling-72 entries only, window rounding, trim fields) against the contract above;
- request writing: atomic, never over an existing request, ids within the allowed characters;
- that nothing here changes what any other gate accepts, or seal().

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

