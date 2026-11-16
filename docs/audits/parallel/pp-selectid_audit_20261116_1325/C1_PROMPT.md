# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_1325
# Branch: pp-selectid
# Generated: 2026-11-16 13:25 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_1325/C1_STEP.diff (147 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5ae1e1b..ef1903a 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2017,6 +2017,29 @@ def read_stories(path):
   6 |                       models=d.get("models"), stories=len(out))
   7 |  
   8 |  
   9 | +def in_pool_ids(stories, pool, aliases=None):
  10 | +    """RULING 118 (4), the ids: the stories file names each moment by the LEDGER's id (the receipts session reads the
  11 | +    ledger), and this build's moments carry that id as mined.ledger_moment_id (ledger_build: each moment gets its own
  12 | +    id; a trimmed variant keeps its parent's ledger id). A ledger row the ledger build dropped as the same speech as
  13 | +    another (ledger_build's duplicates_of: its id -> the kept row's id, `aliases`) stands for the kept one. -> the
  14 | +    stories with moment_ids in this build's own ids (every match, in the file's order, each once) and the file's own
  15 | +    ids kept as ledger_ids. Builds 41-57 matched nothing: they compared the two kinds of id directly."""
  16 | +    idx = {}
  17 | +    for mid, m in pool.items():
  18 | +        lid = (m.get("mined") or {}).get("ledger_moment_id")
  19 | +        if lid:
  20 | +            idx.setdefault(lid, []).append(mid)
  21 | +    out = []
  22 | +    for s in stories:
  23 | +        ids = []
  24 | +        for lid in s["moment_ids"]:
  25 | +            for mid in idx.get(lid) or idx.get((aliases or {}).get(lid)) or []:
  26 | +                if mid not in ids:
  27 | +                    ids.append(mid)
  28 | +        out.append(dict(s, moment_ids=ids, ledger_ids=list(s["moment_ids"])))
  29 | +    return out
  30 | +
  31 | +
  32 |  def story_angles(stories, cleared, hooks, k=MAX_ANGLES):
  33 |      """RULING 118 (4), STORY-FIRST LINE-UPS: angles built INSIDE ONE STORY (its hook and every clip from the same story),
  34 |      tried ahead of the angle writer's; every gate unchanged. For each story in the file's order, the best of `hooks`
  35 | @@ -2846,7 +2869,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  36 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  37 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  38 |            join_cache=None,
  39 | -          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None):
  40 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None,
  41 | +          ledger_aliases=None):
  42 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  43 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  44 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  45 | @@ -3137,6 +3161,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  46 |      stories, s_angles, s_writers = [], [], (set(), set())
  47 |      if candidate is None and stories_path:           # RULING 118 (4): STORY-FIRST LINE-UPS, ahead of the angle writer
  48 |          stories, out["stories"] = read_stories(stories_path)
  49 | +        stories = in_pool_ids(stories, cleared, ledger_aliases)   # the file's ledger ids -> this build's ids
  50 | +        out["stories"]["matched"] = [{"story_id": s["story_id"], "ledger_ids": len(s["ledger_ids"]),
  51 | +                                      "cleared": len(s["moment_ids"])} for s in stories]
  52 |          s_angles, out["stories"]["angles"] = story_angles(stories, cleared, passing, max_angles)
  53 |          if s_angles:                                  # law L-x: the grouping models chose the story's moments
  54 |              s_writers = story_writers(router, out["stories"].get("models"))
  55 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  56 | index ed044d9..ec6d16f 100644
  57 | --- a/tests/package/proof_ledger.py
  58 | +++ b/tests/package/proof_ledger.py
  59 | @@ -482,6 +482,7 @@ def main(argv=None):
  60 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
  61 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
  62 |                stories_path=PK.STORIES,                                             # ruling 118 (4): read only
  63 | +              ledger_aliases=inputs.get("duplicates_of") or {},    # its ledger ids: a dropped duplicate -> the kept row
  64 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
  65 |                lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
  66 |                    segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
  67 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  68 | index abf864c..c3c7388 100644
  69 | --- a/tests/package/test_medley.py
  70 | +++ b/tests/package/test_medley.py
  71 | @@ -4473,13 +4473,19 @@ class TestRuling109Channels(unittest.TestCase):
  72 |          self.assertNotIn("ruling_109", out)
  73 |  
  74 |  
  75 | +def ledgered(*ms):
  76 | +    """The pool's moments as ledger_build makes them: each with its own id and the LEDGER's id kept as
  77 | +    mined.ledger_moment_id ("L" + its id here), the id the stories file names (ruling 118 (4))."""
  78 | +    return [dict(m, mined={"ledger_moment_id": "L" + m["moment_id"]}) for m in ms]
  79 | +
  80 | +
  81 |  class TestRuling118StoryFirst(unittest.TestCase):
  82 |      """RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS: an angle source that builds a line-up INSIDE
  83 |      ONE STORY (the hook and every clip from the same story, 3 channels), ahead of the angle writer, every gate unchanged;
  84 |      the receipts session's stories file is read only; no file: the build as before."""
  85 |      GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
  86 | -    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
  87 | -    STORY = [("S-1", "Bitcoin's own story", ["h", "x", "y", "gone"])]
  88 | +    MS = ledgered(pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
  89 | +    STORY = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lgone"])]     # the file names LEDGER ids
  90 |  
  91 |      def file(self, stories, models=GROUP):
  92 |          d = tempfile.mkdtemp()
  93 | @@ -4499,8 +4505,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
  94 |          return rig
  95 |  
  96 |      def test_every_swap_of_a_story_line_up_stays_inside_its_story(self):
  97 | -        ms = self.MS + [pm("w", "F", 13.0, rank=5.0)]                     # in the story, ranked under the pool's z, q
  98 | -        story = [("S-1", "Bitcoin's own story", ["h", "x", "y", "w"])]
  99 | +        ms = self.MS + ledgered(pm("w", "F", 13.0, rank=5.0))             # in the story, ranked under the pool's z, q
 100 | +        story = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lw"])]
 101 |          rig = self.rig(ms, ["h", "x", "y", "z", "q"], story)               # a weak clip: swapped inside the story
 102 |          rig.medleys = [(False, [], {"clip_02": 2}, Rig.LINE)] + [(False, [], None, "none")] * 6
 103 |          out = rig.run()
 104 | @@ -4526,6 +4532,20 @@ class TestRuling118StoryFirst(unittest.TestCase):
 105 |          self.assertNotIn("stories", out)
 106 |          self.assertEqual((rig.medley_calls[0], out["tried"][0]["text"]), (["h", "z", "q"], "W"))   # its own, as judged
 107 |  
 108 | +    def test_the_files_ledger_ids_become_this_builds_ids(self):
 109 | +        """The receipts session names the LEDGER's ids; this build's moments carry them as mined.ledger_moment_id (a
 110 | +        trimmed variant its parent's), and a ledger row dropped as a duplicate of a kept one stands for the kept one.
 111 | +        Builds 41-57 compared the two kinds of id directly and matched nothing."""
 112 | +        pool = {"b1": {"mined": {"ledger_moment_id": "L1"}}, "b1~trim": {"mined": {"ledger_moment_id": "L1"}},
 113 | +                "b2": {"mined": {"ledger_moment_id": "L2"}}, "b4": {}}
 114 | +        st = PK.in_pool_ids([{"story_id": "S", "headline": "h", "moment_ids": ["L3", "Ldup", "L1", "L2"]}], pool,
 115 | +                            {"Ldup": "L2"})
 116 | +        self.assertEqual(st, [{"story_id": "S", "headline": "h", "moment_ids": ["b2", "b1", "b1~trim"],
 117 | +                               "ledger_ids": ["L3", "Ldup", "L1", "L2"]}])
 118 | +        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], [("S-1", "By build ids", ["h", "x", "y"])]).run()
 119 | +        self.assertEqual(out["stories"]["matched"], [{"story_id": "S-1", "ledger_ids": 3, "cleared": 0}])
 120 | +        self.assertTrue(all("story" not in a for a in out["angles"]))          # build ids are not the file's ids
 121 | +
 122 |      def test_the_file_is_read_in_its_writers_shape_or_not_at_all(self):
 123 |          self.assertEqual(PK.read_stories(None), ([], {"path": None, "read": False, "why": "no stories file named"}))
 124 |          st, rec = PK.read_stories("/nonexistent/stories/latest.json")
 125 | @@ -4589,8 +4609,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
 126 |          self.assertEqual(rig.medley_calls[0], mine[0])                                    # judged first, as any line-up
 127 |  
 128 |      def test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it(self):
 129 | -        ms = [pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 130 | -        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["h", "x", "y"])]).run()
 131 | +        ms = ledgered(pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
 132 | +        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["Lh", "Lx", "Ly"])]).run()
 133 |          self.assertEqual(out["angles"][0]["story"], "S-1")
 134 |          mine = [r for r in out["tried"] if r["angle"] == 1]
 135 |          self.assertTrue(mine)
 136 | @@ -4621,8 +4641,8 @@ class TestRuling118StoryFirst(unittest.TestCase):
 137 |          out = self.rig(self.MS, ["h", "x", "y", "z", "q"], None).run()
 138 |          self.assertEqual((out["stories"]["read"], out["stories"]["why"]), (False, "no file"))
 139 |          self.assertTrue(all("story" not in a for a in out["angles"]))
 140 | -        ms = self.MS + [pm("w", "A", 11.0)]
 141 | -        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["h", "w", "x"])]).run()
 142 | +        ms = self.MS + ledgered(pm("w", "A", 11.0))
 143 | +        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["Lh", "Lw", "Lx"])]).run()
 144 |          self.assertTrue(out["stories"]["angles"][0]["why"].startswith("not an angle"))
 145 |          self.assertTrue(all("story" not in a for a in out["angles"]))
 146 |          self.assertNotIn("stories", Rig(self.MS, ["h", "x", "y", "z", "q"], [(False, [], None, "none")] * 4, []).run())
 147 | 
