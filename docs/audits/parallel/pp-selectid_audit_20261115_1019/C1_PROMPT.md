# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1019
# Branch: pp-selectid
# Generated: 2026-11-15 10:19 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1019/C1_STEP.diff (91 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 63860a3..30bbf8e 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -403,17 +403,23 @@ def main(argv=None):
   6 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
   7 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
   8 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
   9 | -    refused = wp_rep.get("refused") or []                # final: the worker never re-works them (the inputs keep ids)
  10 | -    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(refused)))}")
  11 | +    wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids).
  12 | +    #   Its own name: main() later binds `refused` to start_refused()'s answer (build 6, 10:10 ET Nov 15, reported
  13 | +    #   0 refused on ruling 95's line when this list was still called `refused`)
  14 | +    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(wp_refused)))}")
  15 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
  16 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
  17 | -                                               word_pass_refused=refused)
  18 | +                                               word_pass_refused=wp_refused)
  19 |      inputs["word_pass"] = wp_rep
  20 | +    try:                                                 # RULING 95: when the next qualifying episode could arrive. It
  21 | +        next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
  22 | +    except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
  23 | +        next_try = {"error": f"{type(e).__name__}: {str(e)[:200]}"}       # never the build
  24 |      moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
  25 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
  26 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
  27 | -                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  28 | -                  f, indent=1, default=str)
  29 | +                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments,
  30 | +                   "next_attempt": next_try}, f, indent=1, default=str)
  31 |      pool = json.loads(json.dumps(moments, default=str))   # RULING 107 (1): the pool as it came in, before any stage
  32 |      fp, fp_parts = fingerprint(pool, delivered, pins, since, now, reg, a.routing)
  33 |      same = None if cand is not None else nothing_new(os.path.join(HERE, "proof"), out_dir, fp)
  34 | @@ -506,10 +512,7 @@ def main(argv=None):
  35 |                      spotlit=spotlit)
  36 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
  37 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
  38 | -    try:                                                 # RULING 95: when the next qualifying episode could arrive
  39 | -        res["next_attempt"] = SPOT.next_attempt(rows, wp, now, refused=refused)
  40 | -    except Exception as e:                               # noqa: BLE001  a report, never the build
  41 | -        res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
  42 | +    res["next_attempt"] = next_try                       # RULING 95, computed beside the inputs above
  43 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
  44 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
  45 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
  46 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
  47 | index c1b3e31..cf9d7a6 100644
  48 | --- a/tests/package/test_ruling_107_guard.py
  49 | +++ b/tests/package/test_ruling_107_guard.py
  50 | @@ -161,8 +161,9 @@ class TestTheDriverAsksNoModel(Paths):
  51 |      PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
  52 |                                                                                    "MOMENTS_PIN_LY.json")]
  53 |  
  54 | -    def run_driver(self, left, wp_rep=None, seen=None):
  55 | -        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments."""
  56 | +    def run_driver(self, left, wp_rep=None, seen=None, rows=None):
  57 | +        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments;
  58 | +        rows: the ledger rows the stubbed adapter gives (default none)."""
  59 |          proof = os.path.join(self.tmp.name, "drv", "proof")
  60 |          os.makedirs(proof)
  61 |          delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
  62 | @@ -185,7 +186,7 @@ class TestTheDriverAsksNoModel(Paths):
  63 |          stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
  64 |                   mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
  65 |                   mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
  66 | -                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
  67 | +                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: (list(rows or []), {"excluded": {}})),
  68 |                   mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, dict(wp_rep or {"rows": 0}))),
  69 |                   mock.patch.object(PLG.LB, "build_inputs", inputs),
  70 |                   mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
  71 | @@ -223,6 +224,19 @@ class TestTheDriverAsksNoModel(Paths):
  72 |          self.assertEqual(json.load(open(os.path.join(runs[0], "inputs.json")))["inputs"]["word_pass"]["refused"],
  73 |                           ["Xa1", "Yb2"])
  74 |  
  75 | +    def test_ruling_95_counts_the_refused_from_the_inputs_alone(self):
  76 | +        """Build 6 (10:10 ET Nov 15) printed "0 refused" on ruling 95's line: main() rebound the driver's list to
  77 | +        start_refused()'s answer before ruling 95 read it. Ruling 95 now reads the inputs beside build_inputs, and
  78 | +        inputs.json records it, even for a build that stops with nothing new."""
  79 | +        at = datetime.now(timezone.utc).isoformat()
  80 | +        rows = [{"video_id": "v1", "channel_name": "Talk", "published_at": at, "moment_id": m,
  81 | +                 "episode": {"turns_per_min": 2.0}, "mined": {"pass": "moment", "prompt_version": "mine/2"}}
  82 | +                for m in ("Xa1", "Yb2", "Zc3")]
  83 | +        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, rows=rows)
  84 | +        na = json.load(open(os.path.join(runs[0], "inputs.json")))["next_attempt"]["conversation"]
  85 | +        self.assertEqual((rc, na["rows"], na["word_pass_ready"], na["word_pass_refused"], na["word_pass_waiting"]),
  86 | +                         (0, 3, 0, 2, 1))
  87 | +
  88 |      def test_work_left_undone_goes_on_to_the_router(self):
  89 |          rc, runs = self.run_driver(left=1)
  90 |          self.assertEqual(rc, "router")
  91 | 
