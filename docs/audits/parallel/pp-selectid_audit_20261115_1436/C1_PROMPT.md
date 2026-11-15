# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-selectid-20261115_1436
# Branch: pp-selectid
# Generated: 2026-11-15 14:37 UTC
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

### File: docs/audits/parallel/pp-selectid_audit_20261115_1436/C1_STEP.diff (263 lines)
```
   1 | diff --git a/tests/package/hook115.py b/tests/package/hook115.py
   2 | new file mode 100644
   3 | index 0000000..c9a7547
   4 | --- /dev/null
   5 | +++ b/tests/package/hook115.py
   6 | @@ -0,0 +1,183 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 115 (3) (orchestrator 13:24 ET Nov 15), THE PROPER FIX, REPORT BEFORE USE: "a new hook-question version
   9 | +carrying the approved hooks as positive examples AND five clear negatives from the near-miss file (the mid-conversation
  10 | +openers rated 2, e.g. "you know, it's still an asset"). It takes the job only when it rates all five approved at 4 or
  11 | +more AND all five negatives at 3 or less, on Grok and separately on qwen (qwen wins the job back if it passes both and
  12 | +agrees at ruling 85's bar)."
  13 | +
  14 | +THE VERSION (prompt_v2): package.HOOKS_PROMPT unchanged (ruling 52's ONE hook question, the same contract) with ONE
  15 | +block after its first paragraph: PBX's approved openers (positives: they opened videos he approved) and five
  16 | +mid-conversation openers (negatives), each with its channel. The block names no rating for any example: it says what
  17 | +PBX approved and why the negatives fail, and the question then asks for each part as before.
  18 | +THE TEST, as ordered: each of the ten asked ALONE (package.hook_ratings, one moment a call, cache None) at production's
  19 | +seed 7, on Grok and on qwen. A model passes when every approved hook's own-job rating (min(scroll, alone), ruling 61)
  20 | +is >= 4 and every negative's is <= 3. The ten rated ARE the examples the prompt carries, so a pass may only show the
  21 | +model copying its examples: the same ten are therefore also asked LEAVE-ONE-OUT (the rated item left out of the block),
  22 | +reported beside it. Report only: nothing here is read by a build; the hook job keeps ruling 115 (1)'s question.
  23 | +SPEND: its own ledger SPEND_H115.json, vendor-reported; no call starts at STOP_USD.
  24 | +Usage: python3 -B tests/package/hook115.py [--models grok,qwen] [--report-only]"""
  25 | +import argparse
  26 | +import json
  27 | +import os
  28 | +import sys
  29 | +import time
  30 | +from datetime import datetime, timezone
  31 | +from unittest import mock
  32 | +
  33 | +HERE = os.path.dirname(os.path.abspath(__file__))
  34 | +REPO = os.path.dirname(os.path.dirname(HERE))
  35 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  36 | +sys.path.insert(0, HERE)
  37 | +import eligibility as E  # noqa: E402
  38 | +import hook112 as H  # noqa: E402
  39 | +import package as PK  # noqa: E402
  40 | +import providers as P  # noqa: E402
  41 | +import replay85 as R  # noqa: E402
  42 | +
  43 | +WT = R.WT
  44 | +OUT = os.path.join(WT, "tests", "package", "proof", "hook115")
  45 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_H115.json")
  46 | +LIMIT_USD, STOP_USD, SEED = 0.55, 0.25, 7
  47 | +MODELS = {"grok": "xai:grok-4.20-0309-reasoning", "qwen": "heimdall:qwen/qwen3.8-27b"}
  48 | +NEGATIVES = (("adf6d9c528a27963f790", "Scott Melker"), ("f5f005b9a91b80840778", "CoinTelegraph"),
  49 | +             ("d7578b88ff8e0129064f", "CNBC Television"), ("2e77a0a7af2aab66a3a4", "The Bitcoin Layer"),
  50 | +             ("994ca307911a9ee1eb79", "Simply Bitcoin"))
  51 | +#   ruling 112's 48 h (FUNNEL / NEAR_MISSES' source, hook112.all_ratings): rated 2 as mid-conversation openers, one per
  52 | +#   channel; adf6d9c5 is the order's own example ("you know, it's still an asset").
  53 | +BLOCK = """HOW PBX JUDGES OPENERS (his own verdicts; these are examples, NOT candidates, and are not rated here):
  54 | +OPENERS PBX APPROVED: each one opened a video he approved for publishing.
  55 | +{pos}
  56 | +OPENERS THAT FAIL: each starts mid-conversation, leaning on something said before it ("you know", "all that said",
  57 | +"though", "here", "as I've said"), so a viewer who hears it first has missed what it answers.
  58 | +{neg}
  59 | +"""
  60 | +
  61 | +
  62 | +def negatives(proof=None):
  63 | +    """The five negatives as the hook job reads a moment: the text their rating was given on (hook112.all_ratings over
  64 | +    the builds of ruling 112's window), the channel on screen; an id of their own ("neg-<id>"), so no cache answers."""
  65 | +    recs = H.build_records(proof or H.PROOF, since="ledger_20261113_161500")
  66 | +    ra = H.all_ratings(recs, {})
  67 | +    out = []
  68 | +    for mid, ch in NEGATIVES:
  69 | +        hit = next(((rater, x) for (m, rater), x in sorted(ra.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))
  70 | +                    if m == mid and H.own_rating(x) == 2 and x.get("text")), None)
  71 | +        if hit is None:
  72 | +            raise ValueError(f"negative {mid} has no rating of 2 with its text in the window")
  73 | +        rater, r = hit
  74 | +        out.append({"moment_id": f"neg-{mid[:8]}", "text": r["text"], "channel_id": f"neg:{mid}", "channel_name": ch,
  75 | +                    "label": f"rated 2 by {rater}: {(r.get('why') or '')[:90]}"})
  76 | +    return out
  77 | +
  78 | +
  79 | +def example(m):
  80 | +    t = " ".join(m["text"].split())
  81 | +    return f'  - "{t}" ({m["channel_name"]})'
  82 | +
  83 | +
  84 | +def prompt_v2(pos, neg, leave_out=None):
  85 | +    """package.HOOKS_PROMPT with the examples block after its first paragraph (braces escaped for its .format)."""
  86 | +    keep = lambda ms: [m for m in ms if m["moment_id"] != leave_out]
  87 | +    block = BLOCK.format(pos="\n".join(example(m) for m in keep(pos)), neg="\n".join(example(m) for m in keep(neg)))
  88 | +    head, sep, rest = PK.HOOKS_PROMPT.partition("\n\n")
  89 | +    if not sep:
  90 | +        raise ValueError("HOOKS_PROMPT has no first paragraph")
  91 | +    return head + sep + block.replace("{", "{{").replace("}", "}}") + "\n" + rest
  92 | +
  93 | +
  94 | +def build_router(model, spend_path=SPEND):
  95 | +    r = P.Router(env_path=R.ENV, spend_path=spend_path, limit_usd=LIMIT_USD, limit_basis="reported",
  96 | +                 routing="heimdall_first")
  97 | +    r.chains["coherence_verdict:hook"] = [model]
  98 | +    return r
  99 | +
 100 | +
 101 | +def rate(router, m, prompt, ctx, rate_fn=None):
 102 | +    """One moment, alone, on `prompt` -> its record or {"error"}. No cache: nothing is read or written."""
 103 | +    rate_fn = rate_fn or PK.hook_ratings
 104 | +    wv, wf = PK._writers(router)
 105 | +    with mock.patch.object(PK, "HOOKS_PROMPT", prompt):
 106 | +        got, err = rate_fn(router, [m], ctx, wv, wf, cache=None, seed=SEED)
 107 | +    r = got.get(m["moment_id"])
 108 | +    return dict(r, own=H.own_rating(r)) if r else {"error": err or "no rating"}
 109 | +
 110 | +
 111 | +def verdict(rows):
 112 | +    """{"passes", "approved", "negatives"}: every approved own-job rating >= 4 and every negative's <= 3."""
 113 | +    a = [r.get("own") for r in rows if r["kind"] == "approved"]
 114 | +    n = [r.get("own") for r in rows if r["kind"] == "negative"]
 115 | +    ok = len(a) == 5 and len(n) == 5 and all(isinstance(x, int) and x >= 4 for x in a) and \
 116 | +        all(isinstance(x, int) and x <= 3 for x in n)
 117 | +    return {"passes": ok, "approved": a, "negatives": n}
 118 | +
 119 | +
 120 | +def run(models, now=None):
 121 | +    now = now or datetime.now(timezone.utc)
 122 | +    ctx = E.Context(now, H.registry())
 123 | +    pos, neg = [m for m in H.ref_moments() if "error" not in m], negatives()
 124 | +    if len(pos) != 5:
 125 | +        raise ValueError(f"{5 - len(pos)} approved hook(s) cannot be read")
 126 | +    out = {"ruling": "115 (3), report before use", "at": now.isoformat(timespec="seconds"), "seed": SEED,
 127 | +           "question_v2": prompt_v2(pos, neg), "models": {}}
 128 | +    for key in models:
 129 | +        r = build_router(MODELS[key])
 130 | +        res = {}
 131 | +        for variant in ("as ordered", "leave-one-out"):
 132 | +            rows = []
 133 | +            for kind, m in [("approved", x) for x in pos] + [("negative", x) for x in neg]:
 134 | +                if r.spent() >= STOP_USD:
 135 | +                    rows.append({"kind": kind, "moment_id": m["moment_id"], "error": f"stopped at ${r.spent():.4f}"})
 136 | +                    continue
 137 | +                pr = prompt_v2(pos, neg, leave_out=m["moment_id"] if variant == "leave-one-out" else None)
 138 | +                rows.append(dict(rate(r, m, pr, ctx), kind=kind, moment_id=m["moment_id"],
 139 | +                                 channel=m["channel_name"]))
 140 | +                print(f"  {key} {variant} {m['moment_id']}: {rows[-1].get('own')} "
 141 | +                      f"({rows[-1].get('scroll')}/{rows[-1].get('alone')}/{rows[-1].get('setup')}) "
 142 | +                      f"{rows[-1].get('error') or ''}; ${r.spent():.4f}", flush=True)
 143 | +            res[variant] = {"rows": rows, **verdict(rows)}
 144 | +        out["models"][MODELS[key]] = res
 145 | +    out["spent_usd_reported"] = round(P.Router(env_path=R.ENV, spend_path=SPEND).spent(), 6)
 146 | +    os.makedirs(OUT, exist_ok=True)
 147 | +    with open(os.path.join(OUT, "QUESTION_V2_TEST.json"), "w") as f:
 148 | +        json.dump(out, f, indent=1)
 149 | +    return out
 150 | +
 151 | +
 152 | +def report(path=None):
 153 | +    with open(path or os.path.join(OUT, "QUESTION_V2_TEST.json")) as f:
 154 | +        d = json.load(f)
 155 | +    L = ["# RULING 115 (3): THE HOOK QUESTION WITH PBX'S EXAMPLES (report before use)", "",
 156 | +         f"Measured {d['at']} (UTC), seed {d['seed']}, each hook asked alone. A model takes the job only when every "
 157 | +         "approved hook's own-job rating (min(scroll, alone)) is >= 4 AND every negative's is <= 3. The ten rated are "
 158 | +         "the examples the question carries; LEAVE-ONE-OUT asks each with itself left out of the examples.", "",
 159 | +         "| model | variant | approved (5) | negatives (5) | passes |", "|---|---|---|---|---|"]
 160 | +    for model, res in d["models"].items():
 161 | +        for variant, v in res.items():
 162 | +            L.append(f"| {model} | {variant} | {v['approved']} | {v['negatives']} | {'YES' if v['passes'] else 'no'} |")
 163 | +    L += ["", "Every rating (scroll / alone / setup, and the model's reason):", ""]
 164 | +    for model, res in d["models"].items():
 165 | +        for variant, v in res.items():
 166 | +            for r in v["rows"]:
 167 | +                L.append(f"- {model}, {variant}, {r['kind']} {r['moment_id']} ({r.get('channel')}): "
 168 | +                         + (f"{r.get('own')} ({r.get('scroll')}/{r.get('alone')}/{r.get('setup')}): {r.get('why')}"
 169 | +                            if "error" not in r else f"NO RATING: {r['error']}"))
 170 | +    L += ["", f"Spent ${d['spent_usd_reported']:.4f} (vendor-reported, SPEND_H115.json).", "",
 171 | +          "The question as asked (as ordered: every example in):", "", "```", d["question_v2"], "```"]
 172 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 173 | +        f.write("\n".join(L) + "\n")
 174 | +
 175 | +
 176 | +def main(argv=None):
 177 | +    ap = argparse.ArgumentParser()
 178 | +    ap.add_argument("--models", default="grok,qwen")
 179 | +    ap.add_argument("--report-only", action="store_true")
 180 | +    a = ap.parse_args(argv)
 181 | +    if not a.report_only:
 182 | +        run([k for k in a.models.split(",") if k])
 183 | +    report()
 184 | +    print(open(os.path.join(OUT, "REPORT.md")).read()[:3000])
 185 | +    return 0
 186 | +
 187 | +
 188 | +if __name__ == "__main__":
 189 | +    sys.exit(main())
 190 | diff --git a/tests/package/test_hook115.py b/tests/package/test_hook115.py
 191 | new file mode 100644
 192 | index 0000000..55c2824
 193 | --- /dev/null
 194 | +++ b/tests/package/test_hook115.py
 195 | @@ -0,0 +1,67 @@
 196 | +#!/usr/bin/env python3
 197 | +"""RULING 115 (3): the hook question with PBX's examples (tests/package/hook115.py). Offline: the rating call is a
 198 | +stub; the negatives are read from the proof builds (read only)."""
 199 | +import os
 200 | +import sys
 201 | +import unittest
 202 | +import unittest.mock
 203 | +
 204 | +HERE = os.path.dirname(os.path.abspath(__file__))
 205 | +sys.path.insert(0, HERE)
 206 | +import hook115 as X  # noqa: E402
 207 | +import package as PK  # noqa: E402
 208 | +
 209 | +POS = [{"moment_id": f"ref-{i}", "text": f"Bitcoin {i} {{x}}.", "channel_name": f"P{i}"} for i in range(5)]
 210 | +NEG = [{"moment_id": f"neg-{i}", "text": f"You know, {i}.", "channel_name": f"N{i}"} for i in range(5)]
 211 | +
 212 | +
 213 | +class TestPrompt(unittest.TestCase):
 214 | +    def test_the_block_sits_after_the_first_paragraph_and_the_question_is_unchanged(self):
 215 | +        p = X.prompt_v2(POS, NEG)
 216 | +        filled = p.format(hooks='CANDIDATE id="c"', keys='"c": 1')          # braces in a text are escaped
 217 | +        head = PK.HOOKS_PROMPT.split("\n\n")[0]
 218 | +        self.assertTrue(filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS"))
 219 | +        self.assertIn(PK.HOOK_QUESTION, filled)                              # ONE definition of the hook's job
 220 | +        self.assertIn('"Bitcoin 3 {x}." (P3)', filled)
 221 | +        self.assertIn('"You know, 4." (N4)', filled)
 222 | +        self.assertLess(filled.index("OPENERS PBX APPROVED"), filled.index("OPENERS THAT FAIL"))
 223 | +        self.assertLess(filled.index("OPENERS THAT FAIL"), filled.index('CANDIDATE id="c"'))
 224 | +        self.assertNotIn("4 or more", filled)                                # no example carries a rating
 225 | +
 226 | +    def test_leave_one_out_drops_only_the_rated_item(self):
 227 | +        p = X.prompt_v2(POS, NEG, leave_out="ref-2")
 228 | +        self.assertNotIn("Bitcoin 2 ", p)
 229 | +        self.assertIn("Bitcoin 1 ", p)
 230 | +        p = X.prompt_v2(POS, NEG, leave_out="neg-0")
 231 | +        self.assertNotIn("You know, 0.", p)
 232 | +        self.assertIn("You know, 1.", p)
 233 | +
 234 | +
 235 | +class TestRate(unittest.TestCase):
 236 | +    def test_alone_no_cache_the_prompt_only_for_the_call_and_the_verdict(self):
 237 | +        seen = []
 238 | +
 239 | +        def fake(router, ms, ctx, wv, wf, cache="unset", seed=None):
 240 | +            seen.append((len(ms), cache, seed, PK.HOOKS_PROMPT))
 241 | +            return {ms[0]["moment_id"]: {"scroll": 4, "alone": 5, "setup": 3, "why": "w"}}, None
 242 | +        before = PK.HOOKS_PROMPT
 243 | +        with unittest.mock.patch.object(PK, "_writers", lambda r: (set(), set())):
 244 | +            r = X.rate(None, POS[0], "THE V2 PROMPT", None, rate_fn=fake)
 245 | +        self.assertEqual(seen, [(1, None, 7, "THE V2 PROMPT")])
 246 | +        self.assertEqual((r["own"], PK.HOOKS_PROMPT), (4, before))           # restored after the call
 247 | +        rows = [dict(kind="approved", own=4)] * 5 + [dict(kind="negative", own=3)] * 5
 248 | +        self.assertTrue(X.verdict(rows)["passes"])
 249 | +        for bad in ([dict(kind="approved", own=3)] + rows[1:], rows[:5] + [dict(kind="negative", own=4)] + rows[6:],
 250 | +                    rows[:9], [dict(kind="approved", error="x")] + rows[1:]):
 251 | +            self.assertFalse(X.verdict(bad)["passes"])
 252 | +
 253 | +    def test_the_five_negatives_are_read_rated_2_with_their_text(self):
 254 | +        neg = X.negatives()
 255 | +        self.assertEqual([n["channel_name"] for n in neg], [c for _, c in X.NEGATIVES])
 256 | +        self.assertTrue(neg[0]["text"].startswith("You know, it's still an asset"))
 257 | +        self.assertTrue(all(n["moment_id"].startswith("neg-") and n["text"] for n in neg))
 258 | +
 259 | +
 260 | +if __name__ == "__main__":
 261 | +    import unittest.mock  # noqa: F401
 262 | +    unittest.main()
 263 | 
```