```

---

pp-selectid: A DEFECT IN RULING 118 (4)'S STORY-FIRST SOURCE (live since 1571b7b9, 09:59 ET Nov 16), found at 13:25 ET when
the first 3-channel story appeared. Files: pipeline/package.py (in_pool_ids; build() translates the file's ids;
build()'s new kwarg ledger_aliases), tests/package/proof_ledger.py (passes the ledger build's duplicates_of),
tests/package/test_medley.py.

THE DEFECT: the receipts session's stories file (/home/ultron/pulse_intel/stories/latest.json) names each moment by the
LEDGER's id; this build's moments have their OWN ids (ledger_build.build_inputs: make() gives each re-anchored moment a
new moment_id and keeps the ledger's as mined.ledger_moment_id, pipeline/ledger_build.py:483; a row dropped as the same
speech as a kept row is named in the report's duplicates_of: its ledger id -> the kept row's ledger id,
ledger_build.py:524 and :563). story_angles matched the file's ids against cleared[moment_id] directly: never a match,
so no story angle could ever be built. Seen on build 57's record: the story S-533ed7f7 (3 channels) names ledger ids
533ed7f7..., 917df8e9..., 74f60d1a...: no build moment has them as moment_id; moments[134] carries 533ed7f7 as
mined.ledger_moment_id. The tests had used one id for both.

THE FIX: in_pool_ids(stories, pool, aliases): an index ledger id -> every build id carrying it (mined.ledger_moment_id; a
trimmed variant keeps its parent's), a dropped duplicate's ledger id standing for the kept one (aliases =
duplicates_of); each story's moment_ids become this build's ids (file order, each once), its own kept as ledger_ids.
build() applies it to the stories read, right after read_stories, on `cleared`; the record gains stories.matched (per
story: the file's ids, how many are cleared here). story_angles, story_pool and every gate are unchanged.
proof_ledger passes ledger_aliases=inputs["duplicates_of"] (the report build_inputs returns).

TESTS: in_pool_ids (variants, duplicates, unknown ids, order); every story-first build test now gives its moments
ledger ids distinct from their own and names the ledger ids in the stories file; a file naming build ids matches
nothing. Mutations T1-T3 (no translation; aliases ignored; one build id a ledger id) beside S1-S18, after a control run.

PLEASE CHECK: (1) the mapping (variants, duplicates, ids not in the pool); (2) that nothing else changed; (3) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
