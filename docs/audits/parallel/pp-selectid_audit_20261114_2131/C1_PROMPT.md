# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2131
# Branch: pp-selectid
# Generated: 2026-11-14 21:31 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2131/C1_STEP.diff (685 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 28bcc89..967f665 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -943,6 +943,9 @@ RULES (a line that breaks one is rejected):
   6 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
   7 |    "slams", "exposes", "admits", "confirms", "caught".
   8 |  - A line that names a show, a person or Bitcoin's price cites the clips it comes from.
   9 | +- Never give anyone a ROLE the clips' own words do not state: no "guest", "host", "co-host", "analyst", "expert",
  10 | +  "economist", "strategist", "interviewer", "presenter", "anchor", "panelist" or "commentator". A role is a claim
  11 | +  (law L-v): say "he", "she" or "the speaker", or credit the show.
  12 |  {style}
  13 |  {extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
  14 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
  15 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  16 | index bfbed07..1f409cf 100644
  17 | --- a/pipeline/package_pin.py
  18 | +++ b/pipeline/package_pin.py
  19 | @@ -187,7 +187,18 @@ def window_problems(segments, now=None):
  20 |      return out
  21 |  
  22 |  
  23 | -def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None):
  24 | +def formats_of(segments):
  25 | +    """RULING 93 AMENDED (orchestrator 21:10 ET Nov 14; the integrator's spelling, 21:31): the formats a pin may be
  26 | +    rendered in. ["16x9"] when ANY segment's sealed visual record says so (a source caption the 9:16 crop cuts: a
  27 | +    medley takes the intersection), else None: absent means both formats, as every pin before it."""
  28 | +    for s in segments or []:
  29 | +        if ((s or {}).get("visual") or {}).get("formats") == ["16x9"]:
  30 | +            return ["16x9"]
  31 | +    return None
  32 | +
  33 | +
  34 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None,
  35 | +         formats=None):
  36 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
  37 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
  38 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
  39 | @@ -214,6 +225,8 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shap
  40 |      if shape == "spotlight":                               # ruling 90: the closing line, the kind and the comment,
  41 |          body["vo"]["closing"] = edl_vo.get("closing")      # sealed; keyed on the kind alone, so no medley's body
  42 |          body["shape"], body["first_comment"] = shape, first_comment   # can change (audit 2322 C1, glm)
  43 | +    if formats is not None:                                # ruling 93 amended: "formats", only when present, so every
  44 | +        body["formats"] = formats                          # pin before it recomputes to its own sha
  45 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
  46 |  
  47 |  
  48 | @@ -225,7 +238,8 @@ def pin_seal(pin):
  49 |      shape = mp.get("shape")
  50 |      return seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"],
  51 |                  mp.get("btc_screen"), shape="spotlight" if shape == "spotlight" else None,
  52 | -                first_comment=mp.get("first_comment") if shape == "spotlight" else None)
  53 | +                first_comment=mp.get("first_comment") if shape == "spotlight" else None,
  54 | +                formats=mp.get("formats"))
  55 |  
  56 |  
  57 |  def affirmed_verdict(s):
  58 | @@ -451,8 +465,9 @@ def to_pin(pk, run_name):
  59 |      spot = pk.get("shape") == "spotlight"                 # ruling 90: the agreed contract
  60 |      if spot:
  61 |          edl_vo["closing"] = pk["vo"].get("closing")
  62 | +    fmts = formats_of(segs)                               # ruling 93 amended: sealed, only when 16:9-only
  63 |      sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"),
  64 | -               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None)
  65 | +               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None, formats=fmts)
  66 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
  67 |              "label": "bitcoin", "headline": pk["title"],
  68 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
  69 | @@ -481,6 +496,7 @@ def to_pin(pk, run_name):
  70 |                                     if spot else {}),
  71 |                                  "gates": pk["gates"],
  72 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
  73 | +                                **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
  74 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
  75 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
  76 |                                             "models": pk.get("models")},
  77 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  78 | index 5f7daa3..6011dcf 100644
  79 | --- a/pipeline/spotlight.py
  80 | +++ b/pipeline/spotlight.py
  81 | @@ -474,11 +474,12 @@ def layout_for(router, m, vrec, cache_path=None, seed=7, evidence=None):
  82 |  def clean_visual(v):
  83 |      """RULING 90's "visual check clean" with RULING 93: measured, no ruling-70 flag (a third person shown as a still
  84 |      with a negative claim, on-screen text that asserts beyond the words), not blocked as a hook, and eligible on its
  85 | -    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) is
  86 | -    eligible and flagged for the orchestrator, so it does not make the clip unclean."""
  87 | +    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) and a
  88 | +    "burned_caption" flag (ruling 93 amended, 21:10 Nov 14: the source's own captions never make a clip ineligible)
  89 | +    are flagged for the orchestrator, so they do not make the clip unclean."""
  90 |      import visual_pin as VP
  91 |      return (v or {}).get("measured") is True and not VP.hook_block(v) and not VP.layout_block(v) and \
  92 | -        not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]
  93 | +        not [f for f in v.get("flags") or [] if f.get("kind") not in ("burned_in", "burned_caption")]
  94 |  
  95 |  
  96 |  def alone_score(m):
  97 | @@ -531,6 +532,9 @@ RULES (a line that breaks one is rejected):
  98 |  - No price level; no advice to buy, sell or use leverage; no quotes except the clip's exact words; no "destroys",
  99 |    "slams", "exposes", "admits", "confirms", "caught".
 100 |  - A line that names a show, a person or Bitcoin's price cites the clip.
 101 | +- Never give anyone a ROLE the clip's own words do not state: no "guest", "host", "co-host", "analyst", "expert",
 102 | +  "economist", "strategist", "interviewer", "presenter", "anchor", "panelist" or "commentator". A role is a claim
 103 | +  (law L-v): say "he", "she" or "the speaker", or credit the show.
 104 |  {style}
 105 |  {extra}Return ONLY this JSON object: {{"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}},
 106 |  "comment": {{"text": "...", "cites": []}}, "closing": {{"text": "...", "cites": []}} or null}}"""
 107 | @@ -753,6 +757,8 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 108 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 109 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 110 |                                      why=src_rec.get("why"), evidence=src_rec.get("evidence"), layout=src_rec.get("layout"),
 111 | +                                    format=str((src_rec.get("layout") or {}).get("layout") or "").upper() or None,  # 21:10
 112 | +                                    #   Nov 14: WHICH of CONVERSATION / FIRST_HAND passed, on the pin's sealed row
 113 |                                      rule="ruling 92 amended (09:03 Nov 14): the layout decides (conversation or "
 114 |                                           "first-hand); the captions are evidence, refusing alone only with zero "
 115 |                                           "speaker changes in the 10 minutes around the clip")
 116 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
 117 | index 36973ce..06b7ffa 100644
 118 | --- a/pipeline/tail_variant.py
 119 | +++ b/pipeline/tail_variant.py
 120 | @@ -125,6 +125,13 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s, directives=None):
 121 |                  notes[mid] = "the directive: no variant, the parent is one sentence (no earlier boundary)"
 122 |              continue                                     # one sentence: no earlier boundary
 123 |          wanted = []
 124 | +        if (directives or {}).get(mid, {}).get("reseal") is True:   # RULING 93 AMENDED + 106 (21:31 Nov 14): the SAME
 125 | +            d = directives[mid]                                    # moment sealed again (16:9-only) in the place
 126 | +            m["derived_from"] = {"ruling": "93 amended", "reseal_of": d["alternative_to"],       # of its own earlier
 127 | +                                 "alternative_to": d["alternative_to"], "directive": d.get("by"),  # story, never as a
 128 | +                                 "why": d.get("why") or ""}                                        # second spotlight
 129 | +            notes[mid] = f"the directive: re-sealed in the place of {d['alternative_to']}"
 130 | +            continue
 131 |          if mid in (directives or {}):                    # the orchestrator's directive: this variant, in its place
 132 |              try:
 133 |                  src = CI.source_for(m, sources)
 134 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 135 | index ef4a557..0c87d31 100644
 136 | --- a/pipeline/visual_pin.py
 137 | +++ b/pipeline/visual_pin.py
 138 | @@ -21,6 +21,11 @@ Per clip (a moment's [start, end]):
 139 |    not wholly in the 16:9, that the 9:16 edge would cut mid-word, or that covers the speaker, makes the clip NOT
 140 |    eligible in any role (per clip, never by channel name); one that sits whole in the 16:9 and wholly in or out of the
 141 |    9:16 is eligible and sealed as a "burned_in" FLAG for the orchestrator.
 142 | +- RULING 93 AMENDED (orchestrator 21:10 ET Nov 14), visual-3: the source's own BURNED CAPTIONS of the spoken words are
 143 | +  asked for explicitly (question 4's kind "caption", with the frame times each shows in), on a sheet of one frame a
 144 | +  second (TILES 36, the 35 s ceiling). Visual-2 asked to leave "subtitles of the spoken words" out, twice, and missed
 145 | +  Blockware's. A caption never makes a clip ineligible: one the 9:16 crop cuts mid-word makes it 16:9-ONLY (formats():
 146 | +  "formats": ["16x9"], sealed in the visual record), and each caption is flagged ("burned_caption").
 147 |  - hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 148 |    speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 149 |    third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 150 | @@ -32,11 +37,18 @@ import os
 151 |  import subprocess
 152 |  import threading
 153 |  
 154 | -VERSION = "visual-2"                     # RULING 93 (23:58 ET Nov 13): question 4, burned-in text and the 9:16
 155 | -ROLE = "visual_check"
 156 | -TILES, EVERY_S, TILE_W = 8, 2.0, 480
 157 | +VERSION = "visual-3"                     # RULING 93 AMENDED (21:10 ET Nov 14): the source's burned captions asked for
 158 | +ROLE = "visual_check"                    #   explicitly, one frame a second (visual-2: ruling 93, 23:58 ET Nov 13)
 159 | +TILES, EVERY_S, TILE_W, COLS = 40, 1.0, 320, 6   # 21:10 Nov 14: "at least one frame a second across the span" (the
 160 | +#   35 s ceiling takes 36; 40 leaves room); 6 x 320 px across keeps the sheet 1920 px wide (visual-2 sampled 8 at 480 px:
 161 | +#   one every 3.27 s on Blockware's 22.94 s, and its question excluded the captions it showed)
 162 |  HOW = ("still", "photo", "graphic", "none")
 163 | -BURNED = ("ticker", "crawl", "lower_third", "bug")      # ruling 93: question 4's kinds
 164 | +BURNED = ("ticker", "crawl", "lower_third", "bug", "caption")   # ruling 93: question 4's kinds; "caption" (ruling 93
 165 | +CAPTION = "caption"                                    # amended): the source's own burned subtitles of the words
 166 | +RENDER_16X9_ONLY = False      # the integrator's render cannot yet pass a 16:9-only pin (its message 21:2x Nov 14: its
 167 | +#   release_auth needs the 9:16 rows; it builds the format-aware path, audited): until it says so, a clip that is
 168 | +#   16:9-only is HELD here (layout_block), and no 16:9-only pin is sealed. Flipped on its word, with the package-level
 169 | +#   "formats" (package_pin), in one audited change.
 170 |  RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
 171 |  IN_9X16 = ("whole", "out", "cut")
 172 |  FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 173 | @@ -53,25 +65,33 @@ Answer four questions from the frames only:
 174 |     person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 175 |     a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 176 |     text on the screen names a person.
 177 | -2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 178 | -   words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 179 | +2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not its captions of the
 180 | +   spoken words, which are question 4's; not the channel's logo), copied exactly, each with whether it ASSERTS
 181 | +   something the clip's words do not.
 182 |  3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 183 | -4. burned_in: every piece of text or graphic burned into the SOURCE picture that stays on screen: a ticker or a crawl
 184 | -   (text that runs or scrolls across the frame), a lower third (a name or headline strap), or a channel bug (a logo or
 185 | -   watermark). Not subtitles of the spoken words. For each say whether it sits WHOLLY inside the frame, and how the
 186 | +4. burned_in: every piece of text or graphic burned into the SOURCE picture: a ticker or a crawl (text that runs or
 187 | +   scrolls across the frame), a lower third (a name or headline strap), a channel bug (a logo or watermark), AND THE
 188 | +   SOURCE'S OWN BURNED-IN CAPTIONS OR SUBTITLES of the spoken words (kind "caption": styled words that show what is
 189 | +   being said, often large and animated, word by word or phrase by phrase). Look at EVERY frame: list each distinct
 190 | +   caption text you can read as its own item, copied exactly, with "at": the frame times (seconds) it shows in.
 191 | +   For each item say whether it sits WHOLLY inside the frame, and how the
 192 |     VERTICAL 9:16 version would treat it. The 9:16 version shows, for ONE speaker, a full-height strip about one third
 193 |     of the frame's width, centred on the speaker's face; for two or three people, a band around each face, stacked; for
 194 |     a shared screen (a chart, a slide, b-roll), the whole frame. "in_9x16" is "whole" (wholly inside the 9:16 picture),
 195 | -   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). "covers_speaker": does it cover
 196 | -   the speaking person's face or mouth?
 197 | +   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). FOR A CAPTION the strip may slide
 198 | +   left or right, but only so far that the speaker's WHOLE face stays inside it with a margin (a tenth of the frame's
 199 | +   width from either edge): "whole" if ONE such position shows the caption whole, "cut" if every such position cuts it
 200 | +   mid-word, "out" if it lies outside every such position. "covers_speaker": does it cover the speaking person's face
 201 | +   or mouth? An empty list means you read NO text at all burned into any frame.
 202 |  
 203 |  Return ONLY this JSON object:
 204 |  {{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 205 |    "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 206 |   "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 207 |   "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}},
 208 | - "burned_in": [{{"kind": "ticker|crawl|lower_third|bug", "text": "<its text, copied>", "whole_in_16x9": true or false,
 209 | -   "in_9x16": "whole|out|cut", "covers_speaker": true or false}}]}}"""
 210 | + "burned_in": [{{"kind": "ticker|crawl|lower_third|bug|caption", "text": "<its text, copied>",
 211 | +   "whole_in_16x9": true or false, "in_9x16": "whole|out|cut", "covers_speaker": true or false,
 212 | +   "at": [<the frame times it shows in, seconds>]}}]}}"""
 213 |  
 214 |  
 215 |  def load_cache(path):
 216 | @@ -95,7 +115,7 @@ def save_cache(path, cache):
 217 |  def key(m):
 218 |      """The cache key: the moment and span, VERSION, and a digest of everything else the verdict reads (the clip's
 219 |      words, the prompt, the sheet's parameters; audit 1541 C1). A hit is used only on the same sheet bytes."""
 220 | -    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, FORMAT, str(m.get("text") or "")])
 221 | +    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, COLS, FORMAT, str(m.get("text") or "")])
 222 |      return (f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:"
 223 |              f"{hashlib.sha256(inputs.encode()).hexdigest()[:16]}")
 224 |  
 225 | @@ -109,12 +129,12 @@ def _sha_of(path):
 226 |  
 227 |  
 228 |  def times(dur, every=EVERY_S, tiles=TILES):
 229 | -    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame; at most `tiles`,
 230 | -    the first and the last always kept."""
 231 | +    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame (so no gap is ever
 232 | +    longer than `every`); at most `tiles`, the first and the last always kept."""
 233 |      last = max(0.0, dur - 0.05)
 234 |      ts = [0.0]
 235 |      t = every
 236 | -    while t < last - 0.25:
 237 | +    while t < last - 0.01:
 238 |          ts.append(round(t, 2))
 239 |          t += every
 240 |      if last > 0:
 241 | @@ -156,7 +176,7 @@ def sheet(video, start, end, work_dir):
 242 |          with Image.open(out) as im:
 243 |              tiles.append(im.convert("RGB").copy())
 244 |          os.remove(out)
 245 | -    cols = min(4, len(tiles))
 246 | +    cols = min(COLS, len(tiles))
 247 |      rows = (len(tiles) + cols - 1) // cols
 248 |      w, h = tiles[0].size
 249 |      canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
 250 | @@ -196,10 +216,14 @@ def check(v):
 251 |      if not isinstance(bi, list) or any(
 252 |              not isinstance(x, dict) or x.get("kind") not in BURNED or not isinstance(x.get("text"), (str, type(None)))
 253 |              or type(x.get("whole_in_16x9")) is not bool or x.get("in_9x16") not in IN_9X16 or
 254 | -            type(x.get("covers_speaker")) is not bool for x in bi):        # a wordless bug may carry no text
 255 | -        raise ValueError("burned_in out of contract (ruling 93)")
 256 | +            type(x.get("covers_speaker")) is not bool or
 257 | +            (x["kind"] == CAPTION and not (x.get("text") or "").strip()) or
 258 | +            not isinstance(x.get("at", []), list) or
 259 | +            any(type(a) not in (int, float) for a in x.get("at") or []) for x in bi):   # a wordless bug may carry
 260 | +        raise ValueError("burned_in out of contract (ruling 93)")                          # no text; a caption must
 261 |      items = [{"kind": x["kind"], "text": (x.get("text") or "").strip()[:TEXT_CHARS],
 262 | -              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"]}
 263 | +              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"],
 264 | +              **({"at": sorted({round(float(a), 2) for a in x["at"]})[:TILES]} if x.get("at") else {})}
 265 |               for x in bi]
 266 |      items = sorted(items, key=lambda x: burned_block(x) is None)   # the blocking ones first, so a cut never hides
 267 |      #   one (audit 0003 C1, glm: a ticker listed 13th would otherwise pass)
 268 | @@ -233,14 +257,30 @@ def flags(v):
 269 |      out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 270 |              if x["asserts_beyond_words"]]
 271 |      out += [{"kind": "burned_in", "text": x["text"], "item": x["kind"], "in_9x16": x["in_9x16"]}   # ruling 93: an
 272 | -            for x in v.get("burned_in") or [] if not burned_block(x)]            # eligible lower third or bug,
 273 | +            for x in v.get("burned_in") or [] if not burned_block(x) and x["kind"] != CAPTION]   # eligible lower
 274 | +    out += [{"kind": "burned_caption", "text": x["text"], "in_9x16": x["in_9x16"],              # third or bug, and
 275 | +             **({"at": x["at"]} if x.get("at") else {})}                                          # (ruling 93 amended)
 276 | +            for x in v.get("burned_in") or [] if x["kind"] == CAPTION]                            # each burned caption,
 277 |      return out                                                                   # flagged for the orchestrator
 278 |  
 279 |  
 280 | +def formats(rec):
 281 | +    """RULING 93 AMENDED (orchestrator 21:10 ET Nov 14): "source-burned captions that the 9:16 crop cuts mid-word make the
 282 | +    clip 16:9-ONLY (sealed as formats: ['16x9'], the integrator renders and delivers that format alone) unless a crop
 283 | +    exists that shows them whole; they do not make the clip ineligible." -> ["16x9"] when any burned caption of a
 284 | +    measured record is "cut" in the 9:16, else None (both formats, as before)."""
 285 | +    if not (rec or {}).get("measured"):
 286 | +        return None
 287 | +    cut = [x for x in rec.get("burned_in") or [] if x.get("kind") == CAPTION and x.get("in_9x16") == "cut"]
 288 | +    return ["16x9"] if cut else None
 289 | +
 290 | +
 291 |  def burned_block(x):
 292 |      """RULING 93 on one burned-in item -> why it makes the clip NOT eligible, or None (eligible, flagged): a ticker or
 293 |      a crawl; a lower third or bug that is not wholly inside the 16:9, that the 9:16 edge would cut through mid-word, or
 294 |      that covers the speaker."""
 295 | +    if x["kind"] == CAPTION:                     # ruling 93 amended: a burned caption never makes a clip ineligible;
 296 | +        return None                              # cut by the 9:16 it makes it 16:9-only (formats())
 297 |      if x["kind"] in RUNNING:
 298 |          return f"a {x['kind']} ({x['text'][:80]!r}): not eligible"
 299 |      if not x["whole_in_16x9"]:
 300 | @@ -259,7 +299,12 @@ def layout_block(rec):
 301 |          return "its visual check is not measured (law L-m)"
 302 |      if not isinstance(rec.get("burned_in"), list):
 303 |          return "ruling 93: the burned-in text question was not asked (an earlier visual record)"
 304 | +    if rec.get("version") != VERSION:            # 21:10 Nov 14: visual-2 never asked for the source's captions
 305 | +        return f"its visual record is {rec.get('version')!r}, which never asked for the source's burned captions"
 306 |      why = [w for w in (burned_block(x) for x in rec["burned_in"]) if w]
 307 | +    if formats(rec) and not RENDER_16X9_ONLY:    # ruling 93 amended: 16:9-only, which the render cannot pass yet
 308 | +        why.append("16:9-only (a burned caption the 9:16 crop cuts mid-word, ruling 93 amended), and the integrator's "
 309 | +                   "render cannot pass a 16:9-only pin until its format-aware release lands: held")
 310 |      return (f"ruling 93 ({len(why)} item(s)): " + "; ".join(why))[:600] if why else None   # (audit 0003 C2)
 311 |  
 312 |  
 313 | @@ -280,7 +325,7 @@ def sealed(rec):
 314 |      """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 315 |      name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 316 |      out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 317 | -                               "burned_in", "burned_in_truncated", "backend", "replayed", "why") if k in rec}
 318 | +                               "burned_in", "burned_in_truncated", "formats", "backend", "replayed", "why") if k in rec}
 319 |      if isinstance(rec.get("sheet"), dict):
 320 |          out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 321 |      return out
 322 | @@ -327,6 +372,7 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
 323 |              r = router.call(ROLE, prompt, 1500, sd)
 324 |              v = check(_json(r.text))
 325 |              rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
 326 | +                   **({"formats": formats(dict(v, measured=True))} if formats(dict(v, measured=True)) else {}),
 327 |                     "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
 328 |                     "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
 329 |                     **cost(r),
 330 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 331 | index 010a13e..645106a 100644
 332 | --- a/pipeline/vo_fidelity.py
 333 | +++ b/pipeline/vo_fidelity.py
 334 | @@ -45,6 +45,9 @@ ATTRIB_VERBS = SPEECH_S                                        # (kept for calle
 335 |  PRONOUN_SUBJECTS = ("he", "she", "they", "his guest", "her guest", "their guest", "the guest", "the host",
 336 |                      "this guest", "this host", "the speaker", "this speaker", "the analyst", "this analyst",
 337 |                      "the author", "experts", "analysts", "critics", "many", "some", "others", "people", "everyone")
 338 | +ROLE_RE = re.compile(r"\b((?:co-?)?hosts?|guests?|analysts?|experts?|economists?|strategists?|interviewers?|"
 339 | +                     r"presenters?|anchors?|panelists?|commentators?)\b", re.I)   # orchestrator 21:10 Nov 14: a role
 340 | +#   ("a guest", "the host", "an analyst") is a claim under L-v; a line may give one only when a cited clip's words do
 341 |  VO_SELF = ("i", "we")                                          # PBX MAX itself: its claims are the verdict's to judge
 342 |  RELATION = re.compile(
 343 |      r"\b(agree[sd]?|agreeing|disagree[sd]?|disagreeing|respond(s|ed|ing)? to|repl(y|ies|ied|ying) to|"
 344 | @@ -477,6 +480,12 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
 345 |          if (fact_numbers(without_manifest_date(text, manifest), meta_nums) or names or quotes or atts or times) \
 346 |                  and not cited:                                       # the 10:48 ruling (3): the show date needs none
 347 |              V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
 348 | +        roles = sorted({w.lower() for w in ROLE_RE.findall(text)})   # 21:10 Nov 14 (Blockware's caption: "a guest")
 349 | +        if roles:
 350 | +            have = {str(x).replace("-", "").rstrip("s") for x in pool}
 351 | +            bad = [w for w in roles if w.replace("-", "").rstrip("s") not in have]
 352 | +            if bad:
 353 | +                V("ROLE", f"gives someone a role the cited clips' own words do not state (law L-v): {bad}")
 354 |          pools = []                                                   # per attribution: the governing segments
 355 |          for subj0, form, _ in atts:
 356 |              subj = _clean_subject(subj0)
 357 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 358 | index 9eeb541..8e556dd 100644
 359 | --- a/tests/package/proof_ledger.py
 360 | +++ b/tests/package/proof_ledger.py
 361 | @@ -147,8 +147,10 @@ def directives(path=None):
 362 |      import re
 363 |      story = re.compile(r"moments-[A-Za-z0-9_]+-[0-9a-f]{8}")         # the pins' own story id form (package_pin.to_pin)
 364 |      return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
 365 | -            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and isinstance(d.get("ends"), str) and d["ends"].strip() and
 366 | -            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and
 367 | +            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and
 368 | +            ((isinstance(d.get("ends"), str) and d["ends"].strip() and "reseal" not in d) or   # a variant, or the SAME
 369 | +             (d.get("reseal") is True and "ends" not in d)) and                             # moment re-sealed (93
 370 | +            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and   # amended + 106)
 371 |              isinstance(d.get("by"), str) and d["by"].strip()}
 372 |  
 373 |  
 374 | diff --git a/tests/package/test_formats.py b/tests/package/test_formats.py
 375 | new file mode 100644
 376 | index 0000000..9cbee31
 377 | --- /dev/null
 378 | +++ b/tests/package/test_formats.py
 379 | @@ -0,0 +1,48 @@
 380 | +#!/usr/bin/env python3
 381 | +"""RULING 93 AMENDED (orchestrator 21:10 ET Nov 14; the integrator's spelling, 21:31): a pin whose clip carries a
 382 | +source caption the 9:16 crop cuts is sealed 16:9-ONLY, moments_package["formats"] = ["16x9"], inside the seal; absent
 383 | +means both formats, and every pin sealed before it recomputes to its own sha. A medley takes the intersection."""
 384 | +import copy
 385 | +import json
 386 | +import os
 387 | +import sys
 388 | +import unittest
 389 | +
 390 | +HERE = os.path.dirname(os.path.abspath(__file__))
 391 | +REPO = os.path.dirname(os.path.dirname(HERE))
 392 | +for _p in ("pipeline", "tests/package"):
 393 | +    sys.path.insert(0, os.path.join(REPO, _p))
 394 | +import package_pin as PP  # noqa: E402
 395 | +import test_angles as TA  # noqa: E402
 396 | +
 397 | +
 398 | +class TestFormats(unittest.TestCase):
 399 | +    def test_a_16x9_only_clip_seals_its_format_and_a_pin_without_one_as_before(self):
 400 | +        base = TA.TestPinAndTruth.pk(None)
 401 | +        plain = PP.to_pin(copy.deepcopy(base), "r")
 402 | +        self.assertNotIn("formats", plain["moments_package"])
 403 | +        self.assertEqual(PP.pin_seal(plain), plain["moments_package"]["package_sha256"])
 404 | +        only = copy.deepcopy(base)
 405 | +        only["segments"][1]["visual"] = dict(only["segments"][1].get("visual") or {}, formats=["16x9"])
 406 | +        pin = PP.to_pin(only, "r")                                        # ONE clip of the medley: the intersection
 407 | +        mp = pin["moments_package"]
 408 | +        self.assertEqual(mp["formats"], ["16x9"])
 409 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])          # the integrator's recompute
 410 | +        self.assertNotEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])
 411 | +        dropped = copy.deepcopy(pin)
 412 | +        del dropped["moments_package"]["formats"]                         # stripping it breaks the seal
 413 | +        self.assertNotEqual(PP.pin_seal(dropped), mp["package_sha256"])
 414 | +
 415 | +    def test_formats_of(self):
 416 | +        self.assertIsNone(PP.formats_of([]))
 417 | +        self.assertIsNone(PP.formats_of([{"visual": {"formats": None}}, {}]))
 418 | +        self.assertEqual(PP.formats_of([{}, {"visual": {"formats": ["16x9"]}}]), ["16x9"])
 419 | +
 420 | +    def test_the_spotlight_now_held_still_recomputes(self):
 421 | +        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
 422 | +        pin = json.load(open(p))
 423 | +        self.assertEqual(PP.pin_seal(pin), pin["moments_package"]["package_sha256"])
 424 | +
 425 | +
 426 | +if __name__ == "__main__":
 427 | +    unittest.main()
 428 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 429 | index 9d8e2ca..af68ac8 100644
 430 | --- a/tests/package/test_medley.py
 431 | +++ b/tests/package/test_medley.py
 432 | @@ -33,6 +33,7 @@ from test_eligibility import NOW, REG, source  # noqa: E402
 433 |  from test_gates import Canned  # noqa: E402
 434 |  from test_moments import pm  # noqa: E402
 435 |  import house_style as HS  # noqa: E402
 436 | +import visual_pin as VP  # noqa: E402
 437 |  
 438 |  W = lambda n: " ".join(["word"] * n)
 439 |  
 440 | @@ -648,7 +649,7 @@ class Rig:
 441 |      def visual(self, router, m, work_dir, cache, seed=7, log=print):
 442 |          """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 443 |          self.visual_calls.append(m["moment_id"])
 444 | -        base = {"version": "visual-2", "measured": True, "flags": [],
 445 | +        base = {"version": VP.VERSION, "measured": True, "flags": [],
 446 |                  "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 447 |                                   "finding": "no third person"},
 448 |                  "on_screen_text": [], "lower_third": {"name": None, "text": None}, "burned_in": [],   # ruling 93
 449 | diff --git a/tests/package/test_role_claims.py b/tests/package/test_role_claims.py
 450 | new file mode 100644
 451 | index 0000000..07fa478
 452 | --- /dev/null
 453 | +++ b/tests/package/test_role_claims.py
 454 | @@ -0,0 +1,58 @@
 455 | +#!/usr/bin/env python3
 456 | +"""The orchestrator, 21:10 ET Nov 14: Blockware's spotlight caption called the channel's own presenter "a guest". "A
 457 | +caption may not assign a role the evidence does not show: 'a guest', 'the host', 'an analyst' are claims under L-v. Fix
 458 | +the writer's instructions and add it to the fidelity gate's checks." Offline."""
 459 | +import os
 460 | +import sys
 461 | +import unittest
 462 | +
 463 | +HERE = os.path.dirname(os.path.abspath(__file__))
 464 | +REPO = os.path.dirname(os.path.dirname(HERE))
 465 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 466 | +import package as PK  # noqa: E402
 467 | +import spotlight as SPOT  # noqa: E402
 468 | +import vo_fidelity as VF  # noqa: E402
 469 | +
 470 | +BLOCKWARE = {"m1": {"show": "Blockware Solutions", "speaker": None, "names": [], "video_id": "7BqLu-wzbU0",
 471 | +                    "text": "On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin."}}
 472 | +MAN = {"channels": ["Blockware Solutions"], "date": "2026-11-14"}
 473 | +
 474 | +
 475 | +def rules(text, slot="caption", segs=BLOCKWARE, cites=("m1",)):
 476 | +    out = VF.check_deterministic(segs, [{"slot": slot, "text": text, "cites": list(cites)}], MAN)
 477 | +    return [x["rule"] for x in out["violations"]]
 478 | +
 479 | +
 480 | +class TestTheFidelityGate(unittest.TestCase):
 481 | +    def test_blockwares_caption_fails_and_the_same_line_without_the_role_passes(self):
 482 | +        self.assertIn("ROLE", rules("a guest sold his retirement stocks for bitcoin and skipped the usual path."))
 483 | +        self.assertNotIn("ROLE", rules("he sold his retirement stocks for bitcoin and skipped the usual path."))
 484 | +
 485 | +    def test_every_role_word_in_every_slot_needs_the_clips_own_words(self):
 486 | +        for line in ("The host sold everything.", "an analyst sold his stocks", "Our guest went all in",
 487 | +                     "A Wall Street strategist sold his IRA", "the co-host bought bitcoin", "Two experts disagree"):
 488 | +            for slot in ("caption", "title", "comment", "closing"):
 489 | +                self.assertIn("ROLE", rules(line, slot), (line, slot))
 490 | +
 491 | +    def test_a_role_the_clip_states_is_no_claim_of_ours(self):
 492 | +        segs = {"m1": {"show": "X", "speaker": None, "names": [], "video_id": "v",
 493 | +                       "text": "I'm an analyst at a big bank and I think bitcoin wins."}}
 494 | +        self.assertNotIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs))
 495 | +        self.assertIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs, cites=()))   # not cited: no source
 496 | +        self.assertIn("ROLE", rules("a guest thinks bitcoin wins", segs=segs))                # another role
 497 | +
 498 | +    def test_words_that_only_contain_a_role_are_not_roles(self):
 499 | +        for line in ("He is hosting nothing.", "Ghosts of the old system.", "Anchoring on old prices fails."):
 500 | +            self.assertNotIn("ROLE", rules(line), line)
 501 | +
 502 | +
 503 | +class TestTheWriters(unittest.TestCase):
 504 | +    def test_both_writers_are_told_never_to_give_a_role(self):
 505 | +        for name, prompt in (("spotlight", SPOT.WRITE_SPOT), ("medley", PK.WRITE_LY)):
 506 | +            self.assertIn("Never give anyone a ROLE", prompt, name)
 507 | +            for word in ('"guest"', '"host"', '"analyst"'):
 508 | +                self.assertIn(word, prompt, (name, word))
 509 | +
 510 | +
 511 | +if __name__ == "__main__":
 512 | +    unittest.main()
 513 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 514 | index 585955a..f129580 100644
 515 | --- a/tests/package/test_ruling_104.py
 516 | +++ b/tests/package/test_ruling_104.py
 517 | @@ -378,3 +378,38 @@ class TestTheDirective(unittest.TestCase):
 518 |          no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]                 # a record without a story id
 519 |          got, _ = SPOT.pool([a, alt, b], {}, ctx, spotlit=no_id, captions_for=caps)
 520 |          self.assertEqual([m["moment_id"] for m in got], ["b"])                   # admits no one
 521 | +
 522 | +
 523 | +RESEAL = {"parent": None, "reseal": True, "alternative_to": "moments-ledger_20261114_230148-3f481f5a",
 524 | +          "by": "orchestrator default 21:4x ET Nov 14 (ruling 106 (a))", "why": "16:9-only under ruling 93 amended"}
 525 | +
 526 | +
 527 | +class TestTheReseal(unittest.TestCase):
 528 | +    """RULING 93 AMENDED with 106 (21:31 Nov 14): the SAME moment sealed again (16:9-only) in the place of its own
 529 | +    earlier story, never as a second spotlight of the channel's day, only on a written directive."""
 530 | +
 531 | +    def setUp(self):
 532 | +        self.d = tempfile.TemporaryDirectory()
 533 | +        self.addCleanup(self.d.cleanup)
 534 | +
 535 | +    def test_the_moment_itself_takes_its_earlier_storys_place(self):
 536 | +        src, m = blockware()
 537 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 538 | +                                          directives={m["moment_id"]: dict(RESEAL, parent=m["moment_id"])})
 539 | +        self.assertEqual((vs, replaced), ([], set()))                         # no variant, nothing replaced
 540 | +        self.assertEqual((m["derived_from"]["reseal_of"], m["derived_from"]["alternative_to"]),
 541 | +                         (RESEAL["alternative_to"],) * 2)
 542 | +        self.assertIn("re-sealed in the place of", notes[m["moment_id"]])
 543 | +        rec = [{"channel_id": "c", "day_et": "2026-11-14", "story_id": RESEAL["alternative_to"]}]
 544 | +        self.assertFalse(SPOT.day_taken(rec, "c", "2026-11-14", m["derived_from"]["alternative_to"]))   # its place
 545 | +        self.assertTrue(SPOT.day_taken(rec + [{"channel_id": "c", "day_et": "2026-11-14", "story_id": "other"}],
 546 | +                                       "c", "2026-11-14", m["derived_from"]["alternative_to"]))   # never a second
 547 | +
 548 | +    def test_the_reseal_directive_is_read_strictly(self):
 549 | +        p = os.path.join(self.d.name, "D.json")
 550 | +        good = dict(RESEAL, parent="06d34e155feae654ee56")
 551 | +        with open(p, "w") as f:
 552 | +            json.dump({"directives": [good, dict(good, parent="1" * 20, reseal="yes"),
 553 | +                                      dict(good, parent="2" * 20, ends="...Roth IRA."),      # both: never guessed
 554 | +                                      dict(good, parent="3" * 20, alternative_to="not-a-story")]}, f)
 555 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": good})
 556 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 557 | index a678b34..e6b4035 100644
 558 | --- a/tests/package/test_spotlight.py
 559 | +++ b/tests/package/test_spotlight.py
 560 | @@ -66,7 +66,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
 561 |               hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
 562 |               hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
 563 |                            "backend": "fake:xai", "replayed": False},
 564 | -             visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 565 | +             visual={"version": VP.VERSION, "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 566 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 567 |                                        "finding": "none"}, "on_screen_text": [],
 568 |                       "lower_third": {"name": None, "text": None}, "burned_in": []},
 569 | @@ -181,7 +181,8 @@ class TestPinContract(unittest.TestCase):
 570 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [], "closing": GOOD["closing"]["text"]})
 571 |          self.assertEqual(mp["vo_jobs"], {"closing": "closing"})
 572 |          self.assertEqual(mp["first_comment"], pk["first_comment"])
 573 | -        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
 574 | +        self.assertEqual(mp["gates"]["spotlight_source"]["format"], "CONVERSATION")   # 21:10 Nov 14: WHICH passed,
 575 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])                      # inside the seal
 576 |          integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
 577 |                               mp["gates"], mp.get("btc_screen"),
 578 |                               **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
 579 | @@ -686,7 +687,7 @@ class TestBuild(unittest.TestCase):
 580 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 581 |                   (SPOT.P, "hook_onset_for", lambda m, s, w, c: onset or {"pass": True, "measured": True}),
 582 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 583 | -                 (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 584 | +                 (VP, "visual_for", lambda r, m, w, c: dict({"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [],
 585 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 586 |                   (SPOT, "layout_for", lambda r, m, v, c, **k: (calls.setdefault("layout", []).append(
 587 |                       (m["moment_id"], k.get("evidence"))), {"measured": True, "layout": layout, "why": "w"})[1]),
 588 | @@ -773,9 +774,13 @@ class TestBuild(unittest.TestCase):
 589 |          out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [strap], "flags": [
 590 |              {"kind": "burned_in", "text": "BILL MILLER IV", "item": "lower_third", "in_9x16": "out"}]})
 591 |          self.assertEqual(calls["package_for"], ["a"])                   # eligible, flagged, still clean
 592 | -        self.assertTrue(SPOT.clean_visual({"measured": True, "burned_in": [strap], "flags": [
 593 | +        cap = {"kind": "caption", "text": "SOLD MY ROTH IRA", "whole_in_16x9": True, "in_9x16": "whole",
 594 | +               "covers_speaker": False, "at": [3.27]}                       # ruling 93 amended: a source caption is
 595 | +        self.assertTrue(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [cap], "flags": [
 596 | +            {"kind": "burned_caption", "text": "SOLD MY ROTH IRA", "in_9x16": "whole", "at": [3.27]}]}))   # flagged, clean
 597 | +        self.assertTrue(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [strap], "flags": [
 598 |              {"kind": "burned_in", "text": "BILL MILLER IV"}]}))
 599 | -        self.assertFalse(SPOT.clean_visual({"measured": True, "burned_in": [], "flags": [
 600 | +        self.assertFalse(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [], "flags": [
 601 |              {"kind": "on_screen_text", "text": "SCANDAL"}]}))           # a ruling-70 flag is not clean
 602 |          self.assertFalse(SPOT.clean_visual({"measured": True, "flags": []}))       # no question 4: never
 603 |  
 604 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 605 | index 82c682c..93b4406 100644
 606 | --- a/tests/package/test_visual_pin.py
 607 | +++ b/tests/package/test_visual_pin.py
 608 | @@ -7,6 +7,7 @@ import os
 609 |  import sys
 610 |  import tempfile
 611 |  import unittest
 612 | +from unittest import mock
 613 |  
 614 |  HERE = os.path.dirname(os.path.abspath(__file__))
 615 |  REPO = os.path.dirname(os.path.dirname(HERE))
 616 | @@ -33,9 +34,13 @@ class VFake(Fake):
 617 |  
 618 |  
 619 |  class TestContract(unittest.TestCase):
 620 | -    def test_the_stills_are_the_cut_in_one_every_two_seconds_and_the_last(self):
 621 | -        self.assertEqual(VP.times(16.62), [0.0, 2.37, 4.73, 7.1, 9.47, 11.84, 14.2, 16.57])   # evenly spaced
 622 | -        self.assertEqual(VP.times(5.0), [0.0, 2.0, 4.0, 4.95])
 623 | +    def test_the_stills_are_the_cut_in_one_every_second_and_the_last(self):    # 21:10 Nov 14: >= 1 frame a second
 624 | +        self.assertEqual(VP.times(5.0), [0.0, 1.0, 2.0, 3.0, 4.0, 4.95])
 625 | +        for dur in (5.0, 12.3, 16.62, 22.94, 35.0):                       # every span up to the 35 s ceiling
 626 | +            ts = VP.times(dur)
 627 | +            self.assertEqual((ts[0], ts[-1]), (0.0, round(dur - 0.05, 2)), dur)
 628 | +            self.assertLessEqual(max(b - a for a, b in zip(ts, ts[1:])), 1.0 + 1e-9, dur)
 629 | +        self.assertEqual(len(VP.times(22.94)), 24)                        # Blockware: 24 frames, not 8
 630 |          self.assertEqual(len(VP.times(60.0)), VP.TILES)
 631 |  
 632 |      def test_a_reply_in_contract_and_out_of_it(self):
 633 | @@ -67,7 +72,7 @@ class TestContract(unittest.TestCase):
 634 |      def test_ruling_93_burned_in_text_per_clip(self):
 635 |          item = lambda kind, **k: dict({"kind": kind, "text": "BITCOIN 74,512 | ETH 2,410", "whole_in_16x9": True,
 636 |                                         "in_9x16": "out", "covers_speaker": False}, **k)
 637 | -        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True)
 638 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
 639 |          self.assertIsNone(VP.layout_block(rec()))                                       # nothing burned in
 640 |          for kind in ("ticker", "crawl"):                                                # a ticker or crawl: never
 641 |              self.assertIn(f"a {kind}", VP.layout_block(rec(item(kind))))
 642 | @@ -90,8 +95,40 @@ class TestContract(unittest.TestCase):
 643 |          many = [dict(strap, text=f"strap {i}", in_9x16="out") for i in range(VP.TEXTS_MAX + 3)] + [item("ticker")]
 644 |          v = VP.check(dict(CLEAN, burned_in=many))                                       # the ticker listed last
 645 |          self.assertEqual((len(v["burned_in"]), v["burned_in_truncated"]), (VP.TEXTS_MAX, 4))
 646 | -        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True)))            # is never cut away
 647 | -        self.assertEqual(VP.VERSION, "visual-2")                                        # every clip asked again
 648 | +        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True, version=VP.VERSION)))   # never cut away
 649 | +        self.assertEqual(VP.VERSION, "visual-3")                                        # every clip asked again
 650 | +
 651 | +    def test_ruling_93_amended_the_sources_burned_captions(self):
 652 | +        """21:10 Nov 14: Blockware's captions ('SOLD MY ROTH IRA', '26 NO ROTH IRA NO 401K') were on the sheet, and
 653 | +        visual-2's question told the model to leave subtitles out. A caption never makes a clip ineligible; cut by the
 654 | +        9:16 it makes the clip 16:9-ONLY, held until the integrator's render can pass a 16:9-only pin."""
 655 | +        q4 = VP.PROMPT.split("4. burned_in:")[1]
 656 | +        self.assertNotIn("Not subtitles of the spoken words", q4)            # the cause, gone
 657 | +        for words in ("BURNED-IN CAPTIONS", '"caption"', "EVERY frame", "face"):
 658 | +            self.assertIn(words, q4)
 659 | +        cap = lambda text, cut, at=(16.35, 19.62): {"kind": "caption", "text": text, "whole_in_16x9": True,
 660 | +                                                   "in_9x16": cut, "covers_speaker": False, "at": list(at)}
 661 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
 662 | +        blockware = rec(cap("SOLD MY ROTH IRA", "cut", (3.27,)), cap("26 NO ROTH IRA NO 401K", "cut"))
 663 | +        self.assertEqual(VP.formats(blockware), ["16x9"])
 664 | +        self.assertEqual([f["kind"] for f in VP.flags(blockware)], ["burned_caption", "burned_caption"])
 665 | +        self.assertEqual(VP.flags(blockware)[1]["at"], [16.35, 19.62])
 666 | +        self.assertIn("16:9-only", VP.layout_block(blockware))               # held while the render cannot pass it
 667 | +        self.assertNotIn("ticker", VP.layout_block(blockware))
 668 | +        with mock.patch.object(VP, "RENDER_16X9_ONLY", True):
 669 | +            self.assertIsNone(VP.layout_block(blockware))                    # then eligible, 16:9 only
 670 | +            self.assertEqual(VP.formats(blockware), ["16x9"])
 671 | +        whole = rec(cap("FINANCIALLY INDEPENDENT BY 45", "whole"))
 672 | +        self.assertIsNone(VP.formats(whole))                                 # a crop shows it whole: both formats
 673 | +        self.assertIsNone(VP.layout_block(whole))
 674 | +        self.assertIsNone(VP.formats(dict(blockware, measured=False)))
 675 | +        self.assertEqual(VP.sealed(dict(blockware, formats=VP.formats(blockware)))["formats"], ["16x9"])
 676 | +        for bad in ([dict(cap("x", "cut"), text="")], [dict(cap("x", "cut"), at="16.35")],
 677 | +                    [dict(cap("x", "cut"), at=["16.35"])]):
 678 | +            with self.assertRaises(ValueError):                             # a caption with no words, or bad times
 679 | +                VP.check(dict(CLEAN, burned_in=bad))
 680 | +        old = dict(blockware, version="visual-2")
 681 | +        self.assertIn("never asked for the source's burned captions", VP.layout_block(old))
 682 |  
 683 |      def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 684 |          class R:
 685 | 
