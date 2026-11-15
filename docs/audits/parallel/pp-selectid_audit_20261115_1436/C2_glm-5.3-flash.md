# glm-5.3-flash (z-ai/glm-5.3-flash) 172 s finish=stop usage in 12368 / out 5020 usd_reported=0.001006 usd~0.112 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261115_1436 (hook115.py + test_hook115.py, FIXED diff)

Reviewer: 2nd pass, 308-line diff, nothing in `pipeline/` touched. I now have the other models' Cycle 1 outputs and the C1 consensus. This is my final review.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest about my Cycle 1 gaps (reconstructing from the consensus record, since my own Cycle 1 text isn't reproduced):

- **The model-credit question (glm F5).** I evidently did not press the "does the report credit the *answering* model?" angle. The fix — `verdict(rows, model)` counts a rating only when `r.get("backend") == model` (hook115.py:115) — is the right shape: fail-closed, report-only, and it strengthens the report's own guarantee. I missed that a one-model chain still needs the *report* to prove which model answered, not just the routing to guarantee it.
- **The $0.55-vs-$0.50 discrepancy (qwen).** The order says "cap: $0.50 in all"; the original code had `LIMIT_USD = 0.55`. I likely read the $0.55 as a safety margin and moved on. It's now $0.50 (line 46) with a comment explaining why the router's ceiling legitimately sits above the operational stop (it reserves list-price upper bounds per call). Correct resolution — the *cap* is the ceiling, the *stop* is the governor, and they were conflated.
- **`run()`/`report()` were never exercised (glm F8).** A driver whose only tests cover `prompt_v2`/`rate`/`verdict`/`negatives` but never the orchestration — the stop, the variant loop, the JSON write — had an untested spine. The new `test_run_both_variants_every_item_and_the_stop` (test_hook115.py:264-296) closes that. I should have flagged it.

What I *did* catch that survived: the stopped-row/verdict ambiguity (glm F1, agreed, not changed — I concur with the reasoning), and the report-only nature of the whole artifact.

## 2. WHERE DO I AGREE OR DISAGREE?

**glm F1 (stopped row reads like a rating failure) — AGREE with NOT CHANGED, and with the reasoning.** The row carries `"error": f"stopped at $..."` (line 139), the report prints "NO RATING: stopped at $x" (line 174), and the verdict fails closed because `own` is absent. For a "takes the job only when" clause, fail-closed-on-no-rating is the correct semantics — a stopped model *hasn't* passed, and pretending otherwise would be the bug. The distinction glm wanted (a `stopped: true` marker) is now effectively present in the report via the error string. Resolved.

**glm F2 (rate() drops `err` when a record exists) — AGREE with NOT CHANGED.** `rate_fn` is `PK.hook_ratings` on exactly one moment; a record for that moment and an error for the same call are mutually exclusive in practice. The `err or "no rating"` fallback (line 109) covers the record-absent case. Residual risk: if `hook_ratings` ever returns a *partial* record, `H.own_rating(r)` could raise — but `verdict()`'s `isinstance(x, int)` guard (line 118) catches a non-int, and an *exception* in `own_rating` would propagate. That's a P3, not worth a change: the driver is report-only and a crash is louder than a silent wrong verdict.

**glm F3 (brace-escaping trace) — AGREE, correctly resolved as correct.** The trace: production text `"Bitcoin 0 {x}."` → `BLOCK.format` substitutes it → `.replace("{"→"{{")` doubles it → final `.format(hooks=..., keys=...)` renders it back. The test's f-string `f"Bitcoin {i} {{x}}."` evaluates to the same literal, so test and production paths coincide. The test at line 221 (`filled = p.format(hooks=..., keys=...)`) exercises the real round-trip. A comment would be nice; not required.

**glm F4/Grok (shared SPEND_H115.json, no locking) — AGREE, P3.** `run()` is sequential; the final spend read (lines 149-150) now guards with `os.path.exists(SPEND)` (the C1 fix — good, it no longer constructs a ledger when none exists). Two *concurrent* invocations would race the ledger, but the driver is a human-run measurement tool, not CI. Note-and-move-on.

**qwen ($0.55 > $0.50 cap) — AGREE, correctly FIXED.** See §1. The comment at lines 46-47 now documents the ceiling-vs-stop relationship, which is the durable lesson.

**Grok (negatives test reads proof builds, not hermetic) — AGREE with NOT CHANGED.** The driver's *entire input* is those proof builds; mocking them in the unit test would test the mock. The test at lines 298-302 pins the five are found, rated 2, with the order's own example's text — that's the valuable assertion. Hermeticity would cost more than it buys here.

