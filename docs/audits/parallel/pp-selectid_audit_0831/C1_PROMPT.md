# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0831
# Branch: pp-selectid
# Generated: 2026-11-13 08:31 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0831/C1_STEP.diff (150 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 49bfc9f..1eaba43 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -501,7 +501,7 @@ class Router:
   6 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
   7 |  
   8 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
   9 | -                 local_llm=None, chains=None, limit_basis="estimate"):
  10 | +                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0):
  11 |          with open(config) as f:
  12 |              self.config = json.load(f)
  13 |          self.env_path = env_path or ENV_PATH
  14 | @@ -509,6 +509,9 @@ class Router:
  15 |          if limit_basis not in ("estimate", "reported"):
  16 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  17 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  18 | +        import threading
  19 | +        self.deadline_log, self.slow_log_s = deadline_log, slow_log_s     # order 08:06 item 55: the evidence file
  20 | +        self._log_lock = threading.Lock()
  21 |          self.down, self.notices = {}, []
  22 |          self.backends = {}
  23 |          for name, spec in self.config["backends"].items():
  24 | @@ -578,6 +581,21 @@ class Router:
  25 |          with self._lock():
  26 |              return float(self._ledger()["usd_estimate"])
  27 |  
  28 | +    def _log_slow(self, rec):
  29 | +        """Order 08:06 item 55: one JSON line per call that missed its deadline or answered in >= slow_log_s, appended
  30 | +        to deadline_log (the evidence the Heimdall team gets). Evidence, never a gate: a write that fails becomes a
  31 | +        notice and the call goes on."""
  32 | +        if not self.deadline_log:
  33 | +            return
  34 | +        line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
  35 | +        try:
  36 | +            with self._log_lock:
  37 | +                os.makedirs(os.path.dirname(os.path.abspath(self.deadline_log)), exist_ok=True)
  38 | +                with open(self.deadline_log, "a") as f:
  39 | +                    f.write(line + "\n")
  40 | +        except OSError as e:
  41 | +            self.notices.append(f"the deadline log could not be written: {type(e).__name__}: {e}")
  42 | +
  43 |      def _basis_total(self, d):
  44 |          """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
  45 |          bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
  46 | @@ -726,6 +744,9 @@ class Router:
  47 |              except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
  48 |                  self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
  49 |                  tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
  50 | +                self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
  51 | +                                "deadline_s": deadline_s, "seconds": deadline_s, "prompt_chars": len(prompt),
  52 | +                                "max_tokens": max_tokens})
  53 |                  continue
  54 |              except RequestRejected as e:
  55 |                  self._settle(key)
  56 | @@ -741,6 +762,11 @@ class Router:
  57 |                  raise
  58 |              usd = b.usd(usage)
  59 |              self._settle(key, b, usage, usd, role)
  60 | +            if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
  61 | +                self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
  62 | +                                "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
  63 | +                                "prompt_chars": len(prompt), "max_tokens": max_tokens, "in": (usage or {}).get("in"),
  64 | +                                "out": (usage or {}).get("out")})
  65 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
  66 |                  tried.append((name, "refused this request: an empty reply"))
  67 |                  continue
  68 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  69 | index 637e675..1ea63a0 100644
  70 | --- a/tests/package/proof_ledger.py
  71 | +++ b/tests/package/proof_ledger.py
  72 | @@ -121,7 +121,7 @@ def main(argv=None):
  73 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  74 |                    f, indent=1, default=str)
  75 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  76 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains())
  77 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(), deadline_log=PL.DEADLINE_LOG)
  78 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
  79 |      if spent0 >= PL.LY_STOP_USD:
  80 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  81 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  82 | index c958eab..24e4276 100644
  83 | --- a/tests/package/proof_ly.py
  84 | +++ b/tests/package/proof_ly.py
  85 | @@ -52,6 +52,7 @@ LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate rea
  86 |  LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
  87 |                                     # Each paid call still RESERVES its price-table upper bound while in flight.
  88 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
  89 | +DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
  90 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
  91 |          "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
  92 |          "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
  93 | @@ -276,7 +277,7 @@ def main(argv=None):
  94 |          print(table())
  95 |          return 0
  96 |      router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD,
  97 | -                      limit_basis=LY_LIMIT_BASIS, chains=chains())
  98 | +                      limit_basis=LY_LIMIT_BASIS, chains=chains(), deadline_log=DEADLINE_LOG)
  99 |      own = meter(router)
 100 |      used = reply_meter(router)
 101 |      os.makedirs(a.work_dir, exist_ok=True)
 102 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 103 | index fb94590..0641fe9 100644
 104 | --- a/tests/providers/test_providers.py
 105 | +++ b/tests/providers/test_providers.py
 106 | @@ -89,9 +89,13 @@ class TestDeadline(unittest.TestCase):
 107 |              slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
 108 |              next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 109 |              r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
 110 | -                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0)
 111 | +                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0,
 112 | +                       deadline_log=os.path.join(d, "DEADLINES.jsonl"))
 113 |              t0 = _t.time()
 114 |              rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
 115 | +            log = [json.loads(x) for x in open(os.path.join(d, "DEADLINES.jsonl"))]       # item 55: the evidence
 116 | +            self.assertEqual([(x["kind"], x["model"], x["prompt_chars"], x["max_tokens"], x["deadline_s"]) for x in log],
 117 | +                             [("missed_deadline", "heimdall:deepseek", 1, 100, 0.3)])
 118 |              self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
 119 |              self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
 120 |              self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
 121 | @@ -102,6 +106,28 @@ class TestDeadline(unittest.TestCase):
 122 |                                     slow.upper_usd("p", 100), places=6)
 123 |              self.assertEqual(led["reserved"], {})                      # no reservation left behind
 124 |  
 125 | +    def test_item_55_a_slow_answer_is_logged_and_no_log_writes_nothing(self):
 126 | +        import tempfile
 127 | +        with tempfile.TemporaryDirectory() as d:
 128 | +            class Took(Fake):                                           # a back-end reports its own seconds
 129 | +                def complete(self, prompt, max_tokens, seed, system=None):
 130 | +                    text, usage, _ = super().complete(prompt, max_tokens, seed, system)
 131 | +                    return text, usage, 0.25
 132 | +            slow = Took("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek")
 133 | +            path = os.path.join(d, "DEADLINES.jsonl")
 134 | +            r = router(d, [slow], {"check": ["heimdall:deepseek"]}, deadline_log=path, slow_log_s=0.2)
 135 | +            r.call("check", "pp", 50, 7)                                # no deadline, answered in 0.25 s >= 0.2 s
 136 | +            log = [json.loads(x) for x in open(path)]
 137 | +            self.assertEqual([(x["kind"], x["prompt_chars"], x["in"], x["out"]) for x in log],
 138 | +                             [("answered_slowly", 2, 1000, 100)])
 139 | +            self.assertGreaterEqual(log[0]["seconds"], 0.2)
 140 | +            fast = Fake("heimdall:qwen", "heimdall", answer="{}")
 141 | +            router(d, [fast], {"check": ["heimdall:qwen"]}, deadline_log=path, slow_log_s=0.2).call("check", "p")
 142 | +            self.assertEqual(len(open(path).read().splitlines()), 1)   # a fast answer is not evidence
 143 | +            router(d, [Took("heimdall:x", "heimdall", answer="{}")], {"check": ["heimdall:x"]},
 144 | +                   slow_log_s=0.2).call("check", "p")                   # no deadline_log: nothing written
 145 | +            self.assertEqual(len(open(path).read().splitlines()), 1)
 146 | +
 147 |      def test_an_answer_inside_the_deadline_and_an_error_keep_their_meaning(self):
 148 |          import tempfile
 149 |          with tempfile.TemporaryDirectory() as d:
 150 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse). providers.Router calls paid model vendors in a
fail-over chain. A writer call has a deadline (300 s): a back-end that misses it is abandoned (DeadlineExceeded) and
the chain moves on. Your role: a strict reviewer of a new evidence log.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

The order this diff implements (ORCHESTRATOR 08:06 item 55, verbatim): "Heimdall deepseek and qwen both missed 300 s on
the angle step at 07:14, and one 8-excerpt screen took 8 min. Record every missed deadline (model, prompt size,
seconds) in one file for the Heimdall team; I owe PBX that evidence."
- Already done (data, not in this diff): docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.md + .jsonl, backfilled
  from the build records and the reply cache.

The change:
1. pipeline/providers.py:
   - Router(..., deadline_log=None, slow_log_s=240.0) and _log_slow(rec), which appends one JSON line (with a UTC
     stamp) to deadline_log under a threading.Lock;
   - when the call abandons a back-end at its deadline it logs {"kind": "missed_deadline", role, model, vendor,
     deadline_s, seconds, prompt_chars, max_tokens};
   - when a back-end answers in >= slow_log_s it logs {"kind": "answered_slowly", threshold_s, role, model, vendor,
     deadline_s, seconds, prompt_chars, max_tokens, in, out};
   - without deadline_log nothing is written. A failed write becomes a router notice and never fails the call: this
     is evidence, not a gate.
2. tests/package/proof_ly.py + proof_ledger.py: the order's Routers log to the evidence file's .jsonl (DEADLINE_LOG).
3. tests/providers/test_providers.py:
   - the existing deadline test also asserts the one missed_deadline line;
   - a new test: an answer of 0.25 s against a 0.2 s threshold is logged with its tokens; a fast answer is not; a
     Router with no deadline_log writes nothing.
- test_providers 16 OK; every other suite OK.

Check: every missed deadline is logged exactly once with the fields the order names; the log can never change a
call's outcome or the spend ledger; concurrent calls (the build calls the router from a thread pool) cannot interleave
lines; nothing secret (a key, a prompt's text) is written: only sizes.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

