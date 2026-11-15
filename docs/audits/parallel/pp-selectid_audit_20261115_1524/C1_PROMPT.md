# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1524
# Branch: pp-selectid
# Generated: 2026-11-15 15:24 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1524/C1_STEP.diff (126 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5bbda7a..1afb4a7 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -872,6 +872,25 @@ def hook_live_bar():
   6 |      return HB.bar(None, HOOK_VERSION, HOOK_SEED, path=HB.PATH)
   7 |  
   8 |  
   9 | +BRACES_NOTE = "trailing closing brace(s) dropped (STATE Q2, 15:04 ET Nov 15)"
  10 | +
  11 | +
  12 | +def hook_answer(text):
  13 | +    """STATE Q2 (15:04 ET Nov 15, default at 15:24): the hook job's answer as JSON. Grok's answers out of contract were
  14 | +    valid JSON followed by ONE extra closing brace; an answer whose only extra is trailing closing braces (and white
  15 | +    space) is read as the object before them. -> (object, how many braces were dropped). Anything else that is not one
  16 | +    JSON object raises ValueError: out of contract, as before (and the contract's own checks still apply)."""
  17 | +    t = (text or "").strip()
  18 | +    try:
  19 | +        return json.loads(t), 0
  20 | +    except ValueError:
  21 | +        v, end = json.JSONDecoder().raw_decode(t)        # ValueError when no object starts the answer
  22 | +        rest = t[end:]
  23 | +        if not rest.strip() or rest.replace("}", "").strip():
  24 | +            raise ValueError(f"hook answer: {rest.strip()[:40]!r} after the object") from None
  25 | +        return v, rest.count("}")
  26 | +
  27 | +
  28 |  def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=HOOK_SEED):
  29 |      """RULING 59 (a) / RULING 115: the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked
  30 |      of EVERY given moment ALONE: ONE call per candidate (ruling 115: the asking the calibration measured; a batch moved
  31 | @@ -907,7 +926,7 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  32 |          return out, None
  33 |  
  34 |      def parse(text, ids):
  35 | -        v = json.loads(text.strip())
  36 | +        v, _ = hook_answer(text)                 # STATE Q2: an answer whose only extra is trailing closing braces
  37 |          h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
  38 |          if not isinstance(h, dict) or set(h) != set(ids) or any(
  39 |                  not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
  40 | @@ -926,9 +945,10 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  41 |          except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # this candidate has no rating
  42 |              err = err or f"{type(e).__name__}: {str(e)[:200]}"       # (law L-m); the others are still asked
  43 |              continue
  44 | -        x = h[mid]
  45 | +        x, dropped = h[mid], hook_answer(r.text)[1]
  46 |          rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
  47 | -               "backend": r.backend, "rule": HOOK_OWN_RULE}           # the rating orders hooks; hook_own decides
  48 | +               "backend": r.backend, "rule": HOOK_OWN_RULE,           # the rating orders hooks; hook_own decides
  49 | +               **({"answer_note": f"{dropped} {BRACES_NOTE}"} if dropped else {})}   # said, when it was read so
  50 |          out[mid] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
  51 |          new[key(m)] = {r.backend: rec}
  52 |      _cache_put(cache, new)
  53 | diff --git a/tests/package/hook115.py b/tests/package/hook115.py
  54 | index b5458cf..09deef0 100644
  55 | --- a/tests/package/hook115.py
  56 | +++ b/tests/package/hook115.py
  57 | @@ -114,6 +114,15 @@ def verdict(rows, model=None):
  58 |      return {"passes": ok, "approved": a, "negatives": n}
  59 |  
  60 |  
  61 | +def spent_reported(path=None):
  62 | +    """The ledger's VENDOR-REPORTED total (its usd_reported line), never the price table's estimate."""
  63 | +    path = path or SPEND
  64 | +    if not os.path.exists(path):
  65 | +        return 0.0
  66 | +    with open(path) as f:
  67 | +        return round(float(json.load(f).get("usd_reported") or 0.0), 6)
  68 | +
  69 | +
  70 |  def run(models, now=None):
  71 |      """Every model, both variants, the ten each -> the result, also written to QUESTION_V2_TEST.json."""
  72 |      now = now or datetime.now(timezone.utc)
  73 | @@ -140,8 +149,7 @@ def run(models, now=None):
  74 |                        f"{rows[-1].get('error') or ''}; ${r.spent():.4f}", flush=True)
  75 |              res[variant] = {"rows": rows, **verdict(rows, MODELS[key])}
  76 |          out["models"][MODELS[key]] = res
  77 | -    out["spent_usd_reported"] = round(P.Router(env_path=R.ENV, spend_path=SPEND).spent(), 6) if \
  78 | -        os.path.exists(SPEND) else 0.0
  79 | +    out["spent_usd_reported"] = spent_reported()
  80 |      os.makedirs(OUT, exist_ok=True)
  81 |      with open(os.path.join(OUT, "QUESTION_V2_TEST.json"), "w") as f:
  82 |          json.dump(out, f, indent=1)
  83 | diff --git a/tests/package/test_hook115.py b/tests/package/test_hook115.py
  84 | index 5384fa4..c9c944e 100644
  85 | --- a/tests/package/test_hook115.py
  86 | +++ b/tests/package/test_hook115.py
  87 | @@ -83,7 +83,10 @@ class TestRate(unittest.TestCase):
  88 |                  mock.patch.object(X, "SPEND", os.path.join(d, "S.json")), mock.patch.object(X, "rate", rate), \
  89 |                  mock.patch.object(X, "build_router", R), mock.patch.object(X.H, "ref_moments", lambda: POS), \
  90 |                  mock.patch.object(X, "negatives", lambda: NEG), mock.patch.object(X.H, "registry", lambda: []):
  91 | +            with open(os.path.join(d, "S.json"), "w") as f:            # the report names the REPORTED figure,
  92 | +                f.write('{"usd_reported": 0.1, "usd_estimate": 1.0}')     # never the estimate (15:17 ET Nov 15)
  93 |              out = X.run(["grok", "qwen"])
  94 | +            self.assertEqual(out["spent_usd_reported"], 0.1)
  95 |              self.assertTrue(os.path.exists(os.path.join(d, "QUESTION_V2_TEST.json")))
  96 |              X.report()
  97 |              self.assertIn("by xai:grok-4.20-0309-reasoning", open(os.path.join(d, "REPORT.md")).read())
  98 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  99 | index 3fd7c13..33db082 100644
 100 | --- a/tests/package/test_medley.py
 101 | +++ b/tests/package/test_medley.py
 102 | @@ -1386,6 +1386,23 @@ class TestRuling59HookFirst(unittest.TestCase):
 103 |              got, _ = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
 104 |              self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))   # ... and never read
 105 |  
 106 | +    def test_q2_an_answer_whose_only_extra_is_trailing_closing_braces_is_read(self):
 107 | +        """STATE Q2 (15:04 ET Nov 15, default 15:24): Grok's out-of-contract hook answers were valid JSON and ONE extra
 108 | +        closing brace; such an answer is read and its record says so; any other extra stays out of contract, and the
 109 | +        contract's own checks still apply."""
 110 | +        ms = [pm("a", "A", 12.0)]
 111 | +        ok = '{"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}'
 112 | +        for extra, n in (("}", 1), ("}}\n", 2), (" }", 1)):
 113 | +            got, err = PK.hook_ratings(self.canned(ok + extra), ms, ctx(), set(), set())
 114 | +            self.assertEqual((err, got["a"]["rating"], got["a"].get("answer_note")),
 115 | +                             (None, 4, f"{n} {PK.BRACES_NOTE}"), extra)
 116 | +        got, err = PK.hook_ratings(self.canned(ok), ms, ctx(), set(), set())
 117 | +        self.assertEqual((err, "answer_note" in got["a"]), (None, False))
 118 | +        for bad in (ok + "} x", ok + "]", ok + ', "b": 1}', '{"hooks": {"a": {"scroll": 4}}}}', "} " + ok):
 119 | +            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
 120 | +            self.assertEqual(got, {}, bad)                                   # out of contract: no rating
 121 | +            self.assertIn("Error", err)
 122 | +
 123 |      def test_a_candidate_left_unrated_never_stops_the_others_being_asked(self):
 124 |          """RULING 115: one call a candidate; a candidate whose chain is spent has no rating (law L-m), the others are
 125 |          still asked, and the first error is returned."""
 126 | 
