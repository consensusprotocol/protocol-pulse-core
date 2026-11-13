# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0640
# Branch: pp-selectid
# Generated: 2026-11-13 06:37 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0640/C1_STEP.diff (310 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index d266dbe..e7dbe5a 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -444,6 +444,44 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
   6 |      return a_by, fails, vendors, families
   7 |  
   8 |  
   9 | +def second_screen(router, cleared, a_by, sources, ctx, log=print):
  10 | +    """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
  11 | +    known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
  12 | +    comes from the writer's vendor (L-x). The only step-A vendors are the writers' own two (context_verdict: xai, then
  13 | +    heimdall), so each clip is screened again OFF its first verdict's vendor and family: whichever vendor then writes,
  14 | +    a verdict off it already exists, and no line-up is built on a clip that a re-screen would fail (the 05:48 build).
  15 | +    The clips are grouped by their first verdict's back-end, and the groups' step-A batches run in parallel (each
  16 | +    call takes about 3 min on Heimdall). -> ({moment id: [first verdict, second verdict]} for the clips that pass
  17 | +    both, {moment id: [why not]} for the rest). No second verdict, a failing one, or one from the first's vendor or
  18 | +    family is never a pass (law L-m)."""
  19 | +    groups = {}
  20 | +    for mid, m in cleared.items():
  21 | +        b = router.backends.get((a_by.get(mid) or {}).get("backend"))
  22 | +        groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
  23 | +    jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
  24 | +            for i in range(0, len(g), PRESCREEN_BATCH)]
  25 | +    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as ex:
  26 | +        futs = [ex.submit(prescreen, router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log)
  27 | +                for k, chunk in jobs]
  28 | +        res = [f.result() for f in futs]
  29 | +    two, fail = {}, {}
  30 | +    for (k, chunk), (got, fails, _, _) in zip(jobs, res):
  31 | +        for m in chunk:
  32 | +            mid, a2 = m["moment_id"], got.get(m["moment_id"])
  33 | +            b2 = router.backends.get((a2 or {}).get("backend"))
  34 | +            if fails.get(mid) or a2 is None:
  35 | +                fail[mid] = list(fails.get(mid) or ["STEP_A_UNAVAILABLE: no second verdict (law L-m)"])
  36 | +            elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
  37 | +                fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
  38 | +                             f"first's vendor {k[0]} (law L-m)"]
  39 | +            else:
  40 | +                two[mid] = [a_by[mid], a2]
  41 | +    for m in groups.get(None, []):
  42 | +        fail[m["moment_id"]] = ["STEP_A_UNKNOWN_BACKEND: the first verdict's back-end is unknown, so no second vendor "
  43 | +                                "can be chosen (law L-m)"]
  44 | +    return two, fail
  45 | +
  46 | +
  47 |  ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
  48 |  play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
  49 |  clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
  50 | @@ -1251,9 +1289,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  51 |      out["prescreen"]["trim_cut"] = trim_cut
  52 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  53 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  54 | +    a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log)        # ORDER 06:22 item 45
  55 | +    out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
  56 | +                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
  57 | +                                         for mid in cleared}
  58 | +    cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
  59 | +    log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
  60 | +        f"a verdict off it exists) ({time.time() - t0:.0f} s)")
  61 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  62 | -        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
  63 | -                           f"channels")
  64 | +        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
  65 | +                           f"vendors, from fewer than 3 channels")
  66 |          return out
  67 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
  68 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
  69 | @@ -1277,6 +1322,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  70 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
  71 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
  72 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
  73 | +
  74 | +    def off_writers(mid):
  75 | +        """ORDER 06:22 item 45: the moment's passing step-A verdict from a back-end off every writer's vendor and
  76 | +        family so far (the first screen's first), else None (the re-screen after a write decides, item 44)."""
  77 | +        for a_ in a_two.get(mid, ()):
  78 | +            b = router.backends.get(a_.get("backend"))
  79 | +            if b is not None and b.vendor not in writers_v and b.family not in writers_f:
  80 | +                return a_
  81 | +        return None
  82 | +    for mid in cleared:
  83 | +        a_by[mid] = off_writers(mid) or a_by[mid]
  84 |      writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
  85 |          {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
  86 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
  87 | @@ -1483,15 +1539,31 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  88 |                          continue
  89 |                      writers_v.add(wr.vendor)
  90 |                      writers_f.add(wr.family)
  91 | +                    for m in segs:                             # item 45: the verdict off every writer, when one exists
  92 | +                        a_by[m["moment_id"]] = off_writers(m["moment_id"]) or a_by[m["moment_id"]]
  93 |                      stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
  94 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
  95 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
  96 | -                        got_a, _, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f, store=None)
  97 | -                        for mid, a_ in got_a.items():
  98 | -                            a_by[mid] = a_
  99 | -                        if any(CI.a_failures(a_by.get(m["moment_id"], {})) for m in stale):
 100 | -                            rec["why"] = "step A, re-screened off the writer's vendor, fails a clip: re-lined"
 101 | -                            dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 102 | +                        got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 103 | +                                                         n=len(stale), store=None)
 104 | +                        bad = {}
 105 | +                        for m in stale:
 106 | +                            mid = m["moment_id"]
 107 | +                            if got_a.get(mid) is not None and not fails_a.get(mid):
 108 | +                                a_by[mid] = got_a[mid]
 109 | +                                a_two.setdefault(mid, []).append(got_a[mid])
 110 | +                            else:                              # no verdict off the writers is never a pass (L-m)
 111 | +                                bad[mid] = list(fails_a.get(mid) or ["STEP_A_UNAVAILABLE: no verdict off the writers "
 112 | +                                                                     "(law L-m)"])
 113 | +                        if bad:                                # ORDER 06:22 item 44: only these clips go, for good,
 114 | +                            dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 115 | +                            doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 116 | +                            out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 117 | +                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed))
 118 | +                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
 119 | +                                          f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 120 | +                                                        if swapped is not None else
 121 | +                                                        "no swap fits the line-up rules: re-lined"))
 122 |                              relined = True
 123 |                              break
 124 |                      if join is not None and fields["bridge"] is None:
 125 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 126 | index 3cb6fa9..b468959 100644
 127 | --- a/tests/package/test_medley.py
 128 | +++ b/tests/package/test_medley.py
 129 | @@ -425,23 +425,53 @@ class Rig:
 130 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 131 |  
 132 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 133 | -                 spend=None, no_hook=()):
 134 | +                 spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None):
 135 |          import providers as P
 136 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 137 |          self.takeaways, self.spend = list(takeaways or []), spend
 138 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 139 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 140 | +        self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 141 | +        self.screens, self.events, self.a_seen = [], [], []
 142 | +        self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 143 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 144 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 145 |          call = self.router.call
 146 | -        self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
 147 | -                                                          call(role, prompt, *a, **k))[1]
 148 | +
 149 | +        def rcall(role, prompt, *a, **k):
 150 | +            self.prompts.append((role, prompt))
 151 | +            self.events.append(role)
 152 | +            r = call(role, prompt, *a, **k)
 153 | +            if role == "angle_write" and angle_from:              # the angle from a named back-end (ORDER 06:22)
 154 | +                r = P.Reply(r.text, angle_from[0], angle_from[1], family=angle_from[2])
 155 | +            return r
 156 | +        self.router.call = rcall
 157 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 158 |          self.router.backends = {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek"),
 159 | -                                "heimdall:qwen": B("heimdall", "qwen")}
 160 | +                                "heimdall:qwen": B("heimdall", "qwen"), "openai:gpt": B("openai", "gpt")}
 161 |          self.router.chain = lambda role: ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
 162 |          self.write_avoid = []
 163 |  
 164 | +    def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 165 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print):
 166 | +        """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 167 | +        (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 168 | +        av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
 169 | +        name = next((x for x in ("xai:grok", "heimdall:deepseek", "openai:gpt")
 170 | +                     if self.router.backends[x].vendor not in av and self.router.backends[x].family not in af), None)
 171 | +        self.screens.append((name, [m["moment_id"] for m in ms]))
 172 | +        self.events.append(f"step_a:{name}")
 173 | +        got, fails = {}, {}
 174 | +        for m in ms[:n]:
 175 | +            mid = m["moment_id"]
 176 | +            v = self.router.backends[name].vendor if name else None
 177 | +            if name is None or (v, mid) in self.unavailable:
 178 | +                fails[mid] = ["STEP_A_UNAVAILABLE: ProviderError"]
 179 | +                continue
 180 | +            got[mid] = dict(self.A_OK, backend=name)
 181 | +            fails[mid] = list(self.a_fail.get((v, mid), []))
 182 | +        return got, fails, set(), set()
 183 | +
 184 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 185 |          self.medley_calls.append([m["moment_id"] for m in segs])
 186 |          ok, flagged, ratings, line = self.medleys.pop(0)
 187 | @@ -454,13 +484,14 @@ class Rig:
 188 |              raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
 189 |          self.write_calls.append(([m["moment_id"] for m in segs], join))
 190 |          self.write_avoid.append(avoid_vendor)
 191 | +        self.a_seen.append({m["moment_id"]: a_by[m["moment_id"]]["backend"] for m in segs})
 192 |          b = self.writes.pop(0)
 193 |          fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
 194 |                    "bridge_after": join[0] if join is not None and b is not None else None,
 195 |                    "title": {"text": "Nobody bends the rules", "cites": []},
 196 |                    "caption": {"text": "nobody bends these rules", "cites": []},
 197 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 198 | -        return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
 199 | +        return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 200 |  
 201 |      def run(self):
 202 |          fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
 203 | @@ -469,8 +500,7 @@ class Rig:
 204 |          cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
 205 |          stubs = {
 206 |              "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
 207 | -            "prescreen": lambda router, ms, *a, **k: ({m["moment_id"]: dict(self.A_OK) for m in ms},
 208 | -                                                      {m["moment_id"]: [] for m in ms}, set(), set()),
 209 | +            "prescreen": self.prescreen,
 210 |              "current_levels": lambda *a, **k: [],
 211 |              "medley": self.medley, "write_takeaway": self.write,
 212 |              "paid_gates": lambda *a, **k: (fid, cx),
 213 | @@ -837,6 +867,96 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 214 |          self.assertIsNotNone(out["package"])
 215 |  
 216 |  
 217 | +class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 218 | +    """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 219 | +    after a write swaps out that clip only, and the line-up carries on."""
 220 | +    MS = TestBuildLoop.MS
 221 | +
 222 | +    def test_every_cuttable_clip_is_screened_by_the_second_vendor_before_the_angle_step(self):
 223 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],      # the writer never sees y
 224 | +                  a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
 225 | +        out = rig.run()
 226 | +        self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
 227 | +        self.assertEqual(rig.screens[1], ("heimdall:deepseek", ["h", "x", "y", "z"]))  # the second, off xai
 228 | +        self.assertLess(rig.events.index("step_a:heimdall:deepseek"), rig.events.index("angle_write"))
 229 | +        sv = out["prescreen"]["second_vendor"]
 230 | +        self.assertEqual(sv["h"], "PASS (heimdall:deepseek)")
 231 | +        self.assertTrue(sv["y"].startswith("FAIL: REFERENT_OUTSIDE"), sv["y"])
 232 | +        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
 233 | +        self.assertNotIn("id=y ", angle_prompt)                    # never offered to the angles
 234 | +        self.assertIn("id=z ", angle_prompt)
 235 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])     # no line-up is built on it
 236 | +        self.assertIsNotNone(out["package"])
 237 | +
 238 | +    def test_a_clip_with_no_second_verdict_is_out(self):           # law L-m: nothing measured is never a pass
 239 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
 240 | +                  unavailable={("heimdall", "y")})
 241 | +        out = rig.run()
 242 | +        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith("FAIL: STEP_A_UNAVAILABLE"))
 243 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 244 | +
 245 | +    def test_the_verdict_used_is_the_one_off_the_writers_vendor(self):
 246 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 247 | +        rig.run()                                                  # the angle from vendor "fake": the first verdict
 248 | +        self.assertEqual(set(rig.a_seen[0].values()), {"xai:grok"})
 249 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 250 | +                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
 251 | +        out = rig.run()                                            # Grok wrote the angles: Heimdall's verdict counts
 252 | +        self.assertEqual(set(rig.a_seen[0].values()), {"heimdall:deepseek"})
 253 | +        self.assertEqual(len(rig.screens), 2)                      # and no re-screen was needed after the write
 254 | +        self.assertIsNotNone(out["package"])
 255 | +
 256 | +    def test_a_clip_that_fails_its_re_screen_is_swapped_out_alone_and_the_line_up_carries_on(self):
 257 | +        """The 05:48 build: a line-up passed the clips-alone verdict, a re-screen failed ONE clip, and the line-up was
 258 | +        lost. Now only that clip goes (for good, with its reason), the next-best clip takes its place, the clips-alone
 259 | +        verdict re-judges, and the build goes on to the writer. (Both vendors write here, so the rig's third vendor
 260 | +        re-screens.)"""
 261 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 262 | +                  [None, None], angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})
 263 | +        out = rig.run()
 264 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
 265 | +        self.assertEqual(out["prescreen"]["rescreen_failed"], {"y": ["REFERENT_OUTSIDE"]})
 266 | +        self.assertIn("swapped {'y': 'z'}", out["tried"][0]["why"])
 267 | +        self.assertIn("(out for good)", out["tried"][0]["why"])
 268 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 269 | +        self.assertEqual(rig.screens[2], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 270 | +        self.assertEqual(rig.screens[3], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 271 | +
 272 | +    def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
 273 | +        """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
 274 | +        flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
 275 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 276 | +                  [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
 277 | +        out = rig.run()
 278 | +        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 279 | +        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith("STEP_A_UNAVAILABLE"))
 280 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 281 | +
 282 | +    def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
 283 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 284 | +        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall",
 285 | +                                                                                                  "deepseek")}})()
 286 | +        ms = {m["moment_id"]: m for m in self.MS}
 287 | +        a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
 288 | +                "z": {"backend": "heimdall:deepseek"}}
 289 | +        seen = []
 290 | +
 291 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print):
 292 | +            seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
 293 | +            name = "heimdall:deepseek" if "xai" in wv else "heimdall:deepseek"     # z's second verdict: same vendor
 294 | +            return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
 295 | +        saved = PK.prescreen
 296 | +        PK.prescreen = fake
 297 | +        try:
 298 | +            two, fail = PK.second_screen(router, ms, a_by, {}, ctx())
 299 | +        finally:
 300 | +            PK.prescreen = saved
 301 | +        self.assertEqual(sorted(seen), [(["heimdall"], ["z"]), (["xai"], ["h", "x"])])   # grouped by first vendor
 302 | +        self.assertEqual(sorted(two), ["h", "x"])
 303 | +        self.assertTrue(fail["y"][0].startswith("STEP_A_UNKNOWN_BACKEND"))
 304 | +        self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 305 | +
 306 | +
 307 |  class TestRuling41Search(unittest.TestCase):
 308 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 309 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 310 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips from other channels); the integrator
