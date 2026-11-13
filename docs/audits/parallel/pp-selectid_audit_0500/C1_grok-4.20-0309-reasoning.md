# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 25 s finish=stop usage in 7037 / out 364 usd~0.044 (upper-bound price)

**P0: none**

**P1: none**

**P2: pipeline/package.py:47 (and ly_shape:37)**  
The re-line path and ly_shape guard both assume the question is always segs[0] (the hook) and that the first flagged join is exactly "hook -> clip_01". This matches the added question_hook() predicate and the test rig, but the diff contains no explicit guard against a question-ending clip appearing in any other position. (The eligibility change prevents selection, but that is in a different module.)

**P2: tests/eligibility/test_eligibility.py:64**  
The test removal of "not_statement" from the hook expectation is correct per the diff, but the new clip-role assertion only exercises a synthetic ctx("clip") call. The diff provides no coverage of real middle/last-clip selection paths that would invoke the same eligibility logic with role != "hook".

**P2: pipeline/eligibility.py:11**  
The added `and role != "hook"` implements Ruling 37 exactly as described. No other call sites or roles are altered in the diff, satisfying the "only the hook" constraint *within the visible code*. The orchestrator's explicit relaxation is acknowledged in comments; no standing law (L-m, L-j, M20, etc.) is violated by the shown lines.

All three required behaviors are present and exercised by the new tests:
- question ends hook only (eligibility + test)
- flagged join after question hook never produces a sealed bridge (build re-line + ly_shape refusal)
- dropped set grows, preventing infinite re-line loops (visible in the Rig test and the .add() call)

No unrelated changes, no relaxation of other gates, no new renderer/selector.

**SHIP: yes**