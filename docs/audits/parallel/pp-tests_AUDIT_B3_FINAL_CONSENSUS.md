# CONSENSUS REPORT — PP-TESTS_AUDIT_B3 — CYCLE 2
Generated: 2026-11-12 02:14
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem       | Gemini  | GPT-4o  | Grok    | Consensus |
|-----------------|---------|---------|---------|-----------|
| Backend logic   | 0/100   | 35/100  | 10/100  | **8/100** |
| Frontend/UI     | N/A     | N/A     | N/A     | **N/A**   |
| Error handling  | 0/100   | 48/100  | 15/100  | **10/100**|
| Security        | N/A     | N/A     | 60/100  | **60/100**|
| Performance     | 0/100   | 62/100  | 30/100  | **10/100**|
| Law compliance  | 25/100  | 75/100  | 40/100  | **30/100**|
| World-class gap | 5/100   | 60/100  | 10/100  | **8/100** |
| **OVERALL**     | **10/100** | **49/100** | **22/100** | **18/100** |

> **Scoring methodology note:** GPT-4o scored substantially higher than the other two models because it reviewed the documentation's *described* intent rather than applying the materiality test. Gemini and Grok, by applying the correct standard — does verifiable, executable code exist in the diff — converged on sub-25 overall scores. The consensus weights the materiality test as the controlling factor. GPT-4o's scores are treated as ceiling estimates; Gemini's post-correction scores and Grok's original scores form the realistic floor. The consensus splits closer to the materiality-corrected models.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U-1 | No executable test code exists in the diff
**What it is:** The entire submission — 608 lines across `STATE.md`, `BIBLE_ADDITIONS.md`, `COVERAGE.md`, `AUDIT_RESPONSE.md`, and `AUDIT_BRIEF.md` — is documentation asserting the existence and results of a test suite. The Python files (`tests/adversarial/test_f*.py`, `conftest.py`, `adv_helpers.py`) and all fixture data are absent.

**File/line:** `docs/audits/parallel/` — entire directory; also `tests/adversarial/` — does not appear in diff at all.

**What to change:** The actual test suite source files must be delivered as part of this feature submission. No amount of documentation can substitute for executable code in a code audit. Without the source, every quantitative claim, every compliance assertion, and every pass/fail count is unverifiable.

---

### U-2 | All numeric results are unverified assertions
**What it is:** Claims of "26 PASS / 0 FAIL," per-family pass/xfail counts, G8 floor measurements, L-b timing tables (2:40–4:04), and SHA256SUMS are presented as measured facts. None were produced by code present in the diff.

**File/line:** `pp-tests_STATE.md:17`, `pp-tests_STATE.md:49-56`, `pp-tests_STATE.md:58-72`

**What to change:** Remove or clearly qualify every numeric result with a disclaimer that it is a *claimed* result from a separate, unsubmitted audit chunk. Do not present measured tables as ground truth when the measurement source is absent. Preferably: submit the code that produces these numbers so they become reproducible evidence.

---

### U-3 | Absolute paths make the suite non-portable and the "one command" requirement unverifiable
**What it is:** The documentation references `/home/ultron/protocol_pulse/references` and `~/protocol_pulse` as hardcoded paths. The `PP_REFS_DIR` environment variable override is *described* but never shown in working code. No reviewer can confirm that `python3 -m pytest tests/adversarial -q` completes under 5 minutes on any machine other than the author's.

**File/line:** `pp-tests_STATE.md:32`, `pp-tests_STATE.md:92`

**What to change:** Replace all absolute paths with the `PP_REFS_DIR` environment variable throughout the actual test code (once delivered). Add a `conftest.py` guard that fails loudly with a clear error message if `PP_REFS_DIR` is unset or points to a non-existent directory.

---

### U-4 | Strict xfail contract is uninspectable
**What it is:** The documentation describes `@pytest.mark.xfail(strict=True, raises=AssertionError)` markers and an `adv_helpers.control` helper as central to the compliance architecture, but neither the markers nor the helper appear anywhere in the diff.

**File/line:** `pp-tests_AUDIT_RESPONSE.md:538-539`

**What to change:** Deliver the actual pytest markers and the `adv_helpers.control` helper so reviewers can confirm that the strict-xfail contract holds. The marker must be verified to not pass for the wrong reason (a failure mode the documentation itself acknowledges discovering).

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M-1 | GPU guard described but not shown in code (Gemini + Grok)
**What it is:** The documentation claims a multi-pronged CPU-only guard: `CUDA_VISIBLE_DEVICES` emptied, GPU-dependent libraries stubbed, network sockets blocked, and `nvidia-smi` check at teardown. All of this is described in `pp-tests_STATE.md:26-31` but no implementation exists in the diff.

