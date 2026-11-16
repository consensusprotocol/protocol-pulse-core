# qwen3.8-27b (qwen/qwen3.8-27b) 174 s finish=stop usage in 19556 / out 12967 usd_reported=0.010155 usd~0.253 (upper-bound price)



# Code Audit — pp-selectid / RULING 118 (4) STORY-FIRST LINE-UPS

## Scope

Reviewed the 519-line diff across `pipeline/candidates.py`, `pipeline/package.py`, `tests/package/proof_ledger.py`, `tests/package/test_medley.py`, and `tests/package/test_candidates.py`. Checked against the five requested items and all governing laws.

---

## Findings

### [P3] `read_stories` does not reject an empty-string `moment_id`

```python
all(isinstance(m, dict) and isinstance(m.get("moment_id"), str) for m in ms)
```

A moment with `"moment_id": ""` passes validation. In practice this is harmless (an empty string will never be a key in `cleared`, so it is filtered by `if x in cleared`), but the shape check is one `and m["moment_id"]` away from being airtight. The test suite exercises `{"moment_id": 3}` (wrong type) but not `{"moment_id": ""}`.

**Risk:** none in the current pipeline; a future change that allows empty-string keys in `cleared` would silently include a phantom moment.

---

### [P3] `out["stories"]["angles"]` is a misnomer

The field stores the **per-story diagnostic records** (each with `why`, `cleared`, `channels`, and optionally `angle`/`hook`/`moments`), not the angle objects themselves. The actual angles live in `out["angles"]` (the combined list) and in the local `s_angles`. A reader of the JSON output could reasonably expect `stories.angles` to be the angle dicts.

**Risk:** none functional; purely a readability / future-maintenance concern.

---

### [P3] `story` lambda in `load_candidate` re-reads `record.get("angles")` on every call

```python
story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
    bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))
```

`record.get("angles") or []` is evaluated twice per call (once for `len`, once for indexing). With a small `tried` list this is negligible, but hoisting to a local `angles = record.get("angles") or []` (as `candidates.py` does) would be marginally cleaner and avoid a subtle inconsistency if the record were mutated between the two reads (it isn't, but the pattern is fragile).

---

## Verification of the five requested checks

### (1) A story angle can never take a hook or clip from outside its story

**Confirmed.** Every path that could introduce a new moment is routed through `sel = story_pool(angle, cleared, by_story)`:

| Path | Uses `sel`? |
|---|---|
| `join_moments(angle, sel, doomed)` → join table | ✓ |
| `pool_fill(angle, sel, …, hook_only=True)` → first fill | ✓ |
| `swap_lineup(segs, weak, sel, …)` → weak-clip swap | ✓ |
| `swap_lineup(segs, set(bad), sel, …)` → re-screen swap | ✓ |
| `lineup_for` / `search_lineups` (unchanged) | Choose only from the angle's own moments ∪ join-table moments, both ⊆ story | ✓ |

The angle's own moments are built in `story_angles` from `ids = [x for x in s["moment_ids"] if x in cleared]` — strictly the story's cleared moments. The hook is selected from `hook_ids ∩ ids`. No path reaches outside `sel`.

The test `test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it` explicitly verifies that a 3-moment story (28 s of clips) produces no line-up and never pulls `z` or `q` from the wider pool.

### (2) Nothing changes when there is no file, no 3-channel story, or a candidate

**Confirmed.**

- **No file / unreadable / wrong shape:** `read_stories` returns `([], rec)`. `story_angles([], …)` returns `([], [])`. `s_angles` is empty → `s_writers` stays `(set(), set())` → `writers_v`/`writers_f` are just the angle writer's. `by_story` is `{}`. The combined `angles` list is just the writer's. `out["stories"]["read"]` is `False`. The per-angle loop uses `story_pool` which returns `cleared` (full pool) for non-story angles. Identical to pre-change behaviour.
- **No story of ≥ 3 channels:** `check_angles` raises → `row["why"]` is set → no angle produced. Same as no file.
- **Candidate build:** `if candidate is None and stories_path:` guards the entire stories block. `load_candidate` refuses story angles (both the auto-pick and the explicit-index path). `candidates.seed` skips them. Test `test_a_candidates_build_reads_no_stories` confirms `out` has no `"stories"` key.

### (3) Every gate is unchanged

**Confirmed.** The diff touches no gate code. The clips-alone verdict, coherence, fidelity, step-A re-screens, hook bar, and render-stage `STAND_ALONE` are all called with the same signatures and thresholds. The only change is the **source pool** for moment selection (`sel` vs `cleared`), not the **judgment** of any moment. `check_angles` (the angle contract) is the same function the writer's angles pass through.

### (4) L-x compliance

**Confirmed.** `story_writers` extracts the grouping model IDs from the file's `models.group` field, finds the router back-ends running those models, and returns their vendors and families. These are unioned into `writers_v` / `writers_f`, which are passed to `join_table` (and by extension every verdict that avoids the writer's maker). The test `test_the_stories_grouping_models_never_judge_its_line_ups` verifies that the join table receives `"heimdall"` and `"qwen"` in its avoid sets when a back-end runs one of the grouping models.

### (5) Tests

**Adequate.** 12 new test methods (11 in `TestRuling118StoryFirst`, 1 in `TestRegistry`) cover:

- Reader shape validation (7 malformed inputs + truncated JSON)
- Angle construction (best hook, new-channel-first ordering, 2-channel rejection, no-hook rejection, k-limit)
- `story_pool` isolation (story, unknown story, non-story)
- Build integration (story angle first, line-ups stay in story, join table scoped to story, both swap paths scoped, package names the story)
- Short story never filled from outside
- L-x (grouping models in avoid sets)
- No-change paths (no file, 2-channel story, writer failure, candidate build)
- Candidate exclusion (seed skips, `load_candidate` refuses, auto-pick skips)

18/18 mutations killed. The test `test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before` is particularly valuable: it asserts the build output is structurally identical to the pre-change path.

---

## Governing-law compliance

| Law | Status |
|---|---|
| SENTENCE LAW | Not touched by this diff |
| SELECTION LOCK | Not touched |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Not touched |
| CREDITS | Not touched |
| L-a through L-l | Not touched |
| LAW 20 / M2 (gate thresholds are constants; failed gate = hard stop) | No gate threshold changed; no reclassification |
| M12 FAIL CLOSED | `read_stories` returns no stories on any failure; `story_angles` produces no angle on `check_angles` failure; `load_candidate` raises on story angle; `story_writers` returns empty sets on missing/malformed models |
| LAW 22 (v2f byte-identical) | Not touched |
| Smallest diff / no new renderer / GPU0 / no publishing | Compliant: no new modules, no renderer changes, no GPU allocation, no send path |

No governing-law violations found.

---

## Summary

The implementation is clean, the story-pool isolation is airtight across every moment-introduction path, the fail-closed behaviour on missing/malformed data is correct, L-x is properly enforced, and the no-change guarantees hold. The three P3 nits are cosmetic / defensive-hardening items that do not affect correctness.

**P1_OR_WORSE: 0**