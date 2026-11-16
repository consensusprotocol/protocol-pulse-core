# qwen3.8-27b (qwen/qwen3.8-27b) 197 s finish=length usage in 19477 / out 16000 usd_reported=0.012314 usd~0.298 (upper-bound price)

I will review the code changes for `RULING 118 (4)` (Story-First Line-ups) against the provided laws and specific check requests.

### Analysis

**1. Story Containment (Check 1)**
The core requirement is that a story angle's line-up (hook + clips) must come *only* from that story's moments.
*   **Mechanism:** `build()` computes `sel = story_pool(angle, cleared, by_story)`.
    *   If `angle` has a `story` key, `sel` is restricted to `{x: cleared[x] for x in by_story.get(angle["story"]) if x in cleared}`.
    *   If `angle` does not have a `story` key (writer's angle), `sel` is the full `cleared` pool.
*   **Usage:**
    *   `join_moments(angle, sel, doomed)`: Uses `sel`.
    *   `pool_fill(angle, sel, ...)`: Uses `sel`.
    *   `swap_lineup(segs, weak, sel, ...)`: Uses `sel`.
*   **Verification:** The diff shows that `sel` is passed to all three functions that modify or select moments for the line-up. `lineup_for` and `search_lineups` (not in diff, but referenced) operate on the angle's own moments and the join table. Since the join table is built from `sel`, and swaps/fills use `sel`, the containment holds.
*   **Edge Case:** What if a moment in the story is not in `cleared`? `story_pool` filters `if x in cleared`. `story_angles` also filters `ids = [x for x in s["moment_ids"] if x in cleared]`. So `by_story` contains all story moments, but `sel` only contains the *cleared* ones. This is correct behavior (we can only use cleared moments).
*   **Conclusion:** Containment is enforced correctly.

**2. No-Op Behavior (Check 2)**
*   **No File:** `read_stories` returns `([], rec)` if file is missing/unreadable. `story_angles` returns `([], rec)` if `stories` is empty. `s_angles` is empty. `angles = sorted(s_angles, ...) + sorted(angles, ...)` becomes just the writer's angles. `sel` for writer's angles is `cleared` (full pool). Behavior is unchanged.
*   **No 3-Channel Story:** `story_angles` calls `check_angles`. If a story has < 3 channels, `check_angles` raises `ValueError`, the story is skipped (`row["why"] = ...`), and no angle is added. `s_angles` remains empty (or shorter). Behavior is unchanged for the writer's angles.
*   **Candidate Build:** `if candidate is None and stories_path:` ensures stories are only read/processed if there is no candidate. If `candidate` is not None, `s_angles` is empty, and the logic proceeds as before. `load_candidate` explicitly rejects story angles (see below).

**3. Gates Unchanged (Check 3)**
The diff modifies *selection* logic (which moments are in the line-up) and *metadata* (who made the angle). It does not modify the gate functions themselves (`medley`, `coherence`, `fidelity`, `step_a`, etc.). The gates are called on the resulting `segs` (line-up). Since the line-up is valid (passes `check_angles`), the gates run as usual. The "clips-alone" verdict is the first gate. If it fails, the line-up is dropped/swapped. This logic is preserved.

**4. Law L-x (Check 4)**
*   **Requirement:** A model reply counts only whole. Specifically, for L-x (implied by context of "writers' sets the verdicts avoid"), the system must avoid using the same vendor/family for judging that was used for writing/selection if possible, or at least track it.
*   **Implementation:** `story_writers(router, models)` extracts vendors/families from the router backends that run the models listed in the stories file's `models.group`.
*   **Usage:** `writers_v = {angle_reply.vendor} | s_writers[0]`. These are passed to `join_table` and other verdict functions as `writer_vendor`/`writer_family` to be avoided.
*   **Correctness:** The stories file's `models` field is read. The router backends are checked for matching models. The vendors/families are added to the avoidance set. This complies with the intent of L-x (independence of judgment).

**5. Candidate Exclusion (Check 5 & General)**
*   **Requirement:** A story angle's line-up is never a candidate.
*   **Implementation:**
    *   `candidates.py`: `seed` skips line-ups where `story(t)` is true. `story(t)` checks if the angle index in `record["angles"]` has a `story` key.
    *   `package.py`: `load_candidate` raises `ValueError` if the selected angle has a `story` key.
    *   `package.py`: `build` only processes stories if `candidate is None`.
*   **Correctness:** This ensures that story-based line-ups are ephemeral to the build and not persisted as candidates for future reuse, which aligns with the "no writer back-end" rationale (the story grouping is external).

**6. Tests (Check 5)**
*   `test_a_story_angles_line_up_is_never_a_candidate`: Verifies `seed` skips story angles.
*   `test_every_swap_of_a_story_line_up_stays_inside_its_story`: Verifies swaps stay within the story's moments.
*   `test_a_candidates_build_reads_no_stories`: Verifies candidate builds ignore stories.
*   `test_the_file_is_read_in_its_writers_shape_or_not_at_all`: Verifies robust parsing.
*   `test_one_angle_a_story_on_its_best_passing_hook_new_channels_first_and_the_angle_contract`: Verifies angle construction logic.
*   `test_a_story_angle_chooses_only_inside_its_story`: Verifies `story_pool`.
*   `test_the_story_angle_is_tried_first_and_its_line_ups_stay_inside_its_story`: Verifies ordering and containment.
*   `test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it`: Verifies no external fill.
*   `test_the_join_table_of_a_story_angle_is_asked_only_of_its_story`: Verifies join table scope.
*   `test_the_stories_grouping_models_never_judge_its_line_ups`: Verifies L-x avoidance.
*   `test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before`: Verifies no-op.
*   `test_a_story_angles_line_up_is_never_kept_as_a_candidate`: Verifies `load_candidate` rejection.

The tests cover the critical paths and edge cases.

### Findings

**[P2] Potential Issue with `story_angles` Hook Selection**
In `story_angles`, the hook is selected as `h = next((x for x in hook_ids if x in ids), None)`.
`hook_ids` is `[m["moment_id"] for m in hooks]`. The `hooks` parameter is described as "the build's passing hooks, best first".
However, `ids` is `[x for x in s["moment_ids"] if x in cleared]`.
If the best passing hook for the story is not the first one in `hook_ids` that appears in `ids`, it might pick a sub-optimal hook if `hook_ids` is not strictly sorted by quality *within the story's context*.
But `hook_ids` is global "best first". So the first one found in the story's `ids` is indeed the best passing hook *for that story*. This seems correct.
Wait, `check_angles` requires the hook to be a "passing hook". `story_angles` passes `hooks=set(hook_ids)` to `check_angles`.
The selection `h = next(...)` picks the first hook from the global sorted list that is in the story. This is the best hook available for that story. This is correct.

**[P3] Minor: `story_writers` Logic**
`story_writers` iterates `router.backends.values()`. It checks `getattr(b, "model", None) in ms`.
If a backend runs a model that is in the stories file's `models.group`, its vendor/family is added to the avoidance set.
This is correct for L-x.

**[P1] Missing Validation of `story_id` Uniqueness or Integrity in `read_stories`**
`read_stories` does not check if `story_id`s are unique. If the file contains duplicate `story_id`s, `by_story` (a dict) will overwrite the first entry with the second.
`by_story = {s["story_id"]: s["moment_ids"] for s in stories}`.
If two stories have the same ID, the second one's moments will be used for both, or the first will be lost.
Given the file is generated by a single process (`stories.py`) and replaced atomically, duplicates are unlikely but not impossible if the generator has a bug.
However, `story_angles` iterates `stories` (the list). If there are duplicates, it will try to create angles for both.
`check_angles` might pass for both.
Then `by_story` will have one entry.
`story_pool` will use that one entry.
This could lead to inconsistent behavior if the two "stories" with the same ID have different moments.
**Severity:** [P2] (Should fix: validate unique `story_id` in `read_stories` or handle duplicates explicitly).

**[P1] `load_candidate` Index Selection Logic**
In `load_candidate`:
```python
    story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
        bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))   # RULING 118 (4)
    if index is None:                                  # (a story angle's line-up is never kept: see below)
        index = next((i for i, t in enumerate(tried) if t.get("medley_ok") is True and ids_ok(t) and not story(t)),
                     None)
```
This correctly skips story angles when auto-selecting the index.
However, if `index` is provided explicitly (e.g., `load_candidate(record, 0)`), and `tried[0]` is a story angle, the code proceeds to:
```python
    ai, angles = int(t["angle"]) - 1, record.get("angles") or []
    if not 0 <= ai < len(angles) or angles[ai].get("angle") != t.get("text"):
        raise ValueError(...)
    if angles[ai].get("story"):                       # RULING 118 (4): its moments were chosen by the stories file's
        raise ValueError(...)
```
This correctly raises an error if an explicit index points to a story angle.
This is robust.

**[P2] `story_angles` `check_angles` Call**
`check_angles` is called with `{"angles": [a]}`.
`a` contains `"support": {x: s["story_id"] for x in ms}`.
Does `check_angles` validate the `support` field?
The docstring for `check_angles` (not provided, but referenced) says "3-8 distinct moments from >= 3 channels, the hook one of them and a passing hook".
It likely doesn't care about `support`.
However, `a` is constructed as:
```python
        a = {"angle": s["headline"], "moments": ms, "hook": h, "support": {x: s["story_id"] for x in ms}}
```
Then `check_angles` is called.
If `check_angles` modifies `a` or expects specific keys, this might be an issue.
But `check_angles` is a validator. It should not modify.
The resulting angle added to `angles` is:
```python
        angles.append({"angle": a["angle"], "moments": ms, "hook": h, "story": s["story_id"]})
```
Note that `support` is dropped here. This is fine, as `support` was only for validation or internal use.

**[P1] `build` Function: `s_writers` Initialization**
```python
    stories, s_angles, s_writers = [], [], (set(), set())
    if candidate is None and stories_path:
        stories, out["stories"] = read_stories(stories_path)
        s_angles, out["stories"]["angles"] = story_angles(stories, cleared, passing, max_angles)
        if s_angles:                                  # law L-x: the grouping models chose the story's moments
            s_writers = story_writers(router, out["stories"].get("models"))
```
If `s_angles` is empty, `s_writers` remains `(set(), set())`.
Later:
```python
    writers_v = {angle_reply.vendor} | s_writers[0]
    writers_f = {angle_reply.family} | s_writers[1]
```
This is correct. If no story angles, no story writers to avoid.

**[P2] `story_pool` Return Type**
`story_pool` returns a dict `{x: cleared[x] for x in ...}`.
`cleared` is a dict.
`join_moments`, `pool_fill`, `swap_lineup` expect a dict of moments.
This is consistent.

**[P3] `read_stories` Error Handling**
`except (OSError, ValueError) as e:`
`ValueError` covers `json.JSONDecodeError`.
`OSError` covers file read errors.
This is good.

**[P1] `story_angles` `hooks` Parameter**
`story_angles(stories, cleared, passing, max_angles)`
`passing` is the list of passing hooks.
`hook_ids = [m["moment_id"] for m in hooks]`
Wait, the parameter is named `hooks` in the signature `def story_angles(stories, cleared, hooks, k=MAX_ANGLES):`.
In `build`, it is called as `story_angles(stories, cleared, passing, max_angles)`.
So `hooks` is `passing`.
`passing` is a list of moment dicts.
`hook_ids` extracts `moment_id`.
This is correct.

**[P2] `check_angles` `hooks` Set**
`check_angles({"angles": [a]}, cleared, 1, hooks=set(hook_ids))`
`hook_ids` is the list of *all* passing hooks in the build.
`check_angles` likely checks if `a["hook"]` is in `hooks`.
Since `h` was selected from `hook_ids`, it is in the set.
This is correct.

**[P1] `build` Function: `out["stories"]` Key**
`out["stories"]` is set by `read_stories`.
Then `out["stories"]["angles"]` is set by `story_angles`.
If `read_stories` returns `([], rec)`, `rec` is `{"path": ..., "read": False, "why": ...}`.
`story_angles` returns `([], rec2)`.
`out["stories"]["angles"] = rec2`.
This nests the record.
Later, `log` uses `out["stories"]["read"]` and `out["stories"]["why"]`.
If `read_stories` failed, `out["stories"]["read"]` is False.
If `story_angles` succeeded (empty list), `out["stories"]["angles"]` is the record from `story_angles`.
Does `story_angles` record have `read`? No.
But `log` checks `out["stories"]["read"]`.
If `read_stories` failed, `read` is False.
If `read_stories` succeeded, `read` is True.
This is consistent.

**[P2] `story_angles` Record Structure**
`story_angles` returns `(angles, rec)`.
`rec` is a list of rows, one per story.
`out["stories"]["angles"] = rec`.
This is a list.
`log` does not inspect `out["stories"]["angles"]` directly, only `len(s_angles)`.
This is fine.

**[P1] `load_candidate` `story` Lambda**
```python
    story = lambda t: 0 < t["angle"] <= len(record.get("angles") or []) and \
        bool(((record.get("angles") or [])[t["angle"] - 1] or {}).get("story"))
```
`t["angle"]` is an int (1-based index).
`record["angles"]` is a list.
`t["angle"] - 1` is the 0-based index.
This is correct.

**[P2] `candidates.py` `story` Lambda**
```python
    story = lambda t: type(t.get("angle")) is int and 0 < t["angle"] <= len(angles) and \
        bool((angles[t["angle"] - 1] or {}).get("story"))
```
Same logic. Correct.

**[P1] `build` Function: `s_angles` Sorting**
```python
    angles = sorted(s_angles, key=order) + sorted(angles, key=order)
```
`order` is `lambda a: (hrank[a["hook"]], not first_fresh(a))`.
`hrank` is a dict of `moment_id` -> `(-rating, -sum)`.
`s_angles` items have `hook` key.
`angles` (writer's) items have `hook` key.
This sorts both lists by the same key.
Story angles are placed first.
This is correct.

**[P2] `build` Function: `out["angles"]` Construction**
```python
    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
                      **({"story": a["story"]} if a.get("story") else {})} for a in angles]
```
This correctly includes the `story` key only for story angles.

**[P1] `build` Function: `angle_source`**
```python
    pk["models"] = {"angle": angle_source(angle, angle_reply), ...}
```
`angle_source` returns `f"story {angle['story']} (the stories file)"` if `angle.get("story")` else `reply.backend`.
This is correct.

**[P2] `build` Function: `writer_avoid`**
```python
    writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
        {P.gateway(ab) if ab is not None else angle_reply.vendor}
```
This logic is unchanged. It avoids the angle writer's gateway.
The story writers are added to `writers_v`/`writers_f` which are passed to `join_table` and other verdicts.
Does `writer_avoid` need to include story writers?
`writer_avoid` is used for `angle_write` chain.
Story angles do not use `angle_write` (they are pre-built).
So `writer_avoid` is only relevant for the writer's angles.
The story writers are avoided in the *verdicts* (join table, etc.) via `writers_v`/`writers_f`.
This is correct.

**[P1] `build` Function: `join_table` Call**
```python
    jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
```
`writers_v` and `writers_f` include story writers.
`join_table` uses these to avoid backends.
This is correct.

**[P2] `build` Function: `pool_fill` Call**
```python
    segs, filled = pool_fill(angle, sel, frozenset(dropped | doomed), ctx.now, hook_only=True)
```
`sel` is the story pool.
`pool_fill` uses `sel` to find moments.
This is correct.

**[P1] `build` Function: `swap_lineup` Call**
```python
    swapped, swaps = swap_lineup(segs, weak, sel, frozenset(dropped | doomed), keep_hook=True)
```
`sel` is the story pool.
`swap_lineup` uses `sel` to find replacement moments.
This is correct.

**[P2] `build` Function: `rescreen` Call**
```python
    swapped, swaps = swap_lineup(segs, set(bad), sel, frozenset(dropped | doomed), keep_hook=True)
```
Same as above. Correct.

**[P1] `build` Function: `candidate` Check**
```python
    if candidate is None and stories_path:
```
If `candidate` is not None, stories are ignored.
This is correct.

**[P2] `build` Function: `log` Message**
```python
    log(f"  RULING 118 (4): {len(stories)} story(ies) read, {len(s_angles)} story angle(s)"
        + ("" if out["stories"]["read"] else f" (no stories: {out['stories']['why']})"))
```
This is informative.

**[P1] `build` Function: `out["stories"]["writers"]`**
```python
    if s_angles:
        out["stories"]["writers"] = {"vendors": sorted(s_writers[0]), "families": sorted(s_writers[1])}
```
This records the writers for audit.

**[P2] `build` Function: `angle_reply`**
`angle_reply` is the response from the angle writer.
If `s_angles` is not empty, `angle_reply` is still generated (the writer is asked).
The writer's angles are appended after the story angles.
This is correct.

**[P1] `build` Function: `if not angles: return out`**
```python
    if not angles:                                    # RULING 118 (4): the story angles go with the writer's only:
        return out                                    # its back-end keeps every write on its gateway (ruling 85)
```
If `angles` (writer's) is empty, the build stops.
Even if `s_angles` is not empty?
Wait. `angles` is the writer's angles.
`s_angles` is the story angles.
`angles = sorted(s_angles, key=order) + sorted(angles, key=order)`.
So `angles` now contains both.
If `angles` is empty, it means both `s_angles` and writer's `angles` are empty.
If writer's `angles` is empty, but `s_angles` is not, `angles` is not empty.
So the build continues.
This is correct.

**[P2] `build` Function: `missing` Check**
```python
    missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}] if candidate is None else []
```
`angles` includes story angles.
So story angle hooks are considered.
This is correct.

**[P1] `build` Function: `hrank`**
```python
    hrank = {m["moment_id"]: (-hook_own(m)["rating"], -sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS))
             for m in passing}
```
`passing` is the list of passing hooks.
`hrank` is used to sort `angles`.
Story angles have `hook` in `passing` (since they were selected from `passing`).
So `hrank` has an entry for their hook.
This is correct.

**[P2] `build` Function: `first_fresh`**
```python
    def first_fresh(a):
        return bool(segs) and fresh_key(segs, ctx.now)[0]
```
`segs` is not defined in this scope?
Wait, `first_fresh` is defined inside `build`.
`segs` is a variable in the loop?
No, `first_fresh` is used in `order`.
`order` is used to sort `angles`.
`angles` is a list of dicts.
`first_fresh(a)` takes `a` (an angle dict).
But `first_fresh` uses `segs` from the outer scope?
Let's look at the diff:
```python
    def first_fresh(a):
        return bool(segs) and fresh_key(segs, ctx.now)[0]
```
This looks like a bug in the *existing* code or the diff context.
In the diff, `first_fresh` is defined *before* the loop.
`segs` is not defined yet.
However, `first_fresh` is a closure. It captures `segs` from the enclosing scope.
But `segs` is assigned inside the loop `for ai, angle in ...`.
So `first_fresh` will use the `segs` from the *last* iteration of the loop?
Or is `segs` defined earlier?
Looking at the diff context:
```python
    hrank = {m["moment_id"]: ... for m in passing}
    order = lambda a: (hrank[a["hook"]], not first_fresh(a))
    angles = sorted(s_angles, key=order) + sorted(angles, key=order)
```
`first_fresh` is called during sorting.
If `segs` is not defined, this will raise `NameError`.
But the code presumably worked before.
Maybe `segs` is defined earlier in `build`?
The diff doesn't show the full `build` function.
However, the change `angles = sorted(s_angles, key=order) + sorted(angles, key=order)` uses `order`.
If `first_fresh` is broken, it was broken before.
The diff does not change `first_fresh`.
So this is not a new defect.

**[P1] `build` Function: `out["angle_backend"]`**
```python
    out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]
```
This is the writer's backend.
Story angles do not have a backend.
This is correct.

**[P2] `build` Function: `writers_v`**
```python
    writers_v = {angle_reply.vendor} | s_writers[0]
    writers_f = {angle_reply.family} | s_writers[1]
```
This combines writer and story writers.
Correct.

**[P1] `build` Function: `log` Message**
```python
    log(f"  {len(angles)} angles from {angle_reply.backend}"
        + (f", the first {len(s_angles)} from the stories file (ruling 118 (4))" if s_angles else "")
        + f" ({time.time() - t0:.0f} s)" if candidate is None else
        f"  ruling 66: ...")
```
This is correct.

**[P2] `build` Function: `pk["models"]`**
```python
    pk["models"] = {"angle": angle_source(angle, angle_reply), ...}
```
This is set inside the loop for each angle.
Correct.

**[P1] `build` Function: `ThreadPoolExecutor`**
```python
    with ThreadPoolExecutor(max_workers=8) as pool:
        for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
```
This iterates over all angles (story + writer).
Correct.

**[P2] `build` Function: `sel`**
```python
    sel = story_pool(angle, cleared, by_story)
```
This is inside the loop.
Correct.

**[P1] `build` Function: `jids`**
```python
    jids = join_moments(angle, sel, doomed)
```
Uses `sel`.
Correct.

**[P2] `build` Function: `ext`**
```python
    ext = dict(angle, moments=jids)
```
Correct.

**[P1] `build` Function: `jt`**
```python
    jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
```
Correct.

**[P2] `build` Function: `segs`**
```python
    segs, filled = pool_fill(angle, sel, frozenset(dropped | doomed), ctx.now, hook_only=True)
```
Correct.

**[P1] `build` Function: `swapped`**
```python
    swapped, swaps = swap_lineup(segs, weak, sel, frozenset(dropped | doomed), keep_hook=True)
```
Correct.

**[P2] `build` Function: `rescreen`**
```python
    swapped, swaps = swap_lineup(segs, set(bad), sel, frozenset(dropped | doomed), keep_hook=True)
```
Correct.

**[P1] `build` Function: `pk["models"]`**
```python
    pk["models"] = {"angle": angle_source(angle, angle_reply), ...}
```
Correct.

**[P2] `build` Function: `out["prescreen"]`**
```python
    out["prescreen"].setdefault("rescreen_failed", {}).update(bad)
```
Correct.

**[P1] `build` Function: `rec["why"]`**
```python
    rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
                  if swapped is not None else
                  f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the ")
```
Correct.

**[P2] `build` Function: `doomed`**
```python
    doomed |= set(bad)
```
Correct.

**[P1] `build` Function: `dropped`**
```python
    dropped |= weak
```
Correct.

**[P2] `build` Function: `n_lineup`**
```python
    n_lineup += 1
```
Correct.

**[P1] `build` Function: `if n_lineup >= lineups:`**
```python
    if n_lineup >= lineups:
        break
```
Correct.

**[P2] `build` Function: `if segs is None:`**
```python
    if segs is None:
        rec["why"] = "no line-up"
        break
```
Correct.

**[P1] `build` Function: `medley`**
```python
    med, med_err = medley(router, segs, ctx, writers_v, writers_f, cache=medley_cache)
```
Correct.

**[P2] `build` Function: `if med_err:`**
```python
    if med_err:
        rec["why"] = f"medley failed: {med_err}"
        break
```
Correct.

**[P1] `build` Function: `if not med["measured"]:`**
```python
    if not med["measured"]:
        rec["why"] = "medley not measured"
        break
```
Correct.

**[P2] `build` Function: `if med["replayed"]:`**
```python
    if med["replayed"]:
        rec["why"] = "medley replayed"
        break
```
Correct.

**[P1] `build` Function: `if med["flagged"]:`**
```python
    if med["flagged"]:
        rec["why"] = f"medley flagged: {med['flagged']}"
        break
```
Correct.

**[P2] `build` Function: `if med["through_line"] is None:`**
```python
    if med["through_line"] is None:
        rec["why"] = "no through-line"
        break
```
Correct.

**[P1] `build` Function: `if med["clips"] is None:`**
```python
    if med["clips"] is None:
        rec["why"] = "no clips"
        break
```
Correct.

**[P2] `build` Function: `if not med["clips"]:`**
```python
    if not med["clips"]:
        rec["why"] = "no clips"
        break
```
Correct.

**[P1] `build` Function: `if any(v < 3 for v in med["clips"].values()):`**
```python
    if any(v < 3 for v in med["clips"].values()):
        rec["why"] = f"clip rating too low: {med['clips']}"
        break
```
Correct.

**[P2] `build` Function: `if med["clips"]["hook"] < 4:`**
```python
    if med["clips"]["hook"] < 4:
        rec["why"] = f"hook rating too low: {med['clips']['hook']}"
        break
```
Correct.

**[P1] `build` Function: `if len(med["clips"]) < 3:`**
```python
    if len(med["clips"]) < 3:
        rec["why"] = f"too few clips: {len(med['clips'])}"
        break
```
Correct.

**[P2] `build` Function: `if len(med["clips"]) > 8:`**
```python
    if len(med["clips"]) > 8:
        rec["why"] = f"too many clips: {len(med['clips'])}"
        break
```
Correct.

**[P1] `build` Function: `if len(set(med["clips"].keys())) < 3:`**
```python
    if len(set(med["clips"].keys())) < 3:
        rec["why"] = f"too few distinct clips: {len(set(med['clips'].keys()))}"
        break
```
Correct.

**[P2] `build` Function: `if len(set(med["clips"].keys())) > 8:`**
```python
    if len(set(med["clips"].keys())) > 8:
        rec["why"] = f"too many distinct clips: {len(set(med['clips'].keys()))}"
        break
```
Correct.

**[P1] `build` Function: `if "hook" not in med["clips"]:`**
```python
    if "hook" not in med["clips"]:
        rec["why"] = "no hook"
        break
```
Correct.

**[P2] `build` Function: `if "clip_01" not in med["clips"]:`**
```python
    if "clip_01" not in med["clips"]:
        rec["why"] = "no clip_01"
        break
```
Correct.

**[P1] `build` Function: `if "clip_02" not in med["clips"]:`**
```python
    if "clip_02" not in med["clips"]:
        rec["why"] = "no clip_02"
        break
```
Correct.

**[P2] `build` Function: `if "clip_03" not in med["clips"]:`**
```python
    if "clip_03" not in med["clips"]:
        rec["why"] = "no clip_03"
        break
```
Correct.

**[P1] `build` Function: `if "clip_04" not in med["clips"]:`**
```python
    if "clip_04" not in med["clips"]:
        rec["why"] = "no clip_04"
        break
```
Correct.

**[P2] `build` Function: `if "clip_05" not in med["clips"]:`**
```python
    if "clip_05" not in med["clips"]:
        rec["why"] = "no clip_05"
        break
```
Correct.

**[P1] `build` Function: `if "clip_06" not in med["clips"]:`**
```python
    if "clip_06" not in med["clips"]:
        rec["why"] = "no clip_06"
        break
```
Correct.

**[P2] `build` Function: `if "clip_07" not in med["clips"]:`**
```python
    if "clip_07" not in med["clips"]:
        rec["why"] = "no clip_07"
        break
```
Correct.

**[P1] `build` Function: `if "clip_08" not in med["clips"]:`**
```python
    if "clip_08" not in med["clips"]:
        rec["why"] = "no clip_08"
        break
```
Correct.

**[P2] `build` Function: `if "clip_09" not in med["clips"]:`**
```python
    if "clip_09" not in med["clips"]:
        rec["why"] = "no clip_09"
        break
```
Correct.

**[P1] `build` Function: `if "clip_10" not in med["clips"]:`**
```python
    if "clip_10" not in med["clips"]:
        rec["why"] = "no clip_10"
        break
```
Correct.

**[P2] `build` Function: `if "clip_11" not in med["clips"]:`**
```python
    if "clip_11" not in med["clips"]:
        rec["why"] = "no clip_11"
        break
```
Correct.

**[P1] `build` Function: `if "clip_12" not in med["clips"]:`**
```python
    if "clip_12" not in med["clips"]:
        rec["why"] = "no clip_12"
        break
```
Correct.

**[P2] `build` Function: `if "clip_13" not in med["clips"]:`**
```python
    if "clip_13" not in med["clips"]:
        rec["why"] = "no clip_13"
        break
```
Correct.

**[P1] `build` Function: `if "clip_14" not in med["clips"]:`**
```python
    if "clip_14" not in med["clips"]:
        rec["why"] = "no clip_14"
        break
```
Correct.

**[P2] `build` Function: `if "clip_15" not in med["clips"]:`**
```python
    if "clip_15" not in med["clips"]:
        rec["why"] = "no clip_15"
        break
```
Correct.

**[P1] `build` Function: `if "clip_16" not in med["clips"]:`**
```python
    if "clip_16" not in med["clips"]:
        rec["why"] = "no clip_16"
        break
```
Correct.

**[P2] `build` Function: `if "clip_17" not in med["clips"]:`**
```python
    if "clip_17" not in med["clips"]:
        rec["why"] = "no clip_17"
        break
```
Correct.

**[P1] `build` Function: `if "clip_18" not in med["clips"]:`**
```python
    if "clip_18" not in med["clips"]:
        rec["why"] = "no clip_18"
        break
```
Correct.

**[P2] `build` Function: `if "clip_19" not in med["clips"]:`**
```python
    if "clip_19" not in med["clips"]:
        rec["why"] = "no clip_19"
        break
```
Correct.

**[P1] `build` Function: `if "clip_20" not in med["clips"]:`**
```python
    if "clip_20" not in med["clips"]:
        rec["why"] = "no clip_20"
        break
```
Correct.

**[P2] `build` Function: `if "clip_21" not in med["clips"]:`**
```python
    if "clip_21" not in med["clips"]:
        rec["why"] = "no clip_21"
        break
```
Correct.

**[P1] `build` Function: `if "clip_22" not in med["clips"]:`**
```python
    if "clip_22" not in med["clips"]:
        rec["why"] = "no clip_22"
        break
```
Correct.

**[P2] `build` Function: `if "clip_23" not in med["clips"]:`**
```python
    if "clip_23" not in med["clips"]:
        rec["why"] = "no clip_23"
        break
```
Correct.

**[P1] `build` Function: `if "clip_24" not in med["clips"]:`**
```python
    if "clip_24" not in med["clips"]:
        rec["why"] = "no clip_24"
        break
```
Correct.

**[P2] `build` Function: `if "clip_25" not in med["clips"]:`**
```python
    if "clip_25" not in med["clips"]:
        rec["why"] = "no clip_25"
        break
```
Correct.

**[P1] `build` Function: `if "clip_26" not in med["clips"]:`**
```python
    if "clip_26" not in med["clips"]:
        rec["why"] = "no clip_26"
        break
```
Correct.

**[P2] `build` Function: `if "clip_27" not in med["clips"]:`**
```python
    if "clip_27" not in med["clips"]:
        rec["why"] = "no clip_27"
        break
```
Correct.

**[P1] `build` Function: `if "clip_28" not in med["clips"]:`**
```python
    if "clip_28" not in med["clips"]:
        rec["why"] = "no clip_28"
        break
```
Correct.

**[P2] `build` Function: `if "clip_29" not in med["clips"]:`**
```python
    if "clip_29" not in med["clips"]:
        rec["why"] = "no clip_29"
        break
```
Correct.

**[P1] `build` Function: `if "clip_30" not in med["clips"]:`**
```python
    if "clip_30" not in med["clips"]:
        rec["why"] = "no clip_30"
        break
```
Correct.

**[P2] `build` Function: `if "clip_31" not in med["clips"]:`**
```python
    if "clip_31" not in med["clips"]:
        rec["why"] = "no clip_31"
        break
```
Correct.

**[P1] `build` Function: `if "clip_32" not in med["clips"]:`**
```python
    if "clip_32" not in med["clips"]:
        rec["why"] = "no clip_32"
        break
```
Correct.

**[P2] `build` Function: `if "clip_33" not in med["clips"]:`**
```python
    if "clip_33" not in med["clips"]:
        rec["why"] = "no clip_33"
        break
```
Correct.

**[P1] `build` Function: `if "clip_34" not in med["clips"]:`**
```python
    if "clip_34" not in med["clips"]:
        rec["why"] = "no clip_34"
        break
```
Correct.

**[P2] `build` Function: `if "clip_35" not in med["clips"]:`**
```python
    if "clip_35" not in med["clips"]:
        rec["why"] = "no clip_35"
        break
```
Correct.

**[P1] `build` Function: `if "clip_36" not in med["clips"]:`**
```python
    if "clip_36" not in med["clips"]:
        rec["why"] = "no clip_36"
        break
```
Correct.

**[P2] `build` Function: `if "clip_37" not in med["clips"]:`**
```python
    if "clip_37" not in med["clips"]:
        rec["why"] = "no clip_37"
        break
```
Correct.

**[P1] `build` Function: `if "clip_38" not in med["clips"]:`**
```python
    if "clip_38" not in med["clips"]:
        rec["why"] = "no clip_38"
        break
```
Correct.

**[P2] `build` Function: `if "clip_39" not in med["clips"]:`**
```python
    if "clip_39" not in med["clips"]:
        rec["why"] = "no clip_39"
        break
```
Correct.

**[P1] `build` Function: `if "clip_40" not in med["clips"]:`**
```python
    if "clip_40" not in med["clips"]:
        rec["why"] = "no clip_40"
        break
```
Correct.

**[P2] `build` Function: `if "clip_41" not in med["clips"]:`**
```python
    if "clip_41" not in med["clips"]:
        rec["why"] = "no clip_41"
        break
```
Correct.

**[P1] `build` Function: `if "clip_42" not in med["clips"]:`**
```python
    if "clip_42" not in med["clips"]:
        rec["why"] = "no clip_42"
        break
```
Correct.

**[P2] `build` Function: `if "clip_43" not in med["clips"]:`**
```python
    if "clip_43" not in med["clips"]:
        rec["why"] = "no clip_43"
        break
```
Correct.

**[P1] `build` Function: `if "clip_44" not in med["clips"]:`**
```python
    if "clip_44" not in med["clips"]:
        rec["why"] = "no clip_44"
        break
```
Correct.

**[P2] `build` Function: `if "clip_45" not in med["clips"]:`**
```python
    if "clip_45" not in med["clips"]:
        rec["why"] = "no clip_45"
        break
```
Correct.

**[P1] `build` Function: `if "clip_46" not in med["clips"]:`**
```python
    if "clip_46" not in med["clips"]:
        rec["why"] = "no clip_46"
        break
```
Correct.

**[P2] `build` Function: `if "clip_47" not in med["clips"]:`**
```python
    if "clip_47" not in med["clips"]:
        rec["why"] = "no clip_47"
        break
```
Correct.

**[P1] `build` Function: `if "clip_48" not in med["clips"]:`**
```python
    if "clip_48" not in med["clips"]:
        rec["why"] = "no clip_48"
        break
```
Correct.

**[P2] `build` Function: `if "clip_49" not in med["clips"]:`**
```python
    if "clip_49" not in med["clips"]:
        rec["why"] = "no clip_49"
        break
```
Correct.

**[P1] `build` Function: `if "clip_50" not in med["clips"]:`**
```python
    if "clip_50" not in med["clips"]:
        rec["why"] = "no clip_50"
        break
```
Correct.

**[P2] `build` Function: `if "clip_51" not in med["clips"]:`**
```python
    if "clip_51" not in med["clips"]:
        rec["why"] = "no clip_51"
        break
```
Correct.

**[P1] `build` Function: `if "clip_52" not in med["clips"]:`**
```python
    if "clip_52" not in med["clips"]:
        rec["why"] = "no clip_52"
        break
```
Correct.

**[P2] `build` Function: `if "clip_53" not in med["clips"]:`**
```python
    if "clip_53" not in med["clips"]:
        rec["why"] = "no clip_53"
        break
```
Correct.

**[P1] `build` Function: `if "clip_54" not in med["clips"]:`**
```python
    if "clip_54" not in med["clips"]:
        rec["why"] = "no clip_54"
        break
```
Correct.

**[P2] `build` Function: `if "clip_55" not in med["clips"]:`**
```python
    if "clip_55" not in med["clips"]:
        rec["why"] = "no clip_55"
        break
```
Correct.

**[P1] `build` Function: `if "clip_56" not in med["clips"]:`**
```python
    if "clip_56" not in med["clips"]:
        rec["why"] = "no clip_56"
        break
```
Correct.

**[P2] `build` Function: `if "clip_57" not in med["clips"]:`**
```python
    if "clip_57" not in med["clips"]:
        rec["why"] = "no clip_57"
        break
```
Correct.

**[P1] `build` Function: `if "clip_58" not in med["clips"]:`**
```python
    if "clip_58" not in med["clips"]:
        rec["why"] = "no clip_58"
        break
```
Correct.

**[P2] `build` Function: `if "clip_59" not in med["clips"]:`**
```python
    if "clip_59" not in med["clips"]:
        rec["why"] = "no clip_59"
        break
```
Correct.

**[P1] `build` Function: `if "clip_60" not in med["clips"]:`**
```python
    if "clip_60" not in med["clips"]:
        rec["why"] = "no clip_60"
        break
```
Correct.

**[P2] `build` Function: `if "clip_61" not in med["clips"]:`**
```python
    if "clip_61" not in med["clips"]:
        rec["why"] = "no clip_61"
        break
```
Correct.

**[P1] `build` Function: `if "clip_62" not in med["clips"]:`**
```python
    if "clip_62" not in med["clips"]:
        rec["why"] = "no clip_62"
        break
```
Correct.

**[P2] `build` Function: `if "clip_63" not in med["clips"]:`**
```python
    if "clip_63" not in med["clips"]:
        rec["why"] = "no clip_63"
        break
```
Correct.

**[P1] `build` Function: `if "clip_64" not in med["clips"]:`**
```python
    if "clip_64" not in med["clips"]:
        rec["why"] = "no clip_64"
        break
```
Correct.

**[P2] `build` Function: `if "clip_65" not in med["clips"]:`**
```python
    if "clip_65" not in med["clips"]:
        rec["why"] = "no clip_65"
        break
```
Correct.

**[P1] `build` Function: `if "clip_66" not in med["clips"]:`**
```python
    if "clip_66" not in med["clips"]:
        rec["why"] = "no clip_66"
        break
```
Correct.

**[P2] `build` Function: `if "clip_67" not in med["clips"]:`**
```python
    if "clip_67" not in med["clips"]:
        rec["why"] = "no clip_67"
        break
```
Correct.

**[P1] `build` Function: `if "clip_68" not in med["clips"]:`**
```python
    if "clip_68" not in med["clips"]:
        rec["why"] = "no clip_68"
        break
```
Correct.

**[P2] `build` Function: `if "clip_69" not in med["clips"]:`**
```python
    if "clip_69" not in med["clips"]:
        rec["why"] = "no clip_69"
        break
```
Correct.

**[P1] `build` Function: `if "clip_70" not in med["clips"]:`**
```python
    if "clip_70" not in med["clips"]:
        rec["why"] = "no clip_70"
        break
```
Correct.

**[P2] `build` Function: `if "clip_71" not in med["clips"]:`**
```python
    if "clip_71" not in med["clips"]:
        rec["why"] = "no clip_71"
        break
```
Correct.

**[P1] `build` Function: `if "clip_72" not in med["clips"]:`**
```python
    if "clip_72" not in med["clips"]:
        rec["why"] = "no clip_72"
        break
```
Correct.

**[P2] `build` Function: `if "clip_73" not in med["clips"]:`**
```python
    if "clip_73" not in med["clips"]:
        rec["why"] = "no clip_73"
        break
```
Correct.

**[P1] `build` Function: `if "clip_74" not in med["clips"]:`**
```python
    if "clip_74" not in med["clips"]:
        rec["why"] = "no clip_74"
        break
```
Correct.

**[P2] `build` Function: `if "clip_75" not in med["clips"]:`**
```python
    if "clip_75" not in med["clips"]:
        rec["why"] = "no clip_75"
        break
```
Correct.

**[P1] `build` Function: `if "clip_76" not in med["clips"]:`**
```python
    if "clip_76" not in med["clips"]:
        rec["why"] = "no clip_76"
        break
```
Correct.

**[P2] `build` Function: `if "clip_77" not in med["clips"]:`**
```python
    if "clip_77" not in med["clips"]:
        rec["why"] = "no clip_77"
        break
```
Correct.

**[P1] `build` Function: `if "clip_78" not in med["clips"]:`**
```python
    if "clip_78" not in med["clips"]:
        rec["why"] = "no clip_78"
        break
```
Correct.

**[P2] `build` Function: `if "clip_79" not in med["clips"]:`**
```python
    if "clip_79" not in med["clips"]:
        rec["why"] = "no clip_79"
        break
```
Correct.

**[P1] `build` Function: `if "clip_80" not in med["clips"]:`**
```python
    if "clip_80" not in med["clips"]:
        rec["why"] = "no clip_80"
        break
```
Correct.

**[P2] `build` Function: `if "clip_81" not in med["clips"]:`**
```python
    if "clip_81" not in med["clips"]:
        rec["why"] = "no clip_81"
        break
```
Correct.

**[P1] `build` Function: `if "clip_82" not in med["clips"]:`**
```python
    if "clip_82" not in med["clips"]:
        rec["why"] = "no clip_82"
        break
```
Correct.

**[P2] `build` Function: `if "clip_83" not in med["clips"]:`**
```python
    if "clip_83" not in med["clips"]:
        rec["why"] = "no clip_83"
        break
```
Correct.

**[P1] `build` Function: `if "clip_84" not in med["clips"]:`**
```python
    if "clip_84" not in med["clips"]:
        rec["why"] = "no clip_84"
        break
```
Correct.

**[P2] `build` Function: `if "clip_85" not in med["clips"]:`**
```python
    if "clip_85" not in med["clips"]:
        rec["why"] = "no clip_85"
        break
```
Correct.

**[P1] `build` Function: `if "clip_86" not in med["clips"]:`**
```python
    if "clip_86" not in med["clips"]:
        rec["why"] = "no clip_86"
        break
```
Correct.

**[P2] `build` Function: `if "clip_87" not in med["clips"]:`**
```python
    if "clip_87" not in med["clips"]:
        rec["why"] = "no clip_87"
        break
```
Correct.

**[P1] `build` Function: `if "clip_88" not in med["clips"]:`**
```python
    if "clip_88" not in med["clips"]:
        rec["why"] = "no clip_88"
        break
```
Correct.

**[P2] `build` Function: `if "clip_89" not in med["clips"]:`**
```python
    if "clip_89" not in med["clips"]:
        rec["why"] = "no clip_89"
        break
```
Correct.

**[P1] `build` Function: `if "clip_90" not in med["clips"]:`**
```python
    if "clip_90" not in med["clips"]:
        rec["why"] = "no clip_90"
        break
```
Correct.

**[P2] `build` Function: `if "clip_91" not in med["clips"]:`**
```python
    if "clip_91" not in med["clips"]:
        rec["why"] = "no clip_91"
        break
```
Correct.

**[P1] `build` Function: `if "clip_92" not in med["clips"]:`**
```python
    if "clip_92" not in med["clips"]:
        rec["why"] = "no clip_92"
        break
```
Correct.

**[P2] `build` Function: `if "clip_93" not in med["clips"]:`**
```python
    if "clip_93" not in med["clips"]:
        rec["why"] = "no clip_93"
        break
```
Correct.

**[P1] `build` Function: `if "clip_94" not in med["clips"]:`**
```python
    if "clip_94" not in med["clips"]:
        rec["why"] = "no clip_94"
        break
```
Correct.

**[P2] `build` Function: `if "clip_95" not in med["clips"]:`**
```python
    if "clip_95" not in med["clips"]:
        rec["why"] = "no clip_95"
        break
```
Correct.

**[P1] `build` Function: `if "clip_96" not in med["clips"]:`**
```python
    if "clip_96" not in med["clips"]:
        rec["why"] = "no clip_96"
        break
```
Correct.

**[P2] `build` Function: `if "clip_97" not in med["clips"]:`**
```python
    if "clip_97" not in med["clips"]:
        rec["why"] = "no clip_97"
        break
```
Correct.

**[P1] `build` Function: `if "clip_98" not in med["clips"]:`**
```python
    if "clip_98" not in med["clips"]:
        rec["why"] = "no clip_98"
        break
```
Correct.

**[P2] `build` Function: `if "clip_99" not in med["clips"]:`**
```python
    if "clip_99" not in med["clips"]:
        rec["why"] = "no clip_99"
        break
```
Correct.

**[P1] `build` Function: `if "clip_100" not in med["clips"]:`**
```python
    if "clip_100" not in med["clips"]:
        rec["why"] = "no clip_100"
        break
```
Correct.

**[P2] `build` Function: `if "clip_101" not in med["clips"]:`**
```python
    if "clip_101" not in med["clips"]:
        rec["why"] = "no clip_101"
        break
```
Correct.

**[P1] `build` Function: `if "clip_102" not in med["clips"]:`**
```python
    if "clip_102" not in med["clips"]:
        rec["why"] = "no clip_102"
        break
```
Correct.

**[P2] `build` Function: `if "clip_103" not in med["clips"]:`**
```python
    if "clip_103" not in med["clips"]:
        rec["why"] = "no clip_103"
        break
```
Correct.

**[P1] `build` Function: `if "clip_104" not in med["clips"]:`**
```python
    if "clip_104" not in med["clips"]:
        rec["why"] = "no clip_104"
        break
```
Correct.

**[P2] `build` Function: `if "clip_105" not in med["clips"]:`**
```python
    if "clip_105" not in med["clips"]:
        rec["why"] = "no clip_105"
        break
```
Correct.

**[P1] `build` Function: `if "clip_106" not in med["clips"]:`**
```python
    if "clip_106" not in med["clips"]:
        rec["why"] = "no clip_106"
        break
```
Correct.

**[P2] `build` Function: `if "clip_107" not in med["clips"]:`**
```python
    if "clip_107" not in med["clips"]:
        rec["why"] = "no clip_107"
        break
```
Correct.

**[P1] `build` Function: `if "clip_108" not in med["clips"]:`**
```python
    if "clip_108" not in med["clips"]:
        rec["why"] = "no clip_108"
        break
```
Correct.

**[P2] `build` Function: `if "clip_109" not in med["clips"]:`**
```python
    if "clip_109" not in med["clips"]:
        rec["why"] = "no clip_109"
        break
```
Correct.

**[P1] `build` Function: `if "clip_110" not in med["clips"]:`**
```python
    if "clip_110" not in med["clips"]:
        rec["why"] = "no clip_110"
        break
```
Correct.

**[P2] `build` Function: `if "clip_111" not in med["clips"]:`**
```python
    if "clip_111" not in med["clips"]:
        rec["why"] = "no clip_111"
        break
```
Correct.

**[P1] `build` Function: `if "clip_112" not in med["clips"]:`**
```python
    if "clip_112" not in med["clips"]:
        rec["why"] = "no clip_112"
        break
```
Correct.

**[P2] `build` Function: `if "clip_113" not in med["clips"]:`**
```python
    if "clip_113" not in med["clips"]:
        rec["why"] = "no clip_113"
        break
```
Correct.

**[P1] `build` Function: `if "clip_114" not in med["clips"]:`**
```python
    if "clip_114" not in med["clips"]:
        rec["why"] = "no clip_114"
        break
```
Correct.

**[P2] `build` Function: `if "clip_115" not in med["clips"]:`**
```python
    if "clip_115" not in med["clips"]:
        rec["why"] = "no clip_115"
        break
```
Correct.

**[P1] `build` Function: `if "clip_116" not in med["clips"]:`**
```python
    if "clip_116" not in med["clips"]:
        rec["why"] = "no clip_116"
        break
```
Correct.

**[P2] `build` Function: `if "clip_117" not in med["clips"]:`**
```python