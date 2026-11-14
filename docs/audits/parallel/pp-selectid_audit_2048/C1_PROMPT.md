# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2048
# Branch: pp-selectid
# Generated: 2026-11-13 20:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2048/C1_STEP.diff (562 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index 78a4fde..f45e4d5 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -10,7 +10,10 @@ refused). The takeaway, title and caption are re-gated only if they quote the ch
   6 |  The diff is the render's own (pipeline/pinned.adjudicate_lock): canon.canon_tokens of the run's decode against the
   7 |  approved text, difflib.SequenceMatcher(autojunk=False) opcodes. canon.py here is byte-identical to the render's, and
   8 |  critical() is the render's _lv2_critical with its lists. CPU only, no model call. Imports nothing from package.py
   9 | -(package_pin, which the integrator's check imports, must never pull it in)."""
  10 | +(package_pin, which the integrator's check imports, must never pull it in).
  11 | +
  12 | +RULING 84 (orchestrator 20:41 Nov 13) has its own class, class_84, for the render's lock pre-check only (the
  13 | +second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged."""
  14 |  import re
  15 |  from difflib import SequenceMatcher
  16 |  
  17 | @@ -38,6 +41,10 @@ what which who whom whose why how where
  18 |  """.split())
  19 |  
  20 |  
  21 | +# RULING 84 (a): the fillers the second recogniser hears and Whisper drops, exactly the ruling's list (canon tokens)
  22 | +FILLERS = frozenset(("um", "uh", "er", "ah", "mm", "hmm"))
  23 | +
  24 | +
  25 |  def critical(tok, texts):
  26 |      """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  27 |      capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  28 | @@ -78,6 +85,39 @@ def carry_class(r, p, op, texts):
  29 |      return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"
  30 |  
  31 |  
  32 | +def class_84(spoken, approved):
  33 | +    """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
  34 | +    it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
  35 | +    against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
  36 | +    1. A filler (FILLERS) inside a difference is dropped from the SPOKEN side only: class "filler". A filler on the
  37 | +       approved side alone is not in the class.
  38 | +    2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
  39 | +    3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
  40 | +    4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
  41 | +    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text."""
  42 | +    texts = (spoken, approved)
  43 | +    r, p, ops = diff(spoken, approved)
  44 | +    drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
  45 | +    out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
  46 | +    r2 = [t for i, t in enumerate(r) if i not in drop]
  47 | +    one = 0
  48 | +    for op in SequenceMatcher(None, r2, p, autojunk=False).get_opcodes():
  49 | +        tag, a, b, c, d = op
  50 | +        if tag == "equal":
  51 | +            continue
  52 | +        rs, ps = r2[a:b], p[c:d]
  53 | +        if any(critical(t, texts) for t in rs + ps):
  54 | +            k = None
  55 | +        elif rs and ps:
  56 | +            k = "one function word" if (len(rs) == len(ps) == 1 and rs[0] in FUNCTION_WORDS and
  57 | +                                        ps[0] in FUNCTION_WORDS and one == 0) else None
  58 | +            one += k is not None
  59 | +        else:
  60 | +            k = carry_class(r2, p, op, texts)
  61 | +        out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": k})
  62 | +    return out
  63 | +
  64 | +
  65 |  def reads(x, s, lo, hi):
  66 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
  67 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
  68 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  69 | index 0cc5e96..4ca0726 100644
  70 | --- a/pipeline/lock_precheck.py
  71 | +++ b/pipeline/lock_precheck.py
  72 | @@ -12,7 +12,7 @@ and answers each name and content once.
  73 |  Results: read only, in /home/ultron/protocol_pulse/data/lock_precheck/results/
  74 |  <video_id>.<start %.3f>-<end %.3f>.<decoder[:12]>.json. Each file is a list. The answer is the newest entry (by "at")
  75 |  that meets all of these:
  76 | -- rules == RULES ("ruling 17 + ruling 72 + ruling 73" since 18:43 Nov 13; an answer under any other rules string,
  77 | +- rules == RULES ("ruling 17 + ruling 72 + ruling 73 + ruling 84" since ruling 84; an answer under any other rules string,
  78 |    or in a file named for another decoder, is not valid for the render's code and is never read);
  79 |  - its window is the segment's [start, end];
  80 |  - its role, approved_text, trimmed_leading and untrimmed_start equal the request's.
  81 | @@ -21,9 +21,11 @@ Entries without "rules" are ruling 68's, from before, and are never read.
  82 |  Outcomes:
  83 |  - no_difference, adopted, two_readings: pass. The approved text stands.
  84 |  - adopt_spoken: the text to seal is "spoken_text", already through the render's validate_range + segment_lock. It is
  85 | -  adopted only when this side's own check agrees that every difference is in ruling 67's carry-over class
  86 | -  (attest.carry_class: a function word, or the speaker's own immediate repetition; never a number, a name or a
  87 | -  negation). Otherwise it is a hold (fail closed).
  88 | +  adopted only when this side's own check agrees that every difference is in ruling 84's class (attest.class_84,
  89 | +  the integrator's class: a filler the second recogniser heard, ONE 1-for-1 function word, else ruling 67's
  90 | +  carry-over class for an insert or a drop; never a number, a name or a negation). Otherwise it is a hold (fail
  91 | +  closed). Under ruling 84 (b) the spoken text holds the second recogniser's reading of the one function word; the
  92 | +  render's lock keeps its decode's word and records the other reading (the entry's "alternatives").
  93 |  - hold: the clip may not be used with that text. The reason says why.
  94 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
  95 |    is sent again rather than reusing an error.
  96 | @@ -38,7 +40,8 @@ from datetime import datetime, timezone
  97 |  
  98 |  import attest as AT
  99 |  
 100 | -RULES = "ruling 17 + ruling 72 + ruling 73"   # RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 101 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
 102 | +#   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 103 |  DECODER = "8a101f222598"                      # side): the render's own cut placement joins the pre-check, so its
 104 |  #   decoder_sha changed (8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7); a passing entry carries
 105 |  #   "cut", and a span the render cannot cut holds ("ruling 73: the render cannot cut this span: ...")
 106 | @@ -137,15 +140,12 @@ def decide(seg, e):
 107 |      spoken, approved = e.get("spoken_text"), seg["approved_text"]
 108 |      if not isinstance(spoken, str) or not spoken.strip():
 109 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 110 | -    r, p, ops = AT.diff(spoken, approved)
 111 | -    if not ops:                                       # the same canonical words: the approved text stands
 112 | +    diffs = AT.class_84(spoken, approved)
 113 | +    if not diffs:                                     # the same canonical words: the approved text stands
 114 |          return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 115 | -    classes = [AT.carry_class(r, p, o, (spoken, approved)) for o in ops]
 116 | -    diffs = [{"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 117 | -             for (_, a, b, c, d), k in zip(ops, classes)]
 118 | -    if None in classes:                               # this side's ruling-67 check disagrees: fail closed
 119 | +    if any(x["class"] is None for x in diffs):        # this side's ruling-84 check disagrees: fail closed
 120 |          return {"verdict": "hold", "outcome": out, "differences": diffs,
 121 | -                "why": "adopt_spoken, but by this side's attest.carry_class a difference is outside ruling 67's "
 122 | +                "why": "adopt_spoken, but by this side's attest.class_84 a difference is outside ruling 84's "
 123 |                         "class: " + str([[x["spoken"], x["approved"]] for x in diffs if x["class"] is None])[:300]}
 124 |      return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs}
 125 |  
 126 | @@ -180,11 +180,12 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
 127 |              "error": "; ".join(errs)[:600] or None}
 128 |  
 129 |  
 130 | -def attested(row, run_rule="ruling 72 (live 17:17 Nov 13): adopt_spoken, in ruling 67's carry-over class"):
 131 | +def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
 132 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 133 |      return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 134 |              "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 135 | -                       "ruling 67's carry-over class (checked on this side too), and no line quotes the changed words",
 136 | +                       "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 137 | +                       "or a drop; checked on this side too), and no line quotes the changed words",
 138 |              "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 139 |  
 140 |  
 141 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 142 | index aa6c175..2b7a7cb 100644
 143 | --- a/pipeline/providers.py
 144 | +++ b/pipeline/providers.py
 145 | @@ -178,12 +178,22 @@ class Backend:
 146 |          """The most output tokens this back-end may bill for one call (its own floor applied)."""
 147 |          return max(int(self.spec.get("min_out", 0)), max_tokens)
 148 |  
 149 | -    def upper_usd(self, prompt, max_tokens, system=None):
 150 | -        """The call's spend upper bound: every prompt character a token (a safe over-estimate), IMAGE_TOKENS_UPPER per
 151 | -        image of a vision prompt, + the output cap."""
 152 | +    @staticmethod
 153 | +    def prompt_tokens_upper(prompt, system=None):
 154 | +        """A prompt's input tokens, counted from above: every character a token (a safe over-estimate), + 200 for the
 155 | +        message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
 156 |          n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
 157 | -        return self.usd({"in": len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img,
 158 | -                         "out": self.max_out(max_tokens)})
 159 | +        return len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img
 160 | +
 161 | +    def upper_usd(self, prompt, max_tokens, system=None):
 162 | +        """The call's spend upper bound: its prompt tokens (prompt_tokens_upper) + the output cap."""
 163 | +        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": self.max_out(max_tokens)})
 164 | +
 165 | +    def prompt_usd(self, prompt, system=None):
 166 | +        """RULING 83 (a) (orchestrator 20:33 Nov 13): what a call abandoned at its deadline is booked at: its PROMPT
 167 | +        tokens at the listed input rate, no output. A call that never answered has no vendor token count, so the
 168 | +        prompt is counted from above (prompt_tokens_upper): never an under-booking."""
 169 | +        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": 0})
 170 |  
 171 |      def key(self, name):
 172 |          k = env_value(self.env_path, name)
 173 | @@ -249,22 +259,35 @@ class DeadlineExceeded(Exception):
 174 |      more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 175 |  
 176 |  
 177 | -def _within(seconds, fn):
 178 | +def _within(seconds, fn, on_abandon=None, on_late=None):
 179 |      """fn() in a daemon thread, waited for at most `seconds`. -> its value, or its own exception re-raised, or
 180 | -    DeadlineExceeded. An abandoned thread finishes (or times out) on its own; its result is dropped unrecorded."""
 181 | +    DeadlineExceeded. At the deadline on_abandon() runs (it books the abandoned call) BEFORE DeadlineExceeded is
 182 | +    raised, under a lock the thread takes when it ends, so the booking always comes first. An abandoned thread finishes
 183 | +    (or times out) on its own; then on_late(on_abandon's value, fn's value or None, fn's exception or None) runs in
 184 | +    it (ruling 83 (a): a late answer's own figure replaces the booking). Its text is dropped unrecorded. An exception
 185 | +    from on_late is dropped (it runs where nobody can catch it); the booking then stands."""
 186 |      import threading
 187 | -    box, done = {}, threading.Event()
 188 | +    box, done, lock = {}, threading.Event(), threading.Lock()
 189 |  
 190 |      def run():
 191 |          try:
 192 |              box["value"] = fn()
 193 |          except BaseException as e:            # handed back to the caller below
 194 |              box["error"] = e
 195 | -        finally:
 196 | +        with lock:
 197 |              done.set()
 198 | +            late = "abandoned" in box
 199 | +        if late and on_late is not None:
 200 | +            try:
 201 | +                on_late(box["abandoned"], box.get("value"), box.get("error"))
 202 | +            except Exception:                 # noqa: BLE001 (no caller is left; the booking stands)
 203 | +                pass
 204 |      threading.Thread(target=run, daemon=True, name="pp-deadline").start()
 205 |      if not done.wait(seconds):
 206 | -        raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 207 | +        with lock:
 208 | +            if not done.is_set():             # still running: abandoned (an answer at the deadline is used below)
 209 | +                box["abandoned"] = on_abandon() if on_abandon is not None else None
 210 | +                raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 211 |      if "error" in box:
 212 |          raise box["error"]
 213 |      return box["value"]
 214 | @@ -670,7 +693,7 @@ class Router:
 215 |          """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
 216 |          bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
 217 |          estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
 218 | -        its deadline, booked at its upper bound)."""
 219 | +        its deadline, booked at its prompt tokens (ruling 83 (a), 20:33 Nov 13) until a late answer replaces it)."""
 220 |          if self.limit_basis == "reported":
 221 |              if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
 222 |                  raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
 223 | @@ -735,6 +758,52 @@ class Router:
 224 |                      d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
 225 |              self._save(d)
 226 |  
 227 | +    def _late(self, ab, value, error):
 228 | +        """RULING 83 (a): an abandoned call that ended after its deadline (in its own thread). An answer is accounted
 229 | +        as an on-time one would have been, in place of its prompt-token booking: the vendor's reported figure, or,
 230 | +        with none, the estimate from its own token counts. No answer (an error): the booking stands. Either way one
 231 | +        line goes to the deadline log (item 55). The answer's text is never used or recorded."""
 232 | +        b, role, booked = ab["backend"], ab["role"], float(ab["usd"])
 233 | +        rec = {"kind": "late_answer" if error is None else "late_error", "role": role, "model": b.name,
 234 | +               "vendor": b.vendor, "deadline_s": ab.get("deadline_s"),
 235 | +               "seconds": round(time.time() - ab["t0"] + float(ab.get("deadline_s") or 0), 2), "booked_usd": booked}
 236 | +        if error is None:
 237 | +            try:
 238 | +                _text, usage, _secs = value
 239 | +                usage = dict(usage or {})
 240 | +            except (TypeError, ValueError):
 241 | +                usage = None
 242 | +            if usage is None:
 243 | +                rec.update(kind="late_error", error="no (text, usage, seconds) from the back-end")
 244 | +            else:
 245 | +                usd, rep = b.usd(usage), usage.get("usd_reported")
 246 | +                rec.update({"in": usage.get("in"), "out": usage.get("out"), "usd_estimate": usd,
 247 | +                            "usd_reported": float(rep) if _num(rep) else None})
 248 | +                if self.spend_path:
 249 | +                    with self._lock():
 250 | +                        d = self._ledger()
 251 | +                        bb = d["by_backend"].setdefault(b.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
 252 | +                                                                 "price_usd_per_1m": list(b.price)})
 253 | +                        r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
 254 | +                        delta = usd - booked
 255 | +                        bb.update(usd_estimate=round(bb["usd_estimate"] + delta, 6),
 256 | +                                  **{"in": bb["in"] + int(usage.get("in", 0)), "out": bb["out"] + int(usage.get("out", 0))})
 257 | +                        r["usd_estimate"] = round(r["usd_estimate"] + delta, 6)
 258 | +                        d["usd_estimate"] = round(d["usd_estimate"] + delta, 6)
 259 | +                        d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
 260 | +                        if _num(rep):
 261 | +                            bb.update(usd_reported=round(bb.get("usd_reported", 0.0) + float(rep), 8),
 262 | +                                      reported_calls=bb.get("reported_calls", 0) + 1)
 263 | +                            d["usd_reported"] = round(d.get("usd_reported", 0.0) + float(rep), 8)
 264 | +                        else:
 265 | +                            d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
 266 | +                        d["late_answers"] = d.get("late_answers", 0) + 1
 267 | +                        self._save(d)
 268 | +                    rec["replaced"] = True
 269 | +        else:
 270 | +            rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
 271 | +        self._log_slow(rec)
 272 | +
 273 |      def reject(self, reply, why=""):
 274 |          """The caller found this reply out of its contract: drop its recording, so the exchange is asked again next
 275 |          time instead of served again (fable C1 U1). Offline replay keeps its recordings. -> True if one was dropped."""
 276 | @@ -810,18 +879,25 @@ class Router:
 277 |                  n = self.heimdall_tripwire()
 278 |                  if n:
 279 |                      notices.append(n)
 280 | +
 281 | +            def abandon(b=b, key=key):                 # RULING 83 (a): booked at its PROMPT tokens (input rate), an
 282 | +                booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 283 | +                self._settle(key, b, {"in": 0, "out": 0}, booked, role)
 284 | +                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 285 |              try:
 286 |                  if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 287 | -                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system))
 288 | +                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system),
 289 | +                                                on_abandon=abandon, on_late=self._late)
 290 |                  else:
 291 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 292 | -            except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
 293 | -                self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 294 | -                tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 295 | +            except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked by abandon()
 296 | +                booked = b.prompt_usd(prompt, system)
 297 | +                tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 298 | +                                    "ruling 83 (a))"))
 299 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 300 |                                  "deadline_s": deadline_s, "seconds": deadline_s,
 301 |                                  "prompt_chars": len(prompt_text(prompt)),
 302 | -                                "max_tokens": max_tokens})
 303 | +                                "max_tokens": max_tokens, "booked_usd": booked})
 304 |                  continue
 305 |              except RequestRejected as e:
 306 |                  self._settle(key)
 307 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 308 | index 24e4276..dc5fe4a 100644
 309 | --- a/tests/package/proof_ly.py
 310 | +++ b/tests/package/proof_ly.py
 311 | @@ -47,9 +47,9 @@ import speakers as SP  # noqa: E402
 312 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 313 |  OUT = os.path.join(HERE, "proof")
 314 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 315 | -LY_LIMIT_USD = 12.0                # ruling 48 (07:02 Nov 13): $12.00 VENDOR-REPORTED in total for this order (the
 316 | -LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate read ~12x high: $39.49 = $3.46 reported);
 317 | -LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
 318 | +LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
 319 | +LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
 320 | +LY_STOP_USD = 16.0                 # the estimate counts only where a vendor reports none. At $16 no build starts.
 321 |                                     # Each paid call still RESERVES its price-table upper bound while in flight.
 322 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 323 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
 324 | diff --git a/tests/package/test_attest.py b/tests/package/test_attest.py
 325 | index 5263b7a..522a7b9 100644
 326 | --- a/tests/package/test_attest.py
 327 | +++ b/tests/package/test_attest.py
 328 | @@ -72,6 +72,41 @@ class TestAttest(unittest.TestCase):
 329 |          self.assertEqual(AT.quotes(["No single owner controls the bitcoin network"], r, p, ops), [])
 330 |  
 331 |  
 332 | +
 333 | +class TestClass84(unittest.TestCase):
 334 | +    """RULING 84 (orchestrator 20:41 Nov 13): the pre-check's class, as the integrator applies it, on this side's
 335 | +    comparison (the spoken text against the approved text)."""
 336 | +
 337 | +    def k(self, spoken, approved):
 338 | +        return [(x["spoken"], x["approved"], x["class"]) for x in AT.class_84(spoken, approved)]
 339 | +
 340 | +    def test_fillers_on_the_spoken_side_and_one_function_word(self):
 341 | +        self.assertEqual(self.k("So over time, um, I came to think, uh, or the", "So over time, I came to think, so the"),
 342 | +                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
 343 | +        self.assertEqual(self.k("hmm mm er ah uh um yes", "yes"),
 344 | +                         [(f, "", "filler") for f in ("hmm", "mm", "er", "ah", "uh", "um")])
 345 | +        self.assertEqual(self.k("Um, the", "the"), [("um", "", "filler")])         # capitalised, still not a name
 346 | +        self.assertEqual(self.k("came um came to", "came to"),                      # the repetition, filler-free
 347 | +                         [("um", "", "filler"), ("came", "", "immediate repetition")])
 348 | +        self.assertEqual(self.k("I think the Bitcoin", "I think Bitcoin"), [("the", "", "function word")])
 349 | +        self.assertEqual(self.k("the same", "the same"), [])
 350 | +
 351 | +    def test_what_holds(self):
 352 | +        self.assertEqual(self.k("in the house on it", "on the house in it"),        # a second 1-for-1 holds
 353 | +                         [("in", "on", "one function word"), ("on", "in", None)])
 354 | +        self.assertEqual(self.k("we went to the store", "we went to a shop"), [("the store", "a shop", None)])
 355 | +        self.assertEqual(self.k("went in a store", "went to the store"), [("in a", "to the", None)])   # 2-for-2
 356 | +        self.assertEqual(self.k("the", "the um"), [("", "um", None)])              # a filler on the approved side
 357 | +        self.assertEqual(self.k("I paid 5 dollars", "I paid 6 dollars"), [("5", "6", None)])
 358 | +        self.assertEqual(self.k("it is not", "it is"), [("not", "", None)])
 359 | +        self.assertEqual(self.k("um I asked Mike", "I asked mike"), [("um", "", "filler")])   # canon: the same name
 360 | +
 361 | +    def test_ruling_67s_class_is_unchanged(self):
 362 | +        r, p, ops = AT.diff("so um I came", "so I came")
 363 | +        self.assertEqual([AT.carry_class(r, p, o, ("so um I came", "so I came")) for o in ops], [None])
 364 | +        self.assertEqual(AT.FILLERS, frozenset({"um", "uh", "er", "ah", "mm", "hmm"}))
 365 | +
 366 | +
 367 |  class TestReseal(unittest.TestCase):
 368 |      """reseal() on the pin the render held, with its run's records rebuilt in a temporary directory."""
 369 |  
 370 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 371 | index b65d9d9..229792d 100644
 372 | --- a/tests/package/test_lock_precheck.py
 373 | +++ b/tests/package/test_lock_precheck.py
 374 | @@ -118,11 +118,48 @@ class TestDecide(unittest.TestCase):
 375 |                         "I think Bitcoin never dropped like 5, 6%."):                      # a number, a name, a negation
 376 |              d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 377 |              self.assertEqual(d["verdict"], "hold", spoken)
 378 | -            self.assertIn("outside ruling 67's class", d["why"])
 379 | +            self.assertIn("outside ruling 84's class", d["why"])
 380 |          same = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="i think bitcoin only dropped like 5 6%"))
 381 |          self.assertEqual(same["verdict"], "pass")                                          # no canonical difference
 382 |  
 383 |  
 384 | +
 385 | +class TestRuling84(unittest.TestCase):
 386 | +    """RULING 84 (orchestrator 20:41 Nov 13): fillers the second recogniser hears adopt; ONE 1-for-1 function word
 387 | +    adopts (the render's lock keeps its decode's word and records the other reading); two hold; any other
 388 | +    substitution holds. The 20:12 build's held span: [['', 'um'], ['', 'uh'], ['so', 'or']]."""
 389 | +    BREEDLOVE = {"moment_id": "b", "video_id": "uaHNzi-Kgr8", "start": 100.0, "end": 112.6,
 390 | +                 "text": "So over time, I came to think so the money itself was broken."}
 391 | +    s = LP.segments_of([BREEDLOVE])[0]
 392 | +
 393 | +    def test_the_rules_string_is_the_integrators(self):
 394 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84")
 395 | +
 396 | +    def test_the_held_span_of_the_20_12_build_now_adopts(self):
 397 | +        spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 398 | +        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 399 | +        self.assertEqual(d["verdict"], "adopt")
 400 | +        self.assertEqual([(x["spoken"], x["approved"], x["class"]) for x in d["differences"]],
 401 | +                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
 402 | +        row = dict(self.s, **d, entry={"request_id": "r1"})
 403 | +        self.assertIn("ruling 84", LP.attested(row)["rule"])
 404 | +        self.assertIn("ruling 84's class", LP.attested(row)["carried"])
 405 | +
 406 | +    def test_what_still_holds(self):
 407 | +        for spoken in ("So over time, I came to think or the money itself is broken.",    # two 1-for-1 function words
 408 | +                       "So over time, I came to think in a the money itself was broken.", # a 1-for-2 substitution
 409 | +                       "So over time, I came to believe so the money itself was broken.", # a content word
 410 | +                       "So over time, I came to think so the money itself was not broken.",   # a negation
 411 | +                       "So over time, I came to think so the money itself was broken 2."):    # a number
 412 | +            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
 413 | +            self.assertEqual(d["verdict"], "hold", spoken)
 414 | +            self.assertIn("outside ruling 84's class", d["why"])
 415 | +        e = entry(self.s, "adopt_spoken", spoken_text="So over time, I came to think so the money itself was broken.")
 416 | +        e["approved_text"] = "So over time, um, I came to think so the money itself was broken."
 417 | +        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone
 418 | +        self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 419 | +
 420 | +
 421 |  class TestCheck(Dirs):
 422 |      def run_check(self, segs, appear=None, timeout=60.0):
 423 |          t = [0.0]
 424 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 425 | index ffb9037..857959b 100644
 426 | --- a/tests/providers/test_providers.py
 427 | +++ b/tests/providers/test_providers.py
 428 | @@ -78,15 +78,40 @@ class Slow(Fake):
 429 |          return super().complete(prompt, max_tokens, seed, system)
 430 |  
 431 |  
 432 | +class SlowFail(Slow):
 433 | +    """A back-end that fails only after `delay` seconds (a call abandoned at its deadline that never answers)."""
 434 | +
 435 | +    def complete(self, prompt, max_tokens, seed, system=None):
 436 | +        import time as _t
 437 | +        _t.sleep(self.delay)
 438 | +        raise P.Unavailable("HTTP 504 after the deadline")
 439 | +
 440 | +
 441 | +def wait_for(path, kind, timeout=5.0):
 442 | +    """The deadline log's lines once one of `kind` is in it (an abandoned thread ends on its own clock)."""
 443 | +    import time as _t
 444 | +    t0 = _t.time()
 445 | +    while _t.time() - t0 < timeout:
 446 | +        if os.path.exists(path):
 447 | +            with open(path) as f:
 448 | +                log = [json.loads(x) for x in f]
 449 | +            if any(x["kind"] == kind for x in log):
 450 | +                return log
 451 | +        _t.sleep(0.05)
 452 | +    raise AssertionError(f"no {kind} line in {timeout} s")
 453 | +
 454 | +
 455 |  class TestDeadline(unittest.TestCase):
 456 |      """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
 457 | -    back-end, the failover is recorded, and the abandoned call's upper bound is booked as spent."""
 458 | +    back-end, and the failover is recorded. RULING 83 (a) (20:33 Nov 13): the abandoned call is booked at its PROMPT
 459 | +    tokens at the listed input rate (not the upper bound of a full answer); a late answer's own figure replaces it."""
 460 |  
 461 |      def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
 462 |          import tempfile
 463 |          import time as _t
 464 |          with tempfile.TemporaryDirectory() as d:
 465 | -            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
 466 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.8, family="deepseek",
 467 | +                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
 468 |              next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 469 |              r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
 470 |                         spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0,
 471 | @@ -100,12 +125,86 @@ class TestDeadline(unittest.TestCase):
 472 |              self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
 473 |              self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
 474 |              self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
 475 | -            self.assertIn("abandoned at the deadline", rep.tried[0][1])
 476 | +            self.assertIn("abandoned at the deadline; booked at its prompt tokens", rep.tried[0][1])
 477 |              led = json.load(open(os.path.join(d, "SPEND.json")))
 478 | -            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)       # booked, at its upper bound
 479 | -            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"],
 480 | -                                   slow.upper_usd("p", 100), places=6)
 481 | +            booked = slow.prompt_usd("p")                              # ruling 83 (a): 201 tokens at $10 / 1M
 482 | +            self.assertAlmostEqual(booked, 201 * 10 / 1e6, places=9)
 483 | +            self.assertLess(booked, slow.upper_usd("p", 100) / 5)     # not the upper bound of a full answer
 484 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
 485 | +            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"], booked, places=6)
 486 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked + next_.usd({"in": 1000, "out": 100}),
 487 | +                                   places=6)                           # the answer that was used: no vendor figure
 488 | +            self.assertAlmostEqual(log[0]["booked_usd"], booked, places=9)
 489 |              self.assertEqual(led["reserved"], {})                      # no reservation left behind
 490 | +            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")   # then the vendor's figure arrives
 491 | +            late = [x for x in log if x["kind"] == "late_answer"]
 492 | +            self.assertEqual([(x["model"], x["usd_reported"], x["replaced"], x["booked_usd"]) for x in late],
 493 | +                             [("heimdall:deepseek", 0.0123, True, booked)])
 494 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
 495 | +            b = led["by_backend"]["heimdall:deepseek"]
 496 | +            self.assertEqual((b["calls"], b["in"], b["out"], b["reported_calls"], led["late_answers"]),
 497 | +                             (1, 1000, 100, 1, 1))                     # still one call, now with its own counts
 498 | +            self.assertAlmostEqual(b["usd_reported"], 0.0123, places=9)
 499 | +            self.assertAlmostEqual(b["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=6)
 500 | +            self.assertAlmostEqual(led["usd_reported"], 0.0123, places=9)        # the booking is replaced, not added
 501 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], next_.usd({"in": 1000, "out": 100}), places=6)
 502 | +            self.assertAlmostEqual(led["usd_estimate"], slow.usd({"in": 1000, "out": 100}) +
 503 | +                                   next_.usd({"in": 1000, "out": 100}), places=6)
 504 | +            self.assertEqual(led["reserved"], {})
 505 | +
 506 | +    def test_ruling_83_a_a_late_error_leaves_the_booking_and_a_late_answer_without_a_figure_is_its_estimate(self):
 507 | +        import tempfile
 508 | +        for cls, usage, kind in ((SlowFail, None, "late_error"), (Slow, {"in": 3000, "out": 500}, "late_answer")):
 509 | +            with tempfile.TemporaryDirectory() as d:
 510 | +                slow = cls("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.5, family="glm", usage=usage)
 511 | +                next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 512 | +                             usage={"in": 10, "out": 10, "usd_reported": 0.001})
 513 | +                path = os.path.join(d, "DEADLINES.jsonl")
 514 | +                r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]},
 515 | +                           spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0, limit_basis="reported",
 516 | +                           deadline_log=path)
 517 | +                self.assertEqual(r.call("check", "pp", 100, 7, deadline_s=0.1).backend, "heimdall:qwen")
 518 | +                booked = slow.prompt_usd("pp")
 519 | +                self.assertAlmostEqual(r.spent(), booked + 0.001, places=6)   # the reported basis: booking + figure
 520 | +                log = wait_for(path, kind)
 521 | +                led = json.load(open(os.path.join(d, "SPEND.json")))
 522 | +                if kind == "late_error":                               # no answer: the booking stands
 523 | +                    self.assertIn("HTTP 504", [x for x in log if x["kind"] == kind][0]["error"])
 524 | +                    self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=6)
 525 | +                    self.assertNotIn("late_answers", led)
 526 | +                else:                                                  # an answer, no vendor figure: its estimate
 527 | +                    est = slow.usd(usage)
 528 | +                    self.assertAlmostEqual(led["usd_unreported_estimate"], est, places=6)
 529 | +                    self.assertAlmostEqual(r.spent(), est + 0.001, places=6)
 530 | +                    self.assertIsNone([x for x in log if x["kind"] == kind][0]["usd_reported"])
 531 | +
 532 | +    def test_ruling_83_a_the_booking_always_comes_before_the_late_answer(self):
 533 | +        import threading
 534 | +        go, order = threading.Event(), []
 535 | +
 536 | +        def fn():                                                       # answers only once the test lets it
 537 | +            go.wait(5)
 538 | +            order.append("answered")
 539 | +            return "late"
 540 | +
 541 | +        def abandon():
 542 | +            order.append("booked")
 543 | +            go.set()                                                    # the answer races the booking
 544 | +            import time as _t
 545 | +            _t.sleep(0.3)
 546 | +            order.append("booked done")
 547 | +            return {"k": 1}
 548 | +        done = threading.Event()
 549 | +
 550 | +        def late(ab, value, error):
 551 | +            order.append(("late", ab, value, error))
 552 | +            done.set()
 553 | +        with self.assertRaises(P.DeadlineExceeded):
 554 | +            P._within(0.05, fn, on_abandon=abandon, on_late=late)
 555 | +        self.assertTrue(done.wait(5))
 556 | +        self.assertEqual(order, ["booked", "answered", "booked done", ("late", {"k": 1}, "late", None)])
 557 | +        self.assertEqual(P._within(1.0, lambda: 7, on_abandon=abandon, on_late=late), 7)   # in time: neither runs
 558 | +        self.assertEqual(len(order), 4)
 559 |  
 560 |      @staticmethod
 561 |      def lines(path):
 562 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). Only state what
