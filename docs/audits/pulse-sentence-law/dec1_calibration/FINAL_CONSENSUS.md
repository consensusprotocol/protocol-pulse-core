# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 03:49
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (gate logic) | 9/10 | 8/10 | 7/10 | **8/10** |
| Law Compliance (overall) | 2/10 | 5/10 | 3/10 | **3/10** |
| Sentence Law implementation | 0/10 | 0/10 | 0/10 | **0/10** |
| Test Coverage (gate calibration) | 9/10 | 9/10 | 9/10 | **9/10** |
| Test Coverage (sentence/onset/tail) | 0/10 | 0/10 | 0/10 | **0/10** |
| G8 soft-source logic | 8/10 | 6/10 | 4/10 | **6/10** |
| Threshold calibration (DEC-1) | 2/10 | 6/10 | 2/10 | **3/10** |
| Feature completeness | 0/10 | 3/10 | 1/10 | **1/10** |
| Overall Readiness | 1/10 | 4/10 | 2/10 | **2/10** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Sentence Law is entirely unimplemented
- **What it is:** The feature `pulse-sentence-law` contains zero code that implements sentence boundary detection, mid-sentence cut prevention, the ≥80 ms onset/tail rule, or any fix for defects D1, D2, or D3 described in the feature spec. The diff exclusively touches gate threshold calibration and G8 input wiring.
- **File/Line:** `pipeline/sentence_law.py` — missing entirely; no diff lines exist for this file.
- **What to change:** Implement the actual Sentence Law enforcement logic: sentence boundary detection, onset/tail guard (≥80 ms), mid-sentence cut prevention, and credits warp prevention (D4). This is the entire stated purpose of the feature and is 100% absent.

### U2 — Zero test coverage for Sentence Law
- **What it is:** No tests exist for sentence-boundary detection, onset/tail enforcement, mid-sentence cut rejection, or any of the D1–D4 defect classes. The only new tests cover DEC-1 gate calibration, which is a different concern.
- **File/Line:** `test_sentence_law.py` — missing entirely.
- **What to change:** Create test file with coverage for: sentence boundary enforcement, onset ≥80 ms, tail ≥80 ms, mid-sentence cut rejection, credits warp (D4), and selection-lock (no recomputation of expected words after selection).

### U3 — G8 source-clip wiring fix is correct and necessary
- **What it is:** `run_fresh.py` lines 13–16 correctly supply `source_clips` to `run_gates`, fixing the bug where G8 always failed with a `no_source` error and was silently waived.
- **File/Line:** `run_fresh.py` lines 13–16.
- **What to change:** Retain this fix unconditionally. It is a genuine bug repair and all three models validated it.

### U4 — DEC-1 gate calibration tests are high quality
- **What it is:** `test_dec1_calibration.py` lines 54–175 correctly use the reference asset as a baseline, test the passing case, and test a fixture "just beyond" the threshold to confirm failure. Tests are non-vacuous.
- **File/Line:** `test_dec1_calibration.py` lines 54–175.
- **What to change:** Retain these tests. Do not remove or weaken them regardless of what happens to the threshold constants themselves.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — LAW 20 / M2 violation: threshold constants replaced with reference-derived values
- **Models:** Grok (HIGH), Gemini (HIGH) — GPT-4o partially disagreed, calling it "justified recalibration."
- **What it is:** Lines 190–193 of `qa_gates.py` replace previously fixed constants (12.0, -2.0, 60, 20) with per-format dictionaries (`G3C_VALLEY_DEPTH_DB`, `G5_TRUE_PEAK_MAX_DBFS`, `G8_SHARPNESS_FLOOR`, `G9_LUMA_FLOOR`) whose values are derived from the DEC-1 reference measurement. LAW 20 / M2 states thresholds are constants and must never be loosened to make a render pass. A `# DEC-1` comment is not a protocol amendment.
- **File/Line:** `segment_v1/qa_gates.py` lines 190–193, 203, 231, 261, 279.
- **What to change:** Revert all four threshold dictionaries to the original fixed constants. If DEC-1 represents a genuine calibration requirement, it must be ratified as a formal amendment to LAW 20 by the governing body before the code change is merged. The comment alone is insufficient.

