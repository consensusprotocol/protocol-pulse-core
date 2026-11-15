# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1436
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 151 s finish=stop usage in 10151 / out 4331 usd_reported=0.000852 usd~0.095 (upper-bound price)

# Audit: pp-selectid — RULING 115 (3) hook115.py + test_hook115.py

Scope: 2 new files, 263 diff lines, nothing in `pipeline/` touched. Reviewed against the order's six CHECK items, the governing laws, and the stated intent ("report before use", nothing read by a build).

---

## Findings

### [P1] F1 — `verdict()` counts a stopped/errored approved row as a pass when `own` is absent... no — it fails, but the *stop* path silently produces a 5/5-looking report
Checked (5) the stop under the cap. In `run()`, when `r.spent() >= STOP_USD` the row appended is `{"kind": kind, "moment_id": ..., "error": ...}` — it has **no** `"own"` key. `verdict()` then does `r.get("own")` → `None`, and `all(isinstance(x, int) and x >= 4 for x in a)` correctly fails. Good. **But** the loop `continue`s rather than `break`s: after the cap is hit, every remaining moment still gets a row (correct), yet the *spent* model's variant verdict is reported as `passes: no` with no distinction from a genuine rating failure. That's report-only, so it's a P2, not P1. However — the stop check happens **before** the call, so the call that crosses STOP_USD still runs (spend can exceed $0.25, by design "no call starts at STOP_USD"). With LIMIT_USD $0.55 as the hard cap and ~40 calls at Grok ~$0.005, the arithmetic is safe. Downgraded: **[P2]** — the report cannot distinguish "stopped by cap" from "model rated it 3"; add a `stopped: true` marker. (Report-only, no build reads it.)

