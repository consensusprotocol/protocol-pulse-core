# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_2313
# Branch: pp-selectid
# Generated: 2026-11-16 23:13 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_2313/C1_STEP.diff (224 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 70e79be..c8e7874 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -3448,15 +3448,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |                                 **({"value": {k: value.get(k) for k in ("text", "ok", "measured", "adds", "no_restate",
   7 |                                                                         "missed", "short", "why", "words", "backend")}}
   8 |                                    if value is not None else {})}}
   9 | -        see(order)                                        # RULING 70: the added clip is seen too
  10 | -        vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  11 | -                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  12 | -        if vbad:
  13 | -            note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  14 | -            return None
  15 |          nv_pre = None
  16 | -        if lock_check is not None:                         # RULINGS 68 / 72: its own line-up
  17 | -            try:
  18 | +        if lock_check is not None:                         # RULINGS 68 / 72: its own line-up; RULING 130 (2): FIRST,
  19 | +            try:                                           # before its vision checks are paid
  20 |                  nv_pre = lock_check(order)
  21 |              except Exception as e:                        # noqa: BLE001  audit 1744 C1: no verdict, never a pass
  22 |                  nv_pre = LP.failed(e)
  23 | @@ -3465,6 +3459,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  24 |              if nv_pre.get("error") or not nv_pre.get("segments"):
  25 |                  out["lock_stop"] = note["why_not"]        # no verdict: the search stops, as for a voiced line-up
  26 |              return None
  27 | +        see(order)                                        # RULING 70: the added clip is seen too
  28 | +        vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  29 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  30 | +        if vbad:
  31 | +            note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  32 | +            return None
  33 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
  34 |          pk["medley"] = nv_med
  35 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
  36 | @@ -3710,22 +3710,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  37 |                  if med["flagged"]:
  38 |                      k = joins(labs).index(med["flagged"][0])
  39 |                      join = (k, med["joins"][med["flagged"][0]]["why"])
  40 | -                bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
  41 | -                                       pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  42 |                  extra, relined, w_used, written = "", False, 0, ()
  43 | -                see(segs)                                   # RULING 70: every clip seen before any write is paid
  44 | -                vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  45 | -                            "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
  46 | -                        for m in segs if VP.layout_block(m.get("visual"))                  # included); the cause named
  47 | -                        and not (m is segs[0] and opens_16x9(m))}          # ruling 123 (2): the 16:9-only HOOK only
  48 | -                if vbad or segs[0].get("visual_hook_block"):
  49 | -                    vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  50 | -                    dropped |= set(vbad)
  51 | -                    doomed |= set(vbad)
  52 | -                    rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
  53 | -                    relined, w_used = True, writes      # no write is paid
  54 | -                pre = None
  55 | -                if not relined and lock_check is not None:  # RULINGS 68 / 72: the render's own lock, before any write
  56 | +                pre, no_verdict = None, False
  57 | +                if lock_check is not None:                  # RULINGS 68 / 72: the render's own lock, before any write;
  58 | +                    #   RULING 130 (2) (orchestrator 23:00 ET Nov 16): and FIRST, before the paid checks of the clips
  59 | +                    #   (vision, exclusion, the second pass), so a clip the render cannot cut never costs money
  60 |                      try:
  61 |                          pre = lock_check(segs)
  62 |                      except Exception as e:                # noqa: BLE001  audit 1744 C1: no verdict, never a pass
  63 | @@ -3740,13 +3729,28 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  64 |                      if pre.get("error") or not pre["segments"]:      # no verdict is never a pass (law L-m): nothing
  65 |                          rec["why"] = f"ruling 68 / 72: no lock verdict: {pre.get('error')}"[:500]   # is written, the
  66 |                          rec["budget"], out["lock_stop"] = True, rec["why"]   # search stops, the line-up stays a
  67 | -                        w_used = writes                                     # candidate (class "budget")
  68 | +                        w_used, no_verdict = writes, True                   # candidate (class "budget")
  69 |                      elif held:                             # the render would hold these clips: out, re-lined
  70 |                          dropped |= set(held)
  71 |                          doomed |= set(held)
  72 |                          rec["why"] = ("ruling 72: the render's lock holds " +
  73 |                                        "; ".join(f"{k}: {v}" for k, v in held.items()))[:500] + ": re-lined"
  74 |                          relined, w_used = True, writes
  75 | +                bg = {}                                     # ruling 130 (2): only for a line-up the lock let through
  76 | +                if not relined and not no_verdict:
  77 | +                    bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
  78 | +                                           pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  79 | +                    see(segs)                               # RULING 70: every clip seen before any write is paid
  80 | +                    vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  81 | +                                "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip
  82 | +                            for m in segs if VP.layout_block(m.get("visual"))                  # (L-m included); the
  83 | +                            and not (m is segs[0] and opens_16x9(m))}      # cause named; ruling 123 (2): the 16:9-only
  84 | +                    if vbad or segs[0].get("visual_hook_block"):                               # HOOK only
  85 | +                        vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  86 | +                        dropped |= set(vbad)
  87 | +                        doomed |= set(vbad)
  88 | +                        rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
  89 | +                        relined, w_used = True, writes  # no write is paid
  90 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
  91 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
  92 |                  v_lost, v_redo, v_novoice, v_plan, val = [], False, None, None, None   # RULING 91 (medley half):
  93 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  94 | index 544684c..b3f5a13 100644
  95 | --- a/tests/package/proof_ledger.py
  96 | +++ b/tests/package/proof_ledger.py
  97 | @@ -220,6 +220,25 @@ def delivered_pins(paths):
  98 |  STOP_CEILING_USD = 1.25          # ORDER 17:50 ET Nov 16: --stop-usd at most this ('ADD 25 CENTS': a day cap of $1.25)
  99 |  
 100 |  
 101 | +def lock_off(segs):
 102 | +    """RULING 130 (2) with the 23:02 question (orchestrator, Nov 16): the lock pre-check's second recogniser is
 103 | +    ElevenLabs Scribe, OUTSIDE dollars per span (the integrator, 23:0x Nov 16). With --lock-precheck off no request is
 104 | +    written: the answer is NO VERDICT (never a pass, law L-m), so a line-up that reaches the lock stays a candidate
 105 | +    (class "budget") with nothing paid after it. -> lock_precheck.check's shape."""
 106 | +    return {"ok": False, "request_id": None, "segments": [],
 107 | +            "error": "not asked: --lock-precheck off (ruling 130 (2): the pre-check's Scribe is outside dollars; no "
 108 | +                     "request is sent until the orchestrator releases it)"}
 109 | +
 110 | +
 111 | +def lock_for(mode, out_dir, say):
 112 | +    """RULING 130 (2): the build's lock pre-check: lock_precheck.check, one numbered request per line-up asked
 113 | +    ('pp-selectid.<build>.<n>'), when mode is 'on'; else lock_off (nothing sent). -> the lock_check callable."""
 114 | +    if mode != "on":
 115 | +        return lock_off
 116 | +    n = iter(range(1, 10 ** 6))
 117 | +    return lambda segs: LP.check(segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say)
 118 | +
 119 | +
 120 |  def read_only(path):
 121 |      """ORDER 17:50 ET Nov 16 ("spend the fresh dollar on ONE line-up at a time, the likeliest first; do not screen the
 122 |      whole held pool at Grok"): the --only file, {"ids": [this build's moment ids, at least one], "why": a reason}.
 123 | @@ -383,6 +402,9 @@ def main(argv=None):
 124 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 125 |      ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
 126 |                      help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
 127 | +    ap.add_argument("--lock-precheck", choices=("on", "off"), default="on",
 128 | +                    help="RULING 130 (2): 'off' sends no lock pre-check request (its Scribe is outside dollars); a "
 129 | +                         "line-up that reaches the lock then waits as a candidate")
 130 |      ap.add_argument("--only", metavar="FILE", help="ORDER 17:50 ET Nov 16: {'ids': [moment ids], 'why': text}: this "
 131 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
 132 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
 133 | @@ -526,8 +548,7 @@ def main(argv=None):
 134 |                stories_path=PK.STORIES,                                             # ruling 118 (4): read only
 135 |                ledger_aliases=inputs.get("duplicates_of") or {},    # its ledger ids: a dropped duplicate -> the kept row
 136 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 137 | -              lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 138 | -                  segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 139 | +              lock_check=lock_for(a.lock_precheck, out_dir, say))    # rulings 68 / 72 / 130 (2): off sends nothing
 140 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 141 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 142 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 143 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 144 | index 384c887..b13522c 100644
 145 | --- a/tests/package/test_ledger_build.py
 146 | +++ b/tests/package/test_ledger_build.py
 147 | @@ -1025,5 +1025,36 @@ class TestOrder1750OneLineUpAtATime(unittest.TestCase):
 148 |          self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull).limit_usd, PLG.PL.LY_LIMIT_USD)
 149 |  
 150 |  
 151 | +class TestRuling130LockOff(unittest.TestCase):
 152 | +    """RULING 130 (2): --lock-precheck off writes no request and answers NO VERDICT, never a pass."""
 153 | +
 154 | +    def test_lock_off_answers_no_verdict_and_writes_nothing(self):
 155 | +        sys.path.insert(0, HERE)
 156 | +        import proof_ledger as PLG
 157 | +        import lock_precheck as LP
 158 | +        before = sorted(os.listdir(LP.REQUESTS)) if os.path.isdir(LP.REQUESTS) else []
 159 | +        got = PLG.lock_off([{"moment_id": "x", "video_id": "v", "start": 0.0, "end": 9.0}])
 160 | +        self.assertEqual((got["ok"], got["segments"], got["request_id"]), (False, [], None))
 161 | +        self.assertIn("not asked", got["error"])
 162 | +        self.assertEqual(sorted(os.listdir(LP.REQUESTS)) if os.path.isdir(LP.REQUESTS) else [], before)
 163 | +
 164 | +    def test_lock_for_sends_numbered_requests_when_on_and_nothing_when_off(self):
 165 | +        sys.path.insert(0, HERE)
 166 | +        import proof_ledger as PLG
 167 | +        self.assertIs(PLG.lock_for("off", "/x/ledger_1", print), PLG.lock_off)
 168 | +        with mock.patch.object(PLG.LP, "check", side_effect=lambda segs, rid, log=None: {"rid": rid}) as chk:
 169 | +            f = PLG.lock_for("on", "/x/ledger_1", print)
 170 | +            self.assertEqual([f([1])["rid"], f([2])["rid"]], ["pp-selectid.ledger_1.1", "pp-selectid.ledger_1.2"])
 171 | +        self.assertEqual(chk.call_count, 2)
 172 | +
 173 | +    def test_a_bad_lock_precheck_value_refuses_the_run(self):
 174 | +        sys.path.insert(0, HERE)
 175 | +        import proof_ledger as PLG
 176 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 177 | +                                                                                 "MOMENTS_PIN_LY.json")]
 178 | +        with mock.patch("sys.stderr", new=io.StringIO()), refused_only(), self.assertRaises(SystemExit):
 179 | +            PLG.main(["--delivered", *pins, "--lock-precheck", "maybe"])
 180 | +
 181 | +
 182 |  if __name__ == "__main__":
 183 |      unittest.main()
 184 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 185 | index 5996416..935d77a 100644
 186 | --- a/tests/package/test_medley.py
 187 | +++ b/tests/package/test_medley.py
 188 | @@ -2901,6 +2901,18 @@ class TestRuling72Lock(unittest.TestCase):
 189 |          import lock_precheck as LP
 190 |          self.assertEqual(LP.pin_problems(out["package"]), [])                       # the pin stage's own check
 191 |  
 192 | +    def test_ruling_130_a_clip_the_lock_holds_is_never_seen(self):
 193 | +        """RULING 130 (2) (23:00 ET Nov 16): the render's lock is asked FIRST: a clip it holds is never sent to the paid
 194 | +        vision check; the line-up the search forms next is seen once its own lock passes."""
 195 | +        calls = []
 196 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 197 | +                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
 198 | +        out = rig.run()
 199 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
 200 | +        self.assertNotIn("x", rig.visual_calls)                                  # held by the lock: never seen
 201 | +        self.assertTrue({"y", "z"} <= set(rig.visual_calls), rig.visual_calls)    # the next line-up: seen after it
 202 | +        self.assertIsNotNone(out["package"])
 203 | +
 204 |      def test_no_verdict_writes_nothing_and_stops_the_search(self):
 205 |          rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
 206 |                    lock_check=lock_stub(error=True))
 207 | @@ -2909,6 +2921,8 @@ class TestRuling72Lock(unittest.TestCase):
 208 |          self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))       # no write, no second angle
 209 |          self.assertTrue(out["tried"][0]["budget"])
 210 |          self.assertIn("no lock verdict", out["lock_stop"])
 211 | +        self.assertNotIn("y", rig.visual_calls)        # ruling 130 (2): the line-up's clip is never seen (h and x
 212 | +        #                                                are seen earlier only as the hook stage's openers)
 213 |          c = PK.load_candidate(TestRuling66Candidate().record(), source="proof/ledger_x")
 214 |          out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 215 |                    lock_check=lock_stub(error=True)).run()
 216 | @@ -2980,6 +2994,7 @@ class TestRuling72Lock(unittest.TestCase):
 217 |          self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y", "z"]])          # its own line-up, the added clip
 218 |          self.assertIsNone(out["package"])
 219 |          self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 220 | +        self.assertNotIn("z", rig.visual_calls)        # RULING 130 (2): the added clip the lock holds is never seen
 221 |  
 222 |  
 223 |  class TestRuling76Window(unittest.TestCase):
 224 | 
```

---

pp-selectid: RULING 130 (2) (orchestrator 23:00 ET Nov 16), verbatim: "ORDER OF GATES: run the lock pre-check on every
line-up candidate BEFORE any paid vision check, so a clip the render cannot cut never costs money and the search moves to
the next line-up while clips are fresh. Coordinate with the integrator's lock pre-check service; land it audited."
Files: pipeline/package.py, tests/package/test_medley.py, tests/package/proof_ledger.py, tests/package/test_ledger_build.py.

WHY: tonight's one line-up that passed ruling 117 paid 2 vision checks and 1 coherence call ($0.129) and was then refused
by the render's lock (ruling 72) on What Bitcoin Did d6adeb54; its BTC Sessions clip held at the lock too.

THE CHANGE (package.build's line-up loop, and the no-voice line-up):
(a) The lock block (lock_check(segs): rulings 68 / 72; its body UNCHANGED: a held clip is dropped and the line-up
    re-lined; no verdict: rec "budget", out["lock_stop"], w_used = writes) now runs FIRST, right after the clips-alone
    verdict passes. Only when it neither holds a clip nor gives no verdict (not relined and not no_verdict) are the
    background checks started (bg: exclusion_for and truth_for, the second pass) and the clips seen (see(segs), ruling
    70's paid vision check) with the vbad re-line as before. Before, bg and see(segs) ran first and the lock only on a
    line-up the vision check let through. bg is read in ONE place, UNCHANGED (package.py:3878 in the copy: got = {...
    for mid, f in bg.items()}), inside the writes loop, which a re-lined or no-verdict line-up never enters
    (w_used = writes: the loop's first test, package.py:3760, breaks), so bg = {} there is never read.
(b) The no-voice line-up (its own order, ruling 3 / 91): lock_check(order) first; on a hold or no verdict it returns
    None before see(order); its vision check and vbad only after a passing lock.
(c) The driver: --lock-precheck on|off (default on). lock_for(mode, out_dir, say): 'on' is lock_precheck.check
    (UNCHANGED, lock_precheck.py:171) with one numbered request per line-up ('pp-selectid.<build>.<n>', as before); 'off'
    is lock_off: NO request written, the answer is NO VERDICT ({"ok": False, "segments": [], "error": "not asked ..."}),
    so the build's unchanged no-verdict path keeps the line-up as a candidate (class "budget"), nothing paid after it.
    Why 'off' exists: the pre-check's second recogniser is ElevenLabs Scribe, outside dollars per span (the integrator,
    23:0x Nov 16); the orchestrator has not yet ruled whether daytime builds may spend them (STATE line 1, 23:02).

TESTS: test_medley TestRuling72Lock: new, a clip the lock holds is never sent to the vision check and the next line-up
is seen after its lock passes; the no-voice test: its added clip the lock holds is never seen; the no-verdict test: the
line-up's clip is never seen. test_ledger_build TestRuling130LockOff: lock_off writes nothing and answers no verdict;
lock_for numbers its requests when on and is lock_off when off; a bad --lock-precheck value refuses the run. Mutations
K1-K6 after a control run: 6 of 6 killed. Suites: 40 files by exit code, 854 tests.

PLEASE CHECK: (1) that no paid check (vision, exclusion, the second pass) can run for a line-up the lock holds or gave
no verdict on; (2) that a passing line-up is unchanged in every other respect (bg is read only in the writes loop);
(3) the no-voice path; (4) lock_off can never be a pass; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
