# gemma-4-31b-it (google/gemma-4-31b-it) 811 s finish=stop usage in 20751 / out 9004 usd_reported=0.001760 usd~0.197 (upper-bound price)

The code implements the "Story-First Line-ups" feature (RULING 118 (4)) by reading a stories JSON file, generating angles restricted to those stories, and ensuring these angles are tried before the writer's angles. The implementation of the story pool restriction, the L-x writer avoidance, and the exclusion of story angles from the candidate registry is correct.

However, there is a critical defect in the angle contract validation.

### Findings

**[P1] Angle Contract Violation (Minimum Moments)**
In `pipeline/package.py:109`, the call to `check_angles` is:
`check_angles({"angles": [a]}, cleared, 1, hooks=set(hook_ids))`
The third argument is `min_moments`. The governing law and the feature's own docstring (line 85) explicitly state that an angle must hold the contract of **3-8 distinct moments**. By passing `1`, the code allows story angles with only 1 or 2 moments to pass the gate and proceed to the medley stage. This violates the editorial quality gate for angle composition. It should be `3`.

### Verification of Constraints
1.  **Story Isolation**: Verified. `story_pool` filters the `cleared` pool, and this filtered pool (`sel`) is passed to `join_moments`, `pool_fill`, and both `swap_lineup` calls. This ensures no clip or hook from outside the story can enter a story angle's line-up.
2.  **Fallback Behavior**: Verified. `read_stories` handles missing/malformed files by returning an empty list, and `build()` only executes the story logic `if s_angles:`. If no stories exist or no story meets the 3-channel requirement, the build proceeds exactly as before.
3.  **Gate Integrity**: Verified. The medley and subsequent QA gates are called on the resulting `segs` without modification.
4.  **L-x Compliance**: Verified. `story_writers` extracts the grouping models from the JSON, and their vendors/families are added to `writers_v` and `writers_f`, which are used to avoid those models during the line-up's verdict phase.
5.  **Candidate Exclusion**: Verified. `candidates.seed` and `package.load_candidate` both use the `story` lambda to ensure story angles are never saved as or loaded as candidates.

P1_OR_WORSE: 1