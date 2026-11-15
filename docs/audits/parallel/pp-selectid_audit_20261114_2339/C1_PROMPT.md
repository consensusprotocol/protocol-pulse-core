# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261114_2339
# Branch: pp-selectid
# Generated: 2026-11-14 23:40 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261114_2339/C1_STEP.diff (481 lines)
```
   1 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
   2 | new file mode 100644
   3 | index 0000000..da10481
   4 | --- /dev/null
   5 | +++ b/tests/package/replay110.py
   6 | @@ -0,0 +1,334 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 110 (orchestrator 23:32 ET Nov 14): HEIMDALL CANDIDATES. The recorded Grok verdicts of ruling 85.1's replay
   9 | +(the 319 records behind its 884 (record, model) rows: tests/package/proof/replay85/RESULTS.jsonl) are re-asked, with
  10 | +the SAME prompt, of two models the Heimdall gateway lists (GET /models, 23:3x ET Nov 14; GATEWAY_MODELS.json):
  11 | +- dsv41unc: deepseek/deepseek-v4.1-flash-1017-uncensored (the v4.1 we run, uncensored, per the Heimdall team);
  12 | +- dsv4: deepseek/deepseek-v4-flash-0731-abliterated (the ONLY DeepSeek v4, not 4.1, the gateway lists: an
  13 | +  abliterated build, not a plain v4).
  14 | +Each answer is reduced to the pipeline's own DECISION and compared with Grok's by ruling 85.1's own code
  15 | +(replay85.decide / compare / passes / grok_self). NO routing change: each candidate is a Heimdall back-end made here
  16 | +from the configured deepseek-v4.1-flash spec (model id swapped), on a chain of its own; no config file changes.
  17 | +DEADLINES (ruling 100): a call is cut at CAP_S (300 s, ruling 100's ceiling) so its latency is measured. It is IN TIME
  18 | +when it answered within the deadline ruling 100 gives a live call of that (model, verdict role) today
  19 | +(providers.Router.effective_deadline under heimdall_first: the pair's own table row, else the gateway's configured
  20 | +120 s); LATE (a missed deadline: production would have no verdict) when it answered after that, before the cap; a
  21 | +TIMEOUT when it gave no answer by the cap. Agreement is reported on the in-time answers and on every answer.
  22 | +SPEND: Heimdall only. Its own ledger (tests/package/proof/SPEND_R110.json, vendor-reported basis, an abandoned call at
  23 | +the model's own rate); no call starts once the ledger holds STOP_USD; LIMIT_USD only bounds the reservations of calls
  24 | +in flight (each holds its list-price upper bound, about $0.3), and a call that fits waits for them (reserve_wait_s).
  25 | +Replies are recorded under tests/package/proof/replay110/replies (a re-run is free); RESULTS.jsonl is appended per
  26 | +(record, model) and a re-run resumes. A rate-limited call (HTTP 429) or one refused by the guard writes no row.
  27 | +Usage: python3 -B tests/package/replay110.py [--workers 4] [--models dsv41unc,dsv4] [--limit N] [--table-only]"""
  28 | +import argparse
  29 | +import json
  30 | +import os
  31 | +import statistics
  32 | +import sys
  33 | +import threading
  34 | +import time
  35 | +from concurrent.futures import ThreadPoolExecutor
  36 | +
  37 | +HERE = os.path.dirname(os.path.abspath(__file__))
  38 | +REPO = os.path.dirname(os.path.dirname(HERE))
  39 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  40 | +sys.path.insert(0, HERE)
  41 | +import deadline_table as DT  # noqa: E402
  42 | +import providers as P  # noqa: E402
  43 | +import replay85 as R  # noqa: E402
  44 | +
  45 | +WT = R.WT
  46 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay110")
  47 | +SOURCE = os.path.join(R.OUT, "RESULTS.jsonl")
  48 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R110.json")
  49 | +LIMIT_USD, LIMIT_BASIS, STOP_USD = 3.00, "reported", 0.75
  50 | +RESERVE_WAIT_S = 600.0
  51 | +CAP_S = 300.0
  52 | +TEMPLATE = "heimdall:deepseek/deepseek-v4.1-flash"
  53 | +MODELS = {"dsv41unc": "deepseek/deepseek-v4.1-flash-1017-uncensored",
  54 | +          "dsv4": "deepseek/deepseek-v4-flash-0731-abliterated"}
  55 | +OUTCOMES = ("in_time", "late", "timeout", "error", "out_of_contract")
  56 | +
  57 | +
  58 | +def name(m):
  59 | +    return "heimdall:" + MODELS[m]
  60 | +
  61 | +
  62 | +def source_records(path=SOURCE, wt=WT):
  63 | +    """Ruling 85.1's records, once each, in its order -> ([(path, rec, kind, anchors)], [records that cannot be read or
  64 | +    no longer read as the type ruling 85.1 gave them])."""
  65 | +    seen, out, missing = set(), [], []
  66 | +    with open(path) as f:
  67 | +        for line in f:
  68 | +            try:
  69 | +                x = json.loads(line)
  70 | +            except ValueError:
  71 | +                continue
  72 | +            rel = x.get("record")
  73 | +            if not rel or rel in seen:
  74 | +                continue
  75 | +            seen.add(rel)
  76 | +            try:
  77 | +                with open(os.path.join(wt, rel)) as g:
  78 | +                    rec = json.load(g)
  79 | +            except (OSError, ValueError):
  80 | +                missing.append(rel)
  81 | +                continue
  82 | +            k = R.kind(rec)
  83 | +            if k is None or k != x.get("type"):
  84 | +                missing.append(rel)
  85 | +                continue
  86 | +            out.append((os.path.join(wt, rel), rec, k, list(x.get("anchors") or [])))
  87 | +    return out, missing
  88 | +
  89 | +
  90 | +def build_router(models, record_dir=None, spend_path=None, deadline_log=None):
  91 | +    """The production config's Router under heimdall_first (ruling 100's deadlines as a live call gets them, the table
  92 | +    read, never rewritten), each candidate a Heimdall back-end copied from TEMPLATE's spec with its model id swapped."""
  93 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
  94 | +                 limit_basis=LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
  95 | +                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RESERVE_WAIT_S)
  96 | +    tmpl = r.config["backends"][TEMPLATE]
  97 | +    for m in models:
  98 | +        r.backends[name(m)] = P.HeimdallBackend(name(m), dict(tmpl, model=MODELS[m]), r.env_path)
  99 | +        r.chains[f"replay110_{m}"] = [name(m)]
 100 | +    return r
 101 | +
 102 | +
 103 | +def _listed(d):
 104 | +    return {u: (list(v) if isinstance(v, tuple) else v) for u, v in d.items()}
 105 | +
 106 | +
 107 | +def _tupled(v):
 108 | +    return tuple(v) if isinstance(v, list) else v
 109 | +
 110 | +
 111 | +def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
 112 | +    """One record asked of one candidate -> its row, None (rate limited or refused by the guard: no row, a re-run asks
 113 | +    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made)."""
 114 | +    p, rec, k, anchors, m = job
 115 | +    if router.spent() >= stop_usd:
 116 | +        return "stopped"
 117 | +    b = router.backends[name(m)]
 118 | +    dl = router.effective_deadline(rec.get("role"), b, None)       # ruling 100: what a live call of this verdict gets
 119 | +    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": MODELS[m], "anchors": anchors,
 120 | +           "grok_recorded_at": rec.get("recorded_at"), "grok_seconds": rec.get("seconds"), "deadline_100_s": dl,
 121 | +           "cap_s": cap_s}
 122 | +    try:
 123 | +        row["grok"] = _listed(R.decide(k, rec["text"], rec["prompt"]))
 124 | +    except (ValueError, TypeError, KeyError) as e:
 125 | +        row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
 126 | +    t0 = time.time()
 127 | +    router.down.pop(name(m), None)                        # a failure is never a verdict: each call is tried afresh
 128 | +    try:
 129 | +        rep = router.call(f"replay110_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
 130 | +                          int(rec.get("seed") or 7), system=rec.get("system"), deadline_s=cap_s)
 131 | +    except P.SpendLimit:
 132 | +        return None
 133 | +    except P.ProviderError as e:
 134 | +        if "HTTP 429" in str(e):
 135 | +            sleep(30)
 136 | +            return None
 137 | +        row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
 138 | +                   f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
 139 | +        return row
 140 | +    secs = round(rep.seconds or (time.time() - t0), 2)
 141 | +    row.update(seconds=secs, cached=bool(rep.cached), usd_reported=(rep.usage or {}).get("usd_reported"),
 142 | +               usd_estimate=rep.usd, out_tokens=(rep.usage or {}).get("out"))
 143 | +    try:
 144 | +        row["heimdall"] = _listed(R.decide(k, rep.text, rec["prompt"]))
 145 | +    except (ValueError, TypeError, KeyError) as e:
 146 | +        row.update(heimdall=None, heimdall_error=f"out of contract: {type(e).__name__}: {str(e)[:160]}",
 147 | +                   outcome="out_of_contract")
 148 | +        router.reject(rep)
 149 | +        return row
 150 | +    row["outcome"] = "in_time" if dl is None or secs <= dl else "late"
 151 | +    if row.get("grok") is not None:
 152 | +        row["compare"] = {u: R.compare(k, _tupled(g), _tupled(row["heimdall"].get(u))) for u, g in row["grok"].items()}
 153 | +    return row
 154 | +
 155 | +
 156 | +def run(args):
 157 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 158 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 159 | +    done = set()
 160 | +    if os.path.exists(res_path):
 161 | +        with open(res_path) as f:
 162 | +            for line in f:
 163 | +                try:
 164 | +                    x = json.loads(line)
 165 | +                    done.add((x["record"], x["model"]))
 166 | +                except (ValueError, KeyError):
 167 | +                    pass
 168 | +    recs, missing = source_records()
 169 | +    if args.limit:
 170 | +        recs = recs[:args.limit]
 171 | +    models = [m for m in args.models if m in MODELS]
 172 | +    router = build_router(models, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
 173 | +                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
 174 | +    order, by_type = [], {}                            # round-robin by verdict type: an early table covers them all
 175 | +    for x in recs:
 176 | +        by_type.setdefault(x[2], []).append(x)
 177 | +    while any(by_type.values()):
 178 | +        for k in list(by_type):
 179 | +            if by_type[k]:
 180 | +                order.append(by_type[k].pop(0))
 181 | +    jobs = [(p, r, k, a, m) for (p, r, k, a) in order for m in models if (os.path.relpath(p, WT), m) not in done]
 182 | +    print(f"replay110: {len(recs)} records ({len(missing)} unreadable), {len(models)} models, {len(jobs)} calls to "
 183 | +          f"make ({len(done)} already in RESULTS); stop at ${STOP_USD:.2f} vendor-reported", flush=True)
 184 | +    lock, n = threading.Lock(), {"done": 0, "stopped": 0, "no_row": 0}
 185 | +
 186 | +    def one(job):
 187 | +        row = replay_one(router, job)
 188 | +        with lock:
 189 | +            if row == "stopped":
 190 | +                n["stopped"] += 1
 191 | +            elif row is None:
 192 | +                n["no_row"] += 1
 193 | +            else:
 194 | +                with open(res_path, "a") as f:
 195 | +                    f.write(json.dumps(row) + "\n")
 196 | +            n["done"] += 1
 197 | +            if n["done"] % 10 == 0 or n["done"] == len(jobs):
 198 | +                print(f"  {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, ${router.spent():.4f} spent", flush=True)
 199 | +
 200 | +    def per_model(m):                                  # one pool per model: a slow model never starves the other
 201 | +        with ThreadPoolExecutor(max_workers=args.workers) as ex:
 202 | +            list(ex.map(one, [j for j in jobs if j[4] == m]))
 203 | +    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
 204 | +    for t in ts:
 205 | +        t.start()
 206 | +    for t in ts:
 207 | +        t.join()
 208 | +    print(f"replay110: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row (rate "
 209 | +          f"limited or refused by the guard: a re-run asks them again)", flush=True)
 210 | +    table()
 211 | +
 212 | +
 213 | +def _pct(xs, q):
 214 | +    return DT.percentile(xs, q) if xs else None
 215 | +
 216 | +
 217 | +def _s(x):
 218 | +    return "-" if x is None else f"{x:.0f}"
 219 | +
 220 | +
 221 | +def summary(rows):
 222 | +    """-> {(type, model): figures} over the rows (one per record and model)."""
 223 | +    out = {}
 224 | +    for k in R.DECIDING:
 225 | +        for m in MODELS:
 226 | +            rs = [r for r in rows if r["type"] == k and r["model"] == m]
 227 | +            if not rs:
 228 | +                continue
 229 | +            by = {o: [r for r in rs if r.get("outcome") == o] for o in OUTCOMES}
 230 | +            cin = [c for r in by["in_time"] for c in (r.get("compare") or {}).values()]
 231 | +            call = [c for r in rs for c in (r.get("compare") or {}).values()]
 232 | +            secs = [r["seconds"] for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")
 233 | +                    and isinstance(r.get("seconds"), (int, float))]
 234 | +            out[(k, m)] = {
 235 | +                "records": len(rs), **{o: len(v) for o, v in by.items()},
 236 | +                "missed": len(by["late"]) + len(by["timeout"]),
 237 | +                "units_in_time": len(cin), **{x: cin.count(x) for x in ("agree", "stricter", "looser", "different")},
 238 | +                "agree_in_time_pct": 100 * cin.count("agree") / len(cin) if cin else None,
 239 | +                "units_all": len(call), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
 240 | +                "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
 241 | +                "deadline_100_s": sorted({r.get("deadline_100_s") for r in rs}, key=str),
 242 | +                "usd_reported": round(sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported"))
 243 | +                                          and not r.get("cached")), 6)}
 244 | +    return out
 245 | +
 246 | +
 247 | +def incumbent(records):
 248 | +    """Ruling 85.1's own rows for the deepseek-v4.1-flash we run, on the same records (its run: 300 s cut, 01:06 ET
 249 | +    Nov 14, under the 429 storms of that night) -> {type: figures}."""
 250 | +    out = {}
 251 | +    try:
 252 | +        with open(SOURCE) as f:
 253 | +            rows = [json.loads(x) for x in f if x.strip()]
 254 | +    except (OSError, ValueError):
 255 | +        return out
 256 | +    for k in R.DECIDING:
 257 | +        rs = [r for r in rows if r.get("type") == k and r.get("model") == "deepseek" and r.get("record") in records]
 258 | +        if not rs:
 259 | +            continue
 260 | +        call = [c for r in rs for c in (r.get("compare") or {}).values()]
 261 | +        secs = [r["seconds"] for r in rs if r.get("heimdall") is not None and isinstance(r.get("seconds"), (int, float))]
 262 | +        out[k] = {"records": len(rs), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
 263 | +                  "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
 264 | +                  "timeouts": sum(1 for r in rs if "abandoned at the deadline" in str(r.get("heimdall_error")))}
 265 | +    return out
 266 | +
 267 | +
 268 | +def table():
 269 | +    rows = []
 270 | +    try:
 271 | +        with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
 272 | +            for line in f:
 273 | +                try:
 274 | +                    rows.append(json.loads(line))
 275 | +                except ValueError:
 276 | +                    pass
 277 | +    except OSError:
 278 | +        pass
 279 | +    s = summary(rows)
 280 | +    inc = incumbent({r["record"] for r in rows})
 281 | +    base = R.grok_self()
 282 | +    lines = ["# Ruling 110: Heimdall candidates on ruling 85.1's recorded Grok verdicts", "",
 283 | +             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. "
 284 | +             + "; ".join(f"{m} = {MODELS[m]}" for m in MODELS) + ". In time: answered within ruling 100's deadline "
 285 | +             "for that (model, verdict role) today; late: answered after it (a MISSED deadline in production), before "
 286 | +             f"the {CAP_S:.0f} s cut; timeout: no answer by the cut. Stricter: the candidate fails what Grok passed.", "",
 287 | +             "| type | model | records | in time | late | timeouts | errors | out of contract | missed | units in time | "
 288 | +             "agree | stricter | looser | different | agree % in time | agree % all answers | p50 s | p90 s | "
 289 | +             "ruling-100 deadline s | usd reported |", "|" + "---|" * 20]
 290 | +    for (k, m), x in s.items():
 291 | +        lines.append(f"| {k} | {m} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
 292 | +                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
 293 | +                     f"{x['looser']} | {x['different']} | {_s(x['agree_in_time_pct'])} | {_s(x['agree_all_pct'])} | "
 294 | +                     f"{_s(x['p50_s'])} | {_s(x['p90_s'])} | {', '.join(_s(d) for d in x['deadline_100_s'])} | "
 295 | +                     f"{x['usd_reported']:.4f} |")
 296 | +    lines += ["", "## The deepseek-v4.1-flash we run, on the same records (ruling 85.1's rows: 300 s cut, 01:06 ET "
 297 | +              "Nov 14, under that night's 429 storms)", "",
 298 | +              "| type | records | agree % all answers | p50 s | p90 s | timeouts |", "|---|---|---|---|---|---|"]
 299 | +    for k, x in inc.items():
 300 | +        lines.append(f"| {k} | {x['records']} | {_s(x['agree_all_pct'])} | {_s(x['p50_s'])} | {_s(x['p90_s'])} | "
 301 | +                     f"{x['timeouts']} |")
 302 | +    lines += ["", "## The bars of rulings 85/88/96 (replay85.passes; information only: a model moves into a verdict "
 303 | +              "type only by a later ruling)", ""]
 304 | +    for k in R.DECIDING:
 305 | +        for m in MODELS:
 306 | +            if (k, m) not in s:
 307 | +                continue
 308 | +            ok, why, agree, med = R.passes(rows, base, k, m)
 309 | +            lines.append(f"- {k} / {m}: {'MEETS THE BARS' if ok else 'not: ' + '; '.join(why)}")
 310 | +    lines += ["", "## The baseline: Grok against Grok (replay85.grok_self, from every recorded Grok answer)", "",
 311 | +              "| type | unit pairs | agree % |", "|---|---|---|"]
 312 | +    for k in R.DECIDING:
 313 | +        b = base.get(k)
 314 | +        if b:
 315 | +            lines.append(f"| {k} | {b['pairs']} | {100 * b['agree'] / b['pairs']:.0f} |")
 316 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 317 | +        f.write("\n".join(lines) + "\n")
 318 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 319 | +        json.dump({f"{k}|{m}": x for (k, m), x in s.items()}, f, indent=1)
 320 | +    print("\n".join(lines[:4 + len(s) + 2]), flush=True)
 321 | +    return s
 322 | +
 323 | +
 324 | +def main(argv=None):
 325 | +    ap = argparse.ArgumentParser()
 326 | +    ap.add_argument("--workers", type=int, default=4, help="calls in flight per model")
 327 | +    ap.add_argument("--models", default=",".join(MODELS))
 328 | +    ap.add_argument("--limit", type=int, default=0, help="the first N records only (a pilot)")
 329 | +    ap.add_argument("--table-only", action="store_true")
 330 | +    a = ap.parse_args(argv)
 331 | +    a.models = [m for m in a.models.split(",") if m]
 332 | +    if a.table_only:
 333 | +        table()
 334 | +        return 0
 335 | +    run(a)
 336 | +    return 0
 337 | +
 338 | +
 339 | +if __name__ == "__main__":
 340 | +    sys.exit(main())
 341 | diff --git a/tests/package/test_replay110.py b/tests/package/test_replay110.py
 342 | new file mode 100644
 343 | index 0000000..69cc2a3
 344 | --- /dev/null
 345 | +++ b/tests/package/test_replay110.py
 346 | @@ -0,0 +1,134 @@
 347 | +#!/usr/bin/env python3
 348 | +"""RULING 110's replay driver (tests/package/replay110.py), offline: fake candidates on the real Router, ruling 100's
 349 | +deadline as the Router gives it, replay85's own decisions. A call is in time, late (a missed deadline), a timeout, an
 350 | +error or out of contract; a rate limit writes no row; the spend stop makes no call; the record set is ruling 85.1's."""
 351 | +import json
 352 | +import os
 353 | +import sys
 354 | +import tempfile
 355 | +import time
 356 | +import unittest
 357 | +
 358 | +HERE = os.path.dirname(os.path.abspath(__file__))
 359 | +REPO = os.path.dirname(os.path.dirname(HERE))
 360 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 361 | +    sys.path.insert(0, os.path.join(REPO, _p))
 362 | +import providers as P  # noqa: E402
 363 | +import replay110 as RX  # noqa: E402
 364 | +from test_gates import a_item  # noqa: E402
 365 | +from test_providers import Fake, router  # noqa: E402
 366 | +
 367 | +M = "dsv41unc"
 368 | +PROMPT = '<excerpt label="m1">Bitcoin is a savings technology.</excerpt>'
 369 | +GROK = json.dumps({"excerpts": [a_item("m1")]})
 370 | +FAILS = json.dumps({"excerpts": [a_item("m1", view="quoting_other")]})
 371 | +
 372 | +
 373 | +class Timed(Fake):
 374 | +    """A candidate that answers after `delay` seconds and reports that time, as a live back-end does."""
 375 | +
 376 | +    def __init__(self, answer, delay=0.0, fail=None):
 377 | +        super().__init__(RX.name(M), "heimdall", answer=answer, fail=fail,
 378 | +                         usage={"in": 100, "out": 10, "usd_reported": 0.001})
 379 | +        self.delay = delay
 380 | +
 381 | +    def complete(self, prompt, max_tokens, seed, system=None):
 382 | +        time.sleep(self.delay)
 383 | +        text, usage, _ = super().complete(prompt, max_tokens, seed, system)
 384 | +        return text, usage, self.delay
 385 | +
 386 | +
 387 | +def candidate(d, b, deadline_s=0.3, spent=0.0):
 388 | +    """A Router with the candidate on its replay chain and ruling 100's gateway deadline for context_verdict."""
 389 | +    led = os.path.join(d, "SPEND.json")
 390 | +    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
 391 | +               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 392 | +    r = router(d, [b], {f"replay110_{M}": [RX.name(M)]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 393 | +               routing="heimdall_first")
 394 | +    r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": deadline_s}}
 395 | +    return r
 396 | +
 397 | +
 398 | +def job(d):
 399 | +    p = os.path.join(d, "rec.json")
 400 | +    rec = {"role": "context_verdict", "backend": "xai:grok", "prompt": PROMPT, "text": GROK, "max_tokens": 100,
 401 | +           "seed": 7, "recorded_at": "2026-11-14T01:00:00Z", "seconds": 20.0}
 402 | +    json.dump(rec, open(p, "w"))
 403 | +    return (p, rec, "step_a", [], M)
 404 | +
 405 | +
 406 | +class TestOneRecord(unittest.TestCase):
 407 | +
 408 | +    def test_an_answer_inside_ruling_100s_deadline_is_in_time_and_compared(self):
 409 | +        with tempfile.TemporaryDirectory() as d:
 410 | +            row = RX.replay_one(candidate(d, Timed(GROK, 0.05)), job(d), cap_s=2.0)
 411 | +            self.assertEqual((row["outcome"], row["deadline_100_s"], row["compare"]), ("in_time", 0.3, {"m1": "agree"}))
 412 | +
 413 | +    def test_an_answer_after_the_deadline_is_late_a_missed_deadline_and_still_compared(self):
 414 | +        with tempfile.TemporaryDirectory() as d:
 415 | +            row = RX.replay_one(candidate(d, Timed(FAILS, 0.5)), job(d), cap_s=2.0)
 416 | +            self.assertEqual((row["outcome"], row["compare"]), ("late", {"m1": "stricter"}))
 417 | +            self.assertGreater(row["seconds"], row["deadline_100_s"])
 418 | +
 419 | +    def test_no_answer_by_the_cap_is_a_timeout_with_no_decision(self):
 420 | +        with tempfile.TemporaryDirectory() as d:
 421 | +            row = RX.replay_one(candidate(d, Timed(GROK, 0.6)), job(d), cap_s=0.2)
 422 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("timeout", None))
 423 | +            self.assertNotIn("compare", row)
 424 | +
 425 | +    def test_an_answer_out_of_contract_is_no_verdict(self):
 426 | +        with tempfile.TemporaryDirectory() as d:
 427 | +            row = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
 428 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("out_of_contract", None))
 429 | +
 430 | +    def test_a_failure_is_an_error_and_a_rate_limit_writes_no_row(self):
 431 | +        with tempfile.TemporaryDirectory() as d:
 432 | +            row = RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 502 overloaded")), job(d), cap_s=2.0)
 433 | +            self.assertEqual(row["outcome"], "error")
 434 | +            waited = []
 435 | +            self.assertIsNone(RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 429 too many")), job(d), cap_s=2.0,
 436 | +                                            sleep=waited.append))
 437 | +            self.assertEqual(waited, [30])
 438 | +
 439 | +    def test_at_the_spend_stop_no_call_is_made(self):
 440 | +        with tempfile.TemporaryDirectory() as d:
 441 | +            b = Timed(GROK)
 442 | +            self.assertEqual(RX.replay_one(candidate(d, b, spent=0.75), job(d), cap_s=2.0, stop_usd=0.75), "stopped")
 443 | +            self.assertEqual(b.calls, 0)
 444 | +            self.assertNotEqual(RX.replay_one(candidate(d, b, spent=0.74), job(d), cap_s=2.0, stop_usd=0.75),
 445 | +                                "stopped")
 446 | +            self.assertEqual(b.calls, 1)
 447 | +
 448 | +
 449 | +class TestTheSetAndTheTable(unittest.TestCase):
 450 | +
 451 | +    def test_the_records_are_ruling_85s_once_each_and_an_unreadable_one_is_set_aside(self):
 452 | +        with tempfile.TemporaryDirectory() as d:
 453 | +            os.makedirs(os.path.join(d, "r"))
 454 | +            good = {"role": "context_verdict", "prompt": PROMPT, "text": GROK}
 455 | +            json.dump(good, open(os.path.join(d, "r", "a.json"), "w"))
 456 | +            json.dump(dict(good, role="fidelity_verdict"), open(os.path.join(d, "r", "b.json"), "w"))
 457 | +            src = os.path.join(d, "RESULTS.jsonl")
 458 | +            with open(src, "w") as f:
 459 | +                for rel, m in (("r/a.json", "deepseek"), ("r/a.json", "glm"), ("r/b.json", "glm"), ("r/gone.json", "glm")):
 460 | +                    f.write(json.dumps({"record": rel, "type": "step_a", "model": m, "anchors": ["37c5b5f5"]}) + "\n")
 461 | +            recs, missing = RX.source_records(src, wt=d)
 462 | +            self.assertEqual([(os.path.relpath(p, d), k, a) for p, _, k, a in recs], [("r/a.json", "step_a",
 463 | +                                                                                        ["37c5b5f5"])])
 464 | +            self.assertEqual(sorted(missing), ["r/b.json", "r/gone.json"])
 465 | +
 466 | +    def test_agreement_in_time_leaves_late_answers_out_and_missed_counts_late_and_timeouts(self):
 467 | +        rows = [{"type": "step_a", "model": M, "outcome": "in_time", "seconds": 10.0, "compare": {"a": "agree"}},
 468 | +                {"type": "step_a", "model": M, "outcome": "in_time", "seconds": 30.0, "compare": {"b": "stricter"}},
 469 | +                {"type": "step_a", "model": M, "outcome": "late", "seconds": 200.0, "compare": {"c": "agree"}},
 470 | +                {"type": "step_a", "model": M, "outcome": "timeout", "seconds": 300.0},
 471 | +                {"type": "step_a", "model": M, "outcome": "error", "seconds": 1.0}]
 472 | +        x = RX.summary(rows)[("step_a", M)]
 473 | +        self.assertEqual((x["in_time"], x["late"], x["timeout"], x["error"], x["missed"]), (2, 1, 1, 1, 2))
 474 | +        self.assertEqual((x["units_in_time"], x["agree_in_time_pct"]), (2, 50.0))
 475 | +        self.assertAlmostEqual(x["agree_all_pct"], 200 / 3)
 476 | +        self.assertEqual((x["p50_s"], x["p90_s"]), (30.0, 166.0))     # the answers' times only (10, 30, 200)
 477 | +
 478 | +
 479 | +if __name__ == "__main__":
 480 | +    unittest.main()
 481 | 
```

