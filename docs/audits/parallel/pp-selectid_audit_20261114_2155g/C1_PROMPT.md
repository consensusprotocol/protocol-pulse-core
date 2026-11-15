# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2155g
# Branch: pp-selectid
# Generated: 2026-11-14 21:55 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2155g/C1_STEP.diff (360 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 8e556dd..e490f49 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -20,6 +20,12 @@
   6 |  Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
   7 |  package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
   8 |  
   9 | +RULING 107 (1) (orchestrator 20:20 ET Nov 14), "a build that judges nothing new must cost $0.00": a full build ends by
  10 | +writing FINGERPRINT.json (fingerprint(): its pool, deliveries, ET day, code by content, candidates and the integrator's
  11 | +outputs it read, as they stand at its end, with open_work(): what it left undone). The next build fingerprints its own
  12 | +inputs before any model is asked. When they equal the newest finished build's and that build left nothing undone, it
  13 | +writes NOTHING_NEW.json and stops: no router, no call, $0.00.
  14 | +
  15 |  RULING 66 (13:18; its standing part ruled 14:02), A PASSED LINE-UP IS KEPT: every build first tries the due
  16 |  candidates of the registry (tests/package/proof/CANDIDATES.json, seeded from the build records; pipeline/candidates.py),
  17 |  newest first, inside the 8 judged line-ups (a recorded verdict is free), each as package.build(candidate=...); only when
  18 | @@ -42,6 +48,7 @@ Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since
  19 |  """
  20 |  import argparse
  21 |  import glob
  22 | +import hashlib
  23 |  import json
  24 |  import os
  25 |  import sys
  26 | @@ -76,6 +83,84 @@ REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the c
  27 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
  28 |  DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
  29 |  STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
  30 | +FINGERPRINT = "FINGERPRINT.json"     # RULING 107 (1): a finished build's inputs, written at its end for the next build
  31 | +NOTHING_NEW = "NOTHING_NEW.json"     # RULING 107 (1): a build that found nothing new and asked no model
  32 | +
  33 | +
  34 | +def _sha(x):
  35 | +    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()
  36 | +
  37 | +
  38 | +def _file_sha(path):
  39 | +    try:
  40 | +        with open(path, "rb") as f:
  41 | +            return hashlib.sha256(f.read()).hexdigest()
  42 | +    except OSError:
  43 | +        return None
  44 | +
  45 | +
  46 | +def code_content(repo=REPO, here=HERE):
  47 | +    """The build's code BY CONTENT: every pipeline/*.py and pipeline/*.json, and every driver module of tests/package
  48 | +    (not its tests). A STATE or data commit moves HEAD but changes no judgment, so HEAD is not in it."""
  49 | +    files = sorted(glob.glob(os.path.join(repo, "pipeline", "*.py")) + glob.glob(os.path.join(repo, "pipeline", "*.json"))
  50 | +                   + [f for f in glob.glob(os.path.join(here, "*.py")) if not os.path.basename(f).startswith("test_")])
  51 | +    h = hashlib.sha256()
  52 | +    for f in files:
  53 | +        with open(f, "rb") as fh:
  54 | +            h.update(os.path.relpath(f, repo).encode() + b"\0" + fh.read() + b"\0")
  55 | +    return h.hexdigest()
  56 | +
  57 | +
  58 | +def fingerprint(moments, delivered, pins, since, now, reg):
  59 | +    """RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". Everything a
  60 | +    build's judgments and outcome depend on: the pool's moment records (each with its words, span and sources), what
  61 | +    was delivered and since when, the ET day (the show date every step-A prompt carries), the code and its config BY
  62 | +    CONTENT, the candidate registry and which of its candidates are due now (ruling 66: a resting one comes due after
  63 | +    6 h), the ruling-90 spotlights record, the ruling-104 directives, and the outputs of the integrator's services this
  64 | +    build reads: the pre-check results for the pool's videos and the clip scorer's verdicts. -> (sha256, its parts)."""
  65 | +    vids = {m.get("video_id") for m in moments}
  66 | +    try:
  67 | +        res = sorted((n, os.path.getsize(os.path.join(LP.RESULTS, n)), os.path.getmtime(os.path.join(LP.RESULTS, n)))
  68 | +                     for n in os.listdir(LP.RESULTS) if n.split(".", 1)[0] in vids)
  69 | +    except OSError:
  70 | +        res = None
  71 | +    parts = {"moments": _sha(moments), "delivered": _sha([delivered, [p.get("story_id") for p in pins], since.isoformat()]),
  72 | +             "day_et": SPOT.et_day(now), "code": code_content(), "candidates": _sha(reg.get("candidates")),
  73 | +             "due": sorted([k, fresh] for k, _, fresh in CA.due(reg, now)),
  74 | +             "spotlights": _file_sha(SPOTLIGHTS), "directives": _file_sha(DIRECTIVES),
  75 | +             "precheck_results": _sha(res), "scorer_verdicts": _file_sha(PK.SCORER_VERDICTS)}
  76 | +    return _sha(parts), parts
  77 | +
  78 | +
  79 | +def open_work(res, sp):
  80 | +    """RULING 107 (1): what a finished build left undone, which the next build must try again whatever its inputs:
  81 | +    the moments ruling 102 held (no leg answered), any segment the render's lock gave no verdict on in time, and any
  82 | +    visual check left unmeasured. -> int (0: nothing left)."""
  83 | +    pre, sp = (res or {}).get("prescreen") or {}, sp or {}
  84 | +    h = pre.get("held_102") or {}
  85 | +    held = len(h.get("first") or []) + len(h.get("second") or []) + len(sp.get("held_102") or [])
  86 | +    no_verdict = json.dumps(res, default=str).count('"verdict": "error"') + \
  87 | +        json.dumps(sp, default=str).count('"verdict": "error"')
  88 | +    vis = (res or {}).get("visual") or {}
  89 | +    return held + no_verdict + int(vis.get("unmeasured") or 0)
  90 | +
  91 | +
  92 | +def nothing_new(proof_dir, out_dir, fp):
  93 | +    """RULING 107 (1): the newest earlier FINISHED build (its FINGERPRINT.json) when its fingerprint is this build's and
  94 | +    it left nothing undone; else None. A build that stopped early writes none, and neither does a --from-candidate
  95 | +    one (it tries one line-up, not the pool), so neither can stand for a full build."""
  96 | +    for d in sorted(glob.glob(os.path.join(proof_dir, "ledger_*")), reverse=True):
  97 | +        if os.path.abspath(d) == os.path.abspath(out_dir):
  98 | +            continue
  99 | +        try:
 100 | +            with open(os.path.join(d, FINGERPRINT)) as f:
 101 | +                prev = json.load(f)
 102 | +        except (OSError, ValueError):
 103 | +            continue
 104 | +        if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
 105 | +            return os.path.basename(d)
 106 | +        return None
 107 | +    return None
 108 |  
 109 |  
 110 |  def delivered_pins(paths):
 111 | @@ -316,6 +401,16 @@ def main(argv=None):
 112 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 113 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 114 |                    f, indent=1, default=str)
 115 | +    pool = json.loads(json.dumps(moments, default=str))   # RULING 107 (1): the pool as it came in, before any stage
 116 | +    fp, fp_parts = fingerprint(pool, delivered, pins, since, now, reg)
 117 | +    same = None if cand is not None else nothing_new(os.path.join(HERE, "proof"), out_dir, fp)
 118 | +    if same:                                     # nothing new: no router, no model, $0.00 (ruling 107 (1))
 119 | +        with open(os.path.join(out_dir, NOTHING_NEW), "w") as f:
 120 | +            json.dump({"fingerprint": fp, "parts": fp_parts, "same_as": same, "at": now.isoformat()}, f, indent=1)
 121 | +        say(f"NOTHING NEW (ruling 107 (1)): this build's inputs are {same}'s (fingerprint {fp[:12]}), and that build "
 122 | +            f"left nothing undone: no model is asked, $0.00")
 123 | +        logf.close()
 124 | +        return 0
 125 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
 126 |      routing = a.routing or rt.get("mode") or "today"
 127 |      shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 128 | @@ -526,6 +621,12 @@ def main(argv=None):
 129 |              f"is written with registry false")           # applies this record's outcome (CA.seed)
 130 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
 131 |          json.dump(res, f, indent=1, default=str)
 132 | +    if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
 133 | +        fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg)   # they stand at this build's END
 134 | +        left = open_work(res, sp)
 135 | +        with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
 136 | +            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "build": name}, f, indent=1)
 137 | +        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone")
 138 |      logf.close()
 139 |      return 0
 140 |  
 141 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 142 | new file mode 100644
 143 | index 0000000..e462542
 144 | --- /dev/null
 145 | +++ b/tests/package/test_ruling_107_guard.py
 146 | @@ -0,0 +1,213 @@
 147 | +#!/usr/bin/env python3
 148 | +"""RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". The build driver
 149 | +fingerprints its inputs before any model is asked (proof_ledger.fingerprint), and stops with no router and no call
 150 | +when they equal the newest finished build's and that build left nothing undone (nothing_new, open_work). Offline:
 151 | +temporary proof directories; the driver test stubs the ledger reads and makes building a router an error."""
 152 | +import copy
 153 | +import io
 154 | +import json
 155 | +import os
 156 | +import sys
 157 | +import tempfile
 158 | +import unittest
 159 | +from datetime import datetime, timedelta, timezone
 160 | +from unittest import mock
 161 | +
 162 | +HERE = os.path.dirname(os.path.abspath(__file__))
 163 | +REPO = os.path.dirname(os.path.dirname(HERE))
 164 | +sys.path.insert(0, HERE)
 165 | +import proof_ledger as PLG  # noqa: E402
 166 | +
 167 | +NOW = datetime(2026, 11, 14, 22, 0, tzinfo=timezone.utc)                  # 17:00 ET
 168 | +POOL = [{"moment_id": "m1", "video_id": "vidZZZZZZZ1", "text": "Bitcoin is a bearer asset.", "start": 1.0, "end": 9.0},
 169 | +        {"moment_id": "m2", "video_id": "vidZZZZZZZ2", "text": "Self custody matters.", "start": 3.0, "end": 12.0}]
 170 | +PINS = [{"story_id": "s1"}]
 171 | +DELIVERED = [{"video_id": "old", "start": 0.0, "end": 5.0}]
 172 | +SINCE = datetime(2026, 11, 13, 3, 1, 9, tzinfo=timezone.utc)
 173 | +
 174 | +
 175 | +class Paths(unittest.TestCase):
 176 | +    """Every file the fingerprint reads, in a temporary directory."""
 177 | +
 178 | +    def setUp(self):
 179 | +        self.tmp = tempfile.TemporaryDirectory()
 180 | +        d = self.tmp.name
 181 | +        self.res, self.spot, self.dirs, self.scorer = (os.path.join(d, "results"), os.path.join(d, "SPOTLIGHTS.json"),
 182 | +                                                       os.path.join(d, "DIRECTIVES.json"), os.path.join(d, "latest.json"))
 183 | +        os.makedirs(self.res)
 184 | +        for p, body in ((self.spot, "[]"), (self.dirs, '{"directives": []}'), (self.scorer, '{"verdicts": {}}')):
 185 | +            open(p, "w").write(body)
 186 | +        self.patches = [mock.patch.object(PLG.LP, "RESULTS", self.res), mock.patch.object(PLG, "SPOTLIGHTS", self.spot),
 187 | +                        mock.patch.object(PLG, "DIRECTIVES", self.dirs),
 188 | +                        mock.patch.object(PLG.PK, "SCORER_VERDICTS", self.scorer)]
 189 | +        for p in self.patches:
 190 | +            p.start()
 191 | +
 192 | +    def tearDown(self):
 193 | +        for p in self.patches:
 194 | +            p.stop()
 195 | +        self.tmp.cleanup()
 196 | +
 197 | +    def fp(self, pool=POOL, delivered=DELIVERED, pins=PINS, since=SINCE, now=NOW, reg=None):
 198 | +        return PLG.fingerprint(pool, delivered, pins, since, now, reg or PLG.CA.new_registry())
 199 | +
 200 | +
 201 | +class TestFingerprint(Paths):
 202 | +    def test_the_same_inputs_give_the_same_fingerprint(self):
 203 | +        self.assertEqual(self.fp()[0], self.fp(pool=copy.deepcopy(POOL))[0])
 204 | +        later = NOW + timedelta(hours=3)                                     # still 14 Nov ET
 205 | +        self.assertEqual(self.fp()[0], self.fp(now=later)[0])
 206 | +
 207 | +    def test_every_input_moves_it(self):
 208 | +        base = self.fp()[0]
 209 | +        pool = copy.deepcopy(POOL)
 210 | +        pool[0]["text"] = "Bitcoin is a bearer instrument."
 211 | +        self.assertNotEqual(self.fp(pool=pool)[0], base, "a word of a moment")
 212 | +        self.assertNotEqual(self.fp(pool=POOL + [dict(POOL[0], moment_id="m3")])[0], base, "a new moment")
 213 | +        self.assertNotEqual(self.fp(delivered=DELIVERED + [{"video_id": "x", "start": 1, "end": 2}])[0], base,
 214 | +                            "a delivered span")
 215 | +        self.assertNotEqual(self.fp(pins=[{"story_id": "s2"}])[0], base, "a delivered pin")
 216 | +        self.assertNotEqual(self.fp(since=SINCE + timedelta(hours=1))[0], base, "since")
 217 | +        self.assertNotEqual(self.fp(now=NOW + timedelta(hours=8))[0], base, "the ET day (the show date)")   # 01:00 ET Nov 15
 218 | +        reg = PLG.CA.new_registry()
 219 | +        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "closed",
 220 | +                                      "found_at": "2026-11-14T10:00:00+00:00", "until": None, "fresh_used": False,
 221 | +                                      "history": []}
 222 | +        self.assertNotEqual(self.fp(reg=reg)[0], base, "the registry")
 223 | +        for path, body, what in ((self.spot, '[{"channel_id": "c"}]', "the spotlights record"),
 224 | +                                 (self.dirs, '{"directives": [{"parent": "x"}]}', "a directive"),
 225 | +                                 (self.scorer, '{"verdicts": {"t": 4}}', "the clip scorer's verdicts")):
 226 | +            was = open(path).read()
 227 | +            open(path, "w").write(body)
 228 | +            self.assertNotEqual(self.fp()[0], base, what)
 229 | +            open(path, "w").write(was)
 230 | +        self.assertEqual(self.fp()[0], base)
 231 | +        with mock.patch.object(PLG, "code_content", lambda *a, **k: "other code"):
 232 | +            self.assertNotEqual(self.fp()[0], base, "the code")
 233 | +
 234 | +    def test_a_precheck_result_moves_it_only_for_a_video_of_the_pool(self):
 235 | +        base = self.fp()[0]
 236 | +        open(os.path.join(self.res, "otherVideo1.0.000-9.000.a4c307f78c94.json"), "w").write("[]")
 237 | +        self.assertEqual(self.fp()[0], base)                                 # another video's answer: not this pool
 238 | +        open(os.path.join(self.res, "vidZZZZZZZ1.1.000-9.000.a4c307f78c94.json"), "w").write("[]")
 239 | +        self.assertNotEqual(self.fp()[0], base)                              # an answer for the pool
 240 | +
 241 | +    def test_a_resting_candidate_coming_due_moves_it(self):
 242 | +        reg = PLG.CA.new_registry()
 243 | +        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "resting",
 244 | +                                      "found_at": "2026-11-14T10:00:00+00:00", "until": "2026-11-14T23:00:00+00:00",
 245 | +                                      "fresh_used": False, "history": []}
 246 | +        before, after = self.fp(reg=reg)[0], self.fp(reg=reg, now=NOW + timedelta(hours=1, minutes=30))[0]
 247 | +        self.assertNotEqual(before, after)                                   # 18:30 ET: its 6 h are over
 248 | +
 249 | +    def test_the_code_is_read_by_content_not_by_commit(self):
 250 | +        self.assertEqual(PLG.code_content(), PLG.code_content())
 251 | +        with tempfile.TemporaryDirectory() as d:
 252 | +            os.makedirs(os.path.join(d, "pipeline"))
 253 | +            os.makedirs(os.path.join(d, "drv"))
 254 | +            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 1\n")
 255 | +            open(os.path.join(d, "drv", "proof_x.py"), "w").write("y = 1\n")
 256 | +            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 1\n")
 257 | +            one = PLG.code_content(d, os.path.join(d, "drv"))
 258 | +            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 2\n")
 259 | +            self.assertEqual(PLG.code_content(d, os.path.join(d, "drv")), one)      # a test is not the build's code
 260 | +            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 2\n")
 261 | +            self.assertNotEqual(PLG.code_content(d, os.path.join(d, "drv")), one)
 262 | +
 263 | +
 264 | +class TestOpenWorkAndNothingNew(unittest.TestCase):
 265 | +    def test_open_work_counts_what_a_build_left_undone(self):
 266 | +        self.assertEqual(PLG.open_work({"prescreen": {}, "visual": {}}, {}), 0)
 267 | +        self.assertEqual(PLG.open_work({"prescreen": {"held_102": {"first": ["a"], "second": ["b", "c"]}}},
 268 | +                                       {"held_102": ["d"]}), 4)
 269 | +        self.assertEqual(PLG.open_work({"tried": [{"precheck": {"segments": [{"verdict": "error"}]}}]}, {}), 1)
 270 | +        self.assertEqual(PLG.open_work({}, {"lock_stop": {"segments": [{"verdict": "error"}]}}), 1)
 271 | +        self.assertEqual(PLG.open_work({"visual": {"unmeasured": 2}}, {}), 2)
 272 | +
 273 | +    def test_only_the_newest_finished_build_counts(self):
 274 | +        with tempfile.TemporaryDirectory() as d:
 275 | +            def build(name, fp=None, left=0):
 276 | +                os.makedirs(os.path.join(d, name))
 277 | +                if fp is not None:
 278 | +                    json.dump({"fingerprint": fp, "open_work": left, "build": name},
 279 | +                              open(os.path.join(d, name, PLG.FINGERPRINT), "w"))
 280 | +            me = os.path.join(d, "ledger_20261114_230000")
 281 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))                  # no earlier build
 282 | +            build("ledger_20261114_200000", "F")
 283 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")
 284 | +            build("ledger_20261114_210000")                                  # no FINGERPRINT (stopped, skipped, or a
 285 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")   # candidate's): passed over
 286 | +            build("ledger_20261114_220000", "G")                             # the newest finished build differs
 287 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))
 288 | +            build("ledger_20261114_221000", "F", left=1)                     # the same, but it left work undone
 289 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))
 290 | +            os.makedirs(me)
 291 | +            json.dump({"fingerprint": "F", "open_work": 0}, open(os.path.join(me, PLG.FINGERPRINT), "w"))
 292 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))                   # never this build itself
 293 | +            build("ledger_20261114_222000", "F")
 294 | +            open(os.path.join(d, "ledger_20261114_222500", PLG.FINGERPRINT) if os.makedirs(
 295 | +                os.path.join(d, "ledger_20261114_222500")) is None else "", "w").write("{not json")
 296 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_222000")   # an unreadable one is passed
 297 | +
 298 | +
 299 | +class TestTheDriverAsksNoModel(Paths):
 300 | +    """The driver itself: with the newest finished build's fingerprint equal to this one's and nothing left undone, it
 301 | +    stops before any router exists (building one is an error here); with work left undone, it goes on to the router."""
 302 | +    PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 303 | +                                                                                  "MOMENTS_PIN_LY.json")]
 304 | +
 305 | +    def run_driver(self, left):
 306 | +        proof = os.path.join(self.tmp.name, "drv", "proof")
 307 | +        os.makedirs(proof)
 308 | +        delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
 309 | +        fp, _ = PLG.fingerprint(copy.deepcopy(POOL), delivered, pins, last, datetime.now(timezone.utc),
 310 | +                                PLG.CA.new_registry())
 311 | +        prev = os.path.join(proof, "ledger_20000101_000000")
 312 | +        os.makedirs(prev)
 313 | +        json.dump({"fingerprint": fp, "open_work": left, "build": "ledger_20000101_000000"},
 314 | +                  open(os.path.join(prev, PLG.FINGERPRINT), "w"))
 315 | +
 316 | +        class Built(Exception):
 317 | +            pass
 318 | +
 319 | +        def no_router(*a, **k):
 320 | +            raise Built("a router was built")
 321 | +        stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
 322 | +                 mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
 323 | +                 mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
 324 | +                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
 325 | +                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"rows": 0})),
 326 | +                 mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: (copy.deepcopy(POOL), {}, {})),
 327 | +                 mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
 328 | +                 mock.patch.object(PLG, "build_router", no_router),
 329 | +                 mock.patch("sys.stdout", new=io.StringIO())]
 330 | +        for s in stubs:
 331 | +            s.start()
 332 | +        try:
 333 | +            try:
 334 | +                rc = PLG.main(["--delivered", *self.PIN_PATHS])
 335 | +            except Built:
 336 | +                rc = "router"
 337 | +        finally:
 338 | +            for s in stubs:
 339 | +                s.stop()
 340 | +        runs = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") and n != "ledger_20000101_000000")
 341 | +        return rc, [os.path.join(proof, n) for n in runs]
 342 | +
 343 | +    def test_nothing_new_stops_before_any_router_and_costs_nothing(self):
 344 | +        rc, runs = self.run_driver(left=0)
 345 | +        self.assertEqual(rc, 0)
 346 | +        self.assertEqual(len(runs), 1)
 347 | +        rec = json.load(open(os.path.join(runs[0], PLG.NOTHING_NEW)))
 348 | +        self.assertEqual(rec["same_as"], "ledger_20000101_000000")
 349 | +        self.assertIn("NOTHING NEW (ruling 107 (1))", open(os.path.join(runs[0], "package.log")).read())
 350 | +        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.FINGERPRINT)))   # a skip never stands for a build
 351 | +
 352 | +    def test_work_left_undone_goes_on_to_the_router(self):
 353 | +        rc, runs = self.run_driver(left=1)
 354 | +        self.assertEqual(rc, "router")
 355 | +        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.NOTHING_NEW)))
 356 | +
 357 | +
 358 | +if __name__ == "__main__":
 359 | +    unittest.main()
 360 | 
```

---

pp-selectid, RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00 ... the
test proves it before the second build of the batch" (ruling 108, 21:20).

THE CHANGE (tests/package/proof_ledger.py, the build driver; tests/package/test_ruling_107_guard.py is new):
- fingerprint(moments, delivered, pins, since, now, reg) hashes what a build's judgments and outcome depend on:
  the pool's moment records; the delivered spans, pins and 'since'; the ET day (the show date every step-A prompt
  carries); the code BY CONTENT (every pipeline/*.py and *.json and the tests/package driver modules, not tests:
  code_content()); the candidate registry and which of its candidates are due now; the ruling-90 spotlights record;
  the ruling-104 directives; the integrator's pre-check result files for the pool's videos; the clip scorer's verdict
  file.
- open_work(res, sp) counts what a finished build left undone: ruling 102's held moments, any "verdict": "error"
  (no lock verdict in time), and unmeasured visual checks.
- nothing_new(proof_dir, out_dir, fp): the NEWEST earlier build with a FINGERPRINT.json decides. It matches only
  when its fingerprint equals this one's and it left nothing undone. A skipped build, a stopped build and a
  --from-candidate build write none.
- main(): after inputs.json, the pool is fingerprinted BEFORE any router exists. Nothing new: NOTHING_NEW.json is
  written and the build returns 0 with no router and no call ($0.00). A full build ends by writing FINGERPRINT.json
  with the inputs as they stand at its END (the registry, spotlights and the integrator's outputs it changed) and
  its open work.
UNCHANGED GUARDS: main() writes inputs.json before the guard; build_router is the only way a model is reached; the
registry is saved before package.json.
PLEASE CHECK: (1) Can the guard skip a build that has something new to judge (a new moment, a moment come due, an
answer that arrived, a code change, a new day, held work)? (2) Can it ever let a model call happen before it
decides? (3) Is anything time-varying in the fingerprint that would keep it from ever matching? (4) Do the tests pin
it, including the driver-level test that building a router is an error when nothing is new?



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