renders them. Your role: a strict reviewer of the build loop's step-A verdict handling.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- Step A (law L-s) is a per-clip context verdict: who speaks, whose view, outside referents, retractions. It runs ONCE
  per moment per build, batched (PRESCREEN_BATCH = 8 excerpts per call), on the router's "context_verdict" chain.
- Law L-x: a verdict never comes from the WRITER's vendor or model family. The writer is the "angle_write" chain:
  Heimdall deepseek, then Heimdall qwen, then xai Grok, each with a 300 s deadline (ruling 5). The context_verdict
  chain is xai Grok, then Heimdall deepseek. There are only these two vendors.
- Before this change: step A ran off the EXPECTED writer's vendor (Heimdall), so on xai. When the angle call failed
  over to Grok (xai), every verdict was on the writer's vendor, and the build re-screened a line-up's clips off xai
  only AFTER the line-up passed the clips-alone verdict and its first write. In the 05:48 build that re-screen failed
  ONE clip, the whole line-up was discarded ("re-lined"), and no other line-up fit: no package.
- Laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts to make
  something pass.

The orders this diff implements (ORCHESTRATOR ORDER 06:22, verbatim):
44. "A failed re-screen removes that clip only (it stays out for good, with its reason). The other three had passed:
    swap in the next-best cuttable clip for the failed slot (ruling 41's swap), re-judge only what changed (the new
    clip's step A on both vendors, the clips-alone verdict), and carry on to the writer. Never discard a passing
    line-up for one replaceable clip."
45. "Run the off-vendor step A re-screen on every CUTTABLE clip BEFORE the angle step, so no line-up is ever built on
    a clip that will fail it. It is 10-13 clips, cheap, and it ends this failure class."

The change (pipeline/package.py):
1. second_screen(router, cleared, a_by, sources, ctx): groups the cuttable clips by their FIRST verdict's back-end
   (vendor, family), and screens each group again with prescreen() avoiding that vendor and family. The batches run
   in parallel (a Heimdall step-A call takes about 3 min). It returns {id: [first verdict, second verdict]} for clips
   passing both, and {id: [why not]} for the rest. Fail closed: no second verdict (STEP_A_UNAVAILABLE), a failing one,
   one from the first's vendor or family (STEP_A_SAME_VENDOR), or an unknown first back-end (STEP_A_UNKNOWN_BACKEND).
2. build(): after L-v 2 + CUTTABLE and the hook-onset stage, BEFORE the 3-channel check and the angle call, only the
   clips in second_screen's first result stay in `cleared`. out["prescreen"]["second_vendor"] records PASS (backend)
   or FAIL with the reasons.
3. After the angle call: off_writers(mid) returns the first of the clip's passing verdicts whose back-end is off every
   writer's vendor and family so far, and a_by[mid] takes it.
4. After each write (a write may add a vendor or family to the writers): a_by is re-picked with off_writers for the
   line-up. Any clip still on a writer's vendor or family ("stale") is re-screened (prescreen avoiding all writers).
   A clip whose re-screen fails OR gives no verdict is out for good (dropped and doomed, with its reasons in
   out["prescreen"]["rescreen_failed"]). The line-up is then swapped with ruling 41's swap_lineup at those places,
   and the loop judges the swapped line-up on the clips alone next, then writes. If no swap fits, it re-lines as
   before.
   - A K2 flag fixed here: the old branch assigned a_by only for the clips the re-screen returned, then tested
     CI.a_failures(a_by[...]). A clip whose re-screen call failed (no verdict) kept its STALE verdict from the
     writer's vendor and passed. Now no verdict is never a pass.

The tests (tests/package/test_medley.py):
- The build test rig's step A is now vendor-aware: like the real prescreen through the router, it answers on the
  first back-end off the given vendors and families (xai, then heimdall; a third vendor "openai" exists only in the
  rig, to exercise item 44 when both real vendors are writers). Its failures are set per (vendor, moment).
- New tests: the second screen runs on Heimdall over every cuttable clip before the angle call; a clip failing it, or
  with no second verdict, is never offered to the angles or a line-up; the verdict used is the one off the writer's
  vendor (Grok writing -> Heimdall's verdict, with no re-screen); a re-screen failing one clip swaps it out alone and
  the line-up carries on to a package, re-screening only the new clip; a re-screen with no verdict keeps the clip out;
  second_screen fails closed on an unknown back-end or a same-vendor answer.
- test_medley: 78 tests OK (72 before). The other suites (angles, gates, hook_onset, house_style, ledger_build,
  speakers, providers, moments, eligibility, select_by_id) are unchanged and OK.

Check in particular:
- that NO clip reaches the angle prompt or any line-up without a passing step-A verdict from each of the two vendors
  (items 45, L-m), and that the verdict actually used by the gates is off every writer's vendor and family (L-x),
  also after a write adds a vendor or family;
- that a failed or missing re-screen removes ONLY that clip, keeps it out of every later angle and line-up with its
  reason, and that the swapped line-up is judged on the clips alone before any write (item 44);
- the threading in second_screen: shared state, exceptions, ordering;
- anything that could loop, double-count spend, or leave `cleared`, `a_by` or `a_two` inconsistent;
- whether any existing behaviour changed for a build where the angle comes from Heimdall in time.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

