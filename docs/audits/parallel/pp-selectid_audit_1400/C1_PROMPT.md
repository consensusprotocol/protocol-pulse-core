# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1400
# Branch: pp-selectid
# Generated: 2026-11-13 14:03 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1400/C1_STEP.diff (477 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | new file mode 100644
   3 | index 0000000..61fd446
   4 | --- /dev/null
   5 | +++ b/pipeline/attest.py
   6 | @@ -0,0 +1,148 @@
   7 | +"""RULING 67 (orchestrator 14:02 Nov 13): ATTESTED-TEXT RE-SEAL.
   8 | +
   9 | +When the render's decode and the second recogniser AGREE on a span and the pin's text differs, the pin is re-sealed
  10 | +with the attested text (law L-v: the words as spoken). The verdicts already paid for carry over, recorded as carried
  11 | +with the exact diff, ONLY when every differing token is a function word or an immediate repetition of the speaker's
  12 | +own words. If any differing token is a number, a name, a negation or a content word, the clip's step A (both vendors)
  13 | +and the stand-alone verdict are re-judged on the attested text before the seal (not done here: such a diff is
  14 | +refused). The takeaway, title and caption are re-gated only if they quote the changed words (refused here too).
  15 | +
  16 | +The diff is the render's own (pipeline/pinned.adjudicate_lock): canon.canon_tokens of the run's decode against the
  17 | +approved text, difflib.SequenceMatcher(autojunk=False) opcodes. canon.py here is byte-identical to the render's, and
  18 | +critical() is the render's _lv2_critical with its lists. CPU only, no model call. Imports nothing from package.py
  19 | +(package_pin, which the integrator's check imports, must never pull it in)."""
  20 | +import re
  21 | +from difflib import SequenceMatcher
  22 | +
  23 | +import canon
  24 | +
  25 | +# pipeline/pinned.py (the render), LV2_NEGATIONS / LV2_ORDINALS / _lv2_critical, copied verbatim in behaviour
  26 | +LV2_NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
  27 | +                           "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
  28 | +                           "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
  29 | +LV2_ORDINALS = frozenset({"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
  30 | +                          "eleventh", "twelfth", "twentieth", "hundredth", "thousandth", "millionth", "billionth",
  31 | +                          "half", "quarter", "double", "triple", "dozen"})
  32 | +# English closed-class words: articles, demonstratives, pronouns, prepositions, conjunctions, auxiliaries and their
  33 | +# contractions, wh-words. NO negation, number or ordinal is in it (those are law L-v 2's critical tokens).
  34 | +FUNCTION_WORDS = frozenset("""
  35 | +a an the this that these those that's this's there there's here here's
  36 | +i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
  37 | +myself yourself himself herself itself ourselves themselves one's
  38 | +i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll it'll we'll they'll
  39 | +i'd you'd he'd she'd we'd they'd
  40 | +in on at to of for from with by about into onto upon over under up down out off through as like than via per
  41 | +and or but so because if then when while though although whether
  42 | +is are was were be been being am do does did have has had will would can could shall should may might must
  43 | +what which who whom whose why how where
  44 | +""".split())
  45 | +
  46 | +
  47 | +def critical(tok, texts):
  48 | +    """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  49 | +    capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  50 | +    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
  51 | +        return True
  52 | +    for t in texts:
  53 | +        for m in re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or ""):
  54 | +            w = m.group(0)
  55 | +            if w.lower() == tok and w[0].isupper() and w != "I":
  56 | +                before = t[:m.start()].rstrip()
  57 | +                if before and before[-1] not in ".!?":
  58 | +                    return True
  59 | +    return False
  60 | +
  61 | +
  62 | +def diff(run_text, pin_text):
  63 | +    """The render's ruling-17 diff -> (run tokens, pin tokens, the non-equal opcodes (tag, a, b, c, d))."""
  64 | +    r, p = canon.canon_tokens(run_text), canon.canon_tokens(pin_text)
  65 | +    return r, p, [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
  66 | +
  67 | +
  68 | +def carry_class(r, p, op, texts):
  69 | +    """RULING 67: the class of one difference -> "immediate repetition", "function word", or None (re-judge).
  70 | +    An immediate repetition: one side holds tokens the other lacks, and they repeat the tokens right before or right
  71 | +    after them on that side (the speaker's own words said twice). No critical token (L-v 2) is ever carried over."""
  72 | +    tag, a, b, c, d = op
  73 | +    if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  74 | +        return None
  75 | +
  76 | +    def repeats(x, lo, hi):
  77 | +        n = hi - lo
  78 | +        return n > 0 and (x[max(lo - n, 0):lo] == x[lo:hi] or x[hi:hi + n] == x[lo:hi])
  79 | +    if (tag == "delete" and repeats(r, a, b)) or (tag == "insert" and repeats(p, c, d)):
  80 | +        return "immediate repetition"
  81 | +    if r[a:b] + p[c:d] and all(t in FUNCTION_WORDS for t in r[a:b] + p[c:d]):
  82 | +        return "function word"
  83 | +    return None
  84 | +
  85 | +
  86 | +def reads(x, s, lo, hi):
  87 | +    """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
  88 | +    they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
  89 | +    follow them in s."""
  90 | +    xmap = {a + k: b + k for op, a, a2, b, _ in SequenceMatcher(None, x, s, autojunk=False).get_opcodes()
  91 | +            if op == "equal" for k in range(a2 - a)}
  92 | +    idx = list(range(max(lo - 1, 0), min(hi + 1, len(x))))
  93 | +    if not idx or not all(i in xmap for i in idx) or not all(xmap[j] == xmap[i] + 1 for i, j in zip(idx, idx[1:])):
  94 | +        return False
  95 | +    return (lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)
  96 | +
  97 | +
  98 | +def attested_text(pin_text, run_words):
  99 | +    """The minimal edit of the approved text to the run's decode: the approved surface words wherever the tokens are
 100 | +    equal, the run's own decoded words at each difference. run_words: the run's decoded words of the locked span, in
 101 | +    order. Raises ValueError when a difference does not fall on whole words (fail closed). The result's canonical
 102 | +    tokens equal the run decode's exactly (checked)."""
 103 | +    pw = pin_text.split()
 104 | +    rw = [str(w).strip() for w in run_words if str(w).strip()]
 105 | +    pt = [canon.canon_tokens(w) for w in pw]
 106 | +    rt = [canon.canon_tokens(w) for w in rw]
 107 | +    p, r = [t for x in pt for t in x], [t for x in rt for t in x]
 108 | +    if p != canon.canon_tokens(pin_text) or r != canon.canon_tokens(" ".join(rw)):
 109 | +        raise ValueError("the per-word canonical tokens do not add up to the text's (fail closed)")
 110 | +
 111 | +    def word_at(tok_lens):                              # token index -> (word index, first token of that word)
 112 | +        out, k = {}, 0
 113 | +        for i, n in enumerate(tok_lens):
 114 | +            for j in range(n):
 115 | +                out[k + j] = (i, j == 0)
 116 | +            k += n
 117 | +        return out, k
 118 | +    pmap, pn = word_at([len(x) for x in pt])
 119 | +    rmap, rn = word_at([len(x) for x in rt])
 120 | +
 121 | +    def words(wmap, n, lo, hi, side):                  # the whole words covering tokens lo..hi-1
 122 | +        if lo == hi:                                    # an insertion point must fall between two words
 123 | +            if lo < n and not wmap[lo][1]:
 124 | +                raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
 125 | +            return []
 126 | +        if not wmap[lo][1] or (hi < n and not wmap[hi][1]):
 127 | +            raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
 128 | +        return sorted({wmap[t][0] for t in range(lo, hi)})
 129 | +    out = []
 130 | +    for tag, c, d, a, b in SequenceMatcher(None, p, r, autojunk=False).get_opcodes():   # pin -> run
 131 | +        if tag == "equal":
 132 | +            out += [pw[i] for i in words(pmap, pn, c, d, "approved")]
 133 | +        else:
 134 | +            words(pmap, pn, c, d, "approved")
 135 | +            out += [rw[i] for i in words(rmap, rn, a, b, "run")]
 136 | +    text = " ".join(out)
 137 | +    if canon.canon_tokens(text) != r:
 138 | +        raise ValueError("the attested text's tokens are not the run decode's (fail closed)")
 139 | +    return text
 140 | +
 141 | +
 142 | +def quotes(lines, r, p, ops):
 143 | +    """The lines (takeaway, title, caption, ...) that quote the changed words: a line holding, consecutively, the
 144 | +    approved tokens of a difference with one neighbour on each side, or the run's. -> [line text]."""
 145 | +    def has(text, w):
 146 | +        t, n = canon.canon_tokens(text), len(w)
 147 | +        return n > 0 and any(t[i:i + n] == w for i in range(len(t) - n + 1))
 148 | +    hit = []
 149 | +    for line in lines:
 150 | +        for _, a, b, c, d in ops:
 151 | +            if has(line, p[max(c - 1, 0):d + 1]) or has(line, r[max(a - 1, 0):b + 1]):
 152 | +                hit.append(line)
 153 | +                break
 154 | +    return hit
 155 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 156 | index 0573b1d..90c18f3 100644
 157 | --- a/pipeline/package_pin.py
 158 | +++ b/pipeline/package_pin.py
 159 | @@ -70,7 +70,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 160 |                  "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
 161 |                  "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 162 |                                                             # retired by ruling 56: kept so its pins still recompute)
 163 | -                "scorer_verdict")                          # ruling 56: the clip scorer's affirmation, only when sealed
 164 | +                "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 165 | +                "attested")                                # ruling 67: the attested-text re-seal's record (re-sealed)
 166 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 167 |                                                             # separate constant (a test holds them equal): the
 168 |                                                             # integrator's check_pin_only imports this module, which
 169 | diff --git a/tests/package/reseal_attested.py b/tests/package/reseal_attested.py
 170 | new file mode 100644
 171 | index 0000000..f1d8979
 172 | --- /dev/null
 173 | +++ b/tests/package/reseal_attested.py
 174 | @@ -0,0 +1,135 @@
 175 | +#!/usr/bin/env python3
 176 | +"""RULING 67 (orchestrator 14:02 Nov 13): re-seal a pin the render HELD at ruling 17 with the ATTESTED text of the
 177 | +clip it held (pipeline/attest.py). CPU only, no model call; every input is read only.
 178 | +
 179 | +usage: reseal_attested.py PIN RUN_DIR BUILD_DIR
 180 | +  PIN        the sealed pin the render held
 181 | +  RUN_DIR    the render's run that held it: PROVENANCE.json names the pin file it rendered (its seal must be PIN's);
 182 | +             status.json's one hold reads "<video> words <i0>-<i1>: lock text not adjudicated (ruling 17): ... the
 183 | +             second recogniser reads the run decode"; transcripts/<video>.json holds the run's decoded words
 184 | +  BUILD_DIR  the build that sealed PIN: its package.json holds this side's own second recogniser (scribe_v1) reading
 185 | +             of that clip, recorded live by law L-v 2
 186 | +
 187 | +Writes MOMENTS_PIN_ATTESTED.json beside PIN (never over an existing file). Refuses (exit 2, nothing written) unless:
 188 | +the render's hold says its second recogniser reads the run decode; this side's second recogniser reads the run decode
 189 | +at every difference too; every difference is in ruling 67's carry-over class (a function word, or an immediate
 190 | +repetition of the speaker's own words; never a number, a name or a negation); no line quotes the changed words; and
 191 | +the attested text's canonical tokens are the run decode's, so no ruling-17 difference is left. The re-sealed segment
 192 | +carries "attested" (package_pin.SEALED_LATER: sealed): the text it replaced, the exact diff with each difference's
 193 | +class, and that the pin's verdicts and gates carry over."""
 194 | +import copy
 195 | +import json
 196 | +import os
 197 | +import re
 198 | +import sys
 199 | +from datetime import datetime, timezone
 200 | +
 201 | +HERE = os.path.dirname(os.path.abspath(__file__))
 202 | +REPO = os.path.dirname(os.path.dirname(HERE))
 203 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 204 | +import attest as AT  # noqa: E402
 205 | +import package_pin  # noqa: E402
 206 | +
 207 | +HOLD = re.compile(r"(?P<vid>[A-Za-z0-9_-]{11}) words (?P<i0>\d+)-(?P<i1>\d+): lock text not adjudicated \(ruling 17\): "
 208 | +                  r"at .*? the second recogniser reads the run decode \|")
 209 | +
 210 | +
 211 | +def reseal(pin, run_dir, build_rec, build_dir="", now=None):
 212 | +    """-> (the re-sealed pin, a summary). Raises ValueError with the reason (fail closed)."""
 213 | +    mp = pin["moments_package"]
 214 | +    args = lambda segs: (segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"],
 215 | +                         mp.get("btc_screen"))
 216 | +    if package_pin.seal(*args(pin["segments"])) != mp["package_sha256"]:
 217 | +        raise ValueError("the pin does not recompute to its own seal with this package_pin")
 218 | +    prov = open(os.path.join(run_dir, "PROVENANCE.json")).read()
 219 | +    m = re.search(r"--pinned (\S+?\.json)", prov)
 220 | +    if not m:
 221 | +        raise ValueError("the run's PROVENANCE names no pinned file")
 222 | +    with open(m.group(1)) as f:
 223 | +        if json.load(f)["moments_package"]["package_sha256"] != mp["package_sha256"]:
 224 | +            raise ValueError(f"the run rendered another pin ({m.group(1)})")
 225 | +    with open(os.path.join(run_dir, "status.json")) as f:
 226 | +        holds = [h for h in json.load(f).get("holds") or [] if HOLD.search(str(h))]
 227 | +    if len(holds) != 1:
 228 | +        raise ValueError(f"{len(holds)} ruling-17 holds where the second recogniser reads the run decode (need 1)")
 229 | +    h = HOLD.search(str(holds[0]))
 230 | +    vid, i0, i1 = h["vid"], int(h["i0"]), int(h["i1"])
 231 | +    idx = [i for i, s in enumerate(pin["segments"]) if s["video_id"] == vid]
 232 | +    if len(idx) != 1:
 233 | +        raise ValueError(f"{len(idx)} segments on {vid} (need 1)")
 234 | +    seg = pin["segments"][idx[0]]
 235 | +    with open(os.path.join(run_dir, "transcripts", f"{vid}.json")) as f:
 236 | +        words = [str(w["word"]) for w in json.load(f)["words"][i0:i1 + 1]]
 237 | +    run_t, pin_t = " ".join(w.strip() for w in words), seg["approved_text"]
 238 | +    r, p, ops = AT.diff(run_t, pin_t)
 239 | +    if not ops:
 240 | +        raise ValueError("the approved text already reads the run decode")
 241 | +    classes = [AT.carry_class(r, p, o, (run_t, pin_t)) for o in ops]
 242 | +    if None in classes:
 243 | +        raise ValueError("ruling 67: a differing token is a number, a name, a negation or a content word: step A "
 244 | +                         "(both vendors) and the stand-alone verdict are re-judged first: " +
 245 | +                         str([[" ".join(r[a:b]), " ".join(p[c:d])] for (_, a, b, c, d), k in zip(ops, classes)
 246 | +                              if k is None]))
 247 | +    sp = [t for tr in build_rec.get("tried") or [] for at in tr.get("attempts") or []
 248 | +          for t in (at.get("second_pass") or {}).values()
 249 | +          if t.get("video_id") == vid and round(float(t.get("start", -1)), 3) == round(float(seg["start"]), 3)
 250 | +          and round(float(t.get("end", -1)), 3) == round(float(seg["end"]), 3)]
 251 | +    if not sp or sp[0].get("replayed") is not False or not sp[0].get("second_pass_text"):
 252 | +        raise ValueError("this side's second recogniser has no live reading of the clip in the build record")
 253 | +    s = AT.canon.canon_tokens(sp[0]["second_pass_text"])
 254 | +    if not all(AT.reads(r, s, a, b) for _, a, b, _c, _d in ops):
 255 | +        raise ValueError("this side's second recogniser does not read the run decode at every difference")
 256 | +    text = AT.attested_text(pin_t, words)
 257 | +    lines = [x["text"] for x in mp["edl_vo"].get("bridges") or []] + \
 258 | +        ([mp["edl_vo"]["intro"]] if mp["edl_vo"].get("intro") else []) + [mp["title"], mp["caption"]]
 259 | +    q = AT.quotes(lines, r, p, ops)
 260 | +    if q:
 261 | +        raise ValueError(f"ruling 67: these lines quote the changed words and are re-gated first: {q}")
 262 | +    out = copy.deepcopy(pin)
 263 | +    diffs = [{"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 264 | +             for (_, a, b, c, d), k in zip(ops, classes)]
 265 | +    out["segments"][idx[0]].update(approved_text=text, attested={
 266 | +        "rule": "ruling 67 (orchestrator 14:02 Nov 13): the attested-text re-seal",
 267 | +        "was": pin_t, "differences": diffs,
 268 | +        "carried": "every verdict and gate this pin was sealed with, judged on the text it replaces: each difference "
 269 | +                   "is in ruling 67's carry-over class, and no line quotes the changed words",
 270 | +        "render": {"run": os.path.basename(os.path.normpath(run_dir)), "words": [i0, i1], "decode": run_t},
 271 | +        "second_recogniser": {"model": sp[0].get("model"), "text": sp[0]["second_pass_text"], "record": build_dir}})
 272 | +    sha = package_pin.seal(*args(out["segments"]))
 273 | +    old = mp["package_sha256"]
 274 | +    at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
 275 | +    out["story_id"] = re.sub(r"-[0-9a-f]{8}$", "-" + sha[:8], pin["story_id"])
 276 | +    out["approved_at"] = at
 277 | +    out["approval_ref"] = f"{pin.get('approval_ref')}; re-sealed under ruling 67 (the attested text of {vid})"
 278 | +    out["moments_package"].update(package_sha256=sha, resealed={"of": pin["story_id"], "package_sha256": old,
 279 | +                                                                 "rule": "ruling 67", "at": at})
 280 | +    return out, {"segment": idx[0], "video_id": vid, "differences": diffs, "text": text, "was": pin_t,
 281 | +                 "story_id": out["story_id"], "package_sha256": sha}
 282 | +
 283 | +
 284 | +def main(argv=None):
 285 | +    a = argv if argv is not None else sys.argv[1:]
 286 | +    if len(a) != 3:
 287 | +        print(__doc__, file=sys.stderr)
 288 | +        return 2
 289 | +    pin_path, run_dir, build_dir = a
 290 | +    dest = os.path.join(os.path.dirname(os.path.abspath(pin_path)), "MOMENTS_PIN_ATTESTED.json")
 291 | +    try:
 292 | +        if os.path.exists(dest):
 293 | +            raise ValueError(f"{dest} exists (never written over)")
 294 | +        with open(pin_path) as f:
 295 | +            pin = json.load(f)
 296 | +        with open(os.path.join(build_dir, "package.json")) as f:
 297 | +            rec = json.load(f)
 298 | +        out, summary = reseal(pin, run_dir, rec, os.path.relpath(os.path.abspath(build_dir), REPO))
 299 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 300 | +        print(f"REFUSED (ruling 67): {type(e).__name__}: {e}", file=sys.stderr)
 301 | +        return 2
 302 | +    with open(dest, "x") as f:
 303 | +        json.dump(out, f, indent=1)
 304 | +    print(json.dumps(dict(summary, path=os.path.relpath(dest, REPO)), indent=1))
 305 | +    return 0
 306 | +
 307 | +
 308 | +if __name__ == "__main__":
 309 | +    sys.exit(main())
 310 | diff --git a/tests/package/test_attest.py b/tests/package/test_attest.py
 311 | new file mode 100644
 312 | index 0000000..66b5f3c
 313 | --- /dev/null
 314 | +++ b/tests/package/test_attest.py
 315 | @@ -0,0 +1,147 @@
 316 | +#!/usr/bin/env python3
 317 | +"""RULING 67 (orchestrator 14:02 Nov 13): the attested-text re-seal (pipeline/attest.py, tests/package/reseal_attested.py).
 318 | +The fixture is the pin the render held at 13:48 ET (ledger_20261113_183302, clip 3 mKNAcOFMYD4 words 32-73)."""
 319 | +import copy
 320 | +import json
 321 | +import os
 322 | +import sys
 323 | +import tempfile
 324 | +import unittest
 325 | +
 326 | +HERE = os.path.dirname(os.path.abspath(__file__))
 327 | +REPO = os.path.dirname(os.path.dirname(HERE))
 328 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 329 | +sys.path.insert(0, HERE)
 330 | +import attest as AT  # noqa: E402
 331 | +import package_pin  # noqa: E402
 332 | +import reseal_attested as RA  # noqa: E402
 333 | +
 334 | +PIN = os.path.join(HERE, "proof", "ledger_20261113_183302", "MOMENTS_PIN_LEDGER.json")
 335 | +APPROVED = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank "
 336 | +            "owns the money and they could just take it from me. And that's why we Bitcoin.")
 337 | +RUN = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the bank owns "
 338 | +       "the money and they could just take it from me. and that's why that's why we bitcoin.")
 339 | +SCRIBE = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there, 'cause the bank "
 340 | +          "owns the money and they could just take it from me. And that's why, that's why we Bitcoin.")
 341 | +ATTESTED = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there because the bank "
 342 | +            "owns the money and they could just take it from me. And that's why that's why we Bitcoin.")
 343 | +
 344 | +
 345 | +class TestAttest(unittest.TestCase):
 346 | +    def test_the_held_clip_is_the_carry_over_class(self):
 347 | +        r, p, ops = AT.diff(RUN, APPROVED)
 348 | +        self.assertEqual([[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in ops],
 349 | +                         [["in", "you"], ["that's why", ""]])            # the render's own diffs, verbatim
 350 | +        self.assertEqual([AT.carry_class(r, p, o, (RUN, APPROVED)) for o in ops],
 351 | +                         ["function word", "immediate repetition"])
 352 | +        s = AT.canon.canon_tokens(SCRIBE)
 353 | +        self.assertEqual([AT.reads(r, s, a, b) for _, a, b, c, d in ops], [True, True])    # reads the run decode
 354 | +        self.assertEqual([AT.reads(p, s, c, d) for _, a, b, c, d in ops], [False, False])  # not the approved text
 355 | +        self.assertEqual(AT.attested_text(APPROVED, RUN.split()), ATTESTED)
 356 | +        self.assertEqual(AT.diff(RUN, ATTESTED)[2], [])                   # no ruling-17 difference is left
 357 | +
 358 | +    def test_a_number_a_name_a_negation_or_a_content_word_is_never_carried(self):
 359 | +        for run, pin in (("the money is there", "the money is not there"),          # a negation
 360 | +                         ("i paid 3 coins", "i paid 2 coins"),                     # a number
 361 | +                         ("the first block", "the second block"),                  # an ordinal
 362 | +                         ("i punch in my card", "i punch in my code"),             # a content word
 363 | +                         ("as I told Saylor today", "as I told him today"),        # a name (capitalised mid-sentence)
 364 | +                         ("no no it is fine", "no it is fine")):                   # a repeated negation stays critical
 365 | +            r, p, ops = AT.diff(run, pin)
 366 | +            self.assertTrue(ops, (run, pin))
 367 | +            self.assertIn(None, [AT.carry_class(r, p, o, (run, pin)) for o in ops], (run, pin))
 368 | +        r, p, ops = AT.diff("we buy it we buy it now", "we buy it now")            # a repeated phrase: carried
 369 | +        self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], ["immediate repetition"])
 370 | +
 371 | +    def test_the_attested_text_is_a_minimal_edit_with_the_run_tokens(self):
 372 | +        self.assertEqual(AT.attested_text("So it is, Mr. Big.", "so it was mr big".split()),
 373 | +                         "So it was Mr. Big.")                           # the run's whole word replaces "is,"
 374 | +        with self.assertRaises(ValueError):                                       # a difference inside a word
 375 | +            AT.attested_text("a well-known fact", "a well made fact".split())
 376 | +        self.assertEqual(AT.canon.canon_tokens(AT.attested_text(APPROVED, RUN.split())), AT.canon.canon_tokens(RUN))
 377 | +
 378 | +    def test_a_line_quoting_the_changed_words_is_found(self):
 379 | +        r, p, ops = AT.diff(RUN, APPROVED)
 380 | +        self.assertEqual(AT.quotes(["i punch you my code, he says", "no single owner"], r, p, ops),
 381 | +                         ["i punch you my code, he says"])
 382 | +        self.assertEqual(AT.quotes(["No single owner controls the bitcoin network"], r, p, ops), [])
 383 | +
 384 | +
 385 | +class TestReseal(unittest.TestCase):
 386 | +    """reseal() on the pin the render held, with its run's records rebuilt in a temporary directory."""
 387 | +
 388 | +    def setUp(self):
 389 | +        with open(PIN) as f:
 390 | +            self.pin = json.load(f)
 391 | +        self.tmp = tempfile.TemporaryDirectory()
 392 | +        d = self.tmp.name
 393 | +        self.frozen = os.path.join(d, "MOMENTS_PIN_LEDGER_183302.json")
 394 | +        with open(self.frozen, "w") as f:
 395 | +            json.dump(self.pin, f)
 396 | +        os.makedirs(os.path.join(d, "transcripts"))
 397 | +        with open(os.path.join(d, "PROVENANCE.json"), "w") as f:
 398 | +            json.dump({"x": {"owner": f"pulse_check_run 1 (--pinned {self.frozen})"}}, f)
 399 | +        with open(os.path.join(d, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
 400 | +            json.dump({"words": [{"word": "x"}] * 32 + [{"word": " " + w} for w in RUN.split()]}, f)
 401 | +        self.hold("the run decode")
 402 | +        seg = self.pin["segments"][2]
 403 | +        self.rec = {"tried": [{"attempts": [{"second_pass": {"c3": {
 404 | +            "video_id": "mKNAcOFMYD4", "start": seg["start"], "end": seg["end"], "model": "elevenlabs_stt:scribe_v1",
 405 | +            "replayed": False, "second_pass_text": SCRIBE}}}]}]}
 406 | +
 407 | +    def tearDown(self):
 408 | +        self.tmp.cleanup()
 409 | +
 410 | +    def hold(self, side):
 411 | +        with open(os.path.join(self.tmp.name, "status.json"), "w") as f:
 412 | +            json.dump({"holds": [f"pinned: pinned decision rejected: mKNAcOFMYD4 words 32-{32 + len(RUN.split()) - 1}"
 413 | +                                 f": lock text not adjudicated (ruling 17): at [['in', 'you']] the second recogniser "
 414 | +                                 f"reads {side} | run_decode: '...'"]}, f)
 415 | +
 416 | +    def test_the_held_pin_is_re_sealed_with_the_attested_text(self):
 417 | +        out, summary = RA.reseal(self.pin, self.tmp.name, self.rec, "tests/package/proof/ledger_x")
 418 | +        seg, mp = out["segments"][2], out["moments_package"]
 419 | +        self.assertEqual(seg["approved_text"], ATTESTED)
 420 | +        self.assertEqual(seg["attested"]["was"], APPROVED)
 421 | +        self.assertEqual([(x["run"], x["approved"], x["class"]) for x in seg["attested"]["differences"]],
 422 | +                         [("in", "you", "function word"), ("that's why", "", "immediate repetition")])
 423 | +        sha = package_pin.seal(out["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
 424 | +                               mp["gates"], mp.get("btc_screen"))
 425 | +        self.assertEqual((mp["package_sha256"], out["story_id"]), (sha, "moments-ledger_20261113_183302-" + sha[:8]))
 426 | +        self.assertNotEqual(sha, self.pin["moments_package"]["package_sha256"])
 427 | +        self.assertEqual(mp["resealed"]["package_sha256"], self.pin["moments_package"]["package_sha256"])
 428 | +        segs = [{k: v for k, v in s.items() if k != "attested"} for s in out["segments"]]
 429 | +        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
 430 | +                                             mp["caption"], mp["gates"], mp.get("btc_screen")), sha)   # sealed
 431 | +        self.assertEqual([s["approved_text"] for i, s in enumerate(out["segments"]) if i != 2],
 432 | +                         [s["approved_text"] for i, s in enumerate(self.pin["segments"]) if i != 2])   # one clip
 433 | +
 434 | +    def test_it_refuses_without_both_recognisers_or_on_another_pin(self):
 435 | +        self.hold("neither")                                               # the render's recogniser did not attest
 436 | +        with self.assertRaises(ValueError):
 437 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 438 | +        self.hold("the run decode")
 439 | +        rec = copy.deepcopy(self.rec)                                      # this side's recogniser reads the pin
 440 | +        rec["tried"][0]["attempts"][0]["second_pass"]["c3"]["second_pass_text"] = APPROVED
 441 | +        with self.assertRaises(ValueError):
 442 | +            RA.reseal(self.pin, self.tmp.name, rec)
 443 | +        rec["tried"][0]["attempts"][0]["second_pass"]["c3"].update(second_pass_text=SCRIBE, replayed=True)
 444 | +        with self.assertRaises(ValueError):                                # a replayed reading is never evidence
 445 | +            RA.reseal(self.pin, self.tmp.name, rec)
 446 | +        other = copy.deepcopy(self.pin)
 447 | +        other["moments_package"]["package_sha256"] = "0" * 64
 448 | +        with open(self.frozen, "w") as f:
 449 | +            json.dump(other, f)
 450 | +        with self.assertRaises(ValueError):                                # the run rendered another pin
 451 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 452 | +
 453 | +    def test_it_refuses_a_difference_outside_the_carry_over_class(self):
 454 | +        with open(os.path.join(self.tmp.name, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
 455 | +            json.dump({"words": [{"word": "x"}] * 32 + [{"word": w} for w in RUN.replace("code", "card").split()]}, f)
 456 | +        with self.assertRaises(ValueError) as e:
 457 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 458 | +        self.assertIn("re-judged first", str(e.exception))
 459 | +
 460 | +
 461 | +if __name__ == "__main__":
 462 | +    unittest.main()
 463 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 464 | index 876be01..f3230cd 100644
 465 | --- a/tests/package/test_speakers.py
 466 | +++ b/tests/package/test_speakers.py
 467 | @@ -219,7 +219,8 @@ class TestPinCarriesTheSpeaker(unittest.TestCase):
 468 |                  continue
 469 |              n += 1
 470 |              self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
 471 | -                                              mp["caption"], mp["gates"]), mp["package_sha256"], p)
 472 | +                                              mp["caption"], mp["gates"], mp.get("btc_screen")),   # as check_pin_only
 473 | +                             mp["package_sha256"], p)
 474 |          self.assertGreaterEqual(n, 6)                                    # 37c5b5f5, 41f29b1f and the four L-y pins
 475 |          unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
 476 |                     "measured": True}
 477 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the builder that seals the pins the integrator
