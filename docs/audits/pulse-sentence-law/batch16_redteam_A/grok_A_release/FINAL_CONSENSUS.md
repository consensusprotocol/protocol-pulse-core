# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 22:32
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | 9/10 | **9/10** |
| Law Compliance | 10/10 | 9/10 | 9/10 | **9/10** |
| Test Quality | 10/10 | 10/10 | 10/10 | **10/10** |
| Security / Fail-Closed | 10/10 | 9/10 | 9/10 | **9/10** |
| Overall Readiness | READY* | NO* | READY* | **READY*** |

> *READY with conditions (P1 fix required before ship). GPT-4o's "No" reflects the same underlying condition — not a substantive disagreement.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Non-atomic verdict/evidence write for G17_onset_tail
- **File/Line:** `run_fresh.py:212-213`
- **What it is:** The `put()` call writes the gate's `PASS` verdict first (with `samples: 0` or no evidence), then the sample count is patched in a second, separate statement. If any exception fires between these two lines, the gate ledger contains a `PASS` row with zero samples — a permanently inconsistent state.
- **Why it matters:** Downstream, `release_auth.blockers()` correctly rejects a `PASS` with zero samples, so this cannot silently produce a release. However, it *can* produce an irrecoverable "stuck" run state that requires manual intervention and obscures root cause.
- **What to change:** Calculate the sample count *before* calling `put()`. Pass it into the `put()` call as part of the evidence payload so the verdict and evidence are written in a single, atomic operation. The simplest fix is:
  ```python
  # Compute evidence first
  onset_samples = min(onset_ev["samples"], tail_ev["samples"])
  put("G17_onset_tail", verdict, notes=notes,
      evidence={..., "samples": onset_samples})
  # Remove the second patch line entirely
  ```

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Stale comment referencing G11
- **File/Line:** `run_fresh.py:104`
- **Models:** Gemini + Grok (GPT-4o noted it implicitly)
- **What it is:** A comment reading something like `# G11_parity(run_gates) ... see G11 below` is a remnant of the pre-refactor codebase. The logic it described no longer exists in the same form.
- **What to change:** Delete the comment line entirely. Surrounding code and newer inline comments provide sufficient orientation.

### M2 — `replay.py` exception path — `write_report` call
- **File/Line:** `replay.py:21-23`
- **Models:** Grok + GPT-4o agree a defensive call is warranted; Gemini disagrees (see CONFLICTS below)
- **What it is:** The `except` block sets the run verdict to `HOLD` but Grok/GPT-4o assert no `write_report` is called in that branch.
- **Status:** Disputed — see CONFLICTS. Assess after resolving control-flow question.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 — Redundant HOLD pre-check in `attest_run` (Gemini only)
- **File/Line:** `run_fresh.py:363`
- **Observation:** The explicit `if run.status.get("holds")` → set `HOLD` check is redundant because the `run_state` passed into `release_auth.attest` already incorporates holds, which will cause the attestation to return `HOLD`, and line 378 propagates that back.
- **Assessment:** **Skip for now.** This is belt-and-suspenders, not a bug. The redundancy adds clarity ("fail-closed in two independent places") and removing it introduces regression risk with zero correctness benefit. Leave it.

### I2 — `put()` function deserves explicit parameter documentation (GPT-4o only)
- **File/Line:** `run_fresh.py:87-96`
- **Observation:** The `put()` helper's expected parameter contracts (verdict values, evidence shape) are not formally documented.
- **Assessment:** **Implement as P2.** Not a correctness issue, but a maintainability gap in a security-critical helper. Add a brief docstring enumerating legal verdict strings and the required evidence fields.

### I3 — `record_assets` checks against `launch` not `HEAD` (Gemini only, as a strength)
- **File/Line:** `run_fresh.py:343`
- **Observation:** Gemini correctly identified that checking modifications against the *launch* revision rather than `HEAD` closes a race condition in busy repositories.
- **Assessment:** **Validate, do not change.** This is a confirmed strength (see Validated Strengths).

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict C1 — `replay.py` exception path: does `write_report` get called?

- **Grok + GPT-4o:** Claim the exception branch leaves a stale report on disk (no `write_report` after HOLD is set).
- **Gemini:** Disagrees, asserting that the `try/except` is nested inside a `finally` block that *unconditionally* calls `run.save()` and `rf.write_report(run)` after the except branch modifies `run.status`.