you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- providers.Router.call tries a role's chain of back-ends in order. Each paid call RESERVES its price-table upper
  bound on the spend ledger (a JSON file under an flock) before it runs, and settles after. Ruling 48: the cap is
  checked on the vendors' own reported dollars (usd_reported), plus an estimate for each call whose vendor reports
  none (usd_unreported_estimate). A call with deadline_s runs in a daemon thread (_within). At the deadline it is
  abandoned (Python cannot stop the thread), and the router moves on to the next back-end.
- BEFORE this change, an abandoned call was booked at its UPPER bound as an unreported estimate: every prompt
  character a token, plus the back-end's 16,000-token output floor at $15/1M. That is about $0.26 for a Heimdall call.
  On 20:12 Nov 13, 11 calls abandoned at 120 s booked $2.90 of a build's $2.99. Real answers were $0.09.
- The render's lock pre-check is the integrator's service (ruling 72). It compares the render's lock (its Whisper
  decode) with a second recogniser. Its outcome "adopt_spoken" hands over spoken_text, the second recogniser's text,
  to seal. This side (pipeline/lock_precheck.decide) adopts it only when its OWN check agrees that every difference
  (spoken_text against the approved text) is in the class. Otherwise it holds (fail closed). The integrator's verdict
  comes first: this side never sees adopt_spoken for a span the integrator held.
