# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0510
# Branch: pp-selectid
# Generated: 2026-11-13 05:09 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0510/C1_STEP.diff (360 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ac10906d..3b4d2249 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -72,6 +72,14 @@ COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >
   6 |  BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
   7 |  BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
   8 |  BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
   9 | +LINEUPS_PER_BUILD = 8              # RULING 41 (04:58 ET Nov 13): up to 8 line-ups per BUILD, over every angle. A clips-
  10 | +                                   # alone failure is answered by swapping the segments rated below the bar (swap_lineup);
  11 | +                                   # the bar itself is unchanged
  12 | +SEARCH_USD_REPORTED = 3.00         # ruling 41: a build may spend $3 (vendor-reported) searching, reported in out["search"];
  13 | +SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE delivered (its own line-up). The estimate
  14 | +                                   # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
  15 | +SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
  16 | +SWAP_TOP = 6                       # candidates read per swapped place, best by score first
  17 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  18 |  WRITER_DEADLINE_S = 300.0          # ruling 5: one writer call never waits more than 5 min; it fails over (deepseek ->
  19 |                                     # qwen -> xAI in the writer chain) and the failover is recorded
  20 | @@ -612,6 +620,79 @@ def no_role_on_screen(m):
  21 |      return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
  22 |  
  23 |  
  24 | +def lineup_ok(segs, crange=None, repeat_ok=False):
  25 | +    """The rules lineup_for applies, checked on a GIVEN line-up in play order -> (ok, why): the hook can open (hook
  26 | +    eligibility and the G17a measure), every clip is clip-eligible, the hook + LY_CLIPS clips, one segment per channel
  27 | +    (or, repeat_ok, one channel with two clips from two videos: L-y 4), at most PRICE_PREDICTIONS_MAX price predictions,
  28 | +    a clip under SHORT_CLIP_S only last, the seconds inside crange, and the render's STAND_ALONE (stand_alone_check)."""
  29 | +    lo, hi = crange or medley_content_range()
  30 | +    h, clips = segs[0], segs[1:]
  31 | +    if not LY_CLIPS[0] <= len(clips) <= LY_CLIPS[1]:
  32 | +        return False, f"{len(clips)} clips"
  33 | +    if not ((h.get("eligibility") or {}).get("hook", {}).get("ok") and (h.get("hook_onset") or {}).get("pass") is True):
  34 | +        return False, "the hook cannot open"
  35 | +    if not all((m.get("eligibility") or {}).get("clip", {}).get("ok") for m in clips):
  36 | +        return False, "a clip is not clip-eligible"
  37 | +    chans = [m["channel_id"] for m in segs]
  38 | +    if len(set(chans)) != len(segs) and not (repeat_ok and len(set(chans)) == len(segs) - 1 and
  39 | +                                             len({m["video_id"] for m in segs}) == len(segs)):
  40 | +        return False, "one segment per channel"
  41 | +    if sum("price_prediction" in m.get("risk", []) for m in segs) > PRICE_PREDICTIONS_MAX:
  42 | +        return False, "price predictions"
  43 | +    if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  44 | +        return False, "a short clip that is not last"
  45 | +    dur = sum(m["duration_s"] for m in segs)
  46 | +    if not lo <= dur <= hi:
  47 | +        return False, f"{dur:.1f} s outside {lo}-{hi} s"
  48 | +    if not stand_alone_check(segs)["ok"]:
  49 | +        return False, "the render's STAND_ALONE"
  50 | +    return True, "ok"
  51 | +
  52 | +
  53 | +def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  54 | +    """RULING 41: the next line-up after a clips-alone failure. Every segment in `weak` (moment ids rated below the
  55 | +    bar) is swapped AT ITS PLACE for the next candidate by score from the whole cleared pool: the hook for the next hook
  56 | +    by its first 2 s (scores.hook_first_2s), a clip for the next clip by rank_score. The segments rated 4-5 stay where
  57 | +    they are. The first combination (up to SWAP_TOP candidates per place, in score order) that passes lineup_ok wins,
  58 | +    one clip per channel first, then L-y 4's supply exception. -> (segs, {old id: new id}) or (None, None)."""
  59 | +    used = {m["moment_id"] for m in segs}
  60 | +    places = [i for i, m in enumerate(segs) if m["moment_id"] in weak]
  61 | +    if not places:
  62 | +        return None, None
  63 | +    free = [m for m in pool.values() if m["moment_id"] not in used and m["moment_id"] not in avoid]
  64 | +
  65 | +    def cands(i):
  66 | +        if i == 0:
  67 | +            c = [m for m in free if (m.get("eligibility") or {}).get("hook", {}).get("ok")
  68 | +                 and (m.get("hook_onset") or {}).get("pass") is True]
  69 | +            c.sort(key=lambda m: (-m["scores"]["hook_first_2s"], -m["rank_score"], m["moment_id"]))
  70 | +        else:
  71 | +            c = [m for m in free if (m.get("eligibility") or {}).get("clip", {}).get("ok")]
  72 | +            c.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
  73 | +        return c[:SWAP_TOP]
  74 | +    options = [cands(i) for i in places]
  75 | +    for repeat_ok in (False, True):
  76 | +        for combo in itertools.product(*options):
  77 | +            if len({m["moment_id"] for m in combo}) != len(combo):
  78 | +                continue
  79 | +            new = list(segs)
  80 | +            for i, m in zip(places, combo):
  81 | +                new[i] = m
  82 | +            if lineup_ok(new, crange, repeat_ok)[0]:
  83 | +                return new, {segs[i]["moment_id"]: m["moment_id"] for i, m in zip(places, combo)}
  84 | +    return None, None
  85 | +
  86 | +
  87 | +def supply_exception(segs, ctx):
  88 | +    """L-y 4: the reason a line-up takes two clips from one channel (two videos), else None."""
  89 | +    rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs) if sum(m["channel_id"] == c for m in segs) > 1]
  90 | +    if not rep:
  91 | +        return None
  92 | +    return (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
  93 | +            f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
  94 | +            f" gives two clips, from two videos (L-y 4)")
  95 | +
  96 | +
  97 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  98 |                 need_stand_alone=False):
  99 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 100 | @@ -1052,7 +1133,7 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 101 |  
 102 |  
 103 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 104 | -          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 105 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD):
 106 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 107 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 108 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 109 | @@ -1142,19 +1223,32 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 110 |      doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 111 |  
 112 |      def over_budget(ai):
 113 | -        """Ruling 5 (22:40): per package 15 min wall / $1.50 reported / the $5 estimate ceiling. Checked before every
 114 | -        line-up and every write (audit 2240 C1, glm), not only when an angle ends. -> the stop record, or None."""
 115 | +        """The SEARCH budget (ruling 41, 04:58): a build may spend $3.00 vendor-reported searching ($10.00 estimate
 116 | +        ceiling), inside SEARCH_WALL_S. Checked before every line-up and every write. -> the stop record (it ends the
 117 | +        build), or None. Ruling 5's 15 min / $1.50 is per PACKAGE delivered: package_over()."""
 118 |          used_s = time.time() - t0
 119 |          est, rep = (a - b for a, b in zip(_spent(spend), usd0))
 120 | -        if used_s <= BUDGET_WALL_S and rep <= BUDGET_USD_REPORTED and est <= BUDGET_USD_ESTIMATE:
 121 | +        if used_s <= SEARCH_WALL_S and rep <= SEARCH_USD_REPORTED and est <= SEARCH_USD_ESTIMATE:
 122 |              return None
 123 | -        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: {used_s:.0f} s of {BUDGET_WALL_S:.0f} s wall / "
 124 | -                           f"${rep:.2f} of ${BUDGET_USD_REPORTED:.2f} reported / ${est:.2f} of the "
 125 | -                           f"${BUDGET_USD_ESTIMATE:.2f} estimate ceiling (ruling 5, 22:40)")
 126 | +        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: the search spent {used_s:.0f} s of "
 127 | +                           f"{SEARCH_WALL_S:.0f} s / ${rep:.2f} of ${SEARCH_USD_REPORTED:.2f} reported / ${est:.2f} of "
 128 | +                           f"the ${SEARCH_USD_ESTIMATE:.2f} estimate ceiling (ruling 41, 04:58)")
 129 |          out["budget_stop"] = {"seconds": round(used_s, 1), "usd_reported": round(rep, 4), "usd_estimate": round(est, 4),
 130 |                                "angles_tried": ai + 1, "angles": len(angles)}
 131 |          return out["budget_stop"]
 132 |  
 133 | +    def package_over(line):
 134 | +        """Ruling 5 (22:40) as ruling 41 reads it: per PACKAGE delivered, 15 min wall and $1.50 reported (the $5
 135 | +        estimate ceiling), counted from its own line-up's clips-alone verdict (line = (time, spend at that moment)).
 136 | +        -> why this line-up stops (the search goes on), or None."""
 137 | +        l_s = time.time() - line[0]
 138 | +        l_est, l_rep = (a - b for a, b in zip(_spent(spend), line[1]))
 139 | +        if l_s <= BUDGET_WALL_S and l_rep <= BUDGET_USD_REPORTED and l_est <= BUDGET_USD_ESTIMATE:
 140 | +            return None
 141 | +        return (f"this line-up's package spent {l_s:.0f} s of {BUDGET_WALL_S:.0f} s / ${l_rep:.2f} of "
 142 | +                f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
 143 | +                f"per package delivered: ruling 41)")
 144 | +
 145 |      def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
 146 |          """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 147 |          viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 148 | @@ -1243,23 +1337,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 149 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 150 |          return pk
 151 |  
 152 | +    total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 153 |      with ThreadPoolExecutor(max_workers=8) as pool:
 154 |          for ai, angle in enumerate(angles):
 155 | -            dropped, n_lineup = set(), 0
 156 | -            while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
 157 | +            dropped, n_lineup, swapped = set(), 0, None
 158 | +            while total < lineups and not out["packages"] and not out.get("budget_stop"):
 159 |                  if over_budget(ai):
 160 |                      break
 161 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 162 | -                                             need_stand_alone=True), None
 163 | -                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 164 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 165 | -                                     need_stand_alone=True)
 166 | -                    if segs is not None:
 167 | -                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 168 | -                               if sum(m["channel_id"] == c for m in segs) > 1]
 169 | -                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 170 | -                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 171 | -                                     f" gives two clips, from two videos (L-y 4)")
 172 | +                if swapped is not None:                   # ruling 41: the swapped line-up is judged next
 173 | +                    segs, swapped = swapped, None
 174 | +                    exception = supply_exception(segs, ctx)
 175 | +                else:
 176 | +                    segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 177 | +                                                 need_stand_alone=True), None
 178 | +                    if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
 179 | +                        segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 180 | +                                          need_stand_alone=True)
 181 | +                        if segs is not None:
 182 | +                            exception = supply_exception(segs, ctx)
 183 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 184 |                         "supply_exception": exception, "attempts": []}
 185 |                  out["tried"].append(rec)
 186 | @@ -1267,6 +1362,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 187 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 188 |                      break
 189 |                  n_lineup += 1
 190 | +                total += 1
 191 | +                line = (time.time(), _spent(spend))         # this line-up's package budget counts from here (ruling 41)
 192 |                  ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 193 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 194 |                  log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 195 | @@ -1276,14 +1373,18 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 196 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 197 |                      by_lab = dict(zip(labs, segs))
 198 |                      weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 199 | -                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 200 | +                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 41: the HOOK too (the next hook)
 201 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 202 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 203 |                      if not med.get("measured") or not weak:
 204 |                          rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 205 |                          break
 206 |                      dropped |= weak
 207 | -                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 208 | +                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed))
 209 | +                    rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
 210 | +                                  if swapped is not None else
 211 | +                                  f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 212 | +                                  f"line-up rules: re-lined")
 213 |                      continue
 214 |                  if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
 215 |                      dropped.add(segs[1]["moment_id"])
 216 | @@ -1301,6 +1402,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 217 |                  while w_used < writes:
 218 |                      if over_budget(ai):
 219 |                          break
 220 | +                    w_over = package_over(line)
 221 | +                    if w_over:
 222 | +                        rec["why"] = w_over
 223 | +                        break
 224 |                      w_used += 1
 225 |                      try:
 226 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 227 | @@ -1448,11 +1553,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 228 |                      if nv is not None:
 229 |                          out["packages"].append(nv)
 230 |                          rec["result"] = "PACKAGE (no voice, ruling 3)"
 231 | +                if not out["packages"] and not rec.get("why") and not rec.get("result"):
 232 | +                    last = (rec.get("attempts") or [{}])[-1]
 233 | +                    rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
 234 | +                    rec["why"] = f"{w_used} write(s) failed their gates" + (f" ({', '.join(rules)})" if rules else "")
 235 |                  if out["packages"] or not relined:
 236 |                      break
 237 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
 238 |                  break
 239 |      out["package"] = out["packages"][0] if out["packages"] else None
 240 | +    s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
 241 | +    out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
 242 | +                     "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
 243 | +    log(f"  search: {total} line-up(s) of {lineups}, ${s_rep:.2f} reported / ${s_est:.2f} estimate (ruling 41: $3.00 "
 244 | +        f"reported per build)")
 245 |      if out["package"] is None and not out.get("why_none"):       # every angle ended without a package: say why
 246 |          out["why_none"] = ("no angle gave a package: " + "; ".join(
 247 |              f"angle {t.get('angle')}: {str(t.get('why') or t.get('result') or 'no reason recorded')[:250]}"
 248 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 249 | index 0ee53c23..82005799 100644
 250 | --- a/tests/package/test_medley.py
 251 | +++ b/tests/package/test_medley.py
 252 | @@ -608,23 +608,31 @@ class TestBuildLoop(unittest.TestCase):
 253 |          self.assertEqual(out["angle_backend"], "fake:angle_write")
 254 |          self.assertEqual(out["angle_tried"], [])
 255 |  
 256 | -    def test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling(self):
 257 | -        """Ruling 5 (22:40): per package 15 min wall / $1.50 by the vendors' reported cost; the estimate only as a $5
 258 | -        ceiling. Checked before every line-up and every write (audit 2240 C1, glm), not only when an angle ends."""
 259 | -        for spent, why in (((0.10, 1.51), "reported"), ((5.01, 0.20), "estimate ceiling")):
 260 | +    def test_the_search_budget_ends_the_build_and_the_package_budget_ends_only_its_line_up(self):
 261 | +        """Ruling 41 (04:58): a build may spend $3.00 reported searching (a $10.00 estimate ceiling); ruling 5's $1.50 /
 262 | +        15 min is per PACKAGE delivered, counted from its own line-up's clips-alone verdict."""
 263 | +        for spent, why in (((0.10, 3.01), "reported"), ((10.01, 0.20), "estimate ceiling")):
 264 |              reads = [(0.0, 0.0), (0.0, 0.0)]                  # the baseline, then the check before line-up 1
 265 | -            calls = iter(reads + [spent] * 50)                # ... then over budget from the next check on
 266 | +            calls = iter(reads + [spent] * 80)                # ... then over the search budget from the next check on
 267 |              rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(False, [], None, "none")] * 2, [],
 268 |                        spend=lambda: next(calls))
 269 |              out = rig.run()
 270 | -            self.assertIn("ruling 5", out["why_none"], why)
 271 | +            self.assertIn("ruling 41", out["why_none"], why)
 272 |              self.assertEqual(len(rig.medley_calls), 1, why)          # line-up 1 ran; nothing after the stop
 273 |              self.assertEqual(out["budget_stop"]["angles_tried"], 1, why)
 274 | -        over = iter([(0.0, 0.0)] + [(9.0, 9.0)] * 50)               # over budget from the very first check
 275 | +            self.assertEqual(out["search"]["lineups"], 1, why)
 276 | +        over = iter([(0.0, 0.0)] + [(11.0, 11.0)] * 80)             # over the search budget from the very first check
 277 |          rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], spend=lambda: next(over))
 278 |          out = rig.run()
 279 |          self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
 280 |          self.assertIsNone(out["package"])
 281 | +        rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(True, [], None, Rig.LINE)] * 2, [None, None])
 282 | +        rig.spend = lambda: (0.0, 1.6) if rig.medley_calls else (0.0, 0.0)  # line-up 1's package: $1.60 > $1.50
 283 | +        out = rig.run()
 284 | +        self.assertIn("per package delivered", out["tried"][0]["why"])      # only that line-up stopped
 285 | +        self.assertEqual(len(rig.write_calls), 1)                          # line-up 2 (its own $0.00) wrote
 286 | +        self.assertIsNotNone(out["package"])                               # the search went on: $1.60 < $3.00
 287 | +        self.assertEqual((out["search"]["lineups"], out["search"]["usd_reported"]), (2, 1.6))
 288 |  
 289 |      def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
 290 |          """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
 291 | @@ -726,6 +734,68 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 292 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 293 |  
 294 |  
 295 | +class TestRuling41Search(unittest.TestCase):
 296 | +    """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 297 | +    place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 298 | +    ones rated 4-5 kept; up to 8 line-ups per build; the bar unchanged."""
 299 | +
 300 | +    def pool(self, *spec):
 301 | +        out = {}
 302 | +        for mid, ch, dur, rank, h2s in spec:
 303 | +            m = dict(pm(mid, ch, dur, rank=rank), hook_onset={"pass": True})
 304 | +            m["scores"] = dict(m["scores"], hook_first_2s=h2s)
 305 | +            out[mid] = m
 306 | +        return out
 307 | +
 308 | +    def test_a_clip_below_the_bar_is_swapped_at_its_place_for_the_next_clip_by_rank(self):
 309 | +        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 310 | +                      ("z", "D", 13.0, 5.0, 3), ("w", "E", 13.0, 8.0, 3), ("v", "B", 13.0, 9.5, 3))
 311 | +        segs = [p["h"], p["x"], p["y"]]
 312 | +        new, swaps = PK.swap_lineup(segs, {"x"}, p)
 313 | +        self.assertEqual([m["moment_id"] for m in new], ["h", "v", "y"])     # v: the best rank, x's place, B again
 314 | +        self.assertEqual(swaps, {"x": "v"})
 315 | +        new, swaps = PK.swap_lineup(segs, {"x"}, p, avoid={"v"})
 316 | +        self.assertEqual([m["moment_id"] for m in new], ["h", "w", "y"])     # then the next by rank
 317 | +        self.assertTrue(PK.lineup_ok(new)[0])
 318 | +
 319 | +    def test_a_hook_below_the_bar_is_swapped_for_the_next_hook_by_score(self):
 320 | +        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 321 | +                      ("g", "D", 12.0, 1.0, 5), ("k", "E", 12.0, 9.9, 2))
 322 | +        new, swaps = PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)
 323 | +        self.assertEqual(swaps, {"h": "g"})                                  # by hook_first_2s, not by rank
 324 | +        p["g"]["hook_onset"] = {"pass": False}                               # a hook must still open (G17a)
 325 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)[1], {"h": "k"})
 326 | +
 327 | +    def test_no_swap_when_nothing_fits_the_line_up_rules(self):
 328 | +        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 329 | +                      ("s", "D", 3.0, 9.0, 3))                               # 12 + 3 + 13 = 28 s < the medley's seconds
 330 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"x"}, p), (None, None))
 331 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], set(), p), (None, None))
 332 | +
 333 | +    def test_lineup_for_s_own_line_ups_pass_lineup_ok(self):
 334 | +        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 335 | +                      ("z", "D", 13.0, 9.0, 3), ("w", "E", 6.0, 9.0, 3))
 336 | +        for order in (["h", "x", "y", "z"], ["h", "w", "x", "y"], ["x", "h", "z", "w"]):
 337 | +            segs = PK.lineup_for(angle(order, order[0]), p, need_onset=True, need_stand_alone=True)
 338 | +            if segs is not None:
 339 | +                self.assertEqual(PK.lineup_ok(segs), (True, "ok"), order)
 340 | +
 341 | +    def test_the_build_swaps_a_low_rated_hook_and_stops_at_8_line_ups(self):
 342 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
 343 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
 344 | +        out = rig.run()
 345 | +        self.assertEqual(rig.medley_calls[0][0], "h")
 346 | +        self.assertNotEqual(rig.medley_calls[1][0], "h")                    # the hook rated 3 was swapped
 347 | +        self.assertIn("swapped", out["tried"][0]["why"])
 348 | +        self.assertIsNotNone(out["package"])
 349 | +        many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
 350 | +        fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
 351 | +        rig = Rig(many, [list("abcdefgh"), list("ijklmnop"), list("aceg")], fails, [])
 352 | +        out = rig.run()
 353 | +        self.assertEqual(len(rig.medley_calls), PK.LINEUPS_PER_BUILD)       # 8, over every angle
 354 | +        self.assertEqual(out["search"]["lineups"], 8)
 355 | +
 356 | +
 357 |  class TestRuling37QuestionHook(unittest.TestCase):
 358 |      """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
 359 |      which must be followable with no bridge (no bridge may follow a question; the render's R1 reads the sealed
 360 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway).

