# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_2134
# Branch: pp-selectid
# Generated: 2026-11-16 21:34 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_2134/C1_STEP.diff (183 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 4e971be..70e79be 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -469,6 +469,16 @@ def is_held(why):
   6 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
   7 |  
   8 |  
   9 | +def local_held(a):
  10 | +    """RULING 127 (2) (orchestrator 21:30 ET Nov 16): a step-A verdict from the local judge (gemma3:27b, ruling 87's last
  11 | +    resort), PASS or REFUSE, is never final while a Heimdall family can be asked: HELD, 'local, provisional', never
  12 | +    cached, asked again next build; a sealed package needs the second screen from a real second family. -> the reason."""
  13 | +    why = CI.a_failures(a)
  14 | +    return (f"{HELD}: local, provisional (ruling 127 (2)): the local judge {a.get('backend')}'s verdict "
  15 | +            f"({'refuse: ' + '+'.join(map(str, why)) if why else 'pass'}) is never final while a Heimdall family can "
  16 | +            f"be asked; never cached; held for this build, retried next build")
  17 | +
  18 | +
  19 |  def last_resort_of(verdicts):
  20 |      """RULING 102: the back-ends among `verdicts` (A items) that are the local judge's (ruling 87's last resort)."""
  21 |      return sorted({str(a.get("backend")) for a in verdicts or () if isinstance(a, dict)
  22 | @@ -574,7 +584,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  23 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  24 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  25 |      pick = lambda key: next((x for name, x in sorted((cdb.get(key) or {}).items())        # a cached verdict off the
  26 | -                             if isinstance(x, dict) and off(name) and x.get("backend") == name), None)   # writers'
  27 | +                             if isinstance(x, dict) and off(name) and x.get("backend") == name    # writers', never
  28 | +                             and not name.startswith(LAST_RESORT)), None)                         # the local judge's
  29 |      moved = {}                                          # ruling 126 (1): old-key verdicts, written under the new key
  30 |      a_by, fails, vendors, families, todo, contexts, keys = {}, {}, set(), set(), [], {}, {}
  31 |      for m in order:
  32 | @@ -588,7 +599,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  33 |                           "show_date": CI.show_date(ctx.now)}       # RULING 126 (1): the ET date
  34 |          keys[mid] = step_a_key(m, contexts[mid])                          # ruling 126 (1): the date only with time words
  35 |          rec = db.get(f"{mid}:{STEP_A_VERSION}")
  36 | -        if not (isinstance(rec, dict) and off(rec.get("backend"))):
  37 | +        if not (isinstance(rec, dict) and off(rec.get("backend"))
  38 | +                and not str(rec.get("backend")).startswith(LAST_RESORT)):        # ruling 127 (2): never the local judge's
  39 |              rec = pick(keys[mid])
  40 |              if rec is None and not time_sensitive(m):    # RULING 126 (1): a verdict cached before the date left the key
  41 |                  rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
  42 | @@ -623,6 +635,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  43 |                  fails[m["moment_id"]] = [held_why(e)]
  44 |              continue
  45 |          items, backend = got
  46 | +        if str(backend).startswith(LAST_RESORT):         # RULING 127 (2): the local judge's verdicts are provisional:
  47 | +            for mid, a in items.items():                 # held, never a pass or a refusal, never cached, no vendor
  48 | +                fails[mid] = [local_held(dict(a, backend=backend))]
  49 | +            continue
  50 |          b = router.backends.get(backend)
  51 |          vendors.add(b.vendor if b else backend)
  52 |          families.add(b.family if b else backend)
  53 | @@ -810,6 +826,8 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
  54 |              if fails.get(mid) or a2 is None:            # ruling 102: no verdict at all is HELD, retried next build
  55 |                  fail[mid] = list(fails.get(mid) or [f"{HELD}: no second verdict (law L-m); held for this build, "
  56 |                                                      f"retried next build"])
  57 | +            elif str(a2.get("backend") or "").startswith(LAST_RESORT):   # RULING 127 (2): never the second family
  58 | +                fail[mid] = [local_held(a2)]
  59 |              elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
  60 |                  fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
  61 |                               f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
  62 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
  63 | index 08e48db..5c086fa 100644
  64 | --- a/tests/package/test_ruling_102.py
  65 | +++ b/tests/package/test_ruling_102.py
  66 | @@ -108,21 +108,70 @@ class TestTheSecondFamily(unittest.TestCase):
  67 |          with open(self.cache) as f:
  68 |              return {k: sorted(v) for k, v in json.load(f).items()}
  69 |  
  70 | -    def test_every_faster_leg_unavailable_the_local_judge_answers_and_is_the_last_resort(self):
  71 | +    def local(self, fail):
  72 | +        """RULING 127 (2): every moment HELD as the local judge's provisional verdict, never a pass or a refusal."""
  73 | +        self.assertEqual(sorted(fail), sorted(self.cleared))
  74 | +        self.assertTrue(all(PK.is_held(f) and "local, provisional" in f[0] for f in fail.values()), fail)
  75 | +
  76 | +    def test_every_faster_leg_unavailable_the_local_judges_answer_is_provisional_never_a_pass_never_cached(self):
  77 | +        """RULING 127 (2) (21:30 ET Nov 16): the local judge answers the second screen and its verdict is HELD as
  78 | +        'local, provisional' (no seal can rest on it), never cached; the next build asks Heimdall again."""
  79 |          legs = [Leg(X), Leg(DS, P.Unavailable("HTTP 503")), Leg(G, P.Unavailable("HTTP 503")),
  80 |                  Leg(GEM, P.Unavailable("HTTP 429")), Leg(LJ)]
  81 |          two, fail = self.screen(legs)
  82 | -        self.assertEqual(fail, {})
  83 | -        self.assertEqual({mid: [a["backend"] for a in v] for mid, v in two.items()},
  84 | -                         {mid: [X, LJ] for mid in self.cleared})                 # off Grok: the last leg answered
  85 | +        self.assertEqual(two, {})
  86 | +        self.local(fail)
  87 |          self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])               # in order, each once, never Grok
  88 | -        self.assertEqual({mid: PK.last_resort_of(v) for mid, v in two.items()}, {mid: [LJ] for mid in self.cleared})
  89 | +        self.assertEqual(self.cached(), {})                                      # never remembered
  90 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]                       # the next build: deepseek is back
  91 | +        two, fail = self.screen(legs)
  92 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {DS}))   # asked again, answered
  93 | +
  94 | +    def test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read(self):
  95 | +        """RULING 127 (2): a REFUSE from the local judge is not final either; a local verdict found in the cache (from
  96 | +        before the rule) is passed over and Heimdall is asked."""
  97 | +        legs = [Leg(X)] + [Leg(n, P.Unavailable("down")) for n in (DS, G, GEM)] + [Leg(LJ)]
  98 | +        with mock.patch.object(PK.CI, "a_failures", lambda a: ["REFERENT_OUTSIDE"]):
  99 | +            two, fail = self.screen(legs)
 100 | +        self.assertEqual(two, {})
 101 | +        self.local(fail)
 102 | +        self.assertTrue(all("refuse: REFERENT_OUTSIDE" in f[0] for f in fail.values()), fail)
 103 | +        self.assertEqual(self.cached(), {})
 104 | +        ctx = TM.ctx()
 105 | +        for m in self.ms:                                # a local verdict cached under each moment's key
 106 | +            legs = [Leg(X), Leg(DS)]
 107 | +            rr = router(self.d.name, legs)
 108 | +            PK.prescreen(rr, [m], self.srcs, ctx, {"xai"}, {"grok"}, cache=self.cache, kind="step_a_second",
 109 | +                         failover=True)
 110 | +            with open(self.cache) as f:
 111 | +                d = json.load(f)
 112 | +            k = next(k for k in d if k.startswith(m["moment_id"] + ":"))
 113 | +            d[k] = {LJ: dict(d[k][DS], backend=LJ)}      # the same verdict, as if the local judge had given it
 114 | +            with open(self.cache, "w") as f:
 115 | +                json.dump(d, f)
 116 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]
 117 | +        two, fail = self.screen(legs)
 118 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {DS}))   # Heimdall asked again
 119 | +        self.assertEqual(legs[1].calls, 1)
 120 | +        store = os.path.join(self.d.name, "store.json")  # nor from the build's own ledger (store)
 121 | +        with open(store, "w") as f:
 122 | +            json.dump({f"{m['moment_id']}:{PK.STEP_A_VERSION}": dict(a_item(m["moment_id"]), backend=LJ)
 123 | +                       for m in self.ms}, f)
 124 | +        os.remove(self.cache)
 125 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]   # the local judge a real back-end here: off the writers
 126 | +        a_by, fails, vendors, _ = PK.prescreen(router(self.d.name, legs), self.ms, self.srcs, ctx, {"xai"}, {"grok"},
 127 | +                                               store=store, cache=self.cache, kind="step_a_second", failover=True)
 128 | +        self.assertEqual(({a["backend"] for a in a_by.values()}, legs[1].calls), ({DS}, 1))
 129 |  
 130 |      def test_the_order_is_deepseek_glm_gemini_the_judge(self):
 131 | -        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), LJ)):
 132 | +        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), None)):
 133 |              legs = [Leg(n, P.Unavailable("down") if n in down else None) for n in LEGS]
 134 |              two, fail = self.screen(legs)
 135 | -            self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 136 | +            if want is None:                             # RULING 127 (2): the judge answers, provisional, held
 137 | +                self.assertEqual(two, {})
 138 | +                self.local(fail)
 139 | +            else:
 140 | +                self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 141 |              os.path.exists(self.cache) and os.remove(self.cache)
 142 |          legs = [Leg(n) for n in LEGS]                         # a first verdict from glm: Grok confirms, as before
 143 |          two, _ = self.screen(legs, first=G)
 144 | @@ -132,7 +181,8 @@ class TestTheSecondFamily(unittest.TestCase):
 145 |          legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G, P.DeadlineExceeded("no answer within 60 s")),
 146 |                  Leg(GEM, P.RequestRejected("refused this request")), Leg(LJ)]
 147 |          two, fail = self.screen(legs)
 148 | -        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {LJ}))
 149 | +        self.assertEqual(two, {})                        # ruling 127 (2): the judge's answer is provisional, held
 150 | +        self.local(fail)
 151 |          self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])
 152 |  
 153 |      def test_no_leg_answers_the_clip_is_held_never_cached_and_retried_next_build(self):
 154 | @@ -182,7 +232,9 @@ class TestInTheBuild(unittest.TestCase):
 155 |          self.assertTrue(PK.is_held(out["prescreen"]["failed"]["z"]))
 156 |          self.assertIsNotNone(out["package"])                      # the build goes on without it
 157 |  
 158 | -    def test_a_pin_judged_by_the_local_judge_says_so(self):
 159 | +    def test_a_second_verdict_from_the_local_judge_never_seals_a_package(self):
 160 | +        """RULING 127 (2): even when a screen hands the build the local judge's second verdicts as answers, each is
 161 | +        HELD ('local, provisional'): no clip passes the second family on it, so no package seals on it."""
 162 |          rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None])
 163 |          rig.router.backends[LJ] = type("B", (), {"vendor": "local_judge", "family": "gemma"})()
 164 |          pre = rig.prescreen
 165 | @@ -196,13 +248,10 @@ class TestInTheBuild(unittest.TestCase):
 166 |              return got, fails, v, f
 167 |          rig.prescreen = judged
 168 |          out = rig.run()
 169 | -        segs = out["package"]["segments"]
 170 | -        self.assertEqual(out["prescreen"]["last_resort_87"], {mid: [LJ] for mid in sorted(out["prescreen"]
 171 | -                                                                                         ["last_resort_87"])})
 172 | -        self.assertTrue({sg["moment_id"] for sg in segs} <= set(out["prescreen"]["last_resort_87"]))
 173 | -        row = out["package"]["gates"]["context_a"]
 174 | -        self.assertEqual(row["last_resort"]["verdicts"], {sg["label"]: LJ for sg in segs})
 175 | -        self.assertEqual(row["status"], "PASS")
 176 | +        self.assertIsNone(out["package"])
 177 | +        self.assertEqual(out["prescreen"]["last_resort_87"], {})
 178 | +        local = {mid: w for mid, w in out["prescreen"]["second_vendor"].items() if "local, provisional" in str(w)}
 179 | +        self.assertTrue(local and all(str(w).startswith("HELD") for w in local.values()), out["prescreen"])
 180 |  
 181 |      def test_a_re_screen_off_the_writers_with_no_verdict_and_no_reason_is_held(self):
 182 |          """The writers' re-screen (order 06:22 item 44): a clip it returns nothing at all for is HELD (its default
 183 | 
```

---

pp-selectid: RULING 127 (2) (orchestrator 21:30 ET Nov 16), verbatim: "A verdict from the local gemma3:27b that REFUSES is
never final while a Heimdall family can still be asked: it is recorded as 'local, provisional' and asked again of
Heimdall; it must not be cached as the second vendor's verdict. ... A local PASS is not final either: a sealed package
needs the second screen from a real second family. If a code change is needed for (2), make the smallest one, audit on
Heimdall (it is a verdict-source rule, so it must be audited)". Files: pipeline/package.py, tests/package/test_ruling_102.py.
The diff is on top of ruling 126 (1)'s (audit 20261116_2005, cleared, not yet landed); only 127 (2)'s lines are new here.

UNCHANGED CODE IT USES (package.py): HELD = "STEP_A_HELD (ruling 102)" (:451), LAST_RESORT = "local_judge:" (:452, the
local judge's back-end names: providers.LocalJudgeBackend, vendor "local_judge"), is_held(why) (:467: every reason
starts with HELD), last_resort_of / last_resort_note (the pin's record of local verdicts: now never reached, left as
they are), second_screen's existing branches (no verdict = HELD; same vendor = refused), CI.step_a's failover (a leg out
of contract or past its deadline moves on; the chain's last leg is the local judge).

THE CHANGE:
(a) package.local_held(a): the reason: "STEP_A_HELD (ruling 102): local, provisional (ruling 127 (2)): the local judge
    <backend>'s verdict (pass | refuse: <reasons>) is never final while a Heimdall family can be asked; never cached;
    held for this build, retried next build".
(b) prescreen, after a call: when the back-end that answered is the local judge's (its name starts with LAST_RESORT),
    each of its moments gets that HELD reason; nothing goes to a_by, the build's store (db), the shared cache (new) or
    the vendor/family sets.
(c) prescreen, reading: a cached verdict (pick) or a stored one (db) from the local judge is never used; the moment is
    asked again.
(d) second_screen: a second verdict whose back-end is the local judge's is HELD with that reason, never a pass (for
    any screen that hands one in; (b) already keeps prescreen from doing so).

TESTS (test_ruling_102): the second screen's chain spent down to the local judge: its answer HELD 'local, provisional',
never cached, deepseek asked again next build; a local REFUSE likewise (its reasons in the HELD text); a local verdict in
the cache or in the build's store is passed over and Heimdall asked; the chain-order test and the out-of-contract test
now end HELD at the judge; in the build, second verdicts handed in from the local judge seal no package
(last_resort_87 empty). Mutations L1-L5 after a control run: 5 of 5 killed. Suites: 40 files by exit code, 850 tests.

PLEASE CHECK: (1) that no path can still seal or cache on a local verdict; (2) that a local verdict is HELD (retried),
never a refusal; (3) that nothing else changed for the other legs; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
