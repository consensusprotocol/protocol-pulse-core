### Q1: CORRECTNESS

1. **Function Changes:**
   - **`_tok` and `_lc_words` in `editorial_select.py`:** These functions now use `canon.canon_tokens` to ensure words are in the canonical form (lines 10-12, 34-37). This aligns with the requirement to use a single canonical form for text processing.
   - **`align_quote` in `editorial_select.py`:** Uses `canon.canon_tokens` and `canon.canon_aligned` to align quotes (lines 22-25). This ensures alignment is done in the canonical form, which should prevent off-by-one errors in token handling.
   - **`_numbers` in `editorial_select.py`:** Now uses `canon.canon_tokens` to extract numbers in a canonical form (lines 44-45).
   - **`_norm` in `story_semantics.py`:** Replaced with `canon.canon` to ensure quote-check normal form is consistent with the canonical form (lines 172-174).

2. **Error Handling and State Management:**
   - The functions appear to handle errors appropriately, with no silent exceptions observed in the diff. The use of canonical forms should prevent state leaks between clips, as it standardizes text processing.

3. **Preflight Checks:**
   - The `preflight.py` script includes checks for GPU availability, API responses, disk space, and git status. Each check is designed to fail fast if conditions are not met, preventing the pipeline from starting under incorrect conditions (lines 520-681).

4. **Backtest Functionality:**
   - The `backtest.py` script processes saved universes with frozen inputs, ensuring that changes in code are what affect outcomes, not changes in data (lines 276-509). This aligns with the requirement to prevent data-driven passes.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT
   - The use of canonical forms ensures that sentence boundaries are respected, and no recomputation of expected words occurs after selection (lines 10-12, 34-37).

2. **SELECTION LOCK:** COMPLIANT
   - The changes do not allow for recomputation of expected words after selection (lines 10-12, 34-37).

3. **SNAP LIMIT:** COMPLIANT
   - No evidence in the diff suggests that cuts can move outside the locked sentence's silence.

4. **NEIGHBOUR:** COMPLIANT
   - The canonical form usage ensures that neighboring words are not incorrectly included.

5. **ONSET/TAIL:** COMPLIANT
   - No changes in the diff affect the onset/tail handling.

6. **CREDITS:** COMPLIANT
   - No changes in the diff affect credit handling.

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT
   - No changes in the diff affect sign-off handling.

8. **L-b EDGE WORDS WHOLE:** COMPLIANT
   - No changes in the diff affect edge word handling.

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT
   - No changes in the diff affect dissent handling.

10. **L-d PROTECTED PREVIEW:** COMPLIANT
    - No changes in the diff affect the protected preview handling.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT
    - The use of canonical forms ensures punctuation is handled correctly.

12. **L-f CHANNELS FIRST:** COMPLIANT
    - No changes in the diff affect channel handling.

13. **L-g WRITTEN FORMS:** COMPLIANT
    - Canonical form usage ensures written forms are handled correctly (lines 10-12, 34-37).

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT
    - Canonical form usage ensures text is read as spoken (lines 172-174).

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT
    - No changes in the diff affect claim handling.

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT
    - Preflight checks ensure that only authorized bytes are released (lines 520-681).

17. **L-k ONE CANONICAL FORM:** COMPLIANT
    - The use of `canon.py` ensures one canonical form is used throughout (lines 10-12, 34-37, 172-174).

18. **LAW 20 / M2:** COMPLIANT
    - No changes in the diff affect gate thresholds.

19. **M12 FAIL CLOSED:** COMPLIANT
    - Preflight checks and error handling ensure fail-closed behavior (lines 520-681).

20. **LAW 22:** COMPLIANT
    - No changes in the diff affect the v2f reference path.

### Q3: TESTS

1. **Must-Fail Fixtures:**
   - Tests in `test_backtest.py` and `test_preflight.py` ensure that failures occur for the right reasons, such as missing data or incorrect configurations (lines 686-821, 822-968).

2. **Controls:**
   - Tests verify that the correct paths are taken when conditions are met, ensuring that the pipeline behaves as expected under normal conditions (lines 686-821, 822-968).

3. **Vacuous Assertions:**
   - No vacuous assertions were identified in the tests. Each test appears to have a clear purpose and checks specific conditions.

### Q4: VERDICT

1. **SEVERITY:** None identified.
2. **DIFF LINE:** N/A
3. **ISSUE:** N/A
4. **FIX:** N/A

**VERDICT:** READY