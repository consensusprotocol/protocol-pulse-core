# gemma-4-31b-it (google/gemma-4-31b-it) 175 s finish=stop usage in 11687 / out 3313 usd_reported=0.000773 usd~0.085 (upper-bound price)

The code implements **RULING 146 (1) and (2)**, introducing a "Never-Empty" (soft) pass that allows specific visual and audio failures to pass provided they are flagged and the output is restricted to 16:9.

### Analysis against Governing Laws & Requirements

1.  **9:16 Protection (Ruling 146-1):**
    *   The `soft_graphics` function explicitly sets `m["visual"] = dict(v, formats=["16x9"], ...)`. 
    *   Because `package_pin.formats_of` (referenced in the logic) seals the package based on the most restrictive clip format, any package containing a "soft graphics" clip is forced to `["16x9"]`.
    *   The `vbad` (visual bad) check in `_build` (lines 68-69 and 78-79) specifically excludes clips where `soft and soft_graphics(m)` is True. Since these clips are marked `16x9` only, they can never appear in a 9:16 render.
    *   **Verdict:** Compliant.

2.  **Hard Failures (Third Person, Unmeasured, Mid-word):**
    *   **Third Person:** `visual_pin.graphics_only` returns `None` if `hook_block(rec)` is not None. Third persons are handled by `hook_block`, ensuring they stay HARD.
    *   **Unmeasured:** `visual_pin.graphics_only` requires `rec.get("measured") is True`. Unmeasured records stay HARD.
    *   **Mid-word Cuts:** In `_build` (line 46), the `ONSET_QUIET` regex specifically targets the "ms of genuine quiet... <" string. A mid-word cut (which would have a different `why` string) will not trigger `soft=True` and will remain a HARD failure.
    *   **Verdict:** Compliant.

3.  **Clean Pass Integrity:**
    *   All "soft" logic in `_build` is guarded by the `soft` boolean (passed by the orchestrator).
    *   The `_can_open` check (line 36) allows `on.get("soft") is True`, but `soft` is only assigned to the `hook_onset` record during the soft pass.
    *   **Verdict:** Compliant.

4.  **Inventory and Flagging:**
    *   The `inventory` function correctly adds the `FLAGGED` status and the required descriptive sentences for both `hook_onset` (abrupt start) and `graphics` (ticker/bug/etc. in 16:9).
    *   `package_pin.SOFT_GATES` is updated to include these, ensuring they do not block the final pin.
    *   **Verdict:** Compliant.

5.  **Test Coverage:**
    *   `TestRuling146` covers the critical edge cases:
        *   `test_the_shows_own_graphics_and_what_stays_hard`: Validates that third persons, old versions, and unmeasured records are rejected.
        *   `test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged`: Validates the end-to-end flow of a ticker forcing 16:9 and the correct flag string.
        *   `test_a_hook_with_a_quiet_shortfall_opens_flagged`: Validates G17a soft pass.
        *   `test_an_unmeasured_or_other_onset_failure_stays_hard`: Validates that mid-word cuts are still HARD.
    *   **Verdict:** Comprehensive.

### Final Review
The implementation is precise. It correctly distinguishes between a "measured shortfall" (which is acceptable in a desperate "never-empty" scenario) and a "structural failure" (mid-word cut or third person), while ensuring that visual artifacts that would be cropped in 9:16 are only permitted in 16:9.

P1_OR_WORSE: 0