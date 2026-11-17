# Batch 100 (ruling 131 (A)+(B)), cycle 1: consensus

Panel: Heimdall only (the spend freeze). One seat per invocation at `HEIMDALL_AUDIT_EFFORT=medium`. glm is out
(ruling 119 (3)).

| Seat | Model | Verdict | Findings | Completion tokens | Trace |
|---|---|---|---|---|---|
| qwen27b | qwen27b | PASS | 0 | 19,252 | Traced A1-A7 against the diff's code, quoting `took = ...`, `_majority_text` and both `lock_lines` branches. It checked the word_diff before/after equivalence (A7). |
| gptoss | openai/gpt-oss-20b | PASS | 0 | 16,625 | Traced A1-A7 against the code. Its tail repeats one line ("edl.get('moments_package_sha256') is None ... Good") and concludes PASS. |

**Consensus:** no finding. Nothing to implement.

**Not judged by either seat:**
- whether (A)'s scope matches the ruling beyond the diff;
- the pin_side ruling 84 (b) two-function-word HOLD (unchanged code, flagged to the orchestrator).

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: 20 failing results on the old code. The 2 passing tests are the intended controls.
- MUTATIONS.log: 22 of 22 killed. M10 was killed only after test_canon.TestCurrencyFree was added (dd628733).
