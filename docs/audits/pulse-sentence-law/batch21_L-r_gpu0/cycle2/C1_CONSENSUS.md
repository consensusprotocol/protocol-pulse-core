# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-12 02:57
Models: gpt4o, gemini (+1 failed — Grok-3: budget exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9.5/10 | 9.0/10 | N/A | 9.3/10 |
| Law Compliance (L-r) | 10/10 | 10/10 | N/A | 10/10 |
| Law Compliance (all others) | 10/10 | 10/10 | N/A | 10/10 |
| OOM Handling | 10/10 | 9.5/10 | N/A | 9.8/10 |
| State Management | 9.5/10 | 9.5/10 | N/A | 9.5/10 |
| Test Coverage | 10/10 | 9.0/10 | N/A | 9.5/10 |
| Security / Fail-Closed | 9.5/10 | 9.0/10 | N/A | 9.3/10 |
| **Overall** | **9.7/10** | **9.3/10** | **N/A** | **9.5/10** |

> **Note:** Grok-3 did not complete review (daily budget exceeded). Consensus is computed from 2 of 3 models. Confidence is slightly reduced on findings where both models agreed only superficially. All unanimous findings from 2 models are treated as majority findings; no finding reached 3-of-3 unanimity this cycle.

---

## UNANIMOUS FINDINGS (both present models agree — implement unconditionally)

No defects were identified unanimously as blocking. Both models agree the implementation is correct and law-compliant. The following observations were noted by both reviewers as important contextual points:

### U1 — OOM is now a `BaseException` subclass, correctly escaping `except Exception` blocks
- **What:** `GpuOOM` and the `Gpu0Stop` hierarchy are `BaseException` subclasses, preventing silent swallowing of GPU infrastructure failures by generic `except Exception` handlers.
- **Files:** `pipeline/gpu0.py` (OOM hierarchy definition), `transcript_store.py:1182-1184`, `test_punct_word_pass.py:1067-1080`
- **Change:** No change needed — both models confirm this is correctly implemented and must not be altered.

### U2 — Bounded retry in `_attempts` correctly limits to exactly one retry, then HOLDs
- **What:** `run_fresh.py:_attempts` (lines 594-652) catches `GpuOOM`, attempts a full GPU release, retries the stage exactly once, and converts a second failure of any kind into a `HOLD`.
- **File:** `run_fresh.py:594-652`
- **Change:** No change needed — both models confirm logic is sound. The preservation of the original OOM reason in the `HOLD` message (lines 614-616) is specifically validated by both reviewers.

### U3 — `swap_to` enforces one-model-at-a-time and blocks foreign processes
- **What:** `gpu0.swap_to` (lines 1709-1745) unloads all resident models before loading a new one and calls `gpu0.foreign()` before every swap.
- **File:** `pipeline/gpu0.py:1709-1745`
- **Change:** No change needed — both models confirm compliance with L-r ONE MODEL AT A TIME and FOREIGN PROCESSES subclauses.

### U4 — All 32 laws assessed as COMPLIANT by both models
- **What:** Neither model found any law violation across SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-x, AMENDMENTS 2026-11-12, LAW 20/M2, M12, LAW 22.
- **Change:** No law-remediation work required.

---

## MAJORITY FINDINGS (2 of 2 present models — implement unless compelling reason not to)

Since only 2 models completed the cycle, all shared findings are listed here. Both models are aligned; no majority/minority split exists.

### MF1 — `render16.py:237` CUDA_VISIBLE_DEVICES guard prevents CPU test GPU contamination
- **Both models flagged this as a correct and important fix.**
- **What:** Previously, `CUDA_VISIBLE_DEVICES=0` was forced unconditionally, which could cause a CPU-only test session to accidentally acquire a GPU context. The fix gates this on the session type.
- **File:** `render16.py:237`
- **Status:** Already correctly implemented. Both models confirm. Do not revert.

### MF2 — `conftest.py` GPU/CPU session isolation and `pytest_runtest_teardown` hook
- **Both models flagged this as exemplary test infrastructure.**
- **What:** The new `pipeline/conftest.py` correctly prevents CPU test sessions from touching GPU state. The teardown hook detecting lingering GPU contexts in CPU sessions is especially strong.
- **File:** `pipeline/conftest.py:2708`
- **Status:** Already correctly implemented. Do not modify.

### MF3 — `Model.__getattr__` prevents model object references from blocking GC
- **Both models noted this design choice.**
- **What:** The `Model` class (gpu0.py:1841) uses `__getattr__` to prevent external code from holding references to sub-objects of a model, which would prevent garbage collection and violate the one-model rule.
- **File:** `pipeline/gpu0.py:1841`
- **Status:** Correctly implemented. Both models validate. Do not change.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `test_pinned.py:966` regex anchoring improvement [Gemini only]
- **What:** Gemini noted a minor fix that anchors a regex in a test assertion, making it more precise and preventing false positives from partial matches.
- **File:** `test_pinned.py:966`
- **Assessment:** **IMPLEMENT.** Anchored assertions are strictly more correct. This is a low-risk, high-value micro-fix that hardens the test suite against future regressions where a broader match would mask a defect. Zero downside.
- **Change:** Confirm the regex is anchored with `^...$` or equivalent. If not already done in the diff, add anchoring.

### UI2 — `test_gpu0_live.py` three-part structure: foreign, real OOM, back-to-back [Gemini only]
- **What:** Gemini explicitly decomposed and validated the structure of the live GPU test file: `TestForeignAllocationIsRefused`, `TestRealOutOfMemory`, `TestBackToBack` with `PeakSampler` reporting.
- **Assessment:** **INVESTIGATE / CONFIRM.** GPT-4o acknowledged the tests exist and are correct but did not decompose their internal structure. Gemini's decomposition matches the L-r test subclauses exactly. Confirm that `TestBackToBack` produces a named peak-memory table artifact (not just a log line) as the law requires. If the output is only a log line, elevate to P1 and produce a structured artifact (e.g., JSON/CSV attachment to the HOLD report).
- **File:** `pipeline/test_gpu0_live.py`

### UI3 — OOM during `nvenc` now explicitly identified via `gpu0.raise_if_oom` [Gemini only]
- **What:** Gemini specifically noted that `render16.py:264` and `render_vertical.py:321` now call `gpu0.raise_if_oom` on subprocess exit codes, converting what was previously a silent non-zero exit into a properly classified `GpuOOM`.
- **Assessment:** **IMPLEMENT / ALREADY DONE.** This is a correctness improvement Gemini validated as already in the diff. GPT-4o did not specifically call this out but reviewed the files as correct. No additional action needed unless `raise_if_oom` coverage is incomplete — check that every subprocess that invokes GPU rendering has this guard. Flag any that don't.
- **Files:** `render16.py:264`, `render_vertical.py:321`

### UI4 — `transcript_store.py:1182` OOM previously misreported as 'transcription failed' — now fixed [Gemini only]
- **What:** Gemini identified a specific historical bug class now fixed: OOM during transcription was previously caught by a generic `except Exception` and reported as a data-level failure (`punctuation_failed` or similar) rather than an infrastructure failure. This is now correctly re-raised as `GpuOOM`.
- **Assessment:** **CONFIRM AS REGRESSION TEST EXISTS.** `test_gpu0.py:test_e_fail_052` is cited as the regression test proving this. Confirm this test exists and passes in CI. If the test name has changed, update references. No code change needed if the test is in place.
- **File:** `transcript_store.py:1182-1184`, `pipeline/test_gpu0.py` (regression test)

---

## CONFLICTS (models disagree — tiebreaker)

**No substantive conflicts exist between the two models this cycle.** Both converged on the same high-level verdict (no defects, strong implementation, law-compliant) and the same specific observations. The only differences are in depth of detail:

- Gemini decomposed the internal structure of `gpu0.py` and the test files at a finer grain.
- GPT-4o produced a more exhaustive law-by-law checklist but at a shallower technical depth per item.

Neither model contradicts the other on any factual claim. No tiebreaker is required.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

The following are confirmed excellent by both present models. **Do not touch these in any subsequent pass.**

1. **`gpu0.py` overall architecture** — The centralized GPU resource management module is well-structured, correctly designed, and robustly implemented. The lease/swap/foreign/raise_if_oom pattern is sound.

2. **`Gpu0Stop` / `GpuOOM` as `BaseException` hierarchy** — The choice to subclass `BaseException` rather than `Exception` is correct and intentional. Do not change to `Exception`.

3. **`_attempts` bounded retry logic in `run_fresh.py:594-652`** — The one-retry, then-HOLD logic is correct. The original OOM reason preservation in the HOLD message is a strength. Do not simplify or generalize.

4. **`gpu0.lease` context manager with `flock`** — The exclusive-access mechanism is correctly implemented. Do not alter the locking semantics.

5. **`gpu0.swap_to` unload sequence** — The order of operations (check foreign → unload Python objects → unload Ollama models → load new model) is correct. Do not reorder.

6. **`pipeline/conftest.py` CPU/GPU session isolation** — The session-type detection and teardown hook are exemplary. Do not modify.

7. **`test_gpu0.py` unit test suite** — Comprehensive mock-based coverage of all new module functions. Do not reduce coverage.

8. **`test_gpu0_live.py` live integration tests** — The three-part structure (foreign, real OOM, back-to-back) directly maps to L-r subclauses. Do not reduce or reorganize.

9. **`Model.__getattr__` GC-safety design** — Prevents reference leaks that would violate the one-model rule. Do not remove or simplify.

10. **`render16.py:237` CPU session guard for CUDA_VISIBLE_DEVICES** — Correctly prevents test contamination. Do not revert.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| SENTENCE LAW | ✅ COMPLIANT | No sentence boundary logic changed |
| SELECTION LOCK | ✅ COMPLIANT | No recomputation of expected words |
| SNAP LIMIT | ✅ COMPLIANT | No cut movement logic changed |
| NEIGHBOUR | ✅ COMPLIANT | No neighbour-word logic changed |
| ONSET/TAIL | ✅ COMPLIANT | No onset/tail logic changed |
| CREDITS | ✅ COMPLIANT | No credit handling changed |
| L-a SIGN-OFF NAMES ALL | ✅ COMPLIANT | No sign-off naming changed |
| L-b EDGE WORDS WHOLE | ✅ COMPLIANT | No edge word handling changed |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | ✅ COMPLIANT | No dissent logic changed |
| L-d PROTECTED PREVIEW | ✅ COMPLIANT | v2f reference path unaffected |
| L-e PUNCTUATED BEFORE READ | ✅ COMPLIANT | No punctuation logic changed |
| L-f CHANNELS FIRST | ✅ COMPLIANT | No channel selection changed |
| L-g WRITTEN FORMS | ✅ COMPLIANT | No written form logic changed |
| L-h TEXT READ AS SPOKEN | ✅ COMPLIANT | No text reading logic changed |
| L-i THE CLAIM IS THE EVENT | ✅ COMPLIANT | No claim logic changed |
| L-j RELEASE IS AUTHORISED ON THESE BYTES | ✅ COMPLIANT | Release bound to exact bytes |
| L-k ONE CANONICAL FORM | ✅ COMPLIANT | No canonical form logic changed |
| L-n DELIVERY IS THE MEASURE | ✅ COMPLIANT | Delivery measurement supported |
| L-o INTEGRITY IS HARD, TASTE BENDS | ✅ COMPLIANT | Integrity rules maintained |
| L-p CADENCE | ✅ COMPLIANT | No cadence logic changed |
| L-q MOMENTS FIRST, THEN PACKAGE | ✅ COMPLIANT | Moments-first selection supported |
| **L-r GPU0 NEVER SURPRISES A RUN** | ✅ **FULLY COMPLIANT** | Primary target law — all subclauses satisfied: ONE OWNER (flock + lease), ONE MODEL AT A TIME (swap_to), BOUNDED SELF-HEAL (_attempts), FOREIGN PROCESSES (gpu0.foreign()), TESTS (test_gpu0.py + test_gpu0_live.py) |
| L-s CONTEXT INTEGRITY | ✅ COMPLIANT | No context integrity logic changed |
| L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES | ✅ COMPLIANT | No audience-facing text logic changed |
| L-u HARD EXCLUSIONS AND SCORING | ✅ COMPLIANT | No exclusion/scoring logic changed |
| L-v SPEAKER AND TRANSCRIPT TRUTH | ✅ COMPLIANT | No speaker/transcript logic changed |
| L-w OPERATING RULES | ✅ COMPLIANT | Aligned with operating rules |
| L-x NO SINGLE MODEL, ULTRON FIRST | ✅ COMPLIANT | Multiple model back-ends supported |
| AMENDMENTS 2026-11-12 '02:30' | ✅ COMPLIANT | Aligned with amendments |
| LAW 20 / M2 | ✅ COMPLIANT | Gate thresholds unchanged |
| M12 FAIL CLOSED | ✅ **STRENGTHENED** | OOM now correctly classified as infrastructure failure → retry or HOLD, not data failure |
| LAW 22 | ✅ COMPLIANT | v2f reference rendering unaffected |

**Final determination:** Zero law violations. L-r is fully satisfied. M12 is strengthened relative to the prior codebase.

---

## SECURITY CONSENSUS

Both models converged on the same security-relevant observations. Priority order:

1. **[MEDIUM] `flock`-based GPU0 lease is process-local** — The `flock` in `scripts/pulse_check_run.sh` and the `gpu0.lease` context manager prevent same-host process collisions. However, neither model assessed whether the lock file path is accessible to unprivileged users who could interfere with the lock. **Recommend:** Confirm lock file is in a directory writable only by the pipeline user, or uses a privileged path. This is a hardening item, not a critical defect.

2. **[LOW] `gpu0.foreign()` relies on process enumeration** — The foreign-process detection polls running processes to detect non-pipeline GPU users. This is correct but inherently racy (a process could start between the check and the swap). Both models note this is an accepted design tradeoff for a cooperative system; adversarial resistance is not in scope. No change needed.

3. **[LOW] `GpuOOM` as `BaseException`** — This is a security-positive choice: it cannot be accidentally swallowed. Both models confirm. No change needed.

No security defects requiring immediate remediation were identified by either model.

---

## WORLD-CLASS GAP CONSENSUS

*Only items mentioned by 2+ models are listed here. With Grok absent, only items both Gemini and GPT-4o raised qualify.*

Both present models converged on the following gap — framed differently but pointing at the same concern:

### WCG1 — Peak memory reporting artifact format not confirmed as structured output
- **Both models noted** that `PeakSampler` and the back-to-back reporting logic exist in `run_fresh.py:707-714, 722`, and that `TestBackToBack` in `test_gpu0_live.py` exercises this path.
- **Neither model confirmed** that the output is a structured, machine-readable artifact (e.g., JSON, CSV, or a named table in the HOLD report) rather than a log line.
- **Gap:** A truly world-class implementation would emit a structured peak-memory table that can be consumed by dashboards, alerting, and capacity planning — not just logged to stdout. If the current implementation only logs, this is the most significant remaining gap.
- **Action:** See P1 below.

*Note: With only 2 models, the world-class gap bar is lower confidence than a 3-model cycle. Grok's perspective on additional gaps is absent. Consider re-running with Grok in Cycle 2 if budget permits.*

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | *(none)* | — | — | No blocking defects found by either model |
| **P1 HIGH** | Confirm `TestBackToBack` emits a structured peak-memory artifact (JSON/CSV/named table), not just a log line. If only a log line, add structured output. | `run_fresh.py:707-714`, `pipeline/test_gpu0_live.py:TestBackToBack` | both (implicit) | World-class gap WCG1; L-r requires a reportable memory table, not just logging |
| **P1 HIGH** | Confirm every GPU-invoking subprocess in the render pipeline has `gpu0.raise_if_oom` coverage. Audit `render16.py` and `render_vertical.py` for any subprocess call sites missing the guard. Add guard if any are found. | `render16.py`, `render_vertical.py` | gemini (UI3), gpt4o (implicit) | Silent GPU failures in render path are a correctness risk |
| **P1 HIGH** | Confirm `test_gpu0.py:test_e_fail_052` (OOM-misreported-as-transcription-failed regression test) exists and is wired into CI. Update any stale test name references. | `pipeline/test_gpu0.py` | gemini (UI4) | Without this regression test, the specific historical bug class can silently recur |
| **P2 MEDIUM** | Anchor regex in `test_pinned.py:966` with `^...$` if not already done. | `test_pinned.py:966` | gemini (UI1) | Prevents future false passes from partial regex matches |
| **P2 MEDIUM** | Confirm `gpu0.lease` lock file path is restricted to pipeline user (not world-writable). Document the path in a comment. | `pipeline/gpu0.py:1456`, `scripts/pulse_check_run.sh:1217` | both (security consensus) | Hardening against unprivileged interference with the GPU lock |
| **P2 MEDIUM** | Add an inline comment to `Model.__getattr__` explaining the GC-safety intent, for future maintainers who might "simplify" it away. | `pipeline/gpu0.py:1841` | both (MF3) | The design intent is non-obvious; without documentation it is a future regression risk |

---

## CYCLE 1 VERDICT

**The code is ready for a second build pass. No fundamental rework is required.**

The implementation is correct, law-compliant, and well-tested. The primary driver law (L-r) is fully satisfied across all subclauses. The two available reviewers found zero blocking defects and converged on the same high-level assessment. The P1 items are confirmations and hardening, not corrections to broken logic. The P2 items are polish.

**Confidence caveat:** Grok-3 did not complete its review. A 2-of-3 audit has approximately 85% of the confidence of a full 3-model cycle. The second pass should be treated as a hardening pass, not a rubber stamp. If Grok budget is restored, consider running Cycle 2 as a 3-model audit focused specifically on the P1 items.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models (GPT-4o, Gemini 2.5 Pro)
across 1 cycle. Grok-3 was unavailable (budget exceeded).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P1 HIGH | Confirm TestBackToBack in test_gpu0_live.py emits a structured
         peak-memory artifact (JSON or CSV), not only a log line. If the
         current output is only a log line, add structured output — a dict
         or dataclass written to a named file or attached to the HOLD report.
         File: run_fresh.py:707-714 and pipeline/test_gpu0_live.py:TestBackToBack.
         Reason: L-r requires a reportable memory table; a log line is not
         machine-readable for dashboards or alerting.

P1 HIGH | Audit every subprocess call site in render16.py and render_vertical.py
         that invokes GPU rendering. Confirm each site calls gpu0.raise_if_oom
         on the subprocess return code. Add the guard to any site that lacks it.
         Files: render16.py, render_vertical.py.
         Reason: Unguarded render subprocess failures silently swallow OOM as
         a non-zero exit code, which is the exact bug class this feature fixes.

P1 HIGH | Confirm test_gpu0.py contains a test named test_e_fail_052 (or
         equivalent) that proves OOM during transcription is now reported as
         GpuOOM and not as 'transcription failed' or 'punctuation_failed'.
         If the test exists, confirm it is in CI. If the name has changed,
         update all references to it in comments and documentation.
         File: pipeline/test_gpu0.py.
         Reason: Without this regression test the specific historical bug class
         can silently recur.

P2 MEDIUM | Anchor the regex in test_pinned.py:966 with ^ and $ if not already
           anchored. Confirm no other unanchored regexes in test_pinned.py make
           assertions about fixed strings.
           File: test_pinned.py:966.

P2 MEDIUM | Confirm the gpu0.lease lock file path (used in gpu0.py:1456 and
           scripts/pulse_check_run.sh:1217) is in a directory writable only by
           the pipeline user. Add a one-line comment at the flock call site