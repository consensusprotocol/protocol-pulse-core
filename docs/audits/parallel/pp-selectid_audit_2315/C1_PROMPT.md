# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2315
# Branch: pp-selectid
# Generated: 2026-11-12 23:06 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2315/C1_STEP.diff (394 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | new file mode 100644
   3 | index 00000000..dc7356c6
   4 | --- /dev/null
   5 | +++ b/pipeline/ledger_build.py
   6 | @@ -0,0 +1,154 @@
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
  39 | +SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]
  40 | +INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  41 | +MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
  42 | +STORE = os.path.join(MAIN, "data", "editorial")
  43 | +
  44 | +
  45 | +_ROWS = """
  46 | +import json, sys
  47 | +from datetime import datetime
  48 | +sys.path.insert(0, sys.argv[1])
  49 | +from pipeline.ingest import ledger as IL
  50 | +a = json.loads(sys.stdin.read())
  51 | +rows, rep = IL.best_unused_moments(a["path"], datetime.fromisoformat(a["since"]), datetime.fromisoformat(a["now"]),
  52 | +                                   a["delivered"], store_root=a["store_root"], horizon_h=a["horizon_h"])
  53 | +sys.stdout.write(json.dumps({"rows": rows, "report": rep}, default=str))
  54 | +"""
  55 | +
  56 | +
  57 | +def rows(since, now, delivered_ids=(), ingest_root=INGEST_ROOT, horizon_h=72, timeout=300):
  58 | +    """pp-ingest's adapter, best_unused_moments, run read-only in its OWN interpreter, from its worktree until the
  59 | +    integrator merges it. Its store guard refuses a process in which another transcript_store was imported first, so
  60 | +    the two never share modules. -> (rows, report). Raises RuntimeError when the adapter refuses or fails (fail
  61 | +    closed: no rows is never read as a quiet ledger)."""
  62 | +    import subprocess
  63 | +    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
  64 | +            "since": since.isoformat(), "now": now.isoformat(), "delivered": list(delivered_ids),
  65 | +            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": horizon_h}
  66 | +    env = dict(os.environ, PP_SELECTID_PIPELINE=os.path.dirname(os.path.abspath(__file__)))
  67 | +    p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
  68 | +                       text=True, cwd=ingest_root, env=env, timeout=timeout)
  69 | +    if p.returncode != 0:
  70 | +        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
  71 | +    out = json.loads(p.stdout)
  72 | +    if (out["report"] or {}).get("contract"):
  73 | +        raise RuntimeError(f"the ledger adapter refused: {out['report']['contract']}")
  74 | +    return out["rows"], out["report"]
  75 | +
  76 | +
  77 | +def word_source(row, ctx, store=STORE):
  78 | +    """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
  79 | +    checked), as an eligibility Source with the row's identity, or None."""
  80 | +    vid = row["video_id"]
  81 | +    paths = sorted(glob.glob(os.path.join(store, "transcripts", vid, "transcript.whisper_words*.json")),
  82 | +                   key=lambda p: "punct" not in p)
  83 | +    reg = ctx.channel(row.get("channel_id")) or {}
  84 | +    for p in paths:
  85 | +        try:
  86 | +            rec = json.load(open(p))
  87 | +        except (OSError, ValueError):
  88 | +            continue
  89 | +        if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
  90 | +            continue
  91 | +        timing, toks = S.tokens_from_record(rec)
  92 | +        src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
  93 | +                       row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
  94 | +                       timing=timing, title=row.get("title") or "", file_head=True, vod=True)
  95 | +        if E.sentence_ready(src):
  96 | +            return src, p
  97 | +    return None, None
  98 | +
  99 | +
 100 | +def reanchor(row, src):
 101 | +    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
 102 | +    t0 = row.get("start")
 103 | +    t1 = row.get("end")
 104 | +    hit = SL.anchor(src.tokens, row.get("text") or "",
 105 | +                    t0=(float(t0) - SEARCH_PAD_S) if t0 is not None else None,
 106 | +                    t1=(float(t1) + SEARCH_PAD_S) if t1 is not None else None)
 107 | +    if hit is None:
 108 | +        return None, "the row's text does not anchor in the word record (sentence_law.anchor)"
 109 | +    i0, i1, ratio = hit
 110 | +    k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
 111 | +    k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
 112 | +    if k0 is None or k1 is None:
 113 | +        return None, "the anchored words fall outside the record's sentences"
 114 | +    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
 115 | +    if left > SNAP_WORDS or right > SNAP_WORDS:
 116 | +        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
 117 | +                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
 118 | +    sp = E.Span(src, k0, k1)
 119 | +    return sp, {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
 120 | +
 121 | +
 122 | +def build_inputs(rows, ctx, store=STORE, log=print):
 123 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 124 | +    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 125 | +    each counted with why."""
 126 | +    report = {"rows": len(rows), "no_word_record": 0, "not_anchored": {}, "duplicates": 0, "moments": 0,
 127 | +              "videos": 0, "word_records": {}}
 128 | +    by_vid = {}
 129 | +    for r in rows:
 130 | +        by_vid.setdefault(r["video_id"], []).append(r)
 131 | +    moments, sources, seen = [], {}, set()
 132 | +    for vid, rs in by_vid.items():
 133 | +        src, path = word_source(rs[0], ctx, store)
 134 | +        if src is None:
 135 | +            report["no_word_record"] += len(rs)
 136 | +            continue
 137 | +        report["word_records"][vid] = os.path.relpath(path, store)
 138 | +        for r in rs:
 139 | +            sp, info = reanchor(r, src)
 140 | +            if sp is None:
 141 | +                report["not_anchored"][r["moment_id"]] = info
 142 | +                continue
 143 | +            if (vid, sp.k0, sp.k1) in seen:
 144 | +                report["duplicates"] += 1
 145 | +                continue
 146 | +            seen.add((vid, sp.k0, sp.k1))
 147 | +            m = {"scores": r["scores"], "names_person": r.get("names_person", False), "risk": list(r.get("risk") or []),
 148 | +                 "topics": list(r.get("topics") or []), "reason": r.get("reason") or ""}
 149 | +            mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 150 | +                         ledger_text=r.get("text"))
 151 | +            rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 152 | +            rec["rank_score"] = M.rank_score(rec)
 153 | +            moments.append(rec)
 154 | +            sources[vid] = src
 155 | +    report["moments"], report["videos"] = len(moments), len(sources)
 156 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 157 | +        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 158 | +        f"{report['duplicates']} duplicates")
 159 | +    moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 160 | +    return moments, sources, report
 161 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 162 | new file mode 100644
 163 | index 00000000..10e7eaaf
 164 | --- /dev/null
 165 | +++ b/tests/package/proof_ledger.py
 166 | @@ -0,0 +1,100 @@
 167 | +#!/usr/bin/env python3
 168 | +"""ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 169 | +
 170 | +- The rows are pp-ingest's adapter (best_unused_moments), read-only.
 171 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 172 | +- "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 173 | +- Novelty (L-p): every clip span of the pins already delivered (the 37c5b5f5 review, run 165629; the 41f29b1f medley)
 174 | +  is passed to package.usable as delivered, so an overlapping moment is out.
 175 | +- The same legs, ledger and meters as proof_ly.py: Heimdall writes, xAI judges, scribe_v1 is the second recogniser.
 176 | +  Writer calls have ruling 5's deadline; the budget is ruling 5's.
 177 | +Writes tests/package/proof/ledger_<UTC stamp>/: inputs.json, package.json, package.log, step_a.json and, on a
 178 | +package, MOMENTS_PIN_LEDGER.json.
 179 | +
 180 | +Usage: python3 tests/package/proof_ledger.py [--hours 72]
 181 | +"""
 182 | +import argparse
 183 | +import json
 184 | +import os
 185 | +import sys
 186 | +import time
 187 | +from datetime import datetime, timedelta, timezone
 188 | +
 189 | +HERE = os.path.dirname(os.path.abspath(__file__))
 190 | +REPO = os.path.dirname(os.path.dirname(HERE))
 191 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 192 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 193 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 194 | +sys.path.insert(0, HERE)
 195 | +import eligibility as E  # noqa: E402
 196 | +import ledger_build as LB  # noqa: E402
 197 | +import moments as M  # noqa: E402
 198 | +import package as PK  # noqa: E402
 199 | +import package_pin  # noqa: E402
 200 | +import proof_ly as PL  # noqa: E402
 201 | +import proof_saved_runs as PS  # noqa: E402
 202 | +import providers as P  # noqa: E402
 203 | +
 204 | +DELIVERED_PINS = (os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN.json"),       # 37c5b5f5 (165629)
 205 | +                  os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN_LY.json"))    # 41f29b1f
 206 | +
 207 | +
 208 | +def delivered_spans(paths=DELIVERED_PINS):
 209 | +    """Every clip span of the pins already delivered: {video_id, start, end} (package.usable reads overlaps)."""
 210 | +    out = []
 211 | +    for p in paths:
 212 | +        pin = json.load(open(p))
 213 | +        out += [{"video_id": s["video_id"], "start": s["start"], "end": s["end"], "pin": pin["story_id"]}
 214 | +                for s in pin["segments"]]
 215 | +    return out
 216 | +
 217 | +
 218 | +def main(argv=None):
 219 | +    ap = argparse.ArgumentParser()
 220 | +    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's horizon (and 'since' = now - hours)")
 221 | +    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 222 | +    a = ap.parse_args(argv)
 223 | +    now = datetime.now(timezone.utc)
 224 | +    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M')}")
 225 | +    os.makedirs(out_dir, exist_ok=True)
 226 | +    logf = open(os.path.join(out_dir, "package.log"), "a")
 227 | +    say = lambda s: (print(s, flush=True), logf.write(s + "\n"), logf.flush())
 228 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 229 | +    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
 230 | +        f"{now.isoformat(timespec='seconds')}")
 231 | +    rows, rep = LB.rows(now - timedelta(hours=a.hours), now, horizon_h=int(a.hours))
 232 | +    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 233 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 234 | +    delivered = delivered_spans()
 235 | +    json.dump({"adapter_report": rep, "inputs": inputs, "delivered": delivered,
 236 | +               "moments": moments}, open(os.path.join(out_dir, "inputs.json"), "w"), indent=1, default=str)
 237 | +    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 238 | +                      chains=PL.chains())
 239 | +    own, used = PL.meter(router), PL.reply_meter(router)
 240 | +    t0 = time.time()
 241 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 242 | +                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 243 | +                   spend=lambda: (own["est"], own["best"]))
 244 | +    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 245 | +               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 246 | +               chains=router.chains, inputs=inputs)
 247 | +    if res["package"]:
 248 | +        try:
 249 | +            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M')}", out_dir,
 250 | +                                              name="MOMENTS_PIN_LEDGER.json")
 251 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 252 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
 253 | +            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 254 | +                f"pin {path}")
 255 | +        except package_pin.PinRefused as e:
 256 | +            res["pin_refused"] = str(e)
 257 | +            say(f"PIN REFUSED: {e}")
 258 | +    else:
 259 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 260 | +    json.dump(res, open(os.path.join(out_dir, "package.json"), "w"), indent=1, default=str)
 261 | +    logf.close()
 262 | +    return 0
 263 | +
 264 | +
 265 | +if __name__ == "__main__":
 266 | +    sys.exit(main())
 267 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 268 | new file mode 100644
 269 | index 00000000..71be2338
 270 | --- /dev/null
 271 | +++ b/tests/package/test_ledger_build.py
 272 | @@ -0,0 +1,121 @@
 273 | +#!/usr/bin/env python3
 274 | +"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
 275 | +- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
 276 | +- reading the store's word record (its sha checked, sentence-ready only);
 277 | +- turning rows into the packager's moments (counted drops, no duplicate spans);
 278 | +- the adapter's failures are raised, never read as an empty ledger."""
 279 | +import json
 280 | +import os
 281 | +import sys
 282 | +import tempfile
 283 | +import unittest
 284 | +from unittest import mock
 285 | +
 286 | +HERE = os.path.dirname(os.path.abspath(__file__))
 287 | +REPO = os.path.dirname(os.path.dirname(HERE))
 288 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 289 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 290 | +import eligibility as E  # noqa: E402
 291 | +import ledger_build as LB  # noqa: E402
 292 | +import transcript_store as ts  # noqa: E402
 293 | +from test_eligibility import NOW, REG, source  # noqa: E402
 294 | +
 295 | +SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 296 | +         "That is the whole design and it works every day.", "Bitcoin does not ask for permission."]
 297 | +
 298 | +
 299 | +def row(text, start=None, end=None, mid="L1", vid="vidA"):
 300 | +    return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 301 | +            "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 302 | +            "scores": {"contempt_outrage": 0, "hook_first_2s": 3, "quotable": 3, "stakes": 3, "stance": 3,
 303 | +                       "stands_alone": 4, "surprising_fact": 2},
 304 | +            "risk": [], "topics": [], "reason": "r", "names_person": False,
 305 | +            "mined": {"by": "qwen/qwen3.8-27b@heimdall_qwen27b", "at": NOW.isoformat()}}
 306 | +
 307 | +
 308 | +class TestReanchor(unittest.TestCase):
 309 | +    def setUp(self):
 310 | +        self.src = source(SENTS)
 311 | +
 312 | +    def test_whole_sentences_anchor_exactly(self):
 313 | +        sp, info = LB.reanchor(row(SENTS[1] + " " + SENTS[2]), self.src)
 314 | +        self.assertEqual((sp.k0, sp.k1), (1, 2))
 315 | +        self.assertEqual(info["snapped_words"], [0, 0])
 316 | +        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words
 317 | +
 318 | +    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
 319 | +        sp, info = LB.reanchor(row("can stop Bitcoin from settling a payment."), self.src)   # 1 word short: snaps
 320 | +        self.assertEqual((sp.k0, sp.k1), (1, 1))
 321 | +        self.assertEqual(info["snapped_words"], [1, 0])
 322 | +
 323 | +    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
 324 | +        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
 325 | +        self.assertIsNone(sp)
 326 | +        self.assertIn("not whole sentences", why)
 327 | +        sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
 328 | +        self.assertIsNone(sp)
 329 | +        self.assertIn("does not anchor", why)
 330 | +
 331 | +
 332 | +class TestWordSourceAndInputs(unittest.TestCase):
 333 | +    def store_with(self, d, vid, sentences, break_sha=False):
 334 | +        src = source(sentences, vid=vid)
 335 | +        segs = [{"start": src.tokens[a]["start"], "end": src.tokens[b]["end"],
 336 | +                 "text": E.spoken(src.tokens[a:b + 1]),
 337 | +                 "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens[a:b + 1]]}
 338 | +                for a, b in src.sentences]
 339 | +        rec = {"segments": segs, "transcript_method": "whisper_words_punct", "video_id": vid,     # the store's word
 340 | +               "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens]}  # record shape
 341 | +        rec["transcript_sha256"] = "x" * 64 if break_sha else ts.segments_sha256(segs)
 342 | +        os.makedirs(os.path.join(d, "transcripts", vid), exist_ok=True)
 343 | +        json.dump(rec, open(os.path.join(d, "transcripts", vid, "transcript.whisper_words_punct.json"), "w"))
 344 | +        return src
 345 | +
 346 | +    def test_a_record_whose_sha_does_not_match_its_segments_is_never_read(self):
 347 | +        ctx = E.Context(NOW, REG)
 348 | +        with tempfile.TemporaryDirectory() as d:
 349 | +            self.store_with(d, "vidA", SENTS, break_sha=True)
 350 | +            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None))
 351 | +            self.store_with(d, "vidA", SENTS)
 352 | +            src, path = LB.word_source(row(SENTS[0]), ctx, d)
 353 | +            self.assertIsNotNone(src)
 354 | +            self.assertEqual(src.timing, "word")
 355 | +
 356 | +    def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 357 | +        ctx = E.Context(NOW, REG)
 358 | +        with tempfile.TemporaryDirectory() as d:
 359 | +            self.store_with(d, "vidA", SENTS)
 360 | +            rows = [row(SENTS[0], mid="L1"), row(SENTS[0], mid="L2"),               # the same span twice
 361 | +                    row("Ethereum is a world computer for everyone.", mid="L3"),  # does not anchor
 362 | +                    row(SENTS[0], mid="L4", vid="vidZ")]                            # no word record for vidZ
 363 | +            ms, srcs, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
 364 | +            self.assertEqual((rep["moments"], rep["duplicates"], rep["no_word_record"]), (1, 1, 1))
 365 | +            self.assertEqual(list(rep["not_anchored"]), ["L3"])
 366 | +            m = ms[0]
 367 | +            self.assertEqual(m["mined"]["ledger_moment_id"], "L1")
 368 | +            self.assertEqual(m["text"], SENTS[0])
 369 | +            self.assertEqual(m["timing"], "word")
 370 | +            self.assertIn("rank_score", m)
 371 | +            self.assertEqual(set(srcs), {"vidA"})
 372 | +
 373 | +
 374 | +class TestAdapter(unittest.TestCase):
 375 | +    def test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger(self):
 376 | +        from datetime import timedelta
 377 | +        fail = mock.Mock(returncode=1, stderr="Traceback ... boom", stdout="")
 378 | +        with mock.patch("subprocess.run", return_value=fail):
 379 | +            with self.assertRaises(RuntimeError):
 380 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 381 | +        refused = mock.Mock(returncode=0, stderr="", stdout=json.dumps(
 382 | +            {"rows": [], "report": {"contract": "unavailable: StoreGuard"}}))
 383 | +        with mock.patch("subprocess.run", return_value=refused):
 384 | +            with self.assertRaises(RuntimeError) as cm:
 385 | +                LB.rows(NOW - timedelta(hours=72), NOW)
 386 | +            self.assertIn("refused", str(cm.exception))
 387 | +        ok = mock.Mock(returncode=0, stderr="", stdout=json.dumps({"rows": [{"moment_id": "x"}], "report": {}}))
 388 | +        with mock.patch("subprocess.run", return_value=ok):
 389 | +            self.assertEqual(LB.rows(NOW - timedelta(hours=72), NOW)[0], [{"moment_id": "x"}])
 390 | +
 391 | +
 392 | +if __name__ == "__main__":
 393 | +    unittest.main()
 394 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the
