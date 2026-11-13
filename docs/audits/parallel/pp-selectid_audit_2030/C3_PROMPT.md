# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2030
# Branch: pp-selectid
# Generated: 2026-11-12 21:19 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2030/C3_STEP.diff (1935 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 51f24c7d..6e83a5d6 100644
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
  88 | @@ -126,6 +138,42 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
  89 |                                     # clip; 60-70 s stays hard
  90 |  
  91 |  
  92 | +LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
  93 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
  94 | +LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
  95 | +                                   # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
  96 | +LY_BRIDGE_MIN_WORDS = 3            # the shortest bridge a first write budgets for ("Next, on keys.")
  97 | +LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
  98 | +LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
  99 | +                                   # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
 100 | +LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
 101 | +
 102 | +
 103 | +def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 104 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 105 | +    n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 106 | +    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 107 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 108 | +    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 109 | +    return round(lo, 2), round(hi, 2)
 110 | +
 111 | +
 112 | +def takeaway_budget(content_s, other=()):
 113 | +    """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 114 | +    estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 115 | +    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 116 | +    other = [t for t in other if t and t.strip()]
 117 | +    fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 118 | +    words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 119 | +    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 120 | +              r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 121 | +    for a, b in (LY_AIM_S, RUNTIME_S):
 122 | +        lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 123 | +        if lo <= hi:
 124 | +            return lo, hi
 125 | +    return None
 126 | +
 127 | +
 128 |  def r4_max_vo_words(content_s, n_vo):
 129 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
 130 |      VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
 131 | @@ -179,13 +227,6 @@ def r4(pk):
 132 |                           "R4 (moments-first, 06:00) PASS") + f" | {note}"
 133 |  
 134 |  
 135 | -def budgets(content_s, n_bridges=1):
 136 | -    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
 137 | -    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
 138 | -    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
 139 | -    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
 140 | -
 141 | -
 142 |  def _name(m, ctx):
 143 |      return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
 144 |  
 145 | @@ -197,38 +238,23 @@ def signoff(segs, ctx):
 146 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 147 |  
 148 |  
 149 | -def plain_vo(segs, ctx):
 150 | -    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
 151 | -    last (orchestrator 03:40); the title names whole channels only (U11)."""
 152 | -    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
 153 | -    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
 154 | -    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
 155 | -    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
 156 | -    while len(title) > 70 and len(chans) > 1:
 157 | -        chans = chans[:-1]
 158 | -        title = "Bitcoin: " + ", ".join(chans) + " and others"
 159 | -    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
 160 | -    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}
 161 | +def labels(n):
 162 | +    """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 163 | +    return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 164 |  
 165 |  
 166 | -def assemble(order, by_id, fields, ctx, vo_kind):
 167 | -    segs = [by_id[i] for i in order]
 168 | -    lines = [dict(fields["intro"], slot="intro")] + \
 169 | -        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 170 | -        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 171 | -    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
 172 | +def _package(segs, ctx, fields, vo_kind, vo, lines):
 173 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"] not in ("title", "caption"))
 174 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 175 |            "vo_kind": vo_kind, "style": fields.get("style"),
 176 | -          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
 177 | +          "segments": [{"label": lb, "moment_id": m["moment_id"],
 178 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 179 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 180 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 181 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 182 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 183 | -                       for i, m in enumerate(segs)],
 184 | -          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 185 | -                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
 186 | -                 "signoff": signoff(segs, ctx)},
 187 | +                       for lb, m in zip(labels(len(segs)), segs)],
 188 | +          "vo": dict(vo, signoff=signoff(segs, ctx)),
 189 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
 190 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
 191 |            "lines": lines}
 192 | @@ -240,6 +266,46 @@ def assemble(order, by_id, fields, ctx, vo_kind):
 193 |      return pk
 194 |  
 195 |  
 196 | +def assemble(order, by_id, fields, ctx, vo_kind):
 197 | +    """The PBX MAX v3 shape (an intro after the hook and a line after clips; the orchestrator's given packages of the
 198 | +    night of Nov 11-12). L-y's medley is assemble_medley()."""
 199 | +    segs = [by_id[i] for i in order]
 200 | +    lines = [dict(fields["intro"], slot="intro")] + \
 201 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 202 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 203 | +    vo = {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 204 | +          "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1))}      # the renderer's after_clip
 205 | +    return _package(segs, ctx, fields, vo_kind, vo, lines)
 206 | +
 207 | +
 208 | +def assemble_medley(order, by_id, fields, ctx, vo_kind):
 209 | +    """L-y: the clips back to back, ONE takeaway after the last clip (slot "takeaway", the renderer's after_clip = the
 210 | +    last clip), and at most one bridge: after the hook it is the renderer's intro slot (slot "intro"), after clip k it is
 211 | +    a bridge after_clip k (slot "bridge_1"). fields: takeaway, bridge (None or {"text", "cites", "why"}), bridge_after
 212 | +    (None, 0 = after the hook, or k), title, caption."""
 213 | +    segs = [by_id[i] for i in order]
 214 | +    n_clips = len(segs) - 1
 215 | +    b, k = fields.get("bridge"), fields.get("bridge_after")
 216 | +    if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 217 | +        raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 218 | +    mid = b is not None and k > 0
 219 | +    lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 220 | +        ([dict(b, slot="bridge_1")] if mid else []) + \
 221 | +        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 222 | +         dict(fields["caption"], slot="caption")]
 223 | +    vo = {"intro": b["text"] if b is not None and k == 0 else None,
 224 | +          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 225 | +          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 226 | +    pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 227 | +    pk["shape"] = "medley"
 228 | +    pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 229 | +                                           "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
 230 | +                                           "text": b["text"], "why": b.get("why"),
 231 | +                                           "confirmed_by": fields.get("bridge_confirmed_by")}
 232 | +    pk["supply_exception"] = fields.get("supply_exception")
 233 | +    return pk
 234 | +
 235 | +
 236 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
 237 |  
 238 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
 239 | @@ -309,9 +375,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 240 |      return a_by, fails, vendors, families
 241 |  
 242 |  
 243 | -ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
 244 | -voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
 245 | -checks. The channels were not in one conversation and never answer each other.
 246 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
 247 | +play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
 248 | +clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
 249 | +conversation and never answer each other.
 250 |  
 251 |  {note}
 252 |  {clips}
 253 | @@ -320,52 +387,68 @@ Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repea
 254 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 255 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 256 |  it is today's.
 257 | -The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
 258 | -seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
 259 | -sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
 260 | -from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
 261 | -attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
 262 | +With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
 263 | +clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
 264 | +introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
 265 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
 266 | +each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
 267 | +survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
 268 | +"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
 269 | +words on what it adds and why it follows the clip before it (an internal note).
 270 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 271 |  "support": {{"id": "..."}}}}]}}"""
 272 |  
 273 | -STYLES = {
 274 | -    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
 275 | -            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
 276 | -            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
 277 | -            "clip, as your opinion, never as what the speaker said.",
 278 | -    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
 279 | -             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
 280 | -             "title."}
 281 | +MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
 282 | +Each clip is a person's own words from a show; the shows were not in one conversation.
 283 |  
 284 | -WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 285 | +{clips}
 286 | +
 287 | +1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
 288 | +   "none" if there is none.
 289 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
 290 | +3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
 291 | +   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
 292 | +   words.
 293 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
 294 | +
 295 | +WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 296 |  THE ANGLE (the point this video makes): "{angle}"
 297 | -The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
 298 | +The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
 299 | +in one conversation and never answer each other):
 300 |  
 301 |  {note}
 302 |  {lineup}
 303 |  
 304 | -The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
 305 | -(written by code).
 306 | -Write:
 307 | -- "intro": heard right AFTER the hook: your own take that sets up the angle.
 308 | -- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
 309 | -- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
 310 | -- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
 311 | +After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 312 | +{bridge}Write:
 313 | +- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 314 | +  opinion or conclusion), never a restatement of any clip.
 315 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 316 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 317 | -{style}
 318 |  RULES (a line that breaks one is rejected):
 319 | -- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
 320 | -- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
 321 | -  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
 322 | +- NEVER restate a clip's claim, and never repeat its words: the clip says it, in its own words.
 323 | +- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
 324 | +  or company; never what a speaker thinks or how speakers relate; no prediction of what will happen; no advice or
 325 | +  instruction to the viewer (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
 326 |  - Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
 327 |    for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
 328 | -  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
 329 | +  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
 330 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 331 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 332 |    "slams", "exposes", "admits", "confirms", "caught".
 333 | -{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
 334 | +- Write the title and caption in sentence case: capitalise only the first word and real names. A line that names a
 335 | +  show, a person or Bitcoin's price cites the clips it comes from.
 336 | +{extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 337 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 338 |  
 339 | +BRIDGE_ASK = """ONE JOIN NEEDS HELP: a blind viewer who watched these clips back to back could not follow the jump from
 340 | +{a} to {b} ("{why}"). Write ONE "bridge", heard between them: as short as it can be (at most {n} words); it only makes
 341 | +the next clip's subject or referent clear (its show and its topic, or a question); it never says what the next speaker
 342 | +thinks. Give "why": one sentence on why a viewer could not follow the jump without it. If you judge a viewer CAN
 343 | +follow this jump without narration, give "bridge": null (these clips then do not sit together, and other clips are
 344 | +picked).
 345 | +"""
 346 | +
 347 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
 348 |  different person's own words).
 349 |  
 350 | @@ -419,36 +502,43 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 351 |      return out
 352 |  
 353 |  
 354 | -def lineup_for(angle, by_id, dropped=frozenset()):
 355 | -    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
 356 | -    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
 357 | -    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
 358 | -    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
 359 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
 360 | +    """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 361 | +    medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 362 | +    angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 363 | +    predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), and the clips' seconds inside crange
 364 | +    (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
 365 | +    earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
 366 | +    seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
 367 | +    ONE channel may give two clips, from two different videos. None if impossible."""
 368 | +    lo, hi = crange or medley_content_range()
 369 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 370 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 371 |      hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 372 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 373 |      for h in hooks:
 374 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 375 | -                and m["channel_id"] != h["channel_id"]]
 376 | +                and (repeat_ok or m["channel_id"] != h["channel_id"])]
 377 |          best = None
 378 | -        for n in (3, 2):
 379 | -            lo, hi = content_range(n)
 380 | +        for n in range(clips[0], clips[1] + 1):
 381 |              for combo in itertools.combinations(pool, n):
 382 | -                if len({m["channel_id"] for m in combo}) != n:
 383 | +                chans = [m["channel_id"] for m in (h, *combo)]
 384 | +                if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
 385 | +                                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
 386 |                      continue
 387 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
 388 |                      continue
 389 | -                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
 390 | +                order = sorted(combo, key=lambda m: pos[m["moment_id"]])
 391 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
 392 |                      continue
 393 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
 394 |                  if not lo <= dur <= hi:
 395 |                      continue
 396 | -                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
 397 | +                key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
 398 |                  if best is None or key > best[0]:
 399 |                      best = (key, [h] + order)
 400 | -            if best:
 401 | -                return best[1]
 402 | +        if best:
 403 | +            return best[1]
 404 |      return None
 405 |  
 406 |  
 407 | @@ -489,9 +579,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 408 |          r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
 409 |                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 410 |          v = json.loads(r.text.strip())
 411 | -        labels = [sg["label"] for sg in pk["segments"]]
 412 | +        labs = [sg["label"] for sg in pk["segments"]]
 413 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 414 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
 415 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 416 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 417 |              raise ValueError("coherence verdict out of contract")
 418 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 419 | @@ -515,39 +605,149 @@ def _lineup_block(segs, ctx, a_by):
 420 |      return "\n".join(out)
 421 |  
 422 |  
 423 | -def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
 424 | +def joins(labs):
 425 | +    """The joins of a medley in play order: "<label> -> <next label>"; join k follows segment k (k = 0 is the hook)."""
 426 | +    return [f"{a} -> {b}" for a, b in zip(labs, labs[1:])]
 427 | +
 428 | +
 429 | +def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 430 | +    """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
 431 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
 432 | +    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
 433 | +    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
 434 | +    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
 435 | +    import providers as P
 436 | +    labs = labels(len(segs))
 437 | +    js = joins(labs)
 438 | +    clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 439 | +                      for lb, m in zip(labs, segs))
 440 | +    r = None
 441 | +    try:
 442 | +        r = router.call("coherence_verdict",
 443 | +                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
 444 | +                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 445 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 446 | +        v = json.loads(r.text.strip())
 447 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 448 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 449 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 450 | +                not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
 451 | +                any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 452 | +                    or not isinstance(x["why"], str) for x in v["joins"].values()):
 453 | +            raise ValueError("clips-alone verdict out of contract")
 454 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 455 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 456 | +            router.reject(r)
 457 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 458 | +    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 459 | +    flagged = [j for j in js if v["joins"][j]["followable"] is False]
 460 | +    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 461 | +        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 462 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 463 | +                    replayed=bool(getattr(r, "replayed", False)))
 464 | +
 465 | +
 466 | +def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 467 | +    """L-y: ONE takeaway (host commentary, class D), ONE title, ONE caption, and a bridge ONLY at `join` (k, why), the
 468 | +    one join the clips-alone verdict flagged (L-y 2): the writer gives it with its reason, or null when it judges a
 469 | +    viewer can follow the jump. The takeaway's word budget lands the factory's estimate (takeaway_budget()) with the
 470 | +    other VO lines' texts `other` (a bridge already written; when a bridge is asked for and none is written yet, the
 471 | +    budget holds for any bridge of LY_BRIDGE_MIN_WORDS..LY_BRIDGE_WORDS words where the clips allow it, else for one of
 472 | +    LY_BRIDGE_WORDS). -> (reply, fields) with fields["bridge_after"] = k when a bridge is given."""
 473 |      from select_by_id import UNTRUSTED
 474 |      from story_semantics import quote_data
 475 |      content = sum(m["duration_s"] for m in segs)
 476 | -    nb = len(segs) - 2
 477 | -    iw, bw, (lo, hi) = budgets(content, nb)
 478 | -    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
 479 | +    budget = takeaway_budget(content, other)
 480 | +    if join is not None and not other:                # the bridge's seconds come off the takeaway (audit 2030 C1, glm);
 481 | +        w = lambda n: [" ".join(["word"] * n)]          # until it is written, budget for ANY bridge of 3-12 words (C2,
 482 | +        short, long_ = takeaway_budget(content, w(LY_BRIDGE_MIN_WORDS)), takeaway_budget(content, w(LY_BRIDGE_WORDS))
 483 | +        both = (max(short[0], long_[0]), min(short[1], long_[1])) if short and long_ else None    # qwen P1, grok P2)
 484 | +        budget = both if both and both[0] <= both[1] else long_
 485 | +    budget = budget or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)
 486 | +    labs = labels(len(segs))
 487 | +    ask, shape = "", "null"
 488 | +    if join is not None:
 489 | +        k, why = join
 490 | +        ask = BRIDGE_ASK.format(a=labs[k].upper().replace("_", " "), b=labs[k + 1].upper().replace("_", " "),
 491 | +                                why=" ".join(quote_data(why, 300).replace('"', "'").split()), n=LY_BRIDGE_WORDS)
 492 | +        shape = '{"text": "...", "cites": ["id"], "why": "..."} or null'
 493 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 494 | -    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 495 | -                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
 496 | -                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
 497 | -                             extra=(extra + "\n") if extra else "")
 498 | +    prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 499 | +                             lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 500 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 501 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 502 |      try:
 503 |          obj = json.loads(r.text.strip())
 504 |          ids = [m["moment_id"] for m in segs]
 505 | -        keys = {"intro", "bridges", "title", "caption"}
 506 | +        keys = {"takeaway", "bridge", "title", "caption"}
 507 |          if not isinstance(obj, dict) or set(obj) != keys:
 508 |              raise ValueError(f"keys must be exactly {sorted(keys)}")
 509 | -        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
 510 | -            raise ValueError(f"'bridges' must hold {nb} lines")
 511 | -        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
 512 | -                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
 513 | -            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 514 | +        lines = [("takeaway", obj["takeaway"], {"text", "cites"}), ("title", obj["title"], {"text", "cites"}),
 515 | +                 ("caption", obj["caption"], {"text", "cites"})]
 516 | +        if obj["bridge"] is not None:
 517 | +            if join is None:
 518 | +                raise ValueError("no join needs a bridge: 'bridge' must be null (L-y 1)")
 519 | +            lines.append(("bridge", obj["bridge"], {"text", "cites", "why"}))
 520 | +        for slot, ln, want in lines:
 521 | +            if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
 522 |                      not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 523 | -                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
 524 | -                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
 525 | +                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
 526 | +                    ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
 527 | +                raise ValueError(f"{slot}: needs text and cites from the line-up's ids" +
 528 | +                                 (" and a reason" if "why" in want else ""))
 529 |          if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
 530 |              raise ValueError("title <= 70 characters, caption <= 220")
 531 |      except (ValueError, TypeError):
 532 |          router.reject(r)
 533 |          raise
 534 | -    return r, dict(obj, type="moments", angle=angle["angle"], style=style)
 535 | +    return r, dict(obj, bridge_after=join[0] if join is not None and obj["bridge"] is not None else None,
 536 | +                   type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
 537 | +
 538 | +
 539 | +def ly_shape(pk):
 540 | +    """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
 541 | +    last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
 542 | +    with its reason recorded, and every flagged join bridged (else these clips do not sit together); a bridge within
 543 | +    config.BRIDGE_WORD_CAP words; one clip per channel unless pk["supply_exception"] says why not (L-y 4)."""
 544 | +    from config import BRIDGE_WORD_CAP
 545 | +    segs, vo = pk["segments"], pk["vo"]
 546 | +    n_clips = len(segs) - 1
 547 | +    fails = []
 548 | +    if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 549 | +        fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 550 | +    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 551 | +    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 552 | +        fails.append("no takeaway after the last clip (L-y 1)")
 553 | +    js = joins([sg["label"] for sg in segs])
 554 | +    bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
 555 | +    texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]
 556 | +    if len(bridged) != len(texts):
 557 | +        fails.append(f"a line after clips {after[:-1]} that is not at a join between two clips")
 558 | +    if len(texts) > LY_MAX_BRIDGES:
 559 | +        fails.append(f"{len(texts)} bridges (L-y 2: at most {LY_MAX_BRIDGES})")
 560 | +    med = pk.get("medley") or {}
 561 | +    if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 562 | +        fails.append("the clips-alone verdict was not measured (L-y 3)")
 563 | +    elif sorted(bridged) != sorted(med["flagged"]):
 564 | +        fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 565 | +                     f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 566 | +    rec = pk.get("bridge") or {}
 567 | +    if texts and not (rec.get("why") or "").strip():
 568 | +        fails.append("the bridge's reason is not recorded (L-y 2)")
 569 | +    if texts and (not isinstance(rec.get("text"), str) or rec["text"].strip() != texts[0].strip()):
 570 | +        fails.append("the bridge record's text is not the bridge line (the factory's R11 binds them)")
 571 | +    cb = rec.get("confirmed_by")
 572 | +    if texts and not ((isinstance(cb, str) and cb.strip()) or (isinstance(cb, (list, dict)) and cb)):
 573 | +        fails.append("the bridge's confirmation by the clips-alone verdict is not recorded (L-y 2, R11)")
 574 | +    if not texts and pk.get("bridge"):
 575 | +        fails.append("a bridge record with no bridge line")
 576 | +    for t in texts:
 577 | +        if len(t.split()) > BRIDGE_WORD_CAP:
 578 | +            fails.append(f"bridge of {len(t.split())} words (max {BRIDGE_WORD_CAP})")
 579 | +    chans = [sg["channel_id"] for sg in segs]
 580 | +    if len(set(chans)) != len(chans) and not (pk.get("supply_exception") or "").strip():
 581 | +        fails.append("two clips from one channel without the supply exception recorded (L-y 4)")
 582 | +    return not fails, fails
 583 |  
 584 |  
 585 |  def fidelity_segments(pk, a_by):
 586 | @@ -563,7 +763,7 @@ def fidelity_segments(pk, a_by):
 587 |  
 588 |  def cheap_checks(pk, a_by, levels, now):
 589 |      """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
 590 | -    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
 591 | +    runtime, R4, and for a medley the L-y shape. -> (violations, det, dup, rt_ok, r4_res)."""
 592 |      segs_v = fidelity_segments(pk, a_by)
 593 |      lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 594 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 595 | @@ -571,10 +771,13 @@ def cheap_checks(pk, a_by, levels, now):
 596 |      dup = duplicates(pk)
 597 |      rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 598 |      r4_res = r4(pk)
 599 | +    what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
 600 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
 601 | -                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
 602 | +                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change {what} "
 603 |                                                        f"length"}]) + \
 604 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 605 | +    if pk.get("shape") == "medley":
 606 | +        v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 607 |      return v, det, dup, rt_ok, r4_res
 608 |  
 609 |  
 610 | @@ -654,16 +857,48 @@ def _writers(router):
 611 |  
 612 |  
 613 |  def _redo(violations):
 614 | -    return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
 615 | -            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 616 | +    """The writer's second try: exactly the failing lines, by the keys the writer returns ("bridge" for the one bridge,
 617 | +    whichever join it sits at)."""
 618 | +    key = {"intro": "bridge", "bridge_1": "bridge"}
 619 | +    return ("Your previous reply was REJECTED. Return the WHOLE JSON object again, every key; rewrite ONLY the lines "
 620 | +            "below and keep the others exactly as they were. The failing lines, with the reason:\n" +
 621 | +            "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 622 | +
 623 | +
 624 | +def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 625 | +    """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
 626 | +    the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
 627 | +    passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict.
 628 | +    context_framing: the context-integrity failures the VO's framing causes (VO_DEPENDENT; per clip, so not attributed
 629 | +    to one line: recorded beside `passed`, never folded into it)."""
 630 | +    line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
 631 | +    rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
 632 | +           "words": len((line.get("text") or "").split()),
 633 | +           "cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") == "takeaway"}),
 634 | +           "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
 635 | +           "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None,
 636 | +           "context_framing": None if cx is None else sorted({v["rule"] for v in cx.get("violations") or []
 637 | +                                                              if v.get("rule") in VO_DEPENDENT})}
 638 | +    if fid is not None:
 639 | +        ver = fid.get("verdict") or {}
 640 | +        if fid.get("measured") and isinstance(ver.get("violations"), list):
 641 | +            rec["verdict_fail"] = sorted({v["rule"] for v in ver["violations"] if v.get("slot") in ("takeaway", "-")})
 642 | +            rec["passed"] = not rec["cheap_fail"] and not rec["verdict_fail"]
 643 | +        else:
 644 | +            rec["verdict_fail"] = ["NOT MEASURED"]
 645 | +            rec["passed"] = False if rec["cheap_fail"] else None
 646 | +    return rec
 647 |  
 648 |  
 649 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 650 | -          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
 651 | -    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
 652 | -    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
 653 | -    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
 654 | -    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
 655 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 656 | +    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 657 | +    item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 658 | +    written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 659 | +    one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 660 | +    work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 661 | +    spend: a callable returning the ledger's USD (dollars per package).
 662 | +    -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 663 |      t0 = time.time()
 664 |      usd0 = spend() if spend else None
 665 |      ms, why = usable(moments, ctx, delivered, optout)
 666 | @@ -671,9 +906,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 667 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 668 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 669 |      levels = current_levels(sources.values(), ctx)
 670 | -    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 671 | +    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 672 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 673 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
 674 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 675 | +           "package": None}
 676 |      log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 677 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 678 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 679 | @@ -683,9 +919,25 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 680 |          return out
 681 |      from select_by_id import UNTRUSTED
 682 |      from story_semantics import quote_data
 683 | +    exc, tru = {}, {}
 684 | +    with ThreadPoolExecutor(max_workers=8) as pre:     # L-v 2 + CUTTABLE per moment, before the angles (L-y 3)
 685 | +        futs = {mid: pre.submit(truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
 686 | +        tru.update({mid: f.result() for mid, f in futs.items()})
 687 | +    cut_ok = lambda t: bool(t.get("ok")) and (t.get("edges") or {}).get("cuttable") is True
 688 | +    out["prescreen"]["second_pass"] = {
 689 | +        mid: "PASS" if cut_ok(t) else ("NOT MEASURED: " + t["error"] if t.get("error") else
 690 | +                                       "L-v 2 FAIL" if not t.get("ok") else "not cuttable at an edge (ruling C / 7)")
 691 | +        for mid, t in tru.items()}
 692 | +    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
 693 | +    out["prescreen"]["cuttable"] = len(cleared)
 694 | +    log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
 695 | +    if len({m["channel_id"] for m in cleared.values()}) < 3:
 696 | +        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
 697 | +                           f"channels")
 698 | +        return out
 699 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
 700 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 701 | -    lo, hi = content_range(2)[0], content_range(3)[1]
 702 | +    lo, hi = medley_content_range()
 703 |      angles, angle_reply = None, None
 704 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 705 |          r = None
 706 | @@ -704,28 +956,59 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 707 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 708 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 709 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
 710 | -    exc, tru = {}, {}
 711 | +    doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 712 |      with ThreadPoolExecutor(max_workers=8) as pool:
 713 |          for ai, angle in enumerate(angles):
 714 | -            dropped, w_used = set(), 0
 715 | -            while w_used < writes and not out["packages"]:
 716 | -                segs = lineup_for(angle, cleared, frozenset(dropped))
 717 | -                rec = {"angle": ai + 1, "text": angle["angle"],
 718 | -                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
 719 | +            dropped, n_lineup = set(), 0
 720 | +            while n_lineup < lineups and not out["packages"]:
 721 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed)), None
 722 | +                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 723 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True)
 724 | +                    if segs is not None:
 725 | +                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 726 | +                               if sum(m["channel_id"] == c for m in segs) > 1]
 727 | +                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 728 | +                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 729 | +                                     f" gives two clips, from two videos (L-y 4)")
 730 | +                rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 731 | +                       "supply_exception": exception, "attempts": []}
 732 |                  out["tried"].append(rec)
 733 |                  if segs is None:
 734 | -                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
 735 | +                    rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 736 |                      break
 737 | +                n_lineup += 1
 738 | +                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 739 | +                rec["medley"], rec["medley_ok"] = med, ok_m
 740 | +                log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 741 | +                    f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 742 | +                    f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 743 | +                labs = labels(len(segs))
 744 | +                if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 745 | +                    by_lab = dict(zip(labs, segs))
 746 | +                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 747 | +                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 748 | +                    if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 749 | +                        weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 750 | +                    if not med.get("measured") or not weak:
 751 | +                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 752 | +                        break
 753 | +                    dropped |= weak
 754 | +                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 755 | +                    continue
 756 | +                join = None
 757 | +                if med["flagged"]:
 758 | +                    k = joins(labs).index(med["flagged"][0])
 759 | +                    join = (k, med["joins"][med["flagged"][0]]["why"])
 760 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 761 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 762 | -                extra, relined = "", False
 763 | +                extra, relined, w_used, written = "", False, 0, ()
 764 |                  while w_used < writes:
 765 | -                    style = styles[min(w_used, len(styles) - 1)]
 766 |                      w_used += 1
 767 |                      try:
 768 | -                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
 769 | +                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 770 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup, other=written)
 771 |                      except Exception as e:
 772 | -                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 773 | +                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 774 |                          continue
 775 |                      writers_v.add(wr.vendor)
 776 |                      writers_f.add(wr.family)
 777 | @@ -740,25 +1023,61 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 778 |                              dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 779 |                              relined = True
 780 |                              break
 781 | -                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
 782 | -                                  f"written ({style}), attempt {w_used}")
 783 | +                    if join is not None and fields["bridge"] is None:
 784 | +                        dropped.add(segs[join[0] + 1]["moment_id"])
 785 | +                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 786 | +                                      f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 787 | +                        relined = True
 788 | +                        break
 789 | +                    if fields["bridge"] is not None:
 790 | +                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 791 | +                                                         "backend": med.get("backend")}
 792 | +                    fields["supply_exception"] = exception
 793 | +                    pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 794 | +                                         f"medley (L-y), written, attempt {w_used}")
 795 | +                    pk["medley"] = med
 796 | +                    written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
 797 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 798 | -                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
 799 | +                    att = {"writer": wr.backend, "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 800 | +                           "takeaway_budget": fields.get("takeaway_budget"),
 801 |                             "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 802 |                      rec["attempts"].append(att)
 803 | -                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
 804 | +                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 805 | +                    out["takeaways"].append(take)
 806 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 807 | +                        f"words, {pk['runtime_s_estimate']} s): " +
 808 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 809 |                          + f" ({time.time() - t0:.0f} s)")
 810 | +                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}   # the clips' own gates first
 811 | +                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")
 812 | +                            or (t.get("edges") or {}).get("cuttable") is not True}   # CUTTABLE is a required gate
 813 | +                    if lost:
 814 | +                        rec["lost_why"] = {mid: ("exclusion" if e.get("verdict") != "keep" else
 815 | +                                                 "second pass (L-v 2)" if not t.get("ok") else
 816 | +                                                 "not cuttable at an edge (ruling C / 7)")
 817 | +                                           for mid, (e, t) in got.items() if mid in lost}
 818 | +                        att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 819 | +                        dropped |= lost
 820 | +                        doomed |= lost                         # per-moment verdicts: no angle may use them again
 821 | +                        rec["why"] = f"exclusion / L-v 2 / CUTTABLE dropped {rec['lost_why']}: re-lined"
 822 | +                        relined = True
 823 | +                        break
 824 |                      if cheap:
 825 |                          att["violations"] = cheap
 826 | -                        extra = _redo(cheap)
 827 | +                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 828 | +                        extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 829 | +                                                                     if b else " (no takeaway length lands it: shorten "
 830 | +                                                                                "the bridge)"))
 831 | +                                       if v["rule"] == "RUNTIME" else v for v in cheap])
 832 |                          continue
 833 |                      fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 834 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 835 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 836 |                      att["violations"] = fid["violations"] + cx["violations"]
 837 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 838 | -                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
 839 | -                        f"({time.time() - t0:.0f} s)")
 840 | +                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 841 | +                        f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 842 | +                        f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 843 |                      if not fid["ok"] or not cx["ok"]:
 844 |                          if fid["ok"] and not framing:
 845 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 846 | @@ -768,31 +1087,42 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 847 |                                                              "detail": VO_FIX.get(v["rule"], v["detail"])}
 848 |                                                             for v in framing])
 849 |                          continue
 850 | -                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}
 851 | -                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")}
 852 |                      att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 853 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 854 | -                    if lost:
 855 | -                        dropped |= lost
 856 | -                        rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
 857 | -                        relined = True
 858 | -                        break
 859 | -                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
 860 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
 861 |                      att["coherence"] = coh
 862 | -                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
 863 | -                        f"({time.time() - t0:.0f} s)")
 864 | +                    log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 865 | +                        f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 866 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 867 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 868 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 869 | -                                            ok_c, coh)
 870 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 871 |                      if not ok_c:
 872 | -                        rec["why"] = "coherence below 4 or no through-line: next angle"
 873 | +                        tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 874 | +                        if coh.get("measured") and type(coh.get("vo_point")) is int and \
 875 | +                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 876 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 877 | +                            extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 878 | +                                            f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 879 | +                                            f"being supported by the clips: land the point the clips make together"}])
 880 | +                            continue                          # the clips hold; only the takeaway's point is weak
 881 | +                        weak = {sg["moment_id"] for sg in pk["segments"][1:]
 882 | +                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 883 | +                        dropped |= weak
 884 | +                        relined = bool(weak)
 885 | +                        rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 886 | +                                      (f"dropped {sorted(weak)}, re-lined" if weak else "next angle"))
 887 | +                        break
 888 | +                    import package_pin
 889 | +                    problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 890 | +                    if problems:                              # never return a package its pin would refuse (L-j)
 891 | +                        rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
 892 |                          w_used = writes
 893 |                          break
 894 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
 895 | +                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 896 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 897 |                                      "coherence": coh.get("backend")}
 898 | -                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
 899 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 900 |                      pk["seconds"] = round(time.time() - t0, 1)
 901 |                      pk["usd"] = round(spend() - usd0, 4) if spend else None
 902 |                      out["packages"].append(pk)
 903 | @@ -802,8 +1132,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 904 |                      break
 905 |              if out["packages"]:
 906 |                  break
 907 | -            if time.time() - t0 > BUDGET_S * 2 or (spend and spend() - usd0 > BUDGET_USD * 2):
 908 | -                out["why_none"] = "twice the per-package time / spend budget is used: stopped"
 909 | +            used_s, used_usd = time.time() - t0, (spend() - usd0) if spend else 0.0
 910 | +            if used_s > BUDGET_S * 2 or used_usd > BUDGET_USD * 2:
 911 | +                out["why_none"] = (f"stopped after angle {ai + 1} of {len(angles)}: {used_s:.0f} s of the "
 912 | +                                   f"{BUDGET_S * 2:.0f} s / ${used_usd:.2f} of the ${BUDGET_USD * 2:.2f} (estimate) "
 913 | +                                   f"per-package budget (05:25 item 5, twice)")
 914 | +                out["budget_stop"] = {"seconds": round(used_s, 1), "usd_estimate": round(used_usd, 4),
 915 | +                                      "angles_tried": ai + 1, "angles": len(angles)}
 916 |                  break
 917 |      out["package"] = out["packages"][0] if out["packages"] else None
 918 |      out["seconds"] = round(time.time() - t0, 1)
 919 | @@ -811,9 +1146,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 920 |      return out
 921 |  
 922 |  
 923 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 924 | -    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
 925 | -    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
 926 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 927 | +    """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 928 | +    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 929 | +    A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 930 | +    (shape=(ok, [why]) from ly_shape())."""
 931 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 932 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 933 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 934 | @@ -861,4 +1198,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 935 |                          measured=all("edges" in t for t in truth.values())),
 936 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 937 |                            **votes_of(coh)),
 938 | +        **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 939 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
 940 | +           if medley is not None else {}),
 941 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 942 | +           if shape is not None else {}),
 943 |      }
 944 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 945 | index 3194dcc1..b1da529b 100644
 946 | --- a/pipeline/package_pin.py
 947 | +++ b/pipeline/package_pin.py
 948 | @@ -25,6 +25,13 @@ from datetime import datetime, timezone
 949 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 950 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 951 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 952 | +MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 953 | +
 954 | +
 955 | +def required_gates(pk):
 956 | +    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 957 | +    clips-alone verdict and the L-y shape."""
 958 | +    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 959 |  
 960 |  
 961 |  class PinRefused(Exception):
 962 | @@ -44,12 +51,12 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 963 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 964 |  
 965 |  
 966 | -def gate_problems(gates):
 967 | +def gate_problems(gates, required=REQUIRED_GATES):
 968 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 969 |      if not isinstance(gates, dict):
 970 |          return ["no gate inventory"]
 971 |      out = []
 972 | -    for g in REQUIRED_GATES:
 973 | +    for g in required:
 974 |          row = gates.get(g)
 975 |          if not isinstance(row, dict) or row.get("status") != "PASS":
 976 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 977 | @@ -58,6 +65,17 @@ def gate_problems(gates):
 978 |      return out
 979 |  
 980 |  
 981 | +def bridge_slots(pk):
 982 | +    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
 983 | +    is the "takeaway" and the one bridge before it is bridge_1."""
 984 | +    vo = pk.get("vo") or {}
 985 | +    after = list(vo.get("bridges_after_clip") or [])
 986 | +    last = len(pk.get("segments") or []) - 1
 987 | +    if pk.get("shape") == "medley":
 988 | +        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
 989 | +    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]
 990 | +
 991 | +
 992 |  def line_problems(pk):
 993 |      """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
 994 |      by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
 995 | @@ -66,8 +84,9 @@ def line_problems(pk):
 996 |      if by.get("intro") != vo.get("intro"):
 997 |          out.append("intro")
 998 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 999 | -    if len(bridges) != len(after) or any(by.get(f"bridge_{i + 1}") != t for i, t in enumerate(bridges)) or \
1000 | -            any(k.startswith("bridge_") and int(k.split("_")[1]) > len(bridges) for k in by if k):
1001 | +    slots = bridge_slots(pk)
1002 | +    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
1003 | +            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
1004 |          out.append("bridges")
1005 |      for k in ("title", "caption"):
1006 |          if by.get(k) != pk.get(k):
1007 | @@ -76,8 +95,8 @@ def line_problems(pk):
1008 |  
1009 |  
1010 |  def to_pin(pk, run_name):
1011 | -    problems = gate_problems(pk.get("gates")) + [f"{x}: the gated line differs from the one shipped"
1012 | -                                                 for x in line_problems(pk)]
1013 | +    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
1014 | +                                                                     for x in line_problems(pk)]
1015 |      if problems:
1016 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
1017 |      segs = []
1018 | @@ -100,8 +119,13 @@ def to_pin(pk, run_name):
1019 |                                  "signoff_expected": pk["vo"]["signoff"],
1020 |                                  "title": pk["title"], "caption": pk["caption"],
1021 |                                  "hook_first_words": pk["hook_first_words"],
1022 | -                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
1023 | -                                                                   for i in range(len(pk["vo"]["bridges"]))}},
1024 | +                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
1025 | +                                               if pk["vo"]["intro"] else {}),
1026 | +                                            **{s: "takeaway" if s == "takeaway" else "connection"
1027 | +                                               for s in bridge_slots(pk)}},
1028 | +                                "shape": pk.get("shape"),
1029 | +                                "bridge": pk.get("bridge"),
1030 | +                                "supply_exception": pk.get("supply_exception"),
1031 |                                  "gates": pk["gates"],
1032 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
1033 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
1034 | diff --git a/pipeline/providers.py b/pipeline/providers.py
1035 | index 67dfd391..b0c948d5 100644
1036 | --- a/pipeline/providers.py
1037 | +++ b/pipeline/providers.py
1038 | @@ -221,6 +221,16 @@ class OpenAIBackend(Backend):
1039 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1040 |  
1041 |  
1042 | +def _num(x):
1043 | +    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x >= 0
1044 | +
1045 | +
1046 | +def _reported(usd):
1047 | +    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
1048 | +    the price-table estimate for it, labelled as an estimate)."""
1049 | +    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}
1050 | +
1051 | +
1052 |  class HeimdallBackend(OpenAIBackend):
1053 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
1054 |      words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
1055 | @@ -246,7 +256,8 @@ class HeimdallBackend(OpenAIBackend):
1056 |              text = j["choices"][0]["message"].get("content") or ""
1057 |          except (KeyError, IndexError, TypeError):
1058 |              raise RequestRejected("heimdall: no choices") from None
1059 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1060 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
1061 | +                          **_reported(u.get("cost"))), time.time() - t0
1062 |  
1063 |      def credits(self):
1064 |          """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
1065 | @@ -285,8 +296,9 @@ class XAIBackend(Backend):
1066 |              text = j["choices"][0]["message"].get("content") or ""
1067 |          except (KeyError, IndexError, TypeError):
1068 |              raise RequestRejected("xai: no choices") from None
1069 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
1070 | -            time.time() - t0
1071 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
1072 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning},
1073 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
1074 |  
1075 |  
1076 |  class AnthropicBackend(Backend):
1077 | @@ -575,6 +587,13 @@ class Router:
1078 |                  r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
1079 |                  r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
1080 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
1081 | +                if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
1082 | +                    rep = float(usage["usd_reported"])
1083 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
1084 | +                             reported_calls=b.get("reported_calls", 0) + 1)
1085 | +                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
1086 | +                else:                                  # no vendor figure: the estimate stands for this call
1087 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
1088 |              self._save(d)
1089 |  
1090 |      def reject(self, reply, why=""):
1091 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
1092 | index 4535455d..7a41a3a3 100644
1093 | --- a/tests/moments/test_moments.py
1094 | +++ b/tests/moments/test_moments.py
1095 | @@ -129,13 +129,6 @@ class TestPackageUsable(unittest.TestCase):
1096 |          self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
1097 |                                                  "Go follow them for more. Links are below.")
1098 |  
1099 | -    def test_the_plain_title_never_cuts_a_name(self):
1100 | -        ctx = E.Context(NOW, REG)
1101 | -        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
1102 | -                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
1103 | -        title = PK.plain_vo(segs, ctx)[2]["text"]
1104 | -        self.assertLessEqual(len(title), 70)
1105 | -        self.assertTrue(title.endswith(("and others", "Two", "One")), title)
1106 |  
1107 |  
1108 |  if __name__ == "__main__":
1109 | diff --git a/tests/package/pin_and_verify.py b/tests/package/pin_and_verify.py
1110 | index 4a478de9..37f12287 100644
1111 | --- a/tests/package/pin_and_verify.py
1112 | +++ b/tests/package/pin_and_verify.py
1113 | @@ -7,7 +7,9 @@ Checks on the REAL pin: package_pin.to_pin authorises it (every required gate ex
1114 |  equal the VO / title / caption); pinned.validate_schema accepts it; pinned.build_edl (moments_vo) carries the VO
1115 |  (a line after every clip, the last included), the ONE title and caption and the seal; edl_rules.rule_r4 (R4 for
1116 |  moments) passes on the pin's own segment durations.
1117 | -Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]"""
1118 | +Where the factory copy has edl_rules.rule_r11 (law L-y's VO shape), it runs too.
1119 | +Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]
1120 | +(MAIN_TREE: any directory holding pipeline/{pinned,edl_rules,config}.py, e.g. a `git show` export of a branch)"""
1121 |  import json
1122 |  import os
1123 |  import shutil
1124 | @@ -61,7 +63,11 @@ def main(argv=None):
1125 |          ok, why = edl_rules.rule_r4(edl)
1126 |          print(f"PIN {path}\n  story_id {pin['story_id']} seal {mp['package_sha256']}")
1127 |          print(f"  pinned.validate_schema: OK; build_edl (moments_vo): VO, title, caption, seal carried")
1128 | -        print(f"  edl_rules.rule_r4 (deployed): {'PASS' if ok else 'FAIL'}: {why}")
1129 | +        print(f"  edl_rules.rule_r4 ({main_tree}): {'PASS' if ok else 'FAIL'}: {why}")
1130 | +        if hasattr(edl_rules, "rule_r11"):                  # law L-y's VO shape, where that factory has it
1131 | +            ok11, why11 = edl_rules.rule_r11(edl)
1132 | +            print(f"  edl_rules.rule_r11 ({main_tree}): {'PASS' if ok11 else 'FAIL'}: {why11}")
1133 | +            ok = ok and ok11
1134 |          return 0 if ok else 1
1135 |      finally:
1136 |          shutil.rmtree(tmp, ignore_errors=True)
1137 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
1138 | new file mode 100644
1139 | index 00000000..1fb37a55
1140 | --- /dev/null
1141 | +++ b/tests/package/proof_ly.py
1142 | @@ -0,0 +1,242 @@
1143 | +#!/usr/bin/env python3
1144 | +"""ORCHESTRATOR ORDER 20:30 ET Nov 12 (law L-y, VOICEOVER IS MINIMAL): re-run tonight's universe and the saved ones
1145 | +through the packager's new default, the MEDLEY (pipeline/package.py build()). The table goes to the top of STATE:
1146 | +- packages per universe;
1147 | +- how many needed zero bridges and how many needed one;
1148 | +- the gate pass rate on the single takeaway line;
1149 | +- time and dollars per package.
1150 | +The top package of the newest universe becomes a sealed pin (MOMENTS_PIN_LY.json).
1151 | +
1152 | +LEGS (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"). The probe at
1153 | +20:32 ET found Anthropic "credit balance is too low" (HTTP 400) and OpenAI 429 credit_balance_exhausted, so both stay
1154 | +out. Local gemma runs on GPU0, which this builder never uses (L-r, the session's standing order), so every local leg
1155 | +is out too. What is left:
1156 | +- the writer (angle + takeaway) is Heimdall: deepseek-v4.1-flash, then qwen3.8-27b. This is the config's own
1157 | +  angle_write order once the frozen vendors drop out.
1158 | +- every verdict avoids the writer's vendor (L-x), so it runs on xAI grok-4.20.
1159 | +- the second recogniser is ElevenLabs scribe_v1.
1160 | +CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
1161 | +
1162 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
1163 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
1164 | +estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
1165 | +
1166 | +Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
1167 | +"""
1168 | +import argparse
1169 | +import hashlib
1170 | +import json
1171 | +import os
1172 | +import subprocess
1173 | +import sys
1174 | +import time
1175 | +
1176 | +HERE = os.path.dirname(os.path.abspath(__file__))
1177 | +REPO = os.path.dirname(os.path.dirname(HERE))
1178 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1179 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1180 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1181 | +import moments as M  # noqa: E402
1182 | +import package as PK  # noqa: E402
1183 | +import package_pin  # noqa: E402
1184 | +import proof_moments as PM  # noqa: E402
1185 | +import providers as P  # noqa: E402
1186 | +
1187 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
1188 | +OUT = os.path.join(HERE, "proof")
1189 | +SPEND = os.path.join(OUT, "SPEND_LY.json")
1190 | +LY_LIMIT_USD = 40.0                # the price-table estimate (an upper bound): xAI's own figure ran 1/8 of it on
1191 | +                                   # this order's first calls (estimate $0.636 vs reported $0.078 for 3 grok calls),
1192 | +                                   # so about $5 real; each paid call also RESERVES its upper bound (~$0.26-0.96)
1193 | +                                   # while in flight, and three workers run concurrently
1194 | +TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
1195 | +RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
1196 | +        "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
1197 | +        "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
1198 | +NEWEST = RUNS[0]
1199 | +FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
1200 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
1201 | +SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
1202 | +
1203 | +
1204 | +def chains():
1205 | +    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
1206 | +    cfg = json.load(open(P.CONFIG))
1207 | +    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
1208 | +    out["angle_write"] = list(WRITERS)
1209 | +    return out
1210 | +
1211 | +
1212 | +def ledger():
1213 | +    try:
1214 | +        d = json.load(open(SPEND))
1215 | +    except (OSError, ValueError):
1216 | +        d = {}
1217 | +    est = float(d.get("usd_estimate", 0.0))
1218 | +    best = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
1219 | +    return est, best, d
1220 | +
1221 | +
1222 | +def meter(router):
1223 | +    """THIS process's own spend, from every call the router accounts (Router._settle). The shared ledger's total moves
1224 | +    with the other workers too, so a per-package budget read from it would charge one universe for another's calls.
1225 | +    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}."""
1226 | +    import threading
1227 | +    tot, lock, settle = {"est": 0.0, "best": 0.0}, threading.Lock(), router._settle
1228 | +
1229 | +    def _settle(key, backend=None, usage=None, usd=0.0, role=""):
1230 | +        settle(key, backend, usage, usd, role)
1231 | +        if backend is not None:
1232 | +            rep = (usage or {}).get("usd_reported")
1233 | +            with lock:
1234 | +                tot["est"] += float(usd or 0.0)
1235 | +                tot["best"] += float(rep) if P._num(rep) else float(usd or 0.0)
1236 | +    router._settle = _settle
1237 | +    return tot
1238 | +
1239 | +
1240 | +def code_sha():
1241 | +    """The code this run used: HEAD plus the working tree's diff of pipeline/ and this driver (the results name it)."""
1242 | +    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
1243 | +    diff = subprocess.run(["git", "-C", REPO, "diff", "HEAD", "--", "pipeline", "tests/package"], capture_output=True).stdout
1244 | +    return f"{head}+{hashlib.sha256(diff).hexdigest()[:12]}" if diff else head
1245 | +
1246 | +
1247 | +def run_one(run, router, work_dir, log, own):
1248 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
1249 | +    words, captions, ctx, saved = PM.universe_sources(run)
1250 | +    sources = {s.video_id: s for s in words}
1251 | +    e0, b0 = own["est"], own["best"]
1252 | +    t0 = time.time()
1253 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
1254 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a.json"), spend=lambda: own["est"])
1255 | +    e1, b1 = own["est"], own["best"]
1256 | +    res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
1257 | +               usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
1258 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
1259 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
1260 | +    if res["package"]:
1261 | +        pk = res["package"]
1262 | +        pk["usd_best_known"] = res["usd_best_known"]
1263 | +        try:
1264 | +            path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name="MOMENTS_PIN_LY.json")
1265 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1266 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
1267 | +            log(f"{run}: PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best "
1268 | +                f"known) pin {path}")
1269 | +        except package_pin.PinRefused as e:                # recorded, never a pass; the next universe still runs
1270 | +            res["pin_refused"] = str(e)
1271 | +            log(f"{run}: PIN REFUSED: {e}")
1272 | +    else:
1273 | +        log(f"{run}: no package ({res.get('why_none')}); usable {res['usable']}, cleared "
1274 | +            f"{res['prescreen']['cleared']}")
1275 | +    json.dump(res, open(os.path.join(OUT, run, "package_ly.json"), "w"), indent=1, default=str)
1276 | +    return res
1277 | +
1278 | +
1279 | +def table():
1280 | +    rows = ["| universe | usable / cleared step A | line-ups judged on the clips alone (passed) | package | segments, "
1281 | +            "seconds of clips | bridges | takeaway writes: passed / judged (first write) | runtime estimate | time | "
1282 | +            "$ estimate / $ best known (*) | why none |", "|---|---|---|---|---|---|---|---|---|---|---|"]
1283 | +    tot = {"universes": 0, "packages": 0, "zero": 0, "one": 0, "passed": 0, "judged": 0, "first_passed": 0,
1284 | +           "first_judged": 0, "s": [], "est": [], "best": [], "framing": 0, "flagged_lineups": 0, "lineups": 0,
1285 | +           "budget_stops": []}
1286 | +    for run in RUNS:
1287 | +        f = os.path.join(OUT, run, "package_ly.json")
1288 | +        if not os.path.exists(f):
1289 | +            rows.append(f"| {run} | not run | | | | | | | | | |")
1290 | +            continue
1291 | +        r = json.load(open(f))
1292 | +        tot["universes"] += 1
1293 | +        tried = [t for t in r.get("tried") or [] if t.get("medley") is not None]
1294 | +        med_ok = sum(1 for t in tried if t.get("medley_ok") is True)
1295 | +        if not r.get("package") and (r.get("budget_stop") or "budget" in (r.get("why_none") or "")):
1296 | +            tot["budget_stops"].append(run)
1297 | +        tot["lineups"] += len(tried)
1298 | +        tot["flagged_lineups"] += sum(1 for t in tried if t.get("medley_ok") and t["medley"].get("flagged"))
1299 | +        takes = r.get("takeaways") or []
1300 | +        tot["framing"] += sum(1 for x in takes if x.get("context_framing"))
1301 | +        judged = [x for x in takes if x.get("passed") is not None]
1302 | +        firsts = [x for x in judged if x.get("write") == 1]
1303 | +        tot["passed"] += sum(1 for x in judged if x["passed"])
1304 | +        tot["judged"] += len(judged)
1305 | +        tot["first_passed"] += sum(1 for x in firsts if x["passed"])
1306 | +        tot["first_judged"] += len(firsts)
1307 | +        pk = r.get("package")
1308 | +        if pk:
1309 | +            nb = 0 if not pk.get("bridge") else 1
1310 | +            tot["packages"] += 1
1311 | +            tot["zero" if nb == 0 else "one"] += 1
1312 | +            tot["s"].append(r["seconds"])
1313 | +            tot["est"].append(r.get("usd_estimate") or 0.0)
1314 | +            tot["best"].append(r.get("usd_best_known") or 0.0)
1315 | +            segs = f"{len(pk['segments'])}, {sum(s['duration_s'] for s in pk['segments']):.1f} s"
1316 | +            bridge = "0" if nb == 0 else f"1 ({pk['bridge']['join']}: {pk['bridge']['why']})".replace("|", "/")
1317 | +            pkg, rt, why = f"YES: \"{pk['title']}\"".replace("|", "/"), f"{pk['runtime_s_estimate']} s", ""
1318 | +        else:
1319 | +            segs = bridge = rt = "-"
1320 | +            pkg = "no"
1321 | +            why = (r.get("why_none") or "; ".join(f"angle {t['angle']}: {t.get('why') or '-'}" for t in r.get("tried") or [])
1322 | +                   )[:240].replace("|", "/")
1323 | +        rows.append(f"| {run} | {r['usable']} / {r['prescreen']['cleared']} | {len(tried)} ({med_ok}) | {pkg} | {segs} | "
1324 | +                    f"{bridge} | {sum(1 for x in judged if x['passed'])} / {len(judged)} "
1325 | +                    f"({sum(1 for x in firsts if x['passed'])} / {len(firsts)}) | {rt} | {r['seconds']} s | "
1326 | +                    f"${r.get('usd_estimate')} / ${r.get('usd_best_known')} | {why} |")
1327 | +    n = tot["packages"]
1328 | +    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
1329 | +    _, _, d = ledger()
1330 | +    summary = (f"\n**Totals:**\n"
1331 | +               f"- {tot['universes']} universes run; {n} packages.\n"
1332 | +               f"- Bridges: {tot['zero']} packages needed none, {tot['one']} needed one.\n"
1333 | +               f"- The takeaway line passed its gates in {tot['passed']} of {tot['judged']} judged writes "
1334 | +               f"({tot['first_passed']} of {tot['first_judged']} on the first write); context-integrity failures "
1335 | +               f"caused by the VO's framing, recorded beside it: {tot['framing']} writes.\n"
1336 | +               f"- Line-ups judged on the clips alone: {tot['lineups']}; of those that passed, {tot['flagged_lineups']} "
1337 | +               f"had one join a viewer could not follow (the bridge offered).\n"
1338 | +               f"- Universes without a package because the per-package budget (05:25 item 5, twice) stopped the "
1339 | +               f"search before every angle was tried: {len(tot['budget_stops'])} {tot['budget_stops'] or ''}.\n"
1340 | +               f"- Per package: {mean(tot['s']):.0f} s mean, ${mean(tot['est']):.2f} estimate, "
1341 | +               f"${mean(tot['best']):.2f} best known.\n"
1342 | +               f"- This order's ledger: ${d.get('usd_estimate', 0):.2f} estimate; vendor-reported "
1343 | +               f"${d.get('usd_reported', 0):.4f} + unreported calls' estimate ${d.get('usd_unreported_estimate', 0):.2f}.\n")
1344 | +    note = ("\n(*) $ estimate: the price table's upper bound (the spend guard reads it). $ best known: the vendor's own "
1345 | +            "figure where the reply carries one (xAI cost_in_usd_ticks, Heimdall usage.cost), else that call's estimate "
1346 | +            "(ElevenLabs STT reports none).\n")
1347 | +    text = ("# pp-selectid: the L-y medley re-run (generated by tests/package/proof_ly.py --table)\n\n" +
1348 | +            "\n".join(rows) + "\n" + note + summary)
1349 | +    open(TABLE, "w").write(text)
1350 | +    return text
1351 | +
1352 | +
1353 | +def main(argv=None):
1354 | +    ap = argparse.ArgumentParser()
1355 | +    ap.add_argument("--runs", nargs="+", default=list(RUNS))
1356 | +    ap.add_argument("--table", action="store_true", help="only (re)write the table from the saved results")
1357 | +    ap.add_argument("--work-dir", default=os.path.join(SCRATCH, "lv2"))
1358 | +    a = ap.parse_args(argv)
1359 | +    if a.table:
1360 | +        print(table())
1361 | +        return 0
1362 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
1363 | +    own = meter(router)
1364 | +    os.makedirs(a.work_dir, exist_ok=True)
1365 | +    for run in a.runs:
1366 | +        os.makedirs(os.path.join(OUT, run), exist_ok=True)
1367 | +        logf = open(os.path.join(OUT, run, "package_ly.log"), "a")
1368 | +        say = lambda s: (print(f"[{run}] {s}", flush=True), logf.write(s + "\n"), logf.flush())
1369 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} L-y medley build, code {code_sha()}, chains {json.dumps(router.chains)}")
1370 | +        try:
1371 | +            run_one(run, router, a.work_dir, say, own)
1372 | +        except P.SpendLimit as e:
1373 | +            say(f"STOPPED: {e}")
1374 | +            break
1375 | +        finally:
1376 | +            logf.close()
1377 | +    if router.notices:
1378 | +        print("NOTICES:", router.notices)
1379 | +    print(table())
1380 | +    return 0
1381 | +
1382 | +
1383 | +if __name__ == "__main__":
1384 | +    sys.exit(main())
1385 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1386 | new file mode 100644
1387 | index 00000000..51bce8eb
1388 | --- /dev/null
1389 | +++ b/tests/package/test_medley.py
1390 | @@ -0,0 +1,544 @@
1391 | +#!/usr/bin/env python3
1392 | +"""L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12): the packager's MEDLEY, offline.
1393 | +
1394 | +- The arithmetic: the clips' seconds that let ONE takeaway land the factory's estimate in 60-70 s, and the takeaway's
1395 | +  word budget, which lands it there.
1396 | +- The line-up: the hook + 2-4 clips in the proposer's play order, one per channel (a repeat only as the recorded supply
1397 | +  exception).
1398 | +- The clips-ALONE verdict's contract.
1399 | +- The writer's contract: a bridge only at the flagged join.
1400 | +- ly_shape's must-fail cases.
1401 | +- The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
1402 | +"""
1403 | +import json
1404 | +import os
1405 | +import sys
1406 | +import unittest
1407 | +
1408 | +HERE = os.path.dirname(os.path.abspath(__file__))
1409 | +REPO = os.path.dirname(os.path.dirname(HERE))
1410 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1411 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1412 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1413 | +sys.path.insert(0, HERE)
1414 | +import eligibility as E  # noqa: E402
1415 | +import package as PK  # noqa: E402
1416 | +import package_pin  # noqa: E402
1417 | +from config import BRIDGE_WORD_CAP  # noqa: E402
1418 | +from test_eligibility import NOW, REG  # noqa: E402
1419 | +from test_gates import Canned  # noqa: E402
1420 | +from test_moments import pm  # noqa: E402
1421 | +
1422 | +W = lambda n: " ".join(["word"] * n)
1423 | +
1424 | +
1425 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
1426 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
1427 | +
1428 | +
1429 | +def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
1430 | +    js = PK.joins(labs)
1431 | +    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
1432 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
1433 | +                          if j in flagged else "same subject"} for j in js}}
1434 | +
1435 | +
1436 | +def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
1437 | +    """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
1438 | +    labs = PK.labels(n)
1439 | +    segs = [{"label": lb, "channel_id": (chans or "ABCDEFG")[i], "duration_s": 12.0, "text": f"Bitcoin {lb}."}
1440 | +            for i, lb in enumerate(labs)]
1441 | +    bridges, aft = (["B " + W(5)] if bridge else []) + [W(20)], ([after] if bridge else []) + [n - 1]
1442 | +    return {"shape": "medley", "segments": segs,
1443 | +            "vo": {"intro": intro, "bridges": bridges, "bridges_after_clip": aft, "signoff": "S"},
1444 | +            "medley": {"measured": measured, "flagged": list(flagged)},
1445 | +            "bridge": {"why": bridge, "text": intro or (bridges[0] if bridge else None),
1446 | +                       "confirmed_by": {"join": "x", "why": "y"}} if bridge or intro else None,
1447 | +            "supply_exception": supply}
1448 | +
1449 | +
1450 | +class TestMedleyArithmetic(unittest.TestCase):
1451 | +    def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1452 | +        lo, hi = PK.medley_content_range()
1453 | +        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1454 | +        seg = lambda c: [{"duration_s": c}]
1455 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1456 | +        self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1457 | +        lo1, hi1 = PK.medley_content_range(n_bridges=1)
1458 | +        self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1459 | +        self.assertAlmostEqual(hi - hi1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1460 | +
1461 | +    def test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps(self):
1462 | +        aimed = 0
1463 | +        for c10 in range(300, 560):
1464 | +            c = c10 / 10
1465 | +            b = PK.takeaway_budget(c)
1466 | +            if b is None:
1467 | +                self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1468 | +                continue
1469 | +            lo, hi = b
1470 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1471 | +            for w in (lo, hi):
1472 | +                est = PK.runtime([{"duration_s": c}], [W(w)])
1473 | +                self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1474 | +                p = {"segments": [{"duration_s": c, "channel": "A"}, {"duration_s": 0.0, "channel": "B"}],
1475 | +                     "vo": {"intro": None, "bridges": [W(w)], "bridges_after_clip": [1]}, "runtime_s_estimate": est}
1476 | +                self.assertTrue(PK.r4(p)[0], (c, w, PK.r4(p)[1]))
1477 | +            aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1478 | +        self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1479 | +        self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1480 | +        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1481 | +        self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1482 | +
1483 | +
1484 | +class TestMedleyLineup(unittest.TestCase):
1485 | +    def test_the_hook_and_clips_in_the_proposers_order_one_per_channel(self):
1486 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1487 | +                                          pm("z", "D", 12.0), pm("e", "A", 14.0))}
1488 | +        seg = PK.lineup_for(angle(["h", "y", "x", "z", "e"], "h"), by)
1489 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "y", "x"])        # the earliest that fit, in that order
1490 | +        self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1491 | +
1492 | +    def test_more_clips_when_two_do_not_fill_the_medley(self):
1493 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1494 | +        seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1495 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1496 | +        short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1497 | +        self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1498 | +
1499 | +    def test_a_channel_twice_only_as_the_supply_exception_and_from_two_videos(self):
1500 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0),
1501 | +                                          pm("e", "A", 13.0))}
1502 | +        a = angle(["h", "x", "y", "e"], "h")
1503 | +        self.assertIsNone(PK.lineup_for(a, by))                                    # one per channel cannot fill it
1504 | +        seg = PK.lineup_for(a, by, repeat_ok=True)
1505 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "e"])
1506 | +        same_video = dict(by, e=dict(by["e"], video_id=by["h"]["video_id"]))
1507 | +        self.assertIsNone(PK.lineup_for(a, same_video, repeat_ok=True))           # never two clips of one video
1508 | +
1509 | +
1510 | +class TestClipsAloneVerdict(unittest.TestCase):
1511 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1512 | +    LABS = ["hook", "clip_01", "clip_02"]
1513 | +
1514 | +    def run_it(self, reply):
1515 | +        r = Canned(coherence_verdict=[reply])
1516 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1517 | +        return ok, v, r
1518 | +
1519 | +    def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
1520 | +        r = Canned(coherence_verdict=[verdict(self.LABS)])
1521 | +        prompts = []
1522 | +        call = r.call
1523 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1524 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1525 | +        self.assertTrue(ok)
1526 | +        self.assertEqual(v["flagged"], [])
1527 | +        self.assertNotIn("VOICE-OVER", prompts[0])
1528 | +        self.assertNotIn("TITLE", prompts[0])
1529 | +        self.assertIn('"hook -> clip_01"', prompts[0])
1530 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
1531 | +
1532 | +    def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
1533 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
1534 | +        self.assertTrue(ok)
1535 | +        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
1536 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
1537 | +        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
1538 | +
1539 | +    def test_no_through_line_or_a_weak_clip_fails(self):
1540 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
1541 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
1542 | +        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
1543 | +
1544 | +    def test_out_of_contract_is_not_measured_and_rejected(self):
1545 | +        good = verdict(self.LABS)
1546 | +        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
1547 | +                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
1548 | +                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
1549 | +                    dict(good, vo_point=5),
1550 | +                    dict(good, clips={"hook": 5, "clip_01": 5})):
1551 | +            ok, v, r = self.run_it(bad)
1552 | +            self.assertFalse(ok)
1553 | +            self.assertFalse(v["measured"])
1554 | +            self.assertIsNone(v["flagged"])
1555 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1556 | +
1557 | +
1558 | +class TestWriteTakeaway(unittest.TestCase):
1559 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1560 | +
1561 | +    def write(self, reply, join=None):
1562 | +        r = Canned(angle_write=[reply])
1563 | +        return PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {}, join), r
1564 | +
1565 | +    def lines(self, bridge=None):
1566 | +        return {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": bridge,
1567 | +                "title": {"text": "No ruler.", "cites": ["h"]}, "caption": {"text": "three clips", "cites": []}}
1568 | +
1569 | +    def test_no_bridge_unless_a_join_was_flagged(self):
1570 | +        (rep, f), _ = self.write(self.lines())
1571 | +        self.assertIsNone(f["bridge_after"])
1572 | +        with self.assertRaises(ValueError):
1573 | +            self.write(self.lines({"text": "Next, B.", "cites": ["x"], "why": "w"}))
1574 | +
1575 | +    def test_a_bridge_at_the_flagged_join_needs_its_reason_and_may_be_declined(self):
1576 | +        (rep, f), _ = self.write(self.lines({"text": "Next, B's show on keys.", "cites": ["x"], "why": "no referent"}),
1577 | +                                 join=(1, "the next speaker's 'it' has no referent"))
1578 | +        self.assertEqual(f["bridge_after"], 1)
1579 | +        (rep, f), _ = self.write(self.lines(None), join=(1, "w"))
1580 | +        self.assertIsNone(f["bridge_after"])                                       # declined: build re-lines
1581 | +        for bad in ({"text": "Next.", "cites": ["x"]}, {"text": "Next.", "cites": ["x"], "why": " "},
1582 | +                    {"text": "Next.", "cites": ["zz"], "why": "w"}):
1583 | +            with self.assertRaises(ValueError):
1584 | +                self.write(self.lines(bad), join=(1, "w"))
1585 | +
1586 | +    def test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_of_3_to_12_words(self):
1587 | +        for c10 in range(240, 470, 3):                     # audit 2030 C2 (qwen P1, grok P2): the first write's budget
1588 | +            c = c10 / 10
1589 | +            segs = [dict(m, duration_s=c / 3) for m in self.SEGS]
1590 | +            r = Canned(angle_write=[self.lines()])
1591 | +            prompts = []
1592 | +            call = r.call
1593 | +            r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1594 | +            PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
1595 | +            import re
1596 | +            lo, hi = map(int, re.search(r"one or two sentences, (\d+)-(\d+) words", prompts[0]).groups())
1597 | +            ok_all = all(PK.RUNTIME_S[0] <= PK.runtime([{"duration_s": c}], [W(t), W(b)]) <= PK.RUNTIME_S[1]
1598 | +                         for t in (lo, hi) for b in (PK.LY_BRIDGE_MIN_WORDS, PK.LY_BRIDGE_WORDS))
1599 | +            both = [PK.takeaway_budget(c, [W(b)]) for b in (PK.LY_BRIDGE_MIN_WORDS, PK.LY_BRIDGE_WORDS)]
1600 | +            if all(both) and max(both[0][0], both[1][0]) <= min(both[0][1], both[1][1]):
1601 | +                self.assertTrue(ok_all, (c, lo, hi))       # where the clips allow it, ANY bridge of 3-12 words lands
1602 | +
1603 | +    def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1604 | +        r = Canned(angle_write=[self.lines()])
1605 | +        prompts = []
1606 | +        call = r.call
1607 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1608 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1609 | +        lo, hi = PK.takeaway_budget(39.0)
1610 | +        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1611 | +        self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1612 | +        self.assertNotIn('"intro"', prompts[0])
1613 | +
1614 | +
1615 | +class TestLyShape(unittest.TestCase):
1616 | +    def test_a_clean_medley_passes(self):
1617 | +        self.assertEqual(PK.ly_shape(medley_pk()), (True, []))
1618 | +        self.assertTrue(PK.ly_shape(medley_pk(n=5))[0])
1619 | +
1620 | +    def test_a_bridge_only_and_always_at_the_flagged_join_with_its_reason(self):
1621 | +        self.assertTrue(PK.ly_shape(medley_pk(n=4, bridge="no referent", after=2, flagged=["clip_02 -> clip_03"]))[0])
1622 | +        rec = {"why": "no referent", "text": "Next, B.", "confirmed_by": {"join": "hook -> clip_01"}}
1623 | +        self.assertTrue(PK.ly_shape(medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {"bridge": rec})[0])
1624 | +        must_fail = {
1625 | +            "bridge at an unflagged join": medley_pk(n=4, bridge="w", after=1, flagged=["clip_02 -> clip_03"]),
1626 | +            "bridge with nothing flagged": medley_pk(n=4, bridge="w", after=1),
1627 | +            "flagged join left unbridged": medley_pk(flagged=["clip_01 -> clip_02"]),
1628 | +            "bridge without its reason": medley_pk(n=4, bridge="", after=2, flagged=["clip_02 -> clip_03"]) | {
1629 | +                "vo": medley_pk(n=4, bridge="w", after=2)["vo"]},
1630 | +            "an intro with nothing flagged": medley_pk(intro="Here's the thing.") | {"bridge": {"why": "w"}},
1631 | +            "two bridges": medley_pk(n=4, intro="Next.", bridge="w", after=2,
1632 | +                                     flagged=["hook -> clip_01", "clip_02 -> clip_03"]),
1633 | +            "verdict not measured": medley_pk(measured=False),
1634 | +            "verdict missing": medley_pk() | {"medley": None},
1635 | +            # the factory's R11 (integrator, branch ly-shape): the record binds the line and carries its confirmation
1636 | +            "record text is not the line": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1637 | +                "bridge": dict(rec, text="Next, C.")},
1638 | +            "confirmation missing": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1639 | +                "bridge": dict(rec, confirmed_by=None)},
1640 | +            "confirmation a bool": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1641 | +                "bridge": dict(rec, confirmed_by=True)},
1642 | +            "confirmation empty": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1643 | +                "bridge": dict(rec, confirmed_by={})},
1644 | +            "a record with no bridge line": medley_pk() | {"bridge": rec},
1645 | +        }
1646 | +        for why, pk in must_fail.items():
1647 | +            self.assertFalse(PK.ly_shape(pk)[0], why)
1648 | +
1649 | +    def test_the_takeaway_is_the_line_after_the_last_clip(self):
1650 | +        pk = medley_pk()
1651 | +        pk["vo"] = dict(pk["vo"], bridges_after_clip=[1])
1652 | +        self.assertFalse(PK.ly_shape(pk)[0])
1653 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1654 | +        self.assertFalse(PK.ly_shape(pk)[0])
1655 | +
1656 | +    def test_three_to_five_segments_and_one_clip_per_channel(self):
1657 | +        self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1658 | +        self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1659 | +        self.assertFalse(PK.ly_shape(medley_pk(chans="ABA"))[0])
1660 | +        self.assertTrue(PK.ly_shape(medley_pk(chans="ABA", supply="A gives two clips (L-y 4)"))[0])
1661 | +
1662 | +    def test_a_bridge_over_the_word_cap_fails(self):
1663 | +        pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
1664 | +        pk["vo"]["bridges"][0] = W(BRIDGE_WORD_CAP + 1)
1665 | +        self.assertFalse(PK.ly_shape(pk)[0])
1666 | +
1667 | +
1668 | +def ctx():
1669 | +    return E.Context(NOW, REG)
1670 | +
1671 | +
1672 | +class TestMedleyPackageAndPin(unittest.TestCase):
1673 | +    def build(self, bridge=None, k=None, n=3, text="No ruler, just rules nobody gets to bend."):
1674 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1675 | +                                          pm("z", "D", 9.0))}
1676 | +        order = ["h", "x", "y", "z"][:n]
1677 | +        fields = {"takeaway": {"text": text, "cites": []}, "bridge": bridge, "bridge_after": k,
1678 | +                  "title": {"text": "No ruler.", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1679 | +        return PK.assemble_medley(order, by, fields, ctx(), "medley (L-y)")
1680 | +
1681 | +    def gates(self, pk, **over):
1682 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
1683 | +        g.update(over)
1684 | +        return g
1685 | +
1686 | +    def test_no_intro_and_one_takeaway_after_the_last_clip(self):
1687 | +        pk = self.build()
1688 | +        self.assertIsNone(pk["vo"]["intro"])
1689 | +        self.assertEqual((pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]),
1690 | +                         (["No ruler, just rules nobody gets to bend."], [2]))
1691 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["takeaway", "title", "caption"])
1692 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1693 | +        self.assertEqual(PK.r4(pk)[0], True)
1694 | +
1695 | +    def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1696 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1697 | +        pk = self.build(bridge=b, k=1, n=4)
1698 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 3])
1699 | +        self.assertEqual([x["slot"] for x in pk["lines"]][:2], ["bridge_1", "takeaway"])
1700 | +        self.assertEqual(pk["bridge"]["join"], "clip_01 -> clip_02")
1701 | +        pk0 = self.build(bridge=b, k=0)
1702 | +        self.assertEqual(pk0["vo"]["intro"], "Next, on keys.")
1703 | +        self.assertEqual(pk0["vo"]["bridges_after_clip"], [2])
1704 | +        with self.assertRaises(ValueError):
1705 | +            self.build(bridge=b, k=2)                     # after the last clip is the takeaway's place
1706 | +
1707 | +    def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1708 | +        pk = self.build()
1709 | +        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1710 | +        pk["gates"] = self.gates(pk)
1711 | +        pin = package_pin.to_pin(pk, "test")
1712 | +        mp = pin["moments_package"]
1713 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1714 | +        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1715 | +        self.assertEqual(mp["shape"], "medley")
1716 | +        for missing in ("medley", "ly_shape"):
1717 | +            g = self.gates(pk)
1718 | +            g.pop(missing)
1719 | +            with self.assertRaises(package_pin.PinRefused):
1720 | +                package_pin.to_pin(dict(pk, gates=g), "test")
1721 | +        with self.assertRaises(package_pin.PinRefused):
1722 | +            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
1723 | +
1724 | +    def test_the_gated_takeaway_must_be_the_spoken_one(self):
1725 | +        pk = self.build()
1726 | +        pk["gates"] = self.gates(pk)
1727 | +        pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
1728 | +        with self.assertRaises(package_pin.PinRefused) as cm:
1729 | +            package_pin.to_pin(pk, "test")
1730 | +        self.assertIn("bridges", str(cm.exception))
1731 | +
1732 | +    def test_the_old_shape_keeps_its_slots(self):
1733 | +        pk = {"vo": {"intro": "I", "bridges": ["B", "T"], "bridges_after_clip": [1, 2]}, "segments": [{}, {}, {}]}
1734 | +        self.assertEqual(package_pin.bridge_slots(pk), ["bridge_1", "bridge_2"])
1735 | +        self.assertEqual(package_pin.bridge_slots(dict(pk, shape="medley")), ["bridge_1", "takeaway"])
1736 | +
1737 | +
1738 | +    def test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins(self):
1739 | +        pk = self.build(text=" ".join(["rules"] * (PK.MOMENTS_TAKEAWAY_WORD_CAP + 1)))
1740 | +        pk["medley"] = {"measured": True, "flagged": []}
1741 | +        cheap = PK.cheap_checks(pk, {}, [], NOW)[0]
1742 | +        self.assertTrue(any(v["rule"] == "R4" and "takeaway 1 31 words (max 30)" in v["detail"] for v in cheap), cheap)
1743 | +        b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
1744 | +        pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
1745 | +        pk0["gates"] = self.gates(pk0)
1746 | +        mp = package_pin.to_pin(pk0, "test")["moments_package"]
1747 | +        self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
1748 | +                                        "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
1749 | +        self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})
1750 | +
1751 | +
1752 | +class Rig:
1753 | +    """build() with every model and the network stubbed: the LOOP CONTROL under test (audit 2030 C1, glm P2-6).
1754 | +    medleys: the clips-alone verdicts in call order, each (ok, flagged, ratings, through_line); writes: the writer's
1755 | +    bridges in call order (None = no bridge / declined)."""
1756 | +
1757 | +    LINE = "Nobody gets to bend these rules, and that is exactly why they hold when it counts."
1758 | +    A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
1759 | +            "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
1760 | +
1761 | +    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=()):
1762 | +        import providers as P
1763 | +        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
1764 | +        self.uncuttable, self.excluded = set(uncuttable), set(excluded)
1765 | +        self.medley_calls, self.write_calls, self.prompts = [], [], []
1766 | +        many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
1767 | +        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
1768 | +        call = self.router.call
1769 | +        self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
1770 | +                                                          call(role, prompt, *a, **k))[1]
1771 | +        self.router.backends = {"xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}
1772 | +
1773 | +    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
1774 | +        self.medley_calls.append([m["moment_id"] for m in segs])
1775 | +        ok, flagged, ratings, line = self.medleys.pop(0)
1776 | +        labs = PK.labels(len(segs))
1777 | +        v = verdict(labs, flagged, ratings, line)
1778 | +        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False)
1779 | +
1780 | +    def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
1781 | +        self.write_calls.append(([m["moment_id"] for m in segs], join))
1782 | +        b = self.writes.pop(0)
1783 | +        fields = {"takeaway": {"text": self.LINE, "cites": []}, "bridge": b,
1784 | +                  "bridge_after": join[0] if join is not None and b is not None else None,
1785 | +                  "title": {"text": "Nobody bends the rules", "cites": []},
1786 | +                  "caption": {"text": "three voices, one point", "cites": []},
1787 | +                  "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
1788 | +        return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
1789 | +
1790 | +    def run(self):
1791 | +        fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
1792 | +               "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
1793 | +               "verdict": {"ok": True, "violations": [], "classes": {}}}
1794 | +        cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
1795 | +        stubs = {
1796 | +            "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
1797 | +            "prescreen": lambda router, ms, *a, **k: ({m["moment_id"]: dict(self.A_OK) for m in ms},
1798 | +                                                      {m["moment_id"]: [] for m in ms}, set(), set()),
1799 | +            "current_levels": lambda *a, **k: [],
1800 | +            "medley": self.medley, "write_takeaway": self.write,
1801 | +            "paid_gates": lambda *a, **k: (fid, cx),
1802 | +            "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
1803 | +                                                         "keep", "measured": True, "replayed": False,
1804 | +                                                         "backend": "xai:grok"},
1805 | +            "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
1806 | +                                                     "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
1807 | +            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
1808 | +                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
1809 | +                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
1810 | +                                                             "replayed": False}),
1811 | +        }
1812 | +        saved = {k: getattr(PK, k) for k in stubs}
1813 | +        try:
1814 | +            for k, v in stubs.items():
1815 | +                setattr(PK, k, v)
1816 | +            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent")
1817 | +        finally:
1818 | +            for k, v in saved.items():
1819 | +                setattr(PK, k, v)
1820 | +
1821 | +
1822 | +class TestBuildLoop(unittest.TestCase):
1823 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1824 | +
1825 | +    def test_nothing_is_written_for_clips_that_fail_alone(self):
1826 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], None, "none")], [])
1827 | +        out = rig.run()
1828 | +        self.assertIsNone(out["package"])
1829 | +        self.assertEqual(rig.write_calls, [])
1830 | +        self.assertIn("no through-line", out["tried"][0]["why"])
1831 | +
1832 | +    def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
1833 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
1834 | +                  [None])
1835 | +        out = rig.run()
1836 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
1837 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])           # written only after the clips pass
1838 | +        self.assertIsNotNone(out["package"])
1839 | +        self.assertIsNone(out["package"]["bridge"])
1840 | +
1841 | +    def test_a_declined_bridge_drops_the_clip_after_the_flagged_join(self):
1842 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
1843 | +                                                  (True, [], None, Rig.LINE)], [None, None])
1844 | +        out = rig.run()
1845 | +        self.assertEqual(rig.write_calls[0], (["h", "x", "y"], (1, "the next speaker's 'it' has no referent")))
1846 | +        self.assertIn("followable without a bridge", out["tried"][0]["why"])
1847 | +        self.assertEqual(rig.medley_calls[1], ["h", "x", "z"])                  # y, after the flagged join, dropped
1848 | +        pk = out["package"]
1849 | +        self.assertIsNone(pk["bridge"])
1850 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["ly_shape"]["status"]), ("PASS", "PASS"))
1851 | +
1852 | +    def test_a_given_bridge_sits_at_the_flagged_join_with_its_reason(self):
1853 | +        b = {"text": "Next, a show on keys.", "cites": ["y"], "why": "the next clip's 'it' has no referent"}
1854 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b])
1855 | +        pk = rig.run()["package"]
1856 | +        self.assertEqual((pk["bridge"]["join"], pk["bridge"]["why"]), ("clip_01 -> clip_02", b["why"]))
1857 | +        self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
1858 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
1859 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
1860 | +        package_pin.to_pin(pk, "test")                    # every required row exactly PASS: the pin is allowed
1861 | +
1862 | +    def test_a_clip_the_second_recogniser_cannot_cut_is_never_offered_to_the_angles(self):
1863 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None], uncuttable={"y"})
1864 | +        out = rig.run()
1865 | +        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
1866 | +        self.assertNotIn("id=y ", angle_prompt)          # measured once per moment, before the angles (L-y 3)
1867 | +        self.assertIn("id=x ", angle_prompt)
1868 | +        self.assertEqual(out["prescreen"]["second_pass"]["y"], "not cuttable at an edge (ruling C / 7)")
1869 | +        self.assertEqual(out["prescreen"]["cuttable"], 3)
1870 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
1871 | +        pk = out["package"]
1872 | +        self.assertEqual(pk["gates"]["cuttable"]["status"], "PASS")
1873 | +        package_pin.to_pin(pk, "test")                    # build() returns only a package its pin accepts
1874 | +
1875 | +    def test_an_excluded_moment_stays_out_of_every_later_angle(self):
1876 | +        ms = self.MS + [pm("w", "E", 14.0)]
1877 | +        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "z", "w"]], [(True, [], None, Rig.LINE)] * 2, [None, None],
1878 | +                  excluded={"x"})
1879 | +        out = rig.run()
1880 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "z", "w"]])   # angle 2 never offers x again
1881 | +        self.assertIn("'x': 'exclusion'", out["tried"][0]["why"])
1882 | +        self.assertEqual(len(rig.write_calls), 2)          # the paid verdicts never ran on the doomed line-up
1883 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "z", "w"])
1884 | +
1885 | +    def test_the_supply_exception_is_recorded(self):
1886 | +        ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
1887 | +        rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
1888 | +        pk = rig.run()["package"]
1889 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "e"])
1890 | +        self.assertIn("gives two clips, from two videos (L-y 4)", pk["supply_exception"])
1891 | +        self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")
1892 | +
1893 | +
1894 | +class TestInventoryRows(unittest.TestCase):
1895 | +    def test_the_two_medley_rows(self):
1896 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
1897 | +               "backend": "x", "replayed": False, "measured": True}
1898 | +        coh = {"backend": "x", "replayed": False, "measured": True}
1899 | +        args = (fid, [], True, (True, ""), {"ok": True, "measured": True, "replayed": False, "backends": {}},
1900 | +                {"hook": {"backend": "x", "replayed": False}}, {"h": {"verdict": "keep", "measured": True,
1901 | +                                                                      "replayed": False}},
1902 | +                {"h": {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "s"}}, True, coh)
1903 | +        self.assertNotIn("medley", PK.inventory(*args))
1904 | +        g = PK.inventory(*args, medley=(True, {"backend": "x", "replayed": False, "measured": True, "flagged": []}),
1905 | +                         shape=(True, []))
1906 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("PASS", "PASS"))
1907 | +        g = PK.inventory(*args, medley=(False, {"measured": False, "flagged": None}), shape=(False, ["two bridges"]))
1908 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("NOT RUN", "FAIL"))
1909 | +        self.assertEqual(g["ly_shape"]["why"], ["two bridges"])
1910 | +
1911 | +
1912 | +class TestReportedCost(unittest.TestCase):
1913 | +    def test_the_ledger_keeps_the_vendors_own_figure_beside_the_estimate(self):
1914 | +        import tempfile
1915 | +        import providers as P
1916 | +        with tempfile.TemporaryDirectory() as d:
1917 | +            path = os.path.join(d, "SPEND.json")
1918 | +            r = P.Router(env_path=None, spend_path=path, limit_usd=10.0)
1919 | +            b = r.backends["xai:grok-4.20-0309-reasoning"]
1920 | +            r._settle(None, b, {"in": 1000, "out": 1000, "usd_reported": 0.002}, 0.03, "check")
1921 | +            r._settle(None, b, {"in": 1000, "out": 1000}, 0.03, "check")
1922 | +            led = json.load(open(path))
1923 | +            self.assertAlmostEqual(led["usd_estimate"], 0.06, places=6)
1924 | +            self.assertAlmostEqual(led["usd_reported"], 0.002, places=8)
1925 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.03, places=6)
1926 | +            self.assertEqual(led["by_backend"][b.name]["reported_calls"], 1)
1927 | +        self.assertEqual(P._reported(None), {})
1928 | +        self.assertEqual(P._reported(True), {})
1929 | +        self.assertEqual(P._reported(-1), {})
1930 | +        self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})
1931 | +
1932 | +
1933 | +if __name__ == "__main__":
1934 | +    unittest.main()
1935 | 
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

ROUND 2 (cycles 3 and 4, 21:20 ET): the same diff plus these changes made after cycle 2. Review them first.
11. The first write for a flagged join budgets the takeaway so that ANY bridge of 3-12 words lands 60-70 s, the
    intersection of both budgets (package.write_takeaway). Every redo budgets with the bridge as written.
12. package.ly_shape also fails a bridge record whose text differs from the bridge line, a record whose confirmed_by
    is missing, a bool or empty, and a record with no bridge line. This mirrors the integrator's render-side R11.
13. CUTTABLE (the independent recogniser's sentence boundary at both edges, a REQUIRED gate) was never a drop reason
    in build(); the live run found a package with CUTTABLE FAIL, which the pin refused. Now:
    - L-v 2's second pass and CUTTABLE run ONCE PER CLEARED MOMENT BEFORE the angle call, and the angle proposer
      only sees moments that pass both (out["prescreen"]["second_pass"]);
    - a moment lost to exclusion is "doomed": no later angle may use it;
    - the per-clip results (exclusion, L-v 2, CUTTABLE) are read BEFORE the paid fidelity / context verdicts, so no
      verdict is paid on a line-up that is already lost;
    - build() returns a package only when package_pin.gate_problems(required_gates) is empty.
    Check that filtering early can never let through a moment the later gates would refuse, and never refuse one
    they would pass.
14. The writer prompt's rules now name the fidelity verdict's commentary tests (no checkable fact, no speaker view,
    no prediction, no advice or instruction to the viewer, no accusation, nothing that sounds like a quote) and ask
    for sentence-case titles and captions (title-case words were read as names by the deterministic NAME rule).
    Only the prompt changed; no gate changed.
15. tests/package/proof_ly.py: each worker meters its OWN spend at Router._settle, because the shared ledger moves
    with every worker. The per-package budget stop names which limit stopped it (out["budget_stop"]). A refused pin
    is recorded and the next universe still runs. tests/package/pin_and_verify.py also runs rule_r11 where the
    factory copy has it.