```

---

pp-selectid: RULING 95'S REFUSED COUNT IN THE BUILD DRIVER, A NAME COLLISION FIXED. Reporting only: no gate, verdict
or selection changes.

THE DEFECT (mine; it landed in e19ec46c under audit 20261115_0951, where the mutation that dropped this keyword
SURVIVED, untested). In tests/package/proof_ledger.py main(), the word pass's refused ids were bound to `refused` at
:406 and passed to build_inputs at :410 (right) and to spotlight.next_attempt at :510 (wrong). Between the two, at :438
(UNCHANGED, base 1ffe2302), main() rebinds the same name: `refused = start_refused(spent0)`, the spend check's answer,
None when a build may start. So ruling 95 got refused=None. Builds 6 and 7 (10:10 and 10:16 ET Nov 15) printed
"19 waiting / 0 refused" and "17 waiting / 0 refused" for Bitcoin Magazine, whose rows were 12 and then 17 refused.
build_inputs' counts were right (16 and 21 refused).

THE FIX (tests/package/proof_ledger.py):
1. The list is named `wp_refused`, a name nothing else in main() binds. A comment says why.
2. Ruling 95's record (spotlight.next_attempt, UNCHANGED) is computed right after build_inputs, from the inputs alone
   (rows, the word-pass index, now, wp_refused). This is BEFORE the spend check and before any router. The record is
   written into inputs.json as "next_attempt", so even a build that stops with nothing new (ruling 107 (1)) records it.
   The build record's res["next_attempt"] is that same value; its try/except (a report, never the build) is kept.
   The value is the same as before, because next_attempt reads nothing the build later changes.

TESTS: test_ruling_107_guard's run_driver gains an optional `rows` (the stubbed adapter's rows). A new test,
test_ruling_95_counts_the_refused_from_the_inputs_alone, runs the real driver to its nothing-new stop with 3 rows, 2 of
them refused, and reads inputs.json: 3 rows, 0 ready, 2 refused, 1 waiting. Mutations: 4 of 5 killed after a control
run (the unmutated copy passes all 51 tests in the two files):
- ruling 95 without the refused: killed;
- not recorded in inputs.json: killed;
- build_inputs without the refused: killed;
- the log giving ids: killed.
The 1 that survives: res["next_attempt"] set to {} in the build record, past the router, which no test reaches (the
harness stops at nothing-new or at build_router). Suites: 685 pass.

PLEASE CHECK: (1) that nothing between the new computation and the build record could change what next_attempt reads
(rows, wp, now, wp_refused); (2) that no other name in main() collides (`wp_refused`, `next_try`); (3) that moving
ruling 95 before the guard changes no build outcome and keeps the "a report, never the build" behaviour; (4) the test
and its harness change; (5) whether the surviving mutation matters.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
