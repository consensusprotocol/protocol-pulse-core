# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_0054
# Branch: pp-selectid
# Generated: 2026-11-15 00:54 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_0054/C1_STEP.diff (145 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 78ff10f..0c04f2f 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -30,6 +30,7 @@ Router.notices), it never halts (PBX 02:45).
   6 |  Keys are read by name from the env file inside code; never printed or logged.
   7 |  """
   8 |  import hashlib
   9 | +import http.client
  10 |  import json
  11 |  import os
  12 |  import time
  13 | @@ -129,7 +130,9 @@ def _http_json(url, body, headers, timeout):
  14 |  def _with_backoff(fn, final_codes=()):
  15 |      """fn() with BACKOFF_S retries on 429 / 5xx / transport; HTTP codes in final_codes, an exhausted account and any
  16 |      other 4xx are final. A refusal of the request itself (PER_REQUEST_CODES) raises RequestRejected; anything else
  17 | -    that cannot answer raises Unavailable, with the reason."""
  18 | +    that cannot answer raises Unavailable, with the reason. Transport includes an answer cut mid-body
  19 | +    (http.client.IncompleteRead, an HTTPException but no OSError): it escaped as itself until 00:46 ET Nov 15, when
  20 | +    Heimdall cut a reply 43,669 bytes in and ended ruling 110's replay of one model."""
  21 |      last = None
  22 |      for wait in BACKOFF_S + (None,):
  23 |          try:
  24 | @@ -150,7 +153,7 @@ def _with_backoff(fn, final_codes=()):
  25 |              if e.code in PER_REQUEST_CODES:
  26 |                  raise RequestRejected(last) from None
  27 |              raise Unavailable(last) from None
  28 | -        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
  29 | +        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError, http.client.HTTPException) as e:
  30 |              last = type(e).__name__
  31 |              if wait is not None:
  32 |                  time.sleep(wait)
  33 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
  34 | index eb740e5..73e53ca 100644
  35 | --- a/tests/package/replay110.py
  36 | +++ b/tests/package/replay110.py
  37 | @@ -137,6 +137,10 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  38 |          row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
  39 |                     f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
  40 |          return row
  41 | +    except Exception as e:                            # noqa: BLE001  a call that failed in a way the Router does not
  42 | +        row.update(seconds=round(time.time() - t0, 2), heimdall=None,   # name (00:46 ET Nov 15: a reply cut
  43 | +                   heimdall_error=f"{type(e).__name__}: {str(e)[:200]}", outcome="error")   # mid-body) is an ERROR
  44 | +        return row                                    # row, never the end of the model's run
  45 |      secs = round(rep.seconds or (time.time() - t0), 2)
  46 |      row.update(seconds=secs, cached=bool(rep.cached), usd_reported=(rep.usage or {}).get("usd_reported"),
  47 |                 usd_estimate=rep.usd, out_tokens=(rep.usage or {}).get("out"))
  48 | diff --git a/tests/package/test_replay110.py b/tests/package/test_replay110.py
  49 | index 69cc2a3..18b1bb9 100644
  50 | --- a/tests/package/test_replay110.py
  51 | +++ b/tests/package/test_replay110.py
  52 | @@ -90,6 +90,14 @@ class TestOneRecord(unittest.TestCase):
  53 |                                              sleep=waited.append))
  54 |              self.assertEqual(waited, [30])
  55 |  
  56 | +    def test_a_call_that_fails_in_a_way_the_router_does_not_name_is_an_error_row(self):
  57 | +        import http.client
  58 | +        with tempfile.TemporaryDirectory() as d:          # 00:46 ET Nov 15: a reply cut mid-body ended the run
  59 | +            cut = Timed(GROK, fail=http.client.IncompleteRead(b"x", 21278))
  60 | +            row = RX.replay_one(candidate(d, cut), job(d), cap_s=2.0)
  61 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("error", None))
  62 | +            self.assertTrue(row["heimdall_error"].startswith("IncompleteRead"))
  63 | +
  64 |      def test_at_the_spend_stop_no_call_is_made(self):
  65 |          with tempfile.TemporaryDirectory() as d:
  66 |              b = Timed(GROK)
  67 | diff --git a/tests/providers/test_backoff.py b/tests/providers/test_backoff.py
  68 | new file mode 100644
  69 | index 0000000..064e88e
  70 | --- /dev/null
  71 | +++ b/tests/providers/test_backoff.py
  72 | @@ -0,0 +1,72 @@
  73 | +#!/usr/bin/env python3
  74 | +"""A reply cut mid-body is a transport failure: retried on the backoff, then Unavailable, so the chain fails over as
  75 | +for any other transport failure. At 00:46 ET Nov 15 Heimdall cut a reply 43,669 bytes in; http.client.IncompleteRead
  76 | +(an HTTPException, not an OSError) escaped providers._with_backoff as itself and ended ruling 110's replay of one
  77 | +model. Offline: the real HeimdallBackend and Router; urlopen and the backoff's sleep are stubbed."""
  78 | +import http.client
  79 | +import json
  80 | +import os
  81 | +import sys
  82 | +import tempfile
  83 | +import unittest
  84 | +from unittest import mock
  85 | +
  86 | +HERE = os.path.dirname(os.path.abspath(__file__))
  87 | +REPO = os.path.dirname(os.path.dirname(HERE))
  88 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  89 | +sys.path.insert(0, HERE)
  90 | +import providers as P  # noqa: E402
  91 | +from test_providers import Fake, router  # noqa: E402
  92 | +
  93 | +CUT = http.client.IncompleteRead(b"{" * 10, 21278)
  94 | +
  95 | +
  96 | +class Cut:
  97 | +    """An HTTP response whose body ends before its Content-Length: read() raises IncompleteRead."""
  98 | +
  99 | +    def read(self):
 100 | +        raise CUT
 101 | +
 102 | +
 103 | +class TestACutReplyIsATransportFailure(unittest.TestCase):
 104 | +
 105 | +    def test_a_cut_reply_is_retried_on_the_backoff_and_the_next_try_answers(self):
 106 | +        tries, waits = [], []
 107 | +
 108 | +        def fn():
 109 | +            tries.append(1)
 110 | +            if len(tries) == 1:
 111 | +                raise CUT
 112 | +            return {"ok": 1}
 113 | +        with mock.patch.object(P.time, "sleep", waits.append):
 114 | +            self.assertEqual(P._with_backoff(fn), {"ok": 1})
 115 | +        self.assertEqual((len(tries), waits), (2, [P.BACKOFF_S[0]]))
 116 | +
 117 | +    def test_a_reply_cut_every_time_is_unavailable_and_the_chain_fails_over(self):
 118 | +        with tempfile.TemporaryDirectory() as d:
 119 | +            h = P.HeimdallBackend("heimdall:deepseek/x", {"vendor": "heimdall", "model": "deepseek/x",
 120 | +                                                          "base_url": "http://gateway.invalid/api/v1",
 121 | +                                                          "price_usd_per_1m": [3, 15], "family": "deepseek"},
 122 | +                                  "/nonexistent")
 123 | +            h.key = lambda name: "test-key"
 124 | +            nxt = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 125 | +            r = router(d, [h, nxt], {"check": ["heimdall:deepseek/x", "heimdall:qwen"]})
 126 | +            r.backends = {h.name: h, nxt.name: nxt}
 127 | +            asked, waits = [], []
 128 | +
 129 | +            def urlopen(req, timeout=None):
 130 | +                asked.append(req.full_url)
 131 | +                return Cut()
 132 | +            with mock.patch.object(P.urllib.request, "urlopen", urlopen), \
 133 | +                    mock.patch.object(P.time, "sleep", waits.append):
 134 | +                rep = r.call("check", "p", 100, 7)
 135 | +            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))
 136 | +            tries = [u for u in asked if u.endswith("/chat/completions")]   # (the 90 % tripwire asks /credits)
 137 | +            self.assertEqual(len(tries), len(P.BACKOFF_S) + 1)          # every try, then Unavailable
 138 | +            self.assertEqual(waits, list(P.BACKOFF_S))
 139 | +            self.assertIn("IncompleteRead", rep.tried[0][1])
 140 | +            self.assertIn(h.name, r.down)                               # down for the run, as any transport failure
 141 | +
 142 | +
 143 | +if __name__ == "__main__":
 144 | +    unittest.main()
 145 | 
