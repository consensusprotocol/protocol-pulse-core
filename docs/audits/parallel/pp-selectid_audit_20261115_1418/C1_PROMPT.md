# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1418
# Branch: pp-selectid
# Generated: 2026-11-15 14:18 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1418/C1_STEP.diff (371 lines)
```
   1 | diff --git a/tests/package/replay114.py b/tests/package/replay114.py
   2 | new file mode 100644
   3 | index 0000000..d830c13
   4 | --- /dev/null
   5 | +++ b/tests/package/replay114.py
   6 | @@ -0,0 +1,232 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 114 (orchestrator 13:18 ET Nov 15): V4 ON AN XINFER WORKER. The Heimdall team: the unclosed JSON is "the
   9 | +usual vllm schema problem; the xinfer workers don't have this issue", and a request carrying the HTTP header
  10 | +x-bf-tunnel-instance: pinga282 goes to an xinfer worker IF the gateway forwards the header.
  11 | +(a) 30 of the 93 records that came back unclosed ("truncated") in replay111, the five the team was sent among them
  12 | +    (out_tokens 7, 122, 171, 497, 1564), asked exactly as replay111 asked them (replay111.FormatBackend: the v4
  13 | +    abliterated, response_format json_object, reasoning_effort none; the record's own max_tokens, seed and system),
  14 | +    ONCE WITH the header and ONCE WITHOUT, at the same seed. The legs alternate which goes first.
  15 | +(b) Per call: finish_reason, the response's id, EVERY response header, out_tokens, seconds, the answer's shape
  16 | +    (closed JSON, or replay111.shape) and its text (diagnosis only, never a verdict). Our own request's headers are
  17 | +    NEVER recorded (the Authorization is among them): a row says only whether the x-bf header was sent.
  18 | +(c) REPORT.md: unclosed with / without the header; the response headers that differ between the legs (an instance
  19 | +    name would show there); finish_reason counts for the unclosed answers.
  20 | +SPEND: Heimdall only, vendor-reported (usage.cost), on its own ledger SPEND_R114.json; no call starts once it holds
  21 | +STOP_USD ($0.14 of the order's $0.15). One call at a time. No routing change: nothing here is read by a build.
  22 | +Usage: python3 -B tests/package/replay114.py [--n 30] [--report-only]"""
  23 | +import argparse
  24 | +import collections
  25 | +import contextlib
  26 | +import json
  27 | +import os
  28 | +import sys
  29 | +import time
  30 | +import urllib.error
  31 | +import urllib.request
  32 | +
  33 | +HERE = os.path.dirname(os.path.abspath(__file__))
  34 | +REPO = os.path.dirname(os.path.dirname(HERE))
  35 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  36 | +sys.path.insert(0, HERE)
  37 | +import providers as P  # noqa: E402
  38 | +import replay111 as RY  # noqa: E402
  39 | +
  40 | +WT = RY.WT
  41 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay114")
  42 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R114.json")
  43 | +SOURCE = os.path.join(RY.OUT, "OUT_OF_CONTRACT.jsonl")
  44 | +HEADER = {"x-bf-tunnel-instance": "pinga282"}
  45 | +NAMED = (7, 122, 171, 497, 1564)
  46 | +N, STOP_USD = 30, 0.14
  47 | +
  48 | +
  49 | +def unclosed(path=SOURCE):
  50 | +    """replay111's unclosed answers: its out-of-contract rows of shape "truncated"."""
  51 | +    with open(path) as f:
  52 | +        return [r for r in map(json.loads, f) if r.get("shape") == "truncated"]
  53 | +
  54 | +
  55 | +def pick(rows, n=N, named=NAMED):
  56 | +    """One record for each named out_tokens first, then the others spread evenly in out_tokens order (ties by record)."""
  57 | +    rows = sorted(rows, key=lambda r: (r.get("out_tokens") or 0, r["record"]))
  58 | +    first = []
  59 | +    for t in named:
  60 | +        hit = [r for r in rows if r.get("out_tokens") == t]
  61 | +        if not hit:
  62 | +            raise ValueError(f"no unclosed record with out_tokens {t}")
  63 | +        first.append(hit[0])
  64 | +    rest = [r for r in rows if r not in first]
  65 | +    k = min(n - len(first), len(rest))
  66 | +    return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
  67 | +
  68 | +
  69 | +class Capture:
  70 | +    """providers._http_json for one call, with `extra` headers added; it keeps the RESPONSE's status, id, finish_reason,
  71 | +    usage and every header (an HTTP error's too). The request's own headers are never kept."""
  72 | +
  73 | +    def __init__(self, extra):
  74 | +        self.extra, self.seen = dict(extra), {}
  75 | +
  76 | +    def __call__(self, url, body, headers, timeout):
  77 | +        req = urllib.request.Request(url, data=json.dumps(body).encode(),
  78 | +                                     headers={"Content-Type": "application/json", **headers, **self.extra})
  79 | +        try:
  80 | +            with urllib.request.urlopen(req, timeout=timeout) as resp:
  81 | +                raw = resp.read()
  82 | +                self.seen = {"status": resp.status, "response_headers": dict(resp.headers.items())}
  83 | +        except urllib.error.HTTPError as e:
  84 | +            self.seen = {"status": e.code, "response_headers": dict((e.headers or {}).items())}
  85 | +            raise
  86 | +        j = json.loads(raw)
  87 | +        ch = ((j.get("choices") or [{}])[0] or {}) if isinstance(j, dict) else {}
  88 | +        self.seen.update(id=j.get("id"), finish_reason=ch.get("finish_reason"), usage=j.get("usage"),
  89 | +                         response_model=j.get("model"))
  90 | +        return j
  91 | +
  92 | +
  93 | +@contextlib.contextmanager
  94 | +def capturing(extra):
  95 | +    real, cap = P._http_json, Capture(extra)
  96 | +    P._http_json = cap
  97 | +    try:
  98 | +        yield cap
  99 | +    finally:
 100 | +        P._http_json = real
 101 | +
 102 | +
 103 | +def shape_of(text, out_tokens, cap):
 104 | +    t = (text or "").strip()
 105 | +    try:
 106 | +        json.loads(t)
 107 | +        return "closed JSON"
 108 | +    except ValueError:
 109 | +        return RY.shape(text, out_tokens, cap)
 110 | +
 111 | +
 112 | +def ask(backend, rec, leg):
 113 | +    """One call of `rec` on the v4 backend, leg "with" (the header) or "without" -> its row."""
 114 | +    mt, seed = int(rec.get("max_tokens") or 2000), int(rec.get("seed") or 7)
 115 | +    row = {"leg": leg, "x_bf_header_sent": leg == "with", "seed": seed, "max_tokens": mt}
 116 | +    t0 = time.time()
 117 | +    with capturing(HEADER if leg == "with" else {}) as cap:
 118 | +        try:
 119 | +            text, usage, secs = backend.complete(rec["prompt"], mt, seed, system=rec.get("system"))
 120 | +        except Exception as e:                            # noqa: BLE001  any failure is a row, never the run's end
 121 | +            row.update(seconds=round(time.time() - t0, 2), error=f"{type(e).__name__}: {str(e)[:200]}", **cap.seen)
 122 | +            return row
 123 | +    u = cap.seen.get("usage") or {}
 124 | +    out = int(u.get("completion_tokens") or usage.get("out") or 0)
 125 | +    row.update(seconds=round(secs, 2), **cap.seen, out_tokens=out, usd_reported=usage.get("usd_reported"),
 126 | +               shape=shape_of(text, out, backend.max_out(mt)), text=text[:6000])
 127 | +    row["unclosed"] = row["shape"] == "truncated"
 128 | +    return row
 129 | +
 130 | +
 131 | +def spent(path=None):
 132 | +    """The ledger's vendor-reported total (SPEND, read when called)."""
 133 | +    try:
 134 | +        with open(path or SPEND) as f:
 135 | +            return float(json.load(f).get("usd_reported") or 0.0)
 136 | +    except (OSError, ValueError):
 137 | +        return 0.0
 138 | +
 139 | +
 140 | +def add_spend(usd, path=None):
 141 | +    path = path or SPEND
 142 | +    d = {"usd_reported": round(spent(path) + float(usd or 0.0), 8)}
 143 | +    with open(path + ".tmp", "w") as f:
 144 | +        json.dump(d, f)
 145 | +    os.replace(path + ".tmp", path)
 146 | +
 147 | +
 148 | +def backend():
 149 | +    r = RY.build_router(("none",), spend_path=None)
 150 | +    return r.backends[RY.bname("none")]
 151 | +
 152 | +
 153 | +def run(n=N, b=None, stop_usd=STOP_USD, results=None):
 154 | +    results = results or os.path.join(OUT, "RESULTS.jsonl")
 155 | +    os.makedirs(os.path.dirname(results), exist_ok=True)
 156 | +    b = b or backend()
 157 | +    done = set()
 158 | +    if os.path.exists(results):
 159 | +        with open(results) as f:
 160 | +            done = {(x["record"], x["leg"]) for x in map(json.loads, f)}
 161 | +    for i, src in enumerate(pick(unclosed(), n)):
 162 | +        with open(os.path.join(WT, src["record"])) as f:
 163 | +            rec = json.load(f)
 164 | +        for leg in (("with", "without") if i % 2 == 0 else ("without", "with")):
 165 | +            if (src["record"], leg) in done:
 166 | +                continue
 167 | +            if spent() >= stop_usd:
 168 | +                print(f"replay114: stopped at ${spent():.4f} (stop ${stop_usd:.2f})", flush=True)
 169 | +                return
 170 | +            row = dict(ask(b, rec, leg), record=src["record"], type=src["type"],
 171 | +                       replay111_out_tokens=src.get("out_tokens"), order=i)
 172 | +            add_spend(row.get("usd_reported"))
 173 | +            with open(results, "a") as f:
 174 | +                f.write(json.dumps(row) + "\n")
 175 | +            print(f"  {i + 1}/{n} {leg}: {row.get('shape') or row.get('error')}, {row.get('finish_reason')}, "
 176 | +                  f"{row.get('out_tokens')} tokens, {row.get('seconds')} s; ${spent():.4f}", flush=True)
 177 | +
 178 | +
 179 | +def report(results=None):
 180 | +    results = results or os.path.join(OUT, "RESULTS.jsonl")
 181 | +    with open(results) as f:
 182 | +        rows = [json.loads(x) for x in f]
 183 | +    legs = {lg: [r for r in rows if r["leg"] == lg] for lg in ("with", "without")}
 184 | +    pairs = {}
 185 | +    for r in rows:
 186 | +        pairs.setdefault(r["record"], {})[r["leg"]] = r
 187 | +    keys = collections.Counter()
 188 | +    for p in pairs.values():
 189 | +        if len(p) == 2:
 190 | +            a, b = p["with"].get("response_headers") or {}, p["without"].get("response_headers") or {}
 191 | +            keys.update(k.lower() for k in set(a) | set(b) if a.get(k) != b.get(k))
 192 | +    bf = sorted({k for r in rows for k in (r.get("response_headers") or {}) if k.lower().startswith("x-bf")})
 193 | +    s = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "records": len(pairs), "calls": len(rows),
 194 | +         "usd_reported": round(sum(float(r.get("usd_reported") or 0) for r in rows), 6)}
 195 | +    for lg, rs in legs.items():
 196 | +        s[lg] = {"calls": len(rs), "errors": sum(1 for r in rs if r.get("error")),
 197 | +                 "unclosed": sum(1 for r in rs if r.get("unclosed")),
 198 | +                 "shapes": dict(collections.Counter(r.get("shape") or "error" for r in rs)),
 199 | +                 "finish_reason_unclosed": dict(collections.Counter(str(r.get("finish_reason"))
 200 | +                                                                    for r in rs if r.get("unclosed"))),
 201 | +                 "finish_reason_all": dict(collections.Counter(str(r.get("finish_reason")) for r in rs)),
 202 | +                 "response_models": dict(collections.Counter(str(r.get("response_model")) for r in rs))}
 203 | +    s["headers_differing_within_a_pair"] = dict(keys.most_common())
 204 | +    s["x_bf_response_headers"] = bf
 205 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 206 | +        json.dump(s, f, indent=1)
 207 | +    w, wo = s["with"], s["without"]
 208 | +    L = ["# RULING 114: V4 ON AN XINFER WORKER (the x-bf-tunnel-instance header)", "",
 209 | +         f"{RY.MODEL}, response_format json_object, reasoning_effort none, each record's own max_tokens / seed / "
 210 | +         f"system (as replay111). {s['records']} of replay111's 93 unclosed records, each asked WITH the header "
 211 | +         f"`x-bf-tunnel-instance: pinga282` and WITHOUT it, the same seed. ${s['usd_reported']:.4f} reported.", "",
 212 | +         "| | calls | errors | unclosed | finish_reason of the unclosed | shapes |", "|---|---|---|---|---|---|",
 213 | +         f"| with the header | {w['calls']} | {w['errors']} | {w['unclosed']} | {w['finish_reason_unclosed']} | "
 214 | +         f"{w['shapes']} |",
 215 | +         f"| without | {wo['calls']} | {wo['errors']} | {wo['unclosed']} | {wo['finish_reason_unclosed']} | "
 216 | +         f"{wo['shapes']} |", "",
 217 | +         f"- x-bf-* response headers seen: {bf or 'none'}.",
 218 | +         f"- Response headers whose value differs between the two legs of a record (count of records): "
 219 | +         f"{s['headers_differing_within_a_pair'] or 'none'}.",
 220 | +         f"- The model each response names: with {w['response_models']}; without {wo['response_models']}."]
 221 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 222 | +        f.write("\n".join(L) + "\n")
 223 | +    return s
 224 | +
 225 | +
 226 | +def main(argv=None):
 227 | +    ap = argparse.ArgumentParser()
 228 | +    ap.add_argument("--n", type=int, default=N)
 229 | +    ap.add_argument("--report-only", action="store_true")
 230 | +    a = ap.parse_args(argv)
 231 | +    if not a.report_only:
 232 | +        run(a.n)
 233 | +    print(json.dumps(report(), indent=1))
 234 | +    return 0
 235 | +
 236 | +
 237 | +if __name__ == "__main__":
 238 | +    sys.exit(main())
 239 | diff --git a/tests/package/test_replay114.py b/tests/package/test_replay114.py
 240 | new file mode 100644
 241 | index 0000000..ecd606f
 242 | --- /dev/null
 243 | +++ b/tests/package/test_replay114.py
 244 | @@ -0,0 +1,126 @@
 245 | +#!/usr/bin/env python3
 246 | +"""RULING 114: the x-bf-tunnel-instance replay (tests/package/replay114.py). Offline: urlopen is replaced by a fake
 247 | +gateway; the key is a fake one; files go to a temporary directory."""
 248 | +import io
 249 | +import json
 250 | +import os
 251 | +import sys
 252 | +import tempfile
 253 | +import unittest
 254 | +from email.message import Message
 255 | +from unittest import mock
 256 | +
 257 | +HERE = os.path.dirname(os.path.abspath(__file__))
 258 | +sys.path.insert(0, HERE)
 259 | +import replay114 as RT  # noqa: E402
 260 | +
 261 | +KEY = "sk-FAKE-KEY-never-in-a-row"
 262 | +
 263 | +
 264 | +class Gateway:
 265 | +    """A fake Heimdall: answers each request from `answers` (text, finish_reason), with response headers that name the
 266 | +    instance (x-bf-instance) by whether the request carried the header; it keeps every request it saw."""
 267 | +
 268 | +    def __init__(self, answers):
 269 | +        self.answers, self.seen = list(answers), []
 270 | +
 271 | +    def __call__(self, req, timeout=None):
 272 | +        self.seen.append({"headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data)})
 273 | +        text, fin = self.answers.pop(0)
 274 | +        sent = "x-bf-tunnel-instance" in self.seen[-1]["headers"]
 275 | +        h = Message()
 276 | +        h["x-bf-instance"] = "pinga282" if sent else "vllm-7"
 277 | +        h["content-type"] = "application/json"
 278 | +        body = {"id": f"chatcmpl-{len(self.seen)}", "model": "deepseek/deepseek-v4-flash-0731-abliterated",
 279 | +                "choices": [{"message": {"content": text}, "finish_reason": fin}],
 280 | +                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.0001}}
 281 | +        r = io.BytesIO(json.dumps(body).encode())
 282 | +        r.status, r.headers = 200, h
 283 | +        return r
 284 | +
 285 | +
 286 | +def rec():
 287 | +    return {"prompt": "Judge it.", "max_tokens": 1200, "seed": 28, "system": "Be brief."}
 288 | +
 289 | +
 290 | +class TestPick(unittest.TestCase):
 291 | +    def test_the_named_five_first_then_spread_and_refused_without_one(self):
 292 | +        rows = [{"record": f"r{i:03d}", "type": "t", "out_tokens": t, "shape": "truncated"}
 293 | +                for i, t in enumerate([7, 122, 171, 497, 1564] + list(range(200, 1200, 10)))]
 294 | +        got = RT.pick(rows, 30)
 295 | +        self.assertEqual([r["out_tokens"] for r in got[:5]], [7, 122, 171, 497, 1564])
 296 | +        self.assertEqual(len({r["record"] for r in got}), 30)
 297 | +        self.assertLess(got[5]["out_tokens"], got[-1]["out_tokens"])           # spread over the out_tokens order
 298 | +        with self.assertRaises(ValueError):
 299 | +            RT.pick([r for r in rows if r["out_tokens"] != 497], 30)
 300 | +
 301 | +
 302 | +class TestAsk(unittest.TestCase):
 303 | +    def setUp(self):
 304 | +        self.b = RT.backend()
 305 | +        self.b.key = lambda name: KEY
 306 | +
 307 | +    def test_the_header_only_on_its_leg_the_same_request_otherwise_and_no_key_in_a_row(self):
 308 | +        g = Gateway([('{"a": 1', "length"), ('{"a": 1}', "stop")])
 309 | +        with mock.patch("urllib.request.urlopen", g):
 310 | +            w = RT.ask(self.b, rec(), "with")
 311 | +            wo = RT.ask(self.b, rec(), "without")
 312 | +        self.assertEqual(g.seen[0]["headers"].get("x-bf-tunnel-instance"), "pinga282")
 313 | +        self.assertNotIn("x-bf-tunnel-instance", g.seen[1]["headers"])
 314 | +        self.assertEqual(g.seen[0]["body"], g.seen[1]["body"])                     # the same request, same seed
 315 | +        body = g.seen[0]["body"]
 316 | +        self.assertEqual((body["seed"], body["response_format"], body["reasoning_effort"], body["model"]),
 317 | +                         (28, {"type": "json_object"}, "none", "deepseek/deepseek-v4-flash-0731-abliterated"))
 318 | +        self.assertEqual((w["finish_reason"], w["id"], w["out_tokens"], w["shape"], w["unclosed"]),
 319 | +                         ("length", "chatcmpl-1", 50, "truncated", True))
 320 | +        self.assertEqual((wo["shape"], wo["unclosed"], wo["response_headers"]["x-bf-instance"]),
 321 | +                         ("closed JSON", False, "vllm-7"))
 322 | +        for row in (w, wo):
 323 | +            s = json.dumps(row)
 324 | +            self.assertNotIn(KEY, s)
 325 | +            self.assertNotIn("Bearer", s)
 326 | +            self.assertNotIn("authorization", s.lower())
 327 | +
 328 | +    def test_a_failed_call_is_a_row_with_the_responses_headers(self):
 329 | +        import urllib.error
 330 | +
 331 | +        def refuse(req, timeout=None):
 332 | +            h = Message()
 333 | +            h["x-bf-instance"] = "gw-1"
 334 | +            raise urllib.error.HTTPError(req.full_url, 400, "bad", h, io.BytesIO(b"{}"))
 335 | +        with mock.patch("urllib.request.urlopen", refuse):
 336 | +            row = RT.ask(self.b, rec(), "with")
 337 | +        self.assertIn("error", row)
 338 | +        self.assertEqual((row["status"], row["response_headers"]["x-bf-instance"]), (400, "gw-1"))
 339 | +        self.assertNotIn(KEY, json.dumps(row))
 340 | +
 341 | +
 342 | +class TestRun(unittest.TestCase):
 343 | +    def test_both_legs_alternating_resumed_and_stopped_at_the_cap(self):
 344 | +        with tempfile.TemporaryDirectory() as d:
 345 | +            src = [{"record": f"rec{i}.json", "type": "step_a", "out_tokens": t, "shape": "truncated"}
 346 | +                   for i, t in enumerate((7, 122, 171, 497, 1564, 900))]
 347 | +            for s in src:
 348 | +                with open(os.path.join(d, s["record"]), "w") as f:
 349 | +                    json.dump(rec(), f)
 350 | +            b = RT.backend()
 351 | +            b.key = lambda name: KEY
 352 | +            res, spend = os.path.join(d, "RESULTS.jsonl"), os.path.join(d, "SPEND.json")
 353 | +            real = RT.SPEND
 354 | +            before = os.path.exists(real)
 355 | +            g = Gateway([('{"a": 1}', "stop")] * 12)
 356 | +            with mock.patch.object(RT, "unclosed", lambda: src), mock.patch.object(RT, "WT", d), \
 357 | +                    mock.patch.object(RT, "SPEND", spend), mock.patch("urllib.request.urlopen", g):
 358 | +                RT.run(3, b, stop_usd=1.0, results=res)
 359 | +                rows = [json.loads(x) for x in open(res)]
 360 | +                self.assertEqual([r["leg"] for r in rows], ["with", "without", "without", "with", "with", "without"])
 361 | +                RT.run(3, b, stop_usd=1.0, results=res)                         # resumed: nothing asked again
 362 | +                self.assertEqual(len(g.seen), 6)
 363 | +                RT.run(4, b, stop_usd=0.0005, results=res)                      # the ledger holds 0.0006: stopped
 364 | +                self.assertEqual(len(g.seen), 6)
 365 | +                self.assertAlmostEqual(RT.spent(spend), 0.0006)
 366 | +            self.assertEqual(os.path.exists(real), before)                      # the real ledger never touched
 367 | +
 368 | +
 369 | +if __name__ == "__main__":
 370 | +    unittest.main()
 371 | 
```

