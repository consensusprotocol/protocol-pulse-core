# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 04:04
Models: grok, gpt4o, gemini

---

## SCORES

Scores are synthesized from each model's explicit verdict and severity language. No model used a numeric rubric, so scores are derived from qualitative signal (PASS / flag count / severity labels) mapped to a 1–10 scale where 10 = no defects, fully compliant.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (`select_passages.py`) | 10 | 9 | 10 | **10** |
| Law Compliance — SENTENCE LAW | 10 | 10 | 10 | **10** |
| Law Compliance — SELECTION LOCK | 10 | 10 | 10 | **10** |
| Law Compliance — SNAP LIMIT | 10 | 10 | 10 | **10** |
| Law Compliance — ONSET/TAIL | Uncertain | 7 | 10 | **Uncertain** |
| Law Compliance — CREDITS | Uncertain | N/A | 10 | **Uncertain** |
| Law Compliance — LAW 20 / M2 | 10 | 10 | 10 | **10** |
| Law Compliance — M12 FAIL CLOSED | 10 | 10 | 10 | **10** |
| Law Compliance — LAW 22 / v2f | Uncertain | N/A | 10 | **Uncertain** |
| Test Quality | 10 | 9 | 10 | **10** |
| Overall | **9.5** | **9.0** | **10** | **9.5** |

> **Score note:** The 0.5-point haircut on consensus overall reflects three "Uncertain" ratings on laws that the diff does not touch. These are not defects in the changed code — they are audit visibility gaps. The changed code itself is clean.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models converged on the same high-level conclusion: the changed code and new tests are correct, the laws they touch are compliant, and no concrete defects were found in the diff. There is no issue that all three models simultaneously flagged as requiring a fix.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — ONSET/TAIL compliance is unverifiable from the diff (Gemini + GPT-4o)

- **What it is:** The diff covers selection logic only. Neither the diff nor the test files provide evidence that ONSET/TAIL guard requirements are enforced at the selection layer or verified in these tests.
- **File/line:** `pipeline/select_passages.py` — no specific line; absence of check.
- **GPT-4o rating:** LOW severity, suggested adding explicit checks.
- **Gemini rating:** UNCERTAIN — cannot confirm or deny from provided files.
- **Grok position:** Declared COMPLIANT by absence (no changes to onset/tail code, therefore no regression). This is a technically defensible but weaker claim.
- **Consensus action:** **Investigate further.** This is not a regression introduced by this diff. However, the audit surface is incomplete. Before closing the feature, confirm in a separate audit pass that onset/tail enforcement lives somewhere in the pipeline (rendering layer, pre-filter, or a dedicated gate) and is covered by at least one test. If it does not exist, add it.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — Conflict check on line 46 is a correctness fix for a subtle ordering hazard (Gemini only)

- **What it is:** Gemini specifically called out that `(p is first and _conflicts(p, kind))` on line 46 is not just a refactor — it is a correctness fix for a real edge case where a *previous* slot's fallback selection can claim the time window that is the *primary* choice for a *later* slot. Without this check, the later slot's top pick could be used twice.
- **File/line:** `pipeline/select_passages.py` line 46.
- **Assessment:** **Validate and document.** Grok and GPT-4o noted the check exists but did not explain its necessity as clearly. Gemini's framing is the most precise. The corresponding test (`test_a_window_taken_by_a_fallback...`) confirms the scenario is real. **Action:** Add a one-line inline comment on line 46 explicitly naming the hazard ("guard: a prior slot's fallback may have claimed this window") so future readers do not silently remove it thinking it is redundant with the loop-level conflict check.

### U2 — Post-cut duration check prevents "liar window" silent corruption (Gemini only, most precisely)

- **What it is:** Gemini identified that lines 54–59 fix a subtle class of bug where a candidate window's *declared* duration fits the budget but the *actual sentence-locked segment* does not. Without this check, a 12s declared window containing only 9s of valid sentence speech could be passed through, corrupting the clip silently.
- **File/line:** `pipeline/select_passages.py` lines 54–59.
- **Assessment:** **Document explicitly.** All three models noted the check exists; only Gemini named the bug class ("liar candidate"). The test `test_budget_holds_for_the_locked_words` covers it. **Action:** Add a docstring or comment naming the invariant being enforced: "declared window duration is not authoritative; only the duration of the sentence-locked segment is."

### U3 — Test data realism improvement in `test_fresh.py` (Gemini only)

