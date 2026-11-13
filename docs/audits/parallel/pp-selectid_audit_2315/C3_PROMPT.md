# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2315
# Branch: pp-selectid
# Generated: 2026-11-12 23:34 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2315/C3_STEP.diff (621 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | new file mode 100644
   3 | index 00000000..4bacc40c
   4 | --- /dev/null
   5 | +++ b/pipeline/ledger_build.py
   6 | @@ -0,0 +1,212 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/ledger_build.py — ORCHESTRATOR 22:40 ruling 2: the medley built from the INGEST LEDGER, the path to the first
   9 | +FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call here (package.build makes those).
  10 | +
  11 | +- rows(): pp-ingest's own adapter, pipeline.ingest.ledger.best_unused_moments, with its exclusions applied: delivered,
  12 | +  opted out, hard flags, altcoin or not about Bitcoin, a speaker change, re-uploads. It runs read-only in its own
  13 | +  interpreter, from the pp-ingest worktree, until the integrator merges it.
  14 | +- READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  15 | +  (transcripts/<vid>/transcript.whisper_words*.json, punctuated first, its segments sha checked). Window records from
  16 | +  the word-pass worker (the integrator's contract: transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json,
  17 | +  youtube clock, listed in moments/word_pass.jsonl) need their L-s context from the CAPTION record. That is not wired
  18 | +  yet: such rows are counted in the report and not used.
  19 | +- RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  20 | +  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  21 | +  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  22 | +  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
  23 | +- RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  24 | +  row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  25 | +-> build_inputs(...) = (moments, sources, report).
  26 | +"""
  27 | +import glob
  28 | +import json
  29 | +import os
  30 | +import sys
  31 | +
  32 | +import eligibility as E
  33 | +import moments as M
  34 | +import select_by_id as S
  35 | +import sentence_law as SL
  36 | +import transcript_store as ts
  37 | +
  38 | +SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
  39 | +SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
  40 | +                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
  41 | +                                      r"\w+n't)$|\d", __import__("re").I)
  42 | +                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
  43 | +                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1)
  44 | +APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}   # a typographic apostrophe is read as ' by the guard
  45 | +SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]. Captions
  46 | +                          # and word records share the full-video clock, and a caption cue starts or ends a few
  47 | +                          # seconds off the words; the window only keeps a phrase said again elsewhere in the video
  48 | +                          # from anchoring. A row the window misses is a counted, named drop.
  49 | +INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  50 | +MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
  51 | +STORE = os.path.join(MAIN, "data", "editorial")
  52 | +
  53 | +
  54 | +_ROWS = """
  55 | +import json, sys
  56 | +from datetime import datetime
  57 | +sys.path.insert(0, sys.argv[1])
  58 | +from pipeline.ingest import ledger as IL
  59 | +a = json.loads(sys.stdin.read())
  60 | +rows, rep = IL.best_unused_moments(a["path"], datetime.fromisoformat(a["since"]), datetime.fromisoformat(a["now"]),
  61 | +                                   a["delivered"], store_root=a["store_root"], horizon_h=a["horizon_h"])
  62 | +sys.stdout.write(json.dumps({"rows": rows, "report": rep}, default=str))
  63 | +"""
  64 | +
  65 | +
  66 | +def rows(since, now, delivered_ids=(), ingest_root=INGEST_ROOT, horizon_h=72, timeout=300):
  67 | +    """pp-ingest's adapter, best_unused_moments, run read-only in its OWN interpreter, from its worktree until the
  68 | +    integrator merges it. Its store guard refuses a process in which another transcript_store was imported first, so
  69 | +    the two never share modules. -> (rows, report). Raises RuntimeError when the adapter FAILS or REFUSES (fail
  70 | +    closed: a failure is never read as an empty ledger). An empty successful read is a real result: no row passes the
  71 | +    ledger's own exclusions, and the report's counts say why."""
  72 | +    import subprocess
  73 | +    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
  74 | +            "since": since.isoformat(), "now": now.isoformat(), "delivered": list(delivered_ids),
  75 | +            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": horizon_h}
  76 | +    env = dict(os.environ, PP_SELECTID_PIPELINE=os.path.dirname(os.path.abspath(__file__)))
  77 | +    try:
  78 | +        p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
  79 | +                           text=True, cwd=ingest_root, env=env, timeout=timeout)
  80 | +    except subprocess.TimeoutExpired:                   # a failure like any other: RuntimeError (glm C2 N-5)
  81 | +        raise RuntimeError(f"the ledger adapter did not answer in {timeout} s") from None
  82 | +    if p.returncode != 0:
  83 | +        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
  84 | +    try:
  85 | +        out = json.loads(p.stdout)
  86 | +        got, report = out["rows"], out["report"] or {}
  87 | +        if not isinstance(got, list) or not isinstance(report, dict):
  88 | +            raise TypeError("'rows' is not a list or 'report' is not an object")
  89 | +    except (ValueError, KeyError, TypeError) as e:
  90 | +        raise RuntimeError(f"the ledger adapter's answer cannot be read ({type(e).__name__}: {str(e)[:160]})") from None
  91 | +    if report.get("contract"):
  92 | +        raise RuntimeError(f"the ledger adapter refused: {report['contract']}")
  93 | +    return got, report
  94 | +
  95 | +
  96 | +def word_source(row, ctx, store=STORE):
  97 | +    """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
  98 | +    checked), as an eligibility Source with the row's identity -> (Source, path, passed_over), or (None, None,
  99 | +    passed_over). passed_over names every record read and not used, in reading order, each with why ("<file>: <why>";
 100 | +    "no word record in the store" when there is none). A Source that comes with a non-empty passed_over is a fallback
 101 | +    from the punctuated record, and is visible as one (audit 2315 C2: all three reviewers)."""
 102 | +    vid = row["video_id"]
 103 | +    paths = sorted(glob.glob(os.path.join(store, "transcripts", vid, "transcript.whisper_words*.json")),
 104 | +                   key=lambda p: "punct" not in p)
 105 | +    if not paths:
 106 | +        return None, None, ["no word record in the store"]
 107 | +    reg = ctx.channel(row.get("channel_id")) or {}
 108 | +    passed_over = []
 109 | +    for p in paths:
 110 | +        name = os.path.basename(p)
 111 | +        try:
 112 | +            with open(p) as f:
 113 | +                rec = json.load(f)
 114 | +        except (OSError, ValueError):
 115 | +            passed_over.append(f"{name}: cannot be read")
 116 | +            continue
 117 | +        if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
 118 | +            passed_over.append(f"{name}: its segments do not match its transcript_sha256")
 119 | +            continue
 120 | +        timing, toks = S.tokens_from_record(rec)
 121 | +        src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 122 | +                       row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
 123 | +                       timing=timing, title=row.get("title") or "", file_head=True, vod=True)
 124 | +        if E.sentence_ready(src):
 125 | +            return src, p, passed_over
 126 | +        passed_over.append(f"{name}: not sentence-ready (law L-e)")
 127 | +    return None, None, passed_over
 128 | +
 129 | +
 130 | +def reanchor(row, src):
 131 | +    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
 132 | +    def num(x):
 133 | +        try:
 134 | +            return float(x)
 135 | +        except (TypeError, ValueError):
 136 | +            return None                                 # an unreadable time only widens the search (glm C1 P1-9)
 137 | +    t0, t1 = num(row.get("start")), num(row.get("end"))
 138 | +    hit = SL.anchor(src.tokens, row.get("text") or "",
 139 | +                    t0=(t0 - SEARCH_PAD_S) if t0 is not None else None,
 140 | +                    t1=(t1 + SEARCH_PAD_S) if t1 is not None else None)
 141 | +    if hit is None:
 142 | +        return None, (f"the row's text does not anchor in the word record (sentence_law.anchor"
 143 | +                      + (f", searched {t0 - SEARCH_PAD_S:.0f}-{t1 + SEARCH_PAD_S:.0f} s)" if t0 is not None and
 144 | +                         t1 is not None else ")"))
 145 | +    i0, i1, ratio = hit
 146 | +    k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
 147 | +    k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
 148 | +    if k0 is None or k1 is None:
 149 | +        return None, "the anchored words fall outside the record's sentences"
 150 | +    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
 151 | +    if left > SNAP_WORDS or right > SNAP_WORDS:
 152 | +        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
 153 | +                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
 154 | +    added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
 155 | +             for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
 156 | +    # a typographic apostrophe reads as ' here (glm C2 N-3; none of the store's 66 word records holds one today)
 157 | +    risky = [w for w in added if SNAP_GUARD.search(w)]
 158 | +    if risky:
 159 | +        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
 160 | +    sp = E.Span(src, k0, k1)
 161 | +    return sp, {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 162 | +
 163 | +
 164 | +def build_inputs(rows, ctx, store=STORE, log=print):
 165 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 166 | +    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 167 | +    each counted with why."""
 168 | +    report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "fallbacks": {},
 169 | +              "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "moments": 0, "videos": 0,
 170 | +              "word_records": {}}
 171 | +    by_vid = {}
 172 | +    for r in rows:
 173 | +        by_vid.setdefault(r["video_id"], []).append(r)
 174 | +    moments, sources, seen = [], {}, set()
 175 | +    for vid, rs in by_vid.items():
 176 | +        channels = sorted({str(r.get("channel_id")) for r in rs})
 177 | +        if len(channels) > 1:       # one uploader per video, checked, not assumed (audit 2315 C2: qwen P1, glm P1)
 178 | +            report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
 179 | +            continue
 180 | +        src, path, passed_over = word_source(rs[0], ctx, store)
 181 | +        if src is None:
 182 | +            why = "; ".join(passed_over)
 183 | +            report["no_word_record"] += len(rs)
 184 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 185 | +            continue
 186 | +        if passed_over:
 187 | +            report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 188 | +        report["word_records"][vid] = os.path.relpath(path, store)        # read; whether a moment came of it: moments
 189 | +        for r in rs:
 190 | +            sp, info = reanchor(r, src)
 191 | +            if sp is None:
 192 | +                report["not_anchored"][r["moment_id"]] = info
 193 | +                continue
 194 | +            if (vid, sp.k0, sp.k1) in seen:
 195 | +                report["duplicates"] += 1
 196 | +                continue
 197 | +            try:
 198 | +                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 199 | +                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 200 | +                     "reason": r.get("reason") or ""}
 201 | +                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 202 | +                             ledger_text=r.get("text"))
 203 | +                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 204 | +                rec["rank_score"] = M.rank_score(rec)
 205 | +            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 206 | +                report["malformed"][r.get("moment_id")] = f"{type(e).__name__}: {str(e)[:120]}"
 207 | +                continue
 208 | +            seen.add((vid, sp.k0, sp.k1))
 209 | +            moments.append(rec)
 210 | +            sources[vid] = src
 211 | +    report["moments"], report["videos"] = len(moments), len(sources)
 212 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 213 | +        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 214 | +        f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 215 | +        f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 216 | +        f"{len(report['fallbacks'])} read from a fallback record")
 217 | +    moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 218 | +    return moments, sources, report
 219 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 220 | new file mode 100644
 221 | index 00000000..9c599f17
 222 | --- /dev/null
 223 | +++ b/tests/package/proof_ledger.py
 224 | @@ -0,0 +1,135 @@
 225 | +#!/usr/bin/env python3
 226 | +"""ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 227 | +
 228 | +- The rows are pp-ingest's adapter (best_unused_moments), read-only.
 229 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 230 | +- "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 231 | +- Novelty (L-p): every clip span of the pins already delivered (--delivered, required; tonight: the 37c5b5f5 review,
 232 | +  run 165629, and the 41f29b1f medley) is passed to package.usable as delivered, so an overlapping moment is out.
 233 | +- "since": ruling 2's words are "best_unused_moments since the last delivered video". The default is the newest
 234 | +  delivered pin's approved_at: a line mined after the last delivered package was sealed cannot be in it. --hours is
 235 | +  the adapter's publish window. The pins are read BEFORE anything is written; a missing or broken pin, or a pin with
 236 | +  no clip or no zoned approved_at, refuses the run (exit 2) with why (audit 2315 C2: grok, qwen, glm).
 237 | +- The same legs, ledger and meters as proof_ly.py: Heimdall writes, xAI judges, scribe_v1 is the second recogniser.
 238 | +  Writer calls have ruling 5's deadline; the budget is ruling 5's.
 239 | +Writes tests/package/proof/ledger_<UTC stamp>/: inputs.json, package.json, package.log, step_a.json and, on a
 240 | +package, MOMENTS_PIN_LEDGER.json.
 241 | +
 242 | +Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
 243 | +  tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
 244 | +                       tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
 245 | +"""
 246 | +import argparse
 247 | +import json
 248 | +import os
 249 | +import sys
 250 | +import time
 251 | +from datetime import datetime, timezone
 252 | +
 253 | +HERE = os.path.dirname(os.path.abspath(__file__))
 254 | +REPO = os.path.dirname(os.path.dirname(HERE))
 255 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 256 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 257 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 258 | +sys.path.insert(0, HERE)
 259 | +import eligibility as E  # noqa: E402
 260 | +import ledger_build as LB  # noqa: E402
 261 | +import moments as M  # noqa: E402
 262 | +import package as PK  # noqa: E402
 263 | +import package_pin  # noqa: E402
 264 | +import proof_ly as PL  # noqa: E402
 265 | +import proof_saved_runs as PS  # noqa: E402
 266 | +import providers as P  # noqa: E402
 267 | +
 268 | +def delivered_pins(paths):
 269 | +    """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 270 | +    the newest approved_at, [{path, story_id, approved_at, clips}]). Raises ValueError (or OSError / KeyError /
 271 | +    TypeError) on a pin that cannot be read, has no clip, or has no zoned approved_at: never a partial delivered set."""
 272 | +    if not paths:
 273 | +        raise ValueError("no delivered pin named")
 274 | +    spans, newest, pins = [], None, []
 275 | +    for p in paths:
 276 | +        with open(p) as f:
 277 | +            pin = json.load(f)
 278 | +        at = datetime.fromisoformat(str(pin["approved_at"]).replace("Z", "+00:00"))
 279 | +        if at.tzinfo is None:
 280 | +            raise ValueError(f"{p}: approved_at has no time zone")
 281 | +        segs = pin["segments"]
 282 | +        if not isinstance(segs, list) or not segs:
 283 | +            raise ValueError(f"{p}: no clip")
 284 | +        spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
 285 | +                   "pin": pin["story_id"]} for s in segs]
 286 | +        newest = at if newest is None or at > newest else newest
 287 | +        pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
 288 | +                     "approved_at": at.isoformat(), "clips": len(segs)})
 289 | +    return spans, newest, pins
 290 | +
 291 | +
 292 | +def main(argv=None):
 293 | +    ap = argparse.ArgumentParser()
 294 | +    ap.add_argument("--delivered", nargs="+", required=True, metavar="PIN",
 295 | +                    help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
 296 | +                         "newest one's approved_at")
 297 | +    ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 298 | +    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 299 | +    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 300 | +    a = ap.parse_args(argv)
 301 | +    now = datetime.now(timezone.utc)
 302 | +    try:                                                 # read before anything is written (glm C2 N-4)
 303 | +        delivered, last, pins = delivered_pins(a.delivered)
 304 | +        since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 305 | +        if since.tzinfo is None:
 306 | +            raise ValueError("--since has no time zone")
 307 | +        if since > now:
 308 | +            raise ValueError(f"since {since.isoformat()} is after now")
 309 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 310 | +        print(f"REFUSED: the delivered pins or 'since' cannot be read ({type(e).__name__}: {e})", file=sys.stderr)
 311 | +        return 2
 312 | +    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M')}")
 313 | +    os.makedirs(out_dir, exist_ok=True)
 314 | +    logf = open(os.path.join(out_dir, "package.log"), "a")
 315 | +    say = lambda s: (print(s, flush=True), logf.write(s + "\n"), logf.flush())
 316 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 317 | +    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
 318 | +        f"{now.isoformat(timespec='seconds')}, since {since.isoformat(timespec='seconds')} "
 319 | +        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h")
 320 | +    say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 321 | +        f"{len(delivered)} clip spans out")
 322 | +    rows, rep = LB.rows(since, now, horizon_h=a.hours)
 323 | +    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 324 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 325 | +    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 326 | +        json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 327 | +                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 328 | +                  f, indent=1, default=str)
 329 | +    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 330 | +                      chains=PL.chains())
 331 | +    own, used = PL.meter(router), PL.reply_meter(router)
 332 | +    t0 = time.time()
 333 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 334 | +                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 335 | +                   spend=lambda: (own["est"], own["best"]))
 336 | +    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 337 | +               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 338 | +               since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 339 | +    if res["package"]:
 340 | +        try:
 341 | +            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M')}", out_dir,
 342 | +                                              name="MOMENTS_PIN_LEDGER.json")
 343 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 344 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
 345 | +            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 346 | +                f"pin {path}")
 347 | +        except package_pin.PinRefused as e:
 348 | +            res["pin_refused"] = str(e)
 349 | +            say(f"PIN REFUSED: {e}")
 350 | +    else:
 351 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 352 | +    with open(os.path.join(out_dir, "package.json"), "w") as f:
 353 | +        json.dump(res, f, indent=1, default=str)
 354 | +    logf.close()
 355 | +    return 0
 356 | +
 357 | +
 358 | +if __name__ == "__main__":
 359 | +    sys.exit(main())
 360 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 361 | new file mode 100644
 362 | index 00000000..367d3161
 363 | --- /dev/null
 364 | +++ b/tests/package/test_ledger_build.py
 365 | @@ -0,0 +1,255 @@
 366 | +#!/usr/bin/env python3
 367 | +"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
 368 | +- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
 369 | +- reading the store's word record (its sha checked, sentence-ready only);
 370 | +- turning rows into the packager's moments (counted drops, no duplicate spans);
 371 | +- the adapter's failures are raised, never read as an empty ledger."""
 372 | +import io
 373 | +import json
 374 | +import os
 375 | +import sys
 376 | +import tempfile
 377 | +import unittest
 378 | +from unittest import mock
 379 | +
 380 | +HERE = os.path.dirname(os.path.abspath(__file__))
 381 | +REPO = os.path.dirname(os.path.dirname(HERE))
 382 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 383 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 384 | +import eligibility as E  # noqa: E402
 385 | +import ledger_build as LB  # noqa: E402
 386 | +import transcript_store as ts  # noqa: E402
 387 | +from test_eligibility import NOW, REG, source  # noqa: E402
 388 | +
 389 | +SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 390 | +         "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
 391 | +         "In 2009 Bitcoin started as a quiet experiment."]
 392 | +
 393 | +
 394 | +def row(text, start=None, end=None, mid="L1", vid="vidA"):
 395 | +    return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 396 | +            "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 397 | +            "scores": {"contempt_outrage": 0, "hook_first_2s": 3, "quotable": 3, "stakes": 3, "stance": 3,
 398 | +                       "stands_alone": 4, "surprising_fact": 2},
 399 | +            "risk": [], "topics": [], "reason": "r", "names_person": False,
 400 | +            "mined": {"by": "qwen/qwen3.8-27b@heimdall_qwen27b", "at": NOW.isoformat()}}
 401 | +
 402 | +
 403 | +class TestReanchor(unittest.TestCase):
 404 | +    def setUp(self):
 405 | +        self.src = source(SENTS)
 406 | +
 407 | +    def test_whole_sentences_anchor_exactly(self):
 408 | +        sp, info = LB.reanchor(row(SENTS[1] + " " + SENTS[2]), self.src)
 409 | +        self.assertEqual((sp.k0, sp.k1), (1, 2))
 410 | +        self.assertEqual(info["snapped_words"], [0, 0])
 411 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 412 | +
 413 | +    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 414 | +        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
 415 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
 416 | +        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
 417 | +        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
 418 | +        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
 419 | +        self.assertIsNone(sp)
 420 | +        self.assertIn("not whole sentences", why)
 421 | +
 422 | +    def test_a_snap_never_adds_a_negation_or_a_number(self):
 423 | +        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
 424 | +        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
 425 | +        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
 426 | +                           ("Bitcoin started as a quiet experiment.", "2009")):
 427 | +            sp, why = LB.reanchor(row(text), self.src)
 428 | +            self.assertIsNone(sp, text)
 429 | +            self.assertIn(word, why)
 430 | +
 431 | +    def test_a_typographic_apostrophe_does_not_hide_a_negation(self):
 432 | +        """glm C2 N-3: 'Don\u2019t' (U+2019) is the negation 'Don't' to the guard."""
 433 | +        for apostrophe in ("\u2019", "'"):
 434 | +            src = source([f"Don{apostrophe}t sell your Bitcoin to anyone today.", "That is the plan."])
 435 | +            sp, why = LB.reanchor(row("sell your Bitcoin to anyone today."), src)
 436 | +            self.assertIsNone(sp, apostrophe)
 437 | +            self.assertIn("negation", why)
 438 | +
 439 | +    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 440 | +        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 441 | +        self.assertIsNone(sp)
 442 | +        self.assertIn("not whole sentences", why)
 443 | +        sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 444 | +        self.assertIsNone(sp)
 445 | +        self.assertIn("does not anchor", why)
 446 | +
 447 | +
 448 | +class TestWordSourceAndInputs(unittest.TestCase):
 449 | +    def store_with(self, d, vid, sentences, break_sha=False, method="whisper_words_punct", no_sha=False):
 450 | +        src = source(sentences, vid=vid, method=method)
 451 | +        segs = [{"start": src.tokens[a]["start"], "end": src.tokens[b]["end"],
 452 | +                 "text": E.spoken(src.tokens[a:b + 1]),
 453 | +                 "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens[a:b + 1]]}
 454 | +                for a, b in src.sentences]
 455 | +        rec = {"segments": segs, "transcript_method": method, "video_id": vid,                     # the store's word
 456 | +               "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens]}  # record shape
 457 | +        if not no_sha:
 458 | +            rec["transcript_sha256"] = "x" * 64 if break_sha else ts.segments_sha256(segs)
 459 | +        os.makedirs(os.path.join(d, "transcripts", vid), exist_ok=True)
 460 | +        with open(os.path.join(d, "transcripts", vid, f"transcript.{method}.json"), "w") as f:
 461 | +            json.dump(rec, f)
 462 | +        return src
 463 | +
 464 | +    def test_a_record_whose_sha_does_not_match_its_segments_is_never_read(self):
 465 | +        ctx = E.Context(NOW, REG)
 466 | +        with tempfile.TemporaryDirectory() as d:
 467 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None, ["no word record in the store"]))
 468 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 469 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d),
 470 | +                             (None, None, ["transcript.whisper_words_punct.json: its segments do not match its "
 471 | +                                           "transcript_sha256"]))
 472 | +            self.store_with(d, "vidA", SENTS, no_sha=True)                      # glm C2: no sha at all is no match
 473 | +            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
 474 | +            self.store_with(d, "vidA", SENTS)
 475 | +            src, path, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
 476 | +            self.assertIsNotNone(src)
 477 | +            self.assertEqual((src.timing, passed_over), ("word", []))
 478 | +            p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 479 | +            with open(p) as f:                             # glm C1 P2-10: a segment edited AFTER its sha was taken
 480 | +                rec = json.load(f)
 481 | +            rec["segments"][1]["text"] = "Somebody can stop Bitcoin from settling a payment."
 482 | +            with open(p, "w") as f:
 483 | +                json.dump(rec, f)
 484 | +            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
 485 | +
 486 | +    def test_the_punctuated_record_is_read_first(self):
 487 | +        """qwen C1 P0-1 / glm C1 P0-2: "punct" sorts first (key False < True); the verbatim record only as a fallback."""
 488 | +        ctx = E.Context(NOW, REG)
 489 | +        with tempfile.TemporaryDirectory() as d:
 490 | +            self.store_with(d, "vidA", SENTS)                                   # transcript.whisper_words_punct.json
 491 | +            punct = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
 492 | +            plain = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words.json")
 493 | +            import shutil
 494 | +            shutil.copy(punct, plain)                                           # both valid, both sentence-ready
 495 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words_punct.json"))
 496 | +            os.remove(punct)
 497 | +            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words.json"))
 498 | +
 499 | +    def test_every_record_passed_over_is_named_and_a_fallback_shows(self):
 500 | +        """Audit 2315 C2 (grok, qwen, glm): the reason was the LAST failure only, and a punctuated record rejected
 501 | +        before a verbatim one was used left no trace."""
 502 | +        ctx = E.Context(NOW, REG)
 503 | +        unpunctuated = [" ".join(["bitcoin moves when the market moves"] * 12)]   # 72 words, no stop: not ready
 504 | +        self.assertFalse(E.sentence_ready(source(unpunctuated, vid="vidA", method="whisper_words")))
 505 | +        with tempfile.TemporaryDirectory() as d:
 506 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 507 | +            self.store_with(d, "vidA", unpunctuated, method="whisper_words")
 508 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d)[2],
 509 | +                             ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256",
 510 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e)"])
 511 | +            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 512 | +            self.assertEqual(ms, [])
 513 | +            self.assertEqual(rep["no_word_record_why"],
 514 | +                             {"transcript.whisper_words_punct.json: its segments do not match its transcript_sha256; "
 515 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e)": 1})
 516 | +            self.store_with(d, "vidA", SENTS, method="whisper_words")           # a verbatim record that IS ready
 517 | +            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 518 | +            self.assertEqual(len(ms), 1)
 519 | +            self.assertEqual(rep["fallbacks"], {"vidA": {
 520 | +                "used": "transcript.whisper_words.json",
 521 | +                "passed_over": ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256"]}})
 522 | +
 523 | +    def test_a_video_whose_rows_name_two_channels_is_dropped_whole(self):
 524 | +        """Audit 2315 C2 (qwen P1, glm P1): one uploader per video is checked, never taken from the first row."""
 525 | +        ctx = E.Context(NOW, REG)
 526 | +        with tempfile.TemporaryDirectory() as d:
 527 | +            self.store_with(d, "vidA", SENTS)
 528 | +            other = dict(row(SENTS[2], mid="L2"), channel_id="UCother")
 529 | +            ms, _, rep = LB.build_inputs([row(SENTS[0], mid="L1"), other], ctx, d, log=lambda s: None)
 530 | +            self.assertEqual(ms, [])
 531 | +            self.assertEqual(rep["channel_conflict"], {"vidA": {"rows": 2, "channel_ids": ["UCdd", "UCother"]}})
 532 | +
 533 | +    def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 534 | +        ctx = E.Context(NOW, REG)
 535 | +        with tempfile.TemporaryDirectory() as d:
 536 | +            self.store_with(d, "vidA", SENTS)
 537 | +            rows = [row(SENTS[0], mid="L1"), row(SENTS[0], mid="L2"),               # the same span twice
 538 | +                    row("Ethereum is a world computer for everyone.", mid="L3"),  # does not anchor
 539 | +                    row(SENTS[0], mid="L4", vid="vidZ"),                            # no word record for vidZ
 540 | +                    {k: v for k, v in row(SENTS[3], mid="L5").items() if k != "scores"}]   # malformed: counted
 541 | +            ms, srcs, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
 542 | +            self.assertEqual((rep["moments"], rep["duplicates"], rep["no_word_record"]), (1, 1, 1))
 543 | +            self.assertEqual(list(rep["not_anchored"]), ["L3"])
 544 | +            self.assertEqual(list(rep["malformed"]), ["L5"])                   # glm C1 P1-8: never a crash
 545 | +            m = ms[0]
 546 | +            self.assertEqual(m["mined"]["ledger_moment_id"], "L1")
 547 | +            self.assertEqual(m["scores"], rows[0]["scores"])                  # the ledger's judgment kept (glm P2-6)
 548 | +            self.assertEqual(m["text"], SENTS[0])
 549 | +            self.assertEqual(m["timing"], "word")
 550 | +            self.assertIn("rank_score", m)
 551 | +            self.assertEqual(set(srcs), {"vidA"})
 552 | +
 553 | +
 554 | +class TestAdapter(unittest.TestCase):
 555 | +    def test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger(self):
 556 | +        from datetime import timedelta
 557 | +        fail = mock.Mock(returncode=1, stderr="Traceback ... boom", stdout="")
 558 | +        with mock.patch("subprocess.run", return_value=fail):
 559 | +            with self.assertRaises(RuntimeError):
 560 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 561 | +        refused = mock.Mock(returncode=0, stderr="", stdout=json.dumps(
 562 | +            {"rows": [], "report": {"contract": "unavailable: StoreGuard"}}))
 563 | +        with mock.patch("subprocess.run", return_value=refused):
 564 | +            with self.assertRaises(RuntimeError) as cm:
 565 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 566 | +            self.assertIn("refused", str(cm.exception))
 567 | +        ok = mock.Mock(returncode=0, stderr="", stdout=json.dumps({"rows": [{"moment_id": "x"}], "report": {}}))
 568 | +        with mock.patch("subprocess.run", return_value=ok):
 569 | +            self.assertEqual(LB.rows(NOW - timedelta(hours=72), NOW)[0], [{"moment_id": "x"}])
 570 | +        import subprocess                                                    # glm C2 N-5: every failure is RuntimeError
 571 | +        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("python3", 300)):
 572 | +            with self.assertRaises(RuntimeError) as cm:
 573 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 574 | +            self.assertIn("did not answer", str(cm.exception))
 575 | +        for stdout in ("", "not json", "[]", json.dumps({"rows": {}, "report": {}}), json.dumps({"report": {}})):
 576 | +            with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stderr="", stdout=stdout)):
 577 | +                with self.assertRaises(RuntimeError, msg=stdout) as cm:
 578 | +                    LB.rows(NOW - timedelta(hours=72), NOW)
 579 | +                self.assertIn("cannot be read", str(cm.exception))
 580 | +        empty = mock.Mock(returncode=0, stderr="", stdout=json.dumps(       # grok C1 P0 (reframed): a real empty read
 581 | +            {"rows": [], "report": {"excluded": {"delivered in the previous 24 h": 3}}}))
 582 | +        with mock.patch("subprocess.run", return_value=empty):
 583 | +            rows, rep = LB.rows(NOW - timedelta(hours=72), NOW)
 584 | +            self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))
 585 | +
 586 | +
 587 | +class TestDriverRefuses(unittest.TestCase):
 588 | +    def test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one(self):
 589 | +        """Audit 2315 C2 (grok, qwen, glm): no hard-coded delivered pins; a pin that cannot be read, has no clip or no
 590 | +        zoned approved_at refuses the run (exit 2) before any proof dir exists; 'since' defaults to the newest
 591 | +        delivered pin's approved_at (ruling 2: "best_unused_moments since the last delivered video")."""
 592 | +        sys.path.insert(0, HERE)
 593 | +        import proof_ledger as PLG
 594 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 595 | +                                                                                 "MOMENTS_PIN_LY.json")]
 596 | +        spans, newest, info = PLG.delivered_pins(pins)
 597 | +        self.assertEqual(newest.isoformat(), "2026-11-13T03:01:09+00:00")              # the 41f29b1f medley
 598 | +        self.assertEqual(len(spans), sum(i["clips"] for i in info))
 599 | +        proof = os.path.join(HERE, "proof")
 600 | +        before = sorted(os.listdir(proof))
 601 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()):
 602 | +            with open(pins[1]) as f:
 603 | +                pin = json.load(f)
 604 | +            for name, bad in (("naive.json", dict(pin, approved_at="2026-11-13T03:01:09")),
 605 | +                              ("empty.json", dict(pin, segments=[]))):
 606 | +                with open(os.path.join(d, name), "w") as f:
 607 | +                    json.dump(bad, f)
 608 | +            for argv in (["--delivered", os.path.join(d, "missing.json")],
 609 | +                         ["--delivered", os.path.join(d, "naive.json")],
 610 | +                         ["--delivered", os.path.join(d, "empty.json")],
 611 | +                         ["--delivered", *pins, "--since", "2099-01-01T00:00:00+00:00"],
 612 | +                         ["--delivered", *pins, "--since", "2026-11-13T03:01:09"]):
 613 | +                self.assertEqual(PLG.main(argv), 2, argv)
 614 | +            with self.assertRaises(SystemExit):
 615 | +                PLG.main([])                                                            # --delivered is required
 616 | +        self.assertEqual(sorted(os.listdir(proof)), before)
 617 | +
 618 | +
 619 | +if __name__ == "__main__":
 620 | +    unittest.main()
 621 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the
