# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_0158
# Branch: pp-selectid
# Generated: 2026-11-15 01:59 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_0158/C1_STEP.diff (556 lines)
```
   1 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
   2 | index 73e53ca..3205447 100644
   3 | --- a/tests/package/replay110.py
   4 | +++ b/tests/package/replay110.py
   5 | @@ -105,15 +105,18 @@ def _tupled(v):
   6 |      return tuple(v) if isinstance(v, list) else v
   7 |  
   8 |  
   9 | -def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  10 | +def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep, keep_raw=False, names=None,
  11 | +               prefix="replay110"):
  12 |      """One record asked of one candidate -> its row, None (rate limited or refused by the guard: no row, a re-run asks
  13 | -    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made)."""
  14 | +    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made). RULING 111: keep_raw
  15 | +    keeps an out-of-contract answer's text in its row ("raw_text": for diagnosis only, never a verdict); names maps a
  16 | +    candidate key to its back-end's name (default: name()), and its chain is "<prefix>_<key>"."""
  17 |      p, rec, k, anchors, m = job
  18 |      if router.spent() >= stop_usd:
  19 |          return "stopped"
  20 | -    b = router.backends[name(m)]
  21 | +    b = router.backends[(names or {}).get(m) or name(m)]
  22 |      dl = router.effective_deadline(rec.get("role"), b, None)       # ruling 100: what a live call of this verdict gets
  23 | -    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": MODELS[m], "anchors": anchors,
  24 | +    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": b.model, "anchors": anchors,
  25 |             "grok_recorded_at": rec.get("recorded_at"), "grok_seconds": rec.get("seconds"), "deadline_100_s": dl,
  26 |             "cap_s": cap_s}
  27 |      try:
  28 | @@ -121,9 +124,9 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  29 |      except (ValueError, TypeError, KeyError) as e:
  30 |          row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
  31 |      t0 = time.time()
  32 | -    router.down.pop(name(m), None)                        # a failure is never a verdict: each call is tried afresh
  33 | +    router.down.pop(b.name, None)                         # a failure is never a verdict: each call is tried afresh
  34 |      try:
  35 | -        rep = router.call(f"replay110_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
  36 | +        rep = router.call(f"{prefix}_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
  37 |                            int(rec.get("seed") or 7), system=rec.get("system"), deadline_s=cap_s)
  38 |      except P.SpendLimit:
  39 |          return None
  40 | @@ -149,6 +152,8 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  41 |      except (ValueError, TypeError, KeyError) as e:
  42 |          row.update(heimdall=None, heimdall_error=f"out of contract: {type(e).__name__}: {str(e)[:160]}",
  43 |                     outcome="out_of_contract")
  44 | +        if keep_raw:                                  # ruling 111 (b): the text as it came, for diagnosis only
  45 | +            row["raw_text"] = rep.text
  46 |          router.reject(rep)
  47 |          return row
  48 |      row["outcome"] = "in_time" if dl is None or secs <= dl else "late"
  49 | @@ -222,11 +227,11 @@ def _s(x):
  50 |      return "-" if x is None else f"{x:.0f}"
  51 |  
  52 |  
  53 | -def summary(rows):
  54 | -    """-> {(type, model): figures} over the rows (one per record and model)."""
  55 | +def summary(rows, models=MODELS):
  56 | +    """-> {(type, model): figures} over the rows (one per record and model), for each key of `models`."""
  57 |      out = {}
  58 |      for k in R.DECIDING:
  59 | -        for m in MODELS:
  60 | +        for m in models:
  61 |              rs = [r for r in rows if r["type"] == k and r["model"] == m]
  62 |              if not rs:
  63 |                  continue
  64 | diff --git a/tests/package/replay111.py b/tests/package/replay111.py
  65 | new file mode 100644
  66 | index 0000000..d81b8dc
  67 | --- /dev/null
  68 | +++ b/tests/package/replay111.py
  69 | @@ -0,0 +1,330 @@
  70 | +#!/usr/bin/env python3
  71 | +"""RULING 111 (orchestrator 01:52 ET Nov 15): THE V4 FORMAT RE-TRY. Ruling 110 left the v4 abliterated
  72 | +(deepseek/deepseek-v4-flash-0731-abliterated) unmeasured: 136 of its 319 answers were not valid JSON. Here it is asked
  73 | +in the gateway's JSON mode (response_format {"type": "json_object"}) with a set reasoning_effort, on the same 319
  74 | +records (ruling 85.1's), with the same decisions, comparison and bars (replay85.decide / compare / passes) and the
  75 | +same calls, deadlines, cut, rate limits and guard (replay110.replay_one).
  76 | +THE GATEWAY (probed at 01:5x ET Nov 15): for this model it takes response_format json_object, response_format
  77 | +json_schema and reasoning_effort, so no repair re-ask is needed. json_object is used. The contracts name each prompt's
  78 | +own labels, clip keys, joins and hook ids, so a json_schema would have to be ours, made per prompt, and could steer the
  79 | +answer. Every contract check stays with the pipeline's own parsers.
  80 | +THE EFFORT: none and medium are both asked on the first SAMPLE records (ruling 85.1's order, which covers every
  81 | +verdict type). The better is kept for all 319 by choose(): the higher valid-answer rate, then the higher agreement on
  82 | +valid answers, then the lower p50.
  83 | +OUT OF CONTRACT: each such answer's text is kept in its row ("raw_text": diagnosis only, never a verdict) and named by
  84 | +shape(): empty, code fence, valid JSON with the wrong fields, prose around the JSON, truncated, invalid JSON.
  85 | +SPEND: Heimdall only, on its own ledger (tests/package/proof/SPEND_R111.json, vendor-reported). No call starts once
  86 | +the ledger holds STOP_USD: the order's cap of $0.40, less what calls in flight may still add.
  87 | +Usage: python3 -B tests/package/replay111.py [--workers 6] [--sample 40] [--table-only]"""
  88 | +import argparse
  89 | +import collections
  90 | +import json
  91 | +import os
  92 | +import statistics
  93 | +import sys
  94 | +import threading
  95 | +import time
  96 | +from concurrent.futures import ThreadPoolExecutor
  97 | +
  98 | +HERE = os.path.dirname(os.path.abspath(__file__))
  99 | +REPO = os.path.dirname(os.path.dirname(HERE))
 100 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 101 | +sys.path.insert(0, HERE)
 102 | +import deadline_table as DT  # noqa: E402
 103 | +import providers as P  # noqa: E402
 104 | +import replay85 as R  # noqa: E402
 105 | +import replay110 as RX  # noqa: E402
 106 | +
 107 | +WT = R.WT
 108 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay111")
 109 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R111.json")
 110 | +LIMIT_USD, STOP_USD, SAMPLE = 3.00, 0.38, 40
 111 | +MODEL = "deepseek/deepseek-v4-flash-0731-abliterated"
 112 | +FORMAT = {"type": "json_object"}
 113 | +VARIANTS = ("none", "medium")
 114 | +PREFIX = "replay111"
 115 | +SHAPES = ("empty", "code fence", "valid JSON, wrong fields", "prose around the JSON", "truncated", "invalid JSON")
 116 | +
 117 | +
 118 | +def bname(v):
 119 | +    return f"heimdall:{MODEL}#effort-{v}"
 120 | +
 121 | +
 122 | +class FormatBackend(P.HeimdallBackend):
 123 | +    """providers.HeimdallBackend.complete with the same body (model, max_tokens, seed, temperature, the same messages),
 124 | +    plus the gateway's JSON mode and a reasoning effort. It is copied, not inherited, because the production back-end
 125 | +    builds its body inside complete(). test_replay111 pins that the two bodies differ by those two fields only."""
 126 | +
 127 | +    def __init__(self, name, spec, env_path, effort):
 128 | +        super().__init__(name, spec, env_path)
 129 | +        self.effort = effort
 130 | +
 131 | +    def complete(self, prompt, max_tokens, seed, system=None):
 132 | +        key = self.key("HEIMDALL_API_KEY")
 133 | +        content = prompt if not P.is_vision(prompt) else \
 134 | +            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
 135 | +                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
 136 | +        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
 137 | +                "temperature": self.spec.get("temperature", 0),
 138 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
 139 | +                             {"role": "user", "content": content}],
 140 | +                "response_format": FORMAT, "reasoning_effort": self.effort}
 141 | +        t0 = time.time()
 142 | +        base = self._base()
 143 | +        j = P._with_backoff(lambda: P._http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
 144 | +                                                 self.timeout), final_codes=(401, 402, 403))
 145 | +        u = j.get("usage") or {}
 146 | +        try:
 147 | +            text = j["choices"][0]["message"].get("content") or ""
 148 | +        except (KeyError, IndexError, TypeError):
 149 | +            raise P.RequestRejected("heimdall: no choices") from None
 150 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
 151 | +                          **P._reported(u.get("cost"))), time.time() - t0
 152 | +
 153 | +
 154 | +def build_router(variants, record_dir=None, spend_path=None, deadline_log=None):
 155 | +    """replay110.build_router's Router, with one FormatBackend per effort on its own chain "replay111_<effort>"."""
 156 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 157 | +                 limit_basis=RX.LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
 158 | +                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RX.RESERVE_WAIT_S)
 159 | +    tmpl = r.config["backends"][RX.TEMPLATE]
 160 | +    for v in variants:
 161 | +        r.backends[bname(v)] = FormatBackend(bname(v), dict(tmpl, model=MODEL), r.env_path, v)
 162 | +        r.chains[f"{PREFIX}_{v}"] = [bname(v)]
 163 | +    return r
 164 | +
 165 | +
 166 | +def shape(text, out_tokens=None, cap=None):
 167 | +    """The shape of an answer the parsers refused -> one of SHAPES (the first that applies, in that order)."""
 168 | +    t = (text or "").strip()
 169 | +    if not t:
 170 | +        return "empty"
 171 | +    if t.startswith("```"):
 172 | +        return "code fence"
 173 | +    try:
 174 | +        json.loads(t)
 175 | +        return "valid JSON, wrong fields"
 176 | +    except ValueError as e:
 177 | +        pos = getattr(e, "pos", None)
 178 | +    a, b = t.find("{"), t.rfind("}")
 179 | +    if 0 <= a < b and (a > 0 or b < len(t) - 1):
 180 | +        try:
 181 | +            json.loads(t[a:b + 1])
 182 | +            return "prose around the JSON"
 183 | +        except ValueError:
 184 | +            pass
 185 | +    if (cap and out_tokens and out_tokens >= cap) or t.count("{") > t.count("}") or \
 186 | +            (pos is not None and pos >= len(t) - 1):
 187 | +        return "truncated"
 188 | +    return "invalid JSON"
 189 | +
 190 | +
 191 | +def scores(rows, v):
 192 | +    """One effort's figures over its rows: answers, valid answers, the valid-answer rate, the agreement on valid
 193 | +    answers, p50."""
 194 | +    rs = [r for r in rows if r["model"] == v]
 195 | +    ans = [r for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")]
 196 | +    ok = [r for r in ans if r.get("outcome") in ("in_time", "late")]
 197 | +    cmp_ = [c for r in ok for c in (r.get("compare") or {}).values()]
 198 | +    secs = [r["seconds"] for r in ans if isinstance(r.get("seconds"), (int, float))]
 199 | +    return {"rows": len(rs), "answers": len(ans), "valid": len(ok),
 200 | +            "valid_rate": len(ok) / len(ans) if ans else 0.0,
 201 | +            "agree_valid": cmp_.count("agree") / len(cmp_) if cmp_ else 0.0,
 202 | +            "p50_s": statistics.median(secs) if secs else None}
 203 | +
 204 | +
 205 | +def choose(rows, variants=VARIANTS):
 206 | +    """-> (the better effort, {effort: scores}): the higher valid-answer rate, then the higher agreement on valid
 207 | +    answers, then the lower p50."""
 208 | +    sc = {v: scores(rows, v) for v in variants}
 209 | +    best = max(variants, key=lambda v: (round(sc[v]["valid_rate"], 9), round(sc[v]["agree_valid"], 9),
 210 | +                                        -(sc[v]["p50_s"] if sc[v]["p50_s"] is not None else float("inf"))))
 211 | +    return best, sc
 212 | +
 213 | +
 214 | +def anchor_failures(rows):
 215 | +    """Every anchor decision (a delivered pin's own clip, line-up or line: replay85.anchor_units) Grok passed and the
 216 | +    candidate failed -> [{"record", "type", "model", "unit", "pins"}]."""
 217 | +    anchors, out = R.anchor_texts(), []
 218 | +    for r in rows:
 219 | +        for u, pins in R.anchor_units(r, anchors).items():
 220 | +            if (r.get("compare") or {}).get(u) == "stricter":
 221 | +                out.append({"record": r["record"], "type": r["type"], "model": r["model"], "unit": u, "pins": pins})
 222 | +    return out
 223 | +
 224 | +
 225 | +def ask_one(router, job, names, cap_s=RX.CAP_S):
 226 | +    """One record asked of one effort as this order asks it: replay110.replay_one on the effort's own chain, with
 227 | +    this order's stop (STOP_USD) and every out-of-contract text kept."""
 228 | +    return RX.replay_one(router, job, cap_s=cap_s, stop_usd=STOP_USD, keep_raw=True, names=names, prefix=PREFIX)
 229 | +
 230 | +
 231 | +def _pct(n, d):
 232 | +    return f"{100 * n / d:.0f}%" if d else "-"
 233 | +
 234 | +
 235 | +def _p(v):
 236 | +    return "-" if v is None else f"{v:.0f}%"
 237 | +
 238 | +
 239 | +def _rows(path):
 240 | +    rows = []
 241 | +    try:
 242 | +        with open(path) as f:
 243 | +            for line in f:
 244 | +                try:
 245 | +                    rows.append(json.loads(line))
 246 | +                except ValueError:
 247 | +                    pass
 248 | +    except OSError:
 249 | +        pass
 250 | +    return rows
 251 | +
 252 | +
 253 | +def run(args):
 254 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 255 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 256 | +    recs, missing = RX.source_records()
 257 | +    router = build_router(VARIANTS, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
 258 | +                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
 259 | +    names, lock = {v: bname(v) for v in VARIANTS}, threading.Lock()
 260 | +
 261 | +    def ask(jobs, label):
 262 | +        n = {"done": 0, "stopped": 0, "no_row": 0}
 263 | +
 264 | +        def one(job):
 265 | +            row = ask_one(router, job, names)
 266 | +            with lock:
 267 | +                if row == "stopped":
 268 | +                    n["stopped"] += 1
 269 | +                elif row is None:
 270 | +                    n["no_row"] += 1
 271 | +                else:
 272 | +                    if row.get("outcome") == "out_of_contract":
 273 | +                        cap = router.backends[names[job[4]]].max_out(int(job[1].get("max_tokens") or 2000))
 274 | +                        row["shape"] = shape(row.get("raw_text"), row.get("out_tokens"), cap)
 275 | +                    with open(res_path, "a") as f:
 276 | +                        f.write(json.dumps(row) + "\n")
 277 | +                n["done"] += 1
 278 | +                if n["done"] % 20 == 0 or n["done"] == len(jobs):
 279 | +                    print(f"  {label}: {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, "
 280 | +                          f"${router.spent():.4f} spent", flush=True)
 281 | +        with ThreadPoolExecutor(max_workers=args.workers) as ex:
 282 | +            list(ex.map(one, jobs))
 283 | +        print(f"replay111 {label}: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row",
 284 | +              flush=True)
 285 | +
 286 | +    def done():
 287 | +        return {(x["record"], x["model"]) for x in _rows(res_path) if "record" in x and "model" in x}
 288 | +
 289 | +    sample = recs[:args.sample]
 290 | +    seen = done()
 291 | +    ask([(p, r, k, a, v) for (p, r, k, a) in sample for v in VARIANTS if (os.path.relpath(p, WT), v) not in seen],
 292 | +        f"the sample ({len(sample)} records x {len(VARIANTS)} efforts)")
 293 | +    keys = {os.path.relpath(p, WT) for p, _, _, _ in sample}
 294 | +    best, sc = choose([x for x in _rows(res_path) if x.get("record") in keys])
 295 | +    with open(os.path.join(OUT, "CHOICE.json"), "w") as f:
 296 | +        json.dump({"best": best, "sample_records": len(sample), "scores": sc,
 297 | +                   "rule": "the higher valid-answer rate, then the higher agreement on valid answers, then the lower p50"},
 298 | +                  f, indent=1)
 299 | +    print(f"replay111: effort {best} kept ({json.dumps(sc)})", flush=True)
 300 | +    seen = done()
 301 | +    ask([(p, r, k, a, best) for (p, r, k, a) in recs if (os.path.relpath(p, WT), best) not in seen],
 302 | +        f"all {len(recs)} records on effort {best}")
 303 | +    table()
 304 | +
 305 | +
 306 | +def table():
 307 | +    rows = _rows(os.path.join(OUT, "RESULTS.jsonl"))
 308 | +    try:
 309 | +        with open(os.path.join(OUT, "CHOICE.json")) as f:
 310 | +            choice = json.load(f)
 311 | +    except (OSError, ValueError):
 312 | +        choice = {}
 313 | +    best = choice.get("best")
 314 | +    keys = {r["record"] for r in rows if r.get("model") == best} if best else set()
 315 | +    sample_keys = None
 316 | +    if choice.get("sample_records"):
 317 | +        recs, _ = RX.source_records()
 318 | +        sample_keys = {os.path.relpath(p, WT) for p, _, _, _ in recs[:choice["sample_records"]]}
 319 | +    full = [r for r in rows if r.get("model") == best]
 320 | +    s = RX.summary(full, models=[best]) if best else {}
 321 | +    old = RX.summary([r for r in _rows(SOURCE_110) if r.get("model") == "dsv4" and r.get("record") in keys],
 322 | +                     models=["dsv4"])
 323 | +    base = R.grok_self()
 324 | +    lines = ["# Ruling 111: the v4 abliterated in the gateway's JSON mode", "",
 325 | +             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')}. {MODEL}, response_format {json.dumps(FORMAT)}, "
 326 | +             f"reasoning_effort {best}. Ruling 85.1's records; ruling 100's deadline (the gateway's 120 s); "
 327 | +             f"{CUT_NOTE}", "",
 328 | +             "## The effort, on the sample (the first records in ruling 85.1's order)", "",
 329 | +             "| effort | rows | answers | valid | valid-answer rate | agreement on valid answers | p50 s |",
 330 | +             "|---|---|---|---|---|---|---|"]
 331 | +    for v, x in (choice.get("scores") or {}).items():
 332 | +        lines.append(f"| {v}{' (kept)' if v == best else ''} | {x['rows']} | {x['answers']} | {x['valid']} | "
 333 | +                     f"{100 * x['valid_rate']:.0f}% | {100 * x['agree_valid']:.0f}% | {RX._s(x['p50_s'])} |")
 334 | +    lines += ["", f"## All {len(keys)} records, effort {best} (ruling 110's columns, then the two this order adds)", "",
 335 | +              "| type | records | in time | late | timeouts | errors | out of contract | missed | units in time | agree | "
 336 | +              "stricter | looser | different | agree % in time | p50 s | p90 s | usd reported | VALID-ANSWER RATE | "
 337 | +              "AGREEMENT ON VALID ANSWERS | ruling 110 (no JSON mode): valid-answer rate / agreement |", "|" + "---|" * 20]
 338 | +    for (k, m), x in s.items():
 339 | +        ans = x["in_time"] + x["late"] + x["out_of_contract"]
 340 | +        o = old.get((k, "dsv4")) or {}
 341 | +        oans = o.get("in_time", 0) + o.get("late", 0) + o.get("out_of_contract", 0)
 342 | +        lines.append(f"| {k} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
 343 | +                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
 344 | +                     f"{x['looser']} | {x['different']} | {_p(x['agree_in_time_pct'])} | {RX._s(x['p50_s'])} | "
 345 | +                     f"{RX._s(x['p90_s'])} | {x['usd_reported']:.4f} | {_pct(x['in_time'] + x['late'], ans)} | "
 346 | +                     f"{_p(x['agree_all_pct'])} | {_pct(o.get('in_time', 0) + o.get('late', 0), oans)} / "
 347 | +                     f"{_p(o.get('agree_all_pct'))} |")
 348 | +    bad = [r for r in full if r.get("outcome") == "out_of_contract"]
 349 | +    shapes = collections.Counter(r.get("shape") or "unclassified" for r in bad)
 350 | +    lines += ["", f"## Out of contract: {len(bad)} answers (texts in RESULTS.jsonl and OUT_OF_CONTRACT.jsonl)", ""]
 351 | +    lines += [f"- {n} {sh}" for sh, n in shapes.most_common()] or ["- none"]
 352 | +    for k in R.DECIDING:
 353 | +        per = collections.Counter(r.get("shape") for r in bad if r["type"] == k)
 354 | +        if per:
 355 | +            lines.append(f"  - {k}: " + ", ".join(f"{n} {sh}" for sh, n in per.most_common()))
 356 | +    fails = anchor_failures(full)
 357 | +    lines += ["", f"## Anchor decisions Grok passed that it failed: {len(fails)}", ""]
 358 | +    lines += [f"- {x['type']} {x['record']} unit {x['unit']} (pins {', '.join(x['pins'])})" for x in fails] or ["- none"]
 359 | +    lines += ["", "## The bars of rulings 85/88/96, per verdict type (replay85.passes)", ""]
 360 | +    bars = {}
 361 | +    for k in R.DECIDING:
 362 | +        if (k, best) not in s:
 363 | +            continue
 364 | +        ok, why, agree, med = R.passes(full, base, k, best)
 365 | +        bars[k] = {"meets": ok, "why": why}
 366 | +        lines.append(f"- {k}: {'MEETS THE BARS' if ok else 'DOES NOT: ' + '; '.join(why)}")
 367 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 368 | +        f.write("\n".join(lines) + "\n")
 369 | +    with open(os.path.join(OUT, "OUT_OF_CONTRACT.jsonl"), "w") as f:
 370 | +        for r in bad:
 371 | +            f.write(json.dumps({k_: r.get(k_) for k_ in ("record", "type", "model", "heimdall_error", "shape",
 372 | +                                                        "out_tokens", "raw_text")}) + "\n")
 373 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 374 | +        json.dump({"choice": choice, "sample_keys": len(sample_keys or ()),
 375 | +                   "table": {f"{k}|{m}": x for (k, m), x in s.items()}, "shapes": dict(shapes),
 376 | +                   "anchor_failures": fails, "bars": bars}, f, indent=1)
 377 | +    print("\n".join(lines), flush=True)
 378 | +    return s, shapes, fails, bars
 379 | +
 380 | +
 381 | +SOURCE_110 = os.path.join(RX.OUT, "RESULTS.jsonl")
 382 | +CUT_NOTE = "each call cut at 300 s (replay110)."
 383 | +
 384 | +
 385 | +def main(argv=None):
 386 | +    ap = argparse.ArgumentParser()
 387 | +    ap.add_argument("--workers", type=int, default=6, help="calls in flight")
 388 | +    ap.add_argument("--sample", type=int, default=SAMPLE, help="the records both efforts are asked first")
 389 | +    ap.add_argument("--table-only", action="store_true")
 390 | +    a = ap.parse_args(argv)
 391 | +    if a.table_only:
 392 | +        table()
 393 | +        return 0
 394 | +    run(a)
 395 | +    return 0
 396 | +
 397 | +
 398 | +if __name__ == "__main__":
 399 | +    sys.exit(main())
 400 | diff --git a/tests/package/test_replay111.py b/tests/package/test_replay111.py
 401 | new file mode 100644
 402 | index 0000000..5bd3c96
 403 | --- /dev/null
 404 | +++ b/tests/package/test_replay111.py
 405 | @@ -0,0 +1,150 @@
 406 | +#!/usr/bin/env python3
 407 | +"""RULING 111's re-try driver (tests/package/replay111.py), offline. The v4 is asked in the gateway's JSON mode with a set
 408 | +effort, and otherwise exactly as production asks; an out-of-contract answer's text is kept and its shape named; the
 409 | +better effort is chosen by the stated rule; every anchor decision Grok passed and the candidate failed is listed."""
 410 | +import json
 411 | +import os
 412 | +import sys
 413 | +import tempfile
 414 | +import unittest
 415 | +from unittest import mock
 416 | +
 417 | +HERE = os.path.dirname(os.path.abspath(__file__))
 418 | +REPO = os.path.dirname(os.path.dirname(HERE))
 419 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 420 | +    sys.path.insert(0, os.path.join(REPO, _p))
 421 | +import providers as P  # noqa: E402
 422 | +import replay110 as RX  # noqa: E402
 423 | +import replay111 as RY  # noqa: E402
 424 | +from test_providers import Fake, router  # noqa: E402
 425 | +from test_replay110 import GROK, Timed, candidate, job  # noqa: E402
 426 | +
 427 | +SPEC = {"vendor": "heimdall", "model": RY.MODEL, "base_url": "http://gateway.invalid/api/v1",
 428 | +        "price_usd_per_1m": [3, 15], "family": "deepseek", "temperature": 0, "min_out": 16000}
 429 | +
 430 | +
 431 | +class Answer:
 432 | +    def read(self):
 433 | +        return json.dumps({"choices": [{"message": {"content": '{"ok": 1}'}}],
 434 | +                           "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001}}).encode()
 435 | +
 436 | +
 437 | +class TestTheBackend(unittest.TestCase):
 438 | +
 439 | +    def test_the_json_mode_and_the_effort_are_the_only_fields_added_to_productions_body(self):
 440 | +        bodies = []
 441 | +
 442 | +        def urlopen(req, timeout=None):
 443 | +            bodies.append(json.loads(req.data))
 444 | +            return Answer()
 445 | +        prod = P.HeimdallBackend("heimdall:" + RY.MODEL, SPEC, "/nonexistent")
 446 | +        fmt = RY.FormatBackend(RY.bname("none"), SPEC, "/nonexistent", "none")
 447 | +        for b in (prod, fmt):
 448 | +            b.key = lambda name: "test-key"
 449 | +        with mock.patch.object(P.urllib.request, "urlopen", urlopen):
 450 | +            prod.complete("the prompt", 300, 7, "the system")
 451 | +            text, usage, _ = fmt.complete("the prompt", 300, 7, "the system")
 452 | +        added = {k: bodies[1].pop(k) for k in ("response_format", "reasoning_effort")}
 453 | +        self.assertEqual(added, {"response_format": {"type": "json_object"}, "reasoning_effort": "none"})
 454 | +        self.assertEqual(bodies[1], bodies[0])                         # all else exactly as production sends it
 455 | +        self.assertEqual((text, usage["usd_reported"]), ('{"ok": 1}', 0.0001))
 456 | +
 457 | +
 458 | +class TestTheCall(unittest.TestCase):
 459 | +
 460 | +    def test_an_out_of_contract_answers_text_is_kept_only_when_asked(self):
 461 | +        with tempfile.TemporaryDirectory() as d:
 462 | +            kept = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0, keep_raw=True)
 463 | +            plain = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
 464 | +            self.assertEqual((kept["outcome"], kept["raw_text"]), ("out_of_contract", "not json"))
 465 | +            self.assertNotIn("raw_text", plain)                            # ruling 110's rows are unchanged
 466 | +
 467 | +    def test_a_named_back_end_on_its_own_chain_answers_for_its_key(self):
 468 | +        with tempfile.TemporaryDirectory() as d:
 469 | +            led = os.path.join(d, "SPEND.json")
 470 | +            json.dump({"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}, "reserved": {},
 471 | +                       "usd_reported": 0.0, "usd_unreported_estimate": 0.0}, open(led, "w"))
 472 | +            b = Fake(RY.bname("none"), "heimdall", answer=GROK, usage={"in": 10, "out": 10, "usd_reported": 0.001})
 473 | +            r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 474 | +                       routing="heimdall_first")
 475 | +            r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
 476 | +            p, rec, k, a, _ = job(d)
 477 | +            row = RX.replay_one(r, (p, rec, k, a, "none"), cap_s=2.0, names={"none": b.name}, prefix="replay111")
 478 | +            self.assertEqual((row["outcome"], row["model"], row["model_id"], b.calls), ("in_time", "none", b.model, 1))
 479 | +
 480 | +
 481 | +class TestThisOrdersCall(unittest.TestCase):
 482 | +
 483 | +    def named(self, d, spent, answer):
 484 | +        led = os.path.join(d, "SPEND.json")
 485 | +        json.dump({"usd_estimate": spent, "calls": 1, "by_backend": {}, "by_role": {}, "reserved": {},
 486 | +                   "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 487 | +        b = Fake(RY.bname("none"), "heimdall", answer=answer, usage={"in": 10, "out": 10, "usd_reported": 0.001})
 488 | +        r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 489 | +                   routing="heimdall_first")
 490 | +        r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
 491 | +        p, rec, k, a, _ = job(d)
 492 | +        return r, b, (p, rec, k, a, "none")
 493 | +
 494 | +    def test_this_orders_stop_not_ruling_110s(self):
 495 | +        for held in (0.40, RY.STOP_USD):                                # the order's cap, and its stop below it
 496 | +            with tempfile.TemporaryDirectory() as d:
 497 | +                r, b, j = self.named(d, held, GROK)
 498 | +                self.assertEqual((RY.ask_one(r, j, {"none": b.name}, cap_s=2.0), b.calls), ("stopped", 0))
 499 | +        with tempfile.TemporaryDirectory() as d:
 500 | +            r, b, j = self.named(d, RY.STOP_USD - 0.01, "not json")
 501 | +            row = RY.ask_one(r, j, {"none": b.name}, cap_s=2.0)
 502 | +            self.assertEqual((row["outcome"], row["raw_text"], b.calls), ("out_of_contract", "not json", 1))
 503 | +
 504 | +
 505 | +class TestTheShapes(unittest.TestCase):
 506 | +
 507 | +    def test_each_shape(self):
 508 | +        cases = [("", "empty"), ("   ", "empty"),
 509 | +                 ('```json\n{"a": 1}\n```', "code fence"),
 510 | +                 ('{"a": 1}', "valid JSON, wrong fields"),
 511 | +                 ('Here it is: {"a": 1} as asked.', "prose around the JSON"),
 512 | +                 ('{"a": [1, 2', "truncated"),
 513 | +                 ('{"a": "an answer cut mid-wor', "truncated"),          # the error is at the string's start
 514 | +                 ('{"a": 1 "b": 2}', "invalid JSON")]
 515 | +        for text, want in cases:
 516 | +            self.assertEqual(RY.shape(text), want, text)
 517 | +        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=16000, cap=16000), "truncated")   # at its token cap
 518 | +        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=900, cap=16000), "invalid JSON")
 519 | +
 520 | +
 521 | +def rows_of(v, valid, out_of_contract, agree, secs):
 522 | +    """`valid` in-contract answers (the first `agree` of them agree with Grok) and `out_of_contract` others."""
 523 | +    rs = [{"model": v, "outcome": "in_time", "seconds": secs,
 524 | +           "compare": {f"u{i}": "agree" if i < agree else "stricter"}} for i in range(valid)]
 525 | +    return rs + [{"model": v, "outcome": "out_of_contract", "seconds": secs} for _ in range(out_of_contract)]
 526 | +
 527 | +
 528 | +class TestTheChoice(unittest.TestCase):
 529 | +
 530 | +    def test_the_higher_valid_answer_rate_wins(self):
 531 | +        rows = rows_of("none", 9, 1, 8, 3.0) + rows_of("medium", 7, 3, 7, 3.0)
 532 | +        self.assertEqual(RY.choose(rows)[0], "none")
 533 | +
 534 | +    def test_at_the_same_rate_the_higher_agreement_wins_then_the_lower_p50(self):
 535 | +        rows = rows_of("none", 9, 1, 7, 3.0) + rows_of("medium", 9, 1, 9, 3.0)
 536 | +        self.assertEqual(RY.choose(rows)[0], "medium")
 537 | +        rows = rows_of("none", 9, 1, 9, 3.0) + rows_of("medium", 9, 1, 9, 10.0)
 538 | +        self.assertEqual(RY.choose(rows)[0], "none")
 539 | +
 540 | +
 541 | +class TestTheAnchors(unittest.TestCase):
 542 | +
 543 | +    def test_every_anchor_decision_grok_passed_and_the_candidate_failed_is_listed(self):
 544 | +        rows = [{"record": "r1", "type": "step_a", "model": "none", "compare": {"u1": "stricter", "u2": "stricter"}},
 545 | +                {"record": "r2", "type": "step_a", "model": "none", "compare": {"u1": "stricter"}},
 546 | +                {"record": "r3", "type": "step_a", "model": "none", "compare": {"u1": "agree"}}]
 547 | +        units = {"r1": {"u1": ["37c5b5f5"]}, "r2": {}, "r3": {"u1": ["0c68b589"]}}
 548 | +        with mock.patch.object(RY.R, "anchor_texts", lambda: []), \
 549 | +                mock.patch.object(RY.R, "anchor_units", lambda row, anchors: units[row["record"]]):
 550 | +            got = RY.anchor_failures(rows)
 551 | +        self.assertEqual(got, [{"record": "r1", "type": "step_a", "model": "none", "unit": "u1", "pins": ["37c5b5f5"]}])
 552 | +
 553 | +
 554 | +if __name__ == "__main__":
 555 | +    unittest.main()
 556 | 
