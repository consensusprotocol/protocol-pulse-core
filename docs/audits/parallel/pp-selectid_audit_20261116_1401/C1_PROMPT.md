# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_1401
# Branch: pp-selectid
# Generated: 2026-11-16 14:01 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_1401/C1_STEP.diff (153 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 980c289..3814b5c 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -55,7 +55,8 @@
   6 |     "temperature": 0,
   7 |     "key_name": "XAI_API_KEY_MEDLEY",
   8 |     "family": "grok",
   9 | -   "max_out_cap": 12000
  10 | +   "max_out_cap": 12000,
  11 | +   "reserve_list_fraction": 0.25
  12 |    },
  13 |    "heimdall:qwen/qwen3.8-27b": {
  14 |     "vendor": "heimdall",
  15 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  16 | index a70cdb5..21184cd 100644
  17 | --- a/pipeline/providers.py
  18 | +++ b/pipeline/providers.py
  19 | @@ -999,6 +999,18 @@ class Router:
  20 |              return b.prompt_usd(prompt, system), "list"
  21 |          return round(rate * b.prompt_tokens_upper(prompt, system), 8), "reported_rate"
  22 |  
  23 | +    def _reserve_fraction(self, b):
  24 | +        """RULING 123 (1) (orchestrator 14:05 ET Nov 16): a back-end whose spec names reserve_list_fraction (Grok: 0.25)
  25 | +        is reserved at that fraction of its list-price reserve, until a call of it bills above that fraction of the list
  26 | +        price of what it used: then the day's ledger records the trip (reserve_tripped) and it is reserved at list for
  27 | +        the rest of that ledger's day (proof_ly.day_ledger: a ledger a day). -> the fraction, or None (list)."""
  28 | +        f = b.spec.get("reserve_list_fraction")
  29 | +        if not _num(f) or not self.spend_path:
  30 | +            return None
  31 | +        with self._lock():
  32 | +            d = self._ledger()
  33 | +        return None if (d.get("reserve_tripped") or {}).get(b.name) else float(f)
  34 | +
  35 |      def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
  36 |          """Release a reservation and account the call that answered (a free one too, when the ledger is readable).
  37 |          `unreported` (an abandoned call's booking, ruling 107 Q1) is what the cap's unreported estimate takes in place
  38 | @@ -1012,9 +1024,20 @@ class Router:
  39 |                  if key is None:
  40 |                      return                             # a free call: nothing to guard, nothing to write
  41 |                  raise
  42 | -            d["reserved"].pop(key, None)
  43 | +            held = d["reserved"].pop(key, None)
  44 |              if backend is not None:
  45 |                  usage = usage or {}
  46 | +                f = backend.spec.get("reserve_list_fraction")      # RULING 123 (1): the tripwire, after every call
  47 | +                if _num(f) and _num(usage.get("usd_reported")) and float(usage["usd_reported"]) > float(f) * usd and \
  48 | +                        not (d.get("reserve_tripped") or {}).get(backend.name):
  49 | +                    trip = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "role": role,
  50 | +                            "billed": round(float(usage["usd_reported"]), 6), "list": round(usd, 6),
  51 | +                            "fraction": float(f), "reserved": held,
  52 | +                            "why": f"billed above {float(f):.0%} of list: reserved at list for the rest of the day "
  53 | +                                   f"(ruling 123 (1))"}
  54 | +                    d.setdefault("reserve_tripped", {})[backend.name] = trip
  55 | +                    self.notices.append(f"RESERVE BACK TO LIST: {backend.name} {trip['why']}: billed "
  56 | +                                        f"${trip['billed']:.4f}, list ${trip['list']:.4f}")
  57 |                  b = d["by_backend"].setdefault(backend.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
  58 |                                                                "price_usd_per_1m": list(backend.price)})
  59 |                  b.update(calls=b["calls"] + 1, usd_estimate=round(b["usd_estimate"] + usd, 6),
  60 | @@ -1364,7 +1387,8 @@ class Router:
  61 |                  tried.append((name, bwhy))
  62 |                  continue
  63 |              upper = b.upper_usd(prompt, max_tokens, system)
  64 | -            key = self._reserve(b, upper)
  65 | +            frac = self._reserve_fraction(b)          # RULING 123 (1): Grok at 25 % of list until a call bills over it
  66 | +            key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)
  67 |              if isinstance(b, HeimdallBackend):
  68 |                  n = self.heimdall_tripwire()
  69 |                  if n:
  70 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  71 | index b41e97b..b627add 100644
  72 | --- a/tests/providers/test_providers.py
  73 | +++ b/tests/providers/test_providers.py
  74 | @@ -737,11 +737,13 @@ class TestRuling121Reserve(unittest.TestCase):
  75 |      tokens (step A's 4,000 x 8 was 32,000: $0.80 of Grok output at list, more than the day's $1.00 had left)."""
  76 |      REPLIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "package", "fixtures", "replies")
  77 |  
  78 | -    def xai(self, cap=True, answer='{"ok": true}'):
  79 | +    def xai(self, cap=True, answer='{"ok": true}', frac=True):
  80 |          spec = dict(json.load(open(os.path.join(os.path.dirname(P.__file__), "model_providers.json")))["backends"][
  81 |              "xai:grok-4.20-0309-reasoning"])
  82 |          if not cap:
  83 |              spec.pop("max_out_cap", None)
  84 | +        if not frac:                                  # at list (ruling 123 (1) then reserves Grok at 25 % of it)
  85 | +            spec.pop("reserve_list_fraction", None)
  86 |          b = P.XAIBackend("xai:grok-4.20-0309-reasoning", spec, "/nonexistent")
  87 |          b.sent = []
  88 |          b.key = lambda name: "k"
  89 | @@ -808,7 +810,7 @@ class TestRuling121Reserve(unittest.TestCase):
  90 |                  "calls": 1, "in": 0, "out": 0, "usd_estimate": 0.5835, "usd_reported": 0.5835}},
  91 |                  "by_role": {}, "reserved": {}, "usd_reported": 0.5835, "usd_unreported_estimate": 0.0}, open(led, "w"))
  92 |              for cap, fits in ((True, True), (False, False)):
  93 | -                b = self.xai(cap=cap)
  94 | +                b = self.xai(cap=cap, frac=False)     # ruling 121's check is at list
  95 |                  b.complete = lambda prompt, max_tokens, seed, system=None: ('{"ok": true}', {"in": 2000, "out": 3000}, 0.02)
  96 |                  r = router(d, [b], {"context_verdict": [b.name]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
  97 |                  if fits:
  98 | @@ -818,5 +820,54 @@ class TestRuling121Reserve(unittest.TestCase):
  99 |                          r.call("context_verdict", "p" * 7800, 4000)
 100 |  
 101 |  
 102 | +class TestRuling123Reserve(unittest.TestCase):
 103 | +    """RULING 123 (1) (orchestrator 14:05 ET Nov 16): Grok's reserve at 25 % of list (x 1.25 kept), with a tripwire: the
 104 | +    first call that bills above 25 % of the list price of what it used puts the reserve back to list for the rest of the
 105 | +    day (the day's ledger), written in that ledger and announced."""
 106 | +
 107 | +    def ledger(self, d, spent, name="led.json"):
 108 | +        led = os.path.join(d, name)
 109 | +        json.dump({"usd_estimate": spent, "calls": 1, "by_backend": {}, "by_role": {}, "reserved": {},
 110 | +                   "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 111 | +        return led
 112 | +
 113 | +    def grok(self, usd_reported):
 114 | +        g = Fake("xai:g", "xai", answer="{}", price=(5, 25), usage={"in": 1000, "out": 2000, "usd_reported": usd_reported})
 115 | +        g.spec["reserve_list_fraction"] = 0.25
 116 | +        return g
 117 | +
 118 | +    def test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day(self):
 119 | +        with tempfile.TemporaryDirectory() as d:
 120 | +            led = self.ledger(d, 0.69)
 121 | +            g = self.grok(0.01)                       # its usage at list: 1,000 x $5/M + 2,000 x $25/M = $0.055
 122 | +            r = router(d, [g], {"judge": ["xai:g"]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 123 | +            p = "p" * 3000                            # the reserve at list: 1.25 x (1,200 x $5/M + 12,000 x $25/M) = $0.38
 124 | +            self.assertAlmostEqual(g.upper_usd(p, 12000), 0.3825, places=6)
 125 | +            r.call("judge", p, 12000)                 # 0.69 + 0.38 > 1.00 at list; at 25 %: 0.69 + 0.096: it runs
 126 | +            r.call("judge", p, 12000)                 # billed $0.01 <= 25 % of $0.055: still 25 %
 127 | +            self.assertEqual((g.calls, json.load(open(led)).get("reserve_tripped")), (2, None))
 128 | +            g._usage = {"in": 1000, "out": 2000, "usd_reported": 0.02}     # billed above 25 % of list ($0.01375)
 129 | +            r.call("judge", p, 12000)
 130 | +            trip = json.load(open(led))["reserve_tripped"]["xai:g"]
 131 | +            self.assertEqual((trip["billed"], trip["list"], trip["fraction"], trip["reserved"]),
 132 | +                             (0.02, 0.055, 0.25, round(0.3825 * 0.25, 6)))
 133 | +            self.assertTrue(any(n.startswith("RESERVE BACK TO LIST: xai:g") for n in r.notices), r.notices)
 134 | +            with self.assertRaises(P.SpendLimit):     # 0.73 + the list reserve 0.38 > 1.00: refused, for the day
 135 | +                r.call("judge", p, 12000)
 136 | +            self.assertEqual(g.calls, 3)
 137 | +            day2 = router(d, [g], {"judge": ["xai:g"]}, spend_path=self.ledger(d, 0.69, "day2.json"), limit_usd=1.0,
 138 | +                          limit_basis="reported")
 139 | +            day2.call("judge", p, 12000)              # a new day's ledger: 25 % again
 140 | +            self.assertEqual(g.calls, 4)
 141 | +
 142 | +    def test_only_a_back_end_that_names_the_fraction_is_reserved_below_list(self):
 143 | +        with tempfile.TemporaryDirectory() as d:
 144 | +            led = self.ledger(d, 0.69)
 145 | +            o = Fake("openai:o", "openai", answer="{}", price=(5, 25), usage={"in": 10, "out": 10, "usd_reported": 0.0})
 146 | +            r = router(d, [o], {"judge": ["openai:o"]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 147 | +            with self.assertRaises(P.SpendLimit):
 148 | +                r.call("judge", "p" * 3000, 12000)    # list: 0.69 + 0.38 > 1.00
 149 | +
 150 | +
 151 |  if __name__ == "__main__":
 152 |      unittest.main()
 153 | 
```

---

pp-selectid: RULING 123 (1) (orchestrator 14:05 ET Nov 16), GROK'S RESERVE AT 25 % OF LIST, WITH A TRIPWIRE. Files:
pipeline/providers.py (Router._reserve_fraction; Router.call takes the reserve through it; Router._settle's tripwire),
pipeline/model_providers.json (one key on the xAI reasoning back-end), tests/providers/test_providers.py.

THE ORDER, verbatim: "(1) THE RESERVE: YES. Price Grok's reserve at 25 % of list (x 1.25 kept), on your evidence: all 127
calls since Nov 15 billed 9-12 % of list, the dearest $0.029. WITH A TRIPWIRE: after every outside call compare what was
billed with what was reserved; the first call that bills above 25 % of list puts the reserve back to list at once, for the
rest of the day, and writes it on line 1. The worst case is one call's overshoot (about $0.25) on a day xAI changes its
billing; PBX's dollar is a target he asked me to hold without lowering quality or losing the day, and I accept that tail
for a video today. Audit-first on Heimdall."

THE CHANGE: a back-end whose spec names reserve_list_fraction (the xAI reasoning back-end: 0.25) is reserved at that
fraction of its reserve (upper_usd: ruling 121's characters / 3, its real cap, list, x 1.25), unless the day's ledger
records a trip for it (reserve_tripped[name]). After every call of it that reports a cost, _settle compares the billed
figure with that fraction of the LIST price of what the call used (b.usd(usage)); the first call above it writes
reserve_tripped[name] = {at, role, billed, list, fraction, reserved, why} into the ledger (under the ledger lock, as every
ledger write) and a "RESERVE BACK TO LIST" notice; from then that back-end is reserved at list until the ledger changes
(proof_ly.day_ledger: one ledger a day, 21:10 ET to 21:10 ET). The builder writes the trip on STATE line 1 (its day
keeper reads the ledger). Every other back-end, the cap ($1.00 a day, outside vendors only) and the reservation's
take-settle-release cycle are unchanged (unchanged guards: Router._reserve, the ledger lock, Heimdall uncapped).

TESTS (TestRuling123Reserve): with $0.69 spent of $1.00, a call whose list reserve ($0.38) does not fit runs at 25 %; two
calls billing under 25 % of list keep it; the first billing above it trips (recorded with billed, list, fraction,
reserved; announced); the next call is reserved at list and refused; a new day's ledger is at 25 % again; a back-end
without the key stays at list. Ruling 121's fit test now runs at list (its own check). Mutations Q1-Q4 after a control.

PLEASE CHECK: (1) the tripwire's comparison and that it cannot be missed; (2) that the trip holds for the day; (3) that
nothing but the named back-end changes; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
