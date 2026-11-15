# glm-5.3-flash (z-ai/glm-5.3-flash) 101 s finish=stop usage in 16081 / out 2812 usd_reported=0.000847 usd~0.090 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261115_0158 (Ruling 111, v4 format re-try)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting of what the other models found:

- **The vision-prompt widening of the body test (glm, accepted by the builder).** I did not flag that the body-equality test only exercised one prompt shape. The builder's fix — asking a vision prompt of both backends and pinning equality — is the right mutation-killer for Y3 (body drift). I missed the vision path as a distinct divergence risk; `FormatBackend.complete`'s vision branch (lines 138–140) is hand-copied, not inherited, and is exactly where a copy rots.
- **The `choose()`-returns-None gap (glm, fixed).** I did not flag that when neither effort yields a single valid answer, `choose` returns `None` and the driver must skip the full run gracefully. The builder's fix (test at lines 555–558, mutation Y13) covers it. Missed by me.
- **The overshoot-bounded-by-measurement argument (glm, documented).** The in-flight-6 × $0.0011 ≈ $0.007 margin argument is sound arithmetic; I did not quantify the in-flight overshoot. It is now documented in the docstring (lines 88–91). Missed the quantification; the conclusion is right.
- **The `names`-fallback masking (glm P2).** I would likely have flagged the silent `(names or {}).get(m) or name(m)` fallback. The builder's rebuttal — `name()` raises KeyError for any non-110 key, so a misconfiguration fails loudly — is correct and I accept it. But note the residual: a *typo'd key that IS a valid 110 key* (e.g. `"dsv4"` passed in `names` for a 111 variant) still silently resolves to the wrong backend. That's a P3, not a P2, given the single call site.

## 2. WHERE DO I AGREE OR DISAGREE?

**qwen's P1 (system-prompt suffix) — AGREE WITH THE BUILDER'S REBUTTAL, DISAGREE WITH QWEN.** The builder is right: production's `HeimdallBackend.complete` (base, :420–421) appends `" Reply with one JSON object only."`, and the body test at lines 461–470 proves the two bodies are equal once the two added fields are popped. qwen's claim that "the test will fail" is wrong — the test passed, and the consensus note confirms it. qwen's finding was a false positive; the consensus process worked.

**glm's P1 (copy-rot / divergence risk) — PARTIALLY AGREE, now adequately mitigated.** The widened test (text + vision, both backends, equality after popping the two fields) is the strongest available drift-catcher short of importing production's body-builder. The residual risk — `P._http_json` / `P._with_backoff` signature drift — remains, but the test would catch it at the next test run, which is the accepted cost of copy-not-inherit. Downgraded to P3-with-test; I concur.

**glm's reasoning-budget note — AGREE, correctly documented.** Reasoning tokens counting against the 16,000-token `max_out` is production's own behaviour; classifying a budget-cut answer as "truncated" and counting it against medium in `choose()` is faithful. The docstring (lines 82–84) now states it. No defect.

**qwen's P2 (shape() heuristics) — PARTIALLY AGREE, downgrade to P3.** The brace-count heuristic (`t.count("{") > t.count("}")`) can misclassify when braces appear inside string values, and the `pos >= len(t) - 1` check is loose. But: this is a *diagnostic label only* — it never gates a verdict, never feeds `choose()` (which uses only outcome/compare/seconds), and the order asks for "the 3 commonest failure shapes" as a report. A mislabelled shape costs a wrong line in TABLE.md, not a wrong decision. P3.

**qwen's P3s (spend stop, 110-compat, table arithmetic) — AGREE, no change.** I independently verified: `ask_one` passes `stop_usd=STOP_USD` (line 233), the test at 509–517 exercises both $0.40 and $0.38; the defaults `keep_raw=False, names=None, prefix="replay110"` (line 10–11) preserve ruling 110's behaviour, and the test at 475–480 proves `raw_text` is absent by default; the table's valid-answer rate `(in_time + late) / (in_time + late + out_of_contract)` (line 360) and agreement-over-valid-answers denominators match the order's definitions.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `run()`'s resume logic can double-count sample rows into the full run.** Lines 294–311: after the sample, `seen = done()` is recomputed (line 309) — good — but `done()` keys on `(record, model)` from RESULTS.jsonl. Sample rows for the *losing* effort (e.g. `medium`) are written to RESULTS.jsonl too. The full-run filter is `(relpath, best) not in seen`, so losing-effort rows are correctly skipped. However, if the driver is re-run after a *partial* sample (crash mid-sample), `choose()` at line 299 reads ALL rows for those record keys — including rows from a previous, *different* CHOICE.json's losing effort — and the scores mix efforts' rows from different runs. Since rows are keyed by (record, model) and the model field *is* the effort, the mixing is actually consistent... but `scores()`'s `rows` filter (line 199, `r["model"] == v`) plus `run()`'s `keys`-filtered read (line 299) means a resumed run's CHOICE.json can be computed over a *partial* sample (some (record, effort) pairs missing), silently skewing valid_rate. No freshness/complete-sample check exists. Fix: record the expected sample (record, effort) count in CHOICE.json and warn when the achieved count is short. This is a resume-robustness gap, not a wrong-result-on-clean-run.