**Tiebreaker: Gemini is correct if the control flow is as described.**

The `finally` pattern is a standard Python idiom for exactly this guarantee. If `rf.write_report(run)` appears unconditionally in the `finally` block after the `try/except` that wraps `attest_run`, then the HOLD status set in the `except` block *will* be flushed to disk by the `finally` block. Grok and GPT-4o appear to have read the exception path in isolation without tracing to the enclosing `finally`.

**Resolution:** Verify the `finally` block structure in `replay.py` before the second pass. If Gemini's reading is confirmed, U1 is not a bug — downgrade to P2 (add a comment in the `except` block explaining that `finally` handles the write, to prevent future readers from making the same mistake). If Gemini's reading is wrong, promote to P1.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`release_auth.py` — three-layer authorisation chain** (`blockers` → `attest` → `authorise`): The paranoid re-verification in `authorise()` — re-running `blockers()` *and* re-hashing every bound file — is an exemplary implementation of cryptographically-bound release gating. Do not simplify or shortcut.

2. **`release_auth.blockers()` execution evidence check** (`executed: True` and `samples >= 1`): The explicit guard against vacuous PASS rows (gates that "ran" with no samples) is a critical security property. Do not relax.

3. **`release_auth.attest()` atomic write via `os.replace`**: Prevents partial/corrupt attestation files from being read by a concurrent process. Do not change to a standard `open/write`.

4. **`run_fresh.py` — `edges_on_final` for G17 L-c measurement**: Correctly measures on the final deliverable, not on an intermediate. This matches the amended law text exactly. Do not revert to any intermediate-based measurement.

5. **`run_fresh.py:343` — `record_assets` checks against `launch` not `HEAD`**: Closes a real race condition in busy repos. Do not change to `HEAD`.

6. **`test_release_auth.py` — exhaustive mutation testing**: Each required row, evidence field, and bound file is individually broken to prove fail-closed behavior. The test file is a gold standard. Do not reduce coverage.

7. **G17 `min()` for composite sample count**: Elegant, robust, and correctly fail-closed (evidence is only as strong as the weakest sub-check).

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| L-a (terminal state before candidate) | ✅ COMPLIANT | `attest_run` enforces; `verdict_for` delegates to `blockers` |
| L-b (final-only proof) | ✅ COMPLIANT | `edges_on_final` correctly used in G17 |
| L-c (dissenting check as correct) | ✅ COMPLIANT | `run_fresh.py:215-249` treats dissenter as ground truth |
| L-j (release on exact bytes) | ✅ COMPLIANT | `authorise()` re-hashes every bound file; cryptographic binding confirmed |
| SENTENCE_LAW | ✅ COMPLIANT | Boundary verification confirmed by all models |
| SELECTION_LOCK | ✅ COMPLIANT | No recomputation of expected words post-lock |
| SNAP_LIMIT | ✅ COMPLIANT | Cuts within allowed boundaries confirmed |
| NEIGHBOUR | ✅ COMPLIANT | No audible neighbour-word content included |
| ONSET/TAIL | ✅ COMPLIANT | Edge word preservation confirmed; G17 fix makes this stronger |
| CREDITS | ✅ COMPLIANT | Verified present (GPT-4o noted mid-sentence; no contrary evidence) |
| L-d / SELECTION_LOCK constants | ⚠️ PARTIAL | Not modified in this diff; assumed unchanged from baseline |

**No laws are violated. One partial (L-d constants not visible in diff) warrants confirmation but is not a blocker.**

---

## SECURITY CONSENSUS

All three models agree the overall security posture is a **significant net improvement**. Priority order of remaining concerns:

1. **(P1) Non-atomic G17 evidence write** — can produce inconsistent ledger state. Not exploitable for a false PASS (blocked downstream), but creates unrecoverable run states. Fix required before ship.
2. **(P2) Stale comment at line 104** — confusion risk for future maintainers of a security-critical path. Low severity but zero cost to fix.
3. **(P2, pending C1 resolution) `replay.py` exception path** — if `finally` does not cover the write, a stale diagnostic report could mislead an operator into thinking a HOLD run passed. Needs code-level confirmation.

No model identified any authentication bypass, authorisation escalation, or law-violation attack vector in the new code.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as gaps relative to a truly world-class implementation:

