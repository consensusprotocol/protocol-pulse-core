### Q1: CORRECTNESS
As the provided diff contains no application logic changes, I can only assess the correctness of the new test suite, `pipeline/test_pulse_20261110_mustfail.py`. The suite is well-designed and appears correct in its approach.

-   The test fixture setup in `_G16Fixture.setUpClass` (diff lines 100-124) is correct. It correctly recreates the conditions of the original run by programmatically generating the `selection_lock` (lines 113-114) from the editor's original selection (`B3_chosen.json`). This is crucial for correctly testing for violations against the SELECTION LOCK law, as it establishes the ground truth against which the faulty cuts are measured.
-   The test for the download window offset (`TestWindowOffset`, lines 186-205) correctly uses mocking to intercept the `subprocess.run` call. It then parses the requested download section from the command-line arguments and compares it to the function's returned offset. Using `assertAlmostEqual` (line 202) is the correct way to handle potential floating-point inaccuracies.
-   The tests correctly use a cached, non-live model adjudicator (`allow_model=False`, line 118), which upholds the `M12 FAIL CLOSED` law: if an adjudication is not in the pre-approved cache, the test will fail rather than attempting a new, non-deterministic adjudication.

The test functions do what their names and the file's docstring claim. I can't see how a pass could be produced on missing data; the design seems to ensure failure in such cases.

### Q2: LAW COMPLIANCE
The new test suite is explicitly designed to enforce the Governing Laws by failing on code that violates them. While I cannot see the fixed code, the tests themselves are fully compliant with the spirit and letter of the laws.

-   **SENTENCE LAW:** COMPLIANT. `TestD2Clip01Out` and `TestD3Edges` (lines 146-163) contain assertions that are designed to fail if cuts start or end mid-sentence, directly enforcing this law.
-   **SELECTION LOCK:** COMPLIANT. This law is a primary focus. `TestTautology.test_recomputed_expected_words_fail_the_lock` (line 166) specifically checks that the gate fails if it recomputes expected words instead of using the sealed lock. Furthermore, `TestTautology.test_run_fresh_has_no_recompute_sync_or_wide_snap` (line 173) asserts that the functions which previously performed this re-computation have been physically removed from the codebase.
-   **SNAP LIMIT:** COMPLIANT. The aforementioned test asserting the removal of `_snap_candidates` (line 176) suggests that an overly permissive snapping mechanism has been removed, which is a core part of enforcing this law.
-   **ONSET/TAIL:** COMPLIANT. `TestD1HookOnset.test_g16_in_fails_without_lead_in_pad` (line 137) contains a specific assertion to check that the `genuine_lead_ms` is below the 80ms threshold (line 140), directly testing a requirement of this law.
-   **CREDITS:** COMPLIANT. `TestD4Credits` (lines 207-240) is a robust enforcement of this law. It confirms that the old, warped avatars fail the gates (line 217), a known-good reference passes them (line 224), the system explicitly rejects non-square avatar images (line 232), and that old fallback logic has been removed from the source (lines 238-239).
-   **LAW 20 / M2 (Hard Stop):** COMPLIANT. The entire premise of this "must-fail" test suite is to turn previously silent failures into hard gate failures, which is the essence of this law.
-   **M12 FAIL CLOSED:** COMPLIANT. As noted in Q1, the use of a fixed adjudication cache with `allow_model=False` (line 118) enforces this principle.
-   **LAW 22 (v2f Reference):** COMPLIANT. `test_v2f_finals_pass_g15_and_g12` (line 224) acts as a regression test, ensuring that the new, stricter gates do not accidentally fail the frozen reference render.

### Q3: TESTS
The quality of the tests in `pipeline/test_pulse_20261110_mustfail.py` is excellent. They convincingly prove the claims of the feature.

-   The tests are structured to fail on the current codebase for exactly the reasons outlined in the file's docstring (lines 53-66). For example, `test_g16_in_fails_without_lead_in_pad` (line 137) not only asserts the gate fails but also asserts *why* it fails (`assertLess(r["genuine_lead_ms"], 80)`).
-   The suite includes critical "control" tests that must pass, such as `test_d3c_clip02_out_control_passes` (line 160) and `test_v2f_finals_pass_g15_and_g12` (line 224). These ensure that the eventual fix is not overly aggressive and does not break previously working cases.
-   The tests do not appear to have any assertions that could pass vacuously. They check specific boolean return values, numeric comparisons, and even the content of error messages.
-   A particularly strong and non-vacuous testing pattern is used in lines 173-178 and 235-240, where `inspect.getsource` is used to assert that specific buggy functions and fallback logic have been completely removed from the source code. This is a powerful way to prevent regression.

### Q4: VERDICT
The diff consists of a new gospel file, audit configuration, and a comprehensive "must-fail" test suite. The test suite is exceptionally well-written. It precisely captures the user-reported defects as failing test cases, includes control cases to prevent over-correction, and even asserts that old, problematic code patterns have been removed. This represents a textbook application of Test-Driven Development (TDD). While I have not seen the implementation of the fixes, this commit provides the exact contract that the fixes must fulfill. There are no defects in this diff.

**VERDICT: READY**