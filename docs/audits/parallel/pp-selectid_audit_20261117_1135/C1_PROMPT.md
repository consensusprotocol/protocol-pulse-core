# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1135
# Branch: pp-selectid
# Generated: 2026-11-17 11:35 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1135/C1_STEP.diff (438 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 0d4ba34..ebcdc0b 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -79,6 +79,17 @@ PRESCREEN_WORKERS = 6              # ruling 58: the step-A batches run in parall
   6 |  SECOND_VERDICT_DEADLINE_S = 120.0  # RULING 82 (20:02 Nov 13): each second-vendor / off-writer step-A call; at it the next
   7 |  SECOND_VERDICT_BATCH = 2           # model (deepseek -> glm-5.3-flash -> qwen3.8-27b); small batches so one fits in it
   8 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
   9 | +# RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): TWO CLASSES, a HARD gate refuses, a SOFT gate scores and
  10 | +# FLAGS; NEVER EMPTY: when the clean search seals nothing, a second pass seals the best line-up that passes every hard
  11 | +# gate with its soft flags in plain words (the pin's moments_package "review_flags"; the integrator's note opens
  12 | +# "REVIEW FLAGS: ..."); at most FLAGGED_DAY_MAX flagged packages a day, a clean one always first. STAGE 1 (line 1, 11:29
  13 | +# ET Nov 17): step A only. Its SOFT codes, each with the plain words PBX reads; STALE_TIME (stale time), SPEAKER_CHANGE
  14 | +# (speaker credit) and RETRACTION (factual) stay HARD, even from one family, until stage 2 asks the second family.
  15 | +STEP_A_SOFT = {"NOT_OWN_SINCERE": "step A: the speaker may not be giving their own sincere view",
  16 | +               "REFERENT_OUTSIDE": "step A: the clip refers to something said before it",
  17 | +               "CONDITION_OUTSIDE": "step A: a condition the speaker sets lies outside the clip",
  18 | +               "UNCERTAIN": "step A: the screen was not sure what the clip means"}
  19 | +FLAGGED_DAY_MAX = 2
  20 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
  21 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
  22 |  WRITES = 2
  23 | @@ -469,6 +480,27 @@ def is_held(why):
  24 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
  25 |  
  26 |  
  27 | +def soft_step_a(ms, a_by, fails):
  28 | +    """RULING 137 STAGE 1: the moments step A refused for SOFT codes only (STEP_A_SOFT): a step-A answer on file, a
  29 | +    refusal (never a held one, ruling 102), and every code soft (one hard code keeps it out). -> {moment_id: a copy of
  30 | +    the moment carrying "step_a_flags", its codes}."""
  31 | +    out = {}
  32 | +    for m in ms:
  33 | +        f = fails.get(m["moment_id"])
  34 | +        if m["moment_id"] in a_by and f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f):
  35 | +            out[m["moment_id"]] = dict(m, step_a_flags=sorted({str(c) for c in f}))
  36 | +    return out
  37 | +
  38 | +
  39 | +def cleared_pool(ms, a_by, fails, soft=False):
  40 | +    """The moments that cleared step A (an answer on file, no failure), and in the never-empty pass (RULING 137
  41 | +    stage 1, soft=True) also those soft_step_a lets back, flagged. -> (cleared {id: moment}, back {id: moment})."""
  42 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  43 | +    back = soft_step_a(ms, a_by, fails) if soft else {}
  44 | +    cleared.update(back)
  45 | +    return cleared, back
  46 | +
  47 | +
  48 |  def local_held(a):
  49 |      """RULING 127 (2) (orchestrator 21:30 ET Nov 16): a step-A verdict from the local judge (gemma3:27b, ruling 87's last
  50 |      resort), PASS or REFUSE, is never final while a Heimdall family can be asked: HELD, 'local, provisional', never
  51 | @@ -2991,13 +3023,14 @@ def candidate_lineup(router, candidate, cleared, now):
  52 |      return segs, None
  53 |  
  54 |  
  55 | -def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  56 | +def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  57 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  58 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  59 |            join_cache=None,
  60 |            visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None,
  61 | -          ledger_aliases=None):
  62 | -    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  63 | +          ledger_aliases=None, soft=False):
  64 | +    """RULING 137: soft=True is the never-empty pass (build() calls it): step A's soft refusals are let back, flagged.
  65 | +    L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  66 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  67 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  68 |      one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
  69 | @@ -3134,7 +3167,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  70 |              par.update(ahead.result())
  71 |              ahead_pool.shutdown()
  72 |      pre_by = par.pop("by", None) or {}                   # which back-end confirmed each moment ahead (not reported)
  73 | -    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  74 | +    cleared, back = cleared_pool(ms, a_by, fails, soft)  # RULING 137 stage 1: the never-empty pass adds back, flagged
  75 |      levels = current_levels(sources.values(), ctx)
  76 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  77 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
  78 | @@ -3146,6 +3179,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  79 |                           "last_resort_87": {}},                  # RULING 102: held, never refused; the local judge
  80 |             "angles": [], "takeaways": [],
  81 |             "package": None}
  82 | +    if soft:                                                # RULING 137 stage 1: which came back, with which codes
  83 | +        out["prescreen"]["soft_back"] = {mid: m["step_a_flags"] for mid, m in back.items()}
  84 | +        log(f"  RULING 137 NEVER EMPTY (stage 1): {len(back)} moment(s) step A refused for soft codes only come back, "
  85 | +            f"flagged: " + ", ".join(f"{mid[:8]} {m['step_a_flags']}" for mid, m in back.items()))
  86 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
  87 |          f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
  88 |          f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
  89 | @@ -3581,7 +3618,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  90 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  91 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
  92 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
  93 | -                                last_resort=pin_last_resort(pk))      # RULING 102: on the pin
  94 | +                                last_resort=pin_last_resort(pk), soft=soft)   # RULING 102; RULING 137 stage 1
  95 |          import package_pin
  96 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
  97 |          if problems:
  98 | @@ -4064,7 +4101,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  99 |                                              stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 100 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 101 |                                              value=val,                       # ruling 91: the takeaway earned its place
 102 | -                                            last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 103 | +                                            last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 104 | +                                            soft=soft)                            # RULING 137 stage 1
 105 |                      if not ok_c:
 106 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 107 |                          cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 108 | @@ -4163,6 +4201,22 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 109 |      return out
 110 |  
 111 |  
 112 | +def build(*args, never_empty=False, flagged_today=0, **kw):
 113 | +    """RULINGS 136 / 137, NEVER EMPTY: the clean search first (_build), as before; a clean package always outranks a
 114 | +    flagged one. Only when it seals nothing, never_empty is set and fewer than FLAGGED_DAY_MAX flagged packages went
 115 | +    out today (flagged_today, the caller's count), the never-empty pass: the same search again (_build soft=True) with
 116 | +    step A's soft refusals back in, flagged (stage 1). Its record names both passes ("never_empty")."""
 117 | +    out = _build(*args, **kw)
 118 | +    if not never_empty or out.get("package") or flagged_today >= FLAGGED_DAY_MAX:
 119 | +        return out
 120 | +    (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 121 | +                             f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 122 | +    soft = _build(*args, soft=True, **kw)
 123 | +    info = {"stage": 1, "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 124 | +            "soft_back": (soft.get("prescreen") or {}).get("soft_back")}
 125 | +    return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 126 | +
 127 | +
 128 |  def _spent(spend):
 129 |      """(estimate, vendor-reported) from the caller's meter. A bare number is the estimate alone; its reported figure
 130 |      is then taken to be the same (the conservative reading). No meter: (0, 0)."""
 131 | @@ -4173,7 +4227,7 @@ def _spent(spend):
 132 |  
 133 |  
 134 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 135 | -              hook=None, stand=None, visual=None, value=None, last_resort=None):
 136 | +              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False):
 137 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 138 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 139 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 140 | @@ -4196,6 +4250,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 141 |      det = fid["deterministic"]
 142 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 143 |      a_rows = list((a_by or {}).values())
 144 | +    a_codes = sorted({str(c) for a in a_rows for c in CI.a_failures(a)})   # RULING 137 stage 1: step A's codes; in the
 145 | +    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # never-empty pass, soft ones FLAG
 146 |      return {
 147 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
 148 |          "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 149 | @@ -4208,9 +4264,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 150 |          "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 151 |                                f"{FINAL_TAIL_S} s tail)"),
 152 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 153 | -        "context_a": dict(row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 154 | +        "context_a": dict(row(bool(a_rows) and (not a_codes or soft_a),
 155 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 156 |                                n=len(a_rows)),
 157 | +                          **({"status": "FLAGGED", "flags": [STEP_A_SOFT[c] for c in a_codes]}   # RULING 137 stage 1
 158 | +                             if soft_a and len(a_rows) >= 1 else {}),
 159 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 160 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 161 |                                measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 162 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 163 | index 3c5ca7d..5fb02f2 100644
 164 | --- a/pipeline/package_pin.py
 165 | +++ b/pipeline/package_pin.py
 166 | @@ -31,6 +31,11 @@ REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate
 167 |  # STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 168 |  MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone",
 169 |                  "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 170 | +# RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): a SOFT gate scores and FLAGS. Its row may say "FLAGGED"
 171 | +# with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 172 | +# (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 173 | +SOFT_GATES = frozenset({"context_a"})
 174 | +REVIEW_FLAGS_MAX = 3
 175 |  
 176 |  
 177 |  # RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
 178 | @@ -375,14 +380,41 @@ def speaker_problems(segments):
 179 |      return out
 180 |  
 181 |  
 182 | +def flagged_ok(g, row):
 183 | +    """RULING 137: a FLAGGED row stands only on a SOFT gate and only with its flags: a non-empty list of plain-word
 184 | +    strings."""
 185 | +    fl = row.get("flags")
 186 | +    return g in SOFT_GATES and isinstance(fl, list) and bool(fl) and all(isinstance(f, str) and f.strip() for f in fl)
 187 | +
 188 | +
 189 | +def review_flags_of(gates):
 190 | +    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once."""
 191 | +    out = []
 192 | +    for _g, row in (gates.items() if isinstance(gates, dict) else ()):
 193 | +        if isinstance(row, dict) and row.get("status") == "FLAGGED":
 194 | +            out += [f for f in row.get("flags") or [] if isinstance(f, str) and f not in out]
 195 | +    return out
 196 | +
 197 | +
 198 | +def review_problems(mp):
 199 | +    """RULING 137: [why] when a pin's moments_package "review_flags" is not exactly what its sealed gates flag, or is
 200 | +    over REVIEW_FLAGS_MAX (empty = it holds)."""
 201 | +    want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
 202 | +    out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
 203 | +    return out + ([f"{len(want)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"]
 204 | +                  if len(want) > REVIEW_FLAGS_MAX else [])
 205 | +
 206 | +
 207 |  def gate_problems(gates, required=REQUIRED_GATES):
 208 | -    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 209 | +    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live;
 210 | +    RULING 137: or FLAGGED on a SOFT gate with its flags, flagged_ok)."""
 211 |      if not isinstance(gates, dict):
 212 |          return ["no gate inventory"]
 213 |      out = []
 214 |      for g in required:
 215 |          row = gates.get(g)
 216 | -        if not isinstance(row, dict) or row.get("status") != "PASS":
 217 | +        if not isinstance(row, dict) or not (row.get("status") == "PASS" or
 218 | +                                             (row.get("status") == "FLAGGED" and flagged_ok(g, row))):
 219 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 220 |          elif row.get("replayed") is not False:
 221 |              out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
 222 | @@ -460,6 +492,9 @@ def to_pin(pk, run_name):
 223 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 224 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
 225 |          spotlight_problems(pk) + takeaway_problems(pk)
 226 | +    rf = review_flags_of(pk.get("gates"))                 # RULING 137: derived from the sealed gates, at most 3
 227 | +    problems += [f"{len(rf)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if len(rf) > REVIEW_FLAGS_MAX \
 228 | +        else []
 229 |      if problems:
 230 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 231 |      segs = []
 232 | @@ -510,6 +545,7 @@ def to_pin(pk, run_name):
 233 |                                      "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 234 |                                     if spot else {}),
 235 |                                  "gates": pk["gates"],
 236 | +                                **({"review_flags": rf} if rf else {}),   # RULING 137: absent when clean
 237 |                                  **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 238 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 239 |                                  **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 240 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 241 | index b3f5a13..1feeac5 100644
 242 | --- a/tests/package/proof_ledger.py
 243 | +++ b/tests/package/proof_ledger.py
 244 | @@ -73,6 +73,32 @@ import package as PK  # noqa: E402
 245 |  import hook_bar as HB  # noqa: E402
 246 |  import package_pin  # noqa: E402
 247 |  import proof_ly as PL  # noqa: E402
 248 | +
 249 | +FLAGGED_DAY = os.path.join(HERE, "proof", "FLAGGED_DAY.json")   # RULING 136 (2): the flagged pins of the 21:10 day
 250 | +
 251 | +
 252 | +def flagged_today(path=FLAGGED_DAY, day=None):
 253 | +    """RULING 136 (2): how many flagged packages this builder sealed in the current 21:10-21:10 day (the day ledger's
 254 | +    name keys it; an unreadable or another day's file counts 0)."""
 255 | +    day = day or os.path.basename(PL.day_ledger())
 256 | +    try:
 257 | +        d = json.load(open(path))
 258 | +    except (OSError, ValueError):
 259 | +        return 0
 260 | +    return len(d.get("pins") or []) if isinstance(d, dict) and d.get("day") == day else 0
 261 | +
 262 | +
 263 | +def record_flagged(pin, path=FLAGGED_DAY, day=None):
 264 | +    """RULING 136 (2): a flagged pin was sealed: add it to the day's count."""
 265 | +    day = day or os.path.basename(PL.day_ledger())
 266 | +    try:
 267 | +        d = json.load(open(path))
 268 | +    except (OSError, ValueError):
 269 | +        d = {}
 270 | +    if not isinstance(d, dict) or d.get("day") != day:
 271 | +        d = {"day": day, "pins": []}
 272 | +    d["pins"].append({"story_id": pin["story_id"], "review_flags": pin["moments_package"].get("review_flags")})
 273 | +    json.dump(d, open(path, "w"), indent=1)
 274 |  import proof_saved_runs as PS  # noqa: E402
 275 |  import providers as P  # noqa: E402
 276 |  import speakers as SP  # noqa: E402
 277 | @@ -538,6 +564,7 @@ def main(argv=None):
 278 |      spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
 279 |      sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
 280 |      kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
 281 | +              never_empty=True, flagged_today=flagged_today(),                     # RULINGS 136 / 137 (stage 1)
 282 |                work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 283 |                spend=lambda: (own["est"], own["best"]),
 284 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 285 | @@ -614,6 +641,9 @@ def main(argv=None):
 286 |                                                name="MOMENTS_PIN_LEDGER.json")
 287 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 288 |                            "package_sha256": pin["moments_package"]["package_sha256"]}
 289 | +            if pin["moments_package"].get("review_flags"):        # RULING 136 (2): a flagged pin counts for the day
 290 | +                record_flagged(pin)
 291 | +                res["pin"]["review_flags"] = pin["moments_package"]["review_flags"]
 292 |              import shutil                                # ruling 70: each segment's sheet beside the pin
 293 |              for sg in pin["segments"]:
 294 |                  sh = (sg.get("visual") or {}).get("sheet") or {}
 295 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 296 | new file mode 100644
 297 | index 0000000..6293716
 298 | --- /dev/null
 299 | +++ b/tests/package/test_ruling_137.py
 300 | @@ -0,0 +1,137 @@
 301 | +#!/usr/bin/env python3
 302 | +"""RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17), STAGE 1: NEVER EMPTY for step A. A clean package first;
 303 | +when the clean pass seals nothing, a second pass lets back the moments step A refused for SOFT codes only, each flagged
 304 | +in plain words; the pin's step-A row says FLAGGED with them and moments_package carries them as review_flags (at most
 305 | +3); a hard code, a held moment, a FLAGGED row on a hard gate never pass. Offline."""
 306 | +import json
 307 | +import os
 308 | +import sys
 309 | +import tempfile
 310 | +import unittest
 311 | +from unittest import mock
 312 | +
 313 | +HERE = os.path.dirname(os.path.abspath(__file__))
 314 | +REPO = os.path.dirname(os.path.dirname(HERE))
 315 | +sys.path[:0] = [os.path.join(REPO, "pipeline"), HERE]
 316 | +import package as PK  # noqa: E402
 317 | +import package_pin as PP  # noqa: E402
 318 | +import proof_ledger as PLG  # noqa: E402
 319 | +
 320 | +SINCERE = PK.STEP_A_SOFT["NOT_OWN_SINCERE"]
 321 | +
 322 | +
 323 | +def answer(**kw):
 324 | +    a = {"backend": "b", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [],
 325 | +         "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 326 | +    a.update(kw)
 327 | +    return a
 328 | +
 329 | +
 330 | +class TestTheNeverEmptyPool(unittest.TestCase):
 331 | +    def test_soft_codes_come_back_flagged_and_nothing_else_does(self):
 332 | +        ms = [{"moment_id": k} for k in ("s", "h", "x", "n", "c")]
 333 | +        a_by = {"s": {}, "h": {}, "x": {}, "c": {}}                       # 'n' has no step-A answer on file
 334 | +        fails = {"s": ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"], "h": ["REFERENT_OUTSIDE", "STALE_TIME"],
 335 | +                 "x": [PK.HELD + " no verdict"], "n": ["NOT_OWN_SINCERE"], "c": []}
 336 | +        clean, back = PK.cleared_pool(ms, a_by, fails)
 337 | +        self.assertEqual((sorted(clean), back), (["c"], {}))              # the clean pass: as before
 338 | +        both, back = PK.cleared_pool(ms, a_by, fails, soft=True)
 339 | +        self.assertEqual(sorted(both), ["c", "s"])
 340 | +        self.assertEqual(back["s"]["step_a_flags"], ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
 341 | +        self.assertNotIn("step_a_flags", ms[0])                           # a copy: the pool's moment is untouched
 342 | +
 343 | +
 344 | +class TestTheStepARow(unittest.TestCase):
 345 | +    def base(self, **a):
 346 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 347 | +               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
 348 | +        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
 349 | +        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"hook": answer(**a)},
 350 | +                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
 351 | +                    truth={"m": {"ok": True, "model": "s", "replayed": False, "edges": {"cuttable": True}}},
 352 | +                    coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})
 353 | +
 354 | +    def test_soft_codes_flag_only_in_the_never_empty_pass_and_a_hard_code_still_fails(self):
 355 | +        self.assertEqual(PK.inventory(**self.base(), soft=True)["context_a"]["status"], "PASS")      # clean: PASS
 356 | +        quoted = self.base(view="quoting_someone_else")
 357 | +        self.assertEqual(PK.inventory(**quoted)["context_a"]["status"], "FAIL")                     # the clean pass
 358 | +        row = PK.inventory(**quoted, soft=True)["context_a"]
 359 | +        self.assertEqual((row["status"], row["flags"], row["replayed"]), ("FLAGGED", [SINCERE], False))
 360 | +        stale = self.base(view="quoting_someone_else", time_ok="no")                               # a hard code too
 361 | +        self.assertEqual(PK.inventory(**stale, soft=True)["context_a"]["status"], "FAIL")
 362 | +
 363 | +
 364 | +class TestThePin(unittest.TestCase):
 365 | +    def pk(self, **gates):
 366 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in PP.REQUIRED_GATES}
 367 | +        g.update(gates)
 368 | +        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
 369 | +                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
 370 | +                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
 371 | +                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 372 | +                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 373 | +                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 374 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 375 | +                              "speaker": {"name": "unknown", "role": None, "line": None, "basis": None, "why": "t",
 376 | +                                          "people": [], "measured": True},
 377 | +                              "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 378 | +
 379 | +    def flagged(self, flags, gate="context_a", replayed=False):
 380 | +        return {gate: {"status": "FLAGGED", "by": "x", "replayed": replayed, "n": 1, "flags": flags}}
 381 | +
 382 | +    def test_a_flagged_soft_row_seals_with_its_review_flags(self):
 383 | +        pin = PP.to_pin(self.pk(**self.flagged([SINCERE])), "r")
 384 | +        mp = pin["moments_package"]
 385 | +        self.assertEqual((mp["review_flags"], PP.review_problems(mp)), ([SINCERE], []))
 386 | +        self.assertEqual(mp["package_sha256"], PP.pin_seal(pin))                     # the flags are sealed with the gates
 387 | +        self.assertNotEqual(mp["package_sha256"], PP.to_pin(self.pk(), "r")["moments_package"]["package_sha256"])
 388 | +        self.assertTrue(PP.review_problems(dict(mp, review_flags=["something else"])))   # not the sealed flags
 389 | +        self.assertNotIn("review_flags", PP.to_pin(self.pk(), "r")["moments_package"])   # clean: absent
 390 | +
 391 | +    def test_what_never_seals(self):
 392 | +        for bad in (self.flagged([SINCERE], gate="exclusion"),                         # FLAGGED on a HARD gate
 393 | +                    self.flagged([]), self.flagged([""]), self.flagged("not a list"),
 394 | +                    self.flagged([SINCERE], replayed=True),
 395 | +                    self.flagged(["one", "two", "three", "four"])):                    # over 3 (ruling 136 (2))
 396 | +            with self.assertRaises(PP.PinRefused, msg=str(bad)):
 397 | +                PP.to_pin(self.pk(**bad), "r")
 398 | +
 399 | +
 400 | +class TestTheTwoPasses(unittest.TestCase):
 401 | +    def run_build(self, clean, soft, **kw):
 402 | +        calls = []
 403 | +
 404 | +        def fake(*a, **k):
 405 | +            calls.append(bool(k.get("soft")))
 406 | +            return dict(soft if k.get("soft") else clean)
 407 | +        with mock.patch.object(PK, "_build", side_effect=fake):
 408 | +            out = PK.build("router", [], {}, None, log=lambda m: None, **kw)
 409 | +        return calls, out
 410 | +
 411 | +    def test_clean_first_then_the_never_empty_pass_within_the_day_limit(self):
 412 | +        none, sealed = {"package": None, "why_none": "x"}, {"package": {"p": 1}}
 413 | +        calls, out = self.run_build(sealed, sealed, never_empty=True)
 414 | +        self.assertEqual((calls, "never_empty" in out), ([False], False))            # a clean package: one pass
 415 | +        calls, out = self.run_build(none, sealed, never_empty=True)
 416 | +        self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
 417 | +        calls, out = self.run_build(none, dict(none, why_none="y"), never_empty=True)
 418 | +        self.assertEqual((calls, out["package"], out["never_empty"]["soft_why_none"]), ([False, True], None, "y"))
 419 | +        self.assertEqual(self.run_build(none, sealed)[0], [False])                   # never_empty off: as before
 420 | +        self.assertEqual(self.run_build(none, sealed, never_empty=True, flagged_today=PK.FLAGGED_DAY_MAX)[0], [False])
 421 | +
 422 | +
 423 | +class TestTheDayCount(unittest.TestCase):
 424 | +    def test_counted_per_day_ledger(self):
 425 | +        with tempfile.TemporaryDirectory() as d:
 426 | +            p = os.path.join(d, "FLAGGED_DAY.json")
 427 | +            self.assertEqual(PLG.flagged_today(p, day="D1"), 0)
 428 | +            pin = {"story_id": "s1", "moments_package": {"review_flags": [SINCERE]}}
 429 | +            PLG.record_flagged(pin, p, day="D1")
 430 | +            PLG.record_flagged(dict(pin, story_id="s2"), p, day="D1")
 431 | +            self.assertEqual((PLG.flagged_today(p, day="D1"), PLG.flagged_today(p, day="D2")), (2, 0))
 432 | +            PLG.record_flagged(pin, p, day="D2")                                       # a new day starts afresh
 433 | +            self.assertEqual(json.load(open(p))["pins"], [{"story_id": "s1", "review_flags": [SINCERE]}])
 434 | +
 435 | +
 436 | +if __name__ == "__main__":
 437 | +    unittest.main()
 438 | 
