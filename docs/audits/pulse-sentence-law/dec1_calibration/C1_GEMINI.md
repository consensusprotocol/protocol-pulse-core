Excellent. I will now perform a detailed code audit as one of the three independent AI models.

---

### Q1: CORRECTNESS

The changed functions appear to correctly implement their stated goals, with a few caveats regarding scope.

1.  **`run_fresh.py`:**
    *   **`stage_gates`:** The change on lines 13-16 correctly identifies and fixes a bug where `source_clips` were not being passed to `run_gates` for the G8 sharpness check. The comment on lines 11-12 accurately describes that G8 was previously failing with a "no_source" error and being waived. This change correctly wires the necessary source files (`final_*.mp4` for 16:9 and `vert_*.mp4` for 9:16) into the gate runner, enabling the source-relative sharpness check to function as intended.
    *   The removal of special-casing logic for G8 and G9 (lines 24-31, 41-48) and replacement with simple status reporting (lines 33, 50) is correct *in the context of the gates themselves being recalibrated*. This simplifies the orchestration script, pushing the pass/fail logic entirely into the gates where it belongs.

2.  **`qa_gates.py`:**
    *   **Parameter Passing:** The addition of a `fmt` parameter to `gate_g3c`, `gate_g8`, and `gate_g9` (and its propagation from `run_all_gates`) is correctly implemented. This allows these gates to look up format-specific thresholds from the new constant dictionaries (e.g., line 231, 261, 279). The use of `.get(fmt, default_value)` is a robust way to handle this, preventing `KeyError` exceptions.
    *   **G8 Soft Source Logic:** The new logic on lines 240-244 introduces a specific rule ("DEC-3") for "soft sources." It correctly implements the described logic: if a source file's sharpness is already below the absolute floor, the gate should only check for relative degradation (`degrad_ok`) and not fail on the absolute floor (`floor_ok`). This is a deliberate change to the gate's success criteria.
    *   **Thresholds:** The core logic of the gates `gate_g5`, `gate_g8`, `gate_g9`, and `gate_g3c` correctly uses the new, format-specific constants for their comparisons (e.g., line 204, 231, 261, 279).

3.  **Fail-Closed (M12):** I see no new paths that would violate the M12 FAIL CLOSED law. In `gate_g5`, if `true_peak` is `None`, the check correctly results in `tp_ok` being `False`. The logic changes in `gate_g8` are explicit rule changes, not pathways for missing data to cause a pass. The overall structure remains fail-closed.

**Caveat:** The feature name is `pulse-sentence-law` and the description mentions fixing clipped words (D1) and mid-sentence cuts (D2/D3). However, **this diff contains no changes to `pipeline/sentence_law.py` or any other logic that would implement or fix the SENTENCE LAW itself.** The changes are exclusively focused on re-calibrating existing gates (G3c, G5, G8, G9) and fixing the input to G8. While G3c (acoustic tail) is related to sentence boundaries, it is not the full implementation of Sentence Law. This diff does not address D1, D2, or D3 as described by the Sentence Law.

---

### Q2: LAW COMPLIANCE

*   **SENTENCE LAW:** **VIOLATION.** The diff does not contain any code to implement or enforce this law. The feature's purpose states it will catch clips starting/ending mid-sentence, but no such logic is present in this change.
*   **SELECTION LOCK:** **UNCERTAIN.** No code related to selection or re-computation of words is present in the diff. I cannot verify compliance or violation.
*   **SNAP LIMIT:** **UNCERTAIN.** No code related to moving cuts is present in the diff. I cannot verify compliance or violation.
*   **ONSET/TAIL:** **VIOLATION.** The diff does not contain code to check for the >= 80 ms of sub-speech audio or the >= 85% word duration. This law is not addressed.
*   **CREDITS:** **VIOLATION.** The diff does not contain code to address warped avatars (D4).
*   **LAW 20 / M2:** **PARTIAL.**
    *   The law states "gate thresholds are constants" and "never change what a check accepts to make a render pass". Lines 190-193 in `qa_gates.py` explicitly change the constant thresholds for four gates.
    *   **However, this is a justified, documented, and tested re-calibration**, not an ad-hoc waiver. The comments (lines 184-189) explain that this is a one-time "DEC-1" decision to align the thresholds with an approved reference asset (`v2f_2026-11-06`), making that asset the new definition of "passing."
    *   Furthermore, the changes in `run_fresh.py` (removing lines 24-31 and 41-48) **strengthen** compliance by removing previous logic that effectively re-classified failing gates as "FLAGS" or "APPROVED KNOWN EXCEPTIONS". The new system is a stricter "hard stop".
    *   Therefore, while the constants were changed, it was done to establish a new, stricter baseline, not to pass a failing render.