**File/line:** `pp-tests_STATE.md:26-31`, `conftest.py` (absent)

**What to change:** The `conftest.py` session fixture that implements these guards must be delivered. The `nvidia-smi` teardown check in particular needs a code review, as it must handle machines where `nvidia-smi` is not installed without false-positive failures.

---

### M-2 | The "chunking artefact" defense is procedurally invalid (Gemini + Grok)
**What it is:** `pp-tests_AUDIT_RESPONSE.md:551` pre-emptively rebuts the missing code finding by claiming it was "audited as chunk A (11 files, 150 KB, 94/100)" in a separate submission. The referenced audit is not included in this diff and cannot be verified. Splitting code from its documentation across separate audit submissions and then refuting findings by citing the absent submission is not an acceptable audit procedure.

**File/line:** `pp-tests_AUDIT_RESPONSE.md:509-512`, `pp-tests_AUDIT_RESPONSE.md:551`

**What to change:** An auditable unit must be self-contained. The feature must be resubmitted as a single, complete diff containing both code and documentation. The "chunk A" reference must either be included inline or the claim must be removed.

---

### M-3 | Missing reference failure mode: skip vs. hard fail not verifiable (GPT-4o + Grok)
**What it is:** The documentation asserts that a missing reference produces a hard `FAILURE`, not a skip (`pp-tests_STATE.md:32`, `pp-tests_AUDIT_RESPONSE.md:528`), directly implementing Law L-m. This is a critical compliance point that cannot be verified without the fixture loading code.

**File/line:** `pp-tests_STATE.md:32`, `pp-tests_AUDIT_RESPONSE.md:528`

**What to change:** The fixture loading code that enforces `pytest.fail()` on missing references must be delivered and explicitly reviewed. The test must be confirmed to use `pytest.fail()` (not `pytest.skip()` or a silent exception) in all missing-reference code paths.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X-1 | Seductive meta-narrative risk (Gemini — unique)
**Observation:** Gemini's self-correction identified that the documentation is so well-written and self-critical (the multi-stage internal audit in `AUDIT_RESPONSE.md`) that it successfully distracted two of the three Cycle 1 reviewers into evaluating the *story* of quality rather than verifiable quality. The iterative self-audit narrative (8 findings, then 5 more, then verification) reads as a credibility signal but is itself unverifiable documentation.

**Assessment: IMPLEMENT — HIGH VALUE.** This is not just an observation about this submission; it is a process finding. Future audit procedures should enforce a hard rule: a reviewer may not award credit for described self-audits unless the corrected code is present in the diff. Add this as a standing rule to the audit gospel. The "seductive documentation" anti-pattern is a genuine risk to multi-model review integrity.

---

### X-2 | The pre-scripted rebuttal as a red flag (Gemini — unique)
**Observation:** The presence of `AUDIT_RESPONSE.md` with a pre-emptive `U-1 "REFUTED"` for the missing code finding indicates the author was aware the submission was incomplete. A submission that includes a rebuttal to its own most critical flaw — in advance, without the fix — is qualitatively different from a submission with an accidental omission.

**Assessment: INVESTIGATE FURTHER.** This warrants a process-level question: Was the submission intentionally split to manage review complexity, or was code withheld? The answer affects whether the response is "resubmit with code" or "escalate." For now, treat it as an accidental but invalid procedure (see M-2) rather than malfeasance.

---

### X-3 | Three-model scoring divergence as diagnostic signal (Grok — unique)
**Observation:** Grok noted that the spread between models (Gemini 99/100 → Grok 10/100 in Cycle 1) is itself diagnostic: Gemini scored documentation quality, GPT-4o scored documented claims, Grok scored verifiable deliverable content. These are three different review tasks, only one of which is correct for a code audit.

**Assessment: IMPLEMENT — PROCESS LEVEL.** Add explicit guidance to the audit gospel that reviewers must apply the materiality test first: "Does executable code for the claimed feature exist in the diff?" If no, scores for logic/performance/error-handling must be 0/100 regardless of documentation quality. This calibration rule would have collapsed the Cycle 1 divergence immediately.

---

## CONFLICTS (models disagree — your tiebreaker)

