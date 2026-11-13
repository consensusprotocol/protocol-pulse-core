# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0123
# Branch: pp-selectid
# Generated: 2026-11-13 01:24 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0123/C1_STEP.diff (558 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 0c4bf2f9..b3b07d71 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -83,9 +83,56 @@ def mark(parts):
   6 |      return " ".join(out)
   7 |  
   8 |  
   9 | +def caption_parts(src, k0, k1, w0=None, w1=None, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S):
  10 | +    """A moment on a WINDOW word record (the integrator's word-pass worker: about +-45 s of words around one moment,
  11 | +    on the YouTube clock). Under the contract agreed with the integrator, its L-s context comes from the full-video
  12 | +    CAPTION record the ledger mined it from (src.context_source). The selection is the window record's own words, and
  13 | +    the context is the caption's words by TIME: every caption word overlapping the >= `before` s before the selection,
  14 | +    and every caption word starting in the `after` s after it, or to the media's edge (a caption record is the whole
  15 | +    video). YouTube's automatic captions carry no punctuation, so the window is cut by time, never by sentences, and
  16 | +    the pull-back to a question (which needs a '?') does not apply.
  17 | +    -> ([(text, selected?)], (from_s, to_s)), or (None, None) when there is no caption record or a time is missing
  18 | +    (unmeasured: the context is unavailable and L-s fails closed)."""
  19 | +    cs = getattr(src, "context_source", None)
  20 | +    S, T = src.sentences, src.tokens
  21 | +    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
  22 | +    t0, t1 = E._time(T[lo], "start"), E._time(T[hi], "end")
  23 | +    if cs is None or t0 is None or t1 is None or not cs.tokens:
  24 | +        return None, None
  25 | +    timed = [(tok, E._time(tok, "start"), E._time(tok, "end")) for tok in cs.tokens]
  26 | +    if any(a is None or b is None for _, a, b in timed):
  27 | +        return None, None                            # an unclocked caption record: no measurable window
  28 | +    pre = [tok for tok, a, b in timed if b > t0 - before and a < t0]
  29 | +    post = [tok for tok, a, b in timed if t1 < a <= t1 + after]
  30 | +    parts = [(E.spoken(pre), False), (E.spoken(T[lo:hi + 1]), True), (E.spoken(post), False)]
  31 | +    return [(t, sel) for t, sel in parts if t.strip()], (round(t0 - before, 3), round(t1 + after, 3))
  32 | +
  33 | +
  34 | +def context_around(src, k0, k1, w0=None, w1=None):
  35 | +    """(the context before the selection, the context after it) as text, for any Source: a window record's from its
  36 | +    caption record (caption_parts), every other record's from its own window(). (None, None) when unavailable."""
  37 | +    if getattr(src, "window", None) is not None:
  38 | +        parts, win = caption_parts(src, k0, k1, w0, w1)
  39 | +        if parts is None:
  40 | +            return None, None
  41 | +        i = next(n for n, (_, sel) in enumerate(parts) if sel)
  42 | +        return " ".join(t for t, _ in parts[:i]), " ".join(t for t, _ in parts[i + 1:])
  43 | +    win = window(src, k0, k1)
  44 | +    if win is None:
  45 | +        return None, None
  46 | +    a, b = win
  47 | +    S, T = src.sentences, src.tokens
  48 | +    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
  49 | +    return E.spoken(T[S[a][0]:lo]), E.spoken(T[hi + 1:S[b][1] + 1])
  50 | +
  51 | +
  52 |  def _window_text(src, k0, k1, w0=None, w1=None):
  53 |      """The window's text with the selection marked. With word indices w0..w1 the selection is marked by WORDS (a
  54 | -    moment cut inside a store sentence, ruling 7 / orchestrator 06:45), else by sentences k0..k1."""
  55 | +    moment cut inside a store sentence, ruling 7 / orchestrator 06:45), else by sentences k0..k1. A moment on a WINDOW
  56 | +    word record takes its context from its caption record (caption_parts)."""
  57 | +    if getattr(src, "window", None) is not None:
  58 | +        parts, win = caption_parts(src, k0, k1, w0, w1)
  59 | +        return (mark(parts), win) if parts is not None else (None, None)
  60 |      win = window(src, k0, k1)
  61 |      if win is None:
  62 |          return None, None
  63 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
  64 | index 847d60a3..98c455dd 100644
  65 | --- a/pipeline/ledger_build.py
  66 | +++ b/pipeline/ledger_build.py
  67 | @@ -7,11 +7,20 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
  68 |    interpreter, from the pp-ingest worktree, until the integrator merges it.
  69 |  - READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  70 |    (transcripts/<vid>/transcript.whisper_words_punct.json, then transcript.whisper_words.json: WORD_RECORDS, in that
  71 | -  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments). Window records from
  72 | -  the word-pass worker (the integrator's contract: transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json,
  73 | -  youtube clock, listed in moments/word_pass.jsonl) need their L-s context from the CAPTION record. That is not wired
  74 | -  yet: a row whose video has only a window record counts as waiting for a word record (report.no_word_record, "no
  75 | -  word record in the store") and is not used. No window record exists yet (none in the store at 23:36 ET Nov 12).
  76 | +  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments).
  77 | +- WINDOW records: a video with no such full-video record may have WINDOW records from the integrator's word-pass
  78 | +  worker (pipeline/word_pass_worker.py on branch word-pass, 514dd704).
  79 | +  - Each is transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json: about +-45 s of words around one ledger
  80 | +    moment, on the YouTube clock, with words_sha256.
  81 | +  - Each is listed in moments/word_pass.jsonl as {moment_id, video_id, window_record, record_sha256, sentence_ready,
  82 | +    window, at}.
  83 | +  - word_pass_index() reads that list. window_source() checks every claim before use: the file's sha256 is the row's
  84 | +    record_sha256, the segments sha, words_sha256, the words spell the segments, the YouTube clock, nothing still
  85 | +    unpunctuated, and the ledger row's span inside the window.
  86 | +  - One window per video: the best-ranked row's. The video's other rows re-anchor in it, or are counted out.
  87 | +  - L-s context comes from the caption record the ledger mined the moment from (caption_source(): its segments sha
  88 | +    is the row's transcript_sha256), cut by time (context_integrity.caption_parts). Without one, the context is
  89 | +    unavailable and L-s fails closed.
  90 |  - RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  91 |    row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  92 |    SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  93 | @@ -20,6 +29,7 @@ FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call h
  94 |    row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
  95 |  -> build_inputs(...) = (moments, sources, report).
  96 |  """
  97 | +import hashlib
  98 |  import json
  99 |  import os
 100 |  import sys
 101 | @@ -47,6 +57,9 @@ INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest
 102 |  MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
 103 |  STORE = os.path.join(MAIN, "data", "editorial")
 104 |  WORD_RECORDS = ("transcript.whisper_words_punct.json", "transcript.whisper_words.json")
 105 | +WORD_PASS = os.path.join(STORE, "moments", "word_pass.jsonl")     # the word-pass worker's rows (the integrator's)
 106 | +WINDOW_TOL_S = 0.01      # the ledger row's span must lie inside its window record's [start_s, end_s] (the worker cut
 107 | +                         # the window around that very span; this is only the 3-decimal rounding)
 108 |                            # the store's two word-record slots (transcript_store._store: transcript.<method>.json), read
 109 |                            # in this order: a total order, never the file system's (glm C3 P1-2)
 110 |  
 111 | @@ -129,6 +142,134 @@ def words_off_segments(rec, tol=0.001):
 112 |      return None
 113 |  
 114 |  
 115 | +def _num(x):
 116 | +    try:
 117 | +        v = float(x)
 118 | +    except (TypeError, ValueError):
 119 | +        return None
 120 | +    return v if v == v and v not in (float("inf"), float("-inf")) else None
 121 | +
 122 | +
 123 | +def word_pass_index(path=WORD_PASS):
 124 | +    """The word-pass worker's rows -> ({moment_id: the LAST row of that moment, when it is sentence_ready with a
 125 | +    window_record and a record_sha256}, report). A failed moment's row has neither, and the worker never retries it.
 126 | +    No file yet = no window record yet: ({}, report). A file that exists but cannot be read raises: it is never read
 127 | +    as an empty word pass (law L-j)."""
 128 | +    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path}
 129 | +    try:
 130 | +        f = open(path)
 131 | +    except FileNotFoundError:
 132 | +        return {}, dict(rep, file="none yet: " + path)
 133 | +    last = {}
 134 | +    with f:
 135 | +        for line in f:
 136 | +            if not line.strip():
 137 | +                continue
 138 | +            rep["rows"] += 1
 139 | +            try:
 140 | +                r = json.loads(line)
 141 | +            except ValueError:
 142 | +                rep["unreadable"] += 1
 143 | +                continue
 144 | +            if not isinstance(r, dict) or not isinstance(r.get("moment_id"), str):
 145 | +                rep["unreadable"] += 1
 146 | +                continue
 147 | +            last[r["moment_id"]] = r
 148 | +    out = {}
 149 | +    for mid, r in last.items():
 150 | +        if r.get("error") or r.get("window_record") is None:
 151 | +            rep["failed"] += 1
 152 | +        elif r.get("sentence_ready") is not True:
 153 | +            rep["not_ready"] += 1
 154 | +        elif isinstance(r.get("window_record"), str) and isinstance(r.get("record_sha256"), str):
 155 | +            out[mid] = r
 156 | +            rep["ready"] += 1
 157 | +        else:
 158 | +            rep["unreadable"] += 1
 159 | +    return out, rep
 160 | +
 161 | +
 162 | +def window_source(row, wp, ctx, store=STORE):
 163 | +    """The moment's sentence-ready WINDOW record (its word_pass.jsonl row `wp`) as an eligibility Source, every claim
 164 | +    checked -> (Source, path, None) or (None, None, why). The Source carries .window = {start_s, end_s, record,
 165 | +    words_sha256, record_sha256}; file_head only when the window starts at the media's first second."""
 166 | +    vid, rel = row["video_id"], wp["window_record"]
 167 | +    name = os.path.basename(rel)
 168 | +    base = os.path.join(os.path.realpath(store), "transcripts", vid, "windows")
 169 | +    path = os.path.realpath(os.path.join(store, rel))
 170 | +    if wp.get("video_id") != vid or os.path.dirname(path) != base:
 171 | +        return None, None, f"{name}: not this video's window record (transcripts/{vid}/windows/)"
 172 | +    try:
 173 | +        with open(path, "rb") as f:
 174 | +            raw = f.read()
 175 | +        rec = json.loads(raw)
 176 | +    except (OSError, ValueError):
 177 | +        return None, None, f"{name}: cannot be read"
 178 | +    if hashlib.sha256(raw).hexdigest() != wp["record_sha256"]:
 179 | +        return None, None, f"{name}: the file is not the one word_pass.jsonl names (record_sha256)"
 180 | +    if not isinstance(rec, dict) or rec.get("video_id") != vid or rec.get("transcript_method") != "whisper_words_punct":
 181 | +        return None, None, f"{name}: not a punctuated word record of this video"
 182 | +    try:
 183 | +        sha = ts.segments_sha256(rec.get("segments") or [])
 184 | +        wsha = hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in rec["words"]],
 185 | +                                         ensure_ascii=False).encode()).hexdigest()
 186 | +    except (KeyError, TypeError, ValueError, AttributeError):
 187 | +        return None, None, f"{name}: its segments or words cannot be hashed"
 188 | +    if rec.get("transcript_sha256") != sha:
 189 | +        return None, None, f"{name}: its segments do not match its transcript_sha256"
 190 | +    if rec.get("words_sha256") != wsha:
 191 | +        return None, None, f"{name}: its words do not match its words_sha256"
 192 | +    off = words_off_segments(rec)
 193 | +    if off:
 194 | +        return None, None, f"{name}: its words do not spell its sha-checked segments ({off})"
 195 | +    win = rec.get("window") if isinstance(rec.get("window"), dict) else {}
 196 | +    w0, w1 = _num(win.get("start_s")), _num(win.get("end_s"))
 197 | +    if w0 is None or w1 is None or win.get("clock") != "youtube":
 198 | +        return None, None, f"{name}: no window on the YouTube clock"
 199 | +    if (rec.get("punctuation") or {}).get("still_unpunctuated") is not False:
 200 | +        return None, None, f"{name}: a stretch is still unpunctuated (law L-e)"
 201 | +    t0, t1 = _num(row.get("start")), _num(row.get("end"))
 202 | +    if t0 is None or t1 is None or t0 < w0 - WINDOW_TOL_S or t1 > w1 + WINDOW_TOL_S:
 203 | +        return None, None, f"{name}: the row's span {t0}-{t1} is not inside the window {w0}-{w1}"
 204 | +    if rec.get("channel_id") and rec.get("channel_id") != row.get("channel_id"):
 205 | +        return None, None, f"{name}: it names channel {rec.get('channel_id')}, the ledger row {row.get('channel_id')}"
 206 | +    timing, toks = S.tokens_from_record(rec)
 207 | +    reg = ctx.channel(row.get("channel_id")) or {}
 208 | +    src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 209 | +                   row.get("published_at"), sha, "whisper_words_punct", toks, timing=timing,
 210 | +                   title=row.get("title") or "", file_head=(w0 == 0.0), vod=True)
 211 | +    if not E.sentence_ready(src):
 212 | +        return None, None, f"{name}: not sentence-ready (law L-e)"
 213 | +    src.window = {"start_s": w0, "end_s": w1, "record": rel, "words_sha256": wsha, "record_sha256": wp["record_sha256"]}
 214 | +    return src, path, None
 215 | +
 216 | +
 217 | +def caption_source(row, ctx, store=STORE):
 218 | +    """The full-video record the ledger row was MINED from: the one whose segments sha is the row's transcript_sha256.
 219 | +    It is a window record's L-s context (the contract) -> (Source, file name) or (None, why)."""
 220 | +    vid, want = row["video_id"], row.get("transcript_sha256")
 221 | +    d = os.path.join(store, "transcripts", vid)
 222 | +    try:
 223 | +        names = sorted(n for n in os.listdir(d) if n.startswith("transcript.") and n.endswith(".json"))
 224 | +    except OSError:
 225 | +        return None, "no transcript directory for the video"
 226 | +    for n in names:
 227 | +        try:
 228 | +            with open(os.path.join(d, n)) as f:
 229 | +                rec = json.load(f)
 230 | +            if not isinstance(rec, dict) or not want or rec.get("transcript_sha256") != want or \
 231 | +                    ts.segments_sha256(rec.get("segments") or []) != want:
 232 | +                continue
 233 | +            timing, toks = S.tokens_from_record(rec)
 234 | +        except (OSError, ValueError, KeyError, TypeError, AttributeError):
 235 | +            continue
 236 | +        reg = ctx.channel(row.get("channel_id")) or {}
 237 | +        return E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
 238 | +                        row.get("published_at"), want, rec.get("transcript_method"), toks, timing=timing,
 239 | +                        title=row.get("title") or "", file_head=True, vod=True), n
 240 | +    return None, "no record in the store matches the row's transcript_sha256"
 241 | +
 242 | +
 243 |  def word_source(row, ctx, store=STORE):
 244 |      """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
 245 |      checked), as an eligibility Source with the row's identity -> (Source, path, passed_over), or (None, None,
 246 | @@ -222,11 +363,14 @@ def reanchor(row, src):
 247 |      return sp, info
 248 |  
 249 |  
 250 | -def build_inputs(rows, ctx, store=STORE, log=print):
 251 | -    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). Rows on a video with no sentence-
 252 | -    ready word record, rows whose text does not re-anchor on whole sentences, and duplicates of one span are dropped,
 253 | -    each counted with why."""
 254 | +def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None):
 255 | +    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
 256 | +    {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
 257 | +    nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
 258 | +    span are dropped, each counted with why."""
 259 | +    word_pass = word_pass or {}
 260 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
 261 | +              "window_records": {}, "window_passed_over": {}, "no_caption_context": {},
 262 |                "fallbacks": {},
 263 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
 264 |                "moments": 0, "videos": 0,
 265 | @@ -249,15 +393,35 @@ def build_inputs(rows, ctx, store=STORE, log=print):
 266 |              report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
 267 |              continue
 268 |          src, path, passed_over = word_source(rs[0], ctx, store)
 269 | -        if src is None:
 270 | -            why = "; ".join(passed_over)
 271 | -            report["no_word_record"] += len(rs)
 272 | -            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 273 | -            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 274 | -            continue
 275 | -        if passed_over:
 276 | +        if src is None:                         # the WINDOW path: the best-ranked row of this video with a
 277 | +            wrow, why_w = None, []              # sentence-ready window record (rows arrive best first)
 278 | +            for i, r in irs:
 279 | +                wp = word_pass.get(r["moment_id"])
 280 | +                if wp is None:
 281 | +                    continue
 282 | +                cand, cpath, why = window_source(r, wp, ctx, store)
 283 | +                if cand is not None:
 284 | +                    src, path, wrow = cand, cpath, r
 285 | +                    break
 286 | +                why_w.append(f"{r['moment_id']}: {why}")
 287 | +            if why_w:
 288 | +                report["window_passed_over"][vid] = why_w
 289 | +            if src is None:
 290 | +                why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
 291 | +                                               ["no sentence-ready window record"]))
 292 | +                report["no_word_record"] += len(rs)
 293 | +                report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
 294 | +                report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
 295 | +                continue
 296 | +            src.context_source, cwhy = caption_source(wrow, ctx, store)
 297 | +            if src.context_source is None:
 298 | +                src.context_source = None
 299 | +                report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
 300 | +            report["window_records"][vid] = os.path.relpath(path, os.path.realpath(store))
 301 | +        elif passed_over:
 302 |              report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
 303 | -        report["word_records"][vid] = os.path.relpath(path, store)        # read; whether a moment came of it: moments
 304 | +        if getattr(src, "window", None) is None:
 305 | +            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
 306 |          for i, r in irs:
 307 |              sp, info = reanchor(r, src)
 308 |              if sp is None:
 309 | @@ -286,6 +450,7 @@ def build_inputs(rows, ctx, store=STORE, log=print):
 310 |          f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
 311 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
 312 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
 313 | -        f"{len(report['fallbacks'])} read from a fallback record")
 314 | +        f"{len(report['fallbacks'])} read from a fallback record; {len(report['window_records'])} window record(s) "
 315 | +        f"used ({len(report['no_caption_context'])} without a caption record for L-s)")
 316 |      moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
 317 |      return moments, sources, report
 318 | diff --git a/pipeline/package.py b/pipeline/package.py
 319 | index 95b12b09..aaae8f37 100644
 320 | --- a/pipeline/package.py
 321 | +++ b/pipeline/package.py
 322 | @@ -858,12 +858,13 @@ def exclusion_for(router, m, sources, cache, seed=7):
 323 |      if key not in cache:
 324 |          import moments as M
 325 |          src = sources[m["video_id"]]
 326 | -        a, b = CI.window(src, m["sentences"][0], m["sentences"][1])
 327 | -        w0, w1 = m["words"]
 328 | -        cache[key] = M.exclusion_verdict(
 329 | -            router, m["text"], E.spoken(src.tokens[src.sentences[a][0]:w0]),
 330 | -            E.spoken(src.tokens[w1 + 1:src.sentences[b][1] + 1]), seed=seed,
 331 | -            avoid_model=(m.get("mined") or {}).get("by"))
 332 | +        before, after = CI.context_around(src, m["sentences"][0], m["sentences"][1], *m["words"])
 333 | +        if before is None:                                    # no context to judge in (a window record without its
 334 | +            cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
 335 | +                          "risks": [], "backend": None, "measured": False, "replayed": False}            # record)
 336 | +        else:
 337 | +            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,
 338 | +                                             avoid_model=(m.get("mined") or {}).get("by"))
 339 |      return cache[key]
 340 |  
 341 |  
 342 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 343 | index 5d344003..37091176 100644
 344 | --- a/tests/package/proof_ledger.py
 345 | +++ b/tests/package/proof_ledger.py
 346 | @@ -2,7 +2,9 @@
 347 |  """ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.
 348 |  
 349 |  - The rows are pp-ingest's adapter (best_unused_moments), read-only.
 350 | -- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py).
 351 | +- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py). That
 352 | +  is the store's full-video record, or else the integrator's word-pass WINDOW record (moments/word_pass.jsonl,
 353 | +  --word-pass), whose L-s context comes from the caption record the ledger mined.
 354 |  - "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
 355 |  - Novelty (L-p): every clip span of the pins already delivered (--delivered, required; tonight: the 37c5b5f5 review,
 356 |    run 165629, and the 41f29b1f medley) is passed to package.usable as delivered. usable drops ANY moment that overlaps
 357 | @@ -80,6 +82,7 @@ def main(argv=None):
 358 |      ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 359 |      ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 360 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 361 | +    ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 362 |      a = ap.parse_args(argv)
 363 |      now = datetime.now(timezone.utc)
 364 |      try:                                                 # read before anything is written (glm C2 N-4)
 365 | @@ -108,7 +111,10 @@ def main(argv=None):
 366 |          f"{len(delivered)} clip spans out")
 367 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 368 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 369 | -    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say)
 370 | +    wp, wp_rep = LB.word_pass_index(a.word_pass)
 371 | +    say(f"  word pass: {json.dumps(wp_rep)}")
 372 | +    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp)
 373 | +    inputs["word_pass"] = wp_rep
 374 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 375 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 376 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 377 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 378 | index 696b7d11..07460ed1 100644
 379 | --- a/tests/package/test_ledger_build.py
 380 | +++ b/tests/package/test_ledger_build.py
 381 | @@ -4,6 +4,7 @@
 382 |  - reading the store's word record (its sha checked, sentence-ready only);
 383 |  - turning rows into the packager's moments (counted drops, no duplicate spans);
 384 |  - the adapter's failures are raised, never read as an empty ledger."""
 385 | +import hashlib
 386 |  import io
 387 |  import json
 388 |  import os
 389 | @@ -19,7 +20,7 @@ sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 390 |  import eligibility as E  # noqa: E402
 391 |  import ledger_build as LB  # noqa: E402
 392 |  import transcript_store as ts  # noqa: E402
 393 | -from test_eligibility import NOW, REG, source  # noqa: E402
 394 | +from test_eligibility import NOW, REG, source, tokens  # noqa: E402
 395 |  
 396 |  SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
 397 |           "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
 398 | @@ -241,7 +242,8 @@ class TestWordSourceAndInputs(unittest.TestCase):
 399 |              self.assertEqual(ms, [])
 400 |              self.assertEqual(rep["no_word_record_why"],
 401 |                               {"transcript.whisper_words_punct.json: its segments do not match its transcript_sha256; "
 402 | -                              "transcript.whisper_words.json: not sentence-ready (law L-e)": 1})
 403 | +                              "transcript.whisper_words.json: not sentence-ready (law L-e); "
 404 | +                              "no sentence-ready window record": 1})
 405 |              self.store_with(d, "vidA", SENTS, method="whisper_words")           # a verbatim record that IS ready
 406 |              ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
 407 |              self.assertEqual(len(ms), 1)
 408 | @@ -271,7 +273,8 @@ class TestWordSourceAndInputs(unittest.TestCase):
 409 |              self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["L1"])
 410 |              self.assertEqual(sorted(rep["malformed"]), ["L2", "row 2", "row 3", "row 4"])
 411 |              ms, _, rep = LB.build_inputs([row(SENTS[0], vid="vidZ")], ctx, d, log=lambda s: None)
 412 | -            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store"}})
 413 | +            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store; "
 414 | +                                                                                 "no sentence-ready window record"}})
 415 |  
 416 |      def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
 417 |          ctx = E.Context(NOW, REG)
 418 | @@ -328,6 +331,139 @@ class TestAdapter(unittest.TestCase):
 419 |              self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))
 420 |  
 421 |  
 422 | +SENTS_W = ["So we were talking about money before the break.", "Bitcoin is a global free market.",
 423 | +           "Nobody can stop Bitcoin from settling a payment.", "That is the whole design and it works every day.",
 424 | +           "Anyway, let us move on to the next question."]
 425 | +
 426 | +
 427 | +def window_fixture(d, vid="vidW", w0=600.0, still=False, clock="youtube", caption=True):
 428 | +    """A window record exactly as the word-pass worker's make_record writes it (words on the YouTube clock, segments
 429 | +    from sentences_from_words, words_sha256, window, punctuation), its word_pass.jsonl row, and the full-video caption
 430 | +    record the ledger mined from (unpunctuated lines over the whole video)."""
 431 | +    words = [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in tokens(SENTS_W, t0=w0 + 1.0)]
 432 | +    segs = [{"start": round(x["start"], 3), "end": round(x["end"], 3), "text": x["text"].strip()}
 433 | +            for x in ts.sentences_from_words(words)]
 434 | +    w1 = round(words[-1]["end"] + 1.0, 3)
 435 | +    rec = {"video_id": vid, "transcript_method": "whisper_words_punct", "segments": segs,
 436 | +           "transcript_sha256": ts.segments_sha256(segs), "words": words,
 437 | +           "words_sha256": hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in words],
 438 | +                                                     ensure_ascii=False).encode()).hexdigest(),
 439 | +           "punctuation": {"still_unpunctuated": still},
 440 | +           "window": {"start_s": w0, "end_s": w1, "clock": clock, "offset_s": w0}}
 441 | +    rel = f"transcripts/{vid}/windows/{w0:.3f}-{w1:.3f}.whisper_words_punct.json"
 442 | +    os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
 443 | +    with open(os.path.join(d, rel), "w") as f:
 444 | +        json.dump(rec, f)
 445 | +    with open(os.path.join(d, rel), "rb") as f:
 446 | +        sha = hashlib.sha256(f.read()).hexdigest()
 447 | +    wp = {"moment_id": "W1", "video_id": vid, "window_record": rel, "record_sha256": sha, "sentence_ready": not still,
 448 | +          "window": [w0, w1], "at": "2026-11-13T06:00:00+00:00"}
 449 | +    cap = None
 450 | +    if caption:
 451 | +        lines = [{"start": float(t), "end": float(t + 5), "text": f"caption line {t} about money"} for t in range(0, 900, 5)]
 452 | +        cap = ts.segments_sha256(lines)
 453 | +        with open(os.path.join(d, "transcripts", vid, "transcript.yt_auto.json"), "w") as f:
 454 | +            json.dump({"video_id": vid, "transcript_method": "yt_auto", "segments": lines, "transcript_sha256": cap}, f)
 455 | +    k = [i for i, t in enumerate(words) if t["word"] == "Nobody"][0]
 456 | +    n = len(SENTS_W[2].split())
 457 | +    r = dict(row(SENTS_W[2], start=words[k]["start"], end=words[k + n - 1]["end"], mid="W1", vid=vid),
 458 | +             transcript_sha256=cap)
 459 | +    return rel, wp, r, words
 460 | +
 461 | +
 462 | +class TestWindowRecords(unittest.TestCase):
 463 | +    """The integrator's word-pass worker (word-pass 514dd704): window records listed in moments/word_pass.jsonl."""
 464 | +
 465 | +    def test_the_word_pass_index_reads_each_moments_last_ready_row_and_counts_the_rest(self):
 466 | +        with tempfile.TemporaryDirectory() as d:
 467 | +            p = os.path.join(d, "word_pass.jsonl")
 468 | +            self.assertEqual(LB.word_pass_index(p)[0], {})                          # no file yet: no window record
 469 | +            rows = [{"moment_id": "A", "window_record": None, "record_sha256": None, "sentence_ready": False,
 470 | +                     "error": "word pass: boom"},
 471 | +                    {"moment_id": "B", "window_record": "x", "record_sha256": "s", "sentence_ready": False},
 472 | +                    {"moment_id": "C", "window_record": "x", "record_sha256": "s1", "sentence_ready": True},
 473 | +                    {"moment_id": "C", "window_record": "y", "record_sha256": "s2", "sentence_ready": True,
 474 | +                     "reused": True}]
 475 | +            with open(p, "w") as f:
 476 | +                f.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
 477 | +            idx, rep = LB.word_pass_index(p)
 478 | +            self.assertEqual(list(idx), ["C"])
 479 | +            self.assertEqual(idx["C"]["record_sha256"], "s2")                       # the last row of a moment wins
 480 | +            self.assertEqual((rep["failed"], rep["not_ready"], rep["ready"], rep["unreadable"]), (1, 1, 1, 1))
 481 | +
 482 | +    def test_a_window_record_is_used_only_when_every_claim_checks_out(self):
 483 | +        ctx = E.Context(NOW, REG)
 484 | +        with tempfile.TemporaryDirectory() as d:
 485 | +            rel, wp, r, words = window_fixture(d)
 486 | +            src, path, why = LB.window_source(r, wp, ctx, d)
 487 | +            self.assertIsNone(why)
 488 | +            self.assertEqual((src.timing, src.file_head, src.window["start_s"]), ("word", False, 600.0))
 489 | +            p = os.path.join(d, rel)
 490 | +            with open(p) as f:
 491 | +                good = json.load(f)
 492 | +
 493 | +            def tampered(rec, **row_change):
 494 | +                with open(p, "w") as f:
 495 | +                    json.dump(rec, f)
 496 | +                with open(p, "rb") as f:
 497 | +                    sha = hashlib.sha256(f.read()).hexdigest()
 498 | +                return LB.window_source(dict(r, **row_change.get("row", {})), dict(wp, record_sha256=sha), ctx, d)[2]
 499 | +            w = [dict(x) for x in good["words"]]
 500 | +            w[3]["start"] += 0.05                                     # an INTERIOR word's time: only words_sha256 sees it
 501 | +            self.assertIn("words_sha256", tampered(dict(good, words=w)))
 502 | +            self.assertIn("still unpunctuated", tampered(dict(good, punctuation={"still_unpunctuated": True})))
 503 | +            self.assertIn("YouTube clock", tampered(dict(good, window=dict(good["window"], clock="window"))))
 504 | +            self.assertIn("not inside the window", tampered(good, row={"start": 10.0, "end": 20.0}))
 505 | +            with open(p, "w") as f:
 506 | +                json.dump(good, f)
 507 | +            self.assertIn("record_sha256", LB.window_source(r, dict(wp, record_sha256="0" * 64), ctx, d)[2])
 508 | +            self.assertIn("not this video's window record",
 509 | +                          LB.window_source(r, dict(wp, window_record="transcripts/vidW/x.json"), ctx, d)[2])
 510 | +
 511 | +    def test_a_window_from_the_media_start_is_file_head(self):
 512 | +        with tempfile.TemporaryDirectory() as d:
 513 | +            rel, wp, r, words = window_fixture(d, w0=0.0)
 514 | +            self.assertTrue(LB.window_source(r, wp, E.Context(NOW, REG), d)[0].file_head)
 515 | +
 516 | +    def test_a_video_without_a_full_record_is_built_from_its_window_with_caption_context(self):
 517 | +        import context_integrity as CI
 518 | +        ctx = E.Context(NOW, REG)
 519 | +        with tempfile.TemporaryDirectory() as d:
 520 | +            rel, wp, r, words = window_fixture(d)
 521 | +            far = dict(row("Bitcoin started as a quiet experiment.", start=100.0, end=104.0, mid="W2", vid="vidW"),
 522 | +                       transcript_sha256=r["transcript_sha256"])               # outside the window: it cannot anchor
 523 | +            ms, srcs, rep = LB.build_inputs([r, far], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 524 | +            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 525 | +            self.assertEqual(ms[0]["text"], SENTS_W[2])
 526 | +            self.assertEqual(list(rep["not_anchored"]), ["W2"])
 527 | +            self.assertEqual(rep["window_records"], {"vidW": rel})
 528 | +            src = srcs["vidW"]
 529 | +            self.assertEqual(src.context_source.transcript_method, "yt_auto")
 530 | +            text, win = CI._window_text(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 531 | +            t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
 532 | +            self.assertEqual(win[0], round(t0 - CI.CONTEXT_BEFORE_S, 3))
 533 | +            self.assertIn(f"caption line {int(t0 - 85) // 5 * 5} about money", text)   # the caption, 85 s before
 534 | +            self.assertIn("<selected>" + SENTS_W[2] + "</selected>", text)            # the window's own words
 535 | +            before, after = CI.context_around(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
 536 | +            self.assertIn("caption line", before)
 537 | +            self.assertIn("caption line", after)
 538 | +
 539 | +    def test_a_window_without_its_caption_record_has_no_context_and_fails_closed(self):
 540 | +        import context_integrity as CI
 541 | +        import package as PK
 542 | +        ctx = E.Context(NOW, REG)
 543 | +        with tempfile.TemporaryDirectory() as d:
 544 | +            rel, wp, r, words = window_fixture(d, caption=False)
 545 | +            ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
 546 | +            self.assertEqual(rep["no_caption_context"], {"vidW": "no record in the store matches the row's "
 547 | +                                                                  "transcript_sha256"})
 548 | +            m = ms[0]
 549 | +            self.assertEqual(CI._window_text(srcs["vidW"], m["sentences"][0], m["sentences"][1], *m["words"]),
 550 | +                             (None, None))                                 # step A: unavailable, never cleared
 551 | +            ex = PK.exclusion_for(None, m, srcs, {})                       # no model call is made
 552 | +            self.assertEqual((ex["verdict"], ex["measured"]), ("exclude", False))
 553 | +
 554 | +
 555 |  class TestDriverRefuses(unittest.TestCase):
 556 |      def test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one(self):
 557 |          """Audit 2315 C2 (grok, qwen, glm): no hard-coded delivered pins; a pin that cannot be read, has no clip or no
 558 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
It wires WINDOW word records into the ledger build path (orchestrator ruling 2, 22:40 ET Nov 12: "when [ingest ledger]
rows turn sentence-ready, build from the ledger and seal a pin; that is the first FRESH medley"). The integrator's
word-pass worker (branch word-pass, 514dd704) writes the window records.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- clips are verbatim WHOLE sentences of a sentence-ready, word-timed record (L-o 1, L-e);
- CONTEXT INTEGRITY (L-s): every clip is judged inside its source's transcript from >= 90 s before to >= 60 s after;
- no delivered span is used again (L-p).

The worker's contract, as built:
- A window record is transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json in the store: about +-45 s of words
  around one ledger moment, clipped to the video. It holds:
  - words on the YouTube clock;
  - segments from those words, plus transcript_sha256 (the segments sha);
  - words_sha256 = sha256(json.dumps([[word, start, end], ...], ensure_ascii=False));
  - punctuation.still_unpunctuated;
  - window = {start_s, end_s, clock: "youtube", offset_s}.
- A row in moments/word_pass.jsonl is {moment_id, video_id, window_record (relative to the store), record_sha256 (the
  file's sha256), sentence_ready, window, at}. It may also carry "reused"; a failed moment's row has an error and
  window_record null, and is never retried.
- L-s context for a window clip comes from the full-video CAPTION record the ledger mined the moment from (the
  contract): a window holds only +-45 s, and L-s needs 90 s / 60 s.

The files:
1. pipeline/ledger_build.py:
   - word_pass_index(): the last row per moment_id; only sentence_ready rows with a record count.
   - window_source(): every claim checked before use: the path is under transcripts/<vid>/windows/; the file sha256
     is the row's record_sha256; the method; the segments sha; words_sha256; the words spell the segments; the
     YouTube clock; nothing still unpunctuated; the ledger row's span inside the window; the channel;
     sentence_ready. file_head is True only when the window starts at 0.
   - caption_source(): the full-video record whose segments sha is the ledger row's transcript_sha256.
   - build_inputs(): a video with no full-video word record uses the best-ranked row's window record (one per video;
     the video's other rows re-anchor in it or are counted out), with .context_source = the caption record.
2. pipeline/context_integrity.py:
   - caption_parts(): for a window Source, the selection is the window's own words and the context is the caption's
     words by TIME (>= 90 s before, 60 s after, or to the media's edge), because auto captions carry no punctuation.
     No caption record, or a missing time, gives (None, None).
   - context_around(): the same for the exclusion verdict.
   - _window_text() routes window Sources through caption_parts.
3. pipeline/package.py exclusion_for(): takes its context from context_around(). With no context, it returns exclude
   with measured false.
4. tests/package/proof_ledger.py: passes the word-pass index (--word-pass).
5. tests/package/test_ledger_build.py: fixtures built exactly as the worker's make_record, plus tamper cases.

Check, concretely:
(a) Can a window record that is tampered with, or not sentence-ready, reach a moment (file, segments, words, clock,
    punctuation, path)?
(b) Can a window clip be judged for L-s with LESS than its 90 s / 60 s context, or pass when the context is missing?
(c) Is the caption record the one the ledger mined, and can a wrong one be used?
(d) Does anything change for the full-video records path (byte-identical contexts and exclusion prompts)?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".