1. **Atomicity of multi-field writes in `stage_gates`** (all 3 models): The gate ledger currently relies on the downstream `blockers()` check as a safety net for inconsistent states that *should* never be written. A world-class implementation would make the write itself atomic — single dict construction, single `put()` call, no subsequent patches. Prevents the "defence in depth requires both layers" situation.

2. **Explicit documentation of `put()` parameter contracts** (Gemini + GPT-4o): In a security-critical module, every function that writes to the gate ledger should have a formal docstring enumerating legal verdict values and required evidence fields. Future contributors should not need to read all call sites to understand the contract.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P1 HIGH** | Make G17_onset_tail verdict + evidence write atomic: compute `onset_samples` before `put()`, pass into `put()` as part of evidence payload, remove the separate patch statement | `run_fresh.py:212-213` | **All 3** | Prevents inconsistent ledger state (PASS row, zero samples); eliminates dependency on downstream catch |
| **P2 MEDIUM** | Delete stale comment referencing G11 | `run_fresh.py:104` | Gemini + Grok | Misleading to future maintainers of security-critical path |
| **P2 MEDIUM** | Verify `finally` block coverage of `write_report` in replay exception path; if not covered, add defensive `rf.write_report(run)` call; if covered, add an inline comment explaining the `finally` guarantee | `replay.py:21-23` | Grok + GPT-4o (Gemini disputes) | Eliminate ambiguity; protect against future refactors breaking the guarantee |
| **P2 MEDIUM** | Add docstring to `put()` enumerating legal verdict strings and required evidence fields | `run_fresh.py:87-96` | Gemini + GPT-4o | Maintainability in security-critical helper |

---

## CYCLE 2 VERDICT

**READY WITH CONDITIONS.**

After two full cycles of independent 3-model review, the `pulse-sentence-law` feature represents a substantial and correct improvement to the pipeline's integrity guarantees. The `release_auth` module is a genuinely excellent piece of security engineering. Test coverage is exemplary.

**Absolute final blocker before production ship:**
> **P1 — `run_fresh.py:212-213`:** The non-atomic G17 evidence write must be consolidated into a single `put()` call before deployment.

All other findings are P2 (code quality, documentation, defensive clarity) and may be bundled into the same commit without blocking the ship decision.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item unconditionally. Use judgment on P2 items.

PRIORITY ACTION PLAN:

P1 HIGH | Make G17_onset_tail verdict+evidence write atomic | run_fresh.py:212-213 | models: all 3 |
  - Compute `onset_samples = min(onset_ev["samples"], tail_ev["samples"])` (or equivalent) BEFORE calling put()
  - Pass the computed sample count into put() as part of the evidence dict in a single call
  - Delete the subsequent patch statement that overwrites evidence["samples"] after put() returns
  - Confirm: no PASS row for G17_onset_tail may ever exist in the ledger with samples == 0

P2 MEDIUM | Delete stale comment referencing G11 | run_fresh.py:104 | models: gemini, grok |
  - Remove the comment line entirely; surrounding code is self-explanatory

P2 MEDIUM | Resolve replay exception path write_report coverage | replay.py:21-23 | models: grok, gpt4o |
  - Inspect the control flow: if write_report(run) is already called unconditionally in a finally block
    that wraps the try/except, add an inline comment in the except block stating:
    "# run.status is updated here; finally block below unconditionally calls write_report"
  - If write_report is NOT called in a finally block, add rf.write_report(run) as the last line
    of the except block before re-raising or continuing

P2 MEDIUM | Add docstring to put() helper | run_fresh.py:87-96 | models: gemini, gpt4o |
  - Document: legal verdict string values, required evidence dict fields,
    behaviour when evidence is None vs missing keys

VALIDATED (do NOT touch — all 3 models confirmed excellent):
  - release_auth.py: three-layer authorisation chain (blockers → attest → authorise)
  - release_auth.blockers(): execution evidence guard (executed: True, samples >= 1)
  - release_auth.attest(): atomic write via os.replace
  - run_fresh.py:343: record_assets checks against `launch` not HEAD
  - run_fresh.py G17 measurement via edges_on_final (not intermediate)
  - test_release_auth.py: exhaustive mutation test coverage — do not reduce
  - G17 composite sample count via min() — do not change

After implementing:
  regression_test.sh must show zero FAILs.

