# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_1435
# Branch: pp-selectid
# Generated: 2026-11-17 14:35 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_1435/C1_STEP.diff (462 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index dd41fd9..5bd269c 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2217,6 +2217,102 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
   6 |                      cached=bool(getattr(r, "cached", False)))
   7 |  
   8 |  
   9 | +def chain_cap():
  10 | +    """RULING 136 (2) / 141 (1): the most flags a package may carry (package_pin.REVIEW_FLAGS_MAX: one source)."""
  11 | +    import package_pin
  12 | +    return package_pin.REVIEW_FLAGS_MAX
  13 | +
  14 | +
  15 | +def seg_marks(segs):
  16 | +    """RULING 141 (3): the flags a line-up's clips already carry from the never-empty pass's per-clip gates, one sentence
  17 | +    each as the inventory writes them: step A's soft codes (context_a), a sentence edge (cuttable), STAND_ALONE
  18 | +    (stand_alone), the hook under the calibrated bar (the medley row's hook sentence)."""
  19 | +    n = sum(len(set(m.get("step_a_flags") or [])) + len(m.get("edge_flags") or []) + bool(m.get("stand_soft"))
  20 | +            for m in segs or [])
  21 | +    return n + bool((hook_own(segs[0]) or {}).get("flagged")) if segs else n
  22 | +
  23 | +
  24 | +def lineup_soft(segs, med):
  25 | +    """RULING 141 (3), THE LINE-UP CHAIN (phase A) in the never-empty pass: a clips-alone verdict whose ONLY failures are
  26 | +    soft -> {"weak": {label: rating}, "floor", "soft_joins": [join], "n": the flags it adds}, else None. Soft: a clip
  27 | +    rated under the verdict's floor (ruling 116); a flagged join past the one bridge L-y 2 allows (the first bridgeable
  28 | +    flagged join keeps its bridge); the question hook's first join (ruling 37: no bridge goes there). Hard (None): not
  29 | +    measured, no stated through-line, the hook not passing its own bar (the soft hook bar included), a clip with no
  30 | +    rating, or nothing to flag."""
  31 | +    if not segs or not isinstance(med, dict) or med.get("measured") is not True or \
  32 | +            not _line_ok(med.get("through_line")) or not (hook_own(segs[0]) or {}).get("passes"):
  33 | +        return None
  34 | +    labs, cl = labels(len(segs)), med.get("clips") or {}
  35 | +    if any(type(cl.get(lb)) is not int for lb in labs[1:]):
  36 | +        return None
  37 | +    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
  38 | +    js = joins(labs)
  39 | +    flagged = [j for j in js if j in (med.get("flagged") or [])]
  40 | +    bridge = next((j for j in flagged if not (question_hook(segs) and j == js[0])), None)
  41 | +    soft_joins = [j for j in flagged if j != bridge]
  42 | +    weak = {lb: cl[lb] for lb in labs[1:] if cl[lb] < floor}
  43 | +    if not weak and not soft_joins:
  44 | +        return None
  45 | +    return {"weak": weak, "floor": floor, "soft_joins": soft_joins, "n": len(weak) + len(soft_joins)}
  46 | +
  47 | +
  48 | +def soft_joins_of(med):
  49 | +    """RULING 141 (3): the joins an ACCEPTED kept candidate carries unbridged, flagged (none on any other verdict)."""
  50 | +    return list(((med or {}).get("soft") or {}).get("soft_joins") or [])
  51 | +
  52 | +
  53 | +def coherence_soft(coh, segs, done=()):
  54 | +    """RULING 141 (3), phase A, for the kept candidate retried accepting: a coherence verdict whose ONLY failure is clip
  55 | +    ratings under its own floor -> {"weak": {label: rating}, "floor", "n": the NEW flags (a clip in `done`, already
  56 | +    flagged by the clips-alone verdict, is one doubt, flagged once)}, else None: not measured, the hook not passing
  57 | +    its own bar, no stated through-line or the VO point under its floor (for the free panel: not a majority of its
  58 | +    answers with both), a rating missing, or no weak clip."""
  59 | +    if not segs or not isinstance(coh, dict) or coh.get("measured") is not True or \
  60 | +            not (coh.get("hook_own") or {}).get("passes"):
  61 | +        return None
  62 | +    labs, cl = labels(len(segs)), coh.get("clips") or {}
  63 | +    fl = coh.get("floors") or STANDARD_LINEUP["coherence"]
  64 | +    if any(type(cl.get(lb)) is not int for lb in labs[1:]) or type(coh.get("vo_point")) is not int:
  65 | +        return None
  66 | +    rest = lambda a: _line_ok(a.get("through_line")) and type(a.get("vo_point")) is int and \
  67 | +        a["vo_point"] >= fl["vo_point"]
  68 | +    ans = (coh.get("panel") or {}).get("answers")
  69 | +    if not (sum(bool(rest(a)) for a in ans) * 2 > len(ans) if ans else rest(coh)):
  70 | +        return None
  71 | +    weak = {lb: cl[lb] for lb in labs[1:] if cl[lb] < fl["clip"]}
  72 | +    return {"weak": weak, "floor": fl["clip"], "n": sum(lb not in done for lb in weak)} if weak else None
  73 | +
  74 | +
  75 | +def chain_sentences(soft, who):
  76 | +    """RULING 141 (3) / 138 (3): lineup_soft's flags in plain words, each naming its clip (clip ratings, then joins)."""
  77 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  78 | +    return [f"{CLIP_PLACE.get(lb, 'A clip')} ({ch(lb)}): the checker rated how much it adds to the line-up's point "
  79 | +            f"{x} of 5, needs {soft['floor']}." for lb, x in (soft.get("weak") or {}).items()] + \
  80 | +        join_sentences(soft.get("soft_joins"), who)
  81 | +
  82 | +
  83 | +def join_sentences(js, who):
  84 | +    """RULING 141 (3): one plain sentence per unbridged flagged join."""
  85 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  86 | +    return [f"Between {CLIP_PLACE.get(a, 'A clip').lower()} ({ch(a)}) and {CLIP_PLACE.get(b, 'A clip').lower()} "
  87 | +            f"({ch(b)}): the checker could not follow the jump." for a, b in (j.split(" -> ") for j in js or [])]
  88 | +
  89 | +
  90 | +def coherence_sentences(cs, chain, who):
  91 | +    """RULING 141 (3): the coherence acceptance's flags; a clip the clips-alone verdict already flagged keeps that one
  92 | +    sentence (one doubt, flagged once: review_flags_of gives each sentence once)."""
  93 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  94 | +    first = dict(zip((chain or {}).get("weak") or {}, chain_sentences(dict(chain, soft_joins=[]), who))) if chain \
  95 | +        else {}
  96 | +    return [first.get(lb) or f"{CLIP_PLACE.get(lb, 'A clip')} ({ch(lb)}): with the narration, the checker rated how "
  97 | +            f"much it supports the point {x} of 5, needs {cs['floor']}." for lb, x in (cs.get("weak") or {}).items()]
  98 | +
  99 | +
 100 | +def best_kept(kept):
 101 | +    """RULING 141 (3): the kept candidate to retry: the fewest flags, then the highest lowest clip rating."""
 102 | +    return min(kept, key=lambda c: (c["n"], -c["low"]))
 103 | +
 104 | +
 105 |  def last_clip_only(segs, med):
 106 |      """RULING 62 (12:00): whether a clips-alone failure is its LAST clip's alone: measured, the through-line stated,
 107 |      the hook passing its calibrated bar (ruling 115: hook_own of the line-up's own hook, as medley() judges it), every
 108 | @@ -2908,10 +3004,10 @@ def ly_shape(pk):
 109 |      med = pk.get("medley") or {}
 110 |      if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 111 |          fails.append("the clips-alone verdict was not measured (L-y 3)")
 112 | -    elif question_hook(segs) and js and js[0] in med["flagged"]:
 113 | +    elif question_hook(segs) and js and js[0] in med["flagged"] and js[0] not in soft_joins_of(med):
 114 |          fails.append(f"ruling 37: a hook ending on a question takes no bridge after it, so {js[0]} must be followable "
 115 |                       f"(the render's R1 reads the sealed clips-alone verdict)")
 116 | -    elif sorted(bridged) != sorted(med["flagged"]):
 117 | +    elif sorted(bridged) != sorted(j for j in med["flagged"] if j not in soft_joins_of(med)):   # 141 (3)
 118 |          fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 119 |                       f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 120 |      rec = pk.get("bridge") or {}
 121 | @@ -3826,6 +3922,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 122 |      with ThreadPoolExecutor(max_workers=8) as pool:
 123 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 124 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 125 | +            kept, retried, accept_key, accept_soft = [], False, None, None   # RULING 141 (3): the never-empty pass's
 126 | +            #   kept candidates (soft failures only), and the one retried accepting
 127 |              sel = story_pool(angle, cleared, by_story)    # RULING 118 (4): a story's angle chooses inside its story
 128 |              #   (its join table, the fill, every swap; lineup_for and the search choose only among the angle's own and
 129 |              #   its join table's moments, so the story holds there by construction)
 130 | @@ -3844,12 +3942,15 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 131 |                      + (f"; NOT ASKED: {jt_err}" if jt_err else "") + f" ({time.time() - t0:.0f} s)")
 132 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 133 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 134 | -            while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 135 | -                    not out.get("lock_stop"):
 136 | +            while (total < lineups or (soft and kept and not retried)) and not out["packages"] and \
 137 | +                    not out.get("budget_stop") and not out.get("lock_stop"):
 138 |                  if candidate is not None and n_lineup >= candidate["n_lineup"]:
 139 |                      break                                 # RULING 66: the candidate alone, never re-lined or swapped
 140 |                  if over_budget(ai):
 141 |                      break
 142 | +                if total >= lineups:                      # RULING 141 (3): the judged-line-up budget ran out: only the
 143 | +                    k_ = best_kept(kept)                  # kept candidate's one retry reaches here (the condition above)
 144 | +                    swapped, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
 145 |                  if swapped is not None:                   # ruling 41: the swapped line-up is judged next
 146 |                      segs, swapped = swapped, None
 147 |                      exception = supply_exception(segs, ctx)
 148 | @@ -3876,6 +3977,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 149 |                                                   hook_only=True)   # FIRST: the
 150 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
 151 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 152 | +                if segs is None and soft and kept and not retried:   # RULING 141 (3): the search ran out: the best
 153 | +                    k_ = best_kept(kept)                                # kept candidate, retried once, accepting
 154 | +                    segs, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
 155 | +                    exception = supply_exception(segs, ctx)
 156 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 157 |                         "supply_exception": exception, "attempts": [],
 158 |                         **({"pool_filled": filled} if filled else {}),
 159 | @@ -3908,6 +4013,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 160 |                                         writer_family=writers_f)
 161 |                      judged[key] = (ok_m, med)
 162 |                      total += 0 if med.get("replayed") or med.get("cached") else 1   # 12:00: JUDGED line-ups
 163 | +                if key == accept_key:                       # RULING 141 (3): the kept candidate retried ACCEPTING:
 164 | +                    ok_m, med = True, dict(med, soft=accept_soft)   # its cached verdict's soft failures are its flags
 165 | +                    rec["accepted_soft"] = accept_soft
 166 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 167 |                  if jt and med.get("measured"):            # RULING 117 (3): the table's joins against the verdict's
 168 |                      ids_ = [m["moment_id"] for m in segs]
 169 | @@ -3932,6 +4040,13 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 170 |                  if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
 171 |                      rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
 172 |                      break
 173 | +                if soft and candidate is None and key != accept_key and med.get("measured") and \
 174 | +                        (not ok_m or (question_hook(segs) and joins(labs)[0] in (med.get("flagged") or []))):
 175 | +                    ks = lineup_soft(segs, med)             # RULING 141 (3): soft failures only: KEPT (the search goes
 176 | +                    if ks is not None and seg_marks(segs) + ks["n"] <= chain_cap():   # on, a clean line-up first)
 177 | +                        kept.append({"segs": list(segs), "key": key, "soft": ks, "n": seg_marks(segs) + ks["n"],
 178 | +                                     "low": min(med["clips"][lb] for lb in labs[1:])})
 179 | +                        rec["kept"] = ks
 180 |                  if not ok_m and jt and med.get("measured"):   # RULING 117: the search over the table picks the next
 181 |                      floor_ = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
 182 |                      for lb_, mm in zip(labs[1:], segs[1:]):
 183 | @@ -3989,15 +4104,17 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 184 |                                    f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 185 |                                    f"line-up rules: re-lined")
 186 |                      continue
 187 | -                if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
 188 | +                if question_hook(segs) and joins(labs)[0] in med["flagged"] and \
 189 | +                        joins(labs)[0] not in soft_joins_of(med):   # ruling 37: no bridge after a question (141: flagged)
 190 |                      dropped.add(segs[1]["moment_id"])
 191 |                      rec["why"] = (f"ruling 37: the join after the question hook must be followable without a bridge, and "
 192 |                                    f"the clips alone flag {joins(labs)[0]}: re-lined")
 193 |                      continue
 194 |                  join = None
 195 | -                if med["flagged"]:
 196 | -                    k = joins(labs).index(med["flagged"][0])
 197 | -                    join = (k, med["joins"][med["flagged"][0]]["why"])
 198 | +                bj = next((j for j in med["flagged"] if j not in soft_joins_of(med)), None)   # 141 (3): soft ones flag
 199 | +                if bj is not None:
 200 | +                    k = joins(labs).index(bj)
 201 | +                    join = (k, med["joins"][bj]["why"])
 202 |                  extra, relined, w_used, written = "", False, 0, ()
 203 |                  pre, no_verdict = None, False
 204 |                  if lock_check is not None:                  # RULINGS 68 / 72: the render's own lock, before any write;
 205 | @@ -4134,12 +4251,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 206 |                              break
 207 |                      if join is not None and fields["bridge"] is None:
 208 |                          dropped.add(segs[join[0] + 1]["moment_id"])
 209 | -                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 210 | +                        rec["why"] = (f"the clips-alone verdict flagged {bj}; the writer judged it "
 211 |                                        f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 212 |                          relined = True
 213 |                          break
 214 |                      if fields["bridge"] is not None:
 215 | -                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 216 | +                        fields["bridge_confirmed_by"] = {"join": bj, "why": join[1],
 217 |                                                           "backend": med.get("backend")}
 218 |                      fields["supply_exception"] = exception
 219 |                      pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 220 | @@ -4269,6 +4386,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 221 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 222 |                      ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f,
 223 |                                            hook=segs[0])     # then on the takeaway; ruling 61: the hook's cached
 224 | +                    cs_ = coherence_soft(coh, segs, (accept_soft or {}).get("weak") or ()) \
 225 | +                        if not ok_c and key == accept_key else None   # RULING 141 (3): the accepted candidate only
 226 | +                    if cs_ is not None and seg_marks(segs) + accept_soft["n"] + cs_["n"] <= chain_cap():
 227 | +                        ok_c, coh = True, dict(coh, soft=cs_)     # its clip ratings under coherence's floor: flagged
 228 |                      att["coherence"] = coh
 229 |                      log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 230 |                          f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 231 | @@ -4437,6 +4558,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 232 |      det = fid["deterministic"]
 233 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 234 |      hook_fl = ((medley[1].get("hook_own") or {}).get("flagged") if soft and medley is not None else None)   # 2b
 235 | +    chain = medley[1].get("soft") if soft and medley is not None and medley[0] else None   # RULING 141 (3)
 236 | +    med_fl = ([f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated it under the "
 237 | +               f"hook bar ({hook_fl})."] if hook_fl and medley is not None and medley[0] else []) + \
 238 | +        (chain_sentences(chain, who) if chain else [])
 239 | +    coh_fl = coherence_sentences(coh["soft"], chain, who) if soft and coh_ok and (coh or {}).get("soft") else []
 240 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
 241 |      edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
 242 |                 if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
 243 | @@ -4488,14 +4614,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 244 |                              if edge_fl and truth and all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t)
 245 |                                                           for t in truth.values()) else {})),
 246 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 247 | -                          **votes_of(coh)),
 248 | +                          **votes_of(coh), **({"status": "FLAGGED", "flags": coh_fl} if coh_fl else {})),   # 141 (3)
 249 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 250 |                                 measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"),
 251 | -                           **({"status": "FLAGGED", "flags": [            # RULING 137 stage 2b: the hook under the bar
 252 | -                               f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated "
 253 | -                               f"it under the hook bar ({hook_fl})."]} if hook_fl and medley[0] else {}))}
 254 | +                           **({"status": "FLAGGED", "flags": med_fl} if med_fl else {}))}   # 2b hook bar; 141 (3)
 255 |             if medley is not None else {}),
 256 | -        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 257 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]),
 258 | +                             **({"status": "FLAGGED", "flags": join_sentences(chain["soft_joins"], who)}   # 141 (3)
 259 | +                                if chain and chain["soft_joins"] and shape[0] else {}))}
 260 |             if shape is not None else {}),
 261 |          **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 262 |                                  why=[f"{v['slot']}: {v['detail']}" for v in style])}
 263 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 264 | index 727abc7..e2403da 100644
 265 | --- a/pipeline/package_pin.py
 266 | +++ b/pipeline/package_pin.py
 267 | @@ -39,6 +39,9 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 268 |                          #   word check, "second_pass", stays HARD)
 269 |                          "medley",                          # stage 2b: the hook under the calibrated bar (its own
 270 |                          #   rater's rating; no calibration or another rater stays HARD)
 271 | +                        "coherence", "ly_shape",           # RULING 141 (3), the line-up chain phase A: clip
 272 | +                        #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
 273 | +                        #   stay HARD; the takeaway's value rows are not soft)
 274 |                          "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 275 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 276 |  REVIEW_FLAGS_MAX = 3
 277 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 278 | index 6ef4cf8..b0e276d 100644
 279 | --- a/tests/package/test_ruling_137.py
 280 | +++ b/tests/package/test_ruling_137.py
 281 | @@ -374,6 +374,180 @@ class TestRuling141StandAloneSoft(unittest.TestCase):
 282 |          self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))
 283 |  
 284 |  
 285 | +class TestRuling141LineUpChain(unittest.TestCase):
 286 | +    """RULING 141 (3), THE LINE-UP CHAIN, PHASE A, in the never-empty pass: a line-up refused ONLY by soft line-up gates
 287 | +    (clip ratings under the clips-alone floor, joins past the one bridge, the question hook's first join) is KEPT, the
 288 | +    search goes on (a clean line-up first), and when it runs out the best kept one is retried once ACCEPTING: its soft
 289 | +    failures, and its clip ratings under coherence's own floor, become plain flags within the cap of 3. The through-line,
 290 | +    the hook's own bar and every other L-y check stay HARD; the writes and the value verdict are untouched."""
 291 | +    H = {"moment_id": "h", "text": "Bitcoin h x.", "hook_rating": {"scroll": 5, "alone": 5, "setup": 5, "backend": "xai:grok"}}
 292 | +    X, Y = {"moment_id": "x", "text": "Bitcoin x x."}, {"moment_id": "y", "text": "Bitcoin y x."}
 293 | +
 294 | +    def med(self, ratings=None, flagged=(), line="Nobody can change the rules of Bitcoin.", measured=True):
 295 | +        labs = PK.labels(3)
 296 | +        return {"measured": measured, "through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
 297 | +                "flagged": [j for j in PK.joins(labs) if j in flagged], "floors": {"clip": 3}}
 298 | +
 299 | +    def test_what_a_clips_alone_verdict_keeps(self):
 300 | +        segs = [self.H, self.X, self.Y]
 301 | +        self.assertEqual(PK.lineup_soft(segs, self.med({"clip_02": 2})),
 302 | +                         {"weak": {"clip_02": 2}, "floor": 3, "soft_joins": [], "n": 1})
 303 | +        two = self.med(flagged=("hook -> clip_01", "clip_01 -> clip_02"))
 304 | +        self.assertEqual(PK.lineup_soft(segs, two)["soft_joins"], ["clip_01 -> clip_02"])     # the first keeps a bridge
 305 | +        q = [dict(self.H, text="Is Bitcoin h x?"), self.X, self.Y]
 306 | +        self.assertEqual(PK.lineup_soft(q, self.med(flagged=("hook -> clip_01",)))["soft_joins"], ["hook -> clip_01"])
 307 | +        for bad in (self.med({"clip_02": 2}, line="none"), self.med({"clip_02": 2}, measured=False), self.med()):
 308 | +            self.assertIsNone(PK.lineup_soft(segs, bad), bad)                  # the through-line stays hard
 309 | +        under = dict(self.H, hook_rating=dict(self.H["hook_rating"], scroll=2))
 310 | +        self.assertIsNone(PK.lineup_soft([under, self.X, self.Y], self.med({"clip_02": 2})))   # the hook's own bar
 311 | +        self.assertIsNone(PK.lineup_soft(segs, dict(self.med(), clips={"hook": 5, "clip_01": 5})))   # unmeasured clip
 312 | +        self.assertEqual(PK.seg_marks([dict(self.H), dict(self.X, step_a_flags=["REFERENT_OUTSIDE", "UNCERTAIN"]),
 313 | +                                       dict(self.Y, edge_flags=["EDGE_IN"], stand_soft="why")]), 4)
 314 | +
 315 | +    def test_what_coherence_accepts(self):
 316 | +        segs = [self.H, self.X, self.Y]
 317 | +        coh = {"measured": True, "hook_own": {"passes": True}, "through_line": "Nobody can change the rules of Bitcoin.",
 318 | +               "clips": {"hook": 5, "clip_01": 2, "clip_02": 2}, "vo_point": 4, "floors": {"clip": 3, "vo_point": 3}}
 319 | +        self.assertEqual(PK.coherence_soft(coh, segs, ("clip_02",)),
 320 | +                         {"weak": {"clip_01": 2, "clip_02": 2}, "floor": 3, "n": 1})   # clip_02 is flagged already
 321 | +        for bad in (dict(coh, vo_point=2), dict(coh, through_line="none"), dict(coh, measured=False),
 322 | +                    dict(coh, hook_own={"passes": False}), dict(coh, clips={"hook": 5, "clip_01": 4, "clip_02": 4})):
 323 | +            self.assertIsNone(PK.coherence_soft(bad, segs), bad)
 324 | +        ans = lambda tl, vo: {"through_line": tl, "vo_point": vo}
 325 | +        panel = lambda *a: dict(coh, panel={"answers": list(a)})
 326 | +        self.assertIsNotNone(PK.coherence_soft(panel(ans("Nobody can change the rules here.", 4),
 327 | +                                                     ans("Nobody can change the rules here.", 3), ans("none", 4)), segs))
 328 | +        self.assertIsNone(PK.coherence_soft(panel(ans("none", 4), ans("none", 4),
 329 | +                                                  ans("Nobody can change the rules here.", 4)), segs))   # no majority
 330 | +
 331 | +    def rig(self, medleys, writes, never_empty=True, **kw):
 332 | +        import test_medley as TM                            # the never-empty pass asks the angle writer again
 333 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], medleys, writes,
 334 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]}, **kw)
 335 | +        r.build_kw = {"never_empty": never_empty}
 336 | +        return r, r.run()
 337 | +
 338 | +    WEAK = (False, [], {"clip_02": 2}, "Nobody can change the rules of Bitcoin.")
 339 | +
 340 | +    def test_a_weak_clip_seals_flagged_only_in_the_never_empty_pass(self):
 341 | +        _, clean = self.rig([self.WEAK] * 2, [], never_empty=False)
 342 | +        self.assertIsNone(clean["package"])
 343 | +        r, out = self.rig([self.WEAK] * 4, [None])
 344 | +        pk = out["package"]
 345 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])      # the best kept: retried
 346 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 347 | +        want = [f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
 348 | +                f"needs 3."]
 349 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
 350 | +        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
 351 | +                         (want, []))
 352 | +        self.assertEqual(len(r.medley_calls), 4)                           # the retry read its cached verdict
 353 | +
 354 | +    LINE = "Nobody can change the rules of Bitcoin."
 355 | +    J2 = (False, ["hook -> clip_01", "clip_01 -> clip_02"], None, LINE)
 356 | +    B = {"text": "First, why the rules hold.", "cites": ["x"], "why": "the next speaker's 'it' has no referent"}
 357 | +
 358 | +    def test_joins_past_the_one_bridge_flag_and_the_first_keeps_its_bridge(self):
 359 | +        _, out = self.rig([self.J2] * 8, [self.B])          # each pass: 2 line-ups and ruling 63's reorders
 360 | +        pk = out["package"]
 361 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 362 | +        want = [f"Between the second clip ({ch['clip_01']}) and the third clip ({ch['clip_02']}): the checker could "
 363 | +                f"not follow the jump."]
 364 | +        self.assertEqual(pk["bridge"]["join"], "hook -> clip_01")            # the first flagged join: bridged
 365 | +        self.assertEqual({g: (pk["gates"][g]["status"], pk["gates"][g].get("flags")) for g in ("medley", "ly_shape")},
 366 | +                         {"medley": ("FLAGGED", want), "ly_shape": ("FLAGGED", want)})
 367 | +        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
 368 | +                         (want, []))                                         # one doubt, flagged once
 369 | +
 370 | +    THREE = (False, ["hook -> clip_01", "clip_01 -> clip_02"], {"clip_01": 2, "clip_02": 2}, LINE)
 371 | +
 372 | +    def test_three_flags_are_kept_and_a_fourth_never(self):
 373 | +        _, out = self.rig([self.THREE] * 8, [self.B])
 374 | +        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # 2 clips + 1 join: the cap
 375 | +        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # + the hook under the bar: 4
 376 | +        _, out = self.rig([self.THREE] * 8, [self.B], hooks=under)
 377 | +        self.assertIsNone(out["package"])
 378 | +        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 379 | +
 380 | +    def test_a_clean_line_up_found_later_wins(self):
 381 | +        ok = (True, [], None, self.LINE)
 382 | +        r, out = self.rig([self.WEAK, self.WEAK, self.WEAK, ok], [None])
 383 | +        pk = out["package"]
 384 | +        self.assertEqual(([s["moment_id"] for s in pk["segments"]], pk["gates"]["medley"]["status"]),
 385 | +                         (["h", "x", "z"], "PASS"))
 386 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), [])
 387 | +        self.assertTrue([t for t in out["tried"] if t.get("kept")])          # kept, never needed
 388 | +
 389 | +    def test_coherence_ratings_flag_only_for_the_accepted_candidate(self):
 390 | +        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 5)])
 391 | +        pk = out["package"]
 392 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 393 | +        alone = (f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
 394 | +                 f"needs 3.")
 395 | +        coh = (f"The second clip ({ch['clip_01']}): with the narration, the checker rated how much it supports the "
 396 | +               f"point 2 of 5, needs 3.")
 397 | +        self.assertEqual((pk["gates"]["coherence"]["status"], sorted(pk["gates"]["coherence"]["flags"])),
 398 | +                         ("FLAGGED", sorted([coh, alone])))
 399 | +        self.assertEqual(sorted(PP.review_flags_of(pk["gates"])), sorted([alone, coh]))   # clip_02 flagged once
 400 | +        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 2)])   # the VO point too: today's path
 401 | +        self.assertIsNone(out["package"])
 402 | +
 403 | +    def test_a_question_hook_join_flags_with_no_bridge_at_the_question(self):
 404 | +        import test_medley as TM
 405 | +        ms = [dict(m, text="Is Bitcoin h x?") if m["moment_id"] == "h" else m for m in TM.TestBuildLoop.MS]
 406 | +        q = (True, ["hook -> clip_01"], None, self.LINE)          # one flagged join: ruling 37 refuses it today
 407 | +        r = TM.Rig(ms, ["h", "x", "y", "z"], [q] * 8, [None],
 408 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
 409 | +        r.build_kw = {"never_empty": True}
 410 | +        pk = r.run()["package"]
 411 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 412 | +        want = [f"Between the opening clip ({ch['hook']}) and the second clip ({ch['clip_01']}): the checker could not "
 413 | +                f"follow the jump."]
 414 | +        self.assertEqual((pk.get("bridge"), r.write_calls[-1][1]), (None, None))   # nothing written after the question
 415 | +        self.assertEqual((pk["gates"]["ly_shape"]["status"], PP.review_flags_of(pk["gates"])), ("FLAGGED", want))
 416 | +
 417 | +    def test_coherence_counts_one_doubt_per_clip_against_the_cap(self):
 418 | +        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}     # the hook's flag: 1
 419 | +        _, out = self.rig([self.WEAK] * 8, [None], hooks=under, coherences=[(False, 2, 5)])
 420 | +        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # hook + clip_02 + clip_01: 3, not 4
 421 | +        _, out = self.rig([self.J2] * 8, [self.B], hooks=under, coherences=[(False, 2, 5)])
 422 | +        self.assertIsNone(out["package"])                  # hook + a join + 2 new weak clips: 4, over the cap
 423 | +
 424 | +    def test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too(self):
 425 | +        two = (False, [], {"clip_01": 2, "clip_02": 2}, self.LINE)   # [h, x, y]: y weak (1 flag), then [h, x, z]:
 426 | +        r, out = self.rig([self.WEAK, two, self.WEAK, two], [None])  # x and z weak (2 flags); both kept
 427 | +        self.assertEqual(sum(bool(t.get("kept")) for t in out["never_empty"]["soft_record"]["tried"]
 428 | +                             if t.get("kept")) if not out.get("package") else len([t for t in out["tried"]
 429 | +                                                                                  if t.get("kept")]), 2)
 430 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "y"])   # 1 flag, not 2
 431 | +        import test_medley as TM
 432 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [self.WEAK] * 2, [None],
 433 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
 434 | +        r.build_kw = {"never_empty": True, "lineups": 1}  # one judged line-up a pass: the budget ends first
 435 | +        self.assertEqual([s["moment_id"] for s in r.run()["package"]["segments"]], ["h", "x", "y"])
 436 | +
 437 | +    def test_the_rows_flag_only_in_the_soft_pass_and_only_on_a_passing_shape(self):
 438 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 439 | +        soft_med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": ["clip_01 -> clip_02"],
 440 | +                    "hook_own": {"passes": True}, "soft": {"weak": {}, "floor": 3, "soft_joins": ["clip_01 -> clip_02"],
 441 | +                                                           "n": 1}}
 442 | +        coh = {"backend": "b", "replayed": False, "measured": True, "soft": {"weak": {"clip_01": 2}, "floor": 3, "n": 1}}
 443 | +        who = {"hook": "A", "clip_01": "B", "clip_02": "C"}
 444 | +        inv = lambda soft, shape: PK.inventory(**dict(TestStage2a().base(t), coh=coh), medley=(True, soft_med),
 445 | +                                               shape=shape, soft=soft, who=who)
 446 | +        g = inv(True, (True, []))
 447 | +        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["FLAGGED"] * 3)
 448 | +        g = inv(False, (True, []))
 449 | +        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["PASS"] * 3)
 450 | +        self.assertEqual(inv(True, (False, ["3 bridges"]))["ly_shape"]["status"], "FAIL")   # a hard L-y failure
 451 | +
 452 | +    def test_no_through_line_is_never_kept(self):
 453 | +        none = (False, [], {"clip_02": 2}, "none")
 454 | +        _, out = self.rig([none] * 4, [None])
 455 | +        self.assertIsNone(out["package"])
 456 | +        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 457 | +
 458 | +
 459 |  class TestTheDayCount(unittest.TestCase):
 460 |      def test_counted_per_day_ledger(self):
 461 |          with tempfile.TemporaryDirectory() as d:
 462 | 
