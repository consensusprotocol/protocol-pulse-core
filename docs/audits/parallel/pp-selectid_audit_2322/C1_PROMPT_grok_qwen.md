# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2322
# Branch: pp-selectid
# Generated: 2026-11-13 23:22 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2322/C1_STEP.diff (2018 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | index 2da920e..e7095b4 100644
   3 | --- a/pipeline/lock_precheck.py
   4 | +++ b/pipeline/lock_precheck.py
   5 | @@ -42,10 +42,12 @@ import attest as AT
   6 |  
   7 |  RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
   8 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
   9 | -DECODER = "962353613cb0"                      # side): the render's own cut placement joins the pre-check (a passing
  10 | +DECODER = "c705b20ed800"                      # side): the render's own cut placement joins the pre-check (a passing
  11 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  12 | -#   84 changes the render's adjudicate_lock (pinned.py), so the decoder_sha changed again: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  13 | -#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7)
  14 | +#   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  15 | +#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  16 | +#   spotlight branches in pinned.py, merged fd5c9cc4 at 23:16 ET Nov 13; RULES unchanged; every medley span's decode,
  17 | +#   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  18 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  19 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  20 |                          "lock_requests")      # this worktree's; the service only reads it
  21 | diff --git a/pipeline/package.py b/pipeline/package.py
  22 | index 68384f1..8972b95 100644
  23 | --- a/pipeline/package.py
  24 | +++ b/pipeline/package.py
  25 | @@ -156,12 +156,13 @@ def expired(m, now):
  26 |      return age is None or age > package_pin.WINDOW_H
  27 |  
  28 |  
  29 | -def usable(moments, ctx, delivered=(), optout=frozenset()):
  30 | +def usable(moments, ctx, delivered=(), optout=frozenset(), seg_max=SEG_MAX_S):
  31 |      """delivered: moment ids, or {"video_id", "start", "end"[, "text", "pin"]} of every DELIVERED clip. A moment that
  32 |      overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated),
  33 |      and (RULING 76 b) neither is the same speech (same_speech) anywhere: re-posted by another channel, or said again
  34 |      at another time of the same video (audit 1810 C3: "never reuse any of it"). RULING 76 (a): a moment whose source
  35 | -    is over 12 h old on the render clock (ctx.now) is expired."""
  36 | +    is over 12 h old on the render clock (ctx.now) is expired. seg_max: the longest clip (L-u's 20 s per source video
  37 | +    for a medley; RULING 90's 35 s for a spotlight, the orchestrator's 22:58 note)."""
  38 |      ids = {d for d in delivered if isinstance(d, str)}
  39 |      spans = [d for d in delivered if isinstance(d, dict)]
  40 |      out, why = [], {}
  41 | @@ -187,8 +188,8 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
  42 |                           ", said again at another time of the same video"))
  43 |          elif m["channel_id"] in optout:
  44 |              why[mid] = "channel opted out"
  45 | -        elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
  46 | -            why[mid] = f"{m.get('duration_s')} s: over the {SEG_MAX_S} s per source video (L-u) or unmeasured"
  47 | +        elif m.get("duration_s") is None or m["duration_s"] > seg_max:
  48 | +            why[mid] = f"{m.get('duration_s')} s: over the {seg_max} s per source video (L-u) or unmeasured"
  49 |          elif time_sensitive(m) and (E.age_hours(m["published_at"], ctx.now) is None or
  50 |                                      E.age_hours(m["published_at"], ctx.now) > TIME_SENSITIVE_H):
  51 |              why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
  52 | @@ -1152,12 +1153,14 @@ def write_candidates(path, ms, ctx, build_name):
  53 |      return True
  54 |  
  55 |  
  56 | -def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
  57 | +def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, extra=()):
  58 |      """RULING 56, once per build, before any verdict is attached. (1) The integrator's verdicts (scorer_verdicts, fail
  59 |      closed). (2) The next pass's candidates (write_candidates): every moment the render's STAND_ALONE leaves out as an
  60 |      opener the clip scorer would have to affirm (no_role_on_screen fires, the topic rule does not: no verdict could
  61 |      give a moment that fails the topic rule a place), and the trimmed variant of every moment left out (ruling 33 part
  62 | -    2), each with its text exactly as it would be locked. -> {"index": {pid: verdict}, "record": {...}}."""
  63 | +    2), each with its text exactly as it would be locked. extra (RULING 90): the spotlight pool's moments
  64 | +    (spotlight.pool), whose stand-alone rating the spotlight needs; they join the same request, so the medley's own
  65 | +    candidates and the spotlight's never replace each other. -> {"index": {pid: verdict}, "record": {...}}."""
  66 |      index, rec = scorer_verdicts(verdicts_path, render_scorer_sha()) if verdicts_path else \
  67 |          ({}, {"read": False, "why": "no verdicts file given"})
  68 |      if candidates_path:
  69 | @@ -1165,6 +1168,12 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name):
  70 |                  ({k: x for k, x in m.items() if k != "scorer_verdict"} for m in ms)]
  71 |          ask = [m for m, o, t in left if o and not t] + \
  72 |              [v for m, o, t in left if o or t for v in [trim_variant(m, sources)] if v]
  73 | +        have = {(m["moment_id"], text_sha(m["text"])) for m in ask}
  74 | +        for m in extra or ():                            # ruling 90: once each (same id and text)
  75 | +            k = (m["moment_id"], text_sha(m["text"]))
  76 | +            if k not in have:
  77 | +                have.add(k)
  78 | +                ask.append({x: y for x, y in m.items() if x != "scorer_verdict"})
  79 |          rec = dict(rec, candidates=len(ask), candidates_written=write_candidates(candidates_path, ask, ctx, build_name))
  80 |      return {"index": index, "record": rec}
  81 |  
  82 | @@ -2168,7 +2177,7 @@ def candidate_lineup(router, candidate, cleared, now):
  83 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  84 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  85 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  86 | -          visual_cache=None, registered=None, lock_check=None):
  87 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
  88 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  89 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  90 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  91 | @@ -2208,6 +2217,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  92 |        - a package keeps the approved texts, or seals an adopted spoken text with its "attested" record
  93 |          (lock_precheck.apply, checked again at the pin stage).
  94 |      The no-voice line-up is asked too. lock_check None: no pre-check (the tests' rigs); the driver always passes it.
  95 | +    scorer_extra (RULING 90): the spotlight pool's moments, sent to the clip scorer with this build's own candidates.
  96 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
  97 |      t0 = time.time()
  98 |      usd0 = _spent(spend)
  99 | @@ -2237,7 +2247,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 100 |      ms, why = usable(moments, ctx, delivered, optout)
 101 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 102 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 103 | -    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name)   # ruling 56
 104 | +    scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name,   # ruling 56
 105 | +                         extra=scorer_extra)                                                       # ruling 90
 106 |      ms = [with_verdict(m, scorer["index"]) for m in ms]
 107 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
 108 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
 109 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 110 | index 34b2e86..0954e1c 100644
 111 | --- a/pipeline/package_pin.py
 112 | +++ b/pipeline/package_pin.py
 113 | @@ -33,10 +33,45 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 114 |                  "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 115 |  
 116 |  
 117 | +# RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
 118 | +# Its contract, agreed with the integrator (22:44 ET): moments_package.shape "spotlight", ONE segment (role "hook"),
 119 | +# edl_vo {"intro": null, "bridges": [], "closing": <one line, <= 12 words> or null}, signoff_expected naming that one
 120 | +# channel, first_comment the WHOLE first comment (printed verbatim, nothing appended), and these gate rows, each exactly
 121 | +# PASS and not replayed. No medley row applies (no join, no clips-alone verdict, no coherence of several clips, no L-y
 122 | +# shape); the R4 of a spotlight is its 28-50 s runtime (the render's edl_rules R4 / G5), the "runtime" row.
 123 | +SPOTLIGHT_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime",
 124 | +                   "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable",
 125 | +                   "house_style", "hook_onset", "stand_alone",          # it opens cold: the hook's own pin-stage rows
 126 | +                   "spotlight_source",                                   # ruling 92: conversation, not reaction
 127 | +                   "hook_own", "stands_alone",                           # ruling 90: >= 4 as an opener, >= 4 alone
 128 | +                   "step_a_two_families", "visual", "window_12h", "never_delivered", "one_per_channel_day",
 129 | +                   "precheck")                                           # rulings 68 / 72 / 73 / 84: pass or adopt
 130 | +CLOSING_GATES = ("closing_value", "closing_fidelity", "closing_context")   # ruling 91: a non-null closing only with all
 131 | +SPOT_RUNTIME_S = (28.0, 50.0)            # ruling 90: the moment, the closing line, sign-off, credits card and outro
 132 | +SPOT_CLOSING_MAX_WORDS = 12              # ruling 90 / 91: at most ONE closing line of 12 words or fewer
 133 | +CREDITS_LINE = "Credits \U0001F9E1"      # ruling 90: PBX's first-comment format, 'Credits' and the orange heart
 134 | +
 135 | +
 136 | +def _closing(pk):
 137 | +    """The spotlight's closing line in a package (pk["vo"]) or in a pin's moments_package (edl_vo), else None."""
 138 | +    vo = (pk or {}).get("vo") if isinstance((pk or {}).get("vo"), dict) else (pk or {}).get("edl_vo")
 139 | +    return (vo or {}).get("closing")
 140 | +
 141 | +
 142 |  def required_gates(pk):
 143 |      """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 144 | -    clips-alone verdict and the L-y shape."""
 145 | -    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 146 | +    clips-alone verdict and the L-y shape. A spotlight (ruling 90): SPOTLIGHT_GATES, plus CLOSING_GATES whenever its
 147 | +    closing line is not null (ruling 91). pk: a package, or a pin's moments_package."""
 148 | +    shape = (pk or {}).get("shape")
 149 | +    if shape == "spotlight":
 150 | +        return SPOTLIGHT_GATES + (CLOSING_GATES if _closing(pk) is not None else ())
 151 | +    return REQUIRED_GATES + (MEDLEY_GATES if shape == "medley" else ())
 152 | +
 153 | +
 154 | +def first_comment_text(lines, tags):
 155 | +    """RULING 90: the first comment in PBX's format, the WHOLE comment: the casual line(s), a blank line, 'Credits' and
 156 | +    the orange heart, a blank line, the credits (verified X handles, or the untagged names). Code, never the model."""
 157 | +    return f"{lines}\n\n{CREDITS_LINE}\n\n{' '.join(tags)}"
 158 |  
 159 |  
 160 |  class PinRefused(Exception):
 161 | @@ -112,7 +147,7 @@ def window_problems(segments, now=None):
 162 |      return out
 163 |  
 164 |  
 165 | -def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 166 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None):
 167 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 168 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 169 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
 170 | @@ -121,7 +156,10 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 171 |      all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
 172 |      because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest.
 173 |      btc_screen (ruling 34: the miner's about-Bitcoin screen the render applies, {"pattern", "source"}) enters the body
 174 | -    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems)."""
 175 | +    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems).
 176 | +    RULING 90, the spotlight: edl_vo's "closing" enters the VO body only when edl_vo carries the key, and shape and
 177 | +    first_comment enter the body only for shape "spotlight" (a spotlight always carries all three, null closing
 178 | +    included). A medley's body never holds them, so every pin sealed before the spotlight recomputes (pin_seal)."""
 179 |      def body_of(s):
 180 |          b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 181 |               "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
 182 | @@ -131,11 +169,26 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 183 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
 184 |                                                               for b in edl_vo.get("bridges") or []]},
 185 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 186 | +    if "closing" in edl_vo:                                # ruling 90: only a spotlight's edl_vo carries the key
 187 | +        body["vo"]["closing"] = edl_vo["closing"]
 188 |      if btc_screen is not None:
 189 |          body["btc_screen"] = btc_screen
 190 | +    if shape == "spotlight":                               # ruling 90: the kind and the comment, sealed
 191 | +        body["shape"], body["first_comment"] = shape, first_comment
 192 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 193 |  
 194 |  
 195 | +def pin_seal(pin):
 196 | +    """The package_sha256 a pin's own bytes recompute to, exactly as to_pin sealed it, for every kind (a medley, the
 197 | +    PBX MAX v3 shape, a spotlight): the readiness check's one call. Raises KeyError / TypeError on a pin without the
 198 | +    sealed fields."""
 199 | +    mp = pin["moments_package"]
 200 | +    shape = mp.get("shape")
 201 | +    return seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"],
 202 | +                mp.get("btc_screen"), shape="spotlight" if shape == "spotlight" else None,
 203 | +                first_comment=mp.get("first_comment") if shape == "spotlight" else None)
 204 | +
 205 | +
 206 |  def affirmed_verdict(s):
 207 |      """RULING 56 under RULING 60: True when the segment carries the render's own clip scorer's AFFIRMATION of exactly its
 208 |      text (approved_text in a pin, text in a package): scorer_verdict with affirmed true, kind "moments" and no event
 209 | @@ -210,11 +263,11 @@ def screen_problems(pk):
 210 |      the screen but sealed without it could be refused at render. A carried screen is {"pattern": a non-empty str of at
 211 |      most 500 characters that compiles with re.I, "source": a non-empty str}: the render's own acceptance
 212 |      (run_fresh.moments_screen)."""
 213 | -    if pk.get("shape") != "medley":
 214 | +    if pk.get("shape") not in ("medley", "spotlight"):    # ruling 90: a spotlight is judged with the screen too
 215 |          return []
 216 |      sc = pk.get("btc_screen")
 217 |      if not isinstance(sc, dict) or set(sc) != {"pattern", "source"}:
 218 | -        return ["btc_screen: a medley must carry {pattern, source} (ruling 34)"]
 219 | +        return [f"btc_screen: a {pk.get('shape')} must carry {{pattern, source}} (ruling 34)"]
 220 |      pat, src = sc.get("pattern"), sc.get("source")
 221 |      if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 or not isinstance(src, str) or not src.strip():
 222 |          return ["btc_screen: the pattern must be a non-empty str of at most 500 characters, with a source"]
 223 | @@ -294,6 +347,42 @@ def line_problems(pk):
 224 |      for k in ("title", "caption"):
 225 |          if by.get(k) != pk.get(k):
 226 |              out.append(k)
 227 | +    if pk.get("shape") == "spotlight":                    # ruling 90: the closing line and the first comment too
 228 | +        if by.get("closing") != vo.get("closing"):
 229 | +            out.append("closing")
 230 | +        cr = pk.get("comment_credits") or {}
 231 | +        com = by.get("comment")
 232 | +        if not isinstance(com, str) or not com.strip() or not isinstance(cr.get("tags"), list) or \
 233 | +                not all(isinstance(t, str) and t.strip() for t in cr["tags"]) or \
 234 | +                pk.get("first_comment") != first_comment_text(com, cr["tags"]):
 235 | +            out.append("first_comment")
 236 | +    return out
 237 | +
 238 | +
 239 | +def spotlight_problems(pk):
 240 | +    """[why] for a spotlight that breaks the agreed contract (ruling 90): exactly ONE segment; no intro and no bridge;
 241 | +    a closing line of at most SPOT_CLOSING_MAX_WORDS words, or null; a sign-off that names the segment's channel; a
 242 | +    non-empty first comment; the runtime estimate inside SPOT_RUNTIME_S. Any other shape: none."""
 243 | +    if pk.get("shape") != "spotlight":
 244 | +        return []
 245 | +    out = []
 246 | +    segs = pk.get("segments") or []
 247 | +    vo = pk.get("vo") or {}
 248 | +    if len(segs) != 1:
 249 | +        out.append(f"a spotlight has exactly one segment (got {len(segs)})")
 250 | +    if vo.get("intro") is not None or vo.get("bridges") or vo.get("bridges_after_clip"):
 251 | +        out.append("a spotlight has no intro and no bridge (ruling 90)")
 252 | +    c = vo.get("closing")
 253 | +    if c is not None and (not isinstance(c, str) or not c.strip() or len(c.split()) > SPOT_CLOSING_MAX_WORDS):
 254 | +        out.append(f"the closing line must be null or 1-{SPOT_CLOSING_MAX_WORDS} words (ruling 90): {c!r}")
 255 | +    ch = segs[0].get("channel") if len(segs) == 1 else None
 256 | +    if not isinstance(ch, str) or not ch.strip() or ch not in str(vo.get("signoff") or ""):
 257 | +        out.append(f"the sign-off must name the spotlight's one channel {ch!r} (ruling 90)")
 258 | +    if not isinstance(pk.get("first_comment"), str) or not pk["first_comment"].strip():
 259 | +        out.append("a spotlight carries its first comment (ruling 90)")
 260 | +    rt = pk.get("runtime_s_estimate")
 261 | +    if not isinstance(rt, (int, float)) or isinstance(rt, bool) or not SPOT_RUNTIME_S[0] <= rt <= SPOT_RUNTIME_S[1]:
 262 | +        out.append(f"runtime estimate {rt!r} outside {SPOT_RUNTIME_S[0]:g}-{SPOT_RUNTIME_S[1]:g} s (ruling 90)")
 263 |      return out
 264 |  
 265 |  
 266 | @@ -301,7 +390,8 @@ def to_pin(pk, run_name):
 267 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 268 |                                                                       for x in line_problems(pk)] + \
 269 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 270 | -        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or [])
 271 | +        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
 272 | +        spotlight_problems(pk)
 273 |      if problems:
 274 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 275 |      segs = []
 276 | @@ -317,7 +407,11 @@ def to_pin(pk, run_name):
 277 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 278 |      edl_vo = {"intro": pk["vo"]["intro"],
 279 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 280 | -    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"))
 281 | +    spot = pk.get("shape") == "spotlight"                 # ruling 90: the agreed contract
 282 | +    if spot:
 283 | +        edl_vo["closing"] = pk["vo"].get("closing")
 284 | +    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"),
 285 | +               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None)
 286 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
 287 |              "label": "bitcoin", "headline": pk["title"],
 288 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
 289 | @@ -332,12 +426,18 @@ def to_pin(pk, run_name):
 290 |                                  "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
 291 |                                                 if pk["vo"]["intro"] else {}),
 292 |                                              **{s: "takeaway" if s == "takeaway" else "connection"
 293 | -                                               for s in bridge_slots(pk)}},
 294 | +                                               for s in bridge_slots(pk)},
 295 | +                                            **({"closing": "closing"} if spot and edl_vo["closing"] is not None
 296 | +                                               else {})},
 297 |                                  "shape": pk.get("shape"),
 298 |                                  "bridge": pk.get("bridge"),
 299 |                                  "supply_exception": pk.get("supply_exception"),
 300 |                                  "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
 301 |                                  "caption_fallback": bool(pk.get("caption_fallback")),   # ruling 65 (b): a placeholder
 302 | +                                **({"first_comment": pk["first_comment"],              # ruling 90: sealed, printed
 303 | +                                    "first_comment_credits": pk.get("comment_credits"),  # verbatim; who is tagged
 304 | +                                    "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 305 | +                                   if spot else {}),
 306 |                                  "gates": pk["gates"],
 307 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 308 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 309 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 310 | new file mode 100644
 311 | index 0000000..4634ebd
 312 | --- /dev/null
 313 | +++ b/pipeline/spotlight.py
 314 | @@ -0,0 +1,1002 @@
 315 | +#!/usr/bin/env python3
 316 | +"""pipeline/spotlight.py: RULINGS 90, 91 and 92 (the orchestrator's 22:40 and 22:52 orders, Nov 13; ruling 90 is LAW
 317 | +since 22:52): the SPOTLIGHT, a second pin kind. The medley stays the flagship and is always tried first: "a spotlight
 318 | +is built only when the window's search ends with no medley, or for a moment no medley used".
 319 | +
 320 | +RULING 90, its words: "ONE moment, one speaker, one channel: 12 to 35 s of clip. No hook/clip split, no bridge, no
 321 | +join. Then at most ONE closing line in the PBX MAX voice, 12 words or fewer, class D commentary that characterises what
 322 | +was SAID (the two refused patterns stay refused) ... Then the sign-off and the credits card with that one channel, then
 323 | +the outro. Total 28 to 50 s. ... it must rate >= 4 on the hook's own job (it opens cold) AND >= 4 as a clip standing
 324 | +alone (the ALONE scorer + step A, both vendors as routed); the visual check clean; inside 12 h at the render clock;
 325 | +never a delivered span; at most one spotlight per channel per day. If the strong moment is under 12 s, snap it OUTWARD
 326 | +to the speaker's whole thought (ruling 32's snap; the added words judged as usual), not padded. EVERY integrity law is
 327 | +unchanged: L-s, L-v, the pre-check (17 / 72 / 73 / 84), the cut rules, G16-G20, the credits."
 328 | +RULING 91: "Default for a spotlight: NO PBX line ... A line is written only as a candidate and is kept only if a
 329 | +separate VALUE verdict (off the writer's family) answers all of: it says something the clip does not already say; it
 330 | +does not restate, summarise or cheer the clip; a viewer would miss it if it were cut; it is 12 words or fewer; plus
 331 | +the usual fidelity and context gates. One write, one verdict; anything short of a clear yes means no line."
 332 | +RULING 92: "A spotlight moment must come from a conversation or original reporting ... NOT from a solo host-to-camera
 333 | +news recap or reaction segment, on any channel. Measured, not listed by name: the turn markers across the episode (one
 334 | +speaker throughout = solo), plus the visual check's layout (one face to camera with headline graphics or b-roll =
 335 | +recap)."
 336 | +The pin contract, agreed with the integrator at 22:44 ET: package_pin's shape "spotlight" (SPOTLIGHT_GATES,
 337 | +CLOSING_GATES, spotlight_problems, first_comment_text, the sealed closing / shape / first comment).
 338 | +
 339 | +- pool(): free, before any verdict. package.usable with ruling 90's 35 s ceiling (the orchestrator's 22:58 note: L-u's
 340 | +  20 s per source video is a medley rule), one spotlight per channel per ET day (the SPOTLIGHTS record), the snap of a
 341 | +  short moment (snap()), the render's hook opener rule and its topic rule. The driver sends the pool to the clip scorer
 342 | +  with the medley's own candidates at the build's start (package.build's scorer_extra), so the ALONE rating is asked
 343 | +  before the spotlight needs it.
 344 | +- build(): the medley's own verdicts, each cached or recorded across builds (step A, the second recognition pass and
 345 | +  CUTTABLE, G17a, the hook rating, the visual sheet, the second step-A family), then the ALONE scorer, ruling 92's
 346 | +  source test, the exclusion verdict and the render's lock pre-check, best moment first; then ONE write (title,
 347 | +  caption, the first comment and a candidate closing line), the gates, the closing line's value verdict, and the
 348 | +  package. Nothing measured is never a pass (law L-m); any failure of the closing line leaves no line (ruling 91).
 349 | +"""
 350 | +import base64
 351 | +import hashlib
 352 | +import json
 353 | +import os
 354 | +import re
 355 | +import threading
 356 | +import time
 357 | +from concurrent.futures import ThreadPoolExecutor
 358 | +
 359 | +import context_integrity as CI
 360 | +import eligibility as E
 361 | +import house_style as HS
 362 | +import package as P
 363 | +import package_pin as PP
 364 | +import vo_fidelity as VF
 365 | +
 366 | +SPOT_S = (12.0, 35.0)                  # ruling 90: 12 to 35 s of clip
 367 | +RUNTIME_S = PP.SPOT_RUNTIME_S          # ruling 90: total 28 to 50 s (the render's edl_rules R4 / G5)
 368 | +SNAP_TO_S = round(max(SPOT_S[0], RUNTIME_S[0] - P.FINAL_TAIL_S), 2)
 369 | +#   13.7 s: the factory's tail (sign-off, credits card, outro, edges) is 14.3 s, so with no closing line (ruling 91's
 370 | +#   default) a shorter clip cannot reach 28 s. A moment shorter than this is snapped; it is never padded.
 371 | +HOOK_MIN = 4                           # ruling 90: >= 4 on the hook's own job (package.hook_own: scroll / alone)
 372 | +ALONE_MIN = 4.0                        # ruling 90: >= 4 standing alone, by the ALONE scorer (its scale is 1-5)
 373 | +CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
 374 | +COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
 375 | +COMMENT_MAX_WORDS = 30
 376 | +MARKER_TOL_S = 1.0                     # = ledger_build.MARKER_EDGE_S: a caption marker this close to an edge is not in
 377 | +LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
 378 | +LAYOUT_OK = ("conversation", "first_hand")
 379 | +CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 380 | +FINALISTS = 3                          # moments taken to exclusion, the pre-check and the write, best first
 381 | +WRITES = 2                             # the title, caption and comment: one more write when a gate refuses them
 382 | +SCORER_WAIT_S = 600.0                  # a moment that passes everything but has no ALONE rating yet waits this long for
 383 | +SCORER_POLL_S = 30.0                   # the integrator's scorer pass (its request went out at the build's start)
 384 | +HANDLES = "/home/ultron/protocol_pulse/pipeline/channels.json"   # the integrator's registry: x_handle is verified,
 385 | +HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")                 # an empty one is none (22:44 ET)
 386 | +VALUE_KEYS = ("adds", "no_restate", "missed", "short")
 387 | +CLOSING_SAID = P.TAKEAWAY_SAID.replace("The takeaway may", "The closing line may").replace("the clips SAID",
 388 | +                                                                                            "the clip SAID")
 389 | +
 390 | +
 391 | +def et_day(now):
 392 | +    """The ET calendar day of the render clock (all times ET): the 'day' of one spotlight per channel per day."""
 393 | +    from zoneinfo import ZoneInfo
 394 | +    return now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
 395 | +
 396 | +
 397 | +def load_spotlit(path):
 398 | +    """The spotlights already sealed: [{"channel_id", "channel", "day_et", "story_id", "package_sha256", "at"}]. No
 399 | +    file: none yet. -> the list, or None when the file cannot be read (then one per channel per day is not measured,
 400 | +    and no spotlight is built: law L-m)."""
 401 | +    if not os.path.exists(path):
 402 | +        return []
 403 | +    try:
 404 | +        with open(path) as f:
 405 | +            rows = json.load(f)["spotlights"]
 406 | +    except (OSError, ValueError, KeyError, TypeError):
 407 | +        return None
 408 | +    ok = isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("channel_id"), str) and
 409 | +                                        r["channel_id"] and isinstance(r.get("day_et"), str) for r in rows)
 410 | +    return rows if ok else None
 411 | +
 412 | +
 413 | +def record_spotlit(path, row):
 414 | +    """Append one sealed spotlight to the record, atomically. Raises ValueError when the record cannot be read."""
 415 | +    rows = load_spotlit(path)
 416 | +    if rows is None:
 417 | +        raise ValueError(f"{path} cannot be read: the spotlight is not recorded")
 418 | +    with open(path + ".tmp", "w") as f:
 419 | +        json.dump({"spotlights": rows + [row]}, f, indent=1)
 420 | +    os.replace(path + ".tmp", path)
 421 | +
 422 | +
 423 | +def snap(m, sources, ctx, captions_for=None):
 424 | +    """RULING 90 with ruling 32's snap: a moment shorter than SNAP_TO_S is snapped OUTWARD to the speaker's whole
 425 | +    thought: whole sentences of the SAME word record, the next ones first (the speaker going on), then the ones before
 426 | +    it, until it lasts SNAP_TO_S, never past SPOT_S[1] and never across a caption speaker-change marker (ruling 69's
 427 | +    markers; MARKER_TOL_S from an edge does not count, as ruling 32 reads them). Never padded. Captions with no marker
 428 | +    show no change; L-v 2 then measures one speaker on the audio, as for any snapped moment. The snapped span is a NEW
 429 | +    moment (its own id; the miner's eligibility and price-prediction risk judged again on it) and every gate of the
 430 | +    build judges it as usual. -> (moment, None) or (None, why)."""
 431 | +    import ledger_build as LB
 432 | +    import moments as M
 433 | +    import speakers as SP
 434 | +    try:
 435 | +        src = P.src_of(m, sources)
 436 | +        k0, k1 = m["sentences"]
 437 | +        n = len(src.sentences)
 438 | +        units, _ = (captions_for or SP.captions)(m["video_id"])
 439 | +    except Exception as e:                             # noqa: BLE001  no record to snap in: never a guess
 440 | +        return None, f"no word record or caption record to snap in ({type(e).__name__}: {str(e)[:120]})"
 441 | +    marks = [u[0] for u in units or () if u[2]]
 442 | +
 443 | +    def t(i, key):
 444 | +        x = src.tokens[i].get(key)
 445 | +        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
 446 | +
 447 | +    def measure(a, b):
 448 | +        t0, t1 = t(src.sentences[a][0], "start"), t(src.sentences[b][1], "end")
 449 | +        if t0 is None or t1 is None:
 450 | +            return None, "a word time is missing"
 451 | +        if t1 - t0 > SPOT_S[1]:
 452 | +            return None, f"it would run {t1 - t0:.2f} s, over {SPOT_S[1]:g} s"
 453 | +        inside = [x for x in marks if t0 + MARKER_TOL_S < x < t1 - MARKER_TOL_S]
 454 | +        if inside:
 455 | +            return None, f"a caption speaker-change marker at {inside[0]:.2f} s"
 456 | +        return t1 - t0, None
 457 | +
 458 | +    a, b = k0, k1
 459 | +    dur, why = measure(a, b)
 460 | +    if dur is None:
 461 | +        return None, f"the moment itself is not measured: {why}"
 462 | +    if dur >= SNAP_TO_S:
 463 | +        return m, None                                 # long enough: no snap, the moment as it is
 464 | +    blocked = []
 465 | +    while dur < SNAP_TO_S:
 466 | +        step = None
 467 | +        for na, nb, side in ((a, b + 1, "the next sentence"), (a - 1, b, "the sentence before")):
 468 | +            if na < 0 or nb >= n:
 469 | +                blocked.append(f"{side}: the word record ends")
 470 | +                continue
 471 | +            d, w = measure(na, nb)
 472 | +            if d is None:
 473 | +                blocked.append(f"{side}: {w}")
 474 | +                continue
 475 | +            step = (na, nb, d)
 476 | +            break
 477 | +        if step is None:
 478 | +            return None, f"{dur:.2f} s and no whole sentence can be added ({'; '.join(blocked[-2:])})"
 479 | +        a, b, dur = step
 480 | +    sp = E.Span(src, a, b)
 481 | +    w_old0, w_old1 = src.sentences[k0][0], src.sentences[k1][1]
 482 | +    info = {"snapped_words": [w_old0 - sp.w0, sp.w1 - w_old1]}
 483 | +    record = {"from": m["moment_id"], "sentences": [a, b], "was": [k0, k1], "seconds": [m.get("duration_s"), None],
 484 | +              "added": {"before": E.spoken(src.tokens[sp.w0:w_old0]), "after": E.spoken(src.tokens[w_old1 + 1:sp.w1 + 1])},
 485 | +              "rule": f"ruling 90 with ruling 32's snap: whole sentences outward to {SNAP_TO_S:g} s, no speaker marker"}
 486 | +    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
 487 | +                        "risk": LB.snap_risk(sp.text, info, m.get("risk")), "topics": list(m.get("topics") or []),
 488 | +                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
 489 | +                   dict(m.get("mined") or {}, spotlight_snap_from=m["moment_id"]))
 490 | +    rec["rank_score"] = M.rank_score(rec)
 491 | +    if m.get("source_key"):
 492 | +        rec["source_key"] = m["source_key"]
 493 | +    record["seconds"][1] = rec["duration_s"]
 494 | +    rec["spotlight_snap"] = record
 495 | +    return rec, None
 496 | +
 497 | +
 498 | +def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), captions_for=None):
 499 | +    """Stage 1, FREE (no vendor call) -> (the moments that may be a spotlight, {moment id: why not}): package.usable
 500 | +    with ruling 90's 35 s ceiling (inside 12 h on the render clock, never a delivered span or the same speech, no hard
 501 | +    exclusion, no speaker change inside, L-v 3), one per re-posted speech (ruling 53), one spotlight per channel per ET
 502 | +    day (spotlit; None: not measured, so none), a moment under SNAP_TO_S snapped (snap(), then usable() again on the
 503 | +    snapped span), the render's STAND_ALONE hook opener rule (it opens cold) and its topic rule."""
 504 | +    import stand_alone as SA
 505 | +    ms, why = P.usable(moments, ctx, delivered, optout, seg_max=SPOT_S[1])
 506 | +    ms, reposted = P.reposted_once(ms, sources)
 507 | +    why.update({k: f"ruling 53: {v}" for k, v in reposted.items()})
 508 | +    if spotlit is None:
 509 | +        why.update({m["moment_id"]: "ruling 90: one spotlight per channel per day is not measured (the spotlights "
 510 | +                                    "record cannot be read)" for m in ms})
 511 | +        return [], why
 512 | +    day = et_day(ctx.now)
 513 | +    taken = {r["channel_id"] for r in spotlit if r.get("day_et") == day}
 514 | +    out, seen = [], set()
 515 | +    for m in ms:
 516 | +        mid = m["moment_id"]
 517 | +        if m["channel_id"] in taken:
 518 | +            why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
 519 | +            continue
 520 | +        v = m
 521 | +        if float(m["duration_s"]) < SNAP_TO_S:
 522 | +            v, w = snap(m, sources, ctx, captions_for)
 523 | +            if v is None:
 524 | +                why[mid] = f"ruling 90: {m['duration_s']} s is under {SNAP_TO_S:g} s and the snap fails: {w}"
 525 | +                continue
 526 | +            ok, w2 = P.usable([v], ctx, delivered, optout, seg_max=SPOT_S[1])
 527 | +            if not ok:
 528 | +                why[mid] = f"ruling 90: snapped to {v['moment_id']} ({v['duration_s']} s), which is out: " \
 529 | +                           f"{w2.get(v['moment_id'])}"
 530 | +                continue
 531 | +        if v["moment_id"] in seen:
 532 | +            why[mid] = f"the same span as {v['moment_id']}, already in the pool"
 533 | +            continue
 534 | +        ok, w = SA.opener("hook", v.get("text") or "")
 535 | +        if not ok:
 536 | +            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"
 537 | +            continue
 538 | +        top = P.no_topic(v)
 539 | +        if top:
 540 | +            why[mid] = top
 541 | +            continue
 542 | +        seen.add(v["moment_id"])
 543 | +        out.append(v)
 544 | +    return out, why
 545 | +
 546 | +
 547 | +def episode_turns(video_id, captions_for=None):
 548 | +    """RULING 92's caption half: the speaker-change markers across the EPISODE (speakers.captions, ruling 69's reader).
 549 | +    -> {"measured", "turns", "minutes", "turns_per_min", "file", "sha256"}; no marked record: {"measured": False,
 550 | +    "unmarked": True} (no marker at all is unknown, not solo: pp-ingest's contract)."""
 551 | +    import speakers as SP
 552 | +    try:
 553 | +        units, rec = (captions_for or SP.captions)(video_id)
 554 | +    except Exception as e:                             # noqa: BLE001
 555 | +        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:120]}"}
 556 | +    if not units:
 557 | +        return {"measured": False, "unmarked": True,
 558 | +                "why": "no caption record with speaker-change markers: unmarked or missing (unknown, not solo)"}
 559 | +    turns = sum(1 for u in units if u[2])
 560 | +    minutes = (units[-1][0] - units[0][0]) / 60.0
 561 | +    return {"measured": True, "turns": turns, "minutes": round(minutes, 1),
 562 | +            "turns_per_min": round(turns / minutes, 2) if minutes > 0 else None,
 563 | +            "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 564 | +
 565 | +
 566 | +def source_test(turns, layout):
 567 | +    """RULING 92 -> (ok, why). A PASS needs a MEASURED layout of a conversation or a first-hand statement
 568 | +    (LAYOUT_OK). A recap, a reaction, or a layout the judge cannot place ('other') fails on any channel; a layout that
 569 | +    is not measured is never a pass (law L-m). The caption markers across the episode can only make it stricter: a
 570 | +    layout read as a conversation from an episode whose captions are marked but carry fewer than CONVERSATION_TPM
 571 | +    turns a minute is not measured as a conversation (Nov 13: Simply Bitcoin's solo recap L6H7538ogGs 0.48 turns a
 572 | +    minute; the pool's interviews and panels 1.18-2.53). Unmarked captions are unknown, not solo: the layout decides."""
 573 | +    if not (layout or {}).get("measured"):
 574 | +        return False, f"the layout is not measured: {(layout or {}).get('why')}"
 575 | +    lay = layout["layout"]
 576 | +    if lay not in LAYOUT_OK:
 577 | +        return False, f"the layout is '{lay}' ({layout.get('why')}): not a conversation or a first-hand statement"
 578 | +    tpm = (turns or {}).get("turns_per_min")
 579 | +    if lay == "conversation" and (turns or {}).get("measured") and (tpm is None or tpm < CONVERSATION_TPM):
 580 | +        return False, (f"the frames read as a conversation but the episode's captions carry {tpm} speaker turns a "
 581 | +                       f"minute (under {CONVERSATION_TPM:g})")
 582 | +    return True, f"layout '{lay}'" + (f"; {turns['turns']} caption turns in {turns['minutes']} min ({tpm} a minute)"
 583 | +                                      if (turns or {}).get("measured") else "; captions unmarked")
 584 | +
 585 | +
 586 | +LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 587 | +bottom. The clip's words, as spoken: "{text}"
 588 | +From the frames only, classify the SOURCE's format:
 589 | +- "conversation": two or more people talking with each other: an interview, a podcast, a panel (in one room, or on a
 590 | +  split screen or a video call);
 591 | +- "first_hand": one person making their own statement to an audience: a keynote, a speech, a guest answering on a news
 592 | +  network;
 593 | +- "recap": one host speaking to the camera with headline graphics, a news set or b-roll: a news recap;
 594 | +- "reaction": a host showing or reacting to another video, a post or a chart inside the host's own frame;
 595 | +- "other": none of these, or you cannot tell.
 596 | +Return ONLY this JSON object: {{"layout": "conversation" | "first_hand" | "recap" | "reaction" | "other",
 597 | +"people_on_screen": <the most people visible in one frame, a number>, "why": "<one sentence>"}}"""
 598 | +LAYOUT_VERSION = hashlib.sha256(LAYOUT_PROMPT.encode()).hexdigest()[:12]
 599 | +LAYOUT_LOCK = threading.Lock()
 600 | +
 601 | +
 602 | +def parse_layout(text):
 603 | +    """The layout verdict in contract, or ValueError."""
 604 | +    v = json.loads(text.strip())
 605 | +    if not isinstance(v, dict) or set(v) != {"layout", "people_on_screen", "why"}:
 606 | +        raise ValueError("keys must be exactly layout, people_on_screen, why")
 607 | +    if v["layout"] not in LAYOUTS or type(v["people_on_screen"]) is not int or v["people_on_screen"] < 0 or \
 608 | +            not isinstance(v["why"], str) or not v["why"].strip():
 609 | +        raise ValueError("layout out of contract")
 610 | +    return {"layout": v["layout"], "people_on_screen": v["people_on_screen"], "why": v["why"].strip()[:300]}
 611 | +
 612 | +
 613 | +def _load_json(path):
 614 | +    try:
 615 | +        with open(path) as f:
 616 | +            d = json.load(f)
 617 | +        return d if isinstance(d, dict) else {}
 618 | +    except (OSError, ValueError):
 619 | +        return {}
 620 | +
 621 | +
 622 | +def layout_for(router, m, vrec, cache_path=None, seed=7):
 623 | +    """RULING 92's visual half: the source's layout, judged on the clip's own contact sheet (the visual check's, ruling
 624 | +    70: the same bytes it judged) with LAYOUT_PROMPT, by the visual_check role (one call, cached by the moment, the
 625 | +    sheet's sha256 and the prompt's version). -> {"measured", "layout", "people_on_screen", "why", "backend",
 626 | +    "replayed"} or {"measured": False, "why"}: never a pass unmeasured."""
 627 | +    import providers as Pr
 628 | +    from story_semantics import quote_data
 629 | +    sheet = (vrec or {}).get("sheet") or {}
 630 | +    path, sha = sheet.get("path"), sheet.get("sha256")
 631 | +    if not (vrec or {}).get("measured") or not path or not sha:
 632 | +        return {"measured": False, "why": "no judged contact sheet (the visual check is not measured)"}
 633 | +    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}"
 634 | +    hit = _load_json(cache_path).get(k) if cache_path else None
 635 | +    if isinstance(hit, dict) and hit.get("measured") is True:
 636 | +        return dict(hit, cached=True)
 637 | +    try:
 638 | +        with open(path, "rb") as f:
 639 | +            raw = f.read()
 640 | +    except OSError as e:
 641 | +        return {"measured": False, "why": f"the sheet cannot be read ({type(e).__name__})"}
 642 | +    if hashlib.sha256(raw).hexdigest() != sha:
 643 | +        return {"measured": False, "why": "the sheet on disk is not the one the visual check judged"}
 644 | +    prompt = {"text": LAYOUT_PROMPT.format(n=len(sheet.get("times") or []),
 645 | +                                           text=quote_data(m.get("text") or "", 700).replace('"', "'")),
 646 | +              "images": [base64.b64encode(raw).decode()]}
 647 | +    r = None
 648 | +    try:
 649 | +        r = router.call("visual_check", prompt, 600, seed)
 650 | +        v = parse_layout(r.text)
 651 | +    except Exception as e:                             # noqa: BLE001  no verdict: never a pass (law L-m)
 652 | +        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
 653 | +            router.reject(r)
 654 | +        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 655 | +    rec = dict(v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
 656 | +               version=LAYOUT_VERSION, sheet_sha256=sha)
 657 | +    if cache_path and not rec["replayed"]:
 658 | +        with LAYOUT_LOCK:
 659 | +            c = _load_json(cache_path)
 660 | +            c[k] = rec
 661 | +            with open(cache_path + ".tmp", "w") as f:
 662 | +                json.dump(c, f, indent=1)
 663 | +            os.replace(cache_path + ".tmp", cache_path)
 664 | +    return rec
 665 | +
 666 | +
 667 | +def alone_score(m):
 668 | +    """The ALONE scorer's rating of the moment's CURRENT text (package.verdict_of: the integrator's verdicts of the
 669 | +    render's own scorer, rulings 56 / 60), or None when it has none yet."""
 670 | +    v = P.verdict_of(m)
 671 | +    return float(v["score"]) if v is not None else None
 672 | +
 673 | +
 674 | +def _published_ts(m):
 675 | +    """The moment's publish time as a UTC timestamp; an unreadable one sorts as the oldest."""
 676 | +    from datetime import datetime, timezone
 677 | +    z = P.utc_z(m.get("published_at"))
 678 | +    return datetime.strptime(z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if z else float("-inf")
 679 | +
 680 | +
 681 | +def rank_key(m):
 682 | +    """Best first: the hook's own-job rating, the ALONE rating, the hook's parts, the miner's score, the newest
 683 | +    source, then the id (a total order)."""
 684 | +    hr = m.get("hook_rating") or {}
 685 | +    return (-((P.hook_own(m) or {}).get("rating") or 0), -(alone_score(m) or 0.0),
 686 | +            -sum(hr.get(k) or 0 for k in P.HOOK_PARTS), -float(m.get("rank_score") or 0.0), -_published_ts(m),
 687 | +            m["moment_id"])
 688 | +
 689 | +
 690 | +WRITE_SPOT = """You are PBX MAX, the host of a short Bitcoin video that SPOTLIGHTS one clip of another channel's own
 691 | +words. The clip plays alone, in full; then a sign-off credits the channel (written by code).
 692 | +
 693 | +{note}
 694 | +{clip}
 695 | +
 696 | +Write:
 697 | +- "title": ONE title of at most 8 words (and at most 70 characters) that says what the clip is about.
 698 | +- "caption": ONE caption (at most 220 characters).
 699 | +- "comment": the first comment under the video, as PBX writes them: one or two short casual lines about THIS clip in
 700 | +  plain words; not preachy; no emoji, no hashtags, no handles, no links and no credits (code adds the credits).
 701 | +- "closing": a CANDIDATE closing line the host speaks right after the clip, at most {cmax} words, as your OWN
 702 | +  commentary. It is kept ONLY if it says something the clip does not already say: it never restates, summarises or
 703 | +  cheers the clip, and a viewer would miss it if it were cut. When you have nothing to add, give null: the clip then
 704 | +  goes straight to the sign-off, which is the default. {said}
 705 | +Every line gives "cites": the clip's id when it relies on the clip (none for your own commentary).
 706 | +RULES (a line that breaks one is rejected):
 707 | +- NEVER restate the clip's claim, and never repeat its words: the clip says it, in its own words.
 708 | +- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
 709 | +  or company; never what the speaker thinks; no prediction of what will happen; no advice or instruction to the viewer
 710 | +  (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
 711 | +- Say what the speaker says or thinks ONLY when the clip is marked VERIFIED, by that name, with the clip's own hedge:
 712 | +  "thinks" for "I think", "feels" for "I feel like", "says" only for a flat statement. Otherwise credit the SHOW only
 713 | +  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
 714 | +- No price level; no advice to buy, sell or use leverage; no quotes except the clip's exact words; no "destroys",
 715 | +  "slams", "exposes", "admits", "confirms", "caught".
 716 | +- A line that names a show, a person or Bitcoin's price cites the clip.
 717 | +{style}
 718 | +{extra}Return ONLY this JSON object: {{"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}},
 719 | +"comment": {{"text": "...", "cites": []}}, "closing": {{"text": "...", "cites": []}} or null}}"""
 720 | +
 721 | +VALUE_PROMPT = """You judge ONE line a host would speak right after a clip in a short video. The clip plays first,
 722 | +alone and in full; then the host's line; then a sign-off credits the channel.
 723 | +{note}
 724 | +CLIP (on {show}): "{clip}"
 725 | +LINE: "{line}"
 726 | +Answer each question "yes" or "no". Anything you cannot answer with a clear yes is "no".
 727 | +- "adds": does the line say something the clip does not already say?
 728 | +- "no_restate": does the line avoid restating, summarising or cheering the clip?
 729 | +- "missed": would a viewer miss the line if it were cut?
 730 | +- "short": is the line 12 words or fewer?
 731 | +Return ONLY this JSON object: {{"adds": "yes" | "no", "no_restate": "yes" | "no", "missed": "yes" | "no", "short":
 732 | +"yes" | "no", "why": "<one sentence>"}}"""
 733 | +
 734 | +
 735 | +def parse_write(text, mid, closing_allowed=True):
 736 | +    """One write in contract -> {"title", "caption", "comment", "closing"} (closing None or a line), or ValueError."""
 737 | +    obj = json.loads(text.strip())
 738 | +    keys = {"title", "caption", "comment", "closing"}
 739 | +    if not isinstance(obj, dict) or set(obj) != keys:
 740 | +        raise ValueError(f"keys must be exactly {sorted(keys)}")
 741 | +    out = {}
 742 | +    for slot in ("title", "caption", "comment", "closing"):
 743 | +        ln = obj[slot]
 744 | +        if slot == "closing" and (ln is None or not closing_allowed):
 745 | +            out[slot] = None
 746 | +            continue
 747 | +        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 748 | +                not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 749 | +                any(not isinstance(c, str) or c != mid for c in ln["cites"]):
 750 | +            raise ValueError(f"{slot}: needs text and cites from the clip's id")
 751 | +        out[slot] = {"text": ln["text"].strip(), "cites": list(dict.fromkeys(ln["cites"]))}
 752 | +    if len(out["title"]["text"]) > 70 or len(out["caption"]["text"]) > 220:
 753 | +        raise ValueError("title <= 70 characters, caption <= 220")
 754 | +    return out
 755 | +
 756 | +
 757 | +def parse_value(text):
 758 | +    """Ruling 91's value verdict in contract -> {"adds", "no_restate", "missed", "short", "why"}, or ValueError."""
 759 | +    v = json.loads(text.strip())
 760 | +    if not isinstance(v, dict) or set(v) != set(VALUE_KEYS) | {"why"}:
 761 | +        raise ValueError(f"keys must be exactly {sorted(set(VALUE_KEYS) | {'why'})}")
 762 | +    if any(v[k] not in ("yes", "no") for k in VALUE_KEYS) or not isinstance(v["why"], str):
 763 | +        raise ValueError("each answer is 'yes' or 'no', with a reason")
 764 | +    return {**{k: v[k] for k in VALUE_KEYS}, "why": v["why"].strip()[:300]}
 765 | +
 766 | +
 767 | +def value_verdict(router, m, line, show, writers_v, writers_f, seed=7):
 768 | +    """RULING 91: ONE value verdict on the candidate closing line, off the writer's vendor and family (the
 769 | +    coherence_verdict role). ok only when all four answers are "yes" AND the line counts at most CLOSING_MAX_WORDS
 770 | +    words in code; an unavailable or out-of-contract answer is no verdict, so no line (never re-asked: "one write, one
 771 | +    verdict")."""
 772 | +    import providers as Pr
 773 | +    from select_by_id import UNTRUSTED
 774 | +    from story_semantics import quote_data
 775 | +    prompt = VALUE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), show=quote_data(show, 80),
 776 | +                                 clip=quote_data(m["text"], 1200).replace('"', "'"),
 777 | +                                 line=quote_data(line, 200).replace('"', "'"))
 778 | +    r = None
 779 | +    try:
 780 | +        r = router.call("coherence_verdict", prompt, 400, seed, avoid_vendor=writers_v, avoid_family=writers_f)
 781 | +        v = parse_value(r.text)
 782 | +    except Exception as e:                             # noqa: BLE001  no verdict: no line (ruling 91)
 783 | +        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
 784 | +            router.reject(r)
 785 | +        return {"measured": False, "ok": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 786 | +    words = len(line.split())
 787 | +    return dict(v, measured=True, ok=all(v[k] == "yes" for k in VALUE_KEYS) and words <= CLOSING_MAX_WORDS,
 788 | +                words=words, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 789 | +
 790 | +
 791 | +def style_lint(lines):
 792 | +    """PBX's house style on a spotlight's lines: the title and caption rules (house_style.lint); the closing line by
 793 | +    the takeaway's rules and at most CLOSING_MAX_WORDS words; the comment by the rules every surface keeps (no hashtag,
 794 | +    dash, emoji, hedge or AI phrasing), at most COMMENT_MAX_LINES lines and COMMENT_MAX_WORDS words, and no handle, link
 795 | +    or credit (code adds the credits)."""
 796 | +    out = []
 797 | +    for ln in lines:
 798 | +        slot, text = ln["slot"], ln.get("text") or ""
 799 | +        if slot in ("title", "caption"):
 800 | +            out += HS.lint(slot, text)
 801 | +        elif slot == "closing":
 802 | +            out += [dict(v, slot="closing") for v in HS.lint("takeaway", text)]
 803 | +            if len(text.split()) > CLOSING_MAX_WORDS:
 804 | +                out.append({"slot": "closing", "rule": "STYLE",
 805 | +                            "detail": f"closing-words: {len(text.split())} words (at most {CLOSING_MAX_WORDS})"})
 806 | +        elif slot == "comment":
 807 | +            out += [dict(v, slot="comment") for v in HS.lint("bridge", text)]   # the every-surface rules only
 808 | +            n_lines = len([x for x in text.split("\n") if x.strip()])
 809 | +            if n_lines > COMMENT_MAX_LINES:
 810 | +                out.append({"slot": "comment", "rule": "STYLE",
 811 | +                            "detail": f"comment-lines: {n_lines} lines (at most {COMMENT_MAX_LINES})"})
 812 | +            if HS.words(text) > COMMENT_MAX_WORDS:
 813 | +                out.append({"slot": "comment", "rule": "STYLE",
 814 | +                            "detail": f"comment-words: {HS.words(text)} words (at most {COMMENT_MAX_WORDS})"})
 815 | +            if re.search(r"@|https?://|www\.|\bcredits?\b", text, re.I):
 816 | +                out.append({"slot": "comment", "rule": "STYLE",
 817 | +                            "detail": "comment-credits: no handle, link or credit (code adds them)"})
 818 | +    return out
 819 | +
 820 | +
 821 | +def credits(channel, speaker, table_path=HANDLES):
 822 | +    """RULING 90: the first comment's credits: the channel's X handle and the attested speaker's, ONLY from the
 823 | +    verified table (the integrator's registry: x_handle, an empty one is none). The speaker has a handle only when the
 824 | +    attested name is itself a registry channel (no speaker-level table exists: the integrator, 22:44 ET); a name
 825 | +    without a verified handle stays UNTAGGED, and the record says so. -> {"tags", "channel", "speaker"}."""
 826 | +    try:
 827 | +        with open(table_path) as f:
 828 | +            reg = json.load(f)
 829 | +        rows = reg if isinstance(reg, list) else []
 830 | +    except (OSError, ValueError):
 831 | +        rows = []
 832 | +    def handle_of(name):
 833 | +        for r in rows:
 834 | +            names = [r.get("display_name")] + list(r.get("aliases") or [])
 835 | +            if isinstance(r, dict) and name in [x for x in names if isinstance(x, str)]:
 836 | +                h = r.get("x_handle")
 837 | +                return (h, None) if isinstance(h, str) and HANDLE_RE.match(h) else \
 838 | +                    (None, "the registry has no verified X handle for it")
 839 | +        return None, "not in the verified table" if rows else "the verified table cannot be read"
 840 | +    h, why = handle_of(channel)
 841 | +    out = {"channel": {"name": channel, "handle": h, "untagged_why": why}, "speaker": None}
 842 | +    tags = [h or channel]
 843 | +    sp = speaker if isinstance(speaker, dict) and speaker.get("measured") is True and \
 844 | +        isinstance(speaker.get("name"), str) and speaker["name"] not in ("", "unknown") else None
 845 | +    if sp is not None and sp["name"] != channel:
 846 | +        hs, why_s = handle_of(sp["name"])
 847 | +        out["speaker"] = {"name": sp["name"], "handle": hs, "untagged_why": why_s}
 848 | +        if (hs or sp["name"]) not in tags:
 849 | +            tags.append(hs or sp["name"])
 850 | +    elif sp is None:
 851 | +        out["speaker"] = {"name": None, "handle": None,
 852 | +                          "untagged_why": "no attested speaker (the speaker record names none): the channel only"}
 853 | +    out["tags"] = tags
 854 | +    return out
 855 | +
 856 | +
 857 | +def assemble(m, ctx, fields, closing):
 858 | +    """The spotlight package (ruling 90): ONE segment (label "hook"), no intro and no bridge, the closing line or none,
 859 | +    the sign-off with its one channel (package.signoff), the title, caption and comment as gated lines, the medley's
 860 | +    about-Bitcoin screen (ruling 34: the render judges with it), and the factory's runtime estimate with the closing
 861 | +    line counted."""
 862 | +    lines = ([dict(closing, slot="closing")] if closing else []) + \
 863 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption"),
 864 | +         dict(fields["comment"], slot="comment")]
 865 | +    vo = {"intro": None, "bridges": [], "bridges_after_clip": [], "closing": closing["text"] if closing else None}
 866 | +    pk = P._package([m], ctx, {"title": fields["title"], "caption": fields["caption"], "type": "moments",
 867 | +                               "angle": "", "style": "spotlight"}, "spotlight (ruling 90)", vo, lines)
 868 | +    pk["shape"] = "spotlight"
 869 | +    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}
 870 | +    pk["runtime_s_estimate"] = P.runtime([m], [vo["closing"]])
 871 | +    pk["runtime_note"] = (f"the moment {m['duration_s']:.2f} s (word timing)" +
 872 | +                          (f" + the closing line ({len(vo['closing'].split())} words at {P.R4_WPS} w/s + "
 873 | +                           f"{P.R4_PREROLL_S} s pre-roll)" if vo["closing"] else ", no closing line") +
 874 | +                          f" + tail {P.FINAL_TAIL_S} s (sign-off, credits card, outro, edges): the factory's estimate")
 875 | +    return pk
 876 | +
 877 | +
 878 | +def cheap(pk, a_by, levels, now):
 879 | +    """The free gates of a spotlight's lines -> (violations, det, dup, rt_ok, style): VO fidelity's deterministic rules,
 880 | +    DUPLICATE, the 28-50 s runtime, the house style and the recency facts the pin carries."""
 881 | +    segs_v = P.fidelity_segments(pk, a_by)
 882 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 883 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 884 | +    det = VF.check_deterministic(segs_v, lines, man, levels)
 885 | +    dup = P.duplicates(pk)
 886 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 887 | +    style = style_lint(pk["lines"])
 888 | +    v = det["violations"] + dup + style + \
 889 | +        ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail": f"{pk['runtime_s_estimate']} s outside "
 890 | +                                                                     f"{RUNTIME_S[0]:g}-{RUNTIME_S[1]:g} s"}]) + \
 891 | +        [{"slot": "-", "rule": "RECENCY", "detail": w} for w in PP.recency_problems(pk["segments"])]
 892 | +    return v, det, dup, rt_ok, style
 893 | +
 894 | +
 895 | +def _row(ok, by, replayed=False, measured=True, **extra):
 896 | +    return dict({"status": "NOT RUN" if not measured else ("PASS" if ok else "FAIL"), "by": by,
 897 | +                 "replayed": replayed if isinstance(replayed, bool) else None, "n": 1}, **extra)
 898 | +
 899 | +
 900 | +def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre, src_rec, facts, closing=None):
 901 | +    """The sealed gate inventory of a spotlight (package_pin.SPOTLIGHT_GATES, + CLOSING_GATES with a closing line):
 902 | +    package.inventory's rows that apply to one clip (its "r4" and "coherence" rows judge several clips and a medley's
 903 | +    VO: they are left out), then ruling 90-92's own rows. facts: {"never_delivered", "one_per_channel_day",
 904 | +    "window"} as the build measured them. closing: {"value", "fidelity", "context"} when a closing line ships."""
 905 | +    mid = m["moment_id"]
 906 | +    rows = P.inventory(fid, dup, rt_ok, (True, "n/a"), cx, {"hook": a_off}, {mid: exc}, {mid: truth}, False,
 907 | +                       {"measured": False}, style=style, hook=m.get("hook_onset"), stand=P.stand_alone_check([m]),
 908 | +                       visual=[m.get("visual")])
 909 | +    rows.pop("r4", None)
 910 | +    rows.pop("coherence", None)
 911 | +    v = m.get("visual") or {}
 912 | +    rows["visual"] = _row(v.get("measured") is True and not v.get("flags"), v.get("backend"), v.get("replayed"),
 913 | +                          measured=v.get("measured") is True, flags=list(v.get("flags") or []),
 914 | +                          by_rule="ruling 90: the visual check clean (no flag; ruling 70's sheet)")
 915 | +    own, hr = P.hook_own(m), m.get("hook_rating") or {}
 916 | +    rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 917 | +                            bool(hr.get("replayed", False)), measured=own is not None,
 918 | +                            rating=(own or {}).get("rating"), scroll=hr.get("scroll"), alone=hr.get("alone"),
 919 | +                            why=hr.get("why"), min=HOOK_MIN, rule="ruling 90: >= 4 on the hook's own job (ruling 61)")
 920 | +    sv = P.verdict_of(m)
 921 | +    rows["stands_alone"] = _row(sv is not None and float(sv["score"]) >= ALONE_MIN,
 922 | +                                f"the ALONE scorer ({(sv or {}).get('model')}, the render's stand_alone scorer as the "
 923 | +                                f"integrator's pin-stage service gave it, rulings 56 / 60)", False,
 924 | +                                measured=sv is not None, score=(sv or {}).get("score"), reason=(sv or {}).get("reason"),
 925 | +                                text_sha256=(sv or {}).get("text_sha256"), min=ALONE_MIN)
 926 | +    fams = [a.get("backend") for a in a_two or []]
 927 | +    rows["step_a_two_families"] = _row(len(a_two or []) == 2 and not any(CI.a_failures(a) for a in a_two),
 928 | +                                       fams, None if any(not isinstance(a.get("replayed"), bool) for a in a_two or [])
 929 | +                                       else any(a.get("replayed") for a in a_two or []),
 930 | +                                       measured=len(a_two or []) == 2,
 931 | +                                       rule="ruling 90: step A from both families as routed (package.second_screen)")
 932 | +    rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 933 | +                                    bool((src_rec.get("layout") or {}).get("replayed", False)),
 934 | +                                    measured=(src_rec.get("layout") or {}).get("measured") is True,
 935 | +                                    why=src_rec.get("why"), turns=src_rec.get("turns"), layout=src_rec.get("layout"),
 936 | +                                    rule="ruling 92: conversation, not reaction (caption turns + the layout)")
 937 | +    rows["window_12h"] = _row(not PP.window_problems(pk["segments"], facts["now"]),
 938 | +                              "code (package_pin.window_problems, ruling 76: <= 12 h on the render clock)",
 939 | +                              why=PP.window_problems(pk["segments"], facts["now"]))
 940 | +    rows["never_delivered"] = _row(facts["never_delivered"] is True,
 941 | +                                   "code (package.usable: no delivered span overlapped, not the same speech, ruling 76 b)",
 942 | +                                   measured=isinstance(facts["never_delivered"], bool))
 943 | +    rows["one_per_channel_day"] = _row(facts["one_per_channel_day"] is True,
 944 | +                                       f"code (the spotlights record: no spotlight from this channel on {facts['day']} ET)",
 945 | +                                       measured=isinstance(facts["one_per_channel_day"], bool))
 946 | +    rows["precheck"] = _row(bool((pre or {}).get("ok")), "lock_precheck (the render's own lock: rulings 17 / 68 / 72 / "
 947 | +                                                         "73 / 84)", False, measured=pre is not None and
 948 | +                            not (pre or {}).get("error"),
 949 | +                            verdicts=[s.get("verdict") for s in (pre or {}).get("segments") or []
 950 | +                                      if isinstance(s, dict)])
 951 | +    if closing is not None:
 952 | +        val, cf, cc = closing["value"], closing["fidelity"], closing["context"]
 953 | +        rows["closing_value"] = _row(val.get("ok") is True, val.get("backend"), bool(val.get("replayed", False)),
 954 | +                                     measured=val.get("measured") is True,
 955 | +                                     answers={k: val.get(k) for k in VALUE_KEYS}, why=val.get("why"),
 956 | +                                     words=val.get("words"), rule="ruling 91: all four a clear yes")
 957 | +        rows["closing_fidelity"] = _row(cf.get("ok") is True, cf.get("backend"), bool(cf.get("replayed", False)),
 958 | +                                        measured=bool(cf.get("measured")),
 959 | +                                        violations=[f"{x['slot']}: {x['rule']}" for x in cf.get("violations") or []])
 960 | +        rows["closing_context"] = _row(cc.get("ok") is True, cc.get("backends"), cc.get("replayed"),
 961 | +                                       measured=bool(cc.get("measured")),
 962 | +                                       violations=[x.get("rule") for x in cc.get("violations") or []])
 963 | +    return rows
 964 | +
 965 | +
 966 | +STAGES = ("step A", "the second recognition pass and CUTTABLE", "opens cold (G17a, the hook rules)",
 967 | +          "the hook's own job >= 4", "the visual check clean", "step A from the second family", "the ALONE scorer >= 4",
 968 | +          "ruling 92's source test", "exclusion, the pre-check and the package")
 969 | +
 970 | +
 971 | +def near(rec, k=3):
 972 | +    """The k moments that got furthest (ruling 92's 'three nearest and their ratings'): by the last stage passed, then
 973 | +    the hook's own-job rating, then the ALONE rating."""
 974 | +    rows = sorted(rec.items(), key=lambda kv: (-kv[1].get("stage", 0), -(kv[1].get("hook_own") or 0),
 975 | +                                               -(kv[1].get("alone") or 0), kv[0]))
 976 | +    return [dict(v, moment_id=mid, passed=list(STAGES[:v.get("stage", 0)])) for mid, v in rows[:k]]
 977 | +
 978 | +
 979 | +def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, work_dir=None, store=None,
 980 | +          step_a_cache=None, hook_cache=None, scorer_verdicts_path=None, visual_cache=None, layout_cache=None,
 981 | +          lock_check=None, spotlit=(), handles_path=HANDLES, wait_s=SCORER_WAIT_S, sleep=time.sleep,
 982 | +          captions_for=None, finalists=FINALISTS, attribute=None):
 983 | +    """RULINGS 90-92: the best spotlight in the pool, or none -> {"package", "pool", "moments" (each moment's furthest
 984 | +    stage and why it stopped), "finalists", "near", "why_none", ...}. The stages run cheapest first, each on what the
 985 | +    one before passed; every verdict is the medley's own and cached or recorded across builds: step A
 986 | +    (package.prescreen), L-v 2 and CUTTABLE (truth_for), G17a (hook_onset_for), the render's hook rules and the hook's
 987 | +    own-job rating (package._can_open, hook_ratings: >= HOOK_MIN), the visual check clean (visual_pin: measured, no
 988 | +    flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 989 | +    (a moment with no rating yet waits up to wait_s for the integrator's pass, polling the verdicts file), ruling 92's
 990 | +    source test; then, best first (rank_key), up to `finalists` moments: the exclusion verdict, the render's lock
 991 | +    pre-check (lock_check; no verdict stops the search, as in a medley build) and package_for(). lock_check None: no
 992 | +    pin (fail closed). spotlit: load_spotlit()'s list (None: not measured, no spotlight). attribute: the speaker
 993 | +    attribution (default speakers.attribute_package)."""
 994 | +    import lock_precheck as LP
 995 | +    import visual_pin as VP
 996 | +    t0 = time.time()
 997 | +    out = {"shape": "spotlight", "package": None, "moments": {}, "finalists": [], "near": [], "why_none": None}
 998 | +    if not work_dir:
 999 | +        out["why_none"] = "no work_dir: L-v 2's second pass cannot run (fail closed)"