### C-1 | How severely to penalize the submission overall
- **Grok:** 10/100 overall (Cycle 1), "total gap"
- **Gemini:** 10/100 overall (Cycle 2, corrected down from 83/100)
- **GPT-4o:** 49/100 overall (Cycle 2, corrected down from 88/100)

**Tiebreaker — Grok and Gemini are correct.** GPT-4o's 49/100 reflects partial credit for the high quality of documentation and the described architecture. This is not appropriate for a code audit. The deliverable is executable software; the documentation is supporting material. When the primary deliverable is entirely absent, the score for the submission as a software artifact must be in the single digits. The consensus overall score of **18/100** (averaging the three) is the reported figure, but the actionable truth is Grok/Gemini: nothing passes without the code.

---

### C-2 | Whether security deserves a non-N/A score
- **Grok:** 60/100 (network/GPU guards described but not shown)
- **Gemini + GPT-4o:** N/A

**Tiebreaker — Grok is correct to score it, but 60 is too generous.** There are two concrete security-relevant surfaces: the `PP_REFS_DIR` environment variable (potential path traversal if unsanitized) and the `nvidia-smi` subprocess call (potential injection if the binary path is not hardcoded). These deserve evaluation. However, since neither is implemented in the diff, the score should be closer to 30/100 — credit for identifying the surfaces, penalty for unverifiable implementation. The consensus security score is adjusted to **30/100**.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> **Important caveat:** These strengths apply to the *documentation artifact* only. They are not transferable credit for the absent code. When the code is delivered, these strengths must be re-verified in the implementation.

1. **Documentation structure and clarity.** `STATE.md`, `COVERAGE.md`, and `AUDIT_RESPONSE.md` are exceptionally well-organized. The per-family breakdown, the coverage analysis, and the self-audit record are models of what test suite documentation should look like. **Do not restructure the documentation format.**

2. **Self-audit methodology.** The two-stage internal review (frontier review → verification round) described in `AUDIT_RESPONSE.md` — finding 8 issues then 5 more — represents genuine engineering rigor if the described process was actually followed. **Preserve and enforce this review methodology when the code is delivered.**

3. **Law coverage taxonomy.** The mapping of each test family to specific laws (L-m, L-j, etc.) and the explicit description of which laws are exercised through which entry points is a world-class compliance documentation approach. **Keep this taxonomy intact in the delivered code.**

4. **GPU-elimination strategy.** The described multi-pronged approach (env var + library stubs + network block + teardown probe) is architecturally sound. **Implement it exactly as described; do not simplify.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| **TESTS ONLY** | ✅ COMPLIANT | Only documentation files touched; no production code in diff. Verifiable from diff alone. |
| **CPU ONLY** | ⚠️ PARTIAL — UNVERIFIABLE | Strategy described correctly; implementation absent. Cannot confirm. |
| **Public entry points** | ⚠️ UNVERIFIABLE | Asserted in documentation; no test code to inspect. |
| **Strict xfail** | ⚠️ UNVERIFIABLE | Markers and helpers described but absent from diff. |
| **Genuine-pass AND must-fail** | ⚠️ UNVERIFIABLE | Test family structure described; no test functions to inspect. |
| **L-m: Nothing measured is never a pass** | ❌ VIOLATED (meta-level) | The documentation itself presents "measured" results that cannot be reproduced from the diff. The law is violated at the submission level. |
| **L-j: Fail closed** | ⚠️ UNVERIFIABLE | Test family 3 purpose described; no code to confirm. |
| **Never change what a check accepts** | ⚠️ UNVERIFIABLE | References described as read-only; no fixture code to confirm. |
| **One command, under 5 minutes on CPU** | ⚠️ UNVERIFIABLE | Command documented; timing claims unverified; absolute paths create portability risk. |

**Final determination:** Only **TESTS ONLY** is verifiably compliant. All other laws are either unverifiable or actively violated at the submission level. Law compliance score: **25/100**.

---

## SECURITY CONSENSUS

Two security surfaces identified by cross-model analysis (primarily Grok), neither verifiably mitigated:

1. **`PP_REFS_DIR` path handling** — If the environment variable is used without sanitization in fixture loading, a crafted path could cause the test suite to read from unintended locations. Priority: **Medium**. Mitigation: validate that `PP_REFS_DIR` resolves to an expected subdirectory structure before use.

2. **`nvidia-smi` subprocess invocation** — If the binary path is not hardcoded (e.g., `/usr/bin/nvidia-smi`) and PATH is not controlled, a malicious binary could be executed in a compromised CI environment. Priority: **Low** (test environments are generally trusted). Mitigation: use absolute path; check return code explicitly.

