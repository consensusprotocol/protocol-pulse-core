# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:46
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (gate logic) | 8/10 | 9/10 | 8/10 | 8/10 |
| Law Compliance (overall) | 4/10 | 9/10 | 5/10 | 5/10 |
| Sentence Law implementation | 0/10 | 7/10 | 6/10 | 3/10 |
| Test Coverage (gate calibration) | 9/10 | 9/10 | 8/10 | 9/10 |
| Test Coverage (sentence/onset/tail) | 0/10 | 6/10 | 5/10 | 3/10 |
| G8 soft-source logic | 7/10 | 9/10 | 4/10 | 6/10 |
| Threshold calibration (DEC-1) | 7/10 | 9/10 | 3/10 | 6/10 |
| Feature completeness | 1/10 | 7/10 | 6/10 | 4/10 |
| Overall Readiness | 3/10 | 8/10 | 4/10 | 4/10 |

> **Score methodology:** Gemini and Grok penalized heavily for missing sentence-law implementation and threshold-law tension. GPT-4o was more lenient on both. Consensus scores weight the two dissenting models more heavily on contested items and average on uncontested items.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — `run_fresh.py` G8 source-clip wiring fix is correct and necessary
- **File/Lines:** `run_fresh.py` lines 13-16
- **What:** All three models agree that passing `source_clips` to `run_gates` correctly fixes the previously broken G8 path where sources were missing, causing perpetual "no_source" failures that were silently waived.
- **Action:** Keep the fix exactly as written. No change needed; flagged here as a confirmed correct repair.

### U2 — DEC-1 calibration tests in `test_dec1_calibration.py` are high quality and non-vacuous
- **File/Lines:** `pipeline/test_dec1_calibration.py` lines 54-175
- **What:** All three models independently verified that the four boundary-condition tests (`test_g*_just_beyond_fails`) are specific, correctly structured, and cannot pass vacuously. The control test (`test_reference_passes_every_calibrated_gate`) is correctly positioned as the central invariant.
- **Action:** Preserve these tests exactly. Do not alter thresholds, fixture construction, or assertion style.

### U3 — Zero test coverage for Sentence Law, Onset/Tail, and Credits
- **File/Lines:** N/A — missing files
- **What:** All three models noted the absence of any tests covering sentence-boundary detection, mid-sentence cut prevention, the ≥80 ms sub-speech onset/tail rule, or the credits warp defect (D4).
- **Action:** New test files must be created. See Final Action Plan P0-C and P1-B.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Sentence Law implementation is entirely absent (Gemini + Grok; GPT-4o partially dissented)
- **File/Lines:** N/A — `pipeline/sentence_law.py` missing or unmodified
- **What:** Gemini flagged this as CRITICAL. Grok treated it as implicit in the Law 20 violation finding. GPT-4o assessed SENTENCE LAW as COMPLIANT, but its reasoning was that "the changes do not affect sentence boundary handling directly" — which is precisely the problem. The feature is named `pulse-sentence-law` and the described defects D1 (clipped words), D2/D3 (mid-sentence cuts) are the headline deliverables. None appear in the diff.
- **Tiebreaker:** Gemini and Grok are correct. GPT-4o's compliance determination conflates "not broken" with "implemented." A law that is not implemented is not compliant.
- **Action:** `pipeline/sentence_law.py` must be authored or substantially modified in this commit. See P0-A.

### M2 — Law 20 / M2 tension: threshold constants were changed (Grok + Gemini; GPT-4o dissented)
- **File/Lines:** `qa_gates.py` lines 190-193, 203, 231, 261, 279
- **What:** Grok called this a HIGH severity violation outright. Gemini called it a "PARTIAL" violation but offered a justified-calibration rationale. GPT-4o found full compliance.
- **Tiebreaker:** See CONFLICTS section below for full resolution. The majority concern is valid but the resolution differs from Grok's recommendation. The constants were changed with documented justification (DEC-1 decision, reference-asset anchoring, test coverage), which distinguishes this from an ad-hoc gate-loosening. However, the process risk is real and must be documented.
- **Action:** Add a comment block at lines 190-193 citing the DEC-1 decision record, the approving commit hash of the reference asset, and the date. This satisfies Law 20's intent (traceability) without reverting the calibration. See P2-A.