How package.build() works:
- An angle step proposes up to 3 angles, each a set of moments in play order.
- Per angle, lineup_for() picks a line-up: the hook + clips inside the medley's seconds, one per channel, a short clip
  only last, the render's STAND_ALONE.
- A blind clips-alone verdict (medley()) rates each segment 1-5 and judges each join. It passes only with a
  through-line and every rating >= COHERENCE_MIN (4).
- Then the writes and the gates. The first package that passes every hard gate wins.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR ORDER 04:58 ET Nov 13, RULING 41 (LINE-UP SEARCH): "With 11 cuttable moments and 8 possible hooks,
two line-ups is not a search. When the clips-alone verdict fails, read WHICH clip rated below the bar and swap that
clip (a hook rated 3 -> the next hook by score; a clip rated 2 -> the next clip), keep the ones rated 4-5, and
re-judge. Up to 8 line-ups per build, inside the package budget ($1.50 / 15 min is per PACKAGE delivered; a build may
spend up to $3 searching, report it). Stop at the first that passes. The bar itself is unchanged."
- Before: 2 line-ups per angle. A low-rated HOOK was never swapped: the old code excluded the hook from the weak set,
  and its angle ended. A low-rated clip was re-lined only from the angle's own moments (often 4).
- Ruling 5's budget (15 min wall / $1.50 reported / $5 estimate) was counted from the build's start, so step A, L-v 2
  and slow angle calls used it up before any line-up.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. Every line-up the search judges must pass the
  same line-up rules, and the clips-alone bar (COHERENCE_MIN) and every gate are unchanged.

