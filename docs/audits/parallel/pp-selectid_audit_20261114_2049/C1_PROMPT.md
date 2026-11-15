# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2049
# Branch: pp-selectid
# Generated: 2026-11-14 20:51 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2049/C1_STEP.diff (369 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | index 1c650a3..4b24599 100644
   3 | --- a/pipeline/lock_precheck.py
   4 | +++ b/pipeline/lock_precheck.py
   5 | @@ -40,11 +40,13 @@ from datetime import datetime, timezone
   6 |  
   7 |  import attest as AT
   8 |  
   9 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"   # RULING 103 (orchestrator 14:12 Nov 14): the
  10 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105"   # RULING 105 (orchestrator
  11 | +#   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
  12 | +#   RULING 103 (orchestrator 14:12 Nov 14): the
  13 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  14 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  15 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  16 | -DECODER = "d1e155c642a6"                      # side): the render's own cut placement joins the pre-check (a passing
  17 | +DECODER = "a4c307f78c94"                      # side): the render's own cut placement joins the pre-check (a passing
  18 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  19 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  20 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  21 | @@ -52,6 +54,8 @@ DECODER = "d1e155c642a6"                      # side): the render's own cut plac
  22 |  #   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  23 |  #   RULING 103 with the canon-401k fix (law L-k: '401k' is a plan's name, never 401000), landed together on the
  24 |  #   integrator's side (canon-401k 373d0fed + 077407dc, audited batches 79 and 80): d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce
  25 | +#   RULING 105 (the integrator's branch ruling105 d5bf9674, audited batch 84; both sides land in lockstep as with 103):
  26 | +#   a4c307f78c94d1c4ee068b5c27862c79a90900880bb885fee68da616ce2a20d6
  27 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  28 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  29 |                          "lock_requests")      # this worktree's; the service only reads it
  30 | @@ -138,6 +142,12 @@ def decide(seg, e):
  31 |      if e is None:
  32 |          return {"verdict": "error", "outcome": None, "why": "no answer from the render's lock in time (law L-m)"}
  33 |      out, why = e.get("outcome"), str(e.get("reason") or "")[:400]
  34 | +    u = (e or {}).get("unstable_second_reading") if isinstance(e, dict) else None
  35 | +    if out in PASS and u is not None:                 # RULING 105: a pass that rests on the readings across passes
  36 | +        bad = ruling_105_fails(u)
  37 | +        if bad:                                       # this side's own check of the record disagrees: fail closed
  38 | +            return {"verdict": "hold", "outcome": out, "why": f"ruling 105 (this side's check of the pre-check's "
  39 | +                                                              f"record): {bad}"}
  40 |      if out in PASS:
  41 |          return {"verdict": "pass", "outcome": out, "why": why}
  42 |      if out == "hold":
  43 | @@ -178,7 +188,8 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  44 |      rows = []
  45 |      for s, e in zip(req, got):
  46 |          d = decide(s, e)
  47 | -        rows.append(dict(s, **d, relisten=relisten_of(e), entry=None if e is None else {
  48 | +        rows.append(dict(s, **d, relisten=relisten_of(e), unstable_second_reading=unstable_of(e),
  49 | +                         entry=None if e is None else {
  50 |              "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
  51 |              "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
  52 |              "file": os.path.basename(result_file(s, results_dir))}))
  53 | @@ -187,6 +198,53 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  54 |              "error": "; ".join(errs)[:600] or None}
  55 |  
  56 |  
  57 | +def _truncation(r, token):
  58 | +    """RULING 105 (3): r is the lock's NUMBER token cut short: a prefix of it that keeps a digit and drops only a
  59 | +    NON-DIGIT suffix ('401' of '401k'). A name (a token with no digit) never qualifies, nor does a dropped token ("")
  60 | +    or a different number ('68000' of '86000')."""
  61 | +    return (isinstance(r, str) and bool(r) and r != token and token.startswith(r) and any(ch.isdigit() for ch in r)
  62 | +            and not any(ch.isdigit() for ch in token[len(r):]))
  63 | +
  64 | +
  65 | +def ruling_105_fails(u):
  66 | +    """RULING 105 (orchestrator 20:13 Nov 14), checked on THIS side from the record the pre-check sealed
  67 | +    ("unstable_second_reading"): the token is adjudicated as the lock's only when (1) the decoder read it the same on
  68 | +    every pass, (2) the second recogniser's repeated readings of the same audio differ among themselves and one of
  69 | +    them IS the token, and (3) every differing reading is a truncation of it. -> None when the record's pass holds on
  70 | +    its own readings; else why not (a record that is not an object, the many-token form, a hold verdict, or any of the
  71 | +    three not met: every one a hold, never a pass)."""
  72 | +    if not isinstance(u, dict):
  73 | +        return f"the record is not an object ({type(u).__name__})"
  74 | +    if "tokens" in u or u.get("verdict") != "pass":
  75 | +        return f"the record's verdict is {u.get('verdict')!r}" + (f" ({u.get('why')})" if u.get("why") else "")
  76 | +    tok, dec, sec = u.get("token"), u.get("decoder_readings"), u.get("second_readings")
  77 | +    if not (isinstance(tok, str) and tok and any(ch.isdigit() for ch in tok)):
  78 | +        return f"the token {tok!r} is not a number (a name never qualifies)"
  79 | +    if not (isinstance(dec, list) and dec and isinstance(sec, list) and len(sec) >= 2):
  80 | +        return "the record holds too few readings (the decoder's, and at least two of the second recogniser's)"
  81 | +    dt = [x.get("token") if isinstance(x, dict) else None for x in dec]
  82 | +    st = [x.get("token") if isinstance(x, dict) else None for x in sec]
  83 | +    if any(x != tok for x in dt):
  84 | +        return f"(1) the decoder is not stable: {dt}"
  85 | +    if len(set(st)) < 2 or tok not in st:
  86 | +        return f"(2) the second recogniser is stable in its readings or never reads the token: {st}"
  87 | +    odd = [x for x in st if x != tok and not _truncation(x, tok)]
  88 | +    if odd:
  89 | +        return f"(3) a differing reading is not a truncation of {tok!r}: {odd}"
  90 | +    tests = u.get("tests")
  91 | +    if not (isinstance(tests, dict) and all(tests.get(k) is True for k in
  92 | +                                            ("decoder_stable", "second_unstable", "truncations_only"))):
  93 | +        return f"the record's own tests do not all hold: {tests}"
  94 | +    return None
  95 | +
  96 | +
  97 | +def unstable_of(e):
  98 | +    """RULING 105: the entry's unstable-second-reading record as it stands, or None (the entry's null, a missing key,
  99 | +    or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
 100 | +    r = (e or {}).get("unstable_second_reading") if isinstance(e, dict) else None
 101 | +    return r if isinstance(r, dict) else None
 102 | +
 103 | +
 104 |  def relisten_of(e):
 105 |      """RULING 103: the entry's targeted re-listen record as it stands (one per segment: the lock's token, its short
 106 |      window, both short readings, the verdict, scribe's cost), or None when no re-listen ran (the entry's null, a missing
 107 | @@ -231,6 +289,8 @@ def apply(pk, pre):
 108 |              s["text"], s["attested"] = r["spoken_text"], attested(r)
 109 |          if isinstance(r.get("relisten"), dict):          # RULING 103: "Record both short readings on the pin"
 110 |              s["relisten"] = json.loads(json.dumps(r["relisten"]))   # a copy as it stands (sealed: SEALED_LATER)
 111 | +        if isinstance(r.get("unstable_second_reading"), dict):     # RULING 105: "All readings are recorded on the
 112 | +            s["unstable_second_reading"] = json.loads(json.dumps(r["unstable_second_reading"]))   # pin" (sealed)
 113 |      pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
 114 |      pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
 115 |                        "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
 116 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 117 | index db852b6..bfbed07 100644
 118 | --- a/pipeline/package_pin.py
 119 | +++ b/pipeline/package_pin.py
 120 | @@ -147,7 +147,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 121 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 122 |                  "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
 123 |                  "visual",                                  # ruling 70: the clip's visual record (flags, sheet sha)
 124 | -                "relisten")                                # ruling 103: the targeted re-listen's two short readings
 125 | +                "relisten",                                # ruling 103: the targeted re-listen's two short readings
 126 | +                "unstable_second_reading")                 # ruling 105: every reading across the passes, when it ran
 127 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 128 |                                                             # separate constant (a test holds them equal): the
 129 |                                                             # integrator's check_pin_only imports this module, which
 130 | @@ -441,7 +442,8 @@ def to_pin(pk, run_name):
 131 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 132 |                       **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 133 |                                            "attested",      # rulings 68 / 72: an adopted spoken text, sealed
 134 | -                                          "relisten")      # ruling 103: only when a re-listen ran, sealed
 135 | +                                          "relisten",      # ruling 103: only when a re-listen ran, sealed
 136 | +                                          "unstable_second_reading")   # ruling 105: only when it ran, sealed
 137 |                          if k in s},
 138 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 139 |      edl_vo = {"intro": pk["vo"]["intro"],
 140 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 141 | index 1c8a870..fb087af 100644
 142 | --- a/tests/package/test_lock_precheck.py
 143 | +++ b/tests/package/test_lock_precheck.py
 144 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
 145 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 146 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 147 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 148 | -                         "DcUbBkyeh9M.216.054-228.674.d1e155c642a6.json")             # ruling 103's decoder
 149 | +                         "DcUbBkyeh9M.216.054-228.674.a4c307f78c94.json")             # ruling 105's decoder
 150 |  
 151 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 152 |          segs = LP.segments_of([HOOK, CLIP])
 153 | @@ -133,8 +133,9 @@ class TestRuling84(unittest.TestCase):
 154 |      s = LP.segments_of([BREEDLOVE])[0]
 155 |  
 156 |      def test_the_rules_string_is_the_integrators(self):
 157 | -        """RULING 103 (14:12 Nov 14) joined the integrator's rules string (its message of 14:3x Nov 14)."""
 158 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103")
 159 | +        """RULING 103 (14:12 Nov 14) and RULING 105 (20:13 Nov 14) joined the integrator's rules string (its messages
 160 | +        of 14:3x and 20:5x Nov 14)."""
 161 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105")
 162 |  
 163 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 164 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 165 | @@ -205,11 +206,11 @@ class TestCheck(Dirs):
 166 |  
 167 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
 168 |          """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
 169 | -        integrator's spotlight branches) again, and ruling 103 with the canon-401k fix again (14:3x Nov 14); a file
 170 | -        named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800) is never opened, even
 171 | -        with a matching, newer entry under the current rules."""
 172 | +        integrator's spotlight branches) again, ruling 103 with the canon-401k fix again (14:3x Nov 14), and ruling 105
 173 | +        again (20:5x Nov 14); a file named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800,
 174 | +        d1e155c642a6) is never opened, even with a matching, newer entry under the current rules."""
 175 |          s = LP.segments_of([HOOK])[0]
 176 | -        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800"):
 177 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800", "d1e155c642a6"):
 178 |              old = LP.result_file(s, self.res, decoder=dec)
 179 |              with open(old, "w") as f:
 180 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
 181 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 182 | new file mode 100644
 183 | index 0000000..bfae4f5
 184 | --- /dev/null
 185 | +++ b/tests/package/test_ruling_105.py
 186 | @@ -0,0 +1,182 @@
 187 | +#!/usr/bin/env python3
 188 | +"""RULING 105 (orchestrator 20:13 ET Nov 14), the builder's side, landed in lockstep with the integrator's pre-check
 189 | +(branch ruling105 d5bf9674, decoder a4c307f78c94): the rules and decoder; the record "unstable_second_reading" ("All
 190 | +readings are recorded on the pin") carried from the pre-check entry onto the segment as it stands and sealed
 191 | +(package_pin.SEALED_LATER), only when present, so every pin without one seals as before; and THIS side's own check of a
 192 | +pass that rests on it (lock_precheck.ruling_105_fails): the decoder stable, the second recogniser unstable with one
 193 | +reading equal to the lock's token, every differing reading a truncation of a NUMBER token. Anything else is a hold:
 194 | +a stable disagreement, a different number ('68,000' / '86,000'), a different name (the must-fail cases). Offline."""
 195 | +import copy
 196 | +import os
 197 | +import sys
 198 | +import unittest
 199 | +
 200 | +HERE = os.path.dirname(os.path.abspath(__file__))
 201 | +REPO = os.path.dirname(os.path.dirname(HERE))
 202 | +for _p in ("pipeline", "tests/package"):
 203 | +    sys.path.insert(0, os.path.join(REPO, _p))
 204 | +import lock_precheck as LP  # noqa: E402
 205 | +import package_pin  # noqa: E402
 206 | +import test_angles as TA  # noqa: E402
 207 | +from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402
 208 | +
 209 | +
 210 | +def record(token="401k", decoder=("401k", "401k", "401k"), second=("401", "401", "401k"), verdict="pass", tests=None):
 211 | +    """The integrator's field shape (its message of 20:5x Nov 14), as Blockware 06d34e15's readings fill it."""
 212 | +    when = ("2026-11-14T18:51:07Z", "2026-11-14T19:16:06Z", "now")
 213 | +    return {"token": token,
 214 | +            "decoder_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "lock (long window)",
 215 | +                                  "token": t} for i, t in enumerate(decoder)],
 216 | +            "second_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "long window", "token": t}
 217 | +                                for i, t in enumerate(second)],
 218 | +            "tests": tests if tests is not None else {"decoder_stable": True, "second_unstable": True,
 219 | +                                                      "truncations_only": True},
 220 | +            "verdict": verdict}
 221 | +
 222 | +
 223 | +BLOCKWARE = record()
 224 | +
 225 | +
 226 | +class TestTheRules(Dirs):
 227 | +    def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 228 | +        self.assertTrue(LP.RULES.endswith("+ ruling 103 + ruling 105"))
 229 | +        self.assertEqual(LP.DECODER, "a4c307f78c94")
 230 | +        s = LP.segments_of([HOOK])[0]
 231 | +        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 232 | +                          at="2026-11-14T21:00:00Z"))
 233 | +        self.assertIsNone(LP.answer(s, self.res))                                 # ruling 103's rules: never read
 234 | +        self.put(s, entry(s, at="2026-11-14T21:01:00Z"))
 235 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 236 | +
 237 | +
 238 | +class TestThisSidesCheck(unittest.TestCase):
 239 | +    s = LP.segments_of([HOOK])[0]
 240 | +
 241 | +    def decide(self, rec, outcome="no_difference"):
 242 | +        return LP.decide(self.s, entry(self.s, outcome, unstable_second_reading=rec))
 243 | +
 244 | +    def test_blockwares_readings_pass(self):
 245 | +        self.assertIsNone(LP.ruling_105_fails(copy.deepcopy(BLOCKWARE)))
 246 | +        self.assertEqual(self.decide(copy.deepcopy(BLOCKWARE))["verdict"], "pass")
 247 | +
 248 | +    def test_no_record_changes_nothing(self):
 249 | +        self.assertEqual(self.decide(None)["verdict"], "pass")
 250 | +        self.assertEqual(self.decide(None, "hold")["verdict"], "hold")
 251 | +
 252 | +    def test_must_fail_a_second_recogniser_stable_in_its_disagreement(self):
 253 | +        d = self.decide(record(second=("401", "401", "401")))              # even a record that says "pass"
 254 | +        self.assertEqual(d["verdict"], "hold")
 255 | +        self.assertIn("(2)", d["why"])
 256 | +
 257 | +    def test_a_record_whose_second_readings_never_vary_is_no_unstable_reading(self):
 258 | +        d = self.decide(record(second=("401k", "401k")))                   # nothing disputed: the record should
 259 | +        self.assertEqual(d["verdict"], "hold")                              # be null; one that says "pass" is
 260 | +        self.assertIn("(2)", d["why"])                                      # malformed, and fails closed
 261 | +
 262 | +    def test_must_fail_a_different_number(self):
 263 | +        d = self.decide(record(token="86000", decoder=("86000", "86000"), second=("68000", "86000")))
 264 | +        self.assertEqual(d["verdict"], "hold")                              # '68,000' is no truncation of '86,000'
 265 | +        self.assertIn("(3)", d["why"])
 266 | +
 267 | +    def test_must_fail_a_different_name(self):
 268 | +        for second in (("Taylor", "Saylor"), ("Say", "Saylor")):           # a name never qualifies, cut short or not
 269 | +            d = self.decide(record(token="Saylor", decoder=("Saylor", "Saylor"), second=second))
 270 | +            self.assertEqual(d["verdict"], "hold", second)
 271 | +            self.assertIn("a name never qualifies", d["why"])
 272 | +
 273 | +    def test_a_dropped_token_or_a_digit_cut_off_is_no_truncation(self):
 274 | +        for token, second in (("401k", ("", "401k")),                   # dropped
 275 | +                              ("4015", ("401", "4015")),                 # a digit cut off: another number
 276 | +                              ("401k", ("40", "401k"))):                 # '1k' cut off holds a digit
 277 | +            d = self.decide(record(token=token, decoder=(token, token), second=second))
 278 | +            self.assertEqual(d["verdict"], "hold", second)
 279 | +            self.assertIn("(3)", d["why"])
 280 | +
 281 | +    def test_an_unstable_decoder_holds(self):
 282 | +        d = self.decide(record(decoder=("401k", "401")))
 283 | +        self.assertEqual(d["verdict"], "hold")
 284 | +        self.assertIn("(1)", d["why"])
 285 | +
 286 | +    def test_the_second_recogniser_must_read_the_token_at_least_once(self):
 287 | +        d = self.decide(record(second=("401", "40l")))
 288 | +        self.assertEqual(d["verdict"], "hold")
 289 | +        self.assertIn("(2)", d["why"])
 290 | +
 291 | +    def test_too_few_readings_hold(self):
 292 | +        for dec, sec in (((), ("401", "401k")), (("401k",), ("401k",))):
 293 | +            d = self.decide(record(decoder=dec, second=sec))
 294 | +            self.assertEqual(d["verdict"], "hold", (dec, sec))
 295 | +            self.assertIn("too few readings", d["why"])
 296 | +
 297 | +    def test_the_records_own_tests_and_verdict_must_agree(self):
 298 | +        d = self.decide(record(tests={"decoder_stable": True, "second_unstable": True, "truncations_only": False}))
 299 | +        self.assertEqual(d["verdict"], "hold")
 300 | +        self.assertIn("own tests", d["why"])
 301 | +        d = self.decide(record(verdict="hold"))                          # a hold record under a pass outcome: hold
 302 | +        self.assertEqual(d["verdict"], "hold")
 303 | +        many = {"tokens": ["401k", "45"], "verdict": "hold", "why": "more than one disputed token"}
 304 | +        d = self.decide(many)                                               # the edge form
 305 | +        self.assertEqual(d["verdict"], "hold")
 306 | +        self.assertIn("more than one disputed token", d["why"])
 307 | +        for odd in ("pass", ["401k"], 7):                                   # not an object
 308 | +            self.assertEqual(self.decide(odd)["verdict"], "hold", odd)
 309 | +
 310 | +    def test_a_ruling_105_hold_stays_a_hold(self):
 311 | +        d = self.decide(record(second=("401", "401", "401"), verdict="hold"), outcome="hold")
 312 | +        self.assertEqual(d["verdict"], "hold")
 313 | +
 314 | +
 315 | +class TestTheRecordReachesTheSeal(Dirs):
 316 | +    def check(self, rec):
 317 | +        segs = LP.segments_of([HOOK, CLIP])
 318 | +        self.put(segs[0], entry(segs[0], unstable_second_reading=rec))
 319 | +        self.put(segs[1], entry(segs[1], unstable_second_reading=None))
 320 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 321 | +
 322 | +    def pk(self):
 323 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 324 | +                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}
 325 | +
 326 | +    def test_the_record_is_carried_as_it_stands_and_only_when_present(self):
 327 | +        pre = self.check(copy.deepcopy(BLOCKWARE))
 328 | +        self.assertTrue(pre["ok"])
 329 | +        self.assertEqual([r["unstable_second_reading"] for r in pre["segments"]], [BLOCKWARE, None])
 330 | +        pk = LP.apply(self.pk(), pre)
 331 | +        self.assertEqual(pk["segments"][0]["unstable_second_reading"], BLOCKWARE)
 332 | +        self.assertIsNot(pk["segments"][0]["unstable_second_reading"], pre["segments"][0]["unstable_second_reading"])
 333 | +        self.assertNotIn("unstable_second_reading", pk["segments"][1])
 334 | +        self.assertIsNone(LP.unstable_of({"unstable_second_reading": ["401k"]}))     # not an object: no record
 335 | +
 336 | +    def test_a_pass_this_side_refuses_never_reaches_a_pin(self):
 337 | +        pre = self.check(record(second=("401", "401", "401")))
 338 | +        self.assertFalse(pre["ok"])
 339 | +        self.assertEqual(pre["segments"][0]["verdict"], "hold")
 340 | +        with self.assertRaises(ValueError):
 341 | +            LP.apply(self.pk(), pre)
 342 | +
 343 | +    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
 344 | +        base = TA.TestPinAndTruth.pk(None)
 345 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")
 346 | +        self.assertNotIn("unstable_second_reading", plain["segments"][0])
 347 | +        with_r = copy.deepcopy(base)
 348 | +        with_r["segments"][0]["unstable_second_reading"] = copy.deepcopy(BLOCKWARE)
 349 | +        pin = package_pin.to_pin(with_r, "r")
 350 | +        self.assertEqual(pin["segments"][0]["unstable_second_reading"], BLOCKWARE)
 351 | +        sha = pin["moments_package"]["package_sha256"]
 352 | +        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
 353 | +        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
 354 | +        tampered = copy.deepcopy(pin)
 355 | +        tampered["segments"][0]["unstable_second_reading"]["second_readings"][2]["token"] = "401"
 356 | +        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
 357 | +        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])
 358 | +
 359 | +    def test_the_spotlight_now_rendering_still_recomputes_to_its_own_seal(self):
 360 | +        import json
 361 | +        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
 362 | +        pin = json.load(open(p))
 363 | +        self.assertEqual(package_pin.pin_seal(pin), pin["moments_package"]["package_sha256"])
 364 | +        self.assertTrue(pin["moments_package"]["package_sha256"].startswith("3f481f5a"))
 365 | +
 366 | +
 367 | +if __name__ == "__main__":
 368 | +    unittest.main()
 369 | 
```

---

pp-selectid, RULING 105 (the orchestrator, 20:13 ET Nov 14), the BUILDER's side. It lands in lockstep with the
integrator's pre-check: branch ruling105 d5bf9674, audited (its batch 84), FINAL decoder_sha a4c307f78c94..., RULES
"... + ruling 103 + ruling 105".

THE RULING: "when (1) the primary decoder's reading of the token is stable across its passes, (2) the second
recogniser's repeated readings of the SAME audio differ among themselves and at least one equals the lock's token,
and (3) every differing reading is a TRUNCATION of the lock's token (a prefix of the same term: '401' of '401k'), never
a different number or name, the token is adjudicated as the lock's and the clip may seal. All readings are recorded on
the pin (decoder passes, each scribe reading with its call id) under 'unstable_second_reading'. Anything else stays a
final hold: a second recogniser that is stable in its disagreement, a different number ('68,000' / '86,000'), a
different name. Must-fail tests for those three."

THE INTEGRATOR'S FIELD SHAPE (its message, 20:5x Nov 14): the result entry's key "unstable_second_reading" is null, or
{"token": str, "decoder_readings": [{"at", "source", "token"}], "second_readings": [{"at", "source", "token"}],
"tests": {"decoder_stable", "second_unstable", "truncations_only"}, "verdict": "pass" | "hold"}. The edge form for more
than one disputed token is {"tokens": [...], "verdict": "hold", "why": "..."}. A truncation is the token minus a
NON-DIGIT suffix only; names never qualify, nor does a dropped token. A ruling-105 pass leaves the normal outcome
(no_difference etc.); a ruling-105 hold is "hold".

THE CHANGE ON THIS SIDE:
- pipeline/lock_precheck.py:
  - DECODER and RULES as above.
  - _truncation(r, token) and ruling_105_fails(u): THIS side's own re-check of a pass that rests on the record (defence
    in depth, law L-j fail closed). decide() makes a PASS outcome a HOLD when the entry carries a record that does not
    hold on its own readings.
  - unstable_of(e): the record as it stands, or None when it is not an object.
  - check() rows carry it; apply() copies it onto the segment.
- pipeline/package_pin.py: SEALED_LATER and to_pin's carry gain "unstable_second_reading", only when present, so every
  pin without it seals as before.
- tests/package/test_lock_precheck.py: the literal decoder and rules; d1e155c642a6 joins the never-read decoders.
- tests/package/test_ruling_105.py (new): 16 tests, including the must-fail cases.

UNCHANGED GUARDS (you see only the diff):
- decide() handles a "hold" outcome after the PASS branch: it returns hold whatever the record says.
- apply() raises ValueError unless pre["ok"] is True, which needs every row to pass or adopt.
- package_pin.seal() adds a SEALED_LATER key to a segment's body only when the segment carries that key.
- The integrator's check_pin_only imports package_pin.py LIVE from this worktree, so the seal must stay backward
  compatible: the frozen 3f481f5a pin is tested to still recompute.

PLEASE CHECK:
(1) Does ruling_105_fails implement the three tests exactly, with no gap through which a different number, a name, or
    a stable disagreement passes? Can it refuse a record the integrator rightly passes, such as a token with a
    comma or other formatting?
(2) Is a pass outcome carrying a non-object record correctly a hold? Is a hold outcome never turned into a pass?
(3) Seal compatibility: can any existing pin's recompute change?
(4) Do the tests pin every branch? The mutation results are listed in the consensus file.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
