# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1305
# Branch: pp-selectid
# Generated: 2026-11-17 13:05 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1305/C1_STEP.diff (157 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 09c9f62..0372f28 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -760,6 +760,8 @@ class Router:
   6 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
   7 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
   8 |          self.uncapped = tuple(uncapped)           # RULING 118 (b): vendors recorded in the ledger but never capped
   9 | +        self.spend_refused = []                   # RULING 107 (1): the back-end of every paid call _reserve refused for
  10 | +        #   money (list.append: one per refusal, from any worker thread); a build records them as work left undone
  11 |          self.reserve_wait_s = float(reserve_wait_s)   # _reserve: 0 (the default) refuses at once, as every caller had
  12 |          self.reserve_poll_s = RESERVE_POLL_S          # it; a batch build that may wait for calls in flight opts in
  13 |          import threading
  14 | @@ -944,6 +946,14 @@ class Router:
  15 |          after batch while those four ran."""
  16 |          if not self.spend_path or b.free() or not self._capped(b.name):     # ruling 118 (b): Heimdall is free
  17 |              return None
  18 | +        try:
  19 | +            return self._reserve_capped(b, upper)
  20 | +        except SpendLimit:                        # RULING 107 (1) (build 134, 12:57 ET Nov 17): a call refused for
  21 | +            self.spend_refused.append(b.name)     # money is work left undone, never "nothing new"
  22 | +            raise
  23 | +
  24 | +    def _reserve_capped(self, b, upper):
  25 | +        """_reserve for a capped paid back-end: reserve `upper` or raise SpendLimit (its docstring)."""
  26 |          t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
  27 |          while True:
  28 |              with self._lock():
  29 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  30 | index 3779fe1..3359471 100644
  31 | --- a/tests/package/proof_ledger.py
  32 | +++ b/tests/package/proof_ledger.py
  33 | @@ -170,16 +170,22 @@ def _errors(x):
  34 |      return 0
  35 |  
  36 |  
  37 | -def open_work(res, sp):
  38 | +def open_work(res, sp, refused=()):
  39 |      """RULING 107 (1): what a finished build left undone, which the next build must try again whatever its inputs:
  40 | -    the moments ruling 102 held (no leg answered), any segment the render's lock gave no verdict on in time, and any
  41 | -    visual check left unmeasured. -> int (0: nothing left)."""
  42 | +    the moments ruling 102 held (no leg answered), in the clean pass and, the ones it did not hold too, in the
  43 | +    never-empty pass (its own record, rulings 136 / 137); any segment the render's lock gave no verdict on in time;
  44 | +    any visual check left unmeasured; and every paid call the build's router refused for money (`refused`:
  45 | +    Router.spend_refused; build 133's two clips-alone verdicts at its $0.00 stop, 12:56 ET Nov 17, left the kept
  46 | +    line-up unjudged, and build 134 then asked nothing). -> int (0: nothing left)."""
  47 |      pre, sp = (res or {}).get("prescreen") or {}, sp or {}
  48 |      h = pre.get("held_102") or {}
  49 |      held = len(h.get("first") or []) + len(h.get("second") or []) + len(sp.get("held_102") or [])
  50 | +    s = ((((res or {}).get("never_empty") or {}).get("soft_record") or {}).get("prescreen") or {}).get("held_102") or {}
  51 | +    held += len(set((s.get("first") or []) + (s.get("second") or [])) -
  52 | +                set((h.get("first") or []) + (h.get("second") or [])))
  53 |      no_verdict = _errors(res) + _errors(sp)        # by structure, never a string search (audit 2155g C1, qwen)
  54 |      vis = (res or {}).get("visual") or {}
  55 | -    return held + no_verdict + int(vis.get("unmeasured") or 0)
  56 | +    return held + no_verdict + int(vis.get("unmeasured") or 0) + len(refused or ())
  57 |  
  58 |  
  59 |  HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding
  60 | @@ -760,10 +766,13 @@ def main(argv=None):
  61 |          json.dump(res, f, indent=1, default=str)
  62 |      if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
  63 |          fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg, a.routing)   # at this build's END
  64 | -        left = open_work(res, sp)
  65 | +        money = list(router.spend_refused)       # the calls this build's router refused for money: left undone
  66 | +        left = open_work(res, sp, money)
  67 |          with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
  68 | -            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "build": name}, f, indent=1)
  69 | -        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone")
  70 | +            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "spend_refused": money,
  71 | +                       "build": name}, f, indent=1)
  72 | +        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone"
  73 | +            + (f" ({len(money)} of them paid call(s) the spend stop refused)" if money else ""))
  74 |      logf.close()
  75 |      return 0
  76 |  
  77 | diff --git a/tests/package/test_ledger_router.py b/tests/package/test_ledger_router.py
  78 | index 45b760c..bbf08b9 100644
  79 | --- a/tests/package/test_ledger_router.py
  80 | +++ b/tests/package/test_ledger_router.py
  81 | @@ -104,6 +104,50 @@ class TestRuling118TheBuildsRouterCapsOnlyOutsideVendors(unittest.TestCase):
  82 |              self.assertAlmostEqual(json.load(open(led))["by_backend"]["heimdall:q"]["usd_reported"], 3.5, places=6)
  83 |  
  84 |  
  85 | +class TestRuling107TheBuildsRouterNamesEveryCallItRefusedForMoney(unittest.TestCase):
  86 | +    """RULING 107 (1) (build 134, 12:57 ET Nov 17): the build's router names the back-end of every paid call it refused
  87 | +    for money in spend_refused, and the build records them as work left undone, so the next build is never "nothing
  88 | +    new" on their account. A free call, an answered paid call or a recorded reply is no refusal."""
  89 | +
  90 | +    def router_at(self, d, xai_spent):
  91 | +        led = os.path.join(d, "SPEND.json")
  92 | +        json.dump({"usd_estimate": 0.0, "calls": 1, "by_backend": {
  93 | +            "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": xai_spent}},
  94 | +            "by_role": {}, "reserved": {}, "usd_reported": xai_spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
  95 | +        with contextlib.ExitStack() as st:
  96 | +            for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
  97 | +                                   (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")),
  98 | +                                   (HH, "STATE", os.path.join(d, "HEALTH.json")),
  99 | +                                   (CB, "STATE", os.path.join(d, "BREAKERS.json")),
 100 | +                                   (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
 101 | +                                   (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
 102 | +                st.enter_context(mock.patch.object(mod, name, val))
 103 | +            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 104 | +        h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
 105 | +        x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
 106 | +        r.backends, r.chains["check"], r.chains["judge"] = {"heimdall:q": h, "xai:g": x}, ["heimdall:q"], ["xai:g"]
 107 | +        return r, led, x
 108 | +
 109 | +    def test_each_refusal_for_money_is_named_and_nothing_else(self):
 110 | +        with tempfile.TemporaryDirectory() as d:
 111 | +            r, led, x = self.router_at(d, 0.95)
 112 | +            self.assertEqual(r.spend_refused, [])
 113 | +            r.call("check", "p")                                     # Heimdall: free, never reserved
 114 | +            for n in (1, 2):
 115 | +                with self.assertRaises(P.SpendLimit):
 116 | +                    r.call("judge", "p")                             # 0.95 + its upper bound > the $1.00 stop
 117 | +                self.assertEqual(r.spend_refused, ["xai:g"] * n)
 118 | +            self.assertEqual(x.calls, 0)
 119 | +            open(led, "w").write("{not json")                        # an unreadable ledger refuses for money too
 120 | +            with self.assertRaises(P.SpendLimit):
 121 | +                r.call("judge", "p")
 122 | +            self.assertEqual(r.spend_refused, ["xai:g"] * 3)
 123 | +        with tempfile.TemporaryDirectory() as d:
 124 | +            r, led, x = self.router_at(d, 0.0)
 125 | +            self.assertEqual((r.call("judge", "p").backend, r.spend_refused), ("xai:g", []))   # answered: none
 126 | +            self.assertEqual((r.call("judge", "p").backend, x.calls, r.spend_refused), ("xai:g", 1, []))   # replayed
 127 | +
 128 | +
 129 |  class TestTheLedgerBuildsRouterWaitsForCallsInFlight(unittest.TestCase):
 130 |  
 131 |      def test_a_call_kept_out_only_by_a_call_in_flight_waits_and_answers(self):
 132 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 133 | index 8411c19..6155523 100644
 134 | --- a/tests/package/test_ruling_107_guard.py
 135 | +++ b/tests/package/test_ruling_107_guard.py
 136 | @@ -129,6 +129,20 @@ class TestOpenWorkAndNothingNew(unittest.TestCase):
 137 |          self.assertEqual(PLG.open_work({"a": [{"b": {"verdict": "error"}}, {"verdict": "pass"}]}, {}), 1)   # nested
 138 |          self.assertEqual(PLG.open_work({"why": 'a log line quoting "verdict": "error"'}, {}), 0)   # a string is no verdict
 139 |  
 140 | +    def test_money_refused_calls_and_the_never_empty_pass_holds_are_left_undone(self):
 141 | +        """Build 134 (12:57 ET Nov 17) asked nothing: free build 133's two clips-alone verdicts, refused at its $0.00
 142 | +        stop, were not counted as undone, and the never-empty pass's own record was not read."""
 143 | +        self.assertEqual(PLG.open_work({}, {}, ["xai:grok", "xai:grok"]), 2)      # each refused call
 144 | +        self.assertEqual((PLG.open_work({}, {}, ()), PLG.open_work({}, {}, None)), (0, 0))
 145 | +
 146 | +        def soft(first, second):
 147 | +            return {"never_empty": {"soft_record": {"prescreen": {"held_102": {"first": first, "second": second}}}}}
 148 | +        self.assertEqual(PLG.open_work(soft(["a"], ["b"]), {}), 2)                # the soft pass's own holds
 149 | +        both = dict(soft(["a"], ["b", "c"]), prescreen={"held_102": {"first": ["a"], "second": ["b"]}})
 150 | +        self.assertEqual(PLG.open_work(both, {}), 3)      # a and b once (the clean pass held them too), c new
 151 | +        self.assertEqual(PLG.open_work(dict(both, never_empty=None), {}, ["x"]), 3)   # no soft pass: clean + money
 152 | +        self.assertEqual(PLG.open_work({"never_empty": {"stage": "2a"}}, {}), 0)      # a soft pass that held nothing
 153 | +
 154 |      def test_only_the_newest_finished_build_counts(self):
 155 |          with tempfile.TemporaryDirectory() as d:
 156 |              def build(name, fp=None, left=0):
 157 | 
```

---

pp-selectid: RULING 107 (1)'s guard ("a build that judges nothing new must cost $0.00") has two gaps, found 12:57 ET
Nov 17. The build driver (tests/package/proof_ledger.py) fingerprints its inputs; when they equal the newest finished
build's and that build's FINGERPRINT.json says open_work == 0, it asks no model (nothing_new, proof_ledger.py:207 and
:219, called at :538 before any router exists). open_work counted only the clean pass's ruling-102 holds, lock no-verdicts
and unmeasured visuals. GAP 1: a paid call the router REFUSED FOR MONEY was never counted. Free build 133 (stop = the day's
spend + $0.001) refused the kept line-up's two clips-alone verdicts by design, recorded "0 items left undone", and paid
build 134 with the same inputs then asked nothing. GAP 2: the never-empty pass (rulings 136/137: package.build runs a
soft pass when the clean pass seals nothing; its record is res["never_empty"]["soft_record"]) was never read.

THE CHANGE:
(a) pipeline/providers.py: Router.spend_refused = [] (in __init__). _reserve (providers.py:931; its only callers are
    Router.call at :1406 and Router.transcribe at :1518; RoleModel at :1566 only converts a refusal already raised by
    them) keeps its free / uncapped early return and now calls _reserve_capped (:955, the old body UNCHANGED, which
    raises SpendLimit at :969 over the limit, and via _ledger at :855 or _basis_total at :912 on an unreadable or
    unreported ledger). Every SpendLimit from it appends the back-end's name to spend_refused and re-raises.
    list.append from the worker threads (step A, vision run in pools) is atomic under the GIL.
(b) tests/package/proof_ledger.py open_work(res, sp, refused=()): + len(refused); + the soft pass's held_102 ids not
    already held by the clean pass (a set difference: the soft pass re-runs step A on the same pool, so its first-screen
    holds repeat the clean pass's). At the build's end (:767, only for a full build, not --from-candidate), the driver
    passes list(router.spend_refused) (the one router of the build, built at :551) and records it in FINGERPRINT.json.
(c) Any code change moves the fingerprint (code by content), so the next build runs anyway; after this, a build stopped
    by money writes open_work > 0 and the next one retries. A build that cannot start at the stop (start_refused,
    :380) still writes no FINGERPRINT.

TESTS: test_ruling_107_guard (open_work: each refused call counts; the soft pass's holds count once; none or empty is 0)
and test_ledger_router (the build's own router from PLG.build_router: Heimdall free call and an answered or replayed paid
call add nothing; each refusal over the $1.00 stop and an unreadable ledger each add the back-end). Mutations: 6 of 7
killed. NOT UNIT-TESTED, PLEASE READ: the one wiring line in main() (open_work(res, sp, money) at :767-:773); no
full-run driver harness exists.

PLEASE CHECK: (1) can any money refusal escape the count, or any non-money failure be counted? (2) can a build now loop
forever or pay twice for the same judgment? A build whose router refused money writes open_work > 0, so the next build
runs; its recorded replies replay free and its refused calls cost nothing. (3) thread safety of the append; (4) the soft
pass's set difference; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
