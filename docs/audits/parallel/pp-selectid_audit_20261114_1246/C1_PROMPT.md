# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_1246
# Branch: pp-selectid
# Generated: 2026-11-14 12:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_1246/C1_STEP.diff (824 lines)
```
   1 | diff --git a/pipeline/circuit_breaker.py b/pipeline/circuit_breaker.py
   2 | index 868dc78..459d79d 100644
   3 | --- a/pipeline/circuit_breaker.py
   4 | +++ b/pipeline/circuit_breaker.py
   5 | @@ -112,6 +112,25 @@ def allow(name, path=STATE, now=None, hold_s=None):
   6 |          return True, "trial"
   7 |  
   8 |  
   9 | +def is_open(name, path=STATE, now=None):
  10 | +    """READ ONLY (it never claims a trial): would allow() skip `name` now? Its window open, or its one trial in flight.
  11 | +    RULING 101's estimate of the filter's wait reads it. An unreadable state skips nothing: False."""
  12 | +    now = _now(now)
  13 | +    try:
  14 | +        with _Locked(path):
  15 | +            s = _load(path)
  16 | +    except (BreakerUnreadable, OSError):
  17 | +        return False
  18 | +    m = s["models"].get(name)
  19 | +    until = _t(m.get("open_until")) if isinstance(m, dict) else None
  20 | +    if until is None:
  21 | +        return False
  22 | +    if now < until:
  23 | +        return True
  24 | +    ta, tu = _t(m.get("trial_at")), _t(m.get("trial_until"))
  25 | +    return ta is not None and now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S))
  26 | +
  27 | +
  28 |  def record(name, outcome, path=STATE, now=None, deadline_s=None, seconds=None, tokens=None, max_out=None):
  29 |      """One live call's outcome: "answer", "miss" (its deadline passed) or "runaway" (more than RUNAWAY_X times the cap
  30 |      it was sent). -> the event for the evidence file ({"kind": "breaker_open" | "breaker_close", "model", "why",
  31 | diff --git a/pipeline/deadline_table.py b/pipeline/deadline_table.py
  32 | new file mode 100644
  33 | index 0000000..5d3644d
  34 | --- /dev/null
  35 | +++ b/pipeline/deadline_table.py
  36 | @@ -0,0 +1,108 @@
  37 | +"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. Per (model, verdict type) the
  38 | +deadline is the recorded p90 of that pair's answered calls x FACTOR (1.5), floor FLOOR_S (60 s), ceiling CEIL_S (300 s),
  39 | +recomputed from the records daily; ruling 99's "two misses in a row" is against THAT deadline.
  40 | +
  41 | +- The records: this builder's recorded exchanges (providers.Router's record_dir: one JSON per ANSWERED call, with its
  42 | +  role, back-end and seconds). A pair with fewer than MIN_N answered calls has no row, and its gateway's configured
  43 | +  deadline stands (ruling 82's 120 s on Heimdall).
  44 | +- The table lives in a JSON file with its computed_at; load() recomputes it when it is missing, unreadable or older
  45 | +  than RECOMPUTE_S (a day). The Router applies a row only where a deadline applies today (a verdict role on a gateway
  46 | +  with a configured deadline: Heimdall); Grok keeps none (providers.Router.role_deadline).
  47 | +- Measured at 12:2x ET Nov 14: deepseek's step A, 32 answers, median 166 s, p90 273 s -> 300 s (the ceiling); glm's step
  48 | +  A, 3 answers, p90 39 s -> 60 s (the floor), which its 483-532 s runs still miss."""
  49 | +import glob
  50 | +import json
  51 | +import math
  52 | +import os
  53 | +from datetime import datetime, timezone
  54 | +
  55 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  56 | +                     "DEADLINE_TABLE.json")
  57 | +FACTOR, FLOOR_S, CEIL_S = 1.5, 60.0, 300.0      # ruling 100
  58 | +MIN_N = 3                                      # a pair needs this many answered calls for a row of its own
  59 | +RECOMPUTE_S = 24 * 3600                        # ruling 100: "recomputed from the records daily"
  60 | +RULE = "p90 of the pair's recorded answered calls x 1.5, floor 60 s, ceiling 300 s (ruling 100)"
  61 | +
  62 | +
  63 | +def _iso(t):
  64 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  65 | +
  66 | +
  67 | +def _t(s):
  68 | +    try:
  69 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  70 | +    except (TypeError, ValueError):
  71 | +        return None
  72 | +    return t if t.tzinfo is not None else None
  73 | +
  74 | +
  75 | +def percentile(xs, q):
  76 | +    """Linear interpolation between the closest ranks (numpy's default)."""
  77 | +    xs = sorted(xs)
  78 | +    k = (len(xs) - 1) * q
  79 | +    lo, hi = math.floor(k), math.ceil(k)
  80 | +    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (k - lo)
  81 | +
  82 | +
  83 | +def compute(record_dir, now=None):
  84 | +    """-> {"computed_at", "rule", "rows": {"<back-end>|<role>": {"n", "p50", "p90", "deadline_s"}}} from every recorded
  85 | +    exchange in record_dir (a file that cannot be read, or has no back-end, role or positive seconds, is skipped)."""
  86 | +    now = now or datetime.now(timezone.utc)
  87 | +    seconds = {}
  88 | +    for p in glob.glob(os.path.join(record_dir or "", "*", "*.json")):
  89 | +        try:
  90 | +            with open(p) as f:
  91 | +                r = json.load(f)
  92 | +        except (OSError, ValueError):
  93 | +            continue
  94 | +        b, role, s = r.get("backend"), r.get("role"), r.get("seconds")
  95 | +        if isinstance(b, str) and isinstance(role, str) and isinstance(s, (int, float)) and not isinstance(s, bool) \
  96 | +                and math.isfinite(s) and s > 0:
  97 | +            seconds.setdefault(f"{b}|{role}", []).append(float(s))
  98 | +    rows = {}
  99 | +    for key, xs in sorted(seconds.items()):
 100 | +        if len(xs) < MIN_N:
 101 | +            continue
 102 | +        q = percentile(xs, 0.9)
 103 | +        rows[key] = {"n": len(xs), "p50": round(percentile(xs, 0.5), 1), "p90": round(q, 1),
 104 | +                     "deadline_s": round(min(CEIL_S, max(FLOOR_S, FACTOR * q)), 1)}
 105 | +    return {"computed_at": _iso(now), "rule": RULE, "rows": rows}
 106 | +
 107 | +
 108 | +def load(path=STATE, record_dir=None, now=None):
 109 | +    """The table: the saved one while it is younger than RECOMPUTE_S, else computed again from record_dir and saved
 110 | +    (a save that fails leaves the computed table in use). -> the table dict."""
 111 | +    now = now or datetime.now(timezone.utc)
 112 | +    try:
 113 | +        with open(path) as f:
 114 | +            t = json.load(f)
 115 | +        at = _t(t.get("computed_at")) if isinstance(t, dict) else None
 116 | +        if at is not None and 0 <= (now - at).total_seconds() < RECOMPUTE_S and isinstance(t.get("rows"), dict):
 117 | +            return t
 118 | +    except (OSError, ValueError):
 119 | +        pass
 120 | +    t = compute(record_dir, now)
 121 | +    try:
 122 | +        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
 123 | +        tmp = f"{path}.{os.getpid()}.tmp"
 124 | +        with open(tmp, "w") as f:
 125 | +            json.dump(t, f, indent=1)
 126 | +        os.replace(tmp, path)
 127 | +    except OSError:
 128 | +        pass
 129 | +    return t
 130 | +
 131 | +
 132 | +def deadline(table, backend, role):
 133 | +    """The pair's own deadline in seconds, or None when the table has no row for it."""
 134 | +    row = ((table or {}).get("rows") or {}).get(f"{backend}|{role}") if isinstance(table, dict) else None
 135 | +    d = row.get("deadline_s") if isinstance(row, dict) else None
 136 | +    return float(d) if isinstance(d, (int, float)) and not isinstance(d, bool) and d > 0 else None
 137 | +
 138 | +
 139 | +def text(table, applies=None):
 140 | +    """The table in one line, for STATE (ruling 100: "say the table on STATE once"); applies(key) keeps the rows a
 141 | +    Router would use (the build passes the Heimdall verdict pairs)."""
 142 | +    rows = {k: v for k, v in ((table or {}).get("rows") or {}).items() if applies is None or applies(k)}
 143 | +    return "; ".join(f"{k.split('|')[0].split('/')[-1]} {k.split('|')[1]}: {v['deadline_s']:g} s (n {v['n']}, p50 "
 144 | +                     f"{v['p50']:g}, p90 {v['p90']:g})" for k, v in sorted(rows.items()))
 145 | diff --git a/pipeline/package.py b/pipeline/package.py
 146 | index d542ae5..b3043b4 100644
 147 | --- a/pipeline/package.py
 148 | +++ b/pipeline/package.py
 149 | @@ -492,7 +492,7 @@ def src_of(x, sources):
 150 |  
 151 |  
 152 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 153 | -              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None):
 154 | +              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None, plan_only=False):
 155 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 156 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 157 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 158 | @@ -501,7 +501,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 159 |      context step A reads (its window, title, channel, publish time and the show date, so time words are judged again on
 160 |      a new show date) and the step-A prompt's version. The batches run in parallel (PRESCREEN_WORKERS), each with the
 161 |      seed of its place in the queue. Only a parsed verdict is stored: a call that fails is no verdict (law L-m), never
 162 | -    remembered. writer_vendor / writer_family: of the writers, so step A never runs on them."""
 163 | +    remembered. writer_vendor / writer_family: of the writers, so step A never runs on them. plan_only (ruling 101):
 164 | +    no call is made; -> the moments this screen would ask (no verdict in the ledger or the cache), nothing written."""
 165 |      import providers as P
 166 |      ranked = sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"]))
 167 |      if n is None:
 168 | @@ -539,6 +540,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 169 |              families.add(b.family)
 170 |          else:
 171 |              todo.append(m)
 172 | +    if plan_only:                                        # ruling 101: what this screen would ask, nothing asked
 173 | +        return todo
 174 |      chunks = [todo[i:i + batch] for i in range(0, len(todo), batch)]
 175 |  
 176 |      def screen(i, chunk):
 177 | @@ -577,12 +580,96 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 178 |  
 179 |  def first_bounds(router):
 180 |      """The kwargs of step A's FIRST screen. RULING 85: under heimdall_first the first verdict is a Heimdall family's,
 181 | -    2 clips and 120 s a call (Heimdall needs a median 268 s on 8 clips); today it keeps its batches with no deadline.
 182 | -    One helper for both builds (the medley's and the spotlight's)."""
 183 | -    return {"batch": SECOND_VERDICT_BATCH, "deadline_s": SECOND_VERDICT_DEADLINE_S} \
 184 | +    2 clips a call (Heimdall needs a median 268 s on 8 clips), failing over down the chain (ruling 82); today it keeps
 185 | +    its batches with no deadline. RULING 100 (12:16 Nov 14): no flat deadline is passed: each leg's own (the Router's
 186 | +    role_deadline: its row of the deadline table, else the gateway's 120 s). One helper for both builds."""
 187 | +    return {"batch": SECOND_VERDICT_BATCH, "deadline_s": None, "failover": True} \
 188 |          if getattr(router, "routing", "today") == "heimdall_first" else {}
 189 |  
 190 |  
 191 | +STEP_A_PARALLEL_NEW = 20           # RULING 101 (12:16 Nov 14): over 20 new moments to screen, AND
 192 | +STEP_A_PARALLEL_WAIT_S = 600.0     # the filter would hold the build over 10 minutes: Grok's confirm goes in parallel
 193 | +
 194 | +
 195 | +class _Tally:
 196 | +    """A router seen through one task (ruling 101's confirm-ahead): every reply's vendor-reported dollars (else its
 197 | +    estimate) summed; everything else is the router's own."""
 198 | +
 199 | +    def __init__(self, router):
 200 | +        self._r, self.usd, self.calls = router, 0.0, 0
 201 | +        self._lock = threading.Lock()
 202 | +
 203 | +    def call(self, *a, **k):
 204 | +        rep = self._r.call(*a, **k)
 205 | +        rep_usd = (getattr(rep, "usage", None) or {}).get("usd_reported")
 206 | +        with self._lock:
 207 | +            self.calls += 1
 208 | +            self.usd += float(rep_usd) if isinstance(rep_usd, (int, float)) else float(getattr(rep, "usd", 0) or 0)
 209 | +        return rep
 210 | +
 211 | +    def __getattr__(self, name):
 212 | +        return getattr(self._r, name)
 213 | +
 214 | +
 215 | +def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **first):
 216 | +    """RULING 101 (12:16 Nov 14): does step A ask the Heimdall filter and Grok's confirm IN PARALLEL? Yes when more than
 217 | +    STEP_A_PARALLEL_NEW moments are NEW to the first screen (no verdict in this build's ledger or the shared cache) AND
 218 | +    the filter would hold the build longer than STEP_A_PARALLEL_WAIT_S: its rounds (the new moments' batches over
 219 | +    PRESCREEN_WORKERS) x the deadline of the filter's leading leg (the step_a_first chain's first back-end off the
 220 | +    writers and not breaker-open: ruling 100's per-model deadline). A leading leg with no deadline (Grok) never holds a
 221 | +    build long: sequential. -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg"}."""
 222 | +    new = prescreen(router, ms, sources, ctx, wv, wf, store=store, cache=cache, plan_only=True,
 223 | +                    **{k: v for k, v in first.items() if k in ("batch", "kind")})
 224 | +    if len(new) <= STEP_A_PARALLEL_NEW:                  # under the line: sequential whatever the wait
 225 | +        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None}
 226 | +    leg, dl = None, None
 227 | +    for name in router.chain("context_verdict", kind="step_a_first"):
 228 | +        b = router.backends.get(name)
 229 | +        if b is None or b.vendor in set(wv) or b.family in set(wf) or name in getattr(router, "down", {}) or \
 230 | +                (hasattr(router, "breaker_open") and router.breaker_open(name)):
 231 | +            continue
 232 | +        leg, dl = name, router.role_deadline("context_verdict", b)
 233 | +        break
 234 | +    batch = first.get("batch") or PRESCREEN_BATCH
 235 | +    rounds = math.ceil(math.ceil(len(new) / batch) / PRESCREEN_WORKERS) if new else 0
 236 | +    wait = rounds * dl if dl else 0.0
 237 | +    return {"parallel": len(new) > STEP_A_PARALLEL_NEW and wait > STEP_A_PARALLEL_WAIT_S, "new": new,
 238 | +            "n_new": len(new), "est_wait_s": round(wait, 1), "leg": leg}
 239 | +
 240 | +
 241 | +def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 242 | +    """RULING 101: Grok's confirm asked AT ONCE on every new moment, beside the Heimdall filter: each one's step_a_second
 243 | +    verdict, off every Heimdall family and off the writers, into the step-A cache that the second screen reads later
 244 | +    (it then reuses the verdict off the first's vendor; 'a clip passes only if BOTH pass' is unchanged, and a moment
 245 | +    whose first verdict came from Grok itself is screened off it as before). -> {"asked", "verdicts", "usd", "calls",
 246 | +    "by": {moment id: back-end}}: the spend is reported per build (a verdict the second screen cannot use is extra)."""
 247 | +    import providers as P
 248 | +    hv = {b.vendor for b in router.backends.values() if isinstance(b, P.HeimdallBackend)}
 249 | +    hf = {b.family for b in router.backends.values() if isinstance(b, P.HeimdallBackend)}
 250 | +    tally = _Tally(router)
 251 | +    try:
 252 | +        got, _fails, _, _ = prescreen(tally, new, sources, ctx, set(wv) | hv, set(wf) | hf, n=len(new), store=None,
 253 | +                                      log=log, cache=cache, batch=PRESCREEN_BATCH, deadline_s=None,
 254 | +                                      kind="step_a_second", failover=True)
 255 | +    except Exception as e:                               # noqa: BLE001 (the sequential second screen still runs)
 256 | +        return {"asked": len(new), "verdicts": 0, "usd": round(tally.usd, 4), "calls": tally.calls,
 257 | +                "error": f"{type(e).__name__}: {str(e)[:160]}"}
 258 | +    return {"asked": len(new), "verdicts": len(got), "usd": round(tally.usd, 4), "calls": tally.calls,
 259 | +            "by": {mid: a.get("backend") for mid, a in got.items() if isinstance(a, dict)}}
 260 | +
 261 | +
 262 | +def prewarm_used(router, mids, a_by, pre_by):
 263 | +    """RULING 101: how many of `mids` (the moments reaching the second screen) the confirm-ahead served: it has a
 264 | +    verdict for the moment AND that verdict is off the moment's first verdict's vendor and family (the second screen
 265 | +    reads only such a verdict; a moment whose first verdict came from Grok itself is screened off it as before)."""
 266 | +    n = 0
 267 | +    for mid in mids:
 268 | +        b1 = router.backends.get((a_by.get(mid) or {}).get("backend"))
 269 | +        b2 = router.backends.get(pre_by.get(mid))
 270 | +        n += b1 is not None and b2 is not None and b2.vendor != b1.vendor and b2.family != b1.family
 271 | +    return n
 272 | +
 273 | +
 274 |  def _second_bounds(router):
 275 |      """(batch, deadline_s) of step A's second verdict. Today it is a Heimdall family's (ruling 82: 2 clips, 120 s a
 276 |      call). RULING 88 (c), under heimdall_first, it is Grok confirming a Heimdall pass: Grok's own batch (8 clips) and no
 277 | @@ -2386,9 +2473,21 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 278 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
 279 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 280 |      wv, wf = _writers(router)
 281 | -    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 282 | -                                                   cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 283 | -                                                   **first_bounds(router))
 284 | +    fb = first_bounds(router)
 285 | +    plan = step_a_plan(router, ms, sources, ctx, wv, wf, store=store, cache=step_a_cache, **fb)   # RULING 101
 286 | +    ahead_pool = ThreadPoolExecutor(max_workers=1) if plan["parallel"] else None
 287 | +    ahead = ahead_pool.submit(confirm_ahead, router, plan["new"], sources, ctx, wv, wf, log, step_a_cache) \
 288 | +        if ahead_pool is not None else None              # Grok's confirm beside the Heimdall filter, at once
 289 | +    par = {**{k: plan[k] for k in ("parallel", "n_new", "est_wait_s", "leg")}, "used": 0}
 290 | +    try:
 291 | +        a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 292 | +                                                       cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 293 | +                                                       **fb)
 294 | +    finally:
 295 | +        if ahead is not None:
 296 | +            par.update(ahead.result())
 297 | +            ahead_pool.shutdown()
 298 | +    pre_by = par.pop("by", None) or {}                   # which back-end confirmed each moment ahead (not reported)
 299 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 300 |      levels = current_levels(sources.values(), ctx)
 301 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 302 | @@ -2396,7 +2495,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 303 |             "reposted": reposted,
 304 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 305 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 306 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 307 | +                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par},
 308 | +           "angles": [], "takeaways": [],
 309 |             "package": None}
 310 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 311 |          f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
 312 | @@ -2487,6 +2587,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 313 |                        f"{b['why']}" for b in best) if openers else
 314 |              "no cleared, cuttable moment can open (hook eligibility, G17a, the render's hook rule)"))
 315 |          return out
 316 | +    par["used"] = prewarm_used(router, cleared, a_by, pre_by)    # ruling 101: the confirm-ahead verdicts it reads
 317 |      a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log,
 318 |                                      cache=step_a_cache)                  # ORDER 06:22 item 45
 319 |      out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
 320 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 321 | index 36ece53..aad75f7 100644
 322 | --- a/pipeline/providers.py
 323 | +++ b/pipeline/providers.py
 324 | @@ -720,7 +720,7 @@ class Router:
 325 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 326 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 327 |                   routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
 328 | -                 breakers=None):
 329 | +                 breakers=None, deadlines=None):
 330 |          with open(config) as f:
 331 |              self.config = json.load(f)
 332 |          rt = self.config.get("routing") or {}
 333 | @@ -759,6 +759,8 @@ class Router:
 334 |          # its deadline twice in a row, or runs past twice the cap it was sent, is skipped by every list for 30 minutes
 335 |          # (live calls only: a recorded reply, replay, probes and shadow calls never touch it)
 336 |          self.breakers, self.breaker_events = breakers, []
 337 | +        # RULING 100 (12:16 Nov 14): the per-(model, verdict type) deadlines (pipeline/deadline_table.py's table)
 338 | +        self.deadlines = deadlines
 339 |          if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 340 |              for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 341 |                  if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 342 | @@ -1004,8 +1006,10 @@ class Router:
 343 |  
 344 |      def role_deadline(self, role, b):
 345 |          """The 20:33 order (ruling 82's chain on the verdicts): a call of a verdict role on a back-end whose gateway
 346 | -        names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets it when the
 347 | -        caller sets none. -> seconds or None."""
 348 | +        names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets one when the
 349 | +        caller sets none. RULING 100 (12:16 Nov 14): THAT deadline follows the model: the pair's own row of the
 350 | +        deadline table (p90 of its recorded answers x 1.5, 60-300 s) where it has one, else the gateway's number.
 351 | +        Where no deadline applies today (Grok, a non-verdict role), none applies now. -> seconds or None."""
 352 |          rt = self.config.get("routing") or {}
 353 |          bounded = set(rt.get("verdict_roles") or ())
 354 |          if self.routing == "today":                   # step A's first screen and step C keep no deadline today:
 355 | @@ -1013,7 +1017,11 @@ class Router:
 356 |          if role not in bounded:                       # call cannot answer in 120 s on Heimdall)
 357 |              return None
 358 |          d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 359 | -        return float(d) if _num(d) and d > 0 else None
 360 | +        if not (_num(d) and d > 0):
 361 | +            return None
 362 | +        import deadline_table as DT
 363 | +        own = DT.deadline(self.deadlines, b.name, role)          # ruling 100: the model's own, where it has one
 364 | +        return own if own is not None else float(d)
 365 |  
 366 |      def _breaker_live(self, role):
 367 |          """RULING 99: the breaker counts and skips only this builder's LIVE calls (never replay, a probe or a shadow)."""
 368 | @@ -1040,6 +1048,13 @@ class Router:
 369 |              return None
 370 |          return None if ok else why
 371 |  
 372 | +    def breaker_open(self, name):
 373 | +        """RULING 99, read only (ruling 101's wait estimate): whether a live call would skip `name` now."""
 374 | +        if not self.breakers:
 375 | +            return False
 376 | +        import circuit_breaker as CB
 377 | +        return CB.is_open(name, self.breakers)
 378 | +
 379 |      def _breaker(self, role, name, outcome, **kw):
 380 |          """RULING 99: one live call's outcome to the breaker; an open or a close is one line in the evidence file."""
 381 |          if not self._breaker_live(role):
 382 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 383 | index ac9acba..6f0ce5e 100644
 384 | --- a/tests/package/proof_ledger.py
 385 | +++ b/tests/package/proof_ledger.py
 386 | @@ -58,6 +58,7 @@ import eligibility as E  # noqa: E402
 387 |  import candidates as CA  # noqa: E402
 388 |  import heimdall_health as HH  # noqa: E402
 389 |  import circuit_breaker as CB  # noqa: E402
 390 | +import deadline_table as DT  # noqa: E402
 391 |  import shadow86 as SH  # noqa: E402
 392 |  import ledger_build as LB  # noqa: E402
 393 |  import moments as M  # noqa: E402
 394 | @@ -104,12 +105,43 @@ def delivered_pins(paths):
 395 |  
 396 |  def build_router(routing, shadow, shadow_log):
 397 |      """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
 398 | -    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker."""
 399 | +    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
 400 | +    ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
 401 |      return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 402 |                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 403 |                      routing=routing, shadow=shadow, shadow_log=shadow_log,
 404 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
 405 | -                    breakers=CB.STATE)                                                         # ruling 99
 406 | +                    breakers=CB.STATE,                                                         # ruling 99
 407 | +                    deadlines=DT.load(DT.STATE, PL.REPLIES))                                   # ruling 100
 408 | +
 409 | +
 410 | +def applied(router):
 411 | +    """RULING 100: which rows of the deadline table the build's router uses (a deadline applies to the pair today:
 412 | +    a verdict role on a gateway with a configured deadline). -> applies(key)."""
 413 | +    def applies(key):
 414 | +        name, _, role = key.partition("|")
 415 | +        b = router.backends.get(name)
 416 | +        return b is not None and router.role_deadline(role, b) is not None
 417 | +    return applies
 418 | +
 419 | +
 420 | +def ruling_101_line(par):
 421 | +    """RULING 101 (12:16 Nov 14): the build's line on step A's order, with the extra spend when Grok's confirm ran in
 422 | +    parallel (its verdicts the second screen could not use: the dollars sequential would have saved). -> str or ""."""
 423 | +    if not par:
 424 | +        return ""
 425 | +    if par.get("parallel"):
 426 | +        asked = par.get("asked", 0) or 0
 427 | +        extra = (par.get("usd", 0) or 0) * (asked - (par.get("used", 0) or 0)) / max(1, asked)
 428 | +        return (f"  RULING 101 (step A in parallel): {par.get('n_new')} new moments; the filter ({par.get('leg')}) "
 429 | +                f"would have held the build about {(par.get('est_wait_s') or 0) / 60:.0f} min. Grok's confirm was asked "
 430 | +                f"on {asked} at once ({par.get('verdicts')} verdicts, ${par.get('usd', 0) or 0:.4f} vendor-reported); "
 431 | +                f"the second screen used {par.get('used')}, so about ${extra:.4f} was spent that sequential would have "
 432 | +                f"saved" + (f"; {par['error']}" if par.get("error") else ""))
 433 | +    wait = par.get("est_wait_s")
 434 | +    return (f"  RULING 101: step A sequential ({par.get('n_new')} new moments" +
 435 | +            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')})" if isinstance(wait, (int, float))
 436 | +             else f", not over {PK.STEP_A_PARALLEL_NEW})"))
 437 |  
 438 |  
 439 |  def main(argv=None):
 440 | @@ -207,6 +239,8 @@ def main(argv=None):
 441 |      router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 442 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 443 |          + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 444 | +    say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 445 | +        f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 446 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 447 |      if spent0 >= PL.LY_STOP_USD:
 448 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 449 | @@ -367,6 +401,9 @@ def main(argv=None):
 450 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 451 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 452 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 453 | +    line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
 454 | +    if line101:
 455 | +        say(line101)
 456 |      vis = res.get("visual") or {}
 457 |      say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
 458 |          f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
 459 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 460 | index fefacdc..bf25380 100644
 461 | --- a/tests/package/test_medley.py
 462 | +++ b/tests/package/test_medley.py
 463 | @@ -572,7 +572,9 @@ class Rig:
 464 |  
 465 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 466 |                    batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None, kind=None,
 467 | -                  failover=None):
 468 | +                  failover=None, plan_only=False):
 469 | +        if plan_only:                                      # ruling 101's plan: the moments new to the first screen
 470 | +            return [m for m in ms if m["moment_id"] in getattr(self, "plan_new", ())]
 471 |          self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
 472 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 473 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 474 | @@ -1257,6 +1259,25 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 475 |              self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
 476 |              self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict
 477 |  
 478 | +    def test_ruling_101_plan_only_lists_what_the_screen_would_ask_and_asks_nothing(self):
 479 | +        import tempfile
 480 | +        ms, srcs = self.pool(10)
 481 | +        calls = []
 482 | +        self.fake(calls)
 483 | +        ids = lambda xs: sorted(m["moment_id"] for m in xs)
 484 | +        with tempfile.TemporaryDirectory() as d:
 485 | +            cache = os.path.join(d, "STEP_A_CACHE.json")
 486 | +            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
 487 | +            self.assertEqual((ids(new), calls, os.path.exists(cache)), (ids(ms), [], False))   # all new, nothing asked
 488 | +            PK.prescreen(self.router(), ms[:6], srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # 6 paid for
 489 | +            calls.clear()
 490 | +            with open(cache) as f:
 491 | +                before = f.read()
 492 | +            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
 493 | +            self.assertEqual(ids(new), ids(ms[6:]))                       # only the 4 the cache does not hold
 494 | +            with open(cache) as f:
 495 | +                self.assertEqual((calls, f.read()), ([], before))         # nothing asked, nothing written
 496 | +
 497 |      def test_a_failed_batch_is_no_verdict_never_cached_and_says_why(self):
 498 |          import tempfile
 499 |          ms, srcs = self.pool(10)
 500 | @@ -2529,7 +2550,9 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 501 |  
 502 |      def test_ruling_85_the_first_screen_is_bounded_under_heimdall_first(self):
 503 |          """RULING 85: under heimdall_first the FIRST step-A verdict is a Heimdall family's, so it gets ruling 82's
 504 | -        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before."""
 505 | +        batch (2 clips a call) and fails over down the chain; RULING 100 (12:16 Nov 14): no flat deadline is passed,
 506 | +        each leg gets its own from the Router (role_deadline: its row of the deadline table, else the gateway's 120 s).
 507 | +        Under today's routing it stays unbounded (Grok's), as before."""
 508 |          batches = []
 509 |          for routing in ("today", "heimdall_first"):
 510 |              rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 511 | @@ -2542,10 +2565,129 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 512 |                  return pre(*a, batch=batch, **k)
 513 |              rig.prescreen = spy
 514 |              rig.run()
 515 | -            self.assertEqual(rig.screen_deadlines[0], None if routing == "today" else PK.SECOND_VERDICT_DEADLINE_S)
 516 | +            self.assertIsNone(rig.screen_deadlines[0])          # ruling 100: the Router decides per leg
 517 |          self.assertEqual([b for r, b in batches if r == "heimdall_first"][0], PK.SECOND_VERDICT_BATCH)
 518 | +        self.assertEqual(PK.first_bounds(type("R", (), {"routing": "heimdall_first"})()),
 519 | +                         {"batch": PK.SECOND_VERDICT_BATCH, "deadline_s": None, "failover": True})
 520 |          self.assertEqual([b for r, b in batches if r == "today"][0], PK.PRESCREEN_BATCH)
 521 |  
 522 | +    def test_ruling_101_the_plan_parallel_only_over_20_new_moments_and_10_minutes_of_filter(self):
 523 | +        """RULING 101 (12:16 Nov 14): parallel when the new moments are over 20 AND the filter would hold the build over
 524 | +        10 minutes: its rounds (batches over PRESCREEN_WORKERS) x the leading leg's own deadline (ruling 100), the leg
 525 | +        the first off the writers and not breaker-open; a leading leg with no deadline (Grok) is sequential."""
 526 | +        from unittest import mock
 527 | +
 528 | +        class B:
 529 | +            def __init__(self, vendor, family):
 530 | +                self.vendor, self.family = vendor, family
 531 | +
 532 | +        class R:
 533 | +            routing, down = "heimdall_first", {}
 534 | +
 535 | +            def __init__(self, open_=()):
 536 | +                self.backends = {"heimdall:glm": B("heimdall/glm", "glm"), "heimdall:ds": B("heimdall/deepseek",
 537 | +                                                                                          "deepseek"),
 538 | +                                 "xai:grok": B("xai", "grok")}
 539 | +                self.open_ = set(open_)
 540 | +
 541 | +            def chain(self, role, kind=None):
 542 | +                assert (role, kind) == ("context_verdict", "step_a_first")
 543 | +                return ["heimdall:glm", "heimdall:ds", "xai:grok"]
 544 | +
 545 | +            def role_deadline(self, role, b):
 546 | +                return {"glm": 60.0, "deepseek": 300.0}.get(b.family)
 547 | +
 548 | +            def breaker_open(self, name):
 549 | +                return name in self.open_
 550 | +
 551 | +        def plan(n, router, wv=(), wf=()):
 552 | +            new = [{"moment_id": f"m{i}"} for i in range(n)]
 553 | +            with mock.patch.object(PK, "prescreen", lambda *a, plan_only=False, **k: new if plan_only else None):
 554 | +                return PK.step_a_plan(router, [], {}, None, set(wv), set(wf), **PK.first_bounds(router))
 555 | +        p = plan(20, R())                                                  # under the line: nothing else consulted
 556 | +        self.assertEqual((p["parallel"], p["n_new"], p["est_wait_s"], p["leg"]), (False, 20, None, None))
 557 | +        p = plan(21, R())                                  # glm leads: 11 batches of 2, 2 rounds x 60 s = 2 minutes
 558 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 120.0, "heimdall:glm"))
 559 | +        p = plan(21, R(open_={"heimdall:glm"}))           # glm's breaker open: deepseek leads, 2 x 300 s = 10 minutes
 560 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 600.0, "heimdall:ds"))   # not OVER 10
 561 | +        p = plan(37, R(open_={"heimdall:glm"}))           # 19 batches, 4 rounds x 300 s = 20 minutes
 562 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (True, 1200.0, "heimdall:ds"))
 563 | +        p = plan(37, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # the writer's family: Grok leads,
 564 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 0.0, "xai:grok"))   # no deadline
 565 | +
 566 | +    def test_ruling_101_confirm_ahead_asks_off_every_heimdall_family_and_tallies_its_dollars(self):
 567 | +        from unittest import mock
 568 | +        import providers as P
 569 | +        hb = lambda name, fam: P.HeimdallBackend(name, {"model": fam, "family": fam, "base_url": "http://x"}, "/x")
 570 | +
 571 | +        class Rep:
 572 | +            def __init__(self, usd, reported):
 573 | +                self.usd, self.usage = usd, ({"usd_reported": reported} if reported is not None else {})
 574 | +
 575 | +        class R:
 576 | +            backends = {"heimdall:glm": hb("heimdall:glm", "glm"), "heimdall:ds": hb("heimdall:ds", "deepseek")}
 577 | +            replies = [Rep(0.5, 0.01), Rep(0.5, None)]
 578 | +
 579 | +            def call(self, *a, **k):
 580 | +                return self.replies.pop(0)
 581 | +        got = {}
 582 | +
 583 | +        def fake(router, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
 584 | +            got.update(wv=set(wv), wf=set(wf), kind=kind, n=n, cache=cache)
 585 | +            router.call("context_verdict", "p")
 586 | +            router.call("context_verdict", "q")
 587 | +            return {m["moment_id"]: {"backend": "xai:grok"} for m in new}, {}, set(), set()
 588 | +        with mock.patch.object(PK, "prescreen", fake):
 589 | +            res = PK.confirm_ahead(R(), [{"moment_id": "a"}, {"moment_id": "b"}], {}, None, {"openai"}, {"gpt"},
 590 | +                                   cache="/tmp/c")
 591 | +        self.assertEqual(got, {"wv": {"openai", "heimdall"}, "wf": {"gpt", "glm", "deepseek"}, "kind": "step_a_second",
 592 | +                               "n": 2, "cache": "/tmp/c"})       # off every Heimdall family and off the writers
 593 | +        self.assertEqual(res, {"asked": 2, "verdicts": 2, "usd": 0.51, "calls": 2,      # vendor-reported, else estimate
 594 | +                               "by": {"a": "xai:grok", "b": "xai:grok"}})
 595 | +
 596 | +    def test_ruling_101_in_a_build_grok_confirms_beside_the_filter_and_the_extra_is_reported(self):
 597 | +        """The plan says parallel: Grok's confirm (step_a_second) runs on every new moment ON ANOTHER THREAD while the
 598 | +        first screen runs; the second screen later reads the cache; the report counts what it used."""
 599 | +        import threading
 600 | +        from unittest import mock
 601 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 602 | +                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
 603 | +        rig.router.routing = "heimdall_first"
 604 | +        rig.plan_new = {m["moment_id"] for m in self.MS}
 605 | +        rig.router.chain = lambda role, kind=None: ["openai:gpt", "xai:grok"]   # the rig's writers are heimdall's:
 606 | +        rig.router.role_deadline = lambda role, b: 300.0 if b.vendor == "openai" else None   # a third vendor leads
 607 | +        rig.router.breaker_open = lambda name: False
 608 | +        seen, pre = [], rig.prescreen
 609 | +
 610 | +        def spy(router_, ms, sources_, ctx_, writer_vendor, *a, kind=None, plan_only=False, **k):
 611 | +            if not plan_only:
 612 | +                seen.append((kind, set(writer_vendor), threading.get_ident()))
 613 | +            return pre(router_, ms, sources_, ctx_, writer_vendor, *a, kind=kind, plan_only=plan_only, **k)
 614 | +        rig.prescreen = spy
 615 | +        with mock.patch.object(PK, "STEP_A_PARALLEL_NEW", 1), mock.patch.object(PK, "STEP_A_PARALLEL_WAIT_S", 60.0):
 616 | +            out = rig.run()
 617 | +        par = out["prescreen"]["parallel_101"]
 618 | +        self.assertEqual((par["parallel"], par["n_new"], par["asked"], par["leg"]),
 619 | +                         (True, len(self.MS), len(self.MS), "openai:gpt"))
 620 | +        main = threading.get_ident()
 621 | +        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall"}]   # off the writers (heimdall)
 622 | +        self.assertEqual(len(ahead), 1)                                   # Grok's confirm: once,
 623 | +        self.assertNotEqual(ahead[0], main)                               # on its own thread,
 624 | +        self.assertIn(("step_a_first", {"heimdall"}, main), seen)         # beside the filter on the build's thread
 625 | +        self.assertEqual(par["used"], 0)              # here every first verdict is Grok's own: the second screen
 626 | +        self.assertEqual(rig.screens[-1][0], "heimdall:deepseek")         # screens off it as before
 627 | +
 628 | +    def test_ruling_101_used_counts_only_a_verdict_off_the_first(self):
 629 | +        class B:
 630 | +            def __init__(self, vendor, family):
 631 | +                self.vendor, self.family = vendor, family
 632 | +        r = type("R", (), {"backends": {"heimdall:ds": B("heimdall/deepseek", "deepseek"), "xai:grok": B("xai", "grok"),
 633 | +                                        "heimdall:glm": B("heimdall/glm", "glm")}})()
 634 | +        a_by = {"a": {"backend": "heimdall:ds"}, "b": {"backend": "xai:grok"}, "c": {"backend": "heimdall:glm"},
 635 | +                "d": {"backend": "heimdall:ds"}}
 636 | +        pre_by = {"a": "xai:grok", "b": "xai:grok", "c": "xai:grok"}      # d: no verdict ahead
 637 | +        self.assertEqual(PK.prewarm_used(r, ["a", "b", "c", "d"], a_by, pre_by), 2)   # a and c; b is Grok's own
 638 | +
 639 |      def test_ruling_88_grok_confirms_in_its_own_batches_under_heimdall_first(self):
 640 |          """RULING 88 (c): under heimdall_first the second step-A verdict is Grok confirming Heimdall's passes: Grok's own
 641 |          batch (8) and no deadline, the move-on rule kept; under today it stays a Heimdall family's (2 clips, 120 s)."""
 642 | diff --git a/tests/providers/test_circuit_breaker.py b/tests/providers/test_circuit_breaker.py
 643 | index 3cf2f24..fb13f11 100644
 644 | --- a/tests/providers/test_circuit_breaker.py
 645 | +++ b/tests/providers/test_circuit_breaker.py
 646 | @@ -121,6 +121,31 @@ class TestBreaker(unittest.TestCase):
 647 |              self.rec("slow", at(51))
 648 |  
 649 |  
 650 | +class TestReadOnly(unittest.TestCase):
 651 | +    """RULING 101's estimate reads the breakers without touching them (is_open never claims a trial)."""
 652 | +
 653 | +    def test_is_open_reads_and_never_claims(self):
 654 | +        with tempfile.TemporaryDirectory() as d:
 655 | +            state = os.path.join(d, "BREAKERS.json")
 656 | +            self.assertFalse(CB.is_open(GLM, state, now=at(0)))                     # no state: closed
 657 | +            CB.record(GLM, "miss", state, now=at(0))
 658 | +            CB.record(GLM, "miss", state, now=at(1))                                 # open until 15:31
 659 | +            self.assertTrue(CB.is_open(GLM, state, now=at(30, 59)))
 660 | +            before = open(state).read()
 661 | +            self.assertFalse(CB.is_open(GLM, state, now=at(31)))                    # the window passed: a call may
 662 | +            self.assertEqual(open(state).read(), before)                            # try it, and nothing was claimed
 663 | +            self.assertEqual(CB.allow(GLM, state, now=at(31), hold_s=180.0), (True, "trial"))
 664 | +            self.assertTrue(CB.is_open(GLM, state, now=at(33, 59)))                 # its one trial in flight
 665 | +            self.assertFalse(CB.is_open(GLM, state, now=at(34)))
 666 | +            with open(state, "w") as f:
 667 | +                f.write("{ broken")
 668 | +            self.assertFalse(CB.is_open(GLM, state, now=at(35)))                    # unreadable: skips nothing
 669 | +            r = router(d, [Fake(GLM, "heimdall", answer="x", family="glm")], {"c": [GLM]}, breakers=state)
 670 | +            self.assertFalse(r.breaker_open(GLM))
 671 | +            r.breakers = None
 672 | +            self.assertFalse(r.breaker_open(GLM))
 673 | +
 674 | +
 675 |  class TestRouterBreaker(unittest.TestCase):
 676 |      """providers.Router: live calls only. Two real deadline misses (P._within) open the breaker, the next family leads,
 677 |      and the open is one line in the evidence file."""
 678 | diff --git a/tests/providers/test_deadline_table.py b/tests/providers/test_deadline_table.py
 679 | new file mode 100644
 680 | index 0000000..5733333
 681 | --- /dev/null
 682 | +++ b/tests/providers/test_deadline_table.py
 683 | @@ -0,0 +1,140 @@
 684 | +#!/usr/bin/env python3
 685 | +"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL (pipeline/deadline_table.py and its use in
 686 | +providers.Router.role_deadline and the ledger build). Offline: temporary record dirs and table files."""
 687 | +import json
 688 | +import os
 689 | +import sys
 690 | +import tempfile
 691 | +import unittest
 692 | +from datetime import datetime, timedelta, timezone
 693 | +from unittest import mock
 694 | +
 695 | +HERE = os.path.dirname(os.path.abspath(__file__))
 696 | +REPO = os.path.dirname(os.path.dirname(HERE))
 697 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 698 | +import deadline_table as DT  # noqa: E402
 699 | +import providers as P  # noqa: E402
 700 | +
 701 | +T0 = datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc)
 702 | +DS, GLM, GROK = "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash", "xai:grok-4.20-0309-reasoning"
 703 | +
 704 | +
 705 | +def records(d, rows):
 706 | +    """rows: [(backend, role, seconds)] -> one recorded exchange each, as providers.Router._record writes them."""
 707 | +    for i, (b, role, s) in enumerate(rows):
 708 | +        os.makedirs(os.path.join(d, f"{i:02x}"[-2:]), exist_ok=True)
 709 | +        with open(os.path.join(d, f"{i:02x}"[-2:], f"{i:064x}.json"), "w") as f:
 710 | +            json.dump({"role": role, "backend": b, "seconds": s, "text": "{}"}, f)
 711 | +
 712 | +
 713 | +class TestTable(unittest.TestCase):
 714 | +    def setUp(self):
 715 | +        self.d = tempfile.TemporaryDirectory()
 716 | +        self.rec = os.path.join(self.d.name, "replies")
 717 | +
 718 | +    def tearDown(self):
 719 | +        self.d.cleanup()
 720 | +
 721 | +    def test_p90_times_one_and_a_half_inside_60_to_300_s(self):
 722 | +        records(self.rec, [(DS, "context_verdict", s) for s in (100, 120, 140, 160, 180, 200, 220, 240, 260, 280)]
 723 | +                + [(GLM, "context_verdict", s) for s in (5, 9, 12)]
 724 | +                + [("heimdall:qwen/qwen3.8-27b", "context_verdict", s) for s in (30, 40, 50, 60)]
 725 | +                + [("heimdall:slow/x", "context_verdict", s) for s in (400, 500, 600)]
 726 | +                + [(GROK, "coherence_verdict", s) for s in (10, 20)])          # two answers: no row of its own
 727 | +        t = DT.compute(self.rec, T0)
 728 | +        r = t["rows"]
 729 | +        self.assertEqual(r[f"{DS}|context_verdict"], {"n": 10, "p50": 190.0, "p90": 262.0, "deadline_s": 300.0})
 730 | +        self.assertEqual(r[f"{GLM}|context_verdict"]["deadline_s"], 60.0)                  # the floor
 731 | +        self.assertEqual(r["heimdall:qwen/qwen3.8-27b|context_verdict"]["deadline_s"], 85.5)   # 57 x 1.5
 732 | +        self.assertEqual(r["heimdall:slow/x|context_verdict"]["deadline_s"], 300.0)          # the ceiling
 733 | +        self.assertNotIn(f"{GROK}|coherence_verdict", r)                                       # under MIN_N
 734 | +        self.assertEqual((t["computed_at"], DT.deadline(t, DS, "context_verdict"), DT.deadline(t, GROK, "x")),
 735 | +                         ("2026-11-14T17:00:00Z", 300.0, None))
 736 | +
 737 | +    def test_a_record_that_cannot_be_read_or_has_no_positive_time_is_skipped(self):
 738 | +        records(self.rec, [(DS, "context_verdict", s) for s in (10, 20, 30)] +
 739 | +                [(DS, "context_verdict", bad) for bad in (0, -5, None, "slow", True)])
 740 | +        os.makedirs(os.path.join(self.rec, "zz"), exist_ok=True)
 741 | +        with open(os.path.join(self.rec, "zz", "broken.json"), "w") as f:
 742 | +            f.write("{ broken")
 743 | +        with open(os.path.join(self.rec, "zz", "nan.json"), "w") as f:
 744 | +            f.write('{"role": "context_verdict", "backend": "%s", "seconds": NaN}' % DS)
 745 | +        self.assertEqual(DT.compute(self.rec, T0)["rows"][f"{DS}|context_verdict"]["n"], 3)
 746 | +        self.assertEqual(DT.deadline({"rows": {"a|b": {"deadline_s": "60"}}}, "a", "b"), None)   # no guess
 747 | +        self.assertEqual(DT.deadline(None, "a", "b"), None)
 748 | +
 749 | +    def test_the_table_is_kept_a_day_then_recomputed_and_an_unreadable_one_is_recomputed(self):
 750 | +        path = os.path.join(self.d.name, "TABLE.json")
 751 | +        records(self.rec, [(DS, "context_verdict", s) for s in (100, 110, 120)])
 752 | +        first = DT.load(path, self.rec, T0)
 753 | +        self.assertTrue(os.path.exists(path))
 754 | +        records(self.rec, [(DS, "context_verdict", s) for s in (10, 10, 10, 10, 10, 10, 10)])
 755 | +        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=23)), first)          # within the day: kept
 756 | +        again = DT.load(path, self.rec, T0 + timedelta(hours=24, seconds=1))                # a day later: the records
 757 | +        self.assertNotEqual(again["rows"], first["rows"])
 758 | +        self.assertEqual(again["computed_at"], "2026-11-15T17:00:01Z")
 759 | +        with open(path, "w") as f:
 760 | +            f.write("{ broken")
 761 | +        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=25))["computed_at"], "2026-11-15T18:00:00Z")
 762 | +        self.assertIn("deepseek-v4.1-flash context_verdict:", DT.text(again))
 763 | +        self.assertEqual(DT.text(again, applies=lambda k: False), "")
 764 | +
 765 | +
 766 | +class TestRouter(unittest.TestCase):
 767 | +    """providers.Router.role_deadline: the pair's own deadline where a deadline applies today; the gateway's number
 768 | +    without a row; none where none applies (Grok, a non-verdict role)."""
 769 | +
 770 | +    def router(self, table):
 771 | +        d = tempfile.mkdtemp()
 772 | +        cfg = os.path.join(d, "cfg.json")
 773 | +        json.dump({"schema": "pp.providers/1",
 774 | +                   "backends": {DS: {"vendor": "heimdall", "model": "deepseek", "family": "deepseek",
 775 | +                                     "base_url": "http://x"},
 776 | +                                GLM: {"vendor": "heimdall", "model": "glm", "family": "glm", "base_url": "http://x"},
 777 | +                                GROK: {"vendor": "xai", "model": "grok", "family": "grok"}},
 778 | +                   "roles": {"context_verdict": {"chain": [GLM, DS, GROK]}},
 779 | +                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
 780 | +                               "verdict_deadline_s": {"heimdall": 120}}}, open(cfg, "w"))
 781 | +        return P.Router(cfg, env_path="/nonexistent", deadlines=table)
 782 | +
 783 | +    def test_the_model_s_own_deadline_where_one_applies(self):
 784 | +        table = {"rows": {f"{DS}|context_verdict": {"n": 33, "p50": 165, "p90": 272, "deadline_s": 300.0},
 785 | +                          f"{GROK}|context_verdict": {"n": 268, "p50": 46, "p90": 80, "deadline_s": 120.7}}}
 786 | +        r = self.router(table)
 787 | +        self.assertEqual(r.role_deadline("context_verdict", r.backends[DS]), 300.0)     # its own row
 788 | +        self.assertEqual(r.role_deadline("context_verdict", r.backends[GLM]), 120.0)    # no row: the gateway's
 789 | +        self.assertIsNone(r.role_deadline("context_verdict", r.backends[GROK]))        # none applies today, row or not
 790 | +        self.assertIsNone(r.role_deadline("angle_write", r.backends[DS]))              # not a verdict role
 791 | +        self.assertEqual(self.router(None).role_deadline("context_verdict", r.backends[DS]), 120.0)   # no table
 792 | +
 793 | +    def test_the_build_router_loads_the_table_from_its_own_records(self):
 794 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 795 | +        import proof_ledger as PLG
 796 | +        import proof_ly as PL
 797 | +        with tempfile.TemporaryDirectory() as d:
 798 | +            path = os.path.join(d, "DEADLINE_TABLE.json")
 799 | +            with mock.patch.object(DT, "STATE", path):
 800 | +                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 801 | +            self.assertTrue(os.path.exists(path))
 802 | +            self.assertEqual(r.deadlines, DT.load(path, PL.REPLIES))
 803 | +        app = PLG.applied(r)
 804 | +        self.assertFalse(app(f"{GROK}|context_verdict"))                                # Grok: none applies
 805 | +        self.assertTrue(app("heimdall:deepseek/deepseek-v4.1-flash|context_verdict"))
 806 | +
 807 | +
 808 | +class TestTheBuildLine(unittest.TestCase):
 809 | +    def test_ruling_101_s_line_reports_the_extra_spend(self):
 810 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 811 | +        import proof_ledger as PLG
 812 | +        self.assertEqual(PLG.ruling_101_line(None), "")
 813 | +        line = PLG.ruling_101_line({"parallel": True, "n_new": 37, "leg": DS, "est_wait_s": 1200.0, "asked": 37,
 814 | +                                    "verdicts": 36, "usd": 0.37, "used": 10})
 815 | +        self.assertIn("would have held the build about 20 min", line)
 816 | +        self.assertIn("the second screen used 10, so about $0.2700 was spent that sequential would have saved", line)
 817 | +        self.assertIn("about 2.0 min on", PLG.ruling_101_line({"parallel": False, "n_new": 21, "est_wait_s": 120.0,
 818 | +                                                               "leg": GLM}))
 819 | +        self.assertIn("not over 20", PLG.ruling_101_line({"parallel": False, "n_new": 4, "est_wait_s": None}))
 820 | +
 821 | +
 822 | +if __name__ == "__main__":
 823 | +    unittest.main()
 824 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- providers.Router.call walks a role's chain of model back-ends. A live call on a leg gets a deadline (the caller's
  deadline_s, else Router.role_deadline(role, backend)); at the deadline the leg is abandoned and the chain moves on.
  Ruling 99's circuit breaker skips a model for 30 minutes after it misses its deadline twice in a row.
- STEP A (law L-s) screens each moment's own context twice: the FIRST screen (package.prescreen, kind step_a_first,
  chain heimdall_first = [glm, deepseek, Grok], 2 clips a call) on every usable moment; later, on the moments that
  cleared, were cuttable and passed the hook rules, the SECOND screen (package.second_screen: kind step_a_second,
  chain [Grok, glm, deepseek], 8 clips a call) for a verdict OFF the first verdict's vendor and family. A clip passes
  only if BOTH pass. Verdicts are cached across builds in a shared step-A cache keyed by moment, text, context and
  prompt version, per back-end.
- Before this change: under heimdall_first the first screen passed an explicit flat deadline of 120 s
  (first_bounds -> SECOND_VERDICT_DEADLINE_S), and every other Heimdall verdict call got the gateway's 120 s
  (role_deadline). deepseek's recorded step A answers take median 165 s, p90 272 s (33 answers), so it "missed" its
  deadline on normal calls, its breaker opened, and at 12:24 and 12:40 ET two spotlight candidates with hooks rated
  4 died at the second screen with every leg unavailable (Grok was their first verdict's own vendor, glm's and
  deepseek's breakers open).

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.Router.call: `dl = deadline_s or self.role_deadline(role, b)` per leg; a recorded reply is served before
  any deadline or breaker applies; replay never makes a live call.
- package.prescreen (:494) builds each moment's context and cache key, takes a verdict from this build's store or the
  shared cache when one exists off the given writer vendor/family, and asks the rest in batches on PRESCREEN_WORKERS
  (6) threads. The cache is merged by _cache_put (:475) under CACHE_LOCK (:456), re-reading the file inside the lock,
  so two prescreens in one process cannot lose each other's verdicts.
- package.second_screen (:682) calls prescreen per group with writer sets = the FIRST verdict's (vendor, family) and
  kind step_a_second; through the cache lookup it reuses a cached verdict from any back-end off those sets.
- package._writers(router) returns the angle writer's (vendor, family); step A never runs on it.
- Under heimdall_first each Heimdall family is its own vendor ("heimdall/deepseek", "heimdall/glm"; ruling 85).

THE ORCHESTRATOR'S RULINGS (12:16 ET Nov 14), verbatim:
"100. DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. My 120 s (ruling 82) sits on top of deepseek's NORMAL step A time
(about 105 s recorded), so the breaker opened on a healthy model and Grok decided step A alone again. Per (model,
verdict type) the deadline is the recorded p90 of that pair's answered calls x 1.5, floor 60 s, ceiling 300 s,
recomputed from the records daily (say the table on STATE once). The breaker's 'two misses in a row' is against THAT
deadline. glm's recorded step A median was 45 s, so its 483-532 s today still trips it; deepseek at 105 s does not.
Close deepseek's breaker now by this rule.
101. STEP A ORDER WHILE HEIMDALL IS SLOW: the filter is worth its wait only if it saves more than it costs. Rule: step
A asks the Heimdall filter and Grok's confirm IN PARALLEL when the pool to screen is over 20 new moments and a build
would otherwise wait more than 10 minutes on the filter; a clip passes only if BOTH pass (unchanged); Grok's call is
then not saved, and you report the extra spend per build. Under 20 new moments, sequential as ruled (Heimdall first,
Grok only on a pass). Time to a video comes before the 18 cents."

THE CHANGE (the diff follows):
1. pipeline/deadline_table.py (new): from the build's recorded exchanges (one JSON per ANSWERED call: backend, role,
   seconds), per (backend, role) with at least MIN_N = 3 answers: p50, p90 and deadline = clamp(1.5 x p90, 60, 300).
   Saved with computed_at; load() reuses it for a day, else (or when unreadable) recomputes and saves.
   Measured now (the rows a Router applies): deepseek step A 300 s (n 33, p90 272); deepseek coherence 213 s; qwen step
   A 67 s; qwen coherence 60 s; glm step A 60 s (n 3, p90 39).
2. providers.Router(deadlines=table). role_deadline: where a deadline applies today (a verdict role on a gateway with
   a configured deadline: Heimdall), the pair's own row if it has one, else the gateway's 120 s; where none applies
   (Grok, a non-verdict role) none applies now, row or not. Router.breaker_open(name): a READ-ONLY breaker check
   (circuit_breaker.is_open, new: it never claims a trial).
3. package.first_bounds under heimdall_first: no flat deadline (deadline_s None, failover True, 2 clips a call kept),
   so each leg gets its own deadline from the Router.
4. Ruling 101 in package.build:
   - step_a_plan(): the moments NEW to the first screen (prescreen(plan_only=True): no verdict in the store or the
     cache; nothing asked, nothing written). Over STEP_A_PARALLEL_NEW (20) new, the estimated filter wait is rounds
     (ceil(new / batch) / PRESCREEN_WORKERS, rounded up) x the deadline of the filter's leading leg: the first leg of
     the step_a_first chain off the writers, not down this run and not breaker-open. The plan is parallel when that
     wait is over STEP_A_PARALLEL_WAIT_S (600 s); a leading leg with no deadline (Grok) is sequential.
   - When parallel, confirm_ahead() runs on its own thread BESIDE the first screen: prescreen(kind step_a_second) on
     every new moment with every Heimdall vendor and family added to the writer sets (so only a non-Heimdall leg, Grok,
     answers), into the shared cache. The later second screen is unchanged; it reads those verdicts from the cache
     where they are off the first verdict's vendor and family (a moment whose first verdict was Grok's own is
     screened off it as before).
   - The spend is tallied through a router view (_Tally: vendor-reported dollars, else the estimate).
     prewarm_used() counts the verdicts the second screen could use. The build prints the extra spend
     (usd x unused / asked) per build (proof_ledger.ruling_101_line).
5. tests/package/proof_ledger.py: the build router loads the table (DT.load, from its own record dir) and prints the
   rows it applies; the ruling-101 line per build.
6. Tests: test_deadline_table.py (new, 6), test_circuit_breaker.py (+1), test_medley.py (+5, one updated: the first
   screen passes no flat deadline). 22 mutations, each killed; 22 suites, 590 tests.

ATTACK:
(a) Ruling 100: can a pair's deadline come out under 60 or over 300? Can a row apply where no deadline applied before
    (Grok) or vanish where one did? A pair with 1-2 answers? A stale or unreadable table? Does the breaker now measure
    deepseek against 300 s, and glm against 60 s?
(b) The first screen with no flat deadline: can any leg now wait unbounded where it was bounded before? Failover kept?
(c) Ruling 101: can a clip now pass with only ONE screen's pass? Can the confirm-ahead's verdict be used against its own
    vendor (same vendor twice)? Can the two prescreens running at once corrupt the cache or the store? Is "new
    moments" counted right (cached ones excluded)? Is the 10-minute estimate sound, and what if the leading leg's
    breaker opens mid-build? Is the extra spend reported honestly?
(d) Anything else that could seal a wrong pin, starve a build, or spend past ruling 48's cap.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

