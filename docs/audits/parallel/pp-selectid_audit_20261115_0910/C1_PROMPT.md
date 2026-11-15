# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_0910
# Branch: pp-selectid
# Generated: 2026-11-15 09:13 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_0910/C1_STEP.diff (94 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 967f665..08c0035 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2543,6 +2543,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |      #   video at most once, L-y 4)
   7 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
   8 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
   9 | +    n_ch = len({m["channel_id"] for m in ms})
  10 | +    if candidate is None and n_ch < 3:
  11 | +        # RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel
  12 | +        # cannot make a medley ... run the SPOTLIGHT path"). Every later stage only removes moments (step A's `cleared`
  13 | +        # is a subset of this pool), so the same rule on the cleared moments below would refuse this pool anyway, after
  14 | +        # step A and ruling 101's confirm ahead were paid. It ends here, before any paid verdict; the spotlight (ruling
  15 | +        # 90) runs next as usual. A candidate build (ruling 66) keeps its own path: its outcome is out["candidate"].
  16 | +        why_none = (f"the pool spans {n_ch} channel(s) after the free stages: a medley needs 3; no paid verdict "
  17 | +                    f"(ruling 109)")
  18 | +        log(f"  {n_usable} usable, {len(ms)} in the pool after the free stages: {why_none}")
  19 | +        return {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable,   # out's shape
  20 | +                "current_levels": current_levels(sources.values(), ctx), "no_role": no_role, "ad_read": ad_read,
  21 | +                "trimmed": {k: v["moment_id"] for k, v in trims.items()}, "reposted": reposted,
  22 | +                "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
  23 | +                "prescreen": {"screened": 0, "cleared": 0, "failed": {}, "parallel_101": None,
  24 | +                              "held_102": {"first": [], "second": []}, "last_resort_87": {}},
  25 | +                "angles": [], "takeaways": [], "package": None, "why_none": why_none,
  26 | +                "ruling_109": {"channels": n_ch, "pool": len(ms)}}
  27 |      wv, wf = _writers(router)
  28 |      fb = first_bounds(router)
  29 |      plan = step_a_plan(router, ms, sources, ctx, wv, wf, store=store, cache=step_a_cache, **fb)   # RULING 101
  30 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  31 | index af68ac8..3f62bd8 100644
  32 | --- a/tests/package/test_medley.py
  33 | +++ b/tests/package/test_medley.py
  34 | @@ -3817,5 +3817,59 @@ class TestTakeawayValueRow(unittest.TestCase):
  35 |          package_pin.to_pin(spk(dict(pk, gates=TestMedleyPackageAndPin().gates(pk))), "test")   # the right row: pins
  36 |  
  37 |  
  38 | +class TestRuling109Channels(unittest.TestCase):
  39 | +    """RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel cannot
  40 | +    make a medley ... run the SPOTLIGHT path"): a pool of fewer than 3 channels after the free stages ends the medley
  41 | +    before any paid verdict, with the record the rule on the cleared moments returns; 3 channels are screened and
  42 | +    packaged as before; a build from a ruling-66 candidate keeps its own path."""
  43 | +    ALL = ["h", "x", "y", "z"]
  44 | +
  45 | +    def pool(self, chans):
  46 | +        return [pm(mid, ch, 12.0 + i) for i, (mid, ch) in enumerate(zip(self.ALL, chans))]
  47 | +
  48 | +    def test_one_or_two_channels_ask_nothing(self):
  49 | +        for chans in ("AAAA", "AABB"):
  50 | +            rig = Rig(self.pool(chans), self.ALL, [], [])
  51 | +            out = rig.run()
  52 | +            self.assertEqual((rig.screens, rig.events, rig.hook_calls, rig.visual_calls, rig.medley_calls),
  53 | +                             ([], [], [], [], []), chans)                  # no step A, no call of any kind
  54 | +            n = len(set(chans))
  55 | +            self.assertEqual(out["why_none"], f"the pool spans {n} channel(s) after the free stages: a medley needs 3; "
  56 | +                                              f"no paid verdict (ruling 109)")
  57 | +            self.assertEqual((out["package"], out["usable"], out["prescreen"]["cleared"], out["ruling_109"]),
  58 | +                             (None, 4, 0, {"channels": n, "pool": 4}))
  59 | +
  60 | +    def test_the_channels_are_counted_after_the_free_stages(self):
  61 | +        off = dict(pm("w", "C", 12.0), text="The weather was lovely at the lake today.")   # a third channel, but no
  62 | +        rig = Rig(self.pool("AABB") + [off], self.ALL, [], [])                             # place under the topic rule
  63 | +        out = rig.run()
  64 | +        self.assertEqual((rig.screens, rig.events), ([], []))
  65 | +        self.assertIn("w", out["no_role"])
  66 | +        self.assertEqual((out["usable"], out["ruling_109"]), (5, {"channels": 2, "pool": 4}))
  67 | +
  68 | +    def test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns(self):
  69 | +        gate = Rig(self.pool("AABB"), self.ALL, [], []).run()
  70 | +        late = Rig(self.pool("ABCD"), self.ALL, [], [],
  71 | +                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"], ("xai", "z"): ["REFERENT_OUTSIDE"]}).run()
  72 | +        self.assertEqual(late["why_none"], "2 moments cleared step A from fewer than 3 channels")   # the rule, after
  73 | +        self.assertEqual(set(gate) - {"ruling_109"}, set(late))                                     # step A was paid
  74 | +        self.assertEqual(set(gate["prescreen"]), set(late["prescreen"]))
  75 | +        self.assertEqual(set(gate["scorer"]), set(late["scorer"]))
  76 | +
  77 | +    def test_three_channels_are_screened_and_packaged_as_before(self):
  78 | +        rig = Rig(self.pool("ABCA"), self.ALL, [(True, [], None, Rig.LINE)], [None])
  79 | +        out = rig.run()
  80 | +        self.assertEqual(rig.screens[0], ("xai:grok", self.ALL))
  81 | +        self.assertIsNotNone(out["package"])
  82 | +        self.assertNotIn("ruling_109", out)
  83 | +
  84 | +    def test_a_build_from_a_candidate_keeps_its_own_path(self):
  85 | +        c = PK.load_candidate(TestRuling66Candidate().record())
  86 | +        rig = Rig(self.pool("AABB"), self.ALL, [], [], candidate=c)
  87 | +        out = rig.run()
  88 | +        self.assertEqual(rig.screens, [("xai:grok", self.ALL)])           # screened as before this gate
  89 | +        self.assertNotIn("ruling_109", out)
  90 | +
  91 | +
  92 |  if __name__ == "__main__":
  93 |      unittest.main()
  94 | 
```

---

pp-selectid, THE ORCHESTRATOR'S ORDER 08:56 ET Nov 15, item 2: "one channel cannot make a medley (channel rules), so
run the SPOTLIGHT path on it (ruling 109 free gates first, ruling 107 guard)". RULING 109 (21:30 ET Nov 14): free
gates first; a paid verdict only for what every free gate passed.

THE FINDING. The build driver (tests/package/proof_ledger.py, UNCHANGED) always runs the medley first (package.build),
then the spotlight (spotlight.build, ruling 90; proof_ledger.py:500). The medley pays step A on EVERY moment of its pool
(package.prescreen, pipeline/package.py:2554 in the base) and ruling 101's Grok confirm ahead beside it (:2548-2551)
BEFORE its 3-channel rule (:2587, UNCHANGED: `if len({m["channel_id"] for m in cleared.values()}) < 3:` -> why_none,
return out). This morning's 12-h pool is 63 moments from 2 channels, so the medley pays step A (and the confirm ahead)
on all of them and then refuses. The spotlight's own free gate (ruling 109: an ALONE score known below 4 never reaches
step A, pipeline/spotlight.py:855-862, UNCHANGED) asks only what passes it.

THE CHANGE (pipeline/package.py build(), after the free stages: usable, reposted_once, scorer_pass, the no-role and
trim rules, ad_read_out; before _writers / first_bounds / step_a_plan / confirm_ahead / prescreen): when the pool spans
fewer than 3 channels and the build is not from a ruling-66 candidate, build() returns at once with the record the rule
at :2587 returns (the same keys; prescreen: screened 0, cleared 0, failed {}, parallel_101 None, held_102 empty,
last_resort_87 {}), why_none "the pool spans N channel(s) after the free stages: a medley needs 3; no paid verdict
(ruling 109)", and "ruling_109": {"channels": N, "pool": the pool's size}.

WHY IT CHANGES NO OUTCOME. Nothing between the gate and :2587 adds a moment: `cleared` (:2562) is a subset of `ms`, the
pool at the gate. So the rule at :2587 refuses every pool the gate refuses; the gate only removes the paid calls before
it. The spotlight runs next as usual (proof_ledger.py:500), with its own free gates, and reads the same step-A cache.

WHY CANDIDATE BUILDS ARE LEFT OUT. A build from a ruling-66 candidate returns its outcome in out["candidate"] (set at
:2703, after this point), and proof_ledger's try_one reads it (tests/package/proof_ledger.py:484
`return o, o["candidate"]["class"], ...`, outside its try). The gate's record has no "candidate", so a candidate build
keeps its path, unchanged.

A PRE-EXISTING DEFECT, FLAGGED, NOT FIXED HERE (law K2). The early returns before :2703 (the rule at :2587, :2590 no
work_dir, the no-opener return, :2681, the no-hook return) give a CANDIDATE build no out["candidate"], so
proof_ledger.py:484 would raise KeyError outside its try. No candidate is due today: all are over 12 h old and expire
first (CA.expire, proof_ledger.py:380; this morning's build logged "RULING 66: no candidate is due"). Say whether you
think it must be fixed in this change.

THE GUARD. Ruling 107 (1)'s open_work (proof_ledger.py:146-155, UNCHANGED) reads prescreen.held_102 and visual.unmeasured.
The gate's record has held_102 empty and no "visual", so it leaves no open work, which is right: nothing was asked.
CA.seed (tests/package/candidates.py:61, UNCHANGED) reads record.get("tried") or []: the gate's record has none.

TESTS: tests/package/test_medley.py, class TestRuling109Channels (5), on the existing Rig (every model stubbed):
- one or two channels ask nothing (no step A, no call of any kind);
- the channels are counted after the free stages (a third channel whose only moment fails the topic rule is not counted);
- the record's keys are those the rule at :2587 returns;
- three channels are screened and packaged as before;
- a candidate build keeps its path.
10 of 10 mutations are killed. tests/package (552) and tests/moments, select_by_id and providers (127) all pass.

PLEASE CHECK: (1) that the gate cannot refuse a pool that could seat a medley (the subset argument: does anything after
the gate ADD a moment or a channel?); (2) that nothing paid runs before it (scorer_pass, trim_variant, ad_read_out,
current_levels); (3) the record's shape against the :2587 return and its readers (proof_ledger: res["usable"],
res["prescreen"].get("cleared"), open_work; CA.seed); (4) the candidate exclusion; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
