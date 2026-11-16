# qwen3.8-27b (qwen/qwen3.8-27b) 85 s finish=stop usage in 8853 / out 7052 usd_reported=0.005440 usd~0.132 (upper-bound price)

I will analyze the provided code diff against the "Governing Laws" and the specific "RULING 123 (2)" requirements.

### Context Analysis
The feature implements **RULING 123 (2)**: If no hook passes for both 16:9 and 9:16 formats, a hook that is *only* refused because the 9:16 crop would cut a lower-third/bug (Ruling 93 violation) may open a package sealed as `["16x9"]` only. This hook is exempted from the 9:16 layout check *only* when it is the first segment (the hook). As a clip, it remains blocked.

### Code Review

**1. `pipeline/visual_pin.py` - `crop_only(rec)`**
*   **Logic**: Checks if `rec` is measured, current version, and has no `hook_block` (Ruling 70). It iterates `burned_in` items. It identifies items that cause a block (`burned_block`). It verifies that *all* blocking items are:
    *   Kind in `RUNNING` (lower third/bug) or `CAPTION`? Wait, the docstring says "lower third or bug". The code checks `x["kind"] in RUNNING`. Let's assume `RUNNING` contains lower thirds/bugs.
    *   `whole_in_16x9` is True.
    *   `in_9x16` is "cut".
    *   `covers_speaker` is False.