renders). Your role: a strict reviewer of a path that changes a SEALED pin's text. Only state what you can verify from
the diff; if uncertain, say so; do not guess.

Background (static):
- A pin seals each clip's approved_text, the exact words the render must find. package_pin.seal is sha256 over a
  canonical body: the segments (video, start, end, text, transcript sha, and each SEALED_LATER key a segment carries),
  the VO, the sign-off, title, caption, the gate inventory, and btc_screen.
  - The integrator's check_pin_only imports THIS package_pin.py from the worktree and recomputes every pin's seal.
  - A SEALED_LATER key enters the body only when a segment carries it, so every earlier pin keeps its digest.
- The render's ruling 17 (pipeline/pinned.adjudicate_lock, main tree, read only here):
  - It decodes the clip itself and compares canon.canon_tokens(run decode) with canon_tokens(approved_text) using
    difflib.SequenceMatcher(autojunk=False). No difference: the lock stands.
  - A difference on a number, name or negation always holds.
  - Otherwise its second recogniser (ElevenLabs scribe_v1) decides. If it reads the approved text at every
    difference, the lock takes the approved text; if it reads the run decode, or neither, the render HOLDS.
- 13:48 ET: the render held pin 61fd55d0 at ruling 17 on clip 3 (mKNAcOFMYD4, run words 32-73), with diffs
  [['in','you'], ["that's why",'']] (run decode first). Its second recogniser read the run decode at both places.
  - The approved text came from the word pass's decode: "...I punch you my code ... And that's why we Bitcoin."
  - The speaker says "punch in my code" and "and that's why, that's why we Bitcoin".

