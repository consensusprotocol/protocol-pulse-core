# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1112
# Branch: pp-selectid
# Generated: 2026-11-14 11:12 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1112/C1_STEP.diff (157 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 71411d3..88a255b 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -43,10 +43,12 @@ import sentence_law as SL
   6 |  import transcript_store as ts
   7 |  import vo_fidelity as VF          # snap_risk's price mentions (pure Python; at module level: audit 0332 C2, grok + qwen)
   8 |  
   9 | -SNAP_MAX_S = 20.0         # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  10 | +SNAP_MAX_S = 35.0         # THE ORCHESTRATOR'S 10:48 RULING (2), Nov 14: the read's snap ceiling is the spotlight's 35 s
  11 | +                          # (spotlight.SPOT_S[1]); the medley's own 20 s stays in package.usable (SEG_MAX_S, L-u).
  12 | +                          # Before it, 20 s here dropped rows of 21-23 s before the spotlight's ceiling could apply.
  13 | +                          # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  14 |                            # is SNAPPED OUTWARD to the word record's whole sentences, instead of dropped, when the
  15 | -                          # snapped span stays inside the clip length limit (= package.SEG_MAX_S, L-u) and shows no
  16 | -                          # speaker change. The added words are the speaker's own, so nothing is changed by omission;
  17 | +                          # snapped span stays inside this ceiling and shows no speaker change. The added words are the speaker's own, so nothing is changed by omission;
  18 |                            # the snapped span is judged as usual: step A (L-s), the exclusion verdict (every L-u risk),
  19 |                            # L-v 2 (every number and negation both ways, exactly one speaker measured) and usable() (time
  20 |                            # words). It replaces SNAP_WORDS = 3 and SNAP_GUARD (audit 2315 C1), whose concern was words
  21 | @@ -402,7 +404,8 @@ def reanchor(row, src, cap=None):
  22 |          if a is None or b is None:
  23 |              return None, f"{snap}, its length is not measured (a word time is missing)"
  24 |          if b - a > SNAP_MAX_S:
  25 | -            return None, f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32: the clip length limit)"
  26 | +            return None, (f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32 with the 10:48 ruling (2): "
  27 | +                          f"the spotlight's clip ceiling)")
  28 |          t = marker_inside(cap if cap is not None else getattr(src, "context_source", None), a, b)
  29 |          if t is not None:
  30 |              return None, f"{snap} it holds a caption speaker marker at {t:.2f} s: a measured speaker change (ruling 32)"
  31 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
  32 | index d0bb83c..65efb05 100644
  33 | --- a/pipeline/vo_fidelity.py
  34 | +++ b/pipeline/vo_fidelity.py
  35 | @@ -414,6 +414,21 @@ def time_words(text, meta=()):
  36 |      return out
  37 |  
  38 |  
  39 | +def without_manifest_date(text, manifest=None):
  40 | +    """THE ORCHESTRATOR'S 10:48 RULING (3), Nov 14: NUMBER accepts the manifest's OWN show date as production metadata,
  41 | +    the WHOLE date only ('2026-11-12', 'November 12', 'Nov 12'; a written date may carry its ordinal, 'November 12th',
  42 | +    and the manifest's own year, 'November 12, 2026'), never a bare number, and only when it equals the manifest's date.
  43 | +    -> the text with each such date taken out; everything else is read as before. No manifest date: the text as it is."""
  44 | +    from datetime import date
  45 | +    try:
  46 | +        d = date.fromisoformat(str((manifest or {}).get("date") or ""))
  47 | +    except ValueError:
  48 | +        return text or ""
  49 | +    month = rf"(?:{d.strftime('%B')}|{d.strftime('%b')})"        # 'Nov.' is not one: its period ends a sentence
  50 | +    written = rf"\b{month}\s+0?{d.day}(?:st|nd|rd|th)?(?:,?\s+{d.year})?(?![\w.]?\d)"
  51 | +    return re.sub(rf"(?<![\w-]){re.escape(d.isoformat())}(?![\w-])|{written}", " ", text or "", flags=re.I)
  52 | +
  53 | +
  54 |  def fact_numbers(text, meta_nums=frozenset()):
  55 |      """The numbers of a text that state a fact, [(value, unit)]: leaves out the package's own count beside a production
  56 |      noun ('three voices') and 'one' written as a word (a determiner or pronoun: 'one thing', 'one of')."""
  57 | @@ -454,7 +469,8 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
  58 |          names = names_of(text, meta)
  59 |          quotes = [q for pair in _QUOTE.findall(text) for q in pair if q]
  60 |          times = time_words(text, meta)
  61 | -        if (fact_numbers(text, meta_nums) or names or quotes or atts or times) and not cited:
  62 | +        if (fact_numbers(without_manifest_date(text, manifest), meta_nums) or names or quotes or atts or times) \
  63 | +                and not cited:                                       # the 10:48 ruling (3): the show date needs none
  64 |              V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
  65 |          pools = []                                                   # per attribution: the governing segments
  66 |          for subj0, form, _ in atts:
  67 | @@ -499,7 +515,7 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
  68 |          for chunk, ai in _governed(text, atts):
  69 |              gov = pools[ai] if ai is not None and pools[ai] else cited
  70 |              gpool = [t for c in gov for t in seg_toks[c]]
  71 | -            for val, unit in fact_numbers(chunk, meta_nums):
  72 | +            for val, unit in fact_numbers(without_manifest_date(chunk, manifest), meta_nums):   # 10:48 ruling (3)
  73 |                  if not _has_number(gpool, val, unit):
  74 |                      V("NUMBER", f"{val}{' ' + unit if unit else ''} is not in the cited sentences" +
  75 |                        (" of the attributed speaker / show" if ai is not None and pools[ai] else ""))
  76 | @@ -610,7 +626,7 @@ def strict_features(words, segments, manifest=None, production=False):
  77 |      word, 'as X put it'. -> [feature, ...] (empty: the words may be commentary)."""
  78 |      meta, meta_nums = manifest_terms(segments, manifest)
  79 |      out = []
  80 | -    if fact_numbers(words, meta_nums):
  81 | +    if fact_numbers(without_manifest_date(words, manifest), meta_nums):     # the 10:48 ruling (3): the show date
  82 |          out.append("a number")
  83 |      if names_of(words, meta):
  84 |          out.append(f"a name ({', '.join(names_of(words, meta)[:3])})")
  85 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
  86 | index c0a2d96..cbe3582 100644
  87 | --- a/tests/package/test_gates.py
  88 | +++ b/tests/package/test_gates.py
  89 | @@ -300,6 +300,29 @@ class TestDeterministicRules(unittest.TestCase):
  90 |          self.assertIn("IMPERATIVE", self.rules("It's time to buy.", ["m1"]))
  91 |          self.assertEqual(self.rules("Short-term holders are selling.", ["m1"]), set())
  92 |  
  93 | +    def test_number_takes_the_manifests_own_show_date_whole_and_nothing_else(self):
  94 | +        """The orchestrator's 10:48 ruling (3), Nov 14: NUMBER accepts the manifest's own show date as production
  95 | +        metadata, the WHOLE date only, never a bare number, and only when it equals the manifest's date."""
  96 | +        man = {"date": "2026-11-12", "show": "Pulse Check", "channels": ["Coin Bureau"]}
  97 | +
  98 | +        def rules(text, m=man):
  99 | +            return {v["rule"] for v in VF.check_deterministic(self.SEGS, [{"slot": "signoff", "text": text,
 100 | +                                                                           "cites": []}], m)["violations"]}
 101 | +        for ok in ("Pulse Check for 2026-11-12.", "Pulse Check for November 12.", "Pulse Check, Nov 12.",
 102 | +                   "Pulse Check for November 12, 2026.", "That's Pulse Check, november 12th."):
 103 | +            self.assertEqual(rules(ok), set(), ok)                 # no NUMBER, and no NEEDS_SOURCE for it either
 104 | +        for bad in ("Pulse Check for 2026-11-13.", "Pulse Check for November 13.", "Pulse Check number 12.",
 105 | +                    "Pulse Check for 12.", "Pulse Check for November 12, 2025.", "Pulse Check for 2026-11-120.",
 106 | +                    "Pulse Check, Nov. 12."):                      # (the abbreviation's period ends a sentence)
 107 | +            self.assertIn("NUMBER", rules(bad), bad)
 108 | +            self.assertIn("NEEDS_SOURCE", rules(bad), bad)
 109 | +        self.assertIn("NUMBER", rules("Pulse Check for 2026-11-12.", {"show": "Pulse Check"}))   # no date: as before
 110 | +        v = VF.check_deterministic(self.SEGS, [{"slot": "x", "text": "We stopped at November 120.", "cites": []}], man)
 111 | +        self.assertEqual([x["detail"].split()[0] for x in v["violations"] if x["rule"] == "NUMBER"], ["120"])
 112 | +        self.assertEqual(VF.strict_features("Pulse Check for 2026-11-12", self.SEGS, man, production=True), [])
 113 | +        self.assertEqual(VF.strict_features("Pulse Check for 2026-11-13", self.SEGS, man, production=True),
 114 | +                         ["a number"])                      # the verdict layer's production claim reads it the same
 115 | +
 116 |      def test_price_now_reads_history_forecasts_and_counts(self):
 117 |          self.assertIn("PRICE_NOW", self.rules("Bitcoin just set an all-time high at $126,000.", ["m1"], [73000.0]))
 118 |          self.assertIn("PRICE_NOW", self.rules("Since 2022, Bitcoin is at $126,000.", ["m1"], [73000.0]))
 119 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 120 | index 3c96174..2f4a7a3 100644
 121 | --- a/tests/package/test_ledger_build.py
 122 | +++ b/tests/package/test_ledger_build.py
 123 | @@ -82,18 +82,28 @@ class TestReanchor(unittest.TestCase):
 124 |              sp, info = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 125 |              self.assertEqual(info["added"]["before"], word)
 126 |  
 127 | -    def test_the_snap_limit_is_the_packagers_clip_limit(self):                 # audit 0332 C1, qwen P2-1
 128 | +    def test_the_snap_ceiling_is_the_spotlights_and_the_medley_keeps_its_own_20_s(self):
 129 | +        """The orchestrator's 10:48 ruling (2), Nov 14: the read's snap ceiling is 35 s (spotlight.SPOT_S[1]); the
 130 | +        medley's own 20 s stays in package.usable (SEG_MAX_S)."""
 131 |          import package as PK
 132 | -        self.assertEqual(LB.SNAP_MAX_S, PK.SEG_MAX_S)
 133 | +        import spotlight as SPOT
 134 | +        self.assertEqual((LB.SNAP_MAX_S, SPOT.SPOT_S[1], PK.SEG_MAX_S), (35.0, 35.0, 20.0))
 135 |  
 136 | -    def test_a_snap_longer_than_20_s_stays_out(self):
 137 | -        long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."             # 75 words, 0.3 s each
 138 | +    def test_a_snap_of_21_to_35_s_is_read_and_one_longer_than_35_s_stays_out(self):
 139 | +        mid = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."              # 75 words: 22.5 s
 140 | +        src = source([mid, "That is the plan."])
 141 | +        a, b = src.sentences[0]
 142 | +        self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], 20.0)
 143 | +        sp, info = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 144 | +        self.assertIsNotNone(sp)                                      # read now (the medley's usable() drops it)
 145 | +        self.assertEqual(info["snapped_words"][0], 65)
 146 | +        long_ = "Bitcoin " + " ".join(["keeps"] * 122) + " settling payments."           # 125 words: 37.5 s
 147 |          src = source([long_, "That is the plan."])
 148 |          a, b = src.sentences[0]
 149 |          self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], LB.SNAP_MAX_S)
 150 |          sp, why = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 151 |          self.assertIsNone(sp)
 152 | -        self.assertIn("> 20 s (ruling 32", why)
 153 | +        self.assertIn("> 35 s (ruling 32 with the 10:48 ruling (2)", why)
 154 |          sp, info = LB.reanchor(row(long_), src)                       # whole sentences: no snap, usable() measures it
 155 |          self.assertEqual(info["snapped_words"], [0, 0])
 156 |  
 157 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
