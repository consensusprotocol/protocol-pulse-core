# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1207
# Branch: pp-selectid
# Generated: 2026-11-13 12:08 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1207/C1_STEP.diff (770 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 278b93a..ad2b892 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -576,8 +576,9 @@ THE HOOKS: a video may OPEN only on one of these clips; each was judged first, a
   6 |  4-5 of 5), best first:
   7 |  {hooks}
   8 |  
   9 | -Find ANGLES, best hook first: up to {per} for EACH hook above, at most {k} in all, each written FOR its hook (it opens
  10 | -the video and sets up the point). An angle is ONE sentence a viewer could repeat: a point that several of these clips
  11 | +Find ANGLES, best hook first: for EACH hook above at least one and at most {per} (every hook gets its own), at most
  12 | +{k} in all, each written FOR its hook (it opens the video and sets up the point). An angle is ONE sentence a viewer
  13 | +could repeat: a point that several of these clips
  14 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
  15 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
  16 |  it is today's.
  17 | @@ -602,21 +603,22 @@ HOOK_QUESTION = """THE HOOK is judged on its own job, NOT on the through-line. R
  18 |  
  19 |  MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
  20 |  Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
  21 | -opens the video.
  22 | +opens the video. The hook is shown for context only: it is NOT rated here (its own job was judged on its own).
  23 |  
  24 |  {clips}
  25 |  
  26 |  1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
  27 |     "none" if there is none.
  28 | -2) """ + HOOK_QUESTION + """
  29 | -3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  30 | -4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  31 | -   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
  32 | -   words.
  33 | -Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  34 | -"clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
  35 | +2) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  36 | +3) For each JOIN between two consecutive clips, the hook's own join included (does the hook set up the clip after
  37 | +   it?): could a viewer follow the jump with no narration, i.e. is the next clip's subject or referent clear coming
  38 | +   from the previous clip's ending? Answer true or false, and why in a few words.
  39 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
  40 |  HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
  41 |  HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
  42 | +HOOK_OWN = ("scroll", "alone")     # RULING 61 (12:00): the hook's OWN-JOB rating, cached and never re-asked per line-up
  43 | +HOOK_OWN_RULE = ("the lowest of scroll / alone, cached (ruling 61); 'sets up what follows' is judged at the hook -> "
  44 | +                 "clip_01 join")
  45 |  HOOKS_PROMPT = """You judge OPENING clips for 60-second videos made of other channels' own words (each clip is a person's
  46 |  own words from a show). Each candidate below would play FIRST, before anything else is said. Judge each one ALONE, as
  47 |  the opener of a video; the candidates are not compared with each other and never play together.
  48 | @@ -644,8 +646,9 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  49 |      for m in ms:
  50 |          rec = next((x for name, x in sorted((cdb.get(key(m)) or {}).items())
  51 |                      if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
  52 | -        if rec is not None:
  53 | -            out[m["moment_id"]] = dict(rec, cached=True)
  54 | +        if rec is not None and all(isinstance(rec.get(k), int) for k in HOOK_PARTS):
  55 | +            out[m["moment_id"]] = dict(rec, rating=min(rec[k] for k in HOOK_OWN), rule=HOOK_OWN_RULE,
  56 | +                                       cached=True)          # ruling 61: the own-job rating is scroll / alone
  57 |          else:
  58 |              todo.append(m)
  59 |      if not todo:
  60 | @@ -676,8 +679,8 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  61 |          new = {}
  62 |          for m in todo:
  63 |              x = h[m["moment_id"]]
  64 | -            rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_PARTS), "why": x["why"][:300],
  65 | -                   "backend": r.backend, "rule": HOOK_RULE}
  66 | +            rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
  67 | +                   "backend": r.backend, "rule": HOOK_OWN_RULE}       # ruling 61: scroll / alone
  68 |              out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
  69 |              new[key(m)] = {r.backend: rec}
  70 |          _cache_put(cache, new)
  71 | @@ -723,17 +726,16 @@ picked).
  72 |  """
  73 |  
  74 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
  75 | -different person's own words; the first clip, label "hook", opens the video).
  76 | +different person's own words; the first clip, label "hook", opens the video and is shown for context only: it is NOT
  77 | +rated here, its own job was judged on its own).
  78 |  
  79 |  {package}
  80 |  
  81 |  1) State the video's through-line in ONE sentence, or "none" if it has none.
  82 | -2) """ + HOOK_QUESTION + """
  83 | -3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  84 | -4) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  85 | +2) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  86 | +3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  87 |     1 = no point, or a point the clips do not support).
  88 | -Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  89 | -"clips": {{{clip_keys}}}, "vo_point": 1}}"""
  90 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "vo_point": 1}}"""
  91 |  
  92 |  
  93 |  def current_levels(sources, ctx, hours=24.0):
  94 | @@ -1136,6 +1138,18 @@ def no_role_on_screen(m):
  95 |                                          "with no clip scorer at the pin stage") + f": {c_why}; {h_why}")
  96 |  
  97 |  
  98 | +def hook_own(m):
  99 | +    """RULING 61 (12:00): a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
 100 | +    "alone", "rating": the lower of the two, "source", "rule"}. 'Sets up what follows' is not part of it: it is judged
 101 | +    at the hook -> clip_01 join. None when the moment carries no complete rating (then it never opens, law L-m)."""
 102 | +    r = (m or {}).get("hook_rating") or {}
 103 | +    parts = {k: r.get(k) for k in HOOK_OWN}
 104 | +    if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
 105 | +        return None
 106 | +    return dict(parts, rating=min(parts.values()), source="the hook's cached own-job rating (ruling 61)",
 107 | +                rule=HOOK_OWN_RULE)
 108 | +
 109 | +
 110 |  def can_open(m):
 111 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
 112 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
 113 | @@ -1145,16 +1159,18 @@ def can_open(m):
 114 |      if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True
 115 |              and SA.opener("hook", m.get("text") or "")[0]):
 116 |          return False
 117 | -    r = (m.get("hook_rating") or {}).get("rating") if "hook_rating" in m else HOOK_MIN
 118 | -    return isinstance(r, int) and not isinstance(r, bool) and r >= HOOK_MIN
 119 | +    if "hook_rating" not in m:
 120 | +        return True                                      # not rated yet: judged as before ruling 59
 121 | +    own = hook_own(m)                                    # ruling 61: scroll / alone, the cached own-job rating
 122 | +    return own is not None and own["rating"] >= HOOK_MIN
 123 |  
 124 |  
 125 |  def hook_order(ms):
 126 |      """RULING 59 (c): the passing hooks best first: the derived rating, then the sum of its parts, then the miner's
 127 |      score, then the id (a total order)."""
 128 |      hr = lambda m: m.get("hook_rating") or {}
 129 | -    return sorted(ms, key=lambda m: (-(hr(m).get("rating") or 0), -sum(hr(m).get(k) or 0 for k in HOOK_PARTS),
 130 | -                                     -m["rank_score"], m["moment_id"]))
 131 | +    return sorted(ms, key=lambda m: (-((hook_own(m) or {}).get("rating") or 0),   # ruling 61: the own-job rating
 132 | +                                     -sum(hr(m).get(k) or 0 for k in HOOK_PARTS), -m["rank_score"], m["moment_id"]))
 133 |  
 134 |  
 135 |  def hook_line(m, ctx):
 136 | @@ -1368,23 +1384,28 @@ def duplicates(pk):
 137 |  NO_LINE = re.compile(r"^\W*(none|no\b|n/?a\b|unclear|nothing|there is no)", re.I)
 138 |  
 139 |  
 140 | -def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 141 | +def _line_ok(tl):
 142 | +    """A through-line is stated: a string of >= 4 words that does not read 'none' / 'no' / 'n/a' (M7)."""
 143 | +    tl = tl if isinstance(tl, str) else ""
 144 | +    return bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4
 145 | +
 146 | +
 147 | +def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 148 |      """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
 149 |      (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
 150 | -    Ruling 52, as the orchestrator answered at 09:59 Nov 13: the HOOK is rated on its own job here too (HOOK_QUESTION,
 151 | -    the same three parts as the clips-alone verdict), and its rating is DERIVED as the lowest part (HOOK_RULE), written
 152 | -    to verdict["clips"]["hook"]; the clips after the hook and vo_point are rated as before."""
 153 | +    RULING 61 (12:00): the hook is NOT rated here either. Its cached own-job rating (hook_own of the hook moment
 154 | +    `hook`) is written to verdict["clips"]["hook"]; without one the verdict fails closed (law L-m). The clips after the
 155 | +    hook and vo_point are rated as before; the judge sees the hook's text for context."""
 156 |      import providers as P
 157 |      r = None
 158 |      labs = [sg["label"] for sg in pk["segments"]]
 159 | +    own = hook_own(hook)
 160 |      try:
 161 |          r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
 162 |                              package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 163 |                          1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 164 |          v = json.loads(r.text.strip())
 165 | -        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "vo_point"} or \
 166 | -                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
 167 | -                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
 168 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 169 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 170 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 171 |              raise ValueError("coherence verdict out of contract")
 172 | @@ -1392,9 +1413,10 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 173 |          if r is not None and isinstance(e, (ValueError, TypeError)):
 174 |              router.reject(r)
 175 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
 176 | -    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
 177 | -    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 178 | -    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 179 | +    v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 180 | +             hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 181 | +                                                     "fail closed"})
 182 | +    ok = own is not None and _line_ok(v["through_line"]) and \
 183 |          min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
 184 |      return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 185 |  
 186 | @@ -1418,16 +1440,18 @@ def joins(labs):
 187 |  def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 188 |      """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
 189 |      no narration, is there a through-line a viewer can state?", a 1-5 rating per clip after the hook on how much it
 190 | -    advances it, and per join whether a viewer can follow the jump. RULING 52: the HOOK is rated on its own job, in
 191 | -    three parts the judge answers separately (HOOK_PARTS: stops a scroll in its first 2-3 s, stands alone, sets up
 192 | -    what follows), and its rating is DERIVED, never free-form: the lowest part (HOOK_RULE), written to
 193 | -    verdict["clips"]["hook"]; the parts stay in verdict["hook"]. Never the vendor / family of the writer. -> (ok,
 194 | -    verdict): ok when the through-line is stated (>= 4 words, not 'none'), every rating (the hook's derived one
 195 | -    included) is >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable; verdict["flagged"] = the joins
 196 | -    a viewer could not follow (a bridge may go only there, L-y 2)."""
 197 | +    advances it, and per join whether a viewer can follow the jump. RULING 61 (12:00): THE HOOK IS RATED ONCE. Its
 198 | +    own-job rating ('stops the scroll', 'stands alone': hook_own) is the cached one ruling 59 gave it, never re-asked
 199 | +    here; the judge sees the hook's text for context only. 'Sets up what follows' is judged where it is measurable: the
 200 | +    hook -> clip_01 join (followable, or the one bridge L-y allows). The cached rating is written to
 201 | +    verdict["clips"]["hook"] (the record and the bar read one dict); a hook without one fails closed (law L-m). Never
 202 | +    the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated (>= 4 words, not 'none'),
 203 | +    every rating (the hook's cached one included) is >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not
 204 | +    followable; verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
 205 |      import providers as P
 206 |      labs = labels(len(segs))
 207 |      js = joins(labs)
 208 | +    own = hook_own(segs[0]) if segs else None
 209 |      clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 210 |                        for lb, m in zip(labs, segs))
 211 |      r = None
 212 | @@ -1437,9 +1461,7 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 213 |                                               joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 214 |                          1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 215 |          v = json.loads(r.text.strip())
 216 | -        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "joins"} or \
 217 | -                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
 218 | -                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
 219 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 220 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 221 |                  any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 222 |                  not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
 223 | @@ -1450,15 +1472,60 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 224 |          if r is not None and isinstance(e, (ValueError, TypeError)):
 225 |              router.reject(r)
 226 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 227 | -    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
 228 | -    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 229 | +    v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 230 | +             hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 231 | +                                                     "fail closed"})
 232 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
 233 | -    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 234 | -        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 235 | +    ok = own is not None and _line_ok(v["through_line"]) and min(v["clips"].values()) >= COHERENCE_MIN and \
 236 | +        len(flagged) <= LY_MAX_BRIDGES
 237 |      return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 238 |                      replayed=bool(getattr(r, "replayed", False)))
 239 |  
 240 |  
 241 | +def last_clip_only(segs, med):
 242 | +    """RULING 62 (12:00): whether a clips-alone failure is its LAST clip's alone: measured, the through-line stated,
 243 | +    every other rating (the hook's cached one included) >= COHERENCE_MIN, the last clip's under it, and no more than
 244 | +    LY_MAX_BRIDGES flagged joins once the join into the last clip goes with it."""
 245 | +    labs = labels(len(segs))
 246 | +    cl = med.get("clips") or {}
 247 | +    if not med.get("measured") or not _line_ok(med.get("through_line")) or labs[-1] not in cl or labs[0] not in cl:
 248 | +        return False
 249 | +    rest = [j for j in med.get("flagged") or [] if j != joins(labs)[-1]]
 250 | +    return [lb for lb, x in cl.items() if x < COHERENCE_MIN] == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 251 | +
 252 | +
 253 | +def reorder(segs, bad_pairs, judged, repeat_ok=False):
 254 | +    """RULING 63 (12:00): JOINS BEFORE SWAPS. The next ORDER of the same clips, the hook first, for a line-up whose
 255 | +    ratings all pass but whose flagged joins exceed the one bridge L-y allows. A flagged join is about adjacency:
 256 | +    `bad_pairs` holds every (from, to) moment pair a verdict in this build found unfollowable. Candidates: every
 257 | +    permutation of the clips after the hook not judged yet (`judged`: moment-id tuples), with at most LY_MAX_BRIDGES
 258 | +    known-unfollowable adjacent pairs, under every line-up rule (lineup_ok: the placement limits, the seconds, the
 259 | +    render's STAND_ALONE in the new order). Best: the fewest such pairs, then the fewest clips moved. No step A is
 260 | +    asked again (the same clips). -> the new line-up, or None."""
 261 | +    h, clips = segs[0], list(segs[1:])
 262 | +    best = None
 263 | +    for perm in itertools.permutations(clips):
 264 | +        new = [h, *perm]
 265 | +        ids = tuple(m["moment_id"] for m in new)
 266 | +        n_bad = sum((a, b) in bad_pairs for a, b in zip(ids, ids[1:]))
 267 | +        if ids in judged or n_bad > LY_MAX_BRIDGES:
 268 | +            continue
 269 | +        key = (n_bad, sum(x is not y for x, y in zip(perm, clips)))
 270 | +        if (best is None or key < best[0]) and lineup_ok(new, repeat_ok=repeat_ok)[0]:
 271 | +            best = (key, new)
 272 | +    return best[1] if best else None
 273 | +
 274 | +
 275 | +def allot(angles, per):
 276 | +    """RULING 64 (12:00): at most `per` angles per hook, in the writer's order (the excess is dropped, recorded)."""
 277 | +    seen, out = {}, []
 278 | +    for a in angles:
 279 | +        seen[a["hook"]] = seen.get(a["hook"], 0) + 1
 280 | +        if seen[a["hook"]] <= per:
 281 | +            out.append(a)
 282 | +    return out
 283 | +
 284 | +
 285 |  class NoBridgeFits(ValueError):
 286 |      """These clips leave no takeaway length (and, for a flagged join, no bridge length) that lands 60-70 s."""
 287 |  
 288 | @@ -1888,20 +1955,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 289 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s{placement(m)} | '
 290 |                        f'"{quote_data(m["text"], 600)}"'
 291 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 292 | -    hooks_txt = "\n".join(f'id={m["moment_id"]} | rated {m["hook_rating"]["rating"]} on its own job: '
 293 | -                          f'"{quote_data(m["hook_rating"].get("why") or "", 200)}"' for m in passing)
 294 | -    per = max(1, max_angles // len(passing))
 295 | +    offered = passing[:max_angles]                      # RULING 64: an angle for each passing hook (k at most)
 296 | +    hooks_txt = lambda hs: "\n".join(f'id={m["moment_id"]} | rated {hook_own(m)["rating"]} on its own job: '
 297 | +                                     f'"{quote_data(m["hook_rating"].get("why") or "", 200)}"' for m in hs)
 298 | +    per = max(1, max_angles // len(offered))
 299 |      lo, hi = medley_content_range()
 300 |      angles, angle_reply, errs = None, None, []
 301 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 302 |          r = None
 303 |          try:
 304 |              r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 305 | -                                                               clips=clips, hooks=hooks_txt, per=per, k=max_angles,
 306 | -                                                               lo=lo, hi=hi), 3000, seed,
 307 | +                                                               clips=clips, hooks=hooks_txt(offered), per=per,
 308 | +                                                               k=max_angles, lo=lo, hi=hi), 3000, seed,
 309 |                              deadline_s=WRITER_DEADLINE_S)
 310 | -            angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles,
 311 | -                                               hooks={m["moment_id"] for m in passing}), r   # ruling 59 (c)
 312 | +            got = check_angles(json.loads(r.text.strip()), cleared, max_angles,
 313 | +                               hooks={m["moment_id"] for m in offered})                  # ruling 59 (c)
 314 | +            angles, angle_reply = allot(got, per), r            # ruling 64: at most `per` per hook
 315 | +            if len(angles) < len(got):
 316 | +                out["angle_allotment"] = {"dropped": [a["angle"] for a in got if a not in angles], "per": per}
 317 |              break
 318 |          except Exception as e:
 319 |              if r is not None:
 320 | @@ -1911,10 +1982,28 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 321 |      if not angles:
 322 |          return out
 323 |      out.pop("why_none", None)
 324 | +    missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}]
 325 | +    if missing and len(angles) < max_angles:            # RULING 64: a passing hook left without an angle is asked
 326 | +        k2, r = max_angles - len(angles), None          # for, once, written for exactly those hooks (12:00)
 327 | +        try:
 328 | +            r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 329 | +                                                               clips=clips, hooks=hooks_txt(missing),
 330 | +                                                               per=max(1, k2 // len(missing)), k=k2, lo=lo, hi=hi),
 331 | +                            3000, 9, deadline_s=WRITER_DEADLINE_S)
 332 | +            more = allot(check_angles(json.loads(r.text.strip()), cleared, k2,
 333 | +                                      hooks={m["moment_id"] for m in missing}), max(1, k2 // len(missing)))
 334 | +            angles = angles + more
 335 | +            out["angle_follow_up"] = {"hooks": [m["moment_id"] for m in missing], "angles": len(more),
 336 | +                                      "backend": r.backend}
 337 | +        except Exception as e:                          # never the build: the hooks that have angles go on
 338 | +            if r is not None:
 339 | +                router.reject(r)
 340 | +            out["angle_follow_up"] = {"hooks": [m["moment_id"] for m in missing],
 341 | +                                      "error": f"{type(e).__name__}: {str(e)[:200]}"}
 342 |      def first_fresh(a):                                   # ruling 57: the angles whose first line-up holds a clip
 343 |          segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now, hook_only=True)  # <= FRESH_H
 344 |          return bool(segs) and fresh_key(segs, ctx.now)[0]                                              # old go first
 345 | -    hrank = {m["moment_id"]: (-m["hook_rating"]["rating"], -sum(m["hook_rating"][k] for k in HOOK_PARTS))
 346 | +    hrank = {m["moment_id"]: (-hook_own(m)["rating"], -sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS))
 347 |               for m in passing}                            # ruling 59 (c): the best hook first, then ruling 57's
 348 |      angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))   # freshness; stable: the writer's
 349 |      # order within each
 350 | @@ -2057,6 +2146,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 351 |          return pk
 352 |  
 353 |      total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 354 | +    judged, bad_pairs, spins = {}, set(), 0               # 12:00: verdicts by line-up; ruling 63's unfollowable pairs
 355 |      with ThreadPoolExecutor(max_workers=8) as pool:
 356 |          for ai, angle in enumerate(angles):
 357 |              dropped, n_lineup, swapped = set(), 0, None
 358 | @@ -2088,25 +2178,55 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 359 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 360 |                      break
 361 |                  n_lineup += 1
 362 | -                total += 1
 363 | +                spins += 1
 364 | +                if spins > 4 * lineups:                   # a guard: free (cached) line-ups never turn forever
 365 | +                    rec["why"] = "the search kept meeting line-ups already judged: stopped"
 366 | +                    break
 367 |                  line = (time.time(), _spent(spend))         # this line-up's package budget counts from here (ruling 41)
 368 | -                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 369 | +                key = tuple(m["moment_id"] for m in segs)
 370 | +                if key in judged:                           # 12:00: an identical line-up's verdict again, free
 371 | +                    ok_m, med = judged[key]
 372 | +                    rec["verdict_again"] = True
 373 | +                else:
 374 | +                    ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai,
 375 | +                                       writer_family=writers_f)
 376 | +                    judged[key] = (ok_m, med)
 377 | +                    total += 0 if med.get("replayed") else 1    # 12:00: the budget counts JUDGED line-ups
 378 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 379 | +                labs_ = labels(len(segs))
 380 | +                bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
 381 | +                              for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}   # ruling 63
 382 |                  log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 383 |                      f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 384 |                      f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 385 |                  labs = labels(len(segs))
 386 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 387 |                      by_lab = dict(zip(labs, segs))
 388 | -                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 389 | -                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 41: the HOOK too (the next hook)
 390 | +                    cl = med.get("clips") or {}
 391 | +                    if last_clip_only(segs, med) and len(segs) - 1 > LY_CLIPS[0] and \
 392 | +                            lineup_ok(segs[:-1], repeat_ok=exception is not None)[0]:   # RULING 62: the last clip
 393 | +                        dropped.add(segs[-1]["moment_id"])
 394 | +                        swapped = segs[:-1]
 395 | +                        rec["why"] = (f"ruling 62: only the last clip fails ({cl.get(labs[-1])}): retried without it, "
 396 | +                                      f"the seconds floor still met, before any swap")
 397 | +                        continue
 398 | +                    if med.get("measured") and _line_ok(med.get("through_line")) and labs[0] in cl and \
 399 | +                            min(cl.values()) >= COHERENCE_MIN and len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 400 | +                        order = reorder(segs, bad_pairs, judged, repeat_ok=exception is not None)
 401 | +                        if order is not None:                 # RULING 63: joins before swaps
 402 | +                            swapped = order
 403 | +                            rec["why"] = (f"ruling 63: every rating passes and {len(med['flagged'])} joins are "
 404 | +                                          f"flagged: the same clips reordered, before any swap")
 405 | +                            continue
 406 | +                    weak = {by_lab[lb]["moment_id"] for lb, x in cl.items()
 407 | +                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 61: the hook's is its cached rating
 408 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 409 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 410 |                      hook_weak = segs[0]["moment_id"] in weak
 411 |                      weak.discard(segs[0]["moment_id"])    # ruling 59 (c): the line-up is built AROUND its hook
 412 |                      if not med.get("measured") or not weak:
 413 | -                        rec["why"] = ("the hook rates below the bar in this line-up and no clip after it does; the angle "
 414 | -                                      "is written for this hook (ruling 59 c)" if med.get("measured") and hook_weak else
 415 | +                        rec["why"] = ("the hook carries no own-job rating at the bar (ruling 61); the angle is written "
 416 | +                                      "for this hook (ruling 59 c)" if med.get("measured") and hook_weak else
 417 |                                        "the clips alone have no through-line a viewer can state (or it was not measured)")
 418 |                          break
 419 |                      dropped |= weak
 420 | @@ -2251,7 +2371,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 421 |                          continue
 422 |                      att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 423 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 424 | -                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
 425 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f,
 426 | +                                          hook=segs[0])     # then on the takeaway; ruling 61: the hook's cached
 427 |                      att["coherence"] = coh
 428 |                      log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 429 |                          f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 430 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 431 | index 1d76c65..c574b24 100644
 432 | --- a/tests/package/test_medley.py
 433 | +++ b/tests/package/test_medley.py
 434 | @@ -45,12 +45,10 @@ def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of
 435 |                            if j in flagged else "same subject"} for j in js}}
 436 |  
 437 |  
 438 | -def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin.", hook=None):
 439 | -    """The clips-alone JUDGE's raw reply (ruling 52): the hook's three parts, the clips after the hook, the joins."""
 440 | +def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
 441 | +    """The clips-alone JUDGE's raw reply (ruling 61): the clips after the hook and the joins; the hook is not rated."""
 442 |      js = PK.joins(labs)
 443 | -    h = (ratings or {}).get("hook", 5)
 444 | -    return {"through_line": line, "hook": dict({"scroll": h, "alone": h, "setup": h}, **(hook or {})),
 445 | -            "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
 446 | +    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
 447 |              "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
 448 |                            if j in flagged else "same subject"} for j in js}}
 449 |  
 450 | @@ -154,7 +152,8 @@ class TestMedleyLineup(unittest.TestCase):
 451 |  
 452 |  
 453 |  class TestClipsAloneVerdict(unittest.TestCase):
 454 | -    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 455 | +    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2}), pm("x", "B", 14.0),
 456 | +            pm("y", "C", 13.0)]
 457 |      LABS = ["hook", "clip_01", "clip_02"]
 458 |  
 459 |      def run_it(self, reply):
 460 | @@ -187,24 +186,29 @@ class TestClipsAloneVerdict(unittest.TestCase):
 461 |          self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
 462 |          self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])
 463 |  
 464 | -    def test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts(self):
 465 | +    def test_ruling_61_the_hook_is_rated_once_its_cached_own_job_rating_stands(self):
 466 |          prompts = []
 467 | -        r = Canned(coherence_verdict=[reply(self.LABS, hook={"setup": 3})])
 468 | +        r = Canned(coherence_verdict=[reply(self.LABS)])
 469 |          call = r.call
 470 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 471 |          ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
 472 | -        self.assertFalse(ok)                              # one part under the bar: the hook's derived rating is 3
 473 | -        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 474 | -        self.assertIn("lowest of scroll / alone / setup", v["hook_rule"])
 475 | -        for part in ('"scroll"', '"alone"', '"setup"', "first 2-3 seconds", "wants the next clip",
 476 | -                     "For each clip AFTER the hook", '"clip_01": 1, "clip_02": 1'):
 477 | -            self.assertIn(part, prompts[0])
 478 | -        self.assertNotIn('"hook": 1', prompts[0])         # the hook is not asked for a through-line rating
 479 | -        ok, v, _ = self.run_it(reply(self.LABS, hook={"scroll": 4, "alone": 4, "setup": 4}))
 480 | -        self.assertTrue(ok)                               # every part at the bar of 4
 481 | -        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 482 | -        ok, v, _ = self.run_it(reply(self.LABS, ratings={"hook": 5, "clip_01": 3}))
 483 | -        self.assertFalse(ok)                              # the clips keep their own rating and bar
 484 | +        self.assertTrue(ok)
 485 | +        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})   # min(scroll 5, alone 4), cached
 486 | +        self.assertEqual((v["hook_own"]["scroll"], v["hook_own"]["alone"], v["hook_own"]["rating"]), (5, 4, 4))
 487 | +        self.assertNotIn(PK.HOOK_QUESTION, prompts[0])                         # never re-asked per line-up
 488 | +        self.assertIn("NOT rated here", prompts[0])
 489 | +        self.assertIn('"hook -> clip_01"', prompts[0])                         # 'sets up': the hook's own join
 490 | +        self.assertNotIn('"hook": 1', prompts[0])
 491 | +        self.assertIn('"clip_01": 1, "clip_02": 1', prompts[0])
 492 | +        low = [dict(self.SEGS[0], hook_rating={"scroll": 3, "alone": 5, "setup": 5}), *self.SEGS[1:]]
 493 | +        ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), low, E.Context(NOW, REG), set())
 494 | +        self.assertFalse(ok)                                                   # its cached rating is under the bar
 495 | +        ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), [pm("h", "A", 12.0), *self.SEGS[1:]],
 496 | +                          E.Context(NOW, REG), set())
 497 | +        self.assertFalse(ok)                                                   # no cached rating: fail closed
 498 | +        self.assertNotIn("hook", v["clips"])
 499 | +        ok, v, _ = self.run_it(reply(self.LABS, ratings={"clip_01": 3}))
 500 | +        self.assertFalse(ok)                                                   # the clips keep their bar
 501 |  
 502 |      def test_out_of_contract_is_not_measured_and_rejected(self):
 503 |          good = reply(self.LABS)
 504 | @@ -213,10 +217,8 @@ class TestClipsAloneVerdict(unittest.TestCase):
 505 |                      dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
 506 |                      dict(good, vo_point=5),
 507 |                      dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),            # the hook among the clips
 508 | -                    dict(good, hook={"scroll": 5, "alone": 5}),                           # a part missing (ruling 52)
 509 | -                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 6}),
 510 | -                    dict(good, hook={"scroll": "5", "alone": 5, "setup": 5}),
 511 | -                    {k: x for k, x in good.items() if k != "hook"}):
 512 | +                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 5}),               # a hook rating (ruling 61)
 513 | +                    dict(good, clips={"clip_01": 6, "clip_02": 5})):
 514 |              ok, v, r = self.run_it(bad)
 515 |              self.assertFalse(ok)
 516 |              self.assertFalse(v["measured"])
 517 | @@ -224,46 +226,46 @@ class TestClipsAloneVerdict(unittest.TestCase):
 518 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 519 |  
 520 |  
 521 | -class TestCoherenceHookRating(unittest.TestCase):
 522 | -    """The orchestrator's answer (09:59): ruling 52's hook rating applies to the coherence verdict after the takeaway as
 523 | -    well. ONE definition of the hook's job (HOOK_QUESTION) in both verdicts; the hook's rating derived, never free-form."""
 524 | +class TestCoherenceHookRatedOnce(unittest.TestCase):
 525 | +    """RULING 61 (12:00): the coherence verdict after the takeaway does not rate the hook either: its cached own-job
 526 | +    rating stands (hook_own); the clips after the hook and vo_point are judged as before."""
 527 |      PK_ = {"title": "Nobody bends the rules", "caption": "three clips",
 528 |             "vo": {"intro": None, "bridges": ["No ruler, just rules."], "bridges_after_clip": [2], "signoff": "S"},
 529 |             "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
 530 |                          {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
 531 |                          {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
 532 | +    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2})
 533 |  
 534 | -    def reply(self, hook=None, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
 535 | -        return {"through_line": line, "hook": dict({"scroll": 5, "alone": 5, "setup": 5}, **(hook or {})),
 536 | -                "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
 537 | +    def reply(self, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
 538 | +        return {"through_line": line, "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
 539 |  
 540 | -    def run_it(self, reply):
 541 | +    def run_it(self, reply, hook=HOOK):
 542 |          r = Canned(coherence_verdict=[reply])
 543 |          prompts = []
 544 |          call = r.call
 545 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 546 | -        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"})
 547 | +        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"}, hook=hook)
 548 |          return ok, v, r, prompts
 549 |  
 550 | -    def test_the_hook_is_rated_on_its_own_job_and_derived(self):
 551 | -        ok, v, _, prompts = self.run_it(self.reply(hook={"setup": 3}))
 552 | -        self.assertFalse(ok)
 553 | -        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 554 | -        self.assertIn(PK.HOOK_QUESTION, prompts[0])                 # the one definition, as in the clips-alone verdict
 555 | -        self.assertIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
 556 | -        self.assertIn("For each clip AFTER the hook", prompts[0])
 557 | -        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
 558 | -        ok, v, _, _ = self.run_it(self.reply(hook={"scroll": 4, "alone": 4, "setup": 4}))
 559 | +    def test_the_hook_is_not_re_rated(self):
 560 | +        ok, v, _, prompts = self.run_it(self.reply())
 561 |          self.assertTrue(ok)
 562 |          self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 563 | +        self.assertNotIn(PK.HOOK_QUESTION, prompts[0])
 564 | +        self.assertNotIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
 565 | +        self.assertIn("NOT", prompts[0])
 566 | +        self.assertIn("For each clip AFTER the hook", prompts[0])
 567 | +        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
 568 |          self.assertFalse(self.run_it(self.reply(clips={"clip_02": 3}))[0])      # clips and vo_point as before
 569 |          self.assertFalse(self.run_it(self.reply(vo=3))[0])
 570 | +        self.assertFalse(self.run_it(self.reply(), hook=pm("h", "A", 12.0))[0])   # no cached rating: fail closed
 571 | +        self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 5}))[0])
 572 |  
 573 |      def test_out_of_contract_is_not_measured(self):
 574 |          good = self.reply()
 575 | -        for bad in ({k: x for k, x in good.items() if k != "hook"}, dict(good, hook={"scroll": 5, "alone": 5}),
 576 | -                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}), dict(good, hook={"scroll": 5, "alone": 5,
 577 | -                                                                                               "setup": 0})):
 578 | +        for bad in (dict(good, hook={"scroll": 5, "alone": 5, "setup": 5}),
 579 | +                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),
 580 | +                    {k: x for k, x in good.items() if k != "vo_point"}, dict(good, vo_point=0)):
 581 |              ok, v, r, _ = self.run_it(bad)
 582 |              self.assertEqual((ok, v["measured"]), (False, False))
 583 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 584 | @@ -520,7 +522,7 @@ class Rig:
 585 |  
 586 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 587 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 588 | -                 trim_fail=(), hooks=None, hook_err=None, verdicts=None):
 589 | +                 trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None):
 590 |          import providers as P
 591 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 592 |          self.takeaways, self.spend = list(takeaways or []), spend
 593 | @@ -533,7 +535,8 @@ class Rig:
 594 |          self.screens, self.events, self.a_seen = [], [], []
 595 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 596 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 597 | -        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 598 | +        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}] + ([follow_up] if follow_up else []))
 599 | +        self.angle_hooks = {a[0] for a in many}           # ruling 59: by default only the canned angles' hooks pass
 600 |          call = self.router.call
 601 |  
 602 |          def rcall(role, prompt, *a, **k):
 603 | @@ -579,8 +582,8 @@ class Rig:
 604 |              return {}, self.hook_err
 605 |          out = {}
 606 |          for m in ms:
 607 | -            sc, al, se = self.hooks.get(m["moment_id"], (5, 5, 5))
 608 | -            out[m["moment_id"]] = {"scroll": sc, "alone": al, "setup": se, "rating": min(sc, al, se),
 609 | +            sc, al, se = self.hooks.get(m["moment_id"], (5, 5, 5) if m["moment_id"] in self.angle_hooks else (3, 3, 3))
 610 | +            out[m["moment_id"]] = {"scroll": sc, "alone": al, "setup": se, "rating": min(sc, al),   # ruling 61
 611 |                                     "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 612 |          return out, None
 613 |  
 614 | @@ -1215,23 +1218,24 @@ class TestRuling59HookFirst(unittest.TestCase):
 615 |      def test_only_a_hook_rated_4_or_more_opens(self):
 616 |          m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
 617 |          self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
 618 | -        for rating, ok in ((4, True), (5, True), (3, False), (None, False)):
 619 | -            r = dict(m, hook_rating={"rating": rating})
 620 | -            self.assertEqual(PK.can_open(r), ok, rating)
 621 | +        for (sc, al, se), ok in (((4, 4, 1), True), ((5, 4, 5), True), ((3, 5, 5), False), ((5, 3, 5), False)):
 622 | +            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se})
 623 | +            self.assertEqual(PK.can_open(r), ok, (sc, al, se))           # ruling 61: scroll / alone, never setup
 624 |              self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
 625 | -        self.assertFalse(PK.can_open(dict(m, hook_rating=None)))
 626 | -        self.assertFalse(PK.can_open(dict(m, hook_rating={"rating": True})))
 627 | +        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5}, {"scroll": 5.0, "alone": 5}):
 628 | +            self.assertFalse(PK.can_open(dict(m, hook_rating=bad)), bad)
 629 |          self.assertFalse(PK.can_open(dict(m, text="And Bitcoin is money.")))   # the render's hook rule
 630 | -        self.assertFalse(PK.lineup_ok([dict(m, hook_rating={"rating": 3}), pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
 631 | +        low = dict(m, hook_rating={"scroll": 3, "alone": 4, "setup": 4})
 632 | +        self.assertFalse(PK.lineup_ok([low, pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
 633 |  
 634 |      def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
 635 | -        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"rating": 5})
 636 | +        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5})
 637 |                for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
 638 |          by = {m["moment_id"]: m for m in ms}
 639 |          by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
 640 |          segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
 641 |          self.assertEqual(segs[0]["moment_id"], "a")
 642 | -        low = dict(by, a=dict(by["a"], hook_rating={"rating": 3}))
 643 | +        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 3, "alone": 5, "setup": 5}))
 644 |          self.assertIsNone(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True, hook_only=True))
 645 |          self.assertEqual(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True)[0]["moment_id"], "b")
 646 |          self.assertEqual(PK.swap_lineup(segs, {"a"}, by, keep_hook=True), (None, None))
 647 | @@ -1269,14 +1273,16 @@ class TestRuling59HookFirst(unittest.TestCase):
 648 |          self.assertLess(p.index("id=x | rated 5"), p.index("id=h | rated 4"))    # best first
 649 |          self.assertNotIn("id=y | rated", p)
 650 |          self.assertIn("id=y | C | 13.0 s | cannot open (never the hook) | ", p)
 651 | -        self.assertIn("up to 1 for EACH hook above, at most 3 in all", p)
 652 | +        self.assertIn("for EACH hook above at least one and at most 1 (every hook gets its own)", p)
 653 | +        self.assertNotIn("angle_follow_up", out)                          # ruling 64: both hooks have an angle
 654 |          self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
 655 |          self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
 656 |          self.assertIsNotNone(out["package"])
 657 |  
 658 |      def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
 659 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 660 | -        rig = Rig(ms, ["y", "h", "x", "z"], [(True, [], None, Rig.LINE)], [None], hooks={"y": (3, 3, 3)})
 661 | +        rig = Rig(ms, ["y", "h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
 662 | +                  hooks={"y": (3, 3, 3), "h": (5, 5, 5), "x": (5, 5, 5), "z": (5, 5, 5)})
 663 |          out = rig.run()
 664 |          self.assertIsNone(out["package"])
 665 |          self.assertIn("is not one of THE HOOKS", out["why_none"])           # the first reply, rejected
 666 | @@ -1505,6 +1511,76 @@ class TestRuling56Scorer(unittest.TestCase):
 667 |          self.assertEqual(PK.text_sha(t), hashlib.sha256(t.encode("utf-8")).hexdigest())   # one sha, build and pin
 668 |  
 669 |  
 670 | +class TestRulings6264Search(unittest.TestCase):
 671 | +    """RULINGS 62-64 (12:00): the last clip retried away before any swap; joins before swaps (the same clips
 672 | +    reordered); an angle for every passing hook; the budget counts JUDGED line-ups (an identical one is free)."""
 673 | +
 674 | +    def fresh(self, mid, ch, dur, hours_ago=6.0):
 675 | +        return dict(pm(mid, ch, dur), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 676 | +
 677 | +    def test_ruling_62_only_the_last_clip_fails_and_the_floor_holds(self):
 678 | +        ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 14.0), self.fresh("y", "C", 13.0),
 679 | +              self.fresh("z", "D", 9.0, hours_ago=1.0)]                      # z is fresh: the 4-clip line-up first
 680 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_03": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
 681 | +                  [None])
 682 | +        out = rig.run()
 683 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"], ["h", "x", "y"]])   # 39 s >= the 36.7 s floor
 684 | +        self.assertIn("ruling 62", out["tried"][0]["why"])
 685 | +        self.assertIsNotNone(out["package"])
 686 | +
 687 | +    def test_ruling_62_under_the_floor_swaps_as_now(self):
 688 | +        ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 10.0), self.fresh("y", "C", 10.0),
 689 | +              self.fresh("z", "D", 9.0)]                                    # without z: 32 s, under 36.7
 690 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_03": 2}, Rig.LINE)], [None])
 691 | +        out = rig.run()
 692 | +        self.assertEqual(len(rig.medley_calls), 1)
 693 | +        self.assertNotIn("ruling 62", out["tried"][0]["why"])
 694 | +        self.assertIn("the clips alone fail", out["tried"][0]["why"])
 695 | +
 696 | +    def test_ruling_63_two_flagged_joins_reorder_the_same_clips_first(self):
 697 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 698 | +        rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
 699 | +                                        (True, [], None, Rig.LINE)], [None])
 700 | +        out = rig.run()
 701 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "x"]])   # the hook first, no clip dropped
 702 | +        self.assertIn("ruling 63", out["tried"][0]["why"])
 703 | +        self.assertIsNotNone(out["package"])
 704 | +
 705 | +    def test_reorder_avoids_the_known_unfollowable_pairs_and_moves_least(self):
 706 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})          # it can open (G17a)
 707 | +        segs = [h, pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0)]
 708 | +        got = PK.reorder(segs, {("h", "x"), ("y", "z")}, {("h", "x", "y", "z")})
 709 | +        self.assertEqual([m["moment_id"] for m in got], ["h", "y", "x", "z"])
 710 | +        two = [h, pm("x", "B", 14.0), pm("y", "C", 13.0)]
 711 | +        self.assertIsNone(PK.reorder(two, {("h", "y"), ("y", "x"), ("h", "x"), ("x", "y")}, set()))   # no order helps
 712 | +        short = [dict(h, duration_s=14.0, end=14.0), pm("x", "B", 14.0), pm("s", "C", 7.0), pm("y", "D", 9.0)]
 713 | +        got = PK.reorder(short, {("x", "s")}, {("h", "x", "s", "y")})
 714 | +        self.assertEqual(got[-1]["moment_id"], "s")                         # a short clip plays only LAST
 715 | +
 716 | +    def test_ruling_64_a_passing_hook_left_without_an_angle_is_asked_for(self):
 717 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("g", "D", 12.0), pm("z", "E", 13.0)]
 718 | +        rig = Rig(ms, [["h", "x", "y"]], [(False, [], None, "none"), (True, [], None, Rig.LINE)], [None],
 719 | +                  hooks={"h": (5, 5, 5), "g": (5, 5, 5)},
 720 | +                  follow_up={"angles": [angle(["g", "x", "z"], "g")]})
 721 | +        out = rig.run()
 722 | +        self.assertEqual(out["angle_follow_up"]["hooks"], ["g"])
 723 | +        follow = [p for r, p in rig.prompts if r == "angle_write"][1]
 724 | +        self.assertIn("id=g | rated 5", follow)
 725 | +        self.assertNotIn("id=h | rated", follow)                           # written for exactly the hook left out
 726 | +        self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # the second hook is tried
 727 | +        self.assertIsNotNone(out["package"])
 728 | +        self.assertEqual([a["hook"] for a in PK.allot([angle(["a", "b", "c"], "a")] * 3 +
 729 | +                                                       [angle(["b", "a", "c"], "b")], 1)], ["a", "b"])
 730 | +
 731 | +    def test_the_budget_counts_judged_line_ups_and_an_identical_one_is_free(self):
 732 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 733 | +        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "y"]], [(False, [], None, "none")], [None])
 734 | +        out = rig.run()
 735 | +        self.assertEqual(len(rig.medley_calls), 1)                          # judged once
 736 | +        self.assertEqual(out["search"]["lineups"], 1)
 737 | +        self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free
 738 | +
 739 | +
 740 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 741 |      """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 742 |      after a write swaps out that clip only, and the line-up carries on."""
 743 | @@ -1729,7 +1805,8 @@ class TestProposal1PoolFill(unittest.TestCase):
 744 |      def test_ruling_54_the_proposer_is_told_each_clips_placement_limits(self):
 745 |          ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5),
 746 |                pm("o", "F", 7.3)]
 747 | -        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
 748 | +        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"},
 749 | +                  hooks={"o": (5, 5, 5), "z": (5, 5, 5)})             # o and z can open: rated as passing hooks
 750 |          rig.run()
 751 |          p = next(p for r, p in rig.prompts if r == "angle_write")
 752 |          self.assertIn('id=o | F | 7.3 s | under 8 s: only the hook or the LAST clip | "', p)   # audit 0855 C1, qwen
 753 | @@ -1841,13 +1918,13 @@ class TestRuling41Search(unittest.TestCase):
 754 |              if segs is not None:
 755 |                  self.assertEqual(PK.lineup_ok(segs), (True, "ok"), order)
 756 |  
 757 | -    def test_a_low_rated_hook_is_never_swapped_and_the_search_stops_at_8_line_ups(self):
 758 | +    def test_a_failed_angle_never_swaps_its_hook_and_the_search_stops_at_8_line_ups(self):
 759 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
 760 |          rig = Rig(ms, [["h", "x", "y", "z"], ["g", "x", "y", "z"]],
 761 | -                  [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
 762 | +                  [(False, [], None, "none"), (True, [], None, Rig.LINE)], [None])
 763 |          out = rig.run()
 764 |          self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # ruling 59 (c): h's angle ends, g's next
 765 | -        self.assertIn("written for this hook (ruling 59 c)", out["tried"][0]["why"])
 766 | +        self.assertIn("no through-line", out["tried"][0]["why"])
 767 |          self.assertIsNotNone(out["package"])
 768 |          many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
 769 |          fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
 770 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels, sealed in a pin that the integrator renders). Your role: a strict reviewer of a search and verdict change.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- A build screens moments (step A), rates every moment that can open on the hook's own job in one batched call
  (ruling 59: HOOK_QUESTION's three parts scroll / alone / setup, each 1-5, cached across builds), and gives the angle
  writer THE HOOKS (rated >= 4).
- For each angle it forms line-ups (lineup_for: the hook + 2-4 clips, one per channel, the medley's seconds 36.7-51.5,
  a clip under 8 s only last, the render's STAND_ALONE). Each line-up is judged on the clips ALONE by a blind verdict
  (medley()): a through-line, a 1-5 rating per clip, and per join whether a viewer can follow it.
  - A line-up passes when the through-line is stated, every rating is >= 4, and at most ONE join is flagged (the one
    bridge L-y allows).
  - A failure swaps the weak clips (ruling 41: swap_lineup) or re-lines.
  - At most 8 line-ups per build (ruling 41).
- After the takeaway is written, the coherence verdict (coherence()) rates the clips and the VO's point again.
- Until now both verdicts asked HOOK_QUESTION again inside every line-up, and the hook's rating there was the lowest
  of its three parts.

The orders this diff implements (ORCHESTRATOR RULINGS 12:00 ET Nov 13, verbatim):
"The 11:31 build is the first real one: 31 cuttable, 2 hooks, and three line-ups one step from passing (line-up 5:
4/5/4/3, one flagged join; line-up 6: hook 3 then 5/4/5, one flagged join; angle 2 line-up 2: 4/4/5 with two flagged
joins). What sank them is judge noise and search order, not the clips. Audit these together, build at once.
61. THE HOOK IS RATED ONCE. The same hook rated 4 on its own job (ruling 59, cached) was re-rated 2, 3 and 4 inside
different line-ups. That is noise deciding the outcome. From now: 'stops the scroll' and 'stands alone' are the hook's
cached own-job rating and are NOT re-asked per line-up. 'Sets up what follows' is judged where it is measurable: the
hook -> clip_01 join (followable, or the one bridge L-y allows). The line-up verdict rates the CLIPS and the joins; it
shows the hook's text for context and does not rate it again. Same for the coherence verdict after the takeaway.
62. THE LAST CLIP. A line-up whose only failure is its last clip (rated under 4) is retried WITHOUT that clip when the
remaining hook + clips still meet the medley's seconds floor, before any swap is spent. If the floor is not met, swap
as now.
63. JOINS BEFORE SWAPS. When every rating passes and more than one join is flagged, try the other ORDERS of the same
clips (the hook stays first; placement limits respected) before dropping anything: a flagged join is about adjacency,
and reordering is free of new step A cost. One bridge at most, unchanged (L-y).
64. Your own gap (one angle per passing hook, so the second hook is tried): yes, fix it as you say.
The search budget of 8 line-ups counts JUDGED line-ups; cached verdicts for an identical line-up are free."

The change (pipeline/package.py, tests/package/test_medley.py):

61:
- HOOK_OWN = (scroll, alone). hook_own(m) reads a moment's cached rating and returns {scroll, alone, rating = the
  lower of the two}; it returns None unless both are ints.
  - can_open() uses it (rating >= 4).
  - hook_order() and the angle rank use it.
  - hook_ratings() stores rating = min(scroll, alone), and recomputes it for cached records. The question and its
    cache version are unchanged.
