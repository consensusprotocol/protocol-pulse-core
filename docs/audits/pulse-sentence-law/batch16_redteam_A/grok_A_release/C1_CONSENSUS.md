# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:29
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | 9/10 | **9/10** |
| Law Compliance | 9/10 | 9/10 | 8/10 | **9/10** |
| Test Quality | 10/10 | 9/10 | 10/10 | **10/10** |
| Security / Fail-Closed | 10/10 | 9/10 | 9/10 | **9/10** |
| Overall Readiness | 9/10 | 8/10 | 8/10 | **READY** |

> Score derivation: Gemini and Grok explicitly flagged only LOW items; GPT-4o mislabeled correct behavior as HIGH/MEDIUM issues. Consensus deflates GPT-4o's overall score accordingly.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** No single defect was identified by all three models as an actionable bug requiring a code change. All three converged on the same architectural observation — the fail-closed design is correct — but each flagged *different* minor issues. The absence of unanimous defects is itself a strong signal of code quality.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — G17_onset_tail evidence write ordering (Grok + Gemini)
- **What:** `run_fresh.py:212` — The G17 onset/tail evidence is written to the ledger *after* the `put()` call rather than being bundled atomically inside it. If an exception fires between `put()` and the evidence write, the gate record lands with a `PASS` verdict but no evidence. `release_auth.blockers()` would then correctly reject it (evidence check at line 604–611), but the inconsistency creates a confusing diagnostic state.
- **File/Line:** `run_fresh.py:212`
- **Fix:** Move the `_samples` / evidence population into the `put()` call site, or inside `put()` itself, so verdict and evidence are written atomically. If `put()` accepts an `evidence=` kwarg, pass it there.

### M2 — Stale comment referencing G11 (Gemini + implicit in Grok's structural review)
- **What:** `run_fresh.py:104` — Comment `G11_parity(run_gates) ... see G11 below` predates the refactor and no longer accurately describes the surrounding logic.
- **File/Line:** `run_fresh.py:104`
- **Fix:** Update or remove the stale comment so future readers are not misled.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — `replay` exception path does not call `write_report` (Grok only)
- **What:** `replay.py:21-23` — When `attest_run` raises, the except block sets the verdict to HOLD but never calls `write_report` a second time. The on-disk report therefore still carries whatever partial state existed before the exception.
- **Assessment:** **Investigate further.** If `replay` is ever called in a context where the report file is consumed downstream before the caller inspects the return value, the stale file is a real (if unlikely) hazard. If `replay` is always a diagnostic-only path where the caller exclusively trusts the return value, this is cosmetic. Recommend adding a defensive `write_report` call in the except block to close the gap.
- **File/Line:** `replay.py:21-23`
- **Action:** P2 — add `write_report(run, hold_verdict)` in the except branch.

### U2 — `record_assets` checks against `launch` revision, not `HEAD` (Gemini only)
- **What:** `run_fresh.py:343` — Gemini noted this as a *positive* correctness point (prevents race with a busy repo), but it is worth explicitly documenting *why* `launch` is used, since future maintainers may "fix" it to `HEAD` and introduce the race.
- **Assessment:** **Implement as documentation only.** Add an inline comment explaining that `launch` is intentional to avoid HEAD drift during a long gate run.
- **File/Line:** `run_fresh.py:343`
- **Action:** P2 — add explanatory comment.

### U3 — GPT-4o's HIGH/MEDIUM verdicts are misclassified (GPT-4o only, negative finding)
- **What:** GPT-4o labelled correct, intended behavior (HOLD on missing attestation; HOLD propagation in `attest_run`) as HIGH and MEDIUM issues requiring attention, then immediately stated "Fix: None needed." This is internally contradictory and produces noise.
- **Assessment:** **Skip.** GPT-4o's severity labels for Q4 items 1 and 2 are not actionable. The underlying code behavior is correct as confirmed by both Gemini and Grok. No change needed.

### U4 — L-d (PROTECTED PREVIEW) cannot be verified from this diff (Gemini only)
- **What:** Gemini explicitly flagged that L-d compliance cannot be confirmed because the law's implementation is outside the diff scope.
- **Assessment:** **Investigate further.** This is the only law without a "COMPLIANT" determination from any model. Even if the implementation is in a separate file, a cross-reference check should be documented.
- **Action:** P1 — explicitly verify L-d compliance in the next review pass and add a note to `release_auth.py` or the gospel citing where L-d is enforced.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Severity of GPT-4o's Q4 findings vs. Grok/Gemini
- **GPT-4o:** Flagged line 683 as HIGH severity.
- **Grok + Gemini:** Flagged only LOW issues; found line 683 (and surrounding `authorise()`) to be correct and robust.
- **Tiebreaker: Grok and Gemini are correct.** GPT-4o's Q4 section contradicts itself — it identifies "correct behavior" as HIGH severity then says "Fix: None needed." The paranoid re-verification in `authorise()` is a deliberate strength, not a defect. Discard GPT-4o's severity labels for Q4 items 1 and 2.

