# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_1126
# Branch: pp-selectid
# Generated: 2026-11-16 11:26 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_1126/C1_STEP.diff (208 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 061a9f0..980c289 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -54,7 +54,8 @@
   6 |     ],
   7 |     "temperature": 0,
   8 |     "key_name": "XAI_API_KEY_MEDLEY",
   9 | -   "family": "grok"
  10 | +   "family": "grok",
  11 | +   "max_out_cap": 12000
  12 |    },
  13 |    "heimdall:qwen/qwen3.8-27b": {
  14 |     "vendor": "heimdall",
  15 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  16 | index 2e84551..a70cdb5 100644
  17 | --- a/pipeline/providers.py
  18 | +++ b/pipeline/providers.py
  19 | @@ -68,6 +68,10 @@ class ReplayMiss(Exception):
  20 |  
  21 |  
  22 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
  23 | +RESERVE_CHARS_PER_TOKEN = 3          # RULING 121 (1) (orchestrator 11:25 ET Nov 16): the reserve counts a prompt's tokens
  24 | +RESERVE_MARGIN = 1.25                # as its characters / 3 (a deliberate over-count; English runs near 4), at list
  25 | +#   price, with the output cap the call is really sent (max_out), times 1.25; checked against every recorded Grok step-A
  26 | +#   call: no reported cost beats it (tests/providers TestRuling121Reserve)
  27 |  RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
  28 |                                       # the model's own reported rate once it has this many reported calls
  29 |  RESERVE_POLL_S = 1.0                 # BATCH 3 (Nov 14): how often a call waiting for room under the limit re-reads
  30 | @@ -197,9 +201,18 @@ class Backend:
  31 |          n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
  32 |          return len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img
  33 |  
  34 | +    @staticmethod
  35 | +    def prompt_tokens_reserve(prompt, system=None):
  36 | +        """RULING 121 (1): a prompt's input tokens for the spend guard's reserve: its characters / RESERVE_CHARS_PER_TOKEN,
  37 | +        rounded up, + 200 for the message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
  38 | +        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
  39 | +        return -(-(len(text) + len(system or "")) // RESERVE_CHARS_PER_TOKEN) + 200 + IMAGE_TOKENS_UPPER * n_img
  40 | +
  41 |      def upper_usd(self, prompt, max_tokens, system=None):
  42 | -        """The call's spend upper bound: its prompt tokens (prompt_tokens_upper) + the output cap."""
  43 | -        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": self.max_out(max_tokens)})
  44 | +        """The spend guard's reserve for one call (RULING 121 (1)): its prompt tokens (prompt_tokens_reserve) and the
  45 | +        output cap it is really sent (max_out), at list price, times RESERVE_MARGIN."""
  46 | +        return round(RESERVE_MARGIN * self.usd({"in": self.prompt_tokens_reserve(prompt, system),
  47 | +                                                "out": self.max_out(max_tokens)}), 6)
  48 |  
  49 |      def prompt_usd(self, prompt, system=None):
  50 |          """RULING 83 (a) (orchestrator 20:33 Nov 13): what a call abandoned at its deadline is booked at: its PROMPT
  51 | @@ -453,7 +466,9 @@ class XAIBackend(Backend):
  52 |      SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
  53 |  
  54 |      def max_out(self, max_tokens):
  55 | -        return max(int(self.spec.get("min_out", 8000)), max_tokens * 8)       # a reasoning model thinks inside it
  56 | +        n = max(int(self.spec.get("min_out", 8000)), max_tokens * 8)          # a reasoning model thinks inside it
  57 | +        cap = self.spec.get("max_out_cap")    # RULING 121: the most output it is sent, whatever the role asks (12,000:
  58 | +        return min(n, int(cap)) if cap else n  # step A's 4,000 x 8 was 32,000 and reserved $0.80 of Grok output alone)
  59 |  
  60 |      def complete(self, prompt, max_tokens, seed, system=None):
  61 |          key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
  62 | @@ -914,7 +929,9 @@ class Router:
  63 |      def _reserve(self, b, upper):
  64 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  65 |          SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  66 | -        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late.
  67 | +        reservations stay at list price whatever the basis; since RULING 121 (1) each is the call's reserve
  68 | +        (upper_usd: characters / 3 as its prompt tokens, its real output cap, x 1.25), checked against every recorded
  69 | +        Grok step-A call rather than counted from above.
  70 |          With reserve_wait_s > 0 (a batch build's opt-in; the default 0 keeps the refusal at once that every other
  71 |          caller, the render's among them, relies on): when spent + this call's upper bound fits and only the reservations
  72 |          of calls IN FLIGHT stand in the way, the call waits for them to settle (each ends in an answer, an error or an
  73 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  74 | index 8eef714..b41e97b 100644
  75 | --- a/tests/providers/test_providers.py
  76 | +++ b/tests/providers/test_providers.py
  77 | @@ -368,8 +368,8 @@ class TestRouter(unittest.TestCase):
  78 |                         "usd_reported": 3.46, "usd_unreported_estimate": 1.81}, open(led, "w"))
  79 |              a = Fake("openai:x", "openai", answer="{}", usage={"in": 1000, "out": 100})        # no vendor figure
  80 |              rep = Fake("openai:y", "openai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
  81 | -            p = "p" * 50_000
  82 | -            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
  83 | +            p = "p" * 150_000                                       # ruling 121's reserve: 1.25 x (50,200 x $10/M +
  84 | +            with self.assertRaises(P.SpendLimit):                   # 2,000 x $100/M) = $0.88; old basis: 39.5 + it > 40
  85 |                  router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
  86 |              r = router(d, [a, rep], {"write": ["openai:x"], "judge": ["openai:y"]}, spend_path=led, limit_usd=12,
  87 |                         limit_basis="reported")
  88 | @@ -410,9 +410,9 @@ class TestRouter(unittest.TestCase):
  89 |              self.assertAlmostEqual(led_["by_backend"]["heimdall:q"]["usd_reported"], 4.5, places=6)   # recorded
  90 |              self.assertAlmostEqual(r.spent(), 0.95, places=6)                                        # never counted
  91 |              with self.assertRaises(P.SpendLimit):
  92 | -                r.call("judge", "p")                                   # 0.95 + its upper bound ($0.20) > $1.00
  93 | +                r.call("judge", "p")                    # 0.95 + its reserve ($0.25: ruling 121's x 1.25) > $1.00
  94 |              self.assertEqual((h.calls, x.calls, json.load(open(led))["reserved"]), (1, 0, {}))
  95 | -            r.limit_usd = 1.20
  96 | +            r.limit_usd = 1.25
  97 |              r.call("judge", "p")                                       # it fits under a higher cap: counted
  98 |              self.assertAlmostEqual(r.spent(), 0.96, places=6)
  99 |              every = router(d, [h, x], {"write": ["heimdall:q"]}, **kw)          # no `uncapped`: all counted, as before
 100 | @@ -428,11 +428,12 @@ class TestRouter(unittest.TestCase):
 101 |              led = os.path.join(d, "SPEND.json")
 102 |              a = Fake("openai:x", "openai", answer="{}", usage={"in": 400_000, "out": 0})        # $4.00 a call
 103 |              r = router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=10)
 104 | -            p = "p" * 400_000                                     # upper bound ~ $4.00 in + $0.20 out
 105 | +            p = "p" * 1_200_000             # ruling 121's reserve: 1.25 x (400,200 x $10/M + 2,000 x $100/M) = $5.25
 106 | +            #   (its characters / 3 as tokens: this prompt bills 400,000, three characters a token)
 107 |              r.call("write", p)
 108 |              r.call("write", p)
 109 |              with self.assertRaises(P.SpendLimit):
 110 | -                r.call("write", p)                                # 8.00 + 4.20 > 10: refused BEFORE it runs
 111 | +                r.call("write", p)                                # 8.00 + 5.25 > 10: refused BEFORE it runs
 112 |              d_ = json.load(open(led))
 113 |              self.assertEqual((d_["calls"], a.calls, d_["reserved"]), (2, 2, {}))
 114 |              self.assertLessEqual(d_["usd_estimate"], 10)
 115 | @@ -730,5 +731,92 @@ class TestRuling86Shadow(TestRuling85Routing):
 116 |                               (["heimdall:qwen"], ["xai:grok"]))
 117 |              self.assertEqual((r.backends["heimdall:qwen"].calls, r.backends["xai:grok"].calls), (1, 2))
 118 |  
 119 | +class TestRuling121Reserve(unittest.TestCase):
 120 | +    """RULING 121 (1) (orchestrator 11:25 ET Nov 16): the spend guard reserves a call at its prompt's characters / 3 as
 121 | +    tokens, the output cap it is really sent, list price, times 1.25; and the xAI back-end is sent at most 12,000 output
 122 | +    tokens (step A's 4,000 x 8 was 32,000: $0.80 of Grok output at list, more than the day's $1.00 had left)."""
 123 | +    REPLIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "package", "fixtures", "replies")
 124 | +
 125 | +    def xai(self, cap=True, answer='{"ok": true}'):
 126 | +        spec = dict(json.load(open(os.path.join(os.path.dirname(P.__file__), "model_providers.json")))["backends"][
 127 | +            "xai:grok-4.20-0309-reasoning"])
 128 | +        if not cap:
 129 | +            spec.pop("max_out_cap", None)
 130 | +        b = P.XAIBackend("xai:grok-4.20-0309-reasoning", spec, "/nonexistent")
 131 | +        b.sent = []
 132 | +        b.key = lambda name: "k"
 133 | +        return b
 134 | +
 135 | +    def test_the_reserve_is_characters_over_3_the_real_cap_list_price_x_1_25(self):
 136 | +        b = self.xai()
 137 | +        self.assertEqual((b.max_out(4000), b.max_out(1200), b.max_out(750)), (12000, 9600, 8000))
 138 | +        self.assertEqual(self.xai(cap=False).max_out(4000), 32000)
 139 | +        self.assertAlmostEqual(b.upper_usd("p" * 7800, 4000), 1.25 * ((2600 + 200) * 5e-6 + 12000 * 25e-6), places=6)
 140 | +        self.assertAlmostEqual(b.upper_usd("p" * 7801, 4000, system="s"),             # 7,802 characters / 3 =
 141 | +                               1.25 * ((2601 + 200) * 5e-6 + 12000 * 25e-6), places=6)    # 2,600.7: rounded up
 142 | +        v = {"text": "t" * 30, "images": ["i", "i"]}
 143 | +        self.assertEqual(P.Backend.prompt_tokens_reserve(v), 10 + 200 + 2 * P.IMAGE_TOKENS_UPPER)
 144 | +
 145 | +    def test_grok_is_sent_the_capped_output(self):
 146 | +        b = self.xai()
 147 | +        seen = []
 148 | +        saved = P._http_json
 149 | +        P._http_json = lambda url, body, headers, timeout: (seen.append(body) or {
 150 | +            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}})
 151 | +        try:
 152 | +            try:
 153 | +                b.complete("p", 4000, 7)
 154 | +            except Exception:                          # the reply's own handling is not under test: only what was sent
 155 | +                pass
 156 | +        finally:
 157 | +            P._http_json = saved
 158 | +        self.assertEqual(seen[0]["max_tokens"], 12000)
 159 | +
 160 | +    def recorded(self):
 161 | +        out = []
 162 | +        for root, _, files in os.walk(self.REPLIES):
 163 | +            for f in files:
 164 | +                if not f.endswith(".json"):
 165 | +                    continue
 166 | +                d = json.load(open(os.path.join(root, f)))
 167 | +                if str(d.get("backend")).startswith("xai:grok") and "context_verdict" in str(d.get("role")):
 168 | +                    out.append(d)
 169 | +        return out
 170 | +
 171 | +    def test_no_recorded_grok_step_a_call_cost_more_than_its_reserve(self):
 172 | +        """The ruling's check: on every recorded Grok step-A call, the reserve (with the cap it was really sent then,
 173 | +        8 x its max_tokens) is at or above its reported cost; under the 12,000 cap, every call that stayed inside it."""
 174 | +        calls, old, new = self.recorded(), self.xai(cap=False), self.xai()
 175 | +        self.assertGreaterEqual(len(calls), 438)
 176 | +        usd = lambda d: d["usage"].get("usd_reported", d.get("usd"))
 177 | +        margin, cut = min((old.upper_usd(d["prompt"], d["max_tokens"], d.get("system")) - usd(d), i)
 178 | +                          for i, d in enumerate(calls)), [d for d in calls if d["usage"]["out"] > 12000]
 179 | +        self.assertGreaterEqual(margin[0], 0.10)                         # the tightest: +$0.1075 (the $0.40 of Nov 12)
 180 | +        for d in calls:
 181 | +            if d["usage"]["out"] <= 12000:
 182 | +                self.assertLessEqual(usd(d), new.upper_usd(d["prompt"], d["max_tokens"], d.get("system")))
 183 | +        self.assertEqual(len(cut), 4)                    # one Nov 12, three Nov 13, none since: under the cap they would
 184 | +        self.assertTrue(all(str(d["recorded_at"]) < "2026-11-14" for d in cut))   # have been cut at 12,000 (out of
 185 | +        #   contract: no verdict, held), never billed past the reserve
 186 | +
 187 | +    def test_a_step_a_call_fits_what_the_day_has_left(self):
 188 | +        """The Fox step A of 11:03 ET: two excerpts, about 7,800 characters, max_tokens 4,000; $0.5835 spent of the
 189 | +        $1.00 day. Capped, it reserves $0.39 and runs; with Grok's old 32,000 cap it reserves $1.02 and is refused."""
 190 | +        with tempfile.TemporaryDirectory() as d:
 191 | +            led = os.path.join(d, "SPEND.json")
 192 | +            json.dump({"usd_estimate": 0.5835, "calls": 1, "by_backend": {"xai:grok-4.20-0309-reasoning": {
 193 | +                "calls": 1, "in": 0, "out": 0, "usd_estimate": 0.5835, "usd_reported": 0.5835}},
 194 | +                "by_role": {}, "reserved": {}, "usd_reported": 0.5835, "usd_unreported_estimate": 0.0}, open(led, "w"))
 195 | +            for cap, fits in ((True, True), (False, False)):
 196 | +                b = self.xai(cap=cap)
 197 | +                b.complete = lambda prompt, max_tokens, seed, system=None: ('{"ok": true}', {"in": 2000, "out": 3000}, 0.02)
 198 | +                r = router(d, [b], {"context_verdict": [b.name]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 199 | +                if fits:
 200 | +                    self.assertEqual(r.call("context_verdict", "p" * 7800, 4000).text, '{"ok": true}')
 201 | +                else:
 202 | +                    with self.assertRaises(P.SpendLimit):
 203 | +                        r.call("context_verdict", "p" * 7800, 4000)
 204 | +
 205 | +
 206 |  if __name__ == "__main__":
 207 |      unittest.main()
 208 | 
```

---

pp-selectid: RULING 121 (1) (orchestrator 11:25 ET Nov 16), THE SPEND GUARD'S RESERVE, and the xAI output cap.
Files: pipeline/providers.py (Backend.prompt_tokens_reserve, Backend.upper_usd, XAIBackend.max_out, the _reserve
docstring), pipeline/model_providers.json (one key), tests/providers/test_providers.py.

THE ORDER, verbatim: "(1) THE RESERVE: counting every prompt CHARACTER as a token reserves about four times what a call
can cost. Reserve on a token estimate instead: characters / 3 for the prompt (a deliberate over-count; English runs near
4), the call's real max output, list price, times 1.25. Check it against the 438 recorded Grok step-A calls: the reserve
must be at or above the reported cost of EVERY one of them (report the tightest margin); if any call beats it, raise the
divisor's safety until none does." The daily outside cap stays $1.00 (ruling 118: outside vendors only; Heimdall never
reserved).
WHAT THE MEASURE SHOWED (STATE 11:21): the xAI back-end sends Grok 8 x the nominal max_tokens (XAIBackend.max_out:
max(min_out 8000, 8 x max_tokens)), so step A (nominal 4,000) is sent 32,000 and the guard reserved $0.80 of output at
list for every step-A call. With the call's real max output, ruling 121's reserve passes the check on all 438 recorded
calls (tightest margin +$0.1075) but reserves $1.02 for a ~7,800-character step A: never inside a $1.00 day. Grok's
recorded step-A outputs ran over 12,000 tokens in 4 of 438 (one Nov 12, three Nov 13; none since; since Nov 15 the
largest was 8,871). So the cap: "max_out_cap": 12000 on the xAI reasoning back-end (only step A is sent more than that
today: the hook rating, join table, clips-alone and coherence calls are sent 8,000-9,600). A reply cut at the cap is out
of contract: no verdict, held (law L-m, ruling 102), never a verdict made from part of a reply (unchanged guards:
providers.call_parsed and context_integrity.step_a's parsing; Router.call records finish/length on the breaker).

THE CHANGE: upper_usd (the reserve every paid call takes under the ledger lock, Router.call -> _reserve) = 1.25 x list
price of {in: ceil(characters / 3) + 200 (+ 6,000 per image of a vision prompt), out: max_out(max_tokens)}.
prompt_tokens_upper (characters as tokens) is unchanged and still books an abandoned call (prompt_usd, ruling 83 (a))
and the reported-rate estimate (ruling 107 Q1). The reservation is still taken, settled and released as before
(_reserve, unchanged but for its docstring); Heimdall stays unreserved (ruling 118's `uncapped`).

TESTS (TestRuling121Reserve): the reserve's arithmetic (characters / 3 rounded up, the real cap, x 1.25, images); the
body sent to xAI carries max_tokens 12,000; THE RULING'S CHECK on every recorded Grok step-A call in the fixtures (the
reserve with the cap each call was really sent then is >= its reported cost; tightest margin >= $0.10; under the 12,000
cap, every call that stayed inside it is within the new reserve; the 4 longer ones dated); the guard's behaviour with
$0.5835 spent of $1.00: a ~7,800-character step A reserves $0.39 and runs; at 32,000 it is refused. Three older guard
tests re-sized to the new reserve (same assertions). Mutations R1-R7 after a control run.

PLEASE CHECK: (1) the reserve's arithmetic and that every paid call still reserves before it runs; (2) that nothing else
reads upper_usd as a strict bound; (3) the cap: sent to xAI, and on the breaker's runaway measure; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
