# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-12 02:32
Models: gpt4o, gemini (+1 failed — Grok-3 budget exceeded)

---

## SCORES
| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | 8.5/10 | 9.0/10 | N/A  | 8.7/10    |
| Law Compliance  | 8.5/10 | 9.0/10 | N/A  | 8.7/10    |
| Test Coverage   | 9.0/10 | 9.0/10 | N/A  | 9.0/10    |
| Security        | 8.0/10 | 8.0/10 | N/A  | 8.0/10    |
| Overall         | 8.7/10 | 9.0/10 | N/A  | 8.8/10    |

> **Note on Grok failure:** Scores are derived from two models only. Consensus figures are averages of Gemini and GPT-4o. Where the two models diverge significantly, Gemini's deeper Cycle 2 analysis is weighted more heavily due to its discovery of a novel P1 bug.

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — Scope Discrepancy: D1–D6 Editorial Fixes Missing
- **What it is:** The feature is named `pulse-sentence-law`, the branch is `combo-letterbox-quoteonly-v2`, and the stated feature context implies delivery of both the GPU infrastructure law (L-r) and user-facing editorial defect fixes (D1–D6, including letterboxing). The diff contains **only** the GPU/L-r infrastructure layer. The editorial fixes are entirely absent.
- **File/Line:** N/A — feature scope / project management
- **What to change:** The project lead must formally resolve this before the branch merges. Either: (a) rename the branch and explicitly declare this an infrastructure-only delivery, closing/deferring D1–D6 tickets; or (b) add the missing D1–D6 editorial fixes to this branch before it is considered shippable. This is not optional — both models flagged this as a mandatory gate.

### U2 — `BaseException` for `Gpu0Stop` is Correct and Must Not Be Changed
- **What it is:** Both models confirmed that `Gpu0Stop` correctly inherits from `BaseException` rather than `Exception`. This is intentional and architecturally sound — it prevents application-level `except Exception:` clauses from silently catching infrastructure failures.
- **File/Line:** `pipeline/gpu0.py`, line ~990
- **What to change:** Nothing. This is a validated strength (see Validated Strengths). Listed here because both models noted it explicitly as a correctness checkpoint.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above also qualify as majority findings. No additional majority findings exist beyond U1 above that are not already elevated to Unanimous status.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — Logic Flaw in `gpu0.held()` — **GEMINI ONLY**
- **File/Line:** `pipeline/gpu0.py`, lines 1043–1054
- **What Gemini found:** The `held()` function attempts a non-blocking exclusive `fcntl.flock` to determine if the current process already holds the lease. This is logically incorrect. The call succeeds in **two** distinct situations:
  1. The current process already holds the lock on that file description ✅ (intended)
  2. The file is completely unlocked ❌ (not intended — produces a false `True` and acquires the lock as a silent side effect)
- **Impact per Gemini:** In case 2, `lease()` sees `held() == True` and skips the locking step entirely. The calling process then proceeds to use GPU0 **without actually holding the lease**. This silently breaks the "ONE OWNER" guarantee for standalone script invocations (e.g., `preflight.py`, `backtest.py`) when no prior process has acquired the lease file.
- **GPT-4o assessment:** Did not catch this in either cycle.

**Synthesis verdict: IMPLEMENT — this is a P1 bug.**

The logic is demonstrably wrong. `flock(LOCK_EX | LOCK_NB)` succeeding does not mean "I already hold it" — it means "I can take it." The correct check is to inspect whether the lease file contains the current process's PID (or an ancestor PID), or to use the `holder()` function's approach (which correctly distinguishes locked/unlocked states). The side effect of silently acquiring the lock without entering the full `lease()` bookkeeping path is dangerous.

**Recommended fix:** Rewrite `held()` to:
1. Call `holder()` (or equivalent) to get the PID that currently holds the lock.
2. Return `True` only if that PID matches the current process or one of its known ancestors.
3. Ensure no lock acquisition occurs as a side effect of calling `held()`.
4. Add a test: standalone process calls `lease()` on an **existing but unlocked** lease file and confirm it correctly acquires the lock and completes with ONE OWNER semantics.

