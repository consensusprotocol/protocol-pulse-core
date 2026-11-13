# qwen3.8-27b (qwen/qwen3.8-27b) 35 s finish=stop usage in 6649 / out 1192 usd~0.038 (upper-bound price)

# Audit: pp-selectid-0855 (C1_STEP.diff)

## Verification of the Core Logic

I verified the new `placement()` logic against the stated `lineup_for`/`lineup_ok` rules. The mapping is **correct**:

1.  **Short Clip + Can Open** (`duration < 8s`, `hook.ok` & `hook_onset.pass`):
    *   **New Code:** Returns `" | under 8 s: only the hook or the LAST clip"`.
    *   **Rule Check:** `lineup_for` allows a short clip to be the hook (index 0) or the last clip (index -1). It forbids it in the middle (`order[:-1]` check). The prompt text accurately reflects this.
2.  **Short Clip + Cannot Open** (`duration < 8s`, `!hook.ok` or `!hook_onset.pass`):
    *   **New Code:** Returns `" | under 8 s: only the LAST clip"`.
    *   **Rule Check:** Since it cannot be the hook, the only valid position for a short clip is the last one. The prompt text accurately reflects this.
3.  **Long Clip + Cannot Open** (`duration >= 8s`, `!hook.ok` or `!hook_onset.pass`):
    *   **New Code:** Returns `" | cannot open (never the hook)"`.
    *   **Rule Check:** Long clips have no "last only" restriction, but they still cannot be the hook if ineligible. The prompt text accurately reflects this.
4.  **Long Clip + Can Open** (`duration >= 8s`, `hook.ok` & `hook_onset.pass`):
    *   **New Code:** Returns `""` (empty).
    *   **Rule Check:** No restrictions. Correct.

The prompt sentence in `package.py` (lines 12-14 of the diff) correctly enumerates these three states and their allowed positions.

## Findings

### P1: Missing Test Case for "Short Clip + Can Open" in Prompt Context
**File:** `tests/package/test_medley.py` (lines 51-58 of diff)
**Scenario:** The test verifies that `placement()` returns the correct string for a short clip that *can* open (`short_opener`). However, the test at line 51 (`self.assertIn('id=s | C | 6.9 s | under 8 s: only the LAST clip | "', p)`) only checks the case where the short clip *cannot* open (because `no_hook={"s", "y"}` in the `Rig` setup).
While the unit test for `placement()` itself (line 58) covers the "can open" case, the **prompt generation** test does not verify that the prompt correctly renders the "only the hook or the LAST clip" string for a short clip that *is* eligible to open.
**Risk:** Low. The logic is simple string interpolation. However, a regression where the prompt fails to include the "hook" option for eligible short clips would not be caught by the current prompt assertion.
**Recommendation:** Add a test case where a short clip is eligible to open, and assert that the prompt contains `"under 8 s: only the hook or the LAST clip"`.

### P2: Ambiguity in "LAST clip" vs "LAST id of an angle's list"
**File:** `pipeline/package.py` (lines 12-14 of diff)
**Scenario:** The prompt says: `a clip marked "only the hook or the LAST clip" is the first or the LAST id of an angle's list`.
The term "LAST clip" in the marking is slightly ambiguous. Does it mean "the last clip in the *entire* video" or "the last clip in the *angle's* list"?
The prompt clarifies this by saying "is the first or the LAST id of an angle's list". This is correct because `lineup_for` operates on the angle's list. However, the marking itself (`"only the hook or the LAST clip"`) could be misinterpreted by the LLM as "the last clip in the final video output" if the LLM is not careful.
**Risk:** Very Low. The prompt explicitly defines the meaning of the marking. The LLM is instructed to follow the prompt's definition.
**Recommendation:** No change needed, but ensure the LLM prompt is robust to this ambiguity. The current prompt is clear enough.

### P2: No Change to `lineup_for` or `lineup_ok`
**File:** `pipeline/package.py`
**Scenario:** The diff only changes `placement()` and the prompt. It does not change `lineup_for` or `lineup_ok`.
**Verification:** This is correct. The defect was that `placement()` did not match `lineup_for`'s rules. The fix is to make `placement()` match `lineup_for`, not to change `lineup_for`.
**Risk:** None.

## SHIP: yes with conditions

**Condition:** Add a test case to `tests/package/test_medley.py` that verifies the prompt contains `"under 8 s: only the hook or the LAST clip"` for a short clip that is eligible to open. This will ensure that the prompt correctly communicates the hook exception to the LLM.

The core logic is correct, and the fix addresses the measured defect. The missing test case is a minor gap in test coverage, not a functional bug.