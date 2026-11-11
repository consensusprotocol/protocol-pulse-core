# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
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

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `tail_rows`**:
   - The function `tail_rows` is designed to return a dictionary indicating the status of `G9_tail` and `outro_locked` based on the inputs `g9_pass` and `conform_fallback`. The docstring explains that `G9_tail` should reflect the calibrated gate alone, and `outro_locked` should fail if a conform fallback is used. The function correctly implements this logic as per the docstring (lines 9-13 and 25).
   - There are no off-by-one errors, wrong units, or silent exceptions in this function. The logic is straightforward and directly maps to the inputs provided.

2. **Function `stage_gates`**:
   - The modification in `stage_gates` updates the `rows` dictionary using the `tail_rows` function. This change ensures that the status of `G9_tail` and `outro_locked` is correctly updated based on the results from `res["G9_tail"]["pass"]` and `fallback` (line 25).
   - The function does not introduce any paths that could produce a PASS when data is missing or a model failed. The logic for updating the `rows` dictionary is clear and directly tied to the results of the gate checks.

3. **Test Cases**:
   - The test cases for `tail_rows` verify that the function behaves as expected under different conditions. The tests check that the function returns the correct status for `G9_tail` and `outro_locked` based on the inputs provided (lines 51-64).
   - The tests ensure that the function does not produce a PASS when it should not, and they cover the expected behavior for both passing and failing conditions.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT
   - The diff does not directly address sentence boundaries, but there is no indication that the changes violate this law. The focus is on outro handling, not sentence boundaries.

2. **SELECTION LOCK**: COMPLIANT
   - The changes do not involve recomputing expected words after selection. The logic pertains to outro handling and does not affect sentence selection.

3. **SNAP LIMIT**: COMPLIANT
   - There is no indication that cuts can move outside the locked sentence's silence. The changes are related to outro handling.

4. **ONSET/TAIL**: COMPLIANT
   - The changes ensure that outro handling respects the calibrated gate, which aligns with maintaining audio integrity.

5. **CREDITS**: NOT APPLICABLE
   - The diff does not involve credit handling.

6. **LAW 20 / M2**: COMPLIANT
   - The changes do not alter gate thresholds or reclassify failing gates as false positives. The logic strictly adheres to the existing gate checks.

7. **M12 FAIL CLOSED**: COMPLIANT
   - The logic ensures that missing data or model failures result in a FAIL, as evidenced by the test cases.

8. **LAW 22**: COMPLIANT
   - The changes do not affect the re-rendering of the frozen v2f reference.

### Q3: TESTS

- The test cases effectively verify the behavior of the `tail_rows` function. They ensure that the function returns the correct status for `G9_tail` and `outro_locked` based on the inputs provided (lines 51-64).
- The tests are specific and do not pass vacuously. They cover both passing and failing scenarios, ensuring the function behaves as expected under different conditions.

### Q4: VERDICT

- **SEVERITY**: None | **Diff Line**: N/A | **Issue**: N/A | **Fix**: N/A

**READY**: The changes are compliant with the laws, the functions behave as expected according to their docstrings, and the tests adequately verify the intended behavior. There are no defects identified in the diff provided.

## GEMINI — CYCLE 1 OUTPUT
Excellent. I will now perform the requested code audit.

---

## PULSE CHECK: CODE AUDIT

**Model:** Gemini 2.5 Pro
**Feature:** `pulse-sentence-law`
**Branch:** `combo-letterbox-quoteonly-v2`
**Commit:** `179e56a7` (inferred from diff)

### Q1: CORRECTNESS

The functions modified and added in this diff appear to be correct *for what they do*.

