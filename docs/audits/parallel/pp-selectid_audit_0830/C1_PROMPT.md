# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0830
# Branch: pp-selectid
# Generated: 2026-11-13 08:28 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0830/C1_STEP.diff (138 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 370c558..e7afa32 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -494,8 +494,8 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print):
   6 |  
   7 |  ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
   8 |  play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
   9 | -clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
  10 | -conversation and never answer each other.
  11 | +clips (verbatim quotes, each with its channel, its length and its PLACEMENT LIMITS) that passed our checks. The
  12 | +channels were not in one conversation and never answer each other.
  13 |  
  14 |  {note}
  15 |  {clips}
  16 | @@ -507,7 +507,9 @@ it is today's.
  17 |  With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
  18 |  clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
  19 |  introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
  20 | -channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
  21 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "may only play LAST" is the
  22 | +LAST id of an angle's list or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as
  23 | +the clips allow (aim for {k}); for
  24 |  each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
  25 |  survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
  26 |  "hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
  27 | @@ -910,6 +912,36 @@ def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  28 |      return None, None
  29 |  
  30 |  
  31 | +def placement(m):
  32 | +    """RULING 54: a clip's placement limits as the angle proposer is told them, by the line-up's own rules: under
  33 | +    SHORT_CLIP_S it may only play LAST; without hook eligibility and a passed hook onset (G17a) it cannot open."""
  34 | +    lim = []
  35 | +    if m["duration_s"] < SHORT_CLIP_S:
  36 | +        lim.append(f"may only play LAST (under {SHORT_CLIP_S:.0f} s)")
  37 | +    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
  38 | +        lim.append("cannot open (never the hook)")
  39 | +    return "".join(f" | {x}" for x in lim)
  40 | +
  41 | +
  42 | +def pool_fill(angle, pool, dropped=frozenset()):
  43 | +    """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
  44 | +    exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
  45 | +    are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
  46 | +    rule. Its preference (the proposer's earliest moments first) keeps as many of the angle's own as fit, and the added
  47 | +    clips play after them. -> (segs, [the added moment ids]) or (None, None)."""
  48 | +    own = [mid for mid in angle["moments"] if mid in pool]
  49 | +    rest = [m["moment_id"] for m in sorted(pool.values(), key=lambda m: (-m["rank_score"], m["moment_id"]))
  50 | +            if m["moment_id"] not in own]
  51 | +    if not rest:
  52 | +        return None, None
  53 | +    ext = dict(angle, moments=own + rest)
  54 | +    for repeat_ok in (False, True):
  55 | +        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True)
  56 | +        if segs is not None:
  57 | +            return segs, [m["moment_id"] for m in segs if m["moment_id"] not in own]
  58 | +    return None, None
  59 | +
  60 | +
  61 |  def supply_exception(segs, ctx):
  62 |      """L-y 4: the reason a line-up takes two clips from one channel (two videos), else None."""
  63 |      rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs) if sum(m["channel_id"] == c for m in segs) > 1]
  64 | @@ -1451,7 +1483,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  65 |          out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
  66 |                             f"vendors, from fewer than 3 channels")
  67 |          return out
  68 | -    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
  69 | +    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s{placement(m)} | '
  70 | +                      f'"{quote_data(m["text"], 600)}"'
  71 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
  72 |      lo, hi = medley_content_range()
  73 |      angles, angle_reply = None, None
  74 | @@ -1626,8 +1659,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  75 |                                            need_stand_alone=True)
  76 |                          if segs is not None:
  77 |                              exception = supply_exception(segs, ctx)
  78 | +                    filled = None
  79 | +                    if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
  80 | +                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
  81 | +                        # pool completes it. A re-line after a drop moves on to the next angle, as before
  82 | +                        exception = supply_exception(segs, ctx) if segs is not None else None
  83 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
  84 | -                       "supply_exception": exception, "attempts": []}
  85 | +                       "supply_exception": exception, "attempts": [],
  86 | +                       **({"pool_filled": filled} if filled else {})}
  87 |                  out["tried"].append(rec)
  88 |                  if segs is None:
  89 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
  90 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  91 | index 9b7053f..20251a2 100644
  92 | --- a/tests/package/test_medley.py
  93 | +++ b/tests/package/test_medley.py
  94 | @@ -1129,6 +1129,43 @@ class TestRuling53Reposted(unittest.TestCase):
  95 |          self.assertEqual(out["usable"], 5)                                 # usable keeps its meaning
  96 |  
  97 |  
  98 | +class TestProposal1PoolFill(unittest.TestCase):
  99 | +    """PROPOSAL 1 (pending the orchestrator): the 07:14 build's angles held 4 clips that formed no line-up (36.52 s
 100 | +    < 36.7 s; a short clip mid-order), while 3 cleared clips were never offered. The pool completes such an angle."""
 101 | +
 102 | +    def test_an_angle_that_forms_no_line_up_is_completed_from_the_pool(self):
 103 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 104 | +        for m in ms:
 105 | +            m["hook_onset"] = {"pass": m["moment_id"] not in ("s", "y")}   # as at 07:14: those two cannot open
 106 | +        by = {m["moment_id"]: m for m in ms}
 107 | +        a = angle(["h", "x", "s", "y"], "h")                          # the 07:14 shape: short "s" mid-order
 108 | +        self.assertIsNone(PK.lineup_for(a, by, need_onset=True))      # 8.8 + 13.9 + 13.8 = 36.5 s < 36.7 s
 109 | +        segs, added = PK.pool_fill(a, by)
 110 | +        self.assertEqual([m["moment_id"] for m in segs][:3], ["h", "x", "y"])     # the angle's own first
 111 | +        self.assertEqual(added, ["z"])                                            # the pool's clip after them
 112 | +        self.assertTrue(PK.lineup_ok(segs)[0])
 113 | +        self.assertEqual(PK.pool_fill(a, {k: by[k] for k in ("h", "x", "s", "y")}), (None, None))   # nothing to add
 114 | +
 115 | +    def test_ruling_54_the_proposer_is_told_each_clips_placement_limits(self):
 116 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 117 | +        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
 118 | +        rig.run()
 119 | +        p = next(p for r, p in rig.prompts if r == "angle_write")
 120 | +        self.assertIn('id=s | C | 6.9 s | may only play LAST (under 8 s) | cannot open (never the hook) | "', p)
 121 | +        self.assertIn('id=y | D | 13.8 s | cannot open (never the hook) | "', p)
 122 | +        self.assertIn('id=z | E | 9.5 s | "', p)                       # no limit, nothing added
 123 | +        self.assertIn('a clip marked "may only play LAST" is the\nLAST id of an angle', p)
 124 | +        self.assertIn('a clip marked "cannot open" is never the hook', p)
 125 | +
 126 | +    def test_the_build_records_the_pool_fill_and_judges_the_line_up(self):
 127 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 128 | +        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
 129 | +        out = rig.run()
 130 | +        self.assertEqual(out["tried"][0]["pool_filled"], ["z"])
 131 | +        self.assertEqual(rig.medley_calls[0][:3], ["h", "x", "y"])
 132 | +        self.assertIsNotNone(out["package"])
 133 | +
 134 | +
 135 |  class TestRuling41Search(unittest.TestCase):
 136 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 137 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 138 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY: a hook + 2-4
