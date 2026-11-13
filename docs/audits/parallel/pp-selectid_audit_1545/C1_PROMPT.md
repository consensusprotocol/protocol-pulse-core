# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1545
# Branch: pp-selectid
# Generated: 2026-11-13 15:23 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1545/C1_STEP.diff (378 lines)
```
   1 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
   2 | index 4bd16b6..fb57478 100644
   3 | --- a/pipeline/speakers.py
   4 | +++ b/pipeline/speakers.py
   5 | @@ -18,12 +18,24 @@ Evidence is text, and code checks it:
   6 |    A source line alone never names a clip's speaker: a title that names a guest does not show who speaks a given
   7 |    clip. Otherwise the speaker is "unknown", with why, and every person the source names is still listed (people) for
   8 |    tagging.
   9 | --> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed"}.
  10 | +RULING 69 (orchestrator 15:29 Nov 13): "the attribution step reads the caption turn markers and addresses by name
  11 | +across the whole turn that contains the clip, not only the windows around it; a speaker is named when the turn
  12 | +structure plus one address or self-introduction shows it." captions() reads the episode's caption record with its
  13 | +speaker-change markers ('>>'); turn_of() finds, in code, the ONE turn that holds the clip (no marker inside it), across
  14 | +another person's interjections of at most BACKCHANNEL_WORDS words (A, a one-word "Yeah." by B, A again: one turn of A).
  15 | +The verdict quotes any address by name and any self-introduction inside that turn; check_turn() keeps one only when its
  16 | +quote is verbatim in the turn and holds a name of one of the people. A self-introduction names its speaker; an address
  17 | +names the OTHER person only when the source's lines name exactly two people. A lower third (ruling 70) is one more
  18 | +piece of evidence, never alone: it names nobody by itself, and one that contradicts the decision makes it "unknown".
  19 | +-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed",
  20 | +"turn" (ruling 69's evidence, when a caption turn was read)}.
  21 |  "people" means named in the source's own lines. Code verifies that the name is in the line it cites; the role
  22 |  (host / guest / other) is the verdict's reading of that line, shown beside it for the reader (audit 0007 C1 K3: qwen,
  23 |  glm). A call that fails is retried once with a new seed; a second failure stays "unknown" with measured false, which
  24 |  claims no name (audit 0007 C1 K2).
  25 |  """
  26 | +import hashlib
  27 | +import html
  28 |  import json
  29 |  import os
  30 |  import re
  31 | @@ -37,6 +49,10 @@ MAX_DESCRIPTION_LINES = 60
  32 |  ROLES = ("host", "guest", "other")
  33 |  UNKNOWN = "unknown"
  34 |  STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")
  35 | +INGEST_STORE = os.path.join(os.environ.get("PP_INGEST", "/home/ultron/worktrees/pp-ingest"), "data", "editorial")
  36 | +BACKCHANNEL_WORDS = 3                     # ruling 69: another person's interjection this short does not end a turn
  37 | +TURN_MAX_CHARS = 12000                    # the turn shown to the verdict (a longer one is cut around the clip)
  38 | +MARKER_TOL_S = 0.5                        # caption lines carry their display time: a marker this near an edge is it
  39 |  
  40 |  PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.
  41 |  
  42 | @@ -49,6 +65,10 @@ THE SOURCE'S OWN LINES (its title, its channel and its description, one per line
  43 |  THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
  44 |  {context}
  45 |  
  46 | +THE CLIP'S TURN (from the episode's own captions, whose markers show where the speaker changes; the clip lies inside
  47 | +this one turn of ONE speaker, other people's interjections of at most three words left out):
  48 | +{turn}
  49 | +
  50 |  Do this:
  51 |  1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
  52 |     source line that names them, copied character for character.
  53 | @@ -58,6 +78,10 @@ Do this:
  54 |     Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
  55 |     A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
  56 |     shows it, the speaker is "unknown", and "why" says what is missing.
  57 | +3. In THE CLIP'S TURN only (when one is given), find: (a) an ADDRESS BY NAME, where the speaker of the turn speaks TO one
  58 | +   of the people by name ("..., Scott?", "Mark, what do you think"), not merely about them; (b) a SELF-INTRODUCTION,
  59 | +   where the speaker of the turn names themself ("I'm Mark Yusko", "this is Natalie"). For each, copy at least three
  60 | +   exact words from the turn holding the name, and give the person as listed in step 1. None found: null.
  61 |  
  62 |  Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
  63 |  first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
  64 | @@ -66,7 +90,9 @@ speak in this episode, and nothing in or around the clip shows which one this is
  65 |  Return ONLY this JSON object:
  66 |  {{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
  67 |   "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
  68 | - "why": "..."}}}}
  69 | + "why": "..."}},
  70 | + "turn": {{"address": {{"name": "<the person addressed>", "quote": "<exact words>"}} or null,
  71 | +          "self_intro": {{"name": "<the person>", "quote": "<exact words>"}} or null}}}}
  72 |  
  73 |  Remember: copy every line and the basis exactly; "unknown" whenever the transcript does not show who speaks."""
  74 |  
  75 | @@ -117,6 +143,123 @@ def context(src, k0, k1, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
  76 |      return say(a, k0 - 1), say(k0, k1), say(k1 + 1, b)
  77 |  
  78 |  
  79 | +def captions(video_id, stores=None):
  80 | +    """RULING 69: the episode's caption record WITH speaker-change markers ('>>'): transcript.yt_auto.json from the
  81 | +    first store whose copy carries any (the main tree's, then pp-ingest's: a live episode's captions arrive later).
  82 | +    -> ([(t, text, opens_turn)] in caption order, {"file", "sha256"}), or (None, None). Rolling repeats of a line are
  83 | +    read once; a '>>' inside a line opens a turn there."""
  84 | +    for st in stores or (STORE, INGEST_STORE):
  85 | +        p = os.path.join(st, "transcripts", video_id, "transcript.yt_auto.json")
  86 | +        try:
  87 | +            with open(p, "rb") as f:
  88 | +                raw = f.read()
  89 | +            segs = json.loads(raw).get("segments") or []
  90 | +        except (OSError, ValueError, AttributeError):
  91 | +            continue
  92 | +        units, last, pending = [], None, False
  93 | +        for s in segs:
  94 | +            t = html.unescape(str(s.get("text") or "")).strip()
  95 | +            if not t or t == last:
  96 | +                continue
  97 | +            last = t
  98 | +            for k, part in enumerate(t.split(">>")):
  99 | +                opens, part = (k > 0) or pending, part.strip()
 100 | +                pending = opens and not part              # a bare '>>': the next words open the turn
 101 | +                if part:
 102 | +                    units.append((float(s["start"]), part, opens))
 103 | +        if any(u[2] for u in units):
 104 | +            return units, {"file": p, "sha256": hashlib.sha256(raw).hexdigest()}
 105 | +    return None, None
 106 | +
 107 | +
 108 | +def turn_of(units, start, end, bc=BACKCHANNEL_WORDS, tol=MARKER_TOL_S):
 109 | +    """RULING 69: the ONE turn of one speaker that holds the clip [start, end], from the caption markers -> ({"text",
 110 | +    "start", "end", "backchannels": [the interjections skipped]}, None) or (None, why). The turn runs from the last
 111 | +    marker at or before the clip to the next marker after it; across a stretch of at most `bc` words between two
 112 | +    markers (another person's interjection) it goes on, both ways: the speaker before and after it is the same."""
 113 | +    if not units:
 114 | +        return None, "no caption record with speaker-change markers"
 115 | +    opens = [i for i, u in enumerate(units) if u[2]]
 116 | +    if any(start + tol < units[i][0] < end - tol for i in opens):
 117 | +        return None, "a speaker-change marker falls inside the clip"
 118 | +    before = [i for i in opens if units[i][0] <= start + tol]
 119 | +    if not before:
 120 | +        return None, "no speaker-change marker before the clip"
 121 | +    nxt = lambda i: min([j for j in opens if j > i], default=len(units))
 122 | +    prv = lambda i: max([j for j in opens if j < i], default=None)
 123 | +    words = lambda i, j: sum(len(units[k][1].split()) for k in range(i, j))
 124 | +    a = before[-1]
 125 | +    b = nxt(a)
 126 | +    spans, skipped = [(a, b)], []
 127 | +    while b < len(units) and nxt(b) < len(units) and words(b, nxt(b)) <= bc:   # A | b: B's interjection | A again
 128 | +        skipped.append(" ".join(units[k][1] for k in range(b, nxt(b))))
 129 | +        spans.append((nxt(b), nxt(nxt(b))))
 130 | +        b = nxt(nxt(b))
 131 | +    while prv(a) is not None and prv(prv(a)) is not None and words(prv(a), a) <= bc:   # A again | B's | the turn
 132 | +        p = prv(a)
 133 | +        skipped.insert(0, " ".join(units[k][1] for k in range(p, a)))
 134 | +        spans.insert(0, (prv(p), p))
 135 | +        a = prv(p)
 136 | +    idx = [k for x, y in spans for k in range(x, y)]
 137 | +    text = " ".join(units[k][1] for k in idx)
 138 | +    if len(text) > TURN_MAX_CHARS:                       # cut around the clip, never losing it
 139 | +        mid = next((n for n, k in enumerate(idx) if units[k][0] >= start - tol), 0)
 140 | +        lo = len(" ".join(units[k][1] for k in idx[:mid]))
 141 | +        a0 = max(0, min(lo - TURN_MAX_CHARS // 2, len(text) - TURN_MAX_CHARS))
 142 | +        text = text[a0:a0 + TURN_MAX_CHARS]
 143 | +    return {"text": text, "start": units[idx[0]][0], "end": units[idx[-1]][0], "backchannels": skipped}, None
 144 | +
 145 | +
 146 | +def check_turn(t, people, turn_text):
 147 | +    """RULING 69: the verdict's turn evidence, kept only where code sees it -> {"address", "self_intro"} (each a
 148 | +    {"name", "quote"} or None). A quote stands when it is >= BASIS_MIN_WORDS words, verbatim in the turn, and holds a
 149 | +    word of the person's name; the person must be one of the people."""
 150 | +    out = {"address": None, "self_intro": None}
 151 | +    if not isinstance(t, dict) or not turn_text:
 152 | +        return out
 153 | +    for k in out:
 154 | +        x = t.get(k)
 155 | +        if not isinstance(x, dict) or not isinstance(x.get("name"), str) or not isinstance(x.get("quote"), str):
 156 | +            continue
 157 | +        who = next((p for p in people if _norm(p["name"]) == _norm(x["name"])), None)
 158 | +        q = x["quote"]
 159 | +        if who is not None and len(_norm(q).split()) >= BASIS_MIN_WORDS and _within(q, turn_text) and \
 160 | +                any(_within(w, q) for w in _norm(who["name"]).split() if len(w) > 1):
 161 | +            out[k] = {"name": who["name"], "quote": q.strip()}
 162 | +    return out
 163 | +
 164 | +
 165 | +def decide(rec, turn_ev, people, lower_third=None):
 166 | +    """RULING 69: the speaker from the turn evidence, beside the basis rule's (check) -> the record. A self-introduction
 167 | +    names its speaker; an address names the other person only when the source's lines name exactly two. Two rules that
 168 | +    name different people, or a lower third that contradicts the decision, are "unknown". A lower third alone names
 169 | +    nobody (ruling 70: one more piece of evidence, never alone)."""
 170 | +    by = None
 171 | +    if turn_ev.get("self_intro"):
 172 | +        by = (turn_ev["self_intro"]["name"], f"self-introduction in the clip's turn: {turn_ev['self_intro']['quote']}")
 173 | +    elif turn_ev.get("address"):
 174 | +        others = [p for p in people if _norm(p["name"]) != _norm(turn_ev["address"]["name"])]
 175 | +        if len(people) == 2 and len(others) == 1:
 176 | +            by = (others[0]["name"], f"addresses {turn_ev['address']['name']} in the clip's turn: "
 177 | +                                     f"{turn_ev['address']['quote']}")
 178 | +    out = dict(rec)
 179 | +    if by is not None:
 180 | +        p = next(p for p in people if _norm(p["name"]) == _norm(by[0]))
 181 | +        if rec["name"] != UNKNOWN and _norm(rec["name"]) != _norm(p["name"]):
 182 | +            return dict(rec, name=UNKNOWN, role=None, line=None, basis=None,
 183 | +                        why=f"the clip's turn shows {p['name']!r} but the transcript basis shows {rec['name']!r}")
 184 | +        out.update(name=p["name"], role=p["role"], line=p["line"], basis=by[1])
 185 | +    lt = lower_third if isinstance(lower_third, str) and _norm(lower_third) else None
 186 | +    if lt is not None:
 187 | +        hit = next((p for p in people if any(_within(w, lt) for w in _norm(p["name"]).split() if len(w) > 2)), None)
 188 | +        if out["name"] != UNKNOWN and hit is not None and _norm(hit["name"]) != _norm(out["name"]):
 189 | +            return dict(out, name=UNKNOWN, role=None, line=None, basis=None,
 190 | +                        why=f"the lower third {lt!r} contradicts {out['name']!r}")
 191 | +        if out["name"] != UNKNOWN and hit is not None:
 192 | +            out["basis"] = f"{out['basis']}; the lower third reads {lt!r}"
 193 | +    return out
 194 | +
 195 | +
 196 |  def _json(text):
 197 |      """The reply's JSON object: its outermost {...}, whatever fence or prose surrounds it (audit 0007 C1 glm P1-2,
 198 |      C2 grok P2-1)."""
 199 | @@ -158,8 +301,9 @@ def check(v, lines, clip, around):
 200 |      return rec
 201 |  
 202 |  
 203 | -def attribute(router, seg, src, meta, seed=7):
 204 | -    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false."""
 205 | +def attribute(router, seg, src, meta, seed=7, caps=None, lower_third=None):
 206 | +    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false.
 207 | +    caps: captions(video id) (ruling 69: the turn markers), read by the caller."""
 208 |      import providers as P
 209 |      base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
 210 |      if src is None or "k0" not in seg or "k1" not in seg:
 211 | @@ -168,11 +312,23 @@ def attribute(router, seg, src, meta, seed=7):
 212 |      if not lines:
 213 |          return dict(base, why="the source's title, channel and description are not in the store", measured=True)
 214 |      before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
 215 | -    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip())
 216 | +    units, cap_src = caps if caps else (None, None)
 217 | +    turn, turn_why = turn_of(units, float(seg["start"]), float(seg["end"])) if units else (None, "no caption record "
 218 | +                                                                                                 "with speaker-change "
 219 | +                                                                                                 "markers")
 220 | +    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip(),
 221 | +                           turn=turn["text"] if turn else f"(none: {turn_why})")
 222 |      r = None
 223 |      try:
 224 |          r = router.call("speaker_verdict", prompt, 900, seed)
 225 | -        rec = check(_json(r.text), lines, clip, f"{before} {after}")
 226 | +        v = _json(r.text)
 227 | +        rec = check(v, lines, clip, f"{before} {after}")
 228 | +        ev = check_turn(v.get("turn"), rec["people"], turn["text"] if turn else "")
 229 | +        rec = decide(rec, ev, rec["people"], lower_third)
 230 | +        rec["turn"] = {"read": turn is not None, "why": turn_why, **({"source": cap_src, "start": turn["start"],
 231 | +                                                                      "end": turn["end"],
 232 | +                                                                      "backchannels": turn["backchannels"]}
 233 | +                                                                     if turn else {}), **ev}
 234 |      except Exception as e:                      # any failure claims no name (audit 0007 C1, glm P1-1): Router.call
 235 |          if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)):    # re-raises a back-end's own
 236 |              router.reject(r)                                                         # error
 237 | @@ -180,7 +336,7 @@ def attribute(router, seg, src, meta, seed=7):
 238 |      return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 239 |  
 240 |  
 241 | -def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 242 | +def attribute_package(router, pk, sources, meta_for=store_meta, log=print, captions_for=captions):
 243 |      """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 244 |      for i, s in enumerate(pk["segments"]):
 245 |          try:
 246 | @@ -188,9 +344,11 @@ def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 247 |          except KeyError:
 248 |              src = None                                        # -> "unknown", not measured: never a name
 249 |          meta = meta_for(s["video_id"])
 250 | -        sp = attribute(router, s, src, meta)
 251 | +        caps = captions_for(s["video_id"])                    # ruling 69: the caption turn markers
 252 | +        lt = ((s.get("visual") or {}).get("lower_third") or {}).get("name")   # ruling 70: one more piece, never alone
 253 | +        sp = attribute(router, s, src, meta, caps=caps, lower_third=lt)
 254 |          if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
 255 | -            sp = attribute(router, s, src, meta, seed=8)
 256 | +            sp = attribute(router, s, src, meta, seed=8, caps=caps, lower_third=lt)
 257 |          s["speaker"] = sp
 258 |          log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
 259 |              + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
 260 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 261 | index f3230cd..a08dbac 100644
 262 | --- a/tests/package/test_speakers.py
 263 | +++ b/tests/package/test_speakers.py
 264 | @@ -166,6 +166,113 @@ class TestAttribute(unittest.TestCase):
 265 |          self.assertEqual(r.calls, [])                                # nothing to ask: no call is paid
 266 |  
 267 |  
 268 | +CAPS = [  # the episode's own captions around the clip of the 13:38 pin (mKNAcOFMYD4), with their turn markers
 269 | +    (694.40, "&gt;&gt; Tell that to his wife."), (696.24, "&gt;&gt; No. And here's the thing is cheaters"),
 270 | +    (700.72, "cheat. Liars lie."), (750.64, "I'll tell you, this is my biggest fear"),
 271 | +    (753.60, "like of all No, second biggest. My"), (755.76, "biggest fear is that I go to the bank"),
 272 | +    (762.08, "me and that's why that's why we Bitcoin."), (764.80, "My second biggest fear and th this is"),
 273 | +    (894.64, "And you know, Reddit's a great example."), (908.24, "&gt;&gt; Yeah."),
 274 | +    (909.36, "&gt;&gt; And now Reddit stock is going like this"),
 275 | +    (944.00, "supposed to call him super intelligent,"), (945.28, "Scott? Well, because the president and"),
 276 | +    (956.32, "&gt;&gt; it's I Yeah, I I just, you know, it just")]
 277 | +TWO = [{"name": "Scott Melker", "role": "host", "line": "channel: Scott Melker"},
 278 | +       {"name": "Mark Yusko", "role": "guest", "line": "title: Wall Street's Bitcoin Bet l Mark Yusko"}]
 279 | +
 280 | +
 281 | +def store_with(d, vid, caps, repeat=False):
 282 | +    os.makedirs(os.path.join(d, "transcripts", vid))
 283 | +    segs = [{"start": t, "end": t + 1, "text": x} for t, x in caps]
 284 | +    if repeat:                                    # rolling auto captions repeat a line
 285 | +        segs = [x for sg in segs for x in (sg, dict(sg))]
 286 | +    with open(os.path.join(d, "transcripts", vid, "transcript.yt_auto.json"), "w") as f:
 287 | +        json.dump({"segments": segs, "transcript_method": "yt_auto:en-orig"}, f)
 288 | +
 289 | +
 290 | +class TestRuling69Turn(unittest.TestCase):
 291 | +    """RULING 69 (15:29): the attribution reads the caption turn markers and the addresses by name across the whole
 292 | +    turn that contains the clip; a speaker is named when the turn structure plus one address or self-introduction
 293 | +    shows it; a lower third is one more piece of evidence, never alone."""
 294 | +
 295 | +    def turn(self):
 296 | +        import tempfile
 297 | +        with tempfile.TemporaryDirectory() as d:
 298 | +            store_with(d, "v", CAPS, repeat=True)
 299 | +            units, src = SP.captions("v", stores=(os.path.join(d, "missing"), d))
 300 | +        return units, src
 301 | +
 302 | +    def test_the_turn_holding_the_clip_runs_across_a_one_word_interjection(self):
 303 | +        units, src = self.turn()
 304 | +        self.assertEqual(len(units), len(CAPS))                                   # a repeated line is read once
 305 | +        self.assertEqual(sum(u[2] for u in units), 5)
 306 | +        self.assertEqual(len(src["sha256"]), 64)
 307 | +        t, why = SP.turn_of(units, 755.454, 764.214)
 308 | +        self.assertIsNone(why)
 309 | +        self.assertEqual((t["start"], t["end"], t["backchannels"]), (696.24, 945.28, ["Yeah."]))
 310 | +        self.assertTrue(SP._within("super intelligent, Scott?", t["text"]))       # the address, across "Yeah."
 311 | +        self.assertNotIn("Tell that to his wife", t["text"])
 312 | +        self.assertFalse(SP._within("it's I Yeah", t["text"]))                    # the next real turn is out
 313 | +        self.assertEqual(SP.turn_of(units, 905.0, 912.0)[1], "a speaker-change marker falls inside the clip")
 314 | +        self.assertEqual(SP.turn_of(units, 600.0, 610.0)[1], "no speaker-change marker before the clip")
 315 | +        t2, _ = SP.turn_of(units, 944.0, 946.0)                                    # the same turn, seen from after
 316 | +        self.assertEqual((t2["start"], t2["backchannels"]), (696.24, ["Yeah."]))  # the interjection: both ways
 317 | +
 318 | +    def test_an_address_names_the_other_of_two_people_and_code_checks_the_quote(self):
 319 | +        units, _ = self.turn()
 320 | +        text = SP.turn_of(units, 755.454, 764.214)[0]["text"]
 321 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 322 | +        ev = SP.check_turn({"address": {"name": "Scott Melker", "quote": "call him super intelligent, Scott?"}},
 323 | +                           TWO, text)
 324 | +        out = SP.decide(rec, ev, TWO)
 325 | +        self.assertEqual((out["name"], out["role"]), ("Mark Yusko", "guest"))
 326 | +        self.assertIn("addresses Scott Melker in the clip's turn", out["basis"])
 327 | +        three = TWO + [{"name": "Arthur Hayes", "role": "other", "line": "Arthur Hayes on the AI trade"}]
 328 | +        self.assertEqual(SP.decide(rec, ev, three)["name"], SP.UNKNOWN)          # one of three is not excluded enough
 329 | +        for bad in ({"name": "Scott Melker", "quote": "call him super smart, Scott?"},      # not in the turn
 330 | +                    {"name": "Scott Melker", "quote": "the president and his"},              # no name of his
 331 | +                    {"name": "Jeff Booth", "quote": "call him super intelligent, Scott?"},   # not one of the people
 332 | +                    {"name": "Scott Melker", "quote": "Scott?"}):                            # under three words
 333 | +            self.assertIsNone(SP.check_turn({"address": bad}, TWO, text)["address"], bad)
 334 | +        intro = SP.check_turn({"self_intro": {"name": "Mark Yusko", "quote": "biggest fear is that"}}, TWO, text)
 335 | +        self.assertIsNone(intro["self_intro"])                                    # the quote must hold the name
 336 | +
 337 | +    def test_a_self_introduction_names_its_speaker_and_conflicts_are_unknown(self):
 338 | +        text = "Good morning everyone, I'm Mark Yusko and today we talk about Bitcoin."
 339 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 340 | +        ev = SP.check_turn({"self_intro": {"name": "Mark Yusko", "quote": "I'm Mark Yusko and today"}}, TWO, text)
 341 | +        self.assertEqual(SP.decide(rec, ev, TWO)["name"], "Mark Yusko")
 342 | +        named = dict(rec, name="Scott Melker", role="host", line="channel: Scott Melker", basis="b c d")
 343 | +        self.assertEqual(SP.decide(named, ev, TWO)["name"], SP.UNKNOWN)          # the two rules disagree
 344 | +
 345 | +    def test_a_lower_third_never_names_alone_and_a_contradicting_one_is_unknown(self):
 346 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 347 | +        none = {"address": None, "self_intro": None}
 348 | +        self.assertEqual(SP.decide(rec, none, TWO, lower_third="Mark W. Yusko")["name"], SP.UNKNOWN)
 349 | +        ev = {"address": {"name": "Scott Melker", "quote": "super intelligent, Scott?"}, "self_intro": None}
 350 | +        agree = SP.decide(rec, ev, TWO, lower_third="Mark W. Yusko")
 351 | +        self.assertEqual(agree["name"], "Mark Yusko")
 352 | +        self.assertIn("the lower third reads 'Mark W. Yusko'", agree["basis"])
 353 | +        self.assertEqual(SP.decide(rec, ev, TWO, lower_third="SCOTT MELKER")["name"], SP.UNKNOWN)
 354 | +
 355 | +    def test_attribute_reads_the_turn_and_records_its_evidence(self):
 356 | +        units, src = self.turn()
 357 | +        v = {"people": [{"name": "Scott Melker", "role": "host", "line": "channel: Natalie Brunell"},
 358 | +                        {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit"}],
 359 | +             "speaker": {"name": "unknown", "basis": "", "why": "nothing in the window"},
 360 | +             "turn": {"address": {"name": "Jeff Booth", "quote": "call him super intelligent, Scott?"},
 361 | +                      "self_intro": None}}
 362 | +        seg = {"k0": 2, "k1": 2, "start": 755.454, "end": 764.214}
 363 | +        r = Canned(json.dumps(v))
 364 | +        sp = SP.attribute(r, seg, source(SENTS), META, caps=(units, src))
 365 | +        self.assertIn("THE CLIP'S TURN", r.calls[0][1])
 366 | +        self.assertIn("super intelligent, Scott?", r.calls[0][1])
 367 | +        self.assertEqual(sp["name"], "unknown")       # "Scott Melker" is not on a source line here: not a person,
 368 | +        self.assertTrue(sp["turn"]["read"])            # and the quote holds no name of Jeff Booth: nothing stands
 369 | +        self.assertEqual((sp["turn"]["source"]["sha256"], sp["turn"]["backchannels"]), (src["sha256"], ["Yeah."]))
 370 | +        sp2 = SP.attribute(Canned(json.dumps(v)), seg, source(SENTS), META)               # no captions: as before
 371 | +        self.assertEqual((sp2["turn"]["read"], sp2["turn"]["why"]), (False, "no caption record with speaker-change "
 372 | +                                                                             "markers"))
 373 | +
 374 | +
 375 |  class TestPinCarriesTheSpeaker(unittest.TestCase):
 376 |      def pk(self, sp):
 377 |          g = {k: {"status": "PASS", "replayed": False} for k in package_pin.REQUIRED_GATES}
 378 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder that seals medley pins). Your role: a
strict reviewer of a step that NAMES real people in a sealed pin (PBX tags them publicly). A wrong name is worse than
"unknown". Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static): pipeline/speakers.py attributes each clip's speaker.
- One verdict (role speaker_verdict, one model call) gets the source's own lines (title, channel, description) and 8
  sentences of the word record around the clip, in which turns are NOT marked.
- It proposes the people the source names and who speaks the clip, with a basis quote.
- check() keeps a person only if a source line names them, and a speaker only if the basis (>= 3 words) is verbatim in
  the clip or the transcript around it. Otherwise the speaker is "unknown".
- The 13:38 pin's clip 3 (mKNAcOFMYD4, Scott Melker's live show with the guest Mark Yusko) came out "unknown", though
  the episode's own YouTube captions mark speaker turns with ">>". The clip lies in one turn (opening at 696.24) that
  runs, across the other person's one-word ">> Yeah." (908.24), to an address "...super intelligent, Scott?" (945.28).

The ruling this diff implements (ORCHESTRATOR 15:29 Nov 13, verbatim):
"RULING 69: the attribution step reads the caption turn markers and addresses by name across the whole turn that
contains the clip, not only the windows around it; a speaker is named when the turn structure plus one address or
self-introduction shows it. Audit, then it applies to new pins."
And ruling 70's part that touches this step: "lower_third feeds ruling 69 as one more piece of evidence, never alone."

The change (pipeline/speakers.py, tests/package/test_speakers.py):
1. captions(video_id): reads transcript.yt_auto.json from the first store whose copy carries any '>>' (the main tree's
   store, then pp-ingest's, where a live episode's captions arrive later).
   - It returns units [(t, text, opens_turn)] plus {file, sha256}.
   - Rolling repeats of a line are read once; '>>' is HTML-unescaped; a '>>' inside a line opens a turn there; a bare
     '>>' opens the turn at the next words.
2. turn_of(units, start, end), in code. It returns None with a reason when a marker falls inside the clip, or no marker
   precedes it. Otherwise:
   - the turn runs from the last marker at or before the clip to the next marker;
   - it continues across another person's interjection of <= BACKCHANNEL_WORDS (3) words between two markers, in BOTH
     directions (A, then B's "Yeah.", then A again: one turn of A);
   - the interjections are recorded; the turn is cut to TURN_MAX_CHARS around the clip.
3. The verdict's prompt adds THE CLIP'S TURN and a step 3: quote (>= 3 exact words) any ADDRESS BY NAME (the turn's
   speaker speaking TO one of the people) and any SELF-INTRODUCTION in the turn. The reply gains
   "turn": {"address", "self_intro"}.
4. check_turn() keeps one only when its quote is >= 3 words, verbatim in the turn, holds a word of the person's name,
   and the person is one of the people check() kept.
5. decide():
   - A self-introduction names its speaker.
   - An address names the OTHER person ONLY when the source's lines name exactly two people.
   - When the basis rule (check) names someone else: "unknown".
   - A lower third names nobody alone; one that contradicts the decision makes it "unknown"; one that agrees is added
     to the basis.
6. attribute(..., caps, lower_third) records "turn": {read, why, source {file, sha256}, start, end, backchannels,
   address, self_intro}. attribute_package passes captions(video id) and the segment's ruling-70 visual.lower_third.name
   (absent until ruling 70).
7. Tests: TestRuling69Turn (5), on the real clip's caption lines:
   - the turn across "Yeah.", seen from both sides;
   - the refusals of a marker inside the clip and of no marker before it;
   - an address naming the other of two, and not one of three;
   - the quote checks: not in the turn, no name word, not a person, under 3 words;
   - a self-introduction, and a conflict with the basis rule;
   - the lower third never alone, agreeing, contradicting;
   - attribute() end to end.
   test_speakers 21 OK.
On the real record: turn_of finds the turn 696.24-953.52, skips "Yeah.", and holds "super intelligent, Scott?".

Stated readings (say so if you read the ruling differently):
- K1: "the whole turn that contains the clip" = between the captions' own speaker-change markers. One person's
  interjection of at most three words (a backchannel such as "Yeah.") does not end the other's turn: the words on
  both sides of it are the same speaker's. This is the reading the orchestrator accepted for the 945.28 evidence.
- K2: "an address" names the speaker only by elimination, so only when the source's lines name exactly two people.
  With three or more, an address excludes one and names no one.
- K3: the model finds the quotes; code checks every quote against the turn and the people, as check() already does
  for the basis.
- K4: a lower third is evidence that can CONFIRM or VETO a decision, never make one.

Check in particular:
- any path that NAMES someone on less than the turn structure plus an address or self-introduction;
- the backchannel merge (could it join two different speakers' turns?);
- marker parsing (an unescaped '>>', a line split across markers, rolling repeats);
- the turn cut; the prompt; the conflicts.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