### M3 — Onset/Tail law (≥80 ms sub-speech audio, ≥85% word duration) not implemented (Gemini + Grok)
- **File/Lines:** N/A — missing logic
- **What:** Both Gemini and Grok flagged this explicitly. GPT-4o assessed it as COMPLIANT because G9 tail checks were calibrated — but G9 luma floor calibration is not the same as checking that ≥80 ms of sub-speech audio precedes/follows a cut.
- **Action:** Implement onset/tail enforcement logic. See P1-A.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 — Gemini: Removal of "FLAG / APPROVED KNOWN EXCEPTION" logic from `run_fresh.py` strengthens M12 compliance
- **Source:** Gemini only
- **File/Lines:** `run_fresh.py` lines 24-31 (removed), 41-48 (removed)
- **Assessment:** **IMPLEMENT / CONFIRM.** This is a genuinely valuable observation. The old code re-classified hard gate failures as soft "flags," effectively creating a hidden FAIL-OPEN path. The removal is architecturally correct and strengthens the system. No other model noticed this. It should be explicitly called out in the commit message and preserved unconditionally.

### I2 — Grok: G8 soft-source logic change (`degrad_ok if soft_source else floor_ok and degrad_ok`) is a material acceptance-criteria change, not just a calibration tweak
- **Source:** Grok only
- **File/Lines:** `qa_gates.py` lines 243-244
- **Assessment:** **INVESTIGATE FURTHER.** Grok's concern is legitimate in principle: changing what a gate accepts is distinct from recalibrating a threshold. Gemini accepted this as a deliberate "DEC-3" rule; GPT-4o found it correct. The question is whether the soft-source carve-out has a documented decision record analogous to DEC-1. If this logic was added without a formal decision, it represents an undocumented gate-loosening. **Required action:** Verify that a DEC-3 decision record exists in the project docs. If it does, add a code comment citing it at line 240. If it does not, the logic must either be documented retroactively or reverted pending a formal decision.

### I3 — Gemini: Credits / avatar warp defect (D4) not addressed
- **Source:** Gemini only (Grok and GPT-4o did not raise this)
- **File/Lines:** N/A — missing
- **Assessment:** **INVESTIGATE FURTHER.** If D4 is in scope for this feature branch, it needs implementation. If it was descoped, the feature description should be updated to reflect that. Do not silently omit a listed defect. Requires scope clarification before second pass.

### I4 — GPT-4o: `.get(fmt, default_value)` pattern in threshold lookups prevents KeyError
- **Source:** GPT-4o (Gemini noted it as "robust" without explicit flagging)
- **File/Lines:** `qa_gates.py` lines 231, 261, 279
- **Assessment:** **CONFIRM AS STRENGTH.** The `.get()` pattern with a sensible default is correct defensive programming and aligns with M12 FAIL CLOSED if the default is the strictest value. Verify that the defaults used in `.get()` calls are the strictest available values, not permissive ones. If defaults are permissive, change them to the strictest threshold.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Law 20 / M2: Violation vs. justified re-calibration vs. full compliance

| Model | Position |
|---|---|
| Grok | HIGH violation — revert thresholds to prior constants entirely |
| Gemini | Partial violation — justified by DEC-1 but process risk remains |
| GPT-4o | Fully compliant — thresholds adjusted to match reference worst-case, not loosened |

