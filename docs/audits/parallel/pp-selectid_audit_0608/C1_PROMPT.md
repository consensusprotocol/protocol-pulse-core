# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0608
# Branch: pp-selectid
# Generated: 2026-11-14 06:09 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0608/C1_STEP.diff (756 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 80d079c..f7f2d5a 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -22,6 +22,9 @@ write_takeaway() role angle_write: the ONE takeaway (host commentary), ONE title
   6 |  GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gates):
   7 |                the clips-alone verdict first (no writing before it passes);
   8 |                cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
   9 | +              then RULING 91's VALUE verdict on the takeaway (takeaway_value, before any paid gate; a takeaway
  10 | +              that loses it never ships: the no-voice shape when the line-up's own clips meet the seconds, else ONE
  11 | +              rewrite of the takeaway alone; a second loss ends the line-up);
  12 |                then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
  13 |                integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
  14 |                start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
  15 | @@ -1732,7 +1735,9 @@ TAKEAWAY_LIMIT = ("{lo}-{hi} words, one or two sentences: host commentary attrib
  16 |  TAKEAWAY_WHY = dict(VO_FIX, **LINE_WHY, COMMENTARY="as host commentary it must state no fact, no speaker's view, no "
  17 |                      "advice or prediction and no accusation, and must not sound like a speaker",
  18 |                      COHERENCE="a blind viewer did not find its point supported by the clips",
  19 | -                    RUNTIME="with it the video does not land 60-70 s")
  20 | +                    RUNTIME="with it the video does not land 60-70 s",
  21 | +                    VALUE="it did not earn its place (ruling 91): a viewer must miss it if it were cut, so it must say "
  22 | +                          "something the clips do not already say, never restate, summarise or cheer them")
  23 |  
  24 |  
  25 |  def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None, avoid_model=None,
  26 | @@ -1778,6 +1783,63 @@ def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, av
  27 |      return r, ln
  28 |  
  29 |  
  30 | +TAKEAWAY_VALUE_PROMPT = """You judge ONE line a host would speak at the END of a short video. The clips below play
  31 | +first, back to back, alone and in full, in this order; then the host's line; then a sign-off credits the channels.
  32 | +{note}
  33 | +{clips}
  34 | +LINE: "{line}"
  35 | +Answer each question "yes" or "no". Anything you cannot answer with a clear yes is "no".
  36 | +- "adds": does the line say something the clips do not already say?
  37 | +- "no_restate": does the line avoid restating, summarising or cheering the clips?
  38 | +- "missed": would a viewer miss the line if it were cut?
  39 | +- "short": is the line {cap} words or fewer?
  40 | +Return ONLY this JSON object: {{"adds": "yes" | "no", "no_restate": "yes" | "no", "missed": "yes" | "no", "short":
  41 | +"yes" | "no", "why": "<one sentence>"}}"""
  42 | +
  43 | +
  44 | +def takeaway_value(router, segs, ctx, line, writers_v, writers_f, seed=7):
  45 | +    """RULING 91, its MEDLEY half ('22:53' Nov 13: "The same value verdict also applies to a MEDLEY's takeaway going
  46 | +    forward"): ONE blind value verdict on a written takeaway, in the spotlight's contract (spotlight.parse_value and
  47 | +    VALUE_KEYS: four questions, each a clear "yes" or it is "no") over the medley's clips in play order, off every
  48 | +    writer's vendor and family (role coherence_verdict, the call the spotlight's closing line gets). ok only when all
  49 | +    four answers are "yes" AND the line counts at most LY_TAKEAWAY_MAX_WORDS words in code (house_style.words: house
  50 | +    style's cap, ruling 6; R4's 30 stays the factory's bound). The seed is fixed, so one text over the same clips has
  51 | +    one verdict (a recorded reply is served again, never re-asked). An unavailable or out-of-contract answer is no
  52 | +    verdict: measured False, ok False ("anything short of a clear yes means no line"); an out-of-contract reply is
  53 | +    rejected, so it is never served again. -> the record the "takeaway_value" row reads; "text" is the judged line
  54 | +    (the render binds the row to the takeaway it plays)."""
  55 | +    import providers as Pr
  56 | +    import spotlight as SPOT                           # its contract; imported here (spotlight imports this module)
  57 | +    from select_by_id import UNTRUSTED
  58 | +    from story_semantics import quote_data
  59 | +    q = lambda t, n: quote_data(t, n).replace('"', "'")
  60 | +    clips = "\n".join(f'CLIP {i + 1} (on {q(_name(m, ctx), 80)}): "{q(m["text"], 900)}"' for i, m in enumerate(segs))
  61 | +    prompt = TAKEAWAY_VALUE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), clips=clips,
  62 | +                                          line=q(line, 300), cap=LY_TAKEAWAY_MAX_WORDS)
  63 | +    base = {"text": line, "words": HS.words(line), "cap": LY_TAKEAWAY_MAX_WORDS}
  64 | +    r = None
  65 | +    try:
  66 | +        r = router.call("coherence_verdict", prompt, 400, seed, avoid_vendor=writers_v, avoid_family=writers_f)
  67 | +        v = SPOT.parse_value(r.text)
  68 | +    except Exception as e:                             # noqa: BLE001  no verdict: no line (ruling 91, law L-m)
  69 | +        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
  70 | +            router.reject(r)
  71 | +        return dict(base, measured=False, ok=False, why=f"{type(e).__name__}: {str(e)[:200]}",
  72 | +                    backend=getattr(r, "backend", None), replayed=False)
  73 | +    return dict(base, **v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
  74 | +                ok=all(v[k] == "yes" for k in SPOT.VALUE_KEYS) and base["words"] <= LY_TAKEAWAY_MAX_WORDS)
  75 | +
  76 | +
  77 | +def no_voice_fits(segs, med):
  78 | +    """RULING 91 (medley half): whether a line-up's OWN clips meet the seconds with no VO line, so that a takeaway the
  79 | +    value verdict refused falls back to L-y's no-voice shape with no clip added: the clips-alone verdict measured with
  80 | +    no flagged join (a no-voice medley carries no bridge either: ruling 3), and the clips' seconds inside what
  81 | +    no_voice() accepts (the factory's estimate, the clips + FINAL_TAIL_S, inside 60-70 s)."""
  82 | +    content = sum(m["duration_s"] for m in segs)
  83 | +    return med.get("measured") is True and med.get("flagged") == [] and \
  84 | +        RUNTIME_S[0] - FINAL_TAIL_S <= content <= RUNTIME_S[1] - FINAL_TAIL_S
  85 | +
  86 | +
  87 |  def lone_slot(violations):
  88 |      """RULING 65: "caption" or "title" when EVERY violation is on that one line (the takeaway and the other line pass),
  89 |      else None."""
  90 | @@ -2132,12 +2194,13 @@ def _redo(violations):
  91 |              "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
  92 |  
  93 |  
  94 | -def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
  95 | +def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None, value=None):
  96 |      """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
  97 |      the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
  98 |      passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict.
  99 |      context_framing: the context-integrity failures the VO's framing causes (VO_DEPENDENT; per clip, so not attributed
 100 | -    to one line: recorded beside `passed`, never folded into it)."""
 101 | +    to one line: recorded beside `passed`, never folded into it). value: ruling 91's value verdict on the line
 102 | +    (takeaway_value), recorded beside `passed` too (a value loss never counts toward ruling 3's no-voice trigger)."""
 103 |      line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
 104 |      rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
 105 |             "words": len((line.get("text") or "").split()),
 106 | @@ -2145,7 +2208,9 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 107 |             "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
 108 |             "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None,
 109 |             "context_framing": None if cx is None else sorted({v["rule"] for v in cx.get("violations") or []
 110 | -                                                              if v.get("rule") in VO_DEPENDENT})}
 111 | +                                                              if v.get("rule") in VO_DEPENDENT}),
 112 | +           "value": None if value is None else {k: value.get(k) for k in ("ok", "measured", "adds", "no_restate",
 113 | +                                                                           "missed", "short", "why", "backend")}}
 114 |      if fid is not None:
 115 |          ver = fid.get("verdict") or {}
 116 |          if fid.get("measured") and isinstance(ver.get("violations"), list):
 117 | @@ -2259,6 +2324,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 118 |          (lock_precheck.apply, checked again at the pin stage).
 119 |      The no-voice line-up is asked too. lock_check None: no pre-check (the tests' rigs); the driver always passes it.
 120 |      scorer_extra (RULING 90): the spotlight pool's moments, sent to the clip scorer with this build's own candidates.
 121 | +    RULING 91, its MEDLEY half ('22:53' Nov 13: "a medley that loses its takeaway falls back to L-y's no-voice shape
 122 | +    only if its clips meet the seconds; otherwise the takeaway may be rewritten once"): every written takeaway that
 123 | +    passes its cheap gates is asked ONE value verdict (takeaway_value) before any paid gate. A clear yes on all four
 124 | +    (and <= 20 words in code): the write goes on, and the package seals the "takeaway_value" row with the line it
 125 | +    judged. A loss (no verdict included): the takeaway never ships. When the line-up's OWN clips meet the seconds with
 126 | +    no VO line (no_voice_fits), the no-voice shape follows at once (no_voice(value=...): no clip added). Otherwise ONE
 127 | +    rewrite of the takeaway alone, told the refusal, whatever the ruling-66 counts say. Its loss ends the line-up with no
 128 | +    package. A value loss never counts toward ruling 3's two failures, so ruling 3's no-voice (which may add a clip)
 129 | +    keeps its own trigger.
 130 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 131 |      t0 = time.time()
 132 |      usd0 = _spent(spend)
 133 | @@ -2550,15 +2624,18 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 134 |                  f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
 135 |                  f"per package delivered: ruling 41)")
 136 |  
 137 | -    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
 138 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None):
 139 |          """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 140 |          viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 141 |          dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
 142 |          must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
 143 | -        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why)."""
 144 | +        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why).
 145 | +        RULING 91 (medley half), value = the value verdict the takeaway lost: "a medley that loses its takeaway falls
 146 | +        back to L-y's no-voice shape only if its clips meet the seconds": the line-up's OWN clips (no_voice_fits), so no
 147 | +        clip is ever added on this path; the record names ruling 91 and carries the verdict."""
 148 |          nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
 149 |          pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 150 | -        rec["no_voice"] = note = {"tried": True}
 151 | +        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 152 |          if med.get("measured") is not True or med.get("flagged") != []:     # audit 2240 C1 (qwen, glm): its own guard
 153 |              note["why_not"] = "the clips-alone verdict is not a measured pass with every join followable"
 154 |              return None
 155 | @@ -2567,6 +2644,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 156 |          if content > nv_hi:
 157 |              note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
 158 |              return None
 159 | +        if content < nv_lo and value is not None:            # ruling 91: only if its OWN clips meet the seconds
 160 | +            note["why_not"] = (f"ruling 91: {content:.1f} s of clips, under {nv_lo:.1f} s with no VO line, and no clip "
 161 | +                               f"is added for a takeaway the value verdict refused")
 162 | +            return None
 163 |          if content < nv_lo:                                  # "the packager may add a clip"
 164 |              chans = {m["channel_id"] for m in segs}
 165 |              for mid in angle["moments"]:
 166 | @@ -2595,12 +2676,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 167 |              if not ok2 or nv_med["flagged"]:
 168 |                  note["why_not"] = "the line-up with the added clip fails on the clips alone (or has a join to bridge)"
 169 |                  return None
 170 | +        why_nv = ("the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips back to back with "
 171 | +                  "the sign-off only") if value is None else \
 172 | +            ("ruling 91: the takeaway did not earn its place (its value verdict: " +
 173 | +             (", ".join(f"{k} {value.get(k)}" for k in ("adds", "no_restate", "missed", "short"))
 174 | +              if value.get("measured") else "no verdict") +
 175 | +             f"; {str(value.get('why') or '')[:200]}); the line-up's own clips meet the seconds, so L-y's no-voice "
 176 | +             f"shape ships them back to back with the sign-off only")
 177 |          fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 178 |                    "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 179 |                    "supply_exception": exception,
 180 | -                  "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
 181 | -                                      "back to back with the sign-off only", "added_clip": added,
 182 | -                               "lineup_before": [m["moment_id"] for m in segs]}}
 183 | +                  "no_voice": {"why": why_nv, "added_clip": added, "lineup_before": [m["moment_id"] for m in segs],
 184 | +                               **({"value": {k: value.get(k) for k in ("text", "ok", "measured", "adds", "no_restate",
 185 | +                                                                       "missed", "short", "why", "words", "backend")}}
 186 | +                                  if value is not None else {})}}
 187 |          see(order)                                        # RULING 70: the added clip is seen too
 188 |          vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
 189 |                  if VP.layout_block(m.get("visual"))}                                 # included, law L-m)
 190 | @@ -2638,7 +2727,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 191 |              note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 192 |              note["violations"] = fid["violations"] + cx["violations"]
 193 |              return None
 194 | -        coh = dict(nv_med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 195 | +        coh = dict(nv_med, vo_point=None,
 196 | +                   note=f"no VO line: the clips-alone verdict is the coherence verdict (ruling {note['ruling']})")
 197 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 198 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
 199 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 200 | @@ -2664,7 +2754,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 201 |                  note["why_not"] = f"ruling 68 / 72: {e}"[:400]
 202 |                  return None
 203 |          note["result"] = "PACKAGE"
 204 | -        log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
 205 | +        log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package, ruling {note['ruling']} ({len(order)} clips, "
 206 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 207 |          return pk
 208 |  
 209 | @@ -2825,10 +2915,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 210 |                          relined, w_used = True, writes
 211 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 212 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 213 | +                v_lost, v_redo, v_novoice, val = [], False, None, None   # RULING 91 (medley half): the value
 214 | +                #   verdicts the takeaway lost, its ONE rewrite still due, the loss that sends the line-up to the no-voice
 215 | +                #   shape, and the verdict of the takeaway now written
 216 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 217 | -                    lone = w_used >= writes                # takeaway alone failed, the takeaway ALONE, up to twice
 218 | -                    if lone and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None and
 219 | -                                     not last_rw65):
 220 | +                    lone = w_used >= writes or v_redo      # takeaway alone failed, the takeaway ALONE, up to twice
 221 | +                    if lone and not v_redo and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None
 222 | +                                                    and not last_rw65):
 223 |                          break
 224 |                      if over_budget(ai):
 225 |                          break
 226 | @@ -2836,8 +2929,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 227 |                      if w_over:
 228 |                          rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 229 |                          break
 230 | +                    redo91 = False
 231 |                      if lone:                               # the other lines kept as gated; told each refusal and why
 232 |                          alone_n += 1
 233 | +                        redo91, v_redo = v_redo, False     # ruling 91's one rewrite is spent here, whatever comes of it
 234 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 235 |                          if b is None:
 236 |                              rec["attempts"].append({"writer_error": "no takeaway length lands 60-70 s with the kept "
 237 | @@ -2924,14 +3019,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 238 |                             "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 239 |                             "takeaway_budget": fields.get("takeaway_budget"),
 240 |                             "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]],
 241 | -                           **({"takeaway_alone": {"attempt": alone_n, "refused": [dict(x) for x in t_refused]}}
 242 | +                           **({"takeaway_alone": {"attempt": alone_n, "refused": [dict(x) for x in t_refused],
 243 | +                                                  **({"ruling_91": True} if redo91 else {})}}
 244 |                                if lone else {})}
 245 |                      rec["attempts"].append(att)
 246 |                      take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap)
 247 |                      out["takeaways"].append(take)
 248 |                      last_fields = fields
 249 |                      log(f"  angle {ai + 1} line-up {n_lineup} write {w_used + alone_n}" +
 250 | -                        (" (the takeaway alone, ruling 66 17:02)" if lone else "") +
 251 | +                        (" (the takeaway alone, ruling 91)" if redo91 else
 252 | +                         " (the takeaway alone, ruling 66 17:02)" if lone else "") +
 253 |                          f" ({wr.backend}, takeaway {take['words']} "
 254 |                          f"words, {pk['runtime_s_estimate']} s): " +
 255 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 256 | @@ -2963,12 +3060,41 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 257 |                                                                       else " (no takeaway length lands it)"))
 258 |                                         if v["rule"] == "RUNTIME" else v for v in cheap])
 259 |                          continue
 260 | +                    # RULING 91 (medley half): the value verdict on the takeaway, before any paid gate is asked of it
 261 | +                    val = takeaway_value(router, segs, ctx, fields["takeaway"]["text"], writers_v, writers_f)
 262 | +                    att["value"] = val
 263 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap,
 264 | +                                                                   value=val)
 265 | +                    answers = ", ".join(f"{k} {val.get(k)}" for k in ("adds", "no_restate", "missed", "short"))
 266 | +                    log(f"    value (ruling 91) {'PASS' if val['ok'] else 'LOST'}: " +
 267 | +                        (f"{answers}, {val.get('words')} words" if val.get("measured") else
 268 | +                         f"no verdict ({str(val.get('why'))[:120]})") + f" ({time.time() - t0:.0f} s)")
 269 | +                    if not val["ok"]:                      # "anything short of a clear yes means no line"
 270 | +                        v_lost.append({k: val.get(k) for k in ("text", "measured", "adds", "no_restate", "missed",
 271 | +                                                               "short", "why", "words", "backend")})
 272 | +                        rec["value_lost"] = list(v_lost)
 273 | +                        ref = {"text": fields["takeaway"]["text"], "rule": "VALUE",
 274 | +                               "detail": (f"{answers}: {val.get('why')}" if val.get("measured") else
 275 | +                                          f"no clear yes ({val.get('why')})")[:300]}
 276 | +                        t_refused += [ref] if ref not in t_refused else []      # what its one rewrite is told
 277 | +                        if no_voice_fits(segs, med):       # its OWN clips meet the seconds: L-y's no-voice shape
 278 | +                            v_novoice = val
 279 | +                            break
 280 | +                        if len(v_lost) > 1:                # its one rewrite did not earn its place either
 281 | +                            rec["why"] = ("ruling 91: the takeaway did not earn its place, nor did its one rewrite, "
 282 | +                                          "and the line-up's own clips do not meet the no-voice seconds "
 283 | +                                          f"({sum(m['duration_s'] for m in segs):.1f} s of clips)")
 284 | +                            break
 285 | +                        v_redo = True                      # ONE rewrite of the takeaway alone, told why
 286 | +                        last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 287 | +                        continue
 288 |                      if lone and last_fid is not None:      # ruling 66 amended: the kept lines keep their verdicts
 289 |                          fid, cx = takeaway_alone_gates(router, pk, last_fid, sources, a_by, levels, ctx.now,
 290 |                                                         writers_v, writers_f)
 291 |                      else:
 292 |                          fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 293 | -                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap, fid, cx)
 294 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap, fid, cx,
 295 | +                                                                   value=val)
 296 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 297 |                      att["violations"] = cheap + fid["violations"] + cx["violations"]
 298 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 299 | @@ -3019,7 +3145,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 300 |                                              style=HS.lint_lines(pk["lines"]),
 301 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 302 |                                              stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 303 | -                                            visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 304 | +                                            visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 305 | +                                            value=val)                       # ruling 91: the takeaway earned its place
 306 |                      if not ok_c:
 307 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 308 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 309 | @@ -3049,8 +3176,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 310 |                          break
 311 |                      pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 312 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 313 | -                                    "coherence": coh.get("backend")}
 314 | -                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 315 | +                                    "coherence": coh.get("backend"), "value": val.get("backend")}
 316 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med, "value": val}
 317 |                      pk["seconds"] = round(time.time() - t0, 1)
 318 |                      pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 319 |                      if lock_check is not None:            # rulings 68 / 72: the texts it seals come from the lock
 320 | @@ -3065,12 +3192,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 321 |                      break
 322 |                  rec["relined"] = relined                    # ruling 66: a clip was dropped (or a line-up rule)
 323 |                  if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 324 | -                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop") \
 325 | -                        and not out.get("lock_stop"):
 326 | -                    nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 327 | +                        (v_novoice is not None or take_failed >= NO_VOICE_AFTER) and last_fields is not None and \
 328 | +                        not out.get("budget_stop") and not out.get("lock_stop"):
 329 | +                    nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup,
 330 | +                                  value=v_novoice)      # ruling 91 (its own clips, none added) before ruling 3
 331 |                      if nv is not None:
 332 |                          out["packages"].append(nv)
 333 | -                        rec["result"] = "PACKAGE (no voice, ruling 3)"
 334 | +                        rec["result"] = f"PACKAGE (no voice, ruling {3 if v_novoice is None else 91})"
 335 | +                    elif v_novoice is not None:
 336 | +                        rec["why"] = ("ruling 91: the takeaway did not earn its place, and L-y's no-voice shape did not "
 337 | +                                      "pass: " + str(rec["no_voice"].get("why_not")))[:500]
 338 |                  if not out["packages"] and not rec.get("why") and not rec.get("result"):
 339 |                      last = (rec.get("attempts") or [{}])[-1]
 340 |                      rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
 341 | @@ -3113,9 +3244,12 @@ def _spent(spend):
 342 |  
 343 |  
 344 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 345 | -              hook=None, stand=None, visual=None):
 346 | +              hook=None, stand=None, visual=None, value=None):
 347 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 348 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 349 | +    value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 350 | +    the line it judged (package_pin.takeaway_problems and the render bind it to the takeaway that ships); None leaves
 351 | +    it out, which refuses the pin of any medley that carries a takeaway (package_pin.TAKEAWAY_GATES).
 352 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 353 |      (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
 354 |      the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin.
 355 | @@ -3196,4 +3330,12 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 356 |                             by_rule="visual_pin (ruling 70): one contact sheet per clip; a finding is a FLAG, sealed, "
 357 |                                     "never a reject by itself")}
 358 |             if visual is not None else {}),
 359 | +        **({"takeaway_value": dict(row(value.get("ok") is True, value.get("backend"), value.get("replayed"),
 360 | +                                       measured=value.get("measured") is True),
 361 | +                                   text=value.get("text"), answers={k: value.get(k) for k in ("adds", "no_restate",
 362 | +                                                                                              "missed", "short")},
 363 | +                                   why=value.get("why"), words=value.get("words"), cap=value.get("cap"),
 364 | +                                   rule=f"ruling 91 (medley half): all four a clear yes and at most {LY_TAKEAWAY_MAX_WORDS} "
 365 | +                                        f"words, off every writer's vendor and family")}
 366 | +           if value is not None else {}),
 367 |      }
 368 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 369 | index 445a53b..fc96df7 100644
 370 | --- a/pipeline/package_pin.py
 371 | +++ b/pipeline/package_pin.py
 372 | @@ -47,6 +47,11 @@ SPOTLIGHT_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicat
 373 |                     "step_a_two_families", "visual", "window_12h", "never_delivered", "one_per_channel_day",
 374 |                     "precheck")                                           # rulings 68 / 72 / 73 / 84: pass or adopt
 375 |  CLOSING_GATES = ("closing_value", "closing_fidelity", "closing_context")   # ruling 91: a non-null closing only with all
 376 | +# RULING 91, its MEDLEY half ('22:53' Nov 13: "The same value verdict also applies to a MEDLEY's takeaway going
 377 | +# forward"; the row agreed with the integrator 05:5x ET Nov 14): a medley carrying a takeaway (the VO line after the
 378 | +# LAST clip) ships it only with this row exactly PASS, not replayed, its "text" the takeaway it judged (the render binds
 379 | +# the row to the line it plays). A medley with no takeaway (L-y's no-voice shape) needs no row.
 380 | +TAKEAWAY_GATES = ("takeaway_value",)
 381 |  SPOT_RUNTIME_S = (28.0, 50.0)            # ruling 90: the moment, the closing line, sign-off, credits card and outro
 382 |  SPOT_CLOSING_MAX_WORDS = 12              # ruling 90 / 91: at most ONE closing line of 12 words or fewer
 383 |  CREDITS_LINE = "Credits \U0001F9E1"      # ruling 90: PBX's first-comment format, 'Credits' and the orange heart
 384 | @@ -58,14 +63,47 @@ def _closing(pk):
 385 |      return (vo or {}).get("closing")
 386 |  
 387 |  
 388 | +def takeaway_line(pk):
 389 | +    """A medley's takeaway, the VO line after its LAST clip, else None (only a medley has one: bridge_slots). pk: a
 390 | +    package (pk["vo"]: bridges with bridges_after_clip, the clips counted from pk["segments"]) or a pin's
 391 | +    moments_package (edl_vo's last bridge, when vo_jobs names a "takeaway": to_pin writes it for exactly that line)."""
 392 | +    if (pk or {}).get("shape") != "medley":
 393 | +        return None
 394 | +    vo = pk.get("vo")
 395 | +    if isinstance(vo, dict):
 396 | +        last = len(pk.get("segments") or []) - 1
 397 | +        hit = [t for t, a in zip(vo.get("bridges") or [], vo.get("bridges_after_clip") or []) if a == last]
 398 | +        return hit[-1] if hit else None
 399 | +    ev = pk.get("edl_vo")
 400 | +    if isinstance(ev, dict) and (pk.get("vo_jobs") or {}).get("takeaway") == "takeaway" and ev.get("bridges"):
 401 | +        b = ev["bridges"][-1]
 402 | +        return b.get("text") if isinstance(b, dict) else None
 403 | +    return None
 404 | +
 405 | +
 406 |  def required_gates(pk):
 407 |      """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 408 | -    clips-alone verdict and the L-y shape. A spotlight (ruling 90): SPOTLIGHT_GATES, plus CLOSING_GATES whenever its
 409 | -    closing line is not null (ruling 91). pk: a package, or a pin's moments_package."""
 410 | +    clips-alone verdict and the L-y shape, plus TAKEAWAY_GATES whenever it carries a takeaway (ruling 91, the medley
 411 | +    half). A spotlight (ruling 90): SPOTLIGHT_GATES, plus CLOSING_GATES whenever its closing line is not null (ruling
 412 | +    91). pk: a package, or a pin's moments_package."""
 413 |      shape = (pk or {}).get("shape")
 414 |      if shape == "spotlight":
 415 |          return SPOTLIGHT_GATES + (CLOSING_GATES if _closing(pk) is not None else ())
 416 | -    return REQUIRED_GATES + (MEDLEY_GATES if shape == "medley" else ())
 417 | +    return REQUIRED_GATES + (MEDLEY_GATES if shape == "medley" else ()) + \
 418 | +        (TAKEAWAY_GATES if takeaway_line(pk) is not None else ())
 419 | +
 420 | +
 421 | +def takeaway_problems(pk):
 422 | +    """[why] for a medley whose takeaway_value row (ruling 91) did not judge exactly the takeaway that ships: the row's
 423 | +    "text" must equal the line after the last clip, character for character (the render compares after strip(); this
 424 | +    is stricter, so every pin passing here passes there). The row's status is gate_problems' (required_gates)."""
 425 | +    t = takeaway_line(pk)
 426 | +    if t is None:
 427 | +        return []
 428 | +    row = (pk.get("gates") or {}).get("takeaway_value")
 429 | +    if not isinstance(row, dict) or not isinstance(row.get("text"), str) or row["text"] != t:
 430 | +        return ["takeaway_value: the value verdict did not judge the takeaway that ships (ruling 91)"]
 431 | +    return []
 432 |  
 433 |  
 434 |  def first_comment_text(lines, tags):
 435 | @@ -390,7 +428,7 @@ def to_pin(pk, run_name):
 436 |                                                                       for x in line_problems(pk)] + \
 437 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 438 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
 439 | -        spotlight_problems(pk)
 440 | +        spotlight_problems(pk) + takeaway_problems(pk)
 441 |      if problems:
 442 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 443 |      segs = []
 444 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 445 | index af3a02d..b8903de 100644
 446 | --- a/tests/package/test_medley.py
 447 | +++ b/tests/package/test_medley.py
 448 | @@ -432,6 +432,8 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 449 |      def gates(self, pk, **over):
 450 |          g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
 451 |          g["stand_alone"] = dict(g["stand_alone"], screen=E.BTC_SCREEN.pattern)      # the screen it judged with
 452 | +        if "takeaway_value" in g:                       # ruling 91: the row names the takeaway it judged
 453 | +            g["takeaway_value"] = dict(g["takeaway_value"], text=package_pin.takeaway_line(pk))
 454 |          g.update(over)
 455 |          return g
 456 |  
 457 | @@ -468,8 +470,9 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 458 |  
 459 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 460 |          pk = self.build()
 461 | -        self.assertEqual(package_pin.required_gates(pk)[-6:], ("medley", "ly_shape", "house_style", "hook_onset",
 462 | -                                                               "stand_alone", "visual"))
 463 | +        self.assertEqual(package_pin.required_gates(pk)[-7:], ("medley", "ly_shape", "house_style", "hook_onset",
 464 | +                                                               "stand_alone", "visual",
 465 | +                                                               "takeaway_value"))   # ruling 91: it has a takeaway
 466 |          pk["gates"] = self.gates(pk)
 467 |          pin = package_pin.to_pin(spk(pk), "test")
 468 |          self.assertEqual(pin["label"], "bitcoin")     # the render's STAND_ALONE subject rests on it (audit 0310 C2)
 469 | @@ -478,7 +481,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 470 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 471 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 472 |          self.assertEqual(mp["shape"], "medley")
 473 | -        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"):
 474 | +        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone", "takeaway_value"):
 475 |              g = self.gates(pk)
 476 |              g.pop(missing)
 477 |              with self.assertRaises(package_pin.PinRefused):
 478 | @@ -526,8 +529,9 @@ class Rig:
 479 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 480 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 481 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 482 | -                 cached=False, candidate=None, visuals=None, registered=None, lock_check=None):
 483 | +                 cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None):
 484 |          import providers as P
 485 | +        self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 486 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 487 |          self.takeaways, self.spend = list(takeaways or []), spend
 488 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 489 | @@ -623,6 +627,19 @@ class Rig:
 490 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 491 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 492 |  
 493 | +    def value(self, router, segs, ctx_, line, wv, wf, seed=7):
 494 | +        """RULING 91 (medley half): package.takeaway_value as the build calls it. A clear yes on all four unless
 495 | +        self.values gives the next answers ({"adds": "no", ...}; {"measured": False} = no verdict)."""
 496 | +        self.value_calls.append({"line": line, "segs": [m["moment_id"] for m in segs], "wv": set(wv), "wf": set(wf)})
 497 | +        got = self.values.pop(0) if self.values else {}
 498 | +        base = {"text": line, "words": len(line.split()), "cap": PK.LY_TAKEAWAY_MAX_WORDS}
 499 | +        if got.get("measured") is False:
 500 | +            return dict(base, measured=False, ok=False, why="ProviderError: no back-end", backend=None, replayed=False)
 501 | +        ans = {k: got.get(k, "yes") for k in ("adds", "no_restate", "missed", "short")}
 502 | +        return dict(base, **ans, why=got.get("why", "a point the clips do not make"), measured=True,
 503 | +                    backend="xai:grok", replayed=False,
 504 | +                    ok=all(x == "yes" for x in ans.values()) and base["words"] <= PK.LY_TAKEAWAY_MAX_WORDS)
 505 | +
 506 |      def visual(self, router, m, work_dir, cache, seed=7, log=print):
 507 |          """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 508 |          self.visual_calls.append(m["moment_id"])
 509 | @@ -664,6 +681,7 @@ class Rig:
 510 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 511 |              "hook_onset_for": self.onset,
 512 |              "hook_ratings": self.rate_hooks,
 513 | +            "takeaway_value": self.value,                  # ruling 91 (medley half)
 514 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 515 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 516 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 517 | @@ -2992,6 +3010,7 @@ class TestRuling34Screen(unittest.TestCase):
 518 |          self.assertEqual(pk["btc_screen"], {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE})
 519 |          pk["gates"] = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1}
 520 |                         for k in package_pin.required_gates(pk)}
 521 | +        pk["gates"]["takeaway_value"]["text"] = package_pin.takeaway_line(pk)   # ruling 91: its takeaway, judged
 522 |          with self.assertRaises(package_pin.PinRefused):                 # no judged screen on the stand_alone row
 523 |              package_pin.to_pin(spk(pk), "test")
 524 |          pk["gates"]["stand_alone"]["screen"] = PK.stand_alone_check(pk["segments"])["screen"]   # what it judged
 525 | @@ -3170,5 +3189,230 @@ class TestReportedCost(unittest.TestCase):
 526 |          self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})
 527 |  
 528 |  
 529 | +class TestRuling91MedleyHalf(unittest.TestCase):
 530 | +    """RULING 91, its MEDLEY half ('22:53' Nov 13): "The same value verdict also applies to a MEDLEY's takeaway going
 531 | +    forward: a medley that loses its takeaway falls back to L-y's no-voice shape only if its clips meet the seconds;
 532 | +    otherwise the takeaway may be rewritten once." The row "takeaway_value" was agreed with the integrator (05:5x ET
 533 | +    Nov 14): status PASS, replayed false, "text" the takeaway it judged."""
 534 | +    SHORT = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]          # 39 s: under 45.7 s with no VO line
 535 | +    FITS = [pm("h", "A", 16.0), pm("x", "B", 16.0), pm("y", "C", 16.0)]           # 48 s: 62.3 s with no VO line
 536 | +    NEW = ("Nobody bends these rules, and that is exactly why they keep working for everyone who holds them "
 537 | +           "anywhere.")                                                            # 18 words: lands 39 s of clips
 538 | +    MED = [(True, [], None, Rig.LINE)]
 539 | +
 540 | +    def test_a_takeaway_that_earns_its_place_ships_with_its_row_bound_to_its_text(self):
 541 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None])
 542 | +        pk = rig.run()["package"]
 543 | +        row = pk["gates"]["takeaway_value"]
 544 | +        self.assertEqual((row["status"], row["replayed"], row["n"]), ("PASS", False, 1))
 545 | +        self.assertEqual(row["text"], pk["vo"]["bridges"][-1])                   # the line it judged is the one spoken
 546 | +        self.assertEqual(row["answers"], {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes"})
 547 | +        self.assertEqual((row["words"], row["cap"]), (16, 20))
 548 | +        self.assertEqual(rig.value_calls[0]["segs"], ["h", "x", "y"])            # the medley's clips, in play order
 549 | +        self.assertIn("heimdall", rig.value_calls[0]["wv"])                      # off the writer's vendor and family
 550 | +        self.assertIn("deepseek", rig.value_calls[0]["wf"])
 551 | +        self.assertEqual(pk["checks"]["value"]["text"], Rig.LINE)
 552 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 553 | +        self.assertEqual(mp["gates"]["takeaway_value"]["text"], mp["edl_vo"]["bridges"][-1]["text"])
 554 | +        self.assertEqual(package_pin.takeaway_line(mp), Rig.LINE)
 555 | +
 556 | +    def test_a_lost_takeaway_on_clips_that_meet_the_seconds_ships_no_voice_and_no_paid_gate_judged_it(self):
 557 | +        rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no", "why": "it restates clip_02"}])
 558 | +        out = rig.run()
 559 | +        pk = out["package"]
 560 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])   # its OWN clips, none added
 561 | +        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
 562 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
 563 | +        self.assertIn("ruling 91", pk["no_voice"]["why"])
 564 | +        self.assertIn("adds no", pk["no_voice"]["why"])
 565 | +        self.assertIsNone(pk["no_voice"]["added_clip"])
 566 | +        self.assertEqual((pk["no_voice"]["value"]["adds"], pk["no_voice"]["value"]["text"]), ("no", Rig.LINE))
 567 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 568 | +        self.assertNotIn("takeaway_value", pk["gates"])                          # no takeaway: no row
 569 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 570 | +        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # no rewrite: the clips meet the seconds
 571 | +        att = out["tried"][0]["attempts"][0]
 572 | +        self.assertEqual(att["value"]["adds"], "no")
 573 | +        self.assertNotIn("verdict_classes", att)                                 # asked before any paid gate
 574 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 575 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 576 | +        self.assertIn("ruling 91", pk["checks"]["coherence"]["note"])
 577 | +
 578 | +    def test_a_lost_takeaway_on_short_clips_gets_one_rewrite_alone_told_why(self):
 579 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 580 | +                  values=[{"adds": "no", "no_restate": "no", "why": "it restates the clips"}])
 581 | +        out = rig.run()
 582 | +        pk = out["package"]
 583 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway"), self.NEW)
 584 | +        self.assertEqual(pk["gates"]["takeaway_value"]["text"], self.NEW)      # the rewrite's verdict, never draft 1's
 585 | +        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])
 586 | +        self.assertEqual(len(rig.write_calls), 1)                                # one full write, then the takeaway ALONE
 587 | +        prompt = [p for r, p in rig.prompts if r == "angle_write"][-1]
 588 | +        self.assertIn("Your takeaway was refused", prompt)
 589 | +        self.assertIn(f'"{Rig.LINE}" (it did not earn its place (ruling 91)', prompt)
 590 | +        self.assertIn("adds no, no_restate no, missed yes, short yes: it restates the clips", prompt)
 591 | +        self.assertIn('TITLE: "Nobody bends the rules"', prompt)                # the other lines kept
 592 | +        tried = out["tried"][0]
 593 | +        self.assertTrue(tried["attempts"][1]["takeaway_alone"]["ruling_91"])
 594 | +        self.assertEqual([x["text"] for x in tried["value_lost"]], [Rig.LINE])
 595 | +        self.assertEqual(tried["result"], "PACKAGE")
 596 | +
 597 | +    def test_a_second_loss_ends_the_line_up_and_never_adds_a_clip(self):
 598 | +        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # ruling 3 would add z (52 s)
 599 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 600 | +                  values=[{"adds": "no"}, {"missed": "no"}])
 601 | +        out = rig.run()
 602 | +        self.assertIsNone(out["package"])
 603 | +        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # one rewrite, no more
 604 | +        self.assertIn("ruling 91", out["tried"][0]["why"])
 605 | +        self.assertIn("nor did its one rewrite", out["tried"][0]["why"])
 606 | +        self.assertNotIn("no_voice", out["tried"][0])                            # never the no-voice shape with z
 607 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
 608 | +        self.assertIn("ruling 91", out["why_none"])
 609 | +
 610 | +    def test_no_verdict_is_a_loss(self):
 611 | +        rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"measured": False}])
 612 | +        pk = rig.run()["package"]
 613 | +        self.assertIn("no verdict", pk["no_voice"]["why"])
 614 | +        self.assertFalse(pk["no_voice"]["value"]["measured"])
 615 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 616 | +                  values=[{"measured": False}, {"measured": False}])
 617 | +        out = rig.run()
 618 | +        self.assertIsNone(out["package"])                                       # nothing measured is never a pass
 619 | +        self.assertEqual(len(rig.value_calls), 2)
 620 | +
 621 | +    def test_ruling_3_is_unchanged_and_no_value_verdict_judges_a_takeaway_its_cheap_gates_refuse(self):
 622 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 623 | +        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None], takeaways=bad)
 624 | +        out = rig.run()
 625 | +        self.assertEqual(rig.value_calls, [])                                    # refused by house style first
 626 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
 627 | +        self.assertEqual(out["package"]["no_voice"]["added_clip"], "z")          # ruling 3 may still add a clip
 628 | +        self.assertNotIn("value", out["package"]["no_voice"])
 629 | +
 630 | +    def test_a_value_loss_never_counts_toward_ruling_3s_two_failures(self):
 631 | +        """One value loss, one ordinary failure (its rewrite breaks house style), then a second value loss: the
 632 | +        takeaway failed its OTHER gates once, so ruling 3's no-voice (which would add z) is not reached."""
 633 | +        bad = "Ultimately nobody bends the rules."                                # house style: the opener
 634 | +        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 635 | +                  takeaways=[Rig.LINE, self.NEW], lines=[{"takeaway": {"text": bad, "cites": []}}],
 636 | +                  values=[{"adds": "no"}, {"adds": "no"}])
 637 | +        out = rig.run()
 638 | +        self.assertIsNone(out["package"])
 639 | +        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # the bad line never reached it
 640 | +        self.assertNotIn("no_voice", out["tried"][0])
 641 | +        self.assertIn("ruling 91", out["tried"][0]["why"])
 642 | +
 643 | +    def test_the_line_up_records_every_takeaway_with_its_value(self):
 644 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 645 | +                  values=[{"short": "no"}])
 646 | +        out = rig.run()
 647 | +        vals = [t["value"] for t in out["takeaways"]]
 648 | +        self.assertEqual([(v["ok"], v["short"]) for v in vals], [(False, "no"), (True, "yes")])
 649 | +
 650 | +
 651 | +class TestTakeawayValueVerdict(unittest.TestCase):
 652 | +    """package.takeaway_value: the spotlight's value contract (spotlight.parse_value) over a medley's clips."""
 653 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 654 | +    LINE = "Nobody bends these rules, so nobody has to trust anyone to keep them."
 655 | +    YES = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "a point the clips do not make"}
 656 | +
 657 | +    def ask(self, answer, line=LINE):
 658 | +        r = Canned(coherence_verdict=[answer] if answer is not None else [])
 659 | +        prompts, inner = [], r.call
 660 | +        r.call = lambda role, prompt, *a, **k: (prompts.append((role, prompt, a, k)), inner(role, prompt, *a, **k))[1]
 661 | +        return r, PK.takeaway_value(r, self.SEGS, ctx(), line, {"heimdall"}, {"deepseek"}), prompts
 662 | +
 663 | +    def test_four_clear_yeses_inside_the_cap_pass_off_the_writers(self):
 664 | +        r, v, prompts = self.ask(self.YES)
 665 | +        self.assertTrue(v["ok"] and v["measured"])
 666 | +        self.assertEqual((v["text"], v["words"], v["cap"], v["backend"]), (self.LINE, 13, 20, "fake:coherence_verdict"))
 667 | +        self.assertEqual(r.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # never the writer's vendor
 668 | +        self.assertEqual(prompts[0][2][:2], (400, 7))                                     # one verdict per text: seed 7
 669 | +
 670 | +    def test_any_answer_short_of_a_clear_yes_fails(self):
 671 | +        for k in ("adds", "no_restate", "missed", "short"):
 672 | +            r, v, _ = self.ask(dict(self.YES, **{k: "no"}))
 673 | +            self.assertTrue(v["measured"], k)
 674 | +            self.assertFalse(v["ok"], k)
 675 | +
 676 | +    def test_the_cap_is_counted_in_code(self):
 677 | +        long_ = " ".join(["rules"] * 21)
 678 | +        r, v, _ = self.ask(self.YES, line=long_)                                 # the model said "short": yes
 679 | +        self.assertEqual((v["words"], v["ok"]), (21, False))
 680 | +        r, v, _ = self.ask(self.YES, line=" ".join(["rules"] * 20))
 681 | +        self.assertTrue(v["ok"])
 682 | +
 683 | +    def test_an_answer_out_of_contract_is_no_verdict_and_is_rejected(self):
 684 | +        for bad in ({"adds": "maybe", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "w"},
 685 | +                    {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes"},           # no why
 686 | +                    dict(self.YES, extra="yes"), "not json"):
 687 | +            r, v, _ = self.ask(bad)
 688 | +            self.assertEqual((v["measured"], v["ok"]), (False, False), bad)
 689 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"], bad)       # never served again
 690 | +
 691 | +    def test_no_back_end_is_no_verdict_and_nothing_is_rejected(self):
 692 | +        r, v, _ = self.ask(None)
 693 | +        self.assertEqual((v["measured"], v["ok"], r.rejected), (False, False, []))
 694 | +        self.assertIn("ProviderError", v["why"])
 695 | +
 696 | +    def test_the_prompt_shows_every_clip_in_play_order_then_the_line_and_the_cap(self):
 697 | +        segs = [dict(m, text=f'Bitcoin "{m["moment_id"]}" said.') for m in self.SEGS]
 698 | +        r = Canned(coherence_verdict=[self.YES])
 699 | +        seen, inner = [], r.call
 700 | +        r.call = lambda role, prompt, *a, **k: (seen.append(prompt), inner(role, prompt, *a, **k))[1]
 701 | +        PK.takeaway_value(r, segs, ctx(), 'He said "rules".', set(), set())
 702 | +        p = seen[0]
 703 | +        self.assertLess(p.index("CLIP 1 (on A)"), p.index("CLIP 2 (on B)"))
 704 | +        self.assertLess(p.index("CLIP 3 (on C)"), p.index("LINE:"))
 705 | +        self.assertIn("CLIP 2 (on B): \"Bitcoin 'x' said.\"", p)                # quotes inside a quote are neutralised
 706 | +        self.assertIn("LINE: \"He said 'rules'.\"", p)
 707 | +        self.assertIn('"short": is the line 20 words or fewer?', p)
 708 | +        self.assertIn("SECURITY", p)                                             # the quotes are untrusted data
 709 | +
 710 | +
 711 | +class TestTakeawayValueRow(unittest.TestCase):
 712 | +    """package_pin's half of the row (agreed with the integrator 05:5x ET Nov 14)."""
 713 | +
 714 | +    def pk(self, **kw):
 715 | +        return TestMedleyPackageAndPin().build(**kw)
 716 | +
 717 | +    def test_required_only_for_a_medley_that_carries_a_takeaway(self):
 718 | +        pk = self.pk()
 719 | +        self.assertIn("takeaway_value", package_pin.required_gates(pk))
 720 | +        nv = dict(pk, vo=dict(pk["vo"], bridges=[], bridges_after_clip=[]), no_voice={"why": "x"})
 721 | +        self.assertNotIn("takeaway_value", package_pin.required_gates(nv))       # the no-voice shape: no row
 722 | +        self.assertNotIn("takeaway_value", package_pin.required_gates({"shape": "medley"}))
 723 | +        self.assertNotIn("takeaway_value", package_pin.required_gates(dict(pk, shape=None)))   # only a medley's
 724 | +        self.assertNotIn("takeaway_value", package_pin.required_gates({"shape": "spotlight", "vo": {"closing": "x"}}))
 725 | +
 726 | +    def test_the_takeaway_is_the_line_after_the_last_clip_never_the_bridge(self):
 727 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
 728 | +        pk = self.pk(bridge=b, k=1, n=4)
 729 | +        self.assertEqual(package_pin.takeaway_line(pk), "No ruler, just rules nobody gets to bend.")
 730 | +        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 731 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 732 | +        self.assertEqual(package_pin.takeaway_line(mp), "No ruler, just rules nobody gets to bend.")
 733 | +        self.assertIn("takeaway_value", package_pin.required_gates(mp))
 734 | +        self.assertIsNone(package_pin.takeaway_line(dict(mp, vo_jobs={"bridge_1": "connection"})))
 735 | +
 736 | +    def test_the_row_must_judge_exactly_the_takeaway_that_ships(self):
 737 | +        pk = self.pk()
 738 | +        t = pk["vo"]["bridges"][-1]
 739 | +        for bad in ({"text": "Another line."}, {"text": t + " "}, {"text": None}, {"text": t, "status": "FAIL"},
 740 | +                    {"text": t, "status": "NOT RUN"}, {"text": t, "replayed": True}, {"text": t, "replayed": None}):
 741 | +            g = TestMedleyPackageAndPin().gates(pk)
 742 | +            g["takeaway_value"] = dict(g["takeaway_value"], **bad)
 743 | +            with self.assertRaises(package_pin.PinRefused, msg=bad) as cm:
 744 | +                package_pin.to_pin(spk(dict(pk, gates=g)), "test")
 745 | +            self.assertIn("takeaway_value", str(cm.exception))
 746 | +        g = TestMedleyPackageAndPin().gates(pk)
 747 | +        g.pop("takeaway_value")
 748 | +        with self.assertRaises(package_pin.PinRefused) as cm:
 749 | +            package_pin.to_pin(spk(dict(pk, gates=g)), "test")
 750 | +        self.assertIn("takeaway_value: missing", str(cm.exception))
 751 | +        package_pin.to_pin(spk(dict(pk, gates=TestMedleyPackageAndPin().gates(pk))), "test")   # the right row: pins
 752 | +
 753 | +
 754 |  if __name__ == "__main__":
 755 |      unittest.main()
 756 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

BACKGROUND (static):
- A MEDLEY pin is the hook clip + 2-4 clips played back to back, then at most ONE spoken VO line after the LAST clip
  (the "takeaway"), then a code-written sign-off. package.build() has a writer model write the takeaway, gates it
  (cheap deterministic gates, then paid verdicts: fidelity, context integrity, coherence) and seals a pin
  (package_pin.to_pin; seal() hashes the segments, VO, title, caption and the gate inventory). The render side (another
  team, "the integrator") imports pipeline/package_pin.py from this worktree LIVE and recomputes seal() with it.
- Ruling 3 (Nov 12): if the takeaway fails its gates twice on a line-up whose clips pass "alone", the package ships
  with NO VO line (the "no-voice shape": clips back to back, sign-off only); the packager may add one more clip to
  land 60-70 s.
- RULING 91 (Nov 13), the SPOTLIGHT half, already built: a closing line is kept only if a separate VALUE verdict, off
  the writer's model family, answers four questions with a clear yes: adds (says something the clip does not),
  no_restate (does not restate, summarise or cheer it), missed (a viewer would miss it if it were cut), short (within
  the cap). Anything short of a clear yes means no line. spotlight.value_verdict / parse_value / VALUE_KEYS carry it.
- RULING 91, the MEDLEY half (THIS change), verbatim: "The same value verdict also applies to a MEDLEY's takeaway going
  forward: a medley that loses its takeaway falls back to L-y's no-voice shape only if its clips meet the seconds;
  otherwise the takeaway may be rewritten once."
- The row agreed with the integrator: gates["takeaway_value"] = {status exactly "PASS", replayed false, n 1, text =
  the exact takeaway the verdict judged, answers, why, words, cap}; required for a medley carrying a takeaway; no
  takeaway = no row. The integrator checks status, replayed, and text == the takeaway after strip(). Cap: 20 words
  (house style), counted in code; R4's 30 stays the render's own bound.

THE CHANGE (dynamic; the diff follows):
1. package.takeaway_value(): ONE blind call (role coherence_verdict, as the spotlight's value verdict) showing the
   clips in play order, then the line; parsed by spotlight.parse_value; ok = four "yes" AND house_style.words(line)
   <= 20; off every writer's vendor and family; a fixed seed (one verdict per text over the same clips); unavailable
   or out of contract = measured False, ok False; an out-of-contract reply is rejected (never served again).
2. package.no_voice_fits(): the line-up's OWN clips (none added), the clips-alone verdict measured with no flagged
   join, and the clips + the 14.3 s tail inside 60-70 s.
3. build(): every written takeaway that passes its cheap gates gets the value verdict BEFORE any paid gate. On a loss:
   if no_voice_fits, the no-voice shape at once (no_voice(value=...), which never adds a clip); else ONE rewrite of the
   takeaway alone (write_line, told the refusal), forced past the ruling-66 write counts; a second loss ends the
   line-up with no package. A value loss never counts toward ruling 3's take_failed. The kept verdict is sealed as the
   "takeaway_value" row (inventory(value=...)).
4. package_pin: TAKEAWAY_GATES; takeaway_line() (from a package, or from a pin's moments_package); required_gates adds
   the row for a medley carrying a takeaway; takeaway_problems() refuses a row whose text is not exactly the shipped
   takeaway. seal() is unchanged.
5. Tests: the medley Rig stubs the verdict (default: a clear yes); 17 new tests; an 11-mutation check (each piece
   broken in turn) was killed by them every time. 19 suites, 535 tests pass.

ATTACK:
(a) Can a takeaway ship without a value verdict on exactly its own text? (a stale verdict from an earlier write;
    ruling 65's caption / title rewrite; the lock pre-check's LP.apply; the candidates registry's re-tries)
(b) Can the loop spin, skip the one rewrite, or allow more than one value-driven rewrite? Does the forced rewrite
    interact badly with ruling 66's takeaway-alone writes (alone_n, alone_by, last_fid, t_alone, last_rw65)?
(c) Is "no clip added" airtight on the ruling-91 path, and is ruling 3's own path (which may add a clip) unchanged?
(d) Backward compatibility: does every pin sealed before still recompute (seal() unchanged; the integrator's
    check_pin_only uses REQUIRED_GATES only)? Does any path re-pin an OLD package through to_pin and now refuse it?
(e) The verdict prompt: injection through clip text or the line (quote_data plus '"' -> "'"), and whether its four
    questions and its ok rule match the spotlight's contract.
(f) A known edge, judge it: a lost takeaway whose write ALSO has a lone caption / title failure falls back to the
    no-voice shape with that caption, whose own gates then fail closed (no ruling-65 caption rewrite on that path).
    Acceptable, or a defect?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".

