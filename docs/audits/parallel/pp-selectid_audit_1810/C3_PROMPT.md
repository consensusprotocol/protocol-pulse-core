# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1810
# Branch: pp-selectid
# Generated: 2026-11-13 18:22 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1810/C3_STEP.diff (431 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index ea38cca..4e1c4e2 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -18,6 +18,8 @@ record's tried entry and package.load_candidate rebuilds it. A try's outcome cla
   6 |    "line":    its clips passed but a line failed again            -> resting 6 h, then ONE try with fresh writes;
   7 |                                                                      a line failing that try too -> closed
   8 |    "budget":  a budget stopped it before an outcome               -> as it was
   9 | +  "expired": RULING 76 (18:08 Nov 13): a clip's source is over 12 h old on the render clock (expire()) -> closed for
  10 | +             good: "out of the candidates registry, never offered again"
  11 |  Pure functions; the driver (tests/package/proof_ledger.py) reads and writes the file."""
  12 |  from datetime import datetime, timedelta, timezone
  13 |  
  14 | @@ -45,7 +47,7 @@ def outcome(entry, cls, at, build, why=""):
  15 |      entry["history"].append({"build": build, "at": at, "class": cls, "fresh": bool(entry.get("trying_fresh")),
  16 |                               "why": str(why or "")[:300]})
  17 |      entry.pop("trying_fresh", None)
  18 | -    if cls in ("package", "clip"):
  19 | +    if cls in ("package", "clip", "expired"):
  20 |          entry["state"], entry["until"] = "closed", None
  21 |      elif cls == "line":
  22 |          if entry.get("fresh_used"):
  23 | @@ -88,6 +90,32 @@ def seed(reg, record, source):
  24 |      return added
  25 |  
  26 |  
  27 | +def expire(reg, published, now, window_h, notes=None):
  28 | +    """RULING 76 (a): close for good (class "expired") every candidate not yet closed with a clip whose source was
  29 | +    published more than window_h before the render clock `now`, or whose publish time is not known (never assumed
  30 | +    fresh). published: {moment id: published_at}; notes: {key: where its times were read, and whether the read
  31 | +    succeeded}, put in the expiry's why (audit 1810 C2). -> [the keys expired now]."""
  32 | +    out = []
  33 | +    for k, e in reg["candidates"].items():
  34 | +        if e["state"] == "closed":
  35 | +            continue
  36 | +        old = []
  37 | +        for mid in e.get("lineup") or []:
  38 | +            try:
  39 | +                t = _at(published[mid])
  40 | +            except (KeyError, TypeError, ValueError):
  41 | +                old.append(f"{mid}: no known publish time")
  42 | +                continue
  43 | +            age = (now - t).total_seconds() / 3600.0
  44 | +            if age > window_h:
  45 | +                old.append(f"{mid}: {age:.1f} h")
  46 | +        if old:
  47 | +            outcome(e, "expired", now.isoformat(), "ruling 76", f"over {window_h:g} h on the render clock: " +
  48 | +                    "; ".join(old) + (f" [{(notes or {})[k]}]" if (notes or {}).get(k) else ""))
  49 | +            out.append(k)
  50 | +    return out
  51 | +
  52 | +
  53 |  def registered(reg):
  54 |      """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
  55 |      search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
  56 | diff --git a/pipeline/package.py b/pipeline/package.py
  57 | index ad6dd60..04d5f72 100644
  58 | --- a/pipeline/package.py
  59 | +++ b/pipeline/package.py
  60 | @@ -121,9 +121,44 @@ VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than i
  61 |                              "never relate one speaker to another"}
  62 |  
  63 |  
  64 | +SAME_SPEECH_MIN_WORDS = 8         # ruling 76 (b): below this, only an equal text is the same speech
  65 | +SAME_SPEECH_RUN = 3               # only runs of at least this many words in order count: never scattered common words
  66 | +
  67 | +
  68 | +def same_speech(a, b):
  69 | +    """RULING 76 (b): two texts of at least two words are the same speech when they are equal after normalisation
  70 | +    (canon.canon_tokens), or, with the shorter at least SAME_SPEECH_MIN_WORDS long, when at least REPOST_ALIGN_MIN
  71 | +    (ruling 53's 0.80) of the shorter one's words lie in runs of SAME_SPEECH_RUN or more words that the other says in
  72 | +    the same order (difflib's matching blocks): a re-post cut a little differently is still the same speech; a few
  73 | +    common words in common never are. It decides only what is EXCLUDED: a wrong match loses one moment (fail closed),
  74 | +    a missed one would reuse delivered speech."""
  75 | +    import difflib
  76 | +    import canon
  77 | +    ta, tb = canon.canon_tokens(a or ""), canon.canon_tokens(b or "")
  78 | +    short = min(len(ta), len(tb))
  79 | +    if short < 2:
  80 | +        return False
  81 | +    if ta == tb:
  82 | +        return True
  83 | +    if short < SAME_SPEECH_MIN_WORDS:
  84 | +        return False
  85 | +    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
  86 | +    return sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short
  87 | +
  88 | +
  89 | +def expired(m, now):
  90 | +    """RULING 76 (a): the moment's source is more than package_pin.WINDOW_H old on the render clock, or its publish time
  91 | +    cannot be read (never assumed fresh). No exception for a moment that is not time-sensitive."""
  92 | +    import package_pin
  93 | +    age = E.age_hours(m.get("published_at"), now)
  94 | +    return age is None or age > package_pin.WINDOW_H
  95 | +
  96 | +
  97 |  def usable(moments, ctx, delivered=(), optout=frozenset()):
  98 | -    """delivered: moment ids, or {"video_id", "start", "end"} of moments delivered in the previous 24 h; a moment that
  99 | -    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated)."""
 100 | +    """delivered: moment ids, or {"video_id", "start", "end"[, "text", "pin"]} of every DELIVERED clip. A moment that
 101 | +    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated),
 102 | +    and (RULING 76 b) neither is the same speech (same_speech) in any other video, re-posted by another channel or the
 103 | +    same one. RULING 76 (a): a moment whose source is over 12 h old on the render clock (ctx.now) is expired."""
 104 |      ids = {d for d in delivered if isinstance(d, str)}
 105 |      spans = [d for d in delivered if isinstance(d, dict)]
 106 |      out, why = [], {}
 107 | @@ -131,13 +166,22 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
 108 |          mid = m["moment_id"]
 109 |          overlap = any(d.get("video_id") == m["video_id"] and float(d["start"]) < float(m["end"]) and
 110 |                        float(m["start"]) < float(d["end"]) for d in spans)
 111 | -        if not m.get("on_screen_ok"):
 112 | +        if expired(m, ctx.now):                    # first (audit 1810 C2): its why agrees with ruling 76 (d)'s count
 113 | +            why[mid] = (f"ruling 76 (a): published {m.get('published_at')}, over 12 h before the render clock "
 114 | +                        f"{ctx.now.isoformat(timespec='seconds')}: expired")
 115 | +        elif not m.get("on_screen_ok"):
 116 |              why[mid] = "not eligible on screen: " + "; ".join(
 117 |                  f"{r}: {', '.join(v['reasons'])}" for r, v in (m.get("eligibility") or {}).items() if not v["ok"])
 118 |          elif m.get("excluded"):
 119 |              why[mid] = f"hard exclusion (L-u): {m['excluded']}"
 120 |          elif mid in ids or overlap:
 121 | -            why[mid] = "delivered in the previous 24 h (or overlaps a delivered moment)"
 122 | +            why[mid] = "delivered (or overlaps a delivered moment)"
 123 | +        elif any(d.get("text") and d.get("video_id") != m["video_id"] and same_speech(d["text"], m.get("text"))
 124 | +                 for d in spans):
 125 | +            d = next(d for d in spans if d.get("text") and d.get("video_id") != m["video_id"] and
 126 | +                     same_speech(d["text"], m.get("text")))
 127 | +            why[mid] = (f"ruling 76 (b): the same speech as a delivered clip ({d.get('pin')}: {d.get('video_id')} "
 128 | +                        f"{d.get('start')}-{d.get('end')}), re-posted in another video")
 129 |          elif m["channel_id"] in optout:
 130 |              why[mid] = "channel opted out"
 131 |          elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
 132 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 133 | index a846a1c..2a97444 100644
 134 | --- a/pipeline/package_pin.py
 135 | +++ b/pipeline/package_pin.py
 136 | @@ -82,6 +82,34 @@ TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE
 137 |  SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
 138 |  
 139 |  
 140 | +WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
 141 | +                         # RENDER clock; past it, expired for good (it superseded ruling 57's 72 h window)
 142 | +
 143 | +
 144 | +def window_problems(segments, now=None):
 145 | +    """RULING 76 (a) and (c): every segment's source was published within WINDOW_H of the render clock `now` (default:
 146 | +    this moment, so the check is made again whenever a pin would go to render). An unknown or unreadable publish time
 147 | +    is a problem (never assumed fresh), and so is a time without a zone: as eligibility._parse_time reads it, no
 148 | +    measurement (audit 1810 C1). -> [why]."""
 149 | +    now = now or datetime.now(timezone.utc)
 150 | +    out = []
 151 | +    for s in segments or []:
 152 | +        p = s.get("source_published_at") or s.get("published_at")
 153 | +        try:
 154 | +            t = datetime.fromisoformat(str(p).replace("Z", "+00:00"))
 155 | +        except (TypeError, ValueError):
 156 | +            out.append(f"ruling 76: {s.get('video_id')}: no readable publish time ({p!r})")
 157 | +            continue
 158 | +        if t.tzinfo is None:
 159 | +            out.append(f"ruling 76: {s.get('video_id')}: a publish time without a zone ({p!r}) is no measurement")
 160 | +            continue
 161 | +        age = (now - t).total_seconds() / 3600.0
 162 | +        if age > WINDOW_H:
 163 | +            out.append(f"ruling 76: {s.get('video_id')} was published {p}, {age:.1f} h before the render clock (over "
 164 | +                       f"{WINDOW_H:g} h): expired")
 165 | +    return out
 166 | +
 167 | +
 168 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 169 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 170 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 171 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 172 | index c8814db..bd98749 100644
 173 | --- a/tests/moments/test_moments.py
 174 | +++ b/tests/moments/test_moments.py
 175 | @@ -109,7 +109,8 @@ class TestPackageUsable(unittest.TestCase):
 176 |          ok, why = PK.usable([long_, unmeasured, stale, fresh, excluded, changed], ctx)
 177 |          self.assertEqual([m["moment_id"] for m in ok], ["f"])     # an UNMEASURED speaker (None) is a candidate only:
 178 |          self.assertIn("20.0 s", why["l"])                          # L-v 2 measures it at packaging and the pin refuses
 179 | -        self.assertIn("L-v 3", why["s"])                           # an unmeasured second pass (audit p2 M11)
 180 | +        self.assertIn("ruling 76 (a)", why["s"])                   # an unmeasured second pass (audit p2 M11); a 30 h
 181 | +        #   time-sensitive source is now expired first (ruling 76, 18:08 Nov 13: 12 h), before L-v 3's 24 h rule
 182 |          self.assertIn("accusation", why["x"])
 183 |          self.assertIn("L-v 1", why["t"])
 184 |  
 185 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 186 | index 38e802b..219f17d 100644
 187 | --- a/tests/package/proof_ledger.py
 188 | +++ b/tests/package/proof_ledger.py
 189 | @@ -81,7 +81,7 @@ def delivered_pins(paths):
 190 |              if not isinstance(segs, list) or not segs:
 191 |                  raise ValueError("no clip")
 192 |              spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
 193 | -                       "pin": pin["story_id"]} for s in segs]
 194 | +                       "pin": pin["story_id"], "text": s.get("approved_text")} for s in segs]   # ruling 76 (b)
 195 |              pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
 196 |                           "approved_at": at.isoformat(), "clips": len(segs)})
 197 |          except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:       # which pin (glm C3 P2-3)
 198 | @@ -96,7 +96,8 @@ def main(argv=None):
 199 |                      help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
 200 |                           "newest one's approved_at")
 201 |      ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 202 | -    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 203 | +    ap.add_argument("--hours", type=float, default=package_pin.WINDOW_H,
 204 | +                    help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
 205 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 206 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 207 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 208 | @@ -104,6 +105,9 @@ def main(argv=None):
 209 |                           "record (its tried[N]; default the first that passed), as it was judged")
 210 |      a = ap.parse_args(argv)
 211 |      now = datetime.now(timezone.utc)
 212 | +    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
 213 | +        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
 214 | +        return 2
 215 |      try:                                                 # read before anything is written (glm C2 N-4)
 216 |          delivered, last, pins = delivered_pins(a.delivered)
 217 |          since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 218 | @@ -126,6 +130,18 @@ def main(argv=None):
 219 |              with open(p) as f:
 220 |                  CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
 221 |          CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
 222 | +        pub, notes = {}, {}                              # RULING 76 (a): the open candidates' clips' publish times,
 223 | +        for k, e in reg["candidates"].items():           # from the record that found them (its inputs.json holds every
 224 | +            if e["state"] != "closed":                   # moment of its line-ups); unknown: expired, never fresh
 225 | +                src = os.path.join(e["source"], "inputs.json")
 226 | +                try:
 227 | +                    with open(os.path.join(REPO, src)) as f:
 228 | +                        pub.update({m["moment_id"]: m.get("published_at") for m in json.load(f).get("moments") or []
 229 | +                                    if m.get("moment_id") in e["lineup"]})
 230 | +                    notes[k] = f"publish times from {src}"
 231 | +                except (OSError, ValueError, AttributeError, TypeError) as ex:   # audit 1810 C2: attributable
 232 | +                    notes[k] = f"{src} could not be read ({type(ex).__name__}): no known publish time"
 233 | +        gone = CA.expire(reg, pub, now, package_pin.WINDOW_H, notes)
 234 |          CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
 235 |      except (OSError, ValueError, KeyError, TypeError) as e:
 236 |          print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 237 | @@ -146,6 +162,8 @@ def main(argv=None):
 238 |          (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
 239 |      say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 240 |          f"{len(delivered)} clip spans out")
 241 | +    say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
 242 | +        (f": {gone}" if gone else ""))
 243 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 244 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 245 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 246 | @@ -223,7 +241,8 @@ def main(argv=None):
 247 |      if res["package"]:
 248 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 249 |          try:
 250 | -            lock = LP.pin_problems(res["package"])       # ruling 68: sealed only with a passing lock pre-check
 251 | +            lock = LP.pin_problems(res["package"]) + \
 252 | +                package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
 253 |              if lock:
 254 |                  raise package_pin.PinRefused("; ".join(lock))
 255 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 256 | @@ -244,6 +263,13 @@ def main(argv=None):
 257 |              say(f"PIN REFUSED: {e}")
 258 |      else:
 259 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 260 | +    hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries
 261 | +    res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
 262 | +                        "cleared": (res.get("prescreen") or {}).get("cleared"),
 263 | +                        "cuttable": (res.get("prescreen") or {}).get("cuttable"),
 264 | +                        "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
 265 | +    say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
 266 | +        f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
 267 |      try:                                         # the record is written whatever the ledger says (audit 0707 C1)
 268 |          after = round(router.spent(), 4)
 269 |      except Exception as e:                       # noqa: BLE001
 270 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 271 | index 7c06985..7ab18d0 100644
 272 | --- a/tests/package/test_candidates.py
 273 | +++ b/tests/package/test_candidates.py
 274 | @@ -117,6 +117,32 @@ class TestRegistry(unittest.TestCase):
 275 |              with self.assertRaises(ValueError):
 276 |                  CA.registered(reg)
 277 |  
 278 | +    def test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good(self):
 279 | +        reg = CA.new_registry()
 280 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
 281 | +        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")              # already closed: untouched
 282 | +        pub = {m: (T0 - timedelta(hours=2)).isoformat() for m in "abcdefghi"}
 283 | +        pub["e"] = (T0 - timedelta(hours=12, minutes=1)).isoformat()                    # one clip over 12 h
 284 | +        del pub["c"]                                                                    # one clip of unknown age
 285 | +        self.assertEqual(sorted(CA.expire(reg, pub, T0, 12.0, {"d+e+f": "publish times from r/inputs.json"})),
 286 | +                         ["a+b+c", "d+e+f"])
 287 | +        self.assertIn("[publish times from r/inputs.json]", reg["candidates"]["d+e+f"]["history"][-1]["why"])
 288 | +        e = reg["candidates"]["d+e+f"]
 289 | +        self.assertEqual((e["state"], e["history"][-1]["class"]), ("closed", "expired"))
 290 | +        self.assertIn("e: 12.0 h", e["history"][-1]["why"])
 291 | +        self.assertIn("c: no known publish time", reg["candidates"]["a+b+c"]["history"][-1]["why"])
 292 | +        self.assertEqual(reg["candidates"]["g+h+i"]["history"][-1]["class"], "clip")
 293 | +        self.assertEqual(CA.due(reg, T0), [])                                          # never offered again
 294 | +        fresh = CA.new_registry()
 295 | +        CA.seed(fresh, record(T0, [t(["a", "b"])]), "r")
 296 | +        self.assertEqual(CA.expire(fresh, {"a": T0.isoformat(), "b": T0.isoformat()}, T0, 12.0), [])
 297 | +        # audit 1810 C1 (grok P1, glm P1-1): a later record that passes the same line-up again never revives it
 298 | +        CA.seed(reg, record(T0 + timedelta(hours=1), [t(["d", "e", "f"])], package={"segments": [
 299 | +            {"moment_id": m} for m in "def"]}), "r-later")
 300 | +        self.assertEqual((reg["candidates"]["d+e+f"]["state"], reg["candidates"]["d+e+f"]["history"][-1]["class"]),
 301 | +                         ("closed", "expired"))
 302 | +        self.assertEqual([k for k, _, _ in CA.due(reg, T0 + timedelta(hours=1))], [])
 303 | +
 304 |      def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 305 |          reg = CA.new_registry()
 306 |          for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 307 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 308 | index 74817cb..807e186 100644
 309 | --- a/tests/package/test_ledger_build.py
 310 | +++ b/tests/package/test_ledger_build.py
 311 | @@ -762,6 +762,24 @@ class TestDriverRefuses(unittest.TestCase):
 312 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 313 |                           before)
 314 |  
 315 | +    def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
 316 | +        """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
 317 | +        carry the approved text, for the same-speech rule."""
 318 | +        sys.path.insert(0, HERE)
 319 | +        import proof_ledger as PLG
 320 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 321 | +                                                                                 "MOMENTS_PIN_LY.json")]
 322 | +        with mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
 323 | +            for h in ("12.5", "72", "0", "-1"):
 324 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", h]), 2, h)
 325 | +            self.assertIn("REFUSED (ruling 76)", err.getvalue())
 326 | +            for h in ("12", "6"):                       # audit 1810 C1 (glm P2-1): the bound itself is accepted; the run
 327 | +                with self.assertRaises(AssertionError) as cm:   # goes on, and the guard stops it at the proof dir
 328 | +                    PLG.main(["--delivered", *pins, "--hours", h])
 329 | +                self.assertIn("went on to write a proof dir", str(cm.exception))
 330 | +        spans, _, _ = PLG.delivered_pins(pins)
 331 | +        self.assertTrue(all(isinstance(s["text"], str) and s["text"] for s in spans))
 332 | +
 333 |      def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
 334 |          """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
 335 |          pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
 336 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 337 | index b395b01..8f0638b 100644
 338 | --- a/tests/package/test_medley.py
 339 | +++ b/tests/package/test_medley.py
 340 | @@ -2166,6 +2166,58 @@ class TestRuling72Lock(unittest.TestCase):
 341 |          self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 342 |  
 343 |  
 344 | +class TestRuling76Window(unittest.TestCase):
 345 | +    """RULING 76 (18:08 Nov 13): (a) a moment only while its source is <= 12 h old on the RENDER clock, no exception for
 346 | +    one that is not time-sensitive; (b) a delivered span never again, nor the same speech re-posted in another video;
 347 | +    (c) the pin stage re-checks (a) on the render clock."""
 348 | +
 349 | +    def at(self, mid, hours_ago, **kw):
 350 | +        return dict(pm(mid, mid.upper(), 12.0, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 351 | +
 352 | +    def test_a_moment_over_12_h_or_of_unknown_age_is_expired(self):
 353 | +        ok, why = PK.usable([self.at("a", 11.9), self.at("b", 12.1), dict(self.at("c", 1), published_at=None),
 354 | +                             dict(self.at("d", 1), published_at="yesterday")], ctx())
 355 | +        self.assertEqual([m["moment_id"] for m in ok], ["a"])
 356 | +        for mid in "bcd":
 357 | +            self.assertIn("ruling 76 (a)", why[mid])
 358 | +        both = PK.usable([self.at("t", 30, risk=("time_sensitive",)), dict(self.at("e", 13), excluded=["x"])],
 359 | +                         ctx())[1]
 360 | +        self.assertIn("ruling 76 (a)", both["t"])                              # expired first (audit 1810 C2): the
 361 | +        self.assertIn("ruling 76 (a)", both["e"])                              # why agrees with (d)'s count
 362 | +
 363 | +    def test_delivered_speech_is_never_used_again_in_any_other_video(self):
 364 | +        said = "Currencies are often born for political reasons, but fail for economic reasons."
 365 | +        delivered = [{"video_id": "vD", "start": 10.0, "end": 20.0, "pin": "moments-x-1", "text": said}]
 366 | +        copy = dict(self.at("c", 1), text="Currencies are often born for political reasons but fail for economic "
 367 | +                                          "reasons, he said.", video_id="vOther")
 368 | +        other = dict(self.at("o", 1), text="Bitcoin launched in January of 2009 and was never renamed.",
 369 | +                     video_id="vOther2")
 370 | +        same_video_elsewhere = dict(self.at("s", 1), text=said, video_id="vD", start=40.0, end=50.0)
 371 | +        ok, why = PK.usable([copy, other, same_video_elsewhere], ctx(), delivered)
 372 | +        self.assertEqual([m["moment_id"] for m in ok], ["o", "s"])         # (the same video: the span rule, as before)
 373 | +        self.assertIn("ruling 76 (b): the same speech as a delivered clip (moments-x-1: vD 10.0-20.0)", why["c"])
 374 | +        self.assertTrue(PK.same_speech(said, said.upper()))
 375 | +        self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))                 # never on one word
 376 | +        self.assertFalse(PK.same_speech(said, "Currencies fail."))             # short: only an equal text
 377 | +        self.assertTrue(PK.same_speech("Bitcoin fixes this.", "bitcoin fixes this"))
 378 | +        scattered = "Currencies are rarely political, but reasons fail for many economic reasons of their own."
 379 | +        self.assertFalse(PK.same_speech(said, scattered))                      # common words, not runs of three
 380 | +
 381 | +    def test_the_pin_stage_re_checks_on_the_render_clock(self):
 382 | +        now = NOW
 383 | +        fresh = {"video_id": "v1", "source_published_at": (now - timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")}
 384 | +        stale = {"video_id": "v2", "source_published_at": (now - timedelta(hours=12, minutes=1)).isoformat()}
 385 | +        naive = {"video_id": "v3", "source_published_at": (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()}
 386 | +        self.assertEqual(package_pin.window_problems([fresh], now), [])
 387 | +        p = package_pin.window_problems([fresh, stale, {"video_id": "v4", "source_published_at": None}, naive], now)
 388 | +        self.assertEqual(len(p), 3)
 389 | +        self.assertIn("v2 was published", p[0])
 390 | +        self.assertIn("over 12 h): expired", p[0])
 391 | +        self.assertIn("v4: no readable publish time", p[1])
 392 | +        self.assertIn("v3: a publish time without a zone", p[2])               # audit 1810 C1: no measurement
 393 | +        self.assertEqual(package_pin.WINDOW_H, 12.0)
 394 | +
 395 | +
 396 |  class TestRuling65Caption(unittest.TestCase):
 397 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 398 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 399 | @@ -2532,7 +2584,8 @@ class TestProposal1PoolFill(unittest.TestCase):
 400 |  class TestRuling57Fresh(unittest.TestCase):
 401 |      """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
 402 |      with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
 403 | -    TRIED first: inside an angle and across angles."""
 404 | +    TRIED first: inside an angle and across angles. RULING 76 (18:08 Nov 13) superseded the 72 h window: a moment over
 405 | +    12 h old is expired and never offered (the line-up preference itself is unchanged, and moot inside 12 h)."""
 406 |  
 407 |      def at(self, mid, ch, dur, hours_ago, **kw):
 408 |          return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
 409 | @@ -2554,12 +2607,18 @@ class TestRuling57Fresh(unittest.TestCase):
 410 |          self.assertLess(PK.fresh_key(unknown, NOW), PK.fresh_key(ms[:3], NOW))   # ranks below 50-70 h, never newest
 411 |  
 412 |      def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
 413 | -        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 414 | +        """Since ruling 76: the 13-70 h moments are expired, never offered to the angle writer, and the line-up is
 415 | +        built from the 12 h pool."""
 416 | +        ms = [self.at("h", "A", 12.0, 13), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 417 |                self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
 418 | -        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 419 | +        rig = Rig(ms, [["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 420 |          out = rig.run()
 421 | -        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
 422 | +        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])
 423 |          self.assertEqual(out["angles"][0]["hook"], "f")
 424 | +        prompt = next(p for r, p in rig.prompts if r == "angle_write")
 425 | +        for old in ("h", "x", "y"):
 426 | +            self.assertNotIn(f"id={old} ", prompt)                            # never offered
 427 | +            self.assertIn("ruling 76 (a)", out["unusable"][old])
 428 |  
 429 |  
 430 |  class TestRuling41Search(unittest.TestCase):
 431 | 
```

---

You are auditing a change to the medley pin builder on branch pp-selectid (Protocol Pulse: it builds sealed pins of
other channels' clips; an integrator renders them). Only state what you can verify from the diff; if uncertain, say so;
do not guess.

The order being implemented, RULING 76 (orchestrator 18:08 Nov 13), quoting the owner: "do we have a system in place to
stop our coping system from reusing old clips? We need to delete all the contents after like 6 to 12 hours so that we
never reuse any of it". It supersedes ruling 57's 72 h window, effective now for every build and every pin not yet
rendered:
 (a) "A moment is usable only while its source video's published_at is within 12 HOURS of the RENDER clock. Past 12 h
     it is expired for good: out of the pool, out of the candidates registry, never offered again. No exception for
     'not time-sensitive'."
 (b) "A span that has been DELIVERED in any video is never used again (already so: keep it, and extend it to any
     overlapping span of the same video and to the same speech re-posted on another channel)."
 (c) "Open candidates and sealed-but-unrendered pins are re-checked against (a) at the moment they would render."
 (d) STATE line 1 carries: moments inside 12 h, how many cleared, how many cuttable, hooks >= 4.
 "Audit as one change (the window constant, the registry expiry, the render-clock re-check)." If the 12 h pool cannot
 form a video, the stage it dies at is reported, rather than widening the window.

The change:
1. package_pin.WINDOW_H = 12.0 and window_problems(segments, now=None):
   - each segment's source published within 12 h of the render clock (default: this moment);
   - an unknown or unreadable time is a problem; a zoneless time is UTC, the pipeline's own convention.
   seal() is not changed (the integrator imports this file live for its seal recompute).
2. package.usable():
   - a moment whose source is over 12 h old on ctx.now (the build's render clock), or of unknown age, is out:
     "ruling 76 (a)". It sits after the time-sensitive rule, so a stale time-sensitive moment still reports L-v 3;
     both exclude.
   - delivered spans may carry their text. A moment in ANY OTHER video whose text is the same speech as a delivered
     clip (same_speech) is out: "ruling 76 (b)".
   - same_speech: equal canonical tokens; or, with the shorter text at least 8 words, at least 80 % of the shorter
     one's words in runs of >= 3 words that the other says in the same order (difflib matching blocks).
   - The same-video overlap rule is unchanged.
3. candidates.expire(reg, published, now, window_h): every candidate not yet closed with a clip over 12 h, or of
   unknown age, closes for good, class "expired" (outcome() accepts it).
4. The driver (tests/package/proof_ledger.py):
   - --hours defaults to 12, and a value outside (0, 12] refuses the run before anything is written;
   - delivered spans carry the pin's approved_text;
   - in the refusal block, after the registry is seeded and its stored times checked (CA.due), the open candidates'
     clip publish times are read from the records that found them (inputs.json; unknown means expired), and
     CA.expire runs before any candidate is tried;
   - at the pin stage, package_pin.window_problems(segments) on the real clock joins ruling 68's pin_problems
     (refuse);
   - the record carries ruling_76 counts (inside 12 h, cleared, cuttable, hooks >= 4) and logs them.
5. Tests:
   - test_medley TestRuling76Window (3): (a) with an unknown or unreadable time; (b) with a re-post in another video
     and same_speech's limits; (c) window_problems;
   - ruling 57's build test rewritten: the old moments are now expired and never offered;
   - test_candidates: expire;
   - test_ledger_build: --hours over 12 refuses (under the refusal guard); delivered spans carry text.
   Mutation runs: each of usable's (a) and (b), outcome's "expired", and the --hours refusal fails a test.
   15 suites OK.

Check, against the diff:
- that no moment over 12 h (or of unknown age) can enter a line-up, a candidate try or a pin, on any path;
- that no delivered speech can be reused in another video (and what same_speech might wrongly merge or miss);
- that the registry expiry is for good, and cannot be undone by a later seed;
- that the window can never be widened by an argument;
- that the pin-stage re-check uses the render clock at that moment;
- that nothing else a gate accepts changes, and seal() is unchanged.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

ROUND 2 (cycle 3). The diff now also carries the cycle-1 and cycle-2 consensus. Review the WHOLE diff again, and
these changes in particular:
- usable(): the ruling-76 (a) check is now FIRST, so every expired moment's why says "ruling 76 (a)" and agrees with
  ruling 76 (d)'s independent count. A 30 h time-sensitive moment now reports (a), not L-v 3: L-v 3's 24 h rule can
  no longer fire, since every moment over 12 h is already out (tests/moments/test_moments.py updated).
- candidates.expire(..., notes): each expiry's why names where the publish times were read, or that the record's
  inputs.json could not be read. An unreadable record still expires the candidate (ruling 76: an unknown age is
  never assumed fresh). Its clips are also out of the pool by usable() on their own.
- package_pin.window_problems: a publish time without a zone is no measurement (a problem), as
  eligibility._parse_time reads it behind usable().
- Tests pin the durability of an expiry (a later record that passes or packages the same line-up never revives
  it) and the accepted bound --hours 12.
Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