The change (pipeline/package.py):
1. Constants:
   - LINEUPS_PER_BUILD = 8;
   - SEARCH_USD_REPORTED = 3.00, and SEARCH_USD_ESTIMATE = 10.00 (ruling 5's $5.00 : $1.50 ratio, for calls whose
     vendor reports no cost);
   - SEARCH_WALL_S = 2400 (the build ends cleanly before its driver's timeout; a killed build writes no record);
   - SWAP_TOP = 6.
2. lineup_ok(segs, crange, repeat_ok): lineup_for's rules checked on a GIVEN line-up:
   - the hook is hook-eligible and its G17a onset passed;
   - the clips are clip-eligible, and there are 2-4 of them;
   - one segment per channel, or repeat_ok with one channel giving two videos;
   - price predictions are capped;
   - a short clip plays only last;
   - the seconds are inside crange;
   - stand_alone_check passes.
3. swap_lineup(segs, weak, pool, avoid):
   - Each weak segment (rated below the bar) is swapped at its place for the next candidate by score from the WHOLE
     cleared pool: the hook for the next hook by scores.hook_first_2s, a clip by rank_score.
   - The others stay in place.
   - The first combination (up to SWAP_TOP per place) that passes lineup_ok wins, one per channel first, then the supply
     exception. -> (segs, {old: new}) or (None, None).
4. supply_exception(segs, ctx): the L-y 4 text, factored out verbatim, and now also used for swapped line-ups.
5. build():
   - lineups (default LINEUPS_PER_BUILD) counts line-ups judged over the WHOLE build.
   - On a clips-alone failure, the weak set includes the HOOK. No weak segment or an unmeasured verdict ends the
     angle, as before.
   - The weak moments join `dropped`, and swap_lineup proposes the next line-up (judged next). If no swap fits,
     lineup_for re-lines from the angle as before.
   - over_budget(ai) is now the SEARCH budget: $3.00 reported, $10.00 estimate and SEARCH_WALL_S from the build's
     start. It ends the build.
   - package_over(line): ruling 5's 15 min / $1.50 / $5, counted from each line-up's clips-alone verdict. It ends only
     that line-up; the search goes on.
   - A line-up whose writes all fail now records why. out["search"] reports the line-ups, the reported and estimated
     spend, and the seconds, with a log line.
6. Tests (tests/package/test_medley.py):
   - the budget test is rewritten to ruling 41's semantics;
   - swap_lineup (a clip at its place by rank, a hook by hook score, a hook must still open, none when nothing fits);
   - lineup_for's own line-ups pass lineup_ok;
   - the build swaps a low-rated hook, and stops at 8 line-ups over every angle.

Check in particular:
- that every line-up the search judges passes exactly the rules lineup_for applies (lineup_ok vs lineup_for), and the
  bar is unchanged;
- that the weak set, the swap and `dropped` cannot loop or re-judge a dropped moment;
- that the per-package budget cannot be dodged: a package is still bound by 15 min / $1.50 from its own line-up's
  start, and the search by $3.00;
- the counting of line-ups;
- that nothing else changes: the writes, the gates, the no-voice path and the per-clip drops.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