clips from different channels, 36.7-51.5 s of clips). Your role: a strict reviewer of how line-ups are formed.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- An angle writer proposes ANGLES: a sentence plus 4-8 cleared clip ids in PLAY ORDER, the hook first.
- lineup_for(angle, cleared, dropped, ...) picks the hook + 2-4 clips from the angle's own moments, in the proposer's
  play order, one per channel (or L-y 4's supply exception), under every line-up rule:
  - the hook can open (hook eligibility + the G17a onset measure);
  - a clip under SHORT_CLIP_S (8 s) only LAST;
  - the seconds range;
  - at most one price prediction;
  - at most one trimmed clip (ruling 49);
  - the render's STAND_ALONE.
  It prefers the proposer's earliest moments (the lowest sum of play positions). The line-up is then judged on the
  clips alone; ruling 41's swap replaces below-bar segments from the whole cleared pool.
- The 07:14 build: every angle's own 4 moments formed NO line-up (36.52 s, 0.18 s short of 36.7 s, and a 6.93 s clip
  placed mid-order), so nothing was judged. Three cleared clips were never offered.

The order this diff implements (ORCHESTRATOR RULING 54, 08:06 ET Nov 13, verbatim): "PROPOSAL 1: YES, as you scoped and
measured it: when an angle's own moments cannot form a line-up, complete it from the whole cleared pool by score, the
angle's play order kept, every line-up rule unchanged, first line-up only. One addition: the proposer is told each
clip's seconds and placement limits (a clip that may only play last is never offered mid-order), so fewer angles arrive
unformable."

The change (pipeline/package.py, tests/package/test_medley.py):
1. pool_fill(angle, pool, dropped):
   - appends the pool's other moments, best by rank_score, AFTER the angle's own;
   - runs lineup_for again (one per channel first, then L-y 4's exception) with every rule unchanged;
   - lineup_for's preference for the proposer's earliest moments keeps as many of the angle's own as fit, and puts the
     added clips after them in play order;
   - returns (segs, [the added ids]) or (None, None).
2. build(): only when an angle has formed NOT EVEN ITS FIRST line-up (n_lineup == 0, after both lineup_for tries), the
   pool completes it, and the record carries "pool_filled". A re-line after a drop moves on to the next angle, as
   before.
3. placement(m) and the angle prompt:
   - every clip line now states its limits: "may only play LAST (under 8 s)" for a clip under SHORT_CLIP_S, and
     "cannot open (never the hook)" for a clip without hook eligibility and a passed hook onset;
   - the prompt says such a clip is the LAST id of an angle's list or is not in it, and is never the hook.
4. tests:
   - the 07:14 shape (the hook + 13.9 s + a short clip mid-order + 13.8 s; the two long ones cannot open) forms no
     line-up of its own, and the pool adds a 9.5 s clip after the angle's own;
   - nothing to add gives None;
   - the build records pool_filled and judges the line-up;
   - the prompt carries the limits, and nothing for an unlimited clip.
- Measured on the 07:14 pool before this diff: all 3 angles would have formed a line-up. Each opened on a pool clip,
  because the angle's own hook fails the hook's topic rule; the next opener by its first 2 s came from the pool, as
  ruling 41's hook swap would choose it.
- test_medley 89 OK; every other suite OK.

Check in particular:
- that every line-up rule still applies to a pool-filled line-up (lineup_for runs unchanged on the extended list);
- that the angle's own moments keep their play order and come before the added clips;
- that the fill runs only for an angle's first line-up and never re-admits a dropped or doomed moment;
- that the limits shown to the proposer match the rules lineup_for applies exactly;
- anything that could blow up the combinations (the pool's size) or loop.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

