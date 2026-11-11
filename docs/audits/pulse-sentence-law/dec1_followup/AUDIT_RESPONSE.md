# DEC-1 follow-up — audit dispositions (2026-11-11 ET)

Cross-LLM (GPT-4o / Grok / Gemini, 2 cycles):
- U3 (unanimous): tail_rows correct and fail-closed — kept as is.
- U1/M2 "scope incomplete vs the feature name": the audit harness reuses one feature name
  (`pulse-sentence-law`) for every step of the mission; this commit is scoped by its own message. The
  sentence law itself landed in 99add647 / 9ad93344 / 0449a3ce.
- U2 "untouched laws must read UNVERIFIABLE, not COMPLIANT": agreed; this file records them so.
- M1 "verdict_for not in the diff": it is run_fresh's existing verdict function (HOLD on any FAIL row);
  noted in the test.
- X1 sys.path in tests: the existing pattern of every pipeline test; not changed here.

Heimdall (deepseek / qwen27b / glm): run_fresh.py chunk — no findings. Test chunk [low] "luma-failure ->
HOLD not asserted": IMPLEMENTED (`verdict_for(tail_rows(False, False))` -> HOLD).

Late Heimdall findings on 9aa4fdb2 (G8 source, G9 row): see
docs/audits/pulse-sentence-law/dec1_calibration/HEIMDALL_RUN_FRESH_RESPONSE.md (G8 rejected on
measurements, residual gap = OD-3; G9 row split implemented here).
