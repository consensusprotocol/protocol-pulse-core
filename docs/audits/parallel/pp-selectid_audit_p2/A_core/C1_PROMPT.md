# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-p2
# Branch: pp-selectid
# Generated: 2026-11-12 04:48 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_p2/A_core/STEP.diff (2862 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | new file mode 100644
   3 | index 00000000..28638daa
   4 | --- /dev/null
   5 | +++ b/pipeline/context_integrity.py
   6 | @@ -0,0 +1,302 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/context_integrity.py — CONTEXT INTEGRITY (law L-s, orchestrator 2026-11-12 '02:30'; a HARD gate, separate
   9 | +from VO fidelity): a verbatim whole sentence can still misrepresent its speaker once lifted. Per selected moment:
  10 | +
  11 | +INPUTS  the source's transcript from >= CONTEXT_BEFORE_S before the moment (pulled back to the question it answers, when
  12 | +        one ends within CONTEXT_MAX_BEFORE_S) to >= CONTEXT_AFTER_S after it, the video title, the selected sentences,
  13 | +        and the finished package (order, adjacent clips, VO, title, caption).
  14 | +STEP A  (context only, the package hidden; role "context_verdict", never the writer's vendor): who is speaking, whose
  15 | +        view it is (own sincere / attributed / hypothetical / conditional / sarcastic / question / reading aloud / ad
  16 | +        read), every pronoun and this / that / today with its referent and whether it lies inside the selection, any
  17 | +        governing condition or time frame, any retraction or qualification in the window, the proposition asserted.
  18 | +STEP B  (the package only; role "viewer_takeaway", never the writer's vendor): what an ordinary viewer concludes each
  19 | +        speaker asserts, how certain, and any implied relation (agreeing / answering / rebutting / one conversation)
  20 | +        between speakers.
  21 | +STEP C  (role "context_verdict"): does A's in-context proposition entail B's takeaway, same polarity, no stronger
  22 | +        certainty?
  23 | +DECIDE  (code) PASS only if: own sincere assertion; no speaker change inside; every referent and condition inside the
  24 | +        selection; no retraction; C entails, same polarity, not stronger; no implied relation between speakers of
  25 | +        different source videos. Any "uncertain" fails (law L-m).
  26 | +REPAIR  only extending the clip by whole locked sentences (backwards, to take in a referent or condition) and checking
  27 | +        again, or dropping the MOMENT and repacking; never writing the missing context into the VO (L-s).
  28 | +"""
  29 | +import json
  30 | +
  31 | +import eligibility as E
  32 | +
  33 | +CONTEXT_BEFORE_S = 90.0
  34 | +CONTEXT_MAX_BEFORE_S = 180.0
  35 | +CONTEXT_AFTER_S = 60.0
  36 | +VIEWS = ("own_sincere", "attributed", "hypothetical", "conditional", "sarcastic", "question", "reading_aloud",
  37 | +         "ad_read", "joke", "uncertain")
  38 | +CERTAINTY = ("certain", "likely", "possible", "speculative", "uncertain")
  39 | +RELATIONS = ("none", "agreeing", "answering", "rebutting", "same_conversation", "uncertain")
  40 | +YNU = ("yes", "no", "uncertain")
  41 | +
  42 | +
  43 | +def window(src, k0, k1, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S, max_before=CONTEXT_MAX_BEFORE_S):
  44 | +    """Sentence indices (a, b) of the context window around the moment k0..k1: >= `before` s earlier (back to the
  45 | +    question the moment answers, when one ends within `max_before` s), >= `after` s later; whole sentences."""
  46 | +    S, T = src.sentences, src.tokens
  47 | +    t0 = E._time(T[S[k0][0]], "start")
  48 | +    t1 = E._time(T[S[k1][1]], "end")
  49 | +    a = k0
  50 | +    while a > 0 and t0 is not None and (E._time(T[S[a - 1][0]], "start") or 0) >= t0 - before:
  51 | +        a -= 1
  52 | +    q = a
  53 | +    while q > 0 and t0 is not None and (E._time(T[S[q - 1][0]], "start") or 0) >= t0 - max_before:
  54 | +        q -= 1
  55 | +        if (T[S[q][1]].get("word") or "").rstrip().endswith("?"):
  56 | +            a = min(a, q)
  57 | +            break
  58 | +    b = k1
  59 | +    while b + 1 < len(S) and t1 is not None and (E._time(T[S[b + 1][1]], "end") or 1e18) <= t1 + after:
  60 | +        b += 1
  61 | +    return a, b
  62 | +
  63 | +
  64 | +def _window_text(src, k0, k1):
  65 | +    a, b = window(src, k0, k1)
  66 | +    S, T = src.sentences, src.tokens
  67 | +    parts = []
  68 | +    for k in range(a, b + 1):
  69 | +        t = E.spoken(T[S[k][0]:S[k][1] + 1])
  70 | +        parts.append(f"<selected>{t}</selected>" if k0 <= k <= k1 else t)
  71 | +    return " ".join(parts), (a, b)
  72 | +
  73 | +
  74 | +STEP_A = """You read transcripts of Bitcoin videos. For each EXCERPT below, the sentences inside <selected> are a clip
  75 | +that may be shown on its own. Use the whole excerpt (what comes before and after) to judge the selected words. You do
  76 | +not know how the clip will be used.
  77 | +
  78 | +{excerpts}
  79 | +
  80 | +For each excerpt answer:
  81 | +- "speaker_changes_inside": does the speaker change inside the selected words? "yes" / "no" / "uncertain"
  82 | +- "view": whose view the selected words express: "own_sincere" (the speaker's own sincere assertion), "attributed"
  83 | +  (someone else's view, quoted or reported), "hypothetical", "conditional" (true only under a condition), "sarcastic",
  84 | +  "question", "reading_aloud" (reading a post or article), "ad_read", "joke", or "uncertain"
  85 | +- "referents": every pronoun or pointing word in the selected words (it, they, this, that, he, she, today, here...)
  86 | +  that points at something specific, with what it refers to and whether the selected words themselves identify it
  87 | +  ("inside": true) or a listener needs the words before or after the selection ("inside": false). Leave out words
  88 | +  that point at nothing outside: a dummy "it" ("it's raining", "it's not X that ...", where X is in the selection),
  89 | +  and a generic "we" / "you" / "they" meaning people in general
  90 | +- "conditions": any condition or time frame that governs the selected words, and whether it is INSIDE them
  91 | +- "retraction": "none", or what the speaker later in the excerpt retracts or qualifies about the selected words
  92 | +- "time_ok": "yes" if every time word in the selected words (today, now, this week, just, recently, a "current"
  93 | +  price) still holds on the show date given when the video was published (both on the excerpt), or there is none;
  94 | +  "no" if it is stale; "uncertain"
  95 | +- "proposition": in one sentence, what the speaker asserts in the selected words, read in context
  96 | +- "certainty": "certain", "likely", "possible", "speculative" or "uncertain"
  97 | +Return ONLY this JSON object: {{"excerpts": [{{"label": "...", "speaker_changes_inside": "...", "view": "...",
  98 | +"referents": [{{"word": "...", "refers_to": "...", "inside": true}}], "conditions": [{{"text": "...", "inside": true}}],
  99 | +"retraction": "none", "time_ok": "yes", "proposition": "...", "certainty": "..."}}]}}"""
 100 | +
 101 | +STEP_B = """You are an ordinary viewer of a 60-second video. Here is everything the video shows and says, in order.
 102 | +
 103 | +{package}
 104 | +
 105 | +For each clip say what you conclude its speaker asserts, how certain they sound, and whether it is positive, negative
 106 | +or neutral about its subject. Use the CLIP labels exactly as shown above (hook, clip_01, ...) in "label" and in
 107 | +"labels", never the speakers' names. Then, for each pair of clips, say whether the video presents their speakers as RELATED TO EACH
 108 | +OTHER: one answering the other, one rebutting the other, one agreeing WITH the other ("X agrees", "Y backs that up",
 109 | +"both say"), or the two being in one conversation. Two speakers who each state their own view on the same subject,
 110 | +each credited, are NOT related ("none") unless the video says or implies that they respond to each other.
 111 | +Return ONLY this JSON object: {{"takeaways": [{{"label": "...", "asserts": "...", "certainty": "certain" | "likely" |
 112 | +"possible" | "speculative" | "uncertain", "polarity": "positive" | "negative" | "neutral"}}], "relations":
 113 | +[{{"labels": ["...", "..."], "relation": "none" | "agreeing" | "answering" | "rebutting" | "same_conversation" |
 114 | +"uncertain"}}]}}"""
 115 | +
 116 | +STEP_C = """For each pair below, A is what a speaker asserted, read in its original context; B is what a viewer of a
 117 | +short video concludes the same speaker asserted. Answer for each: does A entail B ("yes", "no", "uncertain"); do they
 118 | +have the same polarity ("yes", "no", "uncertain"); is B more certain than A ("yes", "no", "uncertain")?
 119 | +
 120 | +{pairs}
 121 | +
 122 | +Return ONLY this JSON object: {{"pairs": [{{"label": "...", "entails": "...", "same_polarity": "...",
 123 | +"stronger_certainty": "..."}}]}}"""
 124 | +
 125 | +
 126 | +def _q(t, n):
 127 | +    from story_semantics import quote_data
 128 | +    return quote_data(t, n)
 129 | +
 130 | +
 131 | +def package_view(package):
 132 | +    """The package as a viewer meets it: VO intro, then each segment with its on-screen credit, bridges between, the
 133 | +    sign-off; the title and caption."""
 134 | +    out = [f"TITLE: {_q(package['title'], 200)}", f"CAPTION: {_q(package['caption'], 400)}"]
 135 | +    vo = package["vo"]
 136 | +    if vo.get("intro"):
 137 | +        out.append(f"VOICE-OVER: {_q(vo['intro'], 400)}")
 138 | +    bridges = list(vo.get("bridges") or [])
 139 | +    after = list(vo.get("bridges_after_clip") or range(1, len(bridges) + 1))   # bridge j follows clip after[j]
 140 | +    by_clip = {a: b for a, b in zip(after, bridges)}
 141 | +    for i, seg in enumerate(package["segments"]):                            # segment 0 is the hook, i = clip index
 142 | +        out.append(f'CLIP {seg["label"]} (on screen: {_q(seg["channel"], 80)}): "{_q(seg["text"], 900)}"')
 143 | +        if by_clip.get(i):
 144 | +            out.append(f"VOICE-OVER: {_q(by_clip[i], 400)}")
 145 | +    if vo.get("signoff"):
 146 | +        out.append(f"VOICE-OVER: {_q(vo['signoff'], 300)}")
 147 | +    return "\n".join(out)
 148 | +
 149 | +
 150 | +def _strict(raw, top, item_keys):
 151 | +    obj = json.loads(raw.strip())
 152 | +    if not isinstance(obj, dict) or set(obj) != set(top):
 153 | +        raise ValueError(f"keys must be exactly {sorted(top)}")
 154 | +    for k, keys in item_keys.items():
 155 | +        if not isinstance(obj[k], list):
 156 | +            raise ValueError(f"'{k}' must be a list")
 157 | +        for it in obj[k]:
 158 | +            if not isinstance(it, dict) or set(it) != set(keys):
 159 | +                raise ValueError(f"each item of '{k}' needs exactly {sorted(keys)}")
 160 | +    return obj
 161 | +
 162 | +
 163 | +def contexts_from_sources(package, sources, now=None):
 164 | +    """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
 165 | +    out = {}
 166 | +    for seg in package["segments"]:
 167 | +        src = sources[seg["video_id"]]
 168 | +        text, win = _window_text(src, seg["k0"], seg["k1"])
 169 | +        out[seg["label"]] = {"text": text, "title": src.title or "", "channel": seg["channel"], "window": win,
 170 | +                             "published": str(src.published_at or "")[:16],
 171 | +                             "show_date": now.strftime("%Y-%m-%d") if now else None}
 172 | +    return out
 173 | +
 174 | +
 175 | +def check(router, package, sources, writer_vendor, seed=7):
 176 | +    """The pipeline's entry: contexts built from the sources' records (every segment is a moment)."""
 177 | +    return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
 178 | +
 179 | +
 180 | +def step_a(router, contexts, writer_vendor, seed=7):
 181 | +    """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
 182 | +    Raises ValueError / ProviderError when it cannot be had or read."""
 183 | +    labels = list(contexts)
 184 | +    ex = [f'<excerpt label="{lb}" channel="{_q(contexts[lb]["channel"], 80)}" video_title='
 185 | +          f'"{_q(contexts[lb].get("title") or "", 160)}" published="{contexts[lb].get("published") or "unknown"}" '
 186 | +          f'show_date="{contexts[lb].get("show_date") or "unknown"}">{_q(contexts[lb]["text"], 6000)}</excerpt>'
 187 | +          for lb in labels]
 188 | +    ra = router.call("context_verdict", STEP_A.format(excerpts="\n".join(ex)), 4000, seed, avoid_vendor=writer_vendor)
 189 | +    A = _strict(ra.text, {"excerpts"}, {"excerpts": ("label", "speaker_changes_inside", "view", "referents",
 190 | +                                                     "conditions", "retraction", "time_ok", "proposition",
 191 | +                                                     "certainty")})
 192 | +    a_by = {e["label"]: e for e in A["excerpts"]}
 193 | +    if set(a_by) != set(labels):
 194 | +        raise ValueError(f"step A must answer exactly the labels {labels}")
 195 | +    return a_by, ra.backend
 196 | +
 197 | +
 198 | +def a_failures(a):
 199 | +    """The step-A half of the decision rule for one moment: [rule, ...] (empty = its own context passes)."""
 200 | +    out = []
 201 | +    if a.get("speaker_changes_inside") != "no":
 202 | +        out.append("SPEAKER_CHANGE")
 203 | +    if a.get("view") != "own_sincere":
 204 | +        out.append("NOT_OWN_SINCERE")
 205 | +    refs, conds = a.get("referents"), a.get("conditions")
 206 | +    if not isinstance(refs, list) or any(not isinstance(r, dict) or r.get("inside") is not True for r in refs):
 207 | +        out.append("REFERENT_OUTSIDE")
 208 | +    if not isinstance(conds, list) or any(not isinstance(c, dict) or c.get("inside") is not True for c in conds):
 209 | +        out.append("CONDITION_OUTSIDE")
 210 | +    if a.get("retraction") != "none":
 211 | +        out.append("RETRACTION")
 212 | +    if a.get("time_ok", "yes") != "yes":            # law L-v 3 (older recordings of step A lack the field)
 213 | +        out.append("STALE_TIME")
 214 | +    if a.get("certainty") not in CERTAINTY[:4]:
 215 | +        out.append("UNCERTAIN")
 216 | +    return out
 217 | +
 218 | +
 219 | +def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None):
 220 | +    """package: {"segments": [{"label", "video_id", "channel", "text"}], "vo": {"intro", "bridges", "signoff"},
 221 | +    "title", "caption"}; contexts: {label: {"text" (the window, the moment inside <selected>), "title", "channel"}}
 222 | +    for the segments to judge (a segment without a context is judged only through the package: relations).
 223 | +    -> {"ok", "segments", "relations", "violations", "backends"}. A step that cannot be had or read fails (L-m)."""
 224 | +    import providers as P
 225 | +    segs = package["segments"]
 226 | +    labels = [s["label"] for s in segs if s["label"] in contexts]
 227 | +    all_labels = [s["label"] for s in segs]
 228 | +    out = {"segments": {}, "relations": [], "violations": [], "backends": {}}
 229 | +    V = lambda label, rule, detail: out["violations"].append({"segment": label, "rule": rule, "detail": detail})
 230 | +    if not labels:
 231 | +        V("-", "CONTEXT_UNAVAILABLE", "no segment has its source context")
 232 | +        out["ok"] = False
 233 | +        return out
 234 | +    try:
 235 | +        if a_by is None:
 236 | +            a_by, out["backends"]["A"] = step_a(router, {lb: contexts[lb] for lb in labels}, writer_vendor, seed)
 237 | +        else:
 238 | +            a_by = {lb: a_by[lb] for lb in labels}
 239 | +            out["backends"]["A"] = "precomputed (package-independent: context only)"
 240 | +        rb = router.call("viewer_takeaway", STEP_B.format(package=package_view(package)), 3000, seed,
 241 | +                         avoid_vendor=writer_vendor)
 242 | +        out["backends"]["B"] = rb.backend
 243 | +        B = _strict(rb.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
 244 | +                                                          "relations": ("labels", "relation")})
 245 | +        b_by = {t["label"]: t for t in B["takeaways"]}
 246 | +        if not set(labels) <= set(b_by):
 247 | +            raise ValueError(f"step B must answer at least {labels}")
 248 | +        pairs = "\n".join(f'<pair label="{lb}"><A>{_q(a_by[lb]["proposition"], 400)} (certainty: '
 249 | +                          f'{a_by[lb]["certainty"]})</A><B>{_q(b_by[lb]["asserts"], 400)} (certainty: '
 250 | +                          f'{b_by[lb]["certainty"]})</B></pair>' for lb in labels)
 251 | +        rc = router.call("context_verdict", STEP_C.format(pairs=pairs), 2000, seed, avoid_vendor=writer_vendor)
 252 | +        out["backends"]["C"] = rc.backend
 253 | +        C = _strict(rc.text, {"pairs"}, {"pairs": ("label", "entails", "same_polarity", "stronger_certainty")})
 254 | +        c_by = {c["label"]: c for c in C["pairs"]}
 255 | +        if set(c_by) != set(labels):
 256 | +            raise ValueError(f"step C must answer exactly the labels {labels}")
 257 | +    except (P.ProviderError, P.SpendLimit, ValueError, KeyError, TypeError) as e:
 258 | +        V("-", "CONTEXT_UNAVAILABLE", f"{type(e).__name__}: {str(e)[:240]}")
 259 | +        out["ok"] = False
 260 | +        return out
 261 | +    vid = {s["label"]: s["video_id"] for s in segs}
 262 | +    for lb in labels:
 263 | +        a, b, c = a_by[lb], b_by[lb], c_by[lb]
 264 | +        out["segments"][lb] = {"A": a, "B": b, "C": c, "window": (contexts[lb] or {}).get("window")}
 265 | +        if a["speaker_changes_inside"] != "no":
 266 | +            V(lb, "SPEAKER_CHANGE", f"speaker change inside: {a['speaker_changes_inside']}")
 267 | +        if a["view"] != "own_sincere":
 268 | +            V(lb, "NOT_OWN_SINCERE", f"view: {a['view']}")
 269 | +        for r in a["referents"] if isinstance(a["referents"], list) else [None]:
 270 | +            if not isinstance(r, dict) or r.get("inside") is not True:
 271 | +                V(lb, "REFERENT_OUTSIDE", f"{(r or {}).get('word')!r} -> {(r or {}).get('refers_to')!r}")
 272 | +        for cnd in a["conditions"] if isinstance(a["conditions"], list) else [None]:
 273 | +            if not isinstance(cnd, dict) or cnd.get("inside") is not True:
 274 | +                V(lb, "CONDITION_OUTSIDE", f"{(cnd or {}).get('text')!r}")
 275 | +        if a["retraction"] != "none":
 276 | +            V(lb, "RETRACTION", str(a["retraction"])[:200])
 277 | +        if a.get("time_ok", "yes") != "yes":
 278 | +            V(lb, "STALE_TIME", f"time words stale on the show date: {a.get('time_ok')}")
 279 | +        if a["certainty"] not in CERTAINTY[:4] or b["certainty"] not in CERTAINTY[:4]:
 280 | +            V(lb, "UNCERTAIN", f"certainty A {a['certainty']} / B {b['certainty']}")
 281 | +        if c["entails"] != "yes":
 282 | +            V(lb, "NOT_ENTAILED", f"entails: {c['entails']}")
 283 | +        if c["same_polarity"] != "yes":
 284 | +            V(lb, "POLARITY", f"same polarity: {c['same_polarity']}")
 285 | +        if c["stronger_certainty"] != "no":
 286 | +            V(lb, "STRONGER", f"stronger certainty: {c['stronger_certainty']}")
 287 | +    for rel in B["relations"]:
 288 | +        labs, kind = rel.get("labels"), rel.get("relation")
 289 | +        if kind not in RELATIONS or not isinstance(labs, list) or len(labs) != 2 or any(x not in vid for x in labs):
 290 | +            V("-", "RELATION_UNREADABLE", json.dumps(rel)[:200])
 291 | +            continue
 292 | +        if kind == "none":
 293 | +            continue
 294 | +        if kind == "uncertain" or vid[labs[0]] != vid[labs[1]]:
 295 | +            V("+".join(labs), "FALSE_RELATION", f"the package makes them look {kind}; they are not one conversation")
 296 | +    out["relations"] = B["relations"]
 297 | +    out["judged"] = labels
 298 | +    out["ok"] = not out["violations"]
 299 | +    return out
 300 | +
 301 | +
 302 | +def repairable(violations):
 303 | +    """Labels whose only failures a backward extension by whole sentences may cure (a referent or condition outside the
 304 | +    clip); everything else drops the moment."""
 305 | +    by = {}
 306 | +    for v in violations:
 307 | +        by.setdefault(v["segment"], set()).add(v["rule"])
 308 | +    return {lb for lb, rules in by.items() if rules and rules <= {"REFERENT_OUTSIDE", "CONDITION_OUTSIDE"}}
 309 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
 310 | new file mode 100644
 311 | index 00000000..a6e42770
 312 | --- /dev/null
 313 | +++ b/pipeline/model_providers.json
 314 | @@ -0,0 +1,189 @@
 315 | +{
 316 | + "schema": "pp.providers/1",
 317 | + "law": "L-x NO SINGLE MODEL, ULTRON FIRST (orchestrator 2026-11-12 02:45): every role names >= 2 interchangeable back-ends; the local model on Ultron is first wherever it meets the quality bar; a frontier model or Heimdall is used only where a measured blind A/B (tests/providers/ab_roles.py) shows local is not good enough, and the comparison is re-run so roles migrate to local. Verdict roles never run on the writer's vendor (law L-s; Router.call avoid_vendor). No role's code names a vendor or a model: only this file does.",
 318 | + "decided": "2026-11-12 02:44 ET by pipeline_pp_selectid: an INITIAL order, not yet measured. Mining, story selection and the check verdict put local first (law L-w 1: local gemma mines and scores by id). Angle and writing put a frontier model first (law L-w 1 and PBX 02:35: frontier spend approved for writing and checking) until the A/B shows local meets the bar. Verdicts run on a vendor other than the writer's.",
 319 | + "backends": {
 320 | +  "local:gemma3:27b": {
 321 | +   "vendor": "local",
 322 | +   "model": "gemma3:27b",
 323 | +   "price_usd_per_1m": [
 324 | +    0,
 325 | +    0
 326 | +   ]
 327 | +  },
 328 | +  "openai:gpt-6.1-sol": {
 329 | +   "vendor": "openai",
 330 | +   "model": "gpt-6.1-sol",
 331 | +   "price_usd_per_1m": [
 332 | +    15,
 333 | +    120
 334 | +   ],
 335 | +   "reasoning_effort": "medium",
 336 | +   "min_out": 4000
 337 | +  },
 338 | +  "anthropic:claude-fable-5-2": {
 339 | +   "vendor": "anthropic",
 340 | +   "model": "claude-fable-5-2",
 341 | +   "price_usd_per_1m": [
 342 | +    8,
 343 | +    40
 344 | +   ],
 345 | +   "effort": "medium",
 346 | +   "min_out": 16000
 347 | +  },
 348 | +  "anthropic:claude-opus-5-5": {
 349 | +   "vendor": "anthropic",
 350 | +   "model": "claude-opus-5-5",
 351 | +   "price_usd_per_1m": [
 352 | +    4,
 353 | +    20
 354 | +   ],
 355 | +   "effort": "medium",
 356 | +   "min_out": 16000
 357 | +  },
 358 | +  "xai:grok-4.20-0309-reasoning": {
 359 | +   "vendor": "xai",
 360 | +   "model": "grok-4.20-0309-reasoning",
 361 | +   "price_usd_per_1m": [
 362 | +    5,
 363 | +    25
 364 | +   ],
 365 | +   "temperature": 0,
 366 | +   "key_name": "XAI_API_KEY_MEDLEY"
 367 | +  },
 368 | +  "heimdall:qwen/qwen3.8-27b": {
 369 | +   "vendor": "heimdall",
 370 | +   "model": "qwen/qwen3.8-27b",
 371 | +   "price_usd_per_1m": [
 372 | +    3,
 373 | +    15
 374 | +   ],
 375 | +   "temperature": 0,
 376 | +   "min_out": 16000
 377 | +  },
 378 | +  "heimdall:deepseek/deepseek-v4.1-flash": {
 379 | +   "vendor": "heimdall",
 380 | +   "model": "deepseek/deepseek-v4.1-flash",
 381 | +   "price_usd_per_1m": [
 382 | +    3,
 383 | +    15
 384 | +   ],
 385 | +   "temperature": 0,
 386 | +   "min_out": 16000
 387 | +  },
 388 | +  "heimdall:google/gemma-4-31b-it": {
 389 | +   "vendor": "heimdall",
 390 | +   "model": "google/gemma-4-31b-it",
 391 | +   "price_usd_per_1m": [
 392 | +    3,
 393 | +    15
 394 | +   ],
 395 | +   "temperature": 0,
 396 | +   "min_out": 16000
 397 | +  },
 398 | +  "xai_search:grok-4.7": {
 399 | +   "vendor": "xai_search",
 400 | +   "model": "grok-4.7",
 401 | +   "price_usd_per_1m": [
 402 | +    5,
 403 | +    25
 404 | +   ],
 405 | +   "key_name": "XAI_API_KEY_MEDLEY",
 406 | +   "tools": [
 407 | +    "x_search",
 408 | +    "web_search"
 409 | +   ]
 410 | +  }
 411 | + },
 412 | + "roles": {
 413 | +  "mine": {
 414 | +   "chain": [
 415 | +    "local:gemma3:27b",
 416 | +    "openai:gpt-6.1-sol",
 417 | +    "anthropic:claude-fable-5-2",
 418 | +    "heimdall:qwen/qwen3.8-27b"
 419 | +   ],
 420 | +   "what": "moments.py: whole-sentence ranges by id with engagement scores, risk flags, topics",
 421 | +   "measured": "blind A/B 2026-11-12 03:40 ET on fresh_20261112_050611 (tests/providers/ab/mine_fresh_20261112_050611.json, judge claude-opus-5-5): gpt-6.1-sol better than heimdall qwen3.8-27b; qwen 2067 s vs 300.5 s, 1 of 6 calls rejected by the strict contract. Local gemma3:27b: the integrator's leg (GPU0 lease)."
 422 | +  },
 423 | +  "angle_write": {
 424 | +   "chain": [
 425 | +    "openai:gpt-6.1-sol",
 426 | +    "anthropic:claude-fable-5-2",
 427 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 428 | +    "local:gemma3:27b"
 429 | +   ],
 430 | +   "what": "package.py: the angle, the order, the PBX MAX VO intro / bridges, ONE title, ONE caption"
 431 | +  },
 432 | +  "fidelity_verdict": {
 433 | +   "chain": [
 434 | +    "xai:grok-4.20-0309-reasoning",
 435 | +    "anthropic:claude-opus-5-5",
 436 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 437 | +    "local:gemma3:27b"
 438 | +   ],
 439 | +   "what": "vo_fidelity.py: the blind claim-by-claim verdict on VO, title and caption; never the writer's vendor"
 440 | +  },
 441 | +  "context_verdict": {
 442 | +   "chain": [
 443 | +    "xai:grok-4.20-0309-reasoning",
 444 | +    "anthropic:claude-opus-5-5",
 445 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 446 | +    "local:gemma3:27b"
 447 | +   ],
 448 | +   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor"
 449 | +  },
 450 | +  "viewer_takeaway": {
 451 | +   "chain": [
 452 | +    "anthropic:claude-opus-5-5",
 453 | +    "xai:grok-4.20-0309-reasoning",
 454 | +    "heimdall:qwen/qwen3.8-27b",
 455 | +    "local:gemma3:27b"
 456 | +   ],
 457 | +   "what": "context_integrity.py step B (the finished package only); never the writer's vendor"
 458 | +  },
 459 | +  "trend_brief": {
 460 | +   "chain": [
 461 | +    "xai_search:grok-4.7"
 462 | +   ],
 463 | +   "fallback": "trend_brief.local_baseline (topic frequency across partner channels, last 24 h): free, always available",
 464 | +   "what": "trend_brief.py: one live-search call per cycle; SHADOW weight 0 (law L-w 4)"
 465 | +  },
 466 | +  "story": {
 467 | +   "chain": [
 468 | +    "local:gemma3:27b",
 469 | +    "openai:gpt-6.1-sol",
 470 | +    "anthropic:claude-fable-5-2",
 471 | +    "heimdall:qwen/qwen3.8-27b"
 472 | +   ],
 473 | +   "what": "select_by_id story + line-up calls (story-first type; REQUESTS R6 item 7)"
 474 | +  },
 475 | +  "check": {
 476 | +   "chain": [
 477 | +    "local:gemma3:27b",
 478 | +    "xai:grok-4.20-0309-reasoning",
 479 | +    "anthropic:claude-opus-5-5",
 480 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 481 | +   ],
 482 | +   "what": "select_by_id.ModelChecks; called with avoid_model = the story's model"
 483 | +  },
 484 | +  "exclusion_verdict": {
 485 | +   "chain": [
 486 | +    "local:gemma3:27b",
 487 | +    "xai:grok-4.20-0309-reasoning",
 488 | +    "anthropic:claude-opus-5-5",
 489 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 490 | +   ],
 491 | +   "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
 492 | +  },
 493 | +  "coherence_verdict": {
 494 | +   "chain": [
 495 | +    "anthropic:claude-opus-5-5",
 496 | +    "xai:grok-4.20-0309-reasoning",
 497 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 498 | +    "local:gemma3:27b"
 499 | +   ],
 500 | +   "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
 501 | +  }
 502 | + }
 503 | +}
 504 | diff --git a/pipeline/moments.py b/pipeline/moments.py
 505 | new file mode 100644
 506 | index 00000000..e1509e2c
 507 | --- /dev/null
 508 | +++ b/pipeline/moments.py
 509 | @@ -0,0 +1,384 @@
 510 | +#!/usr/bin/env python3
 511 | +"""pipeline/moments.py — STEP 1 MINE (law L-q, orchestrator 2026-11-12 '01:55'): the cycle's best MOMENTS, by sentence id,
 512 | +never rewritten. A moment is 1-3 consecutive whole sentences of ONE source record that makes sense heard on its own.
 513 | +
 514 | +1 LOCAL PRE-FILTER (free, deterministic, no model): sources of the window (published since the last cycle, plus the
 515 | +  recent window RECENT_H, inside the 72 h universe; opted-out channels never: pipeline/optout.json), eligible as
 516 | +  sources (partner, identity, upload, current); rows = punctuated, injection-free sentences within one sentence of a
 517 | +  sentence that names Bitcoin; an ad read (sponsor markers) is never offered; rows are taken round-robin across videos,
 518 | +  word-timed and on-screen-capable videos first, inside the model's context budget (one call per chunk).
 519 | +2 ONE BATCHED MINING PASS (role "mine" through pipeline/providers.py, law L-x: local gemma first): the model sees
 520 | +  numbered rows and answers ids only: {"moments": [{"range": [a, b], "scores": {7 axes, ints 0-5}, "names_person",
 521 | +  "risk": [enum], "topics": [taxonomy ids], "reason"}]}. The REPLY contract is strict and never repaired (law L-l):
 522 | +  exact keys, integer scores, closed enums, ranges of existing consecutive ids of one video, no overlap; anything else
 523 | +  is rejected and asked again with the reason. Each accepted moment is then judged on its own by eligibility (a
 524 | +  moment is its own statement): failures are recorded on the moment (excluded from packaging), never edited.
 525 | +3 DETERMINISTIC RANKING (law L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone
 526 | +  - 2 x contempt_outrage - soft-risk penalties + trend weight x trend match (SHADOW: weight 0, law L-w 4); "named
 527 | +  figure" is a fact, never a positive axis; hard-exclusion risks never rank. Ties by moment_id.
 528 | +
 529 | +Durations come from locked word timing (timing "word"); a caption / segment duration is only a FLAGGED estimate
 530 | +(duration_estimate_s) and never feeds a runtime. The model's `reason` is forensic only: it never enters a prompt or
 531 | +anything audience-facing. Output records follow the contract published in docs/audits/parallel/pp-selectid_STATE.md
 532 | +(pp.moment/1).
 533 | +"""
 534 | +import hashlib
 535 | +import json
 536 | +import os
 537 | +import re
 538 | +import time
 539 | +from dataclasses import replace
 540 | +
 541 | +import eligibility as E
 542 | +import select_by_id as SB
 543 | +import sentence_law
 544 | +
 545 | +HERE = os.path.dirname(os.path.abspath(__file__))
 546 | +RECENT_H = 24.0                    # "plus a recent window": the last 24 h, beside what is new since the last cycle
 547 | +MAX_MOMENTS_PER_CALL = 12
 548 | +MINE_MAX_TOKENS = 3000
 549 | +ATTEMPTS = 3
 550 | +AXES = ("hook_first_2s", "quotable", "surprising_fact", "stance", "stakes", "stands_alone", "contempt_outrage")
 551 | +POSITIVE = AXES[:6]
 552 | +HARD_RISKS = ("accusation", "partner_attack", "imperative", "guaranteed_return", "single_source_breaking", "ad_read",
 553 | +              "third_party_media")                                  # law L-u: never auto-selected
 554 | +SOFT_RISKS = {"price_prediction": 2, "doom": 2, "politics_non_btc": 3, "time_sensitive": 0}   # down-weights (L-u)
 555 | +RISKS = HARD_RISKS + tuple(SOFT_RISKS)
 556 | +CONTEMPT_WEIGHT = 2                # contempt / outrage is a PENALTY (law L-u)
 557 | +TREND_WEIGHT = 0.0                 # SHADOW (law L-w 4): logged, zero weight; when enabled, capped at ~10-15 % of score
 558 | +REASON_MAX = 200
 559 | +AD_MARKERS = re.compile(r"\b(sponsor(ed)?|brought to you by|use (my |our )?code|promo code|link in the description|"
 560 | +                        r"affiliate link|today's sponsor|check out .{0,30}(dot com|\.com))\b", re.I)
 561 | +OPTOUT = os.path.join(HERE, "optout.json")
 562 | +
 563 | +
 564 | +class Rejected(SB.Rejected):
 565 | +    pass
 566 | +
 567 | +
 568 | +def optout_ids(path=OPTOUT):
 569 | +    """The opt-out registry (PBX 02:35: no outreach; a simple file the selector honours): channel ids never mined or
 570 | +    packaged. A missing file = nobody opted out; an unreadable one fails closed (raises)."""
 571 | +    if not os.path.exists(path):
 572 | +        return frozenset()
 573 | +    with open(path) as f:
 574 | +        d = json.load(f)
 575 | +    ids = d.get("channel_ids") if isinstance(d, dict) else None
 576 | +    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
 577 | +        raise ValueError(f"{path}: expected {{'channel_ids': [str, ...]}}")
 578 | +    return frozenset(ids)
 579 | +
 580 | +
 581 | +def moment_id(src, w0, w1):
 582 | +    return hashlib.sha256(f"{src.video_id}|{src.transcript_sha256}|{w0}|{w1}".encode()).hexdigest()[:20]
 583 | +
 584 | +
 585 | +# ── 1 local pre-filter ──
 586 | +
 587 | +def window_sources(sources, ctx, since=None, recent_h=RECENT_H, optout=frozenset()):
 588 | +    """The cycle's sources: published since `since` (an aware datetime: new since the last cycle) or inside the recent
 589 | +    window, eligible as sources, not opted out; on-screen-capable (word-timed, sentence-ready, layout-eligible) first,
 590 | +    then newest first. Returns (sources, {video_id: why not})."""
 591 | +    keep, skipped = [], {}
 592 | +    for src in sources:
 593 | +        if src.channel_id in optout:
 594 | +            skipped[src.video_id] = "opted out (pipeline/optout.json)"
 595 | +            continue
 596 | +        r = E.eligible(src, replace(ctx, role="evidence"))
 597 | +        if not r.ok:
 598 | +            skipped[src.video_id] = r.why()
 599 | +            continue
 600 | +        age = r.facts.get("age_h")
 601 | +        new = since is not None and E._parse_time(src.published_at) is not None and E._parse_time(src.published_at) >= since
 602 | +        if not (new or (age is not None and age <= recent_h)):
 603 | +            skipped[src.video_id] = f"outside the window ({age:.1f} h old, not new since the last cycle)"
 604 | +            continue
 605 | +        keep.append(src)
 606 | +    on = lambda s: (s.timing == "word" and E.sentence_ready(s) and E.layout_ok(ctx.channel(s.channel_id)))
 607 | +    keep.sort(key=lambda s: (not on(s), E.age_hours(s.published_at, ctx.now) or 1e9, s.video_id))
 608 | +    return keep, skipped
 609 | +
 610 | +
 611 | +def candidate_rows(src):
 612 | +    """Sentence indices of one source worth offering: punctuated, injection-free, not an ad read, within one sentence
 613 | +    of a sentence that names Bitcoin (a range of 1-3 sentences can then name it)."""
 614 | +    import story_semantics as sm
 615 | +    S, T = src.sentences, src.tokens
 616 | +    text = [E.spoken(T[a:b + 1]) for a, b in S]
 617 | +    btc = [E.names_bitcoin(t) for t in text]
 618 | +    rows = []
 619 | +    for k, (a, b) in enumerate(S):
 620 | +        if not any(btc[max(0, k - 1):k + 2]):
 621 | +            continue
 622 | +        if AD_MARKERS.search(text[k]) or sm.injection_markers(text[k]):
 623 | +            continue
 624 | +        if not (E.ends_statement(T[b].get("word")) or (T[b].get("word") or "").rstrip().endswith("?")):
 625 | +            continue
 626 | +        if not all(sentence_law.is_punctuated(T, i) for i in ([a - 1] if a > 0 else []) + [b]):
 627 | +            continue
 628 | +        rows.append(k)
 629 | +    return rows
 630 | +
 631 | +
 632 | +def tables(sources, ctx, budget_chars):
 633 | +    """Round-robin over the sources (no video crowds out the others) into Tables of at most budget_chars of row text."""
 634 | +    per = [(s, candidate_rows(s)) for s in sources]
 635 | +    order, i = [], 0
 636 | +    while any(i < len(ks) for _, ks in per):
 637 | +        for s, ks in per:
 638 | +            if i < len(ks):
 639 | +                order.append((s, ks[i]))
 640 | +        i += 1
 641 | +    chunks, cur, used = [], [], 0
 642 | +    for s, k in order:
 643 | +        cost = len(SB._q(E.Span(s, k, k).text, 600)) + 40
 644 | +        if cur and used + cost > budget_chars:
 645 | +            chunks.append(cur)
 646 | +            cur, used = [], 0
 647 | +        cur.append((s, k))
 648 | +        used += cost
 649 | +    if cur:
 650 | +        chunks.append(cur)
 651 | +    out = []
 652 | +    for ch in chunks:                                  # each table: its sources' rows in sentence order
 653 | +        srcs = list(dict.fromkeys(s for s, _ in ch))
 654 | +        items = [(s, k, False) for s in srcs for k in sorted(k for t, k in ch if t is s)]
 655 | +        out.append(SB.Table(items))
 656 | +    return out
 657 | +
 658 | +
 659 | +# ── 2 the mining call ──
 660 | +
 661 | +MINE_PROMPT = """You pick MOMENTS for 60-second Bitcoin videos built from other channels' own words: the lines a viewer
 662 | +would stop scrolling for. Below are numbered sentences, transcribed word for word, from recent videos (one block per
 663 | +video). Today is {today}.
 664 | +
 665 | +{note}
 666 | +<sentences>
 667 | +{rows}
 668 | +</sentences>
 669 | +
 670 | +A moment is a range [first id, last id] of 1 to 3 consecutive sentences of ONE video that makes sense heard with
 671 | +nothing before it, states something (not a question) and names Bitcoin.
 672 | +For each moment give:
 673 | +- "scores", integers 0-5: "hook_first_2s" (do its first words grab attention), "quotable", "surprising_fact" (a
 674 | +  surprising number or fact), "stance" (a clear opinion), "stakes" (why it matters, emotion), "stands_alone" (clear
 675 | +  without any context), "contempt_outrage" (contempt or outrage: counted AGAINST the moment)
 676 | +- "names_person": true if it names a person
 677 | +- "risk": every one that applies, from: {risks}
 678 | +  (accusation = crime, fraud, insolvency or dishonesty alleged against a named person or company; partner_attack = one
 679 | +  channel attacking another; imperative = telling the viewer to buy, sell or use leverage; ad_read = a sponsor or ad;
 680 | +  third_party_media = someone else's clip being played; time_sensitive = 'today', 'just', or a price level that dates)
 681 | +- "topics": one to three, from: {topics}
 682 | +- "reason": why it works, at most 20 words (internal note; never shown to anyone)
 683 | +Return at most {n} moments, best first, never two that overlap. Use ids only; never rewrite a sentence.
 684 | +If nothing qualifies, answer {{"moments": []}}.
 685 | +Return ONLY this JSON object: {{"moments": [{{"range": [first, last], "scores": {{...}}, "names_person": false,
 686 | +"risk": [], "topics": [], "reason": "..."}}]}}"""
 687 | +
 688 | +
 689 | +def mine_prompt(table, ctx, topics, n=MAX_MOMENTS_PER_CALL):
 690 | +    return MINE_PROMPT.format(today=ctx.now.strftime("%Y-%m-%d"), note=SB.UNTRUSTED, rows=_rows(table, ctx),
 691 | +                              risks=", ".join(RISKS), topics=", ".join(topics), n=n)
 692 | +
 693 | +
 694 | +def _rows(table, ctx):
 695 | +    out, cur, prev = [], None, None
 696 | +    for r in table.rows:
 697 | +        if prev is not None and r.source is prev.source and r.k != prev.k + 1:
 698 | +            out.append("   ... (sentences not shown here: a range never crosses this line)")
 699 | +        prev = r
 700 | +        if r.source is not cur:
 701 | +            cur = r.source
 702 | +            reg = ctx.channel(cur.channel_id) or {}
 703 | +            age = E.age_hours(cur.published_at, ctx.now)
 704 | +            out.append(f"== {reg.get('display_name') or cur.channel_name} | published "
 705 | +                       f"{'?' if age is None else f'{age:.0f} h'} ago | \"{SB._q(cur.title or '', 120)}\"")
 706 | +        sp = r.span
 707 | +        dur = f"{sp.end - sp.start:4.1f} s" if cur.timing == "word" else "  ?  s"
 708 | +        out.append(f"{r.n} | {SB._mmss(sp.start)} | {dur} | {SB._q(sp.text, 600)}")
 709 | +    return "\n".join(out)
 710 | +
 711 | +
 712 | +def check_moments(obj, table, topics, n=MAX_MOMENTS_PER_CALL):
 713 | +    """The reply contract (rejected, never repaired) -> [(span, fields)]. {"moments": []} is a valid empty answer."""
 714 | +    SB._keys(obj, ("moments",))
 715 | +    ms = obj["moments"]
 716 | +    if not isinstance(ms, list) or len(ms) > n:
 717 | +        raise Rejected(f"'moments' must be a list of at most {n}")
 718 | +    out, used = [], {}
 719 | +    for i, m in enumerate(ms):
 720 | +        what = f"moment {i + 1}"
 721 | +        if not isinstance(m, dict):
 722 | +            raise Rejected(f"{what} is not an object")
 723 | +        SB._keys(m, ("range", "scores", "names_person", "risk", "topics", "reason"))
 724 | +        sp = SB._range(m["range"], table, what)
 725 | +        for k in range(sp.k0, sp.k1 + 1):
 726 | +            if (sp.source.video_id, k) in used:
 727 | +                raise Rejected(f"{what} overlaps {used[(sp.source.video_id, k)]}")
 728 | +            used[(sp.source.video_id, k)] = what
 729 | +        sc = m["scores"]
 730 | +        if not isinstance(sc, dict) or set(sc) != set(AXES):
 731 | +            raise Rejected(f"{what}: 'scores' must have exactly {list(AXES)}")
 732 | +        for a in AXES:
 733 | +            if type(sc[a]) is not int or not 0 <= sc[a] <= 5:
 734 | +                raise Rejected(f"{what}: score {a} must be an integer 0-5")
 735 | +        if type(m["names_person"]) is not bool:
 736 | +            raise Rejected(f"{what}: 'names_person' must be true or false")
 737 | +        for key, allowed, lo, hi in (("risk", RISKS, 0, len(RISKS)), ("topics", topics, 1, 3)):
 738 | +            v = m[key]
 739 | +            if not isinstance(v, list) or not lo <= len(v) <= hi or len(set(v)) != len(v) or \
 740 | +                    any(not isinstance(x, str) or x not in allowed for x in v):
 741 | +                raise Rejected(f"{what}: '{key}' must be {lo}-{hi} distinct values from the given list")
 742 | +        if not isinstance(m["reason"], str) or not m["reason"].strip() or len(m["reason"]) > REASON_MAX:
 743 | +            raise Rejected(f"{what}: 'reason' must be a short non-empty string")
 744 | +        out.append((sp, m))
 745 | +    return out
 746 | +
 747 | +
 748 | +# ── 3 judging and ranking ──
 749 | +
 750 | +def judge(sp, ctx):
 751 | +    """The moment on its own (it is its own statement: T13 is met by its own sentences; L-s context integrity judges
 752 | +    what it leaves out). Word-timed: as hook and as clip; otherwise as evidence only (on screen after the word pass)."""
 753 | +    own = tuple(E.statement_entry(E.Span(sp.source, k, k)) for k in range(sp.k0, sp.k1 + 1))
 754 | +    if sp.source.timing == "word":
 755 | +        res = {role: E.eligible(sp, replace(ctx, role=role, story=own)) for role in ("hook", "clip")}
 756 | +    else:
 757 | +        res = {"evidence": E.eligible(sp, replace(ctx, role="evidence"))}
 758 | +    return res
 759 | +
 760 | +
 761 | +def rank_score(rec, trend=None, trend_weight=TREND_WEIGHT):
 762 | +    s = rec["scores"]
 763 | +    score = sum(s[a] for a in POSITIVE) - CONTEMPT_WEIGHT * s["contempt_outrage"]
 764 | +    score -= sum(SOFT_RISKS.get(r, 0) for r in rec["risk"])
 765 | +    if trend and trend_weight:
 766 | +        score += trend_weight * max([trend.get(t, 0.0) for t in rec["topics"]] or [0.0])
 767 | +    return score
 768 | +
 769 | +
 770 | +def record(sp, m, ctx, res, mined):
 771 | +    src = sp.source
 772 | +    dur = round(sp.end - sp.start, 2) if src.timing == "word" else None
 773 | +    elig = {role: {"ok": r.ok, "reasons": r.names(), "targets_missed": r.facts.get("targets_missed", [])}
 774 | +            for role, r in res.items()}
 775 | +    reg = ctx.channel(src.channel_id) or {}
 776 | +    return {"schema": "pp.moment/1", "moment_id": moment_id(src, sp.w0, sp.w1), "video_id": src.video_id,
 777 | +            "channel_id": src.channel_id, "channel_name": reg.get("display_name") or src.channel_name,
 778 | +            "published_at": src.published_at, "title": src.title, "transcript_sha256": src.transcript_sha256,
 779 | +            "transcript_method": src.transcript_method, "timing": src.timing, "words": [sp.w0, sp.w1],
 780 | +            "sentences": [sp.k0, sp.k1], "text": sp.text, "start": sp.start, "end": sp.end, "duration_s": dur,
 781 | +            "duration_estimate_s": None if dur is not None else round(sp.end - sp.start, 2),
 782 | +            "speaker": {"turn_change_inside": None, "label": None, "confidence": None, "named": None,
 783 | +                        "named_source": None},
 784 | +            "scores": dict(m["scores"]), "names_person": m["names_person"], "risk": list(m["risk"]),
 785 | +            "topics": list(m["topics"]), "reason": m["reason"], "eligibility": elig,
 786 | +            "on_screen_ok": any(r.ok for role, r in res.items() if role in E.ON_SCREEN), "excluded": sorted(set(m["risk"]) & set(HARD_RISKS)),
 787 | +            "mined": mined}
 788 | +
 789 | +
 790 | +def mine(router, sources, ctx, topics, since=None, optout=frozenset(), log=print, n=MAX_MOMENTS_PER_CALL,
 791 | +         budget_chars=None, attempts=ATTEMPTS, cycle="", recent_h=RECENT_H):
 792 | +    """The cycle's mining pass -> {"moments": [records, ranked], "calls": [...], "rows": n, "skipped": {...}}."""
 793 | +    srcs, skipped = window_sources(sources, ctx, since=since, recent_h=recent_h, optout=optout)
 794 | +    budget = budget_chars or SB.row_budget(MINE_MAX_TOKENS)
 795 | +    out = {"moments": [], "calls": [], "skipped": skipped, "sources": len(srcs), "rows": 0}
 796 | +    model = _MineModel(router)
 797 | +    for ti, table in enumerate(tables(srcs, ctx, budget)):
 798 | +        out["rows"] += len(table)
 799 | +        log_ = []
 800 | +        base = mine_prompt(table, ctx, topics, n)
 801 | +        status, got = SB._ask(model, base, MINE_MAX_TOKENS, lambda obj: check_moments(obj, table, topics, n),
 802 | +                              attempts, log_)
 803 | +        call = {"table": ti, "rows": len(table), "status": status, "attempts": log_}
 804 | +        out["calls"].append(call)
 805 | +        if status != "accepted":
 806 | +            continue
 807 | +        last = log_[-1]
 808 | +        mined = {"by": (last.get("meta") or {}).get("backend"), "prompt_sha256": last.get("prompt_sha256"),
 809 | +                 "reply_sha256": hashlib.sha256((last.get("raw") or "").encode()).hexdigest(),
 810 | +                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cycle": cycle}
 811 | +        for sp, m in got:
 812 | +            out["moments"].append(record(sp, m, ctx, judge(sp, ctx), mined))
 813 | +    seen = {}
 814 | +    for rec in out["moments"]:                          # one record per moment id (a re-mined moment: the last wins)
 815 | +        seen[rec["moment_id"]] = rec
 816 | +    ranked = sorted(seen.values(), key=lambda r: (-rank_score(r), r["moment_id"]))
 817 | +    for i, rec in enumerate(ranked):
 818 | +        rec["rank"], rec["rank_score"] = i + 1, rank_score(rec)
 819 | +    out["moments"] = ranked
 820 | +    return out
 821 | +
 822 | +
 823 | +class _MineModel(SB.Model):
 824 | +    """select_by_id's call loop over the router's "mine" role (law L-x)."""
 825 | +
 826 | +    def __init__(self, router):
 827 | +        self.router, self.name = router, "role:mine"
 828 | +
 829 | +    def complete(self, prompt, max_tokens, seed):
 830 | +        import providers as P
 831 | +        try:
 832 | +            r = self.router.call("mine", prompt, max_tokens, seed)
 833 | +        except P.ProviderError as e:
 834 | +            raise SB.ModelError(str(e)[:300]) from None
 835 | +        except P.ReplayMiss as e:
 836 | +            raise SB.ReplayMiss(str(e)[:300]) from None
 837 | +        except P.SpendLimit as e:
 838 | +            raise SB.SpendLimit(str(e)) from None
 839 | +        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "usage": r.usage,
 840 | +                        "replayed": r.replayed, "tried": r.tried}
 841 | +
 842 | +
 843 | +# ── the exclusion verdict on one moment in its context (law L-u; also the pp-tests harness's exclusion gate) ──
 844 | +
 845 | +EXCLUSION_PROMPT = """You screen ONE moment (the sentences inside <moment>) from a Bitcoin video before it can be clipped
 846 | +into a short video. The text around it is context only.
 847 | +
 848 | +<before>{before}</before>
 849 | +<moment>{moment}</moment>
 850 | +<after>{after}</after>
 851 | +
 852 | +Answer:
 853 | +- "risks": every one that applies to the MOMENT: "accusation" (crime, fraud, insolvency or dishonesty alleged against a
 854 | +  named person or company), "partner_attack" (one Bitcoin channel or host attacking another), "imperative" (telling
 855 | +  the viewer to buy, sell or use leverage), "guaranteed_return", "single_source_breaking" (a breaking factual claim
 856 | +  resting on one unnamed source or rumour), "ad_read" (a sponsor, ad or affiliate pitch), "third_party_media" (someone
 857 | +  else's clip, song or broadcast being played); an empty list if none
 858 | +- "about_bitcoin": "yes" if the moment is about Bitcoin, "no" if it is about another coin or no crypto at all,
 859 | +  "uncertain"
 860 | +- "why": one short line
 861 | +Criticising a policy is not an accusation; a prediction framed as the speaker's own view is not an imperative;
 862 | +naming a company neutrally is not an accusation.
 863 | +Return ONLY this JSON object: {{"risks": [], "about_bitcoin": "yes", "why": "..."}}"""
 864 | +
 865 | +
 866 | +def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7):
 867 | +    """-> {"verdict": "keep" | "exclude", "why", "risks", "backend"}: a deterministic ad-read screen, then the blind
 868 | +    model verdict (role "exclusion_verdict"); any hard risk, a moment not about Bitcoin, an unreadable or uncertain
 869 | +    verdict excludes (law L-m)."""
 870 | +    import providers as P
 871 | +    from story_semantics import quote_data
 872 | +    if AD_MARKERS.search(moment_text or ""):
 873 | +        return {"verdict": "exclude", "why": f"ad-read marker '{AD_MARKERS.search(moment_text).group(0)}'",
 874 | +                "risks": ["ad_read"], "backend": "deterministic"}
 875 | +    try:
 876 | +        r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
 877 | +                                                                     moment=quote_data(moment_text, 1500),
 878 | +                                                                     after=quote_data(after_text, 3000)), 800, seed)
 879 | +        obj = json.loads(r.text.strip())
 880 | +        if not isinstance(obj, dict) or set(obj) != {"risks", "about_bitcoin", "why"} or \
 881 | +                not isinstance(obj["risks"], list) or any(x not in HARD_RISKS for x in obj["risks"]) or \
 882 | +                obj["about_bitcoin"] not in ("yes", "no", "uncertain"):
 883 | +            raise ValueError("the verdict does not match its contract")
 884 | +    except (P.ProviderError, P.SpendLimit, ValueError) as e:
 885 | +        return {"verdict": "exclude", "why": f"no readable verdict ({type(e).__name__}: {str(e)[:160]})",
 886 | +                "risks": [], "backend": None}
 887 | +    if obj["risks"]:
 888 | +        return {"verdict": "exclude", "why": f"{obj['risks']}: {str(obj['why'])[:200]}", "risks": obj["risks"],
 889 | +                "backend": r.backend}
 890 | +    if obj["about_bitcoin"] != "yes":
 891 | +        return {"verdict": "exclude", "why": f"about Bitcoin: {obj['about_bitcoin']}: {str(obj['why'])[:200]}",
 892 | +                "risks": [], "backend": r.backend}
 893 | +    return {"verdict": "keep", "why": str(obj["why"])[:200], "risks": [], "backend": r.backend}
 894 | diff --git a/pipeline/moments_gate_adapter.py b/pipeline/moments_gate_adapter.py
 895 | new file mode 100644
 896 | index 00000000..45268467
 897 | --- /dev/null
 898 | +++ b/pipeline/moments_gate_adapter.py
 899 | @@ -0,0 +1,103 @@
 900 | +#!/usr/bin/env python3
 901 | +"""The pp-tests exam adapter (pipeline_pp_tests, branch pp-tests: tests/adversarial/test_moments_gates.py; corpora
 902 | +format v1, pp.ci_case/1, pp.vo_case/1, pp.excl_case/1). The harness strips "expected" and "provenance" and calls:
 903 | +
 904 | +  context_integrity(case) -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-s
 905 | +  vo_fidelity(case)       -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-o 11 / L-t
 906 | +  exclusion(case)         -> {"verdict": "keep" | "exclude" | "uncertain", "why"}  law L-u
 907 | +
 908 | +These are the SAME gates the packager runs (context_integrity.check_contexts, vo_fidelity.check,
 909 | +moments.exclusion_verdict) behind the same provider config (law L-x). The harness forbids network connections, so the
 910 | +gates' model replies are recorded on a run that may call out (PP_GATES_REPLAY unset; this session's
 911 | +tests/package/run_exam_record.py, which strips "expected" exactly as the harness does) and served offline under the
 912 | +harness (PP_GATES_REPLAY=1). An exchange that was never recorded is a ReplayMiss: the gate answers "fail" / "exclude"
 913 | +with the reason (nothing measured is never a pass, law L-m).
 914 | +"""
 915 | +import os
 916 | +
 917 | +import context_integrity as CI
 918 | +import moments as M
 919 | +import providers as P
 920 | +import vo_fidelity as VF
 921 | +
 922 | +HERE = os.path.dirname(os.path.abspath(__file__))
 923 | +REPO = os.path.dirname(HERE)
 924 | +RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "package", "fixtures", "gate_replies")
 925 | +SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
 926 | +ENV = "/home/ultron/protocol_pulse/" + "." + "env"
 927 | +_router = None
 928 | +
 929 | +
 930 | +def router():
 931 | +    global _router
 932 | +    if _router is None:
 933 | +        _router = P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
 934 | +                           spend_path=SPEND, limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "40")))
 935 | +    return _router
 936 | +
 937 | +
 938 | +def _join(sentences):
 939 | +    return " ".join(s["text"] for s in sentences or [])
 940 | +
 941 | +
 942 | +def context_integrity(case):
 943 | +    w = case["window"]
 944 | +    n0, n1 = w["selected"]
 945 | +    parts, prev_turn = [], None
 946 | +    for s in w["sentences"]:                     # the caption's own speaker-turn markers, when it has them
 947 | +        t = s["text"]
 948 | +        if s.get("turn") is not None and prev_turn is not None and s["turn"] != prev_turn:
 949 | +            t = "[another speaker] " + t
 950 | +        if s.get("speaker"):
 951 | +            t = f"{s['speaker']}: " + t
 952 | +        prev_turn = s.get("turn")
 953 | +        parts.append(f"<selected>{t}</selected>" if n0 <= s["n"] <= n1 else t)
 954 | +    pkg = case["package"]
 955 | +    segs = [{"label": s["label"], "video_id": s["video_id"], "channel": s["channel"], "text": s["text"],
 956 | +             "role": s.get("role")} for s in pkg["segments"]]
 957 | +    moment = [s["label"] for s in pkg["segments"] if s.get("role") == "moment"]
 958 | +    if len(moment) != 1:
 959 | +        return {"verdict": "fail", "why": f"the case names {len(moment)} moment segments (expected 1)"}
 960 | +    src = case.get("source") or {}
 961 | +    contexts = {moment[0]: {"text": " ".join(parts), "title": src.get("title") or "", "channel": src.get("channel") or "",
 962 | +                            "published": str(src.get("published_at") or "unknown")[:16],
 963 | +                            "show_date": pkg.get("date") or "unknown"}}
 964 | +    package = {"segments": segs, "vo": {"intro": pkg["vo"].get("intro") or "", "bridges": list(pkg["vo"].get("bridges")
 965 | +                                                                                            or []),
 966 | +                                        "signoff": pkg["vo"].get("signoff") or ""},
 967 | +               "title": pkg.get("title") or "", "caption": pkg.get("caption") or ""}
 968 | +    try:
 969 | +        res = CI.check_contexts(router(), package, contexts, writer_vendor=None)
 970 | +    except P.ReplayMiss as e:
 971 | +        return {"verdict": "fail", "why": f"no recorded verdict (replay): {str(e)[:160]}"}
 972 | +    if res["ok"]:
 973 | +        return {"verdict": "pass", "why": "own sincere assertion; referents and conditions inside; entailed; no false relation"}
 974 | +    return {"verdict": "fail", "why": "; ".join(f"{v['segment']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}
 975 | +
 976 | +
 977 | +def vo_fidelity(case):
 978 | +    man = case.get("manifest") or {}
 979 | +    segments = {}
 980 | +    for s in case["segments"]:
 981 | +        names = [s["channel"]] + ([s["speaker"]] if s.get("speaker") else [])
 982 | +        segments[s["label"]] = {"speaker": s.get("speaker") or s["channel"], "names": names, "video_id": s["video_id"],
 983 | +                                "text": _join(s["sentences"])}
 984 | +    lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
 985 | +             for i, ln in enumerate(case["lines"])]
 986 | +    try:
 987 | +        res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man)
 988 | +    except P.ReplayMiss as e:
 989 | +        return {"verdict": "fail", "why": f"no recorded verdict (replay): {str(e)[:160]}"}
 990 | +    if res["ok"]:
 991 | +        return {"verdict": "pass", "why": "every claim bound to its speaker's words; verdict yes with verbatim support"}
 992 | +    return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}
 993 | +
 994 | +
 995 | +def exclusion(case):
 996 | +    try:
 997 | +        res = M.exclusion_verdict(router(), _join(case["moment"]["sentences"]),
 998 | +                                  _join((case.get("context") or {}).get("before")),
 999 | +                                  _join((case.get("context") or {}).get("after")))
