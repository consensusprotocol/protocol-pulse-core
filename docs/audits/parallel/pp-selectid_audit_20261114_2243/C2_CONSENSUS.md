# C2 consensus (FINAL), audit 20261114_2243 (written by the builder; reviewers qwen3.8-27b and glm-5.3-flash, Heimdall)

Both reviewers: P1_OR_WORSE: 0 on the fixed diff. Grok not asked (they agree). No third cycle (no real defect).
- qwen's one [P1] tag (F4, the sleep outside the lock) ends in its own "No defect": a dead process's reservations are
  dropped by _ledger().
- C1's P1 (the wait before the call's deadline): both reviewers accept the opt-in as the fix.

Applied after cycle 2 (tests and a comment, no logic changed; FINAL.diff holds them):
- glm N1 (P2): test_ledger_router's opt-in test now also asserts that the second call WAITED (its own duration
  >= 0.25 s while the first was held 0.3 s), not only that it answered in the end.
- glm N5 (P2): proof_ly.RESERVE_WAIT_S's comment states the invariant: only a caller with no time budget of its own
  may wait; give the build a deadline and the value must be derived again.
Not changed:
- glm N6 (P3) is mistaken: test_ledger_router uses wait_for (metered_miss waits for the late_error line).
- glm N2-N4 (P3): cosmetic.
After the polish: the affected suites (71 tests) pass, and 9 of 9 mutations are killed (MA1-MA3 the meter, MB1-MB4
the wait, MC1 the ledger build does not opt in, MC2 every router waits by default). Every handoff suite (32 suites,
694 tests) passed on the cycle-2 code before the polish.