### UI2 — Documentation and Comment Quality — **GPT-4o ONLY**
- **What GPT-4o noted:** Code is well-documented with clear inline comments on the lease mechanism and model-loading flow, contributing to maintainability.
- **Synthesis verdict: SKIP — no action required.** This is an observation of a strength, not a deficiency. No change needed.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Production Readiness

| Model   | Verdict                  |
|---------|--------------------------|
| Gemini  | **No** — P1 bug blocks ship |
| GPT-4o  | **Yes, with conditions** — scope clarification only |

**Tiebreaker: Gemini is correct.**

GPT-4o's "Yes with conditions" verdict was formed without awareness of the `gpu0.held()` bug (which Gemini discovered in Cycle 2). Once that P1 bug is on the table, the correct verdict is **No**. A silent failure of the core "ONE OWNER" locking mechanism is not a "condition" — it is a blocker. GPT-4o's overall confidence in the codebase is otherwise reasonable, but its production-readiness assessment must be revised downward in light of Gemini's finding.

### C2 — Overall Score

| Model   | Overall |
|---------|---------|
| Gemini  | 8.7/10  |
| GPT-4o  | 9.0/10  |

**Tiebreaker:** Consensus is **8.7/10**, weighted toward Gemini's post-bug-discovery assessment. The 0.3-point gap reflects GPT-4o's pre-bug-discovery baseline; with the `held()` bug now on record, 8.7 is the correct floor.

---

## VALIDATED STRENGTHS (all models agree — do NOT touch in the second pass)

1. **`BaseException` for `Gpu0Stop`** — Architecturally correct and critical. Do not change inheritance hierarchy. The separation of infrastructure failures from application-layer exceptions is a design cornerstone.

2. **`fcntl.flock` as the lease primitive** — Both models confirmed this is an appropriate, standard, and correct choice for enforcing single-process ownership at the OS level.

3. **`_attempts()` bounded self-heal in `run_fresh.py`** — The implementation correctly matches L-r(3): exactly one OOM retry after full resource release (`gpu0.release_all`), second failure converts to Hold, non-OOM `Gpu0Stop` converts to Hold without retry. Do not alter this logic.

4. **`swap_to()` as the single entry point for model loading** — Both models confirmed this correctly enforces "ONE MODEL AT A TIME" and correctly centralizes unload logic for `_resident` and Ollama models. Do not add alternative loading paths.

5. **Test suite for `test_gpu0.py`** — Described as thorough and comprehensive by both models. The test for `BaseException` behavior (line 1671) and model swap behavior (line 1635) are especially well-constructed. Do not remove or weaken these tests; only add to them.

6. **`GpuOOM` propagation fix in `transcript_store.py`** — The fix ensuring CUDA OOM during transcription propagates as `GpuOOM` rather than being caught as `E-FAIL-052` is correct and must remain. Do not revert.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| **L-r ONE OWNER / ONE MODEL AT A TIME** | ⚠️ PARTIAL — P1 bug | `swap_to()` and `_attempts()` are compliant; however the `held()` bug means standalone processes can bypass the lease, creating a silent compliance hole in L-r(1) |
| **L-r(3) BOUNDED SELF-HEAL** | ✅ COMPLIANT | `_attempts()` correctly implements exactly-one-retry semantics |
| **L-j RELEASE IS AUTHORISED ON THESE BYTES** | ✅ COMPLIANT | GPU memory management via `swap_to()` is correct |
| **L-m NOTHING MEASURED IS NEVER A PASS** | ✅ COMPLIANT | OOM errors no longer pass silently |
| **L-n DELIVERY IS THE MEASURE** | ⚠️ CONDITIONAL | GPU infrastructure supports delivery, but D1–D6 scope gap means full feature delivery is unconfirmed |
| **L-o INTEGRITY IS HARD, TASTE BENDS** | ✅ COMPLIANT | Error handling and retry mechanisms preserve integrity |
| **L-s CONTEXT INTEGRITY** | ✅ COMPLIANT | Single-model-at-a-time prevents cross-stage state contamination |
| **L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES** | ⚠️ UNVERIFIED | Cannot confirm without D1–D6 editorial fixes being present in the diff |
| **L-u HARD EXCLUSIONS AND SCORING** | ✅ COMPLIANT | GPU operations do not bypass scoring gates |
| **L-v SPEAKER AND TRANSCRIPT TRUTH** | ✅ COMPLIANT | GpuOOM propagation fix strengthens this law |