MEDLEY). ROUND 2: this is the FINAL diff after two audit cycles. Check that every fix below is right and complete, and
look for anything new. Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

The task (orchestrator ruling 2, 22:40 ET Nov 12): "when [ingest ledger] rows turn sentence-ready, build from the
ledger (best_unused_moments since the last delivered video) and seal a pin; that is the first FRESH medley".
Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of the sentence-locked word transcript (L-o 1);
- a moment is on screen only on a word-timed, sentence-ready record (L-e);
- time-sensitive words only from a source <= 24 h old, judged on the RENDER clock (L-v 3, ruling 1);
- no clip span already delivered is used again (L-p).

The contract agreed with the integrator, who owns the word-pass worker:
- word records: the store's full-video slot (transcripts/<vid>/transcript.whisper_words*.json, write-once, full-video
  clock), or LATER window records the worker lists in moments/word_pass.jsonl (not wired yet; counted, unused).
- the ingest adapter, best_unused_moments(path, since, now, delivered_ids, ...), returns "lines mined at or after
  `since` or published inside the 72 h window", minus its own exclusions. Ledger rows carry the CAPTION clock.

The files:
1. pipeline/ledger_build.py:
   - rows(): the adapter in its own interpreter, read-only.
   - word_source(): the punctuated record first, sha-checked, sentence-ready only.
   - reanchor(): sentence_law.anchor plus a snap of at most 3 words per edge, guarded against an added negation or
     number.
   - build_inputs(): the miner's own judge/record; every drop is counted.
