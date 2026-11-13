# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-2240
# Branch: pp-selectid
# Generated: 2026-11-12 22:45 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_2240/C1_STEP.diff (1313 lines)
```
   1 | diff --git a/pipeline/house_style.py b/pipeline/house_style.py
   2 | new file mode 100644
   3 | index 00000000..195a6912
   4 | --- /dev/null
   5 | +++ b/pipeline/house_style.py
   6 | @@ -0,0 +1,183 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/house_style.py — ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the HOUSE STYLE of the text a viewer reads or
   9 | +hears. That is the TITLE, the CAPTION and the TAKEAWAY (the one VO line); a BRIDGE / INTRO gets the rules shared by every
  10 | +surface.
  11 | +
  12 | +PBX's standing copy rules: lowercase, no hashtags, no em-dashes, no emoji clutter, no AI-sounding phrasing, no hedging.
  13 | +
  14 | +A deterministic lint, no model:
  15 | +- lint(slot, text) -> [violation];
  16 | +- lint_lines(lines) lints a package's lines;
  17 | +- PROMPT_RULES tells the writer the same rules, built from the same constants so the two never drift.
  18 | +
  19 | +Each violation is {"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}, one per rule id.
  20 | +
  21 | +It is a gate on the writer's text BESIDE the VO-fidelity and context gates (L-q / L-t), never instead of them.
  22 | +
  23 | +Decisions the ruling leaves open:
  24 | +- the caption's "short" is CAPTION_MAX_WORDS (24);
  25 | +- a period after a one-letter abbreviation ("u.s.") ends no sentence;
  26 | +- money words match as STEMS on purpose ("investigation" trips invest\\w*);
  27 | +- "May" the month trips the hedge "may";
  28 | +- a title's first-word contraction ("It's", "That's") is not a possessive.
  29 | +"""
  30 | +import re
  31 | +
  32 | +STYLE_SLOTS = ("title", "caption", "takeaway", "bridge", "intro")   # "bridge_1" etc. and "intro" use the bridge rules
  33 | +
  34 | +# every surface
  35 | +HEDGES = ("may", "might", "could be", "perhaps", "possibly", "arguably")
  36 | +AI_PHRASES = ("it's worth noting", "it is worth noting", "delve", "delves", "delving", "tapestry", "testament to",
  37 | +              "in today's world", "ever-evolving", "game-changer", "navigate the")
  38 | +EM_DASHES = ("—", "–", " -- ")                         # em-dash, en-dash, the typed double hyphen
  39 | +EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF☀-➿⭐⭕️]")
  40 | +HASHTAG_RE = re.compile(r"#\w")
  41 | +
  42 | +# caption
  43 | +CAPTION_MAX_SENTENCES = 2
  44 | +CAPTION_MAX_WORDS = 24             # the builder's reading of "one or two SHORT sentences"
  45 | +SELF_REFERENCE = ("this medley", "this video", "this clip", "these clips", "builds toward", "this montage")
  46 | +MONEY_PATTERNS = (r"opportunit\w*", r"invest\w*", r"profit\w*", r"get\s+rich", r"to\s+the\s+moon", r"buy\s+the\s+dip",
  47 | +                  r"financial\s+advice")   # stems on purpose: "opportunity"/"invest"-style words in any form
  48 | +
  49 | +# title
  50 | +TITLE_MAX_WORDS = 8
  51 | +CONTRACTIONS = ("it's", "that's", "what's", "here's", "there's", "who's", "let's", "he's", "she's", "where's", "how's",
  52 | +                "why's")          # a first word that ends in 's but is not a possessive
  53 | +
  54 | +# takeaway
  55 | +TAKEAWAY_MAX_WORDS = 20
  56 | +TAKEAWAY_OPENERS = ("what stands out", "it's worth noting", "ultimately", "in the end")
  57 | +WHICH_MAKES_RE = re.compile(r"\bwhich\s+makes\b", re.I)
  58 | +STYLE_REFERENCE = ("No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still miss "
  59 | +                   "when they look at Bitcoin.")   # the line PBX appreciated (24 words; the 20-word cap is for new lines)
  60 | +
  61 | +RULE_IDS = ("hashtag", "em-dash", "emoji", "hedge", "ai-phrasing",
  62 | +            "caption-lowercase", "caption-sentences", "caption-words", "self-reference", "money-word",
  63 | +            "title-words", "title-possessive",
  64 | +            "takeaway-words", "takeaway-opener", "which-makes")
  65 | +
  66 | +
  67 | +def _norm(text):
  68 | +    """Curly apostrophes read as straight ones, so "it’s worth noting" is caught as "it's worth noting"."""
  69 | +    return (text or "").replace("’", "'").replace("‘", "'")
  70 | +
  71 | +
  72 | +def _phrase_re(phrase):
  73 | +    """A word-bounded, case-insensitive pattern for a phrase; any run of spaces between its words."""
  74 | +    return re.compile(r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b", re.I)
  75 | +
  76 | +
  77 | +_HEDGE_RES = [(h, _phrase_re(h)) for h in HEDGES]
  78 | +_AI_RES = [(p, _phrase_re(p)) for p in AI_PHRASES]
  79 | +_SELF_RES = [(p, _phrase_re(p)) for p in SELF_REFERENCE]
  80 | +_MONEY_RES = [(p, re.compile(r"\b" + p + r"\b", re.I)) for p in MONEY_PATTERNS]
  81 | +_OPENER_RES = [(o, re.compile(r"^\W*" + r"\s+".join(re.escape(w) for w in o.split()) + r"\b", re.I))
  82 | +               for o in TAKEAWAY_OPENERS]
  83 | +_END_RE = re.compile(r"[.!?]['\")\]]*$")
  84 | +_ABBREV_RE = re.compile(r"(\w\.)+['\")\]]*")
  85 | +
  86 | +
  87 | +def words(text):
  88 | +    return len((text or "").split())
  89 | +
  90 | +
  91 | +def sentence_count(text):
  92 | +    """Sentences = tokens that end a sentence ('.', '!', '?', then closing quotes or brackets), not counting a
  93 | +    one-letter abbreviation ("u.s.", "e.g."); a last sentence without final punctuation still counts."""
  94 | +    toks = (text or "").split()
  95 | +    n = sum(1 for t in toks if _END_RE.search(t) and not _ABBREV_RE.fullmatch(t))
  96 | +    if toks and not _END_RE.search(toks[-1]):
  97 | +        n += 1
  98 | +    return max(n, 1) if toks else 0
  99 | +
 100 | +
 101 | +def _found(res, text):
 102 | +    return [name for name, rx in res if rx.search(text)]
 103 | +
 104 | +
 105 | +def lint(slot, text):
 106 | +    """The house style of one line -> [{"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}], one
 107 | +    violation per broken rule. slot: "title", "caption", "takeaway", "intro" or "bridge*" (the bridge rules)."""
 108 | +    kind = "bridge" if slot == "intro" or slot.startswith("bridge") else slot
 109 | +    if kind not in ("title", "caption", "takeaway", "bridge"):
 110 | +        raise ValueError(f"house_style.lint: unknown slot {slot!r}")
 111 | +    t = _norm(text)
 112 | +    out = []
 113 | +
 114 | +    def v(rule, why):
 115 | +        out.append({"slot": slot, "rule": "STYLE", "detail": f"{rule}: {why}"})
 116 | +
 117 | +    # every surface
 118 | +    tags = re.findall(r"#\w+", t)
 119 | +    if tags:
 120 | +        v("hashtag", ", ".join(repr(x) for x in tags))
 121 | +    dashes = [d for d in EM_DASHES if d in t]
 122 | +    if dashes:
 123 | +        v("em-dash", ", ".join(repr(d.strip() or d) for d in dashes) + " (use a period or a comma)")
 124 | +    emo = EMOJI_RE.findall(t)
 125 | +    if emo:
 126 | +        v("emoji", ", ".join(repr(e) for e in emo))
 127 | +    hedges = _found(_HEDGE_RES, t)
 128 | +    if hedges:
 129 | +        v("hedge", ", ".join(repr(h) for h in hedges) + " (say it plainly or not at all)")
 130 | +    ai = _found(_AI_RES, t)
 131 | +    if ai:
 132 | +        v("ai-phrasing", ", ".join(repr(p) for p in ai))
 133 | +
 134 | +    if kind == "caption":
 135 | +        if t != t.lower():
 136 | +            upper = [w for w in t.split() if w != w.lower()]
 137 | +            v("caption-lowercase", "capitals in " + ", ".join(repr(w) for w in upper[:5]) + " (all lowercase, names too)")
 138 | +        n = sentence_count(t)
 139 | +        if n > CAPTION_MAX_SENTENCES:
 140 | +            v("caption-sentences", f"{n} sentences (at most {CAPTION_MAX_SENTENCES})")
 141 | +        if words(t) > CAPTION_MAX_WORDS:
 142 | +            v("caption-words", f"{words(t)} words (at most {CAPTION_MAX_WORDS})")
 143 | +        selfref = _found(_SELF_RES, t)
 144 | +        if selfref:
 145 | +            v("self-reference", ", ".join(repr(p) for p in selfref) + " (never talk about the video itself)")
 146 | +        money = [m.group(0) for _, rx in _MONEY_RES for m in [rx.search(t)] if m]
 147 | +        if money:
 148 | +            v("money-word", ", ".join(repr(m) for m in money))
 149 | +    elif kind == "title":
 150 | +        if words(t) > TITLE_MAX_WORDS:
 151 | +            v("title-words", f"{words(t)} words (at most {TITLE_MAX_WORDS})")
 152 | +        first = t.split()[0] if t.split() else ""
 153 | +        tok = re.sub(r"^\W+|[^\w']+$", "", first).lower()
 154 | +        if re.fullmatch(r"[\w-]+'s|[\w-]+s'", tok) and tok not in CONTRACTIONS:
 155 | +            v("title-possessive", f"opens with the possessive {first!r} (say the thing: 'The market no government owns')")
 156 | +    elif kind == "takeaway":
 157 | +        if words(t) > TAKEAWAY_MAX_WORDS:
 158 | +            v("takeaway-words", f"{words(t)} words (at most {TAKEAWAY_MAX_WORDS})")
 159 | +        opener = _found(_OPENER_RES, t)
 160 | +        if opener:
 161 | +            v("takeaway-opener", f"opens with {opener[0]!r} (make the point; no throat-clearing)")
 162 | +        if WHICH_MAKES_RE.search(t):
 163 | +            v("which-makes", "a 'which makes ...' clause (end the sentence; say the point in the next one)")
 164 | +    return out
 165 | +
 166 | +
 167 | +def lint_lines(lines):
 168 | +    """The house style of a package's lines ([{"slot", "text", ...}]): every title, caption, takeaway, intro and
 169 | +    bridge* line, each violation under the line's own slot; other slots are not text a viewer gets."""
 170 | +    out = []
 171 | +    for ln in lines or []:
 172 | +        slot = ln.get("slot") or ""
 173 | +        if slot in STYLE_SLOTS or slot.startswith("bridge"):
 174 | +            out += lint(slot, ln.get("text") or "")
 175 | +    return out
 176 | +
 177 | +
 178 | +PROMPT_RULES = (
 179 | +    "HOUSE STYLE (PBX's standing copy rules; a line that breaks one is rejected):\n"
 180 | +    f"- Everywhere: no hashtags; no em-dash or en-dash (use a period or a comma); no emoji; no hedging words "
 181 | +    f"({', '.join(HEDGES)}); no AI-sounding phrasing ({', '.join(AI_PHRASES)}).\n"
 182 | +    f"- CAPTION: all lowercase, names too; one or two short sentences, at most {CAPTION_MAX_WORDS} words in all; never "
 183 | +    f"talk about the video itself ({', '.join(SELF_REFERENCE)}); no money words (opportunity, invest, profit, get "
 184 | +    f"rich, to the moon, buy the dip, financial advice).\n"
 185 | +    f"- TITLE: at most {TITLE_MAX_WORDS} words, plain; never open with a possessive (not \"Bitcoin's overlooked value "
 186 | +    f"comes from ...\" but \"The market no government owns\").\n"
 187 | +    f"- TAKEAWAY: at most {TAKEAWAY_MAX_WORDS} words in short declarative sentences: a point, not a summary; never "
 188 | +    f"open with " + ", ".join(f'"{o}"' for o in TAKEAWAY_OPENERS) + "; no \"which makes ...\" clause.\n"
 189 | +    f"- PBX MAX's voice, for its rhythm, never its words: \"{STYLE_REFERENCE}\"")
 190 | diff --git a/pipeline/package.py b/pipeline/package.py
 191 | index 2ca61824..25437c35 100644
 192 | --- a/pipeline/package.py
 193 | +++ b/pipeline/package.py
 194 | @@ -54,6 +54,7 @@ from concurrent.futures import ThreadPoolExecutor
 195 |  
 196 |  import context_integrity as CI
 197 |  import eligibility as E
 198 | +import house_style as HS
 199 |  import vo_fidelity as VF
 200 |  
 201 |  SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
 202 | @@ -68,7 +69,12 @@ SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is
 203 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 204 |  WRITES = 2
 205 |  COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
 206 | -BUDGET_S, BUDGET_USD = 360.0, 1.50  # orchestrator 05:25 item 5: per package
 207 | +BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
 208 | +BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
 209 | +BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
 210 | +NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
 211 | +WRITER_DEADLINE_S = 300.0          # ruling 5: one writer call never waits more than 5 min; it fails over (deepseek ->
 212 | +                                   # qwen -> xAI in the writer chain) and the failover is recorded
 213 |  VO_DEPENDENT = ("NOT_ENTAILED", "POLARITY", "STRONGER", "FALSE_RELATION")   # context failures the VO's framing causes
 214 |  VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than its speaker said in context: do not "
 215 |                            "frame or restate it",
 216 | @@ -139,7 +145,9 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
 217 |  
 218 |  
 219 |  LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
 220 | -LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
 221 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences
 222 | +LY_TAKEAWAY_MAX_WORDS = HS.TAKEAWAY_MAX_WORDS   # ruling 6 (22:40): at most 20 words for a new takeaway; ruling 10's
 223 | +                                   # MOMENTS_TAKEAWAY_WORD_CAP (30) stays the factory's upper bound in R4
 224 |  LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
 225 |                                     # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
 226 |  LY_BRIDGE_MIN_WORDS = 3            # the shortest bridge a first write budgets for ("Next, on keys.")
 227 | @@ -150,10 +158,10 @@ LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone fai
 228 |  
 229 |  
 230 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 231 | -    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 232 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..LY_TAKEAWAY_MAX_WORDS words (and
 233 |      n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 234 |      extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 235 | -    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 236 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MAX_WORDS / R4_WPS + R4_PREROLL_S)
 237 |      hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 238 |      return round(lo, 2), round(hi, 2)
 239 |  
 240 | @@ -177,11 +185,11 @@ def bridge_budget(content_s):
 241 |  def takeaway_budget(content_s, other=()):
 242 |      """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 243 |      estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 244 | -    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 245 | +    LY_TAKEAWAY_MIN_WORDS, above house style's cap (20, ruling 6) or past R4's share. None when no length lands 60-70 s."""
 246 |      other = [t for t in other if t and t.strip()]
 247 |      fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 248 |      words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 249 | -    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 250 | +    cap = min(LY_TAKEAWAY_MAX_WORDS,
 251 |                r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 252 |      for a, b in (LY_AIM_S, RUNTIME_S):
 253 |          lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 254 | @@ -254,6 +262,17 @@ def signoff(segs, ctx):
 255 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 256 |  
 257 |  
 258 | +def utc_z(when):
 259 | +    """An ISO 8601 time with its offset -> "YYYY-MM-DDTHH:MM:SSZ" (UTC), or None when it cannot be read (the pin then
 260 | +    refuses it: ruling 1, 22:40, recency on the render clock needs the source's publish time)."""
 261 | +    from datetime import datetime, timezone
 262 | +    try:
 263 | +        t = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
 264 | +    except (TypeError, ValueError):
 265 | +        return None
 266 | +    return None if t.tzinfo is None else t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
 267 | +
 268 | +
 269 |  def labels(n):
 270 |      """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 271 |      return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 272 | @@ -268,6 +287,8 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
 273 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 274 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 275 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 276 | +                        "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
 277 | +                        "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
 278 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 279 |                         for lb, m in zip(labels(len(segs)), segs)],
 280 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
 281 | @@ -301,17 +322,19 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
 282 |      (None, 0 = after the hook, or k), title, caption."""
 283 |      segs = [by_id[i] for i in order]
 284 |      n_clips = len(segs) - 1
 285 | -    b, k = fields.get("bridge"), fields.get("bridge_after")
 286 | +    b, k, t = fields.get("bridge"), fields.get("bridge_after"), fields.get("takeaway")
 287 |      if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 288 |          raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 289 | +    if t is None and b is not None:
 290 | +        raise ValueError("a no-voice medley carries no bridge either (ruling 3, 22:40: clips back to back)")
 291 |      mid = b is not None and k > 0
 292 |      lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 293 |          ([dict(b, slot="bridge_1")] if mid else []) + \
 294 | -        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 295 | -         dict(fields["caption"], slot="caption")]
 296 | +        ([dict(t, slot="takeaway")] if t is not None else []) + \
 297 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 298 |      vo = {"intro": b["text"] if b is not None and k == 0 else None,
 299 | -          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 300 | -          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 301 | +          "bridges": ([b["text"]] if mid else []) + ([t["text"]] if t is not None else []),
 302 | +          "bridges_after_clip": ([k] if mid else []) + ([n_clips] if t is not None else [])}
 303 |      pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 304 |      pk["shape"] = "medley"
 305 |      pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 306 | @@ -319,6 +342,7 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
 307 |                                             "text": b["text"], "why": b.get("why"),
 308 |                                             "confirmed_by": fields.get("bridge_confirmed_by")}
 309 |      pk["supply_exception"] = fields.get("supply_exception")
 310 | +    pk["no_voice"] = fields.get("no_voice")
 311 |      return pk
 312 |  
 313 |  
 314 | @@ -437,8 +461,8 @@ in one conversation and never answer each other):
 315 |  
 316 |  After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 317 |  {bridge}Write:
 318 | -- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 319 | -  opinion or conclusion), never a restatement of any clip.
 320 | +- "takeaway": {lo}-{hi} words in short declarative sentences: the point the medley adds up to, as YOUR OWN
 321 | +  commentary (your opinion or conclusion), a point and not a summary, never a restatement of any clip.
 322 |  - "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 323 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 324 |  RULES (a line that breaks one is rejected):
 325 | @@ -452,8 +476,8 @@ RULES (a line that breaks one is rejected):
 326 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 327 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 328 |    "slams", "exposes", "admits", "confirms", "caught".
 329 | -- Write the title and caption in sentence case: capitalise only the first word and real names. A line that names a
 330 | -  show, a person or Bitcoin's price cites the clips it comes from.
 331 | +- A line that names a show, a person or Bitcoin's price cites the clips it comes from.
 332 | +{style}
 333 |  {extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 334 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 335 |  
 336 | @@ -697,8 +721,8 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
 337 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 338 |      prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 339 |                               lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 340 | -                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 341 | -    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 342 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES)
 343 | +    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
 344 |      try:
 345 |          obj = json.loads(r.text.strip())
 346 |          ids = [m["moment_id"] for m in segs]
 347 | @@ -739,7 +763,13 @@ def ly_shape(pk):
 348 |      if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 349 |          fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 350 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 351 | -    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 352 | +    nv = pk.get("no_voice")
 353 | +    if nv is not None:                        # ruling 3 (22:40): clips back to back and the sign-off, NO VO line at all,
 354 | +        if not isinstance(nv, dict) or not str(nv.get("why") or "").strip():   # only after the takeaway failed twice
 355 | +            fails.append("a no-voice medley must record why (ruling 3: the takeaway failed its gates twice)")
 356 | +        if bridges or after or vo.get("intro"):
 357 | +            fails.append("a no-voice medley carries no VO line (ruling 3)")
 358 | +    elif not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 359 |          fails.append("no takeaway after the last clip (L-y 1)")
 360 |      js = joins([sg["label"] for sg in segs])
 361 |      bad = [a for a in after[:-1] if type(a) is not int or not 0 < a < n_clips]
 362 | @@ -805,6 +835,7 @@ def cheap_checks(pk, a_by, levels, now):
 363 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 364 |      if pk.get("shape") == "medley":
 365 |          v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 366 | +        v += HS.lint_lines(pk["lines"])                    # ruling 6 (22:40): PBX's copy rules, deterministic
 367 |      return v, det, dup, rt_ok, r4_res
 368 |  
 369 |  
 370 | @@ -927,7 +958,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 371 |      spend: a callable returning the ledger's USD (dollars per package).
 372 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 373 |      t0 = time.time()
 374 | -    usd0 = spend() if spend else None
 375 | +    usd0 = _spent(spend)
 376 |      ms, why = usable(moments, ctx, delivered, optout)
 377 |      wv, wf = _writers(router)
 378 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 379 | @@ -970,7 +1001,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 380 |          r = None
 381 |          try:
 382 |              r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 383 | -                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed)
 384 | +                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed,
 385 | +                            deadline_s=WRITER_DEADLINE_S)
 386 |              angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles), r
 387 |              break
 388 |          except Exception as e:
 389 | @@ -981,9 +1013,96 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 390 |          return out
 391 |      out.pop("why_none", None)
 392 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 393 | +    out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 394 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 395 | +    writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
 396 | +        {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
 397 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
 398 |      doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 399 | +
 400 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
 401 | +        """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 402 | +        viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 403 | +        dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
 404 | +        must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
 405 | +        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why)."""
 406 | +        nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
 407 | +        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 408 | +        rec["no_voice"] = note = {"tried": True}
 409 | +        order, added, nv_med = list(segs), None, med
 410 | +        content = sum(m["duration_s"] for m in order)
 411 | +        if content > nv_hi:
 412 | +            note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
 413 | +            return None
 414 | +        if content < nv_lo:                                  # "the packager may add a clip"
 415 | +            chans = {m["channel_id"] for m in segs}
 416 | +            for mid in angle["moments"]:
 417 | +                m = cleared.get(mid)
 418 | +                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 419 | +                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 420 | +                    continue
 421 | +                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 422 | +                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 423 | +                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 424 | +                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 425 | +                    continue
 426 | +                order, added = cand, mid
 427 | +                break
 428 | +            if added is None:
 429 | +                note["why_not"] = f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 430 | +                return None
 431 | +            ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
 432 | +            note["medley"] = nv_med
 433 | +            if not ok2 or nv_med["flagged"]:
 434 | +                note["why_not"] = "the line-up with the added clip fails on the clips alone (or has a join to bridge)"
 435 | +                return None
 436 | +        fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 437 | +                  "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 438 | +                  "supply_exception": exception,
 439 | +                  "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
 440 | +                                      "back to back with the sign-off only", "added_clip": added,
 441 | +                               "lineup_before": [m["moment_id"] for m in segs]}}
 442 | +        pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 443 | +        pk["medley"] = nv_med
 444 | +        cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 445 | +        if cheap:
 446 | +            note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
 447 | +            note["violations"] = cheap
 448 | +            return None
 449 | +        with ThreadPoolExecutor(max_workers=8) as nv_pool:
 450 | +            bg2 = {m["moment_id"]: (nv_pool.submit(exclusion_for, router, m, sources, exc),
 451 | +                                    nv_pool.submit(truth_for, router, m, work_dir, tru)) for m in order}
 452 | +            got = {mid: (f[0].result(), f[1].result()) for mid, f in bg2.items()}
 453 | +            if any(e.get("verdict") != "keep" or not t.get("ok") or (t.get("edges") or {}).get("cuttable") is not True
 454 | +                   for e, t in got.values()):
 455 | +                note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
 456 | +                return None
 457 | +            fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
 458 | +        if not fid["ok"] or not cx["ok"]:
 459 | +            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 460 | +            note["violations"] = fid["violations"] + cx["violations"]
 461 | +            return None
 462 | +        coh = dict(nv_med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 463 | +        a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 464 | +        pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
 465 | +                                {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 466 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 467 | +        import package_pin
 468 | +        problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 469 | +        if problems:
 470 | +            note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 471 | +            return None
 472 | +        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
 473 | +                        "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 474 | +                        "context": cx.get("backends"), "coherence": nv_med.get("backend")}
 475 | +        pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 476 | +        pk["seconds"] = round(time.time() - t0, 1)
 477 | +        pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 478 | +        note["result"] = "PACKAGE"
 479 | +        log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
 480 | +            f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 481 | +        return pk
 482 | +
 483 |      with ThreadPoolExecutor(max_workers=8) as pool:
 484 |          for ai, angle in enumerate(angles):
 485 |              dropped, n_lineup = set(), 0
 486 | @@ -1029,11 +1148,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 487 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 488 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 489 |                  extra, relined, w_used, written = "", False, 0, ()
 490 | +                take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 491 |                  while w_used < writes:
 492 |                      w_used += 1
 493 |                      try:
 494 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 495 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup, other=written)
 496 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup,
 497 | +                                                    avoid_vendor=writer_avoid or None, other=written)
 498 |                      except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 499 |                          if join is not None:
 500 |                              dropped.add(segs[join[0] + 1]["moment_id"])
 501 | @@ -1077,6 +1198,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 502 |                      rec["attempts"].append(att)
 503 |                      take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 504 |                      out["takeaways"].append(take)
 505 | +                    last_fields = fields
 506 |                      log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 507 |                          f"words, {pk['runtime_s_estimate']} s): " +
 508 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 509 | @@ -1097,6 +1219,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 510 |                          break
 511 |                      if cheap:
 512 |                          att["violations"] = cheap
 513 | +                        take_failed += take["passed"] is False
 514 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 515 |                          extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 516 |                                                                       if b else " (no takeaway length lands it with this "
 517 | @@ -1112,6 +1235,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 518 |                      log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 519 |                          f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 520 |                          f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 521 | +                    take_failed += take["passed"] is False
 522 |                      if not fid["ok"] or not cx["ok"]:
 523 |                          if fid["ok"] and not framing:
 524 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 525 | @@ -1130,7 +1254,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 526 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 527 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 528 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 529 | -                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 530 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 531 | +                                            style=HS.lint_lines(pk["lines"]))
 532 |                      if not ok_c:
 533 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 534 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 535 | @@ -1158,29 +1283,45 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 536 |                                      "coherence": coh.get("backend")}
 537 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 538 |                      pk["seconds"] = round(time.time() - t0, 1)
 539 | -                    pk["usd"] = round(spend() - usd0, 4) if spend else None
 540 | +                    pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 541 |                      out["packages"].append(pk)
 542 |                      rec["result"] = "PACKAGE"
 543 |                      break
 544 | +                if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 545 | +                        take_failed >= NO_VOICE_AFTER and last_fields is not None:
 546 | +                    nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 547 | +                    if nv is not None:
 548 | +                        out["packages"].append(nv)
 549 | +                        rec["result"] = "PACKAGE (no voice, ruling 3)"
 550 |                  if out["packages"] or not relined:
 551 |                      break
 552 |              if out["packages"]:
 553 |                  break
 554 | -            used_s, used_usd = time.time() - t0, (spend() - usd0) if spend else 0.0
 555 | -            if used_s > BUDGET_S * 2 or used_usd > BUDGET_USD * 2:
 556 | -                out["why_none"] = (f"stopped after angle {ai + 1} of {len(angles)}: {used_s:.0f} s of the "
 557 | -                                   f"{BUDGET_S * 2:.0f} s / ${used_usd:.2f} of the ${BUDGET_USD * 2:.2f} (estimate) "
 558 | -                                   f"per-package budget (05:25 item 5, twice)")
 559 | -                out["budget_stop"] = {"seconds": round(used_s, 1), "usd_estimate": round(used_usd, 4),
 560 | -                                      "angles_tried": ai + 1, "angles": len(angles)}
 561 | +            used_s = time.time() - t0
 562 | +            est, rep = (a - b for a, b in zip(_spent(spend), usd0))
 563 | +            if used_s > BUDGET_WALL_S or rep > BUDGET_USD_REPORTED or est > BUDGET_USD_ESTIMATE:
 564 | +                out["why_none"] = (f"stopped after angle {ai + 1} of {len(angles)}: {used_s:.0f} s of {BUDGET_WALL_S:.0f} "
 565 | +                                   f"s wall / ${rep:.2f} of ${BUDGET_USD_REPORTED:.2f} reported / ${est:.2f} of the "
 566 | +                                   f"${BUDGET_USD_ESTIMATE:.2f} estimate ceiling (ruling 5, 22:40)")
 567 | +                out["budget_stop"] = {"seconds": round(used_s, 1), "usd_reported": round(rep, 4),
 568 | +                                      "usd_estimate": round(est, 4), "angles_tried": ai + 1, "angles": len(angles)}
 569 |                  break
 570 |      out["package"] = out["packages"][0] if out["packages"] else None
 571 |      out["seconds"] = round(time.time() - t0, 1)
 572 | -    out["usd"] = round(spend() - usd0, 4) if spend else None
 573 | +    out["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 574 |      return out
 575 |  
 576 |  
 577 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 578 | +def _spent(spend):
 579 | +    """(estimate, vendor-reported) from the caller's meter. A bare number is the estimate alone; its reported figure
 580 | +    is then taken to be the same (the conservative reading). No meter: (0, 0)."""
 581 | +    if not spend:
 582 | +        return 0.0, 0.0
 583 | +    v = spend()
 584 | +    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 585 | +
 586 | +
 587 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None):
 588 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 589 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 590 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 591 | @@ -1237,4 +1378,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 592 |             if medley is not None else {}),
 593 |          **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 594 |             if shape is not None else {}),
 595 | +        **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 596 | +                                why=[f"{v['slot']}: {v['detail']}" for v in style])}
 597 | +           if style is not None else {}),
 598 |      }
 599 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 600 | index b1da529b..c079de8f 100644
 601 | --- a/pipeline/package_pin.py
 602 | +++ b/pipeline/package_pin.py
 603 | @@ -20,12 +20,14 @@ gates -> release authorisation) renders a moments-first package.
 604 |  import hashlib
 605 |  import json
 606 |  import os
 607 | +import re
 608 |  from datetime import datetime, timezone
 609 |  
 610 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 611 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 612 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 613 | -MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 614 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style")   # L-y (20:30): the clips-alone verdict, the medley's shape;
 615 | +                                                         # ruling 6 (22:40): PBX's copy rules on every line
 616 |  
 617 |  
 618 |  def required_gates(pk):
 619 | @@ -38,13 +40,40 @@ class PinRefused(Exception):
 620 |      """The package may not become a pinned decision."""
 621 |  
 622 |  
 623 | +RECENCY_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
 624 | +
 625 | +
 626 | +def recency_problems(segments):
 627 | +    """[why] for segments that do not state the recency facts the render clock checks (ruling 1, 22:40): every segment
 628 | +    a bool "time_sensitive" and "source_published_at" as "YYYY-MM-DDTHH:MM:SSZ" (UTC) that parses."""
 629 | +    from datetime import datetime
 630 | +    out = []
 631 | +    for i, s in enumerate(segments):
 632 | +        if type(s.get("time_sensitive")) is not bool:
 633 | +            out.append(f"segment {i}: time_sensitive must be true or false (got {s.get('time_sensitive')!r})")
 634 | +        at = s.get("source_published_at")
 635 | +        ok = isinstance(at, str) and bool(RECENCY_AT.match(at))
 636 | +        if ok:
 637 | +            try:
 638 | +                datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")
 639 | +            except ValueError:
 640 | +                ok = False
 641 | +        if not ok:
 642 | +            out.append(f"segment {i}: source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got {at!r})")
 643 | +    return out
 644 | +
 645 | +
 646 |  def seal(segments, edl_vo, signoff, title, caption, gates):
 647 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 648 | -    words, the transcript sha), the VO the renderer will speak (intro, bridges with after_clip), the sign-off, the ONE
 649 | -    title and caption (law L-t), and the gate inventory."""
 650 | +    words, the transcript sha, and since ruling 1 (22:40) time_sensitive and source_published_at), the VO the renderer
 651 | +    will speak (intro, bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate
 652 | +    inventory."""
 653 |      body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
 654 |                            "end": round(float(s["end"]), 3), "text": s["approved_text"],
 655 | -                          "transcript_sha256": s.get("transcript_sha256")} for s in segments],
 656 | +                          "transcript_sha256": s.get("transcript_sha256"),
 657 | +                          "time_sensitive": s.get("time_sensitive"),             # ruling 1 (22:40): the render clock
 658 | +                          "source_published_at": s.get("source_published_at")}   # checks L-v 3 on these
 659 | +                         for s in segments],
 660 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
 661 |                                                               for b in edl_vo.get("bridges") or []]},
 662 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 663 | @@ -96,7 +125,8 @@ def line_problems(pk):
 664 |  
 665 |  def to_pin(pk, run_name):
 666 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 667 | -                                                                     for x in line_problems(pk)]
 668 | +                                                                     for x in line_problems(pk)] + \
 669 | +        recency_problems(pk.get("segments") or [])
 670 |      if problems:
 671 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 672 |      segs = []
 673 | @@ -104,6 +134,7 @@ def to_pin(pk, run_name):
 674 |          segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
 675 |                       "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 676 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 677 | +                     "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 678 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 679 |      edl_vo = {"intro": pk["vo"]["intro"],
 680 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 681 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 682 | index 6e8220ca..e65bca1c 100644
 683 | --- a/pipeline/providers.py
 684 | +++ b/pipeline/providers.py
 685 | @@ -221,6 +221,32 @@ class OpenAIBackend(Backend):
 686 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 687 |  
 688 |  
 689 | +class DeadlineExceeded(Exception):
 690 | +    """A back-end gave no answer within the caller's deadline (orchestrator 22:40 ruling 5: one writer call never waits
 691 | +    more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 692 | +
 693 | +
 694 | +def _within(seconds, fn):
 695 | +    """fn() in a daemon thread, waited for at most `seconds`. -> its value, or its own exception re-raised, or
 696 | +    DeadlineExceeded. An abandoned thread finishes (or times out) on its own; its result is dropped unrecorded."""
 697 | +    import threading
 698 | +    box, done = {}, threading.Event()
 699 | +
 700 | +    def run():
 701 | +        try:
 702 | +            box["value"] = fn()
 703 | +        except BaseException as e:            # handed back to the caller below
 704 | +            box["error"] = e
 705 | +        finally:
 706 | +            done.set()
 707 | +    threading.Thread(target=run, daemon=True, name="pp-deadline").start()
 708 | +    if not done.wait(seconds):
 709 | +        raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 710 | +    if "error" in box:
 711 | +        raise box["error"]
 712 | +    return box["value"]
 713 | +
 714 | +
 715 |  def _num(x):
 716 |      import math
 717 |      return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
 718 | @@ -642,7 +668,7 @@ class Router:
 719 |          os.replace(tmp, path)
 720 |  
 721 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 722 | -             avoid_family=None):
 723 | +             avoid_family=None, deadline_s=None):
 724 |          av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
 725 |          tried, notices = [], []
 726 |          for name in self.chain(role):
 727 | @@ -662,13 +688,21 @@ class Router:
 728 |              if self.replay:
 729 |                  tried.append((name, "replay: not recorded"))
 730 |                  continue
 731 | -            key = self._reserve(b, b.upper_usd(prompt, max_tokens, system))
 732 | +            upper = b.upper_usd(prompt, max_tokens, system)
 733 | +            key = self._reserve(b, upper)
 734 |              if b.vendor == "heimdall":
 735 |                  n = self.heimdall_tripwire()
 736 |                  if n:
 737 |                      notices.append(n)
 738 |              try:
 739 | -                text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 740 | +                if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 741 | +                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system))
 742 | +                else:
 743 | +                    text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 744 | +            except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
 745 | +                self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 746 | +                tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 747 | +                continue
 748 |              except RequestRejected as e:
 749 |                  self._settle(key)
 750 |                  tried.append((name, f"refused this request: {e}"))
 751 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 752 | index 23286dd1..40779901 100644
 753 | --- a/tests/package/proof_ly.py
 754 | +++ b/tests/package/proof_ly.py
 755 | @@ -55,7 +55,9 @@ RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448
 756 |          "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
 757 |  NEWEST = RUNS[0]
 758 |  FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
 759 | -WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
 760 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b",      # ruling 5 (22:40): a writer
 761 | +           "xai:grok-4.20-0309-reasoning"]       # call over 5 min fails over deepseek -> qwen -> xAI; the writes then
 762 | +                                                 # stay on the angle's vendor and every verdict avoids it (L-x)
 763 |  SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
 764 |  
 765 |  
 766 | @@ -145,7 +147,8 @@ def run_one(run, router, work_dir, log, own, used=None, as_of_now=False):
 767 |      u0 = dict(used) if used is not None else None
 768 |      t0 = time.time()
 769 |      res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
 770 | -                   work_dir=work_dir, store=os.path.join(OUT, run, f"step_a{suffix}.json"), spend=lambda: own["est"])
 771 | +                   work_dir=work_dir, store=os.path.join(OUT, run, f"step_a{suffix}.json"),
 772 | +                   spend=lambda: (own["est"], own["best"]))       # ruling 5: the budget reads the reported cost
 773 |      e1, b1 = own["est"], own["best"]
 774 |      res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
 775 |                 usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
 776 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 777 | index 61cb0ed8..34762dcd 100644
 778 | --- a/tests/package/test_angles.py
 779 | +++ b/tests/package/test_angles.py
 780 | @@ -55,7 +55,7 @@ class TestAngles(unittest.TestCase):
 781 |          seg = PK.lineup_for(angle(["a", "d", "b", "c"], "a"), by)
 782 |          self.assertIsNotNone(seg)
 783 |          self.assertNotIn("d", [m["moment_id"] for m in seg[1:-1]])                # 6 s: never in the middle
 784 | -        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 16.0), pm("d", "D", 6.0))}
 785 | +        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 19.0), pm("d", "D", 6.0))}
 786 |          seg2 = PK.lineup_for(angle(["a", "b", "d"], "a"), by2)
 787 |          self.assertEqual([m["moment_id"] for m in seg2], ["a", "b", "d"])         # allowed as the last (the punchline)
 788 |  
 789 | @@ -128,7 +128,8 @@ class TestPinAndTruth(unittest.TestCase):
 790 |                  "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 791 |                            {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 792 |                  "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 793 | -                              "transcript_sha256": "t", "url_30s_before": "u"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 794 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 795 | +                              "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 796 |  
 797 |      def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
 798 |          pin = package_pin.to_pin(self.pk(), "r")
 799 | @@ -156,6 +157,36 @@ class TestPinAndTruth(unittest.TestCase):
 800 |          with self.assertRaises(package_pin.PinRefused):
 801 |              package_pin.to_pin(p, "r")
 802 |  
 803 | +    def test_every_pin_segment_states_its_recency_facts_inside_the_seal(self):
 804 | +        """Ruling 1 (22:40): the render clock checks L-v 3 on pin.segments[i].time_sensitive / source_published_at;
 805 | +        both are sealed, and a pin without them is never written (the render side holds such a run too)."""
 806 | +        pin = package_pin.to_pin(self.pk(), "r")
 807 | +        self.assertEqual([(s["time_sensitive"], s["source_published_at"]) for s in pin["segments"]],
 808 | +                         [(False, "2026-11-12T01:00:00Z")] * 2)
 809 | +        mp = pin["moments_package"]
 810 | +        for key, val in (("time_sensitive", True), ("source_published_at", "2026-11-12T01:00:01Z")):
 811 | +            segs = [dict(pin["segments"][0], **{key: val})] + pin["segments"][1:]
 812 | +            self.assertNotEqual(mp["package_sha256"], package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"],
 813 | +                                                                        mp["title"], mp["caption"], mp["gates"]), key)
 814 | +        for key, bad in (("time_sensitive", None), ("time_sensitive", "true"), ("time_sensitive", 1),
 815 | +                         ("source_published_at", None), ("source_published_at", "2026-11-12T01:00:00+00:00"),
 816 | +                         ("source_published_at", "2026-11-12 01:00:00Z"), ("source_published_at", "2026-13-40T01:00:00Z")):
 817 | +            p = self.pk()
 818 | +            p["segments"] = [dict(p["segments"][0], **{key: bad})] + p["segments"][1:]
 819 | +            with self.assertRaises(package_pin.PinRefused) as cm:
 820 | +                package_pin.to_pin(p, "r")
 821 | +            self.assertIn(f"segment 0: {key}", str(cm.exception))
 822 | +        p = self.pk()
 823 | +        p["segments"] = [{k: v for k, v in p["segments"][0].items() if k != "source_published_at"}] + p["segments"][1:]
 824 | +        with self.assertRaises(package_pin.PinRefused):
 825 | +            package_pin.to_pin(p, "r")
 826 | +
 827 | +    def test_the_package_states_each_clips_recency_from_its_moment(self):
 828 | +        self.assertEqual(PK.utc_z("2026-11-11T13:03:23-05:00"), "2026-11-11T18:03:23Z")
 829 | +        self.assertEqual(PK.utc_z("2026-11-11T18:03:23Z"), "2026-11-11T18:03:23Z")
 830 | +        self.assertIsNone(PK.utc_z("2026-11-11T18:03:23"))                       # no offset: not a time we can place
 831 | +        self.assertIsNone(PK.utc_z(None))
 832 | +
 833 |      def test_the_second_pass_compares_both_ways_inside_the_clip_only(self):
 834 |          self.assertFalse(TT.compare("Bitcoin is going to zero.", "Bitcoin is not going to zero.")["ok"])   # a dropped not
 835 |          self.assertFalse(TT.compare("Bitcoin is not going to zero.", "Bitcoin is going to zero.")["ok"])
 836 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
 837 | index 3f5e7b23..71cc0330 100644
 838 | --- a/tests/package/test_gates.py
 839 | +++ b/tests/package/test_gates.py
 840 | @@ -22,7 +22,7 @@ class Canned:
 841 |          self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []
 842 |  
 843 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 844 | -             avoid_family=None):
 845 | +             avoid_family=None, deadline_s=None):
 846 |          self.calls.append((role, avoid_vendor, avoid_family))
 847 |          q = self.answers.get(role)
 848 |          if not q:
 849 | diff --git a/tests/package/test_house_style.py b/tests/package/test_house_style.py
 850 | new file mode 100644
 851 | index 00000000..3d75022d
 852 | --- /dev/null
 853 | +++ b/tests/package/test_house_style.py
 854 | @@ -0,0 +1,166 @@
 855 | +#!/usr/bin/env python3
 856 | +"""pipeline/house_style.py, ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the house style of the title, the caption and the
 857 | +takeaway (bridges get the rules shared by every surface). Must-fail and must-pass cases; the 41f29b1f pin's own lines
 858 | +are the fixtures the ruling names. Offline, no model."""
 859 | +import os
 860 | +import sys
 861 | +import unittest
 862 | +
 863 | +HERE = os.path.dirname(os.path.abspath(__file__))
 864 | +REPO = os.path.dirname(os.path.dirname(HERE))
 865 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 866 | +import house_style as HS  # noqa: E402
 867 | +
 868 | +PIN_41F29B1F = {   # the delivered medley's lines (tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json)
 869 | +    "caption": "A market that no single authority can switch off may be the most mispriced opportunity in finance, and "
 870 | +               "that is the point this medley builds toward.",
 871 | +    "title": "Bitcoin's overlooked value comes from a market no government owns",
 872 | +    "takeaway": "What stands out is how rare it is for any asset to be priced by everyone and controlled by no one, which "
 873 | +                "makes the usual political drama feel irrelevant.",
 874 | +}
 875 | +
 876 | +
 877 | +def ids(slot, text):
 878 | +    return {v["detail"].split(":")[0] for v in HS.lint(slot, text)}
 879 | +
 880 | +
 881 | +class TestTheDeliveredLines(unittest.TestCase):
 882 | +    def test_the_41f29b1f_caption_fails_four_rules(self):
 883 | +        got = ids("caption", PIN_41F29B1F["caption"])
 884 | +        self.assertTrue({"caption-lowercase", "hedge", "self-reference", "money-word"} <= got, got)
 885 | +        self.assertIn("caption-words", got)                     # 26 words, over 24
 886 | +        self.assertGreaterEqual(len(got), 4)
 887 | +
 888 | +    def test_the_41f29b1f_title_fails_possessive_and_length(self):
 889 | +        self.assertEqual(ids("title", PIN_41F29B1F["title"]), {"title-possessive", "title-words"})
 890 | +
 891 | +    def test_the_41f29b1f_takeaway_fails_opener_which_makes_and_length(self):
 892 | +        self.assertEqual(ids("takeaway", PIN_41F29B1F["takeaway"]),
 893 | +                         {"takeaway-opener", "which-makes", "takeaway-words"})
 894 | +
 895 | +    def test_the_style_reference_fails_only_its_length(self):
 896 | +        self.assertEqual(len(HS.STYLE_REFERENCE.split()), 24)
 897 | +        self.assertEqual(ids("takeaway", HS.STYLE_REFERENCE), {"takeaway-words"})
 898 | +
 899 | +
 900 | +class TestMustPass(unittest.TestCase):
 901 | +    def test_plain_lines_pass(self):
 902 | +        self.assertEqual(HS.lint("title", "The market no government owns"), [])
 903 | +        self.assertEqual(HS.lint("caption", "no authority. that's the design."), [])
 904 | +        self.assertEqual(HS.lint("bridge", "Next, on keys."), [])
 905 | +        self.assertEqual(HS.lint("bridge_1", "Next, on keys."), [])
 906 | +        self.assertEqual(HS.lint("intro", "Next, on keys."), [])
 907 | +        self.assertEqual(HS.lint("takeaway", "No ruler. Just rules nobody gets to bend."), [])
 908 | +
 909 | +    def test_pbx_s_own_caption_fails_only_the_sentence_count(self):
 910 | +        self.assertEqual(ids("caption", "no authority. that's the design. three clips, links below."),
 911 | +                         {"caption-sentences"})
 912 | +
 913 | +    def test_no_false_hedges_and_no_false_possessives(self):
 914 | +        for ok in ("the mayor spoke", "maybe not", "mighty rules", "the perhapsless case"):
 915 | +            self.assertNotIn("hedge", ids("caption", ok), ok)
 916 | +        self.assertNotIn("title-possessive", ids("title", "It's the market no government owns"))
 917 | +        self.assertNotIn("title-possessive", ids("title", "That's the design"))
 918 | +        self.assertIn("title-possessive", ids("title", "Bitcoin’s quiet edge"))      # a curly apostrophe too
 919 | +        self.assertIn("title-possessive", ids("title", "Holders' real problem"))      # a plural possessive
 920 | +
 921 | +    def test_a_one_letter_abbreviation_ends_no_sentence(self):
 922 | +        self.assertEqual(HS.sentence_count("u.s. markets fell. bitcoin did not."), 2)
 923 | +        self.assertEqual(HS.sentence_count("no authority"), 1)
 924 | +        self.assertEqual(HS.sentence_count(""), 0)
 925 | +
 926 | +    def test_money_words_are_stems_on_purpose(self):
 927 | +        self.assertIn("money-word", ids("caption", "an investigation of the network"))    # deliberate: invest\w*
 928 | +        self.assertNotIn("money-word", ids("caption", "a nonprofit keeps the code"))     # not a word start
 929 | +
 930 | +
 931 | +class TestEveryRuleFails(unittest.TestCase):
 932 | +    def test_hashtag_on_every_surface(self):
 933 | +        for slot in ("title", "caption", "takeaway", "bridge"):
 934 | +            self.assertIn("hashtag", ids(slot, "rules #bitcoin"), slot)
 935 | +        self.assertNotIn("hashtag", ids("caption", "rule # one"))                        # a bare '#' is no tag
 936 | +
 937 | +    def test_each_dash_form(self):
 938 | +        for d in ("—", "–", " -- "):
 939 | +            self.assertIn("em-dash", ids("caption", f"no ruler{d}just rules"), repr(d))
 940 | +        self.assertNotIn("em-dash", ids("caption", "self-custody, no ruler"))             # a hyphen is fine
 941 | +
 942 | +    def test_emoji(self):
 943 | +        for e in ("\U0001F680", "⭐", "✅", "\U0001F1FA\U0001F1F8"):
 944 | +            self.assertIn("emoji", ids("title", f"No ruler {e}"), repr(e))
 945 | +
 946 | +    def test_every_hedge(self):
 947 | +        for h in HS.HEDGES:
 948 | +            self.assertIn("hedge", ids("takeaway", f"It {h} hold."), h)
 949 | +            self.assertIn("hedge", ids("caption", f"it {h.upper()} hold."), h)          # case-insensitive
 950 | +
 951 | +    def test_every_ai_phrase(self):
 952 | +        for p in HS.AI_PHRASES:
 953 | +            self.assertIn("ai-phrasing", ids("bridge", f"Here, {p} things."), p)
 954 | +        self.assertIn("ai-phrasing", ids("bridge", "It’s worth noting the rules."))     # the curly apostrophe
 955 | +
 956 | +    def test_every_self_reference(self):
 957 | +        for p in HS.SELF_REFERENCE:
 958 | +            self.assertIn("self-reference", ids("caption", f"look at {p} now."), p)
 959 | +
 960 | +    def test_every_money_pattern(self):
 961 | +        for word in ("opportunity", "opportunities", "invest", "investors", "profit", "profitable", "get rich",
 962 | +                     "to the moon", "buy the dip", "financial advice"):
 963 | +            self.assertIn("money-word", ids("caption", f"some {word} here."), word)
 964 | +
 965 | +    def test_the_length_rules(self):
 966 | +        self.assertIn("title-words", ids("title", " ".join(["word"] * (HS.TITLE_MAX_WORDS + 1))))
 967 | +        self.assertNotIn("title-words", ids("title", " ".join(["word"] * HS.TITLE_MAX_WORDS)))
 968 | +        self.assertIn("takeaway-words", ids("takeaway", " ".join(["word"] * (HS.TAKEAWAY_MAX_WORDS + 1))))
 969 | +        self.assertNotIn("takeaway-words", ids("takeaway", " ".join(["word"] * HS.TAKEAWAY_MAX_WORDS)))
 970 | +        self.assertIn("caption-words", ids("caption", " ".join(["word"] * (HS.CAPTION_MAX_WORDS + 1))))
 971 | +        self.assertNotIn("caption-words", ids("caption", " ".join(["word"] * HS.CAPTION_MAX_WORDS)))
 972 | +        self.assertIn("caption-lowercase", ids("caption", "no Ruler."))
 973 | +
 974 | +    def test_every_opener_and_which_makes(self):
 975 | +        for o in HS.TAKEAWAY_OPENERS:
 976 | +            self.assertIn("takeaway-opener", ids("takeaway", f"\"{o.capitalize()}, the rules hold."), o)
 977 | +            self.assertNotIn("takeaway-opener", ids("takeaway", f"The rules hold, {o}."), o)    # only as the opener
 978 | +        self.assertIn("which-makes", ids("takeaway", "The rules hold, which makes it rare."))
 979 | +
 980 | +    def test_every_rule_id_has_a_must_fail_case(self):
 981 | +        fired = set()
 982 | +        for slot, text in [("caption", PIN_41F29B1F["caption"]), ("title", PIN_41F29B1F["title"]),
 983 | +                           ("takeaway", PIN_41F29B1F["takeaway"]), ("caption", "one. two. three."),
 984 | +                           ("bridge", "#tag — \U0001F680 delve")]:
 985 | +            fired |= ids(slot, text)
 986 | +        self.assertEqual(fired, set(HS.RULE_IDS))
 987 | +
 988 | +
 989 | +class TestTheInterface(unittest.TestCase):
 990 | +    def test_violations_carry_the_slot_rule_and_a_rule_id_detail(self):
 991 | +        for v in HS.lint("caption", PIN_41F29B1F["caption"]):
 992 | +            self.assertEqual((v["slot"], v["rule"]), ("caption", "STYLE"))
 993 | +            self.assertIn(v["detail"].split(":")[0], HS.RULE_IDS)
 994 | +        self.assertEqual(len({v["detail"].split(":")[0] for v in HS.lint("caption", PIN_41F29B1F["caption"])}),
 995 | +                         len(HS.lint("caption", PIN_41F29B1F["caption"])))             # one violation per rule id
 996 | +
 997 | +    def test_lint_lines_keeps_each_line_s_own_slot_and_skips_the_rest(self):
 998 | +        lines = [{"slot": "intro", "text": "Next — keys."}, {"slot": "bridge_1", "text": "maybe #keys"},
 999 | +                 {"slot": "takeaway", "text": PIN_41F29B1F["takeaway"]}, {"slot": "title", "text": "Fine title"},
1000 | +                 {"slot": "caption", "text": "fine caption."}, {"slot": "-", "text": "#ignored"}]
1001 | +        got = [(v["slot"], v["detail"].split(":")[0]) for v in HS.lint_lines(lines)]
1002 | +        self.assertIn(("intro", "em-dash"), got)
1003 | +        self.assertIn(("bridge_1", "hashtag"), got)
1004 | +        self.assertNotIn(("bridge_1", "hedge"), got)                                      # "maybe" is no hedge
1005 | +        self.assertIn(("takeaway", "which-makes"), got)
1006 | +        self.assertFalse([s for s, _ in got if s in ("title", "caption", "-")])
1007 | +
1008 | +    def test_an_unknown_slot_is_refused(self):
1009 | +        with self.assertRaises(ValueError):
1010 | +            HS.lint("signoff", "Clips today from A.")
1011 | +
1012 | +    def test_the_prompt_states_the_same_rules(self):
1013 | +        p = HS.PROMPT_RULES
1014 | +        for x in (str(HS.CAPTION_MAX_WORDS), str(HS.TITLE_MAX_WORDS), str(HS.TAKEAWAY_MAX_WORDS), HS.STYLE_REFERENCE,
1015 | +                  "lowercase", "possessive", "which makes") + HS.HEDGES + HS.SELF_REFERENCE + HS.TAKEAWAY_OPENERS:
1016 | +            self.assertIn(x, p, x)
1017 | +
1018 | +
1019 | +if __name__ == "__main__":
1020 | +    unittest.main()
1021 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1022 | index f0a35edc..778310d1 100644
1023 | --- a/tests/package/test_medley.py
1024 | +++ b/tests/package/test_medley.py
1025 | @@ -60,9 +60,9 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
1026 |  class TestMedleyArithmetic(unittest.TestCase):
1027 |      def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1028 |          lo, hi = PK.medley_content_range()
1029 | -        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1030 | -        seg = lambda c: [{"duration_s": c}]
1031 | -        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1032 | +        self.assertEqual((lo, hi), (36.7, 51.5))          # 60 - 14.30 - (20 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1033 | +        seg = lambda c: [{"duration_s": c}]               # (ruling 6, 22:40: a new takeaway is at most 20 words)
1034 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.LY_TAKEAWAY_MAX_WORDS)]), 60.0, places=2)
1035 |          self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1036 |          lo1, hi1 = PK.medley_content_range(n_bridges=1)
1037 |          self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1038 | @@ -77,7 +77,7 @@ class TestMedleyArithmetic(unittest.TestCase):
1039 |                  self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1040 |                  continue
1041 |              lo, hi = b
1042 | -            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1043 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.LY_TAKEAWAY_MAX_WORDS, (c, b))
1044 |              for w in (lo, hi):
1045 |                  est = PK.runtime([{"duration_s": c}], [W(w)])
1046 |                  self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1047 | @@ -87,7 +87,7 @@ class TestMedleyArithmetic(unittest.TestCase):
1048 |              aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1049 |          self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1050 |          self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1051 | -        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1052 | +        b0, b1 = PK.takeaway_budget(45.0), PK.takeaway_budget(45.0, other=[W(10)])
1053 |          self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1054 |  
1055 |  
1056 | @@ -100,9 +100,9 @@ class TestMedleyLineup(unittest.TestCase):
1057 |          self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1058 |  
1059 |      def test_more_clips_when_two_do_not_fill_the_medley(self):
1060 | -        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1061 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.5), pm("x", "B", 9.5), pm("y", "C", 9.5), pm("z", "D", 9.5))}
1062 |          seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1063 | -        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1064 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 38 s: the hook + 3 clips
1065 |          short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1066 |          self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1067 |  
1068 | @@ -212,7 +212,7 @@ class TestWriteTakeaway(unittest.TestCase):
1069 |                  continue
1070 |              fits += 1
1071 |              PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
1072 | -            lo, hi = map(int, re.search(r"one or two sentences, (\d+)-(\d+) words", prompts[0]).groups())
1073 | +            lo, hi = map(int, re.search(r'"takeaway": (\d+)-(\d+) words', prompts[0]).groups())
1074 |              n = int(re.search(r"as short as it can be \(at most (\d+) words\)", prompts[0]).group(1))
1075 |              self.assertEqual((n, (lo, hi)), bb)
1076 |              self.assertTrue(PK.LY_BRIDGE_MIN_WORDS <= n <= PK.LY_BRIDGE_WORDS)
1077 | @@ -220,7 +220,7 @@ class TestWriteTakeaway(unittest.TestCase):
1078 |                  for bw in range(PK.LY_BRIDGE_MIN_WORDS, n + 1):
1079 |                      est = PK.runtime([{"duration_s": c}], [W(t), W(bw)])
1080 |                      self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, t, bw, est))
1081 | -        self.assertGreater(fits, 50)
1082 | +        self.assertGreater(fits, 40)                       # coverage: both branches exercised (50 fit, ruling 6 caps)
1083 |          self.assertGreater(none, 0)                         # at the top of the medley's seconds no bridge fits
1084 |  
1085 |      def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1086 | @@ -230,7 +230,8 @@ class TestWriteTakeaway(unittest.TestCase):
1087 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1088 |          PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1089 |          lo, hi = PK.takeaway_budget(39.0)
1090 | -        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1091 | +        self.assertIn(f'"takeaway": {lo}-{hi} words in short declarative sentences', prompts[0])
1092 | +        self.assertIn("HOUSE STYLE", prompts[0])                  # ruling 6 (22:40): the copy rules ride every write
1093 |          self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1094 |          self.assertNotIn('"intro"', prompts[0])
1095 |  
1096 | @@ -284,6 +285,16 @@ class TestLyShape(unittest.TestCase):
1097 |          pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1098 |          self.assertFalse(PK.ly_shape(pk)[0])
1099 |  
1100 | +    def test_a_no_voice_medley_needs_its_record_and_no_vo_line(self):
1101 | +        pk = medley_pk()
1102 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1103 | +        self.assertFalse(PK.ly_shape(pk)[0])                          # no takeaway and no record: L-y 1 fails
1104 | +        self.assertTrue(PK.ly_shape(dict(pk, no_voice={"why": "the takeaway failed twice"}, bridge=None))[0])
1105 | +        self.assertFalse(PK.ly_shape(dict(pk, no_voice={"why": " "}, bridge=None))[0])      # a record without a why
1106 | +        self.assertFalse(PK.ly_shape(dict(medley_pk(), no_voice={"why": "x"}))[0])        # a VO line with the record
1107 | +        flagged = dict(pk, no_voice={"why": "x"}, bridge=None, medley={"measured": True, "flagged": ["hook -> clip_01"]})
1108 | +        self.assertFalse(PK.ly_shape(flagged)[0])                     # a join a viewer cannot follow, left unbridged
1109 | +
1110 |      def test_three_to_five_segments_and_one_clip_per_channel(self):
1111 |          self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1112 |          self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1113 | @@ -323,6 +334,16 @@ class TestMedleyPackageAndPin(unittest.TestCase):
1114 |          self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1115 |          self.assertEqual(PK.r4(pk)[0], True)
1116 |  
1117 | +    def test_each_segment_states_whether_its_clip_is_time_sensitive_and_when_it_was_published(self):
1118 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0, risk=("time_sensitive",)),
1119 | +                                          pm("y", "C", 13.0))}
1120 | +        fields = {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None, "bridge_after": None,
1121 | +                  "title": {"text": "No ruler", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1122 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
1123 | +        self.assertEqual([s["time_sensitive"] for s in pk["segments"]], [False, True, False])
1124 | +        self.assertEqual({s["source_published_at"] for s in pk["segments"]}, {PK.utc_z(by["h"]["published_at"])})
1125 | +        self.assertRegex(pk["segments"][0]["source_published_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
1126 | +
1127 |      def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1128 |          b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1129 |          pk = self.build(bridge=b, k=1, n=4)
1130 | @@ -337,14 +358,14 @@ class TestMedleyPackageAndPin(unittest.TestCase):
1131 |  
1132 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1133 |          pk = self.build()
1134 | -        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1135 | +        self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
1136 |          pk["gates"] = self.gates(pk)
1137 |          pin = package_pin.to_pin(pk, "test")
1138 |          mp = pin["moments_package"]
1139 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1140 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1141 |          self.assertEqual(mp["shape"], "medley")
1142 | -        for missing in ("medley", "ly_shape"):
1143 | +        for missing in ("medley", "ly_shape", "house_style"):
1144 |              g = self.gates(pk)
1145 |              g.pop(missing)
1146 |              with self.assertRaises(package_pin.PinRefused):
1147 | @@ -389,9 +410,11 @@ class Rig:
1148 |      A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
1149 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
1150 |  
1151 | -    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=()):
1152 | +    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
1153 | +                 spend=None):
1154 |          import providers as P
1155 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
1156 | +        self.takeaways, self.spend = list(takeaways or []), spend
1157 |          self.uncuttable, self.excluded = set(uncuttable), set(excluded)
1158 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
1159 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
1160 | @@ -399,7 +422,11 @@ class Rig:
1161 |          call = self.router.call
1162 |          self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
1163 |                                                            call(role, prompt, *a, **k))[1]
1164 | -        self.router.backends = {"xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}
1165 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
1166 | +        self.router.backends = {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek"),
1167 | +                                "heimdall:qwen": B("heimdall", "qwen")}
1168 | +        self.router.chain = lambda role: ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
1169 | +        self.write_avoid = []
1170 |  
1171 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
1172 |          self.medley_calls.append([m["moment_id"] for m in segs])
1173 | @@ -412,11 +439,12 @@ class Rig:
1174 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
1175 |              raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
1176 |          self.write_calls.append(([m["moment_id"] for m in segs], join))
1177 | +        self.write_avoid.append(avoid_vendor)
1178 |          b = self.writes.pop(0)
1179 | -        fields = {"takeaway": {"text": self.LINE, "cites": []}, "bridge": b,
1180 | +        fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
1181 |                    "bridge_after": join[0] if join is not None and b is not None else None,
1182 |                    "title": {"text": "Nobody bends the rules", "cites": []},
1183 | -                  "caption": {"text": "three voices, one point", "cites": []},
1184 | +                  "caption": {"text": "nobody bends these rules", "cites": []},
1185 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
1186 |          return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
1187 |  
1188 | @@ -446,7 +474,8 @@ class Rig:
1189 |          try:
1190 |              for k, v in stubs.items():
1191 |                  setattr(PK, k, v)
1192 | -            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent")
1193 | +            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
1194 | +                            spend=self.spend)
1195 |          finally:
1196 |              for k, v in saved.items():
1197 |                  setattr(PK, k, v)
1198 | @@ -525,6 +554,53 @@ class TestBuildLoop(unittest.TestCase):
1199 |          self.assertEqual(len(rig.write_calls), 2)          # the paid verdicts never ran on the doomed line-up
1200 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "z", "w"])
1201 |  
1202 | +    def test_no_voice_when_the_takeaway_fails_twice_on_clips_that_hold_alone(self):
1203 | +        """Ruling 3 (22:40): clips back to back and the sign-off, NOT dropped; one clip added to land 60-70 s."""
1204 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
1205 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
1206 | +                  [None, None], takeaways=bad)
1207 | +        out = rig.run()
1208 | +        pk = out["package"]
1209 | +        self.assertIsNotNone(pk)
1210 | +        self.assertEqual(len(rig.write_calls), 2)                  # both takeaways failed (takeaway-opener)
1211 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])   # 39 s + z: 52 s
1212 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])   # the new line-up judged on the clips alone
1213 | +        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
1214 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
1215 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
1216 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
1217 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
1218 | +        self.assertIn("no VO line", pk["checks"]["coherence"]["note"])
1219 | +        mp = package_pin.to_pin(pk, "test")["moments_package"]
1220 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
1221 | +
1222 | +    def test_no_voice_never_ships_a_join_the_blind_check_flagged(self):
1223 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1224 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
1225 | +        rig = Rig(self.MS, ["h", "x", "y"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b, b], takeaways=bad)
1226 | +        out = rig.run()
1227 | +        self.assertIsNone(out["package"])
1228 | +        self.assertNotIn("no_voice", out["tried"][0])           # not tried: the clips need a bridge to be followed
1229 | +
1230 | +    def test_every_write_stays_on_the_angles_vendor(self):
1231 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
1232 | +        out = rig.run()
1233 | +        self.assertEqual(rig.write_avoid, [{"heimdall", "xai"}])  # the angle came from vendor "fake": all others out
1234 | +        self.assertEqual(out["angle_backend"], "fake:angle_write")
1235 | +        self.assertEqual(out["angle_tried"], [])
1236 | +
1237 | +    def test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling(self):
1238 | +        """Ruling 5 (22:40): per package 15 min wall / $1.50 by the vendors' reported cost; the estimate only as a $5
1239 | +        ceiling. Checked when an angle ends."""
1240 | +        for spent, why in (((0.10, 1.51), "reported"), ((5.01, 0.20), "estimate ceiling")):
1241 | +            calls = iter([(0.0, 0.0)] + [spent] * 50)
1242 | +            rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(False, [], None, "none")] * 2, [],
1243 | +                      spend=lambda: next(calls))
1244 | +            out = rig.run()
1245 | +            self.assertIn("ruling 5", out["why_none"], why)
1246 | +            self.assertEqual(out["budget_stop"]["angles_tried"], 1, why)
1247 | +            self.assertEqual(len(rig.medley_calls), 1, why)         # the second angle never ran
1248 | +
1249 |      def test_the_supply_exception_is_recorded(self):
1250 |          ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
1251 |          rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
1252 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1253 | index 23c2775b..fca94141 100644
1254 | --- a/tests/providers/test_providers.py
1255 | +++ b/tests/providers/test_providers.py
1256 | @@ -65,6 +65,56 @@ def wav(tmp, seconds=2.0):
1257 |      return p
1258 |  
1259 |  
1260 | +class Slow(Fake):
1261 | +    """A back-end that answers only after `delay` seconds (a Heimdall angle call that hangs)."""
1262 | +
1263 | +    def __init__(self, name, vendor, answer, delay, **kw):
1264 | +        super().__init__(name, vendor, answer=answer, **kw)
1265 | +        self.delay = delay
1266 | +
1267 | +    def complete(self, prompt, max_tokens, seed, system=None):
1268 | +        import time as _t
1269 | +        _t.sleep(self.delay)
1270 | +        return super().complete(prompt, max_tokens, seed, system)
1271 | +
1272 | +
1273 | +class TestDeadline(unittest.TestCase):
1274 | +    """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
1275 | +    back-end, the failover is recorded, and the abandoned call's upper bound is booked as spent."""
1276 | +
1277 | +    def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
1278 | +        import tempfile
1279 | +        import time as _t
1280 | +        with tempfile.TemporaryDirectory() as d:
1281 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
1282 | +            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
1283 | +            r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
1284 | +                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0)
1285 | +            t0 = _t.time()
1286 | +            rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
1287 | +            self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
1288 | +            self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
1289 | +            self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
1290 | +            self.assertIn("abandoned at the deadline", rep.tried[0][1])
1291 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
1292 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)       # booked, at its upper bound
1293 | +            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"],
1294 | +                                   slow.upper_usd("p", 100), places=6)
1295 | +            self.assertEqual(led["reserved"], {})                      # no reservation left behind
1296 | +
1297 | +    def test_an_answer_inside_the_deadline_and_an_error_keep_their_meaning(self):
1298 | +        import tempfile
1299 | +        with tempfile.TemporaryDirectory() as d:
1300 | +            ok = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.05)
1301 | +            r = router(d, [ok], {"angle_write": ["heimdall:deepseek"]})
1302 | +            self.assertEqual(r.call("angle_write", "p", 100, 7, deadline_s=5).text, '{"ok": 1}')
1303 | +            bad = Fake("heimdall:deepseek", "heimdall", fail="HTTP 503")
1304 | +            r2 = router(d, [bad], {"angle_write": ["heimdall:deepseek"]})
1305 | +            with self.assertRaises(P.ProviderError) as cm:            # the back-end's own error, not a deadline
1306 | +                r2.call("angle_write", "p", 100, 7, deadline_s=5)
1307 | +            self.assertIn("HTTP 503", str(cm.exception))
1308 | +
1309 | +
1310 |  class TestRouter(unittest.TestCase):
1311 |      def test_the_chain_fails_over_and_names_the_model_that_answered(self):
1312 |          with tempfile.TemporaryDirectory() as d:
1313 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the MEDLEY: clips
back to back, ONE takeaway VO line at the end). It implements the orchestrator's rulings of 22:40 ET Nov 12. Standing
laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make
something pass; every verdict avoids the vendor and model family of any reply whose text it judges (L-x).

THE RULINGS (paraphrased exactly):
R1 Recency is checked against the RENDER clock, not the universe's. Pins carry, per segment, "time_sensitive" (bool)
   and "source_published_at" (ISO 8601 UTC), INSIDE the seal. The render side holds a run when a time-sensitive clip is
   older than 24 h at render time, and holds any pin missing or malforming either field.
R3 NO-VOICE FALLBACK (replaces the old plain-VO fallback, which had no L-y form): if the takeaway fails its gates twice,
   the package ships with NO takeaway (clips back to back and the sign-off only), provided the clips-alone verdict
   passed. It is not dropped. The runtime rule still applies, so the packager may add a clip.
R5 BUDGET with Heimdall as the writer: per package 15 min wall and $1.50 by the vendors' reported cost; the price-table
   estimate (it over-states about 7x) only as a hard ceiling at $5. One writer (angle) call may not wait more than
   5 min: on timeout it fails over to the next back-end (qwen, then xAI), and the failover is recorded.
R6 HOUSE STYLE on the three text surfaces, as a deterministic lint, writer-prompt rules and must-fail tests. PBX's copy
   rules: lowercase captions, no hashtags, no em-dashes, no emoji, no AI-sounding phrasing, no hedging.
   - CAPTION: lowercase, one or two short sentences; no hedges (may, might, could be, perhaps); no self-reference (this
     medley, this video, builds toward); no "opportunity"/"invest"-style words.
   - TITLE: at most 8 words, plain, no possessive throat-clearing.
   - TAKEAWAY: at most 20 words, short declarative sentences; never opens with "What stands out", "It's worth noting",
     "Ultimately", "In the end"; no "which makes ..." clause.
   The delivered 41f29b1f caption is a must-fail fixture. Still gated by VO fidelity / context integrity as before.

What changed, and what to check:
1. pipeline/package_pin.py: seal() hashes time_sensitive and source_published_at per segment; to_pin() refuses a
   package whose segment lacks either, or has a non-bool time_sensitive or a published time that is not exactly
   YYYY-MM-DDTHH:MM:SSZ and parseable (recency_problems). The pin's segments carry both fields.
   pipeline/package.py: _package computes them per segment (time_sensitive() of the moment; utc_z of its published_at).
   Can a pin be written whose recency facts are missing, wrong or outside the seal? Is utc_z right on offsets?
2. pipeline/house_style.py (new): lint(slot, text) and lint_lines(lines); the rules and constants; PROMPT_RULES.
   package.cheap_checks runs it on every line of a medley; a sealed "house_style" inventory row is required for a medley
   pin (package_pin.MEDLEY_GATES); the writer prompt carries PROMPT_RULES; the takeaway's word budget is capped at 20
   (LY_TAKEAWAY_MAX_WORDS), so medley_content_range is now 36.7-51.5 s. Check false positives and negatives, the
   sentence counting, the possessive / contraction handling and the emoji ranges.
3. The no-voice fallback in package.build(): a line-up whose clips-alone verdict passed with NO flagged join, whose
   takeaway failed its own gates in both writes (take_failed >= NO_VOICE_AFTER), gets no_voice():
   - the latest write's title and caption;
   - when the clips are under 45.7 s, ONE more clip of the angle in the proposer's order, and that line-up judged on
     the clips alone again with no flagged join;
   - assemble_medley with no takeaway and no bridge, recording pk["no_voice"] = {why, added_clip, lineup_before};
   - every gate again: cheap, exclusion / L-v 2 / CUTTABLE, fidelity and context;
   - coherence = the clips-alone verdict;
   - the inventory, then package_pin.gate_problems.
   ly_shape accepts no VO line only with that record. Can a no-voice package ship without its clips-alone verdict, with
   a join a viewer cannot follow, with a VO line, outside 60-70 s, or with title / caption that skipped a gate?
4. pipeline/providers.py: Router.call(..., deadline_s): the back-end runs in a daemon thread (_within). Past the
   deadline the call is abandoned (DeadlineExceeded), its reservation is settled at its UPPER bound as spent, the
   failover is recorded in Reply.tried, and the next back-end in the chain is tried. Can a reservation leak? Can an
   abandoned call's late answer be recorded or served? Is a back-end's own error still reported as before?
5. package.build(): every writer call carries WRITER_DEADLINE_S (300 s); every takeaway write avoids every writer
   vendor except the angle's (writer_avoid), so the judges keep a vendor; out["angle_tried"] records the failover.
   The budget stop (checked when an angle ends) is: wall > 900 s, or vendor-reported > $1.50, or estimate > $5;
   spend() returns (estimate, reported).
6. tests: test_medley.py (no-voice, vendor pinning, budget, recency), test_house_style.py, test_angles.py (recency
   must-fails), test_providers.py (TestDeadline), test_gates.py (the Canned router takes deadline_s).

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".

