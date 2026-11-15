# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1129
# Branch: pp-selectid
# Generated: 2026-11-15 11:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1129/C1_STEP.diff (737 lines)
```
   1 | diff --git a/tests/package/hook112.py b/tests/package/hook112.py
   2 | new file mode 100644
   3 | index 0000000..7f06d51
   4 | --- /dev/null
   5 | +++ b/tests/package/hook112.py
   6 | @@ -0,0 +1,491 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 112 (orchestrator 11:15 ET Nov 15): THE HOOK SCARCITY DIAGNOSIS. No bar, gate or routing changes.
   9 | +
  10 | +Read-only on every build record (tests/package/proof/ledger_*), the hook cache, pp-ingest's ledger and its queue
  11 | +database (opened mode=ro). The ONE paid part is the calibration (part 2): the hook job as it stands today
  12 | +(package.hook_ratings and package.HOOKS_PROMPT, unchanged) on the approved hooks. It runs on Heimdall only: the hook
  13 | +chain of ruling 88 (coherence_verdict:hook) with every non-Heimdall back-end removed, and no shadow. It uses its own
  14 | +spend ledger, a stop below the order's cap, and no cache (fresh ratings; the production cache is neither read nor
  15 | +written).
  16 | +
  17 | +-> tests/package/proof/hook112/:
  18 | +- FUNNEL.json (1): per build, and per DISTINCT moment, how far each one got toward the hook job and what stopped it.
  19 | +- CALIBRATION.json (2).
  20 | +- NEAR_MISSES.json (3).
  21 | +- HOOK_PASS.json (4).
  22 | +- REPORT.md.
  23 | +Usage: python3 -B tests/package/hook112.py [--no-calibration] [--hours 48]"""
  24 | +import argparse
  25 | +import collections
  26 | +import glob
  27 | +import json
  28 | +import os
  29 | +import re
  30 | +import sqlite3
  31 | +import sys
  32 | +from datetime import datetime, timedelta, timezone
  33 | +
  34 | +HERE = os.path.dirname(os.path.abspath(__file__))
  35 | +REPO = os.path.dirname(os.path.dirname(HERE))
  36 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  37 | +sys.path.insert(0, HERE)
  38 | +
  39 | +PROOF = os.path.join(HERE, "proof")
  40 | +OUT = os.path.join(PROOF, "hook112")
  41 | +SPEND = os.path.join(PROOF, "SPEND_H112.json")
  42 | +LIMIT_USD, STOP_USD = 0.30, 0.25          # the order's cap; no call starts at or over the stop
  43 | +SEEDS = (7, 8, 9)                        # 7 is production's; 8 and 9 show how stable a rating is
  44 | +INGEST = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  45 | +QUEUE_DB = os.path.join(INGEST, "data", "editorial", "ingest", "queue.sqlite")
  46 | +LEDGER = os.path.join(INGEST, "data", "editorial", "moments", "moment_ledger.jsonl")
  47 | +REFS = [("preview", "the protected preview (L-d, PBX 2026-11-11)",
  48 | +         os.path.join(REPO, "references", "pulse_preview_2026-11-11", "PIN.json")),
  49 | +        ("37c5b5f5", "the protected moments reference 37c5b5f5",
  50 | +         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")),
  51 | +        ("41f29b1f", "the protected medley reference 41f29b1f",
  52 | +         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN_LY.json")),
  53 | +        ("0c68b589", "the published medley 0c68b589",
  54 | +         os.path.join(PROOF, "ledger_20261113_183302", "MOMENTS_PIN_ATTESTED.json")),
  55 | +        ("13949b7c", "the last sealed medley 13949b7c (delivered as a pass 17:14 ET Nov 13)",
  56 | +         os.path.join(PROOF, "ledger_20261113_215708", "MOMENTS_PIN_LEDGER.json"))]
  57 | +
  58 | +# THE COMMON STAGES toward the hook job, on which both paths (the medley's and the spotlight's) are placed
  59 | +STAGES = ("in a pool", "passed the free screens", "cleared step A", "passed the second pass and CUTTABLE",
  60 | +          "may open", "rated by the hook job", "rated >= 4")
  61 | +
  62 | +
  63 | +def base(mid):
  64 | +    """A variant (~trim, ~tail) is its moment's speech: one distinct moment."""
  65 | +    return str(mid).split("~")[0]
  66 | +
  67 | +
  68 | +def reason_class(why):
  69 | +    """A short, stable class for a free-text reason (the full texts stay in FUNNEL.json)."""
  70 | +    w = str(why or "")
  71 | +    for pat, cls in ((r"over the 20\.0 s", "over the medley's 20 s"), (r"over the 35\.0 s", "over the spotlight's 35 s"),
  72 | +                     (r"topic rule", "STAND_ALONE topic rule (ruling 34)"),
  73 | +                     (r"STAND_ALONE with the clip scorer|STAND_ALONE", "STAND_ALONE opener rule"),
  74 | +                     (r"ALONE scorer", "the ALONE scorer below 4 (ruling 109, free)"),
  75 | +                     (r"not eligible on screen", "not eligible on screen (opener)"),
  76 | +                     (r"genuine quiet|G17a", "G17a: no genuine quiet before the onset"),
  77 | +                     (r"second pass disagrees|L-v 2 FAIL", "L-v 2: the second pass disagrees"),
  78 | +                     (r"not cuttable", "not cuttable at an edge"), (r"NOT MEASURED", "not measured"),
  79 | +                     (r"cannot open", "cannot open (hook eligibility or the render's opener rule)"),
  80 | +                     (r"ad-read|ad_read", "ad-read marker"), (r"time.sensitive|ruling 76", "stale or time words"),
  81 | +                     (r"speaker", "speaker rule"), (r"fewer than 3 channels|channel\(s\) after the free stages",
  82 | +                                                     "the medley's 3-channel rule"),
  83 | +                     (r"re-posted|ruling 53", "re-posted by a second channel (ruling 53)"),
  84 | +                     (r"not rated", "not rated (the hook call failed)")):
  85 | +        if re.search(pat, w):
  86 | +            return cls
  87 | +    m = re.match(r"step A: ([A-Z_]+)", w)
  88 | +    if m:
  89 | +        return "step A: " + m.group(1)
  90 | +    return w[:60] or "unknown"
  91 | +
  92 | +
  93 | +def build_records(proof=PROOF, since=None):
  94 | +    """[(name, package.json, inputs.json)] of every finished build whose dir name (UTC) is >= since."""
  95 | +    out = []
  96 | +    for d in sorted(glob.glob(os.path.join(proof, "ledger_*"))):
  97 | +        name = os.path.basename(d)
  98 | +        if since and name < since:
  99 | +            continue
 100 | +        try:
 101 | +            pk = json.load(open(os.path.join(d, "package.json")))
 102 | +            inp = json.load(open(os.path.join(d, "inputs.json")))
 103 | +        except (OSError, ValueError):
 104 | +            continue
 105 | +        out.append((name, pk, inp))
 106 | +    return out
 107 | +
 108 | +
 109 | +def medley_trace(pk, inp):
 110 | +    """{moment id: (common stage reached, why it stopped there or None, rating record or None)} for the medley path."""
 111 | +    pre = pk.get("prescreen") or {}
 112 | +    hp = pk.get("hook_pool") or {}
 113 | +    ratings = hp.get("ratings") or {}
 114 | +    unusable, no_role, ad = pk.get("unusable") or {}, pk.get("no_role") or {}, pk.get("ad_read") or {}
 115 | +    reposted = pk.get("reposted") or {}
 116 | +    failed, second, onset = pre.get("failed") or {}, pre.get("second_pass") or {}, pre.get("hook_onset") or {}
 117 | +    trim_cut = pre.get("trim_cut") or {}
 118 | +    pool = [m.get("moment_id") for m in inp.get("moments") or [] if isinstance(m, dict)]
 119 | +    ids = list(dict.fromkeys(pool + list(failed) + list(second) + list(onset) + list(ratings) +
 120 | +                             list((pk.get("trimmed") or {}).values())))
 121 | +    went_on = "second_pass" in pre                     # the medley passed the 3-channel rule on the cleared moments
 122 | +    out = {}
 123 | +    for mid in ids:
 124 | +        if mid in unusable:
 125 | +            out[mid] = (0, unusable[mid], None)
 126 | +        elif mid in no_role:
 127 | +            out[mid] = (0, no_role[mid], None)
 128 | +        elif mid in ad:
 129 | +            out[mid] = (0, ad[mid], None)
 130 | +        elif mid in reposted:
 131 | +            out[mid] = (0, f"re-posted by a second channel (ruling 53): {reposted[mid]}", None)
 132 | +        elif mid in failed:
 133 | +            out[mid] = (1, "step A: " + "; ".join(failed[mid]), None)
 134 | +        elif mid in ratings:
 135 | +            r = ratings[mid]
 136 | +            own = own_rating(r)                        # as it stands today (ruling 61), as the near misses read it
 137 | +            ge4 = isinstance(own, int) and own >= 4
 138 | +            out[mid] = (6 if ge4 else 5, None if ge4 else f"rated {own}", r)
 139 | +        elif mid in second and second[mid] != "PASS":
 140 | +            out[mid] = (2, second[mid], None)
 141 | +        elif mid in trim_cut:
 142 | +            out[mid] = (3, trim_cut[mid], None)
 143 | +        elif mid in onset and onset[mid] != "PASS":
 144 | +            out[mid] = (3, onset[mid], None)
 145 | +        elif mid in onset and hp.get("error"):
 146 | +            out[mid] = (4, f"not rated (the hook call failed): {hp['error']}", None)
 147 | +        elif mid in onset:
 148 | +            out[mid] = (3, "cannot open (hook eligibility or the render's opener rule)", None)
 149 | +        elif not went_on and mid in pool and pre.get("cleared") is not None and mid not in failed and \
 150 | +                (pre.get("screened") or 0) > 0:
 151 | +            out[mid] = (2, "the medley ended at its 3-channel rule (fewer than 3 channels cleared step A)", None)
 152 | +        elif mid in pool:
 153 | +            out[mid] = (1, pk.get("why_none") or "the medley ended before step A", None)
 154 | +    return out
 155 | +
 156 | +
 157 | +def spotlight_trace(pk):
 158 | +    """{moment id: (common stage, why or None, hook_own or None)} for the spotlight path, its widened spans under the
 159 | +    moment they came from."""
 160 | +    sp = pk.get("spotlight") or {}
 161 | +    pool = sp.get("pool") or {}
 162 | +    snapped = {k: (v or {}).get("from") for k, v in (pool.get("snapped") or {}).items() if isinstance(v, dict)}
 163 | +    out = {}
 164 | +    for mid, why in (dict(pool.get("out") or {})).items():
 165 | +        out[snapped.get(mid, mid)] = (0, why, None)
 166 | +    for mid, m in (sp.get("moments") or {}).items():
 167 | +        if not isinstance(m, dict):
 168 | +            continue
 169 | +        st, why, own = int(m.get("stage") or 0), m.get("out"), m.get("hook_own")
 170 | +        if own is not None:
 171 | +            c = (6, None, own) if own >= 4 else (5, why, own)
 172 | +        else:
 173 | +            stepa = st == 0 and (str(why).startswith("step A") or "no verdict (law L-m)" in str(why))
 174 | +            c = {0: (1 if stepa else 0, why, None), 1: (2, why, None), 2: (3, why, None)}.get(st, (4, why, None))
 175 | +        k = snapped.get(mid, mid)
 176 | +        if k not in out or c[0] > out[k][0]:
 177 | +            out[k] = c
 178 | +    return out
 179 | +
 180 | +
 181 | +def funnel(records):
 182 | +    """Per build counts on the common stages, and the distinct roll-up: every moment (by base id) at its furthest
 183 | +    stage over every build and both paths, with the reason it stopped there."""
 184 | +    per_build, best = [], {}
 185 | +    for name, pk, inp in records:
 186 | +        md, st = medley_trace(pk, inp), spotlight_trace(pk)
 187 | +        row = {"build": name, "pool": len(inp.get("moments") or []), "why_none": str(pk.get("why_none") or "")[:200]}
 188 | +        for path, tr in (("medley", md), ("spotlight", st)):
 189 | +            row[path] = {s: sum(1 for c in tr.values() if c[0] >= i) for i, s in enumerate(STAGES)}
 190 | +        per_build.append(row)
 191 | +        for tr in (md, st):
 192 | +            for mid, c in tr.items():
 193 | +                k = base(mid)
 194 | +                if k not in best or c[0] >= best[k][0]:      # a tie keeps the LATEST build's reason
 195 | +                    best[k] = (c[0], c[1], name)
 196 | +    stops = collections.defaultdict(collections.Counter)
 197 | +    for k, (stage, why, _) in best.items():
 198 | +        if stage < 5:
 199 | +            stops[STAGES[stage + 1]][reason_class(why)] += 1
 200 | +    return {"builds": per_build, "distinct": len(best),
 201 | +            "distinct_by_stage": {s: sum(1 for c in best.values() if c[0] >= i) for i, s in enumerate(STAGES)},
 202 | +            "never_rated_stopped_before": {s: dict(c.most_common()) for s, c in stops.items()},
 203 | +            "furthest": {k: {"stage": STAGES[c[0]], "why": c[1], "build": c[2]} for k, c in sorted(best.items())}}
 204 | +
 205 | +
 206 | +def ledger_of(records):
 207 | +    """{build moment id: pp-ingest's ledger moment id}: a build re-anchors each ledger row and gives the moment an id
 208 | +    of its own (mined.ledger_moment_id keeps the row's); a variant (~trim, ~tail) and a spotlight's widened span
 209 | +    (pool.snapped[...]["from"]) map to the moment they came from."""
 210 | +    out = {}
 211 | +    for _, pk, inp in records:
 212 | +        for m in inp.get("moments") or []:
 213 | +            if isinstance(m, dict) and m.get("moment_id"):
 214 | +                lid = (m.get("mined") or {}).get("ledger_moment_id")
 215 | +                if lid:
 216 | +                    out[m["moment_id"]] = lid
 217 | +        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
 218 | +            if isinstance(v, dict) and v.get("from"):
 219 | +                out.setdefault(new, v["from"])
 220 | +    def resolve(v, depth=0):                         # widened span -> its moment (maybe a variant) -> the ledger row
 221 | +        if depth < 4 and v in out and out[v] != v:
 222 | +            return resolve(out[v], depth + 1)
 223 | +        if depth < 4 and base(v) != v:
 224 | +            return resolve(base(v), depth + 1)
 225 | +        return v
 226 | +    return {k: resolve(v) for k, v in out.items()}
 227 | +
 228 | +
 229 | +def ledger_id(mid, lmap):
 230 | +    return lmap.get(mid) or lmap.get(base(mid)) or base(mid)
 231 | +
 232 | +
 233 | +def own_rating(r):
 234 | +    """The own-job rating as it stands today (ruling 61): the lower of scroll and alone; the recorded one when the
 235 | +    parts are missing."""
 236 | +    if isinstance(r.get("scroll"), int) and isinstance(r.get("alone"), int):
 237 | +        return min(r["scroll"], r["alone"])
 238 | +    return r.get("rating")
 239 | +
 240 | +
 241 | +def all_ratings(records, cache):
 242 | +    """{(moment id, rater): rating record with its text and the builds that used it}: the medley's records, and the
 243 | +    spotlight's own-job ratings completed from the hook cache (same moment id; the parts are the cache's)."""
 244 | +    texts = {}
 245 | +    for _, pk, inp in records:
 246 | +        for m in inp.get("moments") or []:
 247 | +            if isinstance(m, dict) and m.get("moment_id"):
 248 | +                texts.setdefault(m["moment_id"], m.get("text") or "")
 249 | +        for mid, m in ((pk.get("spotlight") or {}).get("moments") or {}).items():
 250 | +            if isinstance(m, dict):
 251 | +                texts.setdefault(mid, m.get("text") or "")
 252 | +    by_id = collections.defaultdict(list)
 253 | +    for key, recs in (cache or {}).items():
 254 | +        for rater, rec in (recs or {}).items():
 255 | +            by_id[key.split(":")[0]].append((rater, rec))
 256 | +    out = {}
 257 | +    for name, pk, _ in records:
 258 | +        for mid, r in (((pk.get("hook_pool") or {}).get("ratings")) or {}).items():
 259 | +            k = (mid, r.get("backend"))
 260 | +            out.setdefault(k, dict({p: r.get(p) for p in ("scroll", "alone", "setup", "why")}, rating=own_rating(r),
 261 | +                                   rating_recorded=r.get("rating"), moment_id=mid, rater=r.get("backend"),
 262 | +                                   text=texts.get(mid, ""), builds=[]))
 263 | +            out[k]["builds"].append(name)
 264 | +        for mid, m in (((pk.get("spotlight") or {}).get("moments")) or {}).items():
 265 | +            if not isinstance(m, dict) or m.get("hook_own") is None:
 266 | +                continue
 267 | +            for rater, rec in by_id.get(mid, []) or [(None, {})]:
 268 | +                k = (mid, rater)
 269 | +                out.setdefault(k, dict({p: rec.get(p) for p in ("scroll", "alone", "setup", "why")},
 270 | +                                       rating=own_rating(dict(rec, rating=m.get("hook_own"))),
 271 | +                                       rating_recorded=m.get("hook_own"), moment_id=mid, rater=rater,
 272 | +                                       text=texts.get(mid, ""), builds=[]))
 273 | +                out[k]["builds"].append(name)
 274 | +    return out
 275 | +
 276 | +
 277 | +def snapped_map(records):
 278 | +    """{a spotlight's widened span id: the moment id it came from}, over every build."""
 279 | +    out = {}
 280 | +    for _, pk, _ in records:
 281 | +        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
 282 | +            if isinstance(v, dict) and v.get("from"):
 283 | +                out[new] = v["from"]
 284 | +    return out
 285 | +
 286 | +
 287 | +def near_misses(ratings, n=10, fold=None):
 288 | +    """The n highest-rated hooks (rating, then the sum of the three parts), one per moment, and which part holds a
 289 | +    3 back from a 4. The rating is the own-job rating (ruling 61: the lower of scroll and alone)."""
 290 | +    best, fold = {}, fold or {}
 291 | +    for r in ratings.values():
 292 | +        if not isinstance(r.get("rating"), int):
 293 | +            continue
 294 | +        k = base(fold.get(r["moment_id"], r["moment_id"]))
 295 | +        key = (r["rating"], sum(int(r.get(p) or 0) for p in ("scroll", "alone", "setup")))
 296 | +        if k not in best or key > best[k][0]:
 297 | +            best[k] = (key, r)
 298 | +    top = [r for _, r in sorted(best.values(), key=lambda x: (-x[0][0], -x[0][1], x[1]["moment_id"]))[:n]]
 299 | +    threes = [r for _, r in best.values() if r["rating"] == 3]
 300 | +    held = collections.Counter()
 301 | +    for r in threes:
 302 | +        for p in ("scroll", "alone"):
 303 | +            if r.get(p) == 3:
 304 | +                held[p] += 1
 305 | +        if isinstance(r.get("setup"), int) and r["setup"] <= 3:
 306 | +            held["setup (not in the own-job rating since ruling 61)"] += 1
 307 | +    hist = collections.Counter(r["rating"] for _, r in best.values())
 308 | +    return {"top": top, "rated_distinct": len(best), "ratings": dict(sorted(hist.items())), "threes": len(threes),
 309 | +            "threes_held_back_by": dict(held.most_common())}
 310 | +
 311 | +
 312 | +def never_in_pool(lid, inputs_report):
 313 | +    """Why a ledger row gave no moment, from a build's own inputs report (ledger_build.build_inputs)."""
 314 | +    rep = inputs_report or {}
 315 | +    if lid in set(((rep.get("word_pass") or {}).get("refused")) or ()):
 316 | +        return "refused by the word pass (not sentence-ready; never re-worked)"
 317 | +    if lid in (rep.get("not_anchored") or {}):
 318 | +        return "did not re-anchor: " + str(rep["not_anchored"][lid])[:120]
 319 | +    if lid in (rep.get("duplicates_of") or {}):
 320 | +        return "a duplicate of " + str(rep["duplicates_of"][lid])
 321 | +    return "no moment in the latest build (not in its 12-h ledger, or no word record)"
 322 | +
 323 | +
 324 | +def hook_pass(db_path=QUEUE_DB, since_ts=None, videos=(), ledger=LEDGER, rated_ids=(), furthest=None,
 325 | +              inputs_report=None):
 326 | +    """Ruling 80's hook pass, from pp-ingest's own queue (read-only): its events since since_ts, classed; the given
 327 | +    videos' events and hook rows; whether any of their hook rows reached the hook job (rated_ids: LEDGER ids), and
 328 | +    how far each got (furthest: {ledger id: {"stage", "why"}})."""
 329 | +    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
 330 | +    db.row_factory = sqlite3.Row
 331 | +    ev = db.execute("SELECT e.at, e.ts, e.video_id, e.detail, c.display_name AS channel, v.title, v.moments "
 332 | +                    "FROM events e LEFT JOIN videos v ON v.video_id = e.video_id "
 333 | +                    "LEFT JOIN channels c ON c.channel_id = e.channel_id WHERE e.kind = 'hooks' AND e.ts >= ? "
 334 | +                    "ORDER BY e.ts", (since_ts or 0,)).fetchall()
 335 | +    classes, per_channel, mine = collections.Counter(), collections.defaultdict(collections.Counter), []
 336 | +    for r in ev:
 337 | +        d = json.loads(r["detail"] or "{}")
 338 | +        called = bool((d.get("cost") or 0) > 0 or (d.get("seconds_hook") or 0) >= 1)
 339 | +        cls = ("wrote rows" if d.get("rows") else "0 rows") + (", a model called" if called else ", no model call")
 340 | +        classes[cls] += 1
 341 | +        per_channel[r["channel"] or "?"][cls] += 1
 342 | +        if r["video_id"] in videos:
 343 | +            mine.append({"at": r["at"], "video_id": r["video_id"], "channel": r["channel"], "title": r["title"],
 344 | +                         "moments": r["moments"], **d})
 345 | +    hook_rows = collections.defaultdict(list)
 346 | +    try:
 347 | +        with open(ledger) as f:
 348 | +            for line in f:
 349 | +                try:
 350 | +                    row = json.loads(line)
 351 | +                except ValueError:
 352 | +                    continue
 353 | +                if isinstance(row, dict) and row.get("video_id") in videos and \
 354 | +                        (row.get("mined") or {}).get("pass") == "hook":
 355 | +                    hook_rows[row["video_id"]].append(row.get("moment_id"))
 356 | +    except OSError:
 357 | +        pass
 358 | +    reached = {v: sorted(set(ids) & set(rated_ids)) for v, ids in hook_rows.items()}
 359 | +    how_far = {v: {i: (furthest or {}).get(i) or {"stage": "never in a build's pool",
 360 | +                                                    "why": never_in_pool(i, inputs_report)} for i in ids}
 361 | +               for v, ids in hook_rows.items()}
 362 | +    return {"events": len(ev), "classes": dict(classes.most_common()),
 363 | +            "per_channel": {c: dict(x) for c, x in sorted(per_channel.items())}, "today": mine,
 364 | +            "hook_rows": {v: len(ids) for v, ids in hook_rows.items()}, "hook_rows_rated": reached,
 365 | +            "hook_rows_furthest": how_far}
 366 | +
 367 | +
 368 | +def ref_moments(refs=REFS):
 369 | +    """The approved hooks as the hook job reads a moment: an id of their own (so no production cache entry can
 370 | +    answer for them), the approved text verbatim, and the channel's name on screen."""
 371 | +    out = []
 372 | +    for key, label, path in refs:
 373 | +        seg = json.load(open(path))["segments"][0]
 374 | +        out.append({"moment_id": f"ref-{key}", "text": seg.get("approved_text") or seg.get("text") or "",
 375 | +                    "channel_id": f"ref:{seg.get('video_id')}", "channel_name": seg.get("channel") or "?",
 376 | +                    "label": label, "video_id": seg.get("video_id"),
 377 | +                    "seconds": round(float(seg.get("end") or 0) - float(seg.get("start") or 0), 2)})
 378 | +    return out
 379 | +
 380 | +
 381 | +def heimdall_hook_chain(router):
 382 | +    """Ruling 88's hook list as production reads it, with every non-Heimdall back-end removed (the order: Heimdall
 383 | +    only). Refused when none is left."""
 384 | +    chain = [n for n in router.chain("coherence_verdict", "hook")   # a Heimdall back-end's vendor is "heimdall/<family>"
 385 | +             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]
 386 | +    if not chain:
 387 | +        raise RuntimeError("refused: ruling 88's hook list has no Heimdall back-end")
 388 | +    return chain
 389 | +
 390 | +
 391 | +def build_router(spend_path=SPEND, record_dir=None):
 392 | +    import deadline_table as DT
 393 | +    import providers as P
 394 | +    import replay85 as R
 395 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 396 | +                 limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))
 397 | +    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)
 398 | +    return r
 399 | +
 400 | +
 401 | +def calibrate(router, refs, ctx, seeds=SEEDS, stop_usd=STOP_USD, rate=None):
 402 | +    """The hook job as it stands today (package.hook_ratings, cache None) on the approved hooks, once per seed, as
 403 | +    production asks it: avoiding the writers' vendor and family (package._writers). A call is made only under the
 404 | +    stop. -> [{"seed", "ratings": {id: record} or {}, "error"}]."""
 405 | +    import package as PK
 406 | +    rate = rate or PK.hook_ratings
 407 | +    wv, wf = PK._writers(router)
 408 | +    runs = []
 409 | +    for s in seeds:
 410 | +        if router.spent() >= stop_usd:
 411 | +            runs.append({"seed": s, "ratings": {}, "error": f"stopped: ${router.spent():.4f} spent (stop "
 412 | +                                                            f"${stop_usd:.2f})"})
 413 | +            continue
 414 | +        got, err = rate(router, refs, ctx, wv, wf, cache=None, seed=s)
 415 | +        runs.append({"seed": s, "ratings": got, "error": err, "writers": [sorted(wv), sorted(wf)]})
 416 | +    return runs
 417 | +
 418 | +
 419 | +def report(fun, cal, nm, hp):
 420 | +    L = ["# RULING 112: THE HOOK SCARCITY DIAGNOSIS", ""]
 421 | +    L += ["## (1) THE FUNNEL (the last 48 h of builds)", "",
 422 | +          f"{len(fun['builds'])} builds; {fun['distinct']} distinct moments (a variant is its moment).", "",
 423 | +          "| stage | distinct moments that reached it |", "|---|---|"]
 424 | +    L += [f"| {s} | {n} |" for s, n in fun["distinct_by_stage"].items()]
 425 | +    L += ["", "Never rated by the hook job, by the stage that stopped them (reason classes):", ""]
 426 | +    for s, c in fun["never_rated_stopped_before"].items():
 427 | +        L.append(f"- before \"{s}\": " + "; ".join(f"{k} {n}" for k, n in c.items()))
 428 | +    L += ["", "Per build (medley / spotlight: in a pool, may open, rated, rated >= 4):", ""]
 429 | +    for b in fun["builds"]:
 430 | +        m, s = b["medley"], b["spotlight"]
 431 | +        L.append(f"- {b['build']}: medley {m['in a pool']} / {m['may open']} / {m['rated by the hook job']} / "
 432 | +                 f"{m['rated >= 4']}; spotlight {s['in a pool']} / {s['may open']} / {s['rated by the hook job']} / "
 433 | +                 f"{s['rated >= 4']}")
 434 | +    L += ["", "## (2) CALIBRATION (the hook job as it stands today, Heimdall only, no cache)", ""]
 435 | +    for run in cal.get("runs") or []:
 436 | +        L.append(f"- seed {run['seed']}: " + ("; ".join(
 437 | +            f"{k}: {r.get('rating')} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
 438 | +            f"{r.get('backend')})" for k, r in (run.get("ratings") or {}).items()) or f"NO RATING: {run.get('error')}"))
 439 | +    L += ["", "## (3) THE NEAR MISSES", "",
 440 | +          f"{nm['rated_distinct']} distinct moments rated; ratings {nm['ratings']}; rated 3: {nm['threes']}, held back "
 441 | +          f"by {nm['threes_held_back_by']}", ""]
 442 | +    for r in nm["top"]:
 443 | +        L.append(f"- {r['rating']} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
 444 | +                 f"{r.get('rater')}) {r['moment_id']}: \"{(r.get('text') or '')[:160]}\" -- {r.get('why')}")
 445 | +    L += ["", "## (4) THE HOOK-MINING PASS (ruling 80)", "", f"{hp['events']} events: {hp['classes']}", ""]
 446 | +    for e in hp["today"]:
 447 | +        L.append(f"- {e['at'][:16]} {e['channel']} {e['video_id']}: windows {e.get('windows')}, screened "
 448 | +                 f"{e.get('screened')}, rows {e.get('rows')}, spotlight rows {e.get('spotlight_rows')}, dropped "
 449 | +                 f"{e.get('dropped')}")
 450 | +    L += [f"- hook rows in the ledger: {hp['hook_rows']}; of them rated by the hook job: {hp['hook_rows_rated']}"]
 451 | +    return "\n".join(L) + "\n"
 452 | +
 453 | +
 454 | +def main(argv=None):
 455 | +    ap = argparse.ArgumentParser()
 456 | +    ap.add_argument("--hours", type=float, default=48.0)
 457 | +    ap.add_argument("--no-calibration", action="store_true")
 458 | +    a = ap.parse_args(argv)
 459 | +    now = datetime.now(timezone.utc)
 460 | +    since = (now - timedelta(hours=a.hours)).strftime("ledger_%Y%m%d_%H%M%S")
 461 | +    os.makedirs(OUT, exist_ok=True)
 462 | +    recs = build_records(PROOF, since)
 463 | +    fun = funnel(recs)
 464 | +    cache = json.load(open(os.path.join(PROOF, "HOOK_CACHE.json")))
 465 | +    rts = all_ratings(recs, cache)
 466 | +    nm = near_misses(rts, fold=snapped_map(recs))
 467 | +    today = sorted({m.get("video_id") for m in (recs[-1][2].get("moments") or [])} if recs else set())
 468 | +    lmap = ledger_of(recs)
 469 | +    rated_ids = {ledger_id(k[0], lmap) for k in rts}
 470 | +    by_ledger = {}
 471 | +    for k, v in fun["furthest"].items():                 # the furthest stage of each moment, by its ledger id
 472 | +        lid = ledger_id(k, lmap)
 473 | +        if lid not in by_ledger or STAGES.index(v["stage"]) > STAGES.index(by_ledger[lid]["stage"]):
 474 | +            by_ledger[lid] = v
 475 | +    hp = hook_pass(QUEUE_DB, (now - timedelta(hours=a.hours)).timestamp(), today, LEDGER, rated_ids, by_ledger,
 476 | +                   (recs[-1][2].get("inputs") if recs else None))
 477 | +    cal = {"refs": [], "runs": [], "skipped": a.no_calibration}
 478 | +    if not a.no_calibration:
 479 | +        import eligibility as E
 480 | +        import proof_saved_runs as PS
 481 | +        refs = ref_moments()
 482 | +        router = build_router(SPEND, os.path.join(OUT, "replies"))
 483 | +        cal = {"refs": refs, "chain": router.chain("coherence_verdict", "hook"),
 484 | +               "runs": calibrate(router, refs, E.Context(now, PS.REG)), "spent_usd": round(router.spent(), 6)}
 485 | +    for fname, obj in (("FUNNEL.json", fun), ("CALIBRATION.json", cal), ("NEAR_MISSES.json", nm),
 486 | +                       ("HOOK_PASS.json", hp)):
 487 | +        with open(os.path.join(OUT, fname), "w") as f:
 488 | +            json.dump(obj, f, indent=1, default=str)
 489 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 490 | +        f.write(report(fun, cal, nm, hp))
 491 | +    print(f"ruling 112: {len(recs)} builds since {since}; {fun['distinct']} distinct moments; "
 492 | +          f"{nm['rated_distinct']} rated; calibration {'skipped' if a.no_calibration else cal.get('spent_usd')}")
 493 | +    return 0
 494 | +
 495 | +
 496 | +if __name__ == "__main__":
 497 | +    sys.exit(main())
 498 | diff --git a/tests/package/test_hook112.py b/tests/package/test_hook112.py
 499 | new file mode 100644
 500 | index 0000000..c956269
 501 | --- /dev/null
 502 | +++ b/tests/package/test_hook112.py
 503 | @@ -0,0 +1,233 @@
 504 | +#!/usr/bin/env python3
 505 | +"""RULING 112's diagnosis driver (tests/package/hook112.py), offline: where each moment stopped on the way to the hook
 506 | +job (both paths), the distinct roll-up, the near misses and the part that holds a 3 back, pp-ingest's hook pass read
 507 | +from a database of the same shape, and the calibration's guards (Heimdall only, no cache, the stop)."""
 508 | +import json
 509 | +import os
 510 | +import sqlite3
 511 | +import sys
 512 | +import tempfile
 513 | +import unittest
 514 | +
 515 | +HERE = os.path.dirname(os.path.abspath(__file__))
 516 | +REPO = os.path.dirname(os.path.dirname(HERE))
 517 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 518 | +sys.path.insert(0, HERE)
 519 | +import hook112 as H  # noqa: E402
 520 | +
 521 | +
 522 | +def medley_pk(why_none=None, went_on=True, hook_error=None):
 523 | +    pre = {"screened": 9, "cleared": 6, "failed": {"f": ["REFERENT_OUTSIDE"]}}
 524 | +    if went_on:
 525 | +        pre.update(second_pass={"c": "L-v 2 FAIL", "t": "PASS", "o": "PASS", "x": "PASS", "r3": "PASS", "r4": "PASS"},
 526 | +                   hook_onset={"t": "PASS", "o": "FAIL: 0 ms of genuine quiet", "x": "PASS", "r3": "PASS",
 527 | +                               "r4": "PASS"},
 528 | +                   trim_cut={"t": "FAIL: no trimmed cut was reached"})
 529 | +    return {"unusable": {"u": "22.9 s: over the 20.0 s per source video (L-u) or unmeasured"},
 530 | +            "no_role": {"n": "the render's STAND_ALONE topic rule with the pin's screen (ruling 34)"},
 531 | +            "ad_read": {"a": "an ad-read marker"}, "reposted": {"p": "q"}, "prescreen": pre, "why_none": why_none,
 532 | +            "hook_pool": {"error": hook_error, "ratings": {} if not went_on else {
 533 | +                "r3": {"scroll": 3, "alone": 5, "setup": 4, "rating": 3, "why": "slow start"},
 534 | +                "r4": {"scroll": 4, "alone": 5, "setup": 2, "rating": 2, "why": "old rule: setup counted"}}}}
 535 | +
 536 | +
 537 | +def inputs(ids):
 538 | +    return {"moments": [{"moment_id": i, "text": f"text {i}", "mined": {"ledger_moment_id": f"L{i}"}} for i in ids]}
 539 | +
 540 | +
 541 | +POOL = ["u", "n", "a", "p", "f", "c", "t", "o", "x", "r3", "r4", "s"]
 542 | +
 543 | +
 544 | +class TestTheMedleyTrace(unittest.TestCase):
 545 | +
 546 | +    def test_each_moment_stops_where_its_record_says(self):
 547 | +        tr = H.medley_trace(medley_pk(), inputs(POOL))
 548 | +        got = {k: v[0] for k, v in tr.items()}
 549 | +        self.assertEqual(got, {"u": 0, "n": 0, "a": 0, "p": 0, "f": 1, "c": 2, "t": 3, "o": 3, "x": 3, "r3": 5,
 550 | +                               "r4": 6, "s": 1})
 551 | +        self.assertIn("cannot open", tr["x"][1])                       # passed G17a, never rated: it cannot open
 552 | +        self.assertEqual(tr["r3"][1], "rated 3")
 553 | +        self.assertIsNone(tr["r4"][1])          # today's rule: the lower of scroll / alone (4), not the recorded 2
 554 | +
 555 | +    def test_the_3_channel_rule_and_a_failed_hook_call(self):
 556 | +        tr = H.medley_trace(medley_pk("6 moments cleared step A from fewer than 3 channels", went_on=False),
 557 | +                            inputs(POOL))
 558 | +        self.assertEqual((tr["t"][0], tr["f"][0]), (2, 1))           # cleared, then the medley ended
 559 | +        self.assertIn("3-channel rule", tr["t"][1])
 560 | +        tr = H.medley_trace(medley_pk(hook_error="ProviderError: no back-end"), inputs(POOL))
 561 | +        self.assertEqual(tr["x"][0], 4)                                # it may open; the call failed: not rated
 562 | +        self.assertIn("not rated", tr["x"][1])
 563 | +
 564 | +
 565 | +class TestTheSpotlightTrace(unittest.TestCase):
 566 | +
 567 | +    def test_free_screens_step_a_and_the_hook(self):
 568 | +        pk = {"spotlight": {"pool": {"out": {"long": "35.6 s: over the 35.0 s per source video"},
 569 | +                                     "snapped": {"w1": {"from": "m1"}}},
 570 | +                            "moments": {"al": {"stage": 0, "out": "the ALONE scorer: 2.0 (needs 4) (ruling 109)"},
 571 | +                                        "sa": {"stage": 0, "out": "step A: REFERENT_OUTSIDE"},
 572 | +                                        "lv": {"stage": 1, "out": "L-v 2 / CUTTABLE: the second pass disagrees"},
 573 | +                                        "co": {"stage": 2, "out": "it cannot open cold: G17a"},
 574 | +                                        "w1": {"stage": 3, "out": "the hook's own job rates 3", "hook_own": 3},
 575 | +                                        "h4": {"stage": 5, "out": "the visual check", "hook_own": 4}}}}
 576 | +        tr = H.spotlight_trace(pk)
 577 | +        self.assertEqual({k: v[0] for k, v in tr.items()},
 578 | +                         {"long": 0, "al": 0, "sa": 1, "lv": 2, "co": 3, "m1": 5, "h4": 6})   # w1 is m1's span
 579 | +
 580 | +
 581 | +class TestTheRollUp(unittest.TestCase):
 582 | +
 583 | +    def test_the_furthest_stage_over_builds_a_tie_keeps_the_latest_reason_and_variants_fold(self):
 584 | +        b1 = (medley_pk(), inputs(POOL))
 585 | +        pk2 = medley_pk()
 586 | +        pk2["prescreen"]["failed"] = {"f": ["CONDITION_OUTSIDE"]}       # the same stage, a newer reason
 587 | +        pk2["prescreen"]["second_pass"]["c~trim"] = "PASS"
 588 | +        pk2["prescreen"]["hook_onset"]["c~trim"] = "PASS"
 589 | +        pk2["hook_pool"]["ratings"]["c~trim"] = {"scroll": 2, "alone": 4, "setup": 2, "rating": 2, "why": "w"}
 590 | +        fu = H.funnel([("ledger_1", *b1), ("ledger_2", pk2, inputs(POOL))])
 591 | +        self.assertEqual(fu["furthest"]["f"]["why"], "step A: CONDITION_OUTSIDE")
 592 | +        self.assertEqual(fu["furthest"]["c"]["stage"], "rated by the hook job")   # its ~trim variant was rated
 593 | +        self.assertEqual((fu["distinct"], fu["distinct_by_stage"]["rated >= 4"]), (12, 1))
 594 | +        self.assertEqual(fu["never_rated_stopped_before"]["cleared step A"],      # s: in the pool, no stage record
 595 | +                         {"step A: CONDITION_OUTSIDE": 1, "the medley ended before step A": 1})
 596 | +
 597 | +
 598 | +class TestTheNearMisses(unittest.TestCase):
 599 | +
 600 | +    def test_ranked_one_per_moment_on_todays_rule_and_the_part_that_holds_a_3(self):
 601 | +        rs = {("a", "q"): {"moment_id": "a", "scroll": 4, "alone": 5, "setup": 5, "rating": 4},
 602 | +              ("a~trim", "q"): {"moment_id": "a~trim", "scroll": 4, "alone": 4, "setup": 4, "rating": 4},
 603 | +              ("w", "q"): {"moment_id": "w", "scroll": 5, "alone": 5, "setup": 5, "rating": 5},   # a span of b
 604 | +              ("b", "q"): {"moment_id": "b", "scroll": 3, "alone": 5, "setup": 3, "rating": 3},
 605 | +              ("c", "q"): {"moment_id": "c", "scroll": 3, "alone": 3, "setup": 5, "rating": 3},
 606 | +              ("d", "q"): {"moment_id": "d", "scroll": 2, "alone": 4, "setup": 4, "rating": 2},
 607 | +              ("e", "q"): {"moment_id": "e", "scroll": 3, "alone": 4, "setup": 3, "rating": 3}}
 608 | +        nm = H.near_misses(rs, n=3, fold={"w": "b"})
 609 | +        self.assertEqual([r["moment_id"] for r in nm["top"]], ["w", "a", "c"])   # b's best is its span w
 610 | +        self.assertEqual((nm["rated_distinct"], nm["threes"]), (5, 2))
 611 | +        self.assertEqual(nm["threes_held_back_by"], {"scroll": 2, "alone": 1,      # setup is shown apart: not a part
 612 | +                                                     "setup (not in the own-job rating since ruling 61)": 1})
 613 | +        self.assertEqual(H.own_rating({"scroll": 4, "alone": 5, "setup": 2, "rating": 2}), 4)   # ruling 61
 614 | +
 615 | +
 616 | +class TestTheHookPass(unittest.TestCase):
 617 | +
 618 | +    def db(self, d):
 619 | +        p = os.path.join(d, "queue.sqlite")
 620 | +        db = sqlite3.connect(p)
 621 | +        db.executescript("CREATE TABLE events (id INTEGER, at TEXT, ts REAL, video_id TEXT, channel_id TEXT, kind TEXT, "
 622 | +                         "detail TEXT); CREATE TABLE videos (video_id TEXT, title TEXT, moments INTEGER); "
 623 | +                         "CREATE TABLE channels (channel_id TEXT, display_name TEXT);")
 624 | +        db.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", [
 625 | +            (1, "2026-11-15T13:24:51", 100.0, "bl", "cb", "hooks", json.dumps({"rows": 0, "windows": 4, "cost": 0.0,
 626 | +                                                                               "seconds_hook": 0.1})),
 627 | +            (2, "2026-11-15T15:05:56", 200.0, "v1", "cm", "hooks", json.dumps({"rows": 2, "windows": 18, "cost": 0.004,
 628 | +                                                                               "seconds_hook": 9.0})),
 629 | +            (3, "2026-11-15T15:06:00", 210.0, "v2", "cm", "hooks", json.dumps({"rows": 0, "windows": 3, "cost": 0.001,
 630 | +                                                                               "seconds_hook": 4.0})),
 631 | +            (4, "2026-11-13T00:00:00", 1.0, "old", "cb", "hooks", json.dumps({"rows": 0}))])
 632 | +        db.executemany("INSERT INTO channels VALUES (?, ?)", [("cb", "Bloomberg Television"), ("cm", "Magazine")])
 633 | +        db.executemany("INSERT INTO videos VALUES (?, ?, ?)", [("bl", "IPO", 0), ("v1", "BTC", 29), ("v2", "BTC2", 3)])
 634 | +        db.commit()
 635 | +        db.close()
 636 | +        return p
 637 | +
 638 | +    def test_classes_the_given_videos_and_whether_their_hook_rows_reached_the_job(self):
 639 | +        with tempfile.TemporaryDirectory() as d:
 640 | +            led = os.path.join(d, "ledger.jsonl")
 641 | +            with open(led, "w") as f:
 642 | +                for mid, ps in (("h1", "hook"), ("h2", "hook"), ("m1", "moment"), ("h3", "hook")):
 643 | +                    f.write(json.dumps({"moment_id": mid, "video_id": "v1", "mined": {"pass": ps}}) + "\n")
 644 | +            hp = H.hook_pass(self.db(d), 50.0, ["v1"], led, rated_ids={"h1", "m1"},
 645 | +                             furthest={"h2": {"stage": "cleared step A", "why": "not cuttable"}},
 646 | +                             inputs_report={"word_pass": {"refused": ["h3"]}})
 647 | +        self.assertEqual(hp["classes"], {"0 rows, no model call": 1, "wrote rows, a model called": 1,
 648 | +                                         "0 rows, a model called": 1})        # the old event is outside the window
 649 | +        self.assertEqual(hp["per_channel"]["Bloomberg Television"], {"0 rows, no model call": 1})
 650 | +        self.assertEqual([e["video_id"] for e in hp["today"]], ["v1"])
 651 | +        self.assertEqual((hp["hook_rows"], hp["hook_rows_rated"]), ({"v1": 3}, {"v1": ["h1"]}))
 652 | +        self.assertEqual(hp["hook_rows_furthest"]["v1"]["h2"]["why"], "not cuttable")
 653 | +        self.assertIn("refused by the word pass", hp["hook_rows_furthest"]["v1"]["h3"]["why"])
 654 | +
 655 | +    def test_a_read_only_database_file_serves(self):
 656 | +        with tempfile.TemporaryDirectory() as d:
 657 | +            p = self.db(d)
 658 | +            os.chmod(p, 0o444)                        # a writer would fail to open a read-only file for writing
 659 | +            try:
 660 | +                self.assertEqual(H.hook_pass(p, 0.0, [], os.path.join(d, "none.jsonl"))["events"], 4)
 661 | +            finally:
 662 | +                os.chmod(p, 0o644)
 663 | +
 664 | +
 665 | +class TestTheLedgerIds(unittest.TestCase):
 666 | +
 667 | +    def test_a_span_a_variant_and_a_moment_resolve_to_the_ledger_row(self):
 668 | +        pk = {"spotlight": {"pool": {"snapped": {"w1": {"from": "m1~trim"}, "w2": {"from": "m2"}}}}}
 669 | +        inp = {"moments": [{"moment_id": "m1", "mined": {"ledger_moment_id": "L1"}},
 670 | +                           {"moment_id": "m2", "mined": {"ledger_moment_id": "L2"}}]}
 671 | +        lmap = H.ledger_of([("ledger_1", pk, inp)])
 672 | +        self.assertEqual([H.ledger_id(i, lmap) for i in ("w1", "w2", "m1", "m1~trim", "zz")],
 673 | +                         ["L1", "L2", "L1", "L1", "zz"])
 674 | +
 675 | +
 676 | +class B:
 677 | +    def __init__(self, vendor):
 678 | +        self.vendor, self.family = vendor, vendor
 679 | +
 680 | +
 681 | +class FakeRouter:
 682 | +    def __init__(self, chain, spent=0.0):
 683 | +        self._chain, self._spent, self.down, self.chains = chain, spent, set(), {}
 684 | +        self.backends = {"heimdall:qwen": B("heimdall/qwen"), "heimdall:glm": B("heimdall/glm"), "xai:grok": B("xai"),
 685 | +                         "openai:gpt": B("openai")}          # the vendors as providers.HeimdallBackend gives them
 686 | +
 687 | +    def chain(self, role, kind=None):
 688 | +        return list(self.chains.get(f"{role}:{kind}") or (["openai:gpt"] if role == "angle_write" else self._chain))
 689 | +
 690 | +    def spent(self):
 691 | +        return self._spent
 692 | +
 693 | +
 694 | +class TestTheCalibration(unittest.TestCase):
 695 | +
 696 | +    def test_the_drivers_router_asks_the_hook_job_on_heimdall_only(self):
 697 | +        with tempfile.TemporaryDirectory() as d:
 698 | +            r = H.build_router(spend_path=os.path.join(d, "SPEND.json"))
 699 | +        chain = r.chain("coherence_verdict", "hook")
 700 | +        self.assertTrue(chain and all(r.backends[n].vendor.split("/")[0] == "heimdall" for n in chain), chain)
 701 | +        self.assertNotIn("xai:grok-4.20-0309-reasoning", chain)
 702 | +        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 88's order, Grok removed
 703 | +        self.assertEqual((r.limit_usd, r.limit_basis), (H.LIMIT_USD, "reported"))
 704 | +
 705 | +    def test_heimdall_only_and_refused_without_one(self):
 706 | +        self.assertEqual(H.heimdall_hook_chain(FakeRouter(["heimdall:qwen", "xai:grok", "heimdall:glm"])),
 707 | +                         ["heimdall:qwen", "heimdall:glm"])
 708 | +        with self.assertRaises(RuntimeError):
 709 | +            H.heimdall_hook_chain(FakeRouter(["xai:grok"]))
 710 | +
 711 | +    def test_production_writers_no_cache_every_seed_and_the_stop(self):
 712 | +        asked = []
 713 | +
 714 | +        def rate(router, ms, ctx, wv, wf, cache="unset", seed=None):
 715 | +            asked.append((cache, seed, sorted(wv)))
 716 | +            return {m["moment_id"]: {"rating": 4} for m in ms}, None
 717 | +        refs = [{"moment_id": "ref-a", "text": "t"}]
 718 | +        runs = H.calibrate(FakeRouter(["heimdall:qwen"]), refs, None, seeds=(7, 8), stop_usd=0.25, rate=rate)
 719 | +        self.assertEqual(asked, [(None, 7, ["openai"]), (None, 8, ["openai"])])   # no cache; the writers' vendor
 720 | +        self.assertEqual([r["seed"] for r in runs], [7, 8])
 721 | +        asked.clear()
 722 | +        runs = H.calibrate(FakeRouter(["heimdall:qwen"], spent=0.25), refs, None, seeds=(7,), stop_usd=0.25,
 723 | +                           rate=rate)
 724 | +        self.assertEqual((asked, runs[0]["ratings"]), ([], {}))                  # at the stop: no call
 725 | +        self.assertIn("stopped", runs[0]["error"])
 726 | +
 727 | +    def test_the_approved_hooks_get_ids_no_production_cache_entry_can_answer(self):
 728 | +        refs = H.ref_moments()
 729 | +        self.assertEqual([r["moment_id"] for r in refs], [f"ref-{k}" for k, _, _ in H.REFS])
 730 | +        cache = json.load(open(os.path.join(H.PROOF, "HOOK_CACHE.json")))
 731 | +        self.assertFalse(any(k.split(":")[0].startswith("ref-") for k in cache))
 732 | +        self.assertTrue(all(r["text"] for r in refs))
 733 | +
 734 | +
 735 | +if __name__ == "__main__":
 736 | +    unittest.main()
 737 | 
```