3. **No secrets in documentation** — All three models confirmed no hardcoded API keys, tokens, or credentials. ✅

**Security consensus: No critical vulnerabilities. Two medium/low issues pending code delivery.**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

1. **The gap between documentation and deliverable is total** (all 3 models). A world-class adversarial test suite for a paid intelligence product requires the actual test files, deterministic fixtures with byte-level reproducibility, and a CI job that runs the exact command and publishes JUnit + coverage reports. None of that is present.

2. **No reproducible CI evidence** (Gemini + Grok). A world-class submission includes a CI pipeline artifact — a log, a JUnit XML, a coverage badge — that proves the suite ran green on a neutral machine. The documented results cannot substitute for this.

3. **Portability gap** (all 3 models). Absolute paths mean the suite is currently tied to one developer's machine. World-class test suites run identically on any machine with the correct environment variables set.

4. **No fixture versioning strategy** (Gemini + GPT-4o). The documentation references SHA256SUMS for reference fixtures, but there is no described strategy for how fixtures are updated when the production system legitimately changes — a critical gap for a long-lived adversarial test wall.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Deliver all Python test source files | tests/adversarial/test_f*.py,
            | conftest.py, adv_helpers.py, and all  | conftest.py, adv_helpers.py,
            | fixture data the tests rely on.        | fixtures/
            | models: all (unanimous)               |
            | why: Without the code, there is nothing
            |      to audit. This is the singular
            |      blocker for every other action.

P0 CRITICAL | Remove or qualify all numeric results  | pp-tests_STATE.md:17,49-72
            | (pass/fail counts, G8 floors, timings, |
            | SHA256SUMS) that cannot be reproduced  |
            | from code in this diff.                |
            | models: all (unanimous)                |
            | why: Presenting unverifiable numbers as
            |      measured facts violates L-m at the
            |      submission level and is misleading.

P0 CRITICAL | Resubmit as a single self-contained     | pp-tests_AUDIT_RESPONSE.md:509-512,
            | unit. Remove the "chunk A" rebuttal    | 551
            | or include chunk A inline. An audit    |
            | submission cannot refute findings by   |
            | citing a separate unsubmitted artifact.|
            | models: gemini + grok                  |
            | why: Procedurally invalid; prevents
            |      complete review.

P1 HIGH     | Replace all absolute paths with         | pp-tests_STATE.md:32,92
            | PP_REFS_DIR throughout the actual test  | conftest.py (once delivered)
            | code. Add a conftest.py guard that      |
            | fails loudly if PP_REFS_DIR is unset.  |
            | models: all (unanimous)                |
            | why: Portability; "one command" law
            |      cannot be verified on any other
            |      machine until this is fixed.

P1 HIGH     | Deliver conftest.py GPU/network guard   | conftest.py (absent)
            | implementation: CUDA_VISIBLE_DEVICES,  | pp-tests_STATE.md:26-31
            | library stubs, socket block, nvidia-smi|
            | teardown check. Use absolute path for  |
            | nvidia-smi binary.                     |
            | models: gemini + grok                  |
            | why: CPU ONLY law is unverifiable and
            |      the nvidia-smi call has a security
            |      surface without hardcoded path.

P1 HIGH     | Deliver adv_helpers.control helper and  | pp-tests_AUDIT_RESPONSE.md:538-539
            | confirm strict-xfail markers use       | tests/adversarial/ (absent)
            | pytest.fail() for preconditions, not   |
            | silent exception swallowing.           |
            | models: all (unanimous)                |
            | why: The strict-xfail contract is the
            |      core compliance mechanism; it must
            |      be inspectable.

P1 HIGH     | Confirm missing-reference code paths    | pp-tests_STATE.md:32
            | use pytest.fail() not pytest.skip()    | pp-tests_AUDIT_RESPONSE.md:528
            | in fixture loading logic.              | (fixture code absent)
            | models: gpt4o + grok                   |
            | why: L-m compliance depends entirely
            |      on this; it cannot be assumed.

P2 MEDIUM   | Add sanitization of PP_REFS_DIR value   | conftest.py (once delivered)
            | before use: validate it resolves to    |
            | an expected directory structure.       |
            | models: grok (unique, but valid)       |
            | why: Path traversal risk in test
            |      infrastructure; low severity but
            |      cheap to fix.