1000 | +        return out
1001 | +    ms, why = pool(moments, sources, ctx, delivered, optout, spotlit, captions_for)
1002 | +    out["pool"] = {"may": len(ms), "out": why,
1003 | +                   "snapped": {m["moment_id"]: m["spotlight_snap"] for m in ms if m.get("spotlight_snap")}}
1004 | +    log(f"  SPOTLIGHT (rulings 90-92): {len(ms)} moment(s) may be one ({len(out['pool']['snapped'])} snapped outward "
1005 | +        f"to {SNAP_TO_S:g} s), {len(why)} out before any verdict")
1006 | +    if not ms:
1007 | +        out["why_none"] = "no moment in the 12 h pool may be a spotlight before any verdict (stage 1)"
1008 | +        return out
1009 | +    rec = out["moments"]
1010 | +    for m in ms:
1011 | +        rec[m["moment_id"]] = {"channel": P._name(m, ctx), "video_id": m["video_id"], "seconds": m["duration_s"],
1012 | +                               "text": (m.get("text") or "")[:200], "stage": 0}
1013 | +
1014 | +    def stop(mid, why_):
1015 | +        rec[mid]["out"] = why_
1016 | +
1017 | +    def passed(mids, k):
1018 | +        for mid in mids:
1019 | +            rec[mid]["stage"] = max(rec[mid]["stage"], k)
1020 | +    idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha()) if scorer_verdicts_path else \
1021 | +        ({}, {"read": False, "why": "no verdicts file given"})
1022 | +    out["scorer"] = srec
1023 | +    ms = [P.with_verdict(m, idx) for m in ms]
1024 | +    wv, wf = P._writers(router)
1025 | +    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache)
1026 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
1027 | +    for m in ms:
1028 | +        if m["moment_id"] not in cleared:
1029 | +            stop(m["moment_id"], "step A: " + ("; ".join(fails.get(m["moment_id"]) or []) or "no verdict (law L-m)"))
1030 | +    passed(cleared, 1)
1031 | +    tru, hk = {}, {}
1032 | +    with ThreadPoolExecutor(max_workers=8) as ex:
1033 | +        futs = {mid: ex.submit(P.truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
1034 | +        got = {mid: f.result() for mid, f in futs.items()}
1035 | +    tru.update(got)
1036 | +    cut = {}
1037 | +    for mid, m in cleared.items():
1038 | +        t = tru.get(mid) or {}
1039 | +        if t.get("ok") and (t.get("edges") or {}).get("cuttable") is True:
1040 | +            cut[mid] = m
1041 | +        else:
1042 | +            stop(mid, "L-v 2 / CUTTABLE: " + ("NOT MEASURED: " + str(t["error"]) if t.get("error") else
1043 | +                                              "the second pass disagrees" if not t.get("ok") else
1044 | +                                              "not cuttable at an edge"))
1045 | +    passed(cut, 2)
1046 | +    openers = {}
1047 | +    for mid, m in cut.items():
1048 | +        m["hook_onset"] = P.hook_onset_for(m, sources, work_dir, hk)
1049 | +        m.pop("hook_rating", None)                       # a rating is this build's own (its cache's)
1050 | +        m.pop("visual_hook_block", None)
1051 | +        if P._can_open(m):
1052 | +            openers[mid] = m
1053 | +        else:
1054 | +            stop(mid, f"it cannot open cold: hook eligibility, G17a ({(m['hook_onset'] or {}).get('why')}) or the "
1055 | +                      f"render's hook rule")
1056 | +    passed(openers, 3)
1057 | +    rated, herr = P.hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
1058 | +        ({}, None)
1059 | +    strong = {}
1060 | +    for mid, m in openers.items():
1061 | +        m["hook_rating"] = rated.get(mid) or {"rating": None, "why": f"not rated: {herr}"}
1062 | +        own = P.hook_own(m)
1063 | +        rec[mid]["hook_own"] = (own or {}).get("rating")
1064 | +        if own is not None and own["rating"] >= HOOK_MIN:
1065 | +            strong[mid] = m
1066 | +        else:
1067 | +            stop(mid, f"the hook's own job rates {(own or {}).get('rating')} (needs {HOOK_MIN}): "
1068 | +                      f"{m['hook_rating'].get('why')}")
1069 | +    passed(strong, 4)
1070 | +    vcache = VP.load_cache(visual_cache) if visual_cache else {}
1071 | +    if strong:
1072 | +        with ThreadPoolExecutor(max_workers=4) as ex:
1073 | +            vis = list(ex.map(lambda m_: VP.visual_for(router, m_, work_dir, vcache), list(strong.values())))
1074 | +        for m, v in zip(list(strong.values()), vis):
1075 | +            m["visual"] = v
1076 | +        if visual_cache:
1077 | +            VP.save_cache(visual_cache, vcache)
1078 | +    clean = {}
1079 | +    for mid, m in strong.items():
1080 | +        v = m.get("visual") or {}
1081 | +        if v.get("measured") is True and not v.get("flags") and not VP.hook_block(v):
1082 | +            clean[mid] = m
1083 | +        else:
1084 | +            stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
1085 | +                                              f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
1086 | +    passed(clean, 5)
1087 | +    two, off_fail = P.second_screen(router, clean, a_by, sources, ctx, log=log, cache=step_a_cache) if clean else \
1088 | +        ({}, {})
1089 | +    both = {}
1090 | +    for mid, m in clean.items():
1091 | +        if mid in two:
1092 | +            both[mid] = m
1093 | +        else:
1094 | +            stop(mid, "step A from the second family: " + "; ".join(off_fail.get(mid) or ["no verdict (law L-m)"]))
1095 | +    passed(both, 6)
1096 | +    waited = 0.0
1097 | +    if both and scorer_verdicts_path and wait_s > 0 and \
1098 | +            not any((alone_score(m) or 0.0) >= ALONE_MIN for m in both.values()) and \
1099 | +            any(alone_score(m) is None for m in both.values()):
1100 | +        log(f"  SPOTLIGHT: {sum(alone_score(m) is None for m in both.values())} moment(s) wait for the ALONE scorer "
1101 | +            f"(the integrator's pass; up to {wait_s:.0f} s)")
1102 | +        t_w = time.time()
1103 | +        while time.time() - t_w < wait_s:
1104 | +            sleep(SCORER_POLL_S)
1105 | +            idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha())
1106 | +            both = {mid: P.with_verdict(m, idx) for mid, m in both.items()}
1107 | +            if all(alone_score(m) is not None for m in both.values()):
1108 | +                break
1109 | +        waited = time.time() - t_w
1110 | +        out["scorer"] = srec
1111 | +    out["scorer_waited_s"] = round(waited, 1)
1112 | +    fine = {}
1113 | +    for mid, m in both.items():
1114 | +        sc = alone_score(m)
1115 | +        rec[mid]["alone"] = sc
1116 | +        if sc is not None and sc >= ALONE_MIN:
1117 | +            fine[mid] = m
1118 | +        else:
1119 | +            stop(mid, f"the ALONE scorer: {sc if sc is not None else 'no rating yet'} (needs {ALONE_MIN:g})" +
1120 | +                 (f": {(P.verdict_of(m) or {}).get('reason')}" if sc is not None else
1121 | +                  " (asked with the build's scorer candidates)"))
1122 | +    passed(fine, 7)
1123 | +    ok_src = []
1124 | +    for mid, m in fine.items():
1125 | +        turns = episode_turns(m["video_id"], captions_for)
1126 | +        lay = layout_for(router, m, m.get("visual"), layout_cache)
1127 | +        ok, w = source_test(turns, lay)
1128 | +        m["spotlight_source"] = {"ok": ok, "why": w, "turns": turns, "layout": lay}
1129 | +        rec[mid]["source"] = w
1130 | +        if ok:
1131 | +            ok_src.append(m)
1132 | +        else:
1133 | +            stop(mid, f"ruling 92: {w}")
1134 | +    passed([m["moment_id"] for m in ok_src], 8)
1135 | +    ranked = sorted(ok_src, key=rank_key)
1136 | +    out["finalists"] = [m["moment_id"] for m in ranked]
1137 | +    log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
1138 | +        f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
1139 | +        f"{ALONE_MIN:g}, {len(ranked)} from a conversation ({time.time() - t0:.0f} s)")
1140 | +    exc_cache = {}
1141 | +    for m in ranked[:finalists]:
1142 | +        mid = m["moment_id"]
1143 | +        exc = P.exclusion_for(router, m, sources, exc_cache)
1144 | +        if exc.get("verdict") != "keep":
1145 | +            stop(mid, f"the exclusion verdict: {exc.get('verdict')} ({exc.get('why')})")
1146 | +            continue
1147 | +        if lock_check is None:
1148 | +            stop(mid, "no lock pre-check was given: never a pin (fail closed)")
1149 | +            continue
1150 | +        try:
1151 | +            pre = lock_check([m])
1152 | +        except Exception as e:                           # noqa: BLE001  no verdict, never a pass
1153 | +            pre = LP.failed(e)
1154 | +        if not pre.get("ok"):
1155 | +            stop(mid, f"rulings 68 / 72: the render's lock: {pre.get('error') or 'the clip holds'}"[:400])
1156 | +            if pre.get("error") or not pre.get("segments"):
1157 | +                out["lock_stop"] = rec[mid]["out"]       # no verdict: the search stops (as a medley build)
1158 | +                break
1159 | +            continue
1160 | +        facts = {"now": ctx.now, "day": et_day(ctx.now), "never_delivered": True,   # pool(): usable() with delivered
1161 | +                 "one_per_channel_day": spotlit is not None and m["channel_id"] not in
1162 | +                 {r["channel_id"] for r in spotlit or () if r.get("day_et") == et_day(ctx.now)}}
1163 | +        pk, why_p = package_for(router, m, ctx, sources, two[mid], tru[mid], exc, pre, facts, log=log,
1164 | +                                handles_path=handles_path, attribute=attribute)
1165 | +        if pk is not None:
1166 | +            pk["seconds"] = round(time.time() - t0, 1)
1167 | +            out["package"] = pk
1168 | +            rec[mid]["out"] = "PACKAGE"
1169 | +            break
1170 | +        stop(mid, why_p)
1171 | +    if out["package"] is None:
1172 | +        out["near"] = near(rec)
1173 | +        out["why_none"] = out.get("lock_stop") or ("no moment passes rulings 90-92 now" if not ranked else
1174 | +                                                   f"no finalist gave a package: " +
1175 | +                                                   "; ".join(f"{mid}: {rec[mid].get('out')}"
1176 | +                                                             for mid in out["finalists"][:finalists]))[:600]
1177 | +    return out
1178 | +
1179 | +
1180 | +def package_for(router, m, ctx, sources, a_two, truth, exc, pre, facts, log=print, handles_path=HANDLES,
1181 | +                attribute=None):
1182 | +    """The writes, the gates and the package for ONE moment -> (package, None) or (None, why).
1183 | +    - ONE write (angle_write): title, caption, comment and a candidate closing line. A title, caption or comment that
1184 | +      fails a free gate gets ONE more write of those lines (P._redo); the closing line is never written again
1185 | +      (ruling 91: one write, one verdict).
1186 | +    - Every verdict comes off every writer's vendor and family (law L-s); step A's verdict off them must exist (L-x).
1187 | +    - The lines without the closing: VO fidelity's verdict (vo_fidelity_verdict) and, when no closing ships, context
1188 | +      integrity (context_b / context_c).
1189 | +    - The closing line ships only when ALL hold: it passes the free gates with the package (house style, <= 12 words,
1190 | +      DUPLICATE, the runtime still 28-50 s), ruling 91's value verdict is a clear yes on all four, its own fidelity
1191 | +      verdict passes, and context integrity passes with it spoken after the clip. Otherwise no line (the default).
1192 | +    - Then the speaker record (sealed), the credits and the first comment (code), the lock's adopted text (LP.apply),
1193 | +      and the inventory, every required row exactly PASS (package_pin.gate_problems)."""
1194 | +    import lock_precheck as LP
1195 | +    import providers as Pr
1196 | +    import speakers as SP
1197 | +    from select_by_id import UNTRUSTED
1198 | +    mid = m["moment_id"]
1199 | +    show = P._name(m, ctx)
1200 | +    levels = P.current_levels(sources.values(), ctx)
1201 | +    clip = P._lineup_block([m], ctx, {mid: a_two[0]}).replace("HOOK id=", "CLIP id=", 1)
1202 | +    replies, notes, fields, closing0, extra = [], [], None, None, ""
1203 | +    for w in range(WRITES):
1204 | +        r = None
1205 | +        prompt = WRITE_SPOT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), clip=clip,
1206 | +                                   cmax=CLOSING_MAX_WORDS, said=CLOSING_SAID, style=HS.PROMPT_RULES,
1207 | +                                   extra=(extra + "\n") if extra else "")
1208 | +        try:
1209 | +            r = router.call("angle_write", prompt, 1500, 7 + w, deadline_s=P.WRITER_DEADLINE_S)
1210 | +            got = parse_write(r.text, mid, closing_allowed=(w == 0))
1211 | +        except (Pr.ProviderError, Pr.SpendLimit) as e:
1212 | +            return None, f"no writer answered ({type(e).__name__}: {str(e)[:200]})"
1213 | +        except (ValueError, TypeError, KeyError) as e:
1214 | +            if r is not None:
1215 | +                router.reject(r)
1216 | +            notes.append({"write": w + 1, "error": f"{type(e).__name__}: {str(e)[:200]}"})
1217 | +            extra = f"Your previous reply was REJECTED as out of contract ({str(e)[:200]}). Return the JSON exactly."
1218 | +            continue
1219 | +        replies.append(r)
1220 | +        if w == 0:
1221 | +            closing0 = got["closing"]
1222 | +        fields = {k: got[k] for k in ("title", "caption", "comment")}
1223 | +        wv_, wf_ = {x.vendor for x in replies}, {x.family for x in replies}
1224 | +        a_off = next((a for a in a_two for b in [router.backends.get(a.get("backend"))]
1225 | +                      if b is not None and b.vendor not in wv_ and b.family not in wf_), None)
1226 | +        if a_off is None:
1227 | +            return None, (f"no step-A verdict off the writers {sorted(wv_)} / {sorted(wf_)} (L-x): "
1228 | +                          f"{[a.get('backend') for a in a_two]}")
1229 | +        pk0 = assemble(m, ctx, fields, None)
1230 | +        v0 = cheap(pk0, {mid: a_off}, levels, ctx.now)[0]
1231 | +        notes.append({"write": w + 1, "backend": r.backend, "fields": fields, "closing": closing0 if w == 0 else None,
1232 | +                      "cheap": v0})
1233 | +        if not v0:
1234 | +            break
1235 | +        fields, extra = None, P._redo(v0)
1236 | +    if fields is None:
1237 | +        return None, "the title, caption or comment failed the free gates in both writes: " + \
1238 | +            "; ".join(f"{v['slot']}: {v['rule']}" for v in (notes[-1].get("cheap") or []))[:400] if notes else \
1239 | +            "no write in contract"
1240 | +    writers_v, writers_f = {x.vendor for x in replies}, {x.family for x in replies}
1241 | +    a_lab = {"hook": a_off}
1242 | +    segs_v = P.fidelity_segments(pk0, {mid: a_off})
1243 | +    man = {"channels": [show], "date": ctx.now.strftime("%Y-%m-%d")}
1244 | +    line = lambda pk_, slots: [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk_["lines"]
1245 | +                               if x["slot"] in slots]
1246 | +    spoken_after = lambda pk_: dict(pk_, vo=dict(pk_["vo"], intro=pk_["vo"]["closing"], bridges=[],
1247 | +                                                 bridges_after_clip=[]))   # CI reads the line after the clip there
1248 | +    closing_rec, cl_why, pk1 = None, "no candidate (the writer gave none)", None
1249 | +    with ThreadPoolExecutor(max_workers=6) as ex:
1250 | +        f_fid = ex.submit(VF.check, router, segs_v, line(pk0, ("title", "caption", "comment")), writers_v, 7, man,
1251 | +                          levels, writers_f)
1252 | +        if closing0 is not None:
1253 | +            pk1 = assemble(m, ctx, fields, closing0)
1254 | +            v1 = cheap(pk1, {mid: a_off}, levels, ctx.now)[0]
1255 | +            if v1:
1256 | +                cl_why, pk1 = "the free gates: " + "; ".join(f"{v['slot']}: {v['rule']}: {v['detail']}"
1257 | +                                                             for v in v1)[:300], None
1258 | +            else:
1259 | +                f_val = ex.submit(value_verdict, router, m, closing0["text"], show, writers_v, writers_f)
1260 | +                f_cf = ex.submit(VF.check, router, segs_v, line(pk1, ("closing",)), writers_v, 7, man, levels,
1261 | +                                 writers_f)
1262 | +                f_cc = ex.submit(CI.check_contexts, router, spoken_after(pk1),
1263 | +                                 CI.contexts_from_sources(pk1, sources, ctx.now), writers_v, 7, a_lab, writers_f, True)
1264 | +                val, cf, cc = f_val.result(), f_cf.result(), f_cc.result()
1265 | +                closing_rec = {"value": val, "fidelity": cf, "context": cc}
1266 | +                if not (val.get("ok") and cf.get("ok") and cf.get("measured") and cc.get("ok") and cc.get("measured")):
1267 | +                    cl_why = ("ruling 91's value verdict: " + str(val.get("why")) if not val.get("ok") else
1268 | +                              "its fidelity verdict: " + "; ".join(f"{x['rule']}" for x in cf.get("violations") or [])
1269 | +                              if not (cf.get("ok") and cf.get("measured")) else
1270 | +                              "context integrity with it: " + "; ".join(str(x.get("rule"))
1271 | +                                                                         for x in cc.get("violations") or []))[:300]
1272 | +                    pk1 = None
1273 | +        fid = f_fid.result()
1274 | +    if not (fid.get("ok") and fid.get("measured")):
1275 | +        return None, "VO fidelity's verdict on the title, caption or comment: " + \
1276 | +            "; ".join(f"{x['slot']}: {x['rule']}" for x in fid.get("violations") or [])[:300]
1277 | +    if pk1 is not None:
1278 | +        pk, cx = pk1, closing_rec["context"]
1279 | +    else:
1280 | +        pk = pk0
1281 | +        cx = CI.check_contexts(router, pk0, CI.contexts_from_sources(pk0, sources, ctx.now), writers_v, 7, a_lab,
1282 | +                               writers_f, True)
1283 | +        closing_rec = None
1284 | +        if not (cx.get("ok") and cx.get("measured")):
1285 | +            return None, "context integrity: " + "; ".join(str(x.get("rule")) for x in cx.get("violations") or [])[:300]
1286 | +    v_all, det, dup, rt_ok, style = cheap(pk, {mid: a_off}, levels, ctx.now)
1287 | +    (attribute or SP.attribute_package)(router, pk, sources, log=log)      # the speaker record, sealed (item 3)
1288 | +    cr = credits(show, pk["segments"][0].get("speaker"), handles_path)
1289 | +    pk["comment_credits"] = cr
1290 | +    pk["first_comment"] = PP.first_comment_text(fields["comment"]["text"], cr["tags"])
1291 | +    src_rec = m.get("spotlight_source") or {"ok": False, "why": "not measured"}
1292 | +    pk["spotlight"] = {"moment_id": mid, "snap": m.get("spotlight_snap"), "hook_own": P.hook_own(m),
1293 | +                       "alone": alone_score(m), "source": {k: src_rec.get(k) for k in ("ok", "why")},
1294 | +                       "closing": {"candidate": (closing0 or {}).get("text"), "kept": pk1 is not None,
1295 | +                                   "why_not": None if pk1 is not None else cl_why},
1296 | +                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes]}
1297 | +    pk["models"] = {"writer": [x.backend for x in replies], "fidelity_verdict": fid.get("backend"),
1298 | +                    "context": cx.get("backends"), "value": ((closing_rec or {}).get("value") or {}).get("backend"),
1299 | +                    "layout": (src_rec.get("layout") or {}).get("backend")}
1300 | +    pk["checks"] = {"fidelity": fid, "context": cx, "closing": closing_rec}
1301 | +    pk["gates"] = inventory(pk, m, dict(fid, deterministic=det), dup, rt_ok, style, cx, a_off, a_two, exc, truth,
1302 | +                            pre, src_rec, facts, closing=closing_rec if pk1 is not None else None)
1303 | +    #   (the deterministic row covers every line that ships, the closing line included: cheap() on the final package)
1304 | +    try:
1305 | +        pk = LP.apply(pk, pre)
1306 | +    except Exception as e:                               # noqa: BLE001  never a crash, never a pin
1307 | +        return None, f"rulings 68 / 72: {e}"[:400]
1308 | +    problems = PP.gate_problems(pk["gates"], PP.required_gates(pk)) + \
1309 | +        [f"{x}: the gated line differs from the one shipped" for x in PP.line_problems(pk)] + \
1310 | +        PP.spotlight_problems(pk) + [f"{v['slot']}: {v['rule']}" for v in v_all]
1311 | +    if problems:
1312 | +        return None, f"a required gate is not exactly PASS: {problems}"[:600]
1313 | +    log(f"  SPOTLIGHT PACKAGE: {mid} ({show}, {m['duration_s']} s" +
1314 | +        (f", snapped from {m['spotlight_snap']['from']}" if m.get("spotlight_snap") else "") +
1315 | +        f"), closing line: {pk['vo']['closing']!r}, runtime {pk['runtime_s_estimate']} s")
1316 | +    return pk, None
1317 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
1318 | index 1982ff9..1aba545 100644
1319 | --- a/tests/package/proof_ledger.py
1320 | +++ b/tests/package/proof_ledger.py
1321 | @@ -29,6 +29,12 @@ clips-alone verdict in that earlier build's record (its tried[N]; default the fi
1322 |  stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
1323 |  recordings and only what is missing is paid for; never re-lined, swapped or a new angle.
1324 |  
1325 | +RULING 90 (22:40 ET Nov 13; LAW since 22:52, with 91 and 92), THE SPOTLIGHT: after the medley search, every build
1326 | +tries one spotlight (pipeline/spotlight.py): built when the search ends with no medley, or for a moment no medley used
1327 | +(a sealed medley's clips are out of it). Its free pool goes to the clip scorer with the medley's own candidates at the
1328 | +build's start (package.build's scorer_extra). A sealed spotlight is SPOTLIGHT_PIN.json in the build's directory and a
1329 | +row of tests/package/proof/SPOTLIGHTS.json (one per channel per ET day).
1330 | +
1331 |  Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
1332 |                                               [--from-candidate BUILD_DIR[:N]]
1333 |    tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
1334 | @@ -58,9 +64,11 @@ import proof_ly as PL  # noqa: E402
1335 |  import proof_saved_runs as PS  # noqa: E402
1336 |  import providers as P  # noqa: E402
1337 |  import speakers as SP  # noqa: E402
1338 | +import spotlight as SPOT  # noqa: E402
1339 |  import lock_precheck as LP  # noqa: E402
1340 |  
1341 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
1342 | +SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
1343 |  
1344 |  
1345 |  def delivered_pins(paths):
1346 | @@ -187,7 +195,9 @@ def main(argv=None):
1347 |          f"starts at ${PL.LY_STOP_USD:.2f})")
1348 |      own, used = PL.meter(router), PL.reply_meter(router)
1349 |      t0 = time.time()
1350 | -    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say,
1351 | +    spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
1352 | +    sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
1353 | +    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
1354 |                work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
1355 |                spend=lambda: (own["est"], own["best"]),
1356 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
1357 | @@ -235,6 +245,18 @@ def main(argv=None):
1358 |              res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
1359 |                         why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
1360 |          res["candidate_tries"] = tries
1361 | +    # RULING 90: the spotlight after the medley search (the medley is always tried first): built when the search
1362 | +    # ends with no medley, or for a moment no medley used (a sealed medley's clips are out of it)
1363 | +    sp_delivered = delivered + ([{"video_id": sg["video_id"], "start": float(sg["start"]), "end": float(sg["end"]),
1364 | +                                  "pin": "this build's medley", "text": sg["text"]}
1365 | +                                 for sg in res["package"]["segments"]] if res.get("package") else [])
1366 | +    sp = SPOT.build(router, moments, sources, ctx, delivered=sp_delivered, optout=kw["optout"], log=say,
1367 | +                    work_dir=a.work_dir, store=kw["store"], step_a_cache=kw["step_a_cache"], hook_cache=kw["hook_cache"],
1368 | +                    scorer_verdicts_path=PK.SCORER_VERDICTS, visual_cache=kw["visual_cache"],
1369 | +                    layout_cache=os.path.join(HERE, "proof", "LAYOUT_CACHE.json"), lock_check=kw["lock_check"],
1370 | +                    spotlit=spotlit)
1371 | +    res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
1372 | +                                                "scorer_waited_s", "lock_stop", "scorer")}
1373 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
1374 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
1375 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
1376 | @@ -263,6 +285,33 @@ def main(argv=None):
1377 |              say(f"PIN REFUSED: {e}")
1378 |      else:
1379 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
1380 | +    if sp.get("package"):                                # RULING 90: the spotlight pin, its own file
1381 | +        try:
1382 | +            lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
1383 | +            if lock:
1384 | +                raise package_pin.PinRefused("; ".join(lock))
1385 | +            path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
1386 | +                                              name="SPOTLIGHT_PIN.json")
1387 | +            res["spotlight_pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1388 | +                                    "package_sha256": pin["moments_package"]["package_sha256"]}
1389 | +            import shutil                                # ruling 70: the segment's sheet beside the pin
1390 | +            sh = (pin["segments"][0].get("visual") or {}).get("sheet") or {}
1391 | +            if sh.get("name") and os.path.exists(os.path.join(a.work_dir, "visual", sh["name"])):
1392 | +                shutil.copyfile(os.path.join(a.work_dir, "visual", sh["name"]), os.path.join(out_dir, sh["name"]))
1393 | +            sg = sp["package"]["segments"][0]
1394 | +            SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
1395 | +                                             "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
1396 | +                                             "package_sha256": pin["moments_package"]["package_sha256"],
1397 | +                                             "at": now.isoformat(timespec="seconds"), "build": name})
1398 | +            say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
1399 | +                f"{sp['package']['vo']['closing']!r})")
1400 | +        except (package_pin.PinRefused, ValueError, OSError) as e:
1401 | +            res["spotlight_pin_refused"] = f"{type(e).__name__}: {e}"
1402 | +            say(f"SPOTLIGHT PIN REFUSED: {e}")
1403 | +    else:
1404 | +        say(f"no spotlight ({sp.get('why_none')})" + "".join(
1405 | +            f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
1406 | +            f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
1407 |      hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries;
1408 |      #   `moments` is the adapter's pool from LB.build_inputs, BEFORE usable() filters it (audit 1810 C3)
1409 |      res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
1410 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
1411 | index fcbcaa6..299098c 100644
1412 | --- a/tests/package/test_lock_precheck.py
1413 | +++ b/tests/package/test_lock_precheck.py
1414 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
1415 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
1416 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
1417 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
1418 | -                         "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")             # ruling 84's decoder
1419 | +                         "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")             # ruling 90's decoder
1420 |  
1421 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
1422 |          segs = LP.segments_of([HOOK, CLIP])
1423 | @@ -180,7 +180,7 @@ class TestCheck(Dirs):
1424 |              self.put(s, entry(s))
1425 |          rep, sleeps = self.run_check([HOOK, CLIP])
1426 |          self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
1427 | -        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")
1428 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")
1429 |  
1430 |      def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
1431 |          segs = LP.segments_of([HOOK, CLIP])
1432 | @@ -203,16 +203,16 @@ class TestCheck(Dirs):
1433 |          self.assertEqual(sleeps, [10.0, 10.0, 10.0])
1434 |  
1435 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
1436 | -        """Audit 1845 C2 (glm): ruling 73 changed the decoder, and ruling 84 changed it again; a file named for an
1437 | -        older decoder (25cd6f15e6c9, 8a101f222598) is never opened, even with a matching, newer entry under the current
1438 | -        rules."""
1439 | +        """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
1440 | +        integrator's spotlight branches) again; a file named for an older decoder (25cd6f15e6c9, 8a101f222598,
1441 | +        962353613cb0) is never opened, even with a matching, newer entry under the current rules."""
1442 |          s = LP.segments_of([HOOK])[0]
1443 | -        for dec in ("25cd6f15e6c9", "8a101f222598"):
1444 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0"):
1445 |              old = LP.result_file(s, self.res, decoder=dec)
1446 |              with open(old, "w") as f:
1447 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
1448 |              self.assertTrue(old.endswith(f".{dec}.json"))
1449 | -        self.assertIsNone(LP.answer(s, self.res))                                         # only 962353613cb0's file
1450 | +        self.assertIsNone(LP.answer(s, self.res))                                         # only c705b20ed800's file
1451 |  
1452 |      def test_ruling_73_holds_a_span_the_render_cannot_cut(self):
1453 |          segs = LP.segments_of([HOOK, CLIP])
1454 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
1455 | new file mode 100644
1456 | index 0000000..a4eb9c3
1457 | --- /dev/null
1458 | +++ b/tests/package/test_spotlight.py
1459 | @@ -0,0 +1,558 @@
1460 | +#!/usr/bin/env python3
1461 | +"""RULINGS 90-92 (orchestrator 22:40 / 22:52 ET Nov 13): the SPOTLIGHT pin kind, offline.
1462 | +
1463 | +- The pin contract agreed with the integrator (22:44 ET): shape "spotlight", one hook segment, edl_vo with "closing",
1464 | +  the whole first comment, the gate rows; the seal covers the closing line, the kind and the comment, and every pin
1465 | +  sealed before it recomputes (pin_seal, and the integrator's exact call).
1466 | +- The snap (ruling 32's, outward to the speaker's whole thought), ruling 92's source test, the writer's and the
1467 | +  value verdict's contracts, PBX's comment format and the verified handles, the pool's free rules.
1468 | +- package_for: the closing line ships only with every gate; any failure leaves no line (ruling 91).
1469 | +- build(): the stages in order, the ALONE scorer's wait, the nearest moments when none qualifies.
1470 | +"""
1471 | +import copy
1472 | +import glob
1473 | +import json
1474 | +import os
1475 | +import sys
1476 | +import unittest
1477 | +from datetime import timedelta
1478 | +from unittest import mock
1479 | +
1480 | +HERE = os.path.dirname(os.path.abspath(__file__))
1481 | +REPO = os.path.dirname(os.path.dirname(HERE))
1482 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1483 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1484 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1485 | +sys.path.insert(0, HERE)
1486 | +import eligibility as E  # noqa: E402
1487 | +import moments as M  # noqa: E402
1488 | +import package as PK  # noqa: E402
1489 | +import package_pin as PP  # noqa: E402
1490 | +import providers as P  # noqa: E402
1491 | +import spotlight as SPOT  # noqa: E402
1492 | +import visual_pin as VP  # noqa: E402
1493 | +from test_eligibility import NOW, REG, source  # noqa: E402
1494 | +from test_gates import Canned, a_item  # noqa: E402
1495 | +from test_medley import sv  # noqa: E402
1496 | +from test_moments import pm  # noqa: E402
1497 | +
1498 | +TEXT = ("Bitcoin is the one money nobody can print more of, and that is exactly why people keep holding it through "
1499 | +        "every single cycle we have seen so far, from the very first one to the one we are in right now today.")
1500 | +GOOD = {"title": {"text": "The money nobody can print", "cites": []},
1501 | +        "caption": {"text": "a clear case for a fixed supply.", "cites": []},
1502 | +        "comment": {"text": "This one stuck with me.\nWorth the full listen.", "cites": []},
1503 | +        "closing": {"text": "Scarcity only matters when nobody can quietly change it.", "cites": []}}
1504 | +
1505 | +
1506 | +class B:
1507 | +    def __init__(self, vendor, family):
1508 | +        self.vendor, self.family = vendor, family
1509 | +
1510 | +
1511 | +class Router(Canned):
1512 | +    """Canned answers by role, with the back-ends the step-A verdicts name."""
1513 | +    backends = {"fake:xai": B("xai", "grok"), "fake:heimdall": B("heimdall", "deepseek")}
1514 | +
1515 | +    def __init__(self, **answers):
1516 | +        super().__init__(**answers)
1517 | +        self.down = set()
1518 | +
1519 | +
1520 | +def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
1521 | +    m = pm(mid, channel, dur)
1522 | +    m.update(text=text, channel_name=channel, published_at=(NOW - timedelta(hours=2)).isoformat(),
1523 | +             hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
1524 | +             hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
1525 | +                          "backend": "fake:xai", "replayed": False},
1526 | +             visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
1527 | +                     "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
1528 | +                                      "finding": "none"}, "on_screen_text": [],
1529 | +                     "lower_third": {"name": None, "text": None}},
1530 | +             scorer_verdict=sv(text, 4.0),
1531 | +             spotlight_source={"ok": True, "why": "layout 'conversation'", "turns": {"measured": False},
1532 | +                               "layout": {"measured": True, "layout": "conversation", "backend": "fake:vis",
1533 | +                                          "replayed": False}})
1534 | +    m.update(kw)
1535 | +    return m
1536 | +
1537 | +
1538 | +def two():
1539 | +    return [dict(a_item("hook"), backend="fake:xai", replayed=False),
1540 | +            dict(a_item("hook"), backend="fake:heimdall", replayed=False)]
1541 | +
1542 | +
1543 | +def pre_of(m):
1544 | +    return {"ok": True, "request_id": "r1", "segments": [{"video_id": m["video_id"], "start": round(m["start"], 3),
1545 | +                                                          "end": round(m["end"], 3), "approved_text": m["text"],
1546 | +                                                          "role": "hook", "verdict": "pass", "outcome": "pass"}]}
1547 | +
1548 | +
1549 | +FID_OK = {"ok": True, "measured": True, "verdict": {"ok": True, "violations": []}, "violations": [],
1550 | +          "backend": "fake:verdict", "replayed": False, "deterministic": {"ok": True, "violations": []}}
1551 | +CX_OK = {"ok": True, "measured": True, "violations": [], "backends": {"B": "fake:b", "C": "fake:c"}, "replayed": False}
1552 | +VALUE_YES = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "it names what is at stake"}
1553 | +
1554 | +
1555 | +def unknown_speaker(router, pk, sources, log=print):
1556 | +    for s in pk["segments"]:
1557 | +        s["speaker"] = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test", "people": [],
1558 | +                        "measured": True}
1559 | +    return pk
1560 | +
1561 | +
1562 | +def package(m=None, value=VALUE_YES, write=GOOD, cx=CX_OK, cx_base=CX_OK, fid=FID_OK, cfid=FID_OK, writes=None):
1563 | +    """package_for on one moment with canned verdicts -> (pk, why, router, the context checks asked)."""
1564 | +    m = m or moment()
1565 | +    ctx = E.Context(NOW, REG)
1566 | +    router = Router(angle_write=writes or [write], coherence_verdict=[value])
1567 | +    asked = []
1568 | +
1569 | +    def ci(router_, pk, contexts, *a, **k):
1570 | +        asked.append(pk["vo"].get("intro"))
1571 | +        return copy.deepcopy(cx if pk["vo"].get("intro") else cx_base)
1572 | +    fids = []
1573 | +
1574 | +    def vf(router_, segs, lines, *a, **k):
1575 | +        fids.append([x["slot"] for x in lines])
1576 | +        return copy.deepcopy(cfid if [x["slot"] for x in lines] == ["closing"] else fid)
1577 | +    facts = {"now": NOW, "day": SPOT.et_day(NOW), "never_delivered": True, "one_per_channel_day": True}
1578 | +    with mock.patch.object(SPOT.VF, "check", vf), mock.patch.object(SPOT.CI, "check_contexts", ci), \
1579 | +            mock.patch.object(SPOT.CI, "contexts_from_sources", lambda pk, s, n: {}), \
1580 | +            mock.patch.object(SPOT.P, "current_levels", lambda *a, **k: []):
1581 | +        pk, why = SPOT.package_for(router, m, ctx, {}, two(), {"ok": True, "model": "fake:stt", "replayed": False,
1582 | +                                                               "edges": {"cuttable": True}},
1583 | +                                   {"verdict": "keep", "backend": "fake:excl", "replayed": False, "measured": True},
1584 | +                                   pre_of(m), facts, log=lambda *a: None, handles_path=HANDLES, attribute=unknown_speaker)
1585 | +    return pk, why, router, asked, fids
1586 | +
1587 | +
1588 | +HANDLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_spotlight_channels.json")
1589 | +
1590 | +
1591 | +def setUpModule():
1592 | +    with open(HANDLES, "w") as f:
1593 | +        json.dump([{"display_name": "DataDash", "x_handle": "@Nicholas_Merten", "aliases": []},
1594 | +                   {"display_name": "Natalie Brunell", "x_handle": "@natbrunell", "aliases": ["Natalie"]},
1595 | +                   {"display_name": "Simply Bitcoin", "x_handle": "", "aliases": []}], f)
1596 | +
1597 | +
1598 | +def tearDownModule():
1599 | +    if os.path.exists(HANDLES):
1600 | +        os.remove(HANDLES)
1601 | +
1602 | +
1603 | +class TestPinContract(unittest.TestCase):
1604 | +    def test_required_rows_with_and_without_a_closing_line(self):
1605 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": None}}), PP.SPOTLIGHT_GATES)
1606 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": "A line."}}),
1607 | +                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)
1608 | +        self.assertEqual(PP.required_gates({"shape": "spotlight", "edl_vo": {"closing": "A line."}}),   # a pin's
1609 | +                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)                                   # moments_package
1610 | +        self.assertEqual(PP.required_gates({"shape": "medley"}), PP.REQUIRED_GATES + PP.MEDLEY_GATES)
1611 | +        for g in ("spotlight_source", "hook_own", "stands_alone", "step_a_two_families", "visual", "window_12h",
1612 | +                  "never_delivered", "one_per_channel_day", "precheck"):          # the keys agreed at 22:44 ET
1613 | +            self.assertIn(g, PP.SPOTLIGHT_GATES)
1614 | +        self.assertEqual(PP.CLOSING_GATES, ("closing_value", "closing_fidelity", "closing_context"))
1615 | +
1616 | +    def test_every_pin_sealed_before_recomputes(self):
1617 | +        pins = [p for p in glob.glob(os.path.join(HERE, "proof", "*", "*.json"))
1618 | +                if os.path.basename(p).startswith("MOMENTS_PIN")]
1619 | +        self.assertGreater(len(pins), 5)
1620 | +        for p in pins:
1621 | +            with open(p) as f:
1622 | +                pin = json.load(f)
1623 | +            mp = pin.get("moments_package")
1624 | +            if not mp or "package_sha256" not in mp:
1625 | +                continue
1626 | +            self.assertEqual(PP.pin_seal(pin), mp["package_sha256"], p)
1627 | +            self.assertEqual(PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],   # the
1628 | +                                     mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"], p)
1629 | +
1630 | +    def test_a_spotlight_pin_seals_its_closing_kind_and_comment(self):
1631 | +        pk, why, *_ = package()
1632 | +        self.assertIsNone(why)
1633 | +        pin = PP.to_pin(pk, "t")
1634 | +        mp = pin["moments_package"]
1635 | +        self.assertEqual(mp["shape"], "spotlight")
1636 | +        self.assertEqual(len(pin["segments"]), 1)
1637 | +        self.assertEqual(pin["segments"][0]["role"], "hook")
1638 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [], "closing": GOOD["closing"]["text"]})
1639 | +        self.assertEqual(mp["vo_jobs"], {"closing": "closing"})
1640 | +        self.assertEqual(mp["first_comment"], pk["first_comment"])
1641 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
1642 | +        integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
1643 | +                             mp["gates"], mp.get("btc_screen"),
1644 | +                             **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
1645 | +                                if mp.get("shape") == "spotlight" else {}))       # their exact call (23:1x ET)
1646 | +        self.assertEqual(integrator, mp["package_sha256"])
1647 | +        for change in (lambda p: p["moments_package"]["edl_vo"].update(closing="Another line."),
1648 | +                       lambda p: p["moments_package"].update(first_comment="x"),
1649 | +                       lambda p: p["moments_package"].update(shape="medley")):
1650 | +            p2 = copy.deepcopy(pin)
1651 | +            change(p2)
1652 | +            self.assertNotEqual(PP.pin_seal(p2), mp["package_sha256"])
1653 | +
1654 | +    def test_the_contract_refuses_anything_else(self):
1655 | +        pk, why, *_ = package()
1656 | +        self.assertIsNone(why)
1657 | +        cases = {
1658 | +            "two segments": lambda p: p["segments"].append(dict(p["segments"][0], label="clip_01")),
1659 | +            "an intro": lambda p: p["vo"].update(intro="Here is the thing."),
1660 | +            "a bridge": lambda p: p["vo"].update(bridges=["Next."], bridges_after_clip=[1]),
1661 | +            "a long closing": lambda p: (p["vo"].update(closing=" ".join(["word"] * 13)),
1662 | +                                         next(x for x in p["lines"] if x["slot"] == "closing").update(
1663 | +                                             text=" ".join(["word"] * 13))),
1664 | +            "a comment that is not the gated one": lambda p: p.update(first_comment=p["first_comment"] + " extra"),
1665 | +            "a runtime under 28 s": lambda p: p.update(runtime_s_estimate=27.9),
1666 | +            "no source row": lambda p: p["gates"].pop("spotlight_source"),
1667 | +            "a closing without its rows": lambda p: p["gates"].pop("closing_value"),
1668 | +            "a replayed row": lambda p: p["gates"]["hook_own"].update(replayed=True),
1669 | +            "no first comment": lambda p: p.pop("first_comment"),
1670 | +        }
1671 | +        for name, change in cases.items():
1672 | +            p2 = copy.deepcopy(pk)
1673 | +            change(p2)
1674 | +            with self.assertRaises(PP.PinRefused, msg=name):
1675 | +                PP.to_pin(p2, "t")
1676 | +
1677 | +    def test_the_comment_format(self):
1678 | +        self.assertEqual(PP.first_comment_text("Line one.\nLine two.", ["@a", "Some Name"]),
1679 | +                         "Line one.\nLine two.\n\nCredits \U0001F9E1\n\n@a Some Name")
1680 | +
1681 | +
1682 | +def snap_rig(sentences, k, marks=()):
1683 | +    src = source(sentences, channel="DataDash", age_h=2.0, vid="vidS")
1684 | +    ctx = E.Context(NOW, REG)
1685 | +    sp = E.Span(src, k, k)
1686 | +    m = M.record(sp, {"scores": dict(pm("x", "A", 1.0)["scores"]), "names_person": False, "risk": [],
1687 | +                      "topics": ["price_action"], "reason": "r"}, ctx, M.judge(sp, ctx), {"by": "fake"})
1688 | +    m["rank_score"] = 1.0
1689 | +    caps = lambda vid: ([(t, "w", True) for t in marks] or None, {"file": "f", "sha256": "s"} if marks else None)
1690 | +    return m, {"vidS": src}, ctx, caps
1691 | +
1692 | +
1693 | +S5 = "Bitcoin keeps moving and people keep watching it closely today."      # 10 words: 3.3 s with its pause
1694 | +S20 = " ".join(["Bitcoin"] + ["word"] * 63) + "."                              # 64 words: about 19.5 s
1695 | +S33 = " ".join(["Bitcoin"] + ["word"] * 109) + "."                             # 110 words: about 33 s
1696 | +
1697 | +
1698 | +class TestSnap(unittest.TestCase):
1699 | +    def test_the_next_sentences_first_whole_and_never_padded(self):
1700 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 2)
1701 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1702 | +        self.assertIsNone(why)
1703 | +        self.assertEqual(v["spotlight_snap"]["was"], [2, 2])
1704 | +        self.assertEqual(v["spotlight_snap"]["sentences"][0], 2)                # nothing before was needed
1705 | +        self.assertGreaterEqual(v["duration_s"], SPOT.SNAP_TO_S)
1706 | +        self.assertLess(v["duration_s"] - 3.3, SPOT.SNAP_TO_S)                 # one sentence fewer is too short
1707 | +        self.assertNotEqual(v["moment_id"], m["moment_id"])                    # a NEW moment, judged as usual
1708 | +        self.assertEqual(v["spotlight_snap"]["from"], m["moment_id"])
1709 | +        self.assertIn("eligibility", v)
1710 | +
1711 | +    def test_a_speaker_marker_after_turns_it_to_the_sentences_before(self):
1712 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4)
1713 | +        t_next = srcs["vidS"].tokens[srcs["vidS"].sentences[5][0]]["start"]
1714 | +        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4, marks=(t_next + 1.5,))
1715 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1716 | +        self.assertIsNone(why)
1717 | +        self.assertEqual(v["spotlight_snap"]["sentences"][1], 4)                # never across the marker
1718 | +        self.assertLess(v["spotlight_snap"]["sentences"][0], 4)
1719 | +
1720 | +    def test_no_snap_past_35_s_or_past_the_record(self):
1721 | +        m, srcs, ctx, caps = snap_rig([S20, S5, S20], 1)
1722 | +        v, why = SPOT.snap(m, srcs, ctx, caps)                                 # 3.3 + 19.5 = 22.8 s: fine
1723 | +        self.assertIsNone(why)
1724 | +        m, srcs, ctx, caps = snap_rig([S5], 0)
1725 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1726 | +        self.assertIsNone(v)
1727 | +        self.assertIn("the word record ends", why)
1728 | +        m, srcs, ctx, caps = snap_rig([S33, S5, S33], 1)                     # either side runs past 35 s
1729 | +        v, why = SPOT.snap(m, srcs, ctx, caps)
1730 | +        self.assertIsNone(v)
1731 | +        self.assertIn("over 35 s", why)
1732 | +        m, srcs, ctx, caps = snap_rig([S5, S20, S5], 1)                       # long enough already: unchanged
1733 | +        self.assertIs(SPOT.snap(m, srcs, ctx, caps)[0], m)
1734 | +
1735 | +
1736 | +class TestSourceTest(unittest.TestCase):
1737 | +    def lay(self, kind):
1738 | +        return {"measured": True, "layout": kind, "why": "w", "backend": "b", "replayed": False}
1739 | +
1740 | +    def test_conversation_or_first_hand_pass_and_recap_reaction_other_fail(self):
1741 | +        unmarked = {"measured": False, "unmarked": True}
1742 | +        for kind, want in (("conversation", True), ("first_hand", True), ("recap", False), ("reaction", False),
1743 | +                           ("other", False)):
1744 | +            self.assertEqual(SPOT.source_test(unmarked, self.lay(kind))[0], want, kind)
1745 | +
1746 | +    def test_an_unmeasured_layout_is_never_a_pass(self):
1747 | +        ok, why = SPOT.source_test({"measured": True, "turns": 30, "minutes": 10, "turns_per_min": 3.0},
1748 | +                                   {"measured": False, "why": "no sheet"})
1749 | +        self.assertFalse(ok)
1750 | +        self.assertIn("not measured", why)
1751 | +
1752 | +    def test_the_markers_only_make_it_stricter(self):
1753 | +        solo = {"measured": True, "turns": 8, "minutes": 16.5, "turns_per_min": 0.48}     # Nov 13: L6H7538ogGs
1754 | +        talk = {"measured": True, "turns": 20, "minutes": 16.8, "turns_per_min": 1.19}    # Nov 13: 3kV3nWC5SAY
1755 | +        self.assertFalse(SPOT.source_test(solo, self.lay("conversation"))[0])
1756 | +        self.assertTrue(SPOT.source_test(talk, self.lay("conversation"))[0])
1757 | +        self.assertTrue(SPOT.source_test(solo, self.lay("first_hand"))[0])       # a keynote is one voice
1758 | +        self.assertFalse(SPOT.source_test(talk, self.lay("recap"))[0])
1759 | +
1760 | +
1761 | +class TestContracts(unittest.TestCase):
1762 | +    def test_layout(self):
1763 | +        self.assertEqual(SPOT.parse_layout('{"layout": "conversation", "people_on_screen": 2, "why": "two people"}')
1764 | +                         ["layout"], "conversation")
1765 | +        for bad in ('{"layout": "panel", "people_on_screen": 2, "why": "w"}',
1766 | +                    '{"layout": "recap", "people_on_screen": "1", "why": "w"}',
1767 | +                    '{"layout": "recap", "people_on_screen": 1}', "not json"):
1768 | +            with self.assertRaises(ValueError):
1769 | +                SPOT.parse_layout(bad)
1770 | +
1771 | +    def test_write(self):
1772 | +        got = SPOT.parse_write(json.dumps(dict(GOOD, title={"text": "T", "cites": ["m1"]})), "m1")
1773 | +        self.assertEqual(got["title"]["cites"], ["m1"])
1774 | +        self.assertIsNone(SPOT.parse_write(json.dumps(GOOD), "m1", closing_allowed=False)["closing"])
1775 | +        self.assertIsNone(SPOT.parse_write(json.dumps(dict(GOOD, closing=None)), "m1")["closing"])
1776 | +        for bad in (dict(GOOD, title={"text": "T", "cites": ["other"]}), {k: GOOD[k] for k in ("title", "caption")},
1777 | +                    dict(GOOD, comment={"text": " ", "cites": []}), dict(GOOD, caption={"text": "x" * 221, "cites": []})):
1778 | +            with self.assertRaises(ValueError):
1779 | +                SPOT.parse_write(json.dumps(bad), "m1")
1780 | +
1781 | +    def test_value_verdict_needs_four_clear_yeses_and_twelve_words(self):
1782 | +        m = moment()
1783 | +        r = Router(coherence_verdict=[VALUE_YES])
1784 | +        v = SPOT.value_verdict(r, m, "Scarcity only matters when nobody can quietly change it.", "DataDash",
1785 | +                               {"heimdall"}, {"deepseek"})
1786 | +        self.assertTrue(v["ok"])
1787 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))   # off the writer
1788 | +        for ans in (dict(VALUE_YES, missed="no"), dict(VALUE_YES, adds="no")):
1789 | +            self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[ans]), m, "A line.", "D", set(), set())["ok"])
1790 | +        self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[VALUE_YES]), m, " ".join(["w"] * 13), "D",
1791 | +                                            set(), set())["ok"])                 # code counts the words too
1792 | +        r = Router(coherence_verdict=['{"adds": "maybe"}'])
1793 | +        v = SPOT.value_verdict(r, m, "A line.", "D", set(), set())
1794 | +        self.assertFalse(v["ok"])
1795 | +        self.assertFalse(v["measured"])
1796 | +        self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1797 | +        self.assertFalse(SPOT.value_verdict(Router(), m, "A line.", "D", set(), set())["ok"])   # no answer: no line
1798 | +
1799 | +    def test_style_of_the_comment_and_the_closing(self):
1800 | +        lint = lambda slot, text: [v["detail"].split(":")[0] for v in SPOT.style_lint([{"slot": slot, "text": text}])]
1801 | +        self.assertEqual(lint("comment", "This one stuck with me.\nWorth the full listen."), [])
1802 | +        self.assertIn("comment-lines", lint("comment", "One.\nTwo.\nThree."))
1803 | +        self.assertIn("comment-words", lint("comment", " ".join(["word"] * 31)))
1804 | +        self.assertIn("comment-credits", lint("comment", "Go follow @someone"))
1805 | +        self.assertIn("comment-credits", lint("comment", "Credits to them."))
1806 | +        self.assertIn("emoji", lint("comment", "So good \U0001F525"))
1807 | +        self.assertIn("closing-words", lint("closing", " ".join(["word"] * 13)))
1808 | +
1809 | +
1810 | +class TestCredits(unittest.TestCase):
1811 | +    def test_verified_handles_only_and_untagged_names_said_so(self):
1812 | +        cr = SPOT.credits("DataDash", {"name": "unknown", "measured": True}, HANDLES)
1813 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
1814 | +        self.assertIn("no attested speaker", cr["speaker"]["untagged_why"])
1815 | +        cr = SPOT.credits("Simply Bitcoin", {"name": "Natalie", "measured": True}, HANDLES)   # an alias
1816 | +        self.assertEqual(cr["tags"], ["Simply Bitcoin", "@natbrunell"])
1817 | +        self.assertIn("no verified X handle", cr["channel"]["untagged_why"])
1818 | +        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": True}, HANDLES)
1819 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten", "Jane Guest"])
1820 | +        self.assertEqual(cr["speaker"]["untagged_why"], "not in the verified table")
1821 | +        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": False}, HANDLES)     # never a guess
1822 | +        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
1823 | +        self.assertEqual(SPOT.credits("DataDash", None, "/nonexistent.json")["tags"], ["DataDash"])
1824 | +
1825 | +
1826 | +class TestPool(unittest.TestCase):
1827 | +    def test_one_per_channel_per_day_and_the_record_must_read(self):
1828 | +        ctx = E.Context(NOW, REG)
1829 | +        a, b = moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset"))
1830 | +        caps = lambda vid: (None, None)                                     # (two texts: one speech is one moment)
1831 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": SPOT.et_day(NOW)}],
1832 | +                             captions_for=caps)
1833 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])
1834 | +        self.assertIn("already has a spotlight", why["a"])
1835 | +        got, _ = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": "2026-11-01"}], captions_for=caps)
1836 | +        self.assertEqual(len(got), 2)                                       # another day
1837 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=None, captions_for=caps)
1838 | +        self.assertEqual(got, [])
1839 | +        self.assertIn("not measured", why["a"])
1840 | +
1841 | +    def test_35_s_ceiling_and_the_cold_open(self):
1842 | +        ctx = E.Context(NOW, REG)
1843 | +        caps = lambda vid: (None, None)
1844 | +        long_ok = moment(mid="l", dur=30.0, channel="A")
1845 | +        too_long = moment(mid="t", dur=36.0, channel="B", text=TEXT.replace("money", "asset"))
1846 | +        conj = moment(mid="c", channel="C", text="And " + TEXT.replace("money", "thing"))
1847 | +        got, why = SPOT.pool([long_ok, too_long, conj], {}, ctx, spotlit=[], captions_for=caps)
1848 | +        self.assertEqual([m["moment_id"] for m in got], ["l"])               # 30 s: a medley's 20 s does not bind
1849 | +        self.assertIn("35.0 s", why["t"])
1850 | +        self.assertIn("cannot open cold", why["c"])
1851 | +
1852 | +    def test_the_record(self):
1853 | +        p = os.path.join(HERE, "fixtures_spotlights_record.json")
1854 | +        try:
1855 | +            self.assertEqual(SPOT.load_spotlit(p), [])
1856 | +            SPOT.record_spotlit(p, {"channel_id": "A", "day_et": "2026-11-13"})
1857 | +            self.assertEqual(SPOT.load_spotlit(p), [{"channel_id": "A", "day_et": "2026-11-13"}])
1858 | +            with open(p, "w") as f:
1859 | +                f.write("{")
1860 | +            self.assertIsNone(SPOT.load_spotlit(p))
1861 | +            with self.assertRaises(ValueError):
1862 | +                SPOT.record_spotlit(p, {"channel_id": "B", "day_et": "2026-11-13"})
1863 | +        finally:
1864 | +            if os.path.exists(p):
1865 | +                os.remove(p)
1866 | +
1867 | +
1868 | +class TestPackageFor(unittest.TestCase):
1869 | +    def test_the_closing_line_ships_only_with_every_gate(self):
1870 | +        pk, why, router, asked, fids = package()
1871 | +        self.assertIsNone(why)
1872 | +        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])
1873 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
1874 | +        for g in PP.CLOSING_GATES:
1875 | +            self.assertEqual(pk["gates"][g]["status"], "PASS")
1876 | +        self.assertEqual(asked, [GOOD["closing"]["text"]])                  # context judged WITH the line
1877 | +        self.assertEqual(sorted(map(tuple, fids)), [("closing",), ("title", "caption", "comment")])
1878 | +        self.assertNotIn("coherence", pk["gates"])
1879 | +        self.assertNotIn("r4", pk["gates"])
1880 | +        self.assertTrue(pk["first_comment"].startswith(GOOD["comment"]["text"] + "\n\nCredits \U0001F9E1\n\n"))
1881 | +        self.assertTrue(pk["first_comment"].endswith("@Nicholas_Merten"))
1882 | +        self.assertTrue(28.0 <= pk["runtime_s_estimate"] <= 50.0)
1883 | +
1884 | +    def test_any_failure_leaves_no_line(self):
1885 | +        for name, kw in (("the value verdict says no", {"value": dict(VALUE_YES, adds="no")}),
1886 | +                         ("the value verdict is out of contract", {"value": '{"adds": 1}'}),
1887 | +                         ("its fidelity fails", {"cfid": dict(FID_OK, ok=False, violations=[
1888 | +                             {"slot": "closing", "rule": "COMMENTARY", "detail": "d"}])}),
1889 | +                         ("context fails with it", {"cx": dict(CX_OK, ok=False, violations=[
1890 | +                             {"rule": "NOT_ENTAILED"}])}),
1891 | +                         ("it breaks the house style", {"write": dict(GOOD, closing={
1892 | +                             "text": "Ultimately scarcity matters, which makes it rare.", "cites": []})})):
1893 | +            pk, why, router, asked, fids = package(**kw)
1894 | +            self.assertIsNone(why, name)
1895 | +            self.assertIsNone(pk["vo"]["closing"], name)
1896 | +            self.assertFalse(any(g in pk["gates"] for g in PP.CLOSING_GATES), name)
1897 | +            self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [], name)
1898 | +            self.assertEqual(asked[-1], None, name)                         # the package without it is judged
1899 | +            self.assertFalse(pk["spotlight"]["closing"]["kept"], name)
1900 | +
1901 | +    def test_a_null_closing_is_the_default(self):
1902 | +        pk, why, router, asked, fids = package(write=dict(GOOD, closing=None))
1903 | +        self.assertIsNone(why)
1904 | +        self.assertIsNone(pk["vo"]["closing"])
1905 | +        self.assertEqual(router.calls.count(("coherence_verdict", None, None)), 0)
1906 | +        self.assertNotIn("coherence_verdict", [c[0] for c in router.calls])     # no value verdict is asked
1907 | +
1908 | +    def test_one_more_write_of_a_failing_title_never_of_the_closing(self):
1909 | +        bad = dict(GOOD, title={"text": "The one money nobody can print more of today", "cites": []})   # 9 words
1910 | +        second = dict(GOOD, closing={"text": "A different closing line here.", "cites": []})
1911 | +        pk, why, router, *_ = package(writes=[bad, second])
1912 | +        self.assertIsNone(why)
1913 | +        self.assertEqual(pk["title"], GOOD["title"]["text"])
1914 | +        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])      # the first write's: one write
1915 | +        pk, why, *_ = package(writes=[bad, bad])
1916 | +        self.assertIsNone(pk)
1917 | +        self.assertIn("both writes", why)
1918 | +
1919 | +    def test_the_base_lines_must_pass_their_own_verdicts(self):
1920 | +        pk, why, *_ = package(fid=dict(FID_OK, ok=False, violations=[{"slot": "title", "rule": "VERDICT_NO"}]))
1921 | +        self.assertIsNone(pk)
1922 | +        self.assertIn("VO fidelity", why)
1923 | +        pk, why, *_ = package(value=dict(VALUE_YES, adds="no"), cx_base=dict(CX_OK, ok=False, violations=[
1924 | +            {"rule": "STRONGER"}]))
1925 | +        self.assertIsNone(pk)
1926 | +        self.assertIn("context integrity", why)
1927 | +
1928 | +    def test_step_a_off_the_writer_must_exist(self):
1929 | +        m = moment()
1930 | +        r = Router(angle_write=[GOOD])
1931 | +        r.backends = {"fake:xai": B("fake", "grok"), "fake:heimdall": B("fake", "deepseek")}   # both on the writer
1932 | +        pk, why = SPOT.package_for(r, m, E.Context(NOW, REG), {}, two(), {}, {}, pre_of(m), {}, log=lambda *a: None,
1933 | +                                   attribute=unknown_speaker)
1934 | +        self.assertIsNone(pk)
1935 | +        self.assertIn("L-x", why)
1936 | +
1937 | +
1938 | +class TestBuild(unittest.TestCase):
1939 | +    """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
1940 | +
1941 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None):
1942 | +        ctx = E.Context(NOW, REG)
1943 | +        calls = {}
1944 | +
1945 | +        def prescreen(router, ms_, *a, **k):
1946 | +            return {m["moment_id"]: dict(a_item("hook"), backend="fake:xai") for m in ms_}, \
1947 | +                {m["moment_id"]: [] for m in ms_}, set(), set()
1948 | +
1949 | +        def hook_ratings(router, ms_, *a, **k):
1950 | +            return {m["moment_id"]: {"scroll": ratings[m["moment_id"]], "alone": 5, "setup": 3,
1951 | +                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "fake:xai"}
1952 | +                    for m in ms_}, None
1953 | +
1954 | +        def second(router, cleared, a_by, *a, **k):
1955 | +            return {mid: [a_by[mid], dict(a_item("hook"), backend="fake:heimdall")] for mid in cleared}, {}
1956 | +
1957 | +        def package_for(router, m, *a, **k):
1958 | +            calls.setdefault("package_for", []).append(m["moment_id"])
1959 | +            return {"segments": [m], "shape": "spotlight"}, None
1960 | +        idx = {m["moment_id"]: sv(m["text"], s) for m, s in zip(ms, alone or [4.0] * len(ms)) if s is not None}
1961 | +        seq = list(poll or [])
1962 | +        verdicts = lambda path, sha: (seq.pop(0) if seq else idx, {"read": True})
1963 | +        stubs = [(SPOT.P, "prescreen", prescreen), (SPOT.P, "hook_ratings", hook_ratings),
1964 | +                 (SPOT.P, "second_screen", second), (SPOT, "package_for", package_for),
1965 | +                 (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
1966 | +                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
1967 | +                 (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
1968 | +                 (VP, "visual_for", lambda r, m, w, c: {"measured": True, "flags": [], "backend": "fake:vis"}),
1969 | +                 (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
1970 | +                 (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
1971 | +                 (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
1972 | +                 (SPOT.P, "_writers", lambda r: (set(), set()))]
1973 | +        patches = [mock.patch.object(o, n, f) for o, n, f in stubs]
1974 | +        for p in patches:
1975 | +            p.start()
1976 | +        try:
1977 | +            out = SPOT.build(Router(), ms, {}, ctx, work_dir="/tmp", scorer_verdicts_path="v.json",
1978 | +                             lock_check=lock or (lambda segs: pre_of(segs[0])), spotlit=[], sleep=lambda s: None,
1979 | +                             captions_for=lambda vid: (None, None), wait_s=60.0)
1980 | +        finally:
1981 | +            for p in patches:
1982 | +                p.stop()
1983 | +        return out, calls
1984 | +
1985 | +    def test_the_best_qualifying_moment_goes_to_the_package(self):
1986 | +        ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
1987 | +              moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
1988 | +        out, calls = self.run_build(ms, {"a": 3, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1989 | +        self.assertEqual(calls["package_for"], ["b"])                      # c opens best but stands alone at 3
1990 | +        self.assertIn("hook's own job rates 3", out["moments"]["a"]["out"])
1991 | +        self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
1992 | +        self.assertIsNotNone(out["package"])
1993 | +
1994 | +    def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
1995 | +        ms = [moment(mid="a", channel="A")]
1996 | +        later = {"a": sv(TEXT, 4.0)}
1997 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[None], poll=[{}, later])
1998 | +        self.assertEqual(calls["package_for"], ["a"])
1999 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[None], layout="recap")
2000 | +        self.assertIsNone(out["package"])
2001 | +        self.assertNotIn("package_for", calls)
2002 | +        self.assertIn("no rating yet", out["moments"]["a"]["out"])
2003 | +        self.assertEqual(out["near"][0]["moment_id"], "a")
2004 | +        self.assertEqual(out["near"][0]["passed"][-1], "step A from the second family")
2005 | +
2006 | +    def test_ruling_92_and_a_lock_with_no_verdict_stops(self):
2007 | +        ms = [moment(mid="a", channel="A")]
2008 | +        out, calls = self.run_build(ms, {"a": 5}, layout="reaction")
2009 | +        self.assertIsNone(out["package"])
2010 | +        self.assertIn("ruling 92", out["moments"]["a"]["out"])
2011 | +        out, calls = self.run_build(ms, {"a": 5}, lock=lambda segs: {"ok": False, "segments": [], "error": "timeout"})
2012 | +        self.assertIsNone(out["package"])
2013 | +        self.assertIn("timeout", out["lock_stop"])
2014 | +
2015 | +
2016 | +if __name__ == "__main__":
2017 | +    unittest.main()
2018 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that another
session, the integrator, renders into short Bitcoin videos). The change adds a SECOND PIN KIND, the "spotlight"
(one strong clip, an optional host line, the sign-off). Only state what you can verify from the diff; if uncertain,
say so; do not guess. Be factual and specific: file:line and a concrete input that breaks it.

Background (static):
- The flagship kind is the MEDLEY (a hook clip + 2-4 clips back to back, one takeaway line). A package passes many
  gates; package_pin.to_pin() turns it into a pin only when every REQUIRED gate row in its sealed inventory is exactly
  "PASS" with replayed false (law L-j: fail closed), and seals the gated bytes with seal() (sha256). The integrator's
  readiness check imports THIS worktree's package_pin.py live and recomputes seal() on every pin, so seal() must stay
  backward compatible: every pin sealed before this change must recompute to its own package_sha256.
- Law L-m: nothing measured is never a pass (an unavailable or out-of-contract verdict is no verdict).
- Law L-s: a verdict never comes from the vendor or model family that wrote the line it judges.
- The verdicts the spotlight reuses (step A context integrity, the second recognition pass and CUTTABLE, G17a hook
  onset, the hook rating, the visual check, the second step-A family, exclusion, VO fidelity, context integrity) are
  the medley's own, unchanged, cached across builds.
- The ALONE scorer is the render's stand-alone clip scorer (1-5), run by the integrator's service on candidates this
  builder writes at the start of each build (package.scorer_pass); verdicts are read from a file and apply only to the
  exact text they rated (text_sha256).
- The render's lock pre-check (lock_precheck) re-decodes each clip on the integrator's side and passes, adopts a
  spoken text, or holds the clip. Its results are keyed by the integrator's decoder sha, which moved tonight to
  c705b20ed800 (their spotlight branches changed pinned.py; RULES unchanged).

The orders (verbatim excerpts):
- RULING 90 (22:40 ET Nov 13, LAW since 22:52): "a spotlight is built only when the window's search ends with no
  medley, or for a moment no medley used. SHAPE: ONE moment, one speaker, one channel: 12 to 35 s of clip. No hook/clip
  split, no bridge, no join. Then at most ONE closing line in the PBX MAX voice, 12 words or fewer, class D commentary
  that characterises what was SAID (the two refused patterns stay refused) ... Then the sign-off and the credits card
  with that one channel, then the outro. Total 28 to 50 s. ... WHICH MOMENT: it must rate >= 4 on the hook's own job
  (it opens cold) AND >= 4 as a clip standing alone (the ALONE scorer + step A, both vendors as routed); the visual
  check clean; inside 12 h at the render clock; never a delivered span; at most one spotlight per channel per day. If
  the strong moment is under 12 s, snap it OUTWARD to the speaker's whole thought (ruling 32's snap; the added words
  judged as usual), not padded. EVERY integrity law is unchanged ... YOUR SIDE: the spotlight package (kind
  'spotlight' sealed in the pin; gates: the moment's two ratings, step A both families, pre-check, the closing line's
  fidelity + context as for a takeaway, title, caption). Title 8 words or fewer; caption in house style; ALSO write
  the first-comment draft ... in PBX's format: one or two short casual lines specific to this clip (not preachy, no
  emoji), a blank line, 'Credits' + the orange heart, a blank line, the X handles of the channel and the attested
  speaker (handles only from a verified table: if a handle is not in the table, leave the name untagged and say so)."
- RULING 91 (22:52): "Default for a spotlight: NO PBX line ... A line is written only as a candidate and is kept only
  if a separate VALUE verdict (off the writer's family) answers all of: it says something the clip does not already
  say; it does not restate, summarise or cheer the clip; a viewer would miss it if it were cut; it is 12 words or
  fewer; plus the usual fidelity and context gates. One write, one verdict; anything short of a clear yes means no
  line."
- RULING 92 (22:52): "A spotlight moment must come from a conversation or original reporting: an episode whose caption
  turn structure shows two or more speakers (interview, podcast, panel), or a first-hand statement (a keynote, an
  interview on a news network). NOT from a solo host-to-camera news recap or reaction segment, on any channel.
  Measured, not listed by name: the turn markers across the episode (one speaker throughout = solo), plus the visual
  check's layout (one face to camera with headline graphics or b-roll = recap)."
- 22:58: "The 20 s per source video is a medley rule; for a spotlight the ceiling is ruling 90's 35 s."
- The pin contract agreed with the integrator (22:44): moments_package.shape "spotlight"; exactly one segment, role
  "hook"; edl_vo {"intro": null, "bridges": [], "closing": <= 12 words or null}; signoff_expected names that one
  channel; first_comment is the WHOLE comment (printed verbatim, nothing appended); gate rows always required:
  spotlight_source, hook_own, stands_alone, step_a_two_families, visual, window_12h, never_delivered,
  one_per_channel_day, precheck; and closing_value, closing_fidelity, closing_context whenever closing is non-null.
  The integrator's seal call: seal(segments, edl_vo, signoff, title, caption, gates, btc_screen, shape=...,
  first_comment=...) for a spotlight only.

The change:
1. package_pin.py: SPOTLIGHT_GATES, CLOSING_GATES, SPOT_RUNTIME_S (28, 50), SPOT_CLOSING_MAX_WORDS 12,
   first_comment_text(); required_gates() for the spotlight (a package's vo or a pin's edl_vo); seal() gains
   shape / first_comment (in the body only for shape "spotlight") and edl_vo["closing"] (only when the key is present);
   pin_seal(pin); line_problems() checks the closing line and that first_comment is built from the gated comment;
   spotlight_problems() (one segment, no intro or bridge, closing <= 12 words, the sign-off names the channel, a
   first comment, runtime 28-50 s); screen_problems() also for a spotlight; to_pin() emits the agreed fields.
2. package.py: usable(seg_max=...) (35 s for a spotlight); scorer_pass(extra=...) and build(scorer_extra=...) send the
   spotlight's pool to the ALONE scorer with the medley's own candidates (deduplicated by id and text).
3. spotlight.py (new):
   - pool(): free stage (usable with 35 s, one per re-posted speech, one spotlight per channel per ET day from a
     record, the snap for a moment under SNAP_TO_S = 13.7 s: 28 s minus the factory's 14.3 s tail, the render's hook
     opener rule and its topic rule);
   - snap(): whole sentences of the same word record, the next ones first, then the ones before, never past 35 s,
     never across a caption speaker marker; a new moment re-judged by the miner's eligibility;
   - episode_turns() + layout_for() (a vision verdict on the clip's own contact sheet, cached) + source_test()
     (ruling 92: PASS only for a measured layout "conversation" or "first_hand"; a marked episode under 1.0 caption
     turns a minute is not a conversation);
   - build(): the stages in order (step A, L-v 2 / CUTTABLE, G17a and the hook rules, the hook's own job >= 4, the
     visual check clean, step A from the second family, the ALONE scorer >= 4 with a bounded wait, ruling 92), then
     best first: exclusion, the lock pre-check, package_for(); the three nearest when none qualifies;
   - package_for(): one write (title, caption, comment, candidate closing); one more write of title/caption/comment
     only when a free gate refuses them (never of the closing); every verdict off the writers; the closing ships only
     with the free gates, ruling 91's value verdict (four clear yeses AND <= 12 words in code), its own fidelity
     verdict and context integrity with it spoken; otherwise no line; then the speaker record, credits() from the
     verified table, the first comment, LP.apply, and the inventory (package.inventory's rows minus "r4" and
     "coherence", plus the spotlight rows).
4. lock_precheck.py: DECODER c705b20ed800.
5. proof_ledger.py: the pool to the scorer at the build's start; the spotlight after the medley search (a sealed
   medley's clips excluded); SPOTLIGHT_PIN.json and the SPOTLIGHTS record.
6. Tests: test_spotlight.py (new), test_lock_precheck.py (the decoder).

Check, against the diff:
- that every pin sealed before the change recomputes unchanged, and that a spotlight's closing line, kind and first
  comment are inside the seal;
- that no path can ship a closing line without all three closing rows PASS, or ship one that failed any gate;
- that every required row is computed from a measurement (none hard-coded to PASS without evidence); name any row that
  could PASS on missing data;
- that the snap never pads, never crosses a speaker marker, never exceeds 35 s, and that the snapped span is judged
  by every gate;
- that ruling 92's test cannot pass a solo recap or a reaction, and fails closed when unmeasured;
- that every verdict is off the writers' vendor and family (L-s), the value verdict included;
- the per-channel-per-day rule, including an unreadable record;
- that the medley's behaviour is unchanged (scorer_extra, usable's default, seal for medley pins).

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario for each), then
"SHIP: yes / no / yes with conditions". Reminder: only what you can verify from the diff; fail closed is the law.