1000 | +    except P.ReplayMiss as e:
1001 | +        return {"verdict": "exclude", "why": f"no recorded verdict (replay): {str(e)[:160]}"}
1002 | +    return {"verdict": res["verdict"], "why": res["why"]}
1003 | diff --git a/pipeline/package.py b/pipeline/package.py
1004 | new file mode 100644
1005 | index 00000000..54305a21
1006 | --- /dev/null
1007 | +++ b/pipeline/package.py
1008 | @@ -0,0 +1,698 @@
1009 | +#!/usr/bin/env python3
1010 | +"""pipeline/package.py — STEP 2 PACKAGE + STEP 3 OPTIMISE (law L-q, '01:55'; laws L-s..L-w, '02:30'): the set of
1011 | +moments that makes the best 60-70 s video, the angle that ties them, and the PBX MAX VO. The moments need not share a
1012 | +development: under moments-first there is no same-event test at all (orchestrator 03:00).
1013 | +
1014 | +CODE (deterministic, law L-w 1):
1015 | +  usable()          moments a package may use: on screen eligible (word timing, law L-e), no hard-exclusion risk
1016 | +                    (L-u), not delivered in the previous 24 h (novelty, L-p), channel not opted out, <= 20 s (L-u),
1017 | +                    a time-sensitive moment only from a source <= TIME_SENSITIVE_H old (L-v 3)
1018 | +  candidate_sets()  hook + 2-3 clips, every segment from a DIFFERENT channel (L-u: one clip per channel per video;
1019 | +                    >= 2 channels follows), the runtime arithmetic: segments + VO + FIXED_S inside 60-70 s (L-o) with
1020 | +                    the VO's length as the slack (L-w 1); ranked by the moments' scores, topic diversity, at most one
1021 | +                    price prediction (L-u)
1022 | +WRITER (role "angle_write", law L-w 1: a frontier model until the A/B shows local meets the bar): picks one set, its
1023 | +  type ("story" when every segment states one development, else "moments"), the order (hook first), the angle, the VO
1024 | +  intro and bridges with word budgets computed by code, ONE title, ONE caption (L-t), each line citing moment ids.
1025 | +  The sign-off is code: the credit set, hook first (law L-a: credits = EDL set = spoken sign-off).
1026 | +GATES (both hard): vo_fidelity.check (deterministic + blind verdict on VO, title, caption; L-o 11, L-t) and
1027 | +  context_integrity.check (L-s). A VO failure: regenerate once with the violations, then a PLAIN factual VO (L-w 2:
1028 | +  "Next, <show> on <topic>."); a context failure: extend the clip backwards by whole sentences (<= 2) and check again,
1029 | +  or drop the MOMENT and repack from the next set; an exclusion failure drops the moment.
1030 | +OUTPUT pp.package/1 (contract in STATE): segments (moment ids, verbatim text, times), VO, title, caption, the hook's
1031 | +  first words, the checks, the model per artefact, dollars.
1032 | +"""
1033 | +import itertools
1034 | +import json
1035 | +import re
1036 | +import time
1037 | +
1038 | +import context_integrity as CI
1039 | +import eligibility as E
1040 | +import trend_brief as TB
1041 | +import vo_fidelity as VF
1042 | +
1043 | +SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
1044 | +N_CLIPS = (2, 3)                   # hook + 2-3 clips (eligibility.N_CLIPS)
1045 | +RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the one hard length rule
1046 | +WPS = 2.6                          # PBX MAX VO words per second: an ASSUMPTION until the render measures it
1047 | +SIGNOFF_WORDS = 18                 # the preview's sign-off ("Clips today from A, B, and C. Go follow them ...")
1048 | +FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO (~7.4 s)
1049 | +VO_S = (6.0, 22.0)                 # the VO's seconds (intro + bridges), the slack that lands the runtime
1050 | +TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
1051 | +TOP_SETS = 6                       # sets offered to the writer
1052 | +PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
1053 | +PRESCREEN_BATCH = 8                # excerpts per step-A call
1054 | +MAX_HOOKS = 10
1055 | +PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
1056 | +
1057 | +
1058 | +def channel_of(m):
1059 | +    return m["channel_id"]
1060 | +
1061 | +
1062 | +def usable(moments, ctx, delivered=(), optout=frozenset()):
1063 | +    out, why = [], {}
1064 | +    for m in moments:
1065 | +        mid = m["moment_id"]
1066 | +        if not m.get("on_screen_ok"):
1067 | +            why[mid] = "not eligible on screen: " + "; ".join(
1068 | +                f"{r}: {', '.join(v['reasons'])}" for r, v in (m.get("eligibility") or {}).items() if not v["ok"])
1069 | +        elif m.get("excluded"):
1070 | +            why[mid] = f"hard exclusion (L-u): {m['excluded']}"
1071 | +        elif mid in delivered:
1072 | +            why[mid] = "delivered in the previous 24 h"
1073 | +        elif m["channel_id"] in optout:
1074 | +            why[mid] = "channel opted out"
1075 | +        elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
1076 | +            why[mid] = f"{m.get('duration_s')} s: over the {SEG_MAX_S} s per source video (L-u) or unmeasured"
1077 | +        elif "time_sensitive" in m.get("risk", []) and (E.age_hours(m["published_at"], ctx.now) or 1e9) > TIME_SENSITIVE_H:
1078 | +            why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
1079 | +        elif (m.get("speaker") or {}).get("turn_change_inside") is True:
1080 | +            why[mid] = "a speaker change inside (L-v 1)"
1081 | +        else:
1082 | +            out.append(m)
1083 | +    return out, why
1084 | +
1085 | +
1086 | +def runtime(segs, vo_s):
1087 | +    return round(sum(m["duration_s"] for m in segs) + vo_s + FIXED_S, 2)
1088 | +
1089 | +
1090 | +def content_range():
1091 | +    """Seconds the segments may fill so that some VO length inside VO_S lands the runtime in 60-70 s."""
1092 | +    return RUNTIME_S[0] - FIXED_S - VO_S[1], RUNTIME_S[1] - FIXED_S - VO_S[0]
1093 | +
1094 | +
1095 | +def candidate_sets(ms, k=TOP_SETS):
1096 | +    """Deterministic: hooks = moments eligible as a hook (by hook_first_2s, then rank); for each hook, the best clip
1097 | +    combinations of 2-3 moments from other channels (one segment per channel), inside content_range(); scored by the
1098 | +    moments' rank scores + topic diversity, at most PRICE_PREDICTIONS_MAX price predictions. Distinct sets, best first."""
1099 | +    lo, hi = content_range()
1100 | +    hooks = sorted([m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")],
1101 | +                   key=lambda m: (-m["scores"]["hook_first_2s"], -m["rank_score"], m["moment_id"]))[:MAX_HOOKS]
1102 | +    clips = sorted([m for m in ms if (m.get("eligibility") or {}).get("clip", {}).get("ok")],
1103 | +                   key=lambda m: (-m["rank_score"], m["moment_id"]))[:24]
1104 | +    sets = []
1105 | +    for h in hooks:
1106 | +        pool = [c for c in clips if channel_of(c) != channel_of(h)]
1107 | +        for n in N_CLIPS:
1108 | +            for combo in itertools.combinations(pool, n):
1109 | +                chans = {channel_of(h)} | {channel_of(c) for c in combo}
1110 | +                if len(chans) != n + 1:
1111 | +                    continue
1112 | +                segs = [h, *combo]
1113 | +                dur = sum(m["duration_s"] for m in segs)
1114 | +                if not lo <= dur <= hi:
1115 | +                    continue
1116 | +                if sum("price_prediction" in m["risk"] for m in segs) > PRICE_PREDICTIONS_MAX:
1117 | +                    continue
1118 | +                topics = {t for m in segs for t in m["topics"]}
1119 | +                score = sum(m["rank_score"] for m in segs) + 1.5 * len(topics) + 2 * h["scores"]["hook_first_2s"]
1120 | +                sets.append((score, [m["moment_id"] for m in segs], segs))
1121 | +    sets.sort(key=lambda x: (-x[0], x[1]))
1122 | +    out, seen = [], set()
1123 | +    for score, ids, segs in sets:
1124 | +        key = frozenset(ids)
1125 | +        if key in seen or any(len(key & frozenset(o["ids"])) >= len(ids) - 1 for o in out):
1126 | +            continue                                   # distinct: no two offered sets differ by one moment only
1127 | +        seen.add(key)
1128 | +        out.append({"ids": ids, "segments": segs, "score": round(score, 2),
1129 | +                    "content_s": round(sum(m["duration_s"] for m in segs), 2)})
1130 | +        if len(out) >= k:
1131 | +            break
1132 | +    return out
1133 | +
1134 | +
1135 | +WRITE_PROMPT = """You are the editor and voice of PBX MAX, a 60-second Bitcoin video made of other channels' own words.
1136 | +Below are candidate SETS of clips. Each clip is a verbatim quote, with the channel that said it. The channels were NOT
1137 | +in one conversation (unless two clips share a video), and nobody here is answering anyone else.
1138 | +
1139 | +{note}
1140 | +{sets}
1141 | +
1142 | +Pick ONE set and write:
1143 | +- "set": its number; "order": its clip ids in play order, the hook first (the hook is the clip marked HOOK)
1144 | +- "type": "story" if every clip states the same development, else "moments"
1145 | +- "angle": one sentence: the point these clips make together (for the editor; it is checked like the VO)
1146 | +- "intro": the voice-over before the hook, at most {intro_words} words. The hook plays, then the first clip right
1147 | +  after it (no voice-over between them). "bridges": one voice-over line after each clip except the last (so a set of
1148 | +  a hook and 3 clips has 2 bridges; a hook and 2 clips has 1), each at most {bridge_words} words; a bridge names the
1149 | +  channel of the NEXT clip ("Next, Coin Bureau on ..."). The voice-over may make a point, but ONLY one the clips
1150 | +  themselves state.
1151 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
1152 | +Every line (intro, each bridge, title, caption) gives "cites": the ids of the clips it relies on.
1153 | +RULES (a line that breaks one is rejected):
1154 | +- every number, name, claim and time word ("today", "just") must be said in a cited clip, as the clip says it
1155 | +- attribute a view only to the channel that said it; never say or imply that channels agree, answer, rebut or react to
1156 | +  each other; no "both", "meanwhile ... fires back", "but X disagrees"
1157 | +- never stronger than the clip ("could" stays "could"); no "destroys", "slams", "exposes", "admits", "confirms",
1158 | +  "caught" unless the clip uses that word; no advice to the viewer to buy, sell or use leverage
1159 | +- no quotes except the clip's exact words; no names of people who are not speaking in or named by a clip
1160 | +Return ONLY this JSON object: {{"set": 1, "order": ["id", ...], "type": "moments", "angle": "...",
1161 | +"intro": {{"text": "...", "cites": ["id"]}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
1162 | +"title": {{"text": "...", "cites": ["id"]}}, "caption": {{"text": "...", "cites": ["id"]}}}}"""
1163 | +
1164 | +
1165 | +def _sets_block(sets, ctx):
1166 | +    from story_semantics import quote_data
1167 | +    out = []
1168 | +    for i, s in enumerate(sets, 1):
1169 | +        out.append(f"SET {i} ({s['content_s']:.1f} s of clips):")
1170 | +        for j, m in enumerate(s["segments"]):
1171 | +            reg = ctx.channel(m["channel_id"]) or {}
1172 | +            out.append(f'  {"HOOK" if j == 0 else "clip"} id={m["moment_id"]} | {reg.get("display_name") or m["channel_name"]}'
1173 | +                       f' | {m["duration_s"]:.1f} s | topics {", ".join(TB.label(t) for t in m["topics"])} | '
1174 | +                       f'"{quote_data(m["text"], 700)}"')
1175 | +    return "\n".join(out)
1176 | +
1177 | +
1178 | +def budgets(content_s):
1179 | +    """Word budgets so the VO lands the runtime: VO seconds = target - FIXED_S - content, split intro / bridges."""
1180 | +    target = (RUNTIME_S[0] + RUNTIME_S[1]) / 2
1181 | +    vo_s = max(VO_S[0], min(VO_S[1], target - FIXED_S - content_s))
1182 | +    words = int(vo_s * WPS)
1183 | +    return max(6, int(words * 0.4)), max(5, int(words * 0.3)), vo_s
1184 | +
1185 | +
1186 | +def check_written(obj, sets):
1187 | +    """The writer's reply contract (strict; never repaired) -> (set, order, fields)."""
1188 | +    keys = {"set", "order", "type", "angle", "intro", "bridges", "title", "caption"}
1189 | +    if not isinstance(obj, dict) or set(obj) != keys:
1190 | +        raise ValueError(f"keys must be exactly {sorted(keys)}")
1191 | +    if type(obj["set"]) is not int or not 1 <= obj["set"] <= len(sets):
1192 | +        raise ValueError("'set' must be one of the offered set numbers")
1193 | +    s = sets[obj["set"] - 1]
1194 | +    if not isinstance(obj["order"], list) or sorted(obj["order"]) != sorted(s["ids"]) or obj["order"][0] != s["ids"][0]:
1195 | +        raise ValueError("'order' must be the set's ids, each once, the hook first")
1196 | +    if obj["type"] not in ("story", "moments") or not isinstance(obj["angle"], str) or not obj["angle"].strip():
1197 | +        raise ValueError("'type' must be story or moments; 'angle' a sentence")
1198 | +    lines = [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])]
1199 | +    if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != len(s["ids"]) - 2:
1200 | +        raise ValueError(f"'bridges' must hold {len(s['ids']) - 2} lines (one after each clip but the last; none "
1201 | +                         "between the hook and the first clip)")
1202 | +    lines += [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]
1203 | +    for slot, ln in lines:
1204 | +        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
1205 | +                not ln["text"].strip() or not isinstance(ln["cites"], list) or \
1206 | +                any(c not in s["ids"] for c in ln["cites"]):
1207 | +            raise ValueError(f"{slot}: needs text and cites from the set's ids")
1208 | +    if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
1209 | +        raise ValueError("title <= 70 characters, caption <= 220")
1210 | +    return s, obj["order"], obj
1211 | +
1212 | +
1213 | +def signoff(segs, ctx):
1214 | +    """L-a: the spoken sign-off names exactly the credit set, hook first (code, never the model)."""
1215 | +    names = [(ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"] for m in segs]
1216 | +    names = list(dict.fromkeys(names))
1217 | +    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f", and {names[-1]}"
1218 | +    return f"Clips today from {who}. Go follow them for more. Links are below."
1219 | +
1220 | +
1221 | +def plain_vo(segs, ctx):
1222 | +    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."), its topic the one every segment names by
1223 | +    rule (Bitcoin), so it claims nothing beyond who speaks."""
1224 | +    name = lambda m: (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
1225 | +    first = segs[0]
1226 | +    intro = {"text": f"Here's {name(first)} on Bitcoin.", "cites": [first["moment_id"]]}
1227 | +    bridges = [{"text": f"Next, {name(m)} on Bitcoin.", "cites": [m["moment_id"]]} for m in segs[2:]]
1228 | +    chans = list(dict.fromkeys(name(m) for m in segs))
1229 | +    title = {"text": (f"Bitcoin: {', '.join(chans[:-1])} and {chans[-1]}")[:70], "cites": [m["moment_id"] for m in segs]}
1230 | +    caption = {"text": f"Clips from {', '.join(chans)}. Links to every source below.",
1231 | +               "cites": [m["moment_id"] for m in segs]}
1232 | +    return intro, bridges, title, caption
1233 | +
1234 | +
1235 | +def assemble(order, by_id, fields, ctx, vo_kind):
1236 | +    segs = [by_id[i] for i in order]
1237 | +    reg = lambda m: (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
1238 | +    lines = [dict(fields["intro"], slot="intro")] + \
1239 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
1240 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
1241 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
1242 | +    pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
1243 | +          "vo_kind": vo_kind,
1244 | +          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
1245 | +                        "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": reg(m),
1246 | +                        "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
1247 | +                        "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
1248 | +                        "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
1249 | +                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
1250 | +                       for i, m in enumerate(segs)],
1251 | +          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
1252 | +                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
1253 | +                 "signoff": signoff(segs, ctx)},
1254 | +          "title": fields["title"]["text"], "caption": fields["caption"]["text"],
1255 | +          "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
1256 | +          "lines": lines}
1257 | +    vo_s = vo_words / WPS + len(pk["vo"]["signoff"].split()) / WPS - SIGNOFF_WORDS / WPS
1258 | +    pk["runtime_s_estimate"] = runtime(segs, vo_s)
1259 | +    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words at "
1260 | +                          f"{WPS} w/s (assumed) + fixed {FIXED_S} s; the render measures the final")
1261 | +    return pk
1262 | +
1263 | +
1264 | +def gates(router, pk, by_id, sources, writer_vendor, a_by_moment=None):
1265 | +    segs_v = {s["moment_id"]: {"speaker": s["channel"], "names": [s["channel"]], "video_id": s["video_id"],
1266 | +                               "text": s["text"]} for s in pk["segments"]}
1267 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
1268 | +    fid = VF.check(router, segs_v, lines, writer_vendor)
1269 | +    a_by = None
1270 | +    if a_by_moment is not None:
1271 | +        a_by = {s["label"]: dict(a_by_moment[s["moment_id"]], label=s["label"]) for s in pk["segments"]}
1272 | +    ctx_ = CI.check_contexts(router, pk, CI.contexts_from_sources(pk, sources), writer_vendor, a_by=a_by)
1273 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
1274 | +    return {"fidelity": fid, "context": ctx_, "runtime_ok": rt_ok,
1275 | +            "ok": fid["ok"] and ctx_["ok"] and rt_ok}
1276 | +
1277 | +
1278 | +def write(router, sets, ctx, extra="", seed=7):
1279 | +    from select_by_id import UNTRUSTED
1280 | +    content = min(s["content_s"] for s in sets)
1281 | +    iw, bw, _ = budgets(content)
1282 | +    prompt = WRITE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), sets=_sets_block(sets, ctx),
1283 | +                                 intro_words=iw, bridge_words=bw)
1284 | +    if extra:
1285 | +        prompt += "\n\nYour previous script was rejected: " + extra[:1200] + "\nWrite it again, fixing exactly that."
1286 | +    r = router.call("angle_write", prompt, 3000, seed)
1287 | +    return r, check_written(json.loads(r.text.strip()), sets)
1288 | +
1289 | +
1290 | +def prescreen(router, ms, sources, ctx, n=PRESCREEN_N, batch=PRESCREEN_BATCH, writer_vendor="openai"):
1291 | +    """Step A (context only, package-independent by law L-s) on the best n usable moments, best first with distinct
1292 | +    channels first: {moment_id: A item}, {moment_id: [failing rules]}. The verdict is reused in the final decision.
1293 | +    writer_vendor: the vendor that will WRITE, so step A never runs on it."""
1294 | +    seen, order = set(), []
1295 | +    for m in sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"])):
1296 | +        if m["channel_id"] not in seen:
1297 | +            order.append(m)
1298 | +            seen.add(m["channel_id"])
1299 | +    order += [m for m in sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"])) if m not in order]
1300 | +    order = order[:n]
1301 | +    a_by, fails, vendors = {}, {}, set()
1302 | +    for i in range(0, len(order), batch):
1303 | +        chunk = order[i:i + batch]
1304 | +        contexts = {}
1305 | +        for m in chunk:
1306 | +            text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1])
1307 | +            contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
1308 | +                                        "channel": (ctx.channel(m["channel_id"]) or {}).get("display_name")
1309 | +                                        or m["channel_name"], "window": win,
1310 | +                                        "published": str(m.get("published_at") or "")[:16],
1311 | +                                        "show_date": ctx.now.strftime("%Y-%m-%d")}
1312 | +        try:
1313 | +            got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i)
1314 | +            vendors.add(router.backends[backend].vendor if backend in router.backends else backend)
1315 | +        except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
1316 | +            for m in chunk:
1317 | +                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
1318 | +            continue
1319 | +        for mid, a in got.items():
1320 | +            a_by[mid] = a
1321 | +            fails[mid] = CI.a_failures(a)
1322 | +    return a_by, fails, vendors
1323 | +
1324 | +
1325 | +# ── angle first (orchestrator review 03:40: "select by angle, not by score") ──
1326 | +
1327 | +SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
1328 | +MAX_ANGLES = 5
1329 | +REWRITES = 3                       # a fidelity reject: up to 3 rewrites with the exact rejected claims, then plain VO
1330 | +COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
1331 | +VO_DEPENDENT = ("NOT_ENTAILED", "POLARITY", "STRONGER", "FALSE_RELATION")   # context failures the VO's framing causes
1332 | +VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than its speaker said in context: frame it as "
1333 | +                          "exactly what the speaker says",
1334 | +          "POLARITY": "the framing flips what the speaker meant: frame it as the speaker's own view",
1335 | +          "STRONGER": "the framing makes the speaker sound more certain than they were: keep their hedges ('I think', "
1336 | +                      "'could')",
1337 | +          "FALSE_RELATION": "the voice-over makes these speakers look like they respond to or agree WITH each other: "
1338 | +                            "credit each view to its own speaker, separately"}
1339 | +PRESENT = re.compile(r"\b(is|are|now|today|currently|right now|trading|sitting|this morning|tonight|at the moment|"
1340 | +                     r"just)\b", re.I)
1341 | +
1342 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
1343 | +voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
1344 | +checks. The channels were not in one conversation and never answer each other.
1345 | +
1346 | +{note}
1347 | +{clips}
1348 | +
1349 | +Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repeat: a point that several of these clips
1350 | +GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
1351 | +the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
1352 | +it is today's.
1353 | +The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
1354 | +seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
1355 | +sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
1356 | +from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
1357 | +attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
1358 | +Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
1359 | +"support": {{"id": "..."}}}}]}}"""
1360 | +
1361 | +WRITE_V2 = """You are PBX MAX, the voice of a 60-second Bitcoin video made of other channels' own words.
1362 | +THE ANGLE (the point this video makes): "{angle}"
1363 | +The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
1364 | +
1365 | +{note}
1366 | +{lineup}
1367 | +
1368 | +Write:
1369 | +- "intro": the voice-over before the hook, at most {intro_words} words: set up the angle so the viewer knows why to
1370 | +  listen. The hook plays, then clip 1 right after it (no voice-over between them).
1371 | +- "bridges": one line after each clip except the last ({n_bridges} lines), each at most {bridge_words} words: move the
1372 | +  point forward and name the channel of the NEXT clip.
1373 | +- "title": ONE title, at most 70 characters, that states the angle; "caption": ONE caption, at most 220 characters.
1374 | +Every line gives "cites": the ids of the clips it relies on.
1375 | +RULES (a line that breaks one is rejected):
1376 | +- make the angle's point THROUGH ATTRIBUTION: say what each channel says ("Saifedean Ammous: no authority can take
1377 | +  your Bitcoin"), and tie the clips with short lines that add no claim of your own ("Three channels, one thread.");
1378 | +  every number, name and time word must be said in a cited clip, as the clip says it; never make a clip sound more
1379 | +  certain than it is ("could" stays "could", "I think" stays an opinion)
1380 | +- attribute a view only to the channel that said it; each channel speaks for itself: never say or imply that channels
1381 | +  agree WITH each other, answer, rebut or react to each other (independent views on one point are fine)
1382 | +- do not repeat a clip's own words in the line right before it or in the title: the clip says them
1383 | +- no price level or move in the intro, title or caption unless it is today's level, or you mark it as history
1384 | +  ("from the 2022 low ...")
1385 | +- no "destroys", "slams", "exposes", "admits", "confirms", "caught" unless the clip uses that word; no advice to buy,
1386 | +  sell or use leverage; no quotes except the clip's exact words; no names of people who are not speaking
1387 | +{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": ["id"]}}, "bridges": [{{"text": "...",
1388 | +"cites": ["id"]}}], "title": {{"text": "...", "cites": ["id"]}}, "caption": {{"text": "...", "cites": ["id"]}}}}"""
1389 | +
1390 | +COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
1391 | +different person's own words).
1392 | +
1393 | +{package}
1394 | +
1395 | +1) State the video's through-line in ONE sentence, or "none" if it has none.
1396 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
1397 | +3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
1398 | +   1 = no point, or a point the clips do not support).
1399 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "vo_point": 1}}"""
1400 | +
1401 | +
1402 | +def current_levels(sources, ctx, hours=24.0):
1403 | +    """The Bitcoin price levels this universe states as CURRENT: numbers 10,000-500,000 in sentences that name Bitcoin
1404 | +    and speak in the present ('is', 'now', 'today', 'trading', ...), from sources <= `hours` old (L-v 3)."""
1405 | +    out = set()
1406 | +    for src in sources:
1407 | +        age = E.age_hours(src.published_at, ctx.now)
1408 | +        if age is None or age > hours:
1409 | +            continue
1410 | +        for a, b in src.sentences:
1411 | +            t = E.spoken(src.tokens[a:b + 1])
1412 | +            if E.names_bitcoin(t) and PRESENT.search(t) and not VF.HISTORY.search(t):
1413 | +                out |= {v for v in VF.price_levels(t) if 10_000 <= v <= 500_000}
1414 | +    return sorted(out)
1415 | +
1416 | +
1417 | +def check_angles(obj, by_id, k=MAX_ANGLES):
1418 | +    if not isinstance(obj, dict) or set(obj) != {"angles"} or not isinstance(obj["angles"], list) or \
1419 | +            not 1 <= len(obj["angles"]) <= k:
1420 | +        raise ValueError(f"exactly {{'angles': [1-{k} items]}}")
1421 | +    out = []
1422 | +    for i, a in enumerate(obj["angles"]):
1423 | +        if not isinstance(a, dict) or set(a) != {"angle", "moments", "hook", "support"}:
1424 | +            raise ValueError(f"angle {i + 1}: keys must be exactly angle, moments, hook, support")
1425 | +        ms = a["moments"]
1426 | +        if not isinstance(a["angle"], str) or not a["angle"].strip() or not isinstance(ms, list) or \
1427 | +                not 3 <= len(ms) <= 8 or len(set(ms)) != len(ms) or any(m not in by_id for m in ms):
1428 | +            raise ValueError(f"angle {i + 1}: a sentence and 3-8 distinct offered ids")
1429 | +        if len({by_id[m]["channel_id"] for m in ms}) < 3 or a["hook"] not in ms:
1430 | +            raise ValueError(f"angle {i + 1}: >= 3 channels (one clip per channel, L-u), and the hook one of its moments")
1431 | +        if not isinstance(a["support"], dict) or set(a["support"]) != set(ms):
1432 | +            raise ValueError(f"angle {i + 1}: 'support' needs exactly its moment ids")
1433 | +        out.append(a)
1434 | +    return out
1435 | +
1436 | +
1437 | +def lineup_for(angle, by_id, dropped=frozenset()):
1438 | +    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
1439 | +    2 s), clips from the angle's other moments, every segment from a different channel (L-u), the runtime arithmetic,
1440 | +    a clip under SHORT_CLIP_S only as the last (the punchline). Best by the proposer's order. None if impossible."""
1441 | +    ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
1442 | +    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
1443 | +    hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
1444 | +    lo, hi = content_range()
1445 | +    for h in hooks:
1446 | +        pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
1447 | +                and m["channel_id"] != h["channel_id"]]
1448 | +        best = None
1449 | +        for n in (3, 2):
1450 | +            for combo in itertools.combinations(pool, n):
1451 | +                if len({m["channel_id"] for m in combo}) != n:
1452 | +                    continue
1453 | +                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
1454 | +                shorts = [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]
1455 | +                if shorts:
1456 | +                    continue
1457 | +                dur = h["duration_s"] + sum(m["duration_s"] for m in order)
1458 | +                if not lo <= dur <= hi:
1459 | +                    continue
1460 | +                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
1461 | +                if best is None or key > best[0]:
1462 | +                    best = (key, [h] + order)
1463 | +            if best:
1464 | +                return best[1]
1465 | +    return None
1466 | +
1467 | +
1468 | +def duplicates(pk):
1469 | +    """A clip must add something (orchestrator 03:40): no VO line right before a clip, and no title, repeats the
1470 | +    clip's words (a run of >= 5 canonical tokens, or >= 60 % of a short clip's tokens)."""
1471 | +    out = []
1472 | +    lines = {x["slot"]: x["text"] for x in pk["lines"]}
1473 | +    before = {0: lines.get("intro", "")}
1474 | +    for a, b in zip(pk["vo"]["bridges_after_clip"], pk["vo"]["bridges"]):
1475 | +        before[a + 1] = b
1476 | +    for i, seg in enumerate(pk["segments"]):
1477 | +        ct = VF.ctoks(seg["text"])
1478 | +        for slot, text in (("before " + seg["label"], before.get(i, "")), ("title", lines.get("title", ""))):
1479 | +            lt = VF.ctoks(text)
1480 | +            run5 = any(VF._run_in(ct[j:j + 5], lt) for j in range(max(0, len(ct) - 4)))
1481 | +            share = len([t for t in ct if t in set(lt)]) / max(1, len(ct))
1482 | +            if run5 or (len(ct) <= 15 and share >= 0.6):
1483 | +                out.append({"slot": slot, "rule": "DUPLICATE", "detail": f"repeats the words of {seg['label']}"})
1484 | +    return out
1485 | +
1486 | +
1487 | +def coherence(router, pk, writer_vendor, seed=7):
1488 | +    """The blind QUALITY verdict (a different vendor than the writer): through-line + ratings. -> (ok, verdict)."""
1489 | +    import providers as P
1490 | +    try:
1491 | +        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
1492 | +                        avoid_vendor=writer_vendor)
1493 | +        v = json.loads(r.text.strip())
1494 | +        labels = [sg["label"] for sg in pk["segments"]]
1495 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
1496 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
1497 | +                any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
1498 | +            raise ValueError("coherence verdict out of contract")
1499 | +    except (P.ProviderError, P.SpendLimit, ValueError) as e:
1500 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}"}
1501 | +    ok = str(v["through_line"]).strip().lower() not in ("", "none") and \
1502 | +        min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
1503 | +    return ok, dict(v, backend=r.backend)
1504 | +
1505 | +
1506 | +def _lineup_block(segs, ctx):
1507 | +    from story_semantics import quote_data
1508 | +    return "\n".join(f'{"HOOK" if i == 0 else f"CLIP {i}"} id={m["moment_id"]} | '
1509 | +                     f'{(ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]} | '
1510 | +                     f'{m["duration_s"]:.1f} s | "{quote_data(m["text"], 700)}"' for i, m in enumerate(segs))
1511 | +
1512 | +
1513 | +def write_v2(router, angle, segs, ctx, extra="", seed=7):
1514 | +    from select_by_id import UNTRUSTED
1515 | +    content = sum(m["duration_s"] for m in segs)
1516 | +    iw, bw, _ = budgets(content)
1517 | +    prompt = WRITE_V2.format(angle=angle["angle"].replace('"', "'"), note=UNTRUSTED.replace("<sentences>", "the quotes"),
1518 | +                             lineup=_lineup_block(segs, ctx), intro_words=iw, bridge_words=bw,
1519 | +                             n_bridges=len(segs) - 2, extra=(extra + "\n") if extra else "")
1520 | +    r = router.call("angle_write", prompt, 3000, seed)
1521 | +    obj = json.loads(r.text.strip())
1522 | +    ids = [m["moment_id"] for m in segs]
1523 | +    keys = {"intro", "bridges", "title", "caption"}
1524 | +    if not isinstance(obj, dict) or set(obj) != keys:
1525 | +        raise ValueError(f"keys must be exactly {sorted(keys)}")
1526 | +    if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != len(segs) - 2:
1527 | +        raise ValueError(f"'bridges' must hold {len(segs) - 2} lines")
1528 | +    for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
1529 | +            [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
1530 | +        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
1531 | +                not ln["text"].strip() or not isinstance(ln["cites"], list) or any(c not in ids for c in ln["cites"]):
1532 | +            raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
1533 | +    if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
1534 | +        raise ValueError("title <= 70 characters, caption <= 220")
1535 | +    return r, dict(obj, type="moments", angle=angle["angle"])
1536 | +
1537 | +
1538 | +def integrity(router, pk, sources, writer_vendor, a_by, levels, now=None):
1539 | +    """The hard gates: VO fidelity (deterministic incl. PRICE_NOW + blind verdict), DUPLICATE, context integrity
1540 | +    (A precomputed, B, C), runtime. -> dict with ok and every violation."""
1541 | +    segs_v = {s["moment_id"]: {"speaker": s["channel"], "names": [s["channel"]], "video_id": s["video_id"],
1542 | +                               "text": s["text"]} for s in pk["segments"]}
1543 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
1544 | +    fid = VF.check(router, segs_v, lines, writer_vendor, current_levels=levels)
1545 | +    dup = duplicates(pk)
1546 | +    a_use = None if a_by is None else {s["label"]: dict(a_by[s["moment_id"]], label=s["label"]) for s in pk["segments"]}
1547 | +    ctx_ = CI.check_contexts(router, pk, CI.contexts_from_sources(pk, sources, now), writer_vendor, a_by=a_use)
1548 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
1549 | +    return {"fidelity": fid, "duplicates": dup, "context": ctx_, "runtime_ok": rt_ok,
1550 | +            "fid_ok": fid["ok"] and not dup, "ok": fid["ok"] and not dup and ctx_["ok"] and rt_ok}
1551 | +
1552 | +
1553 | +def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, want=1, max_angles=MAX_ANGLES,
1554 | +          truth_dir=None):
1555 | +    """Angle first (orchestrator 03:40). usable -> step-A prescreen -> ANGLES (role angle_write) -> per angle: line-up
1556 | +    (code) -> write -> integrity gates (hard) -> on a fidelity reject up to REWRITES rewrites with the exact rejected
1557 | +    claims -> COHERENCE (blind quality verdict, other vendor) -> law L-v 2 second recognition pass on the segments
1558 | +    (truth_dir set) -> a package. A context / truth failure drops that moment and rebuilds the angle's line-up; a
1559 | +    coherence failure moves to the next angle. The plain VO is the last resort, ranked below every written VO.
1560 | +    -> {"packages": [best first], "package": the best or None, "tried": [...], ...}."""
1561 | +    import transcript_truth as TT
1562 | +    ms, why = usable(moments, ctx, delivered, optout)
1563 | +    writer_vendor = _writer_vendor(router)
1564 | +    a_by, fails, a_vendors = prescreen(router, ms, sources, ctx, writer_vendor=writer_vendor)
1565 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
1566 | +    levels = current_levels(sources.values(), ctx)
1567 | +    out = {"packages": [], "plain": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
1568 | +           "prescreen": {"screened": len(fails), "cleared": len(cleared),
1569 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": []}
1570 | +    if len({m["channel_id"] for m in cleared.values()}) < 3:
1571 | +        out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
1572 | +        out["package"] = None
1573 | +        return out
1574 | +    from select_by_id import UNTRUSTED
1575 | +    from story_semantics import quote_data
1576 | +    clips = "\n".join(f'id={m["moment_id"]} | {(ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]}'
1577 | +                      f' | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
1578 | +                      for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
1579 | +    try:
1580 | +        lo, hi = content_range()
1581 | +        r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
1582 | +                                                           clips=clips, k=max_angles, lo=lo, hi=hi), 3000, 7)
1583 | +        angles = check_angles(json.loads(r.text.strip()), cleared, max_angles)
1584 | +    except Exception as e:
1585 | +        out["why_none"] = f"no readable angles: {type(e).__name__}: {str(e)[:200]}"
1586 | +        out["package"] = None
1587 | +        return out
1588 | +    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
1589 | +    dropped = set()
1590 | +    for ai, angle in enumerate(angles):
1591 | +        if len(out["packages"]) >= want:
1592 | +            break
1593 | +        for rebuild in range(3):                         # a context / truth failure drops a moment and rebuilds
1594 | +            segs = lineup_for(angle, cleared, frozenset(dropped))
1595 | +            rec = {"angle": ai + 1, "rebuild": rebuild + 1}
1596 | +            if segs is None:
1597 | +                rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the runtime arithmetic"
1598 | +                out["tried"].append(rec)
1599 | +                break
1600 | +            order = [m["moment_id"] for m in segs]
1601 | +            extra, pk, g, wr = "", None, None, None
1602 | +            for attempt in range(1 + REWRITES):
1603 | +                try:
1604 | +                    wr, fields = write_v2(router, angle, segs, ctx, extra=extra, seed=7 + attempt + 10 * ai)
1605 | +                except Exception as e:
1606 | +                    rec.setdefault("writer_errors", []).append(f"{type(e).__name__}: {str(e)[:200]}")
1607 | +                    continue
1608 | +                pk = assemble(order, cleared, fields, ctx, "written" if attempt == 0 else f"rewritten x{attempt}")
1609 | +                g = integrity(router, pk, sources, wr.vendor, None if wr.vendor in a_vendors else a_by, levels,
1610 | +                              ctx.now)
1611 | +                rec.setdefault("attempts", []).append({"fid_ok": g["fid_ok"], "context_ok": g["context"]["ok"],
1612 | +                                                       "runtime": pk["runtime_s_estimate"],
1613 | +                                                       "violations": g["fidelity"]["violations"] + g["duplicates"] +
1614 | +                                                       g["context"]["violations"]})
1615 | +                framing = [v for v in g["context"]["violations"] if v["rule"] in VO_DEPENDENT]
1616 | +                intrinsic = [v for v in g["context"]["violations"] if v["rule"] not in VO_DEPENDENT]
1617 | +                if g["ok"] or intrinsic:
1618 | +                    break                                # done, or a clip's own context fails: drop it below
1619 | +                if g["fid_ok"] and not framing:
1620 | +                    break
1621 | +                bad = g["fidelity"]["violations"] + g["duplicates"] + [
1622 | +                    {"slot": v["segment"], "rule": v["rule"], "detail": VO_FIX.get(v["rule"], v["detail"])}
1623 | +                    for v in framing]
1624 | +                extra = ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite them "
1625 | +                         "so they make the same point ONLY with what the cited clips state:\n" +
1626 | +                         "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in bad))
1627 | +            if g is None:
1628 | +                out["tried"].append(rec)
1629 | +                break
1630 | +            if not g["context"]["ok"]:
1631 | +                bad = {sg["moment_id"] for sg in pk["segments"]
1632 | +                       if any(sg["label"] in v["segment"].split("+") for v in g["context"]["violations"])}
1633 | +                dropped |= bad or {order[-1]}
1634 | +                rec["why"] = "context integrity (B / C): dropped " + ", ".join(sorted(bad or {order[-1]}))
1635 | +                out["tried"].append(rec)
1636 | +                continue
1637 | +            if not g["ok"]:                              # written VO failed after the rewrites: the plain VO, ranked last
1638 | +                intro, bridges, title, caption = plain_vo(segs, ctx)
1639 | +                pk3 = assemble(order, cleared, {"intro": intro, "bridges": bridges, "title": title, "caption": caption,
1640 | +                                                "type": "moments", "angle": angle["angle"] + " (plain VO, L-w 2)"},
1641 | +                               ctx, "plain")
1642 | +                g3 = integrity(router, pk3, sources, wr.vendor, None if wr.vendor in a_vendors else a_by, levels,
1643 | +                               ctx.now)
1644 | +                rec["plain"] = {"ok": g3["ok"], "violations": g3["fidelity"]["violations"] + g3["duplicates"]}
1645 | +                if g3["ok"]:
1646 | +                    pk3["checks"] = {"integrity": _checks(g3), "coherence": None, "vo": "PLAIN VO (fallback, ranked last)"}
1647 | +                    pk3["models"] = {"writer": "plain template", "fidelity_verdict": g3["fidelity"]["backend"],
1648 | +                                     "context": g3["context"].get("backends")}
1649 | +                    out["plain"].append(pk3)
1650 | +                out["tried"].append(rec)
1651 | +                break
1652 | +            ok_c, verdict = coherence(router, pk, wr.vendor)
1653 | +            rec["coherence"] = verdict
1654 | +            if not ok_c:
1655 | +                rec["why"] = "coherence below 4 or no through-line: next angle"
1656 | +                out["tried"].append(rec)
1657 | +                break
1658 | +            if truth_dir:
1659 | +                truth = []
1660 | +                for sg in pk["segments"]:
1661 | +                    if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations")):
1662 | +                        try:
1663 | +                            truth.append(dict(TT.verify_segment(sg["video_id"], float(sg["start"]), float(sg["end"]),
1664 | +                                                                sg["text"], truth_dir), label=sg["label"],
1665 | +                                              moment_id=sg["moment_id"]))
1666 | +                        except Exception as e:
1667 | +                            truth.append({"label": sg["label"], "moment_id": sg["moment_id"],
1668 | +                                          "error": f"{type(e).__name__}: {str(e)[:160]}"})
1669 | +                rec["truth"] = truth
1670 | +                bad = {t["moment_id"] for t in truth if t.get("error") or not t.get("transcript_ok")
1671 | +                       or (t.get("speakers") or {}).get("turn_change_inside")}
1672 | +                if bad:
1673 | +                    dropped |= bad
1674 | +                    rec["why"] = "law L-v: the second pass disagrees or a speaker changes: dropped " + ", ".join(sorted(bad))
1675 | +                    out["tried"].append(rec)
1676 | +                    continue
1677 | +                pk["transcript_truth"] = truth
1678 | +            pk["checks"] = {"integrity": _checks(g), "coherence": verdict, "vo": pk["vo_kind"]}
1679 | +            pk["models"] = {"writer": wr.backend, "fidelity_verdict": g["fidelity"]["backend"],
1680 | +                            "context": g["context"].get("backends"), "coherence": verdict.get("backend")}
1681 | +            out["packages"].append(pk)
1682 | +            out["tried"].append(dict(rec, result="PACKAGE"))
1683 | +            dropped |= set(order)                        # alternatives use other moments
1684 | +            break
1685 | +    rank = lambda p: (-min(list(p["checks"]["coherence"]["clips"].values()) + [p["checks"]["coherence"]["vo_point"]]),
1686 | +                      -sum(p["checks"]["coherence"]["clips"].values()))
1687 | +    out["packages"].sort(key=rank)
1688 | +    out["package"] = (out["packages"] or out["plain"] or [None])[0]
1689 | +    return out
1690 | +
1691 | +
1692 | +def _checks(g):
1693 | +    return {"vo_fidelity": {"deterministic": g["fidelity"]["deterministic"], "verdict": g["fidelity"]["verdict"],
1694 | +                            "backend": g["fidelity"]["backend"]},
1695 | +            "duplicates": g["duplicates"],
1696 | +            "context_integrity": {k: v for k, v in g["context"].items() if k != "segments"},
1697 | +            "context_segments": g["context"]["segments"], "runtime_ok": g["runtime_ok"]}
1698 | +
1699 | +
1700 | +def _writer_vendor(router):
1701 | +    """The vendor of the first available writer in the chain (so step A avoids it); 'openai' if it cannot be told."""
1702 | +    try:
1703 | +        name = router.chain("angle_write")[0]
1704 | +        return router.backends[name].vendor
1705 | +    except Exception:
1706 | +        return "openai"
1707 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
1708 | new file mode 100644
1709 | index 00000000..8b66ebf5
1710 | --- /dev/null
1711 | +++ b/pipeline/package_pin.py
1712 | @@ -0,0 +1,58 @@
1713 | +#!/usr/bin/env python3
1714 | +"""pipeline/package_pin.py — a pp.package/1 as the existing PINNED entry point's decision (pipeline/pinned.py, schema
1715 | +protocol_pulse.pinned_story.v1), so the SAME factory downstream (validate -> cut -> sentence law -> voice -> render ->
1716 | +gates -> release authorisation) renders a moments-first package.
1717 | +
1718 | +- Every segment carries `approved_text` = the moment's exact words (its source sentences, verbatim). The pin is
1719 | +  `machine_cuts`, so the sentence law locates the words BY TEXT in the acquired transcript, never by offsets.
1720 | +- Times are YouTube coordinates (the store record's own seconds in the full video).
1721 | +- `approved_by` names the machine and REVIEW ONLY. No human approved this decision (law L-q: the first delivery is
1722 | +  REVIEW ONLY).
1723 | +- The package's VO (intro, bridges), title, caption and the gate verdicts travel in `moments_package`. pinned.py at
1724 | +  c1451047 ignores the block, so its VO falls back to none; REQUESTS R7 makes pinned.build_edl use it.
1725 | +- Writes nothing itself: to_pin() returns the dict; write_pin() writes it beside the package.
1726 | +"""
1727 | +import hashlib
1728 | +import json
1729 | +import os
1730 | +from datetime import datetime, timezone
1731 | +
1732 | +SCHEMA = "protocol_pulse.pinned_story.v1"
1733 | +
1734 | +
1735 | +def to_pin(pk, run_name):
1736 | +    segs = []
1737 | +    for i, s in enumerate(pk["segments"]):
1738 | +        segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
1739 | +                     "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
1740 | +                     "approved_text": s["text"], "time_coords": "youtube", "source": {"kind": "youtube"}})
1741 | +    body = json.dumps(pk, sort_keys=True, default=str).encode()
1742 | +    return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{hashlib.sha256(body).hexdigest()[:8]}",
1743 | +            "label": "bitcoin", "headline": pk["title"],
1744 | +            "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
1745 | +            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
1746 | +            "approval_ref": f"docs/audits/parallel/pp-selectid_STATE.md (top package, {run_name})",
1747 | +            "machine_cuts": True, "segments": segs,
1748 | +            "moments_package": {"schema": pk["schema"], "package_sha256": hashlib.sha256(body).hexdigest(),
1749 | +                                "type": pk["type"],
1750 | +                                "edl_vo": {"intro": pk["vo"]["intro"],
1751 | +                                           "bridges": [{"text": t, "after_clip": a} for t, a in
1752 | +                                                       zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]},
1753 | +                                "signoff_expected": pk["vo"]["signoff"],
1754 | +                                "title": pk["title"], "caption": pk["caption"],
1755 | +                                "hook_first_words": pk["hook_first_words"],
1756 | +                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
1757 | +                                                                   for i in range(len(pk["vo"]["bridges"]))}},
1758 | +                                "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
1759 | +                                           "models": pk.get("models")},
1760 | +                                "runtime_s_estimate": pk["runtime_s_estimate"],
1761 | +                                "sources_30s_before": [s["url_30s_before"] for s in pk["segments"]]}}
1762 | +
1763 | +
1764 | +def write_pin(pk, run_name, out_dir):
1765 | +    pin = to_pin(pk, run_name)
1766 | +    os.makedirs(out_dir, exist_ok=True)
1767 | +    path = os.path.join(out_dir, "MOMENTS_PIN.json")
1768 | +    with open(path, "w") as f:
1769 | +        json.dump(pin, f, indent=1)
1770 | +    return path, pin
1771 | diff --git a/pipeline/providers.py b/pipeline/providers.py
1772 | new file mode 100644
1773 | index 00000000..de4c547c
1774 | --- /dev/null
1775 | +++ b/pipeline/providers.py
1776 | @@ -0,0 +1,457 @@
1777 | +#!/usr/bin/env python3
1778 | +"""pipeline/providers.py — ONE provider interface for every model role (law L-x, orchestrator 2026-11-12 '02:45':
1779 | +"no single model, Ultron first").
1780 | +
1781 | +Every role (mining, angle + writing, fidelity verdict, context verdict, viewer takeaway, trend brief, story selection,
1782 | +check verdict) calls Router.call(role, prompt, ...). The role's back-end CHAIN comes from pipeline/model_providers.json;
1783 | +no vendor or model name appears in any role's code. A back-end that cannot answer now (out of credit, rate-limited after
1784 | +backoff, server error, transport failure, not configured, the local model without its GPU0 lease) raises Unavailable and
1785 | +the chain moves on, so the run continues when any one vendor is down (tonight OpenAI ran dry mid-run). A role whose whole
1786 | +chain is unavailable raises ProviderError: a failed role, never a pass (law L-m).
1787 | +
1788 | +Verdict roles never run on the writer's vendor (law L-s: "a model from a different vendor than the writer"; orchestrator
1789 | +02:00: the blind judge on another vendor): Router.call(..., avoid_vendor=<the writer's vendor>) skips those back-ends.
1790 | +
1791 | +Replies are text only; strict parsing stays with the caller (no repair here, law L-l). Every exchange can be recorded
1792 | +(record_dir) and replayed offline (replay=True): the recorded back-end name travels with the reply, so every artefact
1793 | +names the model that produced it. Spend is priced per back-end at the config's upper-bound USD per 1M tokens into one
1794 | +ledger with a guard (SpendLimit); Heimdall's account is read from its /credits endpoint and the 90% tripwire NOTIFIES
1795 | +(Reply.notices and Router.notices), it never halts (PBX 02:45).
1796 | +
1797 | +Keys are read by name from the env file inside code; never printed or logged.
1798 | +"""
1799 | +import hashlib
1800 | +import json
1801 | +import os
1802 | +import time
1803 | +import urllib.error
1804 | +import urllib.request
1805 | +from dataclasses import dataclass, field
1806 | +
1807 | +HERE = os.path.dirname(os.path.abspath(__file__))
1808 | +CONFIG = os.path.join(HERE, "model_providers.json")
1809 | +BACKOFF_S = (10, 30, 90)            # rate limits / server errors / transport; an exhausted account is final at once
1810 | +
1811 | +
1812 | +class Unavailable(Exception):
1813 | +    """This back-end cannot answer now: the chain moves to the next one."""
1814 | +
1815 | +
1816 | +class ProviderError(Exception):
1817 | +    """No back-end of the role's chain answered: the role failed (never a pass)."""
1818 | +
1819 | +
1820 | +class SpendLimit(Exception):
1821 | +    """The session's spend guard is reached: no further model call."""
1822 | +
1823 | +
1824 | +class ReplayMiss(Exception):
1825 | +    """Offline replay has no recorded exchange for this call."""
1826 | +
1827 | +
1828 | +@dataclass
1829 | +class Reply:
1830 | +    text: str
1831 | +    backend: str                                  # "vendor:model", the model that produced this text
1832 | +    vendor: str
1833 | +    seconds: float = 0.0
1834 | +    usage: dict = field(default_factory=dict)     # {"in": n, "out": n} (reasoning tokens counted as out)
1835 | +    usd: float = 0.0
1836 | +    replayed: bool = False
1837 | +    tried: list = field(default_factory=list)     # [(backend, why unavailable)] before this one answered
1838 | +    notices: list = field(default_factory=list)
1839 | +
1840 | +
1841 | +def env_value(path, name):
1842 | +    """One key's value from an env file, read by name inside code (never printed or logged)."""
1843 | +    try:
1844 | +        with open(path) as f:
1845 | +            for line in f:
1846 | +                k, sep, v = line.strip().partition("=")
1847 | +                k = k.strip()
1848 | +                k = k[len("export "):].strip() if k.startswith("export ") else k
1849 | +                if sep and k == name:
1850 | +                    return v.strip().strip('"').strip("'")
1851 | +    except OSError:
1852 | +        pass
1853 | +    return None
1854 | +
1855 | +
1856 | +def _http_json(url, body, headers, timeout):
1857 | +    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json",
1858 | +                                                                              **headers})
1859 | +    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
1860 | +
1861 | +
1862 | +def _with_backoff(fn, final_codes=()):
1863 | +    """fn() with BACKOFF_S retries on 429 / 5xx / transport; HTTP codes in final_codes (or any other 4xx) are final.
1864 | +    Raises Unavailable with the reason when it cannot answer."""
1865 | +    last = None
1866 | +    for wait in BACKOFF_S + (None,):
1867 | +        try:
1868 | +            return fn()
1869 | +        except urllib.error.HTTPError as e:
1870 | +            try:
1871 | +                err = json.loads(e.read() or b"{}")
1872 | +            except (ValueError, OSError):
1873 | +                err = {}
1874 | +            e_obj = err.get("error") if isinstance(err.get("error"), dict) else {}
1875 | +            code = str(e_obj.get("code") or e_obj.get("type") or err.get("type") or "")
1876 | +            last = f"HTTP {e.code} {code}".strip()
1877 | +            if e.code in final_codes or "insufficient_quota" in code or "credit" in code or "billing" in code:
1878 | +                raise Unavailable(last + " (final: account)") from None
1879 | +            if (e.code == 429 or e.code >= 500) and wait is not None:
1880 | +                time.sleep(wait)
1881 | +                continue
1882 | +            raise Unavailable(last) from None
1883 | +        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
1884 | +            last = type(e).__name__
1885 | +            if wait is not None:
1886 | +                time.sleep(wait)
1887 | +                continue
1888 | +            raise Unavailable(last) from None
1889 | +    raise Unavailable(last or "unavailable")
1890 | +
1891 | +
1892 | +# ── back-ends ──
1893 | +
1894 | +class Backend:
1895 | +    vendor = "?"
1896 | +
1897 | +    def __init__(self, name, spec, env_path):
1898 | +        self.name, self.spec, self.env_path = name, spec, env_path
1899 | +        self.model = spec["model"]
1900 | +        self.price = tuple(spec.get("price_usd_per_1m") or (0.0, 0.0))
1901 | +        self.timeout = float(spec.get("timeout_s", 600))
1902 | +
1903 | +    def usd(self, usage):
1904 | +        return round(usage.get("in", 0) * self.price[0] / 1e6 + usage.get("out", 0) * self.price[1] / 1e6, 6)
1905 | +
1906 | +    def key(self, name):
1907 | +        k = env_value(self.env_path, name)
1908 | +        if not k:
1909 | +            raise Unavailable(f"{name} not configured")
1910 | +        return k
1911 | +
1912 | +    def complete(self, prompt, max_tokens, seed, system=None):
1913 | +        raise NotImplementedError
1914 | +
1915 | +
1916 | +class LocalBackend(Backend):
1917 | +    """gemma3:27b (or the configured local model) on Ultron's GPU0 Ollama through story_semantics.LocalLLM: its GPU0
1918 | +    placement guard, digest and temperature 0 kept. Only a STARTED LocalLLM handed in by the caller that holds the GPU0
1919 | +    lease (law L-r) makes this back-end available; without one it is Unavailable (this builder session never uses a GPU)."""
1920 | +    vendor = "local"
1921 | +
1922 | +    def __init__(self, name, spec, env_path, llm=None):
1923 | +        super().__init__(name, spec, env_path)
1924 | +        self.llm = llm
1925 | +
1926 | +    def complete(self, prompt, max_tokens, seed, system=None):
1927 | +        if self.llm is None:
1928 | +            raise Unavailable("local model needs a started LocalLLM under the GPU0 lease (law L-r)")
1929 | +        import http.client
1930 | +        import story_semantics as sm
1931 | +        if len(prompt) / 2.5 + max_tokens > sm.LLM_CTX:       # Ollama keeps the tail and drops the instructions
1932 | +            raise Unavailable(f"prompt over the local context {sm.LLM_CTX}")
1933 | +        p = (system + "\n\n" + prompt) if system else prompt
1934 | +        t0 = time.time()
1935 | +        try:
1936 | +            text = self.llm._post(p, max_tokens, seed)
1937 | +        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as e:
1938 | +            raise Unavailable(f"ollama: {type(e).__name__}") from None
1939 | +        return text, {"in": 0, "out": 0}, time.time() - t0
1940 | +
1941 | +
1942 | +class OpenAIBackend(Backend):
1943 | +    """OpenAI chat/completions; JSON mode (the word JSON is put in the system message, as json_object requires)."""
1944 | +    vendor = "openai"
1945 | +    URL = "https://api.openai.com/v1/chat/completions"
1946 | +
1947 | +    def complete(self, prompt, max_tokens, seed, system=None):
1948 | +        key = self.key("OPENAI_API_KEY")
1949 | +        body = {"model": self.model, "max_completion_tokens": max(int(self.spec.get("min_out", 0)), max_tokens),
1950 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object."},
1951 | +                             {"role": "user", "content": prompt}],
1952 | +                "response_format": {"type": "json_object"}, "seed": seed}
1953 | +        if self.spec.get("reasoning_effort"):
1954 | +            body["reasoning_effort"] = self.spec["reasoning_effort"]
1955 | +        t0 = time.time()
1956 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout))
1957 | +        u = j.get("usage") or {}
1958 | +        try:
1959 | +            text = j["choices"][0]["message"].get("content") or ""
1960 | +        except (KeyError, IndexError, TypeError):
1961 | +            raise Unavailable("openai: no choices") from None
1962 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1963 | +
1964 | +
1965 | +class HeimdallBackend(OpenAIBackend):
1966 | +    """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY). JSON is asked for in words only (its models
1967 | +    differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
1968 | +    vendor = "heimdall"
1969 | +    BASE = "https://api-staging.heimdallm.com/api/v1"
1970 | +
1971 | +    def complete(self, prompt, max_tokens, seed, system=None):
1972 | +        key = self.key("HEIMDALL_API_KEY")
1973 | +        body = {"model": self.model, "max_tokens": max(int(self.spec.get("min_out", 0)), max_tokens), "seed": seed,
1974 | +                "temperature": self.spec.get("temperature", 0),
1975 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
1976 | +                             {"role": "user", "content": prompt}]}
1977 | +        t0 = time.time()
1978 | +        j = _with_backoff(lambda: _http_json(self.BASE + "/chat/completions", body, {"Authorization": "Bearer " + key},
1979 | +                                             self.timeout), final_codes=(401, 402, 403))
1980 | +        u = j.get("usage") or {}
1981 | +        try:
1982 | +            text = j["choices"][0]["message"].get("content") or ""
1983 | +        except (KeyError, IndexError, TypeError):
1984 | +            raise Unavailable("heimdall: no choices") from None
1985 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1986 | +
1987 | +    def credits(self):
1988 | +        """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
1989 | +        try:
1990 | +            key = self.key("HEIMDALL_API_KEY")
1991 | +            req = urllib.request.Request(self.BASE + "/credits", headers={"Authorization": "Bearer " + key})
1992 | +            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
1993 | +            d = d.get("data", d)
1994 | +            return float(d["total_usage"]), float(d["total_credits"])
1995 | +        except Exception:
1996 | +            return None
1997 | +
1998 | +
1999 | +class XAIBackend(Backend):
2000 | +    """xAI chat/completions; a judge runs at temperature 0 with the attempt's seed (production parity with LocalLLM).
2001 | +    Told it has no tools and must answer in one message (orchestrator 02:00)."""
2002 | +    vendor = "xai"
2003 | +    URL = "https://api.x.ai/v1/chat/completions"
2004 | +    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
2005 | +
2006 | +    def complete(self, prompt, max_tokens, seed, system=None):
2007 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
2008 | +        body = {"model": self.model, "max_tokens": max(int(self.spec.get("min_out", 8000)), max_tokens * 8),
2009 | +                "temperature": self.spec.get("temperature", 0), "seed": seed,
2010 | +                "messages": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
2011 | +                             {"role": "user", "content": prompt}]}
2012 | +        t0 = time.time()
2013 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
2014 | +                          final_codes=(401, 402, 403))
2015 | +        u = j.get("usage") or {}
2016 | +        reasoning = int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
2017 | +        try:
2018 | +            text = j["choices"][0]["message"].get("content") or ""
2019 | +        except (KeyError, IndexError, TypeError):
2020 | +            raise Unavailable("xai: no choices") from None
2021 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
2022 | +            time.time() - t0
2023 | +
2024 | +
2025 | +class AnthropicBackend(Backend):
2026 | +    """Anthropic Messages (streaming; adaptive thinking at the configured effort)."""
2027 | +    vendor = "anthropic"
2028 | +
2029 | +    def complete(self, prompt, max_tokens, seed, system=None):
2030 | +        try:
2031 | +            import anthropic
2032 | +        except ImportError:
2033 | +            raise Unavailable("anthropic SDK not installed") from None
2034 | +        client = anthropic.Anthropic(api_key=self.key("ANTHROPIC_API_KEY"), max_retries=3, timeout=self.timeout)
2035 | +        kw = {"model": self.model, "max_tokens": max(int(self.spec.get("min_out", 16000)), max_tokens),
2036 | +              "messages": [{"role": "user", "content": prompt}],
2037 | +              "system": (system or "") + " Reply with one JSON object only, no prose, no code fence."}
2038 | +        if self.spec.get("effort"):
2039 | +            kw["output_config"] = {"effort": self.spec["effort"]}
2040 | +            kw["thinking"] = {"type": "adaptive"}
2041 | +        t0 = time.time()
2042 | +        try:
2043 | +            with client.messages.stream(**kw) as s:
2044 | +                msg = s.get_final_message()
2045 | +        except anthropic.APIStatusError as e:
2046 | +            raise Unavailable(f"anthropic HTTP {e.status_code}") from None
2047 | +        except anthropic.APIError as e:
2048 | +            raise Unavailable(f"anthropic {type(e).__name__}") from None
2049 | +        text = "".join(b.text for b in msg.content if b.type == "text")
2050 | +        return text, {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}, time.time() - t0
2051 | +
2052 | +
2053 | +class XAISearchBackend(Backend):
2054 | +    """xAI Responses API with live X and web search tools (x_search, web_search), for the trend brief only. The
2055 | +    reply text is returned as written; the caller validates it into the closed taxonomy (law L-w 4)."""
2056 | +    vendor = "xai_search"
2057 | +    URL = "https://api.x.ai/v1/responses"
2058 | +
2059 | +    def complete(self, prompt, max_tokens, seed, system=None):
2060 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
2061 | +        body = {"model": self.model, "max_output_tokens": max_tokens,
2062 | +                "input": [{"role": "system", "content": system or "Answer with one JSON object only."},
2063 | +                          {"role": "user", "content": prompt}],
2064 | +                "tools": [{"type": t} for t in self.spec.get("tools", ("x_search", "web_search"))]}
2065 | +        t0 = time.time()
2066 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
2067 | +                          final_codes=(401, 402, 403))
2068 | +        text = j.get("output_text") or ""
2069 | +        if not text:
2070 | +            for item in j.get("output") or []:
2071 | +                for part in (item.get("content") or []) if isinstance(item, dict) else []:
2072 | +                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
2073 | +                        text += part.get("text") or ""
2074 | +        u = j.get("usage") or {}
2075 | +        return text, {"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
2076 | +                      "out": int(u.get("output_tokens") or u.get("completion_tokens") or 0)}, time.time() - t0
2077 | +
2078 | +
2079 | +VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
2080 | +           "anthropic": AnthropicBackend}
2081 | +
2082 | +
2083 | +# ── the router ──
2084 | +
2085 | +class Router:
2086 | +    """Role -> back-end chain from the config. call() tries the chain in order (skipping back-ends this run already
2087 | +    found unavailable, and any on avoid_vendor), records every exchange when record_dir is set, prices it into the
2088 | +    spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
2089 | +
2090 | +    def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
2091 | +                 local_llm=None, chains=None):
2092 | +        with open(config) as f:
2093 | +            self.config = json.load(f)
2094 | +        self.env_path = env_path or os.path.join(os.path.dirname(HERE), "." + "env")
2095 | +        self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
2096 | +        self.down, self.notices = {}, []
2097 | +        self.backends = {}
2098 | +        for name, spec in self.config["backends"].items():
2099 | +            cls = VENDORS[spec["vendor"]]
2100 | +            self.backends[name] = cls(name, spec, self.env_path, local_llm) if cls is LocalBackend else \
2101 | +                cls(name, spec, self.env_path)
2102 | +        self.chains = dict(chains or {})          # tests / the A/B harness may pin a role's chain (still by config name)
2103 | +
2104 | +    def chain(self, role):
2105 | +        if role in self.chains:
2106 | +            return list(self.chains[role])
2107 | +        try:
2108 | +            return list(self.config["roles"][role]["chain"])
2109 | +        except KeyError:
2110 | +            raise ProviderError(f"role {role!r} has no chain in {os.path.basename(CONFIG)}") from None
2111 | +
2112 | +    # recording
2113 | +    def _path(self, role, backend, prompt, max_tokens, seed, system):
2114 | +        k = hashlib.sha256(json.dumps([role, backend, prompt, max_tokens, seed, system or ""]).encode()).hexdigest()
2115 | +        return os.path.join(self.record_dir, k[:2], k + ".json")
2116 | +
2117 | +    def _spent(self):
2118 | +        try:
2119 | +            with open(self.spend_path) as f:
2120 | +                return float(json.load(f).get("usd_estimate", 0.0))
2121 | +        except (OSError, ValueError, TypeError):
2122 | +            return 0.0
2123 | +
2124 | +    def _account(self, backend, usage, usd, role):
2125 | +        if not self.spend_path:
2126 | +            return
2127 | +        import fcntl
2128 | +        os.makedirs(os.path.dirname(self.spend_path), exist_ok=True)
2129 | +        with open(self.spend_path + ".lock", "w") as lk:
2130 | +            fcntl.flock(lk, fcntl.LOCK_EX)
2131 | +            d = {"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}}
2132 | +            try:
2133 | +                with open(self.spend_path) as f:
2134 | +                    d.update(json.load(f))
2135 | +            except (OSError, ValueError):
2136 | +                pass
2137 | +            b = d["by_backend"].setdefault(backend.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
2138 | +                                                          "price_usd_per_1m": list(backend.price)})
2139 | +            b.update(calls=b["calls"] + 1, usd_estimate=round(b["usd_estimate"] + usd, 6),
2140 | +                     **{"in": b["in"] + usage.get("in", 0), "out": b["out"] + usage.get("out", 0)})
2141 | +            r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
2142 | +            r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
2143 | +            d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
2144 | +            tmp = f"{self.spend_path}.{os.getpid()}.tmp"
2145 | +            with open(tmp, "w") as f:
2146 | +                json.dump(d, f, indent=1)
2147 | +            os.replace(tmp, self.spend_path)
2148 | +
2149 | +    def heimdall_tripwire(self, at=0.9):
2150 | +        """NOTIFY when Heimdall's account usage reaches `at` of its credits (PBX 02:45: never a halt)."""
2151 | +        h = next((b for b in self.backends.values() if isinstance(b, HeimdallBackend)), None)
2152 | +        got = h.credits() if h else None
2153 | +        if got and got[1] > 0 and got[0] / got[1] >= at:
2154 | +            msg = f"HEIMDALL SPEND AT {int(at * 100)}%: {got[0]:.2f} of {got[1]:.2f} USD"
2155 | +            if msg not in self.notices:
2156 | +                self.notices.append(msg)
2157 | +            return msg
2158 | +        return None
2159 | +
2160 | +    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None):
2161 | +        tried, notices = [], []
2162 | +        for name in self.chain(role):
2163 | +            b = self.backends.get(name)
2164 | +            if b is None:
2165 | +                tried.append((name, "not in config backends"))
2166 | +                continue
2167 | +            if avoid_vendor and b.vendor == avoid_vendor:
2168 | +                tried.append((name, f"same vendor as the writer ({avoid_vendor}): skipped"))
2169 | +                continue
2170 | +            if avoid_model and b.name == avoid_model:
2171 | +                tried.append((name, "same model as the generator: skipped"))
2172 | +                continue
2173 | +            if name in self.down:
2174 | +                tried.append((name, f"down this run: {self.down[name]}"))
2175 | +                continue
2176 | +            path = self._path(role, name, prompt, max_tokens, seed, system) if self.record_dir else None
2177 | +            if path and os.path.exists(path):
2178 | +                with open(path) as f:
2179 | +                    rec = json.load(f)
2180 | +                return Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
2181 | +                             rec.get("usd", 0.0), True, tried, notices)
2182 | +            if self.replay:
2183 | +                tried.append((name, "replay: not recorded"))
2184 | +                continue
2185 | +            if self.spend_path and self._spent() >= self.limit_usd:
2186 | +                raise SpendLimit(f"spend estimate {self._spent():.2f} USD >= {self.limit_usd} USD")
2187 | +            if b.vendor == "heimdall":
2188 | +                n = self.heimdall_tripwire()
2189 | +                if n:
2190 | +                    notices.append(n)
2191 | +            try:
2192 | +                text, usage, secs = b.complete(prompt, max_tokens, seed, system)
2193 | +            except Unavailable as e:
2194 | +                self.down[name] = str(e)
2195 | +                tried.append((name, str(e)))
2196 | +                continue
2197 | +            usd = b.usd(usage)
2198 | +            self._account(b, usage, usd, role)
2199 | +            if path and isinstance(text, str) and text.strip():
2200 | +                os.makedirs(os.path.dirname(path), exist_ok=True)
2201 | +                tmp = f"{path}.{os.getpid()}.tmp"
2202 | +                with open(tmp, "w") as f:
2203 | +                    json.dump({"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
2204 | +                               "max_tokens": max_tokens, "system": system, "prompt": prompt, "text": text,
2205 | +                               "usage": usage, "usd": usd, "seconds": round(secs, 2),
2206 | +                               "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f, indent=1)
2207 | +                os.replace(tmp, path)
2208 | +            return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices)
2209 | +        if self.replay:
2210 | +            raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
2211 | +        raise ProviderError(f"{role}: every back-end unavailable: {tried}")
2212 | +
2213 | +
2214 | +class RoleModel:
2215 | +    """A select_by_id.Model over a role (law L-x for the story-first selector, REQUESTS R6 item 7): complete() ->
2216 | +    (text, meta) with the answering back-end in meta; ProviderError becomes select_by_id.ModelError."""
2217 | +
2218 | +    def __init__(self, router, role, avoid_vendor=None):
2219 | +        self.router, self.role, self.avoid_vendor = router, role, avoid_vendor
2220 | +        self.name = f"role:{role}"
2221 | +
2222 | +    def complete(self, prompt, max_tokens, seed):
2223 | +        import select_by_id as SB
2224 | +        try:
2225 | +            r = self.router.call(self.role, prompt, max_tokens, seed, avoid_vendor=self.avoid_vendor)
2226 | +        except ProviderError as e:
2227 | +            raise SB.ModelError(str(e)[:300]) from None
2228 | +        except ReplayMiss as e:
2229 | +            raise SB.ReplayMiss(str(e)[:300]) from None
2230 | +        except SpendLimit as e:
2231 | +            raise SB.SpendLimit(str(e)) from None
2232 | +        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "replayed": r.replayed,
2233 | +                        "tried": r.tried}
2234 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
2235 | new file mode 100644
2236 | index 00000000..e7ee2eef
2237 | --- /dev/null
2238 | +++ b/pipeline/transcript_truth.py
2239 | @@ -0,0 +1,111 @@
2240 | +#!/usr/bin/env python3
2241 | +"""pipeline/transcript_truth.py — SPEAKER AND TRANSCRIPT TRUTH (law L-v, orchestrator 2026-11-12 '02:30').
2242 | +
2243 | +(2) Every gate trusts one Whisper transcript. For the SELECTED sentences only, a second, independent recognition pass
2244 | +    runs on the SOURCE audio (a different model: OpenAI's transcription API). Any disagreement on a number, a name or
2245 | +    a negation makes that token unusable in VO or title, or drops the moment.
2246 | +(1) The same call's diarisation (gpt-4o-transcribe-diarize) reports the speaker turns inside the window: a moment may
2247 | +    not span a speaker change; a person is NAMED only from verified metadata, never from a diarisation label.
2248 | +
2249 | +audio_window() fetches the audio of [start - pad, end + pad] of a YouTube video on CPU (yt-dlp download sections +
2250 | +ffmpeg to 16 kHz mono WAV) into a caller-given directory (the integrator already holds the downloaded window:
2251 | +second_pass() takes any audio path). No GPU, no Whisper. Keys by name inside code (OPENAI_API_KEY).
2252 | +"""
2253 | +import json
2254 | +import os
2255 | +import re
2256 | +import subprocess
2257 | +import urllib.request
2258 | +import uuid
2259 | +
2260 | +import canon
2261 | +
2262 | +ENV = "/home/ultron/protocol_pulse/" + "." + "env"
2263 | +NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
2264 | +                       "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
2265 | +                       "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
2266 | +_NUM = re.compile(r"^-?\d+(\.\d+)?$")
2267 | +PAD_S = 1.5
2268 | +
2269 | +
2270 | +def audio_window(video_id, start, end, out_dir, pad=PAD_S):
2271 | +    """WAV (16 kHz mono) of the window, fetched with yt-dlp's download sections; returns the path."""
2272 | +    os.makedirs(out_dir, exist_ok=True)
2273 | +    a, b = max(0.0, start - pad), end + pad
2274 | +    base = os.path.join(out_dir, f"{video_id}_{int(a * 1000)}_{int(b * 1000)}")
2275 | +    wav = base + ".wav"
2276 | +    if os.path.exists(wav):
2277 | +        return wav
2278 | +    subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "--download-sections", f"*{a:.2f}-{b:.2f}",
2279 | +                    "--force-keyframes-at-cuts", "-o", base + ".%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
2280 | +                   check=True, timeout=300, capture_output=True)
2281 | +    src = next(os.path.join(out_dir, f) for f in os.listdir(out_dir)
2282 | +               if f.startswith(os.path.basename(base)) and not f.endswith(".wav"))
2283 | +    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True,
2284 | +                   timeout=120)
2285 | +    return wav
2286 | +
2287 | +
2288 | +def second_pass(wav, model="gpt-4o-transcribe-diarize", key=None):
2289 | +    """The OpenAI transcription of the audio: {"text", "segments": [{"speaker", "start", "end", "text"}], "model"}."""
2290 | +    if key is None:
2291 | +        from providers import env_value
2292 | +        key = env_value(ENV, "OPENAI_API_KEY")
2293 | +    boundary = uuid.uuid4().hex
2294 | +    fields = {"model": model, "response_format": "diarized_json" if "diarize" in model else "json"}
2295 | +    if "diarize" in model:
2296 | +        fields["chunking_strategy"] = "auto"
2297 | +    body = b""
2298 | +    for k, v in fields.items():
2299 | +        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
2300 | +    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(wav)}\"\r\n"
2301 | +             f"Content-Type: audio/wav\r\n\r\n").encode() + open(wav, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
2302 | +    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=body,
2303 | +                                 headers={"Authorization": "Bearer " + (key or ""),
2304 | +                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
2305 | +    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
2306 | +    segs = [{"speaker": s.get("speaker"), "start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")}
2307 | +            for s in d.get("segments") or []]
2308 | +    return {"text": d.get("text") or " ".join(s["text"] for s in segs), "segments": segs, "model": model}
2309 | +
2310 | +
2311 | +def critical_tokens(text):
2312 | +    """The tokens law L-v 2 protects: numbers (canonical values), negations, and proper names (capitalised words
2313 | +    after the first word)."""
2314 | +    toks = canon.canon_tokens(text)
2315 | +    nums = [t for t in toks if _NUM.match(t)]
2316 | +    negs = [t for t in toks if t in NEGATIONS or t.endswith("n't")]
2317 | +    words = re.findall(r"(?<![\w$])[A-Za-z][A-Za-z'’-]*", text or "")     # never the K of '16K' (a number's unit)
2318 | +    names = sorted({w for i, w in enumerate(words) if i > 0 and w[0].isupper() and w not in ("I",)})
2319 | +    return {"numbers": nums, "negations": negs, "names": names}
2320 | +
2321 | +
2322 | +def compare(selected_text, second_text):
2323 | +    """Every critical token of the selected sentences must be read the same in the second pass (canonical form).
2324 | +    -> {"ok", "disagree": {"numbers": [...], "negations": [...], "names": [...]}}."""
2325 | +    a, b = critical_tokens(selected_text), canon.canon_tokens(second_text)
2326 | +    bset = set(b)
2327 | +    dis = {"numbers": [n for n in a["numbers"] if n not in bset],
2328 | +           "negations": [n for n in a["negations"] if n not in bset],
2329 | +           "names": [n for n in a["names"] if not set(canon.canon_tokens(n)) <= bset]}
2330 | +    return {"ok": not any(dis.values()), "disagree": dis, "critical": a}
2331 | +
2332 | +
2333 | +def speaker_turns(second, start_rel, end_rel):
2334 | +    """Speakers of the second pass's segments overlapping [start_rel, end_rel] (seconds inside the window): one label
2335 | +    = no change inside; more = a change (law L-v 1); none = not measured."""
2336 | +    sp = [s["speaker"] for s in second["segments"]
2337 | +          if s.get("start") is not None and s.get("end") is not None and s["end"] > start_rel and s["start"] < end_rel]
2338 | +    labels = sorted({x for x in sp if x})
2339 | +    return {"labels": labels, "turn_change_inside": (len(labels) > 1) if labels else None}
2340 | +
2341 | +
2342 | +def verify_segment(video_id, start, end, text, work_dir):
2343 | +    """Both checks for one selected segment -> a record (the second pass's text kept as evidence)."""
2344 | +    wav = audio_window(video_id, start, end, work_dir)
2345 | +    sec = second_pass(wav)
2346 | +    cmp_ = compare(text, sec["text"])
2347 | +    turns = speaker_turns(sec, PAD_S, PAD_S + (end - start))
2348 | +    return {"video_id": video_id, "start": start, "end": end, "model": sec["model"], "second_pass_text": sec["text"],
2349 | +            "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"], "critical": cmp_["critical"],
2350 | +            "speakers": turns, "audio": os.path.basename(wav)}
2351 | diff --git a/pipeline/trend_brief.py b/pipeline/trend_brief.py
2352 | new file mode 100644
2353 | index 00000000..8adb17f7
2354 | --- /dev/null
2355 | +++ b/pipeline/trend_brief.py
2356 | @@ -0,0 +1,169 @@
2357 | +#!/usr/bin/env python3
2358 | +"""pipeline/trend_brief.py — what is hot right now, as a RANKING input only (orchestrator Phase 2 addition '01:55';
2359 | +law L-w 4, '02:30'). Trend is never a gate and never a fact source.
2360 | +
2361 | +- TAXONOMY: a closed list of Bitcoin topic ids, each with our own fixed label and a keyword pattern. Every trend signal
2362 | +  is forced into it; anything else is discarded.
2363 | +- local_baseline(): the free signal from our own corpus. For each topic, the share of partner channels (last 24 h)
2364 | +  with a Bitcoin sentence on that topic. Always available; no model, no network.
2365 | +- grok_brief(): ONE live-search call per cycle (role "trend_brief" through pipeline/providers.py: xAI's Responses API
2366 | +  with x_search + web_search). It asks for 8-12 Bitcoin-only topics with heat 0-1 and rising / fading / steady.
2367 | +  - The reply is validated into the taxonomy (strict, never repaired). Raw post text never enters any prompt: only
2368 | +    (topic id, heat, direction, source count) leave this module, and person names only as a list the packager may use
2369 | +    to boost a moment whose verified SPEAKER is that person.
2370 | +  - Cached per cycle (cycle id + timestamp + sha256 of the reply).
2371 | +  - On any failure: no boost, and the cycle says so.
2372 | +- SHADOW (law L-w 4): moments.TREND_WEIGHT is 0. The brief is logged and compared with the baseline, never used to
2373 | +  rank, until it measurably helps. When enabled, the weight is capped at ~10-15 % of a moment's score. Titles never
2374 | +  take trend phrasing: they use our taxonomy labels at most (law L-t: every word of a title must be supported by the
2375 | +  clips).
2376 | +"""
2377 | +import hashlib
2378 | +import json
2379 | +import os
2380 | +import re
2381 | +import time
2382 | +
2383 | +import eligibility as E
2384 | +
2385 | +TAXONOMY = {   # id: (our own label, pattern over a sentence that names Bitcoin)
2386 | +    "price_action": ("Bitcoin's price move", r"\b(price|all[- ]time high|support|resistance|pullback|sell[- ]?off|rally|"
2387 | +                                             r"dump|pump|correction|drawdown|breakout|\$\d)"),
2388 | +    "etf_flows": ("Bitcoin ETF flows", r"\b(etfs?|inflows?|outflows?|ibit|blackrock|fidelity|grayscale)\b"),
2389 | +    "treasury_companies": ("Bitcoin treasury companies", r"\b(strategy|microstrategy|saylor|treasury compan|metaplanet|"
2390 | +                                                         r"balance sheet|mnav|cost basis)"),
2391 | +    "us_policy": ("US Bitcoin policy", r"\b(strategic (bitcoin )?reserve|congress|senate|house|bill|sec\b|regulat|"
2392 | +                                       r"executive order|white house|legislation)"),
2393 | +    "macro_fed": ("rates, the Fed and the dollar", r"\b(fed\b|federal reserve|rate cuts?|interest rates?|inflation|cpi|"
2394 | +                                                   r"powell|dollar|yields?|liquidity|m2)\b"),
2395 | +    "mining": ("Bitcoin mining", r"\b(miners?|mining|hash ?rate|difficulty|hashprice|halving)\b"),
2396 | +    "onchain": ("on-chain signals", r"\b(on[- ]chain|whales?|long[- ]term holders?|short[- ]term holders?|"
2397 | +                                     r"exchange reserves?|realized price)\b"),
2398 | +    "derivatives_leverage": ("leverage and liquidations", r"\b(leverage|liquidat\w*|futures|options|open interest|"
2399 | +                                                          r"funding rates?)\b"),
2400 | +    "institutional_adoption": ("institutions and Bitcoin", r"\b(banks?|institution\w*|vanguard|jpmorgan|goldman|"
2401 | +                                                           r"pensions?|wall street|custod\w*)\b"),
2402 | +    "sovereign_adoption": ("countries and Bitcoin", r"\b(el salvador|bhutan|nation[- ]states?|countr(y|ies)|sovereign)\b"),
2403 | +    "protocol_dev": ("Bitcoin development", r"\b(bitcoin core|knots|op_return|soft fork|covenants?|taproot|lightning|"
2404 | +                                             r"nodes?)\b"),
2405 | +    "security_custody": ("self-custody and security", r"\b(self[- ]custody|cold storage|seed phrase|hacks?|exploit|"
2406 | +                                                       r"private keys?)\b"),
2407 | +    "quantum": ("quantum computing and Bitcoin", r"\bquantum\b"),
2408 | +    "elections_politics": ("elections and Bitcoin", r"\b(elections?|midterms?|democrats?|republicans?|votes?|campaign)\b"),
2409 | +    "market_sentiment": ("market sentiment", r"\b(fear|greed|capitulat\w*|sentiment|bear market|bull market|cycle|"
2410 | +                                             r"bottom|top)\b"),
2411 | +    "stocks_correlation": ("Bitcoin and stocks", r"\b(nasdaq|s&p|stocks?|equities|tech stocks|nvidia|correlat\w*)"),
2412 | +    "gold_comparison": ("Bitcoin and gold", r"\bgold\b"),
2413 | +    "payments_adoption": ("Bitcoin as money", r"\b(payments?|merchants?|pay with|spend(ing)?|everyday use)\b"),
2414 | +}
2415 | +TOPICS = tuple(TAXONOMY)
2416 | +_PAT = {t: re.compile(p, re.I) for t, (_, p) in TAXONOMY.items()}
2417 | +DIRECTIONS = ("rising", "fading", "steady")
2418 | +BRIEF_MAX_TOKENS = 5000            # < 6k out (token discipline, Phase 2 addition)
2419 | +
2420 | +
2421 | +def label(topic):
2422 | +    return TAXONOMY[topic][0]
2423 | +
2424 | +
2425 | +def topics_of(text):
2426 | +    """Taxonomy ids whose pattern a Bitcoin-naming text matches (the free local classifier)."""
2427 | +    if not E.names_bitcoin(text):
2428 | +        return []
2429 | +    return [t for t in TOPICS if _PAT[t].search(text)]
2430 | +
2431 | +
2432 | +def local_baseline(sources, ctx, hours=24.0):
2433 | +    """{topic: heat 0-1}: the share of the window's partner channels with a Bitcoin sentence on that topic; plus the
2434 | +    channel counts. Free, deterministic, always available (law L-w 4's baseline)."""
2435 | +    by_topic, channels = {t: set() for t in TOPICS}, set()
2436 | +    for src in sources:
2437 | +        age = E.age_hours(src.published_at, ctx.now)
2438 | +        if age is None or age > hours or age < 0:
2439 | +            continue
2440 | +        channels.add(src.channel_id)
2441 | +        for a, b in src.sentences:
2442 | +            for t in topics_of(E.spoken(src.tokens[a:b + 1])):
2443 | +                by_topic[t].add(src.channel_id)
2444 | +    n = max(1, len(channels))
2445 | +    return {"topics": {t: round(len(c) / n, 3) for t, c in by_topic.items() if c},
2446 | +            "channels": {t: len(c) for t, c in by_topic.items() if c}, "window_channels": len(channels),
2447 | +            "hours": hours}
2448 | +
2449 | +
2450 | +BRIEF_PROMPT = """Search X and the web now ({now} UTC) for what Bitcoin-focused accounts and outlets are talking about
2451 | +in the last 24 hours. Bitcoin only: ignore altcoins, memecoins and general politics unless it is about Bitcoin policy.
2452 | +Classify what you find into these topic ids ONLY (anything else is discarded): {topics}.
2453 | +Return 8 to 12 topics. For each: "topic" (an id from the list), "heat" (0 to 1: how much attention it has now),
2454 | +"direction" ("rising", "fading" or "steady"), "sources" (how many distinct posts or articles you saw on it, an integer).
2455 | +Also "persons": at most 5 names of people at the centre of today's Bitcoin conversation (names only).
2456 | +Do not include quotes, post text, links or opinions.
2457 | +Return ONLY this JSON object: {{"topics": [{{"topic": "...", "heat": 0.0, "direction": "...", "sources": 0}}],
2458 | +"persons": []}}"""
2459 | +
2460 | +
2461 | +def check_brief(obj):
2462 | +    """Strict validation into the closed taxonomy (never repaired): -> {topic: {heat, direction, sources}}, persons."""
2463 | +    if not isinstance(obj, dict) or set(obj) != {"topics", "persons"}:
2464 | +        raise ValueError("keys must be exactly ['topics', 'persons']")
2465 | +    ts = obj["topics"]
2466 | +    if not isinstance(ts, list) or not 1 <= len(ts) <= 12:
2467 | +        raise ValueError("'topics' must hold 1-12 items")
2468 | +    out = {}
2469 | +    for t in ts:
2470 | +        if not isinstance(t, dict) or set(t) != {"topic", "heat", "direction", "sources"}:
2471 | +            raise ValueError("each topic needs exactly topic, heat, direction, sources")
2472 | +        if t["topic"] not in TAXONOMY or t["topic"] in out:
2473 | +            raise ValueError(f"topic {t['topic']!r} not in the taxonomy or repeated")
2474 | +        if type(t["heat"]) not in (int, float) or not 0 <= t["heat"] <= 1 or t["direction"] not in DIRECTIONS or \
2475 | +                type(t["sources"]) is not int or t["sources"] < 0:
2476 | +            raise ValueError(f"topic {t['topic']}: heat 0-1, direction {DIRECTIONS}, sources an integer")
2477 | +        out[t["topic"]] = {"heat": float(t["heat"]), "direction": t["direction"], "sources": t["sources"]}
2478 | +    ps = obj["persons"]
2479 | +    if not isinstance(ps, list) or len(ps) > 5 or any(not isinstance(p, str) or not 2 <= len(p) <= 60 or
2480 | +                                                      not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", p) for p in ps):
2481 | +        raise ValueError("'persons' must be at most 5 plain names")
2482 | +    return out, list(ps)
2483 | +
2484 | +
2485 | +def cycle_id(now, hours=4):
2486 | +    """A cycle is a 4 h slot of the UTC day (one call per cycle; law L-p cadence 3-5 h)."""
2487 | +    return f"{now.strftime('%Y%m%d')}T{now.hour // hours * hours:02d}"
2488 | +
2489 | +
2490 | +def grok_brief(router, now, cache_dir, log=print):
2491 | +    """ONE live-search call per cycle, cached; -> {"status", "topics", "persons", "cycle", "backend", "sha256", ...}.
2492 | +    Failure (no back-end, invalid reply) -> status "failed" and NO boost: trend is never a gate."""
2493 | +    import providers as P
2494 | +    cyc = cycle_id(now)
2495 | +    path = os.path.join(cache_dir, f"brief_{cyc}.json")
2496 | +    if os.path.exists(path):
2497 | +        with open(path) as f:
2498 | +            return dict(json.load(f), cached=True)
2499 | +    prompt = BRIEF_PROMPT.format(now=now.strftime("%Y-%m-%d %H:%M"), topics=", ".join(TOPICS))
2500 | +    rec = {"cycle": cyc, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": "shadow (weight 0)"}
2501 | +    try:
2502 | +        r = router.call("trend_brief", prompt, BRIEF_MAX_TOKENS, seed=7)
2503 | +        raw = r.text.strip()
2504 | +        rec.update(backend=r.backend, usd=r.usd, usage=r.usage, sha256=hashlib.sha256(raw.encode()).hexdigest())
2505 | +        topics, persons = check_brief(json.loads(raw))        # exactly one JSON object: prose is never repaired
2506 | +        rec.update(status="ok", topics=topics, persons=persons)
2507 | +    except (P.ProviderError, P.SpendLimit, ValueError, KeyError) as e:
2508 | +        rec.update(status="failed", why=f"{type(e).__name__}: {str(e)[:200]}", topics={}, persons=[])
2509 | +        log(f"  trend brief: no boost this cycle ({rec['why']})")
2510 | +    os.makedirs(cache_dir, exist_ok=True)
2511 | +    with open(path, "w") as f:
2512 | +        json.dump(rec, f, indent=1)
2513 | +    return rec
2514 | +
2515 | +
2516 | +def trend_match(moment, brief, baseline=None):
2517 | +    """The local trend-match axis (no model call): the hottest brief topic among the moment's topics (0 when the brief
2518 | +    failed); person-trends only for a moment whose VERIFIED speaker is that person (law L-w 4)."""
2519 | +    heat = max([((brief or {}).get("topics") or {}).get(t, {}).get("heat", 0.0) for t in moment.get("topics") or []]
2520 | +               or [0.0])
2521 | +    sp = (moment.get("speaker") or {}).get("named")
2522 | +    if sp and sp in ((brief or {}).get("persons") or []) and (moment.get("speaker") or {}).get("named_source"):
2523 | +        heat = max(heat, 0.5)
2524 | +    base = max([((baseline or {}).get("topics") or {}).get(t, 0.0) for t in moment.get("topics") or []] or [0.0])
2525 | +    return {"brief": round(heat, 3), "baseline": round(base, 3)}
2526 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
2527 | new file mode 100644
2528 | index 00000000..dfa5e568
2529 | --- /dev/null
2530 | +++ b/pipeline/vo_fidelity.py
2531 | @@ -0,0 +1,330 @@
2532 | +#!/usr/bin/env python3
2533 | +"""pipeline/vo_fidelity.py — VO FIDELITY (law L-o 11, '01:55'; law L-t, '02:30'): the PBX MAX VO, the title and the
2534 | +caption never put words in a speaker's mouth. Two layers, BOTH must pass ("vo check needs to be real 100%"):
2535 | +
2536 | +(a) DETERMINISTIC (this module, no model): every line names the segments it relies on (cites = moment ids), and
2537 | +    - NEEDS_SOURCE: a line with a fact (number, name, quote, attribution, time word) cites at least one segment;
2538 | +    - NUMBER: every number (canon value and unit, law L-k) is in a cited segment's sentences; when the line attributes
2539 | +      it to a speaker, in THAT speaker's sentences;
2540 | +    - NAME: every proper name is in a cited segment's sentences, or is production metadata (a credited channel, the
2541 | +      show); no name of a person who does not appear (L-t);
2542 | +    - QUOTE: quoted words are a verbatim run of a cited segment (canonical form);
2543 | +    - ATTRIBUTION: "<X> says / argues / warns ..." binds X to a cited segment whose speaker is X;
2544 | +    - RELATION: words that make speakers answer, agree or rebut each other only when every cited segment is from the
2545 | +      same source video (one conversation);
2546 | +    - FRAMING: destroys / slams / exposes / admits / confirms / caught only when the source itself uses the word (L-t);
2547 | +    - IMPERATIVE: no second-person financial imperative (buy / sell / leverage / all in) (L-t);
2548 | +    - TIME: a time word (today, yesterday, this week, just, now) only when a cited segment says it (L-v 3).
2549 | +(b) BLIND VERDICT (role "fidelity_verdict" through pipeline/providers.py, never the writer's vendor): given ONLY the
2550 | +    segments' sentences and the lines, every claim the text makes, implied ones included (agreement, sequence,
2551 | +    certainty, cause), each yes / no / uncertain with the supporting segment and its words COPIED EXACTLY. The decision
2552 | +    is code: every claim "yes" AND its words a verbatim run of that segment (an unverifiable support is a "no");
2553 | +    "no" or "uncertain" anywhere fails (law L-m).
2554 | +"""
2555 | +import json
2556 | +import re
2557 | +
2558 | +import canon
2559 | +
2560 | +METADATA = ("PBX MAX", "Protocol Pulse", "Pulse Check", "Bitcoin", "BTC")
2561 | +ATTRIB_VERBS = ("says", "said", "argues", "argued", "thinks", "believes", "warns", "warned", "predicts", "predicted",
2562 | +                "claims", "claimed", "notes", "noted", "explains", "explained", "expects", "sees", "points out",
2563 | +                "pointed out", "tells", "told", "adds", "added", "calls", "called", "reckons", "insists", "suggests")
2564 | +RELATION = re.compile(r"\b(agree[sd]?|agreeing|disagree[sd]?|respond(s|ed|ing)?|repl(y|ies|ied)|answer(s|ed|ing)?|"
2565 | +                      r"rebut(s|ted)?|push(es|ed)? back|counter(s|ed)?|fire[sd]? back|echo(es|ed)?|contradict(s|ed)?|"
2566 | +                      r"back(s|ed)? (him|her|them|that) up|sides? with|takes? issue|in response|on the other side|"
2567 | +                      r"weighs? in on|shoots? down|both (say|agree|think|warn))\b", re.I)
2568 | +FRAMING = {"destroy": r"destroy\w*", "slam": r"slam\w*", "expose": r"expos\w*", "admit": r"admi(t|ts|tted|tting)\b",
2569 | +           "confirm": r"confirm\w*", "caught": r"caught"}
2570 | +IMPERATIVE = re.compile(r"(\byou (should|need to|must|have to|ought to|'?ve got to)\s+(buy|sell|short|long|load up|"
2571 | +                        r"ape|go all[- ]in|get in|stack|leverage|lever up|bet)\b)|((^|[.!?:]\s*)(buy|sell|short|load up|"
2572 | +                        r"ape in|go all[- ]in|get in now|don't miss|stack sats|lever up)\b)",
2573 | +                        re.I)
2574 | +TIME_WORDS = ("today", "tonight", "yesterday", "this morning", "this week", "this weekend", "right now", "breaking",
2575 | +              "minutes ago", "hours ago", "just announced", "just hit", "just broke", "just dropped", "just crossed",
2576 | +              "just fell", "just jumped", "just surged", "just plunged")   # recency claims (a bare 'now' / 'just' is
2577 | +                                                                          # connective VO, not a time claim)
2578 | +_NUM = re.compile(r"^-?\d+(\.\d+)?$")
2579 | +HISTORY = re.compile(r"\b(19|20)\d{2}\b|\b(since|back in|last cycle|previous cycle|history|historic(al)?|all[- ]time|"
2580 | +                     r"from the \w+ (low|high|bottom|top)|years? ago|decade|in the past|once)\b", re.I)
2581 | +PRICE_SLOTS = ("intro", "title", "caption")      # the lines that read as the headline (law L-t, orchestrator 03:40)
2582 | +
2583 | +
2584 | +def price_levels(text):
2585 | +    """Bitcoin price-like numbers a line states: canonical values >= 1000 (with or without 'dollars'), or any value
2586 | +    followed by 'dollars' (law L-v 3: a level or a move dates fast)."""
2587 | +    t = ctoks(text)
2588 | +    out = []
2589 | +    for i, w in enumerate(t):
2590 | +        if _NUM.match(w):
2591 | +            v = float(w)
2592 | +            if v >= 1000 or (i + 1 < len(t) and t[i + 1] == "dollars"):
2593 | +                out.append(v)
2594 | +    return out
2595 | +
2596 | +
2597 | +def price_now(text, current_levels, tolerance=0.05):
2598 | +    """PRICE_NOW (orchestrator 03:40; laws L-v 3 / L-t): a headline line stating a price level or move must either
2599 | +    read as history (a year, 'since', 'from the 2022 low', ...) or match a level this universe states as current
2600 | +    (within tolerance). -> [violating values]."""
2601 | +    if HISTORY.search(text or ""):
2602 | +        return []
2603 | +    cur = [float(c) for c in current_levels or ()]
2604 | +    return [v for v in price_levels(text) if not any(abs(v - c) <= tolerance * c for c in cur if c > 0)]
2605 | +_QUOTE = re.compile(r"[\"“”]([^\"“”]{3,}?)[\"“”]")
2606 | +_CAPWORD = re.compile(r"\b[A-Z][A-Za-z0-9'’.&-]*(?:\s+[A-Z][A-Za-z0-9'’.&-]*)*")
2607 | +COMMON_CAPS = frozenset("I The This That These Those It And But So We You They He She Here There Now Today Next First "
2608 | +                        "Then Also Plus Meanwhile Still Yet Why What How When Where Who Which Our Your Their Its "
2609 | +                        "Let Let's Clips Go Links Follow Watch Stay A An In On At For From With As If Not No Yes "
2610 | +                        "One Two Three Four Five Six Seven Eight Nine Ten Here's That's It's".split())
2611 | +
2612 | +
2613 | +def ctoks(text):
2614 | +    return canon.canon_tokens(text or "")
2615 | +
2616 | +
2617 | +def _run_in(sub, toks):
2618 | +    """sub (canonical tokens) occurs as a contiguous run in toks."""
2619 | +    n = len(sub)
2620 | +    return n > 0 and any(toks[i:i + n] == sub for i in range(len(toks) - n + 1))
2621 | +
2622 | +
2623 | +def numbers_of(text):
2624 | +    """[(value, unit or None)] in canonical form: '$73,000' -> ('73000', 'dollars'); '16%' -> ('16', 'percent')."""
2625 | +    t = ctoks(text)
2626 | +    out = []
2627 | +    for i, w in enumerate(t):
2628 | +        if _NUM.match(w):
2629 | +            unit = t[i + 1] if i + 1 < len(t) and t[i + 1] in ("dollars", "percent") else None
2630 | +            out.append((w, unit))
2631 | +    return out
2632 | +
2633 | +
2634 | +def _has_number(src_toks, value, unit):
2635 | +    for i, w in enumerate(src_toks):
2636 | +        if w == value and (unit is None or (i + 1 < len(src_toks) and src_toks[i + 1] == unit)):
2637 | +            return True
2638 | +    return False
2639 | +
2640 | +
2641 | +def _title_case(text):
2642 | +    """A headline written in Title Case: >= 3 longer words, production names left out, > 70 % of them capitalised."""
2643 | +    meta = {w.lower() for m in METADATA for w in m.split()}
2644 | +    ws = [w for w in re.findall(r"[A-Za-z][A-Za-z'’]+", text or "") if len(w) > 3 and w.lower().rstrip("'’s") not in meta
2645 | +          and re.sub(r"['’]s$", "", w).lower() not in meta]
2646 | +    return len(ws) >= 3 and sum(w[0].isupper() for w in ws) / len(ws) > 0.7
2647 | +
2648 | +
2649 | +def names_of(text, allowed=()):
2650 | +    """Proper names in a line: capitalised word runs that are not common sentence words or production metadata. A
2651 | +    capital that only starts a sentence, and a Title Case line, are no evidence of a name (measured false rejects,
2652 | +    03:55: 'Past', 'Beyond', 'Historical', 'Bullish Claims Don't Erase Risk'); names there are caught by ATTRIBUTION
2653 | +    and by the blind verdict, which lists every claim about a person."""
2654 | +    if _title_case(text):
2655 | +        return []
2656 | +    allowed_c = [ctoks(a) for a in tuple(allowed) + METADATA]
2657 | +    out = []
2658 | +    starts = {0} | {m.end() for m in re.finditer(r"[.!?:;]\s+|[\"“(]\s*", text or "")}
2659 | +    for m in _CAPWORD.finditer(text or ""):
2660 | +        if m.start() in starts and len(m.group(0).split()) == 1:
2661 | +            continue
2662 | +        words = [w for w in m.group(0).split() if w.strip(".,'’")]
2663 | +        while words and words[0].strip(".,'’") in COMMON_CAPS:
2664 | +            words = words[1:]
2665 | +        if not words:
2666 | +            continue
2667 | +        name = re.sub(r"['’]s$", "", " ".join(words).strip(".,'’"))     # "Bitcoin's" is the name "Bitcoin"
2668 | +        nt = ctoks(name)
2669 | +        if not nt or all(_NUM.match(x) for x in nt):
2670 | +            continue
2671 | +        if any(_run_in(nt, a) or _run_in(a, nt) for a in allowed_c if a):
2672 | +            continue
2673 | +        out.append(name)
2674 | +    return out
2675 | +
2676 | +
2677 | +def _attributions(text):
2678 | +    """[(subject words before the verb, verb)] for '<Subject> <verb>' patterns."""
2679 | +    out = []
2680 | +    for v in ATTRIB_VERBS:
2681 | +        for m in re.finditer(r"([A-Z][\w'’.&-]*(?:\s+[A-Z][\w'’.&-]*){0,4})\s+" + re.escape(v) + r"\b", text or ""):
2682 | +            out.append((m.group(1), v))
2683 | +        for m in re.finditer(r"\baccording to\s+([A-Z][\w'’.&-]*(?:\s+[A-Z][\w'’.&-]*){0,4})", text or ""):
2684 | +            out.append((m.group(1), "according to"))
2685 | +    return out
2686 | +
2687 | +
2688 | +def manifest_terms(segments, manifest=None):
2689 | +    """Production metadata a line may state without a citation (never a claim about what anyone said): the credited
2690 | +    channels and verified speaker names, the show, the date (month, weekday, day, year) and the package's own counts
2691 | +    ('two voices', 'three channels')."""
2692 | +    from datetime import date
2693 | +    names = {n for s in segments.values() for n in [s["speaker"]] + list(s.get("names") or [])}
2694 | +    m = manifest or {}
2695 | +    names |= set(m.get("channels") or []) | ({m["show"]} if m.get("show") else set())
2696 | +    nums = {str(len(segments)), str(len({s["video_id"] for s in segments.values()})),
2697 | +            str(len(set(m.get("channels") or []) or {s["speaker"] for s in segments.values()}))}
2698 | +    if m.get("date"):
2699 | +        try:
2700 | +            d = date.fromisoformat(m["date"])
2701 | +            names |= {d.strftime("%B"), d.strftime("%A"), d.strftime("%b")}
2702 | +            nums |= {str(d.day), str(d.year)}
2703 | +        except ValueError:
2704 | +            pass
2705 | +    return sorted(names), nums
2706 | +
2707 | +
2708 | +def check_deterministic(segments, lines, manifest=None, current_levels=None):
2709 | +    """segments: {moment_id: {"speaker": str, "names": [allowed attribution names], "video_id": str, "text": str}};
2710 | +    lines: [{"slot": str, "text": str, "cites": [moment_id, ...]}] (VO lines, the title, the caption); manifest:
2711 | +    {"channels", "date", "show"} (production metadata, allowed without citation).
2712 | +    -> {"ok": bool, "violations": [{"slot", "rule", "detail"}]}."""
2713 | +    v = []
2714 | +    meta, meta_nums = manifest_terms(segments, manifest)
2715 | +    seg_toks = {mid: ctoks(s["text"]) for mid, s in segments.items()}
2716 | +    for ln in lines:
2717 | +        slot, text, cites = ln["slot"], ln.get("text") or "", list(ln.get("cites") or [])
2718 | +        V = lambda rule, detail: v.append({"slot": slot, "rule": rule, "detail": detail})
2719 | +        unknown = [c for c in cites if c not in segments]
2720 | +        if unknown:
2721 | +            V("CITE_UNKNOWN", f"cites {unknown} are not segments of this package")
2722 | +        cited = [c for c in cites if c in segments]
2723 | +        pool = [t for c in cited for t in seg_toks[c]]
2724 | +        nums = [(val, unit) for val, unit in numbers_of(text) if not (unit is None and val in meta_nums)
2725 | +                and not (unit is None and _NUM.match(val) and float(val) <= 10 and not re.search(rf"\b{re.escape(val)}\b", text))]
2726 | +        names = names_of(text, meta)
2727 | +        quotes = [q for q in _QUOTE.findall(text) if len(ctoks(q)) >= 2]
2728 | +        atts = _attributions(text)
2729 | +        times = [w for w in TIME_WORDS if re.search(r"\b" + re.escape(w) + r"\b", text, re.I)]
2730 | +        if (nums or names or quotes or atts or times) and not cited:
2731 | +            V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
2732 | +        att_pool = pool
2733 | +        for subj, verb in atts:
2734 | +            st = ctoks(subj)
2735 | +            owners = [c for c in cited if any(_run_in(ctoks(n), st) or _run_in(st, ctoks(n))
2736 | +                                              for n in [segments[c]["speaker"]] + list(segments[c].get("names") or []))]
2737 | +            if not owners:
2738 | +                V("ATTRIBUTION", f"'{subj} {verb}': no cited segment is spoken by {subj}")
2739 | +            else:
2740 | +                att_pool = [t for c in owners for t in seg_toks[c]]
2741 | +        for val, unit in nums:
2742 | +            if not _has_number(att_pool if atts else pool, val, unit):
2743 | +                V("NUMBER", f"{val}{' ' + unit if unit else ''} is not in the cited sentences" +
2744 | +                  (" of the attributed speaker" if atts else ""))
2745 | +        for n in names:
2746 | +            if not _run_in(ctoks(n), pool):
2747 | +                V("NAME", f"'{n}' is not said in the cited sentences (and is not a credited channel or the show)")
2748 | +        for q in quotes:
2749 | +            if not any(_run_in(ctoks(q), seg_toks[c]) for c in cited):
2750 | +                V("QUOTE", f"\"{q}\" is not a verbatim run of a cited segment")
2751 | +        if RELATION.search(text) and len({segments[c]["video_id"] for c in cited}) != 1:
2752 | +            V("RELATION", f"'{RELATION.search(text).group(0)}' relates speakers who were not in one conversation")
2753 | +        if RELATION.search(text) and len(cited) < 2:
2754 | +            V("RELATION", f"'{RELATION.search(text).group(0)}' implies an exchange the cited segments do not show")
2755 | +        for lemma, pat in FRAMING.items():
2756 | +            if re.search(r"\b" + pat, text, re.I) and not any(re.search(r"\b" + pat, segments[c]["text"], re.I)
2757 | +                                                              for c in cited):
2758 | +                V("FRAMING", f"'{lemma}' framing is not the source's own word (L-t)")
2759 | +        if IMPERATIVE.search(text):
2760 | +            V("IMPERATIVE", f"financial imperative or advice framing: '{IMPERATIVE.search(text).group(0).strip()}'")
2761 | +        for w in times:
2762 | +            if not any(_run_in(ctoks(w), seg_toks[c]) for c in cited):
2763 | +                V("TIME", f"'{w}' is not said in the cited sentences (L-v 3: time words need the source's own)")
2764 | +        if slot.split("_")[0] in PRICE_SLOTS and current_levels is not None:
2765 | +            stale = price_now(text, current_levels)
2766 | +            if stale:
2767 | +                V("PRICE_NOW", f"states the level(s) {stale} as if current, but this universe's current levels are "
2768 | +                               f"{sorted(set(current_levels))[:6]}; mark it as history or drop it (L-v 3 / L-t)")
2769 | +    return {"ok": not v, "violations": v}
2770 | +
2771 | +
2772 | +VERDICT_PROMPT = """You check a short video script for fidelity to its sources. You see ONLY the words each speaker said
2773 | +(the segments), the production facts (true by construction), and the script's lines (voice-over, title, caption).
2774 | +Nothing else is known about these people.
2775 | +
2776 | +SEGMENTS:
2777 | +{segments}
2778 | +
2779 | +PRODUCTION FACTS (segment label "manifest"):
2780 | +{manifest}
2781 | +
2782 | +SCRIPT LINES:
2783 | +{lines}
2784 | +
2785 | +List EVERY claim the script lines make or imply, including implied ones: that a speaker said, thinks, agrees, answers
2786 | +or disagrees; a number; a time ("today"); a cause; how certain something is. For each claim answer "supported":
2787 | +"yes" only if the words you cite state it with the same meaning, polarity and certainty, adding nothing; "no" if they
2788 | +do not; "uncertain" if you cannot tell. A claim may combine what SEVERAL segments say (a point drawn from two clips):
2789 | +then cite each segment with its own supporting words, and say "yes" only if those words together state the claim
2790 | +without any added inference. Copy every supporting run EXACTLY (a continuous run of that segment's words). A purely
2791 | +connective line ("Next, ...") makes no claim.
2792 | +Return ONLY this JSON object: {{"claims": [{{"line": "<slot>", "claim": "...", "supported": "yes" | "no" | "uncertain",
2793 | +"support": [{{"segment": "<label>", "words": "<exact words>"}}]}}]}}"""
2794 | +
2795 | +
2796 | +def manifest_text(segments, manifest=None):
2797 | +    """The production facts a line may state: the credited channels, the show, the date, that source links are given."""
2798 | +    m = manifest or {}
2799 | +    chans = list(dict.fromkeys(list(m.get("channels") or []) + [s["speaker"] for s in segments.values()]))
2800 | +    parts = [f"The video is about Bitcoin and contains clips from {', '.join(chans)}.", f"There are {len(segments)} clips.",
2801 | +             "Links to every source are below.", "The voice-over is PBX MAX on Protocol Pulse."]
2802 | +    if m.get("show"):
2803 | +        parts.append(f"The show is {m['show']}.")
2804 | +    if m.get("date"):
2805 | +        parts.append(f"The show date is {m['date']}.")
2806 | +    return " ".join(parts)
2807 | +
2808 | +
2809 | +def verdict_prompt(segments, lines, manifest=None):
2810 | +    from story_semantics import quote_data
2811 | +    seg = "\n".join(f'<segment label="{mid}" speaker="{quote_data(s["speaker"], 80)}">{quote_data(s["text"], 900)}'
2812 | +                    f"</segment>" for mid, s in segments.items())
2813 | +    lns = "\n".join(f'<line slot="{ln["slot"]}">{quote_data(ln.get("text") or "", 400)}</line>' for ln in lines)
2814 | +    return VERDICT_PROMPT.format(segments=seg, lines=lns, manifest=manifest_text(segments, manifest))
2815 | +
2816 | +
2817 | +def check_verdict(raw, segments, lines, manifest=None):
2818 | +    """The blind verdict's reply (strict; never repaired) -> {"ok", "claims", "violations"}. A "yes" must cite one or
2819 | +    more segments (or "manifest"), each with words that are a verbatim run of that segment: an unverifiable support is
2820 | +    a failure (law L-m)."""
2821 | +    obj = json.loads(raw.strip()) if isinstance(raw, str) else None
2822 | +    if not isinstance(obj, dict) or set(obj) != {"claims"} or not isinstance(obj["claims"], list):
2823 | +        raise ValueError("the verdict must be exactly {'claims': [...]}")
2824 | +    slots = {ln["slot"] for ln in lines}
2825 | +    texts = dict({mid: s["text"] for mid, s in segments.items()}, manifest=manifest_text(segments, manifest))
2826 | +    v = []
2827 | +    for c in obj["claims"]:
2828 | +        if not isinstance(c, dict) or set(c) != {"line", "claim", "supported", "support"}:
2829 | +            raise ValueError("each claim needs exactly line, claim, supported, support")
2830 | +        if c["line"] not in slots or c["supported"] not in ("yes", "no", "uncertain") or \
2831 | +                not isinstance(c["claim"], str) or not isinstance(c["support"], list):
2832 | +            raise ValueError(f"claim on line {c.get('line')!r}: unknown line, 'supported' value or support list")
2833 | +        if c["supported"] != "yes":
2834 | +            v.append({"slot": c["line"], "rule": "VERDICT_" + c["supported"].upper(), "detail": c["claim"][:200]})
2835 | +            continue
2836 | +        good = [x for x in c["support"] if isinstance(x, dict) and x.get("segment") in texts and
2837 | +                isinstance(x.get("words"), str) and len(ctoks(x["words"])) >= 2 and
2838 | +                _run_in(ctoks(x["words"]), ctoks(texts[x["segment"]]))]
2839 | +        if not c["support"] or len(good) != len(c["support"]):
2840 | +            v.append({"slot": c["line"], "rule": "VERDICT_UNVERIFIED",
2841 | +                      "detail": f"supporting words are not verbatim runs of the cited segments: {c['claim'][:150]}"})
2842 | +    return {"ok": not v, "claims": obj["claims"], "violations": v}
2843 | +
2844 | +
2845 | +def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current_levels=None):
2846 | +    """Both layers. -> {"ok", "deterministic", "verdict", "violations", "backend"}; the verdict never runs on the
2847 | +    writer's vendor; a verdict that cannot be had or read is a failure (law L-m)."""
2848 | +    import providers as P
2849 | +    det = check_deterministic(segments, lines, manifest, current_levels)
2850 | +    out = {"deterministic": det, "verdict": None, "backend": None}
2851 | +    try:
2852 | +        r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
2853 | +                        avoid_vendor=writer_vendor)
2854 | +        out["backend"] = r.backend
2855 | +        out["verdict"] = check_verdict(r.text, segments, lines, manifest)
2856 | +    except (P.ProviderError, P.SpendLimit, ValueError) as e:
2857 | +        out["verdict"] = {"ok": False, "claims": [], "violations": [{"slot": "-", "rule": "VERDICT_UNAVAILABLE",
2858 | +                                                                      "detail": f"{type(e).__name__}: {str(e)[:200]}"}]}
2859 | +    out["violations"] = det["violations"] + out["verdict"]["violations"]
2860 | +    out["ok"] = det["ok"] and out["verdict"]["ok"]
2861 | +    return out
2862 | 
```

---

## YOUR REVIEW TASK: MOMENTS FIRST, THEN PACKAGE, BEHIND ONE PROVIDER INTERFACE (Python pipeline, no UI, no DB)

Context: Protocol Pulse makes 60-70 s Bitcoin videos made of other channels' own words (a hook + 2-3 clips, one clip
per channel) with a PBX MAX voice-over (VO) that makes a point. Nothing is published without a human. New modules:
- pipeline/providers.py + model_providers.json: ONE interface for every model role; a back-end chain per role (local
  gemma first); failover when a vendor is down; verdict roles never on the writer's vendor; record / replay; spend guard.
- pipeline/moments.py: mines MOMENTS by sentence id (strict reply contract, never repaired), judges each by the
  eligibility predicate, ranks deterministically; an exclusion verdict (accusations, ads, imperatives...).
- pipeline/package.py: angle first: step-A context prescreen -> angles (frontier) -> line-up per angle (code: one clip
  per channel, <= 20 s, 60-70 s runtime arithmetic) -> writer -> HARD integrity gates (vo_fidelity, DUPLICATE,
  PRICE_NOW, context_integrity) -> up to 3 rewrites with the exact rejected claims -> blind COHERENCE quality verdict
  -> law L-v 2 second recognition pass (transcript_truth.py) -> a package; plain VO only as the last resort.
- pipeline/vo_fidelity.py: deterministic rules (numbers, names, quotes, attribution, relation words, framing verbs,
  imperatives, time words, PRICE_NOW) + a blind verdict whose supporting words must be verbatim runs (code-checked).
- pipeline/context_integrity.py: step A (source context only), step B (the package only), step C (entailment), the
  decision rule in code; any "uncertain" fails.
- pipeline/trend_brief.py (shadow, weight 0), transcript_truth.py, moments_gate_adapter.py (the exam's adapter),
  package_pin.py (a package as the existing PINNED decision); REQUESTS R7 (exact pinned.py patch) / R8.

The only file is the exact diff under review. Review that diff, nothing else. Only state what you can verify from the
diff shown. If uncertain, say so. Do not guess. Cite diff lines (file + the code you quote).

### Q1: FAIL-OPEN IN THE GATES
Can a package be produced (returned as "package") while ANY hard gate failed, could not run, or ran on nothing: VO
fidelity (deterministic or verdict), DUPLICATE, PRICE_NOW, context integrity (A, B, C), runtime, the second
recognition pass? Can an unreadable / partial / "uncertain" model reply ever count as a pass? Can an exception inside a
gate be swallowed into a pass? Can the plain-VO fallback ship while failing a gate?

### Q2: VENDOR SEPARATION AND L-x
Can a verdict (fidelity, context A / B / C, coherence) ever run on the SAME vendor as the writer of the text it judges
(including after a failover, a rewrite by a fallback writer, or a precomputed step A)? Does any role hard-code a
vendor or model outside model_providers.json? Does the router's failover ever turn a contract violation into "use the
next back-end silently"?

### Q3: VERBATIM AND MODEL TEXT
Can text a model wrote (a miner's reason, an angle sentence, a verdict's reason, the trend brief) reach a clip's text,
the title, the caption or the VO without passing the fidelity gate? Is every clip the source sentences verbatim?

### Q4: THE DETERMINISTIC RULES
For each rule in vo_fidelity.check_deterministic and package.duplicates / price_now / current_levels: a false PASS
(something misleading that gets through) or a false REJECT (an honest line refused)? Name concrete inputs.

### Q5: TESTS AND THE WIRING (R7)
Do the tests fail for the right reason? Any vacuous assertion? Does R7's pinned.py patch refuse an ungated or
unplaceable package, and keep a plain pin unchanged?

Output: a scored list per question (0-100), then FINDINGS: P0 / P1 / P2 with file + quoted code + a concrete failing
input, then the single highest-leverage change.

