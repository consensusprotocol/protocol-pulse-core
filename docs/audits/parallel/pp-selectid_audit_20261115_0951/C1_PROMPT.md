# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_0951
# Branch: pp-selectid
# Generated: 2026-11-15 09:51 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_0951/C1_STEP.diff (312 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 88a255b..db941f0 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -160,9 +160,11 @@ def _num(x):
   6 |  def word_pass_index(path=WORD_PASS):
   7 |      """The word-pass worker's rows -> ({moment_id: the LAST row of that moment, when it is sentence_ready with a
   8 |      window_record and a record_sha256}, report). A failed moment's row has neither, and the worker never retries it.
   9 | -    No file yet = no window record yet: ({}, report). A file that exists but cannot be read raises: it is never read
  10 | -    as an empty word pass (law L-j)."""
  11 | -    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path}
  12 | +    report["refused"]: every moment whose last row gives no window record (failed, not sentence-ready, or unreadable),
  13 | +    sorted. The worker never works a moment again once it has a row (the integrator, 09:37 ET Nov 15), so these are
  14 | +    final, never "waiting". No file yet = no window record yet: ({}, report). A file that exists but cannot be read
  15 | +    raises: it is never read as an empty word pass (law L-j)."""
  16 | +    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path, "refused": []}
  17 |      try:
  18 |          f = open(path)
  19 |      except FileNotFoundError:
  20 | @@ -193,6 +195,7 @@ def word_pass_index(path=WORD_PASS):
  21 |              rep["ready"] += 1
  22 |          else:
  23 |              rep["unreadable"] += 1
  24 | +    rep["refused"] = sorted(mid for mid in last if mid not in out)
  25 |      return out, rep
  26 |  
  27 |  
  28 | @@ -420,9 +423,12 @@ def reanchor(row, src, cap=None):
  29 |      return sp, info
  30 |  
  31 |  
  32 | -def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None):
  33 | +def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None, word_pass_refused=()):
  34 |      """Ledger rows -> (moments in the packager's form, {key: Source}, report). word_pass: word_pass_index()'s
  35 | -    {moment_id: row} (None = no window records).
  36 | +    {moment_id: row} (None = no window records). word_pass_refused: its report's "refused" moment ids. A row with
  37 | +    neither a sentence-ready window record nor a full-video record is counted as REFUSED when the word pass refused it
  38 | +    (final: never re-worked), else as waiting (no row yet): report "window_refused" apart from "window_waiting" and
  39 | +    "no_word_record".
  40 |      - A video with a sentence-ready full-video word record: every row re-anchors in it (key: the video id).
  41 |      - Otherwise ONE WINDOW PER MOMENT, the word-pass worker writing one around each moment. A row with its own
  42 |        sentence-ready window record re-anchors in THAT window, and its moment carries source_key =
  43 | @@ -434,9 +440,10 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  44 |      Rows with no word record, rows that do not re-anchor on whole sentences, and duplicates are dropped, each counted
  45 |      with why. report: "videos" counts the videos that gave moments and "sources" their records (one per window
  46 |      moment); window_records is {video: [records]} (audit 0208 C2, glm N2 / N4)."""
  47 | -    word_pass = word_pass or {}
  48 | +    word_pass, refused = word_pass or {}, set(word_pass_refused or ())
  49 |      report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
  50 | -              "window_records": {}, "window_waiting": 0, "window_failed": 0, "window_passed_over": {},
  51 | +              "window_records": {}, "window_waiting": 0, "window_refused": 0, "window_failed": 0,
  52 | +              "window_passed_over": {},
  53 |                "no_caption_context": {},
  54 |                "fallbacks": {},
  55 |                "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
  56 | @@ -502,10 +509,14 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  57 |                  sources[vid] = src
  58 |              continue
  59 |          caps, why_w, waiting, windows, kept = {}, [], 0, 0, []     # kept: (start, end, moment id) of window moments
  60 | +        n_ref = 0                                    # rows the word pass refused: final, never waiting
  61 |          for i, r in irs:                             # ONE WINDOW PER MOMENT
  62 |              wp = word_pass.get(r["moment_id"])
  63 |              if wp is None:
  64 | -                waiting += 1
  65 | +                if r["moment_id"] in refused:
  66 | +                    n_ref += 1
  67 | +                else:
  68 | +                    waiting += 1
  69 |                  continue
  70 |              wsrc, wpath, why = window_source(r, wp, ctx, store)
  71 |              if wsrc is None:
  72 | @@ -539,19 +550,21 @@ def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store
  73 |              sources[key] = wsrc
  74 |          if why_w:
  75 |              report["window_passed_over"][vid] = why_w
  76 | -        if not windows:
  77 | +        report["window_refused"] += n_ref
  78 | +        if not windows and len(rs) > n_ref:          # rows that still wait (a video the word pass refused whole: none)
  79 |              why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
  80 |                                             ["no sentence-ready window record"]))
  81 | -            report["no_word_record"] += len(rs)
  82 | -            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
  83 | -            report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
  84 | -        else:
  85 | +            report["no_word_record"] += len(rs) - n_ref
  86 | +            report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs) - n_ref
  87 | +            report["no_word_record_videos"][vid] = {"rows": len(rs) - n_ref, "why": why}   # which (glm C3 P2-2)
  88 | +        elif windows:
  89 |              report["window_waiting"] += waiting      # rows of a window video with no window record of their own
  90 |      report["moments"], report["sources"] = len(moments), len(sources)
  91 |      report["videos"] = len({m["video_id"] for m in moments})
  92 |      log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} videos "
  93 |          f"({report['sources']} word records); {report['no_word_record']} rows wait for a word record, "
  94 | -        f"{report['window_waiting']} wait for their own window, {len(report['not_anchored'])} do not re-anchor, "
  95 | +        f"{report['window_waiting']} wait for their own window, {report['window_refused']} refused by the word pass "
  96 | +        f"(not sentence-ready or failed: never re-worked), {len(report['not_anchored'])} do not re-anchor, "
  97 |          f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
  98 |          f"{len(report['channel_conflict'])} video(s) name more than one channel, "
  99 |          f"{len(report['fallbacks'])} read from a fallback record; "
 100 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 101 | index f2290d0..c945ced 100644
 102 | --- a/pipeline/spotlight.py
 103 | +++ b/pipeline/spotlight.py
 104 | @@ -342,16 +342,18 @@ def source_test(evidence, layout):
 105 |      return True, f"layout '{lay}'; the captions' evidence: {evidence_text(evidence)}"
 106 |  
 107 |  
 108 | -def next_attempt(rows, word_pass, now, captions_for=None):
 109 | +def next_attempt(rows, word_pass, now, captions_for=None, refused=()):
 110 |      """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 111 |      could arrive. The NEWEST upload among the adapter's rows whose captions do not refuse it (RULING 92 AMENDED, 09:03
 112 |      Nov 14: unmarked, or marked with at least one speaker change; the layout decides per clip), its caption turns from
 113 |      pp-ingest's `episode` (mine-hook/2 rows), else episode_turns(): an episode marked with zero turns is the one
 114 | -    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 115 | -    waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 116 | +    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready, refused
 117 | +    (refused: word_pass_index's report["refused"], final: the worker never re-works them) or still waiting (no row yet)
 118 | +    (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 119 |      "newest_upload": {...} or None}."""
 120 |      from datetime import datetime, timedelta, timezone
 121 |      import package_pin as PPN
 122 | +    refused = set(refused or ())
 123 |      by_vid = {}
 124 |      for r in rows or ():
 125 |          if isinstance(r, dict) and r.get("video_id"):
 126 | @@ -370,13 +372,14 @@ def next_attempt(rows, word_pass, now, captions_for=None):
 127 |              k = f"{(r.get('mined') or {}).get('pass')}/{(r.get('mined') or {}).get('prompt_version')}"
 128 |              passes[k] = passes.get(k, 0) + 1
 129 |          ready = sum(1 for r in rs if (word_pass.get(r.get("moment_id")) or {}).get("sentence_ready"))
 130 | +        n_ref = sum(1 for r in rs if r.get("moment_id") in refused and r.get("moment_id") not in word_pass)
 131 |          exp = (datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) +
 132 |                 timedelta(hours=PPN.WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None
 133 |          age = E.age_hours(rs[0].get("published_at"), now)
 134 |          return {"video_id": vid, "channel": rs[0].get("channel_name"), "published_at": pub, "expires_at": exp,
 135 |                  "age_h": round(age, 1) if age is not None else None,
 136 |                  "turns_per_min": tpm, "unmarked": unmarked, "turns_from": frm, "rows": len(rs), "passes": passes,
 137 | -                "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 138 | +                "word_pass_ready": ready, "word_pass_refused": n_ref, "word_pass_waiting": len(rs) - ready - n_ref}
 139 |      sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 140 |      conv = [x for x in sts if x["unmarked"] or not (isinstance(x["turns_per_min"], (int, float)) and
 141 |                                                      x["turns_per_min"] <= 0)]       # only MARKED with zero turns is out
 142 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 143 | index 044385c..71d7f95 100644
 144 | --- a/tests/package/funnel.py
 145 | +++ b/tests/package/funnel.py
 146 | @@ -100,6 +100,8 @@ for why, n in (rep.get("no_word_record_why") or {}).items():
 147 |      s0 += [(f"SUPPLY: no word record yet ({why})", None)] * int(n)
 148 |  s0 += [("SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row)", None)] * \
 149 |      int(rep.get("window_waiting") or 0)
 150 | +s0 += [("refused by the word pass (its row is not sentence-ready or failed; never re-worked)", None)] * \
 151 | +    int(rep.get("window_refused") or 0)
 152 |  s0 += [("its window record failed a check", None)] * int(rep.get("window_failed") or 0)
 153 |  na = rep.get("not_anchored") or {}
 154 |  ws_rows = {}
 155 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 156 | index 0e36ebd..63860a3 100644
 157 | --- a/tests/package/proof_ledger.py
 158 | +++ b/tests/package/proof_ledger.py
 159 | @@ -403,9 +403,11 @@ def main(argv=None):
 160 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
 161 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
 162 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
 163 | -    say(f"  word pass: {json.dumps(wp_rep)}")
 164 | +    refused = wp_rep.get("refused") or []                # final: the worker never re-works them (the inputs keep ids)
 165 | +    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(refused)))}")
 166 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 167 | -                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 168 | +                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
 169 | +                                               word_pass_refused=refused)
 170 |      inputs["word_pass"] = wp_rep
 171 |      moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
 172 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 173 | @@ -505,7 +507,7 @@ def main(argv=None):
 174 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
 175 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
 176 |      try:                                                 # RULING 95: when the next qualifying episode could arrive
 177 | -        res["next_attempt"] = SPOT.next_attempt(rows, wp, now)
 178 | +        res["next_attempt"] = SPOT.next_attempt(rows, wp, now, refused=refused)
 179 |      except Exception as e:                               # noqa: BLE001  a report, never the build
 180 |          res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
 181 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 182 | @@ -569,7 +571,8 @@ def main(argv=None):
 183 |          say(f"  RULING 95: the newest conversation upload: {na.get('channel')} {na.get('video_id')} published "
 184 |              f"{na.get('published_at')} (expires {na.get('expires_at')}), {na.get('turns_per_min')} turns a minute, "
 185 |              f"rows {na.get('passes')}, word pass {na.get('word_pass_ready')} ready / {na.get('word_pass_waiting')} "
 186 | -            f"waiting" if na else "  RULING 95: no conversation upload in the window")
 187 | +            f"waiting / {na.get('word_pass_refused')} refused (never re-worked)" if na else
 188 | +            "  RULING 95: no conversation upload in the window")
 189 |          say(f"no spotlight ({sp.get('why_none')})" + "".join(
 190 |              f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
 191 |              f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
 192 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 193 | index cc9b1e8..9edb48f 100644
 194 | --- a/tests/package/test_ledger_build.py
 195 | +++ b/tests/package/test_ledger_build.py
 196 | @@ -462,6 +462,43 @@ class TestWindowRecords(unittest.TestCase):
 197 |              self.assertEqual(idx["C"]["record_sha256"], "s2")                       # the last row of a moment wins
 198 |              self.assertEqual((rep["failed"], rep["not_ready"], rep["ready"], rep["unreadable"]), (1, 1, 1, 1))
 199 |  
 200 | +    def test_the_refused_are_the_moments_whose_last_row_gives_no_window(self):
 201 | +        """The integrator, 09:37 ET Nov 15: the worker never re-works a moment it has a row for, so a moment whose last
 202 | +        row is failed, not sentence-ready or unreadable is refused for good, never waiting."""
 203 | +        with tempfile.TemporaryDirectory() as d:
 204 | +            p = os.path.join(d, "word_pass.jsonl")
 205 | +            self.assertEqual(LB.word_pass_index(p)[1]["refused"], [])               # no file yet: none refused
 206 | +            ok = {"window_record": "x", "record_sha256": "s", "sentence_ready": True}
 207 | +            boom = {"window_record": None, "record_sha256": None, "sentence_ready": False, "error": "boom"}
 208 | +            rows = [dict(ok, moment_id="R"), dict(boom, moment_id="F"),
 209 | +                    dict(ok, moment_id="N", sentence_ready=False), dict(ok, moment_id="U", record_sha256=None),
 210 | +                    dict(boom, moment_id="L"), dict(ok, moment_id="L"),                # the last row wins, both ways
 211 | +                    dict(ok, moment_id="T"), dict(ok, moment_id="T", sentence_ready=False)]
 212 | +            with open(p, "w") as f:
 213 | +                f.write("\n".join(json.dumps(r) for r in rows) + "\n")
 214 | +            idx, rep = LB.word_pass_index(p)
 215 | +            self.assertEqual((sorted(idx), rep["refused"]), (["L", "R"], ["F", "N", "T", "U"]))
 216 | +
 217 | +    def test_a_row_the_word_pass_refused_is_counted_apart_from_the_waiting(self):
 218 | +        ctx = E.Context(NOW, REG)
 219 | +        with tempfile.TemporaryDirectory() as d:
 220 | +            rel, wp, r, words = window_fixture(d)
 221 | +            mk = lambda mid, vid, t: dict(row("Bitcoin started as a quiet experiment.", start=t, end=t + 4.0, mid=mid,
 222 | +                                              vid=vid), transcript_sha256=r["transcript_sha256"])
 223 | +            rows = [r, mk("W2", "vidW", 100.0), mk("W3", "vidW", 200.0),      # vidW: W1 ready, W2 refused, W3 waits
 224 | +                    mk("X1", "vidX", 10.0), mk("X2", "vidX", 20.0),           # vidX: every row refused
 225 | +                    mk("Y1", "vidY", 10.0),                                    # vidY: no row yet
 226 | +                    mk("Z1", "vidZ", 10.0), mk("Z2", "vidZ", 20.0)]           # vidZ: no window; Z1 refused, Z2 waits
 227 | +            go = lambda **k: LB.build_inputs(rows, ctx, d, log=lambda s: None, word_pass={"W1": wp}, **k)
 228 | +            ms, _, rep = go(word_pass_refused=["W2", "X1", "X2", "Z1"])
 229 | +            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
 230 | +            self.assertEqual((rep["window_waiting"], rep["window_refused"], rep["no_word_record"]), (1, 4, 2))
 231 | +            self.assertEqual({v: x["rows"] for v, x in rep["no_word_record_videos"].items()},
 232 | +                             {"vidY": 1, "vidZ": 1})                             # vidX waits for nothing
 233 | +            self.assertEqual(sum(rep["no_word_record_why"].values()), 2)         # the why counts agree
 234 | +            _, _, old = go()                                                     # no refused ids given: as before
 235 | +            self.assertEqual((old["window_waiting"], old["window_refused"], old["no_word_record"]), (2, 0, 5))
 236 | +
 237 |      def test_a_window_record_is_used_only_when_every_claim_checks_out(self):
 238 |          ctx = E.Context(NOW, REG)
 239 |          with tempfile.TemporaryDirectory() as d:
 240 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 241 | index ce0eade..c1b3e31 100644
 242 | --- a/tests/package/test_ruling_107_guard.py
 243 | +++ b/tests/package/test_ruling_107_guard.py
 244 | @@ -161,7 +161,8 @@ class TestTheDriverAsksNoModel(Paths):
 245 |      PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 246 |                                                                                    "MOMENTS_PIN_LY.json")]
 247 |  
 248 | -    def run_driver(self, left):
 249 | +    def run_driver(self, left, wp_rep=None, seen=None):
 250 | +        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments."""
 251 |          proof = os.path.join(self.tmp.name, "drv", "proof")
 252 |          os.makedirs(proof)
 253 |          delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
 254 | @@ -177,12 +178,16 @@ class TestTheDriverAsksNoModel(Paths):
 255 |  
 256 |          def no_router(*a, **k):
 257 |              raise Built("a router was built")
 258 | +
 259 | +        def inputs(*a, **k):
 260 | +            (seen if seen is not None else {}).update(k)
 261 | +            return copy.deepcopy(POOL), {}, {}
 262 |          stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
 263 |                   mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
 264 |                   mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
 265 |                   mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
 266 | -                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"rows": 0})),
 267 | -                 mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: (copy.deepcopy(POOL), {}, {})),
 268 | +                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, dict(wp_rep or {"rows": 0}))),
 269 | +                 mock.patch.object(PLG.LB, "build_inputs", inputs),
 270 |                   mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
 271 |                   mock.patch.object(PLG, "build_router", no_router),
 272 |                   mock.patch("sys.stdout", new=io.StringIO())]
 273 | @@ -208,6 +213,16 @@ class TestTheDriverAsksNoModel(Paths):
 274 |          self.assertIn("NOTHING NEW (ruling 107 (1))", open(os.path.join(runs[0], "package.log")).read())
 275 |          self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.FINGERPRINT)))   # a skip never stands for a build
 276 |  
 277 | +    def test_the_word_pass_refused_reach_the_inputs_and_the_log_gives_their_count(self):
 278 | +        seen = {}
 279 | +        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, seen=seen)
 280 | +        self.assertEqual((rc, seen.get("word_pass_refused")), (0, ["Xa1", "Yb2"]))
 281 | +        log = open(os.path.join(runs[0], "package.log")).read()
 282 | +        self.assertIn('"refused": 2', log)                                   # the count; the ids stay in inputs.json
 283 | +        self.assertNotIn("Xa1", log)
 284 | +        self.assertEqual(json.load(open(os.path.join(runs[0], "inputs.json")))["inputs"]["word_pass"]["refused"],
 285 | +                         ["Xa1", "Yb2"])
 286 | +
 287 |      def test_work_left_undone_goes_on_to_the_router(self):
 288 |          rc, runs = self.run_driver(left=1)
 289 |          self.assertEqual(rc, "router")
 290 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 291 | index c99d420..64517b8 100644
 292 | --- a/tests/package/test_spotlight.py
 293 | +++ b/tests/package/test_spotlight.py
 294 | @@ -538,6 +538,17 @@ class TestRuling94And95(unittest.TestCase):
 295 |          self.assertIn("ruling 94 (a): the trimmed cut is not clean: it bleeds", out["moments"]["a~trim"]["out"])
 296 |          self.assertNotIn("package_for", calls)
 297 |  
 298 | +    def test_ruling_95_a_moment_the_word_pass_refused_is_not_waiting(self):
 299 | +        rows = [{"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 300 | +                 "moment_id": m, "episode": {"turns_per_min": 1.5}, "mined": {"pass": "moment",
 301 | +                                                                             "prompt_version": "mine/2"}}
 302 | +                for m in ("m1", "m2", "m3")]
 303 | +        c = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW, refused=["m2", "zz"])["conversation"]
 304 | +        self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_refused"], c["word_pass_waiting"]),
 305 | +                         (3, 1, 1, 1))                                       # zz is no row of this upload
 306 | +        c = SPOT.next_attempt(rows, {"m1": {"sentence_ready": True}}, NOW)["conversation"]   # none named: as before
 307 | +        self.assertEqual((c["word_pass_refused"], c["word_pass_waiting"]), (0, 2))
 308 | +
 309 |      def test_ruling_95_the_newest_conversation_upload_and_its_mining_state(self):
 310 |          rows = [{"video_id": "old", "channel_name": "Talk", "published_at": "2026-11-13T18:00:00+00:00",
 311 |                   "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 312 | 
```

---

pp-selectid: THE WORD PASS'S REFUSED MOMENTS, COUNTED APART FROM THE WAITING. Reporting only: no gate, verdict or
selection changes; no moment enters or leaves a build because of this change.

THE FINDING (the integrator, 09:37 ET Nov 15). The word-pass worker never works a moment again once it has a row
(ready, not ready or failed: its passed_ids). ledger_build.word_pass_index returns only the sentence-ready rows, so
build_inputs counted a moment whose row is NOT sentence-ready the same as a moment with no row yet: "N wait for their
own window" (pipeline/ledger_build.py:504-509 and :549 in the base). This morning two builds said "4 wait for their own
window" for 4 Scott Melker moments the word pass had refused at 09:05, and my STATE line said the watcher would build
"when they land": they never will. spotlight.next_attempt (ruling 95, pipeline/spotlight.py:345) counted them "waiting"
the same way.

THE CHANGE:
1. word_pass_index: report["refused"] = the sorted moment ids whose LAST row gives no window record (failed, not
   sentence-ready, or unreadable): set(last) - set(out). Its index and its other counts are unchanged. A line that is
   not JSON or has no moment_id is attributable to no moment, so it refuses none (as before, it is counted unreadable).
2. build_inputs(..., word_pass_refused=()): a row with no sentence-ready window record of its own is counted
   "window_refused" when its moment is in word_pass_refused, else exactly as before: "window_waiting" in a video that
   has windows, "no_word_record" (with its why and per-video rows) in a video that has none. A video whose rows are ALL
   refused gets no no_word_record entry: it waits for nothing. The log line gives the refused count. With no refused
   ids given, every count is as before (tested).
3. spotlight.next_attempt(..., refused=()): "word_pass_refused" apart; "word_pass_waiting" = rows - ready - refused.
4. tests/package/proof_ledger.py: passes the report's refused ids to build_inputs and to next_attempt; logs the
   word-pass report with the refused COUNT (the ids stay in inputs.json); ruling 95's line reads
   "ready / waiting / refused".
5. tests/package/funnel.py (a report script over a build's inputs.json): one supply line for the refused.

TESTS:
- test_ledger_build: the index's refused set (the last row decides, both ways), and build_inputs' counts over four
  videos (windows with one refused and one waiting row; all rows refused; no row yet; no window with one refused and
  one waiting row), then the same rows with no refused ids: as before.
- test_spotlight: ruling 95's counts.
- test_ruling_107_guard: the driver passes the ids to build_inputs and logs only their count. Its harness gains two
  optional arguments; the existing tests call it as before.
MUTATIONS: 12 of 14 killed, after a control run (the unmutated copy passes all 93 tests). The 2 that survive:
- the driver's ruling-95 call without refused=: no test reaches the driver past its router (the existing harness stops
  there);
- the funnel script's line: no test runs funnel.py.
SUITES: tests/package, moments, select_by_id and providers: 684 pass.

PLEASE CHECK: (1) that the refused set is exactly what the worker will never re-work (the last row decides, as
word_pass_index's own classification does); (2) that no row can be counted twice (refused and waiting, or refused and
ready), and that every count is as before when no ids are given; (3) the no-window branch: no_word_record, its why
counts and its per-video rows; (4) the driver's wiring, and that the log carries counts, not ids; (5) whether either
surviving mutation matters.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
