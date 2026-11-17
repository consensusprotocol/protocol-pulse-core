# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261116_2342
# Branch: pp-selectid
# Generated: 2026-11-16 23:44 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261116_2342/C1_STEP.diff (265 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 9322b8c..73dcbf9 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -180,6 +180,30 @@
   6 |     "family": "gemma",
   7 |     "deadline_floor_s": 2400,
   8 |     "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min. RULING 102 (13:02 Nov 14): also the LAST leg of step A's second family (ruling 87's last resort), reached without declaring Heimdall down; recorded as such on the pin and on STATE line 1."
   9 | +  },
  10 | +  "heimdall:minimax/minimax-m3.1-flash": {
  11 | +   "vendor": "heimdall",
  12 | +   "model": "minimax/minimax-m3.1-flash",
  13 | +   "price_usd_per_1m": [
  14 | +    3,
  15 | +    15
  16 | +   ],
  17 | +   "temperature": 0,
  18 | +   "min_out": 16000,
  19 | +   "family": "minimax",
  20 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  21 | +  },
  22 | +  "heimdall:openai/gpt-oss-20b": {
  23 | +   "vendor": "heimdall",
  24 | +   "model": "openai/gpt-oss-20b",
  25 | +   "price_usd_per_1m": [
  26 | +    3,
  27 | +    15
  28 | +   ],
  29 | +   "temperature": 0,
  30 | +   "min_out": 16000,
  31 | +   "family": "gpt-oss",
  32 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  33 |    }
  34 |   },
  35 |   "roles": {
  36 | @@ -302,6 +326,20 @@
  37 |      "elevenlabs_stt:scribe_v1"
  38 |     ],
  39 |     "what": "transcript_truth.py: law L-v 2's second, independent recognition pass with speaker turns on the selected segment's source audio (CPU fetch; no GPU, no Whisper)"
  40 | +  },
  41 | +  "coherence_panel": {
  42 | +   "chain": [
  43 | +    "heimdall:qwen/qwen3.8-27b",
  44 | +    "heimdall:minimax/minimax-m3.1-flash",
  45 | +    "heimdall:openai/gpt-oss-20b"
  46 | +   ],
  47 | +   "seeds": [
  48 | +    7,
  49 | +    8
  50 | +   ],
  51 | +   "min_members": 3,
  52 | +   "deadline_s": 900,
  53 | +   "what": "RULING 118 (2) / RULING 130 (4): the free panel measured on ruling 85.1's recorded Grok coherence verdicts (tests/package/proof/panel118/TABLE.md: qwen+minimax+gptoss TAKES: 18 units, no unit without a verdict, 94 % agreement against Grok's own 83 %, anchors 5/5), asked as the replay asked it: each member at seeds 7 and 8, the JSON-only contract line, a malformed answer re-asked once (seed + 100), 900 s; THE RULE: fewer than 3 members answering is no verdict (never a pass); the panel passes when more than half of all its answers pass the bar"
  54 |    }
  55 |   },
  56 |   "routing": {
  57 | diff --git a/pipeline/package.py b/pipeline/package.py
  58 | index c8e7874..0d4ba34 100644
  59 | --- a/pipeline/package.py
  60 | +++ b/pipeline/package.py
  61 | @@ -1874,6 +1874,75 @@ def _line_ok(tl):
  62 |      return bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4
  63 |  
  64 |  
  65 | +PANEL_CONTRACT = "Answer with the JSON object only: no code fences and no text before or after it."   # ruling 118 (2)
  66 | +
  67 | +
  68 | +def coherence_panel_spec(router):
  69 | +    """RULING 118 (2) / 130 (4): the configured coherence panel (model_providers.json role "coherence_panel": its own
  70 | +    role, so it is no verdict role whose deadline-table row would replace its deadline, and no shadow role) ->
  71 | +    {"members": the role's chain as this router has it, "seeds", "min_members", "deadline_s"}, or None (no panel
  72 | +    configured, or a router without a config: the coherence verdict is one rater's, as before)."""
  73 | +    p = ((getattr(router, "config", None) or {}).get("roles") or {}).get("coherence_panel")
  74 | +    if not isinstance(p, dict) or not p.get("chain") or not hasattr(router, "chain"):
  75 | +        return None
  76 | +    return {"members": list(router.chain("coherence_panel")), "seeds": list(p.get("seeds") or [7]),
  77 | +            "min_members": int(p.get("min_members") or 3), "deadline_s": p.get("deadline_s")}
  78 | +
  79 | +
  80 | +def coherence_by_panel(router, pk, spec, parse, prompt, labs, own, writer_vendor=None, writer_family=None):
  81 | +    """RULING 118 (2) / 130 (4): the coherence verdict of the free panel, asked as the panel replay measured it. Each
  82 | +    member (never the writers' vendor or family) at each seed, once more at seed + 100 when its answer is out of contract
  83 | +    or missing; a member with no answer at either seed casts no vote. THE RULE: fewer than spec["min_members"] members
  84 | +    answering is NO VERDICT (never a pass); the panel passes when MORE THAN HALF of all its answers pass the bar (the
  85 | +    through-line, every clip after the hook and the VO point at the bar's floors). The verdict's clips and vo_point are
  86 | +    the answers' lower medians and its through-line the first sound one, for the redo and the re-line that read them.
  87 | +    -> (ok, verdict)."""
  88 | +    import statistics
  89 | +    import providers as P
  90 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  91 | +    names = [n for n in spec["members"] if n in router.backends and router.backends[n].vendor not in wv
  92 | +             and router.backends[n].family not in wf]
  93 | +    fams = {n: router.backends[n].family for n in names}
  94 | +    votes, misses = {}, {}
  95 | +    for n in names:
  96 | +        others = {fams[o] for o in names if o != n} | wf
  97 | +        for sd in spec.get("seeds") or (7,):
  98 | +            for s in (sd, sd + 100):                     # the replay's rule: a malformed answer is asked once more
  99 | +                try:
 100 | +                    r, v = P.call_parsed(router, "coherence_panel", prompt, parse, 1200, s, system=PANEL_CONTRACT,
 101 | +                                         avoid_vendor=writer_vendor, avoid_family=others,
 102 | +                                         deadline_s=spec.get("deadline_s"))
 103 | +                except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 104 | +                    misses.setdefault(n, []).append(f"seed {s}: {type(e).__name__}: {str(e)[:160]}")
 105 | +                    continue
 106 | +                votes.setdefault(n, []).append(dict(v, backend=r.backend, seed=s,
 107 | +                                                    replayed=bool(getattr(r, "replayed", False))))
 108 | +                break
 109 | +    rec = {"members": spec["members"], "answered": sorted(votes), "misses": misses,
 110 | +           "rule": "ruling 118 (2): fewer than %d members answering is no verdict; more than half of all answers pass"
 111 | +                   % int(spec.get("min_members") or 3)}
 112 | +    if len(votes) < int(spec.get("min_members") or 3):
 113 | +        return False, {"error": f"the coherence panel gave no verdict: {len(votes)} of {len(spec['members'])} members "
 114 | +                                f"answered (ruling 118 (2): no verdict, never a pass)", "measured": False, "panel": rec}
 115 | +    fl, which, csha = lineup_floors("coherence", sorted(votes)[0])     # a Heimdall member: the standard bar
 116 | +    answers = [v for n in sorted(votes) for v in votes[n]]
 117 | +    passes = lambda v: _line_ok(v["through_line"]) and min(v["clips"].values()) >= fl["clip"] and \
 118 | +        v["vo_point"] >= fl["vo_point"]
 119 | +    rec["answers"] = [{"backend": v["backend"], "seed": v["seed"], "pass": passes(v), "clips": v["clips"],
 120 | +                       "vo_point": v["vo_point"], "through_line": v["through_line"]} for v in answers]
 121 | +    ok_panel = sum(passes(v) for v in answers) * 2 > len(answers)
 122 | +    tl = next((v["through_line"] for v in answers if _line_ok(v["through_line"])), answers[0]["through_line"])
 123 | +    v = {"through_line": tl,
 124 | +         "clips": {**({labs[0]: own["rating"]} if own else {}),
 125 | +                   **{lb: statistics.median_low([a["clips"][lb] for a in answers]) for lb in labs[1:]}},
 126 | +         "vo_point": statistics.median_low([a["vo_point"] for a in answers]),
 127 | +         "hook_own": own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): fail closed"},
 128 | +         "panel": rec}
 129 | +    ok = own is not None and own["passes"] and ok_panel
 130 | +    return ok, dict(v, backend="panel:" + "+".join(sorted(votes)), measured=True, bar=which, floors=fl,
 131 | +                    calibration_sha256=csha, replayed=any(a["replayed"] for a in answers))
 132 | +
 133 | +
 134 |  def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 135 |      """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
 136 |      (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
 137 | @@ -1884,13 +1953,18 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 138 |      labs = [sg["label"] for sg in pk["segments"]]
 139 |      own = hook_own(hook)
 140 |  
 141 | -    def parse(text):
 142 | -        v = json.loads(text.strip())
 143 | +    def parse(text, braces=False):
 144 | +        v = hook_answer(text)[0] if braces else json.loads(text.strip())   # ruling 118 (2): the panel's brace rule
 145 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 146 |                  not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
 147 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 148 |              raise ValueError("coherence verdict out of contract")
 149 |          return v
 150 | +    spec = coherence_panel_spec(router)
 151 | +    if spec is not None:                         # RULING 118 (2) / 130 (4): the free panel decides coherence
 152 | +        return coherence_by_panel(router, pk, spec, lambda t: parse(t, True), COHERENCE_PROMPT.format(
 153 | +            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])), labs, own,
 154 | +            writer_vendor, writer_family)
 155 |      try:                                         # the 20:33 order: an answer out of contract moves on (P.call_parsed)
 156 |          r, v = P.call_parsed(router, "coherence_verdict", COHERENCE_PROMPT.format(
 157 |                                   package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
 158 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 159 | index 935d77a..3fc3227 100644
 160 | --- a/tests/package/test_medley.py
 161 | +++ b/tests/package/test_medley.py
 162 | @@ -243,6 +243,102 @@ class TestClipsAloneVerdict(unittest.TestCase):
 163 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 164 |  
 165 |  
 166 | +class TestRuling130CoherencePanel(unittest.TestCase):
 167 | +    """RULING 130 (4) / RULING 118 (2): the coherence verdict of the free panel (qwen + minimax + gpt-oss), asked as the
 168 | +    panel replay measured it: each member at seeds 7 and 8 under the JSON-only contract line and 900 s, a malformed
 169 | +    answer asked once more (seed + 100), the closing-brace rule; fewer than 3 members answering is no verdict; the panel
 170 | +    passes when MORE THAN HALF of all its answers pass the bar; never the writers' vendor or family."""
 171 | +    M = ["heimdall:qwen/qwen3.8-27b", "heimdall:minimax/minimax-m3.1-flash", "heimdall:openai/gpt-oss-20b"]
 172 | +    FAM = {M[0]: "qwen", M[1]: "minimax", M[2]: "gpt-oss"}
 173 | +    GOOD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 4}, "vo_point": 4}
 174 | +    BAD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 3}, "vo_point": 2}
 175 | +
 176 | +    def router(self, answers):
 177 | +        """answers: {member: {seed: dict | str (raw text) | Exception}}; a seed with no entry raises ProviderError."""
 178 | +        import providers as P
 179 | +        calls, M, FAM = [], self.M, self.FAM
 180 | +
 181 | +        class R:
 182 | +            config = {"roles": {"coherence_panel": {"chain": M, "seeds": [7, 8], "min_members": 3, "deadline_s": 900}}}
 183 | +            backends = {n: type("B", (), {"vendor": "heimdall/" + FAM[n], "family": FAM[n]})() for n in M}
 184 | +
 185 | +            def chain(self, role, kind=None):
 186 | +                return list(M) if role == "coherence_panel" else []
 187 | +
 188 | +            def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 189 | +                     avoid_family=None, deadline_s=None, kind=None):
 190 | +                left = [n for n in M if FAM[n] not in set(avoid_family or ()) and n not in set(avoid_model or ())]
 191 | +                if role != "coherence_panel" or not left:
 192 | +                    raise P.ProviderError(f"{role}: every back-end unavailable")
 193 | +                n = left[0]
 194 | +                calls.append({"role": role, "member": n, "seed": seed, "system": system, "deadline_s": deadline_s})
 195 | +                a = (answers.get(n) or {}).get(seed)
 196 | +                if a is None or isinstance(a, Exception):
 197 | +                    raise a if isinstance(a, Exception) else P.ProviderError(f"{n}: no answer")
 198 | +                return P.Reply(a if isinstance(a, str) else json.dumps(a), n, "heimdall")
 199 | +        return R(), calls
 200 | +
 201 | +    def run_it(self, answers, writer_family=None):
 202 | +        r, calls = self.router(answers)
 203 | +        ok, v = PK.coherence(r, TestCoherenceHookRatedOnce.PK_, {"xai"}, writer_family=writer_family,
 204 | +                             hook=TestCoherenceHookRatedOnce.HOOK)
 205 | +        return ok, v, calls
 206 | +
 207 | +    def test_the_panel_passes_on_more_than_half_of_its_answers(self):
 208 | +        G, B = self.GOOD, self.BAD
 209 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}, self.M[2]: {7: B, 8: B}})
 210 | +        self.assertTrue(ok)                                            # 4 of 6 answers pass
 211 | +        self.assertEqual(v["backend"], "panel:" + "+".join(sorted(self.M)))
 212 | +        self.assertEqual(sorted((c["member"], c["seed"]) for c in calls), sorted((n, s) for n in self.M for s in (7, 8)))
 213 | +        self.assertTrue(all(c["system"] == PK.PANEL_CONTRACT and c["deadline_s"] == 900 for c in calls))
 214 | +        self.assertEqual((v["measured"], v["replayed"], v["bar"]), (True, False, "standard"))
 215 | +
 216 | +    def test_half_is_not_a_pass_and_the_fields_are_lower_medians(self):
 217 | +        G, B = self.GOOD, self.BAD
 218 | +        ok, v, _ = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: B}, self.M[2]: {7: B, 8: B}})
 219 | +        self.assertFalse(ok)                                           # 3 of 6: not more than half
 220 | +        self.assertEqual((v["clips"]["clip_02"], v["vo_point"]), (3, 2))   # the redo and the re-line read these
 221 | +        self.assertEqual(v["clips"]["hook"], 4)                        # the hook's own cached rating (ruling 61)
 222 | +
 223 | +    def test_fewer_than_three_members_answering_is_no_verdict(self):
 224 | +        G = self.GOOD
 225 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}})
 226 | +        self.assertFalse(ok)
 227 | +        self.assertFalse(v["measured"])
 228 | +        self.assertIn("no verdict", v["error"])
 229 | +        self.assertEqual(sorted(c["seed"] for c in calls if c["member"] == self.M[2]), [7, 8, 107, 108])
 230 | +
 231 | +    def test_the_writers_family_is_never_asked(self):
 232 | +        G = self.GOOD
 233 | +        ok, v, calls = self.run_it({n: {7: G, 8: G} for n in self.M}, writer_family={"qwen"})
 234 | +        self.assertNotIn(self.M[0], {c["member"] for c in calls})
 235 | +        self.assertFalse(ok)                                           # two members left: no verdict
 236 | +        self.assertIn("no verdict", v["error"])
 237 | +
 238 | +    def test_a_malformed_answer_is_asked_once_more_and_trailing_braces_are_read(self):
 239 | +        G = self.GOOD
 240 | +        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: "not json", 107: G, 8: G},
 241 | +                                    self.M[2]: {7: json.dumps(G) + "}", 8: G}})
 242 | +        self.assertTrue(ok)
 243 | +        self.assertEqual(sorted(v["panel"]["answered"]), sorted(self.M))
 244 | +        self.assertIn((self.M[1], 107), [(c["member"], c["seed"]) for c in calls])
 245 | +        read = [(a["backend"], a["seed"]) for a in v["panel"]["answers"]]
 246 | +        self.assertIn((self.M[2], 7), read)                            # the trailing brace dropped, the object read
 247 | +        self.assertIn((self.M[1], 107), read)
 248 | +
 249 | +    def test_a_router_without_the_panel_keeps_one_rater(self):
 250 | +        self.assertIsNone(PK.coherence_panel_spec(Canned(coherence_verdict=[self.GOOD])))
 251 | +
 252 | +    def test_the_configured_panel_is_the_measured_one(self):
 253 | +        """The build's own router: the role's chain resolves to back-ends it holds, of the three families measured."""
 254 | +        sys.path.insert(0, HERE)
 255 | +        import proof_ledger as PLG
 256 | +        r = PLG.build_router("heimdall_first", {}, os.devnull)
 257 | +        spec = PK.coherence_panel_spec(r)
 258 | +        self.assertEqual(sorted(r.backends[n].family for n in spec["members"]), ["gpt-oss", "minimax", "qwen"])
 259 | +        self.assertEqual((spec["seeds"], spec["min_members"], spec["deadline_s"]), ([7, 8], 3, 900))
 260 | +
 261 | +
 262 |  class TestCoherenceHookRatedOnce(unittest.TestCase):
 263 |      """RULING 61 (12:00): the coherence verdict after the takeaway does not rate the hook either: its cached own-job
 264 |      rating stands (hook_own); the clips after the hook and vo_point are judged as before."""
 265 | 
