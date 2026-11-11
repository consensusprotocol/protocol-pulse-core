### Q1: CORRECTNESS

1. **Function Changes**:
   - **`stage_gates` (lines 5-51)**: The function now correctly passes `source_clips` to `run_gates`, aligning with the docstring and ensuring that G8 has the necessary source clips to function correctly. This change addresses the previous issue where G8 always failed due to missing sources.
   - **`gate_g5` (lines 198-215)**: The function now uses a format-specific true peak max (`tp_max`) from `G5_TRUE_PEAK_MAX_DBFS`, ensuring compliance with DEC-1 calibration. The comparison logic is correct.
   - **`gate_g8` (lines 220-247)**: The function now uses a format-specific sharpness floor from `G8_SHARPNESS_FLOOR`. The logic for handling soft sources (lines 239-244) is correct, ensuring that a clip is not rejected for source softness alone.
   - **`gate_g9` (lines 252-264)**: The function now uses a format-specific luma floor from `G9_LUMA_FLOOR`, ensuring compliance with DEC-1 calibration.
   - **`gate_g3c` (lines 269-282)**: The function now uses a format-specific valley depth from `G3C_VALLEY_DEPTH_DB`, ensuring compliance with DEC-1 calibration.

2. **Error Handling**: There are no silent exceptions or paths that produce a PASS when data is missing or a model failed. The changes ensure that the gates are calibrated correctly and that missing data results in a FAIL, as per LAW 20 and M12 FAIL CLOSED.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT. The changes do not affect sentence boundary handling directly.
2. **SELECTION LOCK**: COMPLIANT. There is no evidence of recomputation of expected words after selection.
3. **SNAP LIMIT**: COMPLIANT. The changes do not allow cuts to move outside the locked sentence's silence.
4. **ONSET/TAIL**: COMPLIANT. The changes ensure that the tail checks (G9) are calibrated to the reference.
5. **CREDITS**: Not applicable in the diff provided.
6. **LAW 20 / M2**: COMPLIANT. Thresholds have been adjusted to match the reference's worst-case values, not loosened.
7. **M12 FAIL CLOSED**: COMPLIANT. Missing data or model failure leads to a FAIL.
8. **LAW 22**: COMPLIANT. The v2f reference path is not altered in behavior.
9. **Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing**: COMPLIANT. The changes are minimal and do not introduce new components or publishing logic.

### Q3: TESTS

1. **Test Coverage**:
   - The tests in `test_dec1_calibration.py` (lines 54-175) cover the DEC-1 calibration changes thoroughly.
   - Each gate has a corresponding test to ensure the reference passes and a slightly altered version fails, proving the calibration is correct.

2. **Assertions**:
   - The assertions check for specific conditions that align with the calibration, ensuring that tests do not pass vacuously. For example, the test for `G3c` (lines 134-144) specifically checks the acoustic tail condition.

### Q4: VERDICT

1. **SEVERITY**: None | All changes align with the laws and ensure correct calibration.
2. **Lines**: No specific line has issues that require fixing.

**READY**: The changes are compliant with the governing laws, and the tests adequately prove the claims made about the calibration adjustments.