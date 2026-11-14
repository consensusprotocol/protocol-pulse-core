# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0108A
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

### File: docs/audits/parallel/pp-selectid_audit_0108/A/C1_STEP.diff (1542 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | new file mode 100644
   3 | index 0000000..0e79682
   4 | --- /dev/null
   5 | +++ b/pipeline/heimdall_health.py
   6 | @@ -0,0 +1,211 @@
   7 | +"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
   8 | +(verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.
   9 | +
  10 | +- Heimdall is DOWN when NO Heimdall family answers a verdict or writer call inside its deadline for DOWN_AFTER_S (15
  11 | +  minutes) running: note(False) starts the clock (failing_since), any note(True) stops it. One model down is not
  12 | +  'down': that is ruling 82's chain, and any family's answer stops the clock.
  13 | +- While calls are failing, and while in Plan B, a cheap probe (probe_due / probe_result) runs every PROBE_EVERY_S
  14 | +  (2 minutes).
  15 | +- Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  16 | +  BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
  17 | +- Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  18 | +  Heimdall evidence file (item 55); and, IN CAPITALS with the time, at the start of the caller's STATE line 1 (one
  19 | +  physical line).
  20 | +
  21 | +The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
  22 | +"probe_streak", "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  23 | +'up' or 'down' by guess: note() / mode() raise HealthUnreadable (fail closed: the caller decides, and says so).
  24 | +CPU only; no model call here (the caller makes the probe call and reports it)."""
  25 | +import fcntl
  26 | +import json
  27 | +import os
  28 | +import time
  29 | +from datetime import datetime, timezone
  30 | +
  31 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  32 | +                     "HEIMDALL_HEALTH.json")
  33 | +DOWN_AFTER_S = 15 * 60                  # ruling 87: no family answering for 15 minutes running
  34 | +PROBE_EVERY_S = 2 * 60                  # ruling 87: a cheap probe every 2 minutes while calls fail (and in Plan B)
  35 | +BACK_AFTER = 3                          # ruling 87: back to Heimdall-first after 3 probe answers in a row
  36 | +HEARTBEAT_S = 30.0                      # an answer is written at most once per 30 s per process while all is well
  37 | +_SEEN = {}                              # path -> monotonic time of this process's last written answer (no failure since)
  38 | +MODES = ("heimdall_first", "plan_b")
  39 | +
  40 | +
  41 | +class HealthUnreadable(Exception):
  42 | +    """The state file exists but cannot be read: no guess either way (law L-j)."""
  43 | +
  44 | +
  45 | +def _now(now=None):
  46 | +    return now if now is not None else datetime.now(timezone.utc)
  47 | +
  48 | +
  49 | +def _iso(t):
  50 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  51 | +
  52 | +
  53 | +def _t(s):
  54 | +    try:
  55 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  56 | +    except (TypeError, ValueError):
  57 | +        return None
  58 | +    return t if t.tzinfo is not None else None
  59 | +
  60 | +
  61 | +def _load(path):
  62 | +    if not os.path.exists(path):
  63 | +        return {"mode": "heimdall_first", "last_answer_utc": None, "failing_since_utc": None, "last_probe_utc": None,
  64 | +                "probe_streak": 0, "switches": [], "notes": 0}
  65 | +    try:
  66 | +        with open(path) as f:
  67 | +            s = json.load(f)
  68 | +        if not isinstance(s, dict) or s.get("mode") not in MODES:
  69 | +            raise ValueError("not a health state")
  70 | +        return s
  71 | +    except (OSError, ValueError) as e:
  72 | +        raise HealthUnreadable(f"{path}: {type(e).__name__}: {e}") from None
  73 | +
  74 | +
  75 | +def _save(path, s):
  76 | +    tmp = f"{path}.{os.getpid()}.tmp"
  77 | +    with open(tmp, "w") as f:
  78 | +        json.dump(s, f, indent=1)
  79 | +    os.replace(tmp, path)
  80 | +
  81 | +
  82 | +class _Locked:
  83 | +    def __init__(self, path):
  84 | +        self.path = path
  85 | +
  86 | +    def __enter__(self):
  87 | +        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
  88 | +        self.f = open(self.path + ".lock", "w")
  89 | +        fcntl.flock(self.f, fcntl.LOCK_EX)
  90 | +        return self
  91 | +
  92 | +    def __exit__(self, *exc):
  93 | +        fcntl.flock(self.f, fcntl.LOCK_UN)
  94 | +        self.f.close()
  95 | +        return False
  96 | +
  97 | +
  98 | +def _switch(s, to, why, now, evidence=None, state_md=None, who=""):
  99 | +    """Record one switch: the state, the evidence file, STATE line 1 (capitals, the time, one physical line)."""
 100 | +    rec = {"utc": _iso(now), "to": to, "why": why, "by": who}
 101 | +    s["mode"] = to
 102 | +    s.setdefault("switches", []).append(rec)
 103 | +    if evidence:
 104 | +        try:
 105 | +            with open(evidence, "a") as f:
 106 | +                f.write(json.dumps(dict(rec, kind="switch")) + "\n")
 107 | +        except OSError:
 108 | +            pass                                # evidence, never a gate (the state file holds the switch)
 109 | +    if state_md:
 110 | +        local = now.astimezone().strftime("%H:%M")
 111 | +        word = "SWITCHED TO PLAN B" if to == "plan_b" else "BACK TO HEIMDALL-FIRST"
 112 | +        head = f"{local} ET: {word} ({why.upper()}) |"
 113 | +        try:
 114 | +            with open(state_md) as f:
 115 | +                lines = f.read().split("\n")
 116 | +            lines[0] = f"{head} {lines[0]}" if lines and lines[0] else head
 117 | +            tmp = f"{state_md}.{os.getpid()}.tmp"
 118 | +            with open(tmp, "w") as f:
 119 | +                f.write("\n".join(lines))
 120 | +            os.replace(tmp, state_md)
 121 | +        except OSError:
 122 | +            pass                                # the state file and the evidence file hold the switch
 123 | +
 124 | +
 125 | +def announce(state_md, text, now=None):
 126 | +    """RULING 87: a Plan B fact the orchestrator must see, in capitals with the time, prepended to STATE line 1 (one
 127 | +    physical line). A file that cannot be written is left as it is (the build log carries the fact too)."""
 128 | +    now = _now(now)
 129 | +    head = f"{now.astimezone().strftime('%H:%M')} ET: {text.upper()} |"
 130 | +    try:
 131 | +        with open(state_md) as f:
 132 | +            lines = f.read().split("\n")
 133 | +        lines[0] = f"{head} {lines[0]}" if lines and lines[0] else head
 134 | +        tmp = f"{state_md}.{os.getpid()}.tmp"
 135 | +        with open(tmp, "w") as f:
 136 | +            f.write("\n".join(lines))
 137 | +        os.replace(tmp, state_md)
 138 | +    except OSError:
 139 | +        pass
 140 | +
 141 | +
 142 | +def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False):
 143 | +    """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
 144 | +    refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
 145 | +    drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
 146 | +    An answer while all is well is written at most once per HEARTBEAT_S per process (a failure is always written)."""
 147 | +    import time as _time
 148 | +    now, mono = _now(now), _time.monotonic()
 149 | +    if answered and not drill and mono - _SEEN.get(path, -1e9) < HEARTBEAT_S:
 150 | +        return "heimdall_first" if _SEEN.get(path + "#mode") != "plan_b" else "plan_b"
 151 | +    with _Locked(path):
 152 | +        s = _load(path)
 153 | +        if drill:
 154 | +            s["drills"], s["last_drill_utc"] = int(s.get("drills") or 0) + 1, _iso(now)
 155 | +            _save(path, s)
 156 | +            return s["mode"]
 157 | +        s["notes"] = int(s.get("notes") or 0) + 1
 158 | +        if answered:
 159 | +            s["last_answer_utc"], s["failing_since_utc"] = _iso(now), None
 160 | +        elif not s.get("failing_since_utc"):
 161 | +            s["failing_since_utc"] = _iso(now)
 162 | +        _down_rule(s, now, evidence, state_md, who)
 163 | +        _save(path, s)
 164 | +        if answered:
 165 | +            _SEEN[path], _SEEN[path + "#mode"] = mono, s["mode"]
 166 | +        else:
 167 | +            _SEEN.pop(path, None)
 168 | +        return s["mode"]
 169 | +
 170 | +
 171 | +def _down_rule(s, now, evidence, state_md, who):
 172 | +    fs = _t(s.get("failing_since_utc"))
 173 | +    if s["mode"] == "heimdall_first" and fs is not None and (now - fs).total_seconds() >= DOWN_AFTER_S:
 174 | +        _switch(s, "plan_b", f"no Heimdall family answered inside its deadline for "
 175 | +                             f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
 176 | +                state_md, who)
 177 | +        s["probe_streak"] = 0
 178 | +
 179 | +
 180 | +def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
 181 | +    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches). -> mode."""
 182 | +    now = _now(now)
 183 | +    with _Locked(path):
 184 | +        s = _load(path)
 185 | +        before = s["mode"]
 186 | +        _down_rule(s, now, evidence, state_md, who)
 187 | +        if s["mode"] != before:
 188 | +            _save(path, s)
 189 | +        return s["mode"]
 190 | +
 191 | +
 192 | +def probe_due(path=STATE, now=None):
 193 | +    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
 194 | +    now = _now(now)
 195 | +    with _Locked(path):
 196 | +        s = _load(path)
 197 | +        if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
 198 | +            return False
 199 | +        lp = _t(s.get("last_probe_utc"))
 200 | +        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S
 201 | +
 202 | +
 203 | +def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
 204 | +    """A probe's outcome (any Heimdall family answering it counts). BACK_AFTER answers in a row while in plan_b:
 205 | +    back to heimdall_first (the failure clock cleared). While not yet down, a probe answer is no verdict answer: the
 206 | +    15-minute clock runs on (the ruling counts verdict and writer calls). -> the mode after it."""
 207 | +    now = _now(now)
 208 | +    with _Locked(path):
 209 | +        s = _load(path)
 210 | +        s["last_probe_utc"] = _iso(now)
 211 | +        s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
 212 | +        if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
 213 | +            _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
 214 | +                    state_md, who)
 215 | +            s["failing_since_utc"], s["probe_streak"] = None, 0
 216 | +        _save(path, s)
 217 | +        return s["mode"]
 218 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
 219 | index 11238b1..446e62d 100644
 220 | --- a/pipeline/model_providers.json
 221 | +++ b/pipeline/model_providers.json
 222 | @@ -156,6 +156,26 @@
 223 |     "family": "glm",
 224 |     "base_url": "https://api-staging.heimdallm.com/api/v1",
 225 |     "measured": "ruling 82 (orchestrator 20:02 Nov 13): pp-ingest measured it 24/24 on calibration (default reasoning)"
 226 | +  },
 227 | +  "google:gemini-2.5-pro": {
 228 | +   "vendor": "google",
 229 | +   "model": "gemini-2.5-pro",
 230 | +   "family": "gemini",
 231 | +   "key_name": "GEMINI_API_KEY_MEDLEY",
 232 | +   "price_usd_per_1m": [
 233 | +    1.25,
 234 | +    10
 235 | +   ],
 236 | +   "min_out": 8000,
 237 | +   "timeout_s": 300,
 238 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled."
 239 | +  },
 240 | +  "local_judge:gemma3:27b": {
 241 | +   "vendor": "local_judge",
 242 | +   "model": "gemma3:27b",
 243 | +   "family": "gemma",
 244 | +   "deadline_floor_s": 2400,
 245 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min."
 246 |    }
 247 |   },
 248 |   "roles": {
 249 | @@ -183,6 +203,8 @@
 250 |      "xai:grok-4.20-0309-reasoning",
 251 |      "anthropic:claude-opus-5-5",
 252 |      "heimdall:deepseek/deepseek-v4.1-flash",
 253 | +    "heimdall:z-ai/glm-5.3-flash",
 254 | +    "heimdall:qwen/qwen3.8-27b",
 255 |      "local:gemma3:27b"
 256 |     ],
 257 |     "what": "vo_fidelity.py: the blind claim-by-claim verdict on VO, title and caption; never the writer's vendor"
 258 | @@ -203,6 +225,8 @@
 259 |     "chain": [
 260 |      "anthropic:claude-opus-5-5",
 261 |      "xai:grok-4.20-0309-reasoning",
 262 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 263 | +    "heimdall:z-ai/glm-5.3-flash",
 264 |      "heimdall:qwen/qwen3.8-27b",
 265 |      "local:gemma3:27b"
 266 |     ],
 267 | @@ -238,7 +262,9 @@
 268 |      "local:gemma3:27b",
 269 |      "xai:grok-4.20-0309-reasoning",
 270 |      "anthropic:claude-opus-5-5",
 271 | -    "heimdall:deepseek/deepseek-v4.1-flash"
 272 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 273 | +    "heimdall:z-ai/glm-5.3-flash",
 274 | +    "heimdall:qwen/qwen3.8-27b"
 275 |     ],
 276 |     "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
 277 |    },
 278 | @@ -247,6 +273,8 @@
 279 |      "anthropic:claude-opus-5-5",
 280 |      "xai:grok-4.20-0309-reasoning",
 281 |      "heimdall:deepseek/deepseek-v4.1-flash",
 282 | +    "heimdall:z-ai/glm-5.3-flash",
 283 | +    "heimdall:qwen/qwen3.8-27b",
 284 |      "local:gemma3:27b"
 285 |     ],
 286 |     "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
 287 | @@ -256,6 +284,8 @@
 288 |      "xai:grok-4.20-0309-reasoning",
 289 |      "anthropic:claude-opus-5-5",
 290 |      "heimdall:deepseek/deepseek-v4.1-flash",
 291 | +    "heimdall:z-ai/glm-5.3-flash",
 292 | +    "heimdall:qwen/qwen3.8-27b",
 293 |      "local:gemma3:27b"
 294 |     ],
 295 |     "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
 296 | @@ -275,5 +305,161 @@
 297 |     ],
 298 |     "what": "transcript_truth.py: law L-v 2's second, independent recognition pass with speaker turns on the selected segment's source audio (CPU fetch; no GPU, no Whisper)"
 299 |    }
 300 | + },
 301 | + "routing": {
 302 | +  "ruling": "RULING 85 (orchestrator 21:15 Nov 13, locked 21:18): HEIMDALL FIRST FOR EVERY VERDICT, GROK LAST, behind this switch. mode 'today': the chains under roles (with the 20:33 order: ruling 82's Heimdall chain after Grok on every verdict role). mode 'heimdall_first': the lists below; each Heimdall family is its own maker for every vendor rule, so the two-family rule is kept inside Heimdall (providers.Router). The per-type order is ruled from the replay (tests/package/replay85.py); until then each list is ruling 82's order (deepseek, glm, qwen), Grok last. A build names its routing (proof_ledger --routing).",
 303 | +  "mode": "today",
 304 | +  "verdict_roles": [
 305 | +   "context_verdict",
 306 | +   "coherence_verdict",
 307 | +   "fidelity_verdict",
 308 | +   "exclusion_verdict",
 309 | +   "speaker_verdict",
 310 | +   "viewer_takeaway"
 311 | +  ],
 312 | +  "verdict_deadline_s": {
 313 | +   "heimdall": 120
 314 | +  },
 315 | +  "heimdall_first": {
 316 | +   "context_verdict": [
 317 | +    "heimdall:qwen/qwen3.8-27b",
 318 | +    "heimdall:z-ai/glm-5.3-flash",
 319 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 320 | +    "xai:grok-4.20-0309-reasoning"
 321 | +   ],
 322 | +   "coherence_verdict": [
 323 | +    "xai:grok-4.20-0309-reasoning",
 324 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 325 | +   ],
 326 | +   "fidelity_verdict": [
 327 | +    "heimdall:qwen/qwen3.8-27b",
 328 | +    "heimdall:z-ai/glm-5.3-flash",
 329 | +    "xai:grok-4.20-0309-reasoning"
 330 | +   ],
 331 | +   "exclusion_verdict": [
 332 | +    "heimdall:z-ai/glm-5.3-flash",
 333 | +    "heimdall:qwen/qwen3.8-27b",
 334 | +    "xai:grok-4.20-0309-reasoning"
 335 | +   ],
 336 | +   "speaker_verdict": [
 337 | +    "xai:grok-4.20-0309-reasoning",
 338 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 339 | +    "heimdall:z-ai/glm-5.3-flash",
 340 | +    "heimdall:qwen/qwen3.8-27b"
 341 | +   ],
 342 | +   "viewer_takeaway": [
 343 | +    "xai:grok-4.20-0309-reasoning",
 344 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 345 | +    "heimdall:z-ai/glm-5.3-flash",
 346 | +    "heimdall:qwen/qwen3.8-27b"
 347 | +   ],
 348 | +   "context_verdict:step_a_first": [
 349 | +    "heimdall:qwen/qwen3.8-27b",
 350 | +    "heimdall:z-ai/glm-5.3-flash",
 351 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 352 | +    "xai:grok-4.20-0309-reasoning"
 353 | +   ],
 354 | +   "context_verdict:step_a_second": [
 355 | +    "xai:grok-4.20-0309-reasoning",
 356 | +    "heimdall:qwen/qwen3.8-27b",
 357 | +    "heimdall:z-ai/glm-5.3-flash",
 358 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 359 | +   ],
 360 | +   "context_verdict:step_c": [
 361 | +    "xai:grok-4.20-0309-reasoning",
 362 | +    "heimdall:z-ai/glm-5.3-flash",
 363 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 364 | +   ],
 365 | +   "coherence_verdict:hook": [
 366 | +    "heimdall:qwen/qwen3.8-27b",
 367 | +    "heimdall:z-ai/glm-5.3-flash",
 368 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 369 | +    "xai:grok-4.20-0309-reasoning"
 370 | +   ],
 371 | +   "coherence_verdict:clips_alone": [
 372 | +    "xai:grok-4.20-0309-reasoning",
 373 | +    "heimdall:qwen/qwen3.8-27b",
 374 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 375 | +   ],
 376 | +   "coherence_verdict:coherence": [
 377 | +    "xai:grok-4.20-0309-reasoning",
 378 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 379 | +   ]
 380 | +  },
 381 | +  "plan_b": {
 382 | +   "context_verdict": [
 383 | +    "xai:grok-4.20-0309-reasoning",
 384 | +    "google:gemini-2.5-pro",
 385 | +    "openai:gpt-6.1-sol",
 386 | +    "anthropic:claude-opus-5-5",
 387 | +    "local_judge:gemma3:27b"
 388 | +   ],
 389 | +   "coherence_verdict": [
 390 | +    "xai:grok-4.20-0309-reasoning",
 391 | +    "google:gemini-2.5-pro",
 392 | +    "openai:gpt-6.1-sol",
 393 | +    "anthropic:claude-opus-5-5"
 394 | +   ],
 395 | +   "fidelity_verdict": [
 396 | +    "xai:grok-4.20-0309-reasoning",
 397 | +    "google:gemini-2.5-pro",
 398 | +    "openai:gpt-6.1-sol",
 399 | +    "anthropic:claude-opus-5-5"
 400 | +   ],
 401 | +   "exclusion_verdict": [
 402 | +    "xai:grok-4.20-0309-reasoning",
 403 | +    "google:gemini-2.5-pro",
 404 | +    "openai:gpt-6.1-sol",
 405 | +    "anthropic:claude-opus-5-5"
 406 | +   ],
 407 | +   "speaker_verdict": [
 408 | +    "xai:grok-4.20-0309-reasoning",
 409 | +    "google:gemini-2.5-pro",
 410 | +    "openai:gpt-6.1-sol",
 411 | +    "anthropic:claude-opus-5-5"
 412 | +   ],
 413 | +   "viewer_takeaway": [
 414 | +    "xai:grok-4.20-0309-reasoning",
 415 | +    "google:gemini-2.5-pro",
 416 | +    "openai:gpt-6.1-sol",
 417 | +    "anthropic:claude-opus-5-5"
 418 | +   ],
 419 | +   "angle_write": [
 420 | +    "xai:grok-4.20-0309-reasoning",
 421 | +    "google:gemini-2.5-pro",
 422 | +    "openai:gpt-6.1-sol",
 423 | +    "anthropic:claude-opus-5-5"
 424 | +   ],
 425 | +   "visual_check": [
 426 | +    "xai_vision:grok-4.7"
 427 | +   ]
 428 | +  },
 429 | +  "plan_b_note": "RULING 87: while pipeline/heimdall_health.py says Heimdall is down (no family answered a verdict or writer call inside its deadline for 15 minutes running), these roles run on these chains: Grok mainly, then any other outside key that answers (Gemini's fenced key; OpenAI and Anthropic only when a call shows they have credit: they are tried, never assumed). Back to the mode's chains when the probe has answered 3 times in a row.",
 430 | +  "shadow": {
 431 | +   "*": "xai:grok-4.20-0309-reasoning",
 432 | +   "visual_check": "xai_vision:grok-4.7"
 433 | +  },
 434 | +  "shadow_until_clean_pins": 3,
 435 | +  "shadow_note": "RULING 86: a heimdall_first build asks these back-ends the same prompt of every verdict Heimdall decided (recorded, never deciding) until 3 pins in a row show no decision-changing difference.",
 436 | +  "today_unbounded": [
 437 | +   "context_verdict"
 438 | +  ],
 439 | +  "today": {
 440 | +   "coherence_verdict:coherence": [
 441 | +    "xai:grok-4.20-0309-reasoning",
 442 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 443 | +   ],
 444 | +   "coherence_verdict:clips_alone": [
 445 | +    "xai:grok-4.20-0309-reasoning",
 446 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 447 | +    "heimdall:qwen/qwen3.8-27b"
 448 | +   ],
 449 | +   "context_verdict:step_c": [
 450 | +    "xai:grok-4.20-0309-reasoning",
 451 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 452 | +    "heimdall:z-ai/glm-5.3-flash"
 453 | +   ]
 454 | +  },
 455 | +  "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first."
 456 |   }
 457 |  }
 458 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 459 | index 55b66b3..7cd332c 100644
 460 | --- a/pipeline/providers.py
 461 | +++ b/pipeline/providers.py
 462 | @@ -254,6 +254,86 @@ class OpenAIBackend(Backend):
 463 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 464 |  
 465 |  
 466 | +class GeminiBackend(Backend):
 467 | +    """Google Gemini generateContent. RULING 87 (21:18 Nov 13): PLAN B ONLY. The key (key_name, default
 468 | +    GEMINI_API_KEY_MEDLEY) is fenced to this pipeline. It is sent in a header, never in the URL. JSON is asked for in
 469 | +    words and by responseMimeType. The reply's usageMetadata gives the tokens (thinking counted as output). Gemini
 470 | +    reports no cost, so the price-table estimate stands for each call, labelled as one."""
 471 | +    vendor = "google"
 472 | +    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
 473 | +
 474 | +    def complete(self, prompt, max_tokens, seed, system=None):
 475 | +        if is_vision(prompt):
 476 | +            raise RequestRejected("gemini: no image input on this back-end")
 477 | +        key = self.key(self.spec.get("key_name") or "GEMINI_API_KEY_MEDLEY")
 478 | +        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
 479 | +                "generationConfig": {"maxOutputTokens": self.max_out(max_tokens), "temperature": 0, "seed": seed,
 480 | +                                     "responseMimeType": "application/json"}}
 481 | +        if system:
 482 | +            body["systemInstruction"] = {"parts": [{"text": system}]}
 483 | +        t0 = time.time()
 484 | +        j = _with_backoff(lambda: _http_json(self.URL.format(model=self.model), body, {"x-goog-api-key": key},
 485 | +                                             self.timeout))
 486 | +        u = j.get("usageMetadata") or {}
 487 | +        try:
 488 | +            parts = j["candidates"][0]["content"]["parts"]
 489 | +            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
 490 | +        except (KeyError, IndexError, TypeError):
 491 | +            raise RequestRejected("gemini: no candidates") from None
 492 | +        return text, {"in": int(u.get("promptTokenCount") or 0),
 493 | +                      "out": int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)}, \
 494 | +            time.time() - t0
 495 | +
 496 | +
 497 | +class LocalJudgeBackend(Backend):
 498 | +    """RULING 87 (21:18 Nov 13): the integrator's GPU0 judge service (gemma3:27b). PLAN B ONLY: step A's verdict when
 499 | +    only one outside family answers. The integrator's contract (its message of 21:4x Nov 13):
 500 | +    - a request file in this worktree's tests/package/proof/judge_requests/<request_id>.json (written .tmp, then
 501 | +      renamed; read-only there, answered once per name and content), body {request_id, family "step_a", prompt,
 502 | +      max_tokens, seed}, ONE call per request;
 503 | +    - the answer in RESULTS/<request_id>.<prompt_id>.json, prompt_id = sha256(json.dumps([prompt, max_tokens,
 504 | +      seed]))[:20] (the integrator's local_judge.prompt_id; live 22:26:30 Nov 13, judge_sha c62a1e12088c), with
 505 | +      {request_id, family, prompt_id, model, digest, seed, max_tokens, text, error, seconds, waited_s, at, judge_sha}.
 506 | +      Only that exact file is read: an answer is this prompt's by its own sha.
 507 | +    A render always comes first, so the wait allows WAIT_S (40 min). No answer in time, an error, or a file that
 508 | +    cannot be read is no verdict (Unavailable for this call). The reply's contract is checked by the caller, as for a
 509 | +    vendor's. Local: free, no spend."""
 510 | +    vendor = "local_judge"
 511 | +    REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
 512 | +                            "judge_requests")
 513 | +    RESULTS = "/home/ultron/protocol_pulse/data/local_judge/results"      # the integrator's; read only
 514 | +    WAIT_S, POLL_S = 2400.0, 10.0
 515 | +
 516 | +    def complete(self, prompt, max_tokens, seed, system=None):
 517 | +        if is_vision(prompt) or system:
 518 | +            raise RequestRejected("local judge: a text prompt without a system message only")
 519 | +        rid = f"pp-selectid.{time.strftime('%Y%m%dT%H%M%S')}.{uuid.uuid4().hex[:8]}"
 520 | +        pid = hashlib.sha256(json.dumps([prompt, int(max_tokens), int(seed)]).encode()).hexdigest()[:20]
 521 | +        os.makedirs(self.REQUESTS, exist_ok=True)
 522 | +        tmp, final = os.path.join(self.REQUESTS, rid + ".tmp"), os.path.join(self.REQUESTS, rid + ".json")
 523 | +        with open(tmp, "x") as f:
 524 | +            json.dump({"request_id": rid, "family": "step_a", "prompt": prompt, "max_tokens": int(max_tokens),
 525 | +                       "seed": int(seed)}, f)
 526 | +        os.rename(tmp, final)
 527 | +        t0 = time.time()
 528 | +        answer = os.path.join(self.RESULTS, f"{rid}.{pid}.json")
 529 | +        while True:
 530 | +            if os.path.exists(answer):
 531 | +                try:
 532 | +                    with open(answer) as f:
 533 | +                        rec = json.load(f)
 534 | +                except (OSError, ValueError) as e:
 535 | +                    raise Unavailable(f"local judge: the answer cannot be read ({type(e).__name__})") from None
 536 | +                if not isinstance(rec, dict) or rec.get("request_id") != rid or rec.get("prompt_id") != pid or \
 537 | +                        rec.get("error") or not isinstance(rec.get("text"), str):
 538 | +                    raise RequestRejected(f"local judge: no verdict ({str((rec or {}).get('error'))[:200]})")
 539 | +                return rec["text"], {"in": 0, "out": 0, **{k: rec.get(k) for k in ("judge_sha", "digest",
 540 | +                                                                                    "waited_s")}}, time.time() - t0
 541 | +            if time.time() - t0 >= self.WAIT_S:
 542 | +                raise Unavailable(f"local judge: no answer within {self.WAIT_S:.0f} s (a render comes first)")
 543 | +            time.sleep(self.POLL_S)
 544 | +
 545 | +
 546 |  class DeadlineExceeded(Exception):
 547 |      """A back-end gave no answer within the caller's deadline (orchestrator 22:40 ruling 5: one writer call never waits
 548 |      more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 549 | @@ -577,7 +657,48 @@ class ElevenLabsTranscribe(STTBackend):
 550 |  
 551 |  
 552 |  VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "xai_vision": XAIVisionBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 553 | -           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}
 554 | +           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe,
 555 | +           "google": GeminiBackend, "local_judge": LocalJudgeBackend}
 556 | +
 557 | +
 558 | +ROUTINGS = ("today", "heimdall_first")    # RULING 85 (21:15 Nov 13): the switch (model_providers.json "routing")
 559 | +SHADOW_ROLES = ("context_verdict", "coherence_verdict", "fidelity_verdict", "exclusion_verdict", "speaker_verdict",
 560 | +                "viewer_takeaway", "visual_check")      # RULING 86: the verdicts a shadow back-end is asked again
 561 | +
 562 | +
 563 | +def gateway(b):
 564 | +    """The vendor a back-end is reached through: "heimdall" for every Heimdall model, whatever its routing makes of
 565 | +    b.vendor (ruling 85: under heimdall_first, a Heimdall family is its own maker, b.vendor == "heimdall/<family>")."""
 566 | +    return getattr(b, "gateway", b.vendor)
 567 | +
 568 | +
 569 | +def call_parsed(router, role, prompt, parse, max_tokens=2000, seed=7, system=None, avoid_vendor=None,
 570 | +                avoid_model=None, avoid_family=None, deadline_s=None, kind=None):
 571 | +    """The 20:33 order (ruling 82's chain on every verdict): the role's chain, where an answer OUT OF CONTRACT also
 572 | +    moves on to the next model, each model once. parse(text) raises ValueError / TypeError / KeyError for an answer
 573 | +    out of contract; that reply is rejected (its recording dropped, so it is asked again another time) and its model
 574 | +    skipped. -> (reply, parse(reply.text)). The chain spent: ProviderError (no verdict; nothing is cached by the
 575 | +    caller). Errors of the back-ends themselves (down, refused, past the deadline, empty) move on inside Router.call.
 576 | +    Works with any router that has call() (and reject(), when it has one)."""
 577 | +    skip, why = set(_as_set(avoid_model)), []
 578 | +    while True:
 579 | +        kw = {k: v for k, v in (("system", system), ("avoid_vendor", avoid_vendor), ("avoid_family", avoid_family),
 580 | +                                ("deadline_s", deadline_s), ("kind", kind)) if v is not None}
 581 | +        try:
 582 | +            r = router.call(role, prompt, max_tokens, seed, **kw, **({"avoid_model": frozenset(skip)} if skip else {}))
 583 | +        except ProviderError as e:
 584 | +            if why:
 585 | +                raise ProviderError(f"{e}; answers out of contract: {why}") from e
 586 | +            raise
 587 | +        if r.backend in skip:                      # never a loop: a model told to skip answered again (no verdict)
 588 | +            raise ProviderError(f"{role}: {r.backend} answered again though skipped; answers out of contract: {why}")
 589 | +        try:
 590 | +            return r, parse(r.text)
 591 | +        except (ValueError, TypeError, KeyError) as e:
 592 | +            if hasattr(router, "reject"):
 593 | +                router.reject(r)
 594 | +            why.append((r.backend, f"{type(e).__name__}: {str(e)[:120]}"))
 595 | +            skip.add(r.backend)
 596 |  
 597 |  
 598 |  def _as_set(x):
 599 | @@ -594,9 +715,14 @@ class Router:
 600 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
 601 |  
 602 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 603 | -                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0):
 604 | +                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 605 | +                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None):
 606 |          with open(config) as f:
 607 |              self.config = json.load(f)
 608 | +        rt = self.config.get("routing") or {}
 609 | +        self.routing = routing or rt.get("mode") or "today"     # RULING 85: "today" or "heimdall_first"
 610 | +        if self.routing not in ROUTINGS:
 611 | +            raise ValueError(f"routing must be one of {ROUTINGS}, not {self.routing!r}")
 612 |          self.env_path = env_path or ENV_PATH
 613 |          self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
 614 |          if limit_basis not in ("estimate", "reported"):
 615 | @@ -612,10 +738,46 @@ class Router:
 616 |              self.backends[name] = cls(name, spec, self.env_path, local_llm) if cls is LocalBackend else \
 617 |                  cls(name, spec, self.env_path)
 618 |          self.chains = dict(chains or {})          # tests / the A/B harness may pin a role's chain (still by config name)
 619 | -
 620 | -    def chain(self, role):
 621 | -        if role in self.chains:
 622 | -            return list(self.chains[role])
 623 | +        # RULING 86 (21:18 Nov 13): {role or "*": back-end} asked the SAME prompt of every verdict another back-end
 624 | +        # decided (recorded to shadow_log, never deciding); its role is "shadow86:<role>", so its recordings and its
 625 | +        # spend (ruling 48's ledger) are its own
 626 | +        self.shadow, self.shadow_log, self._shadows = dict(shadow or {}), shadow_log, []
 627 | +        for r_, name_ in self.shadow.items():
 628 | +            if name_ not in self.backends:
 629 | +                raise ValueError(f"the shadow back-end {name_!r} is not in the config")
 630 | +        # RULING 87 (21:18 Nov 13): PLAN B. health: the shared state file (pipeline/heimdall_health.py); every
 631 | +        # Heimdall verdict or writer call's outcome is noted there, and while it says "plan_b" the roles named in
 632 | +        # plan_b_chains (frozen legs already out) run on them: Grok mainly, then any other outside key that answers.
 633 | +        # A probe thread asks each Heimdall family a one-word question every 2 minutes while calls fail.
 634 | +        self.health, self.plan_b_chains, self.state_md = health, dict(plan_b_chains or {}), state_md
 635 | +        self._probe = None
 636 | +        if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 637 | +            for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 638 | +                if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 639 | +                    b.gateway, b.vendor = b.vendor, f"{b.vendor}/{b.family}"
 640 | +
 641 | +    def mode(self):
 642 | +        """RULING 87: "plan_b" while the shared health state says Heimdall is down, else this router's routing."""
 643 | +        if not self.health:
 644 | +            return self.routing
 645 | +        import heimdall_health as HH
 646 | +        return "plan_b" if HH.mode(self.health, evidence=self.deadline_log, state_md=self.state_md,
 647 | +                                   who="pp-selectid") == "plan_b" else self.routing
 648 | +
 649 | +    def chain(self, role, kind=None):
 650 | +        """The back-ends a call of `role` tries, in order. RULING 88 (22:15 Nov 13): a verdict TYPE may have its own
 651 | +        list, keyed "<role>:<kind>" (step_a_first, step_a_second, step_c, hook, clips_alone, coherence); without one,
 652 | +        the role's. Plan B's lists first while Heimdall is down (ruling 87); then this router's overrides; then the
 653 | +        routing's lists (ruling 85, not under "today"); then the role's configured chain."""
 654 | +        keys = ([f"{role}:{kind}"] if kind else []) + [role]
 655 | +        if self.health and any(k in self.plan_b_chains for k in keys) and self.mode() == "plan_b":
 656 | +            return list(next(self.plan_b_chains[k] for k in keys if k in self.plan_b_chains))   # ruling 87
 657 | +        for k in keys:
 658 | +            if k in self.chains:
 659 | +                return list(self.chains[k])
 660 | +            routed = ((self.config.get("routing") or {}).get(self.routing) or {}).get(k)
 661 | +            if routed:                            # RULING 85 / 88: this routing's own list (today: per type only)
 662 | +                return list(routed)
 663 |          try:
 664 |              return list(self.config["roles"][role]["chain"])
 665 |          except KeyError:
 666 | @@ -825,6 +987,119 @@ class Router:
 667 |          except OSError:
 668 |              return False
 669 |  
 670 | +    def role_deadline(self, role, b):
 671 | +        """The 20:33 order (ruling 82's chain on the verdicts): a call of a verdict role on a back-end whose gateway
 672 | +        names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets it when the
 673 | +        caller sets none. -> seconds or None."""
 674 | +        rt = self.config.get("routing") or {}
 675 | +        bounded = set(rt.get("verdict_roles") or ())
 676 | +        if self.routing == "today":                   # step A's first screen and step C keep no deadline today:
 677 | +            bounded -= set(rt.get("today_unbounded") or ())   # ruling 82 bounded only the second screen (8 clips a
 678 | +        if role not in bounded:                       # call cannot answer in 120 s on Heimdall)
 679 | +            return None
 680 | +        d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 681 | +        return float(d) if _num(d) and d > 0 else None
 682 | +
 683 | +    def _note(self, role, b, answered):
 684 | +        """RULING 87: a Heimdall verdict or writer call's outcome, to the shared health state (never a gate here: a
 685 | +        state file that cannot be written is a notice). The probe thread starts at the first failure."""
 686 | +        rt = self.config.get("routing") or {}
 687 | +        if not self.health or not isinstance(b, HeimdallBackend) or \
 688 | +                role not in set(rt.get("verdict_roles") or ()) | {"angle_write"}:
 689 | +            return
 690 | +        import heimdall_health as HH
 691 | +        try:
 692 | +            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
 693 | +        except (HH.HealthUnreadable, OSError) as e:
 694 | +            n = f"RULING 87: the Heimdall health state cannot be read or written: {e}"
 695 | +            if n not in self.notices:
 696 | +                self.notices.append(n)
 697 | +        if not answered:
 698 | +            self.start_probe()
 699 | +
 700 | +    def start_probe(self, every_s=30.0):
 701 | +        """RULING 87: the probe thread (one per router): while HH.probe_due, ask each Heimdall family a one-word
 702 | +        question (60 s each, on ruling 48's ledger as role "probe87"); any answer is a probe answer."""
 703 | +        import threading
 704 | +        if self._probe is not None or not self.health:
 705 | +            return
 706 | +        import heimdall_health as HH
 707 | +        fams = [n for n, b in self.backends.items() if isinstance(b, HeimdallBackend) and n.startswith("heimdall:")
 708 | +                and b.family in ("deepseek", "glm", "qwen")]
 709 | +
 710 | +        def loop():
 711 | +            while True:
 712 | +                try:
 713 | +                    if HH.probe_due(self.health):
 714 | +                        HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
 715 | +                                        state_md=self.state_md, who="pp-selectid probe")
 716 | +                except Exception:                      # noqa: BLE001 (the probe never stops a build)
 717 | +                    pass
 718 | +                time.sleep(every_s)
 719 | +        self._probe = threading.Thread(target=loop, daemon=True, name="pp-probe87")
 720 | +        self._probe.start()
 721 | +
 722 | +    def probe_once(self, names):
 723 | +        """RULING 87: one probe round: each Heimdall family asked a one-word question (60 s, never recorded nor served
 724 | +        from a recording). A family this run marked down is probed all the same: its mark is lifted for the probe and
 725 | +        stays lifted when it answers (it may serve again), restored when it does not. -> True if any family answered."""
 726 | +        ok = False
 727 | +        for n in names:
 728 | +            self.chains.setdefault(f"probe87:{n}", [n])
 729 | +            was = self.down.pop(n, None)
 730 | +            try:
 731 | +                r = self.call(f"probe87:{n}", "Reply with the single word OK.", 64, 7, deadline_s=60.0)
 732 | +                ok = ok or bool(r.text.strip())
 733 | +            except Exception:                          # noqa: BLE001 (a probe that fails is a probe that failed)
 734 | +                if was is not None and n not in self.down:
 735 | +                    self.down[n] = was
 736 | +        return ok
 737 | +
 738 | +    def _shadow_of(self, role):
 739 | +        return self.shadow.get(role) or self.shadow.get("*")
 740 | +
 741 | +    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding):
 742 | +        """RULING 86: ask the role's shadow back-end the same prompt, in a thread; one JSON line to shadow_log per
 743 | +        verdict with both answers. Never raises into the build and never decides."""
 744 | +        import threading
 745 | +        name = self._shadow_of(role)
 746 | +        self.chains.setdefault(f"shadow86:{role}", [name])
 747 | +
 748 | +        def run():
 749 | +            rec = {"role": role, "prompt": prompt_text(prompt), "images": len(prompt["images"]) if is_vision(prompt)
 750 | +                   else 0, "max_tokens": max_tokens, "seed": seed, "system": system,
 751 | +                   "deciding": {"backend": deciding.backend, "vendor": deciding.vendor, "text": deciding.text,
 752 | +                                "cached": bool(getattr(deciding, "cached", False))}}
 753 | +            t0 = time.time()
 754 | +            try:
 755 | +                r = self.call(f"shadow86:{role}", prompt, max_tokens, seed, system=system)
 756 | +                rec["shadow"] = {"backend": r.backend, "text": r.text, "seconds": round(time.time() - t0, 2),
 757 | +                                 "cached": bool(getattr(r, "cached", False)),
 758 | +                                 "usd_reported": (r.usage or {}).get("usd_reported"), "usd_estimate": r.usd}
 759 | +            except Exception as e:                     # noqa: BLE001 (a shadow never stops a build)
 760 | +                rec["shadow"] = {"backend": name, "error": f"{type(e).__name__}: {str(e)[:300]}",
 761 | +                                 "seconds": round(time.time() - t0, 2)}
 762 | +            if self.shadow_log:
 763 | +                line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
 764 | +                try:
 765 | +                    with self._log_lock:
 766 | +                        os.makedirs(os.path.dirname(os.path.abspath(self.shadow_log)), exist_ok=True)
 767 | +                        with open(self.shadow_log, "a") as f:
 768 | +                            f.write(line + "\n")
 769 | +                except OSError as e:
 770 | +                    self.notices.append(f"the shadow log could not be written: {type(e).__name__}: {e}")
 771 | +        t = threading.Thread(target=run, daemon=True, name="pp-shadow86")
 772 | +        self._shadows.append(t)
 773 | +        t.start()
 774 | +
 775 | +    def shadow_wait(self, timeout_s=900.0):
 776 | +        """RULING 86: wait for every shadow call of this router (a build's side-by-side needs them all). -> the number
 777 | +        still running when the time ran out (their lines are then missing from shadow_log, and the report says so)."""
 778 | +        end = time.time() + timeout_s
 779 | +        for t in list(self._shadows):
 780 | +            t.join(max(0.0, end - time.time()))
 781 | +        return sum(t.is_alive() for t in self._shadows)
 782 | +
 783 |      def heimdall_tripwire(self, at=0.9):
 784 |          """NOTIFY when Heimdall's account usage reaches `at` of its credits (PBX 02:45: never a halt)."""
 785 |          h = next((b for b in self.backends.values() if isinstance(b, HeimdallBackend)), None)
 786 | @@ -859,10 +1134,10 @@ class Router:
 787 |          os.replace(tmp, path)
 788 |  
 789 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 790 | -             avoid_family=None, deadline_s=None):
 791 | +             avoid_family=None, deadline_s=None, kind=None):
 792 |          av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
 793 |          tried, notices = [], []
 794 | -        for name in self.chain(role):
 795 | +        for name in self.chain(role, kind):           # ruling 88: the verdict type's own list when it has one
 796 |              b = self.backends.get(name)
 797 |              why = self._skip(name, b, av, am, af)
 798 |              if why is None and isinstance(b, STTBackend):
 799 | @@ -874,23 +1149,36 @@ class Router:
 800 |              if why:
 801 |                  tried.append((name, why))
 802 |                  continue
 803 | -            path = self._path(role, name, prompt, max_tokens, seed, system) if self.record_dir else None
 804 | +            path = self._path(role, name, prompt, max_tokens, seed, system) \
 805 | +                if self.record_dir and not role.startswith("probe87:") else None      # ruling 87: a probe is live
 806 |              if path and os.path.exists(path):
 807 |                  with open(path) as f:
 808 |                      rec = json.load(f)
 809 | -                return Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 810 | -                             rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 811 | +                out = Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 812 | +                            rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 813 | +                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 814 | +                    self._shadow_ask(role, prompt, max_tokens, seed, system, out)  # ruling 86: a recorded verdict too
 815 | +                return out
 816 |              if self.replay:
 817 |                  tried.append((name, "replay: not recorded"))
 818 |                  continue
 819 |              upper = b.upper_usd(prompt, max_tokens, system)
 820 |              key = self._reserve(b, upper)
 821 | -            if b.vendor == "heimdall":
 822 | +            if isinstance(b, HeimdallBackend):
 823 |                  n = self.heimdall_tripwire()
 824 |                  if n:
 825 |                      notices.append(n)
 826 |  
 827 | -            def abandon(b=b, key=key, name=name):      # RULING 83 (a): booked at its PROMPT tokens (input rate), an
 828 | +            dl = deadline_s or self.role_deadline(role, b)      # the caller's deadline, else the role's (20:33)
 829 | +            if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
 830 | +                dl = max(dl, float(b.spec["deadline_floor_s"]))
 831 | +            if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
 832 | +                import heimdall_health as HH
 833 | +                self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
 834 | +                HH.announce(self.state_md, "PLAN B WITH ONE OUTSIDE FAMILY: STEP A'S VERDICT IS ASKED OF THE LOCAL "
 835 | +                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)")
 836 | +
 837 | +            def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 838 |                  booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 839 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 840 |                                  "deadline_s": deadline_s, "seconds": deadline_s,
 841 | @@ -899,22 +1187,25 @@ class Router:
 842 |                  self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 843 |                  return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 844 |              try:
 845 | -                if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 846 | -                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system),
 847 | +                if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 848 | +                    text, usage, secs = _within(dl, lambda: b.complete(prompt, max_tokens, seed, system),
 849 |                                                  on_abandon=abandon, on_late=self._late)
 850 |                  else:
 851 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 852 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 853 | -                booked = b.prompt_usd(prompt, system)  # abandon()
 854 | +                self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 855 | +                booked = b.prompt_usd(prompt, system)
 856 |                  tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 857 |                                      "ruling 83 (a))"))
 858 |                  continue
 859 |              except RequestRejected as e:
 860 |                  self._settle(key)
 861 | +                self._note(role, b, False)
 862 |                  tried.append((name, f"refused this request: {e}"))
 863 |                  continue
 864 |              except Unavailable as e:
 865 |                  self._settle(key)
 866 | +                self._note(role, b, False)
 867 |                  self.down[name] = str(e)
 868 |                  tried.append((name, str(e)))
 869 |                  continue
 870 | @@ -925,13 +1216,15 @@ class Router:
 871 |              self._settle(key, b, usage, usd, role)
 872 |              if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
 873 |                  self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
 874 | -                                "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
 875 | +                                "vendor": b.vendor, "deadline_s": dl, "seconds": round(secs, 2),
 876 |                                  "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 877 |                                  "in": (usage or {}).get("in"),
 878 |                                  "out": (usage or {}).get("out")})
 879 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
 880 | +                self._note(role, b, False)
 881 |                  tried.append((name, "refused this request: an empty reply"))
 882 |                  continue
 883 | +            self._note(role, b, True)                  # ruling 87: a Heimdall family answered inside its deadline
 884 |              recorded = ""
 885 |              if path and isinstance(text, str) and text.strip():
 886 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 887 | @@ -939,8 +1232,11 @@ class Router:
 888 |                                      "text": text,
 889 |                                      "usage": usage, "usd": usd, "seconds": round(secs, 2)})
 890 |                  recorded = path
 891 | -            return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 892 | -                         recorded)
 893 | +            out = Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 894 | +                        recorded)
 895 | +            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 896 | +                self._shadow_ask(role, prompt, max_tokens, seed, system, out)     # ruling 86: asked, never deciding
 897 | +            return out
 898 |          if self.replay:
 899 |              raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
 900 |          raise ProviderError(f"{role}: every back-end unavailable: {tried}")
 901 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 902 | index 74013a1..b034586 100644
 903 | --- a/tests/package/proof_ledger.py
 904 | +++ b/tests/package/proof_ledger.py
 905 | @@ -56,6 +56,8 @@ sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 906 |  sys.path.insert(0, HERE)
 907 |  import eligibility as E  # noqa: E402
 908 |  import candidates as CA  # noqa: E402
 909 | +import heimdall_health as HH  # noqa: E402
 910 | +import shadow86 as SH  # noqa: E402
 911 |  import ledger_build as LB  # noqa: E402
 912 |  import moments as M  # noqa: E402
 913 |  import package as PK  # noqa: E402
 914 | @@ -69,6 +71,7 @@ import lock_precheck as LP  # noqa: E402
 915 |  
 916 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 917 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 918 | +STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
 919 |  
 920 |  
 921 |  def delivered_pins(paths):
 922 | @@ -108,6 +111,8 @@ def main(argv=None):
 923 |                      help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
 924 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 925 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 926 | +    ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
 927 | +                    help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
 928 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 929 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
 930 |                           "record (its tried[N]; default the first that passed), as it was judged")
 931 | @@ -183,8 +188,17 @@ def main(argv=None):
 932 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 933 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 934 |                    f, indent=1, default=str)
 935 | +    rt = json.load(open(P.CONFIG)).get("routing") or {}
 936 | +    routing = a.routing or rt.get("mode") or "today"
 937 | +    shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 938 | +    if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 939 | +        shadow = rt.get("shadow") or None
 940 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 941 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(), deadline_log=PL.DEADLINE_LOG)
 942 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 943 | +                      routing=routing, shadow=shadow, shadow_log=os.path.join(out_dir, "SHADOW86.jsonl"),
 944 | +                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD)    # ruling 87
 945 | +    say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 946 | +        + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 947 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 948 |      if spent0 >= PL.LY_STOP_USD:
 949 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 950 | @@ -333,8 +347,14 @@ def main(argv=None):
 951 |                          "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
 952 |      say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
 953 |          f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
 954 | +    res["routing"] = router.routing                # RULING 85: which routing decided this build
 955 | +    res["mode_at_end"] = router.mode()             # RULING 87: plan_b when Heimdall was down at the end
 956 | +    if router.shadow:                              # RULING 86: every shadow answer in (the pin, if any, is already
 957 | +        left = router.shadow_wait(900.0)           # written and logged above), then the side-by-side
 958 | +        res["shadow86"] = SH.report(out_dir, res, missing=left)
 959 | +        say(f"  SHADOW (ruling 86): {res['shadow86'].get('summary')}")
 960 |      try:                                         # the record is written whatever the ledger says (audit 0707 C1)
 961 | -        after = round(router.spent(), 4)
 962 | +        after = round(router.spent(), 4)         # (after the shadows: their spend is in it)
 963 |      except Exception as e:                       # noqa: BLE001
 964 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 965 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 966 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 967 | index dc5fe4a..702160b 100644
 968 | --- a/tests/package/proof_ly.py
 969 | +++ b/tests/package/proof_ly.py
 970 | @@ -64,14 +64,34 @@ WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b",
 971 |  SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
 972 |  
 973 |  
 974 | -def chains():
 975 | -    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
 976 | +def chains(routing=None):
 977 | +    """Every role's chain for the routing without the frozen legs; the writer = two Heimdall families, then Grok.
 978 | +    RULING 85: routing "today" (the chains under roles) or "heimdall_first" (model_providers.json routing.heimdall_first,
 979 | +    Grok last); default: the config's routing.mode."""
 980 |      cfg = json.load(open(P.CONFIG))
 981 | -    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
 982 | +    rt = cfg.get("routing") or {}
 983 | +    routing = routing or rt.get("mode") or "today"
 984 | +    if routing not in P.ROUTINGS:
 985 | +        raise ValueError(f"routing must be one of {P.ROUTINGS}, not {routing!r}")
 986 | +    routed = rt.get(routing) or {}
 987 | +    out = {r: [b for b in ((routed.get(r) if routing != "today" else None) or v["chain"]) if not b.startswith(FROZEN)]
 988 | +           for r, v in cfg["roles"].items()}
 989 | +    for k, ch in routed.items():                 # RULING 88: a verdict type's own list ("<role>:<kind>")
 990 | +        if ":" in k and isinstance(ch, list):
 991 | +            out[k] = [b for b in ch if not b.startswith(FROZEN)]
 992 |      out["angle_write"] = list(WRITERS)
 993 |      return out
 994 |  
 995 |  
 996 | +def plan_b_chains():
 997 | +    """RULING 87: the Plan B chains (model_providers.json routing.plan_b): Grok mainly, then any other outside key that
 998 | +    answers. OpenAI and Anthropic stay in (they are tried, never assumed: an account without credit is Unavailable at
 999 | +    its first call and down for the run); only GPU0's local model is out (never this builder's)."""
