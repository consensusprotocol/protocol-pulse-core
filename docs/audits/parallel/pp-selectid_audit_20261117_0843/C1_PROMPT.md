# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261117_0843
# Branch: pp-selectid
# Generated: 2026-11-17 08:43 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261117_0843/C1_STEP.diff (417 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index f45e4d5..4d57353 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -13,7 +13,13 @@ critical() is the render's _lv2_critical with its lists. CPU only, no model call
   6 |  (package_pin, which the integrator's check imports, must never pull it in).
   7 |  
   8 |  RULING 84 (orchestrator 20:41 Nov 13) has its own class, class_84, for the render's lock pre-check only (the
   9 | -second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged."""
  10 | +second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged.
  11 | +
  12 | +RULING 131 (orchestrator 08:25 ET Nov 17) has its own re-check, class_131: (A) per differing pair of the render's lock,
  13 | +two of the three readings (the approved text, the run's decode, the second recogniser) decide it and the sealed text
  14 | +takes that reading, at least 3 tokens from both cut edges; never a number, a name or a negation; all three different
  15 | +holds. (B) a currency symbol is formatting (canon.dollars_after_number, G18's one tolerance). It re-runs the render's own
  16 | +steps on the three readings the lock records and never trusts the record's own classes."""
  17 |  import re
  18 |  from difflib import SequenceMatcher
  19 |  
  20 | @@ -118,6 +124,118 @@ def class_84(spoken, approved):
  21 |      return out
  22 |  
  23 |  
  24 | +# RULING 131 (orchestrator 08:25 ET Nov 17): the render's lock records a two-of-three adjudication under this rule (the
  25 | +# integrator's message of 08:2x Nov 17: lock["adjudication"]["rule"] "ruling 131 (A) (orchestrator 2026-11-17
  26 | +# '08:25')"); a pair takes the run's reading only at EDGE_131 words or more from both ends of the span
  27 | +RULE_131 = "ruling 131 (A)"
  28 | +EDGE_131 = 3                                    # pinned.MAJORITY_EDGE
  29 | +
  30 | +
  31 | +def currency_pair(r, p, op):
  32 | +    """RULING 131 (B), the render's own test (pinned.adjudicate_lock): every token on both sides of the pair is a
  33 | +    'dollars' right after a number (canon.dollars_after_number: '$2 billion' is a spoken '2 billion')."""
  34 | +    _tag, a, b, c, d = op
  35 | +    return all(canon.dollars_after_number(r, i) for i in range(a, b)) and \
  36 | +        all(canon.dollars_after_number(p, j) for j in range(c, d))
  37 | +
  38 | +
  39 | +def edge_distance(r, p, op):
  40 | +    """RULING 131 (A), as the render's lock measures it (the integrator's message of 08:4x Nov 17): min(a, len(r) - b)
  41 | +    in the run decode's canon tokens r. A pair with an empty side ("delete" or "insert") inside a repetition may slide,
  42 | +    since both texts stay the same ("that's why that's why": difflib may put the extra copy on either): shift -n while
  43 | +    n <= the equal run before it and seq[x - n] == seq[y - n], +n while n <= the equal run after it and
  44 | +    seq[x + n - 1] == seq[y + n - 1] (seq, x, y = r, a, b for a delete; p, c, d for an insert); its distance is the
  45 | +    largest over the shifts (0 included). A replace never slides."""
  46 | +    tag, a, b, c, d = op
  47 | +    shifts = [0]
  48 | +    full = SequenceMatcher(None, r, p, autojunk=False).get_opcodes()
  49 | +    if tag in ("delete", "insert") and tuple(op) in full:
  50 | +        k = full.index(tuple(op))
  51 | +        seq, x, y = (r, a, b) if tag == "delete" else (p, c, d)
  52 | +        left = full[k - 1][2] - full[k - 1][1] if k > 0 and full[k - 1][0] == "equal" else 0
  53 | +        right = full[k + 1][2] - full[k + 1][1] if k + 1 < len(full) and full[k + 1][0] == "equal" else 0
  54 | +        n = 1
  55 | +        while n <= left and seq[x - n] == seq[y - n]:
  56 | +            shifts.append(-n)
  57 | +            n += 1
  58 | +        n = 1
  59 | +        while n <= right and seq[x + n - 1] == seq[y + n - 1]:
  60 | +            shifts.append(n)
  61 | +            n += 1
  62 | +    return max(min(a + n, len(r) - (b + n)) for n in shifts)
  63 | +
  64 | +
  65 | +def class_131(spoken, approved, adj):
  66 | +    """RULING 131 (A) and (B) (orchestrator 08:25 ET Nov 17): this side's own re-check of an adoption, from the render's
  67 | +    lock record (the pre-check entry's "adjudication": the FIRST lock's "run_decode", "approved", "second_recogniser",
  68 | +    "pairs"), never from the record's own classes. spoken: the entry's spoken text; approved: the segment's approved
  69 | +    text. Each step is the render's own (pinned.adjudicate_lock), re-run on the recorded readings:
  70 | +    1. The ruling-17 diff (diff: canon tokens of the run's decode against the approved text). (B) first: a currency
  71 | +       pair (currency_pair) is no difference and keeps the approved words.
  72 | +    2. A number, a name or a negation in any other pair holds (law L-v 2: the render holds before any vote).
  73 | +    3. Per pair (reads: the render's test of the second recogniser's reading there): it reads the approved words ->
  74 | +       the approved; else it reads the run's AND edge_distance >= EDGE_131 tokens -> the run's; else (all three
  75 | +       differ, or the run's too near an edge) the pair holds.
  76 | +    4. The record's pairs must be exactly these (currency pairs aside), in order: the same words (canon tokens), the
  77 | +       same reading taken, the same edge distance.
  78 | +    5. The spoken text is the merged reading (the approved tokens, each run-taken pair as the run's), or that with
  79 | +       ruling 72's adoptions on top (the second recogniser's fillers, a repetition, one function word): every
  80 | +       difference between them must be in ruling 84's class (class_84, as today's adopt_spoken) AND be the second
  81 | +       recogniser's own reading there (reads), or it holds.
  82 | +    -> [{"spoken", "approved", "class", "took", "edge_distance"} (+ "why" when it holds)], one per pair in the diff's
  83 | +    order, then ruling 72's differences on the merged text (took "ruling 72"), then one per failed whole-record test;
  84 | +    a class None holds."""
  85 | +    def held(why, **kw):
  86 | +        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None}, **kw, **{"class": None},
  87 | +                    why=why)
  88 | +    adj = adj if isinstance(adj, dict) else {}
  89 | +    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
  90 | +    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
  91 | +            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
  92 | +        return [held("the lock record does not hold the three readings of this segment's approved text")]
  93 | +    texts = (run_t, pin_t)
  94 | +    r, p, ops = diff(run_t, pin_t)
  95 | +    s = canon.canon_tokens(sec_t)
  96 | +    out, took_run = [], set()
  97 | +    for op in ops:
  98 | +        _tag, a, b, c, d = op
  99 | +        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d])}
 100 | +        if currency_pair(r, p, op):
 101 | +            out.append(dict(row, took="currency", edge_distance=None, **{"class": "currency format (ruling 131 (B))"}))
 102 | +            continue
 103 | +        row["edge_distance"] = edge_distance(r, p, op)
 104 | +        if any(critical(t, texts) for t in r[a:b] + p[c:d]):
 105 | +            out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
 106 | +        elif reads(p, s, c, d):
 107 | +            out.append(dict(row, took="approved", **{"class": "two of three readings: the approved words"}))
 108 | +        elif reads(r, s, a, b) and row["edge_distance"] >= EDGE_131:
 109 | +            out.append(dict(row, took="run", **{"class": "two of three readings: as spoken"}))
 110 | +            took_run.add((a, c))
 111 | +        else:
 112 | +            out.append(dict(row, took=None, **{"class": None}, why=(
 113 | +                f"the run's reading within {EDGE_131} tokens of a cut edge" if reads(r, s, a, b) else
 114 | +                "all three readings differ")))
 115 | +    merged = []
 116 | +    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
 117 | +        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
 118 | +    rec = adj.get("pairs")
 119 | +    theirs = [(x.get("run"), x.get("approved"), x.get("took"), x.get("edge_distance")) for x in rec] \
 120 | +        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
 121 | +    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out if x["took"] != "currency"]
 122 | +    if theirs != mine:
 123 | +        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
 124 | +    for x in class_84(spoken, " ".join(merged)):        # ruling 72 on top of the merged reading, as today
 125 | +        out.append(dict(x, took="ruling 72", edge_distance=None, **(
 126 | +            {"why": "the spoken text differs from the merged reading outside ruling 84's class"} if x["class"] is None
 127 | +            else {})))
 128 | +    sp = canon.canon_tokens(spoken)                     # and only the second recogniser's own reading there
 129 | +    for tag, a, b, c, d in SequenceMatcher(None, sp, merged, autojunk=False).get_opcodes():
 130 | +        if tag != "equal" and not reads(sp, s, a, b):
 131 | +            out.append(held(f"the spoken text's {' '.join(sp[a:b])!r} for the merged {' '.join(merged[c:d])!r} is not "
 132 | +                            f"the second recogniser's reading there (ruling 72 adopts only its reading)"))
 133 | +    return out
 134 | +
 135 | +
 136 |  def reads(x, s, lo, hi):
 137 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
 138 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
 139 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 140 | index 8eea07a..81dc1a4 100644
 141 | --- a/pipeline/lock_precheck.py
 142 | +++ b/pipeline/lock_precheck.py
 143 | @@ -26,6 +26,12 @@ Outcomes:
 144 |    carry-over class for an insert or a drop; never a number, a name or a negation). Otherwise it is a hold (fail
 145 |    closed). Under ruling 84 (b) the spoken text holds the second recogniser's reading of the one function word; the
 146 |    render's lock keeps its decode's word and records the other reading (the entry's "alternatives").
 147 | +  RULING 131 (A) (orchestrator 08:25 ET Nov 17): when the entry's lock record ("adjudication") is under ruling 131
 148 | +  (A), two of the three readings decided each pair and the spoken text is the lock's merged text. It is adopted only
 149 | +  when this side's own re-check (attest.class_131, from the record's three readings) finds every pair decided the same
 150 | +  way, every run-taken pair at least 3 tokens from both cut edges, no number, name or negation, and the spoken text
 151 | +  the merged reading; anything else is a hold (fail closed). (B): currency format ('$2 billion' for a spoken
 152 | +  '2 billion') is no difference.
 153 |  - hold: the clip may not be used with that text. The reason says why.
 154 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
 155 |    is sent again rather than reusing an error.
 156 | @@ -41,7 +47,9 @@ from datetime import datetime, timezone
 157 |  import attest as AT
 158 |  import canon as C
 159 |  
 160 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105"   # RULING 105 (orchestrator
 161 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131"   # RULING 131
 162 | +#   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
 163 | +#   Nov 17); entries under the old RULES are never read. RULING 105 (orchestrator
 164 |  #   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
 165 |  #   RULING 103 (orchestrator 14:12 Nov 14): the
 166 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
 167 | @@ -158,6 +166,19 @@ def decide(seg, e):
 168 |      spoken, approved = e.get("spoken_text"), seg["approved_text"]
 169 |      if not isinstance(spoken, str) or not spoken.strip():
 170 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 171 | +    adj = e.get("adjudication")
 172 | +    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_131):   # RULING 131 (A): two of three
 173 | +        diffs = AT.class_131(spoken, approved, adj)
 174 | +        bad = [x for x in diffs if x["class"] is None]
 175 | +        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
 176 | +            return {"verdict": "hold", "outcome": out, "differences": diffs,
 177 | +                    "why": "adopt_spoken under ruling 131 (A), but by this side's attest.class_131 it holds: " +
 178 | +                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
 179 | +        if not any(x["took"] == "run" for x in diffs):  # no pair took the spoken reading: the approved text stands
 180 | +            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 131 (A) with no pair taking "
 181 | +                                                              "the run's reading: the approved text stands"}
 182 | +        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
 183 | +                "adoption": AT.RULE_131}
 184 |      diffs = AT.class_84(spoken, approved)
 185 |      if not diffs:                                     # the same canonical words: the approved text stands
 186 |          return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 187 | @@ -262,12 +283,22 @@ def relisten_of(e):
 188 |      return r if isinstance(r, dict) else None
 189 |  
 190 |  
 191 | -def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
 192 | -    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 193 | -    return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 194 | -            "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 195 | -                       "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 196 | -                       "or a drop; checked on this side too), and no line quotes the changed words",
 197 | +def attested(row, run_rule=None):
 198 | +    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it:
 199 | +    ruling 84's class, or ruling 131 (A)'s two of three readings (row["adoption"])."""
 200 | +    if row.get("adoption") == AT.RULE_131:
 201 | +        rule = run_rule or "ruling 72 + ruling 131 (A) (08:25 ET Nov 17): adopt_spoken, two of the three readings agree"
 202 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed pair is the "
 203 | +                   "reading two of the three readings (the approved text, the render's run decode, the second "
 204 | +                   "recogniser) agree on, re-checked on this side from the lock's record, at least 3 tokens from both "
 205 | +                   "cut edges, never a number, a name or a negation; no line quotes the changed words (marked on the "
 206 | +                   "release: 'word check settled by two of three readings')")
 207 | +    else:
 208 | +        rule = run_rule or "ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"
 209 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 210 | +                   "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 211 | +                   "or a drop; checked on this side too), and no line quotes the changed words")
 212 | +    return {"rule": rule, "was": row["approved_text"], "differences": row["differences"], "carried": carried,
 213 |              "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 214 |  
 215 |  
 216 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 217 | index fb087af..648f77b 100644
 218 | --- a/tests/package/test_lock_precheck.py
 219 | +++ b/tests/package/test_lock_precheck.py
 220 | @@ -11,6 +11,7 @@ import unittest
 221 |  HERE = os.path.dirname(os.path.abspath(__file__))
 222 |  REPO = os.path.dirname(os.path.dirname(HERE))
 223 |  sys.path.insert(0, os.path.join(REPO, "pipeline"))
 224 | +import attest as AT  # noqa: E402
 225 |  import lock_precheck as LP  # noqa: E402
 226 |  
 227 |  HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 228 | @@ -133,9 +134,10 @@ class TestRuling84(unittest.TestCase):
 229 |      s = LP.segments_of([BREEDLOVE])[0]
 230 |  
 231 |      def test_the_rules_string_is_the_integrators(self):
 232 | -        """RULING 103 (14:12 Nov 14) and RULING 105 (20:13 Nov 14) joined the integrator's rules string (its messages
 233 | -        of 14:3x and 20:5x Nov 14)."""
 234 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105")
 235 | +        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 236 | +        rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 237 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 238 | +                                   "ruling 131")
 239 |  
 240 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 241 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 242 | @@ -162,6 +164,161 @@ class TestRuling84(unittest.TestCase):
 243 |          self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 244 |  
 245 |  
 246 | +class TestRuling131(Dirs):
 247 | +    """RULING 131 (orchestrator 08:25 ET Nov 17). (A): per differing pair of the render's lock, two of the three readings
 248 | +    (the approved text, the run's decode, the second recogniser) decide it and the sealed text takes that reading, at
 249 | +    least 3 tokens from both cut edges; never a number, a name or a negation; all three different holds. (B): currency
 250 | +    format is no difference. The render's lock records it (the integrator's message of 08:2x Nov 17); this side
 251 | +    re-derives every pair from the three readings (attest.class_131). Last night's held span: What Bitcoin Did d6adeb54
 252 | +    (WdiF0i925rs 3339.900-3354.680), its three readings as the pre-check recorded them at 03:46:30Z Nov 17."""
 253 | +    RUN = ("i have been recently done a bunch of pieces on the 2023 bull market, that climbing a wall of worry. um there "
 254 | +           "was massive amounts of fear during that period of time. bitcoin was actually trending up into the right, "
 255 | +           "and fear was also trending up into the right during that.")
 256 | +    APPROVED = ("I have been recently done a budget pieces on the 2023 bull market, like climbing a wall of worry. There "
 257 | +                "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 258 | +                "right, and fear was also trending up into the right during that.")
 259 | +    SECOND = ("comes next? I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a "
 260 | +              "wall of worry. Um, there was massive amounts of fear during that period of time. Bitcoin was actually "
 261 | +              "trending up into the right, and fear was also trending up into the right during that,")
 262 | +    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. Um, "
 263 | +              "there was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 264 | +              "right, and fear was also trending up into the right during that.")
 265 | +    SPOKEN = MERGED.replace("2023 bull", "2023, uh, bull")      # ruling 72 on top: the second recogniser's 'uh'
 266 | +    PAIRS = [{"run": "bunch of", "approved": "budget", "second_reads": "run", "took": "run",
 267 | +              "agreed": ["run", "second"], "edge_distance": 6},
 268 | +             {"run": "that", "approved": "like", "second_reads": "approved", "took": "approved",
 269 | +              "agreed": ["approved", "second"], "edge_distance": 14},
 270 | +             {"run": "um", "approved": "", "second_reads": "run", "took": "run", "agreed": ["run", "second"],
 271 | +              "edge_distance": 20}]
 272 | +    WBD = {"moment_id": "w", "video_id": "WdiF0i925rs", "start": 3339.9, "end": 3354.68, "text": APPROVED}
 273 | +
 274 | +    def adj(self, **kw):
 275 | +        return dict({"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "verdict": "approved",
 276 | +                     "pairs": self.PAIRS, "recogniser": "elevenlabs:scribe_v1", "usd": 0.0, "run_decode": self.RUN,
 277 | +                     "approved": self.APPROVED, "second_recogniser": self.SECOND}, **kw)
 278 | +
 279 | +    def decide(self, spoken=None, **kw):
 280 | +        s = LP.segments_of([self.WBD])[0]
 281 | +        return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken or self.MERGED, adjudication=self.adj(**kw)))
 282 | +
 283 | +    def test_last_nights_held_span_now_adopts_and_is_sealed_with_its_record(self):
 284 | +        d = self.decide()                                          # the merged text as it stands ("same")
 285 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 286 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in d["differences"]],
 287 | +                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "run")])
 288 | +        d = self.decide(self.SPOKEN)                               # with ruling 72's 'uh' on top ("adopt")
 289 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 290 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"], x["class"]) for x in d["differences"]][3:],
 291 | +                         [("uh", "", "ruling 72", "filler")])
 292 | +        s = LP.segments_of([self.WBD])[0]
 293 | +        self.put(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
 294 | +        pre = LP.check([self.WBD], "r", self.req, self.res, log=lambda m: None)
 295 | +        pk = LP.apply({"segments": [{k: self.WBD[k] for k in ("video_id", "start", "end", "text")}], "lines": []}, pre)
 296 | +        seg = pk["segments"][0]
 297 | +        self.assertEqual((seg["text"], seg["attested"]["was"]), (self.SPOKEN, self.APPROVED))
 298 | +        self.assertIn("ruling 131 (A)", seg["attested"]["rule"])
 299 | +        self.assertIn("two of the three readings", seg["attested"]["carried"])
 300 | +        self.assertEqual(LP.pin_problems(pk), [])
 301 | +
 302 | +    def test_this_side_rederives_every_pair_and_never_trusts_the_record(self):
 303 | +        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"]), dict(self.PAIRS[2])]
 304 | +        for spoken, kw, why in (
 305 | +                (self.MERGED.replace("like climbing", "that climbing"), {"pairs": lie},   # the second reads 'like'
 306 | +                 "the lock record's pairs are not this side's"),
 307 | +                (self.MERGED, {"pairs": self.PAIRS[:2]}, "the lock record's pairs are not this side's"),
 308 | +                (self.MERGED, {"pairs": [dict(p, edge_distance=9) for p in self.PAIRS]},
 309 | +                 "the lock record's pairs are not this side's"),
 310 | +                (self.MERGED.replace("bunch of", "budget"), {}, "outside ruling 84's class"),
 311 | +                (self.MERGED.replace("massive", "huge"), {}, "outside ruling 84's class"),
 312 | +                (self.MERGED.replace("climbing", "the climbing"), {}, "is not the second recogniser's reading"),
 313 | +                (self.MERGED.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 314 | +                 "outside ruling 84's class"),                                     # the second recogniser alone
 315 | +                (self.MERGED, {"second_recogniser": None}, "does not hold the three readings"),
 316 | +                (self.MERGED, {"approved": self.MERGED}, "does not hold the three readings")):
 317 | +            d = self.decide(spoken, **kw)
 318 | +            self.assertEqual(d["verdict"], "hold", (spoken, kw))
 319 | +            self.assertIn(why, d["why"])
 320 | +
 321 | +    def test_what_still_holds(self):
 322 | +        for kw, why in (
 323 | +                ({"second_recogniser": self.SECOND.replace("bunch of", "lunch of")}, "all three readings differ"),
 324 | +                ({"run_decode": self.RUN.replace("have been", "have seen"),               # the 3rd token: 2 from the
 325 | +                  "second_recogniser": self.SECOND.replace("have been", "have seen")},     # edge
 326 | +                 "within 3 tokens of a cut edge"),
 327 | +                ({"run_decode": self.RUN.replace("2023", "2024"),
 328 | +                  "second_recogniser": self.SECOND.replace("2023", "2024")}, "a number, a name or a negation"),
 329 | +                ({"run_decode": self.RUN.replace("there was", "there wasn't"),
 330 | +                  "second_recogniser": self.SECOND.replace("there was", "there wasn't")},
 331 | +                 "a number, a name or a negation"),
 332 | +                ({"run_decode": self.RUN.replace("bunch of", "Saylor"),
 333 | +                  "second_recogniser": self.SECOND.replace("bunch of", "Saylor")}, "a number, a name or a negation")):
 334 | +            d = self.decide(**kw)
 335 | +            self.assertEqual(d["verdict"], "hold", kw)
 336 | +            self.assertIn(why, d["why"])
 337 | +
 338 | +    def test_currency_format_is_no_difference(self):
 339 | +        """BTC Sessions 93cfa865 (2oY7TU6CPok 54.260-61.380), the line-up's second hold: the approved '$2 billion',
 340 | +        '$645 million'; the run's decode and the second recogniser say no 'dollars' (the pre-check at 03:46:32Z)."""
 341 | +        app = ("Meanwhile, Bitcoin had a terrible weekend. We went all the way down to 62K, $2 billion in leverage wiped "
 342 | +               "out, $645 million in just 30 minutes.")
 343 | +        adj = self.adj(pairs=[], run_decode="meanwhile, bitcoin had a terrible weekend. we went all the way down to "
 344 | +                                            "62k, 2 billion in leverage wiped out, 645 million in just 30 minutes.",
 345 | +                       approved=app, second_recogniser="emerging. Meanwhile, Bitcoin had a terrible weekend. We went "
 346 | +                       "all the way down to 62K, two billion in leverage wiped out, 645 million in just 30 minutes.")
 347 | +        s = LP.segments_of([{"video_id": "2oY7TU6CPok", "start": 54.26, "end": 61.38, "text": app}])[0]
 348 | +        rows = AT.class_131(app, app, adj)
 349 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
 350 | +                         [("", "dollars", "currency"), ("", "dollars", "currency")])
 351 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 352 | +        self.assertTrue(AT.currency_pair(["2000000000", "dollars"], ["2000000000"], ("delete", 1, 2, 1, 1)))
 353 | +        self.assertTrue(AT.currency_pair(["2000000000"], ["2000000000", "dollars"], ("insert", 1, 1, 1, 2)))
 354 | +        self.assertFalse(AT.currency_pair(["many", "dollars"], ["many"], ("delete", 1, 2, 1, 1)))   # no number before
 355 | +        self.assertFalse(AT.currency_pair(["5", "dollars", "dollars"], ["5", "dollars"], ("delete", 2, 3, 2, 2)))
 356 | +        self.assertFalse(AT.currency_pair(["5", "euros"], ["5", "dollars"], ("replace", 1, 2, 1, 2)))
 357 | +        self.assertFalse(AT.currency_pair(["5", "dollars"], ["5", "euros"], ("replace", 1, 2, 1, 2)))
 358 | +
 359 | +    def test_a_repetition_slides_to_its_furthest_placement(self):
 360 | +        """mKNAcOFMYD4 755.454-764.214, held Nov 13 (its real readings): difflib puts the extra "that's why" on the
 361 | +        second copy, 2 tokens from the end; the first copy gives the same two texts and is 4 from it (the integrator's
 362 | +        message of 08:4x Nov 17). A spoken text that reverts the vote holds, though it is in ruling 84's class."""
 363 | +        run = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the "
 364 | +               "bank owns the money and they could just take it from me. and that's why that's why we bitcoin.")
 365 | +        app = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the "
 366 | +               "bank owns the money and they could just take it from me. And that's why we Bitcoin.")
 367 | +        sec = ("second biggest. My biggest fear is that I go to the bank and I punch in my code and the money's not "
 368 | +               "there, 'cause the bank owns the money and they could just take it from me, and that's why, that's why "
 369 | +               "we Bitcoin.")
 370 | +        merged = app.replace("punch you", "punch in").replace("that's why we", "that's why that's why we")
 371 | +        pairs = [{"run": "in", "approved": "you", "took": "run", "edge_distance": 13},
 372 | +                 {"run": "that's why", "approved": "", "took": "run", "edge_distance": 4}]
 373 | +        s = LP.segments_of([{"video_id": "mKNAcOFMYD4", "start": 755.454, "end": 764.214, "text": app}])[0]
 374 | +        adj = self.adj(pairs=pairs, run_decode=run, approved=app, second_recogniser=sec)
 375 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=merged, adjudication=adj))["verdict"],
 376 | +                         "adopt")
 377 | +        back = LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))
 378 | +        self.assertEqual(back["verdict"], "hold")
 379 | +        self.assertIn("is not the second recogniser's reading", back["why"])
 380 | +
 381 | +    def test_a_repetition_near_the_start_slides_right(self):
 382 | +        """The same repetition near the span's start: difflib puts the extra "that's why" on the FIRST copy (1 token
 383 | +        from the edge); sliding right through the equal words gives 3."""
 384 | +        app = "So that's why we went to the bank and asked them for the money back."
 385 | +        run = "so that's why that's why we went to the bank and asked them for the money back."
 386 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 387 | +        adj = self.adj(pairs=[{"run": "that's why", "approved": "", "took": "run", "edge_distance": 3}],
 388 | +                       run_decode=run, approved=app, second_recogniser=run)
 389 | +        r, p, ops = AT.diff(run, app)
 390 | +        self.assertEqual((ops, AT.edge_distance(r, p, ops[0])), ([("delete", 1, 3, 1, 1)], 3))   # 1 without the slide
 391 | +        d = LP.decide(s, entry(s, "adopt_spoken", spoken_text="So that's why that's why we went to the bank and asked "
 392 | +                                                               "them for the money back.", adjudication=adj))
 393 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 394 | +
 395 | +    def test_only_a_ruling_131_record_is_rechecked_by_two_of_three(self):
 396 | +        d = self.decide(rule="ruling 17 (orchestrator 2026-11-12 '10:20')")                # ruling 84's class: a
 397 | +        self.assertEqual(d["verdict"], "hold")                                             # content word holds
 398 | +        self.assertIn("outside ruling 84's class", d["why"])
 399 | +
 400 | +
 401 |  class TestCheck(Dirs):
 402 |      def run_check(self, segs, appear=None, timeout=60.0):
 403 |          t = [0.0]
 404 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 405 | index 0b8d8b9..9e5d466 100644
 406 | --- a/tests/package/test_ruling_105.py
 407 | +++ b/tests/package/test_ruling_105.py
 408 | @@ -39,7 +39,7 @@ BLOCKWARE = record()
 409 |  
 410 |  class TestTheRules(Dirs):
 411 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 412 | -        self.assertTrue(LP.RULES.endswith("+ ruling 103 + ruling 105"))
 413 | +        self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 414 |          self.assertEqual(LP.DECODER, "a4c307f78c94")
 415 |          s = LP.segments_of([HOOK])[0]
 416 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 417 | 
