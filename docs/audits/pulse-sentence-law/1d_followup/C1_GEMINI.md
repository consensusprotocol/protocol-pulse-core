Excellent. I will now perform the requested code audit.

### Q1: CORRECTNESS

The changed functions appear to do what they're intended to do, and the logic seems correct and robust.

1.  **Refactoring of Eligibility Checks:** In `pipeline/select_passages.py`, the original `_eligible` function (lines 9-16) is refactored into `_budget`, `_conflicts`, and a new `_eligible` (lines 16-37). This is a good change for clarity and maintainability. The `_conflicts` function correctly centralizes all reasons a candidate passage might conflict with already `used` segments, including a new and important check for when a fallback from a previous slot has already claimed the window for a later slot (docstring line 21, implementation line 22).

2.  **Conflict Check for Top-Ranked Choice:** The logic on line 46 `(p is first and _conflicts(p, kind))` is a crucial correctness fix. It ensures that even the editor's primary choice for a slot is checked for conflicts. This correctly handles the edge case where a *previous* slot's fallback selection might have already used the time window of a *later* slot's primary selection.

3.  **Post-Cut Duration Check:** The new block on lines 54-59 introduces a vital check. It verifies that the duration of the *actual segment created from the locked words* (`seg["duration"]`) respects the budget (`lo`, `hi`), not just the pre-selection declared window duration (`p["duration"]`). This prevents a situation where a declared 12s window might only contain 9s of sentence-complete speech, which would then be incorrectly used as a "clip". The rejection is handled correctly by setting `seg = None`, which causes the loop to continue to the next candidate.

4.  **Fail-Closed Behavior (M12):** The code respects the M12 FAIL CLOSED law. When `_build_segment` fails (which it would for a boundary violation, as tested), it returns `None`. The loop correctly `continue`s on line 51. The new duration check also fails closed by nullifying the segment (`seg = None` on line 59) and allowing the `if seg is not None:` on line 60 to prevent its use. No new paths introduce silent exceptions or pass-on-failure behavior.

### Q2: LAW COMPLIANCE

The code appears to be compliant with all applicable laws.

*   **SENTENCE LAW:** **COMPLIANT.** While the diff doesn't show the implementation of the acoustic pause check, the new tests in `pipeline/test_sentence_windows.py` are explicitly designed to prove its existence and enforcement. The test data on line 160 includes a sentence gap of `0.05`s (< 80ms). The test on lines 236-244 verifies that a candidate clip (`bad`) ending at this illegal boundary is rejected for that specific reason (the `assertIn("OUT", rej["result"] ...)` on line 244). This demonstrates compliance.

*   **SELECTION LOCK:** **COMPLIANT.** The new logic on lines 54-59 operates on `seg`, which is the result of `_build_segment`. This is the point where words are locked. The check uses the duration of this locked segment, it does not recompute or change the selected words. The test on line 122 also confirms the `selection_lock` is created and matches the final segment words.

*   **SNAP LIMIT:** **COMPLIANT.** The test `test_rejected_clip_is_replaced_by_the_next_legal_window` proves this. The `bad` candidate window is rejected because there is "No legal boundary" in the gap (the pause is too short). The system then correctly falls back to another candidate rather than trying to move the cut point into the spoken part of the sentence.

*   **ONSET/TAIL:** **UNCERTAIN.** This diff does not touch rendering or audio processing code, only the selection logic. I cannot verify compliance or violation from the provided files.

*   **CREDITS:** **UNCERTAIN.** This diff does not touch any code related to credit generation or avatar handling. I cannot verify compliance or violation.

*   **LAW 20 / M2:** **COMPLIANT.** The new duration check on lines 55-59 is a hard gate with a clear rejection. It correctly causes a fallback to the next candidate. No thresholds have been loosened; a new, stricter gate has been added.

*   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, failures (boundary not found, duration out of budget) lead to rejection of the candidate segment, not a pass.

*   **LAW 22:** **UNCERTAIN.** This diff does not touch code related to the `v2f` reference render. I cannot verify compliance or violation.

### Q3: TESTS

The new and modified tests are excellent and directly prove the claims.

1.  **`test_fresh.py`:** The update to generate more realistic test data (12 words per sentence, line 73) and the correct handling of source window offsets (`win_off`, line 83) makes the test suite more robust and less likely to have false positives related to coordinate systems.

2.  **`test_sentence_windows.py`:** This file contains the most critical new tests, which are very well-designed.
    *   **`test_rejected_clip_is_replaced...`:** This test (line 235) successfully proves the primary fix. It creates a "must-fail" scenario with a missing inter-sentence pause (line 160), asserts that the clip is rejected for the correct boundary-related reason (line 244), and confirms that the system correctly falls back to a legally-bounded alternative (line 242). It also correctly asserts that a candidate that is too short is never even considered (line 247), proving the pre-filtering works.
    *   **`test_a_window_taken_by_a_fallback...`:** This test (line 249) proves the correctness of the new conflict-checking logic from line 46. It creates a scenario where a fallback takes a window that was the primary choice for a later slot and asserts that the window is not used twice. This is a very good test of a subtle but important edge case.
    *   **`test_budget_holds_for_the_locked_words...`:** This test (line 258) directly and successfully validates the new duration check added on lines 54-59 of `select_passages.py`. It creates a "liar" candidate whose declared duration fits the budget but whose actual sentence-based content does not, and it correctly asserts that this candidate is rejected for that specific reason (line 267).

The tests are not vacuous and provide strong evidence that the bugs are fixed and the laws are being followed.

### Q4: VERDICT

No defects found. The changes are correct, well-tested, and compliant with the specified laws. The code improves robustness by adding checks for critical edge cases (conflicts, mismatch between declared and actual duration) that were likely the source of the reported editorial errors.

**READY**