### M2 — G8 soft-source logic is an unratified policy change
- **Models:** Grok (HIGH), Gemini (medium), GPT-4o (medium).
- **What it is:** Lines 243–244 of `qa_gates.py` introduce a new acceptance rule ("DEC-3"): when a source clip is already below the absolute sharpness floor, only relative degradation (`degrad_ok`) is checked, not the absolute floor (`floor_ok`). This materially changes what G8 accepts. The logic itself is correct per the DEC-3 description, but no ratification record is provided.
- **File/Line:** `segment_v1/qa_gates.py` lines 240–244.
- **What to change:** Revert to `floor_ok and degrad_ok` until DEC-3 is formally approved as a protocol decision. If DEC-3 approval is confirmed out-of-band, document the approval reference (issue number, PBX vote record) in both the code comment and the commit message.

### M3 — Feature is mislabeled / scope mismatch
- **Models:** Gemini (strongly), Grok (strongly) — GPT-4o implied agreement but was less explicit.
- **What it is:** A diff submitted under `pulse-sentence-law` that contains zero sentence-law logic is a process failure. The diff bundles three unrelated efforts: (a) a G8 bug fix, (b) DEC-1 threshold recalibration, and (c) DEC-3 soft-source policy. None of these are Sentence Law.
- **What to change:** Reject this submission as a combined unit. Require it to be split into at minimum two separately named features: `pulse-dec1-calibration` (pending formal ratification) and a genuinely new `pulse-sentence-law` feature containing the actual implementation.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — The mislabeling creates a false compliance record (Gemini only)
- **Observation:** If this diff were merged, the protocol's audit log would record `pulse-sentence-law` as shipped and compliant. Future audits would assume the Sentence Law was implemented. This is worse than the diff simply being wrong — it actively poisons the compliance record.
- **Assessment:** **Implement / Act on immediately.** This is the highest-stakes consequence of the mislabeling problem and justifies the P0 process rejection on its own. Even if every gate change were technically correct, the false record alone is sufficient grounds to block the merge.

### UI2 — `.get(fmt, default_value)` pattern is robust against KeyError (Gemini only)
- **Observation:** The use of `.get()` with a fallback for format lookup prevents `KeyError` exceptions when an unexpected format string is passed.
- **Assessment:** **Keep as implemented.** This is a defensive coding practice worth retaining when the threshold dictionaries are properly ratified and re-introduced.

### UI3 — GPT-4o's partial disagreement on LAW 20 severity (GPT-4o only)
- **Observation:** GPT-4o argued the recalibration was "justified" because it aligns with an approved reference, downgrading the violation to P1 rather than P0.
- **Assessment:** **Do not adopt.** The other two models are correct. LAW 20 exists precisely to prevent well-intentioned recalibrations from quietly shifting thresholds. The existence of a reference does not constitute ratification of a law change. GPT-4o's leniency here is the wrong call; the stricter interpretation is safer and correct.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Severity of G8 soft-source logic change
- **Grok:** SEVERITY HIGH — revert immediately, restore `floor_ok and degrad_ok`.
- **Gemini:** Correctly implemented but unratified policy — block on governance, not correctness.
- **GPT-4o:** Medium concern — needs justification.
- **Tiebreaker ruling: Gemini is most precise.** The code correctly implements DEC-3 as described. The problem is governance, not implementation quality. The correct action is to block on ratification rather than revert on correctness grounds. However, in the absence of confirmed DEC-3 approval, the practical outcome is the same as Grok's: the code must not merge in its current state. Treat as P1 (governance block), not P0 (correctness defect).

