# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0734
# Branch: pp-selectid
# Generated: 2026-11-14 07:34 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0734/C1_STEP.diff (495 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f7f2d5a..58fa458 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -23,8 +23,8 @@ GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gat
   6 |                the clips-alone verdict first (no writing before it passes);
   7 |                cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
   8 |                then RULING 91's VALUE verdict on the takeaway (takeaway_value, before any paid gate; a takeaway
   9 | -              that loses it never ships: the no-voice shape when the line-up's own clips meet the seconds, else ONE
  10 | -              rewrite of the takeaway alone; a second loss ends the line-up);
  11 | +              that loses it never ships: the one no-voice shape (07:30 (A): its own clips or the added clip), else,
  12 | +              when no no-voice line-up exists, ONE rewrite of the takeaway alone; a second loss ends the line-up);
  13 |                then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
  14 |                integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
  15 |                start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
  16 | @@ -1830,16 +1830,6 @@ def takeaway_value(router, segs, ctx, line, writers_v, writers_f, seed=7):
  17 |                  ok=all(v[k] == "yes" for k in SPOT.VALUE_KEYS) and base["words"] <= LY_TAKEAWAY_MAX_WORDS)
  18 |  
  19 |  
  20 | -def no_voice_fits(segs, med):
  21 | -    """RULING 91 (medley half): whether a line-up's OWN clips meet the seconds with no VO line, so that a takeaway the
  22 | -    value verdict refused falls back to L-y's no-voice shape with no clip added: the clips-alone verdict measured with
  23 | -    no flagged join (a no-voice medley carries no bridge either: ruling 3), and the clips' seconds inside what
  24 | -    no_voice() accepts (the factory's estimate, the clips + FINAL_TAIL_S, inside 60-70 s)."""
  25 | -    content = sum(m["duration_s"] for m in segs)
  26 | -    return med.get("measured") is True and med.get("flagged") == [] and \
  27 | -        RUNTIME_S[0] - FINAL_TAIL_S <= content <= RUNTIME_S[1] - FINAL_TAIL_S
  28 | -
  29 | -
  30 |  def lone_slot(violations):
  31 |      """RULING 65: "caption" or "title" when EVERY violation is on that one line (the takeaway and the other line pass),
  32 |      else None."""
  33 | @@ -1922,6 +1912,29 @@ def merge_fid(fid, slot, one):
  34 |                  backend=f"{fid.get('backend')}; the {slot} alone: {one.get('backend')} (ruling 65)")
  35 |  
  36 |  
  37 | +def fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels, writers_v, writers_f, why):
  38 | +    """RULING 65 (b): the package with the FIXED caption (fixed_caption: code-written, no model, so no model verdict;
  39 | +    caption_fallback: true). Its deterministic fidelity layer and the house style (cheap_checks) and context integrity
  40 | +    on the package as it will be sealed still run; the other lines keep their verdicts in `fid` (merge_fid). One code
  41 | +    path for ruling 65's caption and, since the orchestrator's 07:30 ruling (C), for a caption that alone fails its gates
  42 | +    on a no-voice path. -> (pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), the fixed line)."""
  43 | +    line = fixed_caption(fields, segs, ctx)
  44 | +    pk3 = assemble_medley([m["moment_id"] for m in segs], by_id, dict(fields, caption=line), ctx,
  45 | +                          f"{pk.get('vo_kind')}; {why}")
  46 | +    pk3["medley"] = pk.get("medley")
  47 | +    pk3["caption_fallback"] = True
  48 | +    cheap3 = cheap_checks(pk3, a_by, levels, ctx.now)
  49 | +    man = {"channels": [sg["channel"] for sg in pk3["segments"]], "date": ctx.now.strftime("%Y-%m-%d")}
  50 | +    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk3["lines"] if x["slot"] == "caption"]
  51 | +    one = {"deterministic": VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels),
  52 | +           "verdict": {"ok": True, "violations": [], "claims": [], "classes": {"caption": ["the fixed line: no fact"]}},
  53 | +           "measured": True, "replayed": False, "backend": "code, no model: the fixed caption (ruling 65 b)"}
  54 | +    fid3 = merge_fid(fid, "caption", one)
  55 | +    cx3 = CI.check_contexts(router, pk3, CI.contexts_from_sources(pk3, sources, ctx.now), writers_v, 7,
  56 | +                            {sg["label"]: a_by[sg["moment_id"]] for sg in pk3["segments"]}, writers_f, True)
  57 | +    return pk3, fid3, cx3, cheap3, line
  58 | +
  59 | +
  60 |  def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ctx, a_by, sources, levels, writers_v,
  61 |                    writers_f, avoid_vendor=None, seed=7):
  62 |      """RULING 65 (12:52): only `slot` ("caption" or "title") failed (`refused`: its violations); the takeaway and the
  63 | @@ -1980,18 +1993,9 @@ def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ct
  64 |          rec["why"] = (f"the title failed alone {1 + len(rec.get('tries') or [])} times (its second write on the other "
  65 |                        f"writer model, 17:20): held (ruling 65 c): {rec['why']}")
  66 |          return pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, a_by, levels, ctx.now), rec
  67 | -    line = fixed_caption(fields, segs, ctx)               # (b): the fixed caption, code-written, no model
  68 | -    pk3 = build_pk(line, "the fixed caption (ruling 65 b)")
  69 | -    pk3["caption_fallback"] = True
  70 | -    cheap3 = cheap_checks(pk3, a_by, levels, ctx.now)
  71 | -    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk3["lines"] if x["slot"] == "caption"]
  72 | -    one = {"deterministic": VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels),
  73 | -           "verdict": {"ok": True, "violations": [], "claims": [], "classes": {"caption": ["the fixed line: no fact"]}},
  74 | -           "measured": True, "replayed": False, "backend": "code, no model: the fixed caption (ruling 65 b)"}
  75 | -    fid3 = merge_fid(fid, "caption", one)
  76 | -    cx3 = CI.check_contexts(router, pk3, CI.contexts_from_sources(pk3, sources, ctx.now), writers_v, 7, a_use(pk3),
  77 | -                            writers_f, True)
  78 | -    rec.update(fallback=line["text"], caption_fallback=True)
  79 | +    pk3, fid3, cx3, cheap3, line = fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels,
  80 | +                                                       writers_v, writers_f, "the fixed caption (ruling 65 b)")
  81 | +    rec.update(fallback=line["text"], caption_fallback=True)       # (b): the fixed caption, code-written, no model
  82 |      return pk3, fid3, cx3, cheap3, rec
  83 |  
  84 |  
  85 | @@ -2328,11 +2332,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  86 |      only if its clips meet the seconds; otherwise the takeaway may be rewritten once"): every written takeaway that
  87 |      passes its cheap gates is asked ONE value verdict (takeaway_value) before any paid gate. A clear yes on all four
  88 |      (and <= 20 words in code): the write goes on, and the package seals the "takeaway_value" row with the line it
  89 | -    judged. A loss (no verdict included): the takeaway never ships. When the line-up's OWN clips meet the seconds with
  90 | -    no VO line (no_voice_fits), the no-voice shape follows at once (no_voice(value=...): no clip added). Otherwise ONE
  91 | -    rewrite of the takeaway alone, told the refusal, whatever the ruling-66 counts say. Its loss ends the line-up with no
  92 | -    package. A value loss never counts toward ruling 3's two failures, so ruling 3's no-voice (which may add a clip)
  93 | -    keeps its own trigger.
  94 | +    judged. A loss (no verdict included) removes the takeaway, and THE ONE NO-VOICE SHAPE follows at once (the
  95 | +    orchestrator's 07:30 ruling (A): "one shape whatever removed the takeaway"): nv_order's line-up, the line-up's own
  96 | +    clips or the added clip when the seconds need it, every clip gate and join as usual (no_voice(value=...)). Only
  97 | +    when no no-voice line-up exists (no clip lands the seconds, or a join needs a bridge) is the takeaway alone
  98 | +    rewritten ONCE, told the refusal, whatever the ruling-66 counts say; its loss ends the line-up with no package.
  99 | +    A failed no-voice line-up ends the line-up too, as on ruling 3's path. A value loss never counts toward ruling 3's
 100 | +    two failures (it already leads to the same shape). On either no-voice path, a caption that alone fails its gates
 101 | +    becomes ruling 65 (b)'s fixed caption (07:30 (C)); a failing title holds.
 102 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 103 |      t0 = time.time()
 104 |      usd0 = _spent(spend)
 105 | @@ -2624,53 +2631,61 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 106 |                  f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
 107 |                  f"per package delivered: ruling 41)")
 108 |  
 109 | -    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None):
 110 | -        """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 111 | -        viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 112 | -        dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
 113 | -        must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
 114 | -        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why).
 115 | -        RULING 91 (medley half), value = the value verdict the takeaway lost: "a medley that loses its takeaway falls
 116 | -        back to L-y's no-voice shape only if its clips meet the seconds": the line-up's OWN clips (no_voice_fits), so no
 117 | -        clip is ever added on this path; the record names ruling 91 and carries the verdict."""
 118 | +    def nv_order(angle, segs, med, dropped):
 119 | +        """THE NO-VOICE LINE-UP, decided by code before any paid call (ruling 3; the orchestrator's 07:30 ruling (A):
 120 | +        "the no-voice shape is one shape whatever removed the takeaway"): the clips-alone verdict measured with every
 121 | +        join followable; the line-up's OWN clips when they meet the seconds with no VO line; else ONE more clip of the
 122 | +        angle, in the proposer's order, that lands them under the line-up rules (never the registry's line-up, ruling
 123 | +        66). -> {"order", "added", "why_not", "registered_skipped"}; order None when no no-voice line-up exists."""
 124 |          nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
 125 | -        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 126 | -        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 127 | +        plan = {"order": None, "added": None, "why_not": None, "registered_skipped": []}
 128 |          if med.get("measured") is not True or med.get("flagged") != []:     # audit 2240 C1 (qwen, glm): its own guard
 129 | -            note["why_not"] = "the clips-alone verdict is not a measured pass with every join followable"
 130 | -            return None
 131 | -        order, added, nv_med = list(segs), None, med
 132 | -        content = sum(m["duration_s"] for m in order)
 133 | +            return dict(plan, why_not="the clips-alone verdict is not a measured pass with every join followable")
 134 | +        content = sum(m["duration_s"] for m in segs)
 135 |          if content > nv_hi:
 136 | -            note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
 137 | -            return None
 138 | -        if content < nv_lo and value is not None:            # ruling 91: only if its OWN clips meet the seconds
 139 | -            note["why_not"] = (f"ruling 91: {content:.1f} s of clips, under {nv_lo:.1f} s with no VO line, and no clip "
 140 | -                               f"is added for a takeaway the value verdict refused")
 141 | +            return dict(plan, why_not=f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line")
 142 | +        if content >= nv_lo:
 143 | +            return dict(plan, order=list(segs))
 144 | +        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 145 | +        chans = {m["channel_id"] for m in segs}               # "the packager may add a clip"
 146 | +        for mid in angle["moments"]:
 147 | +            m = cleared.get(mid)
 148 | +            if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 149 | +                    not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 150 | +                continue
 151 | +            cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 152 | +            if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 153 | +                    sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 154 | +                    sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
 155 | +                    not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 156 | +                continue
 157 | +            if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
 158 | +                plan["registered_skipped"].append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
 159 | +                continue
 160 | +            return dict(plan, order=cand, added=mid)
 161 | +        return dict(plan, why_not=(f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 162 | +                                   + (f" (ruling 66: {plan['registered_skipped']} left to the registry)"
 163 | +                                      if plan["registered_skipped"] else "")))
 164 | +
 165 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None):
 166 | +        """THE NO-VOICE SHAPE: the package ships with NO VO line, clips back to back and the sign-off; it is not
 167 | +        dropped. Ruling 3 (22:40): the takeaway failed its gates twice; RULING 91 (value = the value verdict the
 168 | +        takeaway lost): its value verdict said no. The orchestrator's 07:30 ruling (A): "one shape whatever removed the
 169 | +        takeaway": the line-up is nv_order's (its own clips, or the added clip when the seconds need it); a line-up
 170 | +        with an added clip is judged on the clips alone again, and every clip gate runs on every clip. The title and
 171 | +        caption are the latest write's and go through every gate again. 07:30 (C): when ONLY the caption fails (its
 172 | +        cheap gates, or its verdict with context integrity passing: ruling 65's own trigger), ruling 65 (b)'s fixed
 173 | +        caption is used, as there (fixed_caption_gates, caption_fallback true); a failing title still holds (65 c).
 174 | +        The record names the ruling and, for 91, carries the verdict. -> a package, or None (rec["no_voice"] why)."""
 175 | +        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 176 | +        plan = nv_order(angle, segs, med, dropped)
 177 | +        if plan["registered_skipped"]:
 178 | +            note["registered_skipped"] = plan["registered_skipped"]
 179 | +        if plan["order"] is None:
 180 | +            note["why_not"] = plan["why_not"]
 181 |              return None
 182 | -        if content < nv_lo:                                  # "the packager may add a clip"
 183 | -            chans = {m["channel_id"] for m in segs}
 184 | -            for mid in angle["moments"]:
 185 | -                m = cleared.get(mid)
 186 | -                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 187 | -                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 188 | -                    continue
 189 | -                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 190 | -                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 191 | -                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 192 | -                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
 193 | -                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 194 | -                    continue
 195 | -                if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
 196 | -                    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
 197 | -                    continue
 198 | -                order, added = cand, mid
 199 | -                break
 200 | -            if added is None:
 201 | -                note["why_not"] = (f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 202 | -                                   + (f" (ruling 66: {note['registered_skipped']} left to the registry)"
 203 | -                                      if note.get("registered_skipped") else ""))
 204 | -                return None
 205 | +        order, added, nv_med = plan["order"], plan["added"], med
 206 | +        if added is not None:                                # its new line-up, judged on the clips alone again
 207 |              ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
 208 |              note["medley"] = nv_med
 209 |              if not ok2 or nv_med["flagged"]:
 210 | @@ -2681,8 +2696,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 211 |              ("ruling 91: the takeaway did not earn its place (its value verdict: " +
 212 |               (", ".join(f"{k} {value.get(k)}" for k in ("adds", "no_restate", "missed", "short"))
 213 |                if value.get("measured") else "no verdict") +
 214 | -             f"; {str(value.get('why') or '')[:200]}); the line-up's own clips meet the seconds, so L-y's no-voice "
 215 | -             f"shape ships them back to back with the sign-off only")
 216 | +             f"; {str(value.get('why') or '')[:200]}); L-y's no-voice shape (one shape, 07:30 (A)) ships the clips back "
 217 | +             f"to back with the sign-off only" + (f", one clip added ({added})" if added else ""))
 218 |          fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 219 |                    "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 220 |                    "supply_exception": exception,
 221 | @@ -2710,7 +2725,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 222 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 223 |          pk["medley"] = nv_med
 224 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 225 | -        if cheap:
 226 | +        if cheap and lone_slot(cheap) != "caption":          # 07:30 (C): only the caption failing alone goes on
 227 |              note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
 228 |              note["violations"] = cheap
 229 |              return None
 230 | @@ -2723,10 +2738,23 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 231 |                  note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
 232 |                  return None
 233 |              fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
 234 | -        if not fid["ok"] or not cx["ok"]:
 235 | -            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 236 | -            note["violations"] = fid["violations"] + cx["violations"]
 237 | -            return None
 238 | +        fixed = None
 239 | +        if cheap or not fid["ok"] or not cx["ok"]:
 240 | +            if not (cx["ok"] and fid.get("measured") and lone_slot(cheap + fid["violations"]) == "caption"):
 241 | +                note["why_not"] = "the title / caption fail VO fidelity or context integrity" + \
 242 | +                    (f" (cheap gates: {sorted({v['rule'] for v in cheap})})" if cheap else "")
 243 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 244 | +                return None
 245 | +            refused = [{k: v.get(k) for k in ("rule", "detail")} for v in cheap + fid["violations"]]
 246 | +            pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), fixed = fixed_caption_gates(   # 07:30 (C): ruling 65 (b)
 247 | +                router, pk, fields, fid, order, cleared, ctx, a_by, sources, levels, writers_v, writers_f,
 248 | +                "the fixed caption on a no-voice path (07:30 (C), ruling 65 b)")
 249 | +            note["caption_fallback"] = {"refused": refused, "written": fields["caption"]["text"],
 250 | +                                        "fixed": fixed["text"]}
 251 | +            if cheap or not fid["ok"] or not cx["ok"]:
 252 | +                note["why_not"] = "the fixed caption (07:30 (C), ruling 65 b) did not pass its gates"
 253 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 254 | +                return None
 255 |          coh = dict(nv_med, vo_point=None,
 256 |                     note=f"no VO line: the clips-alone verdict is the coherence verdict (ruling {note['ruling']})")
 257 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 258 | @@ -2741,7 +2769,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 259 |          if problems:
 260 |              note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 261 |              return None
 262 | -        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
 263 | +        pk["models"] = {"angle": angle_reply.backend,
 264 | +                        "writer": "the latest write's title and caption" if fixed is None else
 265 | +                                  "the latest write's title; the caption is code's fixed line (07:30 (C), ruling 65 b)",
 266 |                          "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 267 |                          "context": cx.get("backends"), "coherence": nv_med.get("backend")}
 268 |          pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 269 | @@ -3077,13 +3107,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 270 |                                 "detail": (f"{answers}: {val.get('why')}" if val.get("measured") else
 271 |                                            f"no clear yes ({val.get('why')})")[:300]}
 272 |                          t_refused += [ref] if ref not in t_refused else []      # what its one rewrite is told
 273 | -                        if no_voice_fits(segs, med):       # its OWN clips meet the seconds: L-y's no-voice shape
 274 | +                        nv_plan = nv_order(angle, segs, med, dropped)          # 07:30 (A): the ONE no-voice shape,
 275 | +                        if nv_plan["order"] is not None:   # its own clips or the added clip: no_voice() below
 276 |                              v_novoice = val
 277 |                              break
 278 |                          if len(v_lost) > 1:                # its one rewrite did not earn its place either
 279 |                              rec["why"] = ("ruling 91: the takeaway did not earn its place, nor did its one rewrite, "
 280 | -                                          "and the line-up's own clips do not meet the no-voice seconds "
 281 | -                                          f"({sum(m['duration_s'] for m in segs):.1f} s of clips)")
 282 | +                                          f"and no no-voice line-up exists ({nv_plan['why_not']})")[:500]
 283 |                              break
 284 |                          v_redo = True                      # ONE rewrite of the takeaway alone, told why
 285 |                          last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 286 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 287 | index ed2b1e3..7c1948f 100644
 288 | --- a/tests/package/test_medley.py
 289 | +++ b/tests/package/test_medley.py
 290 | @@ -530,10 +530,11 @@ class Rig:
 291 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 292 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 293 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 294 | -                 real_value=False):
 295 | +                 real_value=False, caption=None):
 296 |          import providers as P
 297 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 298 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 299 | +        self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
 300 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 301 |          self.takeaways, self.spend = list(takeaways or []), spend
 302 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 303 | @@ -625,7 +626,7 @@ class Rig:
 304 |          fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
 305 |                    "bridge_after": join[0] if join is not None and b is not None else None,
 306 |                    "title": {"text": "Nobody bends the rules", "cites": []},
 307 | -                  "caption": {"text": "nobody bends these rules", "cites": []},
 308 | +                  "caption": {"text": self.caption, "cites": []},
 309 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 310 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 311 |  
 312 | @@ -3261,17 +3262,49 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 313 |          self.assertEqual([x["text"] for x in tried["value_lost"]], [Rig.LINE])
 314 |          self.assertEqual(tried["result"], "PACKAGE")
 315 |  
 316 | -    def test_a_second_loss_ends_the_line_up_and_never_adds_a_clip(self):
 317 | -        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # ruling 3 would add z (52 s)
 318 | -        rig = Rig(ms, ["h", "x", "y", "z"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 319 | +    def test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip(self):
 320 | +        """The orchestrator's 07:30 ruling (A): "the no-voice shape is one shape whatever removed the takeaway (two
 321 | +        failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
 322 | +        need it, each added clip passing every clip gate and the joins as usual." No rewrite is spent."""
 323 | +        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # 39 s + z = 52 s with no VO line
 324 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED * 2, [None], values=[{"adds": "no", "why": "it restates"}])
 325 | +        out = rig.run()
 326 | +        pk = out["package"]
 327 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])
 328 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 329 | +        self.assertIn("one clip added (z)", pk["no_voice"]["why"])
 330 | +        self.assertEqual(pk["no_voice"]["value"]["adds"], "no")
 331 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])          # the new line-up judged on the clips alone
 332 | +        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # no rewrite of the takeaway
 333 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 334 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 335 | +        self.assertNotIn("takeaway_value", pk["gates"])
 336 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 337 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 338 | +
 339 | +    def test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite(self):
 340 | +        """As on ruling 3's path: the added clip's line-up fails the clips-alone verdict, so there is no package, and
 341 | +        the takeaway is not rewritten (a no-voice line-up existed)."""
 342 | +        ms = self.SHORT + [pm("z", "D", 13.0)]
 343 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED + [(False, [], {"clip_03": 2}, Rig.LINE)], [None],
 344 | +                  values=[{"adds": "no"}])
 345 | +        out = rig.run()
 346 | +        self.assertIsNone(out["package"])
 347 | +        self.assertEqual(len(rig.value_calls), 1)
 348 | +        self.assertIn("ruling 91", out["tried"][0]["why"])
 349 | +        self.assertIn("fails on the clips alone", out["tried"][0]["why"])
 350 | +
 351 | +    def test_a_second_loss_ends_the_line_up_when_no_no_voice_line_up_exists(self):
 352 | +        """No clip of the angle can be added (h, x, y are all it has), so ruling 91's one rewrite is used; its loss
 353 | +        ends the line-up."""
 354 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 355 |                    values=[{"adds": "no"}, {"missed": "no"}])
 356 |          out = rig.run()
 357 |          self.assertIsNone(out["package"])
 358 |          self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # one rewrite, no more
 359 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 360 |          self.assertIn("nor did its one rewrite", out["tried"][0]["why"])
 361 | -        self.assertNotIn("no_voice", out["tried"][0])                            # never the no-voice shape with z
 362 | -        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
 363 | +        self.assertIn("no no-voice line-up exists", out["tried"][0]["why"])
 364 | +        self.assertNotIn("no_voice", out["tried"][0])
 365 |          self.assertIn("ruling 91", out["why_none"])
 366 |  
 367 |      def test_no_verdict_is_a_loss(self):
 368 | @@ -3294,18 +3327,115 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 369 |          self.assertEqual(out["package"]["no_voice"]["added_clip"], "z")          # ruling 3 may still add a clip
 370 |          self.assertNotIn("value", out["package"]["no_voice"])
 371 |  
 372 | -    def test_a_value_loss_never_counts_toward_ruling_3s_two_failures(self):
 373 | -        """One value loss, one ordinary failure (its rewrite breaks house style), then a second value loss: the
 374 | -        takeaway failed its OTHER gates once, so ruling 3's no-voice (which would add z) is not reached."""
 375 | -        bad = "Ultimately nobody bends the rules."                                # house style: the opener
 376 | -        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 377 | -                  takeaways=[Rig.LINE, self.NEW], lines=[{"takeaway": {"text": bad, "cites": []}}],
 378 | -                  values=[{"adds": "no"}, {"adds": "no"}])
 379 | -        out = rig.run()
 380 | +    @staticmethod
 381 | +    def contexts_pass():
 382 | +        """context_integrity stubbed to a measured pass (the fixed caption's own context run calls it directly);
 383 | +        returns the restore function."""
 384 | +        import context_integrity as CI
 385 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 386 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 387 | +                                             "backends": {"B": "xai", "C": "xai"}}
 388 | +        CI.contexts_from_sources = lambda *a, **k: {}
 389 | +
 390 | +        def restore():
 391 | +            CI.check_contexts, CI.contexts_from_sources = saved
 392 | +        return restore
 393 | +
 394 | +    UPPER = "Nobody Bends These Rules."                           # house style: a caption is all lowercase
 395 | +    FIXED = "nobody bends the rules\na / b / c"                   # ruling 65 (b): the title lowercase, then the shows
 396 | +
 397 | +    def test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption(self):
 398 | +        """The orchestrator's 07:30 ruling (C): "on a no-voice path, when only the caption fails its gates, ruling 65
 399 | +        (b)'s fixed caption is used and the line-up goes on (caption_fallback: true, as there)."""
 400 | +        restore = self.contexts_pass()
 401 | +        try:
 402 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 403 | +            out = rig.run()
 404 | +        finally:
 405 | +            restore()
 406 | +        pk = out["package"]
 407 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 408 | +        self.assertTrue(pk["caption_fallback"])
 409 | +        self.assertEqual(pk["caption"], self.FIXED)
 410 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "caption"), self.FIXED)
 411 | +        self.assertEqual(pk["title"], "Nobody bends the rules")                  # the title as written and gated
 412 | +        cf = out["tried"][0]["no_voice"]["caption_fallback"]
 413 | +        self.assertEqual((cf["written"], cf["fixed"]), (self.UPPER, self.FIXED))
 414 | +        self.assertTrue(cf["refused"])
 415 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 416 | +        self.assertIn("ruling 65 b", pk["checks"]["fidelity"]["backend"])        # no model judged the fixed line
 417 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 418 | +        self.assertTrue(mp["caption_fallback"])
 419 | +        self.assertEqual(mp["caption"], self.FIXED)
 420 | +
 421 | +    def test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption(self):
 422 | +        restore = self.contexts_pass()
 423 | +        try:
 424 | +            bad = TestRuling66Amended().failing("caption", "it says the clips agree", "VERDICT_NO")
 425 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[bad])
 426 | +            out = rig.run()
 427 | +        finally:
 428 | +            restore()
 429 | +        pk = out["package"]
 430 | +        self.assertTrue(pk["caption_fallback"])
 431 | +        self.assertEqual(pk["caption"], self.FIXED)
 432 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 433 | +        self.assertEqual(out["tried"][0]["no_voice"]["caption_fallback"]["refused"][0]["rule"], "VERDICT_NO")
 434 | +
 435 | +    def test_c_a_failing_title_still_holds_and_so_do_a_title_and_caption_together(self):
 436 | +        """"The title keeps ruling 65 (c)": no fixed title. A title failing alone, or with the caption, holds."""
 437 | +        restore = self.contexts_pass()
 438 | +        try:
 439 | +            title_bad = TestRuling66Amended().failing("title", "it names no show", "VERDICT_NO")
 440 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad])
 441 | +            out = rig.run()
 442 | +            self.assertIsNone(out["package"])
 443 | +            self.assertIn("title / caption fail", out["tried"][0]["no_voice"]["why_not"])
 444 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 445 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad],
 446 | +                      caption=self.UPPER)                                       # both lines fail: no lone caption
 447 | +            out = rig.run()
 448 | +            self.assertIsNone(out["package"])
 449 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 450 | +        finally:
 451 | +            restore()
 452 | +
 453 | +    def test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends(self):
 454 | +        """As there (ruling 65 b): the fixed line has no model verdict, but context integrity on the package as it will
 455 | +        be sealed still decides. A failing run ends the line-up; nothing ships unchecked."""
 456 | +        import context_integrity as CI
 457 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 458 | +        CI.check_contexts = lambda *a, **k: {"ok": False, "violations": [{"rule": "STRONGER", "segment": "hook",
 459 | +                                                                          "detail": "x"}], "measured": True,
 460 | +                                             "replayed": False, "backends": {"B": "xai", "C": "xai"}}
 461 | +        CI.contexts_from_sources = lambda *a, **k: {}
 462 | +        try:
 463 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 464 | +            out = rig.run()
 465 | +        finally:
 466 | +            CI.check_contexts, CI.contexts_from_sources = saved
 467 |          self.assertIsNone(out["package"])
 468 | -        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # the bad line never reached it
 469 | -        self.assertNotIn("no_voice", out["tried"][0])
 470 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 471 | +        nv = out["tried"][0]["no_voice"]
 472 | +        self.assertIn("the fixed caption", nv["why_not"])
 473 | +        self.assertEqual(nv["caption_fallback"]["fixed"], self.FIXED)
 474 | +
 475 | +    def test_c_ruling_3s_no_voice_path_takes_the_fixed_caption_too(self):
 476 | +        """(C) covers either no-voice path: the takeaway failed its gates twice (ruling 3), clip z is added, and the
 477 | +        latest write's caption, failing alone, becomes the fixed line."""
 478 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 479 | +        restore = self.contexts_pass()
 480 | +        try:
 481 | +            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 482 | +                      takeaways=bad, caption=self.UPPER)
 483 | +            out = rig.run()
 484 | +        finally:
 485 | +            restore()
 486 | +        pk = out["package"]
 487 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
 488 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 489 | +        self.assertTrue(pk["caption_fallback"])
 490 | +        self.assertEqual(pk["caption"], "nobody bends the rules\na / b / c / d")
 491 | +        self.assertEqual(rig.value_calls, [])                                  # house style refused both takeaways first
 492 |  
 493 |      def test_the_real_verdict_runs_inside_the_build_and_its_row_seals(self):
 494 |          """build() with package.takeaway_value itself (not the Rig's stub), only the router faked: a clear yes seals
 495 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

BACKGROUND (static):
- A MEDLEY pin: the hook clip + 2-4 clips back to back, then at most ONE spoken VO line after the LAST clip (the
  takeaway), then a code-written sign-off. package.build() writes the takeaway, gates it, and seals a pin.
- THE NO-VOICE SHAPE (ruling 3, Nov 12): when the takeaway is removed, the package ships with NO VO line: clips back to
  back and the sign-off. When the clips are too short for the 60-70 s format, ONE more clip of the angle is added (the
  proposer's order), and the new line-up is judged on the clips alone again; every clip gate runs.
- RULING 91's medley half (committed earlier today, 6626c45d): every written takeaway gets ONE value verdict (four
  clear yeses) before any paid gate; a takeaway that loses it never ships. The text: "a medley that loses its takeaway
  falls back to L-y's no-voice shape only if its clips meet the seconds; otherwise the takeaway may be rewritten once."
  As committed, a value loss went to the no-voice shape only on the line-up's OWN clips (never an added clip), else one
  rewrite of the takeaway alone; a second loss ended the line-up.
- RULING 65 (b): when a medley's caption fails its gates, the caption becomes a FIXED line written by code (the title in
  lowercase, a line break, the shows' names; caption_fallback true): no model verdict on it, but its deterministic layer,
  the house style and context integrity still run. Ruling 65 (c): a failing title is held (no fixed title).

THE ORCHESTRATOR'S RULINGS (07:30 ET Nov 14), verbatim:
(A) "NO. Ruling 91 does not end ruling 3's added clip. The no-voice shape is one shape whatever removed the takeaway
    (two failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
    need it, each added clip passing every clip gate and the joins as usual."
(C) "YES, build it: on a no-voice path, when only the caption fails its gates, ruling 65 (b)'s fixed caption is used and
    the line-up goes on (caption_fallback: true, as there). The title keeps ruling 65 (c)."

THE BUILDER'S READING OF (A), stated on STATE for the orchestrator:
a value verdict's no removes the takeaway and the ONE no-voice shape follows (own clips, or the added clip when the
seconds need it). Ruling 91's one rewrite is used only when NO no-voice line-up can be formed (no clip lands the
seconds, or a join needs a bridge). A no-voice line-up that then fails a gate ends the line-up, as on ruling 3's path.

THE CHANGE (pipeline/package.py; the diff follows):
1. nv_order() (a closure in build()): the no-voice line-up decided by code before any paid call, with ruling 3's own
   rules moved out of no_voice() unchanged. no_voice() uses it for BOTH rulings; the "no clip added on the ruling-91
   path" guard is gone. The module-level no_voice_fits() (own clips only) is removed: nothing calls it now.
2. The value-loss branch asks nv_order(): a line-up exists -> break to no_voice(value=...) (which adds the clip when
   needed and judges the new line-up on the clips alone); none -> one rewrite; a second loss ends the line-up.
3. fixed_caption_gates(): ruling 65 (b)'s fixed-caption gating, extracted unchanged from rewrite_alone() (which now
   calls it), and used by no_voice() when ONLY the caption fails, by ruling 65's own trigger: every cheap and fidelity
   violation on the caption slot, context integrity passing, the fidelity verdict measured. The fixed line's cheap
   gates, merged fidelity and context integrity must then pass, or the line-up ends. A failing title still holds.
4. Tests (tests/package/test_medley.py): (A) the added clip on a value loss; a failed no-voice line-up ends without a
   rewrite; the rewrite only when no no-voice line-up exists. (C) the fixed caption after a cheap failure and after a
   verdict failure; a failing title holds (alone or with the caption); the fixed line's own context run still decides;
   ruling 3's path gets it too. One test removed: "a value loss never counts toward ruling 3's two failures" (under (A)
   both paths lead to the same shape, so that count changes no outcome). 15 mutations, each killed. 19 suites, 543 tests.

ATTACK:
(a) Is (A) implemented exactly: same shape and same added-clip rules on both paths; no path where a value loss adds a
    clip that ruling 3 would not, or vice versa; the added clip's line-up judged on the clips alone again?
(b) Is the extraction of fixed_caption_gates() behaviour-preserving for ruling 65's voiced path (rewrite_alone)?
(c) (C): can a fixed caption ship when anything OTHER than the caption failed (the title, a "-" rule such as RUNTIME
    or R4, a clip's own gate, context integrity)? Can a fixed caption skip its own gates?
(d) Is nv_order() deterministic and identical between the in-loop decision and the post-loop no_voice() call (same
    dropped / doomed / registry state), so the decision to skip the rewrite always matches what no_voice() does?
(e) The removed test and the removed no_voice_fits(): any remaining caller or any behaviour now untested?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".

