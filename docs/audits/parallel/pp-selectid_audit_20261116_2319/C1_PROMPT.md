# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_2319
# Branch: pp-selectid
# Generated: 2026-11-16 23:19 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_2319/C1_STEP.diff (100 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 3814b5c..9322b8c 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -109,6 +109,8 @@
   6 |     "family": "grok"
   7 |    },
   8 |    "xai_vision:grok-4.7": {
   9 | +   "reserve_list_fraction": 0.6,
  10 | +   "reserve_list_fraction_why": "RULING 130 (3) (orchestrator 23:00 ET Nov 16): priced from the real bills: every vision bill recorded in VISUAL_CACHE.json when it was set (32), the largest $0.1752, 59.1 % of the reserve's list bound ($0.2965); median 16.7 %, p90 31.4 %. The tripwire (rulings 123 (1) / 130 (3)): the first bill above what was reserved puts the reserve back to list for the rest of the day.",
  11 |     "vendor": "xai_vision",
  12 |     "model": "grok-4.7",
  13 |     "price_usd_per_1m": [
  14 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  15 | index 21184cd..09c9f62 100644
  16 | --- a/pipeline/providers.py
  17 | +++ b/pipeline/providers.py
  18 | @@ -1028,13 +1028,18 @@ class Router:
  19 |              if backend is not None:
  20 |                  usage = usage or {}
  21 |                  f = backend.spec.get("reserve_list_fraction")      # RULING 123 (1): the tripwire, after every call
  22 | -                if _num(f) and _num(usage.get("usd_reported")) and float(usage["usd_reported"]) > float(f) * usd and \
  23 | -                        not (d.get("reserve_tripped") or {}).get(backend.name):
  24 | +                bill = float(usage["usd_reported"]) if _num(usage.get("usd_reported")) else None
  25 | +                over_list = bill is not None and _num(f) and bill > float(f) * usd
  26 | +                over_held = bill is not None and _num(f) and _num(held) and bill > float(held)   # RULING 130 (3): a
  27 | +                #   bill above what was RESERVED for the call trips too (a vision reply's usage runs past its output
  28 | +                #   cap, so its bill is a small share of the list price of its usage and the first test never fires)
  29 | +                if (over_list or over_held) and not (d.get("reserve_tripped") or {}).get(backend.name):
  30 |                      trip = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "role": role,
  31 | -                            "billed": round(float(usage["usd_reported"]), 6), "list": round(usd, 6),
  32 | +                            "billed": round(bill, 6), "list": round(usd, 6),
  33 |                              "fraction": float(f), "reserved": held,
  34 | -                            "why": f"billed above {float(f):.0%} of list: reserved at list for the rest of the day "
  35 | -                                   f"(ruling 123 (1))"}
  36 | +                            "why": (f"billed above {float(f):.0%} of list" if over_list else
  37 | +                                    f"billed above its reserve (${float(held):.4f})") +
  38 | +                                   ": reserved at list for the rest of the day (rulings 123 (1) / 130 (3))"}
  39 |                      d.setdefault("reserve_tripped", {})[backend.name] = trip
  40 |                      self.notices.append(f"RESERVE BACK TO LIST: {backend.name} {trip['why']}: billed "
  41 |                                          f"${trip['billed']:.4f}, list ${trip['list']:.4f}")
  42 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  43 | index b627add..44e0235 100644
  44 | --- a/tests/providers/test_providers.py
  45 | +++ b/tests/providers/test_providers.py
  46 | @@ -860,6 +860,53 @@ class TestRuling123Reserve(unittest.TestCase):
  47 |              day2.call("judge", p, 12000)              # a new day's ledger: 25 % again
  48 |              self.assertEqual(g.calls, 4)
  49 |  
  50 | +    def test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list(self):
  51 | +        """RULING 130 (3): a reply whose usage runs past its output cap (a vision check's) bills a small share of the
  52 | +        list price of its usage, so 'billed above the fraction of list' never fires; a bill above what was RESERVED for
  53 | +        the call trips the reserve back to list for the day."""
  54 | +        with tempfile.TemporaryDirectory() as d:
  55 | +            led = self.ledger(d, 0.40)
  56 | +            v = Fake("xai_vision:v", "xai", answer="{}", price=(5, 25),
  57 | +                     usage={"in": 1000, "out": 30000, "usd_reported": 0.10})   # its usage at list: $0.755
  58 | +            v.spec["reserve_list_fraction"] = 0.6
  59 | +            r = router(d, [v], {"judge": ["xai_vision:v"]}, spend_path=led, limit_usd=0.80, limit_basis="reported")
  60 | +            p = "p" * 3000                            # upper: 1.25 x (1,200 x $5/M + 12,000 x $25/M) = $0.3825
  61 | +            r.call("judge", p, 12000)                 # reserved 0.6 x 0.3825 = $0.2295; billed $0.10: no trip
  62 | +            self.assertIsNone(json.load(open(led)).get("reserve_tripped"))
  63 | +            v._usage = {"in": 1000, "out": 30000, "usd_reported": 0.25}    # above its $0.2295 reserve, below 0.6 x $0.755
  64 | +            r.call("judge", p, 12000)
  65 | +            trip = json.load(open(led))["reserve_tripped"]["xai_vision:v"]
  66 | +            self.assertEqual((trip["billed"], trip["reserved"]), (0.25, round(0.3825 * 0.6, 6)))
  67 | +            self.assertIn("above its reserve", trip["why"])
  68 | +            led2 = self.ledger(d, 0.40, "same_day.json")                    # 0.40 + 0.2295 fits 0.70; 0.40 + 0.3825 not
  69 | +            json.dump(dict(json.load(open(led2)), reserve_tripped={"xai_vision:v": trip}), open(led2, "w"))
  70 | +            r2 = router(d, [v], {"judge": ["xai_vision:v"]}, spend_path=led2, limit_usd=0.70, limit_basis="reported")
  71 | +            with self.assertRaises(P.SpendLimit):     # tripped: at list for the rest of the day
  72 | +                r2.call("judge", p, 12000)
  73 | +
  74 | +    def test_ruling_130_the_vision_check_is_reserved_at_its_fraction(self):
  75 | +        """RULING 130 (3): the configured vision back-end reserves its fraction of the list bound, not the whole."""
  76 | +        import visual_pin as VP
  77 | +        spec = json.load(open(P.CONFIG))["backends"]["xai_vision:grok-4.7"]
  78 | +        with tempfile.TemporaryDirectory() as d:
  79 | +            v = Fake("xai_vision:grok-4.7", "xai_vision", answer="{}", price=tuple(spec["price_usd_per_1m"]),
  80 | +                     usage={"in": 3000, "out": 2000, "usd_reported": 0.01})
  81 | +            v.spec.update({k: x for k, x in spec.items() if k in ("reserve_list_fraction", "min_out")})
  82 | +            v.vision = True                           # an image back-end (the router's own test)
  83 | +            v.upper_usd = P.VENDORS["xai_vision"]("xai_vision:grok-4.7", spec, env_path=os.devnull).upper_usd
  84 | +            prompt = {"text": VP.PROMPT.format(n=12, text="x" * 400), "images": ["A"]}
  85 | +            up = v.upper_usd(prompt, 1500)
  86 | +            for spent, runs in ((0.70 - up * spec["reserve_list_fraction"] - 0.001, True),
  87 | +                                (0.70 - up * spec["reserve_list_fraction"] + 0.001, False)):
  88 | +                led = self.ledger(d, spent, f"l{spent:.4f}.json")
  89 | +                r = router(d, [v], {"visual_check": ["xai_vision:grok-4.7"]}, spend_path=led, limit_usd=0.70,
  90 | +                           limit_basis="reported")
  91 | +                if runs:
  92 | +                    r.call("visual_check", prompt, 1500)
  93 | +                else:
  94 | +                    with self.assertRaises(P.SpendLimit):
  95 | +                        r.call("visual_check", prompt, 1500)
  96 | +
  97 |      def test_only_a_back_end_that_names_the_fraction_is_reserved_below_list(self):
  98 |          with tempfile.TemporaryDirectory() as d:
  99 |              led = self.ledger(d, 0.69)
 100 | 