1.  **`tail_rows(g9_pass, conform_fallback)` (lines 9-13):** This new function correctly implements the logic described in its docstring. It separates the result of the `G9_tail` luma gate from a new, distinct check `outro_locked`. It returns "PASS" or "FAIL" strings in a dictionary as expected. The logic is straightforward and does not appear to have off-by-one errors, state leakage, or pathways for silent exceptions.
2.  **`stage_gates` modification (line 25):** The replacement of the inline boolean expression with a call to `tail_rows` is correct. It properly passes the `g9_pass` result and the `fallback` boolean to the new function, and `dict.update()` correctly merges the returned dictionary into the `rows[fmt]` dictionary.

However, a significant point of concern is the disconnect between the feature's name/purpose (`pulse-sentence-law`) and the code presented. The diff shows **no changes related to sentence boundary detection, onset/tail audio, or transcript analysis.** The changes are exclusively focused on refactoring the `G9_tail` (luma check on outro) gate logic. This diff, in isolation, does not implement the SENTENCE LAW or fix the documented defects D1, D2, D3, D4, or D5. It may be related to D6 (abrupt channel changes) if an outro is considered a type of channel change, but this is an inference.

Regarding **M12 FAIL CLOSED**, the change actually strengthens this principle. The previous logic on line 24 (`res["G9_tail"]["pass"] and (identical or not fallback)`) could have allowed a non-identical, non-fallback outro to pass the `G9_tail` gate. The new logic (lines 9-13, 25) creates a separate failure row (`outro_locked: FAIL`) if a fallback is used, regardless of whether its luma passes. This closes a potential loophole and makes the gate stricter.

### Q2: LAW COMPLIANCE

Based strictly on the provided diff:

-   **SENTENCE LAW:** **UNVERIFIABLE.** The diff does not contain any code that implements or modifies sentence boundary detection, acoustic pause measurement, or transcript adjudication.
-   **SELECTION LOCK:** **UNVERIFIABLE.** The diff does not touch code related to clip selection or the `selection_lock` in `edl.json`.
-   **SNAP LIMIT:** **UNVERIFIABLE.** The diff does not contain code related to moving cut points.
-   **ONSET/TAIL:** **UNVERIFIABLE.** The diff does not contain code related to audio padding or word duration checks.
-   **CREDITS:** **UNVERIFIABLE.** The diff does not contain code related to avatar rendering or selection.
-   **LAW 20 / M2 (Constant thresholds, hard stop):** **COMPLIANT.** The change makes the gate *stricter* by creating a new, explicit failure condition (`outro_locked`) for using a fallback outro. It does not loosen any thresholds. The test on line 48 confirms the `G9_LUMA_FLOOR` constant is still the point of comparison. The new `outro_locked: FAIL` condition, which leads to a `VERDICT_HOLD` (line 58), correctly implements a hard stop for a condition that was previously coupled with the luma check.
-   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, this change improves adherence to M12 by failing closed on any fallback outro, even if it happens to pass the luma check. See line 57, where `tail_rows(True, True)` results in a `FAIL` for `outro_locked`.
-   **LAW 22 (v2f reference):** **COMPLIANT.** The diff does not change the rendering path for the frozen reference. The test modifications in `test_dec1_calibration.py` (lines 45-48) make the validation against the reference *more robust*, not different.
-   **Other Laws (Smallest diff, etc.):** **COMPLIANT.** The diff is small and focused on its specific task of refactoring the G9 gate.

### Q3: TESTS

The tests added and modified are of high quality for the code they are intended to cover.

1.  **`TestDec1` modification (lines 45-48):** The change from a single, weak assertion (`self.assertFalse(d["luma_ok"] in (True, "True"), d)`) to three specific assertions is a significant improvement. The new tests verify that the gate's overall status is `False`, the specific `luma_ok` key is `'False'`, and crucially, that the measured `mean_luma` was indeed less than the threshold. This proves the gate is failing for the correct reason and is not a vacuous pass.
2.  **`TestTailRows` (lines 51-64):** This new test class is excellent. It directly targets the new `tail_rows` function and its integration into the verdict system.
    -   `test_luma_pass_on_a_fallback_outro_fails_outro_locked` (lines 55-58) correctly proves the core claim of the "Heimdall DEC-1 audit": that a fallback outro is a failure condition (`outro_locked: FAIL`) leading to a `VERDICT_HOLD`, even if

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 04:36
Models: grok, gpt4o, gemini