The ruling this diff implements (ORCHESTRATOR 14:02 Nov 13, verbatim):
"67. ATTESTED-TEXT RE-SEAL. When the render's decode and the second recogniser AGREE on a span and the pin's text
differs, the pin is re-sealed with the attested text (L-v: the words as spoken). The verdicts already paid for carry
over, recorded as carried with the exact diff, ONLY when every differing token is a function word or an immediate
repetition of the speaker's own words (here: you -> in; a repeated "that's why"). If any differing token is a number, a
name, a negation or a content word, the clip's step A (both vendors) and the stand-alone verdict are re-judged on the
attested text before the seal. The takeaway, title and caption are re-gated only if they quote the changed words.
Here: both differences are in the carry-over class. Re-seal, verify, send to the integrator at once."

The change:
1. pipeline/attest.py (new; imports canon only, never package.py):
   - diff(): the render's own diff (canon.py here is byte-identical to the render's).
   - critical(): the render's _lv2_critical with its negation and ordinal lists: a number, a negation, or a name
     (capitalised mid-sentence in either text).
   - carry_class(): "immediate repetition" (a delete/insert whose tokens repeat the tokens right before or after them
     on that side), or "function word" (every token in a closed FUNCTION_WORDS list with no negation, number or
     ordinal), else None. A critical token is never carried.
   - reads(): the render's reads() rule, i.e. the second recogniser reads x's tokens at that position (with one
     neighbour each side, consecutive).
   - attested_text(): the minimal edit. It keeps the approved surface words where tokens are equal and uses the run's
     own decoded words at each difference. A difference that splits a word raises; the result's canonical tokens must
     equal the run decode's.
   - quotes(): the lines quoting the changed words (the approved or run tokens of a difference, with one neighbour
     each side).