---

pp-selectid: RULING 112 (orchestrator 11:15 ET Nov 15), THE HOOK SCARCITY DIAGNOSIS. A new driver,
tests/package/hook112.py, and its tests. No bar, gate or routing changes; nothing in pipeline/ is touched.

THE ORDER, in short: before anyone touches the hook bar, find whether the supply is truly weak or the path to a hook
is too narrow. Heimdall only, cap $0.30. The parts:
(1) the funnel for the last 48 h of builds: pool -> allowed to open (with the exclusions by reason) -> rated by the
    hook job -> rated >= 4; how many DISTINCT moments were ever rated, and how many never were, and what removed them;
(2) calibration: the hook job as it stands today on the approved hooks (the protected preview, 37c5b5f5, 41f29b1f,
    the published 0c68b589); an approved hook rated below 4 means rater drift;
(3) the 10 best hooks of the 48 h with their parts and reason, and which part most often holds a 3 back from a 4;
(4) pp-ingest's hook-mining pass (ruling 80) for today's videos;
(5) a recommendation (written by hand from the outputs; not code).

THE DRIVER, READ-ONLY EXCEPT PART (2):
- build_records: every tests/package/proof/ledger_*/package.json and inputs.json since a cutoff.
- medley_trace / spotlight_trace place each moment on ONE scale of 7 stages ("in a pool" ... "rated >= 4") from each
  build's own record:
  - the medley: unusable, no_role, ad_read, reposted, prescreen.failed / second_pass / hook_onset / trim_cut, and
    hook_pool.ratings. These are written by package.build: the second pass at :2617, G17a, then
    `openers = {... if can_open(m)}` at :2643, hook_pool at :2666 (pipeline/package.py, UNCHANGED).
  - the spotlight: pool.out, and moments[*].stage / out / hook_own (spotlight.build :813, UNCHANGED). A stage-0 stop
    is a free screen unless it is step A's (ruling 109's ALONE gate stops at stage 0 BEFORE step A, :858). A
    widened span (pool.snapped) counts as the moment it came from.
