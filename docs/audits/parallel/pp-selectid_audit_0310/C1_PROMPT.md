# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0310
# Branch: pp-selectid
# Generated: 2026-11-13 03:08 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0310/C1_STEP.diff (260 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 74ea177c..22604c32 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -553,7 +553,31 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
   6 |      return out
   7 |  
   8 |  
   9 | -def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False):
  10 | +def stand_alone_check(segs):
  11 | +    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) on one line-up, at the pin stage
  12 | +    (the integrator held pin d2657bbe on it, 03:00 ET Nov 13): the hook, then the clips in play order (clip_01, ...), the
  13 | +    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and NO clip scorer.
  14 | +    The render's scorer is a local model on GPU0, which this stage may not use, so a clip that opens on a conjunction or
  15 | +    a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue."""
  16 | +    import stand_alone as SA
  17 | +    edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  18 | +           "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  19 | +                     for i, m in enumerate(segs[1:], 1)]}
  20 | +    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  21 | +
  22 | +
  23 | +def no_role_on_screen(m):
  24 | +    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  25 | +    opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  26 | +    it), else None. build() leaves such moments out before any vendor call."""
  27 | +    import stand_alone as SA
  28 | +    c_ok, c_why = SA.opener("clip", m.get("text"))
  29 | +    h_ok, h_why = SA.opener("hook", m.get("text"))
  30 | +    return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
  31 | +
  32 | +
  33 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  34 | +               need_stand_alone=False):
  35 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  36 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  37 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  38 | @@ -563,7 +587,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  39 |      seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
  40 |      ONE channel may give two clips, from two different videos. need_onset (build() sets it): a moment opens the
  41 |      medley only if its hook onset was measured and passed (hook_onset_for, G17a at the pin stage); the proposer's hook
  42 | -    gives way to the angle's next one that did. None if impossible."""
  43 | +    gives way to the angle's next one that did. need_stand_alone (build() sets it): every line-up must pass the render's
  44 | +    STAND_ALONE (stand_alone_check). None if impossible."""
  45 |      lo, hi = crange or medley_content_range()
  46 |      pos = {m: i for i, m in enumerate(angle["moments"])}
  47 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
  48 | @@ -588,6 +613,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  49 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
  50 |                  if not lo <= dur <= hi:
  51 |                      continue
  52 | +                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  53 | +                    continue
  54 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  55 |                  if best is None or key > best[0]:
  56 |                      best = (key, [h] + order)
  57 | @@ -991,15 +1018,19 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  58 |      t0 = time.time()
  59 |      usd0 = _spent(spend)
  60 |      ms, why = usable(moments, ctx, delivered, optout)
  61 | +    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  62 | +    ms = [m for m in ms if m["moment_id"] not in no_role]
  63 |      wv, wf = _writers(router)
  64 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
  65 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  66 |      levels = current_levels(sources.values(), ctx)
  67 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
  68 | +           "no_role": no_role,
  69 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  70 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  71 |             "package": None}
  72 | -    log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  73 | +    log(f"  {len(ms)} usable ({len(no_role)} more left out: they open on a conjunction or reply fragment, which the "
  74 | +        f"render's STAND_ALONE fails with no clip scorer), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  75 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  76 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
  77 |          return out
  78 | @@ -1144,7 +1175,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  79 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
  80 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
  81 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
  82 | -                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
  83 | +                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  84 | +                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
  85 |          import package_pin
  86 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
  87 |          if problems:
  88 | @@ -1167,9 +1199,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  89 |              while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
  90 |                  if over_budget(ai):
  91 |                      break
  92 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True), None
  93 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
  94 | +                                             need_stand_alone=True), None
  95 |                  if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
  96 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True)
  97 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
  98 | +                                     need_stand_alone=True)
  99 |                      if segs is not None:
 100 |                          rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 101 |                                 if sum(m["channel_id"] == c for m in segs) > 1]
 102 | @@ -1319,7 +1353,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 103 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 104 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 105 |                                              style=HS.lint_lines(pk["lines"]),
 106 | -                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 107 | +                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 108 | +                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 109 |                      if not ok_c:
 110 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 111 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 112 | @@ -1378,12 +1413,14 @@ def _spent(spend):
 113 |  
 114 |  
 115 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 116 | -              hook=None):
 117 | +              hook=None, stand=None):
 118 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 119 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 120 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 121 |      (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
 122 | -    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin."""
 123 | +    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin.
 124 | +    stand: stand_alone_check() of the package's segments in play order -> the "stand_alone" row (the render's
 125 | +    STAND_ALONE at the pin stage, required for a medley); None leaves it out, which refuses the pin."""
 126 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 127 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 128 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 129 | @@ -1443,4 +1480,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 130 |                                     "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
 131 |                                 lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 132 |             if hook is not None else {}),
 133 | +        **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 134 | +                                    "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 135 | +                                rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 136 | +                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []])}
 137 | +           if stand is not None else {}),
 138 |      }
 139 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 140 | index d975d12f..6c15c3b0 100644
 141 | --- a/pipeline/package_pin.py
 142 | +++ b/pipeline/package_pin.py
 143 | @@ -26,9 +26,10 @@ from datetime import datetime, timezone
 144 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 145 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 146 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 147 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset")   # hook_onset: G17a at the pin stage, after
 148 | -                                                                      # batch pin #1's render hold (01:39 ET Nov 13)   # L-y (20:30): the clips-alone verdict, the medley's shape;
 149 | -                                                         # ruling 6 (22:40): PBX's copy rules on every line
 150 | +# L-y (20:30): the clips-alone verdict and the medley's shape; ruling 6 (22:40): PBX's copy rules on every line;
 151 | +# hook_onset: G17a at the pin stage, after batch pin #1's render hold (01:39 ET Nov 13); stand_alone: the render's
 152 | +# STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 153 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone")
 154 |  
 155 |  
 156 |  def required_gates(pk):
 157 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 158 | index 6501f65f..85412d49 100644
 159 | --- a/tests/package/test_medley.py
 160 | +++ b/tests/package/test_medley.py
 161 | @@ -368,14 +368,15 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 162 |  
 163 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 164 |          pk = self.build()
 165 | -        self.assertEqual(package_pin.required_gates(pk)[-4:], ("medley", "ly_shape", "house_style", "hook_onset"))
 166 | +        self.assertEqual(package_pin.required_gates(pk)[-5:], ("medley", "ly_shape", "house_style", "hook_onset",
 167 | +                                                               "stand_alone"))
 168 |          pk["gates"] = self.gates(pk)
 169 |          pin = package_pin.to_pin(spk(pk), "test")
 170 |          mp = pin["moments_package"]
 171 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 172 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 173 |          self.assertEqual(mp["shape"], "medley")
 174 | -        for missing in ("medley", "ly_shape", "house_style", "hook_onset"):
 175 | +        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"):
 176 |              g = self.gates(pk)
 177 |              g.pop(missing)
 178 |              with self.assertRaises(package_pin.PinRefused):
 179 | @@ -643,6 +644,70 @@ class TestBuildLoop(unittest.TestCase):
 180 |          self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")
 181 |  
 182 |  
 183 | +class TestStandAloneAtThePinStage(unittest.TestCase):
 184 | +    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) at the pin stage, after the
 185 | +    integrator held pin d2657bbe on it (03:00 ET Nov 13): no clip scorer here (it is a local model on GPU0), so a clip
 186 | +    opening on a conjunction or reply fragment fails closed, and no line-up the render would hold is sealed."""
 187 | +
 188 | +    HOOK = ("Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin "
 189 | +            "wins, open source wins.")
 190 | +    BUT1 = "But we have very rarely in Bitcoin's history seen six negative weeks back to back. I think that was six."
 191 | +    BUT2 = ("But then if someone doesn't understand Bitcoin and you drop 25 % of their portfolio in Bitcoin and Bitcoin "
 192 | +            "goes down 50%. You get fired and they sell their Bitcoin.")
 193 | +
 194 | +    def test_it_gives_the_renders_verdicts_on_the_held_pin_d2657bbe(self):
 195 | +        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": self.BUT1}, {"text": self.BUT2}])
 196 | +        self.assertFalse(r["ok"])
 197 | +        self.assertEqual([(x["segment"], x["pass"]) for x in r["rows"]],     # the render's run_log.txt lines 47-49
 198 | +                         [("hook", True), ("clip_01", False), ("clip_02", False)])
 199 | +        self.assertIn("clip opens on 'but'", r["rows"][1]["opener"]["why"])
 200 | +        self.assertEqual(r["subject"], ["bitcoin", "btc"])
 201 | +
 202 | +    def test_a_moment_opening_on_a_conjunction_or_reply_fragment_has_no_role(self):
 203 | +        for t in (self.BUT1, "And Bitcoin is money.", "Yeah, Bitcoin is money.", "Well, Bitcoin is money."):
 204 | +            self.assertIn("STAND_ALONE", PK.no_role_on_screen({"text": t}) or "", t)
 205 | +        for t in ("I think Bitcoin is money.", "Bitcoin is money.", "It is Bitcoin."):   # a pronoun opens a clip
 206 | +            self.assertIsNone(PK.no_role_on_screen({"text": t}), t)
 207 | +
 208 | +    def test_no_line_up_holds_a_clip_the_render_would_hold(self):
 209 | +        by = {m["moment_id"]: m for m in (dict(pm("h", "A", 12.0), text=self.HOOK), dict(pm("b", "B", 14.0), text=self.BUT1),
 210 | +                                          dict(pm("x", "C", 13.0), text="Bitcoin x."),
 211 | +                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
 212 | +        a = angle(["h", "b", "x", "y"], "h")
 213 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by)], ["h", "b", "x"])     # the old pick
 214 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_stand_alone=True)], ["h", "x", "y"])
 215 | +        no_subject = dict(by, y=dict(by["y"], text="Gold is money."), x=dict(by["x"], text="Gold x."))
 216 | +        self.assertIsNone(PK.lineup_for(a, no_subject, need_stand_alone=True))   # topical: no clip names Bitcoin
 217 | +
 218 | +    def test_a_pronoun_hook_gives_way_to_the_next_hook(self):
 219 | +        by = {m["moment_id"]: m for m in (dict(pm("p", "A", 12.0), text="It is the hardest money. Bitcoin is."),
 220 | +                                          dict(pm("h", "B", 12.0), text=self.HOOK), dict(pm("x", "C", 14.0), text="Bitcoin x."),
 221 | +                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
 222 | +        a = angle(["p", "h", "x", "y"], "p")
 223 | +        self.assertEqual(PK.lineup_for(a, by)[0]["moment_id"], "p")
 224 | +        self.assertEqual(PK.lineup_for(a, by, need_stand_alone=True)[0]["moment_id"], "h")
 225 | +
 226 | +    def test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row(self):
 227 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 228 | +              dict(pm("b", "E", 13.0), text=self.BUT1)]
 229 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 230 | +        out = rig.run()
 231 | +        self.assertEqual(list(out["no_role"]), ["b"])
 232 | +        self.assertIn("clip opens on 'but'", out["no_role"]["b"])
 233 | +        self.assertFalse(any("id=b " in p for role, p in rig.prompts if role == "angle_write"))
 234 | +        g = out["package"]["gates"]["stand_alone"]
 235 | +        self.assertEqual(g["status"], "PASS")
 236 | +        self.assertEqual(len(g["rows"]), 3)
 237 | +
 238 | +    def test_the_row_fails_and_the_pin_is_refused_when_a_clip_opens_on_a_conjunction(self):
 239 | +        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": "Bitcoin x."}, {"text": self.BUT2}])
 240 | +        self.assertFalse(r["ok"])
 241 | +        pk = {"shape": "medley"}
 242 | +        gates = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
 243 | +        gates["stand_alone"] = {"status": "PASS" if r["ok"] else "FAIL", "by": "x", "replayed": False, "n": 1}
 244 | +        self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 245 | +
 246 | +
 247 |  class TestNoVoiceRealGates(unittest.TestCase):
 248 |      """Audit 2240 C2 (glm N8): a no-voice package through the REAL VO-fidelity and context-integrity decisions (canned
 249 |      model replies, no stubbed gate): every required row, the medley rows included, exactly PASS, and the pin is
 250 | @@ -692,7 +757,8 @@ class TestNoVoiceRealGates(unittest.TestCase):
 251 |          coh = dict(med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 252 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 253 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 254 | -                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"})
 255 | +                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"},
 256 | +                                   stand=PK.stand_alone_check(pk["segments"]))
 257 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 258 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 259 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 260 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
"pins"; another session (the integrator) renders them with the main pipeline, whose validate stage runs extra checks.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why this change: the integrator HELD pin d2657bbe at its validate stage (03:00 ET Nov 13), before any render, on the
main pipeline's STAND_ALONE check (main pipeline/run_fresh.py stage_validate -> stand_alone.check_edl):
  STAND_ALONE hook:    [PASS] opener: opens on 'bitcoin' | topic: names the subject (bitcoin)
  STAND_ALONE clip_01: [FAIL] opener: clip opens on 'but'; the clip scorer does not affirm it stands alone (3.0, fault other)
  STAND_ALONE clip_02: [FAIL] opener: clip opens on 'but'; the clip scorer does not affirm it stands alone (3.0, fault other)
This branch's pin-stage gates did not run that check. pipeline/stand_alone.py on this branch is byte-identical to the
main pipeline's at the render's commit. In the render, check_edl gets rate = a CLIP SCORER that is a local model on
the GPU (Ollama, GPU0); this branch's session may not use any GPU. check_edl with rate=None fails closed: a clip that
opens on a conjunction or a reply fragment FAILS when no scorer verdict is available. The render's subject for a
pinned moments package labelled 'bitcoin' is stand_alone.subject_terms("", "bitcoin") = {bitcoin, btc}.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (adding a stricter pre-check is allowed);
- the pin stage must never seal a line-up that the render's own checks would hold.

The change:
1. pipeline/package.py:
   - stand_alone_check(segs): stand_alone.check_edl on the line-up (hook, then clip_01.. in play order), rate=None,
     subject {bitcoin, btc}. With no scorer, a conjunction or reply-fragment clip opener fails closed: stricter than
     the render, which may let its scorer affirm such a clip.
   - no_role_on_screen(m): a moment whose opener fails BOTH as a clip (no scorer) and as a hook (stand_alone.opener)
     can take no place in any line-up. build() leaves such moments out right after usable(), before step A or any
     other vendor call, and records them in out["no_role"] with the reason.
   - lineup_for(..., need_stand_alone=False): when True, a candidate line-up that fails stand_alone_check is skipped
     (the proposer's hook gives way to the next hook, as with need_onset). build() passes need_stand_alone=True at
     both call sites.
   - inventory(..., stand=None): a sealed "stand_alone" gate row (PASS only when check_edl's ok is True), with the
     per-segment rows as evidence. Both inventory call sites pass stand_alone_check of the package's segments.
2. pipeline/package_pin.py: MEDLEY_GATES gains "stand_alone", so write_pin refuses a medley without a PASS row. The
   integrator's recompute (check_pin_only) checks REQUIRED_GATES only, so older pins still recompute.
3. tests/package/test_medley.py:
   - the held pin's three texts give the render's PASS / FAIL / FAIL;
   - the no-role rule: conjunction and reply-fragment openers have no role; pronoun openers can still be clips;
   - lineup_for never picks a "But" clip with need_stand_alone; a line-up with no clip naming Bitcoin is refused;
   - a pronoun hook gives way;
   - build() leaves a "But" moment out before the angle step and seals a PASS row;
   - a FAIL row refuses the pin;
   - the two existing tests are updated for the new required row.

Check in particular:
- that stand_alone_check reproduces the render's check_edl call exactly (segment order, labels clip_01..,
  rate=None, subject), and that nothing here can PASS a line-up the render would hold;
- that no_role_on_screen drops ONLY moments that can be neither a clip nor a hook under check_edl with no scorer
  (a pronoun opener must stay: it fails as a hook but passes as a clip);
- the gate row: unmeasured or failing never PASS; a missing row refuses the pin;
- anything that changes what an EXISTING check accepts.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

