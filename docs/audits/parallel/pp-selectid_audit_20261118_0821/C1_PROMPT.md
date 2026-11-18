# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_0821
# Branch: pp-selectid
# Generated: 2026-11-18 08:21 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_0821/C1_STEP.diff (480 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | index 43b30d8..aae6ba7 100644
   3 | --- a/pipeline/lock_precheck.py
   4 | +++ b/pipeline/lock_precheck.py
   5 | @@ -50,7 +50,7 @@ import attest as AT
   6 |  import canon as C
   7 |  
   8 |  RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
   9 | -         "ruling 142")                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
  10 | +         "ruling 142 + ruling 146")             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
  11 |  #   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
  12 |  #   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
  13 |  #   RULING 131
  14 | @@ -61,7 +61,7 @@ RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 10
  15 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  16 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  17 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  18 | -DECODER = "fc204e4a4385"                      # side): the render's own cut placement joins the pre-check (a passing
  19 | +DECODER = "50fa01b400bd"                      # side): the render's own cut placement joins the pre-check (a passing
  20 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  21 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  22 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  23 | @@ -81,6 +81,8 @@ DECODER = "fc204e4a4385"                      # side): the render's own cut plac
  24 |  #   RULING 142, the integrator's batches 111 (the post_live fallback, acquisition-side) + 112 (canon_spans reads '24' '-7,'
  25 |  #   as '24' '7'; word_form takes the contraction [t + "'s"] / [t, 'is' | 'has']; branch r142-postlive 70e78551; one
  26 |  #   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
  27 | +#   RULING 146 (2), the integrator's batch 114 (sentence_law.lock_cut: a hook lead under 80 ms FLAGS, never holds;
  28 | +#   branch r146-g17a 90aa0486; sentence_law.py byte-identical): 50fa01b400bd4231e38a9a8b77f6a0df6f16a57d6f0e22de0eb376788f039256
  29 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  30 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  31 |                          "lock_requests")      # this worktree's; the service only reads it
  32 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  33 | index 0fe03dc..67a0d4c 100644
  34 | --- a/pipeline/package_pin.py
  35 | +++ b/pipeline/package_pin.py
  36 | @@ -49,6 +49,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
  37 |                          "graphics"})                       # RULING 146 (1): the show's own graphics, 16:9 only
  38 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  39 |  REVIEW_FLAGS_MAX = 3
  40 | +PBX_EXCEPTION_CAP = 5   # RULING 147 (orchestrator 08:20 ET Nov 18): the excepted pin's cap (the exception line itself
  41 | +#   never counts); every other pin keeps REVIEW_FLAGS_MAX
  42 |  EXCEPTION_GATE = "pbx_exception"   # RULING 144 (PBX 07:05 ET Nov 18): a named, logged exception to a HARD rule for ONE
  43 |  #   package. Its row is FLAGGED with the exception in plain words; its sentence opens the review flags (the note's top
  44 |  #   line) and is not a doubt about the content, so it never counts toward REVIEW_FLAGS_MAX.
  45 | @@ -419,8 +421,14 @@ def review_problems(mp):
  46 |      over REVIEW_FLAGS_MAX (empty = it holds)."""
  47 |      want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
  48 |      out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
  49 | -    n = content_flags(mp.get("gates"))
  50 | -    return out + ([f"{n} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] if n > REVIEW_FLAGS_MAX else [])
  51 | +    n, cap = content_flags(mp.get("gates")), flags_cap(mp.get("gates"))
  52 | +    return out + ([f"{n} review flags, over {cap} (ruling 136 (2) / 147)"] if n > cap else [])
  53 | +
  54 | +
  55 | +def flags_cap(gates):
  56 | +    """RULINGS 136 (2) / 147: the most content flags a pin may carry: PBX_EXCEPTION_CAP on the one pin that carries a
  57 | +    ruling-144 exception row, REVIEW_FLAGS_MAX on every other."""
  58 | +    return PBX_EXCEPTION_CAP if isinstance(gates, dict) and EXCEPTION_GATE in gates else REVIEW_FLAGS_MAX
  59 |  
  60 |  
  61 |  def content_flags(gates):
  62 | @@ -517,8 +525,8 @@ def to_pin(pk, run_name):
  63 |          screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
  64 |          spotlight_problems(pk) + takeaway_problems(pk)
  65 |      rf = review_flags_of(pk.get("gates"))                 # RULING 137: derived from the sealed gates, at most 3
  66 | -    problems += [f"{content_flags(pk.get('gates'))} review flags, over {REVIEW_FLAGS_MAX} (ruling 136 (2))"] \
  67 | -        if content_flags(pk.get("gates")) > REVIEW_FLAGS_MAX else []
  68 | +    problems += [f"{content_flags(pk.get('gates'))} review flags, over {flags_cap(pk.get('gates'))} (ruling 136 (2) / "
  69 | +                 f"147)"] if content_flags(pk.get("gates")) > flags_cap(pk.get("gates")) else []
  70 |      if problems:
  71 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
  72 |      segs = []
  73 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
  74 | index 708c64a..678dd58 100644
  75 | --- a/pipeline/sentence_law.py
  76 | +++ b/pipeline/sentence_law.py
  77 | @@ -65,6 +65,11 @@ VALLEY_MARGIN_S = 0.010     # (a TIGHTENING) with no quiet run, the minimum is s
  78 |  SHORT_IN_S, SHORT_OUT_S = 0.080, 0.140   # DEC-10 d: a gap shorter than these (the 01:50 numbers, now choosing
  79 |                                           # only the METHOD, never legality) is cut at its envelope minimum
  80 |  LEAD_TARGET_S = 0.250       # preferred lead-in kept before the first onset (Law 14: breath kept)
  81 | +IN_LEAD_MAX_S = 0.600       # RULING 73 (b) (orchestrator 2026-11-13 '18:00', AMENDED '18:40': 600 ms, not 400; the
  82 | +                            # PBX-approved medley reference's hook opens 0.56 s before its first word, and it is the
  83 | +                            # evidence): the in point is never more than this before the first locked word's onset
  84 | +                            # (its decoded start); dead air before it is trimmed to LEAD_TARGET_S. (pin 13949b7c
  85 | +                            # clip_01 opened 3.47 s before 'I', on non-speech)
  86 |  TAIL_TARGET_S = 0.300       # M19: cut_out = min(offset + 0.30, onset - 0.06)
  87 |  LEAD_PAD_S = 0.250          # D1 room-tone pad (6 frames at 24 fps)
  88 |  QUIET_BELOW_SPEECH_DB = 25.0
  89 | @@ -245,8 +250,9 @@ def find_valley(sa, end_a, start_b):
  90 |  
  91 |  # ── boundaries ──
  92 |  
  93 | -def boundary(sa, words, k):
  94 | -    """Sentence boundary between word k and k+1 (k = -1: file head; k = len-1: file end)."""
  95 | +def boundary(sa, words, k, tail=False):
  96 | +    """Sentence boundary between word k and k+1 (k = -1: file head; k = len-1: file end). tail: the boundary AFTER a
  97 | +    lock's last word (ruling 73 (a)): its pause is searched only after that word's decoded end, never inside it."""
  98 |      n = len(words)
  99 |      rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>",
 100 |             "before_word": words[k + 1]["word"] if k + 1 < n else "<file end>"}
 101 | @@ -274,7 +280,9 @@ def boundary(sa, words, k):
 102 |      # with the words before / after them, which can win a tie (DEC-10 audit: abutting-word fixture). Not the
 103 |      # transcript gap: Whisper's word edges can sit 100+ ms off the real pause (v2f hook OUT, Nov 10 D3c)
 104 |      mid = lambda w: (w["start"] + w["end"]) / 2
 105 | -    quiet, lv = find_pause(sa, mid(words[k]), mid(words[k + 1]))
 106 | +    # ruling 73 (a): after a lock's last word the pause is searched from its decoded END: a quiet run inside the locked
 107 | +    # text (13949b7c's hook: 'or [130 ms] reissued.' inside the decoded 'reissued.') is a hesitation, not the end
 108 | +    quiet, lv = find_pause(sa, words[k]["end"] if tail else mid(words[k]), mid(words[k + 1]))
 109 |      point, gap, pause = boundary_geometry(sa, words, k, lv, quiet)     # DEC-10
 110 |      rec.update(levels=lv, pause=pause, quiet_run=quiet, point=point, word_gap=gap)
 111 |      if pause is None:
 112 | @@ -329,7 +337,7 @@ def edge_plan(sa, words, i0, i1, trimmed=None):
 113 |      """Boundaries around words[i0..i1] and the legal cut ranges they allow. trimmed: the lock's trimmed_leading
 114 |      (ruling 33 part 2): the IN edge is the measured pause after that word, and the cut must SIT in its quiet run."""
 115 |      bin_ = trimmed_boundary(sa, words, i0, trimmed) if trimmed else boundary(sa, words, i0 - 1)
 116 | -    bout = boundary(sa, words, i1)
 117 | +    bout = boundary(sa, words, i1, tail=True)
 118 |      plan = {"in": bin_, "out": bout}
 119 |      if bin_["valid"]:
 120 |          p = bin_["pause"]
 121 | @@ -357,10 +365,40 @@ def edge_plan(sa, words, i0, i1, trimmed=None):
 122 |          ok = hi >= lo - 1e-9
 123 |          bout.update(cut_lo=lo, cut_hi=hi, cut=round(min(max(target, lo), hi), 3), cuttable=ok,
 124 |                      reason=None if ok else "no room after the last word")
 125 | +    _ruling73(bin_, bout, words, i0, i1)
 126 |      plan["ok"] = bool(bin_.get("cuttable") and bout.get("cuttable"))
 127 |      return plan
 128 |  
 129 |  
 130 | +def _ruling73(bin_, bout, words, i0, i1):
 131 | +    """RULING 73 (orchestrator 2026-11-13 '18:00'), THE CUT FOLLOWS THE LOCK'S WORDS, on the legal cut ranges (so the cut
 132 | +    table, accepted_cut, hook_lead and G16 all hold to it):
 133 | +    (a) OUT never before the decoded END of the last locked word;
 134 | +    (b) IN never more than IN_LEAD_MAX_S (600 ms, amended '18:40') before the first locked word's decoded start. Dead
 135 | +        air before it is trimmed to LEAD_TARGET_S; the head-lead rule (80 ms for the hook, ruling 28's hook_lead; the
 136 | +        D1 pad) is unchanged."""
 137 | +    if bin_.get("valid") and "cut_lo" in bin_:
 138 | +        bound = round(words[i0]["start"] - IN_LEAD_MAX_S, 3)
 139 | +        if bin_["cut_lo"] < bound - 1e-9:
 140 | +            bin_["ruling73_in"] = {"bound": bound, "was": [bin_["cut_lo"], bin_["cut_hi"], bin_["cut"]]}
 141 | +            hi = max(bin_["cut_hi"], bound) if bin_.get("file_head") else bin_["cut_hi"]   # a file head keeps its quiet
 142 | +            target = bin_["cut"] if bin_["cut"] >= bound else words[i0]["start"] - LEAD_TARGET_S
 143 | +            ok = hi >= bound - 1e-9
 144 | +            bin_.update(cut_lo=bound, cut_hi=round(hi, 3), cut=round(min(max(target, bound), hi), 3),
 145 | +                        cuttable=bool(bin_.get("cuttable")) and ok,
 146 | +                        reason=bin_.get("reason") if ok else
 147 | +                        f"no cut within {int(round(IN_LEAD_MAX_S * 1000))} ms before the first locked word (ruling 73 b)")
 148 | +    if bout.get("valid") and "cut_lo" in bout:
 149 | +        end = round(words[i1]["end"], 3)
 150 | +        if bout["cut_lo"] < end - 1e-9:
 151 | +            bout["ruling73_out"] = {"bound": end, "was": [bout["cut_lo"], bout["cut_hi"], bout["cut"]]}
 152 | +            ok = bout["cut_hi"] >= end - 1e-9
 153 | +            bout.update(cut_lo=end, cut=round(min(max(bout["cut"], end), bout["cut_hi"]), 3),
 154 | +                        cuttable=bool(bout.get("cuttable")) and ok,
 155 | +                        reason=bout.get("reason") if ok else
 156 | +                        "no cut after the decoded end of the last locked word (ruling 73 a)")
 157 | +
 158 | +
 159 |  # ── selection lock ──
 160 |  
 161 |  def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
 162 | @@ -485,6 +523,11 @@ FADE_MIN_S = 0.010          # law L-b: an edge fade shortens down to 10 ms to st
 163 |  FLOOR_PLUS_DB = 3.0         # law L-b: a word has ended (not yet begun) where its envelope is within 3 dB of the
 164 |                              # level at the cut point (the valley minimum or the room tone the cut sits in)
 165 |  EDGE_WORD_MAX_DB = 1.0      # G17c: every frame of an edge word (and its decay) within 1 dB of the unfaded source
 166 | +EDGE_WORD_FLOOR_DBFS = -90.0   # rulings 16 / 18 / 19: G17c and the ruling-18 token check compare a frame only above
 167 | +                               # max(the gap level, this floor). Ruling 19 ('10:51'): -96 dBFS is the 16-bit floor of a LOSSLESS
 168 | +                               # signal, but prepared clips are AAC: measured 2026-11-12 on run pinned_20261112_135315,
 169 | +                               # clip_01 (c1JGheQBPH4), a pause frame at source 15.14 s: source -92.9 dBFS, prepared AAC clip
 170 | +                               # -94.2 dBFS (1.22 dB apart, codec noise); every frame above -90 dBFS of that span within 0.52 dB.
 171 |  
 172 |  
 173 |  def edge_word_bounds(sa, plan, cut_in, cut_out):
 174 | @@ -550,7 +593,8 @@ def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa
 175 |                  continue
 176 |          t0, t1 = (a, min(a + 0.3, cut_out)) if side == "in" else (max(b - 0.3, cut_in), b)
 177 |          ts, ds = sa.sl(t0, t1)
 178 | -        keep = ds > wb["lim_in" if side == "in" else "lim_out"]       # the word, not the gap it sits next to
 179 | +        keep = ds > max(wb["lim_in" if side == "in" else "lim_out"], EDGE_WORD_FLOOR_DBFS)   # the word, not the gap it
 180 | +        # sits next to; never below the 16-bit quantisation floor, where no audio exists to clip (ruling 16)
 181 |          if not keep.any():                                           # fail closed: no word frames to compare
 182 |              det[side] = {"ok": False, "why": "no frames of the edge word in the measured window"}
 183 |              continue
 184 | @@ -686,8 +730,11 @@ def accepted_cut(src, plan, step=HOP_S, sa=None):
 185 |      v = {side: cand["valley"][side] or short(side) for side in ("in", "out")}
 186 |      # the point guard is reachable: a file head / file end edge has no point, and cut_candidates marks it a
 187 |      # valley when cut_accept clears none of its candidates; it keeps the plan's cut there
 188 | -    cut_in = plan["in"]["point"] if v["in"] and plan["in"].get("point") is not None else cand["in"][0]
 189 | -    cut_out = plan["out"]["point"] if v["out"] and plan["out"].get("point") is not None else cand["out"][0]
 190 | +    clamp = lambda b, x: round(min(max(x, b["cut_lo"]), b["cut_hi"]), 3)       # ruling 73: never outside the ranges
 191 | +    cut_in = clamp(plan["in"], plan["in"]["point"] if v["in"] and plan["in"].get("point") is not None
 192 | +                   else cand["in"][0])                                       # b69 c1: every path clamped
 193 | +    cut_out = clamp(plan["out"], plan["out"]["point"] if v["out"] and plan["out"].get("point") is not None
 194 | +                    else cand["out"][0])
 195 |      # DEC-12b amended / law L-b: every machine-cut edge gets a fade that never overlaps its edge word: 2 frames
 196 |      # (83 ms) inside the gap when it fits, shorter down to 10 ms when it does not (human PIN tables keep 20 / 30)
 197 |      fi, fo, _ = edge_fades(sa, plan, cut_in, cut_out)
 198 | @@ -740,6 +787,70 @@ def hook_lead_at(src, c, fade_ms=0):
 199 |      return ht["lead_ms"], ht["onset"]
 200 |  
 201 |  
 202 | +def padded_lead_ms(src, c, cut_out, fade_ms=0):
 203 | +    """G17a's own measure (head_tail) on the head the D1 pad would build: room_tone(src, c, cut_out, LEAD_PAD_S) (the
 204 | +    source's own quietest genuine run, looped, exactly what apply_lead_in_pad prepends) + the audio as cut at c.
 205 | +    None when the source has no room tone (room_tone fails closed). A gated source whose room tone dips to digital
 206 | +    silence at its loop joins measures short: the pad then does not count (measured on pin #1's hook: 20 ms)."""
 207 | +    try:
 208 | +        tone, _ = room_tone(src, c, cut_out, LEAD_PAD_S)
 209 | +    except LawError:
 210 | +        return None
 211 | +    return _head_tail_of(np.concatenate([tone, _cut_head(src, c, fade_ms)]))["lead_ms"]   # the clip's fade, then pad
 212 | +
 213 | +
 214 | +def hook_lead(src, plan, pick, sa=None):
 215 | +    """Ruling 28 (orchestrator 2026-11-13 '01:55'): the hook starts playback, so it keeps >= HEAD_LEAD_MIN_S (80 ms, D1)
 216 | +    of GENUINE quiet before its first word, measured the way G17a measures it (hook_lead_at: head_tail on the audio
 217 | +    as cut). On pin #1 the planner placed the cut by the word gap (400 ms) while the gate measured the sound: a breath,
 218 | +    then digital zeros from a hard edit, left 20-30 ms. Steps:
 219 | +    1. the planned cut keeps >= 80 ms: it stands.
 220 | +    2. the legal candidates inside the same pause (cut_candidates: cut_accept-clean, nearest the plan's target first),
 221 | +       each with its edge fade and neighbour_clear: the first that keeps >= 80 ms is taken.
 222 | +    3. the D1 room-tone pad (LEAD_PAD_S) before a candidate whose quiet is genuine ALL the way from the cut to the
 223 | +       first word, and only when the padded head itself measures >= 80 ms by G17a's measure (padded_lead_ms): the
 224 | +       source's own room tone must count as genuine quiet.
 225 | +    4. otherwise no legal cut can open this hook: "refused" with the measured reason. RULING 146 (2) (orchestrator
 226 | +       2026-11-18 '07:55'): lock_cut then keeps the planned cut, marked "short" (SOFT, flagged), never a refusal. (Pin #1: digital zeros up to about 40 ms before the first word, and the word record puts the word's
 227 | +       start before the zeros end, so no legal cut lies after them.)
 228 | +    Only a hook that is not at a file head comes here (a file head has its own D1 rule in edge_plan). Returns the
 229 | +    record the cut table keeps; "refused" carries why."""
 230 | +    sa = sa or SourceAudio(src)
 231 | +    need = int(round(HEAD_LEAD_MIN_S * 1000))
 232 | +    lead0, onset0 = hook_lead_at(src, pick["cut_in"], pick["fade_in_ms"])
 233 | +    rec = {"need_ms": need, "planned_cut_in": pick["cut_in"], "planned_lead_ms": lead0}
 234 | +    if lead0 >= need:
 235 | +        return {**rec, "cut_in": pick["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": 0.0, "lead_ms": lead0,
 236 | +                "how": "the planned cut keeps the hook's lead"}
 237 | +    tried = []
 238 | +    for c in cut_candidates(src, plan)["in"]:
 239 | +        fi, fo, _ = edge_fades(sa, plan, c, pick["cut_out"])
 240 | +        ok = neighbour_clear(sa, plan, c, pick["cut_out"], fi, fo)[0]
 241 | +        lead, onset = hook_lead_at(src, c, fi * 1000)
 242 | +        joins = (onset is not None and onset > HOP_S + 1e-9            # quiet after the cut (a cut ON a breath
 243 | +                 and lead >= onset * 1000 - HOP_S * 1000 - 1e-6)        # reads onset 0: never a join), genuine to it
 244 | +        tried.append({"cut_in": c, "lead_ms": lead, "onset_s": onset, "neighbour_clear": ok, "fade_in_ms": int(round(fi * 1000)),
 245 | +                      "genuine_from_cut": joins})
 246 | +        if ok and lead >= need:
 247 | +            return {**rec, "cut_in": c, "fade_in_ms": tried[-1]["fade_in_ms"], "pad_s": 0.0, "lead_ms": lead,
 248 | +                    "how": "moved inside the pause to keep 80 ms", "tried": tried}
 249 | +    for t in [t for t in tried if t["neighbour_clear"] and t["genuine_from_cut"]]:   # nearest the target first
 250 | +        padded = padded_lead_ms(src, t["cut_in"], pick["cut_out"], t["fade_in_ms"])
 251 | +        t["padded_lead_ms"] = padded
 252 | +        if padded is not None and padded >= need:
 253 | +            return {**rec, "cut_in": t["cut_in"], "fade_in_ms": t["fade_in_ms"], "pad_s": LEAD_PAD_S,
 254 | +                    "lead_ms": padded, "how": f"the D1 room-tone pad ({LEAD_PAD_S:.3f} s) before the cut measures "
 255 | +                    f"{padded} ms of genuine lead by G17a's own measure", "tried": tried}
 256 | +    padded = [(t["cut_in"], t["padded_lead_ms"]) for t in tried if "padded_lead_ms" in t]
 257 | +    return {**rec, "refused": (f"no legal cut in the pause keeps {need} ms of genuine quiet before the hook's first word "
 258 | +                               f"(best {max((t['lead_ms'] for t in tried), default=lead0)} ms)"
 259 | +                               + (f", and the D1 room-tone pad does not give it either: G17a measures "
 260 | +                                  + ", ".join(f"{m} ms at {c:.3f}" for c, m in padded)
 261 | +                                  + " (the source's own room tone is not genuine quiet: it dips to digital silence)"
 262 | +                                  if padded else ", and no legal cut has genuine quiet from the cut to the word for a "
 263 | +                                                 "D1 pad to join (digital zeros lie between)")), "tried": tried}
 264 | +
 265 | +
 266 |  def write_lock_cut_table(run_dir):
 267 |      """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
 268 |      the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
 269 | @@ -758,32 +869,61 @@ def write_lock_cut_table(run_dir):
 270 |              continue
 271 |          with open(tpath) as f:
 272 |              words = json.load(f)["words"]
 273 | -        plan = edge_plan(SourceAudio(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4")), words,
 274 | -                         lock["i0"], lock["i1"])
 275 |          entry.update(first_word_expected=lock["first_word"], last_word_expected=lock["last_word"],
 276 | -                     selection_lock_sha256=lock["sha256"],
 277 | -                     pause_in=plan["in"].get("pause"), pause_out=plan["out"].get("pause"))
 278 | -        if not plan["ok"]:
 279 | -            why = [f"{s.upper()}: {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
 280 | -                   if not plan[s].get("cuttable")]
 281 | -            cuts.append({**entry, "error": "locked sentence edges not cuttable: " + "; ".join(why)})
 282 | -            continue
 283 | -        pick = accepted_cut(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4"), plan)
 284 | -        if pick is None:
 285 | -            cuts.append({**entry, "error": (
 286 | -                f"no cut inside the locked pauses keeps the neighbour words inaudible (IN {plan['in']['cut_lo']}-"
 287 | -                f"{plan['in']['cut_hi']}, OUT {plan['out']['cut_lo']}-{plan['out']['cut_hi']})")})
 288 | -            continue
 289 | -        cut_in, cut_out = pick["cut_in"], pick["cut_out"]
 290 | -        cuts.append({**entry, "cut_in": cut_in, "cut_out": cut_out, "cut_duration": round(cut_out - cut_in, 3),
 291 | -                     "fade_in_ms": pick["fade_in_ms"], "fade_out_ms": pick["fade_out_ms"],
 292 | -                     "valley_in": pick["valley_in"], "valley_out": pick["valley_out"],
 293 | -                     "lead_in_pad_s": plan["in"]["lead_in_pad_s"], "verified": True})
 294 | +                     selection_lock_sha256=lock["sha256"])
 295 | +        cuts.append({**entry, **lock_cut(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4"), words, lock,
 296 | +                                         label)})
 297 |      with open(os.path.join(run_dir, "cuts_final.json"), "w") as f:
 298 |          json.dump(cuts, f, indent=2)
 299 |      return cuts
 300 |  
 301 |  
 302 | +def lock_cut(src, words, lock, label):
 303 | +    """One locked segment's cut, exactly as the render places it: edge_plan (ruling 73's edges included),
 304 | +    accepted_cut, ruling 28's hook_lead for the hook, ruling 33's onset rule for a trimmed word. -> the fields the
 305 | +    cut table records ('error', verified False, when the segment cannot be cut). The one code path of
 306 | +    write_lock_cut_table and the pin-stage pre-check (ruling 73 (c), pipeline/lock_precheck.py).
 307 | +    RULING 146 (2) (orchestrator 2026-11-18 '07:55'): G17a's quiet before the hook's first word is SOFT. A hook that
 308 | +    hook_lead cannot give 80 ms keeps the planned cut (accepted_cut's, as any clip), its record marked "short" with
 309 | +    the measured reason; the render flags 'The opening clip may start abruptly.' It is never refused for that. A cut
 310 | +    mid-word stays HARD (accepted_cut, G17b, G17c)."""
 311 | +    plan = edge_plan(SourceAudio(src), words, lock["i0"], lock["i1"], trimmed=lock.get("trimmed_leading"))
 312 | +    out = {"pause_in": plan["in"].get("pause"), "pause_out": plan["out"].get("pause")}
 313 | +    if not plan["ok"]:
 314 | +        why = [f"{s.upper()}: {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
 315 | +               if not plan[s].get("cuttable")]
 316 | +        return {**out, "error": "locked sentence edges not cuttable: " + "; ".join(why)}
 317 | +    pick = accepted_cut(src, plan)
 318 | +    if pick is None:
 319 | +        return {**out, "error": (
 320 | +            f"no cut inside the locked pauses keeps the neighbour words inaudible (IN {plan['in']['cut_lo']}-"
 321 | +            f"{plan['in']['cut_hi']}, OUT {plan['out']['cut_lo']}-{plan['out']['cut_hi']})")}
 322 | +    cut_in, cut_out = pick["cut_in"], pick["cut_out"]
 323 | +    fade_in_ms, pad_s, hook, valley_in = pick["fade_in_ms"], plan["in"]["lead_in_pad_s"], None, pick["valley_in"]
 324 | +    if label == "hook" and not plan["in"].get("file_head"):         # ruling 28: the hook keeps 80 ms (D1)
 325 | +        hook = hook_lead(src, plan, pick)
 326 | +        if hook.get("refused"):                                    # ruling 146 (2): SOFT, the planned cut stands
 327 | +            hook = {**{k: v for k, v in hook.items() if k != "refused"}, "short": hook["refused"],
 328 | +                    "cut_in": pick["cut_in"], "fade_in_ms": pick["fade_in_ms"], "pad_s": plan["in"]["lead_in_pad_s"],
 329 | +                    "lead_ms": hook["planned_lead_ms"], "rule": "ruling 146 (2)",
 330 | +                    "how": "the planned cut stands under 80 ms: flagged, not refused (ruling 146 (2))"}
 331 | +        if hook["cut_in"] != pick["cut_in"]:          # a moved cut is a cut_accept-clean candidate, never a
 332 | +            valley_in = False                          # valley (audit batch 56 C1)
 333 | +        cut_in, fade_in_ms, pad_s = hook["cut_in"], hook["fade_in_ms"], hook["pad_s"]
 334 | +    trim = None
 335 | +    if lock.get("trimmed_leading"):                  # ruling 33 part 2: the onset rule on the audio as cut
 336 | +        ok, trim = trimmed_onset(src, cut_in, fade_in_ms)
 337 | +        if not ok:
 338 | +            return {**out, "verified": False, "trimmed_onset": trim, "error": (
 339 | +                f"trimmed leading word (ruling 33 part 2): {plan['in']['trimmed_leading']!r} cannot be cut cleanly: "
 340 | +                f"the audio as cut at {cut_in:.3f} opens on sound (first onset {trim['onset_s']} s)")}
 341 | +    return {**out, "cut_in": cut_in, "cut_out": cut_out, "cut_duration": round(cut_out - cut_in, 3),
 342 | +            "fade_in_ms": fade_in_ms, "fade_out_ms": pick["fade_out_ms"],
 343 | +            "valley_in": valley_in, "valley_out": pick["valley_out"],
 344 | +            "lead_in_pad_s": pad_s, "verified": True, **({"hook_lead": hook} if hook else {}),
 345 | +            **({"trimmed_onset": trim} if trim else {})}
 346 | +
 347 | +
 348 |  # ── G16 SENTENCE_BOUNDARY (pre-render and final gate) ──
 349 |  
 350 |  
 351 | @@ -815,7 +955,7 @@ def gate_g16(run_dir, source_path_fn=None):
 352 |                  words = json.load(f)["words"]
 353 |              src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(seg["video_id"])
 354 |              sa = SourceAudio(src)
 355 | -            plan = edge_plan(sa, words, lock["i0"], lock["i1"])
 356 | +            plan = edge_plan(sa, words, lock["i0"], lock["i1"], trimmed=lock.get("trimmed_leading"))
 357 |              row["in"] = _edge_row(plan["in"], cut["cut_in"], "in", cut)
 358 |              row["out"] = _edge_row(plan["out"], cut["cut_out"], "out", cut)
 359 |              row["errors"] += [f"IN: {row['in']['why']}"] if not row["in"]["pass"] else []
 360 | @@ -825,6 +965,12 @@ def gate_g16(run_dir, source_path_fn=None):
 361 |                                               float(cut.get("fade_in_ms", 20)) / 1000, float(cut.get("fade_out_ms", 30)) / 1000)
 362 |                  row["neighbour"] = det
 363 |                  row["errors"] += [f"{k.upper()}: {v['why']}" for k, v in det.items() if not v["ok"]]
 364 | +            if row["in"]["pass"] and lock.get("trimmed_leading"):   # ruling 33 part 2: the onset rule, as cut
 365 | +                ok, row["trimmed_onset"] = trimmed_onset(src, cut["cut_in"], float(cut.get("fade_in_ms", 20)))
 366 | +                row["errors"] += [] if ok else [
 367 | +                    f"IN: trimmed leading word (ruling 33 part 2): {plan['in']['trimmed_leading']!r} cannot be cut "
 368 | +                    f"cleanly: the audio as cut at {cut['cut_in']:.3f} opens on sound (first onset "
 369 | +                    f"{row['trimmed_onset']['onset_s']} s)"]
 370 |              row["locked"] = f"'{lock['first_word']}' ... '{lock['last_word']}' ({lock['n_words']} words)"
 371 |          row["pass"] = not row["errors"]
 372 |          ok_all &= row["pass"]
 373 | @@ -836,7 +982,8 @@ def _edge_row(b, cut_t, side, cut):
 374 |      r = {"cut": cut_t, "boundary_valid": b.get("valid"), "pause": b.get("pause"), "lexical": b.get("lexical"),
 375 |           "after_word": b.get("after_word"), "before_word": b.get("before_word")}
 376 |      if not b.get("valid"):
 377 | -        return {**r, "pass": False, "why": f"no sentence boundary: {b.get('reason')}"}
 378 | +        what = "trimmed leading word (ruling 33 part 2)" if "trimmed_leading" in b else "no sentence boundary"
 379 | +        return {**r, "pass": False, "why": f"{what}: {b.get('reason')}"}
 380 |      if not b.get("cuttable"):
 381 |          return {**r, "pass": False, "why": f"boundary not cuttable: {b.get('reason')}"}
 382 |      r.update(cut_lo=b["cut_lo"], cut_hi=b["cut_hi"])
 383 | @@ -886,6 +1033,8 @@ def room_tone(src_path, t0, t1, seconds, sr=48000):
 384 |  def apply_lead_in_pad(run_dir, cut, fps, qp):
 385 |      """Prepend cut['lead_in_pad_s'] of room tone + the held first frame to qa/final_<clip>.mp4
 386 |      (atomic replace). The pad is declared in cuts_final.json, so every gate knows it is there."""
 387 | +    import gpu0
 388 | +    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
 389 |      import wave
 390 |      pad = float(cut["lead_in_pad_s"])
 391 |      clip = os.path.join(run_dir, "qa", f"final_{cut['clip_id']}.mp4")
 392 | @@ -910,6 +1059,31 @@ def apply_lead_in_pad(run_dir, cut, fps, qp):
 393 |      return {"pad_s": pad, "room_tone_source_s": info, "wav": os.path.basename(wav)}
 394 |  
 395 |  
 396 | +def span_fidelity(src_path, clip_path, t0, t1, cut_in, pad_s=0.0, sa=None, offset_s=0.0):
 397 | +    """Ruling 18: the source span [t0, t1] is the clip's audio, frame for frame: G17c's comparison (every 10 ms source
 398 | +    frame above EDGE_WORD_FLOOR_DBFS within EDGE_WORD_MAX_DB in the clip, at the best of +-2 hops, every kept frame
 399 | +    compared). offset_s: where the clip starts inside clip_path (0 for a prepared clip). Returns (ok, detail)."""
 400 | +    sa = sa or SourceAudio(src_path)
 401 | +    ca = SourceAudio(clip_path)
 402 | +    base = offset_s - cut_in + pad_s
 403 | +    _, ds = sa.sl(t0, t1)
 404 | +    keep = ds > EDGE_WORD_FLOOR_DBFS
 405 | +    if not keep.any():
 406 | +        return False, {"span": [round(t0, 3), round(t1, 3)], "why": "no audible source frame in the span"}
 407 | +    best = None
 408 | +    for k in range(-2, 3):
 409 | +        _, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
 410 | +        n = min(len(dc), len(ds))
 411 | +        if n == 0 or keep[n:].any():                                 # a source frame left uncompared: no proof
 412 | +            continue
 413 | +        worst = float(np.max(np.abs(dc[:n] - ds[:n])[keep[:n]]))
 414 | +        if best is None or worst < best[0]:
 415 | +            best = (worst, k)
 416 | +    ok = best is not None and best[0] <= EDGE_WORD_MAX_DB
 417 | +    return ok, {"span": [round(t0, 3), round(t1, 3)], "worst_db": None if best is None else round(best[0], 2),
 418 | +                "shift_hops": None if best is None else best[1], "compared_frames": int(keep.sum())}
 419 | +
 420 | +
 421 |  def gate_g17_edges(run_dir, source_path_fn=None):
 422 |      """G17c (law L-b): every machine-cut segment's prepared clip keeps its first and last word, with their
 423 |      natural decay, at full level against the source (edge_word_fidelity). Human PIN tables are measured too.
 424 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 425 | index 34476f1..957d68e 100644
 426 | --- a/tests/package/test_lock_precheck.py
 427 | +++ b/tests/package/test_lock_precheck.py
 428 | @@ -60,7 +60,7 @@ class TestRequest(Dirs):
 429 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 430 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 431 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 432 | -                         "DcUbBkyeh9M.216.054-228.674.fc204e4a4385.json")             # batches 111 + 112's decoder
 433 | +                         "DcUbBkyeh9M.216.054-228.674.50fa01b400bd.json")             # batch 114's decoder
 434 |  
 435 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 436 |          segs = LP.segments_of([HOOK, CLIP])
 437 | @@ -138,7 +138,7 @@ class TestRuling84(unittest.TestCase):
 438 |          """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
 439 |          RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
 440 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 441 | -                                   "ruling 131 + ruling 135 + ruling 142")
 442 | +                                   "ruling 131 + ruling 135 + ruling 142 + ruling 146")
 443 |  
 444 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 445 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 446 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 447 | index 0a732d6..4a9cdb7 100644
 448 | --- a/tests/package/test_ruling_105.py
 449 | +++ b/tests/package/test_ruling_105.py
 450 | @@ -40,7 +40,7 @@ BLOCKWARE = record()
 451 |  class TestTheRules(Dirs):
 452 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 453 |          self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 454 | -        self.assertEqual(LP.DECODER, "fc204e4a4385")                                 # batches 111 + 112 moved it
 455 | +        self.assertEqual(LP.DECODER, "50fa01b400bd")                                 # batch 114 moved it
 456 |          s = LP.segments_of([HOOK])[0]
 457 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 458 |                            at="2026-11-14T21:00:00Z"))
 459 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 460 | index 346acd4..25b32cb 100644
 461 | --- a/tests/package/test_ruling_137.py
 462 | +++ b/tests/package/test_ruling_137.py
 463 | @@ -565,9 +565,14 @@ class TestRuling144TheOneException(unittest.TestCase):
 464 |          self.assertEqual(PP.review_flags_of(g), [self.EXC, "doubt 0", "doubt 1", "doubt 2"])
 465 |          self.assertEqual(PP.content_flags(g), 3)
 466 |          self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
 467 | -        self.assertEqual(len(PP.review_problems({"gates": self.gates(4), "review_flags": PP.review_flags_of(
 468 | -            self.gates(4))})), 1)                                           # a 4th DOUBT still refuses
 469 | +        self.assertEqual(PP.review_problems({"gates": self.gates(4), "review_flags": PP.review_flags_of(
 470 | +            self.gates(4))}), [])                                           # RULING 147: the excepted pin takes 5
 471 |          self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)
 472 | +        five, six = self.gates(5), self.gates(6)                           # RULING 147: 5 on the excepted pin only
 473 | +        self.assertEqual(PP.review_problems({"gates": five, "review_flags": PP.review_flags_of(five)}), [])
 474 | +        self.assertEqual(len(PP.review_problems({"gates": six, "review_flags": PP.review_flags_of(six)})), 1)
 475 | +        four = {k: v for k, v in self.gates(4).items() if k != PP.EXCEPTION_GATE}
 476 | +        self.assertEqual(len(PP.review_problems({"gates": four, "review_flags": PP.review_flags_of(four)})), 1)   # 3
 477 |  
 478 |      def test_the_driver_takes_it_only_named_and_only_in_this_process(self):
 479 |          import proof_ledger as PLG
 480 | 
```

---

pp-selectid: RULING 147 (orchestrator 08:20 ET Nov 18), two small parts, one lockstep:
(a) THE BUILDER'S MIRROR OF THE INTEGRATOR'S BATCH 114 (ruling 146 (2): G17a's hook lead FLAGS in the render's lock,
    never holds): pipeline/sentence_law.py copied BYTE-IDENTICAL from the integrator's staged file (branch r146-g17a
    7c1bed55, sha256 48e5b639fc871f46cb6a1ba1cb671e5e966b2ab66defbc4e6af38bb55d3656b3, its two audit cycles PASS);
    lock_precheck.DECODER 50fa01b400bd (full sha in the comment, the integrator's lock_precheck.decoder_sha()); RULES +
    " + ruling 146". Pre-check entries gain cut["hook_lead_short"], which this side never reads.
(b) THE EXCEPTION PIN'S CAP: "FOR THIS ONE EXCEPTION PIN ONLY the cap is 5 flags (the '12 hours' exception line does not
    count as one). The cap is 3 again for every later build." package_pin.flags_cap(gates) = PBX_EXCEPTION_CAP (5) when the
    gates carry the ruling-144 exception row (EXCEPTION_GATE, written only by the driver under --pbx-exception, sealed
    with the gates), else REVIEW_FLAGS_MAX (3); to_pin and review_problems compare content_flags (the exception line
    excluded) with it. The integrator's check_pin_only reads review_problems from this module, so it follows per pin.
Files: pipeline/sentence_law.py, pipeline/lock_precheck.py, pipeline/package_pin.py, tests/package/test_ruling_137.py,
tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py.
TESTS: the decoder and RULES pins; the excepted pin seals 4 and 5 doubts and refuses 6; a pin without the exception row
refuses 4. Mutations: 4 of 4 killed (the cap both ways, the decoder, the rules).
PLEASE CHECK: (1) can any pin other than the excepted one get the cap of 5? (2) the mirror is byte-identical and nothing
else on this side changes behaviour; (3) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
