# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261118_0758
# Branch: pp-selectid
# Generated: 2026-11-18 07:58 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261118_0758/C1_STEP.diff (233 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5bd269c..c962a66 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1764,6 +1764,24 @@ def hook_own(m):
   6 |                  rule=HOOK_OWN_RULE, **({"flagged": flag} if flag else {}))
   7 |  
   8 |  
   9 | +GRAPHIC_WORDS = {"ticker": "ticker", "crawl": "crawl", "lower_third": "lower third", "bug": "channel bug"}
  10 | +ONSET_QUIET = re.compile(r"ms of genuine quiet before the hook's first onset <")   # RULING 146 (2): G17a's shortfall
  11 | +
  12 | +
  13 | +def soft_graphics(m):
  14 | +    """RULING 146 (1), the never-empty pass: a clip whose ONLY visual refusal is the source's own on-screen graphics
  15 | +    (VP.graphics_only) plays in a package sealed 16:9 only, where nothing is cut: its visual record (this pass's copy)
  16 | +    is marked formats ['16x9'] (package_pin.formats_of then seals the package 16:9 only) and "graphics_16x9" (its
  17 | +    flag's words). -> True when it is. OUR 9:16 crop cutting burned text or a face stays HARD: no 9:16 version."""
  18 | +    import visual_pin as VP
  19 | +    v = m.get("visual") or {}
  20 | +    kinds = v.get("graphics_16x9") or VP.graphics_only(v)
  21 | +    if not kinds:
  22 | +        return False
  23 | +    m["visual"] = dict(v, formats=["16x9"], graphics_16x9=kinds)
  24 | +    return True
  25 | +
  26 | +
  27 |  def opens_16x9(m):
  28 |      """RULING 123 (2): this moment opens a package sealed formats ['16x9']: the build found no hook for both formats
  29 |      and its own frames are refused only by ruling 93's 9:16 crop (visual_pin.crop_only), still so on its sealed record.
  30 | @@ -1810,7 +1828,8 @@ def _can_open(m, pending_verdict=False):
  31 |      opens = lambda: defer or SA.opener("hook", m.get("text") or "", *sc, moments=True)[0]
  32 |      hook = (m.get("eligibility") or {}).get("hook") or {}
  33 |      elig = hook.get("ok") or (set(hook.get("reasons") or []) == {"opener"} and opens())   # the ledger had no verdict
  34 | -    if not (elig and (m.get("hook_onset") or {}).get("pass") is True and opens()):
  35 | +    on = m.get("hook_onset") or {}                      # RULING 146 (2): a measured quiet shortfall the never-empty
  36 | +    if not (elig and (on.get("pass") is True or on.get("soft") is True) and opens()):   # pass marked "soft" opens
  37 |          return False
  38 |      if "hook_rating" not in m:
  39 |          return True                                      # not rated yet: judged as before ruling 59
  40 | @@ -3485,6 +3504,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  41 |      cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}     # hook lead decides only whether it
  42 |      # may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip (audit 0710 C1, qwen)
  43 |      out["prescreen"]["trim_cut"] = trim_cut
  44 | +    for m in (cleared.values() if soft else ()):          # RULING 146 (2): G17a's quiet before the hook's first word
  45 | +        h = m.get("hook_onset") or {}                      # is SOFT in the never-empty pass (measured shortfalls only;
  46 | +        if h.get("measured") is True and h.get("pass") is not True and ONSET_QUIET.search(str(h.get("why") or "")):
  47 | +            m["hook_onset"] = dict(h, soft=True)          # a cut mid-word or an unmeasured onset stays HARD)
  48 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  49 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  50 |      for m in cleared.values():                                           # a rating is this build's own (its
  51 | @@ -3524,6 +3547,11 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  52 |                  blocked.pop(m["moment_id"], None)
  53 |                  m["visual"] = dict(m["visual"], formats=["16x9"])                     # sealed: package_pin.formats
  54 |                  m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
  55 | +    for m in (rated_open if soft else ()):                # RULING 146 (1): a hook refused only by the show's own
  56 | +        if m.get("visual_hook_block") and soft_graphics(m):    # graphics opens a package sealed 16:9 only, flagged
  57 | +            m.pop("visual_hook_block", None)
  58 | +            blocked.pop(m["moment_id"], None)
  59 | +            m["sixteen_nine_only"] = sixteen[m["moment_id"]] = "the show's own on-screen graphics (ruling 146 (1))"
  60 |      out["visual"] = out_visual
  61 |      if rated_open:
  62 |          log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
  63 | @@ -3841,7 +3869,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  64 |              return None
  65 |          see(order)                                        # RULING 70: the added clip is seen too
  66 |          vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  67 | -                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  68 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))   # included, law L-m)
  69 | +                and not (soft and soft_graphics(m))}      # RULING 146 (1): the show's own graphics, 16:9 only
  70 |          if vbad:
  71 |              note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  72 |              return None
  73 | @@ -4149,7 +4178,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  74 |                      vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  75 |                                  "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip
  76 |                              for m in segs if VP.layout_block(m.get("visual"))                  # (L-m included); the
  77 | -                            and not (m is segs[0] and opens_16x9(m))}      # cause named; ruling 123 (2): the 16:9-only
  78 | +                            and not (m is segs[0] and opens_16x9(m))       # cause named; ruling 123 (2): the 16:9-only
  79 | +                            and not (soft and soft_graphics(m))}           # RULING 146 (1): the show's own graphics
  80 |                      if vbad or segs[0].get("visual_hook_block"):                               # HOOK only
  81 |                          vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  82 |                          dropped |= set(vbad)
  83 | @@ -4628,8 +4658,18 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  84 |             if style is not None else {}),
  85 |          **({"hook_onset": dict(row(hook.get("pass") is True, "hook_onset.measure (sentence_law.edge_plan + head_tail "
  86 |                                     "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
  87 | -                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
  88 | -           if hook is not None else {}),
  89 | +                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"),
  90 | +                               **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
  91 | +                                  if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
  92 | +           if hook is not None else {}),                                                                      # (2)
  93 | +        **({"graphics": {"status": "FLAGGED", "by": "visual_pin.graphics_only (ruling 146 (1)): the show's own "
  94 | +                                                    "on-screen graphics, whole in a package sealed 16:9 only",
  95 | +                         "replayed": False, "n": len(visual), "flags": [
  96 | +                             f"The clip ({(who or {}).get(lb) or 'its channel'}) shows the show's own "
  97 | +                             f"{' / '.join(GRAPHIC_WORDS.get(k, k.replace('_', ' ')) for k in v['graphics_16x9'])}; "
  98 | +                             f"this package is 16:9 only." for lb, v in zip(labels(len(visual)), visual)
  99 | +                             if (v or {}).get("graphics_16x9")]}}
 100 | +           if soft and visual and any((v or {}).get("graphics_16x9") for v in visual) else {}),
 101 |          **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 102 |                                      "stage, moments=True: the render's clip scorer's verdicts as the integrator's "
 103 |                                      "service gave them, stand-alone only, the score alone (rulings 56, 60); without an "
 104 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 105 | index 34d7bce..0fe03dc 100644
 106 | --- a/pipeline/package_pin.py
 107 | +++ b/pipeline/package_pin.py
 108 | @@ -43,7 +43,10 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 109 |                          #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
 110 |                          #   stay HARD; the takeaway's value rows are not soft)
 111 |                          "stand_alone",                     # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 112 | -                        "pbx_exception"})                  # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 113 | +                        "pbx_exception",                   # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 114 | +                        "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
 115 | +                        #   HARD)
 116 | +                        "graphics"})                       # RULING 146 (1): the show's own graphics, 16:9 only
 117 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 118 |  REVIEW_FLAGS_MAX = 3
 119 |  EXCEPTION_GATE = "pbx_exception"   # RULING 144 (PBX 07:05 ET Nov 18): a named, logged exception to a HARD rule for ONE
 120 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 121 | index 3153ca7..401f4c0 100644
 122 | --- a/pipeline/visual_pin.py
 123 | +++ b/pipeline/visual_pin.py
 124 | @@ -345,6 +345,18 @@ def crop_only(rec):
 125 |      return "; ".join(w for w in why if w)
 126 |  
 127 |  
 128 | +def graphics_only(rec):
 129 | +    """RULING 146 (1) (orchestrator 07:55 ET Nov 18): the kinds of the source's OWN on-screen graphics (ticker, crawl,
 130 | +    lower third, bug) when they are a measured, current record's ONLY refusal (ruling 93's burned_block), else None.
 131 | +    They are refused only because OUR 9:16 crop cuts them; a package sealed 16:9 only shows them whole, so there they
 132 | +    are SOFT. A third person (ruling 70), an unmeasured or older record, or a render that cannot pass a 16:9-only pin:
 133 | +    None."""
 134 | +    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
 135 | +            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or not RENDER_16X9_ONLY:
 136 | +        return None
 137 | +    return sorted({x["kind"] for x in rec["burned_in"] if burned_block(x)}) or None
 138 | +
 139 | +
 140 |  def hook_block(rec):
 141 |      """Why this clip may not be the HOOK (ruling 70), or None."""
 142 |      if not (rec or {}).get("measured"):
 143 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 144 | index f2832ff..346acd4 100644
 145 | --- a/tests/package/test_ruling_137.py
 146 | +++ b/tests/package/test_ruling_137.py
 147 | @@ -631,6 +631,85 @@ class TestRuling144TheOneException(unittest.TestCase):
 148 |              PP.WINDOW_H = saved
 149 |  
 150 |  
 151 | +class TestRuling146(unittest.TestCase):
 152 | +    """RULING 146 (orchestrator 07:55 ET Nov 18), the never-empty pass: (1) the source's own on-screen graphics (a ticker,
 153 | +    a lower third, a bug) are SOFT in a package sealed 16:9 only, flagged in the ruling's words; (2) G17a's quiet before
 154 | +    the hook's first word is SOFT (a measured shortfall only), flagged 'The opening clip may start abruptly.'"""
 155 | +    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
 156 | +              "covers_speaker": False}
 157 | +    QUIET = "70 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame)"
 158 | +
 159 | +    def rec(self, **kw):
 160 | +        import visual_pin as VP
 161 | +        r = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [dict(self.TICKER)],
 162 | +             "third_person": {"shown": False, "how": "none", "words_negative": False}}
 163 | +        return dict(r, **kw)
 164 | +
 165 | +    def test_the_shows_own_graphics_and_what_stays_hard(self):
 166 | +        import visual_pin as VP
 167 | +        self.assertEqual(VP.graphics_only(self.rec()), ["ticker"])
 168 | +        for bad in (self.rec(measured=False), self.rec(version="old"), self.rec(burned_in=None), self.rec(burned_in=[])):
 169 | +            self.assertIsNone(VP.graphics_only(bad))
 170 | +        with mock.patch.object(VP, "hook_block", lambda r: "a third person"):
 171 | +            self.assertIsNone(VP.graphics_only(self.rec()))              # ruling 70's third person: not graphics
 172 | +        m = {"moment_id": "x", "visual": self.rec()}
 173 | +        self.assertTrue(PK.soft_graphics(m))
 174 | +        self.assertEqual((m["visual"]["formats"], m["visual"]["graphics_16x9"]), (["16x9"], ["ticker"]))
 175 | +        self.assertFalse(PK.soft_graphics({"moment_id": "y", "visual": self.rec(burned_in=[])}))
 176 | +
 177 | +    def rig(self, ms, never_empty, **kw):
 178 | +        import test_medley as TM
 179 | +        r = TM.Rig(ms, [m["moment_id"] for m in ms], [(True, [], None, TM.Rig.LINE)], [None], **kw)
 180 | +        r.build_kw = {"never_empty": never_empty}
 181 | +        return r
 182 | +
 183 | +    def test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged(self):
 184 | +        from test_moments import pm
 185 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 186 | +        import test_medley as TM
 187 | +        clean = self.rig(ms, False, visuals={"x": {"burned_in": [dict(self.TICKER)]}}).run()
 188 | +        self.assertIsNone(clean["package"])
 189 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 190 | +                   visuals={"x": {"burned_in": [dict(self.TICKER)]}},
 191 | +                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})   # the clean pass reached its line-up
 192 | +        r.build_kw = {"never_empty": True}
 193 | +        pk = r.run()["package"]
 194 | +        self.assertEqual(PP.formats_of(pk["segments"]), ["16x9"])
 195 | +        ch = next(s["channel"] for s in pk["segments"] if s["moment_id"] == "x")
 196 | +        self.assertEqual((pk["gates"]["graphics"]["status"], pk["gates"]["graphics"]["flags"]), (
 197 | +            "FLAGGED", [f"The clip ({ch}) shows the show's own ticker; this package is 16:9 only."]))
 198 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 199 | +
 200 | +    def test_a_hook_with_a_quiet_shortfall_opens_flagged(self):
 201 | +        from test_moments import pm
 202 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 203 | +        quiet = self.QUIET
 204 | +
 205 | +        def make(ne):
 206 | +            r = self.rig(ms, ne)
 207 | +            base = r.onset
 208 | +            r.onset = lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 70, "why": quiet}
 209 | +                                          if m["moment_id"] == "h" else base(m, *a, **k))
 210 | +            return r
 211 | +        self.assertIsNone(make(False).run()["package"])
 212 | +        pk = make(True).run()["package"]
 213 | +        self.assertEqual(pk["segments"][0]["moment_id"], "h")
 214 | +        self.assertEqual((pk["gates"]["hook_onset"]["status"], pk["gates"]["hook_onset"]["flags"]),
 215 | +                         ("FLAGGED", ["The opening clip may start abruptly."]))
 216 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 217 | +
 218 | +    def test_an_unmeasured_or_other_onset_failure_stays_hard(self):
 219 | +        from test_moments import pm
 220 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 221 | +        for rec in ({"pass": False, "measured": False, "why": "not measured"},
 222 | +                    {"pass": False, "measured": True, "why": "the cut lands inside a word"}):
 223 | +            r = self.rig(ms, True)
 224 | +            base = r.onset
 225 | +            r.onset = lambda m, *a, _rec=rec, **k: dict(_rec) if m["moment_id"] == "h" else base(m, *a, **k)
 226 | +            out = r.run()
 227 | +            self.assertTrue(out["package"] is None or out["package"]["segments"][0]["moment_id"] != "h", rec)
 228 | +
 229 | +
 230 |  class TestTheDayCount(unittest.TestCase):
 231 |      def test_counted_per_day_ledger(self):
 232 |          with tempfile.TemporaryDirectory() as d:
 233 | 