- pipeline/attest.carry_class is ruling 67's class (an immediate repetition, or all function words; never a number,
  a name or a negation). Ruling 67's re-seal tool (tests/package/reseal_attested.py) uses it too.

The orders:
- RULING 83 (orchestrator 20:33 Nov 13): "(a) A call abandoned at the deadline is booked at its PROMPT tokens at the
  model's listed input rate, not at the upper bound of a full answer; if the vendor later reports a cost for it, the
  reported figure replaces it. (b) The cap for this order becomes $20.00 vendor-reported, stop-and-tell at $16."
  "Outages must not be what spends the budget."
- RULING 84 (orchestrator 20:41 Nov 13): "(a) FILLERS the second recogniser hears and Whisper drops (um, uh, er, ah, mm,
  hmm) are in the adopt class with the speaker's own repetitions: the lock takes the spoken text, verdicts carry over,
  G18 compares against it. (b) ONE function-word disagreement between the two recognisers in a span (so / or, a / the,
  in / on) is the 'one ambiguous token' already ruled acceptable with acoustic identity (numbers, names, negations and
  content words always hold); the lock keeps the render decode's word and records the other reading. Two or more such
  disagreements in one span still hold."
- The integrator's class for ruling 84 (its message, 20:4x Nov 13), difference by difference:
  1. FILLERS = {um, uh, er, ah, mm, hmm} as canon tokens, dropped from the SECOND RECOGNISER's side only. A difference
     that is only fillers is "filler" and adopts. A filler on the lock side alone is not in the class.
  2. A number, negation or name on either side holds.
  3. One token against one token after fillers, both function words and different: "one function word". At most ONE
     per span; two or more hold.
  4. Any other substitution (both sides non-empty after fillers) holds, 2-for-2 and 1-for-2 included.
  5. A pure insert or drop: ruling 67's class unchanged, on the filler-free sequence.
  Its RULES string is "ruling 17 + ruling 72 + ruling 73 + ruling 84". Its spoken_text carries the second
  recogniser's reading of the one function word; the render's lock keeps the decode's word and records the other.
  Its decoder sha also changes. That value arrives only when the integrator's change is live. It is the ONE line of
  this change not in the diff: DECODER in pipeline/lock_precheck.py, a 12-hex constant naming the result files.

