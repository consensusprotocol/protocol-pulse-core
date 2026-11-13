# Batch 69 cycle 2: one consensus finding (medium), DISPROVED by reproduction; its example added as a test
glm F1 [medium], agreed by qwen27b: "_ruling73's IN branch can raise cut_lo above cut_hi for a non-file-head edge,
making the range empty while cuttable stays True (cut_lo 10.0, cut_hi 13.0, first word at 14.0)".
It does not. For a non-file-head edge _ruling73 computes ok = hi >= bound and sets cuttable = old cuttable AND ok, with
the reason. Reproduced on the reviewers' exact example:
{'cut_lo': 13.6, 'cut_hi': 13.0, 'cut': 13.0, 'cuttable': False,
 'reason': 'no cut within 400 ms before the first locked word (ruling 73 b)'}.
A not-cuttable plan makes edge_plan's plan['ok'] False, so no cut is placed (write_lock_cut_table records the error and
acceptance HOLDs). The example is now test_b_an_emptied_range_is_not_cuttable (passes). test_ruling73 unit tests: 5 passed.
Single votes, checked, no change:
- qwen27b F1 [high] "hook_lead can move cut_in before the bound": hook_lead's candidates are cut_candidates(src, plan),
  a grid inside [cut_lo, cut_hi] (the narrowed range), and the planned cut is clamped. Nothing it returns lies outside.
- glm F2 / cross-examination: an emptied range keeps an out-of-range 'cut' value with cuttable False, which blocks it.
  The point may precede the decoded end, but the OUT clamp in edge_plan and accepted_cut keeps every cut >= the end.
- glm F3 / cross-examination: the delivered test also asserts ruling 73 on every cut (cycle 1). The pre-check cuts its
  final lock (trimmed fields included) with the role's label, as the render does.
