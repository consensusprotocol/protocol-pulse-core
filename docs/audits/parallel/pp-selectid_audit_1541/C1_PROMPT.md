# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1541
# Branch: pp-selectid
# Generated: 2026-11-13 15:42 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1541/C1_STEP.diff (1042 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 8c184de..8ca333d 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -106,6 +106,29 @@
   6 |     ],
   7 |     "family": "grok"
   8 |    },
   9 | +  "xai_vision:grok-4.7": {
  10 | +   "vendor": "xai_vision",
  11 | +   "model": "grok-4.7",
  12 | +   "price_usd_per_1m": [
  13 | +    5,
  14 | +    25
  15 | +   ],
  16 | +   "temperature": 0,
  17 | +   "key_name": "XAI_API_KEY_MEDLEY",
  18 | +   "family": "grok"
  19 | +  },
  20 | +  "heimdall:nvidia/nemotron-3.5-super-vl": {
  21 | +   "vendor": "heimdall",
  22 | +   "model": "nvidia/nemotron-3.5-super-vl",
  23 | +   "price_usd_per_1m": [
  24 | +    3,
  25 | +    15
  26 | +   ],
  27 | +   "temperature": 0,
  28 | +   "min_out": 16000,
  29 | +   "family": "nemotron",
  30 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  31 | +  },
  32 |    "openai_stt:gpt-4o-transcribe-diarize": {
  33 |     "vendor": "openai_stt",
  34 |     "model": "gpt-4o-transcribe-diarize",
  35 | @@ -221,6 +244,14 @@
  36 |     ],
  37 |     "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
  38 |    },
  39 | +  "visual_check": {
  40 | +   "chain": [
  41 | +    "xai_vision:grok-4.7",
  42 | +    "heimdall:qwen/qwen3.8-27b",
  43 | +    "heimdall:nvidia/nemotron-3.5-super-vl"
  44 | +   ],
  45 | +   "what": "RULING 70 (orchestrator 15:29 Nov 13): visual_pin.visual_for, one contact sheet per clip: a third person shown as a still while the words make a negative claim, the source's on-screen text that asserts more than the words, the lower third; xAI first, the Heimdall image models (pipeline/visual_check.py's) as failover; fail closed"
  46 | +  },
  47 |    "transcribe": {
  48 |     "chain": [
  49 |      "openai_stt:gpt-4o-transcribe-diarize",
  50 | diff --git a/pipeline/package.py b/pipeline/package.py
  51 | index 978628c..0ee17d8 100644
  52 | --- a/pipeline/package.py
  53 | +++ b/pipeline/package.py
  54 | @@ -329,6 +329,8 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  55 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  56 |                          **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  57 |                             if m.get("trimmed_leading") else {}),
  58 | +                        **({"visual": __import__("visual_pin").sealed(m["visual"])}    # ruling 70: sealed
  59 | +                           if m.get("visual") else {}),
  60 |                          **({"scorer_verdict": verdict_of(m)}  # ruling 56: "seal only what it affirms" (the pin
  61 |                             if (verdict_of(m) or {}).get("affirmed") is True else {})}   # refuses any other)
  62 |                         for lb, m in zip(labels(len(segs)), segs)],
  63 | @@ -1151,6 +1153,12 @@ def hook_own(m):
  64 |  
  65 |  
  66 |  def can_open(m):
  67 | +    if m.get("visual_hook_block"):                       # RULING 70: its picture may not open the medley
  68 | +        return False
  69 | +    return _can_open(m)
  70 | +
  71 | +
  72 | +def _can_open(m):
  73 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
  74 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
  75 |      59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
  76 | @@ -2024,7 +2032,8 @@ def candidate_lineup(router, candidate, cleared, now):
  77 |  
  78 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  79 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  80 | -          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None):
  81 | +          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  82 | +          visual_cache=None):
  83 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  84 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  85 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  86 | @@ -2039,6 +2048,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  87 |      ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
  88 |      writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
  89 |      freshness next), each line-up opens on its angle's own hook and never swaps it.
  90 | +    RULING 70, THE VISUAL CHECK (visual_pin): every hook rated >= HOOK_MIN is seen right after the ratings, before any
  91 | +    angle is asked (a hook whose sheet shows a third person while its words make a negative claim, or that is not
  92 | +    measured, may not open: can_open); every clip of a line-up that passes the clips-alone verdict is seen before any
  93 | +    write (not measured: dropped and re-lined, law L-m). Findings are sealed as FLAGS on the segment, never a reject by
  94 | +    themselves; the "visual" row is required (package_pin.MEDLEY_GATES). visual_cache: the verdicts by moment and span.
  95 |      RULING 66, A PASSED LINE-UP IS KEPT: candidate (load_candidate) tries ONLY that line-up, after the same pool stages:
  96 |      no angle is asked for (its own angle and back-end), its clips must still form it (candidate_lineup), and it is
  97 |      judged and written with its own seeds, so its recorded calls are served from their recordings; it is never
  98 | @@ -2049,6 +2063,22 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  99 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 100 |      t0 = time.time()
 101 |      usd0 = _spent(spend)
 102 | +    import visual_pin as VP                            # ruling 70
 103 | +    vcache = VP.load_cache(visual_cache) if visual_cache else {}
 104 | +    out_visual = {"calls": 0, "cached": 0, "usd": 0.0, "unmeasured": 0, "flags": 0}
 105 | +
 106 | +    def see(ms_):                                      # RULING 70: the clips' sheets, judged (cached per moment)
 107 | +        todo = [m for m in ms_ if not (m.get("visual") or {}).get("measured")]
 108 | +        if todo:
 109 | +            with ThreadPoolExecutor(max_workers=4) as vp:
 110 | +                recs = list(vp.map(lambda m: VP.visual_for(router, m, work_dir, vcache), todo))
 111 | +            for m, rec in zip(todo, recs):
 112 | +                m["visual"] = rec
 113 | +                out_visual["cached" if rec.get("cached") else "calls"] += 1 if rec.get("measured") else 0
 114 | +                out_visual["usd"] = round(out_visual["usd"] + float(rec.get("usd") or 0.0), 6)
 115 | +                out_visual["unmeasured"] += 0 if rec.get("measured") else 1
 116 | +                out_visual["flags"] += len(rec.get("flags") or [])
 117 | +            VP.save_cache(visual_cache, vcache)
 118 |      ms, why = usable(moments, ctx, delivered, optout)
 119 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 120 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 121 | @@ -2134,10 +2164,25 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 122 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
 123 |                                                                        "cannot open (hook eligibility, G17a or the "
 124 |                                                                        "render's hook rule)")}
 125 | +    for m in cleared.values():
 126 | +        m.pop("visual_hook_block", None)
 127 | +    rated_open = [m for m in cleared.values() if can_open(m)]              # RULING 70: the hooks that would open,
 128 | +    see(rated_open)                                                          # seen before any angle is asked
 129 | +    blocked = {}
 130 | +    for m in rated_open:
 131 | +        why_v = VP.hook_block(m["visual"])
 132 | +        if why_v:
 133 | +            m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
 134 | +    out["visual"] = out_visual
 135 | +    if rated_open:
 136 | +        log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
 137 | +            + (f" ({'; '.join(f'{k}: {v[:90]}' for k, v in blocked.items())})" if blocked else "")
 138 | +            + f" ({time.time() - t0:.0f} s)")
 139 |      best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]
 140 |      out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
 141 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
 142 | -                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])]}
 143 | +                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
 144 | +                        "visual_blocked": blocked}
 145 |      log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} rated >= "
 146 |          f"{HOOK_MIN} on the hook's own job" + (f"; NOT RATED: {hook_err}" if hook_err else "") +
 147 |          f" ({time.time() - t0:.0f} s)")
 148 | @@ -2336,6 +2381,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 149 |                    "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
 150 |                                        "back to back with the sign-off only", "added_clip": added,
 151 |                                 "lineup_before": [m["moment_id"] for m in segs]}}
 152 | +        see(order)                                        # RULING 70: the added clip is seen too
 153 | +        vbad = [m["moment_id"] for m in order if not (m.get("visual") or {}).get("measured")]
 154 | +        if vbad:
 155 | +            note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
 156 | +            return None
 157 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 158 |          pk["medley"] = nv_med
 159 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 160 | @@ -2362,7 +2412,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 161 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 162 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 163 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 164 | -                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 165 | +                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 166 | +                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 167 |          import package_pin
 168 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 169 |          if problems:
 170 | @@ -2491,6 +2542,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 171 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 172 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 173 |                  extra, relined, w_used, written = "", False, 0, ()
 174 | +                see(segs)                                   # RULING 70: every clip seen before any write is paid
 175 | +                vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") for m in segs
 176 | +                        if not (m.get("visual") or {}).get("measured")}
 177 | +                if vbad or segs[0].get("visual_hook_block"):
 178 | +                    vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
 179 | +                    dropped |= set(vbad)
 180 | +                    doomed |= set(vbad)
 181 | +                    rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 182 | +                    relined, w_used = True, writes      # no write is paid
 183 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 184 |                  while w_used < writes:
 185 |                      if over_budget(ai):
 186 | @@ -2642,7 +2702,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 187 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 188 |                                              style=HS.lint_lines(pk["lines"]),
 189 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 190 | -                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 191 | +                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 192 | +                                            visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 193 |                      if not ok_c:
 194 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 195 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 196 | @@ -2722,7 +2783,7 @@ def _spent(spend):
 197 |  
 198 |  
 199 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 200 | -              hook=None, stand=None):
 201 | +              hook=None, stand=None, visual=None):
 202 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 203 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 204 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 205 | @@ -2797,4 +2858,12 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 206 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 207 |                                  medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 208 |             if stand is not None else {}),
 209 | +        **({"visual": dict(row(bool(visual) and all((v or {}).get("measured") is True for v in visual),
 210 | +                               sorted({str((v or {}).get("backend")) for v in visual}) or None,
 211 | +                               rep((v or {}).get("replayed") for v in visual), n=len(visual or []),
 212 | +                               measured=bool(visual) and all((v or {}).get("measured") is True for v in visual)),
 213 | +                           flags=[{"segment": i, **f} for i, v in enumerate(visual) for f in (v or {}).get("flags") or []],
 214 | +                           by_rule="visual_pin (ruling 70): one contact sheet per clip; a finding is a FLAG, sealed, "
 215 | +                                   "never a reject by itself")}
 216 | +           if visual is not None else {}),
 217 |      }
 218 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 219 | index 90c18f3..19330af 100644
 220 | --- a/pipeline/package_pin.py
 221 | +++ b/pipeline/package_pin.py
 222 | @@ -29,7 +29,8 @@ REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate
 223 |  # L-y (20:30): the clips-alone verdict and the medley's shape; ruling 6 (22:40): PBX's copy rules on every line;
 224 |  # hook_onset: G17a at the pin stage, after batch pin #1's render hold (01:39 ET Nov 13); stand_alone: the render's
 225 |  # STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 226 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone")
 227 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone",
 228 | +                "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 229 |  
 230 |  
 231 |  def required_gates(pk):
 232 | @@ -71,7 +72,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 233 |                  "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 234 |                                                             # retired by ruling 56: kept so its pins still recompute)
 235 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 236 | -                "attested")                                # ruling 67: the attested-text re-seal's record (re-sealed)
 237 | +                "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
 238 | +                "visual")                                  # ruling 70: the clip's visual record (flags, sheet sha)
 239 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 240 |                                                             # separate constant (a test holds them equal): the
 241 |                                                             # integrator's check_pin_only imports this module, which
 242 | @@ -279,7 +281,8 @@ def to_pin(pk, run_name):
 243 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 244 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 245 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 246 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict") if k in s},
 247 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual")
 248 | +                        if k in s},
 249 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 250 |      edl_vo = {"intro": pk["vo"]["intro"],
 251 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 252 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 253 | index 1eaba43..aa6c175 100644
 254 | --- a/pipeline/providers.py
 255 | +++ b/pipeline/providers.py
 256 | @@ -66,6 +66,25 @@ class ReplayMiss(Exception):
 257 |      """Offline replay has no recorded exchange for this call."""
 258 |  
 259 |  
 260 | +IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
 261 | +
 262 | +
 263 | +def is_vision(prompt):
 264 | +    """RULING 70: a VISION prompt is {"text": str, "images": [base64 JPEG, ...]}; only a back-end with vision = True
 265 | +    is asked it (the others are skipped for that call)."""
 266 | +    return isinstance(prompt, dict) and isinstance(prompt.get("text"), str) and isinstance(prompt.get("images"), list) \
 267 | +        and all(isinstance(i, str) and i for i in prompt["images"])
 268 | +
 269 | +
 270 | +def prompt_text(prompt):
 271 | +    """The prompt as text, for the spend estimate, the logs and the recordings: a vision prompt's text with each image
 272 | +    as its sha256 (a recording never stores the image; its key still covers the image bytes)."""
 273 | +    if not is_vision(prompt):
 274 | +        return prompt
 275 | +    return prompt["text"] + "".join(f"\n[image sha256={hashlib.sha256(i.encode()).hexdigest()}]"
 276 | +                                    for i in prompt["images"])
 277 | +
 278 | +
 279 |  @dataclass
 280 |  class Reply:
 281 |      text: str
 282 | @@ -140,6 +159,7 @@ def _with_backoff(fn, final_codes=()):
 283 |  
 284 |  class Backend:
 285 |      vendor = "?"
 286 | +    vision = False                   # ruling 70: True only where complete() takes a vision prompt
 287 |  
 288 |      def __init__(self, name, spec, env_path):
 289 |          self.name, self.spec, self.env_path = name, spec, env_path
 290 | @@ -159,8 +179,11 @@ class Backend:
 291 |          return max(int(self.spec.get("min_out", 0)), max_tokens)
 292 |  
 293 |      def upper_usd(self, prompt, max_tokens, system=None):
 294 | -        """The call's spend upper bound: every prompt character a token (a safe over-estimate) + the output cap."""
 295 | -        return self.usd({"in": len(prompt) + len(system or "") + 200, "out": self.max_out(max_tokens)})
 296 | +        """The call's spend upper bound: every prompt character a token (a safe over-estimate), IMAGE_TOKENS_UPPER per
 297 | +        image of a vision prompt, + the output cap."""
 298 | +        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
 299 | +        return self.usd({"in": len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img,
 300 | +                         "out": self.max_out(max_tokens)})
 301 |  
 302 |      def key(self, name):
 303 |          k = env_value(self.env_path, name)
 304 | @@ -260,8 +283,11 @@ def _reported(usd):
 305 |  
 306 |  class HeimdallBackend(OpenAIBackend):
 307 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
 308 | -    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
 309 | +    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire. A vision
 310 | +    prompt (ruling 70) goes as chat-completions content parts: the text, then each image as an image_url data URL, the
 311 | +    form pipeline/visual_check.py uses with these image models."""
 312 |      vendor = "heimdall"
 313 | +    vision = True
 314 |  
 315 |      def _base(self):
 316 |          if not self.spec.get("base_url"):
 317 | @@ -270,10 +296,13 @@ class HeimdallBackend(OpenAIBackend):
 318 |  
 319 |      def complete(self, prompt, max_tokens, seed, system=None):
 320 |          key = self.key("HEIMDALL_API_KEY")
 321 | +        content = prompt if not is_vision(prompt) else \
 322 | +            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
 323 | +                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
 324 |          body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
 325 |                  "temperature": self.spec.get("temperature", 0),
 326 |                  "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
 327 | -                             {"role": "user", "content": prompt}]}
 328 | +                             {"role": "user", "content": content}]}
 329 |          t0 = time.time()
 330 |          base = self._base()
 331 |          j = _with_backoff(lambda: _http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
 332 | @@ -384,6 +413,47 @@ class XAISearchBackend(Backend):
 333 |                        "out": int(u.get("output_tokens") or u.get("completion_tokens") or 0)}, time.time() - t0
 334 |  
 335 |  
 336 | +class XAIVisionBackend(Backend):
 337 | +    """RULING 70: xAI's Responses API with image input (docs.x.ai, image understanding: "type": "input_image", a data
 338 | +    URL, "detail": "high"; "store": false, since a server-side record can make image requests fail). Only a vision
 339 | +    prompt is asked here. Its cost is the vendor's own figure when the reply carries one (cost_in_usd_ticks)."""
 340 | +    vendor = "xai_vision"
 341 | +    vision = True
 342 | +    URL = "https://api.x.ai/v1/responses"
 343 | +    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
 344 | +
 345 | +    def max_out(self, max_tokens):
 346 | +        return max(int(self.spec.get("min_out", 8000)), max_tokens * 4)        # a reasoning model thinks inside it
 347 | +
 348 | +    def complete(self, prompt, max_tokens, seed, system=None):
 349 | +        if not is_vision(prompt):
 350 | +            raise RequestRejected("xai_vision takes a vision prompt only")
 351 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
 352 | +        parts = [{"type": "input_text", "text": prompt["text"]}] + [
 353 | +            {"type": "input_image", "image_url": "data:image/jpeg;base64," + i, "detail": "high"}
 354 | +            for i in prompt["images"]]
 355 | +        body = {"model": self.model, "max_output_tokens": self.max_out(max_tokens), "store": False,
 356 | +                "temperature": self.spec.get("temperature", 0),
 357 | +                "input": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
 358 | +                          {"role": "user", "content": parts}]}
 359 | +        t0 = time.time()
 360 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
 361 | +                          final_codes=(401, 402, 403))
 362 | +        text = j.get("output_text") or ""
 363 | +        if not text:
 364 | +            for item in j.get("output") or []:
 365 | +                for part in (item.get("content") or []) if isinstance(item, dict) else []:
 366 | +                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
 367 | +                        text += part.get("text") or ""
 368 | +        u = j.get("usage") or {}
 369 | +        reasoning = int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
 370 | +        out = int(u.get("output_tokens") or u.get("completion_tokens") or 0)
 371 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
 372 | +        return text, dict({"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
 373 | +                           "out": out + (reasoning if reasoning > out else 0)},
 374 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
 375 | +
 376 | +
 377 |  # ── transcription back-ends (law L-v 2's second recognition pass; role "transcribe") ──
 378 |  
 379 |  def _multipart(fields, file_field, path, content_type="audio/wav"):
 380 | @@ -483,7 +553,7 @@ class ElevenLabsTranscribe(STTBackend):
 381 |              time.time() - t0
 382 |  
 383 |  
 384 | -VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 385 | +VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "xai_vision": XAIVisionBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 386 |             "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}
 387 |  
 388 |  
 389 | @@ -718,6 +788,10 @@ class Router:
 390 |              why = self._skip(name, b, av, am, af)
 391 |              if why is None and isinstance(b, STTBackend):
 392 |                  why = "a transcription back-end (Router.transcribe)"
 393 | +            if why is None and is_vision(prompt) and not b.vision:
 394 | +                why = "no image input (ruling 70)"
 395 | +            if why is None and not is_vision(prompt) and isinstance(b, XAIVisionBackend):
 396 | +                why = "a vision back-end (ruling 70)"
 397 |              if why:
 398 |                  tried.append((name, why))
 399 |                  continue
 400 | @@ -745,7 +819,8 @@ class Router:
 401 |                  self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 402 |                  tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 403 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 404 | -                                "deadline_s": deadline_s, "seconds": deadline_s, "prompt_chars": len(prompt),
 405 | +                                "deadline_s": deadline_s, "seconds": deadline_s,
 406 | +                                "prompt_chars": len(prompt_text(prompt)),
 407 |                                  "max_tokens": max_tokens})
 408 |                  continue
 409 |              except RequestRejected as e:
 410 | @@ -765,7 +840,8 @@ class Router:
 411 |              if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
 412 |                  self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
 413 |                                  "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
 414 | -                                "prompt_chars": len(prompt), "max_tokens": max_tokens, "in": (usage or {}).get("in"),
 415 | +                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 416 | +                                "in": (usage or {}).get("in"),
 417 |                                  "out": (usage or {}).get("out")})
 418 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
 419 |                  tried.append((name, "refused this request: an empty reply"))
 420 | @@ -773,7 +849,8 @@ class Router:
 421 |              recorded = ""
 422 |              if path and isinstance(text, str) and text.strip():
 423 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 424 | -                                    "max_tokens": max_tokens, "system": system, "prompt": prompt, "text": text,
 425 | +                                    "max_tokens": max_tokens, "system": system, "prompt": prompt_text(prompt),
 426 | +                                    "text": text,
 427 |                                      "usage": usage, "usd": usd, "seconds": round(secs, 2)})
 428 |                  recorded = path
 429 |              return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 430 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 431 | new file mode 100644
 432 | index 0000000..3c302d0
 433 | --- /dev/null
 434 | +++ b/pipeline/visual_pin.py
 435 | @@ -0,0 +1,246 @@
 436 | +"""pipeline/visual_pin.py: RULING 70 (orchestrator 15:29 Nov 13), the pin-stage VISUAL check.
 437 | +
 438 | +"One contact sheet per clip, the three questions including lower_third; xAI first, Heimdall image models as failover;
 439 | +fail closed. A finding on third_person or on_screen_text does not reject the clip by itself: it is sealed as a FLAG
 440 | +that I and PBX see with the pin (text of the finding + the sheet), and a clip with a third_person finding may not be
 441 | +the HOOK unless the claim in the words is confirmed as reported fact by step A's context. lower_third feeds ruling 69
 442 | +as one more piece of evidence, never alone. Report the measured cost on the first build."
 443 | +
 444 | +Per clip (a moment's [start, end]):
 445 | +- fetch(): the span's video at <= 480p, yt-dlp download sections on CPU (as transcript_truth.audio_window fetches its
 446 | +  audio).
 447 | +- sheet(): at most TILES stills (the cut-in frame, one every EVERY_S seconds, the last frame), each labelled with its
 448 | +  time in the source, in ONE JPEG contact sheet (ffmpeg on CPU, PIL to tile). No GPU.
 449 | +- ONE verdict (role visual_check: xai_vision:grok-4.7, then the Heimdall image models), JSON, checked in code
 450 | +  (check()). A reply out of contract, or no answer, is retried once with a new seed, then the clip is NOT measured:
 451 | +  it cannot be sealed (law L-m).
 452 | +- flags(): a third_person finding (a person other than the speaker shown as a still, photo or graphic while the words
 453 | +  make a negative claim) and every on-screen text that asserts more than the words. They are sealed, never a reject.
 454 | +- hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 455 | +  speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 456 | +  third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 457 | +Verdicts are cached per moment and span (cache=), like step A's: a clip is paid for once across builds."""
 458 | +import base64
 459 | +import hashlib
 460 | +import json
 461 | +import os
 462 | +import subprocess
 463 | +import threading
 464 | +
 465 | +VERSION = "visual-1"
 466 | +ROLE = "visual_check"
 467 | +TILES, EVERY_S, TILE_W = 8, 2.0, 480
 468 | +HOW = ("still", "photo", "graphic", "none")
 469 | +FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 470 | +CACHE_LOCK = threading.Lock()
 471 | +
 472 | +PROMPT = """You check what a VIEWER SEES in one clip of another channel's video, before it is cut into ours.
 473 | +The image is a contact sheet of {n} frames of the clip, left to right and top to bottom, each labelled with its time in
 474 | +the source video (seconds). The clip's words, as spoken:
 475 | +"{text}"
 476 | +
 477 | +Answer three questions from the frames only:
 478 | +1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
 479 | +   person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 480 | +   a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 481 | +   text on the screen names a person.
 482 | +2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 483 | +   words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 484 | +3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 485 | +
 486 | +Return ONLY this JSON object:
 487 | +{{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 488 | +  "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 489 | + "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 490 | + "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}}}}"""
 491 | +
 492 | +
 493 | +def load_cache(path):
 494 | +    try:
 495 | +        with open(path) as f:
 496 | +            d = json.load(f)
 497 | +        return d if isinstance(d, dict) else {}
 498 | +    except (OSError, ValueError):
 499 | +        return {}
 500 | +
 501 | +
 502 | +def save_cache(path, cache):
 503 | +    if not path:
 504 | +        return
 505 | +    with CACHE_LOCK:
 506 | +        with open(path + ".tmp", "w") as f:
 507 | +            json.dump(cache, f, indent=1, sort_keys=True)
 508 | +        os.replace(path + ".tmp", path)
 509 | +
 510 | +
 511 | +def key(m):
 512 | +    return f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}"
 513 | +
 514 | +
 515 | +def times(dur, every=EVERY_S, tiles=TILES):
 516 | +    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame; at most `tiles`,
 517 | +    the first and the last always kept."""
 518 | +    last = max(0.0, dur - 0.05)
 519 | +    ts = [0.0]
 520 | +    t = every
 521 | +    while t < last - 0.25:
 522 | +        ts.append(round(t, 2))
 523 | +        t += every
 524 | +    if last > 0:
 525 | +        ts.append(round(last, 2))
 526 | +    if len(ts) > tiles:                                  # too many for one sheet: evenly spaced, both ends kept
 527 | +        ts = [round(last * i / (tiles - 1), 2) for i in range(tiles)]
 528 | +    return ts
 529 | +
 530 | +
 531 | +def fetch(video_id, start, end, work_dir):
 532 | +    """The span's video at <= 480p (yt-dlp download sections, CPU) -> the file's path."""
 533 | +    d = os.path.join(work_dir, "visual")
 534 | +    os.makedirs(d, exist_ok=True)
 535 | +    stem = f"{video_id}_{int(start * 1000)}_{int(end * 1000)}"
 536 | +    have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
 537 | +    if not have:
 538 | +        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
 539 | +                        f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
 540 | +                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
 541 | +        have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
 542 | +    if not have:
 543 | +        raise OSError(f"no video fetched for {stem}")
 544 | +    return os.path.join(d, have[0])
 545 | +
 546 | +
 547 | +def sheet(video, start, end, work_dir):
 548 | +    """ONE contact sheet of the clip -> (its path, sha256, the stills' source times)."""
 549 | +    from PIL import Image, ImageDraw
 550 | +    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
 551 | +                       capture_output=True, text=True, check=True, timeout=30)
 552 | +    dur = min(float(r.stdout.strip()), end - start)
 553 | +    offs = times(dur)
 554 | +    d = os.path.join(work_dir, "visual")
 555 | +    tiles = []
 556 | +    for i, t in enumerate(offs):
 557 | +        out = os.path.join(d, f"_still_{os.getpid()}_{threading.get_ident()}_{i}.jpg")
 558 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
 559 | +                        f"scale={TILE_W}:-2", "-q:v", "3", out], check=True, timeout=60)
 560 | +        with Image.open(out) as im:
 561 | +            tiles.append(im.convert("RGB").copy())
 562 | +        os.remove(out)
 563 | +    cols = min(4, len(tiles))
 564 | +    rows = (len(tiles) + cols - 1) // cols
 565 | +    w, h = tiles[0].size
 566 | +    canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
 567 | +    draw = ImageDraw.Draw(canvas)
 568 | +    for i, (im, t) in enumerate(zip(tiles, offs)):
 569 | +        x, y = (i % cols) * w, (i // cols) * h
 570 | +        canvas.paste(im.resize((w, h)), (x, y))
 571 | +        label = f"{start + t:.2f} s"
 572 | +        draw.rectangle([x, y, x + 9 * len(label), y + 16], fill=(0, 0, 0))
 573 | +        draw.text((x + 3, y + 2), label, fill=(255, 255, 255))
 574 | +    tmp = os.path.join(d, f"_sheet_{os.getpid()}_{threading.get_ident()}.jpg")
 575 | +    canvas.save(tmp, "JPEG", quality=85)
 576 | +    with open(tmp, "rb") as f:
 577 | +        sha = hashlib.sha256(f.read()).hexdigest()
 578 | +    path = os.path.join(d, f"visual_{sha[:16]}.jpg")
 579 | +    os.replace(tmp, path)
 580 | +    return path, sha, [round(start + t, 2) for t in offs]
 581 | +
 582 | +
 583 | +def _json(text):
 584 | +    t = str(text or "")
 585 | +    a, b = t.find("{"), t.rfind("}")
 586 | +    if a < 0 or b < a:
 587 | +        raise ValueError("no JSON object in the reply")
 588 | +    return json.loads(t[a:b + 1])
 589 | +
 590 | +
 591 | +def _opt_str(x):
 592 | +    return x.strip() if isinstance(x, str) and x.strip() and x.strip().lower() not in ("null", "none") else None
 593 | +
 594 | +
 595 | +def check(v):
 596 | +    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third"}."""
 597 | +    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third"}:
 598 | +        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third")
 599 | +    tp, ost, lt = v["third_person"], v["on_screen_text"], v["lower_third"]
 600 | +    if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
 601 | +            type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
 602 | +        raise ValueError("third_person out of contract")
 603 | +    if not isinstance(ost, list) or any(not isinstance(x, dict) or not isinstance(x.get("text"), str) or
 604 | +                                        type(x.get("asserts_beyond_words")) is not bool for x in ost):
 605 | +        raise ValueError("on_screen_text out of contract")
 606 | +    if not isinstance(lt, dict):
 607 | +        raise ValueError("lower_third out of contract")
 608 | +    return {"third_person": {"shown": tp["shown"], "how": tp["how"], "words_negative": tp["words_negative"],
 609 | +                             "name_on_screen": _opt_str(tp.get("name_on_screen")), "finding": tp["finding"].strip()},
 610 | +            "on_screen_text": [{"text": x["text"].strip(), "asserts_beyond_words": x["asserts_beyond_words"],
 611 | +                                "why": str(x.get("why") or "").strip()} for x in ost if x["text"].strip()],
 612 | +            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))}}
 613 | +
 614 | +
 615 | +def flags(v):
 616 | +    """RULING 70: the findings sealed as FLAGS (never a reject by themselves)."""
 617 | +    out = []
 618 | +    tp = v["third_person"]
 619 | +    if tp["shown"] and tp["how"] in ("still", "photo", "graphic") and tp["words_negative"]:
 620 | +        out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
 621 | +    out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 622 | +            if x["asserts_beyond_words"]]
 623 | +    return out
 624 | +
 625 | +
 626 | +def hook_block(rec):
 627 | +    """Why this clip may not be the HOOK (ruling 70), or None."""
 628 | +    if not (rec or {}).get("measured"):
 629 | +        return "its visual check is not measured (law L-m)"
 630 | +    if any(f["kind"] == "third_person" for f in rec.get("flags") or []):
 631 | +        return ("ruling 70: a third person is shown as a still while the words make a negative claim, and step A's "
 632 | +                "context does not confirm the claim as reported fact (step A passes only the speaker's own view)")
 633 | +    return None
 634 | +
 635 | +
 636 | +def sealed(rec):
 637 | +    """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 638 | +    name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 639 | +    out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 640 | +                               "backend", "replayed", "why") if k in rec}
 641 | +    if isinstance(rec.get("sheet"), dict):
 642 | +        out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 643 | +    return out
 644 | +
 645 | +
 646 | +def visual_for(router, m, work_dir, cache, seed=7, log=print):
 647 | +    """The clip's visual record (cached per moment and span). Not measured on any failure: never a pass (law L-m).
 648 | +    -> {"version", "measured", "flags", "third_person", "on_screen_text", "lower_third", "sheet" {"name", "sha256",
 649 | +    "times", "path"}, "backend", "replayed", "usd", "cached"} or {"measured": False, "why"}."""
 650 | +    import providers as P
 651 | +    k = key(m)
 652 | +    if cache is not None and k in cache and cache[k].get("measured"):
 653 | +        return dict(cache[k], cached=True, usd=0.0)
 654 | +    try:
 655 | +        video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
 656 | +        path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
 657 | +        with open(path, "rb") as f:
 658 | +            b64 = base64.b64encode(f.read()).decode()
 659 | +    except Exception as e:                       # noqa: BLE001  no sheet: not measured (law L-m)
 660 | +        return {"version": VERSION, "measured": False, "why": f"no contact sheet: {type(e).__name__}: {str(e)[:160]}"}
 661 | +    prompt = {"text": PROMPT.format(n=len(ts), text=str(m.get("text") or "").replace('"', "'")), "images": [b64]}
 662 | +    why = None
 663 | +    for sd in (seed, seed + 1):
 664 | +        r = None
 665 | +        try:
 666 | +            r = router.call(ROLE, prompt, 1500, sd)
 667 | +            v = check(_json(r.text))
 668 | +            rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
 669 | +                   "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
 670 | +                   "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
 671 | +                   "usd": 0.0 if getattr(r, "cached", False) else float(getattr(r, "usd", 0.0) or 0.0),
 672 | +                   "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
 673 | +            if cache is not None and not rec["replayed"]:
 674 | +                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}
 675 | +            return rec
 676 | +        except Exception as e:                   # noqa: BLE001
 677 | +            if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
 678 | +                router.reject(r)
 679 | +            why = f"{type(e).__name__}: {str(e)[:200]}"
 680 | +    return {"version": VERSION, "measured": False, "why": f"no verdict in contract after two tries: {why}",
 681 | +            "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path}}
 682 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 683 | index ab65cbf..334b8c1 100644
 684 | --- a/tests/package/proof_ledger.py
 685 | +++ b/tests/package/proof_ledger.py
 686 | @@ -173,7 +173,8 @@ def main(argv=None):
 687 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 688 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 689 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 690 | -              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 691 | +              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 692 | +              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"))       # ruling 70
 693 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 694 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 695 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 696 | @@ -222,6 +223,13 @@ def main(argv=None):
 697 |                                                name="MOMENTS_PIN_LEDGER.json")
 698 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 699 |                            "package_sha256": pin["moments_package"]["package_sha256"]}
 700 | +            import shutil                                # ruling 70: each segment's sheet beside the pin
 701 | +            for sg in pin["segments"]:
 702 | +                sh = (sg.get("visual") or {}).get("sheet") or {}
 703 | +                if sh.get("name"):
 704 | +                    src = os.path.join(a.work_dir, "visual", sh["name"])
 705 | +                    if os.path.exists(src):
 706 | +                        shutil.copyfile(src, os.path.join(out_dir, sh["name"]))
 707 |              say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 708 |                  f"pin {path}")
 709 |          except package_pin.PinRefused as e:
 710 | @@ -235,6 +243,10 @@ def main(argv=None):
 711 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 712 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 713 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 714 | +    vis = res.get("visual") or {}
 715 | +    say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) judged, {vis.get('cached', 0)} cached, "
 716 | +        f"{vis.get('unmeasured', 0)} not measured, {vis.get('flags', 0)} flag(s); measured cost ${vis.get('usd', 0):.4f} "
 717 | +        f"(the router's figure: vendor-reported where the reply carries it)")
 718 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 719 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 720 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
 721 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 722 | index 33c7418..ee2d718 100644
 723 | --- a/tests/package/test_medley.py
 724 | +++ b/tests/package/test_medley.py
 725 | @@ -465,8 +465,8 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 726 |  
 727 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 728 |          pk = self.build()
 729 | -        self.assertEqual(package_pin.required_gates(pk)[-5:], ("medley", "ly_shape", "house_style", "hook_onset",
 730 | -                                                               "stand_alone"))
 731 | +        self.assertEqual(package_pin.required_gates(pk)[-6:], ("medley", "ly_shape", "house_style", "hook_onset",
 732 | +                                                               "stand_alone", "visual"))
 733 |          pk["gates"] = self.gates(pk)
 734 |          pin = package_pin.to_pin(spk(pk), "test")
 735 |          self.assertEqual(pin["label"], "bitcoin")     # the render's STAND_ALONE subject rests on it (audit 0310 C2)
 736 | @@ -523,7 +523,7 @@ class Rig:
 737 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 738 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 739 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 740 | -                 cached=False, candidate=None):
 741 | +                 cached=False, candidate=None, visuals=None):
 742 |          import providers as P
 743 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 744 |          self.takeaways, self.spend = list(takeaways or []), spend
 745 | @@ -533,6 +533,7 @@ class Rig:
 746 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 747 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 748 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 749 | +        self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 750 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 751 |          self.screens, self.events, self.a_seen = [], [], []
 752 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 753 | @@ -615,6 +616,17 @@ class Rig:
 754 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 755 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 756 |  
 757 | +    def visual(self, router, m, work_dir, cache, seed=7, log=print):
 758 | +        """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 759 | +        self.visual_calls.append(m["moment_id"])
 760 | +        base = {"version": "visual-1", "measured": True, "flags": [],
 761 | +                "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 762 | +                                 "finding": "no third person"},
 763 | +                "on_screen_text": [], "lower_third": {"name": None, "text": None},
 764 | +                "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 765 | +                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "cached": False}
 766 | +        return dict(base, **self.visuals.get(m["moment_id"], {}))
 767 | +
 768 |      def onset(self, m, *a, **k):
 769 |          """hook_onset.measure's record: the hook lead, and for a trimmed moment its trimmed cut ("trim")."""
 770 |          r = ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"} if m["moment_id"] in self.no_hook
 771 | @@ -661,12 +673,15 @@ class Rig:
 772 |              kw["scorer_verdicts_path"] = path
 773 |              stubs["render_scorer_sha"] = lambda *a, **k: "s" * 64       # the render's scorer code, as it is now
 774 |          saved = {k: getattr(PK, k) for k in stubs}
 775 | +        import visual_pin as VP
 776 | +        saved_vp, VP.visual_for = VP.visual_for, self.visual       # ruling 70
 777 |          try:
 778 |              for k, v in stubs.items():
 779 |                  setattr(PK, k, v)
 780 |              return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
 781 |                              spend=self.spend, **kw)
 782 |          finally:
 783 | +            VP.visual_for = saved_vp
 784 |              for k, v in saved.items():
 785 |                  setattr(PK, k, v)
 786 |              if path:
 787 | @@ -1588,6 +1603,72 @@ class TestRulings6264Search(unittest.TestCase):
 788 |          self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free
 789 |  
 790 |  
 791 | +class TestRuling70Visual(unittest.TestCase):
 792 | +    """RULING 70 (15:29): one contact sheet per clip; xAI first, Heimdall image models as failover; fail closed. A finding
 793 | +    is sealed as a FLAG, never a reject by itself; a third_person finding may not be the HOOK (step A confirms no claim
 794 | +    as reported fact: it passes only the speaker's own view)."""
 795 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 796 | +    TP = {"flags": [{"kind": "third_person", "text": "a photo of a CEO beside the host", "name_on_screen": None}],
 797 | +          "third_person": {"shown": True, "how": "photo", "words_negative": True, "name_on_screen": None,
 798 | +                           "finding": "a photo of a CEO beside the host"}}
 799 | +
 800 | +    def test_hooks_are_seen_before_the_angle_and_a_clean_package_seals_every_sheet(self):
 801 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 802 | +        out = rig.run()
 803 | +        self.assertLess(rig.events.index("hook_ratings"), rig.events.index("angle_write"))
 804 | +        self.assertEqual(rig.visual_calls[0], "h")                     # the hook, at the hook stage
 805 | +        self.assertEqual(sorted(set(rig.visual_calls)), ["h", "x", "y"])
 806 | +        pk = out["package"]
 807 | +        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
 808 | +        self.assertEqual([sg["visual"]["sheet"]["name"] for sg in pk["segments"]],
 809 | +                         ["visual_h.jpg", "visual_x.jpg", "visual_y.jpg"])
 810 | +        self.assertNotIn("path", pk["segments"][0]["visual"]["sheet"])  # never a scratch path in the seal
 811 | +        self.assertIn("visual", package_pin.MEDLEY_GATES)
 812 | +        pin = package_pin.to_pin(spk(pk), "r")
 813 | +        self.assertIn("visual", pin["segments"][1])
 814 | +        segs = [{k: v for k, v in sg.items() if k != "visual"} for sg in pin["segments"]]
 815 | +        mp = pin["moments_package"]
 816 | +        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
 817 | +                                             mp["gates"], mp.get("btc_screen")), mp["package_sha256"])   # sealed
 818 | +
 819 | +    def test_a_clip_flag_is_sealed_never_a_reject(self):
 820 | +        flag = {"flags": [{"kind": "on_screen_text", "text": "CEO SCANDAL", "why": "the words say no such thing"}]}
 821 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"x": flag}).run()
 822 | +        pk = out["package"]
 823 | +        self.assertIsNotNone(pk)
 824 | +        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
 825 | +        self.assertEqual(pk["gates"]["visual"]["flags"], [dict(flag["flags"][0], segment=1)])
 826 | +        self.assertEqual(pk["segments"][1]["visual"]["flags"], flag["flags"])
 827 | +
 828 | +    def test_a_third_person_finding_may_not_open_and_no_angle_is_written_for_it(self):
 829 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TP})
 830 | +        out = rig.run()
 831 | +        self.assertIsNone(out["package"])
 832 | +        self.assertIn("h", out["hook_pool"]["visual_blocked"])
 833 | +        self.assertIn("ruling 70", out["hook_pool"]["visual_blocked"]["h"])
 834 | +        self.assertNotIn("angle_write", rig.events)                      # "no hook in the pool": nothing written
 835 | +        self.assertTrue(out["why_none"].startswith("no hook in the pool"), out["why_none"])
 836 | +
 837 | +    def test_a_third_person_clip_that_is_not_the_hook_is_kept_with_its_flag(self):
 838 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"y": self.TP}).run()
 839 | +        self.assertIsNotNone(out["package"])
 840 | +        self.assertEqual([f["kind"] for f in out["package"]["gates"]["visual"]["flags"]], ["third_person"])
 841 | +
 842 | +    def test_an_unmeasured_clip_is_dropped_before_any_write(self):
 843 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 844 | +                  visuals={"y": {"measured": False, "why": "no verdict in contract after two tries"}})
 845 | +        out = rig.run()
 846 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
 847 | +        self.assertTrue(out["tried"][0]["why"].startswith("ruling 70: y: no verdict"), out["tried"][0]["why"])
 848 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])     # no write for the line-up with y
 849 | +        self.assertIsNotNone(out["package"])
 850 | +
 851 | +    def test_an_unmeasured_hook_may_not_open(self):
 852 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": {"measured": False, "why": "no sheet"}}).run()
 853 | +        self.assertIn("not measured", out["hook_pool"]["visual_blocked"]["h"])
 854 | +        self.assertIsNone(out["package"])
 855 | +
 856 | +
 857 |  class TestRuling66Candidate(unittest.TestCase):
 858 |      """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
 859 |      from it asks no angle, tries exactly its clips in its order with its own seeds (so its recorded calls are served
 860 | @@ -2372,7 +2453,9 @@ class TestNoVoiceRealGates(unittest.TestCase):
 861 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 862 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 863 |                                     hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"},
 864 | -                                   stand=PK.stand_alone_check(pk["segments"]))
 865 | +                                   stand=PK.stand_alone_check(pk["segments"]),
 866 | +                                   visual=[{"measured": True, "replayed": False, "backend": "xai_vision:grok-4.7",
 867 | +                                            "flags": []} for _ in pk["segments"]])      # ruling 70
 868 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 869 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 870 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 871 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 872 | new file mode 100644
 873 | index 0000000..4873400
 874 | --- /dev/null
 875 | +++ b/tests/package/test_visual_pin.py
 876 | @@ -0,0 +1,165 @@
 877 | +#!/usr/bin/env python3
 878 | +"""RULING 70 (orchestrator 15:29 Nov 13): the pin-stage visual check (pipeline/visual_pin.py) and the router's vision
 879 | +prompt (providers.is_vision / prompt_text, the xai_vision and Heimdall back-ends). Offline: no network, no model."""
 880 | +import base64
 881 | +import json
 882 | +import os
 883 | +import sys
 884 | +import tempfile
 885 | +import unittest
 886 | +
 887 | +HERE = os.path.dirname(os.path.abspath(__file__))
 888 | +REPO = os.path.dirname(os.path.dirname(HERE))
 889 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 890 | +sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
 891 | +import providers as P  # noqa: E402
 892 | +import visual_pin as VP  # noqa: E402
 893 | +from test_providers import Fake, router  # noqa: E402
 894 | +
 895 | +CLEAN = {"third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 896 | +                          "finding": "only the host on camera"},
 897 | +         "on_screen_text": [{"text": "SIMPLY BITCOIN", "asserts_beyond_words": False, "why": "the show's name"}],
 898 | +         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"}}
 899 | +STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
 900 | +                                  "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
 901 | +             on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
 902 | +                              "why": "the words name no company"}])
 903 | +M = {"moment_id": "m1", "video_id": "vid00000001", "start": 236.688, "end": 253.308, "text": "A CEO makes a mistake."}
 904 | +
 905 | +
 906 | +class VFake(Fake):
 907 | +    vision = True
 908 | +
 909 | +
 910 | +class TestContract(unittest.TestCase):
 911 | +    def test_the_stills_are_the_cut_in_one_every_two_seconds_and_the_last(self):
 912 | +        self.assertEqual(VP.times(16.62), [0.0, 2.37, 4.73, 7.1, 9.47, 11.84, 14.2, 16.57])   # evenly spaced
 913 | +        self.assertEqual(VP.times(5.0), [0.0, 2.0, 4.0, 4.95])
 914 | +        self.assertEqual(len(VP.times(60.0)), VP.TILES)
 915 | +
 916 | +    def test_a_reply_in_contract_and_out_of_it(self):
 917 | +        v = VP.check(STILL)
 918 | +        self.assertIsNone(v["third_person"]["name_on_screen"])               # "null" text is no name
 919 | +        self.assertEqual([f["kind"] for f in VP.flags(v)], ["third_person", "on_screen_text"])
 920 | +        self.assertEqual(VP.flags(VP.check(CLEAN)), [])
 921 | +        self.assertEqual(VP.check(CLEAN)["lower_third"]["name"], "Mark W. Yusko")
 922 | +        for bad in (dict(CLEAN, extra=1), dict(CLEAN, third_person=dict(CLEAN["third_person"], how="video")),
 923 | +                    dict(CLEAN, third_person=dict(CLEAN["third_person"], shown="yes")),
 924 | +                    dict(CLEAN, on_screen_text=[{"text": "x"}]), dict(CLEAN, lower_third="Mark")):
 925 | +            with self.assertRaises(ValueError):
 926 | +                VP.check(bad)
 927 | +
 928 | +    def test_a_third_person_finding_or_no_measure_blocks_the_hook_but_flags_never_reject(self):
 929 | +        self.assertIsNone(VP.hook_block({"measured": True, "flags": VP.flags(VP.check(CLEAN))}))
 930 | +        self.assertIsNone(VP.hook_block({"measured": True, "flags": [{"kind": "on_screen_text", "text": "x"}]}))
 931 | +        self.assertIn("ruling 70", VP.hook_block({"measured": True, "flags": VP.flags(VP.check(STILL))}))
 932 | +        self.assertIn("not measured", VP.hook_block({"measured": False}))
 933 | +        self.assertIn("not measured", VP.hook_block(None))
 934 | +
 935 | +    def test_the_seal_never_holds_a_scratch_path_or_a_cost(self):
 936 | +        s = VP.sealed({"version": "v", "measured": True, "flags": [], "third_person": {}, "on_screen_text": [],
 937 | +                       "lower_third": {}, "backend": "b", "replayed": False, "usd": 0.01, "cached": True,
 938 | +                       "usage": {"in": 1}, "sheet": {"name": "n.jpg", "sha256": "s", "times": [1.0], "path": "/tmp/x"}})
 939 | +        self.assertEqual(s["sheet"], {"name": "n.jpg", "sha256": "s", "times": [1.0]})
 940 | +        self.assertFalse({"usd", "cached", "usage"} & set(s))
 941 | +
 942 | +
 943 | +class TestVisualFor(unittest.TestCase):
 944 | +    def setUp(self):
 945 | +        self.tmp = tempfile.TemporaryDirectory()
 946 | +        self.sheet = os.path.join(self.tmp.name, "visual_x.jpg")
 947 | +        with open(self.sheet, "wb") as f:
 948 | +            f.write(b"\xff\xd8 not a real jpeg")
 949 | +        self.saved = VP.fetch, VP.sheet
 950 | +        VP.fetch = lambda vid, s, e, wd: "/v.mp4"
 951 | +        VP.sheet = lambda v, s, e, wd: (self.sheet, "ab" * 32, [236.69, 253.26])
 952 | +
 953 | +    def tearDown(self):
 954 | +        VP.fetch, VP.sheet = self.saved
 955 | +        self.tmp.cleanup()
 956 | +
 957 | +    def test_xai_first_then_heimdall_and_the_prompt_carries_the_sheet(self):
 958 | +        x = VFake("xai_vision:grok-4.7", "xai_vision", fail="down")
 959 | +        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(STILL))
 960 | +        text_only = Fake("xai:grok", "xai", answer=json.dumps(CLEAN))     # no image input: never asked
 961 | +        r = router(self.tmp.name, [text_only, x, h], {"visual_check": ["xai:grok", "xai_vision:grok-4.7",
 962 | +                                                                       "heimdall:qwen"]})
 963 | +        cache = {}
 964 | +        rec = VP.visual_for(r, M, self.tmp.name, cache)
 965 | +        self.assertTrue(rec["measured"])
 966 | +        self.assertEqual((rec["backend"], text_only.calls, x.calls, h.calls), ("heimdall:qwen", 0, 1, 1))
 967 | +        self.assertEqual([f["kind"] for f in rec["flags"]], ["third_person", "on_screen_text"])
 968 | +        self.assertEqual(rec["sheet"]["sha256"], "ab" * 32)
 969 | +        again = VP.visual_for(r, M, self.tmp.name, cache)                   # paid once: the cache
 970 | +        self.assertTrue(again["cached"])
 971 | +        self.assertEqual((again["usd"], h.calls), (0.0, 1))
 972 | +
 973 | +    def test_out_of_contract_twice_is_not_measured(self):
 974 | +        h = VFake("heimdall:qwen", "heimdall", answer="a man is shown")
 975 | +        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
 976 | +        rec = VP.visual_for(r, M, self.tmp.name, {})
 977 | +        self.assertFalse(rec["measured"])
 978 | +        self.assertIn("two tries", rec["why"])
 979 | +        self.assertEqual(h.calls, 2)                                          # one retry, a new seed
 980 | +
 981 | +    def test_no_sheet_is_not_measured_and_nothing_is_asked(self):
 982 | +        VP.sheet = lambda *a: (_ for _ in ()).throw(OSError("ffmpeg"))
 983 | +        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
 984 | +        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
 985 | +        rec = VP.visual_for(r, M, self.tmp.name, {})
 986 | +        self.assertEqual((rec["measured"], h.calls), (False, 0))
 987 | +
 988 | +
 989 | +class TestVisionPrompt(unittest.TestCase):
 990 | +    def test_the_recording_holds_the_images_sha_never_the_image(self):
 991 | +        img = base64.b64encode(b"jpeg bytes").decode()
 992 | +        prompt = {"text": "look", "images": [img]}
 993 | +        self.assertTrue(P.is_vision(prompt))
 994 | +        self.assertFalse(P.is_vision("look"))
 995 | +        self.assertFalse(P.is_vision({"text": "look", "images": [""]}))
 996 | +        self.assertIn("[image sha256=", P.prompt_text(prompt))
 997 | +        self.assertNotIn(img, P.prompt_text(prompt))
 998 | +        with tempfile.TemporaryDirectory() as d:
 999 | +            h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
1000 | +            r = router(d, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]}, record_dir=os.path.join(d, "rec"))
1001 | +            r.call("visual_check", prompt, 100, 7)
1002 | +            recs = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(d, "rec")) for f in fs]
1003 | +            self.assertEqual(len(recs), 1)
1004 | +            with open(recs[0]) as f:
1005 | +                body = f.read()
1006 | +            self.assertNotIn(img, body)
1007 | +            self.assertIn("[image sha256=", body)
1008 | +            self.assertEqual(r.call("visual_check", prompt, 100, 7).cached, True)   # the same bytes: served
1009 | +
1010 | +    def test_the_upper_bound_counts_each_image(self):
1011 | +        b = Fake("x:y", "openai", price=(1e6, 0))                             # $1 per input token
1012 | +        one = b.upper_usd({"text": "t", "images": ["a"]}, 0)
1013 | +        self.assertEqual(one - b.upper_usd("t", 0), P.IMAGE_TOKENS_UPPER)
1014 | +
1015 | +    def test_the_heimdall_and_xai_vision_bodies(self):
1016 | +        sent = []
1017 | +        saved = P._http_json
1018 | +        P._http_json = lambda url, body, headers, timeout: (sent.append((url, body)) or
1019 | +                                                            {"choices": [{"message": {"content": "{}"}}],
1020 | +                                                             "output_text": "{}", "usage": {}})
1021 | +        try:
1022 | +            h = P.HeimdallBackend("heimdall:qwen", {"model": "qwen", "base_url": "https://h.example/api/v1"}, "/x")
1023 | +            h.key = lambda n: "k"
1024 | +            h.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
1025 | +            x = P.XAIVisionBackend("xai_vision:grok-4.7", {"model": "grok-4.7"}, "/x")
1026 | +            x.key = lambda n: "k"
1027 | +            x.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
1028 | +            with self.assertRaises(P.RequestRejected):
1029 | +                x.complete("text only", 100, 7)
1030 | +        finally:
1031 | +            P._http_json = saved
1032 | +        user = sent[0][1]["messages"][1]["content"]
1033 | +        self.assertEqual(user[1], {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}})
1034 | +        self.assertEqual(sent[1][0], "https://api.x.ai/v1/responses")
1035 | +        self.assertFalse(sent[1][1]["store"])
1036 | +        self.assertEqual(sent[1][1]["input"][1]["content"][1],
1037 | +                         {"type": "input_image", "image_url": "data:image/jpeg;base64,QUJD", "detail": "high"})
1038 | +
1039 | +
1040 | +if __name__ == "__main__":
1041 | +    unittest.main()
1042 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder that seals medley pins the render plays,
built from other channels' clips). Your role: a strict reviewer of a NEW gate that looks at source video and seals
its findings. Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- A build:
  - screens the pool;
  - rates hooks (ruling 59: only a hook rated >= 4 opens);
  - asks a writer for angles;
  - judges each line-up on the clips alone;
  - writes (takeaway / title / caption);
  - gates everything;
  - seals the pin.
- package_pin.seal is sha256 over the pin's body; a SEALED_LATER key enters it only when a segment carries it. The
  integrator's check_pin_only recomputes seals with this file and checks gate_problems() with the default
  REQUIRED_GATES.
- providers.Router routes each role's chain (failover), records every exchange, and runs the spend guard: each paid
  call reserves Backend.upper_usd first and settles after.
- The 13:38 pin's hook (Simply Bitcoin) opened on a split-screen photo of a real CEO while the host said "A CEO makes a
  personal mistake and shareholders pay". The words named nobody, so no text gate saw it; the picture named him.

The ruling this diff implements (ORCHESTRATOR 15:29 Nov 13, verbatim):
"(1) C: YES, build it (RULING 70). One contact sheet per clip, the three questions including lower_third; xAI first,
Heimdall image models as failover; fail closed. A finding on third_person or on_screen_text does not reject the clip
by itself: it is sealed as a FLAG that I and PBX see with the pin (text of the finding + the sheet), and a clip with a
third_person finding may not be the HOOK unless the claim in the words is confirmed as reported fact by step A's
context. lower_third feeds ruling 69 as one more piece of evidence, never alone. Report the measured cost on the first
build."
The three questions, from the proposal it rules on:
(1) third_person: is a person who is NOT speaking shown as a still, photo or graphic while the words make a negative
    claim (reporting on-screen NAME TEXT only, never naming from a face)?
(2) on_screen_text: the source's headline graphics or chyrons, and whether each asserts more than the words.
(3) lower_third: the speaker's on-screen name.

The change:
1. pipeline/visual_pin.py (new):
   - fetch(): the span at <= 480p (yt-dlp download sections, CPU).
   - sheet(): at most 8 stills (the cut-in, one every 2 s, the last; evenly spaced if more), each labelled with its
     source time, in ONE JPEG (ffmpeg + PIL, CPU).
   - visual_for(): ONE verdict (role visual_check). Checked in code (check(): exact keys, enums, types). Out of
     contract or unanswered: retried once with a new seed, then NOT measured. No sheet: not measured, nothing asked.
     Cached per moment + span + VERSION, measured live only.
   - flags(): a third_person finding (shown, as still/photo/graphic, with negative words), and every on_screen_text
     that asserts more than the words.
   - hook_block(): not measured, or a third_person flag, blocks the HOOK.
   - sealed(): the subset a pin seals (findings, flags, the sheet's name/sha256/times, backend; never a scratch path
     or a cost).
2. pipeline/providers.py: a VISION prompt {"text", "images": [base64 JPEG]}.
   - is_vision / prompt_text: the recordings and logs carry each image's sha256, never the image; the record KEY
     still covers the image bytes.
   - Backend.vision (False by default). The router skips a non-vision back-end for a vision prompt, and the vision
     back-end for a text prompt.
   - upper_usd adds IMAGE_TOKENS_UPPER (6000) per image.
   - XAIVisionBackend (vendor xai_vision): the Responses API with "input_image" parts, "detail": "high",
     "store": false (xAI's image-understanding guide uses grok-4.7 and warns a stored record can make image requests
     fail); it refuses a text prompt. Cost from cost_in_usd_ticks when the reply carries it.
   - HeimdallBackend sends a vision prompt as chat-completions content parts (text + image_url data URLs), the form
     the render's pipeline/visual_check.py uses with these models.
3. pipeline/model_providers.json:
   - backends xai_vision:grok-4.7 ([5, 25] per 1M, an upper bound) and heimdall:nvidia/nemotron-3.5-super-vl;
   - role visual_check = [xai_vision:grok-4.7, heimdall:qwen/qwen3.8-27b, heimdall:nvidia/nemotron-3.5-super-vl].
4. pipeline/package.py:
   - build(visual_cache=).
   - The hooks that would open (rated >= 4) are seen right after the hook ratings, BEFORE any angle call.
     hook_block -> m["visual_hook_block"] -> can_open() is False, so no angle is written for it. hook_pool records
     visual_blocked.
   - Every clip of a line-up that passes the clips-alone verdict is seen BEFORE any write. A clip not measured is
     dropped and the line-up re-lined, with no write.
   - The no-voice fallback sees its added clip too.
   - Segments carry visual_pin.sealed(); the inventory has a "visual" row: PASS only when every clip is measured,
     with all flags listed.
   - out["visual"] = {calls, cached, usd, unmeasured, flags}.
5. pipeline/package_pin.py: SEALED_LATER gains "visual"; to_pin carries it; MEDLEY_GATES gains "visual" (required for
   a new medley pin; check_pin_only uses REQUIRED_GATES, so earlier pins are untouched).
6. tests/package/proof_ledger.py: passes visual_cache, copies each sealed sheet beside the pin, and logs the measured
   cost.
7. Tests:
   - test_visual_pin (10): the stills; the contract; the flags; the hook block; the seal subset; xAI first, then
     Heimdall, the text-only back-end never asked, the cache; out-of-contract twice is unmeasured; no sheet asks
     nothing; the recording without the image; the image upper bound; the two request bodies.
   - test_medley +6 (TestRuling70Visual):
     - hooks seen before the angle, and a clean package sealing every sheet;
     - a clip flag sealed, not a reject;
     - a third-person hook blocked with no angle written;
     - a third-person clip (not the hook) kept with its flag;
     - an unmeasured clip dropped before any write;
     - an unmeasured hook blocked.
   - Old tests updated for the new required row. All 14 suites OK.

Stated readings (say so if you read the ruling differently):
- K1: "confirmed as reported fact by step A's context": step A passes only a clip whose view is "own_sincere" (the
  speaker's own assertion; context_integrity.a_failures). No step-A verdict classifies a claim as REPORTED fact, so
  today a third_person finding always blocks the HOOK (fail closed). Asking step A that question is a contract change
  for a later ruling.
- K2: "fail closed" = a clip whose visual check is not measured cannot be sealed: required row, dropped clip, blocked
  hook. A FLAG itself never rejects.
- K3: the sheet and the findings are sealed in the pin (the sheet by sha256; the file beside the pin), so the
  orchestrator and PBX see exactly what the model saw.
- K4: lower_third reaches ruling 69 through the segment's visual record (speakers.attribute_package reads
  visual.lower_third.name). Ruling 69's decide() lets it confirm or veto only.

Check in particular:
- that no path seals a clip without a measured visual check;
- that a third-person hook can never open;
- the router changes (could a text role ever reach a vision back-end, or an image reach a text one; the spend guard;
  the recording);
- the Responses / chat bodies;
- the seal compatibility for earlier pins;
- the cost accounting.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