**Final determination:** L-r is the most critical law for this feature. It is **partially violated** due to the `held()` bug. All other directly testable laws are compliant. L-t and the full L-n picture cannot be confirmed until the D1–D6 scope question is resolved.

---

## SECURITY CONSENSUS

Both models assigned Security 8.0/10 with no change between cycles. No new security-specific findings were raised. The existing observations stand:

1. **Process isolation via `fcntl.flock`** — Correctly used. No TOCTOU race identified in the main path (the `held()` bug is a logical error, not a security race).
2. **Foreign process detection in `swap_to()`** — Both models confirmed this is correctly implemented and prevents foreign processes from holding GPU0 unexpectedly.
3. **No credential or secret handling in the diff** — Nothing to flag.

No security items require immediate action beyond the correctness fixes already in the action plan.

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

### WCG1 — Test Coverage for the `held()` / Standalone Lease Scenario
Both models' analyses (Gemini explicitly, GPT-4o by endorsing the test suite as comprehensive then missing this gap) point to the same blind spot: **there is no test covering the case where `lease()` is called by a standalone process on an existing but unlocked lease file.** A world-class GPU management module must have hermetic coverage of every branch of its core locking primitive. This gap must be closed.

### WCG2 — Scope Completeness: Infrastructure Enabling vs. Feature Delivering
Both models flagged that the branch name and feature tickets imply a complete delivery (infrastructure + editorial fixes) but only the infrastructure layer is present. A world-class delivery process makes this distinction explicit in the commit message, PR description, and ticket status — it does not leave auditors (or future engineers) to infer intent from a branch name. The gap is not just the missing code; it is the missing **explicit scope declaration**.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Resolve scope: formally declare this delivery as infrastructure-only (rename branch + close/defer D1–D6 tickets) OR add D1–D6 editorial fixes to this branch before merge. No merge permitted until this is resolved. | N/A — project/PM level | Both (Unanimous) | Both models flagged this as a mandatory gate. Merging an incomplete feature under a misleading branch name creates permanent confusion in git history and deferred law compliance. |
| **P1 HIGH** | Fix `held()` logic: rewrite to check the lease file's current owner PID against `os.getpid()` / known ancestors, with no lock acquisition as a side effect. Currently returns `True` for an unlocked file and silently acquires the lock, allowing `lease()` to skip its own locking step. | `pipeline/gpu0.py:1043–1054` | Gemini (unique, confirmed by synthesis) | Silent failure of the core "ONE OWNER" guarantee. The locking architecture is useless if the re-entrancy check bypasses the lock on first acquisition. |
| **P1 HIGH** | Add a regression test: standalone process calls `gpu0.lease()` on a pre-existing but unlocked lease file → must correctly acquire the lock (not silently skip it) and enforce ONE OWNER semantics throughout. | `pipeline/test_gpu0.py` | Gemini (unique, confirmed by synthesis) | Current test suite has a blind spot on this exact scenario. Without this test, the P1 bug fix above has no regression guard. |
| **P2 MEDIUM** | After P0 scope resolution: if D1–D6 are deferred, update the PR description and commit message to explicitly state "infrastructure-only delivery of L-r; D1–D6 editorial fixes tracked in [ticket refs]". | PR / commit metadata | Both (implicit) | Prevents future engineers from assuming D1–D6 are present in this merge. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

