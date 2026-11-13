# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0707
# Branch: pp-selectid
# Generated: 2026-11-13 07:08 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0707/C1_STEP.diff (170 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index e65bca1..27fc5f4 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -501,11 +501,14 @@ class Router:
   6 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
   7 |  
   8 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
   9 | -                 local_llm=None, chains=None):
  10 | +                 local_llm=None, chains=None, limit_basis="estimate"):
  11 |          with open(config) as f:
  12 |              self.config = json.load(f)
  13 |          self.env_path = env_path or ENV_PATH
  14 |          self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
  15 | +        if limit_basis not in ("estimate", "reported"):
  16 | +            raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  17 | +        self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  18 |          self.down, self.notices = {}, []
  19 |          self.backends = {}
  20 |          for name, spec in self.config["backends"].items():
  21 | @@ -575,16 +578,34 @@ class Router:
  22 |          with self._lock():
  23 |              return float(self._ledger()["usd_estimate"])
  24 |  
  25 | +    def _basis_total(self, d):
  26 | +        """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
  27 | +        bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
  28 | +        estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
  29 | +        its deadline, booked at its upper bound)."""
  30 | +        if self.limit_basis == "reported":
  31 | +            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
  32 | +        return float(d["usd_estimate"])
  33 | +
  34 | +    def spent(self):
  35 | +        """The ledger's total on this router's limit basis (0.0 with no ledger; raises SpendLimit when unreadable)."""
  36 | +        if not self.spend_path:
  37 | +            return 0.0
  38 | +        with self._lock():
  39 | +            return self._basis_total(self._ledger())
  40 | +
  41 |      def _reserve(self, b, upper):
  42 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  43 | -        SpendLimit when spent + reserved + this call's upper bound would pass the limit."""
  44 | +        SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  45 | +        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late."""
  46 |          if not self.spend_path or b.free():
  47 |              return None
  48 |          with self._lock():
  49 |              d = self._ledger()
  50 |              held = sum(float(x) for x in d["reserved"].values())
  51 | -            if d["usd_estimate"] + held + upper > self.limit_usd:
  52 | -                raise SpendLimit(f"spend estimate {d['usd_estimate']:.2f} USD + reserved {held:.2f} + this call's upper "
  53 | +            spent = self._basis_total(d)
  54 | +            if spent + held + upper > self.limit_usd:
  55 | +                raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's upper "
  56 |                                   f"bound {upper:.2f} > the limit {self.limit_usd} USD")
  57 |              key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  58 |              d["reserved"][key] = round(upper, 6)
  59 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  60 | index 44aaa8e..021086f 100644
  61 | --- a/tests/package/proof_ledger.py
  62 | +++ b/tests/package/proof_ledger.py
  63 | @@ -121,7 +121,15 @@ def main(argv=None):
  64 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  65 |                    f, indent=1, default=str)
  66 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  67 | -                      chains=PL.chains())
  68 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains())
  69 | +    spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
  70 | +    if spent0 >= PL.LY_STOP_USD:
  71 | +        say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  72 | +            f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator decides")
  73 | +        logf.close()
  74 | +        return 3
  75 | +    say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
  76 | +        f"starts at ${PL.LY_STOP_USD:.2f})")
  77 |      own, used = PL.meter(router), PL.reply_meter(router)
  78 |      t0 = time.time()
  79 |      res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
  80 | @@ -144,6 +152,10 @@ def main(argv=None):
  81 |              say(f"PIN REFUSED: {e}")
  82 |      else:
  83 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
  84 | +    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": round(router.spent(), 4), "cap": PL.LY_LIMIT_USD,
  85 | +                              "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
  86 | +    say(f"  spend (ruling 48): ${res['spend_ruling_48']['after']:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported after "
  87 | +        f"this build (${res['spend_ruling_48']['after'] - spent0:.2f} spent by it)")
  88 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
  89 |          json.dump(res, f, indent=1, default=str)
  90 |      logf.close()
  91 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  92 | index 75193f6..c958eab 100644
  93 | --- a/tests/package/proof_ly.py
  94 | +++ b/tests/package/proof_ly.py
  95 | @@ -18,8 +18,9 @@ is out too. What is left:
  96 |  CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
  97 |  
  98 |  SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
  99 | -vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
 100 | -estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
 101 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
 102 | +its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
 103 | +(Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.
 104 |  
 105 |  Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
 106 |  """
 107 | @@ -46,10 +47,10 @@ import speakers as SP  # noqa: E402
 108 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 109 |  OUT = os.path.join(HERE, "proof")
 110 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 111 | -LY_LIMIT_USD = 40.0                # the price-table estimate (an upper bound): xAI's own figure ran 1/8 of it on
 112 | -                                   # this order's first calls (estimate $0.636 vs reported $0.078 for 3 grok calls),
 113 | -                                   # so about $5 real; each paid call also RESERVES its upper bound (~$0.26-0.96)
 114 | -                                   # while in flight, and three workers run concurrently
 115 | +LY_LIMIT_USD = 12.0                # ruling 48 (07:02 Nov 13): $12.00 VENDOR-REPORTED in total for this order (the
 116 | +LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate read ~12x high: $39.49 = $3.46 reported);
 117 | +LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
 118 | +                                   # Each paid call still RESERVES its price-table upper bound while in flight.
 119 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 120 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
 121 |          "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
 122 | @@ -274,7 +275,8 @@ def main(argv=None):
 123 |      if a.table:
 124 |          print(table())
 125 |          return 0
 126 | -    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
 127 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD,
 128 | +                      limit_basis=LY_LIMIT_BASIS, chains=chains())
 129 |      own = meter(router)
 130 |      used = reply_meter(router)
 131 |      os.makedirs(a.work_dir, exist_ok=True)
 132 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 133 | index fca9414..438e1f9 100644
 134 | --- a/tests/providers/test_providers.py
 135 | +++ b/tests/providers/test_providers.py
 136 | @@ -185,6 +185,33 @@ class TestRouter(unittest.TestCase):
 137 |              a.answer = '{"ok": 1}'
 138 |              self.assertEqual((r.call("write", "p").text, a.calls), ('{"ok": 1}', 2))
 139 |  
 140 | +    def test_ruling_48_the_limit_counts_vendor_reported_dollars(self):
 141 | +        """Ruling 48 (07:02 Nov 13): the cap counts the vendors' own reported dollars, plus the estimate for a call
 142 | +        whose vendor reports none; the price-table estimate (12x high on xAI) no longer binds."""
 143 | +        with tempfile.TemporaryDirectory() as d:
 144 | +            led = os.path.join(d, "SPEND.json")
 145 | +            json.dump({"usd_estimate": 39.5, "calls": 400, "by_backend": {}, "by_role": {}, "reserved": {},
 146 | +                       "usd_reported": 3.46, "usd_unreported_estimate": 1.81}, open(led, "w"))
 147 | +            a = Fake("openai:x", "openai", answer="{}", usage={"in": 1000, "out": 100})        # no vendor figure
 148 | +            rep = Fake("openai:y", "openai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
 149 | +            p = "p" * 50_000
 150 | +            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
 151 | +                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
 152 | +            r = router(d, [a, rep], {"write": ["openai:x"], "judge": ["openai:y"]}, spend_path=led, limit_usd=12,
 153 | +                       limit_basis="reported")
 154 | +            self.assertAlmostEqual(r.spent(), 5.27, places=6)
 155 | +            r.call("write", p)                                      # 5.27 + its upper bound < 12: it runs
 156 | +            self.assertAlmostEqual(r.spent(), 5.27 + 0.02, places=6)                 # no figure: its estimate counts
 157 | +            r.call("judge", p)
 158 | +            self.assertAlmostEqual(r.spent(), 5.29 + 0.001, places=6)                # a figure: only the figure counts
 159 | +            self.assertGreater(json.load(open(led))["usd_estimate"], 39.5)
 160 | +            r.limit_usd = r.spent() + 0.05
 161 | +            with self.assertRaises(P.SpendLimit):                   # spent + this call's upper bound > the limit
 162 | +                r.call("write", p)
 163 | +            self.assertEqual(json.load(open(led))["reserved"], {})
 164 | +            with self.assertRaises(ValueError):
 165 | +                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_basis="dollars")
 166 | +
 167 |      def test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit(self):
 168 |          with tempfile.TemporaryDirectory() as d:
 169 |              led = os.path.join(d, "SPEND.json")
 170 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging). This branch's builds call