---

## SCORES

Scores extracted from each model's qualitative judgment, normalized to 0–10.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (G9/tail_rows) | 9 | 9 | 9 | **9.0** |
| Law Compliance (verifiable laws) | 8 | 8 | 8 | **8.0** |
| Law Compliance (unverifiable laws) | 1 | 7 | 6 | **4.7** |
| Test Quality | 9 | 8 | 8 | **8.3** |
| Feature Scope / Completeness | 2 | 5 | 4 | **3.7** |
| M12 Fail Closed | 10 | 9 | 9 | **9.3** |
| Overall Readiness | 3 | 8 | 7 | **6.0** |

> **Scoring note:** GPT-4o graded the unverifiable laws COMPLIANT because the diff didn't violate them. Gemini and Grok correctly scored them UNVERIFIABLE/incomplete, which is the materially correct posture for a named feature that claims to implement those laws. The consensus reflects the stricter interpretation.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — `tail_rows` function logic is correct and well-structured
**What:** The new `tail_rows(g9_pass, conform_fallback)` function correctly separates G9 luma gate results from `outro_locked` fallback detection. All three models independently verified correctness.
**File/Line:** `stage_gates.py` lines 9–13, 25
**Action:** No change needed. Confirmed correct.

### U2 — Tests are non-vacuous and directly verify the new function
**What:** `TestTailRows` and the updated `TestDec1` assertions cover all four input combinations and verify correct dict contents and verdict outcomes. All three models agreed the tests are substantively valid.
**File/Line:** `test_dec1_calibration.py` lines 45–64
**Action:** No change needed. Confirmed strong.