- **What it is:** Gemini flagged that increasing sentence length to 12 words and correctly handling `win_off` offsets in `test_fresh.py` lines 73 and 83 makes tests less likely to produce false positives from coordinate system mismatches.
- **File/line:** `pipeline/test_fresh.py` lines 73, 83.
- **Assessment:** **Accept as-is.** The change is already implemented. Gemini's observation is a validation, not a new action item.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — ONSET/TAIL: COMPLIANT vs UNCERTAIN vs PARTIAL

- **Grok:** COMPLIANT by absence — no changes to onset/tail code, no regression possible.
- **GPT-4o:** PARTIAL — implies compliance but flags lack of explicit checks.
- **Gemini:** UNCERTAIN — cannot verify from provided files.

**Tiebreaker ruling: Gemini and GPT-4o are more precisely correct.** Grok's "compliant by absence" reasoning is valid for regression analysis but insufficient for a law compliance audit. The correct finding is: **this diff does not regress onset/tail behavior, but audit coverage of that law is incomplete for this feature**. The law's status should remain OPEN until a positive assertion (a test or a code path) is located and cited. This is a documentation/traceability gap, not a code defect.

### C2 — CREDITS and LAW 22 / v2f: N/A vs COMPLIANT by absence

- **Grok:** COMPLIANT by absence.
- **GPT-4o:** NOT APPLICABLE.
- **Gemini:** UNCERTAIN.

**Tiebreaker ruling:** All three positions are logically consistent with the actual diff. These laws govern subsystems the diff does not touch. The correct audit-language is **OUT OF SCOPE FOR THIS DIFF** — which is neither a defect nor a compliance claim. No action required.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

1. **`_conflicts` helper function** — correctly centralizes all conflict reasons; logic is sound; do not refactor.
2. **`_build_segment` → post-cut duration check (lines 54–59)** — the fail-closed mechanism is correctly implemented; do not alter the control flow.
3. **M12 FAIL CLOSED implementation** — no path allows silent pass-on-failure; do not introduce any exception-swallowing or default-to-pass logic.
4. **`test_sentence_windows.py` test design** — all three models praised the must-fail/control structure, concrete assertions, and coverage of the three distinct failure modes. Do not reduce test specificity or replace with looser assertions.
5. **`test_fresh.py` coordinate system handling** — the `win_off` fix is correct and makes the suite more robust. Do not revert to the prior test data shape.
6. **Selection lock non-recomputation** — `selection_lock` is set once from `_build_segment` output and never modified. Do not add any code that recalculates expected words after lock.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence | Basis |
|---|---|---|---|
| SENTENCE LAW | ✅ COMPLIANT | High (3/3) | Acoustic pause check proven by `test_rejected_clip_is_replaced_by_the_next_legal_window`; boundary violation causes correct rejection |
| SELECTION LOCK | ✅ COMPLIANT | High (3/3) | Lock set once from `_build_segment`; test line 122 confirms match; no recomputation path |
| SNAP LIMIT | ✅ COMPLIANT | High (3/3) | Cut-point never moved into spoken audio; fallback triggered instead of boundary stretch |
| M12 FAIL CLOSED | ✅ COMPLIANT | High (3/3) | All failure paths (boundary not found, duration out of budget, conflict) result in rejection; no silent pass |
| LAW 20 / M2 | ✅ COMPLIANT | High (3/3) | New duration gate is strictly additive; no threshold loosened |
| ONSET/TAIL | ⚠️ OPEN | Low (0/3 positive assertion) | Not touched by diff; no test visible in provided files; needs traceability confirmation |
| CREDITS | ⬜ OUT OF SCOPE | N/A | Not touched by diff |
| LAW 22 / v2f | ⬜ OUT OF SCOPE | N/A | Not touched by diff |

---

## SECURITY CONSENSUS

No security issues were flagged by any model. The changed code is an internal pipeline selection algorithm operating on structured in-memory data with no I/O, authentication, or external surface area exposed by the diff. Security review is **not applicable to this diff**.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2 or more models:

### WCG-1 — Explicit ONSET/TAIL enforcement is not visible in the selection layer (Gemini + GPT-4o)

The selection pipeline does not contain a visible, tested assertion that selected segments respect onset and tail padding requirements. A world-class implementation would either enforce this at selection time (rejecting candidates whose starts or ends fall within the onset/tail zone) or provide a clear, documented contract that the caller guarantees this invariant before calling `_eligible`. Neither is currently visible in the diff or test suite.

