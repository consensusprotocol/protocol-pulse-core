# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1006
# Branch: pp-selectid
# Generated: 2026-11-13 09:58 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1006/C1_STEP.diff (134 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c1d391f..b1a38d0 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -62,6 +62,7 @@ RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the packaging target the fact
   6 |  VO_S = (6.0, 22.0)                 # the PBX MAX v3 VO's seconds (intro + bridges), content_range()'s slack
   7 |  R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
   8 |  TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
   9 | +FRESH_H = 24.0                     # ruling 57 (09:59 Nov 13): a line-up with a clip this fresh is preferred
  10 |  PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
  11 |  PRESCREEN_BATCH = 8                # excerpts per step-A call
  12 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
  13 | @@ -925,7 +926,7 @@ def placement(m):
  14 |      return "" if opens else " | cannot open (never the hook)"
  15 |  
  16 |  
  17 | -def pool_fill(angle, pool, dropped=frozenset()):
  18 | +def pool_fill(angle, pool, dropped=frozenset(), now=None):
  19 |      """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
  20 |      exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
  21 |      are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
  22 | @@ -944,7 +945,8 @@ def pool_fill(angle, pool, dropped=frozenset()):
  23 |      mine = set(own)
  24 |      half = lambda segs: 2 * sum(m["moment_id"] in mine for m in segs) >= len(segs)   # the angle's own: >= half
  25 |      for repeat_ok in (False, True):
  26 | -        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half)
  27 | +        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half,
  28 | +                          now=now)
  29 |          if segs is not None:
  30 |              return segs, [m["moment_id"] for m in segs if m["moment_id"] not in mine]
  31 |      return None, None
  32 | @@ -960,8 +962,18 @@ def supply_exception(segs, ctx):
  33 |              f" gives two clips, from two videos (L-y 4)")
  34 |  
  35 |  
  36 | +def fresh_key(segs, now):
  37 | +    """RULING 57: how a line-up ranks by its clips' age on the render clock `now`: (holds a clip <= FRESH_H old, minus
  38 | +    the mean age in hours). A clip with no readable publish time is never fresh and counts as the oldest."""
  39 | +    ages = [E.age_hours(m.get("published_at"), now) for m in segs]
  40 | +    known = [a for a in ages if a is not None]
  41 | +    oldest = max(known, default=0.0) + 1.0
  42 | +    return (any(a is not None and a <= FRESH_H for a in ages),
  43 | +            -sum(a if a is not None else oldest for a in ages) / max(1, len(ages)))
  44 | +
  45 | +
  46 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  47 | -               need_stand_alone=False, accept=None):
  48 | +               need_stand_alone=False, accept=None, now=None):
  49 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  50 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  51 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  52 | @@ -1004,6 +1016,9 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  53 |                  if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  54 |                      continue
  55 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  56 | +                if now is not None:                       # ruling 57: a fresh clip first, then the newest clips,
  57 | +                    f = fresh_key([h] + order, now)       # then the proposer's earliest (its play order is kept)
  58 | +                    key = (f[0], f[1], key[0], key[1])
  59 |                  if best is None or key > best[0]:
  60 |                      best = (key, [h] + order)
  61 |          if best:
  62 | @@ -1513,6 +1528,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  63 |      if not angles:
  64 |          return out
  65 |      out.pop("why_none", None)
  66 | +    def first_fresh(a):                                   # ruling 57: the angles whose first line-up holds a clip
  67 | +        segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now)   # <= FRESH_H old go first
  68 | +        return bool(segs) and fresh_key(segs, ctx.now)[0]
  69 | +    angles = sorted(angles, key=lambda a: not first_fresh(a))      # stable: the writer's order within each group
  70 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
  71 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
  72 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
  73 | @@ -1663,15 +1682,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  74 |                      exception = supply_exception(segs, ctx)
  75 |                  else:
  76 |                      segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
  77 | -                                                 need_stand_alone=True), None
  78 | +                                                 need_stand_alone=True, now=ctx.now), None
  79 |                      if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
  80 |                          segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
  81 | -                                          need_stand_alone=True)
  82 | +                                          need_stand_alone=True, now=ctx.now)
  83 |                          if segs is not None:
  84 |                              exception = supply_exception(segs, ctx)
  85 |                      filled = None
  86 |                      if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
  87 | -                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
  88 | +                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now)   # FIRST: the
  89 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
  90 |                          exception = supply_exception(segs, ctx) if segs is not None else None
  91 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
  92 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  93 | index 814be17..4b5ea0f 100644
  94 | --- a/tests/package/test_medley.py
  95 | +++ b/tests/package/test_medley.py
  96 | @@ -1191,6 +1191,37 @@ class TestProposal1PoolFill(unittest.TestCase):
  97 |          self.assertIsNotNone(out["package"])
  98 |  
  99 |  
 100 | +class TestRuling57Fresh(unittest.TestCase):
 101 | +    """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
 102 | +    with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
 103 | +    TRIED first: inside an angle and across angles."""
 104 | +
 105 | +    def at(self, mid, ch, dur, hours_ago, **kw):
 106 | +        return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
 107 | +                    hook_onset={"pass": True})
 108 | +
 109 | +    def test_a_line_up_with_a_fresh_clip_is_tried_first(self):
 110 | +        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 111 | +              self.at("z", "D", 13.0, 5)]                                  # only z is under 24 h
 112 | +        by = {m["moment_id"]: m for m in ms}
 113 | +        a = angle(["h", "x", "y", "z"], "h")
 114 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_onset=True)], ["h", "x", "y"])
 115 | +        segs = PK.lineup_for(a, by, need_onset=True, now=NOW)              # without now: the proposer's earliest
 116 | +        self.assertIn("z", [m["moment_id"] for m in segs])                 # with now: a fresh clip first
 117 | +        self.assertTrue(PK.fresh_key(segs, NOW)[0])
 118 | +        old = dict(by, z=self.at("z", "D", 13.0, 40))                      # nothing fresh: the newest clips next
 119 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, old, need_onset=True, now=NOW)], ["h", "x", "z"])
 120 | +        self.assertFalse(PK.fresh_key([dict(ms[0], published_at=None)], NOW)[0])   # no readable time: never fresh
 121 | +
 122 | +    def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
 123 | +        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 124 | +              self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
 125 | +        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 126 | +        out = rig.run()
 127 | +        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
 128 | +        self.assertEqual(out["angles"][0]["hook"], "f")
 129 | +
 130 | +
 131 |  class TestRuling41Search(unittest.TestCase):
 132 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 133 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 134 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels). Your role: a strict reviewer of a selection preference.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- A build reads moments from videos inside a publish window, screens them, asks an angle writer for up to 3 angles
  (a sentence + clip ids in play order), and tries line-ups. lineup_for() picks one line-up per angle under every
  rule; its preference was (the proposer's earliest moments: the lowest sum of play positions, then the seconds
  nearest the middle of the range). The search stops at the FIRST package that passes every gate.
- Time-sensitive moments ('today', a price level) must come from a source <= 24 h old (L-v 3; usable() enforces it on
  the build clock, and the render re-checks on its own clock). The window itself is the build driver's --hours (72 by
  default), not in this diff.

The order this diff implements (ORCHESTRATOR RULING 57, 09:59 ET Nov 13, the part that is code): "When several line-ups
pass, prefer the one with the newest clips; a line-up with at least one clip from the last 24 h is preferred over one
with none."

The change (pipeline/package.py, tests/package/test_medley.py):
1. FRESH_H = 24.0. fresh_key(segs, now) = (holds a clip <= FRESH_H old on the clock `now`, minus the mean age in
   hours). A clip with no readable publish time is never fresh and counts as the oldest.
2. lineup_for(..., now=None):
   - with now, its key is (fresh, newest, the proposer's earliest, the seconds nearest the middle);
   - without now, the key is unchanged, so every other caller behaves as before;
   - every rule is unchanged, and the chosen clips still play in the proposer's order.
3. pool_fill(..., now=None) passes now through. build() passes ctx.now to lineup_for and pool_fill.
4. build(): before the line-ups, the angles are stably re-ordered so that an angle whose first line-up (lineup_for
   with now) holds a fresh clip is tried before one whose line-up does not. Within each group the writer's order
   stands. out["angles"] records the order tried.
5. tests:
   - with now, a line-up with a fresh clip is chosen over the proposer's earliest;
   - with nothing fresh, the newest clips are chosen;
   - without now, nothing changes;
   - no readable time is never fresh;
   - the build judges the writer's second angle first when only its line-up holds fresh clips.
- test_medley 92 OK; every other suite OK.

Stated readings (say so if you read the ruling differently):
- K1: a build stops at its first passing package, so "when several line-ups pass, prefer..." is applied to the ORDER
  of trying: the fresh-first line-up inside an angle, and fresh-first angles across the build. The alternative,
  continuing to search after a pass to compare passing packages, would spend the search budget twice.
- K2: "newest clips" is the mean age of the line-up's segments, the hook included.
- K3: recency now ranks above the proposer's earliest-moment preference (a heuristic, not a law); the proposer's PLAY
  ORDER is kept.

Check in particular: that no line-up rule changed; that time-sensitive moments are not affected; that the angle
re-order is stable and only by freshness; the cost of the extra lineup_for call per angle; the no-time cases.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

