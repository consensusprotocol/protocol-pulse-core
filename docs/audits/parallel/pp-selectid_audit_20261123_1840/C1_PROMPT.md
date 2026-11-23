# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261123_1840
# Branch: pp-selectid
# Generated: 2026-11-23 18:42 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261123_1840/C1_STEP.diff (276 lines)
```
   1 | diff --git a/pipeline/moments.py b/pipeline/moments.py
   2 | index 7d55d31..db6a324 100644
   3 | --- a/pipeline/moments.py
   4 | +++ b/pipeline/moments.py
   5 | @@ -366,16 +366,23 @@ def ad_read_marker(moment_text, before_text=""):
   6 |      return None
   7 |  
   8 |  
   9 | -def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
  10 | +def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None,
  11 | +                      before_marker_soft=False):
  12 |      """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
  13 |      screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
  14 |      verdict (role "exclusion_verdict", never on the moment's own miner: avoid_model; audit p2 C3); any hard risk, a
  15 |      moment not about Bitcoin, an unreadable or uncertain verdict excludes (law L-m). An unreadable or unavailable verdict
  16 | -    is also NOT measured (the exam adapter reports it as such)."""
  17 | +    is also NOT measured (the exam adapter reports it as such).
  18 | +    before_marker_soft (RULING 146 (3), orchestrator 07:55 ET Nov 18; PBX 08:34: 'we never include any sponsor material
  19 | +    ever, but if it doesn't have any in it then it is fine to use'; the never-empty pass only): a marker ONLY in the
  20 | +    sentence before the moment no longer excludes by itself; the model reads the moment with its context, and its
  21 | +    'ad_read' risk (the moment's own words in the ad, e.g. an ad read's opening line) excludes as always. Kept, the
  22 | +    verdict carries "ad_before" (the screen's reason) for the package's flag. A marker in the moment stays HARD."""
  23 |      import providers as P
  24 |      from story_semantics import quote_data
  25 |      why = ad_read_marker(moment_text, before_text)
  26 | -    if why:
  27 | +    soft_why = why if (why and before_marker_soft and ad_read_marker(moment_text) is None) else None   # RULING 146 (3)
  28 | +    if why and not soft_why:
  29 |          return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
  30 |                  "replayed": False}
  31 |      def parse(text):
  32 | @@ -400,4 +407,5 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
  33 |      if obj["about_bitcoin"] != "yes":
  34 |          return dict(meas, verdict="exclude", why=f"about Bitcoin: {obj['about_bitcoin']}: {str(obj['why'])[:200]}",
  35 |                      risks=[], backend=r.backend)
  36 | -    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend)
  37 | +    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend,
  38 | +                **({"ad_before": soft_why} if soft_why else {}))           # RULING 146 (3): the package flags it
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 3c652a6..dfe1255 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -1296,6 +1296,21 @@ def ad_read_out(ms, sources):
  44 |      return out
  45 |  
  46 |  
  47 | +def ad_before_soft(ms, ad_read, soft):
  48 | +    """RULING 146 (3) (orchestrator 07:55 ET Nov 18): in the never-empty pass, a moment the deterministic ad-read screen
  49 | +    refuses ONLY for a marker in the sentence before it stays in the pool, marked ad_before (this pass's own mark on
  50 | +    its own copies: popped first, never carried in). exclusion_for() then asks the model with the context; its ad_read
  51 | +    risk (the moment's own words in the ad) still excludes. A marker in the moment's own words stays HARD; the clean
  52 | +    pass marks nothing. -> {moment id: the screen's reason}."""
  53 | +    for m in ms:
  54 | +        m.pop("ad_before", None)
  55 | +    out = {k: v for k, v in ad_read.items() if soft and v.endswith("in the sentence before it")}
  56 | +    for m in ms:
  57 | +        if m["moment_id"] in out:
  58 | +            m["ad_before"] = out[m["moment_id"]]
  59 | +    return out
  60 | +
  61 | +
  62 |  def trim_variant(m, sources):
  63 |      """RULING 33 PART 2 (the render merged it at 11e361cc; the orchestrator's 04:58 item 42, "use it now"). A moment
  64 |      whose first word is ONE of TRIM_WORDS, left out by the render's STAND_ALONE opener rule, may be cut one word in.
  65 | @@ -3133,7 +3148,8 @@ def paid_gates(router, pk, sources, a_by, levels, now, writers_v, writers_f, poo
  66 |  
  67 |  
  68 |  def exclusion_for(router, m, sources, cache, seed=7):
  69 | -    key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
  70 | +    soft = bool(m.get("ad_before"))                   # RULING 146 (3): the never-empty pass's sponsor-before mark, and
  71 | +    key = (m["moment_id"] if seed == 7 else (m["moment_id"], seed)) if not soft else (m["moment_id"], seed, "ad_before")
  72 |      if key not in cache:
  73 |          import moments as M
  74 |          src = src_of(m, sources)
  75 | @@ -3142,8 +3158,8 @@ def exclusion_for(router, m, sources, cache, seed=7):
  76 |              cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
  77 |                            "risks": [], "backend": None, "measured": False, "replayed": False}            # record)
  78 |          else:
  79 | -            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,
  80 | -                                             avoid_model=(m.get("mined") or {}).get("by"))
  81 | +            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,   # its own cache key
  82 | +                                             avoid_model=(m.get("mined") or {}).get("by"), before_marker_soft=soft)
  83 |      return cache[key]
  84 |  
  85 |  
  86 | @@ -3433,7 +3449,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  87 |      #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
  88 |      #   video at most once, L-y 4)
  89 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  90 | -    ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  91 | +    ad_soft = ad_before_soft(ms, ad_read, soft)       # RULING 146 (3): the never-empty pass's sponsor-before moments
  92 | +    if ad_soft:
  93 | +        log(f"  RULING 146 (3) NEVER EMPTY: {len(ad_soft)} moment(s) with a sponsor marker only in the sentence before "
  94 | +            f"them go to the exclusion model (its ad_read risk stays HARD), flagged if kept: "
  95 | +            f"{', '.join(k[:8] for k in sorted(ad_soft))}")
  96 | +    ms = [m for m in ms if m["moment_id"] not in ad_read or m["moment_id"] in ad_soft]   # around a moment it refuses
  97 |      n_ch = len({m["channel_id"] for m in ms})
  98 |      if candidate is None and n_ch < 3:
  99 |          # RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel
 100 | @@ -3954,7 +3975,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 101 |                                  stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 102 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 103 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 104 | -                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 105 | +                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},
 106 | +                                chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},   # 146 (3)   # RULING 138 (3)
 107 |                                  seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get("step_a_flags")
 108 |                                             for sg in pk["segments"]},                          # RULING 137 stage 2a
 109 |                                  mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 110 | @@ -4477,7 +4499,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 111 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 112 |                                              value=val,                       # ruling 91: the takeaway earned its place
 113 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 114 | -                                            soft=soft, who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 115 | +                                            soft=soft,
 116 | +                                            chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},
 117 | +                                            who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 118 |                                                              for sg in pk["segments"]},
 119 |                                              seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get(
 120 |                                                  "step_a_flags") for sg in pk["segments"]},    # RULING 137 stage 2a
 121 | @@ -4613,6 +4637,7 @@ def _spent(spend):
 122 |  
 123 |  
 124 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 125 | +              chan_of=None,
 126 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 127 |                seg_flags=None, mids=None):
 128 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 129 | @@ -4712,6 +4737,12 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 130 |                                 **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
 131 |                                    if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
 132 |             if hook is not None else {}),                                                                      # (2)
 133 | +        **({"sponsor": {"status": "FLAGGED", "by": "moments.exclusion_verdict (ruling 146 (3)): a sponsor mention in "
 134 | +                                                   "the sentence before the clip only; its own words judged by the "
 135 | +                                                   "exclusion model", "replayed": False, "n": len(exc), "flags": [
 136 | +                            f"The clip ({(chan_of or {}).get(mid) or 'its channel'}) comes right after a sponsor "
 137 | +                            f"mention." for mid, e in exc.items() if e.get("ad_before") and e.get("verdict") == "keep"]}}
 138 | +           if any(e.get("ad_before") and e.get("verdict") == "keep" for e in exc.values()) else {}),
 139 |          **({"graphics": {"status": "FLAGGED", "by": "visual_pin.graphics_only (ruling 146 (1)): the show's own "
 140 |                                                      "on-screen graphics, whole in a package sealed 16:9 only",
 141 |                           "replayed": False, "n": len(visual), "flags": [
 142 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 143 | index 9cdc53c..bbbba23 100644
 144 | --- a/pipeline/package_pin.py
 145 | +++ b/pipeline/package_pin.py
 146 | @@ -49,6 +49,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 147 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 148 |                          "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
 149 |                          #   91), a measured one; fidelity, length and the banned words stay HARD
 150 | +                        "sponsor",                         # RULING 146 (3): a sponsor mention in the sentence before
 151 | +                        #   a clip only, the clip kept by the exclusion model (its ad_read risk stays HARD)
 152 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 153 |  #   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
 154 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 155 | @@ -454,6 +456,10 @@ def gate_problems(gates, required=REQUIRED_GATES):
 156 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 157 |          elif row.get("replayed") is not False:
 158 |              out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
 159 | +    for g, row in gates.items():                     # RULING 146 (3) (its audit's S8): a FLAGGED row outside the
 160 | +        if g not in required and isinstance(row, dict) and row.get("status") == "FLAGGED" and \
 161 | +                not flagged_ok(g, row):              # required set stands, as any other, only on a SOFT gate with flags
 162 | +            out.append(f"{g}: FLAGGED without a soft gate and its plain flags (ruling 137)")
 163 |      return out
 164 |  
 165 |  
 166 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 167 | index 0e4d42a..f965429 100644
 168 | --- a/tests/package/test_medley.py
 169 | +++ b/tests/package/test_medley.py
 170 | @@ -834,7 +834,8 @@ class Rig:
 171 |              "paid_gates": lambda *a, **k: (self.fids.pop(0) if self.fids else fid, cx),
 172 |              "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
 173 |                                                           "keep", "measured": True, "replayed": False,
 174 | -                                                         "backend": "xai:grok"},
 175 | +                                                         "backend": "xai:grok",     # RULING 146 (3): as the real one
 176 | +                                                         **({"ad_before": m["ad_before"]} if m.get("ad_before") else {})},
 177 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 178 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 179 |              "hook_onset_for": self.onset,
 180 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 181 | index a614ec0..fee382c 100644
 182 | --- a/tests/package/test_ruling_137.py
 183 | +++ b/tests/package/test_ruling_137.py
 184 | @@ -684,6 +684,91 @@ class TestRuling150ValueSoft(unittest.TestCase):
 185 |      def test_no_verdict_stays_hard(self):
 186 |          _, pk = self.run_rig(measured=False)
 187 |          self.assertIsNone(pk)
 188 | +class TestRuling146SponsorBefore(unittest.TestCase):
 189 | +    """RULING 146 (3) (orchestrator 07:55 ET Nov 18; PBX 08:34 'we never include any sponsor material ever, but if it
 190 | +    doesn't have any in it then it is fine to use'), the never-empty pass: a sponsor marker ONLY in the sentence before
 191 | +    a clip goes to the exclusion model with the context; its ad_read risk (the clip's own words in the ad: Natalie
 192 | +    Brunell 6e79ceaa was the opening line of The Bitcoin Way's read) excludes, HARD; kept, the package flags 'The clip
 193 | +    (X) comes right after a sponsor mention.' A marker in the clip's own words stays HARD; the clean pass is unchanged."""
 194 | +    BEFORE = "Use my promo code stories to get 10% off. This episode is sponsored by BitKey."
 195 | +    CLIP = "If your Bitcoin can be frozen or monitored by an exchange, it's not yours."
 196 | +    SPONSOR = "ad-read marker 'sponsored' in the sentence before it"
 197 | +
 198 | +    def verdict(self, text, before, soft, reply):
 199 | +        import json
 200 | +        import types
 201 | +        import moments as M
 202 | +        import providers as P
 203 | +        calls = []
 204 | +
 205 | +        def fake(router, role, prompt, parse, n, seed, avoid_model=None):
 206 | +            calls.append(role)
 207 | +            return types.SimpleNamespace(backend="heimdall:deepseek", replayed=False), parse(json.dumps(reply))
 208 | +        with mock.patch.object(P, "call_parsed", fake):
 209 | +            return M.exclusion_verdict(None, text, before, "", before_marker_soft=soft), calls
 210 | +
 211 | +    def test_the_model_decides_a_marker_in_the_sentence_before(self):
 212 | +        keep = {"risks": [], "about_bitcoin": "yes", "why": "her own view on custody"}
 213 | +        v, calls = self.verdict(self.CLIP, self.BEFORE, True, keep)
 214 | +        self.assertEqual((v["verdict"], v.get("ad_before"), calls), ("keep", self.SPONSOR, ["exclusion_verdict"]))
 215 | +        ad = {"risks": ["ad_read"], "about_bitcoin": "yes", "why": "the opening line of the next ad read"}
 216 | +        v, _ = self.verdict(self.CLIP, self.BEFORE, True, ad)
 217 | +        self.assertEqual((v["verdict"], v.get("ad_before")), ("exclude", None))           # the clip IS the ad: HARD
 218 | +
 219 | +    def test_a_marker_in_the_clip_and_the_clean_pass_stay_hard(self):
 220 | +        keep = {"risks": [], "about_bitcoin": "yes", "why": "x"}
 221 | +        for text, before, soft in ((self.CLIP + " Use my promo code stories.", "", True),
 222 | +                                   (self.CLIP, self.BEFORE, False)):
 223 | +            v, calls = self.verdict(text, before, soft, keep)
 224 | +            self.assertEqual((v["verdict"], v["backend"], calls), ("exclude", "deterministic", []), (text, soft))
 225 | +
 226 | +    def test_the_mark_is_the_passs_own_and_the_cache_key_its_own(self):
 227 | +        ms = [{"moment_id": "a", "ad_before": "stale"}, {"moment_id": "b"}]
 228 | +        ad_read = {"a": self.SPONSOR, "b": "ad-read marker 'promo code' in the moment"}
 229 | +        self.assertEqual(PK.ad_before_soft(ms, ad_read, False), {})
 230 | +        self.assertNotIn("ad_before", ms[0])                                              # popped, never carried in
 231 | +        self.assertEqual(PK.ad_before_soft(ms, ad_read, True), {"a": self.SPONSOR})
 232 | +        self.assertEqual((ms[0].get("ad_before"), ms[1].get("ad_before")), (self.SPONSOR, None))
 233 | +        seen, cache = [], {}
 234 | +        with mock.patch.object(PK, "src_of", lambda m, s: "src"), \
 235 | +                mock.patch.object(PK.CI, "context_around", lambda *a: (self.BEFORE, "")):
 236 | +            import moments as M
 237 | +            with mock.patch.object(M, "exclusion_verdict", lambda *a, **k: seen.append(k) or {"verdict": "keep"}):
 238 | +                PK.exclusion_for(None, dict(ms[0], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
 239 | +                PK.exclusion_for(None, dict(ms[1], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
 240 | +        self.assertEqual([k["before_marker_soft"] for k in seen], [True, False])
 241 | +        self.assertEqual(sorted(map(str, cache)), sorted(map(str, [("a", 7, "ad_before"), "b"])))
 242 | +
 243 | +    def run_rig(self, never_empty, excluded=()):
 244 | +        import test_medley as TM
 245 | +        from test_moments import pm
 246 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 247 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 248 | +                   excluded=excluded, follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
 249 | +        r.build_kw = {"never_empty": never_empty}
 250 | +        with mock.patch.object(PK, "ad_read_out", lambda ms, sources: {"x": self.SPONSOR}):
 251 | +            return r.run()["package"]
 252 | +
 253 | +    def test_a_clip_after_a_sponsor_mention_seals_flagged_never_empty_only(self):
 254 | +        self.assertIsNone(self.run_rig(False))                                            # the clean pass: refused
 255 | +        pk = self.run_rig(True)
 256 | +        self.assertIsNotNone(pk)
 257 | +        ch = next(s["channel"] for s in pk["segments"] if s["moment_id"] == "x")
 258 | +        self.assertEqual((pk["gates"]["sponsor"]["status"], pk["gates"]["sponsor"]["flags"]),
 259 | +                         ("FLAGGED", [f"The clip ({ch}) comes right after a sponsor mention."]))
 260 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 261 | +        self.assertIsNone(self.run_rig(True, excluded={"x"}))                              # the model excludes: HARD
 262 | +
 263 | +    def test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags(self):
 264 | +        pk = self.run_rig(True)
 265 | +        req = PP.required_gates(pk)
 266 | +        self.assertNotIn("sponsor", req)                              # an extra row: gate_problems reads it as well
 267 | +        made_up = {"status": "FLAGGED", "flags": ["A plain sentence."], "replayed": False}
 268 | +        self.assertEqual(PP.gate_problems(dict(pk["gates"], made_up=made_up), req),
 269 | +                         ["made_up: FLAGGED without a soft gate and its plain flags (ruling 137)"])
 270 | +        no_flags = dict(pk["gates"], sponsor=dict(pk["gates"]["sponsor"], flags=[]))
 271 | +        self.assertEqual(PP.gate_problems(no_flags, req),
 272 | +                         ["sponsor: FLAGGED without a soft gate and its plain flags (ruling 137)"])
 273 |  
 274 |  
 275 |  class TestRuling148RuntimeFloor(unittest.TestCase):
 276 | 
```