### C2 — Whether LAW 20 violation is P0 or P1
- **Grok / Gemini:** P0, revert now.
- **GPT-4o:** P1, review and potentially revert.
- **Tiebreaker ruling: Grok and Gemini are correct.** LAW 20 is a named protocol law, not a style guideline. Any change to protected constants without a formal amendment is a P0 blocking violation. GPT-4o's framing ("potentially revert") is too soft.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **G8 source-clip wiring fix** (`run_fresh.py` lines 13–16): Correctly identifies and resolves the bug where G8 was always failing with `no_source` and being silently waived. Do not touch or revert this fix.
2. **DEC-1 calibration test suite** (`test_dec1_calibration.py` lines 54–175): Tests are non-vacuous, use the reference as a real baseline, and correctly prove the failure condition just beyond threshold. Test structure and assertions are production-quality.
3. **Fail-closed posture (M12):** No new code paths produce a PASS when data is missing or a model fails. The fail-closed contract is intact across all changed gates.
4. **Format-parameterized gate signatures:** Adding `fmt` to gate function signatures with `.get(fmt, default)` lookups is the correct architectural direction for format-aware calibration. The pattern should be retained when the ratified constants are introduced.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Detail |
|---|---|---|
| **LAW 20 / M2** (thresholds are constants; never loosen) | 🔴 **VIOLATED** | Lines 190–193, 203, 231, 261, 279 replace fixed constants with reference-derived dicts without formal amendment |
| **SENTENCE LAW** | 🔴 **NOT IMPLEMENTED** | Zero code exists for sentence boundary, onset/tail, mid-sentence cut, or D1–D4 defect prevention |
| **M12 FAIL CLOSED** | 🟢 Compliant | No new paths pass on missing data |
| **LAW 22** (frozen v2f reference byte-identical) | 🟢 Compliant | No renderer changes; reference only read in tests |
| **M1** (smallest diff; no new renderer/compositor/selector; GPU0 only; no publishing) | 🟢 Compliant | Changes are minimal; no new components |
| **SELECTION LOCK** | 🟢 Compliant (vacuously) | Not implemented but also not violated |
| **SNAP LIMIT** | 🟢 Compliant (vacuously) | Not implemented but also not violated |
| **ONSET/TAIL ≥80 ms** | 🔴 **NOT ENFORCED** | No implementation exists |
| **CREDITS** | 🟡 Not applicable to diff | D4 not addressed |

**Final Law Determination:** This diff violates LAW 20 directly and fails to implement the SENTENCE LAW that the feature is named for. It cannot be merged.

---

## SECURITY CONSENSUS

No security vulnerabilities were flagged by any model. The changes are internal quality-gate logic operating on local audio/video metrics with no network I/O, authentication surface, or data exposure. Security posture is unchanged from baseline.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Actual Sentence Law enforcement** (all 3 models): The titular feature — sentence boundary detection, onset/tail guard, mid-sentence cut prevention — does not exist. A world-class pipeline would have deterministic, tested, law-enforced sentence segmentation before any quality gate is run.

2. **Formal protocol amendment process** (Gemini + Grok): World-class protocol engineering requires that changes to protected constants go through a ratification record (DEC decision log, PBX vote, or equivalent) that is cited in both code comments and commit messages. A comment reading `# DEC-1` with no linked record is insufficient governance.

3. **Feature decomposition discipline** (Gemini + Grok): A world-class team does not bundle a bug fix, a law-level calibration change, and a new policy into a single feature branch with a misleading name. Each concern should be its own atomic, reviewable, and independently revertable change.

4. **Sentence Law test coverage** (all 3 models): End-to-end tests proving that mid-sentence cuts are rejected, that onset/tail ≥80 ms is enforced, and that D1–D4 defect classes are caught are entirely absent. World-class coverage would include regression fixtures for each known defect class.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Reject submission; require feature split into pulse-dec1-calibration + pulse-sentence-law | Process / no single file | models: gemini, grok | Merging creates false compliance record; feature is mislabeled; bundled concerns cannot be safely reviewed or reverted as a unit

P0 CRITICAL | Implement actual Sentence Law: sentence boundary detection, onset/tail ≥80 ms guard, mid-sentence cut rejection, D1/D2/D3 defect prevention | pipeline/sentence_law.py (missing) | models: all 3 | Named feature is 0% implemented; this is the entire stated purpose of the branch

