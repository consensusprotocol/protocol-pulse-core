# qwen3.8-27b (qwen/qwen3.8-27b) 44 s finish=stop usage in 6479 / out 1573 usd~0.043 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0855

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the logic mapping and the boundary semantics, but I missed two specific nuances that the other models highlighted:

1.  **Qwen’s P1 (Missing Prompt-Level Test for "Can Open" Short Clip):** I noted that the test at `test_medley.py:57-62` exercised the `lineup_for` logic for the "can open" case, but I failed to explicitly flag that the *prompt string assertion* for the "can open" short clip was missing in the initial diff. I assumed the `lineup_for` test was sufficient, but Qwen correctly identified that the *prompt rendering* of that specific string ("only the hook or the LAST clip") needed its own assertion to prevent regression in the text generation itself.
2.  **GLM’s Nuance on "Nothing Else Changed":** I verified the logic but didn't explicitly trace the prompt text re-wrapping to confirm no accidental loss of the `; for` continuation. GLM explicitly verified that the stray `; for` continuation was preserved across the rewrap, which is a critical detail for prompt integrity.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (SHIP: yes, no findings):** I **agree** with the final verdict but **disagree** with the lack of findings. Grok missed the test coverage gap (Qwen's P1) and the prompt re-wrapping verification (GLM's point). Grok's "no P2" is too lenient given the ambiguity in "LAST clip" (Qwen's P2) and the lack of a negative test case for mid-lineup rejection (GLM's P2).
*   **GLM (SHIP: yes, P2s):** I **agree** with GLM's P2s. The `:.0f` rounding issue is a pre-existing pattern, not a new defect, so P2 is appropriate. The lack of a negative test (short clip mid-lineup failing) is a valid P2 because the enforcement logic (`lineup_for`) wasn't changed, so the existing tests cover it, but the *new* test doesn't explicitly prove the "never in between" constraint is enforced by the *new* marking.
*   **Qwen (SHIP: yes with conditions, P1):** I **agree** with Qwen's P1. The prompt-level test for the "can open" short clip is a genuine gap. The logic is correct, but the test suite should verify that the *prompt* actually contains the new string for that case. The condition to add this test is reasonable.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2: Ambiguity in "LAST clip" scope (Re-confirmed from Qwen)**
*   **File:** `pipeline/package.py` (lines 12-14 of diff)
*   **Scenario:** The prompt says `a clip marked "only the hook or the LAST clip" is the first or the LAST id of an angle's list`. The term "LAST clip" in the marking itself (`"only the hook or the LAST clip"`) could be misinterpreted by the LLM as "the last clip in the final video output" rather than "the last clip in the angle's list".
*   **Risk:** Very Low. The prompt explicitly defines the meaning. However, the marking string itself is slightly ambiguous without the prompt's clarification.
*   **Recommendation:** No change needed, but ensure the LLM prompt is robust to this ambiguity. The current prompt is clear enough.

**P2: No Negative Test for Mid-Lineup Rejection (Re-confirmed from GLM)**
*   **File:** `tests/package/test_medley.py` (lines 57-62 of diff)
*   **Scenario:** The test proves that a short clip *can* be the hook and *can* be last. It does not prove that a short clip *cannot* be mid-lineup.
*   **Risk:** Low. The enforcement logic (`lineup_for`) was not changed, so the existing tests cover the rejection. However, the new test doesn't explicitly verify that the *new* marking's "never in between" claim is enforced.
*   **Recommendation:** Add a test case where a short clip is mid-lineup and assert that `lineup_for` rejects it. This would make the test suite more robust.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Logic Correctness** | 9/10 | 10/10 | Verified against `lineup_for` rules. The hook exception is correctly handled. |
| **Test Coverage** | 7/10 | 8/10 | Qwen's P1 identified a gap in prompt-level testing for the "can open" case. The new test in the diff (line 57) actually *does* include the prompt assertion for the "can open" case (`id=o | F | 7.3 s | under 8 s: only the hook or the LAST clip | "`), so the gap is **closed** in the provided diff. I initially missed this in Cycle 1. |
| **Prompt Clarity** | 8/10 | 9/10 | The prompt sentence is clear, but the "LAST clip" ambiguity remains a minor P2. |
| **Code Quality** | 9/10 | 9/10 | No changes. The `:.0f` rounding is a pre-existing pattern. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None. (Qwen's P1 is resolved in the provided diff: line 57 asserts the prompt contains the "can open" string).
*   **P2 MEDIUM:**
    1.  **Ambiguity in "LAST clip" scope:** `pipeline/package.py` (lines 12-14). The marking string is slightly ambiguous without the prompt's clarification.
    2.  **No Negative Test for Mid-Lineup Rejection:** `tests/package/test_medley.py` (lines 57-62). The test doesn't explicitly verify that a short clip mid-lineup is rejected by `lineup_for`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The most important change is the correction of `placement()` to accurately reflect `lineup_for`'s rules, specifically the hook exception for short clips. This directly addresses the measured defect where the writer was told a short clip "may only play LAST" when it could actually be the hook.

## 7. PRODUCTION READY?

**Yes.**

The logic is correct, the tests cover the critical cases (including the 08:46 shape), and the prompt is clear. The P2s are minor and do not block shipping. The condition from Qwen (add a prompt-level test for the "can open" case) is already met in the provided diff (line 57).