*   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, I find no violations of this law in the diff.
*   **LAW 22:** **COMPLIANT.** This diff does not change any rendering code, so the `v2f` reference will continue to re-render byte-identically. The new tests (`pipeline/test_dec1_calibration.py`) are built entirely around using this frozen reference as the ground truth for QA, which is in the spirit of this law.
*   **Smallest diff:** **COMPLIANT.** The changes are focused and directly related to the problem of gate calibration and wiring.

---

### Q3: TESTS

The new test file `pipeline/test_dec1_calibration.py` is robust and effectively proves the claims related to gate calibration.

*   **Proving the Claim:** The tests prove that the new constants are derived from the reference video and that these new constants work correctly. `test_constants_are_the_reference_measurements` (line 118) acts as a static check, ensuring the hardcoded values match the expected measurements from the reference.
*   **Control Case:** `test_reference_passes_every_calibrated_gate` (line 125) is the critical "control" test. It correctly asserts that the approved `v2f` reference now PASSES all four recalibrated gates. This proves the calibration was successful.
*   **Failure Case:** The four `test_g*_just_beyond_fails` tests are excellent. They don't just test failure, they test failure *at the new boundary*.
    *   `test_g3c_just_beyond_fails` (line 134) correctly isolates a segment and modifies its audio to narrowly fail the new valley depth threshold.
    *   `test_g5_just_beyond_fails` (line 145) correctly boosts volume to narrowly fail the new true peak threshold for the 9x16 format.
    *   `test_g8_just_beyond_fails` (line 153) correctly applies a subtle blur to narrowly fail the new sharpness floor.
    *   `test_g9_just_beyond_fails` (line 165) correctly applies a subtle brightness reduction to narrowly fail the new luma floor.
*   **No Vacuous Passes:** The assertions are specific and check for the exact expected outcome (e.g., `self.assertFalse(next(r for r in table if r["segment"] == "hook")["pass"])` on line 143). They cannot pass vacuously.

**Conclusion on Tests:** The tests are high quality and successfully validate the gate calibration changes. They do **not**, however, provide any test coverage for the missing Sentence Law, Onset/Tail, or Credits features.

---

### Q4: VERDICT

This diff is a high-quality, well-tested fix for a specific subset of the problems described (gate calibration and G8 wiring). However, it critically fails to deliver the headline feature (`pulse-sentence-law`) and other fixes mentioned in the problem description.

| SEVERITY | DIFF LINE | ISSUE | FIX |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | N/A | **Missing Feature Implementation:** The diff does not contain any code to implement the `SENTENCE LAW`, `ONSET/TAIL` law, or fix the `CREDITS` issue, despite being named `pulse-sentence-law` and the description covering these defects (D1, D2, D3, D4). | The code implementing these laws and fixes must be included in the commit. The feature description and name are completely misaligned with the diff's content. |
| **MEDIUM** | `qa_gates.py:240-244` | **Undocumented Rule Change in Description:** The diff introduces a new rule, "DEC-3," for handling soft sources in `gate_g8`. While documented in a code comment, this significant change to the gate's logic is not mentioned in the overarching feature description, which could be misleading to reviewers. | The feature description should be updated to include the DEC-3 rule change for G8 sharpness to provide full context for the code changes. |
| **LOW** | `qa_gates.py:190-193` | **Apparent Violation of Law 20:** The diff modifies gate thresholds that are marked with "Law 20 — do not change". While this is a well-justified and documented calibration, it creates a contradiction with the prior strict interpretation of the law. | The "do not change" comments for these specific constants should be updated or removed to reflect that they are now subject to periodic, principled re-calibration against approved reference assets, as established by DEC-1. |

**NOT READY**