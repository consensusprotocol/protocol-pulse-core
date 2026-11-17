# gemma-4-31b-it (google/gemma-4-31b-it) 356 s finish=stop usage in 12037 / out 5611 usd_reported=0.001069 usd~0.120 (upper-bound price)

The code implements the "soft" hook bar for the never-empty pass (Stage 2b) as required by Rulings 136/137/138.

### Analysis

1.  **Hard vs. Soft Logic**: The clean pass (`soft=False`) remains strictly hard because `m["hook_bar_soft"]` is never set, meaning `hook_own` will only return `passes=True` if the hard bar is met (`ok=True`). In the soft pass, `_build` identifies the best `HOOK_SOFT_MAX` (2) hooks that are under the bar (via `hook_bar_under`) and marks them.
2.  **Strictness of `hook_bar_under`**: The function correctly returns `None` (staying HARD) if:
    *   Any rating part is missing or not an integer (`isinstance(x, int) and not isinstance(x, bool)`).
    *   No valid calibration exists (`_live_bar` is `None`).
    *   The rater of the hook does not match the rater of the calibration (`r.get("backend") != live.get("rater")`).
3.  **Vision Cost Bound**: By limiting the soft-pass candidates to `HOOK_SOFT_MAX` before they are added to `rated_open`, the code ensures that at most 2 additional vision checks are performed per medley attempt.
4.  **Flagging and Inventory**: 
    *   The `inventory` function correctly identifies the soft-pass flag via `hook_fl` (extracted from the `hook_own` result) and generates the required plain-sentence warning.
    *   The "medley" row is marked `FLAGGED` only if the verdict passed (`medley[0]`) and the hook was soft-passed.
    *   `package_pin.SOFT_GATES` now includes `"medley"`, allowing the seal to proceed despite the flag.
5.  **Data Integrity**: The use of `with_verdict` (as noted in the prompt) ensures that the `hook_bar_soft` mark is applied to copies of the moment objects, preventing pollution of the original data or the driver's spotlight pass.
6.  **Tests**: The new tests in `test_ruling_137.py` are comprehensive, covering the specific "hard" failure cases (wrong rater, unmeasured parts), the `HOOK_SOFT_MAX` limit, and the end-to-end `Rig` flow from clean-pass failure to soft-pass flagged success.

### Findings

No violations of the Governing Laws or the specific requirements of Rulings 136/137/138 were found. The implementation is precise and the test coverage is sufficient.

P1_OR_WORSE: 0