# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0915
# Branch: pp-selectid
# Generated: 2026-11-14 09:15 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0915/C1_STEP.diff (670 lines)
```
   1 | diff --git a/pipeline/moments_gate_adapter.py b/pipeline/moments_gate_adapter.py
   2 | index e66ded2..58ffc93 100644
   3 | --- a/pipeline/moments_gate_adapter.py
   4 | +++ b/pipeline/moments_gate_adapter.py
   5 | @@ -13,10 +13,16 @@ tests/package/run_exam_record.py, which strips "expected" exactly as the harness
   6 |  harness (PP_GATES_REPLAY=1). A gate that could not MEASURE (an exchange never recorded, every back-end unavailable, an
   7 |  unreadable verdict) RAISES GateNotMeasured, which the harness counts as an ERROR (audit p2 M5): it is never a pass and
   8 |  never a free rejection either (law L-m). A deterministic failure is a measured "fail".
   9 | +
  10 | +The orchestrator's 09:03 ET Nov 14 order: the exam runs heimdall_first, bounded by VENDOR-REPORTED dollars on its OWN
  11 | +ledger. make_router() is the ONE configuration the live recording (tests/package/run_exam_record.py) and the harness's
  12 | +offline replay both use, so the replay walks exactly the chains the recording walked.
  13 |  """
  14 |  import os
  15 | +import re
  16 |  
  17 |  import context_integrity as CI
  18 | +import eligibility as E
  19 |  import moments as M
  20 |  import providers as P
  21 |  import vo_fidelity as VF
  22 | @@ -27,6 +33,8 @@ RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "p
  23 |  SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
  24 |  ENV = P.ENV_PATH
  25 |  THREAD_SAFE = True                     # the router's ledger and recordings are safe across the harness's threads
  26 | +UNIVERSE_HOURS = 24.0                  # R-29: package.current_levels' window (L-v 3): a level only from news this fresh
  27 | +SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")   # R-29: a news headline / summary read sentence by sentence
  28 |  _router = None
  29 |  
  30 |  
  31 | @@ -34,14 +42,50 @@ class GateNotMeasured(Exception):
  32 |      """The gate could not measure this case (the harness's ERROR)."""
  33 |  
  34 |  
  35 | +def make_router(chains=None):
  36 | +    """The exam's router (the orchestrator's 09:03 order). Env: PP_GATES_ROUTING (default "heimdall_first"),
  37 | +    PP_GATES_LIMIT_USD (default 5.00, the exam's bound) counted on PP_GATES_LIMIT_BASIS (default "reported": the
  38 | +    vendors' own dollars), PP_GATES_SPEND (the exam's own ledger), PP_GATES_RECORD_DIR, PP_GATES_REPLAY=1 (offline).
  39 | +    chains: pinned legs (run_exam_record --chain), else the routing's own lists."""
  40 | +    return P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
  41 | +                    spend_path=SPEND, chains=chains or None,
  42 | +                    limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "5.00")),
  43 | +                    limit_basis=os.environ.get("PP_GATES_LIMIT_BASIS", "reported"),
  44 | +                    routing=os.environ.get("PP_GATES_ROUTING", "heimdall_first"))
  45 | +
  46 | +
  47 |  def router():
  48 |      global _router
  49 |      if _router is None:
  50 | -        _router = P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
  51 | -                           spend_path=SPEND, limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))
  52 | +        _router = make_router()
  53 |      return _router
  54 |  
  55 |  
  56 | +def universe_levels(universe, hours=UNIVERSE_HOURS):
  57 | +    """R-29 (pp-tests' REQUESTS; the orchestrator's 09:03 order "fix it now"): the Bitcoin price levels a v1.1 case's
  58 | +    universe (tonight's news) states as CURRENT, read the way package.current_levels reads sources: every sentence of a
  59 | +    news item's headline and summary that names Bitcoin (eligibility.names_bitcoin), from an item published at most
  60 | +    `hours` before the universe's own clock (built_at), through vo_fidelity.current_level_values. An item whose time
  61 | +    cannot be read is skipped, as package.current_levels skips such a source. [] is a measurement: no current level,
  62 | +    so any line stating a price as current fails PRICE_NOW. A universe with no zoned clock or no news list raises
  63 | +    ValueError: the harness's ERROR, never a guess."""
  64 | +    now = E._parse_time(universe["built_at"])
  65 | +    if now is None:
  66 | +        raise ValueError(f"the universe's clock built_at={universe.get('built_at')!r} is not a zoned time")
  67 | +    if not isinstance(universe["news"], list):
  68 | +        raise ValueError("the universe's news is not a list")
  69 | +    out = set()
  70 | +    for item in universe["news"]:
  71 | +        age = E.age_hours(item.get("published_at"), now)
  72 | +        if age is None or age > hours:
  73 | +            continue
  74 | +        for part in (item.get("headline") or "", item.get("summary") or ""):
  75 | +            for sentence in SENTENCE_SPLIT.split(part):
  76 | +                if sentence.strip() and E.names_bitcoin(sentence):
  77 | +                    out |= set(VF.current_level_values(sentence))
  78 | +    return sorted(out)
  79 | +
  80 | +
  81 |  def _join(sentences):
  82 |      return " ".join(s["text"] for s in sentences or [])
  83 |  
  84 | @@ -109,7 +153,13 @@ def vo_fidelity(case):
  85 |                                  "text": _join(s["sentences"])}
  86 |      lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
  87 |               for i, ln in enumerate(case["lines"])]
  88 | +    if case.get("title") is not None:            # R-29 (v1.1): the title is judged like a line, as the packager passes it
  89 | +        if not isinstance(case["title"], str) or not case["title"].strip():
  90 | +            raise ValueError("the case's title is not a non-empty string")
  91 | +        lines.append({"slot": "title", "text": case["title"], "cites": []})
  92 |      levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
  93 | +    if levels is None and case.get("universe") is not None:   # R-29 (v1.1): tonight's news gives the current levels
  94 | +        levels = universe_levels(case["universe"])
  95 |      try:
  96 |          res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
  97 |      except P.ReplayMiss as e:
  98 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  99 | index d2bb3d4..a3c929f 100644
 100 | --- a/pipeline/spotlight.py
 101 | +++ b/pipeline/spotlight.py
 102 | @@ -64,7 +64,9 @@ TRIM_MARGIN_S = 1.0                    # RULING 94 (a): a moment to be trimmed i
 103 |                                         # ONE trimmed word never takes it back under SNAP_TO_S
 104 |  LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
 105 |  LAYOUT_OK = ("conversation", "first_hand")
 106 | -CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 107 | +NEAR_CLIP_S = 300.0                    # RULING 92 AMENDED (09:03 Nov 14): "the 10 minutes around the clip", read as 5
 108 | +                                       # minutes each side of it; ZERO speaker changes there in a marked episode refuses
 109 | +                                       # (the 1.0-turns-a-minute line, CONVERSATION_TPM, is retired by the same ruling)
 110 |  FINALISTS = 3                          # moments taken to exclusion, the pre-check and the write, best first
 111 |  WRITES = 2                             # the title, caption and comment: one more write when a gate refuses them
 112 |  SCORER_WAIT_S = 600.0                  # a moment that passes everything but has no ALONE rating yet waits this long for
 113 | @@ -264,31 +266,73 @@ def episode_turns(video_id, captions_for=None):
 114 |              "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 115 |  
 116 |  
 117 | -def source_test(turns, layout):
 118 | -    """RULING 92 -> (ok, why). A PASS needs a MEASURED layout of a conversation or a first-hand statement
 119 | -    (LAYOUT_OK). A recap, a reaction, or a layout the judge cannot place ('other') fails on any channel; a layout that
 120 | -    is not measured is never a pass (law L-m). The caption markers across the episode can only make it stricter: a
 121 | -    layout read as a conversation from an episode whose captions are marked but carry fewer than CONVERSATION_TPM
 122 | -    turns a minute is not measured as a conversation (Nov 13: Simply Bitcoin's solo recap L6H7538ogGs 0.48 turns a
 123 | -    minute; the pool's interviews and panels 1.18-2.53). Unmarked captions are unknown, not solo: the layout decides."""
 124 | +def caption_evidence(video_id, start, end, captions_for=None):
 125 | +    """RULING 92 AMENDED (09:03 Nov 14): the caption markers are EVIDENCE for the layout judge, not a refusal line. Read
 126 | +    from the episode's caption record with speaker-change markers (speakers.captions, ruling 69's reader): the turns a
 127 | +    minute across the episode; the speaker changes in the 10 minutes around the clip (NEAR_CLIP_S each side of
 128 | +    [start, end]); and whether the clip's own span sits inside one unbroken turn (no marker more than MARKER_TOL_S
 129 | +    inside an edge). -> {"measured", "marked", ...}: marked False when no copy of the captions carries any marker
 130 | +    (unknown, never solo: no evidence either way); measured False when the record cannot be read."""
 131 | +    import speakers as SP
 132 | +    try:
 133 | +        units, rec = (captions_for or SP.captions)(video_id)
 134 | +    except Exception as e:                             # noqa: BLE001  unreadable: no evidence, never a refusal
 135 | +        return {"measured": False, "marked": None, "why": f"{type(e).__name__}: {str(e)[:120]}"}
 136 | +    if not units:
 137 | +        return {"measured": True, "marked": False,
 138 | +                "why": "no caption record with speaker-change markers: unmarked (unknown, never solo)"}
 139 | +    opens = [u[0] for u in units if u[2]]
 140 | +    minutes = (units[-1][0] - units[0][0]) / 60.0
 141 | +    return {"measured": True, "marked": True, "turns": len(opens), "minutes": round(minutes, 1),
 142 | +            "turns_per_min": round(len(opens) / minutes, 2) if minutes > 0 else None,
 143 | +            "changes_near": sum(1 for t in opens if start - NEAR_CLIP_S <= t <= end + NEAR_CLIP_S),
 144 | +            "one_turn": not any(start + MARKER_TOL_S < t < end - MARKER_TOL_S for t in opens),
 145 | +            "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 146 | +
 147 | +
 148 | +def markers_refuse(evidence):
 149 | +    """RULING 92 AMENDED: the ONE case where the caption markers refuse by themselves: the episode is marked and has
 150 | +    ZERO speaker changes in the 10 minutes around the clip."""
 151 | +    ev = evidence or {}
 152 | +    return ev.get("measured") is True and ev.get("marked") is True and ev.get("changes_near") == 0
 153 | +
 154 | +
 155 | +def evidence_text(evidence):
 156 | +    """The caption evidence as the layout judge reads it (one sentence)."""
 157 | +    ev = evidence or {}
 158 | +    if ev.get("measured") is not True:
 159 | +        return "the captions could not be read (no evidence either way)."
 160 | +    if not ev.get("marked"):
 161 | +        return "the captions carry no speaker-change markers (no evidence either way)."
 162 | +    return (f"{ev.get('turns_per_min')} speaker turns a minute across the episode ({ev.get('turns')} in "
 163 | +            f"{ev.get('minutes')} min); {ev.get('changes_near')} speaker change(s) in the 10 minutes around this clip; "
 164 | +            f"the clip's own words sit inside one unbroken turn: {'yes' if ev.get('one_turn') else 'no'}.")
 165 | +
 166 | +
 167 | +def source_test(evidence, layout):
 168 | +    """RULING 92 AMENDED (09:03 Nov 14) -> (ok, why). The LAYOUT verdict decides the source test alone: a MEASURED
 169 | +    layout of a conversation or a first-hand statement (LAYOUT_OK) passes; a recap, a reaction or 'other' fails on any
 170 | +    channel; a layout that is not measured never passes (law L-m). The caption markers are EVIDENCE shown to the
 171 | +    layout judge (layout_for), not a refusal line (the 1.0-turns-a-minute line refused real interviews: 19 of 67
 172 | +    videos at 0.3-1.0); they refuse by themselves only when the episode is marked and has ZERO speaker changes in the
 173 | +    10 minutes around the clip (markers_refuse)."""
 174 | +    if markers_refuse(evidence):
 175 | +        return False, (f"the episode's captions are marked ({evidence.get('turns')} turns in "
 176 | +                       f"{evidence.get('minutes')} min) and show no speaker change in the 10 minutes around the clip")
 177 |      if not (layout or {}).get("measured"):
 178 |          return False, f"the layout is not measured: {(layout or {}).get('why')}"
 179 |      lay = layout["layout"]
 180 |      if lay not in LAYOUT_OK:
 181 |          return False, f"the layout is '{lay}' ({layout.get('why')}): not a conversation or a first-hand statement"
 182 | -    tpm = (turns or {}).get("turns_per_min")
 183 | -    if lay == "conversation" and (turns or {}).get("measured") and (tpm is None or tpm < CONVERSATION_TPM):
 184 | -        return False, (f"the frames read as a conversation but the episode's captions carry {tpm} speaker turns a "
 185 | -                       f"minute (under {CONVERSATION_TPM:g})")
 186 | -    return True, f"layout '{lay}'" + (f"; {turns['turns']} caption turns in {turns['minutes']} min ({tpm} a minute)"
 187 | -                                      if (turns or {}).get("measured") else "; captions unmarked")
 188 | +    return True, f"layout '{lay}'; the captions' evidence: {evidence_text(evidence)}"
 189 |  
 190 |  
 191 |  def next_attempt(rows, word_pass, now, captions_for=None):
 192 |      """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 193 | -    could arrive. The NEWEST conversation upload among the adapter's rows: caption turns from pp-ingest's `episode`
 194 | -    (mine-hook/2 rows), else episode_turns(), at least CONVERSATION_TPM a minute (an unmarked episode is not counted:
 195 | -    unknown). Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 196 | +    could arrive. The NEWEST upload among the adapter's rows whose captions do not refuse it (RULING 92 AMENDED, 09:03
 197 | +    Nov 14: unmarked, or marked with at least one speaker change; the layout decides per clip), its caption turns from
 198 | +    pp-ingest's `episode` (mine-hook/2 rows), else episode_turns(): an episode marked with zero turns is the one
 199 | +    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 200 |      waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 201 |      "newest_upload": {...} or None}."""
 202 |      from datetime import datetime, timedelta, timezone
 203 | @@ -318,14 +362,16 @@ def next_attempt(rows, word_pass, now, captions_for=None):
 204 |                  "turns_per_min": tpm, "turns_from": frm, "rows": len(rs), "passes": passes,
 205 |                  "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 206 |      sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 207 | -    conv = [x for x in sts if isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] >= CONVERSATION_TPM]
 208 | +    conv = [x for x in sts if not (isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] <= 0)]
 209 |      return {"conversation": conv[0] if conv else None, "newest_upload": sts[0] if sts else None,
 210 | -            "rule": f"the newest upload with >= {CONVERSATION_TPM:g} caption turns a minute (ruling 95)"}
 211 | +            "rule": "the newest upload whose captions do not refuse it (unmarked, or marked with a speaker change; "
 212 | +                    "ruling 92 amended: the layout decides per clip) (ruling 95)"}
 213 |  
 214 |  
 215 |  LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 216 |  bottom. The clip's words, as spoken: "{text}"
 217 | -From the frames only, classify the SOURCE's format:
 218 | +Evidence from the episode's captions (their speaker-change markers), to weigh with the frames: {evidence}
 219 | +From the frames and that evidence, classify the SOURCE's format:
 220 |  - "conversation": two or more people talking with each other: an interview, a podcast, a panel (in one room, or on a
 221 |    split screen or a video call);
 222 |  - "first_hand": one person making their own statement to an audience: a keynote, a speech, a guest answering on a news
 223 | @@ -359,18 +405,21 @@ def _load_json(path):
 224 |          return {}
 225 |  
 226 |  
 227 | -def layout_for(router, m, vrec, cache_path=None, seed=7):
 228 | +def layout_for(router, m, vrec, cache_path=None, seed=7, evidence=None):
 229 |      """RULING 92's visual half: the source's layout, judged on the clip's own contact sheet (the visual check's, ruling
 230 |      70: the same bytes it judged) with LAYOUT_PROMPT, by the visual_check role (one call, cached by the moment, the
 231 | -    sheet's sha256 and the prompt's version). -> {"measured", "layout", "people_on_screen", "why", "backend",
 232 | -    "replayed"} or {"measured": False, "why"}: never a pass unmeasured."""
 233 | +    sheet's sha256, the prompt's version and the evidence shown). RULING 92 AMENDED (09:03 Nov 14): the judge also
 234 | +    reads the caption markers as EVIDENCE (caption_evidence, evidence_text: turns a minute, changes near the clip, one
 235 | +    unbroken turn), never as a refusal line. -> {"measured", "layout", "people_on_screen", "why", "backend",
 236 | +    "replayed", "evidence"} or {"measured": False, "why"}: never a pass unmeasured."""
 237 |      import providers as Pr
 238 |      from story_semantics import quote_data
 239 |      sheet = (vrec or {}).get("sheet") or {}
 240 |      path, sha = sheet.get("path"), sheet.get("sha256")
 241 |      if not (vrec or {}).get("measured") or not path or not sha:
 242 |          return {"measured": False, "why": "no judged contact sheet (the visual check is not measured)"}
 243 | -    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}"
 244 | +    ev_text = evidence_text(evidence)              # the same evidence, the same key (captions can arrive later)
 245 | +    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}:{hashlib.sha256(ev_text.encode()).hexdigest()[:12]}"
 246 |      hit = _load_json(cache_path).get(k) if cache_path else None
 247 |      if isinstance(hit, dict) and hit.get("measured") is True:
 248 |          return dict(hit, cached=True)
 249 | @@ -382,7 +431,8 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
 250 |      if hashlib.sha256(raw).hexdigest() != sha:
 251 |          return {"measured": False, "why": "the sheet on disk is not the one the visual check judged"}
 252 |      prompt = {"text": LAYOUT_PROMPT.format(n=len(sheet.get("times") or []),
 253 | -                                           text=quote_data(m.get("text") or "", 700).replace('"', "'")),
 254 | +                                           text=quote_data(m.get("text") or "", 700).replace('"', "'"),
 255 | +                                           evidence=ev_text),
 256 |                "images": [base64.b64encode(raw).decode()]}
 257 |      r = None
 258 |      try:
 259 | @@ -393,7 +443,7 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
 260 |              router.reject(r)
 261 |          return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 262 |      rec = dict(v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
 263 | -               version=LAYOUT_VERSION, sheet_sha256=sha)
 264 | +               version=LAYOUT_VERSION, sheet_sha256=sha, evidence=ev_text)
 265 |      if cache_path and not rec["replayed"]:
 266 |          with LAYOUT_LOCK:
 267 |              c = _load_json(cache_path)
 268 | @@ -683,8 +733,10 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 269 |      rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 270 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 271 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 272 | -                                    why=src_rec.get("why"), turns=src_rec.get("turns"), layout=src_rec.get("layout"),
 273 | -                                    rule="ruling 92: conversation, not reaction (caption turns + the layout)")
 274 | +                                    why=src_rec.get("why"), evidence=src_rec.get("evidence"), layout=src_rec.get("layout"),
 275 | +                                    rule="ruling 92 amended (09:03 Nov 14): the layout decides (conversation or "
 276 | +                                         "first-hand); the captions are evidence, refusing alone only with zero "
 277 | +                                         "speaker changes in the 10 minutes around the clip")
 278 |      rows["window_12h"] = _row(not PP.window_problems(pk["segments"], facts["now"]),
 279 |                                "code (package_pin.window_problems, ruling 76: <= 12 h on the render clock)",
 280 |                                why=PP.window_problems(pk["segments"], facts["now"]))
 281 | @@ -880,11 +932,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 282 |                    " (asked with the build's scorer candidates)"))
 283 |      passed(fine, 7)
 284 |      ok_src = []
 285 | -    for mid, m in fine.items():
 286 | -        turns = episode_turns(m["video_id"], captions_for)
 287 | -        lay = layout_for(router, m, m.get("visual"), layout_cache)
 288 | -        ok, w = source_test(turns, lay)
 289 | -        m["spotlight_source"] = {"ok": ok, "why": w, "turns": turns, "layout": lay}
 290 | +    for mid, m in fine.items():                        # RULING 92 AMENDED (09:03 Nov 14): the captions as evidence
 291 | +        ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
 292 | +        lay = ({"measured": False, "why": "not asked: the captions refuse the source by themselves"}
 293 | +               if markers_refuse(ev) else                # free, so a refused source never costs a vision call
 294 | +               layout_for(router, m, m.get("visual"), layout_cache, evidence=ev))
 295 | +        ok, w = source_test(ev, lay)
 296 | +        m["spotlight_source"] = {"ok": ok, "why": w, "evidence": ev, "layout": lay}
 297 |          rec[mid]["source"] = w
 298 |          if ok:
 299 |              ok_src.append(m)
 300 | diff --git a/tests/package/run_exam_record.py b/tests/package/run_exam_record.py
 301 | index 9dbc65a..d4de7f6 100644
 302 | --- a/tests/package/run_exam_record.py
 303 | +++ b/tests/package/run_exam_record.py
 304 | @@ -51,8 +51,8 @@ def main(argv=None):
 305 |      for x in a.chain:
 306 |          role, backend = x.split("=", 1)
 307 |          chains.setdefault(role, []).append(backend)
 308 | -    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND, chains=chains or None,
 309 | -                         limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))     # the phase-2 guard
 310 | +    A._router = A.make_router(chains=chains or None)    # the harness's own configuration (the orchestrator's 09:03
 311 | +    #   order: heimdall_first, vendor-reported dollars, the exam's own ledger), so its replay walks these chains
 312 |      os.makedirs(a.out, exist_ok=True)
 313 |      log = []
 314 |      for corpus, gate in GATES:
 315 | diff --git a/tests/package/test_exam_adapter.py b/tests/package/test_exam_adapter.py
 316 | new file mode 100644
 317 | index 0000000..12078e9
 318 | --- /dev/null
 319 | +++ b/tests/package/test_exam_adapter.py
 320 | @@ -0,0 +1,165 @@
 321 | +#!/usr/bin/env python3
 322 | +"""pp-tests' REQUESTS R-29 and the exam's router (the orchestrator's 09:03 ET Nov 14 order: "R-29: FIX IT NOW";
 323 | +"THE EXAM: APPROVED ... heimdall_first, bound $5.00 vendor-reported, on its OWN ledger"):
 324 | +pipeline/moments_gate_adapter.py, the one adapter of pp-tests' moments exam, predated vo_fidelity v1.1. Its
 325 | +vo_fidelity() passed no title and no current price levels from the case's universe, so the must-fail cases built on
 326 | +them were never judged on them. Now: the title is judged like a line (as the packager passes it); the universe's news
 327 | +gives the current levels the way package.current_levels reads sources; v1 cases are unchanged; one router
 328 | +configuration serves the live recording and the offline replay."""
 329 | +import os
 330 | +import shutil
 331 | +import sys
 332 | +import tempfile
 333 | +import unittest
 334 | +from unittest import mock
 335 | +
 336 | +HERE = os.path.dirname(os.path.abspath(__file__))
 337 | +REPO = os.path.dirname(os.path.dirname(HERE))
 338 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 339 | +sys.path.insert(0, HERE)
 340 | +import moments_gate_adapter as A  # noqa: E402
 341 | +import vo_fidelity as VF  # noqa: E402
 342 | +
 343 | +PASS = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "fake",
 344 | +        "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 345 | +        "verdict": {"ok": True, "violations": [], "classes": {}, "claims": []}}
 346 | +SEGS = [{"label": "A", "channel": "Coin Bureau", "video_id": "va", "speaker": None,
 347 | +         "sentences": [{"n": 0, "text": "Bitcoin closed just under 76K on the day."}]},
 348 | +        {"label": "B", "channel": "Swan Bitcoin", "video_id": "vb", "speaker": None,
 349 | +         "sentences": [{"n": 0, "text": "We were around $76,000 by the U.S. close."}]}]
 350 | +LINES = [{"slot": "intro", "text": "Coin Bureau, then Swan Bitcoin.", "cites": ["A", "B"], "after": None},
 351 | +         {"slot": "signoff", "text": "That's Pulse Check.", "cites": [], "after": "B"}]
 352 | +# the real stale_price_title__01's title and universe (pp-tests' corpus, v1.1): its $73,500 news is 38 h old
 353 | +UNIVERSE = {"built_at": "2026-11-12T05:06:13.234375+00:00", "date": "2026-11-12", "use": "staleness only",
 354 | +            "news": [{"headline": "Bitcoin Price Trades Down Near $73,500 After Hot CPI Print Lifts Fed Hike Bets",
 355 | +                      "published_at": "2026-11-10T14:28:12.195473+00:00",
 356 | +                      "summary": "Bitcoin price slipped to $73,500 Tuesday morning."},
 357 | +                     {"headline": "Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'",
 358 | +                      "published_at": "2026-11-11T21:46:12.195473+00:00",
 359 | +                      "summary": "Stablecoin supply fell $14.2 billion in 30 days."}]}
 360 | +
 361 | +
 362 | +def v11(**over):
 363 | +    return dict({"schema": "pp.vo_case/1.1", "id": "case-x", "segments": SEGS, "lines": LINES,
 364 | +                 "manifest": {"show": "Pulse Check", "date": "2026-11-12", "channels": ["Coin Bureau", "Swan Bitcoin"]},
 365 | +                 "title": "Bitcoin ran from 16K to 126K", "universe": UNIVERSE}, **over)
 366 | +
 367 | +
 368 | +class Capture:
 369 | +    """VF.check as the adapter calls it: the arguments kept, a measured pass returned."""
 370 | +
 371 | +    def __init__(self):
 372 | +        self.calls = []
 373 | +
 374 | +    def __call__(self, router, segments, lines, writer_vendor=None, manifest=None, current_levels=None, **k):
 375 | +        self.calls.append({"segments": segments, "lines": lines, "manifest": manifest, "levels": current_levels})
 376 | +        return PASS
 377 | +
 378 | +
 379 | +class TestR29(unittest.TestCase):
 380 | +    def run_case(self, case):
 381 | +        cap = Capture()
 382 | +        with mock.patch.object(A.VF, "check", cap), mock.patch.object(A, "router", lambda: object()):
 383 | +            out = A.vo_fidelity(case)
 384 | +        return out, cap.calls
 385 | +
 386 | +    def test_the_title_is_judged_like_a_line_and_the_universe_gives_the_levels(self):
 387 | +        out, calls = self.run_case(v11())
 388 | +        self.assertEqual(out["verdict"], "pass")
 389 | +        lines = calls[0]["lines"]
 390 | +        self.assertEqual(lines[-1], {"slot": "title", "text": "Bitcoin ran from 16K to 126K", "cites": []})
 391 | +        self.assertEqual([x["slot"] for x in lines], ["intro_0", "signoff_1", "title"])
 392 | +        self.assertEqual(calls[0]["levels"], [])           # measured: no level inside 24 h (not None: not measured)
 393 | +
 394 | +    def test_a_v1_case_is_unchanged(self):
 395 | +        case = {k: v for k, v in v11().items() if k not in ("title", "universe")}
 396 | +        _, calls = self.run_case(case)
 397 | +        self.assertEqual([x["slot"] for x in calls[0]["lines"]], ["intro_0", "signoff_1"])
 398 | +        self.assertIsNone(calls[0]["levels"])               # as before: price_now not measured without a universe
 399 | +
 400 | +    def test_explicit_current_levels_still_win(self):
 401 | +        _, calls = self.run_case(v11(current_levels=[90000.0]))
 402 | +        self.assertEqual(calls[0]["levels"], [90000.0])
 403 | +
 404 | +    def test_the_universe_reads_like_package_current_levels(self):
 405 | +        fresh = {"headline": "Bitcoin is trading at $73,500 this morning.", "summary": "",
 406 | +                 "published_at": "2026-11-12T01:00:00+00:00"}
 407 | +        u = dict(UNIVERSE, news=UNIVERSE["news"] + [fresh])
 408 | +        self.assertEqual(A.universe_levels(u), [73500.0])   # inside 24 h of built_at; the 38 h old one is not
 409 | +        not_btc = dict(fresh, headline="Ethereum is trading at $73,500 this morning.")   # a level, but not Bitcoin's
 410 | +        self.assertEqual(VF.current_level_values(not_btc["headline"]), [73500.0])
 411 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[not_btc])), [])
 412 | +        unreadable = dict(fresh, published_at="yesterday")
 413 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[unreadable, fresh])), [73500.0])   # skipped
 414 | +        zoneless = dict(fresh, published_at="2026-11-12T01:00:00")
 415 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[zoneless])), [])   # no zone, no measurement
 416 | +        late = dict(fresh, published_at="2026-11-12T09:00:00+00:00")   # after built_at: inside (as for sources)
 417 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[late])), [73500.0])
 418 | +
 419 | +    def test_an_unreadable_case_is_the_harness_error_never_a_guess(self):
 420 | +        for bad in (v11(title=""), v11(title=5), v11(universe=dict(UNIVERSE, built_at="2026-11-12")),
 421 | +                    v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")), v11(universe={"news": []}),
 422 | +                    v11(universe=dict(UNIVERSE, news="none"))):
 423 | +            with self.assertRaises(A.GateNotMeasured, msg=str(bad.get("title"))):
 424 | +                self.run_case(bad)
 425 | +        with self.assertRaisesRegex(A.GateNotMeasured, "not a zoned time"):           # said plainly, never a guess
 426 | +            self.run_case(v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")))
 427 | +
 428 | +    def test_the_real_stale_title_case_now_fails_on_its_title_deterministically(self):
 429 | +        """No model: the deterministic layer on the lines the adapter now passes (the 16K / 126K title against the
 430 | +        clips' 76K, with the universe's measured [] levels)."""
 431 | +        _, calls = self.run_case(v11())
 432 | +        c = calls[0]
 433 | +        det = VF.check_deterministic(c["segments"], c["lines"], c["manifest"], c["levels"])
 434 | +        rules = {v["rule"] for v in det["violations"] if v["slot"] == "title"}
 435 | +        self.assertTrue({"NUMBER", "PRICE_NOW"} <= rules, rules)
 436 | +        old = [x for x in c["lines"] if x["slot"] != "title"]   # the old adapter's lines: the title never judged
 437 | +        self.assertFalse([v for v in VF.check_deterministic(c["segments"], old, c["manifest"], None)["violations"]
 438 | +                          if v["slot"] == "title"])
 439 | +
 440 | +
 441 | +class TestExamRouter(unittest.TestCase):
 442 | +    def setUp(self):
 443 | +        self.d = tempfile.mkdtemp()
 444 | +        self.p = [mock.patch.object(A, "SPEND", os.path.join(self.d, "SPEND.json")),
 445 | +                  mock.patch.object(A, "RECORD", os.path.join(self.d, "replies"))]
 446 | +        for p in self.p:
 447 | +            p.start()
 448 | +
 449 | +    def tearDown(self):
 450 | +        for p in self.p:
 451 | +            p.stop()
 452 | +        shutil.rmtree(self.d, ignore_errors=True)
 453 | +
 454 | +    def test_heimdall_first_on_vendor_reported_dollars_bounded_at_5(self):
 455 | +        with mock.patch.dict(os.environ, {}, clear=False):
 456 | +            for k in ("PP_GATES_ROUTING", "PP_GATES_LIMIT_USD", "PP_GATES_LIMIT_BASIS", "PP_GATES_REPLAY"):
 457 | +                os.environ.pop(k, None)
 458 | +            r = A.make_router()
 459 | +        self.assertEqual((r.routing, r.limit_basis, r.limit_usd), ("heimdall_first", "reported", 5.0))
 460 | +        self.assertEqual(r.chain("context_verdict", "step_c")[0], "xai:grok-4.20-0309-reasoning")   # routed lists
 461 | +        with mock.patch.dict(os.environ, {"PP_GATES_ROUTING": "today", "PP_GATES_LIMIT_USD": "4.00",
 462 | +                                          "PP_GATES_REPLAY": "1"}):
 463 | +            r = A.make_router()
 464 | +        self.assertEqual((r.routing, r.limit_usd, r.replay), ("today", 4.0, True))
 465 | +
 466 | +    def test_the_recorder_and_the_harness_share_one_router(self):
 467 | +        import run_exam_record as RX
 468 | +        made = []
 469 | +
 470 | +        def fake(chains=None):
 471 | +            made.append(chains)
 472 | +            return mock.Mock(notices=[])
 473 | +
 474 | +        def no_network(*a, **k):
 475 | +            raise AssertionError("no network in this test")
 476 | +        corpus, out = os.path.join(self.d, "corpus"), os.path.join(self.d, "out")
 477 | +        os.makedirs(corpus)
 478 | +        with mock.patch.object(A, "make_router", fake), mock.patch("urllib.request.urlopen", no_network):
 479 | +            self.assertEqual(RX.main(["--corpus", corpus, "--out", out]), 0)
 480 | +            self.assertEqual(RX.main(["--corpus", corpus, "--out", out, "--chain", "context_verdict=xai:x"]), 0)
 481 | +        self.assertEqual(made, [None, {"context_verdict": ["xai:x"]}])
 482 | +
 483 | +
 484 | +if __name__ == "__main__":
 485 | +    unittest.main()
 486 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 487 | index 7a7d327..afb5318 100644
 488 | --- a/tests/package/test_spotlight.py
 489 | +++ b/tests/package/test_spotlight.py
 490 | @@ -283,25 +283,98 @@ class TestSourceTest(unittest.TestCase):
 491 |      def lay(self, kind):
 492 |          return {"measured": True, "layout": kind, "why": "w", "backend": "b", "replayed": False}
 493 |  
 494 | +    UNMARKED = {"measured": True, "marked": False}
 495 | +
 496 | +    @staticmethod
 497 | +    def marked(tpm, near, one_turn=True):
 498 | +        return {"measured": True, "marked": True, "turns": 10, "minutes": 10.0, "turns_per_min": tpm,
 499 | +                "changes_near": near, "one_turn": one_turn}
 500 | +
 501 |      def test_conversation_or_first_hand_pass_and_recap_reaction_other_fail(self):
 502 | -        unmarked = {"measured": False, "unmarked": True}
 503 |          for kind, want in (("conversation", True), ("first_hand", True), ("recap", False), ("reaction", False),
 504 |                             ("other", False)):
 505 | -            self.assertEqual(SPOT.source_test(unmarked, self.lay(kind))[0], want, kind)
 506 | +            self.assertEqual(SPOT.source_test(self.UNMARKED, self.lay(kind))[0], want, kind)
 507 |  
 508 |      def test_an_unmeasured_layout_is_never_a_pass(self):
 509 | -        ok, why = SPOT.source_test({"measured": True, "turns": 30, "minutes": 10, "turns_per_min": 3.0},
 510 | -                                   {"measured": False, "why": "no sheet"})
 511 | +        ok, why = SPOT.source_test(self.marked(3.0, 4), {"measured": False, "why": "no sheet"})
 512 |          self.assertFalse(ok)
 513 |          self.assertIn("not measured", why)
 514 |  
 515 | -    def test_the_markers_only_make_it_stricter(self):
 516 | -        solo = {"measured": True, "turns": 8, "minutes": 16.5, "turns_per_min": 0.48}     # Nov 13: L6H7538ogGs
 517 | -        talk = {"measured": True, "turns": 20, "minutes": 16.8, "turns_per_min": 1.19}    # Nov 13: 3kV3nWC5SAY
 518 | -        self.assertFalse(SPOT.source_test(solo, self.lay("conversation"))[0])
 519 | -        self.assertTrue(SPOT.source_test(talk, self.lay("conversation"))[0])
 520 | -        self.assertTrue(SPOT.source_test(solo, self.lay("first_hand"))[0])       # a keynote is one voice
 521 | -        self.assertFalse(SPOT.source_test(talk, self.lay("recap"))[0])
 522 | +    def test_ruling_92_amended_the_layout_decides_and_the_1_0_line_is_retired(self):
 523 | +        """09:03 Nov 14: the 1.0 line was drawn from one solo recap at 0.48 and refused real interviews (Bitcoin
 524 | +        Magazine's, CoinDesk's, Pompliano at 0.97). Turns a minute are evidence now, never a refusal line."""
 525 | +        for tpm in (0.48, 0.61, 0.97, 1.19):
 526 | +            self.assertTrue(SPOT.source_test(self.marked(tpm, 2), self.lay("conversation"))[0], tpm)
 527 | +            self.assertFalse(SPOT.source_test(self.marked(tpm, 2), self.lay("recap"))[0], tpm)
 528 | +        self.assertTrue(SPOT.source_test(self.marked(0.3, 1, one_turn=False), self.lay("first_hand"))[0])
 529 | +
 530 | +    def test_the_markers_refuse_alone_only_with_zero_changes_in_the_10_minutes_around_the_clip(self):
 531 | +        ok, why = SPOT.source_test(self.marked(2.5, 0), self.lay("conversation"))
 532 | +        self.assertFalse(ok)                                   # even a conversation layout: zero changes near the clip
 533 | +        self.assertIn("no speaker change in the 10 minutes around the clip", why)
 534 | +        self.assertTrue(SPOT.source_test(self.marked(0.2, 1), self.lay("conversation"))[0])   # one change: the layout
 535 | +        for unknown in (self.UNMARKED, {"measured": False, "marked": None, "why": "unreadable"}, None, {}):
 536 | +            self.assertFalse(SPOT.markers_refuse(unknown), unknown)    # no evidence is never a refusal
 537 | +            self.assertTrue(SPOT.source_test(unknown, self.lay("conversation"))[0], unknown)
 538 | +        self.assertFalse(SPOT.markers_refuse(dict(self.marked(1.0, 0), measured=False)))   # unmeasured counts nothing
 539 | +
 540 | +
 541 | +class TestCaptionEvidence(unittest.TestCase):
 542 | +    """RULING 92 AMENDED (09:03 Nov 14): the caption markers read as EVIDENCE for the layout judge."""
 543 | +    UNITS = [(0.0, "a", True), (100.0, "b", False), (400.0, "c", True), (900.0, "d", True), (1500.0, "e", False)]
 544 | +
 545 | +    def ev(self, start, end, units=None):
 546 | +        return SPOT.caption_evidence("v", start, end, captions_for=lambda vid: (
 547 | +            self.UNITS if units is None else units, {"file": "f", "sha256": "s"}))
 548 | +
 549 | +    def test_turns_a_minute_changes_near_the_clip_and_one_unbroken_turn(self):
 550 | +        e = self.ev(420.0, 440.0)                  # markers at 0, 400, 900; the 10 minutes around it: 120-740 s
 551 | +        self.assertEqual((e["marked"], e["turns"], e["minutes"], e["turns_per_min"]), (True, 3, 25.0, 0.12))
 552 | +        self.assertEqual((e["changes_near"], e["one_turn"]), (1, True))
 553 | +        self.assertFalse(SPOT.markers_refuse(e))
 554 | +        e = self.ev(890.0, 910.0)                  # the 900 s marker falls inside the clip
 555 | +        self.assertEqual((e["changes_near"], e["one_turn"]), (1, False))
 556 | +        e = self.ev(1300.0, 1320.0)                # 1000-1620 s: no marker
 557 | +        self.assertEqual(e["changes_near"], 0)
 558 | +        self.assertTrue(SPOT.markers_refuse(e))
 559 | +        self.assertEqual(self.ev(899.5, 920.0)["one_turn"], True)   # a marker within MARKER_TOL_S of an edge is not in
 560 | +
 561 | +    def test_unmarked_or_unreadable_captions_are_no_evidence(self):
 562 | +        e = SPOT.caption_evidence("v", 1.0, 2.0, captions_for=lambda vid: (None, None))
 563 | +        self.assertEqual((e["measured"], e["marked"]), (True, False))
 564 | +        self.assertFalse(SPOT.markers_refuse(e))
 565 | +
 566 | +        def boom(vid):
 567 | +            raise OSError("disk")
 568 | +        e = SPOT.caption_evidence("v", 1.0, 2.0, captions_for=boom)
 569 | +        self.assertEqual((e["measured"], e["marked"]), (False, None))
 570 | +        self.assertFalse(SPOT.markers_refuse(e))
 571 | +
 572 | +    def test_the_layout_judge_reads_the_evidence_and_its_cache_keys_on_it(self):
 573 | +        import hashlib
 574 | +        d = tempfile.mkdtemp()
 575 | +        try:
 576 | +            sheet = os.path.join(d, "sheet.jpg")
 577 | +            with open(sheet, "wb") as f:
 578 | +                f.write(b"jpeg-bytes")
 579 | +            vrec = {"measured": True, "sheet": {"path": sheet, "sha256": hashlib.sha256(b"jpeg-bytes").hexdigest(),
 580 | +                                                "times": [0.0, 1.0]}}
 581 | +            ans = '{"layout": "conversation", "people_on_screen": 2, "why": "two people"}'
 582 | +            r = Router(visual_check=[ans, ans])
 583 | +            seen, inner = [], r.call
 584 | +            r.call = lambda role, prompt, *a, **k: (seen.append(prompt["text"]), inner(role, prompt, *a, **k))[1]
 585 | +            cache, m = os.path.join(d, "LAYOUT_CACHE.json"), {"moment_id": "m1", "text": "We talked about it."}
 586 | +            e1 = self.ev(420.0, 440.0)
 587 | +            self.assertEqual(SPOT.layout_for(r, m, vrec, cache, evidence=e1)["layout"], "conversation")
 588 | +            self.assertIn("0.12 speaker turns a minute across the episode (3 in 25.0 min)", seen[0])
 589 | +            self.assertIn("1 speaker change(s) in the 10 minutes around this clip", seen[0])
 590 | +            self.assertIn("inside one unbroken turn: yes", seen[0])
 591 | +            self.assertTrue(SPOT.layout_for(r, m, vrec, cache, evidence=e1).get("cached"))     # same evidence: cached
 592 | +            SPOT.layout_for(r, m, vrec, cache, evidence={"measured": True, "marked": False})  # other evidence: asked
 593 | +            self.assertEqual(len(seen), 2)
 594 | +            self.assertIn("no speaker-change markers (no evidence either way)", seen[1])
 595 | +        finally:
 596 | +            shutil.rmtree(d, ignore_errors=True)
 597 |  
 598 |  
 599 |  class TestContracts(unittest.TestCase):
 600 | @@ -456,7 +529,7 @@ class TestRuling94And95(unittest.TestCase):
 601 |                   "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 602 |                                                                                  "prompt_version": "mine-hook/2"}},
 603 |                  {"video_id": "new", "channel_name": "Solo", "published_at": "2026-11-13T22:00:00+00:00",
 604 | -                 "moment_id": "n1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "moment",
 605 | +                 "moment_id": "n1", "episode": {"turns_per_min": 0.0}, "mined": {"pass": "moment",
 606 |                                                                                  "prompt_version": "mine/2"}},
 607 |                  {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 608 |                   "moment_id": "m1", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "hook",
 609 | @@ -470,7 +543,12 @@ class TestRuling94And95(unittest.TestCase):
 610 |                           ("mid", "2026-11-13T20:00:00Z", "2026-11-14T08:00:00Z"))
 611 |          self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_waiting"]), (2, 1, 1))
 612 |          self.assertEqual(c["passes"], {"hook/mine-hook/2": 1, "moment/mine/2": 1})
 613 | -        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but not a conversation
 614 | +        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but marked with ZERO turns
 615 | +        newer = {"video_id": "int", "channel_name": "Interview", "published_at": "2026-11-13T23:00:00+00:00",
 616 | +                 "moment_id": "i1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "hook",
 617 | +                                                                                "prompt_version": "mine-hook/3"}}
 618 | +        self.assertEqual(SPOT.next_attempt(rows + [newer], {}, NOW)["conversation"]["video_id"], "int")   # 92 amended:
 619 | +        #   0.4 turns a minute is evidence now, not under a line: an interview at 0.4 counts (the layout decides)
 620 |          self.assertEqual(c["age_h"], round((NOW - datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc)).total_seconds()
 621 |                                             / 3600, 1))
 622 |          self.assertIsNone(SPOT.next_attempt([], {}, NOW)["conversation"])
 623 | @@ -561,7 +639,7 @@ class TestBuild(unittest.TestCase):
 624 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 625 |  
 626 |      def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None,
 627 | -                  onset=None):
 628 | +                  onset=None, evidence=None):
 629 |          ctx = E.Context(NOW, REG)
 630 |          calls = {}
 631 |  
 632 | @@ -591,8 +669,10 @@ class TestBuild(unittest.TestCase):
 633 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 634 |                   (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 635 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 636 | -                 (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
 637 | -                 (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
 638 | +                 (SPOT, "layout_for", lambda r, m, v, c, **k: (calls.setdefault("layout", []).append(
 639 | +                     (m["moment_id"], k.get("evidence"))), {"measured": True, "layout": layout, "why": "w"})[1]),
 640 | +                 (SPOT, "caption_evidence", lambda vid, s, e, c=None: evidence or {"measured": True,   # 92 amended
 641 | +                                                                                   "marked": False}),
 642 |                   (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
 643 |                   (SPOT.P, "_writers", lambda r: (set(), set()))]
 644 |          patches = [mock.patch.object(o, n, f) for o, n, f in stubs]
 645 | @@ -617,6 +697,24 @@ class TestBuild(unittest.TestCase):
 646 |          self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
 647 |          self.assertIsNotNone(out["package"])
 648 |  
 649 | +    def test_ruling_92_amended_zero_changes_near_the_clip_stops_before_any_vision_call(self):
 650 | +        """09:03 Nov 14: the markers refuse alone only when the episode is marked and shows ZERO speaker changes in the
 651 | +        10 minutes around the clip; then the layout judge (a paid vision call) is never asked. Any other evidence goes
 652 | +        to the judge WITH the evidence, and the layout decides."""
 653 | +        ms = [moment(mid="a", channel="A")]
 654 | +        quiet = {"measured": True, "marked": True, "turns": 5, "minutes": 30.0, "turns_per_min": 0.17,
 655 | +                 "changes_near": 0, "one_turn": True}
 656 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[4.0], evidence=quiet)
 657 | +        self.assertIsNone(out["package"])
 658 | +        self.assertNotIn("layout", calls)                                  # no vision call was paid
 659 | +        self.assertIn("no speaker change in the 10 minutes around the clip", out["moments"]["a"]["out"])
 660 | +        talk = dict(quiet, turns_per_min=0.61, changes_near=3)             # Stephan Livera's 0.61: under the old line
 661 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[4.0], evidence=talk)
 662 | +        self.assertEqual(calls["layout"], [("a", talk)])                   # the judge sees the evidence
 663 | +        self.assertIsNotNone(out["package"])                               # the layout (conversation) decides
 664 | +        self.assertIn("layout 'conversation'", out["moments"]["a"]["source"])
 665 | +        self.assertIn("0.61 speaker turns a minute", out["moments"]["a"]["source"])
 666 | +
 667 |      def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
 668 |          ms = [moment(mid="a", channel="A")]
 669 |          later = {"a": sv(TEXT, 4.0)}
 670 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

BACKGROUND (static):
- pipeline/moments_gate_adapter.py is the ONE adapter of another team's exam (pp-tests: corpora of hostile must-fail
  and must-pass cases for three gates: context integrity, VO fidelity, exclusion). The harness strips the expected
  answer and calls the adapter's functions. Live model replies are recorded by tests/package/run_exam_record.py; the
  harness then replays them OFFLINE (PP_GATES_REPLAY=1), and the router serves the first back-end in its chain that
  has a recording, so the replay must walk the same chains as the recording.
- VO fidelity (vo_fidelity.check) judges each VO line, the title and caption: a deterministic layer (NUMBER, NEEDS_SOURCE,
  PRICE_NOW ...) then a model verdict. PRICE_NOW: with current_levels a list, a line stating a price as current that
  matches no level (5 % tolerance) fails; with current_levels None, PRICE_NOW is not measured. package.current_levels
  (the packager) reads levels from sources: each sentence naming Bitcoin, from sources <= 24 h old, through
  vo_fidelity.current_level_values.
- The SPOTLIGHT (ruling 90) is a one-moment video; ruling 92 is its source test ("conversation, not reaction"): a
  vision judge classifies the clip's contact sheet (layout_for: conversation / first_hand / recap / reaction / other);
  the episode's caption speaker-change markers ('>>') were also used.

THE ORCHESTRATOR'S RULINGS (09:03 ET Nov 14), verbatim:
- "R-29: FIX IT NOW, while the pool is empty (about 20 lines, tests, two cycles). An exam whose must-fail cases pass
  by construction is worse than no exam."
  R-29 (pp-tests): the adapter's vo_fidelity() never passed v1.1's `title` (judged like a line) and derived no current
  price level from v1.1's `universe` (tonight's news). Minimal fix: the title as a line; current_levels from
  universe.news the way package.current_levels does from sources (published <= 24 h before the universe's date).
- "THE EXAM: APPROVED to run after R-29 and the integrator's merge of pp-tests, heimdall_first, bound $5.00
  vendor-reported, on its OWN ledger (not the $20 batch cap); stop and tell me at $4."
- "RULING 92 AMENDED (...): the 1.0 line was drawn from one solo recap at 0.48 and refuses real interviews. FROM NOW:
  the LAYOUT verdict decides the source test alone (CONVERSATION or FIRST_HAND pass; RECAP, REACTION, OTHER fail;
  unmeasured never passes). The caption markers are EVIDENCE shown to the layout judge (turns a minute, and whether
  the clip's own span sits inside one unbroken turn), not a refusal line; they refuse by themselves only when the
  episode is marked and has ZERO speaker changes in the 10 minutes around the clip. Audit as one small change with
  R-29 or after it."

THE CHANGE (the diff follows):
1. moments_gate_adapter.vo_fidelity: a v1.1 case's title is appended as a line {"slot": "title", "text": ..., "cites":
   []}; when the case has a universe (and no explicit current_levels), current_levels = universe_levels(universe):
   each sentence of a news item's headline / summary that names Bitcoin, from items published <= 24 h before the
   universe's clock (built_at, zoned; an item with an unreadable time skipped, as package.current_levels skips such a
   source), through current_level_values. [] is a measurement. A title that is not a non-empty string, a universe with
   no zoned clock or no news list: ValueError -> GateNotMeasured (the harness's ERROR). v1 cases are unchanged.
   Measured on the real corpus: both stale-title cases now fail on their title (NEEDS_SOURCE, NUMBER, PRICE_NOW); their
   $73,500 news is 38-45 h old, so their levels are [] (the 5 % tolerance would have accepted the stale $76,000 line
   against $73,500).
2. make_router(): ONE router configuration for the recorder and the replay: PP_GATES_ROUTING (default
   heimdall_first), PP_GATES_LIMIT_USD (default 5.00), PP_GATES_LIMIT_BASIS (default "reported"), PP_GATES_SPEND (the
   exam's own ledger). run_exam_record.py now calls it instead of building its own Router (no routing, $64.28,
   estimate basis).
3. spotlight.py, ruling 92 amended: caption_evidence() (turns a minute; speaker changes in NEAR_CLIP_S = 300 s each
   side of the clip; one unbroken turn = no marker more than MARKER_TOL_S inside the clip); markers_refuse() (marked
   AND zero changes near); source_test(evidence, layout) (the layout decides; the 1.0 line, CONVERSATION_TPM, retired);
   layout_for(..., evidence) shows the evidence in the prompt and keys its cache on it; the build skips the vision
   call when the markers refuse; the ruling-95 report counts any upload whose captions do not refuse it.
4. Tests: tests/package/test_exam_adapter.py (new, 8) and test_spotlight.py (amended). 17 mutations, each killed.
   20 suites, 559 tests.

ATTACK:
(a) R-29: can a v1.1 must-fail case still pass by construction (the title or the universe not reaching the gate)?
    Does anything change for v1 cases? Is the 24 h window on built_at the right reading of "24 h before the
    universe's date", and is skipping an unreadable item right?
(b) The router: can the replay walk different chains than the recording? Can the exam spend past $5 vendor-reported,
    or touch the $20 batch ledger (SPEND_LY.json)? Can it reach a GPU (local:) or a frozen vendor leg?
(c) Ruling 92 amended: can a marked episode with a speaker change near the clip be refused by the captions? Can an
    unmarked or unreadable caption record refuse? Can an unmeasured layout pass? Is "the 10 minutes around the clip"
    read sensibly? Can a cached layout verdict be reused under different evidence?
(d) Anything else that could seal a wrong spotlight pin or score the exam wrongly.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".

