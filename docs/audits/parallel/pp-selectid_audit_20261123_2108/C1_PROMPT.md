# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261123_2108
# Branch: pp-selectid
# Generated: 2026-11-23 21:30 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261123_2108/C1_STEP.diff (184 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index dfe1255..f4cf969 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -111,6 +111,38 @@ def flag_sentence(label, channel, code):
   6 |             f"{STEP_A_SOFT.get(code) or EDGE_WORDS[code]}."
   7 |  
   8 |  
   9 | +COUNT_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five"}
  10 | +STEP_A_SOFT_MANY = {"NOT_OWN_SINCERE": "the checker doubted each is the speaker's own sincere view (they may be quoting "
  11 | +                                       "someone or joking)",
  12 | +                    "REFERENT_OUTSIDE": "the checker thought each points back to something said before the clip starts",
  13 | +                    "CONDITION_OUTSIDE": "the checker thought each claim depends on a condition said outside the clip",
  14 | +                    "UNCERTAIN": "the checker was not sure what each speaker means"}
  15 | +EDGE_WORDS_MANY = {"EDGE_IN": "the checker heard the sentence run on into each clip's first word, so each may start "
  16 | +                              "mid-sentence",
  17 | +                   "EDGE_OUT": "the checker heard the sentence carry on past each clip's last word, so each may end "
  18 | +                               "mid-sentence"}
  19 | +
  20 | +
  21 | +def kind_sentences(pairs, who):
  22 | +    """RULING 155 (1) (orchestrator 21:06 ET Nov 23: "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code on
  23 | +    several clips is ONE flag in PBX's note, written once with the clips named"): [(label, code)] -> one sentence per
  24 | +    code, in first-seen order: one clip's flag_sentence, or for a code on several clips ONE sentence naming them all
  25 | +    ('Three clips (Strategy, Natalie Brunell, Yahoo Finance): the checker thought each points back ...')."""
  26 | +    by = {}
  27 | +    for lb, c in pairs:
  28 | +        if lb not in by.setdefault(c, []):
  29 | +            by[c].append(lb)
  30 | +    out = []
  31 | +    for c, lbs in by.items():
  32 | +        if len(lbs) == 1:
  33 | +            out.append(flag_sentence(lbs[0], (who or {}).get(lbs[0]), c))
  34 | +        else:
  35 | +            chans = ", ".join(str((who or {}).get(lb) or "its channel") for lb in lbs)
  36 | +            out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
  37 | +                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]}.")
  38 | +    return out
  39 | +
  40 | +
  41 |  def soft_edges(t):
  42 |      """RULING 137 stage 2a: a moment's CUTTABLE failure is soft only when its words match (law L-v 2 ok, measured, no
  43 |      error) and EVERY failing edge failed for the sentence running on at a word boundary (EDGE_SOFT); a word not found,
  44 | @@ -2299,8 +2331,9 @@ def seg_marks(segs):
  45 |      """RULING 141 (3): the flags a line-up's clips already carry from the never-empty pass's per-clip gates, one sentence
  46 |      each as the inventory writes them: step A's soft codes (context_a), a sentence edge (cuttable), STAND_ALONE
  47 |      (stand_alone), the hook under the calibrated bar (the medley row's hook sentence)."""
  48 | -    n = sum(len(set(m.get("step_a_flags") or [])) + len(m.get("edge_flags") or []) + bool(m.get("stand_soft"))
  49 | -            for m in segs or [])
  50 | +    segs = list(segs or [])                         # RULING 155 (1): KINDS, not clips: a code on several clips is one
  51 | +    n = len({c for m in segs for c in (m.get("step_a_flags") or [])}) + \
  52 | +        len({c for m in segs for c in (m.get("edge_flags") or [])}) + any(bool(m.get("stand_soft")) for m in segs)
  53 |      return n + bool((hook_own(segs[0]) or {}).get("flagged")) if segs else n
  54 |  
  55 |  
  56 | @@ -4668,8 +4701,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  57 |          (chain_sentences(chain, who) if chain else [])
  58 |      coh_fl = coherence_sentences(coh["soft"], chain, who) if soft and coh_ok and (coh or {}).get("soft") else []
  59 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
  60 | -    edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
  61 | -               if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
  62 | +    edge_fl = kind_sentences([(lab(mid), c) for mid, t in (truth or {}).items()   # RULING 137 2a; 155 (1): kinds
  63 | +                              if soft and (t.get("edges") or {}).get("cuttable") is not True
  64 | +                              for c in (soft_edges(t) or [])], who)
  65 |      a_rows = list((a_by or {}).values())
  66 |      lab_codes = {lb: sorted({str(c) for c in CI.a_failures(a)} | set((seg_flags or {}).get(lb) or []))   # RULING 137:
  67 |                   for lb, a in (a_by or {}).items()}       # each clip's step-A codes, its verdict's and every screen's soft
  68 | @@ -4692,8 +4726,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  69 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
  70 |                                n=len(a_rows)),
  71 |                            **({"status": "FLAGGED",            # RULING 137 stage 1; 138 (3): a sentence a clip
  72 | -                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb in (a_by or {})
  73 | -                                        for c in lab_codes[lb]]}
  74 | +                              "flags": kind_sentences([(lb, c) for lb in (a_by or {}) for c in lab_codes[lb]],
  75 | +                                                      who)}                  # RULING 155 (1): one sentence a kind
  76 |                               if soft_a and len(a_rows) >= 1 else {}),
  77 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
  78 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
  79 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  80 | index bbbba23..dd8f4bd 100644
  81 | --- a/pipeline/package_pin.py
  82 | +++ b/pipeline/package_pin.py
  83 | @@ -428,7 +428,7 @@ def review_problems(mp):
  84 |      want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
  85 |      out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
  86 |      n, cap = content_flags(mp.get("gates")), flags_cap(mp.get("gates"))
  87 | -    return out + ([f"{n} review flags, over {cap} (ruling 136 (2) / 147)"] if n > cap else [])
  88 | +    return out + ([f"{n} kinds of review flag, over {cap} (rulings 136 (2) / 147 / 155 (1))"] if n > cap else [])
  89 |  
  90 |  
  91 |  def flags_cap(gates):
  92 | @@ -437,10 +437,26 @@ def flags_cap(gates):
  93 |      return PBX_EXCEPTION_CAP if isinstance(gates, dict) and EXCEPTION_GATE in gates else REVIEW_FLAGS_MAX
  94 |  
  95 |  
  96 | +PER_CLIP_KIND = frozenset({"stand_alone", "sponsor", "graphics"})   # RULING 155 (1): one kind said once per clip
  97 | +_CLIP_REF = re.compile(r"^(?:The (?:opening|second|third|fourth|fifth) clip|A clip|The clip|[A-Z][a-z]+ clips) "
  98 | +                       r"\([^)]*\):?\s*")
  99 | +
 100 | +
 101 | +def flag_kind(gate, flag):
 102 | +    """RULING 155 (1): the KIND of one review flag: the row for a row that says one kind once per clip
 103 | +    (PER_CLIP_KIND: STAND_ALONE's per-clip sentences keep the prefix the integrator matches), else the row and the
 104 | +    sentence without the clip it names ('The second clip (Strategy): ...' and 'Three clips (...): ...' read alike)."""
 105 | +    return gate if gate in PER_CLIP_KIND else f"{gate}: {_CLIP_REF.sub('', flag).strip()}"
 106 | +
 107 | +
 108 |  def content_flags(gates):
 109 | -    """RULING 136 (2) / 144: the flags that count toward REVIEW_FLAGS_MAX: every review flag except an exception's."""
 110 | -    exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
 111 | -    return len([f for f in review_flags_of(gates) if f not in exc])
 112 | +    """RULING 136 (2) / 144 / 155 (1) (orchestrator 21:06 ET Nov 23: "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS ... At
 113 | +    most 3 KINDS per package, standing"): the KINDS of flag (flag_kind) on the FLAGGED rows that count toward the cap;
 114 | +    an exception's row never counts."""
 115 | +    if not isinstance(gates, dict):
 116 | +        return 0
 117 | +    return len({flag_kind(g, f) for g, row in gates.items() if g != EXCEPTION_GATE and isinstance(row, dict)
 118 | +                and row.get("status") == "FLAGGED" for f in row.get("flags") or [] if isinstance(f, str)})
 119 |  
 120 |  
 121 |  def gate_problems(gates, required=REQUIRED_GATES):
 122 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 123 | index fee382c..2c50916 100644
 124 | --- a/tests/package/test_ruling_137.py
 125 | +++ b/tests/package/test_ruling_137.py
 126 | @@ -208,6 +208,57 @@ class TestStage2a(unittest.TestCase):
 127 |                                                     "flags": ["a word differs"]}), "r")
 128 |  
 129 |  
 130 | +class TestRuling155FlagKinds(unittest.TestCase):
 131 | +    """RULING 155 (1) (orchestrator 21:06 ET Nov 23): "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code on
 132 | +    several clips is ONE flag in PBX's note, written once with the clips named ... At most 3 KINDS per package,
 133 | +    standing." Build 159's MicroStrategy line-ups carried REFERENT_OUTSIDE on nearly every clip."""
 134 | +    WHO = {"hook": "Natalie Brunell", "clip_01": "Strategy", "clip_02": "Yahoo Finance"}
 135 | +    MERGED = ("Three clips (Natalie Brunell, Strategy, Yahoo Finance): the checker thought each points back to "
 136 | +              "something said before the clip starts.")
 137 | +    SINCERE3 = ("The third clip (Yahoo Finance): the checker doubted this is the speaker's own sincere view (they may "
 138 | +                "be quoting someone or joking).")
 139 | +
 140 | +    def inv(self, seg_flags):
 141 | +        b = TestTheStepARow().base()
 142 | +        b["a_by"] = {lb: answer() for lb in self.WHO}
 143 | +        return PK.inventory(**b, soft=True, seg_flags=seg_flags, who=self.WHO)
 144 | +
 145 | +    def test_one_code_on_several_clips_is_one_sentence_naming_them(self):
 146 | +        a = self.inv({"hook": ["REFERENT_OUTSIDE"], "clip_01": ["REFERENT_OUTSIDE"],
 147 | +                      "clip_02": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]})["context_a"]
 148 | +        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [self.MERGED, self.SINCERE3]))
 149 | +        one = self.inv({"clip_01": ["REFERENT_OUTSIDE"]})["context_a"]
 150 | +        self.assertEqual(one["flags"], ["The second clip (Strategy): the checker thought it points back to something "
 151 | +                                        "said before the clip starts."])                  # one clip: as before
 152 | +
 153 | +    def gates(self):
 154 | +        stand = [PK.STAND_SOFT_PREFIX.format(channel=c) + f"it opens on '{w}'." for c, w in zip(self.WHO.values(),
 155 | +                                                                                                ("and", "so", "but"))]
 156 | +        return {"context_a": {"status": "FLAGGED", "flags": [self.MERGED, self.SINCERE3]},
 157 | +                "stand_alone": {"status": "FLAGGED", "flags": stand},       # one kind, said once per clip (prefix kept)
 158 | +                "medley": {"status": "FLAGGED", "flags": ["The opening clip (Natalie Brunell): the checker rated it "
 159 | +                                                          "under the hook bar (stopping the scroll 2 of 5, needs 3)."]}}
 160 | +
 161 | +    def test_the_cap_counts_kinds(self):
 162 | +        g = self.gates()
 163 | +        self.assertEqual(PP.content_flags(g), 4)                     # REFERENT_OUTSIDE, NOT_OWN_SINCERE, STAND_ALONE, hook
 164 | +        mp = {"gates": g, "review_flags": PP.review_flags_of(g)}
 165 | +        self.assertIn("4 kinds of review flag, over 3", " ".join(PP.review_problems(mp)))
 166 | +        g.pop("medley")
 167 | +        self.assertEqual(PP.content_flags(g), 3)
 168 | +        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
 169 | +        per_clip = {"context_a": {"status": "FLAGGED", "flags": [   # the old per-clip sentences of one code: one kind
 170 | +            "The second clip (A): the checker thought it points back to something said before the clip starts.",
 171 | +            "The third clip (B): the checker thought it points back to something said before the clip starts."]}}
 172 | +        self.assertEqual(PP.content_flags(per_clip), 1)
 173 | +
 174 | +    def test_the_line_up_search_counts_kinds_too(self):
 175 | +        segs = [{"step_a_flags": ["REFERENT_OUTSIDE"]}, {"step_a_flags": ["REFERENT_OUTSIDE"], "stand_soft": True},
 176 | +                {"step_a_flags": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"], "stand_soft": True,
 177 | +                 "edge_flags": ["EDGE_OUT"]}, {"edge_flags": ["EDGE_OUT"]}]
 178 | +        self.assertEqual(PK.seg_marks(segs), 4)        # REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, STAND_ALONE
 179 | +
 180 | +
 181 |  class TestStage2bHookBar(unittest.TestCase):
 182 |      """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 183 |      own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 184 | 
```

---

pp-selectid: RULING 155 (1) (orchestrator 21:06 ET Nov 23): "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code
on several clips is ONE flag in PBX's note, written once with the clips named ('Three clips refer to something said
before them: Strategy, Natalie Brunell, Yahoo Finance'). At most 3 KINDS per package, standing."
THE CHANGE (pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py):
- package.kind_sentences: [(label, code)] -> one sentence per code: a single clip keeps the unchanged flag_sentence; a
  code on several clips is ONE sentence naming their channels ('Three clips (A, B, C): the checker thought each ...').
  inventory uses it for context_a (step A's soft codes) and cuttable (the sentence-edge codes EDGE_IN / EDGE_OUT).
- package.seg_marks (the line-up search's own count of the flags a line-up's clips carry, read against chain_cap, the
  unchanged package.py:2324): distinct step A codes + distinct edge codes + 1 if ANY clip is STAND_ALONE-soft + the hook.
- package_pin.content_flags (read by the unchanged review_problems, package_pin.py:425, the pin's cap check, which the
  integrator's check_pin_only calls LIVE from this file): the number of distinct KINDS (flag_kind) over the FLAGGED
  rows, the exception row excluded as before; flag_kind = the row for a row that says one kind once per clip
  (PER_CLIP_KIND: stand_alone, sponsor, graphics; STAND_ALONE's per-clip sentences keep the exact prefix the
  integrator's batch 107 matches, package.py:4796), else the row plus the sentence with the clip reference stripped.
  review_flags_of (package_pin.py:414, the note's list) is unchanged.
TESTS (TestRuling155FlagKinds): one code on three clips is one sentence naming them, one clip as before; the cap counts
kinds (4 kinds over 3 refuse; 3 pass; the old per-clip sentences of one code count once); the search counts kinds.
Mutations 5 of 5 killed.
PLEASE CHECK: (1) can a package now carry more than 3 KINDS of flag? (2) can two DIFFERENT kinds be counted as one
(a wrong merge, or flag_kind collapsing different doubts)? (3) does anything the integrator matches by exact text change
(STAND_ALONE's prefix, the review_flags list equal to the sealed gates' flags)? (4) is the merged sentence correct for
every soft code and edge code?



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
