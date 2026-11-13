# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0426
# Branch: pp-selectid
# Generated: 2026-11-13 04:27 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0426/C1_STEP.diff (346 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index 24a1e721..f2e898ba 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -56,6 +56,12 @@ MIN_STATEMENT_TOKENS = 5                    # T14 story_semantics.py:372 (quote_
   6 |  HOOK_LEAD_S = sentence_law.HEAD_LEAD_MIN_S  # T12 sentence_law.py:57 (D1; G17a's hook lead; GPT-cut F12)
   7 |  CLIP_SCORER_MIN = stand_alone.CLIP_MIN_SCORE  # T8 stand_alone.py:30
   8 |  BITCOIN_TERMS = re.compile(r"\b(bitcoins?|btcs?)\b", re.I)          # T11 / G2 editorial_select.py:59
   9 | +# RULING 34 (orchestrator 03:12 ET Nov 13; the render's side merged at 55315124): the miner's about-Bitcoin screen,
  10 | +# verbatim, is the per-segment topic test of a moments package. It is sealed into every moments pin (package_pin:
  11 | +# moments_package.btc_screen), and the render's stand_alone.check_edl applies exactly the sealed pattern.
  12 | +BTC_SCREEN_SOURCE = "pp-ingest pipeline/ingest/mine.py@8e6afb61"
  13 | +BTC_SCREEN = re.compile(r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
  14 | +                        r"cold storage|microstrategy|mstr|ibit|saylor)\b", re.I)
  15 |  V2F_VIDEO_IDS = frozenset({"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"})   # S3 editorial_select.py:60
  16 |  CONTINUATION_OPENERS = frozenset(stand_alone.CONJUNCTIONS)          # T8 = editorial_select.py:127
  17 |  INTERJECTIONS = frozenset({"oh", "ah", "wow", "yeah", "yes", "right", "okay", "mhm", "hmm", "huh", "wait", "sure",
  18 | @@ -451,9 +457,11 @@ def _span(span, ctx, role):
  19 |      else:
  20 |          facts["duration_s"] = None
  21 |          R("duration", "no word timestamps: the duration is not measured")
  22 | -    # T11 subject
  23 | -    if not names_bitcoin(text):
  24 | -        R("no_bitcoin", "does not name Bitcoin (Bitcoin-only editorial line; stand_alone.topical at selection)")
  25 | +    # T11 subject. Ruling 34: the literal regex is retired. The HOOK must pass the miner's about-Bitcoin screen itself;
  26 | +    # a clip is judged per line-up (stand_alone.check_edl with the screen: the screen, or it completes the previous
  27 | +    # claim), and the medley must name Bitcoin once (check_edl's medley_names_bitcoin).
  28 | +    if role == "hook" and not BTC_SCREEN.search(text):
  29 | +        R("no_bitcoin", "the hook does not pass the miner's about-Bitcoin screen (ruling 34)")
  30 |      # T12 the hook's lead-in
  31 |      if role == "hook":
  32 |          if w0 == 0:
  33 | diff --git a/pipeline/package.py b/pipeline/package.py
  34 | index cbf43239..089cc44b 100644
  35 | --- a/pipeline/package.py
  36 | +++ b/pipeline/package.py
  37 | @@ -338,6 +338,7 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
  38 |            "bridges_after_clip": ([k] if mid else []) + ([n_clips] if t is not None else [])}
  39 |      pk = _package(segs, ctx, fields, vo_kind, vo, lines)
  40 |      pk["shape"] = "medley"
  41 | +    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}   # ruling 34: sealed (to_pin)
  42 |      pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
  43 |                                             "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
  44 |                                             "text": b["text"], "why": b.get("why"),
  45 | @@ -561,12 +562,15 @@ def stand_alone_check(segs):
  46 |      a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
  47 |      check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
  48 |      scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
  49 | -    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1)."""
  50 | +    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1).
  51 | +    RULING 34 (the render's side merged at 55315124): the topic test is the miner's about-Bitcoin screen that every
  52 | +    moments pin seals (eligibility.BTC_SCREEN, moments_package.btc_screen), and the MEDLEY must name Bitcoin in at
  53 | +    least one segment (out["medley_names_bitcoin"], part of out["ok"]): check_edl(..., screen=...), as the render."""
  54 |      import stand_alone as SA
  55 |      edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  56 |             "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  57 |                       for i, m in enumerate(segs[1:], 1)]}
  58 | -    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  59 | +    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  60 |  
  61 |  
  62 |  def ad_read_out(ms, sources):
  63 | @@ -588,6 +592,16 @@ def ad_read_out(ms, sources):
  64 |      return out
  65 |  
  66 |  
  67 | +def no_topic(m):
  68 | +    """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  69 | +    fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  70 | +    names Bitcoin (stand_alone.topical_screen as a clip: its most favourable place). build() leaves it out before any
  71 | +    vendor call."""
  72 | +    import stand_alone as SA
  73 | +    ok, why = SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)
  74 | +    return None if ok else f"the render's STAND_ALONE topic rule with the pin's screen (ruling 34): {why}"
  75 | +
  76 | +
  77 |  def no_role_on_screen(m):
  78 |      """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  79 |      opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  80 | @@ -1041,7 +1055,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  81 |      usd0 = _spent(spend)
  82 |      ms, why = usable(moments, ctx, delivered, optout)
  83 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  84 | -    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  85 | +    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m) or no_topic(m)] if r}
  86 |      ms = [m for m in ms if m["moment_id"] not in no_role]
  87 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  88 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  89 | @@ -1054,9 +1068,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  90 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  91 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  92 |             "package": None}
  93 | -    log(f"  {n_usable} usable, {len(no_role)} of them left out (they open on a conjunction or reply fragment, which "
  94 | -        f"the render's STAND_ALONE fails with no clip scorer), {len(ad_read)} on an ad-read marker (the exclusion "
  95 | -        f"screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  96 | +    log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
  97 | +        f"would have to affirm, or no place under the topic rule with the pin's screen), {len(ad_read)} on an ad-read "
  98 | +        f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  99 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 100 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 101 |          return out
 102 | @@ -1513,6 +1527,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 103 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 104 |                                      "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 105 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 106 | -                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []])}
 107 | +                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 108 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 109 |             if stand is not None else {}),
 110 |      }
 111 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 112 | index 6c15c3b0..02d1363d 100644
 113 | --- a/pipeline/package_pin.py
 114 | +++ b/pipeline/package_pin.py
 115 | @@ -69,14 +69,16 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 116 |                  "speaker")                                 # the 00:05 ET Nov 13 order, item 3
 117 |  
 118 |  
 119 | -def seal(segments, edl_vo, signoff, title, caption, gates):
 120 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 121 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 122 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 123 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
 124 |      A SEALED_LATER field enters the body only when the segment carries its key. Every pin sealed before that field
 125 |      existed then recomputes to its own package_sha256: the integrator's check recomputes seals with this module, and
 126 |      all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
 127 | -    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest."""
 128 | +    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest.
 129 | +    btc_screen (ruling 34: the miner's about-Bitcoin screen the render applies, {"pattern", "source"}) enters the body
 130 | +    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems)."""
 131 |      def body_of(s):
 132 |          b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 133 |               "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
 134 | @@ -86,9 +88,32 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 135 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
 136 |                                                               for b in edl_vo.get("bridges") or []]},
 137 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 138 | +    if btc_screen is not None:
 139 | +        body["btc_screen"] = btc_screen
 140 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 141 |  
 142 |  
 143 | +def screen_problems(pk):
 144 | +    """[why] for a moments medley that does not carry the screen its line-up was judged with (ruling 34). The render
 145 | +    reads moments_package.btc_screen and, without it, applies the stricter every-segment rule, so a pin judged with
 146 | +    the screen but sealed without it could be refused at render. A carried screen is {"pattern": a non-empty str of at
 147 | +    most 500 characters that compiles with re.I, "source": a non-empty str}: the render's own acceptance
 148 | +    (run_fresh.moments_screen)."""
 149 | +    if pk.get("shape") != "medley":
 150 | +        return []
 151 | +    sc = pk.get("btc_screen")
 152 | +    if not isinstance(sc, dict) or set(sc) != {"pattern", "source"}:
 153 | +        return ["btc_screen: a medley must carry {pattern, source} (ruling 34)"]
 154 | +    pat, src = sc.get("pattern"), sc.get("source")
 155 | +    if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 or not isinstance(src, str) or not src.strip():
 156 | +        return ["btc_screen: the pattern must be a non-empty str of at most 500 characters, with a source"]
 157 | +    try:
 158 | +        re.compile(pat, re.I)
 159 | +    except re.error as e:
 160 | +        return [f"btc_screen: the pattern does not compile ({e})"]
 161 | +    return []
 162 | +
 163 | +
 164 |  def speaker_problems(segments):
 165 |      """[why] for segments whose speaker record (speakers.attribute) is missing or malformed: the orchestrator's 00:05 ET
 166 |      Nov 13 order (item 3) has every pin carry, per segment, the speaker's name (or "unknown", never a guess) with its
 167 | @@ -161,7 +186,8 @@ def line_problems(pk):
 168 |  def to_pin(pk, run_name):
 169 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 170 |                                                                       for x in line_problems(pk)] + \
 171 | -        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or [])
 172 | +        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 173 | +        screen_problems(pk)
 174 |      if problems:
 175 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 176 |      segs = []
 177 | @@ -174,7 +200,7 @@ def to_pin(pk, run_name):
 178 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 179 |      edl_vo = {"intro": pk["vo"]["intro"],
 180 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 181 | -    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"])
 182 | +    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"))
 183 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
 184 |              "label": "bitcoin", "headline": pk["title"],
 185 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
 186 | @@ -195,6 +221,7 @@ def to_pin(pk, run_name):
 187 |                                  "supply_exception": pk.get("supply_exception"),
 188 |                                  "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
 189 |                                  "gates": pk["gates"],
 190 | +                                **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 191 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 192 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
 193 |                                             "models": pk.get("models")},
 194 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 195 | index 168a1cc3..fadf036c 100644
 196 | --- a/pipeline/stand_alone.py
 197 | +++ b/pipeline/stand_alone.py
 198 | @@ -96,9 +96,28 @@ def topical(kind, text, prev_text=None, subject=("bitcoin", "btc")):
 199 |                     f"previous segment's claim (it opens on {first!r}): context, not a clip")
 200 |  
 201 |  
 202 | -def check_edl(edl, rate=None, subject=("bitcoin", "btc")):
 203 | +def topical_screen(kind, text, prev_text, screen):
 204 | +    """Ruling 34 (orchestrator 2026-11-13 '03:42'), moments packages only: a segment is about Bitcoin when the miner's
 205 | +    about-Bitcoin screen (BTC_SCREEN, carried on the pin) matches its own words, or (a clip only) it completes the
 206 | +    previous segment's claim exactly as topical() allows. The medley-level rule (one segment names Bitcoin) is
 207 | +    check_edl's."""
 208 | +    m = screen.search(text or "")
 209 | +    if m:
 210 | +        return True, f"about Bitcoin by the miner's screen ({m.group(0)!r})"
 211 | +    if kind == "hook":
 212 | +        return False, "the hook does not pass the miner's about-Bitcoin screen"
 213 | +    ok, why = topical(kind, text, prev_text, ("bitcoin", "btc"))
 214 | +    if ok:
 215 | +        return ok, why
 216 | +    return False, f"does not pass the miner's about-Bitcoin screen and does not complete the previous claim"
 217 | +
 218 | +
 219 | +def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 220 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 221 | -    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed."""
 222 | +    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed.
 223 | +    screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 224 | +    and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 225 | +    speaker's own words. screen None: every segment names the subject, as before (the story path)."""
 226 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 227 |      need = [(label, s) for label, kind, s in segs if kind == "clip" and _words(s.get("text"))[:1]
 228 |              and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)]
 229 | @@ -114,10 +133,19 @@ def check_edl(edl, rate=None, subject=("bitcoin", "btc")):
 230 |          sc = scores.get(label)
 231 |          score, fault = (sc[0], sc[2]) if sc else (None, None)
 232 |          o_ok, o_why = opener(kind, s.get("text"), score, fault)
 233 | -        t_ok, t_why = topical(kind, s.get("text"), prev, subject)
 234 | +        t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
 235 | +            topical(kind, s.get("text"), prev, subject)
 236 |          rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
 237 |                       "opener": {"pass": o_ok, "why": o_why}, "topic": {"pass": t_ok, "why": t_why},
 238 |                       **({"scorer": {"score": sc[0], "reason": sc[1], "fault": sc[2]}} if sc else {}),
 239 |                       "pass": o_ok and t_ok})
 240 |          prev = s.get("text")
 241 | -    return {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
 242 | +    out = {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
 243 | +    if screen is not None:                                   # ruling 34: the MEDLEY names Bitcoin, once at least
 244 | +        named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]
 245 | +        out["medley_names_bitcoin"] = {"pass": bool(named), "segments": named,
 246 | +                                       "why": f"named by {', '.join(named)}" if named else
 247 | +                                       "no segment names Bitcoin in the speaker's own words (ruling 34)"}
 248 | +        out["screen"] = screen.pattern
 249 | +        out["ok"] = out["ok"] and bool(named)
 250 | +    return out
 251 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 252 | index 46c20050..afffc2c0 100644
 253 | --- a/tests/eligibility/test_eligibility.py
 254 | +++ b/tests/eligibility/test_eligibility.py
 255 | @@ -252,6 +252,20 @@ class TestSpan(unittest.TestCase):
 256 |          self.assertNotIn("opener", r.names(), r.why())
 257 |          self.assertTrue(any("'and so'" in t for t in r.facts["targets_missed"]), r.facts)
 258 |  
 259 | +    def test_the_screen_is_the_miners_verbatim(self):                  # ruling 34: sealed as its source names it
 260 | +        import subprocess
 261 | +        path, commit = E.BTC_SCREEN_SOURCE.split()[-1].split("@")     # 'pipeline/ingest/mine.py', '8e6afb61'
 262 | +        r = subprocess.run(["git", "--no-optional-locks", "-C", "/home/ultron/worktrees/pp-ingest", "show",
 263 | +                            f"{commit}:{path}"], capture_output=True, text=True)
 264 | +        if r.returncode != 0:
 265 | +            self.skipTest("pp-ingest's history is not readable here")
 266 | +        import re as _re
 267 | +        m = _re.search(r'BTC_SCREEN = re.compile\(r"(.*?)"\s*\n\s*r"(.*?)", re.I\)', r.stdout)
 268 | +        self.assertIsNotNone(m)
 269 | +        self.assertEqual(E.BTC_SCREEN.pattern, m.group(1) + m.group(2))
 270 | +        self.assertEqual(E.BTC_SCREEN_SOURCE, "pp-ingest pipeline/ingest/mine.py@8e6afb61")
 271 | +        self.assertTrue(E.BTC_SCREEN.flags & _re.I)
 272 | +
 273 |      def test_duration_count_subject_lead(self):
 274 |          short = self.hook(["Bitcoin fell five percent overnight on the open."])
 275 |          self.assertNotIn("duration", short.names())                                              # law L-o: a target
 276 | @@ -267,6 +281,10 @@ class TestSpan(unittest.TestCase):
 277 |          alt = self.hook(["Solana rallied twenty percent this week after the exchange listing news broke on "
 278 |                           "Monday morning, leading every large cap token higher into the weekend close."])
 279 |          self.assertIn("no_bitcoin", alt.names())                                                 # an altcoin sentence
 280 | +        sats = self.hook(["Michael Saylor just bought another twenty thousand coins for the treasury this week."])
 281 | +        self.assertNotIn("no_bitcoin", sats.names())              # ruling 34: the miner's screen ('saylor'), the hook
 282 | +        src = source(["Gold has been the premier monetary asset for most of human history, people say."])
 283 | +        self.assertNotIn("no_bitcoin", E.eligible(E.Span(src, 0, 0), ctx("clip")).names())   # a clip: per line-up
 284 |          tight = source(["Prices were calm overnight in Asia.", HOOK_TXT], pause=0.0)    # 40 ms between words only
 285 |          sp = E.Span(tight, 1, 1)
 286 |          self.assertIn("hook_lead", E.eligible(sp, ctx("hook", story=statements(sp))).names())   # 40 ms gap (G17a)
 287 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 288 | index 30f6c0dc..1524084d 100644
 289 | --- a/tests/package/test_medley.py
 290 | +++ b/tests/package/test_medley.py
 291 | @@ -725,6 +725,54 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 292 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 293 |  
 294 |  
 295 | +class TestRuling34Screen(unittest.TestCase):
 296 | +    """Ruling 34 (render side merged at 55315124): the topic test is the miner's about-Bitcoin screen the pin seals;
 297 | +    the hook must pass it itself, a clip may complete the previous claim, and the MEDLEY must name Bitcoin once."""
 298 | +
 299 | +    def check(self, *texts):
 300 | +        return PK.stand_alone_check([{"text": t} for t in texts])
 301 | +
 302 | +    def test_the_screen_is_the_topic_and_the_medley_must_name_bitcoin(self):
 303 | +        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying.", "Sats are the unit.")
 304 | +        self.assertEqual([x["topic"]["pass"] for x in r["rows"]], [True, True, True])      # the screen, each one
 305 | +        self.assertFalse(r["medley_names_bitcoin"]["pass"])                                  # but no "Bitcoin"
 306 | +        self.assertFalse(r["ok"])
 307 | +        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying Bitcoin.",
 308 | +                       "That was 25 % of the float.")                                       # completes the claim
 309 | +        self.assertTrue(r["ok"], r["rows"])
 310 | +        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["clip_01"])
 311 | +        self.assertEqual(r["screen"], E.BTC_SCREEN.pattern)
 312 | +        r = self.check("Gold is the oldest money.", "Bitcoin is the newest.", "Bitcoin wins.")
 313 | +        self.assertFalse(r["ok"])                                                            # the hook must pass
 314 | +        self.assertIn("the hook does not pass the miner's about-Bitcoin screen", r["rows"][0]["topic"]["why"])
 315 | +
 316 | +    def test_a_moment_with_no_place_under_the_topic_rule_is_left_out(self):
 317 | +        self.assertIn("ruling 34", PK.no_topic({"text": "Gold is the oldest money."}))
 318 | +        for t in ("Saylor keeps buying.", "That was 25 % of the float.", "Bitcoin is money."):
 319 | +            self.assertIsNone(PK.no_topic({"text": t}), t)
 320 | +
 321 | +    def test_every_medley_seals_the_screen_and_the_recompute_needs_it(self):
 322 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0))}
 323 | +        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 324 | +                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
 325 | +                  "caption": {"text": "three clips", "cites": []}}
 326 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 327 | +        self.assertEqual(pk["btc_screen"], {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE})
 328 | +        pk["gates"] = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1}
 329 | +                       for k in package_pin.required_gates(pk)}
 330 | +        pin = package_pin.to_pin(spk(pk), "test")
 331 | +        mp = pin["moments_package"]
 332 | +        self.assertEqual(mp["btc_screen"], pk["btc_screen"])
 333 | +        args = (pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"])
 334 | +        self.assertEqual(package_pin.seal(*args, mp.get("btc_screen")), mp["package_sha256"])   # check_pin_only's
 335 | +        self.assertNotEqual(package_pin.seal(*args), mp["package_sha256"])                      # 7-argument call
 336 | +        for bad in (None, {"pattern": "", "source": "s"}, {"pattern": "(", "source": "s"},
 337 | +                    {"pattern": "x" * 501, "source": "s"}, {"pattern": "bitcoin"}):
 338 | +            p = dict(spk(pk), btc_screen=bad)
 339 | +            with self.assertRaises(package_pin.PinRefused):
 340 | +                package_pin.to_pin(p, "test")
 341 | +
 342 | +
 343 |  class TestAdReadBeforeTheAngle(unittest.TestCase):
 344 |      """The exclusion screen's deterministic part (moments.ad_read_marker) runs before step A, so no angle is built
 345 |      around a moment the package stage would refuse. The 03:39 build lost its line-up's hook to it after the write."""
 346 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
"pins"; another session (the integrator) renders them with the main pipeline. The pin stage must never seal a line-up
the render's own checks would refuse.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 34 (03:12 ET Nov 13): "no_bitcoin: the literal regex is retired for clips. The miner's
about-Bitcoin screen is the per-clip test. The MEDLEY must name Bitcoin: at least one clip or the hook says it in the
speaker's own words." The integrator merged the render side (main 55315124) with this contract:
- The pin seals moments_package.btc_screen = {"pattern": <regex str of at most 500 characters, compiled with re.I by
  the render>, "source": <file@commit>} inside the sealed package (so it is in moments_package_sha256).
- The render's stand_alone.check_edl(edl, screen=<compiled pattern>) checks each segment's TOPIC with the screen: the
  screen matches the segment's words, or (a clip only) the segment completes the previous claim (topical()'s old
  rule). The HOOK must match the screen itself.
