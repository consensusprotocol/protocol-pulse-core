# Batch 58 cycle 2: one consensus finding, [low]: implemented (test only)

C1 (glm F3, qwen27b agrees): the fade-retry test mocks edge_plan and cut_candidates. It proves the lock's
trimmed_leading reaches edge_plan, but not that the retry's candidates stay inside the quiet run.
- Implemented: test_the_candidates_of_the_trimmed_plan_all_sit_in_the_quiet_run.
  - Unmocked, on the synthetic source: every IN candidate of cut_candidates(edge_plan(..., trimmed)) lies inside the
    quiet run. These are the candidates _retry_fade_edges walks.
  - The old heard-gap range starts earlier, so the narrowing is what keeps them there.

Raised but not agreed:
- qwen27b F1 [high], 1 vote: "a valley boundary escapes the narrowing". edge_plan has no separate valley branch.
  - A trimmed IN edge is valid only WITH a quiet run, so its pause is that run and the narrowing branch applies.
    trimmed_boundary sets no file_head, so the file-head branch is never taken.
  - accepted_cut's valley path cuts at plan['in']['point'], the envelope minimum taken INSIDE the quiet run
    (boundary_geometry with a quiet run).
  - The new candidates test covers the candidate path. No change.
- glm F1 [low], 1 vote: does adjudicate_lock (ruling 17) keep trimmed_leading in the digest? It copies every key but
  sha256 and re-digests. A test now proves it: an adjudicated trimmed lock keeps its record, takes the approved text,
  and verify_lock passes.
- glm F2 [low], 0 votes: the onset rule runs only when the IN range passed. A failing range is already an error,
  so the clip holds either way. No change.
- Cross-examination, not voted:
  (a) "first onset None s" in the hold text when no onset is measured. That clip holds either way. It is a cosmetic
      text, left as audited, not changed after the second cycle.
  (b) The lock records the trimmed word's surface form ('But,'). That is the run's own transcript, whose sha256 is in
      the same lock, so the digest is stable for that transcript. No change.
test_trimmed_leading: 18 passed, 16 subtests.
