**Q1: CORRECTNESS**  
The changed functions in `select_passages.py` (lines 16-37, 46, 54-59) correctly implement the new conflict checks and post-build duration validation against the locked words' actual span. No path allows a PASS when data is missing or a model fails (M12 FAIL CLOSED is respected). No off-by-one, unit, or silent-exception issues visible in the diff. The `_conflicts` helper and budget re-check after `_build_segment` are the only material changes.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SNAP LIMIT / SELECTION LOCK: COMPLIANT (lines 54-59 reject when locked words fall outside budget; selection_lock is never recomputed).  
- ONSET/TAIL, CREDITS, G12/G15, LAW 20/M2, M12 FAIL CLOSED, LAW 22: no changes in the diff, so COMPLIANT by absence.  
- No cut can move outside the locked sentence's silence, no gate thresholds are loosened, and v2f reference behavior is untouched.

**Q3: TESTS**  
The new tests in `test_sentence_windows.py` (lines 235-268) and updates in `test_fresh.py` (lines 83-124) prove the must-fail cases fail for the documented reasons (missing pause, budget violation on locked words, double-use of a fallback window) and the control cases pass with the expected first/last words. No vacuous assertions; every check inspects concrete `first_word`/`last_word`, rejection strings, or coordinate invariants.

**Q4: VERDICT**  
No defects found.  

READY