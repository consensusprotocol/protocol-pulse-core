# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-0829
# Branch: pp-selectid
# Generated: 2026-11-12 08:33 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_0742/C1_STEP.diff (624 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ec029024..840e0f70 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -106,38 +106,49 @@ def time_sensitive(m):
   6 |          any(kind == "current" for _, kind in VF.price_mentions(t))
   7 |  
   8 |  
   9 | -def runtime(segs, vo_s):
  10 | -    """segments' word spans + every spoken VO second (intro, bridges AND the sign-off) + FIXED_S (audit p2 M4)."""
  11 | -    return round(sum(m["duration_s"] for m in segs) + vo_s + FIXED_S, 2)
  12 | +FINAL_TAIL_S = E.TAIL_S             # what a final adds to its word spans (credits card + sign-off, outro, cut edges, pads)
  13 |  
  14 |  
  15 | -R4_MOMENTS_SHARE = 0.40            # orchestrator 06:00 ruling 4: moments-first VO up to 40 % of the runtime; a VO line
  16 | -                                   # after the hook, after every clip and after the last clip; 60-70 s stays hard
  17 | +def runtime(segs, vo_lines):
  18 | +    """The FACTORY's own estimate, the one its hard 60-70 s check reads (edl_rules._r4_moments, main a5ec0f17: "hook +
  19 | +    clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll"): segments' word spans + every VO line
  20 | +    (intro, bridges) at R4_WPS w/s + R4_PREROLL_S each + FINAL_TAIL_S (the sign-off is inside it). It replaced (07:42)
  21 | +    this module's own estimate (2.6 w/s, no pre-roll, FIXED_S + the sign-off), which ran 3-4 s lower than the factory's
  22 | +    on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  23 | +    vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
  24 | +    return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
  25 | +
  26 | +
  27 | +R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first VO up to 45 % of the TOTAL runtime (06:00
  28 | +                                   # ruling 4 said 40 %); a VO line after the hook, after every clip and after the last
  29 | +                                   # clip; 60-70 s stays hard
  30 |  
  31 |  
  32 |  def r4_max_vo_words(content_s, n_vo):
  33 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
  34 | -    VO line) <= 40 % of the runtime estimate (content + VO and the standard sign-off at WPS + FIXED_S)."""
  35 | -    num = R4_MOMENTS_SHARE * (content_s + SIGNOFF_WORDS / WPS + FIXED_S) - R4_PREROLL_S * n_vo
  36 | -    return max(0, int(num / (1 / R4_WPS - R4_MOMENTS_SHARE / WPS)))
  37 | +    VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
  38 | +    # VO_s = w / R4_WPS + PRE * n ; runtime = content + VO_s + TAIL ; VO_s <= SHARE * runtime
  39 | +    vo_max = R4_MOMENTS_SHARE * (content_s + FINAL_TAIL_S) / (1 - R4_MOMENTS_SHARE)
  40 | +    return max(0, int(R4_WPS * (vo_max - R4_PREROLL_S * n_vo)))
  41 |  
  42 |  
  43 | -def min_vo_words(content_s):
  44 | -    """The fewest VO words (intro + bridges) that land 60 s: content + VO + the standard sign-off + FIXED_S >= 60."""
  45 | -    return max(0, int(WPS * (RUNTIME_S[0] - content_s - SIGNOFF_WORDS / WPS - FIXED_S) + 0.999))
  46 | +def min_vo_words(content_s, n_vo=2):
  47 | +    """The fewest VO words (intro + bridges) that land 60 s by the factory's estimate (runtime())."""
  48 | +    return max(0, int(R4_WPS * (RUNTIME_S[0] - content_s - FINAL_TAIL_S - R4_PREROLL_S * n_vo) + 0.999))
  49 |  
  50 |  
  51 |  def content_range(n_clips=2):
  52 |      """Seconds the segments may fill so that some VO lands the runtime in 60-70 s AND fits R4 (one VO line for the
  53 |      intro + one bridge per clip but the last)."""
  54 |      n_vo = 1 + (n_clips - 1)
  55 | -    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10) <= r4_max_vo_words(c / 10, n_vo))
  56 | -    return lo, RUNTIME_S[1] - FIXED_S - SIGNOFF_WORDS / WPS - VO_S[0]
  57 | +    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10, n_vo) <= r4_max_vo_words(c / 10, n_vo))
  58 | +    return lo, RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo          # runtime()'s own terms
  59 |  
  60 |  
  61 |  def r4(pk):
  62 |      """R4 for a moments-first package, as the orchestrator ordered it at 06:00 (ruling 4; the integrator brings
  63 | -    edl_rules.rule_r4 to it): VO (intro + bridges, edl_rules' estimate 2.5 w/s + 1 s per line) <= 40 % of the runtime
  64 | +    edl_rules.rule_r4 to it; the cap is 45 % since ruling 9, 08:29): VO (intro + bridges, edl_rules' estimate 2.5 w/s +
  65 | +    1 s per line) <= R4_MOMENTS_SHARE of the runtime
  66 |      estimate; the word caps of config.py; at most one VO line after each clip (the last clip included).
  67 |      -> (ok, reason). The share over clips + VO (today's edl_rules denominator) is reported beside it."""
  68 |      from config import BRIDGE_WORD_CAP, INTRO_WORD_CAP
  69 | @@ -164,7 +175,7 @@ def r4(pk):
  70 |  def budgets(content_s, n_bridges=1):
  71 |      """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
  72 |      hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
  73 | -    lo = min(min_vo_words(content_s), hi)
  74 | +    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
  75 |      return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
  76 |  
  77 |  
  78 | @@ -214,11 +225,11 @@ def assemble(order, by_id, fields, ctx, vo_kind):
  79 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  80 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
  81 |            "lines": lines}
  82 | -    so_words = len(pk["vo"]["signoff"].split())
  83 | -    pk["runtime_s_estimate"] = runtime(segs, (vo_words + so_words) / WPS)
  84 | -    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words + "
  85 | -                          f"sign-off {so_words} words at {WPS} w/s (assumed) + fixed {FIXED_S} s (credits card, outro, "
  86 | -                          f"transitions); the render measures the final")
  87 | +    vo_lines = [pk["vo"]["intro"]] + list(pk["vo"]["bridges"])
  88 | +    pk["runtime_s_estimate"] = runtime(segs, vo_lines)
  89 | +    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words at "
  90 | +                          f"{R4_WPS} w/s + {R4_PREROLL_S} s pre-roll per line + tail {FINAL_TAIL_S} s (sign-off, credits, "
  91 | +                          f"outro, edges): the factory's own R4 estimate; the render measures the final")
  92 |      return pk
  93 |  
  94 |  
  95 | @@ -778,12 +789,15 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
  96 |      a_rows = list((a_by or {}).values())
  97 |      return {
  98 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
  99 | -        "vo_fidelity_verdict": row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"), fid.get("replayed"),
 100 | -                                   measured=bool(fid.get("measured"))),
 101 | +        "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 102 | +                                        fid.get("replayed"), n=fid.get("runs", 1), measured=bool(fid.get("measured"))),
 103 | +                                    **({"votes": fid["majority"]["votes"], "splits": fid["majority"]["splits"]}
 104 | +                                       if fid.get("majority") else {})),          # ruling 07:42 (3): the majority
 105 |          "duplicate": row(not dup, "code (package.duplicates)"),
 106 |          "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
 107 |                           "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
 108 | -        "runtime": row(rt_ok, f"code (estimate at {WPS} w/s)"),
 109 | +        "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 110 | +                              f"{FINAL_TAIL_S} s tail)"),
 111 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 112 |          "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 113 |                           sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 114 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
 115 | index 5b8a4abf..6483abea 100644
 116 | --- a/pipeline/transcript_truth.py
 117 | +++ b/pipeline/transcript_truth.py
 118 | @@ -117,12 +117,29 @@ def speaker_turns(second, start_rel, end_rel):
 119 |  
 120 |  
 121 |  TERMINAL = (".", "!", "?")
 122 | +REPAIR_DASHES = ("-", "\u2013", "\u2014")
 123 |  
 124 |  
 125 |  def _w(t):
 126 |      return re.sub(r"[^\w']", "", (t or "").lower().replace("’", "'"))
 127 |  
 128 |  
 129 | +def self_repair(words, i, first):
 130 | +    """Orchestrator ruling 8 (08:29): words[i] is a SELF-REPAIR of the clip's first word when it is a truncated
 131 | +    repetition of it by the same speaker: it ends in a dash, its letters are a non-empty proper prefix of the next
 132 | +    word's, the next word is the clip's first word, and both carry the same speaker label (a missing label is not the
 133 | +    same speaker). Heard by the second recogniser and not by the primary, it belongs to the sentence it opens: not a
 134 | +    missing sentence start, not an L-v 2 disagreement. Exactly one such token; anything else is not one."""
 135 | +    if not 0 <= i < len(words) - 1:
 136 | +        return False
 137 | +    r, f = words[i], words[i + 1]
 138 | +    t = (r.get("text") or "").strip()
 139 | +    stem, fw = _w(t.rstrip("".join(REPAIR_DASHES))), _w(f.get("text"))
 140 | +    return (t.endswith(REPAIR_DASHES) and bool(stem) and len(stem) < len(fw) and fw.startswith(stem)
 141 | +            and bool(first) and fw[:4] == _w(first)[:4]
 142 | +            and r.get("speaker") is not None and r.get("speaker") == f.get("speaker"))
 143 | +
 144 | +
 145 |  def edges(second, wav_start, start, end, text):
 146 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
 147 |      the segment's edges, from its word timing on the SOURCE audio. IN: the recogniser's word at the clip's first word
 148 | @@ -142,11 +159,17 @@ def edges(second, wav_start, start, end, text):
 149 |            and _w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4]]
 150 |      if ci:
 151 |          i = ci[0]
 152 | -        prev = ws[i - 1]["text"] if i > 0 else None
 153 | +        j, repair = i - 1, None
 154 | +        if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
 155 | +            repair, j = ws[j]["text"], j - 1
 156 | +        prev = ws[j]["text"] if j >= 0 else None
 157 |          out["in"] = {"ok": prev is not None and prev.rstrip().endswith(TERMINAL), "word": ws[i]["text"],
 158 |                       "before": prev, "why": "a sentence ends before the clip" if prev and prev.rstrip().endswith(TERMINAL)
 159 |                       else ("the window starts at the clip: no word before it" if prev is None else
 160 |                             f"the recogniser runs on into the clip ('{prev}')")}
 161 | +        if repair:
 162 | +            out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 163 | +                             "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 164 |      else:
 165 |          out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
 166 |      if co:
 167 | @@ -170,10 +193,15 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 168 |      sec, rep = second_pass(router, wav)
 169 |      off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
 170 |      span = span_text(sec, off, off + (end - start)) or sec["text"]
 171 | +    sw = [w for w in sec.get("words") or [] if _inside(w, off, off + (end - start))]
 172 | +    toks = re.findall(r"[\w'’$%.,-]+", text or "")
 173 | +    repair = None
 174 | +    if len(sw) > 1 and toks and self_repair(sw, 0, toks[0]):     # ruling 8: only a LEADING self-repair, only one
 175 | +        repair, span = sw[0]["text"], " ".join(w["text"] for w in sw[1:]).strip()
 176 |      cmp_ = compare(text, span)
 177 |      turns = speaker_turns(sec, off, off + (end - start))
 178 |      return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
 179 | -            "second_pass_text": span, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 180 | +            "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 181 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 182 |              "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_S), start, end, text),
 183 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 184 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 185 | index 9642b62e..5ecca1e4 100644
 186 | --- a/pipeline/vo_fidelity.py
 187 | +++ b/pipeline/vo_fidelity.py
 188 | @@ -727,7 +727,7 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 189 |      (law L-m) and leaves the layer NOT measured."""
 190 |      import providers as P
 191 |      det = check_deterministic(segments, lines, manifest, current_levels)
 192 | -    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False}
 193 | +    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False, "seed": seed}
 194 |      r = None
 195 |      try:
 196 |          r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
 197 | @@ -743,3 +743,49 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 198 |      out["violations"] = det["violations"] + out["verdict"]["violations"]
 199 |      out["ok"] = det["ok"] and out["verdict"]["ok"]
 200 |      return out
 201 | +
 202 | +
 203 | +def majority(runs, lines):
 204 | +    """Orchestrator ruling 07:42 (3): a verdict that flips on unchanged text is run THREE times (the seed differs, the
 205 | +    text does not) and the majority decides. runs: check() results on the same segments and lines. Per line slot a
 206 | +    run votes "pass" only when it was measured and its verdict holds no violation on that slot nor on the whole reply
 207 | +    ("-"); a slot passes when more than half of the runs vote "pass" (an unmeasured run votes "fail", law L-m).
 208 | +    -> a check()-shaped result: the seed-free deterministic layer, the first run's claims, every violation of a slot
 209 | +    the majority fails (plus VERDICT_MAJORITY with the votes), "runs" (n) and "majority" = {"votes": {slot: [...]},
 210 | +    "splits": [slots whose votes differ], "runs": [per run: seed, backend, measured, replayed, ok, violations]}. A
 211 | +    split is recorded, never hidden (the ruling: recorded in the package and named in the caption)."""
 212 | +    if not runs or len(runs) % 2 == 0:
 213 | +        raise ValueError(f"majority needs an odd number of runs, got {len(runs)}")
 214 | +    votes = {}
 215 | +    for ln in lines:
 216 | +        s = ln["slot"]
 217 | +        votes[s] = ["pass" if r.get("measured") and not any(
 218 | +            v.get("slot") in (s, "-") for v in (r.get("verdict") or {}).get("violations") or []) else "fail"
 219 | +            for r in runs]
 220 | +    failed = [s for s, vs in votes.items() if 2 * vs.count("pass") <= len(runs)]
 221 | +    viol, seen = [], set()
 222 | +    for s in failed:
 223 | +        viol.append({"slot": s, "rule": "VERDICT_MAJORITY", "detail": f"votes {votes[s]} (seeds "
 224 | +                                                                        f"{[r.get('seed') for r in runs]})"})
 225 | +        for r in runs:
 226 | +            for v in (r.get("verdict") or {}).get("violations") or []:
 227 | +                k = (v.get("slot"), v.get("rule"), v.get("detail"))
 228 | +                if v.get("slot") in (s, "-") and k not in seen:
 229 | +                    seen.add(k)
 230 | +                    viol.append(v)
 231 | +    n_measured = sum(bool(r.get("measured")) for r in runs)
 232 | +    reps = [r.get("replayed") for r in runs]
 233 | +    base = runs[0]
 234 | +    verdict = {"ok": 2 * n_measured > len(runs) and not failed,
 235 | +               "claims": (base.get("verdict") or {}).get("claims") or [], "violations": viol}
 236 | +    out = {"deterministic": base["deterministic"], "verdict": verdict,
 237 | +           "backend": " / ".join(sorted({str(r.get("backend")) for r in runs})),
 238 | +           "measured": 2 * n_measured > len(runs),
 239 | +           "replayed": None if any(not isinstance(x, bool) for x in reps) else any(reps), "runs": len(runs),
 240 | +           "majority": {"votes": votes, "splits": [s for s, vs in votes.items() if len(set(vs)) > 1],
 241 | +                        "runs": [{"seed": r.get("seed"), "backend": r.get("backend"), "measured": r.get("measured"),
 242 | +                                  "replayed": r.get("replayed"), "ok": bool((r.get("verdict") or {}).get("ok")),
 243 | +                                  "violations": (r.get("verdict") or {}).get("violations") or []} for r in runs]}}
 244 | +    out["violations"] = base["deterministic"]["violations"] + viol
 245 | +    out["ok"] = base["deterministic"]["ok"] and verdict["ok"]
 246 | +    return out
 247 | diff --git a/tests/package/pin_and_verify.py b/tests/package/pin_and_verify.py
 248 | new file mode 100644
 249 | index 00000000..4a478de9
 250 | --- /dev/null
 251 | +++ b/tests/package/pin_and_verify.py
 252 | @@ -0,0 +1,71 @@
 253 | +#!/usr/bin/env python3
 254 | +"""Seal a gated package into MOMENTS_PIN.json and verify the pin against the factory AS DEPLOYED (read-only copies of
 255 | +the main tree's pinned.py, edl_rules.py and config.py in a temporary directory, as smoke_r7.py does; nothing is
 256 | +written to the main tree; no download, no Whisper, no GPU, no network).
 257 | +
 258 | +Checks on the REAL pin: package_pin.to_pin authorises it (every required gate exactly PASS, measured live, the lines
 259 | +equal the VO / title / caption); pinned.validate_schema accepts it; pinned.build_edl (moments_vo) carries the VO
 260 | +(a line after every clip, the last included), the ONE title and caption and the seal; edl_rules.rule_r4 (R4 for
 261 | +moments) passes on the pin's own segment durations.
 262 | +Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]"""
 263 | +import json
 264 | +import os
 265 | +import shutil
 266 | +import sys
 267 | +import tempfile
 268 | +
 269 | +HERE = os.path.dirname(os.path.abspath(__file__))
 270 | +REPO = os.path.dirname(os.path.dirname(HERE))
 271 | +sys.path.insert(0, HERE)
 272 | +from smoke_r7 import fake_acq  # noqa: E402
 273 | +
 274 | +
 275 | +def main(argv=None):
 276 | +    argv = argv or sys.argv[1:]
 277 | +    pkg_path, run_name, out_dir = argv[:3]
 278 | +    main_tree = argv[3] if len(argv) > 3 else "/home/ultron/protocol_pulse"
 279 | +    tmp = tempfile.mkdtemp(prefix="pp_pin_verify_")
 280 | +    try:
 281 | +        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
 282 | +                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
 283 | +        for f in ("pinned.py", "edl_rules.py", "config.py"):          # the DEPLOYED versions (read-only copies)
 284 | +            shutil.copy(os.path.join(main_tree, "pipeline", f), os.path.join(tmp, "pipeline", f))
 285 | +        sys.path.insert(0, os.path.join(tmp, "pipeline"))
 286 | +        import edl_rules
 287 | +        import package_pin
 288 | +        import pinned
 289 | +        assert os.path.dirname(pinned.__file__) == os.path.join(tmp, "pipeline")
 290 | +        pk = json.load(open(pkg_path))
 291 | +        path, pin = package_pin.write_pin(pk, run_name, out_dir)        # refuses unless every gate is exactly PASS
 292 | +        pinned.validate_schema(pin)
 293 | +        # the acquisition is faked (no download): each range's own approved words spread over its own start-end
 294 | +        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
 295 | +                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
 296 | +                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
 297 | +                                              "end_file": s["end"], "source_duration": 99999.0,
 298 | +                                              "words": a["transcript"]["words"],
 299 | +                                              "transcript_word_straddles_boundary": False,
 300 | +                                              "edge_words_from": "verify", "approved_text_similarity": 1.0}
 301 | +        pinned.L.make_lock = lambda *a, **k: {"verify": True}
 302 | +        pinned.L.sha256_file = lambda p: "0" * 64
 303 | +        edl, _, _ = pinned.build_edl(pin, fake_acq(pin))
 304 | +        mp = pin["moments_package"]
 305 | +        assert edl["vo"]["intro"] == pk["vo"]["intro"], edl["vo"]
 306 | +        assert [b["text"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges"]), edl["vo"]
 307 | +        assert [b["after_clip"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges_after_clip"]), edl["vo"]
 308 | +        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], (edl.get("title"), edl.get("caption"))
 309 | +        assert edl["moments_package_sha256"] == mp["package_sha256"] == package_pin.seal(
 310 | +            pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"])
 311 | +        for c in edl["clips"]:
 312 | +            c.setdefault("duration", round(c.get("end_file", 0) - c.get("start_file", 0), 2))
 313 | +        ok, why = edl_rules.rule_r4(edl)
 314 | +        print(f"PIN {path}\n  story_id {pin['story_id']} seal {mp['package_sha256']}")
 315 | +        print(f"  pinned.validate_schema: OK; build_edl (moments_vo): VO, title, caption, seal carried")
 316 | +        print(f"  edl_rules.rule_r4 (deployed): {'PASS' if ok else 'FAIL'}: {why}")
 317 | +        return 0 if ok else 1
 318 | +    finally:
 319 | +        shutil.rmtree(tmp, ignore_errors=True)
 320 | +
 321 | +
 322 | +if __name__ == "__main__":
 323 | +    sys.exit(main())
 324 | diff --git a/tests/package/run_given_package.py b/tests/package/run_given_package.py
 325 | index 18a35a1f..305e2bbd 100644
 326 | --- a/tests/package/run_given_package.py
 327 | +++ b/tests/package/run_given_package.py
 328 | @@ -131,13 +131,21 @@ def main(argv=None):
 329 |      ap.add_argument("--takeaway-text", help="a line fix for VO 3 (the takeaway)")
 330 |      ap.add_argument("--tag", default="", help="suffix of the output file")
 331 |      ap.add_argument("--to-does", action="store_true", help="07:25: clip_02 through 'does.'")
 332 | +    ap.add_argument("--to-existed", action="store_true", help="07:42: clip_02 = the first sentence, ending 'existed.'")
 333 | +    ap.add_argument("--title-text", help="07:42 (3): the thesis fallback's title")
 334 | +    ap.add_argument("--clip02", help="08:18: clip_02 = this store moment, as stored (an id or a unique id prefix)")
 335 | +    ap.add_argument("--precheck", action="store_true",
 336 | +                    help="08:18 item 3: step A and the second recogniser (CUTTABLE) only, then stop")
 337 | +    ap.add_argument("--verdict-runs", type=int, default=1,
 338 | +                    help="07:42 (3): run the fidelity verdict N times (seeds 7..), the majority decides")
 339 |      ap.add_argument("--xai-heimdall", action="store_true", help="07:25: Anthropic and OpenAI are out of credit")
 340 |      a = ap.parse_args(argv)
 341 |      t_start = time.time()
 342 |      led0 = json.load(open(PM.SPEND))["usd_estimate"]
 343 |      chains = CHAINS
 344 |      if a.xai_heimdall:                          # orchestrator 07:25: xAI, Heimdall and local only
 345 | -        chains = {r: [b for b in c if not b.startswith(("anthropic:", "openai:"))] for r, c in CHAINS.items()}
 346 | +        chains = {r: [b for b in c if not b.startswith(("anthropic:", "openai:", "openai_stt:"))]
 347 | +                  for r, c in CHAINS.items()}
 348 |          chains = {r: (c + ["heimdall:deepseek/deepseek-v4.1-flash"] if len(c) < 2 and r != "transcribe" else c)
 349 |                    for r, c in chains.items()}
 350 |      router = P.Router(env_path=P.ENV_PATH, record_dir=REPLIES, spend_path=PM.SPEND, limit_usd=PM.LIMIT_USD,
 351 | @@ -156,7 +164,19 @@ def main(argv=None):
 352 |          wbd = recut(by_id, sources, WBD2, 7325, w_us, 464, 464,
 353 |                      "clip_01 replaced (06:45 B): the store's sentence 464 cut at 'U.S.': the independent recogniser "
 354 |                      "ends a sentence there ('in the US. Um, you know')")
 355 | -        if a.to_does:                           # orchestrator 07:25: 'emerges' runs into 'And' with no pause
 356 | +        if sum(map(bool, (a.to_does, a.to_existed, a.clip02))) > 1:
 357 | +            raise SystemExit("--to-does, --to-existed and --clip02 are exclusive")
 358 | +        if a.clip02:                            # orchestrator 08:18: the store moment itself, not a re-cut
 359 | +            hits = [m for mid, m in by_id.items() if mid.startswith(a.clip02)]
 360 | +            if len(hits) != 1:
 361 | +                raise SystemExit(f"--clip02 {a.clip02}: {len(hits)} store moments match")
 362 | +            nat = hits[0]
 363 | +        elif a.to_existed:                        # orchestrator 07:42: the only clean end in this moment
 364 | +            nat = recut(by_id, sources, NATALIE, 1417, 1432, 108, 108,
 365 | +                        "clip_02 = the first sentence only, ending 'existed.' (07:42): the integrator's cutter finds "
 366 | +                        "the only clean end of this moment there (cut 15.02-22.04 s file time, pause + "
 367 | +                        "neighbour-clear OK, one speaker); 'does.' carries the host's 'Mm' in its tail")
 368 | +        elif a.to_does:                         # orchestrator 07:25: 'emerges' runs into 'And' with no pause
 369 |              nat = recut(by_id, sources, NATALIE, 1417, 1456, 108, 111,
 370 |                          "clip_02 extended to 'does.' (07:25): the cutter found no pause after 'emerges.'; the "
 371 |                          "recognisers and the cutter's own M19 pause test end it at 'does.'")
 372 | @@ -173,6 +193,8 @@ def main(argv=None):
 373 |          f["intro"] = dict(f["intro"], text=a.intro_text)
 374 |      if a.takeaway_text and len(f["bridges"]) > 1:
 375 |          f["bridges"][-1] = dict(f["bridges"][-1], text=a.takeaway_text)
 376 | +    if a.title_text:
 377 | +        f["title"] = dict(f["title"], text=a.title_text)
 378 |      pk = PK.assemble(f["order"], by_id, f, ctx, f"written by the orchestrator, variant {a.variant}")
 379 |      pk["vo"]["bridges_after_clip"] = list(f["after"])           # a takeaway may follow the last clip (06:00 ruling 4)
 380 |      levels = PK.current_levels(sources.values(), ctx)
 381 | @@ -195,6 +217,33 @@ def main(argv=None):
 382 |      say(f"step A ({a_backend}, {time.time() - t0:.0f} s): " + "; ".join(
 383 |          f"{lb}: fails {CI.a_failures(x) or 'none'}, speaker {x.get('speaker_is')} verified {x.get('speaker_verified')}"
 384 |          f" ({x.get('speaker_evidence')!r:.60})" for lb, x in a_by.items()))
 385 | +    if a.precheck:                              # 08:18 item 3: step A, then the second recogniser's CUTTABLE
 386 | +        pre = {"step_a": a_by, "truth": {}}
 387 | +        for sg in pk["segments"]:
 388 | +            w_, ws_ = None, None
 389 | +            for x in sorted(os.listdir(AUDIO)):
 390 | +                parts = x[:-4].rsplit("_", 2) if x.endswith(".wav") else []
 391 | +                if len(parts) == 3 and parts[0] == sg["video_id"] and int(parts[1]) / 1000.0 <= float(sg["start"]) - 1.0 \
 392 | +                        and int(parts[2]) / 1000.0 >= float(sg["end"]) + 1.0:
 393 | +                    w_, ws_ = os.path.join(AUDIO, x), int(parts[1]) / 1000.0
 394 | +                    break
 395 | +            try:
 396 | +                pre["truth"][sg["label"]] = TT.verify_segment(router, sg["video_id"], float(sg["start"]), float(sg["end"]),
 397 | +                                                              sg["text"], AUDIO, wav=w_, wav_start=ws_)
 398 | +            except Exception as e:
 399 | +                pre["truth"][sg["label"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
 400 | +            t_ = pre["truth"][sg["label"]]
 401 | +            say(f"PRECHECK {sg['label']} ({sg['moment_id']}): second pass {'PASS' if t_.get('ok') else 'FAIL'} "
 402 | +                f"({t_.get('model')}, disagree {t_.get('disagree')}, speakers {t_.get('speakers')}, err {t_.get('error')}); "
 403 | +                f"CUTTABLE {'PASS' if (t_.get('edges') or {}).get('cuttable') else 'FAIL'} IN "
 404 | +                f"{(t_.get('edges') or {}).get('in')} OUT {(t_.get('edges') or {}).get('out')}; audio {t_.get('audio')}")
 405 | +        led1 = json.load(open(PM.SPEND))["usd_estimate"]
 406 | +        say(f"PRECHECK spend ${led1 - led0:.2f} (ledger ${led1:.2f}) | wall {time.time() - t_start:.0f} s")
 407 | +        os.makedirs(OUT, exist_ok=True)
 408 | +        name = f"precheck_{a.variant}{a.tag}"
 409 | +        json.dump(pre, open(os.path.join(OUT, name + ".json"), "w"), indent=1, default=str)
 410 | +        open(os.path.join(OUT, name + ".log"), "w").write("\n".join(log) + "\n")
 411 | +        return 0
 412 |      segs_v = {}
 413 |      for sg in pk["segments"]:
 414 |          ver = a_by[sg["label"]].get("speaker_verified")
 415 | @@ -225,12 +274,14 @@ def main(argv=None):
 416 |          return PK.exclusion_for(router, by_id[sg["moment_id"]], sources, exc_cache)
 417 |  
 418 |      with ThreadPoolExecutor(max_workers=10) as ex:
 419 | -        f_fid = ex.submit(VF.check, router, segs_v, lines, AUTHOR["vendor"], 7, man, levels, AUTHOR["family"])
 420 | +        f_fid = [ex.submit(VF.check, router, segs_v, lines, AUTHOR["vendor"], 7 + k, man, levels, AUTHOR["family"])
 421 | +                 for k in range(a.verdict_runs)]                # 07:42 (3): seeds 7, 8, 9; the text is unchanged
 422 |          f_ctx = ex.submit(CI.check_contexts, router, pk, contexts, AUTHOR["vendor"], 7,
 423 |                            {lb: x for lb, x in a_by.items()}, AUTHOR["family"], True)
 424 |          f_exc = {sg["label"]: ex.submit(exclusion, sg) for sg in pk["segments"]}
 425 |          f_tru = {sg["label"]: ex.submit(truth, sg) for sg in pk["segments"]}
 426 | -        fid, ctx_ = f_fid.result(), f_ctx.result()
 427 | +        fid_runs, ctx_ = [x.result() for x in f_fid], f_ctx.result()
 428 | +        fid = VF.majority(fid_runs, lines) if a.verdict_runs > 1 else fid_runs[0]
 429 |          exc = {k: v.result() for k, v in f_exc.items()}
 430 |          tru = {}
 431 |          for k, v in f_tru.items():
 432 | @@ -250,6 +301,15 @@ def main(argv=None):
 433 |              f"{json.dumps(c.get('tests')) if c.get('class') == 'commentary' else json.dumps(c.get('support'))[:240]}")
 434 |      for v in (fid["verdict"] or {}).get("violations") or []:
 435 |          say(f"   VIOLATION {v['slot']}: {v['rule']}: {v['detail']}")
 436 | +    if fid.get("majority"):
 437 | +        mj = fid["majority"]
 438 | +        say(f"   MAJORITY of {fid['runs']} (ruling 07:42): votes {json.dumps(mj['votes'])}; splits {mj['splits'] or 'none'}")
 439 | +        for rr, run in zip(mj["runs"], fid_runs):
 440 | +            th = [(c.get("line"), c.get("supported")) for c in (run.get("verdict") or {}).get("claims") or []
 441 | +                  if c.get("line") in ("intro", "title") and c.get("class") != "commentary"]
 442 | +            say(f"   run seed {rr['seed']} ({rr['backend']}, measured {rr['measured']}, replayed {rr['replayed']}): "
 443 | +                f"{'PASS' if rr['ok'] else 'FAIL'}; thesis claims {th}; violations "
 444 | +                f"{[(v['slot'], v['rule']) for v in rr['violations']] or 'none'}")
 445 |      say(f"CONTEXT INTEGRITY (A {ctx_['backends'].get('A')}, B {ctx_['backends'].get('B')}, C "
 446 |          f"{ctx_['backends'].get('C')}): " + ("PASS" if ctx_["ok"] else "FAIL " + json.dumps(ctx_["violations"])))
 447 |      for lb, x in (ctx_.get("segments") or {}).items():
 448 | @@ -281,8 +341,24 @@ def main(argv=None):
 449 |      pk["cut_evidence"] = {lb: {"video_id": t.get("video_id"), "start": t.get("start"), "end": t.get("end"),
 450 |                                 "model": t.get("model"), "audio": t.get("audio"), "in": (t.get("edges") or {}).get("in"),
 451 |                                 "out": (t.get("edges") or {}).get("out")} for lb, t in tru.items()}
 452 | +    if a.to_existed:                            # 07:42 (1): the integrator's cut geometry is the CUTTABLE evidence
 453 | +        import hashlib
 454 | +        facts = "/home/ultron/protocol_pulse/docs/audits/parallel/integrator_RULING7_FACTS.md"
 455 | +        lb2 = pk["segments"][-1]["label"]
 456 | +        pk["cut_evidence"][lb2]["renderer_geometry"] = {
 457 | +            "source": facts, "sha256": hashlib.sha256(open(facts, "rb").read()).hexdigest(),
 458 | +            "entries": ["07:23 ET", "07:41 ET"], "file_time": "YouTube - 514.0",
 459 | +            "cut_in": 15.02, "cut_out": 22.04, "cut_youtube": [529.02, 536.04], "duration_s": 7.02,
 460 | +            "checks": "the renderer's own sentence lock (primary decode 'existed.' 21.18-21.62, next 'And' 21.94) and "
 461 | +                      "cut geometry (edge_plan + accepted_cut, main): pause + neighbour-clear OK, one speaker; the "
 462 | +                      "final '-ed' release ends 21.63, 0.41 s before the cut, in quiet",
 463 | +            "disagreement": "the integrator's second-recogniser pass on its acquired window hears a COMMA after "
 464 | +                            "'existed' ('ever existed, and it- all it has to do'); this builder's three recorded "
 465 | +                            "scribe_v1 passes (windows 527.55-540.84 / -542.50 / -545.04) hear a full stop ('existed. "
 466 | +                            "And it, all it has to do'); the integrator: not a blocker under the existing rule (the "
 467 | +                            "primary's full stop locks the edge); the orchestrator ruled 07:42 with it on file"}
 468 |      say("INVENTORY: " + "; ".join(f"{k} {v['status']}" for k, v in pk["gates"].items()))
 469 | -    pk["checks_given"] = {"fidelity": fid, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
 470 | +    pk["checks_given"] = {"fidelity": fid, "fidelity_runs": fid_runs, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
 471 |                            "coherence": coh, "r4": [r4_ok, r4_why], "runtime_ok": rt_ok, "gates": gates,
 472 |                            "step_a": a_by, "current_levels": levels, "author": AUTHOR,
 473 |                            "wall_s": round(time.time() - t_start, 1), "usd": round(led1 - led0, 4)}
 474 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 475 | index c7cdcb30..86c7c9ae 100644
 476 | --- a/tests/package/test_angles.py
 477 | +++ b/tests/package/test_angles.py
 478 | @@ -90,25 +90,29 @@ class TestAngles(unittest.TestCase):
 479 |  
 480 |  
 481 |  class TestLengthAndR4(unittest.TestCase):
 482 | -    def test_the_runtime_counts_the_signoff_once(self):
 483 | +    def test_the_runtime_is_the_factorys_own_estimate(self):
 484 |          segs = [{"duration_s": 10.0}, {"duration_s": 20.0}]
 485 | -        self.assertAlmostEqual(PK.runtime(segs, (40 + 18) / PK.WPS), 30.0 + 58 / 2.6 + PK.FIXED_S, places=2)
 486 | -        self.assertAlmostEqual(PK.FIXED_S + 18 / PK.WPS, E.TAIL_S, places=1)     # the tail = fixed + one sign-off
 487 | +        # edl_rules._r4_moments: word spans + each VO line at 2.5 w/s + 1 s pre-roll + the 14.30 s tail (sign-off inside)
 488 | +        self.assertAlmostEqual(PK.runtime(segs, ["w " * 10, "w " * 15]), 30.0 + 10 / 2.5 + 1 + 15 / 2.5 + 1 + 14.30,
 489 | +                               places=2)
 490 | +        self.assertAlmostEqual(PK.FINAL_TAIL_S, 14.30, places=2)
 491 |  
 492 |      def test_the_moments_r4_on_tonights_numbers(self):
 493 |          def pk(vo1, vo2, vo3):
 494 |              p = {"segments": [{"duration_s": 8.38, "channel": "A"}, {"duration_s": 11.24, "channel": "B"},
 495 |                                {"duration_s": 10.29, "channel": "C"}],
 496 |                   "vo": {"intro": vo1, "bridges": [vo2, vo3], "bridges_after_clip": [1, 2]}}
 497 | -            p["runtime_s_estimate"] = PK.runtime(p["segments"], (sum(len(x.split()) for x in (vo1, vo2, vo3)) + 19) / PK.WPS)
 498 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], [vo1, vo2, vo3])
 499 |              return p
 500 |          w = lambda n: " ".join(["word"] * n)
 501 | -        ok, why = PK.r4(pk(w(27), w(18), w(18)))                                  # 05:35-06:00's 63 words
 502 | -        self.assertFalse(ok)
 503 | -        self.assertIn("41.0%", why)
 504 | -        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # the rendered 42 words
 505 | +        p63 = pk(w(27), w(18), w(18))                                              # 05:35-06:00's 63 words
 506 | +        ok, why = PK.r4(p63)                  # the factory's denominator: 28.2 s of VO = 38.9 % of 72.41 s (share ok)
 507 | +        self.assertTrue(ok, why)
 508 | +        self.assertIn("38.9%", why)
 509 | +        self.assertAlmostEqual(p63["runtime_s_estimate"], 72.41, places=2)       # ... but over 70 s: the runtime gate
 510 | +        self.assertFalse(PK.RUNTIME_S[0] <= p63["runtime_s_estimate"] <= PK.RUNTIME_S[1])
 511 | +        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # 06:22's 42 words
 512 |          self.assertTrue(ok, why)
 513 | -        self.assertIn("32.6%", why)
 514 |          self.assertFalse(PK.r4(dict(pk(w(13), w(18), w(11)), vo={"intro": w(13), "bridges": [w(5), w(5)],
 515 |                                                                    "bridges_after_clip": [1, 1]}))[0])
 516 |          self.assertLessEqual(PK.min_vo_words(29.91), PK.r4_max_vo_words(29.91, 3))
 517 | @@ -203,6 +207,68 @@ class TestInventory(unittest.TestCase):
 518 |              self.assertTrue(g[row]["status"] != "PASS" or g[row]["replayed"] is not False, (row, g[row]))
 519 |              self.assertTrue(package_pin.gate_problems(g), row)
 520 |  
 521 | +    def test_a_leading_self_repair_is_part_of_the_sentence_and_nothing_else_is(self):
 522 | +        """Ruling 8 (08:29): 'path.' | 'Bit-' 'bitcoin imposes ...' (the same speaker's truncated repetition of the
 523 | +        clip's first word) is CUTTABLE at the IN and no L-v 2 disagreement. Another speaker, a fragment that is not a
 524 | +        prefix, no dash, a full repetition, two fragments, or no sentence end before it: not a self-repair."""
 525 | +        text = "Bitcoin imposes a global free market for the first time ever."
 526 | +
 527 | +        def words(rep=("Bit-",), rep_sp="s0", before="path."):
 528 | +            ws = [{"text": before, "start": 0.4, "end": 0.8, "speaker": "s0"}]
 529 | +            ws += [{"text": r, "start": 1.30 - 0.2 * (len(rep) - 1 - k), "end": 1.42 - 0.2 * (len(rep) - 1 - k),
 530 | +                    "speaker": rep_sp} for k, r in enumerate(rep)]
 531 | +            ws += [{"text": t, "start": 1.72 + 0.3 * k, "end": 1.95 + 0.3 * k, "speaker": "s0"}
 532 | +                   for k, t in enumerate(text.lower().split())]
 533 | +            return ws + [{"text": "Okay,", "start": 6.0, "end": 6.2, "speaker": "s1"}]
 534 | +
 535 | +        class R:
 536 | +            def __init__(self, ws):
 537 | +                self.ws = ws
 538 | +
 539 | +            def transcribe(self, role, wav):
 540 | +                return {"text": " ".join(w["text"] for w in self.ws), "segments": [], "words": self.ws}, \
 541 | +                    type("Rep", (), {"backend": "s", "replayed": False})()
 542 | +        run = lambda ws: TT.verify_segment(R(ws), "v", 1.5, 5.25, text, "/nonexistent", wav="w.wav", wav_start=0.0)
 543 | +        t = run(words())
 544 | +        self.assertTrue(t["edges"]["cuttable"], t["edges"])
 545 | +        self.assertEqual((t["edges"]["in"]["before"], t["edges"]["in"]["self_repair"]), ("path.", "Bit-"))
 546 | +        self.assertEqual(t["self_repair"], "Bit-")
 547 | +        self.assertTrue(t["ok"], t)
 548 | +        self.assertTrue(run(words(rep=()))["edges"]["cuttable"])                 # no false start: unchanged
 549 | +        for kw in ({"rep_sp": "s1"}, {"rep": ("Bo-",)}, {"rep": ("Bit",)}):             # not a self-repair at all
 550 | +            t = run(words(**kw))
 551 | +            self.assertFalse(t["edges"]["cuttable"], kw)
 552 | +            self.assertIsNone(t["edges"]["in"].get("self_repair"), kw)
 553 | +        for kw, before in (({"rep": ("B-", "Bit-")}, "B-"), ({"before": "and"}, "and")):   # exactly ONE token, and only
 554 | +            t = run(words(**kw))                                                           # at a sentence start
 555 | +            self.assertFalse(t["edges"]["cuttable"], kw)
 556 | +            self.assertEqual(t["edges"]["in"]["before"], before, kw)
 557 | +        # a FULL repetition is not truncated, so not a self-repair: the IN's first-word match (4 letters, unchanged
 558 | +        # before ruling 8) reads 'Bitcoin-' as the first word, and L-v 2 still counts it as a disagreement
 559 | +        t = run(words(rep=("Bitcoin-",)))
 560 | +        self.assertIsNone(t["self_repair"])
 561 | +        self.assertIsNone(t["edges"]["in"].get("self_repair"))
 562 | +        self.assertFalse(t["ok"])
 563 | +        self.assertIn("Bitcoin-", t["disagree"]["names"])
 564 | +
 565 | +    def test_the_moments_r4_share_is_45_percent(self):
 566 | +        """Ruling 9 (08:29): 45 % of the TOTAL runtime; 45.1 % is refused; the word caps are unchanged."""
 567 | +        def pk(a, b, c, segs=(8.38, 9.62, 3.50)):
 568 | +            w = lambda n: " ".join(["word"] * n)
 569 | +            p = {"segments": [{"duration_s": d} for d in segs],
 570 | +                 "vo": {"intro": w(a), "bridges": [w(b), w(c)], "bridges_after_clip": [1, 2]}}
 571 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], [w(a), w(b), w(c)])
 572 | +            return p
 573 | +        self.assertEqual(PK.R4_MOMENTS_SHARE, 0.45)
 574 | +        ok, why = PK.r4(pk(30, 18, 18))                                           # 29.4 s of 65.2 s = 45.09 %
 575 | +        self.assertFalse(ok)
 576 | +        self.assertIn("VO=45.1% of the runtime (max 45%)", why)
 577 | +        ok, why = PK.r4(pk(29, 18, 18))                                           # 29.0 s of 64.8 s = 44.75 %
 578 | +        self.assertTrue(ok, why)
 579 | +        ok, why = PK.r4(pk(13, 18, 24))                                           # 08:29's VO 3: 24 words
 580 | +        self.assertFalse(ok)
 581 | +        self.assertIn("bridge 2 24 words (max 20)", why)
 582 | +
 583 |      def test_a_second_pass_without_diarisation_is_not_ok(self):
 584 |          class R:
 585 |              def transcribe(self, role, wav):
 586 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
 587 | index a959ba4d..3f5e7b23 100644
 588 | --- a/tests/package/test_gates.py
 589 | +++ b/tests/package/test_gates.py
 590 | @@ -239,6 +239,33 @@ class TestFidelityVerdict(unittest.TestCase):
 591 |          res, _ = self.verdict(ok, lines)
 592 |          self.assertTrue(res["ok"], res["violations"])
 593 |  
 594 | +    def test_a_flipping_verdict_is_decided_by_the_majority_of_three(self):
 595 | +        """Ruling 07:42 (3): run three times, the majority decides, a 2-1 split is recorded; an unmeasured run is a
 596 | +        'fail' vote (L-m); an even number of runs is refused."""
 597 | +        good = {"claims": [self.claim("intro", self.LINES[0]["text"], "attribution", support=[
 598 | +            {"segment": "m1", "words": "found support at its 200-day moving average"}])]}
 599 | +        unsure = {"claims": [self.claim("intro", self.LINES[0]["text"], "attribution", sup="uncertain")]}
 600 | +
 601 | +        def three(*answers):
 602 | +            r = Canned(fidelity_verdict=list(answers))
 603 | +            runs = [VF.check(r, self.SEGS, self.LINES, "openai", seed=s) for s in (7, 8, 9)]
 604 | +            return VF.majority(runs, self.LINES)
 605 | +        res = three(good, unsure, good)
 606 | +        self.assertTrue(res["ok"], res["violations"])
 607 | +        self.assertEqual(res["majority"]["votes"], {"intro": ["pass", "fail", "pass"]})
 608 | +        self.assertEqual(res["majority"]["splits"], ["intro"])
 609 | +        self.assertEqual([x["seed"] for x in res["majority"]["runs"]], [7, 8, 9])
 610 | +        res = three(unsure, unsure, good)
 611 | +        self.assertFalse(res["ok"])
 612 | +        self.assertEqual([v["rule"] for v in res["violations"]], ["VERDICT_MAJORITY", "VERDICT_UNCERTAIN"])
 613 | +        res = three(good, good)                                   # the third run has no answer: unmeasured
 614 | +        self.assertTrue(res["ok"] and res["measured"])
 615 | +        self.assertEqual(res["majority"]["votes"]["intro"], ["pass", "pass", "fail"])
 616 | +        res = three(good)                                         # two unmeasured runs: never a pass
 617 | +        self.assertEqual((res["ok"], res["measured"]), (False, False))
 618 | +        with self.assertRaises(ValueError):
 619 | +            VF.majority([res, res], self.LINES)
 620 | +
 621 |      def test_no_verdict_is_a_failure_and_not_measured(self):
 622 |          res = VF.check(Canned(), self.SEGS, self.LINES, writer_vendor="openai")
 623 |          self.assertEqual((res["ok"], res["measured"]), (False, False))
 624 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging), written 07:42-08:35 ET
Nov 12 under orchestrator rulings (07:42, 08:18, 08:29). The code gates a video package before a pinned render. Laws: nothing measured
is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make something pass.

What changed, and what to check:
1. package.runtime() now mirrors the DEPLOYED factory's own estimate (edl_rules._r4_moments, main a5ec0f17: "hook +
   clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll", FINAL_TAIL_S = 14.30 with the
   sign-off inside it). It replaced the builder's own estimate (2.6 words/s, no pre-roll, FIXED_S + the sign-off),
   which ran 3-4 s lower on three VO lines. Is the mirror faithful? Do min_vo_words / r4_max_vo_words /
   content_range stay consistent with it? Does the change loosen anything beyond what the factory itself accepts?
2. vo_fidelity.majority(runs, lines) implements the orchestrator's rule: "a verdict that flips on unchanged text: run
   that one verdict three times; majority decides; a 2-1 split is recorded in the package". Check: an unmeasured run
   never counts as a pass vote; a whole-reply failure (slot "-") votes fail on every slot; an even run count is
   refused; the votes and splits reach the sealed gate inventory (package.inventory row "vo_fidelity_verdict");
   the replayed tri-state stays honest; the merged result cannot pass a slot that most runs failed.
3. The driver tests/package/run_given_package.py: --to-existed (clip_02 = store words 1417-1432, ending "existed."),
   --verdict-runs (seeds 7, 8, 9), --title-text, the renderer_geometry evidence added to cut_evidence (outside the
   seal), and the transcribe chain without OpenAI under --xai-heimdall.
4. ORCHESTRATOR RULING 8 (08:29): transcript_truth.self_repair. "A token that the second recogniser hears and the
   primary does not, which is a truncated repetition of the clip's first word by the same speaker, is a self-repair:
   not a missing sentence start and not an L-v 2 disagreement. Exactly that token and nothing else." Check edges()
   (the IN skips exactly one such token, then needs a sentence end) and verify_segment (only a LEADING self-repair is
   dropped from the L-v 2 comparison). Can anything other than one same-speaker truncated prefix slip through?
5. ORCHESTRATOR RULING 9 (08:29): the moments R4 VO share cap is 45 % (was 40 %); 60-70 s stays hard; word caps
   unchanged. Check package.R4_MOMENTS_SHARE and everything derived from it.
6. The driver's --clip02 (a store moment as stored) and --precheck (step A + the second recogniser only, then stop).
7. The tests added or changed (test_gates.py majority test; test_angles.py runtime / R4 / self-repair tests).

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".