```

---

pp-selectid: RULING 141 (3) (orchestrator 13:40 ET Nov 17), THE LINE-UP CHAIN, PHASE A: the approved R136 design (2)'s
KEPT CANDIDATES for clip ratings and joins, in the never-empty pass only. Context: package.build runs the clean pass, and
only when it seals nothing runs _build(soft=True); soft gates flag in one plain sentence each; at most 3 flags seal
(package_pin.REVIEW_FLAGS_MAX, package_pin.py:47; review_flags_of :399 gives each sentence once; flagged_ok :392 needs
non-empty string flags). Scope agreed with the integrator (14:35 ET): its render never holds on unbridged flagged joins
(R11 does not read medley.flagged; R1 is soft at validate; check_pin_only checks no joins); its check_pin_only REFUSES
a pin whose takeaway_value is not exactly PASS (package_pin TAKEAWAY_GATES :68), so the writes and the value verdict are
UNTOUCHED here. The through-line stays HARD (ruling 141 (1): "those four clips do not make a video").

THE CHANGE (package.py; the clean pass is unchanged):
(a) lineup_soft (:2235): a clips-alone verdict (medley(), its ok rule :2212: hook passing, through-line stated, every clip
    >= the floor, <= LY_MAX_BRIDGES flagged joins) whose ONLY failures are soft: clips under the floor; flagged joins
    past the one bridge (the first bridgeable flagged join keeps its bridge); the question hook's first join (ruling 37:
    no bridge after a question). None (hard) when not measured, no through-line, the hook failing its own bar, a clip
    unrated, or nothing to flag.
(b) THE LOOP, per angle: kept / retried / accept_key reset at :3925. KEEP (:4043): in the soft pass, a verdict failing
    (or ruling 37 refusing) with lineup_soft non-None and seg_marks (:2226: the clips' own flags) + its flags <= 3 is
    appended; the search then goes on exactly as before (a clean line-up wins first: it seals and the loop ends).
    RETRY: when the search runs out (:3980, where today "no line-up" breaks) or the judged-line-up budget ends (the
    condition :3945 and :3951), the best kept candidate (best_kept :2311: fewest flags, then the highest lowest rating) is
    retried ONCE; its clips-alone verdict is the cached one (judged, :4008; no new call, total unchanged) and is taken as
    passing with med["soft"] (:4016). Ruling 37 skips a soft join (:4107); the bridge goes to the first flagged join that
    is not soft (bj, :4114, also used for the declined-bridge reason and bridge_confirmed_by). Every later gate runs as
    today: the lock (HARD), vision, the writes, the re-screen.
(c) COHERENCE, the accepted candidate only (:4389): a failure whose ONLY cause is clip ratings under coherence's own floor
    (coherence_soft :2264: measured, the hook passing, the through-line stated and the VO point at its floor; for the
    free panel (:2102's majority) a majority of answers with both) is accepted when every flag stays within 3; a clip the
    clips-alone verdict already flagged is one doubt (counted once, its same sentence reused). Any other failure follows
    today's path (the VO point under the floor still rewrites the takeaway).
(d) ly_shape (:2973): its ruling-37 check and "every flagged join bridged" accept exactly the soft joins of an accepted
    candidate (soft_joins_of :2259; empty for any other verdict). Its other checks stay HARD.
(e) inventory (:4536, :4561): the medley row FLAGGED with the hook-bar sentence (2b) + the clip and join sentences; the
    ly_shape row FLAGGED with the join sentences (only when the shape passes); the coherence row FLAGGED with its
    sentences. package_pin.SOFT_GATES adds "coherence" and "ly_shape".

TESTS (test_ruling_137, 12 new; test_medley's Rig runs the real build): the units of (a) and (c); END TO END: a weak clip
seals flagged only in the never-empty pass (the retry reads its cached verdict); two flagged joins: the bridge at the
first, the second flagged on medley and ly_shape, once in review_flags; a question hook's join flags with nothing
written after the question; 3 flags keep and a 4th never; a clean line-up found later wins; coherence flags only for
the accepted candidate (the VO point under its floor still fails); the cap counts one doubt per clip; the retry takes
the fewest flags and the budget's end retries too; the rows flag only in the soft pass and only on a passing shape; no
through-line is never kept. Mutations: 22 of 24 killed. C1 (the retry's `soft`) is equivalent: kept fills only in the
soft pass. C12 is NOT UNIT-TESTED, please read: coherence is softened only for key == accept_key; the mutant widens it to
any later line-up of the angle after a retry, reachable only through the writer re-screen's hard refusal and its swap
(:4240) after the accepted candidate.

PLEASE CHECK: (1) can a HARD failure be kept or accepted (the through-line, the hook's own bar, the lock, a non-join
L-y check, coherence's VO point)? (2) the clean pass unchanged; (3) the retry: once per angle, the cached verdict, the
budget condition cannot loop; (4) the cap (unique sentences) and the one-doubt rule; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
