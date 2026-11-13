# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0208
# Branch: pp-selectid
# Generated: 2026-11-13 02:09 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0208/C1_STEP.diff (356 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 55202f0b..dd2f7c0c 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -295,7 +295,7 @@ def contexts_from_sources(package, sources, now=None):
   6 |      """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
   7 |      out = {}
   8 |      for seg in package["segments"]:
   9 | -        src = sources[seg["video_id"]]
  10 | +        src = sources[seg.get("source_key") or seg["video_id"]]     # a window segment's own Source (one per moment)
  11 |          w = seg.get("words") or (None, None)
  12 |          text, win = _window_text(src, seg["k0"], seg["k1"], w[0], w[1])
  13 |          if text is None:
  14 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
  15 | index b45f33b5..d3a7ce26 100644
  16 | --- a/pipeline/ledger_build.py
  17 | +++ b/pipeline/ledger_build.py
  18 | @@ -385,21 +385,44 @@ def reanchor(row, src):
  19 |  
  20 |  
  21 |  def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None):
  22 | -    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
  23 | -    {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
  24 | -    nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
  25 | -    span are dropped, each counted with why."""
  26 | +    """Ledger rows -> (moments in the packager's form, {key: Source}, report). word_pass: word_pass_index()'s
  27 | +    {moment_id: row} (None = no window records).
  28 | +    - A video with a sentence-ready full-video word record: every row re-anchors in it (key: the video id).
  29 | +    - Otherwise ONE WINDOW PER MOMENT, the word-pass worker writing one around each moment. A row with its own
  30 | +      sentence-ready window record re-anchors in THAT window, and its moment carries source_key =
  31 | +      "<video>@<w0>-<w1>", its Source's key (the packager looks every moment up by source_key, else by video_id). The
  32 | +      first FRESH build kept one window per video and lost 63 of 74 rows. Two window moments of one video whose spans
  33 | +      overlap in time are one moment: the better-ranked row (rows arrive best first) keeps it.
  34 | +    Rows with no word record, rows that do not re-anchor on whole sentences, and duplicates are dropped, each counted
  35 | +    with why."""
  36 |      word_pass = word_pass or {}
  37 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
  38 | -              "window_records": {}, "window_passed_over": {}, "no_caption_context": {},
  39 | +              "window_records": {}, "window_waiting": 0, "window_passed_over": {}, "no_caption_context": {},
  40 |                "fallbacks": {},
  41 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
  42 | -              "moments": 0, "videos": 0,
  43 | +              "moments": 0, "videos": 0, "sources": 0,
  44 |                "word_records": {}}
  45 |      def malformed(i, r, why):                     # counted under a key no other row can take (qwen C3, glm C3 P1-4)
  46 |          mid = r.get("moment_id") if isinstance(r, dict) else None
  47 |          report["malformed"][mid if isinstance(mid, str) and mid and mid not in report["malformed"] else f"row {i}"] = why
  48 |  
  49 | +    def make(i, r, sp, info, src):
  50 | +        try:
  51 | +            m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
  52 | +                 "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
  53 | +                 "reason": r.get("reason") or ""}
  54 | +            mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
  55 | +                         ledger_text=r.get("text"))
  56 | +            if getattr(src, "window", None) is not None:          # provenance: the window record it was cut from
  57 | +                mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
  58 | +                                                                            None)))
  59 | +            rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
  60 | +            rec["rank_score"] = M.rank_score(rec)
  61 | +            return rec
  62 | +        except (KeyError, TypeError, ValueError) as e:         # counted, never a crash (glm C1 P1-8)
  63 | +            malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
  64 | +            return None
  65 | +
  66 |      by_vid = {}
  67 |      for i, r in enumerate(rows):
  68 |          if not (isinstance(r, dict) and all(isinstance(r.get(k), str) and r.get(k) for k in ("moment_id", "video_id"))):
  69 | @@ -414,67 +437,80 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  70 |              report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
  71 |              continue
  72 |          src, path, passed_over = word_source(rs[0], ctx, store)
  73 | -        if src is None:                         # the WINDOW path: the best-ranked row of this video with a
  74 | -            wrow, why_w = None, []              # sentence-ready window record (rows arrive best first)
  75 | +        if src is not None:                          # the video's full-video word record: every row re-anchors in it
  76 | +            if passed_over:
  77 | +                report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
  78 | +            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
  79 |              for i, r in irs:
  80 | -                wp = word_pass.get(r["moment_id"])
  81 | -                if wp is None:
  82 | +                sp, info = reanchor(r, src)
  83 | +                if sp is None:
  84 | +                    report["not_anchored"][r["moment_id"]] = info
  85 | +                    continue
  86 | +                if (vid, sp.k0, sp.k1) in seen:
  87 | +                    report["duplicates"] += 1
  88 | +                    report["duplicates_of"][r["moment_id"]] = seen[(vid, sp.k0, sp.k1)]   # named (glm C4 P2-5)
  89 | +                    continue
  90 | +                rec = make(i, r, sp, info, src)
  91 | +                if rec is None:
  92 |                      continue
  93 | -                cand, cpath, why = window_source(r, wp, ctx, store)
  94 | -                if cand is not None:
  95 | -                    src, path, wrow = cand, cpath, r
  96 | -                    break
  97 | +                seen[(vid, sp.k0, sp.k1)] = r["moment_id"]
  98 | +                moments.append(rec)
  99 | +                sources[vid] = src
 100 | +            continue
 101 | +        caps, why_w, waiting, windows, kept = {}, [], 0, 0, []     # kept: (start, end, moment id) of window moments
 102 | +        for i, r in irs:                             # ONE WINDOW PER MOMENT
 103 | +            wp = word_pass.get(r["moment_id"])
 104 | +            if wp is None:
 105 | +                waiting += 1
 106 | +                continue
 107 | +            wsrc, wpath, why = window_source(r, wp, ctx, store)
 108 | +            if wsrc is None:
 109 |                  why_w.append(f"{r['moment_id']}: {why}")
 110 | -            if why_w:
 111 | -                report["window_passed_over"][vid] = why_w
 112 | -            if src is None:
 113 | -                why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 114 | -                                               ["no sentence-ready window record"]))
 115 | -                report["no_word_record"] += len(rs)
 116 | -                report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 117 | -                report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 118 |                  continue
 119 | -            src.context_source, cwhy = caption_source(wrow, ctx, store, ledger_store)
 120 | -            if src.context_source is None:
 121 | -                src.context_source = None
 122 | -                report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
 123 | -            report["window_records"][vid] = os.path.relpath(path, os.path.realpath(store))
 124 | -        elif passed_over:
 125 | -            report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 126 | -        if getattr(src, "window", None) is None:
 127 | -            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 128 | -        for i, r in irs:
 129 | -            sp, info = reanchor(r, src)
 130 | +            windows += 1
 131 | +            sha = r.get("transcript_sha256")
 132 | +            if sha not in caps:                      # the caption record the row was mined from, once per sha
 133 | +                caps[sha] = caption_source(r, ctx, store, ledger_store)
 134 | +            wsrc.context_source, cwhy = caps[sha]
 135 | +            if wsrc.context_source is None:
 136 | +                report["no_caption_context"][vid] = cwhy               # L-s fails closed for these clips
 137 | +            report["window_records"].setdefault(vid, []).append(os.path.relpath(wpath, os.path.realpath(store)))
 138 | +            sp, info = reanchor(r, wsrc)
 139 |              if sp is None:
 140 |                  report["not_anchored"][r["moment_id"]] = info
 141 |                  continue
 142 | -            if (vid, sp.k0, sp.k1) in seen:
 143 | +            dup = next((mid for a, b, mid in kept if a < sp.end and sp.start < b), None)
 144 | +            if dup is not None:                      # the same speech, cut from another of the video's windows
 145 |                  report["duplicates"] += 1
 146 | -                report["duplicates_of"][r["moment_id"]] = seen[(vid, sp.k0, sp.k1)]       # named (glm C4 P2-5)
 147 | +                report["duplicates_of"][r["moment_id"]] = dup
 148 |                  continue
 149 | -            try:
 150 | -                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
 151 | -                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
 152 | -                     "reason": r.get("reason") or ""}
 153 | -                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
 154 | -                             ledger_text=r.get("text"))
 155 | -                if getattr(src, "window", None) is not None:      # provenance: the window record it was cut from
 156 | -                    mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
 157 | -                                                                                None)))
 158 | -                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
 159 | -                rec["rank_score"] = M.rank_score(rec)
 160 | -            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
 161 | -                malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
 162 | +            rec = make(i, r, sp, info, wsrc)
 163 | +            if rec is None:
 164 |                  continue
 165 | -            seen[(vid, sp.k0, sp.k1)] = r["moment_id"]
 166 | +            key = f"{vid}@{wsrc.window['start_s']:.3f}-{wsrc.window['end_s']:.3f}"
 167 | +            rec["source_key"] = key
 168 | +            kept.append((sp.start, sp.end, r["moment_id"]))
 169 |              moments.append(rec)
 170 | -            sources[vid] = src
 171 | -    report["moments"], report["videos"] = len(moments), len(sources)
 172 | -    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
 173 | -        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 174 | +            sources[key] = wsrc
 175 | +        if why_w:
 176 | +            report["window_passed_over"][vid] = why_w
 177 | +        if not windows:
 178 | +            why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 179 | +                                           ["no sentence-ready window record"]))
 180 | +            report["no_word_record"] += len(rs)
 181 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 182 | +            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 183 | +        else:
 184 | +            report["window_waiting"] += waiting      # rows of a window video with no window record of their own
 185 | +    report["moments"], report["sources"] = len(moments), len(sources)
 186 | +    report["videos"] = len({m["video_id"] for m in moments})
 187 | +    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} videos "
 188 | +        f"({report['sources']} word records); {report['no_word_record']} rows wait for a word record, "
 189 | +        f"{report['window_waiting']} wait for their own window, {len(report['not_anchored'])} do not re-anchor, "
 190 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 191 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 192 | -        f"{len(report['fallbacks'])} read from a fallback record; {len(report['window_records'])} window record(s) "
 193 | -        f"used ({len(report['no_caption_context'])} without a caption record for L-s)")
 194 | +        f"{len(report['fallbacks'])} read from a fallback record; "
 195 | +        f"{sum(len(v) for v in report['window_records'].values())} window record(s) used "
 196 | +        f"({len(report['no_caption_context'])} video(s) without a caption record for L-s)")
 197 |      moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 198 |      return moments, sources, report
 199 | diff --git a/pipeline/package.py b/pipeline/package.py
 200 | index 8d8ae6a4..30a4b050 100644
 201 | --- a/pipeline/package.py
 202 | +++ b/pipeline/package.py
 203 | @@ -283,6 +283,7 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
 204 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 205 |            "vo_kind": vo_kind, "style": fields.get("style"),
 206 |            "segments": [{"label": lb, "moment_id": m["moment_id"],
 207 | +                        **({"source_key": m["source_key"]} if m.get("source_key") else {}),   # a window moment's
 208 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 209 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 210 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 211 | @@ -358,6 +359,12 @@ def _load_store(store):
 212 |          return json.load(f)
 213 |  
 214 |  
 215 | +def src_of(x, sources):
 216 | +    """A moment's (or a package segment's) own Source: a WINDOW moment's by its source_key (one window record per
 217 | +    moment, the word-pass worker's; ledger_build.build_inputs), every other one's by its video id."""
 218 | +    return sources[x.get("source_key") or x["video_id"]]
 219 | +
 220 | +
 221 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 222 |                store=None, log=print):
 223 |      """Step A (context only, package-independent by law L-s) on the best n usable moments, distinct channels first:
 224 | @@ -389,11 +396,11 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 225 |          chunk = todo[i:i + batch]
 226 |          contexts = {}
 227 |          for m in chunk:
 228 | -            text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1], *m["words"])
 229 | +            text, win = CI._window_text(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
 230 |              if text is None:        # no L-s context (a window record without its caption record, short coverage, an
 231 |                  fails[m["moment_id"]] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]   # unclocked
 232 |                  continue            # moment): THIS moment is not cleared; it never poisons its batch's call
 233 | -            contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
 234 | +            contexts[m["moment_id"]] = {"text": text, "title": src_of(m, sources).title or "",
 235 |                                          "channel": _name(m, ctx), "window": win,
 236 |                                          "published": str(m.get("published_at") or "")[:16],
 237 |                                          "show_date": ctx.now.strftime("%Y-%m-%d")}
 238 | @@ -865,7 +872,7 @@ def exclusion_for(router, m, sources, cache, seed=7):
 239 |      key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
 240 |      if key not in cache:
 241 |          import moments as M
 242 | -        src = sources[m["video_id"]]
 243 | +        src = src_of(m, sources)
 244 |          before, after = CI.context_around(src, m["sentences"][0], m["sentences"][1], *m["words"])
 245 |          if before is None:                                    # no context to judge in (a window record without its
 246 |              cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
 247 | @@ -922,7 +929,7 @@ def hook_onset_for(m, sources, work_dir, cache):
 248 |      if m["moment_id"] not in cache:
 249 |          import hook_onset as HO
 250 |          try:
 251 | -            cache[m["moment_id"]] = HO.measure(sources[m["video_id"]], m["words"][0], m["words"][1], m["video_id"],
 252 | +            cache[m["moment_id"]] = HO.measure(src_of(m, sources), m["words"][0], m["words"][1], m["video_id"],
 253 |                                                 float(m["start"]), float(m["end"]), work_dir)
 254 |          except Exception as e:
 255 |              cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 256 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
 257 | index 155fd48c..1dcfe9e5 100644
 258 | --- a/pipeline/speakers.py
 259 | +++ b/pipeline/speakers.py
 260 | @@ -182,7 +182,7 @@ def attribute(router, seg, src, meta, seed=7):
 261 |  def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 262 |      """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 263 |      for i, s in enumerate(pk["segments"]):
 264 | -        src, meta = sources.get(s["video_id"]), meta_for(s["video_id"])
 265 | +        src, meta = sources.get(s.get("source_key") or s["video_id"]), meta_for(s["video_id"])
 266 |          sp = attribute(router, s, src, meta)
 267 |          if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
 268 |              sp = attribute(router, s, src, meta, seed=8)
 269 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 270 | index 4417ea1e..0350cd47 100644
 271 | --- a/tests/package/test_ledger_build.py
 272 | +++ b/tests/package/test_ledger_build.py
 273 | @@ -440,13 +440,14 @@ class TestWindowRecords(unittest.TestCase):
 274 |          with tempfile.TemporaryDirectory() as d:
 275 |              rel, wp, r, words = window_fixture(d)
 276 |              far = dict(row("Bitcoin started as a quiet experiment.", start=100.0, end=104.0, mid="W2", vid="vidW"),
 277 | -                       transcript_sha256=r["transcript_sha256"])               # outside the window: it cannot anchor
 278 | +                       transcript_sha256=r["transcript_sha256"])               # no window record of its own
 279 |              ms, srcs, rep = LB.build_inputs([r, far], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 280 |              self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 281 |              self.assertEqual(ms[0]["text"], SENTS_W[2])
 282 | -            self.assertEqual(list(rep["not_anchored"]), ["W2"])
 283 | -            self.assertEqual(rep["window_records"], {"vidW": rel})
 284 | -            src = srcs["vidW"]
 285 | +            self.assertEqual((list(rep["not_anchored"]), rep["window_waiting"]), ([], 1))   # it waits for its own
 286 | +            self.assertEqual(rep["window_records"], {"vidW": [rel]})
 287 | +            self.assertEqual(ms[0]["source_key"], f"vidW@600.000-{wp['window'][1]:.3f}")   # one window per moment
 288 | +            src = srcs[ms[0]["source_key"]]
 289 |              self.assertEqual(src.context_source.transcript_method, "yt_auto")
 290 |              text, win = CI._window_text(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 291 |              t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 292 | @@ -460,6 +461,36 @@ class TestWindowRecords(unittest.TestCase):
 293 |              self.assertIn("caption line", before)
 294 |              self.assertIn("caption line", after)
 295 |  
 296 | +    def test_each_moment_reads_its_own_window_and_the_same_speech_twice_is_one_moment(self):
 297 | +        """The 02:01 FRESH build kept ONE window per video and lost 63 of 74 rows. The worker writes a window around
 298 | +        every moment, so each moment re-anchors in its OWN window (its source_key); two windows holding the same
 299 | +        speech give one moment (the better-ranked row keeps it)."""
 300 | +        ctx = E.Context(NOW, REG)
 301 | +        with tempfile.TemporaryDirectory() as d:
 302 | +            rel1, wp1, r1, words1 = window_fixture(d, w0=600.0)               # W1: "Nobody can stop Bitcoin ..."
 303 | +            rel2, wp2, r2, words2 = window_fixture(d, w0=640.0)               # W2: the same sentences, 40 s later
 304 | +            k = [w["word"] for w in words2].index("That")
 305 | +            n = len(SENTS_W[3].split())
 306 | +            r2 = dict(row(SENTS_W[3], start=words2[k]["start"], end=words2[k + n - 1]["end"], mid="W2", vid="vidW"),
 307 | +                      transcript_sha256=r1["transcript_sha256"])
 308 | +            wp2 = dict(wp2, moment_id="W2")
 309 | +            r3 = dict(r1, moment_id="W3")                                    # W1's speech again (W1's window record)
 310 | +            ms, srcs, rep = LB.build_inputs([r1, r2, r3], ctx, d, log=lambda s: None,
 311 | +                                            word_pass={"W1": wp1, "W2": wp2, "W3": dict(wp1, moment_id="W3")})
 312 | +            self.assertEqual(sorted(m["mined"]["ledger_moment_id"] for m in ms), ["W1", "W2"])
 313 | +            keys = {m["mined"]["ledger_moment_id"]: m["source_key"] for m in ms}
 314 | +            self.assertNotEqual(keys["W1"], keys["W2"])                       # two windows, two Sources
 315 | +            self.assertEqual(set(srcs), set(keys.values()))
 316 | +            self.assertEqual(rep["duplicates_of"], {"W3": "W1"})              # the same speech: one moment
 317 | +            self.assertEqual((rep["videos"], rep["sources"]), (1, 2))
 318 | +            import context_integrity as CI                                     # the gate reads each segment's own
 319 | +            m2 = next(m for m in ms if m["mined"]["ledger_moment_id"] == "W2")  # window (package.src_of's key)
 320 | +            seg = {"label": "clip_01", "video_id": "vidW", "source_key": m2["source_key"], "k0": m2["sentences"][0],
 321 | +                   "k1": m2["sentences"][1], "words": m2["words"], "channel": "DataDash"}
 322 | +            got = CI.contexts_from_sources({"segments": [seg]}, srcs)
 323 | +            self.assertIn("<selected>" + SENTS_W[3] + "</selected>", got["clip_01"]["text"])
 324 | +            self.assertIn("caption line", got["clip_01"]["text"])
 325 | +
 326 |      def test_the_caption_coverage_is_measured_never_assumed(self):
 327 |          """Audit 0123 C1 (qwen, glm): a caption that stops short of 60 s after the clip (and short of the media's end),
 328 |          or starts after the 90 s before it (and not near the media's start), leaves the context unavailable."""
 329 | @@ -473,7 +504,7 @@ class TestWindowRecords(unittest.TestCase):
 330 |                  rel, wp, r, words = window_fixture(d, **kw)
 331 |                  ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 332 |                  m = ms[0]
 333 | -                text, win = CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"])
 334 | +                text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
 335 |                  self.assertEqual(text is not None, ok, kw)
 336 |  
 337 |      def test_a_wordless_stretch_inside_the_window_is_bridged_to_reach_the_marks(self):
 338 | @@ -486,7 +517,7 @@ class TestWindowRecords(unittest.TestCase):
 339 |              ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 340 |              m = ms[0]
 341 |              t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 342 | -            text, win = CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"])
 343 | +            text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
 344 |              self.assertLessEqual(win[0], t0 - CI.CONTEXT_BEFORE_S)          # it reaches past the gap
 345 |              self.assertLess(win[0], 515.0)                                     # a word from before the gap ...
 346 |              self.assertTrue(text.startswith("money caption line 585"))        # ... ("money", the last word of line 510)
 347 | @@ -585,7 +616,7 @@ class TestWindowRecords(unittest.TestCase):
 348 |              self.assertEqual(rep["no_caption_context"], {"vidW": "no record in the store matches the row's "
 349 |                                                                    "transcript_sha256"})
 350 |              m = ms[0]
 351 | -            self.assertEqual(CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"]),
 352 | +            self.assertEqual(CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"]),
 353 |                               (None, None))                                 # step A: unavailable, never cleared
 354 |              ex = PK.exclusion_for(None, m, srcs, {})                       # no model call is made
 355 |              self.assertEqual((ex["verdict"], ex["measured"]), ("exclude", False))
 356 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
It moves the ledger build from ONE window record per video to ONE WINDOW RECORD PER MOMENT.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the integrator's word-pass worker writes a sentence-ready window record (about +-45 s of words) around EACH
ledger moment. The FRESH build at 02:01 ET used one window per video (the best-ranked row's). 63 of 74 fresh rows
therefore could not re-anchor, which left 11 moments and no package.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of a sentence-ready, word-timed record (L-o 1, L-e);
- L-s context (>= 90 s before, 60 s after) for a window clip comes from the caption record the ledger mined, by time;
- no delivered span is used again (L-p).

The change:
1. pipeline/ledger_build.py build_inputs():
   - A video WITH a sentence-ready full-video word record: unchanged. Every row re-anchors in it, with the
     (vid, k0, k1) dedup, and the Source is keyed by the video id.
   - Otherwise each row with its OWN sentence-ready window record (window_source(): every claim checked) re-anchors
     in THAT window. Its moment carries source_key = "<video>@<w0>-<w1>", the key of its Source in the returned
     sources.
   - The caption record for L-s is looked up once per mined sha.
   - Two window moments of one video whose spans overlap in TIME are one moment: the better-ranked row (rows arrive
     best first) keeps it, and the other is counted in duplicates_of.
   - Rows of a window video without their own window record are counted in window_waiting.
   - The report adds sources and videos counts, and window_records becomes {video: [records]}.
2. pipeline/package.py:
   - src_of(x, sources) = sources[x.get("source_key") or x["video_id"]], used by prescreen (step A), exclusion_for
     and hook_onset_for.
   - _package's segment rows carry source_key when the moment has one.
3. pipeline/context_integrity.py contexts_from_sources() and pipeline/speakers.py attribute_package(): look the
   segment's Source up by source_key, else video_id.
4. tests/package/test_ledger_build.py:
   - two windows of one video give two moments with two Sources;
   - the same speech in two windows is one moment;
   - the gate's context check reads the segment's own window;
   - the existing window tests use each moment's source_key.

Check, concretely:
(a) Can any lookup still reach the WRONG window or Source for a moment or segment, e.g. one keyed by video_id when a
    source_key exists?
(b) Can the same speech enter two clips through two overlapping windows, or a span cross a window's edge?
(c) Is anything in the full-video path changed?
(d) Does anything downstream (pin, render, novelty, dedup, speakers) still assume one Source per video?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".

