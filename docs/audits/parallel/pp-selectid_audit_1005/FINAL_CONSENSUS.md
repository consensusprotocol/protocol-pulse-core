# pp-selectid audit 1005 (ruling 52's hook rating in the coherence verdict): final consensus after cycle 2

- Cycle 2: no P0 or P1 from grok, qwen or glm. glm's cycle-1 P1 is resolved: no consumer compares the coherence
  verdict's keys exactly, and hook_rule is inert, as in the clips-alone verdict.
- All three confirm:
  - HOOK_QUESTION is defined once and used by both verdicts;
  - MEDLEY_PROMPT is byte-identical;
  - the coherence verdict's clips after the hook and vo_point are judged as before;
  - a malformed reply is never a pass.
- Verification: test_medley 92 OK; every other suite OK; regression_test.sh is run on the worktree before the commit.