---

pp-selectid: RULING 114 (orchestrator 13:18 ET Nov 15), V4 ON AN XINFER WORKER. A new measurement driver,
tests/package/replay114.py, and its offline tests tests/package/test_replay114.py. Nothing in pipeline/ changes; no
build reads anything this writes; no routing change.

THE ORDER, verbatim: "The Heimdall team read our v4 samples. Jon Pry: the unclosed JSON is "the usual vllm schema
problem; the xinfer workers don't have this issue", and a request carrying the HTTP header x-bf-tunnel-instance:
pinga282 goes to an xinfer worker IF the gateway forwards the header (he has asked Thanos whether it does; we can
simply try). DO: (a) 30 of the 93 records that came back unclosed in replay111 (the same 5 I sent the team among them:
out_tokens 7, 122, 171, 497, 1564), same settings as replay111 (json_object, reasoning effort none), ONCE WITH the
header and ONCE WITHOUT, same seed. (b) THIS TIME RECORD per call: finish_reason, the response's id, and every
response header (so we can see which instance answered, e.g. any x-bf-* header), plus out_tokens and seconds. Never
log our own request's Authorization. (c) Report: unclosed with header / without header; whether any response header
shows the instance changed; finish_reason counts for the unclosed ones. If the header changes nothing, say so: it may
not be forwarded. (d) Proof to proof/replay114/." Heimdall only, cap $0.15.

