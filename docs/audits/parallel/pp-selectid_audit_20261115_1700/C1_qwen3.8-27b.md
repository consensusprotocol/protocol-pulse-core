# qwen3.8-27b (qwen/qwen3.8-27b) 51 s finish=stop usage in 7326 / out 1753 usd_reported=0.002290 usd~0.048 (upper-bound price)

# Code Audit: pp-selectid-20261115_1700 (C1_STEP)

## Scope
Review of `pipeline/package.py` (`join_moments` new function, `build` call-site change) and `tests/package/test_medley.py` (2 new tests).

## Findings

### [P2] `join_moments` does not enforce the "second pass" filter from RULING 117(2)
The RULING 117(2) order defines the eligible pool as: *"the hook and the clips that passed step A from both vendors, **the second pass** and CUTTABLE"*. The new `join_moments` function filters on:
- `x != h` (not the hook)
- `x not in doomed`
- `m["video_id"] != hv` (not the hook's own video)
- `eligibility.clip.ok` (clip-eligible)

It does **not** explicitly check that the moment passed "the second pass" (i.e., survived the second vendor's step A). The docstring claims this is covered by `cleared` ("from `cleared`: step A from both vendors, the second pass, CUTTABLE"), which implies `cleared` is pre-filtered. However, the old inline code also used `cleared` without an explicit second-pass check, so this is not a regression. That said, if `cleared` ever contains moments that failed the second pass (e.g., due to a future refactor or a bug in the clearing step), `join_moments` would silently include them. The function's contract relies entirely on the caller's invariant about `cleared`. This is a latent fragility, not a current bug, but worth a comment or an assertion.

**Recommendation:** Add a brief comment in `join_moments` stating that `cleared` is assumed to contain only moments that passed both vendors' step A and the second pass, or add a debug assertion.

### [P3] `can()` helper accesses `cleared[x]` without a guard, but `x` is always in `cleared`
In `join_moments`, the `can(x)` helper does `m = cleared[x]`. The callers ensure `x` is in `cleared`:
- `own` list comprehension: `x in cleared` is checked.
- The `for x in sorted(...)` loop iterates over `cleared` keys.

So this is safe. No action needed, but a defensive `cleared.get(x)` would make the function more robust if ever called with a different contract. Nit only.

### [P3] Channel-diversity ordering: `chans` set is mutated during iteration
```python
chans = {cleared[x]["channel_id"] for x in [h, *own]}
first, then = [], []
for x in sorted(...):
    (then if cleared[x]["channel_id"] in chans else first).append(x)
    chans.add(cleared[x]["channel_id"])
```
The `chans` set is updated as moments are added. This means a moment's channel is considered "already in the set" if *any earlier moment in the sorted iteration* (whether in `first` or `then`) is from that channel. This is the intended behavior per the spec: *"one moment of each channel not yet in the set first, then the others in rank order."* The test `test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first` confirms this: `e1` (E, rank 90) goes to `first` because E is new; `e2` (E, rank 80) goes to `then` because E is now in `chans`. This is correct and deterministic. No issue.

### [P3] `JOIN_MOMENTS_MAX` is referenced but not defined in the diff
The constant `JOIN_MOMENTS_MAX` is used in `join_moments` and was used in the old inline code. It is presumably defined elsewhere in `package.py` (not in the diff). This is fine; no action needed.

### [P3] Test `test_the_writers_own_picks_join_the_table_only_when_they_can_stand_beside_the_hook` does not test the `doomed` parameter's interaction with `own`
The test checks `doomed={"x"}` where `x` is in `angle["moments"]`. This is good. However, it does not test a doomed moment that is *not* in `angle["moments"]` but is in `cleared`. The `can()` function checks `x not in doomed` for all moments, so this is covered by the general logic. The test is sufficient for the stated purpose.

### [P3] No test for the case where `own` is empty
If `angle["moments"]` contains only the hook (or no other cleared moments), `own` is empty. The function should still work: `chans` = {hook's channel}, and the rest of the pool is ordered by channel diversity. This is implicitly covered by the first test (where `own` = ["x", "y"] is non-empty) and the general logic. A dedicated test would be nice but not required.

### [P3] The `build` call-site change is minimal and correct
The old inline code:
```python
own_ = [x for x in angle["moments"] if x != angle["hook"] and x in cleared and x not in doomed]
rest_ = sorted((x for x in cleared if x not in doomed and x != angle["hook"] and x not in own_),
               key=lambda x: (-cleared[x].get("rank_score", 0), x))
jids = ([angle["hook"]] + own_ + rest_)[:JOIN_MOMENTS_MAX]
```
The new code:
```python
jids = join_moments(angle, cleared, doomed)
```
The new function adds two filters the old code lacked:
1. `m["video_id"] != hv` (not the hook's own video)
2. `eligibility.clip.ok` (clip-eligible)
3. Channel-diversity ordering for the `rest` portion.

These are the intended changes per the RULING. The old code did **not** filter by video or clip-eligibility, which was the bug (the table was filled with moments that could never stand beside the hook). The new code is correct.

### [P3] Determinism
The ordering is deterministic:
- `own` is in `angle["moments"]` order (writer's order).
- `rest` is sorted by `(-rank_score, x)`, which is a total order (ties broken by id).
- The `first`/`then` split is deterministic given the sorted order and the `chans` set evolution.
No randomness. Good.

### [P3] No new imports, no new dependencies
The function uses only existing data structures. No new imports. Good.

### [P3] Law compliance
- **LAW 20 / M2**: No gate thresholds changed. No reclassification. Good.
- **M12 FAIL CLOSED**: The function does not produce a pass on missing data; it returns an empty list if no moments qualify, which is a valid (empty) join table. The caller handles empty tables. Good.
- **LAW 22**: No impact on v2f reference. Good.
- **Smallest diff**: The change is minimal and focused. Good.

## Summary
The change is correct and addresses the stated bug (the join table was filled with moments that could never stand beside the hook due to video/clip-eligibility constraints). The new `join_moments` function properly filters and orders the moments. The tests are adequate. The only notable issue is the reliance on the `cleared` invariant (P2), which is a latent fragility but not a current bug.

P1_OR_WORSE: 0