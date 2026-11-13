# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 10429 / out 1903 usd~0.060 (upper-bound price)

# Code Audit: pp-selectid-0712 (C1_STEP.diff)

## Findings

### P0: None
No critical defects found. The implementation correctly enforces the "fail closed" principle for the strict mode and properly seals the `scorer_pending` flag.

### P1: None
No high-severity issues identified.

### P2: Observations / Minor

**1. Constant Duplication (Maintainability)**
*   **File:** `pipeline/package.py` (line 19) and `pipeline/package_pin.py` (line 75)
*   **Scenario:** `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` are both set to `1`. While the test `test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin` asserts they are equal, they are defined independently. If a future ruling changes the limit for lineups but not for pins (or vice versa), this could lead to subtle inconsistencies if the test is not updated.
*   **Recommendation:** Consider importing one constant into the other module or defining a shared constant in a common config module to ensure they remain synchronized by construction.

**2. Logic Clarity in `trim_problems`**
*   **File:** `pipeline/package_pin.py` (lines 89-101)
*   **Scenario:** The check `if s.get("scorer_pending") is not True` is performed *after* the `has_w != has_s` check in the loop, but the count `n` is calculated before the loop. The logic is correct, but the placement of the `scorer_pending` validation inside the `if has_w or has_s` block (implicitly, because it's after the `continue` for non-trimmed segments) is slightly subtle. Specifically, if a segment has `trimmed_leading` but *not* `untrimmed_start`, it hits `continue` at line 104 *before* checking `scorer_pending` at line 99.
    *   *Wait, let me re-read the diff carefully.*
    *   Line 94: `has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s`
    *   Line 95: `if not has_w and not has_s:` -> checks `scorer_pending` presence (line 96-97) -> `continue`.
    *   Line 99: `if s.get("scorer_pending") is not True:` -> This line is **outside** the `if not has_w and not has_s` block. It executes for **all** segments that are not skipped by the `continue` at line 98.
    *   Line 102: `if has_w != has_s:` -> checks consistency -> `continue`.
    *   **Correction:** The code at line 99 checks `scorer_pending` for **every** segment that has *either* `trimmed_leading` or `untrimmed_start` (or both).
        *   If a segment has `trimmed_leading` but no `untrimmed_start`, `has_w` is True, `has_s` is False. It does not enter the `if not has_w and not has_s` block. It reaches line 99. If `scorer_pending` is not True, it adds an error. Then it reaches line 102, adds another error about missing `untrimmed_start`, and continues. This is correct behavior (fail closed, report all issues).
        *   If a segment has `untrimmed_start` but no `trimmed_leading`, same logic applies.
        *   If a segment has neither, it enters the first block. If it has `scorer_pending`, it reports an error. If it doesn't, it continues.
    *   **Conclusion:** The logic is actually robust. It ensures that *any* segment that looks like it might be trimmed (has one of the keys) must have `scorer_pending: True`. And *any* segment that is not trimmed (has neither key) must *not* have `scorer_pending`. This is a strong invariant. No change needed.

**3. Test Coverage for `lineup_for` with `TRIMMED_PER_LINEUP_MAX`**
*   **File:** `tests/package/test_medley.py` (line 159-160)
*   **Scenario:** The test `test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin` verifies that `lineup_for` returns a lineup with exactly 1 trimmed clip. It does not explicitly test that `lineup_for` *refuses* to build a lineup with 2 trimmed clips if they were the only options (i.e., does it return `None` or an empty list?). The code in `package.py` (line 50-51) uses `continue` to skip invalid combos. If all combos are invalid, `lineup_for` will likely return `None` or an empty list depending on its implementation (not fully shown, but standard pattern). The test asserts `sum(...) == 1`, which implies it found a valid lineup. It doesn't prove it *rejects* a 2-trimmed lineup if that were the only candidate. However, `lineup_ok` is tested to reject 2 trimmed clips (line 158). Since `lineup_for` relies on `lineup_ok` (or similar logic), this is likely sufficient.

## Verification of Specific Checks

1.  **Trimmed clip sealed WITHOUT `scorer_pending: true`?**
    *   **No.** `package_pin.trim_problems` (line 99-101) explicitly checks `if s.get("scorer_pending") is not True` for any segment that has `trimmed_leading` or `untrimmed_start`. If missing or False, it adds an error, causing `PinRefused`.
    *   **No clip says pending when not trimmed?**
    *   **No.** `package_pin.trim_problems` (line 95-97) checks `if not has_w and not has_s:` and then `if "scorer_pending" in s:` adds an error. So untrimmed clips cannot have `scorer_pending`.

2.  **No line-up or pin can carry two trimmed clips?**
    *   **Line-up:** `package.lineup_ok` (line 41-42) checks `sum(bool(m.get("trimmed_leading")) for m in segs) > TRIMMED_PER_LINEUP_MAX`. `package.lineup_for` (line 50-51) checks the same condition for candidate combos. The no-voice path (line 59) also checks it.
    *   **Pin:** `package_pin.trim_problems` (line 89-92) checks `n > TRIMMED_PER_PIN_MAX`.
    *   **Constants:** `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` are both 1.

3.  **Pins without a trimmed clip seal exactly as before?**
    *   **Yes.** `SEALED_LATER` includes `scorer_pending`. The `to_pin` function (line 110) only includes `scorer_pending` in the segment dict if it is present in the source segment (`if k in s`). For untrimmed clips, `scorer_pending` is not present (enforced by `trim_problems`), so it is not added to the pin segment. The `seal` function hashes the segment dict. Since the dict is identical to the pre-change version for untrimmed clips (no new keys), the hash is identical. The test `test_the_pin_seals_the_trim_and_refuses_a_malformed_one` (line 173) asserts `self.assertNotIn("scorer_pending", pin["segments"][0])` for an untrimmed segment, confirming this.

4.  **Nothing claims the scorer affirmed anything?**
    *   **Correct.** The code sets `scorer_pending: True`. The `stand_alone_check` in `package.py` (implied by the test at line 135) records the label in `scorer_pending` and marks the row as "PENDING AT THE RENDER". It does not call the scorer. The scorer is only called at `stage_validate` in the render pipeline (outside this diff). The pin stage does not claim affirmation.

## SHIP: yes

The diff correctly implements Ruling 49. The fail-closed behavior is preserved for the strict mode. The sealing logic is robust, ensuring `scorer_pending` is present and true for trimmed clips and absent for untrimmed clips. The limit of 1 trimmed clip per lineup/pin is enforced across all relevant paths. The backward compatibility for untrimmed pins is maintained.