MEDLEY). It implements the builder's part of the orchestrator's ruling 2 (22:40 ET Nov 12): "when [ingest ledger]
rows turn sentence-ready, build from the ledger (best_unused_moments since the last delivered video) and seal a pin;
that is the first FRESH medley". Standing laws: nothing measured is never a pass (L-m); fail closed (L-j); never change
what a check accepts in order to make something pass; clips are verbatim WHOLE sentences of the sentence-locked word
transcript (L-o 1); a moment is on screen only on a word-timed, sentence-ready record (L-e); time-sensitive words only
from a source <= 24 h old, now judged on the RENDER clock (L-v 3, ruling 1).

The contract agreed with the integrator, who owns the word-pass worker:
- word records: the store's full-video slot (transcripts/<vid>/transcript.whisper_words*.json, write-once, one per
  video, full-video clock), or LATER window records under transcripts/<vid>/windows/ that the worker lists in
  moments/word_pass.jsonl. The ledger rows are never rewritten and carry the CAPTION clock.
- each moment is re-anchored by its TEXT in the word record (sentence_law.anchor); L-s context comes from the caption
  record for a window record (not wired yet: only full-video records are used today).

What changed, and what to check:
1. pipeline/ledger_build.py (new):
   - rows(): pp-ingest's adapter run read-only in its OWN interpreter (subprocess), because its store guard refuses a
     process in which another transcript_store was imported first. A failure or a refusal raises RuntimeError; it is
     never read as an empty ledger.
   - word_source(): the punctuated record first; its segments sha must match its transcript_sha256; only a
     sentence-ready record (E.sentence_ready) is used.
   - reanchor(): sentence_law.anchor with the row's caption times +- 30 s as a search window. The span snaps to the
     record's whole sentences only if at most SNAP_WORDS (3) words of an edge sentence lie outside the anchored text;
     otherwise the row is dropped with why. The moment's text is the WORD RECORD's own words.
   - build_inputs(): M.judge / M.record (the miner's own eligibility and record), the ledger's scores / risks / topics
     / reason kept, mined.ledger_moment_id kept, duplicate spans dropped, every drop counted.
   Can a non-whole-sentence clip, a non-word-timed moment, a stale time-sensitive moment, or a moment from an
   unverified record get through? Can a snap change the meaning (3 words)? Is anything silently dropped?
2. tests/package/proof_ledger.py (new): the driver. It sets ctx.now to the RENDER clock, passes every clip span of
   the two pins already delivered as `delivered` (package.usable drops overlaps), uses the medley build (package.build)
   with the same legs and meters as proof_ly.py, and writes the pin.
3. tests/package/test_ledger_build.py (new): the re-anchor and snap rules, the sha check, the counted drops, and the
   adapter's raises.

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".

