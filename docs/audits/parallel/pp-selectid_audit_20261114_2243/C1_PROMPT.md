# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2243
# Branch: pp-selectid
# Generated: 2026-11-14 22:44 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2243/C1_STEP.diff (311 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 44468d7..37b1816 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -69,6 +69,9 @@ class ReplayMiss(Exception):
   6 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
   7 |  RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
   8 |                                       # the model's own reported rate once it has this many reported calls
   9 | +RESERVE_WAIT_S = 600.0               # BATCH 3 (Nov 14): a paid call whose own upper bound fits under the limit and is
  10 | +RESERVE_POLL_S = 1.0                 # kept out only by the reservations of calls IN FLIGHT waits up to this long for
  11 | +                                     # them to settle, re-reading the ledger every RESERVE_POLL_S (Router._reserve)
  12 |  
  13 |  
  14 |  def is_vision(prompt):
  15 | @@ -734,6 +737,7 @@ class Router:
  16 |          if limit_basis not in ("estimate", "reported"):
  17 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  18 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  19 | +        self.reserve_wait_s, self.reserve_poll_s = RESERVE_WAIT_S, RESERVE_POLL_S   # _reserve's wait for calls in flight
  20 |          import threading
  21 |          self.deadline_log, self.slow_log_s = deadline_log, slow_log_s     # order 08:06 item 55: the evidence file
  22 |          self._log_lock = threading.Lock()
  23 | @@ -888,20 +892,34 @@ class Router:
  24 |      def _reserve(self, b, upper):
  25 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  26 |          SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  27 | -        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late."""
  28 | +        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late.
  29 | +        When spent + this call's upper bound fits and only the reservations of calls IN FLIGHT stand in the way, the call
  30 | +        waits for them to settle (each ends in an answer, an error or an abandonment, and releases its reservation),
  31 | +        re-reading the ledger every reserve_poll_s, and reserves once it fits; still kept out after reserve_wait_s, it
  32 | +        is refused (fail closed). Spend alone over the limit is refused at once. Batch 3's builds 1 and 2 (Nov 14) held
  33 | +        28 moments at step A (47 holds in all) without this wait: six step-A workers, each reserving about $0.85, under
  34 | +        a $4.50 limit with $0.27 spent; four fit, and the other workers were refused batch after batch while those four
  35 | +        ran."""
  36 |          if not self.spend_path or b.free():
  37 |              return None
  38 | -        with self._lock():
  39 | -            d = self._ledger()
  40 | -            held = sum(float(x) for x in d["reserved"].values())
  41 | -            spent = self._basis_total(d)
  42 | -            if spent + held + upper > self.limit_usd:
  43 | -                raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's upper "
  44 | -                                 f"bound {upper:.2f} > the limit {self.limit_usd} USD")
  45 | -            key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  46 | -            d["reserved"][key] = round(upper, 6)
  47 | -            self._save(d)
  48 | -        return key
  49 | +        t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
  50 | +        while True:
  51 | +            with self._lock():
  52 | +                d = self._ledger()
  53 | +                held = sum(float(x) for x in d["reserved"].values())
  54 | +                spent = self._basis_total(d)
  55 | +                if spent + held + upper <= self.limit_usd:
  56 | +                    key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  57 | +                    d["reserved"][key] = round(upper, 6)
  58 | +                    self._save(d)
  59 | +                    return key
  60 | +                if spent + upper > self.limit_usd or time.time() >= t_end:
  61 | +                    raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's "
  62 | +                                     f"upper bound {upper:.2f} > the limit {self.limit_usd} USD" +
  63 | +                                     (f" (still, after waiting {self.reserve_wait_s:g} s for the calls in flight)"
  64 | +                                      if waited else ""))
  65 | +            waited = True
  66 | +            time.sleep(max(0.01, float(self.reserve_poll_s)))
  67 |  
  68 |      def reported_rate(self, name):
  69 |          """RULING 107 Q1 (orchestrator 20:40 ET Nov 14): the model's own recorded vendor cost per PROMPT token: its
  70 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  71 | index 5dcf21f..bd6a3df 100644
  72 | --- a/tests/package/proof_ly.py
  73 | +++ b/tests/package/proof_ly.py
  74 | @@ -108,17 +108,22 @@ def ledger():
  75 |  def meter(router):
  76 |      """THIS process's own spend, from every call the router accounts (Router._settle). The shared ledger's total moves
  77 |      with the other workers too, so a per-package budget read from it would charge one universe for another's calls.
  78 | -    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}."""
  79 | +    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}.
  80 | +    Every keyword the router's own _settle takes is passed on unchanged: the meter observes, it never stands between
  81 | +    a call and its booking. Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) lost three abandoned calls' bookings
  82 | +    and held three moments (four holds) because this wrapper refused ruling 107 Q1's `unreported` (a TypeError in
  83 | +    place of the failover). An abandoned call counts in "best" at that booking, as the cap counts it; a late answer that replaces
  84 | +    the booking (Router._replace_booking) is not followed here."""
  85 |      import threading
  86 |      tot, lock, settle = {"est": 0.0, "best": 0.0}, threading.Lock(), router._settle
  87 |  
  88 | -    def _settle(key, backend=None, usage=None, usd=0.0, role=""):
  89 | -        settle(key, backend, usage, usd, role)
  90 | +    def _settle(key, backend=None, usage=None, usd=0.0, role="", **kw):
  91 | +        settle(key, backend, usage, usd, role, **kw)
  92 |          if backend is not None:
  93 | -            rep = (usage or {}).get("usd_reported")
  94 | +            rep, booked = (usage or {}).get("usd_reported"), kw.get("unreported")
  95 |              with lock:
  96 |                  tot["est"] += float(usd or 0.0)
  97 | -                tot["best"] += float(rep) if P._num(rep) else float(usd or 0.0)
  98 | +                tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)
  99 |      router._settle = _settle
 100 |      return tot
 101 |  
 102 | diff --git a/tests/package/test_meter.py b/tests/package/test_meter.py
 103 | new file mode 100644
 104 | index 0000000..275232d
 105 | --- /dev/null
 106 | +++ b/tests/package/test_meter.py
 107 | @@ -0,0 +1,64 @@
 108 | +#!/usr/bin/env python3
 109 | +"""proof_ly.meter observes the router's accounting and never stands between a call and its booking. Batch 3's builds 1
 110 | +and 2 (22:05 and 22:20 ET Nov 14): the meter's wrapper refused ruling 107 Q1's `unreported` keyword, so a call abandoned
 111 | +at its deadline raised TypeError in place of failing over to the next leg; its booking never reached the ledger, its
 112 | +late answer was never accounted and its moments were held. Offline: the real Router over fake legs, a temporary ledger
 113 | +and deadline log."""
 114 | +import json
 115 | +import os
 116 | +import sys
 117 | +import tempfile
 118 | +import unittest
 119 | +
 120 | +HERE = os.path.dirname(os.path.abspath(__file__))
 121 | +REPO = os.path.dirname(os.path.dirname(HERE))
 122 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 123 | +    sys.path.insert(0, os.path.join(REPO, _p))
 124 | +import proof_ly as PL  # noqa: E402
 125 | +from test_providers import Fake, SlowFail, router, wait_for  # noqa: E402
 126 | +from test_ruling_107 import LIST, TOKENS, seed  # noqa: E402
 127 | +
 128 | +QWEN_LIST = 1000 * 10 / 1e6 + 100 * 100 / 1e6          # Fake's list price for qwen's 1,000 in / 100 out
 129 | +
 130 | +
 131 | +def metered_miss(d, **seeded):
 132 | +    """One call through a METERED router: deepseek passes its 0.2 s deadline (and fails later), qwen answers with the
 133 | +    vendor's own figure. -> (reply, the meter, the ledger, the deadline log once the abandoned thread has ended)."""
 134 | +    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 135 | +    seed(spend, **seeded)
 136 | +    slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.4, family="deepseek")
 137 | +    qwen = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 138 | +                usage={"in": 1000, "out": 100, "usd_reported": 0.002})
 139 | +    r = router(d, [slow, qwen], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
 140 | +               limit_usd=50.0, limit_basis="reported", deadline_log=log)
 141 | +    own = PL.meter(r)
 142 | +    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
 143 | +    lines = wait_for(log, "late_error")                # ruling 83 (a)'s late path ran: the abandonment was booked
 144 | +    return rep, own, json.load(open(spend)), lines
 145 | +
 146 | +
 147 | +class TestTheMeterNeverStandsBetweenACallAndItsBooking(unittest.TestCase):
 148 | +
 149 | +    def test_a_missed_deadline_through_the_meter_fails_over_and_is_booked(self):
 150 | +        with tempfile.TemporaryDirectory() as d:
 151 | +            rep, own, led, log = metered_miss(d)
 152 | +            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))     # failed over: no TypeError
 153 | +            self.assertIn("abandoned at the deadline", rep.tried[0][1])
 154 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)          # the booking is in the ledger
 155 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
 156 | +            self.assertEqual([x["kind"] for x in log if x["kind"] in ("missed_deadline", "late_error")],
 157 | +                             ["missed_deadline", "late_error"])
 158 | +            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                  # this process's two calls
 159 | +
 160 | +    def test_the_meter_counts_an_abandoned_call_at_the_booking_the_cap_counts(self):
 161 | +        with tempfile.TemporaryDirectory() as d:        # three reported calls: deepseek's booking is at its own rate
 162 | +            rep, own, led, log = metered_miss(d, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 163 | +                                              in_reported=3000)
 164 | +            booked = 0.003 / 3000 * TOKENS
 165 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
 166 | +            self.assertAlmostEqual(own["best"], booked + 0.002, places=9)                    # as the cap reads it
 167 | +            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                   # est stays list price
 168 | +
 169 | +
 170 | +if __name__ == "__main__":
 171 | +    unittest.main()
 172 | diff --git a/tests/providers/test_reserve_wait.py b/tests/providers/test_reserve_wait.py
 173 | new file mode 100644
 174 | index 0000000..503d235
 175 | --- /dev/null
 176 | +++ b/tests/providers/test_reserve_wait.py
 177 | @@ -0,0 +1,133 @@
 178 | +#!/usr/bin/env python3
 179 | +"""The spend guard waits for calls IN FLIGHT; it never passes the limit and never refuses a call that fits once they
 180 | +settle. Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) held 28 moments at step A: six workers in parallel, each
 181 | +reserving its price-table upper bound (about $0.85) under a $4.50 limit with $0.27 spent, so four fit and the other
 182 | +two were refused batch after batch while those four ran. Offline: the real Router over fake back-ends, real threads,
 183 | +a temporary ledger."""
 184 | +import json
 185 | +import os
 186 | +import sys
 187 | +import tempfile
 188 | +import threading
 189 | +import time
 190 | +import unittest
 191 | +
 192 | +HERE = os.path.dirname(os.path.abspath(__file__))
 193 | +REPO = os.path.dirname(os.path.dirname(HERE))
 194 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 195 | +sys.path.insert(0, HERE)
 196 | +import providers as P  # noqa: E402
 197 | +from test_providers import Fake, router  # noqa: E402
 198 | +
 199 | +U = (1 + 200) * 10 / 1e6 + 1000 * 100 / 1e6     # Fake's upper bound for prompt "p" and max_tokens 1000: $0.10201
 200 | +U_SMALL = (1 + 200) * 10 / 1e6 + 10 * 100 / 1e6  # max_tokens 10: $0.00301
 201 | +
 202 | +
 203 | +class Gate(Fake):
 204 | +    """A back-end whose call stays in flight (its reservation held) until `release` is set; `track` counts how many of
 205 | +    its calls are in flight at once."""
 206 | +
 207 | +    def __init__(self, name, release, track):
 208 | +        super().__init__(name, "openai", answer='{"ok": 1}', usage={"in": 10, "out": 10, "usd_reported": 0.0001})
 209 | +        self.release, self.track = release, track
 210 | +
 211 | +    def complete(self, prompt, max_tokens, seed, system=None):
 212 | +        with self.track["lock"]:
 213 | +            self.track["now"] += 1
 214 | +            self.track["max"] = max(self.track["max"], self.track["now"])
 215 | +        try:
 216 | +            if not self.release.wait(10):
 217 | +                raise P.Unavailable("the test never released this call")
 218 | +            return super().complete(prompt, max_tokens, seed, system)
 219 | +        finally:
 220 | +            with self.track["lock"]:
 221 | +                self.track["now"] -= 1
 222 | +
 223 | +
 224 | +def guarded(d, limit, spent=0.0, wait_s=10.0):
 225 | +    """A router on a ledger with `spent` reported dollars, the guard at `limit`, one Gate back-end."""
 226 | +    led = os.path.join(d, "SPEND.json")
 227 | +    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
 228 | +               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 229 | +    release, track = threading.Event(), {"lock": threading.Lock(), "now": 0, "max": 0}
 230 | +    g = Gate("openai:g", release, track)
 231 | +    r = router(d, [g], {"check": ["openai:g"]}, spend_path=led, limit_usd=limit, limit_basis="reported")
 232 | +    r.reserve_wait_s, r.reserve_poll_s = wait_s, 0.02
 233 | +    return r, g, release, track, led
 234 | +
 235 | +
 236 | +def run(r, results, i, max_tokens=1000):
 237 | +    t0 = time.time()
 238 | +    try:
 239 | +        results[i] = ("answer", r.call("check", "p", max_tokens, i).text, time.time() - t0)
 240 | +    except P.SpendLimit as e:
 241 | +        results[i] = ("refused", str(e), time.time() - t0)
 242 | +
 243 | +
 244 | +class TestTheGuardWaitsForCallsInFlight(unittest.TestCase):
 245 | +
 246 | +    def test_six_workers_with_room_for_four_all_answer_and_never_more_than_four_run(self):
 247 | +        with tempfile.TemporaryDirectory() as d:          # the batch-3 case: room for four upper bounds, six workers
 248 | +            r, g, release, track, led = guarded(d, limit=4.5 * U)
 249 | +            results = {}
 250 | +            ts = [threading.Thread(target=run, args=(r, results, i)) for i in range(6)]
 251 | +            for t in ts:
 252 | +                t.start()
 253 | +            time.sleep(0.4)
 254 | +            self.assertEqual(track["now"], 4)               # four in flight, two waiting: none refused
 255 | +            self.assertEqual(results, {})
 256 | +            held = json.load(open(led))["reserved"]
 257 | +            self.assertEqual(len(held), 4)
 258 | +            self.assertLessEqual(sum(held.values()), 4.5 * U)
 259 | +            release.set()
 260 | +            for t in ts:
 261 | +                t.join(10)
 262 | +            self.assertEqual(sorted(v[0] for v in results.values()), ["answer"] * 6)
 263 | +            self.assertEqual((g.calls, track["max"]), (6, 4))
 264 | +            final = json.load(open(led))
 265 | +            self.assertEqual(final["reserved"], {})
 266 | +            self.assertAlmostEqual(final["usd_reported"], 6 * 0.0001, places=9)
 267 | +
 268 | +    def test_a_call_kept_out_by_spend_alone_is_refused_at_once_even_with_a_call_in_flight(self):
 269 | +        with tempfile.TemporaryDirectory() as d:          # 0.01 spent: the small call fits, the large one never will
 270 | +            r, g, release, track, led = guarded(d, limit=0.1, spent=0.01, wait_s=5.0)
 271 | +            results = {}
 272 | +            small = threading.Thread(target=run, args=(r, results, 0, 10))
 273 | +            small.start()
 274 | +            time.sleep(0.2)
 275 | +            self.assertEqual(track["now"], 1)
 276 | +            run(r, results, 1)                              # 0.01 + its upper bound $0.102 > $0.10
 277 | +            kind, why, secs = results[1]
 278 | +            self.assertEqual(kind, "refused")
 279 | +            self.assertLess(secs, 1.0)                      # no wait: no call settling could let it in
 280 | +            self.assertNotIn("after waiting", why)
 281 | +            release.set()
 282 | +            small.join(10)
 283 | +            self.assertEqual(results[0][0], "answer")
 284 | +
 285 | +    def test_a_call_still_kept_out_when_its_wait_ends_is_refused_and_the_limit_is_never_passed(self):
 286 | +        with tempfile.TemporaryDirectory() as d:          # room for one upper bound and a half
 287 | +            r, g, release, track, led = guarded(d, limit=1.5 * U, wait_s=0.4)
 288 | +            results = {}
 289 | +            first = threading.Thread(target=run, args=(r, results, 0))
 290 | +            first.start()
 291 | +            time.sleep(0.15)
 292 | +            second = threading.Thread(target=run, args=(r, results, 1))
 293 | +            second.start()
 294 | +            time.sleep(0.15)
 295 | +            self.assertEqual(len(json.load(open(led))["reserved"]), 1)    # while it waits: never two reservations
 296 | +            second.join(3)
 297 | +            self.assertFalse(second.is_alive())
 298 | +            kind, why, secs = results[1]
 299 | +            self.assertEqual(kind, "refused")
 300 | +            self.assertIn("after waiting", why)
 301 | +            self.assertGreaterEqual(secs, 0.4)
 302 | +            self.assertEqual(g.calls, 0)                    # nothing answered yet: the first call is still in flight
 303 | +            release.set()
 304 | +            first.join(10)
 305 | +            self.assertEqual((results[0][0], g.calls, track["max"]), ("answer", 1, 1))
 306 | +            self.assertEqual(json.load(open(led))["reserved"], {})
 307 | +
 308 | +
 309 | +if __name__ == "__main__":
 310 | +    unittest.main()
 311 | 