input that breaks it.

BACKGROUND (static):
- The builder reads a miner's ledger of candidate moments (pipeline/ledger_build.py). A row whose anchored text is not
  whole sentences is SNAPPED OUTWARD to the word record's whole sentences (ruling 32), when the snapped span stays
  inside a ceiling and holds no caption speaker marker; otherwise the row is dropped. Two products use the moments: the
  MEDLEY (hook + 2-4 clips; at most 20 s per source video, law L-u) and the SPOTLIGHT (one moment of 12-35 s, ruling 90).
- pipeline/vo_fidelity.py judges every VO line, the title and the caption. Its deterministic layer includes NUMBER
  (every number in a line is in the sentences it cites) and NEEDS_SOURCE (a line with a fact - a number, name, quote,
  attribution or time word - cites at least one segment). Production metadata (the credited shows, the show, the
  date's month and weekday names, the package's own counts) may be stated without a citation. The model-verdict layer
  labels each claim; a "production" claim must cite the manifest and carry no strict feature (strict_features: "a
  number", a name, ...).

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- package.usable(moments, ctx, ..., seg_max=SEG_MAX_S) (package.py:162) drops a moment longer than seg_max; SEG_MAX_S
  = 20.0 (package.py:67) is the medley's default. The spotlight calls usable(..., seg_max=SPOT_S[1]) (spotlight.py:196,
  :217) with SPOT_S = (12.0, 35.0) (spotlight.py:53). So the medley keeps its own 20 s whatever the read lets in.
