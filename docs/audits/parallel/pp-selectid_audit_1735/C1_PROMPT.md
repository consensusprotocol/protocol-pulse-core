# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-1735
# Branch: pp-selectid
# Generated: 2026-11-13 17:22 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_1735/C1_STEP.diff (568 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 80a8185..daf4da2 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -689,6 +689,10 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
   6 |          return out, None
   7 |      return out, err
   8 |  
   9 | +TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
  10 | +                 "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
  11 | +                 "upgrades a speaker's hedged view to a settled claim (\"Bitcoin's apolitical design is the real "
  12 | +                 "productivity story.\" after a speaker's 'I think Bitcoin will outperform').")   # orchestrator 17:20
  13 |  WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  14 |  THE ANGLE (the point this video makes): "{angle}"
  15 |  The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
  16 | @@ -701,6 +705,7 @@ After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off cr
  17 |  {bridge}Write:
  18 |  - "takeaway": {lo}-{hi} words in short declarative sentences: the point the medley adds up to, as YOUR OWN
  19 |    commentary (your opinion or conclusion), a point and not a summary, never a restatement of any clip.
  20 | +  {said}
  21 |  - "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
  22 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
  23 |  RULES (a line that breaks one is rejected):
  24 | @@ -1568,7 +1573,8 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  25 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
  26 |      prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
  27 |                               lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
  28 | -                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES)
  29 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES,
  30 | +                             said=TAKEAWAY_SAID)
  31 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
  32 |      try:
  33 |          obj = json.loads(r.text.strip())
  34 | @@ -1614,27 +1620,48 @@ ids) or your own commentary, which states no fact; never a claim the clips do no
  35 |  cites the clips it comes from.
  36 |  {style}
  37 |  Return ONLY this JSON object: {{"{slot}": {{"text": "...", "cites": []}}}}"""   # RULING 65: one line, alone
  38 | -LINE_WHY = {"VERDICT_NO": "the fact check found that the clips do not say it",
  39 | +LINE_WHY = {"AGAIN": "your first rewrite of it was refused too",   # 17:20: a title's second write is told
  40 | +            "VERDICT_NO": "the fact check found that the clips do not say it",
  41 |              "VERDICT_UNCERTAIN": "the fact check could not find it in the clips",
  42 |              "STYLE": "it breaks the house style"}
  43 |  LINE_LIMIT = {"caption": "at most 220 characters", "title": "at most 70 characters"}
  44 | -
  45 | -
  46 | -def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None):
  47 | +LINE_CHARS = {"caption": 220, "title": 70, "takeaway": 240}
  48 | +LINE_ONLY_WRITES = 2                  # RULING 66 amended (17:02 Nov 13): "up to TWO fresh writes of the failed line only"
  49 | +TAKEAWAY_LIMIT = ("{lo}-{hi} words, one or two sentences: host commentary attributed to nobody that states no fact, no "
  50 | +                  "speaker's view, no advice or prediction and no accusation, and that no viewer could take for a "
  51 | +                  "speaker's words")
  52 | +TAKEAWAY_WHY = dict(VO_FIX, **LINE_WHY, COMMENTARY="as host commentary it must state no fact, no speaker's view, no "
  53 | +                    "advice or prediction and no accusation, and must not sound like a speaker",
  54 | +                    COHERENCE="a blind viewer did not find its point supported by the clips",
  55 | +                    RUNTIME="with it the video does not land 60-70 s")
  56 | +
  57 | +
  58 | +def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None, avoid_model=None,
  59 | +               limit=None):
  60 |      """RULING 65: ONE more write for one line alone ("caption" or "title"): the angle, the line-up, the other lines kept
  61 |      as gated, and the refused sentence(s) with why. A new prompt (WRITE_LINE), so a recorded reply is never replayed
  62 | -    into it. -> (reply, {"text", "cites"}); a reply out of contract raises (and is rejected)."""
  63 | +    into it. -> (reply, {"text", "cites"}); a reply out of contract raises (and is rejected).
  64 | +    RULING 66 amended (17:02): the takeaway alone too. Each refused entry carries the refused sentence ("text") and why
  65 | +    (its rule in plain words, and the gate's detail); the bridge is among the kept lines; `limit` gives its words;
  66 | +    avoid_model puts the second attempt on the other writer model. Ruling 65's prompts are unchanged byte for byte."""
  67 |      from select_by_id import UNTRUSTED
  68 |      from story_semantics import quote_data
  69 |      q = lambda t, n: " ".join(quote_data(t, n).replace('"', "'").split())
  70 |      kept = "\n".join(f'{s.upper()}: "{q(fields[s]["text"], 300)}"' for s in ("takeaway", "title", "caption")
  71 |                       if s != slot and fields.get(s))
  72 | -    why = "; ".join(f'"{q(v.get("detail") or "", 200)}" ({LINE_WHY.get(v.get("rule"), v.get("rule"))})'
  73 | -                    for v in refused)
  74 | +    if slot == "takeaway":                               # ruling 66 amended: the sentences it may not repeat
  75 | +        if (fields.get("bridge") or {}).get("text"):
  76 | +            kept += f'\nBRIDGE (spoken between two clips): "{q(fields["bridge"]["text"], 300)}"'
  77 | +        why = "; ".join(f'"{q(v.get("text") or "", 300)}" ({TAKEAWAY_WHY.get(v.get("rule"), v.get("rule"))}: '
  78 | +                        f'{q(v.get("detail") or "", 240)})' for v in refused) + ". " + TAKEAWAY_SAID
  79 | +    else:
  80 | +        why = "; ".join(f'"{q(v.get("detail") or "", 200)}" ({LINE_WHY.get(v.get("rule"), v.get("rule"))})'
  81 | +                        for v in refused)
  82 |      prompt = WRITE_LINE.format(angle=q(angle["angle"], 300), note=UNTRUSTED.replace("<sentences>", "the quotes"),
  83 |                                 lineup=_lineup_block(segs, ctx, a_by), kept=kept, slot=slot, refused=why,
  84 | -                               limit=LINE_LIMIT[slot], style=HS.PROMPT_RULES)
  85 | -    r = router.call("angle_write", prompt, 1500, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
  86 | +                               limit=limit or LINE_LIMIT[slot], style=HS.PROMPT_RULES)
  87 | +    r = router.call("angle_write", prompt, 1500, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S,
  88 | +                    **({"avoid_model": avoid_model} if avoid_model else {}))
  89 |      try:
  90 |          obj = json.loads(r.text.strip())
  91 |          ids = [m["moment_id"] for m in segs]
  92 | @@ -1642,9 +1669,9 @@ def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, av
  93 |          if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
  94 |                  not ln["text"].strip() or not isinstance(ln["cites"], list) or \
  95 |                  any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
  96 | -                len(ln["text"]) > (220 if slot == "caption" else 70):
  97 | +                len(ln["text"]) > LINE_CHARS[slot]:
  98 |              raise ValueError(f"exactly {{'{slot}': {{'text', 'cites'}}}}, cites from the line-up's ids, "
  99 | -                             f"{LINE_LIMIT[slot]}")
 100 | +                             f"at most {LINE_CHARS[slot]} characters")
 101 |      except (ValueError, TypeError, AttributeError):
 102 |          router.reject(r)
 103 |          raise
 104 | @@ -1658,6 +1685,54 @@ def lone_slot(violations):
 105 |      return next(iter(slots)) if len(slots) == 1 and slots <= {"caption", "title"} else None
 106 |  
 107 |  
 108 | +def _words_in(words, text):
 109 | +    """A verbatim run (>= 2 canonical tokens) of `words` in `text` (as context_integrity.raising_words_ok matches)."""
 110 | +    import canon
 111 | +    if not isinstance(words, str) or not isinstance(text, str):
 112 | +        return False
 113 | +    wt, tt = canon.canon_tokens(words), canon.canon_tokens(text)
 114 | +    return len(wt) >= 2 and any(tt[i:i + len(wt)] == wt for i in range(len(tt) - len(wt) + 1))
 115 | +
 116 | +
 117 | +def takeaway_refusal(fields, violations, cx=None):
 118 | +    """RULING 66 amended (17:02): one write's failures that are the TAKEAWAY's own -> (entries, alone). An entry
 119 | +    {"text": the refused takeaway, "rule", "detail"} is a violation on its slot; RUNTIME or R4 on the whole video ("-"),
 120 | +    which with the other lines kept only the takeaway's length moves; or a context failure the video's words caused
 121 | +    (STRONGER: step C's raising_words; NOT_ENTAILED: its added_by) when those words are a run of the takeaway and of no
 122 | +    other line. alone: every failure of the write is such an entry (none on another line, none a clip's own, none that
 123 | +    no line's words caused), so the takeaway alone may be written again."""
 124 | +    t = ((fields or {}).get("takeaway") or {}).get("text") or ""
 125 | +    others = [((fields or {}).get(s) or {}).get("text") or "" for s in ("title", "caption", "bridge")]
 126 | +    cseg = (cx or {}).get("segments") or {}
 127 | +    entries, alone = [], bool(violations) and bool(t.strip())
 128 | +    for v in violations or []:
 129 | +        rule, detail = v.get("rule"), str(v.get("detail") or "")
 130 | +        own = v.get("slot") == "takeaway" or (v.get("slot") == "-" and rule in ("RUNTIME", "R4"))
 131 | +        if not own and v.get("segment") in cseg and (
 132 | +                (rule == "STRONGER" and detail.startswith("stronger certainty: the video's words")) or
 133 | +                (rule == "NOT_ENTAILED" and detail.startswith("the video's words"))):
 134 | +            c = (cseg[v["segment"]] or {}).get("C") or {}
 135 | +            w = c.get("raising_words") if rule == "STRONGER" else c.get("added_by")
 136 | +            own = _words_in(w, t) and not any(_words_in(w, o) for o in others)
 137 | +        if own:
 138 | +            entries.append({"text": t, "rule": rule, "detail": detail[:300]})
 139 | +        else:
 140 | +            alone = False
 141 | +    return entries, alone
 142 | +
 143 | +
 144 | +def takeaway_alone_gates(router, pk, fid, sources, a_by, levels, now, writers_v, writers_f):
 145 | +    """RULING 66 amended (17:02): the paid gates of a package whose takeaway alone was written again, the other lines
 146 | +    kept as gated (their verdicts in `fid`, the write they came from): the blind fidelity verdict on the takeaway ALONE,
 147 | +    merged (merge_fid), and context integrity on the package as it will be sealed. -> (fid, cx)."""
 148 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 149 | +    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"] if x["slot"] == "takeaway"]
 150 | +    one = VF.check(router, fidelity_segments(pk, a_by), ln, writers_v, 7, man, levels, writers_f)
 151 | +    a_use = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 152 | +    cx = CI.check_contexts(router, pk, CI.contexts_from_sources(pk, sources, now), writers_v, 7, a_use, writers_f, True)
 153 | +    return merge_fid(fid, "takeaway", one), cx
 154 | +
 155 | +
 156 |  def fixed_caption(fields, segs, ctx):
 157 |      """RULING 65 (b): the caption that states no fact, written by code: the gated title in lowercase, a line break, then
 158 |      the channel names in play order separated by ' / ', lowercase too (PBX's house style: a caption is all lowercase,
 159 | @@ -1705,33 +1780,43 @@ def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ct
 160 |          p = assemble_medley(order, by_id, dict(fields, **{slot: line}), ctx, f"{pk.get('vo_kind')}; {why}")
 161 |          p["medley"] = pk.get("medley")
 162 |          return p
 163 | -    try:
 164 | -        r, line = write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=seed,
 165 | -                             avoid_vendor=avoid_vendor)
 166 | -        rec.update(written=line["text"], writer=r.backend)
 167 | -        writers_v.add(r.vendor)                          # L-x: the line's verdict never comes from its writer
 168 | -        writers_f.add(r.family)
 169 | -        pk2 = build_pk(line, f"the {slot} rewritten alone (ruling 65 a)")
 170 | -        cheap2 = cheap_checks(pk2, a_by, levels, ctx.now)
 171 | -        if cheap2[0]:
 172 | -            raise ValueError("cheap gates: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in cheap2[0])[:300])
 173 | -        ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk2["lines"] if x["slot"] == slot]
 174 | -        one = VF.check(router, fidelity_segments(pk2, a_by), ln, writers_v, 7, man, levels, writers_f)
 175 | -        rec["verdict"] = {"ok": one["ok"], "violations": one["violations"], "backend": one.get("backend")}
 176 | -        if not one["ok"]:
 177 | -            raise ValueError("fidelity: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in one["violations"])[:300])
 178 | -        fid2 = merge_fid(fid, slot, one)
 179 | -        cx2 = CI.check_contexts(router, pk2, CI.contexts_from_sources(pk2, sources, ctx.now), writers_v, 7, a_use(pk2),
 180 | -                                writers_f, True)
 181 | -        if not (fid2["ok"] and cx2["ok"]):
 182 | -            raise ValueError("context integrity on the package with it: " +
 183 | -                             "; ".join(f"{v['rule']}" for v in cx2["violations"])[:200])
 184 | -        rec["passed"] = True
 185 | -        return pk2, fid2, cx2, cheap2, rec
 186 | -    except Exception as e:
 187 | -        rec.update(passed=False, why=f"{type(e).__name__}: {str(e)[:300]}")
 188 | +    told, by = list(refused), None                      # 17:20: a title's second write, on the other writer model
 189 | +    for k in range(LINE_ONLY_WRITES if slot == "title" else 1):
 190 | +        r, line = None, None
 191 | +        try:
 192 | +            r, line = write_line(router, angle, segs, ctx, a_by, slot, fields, told, seed=seed,
 193 | +                                 avoid_vendor=avoid_vendor, avoid_model={by} if by else None)
 194 | +            rec.update(written=line["text"], writer=r.backend)
 195 | +            writers_v.add(r.vendor)                      # L-x: the line's verdict never comes from its writer
 196 | +            writers_f.add(r.family)
 197 | +            pk2 = build_pk(line, f"the {slot} rewritten alone (ruling 65 a)")
 198 | +            cheap2 = cheap_checks(pk2, a_by, levels, ctx.now)
 199 | +            if cheap2[0]:
 200 | +                raise ValueError("cheap gates: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in cheap2[0])[:300])
 201 | +            ln = [{k_: x[k_] for k_ in ("slot", "text", "cites")} for x in pk2["lines"] if x["slot"] == slot]
 202 | +            one = VF.check(router, fidelity_segments(pk2, a_by), ln, writers_v, 7, man, levels, writers_f)
 203 | +            rec["verdict"] = {"ok": one["ok"], "violations": one["violations"], "backend": one.get("backend")}
 204 | +            if not one["ok"]:
 205 | +                raise ValueError("fidelity: " + "; ".join(f"{v['rule']}: {v['detail']}"
 206 | +                                                          for v in one["violations"])[:300])
 207 | +            fid2 = merge_fid(fid, slot, one)
 208 | +            cx2 = CI.check_contexts(router, pk2, CI.contexts_from_sources(pk2, sources, ctx.now), writers_v, 7,
 209 | +                                    a_use(pk2), writers_f, True)
 210 | +            if not (fid2["ok"] and cx2["ok"]):
 211 | +                raise ValueError("context integrity on the package with it: " +
 212 | +                                 "; ".join(f"{v['rule']}" for v in cx2["violations"])[:200])
 213 | +            rec["passed"] = True
 214 | +            return pk2, fid2, cx2, cheap2, rec
 215 | +        except Exception as e:
 216 | +            rec.update(passed=False, why=f"{type(e).__name__}: {str(e)[:300]}")
 217 | +            rec.setdefault("tries", []).append({"written": (line or {}).get("text"),
 218 | +                                                "writer": r.backend if r is not None else None, "why": rec["why"]})
 219 | +            by = r.backend if r is not None else by
 220 | +            if line is not None:
 221 | +                told = told + [{"rule": "AGAIN", "detail": f"{line['text']}: {str(e)[:200]}"}]
 222 |      if slot != "caption":                                # (c): a title that fails again is held
 223 | -        rec["why"] = f"the title failed alone twice: held (ruling 65 c): {rec['why']}"
 224 | +        rec["why"] = (f"the title failed alone {1 + len(rec.get('tries') or [])} times (its second write on the other "
 225 | +                      f"writer model, 17:20): held (ruling 65 c): {rec['why']}")
 226 |          return pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, a_by, levels, ctx.now), rec
 227 |      line = fixed_caption(fields, segs, ctx)               # (b): the fixed caption, code-written, no model
 228 |      pk3 = build_pk(line, "the fixed caption (ruling 65 b)")
 229 | @@ -2577,27 +2662,52 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 230 |                      rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 231 |                      relined, w_used = True, writes      # no write is paid
 232 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 233 | -                while w_used < writes:
 234 | +                alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 235 | +                while True:                                # RULING 66 amended (17:02): the writes; then, when the
 236 | +                    lone = w_used >= writes                # takeaway alone failed, the takeaway ALONE, up to twice
 237 | +                    if lone and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None and
 238 | +                                     not last_rw65):
 239 | +                        break
 240 |                      if over_budget(ai):
 241 |                          break
 242 |                      w_over = package_over(line)
 243 |                      if w_over:
 244 |                          rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 245 |                          break
 246 | -                    w_used += 1
 247 | -                    try:
 248 | -                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 249 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 250 | -                                                    avoid_vendor=writer_avoid or None, other=written)
 251 | -                    except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 252 | -                        if join is not None:
 253 | -                            dropped.add(segs[join[0] + 1]["moment_id"])
 254 | -                        rec["why"] = f"{e}: re-lined"
 255 | -                        relined = join is not None
 256 | -                        break
 257 | -                    except Exception as e:
 258 | -                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 259 | -                        continue
 260 | +                    if lone:                               # the other lines kept as gated; told each refusal and why
 261 | +                        alone_n += 1
 262 | +                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 263 | +                        if b is None:
 264 | +                            rec["attempts"].append({"writer_error": "no takeaway length lands 60-70 s with the kept "
 265 | +                                                                    "lines", "takeaway_alone": alone_n})
 266 | +                            break
 267 | +                        try:
 268 | +                            wr, tl = write_line(router, angle, segs, ctx, a_by, "takeaway", last_fields, t_refused,
 269 | +                                                seed=7 + w_used + alone_n + 10 * ai + 100 * n_lineup + wseed,
 270 | +                                                avoid_vendor=writer_avoid or None,
 271 | +                                                avoid_model={alone_by} if alone_by else None,   # the other model
 272 | +                                                limit=TAKEAWAY_LIMIT.format(lo=b[0], hi=b[1]))
 273 | +                        except Exception as e:
 274 | +                            rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}",
 275 | +                                                    "takeaway_alone": alone_n})
 276 | +                            continue
 277 | +                        alone_by = wr.backend
 278 | +                        fields = dict(last_fields, takeaway=tl, takeaway_budget=list(b))
 279 | +                    else:
 280 | +                        w_used += 1
 281 | +                        try:
 282 | +                            wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 283 | +                                                        seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 284 | +                                                        avoid_vendor=writer_avoid or None, other=written)
 285 | +                        except NoBridgeFits as e:              # the seconds rule it out: re-line, no write is paid
 286 | +                            if join is not None:
 287 | +                                dropped.add(segs[join[0] + 1]["moment_id"])
 288 | +                            rec["why"] = f"{e}: re-lined"
 289 | +                            relined = join is not None
 290 | +                            break
 291 | +                        except Exception as e:
 292 | +                            rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 293 | +                            continue
 294 |                      writers_v.add(wr.vendor)
 295 |                      writers_f.add(wr.family)
 296 |                      for m in segs:                             # item 45: the verdict off every writer, when one exists
 297 | @@ -2639,19 +2749,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 298 |                                                           "backend": med.get("backend")}
 299 |                      fields["supply_exception"] = exception
 300 |                      pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 301 | -                                         f"medley (L-y), written, attempt {w_used}")
 302 | +                                         f"medley (L-y), written, attempt {w_used}" +
 303 | +                                         (f", the takeaway alone {alone_n} (ruling 66, 17:02)" if lone else ""))
 304 |                      pk["medley"] = med
 305 |                      written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
 306 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 307 |                      att = {"writer": wr.backend, "writer_tried": [list(x) for x in getattr(wr, "tried", [])],   # ruling 5
 308 |                             "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 309 |                             "takeaway_budget": fields.get("takeaway_budget"),
 310 | -                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 311 | +                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]],
 312 | +                           **({"takeaway_alone": {"attempt": alone_n, "refused": [dict(x) for x in t_refused]}}
 313 | +                              if lone else {})}
 314 |                      rec["attempts"].append(att)
 315 | -                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 316 | +                    take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap)
 317 |                      out["takeaways"].append(take)
 318 |                      last_fields = fields
 319 | -                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 320 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used + alone_n}" +
 321 | +                        (" (the takeaway alone, ruling 66 17:02)" if lone else "") +
 322 | +                        f" ({wr.backend}, takeaway {take['words']} "
 323 |                          f"words, {pk['runtime_s_estimate']} s): " +
 324 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 325 |                          + f" ({time.time() - t0:.0f} s)")
 326 | @@ -2672,6 +2787,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 327 |                      if cheap and lone_slot(cheap) is None:     # ruling 65: a lone caption / title goes on
 328 |                          att["violations"] = cheap
 329 |                          take_failed += take["passed"] is False
 330 | +                        own, t_alone = takeaway_refusal(fields, cheap)          # ruling 66 amended (17:02)
 331 | +                        t_refused += [e for e in own if e not in t_refused]
 332 | +                        last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 333 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 334 |                          extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 335 |                                                                       if b else " (no takeaway length lands it with this "
 336 | @@ -2679,8 +2797,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 337 |                                                                       else " (no takeaway length lands it)"))
 338 |                                         if v["rule"] == "RUNTIME" else v for v in cheap])
 339 |                          continue
 340 | -                    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 341 | -                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 342 | +                    if lone and last_fid is not None:      # ruling 66 amended: the kept lines keep their verdicts
 343 | +                        fid, cx = takeaway_alone_gates(router, pk, last_fid, sources, a_by, levels, ctx.now,
 344 | +                                                       writers_v, writers_f)
 345 | +                    else:
 346 | +                        fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 347 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap, fid, cx)
 348 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 349 |                      att["violations"] = cheap + fid["violations"] + cx["violations"]
 350 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 351 | @@ -2710,6 +2832,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 352 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 353 |                              w_used = writes
 354 |                              break
 355 | +                        own, t_alone = takeaway_refusal(fields, cheap + fid["violations"] + cx["violations"], cx)
 356 | +                        t_refused += [e for e in own if e not in t_refused]   # ruling 66 amended: what it is told
 357 | +                        last_fid, last_rw65 = fid, bool(att.get("rewrite"))
 358 |                          extra = _redo(cheap + fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
 359 |                                                                      "detail": VO_FIX.get(v["rule"], v["detail"])}
 360 |                                                                     for v in framing])
 361 | @@ -2738,6 +2863,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 362 |                              extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 363 |                                              f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 364 |                                              f"being supported by the clips: land the point the clips make together"}])
 365 | +                            ref = {"text": ((fields.get("takeaway") or {}).get("text") or ""), "rule": "COHERENCE",
 366 | +                                   "detail": f"a blind viewer rated its point {coh['vo_point']} of 5"}   # ruling 66
 367 | +                            t_refused += [ref] if ref not in t_refused else []
 368 | +                            t_alone, last_fid, last_rw65 = True, fid, bool(att.get("rewrite"))
 369 |                              continue                          # the clips hold; only the takeaway's point is weak
 370 |                          weak = {sg["moment_id"] for sg in pk["segments"][1:]
 371 |                                  if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 372 | @@ -2771,7 +2900,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 373 |                  if not out["packages"] and not rec.get("why") and not rec.get("result"):
 374 |                      last = (rec.get("attempts") or [{}])[-1]
 375 |                      rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
 376 | -                    rec["why"] = f"{w_used} write(s) failed their gates" + (f" ({', '.join(rules)})" if rules else "")
 377 | +                    rec["why"] = (f"{w_used} write(s)" + (f" and {alone_n} of the takeaway alone (ruling 66, 17:02)"
 378 | +                                                          if alone_n else "") + " failed their gates" +
 379 | +                                  (f" ({', '.join(rules)})" if rules else ""))
 380 |                  if out["packages"] or not relined:
 381 |                      break
 382 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
 383 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 384 | index a002883..675c350 100644
 385 | --- a/tests/package/test_medley.py
 386 | +++ b/tests/package/test_medley.py
 387 | @@ -11,6 +11,7 @@
 388 |  - The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
 389 |  """
 390 |  import json
 391 | +import re
 392 |  import os
 393 |  import sys
 394 |  import unittest
 395 | @@ -1856,6 +1857,172 @@ class TestRuling66Candidate(unittest.TestCase):
 396 |          self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"]])
 397 |  
 398 |  
 399 | +class TestRuling66Amended(unittest.TestCase):
 400 | +    """RULING 66 amended (17:02 Nov 13): a line-up whose clips pass and whose takeaway alone failed gets, at once, up to
 401 | +    TWO writes of the takeaway ALONE (told each refused sentence and why; the second on the other writer model), the
 402 | +    other lines kept as gated; then ruling 3's no-voice fallback when its seconds allow, else the line-up rests."""
 403 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 404 | +    WHY = "host commentary 'Nobody gets to bend these rules' fails imperative_or_prediction"
 405 | +
 406 | +    def failing(self, slot="takeaway", detail=WHY, rule="COMMENTARY"):
 407 | +        return TestRuling65Caption.failing(TestRuling65Caption(), slot, detail, rule)
 408 | +
 409 | +    def run_rig(self, fids, lines, alone_ok=(True,), ms=None, takeaways=None, medleys=None):
 410 | +        import context_integrity as CI
 411 | +        import vo_fidelity as VF
 412 | +        seen, ok_q, avoid = [], list(alone_ok), {}
 413 | +
 414 | +        def one(router, segs, lns, *a, **k):
 415 | +            seen.append([ln["text"] for ln in lns])
 416 | +            ok = ok_q.pop(0) if ok_q else True
 417 | +            v = [] if ok else [{"slot": lns[0]["slot"], "rule": "COMMENTARY", "detail": f"'{lns[0]['text']}' fails x"}]
 418 | +            return {"ok": ok, "violations": v, "measured": True, "replayed": False, "backend": "xai:grok",
 419 | +                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 420 | +                    "verdict": {"ok": ok, "violations": v, "classes": {lns[0]["slot"]: ["commentary"]}, "claims": []}}
 421 | +        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
 422 | +        VF.check = one
 423 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 424 | +                                             "backends": {"B": "xai", "C": "xai"}}
 425 | +        CI.contexts_from_sources = lambda *a, **k: {}
 426 | +        try:
 427 | +            rig = Rig(ms or self.MS, ["h", "x", "y", "z"] if ms else ["h", "x", "y"],
 428 | +                      medleys or [(True, [], None, Rig.LINE)], [None, None], fids=fids, lines=lines,
 429 | +                      takeaways=takeaways)
 430 | +            inner = rig.router.call
 431 | +
 432 | +            def spy(role, prompt, *a, **k):
 433 | +                m = re.search(r"Your (\w+) was refused", prompt) if role == "angle_write" else None
 434 | +                if m:                                          # each line written alone: the model it avoided
 435 | +                    avoid.setdefault(m.group(1), []).append(k.get("avoid_model"))
 436 | +                return inner(role, prompt, *a, **k)
 437 | +            rig.router.call = spy
 438 | +            return rig, rig.run(), seen, avoid
 439 | +        finally:
 440 | +            VF.check, CI.check_contexts, CI.contexts_from_sources = saved
 441 | +
 442 | +    def test_both_writes_refuse_the_takeaway_then_the_takeaway_alone_passes(self):
 443 | +        new = "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."   # 18 words: the budget of 39 s of clips
 444 | +        rig, out, seen, avoid = self.run_rig([self.failing(), self.failing()], [{"takeaway": {"text": new,
 445 | +                                                                                              "cites": []}}])
 446 | +        pk = out["package"]
 447 | +        self.assertIsNotNone(pk)
 448 | +        lines = {x["slot"]: x["text"] for x in pk["lines"]}
 449 | +        self.assertEqual(lines["takeaway"], new)
 450 | +        self.assertEqual((lines["title"], lines["caption"]), ("Nobody bends the rules", "nobody bends these rules"))
 451 | +        prompt = [p for r, p in rig.prompts if r == "angle_write"][-1]
 452 | +        self.assertIn("Your takeaway was refused", prompt)                    # told the refused sentence and why
 453 | +        self.assertIn(f'"{Rig.LINE}" (as host commentary it must state no fact', prompt)
 454 | +        self.assertIn("fails imperative_or_prediction", prompt)
 455 | +        self.assertIn('TITLE: "Nobody bends the rules"', prompt)              # the other lines, kept as gated
 456 | +        self.assertNotIn('TAKEAWAY: "', prompt)
 457 | +        self.assertEqual(seen, [[new]])                                        # the verdict on the takeaway alone
 458 | +        self.assertEqual(len(rig.write_calls), 2)                              # the two writes, then the line alone
 459 | +        att = out["tried"][0]["attempts"][2]
 460 | +        self.assertEqual((att["takeaway_alone"]["attempt"], len(att["takeaway_alone"]["refused"])), (1, 1))
 461 | +        self.assertEqual(prompt.count(f'"{Rig.LINE}"'), 1)                    # the same refusal told once
 462 | +        self.assertEqual(pk["gates"]["vo_fidelity_verdict"]["status"], "PASS")
 463 | +        self.assertEqual(avoid, {"takeaway": [None]})
 464 | +        self.assertEqual([t["write"] for t in out["takeaways"]], [1, 2, 3])
 465 | +        self.assertIn(PK.TAKEAWAY_SAID, prompt)                                # 17:20: the patterns refused today
 466 | +
 467 | +    def test_the_second_takeaway_alone_is_on_the_other_writer_model(self):
 468 | +        a1, a2 = "Rules nobody can bend are rules that work the same way for every single person who holds them.", "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
 469 | +        rig, out, seen, avoid = self.run_rig([self.failing(), self.failing()],
 470 | +                                             [{"takeaway": {"text": a1, "cites": []}},
 471 | +                                              {"takeaway": {"text": a2, "cites": []}}], alone_ok=(False, True))
 472 | +        self.assertEqual(avoid, {"takeaway": [None, {"fake:angle_write"}]})   # the first one's model avoided
 473 | +        self.assertEqual(seen, [[a1], [a2]])
 474 | +        prompts = [p for r, p in rig.prompts if r == "angle_write" and "Your takeaway was refused" in p]
 475 | +        self.assertIn(f'"{a1}"', prompts[1])                                   # its own refusal told too
 476 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "takeaway"), a2)
 477 | +
 478 | +    def test_both_takeaway_alone_writes_fail_and_the_line_up_rests(self):
 479 | +        rig, out, seen, _ = self.run_rig([self.failing(), self.failing()],
 480 | +                                         [{"takeaway": {"text": "Rules nobody can bend are rules that work the same way for every single person who holds them.", "cites": []}},
 481 | +                                          {"takeaway": {"text": "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere.", "cites": []}}],
 482 | +                                         alone_ok=(False, False))
 483 | +        self.assertIsNone(out["package"])
 484 | +        self.assertEqual(len(seen), 2)                                         # up to TWO, never more
 485 | +        self.assertIn("2 write(s) and 2 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])
 486 | +        self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then rest
 487 | +
 488 | +    def test_a_failure_on_another_line_gets_no_takeaway_alone_write(self):
 489 | +        both = dict(self.failing(), violations=[{"slot": "takeaway", "rule": "COMMENTARY", "detail": self.WHY},
 490 | +                                                {"slot": "caption", "rule": "VERDICT_NO", "detail": "x"}])
 491 | +        both["verdict"] = dict(both["verdict"], violations=both["violations"])
 492 | +        rig, out, seen, avoid = self.run_rig([both, both], [{"takeaway": {"text": "never asked", "cites": []}}])
 493 | +        self.assertIsNone(out["package"])
 494 | +        self.assertEqual((seen, avoid), ([], {}))
 495 | +
 496 | +    def test_the_no_voice_fallback_comes_after_the_takeaway_alone(self):
 497 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 498 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 499 | +        rig, out, seen, avoid = self.run_rig([], [{"takeaway": {"text": "Ultimately nobody bends the rules.",
 500 | +                                                                "cites": []}},
 501 | +                                                  {"takeaway": {"text": "In the end nobody bends them.", "cites": []}}],
 502 | +                                             ms=ms, takeaways=bad,
 503 | +                                             medleys=[(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)])
 504 | +        self.assertEqual(len(avoid["takeaway"]), 2)                            # the takeaway alone, twice (STYLE)
 505 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")   # then ruling 3
 506 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])
 507 | +
 508 | +    def test_a_title_refused_alone_gets_its_second_write_on_the_other_model_then_is_held(self):
 509 | +        """17:20: YES, the second attempt applies to a failed title too (two writes of the title alone, the second on
 510 | +        the other writer model), then hold as ruling 65 says."""
 511 | +        t1, t2 = "Rules nobody can bend", "Nobody bends these rules"
 512 | +        refused = self.failing("title", "Bitcoin is owned by nobody at all", "VERDICT_NO")
 513 | +        replies = [{"title": {"text": t1, "cites": []}}, {"title": {"text": t2, "cites": []}}]
 514 | +        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, True))
 515 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"), t2)
 516 | +        self.assertEqual(avoid, {"title": [None, {"fake:angle_write"}]})
 517 | +        second = [p for r, p in rig.prompts if r == "angle_write" and "Your title was refused" in p][1]
 518 | +        self.assertIn(f'"{t1}: ', second)                                       # told the first rewrite's refusal
 519 | +        self.assertIn("(your first rewrite of it was refused too)", second)
 520 | +        self.assertEqual(len(out["tried"][0]["attempts"][0]["rewrite"]["tries"]), 1)
 521 | +        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, False))
 522 | +        self.assertIsNone(out["package"])                                      # then held (ruling 65 c)
 523 | +        self.assertEqual(len(seen), 2)                                          # two writes of the title, no more
 524 | +        self.assertIn("the title failed alone 3 times", out["tried"][0]["why"])
 525 | +        self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
 526 | +        rig, out, seen, avoid = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
 527 | +                                                                                      "cites": []}}],
 528 | +                                             alone_ok=(False,))
 529 | +        self.assertEqual((len(seen), avoid), (1, {"caption": [None]}))          # the caption: one, then the fixed line
 530 | +        self.assertTrue(out["package"]["caption_fallback"])
 531 | +
 532 | +    def test_both_takeaway_prompts_name_the_two_refused_patterns(self):
 533 | +        """17:20: the takeaway writer is told the two patterns refused today, and that the line may characterise what
 534 | +        was SAID, not what WILL happen: in the full write's prompt and in the takeaway written alone."""
 535 | +        self.assertIn("SAID, never what WILL happen", PK.TAKEAWAY_SAID)
 536 | +        self.assertIn("a forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.')", PK.TAKEAWAY_SAID)
 537 | +        self.assertIn("a superlative that upgrades a speaker's hedged view to a settled claim", PK.TAKEAWAY_SAID)
 538 | +        r = Canned(angle_write=[{"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None,
 539 | +                                 "title": {"text": "No ruler.", "cites": ["h"]},
 540 | +                                 "caption": {"text": "three clips", "cites": []}}])
 541 | +        prompts, inner = [], r.call
 542 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), inner(role, prompt, *a, **k))[1]
 543 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), TestWriteTakeaway.SEGS, E.Context(NOW, REG), {})
 544 | +        self.assertIn(PK.TAKEAWAY_SAID, prompts[0])
 545 | +
 546 | +    def test_which_failures_are_the_takeaways_own(self):
 547 | +        f = {"takeaway": {"text": "Bitcoin's apolitical design is the real productivity story."},
 548 | +             "title": {"text": "Apolitical money"}, "caption": {"text": "a steadier design"}, "bridge": None}
 549 | +        strong = {"segment": "clip_02", "rule": "STRONGER",
 550 | +                  "detail": "stronger certainty: the video's words 'x' make the clip sound likely"}
 551 | +        cx = lambda w: {"segments": {"clip_02": {"C": {"raising_words": w}}}}
 552 | +        own, alone = PK.takeaway_refusal(f, [strong], cx("the real productivity story"))
 553 | +        self.assertEqual((alone, own[0]["text"], own[0]["rule"]), (True, f["takeaway"]["text"], "STRONGER"))
 554 | +        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("Apolitical money"))[1], False)       # the title's
 555 | +        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("apolitical"))[1], False)             # < 2 tokens
 556 | +        unsure = dict(strong, detail="stronger certainty: uncertain")
 557 | +        self.assertEqual(PK.takeaway_refusal(f, [unsure], cx("the real productivity story"))[1], False)
 558 | +        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "RUNTIME", "detail": "72 s"}])[1], True)
 559 | +        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "LY_SHAPE", "detail": "x"}])[1], False)
 560 | +        self.assertEqual(PK.takeaway_refusal(f, [])[1], False)                                     # no failure
 561 | +        self.assertEqual(PK.takeaway_refusal(f, [{"segment": "clip_02", "rule": "POLARITY", "detail": "x"}],
 562 | +                                             cx("the real productivity story"))[1], False)        # a clip's own
 563 | +
 564 | +
 565 |  class TestRuling65Caption(unittest.TestCase):
 566 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 567 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 568 | 
