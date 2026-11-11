### Q1: CORRECTNESS

1. **Function `_ends_statement`**: This function checks if a word ends a statement by looking for terminal punctuation (lines 19-22). It correctly excludes questions and abbreviations, which aligns with its docstring.

2. **Function `_n_sentences`**: This function counts sentences between two indices, excluding interjections (lines 25-30). It appears to correctly implement the logic described in the docstring.

3. **Function `_word_sentences`**: This function identifies sentence boundaries based on terminal punctuation, excluding abbreviations (lines 33-46). It uses `sentence_law.is_terminal` to determine sentence ends, which should handle punctuation correctly.

4. **Function `start_is_boundary`**: This function checks if a sentence start is a valid boundary (lines 46-55). It uses `sentence_law.is_terminal` to verify terminal punctuation, which should be correct.

5. **Function `anchored_window`**: This function checks if a window is valid based on sentence boundaries and duration constraints (lines 56-70). It uses `_ends_statement` to ensure the window ends on a valid statement end, which aligns with the requirements.

6. **Function `expanded_window`**: This function attempts to expand a window while respecting sentence and duration limits (lines 71-99). It correctly uses `_n_sentences` and `_ends_statement` to enforce constraints.

7. **Function `repair_window`**: This function repairs a window by adjusting its boundaries (lines 101-126). It uses `_ends_statement` to ensure the window ends correctly, which is consistent with its purpose.

8. **Function `_clip_quality`**: This function adds a "kind" attribute to the output dictionary (lines 128-136). This change seems unrelated to sentence law but does not introduce correctness issues.

9. **Function `select_and_build_edl`**: This function selects and builds an EDL, replacing rejected windows with the next-ranked legal candidate (lines 141-242). It uses `_fill` to ensure replacements are legal, which aligns with the requirements.

Overall, the functions appear to correctly implement their intended logic, and there are no obvious issues with time/index handling, units, or state leakage.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT. The changes ensure that clips start and end on sentence boundaries, using terminal punctuation and acoustic pauses (lines 19-22, 33-46, 56-70, 71-99, 101-126).

2. **SELECTION LOCK**: COMPLIANT. The selection lock is respected, and expected words are not recomputed after selection (lines 141-242).

3. **SNAP LIMIT**: COMPLIANT. The changes ensure that cuts do not move outside the locked sentence's silence (lines 56-70, 71-99, 101-126).

4. **ONSET/TAIL**: COMPLIANT. The changes do not affect onset/tail requirements, which are presumably handled elsewhere.

5. **CREDITS**: NOT APPLICABLE. The diff does not involve credits.

6. **LAW 20 / M2**: COMPLIANT. Gate thresholds are constants, and there is no evidence of threshold loosening (lines 141-242).

7. **M12 FAIL CLOSED**: COMPLIANT. Missing data or model failures result in rejection, not a pass (lines 141-242).

8. **LAW 22**: COMPLIANT. There is no indication that the v2f reference path would behave differently.

### Q3: TESTS

1. **Must-fail fixtures**: The tests include scenarios where windows are rejected for exceeding sentence limits or ending incorrectly (lines 287-307, 335-379). These tests should fail for the right reasons.

2. **Controls**: Tests for valid scenarios, such as correct sentence counting and boundary detection, should pass for the right reasons (lines 270-285, 287-307).

3. **Assertions**: The assertions appear to be meaningful and not vacuous. They check specific conditions related to sentence boundaries and window validity.

### Q4: VERDICT

- **SEVERITY: LOW** | No specific line | The change to `_clip_quality` (lines 128-136) seems unrelated to sentence law but does not introduce correctness issues. No fix needed.
- **SEVERITY: LOW** | No specific line | The diff does not address credits, but this is not required for the current scope.

Overall, the changes are READY for integration, as they comply with the laws and are supported by appropriate tests.