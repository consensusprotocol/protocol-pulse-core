# Batch 107 (ruling 141 (2): the render's STAND_ALONE flag in the ruling's words; a clip the pin already flags is said once): consensus

Heimdall only, one seat per invocation, at medium.

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (checks H1-H4) | PASS (0.92), 28.8k characters of reasoning | FAIL: F1, F3 not defects; F2 applied (defensive) |
| 2 (break-it T1-T3) | PASS (0.92), 41.0k characters | FAIL: F1, NOT a defect |
| 3 (F2's fix alone) | PASS (0.95) | PASS (1.0) |

## gpt-oss findings
- **c1 F1, NOT a defect.** The claim: parentheses around the scorer's reason break "no codes". Parentheses around a plain reason are not a code; the ruled words are "The clip (X) may not stand alone: <the scorer's reason>".
- **c1 F2, APPLIED (0b3a7c55), defensive.** The claim: the model's own reason could echo a snake_case label. Underscores in the reason are now spaces, with a test.
- **c1 F3, NOT a defect.** The claim: a None opener "why" returns "None". `str((r.get("opener") or {}).get("why") or "")` maps None to "", and the `or` gives the default sentence.
- **c2 F1, NOT a defect.** The claim: `re` is not imported. pipeline/run_fresh.py has `import re` at line 48, outside the diff.

## Own evidence
- **MUST_FAIL_OLD_CODE.log:** 6 new or changed tests fail on 04735586 (batch 106 live); the 20 others pass.
- **MUTATIONS.log:** 6 of 6 killed (control: 28 passed).
- **The merged tree:** the full suite list by exit code and both regression scripts. Records in the DoD entry.