2. tests/package/proof_ledger.py: the driver (render clock, delivered spans out, the medley build, the pin).
3. tests/package/test_ledger_build.py.

Fixed after cycle 1 (C1_CONSENSUS):
- the snap may not add a negation or a digit (SNAP_GUARD);
- the delivered pins became an argument;
- malformed rows are counted;
- the drop reason is recorded;
- the horizon is a float;
- tests: punctuated-first, a segment edited after its sha.

Fixed after cycle 2 (C2_DISPOSITIONS):
- K4: word_source returns (Source, path, passed_over). Every record read and not used is named with why, in reading
  order; a fallback from the punctuated record is listed in report.fallbacks.
- K5: a video whose rows name more than one channel_id is dropped whole and counted (report.channel_conflict).
- K6: --delivered is REQUIRED (no hard-coded default). The pins are read before anything is written; a pin that
  cannot be read, has no clip or no zoned approved_at refuses the run (exit 2).
- rows(): a timeout or an unreadable answer raises RuntimeError.
- SNAP_GUARD reads a typographic apostrophe (U+2019 and others) as '.
- tested: a record with no sha; SEARCH_PAD_S's reason is documented.
- NOT a reviewer finding (check it against ruling 2's words): `since` now defaults to the newest delivered pin's
  approved_at, overridable with --since. Before, it was now - 72 h; --hours is now the publish window only.

Check, concretely:
(a) Can a non-whole-sentence clip, a non-word-timed moment, a moment from an unverified record, or a delivered span
    get through?
(b) Is any drop silent?
(c) Does the `since` default match "best_unused_moments since the last delivered video", and can it read too few or
    too many lines?
(d) Is each cycle-2 fix complete?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".

