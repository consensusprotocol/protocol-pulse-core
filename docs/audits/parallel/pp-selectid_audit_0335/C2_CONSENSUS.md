# pp-selectid audit 0335 (ruling 35: too_many_sentences retired): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the FIXED diff against the cycle-1 reviews and C1_CONSENSUS.md. Verdicts:
- grok-4.20-0309-reasoning: "Yes ... Ship." No P0 or P1.
- qwen/qwen3.8-27b: P0 none, P1 none; "Yes."
- z-ai/glm-5.3-flash: P0 none, P1 none; "SHIP: yes. No conditions."

All cycle-1 conditions are closed:
- K1: `targets` is bound at eligibility.py:425.
- K2: the grep found one other reader of the reason string, select_by_id.PLAIN:591. It is a table entry that is no
  longer read; KEPT and flagged.
- K3: the expected string is built from the constant, and the 3-sentence boundary is asserted.

Nothing new above P2. Implemented: nothing further.

## Verification

- test_eligibility OK; test_moments, test_select_by_id and test_ledger_build OK.
- regression_test.sh is run before the commit (in the commit message).