```

---

pp-selectid: RULING 130 (3) (orchestrator 23:00 ET Nov 16), verbatim: "Vision checks reserve at list ($0.30 for two that
billed $0.1245): price the reserve from the real bills with the ruling 123 tripwire." Files: pipeline/providers.py,
pipeline/model_providers.json, tests/providers/test_providers.py.

THE BILLS (measured from every vision bill recorded in tests/package/proof/VISUAL_CACHE.json: 32): min $0.0072, median
$0.0496, p90 $0.0932, max $0.1752; as a share of the reserve's list bound ($0.2965: 1.25 x list at the call's real
output cap, ruling 121 (1)): median 16.7 %, p90 31.4 %, max 59.1 %. A vision reply's usage runs PAST its output cap
(max_out 8,000; recorded "out" up to 28,400 tokens), so every bill is only 24-29 % of the list price of its USAGE.

THE CHANGE:
(a) model_providers.json: xai_vision:grok-4.7 gains reserve_list_fraction 0.6 (the largest bill on record is 59.1 % of
    the list bound), with its why. UNCHANGED code reads it: Router._reserve_fraction (providers.py:1002 in the copy, ruling
    123 (1), 8d878e7f: the fraction unless the day's ledger has reserve_tripped for that back-end) and the reserve call
    (providers.py:1396: key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)).
(b) providers.Router._settle's tripwire (ruling 123 (1)): it fired only when a bill exceeded the fraction times the
    list price of the call's USAGE, which a vision bill never does (24-29 %). It now ALSO fires when the bill exceeds the
    amount RESERVED for that call (held, the reservation it settles). Either way: reserve_tripped for that back-end in
    the day's ledger (the reserve back to list for the rest of the day), the notice, and the record's why names which
    test fired. For Grok (fraction 0.25, bills about $0.01 against reserves of $0.06-0.12) nothing changes in practice.
    The worst overrun past the stop is one call's bill above its reserve, once a day, before the trip.

TESTS (TestRuling123Reserve): new: a bill above its reserve but below the fraction of list trips (and the same day's
next call is reserved at list); the configured vision back-end is reserved at its fraction (a call fits a limit just
above fraction x upper and is refused just below it). The ruling 123 tests unchanged and passing. Mutations V1-V3 after a
control run: 3 of 3 killed. Suites: 40 files by exit code, 852 tests.

PLEASE CHECK: (1) the fraction against the bills; (2) the tripwire's new test (bill vs the held reservation) and that
it cannot fire on a call that reserved nothing; (3) that nothing else changes for the other back-ends; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
