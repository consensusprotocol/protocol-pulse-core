# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0003
# Branch: pp-selectid
# Generated: 2026-11-14 00:03 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0003/C1_STEP.diff (524 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index adb3d40..65c73c4 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -20,7 +20,8 @@ Result           ok; reasons (EVERY blocking reason, named, with its detail); fa
   6 |                   layout_eligible, age_h, tier, duration_s, ...); parts (a Lineup's per-span results)
   7 |  
   8 |  Layout eligibility is measured for every item and reported as the fact `layout_eligible`; for an on-screen role it is
   9 | -also the blocking reason 'layout_ineligible', so the supply DEC-12d removes can be counted.
  10 | +also the blocking reason 'layout_ineligible' (since RULING 93, 23:58 ET Nov 13: only a channel with no registry id; the
  11 | +frames of each clip are judged at the pin stage, visual_pin.layout_block).
  12 |  """
  13 |  import math
  14 |  import re
  15 | @@ -329,8 +330,11 @@ def age_hours(published_at, now):
  16 |  
  17 |  
  18 |  def layout_ok(reg):
  19 | -    """Rule S6 (editorial_select.layout_eligible, DEC-12d): a registry channel with an id and no burned-in chyron."""
  20 | -    return bool(reg and reg.get("channel_id") and not reg.get("has_chyron"))
  21 | +    """Rule S6: a registry channel with an id. RULING 93 (orchestrator 23:58 ET Nov 13): DEC-12d is measured per CLIP,
  22 | +    not per channel. No channel is layout_ineligible by name: every clip, any channel, is judged on its own frames by
  23 | +    the pin-stage visual check (visual_pin.layout_block: a ticker or crawl, or a lower third the 9:16 crop would cut
  24 | +    mid-word or that covers the speaker). The registry's has_chyron is a hint that orders that check, nothing more."""
  25 | +    return bool(reg and reg.get("channel_id"))
  26 |  
  27 |  
  28 |  # ── the predicate ──
  29 | @@ -380,8 +384,7 @@ def _source(src, ctx, role):
  30 |          R("no_transcript", "no transcript words")
  31 |      if role in ON_SCREEN:
  32 |          if not facts["layout_eligible"]:
  33 | -            R("layout_ineligible", f"{facts['channel']}: " + ("burned-in chyron (has_chyron, DEC-12d)"
  34 | -                                                             if reg and reg.get("has_chyron") else "no registry channel id"))
  35 | +            R("layout_ineligible", f"{facts['channel']}: no registry channel id")   # ruling 93: never by name
  36 |          if not sentence_ready(src):
  37 |              R("not_sentence_ready", "no sentence-ready word record (law L-e): " +
  38 |                ("segment timing only" if src.timing != "word" else "a stretch reads unpunctuated"))
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 8972b95..1dc0f26 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -2336,7 +2336,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  44 |      see(rated_open)                                                          # seen before any angle is asked
  45 |      blocked = {}
  46 |      for m in rated_open:
  47 | -        why_v = VP.hook_block(m["visual"])
  48 | +        why_v = VP.hook_block(m["visual"]) or VP.layout_block(m["visual"])    # ruling 93: its own frames, per clip
  49 |          if why_v:
  50 |              m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
  51 |      out["visual"] = out_visual
  52 | @@ -2553,9 +2553,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  53 |                                        "back to back with the sign-off only", "added_clip": added,
  54 |                                 "lineup_before": [m["moment_id"] for m in segs]}}
  55 |          see(order)                                        # RULING 70: the added clip is seen too
  56 | -        vbad = [m["moment_id"] for m in order if not (m.get("visual") or {}).get("measured")]
  57 | -        if vbad:
  58 | -            note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
  59 | +        vbad = [m["moment_id"] for m in order if VP.layout_block(m.get("visual"))]   # ruling 93 (not measured
  60 | +        if vbad:                                                                    # included, law L-m)
  61 | +            note["why_not"] = f"rulings 70 / 93: not measured, or not eligible on its frames: {vbad}"
  62 |              return None
  63 |          nv_pre = None
  64 |          if lock_check is not None:                         # RULINGS 68 / 72: its own line-up
  65 | @@ -2741,8 +2741,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  66 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  67 |                  extra, relined, w_used, written = "", False, 0, ()
  68 |                  see(segs)                                   # RULING 70: every clip seen before any write is paid
  69 | -                vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") for m in segs
  70 | -                        if not (m.get("visual") or {}).get("measured")}
  71 | +                vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") or VP.layout_block(m.get("visual"))
  72 | +                        for m in segs if VP.layout_block(m.get("visual"))}   # ruling 93: per clip (L-m included)
  73 |                  if vbad or segs[0].get("visual_hook_block"):
  74 |                      vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  75 |                      dropped |= set(vbad)
  76 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  77 | index b4ee879..effb73e 100644
  78 | --- a/pipeline/spotlight.py
  79 | +++ b/pipeline/spotlight.py
  80 | @@ -350,6 +350,16 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
  81 |      return rec
  82 |  
  83 |  
  84 | +def clean_visual(v):
  85 | +    """RULING 90's "visual check clean" with RULING 93: measured, no ruling-70 flag (a third person shown as a still
  86 | +    with a negative claim, on-screen text that asserts beyond the words), not blocked as a hook, and eligible on its
  87 | +    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) is
  88 | +    eligible and flagged for the orchestrator, so it does not make the clip unclean."""
  89 | +    import visual_pin as VP
  90 | +    return (v or {}).get("measured") is True and not VP.hook_block(v) and not VP.layout_block(v) and \
  91 | +        not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]
  92 | +
  93 | +
  94 |  def alone_score(m):
  95 |      """The ALONE scorer's rating of the moment's CURRENT text (package.verdict_of: the integrator's verdicts of the
  96 |      render's own scorer, rulings 56 / 60), or None when it has none yet."""
  97 | @@ -595,9 +605,10 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
  98 |      rows.pop("r4", None)
  99 |      rows.pop("coherence", None)
 100 |      v = m.get("visual") or {}
 101 | -    rows["visual"] = _row(v.get("measured") is True and not v.get("flags"), v.get("backend"), v.get("replayed"),
 102 | +    rows["visual"] = _row(clean_visual(v), v.get("backend"), v.get("replayed"),
 103 |                            measured=v.get("measured") is True, flags=list(v.get("flags") or []),
 104 | -                          by_rule="ruling 90: the visual check clean (no flag; ruling 70's sheet)")
 105 | +                          by_rule="ruling 90: the visual check clean (no ruling-70 flag, not blocked as a hook, and "
 106 | +                                  "eligible on its frames under ruling 93; a ruling-93 burned_in flag is listed)")
 107 |      own, hr = P.hook_own(m), m.get("hook_rating") or {}
 108 |      rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 109 |                              bool(hr.get("replayed", False)), measured=own is not None,
 110 | @@ -767,10 +778,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 111 |      clean = {}
 112 |      for mid, m in strong.items():
 113 |          v = m.get("visual") or {}
 114 | -        if v.get("measured") is True and not v.get("flags") and not VP.hook_block(v):
 115 | +        if clean_visual(v):
 116 |              clean[mid] = m
 117 |          else:
 118 |              stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
 119 | +                                              VP.layout_block(v) or
 120 |                                                f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
 121 |      passed(clean, 5)
 122 |      two, off_fail = P.second_screen(router, clean, a_by, sources, ctx, log=log, cache=step_a_cache) if clean else \
 123 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 124 | index 4cecca8..df3c7bb 100644
 125 | --- a/pipeline/visual_pin.py
 126 | +++ b/pipeline/visual_pin.py
 127 | @@ -16,6 +16,11 @@ Per clip (a moment's [start, end]):
 128 |    it cannot be sealed (law L-m).
 129 |  - flags(): a third_person finding (a person other than the speaker shown as a still, photo or graphic while the words
 130 |    make a negative claim) and every on-screen text that asserts more than the words. They are sealed, never a reject.
 131 | +- RULING 93 (23:58 ET Nov 13): question 4 (burned_in): every ticker, crawl, lower third or channel bug burned into
 132 | +  the source, and how the 9:16 version treats it. layout_block(): a ticker or crawl, or a lower third or bug that is
 133 | +  not wholly in the 16:9, that the 9:16 edge would cut mid-word, or that covers the speaker, makes the clip NOT
 134 | +  eligible in any role (per clip, never by channel name); one that sits whole in the 16:9 and wholly in or out of the
 135 | +  9:16 is eligible and sealed as a "burned_in" FLAG for the orchestrator.
 136 |  - hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 137 |    speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 138 |    third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 139 | @@ -27,10 +32,13 @@ import os
 140 |  import subprocess
 141 |  import threading
 142 |  
 143 | -VERSION = "visual-1"
 144 | +VERSION = "visual-2"                     # RULING 93 (23:58 ET Nov 13): question 4, burned-in text and the 9:16
 145 |  ROLE = "visual_check"
 146 |  TILES, EVERY_S, TILE_W = 8, 2.0, 480
 147 |  HOW = ("still", "photo", "graphic", "none")
 148 | +BURNED = ("ticker", "crawl", "lower_third", "bug")      # ruling 93: question 4's kinds
 149 | +RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
 150 | +IN_9X16 = ("whole", "out", "cut")
 151 |  FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 152 |  CACHE_LOCK = threading.Lock()
 153 |  TEXTS_MAX, TEXT_CHARS = 12, 200          # audit 1541 C2: a verbose reply never bloats the sealed pin
 154 | @@ -40,7 +48,7 @@ The image is a contact sheet of {n} frames of the clip, left to right and top to
 155 |  the source video (seconds). The clip's words, as spoken:
 156 |  "{text}"
 157 |  
 158 | -Answer three questions from the frames only:
 159 | +Answer four questions from the frames only:
 160 |  1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
 161 |     person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 162 |     a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 163 | @@ -48,12 +56,22 @@ Answer three questions from the frames only:
 164 |  2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 165 |     words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 166 |  3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 167 | +4. burned_in: every piece of text or graphic burned into the SOURCE picture that stays on screen: a ticker or a crawl
 168 | +   (text that runs or scrolls across the frame), a lower third (a name or headline strap), or a channel bug (a logo or
 169 | +   watermark). Not subtitles of the spoken words. For each say whether it sits WHOLLY inside the frame, and how the
 170 | +   VERTICAL 9:16 version would treat it. The 9:16 version shows, for ONE speaker, a full-height strip about one third
 171 | +   of the frame's width, centred on the speaker's face; for two or three people, a band around each face, stacked; for
 172 | +   a shared screen (a chart, a slide, b-roll), the whole frame. "in_9x16" is "whole" (wholly inside the 9:16 picture),
 173 | +   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). "covers_speaker": does it cover
 174 | +   the speaking person's face or mouth?
 175 |  
 176 |  Return ONLY this JSON object:
 177 |  {{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 178 |    "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 179 |   "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 180 | - "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}}}}"""
 181 | + "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}},
 182 | + "burned_in": [{{"kind": "ticker|crawl|lower_third|bug", "text": "<its text, copied>", "whole_in_16x9": true or false,
 183 | +   "in_9x16": "whole|out|cut", "covers_speaker": true or false}}]}}"""
 184 |  
 185 |  
 186 |  def load_cache(path):
 187 | @@ -171,10 +189,15 @@ def _opt_str(x):
 188 |  
 189 |  
 190 |  def check(v):
 191 | -    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third"}."""
 192 | -    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third"}:
 193 | -        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third")
 194 | -    tp, ost, lt = v["third_person"], v["on_screen_text"], v["lower_third"]
 195 | +    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third", "burned_in"}."""
 196 | +    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third", "burned_in"}:
 197 | +        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third, burned_in")
 198 | +    tp, ost, lt, bi = v["third_person"], v["on_screen_text"], v["lower_third"], v["burned_in"]
 199 | +    if not isinstance(bi, list) or any(
 200 | +            not isinstance(x, dict) or x.get("kind") not in BURNED or not isinstance(x.get("text"), str) or
 201 | +            type(x.get("whole_in_16x9")) is not bool or x.get("in_9x16") not in IN_9X16 or
 202 | +            type(x.get("covers_speaker")) is not bool for x in bi):
 203 | +        raise ValueError("burned_in out of contract (ruling 93)")
 204 |      if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
 205 |              type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
 206 |          raise ValueError("third_person out of contract")
 207 | @@ -191,7 +214,10 @@ def check(v):
 208 |              "on_screen_text": [{"text": x["text"].strip()[:TEXT_CHARS], "asserts_beyond_words": x["asserts_beyond_words"],
 209 |                                  "why": str(x.get("why") or "").strip()[:TEXT_CHARS]} for x in keep],
 210 |              **({"on_screen_text_truncated": len(texts) - len(keep)} if len(texts) > len(keep) else {}),
 211 | -            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))}}
 212 | +            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))},
 213 | +            "burned_in": [{"kind": x["kind"], "text": x["text"].strip()[:TEXT_CHARS],
 214 | +                           "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"],
 215 | +                           "covers_speaker": x["covers_speaker"]} for x in bi][:TEXTS_MAX]}
 216 |  
 217 |  
 218 |  def flags(v):
 219 | @@ -202,7 +228,35 @@ def flags(v):
 220 |          out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
 221 |      out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 222 |              if x["asserts_beyond_words"]]
 223 | -    return out
 224 | +    out += [{"kind": "burned_in", "text": x["text"], "item": x["kind"], "in_9x16": x["in_9x16"]}   # ruling 93: an
 225 | +            for x in v.get("burned_in") or [] if not burned_block(x)]            # eligible lower third or bug,
 226 | +    return out                                                                   # flagged for the orchestrator
 227 | +
 228 | +
 229 | +def burned_block(x):
 230 | +    """RULING 93 on one burned-in item -> why it makes the clip NOT eligible, or None (eligible, flagged): a ticker or
 231 | +    a crawl; a lower third or bug that is not wholly inside the 16:9, that the 9:16 edge would cut through mid-word, or
 232 | +    that covers the speaker."""
 233 | +    if x["kind"] in RUNNING:
 234 | +        return f"a {x['kind']} ({x['text'][:80]!r}): not eligible"
 235 | +    if not x["whole_in_16x9"]:
 236 | +        return f"a {x['kind']} not wholly inside the 16:9 ({x['text'][:80]!r})"
 237 | +    if x["in_9x16"] == "cut":
 238 | +        return f"a {x['kind']} the 9:16 crop would cut through mid-word ({x['text'][:80]!r})"
 239 | +    if x["covers_speaker"]:
 240 | +        return f"a {x['kind']} that covers the speaker ({x['text'][:80]!r})"
 241 | +    return None
 242 | +
 243 | +
 244 | +def layout_block(rec):
 245 | +    """RULING 93 (23:58 ET Nov 13): why the clip may not be on screen in ANY role, or None. Not measured, or a record
 246 | +    without question 4 (an earlier version), is never a pass (law L-m); otherwise burned_block() on every item."""
 247 | +    if not (rec or {}).get("measured"):
 248 | +        return "its visual check is not measured (law L-m)"
 249 | +    if not isinstance(rec.get("burned_in"), list):
 250 | +        return "ruling 93: the burned-in text question was not asked (an earlier visual record)"
 251 | +    why = [w for w in (burned_block(x) for x in rec["burned_in"]) if w]
 252 | +    return ("ruling 93: " + "; ".join(why))[:300] if why else None
 253 |  
 254 |  
 255 |  def hook_block(rec):
 256 | @@ -222,7 +276,7 @@ def sealed(rec):
 257 |      """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 258 |      name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 259 |      out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 260 | -                               "backend", "replayed", "why") if k in rec}
 261 | +                               "burned_in", "backend", "replayed", "why") if k in rec}
 262 |      if isinstance(rec.get("sheet"), dict):
 263 |          out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 264 |      return out
 265 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 266 | index 17896e4..cd89e2d 100644
 267 | --- a/tests/eligibility/test_eligibility.py
 268 | +++ b/tests/eligibility/test_eligibility.py
 269 | @@ -6,8 +6,8 @@ pinned     every law constant equals the module it lives in today (editorial_sel
 270 |  parity     the ported helpers answer as today's (backward_reference, _same_statement, _word_sentences, _ends_statement)
 271 |  must-fail  one fixture per named reason (synthetic, plus real: Altcoin Daily's unpunctuated record, E-FAIL-033)
 272 |  must-pass  the PBX-approved preview's hook and two clips (references/pulse_preview_2026-11-11, frozen word
 273 | -           transcripts); its Bitcoin Magazine clip fails on layout_ineligible (has_chyron, DEC-12d came after) and on
 274 | -           its record's whole-record L-e readiness (one word 570 s away reads unpunctuated), on nothing in its text
 275 | +           transcripts); its Bitcoin Magazine clip fails on its record's whole-record L-e readiness (one word 570 s
 276 | +           away reads unpunctuated), on nothing in its text (ruling 93 retired DEC-12d's channel hold)
 277 |  Run: cd <repo> && python3 -m pytest -q tests/eligibility"""
 278 |  import json
 279 |  import os
 280 | @@ -185,11 +185,14 @@ class TestSource(unittest.TestCase):
 281 |          self.assertIn("not_current", E.eligible(naive, ctx()).names())
 282 |  
 283 |      def test_layout_is_a_fact_always_and_a_reason_on_screen(self):
 284 | -        bm = source([HOOK_TXT], channel="Bitcoin Magazine")    # has_chyron (DEC-12d)
 285 | -        ev = E.eligible(bm, ctx("evidence"))
 286 | -        self.assertTrue(ev.ok)
 287 | -        self.assertIs(ev.facts["layout_eligible"], False)
 288 | -        self.assertIn("layout_ineligible", E.eligible(bm, ctx("clip")).names())
 289 | +        bm = source([HOOK_TXT], channel="Bitcoin Magazine")    # has_chyron: RULING 93 (23:58 ET Nov 13) holds no
 290 | +        ev = E.eligible(bm, ctx("evidence"))                    # channel by name; its frames are judged per clip
 291 | +        self.assertTrue(ev.ok)                                  # (visual_pin.layout_block)
 292 | +        self.assertIs(ev.facts["layout_eligible"], True)
 293 | +        self.assertNotIn("layout_ineligible", E.eligible(bm, ctx("clip")).names())
 294 | +        nobody = source([HOOK_TXT], channel="No Such Channel")  # a channel with no registry id is still held
 295 | +        self.assertIs(E.eligible(nobody, ctx("evidence")).facts["layout_eligible"], False)
 296 | +        self.assertIn("layout_ineligible", E.eligible(nobody, ctx("clip")).names())
 297 |  
 298 |      def test_on_screen_needs_a_sentence_ready_word_record(self):
 299 |          seg = source([HOOK_TXT], timing="segment", method="yt_auto:en")
 300 | @@ -398,8 +401,8 @@ class TestSpan(unittest.TestCase):
 301 |          self.assertIn("no_story_statement", r.names())
 302 |  
 303 |      def test_every_reason_is_reported_not_only_the_first(self):
 304 | -        src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="Bitcoin Magazine",
 305 | -                     age_h=100)
 306 | +        src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="No Such Channel",
 307 | +                     age_h=100)                                      # no registry id: layout_ineligible (ruling 93)
 308 |          r = E.eligible(E.Span(src, 0, 0), ctx("hook", story=statements(E.Span(src, 0, 0))))
 309 |          for n in ("not_current", "layout_ineligible", "not_sentence_ready", "start_case", "duration"):
 310 |              self.assertIn(n, r.names())
 311 | @@ -454,7 +457,7 @@ class TestLineup(unittest.TestCase):
 312 |          r = self.lineup(story=s2, claim=s2[0], hook=None, clips=())
 313 |          self.assertIn("story_bitcoin_screen", r.names())
 314 |          self.assertIn("claim_no_bitcoin", r.names())
 315 | -        bm = source([CLIP_TXT], channel="Bitcoin Magazine", vid="M")
 316 | +        bm = source([CLIP_TXT], channel="No Such Channel", vid="M")   # no registry id (ruling 93: never by name)
 317 |          s3 = (E.Span(self.a, 0, 0), E.Span(bm, 0, 0))
 318 |          self.assertIn("story_layout_channels", self.lineup(story=s3, claim=s3[0], hook=None, clips=()).names())
 319 |          stale = source([CLIP2_TXT], channel="Natalie Brunell", vid="S", age_h=90)
 320 | @@ -548,10 +551,10 @@ class TestRealPreview(unittest.TestCase):
 321 |          for kind, sp, s in spans:
 322 |              r = E.eligible(sp, E.Context(self.now, REG, role=kind, story=story))
 323 |              if s["channel"] == "Bitcoin Magazine":
 324 | -                # DEC-12d (has_chyron) came after the approval; and its ~10-min frozen window transcript has one word
 325 | -                # (598.3 s, 570 s after this clip) in an unpunctuated stretch, which today's whole-record L-e rule
 326 | -                # (transcript_store.sentence_ready) rejects. Both are today's laws, measured, not this passage's text.
 327 | -                self.assertEqual(sorted(r.names()), ["layout_ineligible", "not_sentence_ready"], r.why())
 328 | +                # its ~10-min frozen window transcript has one word (598.3 s, 570 s after this clip) in an
 329 | +                # unpunctuated stretch, which today's whole-record L-e rule (transcript_store.sentence_ready) rejects:
 330 | +                # today's law, measured, not this passage's text. DEC-12d's channel hold is gone (ruling 93).
 331 | +                self.assertEqual(sorted(r.names()), ["not_sentence_ready"], r.why())
 332 |              else:
 333 |                  self.assertTrue(r.ok, f"{s['channel']}: {r.why()}")
 334 |  
 335 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 336 | index 5e25d43..044385c 100644
 337 | --- a/tests/package/funnel.py
 338 | +++ b/tests/package/funnel.py
 339 | @@ -125,7 +125,7 @@ DESC = {"opener": "opens on a pronoun or reply word that needs what came before
 340 |          "no_bitcoin": "does not name Bitcoin: regex `\\b(bitcoins?|btcs?)\\b` (T11, the old story selector's subject "
 341 |                        "screen; 'Bitcoiners', 'sats', 'Satoshi' do not count)",
 342 |          "too_many_sentences": "more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3)",
 343 | -        "layout_ineligible": "the channel has a burned-in chyron (registry has_chyron, DEC-12d)",
 344 | +        "layout_ineligible": "the channel has no registry id (ruling 93: never a hold by channel name)",
 345 |          "not_statement": "ends on a question",
 346 |          "hook_lead": "hook only: transcript gap before the first word < 80 ms",
 347 |          "start_case": "starts lower-case", "fragment": "not a sentence start / end", "too_short": "< 5 words",
 348 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 349 | index 1e3d997..dc22632 100644
 350 | --- a/tests/package/test_medley.py
 351 | +++ b/tests/package/test_medley.py
 352 | @@ -623,10 +623,10 @@ class Rig:
 353 |      def visual(self, router, m, work_dir, cache, seed=7, log=print):
 354 |          """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 355 |          self.visual_calls.append(m["moment_id"])
 356 | -        base = {"version": "visual-1", "measured": True, "flags": [],
 357 | +        base = {"version": "visual-2", "measured": True, "flags": [],
 358 |                  "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 359 |                                   "finding": "no third person"},
 360 | -                "on_screen_text": [], "lower_third": {"name": None, "text": None},
 361 | +                "on_screen_text": [], "lower_third": {"name": None, "text": None}, "burned_in": [],   # ruling 93
 362 |                  "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 363 |                  "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "usd_basis": "reported",
 364 |                  "cached": False}
 365 | @@ -1678,6 +1678,30 @@ class TestRuling70Visual(unittest.TestCase):
 366 |          self.assertIn("not measured", out["hook_pool"]["visual_blocked"]["h"])
 367 |          self.assertIsNone(out["package"])
 368 |  
 369 | +    TICKER = {"burned_in": [{"kind": "ticker", "text": "BTC 74,512 | ETH 2,410", "whole_in_16x9": True,
 370 | +                             "in_9x16": "cut", "covers_speaker": False}]}
 371 | +
 372 | +    def test_ruling_93_a_ticker_holds_the_clip_in_any_role_by_its_own_frames(self):
 373 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
 374 | +        self.assertIn("ruling 93: a ticker", out["hook_pool"]["visual_blocked"]["h"])     # it may not open
 375 | +        self.assertIsNone(out["package"])
 376 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 377 | +                  visuals={"y": self.TICKER})
 378 | +        out = rig.run()
 379 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])          # dropped and re-lined
 380 | +        self.assertIn("ruling 93: a ticker", out["tried"][0]["why"])
 381 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])                   # no write for it
 382 | +        self.assertIsNotNone(out["package"])
 383 | +
 384 | +    def test_ruling_93_a_whole_lower_third_is_eligible_and_flagged(self):
 385 | +        strap = {"kind": "lower_third", "text": "JOE CARLASARE", "whole_in_16x9": True, "in_9x16": "out",
 386 | +                 "covers_speaker": False}
 387 | +        flag = {"kind": "burned_in", "text": "JOE CARLASARE", "item": "lower_third", "in_9x16": "out"}
 388 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 389 | +                  visuals={"x": {"burned_in": [strap], "flags": [flag]}}).run()
 390 | +        self.assertIsNotNone(out["package"])
 391 | +        self.assertEqual(out["package"]["gates"]["visual"]["flags"], [dict(flag, segment=1)])
 392 | +
 393 |  
 394 |  class TestRuling66Candidate(unittest.TestCase):
 395 |      """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
 396 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 397 | index 0e62176..779e766 100644
 398 | --- a/tests/package/test_spotlight.py
 399 | +++ b/tests/package/test_spotlight.py
 400 | @@ -69,7 +69,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
 401 |               visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 402 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 403 |                                        "finding": "none"}, "on_screen_text": [],
 404 | -                     "lower_third": {"name": None, "text": None}},
 405 | +                     "lower_third": {"name": None, "text": None}, "burned_in": []},
 406 |               scorer_verdict=sv(text, 4.0),
 407 |               spotlight_source={"ok": True, "why": "layout 'conversation'", "turns": {"measured": False},
 408 |                                 "layout": {"measured": True, "layout": "conversation", "backend": "fake:vis",
 409 | @@ -495,7 +495,7 @@ class TestPackageFor(unittest.TestCase):
 410 |  class TestBuild(unittest.TestCase):
 411 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 412 |  
 413 | -    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None):
 414 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None):
 415 |          ctx = E.Context(NOW, REG)
 416 |          calls = {}
 417 |  
 418 | @@ -523,7 +523,8 @@ class TestBuild(unittest.TestCase):
 419 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 420 |                   (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
 421 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 422 | -                 (VP, "visual_for", lambda r, m, w, c: {"measured": True, "flags": [], "backend": "fake:vis"}),
 423 | +                 (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 424 | +                                                              "backend": "fake:vis"}, **(visual or {}))),
 425 |                   (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
 426 |                   (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
 427 |                   (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
 428 | @@ -578,6 +579,23 @@ class TestBuild(unittest.TestCase):
 429 |              out, calls = self.run_build(ms, {"a": 5})
 430 |          self.assertIs(calls["facts"][0]["never_delivered"], False)
 431 |  
 432 | +    def test_ruling_93_a_ticker_holds_a_clip_and_a_whole_strap_is_flagged_and_clean(self):
 433 | +        ms = [moment(mid="a", channel="A")]
 434 | +        tick = {"kind": "ticker", "text": "BTC 74,512", "whole_in_16x9": True, "in_9x16": "cut",
 435 | +                "covers_speaker": False}
 436 | +        out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [tick]})
 437 | +        self.assertNotIn("package_for", calls)
 438 | +        self.assertIn("ruling 93: a ticker", out["moments"]["a"]["out"])
 439 | +        strap = dict(tick, kind="lower_third", text="BILL MILLER IV", in_9x16="out")
 440 | +        out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [strap], "flags": [
 441 | +            {"kind": "burned_in", "text": "BILL MILLER IV", "item": "lower_third", "in_9x16": "out"}]})
 442 | +        self.assertEqual(calls["package_for"], ["a"])                   # eligible, flagged, still clean
 443 | +        self.assertTrue(SPOT.clean_visual({"measured": True, "burned_in": [strap], "flags": [
 444 | +            {"kind": "burned_in", "text": "BILL MILLER IV"}]}))
 445 | +        self.assertFalse(SPOT.clean_visual({"measured": True, "burned_in": [], "flags": [
 446 | +            {"kind": "on_screen_text", "text": "SCANDAL"}]}))           # a ruling-70 flag is not clean
 447 | +        self.assertFalse(SPOT.clean_visual({"measured": True, "flags": []}))       # no question 4: never
 448 | +
 449 |      def test_ruling_92_and_a_lock_with_no_verdict_stops(self):
 450 |          ms = [moment(mid="a", channel="A")]
 451 |          out, calls = self.run_build(ms, {"a": 5}, layout="reaction")
 452 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 453 | index 22f9647..0d3a635 100644
 454 | --- a/tests/package/test_visual_pin.py
 455 | +++ b/tests/package/test_visual_pin.py
 456 | @@ -19,7 +19,8 @@ from test_providers import Fake, router  # noqa: E402
 457 |  CLEAN = {"third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 458 |                            "finding": "only the host on camera"},
 459 |           "on_screen_text": [{"text": "SIMPLY BITCOIN", "asserts_beyond_words": False, "why": "the show's name"}],
 460 | -         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"}}
 461 | +         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"},
 462 | +         "burned_in": []}                                                        # ruling 93: question 4
 463 |  STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
 464 |                                    "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
 465 |               on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
 466 | @@ -63,6 +64,29 @@ class TestContract(unittest.TestCase):
 467 |          self.assertIn("not measured", VP.hook_block({"measured": False}))
 468 |          self.assertIn("not measured", VP.hook_block(None))
 469 |  
 470 | +    def test_ruling_93_burned_in_text_per_clip(self):
 471 | +        item = lambda kind, **k: dict({"kind": kind, "text": "BITCOIN 74,512 | ETH 2,410", "whole_in_16x9": True,
 472 | +                                       "in_9x16": "out", "covers_speaker": False}, **k)
 473 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True)
 474 | +        self.assertIsNone(VP.layout_block(rec()))                                       # nothing burned in
 475 | +        for kind in ("ticker", "crawl"):                                                # a ticker or crawl: never
 476 | +            self.assertIn(f"a {kind}", VP.layout_block(rec(item(kind))))
 477 | +        strap = item("lower_third", text="BILL MILLER IV | CIO, MILLER VALUE")
 478 | +        for ok in (dict(strap, in_9x16="whole"), dict(strap, in_9x16="out"), dict(strap, kind="bug", in_9x16="whole")):
 479 | +            self.assertIsNone(VP.layout_block(rec(ok)))                                 # eligible, and flagged
 480 | +            self.assertEqual([f["kind"] for f in VP.flags(VP.check(dict(CLEAN, burned_in=[ok])))], ["burned_in"])
 481 | +        for bad, word in ((dict(strap, in_9x16="cut"), "mid-word"), (dict(strap, covers_speaker=True), "covers"),
 482 | +                          (dict(strap, whole_in_16x9=False), "not wholly inside")):
 483 | +            self.assertIn(word, VP.layout_block(rec(bad)))                              # ... unless cut, covering,
 484 | +        self.assertIn("not measured", VP.layout_block({"measured": False}))             # or not whole in the 16:9
 485 | +        self.assertIn("not asked", VP.layout_block({"measured": True, "flags": []}))    # an earlier record: never
 486 | +        for bad in ([{"kind": "banner", "text": "x", "whole_in_16x9": True, "in_9x16": "out", "covers_speaker": False}],
 487 | +                    [dict(strap, in_9x16="partly")], [dict(strap, covers_speaker="no")], "none"):
 488 | +            with self.assertRaises(ValueError):
 489 | +                VP.check(dict(CLEAN, burned_in=bad))
 490 | +        self.assertIn("burned_in", VP.sealed(rec(strap)))
 491 | +        self.assertEqual(VP.VERSION, "visual-2")                                        # every clip asked again
 492 | +
 493 |      def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 494 |          class R:
 495 |              cached, usd = False, 0.37
 496 | diff --git a/tests/select_by_id/test_select_by_id.py b/tests/select_by_id/test_select_by_id.py
 497 | index eafecb0..51d8333 100644
 498 | --- a/tests/select_by_id/test_select_by_id.py
 499 | +++ b/tests/select_by_id/test_select_by_id.py
 500 | @@ -86,7 +86,9 @@ class TestMustPassPreview(Preview):
 501 |          Yahoo's 'Bitcoin slips below ...'); whether the format allows a tolerance is PBX's call (L-o; audit C2 L-2).
 502 |          The story marks every sentence that states the development: Natalie's three (the drop, the ETF outflows,
 503 |          no part in the Monday rally) and Yahoo's two statements; Yahoo's 'But I don't check it on an hourly basis.'
 504 | -        sits between them. Bitcoin Magazine's sentence counts as evidence (has_chyron) and never goes on screen.
 505 | +        sits between them. Bitcoin Magazine's sentence never goes on screen: since RULING 93 (23:58 ET Nov 13) no
 506 | +        channel is held by name (it now counts as a fourth layout channel), and its record fails the whole-record L-e
 507 | +        readiness (not_sentence_ready), as test_eligibility's preview test measures.
 508 |          With only Natalie's first sentence marked, D4 (a) rejects her next two (no back-reference): the same reason
 509 |          today's auto path stopped her window at 7.15 s (DoD 17:34)."""
 510 |          nat_rows, yah_rows = self.rows(self.table, "Natalie Brunell"), self.rows(self.table, "Yahoo Finance")
 511 | @@ -96,9 +98,10 @@ class TestMustPassPreview(Preview):
 512 |          st = S.choose_story(Scripted(reply(story=ids, claim=ids[0])), self.table, self.ctx)
 513 |          self.assertEqual(st.status, "accepted", st.attempts)
 514 |          self.assertEqual(st.claim.text, st.story[0].text)
 515 | -        self.assertEqual(st.eligibility.facts["story_layout_channels"], 3)
 516 | +        self.assertEqual(st.eligibility.facts["story_layout_channels"], 4)   # ruling 93: no channel by name
 517 |          lt, skipped = S.lineup_table(list(self.src.values()), st.story, self.ctx)
 518 | -        self.assertIn("layout_ineligible", skipped["jbDqdLytkNM"])   # never offered for the screen (DEC-12d)
 519 | +        self.assertNotIn("layout_ineligible", skipped["jbDqdLytkNM"])
 520 | +        self.assertIn("not_sentence_ready", skipped["jbDqdLytkNM"])   # never offered for the screen: its record
 521 |          self.assertFalse(any(r.source.video_id == "jbDqdLytkNM" for r in lt.rows))
 522 |          hook = self.rows(lt, "DataDash")
 523 |          nat, yah = self.rows(lt, "Natalie Brunell"), self.rows(lt, "Yahoo Finance")
 524 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that
