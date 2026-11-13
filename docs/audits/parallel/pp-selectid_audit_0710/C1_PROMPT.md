# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0710
# Branch: pp-selectid
# Generated: 2026-11-13 06:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0710/C1_STEP.diff (493 lines)
```
   1 | diff --git a/pipeline/hook_onset.py b/pipeline/hook_onset.py
   2 | index b5cc7c4..2faa5d1 100644
   3 | --- a/pipeline/hook_onset.py
   4 | +++ b/pipeline/hook_onset.py
   5 | @@ -20,6 +20,14 @@ applied, which can only make this check stricter.
   6 |  
   7 |  measure(...) -> {"pass", "measured", "lead_ms", "cut_in", "pad_s", "why"}. Not measured (no audio, no plan) is never
   8 |  a pass (law L-m).
   9 | +
  10 | +RULING 33 PART 2 (a trimmed moment: ONE leading but/and/so/well/now/yeah left out; item 42): the render plans the IN
  11 | +edge at the measured pause AFTER the trimmed word (sentence_law.trimmed_boundary, edge_plan(trimmed=...)), takes
  12 | +accepted_cut's cut and fade, and holds the clip unless the audio as cut opens in quiet (sentence_law.trimmed_onset:
  13 | +the first onset after the first 10 ms hop). measure(..., trimmed=word) plans and measures exactly that on the L-v 2
  14 | +window, with this slice's one-frame margin, in "trim" ({"pass", "measured", "why", ...}): ruling 33 (a), at any
  15 | +place. "pass" (may it OPEN a medley?) then also needs "trim". The render's functions are copied verbatim from its
  16 | +sentence_law.py at c6605895.
  17 |  """
  18 |  import sentence_law as SL
  19 |  import transcript_truth as TT
  20 | @@ -35,10 +43,41 @@ class _Slice(SL.SourceAudio):
  21 |          self.path, self.t, self.db, self.dur = sa.path, sa.t[m] - t0, sa.db[m], max(0.0, t1 - t0)
  22 |  
  23 |  
  24 | -def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  25 | +def trim_onset(sa, plan, a):
  26 | +    """Ruling 33 (a) as the render measures it at its cut table (write_lock_cut_table): accepted_cut's cut and fade,
  27 | +    then trimmed_onset on the audio as cut. Here on the L-v 2 window (sa.path), so the onset must lie one more 10 ms
  28 | +    frame after the cut than the render's rule asks (the slice vs the render's own decode, as for the hook's lead).
  29 | +    a: the window's start (video seconds). -> {"pass", "measured", "why", "onset_s", "cut_in", "fade_in_ms"}."""
  30 | +    try:
  31 | +        pick = SL.accepted_cut(sa.path, plan, sa=sa)
  32 | +        if pick is None:
  33 | +            return {"pass": False, "measured": True, "why": "no cut keeps the neighbour words inaudible (the render's "
  34 | +                                                                "accepted_cut finds none: it holds the clip)"}
  35 | +        _, r = SL.trimmed_onset(sa.path, pick["cut_in"], pick["fade_in_ms"])
  36 | +    except Exception as e:                               # no audio, no plan for an edge: never a pass (law L-m)
  37 | +        return {"pass": False, "measured": False, "why": f"not measured: {type(e).__name__}: {str(e)[:120]}"}
  38 | +    need = SL.HOP_S + MARGIN_MS / 1000
  39 | +    on = r.get("onset_s")
  40 | +    ok = on is not None and on > need + 1e-9
  41 | +    return {"pass": ok, "measured": True, "onset_s": on, "lead_ms": r.get("lead_ms"),
  42 | +            "cut_in": round(a + pick["cut_in"], 3), "fade_in_ms": pick["fade_in_ms"],
  43 | +            "why": "ok" if ok else f"the audio as cut opens on sound: first onset {on} s, not after {need:.2f} s (the "
  44 | +                                   f"render's first 10 ms hop + one {MARGIN_MS} ms frame)"}
  45 | +
  46 | +
  47 | +def measure(src, w0, w1, video_id, start, end, work_dir, audio=None, trimmed=None):
  48 |      """The hook moment's planned prepared clip: does it keep >= HEAD_LEAD_MIN_S of genuine quiet before its first
  49 |      onset? src: the moment's eligibility Source; w0 / w1: its first / last word indices in src.tokens; start / end:
  50 | -    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window."""
  51 | +    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window.
  52 | +    trimmed: the moment's trimmed_leading (ruling 33 part 2): the IN edge is planned after that word, and ruling
  53 | +    33 (a) is measured in "trim"; the record then carries "trim" on every path."""
  54 | +    rec = _measure(src, w0, w1, video_id, start, end, work_dir, audio, trimmed)
  55 | +    if trimmed and "trim" not in rec:                   # no plan was reached: the trimmed cut is not measured either
  56 | +        rec["trim"] = {"pass": False, "measured": rec.get("measured", False), "why": rec.get("why")}
  57 | +    return rec
  58 | +
  59 | +
  60 | +def _measure(src, w0, w1, video_id, start, end, work_dir, audio, trimmed):
  61 |      need = SL.HEAD_LEAD_MIN_S * 1000 + MARGIN_MS
  62 |      try:
  63 |          if audio is None:
  64 | @@ -56,13 +95,14 @@ def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  65 |      words = [{"word": toks[i]["word"], "start": float(toks[i]["start"]) - a, "end": float(toks[i]["end"]) - a}
  66 |               for i in idx]
  67 |      i0, i1 = idx.index(w0), idx.index(w1)
  68 | -    try:
  69 | -        plan = SL.edge_plan(sa, words, i0, i1)
  70 | +    try:                                                 # ruling 33 part 2: the render's planning of a trimmed IN edge
  71 | +        plan = SL.edge_plan(sa, words, i0, i1, trimmed={"word": trimmed} if trimmed else None)
  72 |      except Exception as e:                               # LawError: no audio to read levels from, and the like
  73 |          return {"pass": False, "measured": False, "why": f"no cut plan: {type(e).__name__}: {str(e)[:120]}"}
  74 |      cin = plan.get("in") or {}
  75 |      if not cin.get("cuttable"):
  76 | -        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut before the hook: "
  77 | +        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut "
  78 | +                f"{'after the trimmed word ' + repr(trimmed) if trimmed else 'before the hook'}: "
  79 |                  f"{cin.get('reason') or 'not cuttable'}"}
  80 |      cut_in = float(cin["cut"])
  81 |      out = plan.get("out") or {}
  82 | @@ -74,6 +114,12 @@ def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  83 |      pad = float(cin.get("lead_in_pad_s") or 0.0)         # a room-tone pad: edge_plan allows one only at a file head
  84 |      lead = int(round(ht["lead_ms"] + pad * 1000))
  85 |      ok = lead >= need
  86 | -    return {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  87 | -            "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
  88 | -                                    f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
  89 | +    rec = {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  90 | +           "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
  91 | +                                   f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
  92 | +    if trimmed:                                          # ruling 33 (a): the trimmed cut opens in quiet, any place
  93 | +        rec["trim"] = trim_onset(sa, plan, a)
  94 | +        if rec["trim"]["pass"] is not True:
  95 | +            rec.update(passed_lead=ok, why=f"the trimmed cut: {rec['trim']['why']}")
  96 | +            rec["pass"] = False
  97 | +    return rec
  98 | diff --git a/pipeline/package.py b/pipeline/package.py
  99 | index d266dbe..e5bd87a 100644
 100 | --- a/pipeline/package.py
 101 | +++ b/pipeline/package.py
 102 | @@ -1137,7 +1137,8 @@ def hook_onset_for(m, sources, work_dir, cache):
 103 |          import hook_onset as HO
 104 |          try:
 105 |              cache[m["moment_id"]] = HO.measure(src_of(m, sources), m["words"][0], m["words"][1], m["video_id"],
 106 | -                                               float(m["start"]), float(m["end"]), work_dir)
 107 | +                                               float(m["start"]), float(m["end"]), work_dir,
 108 | +                                               trimmed=m.get("trimmed_leading"))     # ruling 33 part 2 (item 42)
 109 |          except Exception as e:
 110 |              cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 111 |      return cache[m["moment_id"]]
 112 | @@ -1216,7 +1217,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 113 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 114 |             "package": None}
 115 |      log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
 116 | -        f"would have to affirm, or no place under the topic rule with the pin's screen), {len(ad_read)} on an ad-read "
 117 | +        f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 118 | +        f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 119 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 120 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 121 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 122 | @@ -1245,9 +1247,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 123 |      out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 124 |                                        ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 125 |                                        str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 126 | -    trim_cut = {mid: out["prescreen"]["hook_onset"][mid] for mid, m in cleared.items()     # ruling 33 (a): the
 127 | -                if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}    # acoustic onset rule on the
 128 | -    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}                 # trimmed cut, any place
 129 | +    trim_cut = {mid: ("NOT MEASURED: " if not t.get("measured") else "FAIL: ") + str(t.get("why"))   # ruling 33 (a):
 130 | +                for mid, m in cleared.items() if m.get("trimmed_leading")        # the trimmed cut as the render plans
 131 | +                for t in [m["hook_onset"].get("trim") or {"measured": False, "why": "no trimmed-cut record"}]   # it
 132 | +                if t.get("pass") is not True}                                    # opens in quiet, at ANY place; the
 133 | +    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}     # hook lead decides only the hook
 134 |      out["prescreen"]["trim_cut"] = trim_cut
 135 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 136 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
 137 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 138 | index b283500..708c64a 100644
 139 | --- a/pipeline/sentence_law.py
 140 | +++ b/pipeline/sentence_law.py
 141 | @@ -79,6 +79,7 @@ PUNCT_WINDOW_WORDS = 60
 142 |  WORD_DURATION_RATIO_MIN = 0.85  # G17: rendered edge word keeps >= 85 % of its duration
 143 |  _TERMINAL = (".", "!", "?")
 144 |  _ABBREV = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "jr", "sr", "inc", "ltd", "corp", "prof", "approx"}
 145 | +TRIMMABLE_LEADING = frozenset({"but", "and", "so", "well", "now", "yeah"})   # ruling 33 part 2 (orchestrator '03:42')
 146 |  
 147 |  
 148 |  class LawError(Exception):
 149 | @@ -287,9 +288,47 @@ def boundary(sa, words, k):
 150 |      return {**rec, "valid": True}
 151 |  
 152 |  
 153 | -def edge_plan(sa, words, i0, i1):
 154 | -    """Boundaries around words[i0..i1] and the legal cut ranges they allow."""
 155 | -    bin_ = boundary(sa, words, i0 - 1)
 156 | +def trimmed_boundary(sa, words, i0, trimmed):
 157 | +    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a lock may leave out ONE leading word (TRIMMABLE_LEADING) of a
 158 | +    whole sentence, recorded as lock['trimmed_leading']. Its IN edge is then the MEASURED PAUSE after that word, not a
 159 | +    sentence boundary: (1) words[i0 - 1] is the trimmed word; (2) the untrimmed sentence starts a sentence (the word
 160 | +    before it ends one in a punctuated stretch, or it is the transcript's first word): everything else about whole
 161 | +    sentences is unchanged; (3) a quiet run lies between the trimmed word and the first kept word, with a heard gap.
 162 | +    Otherwise invalid: the word cannot be cut cleanly (no pause, co-articulated) and the clip is held."""
 163 | +    import canon
 164 | +    k, word = i0 - 1, str((trimmed or {}).get("word") or "")
 165 | +    rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>", "before_word": words[i0]["word"],
 166 | +           "trimmed_leading": word, "lexical": "trimmed leading word (ruling 33 part 2)"}
 167 | +    tok = canon.canon_tokens(word)
 168 | +    if k < 0 or len(tok) != 1 or tok[0] not in TRIMMABLE_LEADING or canon.canon_tokens(words[k]["word"]) != tok:
 169 | +        return {**rec, "valid": False, "reason": f"the trimmed word {word!r} is not one of "
 170 | +                f"{'/'.join(sorted(TRIMMABLE_LEADING))} or not the word before the lock ({rec['after_word']!r})"}
 171 | +    if k > 0 and not (is_punctuated(words, k - 1) and is_terminal(words[k - 1]["word"])):
 172 | +        return {**rec, "valid": False, "reason": f"the untrimmed sentence does not start a sentence: "
 173 | +                f"{words[k - 1]['word']!r} before {word!r} does not end one"}
 174 | +    mid = lambda w: (w["start"] + w["end"]) / 2
 175 | +    quiet, lv = find_pause(sa, mid(words[k]), mid(words[i0]))
 176 | +    point, gap, pause = boundary_geometry(sa, words, k, lv, quiet)
 177 | +    rec.update(levels=lv, pause=pause, quiet_run=quiet, point=point, word_gap=gap)
 178 | +    if quiet is None or gap["end"] <= gap["start"]:
 179 | +        return {**rec, "valid": False, "reason": f"the trimmed word {word!r} cannot be cut cleanly: no measured pause "
 180 | +                f"between it and {words[i0]['word']!r} (co-articulated)"}
 181 | +    return {**rec, "valid": True}
 182 | +
 183 | +
 184 | +def trimmed_onset(src, cut_in, fade_in_ms):
 185 | +    """Ruling 33 part 2, the onset rule on the audio as cut: G17a's own measure (head_tail on the cut audio with the
 186 | +    clip's fade-in, hook_lead_at) finds quiet before the first sound (the first onset after the first 10 ms hop, the
 187 | +    criterion ruling 28 uses for 'quiet after the cut'): nothing of the trimmed word opens the clip. (ok, record)."""
 188 | +    lead, onset = hook_lead_at(src, cut_in, fade_in_ms)
 189 | +    ok = onset is not None and onset > HOP_S + 1e-9
 190 | +    return ok, {"cut_in": cut_in, "fade_in_ms": fade_in_ms, "onset_s": onset, "lead_ms": lead, "ok": ok}
 191 | +
 192 | +
 193 | +def edge_plan(sa, words, i0, i1, trimmed=None):
 194 | +    """Boundaries around words[i0..i1] and the legal cut ranges they allow. trimmed: the lock's trimmed_leading
 195 | +    (ruling 33 part 2): the IN edge is the measured pause after that word, and the cut must SIT in its quiet run."""
 196 | +    bin_ = trimmed_boundary(sa, words, i0, trimmed) if trimmed else boundary(sa, words, i0 - 1)
 197 |      bout = boundary(sa, words, i1)
 198 |      plan = {"in": bin_, "out": bout}
 199 |      if bin_["valid"]:
 200 | @@ -301,11 +340,14 @@ def edge_plan(sa, words, i0, i1):
 201 |              bin_.update(cut_lo=0.0, cut_hi=p["start"], cut=p["start"], lead_in_pad_s=pad, cuttable=True)
 202 |          else:                                             # DEC-10: anywhere in the heard gap; aim at the pause
 203 |              g = bin_.get("word_gap") or {"start": p["start"], "end": p["end"]}
 204 | -            hi = round(g["end"] - LEAD_MIN_S, 3)
 205 | +            lo, hi = g["start"], round(g["end"] - LEAD_MIN_S, 3)
 206 | +            if trimmed:                                   # ruling 33 part 2: inside the measured quiet run as well
 207 | +                q = bin_["quiet_run"]
 208 | +                lo, hi = max(lo, q["start"]), min(hi, round(q["end"] - LEAD_MIN_S, 3))
 209 |              target = max(p["start"], p["end"] - LEAD_TARGET_S) if p.get("ms", 0) > 0 else bin_.get("point", p["start"])
 210 | -            bin_.update(cut_lo=g["start"], cut_hi=hi, cuttable=hi >= g["start"] - 1e-9,
 211 | -                        cut=round(min(max(target, g["start"]), hi), 3), lead_in_pad_s=0.0,
 212 | -                        reason=None if hi >= g["start"] - 1e-9 else "no room before the first word")
 213 | +            bin_.update(cut_lo=lo, cut_hi=hi, cuttable=hi >= lo - 1e-9,
 214 | +                        cut=round(min(max(target, lo), hi), 3), lead_in_pad_s=0.0,
 215 | +                        reason=None if hi >= lo - 1e-9 else "no room before the first word")
 216 |      if bout["valid"]:
 217 |          p = bout["pause"]
 218 |          guard = 0.0 if bout.get("file_end") else GUARD_S
 219 | @@ -667,6 +709,37 @@ def _accepted_cut_pair(src, plan, step=HOP_S):
 220 |      return (c["cut_in"], c["cut_out"]) if c else None
 221 |  
 222 |  
 223 | +def _cut_head(src, c, fade_ms):
 224 | +    """LEVEL_WINDOW_S of `src` from `c`, stereo 48 kHz float, with the clip's own linear fade-in of `fade_ms` applied
 225 | +    as prepare applies it (audit batch 56 C1, qwen: measure what the prepared clip will hold)."""
 226 | +    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{c:.3f}", "-i", src, "-t", f"{LEVEL_WINDOW_S}", "-vn", "-ac",
 227 | +                        "2", "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True, timeout=60)
 228 | +    x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64).copy()
 229 | +    k = min(len(x), int(round(fade_ms / 1000 * 48000)))
 230 | +    if k > 0:
 231 | +        x[:k] *= np.linspace(0.0, 1.0, k)[:, None]
 232 | +    return x
 233 | +
 234 | +
 235 | +def _head_tail_of(x):
 236 | +    import tempfile
 237 | +    import wave
 238 | +    with tempfile.TemporaryDirectory() as d:
 239 | +        w = os.path.join(d, "head.wav")
 240 | +        with wave.open(w, "wb") as f:
 241 | +            f.setnchannels(2)
 242 | +            f.setsampwidth(2)
 243 | +            f.setframerate(48000)
 244 | +            f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
 245 | +        return head_tail(SourceAudio(w))
 246 | +
 247 | +
 248 | +def hook_lead_at(src, c, fade_ms=0):
 249 | +    """(genuine lead ms, onset s) of the audio as cut at `c` with its fade-in: G17a's own measure (head_tail)."""
 250 | +    ht = _head_tail_of(_cut_head(src, c, fade_ms))
 251 | +    return ht["lead_ms"], ht["onset"]
 252 | +
 253 | +
 254 |  def write_lock_cut_table(run_dir):
 255 |      """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
 256 |      the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
 257 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 258 | index 45ccfe8..5e25d43 100644
 259 | --- a/tests/package/funnel.py
 260 | +++ b/tests/package/funnel.py
 261 | @@ -39,8 +39,20 @@ def q(t, n=140):
 262 |      return t if len(t) <= n else t[:n - 1] + "…"
 263 |  
 264 |  
 265 | +def mom(mid):
 266 | +    """The moment's record; a trimmed variant ("<id>~trim", ruling 33 part 2) is named by its original, with the
 267 | +    trimmed word marked (the record keeps the variant's id only)."""
 268 | +    if mid in by:
 269 | +        return by[mid]
 270 | +    o = by.get(str(mid).removesuffix("~trim"))
 271 | +    if o is None:
 272 | +        return {}
 273 | +    w, _, rest = (o.get("text") or "").partition(" ")
 274 | +    return dict(o, moment_id=mid, text=f"[{w} trimmed] {rest}", duration_s=f"under {o.get('duration_s')}")
 275 | +
 276 | +
 277 |  def tx(mid):
 278 | -    return by.get(mid, {}).get("text") or texts.get(mid) or ""
 279 | +    return mom(mid).get("text") or texts.get(mid) or ""
 280 |  
 281 |  
 282 |  def emit(title, rows, head=("lost", "exact reason", "one example (moment text)")):
 283 | @@ -189,7 +201,7 @@ try:
 284 |      import transcript_truth as TT
 285 |      rt = P.Router(record_dir=REPLIES, replay=True)
 286 |      for mid in lost3:
 287 | -        m = by[mid]
 288 | +        m = mom(mid)
 289 |          try:
 290 |              t = TT.verify_segment(rt, m["video_id"], float(m["start"]), float(m["end"]), m["text"], LV2)
 291 |              e = t.get("edges") or {}
 292 | @@ -219,25 +231,36 @@ if len(lost3) > 1:
 293 |      print("\nEvery stage-3 loss, exactly:")
 294 |      for mid in lost3:
 295 |          k, d = detail.get(mid, (sp[mid], ""))
 296 | -        print(f"- {by[mid].get('channel_name')}: {k}: {q(d, 260)}")
 297 | +        print(f"- {mom(mid).get('channel_name')}: {k}: {q(d, 260)}")
 298 |  
 299 |  # ---- stage 4: cuttable -> can open
 300 |  ho = pre.get("hook_onset") or {}
 301 |  lost4 = [(v, mid) for mid, v in ho.items() if v != "PASS"]
 302 |  emit(f"Stage 4: {pre.get('cuttable')} cuttable -> {sum(v == 'PASS' for v in ho.values())} can open a medley (G17a; "
 303 |       f"the others stay in play as non-hook clips)", grouped(lost4) or [[0, "-", "-"]])
 304 | +tc, sv = pre.get("trim_cut") or {}, pre.get("second_vendor") or {}
 305 | +if pk.get("trimmed") is not None:
 306 | +    print(f"\nTrimmed variants (ruling 33 part 2): {len(pk['trimmed'])} of the {len(pk.get('no_role') or {})} left "
 307 | +          f"out by STAND_ALONE joined the usable moments; {len(tc)} cleared to here and failed the trimmed cut (a), at "
 308 | +          f"any place:")
 309 | +    for mid, why in tc.items():
 310 | +        print(f"- {mom(mid).get('channel_name')}: {q(why, 200)}: \"{q(tx(mid), 120)}\"")
 311 | +sv_lost = [(v, mid) for mid, v in sv.items() if not str(v).startswith("PASS")]
 312 | +if sv:
 313 | +    emit(f"Stage 4b: step A from the second vendor (order 06:22 item 45): {len(sv) - len(sv_lost)} of {len(sv)} pass",
 314 | +         grouped(sv_lost) or [[0, "-", "-"]])
 315 |  
 316 |  # ---- stage 5: -> angle -> line-ups
 317 |  print(f"\n**Stage 5: the angle step and the line-ups.** why_none: {pk.get('why_none')!r}; angles: "
 318 |        f"{len(pk.get('angles') or [])} from {pk.get('angle_backend')}")
 319 | -cl = [mid for mid, v in sp.items() if v == "PASS"]
 320 | +cl = [mid for mid, v in sp.items() if v == "PASS" and mid not in tc and not str(sv.get(mid, "PASS")).startswith("FAIL")]
 321 |  print("\nThe moments offered to the angle step:")
 322 |  for mid in cl:
 323 | -    m = by.get(mid, {})
 324 | +    m = mom(mid)
 325 |      print(f"- {m.get('channel_name')} ({m.get('video_id')}), {m.get('duration_s')} s, can open: "
 326 |            f"{ho.get(mid) == 'PASS'}: \"{q(m.get('text'), 150)}\"")
 327 |  print(f"\nTogether {round(sum(float(by[m]['duration_s']) for m in cl if m in by), 2)} s from "
 328 | -      f"{len({by[m]['channel_id'] for m in cl if m in by})} channels.")
 329 | +      f"{len({mom(m)['channel_id'] for m in cl if mom(m)})} channels (a trimmed variant's seconds not counted).")
 330 |  for a in pk.get("angles") or []:
 331 |      print(f"- angle: \"{q(a.get('angle'), 200)}\" moments {len(a.get('moments') or [])}")
 332 |  log = open(os.path.join(D, "package.log")).read().splitlines()
 333 | diff --git a/tests/package/test_hook_onset.py b/tests/package/test_hook_onset.py
 334 | index 536bcd7..78ce289 100644
 335 | --- a/tests/package/test_hook_onset.py
 336 | +++ b/tests/package/test_hook_onset.py
 337 | @@ -4,8 +4,11 @@ kept 30 ms of genuine quiet before its first onset. The word record showed a 400
 338 |  then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
 339 |  rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
 340 |  import os
 341 | +import shutil
 342 |  import sys
 343 | +import tempfile
 344 |  import unittest
 345 | +import wave
 346 |  
 347 |  import numpy as np
 348 |  
 349 | @@ -89,5 +92,75 @@ class TestHookOnset(unittest.TestCase):
 350 |          self.assertIn("not inside its audio window", r["why"])
 351 |  
 352 |  
 353 | +TRIM_WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),   # the previous sentence
 354 | +              ("So", 1.75, 1.95),                                                       # the trimmed word
 355 | +              ("Bitcoin", 2.40, 2.80), ("rises.", 2.80, 3.30),                          # the clip: words 4..5
 356 | +              ("Next", 3.70, 4.10), ("words", 4.10, 4.50), ("follow.", 4.50, 5.10)]
 357 | +TRIM_SPEECH = [(0.20, 1.35, -20.0), (2.40, 3.30, -20.0), (3.70, 5.10, -20.0)]
 358 | +
 359 | +
 360 | +def wav(path, spans, dur=6.0, bed=-55.0, sr=16000):
 361 | +    """A real 16 kHz file: white noise at `bed` dBFS RMS (room tone), louder noise over `spans` [(t0, t1, dBFS)]."""
 362 | +    lv = np.full(int(dur * sr), 10 ** (bed / 20))
 363 | +    for a, b, v in spans:
 364 | +        lv[int(a * sr):int(b * sr)] = 10 ** (v / 20)
 365 | +    x = np.clip(np.random.default_rng(7).standard_normal(len(lv)) * lv, -1, 1)
 366 | +    with wave.open(path, "wb") as f:
 367 | +        f.setnchannels(1)
 368 | +        f.setsampwidth(2)
 369 | +        f.setframerate(sr)
 370 | +        f.writeframes((x * 32767).astype(np.int16).tobytes())
 371 | +    return path
 372 | +
 373 | +
 374 | +def trim_src():
 375 | +    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in TRIM_WORDS)
 376 | +    return E.Source("vidT", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
 377 | +                    timing="word", file_head=False, vod=True)
 378 | +
 379 | +
 380 | +class TestTrimmedCut(unittest.TestCase):
 381 | +    """Ruling 33 part 2 (item 42): a trimmed moment's IN edge is planned AFTER the trimmed word, as the render plans it
 382 | +    (sentence_law.trimmed_boundary / edge_plan(trimmed=...), verbatim from its c6605895), and ruling 33 (a) is the
 383 | +    render's own onset rule on the audio as cut (accepted_cut's cut and fade, then trimmed_onset), with one more 10 ms
 384 | +    frame here. On a generated audio file: the render's rule decodes the file. The 05:48 build's two cleared trims
 385 | +    failed the old measure, which only cut after a sentence end ("'So' does not end a sentence")."""
 386 | +
 387 | +    def setUp(self):
 388 | +        self.d = tempfile.mkdtemp()
 389 | +
 390 | +    def tearDown(self):
 391 | +        shutil.rmtree(self.d, ignore_errors=True)
 392 | +
 393 | +    def measure(self, spans, trimmed="So"):
 394 | +        sa = SL.SourceAudio(wav(os.path.join(self.d, "t.wav"), spans))
 395 | +        return HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(sa, 0.0), trimmed=trimmed)
 396 | +
 397 | +    def test_a_measured_pause_after_the_trimmed_word_passes(self):
 398 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                 # "So", 450 ms of room tone, "Bitcoin"
 399 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"]), (True, True), r)
 400 | +        self.assertGreater(r["trim"]["onset_s"], SL.HOP_S + HO.MARGIN_MS / 1000)
 401 | +        self.assertTrue(1.95 <= r["trim"]["cut_in"] < 2.40, r["trim"])        # the cut sits in the pause
 402 | +        self.assertTrue(r["pass"], r)                                         # and its lead lets it open a medley
 403 | +
 404 | +    def test_a_trimmed_word_run_into_the_next_cannot_be_cut(self):
 405 | +        r = self.measure([(0.20, 1.35, -20.0), (1.75, 3.30, -20.0), (3.70, 5.10, -20.0)])   # no pause after "So"
 406 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, True, False), r)
 407 | +        self.assertIn("cannot be cut cleanly", r["trim"]["why"])
 408 | +
 409 | +    def test_the_trimmed_word_must_be_the_word_heard_before_the_clip(self):
 410 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed="But")
 411 | +        self.assertEqual((r["trim"]["pass"], r["pass"]), (False, False), r)
 412 | +        self.assertIn("not the word before the lock", r["trim"]["why"])
 413 | +
 414 | +    def test_untrimmed_is_unchanged_and_no_audio_file_is_never_a_pass(self):
 415 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed=None)   # the old rule: a sentence end first
 416 | +        self.assertEqual((r["pass"], "trim" in r), (False, False), r)
 417 | +        self.assertIn("does not end a sentence", r["why"])
 418 | +        env = Env(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                        # an envelope, no file to cut (law L-m)
 419 | +        r = HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(env, 0.0), trimmed="So")
 420 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, False, False), r)
 421 | +
 422 | +
 423 |  if __name__ == "__main__":
 424 |      unittest.main()
 425 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 426 | index 3cb6fa9..89f8ad6 100644
 427 | --- a/tests/package/test_medley.py
 428 | +++ b/tests/package/test_medley.py
 429 | @@ -425,11 +425,12 @@ class Rig:
 430 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 431 |  
 432 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 433 | -                 spend=None, no_hook=()):
 434 | +                 spend=None, no_hook=(), trim_fail=()):
 435 |          import providers as P
 436 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 437 |          self.takeaways, self.spend = list(takeaways or []), spend
 438 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 439 | +        self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
 440 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 441 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 442 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 443 | @@ -462,6 +463,17 @@ class Rig:
 444 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 445 |          return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
 446 |  
 447 | +    def onset(self, m, *a, **k):
 448 | +        """hook_onset.measure's record: the hook lead, and for a trimmed moment its trimmed cut ("trim")."""
 449 | +        r = ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"} if m["moment_id"] in self.no_hook
 450 | +             else {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"})
 451 | +        if m.get("trimmed_leading"):
 452 | +            ok = m["moment_id"] not in self.trim_fail
 453 | +            r["trim"] = {"pass": ok, "measured": True, "why": "ok" if ok else "the trimmed word 'But' cannot be cut "
 454 | +                                                                              "cleanly: no measured pause (co-articulated)"}
 455 | +            r["pass"] = r["pass"] and ok
 456 | +        return r
 457 | +
 458 |      def run(self):
 459 |          fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
 460 |                 "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 461 | @@ -479,9 +491,7 @@ class Rig:
 462 |                                                           "backend": "xai:grok"},
 463 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 464 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 465 | -            "hook_onset_for": lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"}
 466 | -                                                  if m["moment_id"] in self.no_hook else
 467 | -                                                  {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"}),
 468 | +            "hook_onset_for": self.onset,
 469 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 470 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 471 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 472 | @@ -828,13 +838,18 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 473 |          saved = PK.trim_variant
 474 |          try:
 475 |              PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 476 | -            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 477 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"})
 478 |              out = rig.run()
 479 | +            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 480 | +            out2 = rig2.run()
 481 |          finally:
 482 |              PK.trim_variant = saved
 483 |          self.assertEqual(out["trimmed"], {"b": "b~trim"})
 484 | -        self.assertIn("b~trim", out["prescreen"]["trim_cut"])                     # ruling 33 (a): out, any place
 485 | +        self.assertTrue(out["prescreen"]["trim_cut"]["b~trim"].startswith("FAIL: the trimmed word"))   # (a): out
 486 | +        self.assertNotIn("id=b~trim ", next(p for r, p in rig.prompts if r == "angle_write"))         # at any place
 487 |          self.assertIsNotNone(out["package"])
 488 | +        self.assertEqual(out2["prescreen"]["trim_cut"], {})        # its cut is clean, only its hook lead fails: it
 489 | +        self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 490 |  
 491 |  
 492 |  class TestRuling41Search(unittest.TestCase):
 493 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips from other channels); the integrator
renders them. Your role: a strict reviewer of the pin stage's acoustic cut measure for TRIMMED clips.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- ORCHESTRATOR RULING 33 (03:12 ET Nov 13): "A clip that opens on a discourse conjunction or reply word (but, and,
  so, well, now, yeah) may have that ONE leading word trimmed at the cut when (a) the acoustic onset rule is met on
  the trimmed cut, and (b) the pipeline's STAND_ALONE scorer affirms the trimmed clip at its unchanged threshold, and
  (c) L-s step A is re-judged on the trimmed span. The locked text is the trimmed text. If any of the three fails, the
  clip is out." ORDER 04:58 item 42: use it now (the render merged it).
- The RENDER (the integrator's branch, pipeline/sentence_law.py at c6605895, unchanged since) cuts a trimmed clip so:
  edge_plan(sa, words, i0, i1, trimmed=lock["trimmed_leading"]) plans the IN edge with trimmed_boundary (the
  word before the lock is the trimmed word; the untrimmed sentence starts a sentence; a quiet run with a heard gap
  lies between the trimmed word and the first kept word), and the cut must sit inside that quiet run; then
  accepted_cut picks the cut and its fade; then trimmed_onset(src, cut_in, fade_in_ms) holds the clip unless the
  audio as cut opens in quiet (the first onset after the first 10 ms hop).
- The pin stage (this branch) measures each cuttable moment on its law-L-v-2 audio window (a 16 kHz WAV of
  [start - 4 s, end + 1.5 s], fetched once) with hook_onset.measure: a planned cut, then G17a's genuine lead before
  the first onset, with ONE extra 10 ms frame of margin (the slice vs the render's own decode).
- THE DEFECT this diff fixes: hook_onset.measure planned every IN edge with the OLD edge_plan, which only cuts after a
  sentence end. A trimmed clip's IN edge sits after the trimmed word, which never ends a sentence. So both trimmed
  variants that cleared step A and L-v 2 in the 05:48 build failed with "no cut before the hook: 'So' does not end a
  sentence": a gap in the pin stage, not a property of the moments.
- Ruling 33 (b) is NOT in this diff: the pin stage keeps (b) strict (TRIM_SCORER_PENDING = False), so a line-up with
  a trimmed clip still fails STAND_ALONE until the orchestrator rules. This diff only makes (a) measurable as the
  render measures it.
- Laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts to make
  something pass.

The change:
1. pipeline/sentence_law.py: copied VERBATIM from the render's c6605895 (verified byte-identical by an AST source
   comparison): TRIMMABLE_LEADING, trimmed_boundary, trimmed_onset, edge_plan(trimmed=None) (identical to the old
   edge_plan when trimmed is None), and the three helpers trimmed_onset needs (_cut_head, _head_tail_of,
   hook_lead_at). Nothing else of the render's newer law is taken. No function is removed.
2. pipeline/hook_onset.py:
   - measure(..., trimmed=None): with a trimmed word, the plan is edge_plan(..., trimmed={"word": trimmed}), the
     render's own shape (its lock carries {"word": ...}).
   - trim_onset(sa, plan, a): accepted_cut on the window file, then trimmed_onset, then the pin stage's one-frame
     margin: the onset must lie after 10 ms + 10 ms. Any exception: "not measured", never a pass.
   - The record carries "trim" on every path for a trimmed moment; "pass" (may it OPEN a medley) also needs it.
3. pipeline/package.py:
   - hook_onset_for passes trimmed=m.get("trimmed_leading").
   - build(): a trimmed moment is left out at ANY place when its "trim" record is not a pass (ruling 33 (a)). Before,
     it was left out whenever its HOOK lead failed, which is a different rule (G17a applies to the hook only).
   - The STAND_ALONE log line counts the trimmed variants (order 06:22 item 47).
4. tests/package/funnel.py (the build-record report): a "<id>~trim" variant is named by its original moment instead
   of a blank row or a KeyError; the variants are counted; the moments offered to the angle step exclude the
   trimmed-cut failures (and, when the record has it, the second vendor's step-A failures of the other change).
5. Tests:
   - test_hook_onset: four tests on a GENERATED 16 kHz audio file (the render's rule decodes the file): a measured
     pause after "So" passes (the cut inside the pause, the onset after 20 ms, and the hook lead too); "So" run into
     the next word cannot be cut cleanly; a trimmed word that is not the word before the clip fails; the untrimmed
     rule is unchanged and an envelope with no file is "not measured", never a pass.
   - test_medley: the build rig's onset stub carries the "trim" record. A trimmed moment whose trimmed cut fails is
     out at any place, never offered to the angles; one whose cut is clean but whose hook lead fails stays as a clip.
- Measured on the real data (the 05:48 build's two cleared trims, their own L-v 2 windows), before this audit:
  "So MSCI didn't force any Bitcoin selling this week..." passes (cut in the pause after "So", first onset 130 ms,
  83 ms fade); "So if you look at the average income..." fails ("So" runs into "if": no measured pause).

Stated assumption (K1): the render's trimmed_boundary treats a trimmed word that is the transcript's FIRST word as a
file head. On the pin stage's window the first word is only the window's first word, so that sentence-start check can
pass without its evidence there. The untrimmed sentence's start is ALREADY verified on the full word record by
eligibility (the original moment's IN rule: the word before it ends a sentence, or the file head), and a trimmed
variant inherits that verdict. Say so if you think that is not enough.

Check in particular:
- that the copied functions are used exactly as the render uses them (the trimmed dict shape, the plan, accepted_cut,
  then trimmed_onset), and that any divergence only makes the pin stage stricter;
- that every failure to plan, cut or decode is never a pass, and that "trim" is present on every path for a trimmed
  moment;
- that untrimmed moments are judged exactly as before (the hook lead rule and the old IN boundary);
- that the build's new rule (out at any place only when the trimmed cut fails) is right under ruling 33 (a), and
  that the hook still needs both;
- the funnel changes: nothing in them changes a build.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

