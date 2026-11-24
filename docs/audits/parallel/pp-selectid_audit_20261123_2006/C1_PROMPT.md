# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261123_2006
# Branch: pp-selectid
# Generated: 2026-11-23 20:12 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261123_2006/C1_STEP.diff (332 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index cca269f..4ff7387 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -59,8 +59,10 @@ FILLERS = frozenset(("um", "uh", "er", "ah", "mm", "hmm"))
   6 |  
   7 |  
   8 |  def critical(tok, texts):
   9 | -    """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  10 | -    capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  11 | +    """Law L-v 2 / ruling 143 (1)'s MATERIAL word as the render tests it (pinned._lv2_critical): a number, a negation,
  12 | +    a name (in either text, a capitalised word that does not open a sentence; 'I' excepted) or a ticker (in either
  13 | +    text, a word of two or more capitals, wherever it stands: 'IBIT'; the integrator's batch 113). A doubtful token is
  14 | +    critical."""
  15 |      if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
  16 |          return True
  17 |      for t in texts:
  18 | @@ -68,7 +70,7 @@ def critical(tok, texts):
  19 |              w = m.group(0)
  20 |              if w.lower() == tok and w[0].isupper() and w != "I":
  21 |                  before = t[:m.start()].rstrip()
  22 | -                if before and before[-1] not in ".!?":
  23 | +                if (before and before[-1] not in ".!?") or (len(w) >= 2 and w.isupper()):
  24 |                      return True
  25 |      return False
  26 |  
  27 | @@ -279,6 +281,111 @@ def class_131(spoken, approved, adj):
  28 |      return out
  29 |  
  30 |  
  31 | +RULE_143 = "ruling 143"
  32 | +AUDIO_SHARE_MIN = 0.85     # RULING 143 (4), pinned.AUDIO_SHARE_MIN: two audio readings sharing less are the wrong audio
  33 | +AUDIO_APART_MIN = 3        # ... and only when more than this many of the run decode's words are missing (pinned's)
  34 | +
  35 | +
  36 | +def audio_share(x, y):
  37 | +    """RULING 143 (4) as pinned.audio_share: the share of the run decode's tokens x the second reading y heard, in
  38 | +    order (matched / len(x)); y's extra words (repeats, false starts, the window's spill) never lower it."""
  39 | +    x, y = list(x or []), list(y or [])
  40 | +    if not x or not y:
  41 | +        return 0.0
  42 | +    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / len(x)
  43 | +
  44 | +
  45 | +def wrong_audio(x, y):
  46 | +    """RULING 143 (4) as pinned.wrong_audio: the share when under AUDIO_SHARE_MIN AND more than AUDIO_APART_MIN of the
  47 | +    run decode's tokens are missing (HARD), else None (the same audio)."""
  48 | +    share = audio_share(x, y)
  49 | +    apart = len(list(x or [])) - round(share * len(list(x or [])))
  50 | +    return share if share < AUDIO_SHARE_MIN and apart > AUDIO_APART_MIN else None
  51 | +
  52 | +
  53 | +def material_pair(x, y, texts):
  54 | +    """RULING 143 (1) as pinned.material_pair: a differing pair is MATERIAL when either side holds a number, a negation,
  55 | +    a name, a ticker or an amount (critical); a word-form pair (ruling 142 (2)) is not."""
  56 | +    return not canon.word_form(x, y) and any(critical(t, texts) for t in list(x) + list(y))
  57 | +
  58 | +
  59 | +def class_143(spoken, approved, adj):
  60 | +    """RULING 143 (orchestrator 2026-11-17 '15:55'; landed by ruling 153, 20:03 ET Nov 23): this side's own re-check of
  61 | +    the render lock's settlement, from its record (the pre-check entry's "adjudication": "run_decode", "approved",
  62 | +    "second_recogniser", "pairs"), never from the record's own classes. Each step is pinned.adjudicate_lock's, re-run on
  63 | +    the recorded readings:
  64 | +    1. The ruling-17 diff (canon tokens of the run decode against the approved text); a currency pair (ruling 131 (B))
  65 | +       and a spelling-only pair (ruling 135) are no difference.
  66 | +    2. HARD (4): the run decode and the second recogniser (its fillers dropped, ruling 135 (d)) sharing under
  67 | +       AUDIO_SHARE_MIN of the run's words, more than AUDIO_APART_MIN apart: the wrong audio.
  68 | +    3. Per pair (reads: the render's test of the second reading there): a MATERIAL pair (material_pair) takes the run
  69 | +       decode's reading only when the second recogniser reads it too (the two audio readings agree: the transcript is
  70 | +       corrected), else it holds; a NON-MATERIAL pair never holds: the approved reading where the second recogniser
  71 | +       reads it, else the run decode's.
  72 | +    4. The record's pairs must be exactly these, in order (the same words, materiality and reading taken); the render's
  73 | +       fallback (the settled words cannot be written into the approved text: the run decode's text, every pair
  74 | +       'run') is accepted only with every pair settled and the spoken text the run decode's.
  75 | +    5. The spoken text's canon tokens are the settled reading (the approved tokens, each run-taken pair as the run's).
  76 | +    -> [{"spoken", "approved", "material", "class", "took", "edge_distance"} (+ "why" when it holds)]; a class None
  77 | +    holds."""
  78 | +    def held(why, **kw):
  79 | +        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None, "material": None}, **kw,
  80 | +                    **{"class": None}, why=why)
  81 | +    adj = adj if isinstance(adj, dict) else {}
  82 | +    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
  83 | +    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
  84 | +            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
  85 | +        return [held("the lock record does not hold the three readings of this segment's approved text")]
  86 | +    texts = (run_t, pin_t, sec_t)
  87 | +    r, p, ops = diff(run_t, pin_t)
  88 | +    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]
  89 | +    share = wrong_audio(r, s)
  90 | +    if share is not None:
  91 | +        return [held(f"the run decode and the second recogniser share {share:.0%} of their words: the wrong audio "
  92 | +                     f"(ruling 143 (4))")]
  93 | +    out, took_run = [], set()
  94 | +    for op in ops:
  95 | +        _tag, a, b, c, d = op
  96 | +        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "edge_distance": None}
  97 | +        if currency_pair(r, p, op):
  98 | +            out.append(dict(row, took="currency", material=None, **{"class": "currency format (ruling 131 (B))"}))
  99 | +            continue
 100 | +        if canon.same_words(r[a:b], p[c:d]):
 101 | +            out.append(dict(row, took="spelling", material=None, **{"class": "spelling only (ruling 135)"}))
 102 | +            continue
 103 | +        material = material_pair(r[a:b], p[c:d], texts)
 104 | +        pin_ok, run_ok = reads(p, s, c, d), reads(r, s, a, b)
 105 | +        if material and run_ok:
 106 | +            out.append(dict(row, took="run", material=True, **{"class": "ruling 143 (3): the two audio readings "
 107 | +                                                                         "agree: the transcript corrected"}))
 108 | +        elif material:
 109 | +            out.append(dict(row, took=None, material=True, **{"class": None},
 110 | +                            why="a material word (a number, a negation, a name, a ticker or an amount) on which the "
 111 | +                                "two audio readings disagree (ruling 143 (3))"))
 112 | +        else:
 113 | +            out.append(dict(row, took="approved" if pin_ok else "run", material=False, **{"class": (
 114 | +                "ruling 143 (2): a small word, the approved reading the second recogniser reads" if pin_ok else
 115 | +                "ruling 143 (2): a small word, never a hold: the run decode's reading")}))
 116 | +        if out[-1]["took"] == "run":
 117 | +            took_run.add((a, c))
 118 | +    merged = []
 119 | +    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
 120 | +        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
 121 | +    rec = adj.get("pairs")
 122 | +    theirs = [(x.get("run"), x.get("approved"), x.get("material"), x.get("took")) for x in rec] \
 123 | +        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
 124 | +    mine = [(x["spoken"], x["approved"], x["material"], x["took"]) for x in out if x["took"] not in ("currency",
 125 | +                                                                                                    "spelling")]
 126 | +    sp = canon.canon_tokens(spoken)
 127 | +    fallback = (theirs is not None and len(theirs) == len(mine) and all(t[3] == "run" for t in theirs) and
 128 | +                [t[:3] for t in theirs] == [m[:3] for m in mine] and all(m[3] is not None for m in mine) and sp == r)
 129 | +    if theirs != mine and not fallback:
 130 | +        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
 131 | +    if sp != merged and not fallback:
 132 | +        out.append(held("the spoken text is not the settled reading (ruling 143 seals the settled reading only)"))
 133 | +    return out
 134 | +
 135 | +
 136 |  def reads(x, s, lo, hi):
 137 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
 138 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
 139 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 140 | index aae6ba7..f18e406 100644
 141 | --- a/pipeline/lock_precheck.py
 142 | +++ b/pipeline/lock_precheck.py
 143 | @@ -50,7 +50,9 @@ import attest as AT
 144 |  import canon as C
 145 |  
 146 |  RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
 147 | -         "ruling 142 + ruling 146")             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
 148 | +         "ruling 139 + ruling 142 + ruling 143 + ruling 146")   # RULING 153 (20:03 ET Nov 23): rulings 139 and 143
 149 | +#   join the integrator's string (its lockstep message of 20:1x ET Nov 23, branch r143-material 36896978e)
 150 | +             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
 151 |  #   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
 152 |  #   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
 153 |  #   RULING 131
 154 | @@ -61,7 +63,7 @@ RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 10
 155 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
 156 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
 157 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 158 | -DECODER = "50fa01b400bd"                      # side): the render's own cut placement joins the pre-check (a passing
 159 | +DECODER = "9326604699a7"                      # side): the render's own cut placement joins the pre-check (a passing
 160 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
 161 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
 162 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
 163 | @@ -83,6 +85,10 @@ DECODER = "50fa01b400bd"                      # side): the render's own cut plac
 164 |  #   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
 165 |  #   RULING 146 (2), the integrator's batch 114 (sentence_law.lock_cut: a hook lead under 80 ms FLAGS, never holds;
 166 |  #   branch r146-g17a 90aa0486; sentence_law.py byte-identical): 50fa01b400bd4231e38a9a8b77f6a0df6f16a57d6f0e22de0eb376788f039256
 167 | +#   RULING 153 (orchestrator 20:03 ET Nov 23): the integrator's batches 113 (ruling 143, the material-words lock), 116
 168 | +#   (ruling 139 on the render lock), the ruling-145 allowance (gpu0.py) and 119 (post_live; no decoder file), ONE
 169 | +#   lockstep (branch r143-material 36896978e; pinned.py, sentence_law.py and gpu0.py byte-identical):
 170 | +#   9326604699a7756c18d887cd09bdb280f74d9c732bfb0e1235e4a9f3095850c9
 171 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
 172 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
 173 |                          "lock_requests")      # this worktree's; the service only reads it
 174 | @@ -185,6 +191,20 @@ def decide(seg, e):
 175 |      if not isinstance(spoken, str) or not spoken.strip():
 176 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 177 |      adj = e.get("adjudication")
 178 | +    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_143):   # RULING 143: the settlement
 179 | +        diffs = AT.class_143(spoken, approved, adj)
 180 | +        bad = [x for x in diffs if x["class"] is None]
 181 | +        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
 182 | +            return {"verdict": "hold", "outcome": out, "differences": diffs,
 183 | +                    "why": "adopt_spoken under ruling 143, but by this side's attest.class_143 it holds: " +
 184 | +                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
 185 | +        if not any(x["took"] == "run" for x in diffs):  # no pair took the run decode's reading: the approved text stands
 186 | +            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 143 with no pair taking the "
 187 | +                                                              "run decode's reading: the approved text stands"}
 188 | +        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
 189 | +                "adoption": AT.RULE_143,
 190 | +                "transcript_corrected": [[x["approved"], x["spoken"]] for x in diffs if x.get("material") and
 191 | +                                         x["took"] == "run"]}
 192 |      if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_131):   # RULING 131 (A): two of three
 193 |          diffs = AT.class_131(spoken, approved, adj)
 194 |          bad = [x for x in diffs if x["class"] is None]
 195 | @@ -304,7 +324,16 @@ def relisten_of(e):
 196 |  def attested(row, run_rule=None):
 197 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it:
 198 |      ruling 84's class, or ruling 131 (A)'s two of three readings (row["adoption"])."""
 199 | -    if row.get("adoption") == AT.RULE_131:
 200 | +    if row.get("adoption") == AT.RULE_143:
 201 | +        rule = run_rule or ("ruling 143 (orchestrator 2026-11-17 '15:55', landed by ruling 153): adopt_spoken, the "
 202 | +                            "render lock's settlement")
 203 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed material word "
 204 | +                   "(a number, a negation, a name, a ticker or an amount) is the reading the two audio readings agree "
 205 | +                   "on (the run decode and the second recogniser; the transcript corrected from the audio), each small "
 206 | +                   "word the approved reading the second recogniser reads or the run decode's, re-checked on this side "
 207 | +                   "from the lock's record; no line quotes the changed words (marked on the release: 'transcript "
 208 | +                   "corrected from the audio' where a material word changed)")
 209 | +    elif row.get("adoption") == AT.RULE_131:
 210 |          rule = run_rule or "ruling 72 + ruling 131 (A) (08:25 ET Nov 17): adopt_spoken, two of the three readings agree"
 211 |          carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed pair is the "
 212 |                     "reading two of the three readings (the approved text, the render's run decode, the second "
 213 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 214 | index a70ed0c..8a5f929 100644
 215 | --- a/tests/package/test_lock_precheck.py
 216 | +++ b/tests/package/test_lock_precheck.py
 217 | @@ -60,7 +60,7 @@ class TestRequest(Dirs):
 218 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 219 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 220 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 221 | -                         "DcUbBkyeh9M.216.054-228.674.50fa01b400bd.json")             # batch 114's decoder
 222 | +                         "DcUbBkyeh9M.216.054-228.674.9326604699a7.json")             # ruling 153's lockstep
 223 |  
 224 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 225 |          segs = LP.segments_of([HOOK, CLIP])
 226 | @@ -138,7 +138,7 @@ class TestRuling84(unittest.TestCase):
 227 |          """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
 228 |          RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
 229 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 230 | -                                   "ruling 131 + ruling 135 + ruling 142 + ruling 146")
 231 | +                                   "ruling 131 + ruling 135 + ruling 139 + ruling 142 + ruling 143 + ruling 146")
 232 |  
 233 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 234 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 235 | @@ -627,3 +627,96 @@ class TestApply(Dirs):
 236 |  
 237 |  if __name__ == "__main__":
 238 |      unittest.main()
 239 | +
 240 | +
 241 | +class TestRuling143(Dirs):
 242 | +    """RULING 143 (orchestrator 2026-11-17 '15:55'), landed by RULING 153 (20:03 ET Nov 23) in ONE lockstep with the
 243 | +    integrator's batch 113: when the TWO AUDIO readings (the run decode and the second recogniser) agree with each other
 244 | +    on a material word, the sealed text takes the audio's reading (the transcript is corrected); only when they disagree
 245 | +    does it hold; a small word never holds; the wrong audio (under 85 % shared) holds. This side re-derives every pair
 246 | +    (attest.class_143) and never trusts the record. The case: the FTX-bottom story's Simply Bitcoin 190beaa7
 247 | +    (0shaXx_n870 words 0-30), held at 19:54 on 'fdx' / 'ftx' (the transcript's 'FDX', both audio readings 'FTX')."""
 248 | +    APPROVED = ("On Saturday at 1 in the morning, Bitcoin got flushed down to $55,000. That was four years to the day "
 249 | +                "after the FDX bottom.")
 250 | +    RUN = APPROVED.replace("FDX", "FTX")
 251 | +    SB = {"moment_id": "190beaa7", "video_id": "0shaXx_n870", "start": 0.0, "end": 9.76, "text": APPROVED}
 252 | +
 253 | +    def adj(self, run=None, app=None, sec=None, **kw):
 254 | +        run, app = run or self.RUN, app or self.APPROVED
 255 | +        sec = run if sec is None else sec
 256 | +        r, p, ops = AT.diff(run, app)
 257 | +        pairs = [{"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "material": True, "second_reads": "run",
 258 | +                  "took": "run"} for _, a, b, c, d in ops]
 259 | +        return dict({"rule": "ruling 143 (orchestrator 2026-11-17 '15:55')", "verdict": "settled", "pairs": pairs,
 260 | +                     "run_decode": run, "approved": app, "second_recogniser": sec}, **kw)
 261 | +
 262 | +    def decide(self, spoken=None, seg=None, **kw):
 263 | +        s = LP.segments_of([seg or self.SB])[0]
 264 | +        return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken or self.RUN, adjudication=self.adj(**kw)))
 265 | +
 266 | +    def test_the_two_audio_readings_correct_the_transcript_and_the_pin_says_so(self):
 267 | +        d = self.decide()
 268 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 269 | +        self.assertEqual(d["transcript_corrected"], [["fdx", "ftx"]])
 270 | +        s = LP.segments_of([self.SB])[0]
 271 | +        self.put(s, entry(s, "adopt_spoken", spoken_text=self.RUN, adjudication=self.adj()))
 272 | +        pre = LP.check([self.SB], "r", self.req, self.res, log=lambda m: None)
 273 | +        pk = LP.apply({"segments": [{k: self.SB[k] for k in ("video_id", "start", "end", "text")}], "lines": []}, pre)
 274 | +        seg = pk["segments"][0]
 275 | +        self.assertEqual((seg["text"], seg["attested"]["was"]), (self.RUN, self.APPROVED))
 276 | +        self.assertIn("ruling 143", seg["attested"]["rule"])
 277 | +        self.assertIn("transcript corrected from the audio", seg["attested"]["carried"])
 278 | +        self.assertEqual(LP.pin_problems(pk), [])
 279 | +
 280 | +    def test_a_number_and_a_ticker_are_settled_the_same_way(self):
 281 | +        for app, run in (("Bitcoin bottomed at about 15,000,500 dollars on November 21st of 2022, a deep low.",
 282 | +                          "Bitcoin bottomed at about 15,500 dollars on November 21st of 2022, a deep low."),
 283 | +                         ("IBIT saw its largest outflow since the launch in January of last year, the data shows.",
 284 | +                          "IBTC saw its largest outflow since the launch in January of last year, the data shows.")):
 285 | +            #   a sentence-opening ticker: only the ticker rule makes it material (the integrator's batch 113)
 286 | +            d = self.decide(spoken=run, seg=dict(self.SB, text=app), run=run, app=app)
 287 | +            self.assertEqual(d["verdict"], "adopt", (app, d.get("why")))
 288 | +            self.assertTrue(d["transcript_corrected"], app)
 289 | +            self.assertTrue(all(x["material"] for x in d["differences"]), app)
 290 | +
 291 | +    def test_a_small_word_never_holds(self):
 292 | +        app = "That was four years to the day after the bottom, and nobody saw it coming at all this time."
 293 | +        run, sec = app.replace(", and nobody", ", but nobody"), app.replace(", and nobody", ", so nobody")
 294 | +        r, p, ops = AT.diff(run, app)
 295 | +        pairs = [{"run": "but", "approved": "and", "material": False, "second_reads": "neither", "took": "run"}]
 296 | +        d = self.decide(spoken=run, seg=dict(self.SB, text=app), run=run, app=app, sec=sec, pairs=pairs)
 297 | +        self.assertEqual((d["verdict"], [(x["took"], x["material"]) for x in d["differences"]]),
 298 | +                         ("adopt", [("run", False)]), d.get("why"))
 299 | +        d = self.decide(spoken=app, seg=dict(self.SB, text=app), run=run, app=app, sec=app,
 300 | +                        pairs=[dict(pairs[0], second_reads="approved", took="approved")])
 301 | +        self.assertEqual(d["verdict"], "pass", d.get("why"))              # the second reads 'and': the approved stands
 302 | +
 303 | +    def test_what_holds(self):
 304 | +        other = ("Gold and the stock market both rallied on Friday while the dollar slid against the yen and the "
 305 | +                 "euro after the jobs report.")
 306 | +        for spoken, kw, why in (
 307 | +                (None, {"sec": APPROVED_SB_FDX}, "the two audio readings disagree"),          # the second reads 'FDX'
 308 | +                (None, {"sec": other}, "the wrong audio (ruling 143 (4))"),
 309 | +                (None, {"pairs": [{"run": "ftx", "approved": "fdx", "material": True, "took": "approved"}]},
 310 | +                 "the lock record's pairs are not this side's"),
 311 | +                (None, {"pairs": []}, "the lock record's pairs are not this side's"),
 312 | +                (APPROVED_SB_FDX.replace("four years", "five years"), {}, "the spoken text is not the settled reading"),
 313 | +                (None, {"second_recogniser": None}, "does not hold the three readings")):
 314 | +            d = self.decide(spoken, **kw)
 315 | +            self.assertEqual(d["verdict"], "hold", (spoken, kw))
 316 | +            self.assertIn(why, d["why"])
 317 | +
 318 | +    def test_only_a_ruling_143_record_goes_to_class_143(self):
 319 | +        d = self.decide(rule="ruling 131 (A) (orchestrator 2026-11-17 '08:25')")     # a 131 record: class_131 decides
 320 | +        self.assertNotEqual(d.get("adoption"), AT.RULE_143)
 321 | +
 322 | +    def test_the_old_decoders_answers_are_never_read(self):
 323 | +        s = LP.segments_of([self.SB])[0]
 324 | +        name = os.path.basename(LP.result_file(s, self.res)).replace(LP.DECODER, "50fa01b400bd")
 325 | +        with open(os.path.join(self.res, name), "w") as f:
 326 | +            json.dump([entry(s, "no_difference")], f)
 327 | +        self.assertIsNone(LP.answer(s, self.res))                       # batch 114's decoder: never read again
 328 | +
 329 | +
 330 | +APPROVED_SB_FDX = TestRuling143.APPROVED
 331 | +
 332 | 
