# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0855
# Branch: pp-selectid
# Generated: 2026-11-13 08:53 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0855/C1_STEP.diff (66 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index b849a45..c1d391f 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -507,9 +507,10 @@ it is today's.
   6 |  With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
   7 |  clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
   8 |  introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
   9 | -channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "may only play LAST" is the
  10 | -LAST id of an angle's list or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as
  11 | -the clips allow (aim for {k}); for
  12 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "only the hook or the LAST
  13 | +clip" is the first or the LAST id of an angle's list, never in between; a clip marked "only the LAST clip" is the LAST
  14 | +id or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as the clips allow (aim for
  15 | +{k}); for
  16 |  each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
  17 |  survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
  18 |  "hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
  19 | @@ -913,14 +914,15 @@ def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  20 |  
  21 |  
  22 |  def placement(m):
  23 | -    """RULING 54: a clip's placement limits as the angle proposer is told them, by the line-up's own rules: under
  24 | -    SHORT_CLIP_S it may only play LAST; without hook eligibility and a passed hook onset (G17a) it cannot open."""
  25 | -    lim = []
  26 | +    """RULING 54: a clip's placement limits as the angle proposer is told them, exactly lineup_for's rules. Without hook
  27 | +    eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
  28 | +    short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
  29 | +    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook)."""
  30 | +    opens = bool((m.get("eligibility") or {}).get("hook", {}).get("ok")) and \
  31 | +        (m.get("hook_onset") or {}).get("pass") is True
  32 |      if m["duration_s"] < SHORT_CLIP_S:
  33 | -        lim.append(f"may only play LAST (under {SHORT_CLIP_S:.0f} s)")
  34 | -    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
  35 | -        lim.append("cannot open (never the hook)")
  36 | -    return "".join(f" | {x}" for x in lim)
  37 | +        return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
  38 | +    return "" if opens else " | cannot open (never the hook)"
  39 |  
  40 |  
  41 |  def pool_fill(angle, pool, dropped=frozenset()):
  42 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  43 | index e2a34c8..a3e4c94 100644
  44 | --- a/tests/package/test_medley.py
  45 | +++ b/tests/package/test_medley.py
  46 | @@ -1168,11 +1168,17 @@ class TestProposal1PoolFill(unittest.TestCase):
  47 |          rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
  48 |          rig.run()
  49 |          p = next(p for r, p in rig.prompts if r == "angle_write")
  50 | -        self.assertIn('id=s | C | 6.9 s | may only play LAST (under 8 s) | cannot open (never the hook) | "', p)
  51 | +        self.assertIn('id=s | C | 6.9 s | under 8 s: only the LAST clip | "', p)            # short, cannot open
  52 |          self.assertIn('id=y | D | 13.8 s | cannot open (never the hook) | "', p)
  53 |          self.assertIn('id=z | E | 9.5 s | "', p)                       # no limit, nothing added
  54 | -        self.assertIn('a clip marked "may only play LAST" is the\nLAST id of an angle', p)
  55 | +        self.assertIn('marked "only the hook or the LAST\nclip" is the first or the LAST id', p)
  56 |          self.assertIn('a clip marked "cannot open" is never the hook', p)
  57 | +        short_opener = dict(pm("b", "F", 7.3), hook_onset={"pass": True})   # the 08:46 build's only formable hook
  58 | +        self.assertEqual(PK.placement(short_opener), " | under 8 s: only the hook or the LAST clip")
  59 | +        both = [short_opener] + [dict(m, hook_onset={"pass": True}) for m in (pm("c", "G", 13.9), pm("w", "H", 9.5))] + \
  60 | +            [dict(pm("a", "I", 6.9), hook_onset={"pass": False})]     # 7.3 + 13.9 + 9.5 + 6.9 = 37.6 s
  61 | +        segs = PK.lineup_for(angle(["b", "c", "w", "a"], "b"), {m["moment_id"]: m for m in both}, need_onset=True)
  62 | +        self.assertEqual([m["moment_id"] for m in segs], ["b", "c", "w", "a"])   # lineup_for agrees: a short hook
  63 |  
  64 |      def test_the_build_records_the_pool_fill_and_judges_the_line_up(self):
  65 |          ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
  66 | 
```

---

You are auditing a small corrective diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips).
Your role: a strict reviewer.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- Ruling 54 (committed an hour ago at ebf6ff32) tells the angle proposer each clip's placement limits, so it proposes
  formable angles. lineup_for's rules:
  - the hook needs hook eligibility and a passed hook onset (G17a);
  - a clip under SHORT_CLIP_S (8 s) may play only LAST AMONG THE CLIPS AFTER THE HOOK. In code:
    `[m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]` over the clips after the hook, and
    lineup_ok's `clips[:-1]` with `clips = segs[1:]`.
  So a short clip MAY be the hook.
- THE DEFECT (measured at 08:46 ET, ledger_20261113_134638): the committed placement() marked every short clip "may
  only play LAST". The only formable line-up of that build opened on a 7.26 s clip (Bitcoin Mechanic): 7.26 + 13.94 +
  9.46 + 6.93 = 37.59 s, the short 6.93 s clip last. Told that the opener "may only play LAST", the writer returned no
  angle, which check_angles refuses ("no readable angles"). The limits did not match lineup_for's rules, which ruling 54
  requires.

The change (pipeline/package.py, tests/package/test_medley.py):
1. placement(m) states exactly lineup_for's rules:
   - under 8 s and able to open: "under 8 s: only the hook or the LAST clip";
   - under 8 s and not able to open: "under 8 s: only the LAST clip";
   - 8 s or more and not able to open: "cannot open (never the hook)";
   - otherwise nothing.
2. The angle prompt's PLACEMENT LIMITS sentence names the three markings and what each allows.
3. tests:
   - the limits for each case;
   - the 08:46 shape: lineup_for itself accepts the 7.3 s hook with the short clip last, and placement() says
     "only the hook or the LAST clip" for it.
- test_medley 90 OK; every other suite OK.

Check: that the three markings are exactly the rules lineup_for and lineup_ok apply (in particular the hook exception
of the short-clip rule), that nothing else changed, and the prompt sentence.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