---

pp-selectid: RULING 115 (3) (orchestrator 13:24 ET Nov 15), THE PROPER FIX, REPORT BEFORE USE. A new measurement
driver, tests/package/hook115.py, and its offline tests tests/package/test_hook115.py. Nothing in pipeline/ changes;
the hook job keeps ruling 115 (1)'s question; nothing here is read by a build.

THE ORDER, verbatim: "(3) THE PROPER FIX, in parallel, report before use: your (b), a new hook-question version
carrying the approved hooks as positive examples AND five clear negatives from the near-miss file (the
mid-conversation openers rated 2, e.g. "you know, it's still an asset"). It takes the job only when it rates all five
approved at 4 or more AND all five negatives at 3 or less, on Grok and separately on qwen (qwen wins the job back if
it passes both and agrees at ruling 85's bar). The standing law of ruling 113 (2) is then measured against that
version." Ruling 115's cap: $0.50 in all.

THE DRIVER:
- The positives: hook112.ref_moments() (UNCHANGED, tests/package/hook112.py:373-388): the five PBX-approved hooks,
  their approved text verbatim, ids "ref-<key>".
- The negatives (NEGATIVES): five moments rated 2 as mid-conversation openers in ruling 112's 48 h, one per channel
  (Scott Melker "You know, it's still an asset...", the order's own example; CoinTelegraph "Now, all that said...";
  CNBC Television "There is, though, one potential bright spot here..."; The Bitcoin Layer "...turning though...";
  Simply Bitcoin "As I've said multiple times on this show..."). negatives() reads each one's text from the builds
  (hook112.build_records / all_ratings, UNCHANGED: the source of the near-miss file) where it was rated 2, and gives
  it an id of its own ("neg-<id>"), so no cache entry can answer for it.
- prompt_v2: package.HOOKS_PROMPT unchanged with ONE block after its first paragraph: the approved openers (each "opened
  a video he approved for publishing") and the failing ones ("each starts mid-conversation, leaning on something said
  before it"), each with its channel. No example carries a rating. The braces of the texts are escaped for the
  prompt's .format. HOOK_QUESTION (ruling 52's one question) and the reply contract are the same bytes.
- rate(): package.hook_ratings on ONE moment, cache None (so nothing is read from or written to HOOK_CACHE.json:
  _load_cache(None) is {} and _cache_put(None, ...) returns at once, pipeline/package.py:499-513), at seed 7, with
  HOOKS_PROMPT patched to the v2 text only for the call (unittest.mock.patch.object, restored on exit), avoiding the
  writers' vendor and family (package._writers) as production does.
- build_router(model): providers.Router under heimdall_first with "coherence_verdict:hook" = [that model] alone
  (Grok xai:grok-4.20-0309-reasoning, or qwen heimdall:qwen/qwen3.8-27b), its own ledger SPEND_H115.json, limit $0.55
  on reported spend; no call starts at STOP_USD $0.25.
- THE TEST, as ordered: the ten, each alone, on each model; passes = every approved own-job rating (min(scroll,
  alone), ruling 61) >= 4 AND every negative's <= 3. Because the ten rated ARE the examples the prompt carries, a
  pass may only show the model copying its examples: the same ten are also asked LEAVE-ONE-OUT (the rated item left
  out of the block), reported beside it. ~40 calls: Grok ~$0.005 each, qwen ~$0.0003.
- Output: proof/hook115/QUESTION_V2_TEST.json (every rating, the question as asked) and REPORT.md.

TESTS (offline): the block sits after the first paragraph, HOOK_QUESTION is unchanged in the filled prompt, braces in
a text survive .format, no example carries a rating; leave-one-out drops only the rated item; rate() asks one moment
with cache None and seed 7 and restores HOOKS_PROMPT; the verdict's rule (including a missing rating); the five
negatives are read from the proof builds with their texts.

PLEASE CHECK: (1) that the v2 prompt differs from production's only by the block; (2) that nothing can read or write
the production cache, and HOOKS_PROMPT is restored after every call; (3) that only the named model can answer each
run (no failover to another model); (4) the verdict's rule against the order; (5) the stop under the cap; (6) the
tests.



Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
