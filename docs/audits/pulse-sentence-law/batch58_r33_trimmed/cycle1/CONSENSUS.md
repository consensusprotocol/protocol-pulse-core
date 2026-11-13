# Batch 58 cycle 1: one consensus finding, [low]: implemented

C1 (glm F4, qwen27b agrees): the G16 test meant to show "a cut outside the quiet run" put the cut inside 'But', which
the OLD range (the heard gap) also refuses, so it did not prove the ruling-33 narrowing.
- Implemented: the test now also takes a point the old rule ALLOWS: inside the heard gap, in the trimmed word's decay,
  between the gap's start and the quiet run's start. It asserts that point is clear of both edges by more than
  EDGE_EPS_S, and G16 refuses it ("outside the legal range"). The old 'inside But' point stays as a second subtest.
- test_trimmed_leading: 17 passed, 16 subtests.

Raised but not agreed:
- qwen27b F1 [high], 1 vote, withdrawn in its own text: "the cut range is not constrained to the quiet run". It is.
  edge_plan takes lo = max(gap start, quiet start) and hi = min(gap end, quiet end). The target is clamped to [lo, hi],
  and the valley path cuts at the envelope minimum INSIDE the quiet run (boundary_geometry with a quiet run).
- qwen27b, minor: a trimmed_leading without 'word' reads as '?'. The segment is then still put to the scorer, which is
  stricter, and trimmed_boundary refuses an empty word. Fail-closed both ways; no change.
