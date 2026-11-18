# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_1044
# Branch: pp-selectid
# Generated: 2026-11-18 10:44 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_1044/C1_STEP.diff (138 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c32b7d6..3b025fc 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -296,6 +296,10 @@ LY_FLOOR_S = 30.0                  # RULINGS 148 (1) / 149 (orchestrator 09:56 E
   6 |  LY_SHORT_SPAN_WORDS = 4            # clips too short to land 60 s: the takeaway is asked within this of its longest
   7 |  RUNTIME_SHORT = "This video runs {n} seconds, shorter than usual."   # 148 (1): the flag, NN the factory's estimate
   8 |  _FLOOR = None                      # LY_FLOOR_S while build() runs the never-empty pass (set and cleared there only)
   9 | +VALUE_SOFT_LINE = None             # RULING 150 (1) (orchestrator 10:40 ET Nov 18) BY HAND, the one exception pin: the
  10 | +                                   # exact closing line (the driver's --value-soft-line) whose MEASURED value verdict
  11 | +                                   # (ruling 91) the never-empty pass takes as a flag; every other line as ruled
  12 | +VALUE_FLAG = 'The closing line may mostly restate the clips: "{line}"'   # RULING 150: the flag, the line verbatim
  13 |  
  14 |  
  15 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  16 | @@ -4383,7 +4387,15 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  17 |                      log(f"    value (ruling 91) {'PASS' if val['ok'] else 'LOST'}: " +
  18 |                          (f"{answers}, {val.get('words')} words" if val.get("measured") else
  19 |                           f"no verdict ({str(val.get('why'))[:120]})") + f" ({time.time() - t0:.0f} s)")
  20 | -                    if not val["ok"]:                      # "anything short of a clear yes means no line"
  21 | +                    if (soft and not val["ok"] and val.get("measured") is True and VALUE_SOFT_LINE is not None
  22 | +                            and fields["takeaway"]["text"] == VALUE_SOFT_LINE):          # RULING 150 (1) BY HAND
  23 | +                        val = att["value"] = dict(val, soft=True)
  24 | +                        rec["value_by_hand"] = {"ruling": "150 (1), applied by hand to the exception pin",
  25 | +                                                "line": VALUE_SOFT_LINE, "answers": {k: val.get(k) for k in (
  26 | +                                                    "adds", "no_restate", "missed", "short")}}
  27 | +                        log("    RULING 150 (1) BY HAND: this closing line's value verdict is a flag; fidelity, length "
  28 | +                            "and the banned words stay HARD")
  29 | +                    if not val["ok"] and not val.get("soft"):      # "anything short of a clear yes means no line"
  30 |                          v_lost.append({k: val.get(k) for k in ("text", "measured", "adds", "no_restate", "missed",
  31 |                                                                 "short", "why", "words", "backend")})
  32 |                          rec["value_lost"] = list(v_lost)
  33 | @@ -4735,6 +4747,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  34 |                                                                                                "missed", "short")},
  35 |                                     why=value.get("why"), words=value.get("words"), cap=value.get("cap"),
  36 |                                     rule=f"ruling 91 (medley half): all four a clear yes and at most {LY_TAKEAWAY_MAX_WORDS} "
  37 | -                                        f"words, off every writer's vendor and family")}
  38 | +                                        f"words, off every writer's vendor and family",
  39 | +                                   **({"status": "FLAGGED", "flags": [VALUE_FLAG.format(line=value.get("text"))]}
  40 | +                                      if value.get("soft") and value.get("ok") is not True else {}))}   # RULING 150
  41 |             if value is not None else {}),
  42 |      }
  43 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  44 | index 6400783..9cdc53c 100644
  45 | --- a/pipeline/package_pin.py
  46 | +++ b/pipeline/package_pin.py
  47 | @@ -47,6 +47,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
  48 |                          "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
  49 |                          #   HARD)
  50 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
  51 | +                        "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
  52 | +                        #   91), a measured one; fidelity, length and the banned words stay HARD
  53 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
  54 |  #   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
  55 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  56 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  57 | index 551e068..0cd6787 100644
  58 | --- a/tests/package/proof_ledger.py
  59 | +++ b/tests/package/proof_ledger.py
  60 | @@ -444,6 +444,10 @@ def main(argv=None):
  61 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  62 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  63 |                      f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  64 | +    ap.add_argument("--value-soft-line", metavar="LINE", default=None,
  65 | +                    help="RULING 150 (1) BY HAND (orchestrator 10:40 ET Nov 18), the one exception pin only (needs "
  66 | +                         "--pbx-exception): this exact closing line's measured value verdict is a flag in the "
  67 | +                         "never-empty pass, logged in the record")
  68 |      ap.add_argument("--pbx-exception", metavar="TEXT", default=None,
  69 |                      help="RULING 144 (PBX 07:05 ET Nov 18): this ONE build's 12 h window is waived, named and logged "
  70 |                           "(TEXT starts 'PBX exception'): --hours may reach PBX_EXCEPTION_MAX_H, every 12 h check of "
  71 | @@ -462,6 +466,10 @@ def main(argv=None):
  72 |          print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  73 |          return 2
  74 |      base_h = package_pin.WINDOW_H                        # 12: the rule (rulings 76 + 77) the exception widens
  75 | +    if a.value_soft_line is not None:                    # RULING 150 (1) BY HAND: the one exception pin only
  76 | +        if not a.pbx_exception or not a.value_soft_line.strip():
  77 | +            raise SystemExit("--value-soft-line needs --pbx-exception and the exact closing line")
  78 | +        PK.VALUE_SOFT_LINE = a.value_soft_line
  79 |      if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  80 |          package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  81 |      try:                                                 # read before anything is written (glm C2 N-4)
  82 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  83 | index e7d50a8..1ad887d 100644
  84 | --- a/tests/package/test_ruling_137.py
  85 | +++ b/tests/package/test_ruling_137.py
  86 | @@ -648,6 +648,51 @@ class TestRuling144TheOneException(unittest.TestCase):
  87 |              PP.WINDOW_H = saved
  88 |  
  89 |  
  90 | +class TestRuling150ValueByHand(unittest.TestCase):
  91 | +    """RULING 150 (1) (orchestrator 10:40 ET Nov 18), applied BY HAND to the one exception pin: the exact closing line
  92 | +    the driver names (--value-soft-line) keeps its place in the never-empty pass when its MEASURED value verdict (ruling
  93 | +    91) is LOST, flagged 'The closing line may mostly restate the clips: "<line>"'. Any other line, an unmeasured
  94 | +    verdict, and the clean pass: unchanged."""
  95 | +    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
  96 | +              "covers_speaker": False}
  97 | +
  98 | +    def run_rig(self, line, measured=True):
  99 | +        import test_medley as TM
 100 | +        from test_moments import pm
 101 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 102 | +        lost = {"adds": "yes", "no_restate": "no", "why": "it restates the clips"} if measured else {"measured": False}
 103 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 104 | +                   visuals={"x": {"burned_in": [dict(self.TICKER)]}}, values=[dict(lost) for _ in range(6)],
 105 | +                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
 106 | +        r.build_kw = {"never_empty": True}
 107 | +        with mock.patch.object(PK, "VALUE_SOFT_LINE", line):
 108 | +            return r.run()["package"]
 109 | +
 110 | +    def test_the_named_line_seals_flagged(self):
 111 | +        import test_medley as TM
 112 | +        pk = self.run_rig(TM.Rig.LINE)
 113 | +        self.assertIsNotNone(pk)
 114 | +        row = pk["gates"]["takeaway_value"]
 115 | +        self.assertEqual((row["status"], row["flags"], row["text"]), (
 116 | +            "FLAGGED", [f'The closing line may mostly restate the clips: "{TM.Rig.LINE}"'], TM.Rig.LINE))
 117 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 118 | +
 119 | +    def test_the_clean_pass_never_takes_it(self):
 120 | +        import test_medley as TM
 121 | +        from test_moments import pm
 122 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]           # nothing soft: the clean pass
 123 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 124 | +                   values=[{"adds": "yes", "no_restate": "no", "why": "it restates the clips"} for _ in range(6)])
 125 | +        with mock.patch.object(PK, "VALUE_SOFT_LINE", TM.Rig.LINE):
 126 | +            self.assertIsNone(r.run()["package"])                                   # reaches the value gate: HARD
 127 | +
 128 | +    def test_any_other_line_or_no_verdict_stays_hard(self):
 129 | +        import test_medley as TM
 130 | +        self.assertIsNone(self.run_rig("A different closing line."))
 131 | +        self.assertIsNone(self.run_rig(None))
 132 | +        self.assertIsNone(self.run_rig(TM.Rig.LINE, measured=False))
 133 | +
 134 | +
 135 |  class TestRuling148RuntimeFloor(unittest.TestCase):
 136 |      """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
 137 |      medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
 138 | 
```

---

pp-selectid: RULING 150 (1) (orchestrator 10:40 ET Nov 18), APPLIED BY HAND to the one exception pin ("as a manual
application of this ruling logged in the build record if the code is not yet built; build the code audit-first right
after"). The ruling: the takeaway's value verdict (ruling 91) is SOFT, flagged 'The closing line may mostly restate the
clips: "<the line>"'; fidelity (COMMENTARY, NEEDS_SOURCE), length and the banned words stay HARD. For THIS pin: seal
build 150's line-up with write 1 as the takeaway if it passes fidelity (its only refusal was VALUE).
THE CHANGE (narrow; the general rule follows in its own audited change):
- package.VALUE_SOFT_LINE (None by default) = the exact closing line the driver names (--value-soft-line LINE, which
  requires --pbx-exception and a non-empty line). In _build's write loop, ONLY in the never-empty pass (soft), ONLY
  for a MEASURED value verdict that is not ok, ONLY when the line written is exactly VALUE_SOFT_LINE: val becomes
  dict(val, soft=True), the line-up's record gets value_by_hand {ruling, line, answers}, a log line; the loop then goes
  on to the paid gates (fidelity + context, HARD as before) instead of the rewrite. Every other case: unchanged.
- inventory: the takeaway_value row (its text is the judged line, as the pin and the render compare) gets status
  FLAGGED and flags [VALUE_FLAG with the line verbatim] when value.soft and value.ok is not True.
- package_pin.SOFT_GATES += "takeaway_value" (the integrator's check_pin_only reads it live; its render reads the
  sealed row: FLAGGED with plain flags, replayed false, text equal to the shipped line).
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py, tests/package/test_ruling_137.py.
TESTS (TestRuling150ValueByHand, the real build() on the stubbed rig): the named line seals with the FLAGGED row, the
exact sentence and text, gate_problems none; another line, no line, an unmeasured verdict: no package; the clean pass
reaching the value gate with the line named: no package. Mutations 6 of 6 killed (never by hand; any line; unmeasured
too; the row never flagged; not a soft gate; the clean pass too); control passes.
PLEASE CHECK: (1) can any line other than the named one, or the clean pass, or an unmeasured verdict, get through?
(2) does fidelity / context / length / banned words stay HARD for the named line? (3) the row the render reads.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
