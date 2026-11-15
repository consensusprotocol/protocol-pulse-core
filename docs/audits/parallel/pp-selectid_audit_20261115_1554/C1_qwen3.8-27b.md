# qwen3.8-27b (qwen/qwen3.8-27b) 194 s finish=stop usage in 27667 / out 4552 usd_reported=0.004532 usd~0.151 (upper-bound price)

I will analyze the code changes for `RULING 116` (Calibrated Line-Up Bar) against the provided laws and the specific "PLEASE CHECK" items.

### Analysis of `pipeline/lineup_bar.py`

1.  **`floors_from` Logic**:
    *   It calculates the minimum rating for each part (`clip`, `vo_point`) across the provided runs.
    *   It enforces `FLOOR_MIN` (3).
    *   It raises `ValueError` if runs are missing or ratings are not integers.
    *   *Observation*: The logic `vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]` correctly isolates the "clip" minimums and "vo_point" values. The check `if len(vals) != len(rs)` ensures every run contributed a value. This looks robust.

2.  **`bar` Logic**:
    *   Loads the calibration file via `HB.load` (hook_bar's seal mechanism).
    *   Checks `rater` is a non-empty string.
    *   Checks `question_versions` match the current `MEDLEY_VERSION` and `COHERENCE_VERSION`.
    *   Checks `measured_at` is valid (timezone, not in future).
    *   Checks `valid_h` (null means no expiry, otherwise checks age).
    *   Checks floors are >= `FLOOR_MIN`.
    *   *Observation*: This correctly implements the "fail closed" requirement (M12). If any check fails, it returns `(None, why)`, forcing the caller to use the standard bar.

3.  **`floors_for` Logic**:
    *   Returns calibrated floors only if `live` is not None AND `backend == live["rater"]`.
    *   Otherwise, returns standard floors.
    *   *Observation*: This strictly enforces that *only* the calibrated rater gets the relaxed bar. Any other model (Plan B, etc.) gets the stricter standard bar. This satisfies Check (1).

### Analysis of `pipeline/package.py` Changes

1.  **`_live_lineup_bar`**:
    *   Caches the result of `LB.bar` based on file mtime and minute.
    *   *Observation*: Standard caching pattern, consistent with `_live_bar`.

2.  **`lineup_floors`**:
    *   Retrieves the live bar and calls `LB.floors_for`.
    *   Returns `(floors, which_bar, sha256_or_None)`.
    *   *Observation*: Correctly propagates the "which bar" info for logging/marking.

3.  **`medley` and `coherence` Functions**:
    *   **`medley`**:
        *   `fl, which, csha = lineup_floors("clips_alone", r.backend)`
        *   `ok = ... and min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] ...`
        *   *Critical Check*: Does it exclude the hook? `labs[0]` is the hook label. The min is taken over `v["clips"].items()` where `lb != labs[0]`. This correctly excludes the hook from the line-up floor check. The hook is judged by its own bar (ruling 115) via `own["passes"]`.
        *   *Observation*: This satisfies Check (2) for `medley`.
    *   **`coherence`**:
        *   `fl, which, csha = lineup_floors("coherence", r.backend)`
        *   `ok = ... and min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and v["vo_point"] >= fl["vo_point"]`
        *   *Critical Check*: Excludes hook from clip min. Checks `vo_point` against `fl["vo_point"]`.
        *   *Observation*: This satisfies Check (2) for `coherence`.

4.  **`last_clip_only` (Ruling 62)**:
    *   `floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]`
    *   `return ... [lb for lb, x in cl.items() if lb != labs[0] and x < floor] == [labs[-1]] ...`
    *   *Observation*: Uses the verdict's own floors. Excludes hook. Correct.

5.  **`build` Function (Ruling 63 Reorder & Weak Clips)**:
    *   **Reorder Condition**:
        *   `floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]`
        *   `if ... min(x for lb, x in cl.items() if lb != labs[0]) >= floor ...`
        *   *Observation*: Previously, this likely used `COHERENCE_MIN` and included the hook in the min (or didn't exclude it properly if the hook rating was low). Now it explicitly excludes the hook and uses the dynamic floor. This fixes the "hook at its floors blocking reorder" issue mentioned in the description.
    *   **Weak Clips Calculation**:
        *   `weak = {by_lab[lb]["moment_id"] for lb, x in cl.items() if lb in by_lab and x < floor}`
        *   *Observation*: Uses the dynamic floor.
    *   **Hook Weakness**:
        *   `hook_weak = (med.get("hook_own") or {}).get("passes") is not True`
        *   *Observation*: Correctly delegates hook judgment to its own bar (ruling 115), not the line-up bar.

6.  **`build` Function (Coherence Failure Handling)**:
    *   **Takeaway Rewrite Condition**:
        *   `cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]`
        *   `if ... coh["vo_point"] < cfl["vo_point"] and (coh.get("hook_own") or {}).get("passes") is True and min(x for lb, x in coh["clips"].items() if lb != "hook") >= cfl["clip"] ...`
        *   *Observation*:
            *   Checks `vo_point` against calibrated/standard floor.
            *   Checks hook passes its *own* bar.
            *   Checks non-hook clips against calibrated/standard floor.
            *   *Potential Issue*: The label check `lb != "hook"` is hardcoded. In `medley`, it used `labs[0]`. In `coherence`, the segments are passed as `pk`, and `labs` is derived from `pk["segments"]`. Let's verify if `labs[0]` is always `"hook"`.
            *   Looking at `coherence` function: `labs = [s["label"] for s in pk["segments"]]`. The first segment is the hook. So `labs[0]` is the hook label.
            *   In the `build` function's coherence block, `coh` is the result of `PK.coherence(...)`. The `coh["clips"]` dict keys are the labels.
            *   The code uses `lb != "hook"`. Is the hook label always `"hook"`?
            *   In `test_medley.py` `Rig.coherence`: `segs = pk["segments"]`. `pk` is built with `labels`. `PK.labels(n)` generates `["hook", "clip_01", ...]`.
            *   So yes, the first label is `"hook"`.
            *   However, using the literal string `"hook"` is slightly less robust than using `labs[0]` if the label scheme ever changes, but given `PK.labels` is the standard generator, it is consistent.
            *   *Wait*, look at `weak` calculation in the same block:
                `weak = {sg["moment_id"] for sg in pk["segments"][1:] if (coh.get("clips") or {}).get(sg["label"], cfl["clip"]) < cfl["clip"]}`
                This iterates `pk["segments"][1:]`, effectively excluding the hook. This is correct.

7.  **`lineup_bar_mark`**:
    *   Returns mark only if `med["bar"] == "calibrated"` AND `coh["bar"] == "calibrated"`.
    *   *Observation*: Satisfies Check (4).

### Analysis of `pipeline/package_pin.py`

*   Adds `lineup_bar` to the pin if present.
*   *Observation*: Correctly places it outside the seal (in the `moments_package` dict, not in the `seal` dict).

### Analysis of Tests

*   `test_lineup_bar.py`:
    *   Tests `floors_from` edge cases (missing runs, non-ints).
    *   Tests `bar` validation (versions, rater, time, seal).
    *   Tests `floors_for` (calibrated vs standard).
    *   Tests `lineup_bar_mark` (both calibrated vs one standard).
    *   Tests live file integrity.
*   `test_medley.py` `TestRuling116LineupBar`:
    *   `test_clips_alone_a_clip_at_3_passes_only_on_the_calibrated_raters_verdict`:
        *   Verifies that a clip rated 3 passes with Grok (calibrated) but fails with Gemini (standard).
    *   `test_coherence_a_clip_or_vo_point_at_3_passes_only_on_the_calibrated_raters_verdict`:
        *   Verifies VO point 3 passes with Grok, fails with DeepSeek.
    *   `test_ruling_62_reads_the_verdicts_own_floor`:
        *   Verifies `last_clip_only` uses the dynamic floor.
    *   `test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors`:
        *   Verifies that a hook rated 3 (at its floor) does *not* block a reorder if the other clips pass the line-up floor.
    *   `test_the_takeaway_alone_is_rewritten_when_only_its_point_is_weak_with_a_hook_at_its_floors`:
        *   Verifies the takeaway rewrite logic handles the hook correctly.
    *   `test_after_a_failed_verdict_only_the_clips_under_its_own_floor_are_swapped`:
        *   Verifies weak clip selection uses the dynamic floor.
    *   `test_the_mark_on_a_package_whose_two_verdicts_passed_on_the_calibrated_bar`:
        *   Verifies the mark is present/absent correctly.

### Potential Issues / Findings

1.  **[P2] Hardcoded "hook" label in `build` coherence block**:
    In `pipeline/package.py`, inside `build()`, the coherence failure handling block uses:
    `min(x for lb, x in coh["clips"].items() if lb != "hook") >= cfl["clip"]`
    While `PK.labels` currently generates `"hook"` as the first label, relying on the literal string `"hook"` is fragile. The `medley` block in the same function uses `labs[0]` (derived from `segs`). The `coherence` block has access to `pk["segments"]`, so it could derive the hook label similarly.
    *However*, looking at the `weak` calculation just below it: `for sg in pk["segments"][1:]`. This implies the first segment is the hook.
    If the label generation changes, this line breaks.
    *Severity*: P2 (Should fix for consistency/robustness, but currently works).

2.  **[P3] `lineup_bar_mark` lambda usage**:
    `lm = lineup_bar_mark(*(lambda c: (c.get("medley"), c.get("coherence")))(out["package"].get("checks") or {}))`
    This is a bit convoluted. It creates a lambda, calls it immediately, and unpacks the result.
    It could be:
    `checks = out["package"].get("checks") or {}`
    `lm = lineup_bar_mark(checks.get("medley"), checks.get("coherence"))`
    *Severity*: P3 (Nit, readability).

3.  **[P1] Check (2) Verification: "No site still judges a line-up on COHERENCE_MIN with the hook's own rating inside"**
    Let's re-verify the `build` function's `medley` reorder condition.
    Old code (implied): `min(cl.values()) >= COHERENCE_MIN`. `cl` includes the hook.
    New code: `min(x for lb, x in cl.items() if lb != labs[0]) >= floor`.
    This correctly excludes the hook.
    
    Let's re-verify the `build` function's `coherence` takeaway rewrite condition.
    Old code (implied): `min(coh["clips"].values()) >= COHERENCE_MIN`. `coh["clips"]` includes the hook.
    New code: `min(x for lb, x in coh["clips"].items() if lb != "hook") >= cfl["clip"]`.
    This correctly excludes the hook.
    
    Let's re-verify `last_clip_only`.
    New code: `[lb for lb, x in cl.items() if lb != labs[0] and x < floor]`.
    Correctly excludes hook.

    Let's re-verify `medley` and `coherence` functions themselves.
    `medley`: `min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"]`. Correct.
    `coherence`: `min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"]`. Correct.

    Are there any *other* sites?
    The description says: "Every place that judges those ratings reads the VERDICT'S OWN floors and leaves the hook's slot to its bar".
    The diff shows changes to:
    - `medley`
    - `coherence`
    - `last_clip_only`
    - `build` (reorder condition)
    - `build` (weak clips for medley)
    - `build` (takeaway rewrite condition)
    - `build` (weak clips for coherence)
    
    It seems all identified sites are updated.

4.  **[P1] Check (1) Verification: "Floors apply only to the calibrated rater's own verdicts"**
    `lineup_floors` calls `LB.floors_for(verdict, backend, live, standard)`.
    `LB.floors_for` checks `if live is not None and backend == live["rater"]`.
    If `backend` is not the rater, it returns `standard`.
    `standard` is `STANDARD_LINEUP` which uses `COHERENCE_MIN` (4).
    This logic is sound.

5.  **[P1] Check (3) Verification: "Floors in the file are the source's minimums"**
    `lineup_calibration.json` has `floors`: `clips_alone.clip: 3`, `coherence.clip: 3`, `coherence.vo_point: 3`.
    The test `TestTheLiveCalibration.test_its_floors_are_its_sources_lowest_ratings` verifies that `LB.floors_from(src)` matches the file's floors.
    `src` is built from `tests/package/proof/clips116/CALIBRATION.json` and `COHERENCE.json`.
    This ensures the file is derived from the actual approved runs.

6.  **[P1] Check (4) Verification: "Mark: both verdicts calibrated, outside the seal"**
    `lineup_bar_mark` returns `None` if either is not "calibrated".
    `package_pin.to_pin` adds `lineup_bar` to the `moments_package` dict.
    The `seal` dict is constructed separately in `package_pin` (not shown in diff, but `to_pin` returns a dict with `moments_package` and `seal`).
    The diff shows:
    ```python
    "moments_package": {
        ...
        **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),
        ...
    }
    ```
    This is outside the `seal`. Correct.

7.  **[P2] `STANDARD_LINEUP` Definition**:
    `STANDARD_LINEUP = {"clips_alone": {"clip": COHERENCE_MIN}, "coherence": {"clip": COHERENCE_MIN, "vo_point": COHERENCE_MIN}}`
    `COHERENCE_MIN` is 4.
    The calibrated floors are 3.
    So the standard bar is stricter (4 > 3). This matches the requirement "standard bar ... is stricter".

8.  **[P2] `valid_h` Handling**:
    `lineup_calibration.json` has `"valid_h": null`.
    `LB.bar` handles `vh is None` by skipping the age check.
    This matches "one fixed source ... does not expire".

9.  **[P3] `floors_from` Error Message**:
    `raise ValueError(f"a {verdict} run has no integer {p!r}: the floors cannot be measured")`
    If `vals` is empty (e.g., all runs had empty `clips`), `min(vals)` would raise `ValueError` anyway, but the check `if len(vals) != len(rs)` catches it first if `rs` is not empty.
    If `rs` is empty, `if not rs: raise ValueError`.
    So it's covered.

10. **[P1] `hook_own` Usage in `build`**:
    In the `medley` reorder condition:
    `(med.get("hook_own") or {}).get("passes") is True`
    This ensures the hook passed its *own* bar before considering the line-up reorder.
    In the `coherence` takeaway rewrite condition:
    `(coh.get("hook_own") or {}).get("passes") is True`
    Same logic.
    This is correct.

11. **[P2] `Rig` Class in `test_medley.py`**:
    The `Rig` class is updated to support `coherences` and `lineup_floors`.
    `Rig.coherence` uses `PK.lineup_floors("coherence", "xai:grok")`.
    Since `RIG_RATER` is `"xai:grok"` and the rig patches `_live_lineup_bar` to return a bar with `rater=RIG_RATER`, the rig will get the calibrated floors.
    This allows testing the calibrated path.
    To test the standard path, the rig would need to use a different backend or patch the bar to be invalid.
    The test `test_clips_alone_a_clip_at_3_passes_only_on_the_calibrated_raters_verdict` uses `self.router(rep, "google:gemini-2.5-pro")`.
    `self.router` creates a `Canned` router and wraps `call` to return a `Reply` with the specified backend.
    `PK.medley` calls `lineup_floors("clips_alone", r.backend)`.
    `r.backend` will be `"google:gemini-2.5-pro"`.
    `LB.floors_for` checks `backend == live["rater"]` (`"xai:grok"`).
    They don't match, so it returns `standard` floors.
    This correctly tests the standard bar path.

### Conclusion

The code implements RULING 116 correctly.
- Floors are calibrated and applied only to the specific rater.
- Standard bar is stricter and applied to all others.
- Hook is excluded from line-up floor checks and judged by its own bar.
- Mark is applied only when both verdicts are calibrated and placed outside the seal.
- Tests cover the key scenarios.

The only minor issues are the hardcoded `"hook"` label in one place (P2) and a readability nit (P3). No P0 or P1 defects found.

P1_OR_WORSE: 0