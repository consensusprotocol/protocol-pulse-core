# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_0924
# Branch: pp-selectid
# Generated: 2026-11-16 09:39 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_0924/C1_STEP.diff (519 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index 4e1c4e2..bc834c0 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -62,16 +62,22 @@ def seed(reg, record, source):
   6 |      """Seed the registry from one build record, once per record (reg["records"]). Every tried line-up that passed the
   7 |      clips-alone verdict and is not itself a candidate's try becomes a candidate (one per line-up, the earliest record
   8 |      that passed it). A line-up the record packaged is closed. A record written before the registry existed applies
   9 | -    the outcome of the candidate it tried (its out["candidate"]). -> the keys added."""
  10 | +    the outcome of the candidate it tried (its out["candidate"]). A story angle's line-up (ruling 118 (4)) is never
  11 | +    a candidate: its angle has no writer back-end (law L-x), and a later build reads the story again. -> the keys
  12 | +    added."""
  13 |      if source in reg["records"]:
  14 |          return []
  15 |      reg["records"].append(source)
  16 |      added, at = [], record.get("now")
  17 |      pk = record.get("package") or {}
  18 |      packaged = [s.get("moment_id") for s in pk.get("segments") or []]
  19 | +    angles = record.get("angles") or []
  20 | +    story = lambda t: type(t.get("angle")) is int and 0 < t["angle"] <= len(angles) and \
  21 | +        bool((angles[t["angle"] - 1] or {}).get("story"))                 # RULING 118 (4)
  22 |      for i, t in enumerate(record.get("tried") or []):
  23 |          lu = t.get("lineup")
  24 | -        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None:
  25 | +        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None \
  26 | +                or story(t):
  27 |              continue
  28 |          k = key(lu)
  29 |          if k not in reg["candidates"]:
  30 | diff --git a/pipeline/package.py b/pipeline/package.py
  31 | index fc9cd76..8493f7b 100644
  32 | --- a/pipeline/package.py
  33 | +++ b/pipeline/package.py
  34 | @@ -103,6 +103,8 @@ TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: t
  35 |  # only with the scorer's affirmation of its trimmed text, and package_pin refuses scorer_pending. RULING 60 (11:01): for
  36 |  # a moments pin the scorer judges stand-alone only, and the affirmation is the score alone (stand_alone.affirmed with
  37 |  # moments=True), as the render's validate reads it.
  38 | +STORIES = "/home/ultron/pulse_intel/stories/latest.json"   # RULING 118 (4): the receipts session's stories
  39 | +#   (pipeline_pi_receipts; read only), refreshed every 15 minutes: the story-first angles (read_stories)
  40 |  SCORER_VERDICTS = "/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json"   # ruling 56: the
  41 |  SCORER_KIND = "moments"            # integrator's verdicts (read only); ruling 60: kind "moments", no event
  42 |  RENDER_SCORER_CODE = tuple(f"/home/ultron/protocol_pulse/pipeline/{f}" for f in ("stand_alone.py", "story_semantics.py"))
  43 | @@ -1960,6 +1962,101 @@ def join_moments(angle, cleared, doomed=frozenset()):
  44 |      return ([h] + own + first + then)[:JOIN_MOMENTS_MAX]
  45 |  
  46 |  
  47 | +def read_stories(path):
  48 | +    """RULING 118 (4): the receipts session's stories file (pipeline_pi_receipts, /home/ultron/pulse_intel; read only), in
  49 | +    its writer's documented shape (stories.py): {"generated_at", ..., "models", "stories": [{"story_id", "headline",
  50 | +    "channels", "n_claims", "moments": [{"moment_id", "video_id", "channel_name", "published_at", "claims"}]}]}.
  51 | +    -> (stories, record): each story {"story_id", "headline", "moment_ids"}, in the file's order (the most claims
  52 | +    first). No path, no file, or a file out of that shape: no stories (the build goes on as before) and the record says
  53 | +    why. Its age is recorded, not judged: only the moments this build's own pool still holds can be used."""
  54 | +    rec = {"path": path, "read": False}
  55 | +    if not path:
  56 | +        return [], dict(rec, why="no stories file named")
  57 | +    try:
  58 | +        with open(path) as f:
  59 | +            d = json.load(f)
  60 | +    except FileNotFoundError:
  61 | +        return [], dict(rec, why="no file")
  62 | +    except (OSError, ValueError) as e:
  63 | +        return [], dict(rec, why=f"unreadable ({type(e).__name__})")
  64 | +    st = d.get("stories") if isinstance(d, dict) else None
  65 | +    if not isinstance(st, list):
  66 | +        return [], dict(rec, why="no 'stories' list")
  67 | +    out = []
  68 | +    for i, s in enumerate(st):
  69 | +        ms = s.get("moments") if isinstance(s, dict) else None
  70 | +        if not (isinstance(ms, list) and isinstance(s.get("story_id"), str) and s["story_id"] and
  71 | +                isinstance(s.get("headline"), str) and s["headline"].strip() and
  72 | +                all(isinstance(m, dict) and isinstance(m.get("moment_id"), str) for m in ms)):
  73 | +            return [], dict(rec, why=f"story {i + 1} is out of the file's shape")
  74 | +        out.append({"story_id": s["story_id"], "headline": " ".join(s["headline"].split()),
  75 | +                    "moment_ids": list(dict.fromkeys(m["moment_id"] for m in ms))})
  76 | +    return out, dict(rec, read=True, generated_at=d.get("generated_at"), prompt_version=d.get("prompt_version"),
  77 | +                     models=d.get("models"), stories=len(out))
  78 | +
  79 | +
  80 | +def story_angles(stories, cleared, hooks, k=MAX_ANGLES):
  81 | +    """RULING 118 (4), STORY-FIRST LINE-UPS: angles built INSIDE ONE STORY (its hook and every clip from the same story),
  82 | +    tried ahead of the angle writer's; every gate unchanged. For each story in the file's order, the best of `hooks`
  83 | +    (the build's passing hooks, best first) among the story's cleared moments; the angle's moments are that hook, then
  84 | +    the story's other cleared moments, one of each channel not yet in first, then by rank score (at most 8); its
  85 | +    sentence is the story's headline. It must hold the angle contract (check_angles: 3-8 distinct moments from >= 3
  86 | +    channels, the hook one of them and a passing hook) or the story gives no angle. At most k angles.
  87 | +    -> (angles, record): each angle {"angle", "moments", "hook", "story": story_id}; the record, one row a story."""
  88 | +    hook_ids = [m["moment_id"] for m in hooks]
  89 | +    angles, rec = [], []
  90 | +    for s in stories:
  91 | +        ids = [x for x in s["moment_ids"] if x in cleared]
  92 | +        row = {"story_id": s["story_id"], "cleared": len(ids),
  93 | +               "channels": len({cleared[x]["channel_id"] for x in ids})}
  94 | +        rec.append(row)
  95 | +        if len(angles) >= k:
  96 | +            row["why"] = f"{k} story angle(s) already"
  97 | +            continue
  98 | +        h = next((x for x in hook_ids if x in ids), None)
  99 | +        if h is None:
 100 | +            row["why"] = "no passing hook among its cleared moments"
 101 | +            continue
 102 | +        chans, first, then = {cleared[h]["channel_id"]}, [], []
 103 | +        for x in sorted((x for x in ids if x != h), key=lambda x: (-cleared[x].get("rank_score", 0), x)):
 104 | +            (then if cleared[x]["channel_id"] in chans else first).append(x)
 105 | +            chans.add(cleared[x]["channel_id"])
 106 | +        ms = ([h] + first + then)[:8]
 107 | +        a = {"angle": s["headline"], "moments": ms, "hook": h, "support": {x: s["story_id"] for x in ms}}
 108 | +        try:
 109 | +            check_angles({"angles": [a]}, cleared, 1, hooks=set(hook_ids))
 110 | +        except ValueError as e:
 111 | +            row["why"] = f"not an angle: {e}"
 112 | +            continue
 113 | +        angles.append({"angle": a["angle"], "moments": ms, "hook": h, "story": s["story_id"]})
 114 | +        row.update(angle=len(angles), hook=h, moments=ms)
 115 | +    return angles, rec
 116 | +
 117 | +
 118 | +def story_pool(angle, cleared, by_story):
 119 | +    """RULING 118 (4): the pool a line-up for `angle` takes moments from beyond its own (its join table, the fill, every swap):
 120 | +    a story's angle ONLY its story's cleared moments (`by_story`: story id -> moment ids; a story it does not hold gives
 121 | +    none); any other angle the whole cleared pool, as before."""
 122 | +    if angle.get("story") is None:
 123 | +        return cleared
 124 | +    return {x: cleared[x] for x in by_story.get(angle["story"]) or () if x in cleared}
 125 | +
 126 | +
 127 | +def story_writers(router, models):
 128 | +    """Law L-x for the story angles: the stories file's grouping models chose each story's moments (one of them wrote its
 129 | +    headline), so the back-ends of the router that run those models give their vendors and families to the writers'
 130 | +    sets the verdicts avoid. A model no back-end runs can judge nothing here. -> (vendors, families)."""
 131 | +    ms = {m for m in ((models or {}).get("group") or []) if isinstance(m, str)} if isinstance(models, dict) else set()
 132 | +    bs = [b for b in router.backends.values() if getattr(b, "model", None) in ms]
 133 | +    return {b.vendor for b in bs}, {b.family for b in bs}
 134 | +
 135 | +
 136 | +def angle_source(angle, reply):
 137 | +    """The package's record of who made its angle: the angle writer's back-end, or for a story angle (ruling 118 (4))
 138 | +    the story of the receipts session's stories file it was built inside."""
 139 | +    return f"story {angle['story']} (the stories file)" if angle.get("story") else reply.backend
 140 | +
 141 | +
 142 |  def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
 143 |      """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
 144 |      pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
 145 | @@ -2668,8 +2765,11 @@ def load_candidate(record, index=None, source=""):
 146 |      tried = record.get("tried") or []
 147 |      ids_ok = lambda t: isinstance(t.get("lineup"), list) and bool(t["lineup"]) and \
 148 |          all(isinstance(x, str) for x in t["lineup"]) and type(t.get("angle")) is int    # audit 1330 C2: the shape
 149 | -    if index is None:
 150 | -        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and ids_ok(t)), None)
 151 | +    story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
 152 | +        bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))   # RULING 118 (4)
 153 | +    if index is None:                                  # (a story angle's line-up is never kept: see below)
 154 | +        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and ids_ok(t) and not story(t)),
 155 | +                     None)
 156 |          if index is None:
 157 |              raise ValueError("no line-up in this record passed the clips-alone verdict")
 158 |      if not 0 <= index < len(tried):
 159 | @@ -2683,6 +2783,9 @@ def load_candidate(record, index=None, source=""):
 160 |      ai, angles = int(t["angle"]) - 1, record.get("angles") or []
 161 |      if not 0 <= ai < len(angles) or angles[ai].get("angle") != t.get("text"):
 162 |          raise ValueError(f"tried[{index}]'s angle is not the record's angle {ai + 1}")
 163 | +    if angles[ai].get("story"):                       # RULING 118 (4): its moments were chosen by the stories file's
 164 | +        raise ValueError(f"tried[{index}] is story {angles[ai]['story']!r}'s line-up (ruling 118 (4)): not kept, "
 165 | +                         f"its angle has no writer back-end for law L-x; a later build reads the story again")
 166 |      a = {k: angles[ai][k] for k in ("angle", "moments", "hook")}
 167 |      if a["hook"] != t["lineup"][0]:
 168 |          raise ValueError(f"tried[{index}] does not open on its angle's hook (ruling 59 c)")
 169 | @@ -2721,7 +2824,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 170 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 171 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
 172 |            join_cache=None,
 173 | -          visual_cache=None, registered=None, lock_check=None, scorer_extra=()):
 174 | +          visual_cache=None, registered=None, lock_check=None, scorer_extra=(), stories_path=None):
 175 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 176 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 177 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 178 | @@ -3002,6 +3105,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 179 |      lo, hi = medley_content_range()
 180 |      angles, angle_reply, errs = None, None, []
 181 |      cand_segs = None
 182 | +    stories, s_angles, s_writers = [], [], (set(), set())
 183 | +    if candidate is None and stories_path:           # RULING 118 (4): STORY-FIRST LINE-UPS, ahead of the angle writer
 184 | +        stories, out["stories"] = read_stories(stories_path)
 185 | +        s_angles, out["stories"]["angles"] = story_angles(stories, cleared, passing, max_angles)
 186 | +        if s_angles:                                  # law L-x: the grouping models chose the story's moments
 187 | +            s_writers = story_writers(router, out["stories"].get("models"))
 188 | +        log(f"  RULING 118 (4): {len(stories)} story(ies) read, {len(s_angles)} story angle(s)"
 189 | +            + ("" if out["stories"]["read"] else f" (no stories: {out['stories']['why']})"))
 190 | +    by_story = {s["story_id"]: s["moment_ids"] for s in stories}
 191 |      if candidate is not None:                         # RULING 66 (13:18): A PASSED LINE-UP IS KEPT: its own angle and
 192 |          cand_segs, why_c = candidate_lineup(router, candidate, cleared, ctx.now)   # line-up; no angle is asked for
 193 |          out["candidate"] = {"source": candidate.get("source"), "index": candidate.get("index"),
 194 | @@ -3035,8 +3147,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 195 |                  router.reject(r)
 196 |              errs.append(f"{type(e).__name__}: {str(e)[:200]}")       # every reason, the first one too
 197 |              out["why_none"] = "no readable angles: " + "; then ".join(errs)
 198 | -    if not angles:
 199 | -        return out
 200 | +    if not angles:                                    # RULING 118 (4): the story angles go with the writer's only:
 201 | +        return out                                    # its back-end keeps every write on its gateway (ruling 85)
 202 |      out.pop("why_none", None)
 203 |      missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}] if candidate is None else []
 204 |      if missing and len(angles) < max_angles:            # RULING 64: a passing hook left without an angle is asked
 205 | @@ -3061,11 +3173,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 206 |          return bool(segs) and fresh_key(segs, ctx.now)[0]                                              # old go first
 207 |      hrank = {m["moment_id"]: (-hook_own(m)["rating"], -sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS))
 208 |               for m in passing}                            # ruling 59 (c): the best hook first, then ruling 57's
 209 | -    angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))   # freshness; stable: the writer's
 210 | +    order = lambda a: (hrank[a["hook"]], not first_fresh(a))
 211 | +    angles = sorted(s_angles, key=order) + sorted(angles, key=order)   # RULING 118 (4): the story angles first; then
 212 | +    # ruling 57's freshness; stable: the writer's
 213 |      # order within each
 214 | -    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 215 | +    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
 216 | +                      **({"story": a["story"]} if a.get("story") else {})} for a in angles]
 217 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 218 | -    writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 219 | +    writers_v = {angle_reply.vendor} | s_writers[0]   # RULING 118 (4): and the stories file's grouping models (L-x)
 220 | +    writers_f = {angle_reply.family} | s_writers[1]
 221 | +    if s_angles:
 222 | +        out["stories"]["writers"] = {"vendors": sorted(s_writers[0]), "families": sorted(s_writers[1])}
 223 |  
 224 |      def pin_last_resort(pk):
 225 |          """RULING 102: the pin's record of the local judge's step-A verdicts on its clips (either screen's), by label."""
 226 | @@ -3089,7 +3207,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 227 |      writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
 228 |          {P.gateway(ab) if ab is not None else angle_reply.vendor}   # heimdall_first a family is its own maker, and
 229 |      # a write may still fail over deepseek -> qwen as today); the verdicts avoid every writer's maker and family
 230 | -    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)" if candidate is None else
 231 | +    log(f"  {len(angles)} angles from {angle_reply.backend}"
 232 | +        + (f", the first {len(s_angles)} from the stories file (ruling 118 (4))" if s_angles else "")
 233 | +        + f" ({time.time() - t0:.0f} s)" if candidate is None else
 234 |          f"  ruling 66: the candidate {candidate.get('source')} tried[{candidate.get('index')}] (angle "
 235 |          f"{candidate['ai'] + 1} line-up {candidate['n_lineup']}), as judged: its angle from {angle_reply.backend}, "
 236 |          f"no angle asked ({time.time() - t0:.0f} s)")
 237 | @@ -3264,7 +3384,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 238 |          if problems:
 239 |              note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 240 |              return None
 241 | -        pk["models"] = {"angle": angle_reply.backend,
 242 | +        pk["models"] = {"angle": angle_source(angle, angle_reply),
 243 |                          "writer": "the latest write's title and caption" if fixed is None else
 244 |                                    "the latest write's title; the caption is code's fixed line (07:30 (C), ruling 65 b)",
 245 |                          "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 246 | @@ -3289,9 +3409,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 247 |      with ThreadPoolExecutor(max_workers=8) as pool:
 248 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 249 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 250 | +            sel = story_pool(angle, cleared, by_story)    # RULING 118 (4): a story's angle chooses inside its story
 251 | +            #   (its join table, the fill, every swap; lineup_for and the search choose only among the angle's own and
 252 | +            #   its join table's moments, so the story holds there by construction)
 253 |              jt, a_ratings, ext = {}, {}, angle            # RULING 117: this angle's join table; its clips' ratings
 254 |              if candidate is None and angle["hook"] in cleared and angle["hook"] not in doomed:
 255 | -                jids = join_moments(angle, cleared, doomed)  # the moments that CAN be in its line-up
 256 | +                jids = join_moments(angle, sel, doomed)  # the moments that CAN be in its line-up
 257 |                  ext = dict(angle, moments=jids)           # the search's angle: the writer's order first
 258 |                  jms = [cleared[x] for x in jids]
 259 |                  jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
 260 | @@ -3332,7 +3455,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 261 |                              exception = supply_exception(segs, ctx)
 262 |                      filled = None
 263 |                      if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
 264 | -                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now,
 265 | +                        segs, filled = pool_fill(angle, sel, frozenset(dropped | doomed), ctx.now,
 266 |                                                   hook_only=True)   # FIRST: the
 267 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
 268 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 269 | @@ -3443,7 +3566,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 270 |                                        "the clips alone have no through-line a viewer can state (or it was not measured)")
 271 |                          break
 272 |                      dropped |= weak
 273 | -                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed), keep_hook=True)
 274 | +                    swapped, swaps = swap_lineup(segs, weak, sel, frozenset(dropped | doomed), keep_hook=True)
 275 |                      rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
 276 |                                    if swapped is not None else
 277 |                                    f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 278 | @@ -3572,7 +3695,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 279 |                              dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 280 |                              doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 281 |                              out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 282 | -                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed),
 283 | +                            swapped, swaps = swap_lineup(segs, set(bad), sel, frozenset(dropped | doomed),
 284 |                                                           keep_hook=True)
 285 |                              held = sorted(k for k, v in bad.items() if is_held(v))    # ruling 102: no answer
 286 |                              rec["why"] = (f"step A, re-screened off the writer's vendor, fails "
 287 | @@ -3764,7 +3887,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 288 |                          rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
 289 |                          w_used = writes
 290 |                          break
 291 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 292 | +                    pk["models"] = {"angle": angle_source(angle, angle_reply), "writer": wr.backend, "medley": med.get("backend"),
 293 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 294 |                                      "coherence": coh.get("backend"), "value": val.get("backend")}
 295 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med, "value": val}
 296 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 297 | index a5cae35..ed044d9 100644
 298 | --- a/tests/package/proof_ledger.py
 299 | +++ b/tests/package/proof_ledger.py
 300 | @@ -481,6 +481,7 @@ def main(argv=None):
 301 |                join_cache=os.path.join(HERE, "proof", "JOIN_CACHE.json"),          # ruling 117: cached
 302 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 303 |                scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 304 | +              stories_path=PK.STORIES,                                             # ruling 118 (4): read only
 305 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 306 |                lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 307 |                    segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 308 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 309 | index 7ab18d0..a110a21 100644
 310 | --- a/tests/package/test_candidates.py
 311 | +++ b/tests/package/test_candidates.py
 312 | @@ -173,5 +173,13 @@ class TestRegistry(unittest.TestCase):
 313 |          self.assertTrue(reg["candidates"]["a+b+c"]["history"][-1]["fresh"])
 314 |  
 315 |  
 316 | +    def test_a_story_angles_line_up_is_never_a_candidate(self):
 317 | +        """RULING 118 (4): its angle has no writer back-end (law L-x); a later build reads the story again."""
 318 | +        rec = record(T0, [dict(t(["a", "b", "c"]), angle=1), dict(t(["a", "b", "d"]), angle=2)])
 319 | +        rec["angles"] = [{"angle": "S", "moments": ["a", "b", "c"], "hook": "a", "story": "S-1"},
 320 | +                         {"angle": "W", "moments": ["a", "b", "d"], "hook": "a"}]
 321 | +        self.assertEqual(CA.seed(CA.new_registry(), rec, "r1"), ["a+b+d"])
 322 | +
 323 | +
 324 |  if __name__ == "__main__":
 325 |      unittest.main()
 326 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 327 | index 1adf4a6..48fe738 100644
 328 | --- a/tests/package/test_medley.py
 329 | +++ b/tests/package/test_medley.py
 330 | @@ -754,6 +754,8 @@ class Rig:
 331 |              kw["registered"] = self.registered
 332 |          if self.lock_check is not None:
 333 |              kw["lock_check"] = self.lock_check
 334 | +        if getattr(self, "stories_path", None):            # RULING 118 (4): the stories file (default: none read)
 335 | +            kw["stories_path"] = self.stories_path
 336 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 337 |              import tempfile
 338 |              fd, path = tempfile.mkstemp(suffix=".json")
 339 | @@ -4401,5 +4403,179 @@ class TestRuling109Channels(unittest.TestCase):
 340 |          self.assertNotIn("ruling_109", out)
 341 |  
 342 |  
 343 | +class TestRuling118StoryFirst(unittest.TestCase):
 344 | +    """RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS: an angle source that builds a line-up INSIDE
 345 | +    ONE STORY (the hook and every clip from the same story, 3 channels), ahead of the angle writer, every gate unchanged;
 346 | +    the receipts session's stories file is read only; no file: the build as before."""
 347 | +    GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
 348 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 349 | +    STORY = [("S-1", "Bitcoin's own story", ["h", "x", "y", "gone"])]
 350 | +
 351 | +    def file(self, stories, models=GROUP):
 352 | +        d = tempfile.mkdtemp()
 353 | +        self.addCleanup(lambda: [os.remove(os.path.join(d, f)) for f in os.listdir(d)] and None or os.rmdir(d))
 354 | +        p = os.path.join(d, "latest.json")
 355 | +        with open(p, "w") as f:
 356 | +            json.dump({"generated_at": "2026-11-16T13:43:27Z", "prompt_version": "st1-x", "models": models,
 357 | +                       "stories": [{"story_id": sid, "headline": hl, "channels": 3, "n_claims": 6,
 358 | +                                    "moments": [{"moment_id": m, "video_id": "v" + m, "channel_name": "c",
 359 | +                                                 "published_at": "2026-11-16T10:00:00Z", "claims": []} for m in ms]}
 360 | +                                   for sid, hl, ms in stories]}, f)
 361 | +        return p
 362 | +
 363 | +    def rig(self, ms, writer, stories, **kw):
 364 | +        rig = Rig(ms, writer, [(False, [], None, "none")] * 20, [], **kw)
 365 | +        rig.stories_path = self.file(stories) if stories is not None else "/nonexistent/stories/latest.json"
 366 | +        return rig
 367 | +
 368 | +    def test_every_swap_of_a_story_line_up_stays_inside_its_story(self):
 369 | +        ms = self.MS + [pm("w", "F", 13.0, rank=5.0)]                     # in the story, ranked under the pool's z, q
 370 | +        story = [("S-1", "Bitcoin's own story", ["h", "x", "y", "w"])]
 371 | +        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story)               # a weak clip: swapped inside the story
 372 | +        rig.medleys = [(False, [], {"clip_02": 2}, Rig.LINE)] + [(False, [], None, "none")] * 6
 373 | +        out = rig.run()
 374 | +        mine = [lu for r in out["tried"] if r["angle"] == 1 for lu in [r["lineup"]] if lu]
 375 | +        self.assertEqual(mine[:2], [["h", "x", "y"], ["h", "x", "w"]], out["tried"])
 376 | +        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story, angle_from=("xai:grok", "xai", "grok"),
 377 | +                       a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})    # a clip failing its re-screen: the same
 378 | +        rig.medleys, rig.writes = [(True, [], None, Rig.LINE)] * 2, [None, None]
 379 | +        out = rig.run()
 380 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "w"]])
 381 | +        self.assertIn("swapped {'y': 'w'}", out["tried"][0]["why"])
 382 | +        self.assertEqual(out["package"]["models"]["angle"], "story S-1 (the stories file)")   # who made its angle
 383 | +
 384 | +    def test_a_candidates_build_reads_no_stories(self):
 385 | +        med = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
 386 | +               "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}
 387 | +        c = PK.load_candidate({"tried": [{"angle": 1, "text": "W", "lineup": ["h", "z", "q"], "supply_exception": None,
 388 | +                                          "medley": med, "medley_ok": True}],
 389 | +                               "angles": [{"angle": "W", "moments": ["h", "x", "y", "z", "q"], "hook": "h"}],
 390 | +                               "angle_backend": "heimdall:deepseek", "angle_tried": []}, source="proof/ledger_x")
 391 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY, candidate=c)
 392 | +        out = rig.run()
 393 | +        self.assertNotIn("stories", out)
 394 | +        self.assertEqual((rig.medley_calls[0], out["tried"][0]["text"]), (["h", "z", "q"], "W"))   # its own, as judged
 395 | +
 396 | +    def test_the_file_is_read_in_its_writers_shape_or_not_at_all(self):
 397 | +        self.assertEqual(PK.read_stories(None), ([], {"path": None, "read": False, "why": "no stories file named"}))
 398 | +        st, rec = PK.read_stories("/nonexistent/stories/latest.json")
 399 | +        self.assertEqual((st, rec["read"], rec["why"]), ([], False, "no file"))
 400 | +        p = self.file([("S-1", "  Bitcoin   falls ", ["a", "b", "a"])])
 401 | +        st, rec = PK.read_stories(p)
 402 | +        self.assertEqual(st, [{"story_id": "S-1", "headline": "Bitcoin falls", "moment_ids": ["a", "b"]}])
 403 | +        self.assertEqual((rec["read"], rec["generated_at"], rec["models"], rec["stories"]),
 404 | +                         (True, "2026-11-16T13:43:27Z", self.GROUP, 1))
 405 | +        for bad in ([], {"stories": {}}, {"stories": [{"story_id": "S-1", "headline": "h", "moments": "a"}]},
 406 | +                    {"stories": [{"story_id": "S-1", "headline": " ", "moments": []}]},
 407 | +                    {"stories": [{"story_id": "", "headline": "h", "moments": []}]},
 408 | +                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": [{"moment_id": 3}]}]},
 409 | +                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": []}, "S-2"]}):
 410 | +            with open(p, "w") as f:
 411 | +                json.dump(bad, f)
 412 | +            st, rec = PK.read_stories(p)
 413 | +            self.assertEqual((st, rec["read"]), ([], False), bad)          # the whole file, never part of it
 414 | +        with open(p, "w") as f:
 415 | +            f.write("{")
 416 | +        self.assertEqual(PK.read_stories(p)[1]["why"], "unreadable (JSONDecodeError)")
 417 | +
 418 | +    def test_one_angle_a_story_on_its_best_passing_hook_new_channels_first_and_the_angle_contract(self):
 419 | +        pool = {m["moment_id"]: m for m in [pm("h", "A", 12.0), pm("x", "B", 14.0, rank=5.0), pm("y", "C", 13.0, rank=6.0),
 420 | +                                            pm("w", "A", 11.0, rank=9.0), pm("z", "D", 13.0)]}
 421 | +        st = [{"story_id": "S-1", "headline": "One", "moment_ids": ["h", "w", "x", "y", "gone"]},
 422 | +              {"story_id": "S-2", "headline": "Two", "moment_ids": ["h", "w", "z"]},          # two channels
 423 | +              {"story_id": "S-3", "headline": "Three", "moment_ids": ["y", "w", "z"]},        # no passing hook
 424 | +              {"story_id": "S-6", "headline": "Six", "moment_ids": ["x", "z", "gone"]},       # two cleared moments
 425 | +              {"story_id": "S-4", "headline": "Four", "moment_ids": ["h", "y", "z"]},
 426 | +              {"story_id": "S-5", "headline": "Five", "moment_ids": ["h", "y", "z"]}]         # over k
 427 | +        angles, rec = PK.story_angles(st, pool, [pool["x"], pool["h"]], k=2)               # the passing hooks, best first
 428 | +        self.assertEqual(angles, [{"angle": "One", "moments": ["x", "h", "y", "w"], "hook": "x", "story": "S-1"},
 429 | +                                  {"angle": "Four", "moments": ["h", "z", "y"], "hook": "h", "story": "S-4"}])
 430 | +        self.assertEqual((rec[0]["cleared"], rec[0]["channels"]), (4, 3))                  # "gone" is not in the pool
 431 | +        self.assertTrue(rec[1]["why"].startswith("not an angle: angle 1: >= 3 channels"), rec[1])
 432 | +        self.assertEqual(rec[2]["why"], "no passing hook among its cleared moments")
 433 | +        self.assertEqual(rec[3]["why"], "not an angle: angle 1: 3-8 distinct offered ids")     # the contract's 3
 434 | +        self.assertEqual(rec[5]["why"], "2 story angle(s) already")
 435 | +        for a in angles:                                                                  # the writer's own contract
 436 | +            PK.check_angles({"angles": [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
 437 | +                                         "support": {m: "s" for m in a["moments"]}}]}, pool, 1, hooks={"x", "h"})
 438 | +
 439 | +    def test_a_story_angle_chooses_only_inside_its_story(self):
 440 | +        pool = {m["moment_id"]: m for m in self.MS}
 441 | +        by = {"S-1": ["h", "x", "gone"]}
 442 | +        self.assertEqual(set(PK.story_pool({"story": "S-1"}, pool, by)), {"h", "x"})
 443 | +        self.assertEqual(PK.story_pool({"story": "S-9"}, pool, by), {})                  # a story it does not hold
 444 | +        self.assertIs(PK.story_pool({"angle": "w", "hook": "h"}, pool, by), pool)         # the writer's: as before
 445 | +
 446 | +    def test_the_story_angle_is_tried_first_and_its_line_ups_stay_inside_its_story(self):
 447 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 448 | +        out = rig.run()
 449 | +        self.assertEqual(out["angles"][0], {"angle": "Bitcoin's own story", "moments": ["h", "x", "y"], "hook": "h",
 450 | +                                            "story": "S-1"})
 451 | +        self.assertNotIn("story", out["angles"][1])                                      # the writer's, after it
 452 | +        self.assertEqual((out["stories"]["read"], out["stories"]["angles"][0]["angle"]), (True, 1))
 453 | +        self.assertEqual(out["tried"][0]["angle"], 1)
 454 | +        mine = [r["lineup"] for r in out["tried"] if r["angle"] == 1 and r["lineup"]]
 455 | +        self.assertTrue(mine and all(set(lu) <= {"h", "x", "y"} for lu in mine), out["tried"])
 456 | +        self.assertEqual(rig.medley_calls[0], mine[0])                                    # judged first, as any line-up
 457 | +
 458 | +    def test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it(self):
 459 | +        ms = [pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
 460 | +        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["h", "x", "y"])]).run()
 461 | +        self.assertEqual(out["angles"][0]["story"], "S-1")
 462 | +        mine = [r for r in out["tried"] if r["angle"] == 1]
 463 | +        self.assertTrue(mine)
 464 | +        for r in mine:                                    # 28 s of its own clips: no line-up, never the pool's z or q
 465 | +            self.assertIsNone(r["lineup"], r)
 466 | +            self.assertNotIn("pool_filled", r)
 467 | +
 468 | +    def test_the_join_table_of_a_story_angle_is_asked_only_of_its_story(self):
 469 | +        ids = [m["moment_id"] for m in self.MS]
 470 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY,
 471 | +                       joins={(a, b): True for a in ids for b in ids if a != b})
 472 | +        out = rig.run()
 473 | +        self.assertEqual(rig.join_calls[0], ["h", "x", "y"])                             # the story angle's: its story
 474 | +        self.assertEqual(set(rig.join_calls[1]), set(ids))                               # the writer's: the pool
 475 | +        self.assertTrue(all(set(r["lineup"]) <= {"h", "x", "y"} for r in out["tried"] if r["angle"] == 1 and r["lineup"]))
 476 | +
 477 | +    def test_the_stories_grouping_models_never_judge_its_line_ups(self):
 478 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 479 | +        rig.router.backends["heimdall:qwen"].model = "minimax/minimax-m3.1-flash"        # a back-end running one of them
 480 | +        seen, jt = [], rig.join_table
 481 | +        rig.join_table = lambda router, ms_, c, wv, wf=None, **k: (seen.append((set(wv), set(wf or ()))),
 482 | +                                                                   jt(router, ms_, c, wv, wf, **k))[1]
 483 | +        out = rig.run()
 484 | +        self.assertEqual(out["stories"]["writers"], {"vendors": ["heimdall"], "families": ["qwen"]})
 485 | +        self.assertTrue(seen and all("heimdall" in wv and "qwen" in wf for wv, wf in seen), seen)
 486 | +
 487 | +    def test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before(self):
 488 | +        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], None).run()
 489 | +        self.assertEqual((out["stories"]["read"], out["stories"]["why"]), (False, "no file"))
 490 | +        self.assertTrue(all("story" not in a for a in out["angles"]))
 491 | +        ms = self.MS + [pm("w", "A", 11.0)]
 492 | +        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["h", "w", "x"])]).run()
 493 | +        self.assertTrue(out["stories"]["angles"][0]["why"].startswith("not an angle"))
 494 | +        self.assertTrue(all("story" not in a for a in out["angles"]))
 495 | +        self.assertNotIn("stories", Rig(self.MS, ["h", "x", "y", "z", "q"], [(False, [], None, "none")] * 4, []).run())
 496 | +        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
 497 | +        rig.router.answers["angle_write"] = ["{", "{"]                               # the writer gives no angle:
 498 | +        out = rig.run()                                                              # the build stops, as before
 499 | +        self.assertTrue(out["why_none"].startswith("no readable angles"))
 500 | +        self.assertEqual((out["angles"], rig.medley_calls), ([], []))
 501 | +
 502 | +    def test_a_story_angles_line_up_is_never_kept_as_a_candidate(self):
 503 | +        med = {"measured": True, "replayed": False}
 504 | +        rec = {"angle_backend": "heimdall:deepseek",
 505 | +               "angles": [{"angle": "S", "moments": ["h", "x", "y"], "hook": "h", "story": "S-1"},
 506 | +                          {"angle": "W", "moments": ["h", "x", "y", "z"], "hook": "h"}],
 507 | +               "tried": [{"angle": 1, "text": "S", "lineup": ["h", "x", "y"], "medley_ok": True, "medley": med},
 508 | +                         {"angle": 2, "text": "W", "lineup": ["h", "x", "z"], "medley_ok": True, "medley": med}]}
 509 | +        self.assertEqual(PK.load_candidate(rec)["index"], 1)                             # the writer's line-up
 510 | +        with self.assertRaisesRegex(ValueError, "story 'S-1'"):
 511 | +            PK.load_candidate(rec, 0)
 512 | +        rec["angles"][1]["story"] = "S-2"
 513 | +        with self.assertRaisesRegex(ValueError, "no line-up in this record passed"):
 514 | +            PK.load_candidate(rec)
 515 | +
 516 | +
 517 |  if __name__ == "__main__":
 518 |      unittest.main()
 519 | 
