# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 04:38
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (G9/tail_rows) | 9 | 9 | 9 | **9** |
| Law Compliance (verifiable) | 9 | 8 | 8 | **8** |
| Law Compliance (unverifiable) | — | 4 | 3 | **3** |
| Test Quality | 9 | 8 | 9 | **9** |
| Feature Scope / Completeness | 1 | 3 | 2 | **2** |
| M12 Fail Closed | — | 9 | 10 | **10** |
| Overall Readiness | 2 | 5 | 4 | **3** |

> **Score note:** Gemini did not emit a separate M12 or unverifiable-law numeric; dash entries reflect that. The consensus overall readiness of **3/10** is a hard block on production deployment.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Feature scope is critically incomplete relative to its stated name
- **What:** The branch is named `pulse-sentence-law` and the feature ticket documents SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, and CREDITS changes. The diff contains **zero** code touching any of those domains. It exclusively refactors the G9_tail luma gate.
- **File/line:** Entire diff, all 68 lines.
- **Required change:** Either (a) implement the full SENTENCE LAW, ONSET/TAIL, SELECTION LOCK, SNAP LIMIT, and CREDITS logic and append it to this branch before resubmitting, or (b) extract this refactor into a correctly named branch (e.g., `refactor-g9-tail-gate`) and resubmit the two branches separately. Option (a) is the correct path if this was always intended to be one feature.

### U2 — Unverifiable laws must not be labelled COMPLIANT
- **What:** GPT-4o marked SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, CREDITS, and LAW 22 as COMPLIANT despite the diff not containing any code that implements or touches those laws. Laws that are entirely absent from a diff are UNVERIFIABLE, not COMPLIANT. Labelling them COMPLIANT creates a false audit trail and could allow a future reviewer to assume the laws have been validated.
- **File/line:** Audit record — GPT-4o Cycle 1/2 Q2 section.
- **Required change:** Reclassify all laws not addressed by the diff as UNVERIFIABLE in the final audit record. Future audit templates must enforce this distinction.

### U3 — `tail_rows` refactor is correct and M12-strengthening — do not regress it
- **What:** All three models confirmed that the `tail_rows` function logic is correct per its docstring, the call-site substitution at line 25 is a sound replacement, and the net effect is a *stricter* gate that eliminates a latent path where a `conform_fallback` outro with passing luma could have produced a combined PASS.
- **File/line:** `run_fresh.py` lines 9–13, 25; `test_dec1_calibration.py` lines 51–64.
- **Required change:** No change — this is a validated strength. It must not be touched in the second pass.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `verdict_for` appears in tests but is not defined in the diff
- **Models:** Grok (explicit), Gemini (implicit via self-contained review concern).
- **What:** `test_dec1_calibration.py` lines 58 and 64 call `rf.verdict_for(...)`. This function is not shown in the diff, its signature is not visible, and its behaviour can only be inferred. The diff is therefore not fully self-contained for review.
- **File/line:** `test_dec1_calibration.py` lines 58, 64.
- **Required change:** Confirm `verdict_for` is an existing stable utility (add a comment or import path in the test) or include its definition in the diff. If it is new, it must appear in the diff and be tested independently.

### M2 — Branch naming is a process violation regardless of correctness
- **Models:** Grok, Gemini.
- **What:** Shipping a diff under a misleading feature name (`pulse-sentence-law`) when the work is a G9 gate refactor creates confusion in git history, sprint tracking, and future audits. Even if the full sentence-law code is added later, the commit history will conflate two orthogonal concerns.
- **File/line:** Branch name, commit message.
- **Required change:** If the full feature is delivered on this branch, add a clearly scoped commit message for this sub-change (e.g., `refactor(g9-tail): extract tail_rows, tighten fallback gate`). If split into two branches, rename immediately.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — `sys.path.insert(0, PIPELINE)` in test file is a fragile path injection [Gemini only]
- **What:** `test_dec1_calibration.py` uses `sys.path.insert(0, PIPELINE)` to import `run_fresh`. This is a code smell indicating the pipeline directory is not structured as an installable package, which can cause import ambiguity and brittle CI behaviour.
- **Assessment:** **Investigate further.** This is a real architectural concern but not a correctness or law defect in this diff. It should be tracked as a separate technical debt item. Do not block this feature on it, but open a follow-up ticket.