**Tiebreaker — Gemini is closest to correct:**
- Grok's position (revert everything) is too absolute. Law 20's intent is to prevent ad-hoc gate-loosening to rubber-stamp failing renders, not to freeze constants for eternity regardless of documented decisions. If thresholds could never change, the QA system could never be calibrated to new approved references.
- GPT-4o's position (fully compliant) is too lenient. The spirit of Law 20 requires traceability and formal process, not just a good outcome.
- Gemini's framing is correct: this is a justified calibration *if and only if* the DEC-1 decision record exists and is cited in code. The fix is documentation, not reversion.
- **Resolution:** Keep calibrated thresholds. Mandate a DEC-1 decision-record citation at lines 190-193. Mandate verification that the DEC-3 decision record exists for the soft-source logic. If either decision record is absent, those specific changes must be reverted pending formal documentation.

### C2 — SENTENCE LAW compliance status

| Model | Position |
|---|---|
| GPT-4o | COMPLIANT — changes don't affect sentence boundary handling |
| Grok | Implicitly non-compliant (Law 20 framing absorbs this) |
| Gemini | VIOLATION — law not implemented at all |

**Tiebreaker — Gemini is correct:**
GPT-4o's reasoning is logically flawed. "The changes do not affect sentence boundary handling" is true precisely because there are no sentence boundary changes — which is the violation. A law that is listed as a named deliverable for a feature branch must be implemented, not merely not-broken. The feature is called `pulse-sentence-law`. The sentence law must be in the diff.

### C3 — G8 soft-source logic: correct vs. undocumented gate-loosening

| Model | Position |
|---|---|
| GPT-4o | Correct — deliberate, well-implemented rule |
| Gemini | Correct in context of DEC-3 rule |
| Grok | HIGH violation — restore original `floor_ok and degrad_ok` |

**Tiebreaker — GPT-4o and Gemini are conditionally correct:**
The logic itself is not wrong in concept. However, Grok correctly identifies that changing what a gate accepts requires explicit documentation. The resolution is: cite DEC-3, do not revert. If DEC-3 is undocumented, Grok's recommendation to revert is the correct fallback.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **`run_fresh.py` source_clips wiring fix** (lines 13-16) — Unanimously correct. Do not alter.
2. **`test_dec1_calibration.py` gate calibration tests** (lines 54-175) — Unanimously high quality, non-vacuous, boundary-condition-aware. Do not alter test logic, fixture construction, or assertions.
3. **Removal of FLAG/APPROVED KNOWN EXCEPTION re-classification logic** from `run_fresh.py` — Architecturally correct, strengthens M12 compliance. Do not reintroduce soft-pass paths.
4. **`.get(fmt, default)` pattern for threshold lookups** — Correct defensive programming aligned with M12. Preserve this pattern in all new gate code.
5. **`test_reference_passes_every_calibrated_gate` as central control test** — Correctly anchors calibration to the frozen v2f reference. Do not modify.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence | Notes |
|---|---|---|---|
| SENTENCE LAW | ❌ VIOLATED | High (3/3 effective) | Not implemented. GPT-4o's compliance finding rejected — see C2. |
| SELECTION LOCK | ⚠️ UNCERTAIN | Low | No code touched; cannot verify. |
| SNAP LIMIT | ⚠️ UNCERTAIN | Low | No code touched; cannot verify. |
| ONSET/TAIL (≥80ms) | ❌ VIOLATED | Medium (2/3) | Not implemented. G9 luma calibration is not onset/tail enforcement. |
| CREDITS (D4) | ❌ UNCERTAIN/VIOLATED | Low (1/3) | Gemini only. Requires scope clarification. |
| LAW 20 / M2 | ⚠️ CONDITIONAL | Medium | Compliant if DEC-1/DEC-3 decision records exist and are cited. Violated if they do not. |
| M12 FAIL CLOSED | ✅ COMPLIANT | High (3/3) | No silent pass-on-missing-data paths introduced. FLAG/EXCEPTION logic removed (strengthens). |
| LAW 22 (v2f frozen) | ✅ COMPLIANT | High (3/3) | No renderer changes. Tests read reference; do not rewrite it. |
| Smallest diff / no new renderer | ✅ COMPLIANT | High (3/3) | Changes are scoped and focused. |
| GPU0 only / no publishing | ✅ COMPLIANT | High (3/3) | No GPU or publishing changes visible. |

