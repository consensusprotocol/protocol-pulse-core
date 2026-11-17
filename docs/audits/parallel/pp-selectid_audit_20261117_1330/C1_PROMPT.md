# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1330
# Branch: pp-selectid
# Generated: 2026-11-17 13:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1330/C1_STEP.diff (229 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5b9ed6d..68e6942 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -981,6 +981,10 @@ opens the video. The hook is shown for context only: it is NOT rated here (its o
   6 |  Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
   7 |  HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
   8 |  HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
   9 | +HOOK_PART_WORDS = {"scroll": "stopping the scroll", "alone": "making sense on its own",   # RULING 137 stage 2b: a
  10 | +                   "setup": "setting up what follows"}                                  # part in PBX's words
  11 | +HOOK_SOFT_MAX = 2      # RULING 137 stage 2b: the never-empty pass lets the best 2 hooks under the bar open (each is seen
  12 | +#   by the paid vision check before any angle, as every opener is)
  13 |  HOOK_OWN = ("scroll", "alone")     # RULING 61 (12:00): the hook's OWN-JOB rating, cached and never re-asked per line-up
  14 |  HOOK_OWN_RULE = ("the lowest of scroll / alone, cached (ruling 61); 'sets up what follows' is judged at the hook -> "
  15 |                   "clip_01 join")
  16 | @@ -1667,6 +1671,21 @@ def hook_bar_mark(live=None):
  17 |              "calibration_sha256": (live or {}).get("sha256"), "ruling": "115"}
  18 |  
  19 |  
  20 | +def hook_bar_under(m):
  21 | +    """RULING 137 stage 2b (the calibrated hook bar SOFT in the never-empty pass): the plain detail of a hook rated UNDER
  22 | +    the bar by the bar's own rater, every part measured, e.g. "stopping the scroll 2 of 5, needs 3"; None when it
  23 | +    passes, a part is unmeasured, another back-end rated it, or no calibration is valid (those stay hard, law L-m)."""
  24 | +    r = (m or {}).get("hook_rating") or {}
  25 | +    parts = {k: r.get(k) for k in HOOK_PARTS}
  26 | +    if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
  27 | +        return None
  28 | +    live, _ = _live_bar()
  29 | +    if live is None or r.get("backend") != live.get("rater"):
  30 | +        return None
  31 | +    under = [p for p in HOOK_PARTS if parts[p] < live["floors"][p]]
  32 | +    return "; ".join(f"{HOOK_PART_WORDS[p]} {parts[p]} of 5, needs {live['floors'][p]}" for p in under) or None
  33 | +
  34 | +
  35 |  def hook_own(m):
  36 |      """RULING 61 / RULING 115: a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
  37 |      "alone", "setup", "rating": the lower of scroll and alone (it ORDERS hooks), "passes": RULING 115, every part at
  38 | @@ -1679,9 +1698,11 @@ def hook_own(m):
  39 |          return None
  40 |      live, why = _live_bar()
  41 |      ok, short = HB.passes(dict(parts, backend=r.get("backend")), live)
  42 | -    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok, short=why if live is None else short,
  43 | +    flag = hook_bar_under(m) if not ok and m.get("hook_bar_soft") else None    # RULING 137 stage 2b: a hook the
  44 | +    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok or bool(flag),   # never-empty pass marked
  45 | +                short=why if live is None else short,                                    # opens, flagged
  46 |                  bar=HB.text(live), source="the hook's cached own-job rating (ruling 61), on the calibrated bar (ruling 115)",
  47 | -                rule=HOOK_OWN_RULE)
  48 | +                rule=HOOK_OWN_RULE, **({"flagged": flag} if flag else {}))
  49 |  
  50 |  
  51 |  def opens_16x9(m):
  52 | @@ -3299,7 +3320,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  53 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  54 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  55 |      for m in cleared.values():                                           # a rating is this build's own (its
  56 | -        m.pop("hook_rating", None)                                       # cache's), never one carried in
  57 | +        m.pop("hook_rating", None)                                       # cache's), never one carried in; nor is
  58 | +        m.pop("hook_bar_soft", None)                                     # RULING 137 stage 2b's soft mark
  59 |      openers = {mid: m for mid, m in cleared.items() if can_open(m)}      # RULING 59 (a): every one that can open,
  60 |      rated, hook_err = hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
  61 |          ({}, None)                                                        # each alone (ruling 115), cached
  62 | @@ -3307,6 +3329,14 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  63 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
  64 |                                                                        "cannot open (hook eligibility, G17a or the "
  65 |                                                                        "render's hook rule)")}
  66 | +    under = hook_order([m for mid, m in openers.items() if mid in rated and hook_bar_under(m)])[:HOOK_SOFT_MAX] \
  67 | +        if soft else []                                                   # RULING 137 stage 2b: the hook bar is SOFT
  68 | +    for m in under:                                                       # in the never-empty pass: the best
  69 | +        m["hook_bar_soft"] = True                                         # HOOK_SOFT_MAX hooks under it open, flagged
  70 | +    if under:
  71 | +        out["prescreen"]["soft_hook_bar"] = {m["moment_id"]: hook_bar_under(m) for m in under}
  72 | +        log(f"  RULING 137 NEVER EMPTY (stage 2b): {len(under)} hook(s) rated under the calibrated bar by its own rater "
  73 | +            f"open, flagged: " + ", ".join(f"{m['moment_id'][:8]} ({hook_bar_under(m)})" for m in under))
  74 |      for m in cleared.values():
  75 |          m.pop("visual_hook_block", None)
  76 |      rated_open = [m for m in cleared.values() if can_open(m)]              # RULING 70: the hooks that would open,
  77 | @@ -4295,7 +4325,7 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
  78 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
  79 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
  80 |      soft = _build(*args, soft=True, **kw)
  81 | -    info = {"stage": "2a", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
  82 | +    info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
  83 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
  84 |              "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
  85 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
  86 | @@ -4334,6 +4364,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  87 |          return None if any(not isinstance(x, bool) for x in values) else any(values)
  88 |      det = fid["deterministic"]
  89 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
  90 | +    hook_fl = ((medley[1].get("hook_own") or {}).get("flagged") if soft and medley is not None else None)   # 2b
  91 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
  92 |      edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
  93 |                 if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
  94 | @@ -4387,7 +4418,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  95 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
  96 |                            **votes_of(coh)),
  97 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
  98 | -                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
  99 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"),
 100 | +                           **({"status": "FLAGGED", "flags": [            # RULING 137 stage 2b: the hook under the bar
 101 | +                               f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated "
 102 | +                               f"it under the hook bar ({hook_fl})."]} if hook_fl and medley[0] else {}))}
 103 |             if medley is not None else {}),
 104 |          **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 105 |             if shape is not None else {}),
 106 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 107 | index 180aba9..1fb3855 100644
 108 | --- a/pipeline/package_pin.py
 109 | +++ b/pipeline/package_pin.py
 110 | @@ -35,8 +35,10 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 111 |  # with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 112 |  # (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 113 |  SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 114 | -                        "cuttable"})                       # stage 2a: a sentence edge at a word boundary (L-v 2's
 115 | -#   word check, "second_pass", stays HARD)
 116 | +                        "cuttable",                        # stage 2a: a sentence edge at a word boundary (L-v 2's
 117 | +                        #   word check, "second_pass", stays HARD)
 118 | +                        "medley"})                         # stage 2b: the hook under the calibrated bar (its own
 119 | +#   rater's rating; no calibration or another rater stays HARD)
 120 |  REVIEW_FLAGS_MAX = 3
 121 |  
 122 |  
 123 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 124 | index 3fc3227..0e4d42a 100644
 125 | --- a/tests/package/test_medley.py
 126 | +++ b/tests/package/test_medley.py
 127 | @@ -850,6 +850,7 @@ class Rig:
 128 |              kw["registered"] = self.registered
 129 |          if self.lock_check is not None:
 130 |              kw["lock_check"] = self.lock_check
 131 | +        kw.update(getattr(self, "build_kw", None) or {})  # RULING 137: never_empty / flagged_today, when a test sets
 132 |          if getattr(self, "stories_path", None):            # RULING 118 (4): the stories file (default: none read)
 133 |              kw["stories_path"] = self.stories_path
 134 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 135 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 136 | index c322e28..f61260a 100644
 137 | --- a/tests/package/test_ruling_137.py
 138 | +++ b/tests/package/test_ruling_137.py
 139 | @@ -207,6 +207,89 @@ class TestStage2a(unittest.TestCase):
 140 |                                                     "flags": ["a word differs"]}), "r")
 141 |  
 142 |  
 143 | +class TestStage2bHookBar(unittest.TestCase):
 144 | +    """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 145 | +    own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 146 | +    another rater or an unmeasured part stay hard, and the clean pass never opens it. The rigs' bar (conftest):
 147 | +    scroll 3, alone 4, setup 3, rated by "xai:grok"."""
 148 | +
 149 | +    def hm(self, sc, al, se, backend="xai:grok", mark=False):
 150 | +        m = {"moment_id": "h1", "hook_rating": {"scroll": sc, "alone": al, "setup": se, "backend": backend}}
 151 | +        return dict(m, hook_bar_soft=True) if mark else m
 152 | +
 153 | +    def test_under_the_bar_in_plain_words_and_what_stays_hard(self):
 154 | +        self.assertEqual(PK.hook_bar_under(self.hm(2, 5, 5)), "stopping the scroll 2 of 5, needs 3")
 155 | +        self.assertEqual(PK.hook_bar_under(self.hm(2, 3, 2)), "stopping the scroll 2 of 5, needs 3; making sense on "
 156 | +                         "its own 3 of 5, needs 4; setting up what follows 2 of 5, needs 3")
 157 | +        for m in (self.hm(3, 4, 3), self.hm(2, 5, 5, backend="heimdall:qwen"), self.hm(None, 5, 5),
 158 | +                  self.hm(True, 5, 5), {}, None):
 159 | +            self.assertIsNone(PK.hook_bar_under(m), m)
 160 | +        with mock.patch.object(PK, "_live_bar", lambda: (None, "no valid hook calibration")):
 161 | +            self.assertIsNone(PK.hook_bar_under(self.hm(2, 5, 5)))
 162 | +
 163 | +    def test_only_the_soft_pass_mark_opens_it(self):
 164 | +        own = PK.hook_own(self.hm(2, 5, 5))
 165 | +        self.assertEqual((own["passes"], "flagged" in own), (False, False))
 166 | +        own = PK.hook_own(self.hm(2, 5, 5, mark=True))
 167 | +        self.assertEqual((own["passes"], own["flagged"]), (True, "stopping the scroll 2 of 5, needs 3"))
 168 | +        own = PK.hook_own(self.hm(2, 5, 5, backend="heimdall:qwen", mark=True))
 169 | +        self.assertEqual((own["passes"], "flagged" in own), (False, False))         # another rater: hard
 170 | +        own = PK.hook_own(self.hm(3, 4, 3, mark=True))
 171 | +        self.assertEqual((own["passes"], "flagged" in own), (True, False))          # a pass is never flagged
 172 | +
 173 | +    def rig(self, hooks, never_empty):
 174 | +        import test_medley as TM
 175 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=hooks)
 176 | +        r.build_kw = {"never_empty": never_empty}
 177 | +        return r, r.run()
 178 | +
 179 | +    UNDER = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # h: the best hook, under the bar
 180 | +
 181 | +    def test_a_hook_under_the_bar_seals_flagged_only_in_the_never_empty_pass(self):
 182 | +        _, clean = self.rig(self.UNDER, False)
 183 | +        self.assertIsNone(clean["package"])
 184 | +        self.assertIn("no hook in the pool", clean["why_none"])
 185 | +        r, out = self.rig(self.UNDER, True)
 186 | +        pk = out["package"]
 187 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]][0], "h")
 188 | +        ch = pk["segments"][0].get("channel")
 189 | +        want = [f"The opening clip ({ch}): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
 190 | +                f"needs 3)."]
 191 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
 192 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
 193 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
 194 | +        self.assertEqual(pk["gates"]["coherence"]["status"], "PASS")                 # flagged once, on its own row
 195 | +        self.assertEqual(out["never_empty"]["stage"], "2b")
 196 | +        self.assertEqual(list(out["prescreen"]["soft_hook_bar"])[0], "h")
 197 | +
 198 | +    def test_a_mark_carried_in_is_never_read(self):
 199 | +        import test_medley as TM
 200 | +        ms = [dict(m, hook_bar_soft=True) for m in TM.TestBuildLoop.MS]      # the clean pass pops it with the rating
 201 | +        r = TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=self.UNDER)
 202 | +        r.build_kw = {"never_empty": False}
 203 | +        self.assertIsNone(r.run()["package"])
 204 | +
 205 | +    def test_the_medley_row_flags_only_in_the_soft_pass_and_only_on_a_passing_verdict(self):
 206 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 207 | +        med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": [],
 208 | +               "hook_own": {"passes": True, "flagged": "stopping the scroll 2 of 5, needs 3"}}
 209 | +        row = lambda ok, soft: PK.inventory(**TestStage2a().base(t), medley=(ok, med), soft=soft,
 210 | +                                            who={"hook": "Scott Melker"})["medley"]
 211 | +        self.assertEqual((row(True, True)["status"], row(True, True)["flags"]), ("FLAGGED", [
 212 | +            "The opening clip (Scott Melker): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
 213 | +            "needs 3)."]))
 214 | +        self.assertEqual((row(True, False)["status"], "flags" in row(True, False)), ("PASS", False))
 215 | +        self.assertEqual(row(False, True)["status"], "FAIL")
 216 | +
 217 | +    def test_at_most_the_best_two_under_the_bar_open(self):
 218 | +        r, out = self.rig({"h": (2, 5, 5), "x": (2, 5, 4), "y": (1, 5, 5), "z": (2, 5, 3)}, True)
 219 | +        rec = out.get("prescreen") if out.get("package") else out["never_empty"]["soft_record"]["prescreen"]
 220 | +        rated = (out.get("hook_pool") or out["never_empty"]["soft_record"]["hook_pool"])["ratings"]
 221 | +        under = [m for m in ("h", "x", "z", "y") if m in rated]                       # hook_order: rating, then sum
 222 | +        self.assertEqual(list(rec["soft_hook_bar"]), under[:PK.HOOK_SOFT_MAX])
 223 | +        self.assertEqual(PK.HOOK_SOFT_MAX, 2)
 224 | +
 225 | +
 226 |  class TestTheDayCount(unittest.TestCase):
 227 |      def test_counted_per_day_ledger(self):
 228 |          with tempfile.TemporaryDirectory() as d:
 229 | 
```

---

pp-selectid: RULINGS 136 / 137 / 138, the hard/soft switch, STAGE 2b (1): THE CALIBRATED HOOK BAR (ruling 115) SOFT in
the never-empty pass. Stages 1 and 2a are LIVE: package.build runs the clean pass, and only when it seals nothing (and the
day allows) runs _build(soft=True). A soft gate there flags in one plain sentence per clip (ruling 138 (3)); at most 3
flags seal (package_pin.REVIEW_FLAGS_MAX, :42). The measured yield: the bar refused 12 of 18 hooks over 7 days. Files:
pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py, tests/package/test_medley.py (Rig.run
passes a test's build_kw).

THE CHANGE (only the never-empty pass; the clean pass is unchanged):
(a) hook_bar_under(m): the plain detail of a hook rated UNDER a floor BY THE BAR'S OWN RATER with every part measured
    ("stopping the scroll 2 of 5, needs 3"). None when it passes, a part is unmeasured, another back-end rated it, or no
    calibration is valid: those stay HARD (law L-m).
(b) hook_own(m) (the ONE record every bar check reads) reports passes=True plus "flagged" only for a hook that carries the
    soft mark "hook_bar_soft" AND is under the bar by (a). Every reader therefore follows with no change of its own:
    _can_open (package.py:1758), coherence's ok (:2089), medley's ok (:2153), ruling 62's last_clip_only (:2173),
    ruling 63's reorder (:3893), hook_weak (:3906), the coherence floors (:4222).
(c) _build sets the mark only when soft, on at most HOOK_SOFT_MAX = 2 hooks, the best by hook_order (:1762), after the
    ratings are attached and before rated_open is seen (:3342-3343: each opener pays the vision check before any angle,
    so the cap bounds the extra vision calls). The mark is popped with the old rating at the start of the hook stage, so a
    mark never carries in. The moments _build marks are its own copies: with_verdict (:1501, :1504) builds a new dict
    for every moment (:3200). The driver's spotlight pass gets the driver's own list (proof_ledger.py SPOT.build), never
    these copies.
(d) inventory: the "medley" row (the clips-alone verdict, which holds the hook's slot) is FLAGGED with one sentence
    ("The opening clip (<channel>): the checker rated it under the hook bar (<detail>).") only when soft, the verdict
    passed, and the verdict's hook_own carries "flagged". package_pin.SOFT_GATES adds "medley". flagged_ok (:387) still
    needs non-empty string flags and replayed False. The coherence row stays PASS (one doubt, flagged once).
(e) The wrapper's record label is now stage "2b".

TESTS (test_ruling_137, 6 new): (a)'s detail and every hard case; only a marked hook opens; END TO END through
test_medley's Rig (the real build, every model stubbed): the clean pass finds no hook, and the never-empty pass seals with
the medley row FLAGGED in the exact sentence, review_flags_of equal to it, gate_problems() empty, coherence PASS; a mark
carried in is never read; the row flags only in the soft pass and only on a passing verdict; at most the best 2 open.
Mutations: 12 of 12 killed.

PLEASE CHECK: (1) can a hook with no calibration, another rater, or an unmeasured part open, or can the clean pass open a
hook under the bar? (2) every reader of hook_own's "passes": does any one of them now let through something it should not
(e.g. ruling 62 / 63 / coherence)? (3) the cost bound on vision; (4) the plain sentence and the one-flag count; (5) the
tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