another session renders into short Bitcoin videos). Only state what you can verify from the diff; if uncertain, say
so; do not guess. Be specific: file:line and a concrete input that breaks it.

Background (static):
- DEC-12d (Nov 11) held every clip of a channel the registry marks has_chyron (Bitcoin Magazine, CoinDesk) out of any
  on-screen role, by name: eligibility.layout_ok. The render's G10 TEXT CROP gate measured only those channels.
- RULING 70: the pin-stage VISUAL check (visual_pin): one contact sheet per clip, judged by a vision model; findings
  are sealed as FLAGS, never a reject by themselves, except that a third_person finding may not be the HOOK. A clip
  whose check is not measured is never a pass (law L-m).
- The medley build (package.build) sees every hook before any angle and every clip of a line-up before any write;
  the spotlight (spotlight.build, committed earlier tonight) needs "the visual check clean".

The order (verbatim): "RULING 93: DEC-12d IS MEASURED PER CLIP, NOT PER CHANNEL. ... THE RULE NOW: no channel is
layout_ineligible by name. Every clip, any channel, is judged on its own frames by the pin-stage visual check (ruling
70), which gains one question: 'is there burned-in running text (a ticker, a crawl) or a lower third that the 9:16
crop would cut through mid-word, or that covers the speaker?' A ticker or crawl = not eligible. A static lower third or
channel bug that sits whole in the 16:9 and is either wholly in or wholly out of the 9:16 crop = eligible, flagged for
me. The render's G10 stays as it is and runs on EVERY clip (not only has_chyron channels), still monitoring. The
has_chyron flag stays in the registry as a hint that orders the check, nothing more. YOUR SIDE: eligibility drops the
channel-name hold and reads the visual verdict."
The render's 9:16 (vertical_layout): one speaker = a fixed full-height strip centred on the face, about one third of
the width; two or three people = stacked bands; a shared screen = the whole frame, letterboxed.

