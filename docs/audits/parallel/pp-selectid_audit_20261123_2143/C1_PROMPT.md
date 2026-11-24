# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261123_2143
# Branch: pp-selectid
# Generated: 2026-11-23 21:43 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261123_2143/C1_STEP.diff (302 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f4cf9694b..d2407a768 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -56,6 +56,7 @@ import json
   6 |  import math
   7 |  import os
   8 |  import re
   9 | +import types
  10 |  import threading
  11 |  import time
  12 |  from concurrent.futures import ThreadPoolExecutor
  13 | @@ -139,7 +140,8 @@ def kind_sentences(pairs, who):
  14 |          else:
  15 |              chans = ", ".join(str((who or {}).get(lb) or "its channel") for lb in lbs)
  16 |              out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
  17 | -                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]}.")
  18 | +                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY.get(c) or STEP_A_SOFT.get(c) or EDGE_WORDS.get(c) or c}.")
  19 | +            #   audit 20261123_2108 C1 (qwen P1): never a KeyError, even for a code no table words for several clips
  20 |      return out
  21 |  
  22 |  
  23 | @@ -2776,6 +2778,69 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  24 |                     type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
  25 |  
  26 |  
  27 | +FALLBACK_FLAG = 'A line of ours is the plain fallback: "{line}"'   # RULING 156 (2): one flag kind, the line verbatim
  28 | +FALLBACK_CLOSING = ("{subject}, in their own words.",                       # graded lengths, the shortest that
  29 | +                    "{subject}, in the words of {names}.",                   # lands takeaway_budget is the line
  30 | +                    "{subject}, in the words of {names}, in their own clips.",
  31 | +                    "That was {subject}, in the words of {names}, in the clips you just heard.",
  32 | +                    "That was {subject}, in the words of {names}, each in their own clip, as you just heard.")
  33 | +
  34 | +
  35 | +def fallback_subject(segs, chans):
  36 | +    """RULING 156 (2): the story's subject in the clips' own words: 'Bitcoin', or '<Name> and Bitcoin' where <Name> is
  37 | +    the run of capitalised words (its first never opening a sentence; no channel's word, 'I' or 'Bitcoin' in it) the most
  38 | +    of the line-up's clips say, at least two of them, in their spelling ('Michael Saylor'); ties: the earliest said."""
  39 | +    import collections
  40 | +    skip = {"i", "bitcoin"} | {w.lower() for c in chans for w in re.findall(r"[A-Za-z]+", str(c))}
  41 | +    count, first = collections.Counter(), {}
  42 | +    for i, m in enumerate(segs):
  43 | +        t, names = str(m.get("text") or ""), set()
  44 | +        for mm in re.finditer(r"[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*", t):
  45 | +            run, before = mm.group(0), t[:mm.start()].rstrip()
  46 | +            if not before or before[-1] in ".!?" or any(w.lower() in skip for w in run.split()):
  47 | +                continue
  48 | +            names.add(run)
  49 | +            first.setdefault(run, (i, mm.start()))
  50 | +        for w in names:
  51 | +            count[w] += 1
  52 | +    best = sorted((w for w, n in count.items() if n >= 2), key=lambda w: (-count[w], first[w]))
  53 | +    return f"{best[0]} and Bitcoin" if best else "Bitcoin"
  54 | +
  55 | +
  56 | +def fallback_fields(angle, segs, join=None, other=()):
  57 | +    """RULING 156 (2) (orchestrator 21:34 ET Nov 23): THE SAFE FALLBACK LINES, built by code from fixed templates that
  58 | +    state no fact of their own (only the subject in the clips' own words and the channels' names), gated as any write:
  59 | +    the closing line (the shortest FALLBACK_CLOSING variant inside takeaway_budget), a title ('<Subject>: <names>', or
  60 | +    '<Subject>, in their words' past ruling 6's 8 words), a caption ('<Subject>, in the words of <names>.') and, only
  61 | +    where a join needs one, a bridge ('Next, <channel>.'). -> write_takeaway's fields, or None when no closing variant
  62 | +    lands the budget."""
  63 | +    chans = []
  64 | +    for m in segs:
  65 | +        c = m.get("channel_name") or m.get("channel_id")
  66 | +        if c and c not in chans:
  67 | +            chans.append(c)
  68 | +    names = chans[0] if len(chans) == 1 else ", ".join(chans[:-1]) + " and " + chans[-1]
  69 | +    subject, ids = fallback_subject(segs, chans), [m["moment_id"] for m in segs]
  70 | +    bridge = None
  71 | +    if join is not None:
  72 | +        nxt = segs[join[0] + 1]
  73 | +        bridge = {"text": f"Next, {nxt.get('channel_name') or 'the next channel'}.", "cites": [nxt["moment_id"]],
  74 | +                  "why": "the plain fallback bridge (ruling 156 (2))"}
  75 | +    budget = takeaway_budget(sum(m["duration_s"] for m in segs), list(other) + ([bridge["text"]] if bridge else []))
  76 | +    take = next((t for t in (f.format(subject=subject, names=names) for f in FALLBACK_CLOSING)
  77 | +                 if budget is not None and budget[0] <= len(t.split()) <= budget[1]), None)
  78 | +    if take is None:
  79 | +        return None
  80 | +    title = f"{subject}: {names}"
  81 | +    if len(title.split()) > HS.TITLE_MAX_WORDS or len(title) > LINE_CHARS["title"]:
  82 | +        title = f"{subject}, in their words"
  83 | +    return {"takeaway": {"text": take, "cites": ids}, "title": {"text": title, "cites": ids},
  84 | +            "caption": {"text": f"{subject}, in the words of {names}.".lower(), "cites": ids},   # house style:
  85 | +            "bridge": bridge,                                                          # a caption is all lowercase
  86 | +            "bridge_after": join[0] if bridge else None, "type": "moments", "angle": angle["angle"], "style": "medley",
  87 | +            "takeaway_budget": list(budget), "fallback": True}
  88 | +
  89 | +
  90 |  WRITE_LINE = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  91 |  THE ANGLE (the point this video makes): "{angle}"
  92 |  The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
  93 | @@ -2798,7 +2863,8 @@ LINE_WHY = {"AGAIN": "your first rewrite of it was refused too",   # 17:20: a ti
  94 |              "STYLE": "it breaks the house style"}
  95 |  LINE_LIMIT = {"caption": "at most 220 characters", "title": "at most 70 characters"}
  96 |  LINE_CHARS = {"caption": 220, "title": 70, "takeaway": 240}
  97 | -LINE_ONLY_WRITES = 2                  # RULING 66 amended (17:02 Nov 13): "up to TWO fresh writes of the failed line only"
  98 | +LINE_ONLY_WRITES = 3                  # RULING 156 (1) (21:34 ET Nov 23): up to 4 writes a line per angle (the write and
  99 | +#   3 of the line alone, each told its refusal and the words; the other model after a failure); RULING 66 amended had 2
 100 |  TAKEAWAY_LIMIT = ("{lo}-{hi} words, one or two sentences: host commentary attributed to nobody that states no fact, no "
 101 |                    "speaker's view, no advice or prediction and no accusation, and that no viewer could take for a "
 102 |                    "speaker's words")
 103 | @@ -4283,11 +4349,14 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 104 |                  v_lost, v_redo, v_novoice, v_plan, val = [], False, None, None, None   # RULING 91 (medley half):
 105 |                  #   the value verdicts the takeaway lost, its ONE rewrite still due, the loss that sends the line-up to
 106 |                  #   the no-voice shape with the plan decided for it (nv_order), and the verdict of the takeaway now written
 107 | +                fb_state, fb_text = None, None           # RULING 156 (2): the plain lines, once, after every write
 108 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 109 |                      lone = w_used >= writes or v_redo      # takeaway alone failed, the takeaway ALONE, up to twice
 110 |                      if lone and not v_redo and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None
 111 |                                                      and not last_rw65):
 112 | -                        break
 113 | +                        if not (soft and fb_state is None and w_used >= writes):
 114 | +                            break
 115 | +                        fb_state = "due"                   # never-empty pass: every write failed: the template lines
 116 |                      if over_budget(ai):
 117 |                          break
 118 |                      w_over = package_over(line)
 119 | @@ -4295,7 +4364,18 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 120 |                          rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 121 |                          break
 122 |                      redo91 = False
 123 | -                    if lone:                               # the other lines kept as gated; told each refusal and why
 124 | +                    if fb_state == "due":                  # RULING 156 (2): built by code, gated as any full write
 125 | +                        fields, fb_state = fallback_fields(angle, segs, join, written), "used"
 126 | +                        if fields is None:
 127 | +                            rec["fallback_line"] = {"why_not": "no closing template lands the takeaway's word budget"}
 128 | +                            break
 129 | +                        fb_text = fields["takeaway"]["text"]
 130 | +                        rec["fallback_line"] = {"text": fb_text, "title": fields["title"]["text"]}
 131 | +                        log(f"    RULING 156 (2): every write failed: the plain lines built by code, gated as any: "
 132 | +                            f"{fb_text!r} | title {fields['title']['text']!r}")
 133 | +                        wr = types.SimpleNamespace(vendor="code", family="code", backend="code:fallback (ruling 156)")
 134 | +                        lone = False
 135 | +                    elif lone:                             # the other lines kept as gated; told each refusal and why
 136 |                          alone_n += 1
 137 |                          redo91, v_redo = v_redo, False     # ruling 91's one rewrite is spent here, whatever comes of it
 138 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 139 | @@ -4533,6 +4613,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 140 |                                              value=val,                       # ruling 91: the takeaway earned its place
 141 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 142 |                                              soft=soft,
 143 | +                                            fallback_line=fb_text if fb_text is not None and
 144 | +                                            fields["takeaway"]["text"] == fb_text else None,   # RULING 156 (2)
 145 |                                              chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},
 146 |                                              who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 147 |                                                              for sg in pk["segments"]},
 148 | @@ -4670,7 +4752,7 @@ def _spent(spend):
 149 |  
 150 |  
 151 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 152 | -              chan_of=None,
 153 | +              chan_of=None, fallback_line=None,
 154 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 155 |                seg_flags=None, mids=None):
 156 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 157 | @@ -4771,6 +4853,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 158 |                                 **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
 159 |                                    if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
 160 |             if hook is not None else {}),                                                                      # (2)
 161 | +        **({"fallback_line": {"status": "FLAGGED", "by": "package.fallback_fields (ruling 156 (2)): the plain lines "
 162 | +                                                         "built by code from fixed templates that state no fact, gated "
 163 | +                                                         "as any line", "replayed": False, "n": 1,
 164 | +                              "flags": [FALLBACK_FLAG.format(line=fallback_line)]}}
 165 | +           if soft and fallback_line else {}),
 166 |          **({"sponsor": {"status": "FLAGGED", "by": "moments.exclusion_verdict (ruling 146 (3)): a sponsor mention in "
 167 |                                                     "the sentence before the clip only; its own words judged by the "
 168 |                                                     "exclusion model", "replayed": False, "n": len(exc), "flags": [
 169 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 170 | index dd8f4bd10..272c8b5ef 100644
 171 | --- a/pipeline/package_pin.py
 172 | +++ b/pipeline/package_pin.py
 173 | @@ -49,6 +49,7 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 174 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 175 |                          "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
 176 |                          #   91), a measured one; fidelity, length and the banned words stay HARD
 177 | +                        "fallback_line",                   # RULING 156 (2): our plain lines built by code, gated
 178 |                          "sponsor",                         # RULING 146 (3): a sponsor mention in the sentence before
 179 |                          #   a clip only, the clip kept by the exclusion model (its ad_read risk stays HARD)
 180 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 181 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 182 | index f965429b5..30e5a4aaa 100644
 183 | --- a/tests/package/test_medley.py
 184 | +++ b/tests/package/test_medley.py
 185 | @@ -2860,7 +2860,7 @@ class TestRuling66Amended(unittest.TestCase):
 186 |                                           alone_ok=(False, False))
 187 |          self.assertIsNone(out["package"])
 188 |          self.assertEqual(len(seen), 2)                                         # up to TWO, never more
 189 | -        self.assertIn("2 write(s) and 2 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])
 190 | +        self.assertIn("2 write(s) and 3 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])   # 156 (1)
 191 |          self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then rest
 192 |  
 193 |      def test_a_failure_on_another_line_gets_no_takeaway_alone_write(self):
 194 | @@ -2879,7 +2879,7 @@ class TestRuling66Amended(unittest.TestCase):
 195 |                                                    {"takeaway": {"text": "In the end nobody bends them.", "cites": []}}],
 196 |                                               ms=ms, takeaways=bad,
 197 |                                               medleys=[(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)])
 198 | -        self.assertEqual(len(avoid["takeaway"]), 2)                            # the takeaway alone, twice (STYLE)
 199 | +        self.assertEqual(len(avoid["takeaway"]), 3)                            # the takeaway alone, 3 times (156 (1))
 200 |          self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")   # then ruling 3
 201 |          self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])
 202 |  
 203 | @@ -2899,7 +2899,7 @@ class TestRuling66Amended(unittest.TestCase):
 204 |          rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, False))
 205 |          self.assertIsNone(out["package"])                                      # then held (ruling 65 c)
 206 |          self.assertEqual(len(seen), 2)                                          # two writes of the title, no more
 207 | -        self.assertIn("the title failed alone 3 times", out["tried"][0]["why"])
 208 | +        self.assertIn("the title failed alone 4 times", out["tried"][0]["why"])   # RULING 156 (1): 4 writes a line
 209 |          self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
 210 |          rig, out, seen, avoid = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
 211 |                                                                                        "cites": []}}],
 212 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 213 | index 2c509168e..e9fede70c 100644
 214 | --- a/tests/package/test_ruling_137.py
 215 | +++ b/tests/package/test_ruling_137.py
 216 | @@ -259,6 +259,85 @@ class TestRuling155FlagKinds(unittest.TestCase):
 217 |          self.assertEqual(PK.seg_marks(segs), 4)        # REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, STAND_ALONE
 218 |  
 219 |  
 220 | +FAILING = 2
 221 | +
 222 | +
 223 | +class TestRuling156FallbackLines(unittest.TestCase):
 224 | +    """RULING 156 (2) (orchestrator 21:34 ET Nov 23): when every write fails, the never-empty pass gates ONE set of plain
 225 | +    lines built by code from fixed templates that state no fact (the subject in the clips' own words and the channels'
 226 | +    names); a package on them carries the one flag 'A line of ours is the plain fallback: "<line>"'. The clean pass never
 227 | +    uses them; fidelity stays HARD (they are gated as any write)."""
 228 | +    def segs(self, total=39.0):
 229 | +        from test_moments import pm
 230 | +        ms = [pm("h", "Natalie Brunell", total / 3), pm("x", "Strategy", total / 3), pm("y", "Yahoo Finance", total / 3)]
 231 | +        for m, t in zip(ms, ("Analysts say Michael Saylor will keep buying Bitcoin.",
 232 | +                             "We sold credit, and Michael Saylor said we buy more Bitcoin.",
 233 | +                             "This guy, Michael Saylor, is buying again.")):
 234 | +            m["text"] = t
 235 | +        return ms
 236 | +
 237 | +    def test_the_templates_state_no_fact_fit_the_budget_and_pass_house_style(self):
 238 | +        import house_style as HS
 239 | +        for total in (31.5, 34.5, 39.0, 45.0):
 240 | +            with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):           # the never-empty pass's budget
 241 | +                f = PK.fallback_fields({"angle": "a"}, self.segs(total))
 242 | +            lo, hi = f["takeaway_budget"]
 243 | +            words = f["takeaway"]["text"].split()
 244 | +            self.assertTrue(lo <= len(words) <= hi, (total, f["takeaway"]["text"]))
 245 | +            self.assertIn(f["takeaway"]["text"], [v.format(subject="Michael Saylor and Bitcoin",
 246 | +                                                           names="Natalie Brunell, Strategy and Yahoo Finance")
 247 | +                                                  for v in PK.FALLBACK_CLOSING])
 248 | +            self.assertEqual(HS.lint_lines([{"slot": k, "text": f[k]["text"]} for k in ("takeaway", "title", "caption")]),
 249 | +                             [], total)
 250 | +            self.assertEqual((f["title"]["text"], f["caption"]["text"]), (
 251 | +                "Michael Saylor and Bitcoin, in their words",
 252 | +                "michael saylor and bitcoin, in the words of natalie brunell, strategy and yahoo finance."))
 253 | +        one = self.segs()
 254 | +        one[1]["text"] = "We sold credit."
 255 | +        self.assertEqual(PK.fallback_subject(one, ["Natalie Brunell", "Strategy", "Yahoo Finance"]),
 256 | +                         "Michael Saylor and Bitcoin")                 # still two clips say it
 257 | +        one[2]["text"] = "This guy is buying again."
 258 | +        self.assertEqual(PK.fallback_subject(one, ["Natalie Brunell"]), "Bitcoin")   # one clip only: Bitcoin alone
 259 | +
 260 | +    def test_a_join_that_needs_a_bridge_gets_the_plain_one(self):
 261 | +        with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):
 262 | +            f = PK.fallback_fields({"angle": "a"}, self.segs(), join=(1, "x"))
 263 | +        self.assertEqual((f["bridge"]["text"], f["bridge_after"]), ("Next, Yahoo Finance.", 1))
 264 | +
 265 | +    def run_rig(self, never_empty, failing=FAILING, a_fail=True):
 266 | +        import test_medley as TM
 267 | +        from test_moments import pm
 268 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 269 | +        bad = TM.TestRuling66Amended().failing()
 270 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2,
 271 | +                   fids=[dict(bad) for _ in range(failing)],         # every model write fails fidelity (COMMENTARY)
 272 | +                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"]} if a_fail else None)   # the clean pass stops at 2
 273 | +        #   channels, before any
 274 | +        #   write; the never-empty pass takes y back, flagged (stage 1), and writes
 275 | +        if never_empty:
 276 | +            r.build_kw = {"never_empty": True}
 277 | +        return r, r.run()
 278 | +
 279 | +    def test_every_write_failing_seals_on_the_plain_lines_flagged(self):
 280 | +        r, out = self.run_rig(True)
 281 | +        pk = out["package"]
 282 | +        self.assertIsNotNone(pk, out.get("why_none"))
 283 | +        take = next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway")
 284 | +        self.assertEqual(pk["gates"]["fallback_line"]["flags"], [PK.FALLBACK_FLAG.format(line=take)])
 285 | +        self.assertTrue(any(take == v.format(subject="Bitcoin", names="A, B and C") for v in PK.FALLBACK_CLOSING))
 286 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 287 | +
 288 | +    def test_the_clean_pass_never_uses_them(self):
 289 | +        r, out = self.run_rig(False, a_fail=False)                   # the clean pass reaches the writes, all fail
 290 | +        self.assertIsNone(out["package"])
 291 | +        self.assertNotIn("fallback_line", out["tried"][0])
 292 | +
 293 | +    def test_fidelity_stays_hard_for_the_plain_lines(self):
 294 | +        r, out = self.run_rig(True, failing=FAILING + 1)             # the plain lines' own verdict fails too
 295 | +        self.assertIsNone(out["package"])
 296 | +        self.assertIn("fallback_line", ((out.get("never_empty") or {}).get("soft_record") or {})["tried"][0])
 297 | +
 298 | +
 299 |  class TestStage2bHookBar(unittest.TestCase):
 300 |      """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 301 |      own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 302 | 
```

---

pp-selectid: RULING 156 (orchestrator 21:34 ET Nov 23): "Our writing must never be the reason PBX gets no video."
(1) each line of ours gets up to 4 writes per angle, every rewrite told the gate's refusal and the words; (2) THE SAFE
FALLBACK LINE: when the writes fail, a PLAIN line built by code from a fixed template that states no fact of its own
(only the story's subject in the clips' own words and the channels' names), gated as any line, the package flagged
'A line of ours is the plain fallback: "<line>"'; (3) fidelity stays HARD.
THE CHANGE (pipeline/package.py, pipeline/package_pin.py; tests in tests/package/test_ruling_137.py, test_medley.py):
- LINE_ONLY_WRITES 2 -> 3 (the write and 3 of the line alone = 4; the alone writes are unchanged code: told the refused
  sentence and why, the other model after a failure).
- fallback_subject / fallback_fields (package.py:2810): FALLBACK_CLOSING's 5 graded variants, the shortest inside the
  unchanged takeaway_budget; title '<Subject>: <names>' or '<Subject>, in their words' past 8 words; caption lowercase
  (house style); a bridge 'Next, <channel>.' only for a join that needs one; cites = the line-up's ids.
- The write loop (package.py:4367): ONLY in the never-empty pass (soft), once, when every write is spent
  (w_used >= writes and no takeaway-alone write left): fields = fallback_fields(...), a writer namespace 'code' (no
  judge's vendor), lone = False, so the plain lines go through the SAME full paid gates as a model write
  (paid_gates, package.py:3237, unchanged: fidelity, context) and every later gate (value, coherence, the lock).
- inventory: a FLAGGED 'fallback_line' row (its sentence quotes the closing line) when the sealed takeaway is the
  fallback's text; package_pin.SOFT_GATES += 'fallback_line' (gate_problems, package_pin.py:463, accepts a FLAGGED row
  only on a soft gate; the integrator's pin check reads this file live).
Also in this diff: one line from ruling 155's audit C1 (kind_sentences never raises KeyError).
TESTS: the templates fit the budget at 31.5-45 s and pass house style; the subject rule; the plain bridge; every write
failing seals on the plain lines with the flag and gate_problems none; the clean pass never uses them; the plain lines
failing fidelity refuse (HARD). Mutations 7 of 7 killed.
PLEASE CHECK: (1) can the clean pass, or a line-up whose failure is a CLIP's (not our line's), reach a sealed package
through the fallback without every gate? (2) do the templates ever state a fact or a claim? (3) can the fallback loop
run more than once or never end? (4) is the flag on the package exactly when the sealed closing line is the fallback?



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
