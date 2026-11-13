# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1810
# Branch: pp-selectid
# Generated: 2026-11-13 18:10 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1810/C1_STEP.diff (393 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index ea38cca..a45a456 100644
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
  23 | @@ -88,6 +90,31 @@ def seed(reg, record, source):
  24 |      return added
  25 |  
  26 |  
  27 | +def expire(reg, published, now, window_h):
  28 | +    """RULING 76 (a): close for good (class "expired") every candidate not yet closed with a clip whose source was
  29 | +    published more than window_h before the render clock `now`, or whose publish time is not known (never assumed
  30 | +    fresh). published: {moment id: published_at}. -> [the keys expired now]."""
  31 | +    out = []
  32 | +    for k, e in reg["candidates"].items():
  33 | +        if e["state"] == "closed":
  34 | +            continue
  35 | +        old = []
  36 | +        for mid in e.get("lineup") or []:
  37 | +            try:
  38 | +                t = _at(published[mid])
  39 | +            except (KeyError, TypeError, ValueError):
  40 | +                old.append(f"{mid}: no known publish time")
  41 | +                continue
  42 | +            age = (now - t).total_seconds() / 3600.0
  43 | +            if age > window_h:
  44 | +                old.append(f"{mid}: {age:.1f} h")
  45 | +        if old:
  46 | +            outcome(e, "expired", now.isoformat(), "ruling 76", f"over {window_h:g} h on the render clock: " +
  47 | +                    "; ".join(old))
  48 | +            out.append(k)
  49 | +    return out
  50 | +
  51 | +
  52 |  def registered(reg):
  53 |      """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
  54 |      search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
  55 | diff --git a/pipeline/package.py b/pipeline/package.py
  56 | index ad6dd60..dba525c 100644
  57 | --- a/pipeline/package.py
  58 | +++ b/pipeline/package.py
  59 | @@ -121,9 +121,42 @@ VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than i
  60 |                              "never relate one speaker to another"}
  61 |  
  62 |  
  63 | +SAME_SPEECH_MIN_WORDS = 8         # ruling 76 (b): below this, only an equal text is the same speech
  64 | +SAME_SPEECH_RUN = 3               # only runs of at least this many words in order count: never scattered common words
  65 | +
  66 | +
  67 | +def same_speech(a, b):
  68 | +    """RULING 76 (b): two texts are the same speech when they are equal after normalisation (canon.canon_tokens), or,
  69 | +    with the shorter at least SAME_SPEECH_MIN_WORDS long, when at least REPOST_ALIGN_MIN of the shorter one's words lie
  70 | +    in runs of SAME_SPEECH_RUN or more words that the other says in the same order (difflib's matching blocks): a
  71 | +    re-post cut a little differently is still the same speech; a few common words in common never are."""
  72 | +    import difflib
  73 | +    import canon
  74 | +    ta, tb = canon.canon_tokens(a or ""), canon.canon_tokens(b or "")
  75 | +    short = min(len(ta), len(tb))
  76 | +    if short < 2:
  77 | +        return False
  78 | +    if ta == tb:
  79 | +        return True
  80 | +    if short < SAME_SPEECH_MIN_WORDS:
  81 | +        return False
  82 | +    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
  83 | +    return sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short
  84 | +
  85 | +
  86 | +def expired(m, now):
  87 | +    """RULING 76 (a): the moment's source is more than package_pin.WINDOW_H old on the render clock, or its publish time
  88 | +    cannot be read (never assumed fresh). No exception for a moment that is not time-sensitive."""
  89 | +    import package_pin
  90 | +    age = E.age_hours(m.get("published_at"), now)
  91 | +    return age is None or age > package_pin.WINDOW_H
  92 | +
  93 | +
  94 |  def usable(moments, ctx, delivered=(), optout=frozenset()):
  95 | -    """delivered: moment ids, or {"video_id", "start", "end"} of moments delivered in the previous 24 h; a moment that
  96 | -    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated)."""
  97 | +    """delivered: moment ids, or {"video_id", "start", "end"[, "text", "pin"]} of every DELIVERED clip. A moment that
  98 | +    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated),
  99 | +    and (RULING 76 b) neither is the same speech (same_speech) in any other video, re-posted by another channel or the
 100 | +    same one. RULING 76 (a): a moment whose source is over 12 h old on the render clock (ctx.now) is expired."""
 101 |      ids = {d for d in delivered if isinstance(d, str)}
 102 |      spans = [d for d in delivered if isinstance(d, dict)]
 103 |      out, why = [], {}
 104 | @@ -137,7 +170,13 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
 105 |          elif m.get("excluded"):
 106 |              why[mid] = f"hard exclusion (L-u): {m['excluded']}"
 107 |          elif mid in ids or overlap:
 108 | -            why[mid] = "delivered in the previous 24 h (or overlaps a delivered moment)"
 109 | +            why[mid] = "delivered (or overlaps a delivered moment)"
 110 | +        elif any(d.get("text") and d.get("video_id") != m["video_id"] and same_speech(d["text"], m.get("text"))
 111 | +                 for d in spans):
 112 | +            d = next(d for d in spans if d.get("text") and d.get("video_id") != m["video_id"] and
 113 | +                     same_speech(d["text"], m.get("text")))
 114 | +            why[mid] = (f"ruling 76 (b): the same speech as a delivered clip ({d.get('pin')}: {d.get('video_id')} "
 115 | +                        f"{d.get('start')}-{d.get('end')}), re-posted in another video")
 116 |          elif m["channel_id"] in optout:
 117 |              why[mid] = "channel opted out"
 118 |          elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
 119 | @@ -145,6 +184,9 @@ def usable(moments, ctx, delivered=(), optout=frozenset()):
 120 |          elif time_sensitive(m) and (E.age_hours(m["published_at"], ctx.now) is None or
 121 |                                      E.age_hours(m["published_at"], ctx.now) > TIME_SENSITIVE_H):
 122 |              why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
 123 | +        elif expired(m, ctx.now):
 124 | +            why[mid] = (f"ruling 76 (a): published {m.get('published_at')}, over 12 h before the render clock "
 125 | +                        f"{ctx.now.isoformat(timespec='seconds')}: expired")
 126 |          elif (m.get("speaker") or {}).get("turn_change_inside") is True:
 127 |              why[mid] = "a speaker change inside (L-v 1)"
 128 |          else:
 129 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 130 | index a846a1c..37c8910 100644
 131 | --- a/pipeline/package_pin.py
 132 | +++ b/pipeline/package_pin.py
 133 | @@ -82,6 +82,31 @@ TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE
 134 |  SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
 135 |  
 136 |  
 137 | +WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
 138 | +                         # RENDER clock; past it, expired for good (it superseded ruling 57's 72 h window)
 139 | +
 140 | +
 141 | +def window_problems(segments, now=None):
 142 | +    """RULING 76 (a) and (c): every segment's source was published within WINDOW_H of the render clock `now` (default:
 143 | +    this moment, so the check is made again whenever a pin would go to render). An unknown or unreadable publish time
 144 | +    is a problem (never assumed fresh); a time without a zone is UTC, the pipeline's own. -> [why]."""
 145 | +    now = now or datetime.now(timezone.utc)
 146 | +    out = []
 147 | +    for s in segments or []:
 148 | +        p = s.get("source_published_at") or s.get("published_at")
 149 | +        try:
 150 | +            t = datetime.fromisoformat(str(p).replace("Z", "+00:00"))
 151 | +        except (TypeError, ValueError):
 152 | +            out.append(f"ruling 76: {s.get('video_id')}: no readable publish time ({p!r})")
 153 | +            continue
 154 | +        t = t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
 155 | +        age = (now - t).total_seconds() / 3600.0
 156 | +        if age > WINDOW_H:
 157 | +            out.append(f"ruling 76: {s.get('video_id')} was published {p}, {age:.1f} h before the render clock (over "
 158 | +                       f"{WINDOW_H:g} h): expired")
 159 | +    return out
 160 | +
 161 | +
 162 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 163 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 164 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
 165 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 166 | index 38e802b..2b6ad64 100644
 167 | --- a/tests/package/proof_ledger.py
 168 | +++ b/tests/package/proof_ledger.py
 169 | @@ -81,7 +81,7 @@ def delivered_pins(paths):
 170 |              if not isinstance(segs, list) or not segs:
 171 |                  raise ValueError("no clip")
 172 |              spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
 173 | -                       "pin": pin["story_id"]} for s in segs]
 174 | +                       "pin": pin["story_id"], "text": s.get("approved_text")} for s in segs]   # ruling 76 (b)
 175 |              pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
 176 |                           "approved_at": at.isoformat(), "clips": len(segs)})
 177 |          except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:       # which pin (glm C3 P2-3)
 178 | @@ -96,7 +96,8 @@ def main(argv=None):
 179 |                      help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
 180 |                           "newest one's approved_at")
 181 |      ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
 182 | -    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
 183 | +    ap.add_argument("--hours", type=float, default=package_pin.WINDOW_H,
 184 | +                    help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
 185 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 186 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 187 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 188 | @@ -104,6 +105,9 @@ def main(argv=None):
 189 |                           "record (its tried[N]; default the first that passed), as it was judged")
 190 |      a = ap.parse_args(argv)
 191 |      now = datetime.now(timezone.utc)
 192 | +    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
 193 | +        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
 194 | +        return 2
 195 |      try:                                                 # read before anything is written (glm C2 N-4)
 196 |          delivered, last, pins = delivered_pins(a.delivered)
 197 |          since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
 198 | @@ -126,6 +130,16 @@ def main(argv=None):
 199 |              with open(p) as f:
 200 |                  CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
 201 |          CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
 202 | +        pub = {}                                         # RULING 76 (a): the open candidates' clips' publish times,
 203 | +        for e in reg["candidates"].values():             # from the records that found them (unknown: expired)
 204 | +            if e["state"] != "closed":
 205 | +                try:
 206 | +                    with open(os.path.join(REPO, e["source"], "inputs.json")) as f:
 207 | +                        pub.update({m["moment_id"]: m.get("published_at") for m in json.load(f).get("moments") or []
 208 | +                                    if m.get("moment_id") in e["lineup"]})
 209 | +                except (OSError, ValueError, AttributeError, TypeError):
 210 | +                    pass
 211 | +        gone = CA.expire(reg, pub, now, package_pin.WINDOW_H)
 212 |          CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
 213 |      except (OSError, ValueError, KeyError, TypeError) as e:
 214 |          print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 215 | @@ -146,6 +160,8 @@ def main(argv=None):
 216 |          (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
 217 |      say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
 218 |          f"{len(delivered)} clip spans out")
 219 | +    say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
 220 | +        (f": {gone}" if gone else ""))
 221 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 222 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 223 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 224 | @@ -223,7 +239,8 @@ def main(argv=None):
 225 |      if res["package"]:
 226 |          SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 227 |          try:
 228 | -            lock = LP.pin_problems(res["package"])       # ruling 68: sealed only with a passing lock pre-check
 229 | +            lock = LP.pin_problems(res["package"]) + \
 230 | +                package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
 231 |              if lock:
 232 |                  raise package_pin.PinRefused("; ".join(lock))
 233 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 234 | @@ -244,6 +261,13 @@ def main(argv=None):
 235 |              say(f"PIN REFUSED: {e}")
 236 |      else:
 237 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 238 | +    hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries
 239 | +    res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
 240 | +                        "cleared": (res.get("prescreen") or {}).get("cleared"),
 241 | +                        "cuttable": (res.get("prescreen") or {}).get("cuttable"),
 242 | +                        "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
 243 | +    say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
 244 | +        f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
 245 |      try:                                         # the record is written whatever the ledger says (audit 0707 C1)
 246 |          after = round(router.spent(), 4)
 247 |      except Exception as e:                       # noqa: BLE001
 248 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 249 | index 7c06985..ea2052e 100644
 250 | --- a/tests/package/test_candidates.py
 251 | +++ b/tests/package/test_candidates.py
 252 | @@ -117,6 +117,24 @@ class TestRegistry(unittest.TestCase):
 253 |              with self.assertRaises(ValueError):
 254 |                  CA.registered(reg)
 255 |  
 256 | +    def test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good(self):
 257 | +        reg = CA.new_registry()
 258 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
 259 | +        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")              # already closed: untouched
 260 | +        pub = {m: (T0 - timedelta(hours=2)).isoformat() for m in "abcdefghi"}
 261 | +        pub["e"] = (T0 - timedelta(hours=12, minutes=1)).isoformat()                    # one clip over 12 h
 262 | +        del pub["c"]                                                                    # one clip of unknown age
 263 | +        self.assertEqual(sorted(CA.expire(reg, pub, T0, 12.0)), ["a+b+c", "d+e+f"])
 264 | +        e = reg["candidates"]["d+e+f"]
 265 | +        self.assertEqual((e["state"], e["history"][-1]["class"]), ("closed", "expired"))
 266 | +        self.assertIn("e: 12.0 h", e["history"][-1]["why"])
 267 | +        self.assertIn("c: no known publish time", reg["candidates"]["a+b+c"]["history"][-1]["why"])
 268 | +        self.assertEqual(reg["candidates"]["g+h+i"]["history"][-1]["class"], "clip")
 269 | +        self.assertEqual(CA.due(reg, T0), [])                                          # never offered again
 270 | +        fresh = CA.new_registry()
 271 | +        CA.seed(fresh, record(T0, [t(["a", "b"])]), "r")
 272 | +        self.assertEqual(CA.expire(fresh, {"a": T0.isoformat(), "b": T0.isoformat()}, T0, 12.0), [])
 273 | +
 274 |      def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 275 |          reg = CA.new_registry()
 276 |          for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 277 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 278 | index 74817cb..9f3a8f7 100644
 279 | --- a/tests/package/test_ledger_build.py
 280 | +++ b/tests/package/test_ledger_build.py
 281 | @@ -762,6 +762,20 @@ class TestDriverRefuses(unittest.TestCase):
 282 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 283 |                           before)
 284 |  
 285 | +    def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
 286 | +        """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
 287 | +        carry the approved text, for the same-speech rule."""
 288 | +        sys.path.insert(0, HERE)
 289 | +        import proof_ledger as PLG
 290 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 291 | +                                                                                 "MOMENTS_PIN_LY.json")]
 292 | +        with mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
 293 | +            for h in ("12.5", "72", "0", "-1"):
 294 | +                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", h]), 2, h)
 295 | +            self.assertIn("REFUSED (ruling 76)", err.getvalue())
 296 | +        spans, _, _ = PLG.delivered_pins(pins)
 297 | +        self.assertTrue(all(isinstance(s["text"], str) and s["text"] for s in spans))
 298 | +
 299 |      def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
 300 |          """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
 301 |          pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
 302 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 303 | index b395b01..ec031b7 100644
 304 | --- a/tests/package/test_medley.py
 305 | +++ b/tests/package/test_medley.py
 306 | @@ -2166,6 +2166,54 @@ class TestRuling72Lock(unittest.TestCase):
 307 |          self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 308 |  
 309 |  
 310 | +class TestRuling76Window(unittest.TestCase):
 311 | +    """RULING 76 (18:08 Nov 13): (a) a moment only while its source is <= 12 h old on the RENDER clock, no exception for
 312 | +    one that is not time-sensitive; (b) a delivered span never again, nor the same speech re-posted in another video;
 313 | +    (c) the pin stage re-checks (a) on the render clock."""
 314 | +
 315 | +    def at(self, mid, hours_ago, **kw):
 316 | +        return dict(pm(mid, mid.upper(), 12.0, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())
 317 | +
 318 | +    def test_a_moment_over_12_h_or_of_unknown_age_is_expired(self):
 319 | +        ok, why = PK.usable([self.at("a", 11.9), self.at("b", 12.1), dict(self.at("c", 1), published_at=None),
 320 | +                             dict(self.at("d", 1), published_at="yesterday")], ctx())
 321 | +        self.assertEqual([m["moment_id"] for m in ok], ["a"])
 322 | +        for mid in "bcd":
 323 | +            self.assertIn("ruling 76 (a)", why[mid])
 324 | +        self.assertIn("L-v 3", PK.usable([self.at("t", 30, risk=("time_sensitive",))], ctx())[1]["t"])   # as before
 325 | +
 326 | +    def test_delivered_speech_is_never_used_again_in_any_other_video(self):
 327 | +        said = "Currencies are often born for political reasons, but fail for economic reasons."
 328 | +        delivered = [{"video_id": "vD", "start": 10.0, "end": 20.0, "pin": "moments-x-1", "text": said}]
 329 | +        copy = dict(self.at("c", 1), text="Currencies are often born for political reasons but fail for economic "
 330 | +                                          "reasons, he said.", video_id="vOther")
 331 | +        other = dict(self.at("o", 1), text="Bitcoin launched in January of 2009 and was never renamed.",
 332 | +                     video_id="vOther2")
 333 | +        same_video_elsewhere = dict(self.at("s", 1), text=said, video_id="vD", start=40.0, end=50.0)
 334 | +        ok, why = PK.usable([copy, other, same_video_elsewhere], ctx(), delivered)
 335 | +        self.assertEqual([m["moment_id"] for m in ok], ["o", "s"])         # (the same video: the span rule, as before)
 336 | +        self.assertIn("ruling 76 (b): the same speech as a delivered clip (moments-x-1: vD 10.0-20.0)", why["c"])
 337 | +        self.assertTrue(PK.same_speech(said, said.upper()))
 338 | +        self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))                 # never on one word
 339 | +        self.assertFalse(PK.same_speech(said, "Currencies fail."))             # short: only an equal text
 340 | +        self.assertTrue(PK.same_speech("Bitcoin fixes this.", "bitcoin fixes this"))
 341 | +        scattered = "Currencies are rarely political, but reasons fail for many economic reasons of their own."
 342 | +        self.assertFalse(PK.same_speech(said, scattered))                      # common words, not runs of three
 343 | +
 344 | +    def test_the_pin_stage_re_checks_on_the_render_clock(self):
 345 | +        now = NOW
 346 | +        fresh = {"video_id": "v1", "source_published_at": (now - timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")}
 347 | +        stale = {"video_id": "v2", "source_published_at": (now - timedelta(hours=12, minutes=1)).isoformat()}
 348 | +        naive = {"video_id": "v3", "source_published_at": (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()}
 349 | +        self.assertEqual(package_pin.window_problems([fresh, naive], now), [])  # no zone: UTC, the pipeline's own
 350 | +        p = package_pin.window_problems([fresh, stale, {"video_id": "v4", "source_published_at": None}], now)
 351 | +        self.assertEqual(len(p), 2)
 352 | +        self.assertIn("v2 was published", p[0])
 353 | +        self.assertIn("over 12 h): expired", p[0])
 354 | +        self.assertIn("v4: no readable publish time", p[1])
 355 | +        self.assertEqual(package_pin.WINDOW_H, 12.0)
 356 | +
 357 | +
 358 |  class TestRuling65Caption(unittest.TestCase):
 359 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 360 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 361 | @@ -2532,7 +2580,8 @@ class TestProposal1PoolFill(unittest.TestCase):
 362 |  class TestRuling57Fresh(unittest.TestCase):
 363 |      """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
 364 |      with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
 365 | -    TRIED first: inside an angle and across angles."""
 366 | +    TRIED first: inside an angle and across angles. RULING 76 (18:08 Nov 13) superseded the 72 h window: a moment over
 367 | +    12 h old is expired and never offered (the line-up preference itself is unchanged, and moot inside 12 h)."""
 368 |  
 369 |      def at(self, mid, ch, dur, hours_ago, **kw):
 370 |          return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
 371 | @@ -2554,12 +2603,18 @@ class TestRuling57Fresh(unittest.TestCase):
 372 |          self.assertLess(PK.fresh_key(unknown, NOW), PK.fresh_key(ms[:3], NOW))   # ranks below 50-70 h, never newest
 373 |  
 374 |      def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
 375 | -        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 376 | +        """Since ruling 76: the 13-70 h moments are expired, never offered to the angle writer, and the line-up is
 377 | +        built from the 12 h pool."""
 378 | +        ms = [self.at("h", "A", 12.0, 13), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 379 |                self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
 380 | -        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 381 | +        rig = Rig(ms, [["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 382 |          out = rig.run()
 383 | -        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
 384 | +        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])
 385 |          self.assertEqual(out["angles"][0]["hook"], "f")
 386 | +        prompt = next(p for r, p in rig.prompts if r == "angle_write")
 387 | +        for old in ("h", "x", "y"):
 388 | +            self.assertNotIn(f"id={old} ", prompt)                            # never offered
 389 | +            self.assertIn("ruling 76 (a)", out["unusable"][old])
 390 |  
 391 |  
 392 |  class TestRuling41Search(unittest.TestCase):
 393 | 
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

