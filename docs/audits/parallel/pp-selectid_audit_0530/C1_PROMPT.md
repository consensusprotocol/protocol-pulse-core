# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0530
# Branch: pp-selectid
# Generated: 2026-11-13 05:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0530/C1_STEP.diff (440 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 2b2f07f1..069436e6 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -79,6 +79,7 @@ SEARCH_USD_REPORTED = 3.00         # ruling 41: a build may spend $3 (vendor-rep
   6 |  SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE delivered (its own line-up). The estimate
   7 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   8 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   9 | +TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
  10 |  SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
  11 |                                     # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
  12 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  13 | @@ -299,7 +300,9 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  14 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
  15 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  16 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  17 | -                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
  18 | +                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  19 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  20 | +                           if m.get("trimmed_leading") else {})}                      # ruling 33 part 2, sealed
  21 |                         for lb, m in zip(labels(len(segs)), segs)],
  22 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  23 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  24 | @@ -579,7 +582,9 @@ def stand_alone_check(segs):
  25 |      edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  26 |             "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  27 |                       for i, m in enumerate(segs[1:], 1)]}
  28 | -    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  29 | +    r = SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
  30 | +    r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs) if m.get("trimmed_leading")]   # ruling 33
  31 | +    return r                           # part 2: the render's clip scorer judges a trimmed segment on GPU0 (item 42)
  32 |  
  33 |  
  34 |  def ad_read_out(ms, sources):
  35 | @@ -601,6 +606,38 @@ def ad_read_out(ms, sources):
  36 |      return out
  37 |  
  38 |  
  39 | +def trim_variant(m, sources):
  40 | +    """RULING 33 PART 2 (the render merged it at 11e361cc; the orchestrator's 04:58 item 42, "use it now"). A moment
  41 | +    whose first word is ONE of TRIM_WORDS, left out by the render's STAND_ALONE opener rule, may be cut one word in.
  42 | +    The variant's text, start and words begin at the next word of its word record (start/end bound the KEPT words),
  43 | +    and it carries trimmed_leading (the word as spoken) and untrimmed_start (the trimmed word's start). It must take a
  44 | +    place under the render's STAND_ALONE as trimmed (no_role_on_screen and no_topic both None on the trimmed text).
  45 | +    Then it is judged like any moment: step A on the trimmed span (ruling 33 c), L-v 2 with the trimmed word heard right
  46 | +    before the clip (transcript_truth.edges), and the acoustic onset rule on the trimmed cut (ruling 33 a, build()).
  47 | +    The clip scorer's verdict (ruling 33 b) is the render's, on GPU0: pending at the render (stand_alone_check). -> the
  48 | +    variant, or None."""
  49 | +    import canon
  50 | +    try:
  51 | +        src = src_of(m, sources)
  52 | +        w0, w1 = m["words"]
  53 | +        toks = src.tokens
  54 | +        word, nxt = toks[w0].get("word") or "", toks[w0 + 1]
  55 | +    except (KeyError, IndexError, TypeError, ValueError):
  56 | +        return None
  57 | +    if w1 <= w0 or canon.canon_tokens(word)[:1] not in ([t] for t in TRIM_WORDS):
  58 | +        return None
  59 | +    a = nxt.get("start")
  60 | +    if not isinstance(a, (int, float)) or isinstance(a, bool) or not float(m["start"]) <= float(a) < float(m["end"]):
  61 | +        return None
  62 | +    v = dict(m, moment_id=f"{m['moment_id']}~trim", text=E.spoken(toks[w0 + 1:w1 + 1]), start=float(a),
  63 | +             duration_s=round(float(m["end"]) - float(a), 2), words=[w0 + 1, w1],
  64 | +             trimmed_leading=word.strip().strip(".,!?;:\"'()\u201c\u201d\u2014\u2026"),
  65 | +             untrimmed_start=float(m["start"]), trimmed_from=m["moment_id"])
  66 | +    if no_role_on_screen(v) or no_topic(v):
  67 | +        return None
  68 | +    return v
  69 | +
  70 | +
  71 |  def no_topic(m):
  72 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  73 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  74 | @@ -1070,7 +1107,7 @@ def truth_for(router, m, work_dir, cache):
  75 |          import transcript_truth as TT
  76 |          try:
  77 |              cache[m["moment_id"]] = TT.verify_segment(router, m["video_id"], float(m["start"]), float(m["end"]),
  78 | -                                                      m["text"], work_dir)
  79 | +                                                      m["text"], work_dir, trimmed=m.get("trimmed_leading"))
  80 |          except Exception as e:                         # not measured: never a pass (law L-m)
  81 |              cache[m["moment_id"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
  82 |      return cache[m["moment_id"]]
  83 | @@ -1149,7 +1186,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  84 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  85 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  86 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  87 | -    ms = [m for m in ms if m["moment_id"] not in no_role]
  88 | +    trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
  89 | +    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
  90 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  91 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  92 |      wv, wf = _writers(router)
  93 | @@ -1157,7 +1195,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  94 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  95 |      levels = current_levels(sources.values(), ctx)
  96 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  97 | -           "no_role": no_role, "ad_read": ad_read,
  98 | +           "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
  99 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 100 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 101 |             "package": None}
 102 | @@ -1191,6 +1229,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 103 |      out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 104 |                                        ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 105 |                                        str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 106 | +    trim_cut = {mid: out["prescreen"]["hook_onset"][mid] for mid, m in cleared.items()     # ruling 33 (a): the
 107 | +                if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}    # acoustic onset rule on the
 108 | +    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}                 # trimmed cut, any place
 109 | +    out["prescreen"]["trim_cut"] = trim_cut
 110 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 111 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
 112 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 113 | @@ -1660,6 +1702,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 114 |                                      "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 115 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 116 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 117 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 118 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 119 | +                                scorer_pending=stand.get("scorer_pending") or [])}
 120 |             if stand is not None else {}),
 121 |      }
 122 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 123 | index 101b0e28..b9acb900 100644
 124 | --- a/pipeline/package_pin.py
 125 | +++ b/pipeline/package_pin.py
 126 | @@ -66,7 +66,10 @@ def recency_problems(segments):
 127 |  
 128 |  
 129 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
 130 | -                "speaker")                                 # the 00:05 ET Nov 13 order, item 3
 131 | +                "speaker",                                 # the 00:05 ET Nov 13 order, item 3
 132 | +                "trimmed_leading", "untrimmed_start")      # ruling 33 part 2 (render merged 11e361cc): only when a word
 133 | +                                                           # is trimmed, so every other pin seals as before
 134 | +TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
 135 |  
 136 |  
 137 |  def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 138 | @@ -93,6 +96,28 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
 139 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 140 |  
 141 |  
 142 | +def trim_problems(segments):
 143 | +    """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
 144 | +    refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
 145 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start."""
 146 | +    import canon
 147 | +    out = []
 148 | +    for i, s in enumerate(segments):
 149 | +        has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
 150 | +        if not has_w and not has_s:
 151 | +            continue
 152 | +        if has_w != has_s:
 153 | +            out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 154 | +            continue
 155 | +        w, u = s["trimmed_leading"], s["untrimmed_start"]
 156 | +        tok = canon.canon_tokens(w)[:1] if isinstance(w, str) else []
 157 | +        if tok not in ([t] for t in TRIM_WORDS):
 158 | +            out.append(f"segment {i}: trimmed_leading {w!r} is not one of {'/'.join(TRIM_WORDS)}")
 159 | +        if isinstance(u, bool) or not isinstance(u, (int, float)) or not 0 <= float(u) < float(s["start"]):
 160 | +            out.append(f"segment {i}: untrimmed_start {u!r} must be a number with 0 <= it < start {s['start']!r}")
 161 | +    return out
 162 | +
 163 | +
 164 |  def screen_problems(pk):
 165 |      """[why] for a moments medley that does not carry the screen its line-up was judged with (ruling 34). The render
 166 |      reads moments_package.btc_screen and, without it, applies the stricter every-segment rule, so a pin judged with
 167 | @@ -190,7 +215,7 @@ def to_pin(pk, run_name):
 168 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 169 |                                                                       for x in line_problems(pk)] + \
 170 |          recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
 171 | -        screen_problems(pk)
 172 | +        screen_problems(pk) + trim_problems(pk.get("segments") or [])
 173 |      if problems:
 174 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 175 |      segs = []
 176 | @@ -200,6 +225,7 @@ def to_pin(pk, run_name):
 177 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 178 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 179 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 180 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start") if k in s},   # ruling 33 part 2
 181 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 182 |      edl_vo = {"intro": pk["vo"]["intro"],
 183 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 184 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 185 | index fadf036c..76bb890e 100644
 186 | --- a/pipeline/stand_alone.py
 187 | +++ b/pipeline/stand_alone.py
 188 | @@ -112,15 +112,32 @@ def topical_screen(kind, text, prev_text, screen):
 189 |      return False, f"does not pass the miner's about-Bitcoin screen and does not complete the previous claim"
 190 |  
 191 |  
 192 | +def trimmed_word(seg):
 193 | +    """The leading word a segment's lock trims (ruling 33 part 2: selection_lock.trimmed_leading), else None."""
 194 | +    t = (seg.get("selection_lock") or {}).get("trimmed_leading")
 195 | +    return str(t.get("word") or "?") if isinstance(t, dict) else None
 196 | +
 197 | +
 198 | +def trimmed_opener(word, score, fault):
 199 | +    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a segment locked with ONE leading word trimmed passes only
 200 | +    when the clip scorer affirms the TRIMMED text stands alone at the unchanged threshold, whatever its first word."""
 201 | +    if score is None:
 202 | +        return False, f"{word!r} trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)"
 203 | +    if score >= CLIP_MIN_SCORE and fault != "starts_mid_thought":
 204 | +        return True, f"{word!r} trimmed; the clip scorer affirms the trimmed text stands alone ({score}, fault {fault})"
 205 | +    return False, f"{word!r} trimmed; the clip scorer does not affirm the trimmed text stands alone ({score}, fault {fault})"
 206 | +
 207 | +
 208 |  def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 209 |      """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
 210 | -    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed.
 211 | +    clips opening on a conjunction / reply fragment (the clip scorer) and for every segment whose lock trims a leading
 212 | +    word (ruling 33 part 2, the hook included); without it they fail closed.
 213 |      screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
 214 |      and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
 215 |      speaker's own words. screen None: every segment names the subject, as before (the story path)."""
 216 |      segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
 217 | -    need = [(label, s) for label, kind, s in segs if kind == "clip" and _words(s.get("text"))[:1]
 218 | -            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)]
 219 | +    need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
 220 | +            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))]
 221 |      scores, rate_error = {}, None
 222 |      if need and rate is not None:
 223 |          try:
 224 | @@ -133,6 +150,8 @@ def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None):
 225 |          sc = scores.get(label)
 226 |          score, fault = (sc[0], sc[2]) if sc else (None, None)
 227 |          o_ok, o_why = opener(kind, s.get("text"), score, fault)
 228 | +        if o_ok and trimmed_word(s):                                   # ruling 33 part 2
 229 | +            o_ok, o_why = trimmed_opener(trimmed_word(s), score, fault)
 230 |          t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
 231 |              topical(kind, s.get("text"), prev, subject)
 232 |          rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
 233 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
 234 | index 47f8b401..705d87f1 100644
 235 | --- a/pipeline/transcript_truth.py
 236 | +++ b/pipeline/transcript_truth.py
 237 | @@ -157,7 +157,7 @@ def _canon_to(ws, i):
 238 |      return c[-1] if c else None
 239 |  
 240 |  
 241 | -def edges(second, wav_start, start, end, text):
 242 | +def edges(second, wav_start, start, end, text, trimmed=None):
 243 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
 244 |      the segment's edges, from its word timing on the SOURCE audio. The clip's first / last word is found by its first
 245 |      four letters OR by the L-v 2 canonicaliser on a short run of the recogniser's words (ruling 39: 'sixty-eight
 246 | @@ -166,7 +166,9 @@ def edges(second, wav_start, start, end, text):
 247 |      clip's opening word (a measured pause), or the window reaches the FILE HEAD and holds no word before the clip (the
 248 |      clip opens on the file's first spoken word). OUT: the recogniser's word at the clip's last word (within 0.8 s) ends
 249 |      in terminal punctuation, and the recogniser heard a next word (it did not stop at the window's edge). Store or
 250 | -    caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
 251 | +    caption punctuation is never evidence. trimmed (ruling 33 part 2: ONE leading word trimmed at the cut): the word
 252 | +    the recogniser hears right before the clip's first kept word must be that word, and the IN rule reads before IT,
 253 | +    where the sentence opens. -> {"cuttable", "in", "out"}."""
 254 |      # the recogniser's words in its own (time) order: all 99 recorded transcriptions are time-ordered (audit 0338 C1)
 255 |      ws = [w for w in second.get("words") or [] if w.get("start") is not None]
 256 |      toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
 257 | @@ -187,7 +189,11 @@ def edges(second, wav_start, start, end, text):
 258 |      if ci:                                      # the occurrence NEAREST the clip's start, never an earlier one of the
 259 |          i = min(ci, key=lambda k: abs(float(ws[k]["start"]) - t_in))    # same word (audit 0338: grok C2, glm C1 P2-2)
 260 |          j, repair = i - 1, None
 261 | -        if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
 262 | +        tw = canon.canon_tokens(trimmed or "")[:1]
 263 | +        heard = (canon.canon_tokens(ws[j]["text"])[:1] if j >= 0 else []) if tw else None
 264 | +        if tw and heard == tw:                  # ruling 33 part 2: the trimmed word opens the sentence
 265 | +            j -= 1
 266 | +        elif not tw and self_repair(ws, j, first):     # ruling 8: the speaker's false start opens the sentence
 267 |              repair, j = ws[j]["text"], j - 1
 268 |          prev = ws[j]["text"] if j >= 0 else None
 269 |          t_open = float(ws[j + 1]["start"])      # the clip's opening word (its self-repair, when there is one)
 270 | @@ -209,6 +215,13 @@ def edges(second, wav_start, start, end, text):
 271 |          if repair:
 272 |              out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 273 |                               "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 274 | +        if tw and heard != tw:                  # the trimmed word is not what the recogniser heard: no IN
 275 | +            out["in"] = {"ok": False, "word": ws[i]["text"], "before": ws[i - 1]["text"] if i > 0 else None,
 276 | +                         "trimmed": trimmed, "why": f"the recogniser does not hear the trimmed word {trimmed!r} right "
 277 | +                                                    f"before the clip (ruling 33 part 2)"}
 278 | +        elif tw:
 279 | +            out["in"].update(trimmed=trimmed, why=out["in"]["why"] + f" (before the trimmed word {trimmed!r}, which "
 280 | +                                                                      f"opens the sentence: ruling 33 part 2)")
 281 |      else:
 282 |          out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
 283 |      if co:                                      # the occurrence nearest the clip's end (audit 0338, as at the IN)
 284 | @@ -224,7 +237,7 @@ def edges(second, wav_start, start, end, text):
 285 |      return dict(out, cuttable=out["in"]["ok"] and out["out"]["ok"])
 286 |  
 287 |  
 288 | -def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None):
 289 | +def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None, trimmed=None):
 290 |      """Both checks for one selected segment -> a record (the second pass's text kept as evidence). ok only when the
 291 |      critical tokens agree in both directions AND exactly one speaker was measured inside."""
 292 |      if wav is None:
 293 | @@ -243,5 +256,5 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 294 |              "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 295 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 296 |              "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S), start, end,
 297 | -                           text),
 298 | +                           text, trimmed),
 299 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 300 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 301 | index ba246650..57c0de7d 100644
 302 | --- a/tests/package/test_angles.py
 303 | +++ b/tests/package/test_angles.py
 304 | @@ -399,6 +399,27 @@ class TestEdgesRulings38And39(unittest.TestCase):
 305 |          self.assertTrue(e["in"]["ok"], e["in"])
 306 |          self.assertEqual((e["in"]["self_repair"], e["in"]["pause_ms"]), ("Bit-", 800))
 307 |  
 308 | +    def test_a_trimmed_leading_word_must_be_heard_and_the_in_rule_reads_before_it(self):    # ruling 33 part 2
 309 | +        e = self.edges([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "But", "start": 1.10, "end": 1.30}],
 310 | +                       1.40)                                                     # 'But' heard right before the clip
 311 | +        self.assertFalse(e["in"]["ok"])                       # without the trim: 'But' runs on into the clip
 312 | +        ws, end = self.ws([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "But", "start": 1.10, "end": 1.30}],
 313 | +                          1.40)
 314 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 315 | +        self.assertTrue(e["in"]["ok"], e["in"])
 316 | +        self.assertEqual((e["in"]["before"], e["in"]["trimmed"]), ("path.", "But"))
 317 | +        self.assertIn("before the trimmed word 'But'", e["in"]["why"])
 318 | +        ws, end = self.ws([{"text": "and", "start": 0.20, "end": 0.50}, {"text": "But", "start": 1.30, "end": 1.38}],
 319 | +                          1.40)
 320 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 321 | +        self.assertTrue(e["in"]["ok"], e["in"])                                  # 800 ms before 'But': a pause
 322 | +        self.assertEqual(e["in"]["pause_ms"], 800)
 323 | +        ws, end = self.ws([{"text": "path.", "start": 0.20, "end": 0.60}, {"text": "And", "start": 1.10, "end": 1.30}],
 324 | +                          1.40)
 325 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, self.TEXT, trimmed="But")
 326 | +        self.assertFalse(e["in"]["ok"])                                          # another word was heard
 327 | +        self.assertIn("does not hear the trimmed word 'But'", e["in"]["why"])
 328 | +
 329 |      def test_the_window_reaches_4_s_before_the_clip_and_stops_at_the_file_head(self):
 330 |          import tempfile
 331 |          self.assertEqual((TT.PAD_BEFORE_S, TT.PAD_S, TT.PAUSE_MIN_S), (4.0, 1.5, 0.7))
 332 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 333 | index d00f10db..18598d22 100644
 334 | --- a/tests/package/test_medley.py
 335 | +++ b/tests/package/test_medley.py
 336 | @@ -25,7 +25,7 @@ import eligibility as E  # noqa: E402
 337 |  import package as PK  # noqa: E402
 338 |  import package_pin  # noqa: E402
 339 |  from config import BRIDGE_WORD_CAP  # noqa: E402
 340 | -from test_eligibility import NOW, REG  # noqa: E402
 341 | +from test_eligibility import NOW, REG, source  # noqa: E402
 342 |  from test_gates import Canned  # noqa: E402
 343 |  from test_moments import pm  # noqa: E402
 344 |  import house_style as HS  # noqa: E402
 345 | @@ -734,6 +734,94 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 346 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 347 |  
 348 |  
 349 | +class TestRuling33TrimAtThePinStage(unittest.TestCase):
 350 | +    """Ruling 33 part 2 (render merged 11e361cc), used per the 04:58 order's item 42: a moment opening on ONE of
 351 | +    but/and/so/well/now/yeah, left out by the render's STAND_ALONE opener rule, may be cut one word in. The variant is
 352 | +    judged like any moment (step A, L-v 2 with the trimmed word heard, the acoustic onset rule at the trimmed cut); the
 353 | +    clip scorer's verdict is pending at the render; the pin seals trimmed_leading and untrimmed_start."""
 354 | +
 355 | +    def moment(self, sentence, mid="t"):
 356 | +        src = source([sentence], vid="vT")
 357 | +        a, b = src.sentences[0]
 358 | +        m = dict(pm(mid, "T", 0.0, vid="vT"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
 359 | +                 start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
 360 | +        m["duration_s"] = round(m["end"] - m["start"], 2)
 361 | +        return m, {"vT": src}
 362 | +
 363 | +    def test_one_leading_word_is_trimmed_and_the_variant_carries_it(self):
 364 | +        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 365 | +        self.assertIn("clip opens on 'but'", PK.no_role_on_screen(m))
 366 | +        v = PK.trim_variant(m, srcs)
 367 | +        self.assertEqual((v["moment_id"], v["trimmed_leading"], v["untrimmed_start"]), ("t~trim", "But", m["start"]))
 368 | +        self.assertTrue(v["text"].startswith("Bitcoin has rarely"))
 369 | +        self.assertEqual(v["words"], [m["words"][0] + 1, m["words"][1]])
 370 | +        self.assertGreater(v["start"], m["start"])
 371 | +        self.assertAlmostEqual(v["duration_s"], round(m["end"] - v["start"], 2))
 372 | +        self.assertIsNone(PK.no_role_on_screen(v))
 373 | +
 374 | +    def test_only_one_word_and_only_the_ruled_words(self):
 375 | +        for sentence in ("But then Bitcoin had six negative weeks back to back in its whole history.",    # 'then'
 376 | +                         "Because Bitcoin had six negative weeks back to back in its whole history.",      # not ruled
 377 | +                         "Bitcoin had six negative weeks back to back in its whole history."):             # no opener
 378 | +            m, srcs = self.moment(sentence)
 379 | +            self.assertIsNone(PK.trim_variant(m, srcs), sentence)
 380 | +        self.assertEqual(PK.TRIM_WORDS, package_pin.TRIM_WORDS)
 381 | +
 382 | +    def test_the_scorer_verdict_is_pending_at_the_render_and_sealed_in_the_row(self):
 383 | +        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 384 | +        v = PK.trim_variant(m, srcs)
 385 | +        r = PK.stand_alone_check([{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}])
 386 | +        self.assertTrue(r["ok"], r["rows"])
 387 | +        self.assertEqual(r["scorer_pending"], ["clip_01"])
 388 | +
 389 | +    def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 390 | +        segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 391 | +                dict(pm("x", "B", 14.0), text="Bitcoin keeps every promise it ever made to me.",
 392 | +                     trimmed_leading="But", untrimmed_start=0.0, start=0.3),
 393 | +                dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
 394 | +        by = {m["moment_id"]: m for m in segs}
 395 | +        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
 396 | +                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
 397 | +                  "caption": {"text": "three clips", "cites": []}}
 398 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
 399 | +        self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
 400 | +        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 401 | +        pin = package_pin.to_pin(spk(pk), "test")
 402 | +        s1 = pin["segments"][1]
 403 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 404 | +        self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 405 | +        mp = pin["moments_package"]
 406 | +        args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 407 | +        self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 408 | +        other = [dict(x) for x in pin["segments"]]
 409 | +        other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 410 | +        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 411 | +        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0}):
 412 | +            p = spk(pk)
 413 | +            p["segments"][1] = dict(p["segments"][1], **bad)
 414 | +            with self.assertRaises(package_pin.PinRefused):
 415 | +                package_pin.to_pin(p, "test")
 416 | +        p = spk(pk)
 417 | +        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 418 | +        with self.assertRaises(package_pin.PinRefused):                          # both keys or neither
 419 | +            package_pin.to_pin(p, "test")
 420 | +
 421 | +    def test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out(self):
 422 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 423 | +              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
 424 | +        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
 425 | +        saved = PK.trim_variant
 426 | +        try:
 427 | +            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 428 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 429 | +            out = rig.run()
 430 | +        finally:
 431 | +            PK.trim_variant = saved
 432 | +        self.assertEqual(out["trimmed"], {"b": "b~trim"})
 433 | +        self.assertIn("b~trim", out["prescreen"]["trim_cut"])                     # ruling 33 (a): out, any place
 434 | +        self.assertIsNotNone(out["package"])
 435 | +
 436 | +
 437 |  class TestRuling41Search(unittest.TestCase):
 438 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 439 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 440 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins; the integrator renders them. The pin stage must never seal what the render would
refuse, EXCEPT where the orchestrator has ruled otherwise. One such case is stated below.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why:
- ORCHESTRATOR RULING 33 (03:12 ET Nov 13): "A clip that opens on a discourse conjunction or reply word (but, and,
  so, well, now, yeah) may have that ONE leading word trimmed at the cut when (a) the acoustic onset rule is met on
  the trimmed cut, and (b) the pipeline's STAND_ALONE scorer affirms the trimmed clip at its unchanged threshold, and
  (c) L-s step A is re-judged on the trimmed span. The locked text is the trimmed text. If any of the three fails, the
  clip is out."