1000 | +    cfg = json.load(open(P.CONFIG))
1001 | +    return {r: [b for b in ch if not b.startswith(("local:", "openai_stt:"))]
1002 | +            for r, ch in ((cfg.get("routing") or {}).get("plan_b") or {}).items()}
1003 | +
1004 | +
1005 |  def ledger():
1006 |      try:
1007 |          d = json.load(open(SPEND))
1008 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
1009 | index 99f713c..ea67906 100644
1010 | --- a/tests/package/test_ledger_build.py
1011 | +++ b/tests/package/test_ledger_build.py
1012 | @@ -826,5 +826,63 @@ class TestDriverRefuses(unittest.TestCase):
1013 |                  self.assertIn("overlaps a delivered moment", why["m1"])
1014 |  
1015 |  
1016 | +
1017 | +class TestRuling85NoXai(unittest.TestCase):
1018 | +    """RULINGS 85 + 88 (22:15 Nov 13), on the real config and the real Router's skip rule (no model is called):
1019 | +    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type but
1020 | +    one still has a Heimdall family off the writer, and step A's two verdicts come from two families. The one gap:
1021 | +    coherence keeps Grok with deepseek alone behind it (88 (d): glm out; (e): qwen never decides it), so when deepseek
1022 | +    writes and xAI is down, coherence has no family and the package fails closed."""
1023 | +
1024 | +    @staticmethod
1025 | +    def pl():
1026 | +        sys.path.insert(0, HERE)
1027 | +        import proof_ly as PL
1028 | +        return PL
1029 | +
1030 | +    def pick(self, r, role, av=(), af=(), am=(), kind=None):
1031 | +        PL = self.pl()
1032 | +        for name in r.chain(role, kind):
1033 | +            b = r.backends.get(name)
1034 | +            if b is not None and r._skip(name, b, set(av), set(am), set(af)) is None and not \
1035 | +                    name.startswith(PL.FROZEN):
1036 | +                return name
1037 | +        return None
1038 | +
1039 | +    def test_ruling_88s_lists_and_xai_answering_nothing(self):
1040 | +        PL = self.pl()
1041 | +        X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
1042 | +                       "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
1043 | +        ch = PL.chains("heimdall_first")
1044 | +        self.assertEqual(ch["fidelity_verdict"], [Q, G, X])                       # (a): Heimdall, Grok last
1045 | +        self.assertEqual(ch["exclusion_verdict"], [G, Q, X])
1046 | +        self.assertEqual(ch["context_verdict:step_a_first"], [Q, G, DS, X])        # (c): Heimdall first
1047 | +        self.assertEqual(ch["context_verdict:step_a_second"][0], X)               # (c): Grok confirms
1048 | +        self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
1049 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # (d) / (e): no glm, no qwen
1050 | +        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, Q, DS])         # (d): no glm
1051 | +        today = PL.chains("today")                                                 # (d) and (e) hold today too
1052 | +        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
1053 | +        r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
1054 | +        for n in [n for n in r.backends if n.startswith("xai")]:
1055 | +            r.down[n] = "xAI answers nothing (the test)"
1056 | +        w = r.backends[DS]                                                         # the writer
1057 | +        got = {(role, kind): self.pick(r, role, {w.vendor}, {w.family}, kind=kind) for role, kind in (
1058 | +            ("fidelity_verdict", None), ("exclusion_verdict", None), ("speaker_verdict", None),
1059 | +            ("viewer_takeaway", None), ("context_verdict", "step_c"), ("coherence_verdict", "hook"),
1060 | +            ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
1061 | +        self.assertEqual(got, {("fidelity_verdict", None): Q, ("exclusion_verdict", None): G,
1062 | +                               ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
1063 | +                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
1064 | +                               ("coherence_verdict", "clips_alone"): Q,
1065 | +                               ("coherence_verdict", "coherence"): None})          # THE GAP (fails closed)
1066 | +        first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
1067 | +        fb = r.backends[first]
1068 | +        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
1069 | +        self.assertEqual((first, second), (Q, G))                                  # two Heimdall families, Grok down
1070 | +        r.down.clear()
1071 | +        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
1072 | +        self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
1073 | +
1074 |  if __name__ == "__main__":
1075 |      unittest.main()
1076 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
1077 | new file mode 100644
1078 | index 0000000..e4fab6c
1079 | --- /dev/null
1080 | +++ b/tests/providers/test_heimdall_health.py
1081 | @@ -0,0 +1,259 @@
1082 | +#!/usr/bin/env python3
1083 | +"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE (pipeline/heimdall_health.py and its use in
1084 | +providers.Router). Offline: a temporary state file, the test's own clock, fake back-ends."""
1085 | +import json
1086 | +import os
1087 | +import sys
1088 | +import tempfile
1089 | +import unittest
1090 | +from datetime import datetime, timedelta, timezone
1091 | +
1092 | +HERE = os.path.dirname(os.path.abspath(__file__))
1093 | +REPO = os.path.dirname(os.path.dirname(HERE))
1094 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1095 | +sys.path.insert(0, HERE)
1096 | +import heimdall_health as HH  # noqa: E402
1097 | +import providers as P  # noqa: E402
1098 | +from test_providers import Fake  # noqa: E402
1099 | +
1100 | +T0 = datetime(2026, 11, 14, 2, 0, tzinfo=timezone.utc)
1101 | +
1102 | +
1103 | +class TestHealth(unittest.TestCase):
1104 | +    def setUp(self):
1105 | +        HH._SEEN.clear()
1106 | +        self.d = tempfile.TemporaryDirectory()
1107 | +        self.state = os.path.join(self.d.name, "HEALTH.json")
1108 | +        self.ev = os.path.join(self.d.name, "DEADLINES.jsonl")
1109 | +        self.md = os.path.join(self.d.name, "STATE.md")
1110 | +        with open(self.md, "w") as f:
1111 | +            f.write("21:00 ET: line one as it was.\n\n## a section\n")
1112 | +
1113 | +    def tearDown(self):
1114 | +        self.d.cleanup()
1115 | +
1116 | +    def kw(self, t):
1117 | +        return {"path": self.state, "now": t, "evidence": self.ev, "state_md": self.md}
1118 | +
1119 | +    def test_fifteen_minutes_with_no_family_answering_is_plan_b_and_every_switch_is_on_record(self):
1120 | +        self.assertEqual(HH.note(False, **self.kw(T0)), "heimdall_first")
1121 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=14, seconds=59))), "heimdall_first")
1122 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=15))), "plan_b")
1123 | +        st = json.load(open(self.state))
1124 | +        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b"])
1125 | +        with open(self.ev) as f:
1126 | +            self.assertEqual([json.loads(x)["kind"] for x in f], ["switch"])
1127 | +        first = open(self.md).read().split("\n")[0]
1128 | +        self.assertTrue(first.endswith("| 21:00 ET: line one as it was."), first)     # one physical line, prepended
1129 | +        self.assertIn("ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED", first)
1130 | +
1131 | +    def test_one_answer_stops_the_clock(self):
1132 | +        HH.note(False, **self.kw(T0))
1133 | +        HH.note(True, **self.kw(T0 + timedelta(minutes=10)))           # any family answering: not down
1134 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=20))), "heimdall_first")
1135 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=34))), "heimdall_first")
1136 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=35))), "plan_b")   # idle: the clock still runs
1137 | +
1138 | +    def test_the_probe_every_2_minutes_and_back_after_3_answers_in_a_row(self):
1139 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
1140 | +        self.assertFalse(HH.probe_due(self.state, T0))                  # healthy: no probe
1141 | +        HH.note(False, **k(0))
1142 | +        self.assertTrue(HH.probe_due(self.state, T0))
1143 | +        HH.note(False, **k(15))                                          # down
1144 | +        self.assertEqual(HH.probe_result(True, **k(16)), "plan_b")
1145 | +        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=17)))      # 2 minutes apart
1146 | +        self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=18)))
1147 | +        self.assertEqual(HH.probe_result(False, **k(18)), "plan_b")      # a miss resets the streak
1148 | +        self.assertEqual(HH.probe_result(True, **k(20)), "plan_b")
1149 | +        self.assertEqual(HH.probe_result(True, **k(22)), "plan_b")
1150 | +        self.assertEqual(HH.probe_result(True, **k(24)), "heimdall_first")
1151 | +        st = json.load(open(self.state))
1152 | +        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b", "heimdall_first"])
1153 | +        self.assertIsNone(st["failing_since_utc"])
1154 | +        self.assertIn("BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW)",
1155 | +                      open(self.md).read().split("\n")[0])
1156 | +
1157 | +    def test_a_drill_is_recorded_never_counted_and_answers_write_once_per_heartbeat(self):
1158 | +        HH._SEEN.clear()
1159 | +        for m in range(0, 40, 5):                                        # 40 minutes of drill failures
1160 | +            self.assertEqual(HH.note(False, drill=True, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
1161 | +        st = json.load(open(self.state))
1162 | +        self.assertEqual((st["drills"], st["failing_since_utc"], st["notes"]), (8, None, 0))
1163 | +        HH.note(True, **self.kw(T0))
1164 | +        HH.note(True, **self.kw(T0 + timedelta(seconds=5)))              # inside the heartbeat: not written
1165 | +        self.assertEqual(json.load(open(self.state))["notes"], 1)
1166 | +        HH.note(False, **self.kw(T0 + timedelta(seconds=6)))             # a failure is always written
1167 | +        HH.note(True, **self.kw(T0 + timedelta(seconds=7)))              # and the next answer too
1168 | +        st = json.load(open(self.state))
1169 | +        self.assertEqual((st["notes"], st["failing_since_utc"]), (3, None))
1170 | +        HH._SEEN.clear()
1171 | +
1172 | +    def test_an_unreadable_state_is_never_guessed(self):
1173 | +        with open(self.state, "w") as f:
1174 | +            f.write("{ broken")
1175 | +        for fn in (lambda: HH.note(True, **self.kw(T0)), lambda: HH.mode(**self.kw(T0))):
1176 | +            with self.assertRaises(HH.HealthUnreadable):
1177 | +                fn()
1178 | +        self.assertEqual(open(self.state).read(), "{ broken")
1179 | +
1180 | +
1181 | +class TestRouterPlanB(unittest.TestCase):
1182 | +    """providers.Router: a Heimdall verdict or writer call's outcome is noted; in plan_b the roles of plan_b_chains run
1183 | +    on them at once (Grok first)."""
1184 | +
1185 | +    def setUp(self):
1186 | +        self.d = tempfile.TemporaryDirectory()
1187 | +        self.cfg = os.path.join(self.d.name, "cfg.json")
1188 | +        json.dump({"schema": "pp.providers/1",
1189 | +                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
1190 | +                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek",
1191 | +                                                      "family": "deepseek"}},
1192 | +                   "roles": {"coherence_verdict": {"chain": ["heimdall:deepseek", "xai:grok"]},
1193 | +                             "mine": {"chain": ["heimdall:deepseek"]}},
1194 | +                   "routing": {"mode": "today", "verdict_roles": ["coherence_verdict"]}}, open(self.cfg, "w"))
1195 | +        self.state = os.path.join(self.d.name, "HEALTH.json")
1196 | +
1197 | +    def tearDown(self):
1198 | +        self.d.cleanup()
1199 | +
1200 | +    def router(self):
1201 | +        r = P.Router(self.cfg, env_path="/nonexistent", health=self.state,
1202 | +                     plan_b_chains={"coherence_verdict": ["xai:grok"]})
1203 | +        h = P.HeimdallBackend("heimdall:deepseek", {"model": "deepseek", "family": "deepseek"}, "/nonexistent")
1204 | +        h.complete = lambda *a, **k: ("d", {"in": 1, "out": 1}, 0.01)
1205 | +        r.backends = {"xai:grok": Fake("xai:grok", "xai", answer="x", family="grok"), "heimdall:deepseek": h}
1206 | +        r.start_probe = lambda *a, **k: None                              # no thread in a unit test
1207 | +        return r
1208 | +
1209 | +    def test_outcomes_are_noted_and_plan_b_takes_the_chain(self):
1210 | +        r = self.router()
1211 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "heimdall:deepseek")
1212 | +        st = json.load(open(self.state))
1213 | +        self.assertIsNotNone(st["last_answer_utc"])
1214 | +        self.assertEqual(st["notes"], 1)
1215 | +        r.call("mine", "p")                                               # not a verdict or a write: not noted
1216 | +        self.assertEqual(json.load(open(self.state))["notes"], 1)
1217 | +        HH.note(False, self.state, now=datetime.now(timezone.utc) - timedelta(minutes=16))
1218 | +        HH.note(False, self.state)                                        # 16 minutes with no answer: plan_b
1219 | +        self.assertEqual(r.mode(), "plan_b")
1220 | +        self.assertEqual(r.chain("coherence_verdict"), ["xai:grok"])
1221 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")   # the whole pin stage, at once
1222 | +        self.assertEqual(r.chain("mine"), ["heimdall:deepseek"])          # a role Plan B does not name: as is
1223 | +
1224 | +    def test_a_probe_round_reaches_a_family_marked_down_and_restores_the_mark_when_it_fails(self):
1225 | +        r = self.router()
1226 | +        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
1227 | +        self.assertTrue(r.probe_once(["heimdall:deepseek"]))             # it answers now: the mark is lifted
1228 | +        self.assertNotIn("heimdall:deepseek", r.down)
1229 | +
1230 | +        def down(*a, **k):
1231 | +            raise P.Unavailable("HTTP 503")
1232 | +        r.backends["heimdall:deepseek"].complete = down
1233 | +        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
1234 | +        self.assertFalse(r.probe_once(["heimdall:deepseek"]))
1235 | +        self.assertIn("heimdall:deepseek", r.down)                       # still down: marked as before
1236 | +        self.assertFalse(os.path.exists(os.path.join(self.d.name, "rec")))   # a probe is never recorded
1237 | +
1238 | +    def test_a_failing_heimdall_call_is_noted_as_not_answered(self):
1239 | +        r = self.router()
1240 | +
1241 | +        def down(*a, **k):
1242 | +            raise P.Unavailable("HTTP 503")
1243 | +        r.backends["heimdall:deepseek"].complete = down
1244 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")    # ruling 82's chain moved on
1245 | +        st = json.load(open(self.state))
1246 | +        self.assertIsNotNone(st["failing_since_utc"])
1247 | +        self.assertIsNone(st["last_answer_utc"])
1248 | +
1249 | +
1250 | +
1251 | +class TestLocalJudge(unittest.TestCase):
1252 | +    """RULING 87: the integrator's GPU0 judge (Plan B, one outside family): a request file in this worktree, the answer
1253 | +    read from its results; an error or no answer in time is no verdict; the wait outlasts ruling 82's 120 s."""
1254 | +
1255 | +    def setUp(self):
1256 | +        self.d = tempfile.TemporaryDirectory()
1257 | +        self.req, self.res = os.path.join(self.d.name, "req"), os.path.join(self.d.name, "res")
1258 | +        os.makedirs(self.res)
1259 | +        self.b = P.LocalJudgeBackend("local_judge:gemma3:27b", {"model": "gemma3:27b", "family": "gemma",
1260 | +                                                                "deadline_floor_s": 2400}, "/nonexistent")
1261 | +        self.b.REQUESTS, self.b.RESULTS, self.b.POLL_S = self.req, self.res, 0.05
1262 | +
1263 | +    def tearDown(self):
1264 | +        self.d.cleanup()
1265 | +
1266 | +    def answer_when_asked(self, body):
1267 | +        import threading
1268 | +        import time as _t
1269 | +
1270 | +        def run():                                   # answers the one request that has no answer yet
1271 | +            for _ in range(500):
1272 | +                for n in sorted(os.listdir(self.req)) if os.path.isdir(self.req) else []:
1273 | +                    if not n.endswith(".json"):
1274 | +                        continue
1275 | +                    rid = n[:-len(".json")]
1276 | +                    rq = json.load(open(os.path.join(self.req, n)))
1277 | +                    import hashlib                       # the integrator's prompt_id
1278 | +                    pid = hashlib.sha256(json.dumps([rq["prompt"], rq["max_tokens"], rq["seed"]]).encode()) \
1279 | +                        .hexdigest()[:20]
1280 | +                    out = os.path.join(self.res, f"{rid}.{pid}.json")
1281 | +                    if not os.path.exists(out):
1282 | +                        with open(out, "w") as f:
1283 | +                            json.dump(dict(body, request_id=rid, prompt_id=pid), f)
1284 | +                        return
1285 | +                _t.sleep(0.02)
1286 | +        threading.Thread(target=run, daemon=True).start()
1287 | +
1288 | +    def test_a_request_is_written_and_its_answer_read(self):
1289 | +        self.answer_when_asked({"family": "step_a", "text": '{"excerpts": []}', "error": None})
1290 | +        text, usage, secs = self.b.complete("the step A prompt", 4000, 7)
1291 | +        self.assertEqual((text, usage["in"], usage["out"]), ('{"excerpts": []}', 0, 0))
1292 | +        stray = os.path.join(self.res, "pp-selectid.x.0000.json")         # another answer's file is never read
1293 | +        json.dump({"request_id": "other", "text": "{}"}, open(stray, "w"))
1294 | +        (name,) = os.listdir(self.req)
1295 | +        rq = json.load(open(os.path.join(self.req, name)))
1296 | +        self.assertEqual({k: rq[k] for k in ("family", "prompt", "max_tokens", "seed")},
1297 | +                         {"family": "step_a", "prompt": "the step A prompt", "max_tokens": 4000, "seed": 7})
1298 | +        self.assertTrue(self.b.free())
1299 | +
1300 | +    def test_an_error_or_no_answer_is_no_verdict(self):
1301 | +        self.answer_when_asked({"family": "step_a", "text": "", "error": "GPU0 busy"})
1302 | +        with self.assertRaises(P.RequestRejected):
1303 | +            self.b.complete("p", 100, 7)
1304 | +        self.b.WAIT_S = 0.2
1305 | +        with self.assertRaises(P.Unavailable):
1306 | +            self.b.complete("q", 100, 7)
1307 | +        with self.assertRaises(P.RequestRejected):
1308 | +            self.b.complete("q", 100, 7, system="no system message")
1309 | +
1310 | +    def test_the_wait_outlasts_the_120_s_deadline_and_state_line_1_says_so_once(self):
1311 | +        cfg = os.path.join(self.d.name, "cfg.json")
1312 | +        json.dump({"schema": "pp.providers/1",
1313 | +                   "backends": {"local_judge:gemma3:27b": {"vendor": "local_judge", "model": "gemma3:27b",
1314 | +                                                           "family": "gemma", "deadline_floor_s": 2400}},
1315 | +                   "roles": {"context_verdict": {"chain": ["local_judge:gemma3:27b"]}}}, open(cfg, "w"))
1316 | +        md = os.path.join(self.d.name, "STATE.md")
1317 | +        open(md, "w").write("21:50 ET: line one.\n")
1318 | +        r = P.Router(cfg, env_path="/nonexistent", state_md=md)
1319 | +        r.backends["local_judge:gemma3:27b"] = self.b
1320 | +        seen = {}
1321 | +        orig = P._within
1322 | +
1323 | +        def spy(seconds, fn, **kw):
1324 | +            seen["deadline"] = seconds
1325 | +            return orig(seconds, fn, **kw)
1326 | +        P._within = spy
1327 | +        try:
1328 | +            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
1329 | +            r.call("context_verdict", "p", 100, 7, deadline_s=120.0)
1330 | +            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
1331 | +            r.call("context_verdict", "p2", 100, 7, deadline_s=120.0)
1332 | +        finally:
1333 | +            P._within = orig
1334 | +        self.assertEqual(seen["deadline"], 2400.0)
1335 | +        first = open(md).read().split("\n")[0]
1336 | +        self.assertEqual(first.count("PLAN B WITH ONE OUTSIDE FAMILY"), 1)
1337 | +        self.assertTrue(first.endswith("| 21:50 ET: line one."))
1338 | +
1339 | +if __name__ == "__main__":
1340 | +    unittest.main()
1341 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1342 | index b7498ef..7d9e0a6 100644
1343 | --- a/tests/providers/test_providers.py
1344 | +++ b/tests/providers/test_providers.py
1345 | @@ -481,5 +481,196 @@ class TestRouter(unittest.TestCase):
1346 |              self.assertEqual(meta["backend"], "xai:z")
1347 |  
1348 |  
1349 | +
1350 | +class TestRuling85Routing(unittest.TestCase):
1351 | +    """RULING 85 (21:15 Nov 13): Heimdall first for every verdict, Grok last, behind a switch; the two-family rule kept
1352 | +    INSIDE Heimdall (each family its own maker); the 20:33 order: ruling 82's 120 s on Heimdall for every verdict role,
1353 | +    and an answer out of contract moves on (providers.call_parsed)."""
1354 | +
1355 | +    def cfg(self, d, mode="today"):
1356 | +        p = os.path.join(d, "cfg.json")
1357 | +        json.dump({"schema": "pp.providers/1",
1358 | +                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
1359 | +                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek", "family": "deepseek"},
1360 | +                                "heimdall:glm": {"vendor": "heimdall", "model": "glm", "family": "glm"},
1361 | +                                "heimdall:qwen": {"vendor": "heimdall", "model": "qwen", "family": "qwen"}},
1362 | +                   "roles": {"coherence_verdict": {"chain": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
1363 | +                                                             "heimdall:qwen"]},
1364 | +                             "mine": {"chain": ["heimdall:qwen", "xai:grok"]}},
1365 | +                   "routing": {"mode": mode, "verdict_roles": ["coherence_verdict"],
1366 | +                               "verdict_deadline_s": {"heimdall": 120},
1367 | +                               "heimdall_first": {"coherence_verdict": ["heimdall:deepseek", "heimdall:glm",
1368 | +                                                                        "heimdall:qwen", "xai:grok"]}}}, open(p, "w"))
1369 | +        return p
1370 | +
1371 | +    def fakes(self):
1372 | +        return [Fake("xai:grok", "xai", answer="x", family="grok"),
1373 | +                Fake("heimdall:deepseek", "heimdall", answer="d", family="deepseek"),
1374 | +                Fake("heimdall:glm", "heimdall", answer="g", family="glm"),
1375 | +                Fake("heimdall:qwen", "heimdall", answer="q", family="qwen")]
1376 | +
1377 | +    def router(self, d, mode=None, cfg_mode="today"):
1378 | +        r = P.Router(self.cfg(d, cfg_mode), env_path="/nonexistent", routing=mode)
1379 | +        fs = self.fakes()
1380 | +        if r.routing == "heimdall_first":          # the router's own init re-keyed its real back-ends; fakes too
1381 | +            for b in fs:
1382 | +                if b.vendor == "heimdall":
1383 | +                    b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1384 | +        r.backends = {b.name: b for b in fs}
1385 | +        return r
1386 | +
1387 | +    def test_today_is_unchanged_and_heimdall_first_puts_grok_last(self):
1388 | +        import tempfile
1389 | +        with tempfile.TemporaryDirectory() as d:
1390 | +            t = self.router(d)
1391 | +            self.assertEqual(t.routing, "today")
1392 | +            self.assertEqual(t.call("coherence_verdict", "p").backend, "xai:grok")
1393 | +            self.assertEqual(t.chain("mine"), ["heimdall:qwen", "xai:grok"])
1394 | +            h = self.router(d, "heimdall_first")
1395 | +            self.assertEqual(h.chain("coherence_verdict"), ["heimdall:deepseek", "heimdall:glm", "heimdall:qwen",
1396 | +                                                            "xai:grok"])
1397 | +            self.assertEqual(h.chain("mine"), ["heimdall:qwen", "xai:grok"])   # a role the routing names not: as is
1398 | +            self.assertEqual(h.call("coherence_verdict", "p").backend, "heimdall:deepseek")
1399 | +            self.assertEqual(self.router(d, cfg_mode="heimdall_first").routing, "heimdall_first")  # the config's mode
1400 | +            with self.assertRaises(ValueError):
1401 | +                P.Router(self.cfg(d), env_path="/nonexistent", routing="grok_only")
1402 | +
1403 | +    def test_the_two_family_rule_inside_heimdall(self):
1404 | +        """A Heimdall writer (deepseek) is judged by another Heimdall family (glm) under heimdall_first; today the
1405 | +        vendor rule leaves only Grok; the router's own init re-keys a real Heimdall back-end's vendor."""
1406 | +        import tempfile
1407 | +        with tempfile.TemporaryDirectory() as d:
1408 | +            h = self.router(d, "heimdall_first")
1409 | +            r = h.call("coherence_verdict", "p", avoid_vendor={"heimdall/deepseek"}, avoid_family={"deepseek"})
1410 | +            self.assertEqual((r.backend, r.vendor), ("heimdall:glm", "heimdall/glm"))
1411 | +            t = self.router(d)
1412 | +            r = t.call("coherence_verdict", "p", avoid_vendor={"heimdall"}, avoid_family={"deepseek"})
1413 | +            self.assertEqual(r.backend, "xai:grok")
1414 | +            real = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first")
1415 | +            b = real.backends["heimdall:glm"]
1416 | +            self.assertEqual((b.vendor, P.gateway(b), real.backends["xai:grok"].vendor), ("heimdall/glm", "heimdall",
1417 | +                                                                                           "xai"))
1418 | +            self.assertEqual(P.gateway(P.Router(self.cfg(d), env_path="/nonexistent").backends["heimdall:glm"]),
1419 | +                             "heimdall")
1420 | +
1421 | +    def test_a_verdict_role_gets_120_s_on_heimdall_only(self):
1422 | +        import tempfile
1423 | +        with tempfile.TemporaryDirectory() as d:
1424 | +            h = self.router(d, "heimdall_first")
1425 | +            self.assertEqual(h.role_deadline("coherence_verdict", h.backends["heimdall:glm"]), 120.0)
1426 | +            self.assertIsNone(h.role_deadline("coherence_verdict", h.backends["xai:grok"]))
1427 | +            self.assertIsNone(h.role_deadline("mine", h.backends["heimdall:qwen"]))
1428 | +            slow = Slow("heimdall:deepseek", "heimdall/deepseek", "d", delay=0.6, family="deepseek")
1429 | +            slow.gateway = "heimdall"
1430 | +            h.backends["heimdall:deepseek"] = slow
1431 | +            h.config["routing"]["verdict_deadline_s"] = {"heimdall": 0.1}
1432 | +            r = h.call("coherence_verdict", "p")                 # deepseek is abandoned at 0.1 s: glm answers
1433 | +            self.assertEqual(r.backend, "heimdall:glm")
1434 | +            self.assertIn("abandoned at the deadline", r.tried[0][1])
1435 | +
1436 | +    def test_the_real_config_bounds_today_as_ruled_and_heimdall_first_everywhere(self):
1437 | +        """The 20:33 order bounds fidelity, coherence, step B, speaker and exclusion (120 s on Heimdall); step A's
1438 | +        first screen and step C stay unbounded today (8 clips a call); under heimdall_first every verdict is bounded."""
1439 | +        today, hf = P.Router(env_path="/nonexistent"), P.Router(env_path="/nonexistent", routing="heimdall_first")
1440 | +        ds, xs = "heimdall:deepseek/deepseek-v4.1-flash", "xai:grok-4.20-0309-reasoning"
1441 | +        for role in ("fidelity_verdict", "coherence_verdict", "viewer_takeaway", "speaker_verdict",
1442 | +                     "exclusion_verdict"):
1443 | +            self.assertEqual((today.role_deadline(role, today.backends[ds]), hf.role_deadline(role, hf.backends[ds])),
1444 | +                             (120.0, 120.0), role)
1445 | +            self.assertIsNone(today.role_deadline(role, today.backends[xs]))
1446 | +        self.assertIsNone(today.role_deadline("context_verdict", today.backends[ds]))
1447 | +        self.assertEqual(hf.role_deadline("context_verdict", hf.backends[ds]), 120.0)
1448 | +        self.assertIsNone(hf.role_deadline("angle_write", hf.backends[ds]))   # the writer keeps ruling 5's 300 s
1449 | +
1450 | +    def test_call_parsed_moves_on_past_an_answer_out_of_contract(self):
1451 | +        import tempfile
1452 | +        with tempfile.TemporaryDirectory() as d:
1453 | +            h = self.router(d, "heimdall_first")
1454 | +            h.backends["heimdall:deepseek"].answer = "not json"
1455 | +            r, v = P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1, "g": 2}[t])
1456 | +            self.assertEqual((r.backend, v), ("heimdall:glm", 2))
1457 | +            for b in h.backends.values():
1458 | +                b.answer = "bad"
1459 | +            with self.assertRaises(P.ProviderError) as e:
1460 | +                P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1}[t])
1461 | +            self.assertIn("answers out of contract", str(e.exception))
1462 | +            self.assertEqual({n: b.calls for n, b in h.backends.items()},          # the second run asks each model
1463 | +                             {"heimdall:deepseek": 2, "heimdall:glm": 2, "heimdall:qwen": 1, "xai:grok": 1})  # once
1464 | +
1465 | +    def test_the_writes_keep_their_gateway(self):
1466 | +        """package.build: every write stays on the angle's GATEWAY, so a Heimdall write may still fail over
1467 | +        deepseek -> qwen under heimdall_first, and Grok never writes there."""
1468 | +        import tempfile
1469 | +        with tempfile.TemporaryDirectory() as d:
1470 | +            h = self.router(d, "heimdall_first")
1471 | +            writers = ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
1472 | +            avoid = {P.gateway(h.backends[n]) for n in writers} - {P.gateway(h.backends["heimdall:deepseek"])}
1473 | +            self.assertEqual(avoid, {"xai"})
1474 | +            self.assertFalse({h.backends["heimdall:qwen"].vendor} & avoid)
1475 | +
1476 | +
1477 | +class TestRuling86Shadow(TestRuling85Routing):
1478 | +    """RULING 86 (21:18 Nov 13): the first pins under Heimdall-first are judged twice: Heimdall's families decide, and
1479 | +    Grok is asked the same prompt in SHADOW (recorded to shadow_log, never deciding)."""
1480 | +
1481 | +    def shadow_router(self, d, **kw):
1482 | +        r = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first", shadow={"*": "xai:grok"},
1483 | +                     shadow_log=os.path.join(d, "SHADOW.jsonl"), **kw)
1484 | +        fs = self.fakes()
1485 | +        for b in fs:
1486 | +            if b.vendor == "heimdall":
1487 | +                b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1488 | +        r.backends = {b.name: b for b in fs}
1489 | +        return r
1490 | +
1491 | +    def lines(self, d):
1492 | +        p = os.path.join(d, "SHADOW.jsonl")
1493 | +        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []
1494 | +
1495 | +    def test_a_heimdall_verdict_is_asked_of_grok_in_shadow_and_grok_never_decides(self):
1496 | +        import tempfile
1497 | +        with tempfile.TemporaryDirectory() as d:
1498 | +            r = self.shadow_router(d)
1499 | +            rep = r.call("coherence_verdict", "the prompt", 500, 7)
1500 | +            self.assertEqual((rep.backend, rep.text), ("heimdall:deepseek", "d"))      # Heimdall decides
1501 | +            self.assertEqual(r.shadow_wait(5), 0)
1502 | +            got = self.lines(d)
1503 | +            self.assertEqual([(x["role"], x["prompt"], x["deciding"]["backend"], x["deciding"]["text"],
1504 | +                               x["shadow"]["backend"], x["shadow"]["text"]) for x in got],
1505 | +                             [("coherence_verdict", "the prompt", "heimdall:deepseek", "d", "xai:grok", "x")])
1506 | +            self.assertEqual(r.backends["xai:grok"].calls, 1)
1507 | +            r.call("mine", "p")                                   # not a verdict: no shadow
1508 | +            r.backends["heimdall:deepseek"].fail = "down"
1509 | +            r.backends["heimdall:glm"].fail = "down"
1510 | +            r.backends["heimdall:qwen"].fail = "down"
1511 | +            self.assertEqual(r.call("coherence_verdict", "q").backend, "xai:grok")   # Grok decided: nothing to shadow
1512 | +            self.assertEqual(r.shadow_wait(5), 0)
1513 | +            self.assertEqual(len(self.lines(d)), 1)
1514 | +
1515 | +    def test_a_shadow_that_fails_is_on_record_and_stops_nothing(self):
1516 | +        import tempfile
1517 | +        with tempfile.TemporaryDirectory() as d:
1518 | +            r = self.shadow_router(d)
1519 | +            r.backends["xai:grok"].fail = "xAI is down"
1520 | +            self.assertEqual(r.call("coherence_verdict", "p").text, "d")
1521 | +            self.assertEqual(r.shadow_wait(5), 0)
1522 | +            (x,) = self.lines(d)
1523 | +            self.assertIn("xAI is down", x["shadow"]["error"])
1524 | +
1525 | +    def test_a_recorded_verdict_is_shadowed_too_and_the_shadow_back_end_must_exist(self):
1526 | +        import tempfile
1527 | +        with tempfile.TemporaryDirectory() as d:
1528 | +            r = self.shadow_router(d, record_dir=os.path.join(d, "rec"))
1529 | +            r.call("coherence_verdict", "p")
1530 | +            r.shadow_wait(5)
1531 | +            r.call("coherence_verdict", "p")                      # served from its recording
1532 | +            r.shadow_wait(5)
1533 | +            got = self.lines(d)
1534 | +            self.assertEqual([x["deciding"]["cached"] for x in got], [False, True])
1535 | +            self.assertEqual([x["shadow"]["cached"] for x in got], [False, True])   # the shadow's own recording
1536 | +            self.assertEqual(r.backends["xai:grok"].calls, 1)
1537 | +            with self.assertRaises(ValueError):
1538 | +                P.Router(self.cfg(d), env_path="/nonexistent", shadow={"*": "xai:nope"})
1539 | +
1540 |  if __name__ == "__main__":
1541 |      unittest.main()
1542 | 
```

---

You are auditing PACKAGE A of a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). It
is the router, the Heimdall health state, the provider config and the build driver. Package B (the verdict call
sites, the shadow report and the replay driver) is audited separately. Only state what you can verify from the diff;
if uncertain, say so; do not guess.

Background (static):
- providers.Router.call(role, ...) tries the role's chain of back-ends in order. It skips a back-end that is:
  - on a vendor or family the caller avoids (law L-s: a verdict never comes from the writer's vendor or family);
  - a model the caller avoids;
  - marked down for the run.
  It moves on when a back-end is unavailable, refuses, misses its deadline, or answers empty. The chain spent:
  ProviderError (no verdict, never a pass).
- Each paid call reserves its upper bound on the spend ledger (ruling 48) and settles after. Ruling 83: a call
  abandoned at its deadline is booked at its prompt tokens; a late answer replaces that booking.
- Back-ends are: xAI Grok (vendor xai, family grok); Heimdall, a gateway to several model families (vendor heimdall:
  deepseek, glm, qwen, nemotron); Anthropic and OpenAI (out of credit); a local gemma3:27b on GPU0 (never this
  builder's).
- Every verdict today runs Grok FIRST: step A's first verdict, clips-alone, coherence, hook ratings, fidelity, step B,
  step C, speaker, exclusion, visual. Grok costs about ten times Heimdall per call, and the card behind it may be
  declined.

The orders (verbatim excerpts):
- 20:33 Nov 13: "Ruling 82's chain (deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s a call, an out-of-contract answer
  moves on, an outage is never a verdict) applies to every step that today has one Heimdall model as its only route
  when xAI is the writer or is down: the fidelity verdict, coherence / clips-alone / hook ratings, step B, the speaker
  and exclusion verdicts. The family rules stay: a verdict never comes from the family that wrote the line it judges,
  and step A's two verdicts are from two families."
- RULING 85 (21:15, locked 21:18): "HEIMDALL FIRST FOR EVERY VERDICT, GROK LAST. ... THE ROUTING I will rule from that
  table [the replay], but build it now behind a switch: each verdict type has an ordered list of model FAMILIES; the
  two-family rule (step A: two verdicts from two families; no verdict from the family that wrote the line) is
  satisfied INSIDE Heimdall wherever two Heimdall families both pass the replay for that type; Grok is the last entry
  of every list (used only when Heimdall's families are down or split), and the pipeline must complete a video with
  xAI answering nothing at all."
- RULING 86 (21:18): "The first pin sealed under Heimdall-first routing is judged TWICE: Heimdall's families decide
  (that is the pin), and Grok is asked the same prompts once in SHADOW (recorded, never deciding ...). I get the
  side-by-side per verdict ...: every decision where they differ, which was stricter, and whether the pin would have
  sealed under Grok. ... After three pins with no decision-changing difference, the shadow stops."
- RULING 87 (21:18): "PLAN B, THE FAIL-SAFE. Heimdall is 'down' when NO Heimdall family answers a verdict or writer
  call inside its deadline for 15 MINUTES running (a cheap health probe every 2 min while calls are failing; one model
  down is not 'down' ...). When down: switch the whole pin stage to PLAN B at once: Grok mainly, then any other outside
  key that answers (the Gemini key is fenced to this pipeline and may be used here; OpenAI and Anthropic when they have
  credit: probe, do not assume), keeping the two-family rule with whatever two families answer; if only ONE outside
  family answers, step A's second verdict is the local gemma3:27b on GPU0 through the integrator's judge service, and
  STATE line 1 says so. Return to Heimdall-first when its probe has answered 3 times in a row. Every switch ... is
  written to STATE line 1 in capitals with the time, and to the Heimdall evidence file. The same switch covers the
  miner and the writer ... Plan B's spend counts on the same ledger and the same cap ..."

- RULING 88 (22:15, from the replay's interim): "(a) fidelity and exclusion MOVE to Heimdall now ... (two Heimdall
  families, Grok last). (b) step C, hook rating: MOVE when the full table holds the interim numbers (98-100 %). (c) STEP A
  stays two families with Grok as one of them, but the ORDER changes: the Heimdall verdict is asked FIRST; a clip
  Heimdall refuses is refused and Grok is never asked; only a clip Heimdall passes goes to Grok to confirm. ... (d)
  clips-alone and coherence keep Grok until the table is complete; glm is out of those two (out-of-contract answers).
  (e) qwen failed two anchors: qwen is never the deciding family on coherence or step C."

The change (package A):
1. model_providers.json:
   - roles: the 20:33 chains. fidelity / coherence / speaker / exclusion gain glm and qwen after deepseek;
     viewer_takeaway (step B) gains deepseek and glm before qwen.
   - backends: google:gemini-2.5-pro (Plan B only; key GEMINI_API_KEY_MEDLEY, sent in a header; no vendor cost, so
     the estimate stands). local_judge:gemma3:27b (Plan B only; deadline_floor_s 2400).
   - RULING 88: Router.chain(role, kind) and call(..., kind): a verdict TYPE may have its own list "<role>:<kind>"
     (step_a_first, step_a_second, step_c, hook, clips_alone, coherence); the recordings stay keyed by role. Under
     heimdall_first: fidelity [qwen, glm, Grok]; exclusion [glm, qwen, Grok]; step_a_first [qwen, glm, deepseek, Grok];
     step_a_second [Grok, qwen, glm, deepseek]; step_c [Grok, glm, deepseek]; hook [Grok, qwen, deepseek, glm];
     clips_alone [Grok, qwen, deepseek]; coherence [Grok, deepseek]; speaker / step B [Grok, deepseek, glm, qwen].
     Under today: per-type lists only for (d)/(e): coherence [Grok, deepseek], clips_alone [Grok, deepseek, qwen],
     step_c [Grok, deepseek, glm]; every role keeps its chain.
   - "routing":
     - mode (today);
     - verdict_roles;
     - verdict_deadline_s {heimdall: 120};
     - today_unbounded [context_verdict]: today, step A's first screen and step C keep no deadline (their Heimdall
       fallback carries 8 clips a call; ruling 82 bounded only the second screen);
     - heimdall_first: deepseek, glm, qwen, then Grok, for every verdict role (the per-type order is set from the
       replay);
     - plan_b: Grok, Gemini, OpenAI, Anthropic; context_verdict also gets local_judge;
     - shadow: Grok (grok-4.7 for visual_check);
     - shadow_until_clean_pins: 3.
2. providers.py:
   - ROUTINGS. Router(routing=...): under heimdall_first, each Heimdall back-end's vendor becomes "heimdall/<family>"
     (gateway() keeps "heimdall"), so every existing vendor rule separates the families.
   - chain(role): the Plan B chain while the health state says plan_b, else the overrides, else the routing's list,
     else the role's chain.
   - role_deadline: 120 s on Heimdall for the verdict roles, minus today_unbounded under today.
   - call_parsed(router, ...): an answer out of contract is rejected and its model skipped; the chain spent is
     ProviderError; a skipped model answering again is ProviderError (never a loop).
   - The shadow: SHADOW_ROLES, _shadow_ask (a thread; role "shadow86:<role>" with its own recordings), shadow_wait.
   - Plan B: _note (each Heimdall verdict or writer call's outcome to heimdall_health); mode(); start_probe / probe_once
     (a family marked down is probed; its mark is lifted only if it answers); probes are never recorded or served from
     a recording.
   - GeminiBackend.
   - LocalJudgeBackend: the integrator's contract, a request file in this worktree, its answer from the integrator's
     results directory, up to 40 min; an error or no answer is no verdict. Its deadline floor overrides 120 s. Its first
     use is announced on STATE line 1.
   - The tripwire checks isinstance(HeimdallBackend), not the vendor string.
3. heimdall_health.py (new; shared with pp-ingest's watcher):
   - a state file under an flock;
   - note(answered): the 15-minute rule; a drill is recorded, never counted; an answer is written at most once per
     30 s per process while all is well, a failure always;
   - mode() applies the rule on the clock;
   - probe_due every 2 min while failing or in plan_b;
   - probe_result: 3 answers in a row in plan_b switch back;
   - every switch goes to the state, the evidence file and STATE line 1 (prepended, one physical line);
   - announce();
   - an unreadable state raises HealthUnreadable (never guessed).
4. proof_ly.py: chains(routing); plan_b_chains() (OpenAI / Anthropic kept: tried, never assumed).
   proof_ledger.py: --routing; the Router gets health, plan_b_chains and state_md; the shadow while the routing is
   heimdall_first and the clean streak is under 3; shadow_wait and the shadow report at the end; res["routing"] and
   res["mode_at_end"].
5. Tests:
   - test_providers: today unchanged; Grok last; the two-family rule inside Heimdall; 120 s on Heimdall only;
     call_parsed; the writer's gateway; the real config's deadline split; the shadow (asked, never deciding, failures
     recorded, recorded verdicts shadowed).
   - test_heimdall_health: 15 minutes; one answer stops the clock; probes; back after 3; switches on record; drills;
     the heartbeat; unreadable state; the router's Plan B chain; the probe and the down marks; the local judge.
   - test_ledger_build: the real config with xAI down and deepseek writing; every verdict role answers inside Heimdall
     off the writer; step A's two verdicts from two Heimdall families.

Design choices to check (say if you think any is wrong):
- The family-as-maker re-keying happens only under heimdall_first; today's behaviour is unchanged.
- A refused request (HTTP 400) counts as "not answered" for the health clock; any other family's answer stops it.
- In Plan B the writer is Grok first; with one outside family, verdicts other than step A have no second family and
  fail closed (the ruling names the local judge for step A only).
- The probe lifts a down mark only when the family answers.

Check, against the diff:
- that today's routing is unchanged except the 20:33 chains and their 120 s;
- that no verdict can come from the writer's family under either routing;
- that xAI answering nothing still completes every verdict under heimdall_first;
- the health state's concurrency and fail-closed behaviour;
- that a shadow can never decide or block;
- the Plan B switch and its return;
- spend: shadows, probes and Plan B calls all on the same ledger.

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

