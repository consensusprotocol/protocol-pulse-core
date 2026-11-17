# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1217
# Branch: pp-selectid
# Generated: 2026-11-17 12:17 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1217/C1_STEP.diff (323 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f26688d..5b9ed6d 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -96,9 +96,32 @@ CLIP_PLACE = {"hook": "The opening clip", "clip_01": "The second clip", "clip_02
   6 |                "clip_03": "The fourth clip", "clip_04": "The fifth clip"}
   7 |  
   8 |  
   9 | +# RULING 137 stage 2a (line 1, 12:12 ET, default SOFT): CUTTABLE's sentence-edge part is soft. Only these two reasons
  10 | +# of transcript_truth.edges (the sentence running on at a word boundary) flag; every other edge failure stays HARD.
  11 | +EDGE_SOFT = {"in": "the recogniser runs on into the clip", "out": "the recogniser's sentence continues past the clip"}
  12 | +EDGE_WORDS = {"EDGE_IN": "the checker heard the sentence run on into the clip's first word, so it may start "
  13 | +                         "mid-sentence",
  14 | +              "EDGE_OUT": "the checker heard the sentence carry on past the clip's last word, so it may end "
  15 | +                          "mid-sentence"}
  16 | +
  17 | +
  18 |  def flag_sentence(label, channel, code):
  19 |      """RULING 138 (3): one flag as PBX reads it: the clip's place and channel, then what the checker doubted."""
  20 | -    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): {STEP_A_SOFT[code]}."
  21 | +    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): " \
  22 | +           f"{STEP_A_SOFT.get(code) or EDGE_WORDS[code]}."
  23 | +
  24 | +
  25 | +def soft_edges(t):
  26 | +    """RULING 137 stage 2a: a moment's CUTTABLE failure is soft only when its words match (law L-v 2 ok, measured, no
  27 | +    error) and EVERY failing edge failed for the sentence running on at a word boundary (EDGE_SOFT); a word not found,
  28 | +    a trimmed word, an unmeasured edge stay hard. -> ["EDGE_IN" / "EDGE_OUT"] or None."""
  29 | +    if not isinstance(t, dict) or t.get("error") or t.get("ok") is not True or not isinstance(t.get("edges"), dict):
  30 | +        return None
  31 | +    e = t["edges"]
  32 | +    bad = [k for k in ("in", "out") if (e.get(k) or {}).get("ok") is not True]
  33 | +    if not bad or not all(str((e.get(k) or {}).get("why") or "").startswith(EDGE_SOFT[k]) for k in bad):
  34 | +        return None
  35 | +    return ["EDGE_" + k.upper() for k in bad]
  36 |  FLAGGED_DAY_MAX = 2
  37 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
  38 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
  39 | @@ -490,15 +513,39 @@ def is_held(why):
  40 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
  41 |  
  42 |  
  43 | +def soft_codes(f):
  44 | +    """RULING 137: a step-A refusal's codes when every one is SOFT (STEP_A_SOFT) and it is a refusal, not a held
  45 | +    moment (ruling 102), else None (a hard code, a hold, or no refusal keeps it as it was)."""
  46 | +    return sorted({str(c) for c in f}) if f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f) else None
  47 | +
  48 | +
  49 | +def add_flags(m, codes):
  50 | +    """RULING 137: the moment carries every soft step-A code any screen gave it (each becomes one plain sentence)."""
  51 | +    m["step_a_flags"] = sorted(set(m.get("step_a_flags") or []) | set(codes))
  52 | +    return m
  53 | +
  54 | +
  55 | +def soft_second(cleared, a_two, off_fail):
  56 | +    """RULING 137 STAGE 2a: the moments the SECOND family refused for soft codes only stay, flagged (the same step-A
  57 | +    rule as the first screen's: soft_codes). -> {moment_id: codes}; the moments in cleared carry them."""
  58 | +    out = {}
  59 | +    for mid, m in cleared.items():
  60 | +        c = soft_codes(off_fail.get(mid)) if mid not in a_two else None
  61 | +        if c:
  62 | +            out[mid] = c
  63 | +            add_flags(m, c)
  64 | +    return out
  65 | +
  66 | +
  67 |  def soft_step_a(ms, a_by, fails):
  68 |      """RULING 137 STAGE 1: the moments step A refused for SOFT codes only (STEP_A_SOFT): a step-A answer on file, a
  69 |      refusal (never a held one, ruling 102), and every code soft (one hard code keeps it out). -> {moment_id: a copy of
  70 |      the moment carrying "step_a_flags", its codes}."""
  71 |      out = {}
  72 |      for m in ms:
  73 | -        f = fails.get(m["moment_id"])
  74 | -        if m["moment_id"] in a_by and f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f):
  75 | -            out[m["moment_id"]] = dict(m, step_a_flags=sorted({str(c) for c in f}))
  76 | +        c = soft_codes(fails.get(m["moment_id"])) if m["moment_id"] in a_by else None
  77 | +        if c:
  78 | +            out[m["moment_id"]] = dict(m, step_a_flags=c)
  79 |      return out
  80 |  
  81 |  
  82 | @@ -3223,7 +3270,16 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  83 |          mid: "PASS" if cut_ok(t) else ("NOT MEASURED: " + t["error"] if t.get("error") else
  84 |                                         "L-v 2 FAIL" if not t.get("ok") else "not cuttable at an edge (ruling C / 7)")
  85 |          for mid, t in tru.items()}
  86 | -    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
  87 | +    cut_soft = {mid: e for mid in cleared if not cut_ok(tru.get(mid) or {})       # RULING 137 stage 2a: a sentence
  88 | +                for e in [soft_edges(tru.get(mid) or {})] if e} if soft else {}    # edge at a word boundary flags
  89 | +    for mid, e in cut_soft.items():
  90 | +        cleared[mid]["edge_flags"] = e
  91 | +    if cut_soft:
  92 | +        out["prescreen"]["soft_edges"] = cut_soft
  93 | +        log(f"  RULING 137 NEVER EMPTY (stage 2a): {len(cut_soft)} moment(s) whose words match fail CUTTABLE only at a "
  94 | +            f"sentence edge (the recogniser runs on at a word boundary) stay, flagged: "
  95 | +            + ", ".join(f"{mid[:8]} {e}" for mid, e in cut_soft.items()))
  96 | +    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {}) or mid in cut_soft}
  97 |      out["prescreen"]["cuttable"] = len(cleared)
  98 |      log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
  99 |      hk = {}
 100 | @@ -3320,7 +3376,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 101 |          log(f"  RULING 102: held for this build (no leg answered; retried next build): {len(h['first'])} at the first "
 102 |              f"screen, {len(h['second'])} at the second {h['second']}; the local judge (ruling 87's last resort) gave "
 103 |              f"{len(out['prescreen']['last_resort_87'])} step-A verdict(s): {sorted(out['prescreen']['last_resort_87'])}")
 104 | -    cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
 105 | +    soft_two = soft_second(cleared, a_two, off_fail) if soft else {}   # RULING 137 stage 2a: flagged, kept
 106 | +    if soft_two:
 107 | +        out["prescreen"]["soft_second"] = soft_two
 108 | +        log(f"  RULING 137 NEVER EMPTY (stage 2a): {len(soft_two)} moment(s) the second family refused for soft codes "
 109 | +            f"only stay, flagged: " + ", ".join(f"{mid[:8]} {c}" for mid, c in soft_two.items()))
 110 | +    cleared = {mid: m for mid, m in cleared.items() if mid in a_two or mid in soft_two}
 111 |      log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
 112 |          f"a verdict off it exists) ({time.time() - t0:.0f} s)")
 113 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 114 | @@ -3629,7 +3690,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 115 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 116 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 117 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 118 | -                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]})   # RULING 138 (3)
 119 | +                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 120 | +                                seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get("step_a_flags")
 121 | +                                           for sg in pk["segments"]},                          # RULING 137 stage 2a
 122 | +                                mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 123 |          import package_pin
 124 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 125 |          if problems:
 126 | @@ -3944,6 +4008,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 127 |                              if got_a.get(mid) is not None and not fails_a.get(mid):
 128 |                                  a_by[mid] = got_a[mid]
 129 |                                  a_two.setdefault(mid, []).append(got_a[mid])
 130 | +                            elif soft and got_a.get(mid) is not None and soft_codes(fails_a.get(mid)):   # RULING 137
 131 | +                                add_flags(m, soft_codes(fails_a[mid]))       # stage 2a: a soft refusal off the writer
 132 | +                                a_by[mid] = got_a[mid]                        # stays, flagged
 133 |                              else:                              # no verdict off the writers is never a pass (L-m)
 134 |                                  bad[mid] = list(fails_a.get(mid) or [f"{HELD}: no verdict off the writers (law L-m);"
 135 |                                                                       f" held for this build, retried next build"])
 136 | @@ -4114,7 +4181,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 137 |                                              value=val,                       # ruling 91: the takeaway earned its place
 138 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 139 |                                              soft=soft, who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 140 | -                                                            for sg in pk["segments"]})
 141 | +                                                            for sg in pk["segments"]},
 142 | +                                            seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get(
 143 | +                                                "step_a_flags") for sg in pk["segments"]},    # RULING 137 stage 2a
 144 | +                                            mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 145 |                      if not ok_c:
 146 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 147 |                          cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 148 | @@ -4225,8 +4295,9 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 149 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 150 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 151 |      soft = _build(*args, soft=True, **kw)
 152 | -    info = {"stage": 1, "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 153 | -            "soft_back": (soft.get("prescreen") or {}).get("soft_back")}
 154 | +    info = {"stage": "2a", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 155 | +            "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 156 | +            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
 157 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 158 |  
 159 |  
 160 | @@ -4240,7 +4311,8 @@ def _spent(spend):
 161 |  
 162 |  
 163 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 164 | -              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None):
 165 | +              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 166 | +              seg_flags=None, mids=None):
 167 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 168 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 169 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 170 | @@ -4262,9 +4334,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 171 |          return None if any(not isinstance(x, bool) for x in values) else any(values)
 172 |      det = fid["deterministic"]
 173 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 174 | +    lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
 175 | +    edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
 176 | +               if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
 177 |      a_rows = list((a_by or {}).values())
 178 | -    a_codes = sorted({str(c) for a in a_rows for c in CI.a_failures(a)})   # RULING 137 stage 1: step A's codes; in the
 179 | -    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # never-empty pass, soft ones FLAG
 180 | +    lab_codes = {lb: sorted({str(c) for c in CI.a_failures(a)} | set((seg_flags or {}).get(lb) or []))   # RULING 137:
 181 | +                 for lb, a in (a_by or {}).items()}       # each clip's step-A codes, its verdict's and every screen's soft
 182 | +    a_codes = sorted({c for cs in lab_codes.values() for c in cs})   # ones (stage 2a); in the never-empty pass, soft
 183 | +    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # ones FLAG
 184 |      return {
 185 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
 186 |          "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 187 | @@ -4281,8 +4358,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 188 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 189 |                                n=len(a_rows)),
 190 |                            **({"status": "FLAGGED",            # RULING 137 stage 1; 138 (3): a sentence a clip
 191 | -                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb, a in (a_by or {}).items()
 192 | -                                        for c in sorted({str(x) for x in CI.a_failures(a)})]}
 193 | +                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb in (a_by or {})
 194 | +                                        for c in lab_codes[lb]]}
 195 |                               if soft_a and len(a_rows) >= 1 else {}),
 196 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 197 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 198 | @@ -4299,10 +4376,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 199 |          "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
 200 |                             rep(t.get("replayed") for t in truth.values()), n=len(truth),
 201 |                             measured=all("error" not in t for t in truth.values())),
 202 | -        "cuttable": row(all((t.get("edges") or {}).get("cuttable") is True for t in truth.values()),
 203 | +        "cuttable": dict(row(all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t))
 204 | +                                 for t in truth.values()),
 205 |                          "transcript_truth.edges: the independent recogniser's sentence boundary at every IN and OUT "
 206 |                          "(orchestrator 06:45 ruling C / 7)", rep(t.get("replayed") for t in truth.values()), n=len(truth),
 207 |                          measured=all("edges" in t for t in truth.values())),
 208 | +                         **({"status": "FLAGGED", "flags": edge_fl}       # RULING 137 stage 2a: a sentence edge
 209 | +                            if edge_fl and truth and all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t)
 210 | +                                                         for t in truth.values()) else {})),
 211 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 212 |                            **votes_of(coh)),
 213 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 214 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 215 | index 5fb02f2..180aba9 100644
 216 | --- a/pipeline/package_pin.py
 217 | +++ b/pipeline/package_pin.py
 218 | @@ -34,7 +34,9 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 219 |  # RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): a SOFT gate scores and FLAGS. Its row may say "FLAGGED"
 220 |  # with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 221 |  # (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 222 | -SOFT_GATES = frozenset({"context_a"})
 223 | +SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 224 | +                        "cuttable"})                       # stage 2a: a sentence edge at a word boundary (L-v 2's
 225 | +#   word check, "second_pass", stays HARD)
 226 |  REVIEW_FLAGS_MAX = 3
 227 |  
 228 |  
 229 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 230 | index bc71226..c322e28 100644
 231 | --- a/tests/package/test_ruling_137.py
 232 | +++ b/tests/package/test_ruling_137.py
 233 | @@ -114,8 +114,9 @@ class TestTheTwoPasses(unittest.TestCase):
 234 |          none, sealed = {"package": None, "why_none": "x"}, {"package": {"p": 1}}
 235 |          calls, out = self.run_build(sealed, sealed, never_empty=True)
 236 |          self.assertEqual((calls, "never_empty" in out), ([False], False))            # a clean package: one pass
 237 | -        calls, out = self.run_build(none, sealed, never_empty=True)
 238 | +        calls, out = self.run_build(none, dict(sealed, prescreen={"soft_back": {}}), never_empty=True)
 239 |          self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
 240 | +        self.assertEqual(out["never_empty"]["soft_record"]["prescreen"], {"soft_back": {}})   # the soft pass's record
 241 |          calls, out = self.run_build(none, dict(none, why_none="y"), never_empty=True)
 242 |          self.assertEqual((calls, out["package"], out["never_empty"]["soft_why_none"]), ([False, True], None, "y"))
 243 |          self.assertEqual(self.run_build(none, sealed)[0], [False])                   # never_empty off: as before
 244 | @@ -134,6 +135,78 @@ class TestTheTwoPasses(unittest.TestCase):
 245 |          self.assertEqual(calls, [["lineups", "log"], ["lineups", "log", "soft"]])
 246 |  
 247 |  
 248 | +class TestStage2a(unittest.TestCase):
 249 | +    """RULING 137 STAGE 2a: the second family's soft step-A refusals, and the re-screen's after the writes, flag like the
 250 | +    first's (soft_codes); CUTTABLE's sentence-edge part flags (line 1 12:12 ET, default SOFT) while L-v 2's word check
 251 | +    and every other edge failure stay hard. DataDash 8dbc30ee's real record (replayed 12:1x ET): IN runs on from
 252 | +    'line:', 100 ms, the words match."""
 253 | +    DATADASH = {"ok": True, "model": "elevenlabs_stt:scribe_v1", "replayed": False,
 254 | +                "edges": {"in": {"ok": False, "word": "Bitcoin", "before": "line:", "pause_ms": 100,
 255 | +                                 "why": "the recogniser runs on into the clip ('line:', 100 ms before it)"},
 256 | +                          "out": {"ok": True, "word": "holdings.", "after": "The",
 257 | +                                  "why": "a sentence ends at the clip's last word"}, "cuttable": False}}
 258 | +
 259 | +    def test_soft_codes_and_the_second_family(self):
 260 | +        self.assertEqual(PK.soft_codes(["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]), ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
 261 | +        for f in (["REFERENT_OUTSIDE", "STALE_TIME"], [PK.HELD + " x"], [], None, ["SPEAKER_CHANGE"], ["RETRACTION"]):
 262 | +            self.assertIsNone(PK.soft_codes(f), f)
 263 | +        cleared = {"a": {"moment_id": "a"}, "b": {"moment_id": "b"}, "c": {"moment_id": "c"}, "d": {"moment_id": "d"}}
 264 | +        got = PK.soft_second(cleared, {"a": [{}]}, {"b": ["REFERENT_OUTSIDE"], "c": ["STALE_TIME"], "d": [PK.HELD]})
 265 | +        self.assertEqual(got, {"b": ["REFERENT_OUTSIDE"]})
 266 | +        self.assertEqual((cleared["b"].get("step_a_flags"), "step_a_flags" in cleared["c"]), (["REFERENT_OUTSIDE"], False))
 267 | +
 268 | +    def test_only_a_sentence_running_on_at_a_word_boundary_is_soft(self):
 269 | +        import copy
 270 | +        self.assertEqual(PK.soft_edges(self.DATADASH), ["EDGE_IN"])
 271 | +        both = copy.deepcopy(self.DATADASH)
 272 | +        both["edges"]["out"] = {"ok": False, "word": "x", "after": "y", "why": "the recogniser's sentence continues past the clip"}
 273 | +        self.assertEqual(PK.soft_edges(both), ["EDGE_IN", "EDGE_OUT"])
 274 | +        for why_in in ("the recogniser has no 'bitc' within 0.6 s of the clip's start", "no word timing from the recogniser",
 275 | +                       "the window starts at the clip: no word before it",
 276 | +                       "the recogniser does not hear the trimmed word 'And' right before the clip (ruling 33 part 2)"):
 277 | +            t = copy.deepcopy(self.DATADASH)
 278 | +            t["edges"]["in"]["why"] = why_in
 279 | +            self.assertIsNone(PK.soft_edges(t), why_in)
 280 | +        end = copy.deepcopy(self.DATADASH)
 281 | +        end["edges"]["out"] = {"ok": False, "why": "the window ends at the clip: no word after it"}
 282 | +        self.assertIsNone(PK.soft_edges(end))
 283 | +        for bad in (dict(self.DATADASH, ok=False), dict(self.DATADASH, error="x"), dict(self.DATADASH, edges=None)):
 284 | +            self.assertIsNone(PK.soft_edges(bad))
 285 | +
 286 | +    def base(self, truth, a=None):
 287 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 288 | +               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
 289 | +        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
 290 | +        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"clip_01": a or answer()},
 291 | +                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
 292 | +                    truth={"m": truth}, coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})
 293 | +
 294 | +    def test_the_rows_flag_with_the_clip_named(self):
 295 | +        kw = dict(who={"clip_01": "DataDash"}, mids={"m": "clip_01"})
 296 | +        self.assertEqual(PK.inventory(**self.base(self.DATADASH), **kw)["cuttable"]["status"], "FAIL")   # clean pass
 297 | +        row = PK.inventory(**self.base(self.DATADASH), soft=True, **kw)["cuttable"]
 298 | +        self.assertEqual((row["status"], row["flags"]), ("FLAGGED", [
 299 | +            "The second clip (DataDash): the checker heard the sentence run on into the clip's first word, so it may "
 300 | +            "start mid-sentence."]))
 301 | +        hard = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], **{"in": {"ok": False, "why": "no word timing from the recogniser"}}))
 302 | +        self.assertEqual(PK.inventory(**self.base(hard), soft=True, **kw)["cuttable"]["status"], "FAIL")
 303 | +        ok = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], cuttable=True, **{"in": {"ok": True, "why": "ok"}}))
 304 | +        a = PK.inventory(**self.base(ok), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]}, **kw)["context_a"]
 305 | +        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [                     # the second family's doubt
 306 | +            "The second clip (DataDash): the checker thought it points back to something said before the clip starts."]))
 307 | +        stale = PK.inventory(**self.base(ok, answer(time_ok="no")), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]},
 308 | +                             **kw)["context_a"]
 309 | +        self.assertEqual(stale["status"], "FAIL")                                   # a hard code still fails
 310 | +
 311 | +    def test_the_pin_takes_a_flagged_sentence_edge_never_a_flagged_word_check(self):
 312 | +        pk = TestThePin().pk(cuttable={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1, "flags": ["The second "
 313 | +                                       "clip (DataDash): the checker heard the sentence run on."]})
 314 | +        self.assertEqual(len(PP.to_pin(pk, "r")["moments_package"]["review_flags"]), 1)
 315 | +        with self.assertRaises(PP.PinRefused):
 316 | +            PP.to_pin(TestThePin().pk(second_pass={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1,
 317 | +                                                   "flags": ["a word differs"]}), "r")
 318 | +
 319 | +
 320 |  class TestTheDayCount(unittest.TestCase):
 321 |      def test_counted_per_day_ledger(self):
 322 |          with tempfile.TemporaryDirectory() as d:
 323 | 