P0 CRITICAL | Create sentence law test suite covering boundary enforcement, onset/tail, mid-sentence rejection, D4 credits warp, selection lock | test_sentence_law.py (missing) | models: all 3 | Zero test coverage for the feature's actual requirements

P1 HIGH | Revert G3C_VALLEY_DEPTH_DB, G5_TRUE_PEAK_MAX_DBFS, G8_SHARPNESS_FLOOR, G9_LUMA_FLOOR to original fixed constants pending formal DEC-1 ratification | segment_v1/qa_gates.py:190-193, 203, 231, 261, 279 | models: gemini, grok | LAW 20 / M2 violation; a comment is not a protocol amendment; reintroduce only after governing body ratification is on record

P1 HIGH | Revert G8 soft-source acceptance logic to `floor_ok and degrad_ok` pending formal DEC-3 ratification; if approval is confirmed, cite the approval record in code and commit | segment_v1/qa_gates.py:240-244 | models: gemini, grok | Unratified policy change to gate acceptance criteria; governance block, not correctness defect

P2 MEDIUM | Extract G8 wiring fix and waiver-logic removal from this branch into the pulse-dec1-calibration feature where it belongs | run_fresh.py:13-16, 33, 50 | models: all 3 (keep the fix, reattribute it) | Fix is correct and should ship, but under the right feature name and alongside the calibration it enables
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

**Overall Consensus Score: 2/10**

This submission has two independent blocking failures, either of which alone would be sufficient to reject it:

1. **LAW 20 is violated.** Four protected gate threshold constants were replaced with reference-derived values without a formal protocol amendment. This is not a matter of interpretation; the law exists specifically to prevent this class of change from occurring without governance oversight.

2. **The feature does not exist.** A branch named `pulse-sentence-law` contains zero implementation of the Sentence Law. No sentence boundary logic, no onset/tail enforcement, no D1–D4 defect handling. The only code in the diff is gate recalibration and a G8 input bug fix — both entirely unrelated to the stated feature.

The G8 wiring fix and the DEC-1 test suite are genuinely good work and should not be discarded — but they belong in a differently named, separately governed feature. As submitted, this branch conflates three unrelated concerns under a misleading name, violates a core protocol law, and would create a false compliance record if merged.

**Absolute final blockers:**
- Sentence Law implementation is missing in its entirety.
- LAW 20 violation must be resolved (revert or ratify) before any threshold change merges.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement actual Sentence Law: sentence boundary detection,
onset/tail ≥80 ms guard, mid-sentence cut rejection, D1/D2/D3 defect
prevention | pipeline/sentence_law.py (missing) | The named feature is
0% implemented; this is the entire stated purpose of the branch.

P0 CRITICAL | Create sentence law test suite covering: sentence boundary
enforcement, onset ≥80 ms, tail ≥80 ms, mid-sentence cut rejection,
D4 credits warp prevention, selection lock (no recomputation of expected
words after selection) | test_sentence_law.py (missing) | Zero test
coverage for the feature's actual requirements.

P1 HIGH | Revert G3C_VALLEY_DEPTH_DB, G5_TRUE_PEAK_MAX_DBFS,
G8_SHARPNESS_FLOOR, G9_LUMA_FLOOR to the original fixed constants.
Do NOT introduce DEC-1 calibration in this branch. LAW 20 / M2 prohibits
threshold changes without formal amendment. These constants must be
restored to their pre-diff values | segment_v1/qa_gates.py:190-193,
203, 231, 261, 279.

P1 HIGH | Revert G8 soft-source acceptance logic to the original
`floor_ok and degrad_ok` rule. The DEC-3 policy change requires
ratification before it may ship. Remove lines 240-244 and restore
the prior single-condition check | segment_v1/qa_gates.py:240-244.

P2 MEDIUM | Retain the G8 source-clip wiring fix (run_fresh.py:13-16)
and the removal of the waiver logic (lines 33, 50) — these are correct
bug fixes that belong in this branch as supporting infrastructure for
the Sentence Law work. Keep them exactly as written.

