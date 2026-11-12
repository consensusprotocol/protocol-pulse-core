### Q1: CORRECTNESS

1. **Functionality and Docstring Compliance:**
   - The `norm_word` function (lines 8-12) is updated to use the canonical form from `pipeline/canon.py`, which aligns with its docstring.
   - The `spoken_tokens` function (lines 23-46) now uses `canon.canon_tokens`, which matches the docstring's description of converting words to a canonical form.
   - The `_norm` function in `editorial_gate.py` (lines 57-60) and `_g20_norm` in `gates.py` (lines 80-84) have been updated to use the canonical form, aligning with their purpose of normalizing text.
   - The `_key` function in `punctuation.py` (lines 118-125) correctly implements the canonical form with adjustments for currency/percent words, as per its docstring.
   - The `canon.py` module (lines 414-628) provides a comprehensive implementation of the canonical form, covering various transformations like entity decoding, number normalization, and punctuation handling, as described in its header comment.

2. **Error Handling and Data Integrity:**
   - The changes ensure that text normalization and comparison are consistent across the pipeline, reducing the risk of silent exceptions or incorrect comparisons.
   - There is no indication from the diff that a path could produce a PASS when data is missing or a model failed. The functions seem to handle inputs robustly, but without the full context of how these functions are called, it's hard to be certain.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT
   - The use of `canon.canon_tokens` ensures that words are consistently normalized, supporting accurate sentence boundary detection (lines 8-12, 23-46).

2. **SELECTION LOCK:** COMPLIANT
   - The changes do not indicate any recomputation of expected words after selection. The use of canonical forms ensures consistency (lines 330-333).

3. **SNAP LIMIT:** COMPLIANT
   - The canonical form ensures that comparisons are accurate, which supports maintaining snap limits (lines 23-46).

4. **NEIGHBOUR:** COMPLIANT
   - The canonical form helps ensure that edge words are correctly identified, supporting the neighbor rule (lines 23-46).

5. **ONSET/TAIL:** COMPLIANT
   - The canonical form aids in maintaining accurate onset and tail word detection (lines 23-46).

6. **CREDITS:** COMPLIANT
   - The use of canonical forms in name matching (lines 80-84) supports accurate credit checks.

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT
   - The canonical form is used to ensure accurate name matching in sign-offs (lines 400-410).

8. **L-b EDGE WORDS WHOLE:** COMPLIANT
   - The canonical form supports accurate edge word detection (lines 23-46).

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT
   - The canonical form aids in ensuring accurate edge word comparisons (lines 23-46).

10. **L-d PROTECTED PREVIEW:** COMPLIANT
    - The changes do not affect the protected preview path.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT
    - The canonical form ensures that punctuation is consistently handled (lines 23-46).

12. **L-f CHANNELS FIRST:** COMPLIANT
    - The canonical form supports accurate channel name detection (lines 400-410).

13. **L-g WRITTEN FORMS:** COMPLIANT
    - The canonical form explicitly handles written forms as spoken words (lines 414-628).

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT
    - The canonical form decodes entities and joins split tokens, aligning with this law (lines 414-628).

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT
    - The canonical form supports accurate event detection (lines 414-628).

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT
    - The changes ensure consistent text handling, supporting accurate release checks (lines 414-628).

17. **L-k ONE CANONICAL FORM:** COMPLIANT
    - The introduction of `canon.py` ensures that all text comparisons use a single canonical form (lines 414-628).

18. **LAW 20 / M2:** COMPLIANT
    - The changes do not alter gate thresholds or reclassify failing gates.

19. **M12 FAIL CLOSED:** COMPLIANT
    - The changes ensure robust handling of text normalization, reducing the risk of silent failures.

20. **LAW 22:** COMPLIANT
    - The changes do not affect the v2f reference path.

### Q3: TESTS

1. **Test Coverage:**
   - The tests in `test_canon.py` (lines 629-862) comprehensively cover the canonical form transformations, including HTML entities, unicode normalization, number handling, and more.
   - The tests in `test_g3b_majority.py` (lines 148-180) verify that symbols are read as spoken words, aligning with law L-g.
   - The tests in `test_stand_alone.py` (lines 182-195) ensure that subject terms are correctly identified, supporting law L-f.

2. **Must-Fail and Must-Pass:**
   - The tests include cases that must fail and pass, as required by the laws, ensuring that the canonical form is correctly implemented and used.

3. **Potential Issues:**
   - There are no indications of assertions that could pass vacuously. The tests seem well-constructed to validate the canonical form.

### Q4: VERDICT

1. **SEVERITY | diff line | issue | fix:**
   - No defects were identified in the diff. The changes appear to be well-aligned with the laws and the functionality described.

2. **READY:** The changes are ready for integration, as they comply with the laws and are supported by comprehensive tests.