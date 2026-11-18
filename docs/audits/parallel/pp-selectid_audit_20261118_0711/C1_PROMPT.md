# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_0711
# Branch: pp-selectid
# Generated: 2026-11-18 07:11 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_0711/C1_STEP.diff (171 lines)
```
   1 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
   2 | index e2403da..34d7bce 100644
   3 | --- a/pipeline/package_pin.py
   4 | +++ b/pipeline/package_pin.py
   5 | @@ -42,9 +42,13 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
   6 |                          "coherence", "ly_shape",           # RULING 141 (3), the line-up chain phase A: clip
   7 |                          #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
   8 |                          #   stay HARD; the takeaway's value rows are not soft)
   9 | -                        "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
  10 | +                        "stand_alone",                     # RULING 141 (2): a clip's STAND_ALONE opener (the topic
  11 | +                        "pbx_exception"})                  # RULING 144: EXCEPTION_GATE, only on the one excepted pin
  12 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  13 |  REVIEW_FLAGS_MAX = 3
  14 | +EXCEPTION_GATE = "pbx_exception"   # RULING 144 (PBX 07:05 ET Nov 18): a named, logged exception to a HARD rule for ONE
  15 | +#   package. Its row is FLAGGED with the exception in plain words; its sentence opens the review flags (the note's top
  16 | +#   line) and is not a doubt about the content, so it never counts toward REVIEW_FLAGS_MAX.
  17 |  
  18 |  
  19 |  # RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
  20 | @@ -397,9 +401,11 @@ def flagged_ok(g, row):
  21 |  
  22 |  
  23 |  def review_flags_of(gates):
  24 | -    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once."""
  25 | +    """RULING 137: the plain-word flags of the inventory's FLAGGED rows, in gate order, each once; RULING 144: an
  26 | +    exception's row first (the note's top line)."""
  27 |      out = []
  28 | -    for _g, row in (gates.items() if isinstance(gates, dict) else ()):
  29 | +    items = list(gates.items()) if isinstance(gates, dict) else []
  30 | +    for _g, row in sorted(items, key=lambda kv: kv[0] != EXCEPTION_GATE):
  31 |          if isinstance(row, dict) and row.get("status") == "FLAGGED":
  32 |              out += [f for f in row.get("flags") or [] if isinstance(f, str) and f not in out]
  33 |      return out
  34 | @@ -410,8 +416,14 @@ def review_problems(mp):
  35 |      over REVIEW_FLAGS_MAX (empty = it holds)."""
  36 |      want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
  37 |      out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
  38 | -    return out + ([f"{len(want)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"]
  39 | -                  if len(want) > REVIEW_FLAGS_MAX else [])
  40 | +    n = content_flags(mp.get("gates"))
  41 | +    return out + ([f"{n} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if n > REVIEW_FLAGS_MAX else [])
  42 | +
  43 | +
  44 | +def content_flags(gates):
  45 | +    """RULING 136 (2) / 144: the flags that count toward REVIEW_FLAGS_MAX: every review flag except an exception's."""
  46 | +    exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
  47 | +    return len([f for f in review_flags_of(gates) if f not in exc])
  48 |  
  49 |  
  50 |  def gate_problems(gates, required=REQUIRED_GATES):
  51 | @@ -502,8 +514,8 @@ def to_pin(pk, run_name):
  52 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
  53 |          spotlight_problems(pk) + takeaway_problems(pk)
  54 |      rf = review_flags_of(pk.get("gates"))                 # RULING 137: derived from the sealed gates, at most 3
  55 | -    problems += [f"{len(rf)} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if len(rf) > REVIEW_FLAGS_MAX \
  56 | -        else []
  57 | +    problems += [f"{content_flags(pk.get('gates'))} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] \
  58 | +        if content_flags(pk.get("gates")) > REVIEW_FLAGS_MAX else []
  59 |      if problems:
  60 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
  61 |      segs = []
  62 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  63 | index 3359471..55b6b06 100644
  64 | --- a/tests/package/proof_ledger.py
  65 | +++ b/tests/package/proof_ledger.py
  66 | @@ -249,6 +249,7 @@ def delivered_pins(paths):
  67 |      return spans, newest, pins
  68 |  
  69 |  
  70 | +PBX_EXCEPTION_MAX_H = 30.0     # RULING 144 (PBX 07:05 ET Nov 18): yesterday's batch, for one package only
  71 |  STOP_CEILING_USD = 1.50          # RULING 137 (3) (orchestrator 11:05 ET Nov 17): the day cap is $1.50 all-in from the
  72 |  #   21:10 ET day of Nov 17 (today's stop $1.40, given as --stop-usd); --stop-usd at most this. Was 1.25 (ORDER 17:50 ET
  73 |  #   Nov 16, 'ADD 25 CENTS').
  74 | @@ -443,14 +444,25 @@ def main(argv=None):
  75 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  76 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  77 |                      f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  78 | +    ap.add_argument("--pbx-exception", metavar="TEXT", default=None,
  79 | +                    help="RULING 144 (PBX 07:05 ET Nov 18): this ONE build's 12 h window is waived, named and logged "
  80 | +                         "(TEXT starts 'PBX exception'): --hours may reach PBX_EXCEPTION_MAX_H, every 12 h check of "
  81 | +                         "this process reads it, and the package carries TEXT as its first review flag")
  82 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
  83 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
  84 |                           "record (its tried[N]; default the first that passed), as it was judged")
  85 |      a = ap.parse_args(argv)
  86 |      now = datetime.now(timezone.utc)
  87 | -    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
  88 | -        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
  89 | +    if a.pbx_exception is not None and not (isinstance(a.pbx_exception, str) and
  90 | +                                            a.pbx_exception.startswith("PBX exception") and a.pbx_exception.strip()):
  91 | +        print("REFUSED (ruling 144): --pbx-exception must name the exception ('PBX exception ...')", file=sys.stderr)
  92 |          return 2
  93 | +    cap = PBX_EXCEPTION_MAX_H if a.pbx_exception else package_pin.WINDOW_H
  94 | +    if not 0 < a.hours <= cap:                           # ruling 76: "rather than widen the window" (144: one exception)
  95 | +        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  96 | +        return 2
  97 | +    if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  98 | +        package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  99 |      try:                                                 # read before anything is written (glm C2 N-4)
 100 |          delivered, last, pins = delivered_pins(a.delivered)
 101 |          since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 102 | @@ -641,6 +653,11 @@ def main(argv=None):
 103 |      if res["package"]:
 104 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 105 |          try:
 106 | +            if a.pbx_exception:                          # RULING 144: the exception's row, its plain words first
 107 | +                res["package"]["gates"][package_pin.EXCEPTION_GATE] = {
 108 | +                    "status": "FLAGGED", "flags": [a.pbx_exception], "by": "ruling 144 (PBX 07:05 ET Nov 18)",
 109 | +                    "replayed": False, "n": len(res["package"]["segments"]), "window_h": a.hours}
 110 | +                res["pbx_exception"] = {"text": a.pbx_exception, "window_h": a.hours}
 111 |              lock = LP.pin_problems(res["package"]) + \
 112 |                  package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
 113 |              if lock:
 114 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 115 | index b0e276d..a679178 100644
 116 | --- a/tests/package/test_ruling_137.py
 117 | +++ b/tests/package/test_ruling_137.py
 118 | @@ -548,6 +548,52 @@ class TestRuling141LineUpChain(unittest.TestCase):
 119 |          self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 120 |  
 121 |  
 122 | +class TestRuling144TheOneException(unittest.TestCase):
 123 | +    """RULING 144 (PBX 07:05 ET Nov 18): ONE build's 12 h window waived, named and logged. Its row is FLAGGED with the
 124 | +    plain words, they open the review flags (the note's top line), and they never count toward the cap of 3."""
 125 | +    EXC = "PBX exception Nov 18: these clips are older than 12 hours (allowed for this one video only)"
 126 | +
 127 | +    def gates(self, n_content):
 128 | +        g = {f"g{i}": {"status": "FLAGGED", "flags": [f"doubt {i}"], "by": "x", "replayed": False, "n": 1}
 129 | +             for i in range(n_content)}
 130 | +        g[PP.EXCEPTION_GATE] = {"status": "FLAGGED", "flags": [self.EXC], "by": "ruling 144", "replayed": False, "n": 3}
 131 | +        return g
 132 | +
 133 | +    def test_the_exception_reads_first_and_is_not_a_doubt(self):
 134 | +        g = self.gates(3)
 135 | +        self.assertEqual(PP.review_flags_of(g), [self.EXC, "doubt 0", "doubt 1", "doubt 2"])
 136 | +        self.assertEqual(PP.content_flags(g), 3)
 137 | +        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
 138 | +        self.assertEqual(len(PP.review_problems({"gates": self.gates(4), "review_flags": PP.review_flags_of(
 139 | +            self.gates(4))})), 1)                                           # a 4th DOUBT still refuses
 140 | +        self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)
 141 | +
 142 | +    def test_the_driver_takes_it_only_named_and_only_in_this_process(self):
 143 | +        import proof_ledger as PLG
 144 | +        pins = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
 145 | +                for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]
 146 | +
 147 | +        class Past(Exception):
 148 | +            pass
 149 | +
 150 | +        def stop(*a, **k):
 151 | +            raise Past()
 152 | +        saved = PP.WINDOW_H
 153 | +        try:
 154 | +            with mock.patch("sys.stderr"):
 155 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26"]), 2)            # 12 h as ever
 156 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "please"]), 2)
 157 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "31", "--pbx-exception",
 158 | +                                           "PBX exception x"]), 2)                                  # 30 h at most
 159 | +            self.assertEqual(PP.WINDOW_H, saved)                               # nothing changed by a refusal
 160 | +            with mock.patch.object(PLG, "delivered_pins", stop):
 161 | +                with self.assertRaises(Past):
 162 | +                    PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "PBX exception x"])
 163 | +            self.assertEqual(PP.WINDOW_H, 26.0)                                # this process: every 12 h check reads it
 164 | +        finally:
 165 | +            PP.WINDOW_H = saved
 166 | +
 167 | +
 168 |  class TestTheDayCount(unittest.TestCase):
 169 |      def test_counted_per_day_ledger(self):
 170 |          with tempfile.TemporaryDirectory() as d:
 171 | 
```