---

pp-selectid: RULING 146 (3) (orchestrator 07:55 ET Nov 18; restated 18:18 ET Nov 23: "HARD: ANY sponsor or ad-read
words inside the clip (PBX: 'we never include any sponsor material, ever')"; "SOFT, flagged: a clip right after a
sponsor mention"). Builder-only: the integrator's render never re-checks sponsor mentions (its DoD: "nothing checks for
a sponsor mention").
THE CHANGE (never-empty pass only; the clean pass unchanged):
- moments.exclusion_verdict(..., before_marker_soft=False) (moments.py:369): with before_marker_soft, a deterministic
  ad-read marker (ad_read_marker, moments.py:358, unchanged) found ONLY in the sentence before the moment (none in the
  moment's own words) no longer excludes by itself: the blind model reads the moment with its context; ANY risk it
  names (ad_read among them: the moment's own words in the ad) excludes as always; a kept verdict carries "ad_before"
  (the screen's reason). A marker in the moment's own words stays a deterministic exclude.
- package.ad_before_soft (package.py:1299): pops every moment's old mark first; in the never-empty pass only, marks the
  moments the free screen ad_read_out (package.py:1280, unchanged) refused ONLY for a marker "in the sentence before
  it"; _build (package.py:3452) keeps those moments in the pool; exclusion_for (package.py:3150) passes the mark as
  before_marker_soft under its OWN cache key.
- inventory (package.py:4740): an extra "sponsor" row, FLAGGED, one flag per kept marked clip: "The clip (<channel>)
  comes right after a sponsor mention." package_pin.SOFT_GATES += "sponsor".
- package_pin.gate_problems (package_pin.py:446): ALSO checks every FLAGGED row outside the required set with the
  unchanged flagged_ok (package_pin.py:407: a SOFT gate and non-empty plain flags). The integrator's check_pin_only
  calls gate_problems live: this only adds refusals (the live soft rows graphics / runtime / hook_onset /
  pbx_exception are all in SOFT_GATES). review_flags_of (414) and the cap (content_flags, 440) already count every
  FLAGGED row's flags.
Files: pipeline/moments.py, pipeline/package.py, pipeline/package_pin.py, tests/package/test_medley.py (the rig's
exclusion stub returns the mark as the real one does), tests/package/test_ruling_137.py.
TESTS (TestRuling146SponsorBefore): the model decides a marker in the sentence before (keep: marked; ad_read: exclude);
a marker in the clip, and the clean pass, stay deterministic excludes with no model call; the mark is the pass's own
and the cache key its own; the real build() seals FLAGGED in the never-empty pass only and refuses when the model
excludes; an extra FLAGGED row stands only on a soft gate with flags. Mutations 11 of 11 killed.
PLEASE CHECK: (1) can any words of the clip ITSELF that belong to an ad read reach a sealed package? (2) can the clean
pass, or a cached verdict from the other pass, let a marked moment in? (3) is the flag right (one per kept marked clip,
counted toward the cap of 3)? (4) does the gate_problems addition refuse anything a live pin legitimately carries?



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