```

---

pp-selectid: RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17), STAGE 1 of the hard/soft switch: NEVER EMPTY
for step A. Approved design (docs/audits/parallel/pp-selectid_R136_DESIGN_20261117.md): "(1) TWO CLASSES. HARD gates
still refuse ... Every OTHER gate becomes SOFT: it scores and FLAGS, it does not refuse ... (2) NEVER EMPTY. When no
line-up passes clean, the build seals the BEST line-up that passes every hard gate, with its soft flags listed in plain
words at the top of the Telegram note ('REVIEW FLAGS: ...'), at most one such flagged package per build window and at
most two a day, and only if it has no more than 3 soft flags; PBX decides. A clean package always outranks a flagged
one." Stage 1 covers step A only (today's kept line-up was refused there for soft codes only); every other gate is
unchanged here (stage 2). Files: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py,
tests/package/test_ruling_137.py. package_pin.py is imported LIVE by the integrator's check_pin_only, which calls
PP.gate_problems(mp["gates"], PP.required_gates(mp)) (its message of 11:3x): it changes nothing on its side.

THE CHANGE:
(a) package.STEP_A_SOFT (the plain words PBX reads per soft code): NOT_OWN_SINCERE, REFERENT_OUTSIDE,
    CONDITION_OUTSIDE, UNCERTAIN. STALE_TIME, SPEAKER_CHANGE and RETRACTION stay HARD even from one family in stage 1
    (context_integrity.a_failures, UNCHANGED, gives the codes). FLAGGED_DAY_MAX = 2.
(b) package.soft_step_a (:483) / cleared_pool (:495): the clean pool exactly as before; with soft=True also the moments
    step A refused for soft codes ONLY (an answer on file, not held, every code soft), each a copy carrying
    "step_a_flags".
(c) package.build (:4204) is now a wrapper over the former build (renamed _build, one new parameter soft=False, used
    only at cleared_pool and the two inventory calls): the clean pass first; only when it seals nothing, never_empty is
    set and fewer than FLAGGED_DAY_MAX flagged packages went out today, the soft pass; its record names both
    ("never_empty"). Every gate after step A runs on the soft pass's line-ups exactly as on the clean pass (L-v 2,
    CUTTABLE, hook onset, the hook bar, joins, clips-alone, the lock, vision, writes, coherence, value: all UNCHANGED).
(d) package.inventory (:4229): the "context_a" row is FLAGGED with "flags" (STEP_A_SOFT's words) only in the soft pass
    and only when every step-A code of the package's segments is soft; otherwise exactly as before (FAIL on any code).
(e) package_pin: SOFT_GATES = {"context_a"}; flagged_ok; gate_problems (:408) accepts a FLAGGED row only on a SOFT gate
    with a non-empty list of non-empty string flags, and still needs replayed False; review_flags_of derives the pin's
    moments_package "review_flags" from the sealed FLAGGED rows (to_pin :489, at most REVIEW_FLAGS_MAX 3, absent when
    clean); review_problems binds the unsealed list to the sealed rows. The flags sit inside the sealed gate inventory,
    so seal()/pin_seal (UNCHANGED, :249) bind them; an old pin has no FLAGGED row and recomputes as before.
(f) proof_ledger: never_empty=True and flagged_today (FLAGGED_DAY.json, keyed by the 21:10 day ledger) into every
    build call; record_flagged after a flagged pin is written.

TESTS (test_ruling_137, 6): the pool (soft codes back flagged; a hard code, a held moment, no answer stay out; the clean
pass unchanged; a copy); the step-A row (PASS clean; FAIL in the clean pass; FLAGGED with the words in the soft pass; a
hard code FAILS even then); the pin (seals with review_flags, sealed, bound; absent when clean; FLAGGED on a hard gate,
empty or non-string flags, replayed, and 4 flags never seal); the two passes (clean first; soft only after an empty
clean pass; the day limit; never_empty off); the day count (per day ledger, resets). Mutations P1-P14 after a control:
13 of 14 killed; P2 survives as an EQUIVALENT mutant (a held reason is never a soft code, so not is_held is redundant
with the all-soft test; kept as ruling 102's explicit intent).

PLEASE CHECK: (1) that no HARD gate can be passed by this change (a hard step-A code, any other gate's FAIL, a FLAGGED
row on a hard gate); (2) that a clean package always comes first and the soft pass runs only after an empty clean pass,
within the day limit; (3) that the pin's flags are bound by the seal and the live check accepts exactly this; (4) that
every pin sealed before this recomputes; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
