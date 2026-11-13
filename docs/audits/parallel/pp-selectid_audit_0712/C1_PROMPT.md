# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0712
# Branch: pp-selectid
# Generated: 2026-11-13 07:11 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0712/C1_STEP.diff (197 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 4263680..c6f3ed8 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -80,11 +80,14 @@ SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE de
   6 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   7 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   8 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
   9 | -TRIM_SCORER_PENDING = False        # ruling 33 (b): the render's clip scorer must affirm every trimmed segment; it runs on
  10 | -                                   # GPU0, which the pin stage may not use. False (the default): the pin stage judges a
  11 | -                                   # trimmed segment as the render does with no scorer, so it fails closed and is never
  12 | -                                   # sealed. True ONLY on the orchestrator's explicit yes: it is sealed with the verdict
  13 | -                                   # pending at the render, stated in the sealed row (audit 0530: the reviewers split on L-m)
  14 | +TRIM_SCORER_PENDING = True         # ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the
  15 | +                                   # pin stage may not use) must affirm every trimmed segment. RULING 49 (07:02 Nov 13):
  16 | +                                   # YES, a trimmed clip is sealed with that verdict PENDING AT THE RENDER (stage_validate
  17 | +                                   # runs before any render; a refusal there costs no GPU), stated in the sealed row and
  18 | +                                   # per clip in the pin (scorer_pending: true). False: the render's check with no scorer
  19 | +TRIMMED_PER_LINEUP_MAX = 1         # ruling 49 (b): at most ONE trimmed clip per line-up until the first trimmed clip has
  20 | +                                   # been affirmed at validate once (the integrator says when): one refusal cannot sink a
  21 | +                                   # line-up twice. package_pin.TRIMMED_PER_PIN_MAX holds the pin to the same number
  22 |  SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
  23 |                                     # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
  24 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  25 | @@ -306,8 +309,9 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  26 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  27 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  28 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  29 | -                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  30 | -                           if m.get("trimmed_leading") else {})}                      # ruling 33 part 2, sealed
  31 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"],
  32 | +                            "scorer_pending": True}                     # ruling 49 (a): the clip scorer's verdict on
  33 | +                           if m.get("trimmed_leading") else {})}       # the trimmed text is pending at the render
  34 |                         for lb, m in zip(labels(len(segs)), segs)],
  35 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  36 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  37 | @@ -736,6 +740,8 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  38 |          return False, "one segment per channel"
  39 |      if sum("price_prediction" in m.get("risk", []) for m in segs) > PRICE_PREDICTIONS_MAX:
  40 |          return False, "price predictions"
  41 | +    if sum(bool(m.get("trimmed_leading")) for m in segs) > TRIMMED_PER_LINEUP_MAX:
  42 | +        return False, f"more than {TRIMMED_PER_LINEUP_MAX} trimmed clip (ruling 49 b)"
  43 |      if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  44 |          return False, "a short clip that is not last"
  45 |      dur = sum(m["duration_s"] for m in segs)
  46 | @@ -822,6 +828,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  47 |                      continue
  48 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
  49 |                      continue
  50 | +                if sum(bool(m.get("trimmed_leading")) for m in (h, *combo)) > TRIMMED_PER_LINEUP_MAX:   # ruling 49 b
  51 | +                    continue
  52 |                  order = sorted(combo, key=lambda m: pos[m["moment_id"]])
  53 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
  54 |                      continue
  55 | @@ -1405,6 +1413,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  56 |                  cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
  57 |                  if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
  58 |                          sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
  59 | +                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
  60 |                          not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
  61 |                      continue
  62 |                  order, added = cand, mid
  63 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  64 | index c8a76d3..f860174 100644
  65 | --- a/pipeline/package_pin.py
  66 | +++ b/pipeline/package_pin.py
  67 | @@ -67,8 +67,9 @@ def recency_problems(segments):
  68 |  
  69 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
  70 |                  "speaker",                                 # the 00:05 ET Nov 13 order, item 3
  71 | -                "trimmed_leading", "untrimmed_start")      # ruling 33 part 2 (render merged 11e361cc): only when a word
  72 | -                                                           # is trimmed, so every other pin seals as before
  73 | +                "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
  74 | +                "scorer_pending")                          # is trimmed, so every other pin seals as before (ruling 49 a)
  75 | +TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX
  76 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
  77 |  
  78 |  
  79 | @@ -99,13 +100,24 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
  80 |  def trim_problems(segments):
  81 |      """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
  82 |      refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
  83 | -    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start."""
  84 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49: (a) every trimmed clip says
  85 | +    scorer_pending: true (the clip scorer's verdict is pending at the render) and no other clip carries the key;
  86 | +    (b) at most TRIMMED_PER_PIN_MAX trimmed clips."""
  87 |      import canon
  88 |      out = []
  89 | +    n = sum("trimmed_leading" in s or "untrimmed_start" in s for s in segments)
  90 | +    if n > TRIMMED_PER_PIN_MAX:
  91 | +        out.append(f"{n} trimmed clips: at most {TRIMMED_PER_PIN_MAX} until the first is affirmed at validate "
  92 | +                   f"(ruling 49 b)")
  93 |      for i, s in enumerate(segments):
  94 |          has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
  95 |          if not has_w and not has_s:
  96 | +            if "scorer_pending" in s:
  97 | +                out.append(f"segment {i}: scorer_pending belongs to a trimmed clip only (ruling 49 a)")
  98 |              continue
  99 | +        if s.get("scorer_pending") is not True:
 100 | +            out.append(f"segment {i}: a trimmed clip must say scorer_pending: true (ruling 49 a: the clip scorer's "
 101 | +                       f"verdict on the trimmed text is pending at the render)")
 102 |          if has_w != has_s:
 103 |              out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 104 |              continue
 105 | @@ -226,7 +238,7 @@ def to_pin(pk, run_name):
 106 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 107 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 108 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 109 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start") if k in s},   # ruling 33 part 2
 110 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_pending") if k in s},
 111 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 112 |      edl_vo = {"intro": pk["vo"]["intro"],
 113 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 114 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 115 | index a8d3d92..c68fcc1 100644
 116 | --- a/tests/package/test_medley.py
 117 | +++ b/tests/package/test_medley.py
 118 | @@ -810,24 +810,38 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 119 |          m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
 120 |          self.assertIsNone(PK.trim_variant(m, srcs))
 121 |  
 122 | -    def test_strict_by_default_and_pending_at_the_render_only_on_the_switch(self):
 123 | +    def test_pending_at_the_render_by_ruling_49_and_strict_on_the_switch(self):
 124 |          m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 125 |          v = PK.trim_variant(m, srcs)
 126 |          line = [{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}]
 127 | -        self.assertFalse(PK.TRIM_SCORER_PENDING)                      # the default: the render's check, no scorer
 128 | +        self.assertTrue(PK.TRIM_SCORER_PENDING)                       # ruling 49 (07:02): YES
 129 |          r = PK.stand_alone_check(line)
 130 | -        self.assertFalse(r["ok"])                                     # a trimmed segment fails closed, never sealed
 131 | -        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 132 | -        self.assertEqual(r["scorer_pending"], [])
 133 | +        self.assertTrue(r["ok"], r["rows"])
 134 | +        self.assertEqual(r["scorer_pending"], ["clip_01"])
 135 | +        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 136 |          saved = PK.TRIM_SCORER_PENDING
 137 | -        try:                                                          # the orchestrator's explicit yes only
 138 | -            PK.TRIM_SCORER_PENDING = True
 139 | +        try:                                                          # the strict switch: the render's check with
 140 | +            PK.TRIM_SCORER_PENDING = False                            # no scorer fails closed, never sealed
 141 |              r = PK.stand_alone_check(line)
 142 |          finally:
 143 |              PK.TRIM_SCORER_PENDING = saved
 144 | -        self.assertTrue(r["ok"], r["rows"])
 145 | -        self.assertEqual(r["scorer_pending"], ["clip_01"])
 146 | -        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 147 | +        self.assertFalse(r["ok"])
 148 | +        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 149 | +        self.assertEqual(r["scorer_pending"], [])
 150 | +
 151 | +    def test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin(self):
 152 | +        self.assertEqual(PK.TRIMMED_PER_LINEUP_MAX, package_pin.TRIMMED_PER_PIN_MAX)
 153 | +        ms = [dict(pm("h", "A", 12.0)), dict(pm("x", "B", 14.0), trimmed_leading="But", untrimmed_start=0.0),
 154 | +              dict(pm("y", "C", 13.0), trimmed_leading="So", untrimmed_start=0.0), dict(pm("z", "D", 13.0))]
 155 | +        for m in ms:
 156 | +            m["hook_onset"] = {"pass": True}
 157 | +        by = {m["moment_id"]: m for m in ms}
 158 | +        self.assertEqual(PK.lineup_ok([by["h"], by["x"], by["y"]])[1], "more than 1 trimmed clip (ruling 49 b)")
 159 | +        segs = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by, need_onset=True)
 160 | +        self.assertEqual(sum(bool(m.get("trimmed_leading")) for m in segs), 1, [m["moment_id"] for m in segs])
 161 | +        two = [{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True},
 162 | +               {"trimmed_leading": "So", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True}]
 163 | +        self.assertIn("2 trimmed clips", package_pin.trim_problems(two)[0])
 164 |  
 165 |      def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 166 |          segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 167 | @@ -843,19 +857,27 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 168 |          pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 169 |          pin = package_pin.to_pin(spk(pk), "test")
 170 |          s1 = pin["segments"][1]
 171 | -        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 172 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"], s1["scorer_pending"]), ("But", 0.0, True))
 173 |          self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 174 | +        self.assertNotIn("scorer_pending", pin["segments"][0])                    # ruling 49 (a): per trimmed clip
 175 |          mp = pin["moments_package"]
 176 |          args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 177 |          self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 178 |          other = [dict(x) for x in pin["segments"]]
 179 |          other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 180 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 181 | -        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0}):
 182 | +        other[1]["trimmed_leading"], other[1]["scorer_pending"] = "But", False      # and so is scorer_pending
 183 | +        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 184 | +        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
 185 | +                    {"scorer_pending": False}):                                       # ruling 49 (a) in plain words
 186 |              p = spk(pk)
 187 |              p["segments"][1] = dict(p["segments"][1], **bad)
 188 |              with self.assertRaises(package_pin.PinRefused):
 189 |                  package_pin.to_pin(p, "test")
 190 | +        p = spk(pk)
 191 | +        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # only on a trimmed clip
 192 | +        with self.assertRaises(package_pin.PinRefused):
 193 | +            package_pin.to_pin(p, "test")
 194 |          self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
 195 |          p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
 196 |          p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 197 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips); the integrator renders them. Your role: a
strict reviewer of how TRIMMED clips are sealed.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- Ruling 33 part 2 lets a clip that opens on ONE of but/and/so/well/now/yeah be cut one word in, when (a) the cut opens
  in quiet (measured at the pin stage as the render measures it), (b) the render's STAND_ALONE clip scorer affirms the
  trimmed clip, and (c) step A is re-judged on the trimmed span.
- The render's clip scorer is gemma3:27b through Ollama on Ultron's GPU0 (run_fresh.stage_validate ->
  story_semantics.LocalLLM). The pin-stage builder may not use any GPU. Until now the builder kept (b) STRICT
  (TRIM_SCORER_PENDING = False): a trimmed segment failed the pin stage's STAND_ALONE, so it was never in a line-up.
- A pin's per-segment keys are sealed in package_sha256 (package_pin.seal). SEALED_LATER keys enter the seal only
  when the segment carries them, so older pins recompute their seal unchanged. The integrator's check_pin_only
  imports this branch's package_pin.py. The render's pinned.validate_schema checks named keys and ignores unknown ones.

The order this diff implements (ORCHESTRATOR RULING 49, 07:02 ET Nov 13, verbatim): "ITEM 42, YES: a trimmed clip may be
sealed with the clip scorer's verdict pending at the render, because stage_validate runs before any render and a
refusal there costs no GPU. Two conditions: (a) the pin says so in plain words (scorer_pending: true per trimmed clip);
(b) a line-up carries at most ONE trimmed clip until the first trimmed clip has been affirmed at validate once, so one
refusal cannot sink a line-up twice. If you can call the same scorer with the same prompt and model at the pin stage
inside budget, do that instead and seal its verdict: say which you did."
- Which we did: pending at the render. The same scorer (gemma3:27b, Ollama, GPU0) cannot run at the pin stage, and no
  other box this builder may use serves that model.

The change:
1. pipeline/package.py:
   - TRIM_SCORER_PENDING = True. stand_alone_check then judges a trimmed segment on its trimmed text with no lock
     marker, and records the trimmed labels in scorer_pending; the sealed STAND_ALONE row says "PENDING AT THE RENDER"
     (both unchanged code).
   - TRIMMED_PER_LINEUP_MAX = 1, enforced in lineup_for (its inline rules), lineup_ok (used by ruling 41's swap and
     item 44's swap), and the no-voice path's added clip.
   - The package's trimmed segment rows carry "scorer_pending": True next to trimmed_leading / untrimmed_start.
2. pipeline/package_pin.py:
   - SEALED_LATER gains "scorer_pending" (sealed only when present).
   - TRIMMED_PER_PIN_MAX = 1.
   - to_pin copies scorer_pending.
   - trim_problems refuses: a trimmed segment without scorer_pending: true; scorer_pending on an untrimmed segment;
     more than TRIMMED_PER_PIN_MAX trimmed segments.
3. tests/package/test_medley.py:
   - The default is now pending, and the strict switch still fails closed.
   - One trimmed clip per line-up: lineup_ok refuses two; lineup_for never picks two; the pin refuses two; the two
     constants are equal.
   - The pin seals scorer_pending: true on the trimmed clip only, and it is inside the seal. Refused: scorer_pending
     false, and scorer_pending on an untrimmed clip.
- test_medley 81 OK; every other suite OK.

Check in particular:
- that a trimmed clip can never be sealed WITHOUT "scorer_pending": true in plain words, and that no clip says pending
  when it is not trimmed;
- that no line-up or pin can carry two trimmed clips, through every path that builds or changes a line-up (lineup_for,
  ruling 41's swap, item 44's swap, the no-voice added clip);
- that pins without a trimmed clip seal exactly as before (the SEALED_LATER contract);
- that nothing claims the scorer affirmed anything.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

