# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0007
# Branch: pp-selectid
# Generated: 2026-11-13 00:08 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0007/C1_STEP.diff (769 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 1709764a..8c184de0 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -212,6 +212,15 @@
   6 |     ],
   7 |     "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
   8 |    },
   9 | +  "speaker_verdict": {
  10 | +   "chain": [
  11 | +    "xai:grok-4.20-0309-reasoning",
  12 | +    "anthropic:claude-opus-5-5",
  13 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  14 | +    "local:gemma3:27b"
  15 | +   ],
  16 | +   "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
  17 | +  },
  18 |    "transcribe": {
  19 |     "chain": [
  20 |      "openai_stt:gpt-4o-transcribe-diarize",
  21 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  22 | index 598db658..aaa361c7 100644
  23 | --- a/pipeline/package_pin.py
  24 | +++ b/pipeline/package_pin.py
  25 | @@ -65,14 +65,15 @@ def recency_problems(segments):
  26 |  
  27 |  def seal(segments, edl_vo, signoff, title, caption, gates):
  28 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
  29 | -    words, the transcript sha, and since ruling 1 (22:40) time_sensitive and source_published_at), the VO the renderer
  30 | -    will speak (intro, bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate
  31 | -    inventory."""
  32 | +    words, the transcript sha, since ruling 1 (22:40) time_sensitive and source_published_at, and since the 00:05 ET
  33 | +    Nov 13 order the speaker record), the VO the renderer will speak (intro, bridges with after_clip), the sign-off,
  34 | +    the ONE title and caption (law L-t), and the gate inventory."""
  35 |      body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
  36 |                            "end": round(float(s["end"]), 3), "text": s["approved_text"],
  37 |                            "transcript_sha256": s.get("transcript_sha256"),
  38 |                            "time_sensitive": s.get("time_sensitive"),             # ruling 1 (22:40): the render clock
  39 | -                          "source_published_at": s.get("source_published_at")}   # checks L-v 3 on these
  40 | +                          "source_published_at": s.get("source_published_at"),   # checks L-v 3 on these
  41 | +                          "speaker": s.get("speaker")}                           # 00:05 ET Nov 13 item 3
  42 |                           for s in segments],
  43 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
  44 |                                                               for b in edl_vo.get("bridges") or []]},
  45 | @@ -80,6 +81,22 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
  46 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
  47 |  
  48 |  
  49 | +def speaker_problems(segments):
  50 | +    """[why] for segments whose speaker record (speakers.attribute) is missing or malformed: the orchestrator's 00:05 ET
  51 | +    Nov 13 order (item 3) has every pin carry, per segment, the speaker's name (or "unknown", never a guess) with its
  52 | +    evidence. A named speaker needs the source line that names them and the basis that shows they speak the clip."""
  53 | +    out = []
  54 | +    for i, s in enumerate(segments):
  55 | +        sp = s.get("speaker")
  56 | +        if not isinstance(sp, dict) or not isinstance(sp.get("name"), str) or not sp["name"].strip():
  57 | +            out.append(f'segment {i}: no speaker record (a name, or "unknown")')
  58 | +        elif not isinstance(sp.get("people"), list) or type(sp.get("measured")) is not bool:
  59 | +            out.append(f"segment {i}: the speaker record states no people list or no measured flag")
  60 | +        elif sp["name"] != "unknown" and not all(isinstance(sp.get(k), str) and sp[k].strip() for k in ("line", "basis")):
  61 | +            out.append(f"segment {i}: speaker {sp['name']!r} is named without the source line and the basis")
  62 | +    return out
  63 | +
  64 | +
  65 |  def gate_problems(gates, required=REQUIRED_GATES):
  66 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
  67 |      if not isinstance(gates, dict):
  68 | @@ -126,7 +143,7 @@ def line_problems(pk):
  69 |  def to_pin(pk, run_name):
  70 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
  71 |                                                                       for x in line_problems(pk)] + \
  72 | -        recency_problems(pk.get("segments") or [])
  73 | +        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or [])
  74 |      if problems:
  75 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
  76 |      segs = []
  77 | @@ -135,6 +152,7 @@ def to_pin(pk, run_name):
  78 |                       "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
  79 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
  80 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
  81 | +                     "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
  82 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
  83 |      edl_vo = {"intro": pk["vo"]["intro"],
  84 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
  85 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
  86 | new file mode 100644
  87 | index 00000000..d903028f
  88 | --- /dev/null
  89 | +++ b/pipeline/speakers.py
  90 | @@ -0,0 +1,170 @@
  91 | +#!/usr/bin/env python3
  92 | +"""pipeline/speakers.py: ORCHESTRATOR 00:05 ET Nov 13, item 3. Every pin segment names its SPEAKER where the source
  93 | +names the person, with the evidence: PBX tags the right people, and law L-v 1 needs it. An unknown speaker is
  94 | +"unknown", never a guess.
  95 | +
  96 | +Evidence is text, and code checks it:
  97 | +- source_lines(meta): the source's own lines, from the store's meta.json (yt-dlp, at acquisition): "title: ...",
  98 | +  "channel: ...", then each description line that is not a bare link.
  99 | +- context(src, k0, k1): the clip's own words in the word record, with CONTEXT_BEFORE sentences before it and
 100 | +  CONTEXT_AFTER after it.
 101 | +- One verdict (role speaker_verdict) proposes, as JSON, two things: the people the source's lines name, each with the
 102 | +  line that names them; and who speaks THIS clip, with a basis quoted from the transcript.
 103 | +- check() keeps only what the text shows:
 104 | +  - a person stands only if their line is part of one of the source's lines and holds their name; the person
 105 | +    carries that WHOLE source line as evidence;
 106 | +  - the speaker is named only if they are one of those people AND the basis (>= BASIS_MIN_WORDS words) is verbatim in
 107 | +    the clip or the transcript around it.
 108 | +  A source line alone never names a clip's speaker: a title that names a guest does not show who speaks a given
 109 | +  clip. Otherwise the speaker is "unknown", with why, and every person the source names is still listed (people) for
 110 | +  tagging.
 111 | +-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed"}.
 112 | +"""
 113 | +import json
 114 | +import os
 115 | +import re
 116 | +
 117 | +import eligibility as E
 118 | +
 119 | +CONTEXT_BEFORE, CONTEXT_AFTER = 8, 2      # sentences of the word record around the clip, for who speaks it
 120 | +BASIS_MIN_WORDS = 3                       # a basis is a phrase, never one word
 121 | +MAX_DESCRIPTION_LINES = 60
 122 | +ROLES = ("host", "guest", "other")
 123 | +UNKNOWN = "unknown"
 124 | +STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")
 125 | +
 126 | +PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.
 127 | +
 128 | +Tone: factual. Name a person only when the text below shows it. "unknown" is a correct, expected answer, and a wrong
 129 | +name is worse than "unknown". Never infer from the topic, the style or the title alone.
 130 | +
 131 | +THE SOURCE'S OWN LINES (its title, its channel and its description, one per line):
 132 | +{lines}
 133 | +
 134 | +THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
 135 | +{context}
 136 | +
 137 | +Do this:
 138 | +1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
 139 | +   source line that names them, copied character for character.
 140 | +2. Decide who speaks the words inside <clip>. Name a person only if the TRANSCRIPT shows it, for example:
 141 | +   - the transcript just before the clip addresses them by name, and the clip answers;
 142 | +   - the clip speaks of their own work, role or company in the first person, and a source line ties that to them.
 143 | +   Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
 144 | +   A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
 145 | +   shows it, the speaker is "unknown", and "why" says what is missing.
 146 | +
 147 | +Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
 148 | +first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
 149 | +speak in this episode, and nothing in or around the clip shows which one this is"}}
 150 | +
 151 | +Return ONLY this JSON object:
 152 | +{{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
 153 | + "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
 154 | + "why": "..."}}}}
 155 | +
 156 | +Remember: copy every line and the basis exactly; "unknown" whenever the transcript does not show who speaks."""
 157 | +
 158 | +
 159 | +def _norm(s):
 160 | +    """Case, punctuation and spacing aside: the text a quote must match."""
 161 | +    return " ".join(re.sub(r"[^\w']+", " ", str(s or "").casefold()).split())
 162 | +
 163 | +
 164 | +def store_meta(video_id, store=STORE):
 165 | +    """The store's meta.json for a video (title, channel, description), or {} when it is not there."""
 166 | +    try:
 167 | +        with open(os.path.join(store, "transcripts", video_id, "meta.json")) as f:
 168 | +            meta = json.load(f)
 169 | +        return meta if isinstance(meta, dict) else {}
 170 | +    except (OSError, ValueError):
 171 | +        return {}
 172 | +
 173 | +
 174 | +def source_lines(meta):
 175 | +    out = []
 176 | +    if isinstance(meta.get("exact_title"), str) and meta["exact_title"].strip():
 177 | +        out.append(f"title: {meta['exact_title'].strip()}")
 178 | +    if isinstance(meta.get("channel_name"), str) and meta["channel_name"].strip():
 179 | +        out.append(f"channel: {meta['channel_name'].strip()}")
 180 | +    desc = meta.get("description") if isinstance(meta.get("description"), str) else ""
 181 | +    for line in desc.split("\n"):
 182 | +        line = line.strip()
 183 | +        if line and not re.fullmatch(r"\S*https?://\S*", line) and len(out) < MAX_DESCRIPTION_LINES + 2:
 184 | +            out.append(line)
 185 | +    return out
 186 | +
 187 | +
 188 | +def context(src, k0, k1, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
 189 | +    """(the sentences before, the clip, the sentences after) in the word record's own words."""
 190 | +    sents = src.sentences
 191 | +    a, b = max(0, k0 - before), min(len(sents) - 1, k1 + after)
 192 | +
 193 | +    def say(i, j):
 194 | +        return E.spoken(src.tokens[sents[i][0]:sents[j][1] + 1]) if i <= j else ""
 195 | +    return say(a, k0 - 1), say(k0, k1), say(k1 + 1, b)
 196 | +
 197 | +
 198 | +def check(v, lines, clip, around):
 199 | +    """The verdict, kept only where the text shows it (never the model's word) -> the speaker record (no backend)."""
 200 | +    if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
 201 | +        raise ValueError("speaker verdict out of contract")
 202 | +    nlines = [_norm(x) for x in lines]
 203 | +    people = []
 204 | +    for p in v["people"]:
 205 | +        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not isinstance(p.get("line"), str):
 206 | +            continue
 207 | +        nn, nl = _norm(p["name"]), _norm(p["line"])
 208 | +        whole = next((lines[i] for i, x in enumerate(nlines) if nl and nl in x), None)
 209 | +        if not nn or whole is None or nn not in _norm(whole) or any(_norm(q["name"]) == nn for q in people):
 210 | +            continue                             # not a source line, or the line does not name them
 211 | +        people.append({"name": p["name"].strip(), "role": p.get("role") if p.get("role") in ROLES else "other",
 212 | +                       "line": whole})
 213 | +    sp = v["speaker"]
 214 | +    name, basis = sp.get("name"), sp.get("basis")
 215 | +    rec = {"name": UNKNOWN, "role": None, "line": None, "basis": None,
 216 | +           "why": str(sp.get("why") or "")[:300], "people": people}
 217 | +    if isinstance(name, str) and _norm(name) not in ("", UNKNOWN):
 218 | +        match = next((p for p in people if _norm(p["name"]) == _norm(name)), None)
 219 | +        nb = _norm(basis)
 220 | +        if match is None:
 221 | +            rec["why"] = f"{name.strip()!r} is not a person the source's lines name"
 222 | +        elif len(nb.split()) < BASIS_MIN_WORDS or not (nb in _norm(clip) or nb in _norm(around)):
 223 | +            rec["why"] = (f"the basis for {name.strip()!r} is not {BASIS_MIN_WORDS}+ words found in the clip or the "
 224 | +                          f"transcript around it")
 225 | +        else:
 226 | +            rec.update(name=match["name"], role=match["role"], line=match["line"], basis=str(basis).strip())
 227 | +    return rec
 228 | +
 229 | +
 230 | +def attribute(router, seg, src, meta, seed=7):
 231 | +    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false."""
 232 | +    import providers as P
 233 | +    base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
 234 | +    if src is None or "k0" not in seg or "k1" not in seg:
 235 | +        return dict(base, why="no word record for the clip's context")
 236 | +    lines = source_lines(meta or {})
 237 | +    if not lines:
 238 | +        return dict(base, why="the source's title, channel and description are not in the store", measured=True)
 239 | +    before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
 240 | +    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip())
 241 | +    r = None
 242 | +    try:
 243 | +        r = router.call("speaker_verdict", prompt, 900, seed)
 244 | +        rec = check(json.loads(r.text.strip()), lines, clip, f"{before} {after}")
 245 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 246 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 247 | +            router.reject(r)
 248 | +        return dict(base, why=f"not measured: {type(e).__name__}: {str(e)[:160]}")
 249 | +    return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 250 | +
 251 | +
 252 | +def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 253 | +    """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 254 | +    for i, s in enumerate(pk["segments"]):
 255 | +        s["speaker"] = attribute(router, s, sources.get(s["video_id"]), meta_for(s["video_id"]))
 256 | +        sp = s["speaker"]
 257 | +        log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
 258 | +            + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
 259 | +            + f"; the source names {[p['name'] for p in sp['people']]}")
 260 | +    return pk
 261 | diff --git a/tests/package/proof_batch.py b/tests/package/proof_batch.py
 262 | new file mode 100644
 263 | index 00000000..785f2bcf
 264 | --- /dev/null
 265 | +++ b/tests/package/proof_batch.py
 266 | @@ -0,0 +1,181 @@
 267 | +#!/usr/bin/env python3
 268 | +"""ORCHESTRATOR 00:05 ET Nov 13 (PBX on the L-y medley: "new batch!"): up to THREE novel L-y medleys, ranked, sealed.
 269 | +
 270 | +Why rebuilds: the four L-y packages of the 20:30 re-run (fresh_20261112_001448, fresh_20261111_213954,
 271 | +fresh_20261111_192645, fresh_20261111_190259) were built with delivered=() and every one reuses delivered moments.
 272 | +Each opens on the hook wdk5JZ9hPzs 3218.1-3221.6 (in 37c5b5f5 and 41f29b1f) and carries c1JGheQBPH4 2403.2-2422.1 (in
 273 | +41f29b1f); 001448 is 41f29b1f clip for clip. The order's item 2 ("no moment reused") therefore rebuilds every one from
 274 | +the remaining moments.
 275 | +
 276 | +build RUN: one universe's medley, built by the packager as it stands (house style in the writer's prompt and in the
 277 | +STYLE lint, recency facts per segment, ruling 5's budget and deadlines):
 278 | +- "now" is the RENDER clock (ruling 1): step A, L-v 3 and currency are judged against tonight.
 279 | +- Novelty: every clip span of --delivered (the delivered pins) and of --exclude (the batch's kept packages) goes to
 280 | +  package.usable as delivered, which drops any moment that overlaps one in the same video (L-p).
 281 | +- --avoid-videos drops every moment of those source videos first ("no source video used twice across the batch if
 282 | +  avoidable"). When such a build finds no package, a second build without the avoidance is the order's "if
 283 | +  avoidable"; it is a separate run with its own tag.
 284 | +- The legs and meters are proof_ly's. Spend goes to the batch's own ledger, SPEND_BATCH.json (estimate ceiling
 285 | +  BATCH_LIMIT_USD). The order's budget is $6 vendor-reported for the batch.
 286 | +Writes tests/package/proof/<RUN>/package_batch_<tag>.json (the package, or why none) and package_batch_<tag>.log.
 287 | +
 288 | +seal RUN --tag T: the kept package's speakers (speakers.attribute_package: the source's own lines and the transcript
 289 | +around each clip; "unknown" unless the text shows it), then the pin through package_pin.to_pin (every gate, recency
 290 | +and speaker check) -> tests/package/proof/<RUN>/MOMENTS_PIN_BATCH_<T>.json; the speakers are written back into
 291 | +package_batch_<T>.json.
 292 | +
 293 | +Usage: python3 tests/package/proof_batch.py build RUN --tag T --delivered PIN ... [--exclude PKG_JSON ...]
 294 | +                                                   [--avoid-videos VID ...]
 295 | +       python3 tests/package/proof_batch.py seal RUN --tag T
 296 | +"""
 297 | +import argparse
 298 | +import json
 299 | +import os
 300 | +import sys
 301 | +import time
 302 | +from datetime import datetime, timezone
 303 | +
 304 | +HERE = os.path.dirname(os.path.abspath(__file__))
 305 | +REPO = os.path.dirname(os.path.dirname(HERE))
 306 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 307 | +sys.path.insert(0, HERE)
 308 | +import eligibility as E  # noqa: E402
 309 | +import moments as M  # noqa: E402
 310 | +import package as PK  # noqa: E402
 311 | +import package_pin  # noqa: E402
 312 | +import proof_ledger as PLG  # noqa: E402
 313 | +import proof_ly as PL  # noqa: E402
 314 | +import providers as P  # noqa: E402
 315 | +import speakers as SP  # noqa: E402
 316 | +
 317 | +OUT = PL.OUT
 318 | +SPEND = os.path.join(OUT, "SPEND_BATCH.json")
 319 | +BATCH_LIMIT_USD = 30.0     # the price-table estimate ceiling for the batch's own ledger (an upper bound; the
 320 | +                           # reported cost ran about 1/8 of it tonight); ruling 5's per-package $1.50 reported and
 321 | +                           # $5 estimate still stop each build; the order's batch budget is $6 vendor-reported
 322 | +
 323 | +
 324 | +def package_spans(paths):
 325 | +    """Every clip span of the batch's kept packages (package_batch_*.json) -> [{video_id, start, end, pin}]."""
 326 | +    out = []
 327 | +    for p in paths:
 328 | +        with open(p) as f:
 329 | +            res = json.load(f)
 330 | +        pk = res.get("package")
 331 | +        if not pk:
 332 | +            raise ValueError(f"{p}: holds no package")
 333 | +        out += [{"video_id": s["video_id"], "start": float(s["start"]), "end": float(s["end"]),
 334 | +                 "pin": f"batch:{os.path.basename(os.path.dirname(p))}"} for s in pk["segments"]]
 335 | +    return out
 336 | +
 337 | +
 338 | +def build(run, tag, delivered, avoid, router, own, used, say, work_dir):
 339 | +    rec_m = json.load(open(os.path.join(PL.PM.OUT, run, "moments.json")))
 340 | +    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
 341 | +    sources = {s.video_id: s for s in words}
 342 | +    now = datetime.now(timezone.utc)
 343 | +    ctx = E.Context(now, PL.PM.PS.REG, ledger=PL.PM.PS.ledger_entries())
 344 | +    moments = [m for m in rec_m["moments"] if m["video_id"] not in avoid]
 345 | +    say(f"  {len(rec_m['moments'])} moments, {len(rec_m['moments']) - len(moments)} on avoided videos out; "
 346 | +        f"{len(delivered)} delivered or kept spans out; now (render clock) {now.isoformat(timespec='seconds')}")
 347 | +    e0, b0 = own["est"], own["best"]
 348 | +    u0 = dict(used)
 349 | +    t0 = time.time()
 350 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 351 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a_now.json"),
 352 | +                   spend=lambda: (own["est"], own["best"]))
 353 | +    res.update(run=run, tag=tag, seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"] - e0, 4),
 354 | +               usd_best_known=round(own["best"] - b0, 4), code=PL.code_sha(), chains=router.chains,
 355 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"), as_of=now.isoformat(), avoid_videos=sorted(avoid),
 356 | +               delivered_spans=delivered,
 357 | +               full={k: round(used[k] - u0[k], 4) for k in ("est", "best", "model_s", "calls")})
 358 | +    if res["package"]:
 359 | +        res["package"]["usd_best_known"] = res["usd_best_known"]
 360 | +        say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known): "
 361 | +            + "; ".join(f"{s['video_id']} {float(s['start']):.1f}-{float(s['end']):.1f}"
 362 | +                        for s in res["package"]["segments"]))
 363 | +    else:
 364 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 365 | +    with open(os.path.join(OUT, run, f"package_batch_{tag}.json"), "w") as f:
 366 | +        json.dump(res, f, indent=1, default=str)
 367 | +    return res
 368 | +
 369 | +
 370 | +def seal(run, tag, router, say):
 371 | +    path = os.path.join(OUT, run, f"package_batch_{tag}.json")
 372 | +    with open(path) as f:
 373 | +        res = json.load(f)
 374 | +    pk = res.get("package")
 375 | +    if not pk:
 376 | +        raise ValueError(f"{path}: holds no package")
 377 | +    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
 378 | +    SP.attribute_package(router, pk, {s.video_id: s for s in words}, log=say)
 379 | +    with open(path, "w") as f:
 380 | +        json.dump(res, f, indent=1, default=str)
 381 | +    out, pin = package_pin.write_pin(pk, f"batch_{tag}_{run}", os.path.join(OUT, run),
 382 | +                                     name=f"MOMENTS_PIN_BATCH_{tag.upper()}.json")
 383 | +    say(f"PIN {os.path.relpath(out, REPO)} {pin['moments_package']['package_sha256']}")
 384 | +    return out, pin
 385 | +
 386 | +
 387 | +def main(argv=None):
 388 | +    ap = argparse.ArgumentParser()
 389 | +    sub = ap.add_subparsers(dest="cmd", required=True)
 390 | +    b = sub.add_parser("build")
 391 | +    b.add_argument("run")
 392 | +    b.add_argument("--tag", required=True)
 393 | +    b.add_argument("--delivered", nargs="+", required=True, metavar="PIN")
 394 | +    b.add_argument("--exclude", nargs="*", default=[], metavar="PKG_JSON", help="the batch's kept packages")
 395 | +    b.add_argument("--avoid-videos", nargs="*", default=[], metavar="VID")
 396 | +    b.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 397 | +    sl = sub.add_parser("seal")
 398 | +    sl.add_argument("run")
 399 | +    sl.add_argument("--tag", required=True)
 400 | +    a = ap.parse_args(argv)
 401 | +    if a.cmd == "seal":
 402 | +        router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND,
 403 | +                          limit_usd=BATCH_LIMIT_USD, chains=PL.chains())
 404 | +        own = PL.meter(router)
 405 | +        with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
 406 | +            def say(s):
 407 | +                print(f"[{a.run}:{a.tag}] {s}", flush=True)
 408 | +                logf.write(s + "\n")
 409 | +                logf.flush()
 410 | +            say(f"=== {time.strftime('%H:%M:%S %Z')} SEAL {a.tag}: speakers, then the pin")
 411 | +            try:
 412 | +                seal(a.run, a.tag, router, say)
 413 | +            except (package_pin.PinRefused, ValueError, OSError) as e:
 414 | +                say(f"PIN REFUSED: {type(e).__name__}: {e}")
 415 | +                return 4
 416 | +            finally:
 417 | +                say(f"  speakers: ${own['est']:.4f} estimate, ${own['best']:.4f} best known")
 418 | +        return 0
 419 | +    try:                                                # read before anything is written (fail closed)
 420 | +        delivered, _, pins = PLG.delivered_pins(a.delivered)
 421 | +        delivered = delivered + package_spans(a.exclude)
 422 | +        if not os.path.exists(os.path.join(PL.PM.OUT, a.run, "moments.json")):
 423 | +            raise ValueError(f"{a.run}: no saved universe")
 424 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 425 | +        print(f"REFUSED: {type(e).__name__}: {e}", file=sys.stderr)
 426 | +        return 2
 427 | +    os.makedirs(a.work_dir, exist_ok=True)
 428 | +    router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND, limit_usd=BATCH_LIMIT_USD,
 429 | +                      chains=PL.chains())
 430 | +    own, used = PL.meter(router), PL.reply_meter(router)
 431 | +    with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
 432 | +        def say(s):
 433 | +            print(f"[{a.run}:{a.tag}] {s}", flush=True)
 434 | +            logf.write(s + "\n")
 435 | +            logf.flush()
 436 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} BATCH medley build {a.tag}, code {PL.code_sha()}, delivered "
 437 | +            f"{[p['story_id'] for p in pins]}, kept {a.exclude}, avoid {sorted(a.avoid_videos)}")
 438 | +        try:
 439 | +            build(a.run, a.tag, delivered, set(a.avoid_videos), router, own, used, say, a.work_dir)
 440 | +        except P.SpendLimit as e:
 441 | +            say(f"STOPPED: {e}")
 442 | +            return 3
 443 | +    return 0
 444 | +
 445 | +
 446 | +if __name__ == "__main__":
 447 | +    sys.exit(main())
 448 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 449 | index e574a0ad..5d344003 100644
 450 | --- a/tests/package/proof_ledger.py
 451 | +++ b/tests/package/proof_ledger.py
 452 | @@ -43,6 +43,7 @@ import package_pin  # noqa: E402
 453 |  import proof_ly as PL  # noqa: E402
 454 |  import proof_saved_runs as PS  # noqa: E402
 455 |  import providers as P  # noqa: E402
 456 | +import speakers as SP  # noqa: E402
 457 |  
 458 |  def delivered_pins(paths):
 459 |      """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 460 | @@ -123,6 +124,7 @@ def main(argv=None):
 461 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 462 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 463 |      if res["package"]:
 464 | +        SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 465 |          try:
 466 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 467 |                                                name="MOMENTS_PIN_LEDGER.json")
 468 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 469 | index 40779901..75193f64 100644
 470 | --- a/tests/package/proof_ly.py
 471 | +++ b/tests/package/proof_ly.py
 472 | @@ -41,6 +41,7 @@ import package as PK  # noqa: E402
 473 |  import package_pin  # noqa: E402
 474 |  import proof_moments as PM  # noqa: E402
 475 |  import providers as P  # noqa: E402
 476 | +import speakers as SP  # noqa: E402
 477 |  
 478 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 479 |  OUT = os.path.join(HERE, "proof")
 480 | @@ -159,6 +160,7 @@ def run_one(run, router, work_dir, log, own, used=None, as_of_now=False):
 481 |      if res["package"]:
 482 |          pk = res["package"]
 483 |          pk["usd_best_known"] = res["usd_best_known"]
 484 | +        SP.attribute_package(router, pk, sources, log=log)                # 00:05 ET Nov 13 item 3: sealed in the pin
 485 |          try:
 486 |              path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name=f"MOMENTS_PIN_LY{suffix.upper()}.json")
 487 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 488 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 489 | index 34762dcd..60a9f85a 100644
 490 | --- a/tests/package/test_angles.py
 491 | +++ b/tests/package/test_angles.py
 492 | @@ -129,6 +129,8 @@ class TestPinAndTruth(unittest.TestCase):
 493 |                            {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 494 |                  "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 495 |                                "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 496 | +                              "speaker": {"name": "unknown", "role": None, "line": None, "basis": None, "why": "t",
 497 | +                                          "people": [], "measured": True},
 498 |                                "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 499 |  
 500 |      def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
 501 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 502 | index 68b37217..6b68f88e 100644
 503 | --- a/tests/package/test_medley.py
 504 | +++ b/tests/package/test_medley.py
 505 | @@ -58,6 +58,15 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
 506 |              "supply_exception": supply}
 507 |  
 508 |  
 509 | +
 510 | +def spk(pk):
 511 | +    """speakers.attribute's record on every segment, as the real flow attaches it before the pin is sealed (the
 512 | +    00:05 ET Nov 13 order, item 3): an unknown speaker, measured, no person named."""
 513 | +    for s in pk.get("segments") or []:
 514 | +        s.setdefault("speaker", {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test",
 515 | +                                 "people": [], "measured": True})
 516 | +    return pk
 517 | +
 518 |  class TestMedleyArithmetic(unittest.TestCase):
 519 |      def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
 520 |          lo, hi = PK.medley_content_range()
 521 | @@ -361,7 +370,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 522 |          pk = self.build()
 523 |          self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
 524 |          pk["gates"] = self.gates(pk)
 525 | -        pin = package_pin.to_pin(pk, "test")
 526 | +        pin = package_pin.to_pin(spk(pk), "test")
 527 |          mp = pin["moments_package"]
 528 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 529 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 530 | @@ -370,16 +379,16 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 531 |              g = self.gates(pk)
 532 |              g.pop(missing)
 533 |              with self.assertRaises(package_pin.PinRefused):
 534 | -                package_pin.to_pin(dict(pk, gates=g), "test")
 535 | +                package_pin.to_pin(spk(dict(pk, gates=g)), "test")
 536 |          with self.assertRaises(package_pin.PinRefused):
 537 | -            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
 538 | +            package_pin.to_pin(spk(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False}))), "test")
 539 |  
 540 |      def test_the_gated_takeaway_must_be_the_spoken_one(self):
 541 |          pk = self.build()
 542 |          pk["gates"] = self.gates(pk)
 543 |          pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
 544 |          with self.assertRaises(package_pin.PinRefused) as cm:
 545 | -            package_pin.to_pin(pk, "test")
 546 | +            package_pin.to_pin(spk(pk), "test")
 547 |          self.assertIn("bridges", str(cm.exception))
 548 |  
 549 |      def test_the_old_shape_keeps_its_slots(self):
 550 | @@ -396,7 +405,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 551 |          b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
 552 |          pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
 553 |          pk0["gates"] = self.gates(pk0)
 554 | -        mp = package_pin.to_pin(pk0, "test")["moments_package"]
 555 | +        mp = package_pin.to_pin(spk(pk0), "test")["moments_package"]
 556 |          self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
 557 |                                          "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
 558 |          self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})
 559 | @@ -530,7 +539,7 @@ class TestBuildLoop(unittest.TestCase):
 560 |          self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
 561 |          self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
 562 |          self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 563 | -        package_pin.to_pin(pk, "test")                    # every required row exactly PASS: the pin is allowed
 564 | +        package_pin.to_pin(spk(pk), "test")                    # every required row exactly PASS: the pin is allowed
 565 |  
 566 |      def test_a_clip_the_second_recogniser_cannot_cut_is_never_offered_to_the_angles(self):
 567 |          rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None], uncuttable={"y"})
 568 | @@ -543,7 +552,7 @@ class TestBuildLoop(unittest.TestCase):
 569 |          self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 570 |          pk = out["package"]
 571 |          self.assertEqual(pk["gates"]["cuttable"]["status"], "PASS")
 572 | -        package_pin.to_pin(pk, "test")                    # build() returns only a package its pin accepts
 573 | +        package_pin.to_pin(spk(pk), "test")                    # build() returns only a package its pin accepts
 574 |  
 575 |      def test_an_excluded_moment_stays_out_of_every_later_angle(self):
 576 |          ms = self.MS + [pm("w", "E", 14.0)]
 577 | @@ -572,7 +581,7 @@ class TestBuildLoop(unittest.TestCase):
 578 |          self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
 579 |          self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 580 |          self.assertIn("no VO line", pk["checks"]["coherence"]["note"])
 581 | -        mp = package_pin.to_pin(pk, "test")["moments_package"]
 582 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 583 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 584 |  
 585 |      def test_no_voice_never_ships_a_join_the_blind_check_flagged(self):
 586 | @@ -667,7 +676,7 @@ class TestNoVoiceRealGates(unittest.TestCase):
 587 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 588 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 589 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 590 | -        mp = package_pin.to_pin(pk, "test")["moments_package"]
 591 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 592 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 593 |  
 594 |      def test_a_published_time_without_an_offset_fails_before_any_paid_verdict(self):
 595 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 596 | new file mode 100644
 597 | index 00000000..edf70db3
 598 | --- /dev/null
 599 | +++ b/tests/package/test_speakers.py
 600 | @@ -0,0 +1,168 @@
 601 | +#!/usr/bin/env python3
 602 | +"""pipeline/speakers.py (ORCHESTRATOR 00:05 ET Nov 13, item 3): every pin segment names its speaker where the source
 603 | +names the person, with the evidence; an unknown speaker is "unknown", never a guess. Offline: the verdict is canned,
 604 | +and code checks every claim against the text."""
 605 | +import json
 606 | +import os
 607 | +import sys
 608 | +import unittest
 609 | +
 610 | +HERE = os.path.dirname(os.path.abspath(__file__))
 611 | +REPO = os.path.dirname(os.path.dirname(HERE))
 612 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 613 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 614 | +import package_pin  # noqa: E402
 615 | +import speakers as SP  # noqa: E402
 616 | +from test_eligibility import source  # noqa: E402
 617 | +
 618 | +META = {"exact_title": "Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
 619 | +        "channel_name": "Natalie Brunell",
 620 | +        "description": "Are we headed toward a future of abundance?\n"
 621 | +                       "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.\n"
 622 | +                       "https://example.com/link\n"}
 623 | +LINES = SP.source_lines(META)
 624 | +SENTS = ["Jeff, you wrote about deflation years ago.", "What do you see now?",
 625 | +         "When I wrote The Price of Tomorrow, I said technology is deflationary.",
 626 | +         "Bitcoin lets that deflation reach everyone.", "That is the point."]
 627 | +
 628 | +
 629 | +def verdict(name, basis, people=None):
 630 | +    return {"people": people if people is not None else [
 631 | +        {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit The Price of Tomorrow"},
 632 | +        {"name": "Natalie Brunell", "role": "host", "line": "channel: Natalie Brunell"}],
 633 | +        "speaker": {"name": name, "basis": basis, "why": "w"}}
 634 | +
 635 | +
 636 | +class Reply:
 637 | +    def __init__(self, text):
 638 | +        self.text, self.backend, self.replayed, self.usage, self.usd, self.seconds = text, "xai:grok", False, {}, 0, 0
 639 | +
 640 | +
 641 | +class Canned:
 642 | +    def __init__(self, text):
 643 | +        self.text, self.calls, self.rejected = text, [], []
 644 | +
 645 | +    def call(self, role, prompt, max_tokens=2000, seed=7, **k):
 646 | +        self.calls.append((role, prompt))
 647 | +        return Reply(self.text)
 648 | +
 649 | +    def reject(self, r):
 650 | +        self.rejected.append(r)
 651 | +
 652 | +
 653 | +class TestSourceLinesAndContext(unittest.TestCase):
 654 | +    def test_the_sources_own_lines_and_never_a_bare_link(self):
 655 | +        self.assertEqual(LINES[:2], ["title: Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
 656 | +                                     "channel: Natalie Brunell"])
 657 | +        self.assertIn("Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.",
 658 | +                      LINES)
 659 | +        self.assertNotIn("https://example.com/link", LINES)
 660 | +        self.assertEqual(SP.source_lines({}), [])
 661 | +
 662 | +    def test_the_context_is_the_word_records_own_sentences_around_the_clip(self):
 663 | +        before, clip, after = SP.context(source(SENTS), 2, 2, before=2, after=1)
 664 | +        self.assertEqual((before, clip, after), (SENTS[0] + " " + SENTS[1], SENTS[2], SENTS[3]))
 665 | +
 666 | +
 667 | +class TestCheck(unittest.TestCase):
 668 | +    clip, around = SENTS[2], SENTS[0] + " " + SENTS[1]
 669 | +
 670 | +    def test_a_person_stands_only_on_a_source_line_that_names_them_and_carries_the_whole_line(self):
 671 | +        people = [{"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit"},     # part of a line
 672 | +                  {"name": "Saifedean Ammous", "role": "guest", "line": "Saifedean Ammous joins me"},      # not a line
 673 | +                  {"name": "Natalie Brunell", "role": "host", "line": "Jeff Booth joins me to revisit"},  # not her line
 674 | +                  {"name": "jeff booth", "role": "guest", "line": "title: Jeff Booth Warning"}]           # twice
 675 | +        rec = SP.check(verdict("unknown", "", people), LINES, self.clip, self.around)
 676 | +        self.assertEqual([(p["name"], p["line"]) for p in rec["people"]], [
 677 | +            ("Jeff Booth", "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our "
 678 | +                           "future.")])
 679 | +
 680 | +    def test_a_speaker_is_named_only_on_a_basis_in_the_clip_or_the_transcript_around_it(self):
 681 | +        rec = SP.check(verdict("Jeff Booth", "When I wrote The Price of Tomorrow"), LINES, self.clip, self.around)
 682 | +        self.assertEqual((rec["name"], rec["role"], rec["basis"]), ("Jeff Booth", "guest",
 683 | +                                                                    "When I wrote The Price of Tomorrow"))
 684 | +        self.assertTrue(rec["line"].startswith("Jeff Booth joins me"))
 685 | +        rec = SP.check(verdict("Jeff Booth", "jeff you wrote about deflation"), LINES, self.clip, self.around)
 686 | +        self.assertEqual(rec["name"], "Jeff Booth")                  # case and punctuation aside, in the context
 687 | +
 688 | +    def test_a_title_that_names_a_guest_never_names_the_clips_speaker(self):
 689 | +        """A basis found only in the source's lines (the title, the description) does not show who speaks a clip."""
 690 | +        for basis in ("Jeff Booth joins me to revisit", "title: Jeff Booth Warning"):
 691 | +            rec = SP.check(verdict("Jeff Booth", basis), LINES, self.clip, self.around)
 692 | +            self.assertEqual(rec["name"], "unknown", basis)
 693 | +            self.assertIn("not 3+ words found in the clip", rec["why"])
 694 | +            self.assertEqual([p["name"] for p in rec["people"]], ["Jeff Booth", "Natalie Brunell"])   # still tagged
 695 | +
 696 | +    def test_a_short_basis_an_unnamed_person_or_an_invented_quote_is_unknown(self):
 697 | +        for name, basis in (("Jeff Booth", "I wrote"), ("Saifedean Ammous", "When I wrote The Price of Tomorrow"),
 698 | +                            ("Jeff Booth", "As I said on my own podcast yesterday")):
 699 | +            rec = SP.check(verdict(name, basis), LINES, self.clip, self.around)
 700 | +            self.assertEqual((rec["name"], rec["basis"], rec["line"]), ("unknown", None, None), (name, basis))
 701 | +
 702 | +    def test_a_verdict_out_of_contract_raises(self):
 703 | +        for bad in ([], {"people": {}, "speaker": {}}, {"people": [], "speaker": "Jeff"}):
 704 | +            with self.assertRaises(ValueError):
 705 | +                SP.check(bad, LINES, self.clip, self.around)
 706 | +
 707 | +
 708 | +class TestAttribute(unittest.TestCase):
 709 | +    seg = {"video_id": "vidA", "k0": 2, "k1": 2}
 710 | +
 711 | +    def test_a_named_speaker_with_its_evidence_and_the_backend(self):
 712 | +        r = Canned(json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")))
 713 | +        rec = SP.attribute(r, self.seg, source(SENTS), META)
 714 | +        self.assertEqual((rec["name"], rec["measured"], rec["backend"]), ("Jeff Booth", True, "xai:grok"))
 715 | +        self.assertEqual(r.calls[0][0], "speaker_verdict")
 716 | +        self.assertIn("<clip>" + SENTS[2] + "</clip>", r.calls[0][1])
 717 | +
 718 | +    def test_a_reply_out_of_contract_is_unknown_not_measured_and_rejected(self):
 719 | +        r = Canned("Jeff Booth, probably")
 720 | +        rec = SP.attribute(r, self.seg, source(SENTS), META)
 721 | +        self.assertEqual((rec["name"], rec["measured"]), ("unknown", False))
 722 | +        self.assertTrue(rec["why"].startswith("not measured"))
 723 | +        self.assertEqual(len(r.rejected), 1)
 724 | +
 725 | +    def test_no_source_lines_or_no_word_record_is_unknown_with_why(self):
 726 | +        r = Canned("{}")
 727 | +        self.assertEqual(SP.attribute(r, self.seg, source(SENTS), {})["why"],
 728 | +                         "the source's title, channel and description are not in the store")
 729 | +        self.assertEqual(SP.attribute(r, self.seg, None, META)["why"], "no word record for the clip's context")
 730 | +        self.assertEqual(r.calls, [])                                # nothing to ask: no call is paid
 731 | +
 732 | +
 733 | +class TestPinCarriesTheSpeaker(unittest.TestCase):
 734 | +    def pk(self, sp):
 735 | +        g = {k: {"status": "PASS", "replayed": False} for k in package_pin.REQUIRED_GATES}
 736 | +        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
 737 | +                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
 738 | +                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
 739 | +                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 740 | +                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 741 | +                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 742 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 743 | +                              "source_published_at": "2026-11-12T01:00:00Z", **({"speaker": sp} if sp else {})}
 744 | +                             for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 745 | +
 746 | +    def test_the_pin_refuses_a_segment_without_a_speaker_record_or_a_named_one_without_evidence(self):
 747 | +        named = {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me", "basis": "When I wrote it",
 748 | +                 "why": "", "people": [], "measured": True}
 749 | +        for sp in (None, {"name": ""}, {"name": "unknown", "people": []}, dict(named, basis=""), dict(named, line=None)):
 750 | +            with self.assertRaises(package_pin.PinRefused, msg=sp):
 751 | +                package_pin.to_pin(self.pk(sp), "r")
 752 | +        pin = package_pin.to_pin(self.pk(named), "r")
 753 | +        self.assertEqual([s["speaker"]["name"] for s in pin["segments"]], ["Jeff Booth", "Jeff Booth"])
 754 | +
 755 | +    def test_the_speaker_is_inside_the_seal(self):
 756 | +        unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
 757 | +                   "measured": True}
 758 | +        pin = package_pin.to_pin(self.pk(unknown), "r")
 759 | +        mp = pin["moments_package"]
 760 | +        self.assertEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"],
 761 | +                                                                 mp["title"], mp["caption"], mp["gates"]))
 762 | +        segs = [dict(s, speaker=dict(s["speaker"], name="Jeff Booth")) for s in pin["segments"]]
 763 | +        self.assertNotEqual(mp["package_sha256"], package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"],
 764 | +                                                                    mp["title"], mp["caption"], mp["gates"]))
 765 | +
 766 | +
 767 | +if __name__ == "__main__":
 768 | +    unittest.main()
 769 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging under law L-y, the MEDLEY of
