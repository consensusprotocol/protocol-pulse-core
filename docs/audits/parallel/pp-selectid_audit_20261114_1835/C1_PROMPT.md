# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_1835
# Branch: pp-selectid
# Generated: 2026-11-14 18:35 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_1835/C1_STEP.diff (270 lines)
```
   1 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
   2 | index 370390e..5f7daa3 100644
   3 | --- a/pipeline/spotlight.py
   4 | +++ b/pipeline/spotlight.py
   5 | @@ -189,6 +189,14 @@ def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
   6 |      return rec, None
   7 |  
   8 |  
   9 | +def day_taken(spotlit, channel_id, day, alternative_to=None):
  10 | +    """RULING 90: the channel already has a spotlight on this ET day. RULING 104 on the orchestrator's directive: a
  11 | +    variant that is the ALTERNATIVE to a named sealed spotlight takes that story's place, and only that one (any other
  12 | +    record of the channel that day still takes it). One rule for the pool and for the pin. -> bool."""
  13 | +    return any(r.get("channel_id") == channel_id and r.get("day_et") == day and
  14 | +               not (isinstance(alternative_to, str) and r.get("story_id") == alternative_to) for r in spotlit)
  15 | +
  16 | +
  17 |  def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), captions_for=None):
  18 |      """Stage 1, FREE (no vendor call) -> (the moments that may be a spotlight, {moment id: why not}): package.usable
  19 |      with ruling 90's 35 s ceiling (inside 12 h on the render clock, never a delivered span or the same speech, no hard
  20 | @@ -204,11 +212,11 @@ def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), ca
  21 |                                      "record cannot be read)" for m in ms})
  22 |          return [], why
  23 |      day = et_day(ctx.now)
  24 | -    taken = {r["channel_id"] for r in spotlit if r.get("day_et") == day}
  25 | +
  26 |      out, seen = [], set()
  27 |      for m in ms:
  28 |          mid = m["moment_id"]
  29 | -        if m["channel_id"] in taken:
  30 | +        if day_taken(spotlit, m["channel_id"], day, (m.get("derived_from") or {}).get("alternative_to")):
  31 |              why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
  32 |              continue
  33 |          v, target = m, SNAP_TO_S + (TRIM_MARGIN_S if P.hook_trim(m) else 0.0)
  34 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
  35 | index ce29936..6c83528 100644
  36 | --- a/pipeline/tail_variant.py
  37 | +++ b/pipeline/tail_variant.py
  38 | @@ -19,7 +19,10 @@ a variant that drops the speaker's own condition or conclusion fails there."
  39 |    A parent with a current hold is REPLACED by its variant ("the hold is final and the clip may only be saved by a
  40 |    variant that leaves the token out", ruling 103): the two never compete for a line-up or a finalist's place. A parent
  41 |    over the ceiling stays beside its variant (the medley may still use it).
  42 | -A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out."""
  43 | +A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out.
  44 | +- directive_variant(): ONLY on the orchestrator's written directive (proof_ledger.DIRECTIVES, written by the builder
  45 | +  quoting the ruling), the variant of a NAMED parent ending as the directive says, as the ALTERNATIVE to a named sealed
  46 | +  spotlight (ruling 90's one place per channel per day then admits it beside that story, and nothing else)."""
  47 |  import attest as AT
  48 |  import canon as C
  49 |  import eligibility as E
  50 | @@ -90,9 +93,27 @@ def held_word(m, src, entry):
  51 |      return None
  52 |  
  53 |  
  54 | -def for_pool(moments, sources, ctx, results_dir, ceil_s):
  55 | -    """The ruling-104 variants for this build's pool. -> (variants, {parent id: why it has none / which it got},
  56 | -    {the ids of the parents a current hold makes final: replaced by their variants})."""
  57 | +def directive_variant(m, src, ctx, d):
  58 | +    """The orchestrator's directive `d` ({"parent", "ends", "alternative_to", "by", "why"}) on the parent `m`: its variant
  59 | +    ending at the longest earlier sentence boundary whose words END as d["ends"] (canon tokens), recorded with the
  60 | +    directive and the spotlight it is the alternative to. -> (variant, None) or (None, why there is none)."""
  61 | +    k0, k1 = m["sentences"]
  62 | +    want = C.canon_tokens(str(d.get("ends") or "").lstrip(".\u2026 "))
  63 | +    if not want:
  64 | +        return None, "the directive names no ending"
  65 | +    for k in range(k1 - 1, k0 - 1, -1):
  66 | +        got = C.canon_tokens(E.spoken(src.tokens[src.sentences[k0][0]:src.sentences[k][1] + 1]))
  67 | +        if got[-len(want):] == want:
  68 | +            v = variant(m, src, k, ctx, f"the orchestrator's directive ({d.get('by')}): {d.get('why') or ''}".strip())
  69 | +            v["derived_from"].update(directive=d.get("by"), alternative_to=d.get("alternative_to"))
  70 | +            return v, None
  71 | +    return None, f"no earlier sentence boundary of the parent ends {d.get('ends')!r}"
  72 | +
  73 | +
  74 | +def for_pool(moments, sources, ctx, results_dir, ceil_s, directives=None):
  75 | +    """The ruling-104 variants for this build's pool. directives: {parent id: the orchestrator's directive} (a parent
  76 | +    named there gets the directive's variant, in its place, whatever its pre-check says). -> (variants, {parent id: why
  77 | +    it has none / which it got}, {the ids of the parents replaced by their variants})."""
  78 |      import context_integrity as CI
  79 |      have = {m["moment_id"] for m in moments}
  80 |      out, notes, replaced = [], {}, set()
  81 | @@ -102,6 +123,23 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s):
  82 |          if not (isinstance(k0, int) and isinstance(k1, int) and k1 > k0):
  83 |              continue                                     # one sentence: no earlier boundary
  84 |          wanted = []
  85 | +        if mid in (directives or {}):                    # the orchestrator's directive: this variant, in its place
  86 | +            try:
  87 | +                src = CI.source_for(m, sources)
  88 | +            except KeyError:
  89 | +                notes[mid] = "the directive: no variant, its word record is not in this build"
  90 | +                continue
  91 | +            v, why = directive_variant(m, src, ctx, directives[mid])
  92 | +            if v is None:
  93 | +                notes[mid] = f"the directive: no variant, {why}"
  94 | +                continue
  95 | +            if v["moment_id"] not in have:
  96 | +                have.add(v["moment_id"])
  97 | +                out.append(v)
  98 | +            replaced.add(mid)
  99 | +            notes[mid] = (f"the directive's variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r}), "
 100 | +                          f"in its place, the alternative to {v['derived_from'].get('alternative_to')}")
 101 | +            continue
 102 |          e = holds(m, results_dir)
 103 |          try:
 104 |              src = CI.source_for(m, sources)
 105 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 106 | index b646c26..ada9c27 100644
 107 | --- a/tests/package/proof_ledger.py
 108 | +++ b/tests/package/proof_ledger.py
 109 | @@ -74,6 +74,7 @@ import tail_variant as TV  # noqa: E402
 110 |  
 111 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 112 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 113 | +DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
 114 |  STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
 115 |  
 116 |  
 117 | @@ -132,13 +133,38 @@ def applied(router):
 118 |      return applies
 119 |  
 120 |  
 121 | -def with_variants(moments, sources, ctx, inputs, say, results_dir=None):
 122 | +def directives(path=None):
 123 | +    """RULING 104: the orchestrator's directives ({"directives": [{"parent", "ends", "alternative_to", "by", "why"}]}),
 124 | +    written by the builder only on the orchestrator's written yes, quoting it. -> {parent id: directive}; none when the
 125 | +    file is absent; an unreadable file or a malformed row is never guessed at: no directive (the rules stand)."""
 126 | +    try:
 127 | +        with open(path or DIRECTIVES) as f:
 128 | +            rows = json.load(f).get("directives") or []
 129 | +    except (OSError, ValueError, AttributeError):
 130 | +        return {}
 131 | +    return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
 132 | +            isinstance(d.get("ends"), str) and isinstance(d.get("alternative_to"), str) and isinstance(d.get("by"), str)}
 133 | +
 134 | +
 135 | +def spot_place(pk, again, now):
 136 | +    """RULING 90 at the pin, read again: the spotlight's channel must have no spotlight on this ET day, unless the
 137 | +    package is ruling 104's ALTERNATIVE (the orchestrator's directive) to that day's named story (spotlight.day_taken).
 138 | +    again: the spotlights record, None when it cannot be read (then no pin). -> (why it cannot take the place or None,
 139 | +    the story it is the alternative to or None)."""
 140 | +    alt = ((pk.get("spotlight") or {}).get("derived_from") or {}).get("alternative_to")
 141 | +    if again is None or SPOT.day_taken(again, pk["segments"][0]["channel_id"], SPOT.et_day(now), alt):
 142 | +        return "ruling 90: this channel already has a spotlight today, or the record cannot be read", alt
 143 | +    return None, alt
 144 | +
 145 | +
 146 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directives_path=None):
 147 |      """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
 148 |      pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
 149 |      judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
 150 |      hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
 151 |      them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
 152 | -    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 153 | +    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1],
 154 | +                                            directives=directives(directives_path))
 155 |      inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
 156 |                              "notes": notes}
 157 |      say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
 158 | @@ -397,9 +423,9 @@ def main(argv=None):
 159 |          try:
 160 |              lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
 161 |              again = SPOT.load_spotlit(SPOTLIGHTS)        # one per channel per day, read again at the pin
 162 | -            if again is None or any(r["channel_id"] == sp["package"]["segments"][0]["channel_id"] and
 163 | -                                    r.get("day_et") == SPOT.et_day(now) for r in again):
 164 | -                lock.append("ruling 90: this channel already has a spotlight today, or the record cannot be read")
 165 | +            why_place, alt = spot_place(sp["package"], again, now)
 166 | +            if why_place:
 167 | +                lock.append(why_place)
 168 |              if lock:
 169 |                  raise package_pin.PinRefused("; ".join(lock))
 170 |              path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 171 | @@ -414,7 +440,8 @@ def main(argv=None):
 172 |              SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
 173 |                                               "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
 174 |                                               "package_sha256": pin["moments_package"]["package_sha256"],
 175 | -                                             "at": now.isoformat(timespec="seconds"), "build": name})
 176 | +                                             "at": now.isoformat(timespec="seconds"), "build": name,
 177 | +                                             **({"alternative_to": alt} if alt else {})})    # ruling 104
 178 |              say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
 179 |                  f"{sp['package']['vo']['closing']!r})")
 180 |          except (package_pin.PinRefused, ValueError, OSError) as e:
 181 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 182 | index 728f40a..0b605ed 100644
 183 | --- a/tests/package/test_ruling_104.py
 184 | +++ b/tests/package/test_ruling_104.py
 185 | @@ -260,3 +260,84 @@ class TestTheSpotlight(unittest.TestCase):
 186 |  
 187 |  if __name__ == "__main__":
 188 |      unittest.main()
 189 | +
 190 | +
 191 | +DIRECTIVE = {"parent": None, "ends": "...I still don't use my Roth IRA.", "alternative_to": "moments-x-3f481f5a",
 192 | +             "by": "orchestrator 18:4x ET Nov 14", "why": "two of three readings of the token say 401"}
 193 | +
 194 | +
 195 | +class TestTheDirective(unittest.TestCase):
 196 | +    """RULING 104 on the orchestrator's written directive: a NAMED parent's variant ending as the directive says, as
 197 | +    the ALTERNATIVE to a named sealed spotlight; nothing without a directive."""
 198 | +
 199 | +    def setUp(self):
 200 | +        self.d = tempfile.TemporaryDirectory()
 201 | +        self.addCleanup(self.d.cleanup)
 202 | +
 203 | +    def test_the_directive_names_the_ending_and_the_variant_records_it(self):
 204 | +        src, m = blockware()
 205 | +        d = dict(DIRECTIVE, parent=m["moment_id"])
 206 | +        v, why = TV.directive_variant(m, src, CTX, d)
 207 | +        self.assertIsNone(why)
 208 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 209 | +        self.assertEqual((v["derived_from"]["directive"], v["derived_from"]["alternative_to"]),
 210 | +                         ("orchestrator 18:4x ET Nov 14", "moments-x-3f481f5a"))
 211 | +        self.assertEqual(v["mined"]["derived_from"]["alternative_to"], "moments-x-3f481f5a")   # in its mined record
 212 | +        for ends in ("...by 45.", "...I sold every stock", ""):                # the parent's own end; mid-sentence;
 213 | +            self.assertIsNone(TV.directive_variant(m, src, CTX, dict(d, ends=ends))[0], ends)   # nothing named
 214 | +
 215 | +    def test_a_named_parent_is_replaced_whatever_its_pre_check_says(self):
 216 | +        src, m = blockware()
 217 | +        put(self.d.name, m, [hold(m, outcome="no_difference")])                 # its current answer: a pass
 218 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 219 | +                                          directives={m["moment_id"]: dict(DIRECTIVE, parent=m["moment_id"])})
 220 | +        self.assertEqual(([v["sentences"] for v in vs], replaced), ([[0, 2]], {m["moment_id"]}))
 221 | +        self.assertIn("the alternative to moments-x-3f481f5a", notes[m["moment_id"]])
 222 | +        self.assertEqual(TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0), ([], {}, set()))   # none
 223 | +
 224 | +    def test_the_directives_file_is_read_and_never_guessed_at(self):
 225 | +        p = os.path.join(self.d.name, "D.json")
 226 | +        self.assertEqual(PLG.directives(p), {})                                  # absent: none
 227 | +        with open(p, "w") as f:
 228 | +            f.write("{ broken")
 229 | +        self.assertEqual(PLG.directives(p), {})
 230 | +        good = dict(DIRECTIVE, parent="06d34e155feae654ee56")
 231 | +        with open(p, "w") as f:
 232 | +            json.dump({"directives": [good, dict(good, parent="b", by=None), dict(good, parent="c", ends=7), "x",
 233 | +                                      dict(good, parent=5), dict(good, parent="d", alternative_to=None)]}, f)
 234 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": good})       # malformed rows dropped
 235 | +        src, m = blockware()
 236 | +        with open(p, "w") as f:
 237 | +            json.dump({"directives": [dict(DIRECTIVE, parent=m["moment_id"])]}, f)
 238 | +        out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, lambda s: None, results_dir=self.d.name,
 239 | +                                directives_path=p)
 240 | +        self.assertEqual([x["sentences"] for x in out], [[0, 2]])                # in the parent's place
 241 | +
 242 | +    def test_the_alternative_takes_the_day_s_place_only_beside_its_named_story(self):
 243 | +        ctx = E.Context(NOW, REG)
 244 | +        a, b = TS.moment(mid="a", channel="A"), TS.moment(mid="b", channel="B", text=TS.TEXT.replace("money", "asset"))
 245 | +        caps = lambda vid: (None, None)
 246 | +        day = [{"channel_id": "A", "day_et": SPOT.et_day(NOW), "story_id": "moments-x-3f481f5a"}]
 247 | +        alt = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-3f481f5a"})
 248 | +        got, why = SPOT.pool([alt, b], {}, ctx, spotlit=day, captions_for=caps)
 249 | +        self.assertEqual(sorted(m["moment_id"] for m in got), ["a", "b"])        # the alternative is admitted
 250 | +        other = dict(a, derived_from={"ruling": 104, "from": "p", "alternative_to": "moments-x-another"})
 251 | +        got, why = SPOT.pool([other, b], {}, ctx, spotlit=day, captions_for=caps)
 252 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # another story's: refused
 253 | +        self.assertIn("already has a spotlight", why["a"])
 254 | +        got, why = SPOT.pool([a, b], {}, ctx, spotlit=day, captions_for=caps)
 255 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # no directive: refused, as before
 256 | +        today = SPOT.et_day(NOW)                                                  # the one rule, as the pin reads it
 257 | +        self.assertFalse(SPOT.day_taken(day, "A", today, "moments-x-3f481f5a"))
 258 | +        self.assertTrue(SPOT.day_taken(day, "A", today, None))
 259 | +        self.assertTrue(SPOT.day_taken(day + [{"channel_id": "A", "day_et": today, "story_id": "moments-alt"}], "A",
 260 | +                                       today, "moments-x-3f481f5a"))             # one alternative, not two
 261 | +        self.assertFalse(SPOT.day_taken(day, "A", "2026-11-15", None))           # another day
 262 | +        pk = {"segments": [{"channel_id": "A"}],
 263 | +              "spotlight": {"derived_from": {"ruling": 104, "alternative_to": "moments-x-3f481f5a"}}}
 264 | +        self.assertEqual(PLG.spot_place(pk, day, NOW), (None, "moments-x-3f481f5a"))     # at the pin: admitted
 265 | +        self.assertTrue(PLG.spot_place({"segments": [{"channel_id": "A"}]}, day, NOW)[0])  # no directive: refused
 266 | +        self.assertTrue(PLG.spot_place(pk, None, NOW)[0])                                  # unreadable: refused
 267 | +        no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]                 # a record without a story id
 268 | +        got, _ = SPOT.pool([a, alt, b], {}, ctx, spotlit=no_id, captions_for=caps)
 269 | +        self.assertEqual([m["moment_id"] for m in got], ["b"])                   # admits no one
 270 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- RULING 104 (the orchestrator, 14:12 ET Nov 14), already implemented and committed (5aad59b5): "a spotlight (and a
  medley hook or clip) may be sealed as a variant that ENDS at an earlier sentence boundary of the mined moment, when
  that is what keeps it lawful (a held word after the boundary, a tail the cut cannot make, the seconds ceiling). It
  is a new span: it faces every gate again from the start ..., and the variant is recorded as derived from its parent
  row."
  - pipeline/tail_variant.py makes such variants at pool time when the parent's CURRENT lock pre-check answer HOLDS
    (or ruling 73's cut hold, or the 35 s ceiling). A parent with a current hold is REPLACED by its variant.
- RULING 90: at most one spotlight per channel per ET day (tests/package/proof/SPOTLIGHTS.json records each sealed
  spotlight: channel_id, day_et, story_id, ...). spotlight.pool refuses a taken channel's moments. The ledger build
  reads the record again at the pin and refuses there too.
- THE CASE (now): the spotlight pin 3f481f5a, Blockware Solutions 06d34e15, the FULL 22.94 s clip, sealed at 18:23 ET.
  - The integrator's pre-check answered "no_difference" (the second recogniser read "401k" this time).
  - The integrator froze it but has not launched it. Scribe read the token three times today: "401" (13:51, long),
    "401" (14:16, ruling 103's short re-listen, recorded as final) and "401k" (18:17, long).
  - It asks the orchestrator whether the full clip may go. It also asks the builder to have the ruling-104 VARIANT
    (0.000-15.280, ending "...I still don't use my Roth IRA.") ready so the orchestrator can choose before 00:00 ET,
    when the source expires.
  - The builder put the question on STATE line 1. Two of the orchestrator's rules stand in the way of that variant:
    its current pre-check answer is a pass, and ruling 90 gives Blockware's channel to 3f481f5a today. The variant is
    built ONLY on the orchestrator's written yes.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff):
- tail_variant.variant(m, src, k, ctx, why) builds the variant by moments.record over eligibility.Span(src, k0, k):
  eligibility judged afresh, its own id, derived_from on the record and in its mined record (the same dict).
- Every gate (step A both families, CUTTABLE, opener rating, visual, ALONE, exclusion, the lock pre-check, the writes)
  runs on every pool moment, the variant included. spotlight.snap never snaps a ruling-104 variant outward.
- package_pin seals segments; pk["spotlight"] (with derived_from) rides on the pin outside the seal.

THE CHANGE (the diff follows): the builder's path for the orchestrator's DIRECTIVE.
1. tests/package/proof_ledger.py:
   - DIRECTIVES = tests/package/proof/RULING_104_DIRECTIVES.json, written by the builder ONLY on the orchestrator's
     written yes, quoting it.
   - directives(path) reads {"directives": [{"parent", "ends", "alternative_to", "by", "why"}]}. An absent or
     unreadable file, or a malformed row, gives no directive (the rules stand).
   - with_variants passes them to for_pool.
   - spot_place(pk, again, now) is the pin-time ruling-90 check through spotlight.day_taken. It also returns the story
     the package is the alternative to, which record_spotlit then records.
2. pipeline/tail_variant.py:
   - directive_variant(m, src, ctx, d): the variant ending at the longest earlier sentence boundary whose words END as
     d["ends"] (canon tokens), recorded with derived_from.directive and derived_from.alternative_to.
   - for_pool(..., directives): a NAMED parent gets the directive's variant, in its place, whatever its pre-check says.
     No variant when no boundary matches (noted).
3. pipeline/spotlight.py: day_taken(spotlit, channel_id, day, alternative_to) is the ONE rule for the pool and the pin.
   A channel's day is taken by any record of it that day, except the one story the moment is the named alternative to.
   An alternative to another story, a moment with no directive, or a record without a story_id admits no one.
4. Tests in test_ruling_104.py (+4) and 10 mutations, each killed.

ATTACK:
(a) Can anything be sealed through this path WITHOUT a directive file the builder wrote (absent, unreadable, malformed,
    another parent)? Can a directive admit a second spotlight that is NOT the named alternative, or a third one?
(b) Does the directive's variant still face every gate (nothing skipped or inherited from the full clip)? Can it end
    mid-sentence, at the parent's own end, or anywhere other than the named ending?
(c) Can the full clip 3f481f5a and its alternative both reach a render without the orchestrator choosing? (The builder
    seals; the integrator launches.)
(d) Any change to ruling 104's hold, cut or ceiling triggers, or to ruling 90 for every moment without a directive?
(e) Anything else that could seal a wrong pin or spend without a directive.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