```

---

pp-selectid, RULING 111 (orchestrator 01:52 ET Nov 15), THE V4 FORMAT RE-TRY.

THE ORDER: re-run deepseek/deepseek-v4-flash-0731-abliterated on all 319 records of ruling 85.1's replay, with the
contract enforced the gateway's way: response_format json (json_object, or json_schema if the gateway takes it) and
reasoning effort none. Try efforts none and medium on a 40-record sample first and keep the better. Keep the raw text
of every out-of-contract answer (diagnosis only, never a verdict) and report the 3 commonest failure shapes. Give
ruling 110's table, plus per verdict type the valid-answer rate, the agreement on valid answers and every anchor
decision Grok passed that it failed, and whether each type now meets the bars of 85/88/96. Heimdall only, cap $0.40,
no routing change.

THE GATEWAY (probed at 01:5x ET with three tiny calls): for this model it takes response_format json_object,
response_format json_schema and reasoning_effort (none: 1 s, no reasoning; medium: the reasoning arrives in its own
field, not in the content). No repair re-ask is needed.
json_object IS USED, NOT json_schema: the contracts name each prompt's own labels, clip keys, joins and hook ids, so a
schema would be ours, made per prompt, and could steer the answer. Every contract check stays with the pipeline's own
parsers (replay85.decide).

THE CHANGE:
1. tests/package/replay110.py (ruling 110's driver, 45455462 / 397f2760): replay_one gains keep_raw (an
   out-of-contract answer's text goes into its row as "raw_text"), names (a key -> back-end name map) and prefix
   (its chain "<prefix>_<key>"); summary gains models. The defaults are ruling 110's behaviour: its 9 tests pass
   unchanged, and a test in test_replay111 shows its rows carry no raw_text.
2. tests/package/replay111.py (new):
   - FormatBackend: providers.HeimdallBackend.complete (UNCHANGED, base pipeline/providers.py:415-434) copied, with
     response_format {"type": "json_object"} and reasoning_effort added to the body. A test pins that its body equals
     production's, minus those two fields.
   - ask_one: replay110.replay_one with this order's stop (STOP_USD $0.38, under the $0.40 cap), keep_raw and the
     effort's own chain. A test shows that at $0.40 and at $0.38 no call starts.
   - shape(): empty, code fence, valid JSON with the wrong fields, prose around the JSON, truncated (out tokens at the
     cap, more { than }, or the error at the very end), invalid JSON.
   - choose(): the higher valid-answer rate, then the higher agreement on valid answers, then the lower p50.
   - anchor_failures(): every unit replay85.anchor_units (UNCHANGED) names as an anchor's own decision, where the
     candidate is "stricter" than Grok.
   - table(): ruling 110's columns, plus the valid-answer rate, the agreement on valid answers, ruling 110's v4
     figures beside, the shapes, the anchor failures and replay85.passes per type.
   - Own ledger SPEND_R111.json, record dir proof/replay111/replies, chains replay111_none / replay111_medium (no cache
     shared with ruling 110's replies).
TESTS: tests/package/test_replay111.py (8). 12 of 12 mutations killed.

PLEASE CHECK: (1) that FormatBackend asks exactly what production asks plus the two fields; (2) shape()'s order and
rules, especially "truncated"; (3) choose()'s rule and its ties; (4) the spend stop under the $0.40 cap; (5) that
ruling 110's behaviour is unchanged by the defaults; (6) the table's arithmetic (valid-answer rate = in time + late
over in time + late + out of contract; agreement on valid answers = over every valid answer's units); (7) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