**[P2] `table()`'s ruling-110 comparison column silently degrades when SOURCE_110 rows are missing.** Lines 334–335: `old = RX.summary([r for r in _rows(SOURCE_110) if ...], models=["dsv4"])`. If ruling 110's RESULTS.jsonl is absent or moved, `_rows` returns `[]` (the OSError is swallowed at line 253), `old` is `{}`, and the comparison column renders as `- / -` (lines 361–362) with no warning. The order requires ruling 110's figures "beside" — a silent dash column could be read as "no data" rather than "file missing". Fix: print one warning line when SOURCE_110 yields zero rows. Cheap, prevents a misread report.

**[P3] `shape()`'s "code fence" check precedes the JSON-validity check, so a fenced *valid* answer is labelled "code fence" even though the gateway's json_object mode should never produce one.** Lines 176–180. If json_object mode ever returns a fence, that's itself diagnostic information (the mode isn't being honoured) that the "code fence" label correctly surfaces — so the ordering is arguably right. But note the interaction: a fenced answer that ALSO fails the contract would be counted under "code fence", not "valid JSON, not the contract", which is the more informative label. Diagnostic-labelling preference only; no behavioural impact.

**[P3] `scores()`'s `agree_valid` denominator is units, not answers — matches the order, but the docstring of `table()`'s column header says "agreement on valid answers" while `choose()`'s tie-break uses the same figure.** Consistent between the two, which is what matters; the order's wording ("the agreement on valid answers") is honoured. No change.

**[P3] `ask_one`'s `cap_s=RX.CAP_S` default (line 230) means the 300 s cut is ruling 110's, as the order requires — but the deadline_100_s column (replay110 line 22) still records the ruling-100 deadline, and TABLE.md's header (line 339) says "ruling 100's deadline (the gateway's 120 s)".** Consistent; verified the 120 s figure appears in the test's routing config (line 490, 505). No defect.

**[P3] `run()`'s progress print (line 283) divides nothing — `n["done"] % 20` on a 638-call sample×2 phase (319×2=638... no, sample is 40×2=80) — fine.** Verified: sample phase is 40×2=80 jobs, so the `% 20` prints at 20/40/60/80. No defect.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| FormatBackend body fidelity | 8.5/10 | 9/10 | Vision-prompt equality now pinned; residual copy-rot risk accepted and test-guarded |
| shape() diagnostics | 8/10 | 8/10 | Heuristic looseness confirmed but diagnostic-only; no verdict impact |
| choose() + resume/choice logic | 8.5/10 | 8/10 | New: partial-sample resume can skew CHOICE.json scores (my Cycle 2 finding) |
| Spend/stop compliance | 9.5/10 | 9.5/10 | Overshoot now bounded by measurement and documented; tests cover $0.38/$0.40 |
| Ruling-110 backward compat | 9/10 | 9.5/10 | Defaults proven by test; names-fallback rebuttal accepted (residual typo case = P3) |
| Table/reporting | 8.5/10 | 8.5/10 | Arithmetic verified; new: silent SOURCE_110-missing degradation (P2) |
| Tests | 8.5/10 | 9/10 | 13/13 mutations killed; vision + no-valid-answer cases added |

## 5. FINAL PRIORITY LIST

- **[P2] replay111.py:294–311** — resumed runs compute `choose()` over whatever rows exist; a partial sample silently skews valid_rate/agreement in CHOICE.json. Add a completeness check (expected vs. achieved (record, effort) pairs) and warn.
- **[P2] replay111.py:334–335, 361–362** — missing/empty SOURCE_110 renders the ruling-110 comparison column as dashes with no warning. Print one warning when the source yields zero rows.
- **[P3] replay111.py:190–191** — `pos >= len(t) - 1` and the brace-count heuristic are loose; diagnostic-only, acceptable.
- **[P3] replay111.py:176–180** — "code fence" precedence over "valid JSON, not the contract" hides the more informative label for fenced-but-valid answers; diagnostic preference only.
- **[P3] replay110.py:21** — `names` typo that collides with a valid 110 key silently resolves to the wrong backend; single call site, acceptable.

No P0, no P1. Both Cycle 1 P1s were correctly resolved (one was a false positive, one was fixed by widening the test).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the sample-completeness warning to `run()`'s choice step — it is the only place where a silent, plausible failure mode (a resumed, partial sample) can put a skewed number into CHOICE.json that then drives the full 319-record run.

## 7. PRODUCTION READY?

**Yes with conditions.** Conditions: (a) the CHOICE.json completeness warning (replay111.py:299–303) — a one-line guard, not a redesign; (b) the SOURCE_110-missing warning (replay111.py:334) — one line. Both are report-robustness, not correctness-of-verdict; the measurement machinery, spend stop, backward compatibility, and contract enforcement are sound and test-pinned, and 13/13 mutations killed.

P1_OR_WORSE: 0