Two blockers prevent shipping:

1. **P0 — Scope ambiguity is unresolved.** The branch contains only a subset of what its name and associated tickets describe. No merge should occur until the team formally declares intent in writing.

2. **P1 — `gpu0.held()` has a silent logic bug** that breaks the "ONE OWNER" guarantee for standalone script invocations. This is the single most dangerous defect in the codebase: it fails silently, produces no error, and allows a process to operate on GPU0 without the lease it believes it holds. The fix is straightforward; the bug must not ship.

The underlying GPU infrastructure architecture — `BaseException` for `Gpu0Stop`, `fcntl.flock` leasing, `swap_to()` as a single loading entrypoint, `_attempts()` bounded self-heal — is well-designed, well-tested, and law-compliant. This is genuinely good engineering. The two blockers are fixable in a short follow-up pass. Once they are resolved, this feature is shippable.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Resolve scope declaration | N/A (project-level gate) | models: both |
  Before writing any code, confirm with the project lead whether this branch
  is intended as infrastructure-only (L-r) or must also include D1–D6 editorial
  fixes. If infrastructure-only: rename the branch to `gpu0-lease-lr` (or
  equivalent), update CHANGELOG and PR description to state explicitly
  "infrastructure-only delivery of L-r; D1–D6 tracked separately", and close
  or defer D1–D6 tickets with a note. If D1–D6 must be included: implement
  them before proceeding with the merge. Do not proceed past this gate
  without a written resolution on record.

P1 HIGH | Fix gpu0.held() logic flaw | pipeline/gpu0.py:1043-1054 | models: gemini |
  The current implementation calls fcntl.flock(LOCK_EX | LOCK_NB) to test
  whether the current process already holds the lease. This is incorrect:
  the call succeeds both when the process already holds the lock AND when
  the file is completely unlocked. In the unlocked case, held() returns True
  as a false positive AND acquires the lock as a silent side effect, causing
  lease() to skip its own locking step. The process then operates on GPU0
  without a valid lease.

  Rewrite held() to:
  1. Read the PID recorded in the lease file (use the same mechanism as
     holder() which correctly distinguishes locked vs unlocked states).
  2. Return True only if that PID matches os.getpid() or a known ancestor
     PID of the current process.
  3. Ensure held() has zero side effects — it must never acquire, release,
     or modify the lock or lease file.
  4. If the lease file does not exist or is unlocked, return False.

P1 HIGH | Add regression test for standalone lease acquisition | pipeline/test_gpu0.py | models: gemini |
  Add a test case covering this exact scenario:
    - A lease file exists on disk but is unlocked (no process holds it).
    - A standalone process (simulated) calls gpu0.lease().
    - Assert: the process correctly acquires the exclusive lock (held() now
      returns True for the correct reason).
    - Assert: no other process can acquire the lease concurrently.
    - Assert: on context manager exit, the lock is released and held()
      returns False.
  This test must fail on the unfixed code and pass on the fixed code.
  It is the regression guard for the P1 bug above.

P2 MEDIUM | Update PR description and commit message | PR metadata / git commit | models: both |
  After P0 resolution: ensure the commit message and PR description explicitly
  state the delivery scope (infrastructure-only or full feature). If
  infrastructure-only, include ticket references for D1–D6 as deferred.
  Format: "feat(pulse-sentence-law): L-r GPU lease infrastructure [scope: infra-only; D1–D6 deferred to #XXX]"

