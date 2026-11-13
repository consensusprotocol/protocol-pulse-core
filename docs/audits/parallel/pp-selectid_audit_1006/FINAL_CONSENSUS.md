# pp-selectid audit 1006 (RULING 57: prefer the line-ups with the newest clips): final consensus after cycle 2

- Cycle 2: no P0 or P1 from grok, qwen or glm.
  - qwen: "Yes".
  - grok and glm: "Yes with conditions"; every condition they state is a P2 (below).
- All three confirm qwen's cycle-1 P1 is resolved by F1. A line-up whose ages are all unknown now ranks below any line-up
  with real ages. It is tested.
- All three confirm A1: dropped and doomed are empty when first_fresh runs.

## P2s: recorded, with the evidence

| # | finding | disposition |
|---|---|---|
| N1 | glm: first_fresh() calls lineup_for without repeat_ok. The loop retries with repeat_ok=True when the strict call returns None. So an angle whose only formable line-up needs the L-y 4 repeat is sorted as not fresh. | Verified from the code. It affects only the order in which angles are tried; no gate and no line-up rule changes. glm alone raised it, so it is not consensus. Recorded for the next audited change. |
| N2 | glm: is E.age_hours(published_at, now=None) safe when ctx.now is None? | Not a finding. Context.__post_init__ raises unless now is an aware datetime (pipeline/eligibility.py:164-166), so build() never runs with ctx.now None. |
| N4 | glm: no test that the not-fresh group keeps the writer's order | Recorded. sorted() is stable by the language's definition. The cross-group test (the writer's second angle, which is fresh, is judged first) is in TestRuling57Fresh. |
| G1 | grok: TIME_SENSITIVE_H and FRESH_H are both 24.0 | Intended; they are two separate rulings. TIME_SENSITIVE_H is L-v 3's gate on time-sensitive words. FRESH_H is ruling 57's preference. The orchestrator set each one, so neither follows the other. |
| G2 / Q1 | grok and qwen: first_fresh's extra lineup_for call per angle | Recorded, as in A3. The pool is 5-13 cleared moments, there are at most 3 angles, and each call takes milliseconds before any writer call. |

## Rebase onto HEAD

- The audited diff (C2_STEP.diff) was built on 053cbbc9.
- HEAD then moved to f0524d13. ddfe1dc9 is the coherence change; it touched both files, in other regions.
- git apply applied C2_STEP.diff cleanly to a fresh copy of HEAD. The test hunk landed 45 lines lower.
- The rebased diff's added and removed lines are identical to C2_STEP.diff's.

## Verification

- On the rebased copy, all 11 suites are OK. test_medley has 94 tests: 92 plus TestRuling57Fresh's 2.
- regression_test.sh is run on the worktree before the commit.