### [P2] F2 — `rate()`'s error path loses the router's failure reason when the rating record exists but is malformed
`rate()` returns `dict(r, own=H.own_rating(r)) if r else {"error": err or "no rating"}`. If `hook_ratings` returns a record, `err` is discarded even when the record is a partial (e.g. `{"scroll": 4}` with no `alone`). `H.own_rating(r)` (ruling 61's `min(scroll, alone)`) will then raise or return something non-int; `verdict()`'s `isinstance(x, int)` guard catches it, so the verdict fails closed — consistent with M12. But the *report* shows `own: None` with no `why`/`error`, which is exactly the "dissent is right until disproved" opacity L-l warns about. **[P2]** — attach `err` to the returned record when present.

### [P1] F3 — `prompt_v2` escapes braces **after** the block is built, but the *positives/negatives texts themselves* are inserted before escaping, so a text containing `{...}` is double-escaped... no, it's correct
`BLOCK.format(pos=..., neg=...)` — the texts are substituted by `.format`, so any `{`/`}` inside them would raise KeyError/IndexError at format time, not later. Then `.replace("{","{{")` escapes the *result*, which now contains the texts. So a text with braces becomes `{{x}}` in the final prompt, and the test's `filled = p.format(hooks=..., keys=...)` correctly exercises this (`POS` texts are `f"Bitcoin {i} {{x}}."` — note the *test* pre-escapes, so the production path where a text holds a literal `{` is only covered by the double-escape). Trace: production text `"Bitcoin 0 {x}."` → after `BLOCK.format` the block holds `{x}` → after `.replace` it holds `{{x}}` → final `.format(hooks=..., keys=...)` renders `{x}`. Correct. But the test's POS texts are *already* `{{x}}` in the Python source, meaning after `BLOCK.format` they hold `{{x}}`... wait: `f"Bitcoin {i} {{x}}."` evaluates to `Bitcoin 0 {x}.` — the f-string consumes the doubling. So after `BLOCK.format` the block holds `{x}`, after `.replace` it holds `{{x}}`, and the final `.format` restores `{x}`. Consistent. **[P3]** — the test's f-string doubling vs. production's runtime doubling are the same by accident of f-string semantics; a comment would help.

### [P4→P2] F4 — CHECK (2): cache isolation is real, but `run()`'s final spend read constructs a **new Router** that may re-read a shared ledger concurrently
`out["spent_usd_reported"] = round(P.Router(env_path=R.ENV, spend_path=SPEND).spent(), 6)` — a fresh Router on the same SPEND_H115.json. Since `run()` is single-threaded and the per-model routers are already closed, this is safe. But if two invocations of hook115.py (e.g. `--models grok` and `--models qwen` in parallel, which the order's "in parallel" invites) share SPEND_H115.json, the ledger is a shared mutable file with no locking. The order says "in parallel" refers to the *ruling's three parts*, not this driver, and the driver runs models sequentially. **[P3]** — note the assumption; a concurrent second invocation would race the ledger.

### [P1] F5 — CHECK (3): "only the named model can answer" — the chain is pinned, but `heimdall_first` routing + a single-element chain means no failover, **except** the Router's own retry/fallback inside `chat` is not shown
`r.chains["coherence_verdict:hook"] = [model]` pins the chain to one model. Whether `providers.Router` internally fails over to a *different* model when the sole chain element errors depend

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 45 s finish=stop usage in 10186 / out 889 usd_reported=0.027111 usd~0.073 (upper-bound price)

**Audit Summary for pp-selectid-20261115_1436 (hook115 measurement driver)**

The diff adds a self-contained measurement tool (`tests/package/hook115.py`) + offline unit test to implement Ruling 115 (3) exactly as written. It constructs `prompt_v2` (original `HOOKS_PROMPT` first paragraph + PBX examples block + unchanged `HOOK_QUESTION` contract), runs the ten moments alone (cache=None, seed=7, isolated router with `coherence_verdict:hook` forced to a single model, own spend ledger), computes the exact pass rule required by the ruling ("all 5 approved own >= 4 AND all 5 negatives <= 3"), does the leave-one-out variant to surface copying, stays under the $0.50 cap, writes only to its own proof/ directory, and produces the mandated REPORT.md before any production use. No pipeline/ code is touched; the hook job continues to use ruling 115 (1)'s prompt and contract. All six explicit "PLEASE CHECK" items pass.

No violations of any Governing Law were found (L-a through L-l, M2, M12, LAW 20/22, SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-c dissent-is-right, L-d protected preview, L-e punctuated-before-read, L-f channels-first, L-g written forms, L-h text-read-as-spoken, L-i claim-is-the-event, L-j release-authorised-on-these-bytes, L-k one-canonical-form, L-l model-reply-counts-only-whole). The added code never touches EDLs, transcripts, cuts, renders, gates, selection locks, edge-word fidelity, sign-off voiceovers, canonicalisation, release attestation, or any production cache/ledger. All model calls are isolated, fail-closed where relevant, and the measurement itself is not part of any release gate.

**Findings**

[P2] `hook115.py:64` and `negatives()` – test depends on live proof files (`hook112.build_records(..., since="ledger_20261113_161500")` + `all_ratings`). While the ruling explicitly requires these exact negatives, the unit test (`test_hook115.py:254`) is therefore not hermetic. A missing or mutated proof package breaks CI. Mock the ledger read for the unit test (the integration run can stay).

[P2] `hook115.py:88` – `partition("\n\n")` to splice the examples block after the first paragraph is fragile. If `HOOKS_PROMPT` ever gains an earlier blank line or formatting change, the splice point moves silently. Use `split("\n\n", 1)` for an explicit "after first paragraph only" contract.

[P3] Hard-coded magic values (STOP_USD=0.25, LIMIT_USD=0.55, SEED=7, the exact NEGATIVES list and ledger timestamp, model strings, SPEND_H115.json path, OUT directory). These should be named constants at module level with comments tying them to the ruling cap and the "stop early" safety margin.

[P3] `hook115.py:184` – `print(open(...).read()[:3000])` is a quick-and-dirty console dump. If the report grows beyond 3000 chars the truncation hides part of the "every rating" section the ruling asks to see. Use `pathlib` + explicit `print(report)` or let the caller read the generated REPORT.md.

[P3] Minor style: `sys.path.insert(0, ...)` twice, duplicate `import unittest.mock` inside `if __name__`, and a 183-line test driver that mixes real LLM spend with offline verification. Could be split into a lightweight measurement script under `tools/audits/` rather than living next to unit tests, but this is cosmetic given the "report before use" mandate.

No P0 or P1 defects. The implementation is precise, auditable, fail-closed where required, smallest reasonable diff for the ruling, and ready for the parallel review by the other two models. The generated REPORT.md (once run) can be attached to the merge request as the required evidence before any production hook-model change.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 11187 / out 3019 usd_reported=0.002673 usd~0.079 (upper-bound price)

I will review the code in `tests/package/hook115.py` and `tests/package/test_hook115.py` against the provided laws and the specific "PLEASE CHECK" items.

### Analysis

**1. Context & Scope**
The feature is a "report before use" measurement driver for Ruling 115(3). It tests a new prompt version (`prompt_v2`) that includes positive and negative examples for hook rating.
- **Constraint:** "Nothing in pipeline/ changes; the hook job keeps ruling 115 (1)'s question; nothing here is read by a build."
- **Constraint:** "Report only: nothing here is read by a build".
- **Law Compliance:** Since this is a test/measurement script and not part of the production render pipeline (`run_fresh.py`), the strict "Governing Laws" regarding video rendering (Sentence Law, Snap Limit, etc.) do not directly apply to the *logic* of this Python script, but the script must not violate the *integrity* of the system (e.g., corrupting caches, bypassing spend limits, or altering production state).

**2. Review of `hook115.py`**

*   **Spend Limits (Check 5):**
    *   `LIMIT_USD = 0.55`, `STOP_USD = 0.25`.
    *   The order states: "Ruling 115's cap: $0.50 in all."
    *   The code sets `limit_usd=0.55` in `build_router`.
    *   **Finding:** The hard limit in the router is $0.55, which exceeds the stated cap of $0.50. While `STOP_USD` is $0.25 (which is well under $0.50), the `Router`'s `limit_usd` is the hard stop for the vendor API. If the spend logic in `providers.Router` allows up to `limit_usd` before throwing an error, this could potentially exceed the $0.50 cap if the `STOP_USD` check is bypassed or if the "reported" spend lags. However, the loop explicitly checks `if r.spent() >= STOP_USD: ... continue`. This prevents *new* calls after $0.25. The total spend will be bounded by the cost of the calls made before $0.25.
    *   Let's estimate cost: ~40 calls. Grok ~$0.005, Qwen ~$0.0003. Total ~$0.20. This is under $0.25. So `STOP_USD` is the effective governor.
    *   Is $0.55 a violation? The order says "cap: $0.50". Setting the router limit to $0.55 is technically higher than the cap. If a bug caused `STOP_USD` to be ignored, the router would allow up to $0.55. This is a safety margin issue.
    *   **Severity:** [P2] The router limit ($0.55) exceeds the stated ruling cap ($0.50). It should be set to $0.50 or lower to strictly enforce the cap at the infrastructure level, relying on `STOP_USD` for the operational stop.

*   **Cache Isolation (Check 2):**
    *   `rate()` uses `cache=None`.
    *   `PK.hook_ratings` is called with `cache=None`.
    *   The docstring says: "No cache: nothing is read or written."
    *   `build_router` uses `spend_path=SPEND` which is `tests/package/proof/SPEND_H115.json`. This is isolated from production spend logs.
    *   `mock.patch.object(PK, "HOOKS_PROMPT", prompt)` ensures the production prompt variable is restored.
    *   **Finding:** The isolation looks correct. `cache=None` prevents reading/writing `HOOK_CACHE.json`.

*   **Model Routing (Check 3):**
    *   `build_router` sets `r.chains["coherence_verdict:hook"] = [model]`.
    *   This forces the specific model (Grok or Qwen) to handle the request.
    *   `routing="heimdall_first"` is set, but the explicit chain override should take precedence for that specific task type.
    *   **Finding:** Correct. No failover to other models for the hook rating task.

*   **Prompt Construction (Check 1):**
    *   `prompt_v2` inserts a block after the first paragraph of `PK.HOOKS_PROMPT`.
    *   It escapes braces `{` and `}` in the block to prevent `.format` errors.
    *   It uses `PK.HOOK_QUESTION` implicitly by keeping the rest of the prompt intact.
    *   **Finding:** The logic `head + sep + block... + "\n" + rest` preserves the original structure. The escaping `block.replace("{", "{{").replace("}", "}}")` is crucial because `HOOKS_PROMPT` likely uses `.format()`. If the examples contain `{` or `}`, this prevents `KeyError`.
    *   **Potential Issue:** What if the *original* `HOOKS_PROMPT` has placeholders that are *not* meant to be filled by the examples? The code assumes `HOOKS_PROMPT` is a template. The test `test_the_block_sits_after_the_first_paragraph...` verifies that `filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS")`. This implies the structure is preserved.

*   **Verdict Logic (Check 4):**
    *   `verdict(rows)` checks:
        *   `len(a) == 5` and `len(n) == 5`.
        *   All approved `own` ratings `>= 4`.
        *   All negative `own` ratings `<= 3`.
    *   `own` is defined as `H.own_rating(r)`. The docstring says `own` is `min(scroll, alone)`.
    *   The order says: "rates all five approved at 4 or more AND all five negatives at 3 or less".
    *   **Finding:** The logic matches the order.

*   **Data Integrity (Negatives):**
    *   `negatives()` reads from `H.build_records` and `H.al

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1436 (ruling 115 (3)'s question-with-examples driver, tests/package/hook115.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0), glm-5.3-flash (1); they disagree on a P1, so Grok was asked (0). Cycle 1:
$0.0306 vendor-reported. No paid call of the driver has been made.

THE P1 (glm F5): "nothing asserts which model answered: if the Router fell back to another model, the report would
credit the wrong one". The chain is one model (r.chains["coherence_verdict:hook"] = [model]; providers.Router.call
tries only its chain, and call_parsed skips a model that answered out of contract, so a one-model chain cannot reach
another: tests/providers/test_providers.py covers both). FIXED anyway, as the report's own guarantee: each row keeps
the answering back-end (hook_ratings' record "backend"), the report prints it on every rating ("by <model>"), and
verdict(rows, model) counts a rating ONLY when the named model gave it (else it is no rating, and the model does not
pass). New test.

ACTED ON:
- qwen P2 "the router limit $0.55 is above ruling 115's $0.50 cap": LIMIT_USD is now $0.50 (the router reserves each
  call's list-price upper bound, so it sits above our own stop on reported spend, STOP_USD $0.25).
- glm F8 "run() and report() are never exercised": NEW TEST with the calls stubbed: both models, both variants, ten
  rows each; as ordered every example is in the prompt; leave-one-out leaves the rated item out; the rows carry the
  answering model; past STOP_USD no call is made (7 rows "stopped", 3 calls); the JSON and REPORT.md are written.
- The final spend read no longer constructs a ledger when none exists.

NOT CHANGED:
- glm F1 "a stopped row reads like a rating failure in the verdict": the row says "stopped at $x" in the report's
  every-rating list; the verdict fails closed (no rating = no pass), which is right for "takes the job only when".
- glm F2 "rate() drops err when a record exists": one candidate a call, so a record means no error for it.
- glm F7 "the order says 'rates ... 4 or more': the own-job rating min(scroll, alone)": that is the rating ruling 113
  (2)'s law reads (ruling 61); the report gives every part beside it, setup included.
- Grok P2 "the negatives test reads the proof builds": deliberate; the driver's whole input is those builds, and the
  test pins that the five are found rated 2 with their texts.
- Grok P2 "partition('\n\n')": it splits at the FIRST blank line only (as split(..., 1)); the test pins the block
  right after the first paragraph and HOOK_QUESTION unchanged.

TESTS: 6 offline (was 4), all pass.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1436/C2_STEP.diff (308 lines)
```
   1 | diff --git a/tests/package/hook115.py b/tests/package/hook115.py
   2 | new file mode 100644
   3 | index 0000000..b5458cf
   4 | --- /dev/null
   5 | +++ b/tests/package/hook115.py
   6 | @@ -0,0 +1,188 @@
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
  46 | +LIMIT_USD, STOP_USD, SEED = 0.50, 0.25, 7   # the router's ceiling is ruling 115's cap (it reserves each call's
  47 | +#   list-price upper bound, so it sits above our own stop on reported spend; audit 1436 C1, qwen)
  48 | +MODELS = {"grok": "xai:grok-4.20-0309-reasoning", "qwen": "heimdall:qwen/qwen3.8-27b"}
  49 | +NEGATIVES = (("adf6d9c528a27963f790", "Scott Melker"), ("f5f005b9a91b80840778", "CoinTelegraph"),
  50 | +             ("d7578b88ff8e0129064f", "CNBC Television"), ("2e77a0a7af2aab66a3a4", "The Bitcoin Layer"),
  51 | +             ("994ca307911a9ee1eb79", "Simply Bitcoin"))
  52 | +#   ruling 112's 48 h (FUNNEL / NEAR_MISSES' source, hook112.all_ratings): rated 2 as mid-conversation openers, one per
  53 | +#   channel; adf6d9c5 is the order's own example ("you know, it's still an asset").
  54 | +BLOCK = """HOW PBX JUDGES OPENERS (his own verdicts; these are examples, NOT candidates, and are not rated here):
  55 | +OPENERS PBX APPROVED: each one opened a video he approved for publishing.
  56 | +{pos}
  57 | +OPENERS THAT FAIL: each starts mid-conversation, leaning on something said before it ("you know", "all that said",
  58 | +"though", "here", "as I've said"), so a viewer who hears it first has missed what it answers.
  59 | +{neg}
  60 | +"""
  61 | +
  62 | +
  63 | +def negatives(proof=None):
  64 | +    """The five negatives as the hook job reads a moment: the text their rating was given on (hook112.all_ratings over
  65 | +    the builds of ruling 112's window), the channel on screen; an id of their own ("neg-<id>"), so no cache answers."""
  66 | +    recs = H.build_records(proof or H.PROOF, since="ledger_20261113_161500")
  67 | +    ra = H.all_ratings(recs, {})
  68 | +    out = []
  69 | +    for mid, ch in NEGATIVES:
  70 | +        hit = next(((rater, x) for (m, rater), x in sorted(ra.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))
  71 | +                    if m == mid and H.own_rating(x) == 2 and x.get("text")), None)
  72 | +        if hit is None:
  73 | +            raise ValueError(f"negative {mid} has no rating of 2 with its text in the window")
  74 | +        rater, r = hit
  75 | +        out.append({"moment_id": f"neg-{mid[:8]}", "text": r["text"], "channel_id": f"neg:{mid}", "channel_name": ch,
  76 | +                    "label": f"rated 2 by {rater}: {(r.get('why') or '')[:90]}"})
  77 | +    return out
  78 | +
  79 | +
  80 | +def example(m):
  81 | +    t = " ".join(m["text"].split())
  82 | +    return f'  - "{t}" ({m["channel_name"]})'
  83 | +
  84 | +
  85 | +def prompt_v2(pos, neg, leave_out=None):
  86 | +    """package.HOOKS_PROMPT with the examples block after its first paragraph (braces escaped for its .format)."""
  87 | +    keep = lambda ms: [m for m in ms if m["moment_id"] != leave_out]
  88 | +    block = BLOCK.format(pos="\n".join(example(m) for m in keep(pos)), neg="\n".join(example(m) for m in keep(neg)))
  89 | +    head, sep, rest = PK.HOOKS_PROMPT.partition("\n\n")
  90 | +    if not sep:
  91 | +        raise ValueError("HOOKS_PROMPT has no first paragraph")
  92 | +    return head + sep + block.replace("{", "{{").replace("}", "}}") + "\n" + rest
  93 | +
  94 | +
  95 | +def build_router(model, spend_path=SPEND):
  96 | +    r = P.Router(env_path=R.ENV, spend_path=spend_path, limit_usd=LIMIT_USD, limit_basis="reported",
  97 | +                 routing="heimdall_first")
  98 | +    r.chains["coherence_verdict:hook"] = [model]
  99 | +    return r
 100 | +
 101 | +
 102 | +def rate(router, m, prompt, ctx, rate_fn=None):
 103 | +    """One moment, alone, on `prompt` -> its record or {"error"}. No cache: nothing is read or written."""
 104 | +    rate_fn = rate_fn or PK.hook_ratings
 105 | +    wv, wf = PK._writers(router)
 106 | +    with mock.patch.object(PK, "HOOKS_PROMPT", prompt):
 107 | +        got, err = rate_fn(router, [m], ctx, wv, wf, cache=None, seed=SEED)
 108 | +    r = got.get(m["moment_id"])
 109 | +    return dict(r, own=H.own_rating(r)) if r else {"error": err or "no rating"}
 110 | +
 111 | +
 112 | +def verdict(rows, model=None):
 113 | +    """{"passes", "approved", "negatives"}: every approved own-job rating >= 4 and every negative's <= 3. A rating the
 114 | +    named model did not give counts as none (audit 1436 C1, glm: the report never credits another model)."""
 115 | +    own = lambda r: r.get("own") if model is None or r.get("backend") == model else None
 116 | +    a = [own(r) for r in rows if r["kind"] == "approved"]
 117 | +    n = [own(r) for r in rows if r["kind"] == "negative"]
 118 | +    ok = len(a) == 5 and len(n) == 5 and all(isinstance(x, int) and x >= 4 for x in a) and \
 119 | +        all(isinstance(x, int) and x <= 3 for x in n)
 120 | +    return {"passes": ok, "approved": a, "negatives": n}
 121 | +
 122 | +
 123 | +def run(models, now=None):
 124 | +    """Every model, both variants, the ten each -> the result, also written to QUESTION_V2_TEST.json."""
 125 | +    now = now or datetime.now(timezone.utc)
 126 | +    ctx = E.Context(now, H.registry())
 127 | +    pos, neg = [m for m in H.ref_moments() if "error" not in m], negatives()
 128 | +    if len(pos) != 5:
 129 | +        raise ValueError(f"{5 - len(pos)} approved hook(s) cannot be read")
 130 | +    out = {"ruling": "115 (3), report before use", "at": now.isoformat(timespec="seconds"), "seed": SEED,
 131 | +           "question_v2": prompt_v2(pos, neg), "models": {}}
 132 | +    for key in models:
 133 | +        r = build_router(MODELS[key])
 134 | +        res = {}
 135 | +        for variant in ("as ordered", "leave-one-out"):
 136 | +            rows = []
 137 | +            for kind, m in [("approved", x) for x in pos] + [("negative", x) for x in neg]:
 138 | +                if r.spent() >= STOP_USD:
 139 | +                    rows.append({"kind": kind, "moment_id": m["moment_id"], "error": f"stopped at ${r.spent():.4f}"})
 140 | +                    continue
 141 | +                pr = prompt_v2(pos, neg, leave_out=m["moment_id"] if variant == "leave-one-out" else None)
 142 | +                rows.append(dict(rate(r, m, pr, ctx), kind=kind, moment_id=m["moment_id"],
 143 | +                                 channel=m["channel_name"]))
 144 | +                print(f"  {key} {variant} {m['moment_id']}: {rows[-1].get('own')} "
 145 | +                      f"({rows[-1].get('scroll')}/{rows[-1].get('alone')}/{rows[-1].get('setup')}) "
 146 | +                      f"{rows[-1].get('error') or ''}; ${r.spent():.4f}", flush=True)
 147 | +            res[variant] = {"rows": rows, **verdict(rows, MODELS[key])}
 148 | +        out["models"][MODELS[key]] = res
 149 | +    out["spent_usd_reported"] = round(P.Router(env_path=R.ENV, spend_path=SPEND).spent(), 6) if \
 150 | +        os.path.exists(SPEND) else 0.0
 151 | +    os.makedirs(OUT, exist_ok=True)
 152 | +    with open(os.path.join(OUT, "QUESTION_V2_TEST.json"), "w") as f:
 153 | +        json.dump(out, f, indent=1)
 154 | +    return out
 155 | +
 156 | +
 157 | +def report(path=None):
 158 | +    with open(path or os.path.join(OUT, "QUESTION_V2_TEST.json")) as f:
 159 | +        d = json.load(f)
 160 | +    L = ["# RULING 115 (3): THE HOOK QUESTION WITH PBX'S EXAMPLES (report before use)", "",
 161 | +         f"Measured {d['at']} (UTC), seed {d['seed']}, each hook asked alone. A model takes the job only when every "
 162 | +         "approved hook's own-job rating (min(scroll, alone)) is >= 4 AND every negative's is <= 3. The ten rated are "
 163 | +         "the examples the question carries; LEAVE-ONE-OUT asks each with itself left out of the examples.", "",
 164 | +         "| model | variant | approved (5) | negatives (5) | passes |", "|---|---|---|---|---|"]
 165 | +    for model, res in d["models"].items():
 166 | +        for variant, v in res.items():
 167 | +            L.append(f"| {model} | {variant} | {v['approved']} | {v['negatives']} | {'YES' if v['passes'] else 'no'} |")
 168 | +    L += ["", "Every rating (scroll / alone / setup, and the model's reason):", ""]
 169 | +    for model, res in d["models"].items():
 170 | +        for variant, v in res.items():
 171 | +            for r in v["rows"]:
 172 | +                L.append(f"- {model}, {variant}, {r['kind']} {r['moment_id']} ({r.get('channel')}): "
 173 | +                         + (f"{r.get('own')} ({r.get('scroll')}/{r.get('alone')}/{r.get('setup')}) by "
 174 | +                            f"{r.get('backend')}: {r.get('why')}" if "error" not in r else f"NO RATING: {r['error']}"))
 175 | +    L += ["", f"Spent ${d['spent_usd_reported']:.4f} (vendor-reported, SPEND_H115.json).", "",
 176 | +          "The question as asked (as ordered: every example in):", "", "```", d["question_v2"], "```"]
 177 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 178 | +        f.write("\n".join(L) + "\n")
 179 | +
 180 | +
 181 | +def main(argv=None):
 182 | +    ap = argparse.ArgumentParser()
 183 | +    ap.add_argument("--models", default="grok,qwen")
 184 | +    ap.add_argument("--report-only", action="store_true")
 185 | +    a = ap.parse_args(argv)
 186 | +    if not a.report_only:
 187 | +        run([k for k in a.models.split(",") if k])
 188 | +    report()
 189 | +    print(open(os.path.join(OUT, "REPORT.md")).read()[:3000])
 190 | +    return 0
 191 | +
 192 | +
 193 | +if __name__ == "__main__":
 194 | +    sys.exit(main())
 195 | diff --git a/tests/package/test_hook115.py b/tests/package/test_hook115.py
 196 | new file mode 100644
 197 | index 0000000..5384fa4
 198 | --- /dev/null
 199 | +++ b/tests/package/test_hook115.py
 200 | @@ -0,0 +1,107 @@
 201 | +#!/usr/bin/env python3
 202 | +"""RULING 115 (3): the hook question with PBX's examples (tests/package/hook115.py). Offline: the rating call is a
 203 | +stub; the negatives are read from the proof builds (read only)."""
 204 | +import os
 205 | +import sys
 206 | +import unittest
 207 | +import unittest.mock
 208 | +
 209 | +HERE = os.path.dirname(os.path.abspath(__file__))
 210 | +sys.path.insert(0, HERE)
 211 | +import hook115 as X  # noqa: E402
 212 | +import package as PK  # noqa: E402
 213 | +
 214 | +POS = [{"moment_id": f"ref-{i}", "text": f"Bitcoin {i} {{x}}.", "channel_name": f"P{i}"} for i in range(5)]
 215 | +NEG = [{"moment_id": f"neg-{i}", "text": f"You know, {i}.", "channel_name": f"N{i}"} for i in range(5)]
 216 | +
 217 | +
 218 | +class TestPrompt(unittest.TestCase):
 219 | +    def test_the_block_sits_after_the_first_paragraph_and_the_question_is_unchanged(self):
 220 | +        p = X.prompt_v2(POS, NEG)
 221 | +        filled = p.format(hooks='CANDIDATE id="c"', keys='"c": 1')          # braces in a text are escaped
 222 | +        head = PK.HOOKS_PROMPT.split("\n\n")[0]
 223 | +        self.assertTrue(filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS"))
 224 | +        self.assertIn(PK.HOOK_QUESTION, filled)                              # ONE definition of the hook's job
 225 | +        self.assertIn('"Bitcoin 3 {x}." (P3)', filled)
 226 | +        self.assertIn('"You know, 4." (N4)', filled)
 227 | +        self.assertLess(filled.index("OPENERS PBX APPROVED"), filled.index("OPENERS THAT FAIL"))
 228 | +        self.assertLess(filled.index("OPENERS THAT FAIL"), filled.index('CANDIDATE id="c"'))
 229 | +        self.assertNotIn("4 or more", filled)                                # no example carries a rating
 230 | +
 231 | +    def test_leave_one_out_drops_only_the_rated_item(self):
 232 | +        p = X.prompt_v2(POS, NEG, leave_out="ref-2")
 233 | +        self.assertNotIn("Bitcoin 2 ", p)
 234 | +        self.assertIn("Bitcoin 1 ", p)
 235 | +        p = X.prompt_v2(POS, NEG, leave_out="neg-0")
 236 | +        self.assertNotIn("You know, 0.", p)
 237 | +        self.assertIn("You know, 1.", p)
 238 | +
 239 | +
 240 | +class TestRate(unittest.TestCase):
 241 | +    def test_alone_no_cache_the_prompt_only_for_the_call_and_the_verdict(self):
 242 | +        seen = []
 243 | +
 244 | +        def fake(router, ms, ctx, wv, wf, cache="unset", seed=None):
 245 | +            seen.append((len(ms), cache, seed, PK.HOOKS_PROMPT))
 246 | +            return {ms[0]["moment_id"]: {"scroll": 4, "alone": 5, "setup": 3, "why": "w"}}, None
 247 | +        before = PK.HOOKS_PROMPT
 248 | +        with unittest.mock.patch.object(PK, "_writers", lambda r: (set(), set())):
 249 | +            r = X.rate(None, POS[0], "THE V2 PROMPT", None, rate_fn=fake)
 250 | +        self.assertEqual(seen, [(1, None, 7, "THE V2 PROMPT")])
 251 | +        self.assertEqual((r["own"], PK.HOOKS_PROMPT), (4, before))           # restored after the call
 252 | +        rows = [dict(kind="approved", own=4)] * 5 + [dict(kind="negative", own=3)] * 5
 253 | +        self.assertTrue(X.verdict(rows)["passes"])
 254 | +        for bad in ([dict(kind="approved", own=3)] + rows[1:], rows[:5] + [dict(kind="negative", own=4)] + rows[6:],
 255 | +                    rows[:9], [dict(kind="approved", error="x")] + rows[1:]):
 256 | +            self.assertFalse(X.verdict(bad)["passes"])
 257 | +
 258 | +    def test_a_rating_by_another_model_never_counts(self):
 259 | +        rows = [dict(kind="approved", own=4, backend="xai:g")] * 5 + [dict(kind="negative", own=3, backend="xai:g")] * 5
 260 | +        self.assertTrue(X.verdict(rows, "xai:g")["passes"])
 261 | +        other = [dict(rows[0], backend="heimdall:q")] + rows[1:]
 262 | +        self.assertEqual((X.verdict(other, "xai:g")["passes"], X.verdict(other, "xai:g")["approved"][0]), (False, None))
 263 | +
 264 | +    def test_run_both_variants_every_item_and_the_stop(self):
 265 | +        """run() with the calls stubbed: each model asks the ten in both variants (leave-one-out drops the rated
 266 | +        item from the prompt), the rows carry the answering model, and past STOP_USD no call is made."""
 267 | +        import tempfile
 268 | +        from unittest import mock
 269 | +        asked = []
 270 | +
 271 | +        class R:
 272 | +            def __init__(self, model):
 273 | +                self.model, self.n = model, 0
 274 | +
 275 | +            def spent(self):
 276 | +                return 0.30 if self.model == "heimdall:qwen/qwen3.8-27b" and self.n >= 3 else 0.0
 277 | +
 278 | +        def rate(router, m, prompt, ctx, rate_fn=None):
 279 | +            router.n += 1
 280 | +            asked.append((router.model, m["moment_id"], m["text"][:10] in prompt.split("OPENERS PBX APPROVED")[1]))
 281 | +            return {"scroll": 5, "alone": 5, "setup": 5, "own": 5, "why": "w", "backend": router.model}
 282 | +        with tempfile.TemporaryDirectory() as d, mock.patch.object(X, "OUT", d), \
 283 | +                mock.patch.object(X, "SPEND", os.path.join(d, "S.json")), mock.patch.object(X, "rate", rate), \
 284 | +                mock.patch.object(X, "build_router", R), mock.patch.object(X.H, "ref_moments", lambda: POS), \
 285 | +                mock.patch.object(X, "negatives", lambda: NEG), mock.patch.object(X.H, "registry", lambda: []):
 286 | +            out = X.run(["grok", "qwen"])
 287 | +            self.assertTrue(os.path.exists(os.path.join(d, "QUESTION_V2_TEST.json")))
 288 | +            X.report()
 289 | +            self.assertIn("by xai:grok-4.20-0309-reasoning", open(os.path.join(d, "REPORT.md")).read())
 290 | +        g = out["models"]["xai:grok-4.20-0309-reasoning"]
 291 | +        self.assertEqual([len(v["rows"]) for v in g.values()], [10, 10])
 292 | +        self.assertTrue(all(inside for model, mid, inside in asked[:10]))          # as ordered: every example in
 293 | +        self.assertFalse(any(inside for model, mid, inside in asked[10:15]))      # leave-one-out: not itself
 294 | +        q = out["models"]["heimdall:qwen/qwen3.8-27b"]["as ordered"]["rows"]
 295 | +        self.assertEqual(sum("error" in r for r in q), 7)                          # stopped after 3 calls
 296 | +        self.assertEqual(sum(1 for model, *_ in asked if model.startswith("heimdall")), 3)
 297 | +
 298 | +    def test_the_five_negatives_are_read_rated_2_with_their_text(self):
 299 | +        neg = X.negatives()
 300 | +        self.assertEqual([n["channel_name"] for n in neg], [c for _, c in X.NEGATIVES])
 301 | +        self.assertTrue(neg[0]["text"].startswith("You know, it's still an asset"))
 302 | +        self.assertTrue(all(n["moment_id"].startswith("neg-") and n["text"] for n in neg))
 303 | +
 304 | +
 305 | +if __name__ == "__main__":
 306 | +    import unittest.mock  # noqa: F401
 307 | +    unittest.main()
 308 | 
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


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
