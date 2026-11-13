# pp-selectid audit 0815 (RULING 52): final consensus after cycle 2

- Cycle 2: no P0 or P1 from grok, qwen or glm; all three production ready.
- Every cycle-1 point is settled from the code:
  - A1: the integral float follows the clips' existing strict-int contract, failing closed;
  - A2: the hook's derived rating is inside the unchanged min;
  - A3: no reader checks the verdict's shape, and the seal records only status / by / replayed / measured / flagged;
  - A4: the derivation runs only after the contract;
  - A5: the formula is min.
- Verification: test_medley 82 OK; every other suite OK; regression_test.sh is run on the worktree before the commit.