VALIDATED — do NOT touch these, all models confirmed excellent:
- G8 source-clip wiring fix: run_fresh.py lines 13-16 — correct bug fix,
  retain unconditionally.
- DEC-1 calibration test suite: test_dec1_calibration.py lines 54-175 —
  non-vacuous, high-quality tests; retain even though the threshold
  constants they test must be reverted in this branch.
- Fail-closed posture (M12): all changed gates correctly fail on missing
  data; do not alter any exception-handling or None-check logic.
- Format-parameterized gate signatures: the `fmt` parameter pattern with
  `.get(fmt, default)` lookups is the correct architecture; retain the
  signatures even after reverting the threshold dict values.

After implementing: regression_test.sh must show zero FAILs.
Confirm pipeline/sentence_law.py exists and is non-empty.
Confirm test_sentence_law.py exists with ≥1 passing and ≥1 failing fixture per law rule.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: Grok — In Cycle 1, Grok was the only model to immediately and unambiguously flag the Law 20/M2 violation as a hard SEVERITY HIGH finding with precise line citations, rather than hedging it as "potential" or "benign recalibration," and its NOT READY verdict proved correct against every Cycle 2 consensus finding. In Cycle 2, Grok demonstrated the highest intellectual honesty by explicitly disavowing its own Cycle 1 leniency, correctly converging on both the Law 20 violation and the missing Sentence Law implementation with sharper framing than GPT-4o and comparable depth to Gemini, while also surfacing the unique meta-finding that the feature is fundamentally mis-named — a gate recalibration patch fraudulently labeled as a law implementation.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — BLOCKER: Implement the Sentence Law (feature is 100% absent)**
- Create `pipeline/sentence_law.py` with sentence boundary detection, mid-sentence cut prevention, onset/tail guard (≥80 ms minimum), and D1/D2/D3/D4 defect enforcement
- Wire enforcement into the render pipeline at the point where cuts are finalized
- No other fix matters until this exists; the feature name is a lie without it

**P1 — BLOCKER: Revert all DEC-1 threshold changes (Law 20/M2 violation)**
- Revert lines 190–193, 203, 231, 261, 279 in `qa_gates.py` to their prior fixed constants
- Do not replace constants with reference-derived values under any framing; if DEC-1 calibration is legitimately required, it must go through a formal protocol amendment that amends the law itself, not silently bypass it in a feature branch

**P2 — BLOCKER: Revert G8 soft-source acceptance logic change**
- Restore line 243–244 to the original `floor_ok and degrad_ok` rule
- The soft-source carve-out is a policy change to acceptance criteria, not a calibration fix; it requires an explicit protocol decision, not a buried conditional

**P3 — HIGH: Create Sentence Law test suite**
- Create `test_sentence_law.py` covering: sentence boundary enforcement, onset ≥80 ms guard, tail ≥80 ms guard, mid-sentence cut rejection, D1/D2/D3 defect classification, D4 credits warp prevention
- Tests must be non-vacuous: fixtures must pass the boundary condition and fail one step beyond it

**P4 — MEDIUM: Retain and expand DEC-1 gate calibration tests (but decouple from Law 20 violation)**
- Keep `test_dec1_calibration.py` structure — it is the only high-quality artifact in this diff (consensus 9/10)
- Decouple tests from the reverted threshold values; once P1 is resolved via proper protocol amendment, these tests will serve as the validation harness for any future legitimate recalibration

**P5 — MEDIUM: Retain G8 source-clip wiring fix in `run_fresh.py`**
- The fix on lines 13–16 is correct, necessary, and unanimously validated (U1 consensus finding)
- This is the one clean bug fix in the diff and should survive the revert of all other changes

**P6 — LOW: Rename or re-scope the feature branch**
- The branch `pulse-sentence-law` must not ship containing only gate calibration patches; rename to `pulse-dec1-gate-calibration` if that scope is retained, or hold the branch open until P0 is complete
- Prevents future audit confusion and enforces honest feature accounting