### X2 — Test assertion tightening in `TestDec1` is a silent quality improvement [Grok only]
- **What:** Grok observed that the earlier assertion change (lines 46–48) tightens a check from an indirect `luma_ok` boolean to an explicit `ok` + numeric comparison, making the test more precise.
- **Assessment:** **Implement as stated — already in the diff.** This is a validated micro-improvement. No action needed beyond preserving it.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — GPT-4o "COMPLIANT" vs Grok/Gemini "UNVERIFIABLE" for untouched laws

**GPT-4o position:** Laws not violated = COMPLIANT.
**Grok/Gemini position:** Laws not addressed = UNVERIFIABLE.

**Tiebreaker — Grok/Gemini are correct.** The distinction is fundamental to audit integrity. COMPLIANT means the diff was examined and found to satisfy a law. UNVERIFIABLE means the law is simply not in scope of this diff; no determination can be made. Collapsing UNVERIFIABLE into COMPLIANT inflates confidence in the audit and defeats the purpose of law-by-law tracking. All future audit templates must enforce the three-state classification: COMPLIANT | VIOLATED | UNVERIFIABLE.

### C2 — Overall readiness: GPT-4o (5) vs Grok (4) vs Gemini (2)

**Tiebreaker — Gemini's lower score (2) is closest to correct.** The spread reflects the same underlying disagreement about how harshly to penalise scope incompleteness. Because the diff's stated purpose (SENTENCE LAW) is completely absent, an overall readiness score above 3 misrepresents the submission's maturity. Consensus is set at **3** as a slight softening to credit the genuine M12 improvement.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

1. **`tail_rows(g9_pass, conform_fallback)` logic** — Correct, clean, matches docstring exactly, no silent exception paths. Do not modify.
2. **`stage_gates` call-site substitution (line 25)** — Sound replacement; `dict.update()` correctly merges; no state leakage. Do not modify.
3. **`TestTailRows` test suite (lines 51–64)** — All four input combinations covered, assertions are non-vacuous, verdict outcomes verified. Do not modify.
4. **M12 Fail Closed improvement** — The elimination of the latent fallback-pass path is a genuine security improvement. Do not revert.
5. **Tightened `TestDec1` assertions (lines 46–48)** — More precise than the prior indirect check. Do not revert.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|---|---|---|
| SENTENCE LAW | **UNVERIFIABLE — NOT IMPLEMENTED** | Zero code changes in this domain |
| SELECTION LOCK | **UNVERIFIABLE — NOT IMPLEMENTED** | Zero code changes in this domain |
| SNAP LIMIT | **UNVERIFIABLE — NOT IMPLEMENTED** | Zero code changes in this domain |
| ONSET/TAIL | **UNVERIFIABLE — NOT IMPLEMENTED** | Zero code changes in this domain |
| CREDITS | **UNVERIFIABLE — NOT IMPLEMENTED** | Zero code changes in this domain |
| LAW 20 / M2 (constant thresholds, hard stop) | **COMPLIANT** | No thresholds altered; gate made stricter |
| M12 FAIL CLOSED | **COMPLIANT — IMPROVED** | Fallback path explicitly fails; latent pass path eliminated |
| LAW 22 (v2f reference byte-identity) | **UNVERIFIABLE** | No rendering or reference path changes |

**Final determination:** 1 law COMPLIANT, 1 law COMPLIANT-IMPROVED, 6 laws UNVERIFIABLE. No laws violated within the scope of the diff. The feature cannot be certified against SENTENCE LAW or its related laws until that code is written.

---

## SECURITY CONSENSUS