- MEDLEY_PROMPT no longer contains HOOK_QUESTION: the hook is shown "for context only: it is NOT rated here". The
  judge rates the clips after the hook and every join, "the hook's own join included (does the hook set up the clip
  after it?)".
  - medley() contract: exactly {through_line, clips (the clips after the hook), joins}.
  - verdict["clips"]["hook"] = the hook's cached own-job rating. A hook without one fails closed, and is not put into
    clips.
  - ok = own rating present and the through-line stated and every rating >= 4 and flagged joins <= 1.
- The same for COHERENCE_PROMPT / coherence(..., hook=the hook moment), whose call site passes segs[0].
  _line_ok() is factored out (the through-line rule M7, unchanged).
62: last_clip_only(segs, med): measured, the through-line stated, the hook's rating present, the last clip the only
    rating under 4, and at most one flagged join once the join INTO the last clip is discounted. In the loop, the
    line-up without its last clip is judged next (the last clip goes to `dropped`) when it keeps >= 2 clips and passes
    lineup_ok (which includes the seconds floor and the render's STAND_ALONE), before any swap.
63: when the verdict is measured, the through-line is stated, every rating (the hook's included) is >= 4, and more than
    one join is flagged, reorder() picks the next order:
    - every permutation of the clips after the hook (the hook first) not judged yet in this build;
    - at most one adjacent pair known to be unfollowable (bad_pairs: every flagged (from, to) moment pair of this
      build's verdicts);
    - passing lineup_ok (placement limits, the render's STAND_ALONE in the new order);
    - best by the fewest such pairs, then the fewest clips moved.
    When no order qualifies, the old path runs (the clips after the flagged joins are weak; swap or re-line).
64:
- offered = the best max_angles (3) passing hooks; per = max(1, 3 // len(offered)).
- The angle prompt says "for EACH hook above at least one and at most {per} (every hook gets its own), at most {k} in
  all".
- allot() keeps at most `per` angles per hook, in the writer's order; the dropped ones are recorded.
- An offered hook left without an angle gets ONE follow-up angle call written for exactly those hooks, within the
  remaining angle budget; it uses the same contract and allot. A failed follow-up is recorded and never fails the
  build. No verdict sees the angle sentence (CI.package_view shows the title, caption, clips and VO), and the writes
  stay on the first angle call's vendor as before.
The budget:
- An identical line-up (the same moment ids in the same order) reuses its verdict free: `judged`, keyed by the id tuple.
- `total` counts only verdicts actually asked and not replayed.
- A guard stops an angle's loop after 4 x the budget in iterations, so free repeats never turn forever.
Tests:
- the clips-alone and coherence verdict tests are rewritten for 61;
- ruling 59's tests read the rating from its parts;
- the test Rig rates only its canned angles' hooks as passing unless a test rates hooks, and can give a follow-up
  reply;
- new tests: 62 (the floor met, and not met), 63 (a reorder first; the unit cases), 64 (the follow-up call; allot),
  and the budget (an identical line-up judged once).
test_medley 119 OK; all 11 suites OK.

Stated readings (say so if you read the rulings differently):
- K1 (61): the gate for opening (ruling 59 b) becomes the own-job rating, min(scroll, alone). 'Setup', still asked in
  the batched hook question (unchanged, so its cache stays valid), is recorded but gates nothing: it is judged at the
  hook's join.
- K2 (62): "only failure" means the last clip is the only rating under 4, the through-line is stated, and the flagged
  joins, once the join into the last clip goes with it, are within the one bridge.
- K3 (63): a reordered line-up is a new line-up and is judged (it counts when judged). Known-unfollowable pairs come
  from every verdict of the build, because a pair's adjacency is the same in any line-up.
- K4 (64): per-hook calls would cost a call per hook. One call plus a follow-up only for hooks left without an angle
  keeps the cost at one or two calls.
- K5 (budget): "cached verdicts for an identical line-up are free" covers an identical line-up within the build (the
  memo) and a verdict the router replays from its recorded replies.

Check in particular:
- that no hook can open or pass without its cached own-job rating >= 4;
- that the contracts reject a hook rating in the reply;
- 62's floor and placement checks;
- 63's search (termination, the hook fixed, placement limits, no repeat of a judged order);
- 64's follow-up (it can never fail the build, and its vendor);
- that the budget can never loop forever;
- any old caller of medley / coherence / can_open that changes behaviour unintentionally.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

