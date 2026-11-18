# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_0727
# Branch: pp-selectid
# Generated: 2026-11-18 07:27 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_0727/C1_STEP.diff (91 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 55b6b06..551e068 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -53,7 +53,7 @@ import json
   6 |  import os
   7 |  import sys
   8 |  import time
   9 | -from datetime import datetime, timezone
  10 | +from datetime import datetime, timedelta, timezone
  11 |  
  12 |  HERE = os.path.dirname(os.path.abspath(__file__))
  13 |  REPO = os.path.dirname(os.path.dirname(HERE))
  14 | @@ -461,6 +461,7 @@ def main(argv=None):
  15 |      if not 0 < a.hours <= cap:                           # ruling 76: "rather than widen the window" (144: one exception)
  16 |          print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  17 |          return 2
  18 | +    base_h = package_pin.WINDOW_H                        # 12: the rule (rulings 76 + 77) the exception widens
  19 |      if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  20 |          package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  21 |      try:                                                 # read before anything is written (glm C2 N-4)
  22 | @@ -522,7 +523,12 @@ def main(argv=None):
  23 |          f"{len(delivered)} clip spans out")
  24 |      say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
  25 |          (f": {gone}" if gone else ""))
  26 | -    rows, rep = LB.rows(since, now, horizon_h=a.hours)
  27 | +    a_now = now - timedelta(hours=a.hours - base_h) if a.pbx_exception else now   # RULING 144: the ingest adapter
  28 | +    rows, rep = LB.rows(since, a_now, horizon_h=a.hours)   # (pp-ingest's; its own 12 h expiry, rulings 76 + 77) is read
  29 | +    if a.pbx_exception:                                  # as of this earlier clock, so it admits moments up to --hours
  30 | +        say(f"  RULING 144 ({a.pbx_exception}): the ingest adapter read as of {a_now.isoformat(timespec='seconds')} "
  31 | +            f"({a.hours - base_h:g} h before the render clock), so its own {base_h:g} h expiry admits moments up to "
  32 | +            f"{a.hours:g} h old; every other check runs on the render clock with a {a.hours:g} h window")
  33 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
  34 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
  35 |      wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids);
  36 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  37 | index a679178..f2832ff 100644
  38 | --- a/tests/package/test_ruling_137.py
  39 | +++ b/tests/package/test_ruling_137.py
  40 | @@ -8,6 +8,7 @@ import os
  41 |  import sys
  42 |  import tempfile
  43 |  import unittest
  44 | +from datetime import datetime, timezone
  45 |  from unittest import mock
  46 |  
  47 |  HERE = os.path.dirname(os.path.abspath(__file__))
  48 | @@ -593,6 +594,42 @@ class TestRuling144TheOneException(unittest.TestCase):
  49 |          finally:
  50 |              PP.WINDOW_H = saved
  51 |  
  52 | +    def test_the_ingest_adapter_is_asked_as_of_hours_minus_12_earlier(self):
  53 | +        """pp-ingest's adapter drops a moment 12 h after its video's publish time on the clock it is given (rulings 76 +
  54 | +        77); under the exception it is given the render clock minus (hours - 12) h, so it admits moments up to --hours
  55 | +        old. Without the exception it gets the render clock, as ever."""
  56 | +        import tempfile
  57 | +        import proof_ledger as PLG
  58 | +        pins = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
  59 | +                for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]
  60 | +        seen = []
  61 | +
  62 | +        class Past(Exception):
  63 | +            pass
  64 | +
  65 | +        def rows(since, now, horizon_h=None, **k):
  66 | +            seen.append((now, horizon_h))
  67 | +            raise Past()
  68 | +        saved = PP.WINDOW_H
  69 | +        try:
  70 | +            for extra in ([], ["--hours", "26", "--pbx-exception", "PBX exception x"]):
  71 | +                with tempfile.TemporaryDirectory() as d:          # one folder a run: a run's folder is never reused
  72 | +                    os.makedirs(os.path.join(d, "proof"))
  73 | +                    with mock.patch.object(PLG, "HERE", d), \
  74 | +                            mock.patch.object(PLG, "REGISTRY", os.path.join(d, "proof", "CANDIDATES.json")), \
  75 | +                            mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []), \
  76 | +                            mock.patch.object(PLG.LB, "rows", rows), mock.patch("sys.stdout"):
  77 | +                        t0 = datetime.now(timezone.utc)
  78 | +                        with self.assertRaises(Past):
  79 | +                            PLG.main(["--delivered", *pins, *extra])
  80 | +                now, h = seen[-1]
  81 | +                back = (t0 - now).total_seconds() / 3600
  82 | +                self.assertAlmostEqual(back, 14.0 if extra else 0.0, delta=0.05)
  83 | +                self.assertEqual(h, 26.0 if extra else 12.0)
  84 | +                PP.WINDOW_H = saved
  85 | +        finally:
  86 | +            PP.WINDOW_H = saved
  87 | +
  88 |  
  89 |  class TestTheDayCount(unittest.TestCase):
  90 |      def test_counted_per_day_ledger(self):
  91 | 
```

---

pp-selectid: RULING 144 (PBX 07:05 ET Nov 18: "disregard the 12 hour rule for this one exception"), PART 2. Part 1 is
live (fc191b4e, audit 20261118_0711): --pbx-exception TEXT lets --hours reach 30 for ONE build process and widens
package_pin.WINDOW_H for it. The first run (build 144, 07:24 ET) found NONE of the six named moments: the ingest adapter
(pp-ingest's pipeline.ingest.ledger.best_unused_moments, another session's code, run read-only through
pipeline/ledger_build.rows) has its OWN expiry: a moment is dropped when the clock it is GIVEN is at or past
min(expires_at, published_at + 12 h) (rulings 76 + 77; ledger.py:281 and :338). It dropped 3069 rows. File:
tests/package/proof_ledger.py (+ its test in tests/package/test_ruling_137.py).

THE CHANGE (only with --pbx-exception): the adapter is called with a_now = render clock - (hours - 12) h (12 = WINDOW_H
read BEFORE the exception widens it), and horizon_h = hours, so its own 12 h expiry admits moments up to --hours old
(a moment published exactly --hours ago expires at a_now and stays out). A line in the build log names it. Every other
check runs on the real render clock: package.expired and window_problems with the widened window, never-reused against
the delivered pins (package.usable), the exclusions, and the seal. Without the flag: the adapter gets the render clock,
exactly as before. The adapter's other drops (delivered in 24 h, opt-out, hard flags) still run on its rows.

TESTS: the adapter's clock is the render clock without the exception, and 14 h earlier with --hours 26 and the
exception; its horizon is the window. Mutations: 2 of 2 killed (the clock never moved; moved by hours, not hours - 12).

PLEASE CHECK: (1) can this admit anything the exception did not (older than --hours, a delivered or excluded moment)?
(2) can it leak into a build without the flag? (3) the arithmetic at the boundary; (4) the test.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