paid model vendors through providers.Router, which books every call in a spend ledger (SPEND_LY.json) and refuses a
call that would pass a limit. Your role: a strict reviewer of the spend guard.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- The ledger keeps, per call, the price-table ESTIMATE (usd_estimate: every call, an upper bound) and, separately, the
  vendor's OWN reported cost where the reply carries one (usd_reported: xAI cost_in_usd_ticks, Heimdall usage.cost),
  else the estimate for that call (usd_unreported_estimate: calls with no vendor figure, e.g. speech-to-text, and calls
  abandoned at a deadline, booked at their upper bound). Router._settle maintains all three.
- Before a paid call, Router._reserve reserves the call's price-table upper bound under a file lock and refuses it
  (SpendLimit) when spent + reserved + upper > limit_usd. Until this diff, "spent" was always usd_estimate.
- The build driver (tests/package/proof_ledger.py) and the saved-runs driver (proof_ly.py) construct the Router for
  this order with limit_usd = LY_LIMIT_USD (was 40.0, by the estimate).

The order this diff implements (ORCHESTRATOR RULING 48, 07:02 ET Nov 13, verbatim): "SPEND. The cap is on
VENDOR-REPORTED dollars, not the price-table estimate (the estimate reads 12x high: $40 estimated = $3.46 reported).
New cap for this fresh batch: $12.00 vendor-reported in total, from where you stand ($3.46 used). For calls where a
vendor reports no cost, count the estimate for that call only. Keep the running total on STATE line 1 with every
build: reported / cap. At $10 reported stop and tell me."
- Measured before this diff: usd_estimate $39.49, usd_reported $3.46, usd_unreported_estimate $1.81 (STT and calls
  abandoned at the 300 s deadline). So the running total by the ruling's own rule is $5.26, not $3.46; STATE says so.

