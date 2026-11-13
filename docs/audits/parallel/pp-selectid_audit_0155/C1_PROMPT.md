# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0155
# Branch: pp-selectid
# Generated: 2026-11-13 01:56 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0155/C1_STEP.diff (374 lines)
```
   1 | diff --git a/pipeline/hook_onset.py b/pipeline/hook_onset.py
   2 | new file mode 100644
   3 | index 00000000..7f87faa5
   4 | --- /dev/null
   5 | +++ b/pipeline/hook_onset.py
   6 | @@ -0,0 +1,74 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/hook_onset.py: G17a at the PIN stage. The render holds a medley whose HOOK keeps less than
   9 | +HEAD_LEAD_MIN_S (80 ms, D1: the hook starts playback) of GENUINE quiet before its first onset in the prepared clip
  10 | +(sentence_law.gate_g17_prepared).
  11 | +
  12 | +Batch pin #1, held 01:39 ET Nov 13: the word record put a 400 ms gap before the hook's first word. The source audio
  13 | +holds breath, then a run of digital zeros (a hard edit), then speech. Zeros are not room tone, so the genuine lead
  14 | +was 30 ms. The word record's timestamps cannot see an edit; only the audio can.
  15 | +
  16 | +So before a moment may OPEN a medley:
  17 | +- its cut is planned on the SOURCE audio (the L-v 2 window that transcript_truth.audio_window already fetched for the
  18 | +  second recogniser) with the render's own sentence_law.edge_plan;
  19 | +- the planned prepared clip's head (the source's 10 ms envelope from the planned cut on, a lead-in pad added only
  20 | +  where edge_plan allows one: a file head) is measured with the render's own sentence_law.head_tail.
  21 | +
  22 | +The envelope is sliced from the source, so it can differ from the render's decode of the prepared file by up to one
  23 | +10 ms frame. The render's 20 ms fade-in is not applied, which can only make this check stricter.
  24 | +
  25 | +measure(...) -> {"pass", "measured", "lead_ms", "cut_in", "pad_s", "why"}. Not measured (no audio, no plan) is never
  26 | +a pass (law L-m).
  27 | +"""
  28 | +import sentence_law as SL
  29 | +import transcript_truth as TT
  30 | +
  31 | +
  32 | +class _Slice(SL.SourceAudio):
  33 | +    """[t0, t1] of a decoded source's envelope on its own clock (from 0): the planned prepared clip, before fades."""
  34 | +
  35 | +    def __init__(self, sa, t0, t1):                     # no decode: SourceAudio's methods read t / db / dur only
  36 | +        m = (sa.t >= t0 - 1e-9) & (sa.t < t1 - 1e-9)
  37 | +        self.path, self.t, self.db, self.dur = sa.path, sa.t[m] - t0, sa.db[m], max(0.0, t1 - t0)
  38 | +
  39 | +
  40 | +def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  41 | +    """The hook moment's planned prepared clip: does it keep >= HEAD_LEAD_MIN_S of genuine quiet before its first
  42 | +    onset? src: the moment's eligibility Source; w0 / w1: its first / last word indices in src.tokens; start / end:
  43 | +    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window."""
  44 | +    need = SL.HEAD_LEAD_MIN_S * 1000
  45 | +    try:
  46 | +        if audio is None:
  47 | +            wav, a = TT.audio_window(video_id, float(start), float(end), work_dir)
  48 | +            sa = SL.SourceAudio(wav)
  49 | +        else:
  50 | +            sa, a = audio
  51 | +    except Exception as e:
  52 | +        return {"pass": False, "measured": False, "why": f"no source audio: {type(e).__name__}: {str(e)[:120]}"}
  53 | +    toks = src.tokens
  54 | +    idx = [i for i, t in enumerate(toks) if isinstance(t.get("start"), (int, float)) and
  55 | +           isinstance(t.get("end"), (int, float)) and float(t["start"]) >= a and float(t["end"]) <= a + sa.dur]
  56 | +    if w0 not in idx or w1 not in idx:
  57 | +        return {"pass": False, "measured": False, "why": "the clip's words are not inside its audio window"}
  58 | +    words = [{"word": toks[i]["word"], "start": float(toks[i]["start"]) - a, "end": float(toks[i]["end"]) - a}
  59 | +             for i in idx]
  60 | +    i0, i1 = idx.index(w0), idx.index(w1)
  61 | +    try:
  62 | +        plan = SL.edge_plan(sa, words, i0, i1)
  63 | +    except Exception as e:                               # LawError: no audio to read levels from, and the like
  64 | +        return {"pass": False, "measured": False, "why": f"no cut plan: {type(e).__name__}: {str(e)[:120]}"}
  65 | +    cin = plan.get("in") or {}
  66 | +    if not cin.get("cuttable"):
  67 | +        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut before the hook: "
  68 | +                f"{cin.get('reason') or 'not cuttable'}"}
  69 | +    cut_in = float(cin["cut"])
  70 | +    out = plan.get("out") or {}
  71 | +    cut_out = float(out["cut"]) if out.get("cuttable") else words[i1]["end"]
  72 | +    try:
  73 | +        ht = SL.head_tail(_Slice(sa, cut_in, cut_out))
  74 | +    except Exception as e:
  75 | +        return {"pass": False, "measured": False, "why": f"no head measured: {type(e).__name__}: {str(e)[:120]}"}
  76 | +    pad = float(cin.get("lead_in_pad_s") or 0.0)         # a room-tone pad: edge_plan allows one only at a file head
  77 | +    lead = int(round(ht["lead_ms"] + pad * 1000))
  78 | +    ok = lead >= need
  79 | +    return {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  80 | +            "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms (G17a)"}
  81 | diff --git a/pipeline/package.py b/pipeline/package.py
  82 | index aaae8f37..de6a4a35 100644
  83 | --- a/pipeline/package.py
  84 | +++ b/pipeline/package.py
  85 | @@ -542,7 +542,7 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
  86 |      return out
  87 |  
  88 |  
  89 | -def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
  90 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False):
  91 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  92 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  93 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  94 | @@ -550,11 +550,14 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  95 |      (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
  96 |      earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
  97 |      seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
  98 | -    ONE channel may give two clips, from two different videos. None if impossible."""
  99 | +    ONE channel may give two clips, from two different videos. need_onset (build() sets it): a moment opens the
 100 | +    medley only if its hook onset was measured and passed (hook_onset_for, G17a at the pin stage); the proposer's hook
 101 | +    gives way to the angle's next one that did. None if impossible."""
 102 |      lo, hi = crange or medley_content_range()
 103 |      pos = {m: i for i, m in enumerate(angle["moments"])}
 104 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 105 | -    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 106 | +    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
 107 | +             (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
 108 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 109 |      for h in hooks:
 110 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 111 | @@ -907,6 +910,20 @@ def truth_for(router, m, work_dir, cache):
 112 |      return cache[m["moment_id"]]
 113 |  
 114 |  
 115 | +def hook_onset_for(m, sources, work_dir, cache):
 116 | +    """G17a at the pin stage (hook_onset.measure): may this moment OPEN a medley? Its cut planned on the source audio
 117 | +    (the L-v 2 window) with the render's own edge_plan, and >= 80 ms of genuine quiet before its first onset by the
 118 | +    render's own head_tail. Any failure to measure is recorded and never a pass (law L-m)."""
 119 | +    if m["moment_id"] not in cache:
 120 | +        import hook_onset as HO
 121 | +        try:
 122 | +            cache[m["moment_id"]] = HO.measure(sources[m["video_id"]], m["words"][0], m["words"][1], m["video_id"],
 123 | +                                               float(m["start"]), float(m["end"]), work_dir)
 124 | +        except Exception as e:
 125 | +            cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 126 | +    return cache[m["moment_id"]]
 127 | +
 128 | +
 129 |  def _writers(router):
 130 |      """The vendor and family of the angle_write chain's first back-end not down (verdicts avoid them; a live failover
 131 |      adds the next writer's)."""
 132 | @@ -992,6 +1009,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 133 |      cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
 134 |      out["prescreen"]["cuttable"] = len(cleared)
 135 |      log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
 136 | +    hk = {}
 137 | +    with ThreadPoolExecutor(max_workers=4) as pre:     # G17a at the pin stage: which moments may OPEN a medley
 138 | +        futs = {mid: pre.submit(hook_onset_for, m, sources, work_dir, hk) for mid, m in cleared.items()}
 139 | +        for mid, f in futs.items():
 140 | +            cleared[mid]["hook_onset"] = f.result()
 141 | +    out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 142 | +                                      ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 143 | +                                      str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 144 | +    log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 145 | +        f"(>= 80 ms of genuine quiet before the first onset, G17a)")
 146 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 147 |          out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
 148 |                             f"channels")
 149 | @@ -1106,7 +1133,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 150 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 151 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
 152 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 153 | -                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 154 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 155 | +                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 156 |          import package_pin
 157 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 158 |          if problems:
 159 | @@ -1129,9 +1157,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 160 |              while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
 161 |                  if over_budget(ai):
 162 |                      break
 163 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed)), None
 164 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True), None
 165 |                  if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 166 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True)
 167 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True)
 168 |                      if segs is not None:
 169 |                          rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 170 |                                 if sum(m["channel_id"] == c for m in segs) > 1]
 171 | @@ -1280,7 +1308,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 172 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 173 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 174 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 175 | -                                            style=HS.lint_lines(pk["lines"]))
 176 | +                                            style=HS.lint_lines(pk["lines"]),
 177 | +                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 178 |                      if not ok_c:
 179 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 180 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 181 | @@ -1338,11 +1367,13 @@ def _spent(spend):
 182 |      return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 183 |  
 184 |  
 185 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None):
 186 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 187 | +              hook=None):
 188 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 189 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 190 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 191 | -    (shape=(ok, [why]) from ly_shape())."""
 192 | +    (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
 193 | +    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin."""
 194 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 195 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 196 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 197 | @@ -1398,4 +1429,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 198 |          **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 199 |                                  why=[f"{v['slot']}: {v['detail']}" for v in style])}
 200 |             if style is not None else {}),
 201 | +        **({"hook_onset": dict(row(hook.get("pass") is True, "hook_onset.measure (sentence_law.edge_plan + head_tail "
 202 | +                                   "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
 203 | +                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 204 | +           if hook is not None else {}),
 205 |      }
 206 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 207 | index 87fb9461..d975d12f 100644
 208 | --- a/pipeline/package_pin.py
 209 | +++ b/pipeline/package_pin.py
 210 | @@ -26,7 +26,8 @@ from datetime import datetime, timezone
 211 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 212 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 213 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 214 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style")   # L-y (20:30): the clips-alone verdict, the medley's shape;
 215 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset")   # hook_onset: G17a at the pin stage, after
 216 | +                                                                      # batch pin #1's render hold (01:39 ET Nov 13)   # L-y (20:30): the clips-alone verdict, the medley's shape;
 217 |                                                           # ruling 6 (22:40): PBX's copy rules on every line
 218 |  
 219 |  
 220 | diff --git a/tests/package/test_hook_onset.py b/tests/package/test_hook_onset.py
 221 | new file mode 100644
 222 | index 00000000..142fdf4d
 223 | --- /dev/null
 224 | +++ b/tests/package/test_hook_onset.py
 225 | @@ -0,0 +1,72 @@
 226 | +#!/usr/bin/env python3
 227 | +"""pipeline/hook_onset.py: G17a at the PIN stage. Batch pin #1 was held at render (01:39 ET Nov 13) because its hook
 228 | +kept 30 ms of genuine quiet before its first onset. The word record showed a 400 ms gap, but the source held breath,
 229 | +then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
 230 | +rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
 231 | +import os
 232 | +import sys
 233 | +import unittest
 234 | +
 235 | +import numpy as np
 236 | +
 237 | +HERE = os.path.dirname(os.path.abspath(__file__))
 238 | +REPO = os.path.dirname(os.path.dirname(HERE))
 239 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 240 | +import eligibility as E  # noqa: E402
 241 | +import hook_onset as HO  # noqa: E402
 242 | +import sentence_law as SL  # noqa: E402
 243 | +
 244 | +WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),        # the previous sentence
 245 | +         ("When", 1.75, 2.15), ("Bitcoin", 2.15, 2.60), ("rises.", 2.60, 3.20),           # the hook: words 3..5
 246 | +         ("Next", 3.60, 4.00), ("words", 4.00, 4.40), ("follow.", 4.40, 5.00)]
 247 | +
 248 | +
 249 | +class Env(SL.SourceAudio):
 250 | +    """A synthetic source envelope (no decode): `spans` [(t0, t1, dBFS)] over a bed of room tone."""
 251 | +
 252 | +    def __init__(self, spans, dur=6.0, bed=-55.0):
 253 | +        self.path, self.dur = "synthetic", dur
 254 | +        self.t = np.arange(int(round(dur / SL.HOP_S))) * SL.HOP_S
 255 | +        self.db = np.full(len(self.t), bed)
 256 | +        for a, b, v in spans:
 257 | +            self.db[(self.t >= a - 1e-9) & (self.t < b - 1e-9)] = v
 258 | +
 259 | +
 260 | +SPEECH = [(0.20, 1.36, -20.0), (3.60, 5.00, -20.0)]
 261 | +
 262 | +
 263 | +def src():
 264 | +    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in WORDS)
 265 | +    return E.Source("vidH", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
 266 | +                    timing="word", file_head=False, vod=True)
 267 | +
 268 | +
 269 | +class TestHookOnset(unittest.TestCase):
 270 | +    def measure(self, env, **kw):
 271 | +        return HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent", audio=(env, 0.0), **kw)
 272 | +
 273 | +    def test_breath_then_digital_zeros_before_the_first_word_fails_g17a(self):
 274 | +        """Pin #1's pattern: a 400 ms word-record gap that is breath, then digital zeros, then 30 ms of quiet."""
 275 | +        env = Env(SPEECH + [(1.41, 1.58, -27.0), (1.65, 1.78, -200.0), (1.78, 1.81, -60.0), (1.81, 3.20, -20.0)])
 276 | +        r = self.measure(env)
 277 | +        self.assertEqual((r["pass"], r["measured"]), (False, True), r)
 278 | +        self.assertLess(r["lead_ms"], 80)
 279 | +        self.assertIn("G17a", r["why"])
 280 | +
 281 | +    def test_room_tone_before_the_first_word_passes(self):
 282 | +        env = Env(SPEECH + [(1.81, 3.20, -20.0)])                    # 1.36 .. 1.81: genuine room tone (-55)
 283 | +        r = self.measure(env)
 284 | +        self.assertEqual((r["pass"], r["measured"]), (True, True), r)
 285 | +        self.assertGreaterEqual(r["lead_ms"], 80)
 286 | +
 287 | +    def test_no_audio_or_words_outside_the_window_is_not_measured_never_a_pass(self):
 288 | +        r = HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent/dir")      # no L-v 2 window, no network
 289 | +        self.assertEqual((r["pass"], r["measured"]), (False, False))
 290 | +        env = Env(SPEECH + [(1.81, 3.20, -20.0)], dur=2.5)                       # the hook runs past the audio
 291 | +        r = self.measure(env)
 292 | +        self.assertEqual((r["pass"], r["measured"]), (False, False))
 293 | +        self.assertIn("not inside its audio window", r["why"])
 294 | +
 295 | +
 296 | +if __name__ == "__main__":
 297 | +    unittest.main()
 298 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 299 | index 6b68f88e..6501f65f 100644
 300 | --- a/tests/package/test_medley.py
 301 | +++ b/tests/package/test_medley.py
 302 | @@ -368,14 +368,14 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 303 |  
 304 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 305 |          pk = self.build()
 306 | -        self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
 307 | +        self.assertEqual(package_pin.required_gates(pk)[-4:], ("medley", "ly_shape", "house_style", "hook_onset"))
 308 |          pk["gates"] = self.gates(pk)
 309 |          pin = package_pin.to_pin(spk(pk), "test")
 310 |          mp = pin["moments_package"]
 311 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 312 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 313 |          self.assertEqual(mp["shape"], "medley")
 314 | -        for missing in ("medley", "ly_shape", "house_style"):
 315 | +        for missing in ("medley", "ly_shape", "house_style", "hook_onset"):
 316 |              g = self.gates(pk)
 317 |              g.pop(missing)
 318 |              with self.assertRaises(package_pin.PinRefused):
 319 | @@ -421,11 +421,11 @@ class Rig:
 320 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 321 |  
 322 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 323 | -                 spend=None):
 324 | +                 spend=None, no_hook=()):
 325 |          import providers as P
 326 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 327 |          self.takeaways, self.spend = list(takeaways or []), spend
 328 | -        self.uncuttable, self.excluded = set(uncuttable), set(excluded)
 329 | +        self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 330 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 331 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 332 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 333 | @@ -475,6 +475,9 @@ class Rig:
 334 |                                                           "backend": "xai:grok"},
 335 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 336 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 337 | +            "hook_onset_for": lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"}
 338 | +                                                  if m["moment_id"] in self.no_hook else
 339 | +                                                  {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"}),
 340 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 341 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 342 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 343 | @@ -617,6 +620,20 @@ class TestBuildLoop(unittest.TestCase):
 344 |          self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
 345 |          self.assertIsNone(out["package"])
 346 |  
 347 | +    def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
 348 | +        """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
 349 | +        only when its hook onset was measured and passed; the proposer's hook gives way to the angle's next."""
 350 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
 351 | +        pk = rig.run()["package"]
 352 | +        self.assertNotEqual(pk["segments"][0]["moment_id"], "h")
 353 | +        self.assertEqual(pk["gates"]["hook_onset"]["status"], "PASS")
 354 | +        self.assertEqual(pk["gates"]["hook_onset"]["lead_ms"], 200)
 355 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h", "x", "y", "z"})
 356 | +        out = rig.run()
 357 | +        self.assertIsNone(out["package"])
 358 | +        self.assertEqual(rig.medley_calls, [])                    # nothing paid for a line-up that cannot open
 359 | +        self.assertIn("no line-up", out["tried"][0]["why"])
 360 | +
 361 |      def test_the_supply_exception_is_recorded(self):
 362 |          ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
 363 |          rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
 364 | @@ -674,7 +691,8 @@ class TestNoVoiceRealGates(unittest.TestCase):
 365 |                 for sg in pk["segments"]}
 366 |          coh = dict(med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 367 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 368 | -                                   shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 369 | +                                   shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 370 | +                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"})
 371 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 372 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 373 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 374 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real
clips). It adds G17a at the PIN stage: a medley's HOOK must keep >= 80 ms (HEAD_LEAD_MIN_S, D1: the hook starts
playback) of GENUINE quiet before its first onset in the prepared clip.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: the integrator's render HELD batch pin #1 at 01:39 ET Nov 13 on G17_onset_tail. Its hook kept 30 ms of genuine
lead (the render measures that with sentence_law.gate_g17_prepared = head_tail on the prepared clip).
- The packager's eligibility rule T12 measured the WORD RECORD's gap before the hook (400 ms) and passed it.
- The source audio, measured offline with acoustic.rms_envelope at 10 ms, holds breath (about -27 dBFS), then exact
  DIGITAL ZEROS (a hard edit, -200 dB), then speech.
- Zeros are not room tone (quiet_runs(genuine=True) drops frames under DIGITAL_FLOOR_DBFS), so the genuine lead was
  about 20-30 ms.
- On pin #1's real audio, the new check measures 20 ms for that hook (FAIL), and 200 ms / 30 ms for its two other
  clips (only a hook needs 80 ms).

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- the gate inventory is sealed, and a required row missing or not exactly PASS refuses the pin.

The files:
1. pipeline/hook_onset.py (new): measure(src, w0, w1, video_id, start, end, work_dir, audio=None).
   - The moment's cut is planned on the SOURCE audio (the L-v 2 window that transcript_truth.audio_window already
     fetched) with the render's own sentence_law.edge_plan.
   - The planned prepared clip's head is measured with the render's own sentence_law.head_tail, on a slice of the
     source envelope from the planned cut (_Slice).
   - A lead-in pad counts only where edge_plan grants one (a file head).
   - It is not measured (never a pass) on any missing audio, word or plan.
2. pipeline/package.py:
   - hook_onset_for(): a cached wrapper.
   - build(): measures every moment that cleared L-v 2 + CUTTABLE, before the angles.
   - lineup_for(need_onset=True, set by build): a moment OPENS a medley only if its hook onset was measured and
     passed; the proposer's hook gives way to the angle's next one that did.
   - inventory(hook=...): a sealed "hook_onset" row (PASS / FAIL / NOT RUN, with lead_ms, cut_in, why).
3. pipeline/package_pin.py: MEDLEY_GATES gains "hook_onset", so to_pin refuses a medley without it, exactly PASS.
4. tests/package/test_hook_onset.py (new): synthetic envelopes. Breath, then digital zeros, then speech: FAIL. Room
   tone: PASS. No audio, or words outside the window: not measured.
5. tests/package/test_medley.py:
   - the build rig stubs hook_onset_for (no audio);
   - a new test: the proposer's hook gives way, and with none able to open there is no line-up and no paid call;
   - the medley rows include hook_onset.

Check, concretely:
(a) Can a hook with < 80 ms of genuine lead (as the render will measure it) still reach a pin? Look at the slice
    versus the prepared clip, the pad, zeros, and the cut's choice.
(b) Can an unmeasured hook pass or open a line-up?
(c) Does anything change for non-hook clips, or for the full-video and window paths?
(d) Is the hook_onset row really required and sealed for every medley pin, the no-voice path included?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".

