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
`r.chains["coherence_verdict:hook"] = [model]` pins the chain to one model. Whether `providers.Router` internally fails over to a *different* model when the sole chain element errors depends on code not in this diff. If Router retries the same model, fine; if it falls back to a default, CHECK (3) is violated silently and the report would credit the wrong model. The driver prints `r.spent()` after each call, which would expose unexpected spend, but nothing *asserts* the answering model. **[P1]** — the driver should record the answering model's identity (or assert `len(chain)==1` semantics) in each row, since the order requires "on Grok and separately on qwen" and the report's model column is keyed by the *requested* model, not the *answering* one. If Router is known to never fail over with a 1-element chain, downgrade to P2 with a comment.

### [F6] CHECK (1): the v2 prompt differs from production's only by the block — verified, with one caveat
`prompt_v2` = `head + sep + block + "\n" + rest` where `head, sep, rest = PK.HOOKS_PROMPT.partition("\n\n")`. If HOOKS_PROMPT's first paragraph is followed by exactly one `\n\n`, this reconstructs it byte-identically. But if HOOKS_PROMPT contains **more than one** `\n\n` (multiple paragraphs), `rest` still holds everything after the *first* — correct. If HOOKS_PROMPT *starts* with `\n\n` (empty head), `head=""`, `sep="\n\n"`, and the block lands before the (empty) first paragraph — the test's `filled.startswith(head + "\nONE PBX...")`... the test asserts `filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS")`, which pins the block immediately after the first paragraph. If HOOKS_PROMPT's first paragraph ends with trailing whitespace or the separator is `\n\n\n`, the reconstruction is still faithful (partition keeps the rest verbatim). The one real risk: if HOOKS_PROMPT's first paragraph *contains* an internal `\n\n`... impossible, partition splits at the first. **Verified** — the only transformation is the block insertion; `HOOK_QUESTION` and the reply contract are the same bytes (test asserts `HOOK_QUESTION in filled`). Caveat: the test does **not** assert that `rest` (the question + contract) is byte-identical to production's — it asserts only `HOOK_QUESTION in filled`. If the contract's braces survive, fine; but a stronger test would be `self.assertTrue(filled.endswith(PK.HOOKS_PROMPT.partition("\n\n")[2]))`. **[P2]** — strengthen the test.

### [P2] F7 — CHECK (4): the verdict's rule vs. the order — `own` uses ruling 61's `min(scroll, alone)`, but the order says "rates all five approved at 4 or more"
The order's bar: "rates all five approved at 4 or more AND all five negatives at 3 or less". The driver uses `own = H.own_rating(r)` = `min(scroll, alone)` per ruling 61. These agree *only if* ruling 61's definition is the order's intent — the order says "agrees at ruling 85's bar" for the *qwen-returns-the-job* clause, and ruling 61's own-job rating is the established precedent. Consistent with the ruling-112 precedent. **Verified** — but note `setup` is printed yet not part of the verdict; that's ruling 61's definition, not a defect. Also: `verdict()` requires `len(a)==5 and len(n)==5` — if `run()`'s positives check `if len(pos) != 5: raise` guards the input, but a *negative* whose rating-2 record is missing raises in `negatives()` (fail-closed, M12-compliant). Good.

### [P2] F8 — CHECK (6): the tests never exercise `run()` or `report()`
`test_hook115.py` covers `prompt_v2`, `rate`, `verdict`, `negatives` — but `run()`'s row-assembly, the STOP_USD continue-not-break, the JSON/REPORT.md writing, and the final spend read are untested. `report()`'s f-string with `d['spent_usd_reported']:.4f` will raise if the key is missing (fail-closed, fine). The `main()` path with `--report-only` reads a file that must already exist — if `run()` was never executed, `report()` raises FileNotFoundError, which is correct fail-closed behavior but the error message won't say "run the driver first". **[P2]** — one integration test with a fully stubbed router would close the gap; the STOP_USD path (F1) is the most valuable to cover.

### [P3] F9 — `negatives()`'s `hit` selection: `sorted(ra.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))` — the sort key coerces the second tuple element to `str`, which is only needed if raters can be non-strings
If raters are always strings, the `str()` is dead weight; if they can be ints, the sort mixes... actually `str()` makes it deterministic. Fine. But the `next(...)` with a generator over sorted items picks the **first** rating-2-with-text in sorted order — if *two* raters rated the same moment 2 with different texts, the choice is deterministic but arbitrary. The order says "the mid-conversation openers rated 2" — singular per channel, and the test asserts the channel order and the first negative's text, which pins the Melker case. **[P3]** — if two raters' texts differ, the report's negative text depends on rater sort order; a comment noting the determinism rule would help.

### [P3] F10 — `example()` collapses whitespace with `" ".join(m["text"].split())` — good (L-k-adjacent hygiene), but the *negatives' `label`* truncates `why` at 90 chars with `[:90]` mid-word
Cosmetic; the label is prompt-only. **[P3]**.

### [P3] F11 — `run()`'s `out["question_v2"]` is the as-ordered prompt (no leave-one-out), but the report's final fenced block says "The question as asked (as ordered: every example in)" — accurate
No defect. Noted for the record.