- ORDER 04:58, item 42: "USE RULING 33 PART 2 NOW (merged on main 11e361cc) ... Rebuild with trimmed_leading as soon
  as your side is audited; report how many of the 113 come back."
- The render's contract (main c6605895): on a segment, only when a word is trimmed:
  - "trimmed_leading", the ONE word as spoken, whose canonical token is one of but/and/so/well/now/yeah;
  - "untrimmed_start", 0 <= untrimmed_start < start;
  - approved_text is the trimmed text, and start/end bound the kept words.
  The render checks:
  - the trimmed word sits right before the lock in its own transcript, with a sentence end (or the file's first word)
    before it;
  - a quiet run between the trimmed word and the first kept word;
  - the cut opens in quiet;
  - STAND_ALONE: its clip scorer (a local model on GPU0) must affirm EVERY trimmed segment.
- THE STATED ASSUMPTION: this session may not use any GPU, so the scorer cannot run at the pin stage. The render's
  check_edl with rate=None fails a trimmed segment closed. Per item 42 ("use it now"), the scorer's verdict is
  PENDING AT THE RENDER: the pin stage records it, and the render holds a trimmed pin its scorer refuses, at validate,
  before any cut (the integrator: "That costs a run slot, not a bad video"). (a) and (c) ARE judged at the pin stage.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (the trim is the orchestrator's own ruling).

The change:
1. pipeline/stand_alone.py: synced byte-identical to main's c6605895 (the render's trimmed_word / trimmed_opener in
   check_edl).
2. pipeline/transcript_truth.py, edges(..., trimmed=None) and verify_segment(..., trimmed=None):
   - with a trimmed word, the recogniser's word right before the clip's first kept word must be that word (by its
     canonical token), else IN fails;
   - the IN rule (a sentence end, a measured pause >= 700 ms, or the file head) then reads before the trimmed word;
   - without one, the IN rule is unchanged.
3. pipeline/package.py:
   - TRIM_WORDS.
   - trim_variant(m, sources): for a moment whose first word is one of TRIM_WORDS, the variant takes text, start and
     words from the next word of its word record, with duration_s = end - new start, trimmed_leading (the word as
     spoken), untrimmed_start (the original start) and moment_id "<id>~trim". It must pass no_role_on_screen and
     no_topic on the trimmed text, else None.
   - build(): the variants of the moments the opener rule left out join the usable moments (before the ad-read screen
     and step A, which judges the trimmed span: ruling 33 c). out["trimmed"] records them.
   - truth_for passes trimmed=m.get("trimmed_leading").
   - After the hook-onset measure, a trimmed moment that does not pass it (the acoustic onset at its trimmed cut:
     ruling 33 a) is left out at ANY place, recorded in out["prescreen"]["trim_cut"].
   - stand_alone_check records r["scorer_pending"] = the labels of trimmed segments. Its EDL carries no
     selection_lock, so check_edl judges the trimmed text's own opener; the sealed stand_alone row carries
     scorer_pending.
   - _package's segment rows carry trimmed_leading and untrimmed_start when present.
4. pipeline/package_pin.py:
   - SEALED_LATER gains trimmed_leading and untrimmed_start, so they enter the seal only when present and older pins
     recompute;
   - TRIM_WORDS;
   - to_pin copies both keys onto the pin segment;
   - trim_problems refuses a pin unless: both keys or neither; the canonical token is one of TRIM_WORDS;
     0 <= untrimmed_start < start.
5. Tests:
   - the edge rule with and without the trim, another word heard, and the pause before the trimmed word;
   - trim_variant ("But" trimmed; "But then" and "Because" and no opener give None);
   - the pending scorer;
   - the pin sealing the trim, and the malformed refusals;
   - a trimmed moment without a clean cut left out.

Check in particular:
- that (a) and (c) are really judged at the pin stage, and that a trimmed moment that fails either is out;
- that the scorer's pending status is visible in the sealed record and nothing pretends it was affirmed;
- that the pin's fields match the render's contract exactly;
- that untrimmed segments, old pins and the rest of the IN rule are unchanged;
- whether "pending at the render" is a defensible reading of the item-42 order. Say so if you think it is not.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".