- funnel: per build, and DISTINCT moments (a ~trim / ~tail variant is its moment) at their furthest stage over every
  build and both paths. A tie keeps the LATEST build's reason. Classes of the reasons for the never-rated.
- all_ratings + near_misses: every hook rating in the window (the medley's hook_pool.ratings; the spotlight's
  hook_own, completed from HOOK_CACHE.json by moment id), on TODAY's rule. That rule is own_rating, the lower of
  scroll and alone (ruling 61; package.hook_own :1383): an early record that stored a three-part rating is read on
  today's rule. One entry per moment, ranked by rating and then the sum of the parts. "Held back": among those
  rated 3, which part is at 3 (setup is shown apart; it is not in the rating since ruling 61).
- ledger_of / ledger_id: a build gives each re-anchored moment its OWN id (0 of 57 equal their ledger id in
  ledger_20261115_151621); mined.ledger_moment_id maps back, and snapped spans and variants resolve through it.
- hook_pass: pp-ingest's queue database opened with mode=ro (sqlite URI), its 'hooks' events (classed: rows or not,
  a model called or not), the given videos' events, their hook rows in pp-ingest's ledger (read), and how far each
  got in our builds (never_in_pool: the latest build's own inputs report: word-pass refusal, no re-anchor, or a
  duplicate).