```

---

pp-selectid: RULINGS 136 / 137 / 138, STAGE 2a of the hard/soft switch (stage 1, never-empty for step A's first
screen, is LIVE: audit 20261117_1135). Approved design: HARD = the words the cut carries (L-v 2), a cut mid-word,
speaker credit, a factual or stale-time step-A refusal by BOTH families, exclusion, 12 h, never-reused, channel count,
runtime, spend; SOFT (flag, never refuse) = everything else; NEVER EMPTY seals the best line-up that passes every hard
gate with at most 3 flags, each one plain sentence naming the clip (ruling 138 (3)). Stage 1's step-A reading (ruling
138 (1)): SOFT = NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN; HARD = STALE_TIME, SPEAKER_CHANGE,
RETRACTION (kept hard here even from one family). Files: pipeline/package.py, pipeline/package_pin.py,
tests/package/test_ruling_137.py. Today's evidence: build 131's soft pass lost DataDash 8dbc30ee at CUTTABLE (its words
match; the second recogniser runs on from 'line:' into its first word, 100 ms) and three moments at the SECOND step-A
screen for soft codes only.

THE CHANGE (only in the never-empty pass, soft=True; the clean pass is unchanged):
(a) soft_codes(f): a refusal's codes when all are soft and it is not held, else None; add_flags; soft_step_a (stage 1)
    now uses soft_codes. soft_second(cleared, a_two, off_fail): the moments the SECOND family refused for soft codes
    only stay, carrying the codes as "step_a_flags"; in _build they join cleared beside the moments it passed. The
    re-screen off the writer's family after the writes: a soft-only refusal keeps the clip, flagged, instead of
    dropping it (a hard code or no verdict still drops it, as before).
(b) CUTTABLE's sentence-edge part (line 1, 12:12 ET, default SOFT): soft_edges(t) returns the failing sides only when
    L-v 2's words match (ok True, no error, edges measured) and EVERY failing edge failed for exactly
    transcript_truth.edges' run-on reasons ("the recogniser runs on into the clip" / "the recogniser's sentence
    continues past the clip"); a word not found, a trimmed word, an unmeasured or window-edge edge stay HARD. Such
    moments stay in the soft pass (edge_flags). L-v 2's "second_pass" row stays HARD.
(c) inventory: context_a's codes are each clip's verdict codes plus every screen's soft codes (seg_flags), FLAGGED only
    when all are soft; "cuttable" is FLAGGED with one sentence per failing edge when every non-cuttable segment's
    failure is soft; both name the clip (who, mids: truth is keyed by moment id). package_pin.SOFT_GATES adds
    "cuttable" ("second_pass" never).
(d) the wrapper keeps the soft pass's own record (never_empty.soft_record: prescreen, hook_pool, tried).

TESTS (test_ruling_137: 11): soft_codes and the second family; only the run-on reasons are soft (DataDash 8dbc30ee's real
record), every other edge reason and a failed word check stay hard; both rows flag with the clip named, a hard code
still fails; the pin takes a FLAGGED cuttable, never a FLAGGED second_pass; the soft record. Mutations: 23 of 23
effective ones killed. NOT UNIT-TESTED, PLEASE READ: the three call sites inside _build (the second screen's
cleared filter, the re-screen's new branch, the cut_soft filter): they only call the tested helpers.

PLEASE CHECK: (1) that nothing HARD can pass: a hard code, a held moment, no verdict, a word mismatch, any non-run-on
edge failure, a FLAGGED word check; (2) that the clean pass is unchanged; (3) the three _build call sites; (4) that
every flag names its clip in one sentence; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
