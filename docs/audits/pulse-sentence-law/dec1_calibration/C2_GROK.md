**Cycle 2 Audit — pulse-sentence-law**

### 1. WHAT DID THEY CATCH THAT YOU MISSED?
- Grok correctly identified the **Law 20 / M2 violation** from replacing fixed constants with reference-derived values (lines 190-193, 203, 231, 261, 279). I treated this as benign recalibration; it is not.
- Gemini flagged the **complete absence of Sentence Law implementation** (no changes to sentence boundary detection, onset/tail ≥80 ms rule, or D1/D2/D3 defects). The feature name and docs claim this is the purpose, yet the diff only touches gate thresholds and G8 wiring.
- Both noted the **G8 soft-source rule change** (lines 243-244) as a material acceptance-logic modification, not a pure calibration.

### 2. WHERE DO YOU AGREE OR DISAGREE?
- **Agree with Grok** on Law 20 violation (HIGH). Changing thresholds to make the reference pass is exactly what the law prohibits, regardless of “DEC-1” framing.
- **Agree with Gemini** on missing Sentence Law (CRITICAL). The diff contains zero enforcement of sentence-boundary, mid-sentence cut, or onset/tail rules.
- **Partially agree** on G8 logic: the soft-source path is a deliberate policy change, not a bug fix. It should be called out explicitly rather than buried in calibration.
- **Disagree with my Cycle 1 self**: I was too lenient on both the threshold change and feature completeness.

### 3. NEW FINDINGS FROM THIS REVIEW
The core tension is now clear: the diff attempts to **redefine “passing”** by moving the goalposts to the reference’s measured values while simultaneously claiming Law 20 compliance. This is incompatible. No model in Cycle 1 fully surfaced that the feature is mis-named — it is a gate recalibration patch, not a Sentence Law implementation.

### 4. REVISED SCORES

| Subsystem                    | Cycle 1 | Cycle 2 | Why changed |
|-----------------------------|---------|---------|-------------|
| Correctness (gate logic)    | 9/10    | 7/10    | G8 logic change is now visible as policy shift |
| Law Compliance (overall)    | 9/10    | 3/10    | Clear Law 20 violation + missing Sentence Law |
| Sentence Law implementation | 7/10    | 0/10    | Confirmed absent |
| Test Coverage (gate calibration) | 9/10 | 9/10 | Still strong |
| Test Coverage (sentence/onset/tail) | 6/10 | 0/10 | Confirmed missing |
| G8 soft-source logic        | 9/10    | 4/10    | Now recognized as acceptance change |
| Threshold calibration (DEC-1) | 9/10  | 2/10    | Violates Law 20 |
| Feature completeness        | 7/10    | 1/10    | Wrong feature delivered |
| Overall Readiness           | 8/10    | 2/10    | Major law and scope failures |

### 5. FINAL PRIORITY LIST
**P0 CRITICAL**
- Revert all four threshold dicts (G3C_VALLEY_DEPTH_DB, G5_TRUE_PEAK_MAX_DBFS, G8_SHARPNESS_FLOOR, G9_LUMA_FLOOR) to the original fixed constants (qa_gates.py:190-193).
- Remove or explicitly justify the G8 soft-source rule change (qa_gates.py:243-244) with a new law or DEC record.
- Implement actual Sentence Law checks (sentence boundary detection, ≥80 ms onset/tail, mid-sentence cut prevention) or rename the feature.

**P1 HIGH**
- Add tests covering sentence-boundary, onset/tail, and credits warp (D4).
- Restore or document the previous G8/G9 waiver logic if the new hard-stop behavior is intentional.

**P2 MEDIUM**
- Ensure `run_fresh.py` G8 source wiring fix remains (it is correct).

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Revert the four threshold dictionaries to fixed constants and implement the actual sentence-boundary and onset/tail enforcement logic that the feature name promises.

### 7. PRODUCTION READY?
**No.**  
The diff violates Law 20, delivers zero of the advertised Sentence Law functionality, and changes gate acceptance criteria without proper governance. It must be reworked before any release.