```

---

pp-selectid: RULING 131 (orchestrator 08:25 ET Nov 17), the builder's lockstep half. "(A) ADOPTED as written: per
differing pair, two of the three readings (approved text, the render's run decode, the second recogniser) decide it
and the sealed text takes that reading, for fillers, function words, repetitions and content words, each at least 3
words from a cut edge; never a number (save B), a name or a negation; a pair where all three differ HOLDS. (B)
ADOPTED: a currency symbol is formatting ('$2 billion' equals a spoken '2 billion'), a canon like 401k."
The render's lock (the integrator's side, pinned.adjudicate_lock) applies it and records it; THIS side only reads the
lock pre-check's answer for a segment and decides whether to seal it. Files: pipeline/attest.py,
pipeline/lock_precheck.py, tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py. canon.py is the
integrator's, taken byte-identical at landing: this side uses only canon.dollars_after_number(tokens, k) (tokens[k] ==
"dollars", k > 0, tokens[k-1] matches \d+(\.\d+)?), canon.canon_tokens and canon.canon_spans (all UNCHANGED otherwise).

THE RECORD (the integrator's messages of 08:2x-08:4x Nov 17): an entry with outcome "adopt_spoken" whose
"adjudication" (the FIRST lock's) has rule "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", the three full readings
"run_decode", "approved", "second_recogniser", and "pairs" [{"run", "approved", "second_reads", "took":
"run"|"approved", "agreed", "edge_distance"}], currency pairs NOT among them. "spoken_text" is the lock's merged text,
or that with ruling 72's adoptions on top (the second recogniser's fillers / a repetition / one function word beyond
the merged text: today's adopt_spoken layer). The render's rule per pair: the approved reading where the second
recogniser reads the approved words; else the run's where it reads the run's AND edge_distance >= 3; else HOLD.
edge_distance = min(a, len(run) - b) in the run decode's canon tokens, except that a pair with an empty side (delete /
insert) inside a repetition may slide through the equal tokens beside it (both texts stay the same), taking the
largest distance over its placements.

THE CHANGE:
(a) attest.class_131(spoken, approved, adj) (attest.py:168): THIS SIDE'S OWN RE-CHECK, re-running the render's steps
    on the recorded readings, never trusting the record's classes. attest.diff (UNCHANGED :69: canon tokens,
    SequenceMatcher non-equal opcodes); per pair: currency_pair (:134) -> no difference, keeps the approved words; a
    number, a name or a negation (attest.critical, UNCHANGED :54, the render's _lv2_critical) -> holds; the second
    recogniser reads the approved words (attest.reads, UNCHANGED :239, the render's own test) -> took approved; else
    reads the run's AND edge_distance (:142) >= 3 -> took run; else holds. Whole-record tests: the record's pairs must
    equal this side's (run, approved, took, edge_distance) in order; the record's approved reading must be the
    segment's approved text (canon tokens); the spoken text against the merged tokens: every difference must be in
    ruling 84's class (attest.class_84, UNCHANGED :94) AND be the second recogniser's own reading there (reads).
(b) lock_precheck.decide (lock_precheck.py:148): an adopt_spoken whose adjudication rule starts with "ruling 131 (A)"
    goes to class_131: any class None -> hold (fail closed); no pair took the run's reading -> pass (the approved
    stands); else adopt with "adoption": "ruling 131 (A)". Every other adopt_spoken keeps class_84 exactly as before.
    Ruling 105's check runs first for every pass and adoption (UNCHANGED :155).
(c) lock_precheck.attested (:286): the sealed record's rule holds the literal "ruling 131 (A)" (the integrator's
    release caption prints 'word check settled by two of three readings' from it) when the row's adoption is ruling
    131's, else ruling 84's as before. apply (UNCHANGED :311) seals the spoken text with it and still refuses when a
    line quotes the changed words (:326); pin_problems (UNCHANGED :348) still needs the pre-check to cover the segments
    as they now stand.
(d) RULES gains "+ ruling 131" (an entry under the old rules is never read: _matches, UNCHANGED :105). DECODER moves to
    the integrator's final sha at landing (a constant; the old one joins the never-read list).

TESTS (TestRuling131, 7 tests): last night's held span (WdiF0i925rs 3339.900-3354.680, its REAL three readings)
adopts as merged and with ruling 72's 'uh' on top, sealed through check/apply with the ruling 131 record; a record
that lies (a pair claimed run that the second reads as approved; a missing pair; a wrong edge distance; a spoken text
outside the class; a function word the second recogniser never heard; a content word only the second recogniser
heard; no readings; another approved text) holds; all three different, a run pair 2 tokens from the edge, a number,
a negation, a name hold; mKNAcOFMYD4's real readings: the repeated "that's why" slides left to 4 and adopts, and a
spoken text that reverts the vote holds; the same repetition near the start slides right (1 -> 3); the BTC Sessions
span (real readings) is currency format only and passes; currency_pair's edges; an adopt_spoken under ruling 17's
record keeps ruling 84's class. Mutations M1-M19 after a control run: 19 of 19 killed.

PLEASE CHECK: (1) that nothing the ruling forbids can be sealed: a number, a name, a negation, a three-way
disagreement, a run reading within 3 tokens of an edge; (2) that a record which disagrees with this side's own
derivation always holds, never passes; (3) that the currency test cannot hide a real difference; (4) that the slide
cannot carry a pair that is not a true repetition, nor beyond the equal tokens beside it; (5) that ruling 72's layer
on the merged text cannot reintroduce or revert a decided word; (6) that ruling 84's existing path is unchanged for
any other adopt_spoken; (7) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
