# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1351
# Branch: pp-selectid
# Generated: 2026-11-17 13:51 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1351/C1_STEP.diff (271 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 68e6942..7f0bbe1 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1569,6 +1569,64 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, ex
   6 |      return {"index": index, "record": rec}
   7 |  
   8 |  
   9 | +STAND_SOFT_PREFIX = "The clip ({channel}) may not stand alone: "   # RULING 141 (2): the integrator's render matches
  10 | +#   this prefix exactly (it then skips its own flag for that channel's clip)
  11 | +
  12 | +
  13 | +def stand_plain(m):
  14 | +    """RULING 141 (2): the render's STAND_ALONE opener refusal of moment m as a CLIP, in plain words (the clip scorer's
  15 | +    reason), e.g. "it opens on 'but' and the clip scorer has no verdict for it"; None when the clip role passes."""
  16 | +    import stand_alone as SA
  17 | +    v = verdict_of(m)
  18 | +    ok, why = SA.opener("clip", m.get("text") or "", v["score"] if v else None, v["fault"] if v else None,
  19 | +                        moments=True)
  20 | +    if ok:
  21 | +        return None
  22 | +    x = re.match(r"clip opens on (.+?) and no clip-scorer verdict is available", why)
  23 | +    if x:
  24 | +        return f"it opens on {x.group(1)} and the clip scorer has no verdict for it"
  25 | +    x = re.match(r"clip opens on (.+?); the clip scorer does not affirm it stands alone \(([^,]+), fault (.+)\)$", why)
  26 | +    if x:
  27 | +        f = x.group(3).replace("_", " ")
  28 | +        return f"it opens on {x.group(1)} and the clip scorer rated it {x.group(2)} of 5" + \
  29 | +            (f" ({f})" if f not in ("None", "none", "") else "")
  30 | +    return why
  31 | +
  32 | +
  33 | +def stand_soft_rows(stand, segs):
  34 | +    """RULING 141 (2) (STAND_ALONE soft in the never-empty pass): {label: plain reason} for the CLIP rows of a check_edl
  35 | +    result `stand` (stand_alone_check(segs)) that fail ONLY its opener rule, each on a moment that pass brought back
  36 | +    (its "stand_soft" mark); None when the check passes or any other failure stands: the hook's row, any topic row
  37 | +    (ruling 34), the medley not naming Bitcoin, a failing row of an unmarked clip (these stay HARD)."""
  38 | +    if not isinstance(stand, dict) or stand.get("ok") is True or \
  39 | +            (stand.get("medley_names_bitcoin") or {}).get("pass") is not True:
  40 | +        return None
  41 | +    by, out = dict(zip(labels(len(segs)), segs)), {}
  42 | +    for r in stand.get("rows") or []:
  43 | +        if r.get("pass") is True:
  44 | +            continue
  45 | +        m = by.get(r.get("segment"))
  46 | +        if r.get("segment") == "hook" or m is None or not m.get("stand_soft") or \
  47 | +                (r.get("topic") or {}).get("pass") is not True or (r.get("opener") or {}).get("pass") is not False:
  48 | +            return None
  49 | +        out[r["segment"]] = m["stand_soft"]
  50 | +    return out or None
  51 | +
  52 | +
  53 | +def stand_ok(segs):
  54 | +    """The render's STAND_ALONE on a line-up for the line-up rules (lineup_ok, lineup_for): it passes, or RULING 141 (2),
  55 | +    its only failures are clips the never-empty pass brought back failing only the opener rule (stand_soft_rows)."""
  56 | +    st = stand_alone_check(segs)
  57 | +    return st["ok"] is True or bool(stand_soft_rows(st, segs))
  58 | +
  59 | +
  60 | +def stand_with_soft(segs):
  61 | +    """The pin stage's STAND_ALONE (stand_alone_check) with RULING 141 (2)'s soft rows when there are any."""
  62 | +    st = stand_alone_check(segs)
  63 | +    sr = stand_soft_rows(st, segs)
  64 | +    return dict(st, soft_rows=sr) if sr else st
  65 | +
  66 | +
  67 |  def no_topic(m):
  68 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  69 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  70 | @@ -1800,7 +1858,7 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  71 |      dur = sum(m["duration_s"] for m in segs)
  72 |      if not lo <= dur <= hi:
  73 |          return False, f"{dur:.1f} s outside {lo}-{hi} s"
  74 | -    if not stand_alone_check(segs)["ok"]:
  75 | +    if not stand_ok(segs):                                   # RULING 141 (2): only marked clips' openers flag
  76 |          return False, "the render's STAND_ALONE"
  77 |      return True, "ok"
  78 |  
  79 | @@ -1937,7 +1995,7 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  80 |                      continue
  81 |                  if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  82 |                      continue
  83 | -                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  84 | +                if need_stand_alone and not stand_ok([h] + order):     # RULING 141 (2): marked clips flag
  85 |                      continue
  86 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  87 |                  if now is not None:                       # ruling 57: a fresh clip first, then the newest clips,
  88 | @@ -3198,6 +3256,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  89 |      scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name,   # ruling 56
  90 |                           extra=scorer_extra)                                                       # ruling 90
  91 |      ms = [with_verdict(m, scorer["index"]) for m in ms]
  92 | +    for m in ms:                                       # RULING 141 (2)'s soft mark is this pass's own, never carried in
  93 | +        m.pop("stand_soft", None)
  94 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  95 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  96 |      admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
  97 | @@ -3206,6 +3266,16 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  98 |               for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
  99 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
 100 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
 101 | +    stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trims
 102 | +                  and no_topic(m) is None for p in [stand_plain(m)] if p}   # RULING 141 (2): STAND_ALONE SOFT in the
 103 | +    for m in ms:                                                            # never-empty pass: a moment left out ONLY
 104 | +        if m["moment_id"] in stand_back:                                    # by the opener rule (no topic refusal, no
 105 | +            m["stand_soft"] = stand_back[m["moment_id"]]                    # affirmed trim) comes back as a clip,
 106 | +    if stand_back:                                                          # flagged; it never opens (the hook rule)
 107 | +        log(f"  RULING 141 NEVER EMPTY (STAND_ALONE soft): {len(stand_back)} moment(s) left out only by the render's "
 108 | +            f"STAND_ALONE opener rule come back as clips, flagged: " +
 109 | +            ", ".join(f"{mid[:8]} ({p})" for mid, p in stand_back.items()))
 110 | +    no_role = {k: v for k, v in no_role.items() if k not in stand_back}
 111 |      ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42);
 112 |      #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
 113 |      #   video at most once, L-y 4)
 114 | @@ -3248,6 +3318,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 115 |      cleared, back = cleared_pool(ms, a_by, fails, soft)  # RULING 137 stage 1: the never-empty pass adds back, flagged
 116 |      levels = current_levels(sources.values(), ctx)
 117 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 118 | +           **({"soft_stand": stand_back} if stand_back else {}),          # RULING 141 (2): back, flagged
 119 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 120 |             "reposted": reposted,
 121 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 122 | @@ -3717,7 +3788,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 123 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 124 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 125 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 126 | -                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 127 | +                                stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 128 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 129 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 130 |                                  who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 131 | @@ -4206,7 +4277,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 132 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 133 |                                              style=HS.lint_lines(pk["lines"]),
 134 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 135 | -                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 136 | +                                            stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 137 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 138 |                                              value=val,                       # ruling 91: the takeaway earned its place
 139 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 140 | @@ -4327,7 +4398,7 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 141 |      soft = _build(*args, soft=True, **kw)
 142 |      info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 143 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 144 | -            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
 145 | +            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}}   # its record
 146 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 147 |  
 148 |  
 149 | @@ -4438,7 +4509,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 150 |                                      "affirming one a conjunction, reply-fragment or trimmed opener fails closed)"),
 151 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 152 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 153 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 154 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 155 | +                                **({"status": "FLAGGED", "flags": [           # RULING 141 (2): one plain sentence a clip
 156 | +                                    STAND_SOFT_PREFIX.format(channel=(who or {}).get(lb) or "its channel") + f"{why}."
 157 | +                                    for lb, why in stand["soft_rows"].items()]} if soft and stand.get("soft_rows") else {}))}
 158 |             if stand is not None else {}),
 159 |          **({"visual": dict(row(bool(visual) and all((v or {}).get("measured") is True for v in visual),
 160 |                                 sorted({str((v or {}).get("backend")) for v in visual}) or None,
 161 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 162 | index 1fb3855..727abc7 100644
 163 | --- a/pipeline/package_pin.py
 164 | +++ b/pipeline/package_pin.py
 165 | @@ -37,8 +37,10 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 166 |  SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 167 |                          "cuttable",                        # stage 2a: a sentence edge at a word boundary (L-v 2's
 168 |                          #   word check, "second_pass", stays HARD)
 169 | -                        "medley"})                         # stage 2b: the hook under the calibrated bar (its own
 170 | -#   rater's rating; no calibration or another rater stays HARD)
 171 | +                        "medley",                          # stage 2b: the hook under the calibrated bar (its own
 172 | +                        #   rater's rating; no calibration or another rater stays HARD)
 173 | +                        "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 174 | +#   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 175 |  REVIEW_FLAGS_MAX = 3
 176 |  
 177 |  
 178 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 179 | index f61260a..fe400ca 100644
 180 | --- a/tests/package/test_ruling_137.py
 181 | +++ b/tests/package/test_ruling_137.py
 182 | @@ -290,6 +290,88 @@ class TestStage2bHookBar(unittest.TestCase):
 183 |          self.assertEqual(PK.HOOK_SOFT_MAX, 2)
 184 |  
 185 |  
 186 | +class TestRuling141StandAloneSoft(unittest.TestCase):
 187 | +    """RULING 141 (2): STAND_ALONE SOFT in the never-empty pass (the builder's half; the integrator's render already only
 188 | +    flags an opener refusal and holds on the topic rule and the medley naming Bitcoin). A moment left out ONLY by the
 189 | +    render's STAND_ALONE opener rule comes back as a clip, flagged "The clip (<channel>) may not stand alone: <reason>."
 190 | +    (the integrator matches that prefix); it never opens; the topic rule, the hook's row, an unmarked clip and the medley
 191 | +    naming Bitcoin stay hard."""
 192 | +
 193 | +    def m(self, text, verdict=None):
 194 | +        x = {"moment_id": "q", "text": text}
 195 | +        return dict(x, scorer_verdict=dict(verdict, text_sha256=PK.text_sha(text))) if verdict else x
 196 | +
 197 | +    def test_the_reason_in_plain_words(self):
 198 | +        self.assertEqual(PK.stand_plain(self.m("But Bitcoin q x.")),
 199 | +                         "it opens on 'but' and the clip scorer has no verdict for it")
 200 | +        self.assertEqual(PK.stand_plain(self.m("And Bitcoin q x.", {"score": 2.0, "fault": "starts_mid_thought",
 201 | +                                                                     "reason": "r"})),
 202 | +                         "it opens on 'and' and the clip scorer rated it 2.0 of 5 (starts mid thought)")
 203 | +        self.assertIsNone(PK.stand_plain(self.m("Bitcoin q x.")))
 204 | +        self.assertTrue(PK.STAND_SOFT_PREFIX.format(channel="X").startswith("The clip (X) may not stand alone: "))
 205 | +
 206 | +    def test_only_marked_clips_failing_only_the_opener_are_soft(self):
 207 | +        segs = [{"moment_id": "h", "stand_soft": "why h"}, {"moment_id": "a", "stand_soft": "why a"},
 208 | +                {"moment_id": "b"}]                                     # a mark on the hook never softens its row
 209 | +        row = lambda seg, o, t=True: {"segment": seg, "pass": o and t, "opener": {"pass": o}, "topic": {"pass": t}}
 210 | +        st = {"ok": False, "rows": [row("hook", True), row("clip_01", False), row("clip_02", True)],
 211 | +              "medley_names_bitcoin": {"pass": True}}
 212 | +        self.assertEqual(PK.stand_soft_rows(st, segs), {"clip_01": "why a"})
 213 | +        for bad in ([row("hook", False), row("clip_01", False), row("clip_02", True)],      # the hook's own row
 214 | +                    [row("hook", True), row("clip_01", False, False), row("clip_02", True)],   # its topic too
 215 | +                    [row("hook", True), row("clip_01", False), row("clip_02", False)]):     # an unmarked clip
 216 | +            self.assertIsNone(PK.stand_soft_rows(dict(st, rows=bad), segs), bad)
 217 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin={"pass": False}), segs))
 218 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin=None), segs))   # unmeasured: hard
 219 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, ok=True), segs))
 220 | +
 221 | +    def rig(self, never_empty, carry=False):
 222 | +        import test_medley as TM
 223 | +        from test_moments import pm
 224 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), dict(pm("z", "C", 13.0), text="But Bitcoin z x."),
 225 | +              dict(pm("w", "D", 13.0), text="But nothing here at all.")]   # w: the topic rule (ruling 34) too
 226 | +        ms = [dict(m, stand_soft="carried in") for m in ms] if carry else ms
 227 | +        r = TM.Rig(ms, ["h", "x", "z"], [(True, [], None, TM.Rig.LINE)], [None])
 228 | +        r.build_kw = {"never_empty": never_empty}
 229 | +        return r.run()
 230 | +
 231 | +    def test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass(self):
 232 | +        clean = self.rig(False)
 233 | +        self.assertIsNone(clean["package"])
 234 | +        self.assertIn("z", clean["no_role"])                        # the clean pass: 2 channels, no paid verdict
 235 | +        out = self.rig(True)
 236 | +        pk = out["package"]
 237 | +        segs = {s["moment_id"]: s for s in pk["segments"]}
 238 | +        self.assertEqual((set(segs), pk["segments"][0]["moment_id"]), ({"h", "x", "z"}, "h"))   # never the hook
 239 | +        want = [f"The clip ({segs['z']['channel']}) may not stand alone: it opens on 'but' and the clip scorer has no "
 240 | +                f"verdict for it."]
 241 | +        self.assertEqual((pk["gates"]["stand_alone"]["status"], pk["gates"]["stand_alone"]["flags"]), ("FLAGGED", want))
 242 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
 243 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
 244 | +        self.assertEqual(out["soft_stand"], {"z": "it opens on 'but' and the clip scorer has no verdict for it"})
 245 | +        self.assertIn("w", out["no_role"])                              # the topic rule stays HARD: never back
 246 | +
 247 | +    def test_a_mark_carried_in_is_never_read(self):
 248 | +        self.assertIsNone(self.rig(False, carry=True)["package"])
 249 | +
 250 | +    def test_the_line_up_rules_take_a_marked_clip_and_refuse_an_unmarked_one(self):
 251 | +        from test_moments import pm
 252 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
 253 | +        z = dict(pm("z", "C", 13.0), text="But Bitcoin z x.")
 254 | +        segs = [h, pm("x", "B", 14.0), z]
 255 | +        self.assertEqual(PK.lineup_ok(segs), (False, "the render's STAND_ALONE"))
 256 | +        self.assertEqual(PK.lineup_ok([h, segs[1], dict(z, stand_soft="it opens on 'but'")]), (True, "ok"))
 257 | +
 258 | +    def test_the_row_flags_only_in_the_soft_pass(self):
 259 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 260 | +        st = {"ok": False, "rows": [], "medley_names_bitcoin": {"pass": True}, "soft_rows": {"clip_02": "why z"}}
 261 | +        row = lambda soft: PK.inventory(**TestStage2a().base(t), stand=st, soft=soft, who={"clip_02": "Yahoo Finance"})[
 262 | +            "stand_alone"]
 263 | +        self.assertEqual((row(True)["status"], row(True)["flags"]), (
 264 | +            "FLAGGED", ["The clip (Yahoo Finance) may not stand alone: why z."]))
 265 | +        self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))
 266 | +
 267 | +
 268 |  class TestTheDayCount(unittest.TestCase):
 269 |      def test_counted_per_day_ledger(self):
 270 |          with tempfile.TemporaryDirectory() as d:
 271 | 
