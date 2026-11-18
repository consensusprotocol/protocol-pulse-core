# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_1012
# Branch: pp-selectid
# Generated: 2026-11-18 10:12 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_1012/C1_STEP.diff (209 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 250c4f1..c32b7d6 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -290,6 +290,12 @@ LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
   6 |  LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
   7 |                                     # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
   8 |  LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
   9 | +LY_FLOOR_S = 30.0                  # RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18, standing from the 12:00 build):
  10 | +                                   # a medley's clips may total down to this in the never-empty pass; under
  11 | +                                   # medley_content_range()'s lo the package carries RUNTIME_SHORT; under it, refused
  12 | +LY_SHORT_SPAN_WORDS = 4            # clips too short to land 60 s: the takeaway is asked within this of its longest
  13 | +RUNTIME_SHORT = "This video runs {n} seconds, shorter than usual."   # 148 (1): the flag, NN the factory's estimate
  14 | +_FLOOR = None                      # LY_FLOOR_S while build() runs the never-empty pass (set and cleared there only)
  15 |  
  16 |  
  17 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  18 | @@ -301,6 +307,23 @@ def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  19 |      return round(lo, 2), round(hi, 2)
  20 |  
  21 |  
  22 | +def ly_lo(lo):
  23 | +    """RULINGS 148 (1) / 149: the clips' seconds floor of a line-up: lo, or LY_FLOOR_S under it while the never-empty
  24 | +    pass runs. Only the acceptance reads it; a search's preference keeps the calibrated middle."""
  25 | +    return lo if _FLOOR is None else min(lo, _FLOOR)
  26 | +
  27 | +
  28 | +def runtime_short(pk):
  29 | +    """RULINGS 148 (1) / 149: the plain sentence of a medley sealed under 60 s by the never-empty pass (its clips at
  30 | +    LY_FLOOR_S or more, the factory's estimate under RUNTIME_S[0]): RUNTIME_SHORT with NN the estimate in whole
  31 | +    seconds. None in the clean pass, for any other shape, at 60 s or more, or under the floor."""
  32 | +    est = pk.get("runtime_s_estimate")
  33 | +    if _FLOOR is None or pk.get("shape") != "medley" or not isinstance(est, (int, float)) or isinstance(est, bool) \
  34 | +            or est >= RUNTIME_S[0] or sum(sg["duration_s"] for sg in pk.get("segments") or []) < _FLOOR:
  35 | +        return None
  36 | +    return RUNTIME_SHORT.format(n=int(round(est)))
  37 | +
  38 | +
  39 |  def bridge_budget(content_s):
  40 |      """For a line-up that must carry one bridge (L-y 2), before the bridge is written: (n, (lo, hi)), the largest bridge
  41 |      limit n <= LY_BRIDGE_WORDS words such that ANY bridge of LY_BRIDGE_MIN_WORDS..n words with a takeaway of lo..hi
  42 | @@ -330,7 +353,9 @@ def takeaway_budget(content_s, other=()):
  43 |          lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
  44 |          if lo <= hi:
  45 |              return lo, hi
  46 | -    return None
  47 | +    if _FLOOR is not None and content_s >= _FLOOR and LY_TAKEAWAY_MIN_WORDS <= cap < words_at(RUNTIME_S[0]):
  48 | +        return max(LY_TAKEAWAY_MIN_WORDS, cap - LY_SHORT_SPAN_WORDS), cap     # RULINGS 148 (1) / 149: clips too short
  49 | +    return None                                                               # to land 60 s: the longest takeaway
  50 |  
  51 |  
  52 |  def r4_max_vo_words(content_s, n_vo):
  53 | @@ -1886,8 +1911,8 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  54 |      if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  55 |          return False, "a short clip that is not last"
  56 |      dur = sum(m["duration_s"] for m in segs)
  57 | -    if not lo <= dur <= hi:
  58 | -        return False, f"{dur:.1f} s outside {lo}-{hi} s"
  59 | +    if not ly_lo(lo) <= dur <= hi:                       # RULINGS 148 (1) / 149: the floor in the never-empty pass
  60 | +        return False, f"{dur:.1f} s outside {ly_lo(lo)}-{hi} s"
  61 |      if not stand_ok(segs):                                   # RULING 141 (2): only marked clips' openers flag
  62 |          return False, "the render's STAND_ALONE"
  63 |      return True, "ok"
  64 | @@ -2021,7 +2046,7 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  65 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
  66 |                      continue
  67 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
  68 | -                if not lo <= dur <= hi:
  69 | +                if not ly_lo(lo) <= dur <= hi:               # RULINGS 148 (1) / 149 (the key below: lo's middle)
  70 |                      continue
  71 |                  if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  72 |                      continue
  73 | @@ -3077,7 +3102,7 @@ def cheap_checks(pk, a_by, levels, now):
  74 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
  75 |      det = VF.check_deterministic(segs_v, lines, man, levels)
  76 |      dup = duplicates(pk)
  77 | -    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
  78 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1] or runtime_short(pk) is not None   # 148 (1)
  79 |      r4_res = r4(pk)
  80 |      what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
  81 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
  82 | @@ -3921,7 +3946,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  83 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
  84 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
  85 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
  86 | -                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
  87 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]), short=runtime_short(pk),
  88 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  89 |                                  stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
  90 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
  91 | @@ -4435,7 +4460,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  92 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
  93 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
  94 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
  95 | -                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
  96 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk), short=runtime_short(pk),
  97 |                                              style=HS.lint_lines(pk["lines"]),
  98 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  99 |                                              stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 100 | @@ -4556,7 +4581,12 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 101 |          return out
 102 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 103 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 104 | -    soft = _build(*args, soft=True, **kw)
 105 | +    global _FLOOR
 106 | +    _FLOOR = LY_FLOOR_S                                  # RULINGS 148 (1) / 149: the floor, in this pass only
 107 | +    try:
 108 | +        soft = _build(*args, soft=True, **kw)
 109 | +    finally:
 110 | +        _FLOOR = None
 111 |      info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 112 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 113 |              "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}}   # its record
 114 | @@ -4572,7 +4602,7 @@ def _spent(spend):
 115 |      return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 116 |  
 117 |  
 118 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 119 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 120 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 121 |                seg_flags=None, mids=None):
 122 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 123 | @@ -4619,8 +4649,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 124 |          "duplicate": row(not dup, "code (package.duplicates)"),
 125 |          "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
 126 |                           "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
 127 | -        "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 128 | -                              f"{FINAL_TAIL_S} s tail)"),
 129 | +        "runtime": dict(row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 130 | +                                   f"{FINAL_TAIL_S} s tail)"),
 131 | +                        **({"status": "FLAGGED", "flags": [short]} if short and rt_ok else {})),   # RULINGS 148 (1) / 149
 132 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 133 |          "context_a": dict(row(bool(a_rows) and (not a_codes or soft_a),
 134 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 135 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 136 | index 67a0d4c..6400783 100644
 137 | --- a/pipeline/package_pin.py
 138 | +++ b/pipeline/package_pin.py
 139 | @@ -46,7 +46,9 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 140 |                          "pbx_exception",                   # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 141 |                          "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
 142 |                          #   HARD)
 143 | -                        "graphics"})                       # RULING 146 (1): the show's own graphics, 16:9 only
 144 | +                        "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 145 | +                        "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 146 | +#   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
 147 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 148 |  REVIEW_FLAGS_MAX = 3
 149 |  PBX_EXCEPTION_CAP = 5   # RULING 147 (orchestrator 08:20 ET Nov 18): the excepted pin's cap (the exception line itself
 150 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 151 | index 5f8d8c9..e7d50a8 100644
 152 | --- a/tests/package/test_ruling_137.py
 153 | +++ b/tests/package/test_ruling_137.py
 154 | @@ -648,6 +648,54 @@ class TestRuling144TheOneException(unittest.TestCase):
 155 |              PP.WINDOW_H = saved
 156 |  
 157 |  
 158 | +class TestRuling148RuntimeFloor(unittest.TestCase):
 159 | +    """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
 160 | +    medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
 161 | +    its runtime gate row FLAGGED 'This video runs NN seconds, shorter than usual.' (NN the factory's estimate). Under
 162 | +    30 s nothing seals; the clean pass is unchanged."""
 163 | +
 164 | +    def run_rig(self, ms, never_empty):
 165 | +        import test_medley as TM
 166 | +        ids = [m["moment_id"] for m in ms]
 167 | +        r = TM.Rig(ms, ids, [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 168 | +                   follow_up={"angles": [TM.angle(ids, ids[0])]})
 169 | +        r.build_kw = {"never_empty": never_empty}
 170 | +        return r.run()
 171 | +
 172 | +    def test_a_short_lineup_seals_flagged_in_the_never_empty_pass_only(self):
 173 | +        from test_moments import pm
 174 | +        ms = [pm("h", "A", 11.0), pm("x", "B", 11.5), pm("y", "C", 11.4)]          # 33.9 s: under 36.7, over 30
 175 | +        self.assertIsNone(self.run_rig(ms, False)["package"])                       # the clean pass: unchanged
 176 | +        pk = self.run_rig(ms, True)["package"]
 177 | +        self.assertIsNotNone(pk)
 178 | +        est = pk["runtime_s_estimate"]
 179 | +        self.assertLess(est, PK.RUNTIME_S[0])
 180 | +        self.assertEqual((pk["gates"]["runtime"]["status"], pk["gates"]["runtime"]["flags"]),
 181 | +                         ("FLAGGED", [f"This video runs {int(round(est))} seconds, shorter than usual."]))
 182 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 183 | +        self.assertIsNone(PK._FLOOR)                                                # cleared after the pass
 184 | +
 185 | +    def test_under_the_floor_nothing_seals(self):
 186 | +        from test_moments import pm
 187 | +        ms = [pm("h", "A", 9.0), pm("x", "B", 9.5), pm("y", "C", 9.4)]              # 27.9 s
 188 | +        self.assertIsNone(self.run_rig(ms, True)["package"])
 189 | +
 190 | +    def test_the_takeaway_budget_and_the_sentence(self):
 191 | +        b40 = PK.takeaway_budget(40.0)
 192 | +        self.assertIsNone(PK.takeaway_budget(33.9))                                 # outside the pass: no length
 193 | +        pk = {"shape": "medley", "runtime_s_estimate": 57.19, "segments": [{"duration_s": 20.0}, {"duration_s": 13.9}]}
 194 | +        self.assertIsNone(PK.runtime_short(pk))                                     # the clean pass: no sentence
 195 | +        with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):
 196 | +            lo, hi = PK.takeaway_budget(33.9)
 197 | +            self.assertEqual((hi, lo), (PK.LY_TAKEAWAY_MAX_WORDS, PK.LY_TAKEAWAY_MAX_WORDS - PK.LY_SHORT_SPAN_WORDS))
 198 | +            self.assertIsNone(PK.takeaway_budget(29.0))                             # under the floor
 199 | +            self.assertEqual(PK.takeaway_budget(40.0), b40)                          # a full line-up: unchanged
 200 | +            self.assertEqual(PK.runtime_short(pk), "This video runs 57 seconds, shorter than usual.")
 201 | +            for bad in (dict(pk, runtime_s_estimate=60.0), dict(pk, shape="vo"),
 202 | +                        dict(pk, segments=[{"duration_s": 29.9}])):
 203 | +                self.assertIsNone(PK.runtime_short(bad), bad)
 204 | +
 205 | +
 206 |  class TestRuling146(unittest.TestCase):
 207 |      """RULING 146 (orchestrator 07:55 ET Nov 18), the never-empty pass: (1) the source's own on-screen graphics (a ticker,
 208 |      a lower third, a bug) are SOFT in a package sealed 16:9 only, flagged in the ruling's words; (2) G17a's quiet before
 209 | 
