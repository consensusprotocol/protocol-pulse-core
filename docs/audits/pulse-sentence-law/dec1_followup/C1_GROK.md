**Q1: CORRECTNESS**  
The added `tail_rows` (lines 9-13) matches its docstring and the call site (line 25). It separates the G9 calibrated gate result from the `outro_locked` check and never produces a PASS when `conform_fallback=True`. No off-by-one, unit, or exception paths are visible in the diff. The change at line 25 is a direct substitution that preserves prior logic. No evidence of state leakage or recomputation of locked values.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL: not addressed in this diff (no changes to `sentence_law.py`, boundary adjudication, or cut movement).  
- CREDITS, LAW 20/M2, M12 FAIL CLOSED: not touched.  
- LAW 22 (v2f reference byte-identity): the diff does not alter rendering or reference paths.  
- The G9/outro separation (lines 9-13, 25, 57-64) keeps the calibrated gate independent of fallback, which is consistent with “fail closed” and “never loosen a gate.” No violations visible in the provided diff.

**Q3: TESTS**  
`TestTailRows` (lines 51-64) directly exercises the new function with the four input combinations and asserts the exact dicts plus verdict outcomes. The assertions are non-vacuous. The earlier assertion change (lines 46-48) tightens the check from an indirect `luma_ok` test to an explicit `ok` + numeric comparison. No vacuous paths observed.

**Q4: VERDICT**  
Defects:  
- SEVERITY: LOW | diff line 58, 64 | `verdict_for` is called on the return value of `tail_rows` but is not added or shown in the diff for `run_fresh.py`.  
- SEVERITY: LOW | diff line 1-68 | The commit title/branch is “pulse-sentence-law” yet the diff contains only G9_tail refactoring; sentence-boundary, onset, or credit logic is absent.

READY (for the narrow scope of the diff). The changes shown are internally consistent and do not violate the listed laws.