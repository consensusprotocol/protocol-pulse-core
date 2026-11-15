# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1700
# Branch: pp-selectid
# Generated: 2026-11-15 17:01 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1700/C1_STEP.diff (82 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 7a058ff..fc9cd76 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1936,6 +1936,30 @@ def reorder(segs, bad_pairs, judged, repeat_ok=False):
   6 |      return best[1] if best else None
   7 |  
   8 |  
   9 | +def join_moments(angle, cleared, doomed=frozenset()):
  10 | +    """RULING 117 (2): the moments an angle's join table is asked of -> their ids, the hook first: "the moments that
  11 | +    can be in a line-up for an angle" (from `cleared`: step A from both vendors, the second pass, CUTTABLE; not
  12 | +    doomed), at most JOIN_MOMENTS_MAX. lineup_ok's own rules bound the set: every clip is clip-eligible, and every
  13 | +    segment has its own video (one channel per segment, and L-y 4's supply exception still needs a video per segment),
  14 | +    so never a moment of the hook's own video. Order: the hook, its writer's other moments, then the rest of the pool by
  15 | +    rank score, one moment of each channel not yet in the set first (the 16:54 replay: a rank-only fill spent the
  16 | +    table on the hook's own video)."""
  17 | +    h = angle["hook"]
  18 | +    hv = cleared[h]["video_id"]
  19 | +
  20 | +    def can(x):
  21 | +        m = cleared[x]
  22 | +        return x != h and x not in doomed and m["video_id"] != hv and \
  23 | +            bool(((m.get("eligibility") or {}).get("clip") or {}).get("ok"))
  24 | +    own = [x for x in angle["moments"] if x in cleared and can(x)]
  25 | +    chans = {cleared[x]["channel_id"] for x in [h, *own]}
  26 | +    first, then = [], []
  27 | +    for x in sorted((x for x in cleared if can(x) and x not in own), key=lambda x: (-cleared[x].get("rank_score", 0), x)):
  28 | +        (then if cleared[x]["channel_id"] in chans else first).append(x)
  29 | +        chans.add(cleared[x]["channel_id"])
  30 | +    return ([h] + own + first + then)[:JOIN_MOMENTS_MAX]
  31 | +
  32 | +
  33 |  def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
  34 |      """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
  35 |      pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
  36 | @@ -3267,12 +3291,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  37 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
  38 |              jt, a_ratings, ext = {}, {}, angle            # RULING 117: this angle's join table; its clips' ratings
  39 |              if candidate is None and angle["hook"] in cleared and angle["hook"] not in doomed:
  40 | -                # the moments that can be in its line-up: its hook, its writer's other moments, then the rest of the
  41 | -                # cleared pool (step A from both vendors, the second pass, CUTTABLE) by rank score; at most 8
  42 | -                own_ = [x for x in angle["moments"] if x != angle["hook"] and x in cleared and x not in doomed]
  43 | -                rest_ = sorted((x for x in cleared if x not in doomed and x != angle["hook"] and x not in own_),
  44 | -                               key=lambda x: (-cleared[x].get("rank_score", 0), x))
  45 | -                jids = ([angle["hook"]] + own_ + rest_)[:JOIN_MOMENTS_MAX]
  46 | +                jids = join_moments(angle, cleared, doomed)  # the moments that CAN be in its line-up
  47 |                  ext = dict(angle, moments=jids)           # the search's angle: the writer's order first
  48 |                  jms = [cleared[x] for x in jids]
  49 |                  jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
  50 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  51 | index b00f780..4366178 100644
  52 | --- a/tests/package/test_medley.py
  53 | +++ b/tests/package/test_medley.py
  54 | @@ -1921,6 +1921,27 @@ class TestRuling117JoinSearch(unittest.TestCase):
  55 |          rig.run()
  56 |          self.assertEqual((len(rig.join_calls[0]), rig.join_calls[0][:3]), (8, ["h", "m0", "m1"]))
  57 |  
  58 | +    def test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first(self):
  59 | +        """The 16:54 replay: never the hook's own video, never a clip-ineligible moment; after the writer's picks, a
  60 | +        moment of a channel not yet in the set comes before a second moment of a channel already in it, whatever their
  61 | +        rank scores."""
  62 | +        ms = [pm("h", "A", 12.0, vid="V1"), pm("x", "B", 14.0), pm("y", "C", 13.0),
  63 | +              pm("a2", "A", 13.0, rank=99.0, vid="V1"),                       # the hook's own video: never
  64 | +              pm("n", "E", 13.0, rank=99.0, clip=False),                      # not clip-eligible: never
  65 | +              pm("b2", "B", 13.0, rank=50.0),                                 # B is in the set already: after...
  66 | +              pm("d", "D", 13.0, rank=1.0),                                   # ...the new channel D
  67 | +              pm("e1", "E", 13.0, rank=90.0), pm("e2", "E", 13.0, rank=80.0)]   # E: its first new, its second not
  68 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins={})
  69 | +        rig.run()
  70 | +        self.assertEqual(rig.join_calls, [["h", "x", "y", "e1", "d", "e2", "b2"]])
  71 | +
  72 | +    def test_the_writers_own_picks_join_the_table_only_when_they_can_stand_beside_the_hook(self):
  73 | +        c = {m["moment_id"]: m for m in [pm("h", "A", 12.0, vid="V1"), pm("w", "A", 13.0, vid="V1"),
  74 | +                                         pm("z", "C", 13.0, clip=False), pm("x", "D", 13.0), pm("q", "E", 13.0)]}
  75 | +        angle = {"hook": "h", "moments": ["h", "w", "z", "x"]}
  76 | +        self.assertEqual(PK.join_moments(angle, c), ["h", "x", "q"])
  77 | +        self.assertEqual(PK.join_moments(angle, c, doomed={"x"}), ["h", "q"])            # a doomed moment: never
  78 | +
  79 |      def test_no_table_or_an_empty_one_is_the_build_as_before(self):
  80 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
  81 |          for joins in (None, {}):
  82 | 
```

---

pp-selectid: RULING 117 (orchestrator 16:24 ET Nov 15), THE JOINS: SEARCH, DO NOT LOOSEN; (2)'s set of moments.
Files: pipeline/package.py (join_moments, NEW; build()'s one call of it), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) BUILD THE JOIN TABLE: for the moments that can be in a line-up for an angle (the hook and the
clips that passed step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle), ask ONCE per ordered
pair ...". The join law does NOT move (one bridge); the full verdicts still decide.

WHY: the landed table (audit 20261115_1632, commit 2d2819c3) filled its 8 moments with the hook, the writer's picks,
then the cleared pool by rank score. Replayed on today's builds 8-12 (commit bb8a842c), zero of 10 angles reached a
line-up: 7 of today's 14 cleared moments are of the hooks' own video (one Simply Bitcoin video), and lineup_ok never
lets two segments share a video, so most of each table was moments that can never stand beside that hook.

THE CHANGE: join_moments(angle, cleared, doomed) -> ids, the hook first. It replaces the inline fill in build() at the
same call site (pipeline/package.py:3294); the table (join_table), the search and the verdicts are unchanged.
- A moment is in the set only when it CAN be in a line-up with this hook under lineup_ok's own rules: not the hook,
  not doomed, NOT of the hook's own video, and clip-eligible (eligibility.clip.ok truthy: lineup_ok's own test).
- Order: the hook; the writer's other moments (the writer's order, the same filter); then the rest of the cleared
  pool by rank score (ties by id), one moment of each channel not yet in the set first, then the others in rank
  order. At most JOIN_MOMENTS_MAX (8).

UNCHANGED GUARDS (not in the diff hunks):
- lineup_ok, pipeline/package.py:1591-1619: every clip clip-eligible (1602-1603); one segment per channel, or
  (repeat_ok, L-y 4's supply exception) one channel twice with every segment its own video (1604-1607).
- search_lineups, pipeline/package.py:2031: the hook is the angle's own hook, always first; every candidate goes
  through lineup_ok (2057) with LY_MAX_BRIDGES (pipeline/package.py:243, = 1); build() passes it
  frozenset(dropped | doomed) (3319, 3403), so a doomed or dropped moment never enters a line-up either way.
- join_table, the join question, JOIN_CACHE, medley() / coherence() and their floors: not touched.

TESTS (test_medley TestRuling117JoinSearch, 15): the build-level fill (a moment of the hook's own video and a
clip-ineligible moment never join; a new channel's first moment comes before a second moment of a channel already in
the set, whatever their rank scores; a new channel's second moment counts as a channel already in the set); the
earlier cap test; join_moments directly (the writer's own picks join only when they can stand beside the hook; a
doomed moment never). All 40 suite files pass. Mutations after a control run: the fill (K1-K9) and J1-J14.

PLEASE CHECK: (1) that the filter removes ONLY moments lineup_ok could never accept beside this hook, so the search
loses no line-up it could have found; (2) that the order is as stated and deterministic; (3) that nothing about the
join law, the table's question, its cache or the verdicts moved; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
