# gemma-4-31b-it (google/gemma-4-31b-it) 371 s finish=stop usage in 10320 / out 5349 usd_reported=0.000983 usd~0.111 (upper-bound price)

The code implements **RULING 119 (1)**, introducing a calibrated floor of **3.0** for the stand-alone clip scorer on the candidates path, restricted to a specific scorer SHA (`edd54964a5ab`), while maintaining the render's standard bar of **3.5**.

### Audit Findings

1.  **Floor Threshold & Scorer Restriction**: 
    *   In `package_pin.py` (lines 71-72), `STAND_ALONE_FLOOR` is correctly set to `3.0` and `STAND_ALONE_FLOOR_SCORER` to `"edd54964a5ab"`.
    *   In `package_pin.py` (line 91), the `on_floor` logic strictly requires the score to be $\ge 3.0$ AND the `scorer_sha` to start with the approved prefix.
    *   In `package.py` (line 18), the same restrictions are applied when identifying floor-affirmed verdicts.
    *   **Result**: Compliant. Nothing under 3.0 or from another scorer is affirmed.

2.  **Render Bar Integrity**:
    *   The render's standard bar (`SCORER_MIN = 3.5`) remains the primary check.
    *   In `package_pin.py` (line 93), the logic `(v["score"] >= SCORER_MIN or on_floor)` ensures that any clip meeting the 3.5 bar passes normally, while only those specifically marked as `calibrated` (and meeting the 3.0 floor) are granted the exception.
    *   **Result**: Compliant. The render's own bar is untouched; the floor is an additive exception for specific approved clips.

3.  **Seal and Marking**:
    *   `package.py` (lines 38-47) correctly identifies segments affirmed *only* on the floor and creates a `stand_alone_bar` mark.
    *   `package_pin.py` (line 102) adds `stand_alone_bar` to the pin dictionary.
    *   The test `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal` (lines 159-164) confirms that adding this mark does not change the `package_sha256`.
    *   **Result**: Compliant. The mark is carried outside the seal.

4.  **Test Validation**:
    *   `test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on` verifies the 3.0 threshold and the SHA restriction (ensuring other SHAs still require 3.5).
    *   `test_the_pin_check_accepts_a_floor_affirmation_only_whole` ensures that any mutation to the `bar`, `floor`, `score`, or `sha` results in a failure.
    *   **Result**: Compliant.

### Final Verification
- **Nothing < 3.0 affirmed?** Yes (`v["score"] >= 3.0`).
- **Nothing from other scorer affirmed?** Yes (`startswith("edd54964a5ab")`).
- **Render bar untouched?** Yes (3.5 still the default).
- **Mark outside seal?** Yes (verified by hash comparison in tests).

P1_OR_WORSE: 0