# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1057
# Branch: pp-selectid
# Generated: 2026-11-14 10:58 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1057/C1_STEP.diff (564 lines)
```
   1 | diff --git a/pipeline/circuit_breaker.py b/pipeline/circuit_breaker.py
   2 | new file mode 100644
   3 | index 0000000..ac8aa15
   4 | --- /dev/null
   5 | +++ b/pipeline/circuit_breaker.py
   6 | @@ -0,0 +1,162 @@
   7 | +"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER. A model that misses its deadline MISSES_TO_OPEN (2)
   8 | +times in a row, or returns more than RUNAWAY_X (2) times its max_tokens, is SKIPPED by every list for OPEN_S (30
   9 | +minutes): the next family leads. After that, ONE real call may try it again (the trial, claimed under the lock); an
  10 | +answer closes the breaker, a miss or a runaway re-opens it for REOPEN_S (60 minutes). Every open and close is one line
  11 | +in the Heimdall evidence file (model, deadline, seconds, tokens: the caller logs the event this module returns); the
  12 | +count goes on STATE line 1 (summary()).
  13 | +
  14 | +- "Its max_tokens" is the cap the call actually SENT (providers.Backend.max_out: every Heimdall family is sent its
  15 | +  min_out floor of 16,000, Grok 8 x max_tokens, since a reasoning model thinks inside it). Measured on 1,252 recorded
  16 | +  answers (10:4x ET Nov 14): none exceeds 1x that cap; against the CALLER's max_tokens, 309 of 676 healthy Grok answers
  17 | +  and 61 of 127 deepseek answers would read as runaways. Asked of the orchestrator on STATE line 1.
  18 | +- A breaker is not an outage (ruling 87's clock is about NO family answering); it lives in its own state file.
  19 | +- Only LIVE calls touch it: a recorded reply is served as before, replay never consults it, and probes (ruling 87) and
  20 | +  shadow calls (ruling 86) neither count nor skip (the caller decides; providers.Router._breaker_live).
  21 | +- The state file: {"models": {name: {"misses", "open_until", "trial_at", "opens", "why"}}, "events": [the last
  22 | +  EVENTS_KEPT opens and closes]}. Times are ISO UTC. An unreadable file raises BreakerUnreadable: the caller says so and
  23 | +  skips nothing by it (an optimisation never stops a verdict; ruling 82's chain still fails over call by call)."""
  24 | +import fcntl
  25 | +import json
  26 | +import os
  27 | +from datetime import datetime, timedelta, timezone
  28 | +
  29 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  30 | +                     "BREAKERS.json")
  31 | +MISSES_TO_OPEN = 2                      # ruling 99: two deadline misses in a row
  32 | +OPEN_S = 30 * 60                        # ruling 99: skipped by every list for 30 minutes
  33 | +REOPEN_S = 60 * 60                      # ruling 99: a failed trial re-opens it for 60
  34 | +RUNAWAY_X = 2.0                         # ruling 99: more than twice its max_tokens (the cap sent)
  35 | +TRIAL_HOLD_S = 15 * 60                  # a trial whose call never reports (its process ended) frees the trial after
  36 | +EVENTS_KEPT = 500
  37 | +
  38 | +
  39 | +class BreakerUnreadable(Exception):
  40 | +    """The state file exists but cannot be read: no guess either way."""
  41 | +
  42 | +
  43 | +def _now(now=None):
  44 | +    return now if now is not None else datetime.now(timezone.utc)
  45 | +
  46 | +
  47 | +def _iso(t):
  48 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  49 | +
  50 | +
  51 | +def _t(s):
  52 | +    try:
  53 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  54 | +    except (TypeError, ValueError):
  55 | +        return None
  56 | +    return t if t.tzinfo is not None else None
  57 | +
  58 | +
  59 | +def _load(path):
  60 | +    if not os.path.exists(path):
  61 | +        return {"models": {}, "events": []}
  62 | +    try:
  63 | +        with open(path) as f:
  64 | +            s = json.load(f)
  65 | +        if not isinstance(s, dict) or not isinstance(s.get("models"), dict):
  66 | +            raise ValueError("not a breaker state")
  67 | +        return s
  68 | +    except (OSError, ValueError) as e:
  69 | +        raise BreakerUnreadable(f"{path}: {type(e).__name__}: {e}") from None
  70 | +
  71 | +
  72 | +def _save(path, s):
  73 | +    tmp = f"{path}.{os.getpid()}.tmp"
  74 | +    with open(tmp, "w") as f:
  75 | +        json.dump(s, f, indent=1)
  76 | +    os.replace(tmp, path)
  77 | +
  78 | +
  79 | +class _Locked:
  80 | +    def __init__(self, path):
  81 | +        self.path = path
  82 | +
  83 | +    def __enter__(self):
  84 | +        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
  85 | +        self.f = open(self.path + ".lock", "w")
  86 | +        fcntl.flock(self.f, fcntl.LOCK_EX)
  87 | +        return self
  88 | +
  89 | +    def __exit__(self, *exc):
  90 | +        fcntl.flock(self.f, fcntl.LOCK_UN)
  91 | +        self.f.close()
  92 | +        return False
  93 | +
  94 | +
  95 | +def allow(name, path=STATE, now=None):
  96 | +    """May a live call go to `name` now? -> (True, None) closed; (True, "trial") the one call after the open window
  97 | +    (claimed here, under the lock); (False, why) open, or a trial already in flight. A malformed record skips nothing."""
  98 | +    now = _now(now)
  99 | +    with _Locked(path):
 100 | +        s = _load(path)
 101 | +        m = s["models"].get(name)
 102 | +        until = _t(m.get("open_until")) if isinstance(m, dict) else None
 103 | +        if until is None:
 104 | +            return True, None
 105 | +        if now < until:
 106 | +            return False, f"circuit breaker open until {m['open_until']} (ruling 99: {m.get('why')})"
 107 | +        ta = _t(m.get("trial_at"))
 108 | +        if ta is not None and (now - ta).total_seconds() < TRIAL_HOLD_S:
 109 | +            return False, f"circuit breaker: its one trial call is in flight since {m['trial_at']} (ruling 99)"
 110 | +        m["trial_at"] = _iso(now)
 111 | +        _save(path, s)
 112 | +        return True, "trial"
 113 | +
 114 | +
 115 | +def record(name, outcome, path=STATE, now=None, deadline_s=None, seconds=None, tokens=None, max_out=None):
 116 | +    """One live call's outcome: "answer", "miss" (its deadline passed) or "runaway" (more than RUNAWAY_X times the cap
 117 | +    it was sent). -> the event for the evidence file ({"kind": "breaker_open" | "breaker_close", "model", "why",
 118 | +    "deadline_s", "seconds", "tokens", "max_out", "until", "utc"}) or None."""
 119 | +    if outcome not in ("answer", "miss", "runaway"):
 120 | +        raise ValueError(f"outcome must be answer, miss or runaway, not {outcome!r}")
 121 | +    now = _now(now)
 122 | +    with _Locked(path):
 123 | +        s = _load(path)
 124 | +        m = s["models"].get(name)
 125 | +        if not isinstance(m, dict):
 126 | +            m = s["models"][name] = {"misses": 0, "open_until": None, "trial_at": None, "opens": 0}
 127 | +        until = _t(m.get("open_until"))
 128 | +        detail = {"model": name, "deadline_s": deadline_s, "seconds": seconds, "tokens": tokens, "max_out": max_out}
 129 | +        ev = None
 130 | +        if outcome == "answer":
 131 | +            m["misses"] = 0
 132 | +            if until is not None and now >= until:            # the trial (a call after the window) answered
 133 | +                m["open_until"], m["trial_at"] = None, None
 134 | +                ev = dict(detail, kind="breaker_close", why="the trial call answered")
 135 | +        elif until is not None and now >= until:              # the trial failed: open again, for longer
 136 | +            m["why"] = "the trial call " + ("missed its deadline" if outcome == "miss" else
 137 | +                                            f"returned more than {RUNAWAY_X:g}x the cap it was sent")
 138 | +            m["open_until"], m["trial_at"] = _iso(now + timedelta(seconds=REOPEN_S)), None
 139 | +            m["opens"] = int(m.get("opens") or 0) + 1
 140 | +            ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
 141 | +        elif until is None:                                   # closed (while open, a call from before it is ignored)
 142 | +            m["misses"] = int(m.get("misses") or 0) + (1 if outcome == "miss" else 0)
 143 | +            if outcome == "runaway" or m["misses"] >= MISSES_TO_OPEN:
 144 | +                m["why"] = (f"returned more than {RUNAWAY_X:g}x the cap it was sent" if outcome == "runaway" else
 145 | +                            f"missed its deadline {MISSES_TO_OPEN} times in a row")
 146 | +                m["open_until"], m["trial_at"], m["misses"] = _iso(now + timedelta(seconds=OPEN_S)), None, 0
 147 | +                m["opens"] = int(m.get("opens") or 0) + 1
 148 | +                ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
 149 | +        if ev:
 150 | +            ev["utc"] = _iso(now)
 151 | +            s["events"] = (list(s.get("events") or []) + [ev])[-EVENTS_KEPT:]
 152 | +        _save(path, s)
 153 | +        return ev
 154 | +
 155 | +
 156 | +def summary(path=STATE, now=None, since=None):
 157 | +    """For STATE line 1 (ruling 99: "the count goes on STATE line 1"): the breakers open now and the opens / closes
 158 | +    since `since` (an aware datetime; default: the last 24 hours). -> {"open": [...], "opens": n, "closes": n}."""
 159 | +    now = _now(now)
 160 | +    since = since or now - timedelta(hours=24)
 161 | +    with _Locked(path):
 162 | +        s = _load(path)
 163 | +    open_now = [{"model": n, "until": m.get("open_until"), "why": m.get("why")}
 164 | +                for n, m in sorted(s["models"].items()) if isinstance(m, dict) and _t(m.get("open_until")) is not None
 165 | +                and now < _t(m.get("open_until"))]
 166 | +    evs = [e for e in s.get("events") or [] if isinstance(e, dict) and (_t(e.get("utc")) or since) >= since]
 167 | +    return {"open": open_now, "opens": sum(1 for e in evs if e.get("kind") == "breaker_open"),
 168 | +            "closes": sum(1 for e in evs if e.get("kind") == "breaker_close")}
 169 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 170 | index 6dc0aee..bc0f1fe 100644
 171 | --- a/pipeline/providers.py
 172 | +++ b/pipeline/providers.py
 173 | @@ -719,7 +719,8 @@ class Router:
 174 |  
 175 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 176 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 177 | -                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None):
 178 | +                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
 179 | +                 breakers=None):
 180 |          with open(config) as f:
 181 |              self.config = json.load(f)
 182 |          rt = self.config.get("routing") or {}
 183 | @@ -754,6 +755,10 @@ class Router:
 184 |          # A probe thread asks each Heimdall family a one-word question every 2 minutes while calls fail.
 185 |          self.health, self.plan_b_chains, self.state_md = health, dict(plan_b_chains or {}), state_md
 186 |          self._probe = None
 187 | +        # RULING 99 (10:48 Nov 14): the circuit breaker's state file (pipeline/circuit_breaker.py). A model that misses
 188 | +        # its deadline twice in a row, or runs past twice the cap it was sent, is skipped by every list for 30 minutes
 189 | +        # (live calls only: a recorded reply, replay, probes and shadow calls never touch it)
 190 | +        self.breakers, self.breaker_events = breakers, []
 191 |          if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 192 |              for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 193 |                  if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 194 | @@ -947,6 +952,10 @@ class Router:
 195 |                  usd, rep = b.usd(usage), usage.get("usd_reported")
 196 |                  rec.update({"in": usage.get("in"), "out": usage.get("out"), "usd_estimate": usd,
 197 |                              "usd_reported": float(rep) if _num(rep) else None})
 198 | +                n_out, cap = usage.get("out"), ab.get("max_out")
 199 | +                if _num(n_out) and _num(cap) and n_out > self._runaway_x() * cap:   # ruling 99: a late runaway
 200 | +                    self._breaker(role, b.name, "runaway", deadline_s=ab.get("deadline_s"), seconds=rec["seconds"],
 201 | +                                  tokens=n_out, max_out=cap)
 202 |                  if self.spend_path:
 203 |                      try:
 204 |                          self._replace_booking(b, role, booked, usage, usd, rep)
 205 | @@ -1006,6 +1015,46 @@ class Router:
 206 |          d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 207 |          return float(d) if _num(d) and d > 0 else None
 208 |  
 209 | +    def _breaker_live(self, role):
 210 | +        """RULING 99: the breaker counts and skips only this builder's LIVE calls (never replay, a probe or a shadow)."""
 211 | +        return bool(self.breakers) and not self.replay and not role.startswith(("probe87:", "shadow86:"))
 212 | +
 213 | +    @staticmethod
 214 | +    def _runaway_x():
 215 | +        import circuit_breaker as CB
 216 | +        return CB.RUNAWAY_X
 217 | +
 218 | +    def _breaker_allow(self, role, name):
 219 | +        """RULING 99 -> why `name` is skipped now (its breaker is open, or its one trial is in flight), or None. A state
 220 | +        that cannot be read skips nothing (a notice): the breaker saves minutes, it never stops a verdict."""
 221 | +        if not self._breaker_live(role):
 222 | +            return None
 223 | +        import circuit_breaker as CB
 224 | +        try:
 225 | +            ok, why = CB.allow(name, self.breakers)
 226 | +        except (CB.BreakerUnreadable, OSError) as e:
 227 | +            n = f"RULING 99: the circuit breaker's state cannot be read, so it skips nothing: {e}"
 228 | +            if n not in self.notices:
 229 | +                self.notices.append(n)
 230 | +            return None
 231 | +        return None if ok else why
 232 | +
 233 | +    def _breaker(self, role, name, outcome, **kw):
 234 | +        """RULING 99: one live call's outcome to the breaker; an open or a close is one line in the evidence file."""
 235 | +        if not self._breaker_live(role):
 236 | +            return
 237 | +        import circuit_breaker as CB
 238 | +        try:
 239 | +            ev = CB.record(name, outcome, self.breakers, **kw)
 240 | +        except (CB.BreakerUnreadable, OSError) as e:
 241 | +            n = f"RULING 99: the circuit breaker's state cannot be read or written: {e}"
 242 | +            if n not in self.notices:
 243 | +                self.notices.append(n)
 244 | +            return
 245 | +        if ev:
 246 | +            self.breaker_events.append(ev)
 247 | +            self._log_slow(dict(ev, role=role))
 248 | +
 249 |      def _note(self, role, b, answered):
 250 |          """RULING 87: a Heimdall verdict or writer call's outcome, to the shared health state (never a gate here: a
 251 |          state file that cannot be written is a notice). The probe thread starts at the first failure."""
 252 | @@ -1170,6 +1219,10 @@ class Router:
 253 |              if self.replay:
 254 |                  tried.append((name, "replay: not recorded"))
 255 |                  continue
 256 | +            bwhy = self._breaker_allow(role, name)              # ruling 99: an open breaker skips it; the next leads
 257 | +            if bwhy:
 258 | +                tried.append((name, bwhy))
 259 | +                continue
 260 |              upper = b.upper_usd(prompt, max_tokens, system)
 261 |              key = self._reserve(b, upper)
 262 |              if isinstance(b, HeimdallBackend):
 263 | @@ -1193,7 +1246,8 @@ class Router:
 264 |                                  "prompt_chars": len(prompt_text(prompt)),
 265 |                                  "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
 266 |                  self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 267 | -                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 268 | +                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time(),
 269 | +                        "max_out": b.max_out(max_tokens)}             # ruling 99: a late runaway is measured on it
 270 |              try:
 271 |                  if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 272 |                      text, usage, secs = _within(dl, lambda: b.complete(prompt, max_tokens, seed, system),
 273 | @@ -1202,6 +1256,7 @@ class Router:
 274 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 275 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 276 |                  self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 277 | +                self._breaker(role, name, "miss", deadline_s=dl, seconds=dl, max_out=b.max_out(max_tokens))
 278 |                  booked = b.prompt_usd(prompt, system)
 279 |                  tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 280 |                                      "ruling 83 (a))"))
 281 | @@ -1233,6 +1288,9 @@ class Router:
 282 |                  tried.append((name, "refused this request: an empty reply"))
 283 |                  continue
 284 |              self._note(role, b, True)                  # ruling 87: a Heimdall family answered inside its deadline
 285 | +            cap, n_out = b.max_out(max_tokens), (usage or {}).get("out")
 286 | +            self._breaker(role, name, "runaway" if _num(n_out) and n_out > self._runaway_x() * cap else "answer",
 287 | +                          deadline_s=dl, seconds=round(secs, 2), tokens=n_out, max_out=cap)       # ruling 99
 288 |              recorded = ""
 289 |              if path and isinstance(text, str) and text.strip():
 290 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 291 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 292 | index b034586..ac9acba 100644
 293 | --- a/tests/package/proof_ledger.py
 294 | +++ b/tests/package/proof_ledger.py
 295 | @@ -57,6 +57,7 @@ sys.path.insert(0, HERE)
 296 |  import eligibility as E  # noqa: E402
 297 |  import candidates as CA  # noqa: E402
 298 |  import heimdall_health as HH  # noqa: E402
 299 | +import circuit_breaker as CB  # noqa: E402
 300 |  import shadow86 as SH  # noqa: E402
 301 |  import ledger_build as LB  # noqa: E402
 302 |  import moments as M  # noqa: E402
 303 | @@ -101,6 +102,16 @@ def delivered_pins(paths):
 304 |      return spans, newest, pins
 305 |  
 306 |  
 307 | +def build_router(routing, shadow, shadow_log):
 308 | +    """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
 309 | +    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker."""
 310 | +    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 311 | +                    limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 312 | +                    routing=routing, shadow=shadow, shadow_log=shadow_log,
 313 | +                    health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
 314 | +                    breakers=CB.STATE)                                                         # ruling 99
 315 | +
 316 | +
 317 |  def main(argv=None):
 318 |      ap = argparse.ArgumentParser()
 319 |      ap.add_argument("--delivered", nargs="+", required=True, metavar="PIN",
 320 | @@ -193,10 +204,7 @@ def main(argv=None):
 321 |      shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 322 |      if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 323 |          shadow = rt.get("shadow") or None
 324 | -    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 325 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 326 | -                      routing=routing, shadow=shadow, shadow_log=os.path.join(out_dir, "SHADOW86.jsonl"),
 327 | -                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD)    # ruling 87
 328 | +    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 329 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 330 |          + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 331 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 332 | @@ -367,6 +375,16 @@ def main(argv=None):
 333 |                                if vis.get("estimated_calls") else ""))
 334 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 335 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 336 | +    evs = router.breaker_events                  # RULING 99: the circuit breaker's count, for STATE line 1
 337 | +    try:
 338 | +        bs = CB.summary(CB.STATE)
 339 | +        res["breakers_ruling_99"] = dict(bs, this_build=evs)
 340 | +        say(f"  RULING 99 (circuit breaker): this build opened {sum(e['kind'] == 'breaker_open' for e in evs)} and "
 341 | +            f"closed {sum(e['kind'] == 'breaker_close' for e in evs)}; open now: "
 342 | +            + ("; ".join(f"{o['model']} until {o['until']} ({o['why']})" for o in bs["open"]) or "none")
 343 | +            + f"; in 24 h: {bs['opens']} opened, {bs['closes']} closed")
 344 | +    except Exception as e:                       # noqa: BLE001 (the record is written whatever the breaker says)
 345 | +        say(f"  RULING 99 (circuit breaker): its state cannot be read: {type(e).__name__}: {str(e)[:160]}")
 346 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
 347 |          if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:      # 1420b C2: its flag tells the truth
 348 |              CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
 349 | diff --git a/tests/providers/test_circuit_breaker.py b/tests/providers/test_circuit_breaker.py
 350 | new file mode 100644
 351 | index 0000000..345cac2
 352 | --- /dev/null
 353 | +++ b/tests/providers/test_circuit_breaker.py
 354 | @@ -0,0 +1,209 @@
 355 | +#!/usr/bin/env python3
 356 | +"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER (pipeline/circuit_breaker.py and its use in
 357 | +providers.Router and the ledger build). Offline: a temporary state file, the test's own clock, fake back-ends."""
 358 | +import json
 359 | +import os
 360 | +import sys
 361 | +import tempfile
 362 | +import unittest
 363 | +from datetime import datetime, timedelta, timezone
 364 | +
 365 | +HERE = os.path.dirname(os.path.abspath(__file__))
 366 | +REPO = os.path.dirname(os.path.dirname(HERE))
 367 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 368 | +sys.path.insert(0, HERE)
 369 | +import circuit_breaker as CB  # noqa: E402
 370 | +import providers as P  # noqa: E402
 371 | +from test_providers import Fake, Slow, router, wait_for  # noqa: E402
 372 | +
 373 | +T0 = datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)
 374 | +GLM = "heimdall:z-ai/glm-5.3-flash"
 375 | +
 376 | +
 377 | +def at(minutes=0, seconds=0):
 378 | +    return T0 + timedelta(minutes=minutes, seconds=seconds)
 379 | +
 380 | +
 381 | +class TestBreaker(unittest.TestCase):
 382 | +    def setUp(self):
 383 | +        self.d = tempfile.TemporaryDirectory()
 384 | +        self.state = os.path.join(self.d.name, "BREAKERS.json")
 385 | +
 386 | +    def tearDown(self):
 387 | +        self.d.cleanup()
 388 | +
 389 | +    def rec(self, outcome, t, **kw):
 390 | +        return CB.record(GLM, outcome, self.state, now=t, **kw)
 391 | +
 392 | +    def test_two_deadline_misses_in_a_row_open_it_for_30_minutes(self):
 393 | +        self.assertIsNone(self.rec("miss", at(0)))
 394 | +        self.assertIsNone(self.rec("answer", at(1)))                      # an answer between: not in a row
 395 | +        self.assertIsNone(self.rec("miss", at(2)))
 396 | +        ev = self.rec("miss", at(3), deadline_s=120.0, seconds=120.0, max_out=16000)
 397 | +        self.assertEqual({k: ev[k] for k in ("kind", "model", "why", "until", "deadline_s", "seconds", "tokens",
 398 | +                                             "max_out", "utc")},
 399 | +                         {"kind": "breaker_open", "model": GLM, "why": "missed its deadline 2 times in a row",
 400 | +                          "until": "2026-11-14T15:33:00Z", "deadline_s": 120.0, "seconds": 120.0, "tokens": None,
 401 | +                          "max_out": 16000, "utc": "2026-11-14T15:03:00Z"})
 402 | +        ok, why = CB.allow(GLM, self.state, now=at(32, 59))
 403 | +        self.assertFalse(ok)
 404 | +        self.assertIn("open until 2026-11-14T15:33:00Z", why)
 405 | +        self.assertEqual(CB.allow("heimdall:deepseek/deepseek-v4.1-flash", self.state, now=at(4)), (True, None))
 406 | +
 407 | +    def test_after_30_minutes_one_trial_an_answer_closes_it_and_a_miss_reopens_it_for_60(self):
 408 | +        self.rec("miss", at(0))
 409 | +        self.rec("miss", at(1))                                           # open until 15:31
 410 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))
 411 | +        ok, why = CB.allow(GLM, self.state, now=at(31, 1))                # one trial at a time
 412 | +        self.assertFalse(ok)
 413 | +        self.assertIn("trial call is in flight", why)
 414 | +        ev = self.rec("answer", at(32))
 415 | +        self.assertEqual((ev["kind"], ev["why"]), ("breaker_close", "the trial call answered"))
 416 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(33)), (True, None))
 417 | +        self.rec("miss", at(40))
 418 | +        self.rec("miss", at(41))                                          # open again until 16:11
 419 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(71)), (True, "trial"))
 420 | +        ev = self.rec("miss", at(73))                                     # the trial misses: 60 minutes
 421 | +        self.assertEqual((ev["kind"], ev["until"], ev["why"]),
 422 | +                         ("breaker_open", "2026-11-14T17:13:00Z", "the trial call missed its deadline"))
 423 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(132, 59))[0])
 424 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(133)), (True, "trial"))
 425 | +        self.assertEqual(json.load(open(self.state))["models"][GLM]["opens"], 3)
 426 | +
 427 | +    def test_a_runaway_opens_it_at_once(self):
 428 | +        ev = self.rec("runaway", at(0), tokens=40000, max_out=16000)
 429 | +        self.assertEqual((ev["kind"], ev["why"], ev["tokens"]),
 430 | +                         ("breaker_open", "returned more than 2x the cap it was sent", 40000))
 431 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(30)), (True, "trial"))
 432 | +        ev = self.rec("runaway", at(31), tokens=40000, max_out=16000)   # a trial that runs away re-opens it too
 433 | +        self.assertEqual((ev["why"], ev["until"]),
 434 | +                         ("the trial call returned more than 2x the cap it was sent", "2026-11-14T16:31:00Z"))
 435 | +
 436 | +    def test_calls_in_flight_when_it_opened_change_nothing_and_a_dead_trial_is_freed(self):
 437 | +        self.rec("miss", at(0))
 438 | +        self.rec("miss", at(0, 30))                                       # open until 15:30:30
 439 | +        self.assertIsNone(self.rec("miss", at(5)))                        # calls from before it opened: two misses
 440 | +        self.assertIsNone(self.rec("miss", at(5, 30)))                    # never extend or re-open the window
 441 | +        self.assertIsNone(self.rec("answer", at(6)))                      # an answer inside the window: still open
 442 | +        self.assertEqual(json.load(open(self.state))["models"][GLM]["open_until"], "2026-11-14T15:30:30Z")
 443 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))   # its caller's process ends ...
 444 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(45, 59))[0])
 445 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(46)), (True, "trial"))   # ... freed after TRIAL_HOLD_S
 446 | +
 447 | +    def test_the_count_for_state_line_1_and_an_unreadable_state_is_never_guessed(self):
 448 | +        self.rec("miss", at(0))
 449 | +        self.rec("miss", at(1))
 450 | +        CB.allow(GLM, self.state, now=at(31))
 451 | +        self.rec("answer", at(32))
 452 | +        self.rec("runaway", at(40), tokens=40000, max_out=16000)
 453 | +        s = CB.summary(self.state, now=at(41))
 454 | +        self.assertEqual((s["opens"], s["closes"], [o["model"] for o in s["open"]]), (2, 1, [GLM]))
 455 | +        self.assertEqual(CB.summary(self.state, now=at(41), since=at(35))["opens"], 1)
 456 | +        with open(self.state, "w") as f:
 457 | +            f.write("{ broken")
 458 | +        for fn in (lambda: CB.allow(GLM, self.state, now=at(50)), lambda: self.rec("miss", at(50)),
 459 | +                   lambda: CB.summary(self.state, now=at(50))):
 460 | +            with self.assertRaises(CB.BreakerUnreadable):
 461 | +                fn()
 462 | +        self.assertEqual(open(self.state).read(), "{ broken")
 463 | +        json.dump({"models": {GLM: {"open_until": "soon"}}}, open(self.state, "w"))
 464 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(50)), (True, None))   # a malformed record skips nothing
 465 | +        with self.assertRaises(ValueError):
 466 | +            self.rec("slow", at(51))
 467 | +
 468 | +
 469 | +class TestRouterBreaker(unittest.TestCase):
 470 | +    """providers.Router: live calls only. Two real deadline misses (P._within) open the breaker, the next family leads,
 471 | +    and the open is one line in the evidence file."""
 472 | +
 473 | +    def setUp(self):
 474 | +        self.d = tempfile.TemporaryDirectory()
 475 | +        self.state = os.path.join(self.d.name, "BREAKERS.json")
 476 | +        self.log = os.path.join(self.d.name, "DEADLINES.jsonl")
 477 | +
 478 | +    def tearDown(self):
 479 | +        self.d.cleanup()
 480 | +
 481 | +    def mk(self, backends, chain, **kw):
 482 | +        return router(self.d.name, backends, {"check": chain, "probe87:" + chain[0]: [chain[0]]}, deadline_log=self.log,
 483 | +                      breakers=self.state, **kw)
 484 | +
 485 | +    def test_two_misses_skip_glm_and_the_next_family_leads(self):
 486 | +        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.4, family="glm")
 487 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 488 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 489 | +        self.assertEqual([r.call("check", f"p{i}", 100, 7, deadline_s=0.1).backend for i in range(2)],
 490 | +                         ["heimdall:deepseek"] * 2)
 491 | +        rep = r.call("check", "p3", 100, 7, deadline_s=0.1)
 492 | +        import time as _t
 493 | +        _t.sleep(0.6)                                                     # the two abandoned calls end on their clock
 494 | +        self.assertEqual((rep.backend, glm.calls), ("heimdall:deepseek", 2))      # glm not asked a third time
 495 | +        self.assertIn("circuit breaker open until", dict(rep.tried)[GLM])
 496 | +        self.assertEqual([e["kind"] for e in r.breaker_events], ["breaker_open"])
 497 | +        opened = [x for x in wait_for(self.log, "breaker_open") if x["kind"] == "breaker_open"]
 498 | +        self.assertEqual({k: opened[0][k] for k in ("model", "deadline_s", "seconds", "max_out", "role")},
 499 | +                         {"model": GLM, "deadline_s": 0.1, "seconds": 0.1, "max_out": 100, "role": "check"})
 500 | +        self.assertEqual(r.call("probe87:" + GLM, "Reply with the single word OK.", 64, 7).backend, GLM)  # a probe:
 501 | +        #   asked all the same, and never counted (ruling 87's probe is not a list)
 502 | +
 503 | +    def test_a_runaway_answer_opens_it_and_a_recorded_reply_is_still_served(self):
 504 | +        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 201})   # > 2 x 100
 505 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 506 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"], record_dir=os.path.join(self.d.name, "rec"))
 507 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # it answered: the answer stands
 508 | +        self.assertEqual(r.breaker_events[0]["why"], "returned more than 2x the cap it was sent")
 509 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # its recorded reply: served, nothing paid
 510 | +        self.assertEqual(glm.calls, 1)
 511 | +        self.assertEqual(r.call("check", "q", 100, 7).backend, "heimdall:deepseek")   # a live call: skipped
 512 | +        glm2 = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 200})  # exactly 2x
 513 | +        r2 = self.mk([glm2, ds], [GLM, "heimdall:deepseek"])
 514 | +        os.remove(self.state)
 515 | +        r2.call("check", "p", 100, 7)
 516 | +        self.assertEqual(r2.breaker_events, [])
 517 | +        healthy = Fake("heimdall:deepseek2", "heimdall", answer='{"ok": 3}', family="deepseek",
 518 | +                       usage={"in": 10, "out": 1500})
 519 | +        healthy.spec["min_out"] = 1000          # a reasoning model is sent its floor (as Grok and deepseek are):
 520 | +        r3 = self.mk([healthy, ds], ["heimdall:deepseek2", "heimdall:deepseek"])
 521 | +        self.assertEqual(r3.call("check", "z", 100, 7).backend, "heimdall:deepseek2")
 522 | +        self.assertEqual(r3.breaker_events, [])  # 1500 of a 1000 cap: no runaway (15x the caller's 100 would be one)
 523 | +
 524 | +    def test_a_late_answer_that_ran_away_opens_it(self):
 525 | +        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.3, family="glm", usage={"in": 10, "out": 5000})
 526 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 527 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 528 | +        self.assertEqual(r.call("check", "p", 100, 7, deadline_s=0.1).backend, "heimdall:deepseek")   # one miss
 529 | +        log = wait_for(self.log, "breaker_open")                          # its late answer: 5000 > 2 x 100
 530 | +        self.assertEqual([x["why"] for x in log if x["kind"] == "breaker_open"],
 531 | +                         ["returned more than 2x the cap it was sent"])
 532 | +        self.assertFalse(CB.allow(GLM, self.state)[0])
 533 | +
 534 | +    def test_replay_never_consults_it_and_an_unreadable_state_skips_nothing(self):
 535 | +        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm")
 536 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 537 | +        CB.record(GLM, "runaway", self.state)                             # open now
 538 | +        rr = self.mk([glm, ds], [GLM, "heimdall:deepseek"], replay=True)
 539 | +        self.assertIsNone(rr._breaker_allow("check", GLM))                # replay walks its recordings only
 540 | +        with open(self.state, "w") as f:
 541 | +            f.write("{ broken")
 542 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 543 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # never a skip by guess
 544 | +        self.assertTrue(any("RULING 99" in n for n in r.notices))
 545 | +        no = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 546 | +        no.breakers = None                                                # a router given no state: no breaker
 547 | +        self.assertIsNone(no._breaker_allow("check", GLM))
 548 | +
 549 | +
 550 | +class TestTheBuildUsesIt(unittest.TestCase):
 551 | +    def test_the_build_router_has_the_breaker_and_the_health(self):
 552 | +        """The ledger build's one router (proof_ledger.build_router) is given ruling 99's state and ruling 87's."""
 553 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 554 | +        import heimdall_health as HH
 555 | +        import proof_ledger as PLG
 556 | +        with tempfile.TemporaryDirectory() as d:
 557 | +            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 558 | +        self.assertEqual((r.breakers, r.health, r.routing), (CB.STATE, HH.STATE, "heimdall_first"))
 559 | +        self.assertEqual(os.path.basename(CB.STATE), "BREAKERS.json")
 560 | +
 561 | +
 562 | +if __name__ == "__main__":
 563 | +    unittest.main()
 564 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence of calls that breaks it.

BACKGROUND (static):
- providers.Router.call(role, prompt, max_tokens, ...) walks a role's chain of model back-ends in order. For each leg
  it first serves a RECORDED reply when one exists on disk (no paid call), else (in replay mode) moves on, else makes a
  live paid call under a deadline (Heimdall gateway legs: 120 s). A leg that misses its deadline is abandoned and the
  chain moves on; a leg that answers decides. Ruling 87's shared health file and its probe thread (probe roles
  "probe87:<model>") are a SEPARATE mechanism about Heimdall as a whole; ruling 86's shadow calls (roles
  "shadow86:<role>") ask Grok the same prompt and never decide.
- Before this change, a deadline miss did not stop the Router from asking the same model again on the next call: glm
  missed every call's 120 s deadline at 09:55 ET, so every glm-first verdict burned 120 s before deepseek or Grok.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.py:1211 serves a recorded reply before anything else; :1219 `if self.replay: ... continue` (replay never
  makes a live call). The new breaker check (:1222) sits AFTER both, so it only ever gates a live paid call.
- providers._within (:345) raises DeadlineExceeded (class at :340) when the deadline passes; the abandoned call keeps
  running in its own thread and, if it ends, calls Router._late (:934) with (text, usage, seconds) or an error.
- Router._log_slow (:850) appends one JSON line to the evidence file (deadline_log) and does nothing when no path is
  set; a write failure becomes a notice, never an exception.
- Backend.max_out(max_tokens) is the output cap a call actually SENDS: base back-ends max(spec min_out, max_tokens)
  (:177), xAI text max(min_out or 8000, 8 x max_tokens) (:443), xAI vision max(..., 4 x max_tokens) (:531).
  model_providers.json gives every Heimdall family min_out 16,000. Usage "out" is the vendor's completion count, with
  reasoning tokens included (xAI's backend adds them explicitly).
- tests/package/proof_ledger.py builds the ONE production Router of a ledger build; the exam's adapter
  (moments_gate_adapter.make_router) builds its own Router with no breaker (its replay must stay deterministic).

THE ORCHESTRATOR'S RULING (10:48 ET Nov 14), verbatim:
"RULING 99, THE CIRCUIT BREAKER. A model that misses its deadline TWICE in a row, or returns more than twice its
max_tokens (a runaway: glm gave 16,000 tokens against 4,000, and 10,455 for a one-word probe), is SKIPPED by every list
for 30 minutes; the next family leads. After 30 minutes one real call may try it again; a miss re-opens the breaker for
60. Every open / close is one line in the Heimdall evidence file (model, deadline, seconds, tokens) and the count goes
on STATE line 1. A breaker is not an outage: ruling 87's clock is about NO family answering. While glm's breaker is
open, step A's Heimdall filter is deepseek, the hook rating is qwen -> deepseek, fidelity is qwen -> Grok, exclusion
is deepseek -> Grok. This is why Grok served 24 of 27 step A verdicts at 09:55 after each burned 120 s: fix that first,
it is costing every build minutes and dollars."
FACT, measured and put to the orchestrator on STATE line 1 (10:45): glm was SENT a 16,000-token cap (its min_out), not
4,000; its 16,000 tokens were 1.00x that cap and the probe's 10,455 were 0.65x. On 1,252 recorded answers no model
exceeds 1x the cap it was sent; against the CALLER's max_tokens, 309 of 676 healthy Grok answers and 61 of 127 deepseek
answers exceed 2x. So this change reads "its max_tokens" as the cap actually sent (Backend.max_out). The heimdall_first
lists minus glm are exactly the chains the ruling names (step A first: deepseek, Grok; hook: qwen, deepseek, Grok;
fidelity: qwen, Grok; exclusion: deepseek, Grok).

THE CHANGE (the diff follows):
1. pipeline/circuit_breaker.py (new): a JSON state file under an flock (tests/package/proof/BREAKERS.json), shared by the
   builder's processes. allow(name) -> (True, None) closed; (True, "trial") the ONE call after the open window, claimed
   under the lock; (False, why) open, or a trial in flight (a trial whose caller never reports is freed after 15
   minutes). record(name, "answer" | "miss" | "runaway"): closed: 2 misses in a row (an answer resets the count) or one
   runaway open it for 30 minutes; open, inside the window: ignored (calls in flight from before it opened); after the
   window: an answer closes it, a miss or a runaway re-opens it for 60 minutes. Each open / close is returned as an
   event with model, why, deadline_s, seconds, tokens, max_out, until, utc. summary() gives the open breakers and the
   opens / closes in the last 24 h. An unreadable file raises BreakerUnreadable; a malformed record skips nothing.
2. pipeline/providers.py: Router(breakers=path). Live calls only (never replay, probe87: or shadow86: roles):
   _breaker_allow before the paid call skips an open model (the next leg leads); a deadline miss records "miss"; an
   answer records "runaway" when its output exceeds 2x the cap sent, else "answer"; a LATE answer (in _late) that ran
   past 2x the cap records "runaway". Each event goes to the evidence file (_log_slow) and router.breaker_events. An
   unreadable breaker state skips nothing (a notice): the breaker saves minutes, it never stops a verdict.
3. tests/package/proof_ledger.py: the build's Router is made by build_router() (the same arguments as before, plus
   breakers=circuit_breaker.STATE), and the build log and record carry the count for STATE line 1.
4. Tests: tests/providers/test_circuit_breaker.py (new, 10 tests, real deadline misses through _within). 17 mutations,
   each killed. 21 suites, 578 tests pass.

ATTACK:
(a) Can glm burn its deadline more than twice in a row, across threads or across build processes, once this is live?
    Can the breaker skip a model that is healthy (Grok or deepseek reasoning inside their caps)?
(b) The trial: can two calls both be the trial? Can a trial claim be lost so the model is never tried again? Can a
    call that started before the open re-open or extend it?
(c) Can an open breaker ever leave a verdict with NO leg (fail closed is acceptable; a wrong verdict is not)? Can it
    change which RECORDED reply a replay serves?
(d) Concurrency: two processes and eight threads on one state file; the lock; the atomic write.
(e) Anything that could make a build slower or costlier than before, or break pp-ingest (which never loads this file).

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