---

pp-selectid, RULING 110 (orchestrator 23:32 ET Nov 14), HEIMDALL CANDIDATES: replay ruling 85.1's recorded Grok
verdicts against two Heimdall models, per verdict type: agreement with the recorded Grok verdict, p50/p90 latency,
error and missed-deadline counts, ruling 100's deadlines; a table in STATE and proof/. NO routing change (a model moves
into a verdict type only by a later ruling, at the bars of rulings 85/88/96). Heimdall calls only, no outside spend.

THE MODELS (the gateway's own list, GET /models, 23:3x ET): deepseek/deepseek-v4.1-flash-1017-uncensored (the v4.1 we
run, uncensored) and deepseek/deepseek-v4-flash-0731-abliterated (the ONLY DeepSeek v4, not 4.1, the gateway lists).

THE CHANGE: one new driver, tests/package/replay110.py, and its test. Nothing else changes (no config file, no
pipeline code, ruling 85.1's replay85.py untouched). It REUSES, UNCHANGED, ruling 85.1's own code for the method:
replay85.kind / decide (tests/package/replay85.py:68, :85: an answer -> the pipeline's decision by its own parsers,
ValueError/TypeError/KeyError = out of contract), compare (:178), grok_self (:343, Grok against Grok, the bar),
passes (:531, the bars of 85/88/96; MIN_UNITS :528).
- THE RECORDS: exactly the records behind ruling 85.1's RESULTS.jsonl, once each (319, all readable today; a record
  that cannot be read, or reads as another type, is set aside and counted).