**Grok (`partition("\n\n")` fragility) — AGREE with NOT CHANGED.** `partition` splits at the *first* occurrence only, which is exactly `split("\n\n", 1)` semantics; the test pins the block right after the first paragraph (line 223) and that `HOOK_QUESTION` survives (line 224). If `HOOKS_PROMPT` gains an earlier blank line, the test fails loudly. Fine.

**glm F5 (model credit) — AGREE, FIXED, and the fix is better than the finding.** Note the subtlety: `verdict(rows)` with `model=None` (used in the offline test, line 252-253) counts *any* rating, while the production path passes `MODELS[key]` (line 147). That's the right default — the test exercises the rule, production exercises the guarantee.

**glm F8 (run/report untested) — AGREE, FIXED.** The new test covers: both models, both variants, 10 rows each (line 291), every-example-in for "as ordered" (line 292), leave-one-out drops the rated item (line 293), the stop fires after 3 calls with 7 error rows (lines 294-296), the JSON is written, and REPORT.md carries the answering model (line 289). This is the test that makes the driver trustworthy.

## 3. NEW FINDINGS (Cycle 2)

**[P2] N1 — `verdict()`'s `model` parameter compares against the *full* model string, but the report's "by <model>" prints `r.get("backend")` — and nothing verifies they're the same vocabulary.** Lines 115, 147, 173. If `hook_ratings`' record's `backend` field ever uses a different naming convention than `MODELS`' keys (`"xai:grok-4.20-0309-prod"` vs `"xai:grok-4.20-0309-reasoning"`), every rating silently counts as "no rating" and both models fail — a *false negative* verdict, not a false pass, so it fails safe, but the report would read "passes: no" with no hint why. The new test (line 259) does pin `backend="xai:g"` matching the verdict's model, so the *mechanism* is tested; only the *vocabulary* is assumed. Mitigation: the report prints the backend on every rating (line 173), so a human comparing report to MODELS would spot it. Downgrade to P2→P3: the failure mode is loud-in-report, silent-in-verdict, and the driver is report-only. **P3.**

**[P2] N2 — `run()`'s stop check uses `r.spent() >= STOP_USD` *before* the call, but the printed spend after the call (line 146) can exceed STOP_USD, and the *next* iteration's check catches it — meaning the last call's cost is unbounded by STOP_USD.** This is by design ("no call starts at STOP_USD" — the docstring, line 23) and the router's `limit_usd=0.50` bounds it. But note: the *leave-one-out* variant runs second, so if the "as ordered" variant alone crosses $0.25, the leave-one-out variant gets *zero* ratings — yet the report's table (line 167) would show the leave-one-out row as "no" with 10 "NO RATING" lines, indistinguishable at a glance from a model that rated poorly. The report's every-rating list does disambiguate (line 174). **P3** — report-only, human-read.

**[P2] N3 — `test_run_both_variants_every_item_and_the_stop`'s fake `rate` (line 278) shadows the module's `rate` via `mock.patch.object(X, "rate", rate)`, but the fake's signature lacks `rate_fn=None`... no, it has it.** Checking: `def rate(router, m, prompt, ctx, rate_fn=None)` — matches. But the fake *ignores* `ctx`/`prompt`-vs-`HOOKS_PROMPT` restoration, which is fine because the real `rate`'s mock.patch of `HOOKS_PROMPT` is what the *other* test (line 241-251) covers. However: the fake's `asked` list records `m["text"][:10] in prompt.split("OPENERS PBX APPROVED")[1]` — this checks the text appears *after* the positives header, but for a *negative* moment in the "as ordered" variant, the text appears after "OPENERS THAT FAIL", which is also after "OPENERS PBX APPROVED" in the block. So the assertion (line 292, `all(inside for ... asked[:10])`) passes for the right reason. And line 293's `not any(inside for ... asked[10:15])` — the first five of leave-one-out are the *approved* items, each with itself dropped; `m["text"][:10]` for `ref-0` is "Bitcoin 0 " which... wait, the leave-one-out prompt for `ref-0` still contains "Bitcoin 1 " through "Bitcoin 4 " — but the *asked* moment's own text "Bitcoin 0 " is what's checked, and it's genuinely absent. Correct. But there's a subtle trap: `"Bitcoin 1 " in prompt` would also match "Bitcoin 1 " inside... no, the texts are `f"Bitcoin {i} {{x}}."` — after prompt_v2's escaping, the prompt holds `Bitcoin 1 {{x}}` — wait, no: the *test's* POS texts are `f"Bitcoin {i} {{x}}."` = `"Bitcoin 0 {x}."` literally, and prompt_v2 escapes them to `Bitcoin 0 {{x}}` in the returned prompt. So `m["text"][:10]` = `"Bitcoin 0 "` (10 chars: B-i-t-c-o-i-n-space-0-space) — that's present as `Bitcoin 0 {{x}}`'s prefix. And for leave-one-out of `ref-0`, "Bitcoin 0 " is genuinely gone. The assertion is sound. **No finding** — I traced it; it's correct, but this took effort, which itself is the P3: a comment on the escaping round-trip (glm's F3) would have made this trace trivial.