VALIDATED — do NOT touch these areas, all models confirmed excellent:

  - BaseException inheritance for Gpu0Stop (gpu0.py ~line 990): correct by
    design; do not change to Exception.
  - fcntl.flock as the lease primitive: correct OS-level choice; do not replace.
  - _attempts() bounded self-heal in run_fresh.py (lines 390-426): correctly
    implements L-r(3); do not alter retry count or Hold conversion logic.
  - swap_to() as the single entry point for model loading (gpu0.py line 1294):
    correctly enforces ONE MODEL AT A TIME; do not add alternative load paths.
  - Existing test_gpu0.py tests (lines 1635, 1671): these tests are correct
    and must not be weakened or removed; only add new tests.
  - GpuOOM propagation fix in transcript_store.py (lines 843-845): correct
    and must remain; do not revert.

After implementing all P0 and P1 items:
  regression_test.sh must show zero FAILs.
  The new test for held() must appear in the test run output and show PASS.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — fix gpu0.held() lease logic, add regression test, resolve scope declaration"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Gemini — 2-Sentence Justification

Gemini delivered the single highest-impact finding of the entire audit cycle: the P1 scope discrepancy (D1–D6 editorial fixes entirely absent from the branch), a project-level issue that GPT-4o missed in Cycle 1 and only acknowledged after Gemini surfaced it. Beyond that unique discovery, Gemini's Cycle 1 analysis demonstrated superior technical depth — correctly identifying the `BaseException` rationale, the `fcntl.flock` child-process inheritance edge case, and the `_attempts()` bounded self-heal logic — with precise file/line attribution and clear reasoning that proved fully accurate when validated in Cycle 2.

---

## FINAL SECOND-PASS PRIORITY LIST

The following is the definitive ordered list derived from both audit cycles, weighted by severity, consensus strength, and Gemini's Cycle 2 uplift. Items are ordered: implement the top items first; do not skip lower items on the assumption they are minor.

---

### P0 — MERGE BLOCKER (resolve before any merge proceeds)

**P0-1 — Scope Gate: Formally resolve D1–D6 delivery status**
- **Source:** Gemini (Cycle 1, confirmed by GPT-4o Cycle 2, elevated to U1 in consensus)
- **Action:** Project lead must choose exactly one path before merge:
  - **(a) Infrastructure-only delivery:** Rename branch to reflect GPU/L-r scope only. Explicitly open tracked tickets for D1–D6 (letterboxing, quote-only, etc.) on a follow-on branch. Update the feature acceptance criteria to remove D1–D6 from this delivery.
  - **(b) Complete delivery:** Add D1–D6 editorial fixes to this branch and re-audit the new diff before merge.
- **Why P0:** The branch name (`combo-letterbox-quoteonly-v2`) and feature name (`pulse-sentence-law`) create an auditable commitment to D1–D6 that is not met. Merging silently drops user-facing fixes without a paper trail.

---

### P1 — MUST FIX (correctness or law compliance at risk)

**P1-1 — Verify `gpu0.release_all` is called on all abnormal exit paths**
- **Source:** Cycle 2 consensus, Gemini deeper analysis
- **Action:** Audit every code path that can exit a run abnormally (exceptions, signals, timeouts) and confirm `gpu0.release_all` is reachable on each. Add a `try/finally` guard at the top-level run dispatcher if any path is unguarded. Write a test that sends SIGTERM mid-run and asserts the lease is released.
- **Why P1:** A leaked lease blocks all subsequent GPU0 jobs with `LeaseBusy` until the process is manually killed. This is a silent availability failure.

**P1-2 — Confirm `_attempts()` records both attempt outcomes, not only the final one**
- **Source:** GPT-4o Cycle 1 (lines 390–426), validated in Cycle 2
- **Action:** Inspect the `Hold` payload written after a second OOM failure and verify it contains the exception detail from *both* attempt 1 and attempt 2. If only the final exception is stored, amend `_attempts()` to accumulate exceptions into the Hold record.
- **Why P1:** Law L-r(3) requires the bounded self-heal to be auditable. A Hold with only one exception makes it impossible to determine whether the first attempt also failed with OOM or with a different error class.

