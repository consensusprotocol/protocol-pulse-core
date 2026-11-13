# pp-selectid audit 0728 (one canonical token for a trimmed word): final consensus after cycle 2

- Cycle 2: no P0 or P1 from grok, qwen or glm. All three are production ready (grok: "yes with conditions").
- grok's condition, that no other fixture asserts the old reason text: verified. The trim reason's only occurrence was
  package_pin.py's own line, now replaced, and no test asserts it. The phrase "is not one of" appears elsewhere only in
  unrelated messages (release_auth, eligibility, vo_fidelity, the speaker check).
- The change makes this branch accept exactly what the render's pinned.validate_schema accepts: one canonical token,
  in but/and/so/well/now/yeah.
- Verification: test_medley 81 OK; every other suite OK; regression_test.sh is run on the worktree before the commit.
