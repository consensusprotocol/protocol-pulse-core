# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 23:29 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (354 lines)
```
   1 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
   2 | index f6cbdc63..e85f7ff2 100644
   3 | --- a/pipeline/story_semantics.py
   4 | +++ b/pipeline/story_semantics.py
   5 | @@ -398,11 +398,45 @@ Return ONLY JSON with keys:
   6 |  "rationale": one sentence}}"""
   7 |  
   8 |  
   9 | +def _field(o, key, kind, allowed=None, nonempty=False, lo=None, hi=None):
  10 | +    """One field of a model reply, strictly (red-team B): exact type (an int is never a bool or a string, a list
  11 | +    is a list), an enumerated value, a non-empty string, a number in range. Raises ValueError: the call failed."""
  12 | +    if not isinstance(o, dict):
  13 | +        raise ValueError("reply is not a JSON object")
  14 | +    v = o.get(key)
  15 | +    ok = {"int": type(v) is int, "bool": type(v) is bool, "str": isinstance(v, str), "list": isinstance(v, list),
  16 | +          "num": type(v) in (int, float)}[kind]
  17 | +    if not ok:
  18 | +        raise ValueError(f"{key} must be {kind}, got {type(v).__name__}")
  19 | +    if allowed is not None and v not in allowed:
  20 | +        raise ValueError(f"{key} {v!r} not in {allowed}")
  21 | +    if nonempty and not (v.strip() if isinstance(v, str) else v):
  22 | +        raise ValueError(f"{key} is empty")
  23 | +    if (lo is not None and v < lo) or (hi is not None and v > hi):
  24 | +        raise ValueError(f"{key} {v!r} outside [{lo}, {hi}]")
  25 | +    return v
  26 | +
  27 | +
  28 | +def _str_list(o, key):
  29 | +    if not all(isinstance(x, str) for x in _field(o, key, "list")):
  30 | +        raise ValueError(f"{key} must be a list of strings")
  31 | +
  32 | +
  33 |  def _v_derive(o):
  34 | -    for k in ("underlying_event", "bitcoin_relevance", "importance"):
  35 | -        if k not in o:
  36 | -            raise ValueError(f"missing {k}")
  37 | -    int(o["bitcoin_relevance"]), int(o["importance"])
  38 | +    """Every field a decision reads: the event, its Bitcoin relevance and importance (the screen and the ranking),
  39 | +    its date and recency (currentness), the entities / action / object / confusables (adjudication context)."""
  40 | +    _field(o, "underlying_event", "str", nonempty=True)
  41 | +    _field(o, "bitcoin_relevance", "int", lo=0, hi=5)
  42 | +    _field(o, "importance", "int", lo=0, hi=5)
  43 | +    _field(o, "event_date", "str", nonempty=True)
  44 | +    _field(o, "event_recency", "str", allowed=("current", "recent", "historical"))
  45 | +    _field(o, "action", "str")
  46 | +    _field(o, "affected_object", "str")
  47 | +    if not all(isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()
  48 | +               and isinstance(e.get("aliases", []), list) for e in _field(o, "entities", "list")):
  49 | +        raise ValueError("entities must be objects with a name and an aliases list")
  50 | +    _str_list(o, "must_not_confuse_with")
  51 | +    _str_list(o, "concepts")
  52 |  
  53 |  
  54 |  CLUSTER_NOTE = ("This item is a development several Bitcoin channels state in common (DEC-13): underlying_event "
  55 | @@ -588,13 +622,23 @@ Return ONLY JSON: {{"quote_actor": who acts in the quote ("unstated" if nobody i
  56 |  
  57 |  
  58 |  def _v_adj(o):
  59 | -    if o.get("verdict") not in VERDICTS:
  60 | -        raise ValueError(f"verdict {o.get('verdict')!r} not in {VERDICTS}")
  61 | +    _field(o, "verdict", "str", allowed=VERDICTS)
  62 | +    _str_list(o, "supporting_chunk_ids")
  63 | +    _field(o, "evidence_quote", "str")
  64 | +    _field(o, "confidence", "num", lo=0, hi=1)
  65 | +    _field(o, "reason", "str")
  66 | +
  67 | +
  68 | +SUPPORT_PRESENTED = ("current", "past", "unclear")
  69 |  
  70 |  
  71 |  def _v_sup(o):
  72 | -    if o.get("support") not in SUPPORT:
  73 | -        raise ValueError(f"support {o.get('support')!r} not in {SUPPORT}")
  74 | +    """GPT-select F01: the fields that decide SUPPORTS are required and typed (a missing same_actor_action_object
  75 | +    or presented_as was read as agreement)."""
  76 | +    _field(o, "support", "str", allowed=SUPPORT)
  77 | +    _field(o, "same_actor_action_object", "bool")
  78 | +    _field(o, "presented_as", "str", allowed=SUPPORT_PRESENTED)
  79 | +    _field(o, "reason", "str")
  80 |  
  81 |  
  82 |  def _entities_str(q):
  83 | @@ -629,8 +673,8 @@ Return ONLY JSON: {{"label": one of the three, "reason": one sentence}}"""
  84 |  
  85 |  
  86 |  def _v_react(o):
  87 | -    if o.get("label") not in REACTION_LABELS:
  88 | -        raise ValueError(f"label {o.get('label')!r} not in {REACTION_LABELS}")
  89 | +    _field(o, "label", "str", allowed=REACTION_LABELS)
  90 | +    _field(o, "reason", "str")
  91 |  
  92 |  
  93 |  def verify_reaction(llm, q, anchor, sentence):
  94 | @@ -646,11 +690,13 @@ def verify_support(llm, q, quote):
  95 |                                obj=q.get("affected_object", "-"), entities=_entities_str(q),
  96 |                                note=UNTRUSTED_NOTE, quote=quote_data(quote, 600))
  97 |      s = llm.chat_json(p, max_tokens=350, validate=_v_sup)
  98 | -    if s["support"] == "SUPPORTS":       # the structured fields must agree with the label
  99 | -        if s.get("same_actor_action_object") is False:
 100 | -            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is false"
 101 | -        elif str(s.get("presented_as", "")).lower() == "past":
 102 | +    if s["support"] == "SUPPORTS":       # the structured fields must AGREE with the label (fail closed: GPT-select F01)
 103 | +        if s["same_actor_action_object"] is not True:
 104 | +            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is not true"
 105 | +        elif s["presented_as"] == "past":
 106 |              s["support"], s["downgraded"] = "BACKGROUND", "presented_as past"
 107 | +        elif s["presented_as"] != "current":
 108 | +            s["support"], s["downgraded"] = "INCONCLUSIVE", f"presented_as {s['presented_as']}"
 109 |      return s
 110 |  
 111 |  
 112 | @@ -738,8 +784,13 @@ def emergent_clusters(chunks, vecs, min_channels=3, threshold=0.22, max_clusters
 113 |  
 114 |  
 115 |  def _v_label(o):
 116 | -    if not isinstance(o.get("is_specific_event"), bool):
 117 | -        raise ValueError("is_specific_event must be boolean")
 118 | +    """A specific event must come with everything the current-development check reads."""
 119 | +    if _field(o, "is_specific_event", "bool"):
 120 | +        _field(o, "headline", "str", nonempty=True)
 121 | +        _field(o, "event_date", "str", nonempty=True)
 122 | +        _field(o, "current_development_quote", "str", nonempty=True)
 123 | +        _field(o, "current_development_chunk_id", "str", nonempty=True)
 124 | +        _str_list(o, "member_chunk_ids")
 125 |  
 126 |  
 127 |  def label_cluster(llm, chunks, vecs, group, today, k=8):
 128 | @@ -805,9 +856,22 @@ Return ONLY JSON: {{"ratings": [{{"id": passage id, "score": 1-5, "fault": one o
 129 |  BOUNDARY_FAULTS = ("starts_mid_thought", "ends_mid_thought")   # D3: the only faults a repair may address
 130 |  
 131 |  
 132 | -def _v_rate(o):
 133 | -    if not isinstance(o.get("ratings"), list):
 134 | -        raise ValueError("ratings must be a list")
 135 | +RATE_FAULTS = BOUNDARY_FAULTS + ("none", "off_topic", "other")
 136 | +
 137 | +
 138 | +def _v_rate(o, ids=None):
 139 | +    """GPT-select F12: a score outside 1-5 or not a number, an unknown fault, a duplicate or unknown passage id, or
 140 | +    (with ids) a passage left unrated is a failed call; it is never clamped into a perfect score."""
 141 | +    seen = set()
 142 | +    for x in _field(o, "ratings", "list"):
 143 | +        pid = str(_field(x, "id", "str") if isinstance((x or {}).get("id"), str) else _field(x, "id", "int"))
 144 | +        _field(x, "score", "num", lo=1, hi=5)
 145 | +        _field(x, "fault", "str", allowed=RATE_FAULTS)
 146 | +        if pid in seen or (ids is not None and pid not in ids):
 147 | +            raise ValueError(f"rating id {pid!r} duplicate or unknown")
 148 | +        seen.add(pid)
 149 | +    if ids is not None and seen != set(ids):
 150 | +        raise ValueError(f"unrated passages: {sorted(set(ids) - seen)[:5]}")
 151 |  
 152 |  
 153 |  def rate_passages(llm, q, passages):
 154 | @@ -816,19 +880,15 @@ def rate_passages(llm, q, passages):
 155 |      ex = "\n".join(f'<excerpt id="{p["pid"]}" channel="{p["channel"]}" seconds="{p["duration"]:.0f}">'
 156 |                     f'{quote_data(p["text"], 700)}</excerpt>' for p in passages)
 157 |      try:
 158 | +        ids = {str(p["pid"]) for p in passages}
 159 |          r = llm.chat_json(CLIP_PROMPT.format(event=q.get("underlying_event", ""), note=UNTRUSTED_NOTE,
 160 | -                                             passages=ex), max_tokens=1200, validate=_v_rate)
 161 | +                                             passages=ex), max_tokens=1200, validate=lambda o: _v_rate(o, ids))
 162 |      except LLMParseError as e:
 163 |          return {}, {"error": str(e), "llm_attempts": e.attempts}
 164 |      out = {}
 165 |      valid = {p["pid"] for p in passages}
 166 | -    for x in r.get("ratings", []) or []:
 167 | -        try:
 168 | -            pid = str(x["id"])
 169 | -            if pid in valid:
 170 | -                fault = x.get("fault") if x.get("fault") in BOUNDARY_FAULTS + ("none", "off_topic", "other") \
 171 | -                    else "unspecified"
 172 | -                out[pid] = (max(1.0, min(5.0, float(x["score"]))), x.get("reason", ""), fault)
 173 | -        except Exception:
 174 | -            pass
 175 | +    for x in r["ratings"]:                          # validated: every passage once, score 1-5, a known fault
 176 | +        pid = str(x["id"])
 177 | +        if pid in valid:
 178 | +            out[pid] = (float(x["score"]), str(x.get("reason", "")), x["fault"])
 179 |      return out, None
 180 | diff --git a/pipeline/test_caption_entities.py b/pipeline/test_caption_entities.py
 181 | index 09b15c3f..cdf2f9e5 100644
 182 | --- a/pipeline/test_caption_entities.py
 183 | +++ b/pipeline/test_caption_entities.py
 184 | @@ -105,8 +105,13 @@ class TestClusterClaimIsTheEvent(unittest.TestCase):
 185 |  
 186 |          def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 187 |              self.prompts.append(prompt)
 188 | -            return {"underlying_event": "The US held its general elections on November 8th, 2026.",
 189 | -                    "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin"}
 190 | +            obj = {"underlying_event": "The US held its general elections on November 8th, 2026.",
 191 | +                   "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin",
 192 | +                   "event_date": "2026-11-08", "event_recency": "current", "entities": [], "concepts": [],
 193 | +                   "must_not_confuse_with": []}
 194 | +            if validate:
 195 | +                validate(obj)
 196 | +            return obj
 197 |  
 198 |      def test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged(self):
 199 |          claim = "Following the US elections, Bitcoin experienced a sell-off and net outflows from US Bitcoin ETFs."
 200 | diff --git a/pipeline/test_editorial_robust.py b/pipeline/test_editorial_robust.py
 201 | index 59a1c282..498884d2 100644
 202 | --- a/pipeline/test_editorial_robust.py
 203 | +++ b/pipeline/test_editorial_robust.py
 204 | @@ -229,7 +229,7 @@ class TestQuoteAnchoredWindows(unittest.TestCase):
 205 |                  self.score = score
 206 |  
 207 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 208 | -                return {"ratings": [{"id": i, "score": self.score, "reason": "start at 0.0 instead"}
 209 | +                return {"ratings": [{"id": i, "score": self.score, "fault": "none", "reason": "start at 0.0 instead"}
 210 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 211 |          c = {"query": RUN3["binance"]["query"], "headline": RUN3["binance"]["headline"]}
 212 |          cq = es._clip_quality(c, same, FakeEmbedder(), Rater(5), reg, words, log=lambda s: None)
 213 | @@ -279,10 +279,45 @@ class ScriptedLLM(sm.LocalLLM):
 214 |  
 215 |  class TestMalformedLLM(unittest.TestCase):
 216 |      def test_retry_then_valid(self):
 217 | -        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}', '```json\n{"support": "SUPPORTS",}\n```'])
 218 | +        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}',
 219 | +                           '```json\n{"support": "SUPPORTS", "same_actor_action_object": true, "presented_as": "current", '
 220 | +                           '"reason": "r",}\n```'])
 221 |          self.assertEqual(llm.chat_json("p", validate=sm._v_sup)["support"], "SUPPORTS")
 222 |          self.assertEqual(llm.calls, 2)
 223 |  
 224 | +    def test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call(self):
 225 | +        """Red-team B (GPT-select F01 / F11 / F12): missing / mistyped / out-of-range fields are never accepted."""
 226 | +        for v, bad in ((sm._v_sup, {"support": "SUPPORTS", "reason": "r"}),                       # fields missing
 227 | +                       (sm._v_sup, {"support": "SUPPORTS", "same_actor_action_object": "true", "presented_as": "current",
 228 | +                                    "reason": "r"}),                                              # a string bool
 229 | +                       (sm._v_adj, {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": "AAA:0-1", "evidence_quote": "q",
 230 | +                                    "confidence": 0.9, "reason": "r"}),                           # ids not a list
 231 | +                       (sm._v_derive, {"underlying_event": "x", "bitcoin_relevance": True, "importance": 3}),  # bool int
 232 | +                       (sm._v_label, {"is_specific_event": True, "headline": "h"}),             # quote / ids missing
 233 | +                       (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 9, "fault": "none"},
 234 | +                                                                          {"id": "p1", "score": 4, "fault": "none"}]}),
 235 | +                       (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 4, "fault": "none"}]}),
 236 | +                       (lambda o: sm._v_rate(o, {"p0"}), {"ratings": [{"id": "p0", "score": 4, "fault": "great"}]})):
 237 | +            with self.assertRaises(ValueError, msg=str(bad)):
 238 | +                v(bad)
 239 | +
 240 | +    def test_supports_needs_both_deciding_fields_exactly(self):
 241 | +        class One:
 242 | +            model, calls = "fake", 0
 243 | +
 244 | +            def __init__(self, reply):
 245 | +                self.reply = reply
 246 | +
 247 | +            def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 248 | +                if validate:
 249 | +                    validate(self.reply)
 250 | +                return dict(self.reply)
 251 | +        base = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "r"}
 252 | +        self.assertEqual(sm.verify_support(One(base), {"underlying_event": "x"}, "q")["support"], "SUPPORTS")
 253 | +        for change, want in (({"same_actor_action_object": False}, "TOPIC_ONLY"), ({"presented_as": "past"}, "BACKGROUND"),
 254 | +                             ({"presented_as": "unclear"}, "INCONCLUSIVE")):
 255 | +            self.assertEqual(sm.verify_support(One({**base, **change}), {"underlying_event": "x"}, "q")["support"], want)
 256 | +
 257 |      def test_bounded_and_recorded(self):
 258 |          llm = ScriptedLLM(["not json", '{"verdict": "MAYBE"}', '{"verdict": '])
 259 |          with self.assertRaises(sm.LLMParseError) as cm:
 260 | @@ -348,27 +383,35 @@ class FakeLLM:
 261 |              if "PARSEFAIL" in h:
 262 |                  raise sm.LLMParseError("no valid JSON after 3 attempts",
 263 |                                         [{"attempt": i + 1, "error": "bad", "raw": "{oops"} for i in range(3)])
 264 | -            return {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 265 | +            return self._ok(validate, {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 266 |                      "event_recency": self.model_recency, "entities": [{"name": "Congress", "aliases": ["midterms", "Senate"]}],
 267 |                      "action": "flip", "affected_object": "Congress", "concepts": ["midterms", "Congress"],
 268 | -                    "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True}
 269 | +                    "must_not_confuse_with": [], "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True})
 270 |          if prompt.startswith("You verify whether"):
 271 |              self.adj += 1
 272 |              if self.crash and self.adj == self.crash:
 273 |                  raise RuntimeError("boom (simulated crash)")
 274 |              m = re.search(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 275 |              words = m.group(2).split()[:10]
 276 | -            return {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 277 | -                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"}
 278 | +            return self._ok(validate, {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 279 | +                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"})
 280 |          if prompt.startswith("Decide whether a QUOTE"):
 281 | -            return {"support": "SUPPORTS", "reason": "fake"}
 282 | +            return self._ok(validate, {"support": "SUPPORTS", "same_actor_action_object": True,
 283 | +                                       "presented_as": "current", "reason": "fake"})
 284 |          if prompt.startswith("These transcript excerpts"):
 285 | -            return {"is_specific_event": False}
 286 | +            return self._ok(validate, {"is_specific_event": False})
 287 |          if prompt.startswith("You pick clips"):
 288 | -            return {"ratings": [{"id": i, "score": 5, "reason": "fake"}
 289 | -                                for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 290 | +            return self._ok(validate, {"ratings": [{"id": i, "score": 5, "fault": "none", "reason": "fake"}
 291 | +                                                   for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]})
 292 |          raise AssertionError("unexpected prompt")
 293 |  
 294 | +    @staticmethod
 295 | +    def _ok(validate, obj):
 296 | +        """The real chat_json contract: a reply the validator rejects is a failed call, never returned."""
 297 | +        if validate:
 298 | +            validate(obj)
 299 | +        return obj
 300 | +
 301 |  
 302 |  TXT = ("Democrats took the House and the Senate in the midterms this week and Congress flips, "
 303 |         "which changes the outlook for Bitcoin policy and crypto legislation next year. ")
 304 | diff --git a/pipeline/test_same_event_merge.py b/pipeline/test_same_event_merge.py
 305 | index 966ebae6..0853841b 100644
 306 | --- a/pipeline/test_same_event_merge.py
 307 | +++ b/pipeline/test_same_event_merge.py
 308 | @@ -47,8 +47,13 @@ class MergeLLM(RoutedLLM):
 309 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 310 |          if prompt.startswith(sm.DERIVE_PROMPT.split("{")[0][:40]):
 311 |              self.prompts.append(prompt)
 312 | -            return {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 313 | -                    "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current"}
 314 | +            obj = {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 315 | +                   "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current",
 316 | +                   "event_date": "2026-11-09", "action": "fell", "affected_object": "Bitcoin price", "entities": [],
 317 | +                   "concepts": [], "must_not_confuse_with": []}
 318 | +            if validate:
 319 | +                validate(obj)
 320 | +            return obj
 321 |          return super().chat_json(prompt, max_tokens, validate, attempts)
 322 |  
 323 |  
 324 | diff --git a/pipeline/test_window_review.py b/pipeline/test_window_review.py
 325 | index 3e14b898..7cbc5183 100644
 326 | --- a/pipeline/test_window_review.py
 327 | +++ b/pipeline/test_window_review.py
 328 | @@ -136,7 +136,7 @@ class TestHooksUseVerifiedExpansion(unittest.TestCase):
 329 |              model = "fake"
 330 |  
 331 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 332 | -                return {"ratings": [{"id": i, "score": 3, "reason": "x"}
 333 | +                return {"ratings": [{"id": i, "score": 3, "fault": "none", "reason": "x"}
 334 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 335 |          seen = []
 336 |          orig_e, orig_a = es.expanded_window, es.anchored_window
 337 | @@ -331,12 +331,14 @@ class RoutedLLM:
 338 |              hit = [i for i, t in re.findall(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 339 |                     if self.second_quote and sm._norm(self.second_quote) in sm._norm(t)]
 340 |              if not hit:
 341 | -                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "reason": "fake"}
 342 | +                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "confidence": 0.9,
 343 | +                        "reason": "fake"}
 344 |              return {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": hit[:1],
 345 |                      "evidence_quote": self.second_quote, "confidence": 0.9, "reason": "fake"}
 346 |          if prompt.startswith("Decide whether a QUOTE"):
 347 |              q = re.search(r'<excerpt id="quote">(.*?)</excerpt>', prompt, re.S).group(1)
 348 | -            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY", "reason": "fake"}
 349 | +            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY",
 350 | +                    "same_actor_action_object": sm._norm(q) in self.on_event, "presented_as": "current", "reason": "fake"}
 351 |          if prompt.startswith("You check ONE SENTENCE"):                 # D4 reaction / consequence verifier
 352 |              t = re.search(r'<excerpt id="sentence">(.*?)</excerpt>', prompt, re.S).group(1)
 353 |              return {"label": sm.REACTION_OK if sm._norm(t) in self.reactions else "NEW_SUBJECT", "reason": "fake"}
 354 | 
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

