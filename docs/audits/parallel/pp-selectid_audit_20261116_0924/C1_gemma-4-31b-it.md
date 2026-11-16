# gemma-4-31b-it (google/gemma-4-31b-it) 327 s finish=stop usage in 20836 / out 3973 usd_reported=0.001139 usd~0.122 (upper-bound price)

The code implements **RULING 118 (4): STORY-FIRST LINE-UPS** as requested. It introduces a mechanism to prioritize angles derived from a pre-grouped stories file while maintaining all existing quality gates and the "writer-centric" build flow.

### Audit Analysis

**1. Story Angle Restriction (Inside the Story)**
The implementation ensures that story angles are strictly contained within their respective stories across all potential modification paths in the `build()` loop:
- **Join Table:** `join_moments` is called with `sel` (the restricted pool), ensuring the join table only contains moments from the same story.
- **Pool Fill:** `pool_fill` is called with `sel`, preventing the line-up from being filled by moments outside the story.
- **Swaps:** Both `swap_lineup` calls (for weak clips and re-screen failures) use `sel`, ensuring any replacement clip is also from the same story.
- **Selection:** `story_pool` correctly filters the `cleared` pool based on the `story_id` if the angle is a story angle.

**2. Fallback and Candidate Behavior**
- **No File/Invalid Shape:** `read_stories` implements a strict "all-or-nothing" validation. If the file is missing, unreadable, or any single story is malformed, it returns an empty list and a record of the failure, allowing the build to proceed as before.
- **Candidate Exclusion:** The code correctly prevents story angles from becoming candidates. `candidates.seed` and `load_candidate` both use the `story(t)` lambda to skip story-based line-ups, ensuring they are not cached as candidates for future builds.
- **Candidate Builds:** In `build()`, the `if candidate is None and stories_path:` block ensures that when a specific candidate is being re-processed, the story-first logic is bypassed.

**3. Gate Integrity and Ordering**
- **Ordering:** `angles = sorted(s_angles, key=order) + sorted(angles, key=order)` correctly places story angles ahead of the writer's angles while maintaining the rank/freshness sorting key.
- **Gates:** The loop `for ai, angle in enumerate(angles):` processes story angles through the exact same pipeline (medley, fidelity, context, coherence, value) as writer angles. No gates were bypassed or modified.
- **Writer Gateway:** The check `if not angles: return out` (where `angles` are the writer's results) ensures that if the writer fails to produce any angles, the build stops, preserving the ruling that the writer's gateway controls the build's progression.

**4. Law L-x (Writer Avoidance)**
- `story_writers` extracts the vendors and families of the models used for grouping.
- These are merged into `writers_v` and `writers_f` in `build()`, which are then used to populate `writer_avoid`. This ensures that the models that created the story grouping cannot judge the resulting line-ups.

**5. Test Coverage**
The `TestRuling118StoryFirst` suite is comprehensive, covering:
- The "all-or-nothing" file reader.
- The angle contract (3+ channels, passing hook, 3-8 moments).
- The priority of new channels over rank score in `story_angles`.
- The restriction of joins, fills, and swaps to the story pool.
- The exclusion of story angles from the candidate registry.
- The correct attribution of the angle source in the package.

### Findings

No defects found. The implementation is precise and adheres to all governing laws and the specific ruling.

P1_OR_WORSE: 0