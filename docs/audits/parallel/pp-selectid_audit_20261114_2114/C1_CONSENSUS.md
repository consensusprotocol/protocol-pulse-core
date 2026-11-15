# Cycle 1 consensus: pp-selectid audit 20261114_2114 (RULING 108: batch 3's own build ledger, cap and stop)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Both report P1_OR_WORSE 0, so Grok was not asked.
Cost: $0.0035 vendor-reported. The change is 30 lines, so the small cap applies: one reviewer set, two cycles, $0.30.

IMPLEMENTED (glm P2):
- the test pins LY_LIMIT_BASIS == "reported";
- the test pins one build's headroom: LY_LIMIT_USD - LY_STOP_USD >= $0.50.

NOTED, NO CHANGE:
- qwen P2 / glm P2 (the headroom is an assumption). The stop is the soft pre-check. The hard guard is the Router's
  limit: every paid call RESERVES its upper bound before it runs, and none passes $4.50 (providers.Router._reserve).
  So a build that would cost more than the headroom is stopped mid-build, never paid past the cap.
- glm P2 (a second hard-coded SPEND_LY.json): a grep finds one other use, tests/package/replay85.py. That is the
  ruling-85 replay tool, not run in batch 3; no build path uses it. proof_ledger.build_router passes PL.SPEND.
- glm P2/P3 (STATE line 1 "saying"): the builder writes STATE from the build's printed refusal, so it is not this
  module's side effect.
