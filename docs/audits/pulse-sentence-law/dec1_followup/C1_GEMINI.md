Excellent. I will now perform the requested code audit.

---

## PULSE CHECK: CODE AUDIT

**Model:** Gemini 2.5 Pro
**Feature:** `pulse-sentence-law`
**Branch:** `combo-letterbox-quoteonly-v2`
**Commit:** `179e56a7` (inferred from diff)

### Q1: CORRECTNESS

The functions modified and added in this diff appear to be correct *for what they do*.

1.  **`tail_rows(g9_pass, conform_fallback)` (lines 9-13):** This new function correctly implements the logic described in its docstring. It separates the result of the `G9_tail` luma gate from a new, distinct check `outro_locked`. It returns "PASS" or "FAIL" strings in a dictionary as expected. The logic is straightforward and does not appear to have off-by-one errors, state leakage, or pathways for silent exceptions.
2.  **`stage_gates` modification (line 25):** The replacement of the inline boolean expression with a call to `tail_rows` is correct. It properly passes the `g9_pass` result and the `fallback` boolean to the new function, and `dict.update()` correctly merges the returned dictionary into the `rows[fmt]` dictionary.

However, a significant point of concern is the disconnect between the feature's name/purpose (`pulse-sentence-law`) and the code presented. The diff shows **no changes related to sentence boundary detection, onset/tail audio, or transcript analysis.** The changes are exclusively focused on refactoring the `G9_tail` (luma check on outro) gate logic. This diff, in isolation, does not implement the SENTENCE LAW or fix the documented defects D1, D2, D3, D4, or D5. It may be related to D6 (abrupt channel changes) if an outro is considered a type of channel change, but this is an inference.

Regarding **M12 FAIL CLOSED**, the change actually strengthens this principle. The previous logic on line 24 (`res["G9_tail"]["pass"] and (identical or not fallback)`) could have allowed a non-identical, non-fallback outro to pass the `G9_tail` gate. The new logic (lines 9-13, 25) creates a separate failure row (`outro_locked: FAIL`) if a fallback is used, regardless of whether its luma passes. This closes a potential loophole and makes the gate stricter.

### Q2: LAW COMPLIANCE

Based strictly on the provided diff:

-   **SENTENCE LAW:** **UNVERIFIABLE.** The diff does not contain any code that implements or modifies sentence boundary detection, acoustic pause measurement, or transcript adjudication.
-   **SELECTION LOCK:** **UNVERIFIABLE.** The diff does not touch code related to clip selection or the `selection_lock` in `edl.json`.
-   **SNAP LIMIT:** **UNVERIFIABLE.** The diff does not contain code related to moving cut points.
-   **ONSET/TAIL:** **UNVERIFIABLE.** The diff does not contain code related to audio padding or word duration checks.
-   **CREDITS:** **UNVERIFIABLE.** The diff does not contain code related to avatar rendering or selection.
-   **LAW 20 / M2 (Constant thresholds, hard stop):** **COMPLIANT.** The change makes the gate *stricter* by creating a new, explicit failure condition (`outro_locked`) for using a fallback outro. It does not loosen any thresholds. The test on line 48 confirms the `G9_LUMA_FLOOR` constant is still the point of comparison. The new `outro_locked: FAIL` condition, which leads to a `VERDICT_HOLD` (line 58), correctly implements a hard stop for a condition that was previously coupled with the luma check.
-   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, this change improves adherence to M12 by failing closed on any fallback outro, even if it happens to pass the luma check. See line 57, where `tail_rows(True, True)` results in a `FAIL` for `outro_locked`.
-   **LAW 22 (v2f reference):** **COMPLIANT.** The diff does not change the rendering path for the frozen reference. The test modifications in `test_dec1_calibration.py` (lines 45-48) make the validation against the reference *more robust*, not different.
-   **Other Laws (Smallest diff, etc.):** **COMPLIANT.** The diff is small and focused on its specific task of refactoring the G9 gate.

### Q3: TESTS

The tests added and modified are of high quality for the code they are intended to cover.

1.  **`TestDec1` modification (lines 45-48):** The change from a single, weak assertion (`self.assertFalse(d["luma_ok"] in (True, "True"), d)`) to three specific assertions is a significant improvement. The new tests verify that the gate's overall status is `False`, the specific `luma_ok` key is `'False'`, and crucially, that the measured `mean_luma` was indeed less than the threshold. This proves the gate is failing for the correct reason and is not a vacuous pass.
2.  **`TestTailRows` (lines 51-64):** This new test class is excellent. It directly targets the new `tail_rows` function and its integration into the verdict system.
    -   `test_luma_pass_on_a_fallback_outro_fails_outro_locked` (lines 55-58) correctly proves the core claim of the "Heimdall DEC-1 audit": that a fallback outro is a failure condition (`outro_locked: FAIL`) leading to a `VERDICT_HOLD`, even if it passes the luma check (`G9_tail: PASS`).
    -   `test_rows_follow_their_own_inputs` (lines 60-64) correctly validates the other logical paths, ensuring the function behaves as expected in passing and other failing scenarios.

The tests successfully prove the correctness of the G9 gate logic refactor. However, **they do not prove that the overall feature goals have been met.** There are no tests shown that would fail on the `pulse_20261110` fixtures for clipped words, mid-sentence cuts, warped avatars, or letterboxing. The tests validate the code in the diff, but the code in the diff does not appear to address the primary problem description.

### Q4: VERDICT

| SEVERITY | DIFF LINE | ISSUE | FIX |
| :--- | :--- | :--- | :--- |
| **MAJOR** | 1-68 | **Scope Mismatch.** The diff exclusively contains a refactor of the `G9_tail` (outro luma) gate. It presents no code related to the feature's primary purpose: implementing SENTENCE LAW or fixing defects D1-D5 (clipped words, mid-sentence cuts, warped avatars, letterboxing). The audit cannot verify the core claims of the feature. | The full set of changes implementing the SENTENCE LAW and fixing the documented defects must be provided for review. Alternatively, the feature description must be revised to reflect that this commit is only a prerequisite or a fix for the G9 gate logic. |
| MINOR | 45 | **Test Weakness (Now Fixed).** The previous assertion was weak and could pass if `luma_ok` was `None` or `0`. | The change to more specific assertions on lines 46-48 is the correct fix and has been implemented well. This is a positive change, not a remaining defect. |

**Conclusion:**

The code changes within this diff are correct, well-tested, and improve the strictness and clarity of the `G9_tail` gate, in compliance with M12 and M2.

However, there is a critical disconnect between the code provided and the stated purpose of the `pulse-sentence-law` feature. I cannot verify compliance with SENTENCE LAW, ONSET/TAIL, CREDITS, or any of the fixes for defects D1 through D5, as no relevant code has been provided. The quality gate's purpose is to ensure the feature does what it claims; based on this diff, I cannot make that determination.

**NOT READY**