```

---

pp-selectid: RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS. Files: pipeline/package.py (read_stories,
story_angles, story_pool, story_writers, angle_source; build(); load_candidate), pipeline/candidates.py (seed),
tests/package/proof_ledger.py (the builds pass the stories file), tests/package/test_medley.py, tests/package/test_candidates.py.

THE ORDER, verbatim: "(4) STORY-FIRST LINE-UPS (the supply fix that costs nothing): what killed every line-up yesterday was
joins and no through-line, because angles were assembled from moments that only share a topic word. The receipts session
(pipeline_pi_receipts, /home/ultron/pulse_intel) now reads every moment into claims and groups the day's claims across
channels into STORIES. It will write, read-only for you, /home/ultron/pulse_intel/stories/latest.json: stories with their
moment_ids, channels and one-line headline, refreshed as moments arrive. Add an angle source that builds a line-up INSIDE
ONE STORY (hook and clips all from the same story, 3 channels), ahead of the angle writer; every gate unchanged. Until that
file exists, build as now."
THE FILE (its writer's docstring, /home/ultron/pulse_intel/stories.py): {"generated_at", "grouped_at", "window", "prompt_version",
"models": {"group": [two model ids]}, "counts", "note", "stories": [{"story_id", "headline", "channels", "n_claims",
"moments": [{"moment_id", "video_id", "channel_name", "published_at", "claims": [...]}]}]}; replaced in one step (temp file
+ rename); a moment sits in at most one story; a story is written only with claims from >= 2 channels; every 15 minutes.

THE CHANGE:
- read_stories(path): the file in that shape or not at all (no file / unreadable / any story out of shape: no stories, the
  record says why; the build goes on as before). Each story -> {story_id, headline (whitespace normalised), moment_ids}.
- story_angles(stories, cleared, passing hooks, k=MAX_ANGLES): per story (file order), its best PASSING hook among its
  cleared moments; moments = that hook, then the story's other cleared moments, a new channel first, then by rank (<= 8);
  sentence = the headline; it must pass the writer's own angle contract (check_angles, package.py:1058: 3-8 distinct
  moments, >= 3 channels, the hook one of them and a passing hook) or the story gives no angle (recorded). At most k.
- build(): only when there is no candidate (ruling 66) and a stories path: the story angles go AHEAD of the writer's angles
  (each list sorted by ruling 59/57's key as before). The writer is still asked exactly as before (its follow-up only for
  its own angles); when it gives no angle the build stops as before (the writes stay on the writer's gateway, ruling 85:
  package.py:3207). In the per-angle loop, sel = story_pool(angle, cleared, ...): a story angle's join table
  (join_moments), its fill (pool_fill) and both swaps (swap_lineup: a weak clip; a clip failing its re-screen) take
  moments ONLY from its story's cleared moments; any other angle the whole pool as before. lineup_for (package.py:1730)
  and search_lineups (package.py:2143) choose only among the angle's own moments / its join table's moments, so the story
  holds there by construction (unchanged).
- Law L-x: story_writers(): the router back-ends running the file's grouping models give their vendors and families to
  the writers' sets every verdict avoids (with the angle writer's, as before).
- angle_source(): a story angle's package records "story <id> (the stories file)" as its angle's maker (models.angle).
- A story angle's line-up is never a ruling-66 candidate (candidates.seed skips it; load_candidate refuses it and its
  first pick skips it): its angle has no writer back-end for L-x; a later build reads the story again.
- proof_ledger passes stories_path=PK.STORIES to the builds (a candidate's build ignores it).

UNCHANGED GUARDS (not in the diff): every verdict and gate after the line-up (clips-alone, coherence, fidelity, step A
re-screens, the hook bar, the render's STAND_ALONE at the pin stage package.py:1085); the loop stops at the first package
that passes every gate; the candidate loop takes angles[0] only on a candidate's build (package.py:3410).

TESTS (test_medley TestRuling118StoryFirst, 11; test_candidates, 1): the reader (shape or nothing); the angles (best
passing hook, new channels first, 2 channels refused, no passing hook, k); story_pool; the build: the story angle first and
its line-ups inside its story; a story too short is never filled from outside it; its join table asked only of its story;
both swaps inside it, and its package names the story; L-x; no file / no 3-channel story / no writer: as before; a
candidate's build reads no stories; never a candidate. Mutations S1-S18 after a control run: 18 of 18 killed.

PLEASE CHECK: (1) that a story angle can never take a hook or clip from outside its story, in any path of the loop;
(2) that nothing changes when there is no file, no story of 3 channels, or a candidate; (3) that every gate is unchanged;
(4) L-x; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
