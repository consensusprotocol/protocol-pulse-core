# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 22:52 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (969 lines)
```
   1 | diff --git a/pipeline/editorial_select.py b/pipeline/editorial_select.py
   2 | index b3413b83..f2a04047 100644
   3 | --- a/pipeline/editorial_select.py
   4 | +++ b/pipeline/editorial_select.py
   5 | @@ -130,7 +130,9 @@ _TERMINAL = (".", "!", "?")
   6 |  
   7 |  
   8 |  def _tok(w):
   9 | -    return [t for t in re.split(r"[^a-z0-9]+", (w or "").lower().replace("’", "'").replace("'", "")) if t]
  10 | +    """Words in the pipeline's one canonical form (pipeline/canon.py)."""
  11 | +    import canon
  12 | +    return canon.canon_tokens(w)
  13 |  
  14 |  
  15 |  def _ends_statement(word):
  16 | @@ -163,8 +165,10 @@ def align_quote(quote, words, t0, t1):
  17 |      """Locate a verified quote in word timestamps within [t0, t1]. Returns
  18 |      {"w0", "w1", "start", "end", "ratio"} or None. Never fabricates a location."""
  19 |      from difflib import SequenceMatcher
  20 | -    qt = [t for w in (quote or "").split() for t in _tok(w)]
  21 | -    toks = [(t, i) for i, w in enumerate(words) if t0 <= w["start"] <= t1 for t in _tok(w["word"])]
  22 | +    import canon                                      # one canonical form; a token keeps the word it starts in
  23 | +    qt = canon.canon_tokens(quote)
  24 | +    idx = [i for i, w in enumerate(words) if t0 <= w["start"] <= t1]
  25 | +    toks = [(t, idx[o]) for t, o in canon.canon_aligned([words[i]["word"] for i in idx])]
  26 |      if len(qt) < 5 or not toks:
  27 |          return None
  28 |      seq = [t for t, _ in toks]
  29 | @@ -372,12 +376,16 @@ _NOT_ENTITY = {"I", "The", "This", "That", "These", "Those", "It", "And", "But",
  30 |  
  31 |  
  32 |  def _lc_words(text):
  33 | -    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("’", "'"))
  34 | +    """Words in the pipeline's one canonical form, contractions reduced to their heads ("that's" -> "that":
  35 | +    backward references and interjections ask which word a contraction starts with; pipeline/canon.py)."""
  36 | +    import canon
  37 | +    return canon.canon_tokens(text, heads=True)
  38 |  
  39 |  
  40 |  def _numbers(text):
  41 | -    t = re.sub(r"(\d)\s+([.,])\s*(\d)", r"\1\2\3", text or "")      # whisper writes '6 .3' and '80 ,000'
  42 | -    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", t)}
  43 | +    """The numbers a text states, as canonical values ('80 ,000' = '80,000' = 'eighty thousand'; pipeline/canon.py)."""
  44 | +    import canon
  45 | +    return {t for t in canon.canon_tokens(text) if re.fullmatch(r"\d+(?:\.\d+)?", t)}
  46 |  
  47 |  
  48 |  def _anchor_entities(anchor, q):
  49 | @@ -575,12 +583,16 @@ def _infra_error(msg):
  50 |  
  51 |  
  52 |  def select_story(run_dir, log=print, embedder=None, llm=None, universe_fn=None,
  53 | -                 stories_path=STORIES_PATH, topup=True, now=None):
  54 | +                 stories_path=STORIES_PATH, topup=True, now=None, transcript_fn=None, words_fn=None):
  55 | +    """transcript_fn(video_id) -> record and words_fn(video_id) -> (record, status) are the backtest's frozen
  56 | +    inputs (pipeline/backtest.py: a saved day's own transcript records; existing word records only, no download,
  57 | +    no GPU swap); production passes neither."""
  58 |      rec = {"law": "titles/metadata are discovery hints; transcripts establish story identity",
  59 |             "started": ts.now_iso()}
  60 |      ck = Checkpoint(run_dir, rec)
  61 |      try:
  62 | -        return _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now)
  63 | +        return _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now,
  64 | +                             transcript_fn, words_fn)
  65 |      except NoProducibleStory:
  66 |          raise
  67 |      except Exception as e:
  68 | @@ -590,7 +602,8 @@ def select_story(run_dir, log=print, embedder=None, llm=None, universe_fn=None,
  69 |          raise
  70 |  
  71 |  
  72 | -def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now):
  73 | +def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now,
  74 | +                  transcript_fn=None, words_fn=None):
  75 |      import story_semantics as sm
  76 |      from transcript_ingest import universe as ingest_universe
  77 |      t0 = time.time()
  78 | @@ -611,7 +624,7 @@ def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_pat
  79 |      vids = [v for v in vids if v["video_id"] not in V2F_VIDEO_IDS]
  80 |      budget, used, uni = TOPUP_MAX_WHISPER_HOURS * 3600, 0.0, []
  81 |      for v in sorted(vids, key=lambda v: (0 if layout_eligible(v["channel"]) else 1, v["age_h"])):
  82 | -        r = ts.canonical_transcript(v["video_id"])
  83 | +        r = (transcript_fn or ts.canonical_transcript)(v["video_id"])
  84 |          status = "cached" if r else None
  85 |          if r is None and topup:
  86 |              try:
  87 | @@ -849,9 +862,11 @@ def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_pat
  88 |                      need[v["video_id"]] = v["channel_id"]
  89 |          words, arb = {}, {"videos": sorted(need)}
  90 |          rec.setdefault("gpu_arbitration", {})[pname] = arb
  91 | -        todo = [vid for vid in need if not ts.sentence_ready(ts.canonical_transcript(vid))]
  92 | +        todo = [] if words_fn else [vid for vid in need if not ts.sentence_ready(ts.canonical_transcript(vid))]
  93 |          for vid in need:
  94 | -            if vid not in todo:
  95 | +            if words_fn:
  96 | +                words[vid] = words_fn(vid)                  # backtest: existing word records only
  97 | +            elif vid not in todo:
  98 |                  words[vid] = (ts.canonical_transcript(vid), "cached")
  99 |          if todo:
 100 |              try:
 101 | diff --git a/pipeline/render16.py b/pipeline/render16.py
 102 | index 7d3fccac..18962aa2 100644
 103 | --- a/pipeline/render16.py
 104 | +++ b/pipeline/render16.py
 105 | @@ -32,11 +32,11 @@ from config import (FPS, PRE_ROLL, WIDTH, HEIGHT, ACCENT_COLOR,
 106 |                      conform_outro)
 107 |  
 108 |  # Import shoutout renderer from segment_v1 (frozen)
 109 | -sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
 110 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "segment_v1"))   # this checkout, never a fixed path (Claude-gates C4)
 111 |  from scene_shoutout import render_shoutout, save_qa_frames
 112 |  
 113 |  # Import relay for API keys
 114 | -sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 115 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
 116 |  from relay import get_key
 117 |  
 118 |  
 119 | diff --git a/pipeline/render_vertical.py b/pipeline/render_vertical.py
 120 | index 6a66f9a9..418fd124 100644
 121 | --- a/pipeline/render_vertical.py
 122 | +++ b/pipeline/render_vertical.py
 123 | @@ -36,7 +36,7 @@ from config import (FPS, PRE_ROLL, WIDTH, HEIGHT, VERT_W, VERT_H,
 124 |  from shoutout import build_shoutout
 125 |  
 126 |  # Import relay for API keys
 127 | -sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 128 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
 129 |  from relay import get_key
 130 |  
 131 |  # ── Vertical-specific constants ──
 132 | diff --git a/pipeline/shoutout.py b/pipeline/shoutout.py
 133 | index b9663c40..ee8dba7c 100644
 134 | --- a/pipeline/shoutout.py
 135 | +++ b/pipeline/shoutout.py
 136 | @@ -20,7 +20,7 @@ sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 137 |  from config import resolve_paths
 138 |  
 139 |  # Import the frozen shoutout renderer
 140 | -sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
 141 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "segment_v1"))   # this checkout, never a fixed path (Claude-gates C4)
 142 |  from scene_shoutout import render_shoutout, save_qa_frames
 143 |  
 144 |  
 145 | diff --git a/pipeline/signoff.py b/pipeline/signoff.py
 146 | index e91040c0..ec7bd872 100644
 147 | --- a/pipeline/signoff.py
 148 | +++ b/pipeline/signoff.py
 149 | @@ -23,7 +23,7 @@ import datetime
 150 |  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 151 |  from config import SIGNOFF_WORD_CAP
 152 |  
 153 | -sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 154 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
 155 |  from relay import get_key
 156 |  
 157 |  LEGACY_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "signoff_history.json")
 158 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
 159 | index 8bc551a9..f6cbdc63 100644
 160 | --- a/pipeline/story_semantics.py
 161 | +++ b/pipeline/story_semantics.py
 162 | @@ -360,11 +360,10 @@ def prompt_sha(p):
 163 |  
 164 |  
 165 |  def _norm(s):
 166 | -    """Quote-check normal form: entities decoded and split Whisper tokens joined (law L-h, as
 167 | -    transcript_store.read_text), lower-case, letters / digits / spaces only."""
 168 | -    import html
 169 | -    t = re.sub(r"\s+(?=[.,][0-9a-z])", "", html.unescape(s or "").lower())
 170 | -    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", t)).strip()
 171 | +    """Quote-check normal form = the pipeline's one canonical form (pipeline/canon.py: entities, unicode, split
 172 | +    tokens, numbers, currency / percent, case, punctuation)."""
 173 | +    import canon
 174 | +    return canon.canon(s)
 175 |  
 176 |  
 177 |  def quote_in(quote, texts):
 178 | diff --git a/pipeline/vo.py b/pipeline/vo.py
 179 | index af7ab1bf..31c0d485 100644
 180 | --- a/pipeline/vo.py
 181 | +++ b/pipeline/vo.py
 182 | @@ -16,7 +16,7 @@ import time
 183 |  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 184 |  from config import resolve_paths
 185 |  
 186 | -sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 187 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
 188 |  from relay import get_key
 189 |  
 190 |  
 191 | diff --git a/scripts/pulse_check_run.sh b/scripts/pulse_check_run.sh
 192 | index 0346fae3..34183a0f 100755
 193 | --- a/scripts/pulse_check_run.sh
 194 | +++ b/scripts/pulse_check_run.sh
 195 | @@ -11,14 +11,19 @@
 196 |  #   detached session pipeline_pulse_check_<UTC stamp>; scripts/tmux_cleanup.sh (cron) keeps 'pipeline'
 197 |  #   sessions, so a long render is never reaped as idle. No other session is touched.
 198 |  # - GPU0 only (CUDA_VISIBLE_DEVICES=0); nothing is published: drops go to the Telegram approval chat
 199 | -#   only (pipeline/telegram.deliver_run), and ONLY when every gate passed: "HOLD FOR APPROVAL - all gates
 200 | -#   passed, no waivers" (orchestrator 2026-11-11 08:30: a HOLD is never sent; its run dir is the record).
 201 | +#   only (pipeline/telegram.deliver_run), and ONLY for a run release_auth.authorise passes (its attestation is
 202 | +#   ALL_PASS and every bound file has its attested sha256): "HOLD FOR APPROVAL - all release gates passed, no
 203 | +#   waivers" (orchestrator 2026-11-11 08:30: a HOLD is never sent; its run dir is the record). Children never
 204 | +#   inherit the lock fd (9>&-), so an orphaned child cannot keep the next run out.
 205 |  # - log: logs/pulse_check/run_<stamp>.log (git HEAD, run dir, exit code, delivery message ids)
 206 |  # - DEC-9 story ledger: an AUTO run whose two finals went out as HOLD FOR APPROVAL is recorded in
 207 |  #   data/pulse_check/story_ledger.jsonl (its counted evidence statements); later auto runs never select an
 208 |  #   event resting on one of them (pipeline/story_ledger.py)
 209 | -# Exit (--foreground, and in the log): run_fresh's code (0 = every gate passed, 3 = HOLD), 70 = the run
 210 | -# rendered but the Telegram drop failed, 71 = delivered but the DEC-9 story ledger write failed,
 211 | +# - preflight first (pipeline/preflight.py: GPU0, Ollama, yt-dlp, ElevenLabs quota, Telegram, disk, a clean pushed
 212 | +#   HEAD, no other run, brand assets + registry): a failure exits 3 (HOLD) before run_fresh starts
 213 | +# Exit (--foreground, and in the log): run_fresh's code (0 = every release gate passed, 3 = HOLD), 70 = the run
 214 | +# passed but was not delivered (the drop failed or was refused by release_auth, or no finals were found), 71 =
 215 | +# delivered but the DEC-9 story ledger write failed,
 216 |  # 75 = locked, 64 = usage. The detached launcher exits 0 once the
 217 |  # tmux session is up (1 if tmux failed, 75 if a run already holds the lock); the run's code is in the log.
 218 |  set -uo pipefail
 219 | @@ -49,7 +54,9 @@ if [ "$FOREGROUND" = 0 ] && [[ "$CUR_SESSION" != pipeline_* ]]; then
 220 |    fi
 221 |    NAME="pipeline_pulse_check_$STAMP"
 222 |    CMD="bash $(printf '%q' "$SELF") --foreground"
 223 | -  for a in "${ORIG[@]}"; do CMD+=" $(printf '%q' "$a")"; done
 224 | +  # the RESOLVED arguments (a relative PIN path is not re-resolved inside the new session: GPT-gates F39)
 225 | +  for a in "${ARGS[@]}"; do CMD+=" $(printf '%q' "$a")"; done
 226 | +  [ "$TELEGRAM" = 0 ] && CMD+=" --no-telegram"
 227 |    if ! tmux new-session -d -s "$NAME" "$CMD"; then
 228 |      echo "pulse_check_run: tmux could not start session $NAME" >&2; exit 1
 229 |    fi
 230 | @@ -69,7 +76,13 @@ fi
 231 |  export CUDA_VISIBLE_DEVICES=0
 232 |  cd "$REPO/pipeline" || exit 1
 233 |  echo "=== pulse_check_run $STAMP | HEAD $(git -C "$REPO" rev-parse HEAD) | args: ${ARGS[*]:-auto} ===" | tee -a "$LOG"
 234 | -python3 run_fresh.py "${ARGS[@]}" 2>&1 | tee -a "$LOG"
 235 | +# preflight (orchestrator 2026-11-11 '21:10'): seconds, before any hour is spent; a failure is a HOLD with the reason
 236 | +python3 preflight.py 9>&- 2>&1 | tee -a "$LOG" 9>&-
 237 | +if [ "${PIPESTATUS[0]}" != 0 ]; then
 238 | +  echo "run_fresh exit 3 | run dir none (preflight HOLD: run_fresh not started)" | tee -a "$LOG"
 239 | +  exit 3
 240 | +fi
 241 | +python3 run_fresh.py "${ARGS[@]}" 9>&- 2>&1 | tee -a "$LOG" 9>&-
 242 |  RC=${PIPESTATUS[0]}
 243 |  RUN_DIR="$(grep -m1 -oP '(?<==== FRESH-TOPIC RUN ).*(?= ===)' "$LOG" || true)"
 244 |  echo "run_fresh exit $RC | run dir ${RUN_DIR:-none}" | tee -a "$LOG"
 245 | @@ -80,7 +93,7 @@ if [ "$TELEGRAM" = 1 ] && [ "$RC" != 0 ]; then
 246 |    echo "HOLD (run_fresh exit $RC): not delivered; see $RUN_DIR/REPORT.md" | tee -a "$LOG"
 247 |  elif [ "$TELEGRAM" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/out/segment.mp4" ] && [ -f "$RUN_DIR/out/segment_vertical.mp4" ]; then
 248 |    python3 -c "import sys, telegram; r = telegram.deliver_run(sys.argv[1]); print('delivered:', [m.get('message_id') for m in r['messages']])" \
 249 | -    "$RUN_DIR" 2>&1 | tee -a "$LOG"
 250 | +    "$RUN_DIR" 9>&- 2>&1 | tee -a "$LOG" 9>&-
 251 |    if [ "${PIPESTATUS[0]}" != 0 ]; then
 252 |      echo "pulse_check_run: Telegram delivery FAILED (see above); run dir $RUN_DIR" | tee -a "$LOG"
 253 |      exit 70
 254 | @@ -88,12 +101,15 @@ elif [ "$TELEGRAM" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/out/segment.mp4"
 255 |    # DEC-9 ledger, from the delivery record just written (a separate step: a ledger fault never reads as a
 256 |    # failed drop, and is never silent: the next auto run could select this story again)
 257 |    python3 -c "import json, os, sys, story_ledger; r = json.load(open(os.path.join(sys.argv[1], 'TELEGRAM_DELIVERY.json'))); e = story_ledger.record_if_approved(sys.argv[1], r, sys.argv[2]); print('story ledger:', 'recorded ' + e['run'] if e else 'not recorded (pinned, review-only or option)')" \
 258 | -    "$RUN_DIR" "$MODE" 2>&1 | tee -a "$LOG"
 259 | +    "$RUN_DIR" "$MODE" 9>&- 2>&1 | tee -a "$LOG" 9>&-
 260 |    if [ "${PIPESTATUS[0]}" != 0 ]; then
 261 |      echo "pulse_check_run: delivered, but the story ledger was NOT recorded (see above): the next auto run may select this story again; run dir $RUN_DIR" | tee -a "$LOG"
 262 |      exit 71
 263 |    fi
 264 |  elif [ "$TELEGRAM" = 1 ]; then
 265 | -  echo "no finals rendered: nothing delivered (the run's REPORT.md and status.json are the ledger)" | tee -a "$LOG"
 266 | +  # run_fresh exited 0 (every release gate passed) but no run dir / finals were found: nothing was delivered,
 267 | +  # and that is never a success (GPT-gates F38, Claude-gates P2)
 268 | +  echo "pulse_check_run: run_fresh exit 0 but run dir '${RUN_DIR:-none}' has no finals: NOT delivered" | tee -a "$LOG"
 269 | +  exit 70
 270 |  fi
 271 |  exit "$RC"
 272 | diff --git a/pipeline/backtest.py b/pipeline/backtest.py
 273 | new file mode 100644
 274 | index 00000000..5ba6215b
 275 | --- /dev/null
 276 | +++ b/pipeline/backtest.py
 277 | @@ -0,0 +1,236 @@
 278 | +#!/usr/bin/env python3
 279 | +"""pipeline/backtest.py — editorial selection on every saved universe (orchestrator order 2026-11-11 '21:10').
 280 | +
 281 | +Every fresh run that saved its universe (runs/fresh_*/TOPIC_SELECTION.json with transcript shas) is a free test
 282 | +day. Each day goes through editorial selection only (select_story: clusters -> coverage -> clip quality, whose
 283 | +windows already apply the stand-alone screen and the text-level sentence rules: boundary start, full-stop end,
 284 | +whole sentences, durations), with:
 285 | +  - the day's OWN transcript records (by the sha it recorded; frozen inputs, so a code change is what moves a row),
 286 | +  - existing word records only (store word records, else a run's large-v3 transcript; no download, no GPU swap),
 287 | +  - the story-engine items the day saw (rebuilt from its saved candidates),
 288 | +  - 'now' pinned to that run's start,
 289 | +  - the cached embeddings and the validated LLM reply cache (warm days re-ask nothing).
 290 | +Not covered (needs media): the acoustic sentence law at the cut, review / validate on the EDL, render, gates.
 291 | +
 292 | +One table: day, universe, clusters (>= 2 channels), Bitcoin-screened (48 h / 72 h), coverage-qualified,
 293 | +producible, and the selected lineup (story, channels), or the gate that stopped each of the top 5. From now on this
 294 | +is the selection regression suite: a change that lowers the number of producible days is a HOLD on the change.
 295 | +
 296 | +Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/backtest.py [--runs NAME ...] [--out DIR]
 297 | +"""
 298 | +import argparse
 299 | +import glob
 300 | +import hashlib
 301 | +import json
 302 | +import os
 303 | +import sys
 304 | +import time
 305 | +import traceback
 306 | +from datetime import datetime, timezone
 307 | +
 308 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
 309 | +REPO = os.path.dirname(PIPELINE_DIR)
 310 | +sys.path.insert(0, PIPELINE_DIR)
 311 | +import transcript_store as ts  # noqa: E402
 312 | +
 313 | +RUNS_DIR = os.environ.get("PP_RUNS_DIR", os.path.join(REPO, "runs"))   # a worktree backtest reads the main runs
 314 | +# acceptance-critical day first (Nov 10: the protected preview's day), then the newest
 315 | +PRIORITY = ("fresh_20261110_093150", "fresh_20261112_013452", "fresh_20261111_213954", "fresh_20261107_080503",
 316 | +            "fresh_20261106_213852")
 317 | +
 318 | +
 319 | +def saved_days(runs_dir=RUNS_DIR):
 320 | +    """Run dirs whose TOPIC_SELECTION.json carries a universe with transcript shas, priority days first."""
 321 | +    out = []
 322 | +    for p in sorted(glob.glob(os.path.join(runs_dir, "fresh_*", "TOPIC_SELECTION.json"))):
 323 | +        try:
 324 | +            d = json.load(open(p))
 325 | +        except (OSError, ValueError):
 326 | +            continue
 327 | +        uni = d.get("universe") or []
 328 | +        if d.get("started") and any(u.get("transcript_sha256") for u in uni):
 329 | +            out.append(os.path.dirname(p))
 330 | +    rank = {n: i for i, n in enumerate(PRIORITY)}
 331 | +    return sorted(out, key=lambda r: (rank.get(os.path.basename(r), len(rank)), os.path.basename(r)))
 332 | +
 333 | +
 334 | +def frozen_transcripts(saved):
 335 | +    """transcript_fn: the record with the sha this day recorded (hash-checked on read), else None."""
 336 | +    want = {u["video_id"]: u.get("transcript_sha256") for u in saved.get("universe") or []}
 337 | +
 338 | +    def fn(video_id):
 339 | +        sha = want.get(video_id)
 340 | +        if not sha:
 341 | +            return None
 342 | +        try:
 343 | +            return next((r for r in ts.transcript_records(video_id) if r["transcript_sha256"] == sha), None)
 344 | +        except (OSError, ValueError, ts.AcquisitionError):
 345 | +            return None
 346 | +    return fn
 347 | +
 348 | +
 349 | +def _run_transcript(video_id, runs_dir=RUNS_DIR):
 350 | +    """A run's own large-v3 word transcript of this video (select_passages), wrapped as a word record."""
 351 | +    import punctuation
 352 | +    for p in sorted(glob.glob(os.path.join(runs_dir, "*", "transcripts", f"{video_id}.json"))):
 353 | +        try:
 354 | +            d = json.load(open(p))
 355 | +        except (OSError, ValueError):
 356 | +            continue
 357 | +        words = d.get("words") or []
 358 | +        if words and (d.get("punctuation") or not punctuation.needs_restoration(words)):
 359 | +            return {"video_id": video_id, "words": words, "transcript_method": "run_transcript:large-v3",
 360 | +                    "transcript_model": "large-v3 (run transcript)", "source_path": os.path.relpath(p, REPO),
 361 | +                    "transcript_sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
 362 | +    return None
 363 | +
 364 | +
 365 | +def offline_words(runs_dir=RUNS_DIR):
 366 | +    """words_fn: a sentence-ready store word record, else a run's large-v3 transcript, else none (a live run
 367 | +    would transcribe: recorded as the gate)."""
 368 | +    def fn(video_id):
 369 | +        r = ts.canonical_transcript(video_id)
 370 | +        if ts.sentence_ready(r):
 371 | +            return r, f"store {r['transcript_method']}"
 372 | +        r = _run_transcript(video_id, runs_dir)
 373 | +        if r:
 374 | +            return r, f"run transcript {r['source_path']}"
 375 | +        return None, "backtest: no word record (a live run would transcribe it)"
 376 | +    return fn
 377 | +
 378 | +
 379 | +def stories_of(saved):
 380 | +    """The story-engine items this day saw, rebuilt from its saved candidates."""
 381 | +    items = []
 382 | +    for c in saved.get("candidates") or []:
 383 | +        if c.get("origin") != "story_engine" or not c.get("headline"):
 384 | +            continue
 385 | +        items.append({"rank": c.get("engine_rank"), "overall_score": c.get("engine_score"),
 386 | +                      "headline": c["headline"], "summary": c.get("summary") or "",
 387 | +                      "source_domain": c.get("source_domain") or "",
 388 | +                      "freshness_minutes": round((c.get("age_h") or 0) * 60)})
 389 | +    gen = (saved.get("story_engine") or {}).get("generated_at") or saved["started"]
 390 | +    return {"generated_at": gen, "stories": items}
 391 | +
 392 | +
 393 | +def universe_of(saved, registry):
 394 | +    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}
 395 | +
 396 | +    def fn(hours):
 397 | +        out = []
 398 | +        for u in saved.get("universe") or []:
 399 | +            ch = by_cid.get(u.get("channel_id")) or {"channel_id": u.get("channel_id"), "display_name": u.get("channel")}
 400 | +            out.append({"video_id": u["video_id"], "rss": {"title": u.get("title"), "published": u.get("published_at")},
 401 | +                        "channel": ch, "age_h": u.get("age_h")})
 402 | +        return out
 403 | +    return fn
 404 | +
 405 | +
 406 | +def summarise(day_dir, out_dir, seconds, outcome):
 407 | +    t = json.load(open(os.path.join(out_dir, "TOPIC_SELECTION.json")))
 408 | +    em = t.get("emergent_clusters") or []
 409 | +    cands = t.get("candidates") or []
 410 | +    row = {"run": os.path.basename(day_dir), "day": (t.get("today") or ""), "outcome": outcome,
 411 | +           "seconds": round(seconds), "universe": (t.get("universe_summary") or {}).get("videos"),
 412 | +           "with_transcript": (t.get("universe_summary") or {}).get("with_transcript"),
 413 | +           "clusters": len(em), "screen_48h": sum(e.get("screen") == "48h" for e in em),
 414 | +           "screen_72h": sum(e.get("screen") == "72h" for e in em),
 415 | +           "coverage_qualified": sum(1 for c in cands if c.get("clip_quality") is not None),
 416 | +           "producible": sum(1 for c in cands if c.get("decision") == "producible"),
 417 | +           "llm": t.get("llm", {}).get("calls"), "llm_cache_hits": t.get("llm", {}).get("cache_hits")}
 418 | +    if t.get("selected"):
 419 | +        chosen = json.load(open(os.path.join(out_dir, "passages.json"))).get("chosen") or []
 420 | +        row["selected"] = {"headline": t["selected"]["headline"], "origin": t["selected"]["origin"],
 421 | +                           "channels": [p["channel"] for p in chosen],
 422 | +                           "lineup": [{"kind": p["kind"], "channel": p["channel"], "video_id": p["video_id"],
 423 | +                                       "start": p["start"], "end": p["end"], "text": p["text"][:160]} for p in chosen]}
 424 | +    ranked = sorted((c for c in cands if c.get("importance")),
 425 | +                    key=lambda c: -c["importance"].get("importance_score", 0))
 426 | +    row["top5"] = [{"headline": c["headline"][:100], "origin": c["origin"],
 427 | +                    "score": c["importance"].get("importance_score"),
 428 | +                    "gate": c.get("decision") or "; ".join(c.get("importance_gate") or []) or "not evaluated"}
 429 | +                   for c in ranked[:5]]
 430 | +    return row
 431 | +
 432 | +
 433 | +def run_day(day_dir, out_root, L, E, registry):
 434 | +    import editorial_select as es
 435 | +    saved = json.load(open(os.path.join(day_dir, "TOPIC_SELECTION.json")))
 436 | +    out_dir = os.path.join(out_root, os.path.basename(day_dir))
 437 | +    os.makedirs(out_dir, exist_ok=True)
 438 | +    sp = os.path.join(out_dir, "stories.json")
 439 | +    json.dump(stories_of(saved), open(sp, "w"))
 440 | +    now = datetime.fromisoformat(saved["started"]).astimezone(timezone.utc)
 441 | +    logf = open(os.path.join(out_dir, "selection.log"), "w")
 442 | +    t0 = time.time()
 443 | +    try:
 444 | +        es.select_story(out_dir, log=lambda s: (logf.write(str(s) + "\n"), logf.flush()), embedder=E, llm=L,
 445 | +                        universe_fn=universe_of(saved, registry), stories_path=sp, topup=False, now=now,
 446 | +                        transcript_fn=frozen_transcripts(saved), words_fn=offline_words())
 447 | +        outcome = "PRODUCIBLE"
 448 | +    except es.NoProducibleStory as e:
 449 | +        outcome = f"HOLD: {e}"
 450 | +    except Exception as e:                                         # a crash is a row, never a silent skip
 451 | +        outcome = f"CRASH: {type(e).__name__}: {e}"
 452 | +        logf.write(traceback.format_exc())
 453 | +    finally:
 454 | +        logf.close()
 455 | +    try:
 456 | +        return summarise(day_dir, out_dir, time.time() - t0, outcome)
 457 | +    except (OSError, ValueError, KeyError) as e:
 458 | +        return {"run": os.path.basename(day_dir), "outcome": outcome, "summary_error": str(e),
 459 | +                "seconds": round(time.time() - t0)}
 460 | +
 461 | +
 462 | +def table(rows):
 463 | +    lines = ["| run | day | outcome | universe | clusters | 48h / 72h | cov-qualified | producible | lineup | s | LLM calls / cache hits |",
 464 | +             "|---|---|---|---|---|---|---|---|---|---|---|"]
 465 | +    for r in rows:
 466 | +        sel = r.get("selected")
 467 | +        lineup = (f"{sel['headline'][:70]} ({', '.join(sel['channels'])})" if sel else "-")
 468 | +        lines.append(f"| {r['run']} | {r.get('day', '')} | {r['outcome'][:60]} | {r.get('universe')} / "
 469 | +                     f"{r.get('with_transcript')} | {r.get('clusters')} | {r.get('screen_48h')} / {r.get('screen_72h')} | "
 470 | +                     f"{r.get('coverage_qualified')} | {r.get('producible')} | {lineup} | {r.get('seconds')} | "
 471 | +                     f"{r.get('llm')} / {r.get('llm_cache_hits')} |")
 472 | +    days = {r.get("day") for r in rows if r["outcome"] == "PRODUCIBLE"}
 473 | +    lines.append(f"\nProducible days: {len(days)} of {len({r.get('day') for r in rows})} ({sorted(days)})")
 474 | +    for r in rows:
 475 | +        if r["outcome"] != "PRODUCIBLE":
 476 | +            lines.append(f"\n{r['run']} top 5 by importance and the gate that stopped each:")
 477 | +            lines += [f"- [{c['score']}] {c['headline']} ({c['origin']}): {c['gate'][:200]}" for c in r.get("top5", [])]
 478 | +    return "\n".join(lines)
 479 | +
 480 | +
 481 | +def main(argv=None):
 482 | +    ap = argparse.ArgumentParser()
 483 | +    ap.add_argument("--runs", nargs="*", help="run dir names (default: every saved universe)")
 484 | +    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "backtest_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
 485 | +    a = ap.parse_args(argv)
 486 | +    import story_semantics as sm
 487 | +    days = saved_days()
 488 | +    if a.runs:
 489 | +        days = [d for d in days if os.path.basename(d) in set(a.runs)]
 490 | +    os.makedirs(a.out, exist_ok=True)
 491 | +    registry = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
 492 | +    E, L = sm.Embedder(), sm.LocalLLM().start()
 493 | +    rows, t0 = [], time.time()
 494 | +    try:
 495 | +        for d in days:
 496 | +            print(f"== {os.path.basename(d)}", flush=True)
 497 | +            rows.append(run_day(d, a.out, L, E, registry))
 498 | +            r = rows[-1]
 499 | +            print(f"   {r['outcome'][:100]} | {r.get('seconds')} s | LLM {r.get('llm')} calls, "
 500 | +                  f"{r.get('llm_cache_hits')} cached", flush=True)
 501 | +            json.dump({"rows": rows, "seconds": round(time.time() - t0)}, open(os.path.join(a.out, "backtest.json"), "w"),
 502 | +                      indent=1)
 503 | +            open(os.path.join(a.out, "BACKTEST.md"), "w").write(table(rows) + "\n")
 504 | +    finally:
 505 | +        L.stop()
 506 | +        E.close()
 507 | +    print(table(rows))
 508 | +    print(f"total {round(time.time() - t0)} s -> {a.out}")
 509 | +    return 0
 510 | +
 511 | +
 512 | +if __name__ == "__main__":
 513 | +    sys.exit(main())
 514 | diff --git a/pipeline/preflight.py b/pipeline/preflight.py
 515 | new file mode 100644
 516 | index 00000000..eb2afdce
 517 | --- /dev/null
 518 | +++ b/pipeline/preflight.py
 519 | @@ -0,0 +1,166 @@
 520 | +#!/usr/bin/env python3
 521 | +"""pipeline/preflight.py — fail fast before a Pulse Check run spends an hour (orchestrator order 2026-11-11 '21:10').
 522 | +
 523 | +Checks (seconds; secrets are read through relay.get_key and never printed):
 524 | +  gpu0        GPU0 has no compute job except the GPU0 Ollama server's own runners, and enough memory free once
 525 | +              that model is counted as ours
 526 | +  ollama      the editorial model is installed on the GPU0 Ollama and answers a 1-token request
 527 | +  yt_dlp      yt-dlp reads one known video's metadata
 528 | +  elevenlabs  the API answers with the account's quota and enough characters left for a sign-off
 529 | +  telegram    the approval bot answers getMe
 530 | +  disk        free space on the repo's filesystem
 531 | +  git         pipeline / segment_v1 tracked files unmodified, HEAD pushed (an ancestor of the upstream branch)
 532 | +  no_other_run no run_fresh.py process besides this run
 533 | +  assets      outro masters, brand mark, music, channel registry and every layout-eligible channel's avatar
 534 | +Exit 0 = all pass, 3 = HOLD (the wrapper records the reasons and never starts run_fresh). Usage: python3 preflight.py
 535 | +"""
 536 | +import glob
 537 | +import json
 538 | +import os
 539 | +import shutil
 540 | +import subprocess
 541 | +import sys
 542 | +import urllib.request
 543 | +
 544 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
 545 | +REPO = os.path.dirname(PIPELINE_DIR)
 546 | +sys.path.insert(0, PIPELINE_DIR)
 547 | +sys.path.insert(1, os.path.join(REPO, "video_pipeline_v3"))     # relay.get_key (the pipeline's key loader)
 548 | +
 549 | +GPU0_FREE_MIB = 20000             # editorial model ~19 GB + Whisper; counted with our own Ollama model released
 550 | +DISK_FREE_GB = 25
 551 | +ELEVEN_MIN_CHARS = 2000           # a sign-off is ~150 characters; this leaves room for retries
 552 | +KNOWN_VIDEO = "RBFN4CB60To"       # a v2f source video (references/v2f_2026-11-06), public and stable
 553 | +
 554 | +
 555 | +def _run(cmd, timeout=30):
 556 | +    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
 557 | +
 558 | +
 559 | +def _get_json(url, headers=None, timeout=15, data=None):
 560 | +    req = urllib.request.Request(url, headers=headers or {}, data=data)
 561 | +    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
 562 | +
 563 | +
 564 | +def check_gpu0():
 565 | +    import story_semantics as sm
 566 | +    gpus = dict(l.split(", ") for l in _run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"])
 567 | +                .stdout.strip().splitlines())
 568 | +    apps = [l.split(", ") for l in _run(["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory",
 569 | +                                         "--format=csv,noheader,nounits"]).stdout.strip().splitlines() if l]
 570 | +    serve = sm.LocalLLM()._listener_pid()
 571 | +    ours = set(_run(["pgrep", "-P", str(serve)]).stdout.split()) | {str(serve)} if serve else set()
 572 | +    others = [(p, m) for p, u, m in apps if u == gpus.get("0") and p not in ours]
 573 | +    if others:
 574 | +        return False, "other job(s) on GPU0: " + ", ".join(
 575 | +            f"pid {p} ({m} MiB) {_run(['ps', '-o', 'args=', '-p', p]).stdout.strip()[:60]}" for p, m in others)
 576 | +    used, total = sm.gpu0_memory()
 577 | +    held = sum(int(m) for p, u, m in apps if u == gpus.get("0") and p in ours)
 578 | +    free = total - used + held
 579 | +    return free >= GPU0_FREE_MIB, f"{free} MiB available with our model released (need {GPU0_FREE_MIB})"
 580 | +
 581 | +
 582 | +def check_ollama():
 583 | +    import story_semantics as sm
 584 | +    digest = sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)
 585 | +    if not digest:
 586 | +        return False, f"{sm.LLM_MODEL} not installed on {sm.LLM_HOST}"
 587 | +    body = json.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False,
 588 | +                       "options": {"num_predict": 1}}).encode()
 589 | +    r = _get_json(f"http://{sm.LLM_HOST}/api/generate", {"Content-Type": "application/json"}, timeout=180, data=body)
 590 | +    return "response" in r, f"{sm.LLM_MODEL} {digest[:12]} answered"
 591 | +
 592 | +
 593 | +def check_yt_dlp():
 594 | +    import transcript_store as ts
 595 | +    r = ts._ytdlp(["-J", "--skip-download", ts.canonical_url(KNOWN_VIDEO)], timeout=60)
 596 | +    try:
 597 | +        ok = json.loads(r.stdout).get("id") == KNOWN_VIDEO
 598 | +    except ValueError:
 599 | +        ok = False
 600 | +    return ok, "metadata read" if ok else f"yt-dlp failed: {(r.stderr or '')[-160:]}"
 601 | +
 602 | +
 603 | +def check_elevenlabs():
 604 | +    from relay import get_key
 605 | +    s = _get_json("https://api.elevenlabs.io/v1/user/subscription", {"xi-api-key": get_key("ELEVENLABS_API_KEY")})
 606 | +    left = int(s.get("character_limit", 0)) - int(s.get("character_count", 0))
 607 | +    return left >= ELEVEN_MIN_CHARS, f"{left} characters left (need {ELEVEN_MIN_CHARS})"
 608 | +
 609 | +
 610 | +def check_telegram():
 611 | +    from relay import get_key
 612 | +    r = _get_json(f"https://api.telegram.org/bot{get_key('TELEGRAM_BOT_TOKEN')}/getMe")
 613 | +    return bool(r.get("ok")), "bot answers" if r.get("ok") else "getMe not ok"
 614 | +
 615 | +
 616 | +def check_disk():
 617 | +    free = shutil.disk_usage(REPO).free / 1e9
 618 | +    return free >= DISK_FREE_GB, f"{free:.0f} GB free (need {DISK_FREE_GB})"
 619 | +
 620 | +
 621 | +def check_git():
 622 | +    dirty = _run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no", "--", "pipeline",
 623 | +                  "segment_v1"]).stdout.strip()
 624 | +    if dirty:
 625 | +        return False, "tracked pipeline / segment_v1 files modified: " + " ".join(dirty.split()[:6])
 626 | +    up = _run(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "@{u}"]).stdout.strip()
 627 | +    if not up:
 628 | +        return False, "the branch has no upstream"
 629 | +    pushed = _run(["git", "-C", REPO, "merge-base", "--is-ancestor", "HEAD", up]).returncode == 0
 630 | +    head = _run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"]).stdout.strip()
 631 | +    return pushed, f"HEAD {head} " + ("pushed" if pushed else f"NOT on {up}")
 632 | +
 633 | +
 634 | +def check_no_other_run():
 635 | +    me = os.getpid()
 636 | +    procs = [l for l in _run(["pgrep", "-af", "run_fresh.py"]).stdout.splitlines()
 637 | +             if l and int(l.split()[0]) != me and "pgrep" not in l]
 638 | +    return not procs, "none" if not procs else f"running: {procs[0][:80]}"
 639 | +
 640 | +
 641 | +def check_assets():
 642 | +    import config
 643 | +    reg = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
 644 | +    need = {"outro 16:9": config.OUTRO_MASTER_16x9, "outro 9:16": config.OUTRO_MASTER_9x16,
 645 | +            "brand mark": config.resolve_brand(PIPELINE_DIR)}
 646 | +    missing = [k for k, p in need.items() if not (p and os.path.isfile(p) and os.path.getsize(p) > 0)]
 647 | +    if not glob.glob(os.path.join(REPO, "video_pipeline_v3", "assets", "music", "*.mp3")):
 648 | +        missing.append("music")
 649 | +    import editorial_select as es
 650 | +    avatars = [c["display_name"] for c in reg if c.get("enabled", True) and es.layout_eligible(c)
 651 | +               and not (c.get("avatar_path") and os.path.isfile(c["avatar_path"]))]
 652 | +    missing += [f"avatar: {n}" for n in avatars]
 653 | +    return not missing, "present" if not missing else "missing: " + ", ".join(missing[:8])
 654 | +
 655 | +
 656 | +CHECKS = [("gpu0", check_gpu0), ("ollama", check_ollama), ("yt_dlp", check_yt_dlp),
 657 | +          ("elevenlabs", check_elevenlabs), ("telegram", check_telegram), ("disk", check_disk),
 658 | +          ("git", check_git), ("no_other_run", check_no_other_run), ("assets", check_assets)]
 659 | +
 660 | +
 661 | +def run_checks(checks=None):
 662 | +    out = []
 663 | +    for name, fn in (CHECKS if checks is None else checks):
 664 | +        try:
 665 | +            ok, detail = fn()
 666 | +        except Exception as e:                        # an exception is a failed check, never a pass
 667 | +            ok, detail = False, f"{type(e).__name__}: {str(e)[:160]}"
 668 | +        out.append({"check": name, "ok": bool(ok), "detail": detail})
 669 | +    return out
 670 | +
 671 | +
 672 | +def main():
 673 | +    res = run_checks()
 674 | +    for r in res:
 675 | +        print(f"  preflight {r['check']:13s} [{'PASS' if r['ok'] else 'FAIL'}] {r['detail']}", flush=True)
 676 | +    bad = [r for r in res if not r["ok"]]
 677 | +    if bad:
 678 | +        print("HOLD (preflight): " + "; ".join(f"{r['check']}: {r['detail']}" for r in bad), flush=True)
 679 | +        return 3
 680 | +    print("preflight: all checks passed", flush=True)
 681 | +    return 0
 682 | +
 683 | +
 684 | +if __name__ == "__main__":
 685 | +    sys.exit(main())
 686 | diff --git a/pipeline/test_backtest.py b/pipeline/test_backtest.py
 687 | new file mode 100644
 688 | index 00000000..1222c02a
 689 | --- /dev/null
 690 | +++ b/pipeline/test_backtest.py
 691 | @@ -0,0 +1,130 @@
 692 | +#!/usr/bin/env python3
 693 | +"""pipeline/backtest.py (orchestrator order 2026-11-11 '21:10'): every saved universe through editorial selection only,
 694 | +with its own transcript records, existing word records only (no download, no GPU swap), its own story-engine
 695 | +items and 'now' pinned to its run.
 696 | +unit   saved-day discovery and priority; the story items rebuilt from a day's candidates; word sources (a store word
 697 | +       record first, else a run's large-v3 transcript, else the gate text); select_story's hooks: with
 698 | +       transcript_fn / words_fn it never acquires, transcribes or releases GPU0
 699 | +Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_backtest.py"""
 700 | +import json
 701 | +import os
 702 | +import shutil
 703 | +import sys
 704 | +import tempfile
 705 | +import unittest
 706 | +
 707 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 708 | +sys.path.insert(0, PIPELINE)
 709 | +import backtest as B  # noqa: E402
 710 | +import transcript_store as ts  # noqa: E402
 711 | +from test_editorial_robust import FakeLLM, Orchestration  # noqa: E402
 712 | +
 713 | +
 714 | +def _saved(started="2026-11-10T09:31:52+00:00", shas=True):
 715 | +    return {"started": started, "today": started[:10],
 716 | +            "universe": [{"video_id": "VIDAAAAAAA1", "channel": "X", "channel_id": "UCx", "title": "t",
 717 | +                          "published_at": started, "age_h": 3.0, "transcript_sha256": "ab" * 32 if shas else None}],
 718 | +            "story_engine": {"generated_at": "2026-11-10T09:10:00+00:00"},
 719 | +            "candidates": [{"origin": "story_engine", "engine_rank": 1, "engine_score": 50, "headline": "H1",
 720 | +                            "summary": "S1", "source_domain": "d.com", "age_h": 2.0},
 721 | +                           {"origin": "transcript_cluster", "headline": "C1"}]}
 722 | +
 723 | +
 724 | +class TestDays(unittest.TestCase):
 725 | +    def setUp(self):
 726 | +        self.tmp = tempfile.mkdtemp(prefix="btdays_")
 727 | +
 728 | +    def tearDown(self):
 729 | +        shutil.rmtree(self.tmp, ignore_errors=True)
 730 | +
 731 | +    def _day(self, name, saved):
 732 | +        os.makedirs(os.path.join(self.tmp, name))
 733 | +        json.dump(saved, open(os.path.join(self.tmp, name, "TOPIC_SELECTION.json"), "w"))
 734 | +
 735 | +    def test_only_days_with_a_saved_universe_count_and_the_priority_day_leads(self):
 736 | +        self._day("fresh_20261112_000000", _saved("2026-11-12T00:00:00+00:00"))
 737 | +        self._day("fresh_20261110_093150", _saved())
 738 | +        self._day("fresh_20261106_133059", {"started": "2026-11-06T13:30:59+00:00", "universe": []})
 739 | +        self._day("fresh_20261107_064831", _saved("2026-11-07T06:48:31+00:00", shas=False))
 740 | +        names = [os.path.basename(d) for d in B.saved_days(self.tmp)]
 741 | +        self.assertEqual(names, ["fresh_20261110_093150", "fresh_20261112_000000"])
 742 | +
 743 | +    def test_the_story_items_are_the_days_own(self):
 744 | +        st = B.stories_of(_saved())
 745 | +        self.assertEqual(st["generated_at"], "2026-11-10T09:10:00+00:00")
 746 | +        self.assertEqual([s["headline"] for s in st["stories"]], ["H1"])               # clusters are re-derived
 747 | +        self.assertEqual(st["stories"][0]["freshness_minutes"], 120)
 748 | +
 749 | +
 750 | +class TestWordSources(unittest.TestCase):
 751 | +    def setUp(self):
 752 | +        self.tmp = tempfile.mkdtemp(prefix="btwords_")
 753 | +        self.saved = (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR)
 754 | +        ts.STORE_DIR = self.tmp
 755 | +        ts.TRANSCRIPTS_DIR = os.path.join(self.tmp, "transcripts")
 756 | +        ts.STATE_DIR = os.path.join(self.tmp, "state")
 757 | +        ts.MEDIA_DIR = os.path.join(self.tmp, "media")
 758 | +        self.runs = os.path.join(self.tmp, "runs")
 759 | +
 760 | +    def tearDown(self):
 761 | +        ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR = self.saved
 762 | +        shutil.rmtree(self.tmp, ignore_errors=True)
 763 | +
 764 | +    def test_store_then_run_transcript_then_the_gate(self):
 765 | +        words = [{"word": w + ".", "start": i, "end": i + 0.5} for i, w in enumerate(["One", "Two", "Three"])]
 766 | +        os.makedirs(os.path.join(self.runs, "pinned_x", "transcripts"))
 767 | +        json.dump({"words": words}, open(os.path.join(self.runs, "pinned_x", "transcripts", "RUNVIDAAAA1.json"), "w"))
 768 | +        fn = B.offline_words(self.runs)
 769 | +        r, st = fn("RUNVIDAAAA1")
 770 | +        self.assertTrue(st.startswith("run transcript"))
 771 | +        self.assertEqual((r["words"], r["transcript_method"]), (words, "run_transcript:large-v3"))
 772 | +        r, st = fn("NOWORDSAAA1")
 773 | +        self.assertIsNone(r)
 774 | +        self.assertIn("no word record", st)
 775 | +        vid = "STOREVIDAA1"                                   # a sentence-ready store record wins over the run's
 776 | +        meta = {"schema": 1, "video_id": vid, "canonical_url": ts.canonical_url(vid), "channel_id": "UCfakefake03",
 777 | +                "channel_name": "Fake", "exact_title": "t", "published_at": "2026-11-10T00:00:00+00:00", "duration": 9}
 778 | +        os.makedirs(ts._vdir(vid))
 779 | +        ts._store(ts._make_record(meta, "whisper_words", "fake", ts.sentences_from_words(words), extra={"words": words}))
 780 | +        json.dump({"words": words}, open(os.path.join(self.runs, "pinned_x", "transcripts", f"{vid}.json"), "w"))
 781 | +        r, st = fn(vid)
 782 | +        self.assertEqual((st, r["transcript_method"]), ("store whisper_words", "whisper_words"))
 783 | +
 784 | +
 785 | +class TestHooks(Orchestration):
 786 | +    def test_with_the_hooks_selection_never_acquires_transcribes_or_releases_gpu0(self):
 787 | +        import editorial_select as es
 788 | +        calls = {"acquire": 0, "release": 0, "words": []}
 789 | +        orig = ts.acquire
 790 | +
 791 | +        def no_acquire(*a, **k):
 792 | +            calls["acquire"] += 1
 793 | +            raise AssertionError("backtest must not acquire")
 794 | +
 795 | +        def release(llm, **kw):
 796 | +            calls["release"] += 1
 797 | +            raise AssertionError("backtest must not release GPU0")
 798 | +
 799 | +        def words_fn(vid):
 800 | +            calls["words"].append(vid)
 801 | +            return None, "backtest: no word record (a live run would transcribe it)"
 802 | +        import story_semantics as sm
 803 | +        from test_editorial_robust import NOW, FakeEmbedder
 804 | +        saved_release = sm.release_gpu0_for_whisper
 805 | +        ts.acquire, sm.release_gpu0_for_whisper = no_acquire, release
 806 | +        try:
 807 | +            with self.assertRaises(es.NoProducibleStory):
 808 | +                es.select_story(self.run_dir, log=lambda s: None, embedder=FakeEmbedder(), llm=FakeLLM(),
 809 | +                                universe_fn=lambda h: self.uni, stories_path=self.stories, topup=False, now=NOW,
 810 | +                                transcript_fn=ts.canonical_transcript, words_fn=words_fn)
 811 | +        finally:
 812 | +            ts.acquire, sm.release_gpu0_for_whisper = orig, saved_release
 813 | +        self.assertEqual((calls["acquire"], calls["release"]), (0, 0))
 814 | +        self.assertTrue(calls["words"])                          # the coverage-qualified story asked for words
 815 | +        t = self.topic()
 816 | +        dem = [c for c in t["candidates"] if c["headline"].startswith("Democrats")][0]
 817 | +        self.assertIn("no word record", json.dumps(dem.get("clip_quality") or dem.get("decision")))
 818 | +
 819 | +
 820 | +if __name__ == "__main__":
 821 | +    unittest.main()
 822 | diff --git a/pipeline/test_preflight.py b/pipeline/test_preflight.py
 823 | new file mode 100644
 824 | index 00000000..edbb2739
 825 | --- /dev/null
 826 | +++ b/pipeline/test_preflight.py
 827 | @@ -0,0 +1,141 @@
 828 | +#!/usr/bin/env python3
 829 | +"""pipeline/preflight.py (orchestrator order 2026-11-11 '21:10'): fail fast before a run spends an hour.
 830 | +unit   an exception in a check is a failed check (fail closed); any failure exits 3 with 'HOLD (preflight)';
 831 | +       a foreign job on GPU0 fails (the GPU0 Ollama's own runners do not); a dirty or unpushed tree fails; secrets
 832 | +       never reach the output; a disabled channel's missing avatar does not fail the asset check
 833 | +wrapper scripts/pulse_check_run.sh runs preflight.py after the run lock and before run_fresh.py, and exits 3 on a
 834 | +       failure without starting run_fresh
 835 | +Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_preflight.py"""
 836 | +import io
 837 | +import os
 838 | +import re
 839 | +import sys
 840 | +import types
 841 | +import unittest
 842 | +from contextlib import redirect_stdout
 843 | +
 844 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 845 | +REPO = os.path.dirname(PIPELINE)
 846 | +sys.path.insert(0, PIPELINE)
 847 | +import preflight as P  # noqa: E402
 848 | +
 849 | +
 850 | +class R:
 851 | +    def __init__(self, stdout="", returncode=0, stderr=""):
 852 | +        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr
 853 | +
 854 | +
 855 | +class TestRunner(unittest.TestCase):
 856 | +    def test_an_exception_is_a_failed_check_and_any_failure_holds(self):
 857 | +        def boom():
 858 | +            raise RuntimeError("network down")
 859 | +        res = P.run_checks([("ok", lambda: (True, "fine")), ("boom", boom)])
 860 | +        self.assertEqual([(r["check"], r["ok"]) for r in res], [("ok", True), ("boom", False)])
 861 | +        self.assertIn("network down", res[1]["detail"])
 862 | +        saved = P.CHECKS
 863 | +        P.CHECKS = [("ok", lambda: (True, "fine")), ("bad", lambda: (False, "nope"))]
 864 | +        out = io.StringIO()
 865 | +        try:
 866 | +            with redirect_stdout(out):
 867 | +                code = P.main()
 868 | +        finally:
 869 | +            P.CHECKS = saved
 870 | +        self.assertEqual(code, 3)
 871 | +        self.assertIn("HOLD (preflight): bad: nope", out.getvalue())
 872 | +
 873 | +
 874 | +class TestChecks(unittest.TestCase):
 875 | +    def setUp(self):
 876 | +        self.saved_run = P._run
 877 | +
 878 | +    def tearDown(self):
 879 | +        P._run = self.saved_run
 880 | +
 881 | +    def test_a_foreign_job_on_gpu0_fails_and_our_ollama_runner_does_not(self):
 882 | +        import story_semantics as sm
 883 | +        saved = (sm.LocalLLM._listener_pid, sm.gpu0_memory, os.environ.get("CUDA_VISIBLE_DEVICES"))
 884 | +        os.environ["CUDA_VISIBLE_DEVICES"] = "0"                       # as the wrapper exports it
 885 | +        sm.LocalLLM._listener_pid = lambda self: 100
 886 | +        sm.gpu0_memory = lambda: (19000, 24564)
 887 | +
 888 | +        def run(cmd, timeout=30):
 889 | +            if "--query-gpu=index,uuid" in cmd:
 890 | +                return R("0, GPU-A\n1, GPU-B\n")
 891 | +            if "--query-compute-apps=pid,gpu_uuid,used_memory" in cmd:
 892 | +                return R(self.apps)
 893 | +            if cmd[0] == "pgrep":
 894 | +                return R("101\n")
 895 | +            return R("python3 something\n")
 896 | +        P._run = run
 897 | +        try:
 898 | +            self.apps = "101, GPU-A, 18900\n555, GPU-B, 21000\n"          # our runner on GPU0, GPU1 busy
 899 | +            ok, d = P.check_gpu0()
 900 | +            self.assertTrue(ok, d)
 901 | +            self.apps = "101, GPU-A, 18900\n777, GPU-A, 1962\n"          # a foreign job on GPU0
 902 | +            ok, d = P.check_gpu0()
 903 | +            self.assertFalse(ok)
 904 | +            self.assertIn("pid 777", d)
 905 | +        finally:
 906 | +            sm.LocalLLM._listener_pid, sm.gpu0_memory, cvd = saved
 907 | +            if cvd is None:
 908 | +                os.environ.pop("CUDA_VISIBLE_DEVICES", None)
 909 | +            else:
 910 | +                os.environ["CUDA_VISIBLE_DEVICES"] = cvd
 911 | +
 912 | +    def test_a_dirty_or_unpushed_tree_fails(self):
 913 | +        replies = {"status": R(" M pipeline/editorial_select.py\n")}
 914 | +        P._run = lambda cmd, timeout=30: replies.get(cmd[3] if len(cmd) > 3 else "", R(""))
 915 | +        ok, d = P.check_git()
 916 | +        self.assertFalse(ok)
 917 | +        self.assertIn("editorial_select.py", d)
 918 | +        replies = {"status": R(""), "rev-parse": R("origin/branch\n"), "merge-base": R("", returncode=1)}
 919 | +        P._run = lambda cmd, timeout=30: replies.get(cmd[3], R("abc123\n"))
 920 | +        ok, d = P.check_git()
 921 | +        self.assertFalse(ok)
 922 | +        self.assertIn("NOT on origin/branch", d)
 923 | +
 924 | +    def test_secrets_never_reach_the_output(self):
 925 | +        relay = types.ModuleType("relay")
 926 | +        relay.get_key = lambda name: "SECRET-" + name
 927 | +        saved_mod, saved_get = sys.modules.get("relay"), P._get_json
 928 | +        sys.modules["relay"] = relay
 929 | +        seen = []
 930 | +
 931 | +        def get(url, headers=None, timeout=15, data=None):
 932 | +            seen.append(url + str(headers))
 933 | +            return {"ok": True} if "telegram" in url else {"character_limit": 10000, "character_count": 100}
 934 | +        P._get_json = get
 935 | +        try:
 936 | +            res = P.run_checks([("elevenlabs", P.check_elevenlabs), ("telegram", P.check_telegram)])
 937 | +        finally:
 938 | +            P._get_json = saved_get
 939 | +            if saved_mod is None:
 940 | +                sys.modules.pop("relay", None)
 941 | +            else:
 942 | +                sys.modules["relay"] = saved_mod
 943 | +        self.assertTrue(all(r["ok"] for r in res), res)
 944 | +        self.assertTrue(any("SECRET-" in s for s in seen))                # the key was used...
 945 | +        self.assertFalse(any("SECRET" in r["detail"] for r in res))       # ...and never reported
 946 | +
 947 | +    def test_a_disabled_channel_without_an_avatar_does_not_fail_assets(self):
 948 | +        import json
 949 | +        reg = json.load(open(os.path.join(PIPELINE, "channels.json")))
 950 | +        off = [c for c in reg if not c.get("enabled", True) and not c.get("avatar_path")]
 951 | +        if not off:
 952 | +            self.skipTest("no disabled channel without an avatar in the registry")
 953 | +        ok, d = P.check_assets()
 954 | +        self.assertTrue(ok, d)
 955 | +        self.assertNotIn(off[0]["display_name"], d)
 956 | +
 957 | +
 958 | +class TestWrapper(unittest.TestCase):
 959 | +    def test_preflight_runs_before_run_fresh_and_a_failure_exits_3(self):
 960 | +        s = open(os.path.join(REPO, "scripts", "pulse_check_run.sh")).read()
 961 | +        pf, rf = s.index("python3 preflight.py"), s.index("python3 run_fresh.py")
 962 | +        lock = s.index('if ! flock -n 9; then\n  echo "pulse_check_run: another run holds', s.index('LOG_DIR='))
 963 | +        self.assertTrue(lock < pf < rf)
 964 | +        self.assertRegex(s[pf:rf], re.compile(r'PIPESTATUS\[0\]\}" != 0 \]; then.*?exit 3', re.S))
 965 | +
 966 | +
 967 | +if __name__ == "__main__":
 968 | +    unittest.main()
 969 | 
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