```

---

pp-selectid: A REPLY CUT MID-BODY. At 00:46 ET Nov 15, during ruling 110's replay, Heimdall cut a
deepseek-v4.1-flash-1017-uncensored reply 43,669 bytes in (http.client.IncompleteRead, 21,278 bytes short).
- IncompleteRead is an http.client.HTTPException, NOT an OSError. providers._with_backoff (base pipeline/providers.py:
  129-160) retries only urllib.error.URLError / TimeoutError / ConnectionError / OSError / ValueError, so it escaped
  as itself. Its docstring promises "anything else that cannot answer raises Unavailable".
- Router.call's `except BaseException: self._settle(key); raise` (UNCHANGED, :1377-1379) let it out of the call: no
  failover to the next leg.
- In the replay driver it ended that model's thread pool. Executor.map cancels the queued jobs after an exception, so
  113 calls never ran. In a build, the same failure would end the call the same way: package.prescreen holds it (its
  `except Exception`); a caller that catches only ProviderError would see the raw exception.

THE CHANGE:
1. pipeline/providers.py: `import http.client`; http.client.HTTPException joins _with_backoff's transport errors.
   A cut reply is now retried on BACKOFF_S (10, 30, 90 s), then raises Unavailable(<the exception's name>). Router.call
   treats that as any transport failure (UNCHANGED, :1371-1376): reservation released, health noted, the back-end down
   for this Router's run, failover to the next leg. Heimdall's credits() already catches Exception (UNCHANGED, :428-436).
2. tests/package/replay110.py (ruling 110's driver, landed 45455462): replay_one turns any other exception from the
   call into an ERROR row (with its type), never the end of the model's run.

TESTS: tests/providers/test_backoff.py (new; the real HeimdallBackend and Router, urlopen and sleep stubbed): one cut
reply is retried and the next try answers; a reply cut every time is Unavailable after every backoff and the chain
fails over (the 90% tripwire's /credits request is not counted). tests/package/test_replay110.py: a call failing with
IncompleteRead is an error row. 3 of 3 mutations killed (C1 the cut reply escapes, C2 it is Unavailable at once and
never retried, C3 the replay lets it end the run).

PLEASE CHECK: (1) any HTTPException that must NOT be retried, or that is already handled before this clause;
(2) spend: a retry is a new request under the same reservation, and a cut reply may still be billed but is not booked
(the same as a 5xx retry today); (3) whether marking the back-end down for the run after four cut replies is right
(it is what every other transport failure does); (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
