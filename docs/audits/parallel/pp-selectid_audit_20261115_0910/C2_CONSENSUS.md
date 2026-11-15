# C2 CONSENSUS — pp-selectid audit 20261115_0910 (the medley's ruling-109 channel gate)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and deepseek-v4.1-flash (glm-5.3-flash's ruling-99 breaker was open, so the
driver took the next family). deepseek gave NO ANSWER (finish=length: 16,000 output tokens of reasoning and an empty
content), so Grok was asked, as ruling 107 (2) says: grok-4.20-0309-reasoning (P1_OR_WORSE: 0). Cycle 2: $0.0282
vendor-reported. AUDIT TOTAL: $0.0315 vendor-reported (cap $1.00: 80 changed lines).

NO P0, P1 OR P2 IS OPEN. No real defect was found, so there is no third cycle (ruling 107 (2)).

1. qwen [P2] "verify current_levels is free". VERIFIED: pipeline/package.py:974-987 loops over the sources in pure Python
   (eligibility.age_hours, spoken, names_bitcoin and vo_fidelity.current_level_values). It has no router and no I/O
   beyond the sources already in memory. The base calls it on every medley build at :2563, after the prescreen; the gate
   calls the same function on the same sources.
2. Grok [P3] "a comment tying 'unusable': why to the pre-gate accumulation". NOT APPLIED: `why` is package.usable's
   (`ms, why = usable(...)`, :2527), the same variable the base's record literal uses (:2563 "unusable": why).
3. Grok [P3] "move the test's imports to module level". NOT APPLIED, deliberately: proof_ledger imports the whole build
   driver (providers, spotlight, lock_precheck, ...). Importing it inside the one test that needs it keeps
   test_medley's other 200 tests off that import.
4. Grok [P3] / qwen [P3] "why_none wording differs from :2587's". INTENDED: the gate stops before step A, so it cannot
   count cleared moments, and it names ruling 109.
5. Both [P3] the pre-existing candidate KeyError (proof_ledger.py:484). TRACKED in the handoff's open items for its own
   change and audit. This change adds no exposure.

THE CODE AS AUDITED IS THE CODE LANDED: FINAL.diff, identical to C2_STEP.diff (pipeline/package.py +18;
tests/package/test_medley.py +62:
TestRuling109Channels, 6 tests). tests/package 553 pass; 10 of 10 mutations killed.
