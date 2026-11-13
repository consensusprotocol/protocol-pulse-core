# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2030
# Branch: pp-selectid
# Generated: 2026-11-12 20:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2030/C1_STEP.diff (1584 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 51f24c7d..662f4297 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -9,29 +9,44 @@ usable()      moments a package may use: on screen eligible (word timing, law L-
   6 |  prescreen()   step A of law L-s on each usable moment's own context, ONCE per moment (package-independent), stored on
   7 |                the moment (`store`: a JSON ledger keyed by moment and the step-A prompt); never recomputed
   8 |  ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
   9 | -              channels (one clip per channel, L-u)
  10 | -lineup_for()  code: hook + 2-3 clips for one angle, every segment from a different channel, at most one price prediction
  11 | -              (L-u), a clip under SHORT_CLIP_S only as the punchline, and the length the runtime (60-70 s, L-o) AND the
  12 | -              factory's EDL rule R4 (VO <= 25 % of runtime, one bridge per channel transition) both allow
  13 | -write_v3()    role angle_write: the PBX MAX VO in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...), in
  14 | -              one of two styles (05:25 item 3): "host" (tease / hedge-matched hand-off of a VERIFIED speaker / the
  15 | -              host's own takeaway after a clip) or "quote" (show + topic, at most four exact words quoted); NEVER a
  16 | -              restatement of a clip's claim; word budgets from R4 and the runtime
  17 | -GATES (hard, every one, recorded in a sealed inventory, package_pin.REQUIRED_GATES):
  18 | -              cheap first (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4;
  19 | +              channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
  20 | +lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
  21 | +              channel, at most one price prediction (L-u), a clip under SHORT_CLIP_S only as the punchline, and seconds
  22 | +              that let ONE takeaway land the factory's runtime estimate in 60-70 s (L-o, L-y 4)
  23 | +medley()      the blind clips-ALONE verdict (L-y 3): a through-line, a rating per clip, a verdict per join
  24 | +write_takeaway() role angle_write: the ONE takeaway (host commentary), ONE title, ONE caption, and the one bridge only
  25 | +              at a join the clips-alone verdict flagged (L-y 2); NEVER a restatement of a clip's claim
  26 | +GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gates):
  27 | +              the clips-alone verdict first (no writing before it passes);
  28 | +              cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
  29 |                then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
  30 |                integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
  31 | -              start in the background as soon as a line-up is fixed; then COHERENCE (blind, >= 4).
  32 | +              start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
  33 |                Every verdict avoids the vendors and model families of every reply whose text it judges (L-x).
  34 |                A rejected line goes back to the writer with the exact violations; a clip that fails exclusion or L-v 2
  35 | -              is dropped and the angle re-lined; at most WRITES writes per angle and MAX_ANGLES angles; the first
  36 | -              package with coherence >= COHERENCE_MIN wins (05:30).
  37 | +              is dropped and the angle re-lined; at most WRITES writes per line-up, LY_LINEUPS line-ups per angle and
  38 | +              MAX_ANGLES angles; the first package that passes every gate wins (05:30).
  39 |  OUTPUT pp.package/1: segments (moment ids, verbatim text, times), VO, title, caption, the gate inventory, the model per
  40 |                artefact, seconds and dollars.
  41 | +
  42 | +L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12, PBX's verdict on the reviewed video; amends L-q, L-w 1 and
  43 | +R4-moments): build() makes the MEDLEY the default shape. The hook and 2-4 clips play back to back with no narration,
  44 | +then ONE takeaway after the last clip (host commentary, class D, one or two sentences, <= 30 words), then the
  45 | +sign-off. There is no intro after the hook and no bridge.
  46 | +- SELECTION carries the weight: the angle proposer gives the moments in PLAY ORDER, each clip's opening making sense
  47 | +  after the previous clip's ending in the speaker's own words (lineup_for).
  48 | +- The blind coherence verdict is asked on the clips ALONE first (medley(): a through-line a viewer can state, a rating
  49 | +  per clip, and per join whether a viewer can follow the jump). Only then is it asked on the takeaway (coherence()).
  50 | +- A bridge is the EXCEPTION: at most ONE, only at the join the clips-alone verdict flagged, and only when the writer
  51 | +  also judges a viewer cannot follow it. The package records why (ly_shape()). Two or more flagged joins mean the
  52 | +  line-up is wrong: other clips are picked.
  53 | +- 3-5 clips; the factory's runtime estimate stays inside 60-70 s (the measured final is accepted at 58-72 s, ruling 12).
  54 | +- One clip per channel unless the supply forces otherwise, and then the package says so (supply_exception).
  55 |  """
  56 |  import hashlib
  57 |  import itertools
  58 |  import json
  59 | +import math
  60 |  import os
  61 |  import re
  62 |  import time
  63 | @@ -42,11 +57,8 @@ import eligibility as E
  64 |  import vo_fidelity as VF
  65 |  
  66 |  SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
  67 | -RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the one hard length rule
  68 | -WPS = 2.6                          # PBX MAX VO words per second: an ASSUMPTION until the render measures it
  69 | -SIGNOFF_WORDS = 18                 # the preview's sign-off ("Clips today from A, B, and C. Go follow them ...")
  70 | -FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO (~7.4 s)
  71 | -VO_S = (6.0, 22.0)                 # the VO's seconds (intro + bridges), the slack that lands the runtime
  72 | +RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the packaging target the factory's estimate must meet (ruling 12)
  73 | +VO_S = (6.0, 22.0)                 # the PBX MAX v3 VO's seconds (intro + bridges), content_range()'s slack
  74 |  R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
  75 |  TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
  76 |  PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
  77 | @@ -113,8 +125,8 @@ def runtime(segs, vo_lines):
  78 |      """The FACTORY's own estimate, the one its hard 60-70 s check reads (edl_rules._r4_moments, main a5ec0f17: "hook +
  79 |      clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll"): segments' word spans + every VO line
  80 |      (intro, bridges) at R4_WPS w/s + R4_PREROLL_S each + FINAL_TAIL_S (the sign-off is inside it). It replaced (07:42)
  81 | -    this module's own estimate (2.6 w/s, no pre-roll, FIXED_S + the sign-off), which ran 3-4 s lower than the factory's
  82 | -    on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  83 | +    this module's own estimate (2.6 w/s, no pre-roll, a fixed tail + the sign-off), which ran 3-4 s lower than the
  84 | +    factory's on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  85 |      vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
  86 |      return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
  87 |  
  88 | @@ -126,6 +138,41 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
  89 |                                     # clip; 60-70 s stays hard
  90 |  
  91 |  
  92 | +LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
  93 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
  94 | +LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
  95 | +                                   # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
  96 | +LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
  97 | +LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
  98 | +                                   # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
  99 | +LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
 100 | +
 101 | +
 102 | +def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 103 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 104 | +    n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 105 | +    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 106 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 107 | +    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 108 | +    return round(lo, 2), round(hi, 2)
 109 | +
 110 | +
 111 | +def takeaway_budget(content_s, other=()):
 112 | +    """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 113 | +    estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 114 | +    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 115 | +    other = [t for t in other if t and t.strip()]
 116 | +    fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 117 | +    words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 118 | +    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 119 | +              r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 120 | +    for a, b in (LY_AIM_S, RUNTIME_S):
 121 | +        lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 122 | +        if lo <= hi:
 123 | +            return lo, hi
 124 | +    return None
 125 | +
 126 | +
 127 |  def r4_max_vo_words(content_s, n_vo):
 128 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
 129 |      VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
 130 | @@ -179,13 +226,6 @@ def r4(pk):
 131 |                           "R4 (moments-first, 06:00) PASS") + f" | {note}"
 132 |  
 133 |  
 134 | -def budgets(content_s, n_bridges=1):
 135 | -    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
 136 | -    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
 137 | -    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
 138 | -    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
 139 | -
 140 | -
 141 |  def _name(m, ctx):
 142 |      return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
 143 |  
 144 | @@ -197,38 +237,23 @@ def signoff(segs, ctx):
 145 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 146 |  
 147 |  
 148 | -def plain_vo(segs, ctx):
 149 | -    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
 150 | -    last (orchestrator 03:40); the title names whole channels only (U11)."""
 151 | -    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
 152 | -    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
 153 | -    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
 154 | -    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
 155 | -    while len(title) > 70 and len(chans) > 1:
 156 | -        chans = chans[:-1]
 157 | -        title = "Bitcoin: " + ", ".join(chans) + " and others"
 158 | -    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
 159 | -    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}
 160 | +def labels(n):
 161 | +    """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 162 | +    return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 163 |  
 164 |  
 165 | -def assemble(order, by_id, fields, ctx, vo_kind):
 166 | -    segs = [by_id[i] for i in order]
 167 | -    lines = [dict(fields["intro"], slot="intro")] + \
 168 | -        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 169 | -        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 170 | -    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
 171 | +def _package(segs, ctx, fields, vo_kind, vo, lines):
 172 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"] not in ("title", "caption"))
 173 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 174 |            "vo_kind": vo_kind, "style": fields.get("style"),
 175 | -          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
 176 | +          "segments": [{"label": lb, "moment_id": m["moment_id"],
 177 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 178 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 179 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 180 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 181 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 182 | -                       for i, m in enumerate(segs)],
 183 | -          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 184 | -                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
 185 | -                 "signoff": signoff(segs, ctx)},
 186 | +                       for lb, m in zip(labels(len(segs)), segs)],
 187 | +          "vo": dict(vo, signoff=signoff(segs, ctx)),
 188 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
 189 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
 190 |            "lines": lines}
 191 | @@ -240,6 +265,46 @@ def assemble(order, by_id, fields, ctx, vo_kind):
 192 |      return pk
 193 |  
 194 |  
 195 | +def assemble(order, by_id, fields, ctx, vo_kind):
 196 | +    """The PBX MAX v3 shape (an intro after the hook and a line after clips; the orchestrator's given packages of the
 197 | +    night of Nov 11-12). L-y's medley is assemble_medley()."""
 198 | +    segs = [by_id[i] for i in order]
 199 | +    lines = [dict(fields["intro"], slot="intro")] + \
 200 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 201 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 202 | +    vo = {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 203 | +          "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1))}      # the renderer's after_clip
 204 | +    return _package(segs, ctx, fields, vo_kind, vo, lines)
 205 | +
 206 | +
 207 | +def assemble_medley(order, by_id, fields, ctx, vo_kind):
 208 | +    """L-y: the clips back to back, ONE takeaway after the last clip (slot "takeaway", the renderer's after_clip = the
 209 | +    last clip), and at most one bridge: after the hook it is the renderer's intro slot (slot "intro"), after clip k it is
 210 | +    a bridge after_clip k (slot "bridge_1"). fields: takeaway, bridge (None or {"text", "cites", "why"}), bridge_after
 211 | +    (None, 0 = after the hook, or k), title, caption."""
 212 | +    segs = [by_id[i] for i in order]
 213 | +    n_clips = len(segs) - 1
 214 | +    b, k = fields.get("bridge"), fields.get("bridge_after")
 215 | +    if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 216 | +        raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 217 | +    mid = b is not None and k > 0
 218 | +    lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 219 | +        ([dict(b, slot="bridge_1")] if mid else []) + \
 220 | +        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 221 | +         dict(fields["caption"], slot="caption")]
 222 | +    vo = {"intro": b["text"] if b is not None and k == 0 else None,
 223 | +          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 224 | +          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 225 | +    pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 226 | +    pk["shape"] = "medley"
 227 | +    pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 228 | +                                           "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
 229 | +                                           "text": b["text"], "why": b.get("why"),
 230 | +                                           "confirmed_by": fields.get("bridge_confirmed_by")}
 231 | +    pk["supply_exception"] = fields.get("supply_exception")
 232 | +    return pk
 233 | +
 234 | +
 235 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
 236 |  
 237 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
 238 | @@ -309,9 +374,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 239 |      return a_by, fails, vendors, families
 240 |  
 241 |  
 242 | -ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
 243 | -voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
 244 | -checks. The channels were not in one conversation and never answer each other.
 245 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
 246 | +play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
 247 | +clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
 248 | +conversation and never answer each other.
 249 |  
 250 |  {note}
 251 |  {clips}
 252 | @@ -320,52 +386,65 @@ Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repea
 253 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 254 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 255 |  it is today's.
 256 | -The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
 257 | -seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
 258 | -sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
 259 | -from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
 260 | -attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
 261 | +With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
 262 | +clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
 263 | +introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
 264 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
 265 | +each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
 266 | +survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
 267 | +"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
 268 | +words on what it adds and why it follows the clip before it (an internal note).
 269 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 270 |  "support": {{"id": "..."}}}}]}}"""
 271 |  
 272 | -STYLES = {
 273 | -    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
 274 | -            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
 275 | -            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
 276 | -            "clip, as your opinion, never as what the speaker said.",
 277 | -    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
 278 | -             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
 279 | -             "title."}
 280 | +MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
 281 | +Each clip is a person's own words from a show; the shows were not in one conversation.
 282 | +
 283 | +{clips}
 284 |  
 285 | -WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 286 | +1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
 287 | +   "none" if there is none.
 288 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
 289 | +3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
 290 | +   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
 291 | +   words.
 292 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
 293 | +
 294 | +WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 295 |  THE ANGLE (the point this video makes): "{angle}"
 296 | -The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
 297 | +The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
 298 | +in one conversation and never answer each other):
 299 |  
 300 |  {note}
 301 |  {lineup}
 302 |  
 303 | -The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
 304 | -(written by code).
 305 | -Write:
 306 | -- "intro": heard right AFTER the hook: your own take that sets up the angle.
 307 | -- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
 308 | -- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
 309 | -- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
 310 | +After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 311 | +{bridge}Write:
 312 | +- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 313 | +  opinion or conclusion), never a restatement of any clip.
 314 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 315 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 316 | -{style}
 317 |  RULES (a line that breaks one is rejected):
 318 | -- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
 319 | -- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
 320 | -  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
 321 | +- NEVER restate a clip's claim, and never repeat its words: the clip says it, in its own words.
 322 | +- Your OWN commentary must contain no number, price, date, named person or company, must not say or imply what any
 323 | +  speaker thinks, and must not relate speakers.
 324 |  - Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
 325 |    for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
 326 |    ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
 327 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 328 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 329 |    "slams", "exposes", "admits", "confirms", "caught".
 330 | -{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
 331 | +{extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 332 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 333 |  
 334 | +BRIDGE_ASK = """ONE JOIN NEEDS HELP: a blind viewer who watched these clips back to back could not follow the jump from
 335 | +{a} to {b} ("{why}"). Write ONE "bridge", heard between them: as short as it can be (at most {n} words); it only makes
 336 | +the next clip's subject or referent clear (its show and its topic, or a question); it never says what the next speaker
 337 | +thinks. Give "why": one sentence on why a viewer could not follow the jump without it. If you judge a viewer CAN
 338 | +follow this jump without narration, give "bridge": null (these clips then do not sit together, and other clips are
 339 | +picked).
 340 | +"""
 341 | +
 342 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
 343 |  different person's own words).
 344 |  
 345 | @@ -419,36 +498,43 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 346 |      return out
 347 |  
 348 |  
 349 | -def lineup_for(angle, by_id, dropped=frozenset()):
 350 | -    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
 351 | -    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
 352 | -    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
 353 | -    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
 354 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
 355 | +    """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 356 | +    medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 357 | +    angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 358 | +    predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), and the clips' seconds inside crange
 359 | +    (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
 360 | +    earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
 361 | +    seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
 362 | +    ONE channel may give two clips, from two different videos. None if impossible."""
 363 | +    lo, hi = crange or medley_content_range()
 364 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 365 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 366 |      hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 367 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 368 |      for h in hooks:
 369 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 370 | -                and m["channel_id"] != h["channel_id"]]
 371 | +                and (repeat_ok or m["channel_id"] != h["channel_id"])]
 372 |          best = None
 373 | -        for n in (3, 2):
 374 | -            lo, hi = content_range(n)
 375 | +        for n in range(clips[0], clips[1] + 1):
 376 |              for combo in itertools.combinations(pool, n):
 377 | -                if len({m["channel_id"] for m in combo}) != n:
 378 | +                chans = [m["channel_id"] for m in (h, *combo)]
 379 | +                if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
 380 | +                                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
 381 |                      continue
 382 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
 383 |                      continue
 384 | -                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
 385 | +                order = sorted(combo, key=lambda m: pos[m["moment_id"]])
 386 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
 387 |                      continue
 388 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
 389 |                  if not lo <= dur <= hi:
 390 |                      continue
 391 | -                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
 392 | +                key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
 393 |                  if best is None or key > best[0]:
 394 |                      best = (key, [h] + order)
 395 | -            if best:
 396 | -                return best[1]
 397 | +        if best:
 398 | +            return best[1]
 399 |      return None
 400 |  
 401 |  
 402 | @@ -489,9 +575,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 403 |          r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
 404 |                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 405 |          v = json.loads(r.text.strip())
 406 | -        labels = [sg["label"] for sg in pk["segments"]]
 407 | +        labs = [sg["label"] for sg in pk["segments"]]
 408 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 409 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
 410 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 411 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 412 |              raise ValueError("coherence verdict out of contract")
 413 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 414 | @@ -515,39 +601,133 @@ def _lineup_block(segs, ctx, a_by):
 415 |      return "\n".join(out)
 416 |  
 417 |  
 418 | -def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
 419 | +def joins(labs):
 420 | +    """The joins of a medley in play order: "<label> -> <next label>"; join k follows segment k (k = 0 is the hook)."""
 421 | +    return [f"{a} -> {b}" for a, b in zip(labs, labs[1:])]
 422 | +
 423 | +
 424 | +def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 425 | +    """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
 426 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
 427 | +    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
 428 | +    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
 429 | +    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
 430 | +    import providers as P
 431 | +    labs = labels(len(segs))
 432 | +    js = joins(labs)
 433 | +    clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 434 | +                      for lb, m in zip(labs, segs))
 435 | +    r = None
 436 | +    try:
 437 | +        r = router.call("coherence_verdict",
 438 | +                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
 439 | +                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 440 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 441 | +        v = json.loads(r.text.strip())
 442 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 443 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 444 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 445 | +                not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
 446 | +                any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 447 | +                    or not isinstance(x["why"], str) for x in v["joins"].values()):
 448 | +            raise ValueError("clips-alone verdict out of contract")
 449 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 450 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 451 | +            router.reject(r)
 452 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 453 | +    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 454 | +    flagged = [j for j in js if v["joins"][j]["followable"] is False]
 455 | +    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 456 | +        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 457 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 458 | +                    replayed=bool(getattr(r, "replayed", False)))
 459 | +
 460 | +
 461 | +def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 462 | +    """L-y: ONE takeaway (host commentary, class D), ONE title, ONE caption, and a bridge ONLY at `join` (k, why), the
 463 | +    one join the clips-alone verdict flagged (L-y 2): the writer gives it with its reason, or null when it judges a
 464 | +    viewer can follow the jump. The takeaway's word budget lands the factory's estimate (takeaway_budget()).
 465 | +    -> (reply, fields) with fields["bridge_after"] = k when a bridge is given."""
 466 |      from select_by_id import UNTRUSTED
 467 |      from story_semantics import quote_data
 468 |      content = sum(m["duration_s"] for m in segs)
 469 | -    nb = len(segs) - 2
 470 | -    iw, bw, (lo, hi) = budgets(content, nb)
 471 | -    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
 472 | +    budget = takeaway_budget(content, other) or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)
 473 | +    labs = labels(len(segs))
 474 | +    ask, shape = "", "null"
 475 | +    if join is not None:
 476 | +        k, why = join
 477 | +        ask = BRIDGE_ASK.format(a=labs[k].upper().replace("_", " "), b=labs[k + 1].upper().replace("_", " "),
 478 | +                                why=" ".join(quote_data(why, 300).replace('"', "'").split()), n=LY_BRIDGE_WORDS)
 479 | +        shape = '{"text": "...", "cites": ["id"], "why": "..."} or null'
 480 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 481 | -    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 482 | -                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
 483 | -                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
 484 | -                             extra=(extra + "\n") if extra else "")
 485 | +    prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 486 | +                             lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 487 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 488 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 489 |      try:
 490 |          obj = json.loads(r.text.strip())
 491 |          ids = [m["moment_id"] for m in segs]
 492 | -        keys = {"intro", "bridges", "title", "caption"}
 493 | +        keys = {"takeaway", "bridge", "title", "caption"}
 494 |          if not isinstance(obj, dict) or set(obj) != keys:
 495 |              raise ValueError(f"keys must be exactly {sorted(keys)}")
 496 | -        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
 497 | -            raise ValueError(f"'bridges' must hold {nb} lines")
 498 | -        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
 499 | -                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
 500 | -            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 501 | +        lines = [("takeaway", obj["takeaway"], {"text", "cites"}), ("title", obj["title"], {"text", "cites"}),
 502 | +                 ("caption", obj["caption"], {"text", "cites"})]
 503 | +        if obj["bridge"] is not None:
 504 | +            if join is None:
 505 | +                raise ValueError("no join needs a bridge: 'bridge' must be null (L-y 1)")
 506 | +            lines.append(("bridge", obj["bridge"], {"text", "cites", "why"}))
 507 | +        for slot, ln, want in lines:
 508 | +            if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
 509 |                      not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 510 | -                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
 511 | -                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
 512 | +                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
 513 | +                    ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
 514 | +                raise ValueError(f"{slot}: needs text and cites from the line-up's ids" +
 515 | +                                 (" and a reason" if "why" in want else ""))
 516 |          if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
 517 |              raise ValueError("title <= 70 characters, caption <= 220")
 518 |      except (ValueError, TypeError):
 519 |          router.reject(r)
 520 |          raise
 521 | -    return r, dict(obj, type="moments", angle=angle["angle"], style=style)
 522 | +    return r, dict(obj, bridge_after=join[0] if join is not None and obj["bridge"] is not None else None,
 523 | +                   type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
 524 | +
 525 | +
 526 | +def ly_shape(pk):
 527 | +    """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
 528 | +    last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
 529 | +    with its reason recorded, and every flagged join bridged (else these clips do not sit together); a bridge within
 530 | +    config.BRIDGE_WORD_CAP words; one clip per channel unless pk["supply_exception"] says why not (L-y 4)."""
 531 | +    from config import BRIDGE_WORD_CAP
 532 | +    segs, vo = pk["segments"], pk["vo"]
 533 | +    n_clips = len(segs) - 1
 534 | +    fails = []
 535 | +    if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 536 | +        fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 537 | +    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 538 | +    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 539 | +        fails.append("no takeaway after the last clip (L-y 1)")
 540 | +    js = joins([sg["label"] for sg in segs])
 541 | +    bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
 542 | +    texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]
 543 | +    if len(bridged) != len(texts):
 544 | +        fails.append(f"a line after clips {after[:-1]} that is not at a join between two clips")
 545 | +    if len(texts) > LY_MAX_BRIDGES:
 546 | +        fails.append(f"{len(texts)} bridges (L-y 2: at most {LY_MAX_BRIDGES})")
 547 | +    med = pk.get("medley") or {}
 548 | +    if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 549 | +        fails.append("the clips-alone verdict was not measured (L-y 3)")
 550 | +    elif sorted(bridged) != sorted(med["flagged"]):
 551 | +        fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 552 | +                     f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 553 | +    if texts and not ((pk.get("bridge") or {}).get("why") or "").strip():
 554 | +        fails.append("the bridge's reason is not recorded (L-y 2)")
 555 | +    for t in texts:
 556 | +        if len(t.split()) > BRIDGE_WORD_CAP:
 557 | +            fails.append(f"bridge of {len(t.split())} words (max {BRIDGE_WORD_CAP})")
 558 | +    chans = [sg["channel_id"] for sg in segs]
 559 | +    if len(set(chans)) != len(chans) and not (pk.get("supply_exception") or "").strip():
 560 | +        fails.append("two clips from one channel without the supply exception recorded (L-y 4)")
 561 | +    return not fails, fails
 562 |  
 563 |  
 564 |  def fidelity_segments(pk, a_by):
 565 | @@ -563,7 +743,7 @@ def fidelity_segments(pk, a_by):
 566 |  
 567 |  def cheap_checks(pk, a_by, levels, now):
 568 |      """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
 569 | -    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
 570 | +    runtime, R4, and for a medley the L-y shape. -> (violations, det, dup, rt_ok, r4_res)."""
 571 |      segs_v = fidelity_segments(pk, a_by)
 572 |      lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 573 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 574 | @@ -571,10 +751,13 @@ def cheap_checks(pk, a_by, levels, now):
 575 |      dup = duplicates(pk)
 576 |      rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 577 |      r4_res = r4(pk)
 578 | +    what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
 579 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
 580 | -                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
 581 | +                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change {what} "
 582 |                                                        f"length"}]) + \
 583 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 584 | +    if pk.get("shape") == "medley":
 585 | +        v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 586 |      return v, det, dup, rt_ok, r4_res
 587 |  
 588 |  
 589 | @@ -654,16 +837,43 @@ def _writers(router):
 590 |  
 591 |  
 592 |  def _redo(violations):
 593 | +    """The writer's second try: exactly the failing lines, by the keys the writer returns ("bridge" for the one bridge,
 594 | +    whichever join it sits at)."""
 595 | +    key = {"intro": "bridge", "bridge_1": "bridge"}
 596 |      return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
 597 | -            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 598 | +            "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 599 | +
 600 | +
 601 | +def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None):
 602 | +    """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
 603 | +    the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
 604 | +    passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict."""
 605 | +    line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
 606 | +    rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
 607 | +           "words": len((line.get("text") or "").split()),
 608 | +           "cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") == "takeaway"}),
 609 | +           "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
 610 | +           "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None}
 611 | +    if fid is not None:
 612 | +        ver = fid.get("verdict") or {}
 613 | +        if fid.get("measured") and isinstance(ver.get("violations"), list):
 614 | +            rec["verdict_fail"] = sorted({v["rule"] for v in ver["violations"] if v.get("slot") in ("takeaway", "-")})
 615 | +            rec["passed"] = not rec["cheap_fail"] and not rec["verdict_fail"]
 616 | +        else:
 617 | +            rec["verdict_fail"] = ["NOT MEASURED"]
 618 | +            rec["passed"] = False if rec["cheap_fail"] else None
 619 | +    return rec
 620 |  
 621 |  
 622 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 623 | -          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
 624 | -    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
 625 | -    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
 626 | -    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
 627 | -    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
 628 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 629 | +    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 630 | +    item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 631 | +    written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 632 | +    one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 633 | +    work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 634 | +    spend: a callable returning the ledger's USD (dollars per package).
 635 | +    -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 636 |      t0 = time.time()
 637 |      usd0 = spend() if spend else None
 638 |      ms, why = usable(moments, ctx, delivered, optout)
 639 | @@ -671,9 +881,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 640 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 641 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 642 |      levels = current_levels(sources.values(), ctx)
 643 | -    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 644 | +    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 645 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 646 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
 647 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 648 | +           "package": None}
 649 |      log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 650 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 651 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 652 | @@ -685,7 +896,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 653 |      from story_semantics import quote_data
 654 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
 655 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 656 | -    lo, hi = content_range(2)[0], content_range(3)[1]
 657 | +    lo, hi = medley_content_range()
 658 |      angles, angle_reply = None, None
 659 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 660 |          r = None
 661 | @@ -707,25 +918,56 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 662 |      exc, tru = {}, {}
 663 |      with ThreadPoolExecutor(max_workers=8) as pool:
 664 |          for ai, angle in enumerate(angles):
 665 | -            dropped, w_used = set(), 0
 666 | -            while w_used < writes and not out["packages"]:
 667 | -                segs = lineup_for(angle, cleared, frozenset(dropped))
 668 | -                rec = {"angle": ai + 1, "text": angle["angle"],
 669 | -                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
 670 | +            dropped, n_lineup = set(), 0
 671 | +            while n_lineup < lineups and not out["packages"]:
 672 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped)), None
 673 | +                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 674 | +                    segs = lineup_for(angle, cleared, frozenset(dropped), repeat_ok=True)
 675 | +                    if segs is not None:
 676 | +                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 677 | +                               if sum(m["channel_id"] == c for m in segs) > 1]
 678 | +                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 679 | +                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 680 | +                                     f" gives two clips, from two videos (L-y 4)")
 681 | +                rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 682 | +                       "supply_exception": exception, "attempts": []}
 683 |                  out["tried"].append(rec)
 684 |                  if segs is None:
 685 | -                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
 686 | +                    rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 687 |                      break
 688 | +                n_lineup += 1
 689 | +                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 690 | +                rec["medley"] = med
 691 | +                log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 692 | +                    f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 693 | +                    f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 694 | +                labs = labels(len(segs))
 695 | +                if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 696 | +                    by_lab = dict(zip(labs, segs))
 697 | +                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 698 | +                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 699 | +                    if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 700 | +                        weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 701 | +                    if not med.get("measured") or not weak:
 702 | +                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 703 | +                        break
 704 | +                    dropped |= weak
 705 | +                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 706 | +                    continue
 707 | +                join = None
 708 | +                if med["flagged"]:
 709 | +                    k = joins(labs).index(med["flagged"][0])
 710 | +                    join = (k, med["joins"][med["flagged"][0]]["why"])
 711 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 712 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 713 | -                extra, relined = "", False
 714 | +                extra, relined, w_used = "", False, 0
 715 |                  while w_used < writes:
 716 | -                    style = styles[min(w_used, len(styles) - 1)]
 717 |                      w_used += 1
 718 |                      try:
 719 | -                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
 720 | +                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 721 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup)
 722 |                      except Exception as e:
 723 | -                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 724 | +                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 725 |                          continue
 726 |                      writers_v.add(wr.vendor)
 727 |                      writers_f.add(wr.family)
 728 | @@ -740,13 +982,28 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 729 |                              dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 730 |                              relined = True
 731 |                              break
 732 | -                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
 733 | -                                  f"written ({style}), attempt {w_used}")
 734 | +                    if join is not None and fields["bridge"] is None:
 735 | +                        dropped.add(segs[join[0] + 1]["moment_id"])
 736 | +                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 737 | +                                      f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 738 | +                        relined = True
 739 | +                        break
 740 | +                    if fields["bridge"] is not None:
 741 | +                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 742 | +                                                         "backend": med.get("backend")}
 743 | +                    fields["supply_exception"] = exception
 744 | +                    pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 745 | +                                         f"medley (L-y), written, attempt {w_used}")
 746 | +                    pk["medley"] = med
 747 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 748 | -                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
 749 | +                    att = {"writer": wr.backend, "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 750 | +                           "takeaway_budget": fields.get("takeaway_budget"),
 751 |                             "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 752 |                      rec["attempts"].append(att)
 753 | -                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
 754 | +                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 755 | +                    out["takeaways"].append(take)
 756 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 757 | +                        f"words, {pk['runtime_s_estimate']} s): " +
 758 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 759 |                          + f" ({time.time() - t0:.0f} s)")
 760 |                      if cheap:
 761 | @@ -754,11 +1011,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 762 |                          extra = _redo(cheap)
 763 |                          continue
 764 |                      fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 765 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid)
 766 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 767 |                      att["violations"] = fid["violations"] + cx["violations"]
 768 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 769 | -                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
 770 | -                        f"({time.time() - t0:.0f} s)")
 771 | +                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 772 | +                        f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 773 | +                        f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 774 |                      if not fid["ok"] or not cx["ok"]:
 775 |                          if fid["ok"] and not framing:
 776 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 777 | @@ -777,22 +1036,34 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 778 |                          rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
 779 |                          relined = True
 780 |                          break
 781 | -                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
 782 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
 783 |                      att["coherence"] = coh
 784 | -                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
 785 | -                        f"({time.time() - t0:.0f} s)")
 786 | +                    log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 787 | +                        f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 788 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 789 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 790 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 791 | -                                            ok_c, coh)
 792 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 793 |                      if not ok_c:
 794 | -                        rec["why"] = "coherence below 4 or no through-line: next angle"
 795 | -                        w_used = writes
 796 | +                        tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 797 | +                        if coh.get("measured") and type(coh.get("vo_point")) is int and \
 798 | +                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 799 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 800 | +                            extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 801 | +                                            f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 802 | +                                            f"being supported by the clips: land the point the clips make together"}])
 803 | +                            continue                          # the clips hold; only the takeaway's point is weak
 804 | +                        weak = {sg["moment_id"] for sg in pk["segments"][1:]
 805 | +                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 806 | +                        dropped |= weak
 807 | +                        relined = bool(weak)
 808 | +                        rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 809 | +                                      (f"dropped {sorted(weak)}, re-lined" if weak else "next angle"))
 810 |                          break
 811 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
 812 | +                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 813 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 814 |                                      "coherence": coh.get("backend")}
 815 | -                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
 816 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 817 |                      pk["seconds"] = round(time.time() - t0, 1)
 818 |                      pk["usd"] = round(spend() - usd0, 4) if spend else None
 819 |                      out["packages"].append(pk)
 820 | @@ -811,9 +1082,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 821 |      return out
 822 |  
 823 |  
 824 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 825 | -    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
 826 | -    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
 827 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 828 | +    """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 829 | +    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 830 | +    A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 831 | +    (shape=(ok, [why]) from ly_shape())."""
 832 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 833 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 834 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 835 | @@ -861,4 +1134,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 836 |                          measured=all("edges" in t for t in truth.values())),
 837 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 838 |                            **votes_of(coh)),
 839 | +        **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 840 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
 841 | +           if medley is not None else {}),
 842 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 843 | +           if shape is not None else {}),
 844 |      }
 845 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 846 | index 3194dcc1..b1da529b 100644
 847 | --- a/pipeline/package_pin.py
 848 | +++ b/pipeline/package_pin.py
 849 | @@ -25,6 +25,13 @@ from datetime import datetime, timezone
 850 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 851 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 852 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 853 | +MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 854 | +
 855 | +
 856 | +def required_gates(pk):
 857 | +    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 858 | +    clips-alone verdict and the L-y shape."""
 859 | +    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 860 |  
 861 |  
 862 |  class PinRefused(Exception):
 863 | @@ -44,12 +51,12 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 864 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 865 |  
 866 |  
 867 | -def gate_problems(gates):
 868 | +def gate_problems(gates, required=REQUIRED_GATES):
 869 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 870 |      if not isinstance(gates, dict):
 871 |          return ["no gate inventory"]
 872 |      out = []
 873 | -    for g in REQUIRED_GATES:
 874 | +    for g in required:
 875 |          row = gates.get(g)
 876 |          if not isinstance(row, dict) or row.get("status") != "PASS":
 877 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 878 | @@ -58,6 +65,17 @@ def gate_problems(gates):
 879 |      return out
 880 |  
 881 |  
 882 | +def bridge_slots(pk):
 883 | +    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
 884 | +    is the "takeaway" and the one bridge before it is bridge_1."""
 885 | +    vo = pk.get("vo") or {}
 886 | +    after = list(vo.get("bridges_after_clip") or [])
 887 | +    last = len(pk.get("segments") or []) - 1
 888 | +    if pk.get("shape") == "medley":
 889 | +        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
 890 | +    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]
 891 | +
 892 | +
 893 |  def line_problems(pk):
 894 |      """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
 895 |      by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
 896 | @@ -66,8 +84,9 @@ def line_problems(pk):
 897 |      if by.get("intro") != vo.get("intro"):
 898 |          out.append("intro")
 899 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 900 | -    if len(bridges) != len(after) or any(by.get(f"bridge_{i + 1}") != t for i, t in enumerate(bridges)) or \
 901 | -            any(k.startswith("bridge_") and int(k.split("_")[1]) > len(bridges) for k in by if k):
 902 | +    slots = bridge_slots(pk)
 903 | +    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
 904 | +            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
 905 |          out.append("bridges")
 906 |      for k in ("title", "caption"):
 907 |          if by.get(k) != pk.get(k):
 908 | @@ -76,8 +95,8 @@ def line_problems(pk):
 909 |  
 910 |  
 911 |  def to_pin(pk, run_name):
 912 | -    problems = gate_problems(pk.get("gates")) + [f"{x}: the gated line differs from the one shipped"
 913 | -                                                 for x in line_problems(pk)]
 914 | +    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 915 | +                                                                     for x in line_problems(pk)]
 916 |      if problems:
 917 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 918 |      segs = []
 919 | @@ -100,8 +119,13 @@ def to_pin(pk, run_name):
 920 |                                  "signoff_expected": pk["vo"]["signoff"],
 921 |                                  "title": pk["title"], "caption": pk["caption"],
 922 |                                  "hook_first_words": pk["hook_first_words"],
 923 | -                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
 924 | -                                                                   for i in range(len(pk["vo"]["bridges"]))}},
 925 | +                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
 926 | +                                               if pk["vo"]["intro"] else {}),
 927 | +                                            **{s: "takeaway" if s == "takeaway" else "connection"
 928 | +                                               for s in bridge_slots(pk)}},
 929 | +                                "shape": pk.get("shape"),
 930 | +                                "bridge": pk.get("bridge"),
 931 | +                                "supply_exception": pk.get("supply_exception"),
 932 |                                  "gates": pk["gates"],
 933 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 934 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
 935 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 936 | index 67dfd391..b0c948d5 100644
 937 | --- a/pipeline/providers.py
 938 | +++ b/pipeline/providers.py
 939 | @@ -221,6 +221,16 @@ class OpenAIBackend(Backend):
 940 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 941 |  
 942 |  
 943 | +def _num(x):
 944 | +    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x >= 0
 945 | +
 946 | +
 947 | +def _reported(usd):
 948 | +    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
 949 | +    the price-table estimate for it, labelled as an estimate)."""
 950 | +    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}
 951 | +
 952 | +
 953 |  class HeimdallBackend(OpenAIBackend):
 954 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
 955 |      words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
 956 | @@ -246,7 +256,8 @@ class HeimdallBackend(OpenAIBackend):
 957 |              text = j["choices"][0]["message"].get("content") or ""
 958 |          except (KeyError, IndexError, TypeError):
 959 |              raise RequestRejected("heimdall: no choices") from None
 960 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 961 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
 962 | +                          **_reported(u.get("cost"))), time.time() - t0
 963 |  
 964 |      def credits(self):
 965 |          """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
 966 | @@ -285,8 +296,9 @@ class XAIBackend(Backend):
 967 |              text = j["choices"][0]["message"].get("content") or ""
 968 |          except (KeyError, IndexError, TypeError):
 969 |              raise RequestRejected("xai: no choices") from None
 970 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
 971 | -            time.time() - t0
 972 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
 973 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning},
 974 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
 975 |  
 976 |  
 977 |  class AnthropicBackend(Backend):
 978 | @@ -575,6 +587,13 @@ class Router:
 979 |                  r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
 980 |                  r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
 981 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
 982 | +                if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
 983 | +                    rep = float(usage["usd_reported"])
 984 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
 985 | +                             reported_calls=b.get("reported_calls", 0) + 1)
 986 | +                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
 987 | +                else:                                  # no vendor figure: the estimate stands for this call
 988 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
 989 |              self._save(d)
 990 |  
 991 |      def reject(self, reply, why=""):
 992 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 993 | index 4535455d..7a41a3a3 100644
 994 | --- a/tests/moments/test_moments.py
 995 | +++ b/tests/moments/test_moments.py
 996 | @@ -129,13 +129,6 @@ class TestPackageUsable(unittest.TestCase):
 997 |          self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
 998 |                                                  "Go follow them for more. Links are below.")
 999 |  
1000 | -    def test_the_plain_title_never_cuts_a_name(self):
1001 | -        ctx = E.Context(NOW, REG)
1002 | -        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
1003 | -                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
1004 | -        title = PK.plain_vo(segs, ctx)[2]["text"]
1005 | -        self.assertLessEqual(len(title), 70)
1006 | -        self.assertTrue(title.endswith(("and others", "Two", "One")), title)
1007 |  
1008 |  
1009 |  if __name__ == "__main__":
1010 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
1011 | new file mode 100644
1012 | index 00000000..eecc07fa
1013 | --- /dev/null
1014 | +++ b/tests/package/proof_ly.py
1015 | @@ -0,0 +1,203 @@
1016 | +#!/usr/bin/env python3
1017 | +"""ORCHESTRATOR ORDER 20:30 ET Nov 12 (law L-y, VOICEOVER IS MINIMAL): re-run tonight's universe and the saved ones
1018 | +through the packager's new default, the MEDLEY (pipeline/package.py build()). The table goes to the top of STATE:
1019 | +- packages per universe;
1020 | +- how many needed zero bridges and how many needed one;
1021 | +- the gate pass rate on the single takeaway line;
1022 | +- time and dollars per package.
1023 | +The top package of the newest universe becomes a sealed pin (MOMENTS_PIN_LY.json).
1024 | +
1025 | +LEGS (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"). The probe at
1026 | +20:32 ET found Anthropic "credit balance is too low" (HTTP 400) and OpenAI 429 credit_balance_exhausted, so both stay
1027 | +out. Local gemma runs on GPU0, which this builder never uses (L-r, the session's standing order), so every local leg
1028 | +is out too. What is left:
1029 | +- the writer (angle + takeaway) is Heimdall: deepseek-v4.1-flash, then qwen3.8-27b. This is the config's own
1030 | +  angle_write order once the frozen vendors drop out.
1031 | +- every verdict avoids the writer's vendor (L-x), so it runs on xAI grok-4.20.
1032 | +- the second recogniser is ElevenLabs scribe_v1.
1033 | +CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
1034 | +
1035 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
1036 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
1037 | +estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
1038 | +
1039 | +Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
1040 | +"""
1041 | +import argparse
1042 | +import hashlib
1043 | +import json
1044 | +import os
1045 | +import subprocess
1046 | +import sys
1047 | +import time
1048 | +
1049 | +HERE = os.path.dirname(os.path.abspath(__file__))
1050 | +REPO = os.path.dirname(os.path.dirname(HERE))
1051 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1052 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1053 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1054 | +import moments as M  # noqa: E402
1055 | +import package as PK  # noqa: E402
1056 | +import package_pin  # noqa: E402
1057 | +import proof_moments as PM  # noqa: E402
1058 | +import providers as P  # noqa: E402
1059 | +
1060 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
1061 | +OUT = os.path.join(HERE, "proof")
1062 | +SPEND = os.path.join(OUT, "SPEND_LY.json")
1063 | +LY_LIMIT_USD = 15.0                # the price-table estimate (an upper bound; xAI's own figure ran ~1/7 of it, 05:30)
1064 | +TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
1065 | +RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
1066 | +        "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
1067 | +        "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
1068 | +NEWEST = RUNS[0]
1069 | +FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
1070 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
1071 | +SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
1072 | +
1073 | +
1074 | +def chains():
1075 | +    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
1076 | +    cfg = json.load(open(P.CONFIG))
1077 | +    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
1078 | +    out["angle_write"] = list(WRITERS)
1079 | +    return out
1080 | +
1081 | +
1082 | +def ledger():
1083 | +    try:
1084 | +        d = json.load(open(SPEND))
1085 | +    except (OSError, ValueError):
1086 | +        d = {}
1087 | +    est = float(d.get("usd_estimate", 0.0))
1088 | +    best = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
1089 | +    return est, best, d
1090 | +
1091 | +
1092 | +def code_sha():
1093 | +    """The code this run used: HEAD plus the working tree's diff of pipeline/ and this driver (the results name it)."""
1094 | +    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
1095 | +    diff = subprocess.run(["git", "-C", REPO, "diff", "HEAD", "--", "pipeline", "tests/package"], capture_output=True).stdout
1096 | +    return f"{head}+{hashlib.sha256(diff).hexdigest()[:12]}" if diff else head
1097 | +
1098 | +
1099 | +def run_one(run, router, work_dir, log):
1100 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
1101 | +    words, captions, ctx, saved = PM.universe_sources(run)
1102 | +    sources = {s.video_id: s for s in words}
1103 | +    e0, b0, _ = ledger()
1104 | +    t0 = time.time()
1105 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
1106 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a.json"), spend=lambda: ledger()[0])
1107 | +    e1, b1, _ = ledger()
1108 | +    res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
1109 | +               usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
1110 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
1111 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
1112 | +    if res["package"]:
1113 | +        pk = res["package"]
1114 | +        pk["usd_best_known"] = res["usd_best_known"]
1115 | +        path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name="MOMENTS_PIN_LY.json")
1116 | +        res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1117 | +                      "package_sha256": pin["moments_package"]["package_sha256"]}
1118 | +        log(f"{run}: PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known)"
1119 | +            f" pin {path}")
1120 | +    else:
1121 | +        log(f"{run}: no package ({res.get('why_none')}); usable {res['usable']}, cleared "
1122 | +            f"{res['prescreen']['cleared']}")
1123 | +    json.dump(res, open(os.path.join(OUT, run, "package_ly.json"), "w"), indent=1, default=str)
1124 | +    return res
1125 | +
1126 | +
1127 | +def table():
1128 | +    rows = ["| universe | usable / cleared step A | line-ups judged on the clips alone (passed) | package | segments, "
1129 | +            "seconds of clips | bridges | takeaway writes: passed / judged (first write) | runtime estimate | time | "
1130 | +            "$ estimate / $ best known | why none |", "|---|---|---|---|---|---|---|---|---|---|---|"]
1131 | +    tot = {"universes": 0, "packages": 0, "zero": 0, "one": 0, "passed": 0, "judged": 0, "first_passed": 0,
1132 | +           "first_judged": 0, "s": [], "est": [], "best": []}
1133 | +    for run in RUNS:
1134 | +        f = os.path.join(OUT, run, "package_ly.json")
1135 | +        if not os.path.exists(f):
1136 | +            rows.append(f"| {run} | not run | | | | | | | | | |")
1137 | +            continue
1138 | +        r = json.load(open(f))
1139 | +        tot["universes"] += 1
1140 | +        tried = [t for t in r.get("tried") or [] if t.get("medley") is not None]
1141 | +        med_ok = sum(1 for t in tried if t["medley"].get("measured") and
1142 | +                     len(t["medley"].get("flagged") or []) <= PK.LY_MAX_BRIDGES and t.get("attempts"))
1143 | +        takes = r.get("takeaways") or []
1144 | +        judged = [x for x in takes if x.get("passed") is not None]
1145 | +        firsts = [x for x in judged if x.get("write") == 1]
1146 | +        tot["passed"] += sum(1 for x in judged if x["passed"])
1147 | +        tot["judged"] += len(judged)
1148 | +        tot["first_passed"] += sum(1 for x in firsts if x["passed"])
1149 | +        tot["first_judged"] += len(firsts)
1150 | +        pk = r.get("package")
1151 | +        if pk:
1152 | +            nb = 0 if not pk.get("bridge") else 1
1153 | +            tot["packages"] += 1
1154 | +            tot["zero" if nb == 0 else "one"] += 1
1155 | +            tot["s"].append(r["seconds"])
1156 | +            tot["est"].append(r.get("usd_estimate") or 0.0)
1157 | +            tot["best"].append(r.get("usd_best_known") or 0.0)
1158 | +            segs = f"{len(pk['segments'])}, {sum(s['duration_s'] for s in pk['segments']):.1f} s"
1159 | +            bridge = "0" if nb == 0 else f"1 ({pk['bridge']['join']}: {pk['bridge']['why']})".replace("|", "/")
1160 | +            pkg, rt, why = f"YES: \"{pk['title']}\"".replace("|", "/"), f"{pk['runtime_s_estimate']} s", ""
1161 | +        else:
1162 | +            segs = bridge = rt = "-"
1163 | +            pkg = "no"
1164 | +            why = (r.get("why_none") or "; ".join(f"angle {t['angle']}: {t.get('why') or '-'}" for t in r.get("tried") or [])
1165 | +                   )[:240].replace("|", "/")
1166 | +        rows.append(f"| {run} | {r['usable']} / {r['prescreen']['cleared']} | {len(tried)} ({med_ok}) | {pkg} | {segs} | "
1167 | +                    f"{bridge} | {sum(1 for x in judged if x['passed'])} / {len(judged)} "
1168 | +                    f"({sum(1 for x in firsts if x['passed'])} / {len(firsts)}) | {rt} | {r['seconds']} s | "
1169 | +                    f"${r.get('usd_estimate')} / ${r.get('usd_best_known')} | {why} |")
1170 | +    n = tot["packages"]
1171 | +    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
1172 | +    _, _, d = ledger()
1173 | +    summary = (f"\n**Totals:**\n"
1174 | +               f"- {tot['universes']} universes run; {n} packages.\n"
1175 | +               f"- Bridges: {tot['zero']} packages needed none, {tot['one']} needed one.\n"
1176 | +               f"- The takeaway line passed its gates in {tot['passed']} of {tot['judged']} judged writes "
1177 | +               f"({tot['first_passed']} of {tot['first_judged']} on the first write).\n"
1178 | +               f"- Per package: {mean(tot['s']):.0f} s mean, ${mean(tot['est']):.2f} estimate, "
1179 | +               f"${mean(tot['best']):.2f} best known.\n"
1180 | +               f"- This order's ledger: ${d.get('usd_estimate', 0):.2f} estimate; vendor-reported "
1181 | +               f"${d.get('usd_reported', 0):.4f} + unreported calls' estimate ${d.get('usd_unreported_estimate', 0):.2f}.\n")
1182 | +    text = ("# pp-selectid: the L-y medley re-run (generated by tests/package/proof_ly.py --table)\n\n" +
1183 | +            "\n".join(rows) + "\n" + summary)
1184 | +    open(TABLE, "w").write(text)
1185 | +    return text
1186 | +
1187 | +
1188 | +def main(argv=None):
1189 | +    ap = argparse.ArgumentParser()
1190 | +    ap.add_argument("--runs", nargs="+", default=list(RUNS))
1191 | +    ap.add_argument("--table", action="store_true", help="only (re)write the table from the saved results")
1192 | +    ap.add_argument("--work-dir", default=os.path.join(SCRATCH, "lv2"))
1193 | +    a = ap.parse_args(argv)
1194 | +    if a.table:
1195 | +        print(table())
1196 | +        return 0
1197 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
1198 | +    os.makedirs(a.work_dir, exist_ok=True)
1199 | +    for run in a.runs:
1200 | +        os.makedirs(os.path.join(OUT, run), exist_ok=True)
1201 | +        logf = open(os.path.join(OUT, run, "package_ly.log"), "a")
1202 | +        say = lambda s: (print(f"[{run}] {s}", flush=True), logf.write(s + "\n"), logf.flush())
1203 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} L-y medley build, code {code_sha()}, chains {json.dumps(router.chains)}")
1204 | +        try:
1205 | +            run_one(run, router, a.work_dir, say)
1206 | +        except P.SpendLimit as e:
1207 | +            say(f"STOPPED: {e}")
1208 | +            break
1209 | +        finally:
1210 | +            logf.close()
1211 | +    if router.notices:
1212 | +        print("NOTICES:", router.notices)
1213 | +    print(table())
1214 | +    return 0
1215 | +
1216 | +
1217 | +if __name__ == "__main__":
1218 | +    sys.exit(main())
1219 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1220 | new file mode 100644
1221 | index 00000000..e340eaca
1222 | --- /dev/null
1223 | +++ b/tests/package/test_medley.py
1224 | @@ -0,0 +1,359 @@
1225 | +#!/usr/bin/env python3
1226 | +"""L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12): the packager's MEDLEY, offline.
1227 | +
1228 | +- The arithmetic: the clips' seconds that let ONE takeaway land the factory's estimate in 60-70 s, and the takeaway's
1229 | +  word budget, which lands it there.
1230 | +- The line-up: the hook + 2-4 clips in the proposer's play order, one per channel (a repeat only as the recorded supply
1231 | +  exception).
1232 | +- The clips-ALONE verdict's contract.
1233 | +- The writer's contract: a bridge only at the flagged join.
1234 | +- ly_shape's must-fail cases.
1235 | +- The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
1236 | +"""
1237 | +import json
1238 | +import os
1239 | +import sys
1240 | +import unittest
1241 | +
1242 | +HERE = os.path.dirname(os.path.abspath(__file__))
1243 | +REPO = os.path.dirname(os.path.dirname(HERE))
1244 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1245 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1246 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1247 | +sys.path.insert(0, HERE)
1248 | +import eligibility as E  # noqa: E402
1249 | +import package as PK  # noqa: E402
1250 | +import package_pin  # noqa: E402
1251 | +from config import BRIDGE_WORD_CAP  # noqa: E402
1252 | +from test_eligibility import NOW, REG  # noqa: E402
1253 | +from test_gates import Canned  # noqa: E402
1254 | +from test_moments import pm  # noqa: E402
1255 | +
1256 | +W = lambda n: " ".join(["word"] * n)
1257 | +
1258 | +
1259 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
1260 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
1261 | +
1262 | +
1263 | +def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
1264 | +    js = PK.joins(labs)
1265 | +    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
1266 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
1267 | +                          if j in flagged else "same subject"} for j in js}}
1268 | +
1269 | +
1270 | +def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
1271 | +    """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
1272 | +    labs = PK.labels(n)
1273 | +    segs = [{"label": lb, "channel_id": (chans or "ABCDEFG")[i], "duration_s": 12.0, "text": f"Bitcoin {lb}."}
1274 | +            for i, lb in enumerate(labs)]
1275 | +    bridges, aft = (["B " + W(5)] if bridge else []) + [W(20)], ([after] if bridge else []) + [n - 1]
1276 | +    return {"shape": "medley", "segments": segs,
1277 | +            "vo": {"intro": intro, "bridges": bridges, "bridges_after_clip": aft, "signoff": "S"},
1278 | +            "medley": {"measured": measured, "flagged": list(flagged)},
1279 | +            "bridge": {"why": bridge} if bridge or intro else None, "supply_exception": supply}
1280 | +
1281 | +
1282 | +class TestMedleyArithmetic(unittest.TestCase):
1283 | +    def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1284 | +        lo, hi = PK.medley_content_range()
1285 | +        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1286 | +        seg = lambda c: [{"duration_s": c}]
1287 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1288 | +        self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1289 | +        lo1, hi1 = PK.medley_content_range(n_bridges=1)
1290 | +        self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1291 | +        self.assertAlmostEqual(hi - hi1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1292 | +
1293 | +    def test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps(self):
1294 | +        aimed = 0
1295 | +        for c10 in range(300, 560):
1296 | +            c = c10 / 10
1297 | +            b = PK.takeaway_budget(c)
1298 | +            if b is None:
1299 | +                self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1300 | +                continue
1301 | +            lo, hi = b
1302 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1303 | +            for w in (lo, hi):
1304 | +                est = PK.runtime([{"duration_s": c}], [W(w)])
1305 | +                self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1306 | +                p = {"segments": [{"duration_s": c, "channel": "A"}, {"duration_s": 0.0, "channel": "B"}],
1307 | +                     "vo": {"intro": None, "bridges": [W(w)], "bridges_after_clip": [1]}, "runtime_s_estimate": est}
1308 | +                self.assertTrue(PK.r4(p)[0], (c, w, PK.r4(p)[1]))
1309 | +            aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1310 | +        self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1311 | +        self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1312 | +        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1313 | +        self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1314 | +
1315 | +
1316 | +class TestMedleyLineup(unittest.TestCase):
1317 | +    def test_the_hook_and_clips_in_the_proposers_order_one_per_channel(self):
1318 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1319 | +                                          pm("z", "D", 12.0), pm("e", "A", 14.0))}
1320 | +        seg = PK.lineup_for(angle(["h", "y", "x", "z", "e"], "h"), by)
1321 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "y", "x"])        # the earliest that fit, in that order
1322 | +        self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1323 | +
1324 | +    def test_more_clips_when_two_do_not_fill_the_medley(self):
1325 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1326 | +        seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1327 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1328 | +        short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1329 | +        self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1330 | +
1331 | +    def test_a_channel_twice_only_as_the_supply_exception_and_from_two_videos(self):
1332 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0),
1333 | +                                          pm("e", "A", 13.0))}
1334 | +        a = angle(["h", "x", "y", "e"], "h")
1335 | +        self.assertIsNone(PK.lineup_for(a, by))                                    # one per channel cannot fill it
1336 | +        seg = PK.lineup_for(a, by, repeat_ok=True)
1337 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "e"])
1338 | +        same_video = dict(by, e=dict(by["e"], video_id=by["h"]["video_id"]))
1339 | +        self.assertIsNone(PK.lineup_for(a, same_video, repeat_ok=True))           # never two clips of one video
1340 | +
1341 | +
1342 | +class TestClipsAloneVerdict(unittest.TestCase):
1343 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1344 | +    LABS = ["hook", "clip_01", "clip_02"]
1345 | +
1346 | +    def run_it(self, reply):
1347 | +        r = Canned(coherence_verdict=[reply])
1348 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1349 | +        return ok, v, r
1350 | +
1351 | +    def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
1352 | +        r = Canned(coherence_verdict=[verdict(self.LABS)])
1353 | +        prompts = []
1354 | +        call = r.call
1355 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1356 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1357 | +        self.assertTrue(ok)
1358 | +        self.assertEqual(v["flagged"], [])
1359 | +        self.assertNotIn("VOICE-OVER", prompts[0])
1360 | +        self.assertNotIn("TITLE", prompts[0])
1361 | +        self.assertIn('"hook -> clip_01"', prompts[0])
1362 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
1363 | +
1364 | +    def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
1365 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
1366 | +        self.assertTrue(ok)
1367 | +        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
1368 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
1369 | +        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
1370 | +
1371 | +    def test_no_through_line_or_a_weak_clip_fails(self):
1372 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
1373 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
1374 | +        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
1375 | +
1376 | +    def test_out_of_contract_is_not_measured_and_rejected(self):
1377 | +        good = verdict(self.LABS)
1378 | +        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
1379 | +                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
1380 | +                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
1381 | +                    dict(good, vo_point=5),
1382 | +                    dict(good, clips={"hook": 5, "clip_01": 5})):
1383 | +            ok, v, r = self.run_it(bad)
1384 | +            self.assertFalse(ok)
1385 | +            self.assertFalse(v["measured"])
1386 | +            self.assertIsNone(v["flagged"])
1387 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1388 | +
1389 | +
1390 | +class TestWriteTakeaway(unittest.TestCase):
1391 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1392 | +
1393 | +    def write(self, reply, join=None):
1394 | +        r = Canned(angle_write=[reply])
1395 | +        return PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {}, join), r
1396 | +
1397 | +    def lines(self, bridge=None):
1398 | +        return {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": bridge,
1399 | +                "title": {"text": "No ruler.", "cites": ["h"]}, "caption": {"text": "three clips", "cites": []}}
1400 | +
1401 | +    def test_no_bridge_unless_a_join_was_flagged(self):
1402 | +        (rep, f), _ = self.write(self.lines())
1403 | +        self.assertIsNone(f["bridge_after"])
1404 | +        with self.assertRaises(ValueError):
1405 | +            self.write(self.lines({"text": "Next, B.", "cites": ["x"], "why": "w"}))
1406 | +
1407 | +    def test_a_bridge_at_the_flagged_join_needs_its_reason_and_may_be_declined(self):
1408 | +        (rep, f), _ = self.write(self.lines({"text": "Next, B's show on keys.", "cites": ["x"], "why": "no referent"}),
1409 | +                                 join=(1, "the next speaker's 'it' has no referent"))
1410 | +        self.assertEqual(f["bridge_after"], 1)
1411 | +        (rep, f), _ = self.write(self.lines(None), join=(1, "w"))
1412 | +        self.assertIsNone(f["bridge_after"])                                       # declined: build re-lines
1413 | +        for bad in ({"text": "Next.", "cites": ["x"]}, {"text": "Next.", "cites": ["x"], "why": " "},
1414 | +                    {"text": "Next.", "cites": ["zz"], "why": "w"}):
1415 | +            with self.assertRaises(ValueError):
1416 | +                self.write(self.lines(bad), join=(1, "w"))
1417 | +
1418 | +    def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1419 | +        r = Canned(angle_write=[self.lines()])
1420 | +        prompts = []
1421 | +        call = r.call
1422 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1423 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1424 | +        lo, hi = PK.takeaway_budget(39.0)
1425 | +        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1426 | +        self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1427 | +        self.assertNotIn('"intro"', prompts[0])
1428 | +
1429 | +
1430 | +class TestLyShape(unittest.TestCase):
1431 | +    def test_a_clean_medley_passes(self):
1432 | +        self.assertEqual(PK.ly_shape(medley_pk()), (True, []))
1433 | +        self.assertTrue(PK.ly_shape(medley_pk(n=5))[0])
1434 | +
1435 | +    def test_a_bridge_only_and_always_at_the_flagged_join_with_its_reason(self):
1436 | +        self.assertTrue(PK.ly_shape(medley_pk(n=4, bridge="no referent", after=2, flagged=["clip_02 -> clip_03"]))[0])
1437 | +        self.assertTrue(PK.ly_shape(medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1438 | +            "bridge": {"why": "no referent"}})[0])
1439 | +        must_fail = {
1440 | +            "bridge at an unflagged join": medley_pk(n=4, bridge="w", after=1, flagged=["clip_02 -> clip_03"]),
1441 | +            "bridge with nothing flagged": medley_pk(n=4, bridge="w", after=1),
1442 | +            "flagged join left unbridged": medley_pk(flagged=["clip_01 -> clip_02"]),
1443 | +            "bridge without its reason": medley_pk(n=4, bridge="", after=2, flagged=["clip_02 -> clip_03"]) | {
1444 | +                "vo": medley_pk(n=4, bridge="w", after=2)["vo"]},
1445 | +            "an intro with nothing flagged": medley_pk(intro="Here's the thing.") | {"bridge": {"why": "w"}},
1446 | +            "two bridges": medley_pk(n=4, intro="Next.", bridge="w", after=2,
1447 | +                                     flagged=["hook -> clip_01", "clip_02 -> clip_03"]),
1448 | +            "verdict not measured": medley_pk(measured=False),
1449 | +            "verdict missing": medley_pk() | {"medley": None},
1450 | +        }
1451 | +        for why, pk in must_fail.items():
1452 | +            self.assertFalse(PK.ly_shape(pk)[0], why)
1453 | +
1454 | +    def test_the_takeaway_is_the_line_after_the_last_clip(self):
1455 | +        pk = medley_pk()
1456 | +        pk["vo"] = dict(pk["vo"], bridges_after_clip=[1])
1457 | +        self.assertFalse(PK.ly_shape(pk)[0])
1458 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1459 | +        self.assertFalse(PK.ly_shape(pk)[0])
1460 | +
1461 | +    def test_three_to_five_segments_and_one_clip_per_channel(self):
1462 | +        self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1463 | +        self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1464 | +        self.assertFalse(PK.ly_shape(medley_pk(chans="ABA"))[0])
1465 | +        self.assertTrue(PK.ly_shape(medley_pk(chans="ABA", supply="A gives two clips (L-y 4)"))[0])
1466 | +
1467 | +    def test_a_bridge_over_the_word_cap_fails(self):
1468 | +        pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
1469 | +        pk["vo"]["bridges"][0] = W(BRIDGE_WORD_CAP + 1)
1470 | +        self.assertFalse(PK.ly_shape(pk)[0])
1471 | +
1472 | +
1473 | +def ctx():
1474 | +    return E.Context(NOW, REG)
1475 | +
1476 | +
1477 | +class TestMedleyPackageAndPin(unittest.TestCase):
1478 | +    def build(self, bridge=None, k=None, n=3, text="No ruler, just rules nobody gets to bend."):
1479 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1480 | +                                          pm("z", "D", 9.0))}
1481 | +        order = ["h", "x", "y", "z"][:n]
1482 | +        fields = {"takeaway": {"text": text, "cites": []}, "bridge": bridge, "bridge_after": k,
1483 | +                  "title": {"text": "No ruler.", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1484 | +        return PK.assemble_medley(order, by, fields, ctx(), "medley (L-y)")
1485 | +
1486 | +    def gates(self, pk, **over):
1487 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
1488 | +        g.update(over)
1489 | +        return g
1490 | +
1491 | +    def test_no_intro_and_one_takeaway_after_the_last_clip(self):
1492 | +        pk = self.build()
1493 | +        self.assertIsNone(pk["vo"]["intro"])
1494 | +        self.assertEqual((pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]),
1495 | +                         (["No ruler, just rules nobody gets to bend."], [2]))
1496 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["takeaway", "title", "caption"])
1497 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1498 | +        self.assertEqual(PK.r4(pk)[0], True)
1499 | +
1500 | +    def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1501 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1502 | +        pk = self.build(bridge=b, k=1, n=4)
1503 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 3])
1504 | +        self.assertEqual([x["slot"] for x in pk["lines"]][:2], ["bridge_1", "takeaway"])
1505 | +        self.assertEqual(pk["bridge"]["join"], "clip_01 -> clip_02")
1506 | +        pk0 = self.build(bridge=b, k=0)
1507 | +        self.assertEqual(pk0["vo"]["intro"], "Next, on keys.")
1508 | +        self.assertEqual(pk0["vo"]["bridges_after_clip"], [2])
1509 | +        with self.assertRaises(ValueError):
1510 | +            self.build(bridge=b, k=2)                     # after the last clip is the takeaway's place
1511 | +
1512 | +    def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1513 | +        pk = self.build()
1514 | +        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1515 | +        pk["gates"] = self.gates(pk)
1516 | +        pin = package_pin.to_pin(pk, "test")
1517 | +        mp = pin["moments_package"]
1518 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1519 | +        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1520 | +        self.assertEqual(mp["shape"], "medley")
1521 | +        for missing in ("medley", "ly_shape"):
1522 | +            g = self.gates(pk)
1523 | +            g.pop(missing)
1524 | +            with self.assertRaises(package_pin.PinRefused):
1525 | +                package_pin.to_pin(dict(pk, gates=g), "test")
1526 | +        with self.assertRaises(package_pin.PinRefused):
1527 | +            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
1528 | +
1529 | +    def test_the_gated_takeaway_must_be_the_spoken_one(self):
1530 | +        pk = self.build()
1531 | +        pk["gates"] = self.gates(pk)
1532 | +        pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
1533 | +        with self.assertRaises(package_pin.PinRefused) as cm:
1534 | +            package_pin.to_pin(pk, "test")
1535 | +        self.assertIn("bridges", str(cm.exception))
1536 | +
1537 | +    def test_the_old_shape_keeps_its_slots(self):
1538 | +        pk = {"vo": {"intro": "I", "bridges": ["B", "T"], "bridges_after_clip": [1, 2]}, "segments": [{}, {}, {}]}
1539 | +        self.assertEqual(package_pin.bridge_slots(pk), ["bridge_1", "bridge_2"])
1540 | +        self.assertEqual(package_pin.bridge_slots(dict(pk, shape="medley")), ["bridge_1", "takeaway"])
1541 | +
1542 | +
1543 | +class TestInventoryRows(unittest.TestCase):
1544 | +    def test_the_two_medley_rows(self):
1545 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
1546 | +               "backend": "x", "replayed": False, "measured": True}
1547 | +        coh = {"backend": "x", "replayed": False, "measured": True}
1548 | +        args = (fid, [], True, (True, ""), {"ok": True, "measured": True, "replayed": False, "backends": {}},
1549 | +                {"hook": {"backend": "x", "replayed": False}}, {"h": {"verdict": "keep", "measured": True,
1550 | +                                                                      "replayed": False}},
1551 | +                {"h": {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "s"}}, True, coh)
1552 | +        self.assertNotIn("medley", PK.inventory(*args))
1553 | +        g = PK.inventory(*args, medley=(True, {"backend": "x", "replayed": False, "measured": True, "flagged": []}),
1554 | +                         shape=(True, []))
1555 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("PASS", "PASS"))
1556 | +        g = PK.inventory(*args, medley=(False, {"measured": False, "flagged": None}), shape=(False, ["two bridges"]))
1557 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("NOT RUN", "FAIL"))
1558 | +        self.assertEqual(g["ly_shape"]["why"], ["two bridges"])
1559 | +
1560 | +
1561 | +class TestReportedCost(unittest.TestCase):
1562 | +    def test_the_ledger_keeps_the_vendors_own_figure_beside_the_estimate(self):
1563 | +        import tempfile
1564 | +        import providers as P
1565 | +        with tempfile.TemporaryDirectory() as d:
1566 | +            path = os.path.join(d, "SPEND.json")
1567 | +            r = P.Router(env_path=None, spend_path=path, limit_usd=10.0)
1568 | +            b = r.backends["xai:grok-4.20-0309-reasoning"]
1569 | +            r._settle(None, b, {"in": 1000, "out": 1000, "usd_reported": 0.002}, 0.03, "check")
1570 | +            r._settle(None, b, {"in": 1000, "out": 1000}, 0.03, "check")
1571 | +            led = json.load(open(path))
1572 | +            self.assertAlmostEqual(led["usd_estimate"], 0.06, places=6)
1573 | +            self.assertAlmostEqual(led["usd_reported"], 0.002, places=8)
1574 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.03, places=6)
1575 | +            self.assertEqual(led["by_backend"][b.name]["reported_calls"], 1)
1576 | +        self.assertEqual(P._reported(None), {})
1577 | +        self.assertEqual(P._reported(True), {})
1578 | +        self.assertEqual(P._reported(-1), {})
1579 | +        self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})
1580 | +
1581 | +
1582 | +if __name__ == "__main__":
1583 | +    unittest.main()
1584 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse, moments-first packaging), written 20:30-21:10 ET Nov 12
under the orchestrator's new law L-y. The code gates a video package before a pinned render. Standing laws: nothing
measured is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make something pass;
every model verdict avoids the vendor and model family of any reply whose text it judges (L-x).

LAW L-y VOICEOVER IS MINIMAL (the order, paraphrased exactly):
 1. DEFAULT SHAPE: hook clip -> clip -> clip (-> clip) back to back as a medley, joined by the approved transition, then
    ONE voiceover line at the END (the takeaway) and the sign-off naming every channel. No VO intro after the hook. No
    bridges between clips.
 2. A bridge between two clips is the EXCEPTION, used only when the packager judges, and the blind coherence check
    confirms, that a viewer could not follow the jump without it (the second clip's subject or referent is unclear
    coming from the first). At most ONE bridge per video, as short as it can be, and the package records why it was
    needed. If two or more bridges would be needed, the line-up is wrong: pick clips that sit together.
 3. SELECTION carries the weight: the packager chooses moments that follow from one another WITHOUT narration - each
    clip's opening must make sense after the previous clip's ending, in the speaker's own words. The coherence verdict
    is asked on the clips ALONE first ("played back to back with no narration, is there a through-line a viewer can
    state?"), and only then on the takeaway.
 4. Runtime: 3 to 5 clips, the measured final 58-72 s accepted, target 60-70 (the packaging estimate stays inside
    60-70). Per-clip duration targets stay targets. One clip per channel still holds unless the supply forces
    otherwise (then say so in the package).
 5. The takeaway is host commentary (class D): one or two sentences; it is still gated (VO fidelity, context
    integrity). The title and caption still carry the angle. The existing caps stay as upper bounds (takeaway 30 words,
    bridge 20 words, VO share <= 45 % of the runtime estimate).
 6. Keep every VO gate.

What changed, and what to check:
1. package.build(): the medley is the default. Per angle up to LY_LINEUPS line-ups; each line-up is judged on the
   clips ALONE first (package.medley) before anything is written; only a passing line-up gets writes
   (write_takeaway); the one bridge is offered to the writer ONLY at the join the clips-alone verdict flagged, and if
   the writer declines it, the line-up is dropped (re-lined); then the cheap gates (incl. ly_shape), the fidelity
   verdict and context integrity, exclusion and the second recognition pass, and last the coherence verdict WITH the
   takeaway. Check the loop control (dropped / relined / next angle), that nothing is written for a line-up whose
   clips alone fail, and that the takeaway's gate results are recorded honestly (_takeaway_record).
2. package.ly_shape(): the code check of L-y on the package. Can a package pass with: an intro when no hook join was
   flagged; a bridge at a join that was not flagged; a flagged join left unbridged; two bridges; no takeaway after the
   last clip; a bridge without its recorded reason; a bridge over 20 words; 2 or 6 segments; two clips of one channel
   without the recorded supply exception; an unmeasured clips-alone verdict?
3. package.medley(): the blind clips-alone verdict. Is its JSON contract strict (exact keys, every consecutive join,
   booleans)? Does the prompt carry NO voice-over and NO title? Is "flagged" right? ok = a stated through-line
   (>= 4 words, not 'none'), every clip >= 4, at most one unfollowable join.
4. package.write_takeaway(): a bridge must be null unless a join was offered; an offered bridge needs text, cites from
   the line-up and a non-empty reason. The takeaway's word budget (takeaway_budget) must land the factory's runtime
   estimate (package.runtime: clips' word spans + each VO line words / 2.5 + 1.0 s + the 14.30 s tail) in 60-70 s and
   respect the 30-word cap and R4's 45 % share. medley_content_range() gives the clips' seconds that allow that.
5. package.lineup_for(): the hook + 2-4 clips in the proposer's play order, one per channel; repeat_ok allows ONE
   channel twice, only from two different videos, and build() uses it only when no one-per-channel line-up exists,
   recording the supply exception.
6. package.assemble_medley() and package_pin.py: intro None (the deployed pinned.py accepts "intro null"); the takeaway
   is the line after the LAST clip (slot "takeaway"); a bridge after the hook is the renderer's intro slot, after clip
   k a bridge after_clip k; required_gates(pk) adds "medley" and "ly_shape" for a medley; line_problems maps the
   slots; the seal is unchanged in form.
7. pipeline/providers.py: the ledger now records the vendor's own cost per call (xAI cost_in_usd_ticks / 1e10,
   Heimdall usage.cost) beside the price-table estimate; the spend guard still reads the estimate. Any way this can
   corrupt the ledger or let spend pass the guard?
8. tests/package/proof_ly.py: the re-run driver. Chains: no local leg (the builder never uses the GPU), no Anthropic /
   OpenAI (out of credit); writer = Heimdall deepseek then qwen; verdicts avoid the writer's vendor, so xAI. Its own
   ledger and cap. The table: packages per universe, zero / one bridge, the takeaway pass rate, time and dollars.
9. Removed: write_v3, STYLES, budgets, plain_vo (intro + bridges shapes, contrary to L-y 1) and plain_vo's title test.
   Does anything still need them?
10. tests/package/test_medley.py: do the must-fail tests prove each rule above?

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".