real clips). It implements the builder's part of the orchestrator's order of 00:05 ET Nov 13: a BATCH of up to three
novel medleys, and item 3, "every pin carries, per segment, the SPEAKER'S NAME where the source's title/description
names the guest, with its evidence (the description line) ... Unknown speaker = say unknown, never guess."

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- no clip span already delivered is used again (L-p);
- time-sensitive words only from a source <= 24 h old, judged on the RENDER clock (L-v 3);
- every pin is sealed: package_sha256 over its segments, VO, title, caption and gate inventory.

The files:
1. pipeline/speakers.py (new): who speaks each pin segment.
   - source_lines(meta): the source's own title / channel / description lines (the store's meta.json).
   - context(src, k0, k1): the word record's sentences around the clip.
   - One verdict call (new role speaker_verdict in model_providers.json) proposes the people the source names and the
     clip's speaker, with quotes.
   - check() keeps only what the text shows:
     - a person needs a source line that names them;
     - a named speaker needs a basis of 3+ words found in the clip or the transcript around it (never a source line
       alone: a title naming a guest does not show who speaks a given clip).
   - Otherwise the speaker is "unknown", with why, and the people the source names stay listed for tagging.
2. pipeline/package_pin.py:
   - speaker_problems(): to_pin refuses a segment without a speaker record, or a named speaker without its line and
     basis;
   - the speaker record is carried on each pin segment and is inside the seal.
3. tests/package/proof_batch.py (new): the batch driver.
   - build: one saved universe's medley, built by the packager on the render clock, with every clip span of the
     delivered pins and of the batch's kept packages passed as delivered, and the kept source videos avoided where
     possible.
   - seal: speakers, then the pin.
4. tests/package/proof_ledger.py and proof_ly.py: speakers are attributed before a pin is written.
5. Tests: tests/package/test_speakers.py (new); fixture updates in test_medley.py / test_angles.py (each pin fixture
   now carries a speaker record, as the real flow attaches it before sealing).

Check, concretely:
(a) Can a WRONG speaker name reach a pin? For example: a title naming a guest while the host speaks the clip; a quote
    that is not in the text; a person the source does not name; a reply out of contract.
(b) Is any failure silent or counted as a pass? A failed call must be "unknown" with measured false, never a name.
(c) Is the speaker record really inside the seal, and does to_pin refuse every malformed record?
(d) Does the batch build keep delivered spans and the batch's kept spans out, on the render clock?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".