- THE CANDIDATES: each a providers.HeimdallBackend made in the driver from the configured
  heimdall:deepseek/deepseek-v4.1-flash spec with the model id swapped, on its own chain "replay110_<m>".
- RULING 100: per call, deadline_100 = Router.effective_deadline(<the record's own verdict role>, candidate)
  (UNCHANGED, pipeline/providers.py:1089-1101, under routing heimdall_first: the pair's deadline-table row, else
  role_deadline :1076-1087, the gateway's configured 120 s). Today both candidates have no row: 120 s for every
  type. The call itself is cut at CAP_S = 300 s (ruling 100's ceiling) so its latency is measured: IN TIME if it
  answered within deadline_100; LATE (a missed deadline in production) if after it and before 300 s; TIMEOUT if no
  answer by 300 s (the Router's ProviderError, :1410, carries "abandoned at the deadline"); ERROR otherwise; OUT OF
  CONTRACT if decide() raised. Agreement is given on the in-time answers and on every answer.
- THE DEADLINE TABLE is read with DT.load(DT.STATE, None) (UNCHANGED, pipeline/deadline_table.py:77-100: with no
  record dir it is never saved over the production table).
- SPEND: its own ledger tests/package/proof/SPEND_R110.json (vendor-reported basis), limit $3.00 for the reservations
  in flight (each holds its list-price upper bound, ~$0.3) with reserve_wait_s 600 (7a2ddf91); NO CALL STARTS once
  the ledger holds $0.75 (batch 3's mining/checks share is $1.00). A rate limit (HTTP 429) or a guard refusal writes no
  row (a re-run asks again); its own record dir and deadline log; no breaker or health state is written (the Router
  gets neither).

PLEASE CHECK: (1) the classification against ruling 100 (in time / late / timeout / error / out of contract) and the
deadline it reads; (2) that the set is ruling 85.1's and the decisions are its own; (3) the spend stop and the guard;
(4) anything that could write production state or change routing; (5) the table's arithmetic (p50/p90 over answers
only; missed = late + timeouts); (6) the tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