### U3 — Feature scope is materially incomplete relative to its stated purpose
**What:** The branch name `pulse-sentence-law` and the feature description claim to implement SENTENCE LAW, ONSET/TAIL, SELECTION LOCK, SNAP LIMIT, CREDITS, and defects D1–D5. The diff contains **zero** code addressing any of these. All three models flagged this gap — Gemini called it MAJOR/NOT READY, Grok called it LOW severity but noted it, GPT-4o implicitly accepted the narrow scope. The correct classification is **critical incompleteness**.
**File/Line:** Entire diff (lines 1–68)
**Action:** The missing implementation must be provided before this feature can be marked READY. See P0 in the action plan.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `outro_locked: FAIL` strengthens M12 Fail Closed (positive finding)
**Models:** Gemini, Grok
**What:** Both noted that the new `tail_rows` logic closes a loophole where a fallback outro with passing luma could previously produce a combined PASS. The gate is now stricter: any `conform_fallback=True` unconditionally fails `outro_locked` regardless of luma result. This is correct behavior.
**File/Line:** `stage_gates.py` lines 9–13
**Action:** Preserve as-is. This is an improvem

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (68 lines)
```
   1 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
   2 | index 12a50b7d..179e56a7 100644
   3 | --- a/pipeline/run_fresh.py
   4 | +++ b/pipeline/run_fresh.py
   5 | @@ -568,6 +568,13 @@ def _status(ok):
   6 |      return "PASS" if ok else "FAIL"
   7 |  
   8 |  
   9 | +def tail_rows(g9_pass, conform_fallback):
  10 | +    """G9_tail is the DEC-1 calibrated gate alone (no exception path). outro_locked: the luma floor is
  11 | +    the approved reference's LOCKED outro tail, so a conform fallback (some other outro) fails closed
  12 | +    on its own row even when its tail clears the floor (Heimdall DEC-1 audit: keep the two apart)."""
  13 | +    return {"G9_tail": _status(g9_pass), "outro_locked": _status(not conform_fallback)}
  14 | +
  15 | +
  16 |  def stage_gates(run, final16, man16, final9, man9):
  17 |      # Keep the source-relative sharpness threshold local to this stage so QA does not
  18 |      # depend on module-global lookup state during long production runs. Threshold unchanged.
  19 | @@ -685,8 +692,7 @@ def stage_gates(run, final16, man16, final9, man9):
  20 |          g9_report[fmt] = {"gate": d, "outro_master_sha256": msha, "outro_conformed_sha256": csha,
  21 |                            "hash_identical_to_locked_outro": identical,
  22 |                            "last_segment": last.get("label"), "conform_fallback": fallback}
  23 | -        # DEC-1 calibrated the luma floor to the approved reference's locked outro; no exception path
  24 | -        rows[fmt]["G9_tail"] = _status(res["G9_tail"]["pass"] and (identical or not fallback))
  25 | +        rows[fmt].update(tail_rows(res["G9_tail"]["pass"], fallback))
  26 |  
  27 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
  28 |      adj = L.Adjudicator()
  29 | diff --git a/pipeline/test_dec1_calibration.py b/pipeline/test_dec1_calibration.py
  30 | index e20b4bd5..2b6ed47a 100644
  31 | --- a/pipeline/test_dec1_calibration.py
  32 | +++ b/pipeline/test_dec1_calibration.py
  33 | @@ -16,6 +16,7 @@ import unittest
  34 |  PIPELINE = os.path.dirname(os.path.abspath(__file__))
  35 |  REPO = os.path.dirname(PIPELINE)
  36 |  sys.path.insert(0, os.path.join(REPO, "segment_v1"))
  37 | +sys.path.insert(0, PIPELINE)                      # run_fresh (no module name is shared with segment_v1)
  38 |  REF = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
  39 |  OUT = {"16x9": os.path.join(REF, "out", "segment.mp4"), "9x16": os.path.join(REF, "out", "segment_vertical.mp4")}
  40 |  MAN = {f: os.path.join(REF, "qa", f"concat_manifest_{f}.json") for f in OUT}
  41 | @@ -131,7 +132,25 @@ class TestDec1(unittest.TestCase):
  42 |          ffmpeg("-sseof", "-3", "-i", OUT["16x9"], "-vf", "eq=brightness=-0.006", "-c:v", "libx264", "-crf", "12",
  43 |                 "-preset", "veryfast", "-c:a", "copy", p)
  44 |          ok, d = quiet(q.gate_g9, p, self.tmp, fmt="16x9")
  45 | -        self.assertFalse(d["luma_ok"] in (True, "True"), d)
  46 | +        self.assertFalse(ok, d)
  47 | +        self.assertEqual(str(d["luma_ok"]), "False", d)          # numpy bool or bool; None/0 fail
  48 | +        self.assertLess(d["mean_luma"], q.G9_LUMA_FLOOR["16x9"], d)
  49 | +
  50 | +
  51 | +class TestTailRows(unittest.TestCase):
  52 | +    """Heimdall DEC-1 audit: G9_tail is the calibrated gate alone; a conform fallback (not the locked
  53 | +    outro the floor was measured on) fails its own row, so the run still holds."""
  54 | +
  55 | +    def test_luma_pass_on_a_fallback_outro_fails_outro_locked(self):
  56 | +        import run_fresh as rf
  57 | +        self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
  58 | +        self.assertEqual(rf.verdict_for(rf.tail_rows(True, True))[0], rf.VERDICT_HOLD)
  59 | +
  60 | +    def test_rows_follow_their_own_inputs(self):
  61 | +        import run_fresh as rf
  62 | +        self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})
  63 | +        self.assertEqual(rf.tail_rows(False, False), {"G9_tail": "FAIL", "outro_locked": "PASS"})
  64 | +        self.assertEqual(rf.verdict_for(rf.tail_rows(True, False))[0], rf.VERDICT_CANDIDATE)
  65 |  
  66 |  
  67 |  if __name__ == "__main__":
  68 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