### C2 — Whether L-c implementation is complete
- **GPT-4o:** States COMPLIANT at lines 215-249 without noting the specific `edges_on_final` detail.
- **Gemini:** Explicitly praises `edges_on_final` as a *crucial correctness fix* over the prior string-prefix approach.
- **Grok:** Confirms COMPLIANT but does not elaborate on `edges_on_final`.
- **Tiebreaker: Gemini's characterization is most precise.** The shift to `edges_on_final` is the mechanically significant change here. No conflict on compliance status — all agree it is compliant — but Gemini's depth is authoritative.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **`release_auth.py` architecture** — The fail-closed, inventory-first, evidence-required, paranoid re-verification design of `blockers()` / `attest()` / `authorise()` is unanimously praised. Do not restructure.

2. **`put()` helper in `stage_gates()`** — The refactor from string-prefix parsing to structured dict storage is unanimously recognized as a correctness and maintainability improvement. Do not revert.

3. **`verdict_for()` delegating to `release_auth.blockers()`** — Removes fragile string-prefix logic. All models confirmed this is correct. Do not alter.

4. **`test_release_auth.py` test suite** — All models rated it excellent. The systematic mutation testing of every required row, evidence field, bound file, and run state is thorough and non-vacuous. Do not reduce coverage.

5. **`attest_run()` terminal-state enforcement** — The final reconciliation at line 377 (ensuring run status can never disagree with attestation verdict) is correct and important. Do not change.

6. **Atomic `os.replace` in `attest()`** — Good practice, unanimously noted. Do not change.

7. **`TestBytes` covering pre- and post-attestation file mutation** — Proving L-j at the byte level is correctly tested. Do not remove.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence |
|---|---|---|
| L-a SIGN-OFF NAMES ALL | ✅ COMPLIANT | High (all 3 models) |
| L-b EDGE WORDS WHOLE | ✅ COMPLIANT | High (all 3 models) |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | ✅ COMPLIANT | High — `edges_on_final` correctly used |
| L-d PROTECTED PREVIEW | ⚠️ UNVERIFIED | Cannot confirm from diff; must check separately |
| L-e through L-i, L-k | ✅ ENFORCEMENT COMPLIANT | Mechanism is correct; underlying implementations outside diff |
| L-j RELEASE IS AUTHORISED ON THESE BYTES | ✅ COMPLIANT | High — primary focus of diff |
| LAW 20 / M2 (thresholds constant) | ✅ COMPLIANT | High (all 3 models) |
| M12 FAIL CLOSED | ✅ COMPLIANT | High — entire architecture built on this |
| LAW 22 (v2f reference) | ✅ COMPLIANT | High (all 3 models) |
| SENTENCE LAW | ✅ COMPLIANT | High (all 3 models) |
| SELECTION LOCK | ✅ COMPLIANT | High (all 3 models) |
| SNAP LIMIT | ✅ COMPLIANT | High (all 3 models) |

**Single outstanding gap: L-d.** Assign ownership and document compliance location before Cycle 2 closes.

---

## SECURITY CONSENSUS

| Issue | Models | Priority |
|---|---|---|
| Atomicity gap: evidence written outside `put()` leaves window where PASS verdict exists with no evidence | Grok + Gemini | Medium |
| Replay exception path leaves stale on-disk report | Grok | Low |
| L-d compliance location undocumented | Gemini | Low-Medium |

No model identified injection, privilege escalation, path traversal, or cryptographic weaknesses. The re-hashing in `authorise()` is the correct mitigation against post-gate file substitution, and all models confirmed it works correctly.

---

## WORLD-CLASS GAP CONSENSUS (2+ models mentioned)

### WCG-1 — Atomicity of evidence + verdict write (Grok + Gemini)
A truly world-class audit pipeline would make it structurally impossible to record a verdict without simultaneously recording its evidence. The current design relies on call-site discipline (write evidence after `put()`). Making `put()` accept evidence as a required parameter — and refuse to write without it — would eliminate the gap by construction, not convention.

### WCG-2 — Stale documentation / comments lagging implementation (Gemini + Grok)
Both models independently noted that inline documentation has not kept pace with the refactor (the G11 comment, the `launch` vs `HEAD` choice). World-class pipelines treat stale comments as bugs. A documentation linting pass should be part of the standard gate suite.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Atomic evidence+verdict write in put()       | run_fresh.py:87-96,212     | models: grok+gemini   | PASS verdict can exist on disk with no evidence if exception fires mid-sequence; blockers() catches it but creates diagnostic confusion and a narrow integrity gap