The change:
1. pipeline/providers.py:
   - Backend.prompt_tokens_upper (shared with upper_usd) and Backend.prompt_usd (input tokens only).
   - _within(seconds, fn, on_abandon, on_late). At the deadline, on_abandon runs under a lock BEFORE
     DeadlineExceeded is raised. The worker thread takes the same lock when it ends, so the booking always comes
     before on_late.
   - Router.call: abandon() books prompt_usd as an unreported estimate and releases the reservation.
   - Router._late: a late ANSWER is accounted as an on-time answer would have been, in place of the booking: the
     vendor's figure, or with none, the estimate from its own tokens. A late ERROR leaves the booking. One line goes
     to the deadline log either way. The late text is never used or recorded.
2. tests/package/proof_ly.py: LY_LIMIT_USD 12 -> 20, LY_STOP_USD 10 -> 16.
3. pipeline/attest.py: FILLERS and class_84 (new). carry_class is unchanged.
4. pipeline/lock_precheck.py:
   - RULES is the integrator's string;
   - decide() classifies with class_84;
   - attested()'s rule and carried texts name ruling 84.
5. Tests:
   - providers: the prompt-token booking, then the late vendor figure replacing it (no double count); a late error
     leaves the booking; a late answer without a figure books its estimate; the ordering of _within with a racing
     answer.
   - attest: class_84 case by case; carry_class unchanged.
   - lock_precheck: the 20:12 held span (um, uh, so/or) now adopts; two 1-for-1 function words, a 1-for-2, a content
     word, a negation, a number, and a filler on the approved side alone all hold; RULES is the integrator's string.

Design choices to check (each is a decision, say if you think it is wrong):
- A late answer WITHOUT a vendor figure is booked at the estimate from its own tokens (more than the prompt booking).
  The ruling names only the reported figure. This keeps a call that measurably used output tokens from being booked
  below them.
- The reservation is released at the deadline: the guard no longer holds the in-flight remainder of an abandoned
  call.
- Prompt tokens are counted one per character (+200): an abandoned call has no vendor token count.
- This side's class matches the integrator's exactly. The integrator also allowed a wider one ("every token a
  function word or a filler").

Check, against the diff:
- the ledger arithmetic of _late: no double count; usd_unreported_estimate ends exactly as if the call had answered on
  time; usd_reported moves only on a vendor figure;
- the ordering: the booking always precedes the late replacement; no deadlock; what happens when on_abandon raises
  (SpendLimit on an unreadable ledger) and when on_late raises;
- thread safety of ledger writes from the abandoned thread;
- class_84 against the integrator's five rules;
- that nothing the integrator held can be sealed on this side; the cap / stop change.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