```

---

pp-selectid: RULING 141 (2) (orchestrator 13:40 ET Nov 17): STAND_ALONE becomes SOFT, the first item of stage 2b; the
builder's half. Context: the never-empty pass (package.build runs _build(soft=True) only when the clean pass sealed
nothing) flags soft gates in one plain sentence each; at most 3 flags seal (package_pin.REVIEW_FLAGS_MAX). STAND_ALONE
left out 77 of 110 usable moments today. The integrator's side needs no change: since its batch 105 (11:51 ET) its
render's validate re-asks every opener and only FLAGS an unaffirmed / unrated / conjunction opener; it HOLDS only on the
topic rule (ruling 34), the medley naming Bitcoin, and a malformed ruling-119 floor mark. Its next batch skips its own
flag for a channel whose pin already carries "The clip (<channel>) may not stand alone:", so that prefix must be exact.
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE (never-empty pass only; the clean pass is unchanged):
(a) _build: no_role (package.py:3261: no_role_on_screen :1640, the opener rule; no_topic :1630, the topic rule) still
    leaves out what it did. In the soft pass, a moment left out ONLY by the opener rule (no_topic None) and with no
    affirmed trim variant (trims, :3264, the clean path, kept first) comes back (stand_back, :3269), carrying its plain
    reason as the mark "stand_soft" (stand_plain :1576: "it opens on 'but' and the clip scorer has no verdict for it" /
    "... rated it 2.0 of 5 (starts mid thought)"). The mark is popped after with_verdict, so it never carries in. It
    never opens: the hook role still needs SA.opener("hook") in _can_open (:1809), which every conjunction fails.
(b) stand_soft_rows(stand, segs) (:1596): the clip rows of check_edl (stand_alone.py:176-222: one row a segment, the
    opener and topic results, plus medley_names_bitcoin) that fail ONLY the opener, each on a marked moment. None if
    the check passes, the hook's row fails (even marked), any topic row fails, an unmarked clip's row fails, or the
    medley does not name Bitcoin (also when that record is missing).
(c) stand_ok(segs) (:1616) = the check passes, or only (b)'s rows fail. It replaces the bare check in lineup_ok (:1861)
    and in lineup_for's picker (:1998). stand_with_soft (:1623) adds the soft rows to the pin stage's check at both
    inventory call sites.
(d) inventory: the "stand_alone" row is FLAGGED with "The clip (<channel>) may not stand alone: <reason>." for each soft
    row (STAND_SOFT_PREFIX :1572, the integrator's exact prefix), only when soft. package_pin.SOFT_GATES adds
    "stand_alone". The record keeps out["soft_stand"].

TESTS (test_ruling_137, 7 new): the plain reason; (b)'s every hard case; END TO END through test_medley's Rig: a 3-moment
pool whose third channel opens on "But": the clean pass leaves it out and stops at 2 channels; the never-empty pass seals
with the stand_alone row FLAGGED in the exact sentence, review_flags_of equal to it, gate_problems() empty, the hook not
the flagged clip; a moment failing the topic rule too stays out. lineup_ok takes a marked clip and refuses an unmarked
one. The row flags only in the soft pass. Mutations: 11 of 14 killed. Survivors: S13 (the pop of a carried mark) and
S14 (the explicit opener check) are equivalent today; S3, preferring an affirmed trim, is NOT UNIT-TESTED: please read
:3269's "not in trims".

PLEASE CHECK: (1) can anything the topic rule, the medley-names-Bitcoin rule or the hook rule refuses get through? (2) the
clean pass unchanged; (3) lineup_ok / lineup_for / the pin row agree; (4) the exact prefix; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
