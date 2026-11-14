# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_1441
# Branch: pp-selectid
# Generated: 2026-11-14 14:41 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_1441/C1_STEP.diff (522 lines)
```
   1 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
   2 | index 84ef788..e9a3173 100644
   3 | --- a/pipeline/spotlight.py
   4 | +++ b/pipeline/spotlight.py
   5 | @@ -48,6 +48,7 @@ import eligibility as E
   6 |  import house_style as HS
   7 |  import package as P
   8 |  import package_pin as PP
   9 | +import tail_variant as TV
  10 |  import vo_fidelity as VF
  11 |  
  12 |  SPOT_S = (12.0, 35.0)                  # ruling 90: 12 to 35 s of clip
  13 | @@ -152,6 +153,9 @@ def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
  14 |          return None, f"the moment itself: {why}"
  15 |      if dur >= target:
  16 |          return m, None                                 # long enough: no snap, the moment as it is
  17 | +    if (m.get("derived_from") or {}).get("ruling") == 104:      # RULING 104: a variant ends where it must; snapping
  18 | +        return None, (f"{dur:.2f} s, and a ruling-104 variant is never snapped outward (that would put back the "
  19 | +                      f"words it leaves out)")
  20 |      blocked = []
  21 |      while dur < target:
  22 |          step = None
  23 | @@ -484,6 +488,12 @@ def _published_ts(m):
  24 |      return datetime.strptime(z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if z else float("-inf")
  25 |  
  26 |  
  27 | +def finalist_order(ms):
  28 | +    """The finalists' order: best first (rank_key), every ruling-104 variant after its own parent (the 14:12 order:
  29 | +    the full clip is tried first; tail_variant.parents_first)."""
  30 | +    return TV.parents_first(sorted(ms, key=rank_key))
  31 | +
  32 | +
  33 |  def rank_key(m):
  34 |      """Best first: the hook's own-job rating, the ALONE rating, the hook's parts, the miner's score, the newest
  35 |      source, then the id (a total order)."""
  36 | @@ -957,7 +967,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  37 |          else:
  38 |              stop(mid, f"ruling 92: {w}")
  39 |      passed([m["moment_id"] for m in ok_src], 8)
  40 | -    ranked = sorted(ok_src, key=rank_key)
  41 | +    ranked = finalist_order(ok_src)
  42 |      out["finalists"] = [m["moment_id"] for m in ranked]
  43 |      log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
  44 |          f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
  45 | @@ -1122,7 +1132,8 @@ def package_for(router, m, ctx, sources, a_two, truth, exc, pre, facts, log=prin
  46 |                         "alone": alone_score(m), "source": {k: src_rec.get(k) for k in ("ok", "why")},
  47 |                         "closing": {"candidate": (closing0 or {}).get("text"), "kept": pk1 is not None,
  48 |                                     "why_not": None if pk1 is not None else cl_why},
  49 | -                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes]}
  50 | +                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes],
  51 | +                       **({"derived_from": m["derived_from"]} if m.get("derived_from") else {})}   # RULING 104
  52 |      pk["models"] = {"writer": [x.backend for x in replies], "fidelity_verdict": fid.get("backend"),
  53 |                      "context": cx.get("backends"), "value": ((closing_rec or {}).get("value") or {}).get("backend"),
  54 |                      "layout": (src_rec.get("layout") or {}).get("backend")}
  55 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
  56 | new file mode 100644
  57 | index 0000000..42e3650
  58 | --- /dev/null
  59 | +++ b/pipeline/tail_variant.py
  60 | @@ -0,0 +1,169 @@
  61 | +"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN: "a spotlight (and a medley hook or clip) may be sealed
  62 | +as a variant that ENDS at an earlier sentence boundary of the mined moment, when that is what keeps it lawful (a held word
  63 | +after the boundary, a tail the cut cannot make, the seconds ceiling). It is a new span: it faces every gate again from
  64 | +the start (step A both families, CUTTABLE at the new OUT, ALONE >= 4, the opener rating, the 12 s floor, the visual check,
  65 | +the lock pre-check), and the variant is recorded as derived from its parent row. Omission is judged by step A as always:
  66 | +a variant that drops the speaker's own condition or conclusion fails there."
  67 | +
  68 | +- variant(): the parent moment cut to end at the end of one of its own earlier sentences, made by the miner's own
  69 | +  machinery (moments.record over eligibility.Span: eligibility judged afresh, its id the span's own), with the parent's
  70 | +  scores, topics and risk, and "derived_from" (here and in its mined record): the parent row.
  71 | +- for_pool(): the variants a build adds to its pool, BESIDE their parents (every gate then judges them as any moment):
  72 | +  - a held word: the lock pre-check's newest HOLD on the parent's exact span (any decoder and rules: it only proposes a
  73 | +    candidate; the variant faces the pre-check under the current ones). The held word is placed on this side
  74 | +    (held_word); the variant ends at the parent's last sentence boundary before it.
  75 | +  - a tail the cut cannot make: a hold that is ruling 73's ("the render cannot cut this span"): the last sentence goes.
  76 | +  - the seconds ceiling: a parent longer than ceil_s: the longest variant within it.
  77 | +  When two apply, the shorter variant (it satisfies both). None when no earlier boundary does.
  78 | +- parents_first(): a variant is never tried before its own parent (the 14:12 order: the full clip first, if lawful).
  79 | +A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out."""
  80 | +import glob
  81 | +import json
  82 | +import os
  83 | +
  84 | +import attest as AT
  85 | +import canon as C
  86 | +import eligibility as E
  87 | +import moments as M
  88 | +
  89 | +CUT_HOLD = "ruling 73"          # a hold whose reason starts so: the render cannot cut this span (the tail goes)
  90 | +
  91 | +
  92 | +def variant(m, src, k, ctx, why):
  93 | +    """The parent moment `m` (a pp.moment/1 record) ending at the end of its source's sentence k, its first sentence
  94 | +    unchanged (m's first sentence <= k < its last). -> the new moment record. ValueError for any other k."""
  95 | +    k0, k1 = m["sentences"]
  96 | +    if not (isinstance(k, int) and k0 <= k < k1):
  97 | +        raise ValueError(f"a tail variant ends at an earlier sentence of the moment: {k!r} is not in [{k0}, {k1})")
  98 | +    sp = E.Span(src, k0, k)
  99 | +    derived = {"ruling": 104, "from": m["moment_id"],
 100 | +               "ledger_moment_id": (m.get("mined") or {}).get("ledger_moment_id"),
 101 | +               "sentences": [k0, k], "was": [k0, k1], "end_was": m.get("end"), "why": why,
 102 | +               "left_out": E.spoken(src.tokens[sp.w1 + 1:src.sentences[k1][1] + 1])}
 103 | +    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
 104 | +                        "risk": list(m.get("risk") or []), "topics": list(m.get("topics") or []),
 105 | +                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
 106 | +                   dict(m.get("mined") or {}, derived_from=derived))
 107 | +    rec["rank_score"] = M.rank_score(rec)
 108 | +    if m.get("source_key"):
 109 | +        rec["source_key"] = m["source_key"]
 110 | +    rec["derived_from"] = derived
 111 | +    return rec
 112 | +
 113 | +
 114 | +def holds(m, results_dir):
 115 | +    """The newest lock pre-check HOLD on the parent's exact span (its video, start and end to the millisecond, its own
 116 | +    text as the approved text, as a hook or a clip), in the integrator's results under ANY decoder and rules. -> the
 117 | +    entry, or None (no hold, or nothing readable)."""
 118 | +    start, end = round(float(m["start"]), 3), round(float(m["end"]), 3)
 119 | +    best = None
 120 | +    for p in sorted(glob.glob(os.path.join(results_dir, f"{m['video_id']}.{start:.3f}-{end:.3f}.*.json"))):
 121 | +        try:
 122 | +            with open(p) as f:
 123 | +                entries = json.load(f)
 124 | +        except (OSError, ValueError):
 125 | +            continue
 126 | +        for e in entries if isinstance(entries, list) else []:
 127 | +            w = e.get("window") if isinstance(e, dict) else None
 128 | +            try:
 129 | +                win = [round(float(w[0]), 3), round(float(w[1]), 3)] if isinstance(w, list) and len(w) == 2 else None
 130 | +            except (TypeError, ValueError):
 131 | +                win = None
 132 | +            if not (isinstance(e, dict) and e.get("outcome") == "hold" and win == [start, end] and
 133 | +                    e.get("role") in ("hook", "clip") and e.get("approved_text") == m.get("text")):
 134 | +                continue
 135 | +            at = str(e.get("at") or "")
 136 | +            if best is None or at >= best[0]:
 137 | +                best = (at, e)
 138 | +    return best[1] if best else None
 139 | +
 140 | +
 141 | +def held_word(m, src, entry):
 142 | +    """The index (into src.tokens) of the parent's first word that the HOLD is about, placed on THIS side: the entry's
 143 | +    second reading (as_spoken.text) against the parent's own text, through this side's canon and ruling 84's class
 144 | +    (attest.class_84, as decide() judges an adoption): the first difference outside the class whose approved side is
 145 | +    not empty, at its tokens' first occurrence among the parent's words (canon.canon_spans). Recomputed from the texts,
 146 | +    it does not depend on the canon the entry was written under. -> int, or None when it cannot be placed (no second
 147 | +    reading, no such difference, an insert on the spoken side alone, or tokens not found): then no variant."""
 148 | +    spoken = ((entry or {}).get("as_spoken") or {}).get("text") if isinstance(entry, dict) else None
 149 | +    if not isinstance(spoken, str) or not spoken.strip():
 150 | +        return None
 151 | +    w0, w1 = m["words"]
 152 | +    spans = C.canon_spans([t.get("word") or "" for t in src.tokens[w0:w1 + 1]])
 153 | +    toks = [t for t, _, _ in spans]
 154 | +    for d in AT.class_84(spoken, m["text"]):
 155 | +        if d["class"] is not None:
 156 | +            continue
 157 | +        want = d["approved"].split()
 158 | +        if not want:
 159 | +            return None                                  # the second reading inserted it: nowhere to end before
 160 | +        for i in range(len(toks) - len(want) + 1):
 161 | +            if toks[i:i + len(want)] == want:
 162 | +                return w0 + spans[i][1]
 163 | +        return None
 164 | +    return None
 165 | +
 166 | +
 167 | +def for_pool(moments, sources, ctx, results_dir, ceil_s):
 168 | +    """The ruling-104 variants for this build's pool. -> (variants, {parent id: why it has none / which it got})."""
 169 | +    import context_integrity as CI
 170 | +    have = {m["moment_id"] for m in moments}
 171 | +    out, notes = [], {}
 172 | +    for m in moments:
 173 | +        mid = m["moment_id"]
 174 | +        k0, k1 = m.get("sentences") or (None, None)
 175 | +        if not (isinstance(k0, int) and isinstance(k1, int) and k1 > k0):
 176 | +            continue                                     # one sentence: no earlier boundary
 177 | +        wanted = []
 178 | +        e = holds(m, results_dir)
 179 | +        try:
 180 | +            src = CI.source_for(m, sources)
 181 | +        except KeyError:
 182 | +            if e is not None or float(m.get("duration_s") or 0) > ceil_s:
 183 | +                notes[mid] = "no variant: its word record is not in this build"
 184 | +            continue
 185 | +        if e is not None:
 186 | +            if str(e.get("reason") or "").startswith(CUT_HOLD):
 187 | +                wanted.append((k1 - 1, f"a tail the cut cannot make ({str(e.get('reason'))[:160]})"))
 188 | +            else:
 189 | +                i = held_word(m, src, e)
 190 | +                ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]
 191 | +                if ks:
 192 | +                    wanted.append((ks[-1], f"a held word after the boundary: {src.tokens[i].get('word')!r} at "
 193 | +                                           f"{src.tokens[i].get('start')} s (the lock pre-check's hold, "
 194 | +                                           f"{e.get('request_id')})"))
 195 | +                else:
 196 | +                    notes[mid] = ("no variant: the held word cannot be placed" if i is None else
 197 | +                                  "no variant: the held word is in its first sentence")
 198 | +        if float(m.get("duration_s") or 0) > ceil_s:
 199 | +            t0 = float(m["start"])
 200 | +            ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]
 201 | +            if ks:
 202 | +                wanted.append((ks[-1], f"the seconds ceiling ({float(m['duration_s']):.2f} s > {ceil_s:g} s)"))
 203 | +            else:
 204 | +                notes[mid] = f"no variant: no earlier boundary within {ceil_s:g} s"
 205 | +        if not wanted:
 206 | +            continue
 207 | +        k = min(x[0] for x in wanted)
 208 | +        v = variant(m, src, k, ctx, "; ".join(w for _, w in wanted))
 209 | +        if v["moment_id"] in have:
 210 | +            notes[mid] = f"its variant {v['moment_id']} is already in the pool"
 211 | +            continue
 212 | +        have.add(v["moment_id"])
 213 | +        out.append(v)
 214 | +        notes[mid] = f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
 215 | +    return out, notes
 216 | +
 217 | +
 218 | +def parents_first(ranked):
 219 | +    """The finalists' order with every variant that is ranked ABOVE its own parent moved to just after the parent: the
 220 | +    full clip is tried first, its variant only after it (the 14:12 order). Everything else keeps its place."""
 221 | +    out = list(ranked)
 222 | +    for v in [m for m in ranked if (m.get("derived_from") or {}).get("from")]:
 223 | +        ids = [x["moment_id"] for x in out]
 224 | +        p = v["derived_from"]["from"]
 225 | +        if p in ids and ids.index(v["moment_id"]) < ids.index(p):
 226 | +            at = ids.index(p)
 227 | +            out.remove(v)
 228 | +            out.insert(at, v)                            # the parent moved up by one: v lands right after it
 229 | +    return out
 230 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 231 | index d2b60dd..cf26fce 100644
 232 | --- a/tests/package/proof_ledger.py
 233 | +++ b/tests/package/proof_ledger.py
 234 | @@ -70,6 +70,7 @@ import providers as P  # noqa: E402
 235 |  import speakers as SP  # noqa: E402
 236 |  import spotlight as SPOT  # noqa: E402
 237 |  import lock_precheck as LP  # noqa: E402
 238 | +import tail_variant as TV  # noqa: E402
 239 |  
 240 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 241 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 242 | @@ -131,6 +132,18 @@ def applied(router):
 243 |      return applies
 244 |  
 245 |  
 246 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None):
 247 | +    """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants BESIDE their parents (tail_variant.for_pool:
 248 | +    a lock pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every
 249 | +    gate judges them from the start, the clip scorer included (its pool is made from these moments). inputs["ruling_104"]
 250 | +    records them and why each parent has one or none. -> the new list of moments."""
 251 | +    variants, notes = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 252 | +    inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "notes": notes}
 253 | +    say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool" +
 254 | +        "".join(f"; {k}: {w}" for k, w in sorted(notes.items())))
 255 | +    return list(moments) + variants
 256 | +
 257 | +
 258 |  def start_refused(spent0):
 259 |      """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
 260 |      STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
 261 | @@ -259,6 +272,7 @@ def main(argv=None):
 262 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 263 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 264 |      inputs["word_pass"] = wp_rep
 265 | +    moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
 266 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 267 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 268 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 269 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 270 | new file mode 100644
 271 | index 0000000..de94c55
 272 | --- /dev/null
 273 | +++ b/tests/package/test_ruling_104.py
 274 | @@ -0,0 +1,247 @@
 275 | +#!/usr/bin/env python3
 276 | +"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN (pipeline/tail_variant.py and its use in the ledger
 277 | +build and the spotlight): a variant ENDING at an earlier sentence boundary of the mined moment, when that keeps it lawful
 278 | +(a held word after the boundary, a tail the cut cannot make, the seconds ceiling); a new span that faces every gate,
 279 | +recorded as derived from its parent row. The case: Blockware Solutions 06d34e15, held on "401k".
 280 | +Offline: word-timed test sources, a temporary results directory."""
 281 | +import copy
 282 | +import json
 283 | +import os
 284 | +import sys
 285 | +import tempfile
 286 | +import unittest
 287 | +
 288 | +HERE = os.path.dirname(os.path.abspath(__file__))
 289 | +REPO = os.path.dirname(os.path.dirname(HERE))
 290 | +for _p in ("pipeline", "tests/package", "tests/eligibility"):
 291 | +    sys.path.insert(0, os.path.join(REPO, _p))
 292 | +import eligibility as E  # noqa: E402
 293 | +import moments as M  # noqa: E402
 294 | +import proof_ledger as PLG  # noqa: E402
 295 | +import spotlight as SPOT  # noqa: E402
 296 | +import tail_variant as TV  # noqa: E402
 297 | +import test_spotlight as TS  # noqa: E402
 298 | +from test_eligibility import NOW, REG, source  # noqa: E402
 299 | +
 300 | +SENTENCES = ["On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin.",
 301 | +             "That ended up being one of the best financial decisions I've ever made, but not for the reason most "
 302 | +             "people think.",
 303 | +             "I'm 26 now, and I still don't use my Roth IRA.",
 304 | +             "I don't have a 401k.",
 305 | +             "I don't own a single share of any index fund, and I'm on pace to be financially independent by 45."]
 306 | +CTX = E.Context(NOW, REG)
 307 | +META = {"scores": {"contempt_outrage": 0, "hook_first_2s": 5, "quotable": 4, "stakes": 5, "stance": 4,     # the real
 308 | +                   "stands_alone": 5, "surprising_fact": 4},                                         # row's, build 11
 309 | +        "names_person": False, "risk": [], "topics": ["bitcoin"], "reason": "Strong personal narrative hook"}
 310 | +
 311 | +
 312 | +def parent(src, k0=0, k1=4, vid="7BqLu-wzbU0"):
 313 | +    sp = E.Span(src, k0, k1)
 314 | +    m = M.record(sp, META, CTX, M.judge(sp, CTX), {"ledger_moment_id": "06d34e155feae654ee56"})
 315 | +    m["rank_score"] = M.rank_score(m)
 316 | +    m["source_key"] = vid
 317 | +    return m
 318 | +
 319 | +
 320 | +def blockware():
 321 | +    src = source(SENTENCES, vid="7BqLu-wzbU0")
 322 | +    return src, parent(src)
 323 | +
 324 | +
 325 | +def hold(m, decoder="c705b20ed800", at="2026-11-14T18:51:07Z", spoken=None, reason="ruling 72/84: ... at "
 326 | +         "[['401000', '401']]", outcome="hold", role="hook", text=None):
 327 | +    return {"request_id": "pp-selectid.ledger_x.1", "video_id": m["video_id"], "start": m["start"], "end": m["end"],
 328 | +            "window": [round(m["start"], 3), round(m["end"], 3)], "role": role,
 329 | +            "approved_text": m["text"] if text is None else text, "outcome": outcome, "reason": reason, "at": at,
 330 | +            "as_spoken": {"verdict": outcome, "text": m["text"].replace("401k.", "401 ,") if spoken is None
 331 | +                          else spoken}}
 332 | +
 333 | +
 334 | +def put(d, m, entries, decoder="c705b20ed800"):
 335 | +    p = os.path.join(d, f"{m['video_id']}.{round(m['start'], 3):.3f}-{round(m['end'], 3):.3f}.{decoder}.json")
 336 | +    with open(p, "w") as f:
 337 | +        json.dump(entries, f)
 338 | +
 339 | +
 340 | +class TestTheVariant(unittest.TestCase):
 341 | +    def test_it_ends_at_the_boundary_is_a_new_span_and_names_its_parent(self):
 342 | +        src, m = blockware()
 343 | +        v = TV.variant(m, src, 2, CTX, "a held word")
 344 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 345 | +        self.assertEqual((v["sentences"], v["start"], v["end"]), ([0, 2], m["start"], src.tokens[src.sentences[2][1]]["end"]))
 346 | +        self.assertNotEqual(v["moment_id"], m["moment_id"])                            # its own id
 347 | +        self.assertEqual(v["moment_id"], M.record(E.Span(src, 0, 2), META, CTX, M.judge(E.Span(src, 0, 2), CTX),
 348 | +                                                  {})["moment_id"])                    # the span's own
 349 | +        d = v["derived_from"]
 350 | +        self.assertEqual((d["ruling"], d["from"], d["ledger_moment_id"], d["sentences"], d["was"]),
 351 | +                         (104, m["moment_id"], "06d34e155feae654ee56", [0, 2], [0, 4]))
 352 | +        self.assertEqual(d["left_out"], " ".join(SENTENCES[3:]))
 353 | +        self.assertEqual(v["mined"]["derived_from"], d)                                 # in its mined record too
 354 | +        self.assertEqual((v["source_key"], v["scores"], v["topics"]), (m["source_key"], m["scores"], m["topics"]))
 355 | +        self.assertEqual(set(v["eligibility"]), {"hook", "clip"})                       # judged afresh on its span
 356 | +        for k in (4, 5, -1, "2"):
 357 | +            with self.assertRaises(ValueError):
 358 | +                TV.variant(m, src, k, CTX, "x")
 359 | +
 360 | +
 361 | +class TestTheHeldWord(unittest.TestCase):
 362 | +    def test_the_401k_hold_is_placed_on_its_word_from_the_texts(self):
 363 | +        src, m = blockware()
 364 | +        i = TV.held_word(m, src, hold(m))
 365 | +        self.assertEqual(src.tokens[i]["word"], "401k.")
 366 | +        self.assertEqual(i, src.sentences[3][0] + 4)                                   # "I don't have a 401k."
 367 | +
 368 | +    def test_a_difference_inside_ruling_84_s_class_is_passed_over(self):
 369 | +        """A one-function-word substitution earlier in the span is in ruling 84's class: the held word is still 401k."""
 370 | +        src, m = blockware()
 371 | +        spoken = m["text"].replace("one of the best", "one of a best").replace("401k.", "401 ,")
 372 | +        self.assertEqual(src.tokens[TV.held_word(m, src, hold(m, spoken=spoken))]["word"], "401k.")
 373 | +
 374 | +    def test_an_insert_before_the_hold_cannot_be_placed_so_no_variant(self):
 375 | +        """The second reading inserts a number in the FIRST sentence and differs on 401k: no variant can leave the
 376 | +        insert out, so the word is not placed (no variant), never the later 401k."""
 377 | +        src, m = blockware()
 378 | +        spoken = m["text"].replace("into Bitcoin.", "into Bitcoin 21.").replace("401k.", "401 ,")
 379 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=spoken)))
 380 | +
 381 | +    def test_what_cannot_be_placed_gives_none(self):
 382 | +        src, m = blockware()
 383 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken="")))                          # no second reading
 384 | +        self.assertIsNone(TV.held_word(m, src, dict(hold(m), as_spoken=None)))
 385 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("401k.", "401k, um,"))))  # a filler
 386 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("Bitcoin.", "Bitcoin 21."))))  # inserted
 387 | +
 388 | +
 389 | +class TestTheHolds(unittest.TestCase):
 390 | +    def setUp(self):
 391 | +        self.d = tempfile.TemporaryDirectory()
 392 | +        self.addCleanup(self.d.cleanup)
 393 | +
 394 | +    def test_the_newest_hold_on_the_exact_span_under_any_decoder(self):
 395 | +        src, m = blockware()
 396 | +        self.assertIsNone(TV.holds(m, self.d.name))
 397 | +        put(self.d.name, m, [hold(m, at="2026-11-14T18:00:00Z", reason="old")], decoder="962353613cb0")
 398 | +        put(self.d.name, m, [hold(m, at="2026-11-14T18:51:07Z", reason="new"),
 399 | +                             hold(m, outcome="no_difference", at="2026-11-14T19:00:00Z"),       # not a hold
 400 | +                             hold(m, at="2026-11-14T19:30:00Z", text="another text"),           # another span's text
 401 | +                             dict(hold(m, at="2026-11-14T19:31:00Z"), window=[0.0, 9.0])])      # another window
 402 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 403 | +        only_old = tempfile.TemporaryDirectory()                                       # a hold under another decoder
 404 | +        self.addCleanup(only_old.cleanup)                                                # only: still a candidate
 405 | +        put(only_old.name, m, [hold(m, reason="under ruling 90's decoder")], decoder="962353613cb0")
 406 | +        self.assertEqual(TV.holds(m, only_old.name)["reason"], "under ruling 90's decoder")
 407 | +        with open(os.path.join(self.d.name, f"{m['video_id']}.0.000-1.000.c705b20ed800.json"), "w") as f:
 408 | +            f.write("{ broken")                                                                  # never read: another span
 409 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 410 | +
 411 | +
 412 | +class TestThePool(unittest.TestCase):
 413 | +    def setUp(self):
 414 | +        self.d = tempfile.TemporaryDirectory()
 415 | +        self.addCleanup(self.d.cleanup)
 416 | +
 417 | +    def pool(self, ms, sources, ceil_s=35.0):
 418 | +        return TV.for_pool(ms, sources, CTX, self.d.name, ceil_s)
 419 | +
 420 | +    def test_blockware_held_on_401k_gives_the_variant_ending_before_it(self):
 421 | +        src, m = blockware()
 422 | +        put(self.d.name, m, [hold(m)])
 423 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 424 | +        self.assertEqual([v["text"] for v in vs], [" ".join(SENTENCES[:3])])     # "...I still don't use my Roth IRA."
 425 | +        self.assertIn("a held word after the boundary: '401k.'", vs[0]["derived_from"]["why"])
 426 | +        self.assertIn(vs[0]["moment_id"], notes[m["moment_id"]])
 427 | +
 428 | +    def test_a_cut_the_render_cannot_make_drops_the_last_sentence(self):
 429 | +        src, m = blockware()
 430 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span: the OUT edge")])
 431 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src})
 432 | +        self.assertEqual(vs[0]["sentences"], [0, 3])
 433 | +
 434 | +    def test_the_seconds_ceiling_gives_the_longest_variant_within_it(self):
 435 | +        src, m = blockware()
 436 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01           # sentences 0-2 fit, 0-3 do not
 437 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 438 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 439 | +        self.assertIn("the seconds ceiling", vs[0]["derived_from"]["why"])
 440 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span")])   # both: the shorter
 441 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 442 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 443 | +        self.assertIn("a tail the cut cannot make", vs[0]["derived_from"]["why"])
 444 | +
 445 | +    def test_no_variant_where_none_keeps_it_lawful(self):
 446 | +        src, m = blockware()
 447 | +        put(self.d.name, m, [hold(m, spoken=m["text"].replace("20th", "21st"))])       # held in its FIRST sentence
 448 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 449 | +        self.assertEqual((vs, notes[m["moment_id"]]), ([], "no variant: the held word is in its first sentence"))
 450 | +        one = parent(src, 2, 2)                                                           # one sentence: no boundary
 451 | +        put(self.d.name, one, [hold(one)])
 452 | +        self.assertEqual(self.pool([one], {"7BqLu-wzbU0": src}), ([], {}))
 453 | +        self.assertEqual(self.pool([m], {}), ([], {m["moment_id"]: "no variant: its word record is not in this build"}))
 454 | +        clean = blockware()[1]                                                            # no hold, under the ceiling
 455 | +        clean["start"] += 0.0005                                                          # (another span on file)
 456 | +        self.assertEqual(self.pool([clean], {"7BqLu-wzbU0": src}), ([], {}))
 457 | +
 458 | +    def test_a_variant_already_in_the_pool_is_not_added_twice(self):
 459 | +        src, m = blockware()
 460 | +        put(self.d.name, m, [hold(m)])
 461 | +        v = TV.variant(m, src, 2, CTX, "x")
 462 | +        vs, notes = self.pool([m, v], {"7BqLu-wzbU0": src})
 463 | +        self.assertEqual(vs, [])
 464 | +        self.assertIn("already in the pool", notes[m["moment_id"]])
 465 | +
 466 | +    def test_the_ledger_build_puts_them_beside_their_parents(self):
 467 | +        src, m = blockware()
 468 | +        put(self.d.name, m, [hold(m)])
 469 | +        inputs, said = {}, []
 470 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, inputs, said.append, results_dir=self.d.name)
 471 | +        self.assertEqual([x["moment_id"] for x in out][0], m["moment_id"])              # the parent stays
 472 | +        self.assertEqual(len(out), 2)
 473 | +        self.assertEqual(inputs["ruling_104"]["variants"], [out[1]["moment_id"]])
 474 | +        self.assertIn("RULING 104 (the tail-side twin): 1 variant(s) in the pool", said[0])
 475 | +
 476 | +
 477 | +class TestTheSpotlight(unittest.TestCase):
 478 | +    def test_the_full_clip_is_tried_before_its_variant(self):
 479 | +        A, B, p = {"moment_id": "a"}, {"moment_id": "b"}, {"moment_id": "p"}
 480 | +        v = {"moment_id": "v", "derived_from": {"ruling": 104, "from": "p"}}
 481 | +        ids = lambda xs: [x["moment_id"] for x in xs]
 482 | +        self.assertEqual(ids(TV.parents_first([v, A, p, B])), ["a", "p", "v", "b"])
 483 | +        self.assertEqual(ids(TV.parents_first([p, A, v])), ["p", "a", "v"])             # already after: unchanged
 484 | +        self.assertEqual(ids(TV.parents_first([A, v, B])), ["a", "v", "b"])             # no parent: unchanged
 485 | +
 486 | +    def test_the_spotlight_s_finalists_put_the_parent_first_however_the_variant_ranks(self):
 487 | +        p = {"moment_id": "p", "rank_score": 1.0, "published_at": "2026-11-14T17:00:22+00:00"}
 488 | +        v = dict(p, moment_id="v", rank_score=9.0, derived_from={"ruling": 104, "from": "p"})
 489 | +        x = dict(p, moment_id="x", rank_score=5.0)
 490 | +        self.assertEqual([m["moment_id"] for m in sorted([p, v, x], key=SPOT.rank_key)], ["v", "x", "p"])
 491 | +        self.assertEqual([m["moment_id"] for m in SPOT.finalist_order([p, v, x])], ["x", "p", "v"])
 492 | +
 493 | +    def test_a_variant_is_never_snapped_outward(self):
 494 | +        src, m = blockware()
 495 | +        short = TV.variant(m, src, 1, CTX, "x")                                          # two sentences, under 13.7 s
 496 | +        self.assertLess(short["duration_s"], SPOT.SNAP_TO_S)
 497 | +        caps = lambda vid: ([], None)
 498 | +        v, why = SPOT.snap(short, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)
 499 | +        self.assertIsNone(v)
 500 | +        self.assertIn("never snapped outward", why)
 501 | +        plain = dict(short)
 502 | +        plain.pop("derived_from")
 503 | +        v, _ = SPOT.snap(plain, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)         # any other moment: snapped
 504 | +        self.assertIsNotNone(v)
 505 | +        long_ = TV.variant(m, src, 2, CTX, "x")
 506 | +        self.assertGreaterEqual(long_["duration_s"], SPOT.SNAP_TO_S)
 507 | +        self.assertIs(SPOT.snap(long_, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)[0], long_)
 508 | +
 509 | +    def test_the_spotlight_pin_records_where_the_variant_came_from(self):
 510 | +        m = TS.moment()
 511 | +        pk, why, *_ = TS.package(m=m)
 512 | +        self.assertIsNone(why)
 513 | +        self.assertNotIn("derived_from", pk["spotlight"])                               # every other pin as before
 514 | +        d = {"ruling": 104, "from": "06d34e155feae654ee56", "sentences": [0, 2], "was": [0, 4], "why": "x"}
 515 | +        pk, why, *_ = TS.package(m=dict(copy.deepcopy(m), derived_from=d))
 516 | +        self.assertIsNone(why)
 517 | +        self.assertEqual(pk["spotlight"]["derived_from"], d)
 518 | +
 519 | +
 520 | +if __name__ == "__main__":
 521 | +    unittest.main()
 522 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- A MOMENT is a mined span of whole sentences of one word-timed source (moments.record over eligibility.Span(source,
  k0, k1)): its text is the words as spoken, its id is the span's own, and eligibility is judged on the span.
- Each build:
  - adds the ledger's moments to a pool (tests/package/proof_ledger.py, LB.build_inputs);
  - sends the pool to the integrator's clip scorer (the ALONE rating);
  - runs the medley search (package.build) and then the SPOTLIGHT (spotlight.build).
- The spotlight's stages run cheapest first:
  - a free pool (usable, under the 35 s ceiling SPOT_S[1]; a moment under SNAP_TO_S 13.7 s is "snapped OUTWARD" by
    spotlight.snap: whole following sentences are added, then preceding ones);
  - step A from both families, CUTTABLE, the opener rating, the visual check, ALONE >= 4;
  - then, best first (rank_key), up to 3 finalists face the exclusion verdict, the render's lock pre-check
    (lock_precheck), the writes and every gate. The first that passes seals a pin.
- The lock pre-check's answers are list-of-entry files <video>.<start>-<end>.<decoder>.json in the integrator's results
  dir. An entry has outcome ("hold", "no_difference", ...), window, role, approved_text, reason, and as_spoken {verdict,
  differences, text: the second recogniser's full reading}.
- attest.class_84(spoken, approved) is this side's copy of the integrator's ruling-84 class: one dict per difference,
  {"spoken", "approved", "class"}; class None is a difference outside the class (a number, a name, a negation, or a
  substitution other than one function word): it holds. canon.canon_spans(words) gives (token, first word index, last
  word index).
- THE CASE: Blockware Solutions 06d34e15 (video 7BqLu-wzbU0, 0.000-22.940 s, hook 4, ALONE 4.0) is held because the
  second recogniser hears "I don't have a 401" where the lock says "401k". The integrator ran ruling 103's targeted
  re-listen on it; the hold is FINAL. The orchestrator: "if it holds, seal the tail-side variant ending '...I still don't
  use my Roth IRA.' if it passes every gate. It expires 00:00 ET: this is the spotlight demo PBX is waiting for."

THE ORCHESTRATOR'S RULING (14:12 ET Nov 14), verbatim:
"RULING 104, THE TAIL-SIDE TWIN: a spotlight (and a medley hook or clip) may be sealed as a variant that ENDS at an
earlier sentence boundary of the mined moment, when that is what keeps it lawful (a held word after the boundary, a tail
the cut cannot make, the seconds ceiling). It is a new span: it faces every gate again from the start (step A both
families, CUTTABLE at the new OUT, ALONE >= 4, the opener rating, the 12 s floor, the visual check, the lock pre-check),
and the variant is recorded as derived from its parent row. Omission is judged by step A as always: a variant that drops
the speaker's own condition or conclusion fails there."
And: "(3) Blockware 06d34e15: FIRST the re-listen (103) on '401k'; if it passes, seal the full 22.94 s spotlight; if it
holds, seal the tail-side variant ending '...I still don't use my Roth IRA.' if it passes every gate."

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- The pool (proof_ledger.main) is built from `moments` after this change's with_variants(), so the clip scorer, the
  medley and the spotlight all see each variant as a moment.
- package.usable / spotlight.pool keep one video at most once per line-up (L-y 4) and apply every free rule to each
  moment, the variant included.
- Every paid gate (step A both families, CUTTABLE, the opener rating, the visual check, ALONE, exclusion, the lock
  pre-check under the CURRENT decoder and rules, the writes) runs on each pool moment as before. Nothing in the diff
  skips a gate for a variant.
- package_pin seals the segment (video, start, end, text, ...). pk["spotlight"] rides on the pin OUTSIDE the seal
  (moments_package.spotlight).

THE CHANGE (the diff follows):
1. pipeline/tail_variant.py (new):
   - variant(m, src, k, ctx, why): the parent cut to end at its sentence k (k0 <= k < k1), made by
     moments.record(E.Span(src, k0, k)): eligibility judged afresh, its own id, the parent's scores, topics and risk.
     "derived_from" (ruling 104, the parent id, its ledger row, the sentences, why, the words left out) is set on it
     and on its mined record.
   - holds(m, results_dir): the newest HOLD entry on the parent's exact span (window, role hook or clip, approved_text
     equal to the parent's text), under ANY decoder and rules. It only proposes a candidate; the variant faces the
     pre-check under the current ones.
   - held_word(m, src, entry): the parent's first word the hold is about, placed on THIS side by class_84 on the entry's
     second reading against the parent's text (so it does not depend on the canon the entry was written under):
     - the first difference with class None and a non-empty approved side, at its tokens' first occurrence among the
       parent's words;
     - None when it cannot be placed, including an insert on the spoken side, which no variant can leave out.
   - for_pool(moments, sources, ctx, results_dir, ceil_s): per parent with more than one sentence, three triggers:
     - a hold: the variant ends at the last boundary before the held word;
     - ruling 73's cut hold: the last sentence goes;
     - over the ceiling: the longest variant within it.
     When several apply, the shorter variant. No duplicate id. The notes say why each parent has a variant or none.
   - parents_first(ranked): a variant ranked above its own parent moves to just after it; nothing else moves.
2. tests/package/proof_ledger.py: with_variants() adds the variants BESIDE their parents right after the inputs are
   built, records them in inputs["ruling_104"] and prints a RULING 104 line.
3. pipeline/spotlight.py:
   - snap() never snaps a ruling-104 variant outward: that would put back the words it leaves out.
   - finalist_order() = parents_first(sorted(rank_key)), so the full clip is tried first (the 14:12 order).
   - pk["spotlight"]["derived_from"] is set when the moment is a variant (outside the seal).
4. Tests: test_ruling_104.py (new, 16). 19 mutations.

ATTACK:
(a) Can a variant reach a pin without facing every gate, or with its parent's verdicts (cached step A, ALONE, the
    pre-check) instead of its own? Can it be snapped, trimmed or extended back over the held words?
(b) Can a variant still contain the held word (the boundary, the first occurrence, a repeated token)? Can it end
    mid-sentence?
(c) Can the full clip lose its turn (a variant sealed before the parent's own re-listen and pre-check), or a variant
    be added when no trigger applies?
(d) Is "recorded as derived from its parent row" met (on the moment, its mined record, the build record and the
    spotlight pin)? Can the pin's seal change for a pin that is not a variant?
(e) Anything else that could seal a wrong pin, double a moment in a line-up, or spend without a trigger.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

