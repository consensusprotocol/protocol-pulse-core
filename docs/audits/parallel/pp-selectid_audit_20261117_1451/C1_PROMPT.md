# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1451
# Branch: pp-selectid
# Generated: 2026-11-17 14:51 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1451/C1_STEP.diff (199 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index f4bb6eb..690d09a 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -237,7 +237,8 @@ def class_131(spoken, approved, adj):
   6 |              out.append(dict(row, took="spelling", edge_distance=None, **{"class": "spelling only (ruling 135)"}))
   7 |              continue
   8 |          row["edge_distance"] = edge_distance(r, p, op)
   9 | -        if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  10 | +        if any(critical(t, texts) for t in r[a:b] + p[c:d]) and not canon.word_form(r[a:b], p[c:d]):   # RULING 142
  11 | +            #   (2): a possessive or plural ending ('bitcoin' / "bitcoin's") goes to the vote, as the render's lock
  12 |              out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
  13 |          elif reads(p, s, c, d):
  14 |              out.append(dict(row, took="approved", **{"class": "two of three readings: the approved words"}))
  15 | diff --git a/pipeline/canon.py b/pipeline/canon.py
  16 | index 9a373e0..c12c8a1 100644
  17 | --- a/pipeline/canon.py
  18 | +++ b/pipeline/canon.py
  19 | @@ -16,7 +16,8 @@ different name does not. canon_tokens(text) -> the canonical word list; canon(te
  20 |                        'five point five percent'; 'dollar' = 'dollars'; currency_free() (ruling 131 (B)) also equals
  21 |                        '$2 billion' and a spoken '2 billion' where a site asks for it (G18, the sentence lock)
  22 |    signs               '-5%' = 'minus 5 percent', '+5%' = 'plus 5 percent' (GPT-cut F04: -5% != +5%); a hyphen
  23 | -                      between words or a range ('2026-11', '74-75') is not a sign
  24 | +                      between words or a range ('2026-11', '74-75') is not a sign, nor one right after a number
  25 | +                      and a space before a digit ('24 -7, 365' = '24/7/365', ruling 142 (1))
  26 |  Every comparison site (quote verification, selection anchors, edge words, G3b, G18, sign-off names, ledger
  27 |  statements) goes through this module; pipeline/test_canon.py fails any site that compares text another way.
  28 |  """
  29 | @@ -75,10 +76,12 @@ _SIGN = re.compile(r"(?<![\w.,$%])-(?=\$?\d)")             # '-5%', '(-$40M)': a
  30 |  _SIGN_SPACED = re.compile(r"(^|[^\d\s.,%]\s*)-\s+(?=\$?\d)")   # '- 5%', 'is - 5%' (cycle-2 #6); '70 - 75' is a range
  31 |  _PLUS = re.compile(r"\+\s*(?=\$?\d)")                         # '+5%', '+ 5%': a plus is never a hyphen
  32 |  _CUR_SIGN = re.compile(r"\$\s*([-+])\s*(?=\d)")                # '$-5', '$+5': the sign after the currency
  33 | +_NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)")    # ruling 142 (1): '24 -7' after a number and a space: never a sign
  34 |  
  35 |  
  36 |  def _prepare(text):
  37 |      t = fold(text).replace("\u2212", " minus ")       # (fold maps U+2212 itself; kept for safety)
  38 | +    t = _NUM_HYPHEN.sub(r"\1", t)                    # ruling 142 (1): '24 -7, 365' reads '24 7 365', as '24/7/365'
  39 |      t = _CUR_SIGN.sub(lambda m: (" minus $" if m.group(1) == "-" else " plus $"), t)
  40 |      t = _PLUS.sub(" plus ", t)
  41 |      t = _SIGN_SPACED.sub(lambda m: m.group(1) + " minus ", t)
  42 | @@ -306,6 +309,24 @@ def nonlexical(tok, stray=False):
  43 |      return tok in FILLER_TOKENS or (stray and len(tok) == 1 and tok in CONSONANTS)
  44 |  
  45 |  
  46 | +_FORM_END = re.compile(r"(?:'s|s'|'|s)$")         # ruling 142 (2): a possessive or plural ending (the canon folds ’)
  47 | +
  48 | +
  49 | +def word_form(x, y):
  50 | +    """Ruling 142 (2) (orchestrator 2026-11-17 '14:32'): two readings that differ ONLY by a possessive or plural ending
  51 | +    on ONE word ('bitcoin' / "bitcoin's" / 'bitcoins' / "bitcoins'"): a word-form pair, decided like any other differing
  52 | +    pair by ruling 131 (A)'s two of three (the sealed text takes that reading; all three different still holds). Never
  53 | +    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's)."""
  54 | +    x, y = list(x or []), list(y or [])
  55 | +    if len(x) != len(y) or not x:
  56 | +        return False
  57 | +    diff = [(a, b) for a, b in zip(x, y) if a != b]
  58 | +    if len(diff) != 1 or re.search(r"\d", diff[0][0] + diff[0][1]):
  59 | +        return False
  60 | +    a, b = (_FORM_END.sub("", t) for t in diff[0])
  61 | +    return bool(a) and a == b
  62 | +
  63 | +
  64 |  def same_words(x, y, stray=()):
  65 |      """RULING 135: the two sides of a differing pair (lists of canon tokens) are the same words. Both sides in comparison
  66 |      form (a, c), fillers left out (d); equal tokens, or, when neither side holds a digit, equal letters once every space
  67 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  68 | index f16b280..01138c8 100644
  69 | --- a/pipeline/lock_precheck.py
  70 | +++ b/pipeline/lock_precheck.py
  71 | @@ -49,7 +49,9 @@ from datetime import datetime, timezone
  72 |  import attest as AT
  73 |  import canon as C
  74 |  
  75 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135"   # RULING 135
  76 | +RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
  77 | +         "ruling 142")                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
  78 | +#   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
  79 |  #   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
  80 |  #   RULING 131
  81 |  #   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
  82 | @@ -59,7 +61,7 @@ RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105
  83 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  84 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  85 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  86 | -DECODER = "b52c9354d604"                      # side): the render's own cut placement joins the pre-check (a passing
  87 | +DECODER = "fe809cb4e680"                      # side): the render's own cut placement joins the pre-check (a passing
  88 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  89 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  90 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  91 | @@ -74,6 +76,8 @@ DECODER = "b52c9354d604"                      # side): the render's own cut plac
  92 |  #   ce72aefa342dcd94dd45d8b4bc96ec6477ec04c91914db2054403338d7559e60
  93 |  #   RULING 135 (the comparison canon: canon.same_words; the integrator's branch r135-canon, audited; lockstep as with 131):
  94 |  #   b52c9354d604ab2303a91e6e6e5f926990987d46448992579684934f62e9392d
  95 | +#   RULING 142 (canon's '24 -7' and canon.word_form, adjudicate_lock's word-form exemption; the integrator's branch
  96 | +#   r141-sign f02dd73c, audited; lockstep as with 135): fe809cb4e680a3bc5df49e4c397e79f6cf2277650ea02c05cf88b34ecc573ebd
  97 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  98 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  99 |                          "lock_requests")      # this worktree's; the service only reads it
 100 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 101 | index 0c7fc5a..17514ac 100644
 102 | --- a/tests/package/test_lock_precheck.py
 103 | +++ b/tests/package/test_lock_precheck.py
 104 | @@ -12,6 +12,7 @@ HERE = os.path.dirname(os.path.abspath(__file__))
 105 |  REPO = os.path.dirname(os.path.dirname(HERE))
 106 |  sys.path.insert(0, os.path.join(REPO, "pipeline"))
 107 |  import attest as AT  # noqa: E402
 108 | +import canon as C  # noqa: E402
 109 |  import lock_precheck as LP  # noqa: E402
 110 |  
 111 |  HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 112 | @@ -59,7 +60,7 @@ class TestRequest(Dirs):
 113 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 114 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 115 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 116 | -                         "DcUbBkyeh9M.216.054-228.674.b52c9354d604.json")             # ruling 135's decoder
 117 | +                         "DcUbBkyeh9M.216.054-228.674.fe809cb4e680.json")             # ruling 142's decoder
 118 |  
 119 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 120 |          segs = LP.segments_of([HOOK, CLIP])
 121 | @@ -134,10 +135,10 @@ class TestRuling84(unittest.TestCase):
 122 |      s = LP.segments_of([BREEDLOVE])[0]
 123 |  
 124 |      def test_the_rules_string_is_the_integrators(self):
 125 | -        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 126 | -        rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 127 | +        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
 128 | +        RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
 129 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 130 | -                                   "ruling 131 + ruling 135")
 131 | +                                   "ruling 131 + ruling 135 + ruling 142")
 132 |  
 133 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 134 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 135 | @@ -386,6 +387,50 @@ class TestRuling135(unittest.TestCase):
 136 |          self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 137 |  
 138 |  
 139 | +class TestRuling142(unittest.TestCase):
 140 | +    """RULING 142 (orchestrator 14:32 ET Nov 17), the integrator's batch 110 mirrored (its canon.py byte-identical, its
 141 | +    adjudicate_lock hunk in attest.class_131): (1) a hyphen right after a number and a space, before a digit, is never
 142 | +    a sign ('24/7/365' decoded '24 -7, 365': Yahoo Finance f0a51c45 held on 'minus'); (2) a possessive or plural
 143 | +    ending is a word-form pair: no law L-v 2 hold before ruling 131 (A)'s two of three, which decides it (the run's
 144 | +    reading only at an edge >= 3; all three different still holds): Natalie Brunell feb4b72f ('bitcoin' / "bitcoin's")."""
 145 | +    APP = "The thing about Bitcoin's design is that nobody can change the rules without everyone agreeing to it here."
 146 | +    RUN = "The thing about Bitcoin design is that nobody can change the rules without everyone agreeing to it here."
 147 | +    THIRD = "The thing about Bitcoins design is that nobody can change the rules without everyone agreeing to it here."
 148 | +    s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": APP}])[0]
 149 | +
 150 | +    def test_a_number_space_hyphen_digit_is_no_sign(self):
 151 | +        self.assertEqual(C.canon_tokens("24 -7, 365"), ["24", "7", "365"])
 152 | +        self.assertIn("minus", C.canon_tokens("it fell -5% today"))           # a sign after a word stays a sign
 153 | +        self.assertIn("minus", C.canon_tokens("it is - 5% now"))
 154 | +
 155 | +    def test_a_word_form_pair_and_what_is_not_one(self):
 156 | +        self.assertTrue(C.word_form(["bitcoin"], ["bitcoin's"]))
 157 | +        self.assertTrue(C.word_form(["bitcoin"], ["bitcoins"]))
 158 | +        for x, y in ((["1990"], ["1990s"]), (["bitcoin", "x"], ["bitcoin's", "y"]), (["bitcoin"], ["ethereum"]),
 159 | +                     ([], []), (["bitcoin"], ["bitcoin's", "x"])):
 160 | +            self.assertFalse(C.word_form(x, y), (x, y))
 161 | +
 162 | +    def decide(self, spoken, second, took):
 163 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": self.APP,
 164 | +               "second_recogniser": second,
 165 | +               "pairs": [{"run": "bitcoin", "approved": "bitcoin's", "took": took, "edge_distance": 3}]}
 166 | +        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, adjudication=adj))
 167 | +
 168 | +    def test_two_of_three_decides_a_word_form_pair_of_a_name(self):
 169 | +        self.assertEqual(self.decide(self.APP, self.APP, "approved")["verdict"], "pass")   # the approved words
 170 | +        d = self.decide(self.RUN, self.RUN, "run")                                      # as spoken, edge 3
 171 | +        self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
 172 | +        self.assertEqual(self.decide(self.APP, self.THIRD, None)["verdict"], "hold")    # all three differ
 173 | +
 174 | +    def test_a_name_that_is_no_word_form_still_holds(self):
 175 | +        app = self.APP.replace("Bitcoin's", "Ethereum's")
 176 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": app,
 177 | +               "second_recogniser": app, "pairs": [{"run": "bitcoin", "approved": "ethereum's", "took": "approved",
 178 | +                                                    "edge_distance": 3}]}
 179 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 180 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "hold")
 181 | +
 182 | +
 183 |  class TestCheck(Dirs):
 184 |      def run_check(self, segs, appear=None, timeout=60.0):
 185 |          t = [0.0]
 186 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 187 | index 4903fe7..ecccdfc 100644
 188 | --- a/tests/package/test_ruling_105.py
 189 | +++ b/tests/package/test_ruling_105.py
 190 | @@ -40,7 +40,7 @@ BLOCKWARE = record()
 191 |  class TestTheRules(Dirs):
 192 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 193 |          self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 194 | -        self.assertEqual(LP.DECODER, "b52c9354d604")                                 # ruling 135 moved it
 195 | +        self.assertEqual(LP.DECODER, "fe809cb4e680")                                 # ruling 142 moved it
 196 |          s = LP.segments_of([HOOK])[0]
 197 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 198 |                            at="2026-11-14T21:00:00Z"))
 199 | 
```

---

pp-selectid: RULING 142 (1) + (2) (orchestrator 14:32 ET Nov 17), the BUILDER'S MIRROR of the integrator's batch 110
(its branch r141-sign f02dd73c, audited on its side), a DECODER LOCKSTEP as rulings 131 / 135 were. Both sides must decide
every lock record identically: the integrator's render (pinned.adjudicate_lock) writes it, and this side's
lock_precheck.decide (lock_precheck.py:161) re-derives it with attest.class_131 (lock_precheck.py:184); a record whose
pairs differ from this side's derivation always holds (attest.py:260). Files: pipeline/canon.py (copied BYTE-IDENTICAL
from the integrator's staged file, sha256 88e45f13d738fa7f38e625c395d247464d433ac26a954732536297f1a96ba742),
pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py.

THE RULING: (1) a hyphen right after a number and a space, before a digit, is never a sign ('24/7/365', decoded
'24 -7, 365' by the run: Yahoo Finance f0a51c45 held on 'minus'). (2) "L-v 2 'bitcoin' against 'bitcoin's': a
possessive or plural ending is a word-form pair like any other: ruling 131 (A)'s two-of-three decides it and the sealed
text takes that reading; all three differing still holds" (Natalie Brunell feb4b72f).

THE CHANGE:
(a) canon.py (the integrator's): _NUM_HYPHEN (canon.py:79) applied in _prepare (:84) before the sign passes;
    word_form(x, y) (:315): equal-length token lists, exactly ONE differing token, no digit in it, equal once a trailing
    's / s' / ' / s is stripped.
(b) attest.class_131 (attest.py:197), mirroring the integrator's one-line adjudicate_lock hunk ("crit = sorted({t for _,
    a, b, c, d in ops if not canon.word_form(r[a:b], p[c:d]) for t in ... if _lv2_critical(...)})"): a differing pair
    for which canon.word_form is True is exempt from the critical-token hold (:240). Everything else is UNCHANGED: the
    currency pairs first (:232), the spelling pairs next (:235, ruling 135), then the vote: the approved words when the
    second recogniser reads them (:243), the run's reading only when it does and the pair is >= EDGE_131 tokens from both
    cut edges (:245), else a hold ("all three readings differ"). class_84 and carry_class are untouched, as on the
    integrator's side.
(c) lock_precheck.py: RULES gains " + ruling 142"; DECODER "fe809cb4e680" (full sha in the comment). Entries under the
    old RULES or decoder are never read (unchanged rule).

TESTS (test_lock_precheck TestRuling142, 4 new; the RULES and decoder pins updated): '24 -7, 365' has no sign while
'fell -5%' and 'is - 5%' keep theirs; word_form's positive and negative cases (a digit, two differing tokens, other
words, empty, unequal lengths); a word-form pair of a NAME decided two of three both ways (pass / adopt under ruling 131
(A)) and held when all three differ; a name that is no word form still holds. Mutations: 6 of 6 killed.

PLEASE CHECK: (1) can word_form exempt anything the ruling did not (a number, a negation, a different name, two words)?
(2) is the mirror exactly the integrator's hunk (same pairs, same order, nothing else exempted)? (3) the sign rule's
reach ('24 -7' never a sign; '-5' after a word still one); (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