THE DRIVER:
- unclosed(): replay111's OUT_OF_CONTRACT.jsonl rows of shape "truncated" (93). pick(): one record for each of the
  five named out_tokens first, then the others spread evenly in out_tokens order -> 30 distinct records (today: 15
  step_a, 14 clips_alone, 1 coherence).
- ask(): the call is replay111's own: replay111.FormatBackend("none").complete(prompt, max_tokens, seed,
  system) with the record's own prompt, max_tokens, seed and system (tests/package/replay111.py:56-87, UNCHANGED:
  model deepseek/deepseek-v4-flash-0731-abliterated, response_format json_object, reasoning_effort "none",
  max_tokens via max_out, temperature from the template spec, the system line + " Reply with one JSON object
  only."). The only change is the transport: capturing() swaps providers._http_json (the function FormatBackend
  calls, providers.py:124-127, UNCHANGED) for a Capture that sends the same request plus the extra header on the
  "with" leg and keeps the RESPONSE's status, every header, id, finish_reason, usage and model. On an HTTP error it
  keeps that response's status and headers and re-raises (providers._with_backoff, UNCHANGED, still retries 429 /
  5xx). The real _http_json is restored in a finally.
- The request's headers (the Authorization among them) are never put in a row: a row holds leg, x_bf_header_sent,
  seed, max_tokens, seconds, status, response_headers, id, finish_reason, usage, response_model, out_tokens,
  usd_reported, shape, unclosed, text (diagnosis only), and the record's id.