```

---

pp-selectid: STATE Q2 (15:04 ET Nov 15; ruling 106's default at 15:24: YES, audit-first), THE HOOK JOB READS AN
ANSWER WHOSE ONLY EXTRA IS TRAILING CLOSING BRACES. And a one-line fix to ruling 115 (3)'s driver (the spend it
reports). Files: pipeline/package.py (hook_answer, hook_ratings' parse and record), tests/package/test_medley.py,
tests/package/hook115.py, tests/package/test_hook115.py.

THE QUESTION AS ASKED ON STATE LINE 1 (15:04 ET), verbatim: "Q2 GROK'S OUT-OF-CONTRACT HOOK ANSWER IS VALID JSON WITH
ONE EXTRA CLOSING BRACE (1 OF 10 TODAY; THE ALONE-TEST'S 2 WERE JSONDecodeErrors TOO, THEIR TEXT NOT KEPT, SO NOT
KNOWN TO BE THE SAME): ACCEPT AN ANSWER WHOSE ONLY EXTRA IS TRAILING CLOSING BRACES (AUDIT-FIRST)? RECOMMENDED: YES.
DEFAULT IN 20 MIN: YES." No answer came by 15:24, so the default is acted on.

THE EVIDENCE: build 11 (ledger_20261115_195152) kept Grok's refused hook answer in its shadow log (SHADOW86.jsonl, the
deciding text): '{"hooks": {"2bca1130b3eceac83ff8": {"scroll": 2, "alone": 3, "setup": 3, "why": "conversational
opener lacks punch"}}}}' -> json.loads: "Extra data: line 1 column 119". The object is complete; the last "}" is extra.
Ruling 115 (3)'s test lost one Grok rating per variant the same way (JSONDecodeError; text not kept).

THE CHANGE:
- package.hook_answer(text): json.loads first; only when that fails, json.JSONDecoder().raw_decode reads the object
  that STARTS the answer, and the rest must be closing braces and white space only (at least one brace) -> (object,
  braces dropped). Any other rest (text, "]", another key, nothing at all) raises ValueError: out of contract as
  before. hook_ratings' parse uses it; the contract's own checks are unchanged and still apply to the object (a
  partial object followed by braces is still refused). Only the hook job reads answers this way; every other verdict
  keeps json.loads.
- The record of a rating read this way says so: "answer_note": "<n> trailing closing brace(s) dropped (STATE Q2,
  15:04 ET Nov 15)" (the cache keeps it with the rating).
- hook115.py: the run's reported spend is read from the ledger's usd_reported line (spent_reported); its closing read
  had built a router on the estimate basis and written the price table's estimate ($1.0964 against $0.1062 reported:
  corrected by hand in the committed result file, c7775751).

UNCHANGED GUARDS: providers.call_parsed (pipeline/providers.py:690-716) moves on to the next model when parse raises
ValueError / TypeError / KeyError; hook_ratings catches the chain spent per candidate (law L-m: no rating);
_cache_put stores only records hook_ratings built.

TESTS: test_medley's new test: one, two (with a newline) or a spaced trailing brace is read, rating 4, and the
record carries the note; a clean answer carries none; "} x", "]", a further key, a partial object plus a brace, and a
brace BEFORE the object stay out of contract (no rating). test_hook115: the reported figure, never the estimate.
Suites: 281 pass (medley, hook115, spotlight, hook_bar). Mutations (after a control run): braces never accepted, any
trailing text accepted, the record not saying so, the estimate read as reported: 4 of 4 killed.

PLEASE CHECK: (1) that nothing but a complete object followed ONLY by closing braces is read; (2) that the hook
contract's checks still decide; (3) that no other verdict's parsing changes; (4) the spend fix; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