---

## SECURITY CONSENSUS

No security issues were flagged by any model. The diff does not introduce external inputs, deserialization, privilege escalation, or new network paths. No security findings to report.

---

## WORLD-CLASS GAP CONSENSUS (2+ models flagged)

1. **Missing headline feature (Sentence Law, D1/D2/D3):** The branch is named for a law that is not in the diff. A world-class delivery ships the full contract. *(Gemini + Grok, implicitly all 3)*
2. **Missing onset/tail enforcement:** The ≥80 ms sub-speech audio check is a named law and is absent. Gate calibration of an adjacent metric (G9 luma) is not a substitute. *(Gemini + Grok)*
3. **Missing decision-record traceability in code:** World-class QA systems annotate threshold constants with the decision record (date, approver, record ID) that authorized a change, so future engineers can distinguish "calibrated by decision" from "changed to pass." *(Gemini + Grok, implicitly)*
4. **No cross-law integration test:** A world-class audit would include an end-to-end test that exercises a render through G3c, G5, G8, G9 *and* sentence-law checks in a single pipeline call. The current tests are unit-level only. *(Gemini + GPT-4o)*

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Implement pipeline/sentence_law.py with D1/D2/D3 enforcement | pipeline/sentence_law.py (new or substantially modified) | models: gemini+grok (GPT-4o rejected) | Feature is named pulse-sentence-law; D1 (clipped words), D2/D3 (mid-sentence cuts) are primary deliverables; none appear in diff; branch cannot ship without them

P0 CRITICAL | Author tests for sentence law: boundary detection, mid-sentence cut rejection, clipped-word detection | pipeline/test_sentence_law.py (new) | models: all 3 (unanimous gap) | Zero test coverage for the headline feature; no confidence in correctness without tests

P0 CRITICAL | Verify DEC-1 decision record exists; add citation comment at threshold block | qa_gates.py lines 190-193 | models: gemini+grok | Law 20 compliance is conditional on documented decision; if record absent, revert calibrated thresholds until formally approved

P0 CRITICAL | Verify DEC-3 decision record exists for soft-source logic; add citation comment | qa_gates.py lines 240-244 | models: grok (unique, elevated) | Changing gate acceptance criteria without a decision record is a Law 20 violation regardless of technical correctness; if DEC-3 absent, revert lines 243-244 to `floor_ok and degrad_ok` pending formal decision

P1 HIGH | Implement onset/tail enforcement: ≥80ms sub-speech audio before first word and after last word | pipeline/sentence_law.py or pipeline/qa_gates.py (new gate or sub-check) | models: gemini+grok | Named law; not implemented; G9 luma calibration is not equivalent

P1 HIGH | Author onset/tail tests at boundary condition (79ms fails, 80ms passes) | pipeline/test_onset_tail.py (new) | models: gemini+grok | No coverage; cannot verify correctness

P1 HIGH | Clarify scope of D4 (credits/avatar warp): implement if in scope, update feature description if descoped | pipeline/ (location TBD) or docs/ | models: gemini (unique, elevated) | Cannot silently omit a listed defect; resolve scope ambiguity before second pass

P1 HIGH | Verify .get(fmt, default) defaults are the STRICTEST available threshold values, not permissive ones | qa_gates.py lines 231, 261, 279 | models: gpt4o+gemini (implicit) | M12 FAIL CLOSED requires that an unknown format fails hard, not passes softly; permissive defaults are a silent FAIL-OPEN

P2 MEDIUM | Add DEC-1 decision record citation to code comment block (date, approver, record ID, reference asset commit hash) | qa_gates.py lines 184-193 | models: gemini+grok | Traceability requirement for Law 20; distinguishes calibration from ad-hoc loosening for future engineers

P2 MEDIUM | Add commit-message / changelog note explicitly calling out removal of FLAG/APPROVED KNOWN EXCEPTION logic as an M12 strengthening | run_fresh.py | models: gemini (unique) | Architectural improvement should be documented; future engineers must not reintroduce soft-pass paths