- shape_of(): "closed JSON" when the text parses, else replay111.shape (unchanged); unclosed = "truncated".
- run(): one call at a time; the two legs alternate which goes first (record i even: with first); a re-run skips
  (record, leg) pairs already in RESULTS.jsonl; no call starts once SPEND_R114.json holds STOP_USD $0.14
  (vendor-reported usage.cost, added after each call). Calls are ~$0.0003 (replay111: 96 step-A calls $0.032).
- report(): per leg: calls, errors, unclosed, shapes, finish_reason counts (all, and the unclosed); the response
  headers whose value differs between a record's two legs; every x-bf* response header seen; REPORT.md and
  SUMMARY.json.

TESTS (offline: urlopen replaced by a fake gateway, a fake key, temporary files): the pick; the header sent on its
leg only and the two requests otherwise identical (seed, model, response_format, reasoning_effort); the row's fields;
no key, "Bearer" or "authorization" in any row; a failed call is a row with the response's headers; both legs,
alternating, resumed without re-asking, stopped at the cap, and the real ledger never touched. (A first version bound
the ledger path at definition time, so the test's patch missed it: fixed, and the test now checks the real ledger.)

PLEASE CHECK: (1) that the request is byte-for-byte replay111's apart from the one header; (2) that no request header
(the Authorization) can reach a row, the report or a log line; (3) the stop under the cap; (4) the report's counts;
(5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