**[P2] N4 — `report()` reads the JSON written by `run()` with no freshness/consistency check, and `main(--report-only)` will happily regenerate REPORT.md from a *stale* QUESTION_V2_TEST.json.** Lines 157-178, 186-188. If someone edits the prompt and re-runs with `--report-only`, the report's "The question as asked" section shows the *old* question. Report-only, human-read, and the JSON carries `"at"` (line 130) so the staleness is discoverable. **P3.**

**[P2] N5 — `run()`'s `pos` filter, line 127: `[m for m in H.ref_moments() if "error" not in m]` silently drops errored moments, then line 128-129 raises if `len(pos) != 5`.** Good — the count check converts silent-dropping into a loud failure. But the error message `f"{5 - len(pos)} approved hook(s) cannot be read"` assumes exactly 5 expected; if `ref_moments()` ever returns 6 (a sixth approved hook), the message says "-1 approved hook(s) cannot be read" — nonsense, but the *check* still fires correctly (6 ≠ 5 → raise). Actually wait: if 6 come back, `len(pos) != 5` → raise with "−1 approved hook(s) cannot be read". Confusing but not wrong. **P3.**

**[P2] N6 — the `qwen`-wins-the-job-back clause ("agrees at ruling 85's bar") is not implemented or measured.** The order's parenthetical: "qwen wins the job back if it passes both and agrees at ruling 85's bar." The driver measures pass/fail per model per variant but computes no *agreement* metric between Grok and qwen — no comparison of their ratings, no ruling-85-bar check. The report shows both models' ratings side by side, so a human can eyeball agreement, but the order's conditional is a *computed* criterion, and nothing in the code computes it. Is this in scope? The order says "(3) ... in parallel, report before use" — the parenthetical describes when qwen wins the job back, which is arguably the *orchestrator's* decision, not the driver's. But the driver is the measurement instrument for that decision, and it stops one step short: it produces the ratings but not the agreement verdict. **P2** — the report gives the raw materials, but the ruling-85 agreement (whatever its bar: same ratings? same pass? rating-distance ≤1?) is neither computed nor reported, so the orchestrator must derive it by hand from the every-rating list. This is my strongest new finding.

**[P2] N7 — `verdict()`'s `own` lambda, line 115: `r.get("own") if model is None or r.get("backend") == model else None` — when `model` is given and the row has NO `backend` (e.g. a stopped row, which has only `kind`/`moment_id`/`error`), it returns None.** Correct (fail-closed). But when `model is None` and the row is a stopped row, `r.get("own")` → None → `isinstance(x, int)` fails → not a pass. Also correct. No finding — traced.

**[P2] N8 — `main()`'s `--models` parsing, line 187: `[k for k in a.models.split(",") if k]` — an unknown key like `--models grok,claud` raises `KeyError` at line 133 (`MODELS[key]`) *after* the router for `grok` has already been built and possibly spent.** Actually, `build_router` is called per-iteration; if `grok` runs first and `claud` raises, the JSON is never written (the exception propagates past line 152), so the grok spend is recorded in SPEND_H115.json but no report. Recoverable by re-running (the ledger persists, and the stop check will... no — a fresh `run()` builds a *fresh* Router on the same ledger, so `r.spent()` reflects prior spend and the stop check correctly skips). Actually that's *good* behavior: the ledger persists, so a re-run resumes under the cap. **P3** — but note the JSON/report are only written on *complete* success; a mid-run crash loses the partial report entirely. For a $0.25-0.50 measurement, acceptable. **P3.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| prompt_v2 construction & escaping | 9/10 | 9/10 | Traced again (N3); correct, but the escaping round-trip needs a comment to be maintainable |
| Isolation (cache/ledger/HOOKS_PROMPT) | 9/10 | 9.5/10 | C1 fixed the final-spend-read ledger construction; `exists` guard at 149-150; mock.patch restores (tested, line 251) |
| Model pinning & credit | 8/10 | 9.5/10 | glm F5's fix (backend-verified verdict, lines 115/147/173) closes the report-credit gap; residual: vocabulary assumption (N1, P3) |
| Verdict rule vs. order | 9/10 | 9/10 | Matches the order exactly; the ruling-85 agreement clause remains uncomputed (N6, P2) |
| Spend cap compliance | 8.5/10 | 9.5/10 | LIMIT_USD now $0.50 = the ruling cap (line 46); stop-at-$0.25 governor; ledger persists across re-runs (N8) |
| Test coverage | 7/10 | 9/10 | run()/report() now exercised end-to-end with the stop (lines 264-296); negatives test pins the order's own example (line 301) |
| Report fidelity | 8/10 | 8.5/10 | Every rating carries its backend; stopped rows say "stopped at $x"; agreement metric still absent (N6) |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none.