```

---

pp-selectid, two defects found in batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14), each fixed at its root. Both
builds held moments at step A's first screen ("no step-A verdict ... held for this build, retried next build", ruling
102): 28 distinct moments (47 holds) by SpendLimit and 3 moments (4 holds) by a TypeError. No refusal, no wrong pass.

DEFECT 1 (tests/package/proof_ly.py meter()): the wrapper it puts over Router._settle had the old signature
(key, backend, usage, usd, role). Ruling 107 Q1 (commit e7f68e11) made the router's abandon() call
self._settle(key, b, {"in": 0, "out": 0}, listed, role, unreported=booked) (base pipeline/providers.py:1327). In a
metered build each call abandoned at its deadline raised TypeError inside on_abandon. _within (base providers.py:
347-378, UNCHANGED) lets that exception propagate in place of DeadlineExceeded and never sets box["abandoned"], so:
no failover to the next leg; the booking never reached the ledger; on_late never ran. Router.call's
`except BaseException: self._settle(key); raise` (base providers.py:1356-1358, UNCHANGED) released the reservation.
Three glm calls lost their bookings ($0.086 at list, from the deadline log).
FIX: the wrapper passes every keyword on (**kw) and counts an abandoned call in "best" at the booking
(kw["unreported"]), as the router's _settle counts it on the cap's basis (base providers.py:975-976).

DEFECT 2 (pipeline/providers.py Router._reserve): batch 3's build cap is LY_LIMIT_USD = 4.50 on the reported basis
(tests/package/proof_ly.py, UNCHANGED). Each paid call reserves its price-table upper bound (a Grok step-A call about
$0.85: prompt + 8 x max_tokens of reasoning output, XAIBackend.max_out base providers.py:445-446). Step A runs six
batches in parallel (package.PRESCREEN_WORKERS = 6, base pipeline/package.py:77, ThreadPoolExecutor at :588). With
$0.27 spent four calls fit; _reserve refused the fifth and sixth AT ONCE ("spend 0.27 + reserved 3.64 + this call's
upper bound 0.85 > the limit 4.5"), and those workers were refused batch after batch while the four ran.
FIX: when spent + this call's upper bound fits and only reservations of calls IN FLIGHT stand in the way, _reserve
waits (sleeping OUTSIDE the ledger lock, re-reading the ledger every reserve_poll_s) and reserves once it fits. Still
kept out after reserve_wait_s (600 s): SpendLimit, as before (fail closed). Spend alone over the limit: SpendLimit at
once, as before. Each save still keeps spent + reserved <= the limit. UNCHANGED: _ledger() (base providers.py:
814-839) drops reservations of processes that are gone; _lock() (base :806-812) is an fcntl flock on SPEND.json.lock
taken through a NEW open file each time, so threads of one process exclude each other too.

TESTS: tests/package/test_meter.py (a deadline miss through a metered router fails over, books, and the meter
counts the booking); tests/providers/test_reserve_wait.py (six workers with room for four: all six answer, never more
than four in flight; spend alone over the limit: refused at once with a call in flight; a wait that ends still kept
out: refused, and never two reservations past the limit). Mutation checks: 3 of 3 and 4 of 4 killed.

PLEASE CHECK: (1) Can the wait deadlock or starve: can a call in flight need anything a waiting call holds? (2) Is
the limit ever passed: any path where a reservation is saved with spent + reserved > limit? (3) Callers that assumed
SpendLimit comes back at once: the wait runs before the call's deadline (_within) starts; can a caller with its own
time budget (prescreen, ruling 101's wait estimate, the shadow's background asks) now hang for long? (4) Is "best" right
for an abandoned call, and is any other wrapper of a Router method left with an old signature? (5) Test timing.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