2. tests/package/reseal_attested.py PIN RUN_DIR BUILD_DIR (new). reseal() refuses (ValueError; exit 2, nothing written)
   unless all of these hold:
   - the pin recomputes to its own seal;
   - the run's PROVENANCE names a pinned file whose seal is the pin's;
   - status.json has exactly one ruling-17 hold whose second recogniser "reads the run decode";
   - exactly one segment is on that video;
   - this side's own second recogniser reading of that clip (live, not replayed, from the build record that sealed
     the pin) reads the run decode at every difference;
   - every difference is in the carry-over class (otherwise: "re-judged first");
   - no line (takeaway/bridges/intro, title, caption) quotes the changed words.
   It then sets that segment's approved_text to the attested text and its "attested" record: the text replaced, the
   exact diffs with their classes, what is carried, the render's run and words and decode, and the second
   recogniser's reading. It re-seals, sets story_id with the new sha8, approved_at, and moments_package.resealed {of,
   old sha, rule, at} (outside the seal), and writes MOMENTS_PIN_ATTESTED.json beside the pin (never over a file).
3. package_pin.SEALED_LATER gains "attested". Earlier pins carry no such key, so they recompute unchanged.
4. tests/package/test_speakers.py: its "every earlier pin still recomputes" test called seal() without btc_screen, so
   the first pin carrying btc_screen (the 13:38 pin, committed at 13:45) failed it. It now passes mp.get("btc_screen"),
   as the integrator's check_pin_only does. Test-only.