P1 HIGH     | Verify and document L-d compliance location  | release_auth.py + gospel   | models: gemini        | Only law with no confirmed implementation location; must be documented before this audit cycle closes

P1 HIGH     | Add write_report() in replay except branch    | replay.py:21-23            | models: grok          | Stale on-disk report after attest_run exception could mislead downstream consumers of the report file

P2 MEDIUM   | Update stale G11 comment                      | run_fresh.py:104           | models: gemini+grok   | Comment predates refactor; misleads future maintainers

P2 MEDIUM   | Document launch-vs-HEAD intent                | run_fresh.py:343           | models: gemini        | Future maintainer may "fix" to HEAD and introduce repo-race; one line of comment prevents this

P2 MEDIUM   | Make evidence a required param to put()       | run_fresh.py:87-96         | models: grok+gemini   | Structural enforcement > call-site discipline; prevents the P0 gap by construction in future gates
```

---

## CYCLE 1 VERDICT

**READY for a second build pass.** The code is architecturally sound. No model identified a defect that would allow an incorrect audio segment to be authorized for delivery, which is the central safety requirement. The P0 item is a narrow atomicity gap that `release_auth.blockers()` already catches defensively — it does not represent a live release risk today, but it must be closed before this code handles production volume. All P1 and P2 items are well-scoped and non-invasive.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models (Gemini 2.5 Pro,
GPT-4o, Grok-3) across 1 cycle. Implement every P0 and P1 item from the
consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Atomic evidence+verdict write in put()
  File: run_fresh.py:87-96,212
  Change: Extend the put() helper to accept an evidence= kwarg (or a
  required samples= int). Do not return until verdict AND evidence are
  written to the ledger in the same operation. The post-put evidence
  assignment at line 212 must move inside put(). If put() cannot receive
  evidence atomically in a single call, restructure stage_gates() so the
  gate computes evidence first, then calls put() once with both.
  Why: A PASS verdict can currently land on disk without evidence if an
  exception fires between put() and the evidence write. blockers() catches
  this defensively, but the gap must be closed by construction.

P1 HIGH | Verify and document L-d (PROTECTED PREVIEW) compliance location
  File: release_auth.py header comment + PULSE_SENTENCE_LAW_GOSPEL.md
  Change: Locate the file/function that enforces L-d. Add a one-line
  comment in release_auth.py (near the REQUIRED gate list) citing where
  L-d is enforced (e.g., "L-d enforced in preview_guard.py:protect()").
  Update the gospel's compliance table with the same pointer.
  Why: L-d is the only law with no confirmed implementation location in
  this audit. It must be documented before the cycle closes.

P1 HIGH | Add write_report() in replay() except branch
  File: replay.py:21-23
  Change: In the except block that sets verdict=HOLD, call write_report()
  (or equivalent) with the HOLD verdict immediately after setting it,
  before re-raising or returning. This ensures the on-disk report always
  reflects the current in-memory state.
  Why: An exception in attest_run() leaves the on-disk report in a stale
  partial state. Any downstream consumer that reads the file (not the
  return value) sees incorrect data.

P2 MEDIUM | Update stale G11 comment
  File: run_fresh.py:104
  Change: Rewrite or remove the comment referencing G11_parity. It
  predates the put() refactor and no longer accurately describes the
  surrounding logic.

P2 MEDIUM | Document launch-vs-HEAD intent in record_assets
  File: run_fresh.py:343
  Change: Add an inline comment: "Compare against launch revision, not
  HEAD, to avoid false-dirty reads if another commit lands during a long
  gate run."

P2 MEDIUM | Enforce evidence as a structurally required param in put()
  File: run_fresh.py:87-96
  Change: Once P0 is implemented, consider making the evidence/samples
  parameter non-optional (no default=None). Any gate that calls put()
  without evidence should fail loudly at development time, not silently
  at runtime.

VALIDATED — do NOT touch (all 3 models confirmed excellent):
  - release_auth.py: blockers() / attest() / authorise() architecture
  - run_fresh.py: put() helper structure and verdict_for() delegation
  - run_fresh.py: attest_run() terminal-state reconciliation (line 377)
  - run_fresh.py: L-c implementation using edges_on_final (lines 235-247)
  - release_auth.py: atomic os.replace in attest()
  - test_release_auth.py: entire test suite (TestPassingRun, TestInventory,
    TestEvidence, TestBytes, TestPackAndRun) — do not reduce coverage
  - story_ledger tests: authorised/status field coverage

After implementing:
  regression_test.sh must show zero FAILs.
  Confirm blockers() rejects a gate record with verdict=PASS and samples=0.
  Confirm replay() on-disk report matches return value after attest failure.
  Confirm L-d compliance is documented with a file:function pointer.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements C1"
git push origin combo-letterbox-quoteonly-v2
```