**P1 HIGH:** none.

**P2 MEDIUM:**
- **[P2] N6** — hook115.py:112-120, 157-178: the ruling-85 agreement clause ("qwen wins the job back if it passes both and agrees at ruling 85's bar") is not computed anywhere. The driver produces both models' ratings but no agreement verdict; the orchestrator must derive it by hand. Add an `agreement()` (or at minimum a report line comparing the two models' ratings per moment) — the order's conditional is a *measured* criterion, and the measurement instrument should close the loop.

**P3 (should-fix, non-blocking):**
- **[P3] N1** — hook115.py:115/147/173: `verdict`'s model string vs. the record's `backend` vocabulary is assumed identical; a mismatch fails safe (false-negative) but silently. One report line noting "backend values: {set of backends}" would surface it.
- **[P3] N3** — hook115.py:88-92 / test:214: the brace-escaping round-trip (f-string doubling vs. runtime doubling) is correct but non-obvious; a one-line comment at the `.replace` (line 92) would have saved the trace.
- **[P3] N4** — hook115.py:186-188: `--report-only` regenerates REPORT.md from whatever QUESTION_V2_TEST.json exists, with no staleness warning; the `"at"` field (line 130) makes it discoverable, but a printed "measured at" line in `main` would be kinder.
- **[P3] N5** — hook115.py:128-129: the "5 - len(pos)" error message assumes exactly 5; harmless (the check itself is count-agnostic).
- **[P3] N8** — hook115.py:152: the JSON/report are written only on complete success; a mid-run crash loses the partial report (the ledger persists, so a re-run resumes under the cap — good).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Compute and report the ruling-85 agreement between Grok and qwen (N6) — it's the one clause of the order the driver measures the inputs for but never evaluates, and it's the clause that actually decides who takes the job.

## 7. PRODUCTION READY?

**Yes with conditions** — noting this artifact *is* the report-before-use prerequisite, so "production ready" here means "ready to run for the ruling's evidence":

1. **[P2→condition] Add the agreement computation** (N6): either a computed ruling-85 agreement verdict in the report, or an explicit report line stating the agreement is adjudicated elsewhere under the order's parenthetical. One or the other, so the report is self-contained evidence.
2. **[P3→condition] One-line comment** at hook115.py:92 documenting the brace-escaping round-trip (the test's f-string doubling and the runtime doubling coincide by f-string semantics — this took a three-model trace to confirm).
3. No code changes required for: the $0.50 cap (fixed, correctly documented), the model-credit verdict (fixed, fail-closed), the stop semantics (fail-closed, correctly reported), or the isolation (verified: `cache=None` at line 107, `HOOKS_PROMPT` restored and *tested* restored at line 251, own ledger, own proof directory).

The six PLEASE CHECK items: (1) v2 = production + the block only — **yes** (test lines 219-229: head preserved, question unchanged, positives-then-negatives, no ratings in examples); (2) no production cache read/write, prompt restored — **yes** (cache=None, line 107; restoration tested, line 251); (3) only the named model answers — **yes** (one-model chain, line 98, plus the backend-verified verdict, line 115); (4) verdict = the order's rule — **yes** (lines 118-119, tested including the missing-rating case, line 255); (5) stop under the cap — **yes** (no call starts at/after $0.25, line 138; router ceiling $0.50 = the ruling cap, line 46; tested, lines 294-296); (6) the tests — **yes, 6 offline, all pass, now covering the orchestration**.

P1_OR_WORSE: 0