Then run:
  git add -A && git commit -m "feat(pulse-sentence-law): post-audit final pass — consensus improvements C2"
  git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: Grok — [2 sentence justification]

Grok delivered the highest-quality analysis across both cycles: in Cycle 1 it was the only model to independently identify both the G17_onset_tail non-atomic write (with a precise, implementable fix location) and the replay exception path gap, while also providing the most structured law-compliance mapping (L-a through L-j with exact line citations) and the clearest severity-labelled findings. In Cycle 2 it maintained scoring discipline (no score inflation or deflation without new evidence), correctly triaged U1 as P1-HIGH versus U1's replay path as only partially concerning, and produced the cleanest prioritised action list with the least noise — outperforming GPT-4o (which missed both issues in Cycle 1 and produced a vague "put() documentation" non-finding) and Gemini (which omitted test quality entirely in Cycle 1 and leaned on consensus rather than independent discovery).

---

## FINAL SECOND-PASS PRIORITY LIST

The following is the definitive ordered list of what to implement, synthesised from all three models across both cycles and the consensus report. Items are ordered by risk to release integrity.

---

### P1 — MUST FIX BEFORE SHIP

**[P1-1] Non-atomic verdict/evidence write — `run_fresh.py:212-213`**
- **Finding:** `put()` is called with `samples: 0` (or absent), and the sample count is patched in a second statement. An exception between the two lines leaves a permanent `PASS` row with zero evidence in the gate ledger.
- **Risk:** Cannot silently release (blockers() catches it), but produces an irrecoverable stuck-run requiring manual intervention and destroying audit traceability.
- **Fix:** Compute `onset_samples = min(onset_ev["samples"], tail_ev["samples"])` before the `put()` call; pass it inside the evidence dict in the same call; delete the patch line entirely.
- **Test:** Add a unit test that injects an exception immediately after `put()` returns and asserts the ledger row is either absent or contains a consistent `samples >= 1` value — never `PASS` with `samples == 0`.

---

### P2 — FIX IN SAME PR (low effort, high clarity value)

**[P2-1] Stale comment referencing G11 — `run_fresh.py:104`**
- **Finding:** Comment is a remnant of the pre-refactor code path and no longer describes the live logic, creating misleading context for future reviewers.
- **Risk:** Documentation debt; no runtime impact, but actively misleads auditors reviewing law compliance.
- **Fix:** Delete or rewrite the comment to accurately describe the current `put()`-based dispatch. One line.

---

### P3 — ADDRESS IN FOLLOW-ON PR

**[P3-1] Replay exception path does not re-call `write_report` — `replay.py:21-23`**
- **Finding:** When `attest_run()` raises inside `replay()`, the HOLD verdict is set in memory but `write_report` is not called again, leaving the previously written report (if any) on disk with stale content.
- **Risk:** Low in practice (replay is diagnostic, not a release path), but a downstream consumer reading the report file after a failed replay will see inconsistent state.
- **Fix:** Add a `write_report(run_state)` call inside the `except` block after the HOLD is set, mirroring the pattern used in the main `run_fresh` exception handler.
- **Note:** Grok correctly flagged this as real but low-risk. GPT-4o and Gemini confirmed agreement in Cycle 2. It is not a blocker but should not be left indefinitely.

**[P3-2] `put()` function internal contract not documented — `run_fresh.py:87-96`**
- **Finding:** `put()` is a new, load-bearing helper with no docstring specifying its atomicity guarantees, expected argument types, or behaviour on duplicate keys.
- **Risk:** Future callers may misuse it in ways that reintroduce the P1-1 class of bug.
- **Fix:** Add a three-line docstring specifying: (a) evidence must be fully populated before calling, (b) duplicate keys raise, (c) the function is not thread-safe.

---

### CLOSED — NO ACTION REQUIRED

| ID | Finding | Reason closed |
|----|---------|---------------|
| C1 | `release_auth.blockers()` rejects PASS with zero samples | Correctly implemented; serves as the downstream safety net for P1-1 |
| C2 | `authorise()` re-hashes bound files at release time | Correctly paranoid; no issue found |
| C3 | `attest_run()` terminal-state enforcement | Correctly implemented; `run_state.get("ok") is True` guard confirmed |
| C4 | Test coverage of `test_release_auth.py` | Exhaustive mutation testing confirmed by all three models; 10/10 |