THE PAID PART, (2) calibrate:
- package.hook_ratings (:863, UNCHANGED) with cache=None. _load_cache(None) is {} (:497; open(None) raises TypeError,
  caught) and _cache_put(None, ...) returns at once (:508), so the production HOOK_CACHE.json is neither read nor
  written.
- The approved hooks get ids "ref-<key>", so no cached rating can answer for them.
- Asked as production asks: avoiding package._writers(router)'s vendor and family, once per seed (7 is production's;
  8 and 9 show stability).
- The router (build_router) is providers.Router under heimdall_first, built DIRECTLY: not proof_ledger.build_router,
  so no ruling-86 shadow (Grok). Its own spend ledger is tests/package/proof/SPEND_H112.json, limit $0.30 (the
  order's cap); no call starts at or over STOP_USD $0.25.
- Its hook list (ruling 88, "coherence_verdict:hook", providers.Router.chain :794) is production's with every
  non-Heimdall back-end removed: heimdall_hook_chain keeps a back-end whose vendor is "heimdall/<family>" (that is
  how providers.HeimdallBackend names it), and refuses when none is left. Today's list is qwen, glm, deepseek;
  Grok is dropped.

TESTS: tests/package/test_hook112.py (12), offline. Both traces stage by stage. The roll-up's furthest stage, the
latest reason on a tie, and folded variants. The near misses on today's rule, folded, with the held-back counts. The
hook pass over a database and ledger of the same shape. The ledger-id resolution. A REAL Router built by
build_router: its hook chain is Heimdall only, qwen first, no Grok. The calibration's guards: no cache, production's
writers, every seed, no call at the stop, refusal without a Heimdall back-end, and the reference ids absent from
the production cache. 15 of 15 mutations killed after a control run (the unmutated copy passes all 12). Suites: 697
pass.

PLEASE CHECK: (1) that both traces place every moment where package.build and spotlight.build actually stopped it (the
cited lines); (2) the roll-up, the tie rule, and the ledger-id mapping; (3) the near misses' rule and the held-back
count; (4) that the calibration can reach no non-Heimdall back-end, no shadow, and no production cache or spend
ledger, and stops under the cap; (5) that the hook pass and every other read cannot write to pp-ingest's or the
main tree's files; (6) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