```

---

pp-selectid: RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18, standing from the 12:00 ET build): "the 30 s floor with
a 'runs short' flag up to 36.7 s". A medley's clips may total LY_FLOOR_S (30.0 s) or more; under the calibrated floor
(medley_content_range()'s lo, 36.7 s: one 20-word takeaway landing 60 s) the package carries the flag "This video runs NN
seconds, shorter than usual." (NN = the factory's runtime estimate, whole seconds); under 30 s still refused.
SCOPE: the NEVER-EMPTY pass only (a flag belongs to it; the clean pass is unchanged). build() sets the module's _FLOOR to
LY_FLOOR_S around _build(soft=True) and clears it in a finally (the soft pass runs after the clean pass, in sequence).
THE CHANGE (pipeline/package.py, pipeline/package_pin.py):
1. ly_lo(lo): lo, or min(lo, _FLOOR) in the pass. Used ONLY by the two acceptance checks (lineup_ok's seconds test,
   lineup_for's); lineup_for's preference key keeps the calibrated middle (lo + hi) / 2. The angle writer's prompt
   keeps the calibrated lo/hi (unchanged text: cached replies stay valid).
2. takeaway_budget: when neither LY_AIM_S nor 60-70 s can be landed, in the pass, with content_s >= _FLOOR and
   LY_TAKEAWAY_MIN_WORDS <= cap < the words that would land 60 s: (max(MIN, cap - 4), cap), the longest takeaway house
   style and R4 allow. Full line-ups: unchanged (tested). bridge_budget follows (it calls takeaway_budget).
3. runtime_short(pk): the sentence, only with _FLOOR set, shape "medley", a numeric estimate under RUNTIME_S[0] (60 s),
   and the clips' seconds >= _FLOOR; else None. cheap_checks: rt_ok = 60-70 s OR runtime_short(pk) (so no RUNTIME
   violation / rewrite for an accepted short medley). inventory(short=runtime_short(pk)) at both call sites: the
   "runtime" gate row becomes {"status": "FLAGGED", "flags": [sentence], ...row} (rt_ok must hold).
4. package_pin.SOFT_GATES += "runtime" (the integrator's check_pin_only reads SOFT_GATES live; its render's G5 / R4
   follow this sealed FLAGGED row, its batch 115). The flag counts toward the cap (content_flags), as ruled.
TESTS (test_ruling_137.TestRuling148RuntimeFloor, the real build() on the stubbed rig): 33.9 s of clips: the clean pass
seals nothing, the never-empty pass seals with runtime FLAGGED and the exact sentence, gate_problems none, _FLOOR cleared;
27.9 s: nothing; the takeaway budget at 33.9 / 29.0 / 40.0 s with and without the floor; the sentence's refusals.
Mutations: 7 of 7 killed (no floor in the acceptance; no short budget; no sentence; build() never sets the floor;
runtime not a soft gate; the row never flagged; rt_ok ignoring the floor); control passes.
PLEASE CHECK: (1) can the floor leak into the clean pass or a later build (the global)? (2) can a package under 30 s,
over 70 s, or of another shape seal through it? (3) the takeaway budget's fallback; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
