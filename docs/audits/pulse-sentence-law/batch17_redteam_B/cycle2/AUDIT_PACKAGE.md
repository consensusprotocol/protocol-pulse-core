# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 23:40 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (473 lines)
```
   1 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
   2 | index f6cbdc63..d5efaf8b 100644
   3 | --- a/pipeline/story_semantics.py
   4 | +++ b/pipeline/story_semantics.py
   5 | @@ -23,6 +23,7 @@ Identity rules (nothing lexical stands in for semantics):
   6 |  import gc
   7 |  import hashlib
   8 |  import json
   9 | +import math
  10 |  import os
  11 |  import re
  12 |  import subprocess
  13 | @@ -398,11 +399,64 @@ Return ONLY JSON with keys:
  14 |  "rationale": one sentence}}"""
  15 |  
  16 |  
  17 | +def _field(o, key, kind, allowed=None, nonempty=False, lo=None, hi=None, optional=False):
  18 | +    """One field of a model reply, strictly (red-team B): exact type (an int is never a bool or a string; an
  19 | +    integral float such as 5.0 counts as an int), an enumerated value (compared, and written back, stripped and
  20 | +    lower-case: 'Current' is 'current'), a non-empty string, a finite number in range. optional: an absent / null
  21 | +    field is accepted (a reason no decision reads). Raises ValueError: the call failed."""
  22 | +    if not isinstance(o, dict):
  23 | +        raise ValueError("reply is not a JSON object")
  24 | +    v = o.get(key)
  25 | +    if optional and v is None:
  26 | +        return None
  27 | +    if kind == "int" and type(v) is float and math.isfinite(v) and v == int(v):
  28 | +        v = o[key] = int(v)
  29 | +    if allowed is not None and isinstance(v, str):
  30 | +        v = o[key] = v.strip().lower()
  31 | +    # type(), not isinstance(): bool is a subclass of int, so isinstance(True, int) would accept True as 1
  32 | +    ok = {"int": type(v) is int, "bool": type(v) is bool, "str": isinstance(v, str), "list": isinstance(v, list),
  33 | +          "num": type(v) in (int, float) and math.isfinite(v)}[kind]      # NaN / inf never pass (batch 17 audit #1)
  34 | +    if not ok:
  35 | +        raise ValueError(f"{key} must be {kind}, got {type(v).__name__}")
  36 | +    if allowed is not None and v not in allowed:
  37 | +        raise ValueError(f"{key} {v!r} not in {allowed}")
  38 | +    if nonempty and not (v.strip() if isinstance(v, str) else v):
  39 | +        raise ValueError(f"{key} is empty")
  40 | +    if (lo is not None and v < lo) or (hi is not None and v > hi):
  41 | +        raise ValueError(f"{key} {v!r} outside [{lo}, {hi}]")
  42 | +    return v
  43 | +
  44 | +
  45 | +def _str_list(o, key, nonempty=False):
  46 | +    """A list of strings; nonempty: at least one, and no empty string in it."""
  47 | +    v = _field(o, key, "list")
  48 | +    if not all(isinstance(x, str) and (x.strip() or not nonempty) for x in v) or (nonempty and not v):
  49 | +        raise ValueError(f"{key} must be a list of {'non-empty ' if nonempty else ''}strings")
  50 | +
  51 | +
  52 | +EVENT_DATE = re.compile(r"unknown|(19|20)\d{2}(-\d{2}(-\d{2})?)?")   # the forms the prompts ask for
  53 | +
  54 | +
  55 |  def _v_derive(o):
  56 | -    for k in ("underlying_event", "bitcoin_relevance", "importance"):
  57 | -        if k not in o:
  58 | -            raise ValueError(f"missing {k}")
  59 | -    int(o["bitcoin_relevance"]), int(o["importance"])
  60 | +    """Every field a decision reads: the event, its Bitcoin relevance and importance (the screen and the ranking),
  61 | +    its date and recency (currentness), the entities / action / object / confusables (adjudication context)."""
  62 | +    _field(o, "underlying_event", "str", nonempty=True)
  63 | +    _field(o, "bitcoin_relevance", "int", lo=0, hi=5)
  64 | +    _field(o, "importance", "int", lo=0, hi=5)
  65 | +    if not EVENT_DATE.fullmatch(_field(o, "event_date", "str", nonempty=True).strip()):
  66 | +        raise ValueError(f"event_date {o['event_date']!r} is not YYYY-MM-DD / YYYY-MM / YYYY / unknown")
  67 | +    _field(o, "event_recency", "str", allowed=("current", "recent", "historical"))
  68 | +    _field(o, "action", "str")
  69 | +    _field(o, "affected_object", "str")
  70 | +    ents = _field(o, "entities", "list")
  71 | +    for e in ents:
  72 | +        if isinstance(e, dict) and e.get("aliases") is None:
  73 | +            e["aliases"] = []                       # a null aliases list is an empty one
  74 | +    if not all(isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()
  75 | +               and isinstance(e["aliases"], list) for e in ents):
  76 | +        raise ValueError("entities must be objects with a name and an aliases list")
  77 | +    _str_list(o, "must_not_confuse_with")
  78 | +    _str_list(o, "concepts")
  79 |  
  80 |  
  81 |  CLUSTER_NOTE = ("This item is a development several Bitcoin channels state in common (DEC-13): underlying_event "
  82 | @@ -588,13 +642,26 @@ Return ONLY JSON: {{"quote_actor": who acts in the quote ("unstated" if nobody i
  83 |  
  84 |  
  85 |  def _v_adj(o):
  86 | -    if o.get("verdict") not in VERDICTS:
  87 | -        raise ValueError(f"verdict {o.get('verdict')!r} not in {VERDICTS}")
  88 | +    """A positive verdict must carry its evidence: supporting chunk ids and a quote (claude-fable B #4)."""
  89 | +    positive = _field(o, "verdict", "str", allowed=tuple(v.lower() for v in VERDICTS)) == "current_event"
  90 | +    o["verdict"] = o["verdict"].upper()           # the canonical label form
  91 | +    _str_list(o, "supporting_chunk_ids", nonempty=positive)
  92 | +    _field(o, "evidence_quote", "str", nonempty=positive)
  93 | +    _field(o, "confidence", "num", lo=0, hi=1)
  94 | +    _field(o, "reason", "str", optional=True)
  95 | +
  96 | +
  97 | +SUPPORT_PRESENTED = ("current", "past", "unclear")
  98 |  
  99 |  
 100 |  def _v_sup(o):
 101 | -    if o.get("support") not in SUPPORT:
 102 | -        raise ValueError(f"support {o.get('support')!r} not in {SUPPORT}")
 103 | +    """GPT-select F01: the fields that decide SUPPORTS are required and typed (a missing same_actor_action_object
 104 | +    or presented_as was read as agreement)."""
 105 | +    _field(o, "support", "str", allowed=tuple(x.lower() for x in SUPPORT))
 106 | +    o["support"] = o["support"].upper()            # the canonical label form
 107 | +    _field(o, "same_actor_action_object", "bool")
 108 | +    _field(o, "presented_as", "str", allowed=SUPPORT_PRESENTED)
 109 | +    _field(o, "reason", "str", optional=True)
 110 |  
 111 |  
 112 |  def _entities_str(q):
 113 | @@ -629,8 +696,9 @@ Return ONLY JSON: {{"label": one of the three, "reason": one sentence}}"""
 114 |  
 115 |  
 116 |  def _v_react(o):
 117 | -    if o.get("label") not in REACTION_LABELS:
 118 | -        raise ValueError(f"label {o.get('label')!r} not in {REACTION_LABELS}")
 119 | +    _field(o, "label", "str", allowed=tuple(x.lower() for x in REACTION_LABELS))
 120 | +    o["label"] = o["label"].upper()
 121 | +    _field(o, "reason", "str", optional=True)
 122 |  
 123 |  
 124 |  def verify_reaction(llm, q, anchor, sentence):
 125 | @@ -646,11 +714,13 @@ def verify_support(llm, q, quote):
 126 |                                obj=q.get("affected_object", "-"), entities=_entities_str(q),
 127 |                                note=UNTRUSTED_NOTE, quote=quote_data(quote, 600))
 128 |      s = llm.chat_json(p, max_tokens=350, validate=_v_sup)
 129 | -    if s["support"] == "SUPPORTS":       # the structured fields must agree with the label
 130 | -        if s.get("same_actor_action_object") is False:
 131 | -            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is false"
 132 | -        elif str(s.get("presented_as", "")).lower() == "past":
 133 | +    if s["support"] == "SUPPORTS":       # the structured fields must AGREE with the label (fail closed: GPT-select F01)
 134 | +        if s["same_actor_action_object"] is not True:
 135 | +            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is not true"
 136 | +        elif s["presented_as"] == "past":
 137 |              s["support"], s["downgraded"] = "BACKGROUND", "presented_as past"
 138 | +        elif s["presented_as"] != "current":
 139 | +            s["support"], s["downgraded"] = "INCONCLUSIVE", f"presented_as {s['presented_as']}"
 140 |      return s
 141 |  
 142 |  
 143 | @@ -738,8 +808,14 @@ def emergent_clusters(chunks, vecs, min_channels=3, threshold=0.22, max_clusters
 144 |  
 145 |  
 146 |  def _v_label(o):
 147 | -    if not isinstance(o.get("is_specific_event"), bool):
 148 | -        raise ValueError("is_specific_event must be boolean")
 149 | +    """A specific event must come with everything the current-development check reads."""
 150 | +    if _field(o, "is_specific_event", "bool"):
 151 | +        _field(o, "headline", "str", nonempty=True)
 152 | +        if not EVENT_DATE.fullmatch(_field(o, "event_date", "str", nonempty=True).strip()):
 153 | +            raise ValueError(f"event_date {o['event_date']!r} is not YYYY-MM-DD / YYYY-MM / YYYY / unknown")
 154 | +        _field(o, "current_development_quote", "str", nonempty=True)
 155 | +        _field(o, "current_development_chunk_id", "str", nonempty=True)
 156 | +        _str_list(o, "member_chunk_ids", nonempty=True)
 157 |  
 158 |  
 159 |  def label_cluster(llm, chunks, vecs, group, today, k=8):
 160 | @@ -805,9 +881,24 @@ Return ONLY JSON: {{"ratings": [{{"id": passage id, "score": 1-5, "fault": one o
 161 |  BOUNDARY_FAULTS = ("starts_mid_thought", "ends_mid_thought")   # D3: the only faults a repair may address
 162 |  
 163 |  
 164 | -def _v_rate(o):
 165 | -    if not isinstance(o.get("ratings"), list):
 166 | -        raise ValueError("ratings must be a list")
 167 | +RATE_FAULTS = BOUNDARY_FAULTS + ("none", "off_topic", "other")
 168 | +
 169 | +
 170 | +def _v_rate(o, ids=None):
 171 | +    """GPT-select F12: a score outside 1-5 or not a number, an unknown fault, a duplicate or unknown passage id, or
 172 | +    (with ids) a passage left unrated is a failed call; it is never clamped into a perfect score."""
 173 | +    seen = set()
 174 | +    for x in _field(o, "ratings", "list"):
 175 | +        if not isinstance(x, dict):                   # an entry that is not an object is a failed call (audit #2)
 176 | +            raise ValueError("a rating is not an object")
 177 | +        pid = str(_field(x, "id", "str") if isinstance(x.get("id"), str) else _field(x, "id", "int"))
 178 | +        _field(x, "score", "num", lo=1, hi=5)
 179 | +        _field(x, "fault", "str", allowed=RATE_FAULTS)              # stripped / lower-cased before the check
 180 | +        if pid in seen or (ids is not None and pid not in ids):
 181 | +            raise ValueError(f"rating id {pid!r} duplicate or unknown")
 182 | +        seen.add(pid)
 183 | +    if ids is not None and seen != set(ids):
 184 | +        raise ValueError(f"unrated passages: {sorted(set(ids) - seen)[:5]}")
 185 |  
 186 |  
 187 |  def rate_passages(llm, q, passages):
 188 | @@ -816,19 +907,15 @@ def rate_passages(llm, q, passages):
 189 |      ex = "\n".join(f'<excerpt id="{p["pid"]}" channel="{p["channel"]}" seconds="{p["duration"]:.0f}">'
 190 |                     f'{quote_data(p["text"], 700)}</excerpt>' for p in passages)
 191 |      try:
 192 | +        ids = {str(p["pid"]) for p in passages}
 193 |          r = llm.chat_json(CLIP_PROMPT.format(event=q.get("underlying_event", ""), note=UNTRUSTED_NOTE,
 194 | -                                             passages=ex), max_tokens=1200, validate=_v_rate)
 195 | +                                             passages=ex), max_tokens=1200, validate=lambda o: _v_rate(o, ids))
 196 |      except LLMParseError as e:
 197 |          return {}, {"error": str(e), "llm_attempts": e.attempts}
 198 |      out = {}
 199 | -    valid = {p["pid"] for p in passages}
 200 | -    for x in r.get("ratings", []) or []:
 201 | -        try:
 202 | -            pid = str(x["id"])
 203 | -            if pid in valid:
 204 | -                fault = x.get("fault") if x.get("fault") in BOUNDARY_FAULTS + ("none", "off_topic", "other") \
 205 | -                    else "unspecified"
 206 | -                out[pid] = (max(1.0, min(5.0, float(x["score"]))), x.get("reason", ""), fault)
 207 | -        except Exception:
 208 | -            pass
 209 | +    by_id = {str(p["pid"]): p["pid"] for p in passages}   # one normalisation for validation and output (audit #3)
 210 | +    for x in r["ratings"]:                          # validated: every passage once, score 1-5, a known fault
 211 | +        pid = str(x["id"])
 212 | +        if pid in by_id:
 213 | +            out[by_id[pid]] = (float(x["score"]), str(x.get("reason", "")), x["fault"])
 214 |      return out, None
 215 | diff --git a/pipeline/test_caption_entities.py b/pipeline/test_caption_entities.py
 216 | index 09b15c3f..cdf2f9e5 100644
 217 | --- a/pipeline/test_caption_entities.py
 218 | +++ b/pipeline/test_caption_entities.py
 219 | @@ -105,8 +105,13 @@ class TestClusterClaimIsTheEvent(unittest.TestCase):
 220 |  
 221 |          def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 222 |              self.prompts.append(prompt)
 223 | -            return {"underlying_event": "The US held its general elections on November 8th, 2026.",
 224 | -                    "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin"}
 225 | +            obj = {"underlying_event": "The US held its general elections on November 8th, 2026.",
 226 | +                   "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin",
 227 | +                   "event_date": "2026-11-08", "event_recency": "current", "entities": [], "concepts": [],
 228 | +                   "must_not_confuse_with": []}
 229 | +            if validate:
 230 | +                validate(obj)
 231 | +            return obj
 232 |  
 233 |      def test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged(self):
 234 |          claim = "Following the US elections, Bitcoin experienced a sell-off and net outflows from US Bitcoin ETFs."
 235 | diff --git a/pipeline/test_editorial_robust.py b/pipeline/test_editorial_robust.py
 236 | index 59a1c282..5c8506cf 100644
 237 | --- a/pipeline/test_editorial_robust.py
 238 | +++ b/pipeline/test_editorial_robust.py
 239 | @@ -229,8 +229,14 @@ class TestQuoteAnchoredWindows(unittest.TestCase):
 240 |                  self.score = score
 241 |  
 242 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 243 | -                return {"ratings": [{"id": i, "score": self.score, "reason": "start at 0.0 instead"}
 244 | -                                    for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 245 | +                if prompt.startswith("You check ONE SENTENCE"):        # the adjacent-sentence verifier: a new subject
 246 | +                    reply = {"label": "NEW_SUBJECT", "reason": "fake"}
 247 | +                else:
 248 | +                    reply = {"ratings": [{"id": i, "score": self.score, "fault": "none", "reason": "start at 0.0 instead"}
 249 | +                                         for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 250 | +                if validate:
 251 | +                    validate(reply)
 252 | +                return reply
 253 |          c = {"query": RUN3["binance"]["query"], "headline": RUN3["binance"]["headline"]}
 254 |          cq = es._clip_quality(c, same, FakeEmbedder(), Rater(5), reg, words, log=lambda s: None)
 255 |          self.assertTrue(any("deduped" in str(x) for a in cq["anchors"] for x in a.get("windows", {}).values()), cq["anchors"])
 256 | @@ -279,10 +285,100 @@ class ScriptedLLM(sm.LocalLLM):
 257 |  
 258 |  class TestMalformedLLM(unittest.TestCase):
 259 |      def test_retry_then_valid(self):
 260 | -        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}', '```json\n{"support": "SUPPORTS",}\n```'])
 261 | +        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}',
 262 | +                           '```json\n{"support": "SUPPORTS", "same_actor_action_object": true, "presented_as": "current", '
 263 | +                           '"reason": "r",}\n```'])
 264 |          self.assertEqual(llm.chat_json("p", validate=sm._v_sup)["support"], "SUPPORTS")
 265 |          self.assertEqual(llm.calls, 2)
 266 |  
 267 | +    def test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call(self):
 268 | +        """Red-team B (GPT-select F01 / F11 / F12; batch 17 audits): ONE defect per case on an otherwise valid reply,
 269 | +        so each case proves its own rule; the valid bases themselves pass."""
 270 | +        import copy
 271 | +        bases = {
 272 | +            "sup": (sm._v_sup, {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current",
 273 | +                                "reason": "r"}),
 274 | +            "adj": (sm._v_adj, {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["AAA:0-1"], "evidence_quote": "q q q",
 275 | +                                "confidence": 0.9, "reason": "r"}),
 276 | +            "derive": (sm._v_derive, {"underlying_event": "x", "bitcoin_relevance": 5, "importance": 3,
 277 | +                                      "event_date": "2026-11-10", "event_recency": "current", "action": "a",
 278 | +                                      "affected_object": "b", "entities": [{"name": "n", "aliases": []}],
 279 | +                                      "must_not_confuse_with": [], "concepts": []}),
 280 | +            "label": (sm._v_label, {"is_specific_event": True, "headline": "h", "event_date": "2026-11",
 281 | +                                    "current_development_quote": "q", "current_development_chunk_id": "c",
 282 | +                                    "member_chunk_ids": ["c"]}),
 283 | +            "rate": (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 4, "fault": "none"},
 284 | +                                                                       {"id": "p1", "score": 2.5, "fault": "off_topic"}]}),
 285 | +        }
 286 | +        for name, (v, base) in bases.items():
 287 | +            v(copy.deepcopy(base))                                                     # the base is valid
 288 | +        defects = [
 289 | +            ("sup", lambda o: o.pop("same_actor_action_object")), ("sup", lambda o: o.pop("presented_as")),
 290 | +            ("sup", lambda o: o.__setitem__("same_actor_action_object", "true")),
 291 | +            ("adj", lambda o: o.__setitem__("supporting_chunk_ids", "AAA:0-1")),
 292 | +            ("adj", lambda o: o.__setitem__("supporting_chunk_ids", [])),             # positive without evidence
 293 | +            ("adj", lambda o: o.__setitem__("evidence_quote", "")),
 294 | +            ("adj", lambda o: o.__setitem__("confidence", float("nan"))),
 295 | +            ("derive", lambda o: o.__setitem__("bitcoin_relevance", True)),           # a bool is not an int
 296 | +            ("derive", lambda o: o.__setitem__("importance", 7)),
 297 | +            ("derive", lambda o: o.__setitem__("event_date", "n/a")),
 298 | +            ("label", lambda o: o.pop("current_development_quote")),
 299 | +            ("label", lambda o: o.__setitem__("member_chunk_ids", [])),
 300 | +            ("label", lambda o: o.__setitem__("member_chunk_ids", [""])),
 301 | +            ("rate", lambda o: o["ratings"][0].__setitem__("score", 9)),
 302 | +            ("rate", lambda o: o["ratings"][0].__setitem__("score", float("nan"))),
 303 | +            ("rate", lambda o: o["ratings"].pop()),                                   # a passage left unrated
 304 | +            ("rate", lambda o: o["ratings"].append(dict(o["ratings"][0]))),           # a duplicate id
 305 | +            ("rate", lambda o: o["ratings"].__setitem__(0, "p0")),                    # an entry that is not an object
 306 | +            ("rate", lambda o: o["ratings"][0].__setitem__("fault", "great")),
 307 | +        ]
 308 | +        for name, fn in defects:
 309 | +            v, base = bases[name]
 310 | +            o = copy.deepcopy(base)
 311 | +            fn(o)
 312 | +            with self.assertRaises(ValueError, msg=f"{name}: {o}"):
 313 | +                v(o)
 314 | +
 315 | +    def test_harmless_variations_are_accepted(self):
 316 | +        """claude-fable B #5: case, an integral float, a null aliases list or a missing reason are not failures."""
 317 | +        o = {"support": "Supports", "same_actor_action_object": True, "presented_as": "Current"}
 318 | +        sm._v_sup(o)
 319 | +        self.assertEqual((o["support"], o["presented_as"]), ("SUPPORTS", "current"))
 320 | +        d = {"underlying_event": "x", "bitcoin_relevance": 5.0, "importance": 3, "event_date": "unknown",
 321 | +             "event_recency": "Current", "action": "a", "affected_object": "b", "entities": [{"name": "n", "aliases": None}],
 322 | +             "must_not_confuse_with": [], "concepts": []}
 323 | +        sm._v_derive(d)
 324 | +        self.assertEqual((d["bitcoin_relevance"], d["entities"][0]["aliases"]), (5, []))
 325 | +
 326 | +    def test_an_invalid_reply_through_the_real_call_is_inconclusive_never_counted(self):
 327 | +        """The whole path: a support reply without its deciding fields, every attempt, through the REAL chat_json
 328 | +        (ScriptedLLM) and adjudicate: not counted, INCONCLUSIVE with the attempts recorded."""
 329 | +        adj = json.dumps({"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["AAAAAAAAAAA:0-1000"],
 330 | +                          "evidence_quote": "some text here and more words", "confidence": 0.9, "reason": "r"})
 331 | +        llm = ScriptedLLM([adj] + ['{"support": "SUPPORTS", "reason": "r"}'] * 3)
 332 | +        v = sm.adjudicate(llm, {"underlying_event": "x"}, {"title": "t", "channel": "c"},
 333 | +                          [{"chunk_id": "AAAAAAAAAAA:0-1000", "text": "some text here and more words"}])
 334 | +        self.assertFalse(v["counted_as_same_event"])
 335 | +        self.assertEqual(v["support"], "INCONCLUSIVE")
 336 | +        self.assertEqual(len(v["support_error"]["llm_attempts"]), 3)
 337 | +
 338 | +    def test_supports_needs_both_deciding_fields_exactly(self):
 339 | +        class One:
 340 | +            model, calls = "fake", 0
 341 | +
 342 | +            def __init__(self, reply):
 343 | +                self.reply = reply
 344 | +
 345 | +            def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 346 | +                if validate:
 347 | +                    validate(self.reply)
 348 | +                return dict(self.reply)
 349 | +        base = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "r"}
 350 | +        self.assertEqual(sm.verify_support(One(base), {"underlying_event": "x"}, "q")["support"], "SUPPORTS")
 351 | +        for change, want in (({"same_actor_action_object": False}, "TOPIC_ONLY"), ({"presented_as": "past"}, "BACKGROUND"),
 352 | +                             ({"presented_as": "unclear"}, "INCONCLUSIVE")):
 353 | +            self.assertEqual(sm.verify_support(One({**base, **change}), {"underlying_event": "x"}, "q")["support"], want)
 354 | +
 355 |      def test_bounded_and_recorded(self):
 356 |          llm = ScriptedLLM(["not json", '{"verdict": "MAYBE"}', '{"verdict": '])
 357 |          with self.assertRaises(sm.LLMParseError) as cm:
 358 | @@ -348,27 +444,39 @@ class FakeLLM:
 359 |              if "PARSEFAIL" in h:
 360 |                  raise sm.LLMParseError("no valid JSON after 3 attempts",
 361 |                                         [{"attempt": i + 1, "error": "bad", "raw": "{oops"} for i in range(3)])
 362 | -            return {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 363 | +            return self._ok(validate, {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 364 |                      "event_recency": self.model_recency, "entities": [{"name": "Congress", "aliases": ["midterms", "Senate"]}],
 365 |                      "action": "flip", "affected_object": "Congress", "concepts": ["midterms", "Congress"],
 366 | -                    "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True}
 367 | +                    "must_not_confuse_with": [], "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True})
 368 |          if prompt.startswith("You verify whether"):
 369 |              self.adj += 1
 370 |              if self.crash and self.adj == self.crash:
 371 |                  raise RuntimeError("boom (simulated crash)")
 372 |              m = re.search(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 373 |              words = m.group(2).split()[:10]
 374 | -            return {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 375 | -                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"}
 376 | +            return self._ok(validate, {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 377 | +                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"})
 378 |          if prompt.startswith("Decide whether a QUOTE"):
 379 | -            return {"support": "SUPPORTS", "reason": "fake"}
 380 | +            return self._ok(validate, {"support": "SUPPORTS", "same_actor_action_object": True,
 381 | +                                       "presented_as": "current", "reason": "fake"})
 382 |          if prompt.startswith("These transcript excerpts"):
 383 | -            return {"is_specific_event": False}
 384 | +            return self._ok(validate, {"is_specific_event": False})
 385 |          if prompt.startswith("You pick clips"):
 386 | -            return {"ratings": [{"id": i, "score": 5, "reason": "fake"}
 387 | -                                for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 388 | +            return self._ok(validate, {"ratings": [{"id": i, "score": 5, "fault": "none", "reason": "fake"}
 389 | +                                                   for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]})
 390 |          raise AssertionError("unexpected prompt")
 391 |  
 392 | +    @staticmethod
 393 | +    def _ok(validate, obj):
 394 | +        """The real chat_json contract: a reply the validator rejects is a failed call (LLMParseError), never
 395 | +        returned."""
 396 | +        if validate:
 397 | +            try:
 398 | +                validate(obj)
 399 | +            except ValueError as e:
 400 | +                raise sm.LLMParseError(f"no valid JSON after 3 attempts: {e}", [{"attempt": 1, "error": str(e)}])
 401 | +        return obj
 402 | +
 403 |  
 404 |  TXT = ("Democrats took the House and the Senate in the midterms this week and Congress flips, "
 405 |         "which changes the outlook for Bitcoin policy and crypto legislation next year. ")
 406 | diff --git a/pipeline/test_same_event_merge.py b/pipeline/test_same_event_merge.py
 407 | index 966ebae6..0853841b 100644
 408 | --- a/pipeline/test_same_event_merge.py
 409 | +++ b/pipeline/test_same_event_merge.py
 410 | @@ -47,8 +47,13 @@ class MergeLLM(RoutedLLM):
 411 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 412 |          if prompt.startswith(sm.DERIVE_PROMPT.split("{")[0][:40]):
 413 |              self.prompts.append(prompt)
 414 | -            return {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 415 | -                    "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current"}
 416 | +            obj = {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 417 | +                   "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current",
 418 | +                   "event_date": "2026-11-09", "action": "fell", "affected_object": "Bitcoin price", "entities": [],
 419 | +                   "concepts": [], "must_not_confuse_with": []}
 420 | +            if validate:
 421 | +                validate(obj)
 422 | +            return obj
 423 |          return super().chat_json(prompt, max_tokens, validate, attempts)
 424 |  
 425 |  
 426 | diff --git a/pipeline/test_window_review.py b/pipeline/test_window_review.py
 427 | index 3e14b898..a7fd40eb 100644
 428 | --- a/pipeline/test_window_review.py
 429 | +++ b/pipeline/test_window_review.py
 430 | @@ -136,8 +136,11 @@ class TestHooksUseVerifiedExpansion(unittest.TestCase):
 431 |              model = "fake"
 432 |  
 433 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 434 | -                return {"ratings": [{"id": i, "score": 3, "reason": "x"}
 435 | +                reply = {"ratings": [{"id": i, "score": 3, "fault": "none", "reason": "x"}
 436 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 437 | +                if validate:
 438 | +                    validate(reply)
 439 | +                return reply
 440 |          seen = []
 441 |          orig_e, orig_a = es.expanded_window, es.anchored_window
 442 |  
 443 | @@ -325,18 +328,27 @@ class RoutedLLM:
 444 |          self.second_quote, self.rate, self.prompts = second_quote, rate or (lambda t: (5, "none")), []
 445 |  
 446 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 447 | +        """Every reply is validated like the real call (batch 17 audit: fakes that skip the validator test nothing)."""
 448 | +        reply = self._reply(prompt)
 449 | +        if validate:
 450 | +            validate(reply)
 451 | +        return reply
 452 | +
 453 | +    def _reply(self, prompt):
 454 |          sm = self.sm
 455 |          self.prompts.append(prompt)
 456 |          if prompt.startswith("You verify whether"):
 457 |              hit = [i for i, t in re.findall(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 458 |                     if self.second_quote and sm._norm(self.second_quote) in sm._norm(t)]
 459 |              if not hit:
 460 | -                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "reason": "fake"}
 461 | +                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "confidence": 0.9,
 462 | +                        "reason": "fake"}
 463 |              return {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": hit[:1],
 464 |                      "evidence_quote": self.second_quote, "confidence": 0.9, "reason": "fake"}
 465 |          if prompt.startswith("Decide whether a QUOTE"):
 466 |              q = re.search(r'<excerpt id="quote">(.*?)</excerpt>', prompt, re.S).group(1)
 467 | -            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY", "reason": "fake"}
 468 | +            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY",
 469 | +                    "same_actor_action_object": sm._norm(q) in self.on_event, "presented_as": "current", "reason": "fake"}
 470 |          if prompt.startswith("You check ONE SENTENCE"):                 # D4 reaction / consequence verifier
 471 |              t = re.search(r'<excerpt id="sentence">(.*?)</excerpt>', prompt, re.S).group(1)
 472 |              return {"label": sm.REACTION_OK if sm._norm(t) in self.reactions else "NEW_SUBJECT", "reason": "fake"}
 473 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

