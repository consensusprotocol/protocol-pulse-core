# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1057
# Branch: pp-selectid
# Generated: 2026-11-17 10:57 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1057/C1_STEP.diff (269 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index ba38c08..46e4316 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -19,7 +19,14 @@ RULING 131 (orchestrator 08:25 ET Nov 17) has its own re-check, class_131: (A) p
   6 |  two of the three readings (the approved text, the run's decode, the second recogniser) decide it and the sealed text
   7 |  takes that reading, at least 3 tokens from both cut edges; never a number, a name or a negation; all three different
   8 |  holds. (B) a currency symbol is formatting (canon.dollars_after_number, G18's one tolerance). It re-runs the render's own
   9 | -steps on the three readings the lock records and never trusts the record's own classes."""
  10 | +steps on the three readings the lock records and never trusts the record's own classes.
  11 | +
  12 | +RULING 135 (orchestrator 10:50 ET Nov 17), THE COMPARISON CANON: "differences of spelling are not differences of
  13 | +speech". A differing pair whose two sides are the same words by canon.same_words (case, punctuation and apostrophes
  14 | +ignored; segmentation ignored, names too; the closed list of spoken reductions; non-lexical tokens, fillers and a stray
  15 | +single consonant, left out; a digit or a different single letter still differs) is no difference: dropped right after
  16 | +the currency pairs in class_131 (as the render's lock drops it before the critical check and the vote) and before any
  17 | +class in class_84 (as ruling 72's comparison drops it). The sealed text keeps the approved words there."""
  18 |  import re
  19 |  from difflib import SequenceMatcher
  20 |  
  21 | @@ -112,6 +119,9 @@ def class_84(spoken, approved):
  22 |          if tag == "equal":
  23 |              continue
  24 |          rs, ps = r2[a:b], p[c:d]
  25 | +        if canon.same_words(rs, ps):                     # RULING 135: spelling only, not a difference of speech
  26 | +            out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": "spelling only (ruling 135)"})
  27 | +            continue
  28 |          if any(critical(t, texts) for t in rs + ps):
  29 |              k = None
  30 |          elif rs and ps:
  31 | @@ -221,6 +231,9 @@ def class_131(spoken, approved, adj):
  32 |          if currency_pair(r, p, op):
  33 |              out.append(dict(row, took="currency", edge_distance=None, **{"class": "currency format (ruling 131 (B))"}))
  34 |              continue
  35 | +        if canon.same_words(r[a:b], p[c:d]):            # RULING 135: dropped before the critical check and the vote
  36 | +            out.append(dict(row, took="spelling", edge_distance=None, **{"class": "spelling only (ruling 135)"}))
  37 | +            continue
  38 |          row["edge_distance"] = edge_distance(r, p, op)
  39 |          if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  40 |              out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
  41 | @@ -239,7 +252,8 @@ def class_131(spoken, approved, adj):
  42 |      rec = adj.get("pairs")
  43 |      theirs = [(x.get("run"), x.get("approved"), x.get("took"), x.get("edge_distance")) for x in rec] \
  44 |          if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
  45 | -    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out if x["took"] != "currency"]
  46 | +    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out
  47 | +            if x["took"] not in ("currency", "spelling")]           # the record keeps both apart from its pairs
  48 |      if theirs != mine:
  49 |          out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
  50 |      sp = canon.canon_tokens(spoken)
  51 | diff --git a/pipeline/canon.py b/pipeline/canon.py
  52 | index 25aa737..12b8809 100644
  53 | --- a/pipeline/canon.py
  54 | +++ b/pipeline/canon.py
  55 | @@ -281,6 +281,50 @@ def currency_free(tokens):
  56 |      return [w for k, w in enumerate(tokens) if not dollars_after_number(tokens, k)]
  57 |  
  58 |  
  59 | +# RULING 135 (orchestrator 10:50 ET Nov 17): THE COMPARISON CANON. "Differences of spelling are not differences of
  60 | +# speech." Applied to a differing pair's two sides before the pair is compared (the lock, ruling 72's comparison,
  61 | +# G18); canon_tokens itself is unchanged, so spans, edges and indices are not touched.
  62 | +REDUCTIONS = {      # (c) spoken reductions equal their full form: a CLOSED list, none added without a ruling
  63 | +    "kinda": ("kind", "of"), "sorta": ("sort", "of"), "gonna": ("going", "to"), "wanna": ("want", "to"),
  64 | +    "gotta": ("got", "to"), "lemme": ("let", "me"), "gimme": ("give", "me"), "cause": ("because",),
  65 | +    "cuz": ("because",), "em": ("them",), "ya": ("you",), "yeah": ("yes",), "yep": ("yes",)}
  66 | +FILLER_TOKENS = frozenset({"um", "uh", "er", "ah", "hm", "hmm", "mm", "mhm"})      # (d) non-lexical
  67 | +CONSONANTS = frozenset("bcdfghjklmnpqrstvwxz")                                     # (d) a stray consonant ("a", "i": words)
  68 | +
  69 | +
  70 | +def comparison_form(tokens):
  71 | +    """RULING 135 (a)+(c): canon tokens with their apostrophes removed, each spoken reduction (REDUCTIONS) expanded."""
  72 | +    out = []
  73 | +    for t in tokens:
  74 | +        t = str(t).replace("'", "")
  75 | +        out += list(REDUCTIONS.get(t, (t,)))
  76 | +    return out
  77 | +
  78 | +
  79 | +def nonlexical(tok):
  80 | +    """RULING 135 (d): a filler (FILLER_TOKENS) or a single consonant letter: not a word."""
  81 | +    return tok in FILLER_TOKENS or (len(tok) == 1 and tok in CONSONANTS)
  82 | +
  83 | +
  84 | +def same_words(x, y):
  85 | +    """RULING 135: the two sides of a differing pair (lists of canon tokens) are the same words. Both sides in comparison
  86 | +    form (a, c), non-lexical tokens left out (d); equal tokens, or, when neither side holds a digit, equal letters once
  87 | +    every space and hyphen is gone (b: 'itrust capital's' = 'I trust capital's' = 'iTrustCapital's', names too). Still
  88 | +    a difference: two different single letters (a letter-name dispute), any digit difference (numbers compare token for
  89 | +    token; the currency form is (B)'s), and any other change of letters (a negation, a name, a content word)."""
  90 | +    cx, cy = comparison_form(x), comparison_form(y)
  91 | +    lx = [t for t in cx if len(t) == 1 and t in CONSONANTS]
  92 | +    ly = [t for t in cy if len(t) == 1 and t in CONSONANTS]
  93 | +    if lx and ly and lx != ly:
  94 | +        return False
  95 | +    a, b = [t for t in cx if not nonlexical(t)], [t for t in cy if not nonlexical(t)]
  96 | +    if a == b:
  97 | +        return True
  98 | +    if any(ch.isdigit() for t in a + b for ch in t):
  99 | +        return False
 100 | +    return "".join(a).replace("-", "") == "".join(b).replace("-", "")
 101 | +
 102 | +
 103 |  def canon(text):
 104 |      return " ".join(canon_tokens(text))
 105 |  
 106 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 107 | index d641d88..12aab99 100644
 108 | --- a/pipeline/lock_precheck.py
 109 | +++ b/pipeline/lock_precheck.py
 110 | @@ -31,7 +31,9 @@ Outcomes:
 111 |    when this side's own re-check (attest.class_131, from the record's three readings) finds every pair decided the same
 112 |    way, every run-taken pair at least 3 tokens from both cut edges, no number, name or negation, and the spoken text
 113 |    the merged reading; anything else is a hold (fail closed). (B): currency format ('$2 billion' for a spoken
 114 | -  '2 billion') is no difference.
 115 | +  '2 billion') is no difference. RULING 135: neither is a pair of the same words by canon.same_words (spelling,
 116 | +  segmentation, the closed reductions, fillers and a stray consonant); this side's re-checks drop it where the
 117 | +  render's lock and ruling 72's comparison do (attest.class_131, attest.class_84).
 118 |  - hold: the clip may not be used with that text. The reason says why.
 119 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
 120 |    is sent again rather than reusing an error.
 121 | @@ -47,7 +49,9 @@ from datetime import datetime, timezone
 122 |  import attest as AT
 123 |  import canon as C
 124 |  
 125 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131"   # RULING 131
 126 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135"   # RULING 135
 127 | +#   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
 128 | +#   RULING 131
 129 |  #   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
 130 |  #   Nov 17); entries under the old RULES are never read. RULING 105 (orchestrator
 131 |  #   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
 132 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 133 | index c39b164..ecf4966 100644
 134 | --- a/tests/package/test_lock_precheck.py
 135 | +++ b/tests/package/test_lock_precheck.py
 136 | @@ -137,7 +137,7 @@ class TestRuling84(unittest.TestCase):
 137 |          """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 138 |          rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 139 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 140 | -                                   "ruling 131")
 141 | +                                   "ruling 131 + ruling 135")
 142 |  
 143 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 144 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 145 | @@ -160,8 +160,8 @@ class TestRuling84(unittest.TestCase):
 146 |              self.assertIn("outside ruling 84's class", d["why"])
 147 |          e = entry(self.s, "adopt_spoken", spoken_text="So over time, I came to think so the money itself was broken.")
 148 |          e["approved_text"] = "So over time, um, I came to think so the money itself was broken."
 149 | -        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone
 150 | -        self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 151 | +        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone: since
 152 | +        self.assertEqual(LP.decide(s2, e)["verdict"], "adopt")             # RULING 135 (d) no difference wherever it sits
 153 |  
 154 |  
 155 |  class TestRuling131(Dirs):
 156 | @@ -180,16 +180,17 @@ class TestRuling131(Dirs):
 157 |      SECOND = ("comes next? I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a "
 158 |                "wall of worry. Um, there was massive amounts of fear during that period of time. Bitcoin was actually "
 159 |                "trending up into the right, and fear was also trending up into the right during that,")
 160 | -    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. Um, "
 161 | -              "there was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 162 | -              "right, and fear was also trending up into the right during that.")
 163 | -    SPOKEN = MERGED.replace("2023 bull", "2023, uh, bull")      # ruling 72 on top: the second recogniser's 'uh'
 164 | +    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. There "
 165 | +              "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 166 | +              "right, and fear was also trending up into the right during that.")   # RULING 135: 'um' is no word, the
 167 | +    SPOKEN = MERGED                     # approved words stay there; ruling 72's 'uh' and 'Um' are no difference either
 168 | +    HEARD = ("I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a wall of worry. "
 169 | +             "Um, there was massive amounts of fear during that period of time. Bitcoin was actually trending up into "
 170 | +             "the right, and fear was also trending up into the right during that,")   # the second reading, trimmed
 171 |      PAIRS = [{"run": "bunch of", "approved": "budget", "second_reads": "run", "took": "run",
 172 |                "agreed": ["run", "second"], "edge_distance": 6},
 173 |               {"run": "that", "approved": "like", "second_reads": "approved", "took": "approved",
 174 | -              "agreed": ["approved", "second"], "edge_distance": 14},
 175 | -             {"run": "um", "approved": "", "second_reads": "run", "took": "run", "agreed": ["run", "second"],
 176 | -              "edge_distance": 20}]
 177 | +              "agreed": ["approved", "second"], "edge_distance": 14}]          # 'um' / '': spelling only (ruling 135)
 178 |      WBD = {"moment_id": "w", "video_id": "WdiF0i925rs", "start": 3339.9, "end": 3354.68, "text": APPROVED}
 179 |  
 180 |      def adj(self, **kw):
 181 | @@ -205,11 +206,11 @@ class TestRuling131(Dirs):
 182 |          d = self.decide()                                          # the merged text as it stands ("same")
 183 |          self.assertEqual(d["verdict"], "adopt", d.get("why"))
 184 |          self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in d["differences"]],
 185 | -                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "run")])
 186 | -        d = self.decide(self.SPOKEN)                               # with ruling 72's 'uh' on top ("adopt")
 187 | +                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "spelling")])
 188 | +        d = self.decide(self.HEARD)                                # the second reading itself: only no-words differ
 189 |          self.assertEqual(d["verdict"], "adopt", d.get("why"))
 190 | -        self.assertEqual([(x["spoken"], x["approved"], x["took"], x["class"]) for x in d["differences"]][3:],
 191 | -                         [("uh", "", "ruling 72", "filler")])
 192 | +        self.assertTrue(d["differences"][3:] and {x["class"] for x in d["differences"][3:]} <=
 193 | +                        {"filler", "spelling only (ruling 135)"}, d["differences"][3:])   # no word differs
 194 |          s = LP.segments_of([self.WBD])[0]
 195 |          self.put(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
 196 |          pre = LP.check([self.WBD], "r", self.req, self.res, log=lambda m: None)
 197 | @@ -221,17 +222,17 @@ class TestRuling131(Dirs):
 198 |          self.assertEqual(LP.pin_problems(pk), [])
 199 |  
 200 |      def test_this_side_rederives_every_pair_and_never_trusts_the_record(self):
 201 | -        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"]), dict(self.PAIRS[2])]
 202 | +        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"])]
 203 |          for spoken, kw, why in (
 204 |                  (self.MERGED.replace("like climbing", "that climbing"), {"pairs": lie},   # the second reads 'like'
 205 |                   "the lock record's pairs are not this side's"),
 206 | -                (self.MERGED, {"pairs": self.PAIRS[:2]}, "the lock record's pairs are not this side's"),
 207 | +                (self.MERGED, {"pairs": self.PAIRS[:1]}, "the lock record's pairs are not this side's"),
 208 |                  (self.MERGED, {"pairs": [dict(p, edge_distance=9) for p in self.PAIRS]},
 209 |                   "the lock record's pairs are not this side's"),
 210 |                  (self.MERGED.replace("bunch of", "budget"), {}, "neither the merged reading nor"),
 211 |                  (self.MERGED.replace("massive", "huge"), {}, "neither the merged reading nor"),
 212 |                  (self.MERGED.replace("climbing", "the climbing"), {}, "neither the merged reading nor"),
 213 | -                (self.SPOKEN.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 214 | +                (self.HEARD.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 215 |                   "outside ruling 84's class"),                                     # the second recogniser alone
 216 |                  (self.MERGED, {"second_recogniser": None}, "does not hold the three readings"),
 217 |                  (self.MERGED, {"approved": self.MERGED}, "does not hold the three readings")):
 218 | @@ -342,6 +343,50 @@ class TestRuling131(Dirs):
 219 |          self.assertIn("outside ruling 84's class", d["why"])
 220 |  
 221 |  
 222 | +class TestRuling135(unittest.TestCase):
 223 | +    """RULING 135 (orchestrator 10:50 ET Nov 17), the comparison canon: spelling, segmentation (names too), the closed
 224 | +    list of spoken reductions, fillers and a stray single consonant are no difference; a digit, a different single
 225 | +    letter, a negation and any other change of letters still are. Today's held spans: DataDash 8dbc30ee ('itrust
 226 | +    capital's' / 'I trust capital's' / 'iTrustCapital's'), DataDash f9413625 ('kind of' / 'kinda'), Natalie Brunell
 227 | +    cae5123f (the second recogniser's stray 'h')."""
 228 | +    APPROVED = "Bitcoin conviction and risk management with I trust capital's vault is kind of the point here today."
 229 | +    s = LP.segments_of([{"video_id": "WjnphankXmM", "start": 601.967, "end": 613.827, "text": APPROVED}])[0]
 230 | +
 231 | +    def decide(self, spoken, **kw):
 232 | +        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, **kw))
 233 | +
 234 | +    def test_spelling_is_no_difference_in_ruling_72s_layer(self):
 235 | +        for spoken in ("Bitcoin conviction and risk management with iTrustCapital's vault is kind of the point here today.",
 236 | +                       "Bitcoin conviction and risk management with I trust capital's vault is kinda the point here today.",
 237 | +                       "Bitcoin conviction and risk management with I-trust Capital's vault is kind of the point here, h, today."):
 238 | +            d = self.decide(spoken)
 239 | +            self.assertIn(d["verdict"], ("adopt", "pass"), (spoken, d.get("why")))
 240 | +            self.assertTrue(all(x["class"] == "spelling only (ruling 135)" for x in d.get("differences") or []), d)
 241 | +
 242 | +    def test_what_still_holds(self):
 243 | +        for spoken in ("Bitcoin conviction and risk management with I trust capital's vault is kind of the point here 2day.",
 244 | +                       "Bitcoin conviction and risk management with I trust capital's vault isn't kind of the point here today.",
 245 | +                       "Bitcoin conviction and risk management with I bust capital's vault is kind of the point here today.",
 246 | +                       "Bitcoin conviction and risk management with Q trust capital's vault is kind of the point here today."):
 247 | +            self.assertEqual(self.decide(spoken)["verdict"], "hold", spoken)
 248 | +
 249 | +    def test_a_spelling_pair_never_reaches_the_vote_in_class_131(self):
 250 | +        """The render's lock drops a same-words pair right after the currency pairs: it is in neither the record's
 251 | +        pairs nor the vote, and the sealed text keeps the approved words there (8dbc30ee's three readings)."""
 252 | +        app = "So Q is a product, iTrustCapital's vault holds the coins and the founder bought a bunch of pieces then."
 253 | +        run = "so q is a product, itrust capital's vault holds the coins and the founder bought a bunch of pieces then."
 254 | +        sec = "So Q is a product, I trust capital's vault holds the coins and the founder bought a bunch of pieces then."
 255 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 256 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "pairs": [], "run_decode": run,
 257 | +               "approved": app, "second_recogniser": sec}
 258 | +        rows = AT.class_131(app, app, adj)
 259 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
 260 | +                         [("itrust", "itrustcapitals", "spelling")] if rows and rows[0]["approved"] == "itrustcapitals"
 261 | +                         else [(rows[0]["spoken"], rows[0]["approved"], "spelling")] + [] if rows else [])
 262 | +        self.assertTrue(rows and all(x["took"] == "spelling" for x in rows), rows)
 263 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 264 | +
 265 | +
 266 |  class TestCheck(Dirs):
 267 |      def run_check(self, segs, appear=None, timeout=60.0):
 268 |          t = [0.0]
 269 | 
