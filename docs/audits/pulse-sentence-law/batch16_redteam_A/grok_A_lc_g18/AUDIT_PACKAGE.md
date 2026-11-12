# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 22:39 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (525 lines)
```
   1 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
   2 | index 9dd31e3b..15657eff 100644
   3 | --- a/pipeline/sentence_law.py
   4 | +++ b/pipeline/sentence_law.py
   5 | @@ -88,7 +88,9 @@ class LawError(Exception):
   6 |  # ── text ──
   7 |  
   8 |  def tokens(text):
   9 | -    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower().replace("’", "'").replace("'", "")) if t]
  10 | +    """Words in the pipeline's one canonical form (pipeline/canon.py)."""
  11 | +    import canon
  12 | +    return canon.canon_tokens(text)
  13 |  
  14 |  
  15 |  def is_terminal(word):
  16 | @@ -144,7 +146,8 @@ class SourceAudio:
  17 |          live = d[d > DIGITAL_FLOOR_DBFS]
  18 |          if len(live) < 10:
  19 |              raise LawError(f"no audio in [{t0:.2f}, {t1:.2f}]")
  20 | -        speech = float(np.median(live[live > np.percentile(live, 30)]))
  21 | +        upper = live[live > np.percentile(live, 30)]
  22 | +        speech = float(np.median(upper if len(upper) else live))     # a flat envelope gives no NaN (GPT-cut F28)
  23 |          bed = float(np.percentile(live, 10))
  24 |          quiet = min(speech - VALLEY_BELOW_SPEECH_DB, max(speech - QUIET_BELOW_SPEECH_DB, bed + BED_PLUS_DB))
  25 |          return {"speech_db": round(speech, 1), "bed_db": round(bed, 1), "quiet_db": round(quiet, 1),
  26 | @@ -322,9 +325,11 @@ def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
  27 |      """Locate the editor's selected text in a word-timestamp transcript (text alignment, never time
  28 |      arithmetic; [t0, t1] only narrows the search). The span's first and last tokens must equal the
  29 |      selection's. Returns (i0, i1, ratio) or None."""
  30 | +    import canon                                      # one canonical form; a token keeps the word it starts in
  31 |      qt = tokens(text)
  32 | -    toks = [(t, wi) for wi, w in enumerate(words)
  33 | -            if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1) for t in tokens(w["word"])]
  34 | +    idx = [wi for wi, w in enumerate(words)
  35 | +           if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1)]
  36 | +    toks = [(t, idx[o]) for t, o in canon.canon_aligned([words[wi]["word"] for wi in idx])]
  37 |      seq = [t for t, _ in toks]
  38 |      if len(qt) < 3 or not seq:
  39 |          return None
  40 | @@ -345,8 +350,8 @@ def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
  41 |          return None
  42 |      r, s, e = best
  43 |      i0, i1 = toks[s][1], toks[e][1]
  44 | -    if tokens(words[i0]["word"])[0] != qt[0] or tokens(words[i1]["word"])[-1] != qt[-1]:
  45 | -        return None
  46 | +    if (s and toks[s - 1][1] == i0) or (e + 1 < len(toks) and toks[e + 1][1] == i1):
  47 | +        return None                    # a lock starts on its first word's first token and ends on its last word's last
  48 |      return i0, i1, round(r, 3)
  49 |  
  50 |  
  51 | @@ -473,14 +478,27 @@ def edge_fades(sa, plan, cut_in, cut_out):
  52 |      return round(fi, 3), round(fo, 3), wb
  53 |  
  54 |  
  55 | -def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa=None):
  56 | +def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa=None, offset_s=0.0,
  57 | +                       gain_invariant=False):
  58 |      """G17c (law L-b): the first and the last word of a prepared clip, with their natural decay, at full level:
  59 |      every 10 ms frame of the source over [first onset, + 0.3 s] and [last end - 0.3 s, last end] that is above
  60 |      the gap level next to the cut is matched in the clip within EDGE_WORD_MAX_DB (best alignment within +-2
  61 | -    hops absorbs the codec's delay). Returns (ok, detail)."""
  62 | +    hops absorbs the codec's delay). Every word frame must be compared (GPT-cut F07: an alignment that leaves a
  63 | +    word frame outside the clip is no proof; zero compared frames is never 'perfect').
  64 | +    offset_s: where the clip starts inside clip_path (0 for a prepared clip; the segment's start in a FINAL).
  65 | +    gain_invariant: the final's constant gain (amix + loudnorm) is measured on the clip's own interior speech
  66 | +    and removed before the 1 dB comparison (law L-c: the proof is made on the final's bytes). Returns (ok,
  67 | +    detail)."""
  68 |      sa = sa or SourceAudio(src_path)
  69 |      ca = SourceAudio(clip_path)
  70 |      wb = edge_word_bounds(sa, plan, cut_in, cut_out)
  71 | +    base = offset_s - cut_in + pad_s                                # source time -> clip_path time
  72 | +    gain = 0.0
  73 | +    if gain_invariant:
  74 | +        gain = _gain_db(sa, ca, cut_in, cut_out, base)
  75 | +        if gain is None:
  76 | +            return False, {side: {"ok": False, "why": "the final's gain is not measurable on the clip interior"}
  77 | +                           for side in ("in", "out")}
  78 |      det = {}
  79 |      for side, (a, b) in (("in", (wb["onset"], None)), ("out", (None, wb["end"]))):
  80 |          if (a if side == "in" else b) is None:
  81 | @@ -494,22 +512,92 @@ def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa
  82 |              continue
  83 |          best = None
  84 |          for k in range(-2, 3):
  85 | -            tc, dc = ca.sl(t0 - cut_in + pad_s + k * HOP_S, t1 - cut_in + pad_s + k * HOP_S)
  86 | +            tc, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
  87 |              n = min(len(dc), len(ds))
  88 | -            if n == 0:
  89 | +            if n == 0 or keep[n:].any():                             # a word frame left uncompared: no proof
  90 |                  continue
  91 | -            diff = np.abs(dc[:n] - ds[:n])[keep[:n]]
  92 | -            worst = float(np.max(diff)) if len(diff) else 0.0
  93 | +            diff = np.abs(dc[:n] - gain - ds[:n])[keep[:n]]
  94 | +            worst = float(np.max(diff))
  95 |              if best is None or worst < best[0]:
  96 |                  best = (worst, k)
  97 |          ok = best is not None and best[0] <= EDGE_WORD_MAX_DB
  98 |          det[side] = {"ok": ok, "span": [round(t0, 3), round(t1, 3)], "worst_db": None if best is None else round(best[0], 2),
  99 | -                     "shift_hops": None if best is None else best[1],
 100 | +                     "shift_hops": None if best is None else best[1], "compared_frames": int(keep.sum()),
 101 | +                     **({"gain_db": round(gain, 2)} if gain_invariant else {}),
 102 |                       "why": "edge word at full level" if ok else
 103 | -                     f"edge word up to {best[0] if best else float('nan'):.1f} dB off the source (max {EDGE_WORD_MAX_DB})"}
 104 | +                     "no alignment compares every frame of the edge word" if best is None else
 105 | +                     f"edge word up to {best[0]:.1f} dB off the source (max {EDGE_WORD_MAX_DB})"}
 106 |      return all(v["ok"] for v in det.values()), det
 107 |  
 108 |  
 109 | +GAIN_INTERIOR_MARGIN_S = 0.5    # law L-c: the final's gain is read away from both edges (fades, dissolves)
 110 | +SPAN_EDGE_S = 0.3               # span_matches: edges excluded (fades, dissolves)
 111 | +SPAN_MISMATCH_DB = 6.0          # a speech frame off the source by more than this is a mismatch
 112 | +SPAN_MISMATCH_RUN_S = 0.15      # this long a run of mismatching speech frames = the audio is not the source span
 113 | +
 114 | +
 115 | +def span_matches(src_path, final_path, cut_in, cut_out, offset_s, pad_s=0.0, sa=None):
 116 | +    """GPT-cut F05: the acoustic adjudication of a repeat-only G18 difference. The final's audio of a segment is
 117 | +    the source span itself: after the constant gain is removed (_gain_db) and the best of +-2 hops, no run of
 118 | +    SPAN_MISMATCH_RUN_S of consecutive speech frames differs from the source by more than SPAN_MISMATCH_DB (an
 119 | +    inserted or dropped word shifts everything after it). Edges (SPAN_EDGE_S) are excluded. (ok, detail)."""
 120 | +    sa = sa or SourceAudio(src_path)
 121 | +    ca = SourceAudio(final_path)
 122 | +    base = offset_s - cut_in + pad_s
 123 | +    gain = _gain_db(sa, ca, cut_in, cut_out, base)
 124 | +    if gain is None:
 125 | +        return False, {"why": "gain not measurable"}
 126 | +    t0, t1 = cut_in + SPAN_EDGE_S, cut_out - SPAN_EDGE_S
 127 | +    _, ds = sa.sl(t0, t1)
 128 | +    if len(ds) < 20:
 129 | +        return False, {"why": "span too short to compare"}
 130 | +    speech = ds > np.percentile(ds, 50)
 131 | +    best = None
 132 | +    for k in range(-2, 3):
 133 | +        _, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
 134 | +        if len(dc) < len(ds):
 135 | +            continue
 136 | +        bad = (np.abs(dc[:len(ds)] - gain - ds) > SPAN_MISMATCH_DB) & speech
 137 | +        run = longest = 0
 138 | +        for b in bad:
 139 | +            run = run + 1 if b else 0
 140 | +            longest = max(longest, run)
 141 | +        if best is None or longest < best[0]:
 142 | +            best = (longest, k, int(bad.sum()))
 143 | +    if best is None:
 144 | +        return False, {"why": "the final is shorter than the source span"}
 145 | +    ok = best[0] * HOP_S < SPAN_MISMATCH_RUN_S
 146 | +    return ok, {"gain_db": round(gain, 2), "shift_hops": best[1], "longest_mismatch_ms": int(round(best[0] * HOP_S * 1000)),
 147 | +                "mismatch_frames": best[2], "speech_frames": int(speech.sum())}
 148 | +
 149 | +
 150 | +
 151 | +
 152 | +def _gain_db(sa, ca, cut_in, cut_out, base):
 153 | +    """The constant gain (dB) between a source span and its rendered copy: the median level difference over the
 154 | +    span's interior speech frames (the louder half of the source), at the best of +-2 hops. None when the
 155 | +    interior has fewer than 20 speech frames or the difference is not steady (spread > 1 dB)."""
 156 | +    t0, t1 = cut_in + GAIN_INTERIOR_MARGIN_S, cut_out - GAIN_INTERIOR_MARGIN_S
 157 | +    if t1 - t0 < 0.5:
 158 | +        return None
 159 | +    _, ds = sa.sl(t0, t1)
 160 | +    if len(ds) < 20:
 161 | +        return None
 162 | +    speech = ds > np.percentile(ds, 50)
 163 | +    best = None
 164 | +    for k in range(-2, 3):
 165 | +        _, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
 166 | +        n = min(len(dc), len(ds))
 167 | +        m = speech[:n]
 168 | +        if n < len(ds) or m.sum() < 20:
 169 | +            continue
 170 | +        d = dc[:n][m] - ds[:n][m]
 171 | +        spread = float(np.percentile(d, 75) - np.percentile(d, 25))
 172 | +        if best is None or spread < best[1]:
 173 | +            best = (float(np.median(d)), spread)
 174 | +    return None if best is None or best[1] > 1.0 else best[0]
 175 | +
 176 | +
 177 |  def accepted_cut(src, plan, step=HOP_S, sa=None):
 178 |      """The cut nearest the plan's targets. Both edges clear of cut_accept: its unchanged acoustics check on the
 179 |      pair (20 / 30 ms fades). An edge only reachable at the envelope minimum (DEC-10 d) gets a 2-frame fade and
 180 | @@ -747,6 +835,39 @@ def gate_g17_edges(run_dir, source_path_fn=None):
 181 |      return ok_all, table
 182 |  
 183 |  
 184 | +def edges_on_final(final_path, segments, run_dir, source_path_fn=None):
 185 | +    """Law L-c as amended by the orchestrator (addendum 2026-11-11 '22:00', GPT-cut F03): the acoustic proof
 186 | +    that overrules a dissenting edge reading is G17c measured on the FINAL file being approved (its bytes, its
 187 | +    gain removed), never on the prepared clip. {label: {"in": detail, "out": detail}} for every talking head of
 188 | +    that final; a segment that cannot be measured has both sides ok False."""
 189 | +    with open(os.path.join(run_dir, "edl.json")) as f:
 190 | +        locks = {label: (seg.get("selection_lock"), seg["video_id"]) for label, seg in _segments(json.load(f))}
 191 | +    with open(os.path.join(run_dir, "cuts_final.json")) as f:
 192 | +        cuts = {c["clip_id"]: c for c in json.load(f)}
 193 | +    out = {}
 194 | +    for seg in segments:
 195 | +        if seg.get("type") != "talking_head":
 196 | +            continue
 197 | +        label = seg["label"]
 198 | +        (lock, vid), cut = locks.get(label, (None, None)), cuts.get(label)
 199 | +        if not lock or not cut:
 200 | +            out[label] = {s: {"ok": False, "why": "no lock / cut"} for s in ("in", "out")}
 201 | +            continue
 202 | +        try:
 203 | +            with open(os.path.join(run_dir, "transcripts", f"{vid}.json")) as f:
 204 | +                words = json.load(f)["words"]
 205 | +            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(vid)
 206 | +            sa = SourceAudio(src)
 207 | +            plan = edge_plan(sa, words, lock["i0"], lock["i1"])
 208 | +            _, det = edge_word_fidelity(src, final_path, plan, cut["cut_in"], cut["cut_out"],
 209 | +                                        float(cut.get("lead_in_pad_s") or 0), sa=sa, offset_s=float(seg["start"]),
 210 | +                                        gain_invariant=True)
 211 | +        except (LawError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
 212 | +            det = {s: {"ok": False, "why": f"not measurable: {type(e).__name__}: {e}"} for s in ("in", "out")}
 213 | +        out[label] = det
 214 | +    return out
 215 | +
 216 | +
 217 |  # ── G17 ONSET/TAIL INTEGRITY (rendered audio) ──
 218 |  
 219 |  def head_tail(sa):
 220 | diff --git a/pipeline/test_dec1_calibration.py b/pipeline/test_dec1_calibration.py
 221 | index 3c1ed3c3..b09c8982 100644
 222 | --- a/pipeline/test_dec1_calibration.py
 223 | +++ b/pipeline/test_dec1_calibration.py
 224 | @@ -143,17 +143,29 @@ class TestTailRows(unittest.TestCase):
 225 |      """Heimdall DEC-1 audit: G9_tail is the calibrated gate alone; a conform fallback (not the locked
 226 |      outro the floor was measured on) fails its own row, so the run still holds."""
 227 |  
 228 | +    def verdict(self, tail):
 229 | +        """run_fresh's verdict (release_auth's exact inventory) on an otherwise passing 16:9 row set."""
 230 | +        import run_fresh as rf
 231 | +        from test_release_auth import passing_rows
 232 | +        return rf.verdict_for({**passing_rows()["16x9"], **tail}, "16x9")[0]
 233 | +
 234 |      def test_luma_pass_on_a_fallback_outro_fails_outro_locked(self):
 235 | -        import run_fresh as rf          # verdict_for: run_fresh's existing verdict (HOLD on any FAIL row)
 236 | +        import run_fresh as rf
 237 |          self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
 238 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(True, True))[0], rf.VERDICT_HOLD)
 239 | +        self.assertEqual(self.verdict(rf.tail_rows(True, True)), rf.VERDICT_HOLD)
 240 | +
 241 | +    def test_an_outro_that_is_not_hash_identical_fails_outro_locked(self):
 242 | +        """GPT-cut F09: the identity was computed and then ignored; outro_locked now requires it."""
 243 | +        import run_fresh as rf
 244 | +        self.assertEqual(rf.tail_rows(True, False, identical=False), {"G9_tail": "PASS", "outro_locked": "FAIL"})
 245 | +        self.assertEqual(self.verdict(rf.tail_rows(True, False, identical=False)), rf.VERDICT_HOLD)
 246 |  
 247 |      def test_rows_follow_their_own_inputs(self):
 248 |          import run_fresh as rf
 249 |          self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})
 250 |          self.assertEqual(rf.tail_rows(False, False), {"G9_tail": "FAIL", "outro_locked": "PASS"})
 251 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(False, False))[0], rf.VERDICT_HOLD)   # luma fail holds
 252 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(True, False))[0], rf.VERDICT_CANDIDATE)
 253 | +        self.assertEqual(self.verdict(rf.tail_rows(False, False)), rf.VERDICT_HOLD)   # luma fail holds
 254 | +        self.assertEqual(self.verdict(rf.tail_rows(True, False)), rf.VERDICT_CANDIDATE)
 255 |  
 256 |  
 257 |  if __name__ == "__main__":
 258 | diff --git a/pipeline/test_fresh.py b/pipeline/test_fresh.py
 259 | index 199fb605..70b0a657 100644
 260 | --- a/pipeline/test_fresh.py
 261 | +++ b/pipeline/test_fresh.py
 262 | @@ -282,15 +282,17 @@ class TestClipContract(unittest.TestCase):
 263 |  
 264 |  class TestRunFreshRules(unittest.TestCase):
 265 |      def test_verdict_rules(self):
 266 | +        """Red-team 2026-11-11 A: the verdict is release_auth's exact inventory. The old prefix rules ('FLAG...',
 267 | +        'LIMITED...' and the '(run_gates)' placeholder passing) are gone: each of them now HOLDS."""
 268 |          from run_fresh import verdict_for, VERDICT_CANDIDATE, VERDICT_HOLD
 269 | -        ok_rows = {"G1_voice": "PASS", "G8_sharpness": "FLAG/LIMITED (x)",
 270 | -                   "G9_tail": "FLAG (APPROVED KNOWN EXCEPTION ...)",
 271 | -                   "G14_frame_similarity": "LIMITED (not valid)",
 272 | -                   "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below"}
 273 | -        self.assertEqual(verdict_for(ok_rows)[0], VERDICT_CANDIDATE)
 274 | -        for bad in ("FAIL", "HOLD(inconclusive)", "SKIPPED (no horiz_mp4)",
 275 | -                    "FAIL (fallback occurred)"):
 276 | -            self.assertEqual(verdict_for({**ok_rows, "Gx": bad})[0], VERDICT_HOLD, bad)
 277 | +        from test_release_auth import passing_rows
 278 | +        for fmt in ("16x9", "9x16"):
 279 | +            self.assertEqual(verdict_for(passing_rows()[fmt], fmt)[0], VERDICT_CANDIDATE, fmt)
 280 | +        for row, bad in (("G8_sharpness", "FLAG/LIMITED (x)"), ("G9_tail", "FLAG (APPROVED KNOWN EXCEPTION ...)"),
 281 | +                         ("G18_word_for_word", "FAIL"), ("G16_sentence_boundary", "HOLD(inconclusive)"),
 282 | +                         ("G20_signoff_names_all", "SKIPPED (no horiz_mp4)"), ("G11_parity(run_gates)", "NOT RUN BY run_gates")):
 283 | +            rows = {**passing_rows()["9x16"], row: bad}
 284 | +            self.assertEqual(verdict_for(rows, "9x16")[0], VERDICT_HOLD, (row, bad))
 285 |  
 286 |      def test_no_publishing_path(self):
 287 |          src = open(os.path.join(PIPELINE, "run_fresh.py")).read()
 288 | diff --git a/pipeline/test_word_diff.py b/pipeline/test_word_diff.py
 289 | index 90c0c055..ffe52663 100644
 290 | --- a/pipeline/test_word_diff.py
 291 | +++ b/pipeline/test_word_diff.py
 292 | @@ -27,10 +27,27 @@ class TestCanonical(unittest.TestCase):
 293 |                       ("U .S. Bitcoin ETFs had about $1 .3 billion", "US Bitcoin ETFs had about one point three billion dollars"),
 294 |                       ("around $74 000, around the 50 weekly MA", "around seventy four thousand dollars around the fifty weekly MA"),
 295 |                       ("241 House winners and 50 senators", "two hundred forty one house winners and fifty senators"),
 296 | -                     ("up still 25 % off the lows", "up still twenty five percent off the lows"),
 297 | -                     ("days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped")):
 298 | +                     ("up still 25 % off the lows", "up still twenty five percent off the lows")):
 299 |              self.assertEqual(W.diff(a, b), [], (a, b))
 300 |  
 301 | +    def test_a_repeat_only_difference_is_kept_as_evidence(self):
 302 | +        """GPT-cut F05: a disfluent repeat rendered differently is NOT removed from the comparison; it is a
 303 | +        repeat-only difference (gone with collapse=True) that gate_g18 decides by the audio (span_matches)."""
 304 | +        a, b = "days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped"
 305 | +        self.assertNotEqual(W.diff(a, b), [])
 306 | +        self.assertEqual(W.diff(a, b, collapse=True), [])
 307 | +        self.assertNotEqual(W.diff("bitcoin is falling", "bitcoin is falling bitcoin is falling"), [])
 308 | +
 309 | +    def test_units_and_signs_are_not_erased(self):
 310 | +        """GPT-cut F04: five percent vs five dollars, -5% vs +5%, $5 vs 5% differ; only a '$' formatting
 311 | +        difference (whisper writes '$74,000' for a spoken 'seventy-four thousand') is tolerated."""
 312 | +        for a, b in (("bitcoin fell five percent today", "bitcoin fell five dollars today"),
 313 | +                     ("it moved -5% on the day", "it moved +5% on the day"),
 314 | +                     ("it costs $5", "it costs 5%")):
 315 | +            self.assertNotEqual(W.diff(a, b), [], (a, b))
 316 | +        self.assertEqual(W.diff("around $74,000 today", "around 74 000 today"), [])
 317 | +        self.assertEqual(W.diff("it fell -5%", "it fell minus five percent"), [])
 318 | +
 319 |      def test_a_half_written_or_spoken_is_the_same_number(self):
 320 |          """Recut run 6 G18 clip_02: the final was heard as 'five and a half percent', the source span as
 321 |          '5 .5%' (the same audio). Equal both ways; any real difference in the number still counts."""
 322 | @@ -49,9 +66,10 @@ class TestCanonical(unittest.TestCase):
 323 |          d = W.diff("It went from above $81,000 after the election. That was the week.",
 324 |                     "81,000 after the election. That was the week. All right, you've probably seen")
 325 |          self.assertIn(("delete", "it went from above", ""), d)
 326 | -        self.assertIn(("insert", "", "all right you've probably seen"), d)
 327 | +        self.assertIn(("insert", "", "all right you've probably seen"), d)   # canon keeps apostrophes (M1)
 328 |          self.assertEqual(W.diff("the market fell", "the market rose"), [("replace", "fell", "rose")])
 329 | -        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "sharply")])
 330 | +        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "fell sharply")])
 331 | +        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply", collapse=True), [("insert", "", "sharply")])
 332 |  
 333 |      def test_edges_compare_the_first_and_last_two_words(self):
 334 |          self.assertEqual(W.edges("But I don't check it. Many times.", "but i don't check it many times"), [])
 335 | @@ -60,6 +78,51 @@ class TestCanonical(unittest.TestCase):
 336 |                           [("start", "it went", "above 81000"), ("end", "last week", "people celebrating")])
 337 |  
 338 |  
 339 | +class TestSpanMatches(unittest.TestCase):
 340 | +    """span_matches (sentence_law): the final's segment IS the source span when, gain removed, no 150 ms run of
 341 | +    speech frames differs by more than 6 dB. Synthetic speech-like bursts; must-pass: the same span with a gain,
 342 | +    a quiet bed and a codec round trip; must-fail: the same span with 300 ms of it repeated (a concat defect)."""
 343 | +
 344 | +    @classmethod
 345 | +    def setUpClass(cls):
 346 | +        import numpy as np
 347 | +        import subprocess
 348 | +        cls.tmp = tempfile.mkdtemp(prefix="span_")
 349 | +        sr, rng = 16000, np.random.default_rng(7)
 350 | +        t = np.arange(int(sr * 6.0)) / sr
 351 | +        env = np.zeros_like(t)
 352 | +        k = 0.2
 353 | +        while k < 5.8:                                       # syllable-like bursts of varying length and level
 354 | +            d = rng.uniform(0.08, 0.25)
 355 | +            env[(t >= k) & (t < k + d)] = rng.uniform(0.2, 0.9)
 356 | +            k += d + rng.uniform(0.05, 0.2)
 357 | +        src = env * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
 358 | +        bed = 0.003 * rng.standard_normal(len(t))
 359 | +
 360 | +        def wav(name, x):
 361 | +            path = os.path.join(cls.tmp, name)
 362 | +            raw = path + ".f32"
 363 | +            x.astype(np.float32).tofile(raw)
 364 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw,
 365 | +                            "-c:a", "aac", "-b:a", "192k", path], check=True)
 366 | +            return path
 367 | +        cls.src = wav("src.m4a", src)
 368 | +        cls.same = wav("same.m4a", 0.5 * src + bed)                              # gain + bed + codec
 369 | +        rep = np.concatenate([src[:int(sr * 3.0)], src[int(sr * 2.7):int(sr * 3.0)], src[int(sr * 3.0):]])[:len(src)]
 370 | +        cls.repeat = wav("repeat.m4a", 0.5 * rep + bed)                          # 300 ms repeated at 3.0 s
 371 | +
 372 | +    @classmethod
 373 | +    def tearDownClass(cls):
 374 | +        shutil.rmtree(cls.tmp, ignore_errors=True)
 375 | +
 376 | +    def test_the_same_span_matches_and_a_repeat_does_not(self):
 377 | +        import sentence_law as L
 378 | +        ok, det = L.span_matches(self.src, self.same, 0.0, 5.9, 0.0)
 379 | +        self.assertTrue(ok, det)
 380 | +        ok, det = L.span_matches(self.src, self.repeat, 0.0, 5.9, 0.0)
 381 | +        self.assertFalse(ok, det)
 382 | +
 383 | +
 384 |  def _clips():
 385 |      """Yesterday's three clips: the editor's sentences locked on today's transcripts (as the G16 fixture),
 386 |      and the source span each was cut from."""
 387 | diff --git a/pipeline/word_diff.py b/pipeline/word_diff.py
 388 | index dad11755..386cb7a0 100644
 389 | --- a/pipeline/word_diff.py
 390 | +++ b/pipeline/word_diff.py
 391 | @@ -23,91 +23,17 @@ import tempfile
 392 |  ASR = {"model": "large-v3", "language": "en", "beam_size": 5, "word_timestamps": True, "vad_filter": False}
 393 |  EDGE_WORDS = 2
 394 |  
 395 | -_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
 396 | -                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
 397 | -_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
 398 | -_SCALES = {"hundred": 100, "thousand": 1000}   # whisper writes '74,000' but keeps '1.3 billion' as words
 399 | -_AFTER_NUMBER = {"dollars", "dollar", "percent", "per", "cent"}
 400 | -
 401 | -
 402 | -def _spelled_numbers(tokens):
 403 | -    """'seventy four thousand' -> '74000', 'one hundred and twenty' -> '120'. Only a well-formed phrase is
 404 | -    joined: a unit after a unit or after a teen ('one two', 'eleven three') starts a new number, so a
 405 | -    count like 'one two three' stays three tokens (Heimdall: additive joining hid differences)."""
 406 | -    out, i = [], 0
 407 | -    while i < len(tokens):
 408 | -        if tokens[i] in _UNITS or tokens[i] in _TENS:
 409 | -            total, cur, j, last = 0, 0, i, None
 410 | -            while j < len(tokens):
 411 | -                t = tokens[j]
 412 | -                if t in _UNITS:
 413 | -                    if last in ("unit",) or (last == "tens" and _UNITS[t] >= 10):
 414 | -                        break
 415 | -                    cur += _UNITS[t]
 416 | -                    last = "unit"
 417 | -                elif t in _TENS:
 418 | -                    if last in ("unit", "tens"):
 419 | -                        break
 420 | -                    cur += _TENS[t]
 421 | -                    last = "tens"
 422 | -                elif t == "hundred" and last in ("unit",):
 423 | -                    cur *= 100
 424 | -                    last = "hundred"
 425 | -                elif t in _SCALES and t != "hundred" and last is not None:
 426 | -                    total += max(cur, 1) * _SCALES[t]
 427 | -                    cur, last = 0, "scale"
 428 | -                elif (t == "and" and last in ("hundred", "scale") and j + 1 < len(tokens)
 429 | -                      and (tokens[j + 1] in _UNITS or tokens[j + 1] in _TENS)):
 430 | -                    last = "and"
 431 | -                else:
 432 | -                    break
 433 | -                j += 1
 434 | -            out.append(str(total + cur))
 435 | -            i = j
 436 | -        else:
 437 | -            out.append(tokens[i])
 438 | -            i += 1
 439 | -    return out
 440 | -
 441 | -
 442 | -_NUM = re.compile(r"\d+(p\d+)?")
 443 | -
 444 | -
 445 | -def _decimals(tokens):
 446 | -    """Spoken decimals as the written form's single token: 'one point three' -> '1p3' (like '1.3'), and
 447 | -    'five and a half' -> '5p5' (like '5.5'; recut run 6 G18: '5 .5%' vs 'five and a half percent', the same
 448 | -    audio). Only after a number: 'a year and a half' stays words. Before 2026-11-11 a decimal split into
 449 | -    two digit tokens and the repeat-collapser then merged '5 5' into '5', so 5.5 % and 5 % compared equal."""
 450 | -    out, k = [], 0
 451 | -    while k < len(tokens):
 452 | -        w = tokens[k]
 453 | -        if w.isdigit() and tokens[k + 1:k + 2] == ["point"] and k + 2 < len(tokens) and tokens[k + 2].isdigit():
 454 | -            out.append(f"{w}p{tokens[k + 2]}")
 455 | -            k += 3
 456 | -        elif w.isdigit() and tokens[k + 1:k + 4] == ["and", "a", "half"]:
 457 | -            out.append(f"{w}p5")
 458 | -            k += 4
 459 | -        else:
 460 | -            out.append(w)
 461 | -            k += 1
 462 | -    return out
 463 | -
 464 | -
 465 | -def norm(text):
 466 | -    t = (text or "").lower().replace("’", "'")
 467 | -    t = re.sub(r"(\d)\s+([.,]\d)", r"\1\2", t)            # '88 ,000' -> '88,000', '1 .3' -> '1.3'
 468 | -    t = re.sub(r"(\d)\s+(?=\d{3}\b)", r"\1", t)             # '74 000' -> '74000'
 469 | -    t = re.sub(r"\$\s+(\d)", r"$\1", t)
 470 | -    t = re.sub(r"\b(\w)\s+\.(?=\w)", r"\1.", t)              # 'u .s.' -> 'u.s.'
 471 | -    t = re.sub(r"\b([a-z])\.(?=[a-z]\b)", r"\1", t)            # 'u.s.' -> 'us.' (single-letter abbreviations)
 472 | -    t = re.sub(r"(?<=\d)[,](?=\d{3}\b)", "", t)             # '74,000' -> '74000'
 473 | -    t = re.sub(r"(?<=\d)\.(?=\d)", "p", t)                   # '5.5' -> '5p5': a decimal stays ONE token
 474 | -    t = re.sub(r"[^\w\s']", " ", t)                         # punctuation, '$', '%' (both sides alike)
 475 | -    t = re.sub(r"(?<!\w)'|'(?!\w)", "", t)                  # quote marks, not apostrophes
 476 | -    tokens = _decimals(_spelled_numbers(t.split()))          # 'one point three' / 'five and a half' -> '1p3' / '5p5'
 477 | -    tokens = [w for k, w in enumerate(tokens) if not (w in _AFTER_NUMBER and k and (
 478 | -        _NUM.fullmatch(tokens[k - 1]) or tokens[k - 1] in ("million", "billion", "trillion")))]
 479 | -    return _collapse_repeats(tokens)
 480 | +def norm(text, collapse=False):
 481 | +    """G18's comparison form: the pipeline's one canonical form (pipeline/canon.py: case, punctuation, split number
 482 | +    fragments, spelled numbers, decimals, currency / percent, signs), then G18's one tolerance, both sides alike:
 483 | +    'dollars' right after a number is dropped (whisper writes '$74,000' for a spoken 'seventy-four thousand';
 484 | +    '5 percent' vs '5 dollars' still differ: GPT-cut F04). collapse=True also folds immediate repeats of 1-3
 485 | +    words ('of course of course'); a difference that only that removes is NOT dropped from the evidence: G18
 486 | +    adjudicates it acoustically (GPT-cut F05, gate_g18)."""
 487 | +    import canon
 488 | +    t = canon.canon_tokens(text)
 489 | +    t = [w for k, w in enumerate(t) if not (w == "dollars" and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1]))]
 490 | +    return _collapse_repeats(t) if collapse else t
 491 |  
 492 |  
 493 |  def _collapse_repeats(tokens):
 494 | @@ -121,9 +47,9 @@ def _collapse_repeats(tokens):
 495 |      return out
 496 |  
 497 |  
 498 | -def diff(expected, heard):
 499 | +def diff(expected, heard, collapse=False):
 500 |      """Word-level differences [(op, expected_words, heard_words)] after canonicalisation; [] if equal."""
 501 | -    e, h = norm(expected), norm(heard)
 502 | +    e, h = norm(expected, collapse), norm(heard, collapse)
 503 |      out = []
 504 |      for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes():
 505 |          if op != "equal":
 506 | @@ -180,6 +106,18 @@ def gate_g18(final_path, segments, clips, transcriber=None):
 507 |          row = {"segment": label, "heard": heard, "source_span_heard": src, "lock_text": c["lock_text"],
 508 |                 "edges": edges(c["lock_text"], heard), "identity": diff(src, heard),
 509 |                 "lock_diff_reported": diff(c["lock_text"], heard)}
 510 | +        if row["identity"] and not diff(src, heard, collapse=True):
 511 | +            # only repeats differ (two whisper passes render a disfluent repeat differently, Nov 10 fixture): the
 512 | +            # difference stays in the row and is decided by the audio: the final's segment must BE the source span
 513 | +            import sentence_law as L
 514 | +            try:
 515 | +                same, det = L.span_matches(c["source"], final_path, c["cut_in"], c["cut_out"], float(seg["start"]),
 516 | +                                           float(c.get("pad_s") or 0.0))
 517 | +            except Exception as e:                   # not measurable: the difference stands
 518 | +                same, det = False, {"why": f"{type(e).__name__}: {e}"}
 519 | +            row["repeat_only_adjudication"] = {"same_audio": same, **det}
 520 | +            if same:
 521 | +                row["identity_repeats_only"], row["identity"] = row["identity"], []
 522 |          row["pass"] = not row["edges"] and not row["identity"]
 523 |          ok_all &= row["pass"]
 524 |          rows.append(row)
 525 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