**P1-3 — Validate `REQUIREMENT_MIB` values against current model weights**
- **Source:** Gemini Cycle 1 (`swap_to` / line 977 area)
- **Action:** Cross-reference every entry in `REQUIREMENT_MIB` against the actual peak MiB recorded by `PeakSampler` in staging. If any entry is understated by more than 10%, update the value and add a CI assertion that compares live peak samples against the declared requirement on each model-load test run.
- **Why P1:** An understated requirement causes `swap_to` to proceed when there is insufficient headroom, producing the OOM it was designed to prevent.

---

### P2 — SHOULD FIX (robustness, maintainability, or law compliance gap)

**P2-1 — Add explicit test for inherited file descriptor closure in child processes**
- **Source:** Gemini Cycle 1 (lines 1043–1053, 1605–1614)
- **Action:** Add a test in `test_gpu0.py` that forks a child process simulating `run_fresh.py` via `pulse_check_run.sh`, confirms the child cannot re-acquire the parent's `fcntl.flock` lease, and confirms the child's inherited fd is correctly closed on exec. Without this test the child-process lease-inheritance logic is covered only by code inspection.
- **Why P2:** The logic is sound per Gemini's analysis, but the absence of a targeted test means a future refactor of the fork/exec path could silently re-introduce lease leakage.

**P2-2 — Document the `BaseException` inheritance contract at the class definition**
- **Source:** Both models (unanimous finding U2)
- **Action:** Add a docstring block to `Gpu0Stop` (and `GpuOOM` if it also inherits `BaseException`) that explicitly states: *"Inherits BaseException, not Exception. This is intentional. Do not change. Application-level except Exception: clauses must not catch infrastructure failures."* Reference the law (L-r) that mandates this.
- **Why P2:** Both models had to reason about this independently. Without inline documentation, the next engineer will face the same question and may "fix" it incorrectly.

**P2-3 — Assert `PeakSampler` stage boundaries are never nested**
- **Source:** GPT-4o Cycle 1 (lines 1482–1516)
- **Action:** Add a runtime assertion (or test) that confirms a new `PeakSampler` stage cannot be opened while another is open on the same thread/process. Nested stages would cause peak readings to be attributed to the wrong stage, corrupting the memory-requirement data that feeds `REQUIREMENT_MIB`.
- **Why P2:** The correctness of P1-3's validation depends on `PeakSampler` data being clean. A nesting bug silently undermines that entire feedback loop.

---

### P3 — NICE TO HAVE (quality, documentation, observability)

**P3-1 — Add observability: log lease acquisition duration**
- **Action:** Emit a structured log line when a lease is released that records how long it was held. This feeds future capacity planning and makes `LeaseBusy` contention visible in dashboards without requiring a code change later.

**P3-2 — Add a `swap_to` integration test covering the foreign-process detection path**
- **Action:** The foreign-process check in `swap_to` is currently covered only by unit tests with mocked process lists. Add an integration test that actually launches a foreign CUDA process, calls `swap_to`, and asserts the correct exception type and message.

**P3-3 — Confirm test naming convention matches project standards**
- **Source:** GPT-4o Cycle 2 (documentation/maintainability note)
- **Action:** Verify that tests added in `test_gpu0.py` follow the same naming and fixture conventions as the rest of the test suite. Inconsistent naming makes test-failure triage harder under CI.

---

### IMPLEMENTATION ORDER SUMMARY

| Order | ID | Effort | Blocking |
|-------|----|--------|----------|
| 1 | P0-1 | Low (decision) | Yes — merge blocked until resolved |
| 2 | P1-1 | Medium | Yes — availability risk |
| 3 | P1-2 | Low | Yes — law L-r(3) auditability |
| 4 | P1-3 | Medium | Yes — correctness of swap_to |
| 5 | P2-1 | Medium | No |
| 6 | P2-2 | Low | No |
| 7 | P2-3 | Low | No |
| 8 | P3-1 |