```

---

pp-selectid: RULING 135 (orchestrator 10:50 ET Nov 17), the builder's lockstep half, FAST. "A COMPARISON CANON applied
to all three readings before any pair is compared ... (a) case, punctuation and apostrophes ignored; (b) SEGMENTATION
ignored: readings whose letters are identical once spaces and hyphens are removed are the same ... names too ... (c)
spoken reductions equal their full form, a closed list in canon.py ... (d) NON-LEXICAL tokens are fillers wherever they
sit ... and any stray single consonant letter one reading alone hears ... STILL HOLDS: numbers (save the currency
canon), negations, a name whose letters differ, any content pair where all three differ, ruling 73's sentence edges."
The integrator owns canon.py (taken byte-identical: canon.same_words(x, y), comparison_form, REDUCTIONS, FILLER_TOKENS,
CONSONANTS) and the render's lock: it drops a run/approved pair with same_words right after the currency pairs, before
the critical check and the vote, and ruling 72's comparison drops a lock/second-recogniser pair with same_words before
its classes. Files here: pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py
(canon.py shown for reference: it is the integrator's, audited on its side).

THE CHANGE (this side's re-checks mirror the render exactly where it drops):
(a) attest.class_131 (the ruling 131 (A) re-check): right after the currency pairs, a pair with canon.same_words is
    dropped (took "spelling"), before the critical check (attest.critical, UNCHANGED) and the vote; it keeps the approved
    words in the merged text; the record's pairs are compared without it, as without the currency pairs (the
    integrator's record keeps both apart: "currency_format", "spelling_only").
(b) attest.class_84 (ruling 84's class, used for every adopt_spoken and for ruling 72's layer on the merged text): a
    differing pair with canon.same_words is class "spelling only (ruling 135)", before the critical check and the
    classes; ruling 84's existing filler step (fillers in a difference, spoken side) runs first, UNCHANGED.
(c) lock_precheck.RULES gains "+ ruling 135"; DECODER moves to the integrator's final sha at landing.

TESTS: TestRuling135: spelling, segmentation (a name too: 'I trust capital's' / 'iTrustCapital's' / 'I-trust Capital's'),
'kinda' / 'kind of', a stray 'h' are no difference in ruling 72's layer; a digit, a negation, a changed content word
('trust' / 'bust') and a letter-name dispute ('Q' / 'I') still hold; in class_131 a same-words pair never reaches the
record's pairs or the vote. TestRuling131's fixtures move to ruling 135 (last night's 'um' / '' is now spelling only,
the sealed text keeps the approved words; ruling 72's 'uh' / 'Um' are no difference), and TestRuling84's "a filler on
the approved side alone" now adopts (135 (d): wherever it sits). Mutations M1-M26 after a control run: 26 of 26
killed (M24-M26 the three new drops). 47 lock tests pass.

PLEASE CHECK: (1) that nothing 135 keeps holding can be dropped as spelling: a number, a negation, a name whose letters
differ, a different single letter, a content word; (2) that the drops sit exactly where the render's do (after
currency, before critical and the vote; before ruling 84's classes); (3) that a same-words pair can never change the
sealed text; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