```

---

You are auditing a change to the medley package builder on branch pp-selectid (Protocol Pulse: the builder of sealed
medley pins). Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- package.build: for a line-up whose clips pass the clips-alone verdict, a writer model writes the lines in one full
  write (write_takeaway: the TAKEAWAY, host commentary after the last clip; the TITLE; the CAPTION; a BRIDGE only at a
  join the verdict flagged). Each write is gated:
  - cheap_checks (deterministic: house style, runtime 60-70 s, R4, the deterministic fidelity layer);
  - paid_gates: the blind fidelity verdict on every line, and context integrity per clip, whose step C can find that
    the video's words make a speaker sound more certain (STRONGER);
  - coherence (the takeaway's point).
  Up to WRITES = 2 full writes.
- Writers are two Heimdall models (deepseek, qwen; vendor heimdall); judges are never the writer's vendor (law L-x).
- RULING 65 (12:52): when only the caption or the title fails, ONE write of that line alone (write_line, a new prompt
  told the refused sentence and why; the other lines kept as gated, their verdicts merged by merge_fid). Then: a
  caption gets a FIXED caption, a title is held.
- RULING 3: when the takeaway fails both writes and the clips need no bridge, the no-voice fallback may ship the clips
  with no VO line (adding one clip to land the seconds).

The orders being implemented:
- RULING 66 AMENDED (orchestrator 17:02): "a candidate whose clips pass and whose LINE failed gets, at once, up to TWO
  fresh writes of the failed line only (the writer told the refused sentence and why; the second attempt on the other
  writer model), the passing lines kept as gated ... If the takeaway still fails both, L-y's no-voice fallback applies
  if the clips meet its seconds, else rest."
- 17:20:
  - "YES, the second attempt applies to a failed title as well (two fresh writes of the failed line alone, the second
    on the other writer model), then hold as ruling 65 says."
  - "NO CHANGE to either judge." The fix is on the writer's side: "tell the takeaway writer, in its prompt, the two
    patterns that were refused today (a forecast or permanence claim stated as fact; a superlative that upgrades a
    speaker's hedged view) and that the line may characterise what was SAID, not what WILL happen."

The change (pipeline/package.py; tests in tests/package/test_medley.py):
1. The write loop is `while True`. After the full writes are spent, if the LAST write failed on the takeaway ALONE, up
   to LINE_ONLY_WRITES = 2 writes of the takeaway alone follow (write_line slot "takeaway"):
   - each is told every refused takeaway of this line-up with why (deduplicated) plus TAKEAWAY_SAID;
   - the second avoids the first's model (avoid_model = the first one's backend name);
   - the other lines (title, caption, bridge) are kept from the last write;
   - the kept lines' verdicts are kept via merge_fid when that write reached the paid gates (takeaway_alone_gates:
     the verdict on the takeaway alone, plus context integrity on the whole package); otherwise every line is judged
     (paid_gates);
   - cheap checks, coherence, the inventory and package_pin.gate_problems all run as before;
   - ruling 3's no-voice fallback runs after the loop, so after these writes.
2. takeaway_refusal(fields, violations, cx) decides "the takeaway alone". Its own failures are:
   - a violation on its slot;
   - RUNTIME or R4 on "-" (with the other lines kept, only its length moves them);
   - STRONGER / NOT_ENTAILED whose step-C cited words (raising_words / added_by) are a run of >= 2 canonical tokens
     of the takeaway and of no other line, and only when the violation's detail shows the words path.
   Anything else (another line, a clip's own failure, POLARITY, "stronger certainty: uncertain", LY_SHAPE, RECENCY)
   makes it not alone. No takeaway-alone write follows a write whose caption / title went through ruling 65's rewrite
   (last_rw65), and none when no takeaway length lands the seconds (takeaway_budget None).
3. Ruling 65's rewrite_alone, for a TITLE only:
   - up to LINE_ONLY_WRITES writes;
   - the second avoids the first's model and is told the first rewrite's refusal (rule "AGAIN");
   - then held as before, with the count in the why.
   The caption keeps one write, then the fixed caption. Ruling 65's prompts are unchanged byte for byte (the takeaway
   prompt pieces are added only for slot "takeaway").
4. TAKEAWAY_SAID, the 17:20 sentence with today's two refused examples, is in the full write's prompt (WRITE_LY) and
   in the takeaway-alone prompt.
5. Records: each takeaway-alone attempt carries "takeaway_alone" {attempt, refused}; out["takeaways"] numbers it 3, 4;
   the line-up's why counts the takeaway-alone writes; the title's rewrite record carries "tries".
6. Tests: the takeaway alone passing on attempt 1; attempt 2 on the other model; both failing (then no-voice is tried,
   else rest); another line failing (no takeaway-alone write); no-voice after the takeaway-alone writes; which failures
   are the takeaway's own; the title's second write on the other model then held (and the caption unchanged); both
   prompts carry TAKEAWAY_SAID. Mutation runs: each new behaviour removed fails its test. All 14 suites OK (medley 149).

Check, against the diff:
- that the loop always terminates (every iteration spends a write or a takeaway-alone attempt, or breaks) and never
  writes more than WRITES full writes + 2 takeaway-alone writes;
- that the takeaway-alone path can never seal a line that did not pass every gate (no gate accepts more than before:
  law: never change what a check accepts to make something pass);
- that the kept lines' verdicts are only merged when that write's lines were judged, and that merge_fid's precondition
  (the kept write's violations only on the takeaway) holds whenever it is used;
- the attribution in takeaway_refusal (false "alone" would rewrite the wrong line; false "not alone" only loses a try);
- that ruling 65's caption path and prompts are unchanged, and that the title gets exactly two writes;
- that the writer, not the judges, is what changed (no judge prompt or threshold touched).

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

