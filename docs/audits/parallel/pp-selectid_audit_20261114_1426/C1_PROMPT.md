# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_1426
# Branch: pp-selectid
# Generated: 2026-11-14 14:27 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_1426/C1_STEP.diff (303 lines)
```
   1 | diff --git a/pipeline/canon.py b/pipeline/canon.py
   2 | index c977a6a..6564cd6 100644
   3 | --- a/pipeline/canon.py
   4 | +++ b/pipeline/canon.py
   5 | @@ -29,6 +29,9 @@ _UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eig
   6 |  _TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
   7 |  _SCALES = {"hundred": 100, "thousand": 10 ** 3, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
   8 |  _SUFFIX = {"k": 10 ** 3, "m": 10 ** 6, "mn": 10 ** 6, "b": 10 ** 9, "bn": 10 ** 9, "t": 10 ** 12, "tn": 10 ** 12}
   9 | +# US retirement plans are NAMES: '401k' = '401(k)' (tokenised '401', 'k') is never 401000 (L-k: a different number never
  10 | +# compares equal; the 2026-11-14 pre-check finding). With a '$' before it, '$401k' stays the amount $401,000.
  11 | +_PLANS = ("401k", "403b", "457b")
  12 |  _ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
  13 |          "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
  14 |          "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
  15 | @@ -157,6 +160,13 @@ def _canon_seq(trips, heads=False):
  16 |              i += 1
  17 |              continue
  18 |          num, s0 = None, i
  19 | +        plan = t if t in _PLANS else (t + toks[i + 1] if i + 1 < len(toks) and len(toks[i + 1]) == 1
  20 | +                                      and t + toks[i + 1] in _PLANS else None)     # '401', 'k': only the letter
  21 | +        if plan is not None and owed is None:        # a plan's name, one token over every word it spans
  22 | +            last = i if plan == t else i + 1
  23 | +            out.append((plan, trips[i][1], trips[last][2]))
  24 | +            i = last + 1
  25 | +            continue
  26 |          m = _NUM.match(t)
  27 |          if m:
  28 |              try:
  29 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  30 | index e7095b4..a9eed55 100644
  31 | --- a/pipeline/lock_precheck.py
  32 | +++ b/pipeline/lock_precheck.py
  33 | @@ -40,14 +40,18 @@ from datetime import datetime, timezone
  34 |  
  35 |  import attest as AT
  36 |  
  37 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  38 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"   # RULING 103 (orchestrator 14:12 Nov 14): the
  39 | +#   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  40 | +#   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  41 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  42 | -DECODER = "c705b20ed800"                      # side): the render's own cut placement joins the pre-check (a passing
  43 | +DECODER = "d1e155c642a6"                      # side): the render's own cut placement joins the pre-check (a passing
  44 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  45 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  46 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  47 |  #   spotlight branches in pinned.py, merged fd5c9cc4 at 23:16 ET Nov 13; RULES unchanged; every medley span's decode,
  48 |  #   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  49 | +#   RULING 103 with the canon-401k fix (law L-k: '401k' is a plan's name, never 401000), landed together on the
  50 | +#   integrator's side (canon-401k 373d0fed + 077407dc, audited batches 79 and 80): d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce
  51 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  52 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  53 |                          "lock_requests")      # this worktree's; the service only reads it
  54 | @@ -174,7 +178,7 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  55 |      rows = []
  56 |      for s, e in zip(req, got):
  57 |          d = decide(s, e)
  58 | -        rows.append(dict(s, **d, entry=None if e is None else {
  59 | +        rows.append(dict(s, **d, relisten=relisten_of(e), entry=None if e is None else {
  60 |              "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
  61 |              "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
  62 |              "file": os.path.basename(result_file(s, results_dir))}))
  63 | @@ -183,6 +187,14 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  64 |              "error": "; ".join(errs)[:600] or None}
  65 |  
  66 |  
  67 | +def relisten_of(e):
  68 | +    """RULING 103: the entry's targeted re-listen record as it stands (one per segment: the lock's token, its short
  69 | +    window, both short readings, the verdict, scribe's cost), or None when no re-listen ran (the entry's null, a missing
  70 | +    key, or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
  71 | +    r = (e or {}).get("relisten") if isinstance(e, dict) else None
  72 | +    return r if isinstance(r, dict) else None
  73 | +
  74 | +
  75 |  def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
  76 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
  77 |      return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
  78 | @@ -217,6 +229,8 @@ def apply(pk, pre):
  79 |              if q:
  80 |                  raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
  81 |              s["text"], s["attested"] = r["spoken_text"], attested(r)
  82 | +        if isinstance(r.get("relisten"), dict):          # RULING 103: "Record both short readings on the pin"
  83 | +            s["relisten"] = r["relisten"]                # (sealed: package_pin.SEALED_LATER; only when one ran)
  84 |      pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
  85 |      pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
  86 |                        "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
  87 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  88 | index fc96df7..db852b6 100644
  89 | --- a/pipeline/package_pin.py
  90 | +++ b/pipeline/package_pin.py
  91 | @@ -146,7 +146,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
  92 |                                                             # retired by ruling 56: kept so its pins still recompute)
  93 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
  94 |                  "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
  95 | -                "visual")                                  # ruling 70: the clip's visual record (flags, sheet sha)
  96 | +                "visual",                                  # ruling 70: the clip's visual record (flags, sheet sha)
  97 | +                "relisten")                                # ruling 103: the targeted re-listen's two short readings
  98 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
  99 |                                                             # separate constant (a test holds them equal): the
 100 |                                                             # integrator's check_pin_only imports this module, which
 101 | @@ -439,7 +440,8 @@ def to_pin(pk, run_name):
 102 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 103 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 104 |                       **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 105 | -                                          "attested")      # rulings 68 / 72: an adopted spoken text, sealed
 106 | +                                          "attested",      # rulings 68 / 72: an adopted spoken text, sealed
 107 | +                                          "relisten")      # ruling 103: only when a re-listen ran, sealed
 108 |                          if k in s},
 109 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 110 |      edl_vo = {"intro": pk["vo"]["intro"],
 111 | diff --git a/pipeline/test_canon.py b/pipeline/test_canon.py
 112 | index 2ed80aa..1ea065c 100644
 113 | --- a/pipeline/test_canon.py
 114 | +++ b/pipeline/test_canon.py
 115 | @@ -264,5 +264,36 @@ class TestSites(unittest.TestCase):
 116 |          self.assertFalse(missing, missing)
 117 |  
 118 |  
 119 | +class TestRetirementPlans(unittest.TestCase):
 120 | +    """L-k (a different number never compares equal), the 2026-11-14 pre-check finding on 7BqLu-wzbU0: a US
 121 | +    retirement plan is a NAME. '401k' read as 401000 made 'a 401k' equal 'a 401,000'; '401(k)' read as 401 + 'k'
 122 | +    made the plan's two spellings differ. Both spellings are now one token; a '$' keeps an amount an amount."""
 123 | +
 124 | +    def test_a_plan_is_never_the_number(self):
 125 | +        for plan, amount in (("a 401k", "a 401,000"), ("a 401k", "a 401 thousand"), ("a 401(k)", "a 401,000"),
 126 | +                             ("my 403(b)", "my 403 billion"), ("a 457b", "a 457,000,000,000")):
 127 | +            self.assertFalse(C.same(plan, amount), (plan, amount))
 128 | +
 129 | +    def test_the_plans_spellings_are_one_name(self):
 130 | +        for a, b in (("I don't have a 401k.", "I don't have a 401(k)."), ("a 401K", "a 401(k)"),
 131 | +                     ("my 403b", "my 403(b)"), ("a 457(b) plan", "a 457b plan")):
 132 | +            self.assertTrue(C.same(a, b), (a, b))
 133 | +        self.assertEqual(C.canon_tokens("I don't have a 401(k)"), ["i", "don't", "have", "a", "401k"])
 134 | +
 135 | +    def test_the_pre_check_case_still_differs(self):
 136 | +        self.assertFalse(C.same("I don't have a 401k", "I don't have a 401 ,"))     # the second recogniser's reading
 137 | +
 138 | +    def test_amounts_are_unchanged(self):
 139 | +        self.assertEqual(C.canon_tokens("$401k"), ["401000", "dollars"])           # a '$' keeps it an amount
 140 | +        self.assertEqual(C.canon_tokens("40k"), ["40000"])
 141 | +        self.assertTrue(C.same("74k", "seventy four thousand"))
 142 | +        self.assertEqual(C.canon_tokens("401,000"), ["401000"])
 143 | +        self.assertEqual(C.canon_tokens("401 kilos"), ["401", "kilos"])           # only the single letter joins
 144 | +
 145 | +    def test_the_split_form_spans_both_words(self):
 146 | +        spans = C.canon_spans(["a", "401", "k", "plan"])
 147 | +        self.assertIn(("401k", 1, 2), [tuple(s) for s in spans])
 148 | +
 149 | +
 150 |  if __name__ == "__main__":
 151 |      unittest.main()
 152 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 153 | index 299098c..1c8a870 100644
 154 | --- a/tests/package/test_lock_precheck.py
 155 | +++ b/tests/package/test_lock_precheck.py
 156 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
 157 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 158 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 159 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 160 | -                         "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")             # ruling 90's decoder
 161 | +                         "DcUbBkyeh9M.216.054-228.674.d1e155c642a6.json")             # ruling 103's decoder
 162 |  
 163 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 164 |          segs = LP.segments_of([HOOK, CLIP])
 165 | @@ -133,7 +133,8 @@ class TestRuling84(unittest.TestCase):
 166 |      s = LP.segments_of([BREEDLOVE])[0]
 167 |  
 168 |      def test_the_rules_string_is_the_integrators(self):
 169 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84")
 170 | +        """RULING 103 (14:12 Nov 14) joined the integrator's rules string (its message of 14:3x Nov 14)."""
 171 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103")
 172 |  
 173 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 174 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 175 | @@ -180,7 +181,7 @@ class TestCheck(Dirs):
 176 |              self.put(s, entry(s))
 177 |          rep, sleeps = self.run_check([HOOK, CLIP])
 178 |          self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
 179 | -        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")
 180 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], f"DcUbBkyeh9M.216.054-228.674.{LP.DECODER}.json")
 181 |  
 182 |      def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
 183 |          segs = LP.segments_of([HOOK, CLIP])
 184 | @@ -204,15 +205,16 @@ class TestCheck(Dirs):
 185 |  
 186 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
 187 |          """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
 188 | -        integrator's spotlight branches) again; a file named for an older decoder (25cd6f15e6c9, 8a101f222598,
 189 | -        962353613cb0) is never opened, even with a matching, newer entry under the current rules."""
 190 | +        integrator's spotlight branches) again, and ruling 103 with the canon-401k fix again (14:3x Nov 14); a file
 191 | +        named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800) is never opened, even
 192 | +        with a matching, newer entry under the current rules."""
 193 |          s = LP.segments_of([HOOK])[0]
 194 | -        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0"):
 195 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800"):
 196 |              old = LP.result_file(s, self.res, decoder=dec)
 197 |              with open(old, "w") as f:
 198 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
 199 |              self.assertTrue(old.endswith(f".{dec}.json"))
 200 | -        self.assertIsNone(LP.answer(s, self.res))                                         # only c705b20ed800's file
 201 | +        self.assertIsNone(LP.answer(s, self.res))                                         # only LP.DECODER's file
 202 |  
 203 |      def test_ruling_73_holds_a_span_the_render_cannot_cut(self):
 204 |          segs = LP.segments_of([HOOK, CLIP])
 205 | diff --git a/tests/package/test_ruling_103.py b/tests/package/test_ruling_103.py
 206 | new file mode 100644
 207 | index 0000000..a802450
 208 | --- /dev/null
 209 | +++ b/tests/package/test_ruling_103.py
 210 | @@ -0,0 +1,92 @@
 211 | +#!/usr/bin/env python3
 212 | +"""RULING 103 (orchestrator 14:12 ET Nov 14), the builder's side, landed with the integrator's canon-401k fix (one
 213 | +decoder-sha move): the pre-check's rules and decoder; the targeted re-listen's record ("Record both short readings on
 214 | +the pin") carried from the pre-check entry onto the segment as it stands and sealed (package_pin.SEALED_LATER), only when
 215 | +a re-listen ran, so every pin without one seals as before; canon's '401k' is a plan's name (pipeline/test_canon.py, the
 216 | +integrator's tests, byte-identical). Offline: temporary requests and results directories."""
 217 | +import copy
 218 | +import json
 219 | +import os
 220 | +import sys
 221 | +import unittest
 222 | +
 223 | +HERE = os.path.dirname(os.path.abspath(__file__))
 224 | +REPO = os.path.dirname(os.path.dirname(HERE))
 225 | +for _p in ("pipeline", "tests/package"):
 226 | +    sys.path.insert(0, os.path.join(REPO, _p))
 227 | +import canon as C  # noqa: E402
 228 | +import lock_precheck as LP  # noqa: E402
 229 | +import package_pin  # noqa: E402
 230 | +import test_angles as TA  # noqa: E402
 231 | +from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402
 232 | +
 233 | +RELISTEN = {"token": "401k", "against": "", "window": [14.84, 18.38], "source_window": [14.84, 18.38],
 234 | +            "decoder_reading": "IRA. I don't have a 401k. I don't own a single",
 235 | +            "second_reading": "Roth IRA. I don't have a 401k. I don't own a single", "verdict": "pass",
 236 | +            "scribe_usd": 0.0007}
 237 | +
 238 | +
 239 | +class TestTheRules(Dirs):
 240 | +    def test_an_entry_under_the_rules_before_103_is_never_read(self):
 241 | +        s = LP.segments_of([HOOK])[0]
 242 | +        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84", at="2026-11-14T19:00:00Z"))
 243 | +        self.assertIsNone(LP.answer(s, self.res))
 244 | +        self.put(s, entry(s, at="2026-11-14T19:01:00Z"))                     # the same answer under ruling 103's rules
 245 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 246 | +
 247 | +
 248 | +class TestTheRecordReachesTheSeal(Dirs):
 249 | +    def check(self, relisten):
 250 | +        segs = LP.segments_of([HOOK, CLIP])
 251 | +        self.put(segs[0], entry(segs[0], relisten=relisten))
 252 | +        self.put(segs[1], entry(segs[1], relisten=None))
 253 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 254 | +
 255 | +    def pk(self):
 256 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 257 | +                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}
 258 | +
 259 | +    def test_a_relisten_record_is_carried_as_it_stands_and_only_when_one_ran(self):
 260 | +        pre = self.check(copy.deepcopy(RELISTEN))
 261 | +        self.assertTrue(pre["ok"])
 262 | +        self.assertEqual([r["relisten"] for r in pre["segments"]], [RELISTEN, None])
 263 | +        pk = LP.apply(self.pk(), pre)
 264 | +        self.assertEqual(pk["segments"][0]["relisten"], RELISTEN)                 # as it stands
 265 | +        self.assertNotIn("relisten", pk["segments"][1])                           # null: no key
 266 | +        for odd in ("pass", ["401k"], 7):                                           # not an object: no record
 267 | +            self.tmp.cleanup()
 268 | +            self.setUp()
 269 | +            pre = self.check(odd)
 270 | +            self.assertIsNone(pre["segments"][0]["relisten"], odd)                 # the row's contract: None
 271 | +            pk = LP.apply(self.pk(), pre)
 272 | +            self.assertNotIn("relisten", pk["segments"][0], odd)
 273 | +
 274 | +    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
 275 | +        base = TA.TestPinAndTruth.pk(None)
 276 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")
 277 | +        self.assertNotIn("relisten", plain["segments"][0])
 278 | +        with_r = copy.deepcopy(base)
 279 | +        with_r["segments"][0]["relisten"] = copy.deepcopy(RELISTEN)
 280 | +        pin = package_pin.to_pin(with_r, "r")
 281 | +        self.assertEqual(pin["segments"][0]["relisten"], RELISTEN)
 282 | +        sha = pin["moments_package"]["package_sha256"]
 283 | +        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
 284 | +        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
 285 | +        tampered = copy.deepcopy(pin)
 286 | +        tampered["segments"][0]["relisten"]["second_reading"] = "Roth IRA. I don't have a 401. I don't own a single"
 287 | +        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
 288 | +        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])
 289 | +
 290 | +
 291 | +class TestCanonOnThisSide(unittest.TestCase):
 292 | +    """The integrator's canon fix, taken byte-identical (its own tests: pipeline/test_canon.py TestRetirementPlans):
 293 | +    this side's step-A and attest code read the same canonical tokens as the render's lock."""
 294 | +
 295 | +    def test_the_plan_is_a_name_here_too(self):
 296 | +        self.assertFalse(C.same("a 401k", "a 401,000"))
 297 | +        self.assertTrue(C.same("I don't have a 401k.", "I don't have a 401(k)."))
 298 | +        self.assertFalse(C.same("I don't have a 401k", "I don't have a 401 ,"))     # Blockware's hold stands
 299 | +
 300 | +
 301 | +if __name__ == "__main__":
 302 | +    unittest.main()
 303 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- Before a line-up is written and before its pin is sealed, the builder asks the integrator's service to run the
  render's own lock on each segment (the "lock pre-check", pipeline/lock_precheck.py, rulings 68 / 72).
  - Requests go to this worktree's lock_requests dir. Answers are list-of-entry files named
    <video>.<start>-<end>.<DECODER>.json in the integrator's results dir (read only here).
  - An entry is read only when its "rules" string equals RULES and its file is named for DECODER: an answer under any
    other rules or decoder is not valid for the render's code.
- A pin (package_pin.to_pin) seals a sha256 over the gated bytes. Per segment: video, start, end, text, transcript sha,
  plus each SEALED_LATER field the segment carries, so a field enters the body only when present.
  - The integrator's check imports THIS worktree's package_pin.py and recomputes every pin's seal (pin_seal).
  - Every pin already delivered must recompute unchanged.
- canon.py is the one canonical text form both sides compare with (law L-k: a different number never compares equal).
  This worktree's copy was byte-identical to the render's.

THE ORCHESTRATOR'S RULING (14:12 ET Nov 14), verbatim:
"RULING 103, THE TARGETED RE-LISTEN (for a hold where the two independent readings differ on ONE number or name token,
as '401k' against '401' on Blockware 06d34e15). The hold stands as the default: a number or name disagreement is never
waved through. But one long-span reading against another is weak evidence about one token. Before the hold is final,
BOTH recognisers are asked again on a SHORT window cut around that token alone (the token's word times, 1.5 s either
side, the same audio the cut will use). The lock passes on that token only if BOTH short-window readings give the
lock's token (after the canon, with the 401k fix: a plan's name is not the number 401000). If either short reading still
differs, or the two differ from each other, the hold is final and the clip may only be saved by a variant that leaves
the token out. Record both short readings on the pin. Scribe's cost for 4 s is nothing; say it.
ORDER OF WORK: ... (2) with the integrator, land the canon-401k fix and ruling 103 together so the decoder sha moves
once ..."

THE INTEGRATOR'S SIDE (its messages of 14:2x-14:3x ET Nov 14; facts, not in this diff):
- Branch canon-401k 077407dc = 373d0fed (canon: '401k' / '401(k)' / 403(b) / 457(b) are one NAME token, never 401000;
  a '$' keeps an amount an amount) + ruling 103 in the render's adjudicate_lock. Audited batches 79 and 80, two cycles
  each, clean.
- The final decoder_sha is d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce. RULES becomes
  "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"; entries under the old RULES are never reused.
- The relisten record sits on each result entry, key "relisten", ONE per segment (a span decides at most one token).
  - It is null when no re-listen ran. Otherwise it is an object {token, against, window [f, f], source_window [f, f],
    decoder_reading, second_reading, verdict "pass" | "hold", scribe_usd}, or the edge form
    {token, against, verdict "hold", why}.
  - Only outcome "hold" or a passing lock carries a non-null record. relisten.verdict is the re-listen's own verdict,
    never an outcome.
- Ruling 103 added and renamed NO outcome. The set is "decoded", "no_difference", "adopted", "two_readings",
  "adopt_spoken", "hold", "error".
  - "decoded" is only for a decode-only request without approved_text. The builder's requests always carry it, and
    its decide() fails closed on "decoded", as it should.
  - A re-listen pass keeps the normal outcome (no_difference / adopted / two_readings), with spoken_text null.
- Landing: the builder commits this change and says READY with no build running. The integrator merges to main and
  pushes. Only then does the builder push, so no pre-check of the builder's waits on a sha it cannot read.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- lock_precheck.decide(): PASS = {"no_difference", "adopted", "two_readings"} passes; "adopt_spoken" adopts only after
  this side's own class_84 check; "hold" holds; anything else (including "decoded" and "error") is no verdict, never a
  pass.
- lock_precheck._matches(): rules == RULES, the window equals the segment's [start, end], and role, approved_text and the
  trim fields are equal.
- package_pin.seal() / pin_seal(): unchanged; body_of() adds `{k: s[k] for k in SEALED_LATER if k in s}`.

THE CHANGE (the diff follows):
1. lock_precheck.py:
   - RULES and DECODER updated (with the full sha in the history comment).
   - relisten_of(e): the entry's "relisten" when it is an object, else None.
   - check() puts it on each row ("relisten").
   - apply() copies a row's object record onto the package segment ("relisten") as it stands. Absent otherwise.
2. package_pin.py: SEALED_LATER gains "relisten", and to_pin carries "relisten" from the segment when present.
3. canon.py and test_canon.py: the integrator's fixed files, byte-identical (git show 077407dc:pipeline/canon.py). This
   side's copies were byte-identical to theirs before the fix.
4. Tests:
   - test_ruling_103.py (new, 5):
     - an entry under the old RULES is never read;
     - the record is carried as it stands, only when one ran;
     - a non-object is never carried, in the row or on the segment;
     - the record is inside the seal and pin_seal recomputes it, and a tampered reading changes the seal;
     - a pin without a record seals as before;
     - canon's plan-name cases on this side.
   - test_lock_precheck.py: its decoder literals and old-decoder list updated (c705b20ed800 joins the never-read list).
   - 8 mutations, each killed.
   - pipeline/test_canon.py TestSites::test_no_ad_hoc_normaliser_outside_canon already fails at HEAD (pipeline/
     speakers.py's own normalisers), before and after this change; it is not in this change's scope.

ATTACK:
(a) Can any answer under the old decoder or the old RULES still be read? Can a valid new answer be missed (a pass read
    as no verdict)?
(b) The relisten record: can a non-null record reach a pin that the render would refuse, or a null or odd one reach
    it? Is it sealed as it stands (no re-shaping)? Can a pin delivered before this change fail its recompute?
(c) canon: does the fix change any comparison the builder's own gates make, beyond '401k'-class plan names (an amount
    with '$', '40k', '401 kilos')?
(d) The landing order: can a build of the builder's run while the decoder it reads is not the one the service serves?
(e) Anything else that could seal a wrong pin or block every pre-check.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