---

pp-selectid: RULING 144 (orchestrator 07:15 ET Nov 18, PBX's words 07:05: "disregard the 12 hour rule for this one
exception and get this video done"). ONE package, from yesterday's batch, with the 12 h window waived: a NAMED, LOGGED
exception ('PBX exception Nov 18: clips older than 12 hours'); never-reused still holds; the rule is back for every
later build. The integrator's render needs nothing (its only age gate is L-v 3's 24 h for time_sensitive segments) and
asked that the exception's plain words be the FIRST review flag (its note prints review flags first). Files:
tests/package/proof_ledger.py (the build driver), pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE:
(a) proof_ledger: --pbx-exception TEXT. Refused (exit 2, before anything is written) unless TEXT starts "PBX exception".
    With it, --hours may reach PBX_EXCEPTION_MAX_H (30) instead of package_pin.WINDOW_H (12); without it, 12 as ever.
    package_pin.WINDOW_H = hours FOR THIS PROCESS ONLY (one build = one process; every 12 h check reads that constant:
    package.expired, package_pin.window_problems at the seal, the candidate registry's expiry). After the package seals
    and before its pin is written, the driver adds the exception's gate row (FLAGGED, flags [TEXT], replayed False) and
    records res["pbx_exception"].
(b) package_pin: EXCEPTION_GATE "pbx_exception" in SOFT_GATES (FLAGGED accepted by gate_problems as any soft row);
    review_flags_of lists its flags FIRST; content_flags = the review flags except the exception's: the cap of 3
    (to_pin and review_problems) counts only doubts about the content.

TESTS (test_ruling_137, 2 new): the exception first and not counted (3 doubts + it seal; a 4th doubt still refuses);
the driver: --hours 26 without the exception refused, an unnamed exception refused, 31 h refused, nothing changed by a
refusal, and with a named exception the window becomes 26 for the process. Mutations: 7 of 7 killed.

PLEASE CHECK: (1) can the exception leak to a later build or another pin? (2) can it carry more than ONE flag past the
cap, or hide a doubt? (3) anything else the 12 h rule guards that this bypasses (never-reused must hold)? (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