5. Tests: test_attest.py (7) runs the held clip's real texts:
   - the render's exact diffs and the classes;
   - the second recogniser reads the run decode, not the approved text;
   - the attested text, with no ruling-17 difference left;
   - negation, number, ordinal, content word, name, and a repeated negation are never carried;
   - a word-splitting difference raises; the quoting check;
   - reseal() end to end on the real held pin with its run records rebuilt in a temp dir (the seal recomputes, the
     "attested" record is sealed, only clip 3 changes);
   - the refusals: neither recogniser, this side reads the pin, a replayed reading, another pin, a content word.
   All 12 suites OK.

Real-data dry run, on a copy of the held pin with the real run dir and build record:
- differences [{run "in", approved "you", "function word"}, {run "that's why", approved "", "immediate repetition"}];
- attested text "My biggest fear is that I go to the bank and I punch in my code and the money's not there because
  the bank owns the money and they could just take it from me. And that's why that's why we Bitcoin.";
- re-sealed; no line quotes the changed words.

Stated readings (say so if you read the ruling differently):
- K1: "the render's decode and the second recogniser AGREE": the render's own hold says so ("the second recogniser
  reads the run decode"), AND this side's own live scribe_v1 reading must read the run decode at every difference.
  Both are required (fail closed).
- K2: "immediate repetition of the speaker's own words": the tokens one side lacks repeat the tokens right before or
  right after them. A critical token (L-v 2) is never carried, even when repeated.
- K3: a difference outside the carry-over class, or a line quoting the changed words, REFUSES here. The re-judge path
  the ruling describes for those is not built (not needed for this pin; fail closed).
- K4: the "attested" record is SEALED (a SEALED_LATER key), so the text's provenance cannot be altered without
  breaking the seal. resealed {of, old sha, at} is outside the seal (bookkeeping).
- K5: the minimal edit uses the run's own words at the differences, so the display text keeps the approved casing
  elsewhere; equal canonical tokens make the render's lock stand with no difference.

Check in particular:
- that no path re-seals a text the render's lock would still hold, or carries over a critical or content-word diff;
- the seal compatibility for every earlier pin and for check_pin_only;
- the refusal paths, and that nothing is written on a refusal;
- the minimal edit's correctness (word boundaries, insert/delete/replace);
- the test_speakers fix.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