```

---

pp-selectid: RULING 146 (1) + (2) (orchestrator 07:55 ET Nov 18), in the NEVER-EMPTY pass only (package.build runs it
only when the clean pass sealed nothing). The approved HARD list keeps: OUR crop cutting burned text or a face, a cut
mid-word. RULED SOFT: (1) the source's OWN on-screen graphics (a ticker crawl, a 'LIVE' lower third, a channel bug) in a
package sealed 16:9 ONLY, where nothing is cut ("Ruling 93's 'a ticker is never allowed' is withdrawn for 16:9-only
packages; in 9:16 the crop rule stands"), flag "The clip (X) shows the show's own ticker / lower third; this package is
16:9 only."; (2) G17a, the quiet before the hook's first word, flag "The opening clip may start abruptly." The
integrator's render re-asks neither the ticker nor the lower third (vertical_layout's 9:16 crop only; a pin sealed
formats ['16x9'] renders and releases 16:9 only, release_auth.release_formats). It holds G17a HARD in its lock / cut
table and is making those flags (its own lockstep); its render pads room tone, so its check is the more lenient and
decides through the build's own lock pre-check. Files: pipeline/visual_pin.py, pipeline/package.py,
pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE:
(a) visual_pin.graphics_only(rec): the kinds of the burned items burned_block refuses, when a measured, current record has
    no third person (ruling 70's hook_block) and the render can pass a 16:9-only pin; else None.
(b) package.soft_graphics(m): marks the pass's own copy of the clip's visual record formats ['16x9'] (package_pin.
    formats_of then seals the WHOLE package 16:9 only, as ruling 123's hook already did) and graphics_16x9. It is used
    only when soft: at the hook stage (a hook refused only by the graphics opens), and in both clip refusals (vbad, the
    main line-up and the no-voice order). Our 9:16 crop is never made: no 9:16 version exists.
(c) G17a: in the soft pass, a hook_onset record MEASURED and failed by the quiet shortfall (its why matches "ms of genuine
    quiet before the hook's first onset <") becomes {..., soft: True}; _can_open accepts pass OR soft. Unmeasured, or any
    other failure (a cut mid-word), stays HARD.
(d) inventory: hook_onset row FLAGGED with the ruling's sentence when soft and the hook is soft; a new optional "graphics"
    row FLAGGED, one sentence per such clip with its channel. package_pin.SOFT_GATES adds hook_onset and graphics.

TESTS (4): graphics_only and soft_graphics (a third person, unmeasured, older, empty stay hard); END TO END through the
Rig: a clip whose only problem is the show's ticker seals 16:9 only with the exact sentence (the clean pass seals
nothing); a hook with a 70 ms quiet shortfall opens flagged (the clean pass seals nothing); an unmeasured or other onset
failure never opens. Mutations: 7 of 8 killed (F7, "graphics" in SOFT_GATES, is equivalent: gate_problems checks only
required rows and graphics is optional).

PLEASE CHECK: (1) can a 9:16 version ever carry a clip whose burned text our crop cuts? (2) can a third person, an
unmeasured record or a mid-word cut pass? (3) the clean pass unchanged; (4) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