**Gap:** No test proves onset/tail is enforced anywhere in the feature's execution path.
**World-class standard:** Every hard law should have at least one must-fail test that proves rejection when the law is violated.

### WCG-2 — "Liar window" hazard class is undocumented in code (Gemini + GPT-4o, implicit)

Both models noted that the declared-vs-actual duration mismatch is a non-obvious hazard. A world-class codebase would name this invariant in a docstring or comment so that future engineers understand why the post-cut check cannot be removed. Currently the check exists and works, but its purpose is only discoverable by reading the test.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P1 HIGH** | Add inline comment naming the fallback-window-collision hazard: `# guard: a prior slot's fallback may have claimed this window — must conflict-check even the top-ranked candidate` | `pipeline/select_passages.py:46` | unique/gemini | Without this comment the check looks redundant and is a deletion risk in future refactors |
| **P1 HIGH** | Add docstring to the post-cut duration block naming the "liar window" invariant: `# Declared window duration is not authoritative; only the sentence-locked segment duration is binding` | `pipeline/select_passages.py:54–59` | unique/gemini | Same deletion risk; the invariant must be named, not just implemented |
| **P1 HIGH** | Locate or create a test that proves ONSET/TAIL rejection: either find the existing enforcement path and cite it in an audit note, or add a must-fail test with a candidate whose start falls within the onset zone | `pipeline/test_sentence_windows.py` (new test) or docs | majority/gemini+gpt4o | ONSET/TAIL is a named law; its compliance has zero positive evidence in the visible test surface |
| **P2 MEDIUM** | Add `# compliant-by-scope: CREDITS and LAW 22/v2f not touched by this diff` comment to the module header or a companion audit note | `pipeline/select_passages.py` header or audit doc | majority/gemini+gpt4o | Prevents future auditors from reopening these as unknowns and makes the scope boundary explicit |
| **P2 MEDIUM** | Confirm in a brief audit note (or test comment) that ONSET/TAIL enforcement lives in a specific layer (render, pre-filter, or dedicated gate) and is not expected at the selection layer | Audit doc / `test_sentence_windows.py` comment | majority | Closes the traceability gap without necessarily adding a redundant code-layer check |

> **P0 CRITICAL: None.** No model found a correctness defect, compliance violation, or security issue in the changed code.

---

## CYCLE 1 VERDICT

**The code is correct and ready for a second build pass.**

The changed logic in `select_passages.py` is sound. All three models converged independently on a clean verdict for the modified code. The two P1 items are documentation hardening against future regression, not defect fixes. The ONSET/TAIL traceability gap is a pre-existing audit surface issue, not a regression introduced by this diff.

No fundamental rework is required.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
Implement every P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P1 HIGH | Add inline comment naming the fallback-window-collision hazard
        | pipeline/select_passages.py:46
        | Comment text: "# guard: a prior slot's fallback may have claimed this window — must conflict-check even the top-ranked candidate"
        | Why: deletion risk — without the comment this check looks redundant

P1 HIGH | Add docstring/comment naming the "liar window" invariant
        | pipeline/select_passages.py:54–59
        | Comment text: "# Declared window duration is not authoritative; only the sentence-locked segment duration is binding against budget"
        | Why: same deletion risk; invariant must be named, not just implemented

P1 HIGH | Locate or create a must-fail test proving ONSET/TAIL rejection
        | pipeline/test_sentence_windows.py (new test) OR locate existing enforcement path and add an audit-note citation
        | Why: ONSET/TAIL is a named law with zero positive test evidence in the visible surface; traceability gap must be closed

P2 MEDIUM | Add scope comment to module header clarifying CREDITS and LAW 22/v2f are out of scope for this diff
          | pipeline/select_passages.py header
          | Why: prevents future auditors from reopening as unknowns

P2 MEDIUM | Add a comment or audit note confirming which layer (render, pre-filter, or dedicated gate) owns ONSET/TAIL enforcement
          | Audit doc or test_sentence_windows.py header comment
          | Why: closes traceability gap without adding a redundant code-layer check

VALIDATED — do NOT touch these (all 3 models confirmed excellent):
- _conflicts helper function and its logic
- _build_segment → post-cut duration check control flow (lines 54–59)
- M12 FAIL CLOSED control flow (no exception-swallowing, no default-to-pass)
- test_sentence_windows.py test structure, must-fail/control pattern, and concrete assertions
- test_fresh.py win_off coordinate handling and 12-word sentence data
- selection_lock set-once-from-_build_segment pattern (no recomputation after lock)

After implementing:
regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```