P2 MEDIUM | Add integration test: full pipeline call exercising G3c+G5+G8+G9+sentence_law on a single render | pipeline/test_integration_pulse.py (new) | models: gemini+gpt4o (implicit) | Unit tests cover gates in isolation; no end-to-end coverage proves gates interact correctly under orchestration
```

---

## CYCLE 1 VERDICT

**NOT READY — Fundamental rework required before second build pass.**

The gate calibration work (G3c, G5, G8, G9, DEC-1) is technically sound and well-tested. The G8 source-clip wiring fix is correct. The removal of the soft-pass FLAG logic is an architectural improvement.

However, the branch delivers less than 25% of its stated contract. The headline feature — Sentence Law enforcement covering D1/D2/D3 — is entirely absent from the diff. The Onset/Tail law is unimplemented. D4 scope is unresolved. Two threshold changes (DEC-1 calibration, DEC-3 soft-source logic) have conditional Law 20 compliance that depends on external decision records that have not been verified.

A second build pass must ship the sentence law implementation, onset/tail enforcement, decision-record citations, and the full test suite before this branch is auditable as READY.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement pipeline/sentence_law.py with D1/D2/D3 enforcement | pipeline/sentence_law.py (new or substantially modified) | The feature is named pulse-sentence-law; clipped words (D1) and mid-sentence cuts (D2/D3) are primary deliverables and are entirely absent from the current diff.

P0 CRITICAL | Author tests for sentence law: boundary detection, mid-sentence cut rejection, clipped-word detection | pipeline/test_sentence_law.py (new) | Zero test coverage for the headline feature.

P0 CRITICAL | Verify DEC-1 decision record exists in docs/; add citation comment at qa_gates.py lines 190-193 citing record ID, approver, date, and reference asset commit hash. If the record does not exist, revert lines 190-193 to their prior constants until formally approved. | qa_gates.py lines 190-193

P0 CRITICAL | Verify DEC-3 decision record exists in docs/ for the soft-source gate logic. Add citation comment at qa_gates.py lines 240-244. If DEC-3 does not exist, revert lines 243-244 to `floor_ok and degrad_ok` pending formal decision. | qa_gates.py lines 240-244

P1 HIGH | Implement onset/tail enforcement: ≥80ms sub-speech audio required before first word and after last word per cut. Add as a new sub-check in pipeline/sentence_law.py or as a new gate in qa_gates.py. | pipeline/sentence_law.py or qa_gates.py

P1 HIGH | Author onset/tail boundary tests: 79ms fixture must FAIL, 80ms fixture must PASS. | pipeline/test_onset_tail.py (new)

P1 HIGH | Clarify scope of D4 (credits/avatar warp). If in scope: implement fix and tests. If descoped: update PULSE_SENTENCE_LAW_GOSPEL.md and feature description to explicitly remove D4. Do not leave it silently unaddressed. | pipeline/ or docs/

P1 HIGH | Verify that all .get(fmt, default) threshold lookups in qa_gates.py lines 231, 261, 279 use the STRICTEST available threshold as the default, not a permissive one. If any default is permissive, replace it with the strictest value. | qa_gates.py lines 231, 261, 279

P2 MEDIUM | Add DEC-1 decision-record citation block (date, approver, record ID, reference asset commit hash) as a comment at qa_gates.py lines 184-193. | qa_gates.py lines 184-193

P2 MEDIUM | Add a changelog entry or inline comment in run_fresh.py explicitly documenting that the FLAG/APPROVED KNOWN EXCEPTION soft-pass logic was removed as an M12 strengthening. Future engineers must not reintroduce it. | run_fresh.py

P2 MEDIUM | Author an end-to-end integration test that exercises a single render through G3c, G5, G8, G9, and sentence_law checks in one orchestrated pipeline call. | pipeline/test_integration_pulse.py (new)

VALIDATED — do NOT touch these