```

---

pp-selectid: THE ORCHESTRATOR'S THREE FIXES OF 21:10 ET Nov 14, plus the sealed "formats" and the re-seal directive.

THE ORCHESTRATOR (21:10): "1. THE VISUAL CHECK MISSED BURNED-IN CAPTIONS ... sample at least one frame a second across
the span, and ask explicitly for burned-in captions / subtitles. RULING 93 AMENDED: source-burned captions that the 9:16
crop cuts mid-word make the clip 16:9-ONLY (sealed as formats: ['16x9'], the integrator renders and delivers that format
alone) unless a crop exists that shows them whole; they do not make the clip ineligible. 2. THE CAPTION SAYS 'a guest'
... A caption may not assign a role the evidence does not show: 'a guest', 'the host', 'an analyst' are claims under
L-v. Fix the writer's instructions and add it to the fidelity gate's checks. 3. ... record on the pin WHICH of
CONVERSATION / FIRST_HAND passed."
THE INTEGRATOR (21:2x and 21:31):
- Its render cannot yet pass a 16:9-only pin, so none is sealed until its format-aware release lands.
- Its crop slides only while the speaker's face stays inside.
- The spelling: moments_package["formats"] = ["16x9"], inside the seal; absent means both.

ROOT CAUSE of the miss: the sheet's 8 frames DID show Blockware's captions. Visual-2's question told the model, twice,
to leave out "subtitles of the spoken words", so it reported none.

THE CHANGE:
- pipeline/visual_pin.py, VERSION "visual-3":
  - frames: TILES 40, EVERY_S 1.0, 6 columns of 320 px, so no gap exceeds a second (times() also keeps the last
    frame within a second);
  - question 4 asks for the source's own burned CAPTIONS (kind "caption", with "at" frame times), with the face-safe
    crop rule;
  - burned_block: a caption never makes a clip ineligible;
  - formats(): ["16x9"] when a caption is "cut";
  - layout_block: holds a 16:9-only clip while RENDER_16X9_ONLY is False, and holds a record of another VERSION;
  - flags: "burned_caption"; sealed() carries "formats".
- pipeline/spotlight.py:
  - clean_visual ignores "burned_caption" flags;
  - the spotlight_source gate row carries "format": "CONVERSATION" | "FIRST_HAND" (sealed in the gates);
  - WRITE_SPOT's RULES gain the role rule.
- pipeline/package.py: WRITE_LY's RULES gain the role rule.
- pipeline/vo_fidelity.py: check_deterministic gains rule "ROLE". A line naming a role (guest, host, co-host,
  analyst, expert, economist, strategist, interviewer, presenter, anchor, panelist, commentator) fails unless a CITED
  clip's own words state that role.
- pipeline/package_pin.py:
  - formats_of(segments) (the intersection);
  - seal(..., formats=None) puts it in the body only when present;
  - pin_seal passes it;
  - to_pin seals moments_package["formats"].
- pipeline/tail_variant.py + tests/package/proof_ledger.py: a directive {"parent", "reseal": true,
  "alternative_to", "by", "why"} marks the SAME moment (no variant) as re-sealed in the place of its own earlier
  story. spotlight.day_taken then lets it take that story's place for the day, and only that one. A row with both
  "ends" and "reseal", or a reseal that is not exactly true, is dropped.
- Tests: test_visual_pin, test_spotlight, test_role_claims (new), test_formats (new), test_ruling_104, test_medley
  (fixture version).

UNCHANGED GUARDS: spotlight.day_taken excludes only the named story's own record. Every other record of the
channel's day still takes the place. The visual cache key includes VERSION and the sheet's parameters, so visual-2
verdicts are never reused. check_pin_only (the integrator's) recomputes through pin_seal.

PLEASE CHECK:
(1) Can a 16:9-only clip be sealed while RENDER_16X9_ONLY is False?
(2) Can the ROLE rule pass a role no cited clip states, or refuse a sentence with no role word?
(3) Does "formats" change any existing pin's recompute?
(4) Can a reseal directive create a second spotlight for a channel's day?
(5) Do the tests pin each piece? The mutation results are in the consensus file.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
