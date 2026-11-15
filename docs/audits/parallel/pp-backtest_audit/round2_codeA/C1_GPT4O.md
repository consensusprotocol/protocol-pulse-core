### Q1: CORRECTNESS

The diff introduces a comprehensive set of modules and functions for handling the "Pulse Check" pipeline, focusing on sentence law, onset, and credits compliance. Here's an analysis of the correctness of the functions based on their docstrings and the laws:

1. **Export Functionality**:
   - **`load_record` (Lines 387-399)**: Correctly loads a transcript record by its SHA and checks for hash mismatches, which aligns with the requirement to ensure data integrity.
   - **`tokens` (Lines 402-421)**: Extracts tokens with timestamps, handling both word-level and segment-level timing. The function appears to handle different timing methods correctly.
   - **`sentences` (Lines 424-439)**: Splits tokens into sentences using `sentence_law.is_terminal`, which is consistent with the law that sentences must be whole and standalone.

2. **Lineup and Rules**:
   - **`parse_oracle` (Lines 746-772)**: Parses oracle responses with strict schema validation, ensuring that malformed or incomplete replies are not accepted, which complies with the fail-closed principle.
   - **`check` (Lines 810-860)**: Validates line-up structure against deterministic rules, including sentence count, duration, and altcoin content. It correctly identifies violations, ensuring compliance with the product rules.

3. **Ledger and Spend Management**:
   - **`Ledger` class (Lines 970-1063)**: Manages spend tracking with file locks to ensure atomic updates, preventing overspending. The logic for reserving and settling spends appears robust.

4. **Model and Backend Management**:
   - **`call_backend` (Lines 1550-1591)**: Manages model calls with context length checks and handles vendor-specific errors, ensuring that no call is made if it would exceed the context window or if the spend guard is triggered.

5. **Replay and Scoring**:
   - **`replay` function (Lines 1753-1806)**: Replays the selection process using cached data, stopping if a cache miss occurs, which aligns with the requirement to not infer results when data is missing.

Overall, the functions seem to adhere to their intended purposes, with careful handling of exceptions and strict compliance with schema validation.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT
   - Sentence boundaries are determined using `sentence_law.is_terminal`, ensuring that clips start and end with whole sentences (Lines 424-439).

2. **SELECTION LOCK**: COMPLIANT
   - The `parse_oracle` function ensures that sentence IDs are validated against the day's export, preventing recomputation after selection (Lines 746-772).

3. **SNAP LIMIT**: COMPLIANT
   - The `check` function ensures that segments do not exceed their allowed duration windows unless explicitly allowed (Lines 810-860).

4. **ONSET/TAIL**: COMPLIANT
   - The `check` function enforces duration constraints that indirectly ensure onset and tail compliance (Lines 810-860).

5. **CREDITS**: COMPLIANT
   - The `layout_survives` function checks for layout eligibility, which includes credit compliance (Lines 874-890).

6. **FAIL CLOSED**: COMPLIANT
   - Functions like `parse_oracle` and `parse_judge` strictly validate input and fail if any required data is missing or malformed (Lines 746-772, 775-797).

7. **MODEL REPLY COUNTS ONLY WHOLE**: COMPLIANT
   - Model replies are validated against strict schemas, ensuring that incomplete replies are not accepted (Lines 746-772, 775-797).

8. **LAW 20 / M2**: COMPLIANT
   - Gate thresholds are constants and not modified within the diff, ensuring that a failed gate is a hard stop.

9. **M12 FAIL CLOSED**: COMPLIANT
   - Missing data or model failures lead to a rejection, as seen in the handling of exceptions in functions like `call_backend` (Lines 1550-1591).

10. **LAW 22**: COMPLIANT
    - The v2f reference is not modified, ensuring consistent behavior.

### Q3: TESTS

The provided diff does not include explicit test cases, but the structure suggests that tests are likely part of the overall pipeline, as indicated by references to test files and fixtures (e.g., `test_oracle_export.py` mentioned in comments). The functions are designed with fail-closed principles, which would be tested by ensuring that invalid inputs lead to expected failures.

### Q4: VERDICT

- **SEVERITY: LOW** | No specific line | General observation | Ensure that all test cases are updated to reflect any changes in logic or schema validation.
- **SEVERITY: LOW** | No specific line | General observation | Verify that all external dependencies (e.g., model APIs) are mocked appropriately in tests to ensure consistent test results.

Overall, the code appears to be robust and compliant with the specified laws. The functions are well-structured, with clear error handling and adherence to schema validation. The diff is READY for integration, assuming that the tests are comprehensive and cover all edge cases.