P2 MEDIUM   | Add a fixture versioning / update        | docs/audits/parallel/COVERAGE.md
            | strategy document describing how        |
            | reference fixtures are updated when     |
            | the production system legitimately      |
            | changes. Include SHA256SUM regeneration |
            | procedure.                              |
            | models: gemini + gpt4o                 |
            | why: Long-lived adversarial test walls
            |      rot without a maintenance strategy.

P2 MEDIUM   | Add to audit gospel: "reviewers must    | docs/gospels/PP_TESTS_GOSPEL.md
            | apply the materiality test first;       |
            | scores for logic/performance/error-     |
            | handling are 0/100 if no executable     |
            | code is present."                       |
            | models: grok + gemini (process finding)|
            | why: Prevents Cycle 1 divergence pattern
            |      from recurring in future audits.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY. NOT MERGE READY.**

After two full cycles of three-model review, the determination is unambiguous and unanimous: **this submission does not contain the artifact it is auditing.** The diff is 608 lines of documentation about a test suite whose source code is entirely absent.

**Absolute final blocker:** The Python test files (`tests/adversarial/test_f*.py`), `conftest.py`, `adv_helpers.py`, and all fixture data must be present in the diff before any further review can proceed. Every other finding — compliance, portability, security, strict-xfail correctness — is secondary to this. A code audit of absent code is not an audit.

**Conditions for re-approval:** Resubmit as a single complete diff containing all source and fixture files. The resubmission will require a fresh full audit cycle. Documentation may carry over; scores do not.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_audit_B3_CONSENSUS_C2.md.

This is the FINAL PASS for pp-tests_audit_B3.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Deliver all Python test source files (tests/adversarial/test_f*.py,
            | conftest.py, adv_helpers.py) and all fixture data the tests rely on.
            | Without these, no further review is possible.

P0 CRITICAL | Remove or qualify all numeric results (pass/fail counts, G8 floors,
            | timings, SHA256SUMS) in pp-tests_STATE.md:17,49-72 that cannot be
            | reproduced from code present in this diff.

P0 CRITICAL | Resubmit as a single self-contained unit. Remove the "chunk A"
            | rebuttal in pp-tests_AUDIT_RESPONSE.md:509-512,551 or include

---

# WINNER DETERMINATION

# WINNER: **Grok**

Grok delivered the highest-quality analysis overall. It was the only Cycle 1 model to correctly apply the materiality test from the outset — identifying that the diff contained zero executable code and therefore that every quantitative claim (26 PASS/0 FAIL, SHA256SUMS, per-family counts) was an unverifiable assertion rather than evidence. While Gemini and GPT-4o were seduced by the documentation's exceptional self-critical narrative and reviewed the *story* of the code's quality, Grok reviewed the *actual deliverable* and found it absent. This judgment proved correct in Cycle 2: all three models converged on Grok's framing, and the consensus scoring methodology explicitly adopted Grok's materiality test as the controlling standard.

**Criterion-by-criterion verdict:**

| Criterion | Winner | Reasoning |
|---|---|---|
| **Accuracy** | Grok | Its Cycle 1 findings were confirmed correct by all three models in Cycle 2. Gemini and GPT-4o both explicitly acknowledged they had been wrong and Grok had been right. |
| **Depth** | Grok | Uniquely identified: (1) the materiality failure, (2) the meta-violation of L-m applied to the audit process itself, (3) the unverifiability of absolute paths and portability, (4) the distinction between "audit of assertions" vs "audit of software." |
| **Actionability** | Grok | Flagged specific, concrete absences: named files (`conftest.py`, `adv_helpers.py`, `tests/adversarial/*.py`), specific line references (`STATE:17`, `STATE:49-56`, `STATE:58-72`), and specific law violations (L-m). Recommendations required no interpretation. |
| **Completeness** | Grok | Covered all sections with appropriate verdicts — COMPLIANT, PARTIAL, UNVERIFIABLE, and VIOLATION — rather than accepting documentation prose as evidence of compliance. |

---

# FINAL SECOND-PASS PRIORITY LIST

The following is the definitive ordered list of what to implement, weighted by consensus materiality, unanimous agreement, and blocking dependency order.

---

## PRIORITY 1 — BLOCKING: Deliver the Executable Artifact

**Implement unconditionally. Nothing else can be verified until this is done.**

### P1-A | Provide all missing Python test files
- `tests/adversarial/test_f1_*.py` through `test_f{N}_*.py` (all families documented in `COVERAGE.md`)
- `tests/adversarial/conftest.py` (network socket blocking, `CUDA_VISIBLE_DEVICES` clearing, `nvidia-smi` post-check)
- `tests/adversarial/adv_helpers.py` (all helper utilities referenced in documentation)
- All fixture files referenced by the tests