No security vulnerabilities were identified by any model in the code as written. The closest security-adjacent finding is the M12 improvement (closing a fallent PASS path), which is a positive signal. No injection, auth, or data-exposure risks were identified.

**Priority order:**
1. *(No active security issues to remediate — maintain current M12 strictness.)*

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Missing core feature implementation** (all 3 models) — A world-class delivery of `pulse-sentence-law` requires sentence boundary detection, onset/tail audio validation, selection lock enforcement, snap limit adjudication, and credit handling. None of these exist in the diff. The gap between the feature's name and its content is the single largest distance from world-class.

2. **Audit trail fidelity** (Grok + Gemini) — World-class audit practice requires that law compliance determinations distinguish COMPLIANT, VIOLATED, and UNVERIFIABLE. Collapsing the third state inflates audit confidence and creates false safety. The audit template itself needs to be hardened.

3. **Self-contained diffs** (Grok + Gemini) — A world-class diff includes every function called by the new tests. The absence of `verdict_for` from the diff forces reviewers to infer its behaviour, reducing audit confidence.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Implement full pulse-sentence-law feature (SENTENCE LAW, ONSET/TAIL,
             | SELECTION LOCK, SNAP LIMIT, CREDITS) or split this refactor into its
             | own correctly-named branch before any merge
             | Entire diff / new files TBD
             | models: all 3
             | why: The feature's stated scope is 0% implemented; the branch name is
             |      actively misleading; no law compliance determination is possible

P0 CRITICAL | Reclassify all unverifiable law statuses in audit record from COMPLIANT
             | to UNVERIFIABLE; update audit template to enforce 3-state classification
             | Audit tooling / template
             | models: grok, gemini (unanimous on principle)
             | why: False COMPLIANT ratings corrupt the audit trail and defeat
             |      the purpose of per-law tracking

P1 HIGH     | Confirm or include definition of `verdict_for` in diff; add import
             | path comment in test file so diff is self-contained for review
             | test_dec1_calibration.py lines 58, 64
             | models: grok, gemini
             | why: Reviewers cannot audit behaviour of untested external functions;
             |      self-contained diffs are required for valid certification

P2 MEDIUM   | Add scoped commit message for G9 refactor sub-change regardless of
             | whether feature is split or combined
             | Branch / commit metadata
             | models: grok, gemini
             | why: Preserves git history legibility and sprint traceability

P2 MEDIUM   | Open technical debt ticket for sys.path.insert fragility in test
             | runner; migrate pipeline to installable package structure
             | test_dec1_calibration.py line 37
             | models: gemini (unique — investigate)
             | why: Not a blocker but will cause brittle CI as codebase grows
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The code changes present in the diff are **correct, well-tested, and represent a genuine improvement to M12 Fail Closed semantics**. If this were submitted as `refactor-g9-tail-gate`, it would be READY after resolving the `verdict_for` self-containment issue (P1).

However, as submitted under `pulse-sentence-law`, the feature is **critically incomplete**. The laws it is named to implement — SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, CREDITS — are entirely absent from the diff. No compliance determination can be made for any of them.

**Absolute final blocker:** The SENTENCE LAW feature implementation does not exist. Zero lines of the promised functionality are present. This cannot be waived, deferred, or mitigated by the quality of the G9 refactor.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement full pulse-sentence-law feature (SENTENCE LAW, ONSET/TAIL,
             | SELECTION LOCK, SNAP LIMIT, CREDITS) or split this refactor into its
             | own correctly-named branch before any merge.
             | Target: new files TBD per gospel spec.
             | The G9 tail_rows refactor is already correct — do not regress it.

P0 CRITICAL | Reclassify all law compliance statuses in the audit template.
             | COMPLIANT = diff examined and satisfies law.
             | VIOLATED = diff examined and breaks law.
             | UNVERIFIABLE = law not in scope of this diff; no determination possible.
             | Update audit tooling to enforce this 3-state model going forward.

