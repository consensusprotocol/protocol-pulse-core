# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1330
# Branch: pp-selectid
# Generated: 2026-11-13 13:26 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1330/C1_STEP.diff (383 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 94d6b2f..bca94a8 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1964,9 +1964,65 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
   6 |      return rec
   7 |  
   8 |  
   9 | +def load_candidate(record, index=None, source=""):
  10 | +    """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. The candidate an earlier build's record (its package.json) holds: a
  11 | +    tried line-up that passed the clips-alone verdict (medley_ok True), with what a build needs to try it again AS IT WAS
  12 | +    JUDGED: its angle (text, moments, hook) and the angle's back-end (the writers' vendor and family, law L-x), its clips
  13 | +    in play order, its supply exception, the recorded verdict, and the seeds it was judged and written with (the angle's
  14 | +    index and the line-up's number in that angle), so every call it made is served from its recording and only what is
  15 | +    missing is paid for. index: the record's tried[] entry (None: the first that passed). Raises ValueError."""
  16 | +    tried = record.get("tried") or []
  17 | +    if index is None:
  18 | +        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and t.get("lineup")), None)
  19 | +        if index is None:
  20 | +            raise ValueError("no line-up in this record passed the clips-alone verdict")
  21 | +    if not 0 <= index < len(tried):
  22 | +        raise ValueError(f"the record has no tried[{index}] ({len(tried)} line-ups tried)")
  23 | +    t = tried[index]
  24 | +    if t.get("medley_ok") is not True or not t.get("lineup"):
  25 | +        raise ValueError(f"tried[{index}] did not pass the clips-alone verdict")
  26 | +    med = t.get("medley") or {}
  27 | +    if med.get("measured") is not True or med.get("replayed") is not False:
  28 | +        raise ValueError(f"tried[{index}]'s clips-alone verdict was not measured live (law L-j)")
  29 | +    ai, angles = int(t["angle"]) - 1, record.get("angles") or []
  30 | +    if not 0 <= ai < len(angles) or angles[ai].get("angle") != t.get("text"):
  31 | +        raise ValueError(f"tried[{index}]'s angle is not the record's angle {ai + 1}")
  32 | +    a = {k: angles[ai][k] for k in ("angle", "moments", "hook")}
  33 | +    if a["hook"] != t["lineup"][0]:
  34 | +        raise ValueError(f"tried[{index}] does not open on its angle's hook (ruling 59 c)")
  35 | +    if not record.get("angle_backend"):
  36 | +        raise ValueError("the record names no angle back-end")
  37 | +    n = sum(1 for u in tried[:index + 1] if u.get("angle") == t["angle"] and u.get("lineup"))   # its line-up number
  38 | +    return {"source": source, "index": index, "ai": ai, "n_lineup": n, "angle": a,
  39 | +            "angle_backend": record["angle_backend"], "angle_tried": list(record.get("angle_tried") or []),
  40 | +            "lineup": list(t["lineup"]), "supply_exception": t.get("supply_exception"), "medley": med}
  41 | +
  42 | +
  43 | +def candidate_lineup(router, candidate, cleared, now):
  44 | +    """RULING 66: the candidate's line-up as THIS build's pool holds it, or why it is closed. Every clip must still be
  45 | +    cleared (a clip delivered, aged out or failing a gate closes it), its hook must still open (its cached rating >=
  46 | +    HOOK_MIN, G17a), and exactly its clips, in its order, must still form a line-up under lineup_for's own rules
  47 | +    (the seconds, the channels, price predictions, short clips, trims, the render's STAND_ALONE).
  48 | +    -> (segs, None) or (None, why)."""
  49 | +    ids = list(candidate["lineup"])
  50 | +    if router.backends.get(candidate.get("angle_backend")) is None:
  51 | +        return None, f"its angle's back-end {candidate.get('angle_backend')!r} is not in the router"
  52 | +    gone = [mid for mid in ids if mid not in cleared]
  53 | +    if gone:
  54 | +        return None, f"no longer cleared in this pool (delivered, aged out, or a gate fails): {gone}"
  55 | +    if not can_open(cleared[ids[0]]):
  56 | +        return None, f"its hook no longer opens (rating >= {HOOK_MIN} and G17a): {ids[0]}"
  57 | +    segs = lineup_for(dict(candidate["angle"], moments=ids), cleared, clips=(len(ids) - 1, len(ids) - 1),
  58 | +                      repeat_ok=candidate.get("supply_exception") is not None, need_onset=True,
  59 | +                      need_stand_alone=True, now=now, hook_only=True)
  60 | +    if segs is None or [m["moment_id"] for m in segs] != ids:
  61 | +        return None, "its clips no longer form its line-up under the line-up rules (lineup_for)"
  62 | +    return segs, None
  63 | +
  64 | +
  65 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  66 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  67 | -          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name=""):
  68 | +          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None):
  69 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  70 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  71 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  72 | @@ -1981,6 +2037,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  73 |      ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
  74 |      writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
  75 |      freshness next), each line-up opens on its angle's own hook and never swaps it.
  76 | +    RULING 66, A PASSED LINE-UP IS KEPT: candidate (load_candidate) tries ONLY that line-up, after the same pool stages:
  77 | +    no angle is asked for (its own angle and back-end), its clips must still form it (candidate_lineup), and it is
  78 | +    judged and written with its own seeds, so its recorded calls are served from their recordings; it is never
  79 | +    re-lined or swapped (a failing gate closes it: out["candidate"]).
  80 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
  81 |      t0 = time.time()
  82 |      usd0 = _spent(spend)
  83 | @@ -2111,7 +2171,21 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  84 |      per = max(1, max_angles // len(offered))
  85 |      lo, hi = medley_content_range()
  86 |      angles, angle_reply, errs = None, None, []
  87 | -    for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
  88 | +    cand_segs = None
  89 | +    if candidate is not None:                         # RULING 66 (13:18): A PASSED LINE-UP IS KEPT: its own angle and
  90 | +        cand_segs, why_c = candidate_lineup(router, candidate, cleared, ctx.now)   # line-up; no angle is asked for
  91 | +        out["candidate"] = {"source": candidate.get("source"), "index": candidate.get("index"),
  92 | +                            "lineup": list(candidate["lineup"]), "closed": why_c}
  93 | +        if why_c is not None:
  94 | +            out["why_none"] = f"ruling 66: the candidate is closed: {why_c}"
  95 | +            log(f"  {out['why_none']}")
  96 | +            return out
  97 | +        from types import SimpleNamespace
  98 | +        b = router.backends[candidate["angle_backend"]]
  99 | +        angles = [dict(candidate["angle"])]
 100 | +        angle_reply = SimpleNamespace(backend=candidate["angle_backend"], vendor=b.vendor, family=b.family,
 101 | +                                      tried=[list(x) for x in candidate.get("angle_tried") or []])
 102 | +    for seed in ((7, 8) if candidate is None else ()):   # one re-ask on an out-of-contract reply (never served again)
 103 |          r = None
 104 |          try:
 105 |              r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 106 | @@ -2132,7 +2206,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 107 |      if not angles:
 108 |          return out
 109 |      out.pop("why_none", None)
 110 | -    missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}]
 111 | +    missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}] if candidate is None else []
 112 |      if missing and len(angles) < max_angles:            # RULING 64: a passing hook left without an angle is asked
 113 |          k2, r = max_angles - len(angles), None          # for, once, written for exactly those hooks (12:00)
 114 |          try:
 115 | @@ -2175,7 +2249,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 116 |          a_by[mid] = off_writers(mid) or a_by[mid]
 117 |      writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
 118 |          {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
 119 | -    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
 120 | +    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)" if candidate is None else
 121 | +        f"  ruling 66: the candidate {candidate.get('source')} tried[{candidate.get('index')}] (angle "
 122 | +        f"{candidate['ai'] + 1} line-up {candidate['n_lineup']}), as judged: its angle from {angle_reply.backend}, "
 123 | +        f"no angle asked ({time.time() - t0:.0f} s)")
 124 |      doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 125 |  
 126 |      def over_budget(ai):
 127 | @@ -2298,9 +2375,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 128 |      total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 129 |      judged, bad_pairs, spins = {}, set(), 0               # 12:00: verdicts by line-up; ruling 63's unfollowable pairs
 130 |      with ThreadPoolExecutor(max_workers=8) as pool:
 131 | -        for ai, angle in enumerate(angles):
 132 | -            dropped, n_lineup, swapped = set(), 0, None
 133 | +        for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 134 | +            dropped, n_lineup, swapped, filled = set(), 0, None, None
 135 | +            if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 136 | +                n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 137 |              while total < lineups and not out["packages"] and not out.get("budget_stop"):
 138 | +                if candidate is not None and n_lineup >= candidate["n_lineup"]:
 139 | +                    break                                 # RULING 66: the candidate alone, never re-lined or swapped
 140 |                  if over_budget(ai):
 141 |                      break
 142 |                  if swapped is not None:                   # ruling 41: the swapped line-up is judged next
 143 | @@ -2322,7 +2403,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 144 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 145 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 146 |                         "supply_exception": exception, "attempts": [],
 147 | -                       **({"pool_filled": filled} if filled else {})}
 148 | +                       **({"pool_filled": filled} if filled else {}),
 149 | +                       **({"candidate": candidate.get("source")} if candidate is not None else {})}
 150 |                  out["tried"].append(rec)
 151 |                  if segs is None:
 152 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 153 | @@ -2350,6 +2432,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 154 |                      f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 155 |                      f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 156 |                  labs = labels(len(segs))
 157 | +                if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
 158 | +                    rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
 159 | +                    break
 160 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 161 |                      by_lab = dict(zip(labs, segs))
 162 |                      cl = med.get("clips") or {}
 163 | @@ -2597,6 +2682,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 164 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
 165 |                  break
 166 |      out["package"] = out["packages"][0] if out["packages"] else None
 167 | +    if candidate is not None:                             # RULING 66: what became of the candidate
 168 | +        t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 169 | +        out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 170 |      s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
 171 |      out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
 172 |                       "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
 173 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 174 | index 3310302..ed6cbba 100644
 175 | --- a/tests/package/proof_ledger.py
 176 | +++ b/tests/package/proof_ledger.py
 177 | @@ -20,7 +20,13 @@
 178 |  Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
 179 |  package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
 180 |  
 181 | +RULING 66 (13:18), A PASSED LINE-UP IS KEPT: --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
 182 | +clips-alone verdict in that earlier build's record (its tried[N]; default the first that passed), after the same pool
 183 | +stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
 184 | +recordings and only what is missing is paid for; never re-lined, swapped or a new angle.
 185 | +
 186 |  Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
 187 | +                                             [--from-candidate BUILD_DIR[:N]]
 188 |    tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
 189 |                         tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
 190 |  """
 191 | @@ -83,6 +89,9 @@ def main(argv=None):
 192 |      ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 193 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 194 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 195 | +    ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 196 | +                    help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
 197 | +                         "record (its tried[N]; default the first that passed), as it was judged")
 198 |      a = ap.parse_args(argv)
 199 |      now = datetime.now(timezone.utc)
 200 |      try:                                                 # read before anything is written (glm C2 N-4)
 201 | @@ -92,8 +101,16 @@ def main(argv=None):
 202 |              raise ValueError("--since has no time zone")
 203 |          if since > now:
 204 |              raise ValueError(f"since {since.isoformat()} is after now")
 205 | +        cand = None
 206 | +        if a.from_candidate:                             # RULING 66: read before anything is written
 207 | +            cdir, sep, idx = a.from_candidate.rpartition(":")
 208 | +            cdir, idx = (cdir, idx) if sep and idx.isdigit() else (a.from_candidate, "")
 209 | +            with open(os.path.join(cdir, "package.json")) as f:
 210 | +                cand = PK.load_candidate(json.load(f), int(idx) if idx else None,
 211 | +                                         source=os.path.relpath(os.path.abspath(cdir), REPO))
 212 |      except (OSError, ValueError, KeyError, TypeError) as e:
 213 | -        print(f"REFUSED: the delivered pins or 'since' cannot be read ({type(e).__name__}: {e})", file=sys.stderr)
 214 | +        print(f"REFUSED: the delivered pins, 'since' or the candidate cannot be read ({type(e).__name__}: {e})",
 215 | +              file=sys.stderr)
 216 |          return 2
 217 |      out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
 218 |      try:
 219 | @@ -106,7 +123,8 @@ def main(argv=None):
 220 |      ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 221 |      say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
 222 |          f"{now.isoformat(timespec='seconds')}, since {since.isoformat(timespec='seconds')} "
 223 | -        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h")
 224 | +        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h" +
 225 | +        (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
 226 |      say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 227 |          f"{len(delivered)} clip spans out")
 228 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 229 | @@ -138,7 +156,8 @@ def main(argv=None):
 230 |                     step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 231 |                     hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 232 |                     scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 233 | -                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 234 | +                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 235 | +                   candidate=cand)                                                     # ruling 66
 236 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 237 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 238 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 239 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 240 | index ea0699e..03130d7 100644
 241 | --- a/tests/package/test_medley.py
 242 | +++ b/tests/package/test_medley.py
 243 | @@ -523,7 +523,7 @@ class Rig:
 244 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 245 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 246 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 247 | -                 cached=False):
 248 | +                 cached=False, candidate=None):
 249 |          import providers as P
 250 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 251 |          self.takeaways, self.spend = list(takeaways or []), spend
 252 | @@ -532,6 +532,7 @@ class Rig:
 253 |          self.verdicts = verdicts                           # ruling 56: {pid: verdict} in the integrator's file shape
 254 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 255 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 256 | +        self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 257 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 258 |          self.screens, self.events, self.a_seen = [], [], []
 259 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 260 | @@ -592,6 +593,7 @@ class Rig:
 261 |  
 262 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 263 |          self.medley_calls.append([m["moment_id"] for m in segs])
 264 | +        self.seeds.append(("medley", seed))
 265 |          ok, flagged, ratings, line = self.medleys.pop(0)
 266 |          labs = PK.labels(len(segs))
 267 |          v = verdict(labs, flagged, ratings, line)
 268 | @@ -602,6 +604,7 @@ class Rig:
 269 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
 270 |              raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
 271 |          self.write_calls.append(([m["moment_id"] for m in segs], join))
 272 | +        self.seeds.append(("write", seed))
 273 |          self.write_avoid.append(avoid_vendor)
 274 |          self.a_seen.append({m["moment_id"]: a_by[m["moment_id"]]["backend"] for m in segs})
 275 |          b = self.writes.pop(0)
 276 | @@ -646,7 +649,7 @@ class Rig:
 277 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 278 |                                                               "replayed": False}),
 279 |          }
 280 | -        kw, path = {}, None
 281 | +        kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
 282 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 283 |              import tempfile
 284 |              fd, path = tempfile.mkstemp(suffix=".json")
 285 | @@ -1585,6 +1588,97 @@ class TestRulings6264Search(unittest.TestCase):
 286 |          self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free
 287 |  
 288 |  
 289 | +class TestRuling66Candidate(unittest.TestCase):
 290 | +    """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
 291 | +    from it asks no angle, tries exactly its clips in its order with its own seeds (so its recorded calls are served
 292 | +    from their recordings), and never re-lines or swaps it: a failing gate closes it."""
 293 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 294 | +    TEXT, T2 = "Nobody controls Bitcoin.", "Nobody can change it."
 295 | +    MED = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
 296 | +           "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}
 297 | +
 298 | +    def record(self, tried=None):
 299 | +        return {"tried": tried if tried is not None else [
 300 | +            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y"], "supply_exception": None, "medley": self.MED,
 301 | +             "medley_ok": True},
 302 | +            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "z"], "supply_exception": None,
 303 | +             "medley": dict(self.MED, clips={"hook": 4, "clip_01": 2, "clip_02": 4}), "medley_ok": False}],
 304 | +            "angles": [{"angle": self.TEXT, "moments": ["h", "x", "y", "z"], "hook": "h"},
 305 | +                       {"angle": self.T2, "moments": ["x", "h", "y", "z"], "hook": "x"}],
 306 | +            "angle_backend": "heimdall:deepseek", "angle_tried": []}
 307 | +
 308 | +    def test_the_record_gives_the_first_passing_line_up_with_its_seeds(self):
 309 | +        c = PK.load_candidate(self.record(), source="proof/ledger_x")
 310 | +        self.assertEqual((c["index"], c["ai"], c["n_lineup"], c["lineup"], c["angle"]["hook"], c["angle_backend"]),
 311 | +                         (0, 0, 1, ["h", "x", "y"], "h", "heimdall:deepseek"))
 312 | +        self.assertEqual(c["medley"], self.MED)                              # the verdict travels with it
 313 | +        with self.assertRaises(ValueError):
 314 | +            PK.load_candidate(self.record(), 1)                              # tried[1] did not pass
 315 | +        r = self.record()
 316 | +        for bad in (dict(r, tried=[]),                                       # nothing passed
 317 | +                    dict(r, angles=[dict(r["angles"][0], angle="another angle")]),   # not its angle
 318 | +                    dict(r, tried=[dict(r["tried"][0], medley=dict(self.MED, replayed=True))]),   # replayed (L-j)
 319 | +                    dict(r, tried=[dict(r["tried"][0], lineup=["x", "h", "y"])])):   # not its angle's hook
 320 | +            with self.assertRaises(ValueError):
 321 | +                PK.load_candidate(bad)
 322 | +
 323 | +    def test_the_line_up_number_counts_only_this_angles_line_ups(self):
 324 | +        rec = self.record(tried=[
 325 | +            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y"], "medley": self.MED, "medley_ok": False},
 326 | +            {"angle": 1, "text": self.TEXT, "lineup": None},
 327 | +            {"angle": 2, "text": self.T2, "lineup": ["x", "h", "y"], "medley": self.MED, "medley_ok": False},
 328 | +            {"angle": 2, "text": self.T2, "lineup": ["x", "h", "z"], "medley": self.MED, "medley_ok": True}])
 329 | +        c = PK.load_candidate(rec)
 330 | +        self.assertEqual((c["index"], c["ai"], c["n_lineup"], c["lineup"]), (3, 1, 2, ["x", "h", "z"]))
 331 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], hooks={"x": (5, 5, 5)},
 332 | +                  candidate=c)
 333 | +        out = rig.run()
 334 | +        self.assertIsNotNone(out["package"])
 335 | +        self.assertEqual(rig.seeds, [("medley", 7 + 2 + 10), ("write", 7 + 1 + 10 + 200)])   # angle 2, line-up 2's
 336 | +
 337 | +    def test_a_build_from_the_candidate_asks_no_angle_and_judges_it_with_its_own_seeds(self):
 338 | +        c = PK.load_candidate(self.record(), source="proof/ledger_x")
 339 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c)
 340 | +        out = rig.run()
 341 | +        self.assertIsNotNone(out["package"])
 342 | +        self.assertEqual([r for r, _ in rig.prompts if r == "angle_write"], [])   # no angle asked for
 343 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
 344 | +        self.assertEqual(rig.seeds, [("medley", 8), ("write", 108)])        # angle 1 line-up 1's, as recorded
 345 | +        self.assertEqual(out["tried"][0]["candidate"], "proof/ledger_x")
 346 | +        self.assertEqual((out["candidate"]["closed"], out["candidate"]["result"]), (None, "PACKAGE"))
 347 | +        self.assertEqual(out["angle_backend"], "heimdall:deepseek")          # L-x: the writers' vendor as recorded
 348 | +
 349 | +    def test_a_candidate_whose_clip_left_the_pool_is_closed_before_any_call(self):
 350 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [], [], uncuttable={"y"}, candidate=PK.load_candidate(self.record()))
 351 | +        out = rig.run()
 352 | +        self.assertIsNone(out["package"])
 353 | +        self.assertTrue(out["why_none"].startswith("ruling 66: the candidate is closed: no longer cleared"),
 354 | +                        out["why_none"])
 355 | +        self.assertIn("'y'", out["candidate"]["closed"])
 356 | +        self.assertEqual((rig.medley_calls, rig.write_calls, [r for r, _ in rig.prompts if r == "angle_write"]),
 357 | +                         ([], [], []))
 358 | +
 359 | +    def test_a_candidate_failing_its_verdict_now_is_closed_never_re_lined(self):
 360 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE)], [],
 361 | +                  candidate=PK.load_candidate(self.record()))
 362 | +        out = rig.run()
 363 | +        self.assertIsNone(out["package"])
 364 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])               # no swap, no second line-up
 365 | +        self.assertEqual(len(out["tried"]), 1)
 366 | +        self.assertEqual(out["tried"][0]["why"], "ruling 66: the candidate fails its clips-alone verdict now: closed")
 367 | +        self.assertEqual(out["candidate"]["result"], out["tried"][0]["why"])
 368 | +
 369 | +    def test_exactly_its_clips_never_a_subset(self):
 370 | +        ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
 371 | +        rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
 372 | +                                  "supply_exception": None, "medley": self.MED, "medley_ok": True}])
 373 | +        self.assertEqual(PK.lineup_for(rec["angles"][0], {m["moment_id"]: m for m in ms}),
 374 | +                         [ms[0], ms[1], ms[2]])                              # the search alone would take a subset
 375 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], None, "none")], [], candidate=PK.load_candidate(rec))
 376 | +        rig.run()
 377 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"]])
 378 | +
 379 | +
 380 |  class TestRuling65Caption(unittest.TestCase):
 381 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 382 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 383 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, sealed in a pin the integrator
renders). Your role: a strict reviewer of a build path that may seal a pin. Only state what you can verify from the
diff; if uncertain, say so; do not guess.

Background (static):
- A build screens the pool (cached step-A verdicts, the render's clip-scorer verdicts, the second recognition pass
  and CUTTABLE, the hook onset G17a, cached hook ratings, a second vendor's step A).
- It then asks a writer model for ANGLES. Each line-up is judged on the clips ALONE (medley(), seed
  7 + n_lineup + 10 * ai). A line-up that passes gets at most 2 writes (write_takeaway, seed
  7 + w_used + 10 * ai + 100 * n_lineup). Each write is gated: the cheap checks; the paid fidelity verdict and context
  integrity; ruling 65's caption-only write; coherence. Then the sealed inventory, and the pin.
- The router records every exchange by sha256(role, back-end, prompt, max_tokens, seed, system). A LIVE run serves a
  recorded reply to identical bytes with cached=True, replayed=False: free, and deliverable. An offline replay sets
  replayed=True, never deliverable (law L-j).
- In the 12:22 build (record tests/package/proof/ledger_20261113_172217), angle 1 line-up 1 passed the clips-alone
  verdict (Simply Bitcoin -> CNBC Television -> Scott Melker, 39.3 s, 4/4/4, no flagged join). Its writes' takeaway
  and title passed; its caption failed fidelity. Ruling 65 (committed since) now gives a caption-only write.
- The 13:05 rebuild could not reach that line-up. The pool had changed, so the angle prompt differed and the writer
  wrote other angles.

The order this diff implements (ORCHESTRATOR ORDER 13:18, verbatim):
"66. A PASSED LINE-UP IS KEPT. Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE (clips,
order, the verdict, the gated takeaway and title if written) and stays a candidate until one of its clips is delivered,
ages out, or fails a gate. Every build first tries the open candidates, newest first, before asking for new angles.
RIGHT NOW, before anything else and without waiting for the running build's remaining line-ups: take the 12:22 build's
passing line-up from its record (ledger_20261113_172217: Simply Bitcoin -> CNBC Television -> Scott Melker, 39.3 s,
hook 4 / 4 / 4, no flagged join; takeaway and title gated in its writes), run ONLY what is missing: ruling 65's
caption-only write (then the fixed fallback if it fails), the coherence verdict, your verifier, and seal. Use the
recorded verdicts; pay only for the new calls. If the smallest way to do that is a --from-candidate path on
proof_ledger, build that as the audited change for 66; if it needs the audit before it may seal, run the audit now, it
is one small change."

The change (pipeline/package.py, tests/package/proof_ledger.py, tests/package/test_medley.py):
1. load_candidate(record, index=None, source) reads an earlier build's package.json and returns the candidate.
   - It takes the first tried[] entry with medley_ok True, or the given index, which must have passed.
   - It returns: the angle {angle, moments, hook} (record["angles"][ai], whose text must equal the entry's), the
     angle's back-end and the line-up's ids in order, the supply exception, the recorded verdict, and the seeds:
     ai = entry["angle"] - 1, and n_lineup = the count of this angle's entries with a line-up up to it (exactly the
     loop's counter).
   - Refused (ValueError): no passing entry; a verdict not measured live (replayed / unmeasured); an angle mismatch;
     a line-up not opening on its angle's hook; no angle back-end.
2. candidate_lineup(router, candidate, cleared, now) gives the candidate as THIS build's pool holds it, or why it is
   closed:
   - every clip still cleared (a clip delivered, aged out or failing a gate is gone from `cleared`);
   - the hook still can_open (its cached rating >= 4, G17a);
   - exactly its clips in its order still form a line-up under lineup_for's own rules: the seconds, channels, price
     predictions, short clips, trims, STAND_ALONE. clips=(n, n) pins the clip count so the search cannot pick a subset.
3. build(..., candidate=None). With a candidate, after the SAME pool stages:
   - candidate_lineup; if closed, return why_none "ruling 66: the candidate is closed: ..." before any further call;
   - no angle call and no follow-up angle call; angles = [its angle]; the writers' vendor and family come from the
     recorded angle back-end (L-x);
   - the loop runs once, with ai = the recorded index and n_lineup starting at the recorded number - 1, and the
     candidate's segments preset as `swapped`, so the first iteration judges exactly them with the recorded seeds;
   - a guard at the loop's top ends it after that line-up (never re-lined, swapped or reordered);
   - a failing clips-alone verdict closes it at once;
   - everything else is the unchanged code: the verdict call, the writes, every gate, ruling 65, coherence, the
     inventory and the pin.
   - out["candidate"] records the source, index, line-up, closed-why and result; the tried entry names its candidate.
   - `filled` is now initialised per angle, because a candidate's first iteration takes the swapped branch, where it
     was never set.
4. proof_ledger.py --from-candidate BUILD_DIR[:N]: the record is read before anything is written (a bad record refuses
   the run, exit 2), logged in the header line, and passed to build(candidate=...).
5. Tests (TestRuling66Candidate, 6): the loader and its refusals; the line-up number; a build from a candidate asking
   no angle, with the seeds (8, 108) and (19, 218); closed before any call when a clip left the pool; closed (one
   verdict call, no re-line) when its verdict fails now; exactly its clips (the plain search would take a subset).
   test_medley 131 OK.

Stated readings (say so if you read the order differently):
- K1: "use the recorded verdicts; pay only for the new calls" is met by asking the SAME calls with the SAME bytes and
  seeds. The router then serves each recorded reply (cached, live, deliverable), and pays for a call only when its
  bytes differ. Then it is judged afresh on the bytes that will be sealed, which is L-j.
  - We do NOT paste the recorded verdict into a package without asking. A recording is served only for byte-identical
    prompts, which proves the verdict is about these exact clips and lines.
- K2: the candidate goes through every pool stage of THIS build (delivered pins, the 72 h window, step A, CUTTABLE,
  G17a, the hook rating, the second vendor). Order 66's "until one of its clips is delivered, ages out, or fails a
  gate" is then exactly "a clip left `cleared`, or a line-up rule fails".
- K3: this change is the --from-candidate path the order names as the audited change for 66, for RIGHT NOW. "Every
  build first tries the open candidates, newest first" (a standing registry read by every build) is the next change,
  built on load_candidate / build(candidate=).
- K4: in candidate mode a failing clips-alone verdict closes the candidate at once; ruling 62/63's retries and swaps
  are not run. The order says to try that line-up, and a swap would be a new line-up.

Check in particular:
- that the recorded seeds reproduce exactly (ai, n_lineup) for any tried entry, including after a None line-up and
  across angles;
- that no path in candidate mode calls the angle writer, judges a second line-up, or seals without every gate;
- L-x (the writers' vendor and family);
- the `filled` initialisation (no change to normal builds);
- the guard and the closure paths;
- the proof_ledger refusal path.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