The change:
1. pipeline/providers.py:
   - Router(..., limit_basis="estimate"): "estimate" keeps the old behaviour for every other caller (the default);
     "reported" checks usd_reported + usd_unreported_estimate; anything else raises ValueError.
   - _basis_total(d) computes the basis; spent() returns it under the ledger lock.
   - _reserve compares spent-on-the-basis + reserved + upper with limit_usd. Reservations stay price-table upper
     bounds, so the guard can only stop early, never late.
2. tests/package/proof_ly.py: LY_LIMIT_USD = 12.0, LY_LIMIT_BASIS = "reported", LY_STOP_USD = 10.0; proof_ly's own
   Router uses the basis.
3. tests/package/proof_ledger.py (one build): the Router uses the basis. Before the build: at or over LY_STOP_USD it
   logs REFUSED and exits 3, with no paid call. Else it logs the running total. After the build it logs and records
   spend_ruling_48 {before, after, cap, stop, basis} in package.json. A build that starts below $10 may still spend
   up to its own per-build budget (ruling 41: $3.00 reported for the search); the Router's $12 cap is the hard stop.
4. tests/providers/test_providers.py: one new test. The old basis refuses at 39.5 + upper > 40. The reported basis
   reads 5.27 and lets a call run. A call with no vendor figure adds its estimate; a call with a figure adds only the
   figure. The limit refuses at spent + upper; reservations are released; an unknown basis is refused.

Check in particular:
- that the reported basis counts every call exactly once (reported OR its estimate), never zero for a paid call, and
  that the lock and reservation logic are unchanged;
- that nothing else changes for callers that do not pass limit_basis;
- that a build can never start at or over $10, and that the hard cap is $12 on the ruling's basis;
- whether "at $10 reported stop" is satisfied by refusing to START a build at $10 while a running build may continue
  to the $12 cap (bounded by its own $3 reported search budget). Say so if you read the ruling differently.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