- vo_fidelity._governed(text, atts) (:352) splits a line into chunks at sentence ends (and attributions); the NUMBER
  check reads each chunk. NEEDS_SOURCE reads the whole line.
- vo_fidelity.manifest_terms (:276) admits the show date's month / weekday NAMES as production metadata, not its digits.
- vo_fidelity.check (:740) ALWAYS asks the model verdict, whatever the deterministic layer found; the deterministic
  layer is code, so a change to it applies at scoring time without new model calls.

THE ORCHESTRATOR'S RULINGS (10:48 ET Nov 14), verbatim:
"(2) YES: the ledger read's snap ceiling is 35 s; the medley's own 20 s stays in package.usable.
 (3) YES: vo_fidelity's NUMBER rule accepts the manifest's own show date as production metadata, the WHOLE date only
 ('2026-11-12', 'November 12', 'Nov 12'), never a bare number, and only when it equals the manifest's date. pp-tests
 keeps its 30 cases."
Context: before (2), the read dropped rows whose snap ran 21-23 s before the spotlight's 35 s ceiling could apply.
Before (3), "Pulse Check for 2026-11-12." (the manifest's own date) failed NUMBER in 16 of pp-tests' 40 must-pass VO
cases, and gave 14 must-fail cases a rejection for the wrong reason.

THE CHANGE (the diff follows):
1. ledger_build.SNAP_MAX_S 20.0 -> 35.0 (= spotlight.SPOT_S[1]); its comment and the drop reason say so. Tests: the
   ceiling equals the spotlight's while the medley's SEG_MAX_S stays 20; a 22.5 s snap is now read; a 37.5 s one stays
   out.
2. vo_fidelity.without_manifest_date(text, manifest): takes out of a text the manifest's OWN date, whole: ISO
   ('2026-11-12'), or written ('November 12' / 'Nov 12', an optional ordinal 'th', an optional ', 2026' of the
   manifest's year), case-insensitive, never followed by another digit; no manifest date: the text as it is. 'Nov.' is
   NOT accepted (its period ends a sentence in _governed, so the day would be read alone). It is applied at the three
   places a number is read for this purpose: the NUMBER loop (each chunk), NEEDS_SOURCE (the whole line) and
   strict_features (a production claim's words). Tests: the five accepted forms give NO violation; a different day, a
   bare '12', 'number 12', a different year, '2026-11-120' and 'Nov. 12' are still NUMBER and NEEDS_SOURCE; no manifest
   date: as before; strict_features agrees; a longer number keeps its whole value ('120'). 9 mutations, each killed;
   20 suites, 570 tests.

ATTACK:
(a) Ruling (2): can a moment of 21-35 s now reach a MEDLEY? Does anything between the read and package.usable assume
    20 s (a cut, a hook rule, the clip scorer, the candidate registry)? Can a snap now cross a speaker change?
(b) Ruling (3): can any number OTHER than the manifest's own whole date escape NUMBER or NEEDS_SOURCE (a price, a count,
    a day alone, another date, a date inside a larger number, a date in a quote)? Is 'November 12, 2025' handled? A
    malformed or missing manifest date? Can the change make a must-fail case pass by construction?
(c) Anything else that could seal a wrong pin or score the exam wrongly.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete input), then
"SHIP: yes / no / yes with conditions".