P1 HIGH     | Add definition or stable import reference for `verdict_for` to the diff
             | so the test file is self-contained for review.
             | File: test_dec1_calibration.py lines 58, 64.

P2 MEDIUM   | Add a scoped commit message for the G9 sub-change:
             |   refactor(g9-tail): extract tail_rows, tighten conform_fallback gate
             | File: commit metadata / branch history.

P2 MEDIUM   | Open a technical debt ticket: migrate pipeline directory to installable
             | Python package to remove sys.path.insert fragility.
             | File: test_dec1_calibration.py line 37.

VALIDATED (do NOT touch — all 3 models confirmed excellent):
- tail_rows(g9_pass, conform_fallback) logic — correct, do not modify.
- stage_gates call-site substitution at run_fresh.py line 25 — correct, do not modify.
- TestTailRows test suite lines 51–64 — non-vacuous, complete, do not modify.
- M12 Fail Closed improvement — latent fallback-pass path is eliminated, do not revert.
- Tightened TestDec1 assertions lines 46–48 — more precise than prior check, do not revert.

After implementing:
  regression_test.sh must show zero FAILs.
  All six UNVERIFIABLE laws must have corresponding implementation
  and test coverage before this run is considered complete.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: Gemini — Gemini delivered the highest-quality analysis across all four criteria, correctly identifying the feature scope incompleteness as a **critical, show-stopping defect** (scoring it 1/10) rather than a minor observation, explicitly labeling unverifiable laws as UNVERIFIABLE rather than COMPLIANT (preventing a false audit trail), and providing the most precise articulation of the M12 Fail Closed improvement by tracing the exact latent code path that the refactor eliminated. Its depth and accuracy were validated by the Cycle 2 consensus, which adopted its framing wholesale.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — Hard Blocks (production deployment impossible until resolved)**

1. **Implement the full SENTENCE LAW, ONSET/TAIL, SELECTION LOCK, SNAP LIMIT, and CREDITS logic** on this branch, or extract the G9 refactor into a correctly named branch (`refactor-g9-tail-gate`) and submit separately. The diff as-is delivers ~5% of the stated feature scope. *(U1 — unanimous)*

2. **Reclassify all untouched laws as UNVERIFIABLE in the audit trail**, not COMPLIANT. SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, CREDITS, and LAW 22 must carry explicit UNVERIFIABLE status until code implementing them appears in a diff. *(U2 — unanimous)*

**P1 — High Priority (implement before next review cycle)**

3. **Expose `verdict_for` in the diff or document its contract explicitly.** Tests on lines 58 and 64 call `rf.verdict_for()` on the output of `tail_rows`, but the function is not defined or modified in the provided diff. The diff is not self-contained for review. Add an import, stub, or inline definition so the test file is auditable in isolation. *(Grok C1, Gemini C2 — corroborated)*

4. **Rename the branch to reflect actual scope** regardless of which path is chosen in P0. A branch named `pulse-sentence-law` shipping only a G9 gate refactor creates permanent misleading history in git blame and release notes. *(U1 corollary — unanimous)*

**P2 — Medium Priority (implement within this sprint)**

5. **Document the M12 Fail Closed improvement explicitly in the commit message and PR description.** The elimination of the latent path where a fallback outro with passing luma could produce a combined PASS is a meaningful safety improvement that is currently undocumented. Future reviewers will not know the old behavior was a risk without this record. *(Grok C2, Gemini C2 — corroborated)*

6. **Add a regression test for the eliminated latent path.** Write a test case that passes `g9_pass=True, conform_fallback=True` and asserts `outro_locked == "FAIL"`, with an inline comment referencing the prior inline expression it replaced. This guards against reintroduction of the old logic. *(Gemini C1 — depth finding)*

**P3 — Low Priority (address before feature is closed)**

7. **Align the commit title with the diff contents.** The commit message references `pulse-sentence-law` while the change is a G9/outro refactor. This should be corrected in the squash commit message when the branch is merged or renamed. *(Grok C1 — low severity finding)*