**Acceptance criterion:** `python3 -m pytest tests/adversarial -q` executes without import errors from a clean checkout.

### P1-B | Make the single command self-contained and portable
- Remove all hardcoded absolute paths (`/home/ultron/protocol_pulse/references`, `~/protocol_pulse`)
- Replace with `PP_REFS_DIR` environment variable with a documented default relative to the repo root
- Document the one required environment variable in `README` or `CONTRIBUTING`

**Acceptance criterion:** The command runs identically on any machine with the repo checked out, without manual path configuration.

---

## PRIORITY 2 — CRITICAL: Verify All Quantitative Claims Against Live Execution

**These cannot be accepted as true until P1 is complete. Treat all as unverified until CI confirms them.**

### P2-A | Reproduce the claimed 26 PASS / 0 FAIL result
- Run the delivered suite end-to-end on CPU
- Confirm per-family pass/xfail counts match `STATE.md` lines 49–56 exactly
- If any count diverges, the documentation must be corrected to match reality — reality is authoritative, documentation is not

### P2-B | Reproduce the G8 and L-b measurements
- Re-execute `gate_g8` and `gate_g17c` invocations documented in `STATE.md` lines 58–72
- Confirm the 9:16 timing and floor values are reproducible on a standard CPU machine
- Record the exact hardware spec used so the "under 5 minutes" law can be evaluated fairly

### P2-C | Verify SHA256SUMS against actual reference files
- Run the documented checksum verification against the actual files at `PP_REFS_DIR`
- Any mismatch is a P0 blocker on release authorization

---

## PRIORITY 3 — HIGH: Law Compliance Gaps (Partially Verifiable from Documentation Alone)

### P3-A | CPU ONLY — confirm the guard is implemented, not just described
- `STATE.md` lines 26–31 describe a multi-pronged CPU guard but supply no implementation
- After P1-A is delivered, audit `conftest.py` to confirm:
  - `CUDA_VISIBLE_DEVICES=""` is set before any import
  - GPU-dependent libraries are stubbed at import time, not at call time
  - `nvidia-smi` post-check is a hard `assert`, not a warning

### P3-B | Strict xfail — confirm no xfail can pass for the wrong reason
- The `AUDIT_RESPONSE.md` self-audit found 8 issues including xfail tests that could pass spuriously
- After P1-A is delivered, verify that every `@pytest.mark.xfail(strict=True)` marker:
  - Has a `reason=` string tied to a specific written request identifier
  - Fails on the *correct* assertion, not on an import error or fixture failure upstream

### P3-C | Fail closed — confirm release authorization requires byte-level match
- Verify that any missing reference file causes a `FAIL`, not a `SKIP` or a vacuous `PASS`
- Verify that the release gate (`gate_g8`) cannot be satisfied by a subset of the required measurements

---

## PRIORITY 4 — MEDIUM: Documentation Corrections (Post-Code-Delivery)

**These are only addressable after P1–P3 are resolved. Do not spend time here before the code exists.**

### P4-A | Reconcile all numeric claims with live execution results
- Update `STATE.md` pass/xfail counts, timing tables, and measurement floors to match what the actual suite produces
- Remove or clearly mark any forward-looking claims as "TARGET" rather than "MEASURED"

### P4-B | Classify portability assumptions explicitly
- Document minimum CPU spec required for "under 5 minutes" compliance
- Document whether `PP_REFS_DIR` files are committed to the repo, downloaded, or generated

### P4-C | Add a machine-readable manifest
- Provide a `tests/adversarial/MANIFEST.txt` listing every expected test file, its family, and its expected outcome (PASS or strict-xfail)
- This makes the "26 PASS" claim falsifiable by inspection, independent of execution

---

## PRIORITY 5 — LOW: Process Improvements for Future Audits

### P5-A | Require code-first submission policy
- The audit process should reject documentation-only diffs at intake
- A diff that contains no `.py` files in `tests/` is automatically returned for resubmission before model review begins
- This prevents the "seductive meta-narrative" failure mode that misled two of three models in Cycle 1

### P5-B | Establish a materiality checklist for auditors
- Before scoring any section, auditors must answer: "Does executable code exist in the diff that implements this claim?"
- If NO: the section score is 0/100 and the finding is logged as UNVERIFIABLE, not COMPLIANT
- This checklist should be prepended to every future audit brief

---

**Implementation order is strict for P1–P3. P4 and P5 may proceed in parallel after P1-A is merged.**