### [P2] F12 — CHECK (2): HOOKS_PROMPT restoration — verified, but only via `mock.patch.object` context manager
`rate()` patches `PK.HOOKS_PROMPT` inside a `with` block, so restoration is guaranteed even on exception. The test asserts `(r["own"], PK.HOOKS_PROMPT) == (4, before)` — restoration after a *successful* call. If `rate_fn` raises, the context manager restores, but `rate()` propagates the exception, which `run()` does not catch — one model's exception aborts the whole run, losing the other model's completed rows (they're only in `out`, which is never written because `run()` never reaches the JSON dump). **[P2]** — wrap the per-model loop in try/except, write the partial JSON, and re-raise or report. Fail-closed is satisfied (no report = no use), but the order says "report before use" and a crash loses the spend record's context. Actually — SPEND_H115.json is written by the Router, so spend survives; only the ratings are lost. Still: **[P2]**.

### [P3] F13 — `LIMIT_USD, STOP_USD, SEED = 0.55, 0.25, 7` — the order's cap is "$0.50 in all" for ruling 115, which covers all three parts, not this driver alone
The driver's LIMIT_USD $0.55 *exceeds* the ruling's $0.50 total cap. If parts (1), (2), (3) share a ledger, this driver could spend $0.55 of the $0.50. But it uses its **own** ledger SPEND_H115.json, so the $0.55 is this driver's own limit, and the ruling's $0.50 is presumably the ruling's total across parts — the driver's cap should then be ≤ $0.50 minus parts (1)+(2)'s spend, which the driver cannot know. Since the ledger is its own and the order's cap language ("Ruling 115's cap: $0.50 in all") is ambiguous about whether the driver's limit is within it, this is a documentation question, not a code defect. **[P3]** — note in the report which parts' spend the $0.55 covers.

### [P3] F14 — `main()` prints the first 3000 chars of REPORT.md — `open(...).read()[:3000]` without closing the file
CPython refcounting closes it; fine. **[P3]** — `with` would be tidier.

### [P3] F15 — `import eligibility as E` / `E.Context(now, H.registry())` — the Context's second positional argument
Whether `E.Context` takes `(now, registry)` positionally is assumed from hook112's precedent; if the signature differs, the driver fails at launch, not mid-run. Fail-closed. **[E-] Not a finding** — noted.

### [P2] F16 — CHECK (5) revisited: the STOP_USD check uses `r.spent() >= STOP_USD` *before* each call, but `verdict()`'s `len(a)==5` requirement means a stopped run can never pass
By design: a stopped run reports `passes: no` — correct, "takes the job only when it rates all five...". Fail-closed. But combined with F1's continue-not-break, a stop at the *first* approved moment produces 10 error rows, and the report's variant table shows `| no |` with an approved column of `[None, None, ...]` — the report's `v['approved']` prints the raw list, which for error rows prints `None` (not the error). The report's detail section does show `NO RATING: stopped at $...`. Acceptable. **[P3]** — the summary table's `None`-lists are noisy; print the error count.

### F17 — Laws compliance sweep
- **M12 FAIL CLOSED**: `negatives()` raises on a missing rating-2 record; `verdict()` requires exactly 5+5 ints; `prompt_v2` raises if HOOKS_PROMPT has no `\n\n`. ✔
- **LAW 20/M2**: thresholds (4/3, 5+5, STOP/LIMIT) are module constants; nothing reclassifies. ✔
- **L-k ONE CANONICAL FORM**: the driver compares nothing textual — ratings are ints; the only text comparison is the test's `startswith("You know, it's still an asset")` in the *test*, which is a fixture assertion, not a pipeline comparison. ✔ (Test-side literal, not a violation of TestSites' "no ad-hoc normaliser" — no normaliser is defined.)
- **L-b/L-c/L-e…L-l**: not applicable (no gates, no model-reply field validation beyond `own_rating` — see F2). Note: **L-l** says "a model reply counts only whole" — `rate()`'s record is passed to `verdict()` without field validation (is `scroll` an int? is `why` present?). `H.own_rating` presumably guards, and `verdict()`'s `isinstance` check is the final guard. If `hook_ratings` returns `{"scroll": "4"}` (string), `own_rating`'s `min()` on mixed types raises TypeError → run aborts → fail-closed. ✔ but brittle; **[P3]** — L-l's spirit says validate the reply's fields at the boundary; `verdict()`'s isinstance is that boundary, and it's *after* `own_rating` may have raised. Reorder: validate before `own_rating`. **[P3]**.
- **Smallest diff / M1**: no new renderer/selector; two test-package files. ✔
- **GPU0/publishing**: N/A. ✔

---

## Summary

| # | Severity | Finding |
|---|---|---|
| F1 | P2 | Stopped rows indistinguishable from rating failures in the verdict; continue-not-break |
| F2 | P2 | `rate()` discards `err` when a (partial) record exists; L-l boundary check after `own_rating` |
| F5 | P1 | No assertion/record of the *answering* model; if Router fails over, the report credits the wrong model |
| F6 | P2 | Test doesn't assert the post-block remainder is byte-identical to production's prompt tail |
| F8 | P2 | No test exercises `run()`/`report()`; the STOP_USD path is untested |
| F12 | P2 | An exception in one model's loop aborts the run; partial results never written |
| F3/F4/F9/F10/F13/F14/F16 | P3 | (see above) |

**P1_OR_WORSE: 1**

---

*Reviewer: Gemini 2.5 Pro. Nothing in `pipeline/` changes; the hook job keeps ruling 115 (1)'s question; nothing here is read by a build — the report-before-use contract is honored, and the driver's fail-closed posture (M12) is sound. The one P1 is cheap to fix: record the answering model per row.*