```

---

pp-selectid: RULING 143's MIRROR on the builder's side (orchestrator ruling 153, 20:03 ET Nov 23: "RULING 143 LANDS
NOW ... when the TWO AUDIO READINGS agree with each other, the sealed text takes the audio's reading and the
transcript is corrected; only when the two audio readings DISAGREE on a material word does it hold"), in ONE decoder
lockstep with the integrator's batch 113 (pinned.adjudicate_lock under ruling 143: branch r143-material 36896978e).
pinned.py, sentence_law.py and gpu0.py are copied byte-identical (not part of this review).
THE CHANGE (pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py):
- attest.critical (attest.py:61): the render's _lv2_critical now also takes a TICKER (a word of two or more capitals,
  wherever it stands, a sentence opener included).
- attest.audio_share / wrong_audio / material_pair (attest.py:~290-310): pinned's, re-implemented: share = matched run
  tokens / len(run); wrong audio = share < 0.85 AND more than 3 run tokens missing; material = not canon.word_form and
  any critical token.
- attest.class_143 (attest.py:312): this side's re-check of a settlement from the lock record (run_decode, approved,
  second_recogniser, pairs), never from the record's classes: the ruling-17 diff (unchanged attest.diff, :78); currency
  (unchanged currency_pair, :155) and spelling pairs are no difference; the wrong audio holds; per pair (unchanged
  attest.reads, :389, pinned's test): material -> the run's reading only when the second recogniser reads it, else
  HOLD; small -> the approved reading when the second reads it, else the run's (never a hold); the record's pairs
  must equal this side's (words, materiality, reading taken), or the render's fallback (every pair 'run', the spoken
  text the run decode's); the spoken text must be the settled reading.
- lock_precheck.decide (lock_precheck.py:172, branch :194): an adopt_spoken whose adjudication rule starts
  "ruling 143" goes to class_143: any class None holds; no run-taken pair = pass (the approved text stands); else
  adopt with transcript_corrected = the material pairs taken from the audio. attested (:324): the sealed record's rule
  and carried text for a 143 adoption. RULES gains rulings 139 and 143; DECODER 9326604699a7 (the integrator's).
TESTS (TestRuling143): the FTX-bottom case ('FDX' in the transcript, both audio readings 'FTX') adopts, is sealed by
apply with its attested record, pin_problems none; a number format and a sentence-opening ticker settle the same
way; a small word never holds; holds: the second reads 'FDX', the wrong audio, a record that lies, an empty record,
a spoken text that is not the settled reading, a record without the readings; a 131 record is not class_143's; an
answer under the old decoder is never read. Mutations 9 of 9 killed.
PLEASE CHECK: (1) can a material word the two AUDIO readings disagree on reach a sealed text? (2) can a record that
lies (pairs, readings, spoken text) pass? (3) does class_143 match pinned.adjudicate_lock's ruling 143 (incl. the
fallback when the settled words cannot be written into the approved text)? (4) is the ticker rule the render's?



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