- The MEDLEY must name Bitcoin: the hook or one clip says bitcoin / btc in its own words (out["medley_names_bitcoin"],
  part of out["ok"]).
- If btc_screen is absent or malformed, the render applies the old strict rule (every segment names Bitcoin).
- The integrator's recompute (check_pin_only) now calls seal(..., mp.get("btc_screen")) as a 7th argument.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. The relaxation here is the orchestrator's own
  ruling and the render's merged code; check that the pin stage does exactly that and no more.

The change:
1. pipeline/stand_alone.py: synced BYTE-IDENTICAL to main's at 55315124 (the render's own topical_screen() and
   check_edl(screen=...)). Passing no screen keeps the old behaviour.
2. pipeline/eligibility.py:
   - BTC_SCREEN: the miner's screen verbatim (pp-ingest pipeline/ingest/mine.py@8e6afb61, 131 characters), compiled
     with re.I, plus BTC_SCREEN_SOURCE;
   - T11: the HOOK role needs BTC_SCREEN, not the literal regex; the CLIP role has no per-moment topic flag (a clip
     may complete the previous claim, decided per line-up).
3. pipeline/package.py:
   - stand_alone_check passes screen=E.BTC_SCREEN, so the line-up filter and the sealed "stand_alone" row require the
     screen topic AND medley_names_bitcoin (out["ok"]);
   - no_topic(m): a moment that fails topical_screen as a clip right after a segment naming Bitcoin (its most
     favourable place) can take no place, and build() leaves it out with the opener rule before any vendor call;
   - assemble_medley sets pk["btc_screen"] = {pattern, source};
   - the inventory row records medley_names_bitcoin and the screen.
4. pipeline/package_pin.py:
   - seal(..., btc_screen=None): the screen enters the sealed body only when given, so every earlier pin recomputes;
   - to_pin seals pk["btc_screen"] and writes moments_package.btc_screen;
   - screen_problems refuses a MEDLEY without a valid {pattern, source}: a non-empty str of at most 500 characters
     that compiles with re.I, and a source. That is the render's own acceptance.
5. Tests:
   - the screen as topic, and the medley rule;
   - the hook must pass the screen; a clip may complete the previous claim;
   - no_topic;
   - every medley seals the screen, and the 7-argument recompute equals while the 6-argument one does not;
   - a missing or malformed screen refuses the pin;
   - the eligibility hook rule;
   - a mirror test of the pattern against the miner's file at the sealed commit.

Check in particular:
- that the pin stage's check is the render's, with the same compiled screen, the same medley rule and the same
  hook-must-match rule, and cannot PASS a line-up the render would refuse;
- that the sealed screen is exactly the one the line-up was judged with;
- that old pins still recompute;
- that no_topic drops ONLY moments that can take no place under the render's rule;
- that the story path (no screen) is unchanged.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