```

---

pp-selectid: RULING 130 (4) (orchestrator 23:00 ET Nov 16): "Then coherence panel wiring (ruling 118)." RULING 118 (2):
the free panel decides a verdict type only where its replay proved it (tests/package/proof/panel118/TABLE.md: on
ruling 85.1's recorded Grok coherence verdicts, qwen+minimax+gptoss TAKES: 18 units, no unit without a verdict, 94 %
agreement against Grok's own 83 %, stricter 0, looser 1, anchors 5/5; no other type took). Files: pipeline/package.py,
pipeline/model_providers.json, tests/package/test_medley.py.

THE REPLAY'S RULE, AS MEASURED (scratchpad panel118.py): each member at seeds 7 and 8, the JSON-only contract as the system
line, a malformed answer re-asked once (seed + 100), the closing-brace rule, 900 s; fewer than 3 members answering is
NO VERDICT (never a pass); the panel passes when MORE THAN HALF of all its answers (members x seeds) pass; each answer
judged on the standard bar (replay85.decide: the through-line and every rating >= COHERENCE_MIN 4).

THE CHANGE:
(a) model_providers.json: two Heimdall back-ends (minimax-m3.1-flash, gpt-oss-20b: the replay's spec), and a ROLE
    "coherence_panel" (chain: qwen, minimax, gpt-oss; seeds [7, 8]; min_members 3; deadline_s 900; its why). Its own
    role, so it is not a verdict role (whose deadline-table row would replace the 900 s: qwen's coherence row is 60 s)
    and not a shadow role. proof_ly.chains gives it its chain as for any role.
(b) package.coherence_panel_spec(router): the role's spec, or None (no such role, or a router without a config: then
    coherence() is ONE rater's, exactly as before; every existing coherence test runs that path).
(c) package.coherence_by_panel: each member never of the writers' vendor or family, at each seed, through
    providers.call_parsed on the role (one member a call: the others' families avoided), system PANEL_CONTRACT,
    deadline 900 s; out of contract or no answer: once more at seed + 100; the parse is coherence's own contract after
    package.hook_answer's brace rule (UNCHANGED, package.py:923). < min_members answering: (False, {"error": "... no
    verdict ...", "measured": False}). The bar: lineup_floors("coherence", <a member>) (UNCHANGED, :1538): the standard
    bar for a Heimdall member. ok = the hook's own cached rating passes (ruling 61, as before) and more than half of
    the answers pass. The verdict carries, for the code that reads a failed one (UNCHANGED, :4069: the takeaway's redo
    when only vo_point is under its floor; else the weak clips dropped), the answers' LOWER MEDIANS of every clip and of
    vo_point and the first sound through-line; backend "panel:<members>"; replayed only if an answer was replayed (the
    router's offline replay); measured True; every answer in v["panel"]. The pin's gate check (package_pin.gate_problems,
    UNCHANGED, :378) reads only status PASS and replayed False, never the back-end's name.

TESTS (TestRuling130CoherencePanel): more than half passes; exactly half does not, and the fields are the lower medians;
fewer than 3 members is no verdict (the missing member asked at 7, 8, 107, 108); the writers' family is never asked;
a malformed answer is asked once more and a trailing brace is read; a router without the panel keeps one rater; the
build's own router resolves the role to the three measured families. Mutations P1-P8 after a control run: 8 of 8
killed. Suites: 40 files by exit code, 863 tests.

PLEASE CHECK: (1) that the rule is the replay's, exactly (no verdict below 3 members; majority over all answers;
the standard bar); (2) that the writers' vendor and family are never asked; (3) that a failed panel verdict routes the
redo / re-line as a single rater's did; (4) that a no-verdict can never pass; (5) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