*   **Potential Issue**: The code returns `None` if `formats(rec) and not RENDER_16X9_ONLY`. This seems to be a guard against records that are already explicitly formatted for 16:9 only? Or perhaps it's checking if the record *claims* to be 16:9 only already? The logic `if ... (formats(rec) and not RENDER_16X9_ONLY): return None` is slightly ambiguous without seeing `RENDER_16X9_ONLY` definition, but likely ensures we don't double-process or apply this to records that are already restricted.
*   **Law Compliance**:
    *   **SENTENCE LAW**: Not directly applicable to visual pins, but the hook selection relies on valid clips.
    *   **LAW 20 / M2**: Thresholds are constants. The logic is deterministic.
    *   **M12 FAIL CLOSED**: If `rec` is not measured or version mismatch, it returns `None` (fails closed, i.e., doesn't qualify for the exception).

**2. `pipeline/package.py` - `build()`**
*   **Logic**:
    ```python
    sixteen = {}
    if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]:
        # Condition: There are rated openers, AND NONE of them are unblocked (i.e., all are blocked).
        for m in rated_open:
            why_c = VP.crop_only(m.get("visual"))
            if why_c:
                m.pop("visual_hook_block", None)
                blocked.pop(m["moment_id"], None)
                m["visual"] = dict(m["visual"], formats=["16x9"])
                m["sixteen_nine_only"] = sixteen[m["moment_id"]] = why_c
    ```
*   **Critical Check 1: "Exception fires only when no both-format hook exists"**:
    The condition `not [m for m in rated_open if not m.get("visual_hook_block")]` translates to: "There is no moment in `rated_open` that does *not* have a `visual_hook_block`." In other words, *every* moment in `rated_open` has a `visual_hook_block`.
    *   If a hook passes for both formats, it would *not* have `visual_hook_block` (or it would be cleared earlier).
    *   If a hook is blocked by Ruling 70 (third person), it has `visual_hook_block`. `crop_only` returns `None` for these (because `hook_block(rec) is not None`). So they won't be unblocked.
    *   If a hook is blocked by Ruling 93 (crop), it has `visual_hook_block`. `crop_only` returns the reason. It *will* be unblocked.
    *   **Scenario**: What if there are two hooks? Hook A is blocked by Ruling 70. Hook B is blocked by Ruling 93.
        *   `rated_open` contains A and B.
        *   Both have `visual_hook_block`.
        *   The condition `not [m for m in rated_open if not m.get("visual_hook_block")]` is True (list is empty).
        *   Loop runs.
        *   A: `crop_only` returns `None` (Ruling 70). A remains blocked.
        *   B: `crop_only` returns reason. B is unblocked, marked `sixteen_nine_only`.
        *   Result: B becomes the hook.
        *   **Is this correct?** The order says: "when no hook passes for both formats... a hook whose only refusal is ruling 93's 9:16 crop may open".
        *   If Hook A was blocked by Ruling 70, it does *not* pass for both formats (it fails the "third person" check which applies to both). Hook B fails 9:16 crop. So *no* hook passes for both formats. The exception should apply to B.
        *   **However**, what if Hook A was blocked by *something else* that isn't Ruling 70 or 93? `crop_only` handles specific cases.
        *   **What if there is a hook that passes both formats?**
            *   If Hook C passes both, it does *not* have `visual_hook_block`.
            *   The list `[m for m in rated_open if not m.get("visual_hook_block")]` would contain C.
            *   The condition `not [...]` would be False.
            *   The exception block is skipped.
            *   Hook C remains the valid hook.
            *   **This satisfies "A both-format hook always wins".**

*   **Critical Check 2: "Only the hook is excused"**:
    The code modifies `m` (the moment) in `rated_open`. Later, `hook_order` is called on `cleared.values()`.
    Wait, `rated_open` is a list of moments. `cleared` is a dict.
    Let's trace how `rated_open` relates to `cleared`.
    In `build`, `rated_open` is likely the list of moments that passed the initial hook bar.
    The code modifies `m` in place: `m.pop("visual_hook_block", None)`.
    Then `out["hook_pool"]["passing"]` is calculated from `hook_order([m for m in cleared.values() if can_open(m)])`.
    Does `cleared` contain the same objects as `rated_open`?
    Usually, `cleared` is built from `moments`. If `rated_open` contains references to the same dicts in `cleared`, the modification persists.
    `can_open(m)` checks `if m.get("visual_hook_block"): return False`.
    Since we popped `visual_hook_block`, `can_open` will now return `True` (assuming other conditions in `can_open` are met).
    So the moment becomes a valid hook candidate.

*   **Critical Check 3: "Seal says 16:9 only"**:
    `m["visual"] = dict(m["visual"], formats=["16x9"])`.
    This updates the visual record.
    Later, `package_pin.formats_of(out["package"]["segments"])` is used to seal the package.
    The test `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only` asserts `package_pin.formats_of(...) == ["16x9"]`.
    This implies `formats_of` reads the `formats` key from the segment's visual data.
    Since we set `formats=["16x9"]` on the hook moment, and it becomes the first segment, the package should be sealed as 16:9 only.

*   **Critical Check 4: "As a clip its refusal stands"**:
    The code has two layout checks later in `build`:
    1.  `vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}`
    2.  `vbad = {m["moment_id"]: ... for m in segs if VP.layout_block(m.get("visual")) and not (m is segs[0] and opens_16x9(m))}`
    
    `opens_16x9(m)` checks:
    ```python
    return bool(m.get("sixteen_nine_only")) and v.get("formats") == ["16x9"] and bool(VP.crop_only(v))
    ```
    If `m` is the hook (`order[0]` or `segs[0]`) and it has the `sixteen_nine_only` flag, `opens_16x9` returns True.
    The condition `not (m is order[0] and opens_16x9(m))` becomes `not (True and True)` = `False`.
    So the `if` block for adding to `vbad` is skipped for the hook.
    For any other clip (`m is not order[0]`), `opens_16x9` might be True (if it was also marked), but `m is order[0]` is False, so `not (False and ...)` is `True`.
    Wait. If a *clip* (not the hook) has `sixteen_nine_only` set, does it get blocked?
    The code only sets `sixteen_nine_only` on moments in `rated_open` that were unblocked to serve as the *hook*.
    If a moment is not the hook, it remains in `blocked` or is not selected as the hook.
    If it *is* selected as a clip later, does it have `visual_hook_block`?
    The code `m.pop("visual_hook_block", None)` removed the block.
    So `can_open` returns True.
    But `layout_block` is checked separately.
    `VP.layout_block(m.get("visual"))` will still return a reason because the visual record still has the burned-in text that cuts in 9:16.
    The exception `not (m is order[0] and opens_16x9(m))` only applies if `m` is the *first* segment.
    If this moment is used as a *clip* (not the first segment), `m is order[0]` is False.
    So `not (False and ...)` is True.
    So `VP.layout_block` is evaluated. It returns a reason.
    So `m` is added to `vbad`.
    So the clip is rejected.
    **This satisfies "As a clip its refusal stands".**

**3. `pipeline/package.py` - `opens_16x9(m)`**
*   Imports `visual_pin as VP` inside the function. This is fine for avoiding circular imports if any, though `VP` is likely already imported at the top of `package.py` (used as `VP.crop_only` in `build`).
*   Checks `m.get("sixteen_nine_only")`.
*   Checks `v.get("formats") == ["16x9"]`.
*   Checks `bool(VP.crop_only(v))`.
*   This ensures the exception is only valid if the *current* state of the visual record still qualifies as a "crop only" refusal.

**4. Tests**
*   `test_only_a_crop_refusal_qualifies`: Verifies `crop_only` logic.
*   `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only`: Verifies the build logic.
*   `test_a_both_format_hook_always_wins`: Verifies that if a good hook exists, the exception doesn't trigger.
*   `test_as_a_clip_its_refusal_stands`: Verifies that if the moment is not the hook, it is still blocked by layout.

### Potential Issues / Findings

**[P1] Ambiguity in `crop_only` regarding `formats(rec)`**
In `visual_pin.py`:
```python
if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
        isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or \
        (formats(rec) and not RENDER_16X9_ONLY):
    return None
```
The condition `(formats(rec) and not RENDER_16X9_ONLY)` is unclear.
If `RENDER_16X9_ONLY` is a global flag indicating the *current render target* is 16:9 only, then `not RENDER_16X9_ONLY` means "we are NOT rendering 16:9 only".
If we are rendering 9:16 (or both), and `formats(rec)` returns something (e.g., `["16x9", "9x16"]`), then `formats(rec)` is truthy.
If `RENDER_16X9_ONLY` is False, `not False` is True.
So `formats(rec) and True` is True.
Then `return None`.
This would mean `crop_only` returns `None` (doesn't qualify) if the record has *any* formats defined and we are not in a 16:9-only render mode?
This seems backwards or dependent on context not visible.
However, looking at the test `test_only_a_crop_refusal_qualifies`, it calls `VP.crop_only(self.rec())`.
`self.rec()` creates a base dict: `{"version": VP.VERSION, "measured": True, "flags": [], "burned_in": ...}`.
It does *not* include a `formats` key.
So `formats(rec)` likely returns `None` or `[]` or `False` if the key is missing.
If `formats(rec)` is falsy, the condition `(formats(rec) and ...)` is False.
So the `return None` is not triggered by this clause.
But what if a record *does* have `formats`?
The Ruling says: "Ruling 93 as amended already lets a clip with burned-in text go 16:9-ONLY... Apply the same to a hook".
If a record is *already* sealed as 16:9 only, does it need this exception?
The exception is for records that are *refused* by the 9:16 crop.
If a record is already 16:9 only, it might not be "refused" by the 9:16 crop in the same way, or it might be handled by a different path.
The code in `build` sets `m["visual"] = dict(m["visual"], formats=["16x9"])` *after* `crop_only` returns a reason.
So `crop_only` is called on the *original* record.
If the original record has `formats` defined, and `RENDER_16X9_ONLY` is False, `crop_only` returns `None`.
This might be a valid guard: "If this record is already explicitly formatted, don't apply this dynamic exception."
However, the variable name `RENDER_16X9_ONLY` suggests it's a global state. If the pipeline is running in a mode where it *can* render 16:9 only, this flag might be relevant.
Given the lack of context on `RENDER_16X9_ONLY`, this is a potential logic trap, but likely intentional to prevent overriding explicit format seals. I will flag it as a P2 for clarity/verification.

**[P2] `opens_16x9` re-evaluates `crop_only`**
`opens_16x9` calls `VP.crop_only(v)` again.
In `build`, we already called `VP.crop_only` to decide to unblock.
We stored the result in `m["sixteen_nine_only"]`.
Then we modified `m["visual"]` to add `formats=["16x9"]`.
Does adding `formats=["16x9"]` to the visual record change the result of `crop_only`?
`crop_only` checks `formats(rec)`.
If `formats(rec)` now returns `["16x9"]`, and `RENDER_16X9_ONLY` is False, `crop_only` might return `None` due to the `(formats(rec) and not RENDER_16X9_ONLY)` clause.
If `crop_only` returns `None`, `opens_16x9` returns `False`.
If `opens_16x9` returns `False`, the exception in the layout check `not (m is order[0] and opens_16x9(m))` becomes `not (True and False)` = `True`.
So the layout block *is* applied.
So the hook is *rejected*.
This would break the feature if `RENDER_16X9_ONLY` is False.
Let's re-read `crop_only`:
```python
if ... or (formats(rec) and not RENDER_16X9_ONLY):
    return None
```
If `RENDER_16X9_ONLY` is a constant `True` in this context?
Or if `formats(rec)` is empty/None initially?
In `build`, `m["visual"]` is the original record.
If the original record did *not* have `formats`, `crop_only` passed.
Then we set `formats=["16x9"]`.
Now `opens_16x9` calls `crop_only` on the *modified* record.
If `formats(rec)` is now `["16x9"]` (truthy), and `RENDER_16X9_ONLY` is False, `crop_only` returns `None`.
Then `opens_16x9` returns `False`.
Then the layout check fails to exempt the hook.
The hook is blocked.
**This is a P0/P1 risk.**
Does `RENDER_16X9_ONLY` exist?
The prompt says: "The integrator confirms a pin sealed formats ["16x9"] renders 16:9 only through its existing path... and needs nothing new."
If the existing path handles 16:9 only pins, maybe `RENDER_16X9_ONLY` is not a global flag but a property of the render context?
Or maybe `formats(rec)` in `crop_only` is meant to check if the record *claims* to be 16:9 only *already*?
If `crop_only` is designed to return `None` for records that are *already* 16:9 only (because they don't need the "exception", they are just 16:9 only), then re-evaluating it after setting `formats=["16x9"]` would cause `opens_16x9` to fail.
However, `opens_16x9` is used to *exempt* the hook from the 9:16 crop check.
If the hook is now sealed as 16:9 only, does it still need to be exempted from the 9:16 crop check?
The check is `VP.layout_block(m.get("visual"))`.
`layout_block` likely checks if the visual is valid for the *current* render formats.
If the package is sealed 16:9 only, does `layout_block` still complain about the 9:16 crop?
The code comment says: "ruling 93 (not measured included, law L-m)".
If the package is 16:9 only, the 9:16 crop is irrelevant.
But the code explicitly checks `VP.layout_block` and then applies the exception.
If `opens_16x9` returns `False` because `crop_only` now returns `None` (due to `formats` being set), the exception is not applied.
If the exception is not applied, `vbad` will contain the hook.
The hook will be dropped.
**This suggests a logic flaw in `opens_16x9` or `crop_only` interaction.**

Let's look at `crop_only` again.
`if ... (formats(rec) and not RENDER_16X9_ONLY): return None`
If `RENDER_16X9_ONLY` is `True`, then `not True` is `False`. The clause is `False`. `crop_only` proceeds.
If `RENDER_16X9_ONLY` is `False`, and `formats(rec)` is `["16x9"]`, the clause is `True`. `crop_only` returns `None`.
So, if the system is *not* in a "16:9 only render mode", `crop_only` refuses to qualify a record that has `formats` set.
But we *just* set `formats` to `["16x9"]`.
So `opens_16x9` will fail.
Unless `RENDER_16X9_ONLY` is `True`?
The Ruling says "opens a package sealed formats ['16x9']".
It doesn't say the *render mode* is 16:9 only. It says the *package* is sealed 16:9 only.
If `RENDER_16X9_ONLY` is a global flag for the *entire pipeline run*, and this run is mixed (some 16:9, some 9:16), then `RENDER_16X9_ONLY` is likely `False`.
In that case, `crop_only` returns `None` for the modified record.
`opens_16x9` returns `False`.
The hook is not exempted.
The hook is blocked by `layout_block`.
The feature fails.

**Wait**, look at `layout_block`.
`layout_block` probably checks if the visual is valid for the *formats* the package is being built for.
If the package is being built for 16:9 only (because the hook forces it?), then `layout_block` might not complain about 9:16.
But the code *first* calculates `vbad` using `layout_block`, and *then* filters `vbad` using `opens_16x9`.
If `layout_block` returns a reason (because it sees the 9:16 crop issue), and `opens_16x9` returns `False` (because `crop_only` failed on the modified record), then the hook is in `vbad`.
Then `if vbad: ... return None`.
The package is not built.

**Is `RENDER_16X9_ONLY` a typo for something else?**
Or does `formats(rec)` in `crop_only` refer to the *original* formats?
No, `rec` is the argument.
In `opens_16x9`, `v` is `m.get("visual")`, which is the *modified* visual.
So `crop_only` sees the modified visual.

**Hypothesis**: `RENDER_16X9_ONLY` is `True` in the context where this exception is needed?
No, the exception is for *mixed* packages where the hook *forces* 16:9.
If the whole render was 16:9 only, the 9:16 crop wouldn't be an issue in the first place (or would it? If the source is 16:9, 9:16 is a crop. If the render is 16:9 only, we don't render 9:16. So `layout_block` might not check 9:16 if the target is 16:9 only).
If `layout_block` is aware of the target format, and the target is 16:9 only, it might not block.
But the code *explicitly* adds the `opens_16x9` check, implying `layout_block` *does* block even if the target is 16:9 only?
Or maybe `layout_block` is format-agnostic and always checks 9:16 crop?
If `layout_block` always checks 9:16 crop, then we *need* the exception.
And if we need the exception, `opens_16x9` must return `True`.
For `opens_16x9` to return `True`, `crop_only` must return a reason.
For `crop_only` to return a reason, `(formats(rec) and not RENDER_16X9_ONLY)` must be `False`.
Since `formats(rec)` is `["16x9"]` (True), `not RENDER_16X9_ONLY` must be `False`.
So `RENDER_16X9_ONLY` must be `True`.
If `RENDER_16X9_ONLY` is `True`, it means the *render* is 16:9 only.
But the Ruling says "opens a package sealed formats ['16x9']".
If the render is 16:9 only, why do we need this complex exception?
Maybe `RENDER_16X9_ONLY` is not a global flag, but a property of the *moment* or *package*?
No, it's used in `visual_pin.py` without arguments. It's a global.

**Alternative Interpretation**:
Maybe `formats(rec)` in `crop_only` is meant to check if the record is *already* restricted to 16:9 *before* we apply this exception?
If so, the logic `if formats(rec) ... return None` means "If it's already 16:9 only, don't apply this exception (because it's not needed, or handled elsewhere)".
But we *set* `formats` to `["16x9"]` *after* `crop_only` is called in `build`.
So `crop_only` in `build` sees the *original* record (no formats). It returns a reason.
Then we set formats.
Then `opens_16x9` is called later. It sees the *modified* record (with formats).
If `RENDER_16X9_ONLY` is `False`, `crop_only` returns `None`.
`opens_16x9` returns `False`.
Exception fails.

**Conclusion**: There is a high probability that `opens_16x9` will fail to exempt the hook because `crop_only` returns `None` for the modified record (due to `formats` being set and `RENDER_16X9_ONLY` being `False`).
This would result in the hook being blocked, and the package failing to build.
**This is a P0 defect.**

**Fix**: `opens_16x9` should not re-evaluate `crop_only` on the modified record. It should rely on the `sixteen_nine_only` flag and the `formats` check.
Or, `crop_only` should not return `None` if `formats` is `["16x9"]` and `RENDER_16X9_ONLY` is `False`?
Actually, if `RENDER_16X9_ONLY` is `False`, it means we are *not* in a 16:9 only render mode.
But the package *is* sealed 16:9 only.
Maybe `RENDER_16X9_ONLY` should be `True` for this package?
If the package is sealed 16:9 only, the render *is* 16:9 only.
So `RENDER_16X9_ONLY` should be `True`.
If `RENDER_16X9_ONLY` is `True`, `not True` is `False`.
`formats(rec) and False` is `False`.
`crop_only` proceeds.
It checks the burned-in items.
It returns the reason.
`opens_16x9` returns `True`.
Exception applies.
So, **if** `RENDER_16X9_ONLY` is correctly set to `True` when the package is sealed 16:9 only, the code works.
Does the code set `RENDER_16X9_ONLY`?
The diff does not show `RENDER_16X9_ONLY` being set.
It is likely a global variable in `visual_pin.py` or imported.
If it is a global that is *not* updated when the package is sealed 16:9 only, then it remains `False` (assuming default is mixed).
Then `crop_only` fails.
**This is a P1 defect** (depends on global state management not shown in diff).

**[P2] `sixteen` dict usage**
`sixteen[m["moment_id"]] = why_c`
This is used to populate `out["hook_pool"]["sixteen_nine_only"]`.
This looks correct.

**[P3] Test `test_as_a_clip_its_refusal_stands`**
The test asserts `out["package"] is None or "y" not in [s["moment_id"] for s in out["package"]["segments"]]`.
If the package is built with `y` as a clip, it should fail.
The test setup: `visuals={"y": self.CUT}`.
`y` is a clip (not the hook, since `h` is the hook? No, `h` is the hook in other tests).
In this test, `MS` has `h, x, y, z`.
`visuals` only has `y`.
`hooks` is not specified, so default?
The test says `Rig(self.MS, ["h", "x", "y", "z"], ... visuals={"y": self.CUT})`.
If `y` is the only one with a visual cut, and it's not the hook, it should be blocked.
The test asserts it is not in the segments.
This seems correct.

### Summary of Findings

1.  **[P1] `opens_16x9` / `crop_only` Interaction**: `opens_16x9` re-evaluates `crop_only` on the visual record *after* `formats=["16x9"]` has been set. If `RENDER_16X9_ONLY` is `False` (mixed render mode), `crop_only` returns `None` due to the `(formats(rec) and not RENDER_16X9_ONLY)` guard. This causes `opens_16x9` to return `False`, failing to exempt the hook from the layout block. The hook is then rejected, and the package fails to build. This relies on `RENDER_16X9_ONLY` being `True` for 16:9-only packages, which is not evident in the diff.
2.  **[P2] `RENDER_16X9_ONLY` Global State**: The logic depends on a global flag `RENDER_16X9_ONLY` that is not shown being updated in the diff. If this flag is not synchronized with the package's sealed formats, the feature will break.
3.  **[P3] Clarity of `crop_only` Guard**: The guard `(formats(rec) and not RENDER_16X9_ONLY)` is cryptic. It prevents `crop_only` from qualifying records that have explicit formats unless in 16:9-only mode. This is likely intentional to avoid double-processing, but it creates the P1 issue.

P1_OR_WORSE: 1