The change:
1. eligibility.layout_ok: a registry channel with an id (has_chyron no longer holds); layout_ineligible only for a
   channel with no registry id.
2. visual_pin: VERSION visual-2 (every clip is asked again: the cache key holds the version); question 4 "burned_in"
   (kind ticker / crawl / lower_third / bug, text, whole_in_16x9, in_9x16 whole / out / cut, covers_speaker) in the
   prompt and in check(); burned_block() per item; layout_block(rec): not measured, a record without question 4, a
   ticker or crawl, or a lower third / bug that is not whole in the 16:9, that the 9:16 would cut mid-word, or that
   covers the speaker -> not eligible; otherwise eligible, and each item is a "burned_in" FLAG (flags()); sealed()
   keeps burned_in.
3. package.build: a hook's visual block is hook_block OR layout_block; a line-up clip (and the no-voice line-up's
   clips) blocked by layout_block is dropped and re-lined before any write, as an unmeasured one was.
4. spotlight.clean_visual: measured, not hook-blocked, not layout-blocked, no ruling-70 flag; a ruling-93 burned_in
   flag keeps it clean (eligible, flagged). The spotlight's visual gate row uses it.
5. Tests: the medley rig's records are visual-2; new cases (a ticker holds a hook and a line-up clip; a whole strap is
   eligible and flagged; the contract and each block reason); the eligibility and select_by_id tests that asserted the
   channel hold now assert ruling 93 (Bitcoin Magazine no longer held by name; a channel with no registry id still
   is; the preview's Bitcoin Magazine clip is still never on screen, now on its record's sentence readiness).

Check: that no channel is held by name anywhere in this path; that a ticker / crawl / cut / covering item can never
reach a pin; that an unmeasured or pre-ruling-93 record is never a pass; that a whole, static item is eligible and
flagged, never dropped; that medley pins sealed before the change still recompute (the seal reads the visual record
only through sealed(), whose new key appears only on new records). Answer with findings tagged <critical>, <high>,
<medium> (file:line, a concrete scenario), then "SHIP: yes / no / yes with conditions".

