# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 22:43
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| **Correctness** | 7 | 8 | 9 | **7** |
| **Law Compliance** | 5 | 7 | 7 | **6** |
| **Test Coverage** | 8 | 8 | 9 | **8** |
| **Security / Fail-Closed** | — | 8 | 9 | **8** |
| **Overall Readiness** | NO | 7 | 8 | **7 — CONDITIONAL** |

> **Score rationale:** Gemini applied the most rigorous methodology (treating unverified dependencies as direct score penalties). The consensus adopts Gemini's lower bounds on Correctness and Law Compliance because those depressed scores reflect a genuine epistemic gap, not excessive caution. Fail-Closed is not independently scored by Gemini; GPT-4o/Grok agree at 8–9, consensus takes 8.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### UF-1 — `pipeline/canon.py` is unaudited and all text-normalization law compliance is contingent on it

**What it is:** The diff deletes all local normalization/tokenization logic from `sentence_law.py` (tokenizer, written/spoken-form expansion, currency handling) and from `word_diff.py` (lines 395-479 removed) and delegates entirely to the unseen `pipeline/canon.py`. Every claim of compliance with **L-g** (symbols), **L-h** (entities), and **L-k** (canonical form) now depends on code that was not part of this diff and has not been audited by any of the three models.

**File/Lines affected:** `pipeline/sentence_law.py:11, 30`; `pipeline/word_diff.py:487, 513`

**What to change:** Surface `pipeline/canon.py` in the PR diff. Run (or write) an isolated unit-test suite that exercises every branch of `canon.py` relevant to L-g, L-h, and L-k — number-to-word expansion, currency handling, punctuation assumptions, repeat collapsing, and spoken-form normalization. All tests must pass before merge. If the module already has tests, attach a passing CI run as evidence.

---

### UF-2 — LAW 22 / v2f regression artefact is absent

**What it is:** LAW 22 requires proof that no video-fingerprint hash has changed as a result of this diff. No `v2f` regression output, CI badge, or hash manifest is attached to the PR. All three models flagged this as "cannot verify."

**File/Lines affected:** CI / PR artefacts (not a source file); the regression is exercised via `regression_test.sh`.

**What to change:** Attach the full output of the `v2f` regression test run to the PR (committed artefact or pinned CI link). The output must show zero hash drift. This is a process requirement and cannot be satisfied by code changes alone.

---

## MAJORITY FINDINGS (2 of 3 models agree)

No majority-only findings exist in this cycle. Both systemic issues (UF-1, UF-2) achieved unanimous consensus. All other observations either (a) concern code quality already validated as strong, or (b) were raised by only one model (see Unique Insights below).

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 (Gemini only) — Local / function-scoped imports are an anti-pattern

**What it is:** Several key functions use `import canon` inside the function body rather than at module top level. Gemini notes this violates PEP 8, obscures the dependency graph at a glance, and carries a minor per-call overhead if the functions are called in tight loops.

**Files/Lines:** `pipeline/sentence_law.py:11, 30`; `pipeline/word_diff.py:487, 513`

**Assessment: IMPLEMENT — P2.** The finding is factually correct and the fix is a one-line move per site. There is no downside. It makes the dependency on `canon.py` explicit and visible to any future auditor at the top of the file, which directly supports the UF-1 remediation effort.

---

### UI-2 (Gemini only) — Structured exception logging missing in `edges_on_final` and `gate_g18`

**What it is:** The `try...except` blocks at `sentence_law.py:211` and `word_diff.py:517` correctly fail closed, but the `why` field in the detail dictionary captures only a string message, not a full structured traceback. In production, debugging a silent acoustic-measurement failure would require re-running the job under a debugger.

**Files/Lines:** `pipeline/sentence_law.py:211`; `pipeline/word_diff.py:517`

**Assessment: IMPLEMENT — P2.** Add `"exc": traceback.format_exc()` (or equivalent structured field) to the detail dict inside each `except` block. Zero risk, significant operational upside.

---

### UI-3 (GPT-4o only) — Error handling paths themselves are not explicitly tested

**What it is:** GPT-4o raised that while `try...except` blocks exist and are correct, there are no tests that deliberately inject an exception and assert that the fail-closed path returns `False` (or the expected HOLD verdict).

**Assessment: INVESTIGATE FURTHER — P1.** The existing test suite does not appear to cover the exception branch. A single parametrized test that patches the measurement function to raise, then asserts the result is `False`/HOLD, would close this gap. This is a real coverage hole, though not as severe as UF-1.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1 — Overall readiness verdict

| Model | Verdict |
|---|---|
| Grok | "Yes with conditions" (overall 8) |
| GPT-4o | "No" (overall 7) |
| Gemini | "No" (overall NO) |

**Tiebreaker — GEMINI/GPT-4o are correct.** Grok's "Yes with conditions" framing is semantically equivalent to the others but chose an optimistic label that understates the severity. The two conditions Grok identifies (canon.py audit, LAW 22 proof) are both P0 hard blockers that make the feature un-mergeable in its current state. The correct label is **NO — blocked**, not "yes with conditions." A "yes with conditions" label risks a reviewer treating the conditions as optional or post-merge cleanup. They are not.

---

### CONFLICT-2 — Correctness score (7 vs 8 vs 9)

| Model | Score |
|---|---|
| Gemini | 7 |
| GPT-4o | 8 |
| Grok | 9 |

**Tiebreaker — consensus at 7.** Grok scored correctness in isolation from the dependency; GPT-4o partially discounted for the dependency; Gemini fully discounted. Because correctness of the diff is *inseparable* from correctness of its sole text-normalization dependency, the lower score is the epistemically honest one. The code-within-the-diff is excellent; the system-level correctness is unproven.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

The following areas received unanimous positive assessment. They are locked. Do not alter them.

1. **`span_matches` function (lines 115-147)** — Correct implementation of interior-only acoustic comparison with ±2-hop tolerance; "run of bad frames" approach for insertion/deletion detection is robust.
2. **`_gain_db` function (lines 152-174)** — Correct use of IQR spread to verify gain is constant before accepting it; median over interior frames correctly avoids fade artifacts.
3. **`edges_on_final` function (lines 184-214)** — Correct fail-closed structure via `try...except`; correctly orchestrates G17c on final bytes; both sides are checked.
4. **Tightened anchor check (lines 46-47)** — Correctly prevents partial-word SELECTION LOCK matches; closes the class of off-by-one bugs described in the design doc.
5. **`edge_word_fidelity` every-frame rule (line 89: `keep[n:].any()`)** — Correctly implements GPT-cut F07; prevents alignment acceptance when coverage is incomplete.
6. **`gain_invariant` path in `edge_word_fidelity` (lines 73-77, 93)** — Correctly isolates comparison from loudness changes in the final render; aligns with L-c.
7. **`speech_bed_quiet` NaN fix (line 22)** — Correct fallback to `live` when `upper` is empty; prevents silent NaN propagation.
8. **`gate_g18` repeat-only handling (lines 510-521)** — Correct isolation of repeat-only cases; correct preservation of original diff as evidence for acoustic adjudication.
9. **Test suite additions** — `TestSpanMatches`, `test_a_repeat_only_difference_is_kept_as_evidence`, `test_units_and_signs_are_not_erased`, and updated verdict tests are all substantive and correctly probe the new behaviors.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|---|---|---|
| **SENTENCE LAW** | COMPLIANT (within diff) | Core logic unchanged; now routed through canon. |
| **L-k (canonical form)** | **UNVERIFIABLE** | Entirely dependent on unaudited `canon.py`. |
| **L-g (symbols)** | **UNVERIFIABLE** | Entirely dependent on unaudited `canon.py`. |
| **L-h (entities)** | **UNVERIFIABLE** | Entirely dependent on unaudited `canon.py`. |
| **L-b (fades stay in gap)** | COMPLIANT | `edges_on_final` correctly restricts proof to final bytes. |
| **L-c (gain-invariant comparison)** | COMPLIANT | `gain_invariant` path in `edge_word_fidelity` correctly removes gain before frame comparison. |
| **SELECTION LOCK** | COMPLIANT | Strengthened by new anchor checks at lines 46-47. |
| **SNAP LIMIT** | COMPLIANT | No changes to relevant logic; unchanged. |
| **LAW 22 (no v2f drift)** | **CANNOT VERIFY** | Regression artefact not attached. |
| **G17c** | COMPLIANT | `edges_on_final` correctly implements on final bytes. |
| **G18** | COMPLIANT (within diff) | `gate_g18` correctly handles repeat-only differences with acoustic tie-breaker. |
| **M12 (FAIL CLOSED)** | COMPLIANT | All `try...except` blocks produce `False`/HOLD on exception. |

**Net compliance verdict: PARTIAL.** Three laws are unverifiable. No laws are actively violated within the diff itself, but "not violated within the diff" is not equivalent to "compliant" when the enforcing logic lives in an unseen module.

---

## SECURITY CONSENSUS

No classical security vulnerabilities (injection, path traversal, privilege escalation, information disclosure) were identified by any model. The security analysis converged on one structural concern:

**Fail-Closed Integrity (8/10 — strong but gap noted):** All three models confirmed that `try...except` blocks in `edges_on_final` and `gate_g18` correctly fail closed. GPT-4o and Gemini both noted that the exception paths produce correct failure outcomes but lack structured observability (no traceback capture), which is a production-operations risk rather than a security risk. This maps to UI-2 above.

**Priority:** No P0 security items. UI-2 (structured logging) is P2 operational hardening.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as the gap between "good" and "world-class":

### WCG-1 — The dependency inversion is unproven (all 3 models)
A world-class audit of a refactoring that centralizes normalization into a shared module would include the shared module in the same PR, with its own test coverage committed alongside. The current structure forces the reviewer to trust an off-screen dependency. The fix is not complex — include `canon.py` in the diff and add its test file — but its absence is the single largest gap between this PR and a world-class submission.

### WCG-2 — Compliance proof is assertion, not evidence (GPT-4o + Grok)
Both models noted that LAW 22 compliance is currently an assertion ("we didn't change v2f logic, therefore no drift") rather than evidence (a passing regression run). World-class regulated-audio engineering attaches machine-generated proof to every compliance claim. This is a process maturity gap.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Surface `pipeline/canon.py` in the PR diff; add or attach a passing isolated unit-test suite covering L-g, L-h, L-k branches (number-to-word, currency, punctuation, spoken-form, repeat-collapse) | `pipeline/canon.py` + its test file | ALL 3 | Law compliance for L-g, L-h, L-k is entirely contingent on this module. Cannot verify compliance without it. Hard merge blocker. |
| **P0 CRITICAL** | Attach v2f regression output (committed artefact or pinned CI run) proving zero hash drift. `regression_test.sh` must show zero FAILs. | CI / PR artefacts | ALL 3 | LAW 22 requires machine-generated proof of non-drift. Assertion is not sufficient. Hard merge blocker. |
| **P1 HIGH** | Add fail-closed exception-path tests: patch measurement functions to raise, assert result is `False`/HOLD verdict for both `edges_on_final` and `gate_g18` | `tests/test_sentence_law.py`; `tests/test_word_diff.py` | GPT-4o (unique, but structurally sound) | The only untested code paths are the `except` branches. These are the paths most likely to mask bugs in production. |
| **P2 MEDIUM** | Move local imports to module-level | `pipeline/sentence_law.py:11,30`; `pipeline/word_diff.py:487,513` | Gemini | PEP 8; makes canon.py dependency visible at file top; directly supports future audits of UF-1. |
| **P2 MEDIUM** | Add `"exc": traceback.format_exc()` to the detail dict in both `except` blocks | `pipeline/sentence_law.py:211`; `pipeline/word_diff.py:517` | Gemini | Structured exception capture enables production debugging without job replay. Zero risk. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The code *within the diff* is of high quality. The acoustic adjudication logic, the tightened anchor checks, the every-frame coverage rule, the NaN fix, and the repeat-only handling are all correct, robust, and well-tested. In isolation, this is excellent work.

**The absolute final blockers are:**

1. **`pipeline/canon.py` must be audited.** The diff removes all local normalization logic and replaces it with an unseen module. Until that module is surfaced, reviewed, and covered by tests, compliance with L-g, L-h, and L-k cannot be asserted. This is not a risk to be accepted — it is an unknown.

2. **The v2f / LAW 22 regression proof must be attached.** A passing `regression_test.sh` output must be committed alongside the PR. No regression artefact = no LAW 22 compliance = no merge.

No other blockers exist. If both conditions are satisfied, the feature is ready to ship.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Surface pipeline/canon.py in the PR diff and add an isolated
            | unit-test suite covering every branch relevant to L-g, L-h,
            | L-k: number-to-word expansion, currency handling, punctuation
            | assumptions, spoken-form normalization, repeat collapsing.
            | All tests must pass. Without this, law compliance for L-g/L-h/L-k
            | is unverifiable and the feature cannot merge.
            | File: pipeline/canon.py + tests/test_canon.py

P0 CRITICAL | Run regression_test.sh and commit the output (or attach a pinned
            | CI run) proving zero v2f hash drift. This is the LAW 22
            | compliance proof. Must be attached before merge.
            | File: CI artefacts / regression_test.sh

P1 HIGH     | Add fail-closed exception-path tests for edges_on_final and
            | gate_g18. Patch the underlying measurement call to raise an
            | exception, then assert the return value is False and the verdict
            | is HOLD. This closes the only untested code paths in the diff.
            | File: tests/test_sentence_law.py; tests/test_word_diff.py

P2 MEDIUM   | Move all local/function-scoped `import canon` statements to
            | module-level at the top of each file. PEP 8 compliance and
            | makes the canon.py dependency visible to future auditors.
            | File: pipeline/sentence_law.py:11,30; pipeline/word_diff.py:487,513

P2 MEDIUM   | In both except blocks, add "exc": traceback.format_exc() to the
            | detail dictionary to enable structured production debugging.
            | File: pipeline/sentence_law.py:211; pipeline/word_diff.py:517

VALIDATED (do NOT touch — all 3 models confirmed excellent):
- span_matches function (lines 115-147): interior-only comparison, ±2-hop tolerance, run-of-bad-frames logic
- _gain_db function (lines 152-174): IQR spread check, interior-frame median
- edges_on_final function (lines 184-214): fail-closed structure, G17c on final bytes, both-sides check
- Anchor check (lines 46-47): tightened SELECTION LOCK, prevents partial-word matches
- edge_word_fidelity every-frame rule (line 89): keep[n:].any() check, GPT-cut F07 implementation
- gain_invariant path in edge_word_fidelity (lines 73-77, 93): gain removal before frame comparison
- speech_bed_quiet NaN fix (line 22): fallback to live when upper is empty
- gate_g18 repeat-only handling (lines 510-521): isolation, evidence preservation, acoustic tie-breaker
- Full test suite additions: TestSpanMatches, repeat-only evidence test, units/signs test, verdict tests

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Gemini

Gemini delivered the highest-quality analysis across both cycles by applying the most rigorous methodology — treating unverified dependencies as direct score penalties rather than positive refactoring signals, and correctly identifying the `canon.py` audit gap and LAW 22 regression absence as systemic P0 risks before the consensus formed. Its assessments proved most accurate in Cycle 2 (adopted as the consensus lower bounds), deepest in coverage (sole model to flag both MF-1 and MF-2 independently with detailed justification), and most actionable (specific file/line callouts with precise remediation steps).

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — BLOCKING (do not merge until resolved)**

1. **Audit and surface `pipeline/canon.py`** *(UF-1)*
   - Add full diff of `canon.py` to the PR
   - Write/run isolated unit tests covering: number-to-word expansion, currency handling, punctuation assumptions, repeat collapsing, spoken-form normalization
   - Explicitly verify L-g, L-h, L-k compliance in each branch
   - Attach passing CI run as merge evidence

2. **Attach LAW 22 / v2f regression artifact** *(UF-2)*
   - Produce and attach the `v2f` regression test output proving the reference hash is unchanged post-refactor
   - If no existing test covers this, write one before merge
   - Compliance cannot be asserted from the diff alone

**P1 — HIGH (resolve before or immediately after merge)**

3. **Validate `edge_word_fidelity` gain-invariant path against `canon.py` outputs**
   - The `offset_s` + `gain_invariant` logic (lines 73-77, 93) is only as correct as the tokens it receives from `canon.py`; integration test needed end-to-end, not just unit-level

4. **Stress-test `_gain_db` IQR spread threshold**
   - The `spread` guard for constant-gain detection is robust in design but has no adversarial test case (e.g., gain ramp, compression artifact); add at least one must-fail synthetic case

5. **Confirm `span_matches` SPAN_EDGE_S exclusion is law-referenced**
   - The edge-exclusion constant is used but not traced to a specific law citation in comments; add inline reference to prevent silent relaxation in future patches

**P2 — MEDIUM (schedule within one sprint)**

6. **Add `speech_bed_quiet` NaN guard regression test**
   - The fix (line 22, `np.median` on flat envelope) prevents silent failure but has no dedicated test; add a synthetic flat-envelope case asserting non-NaN output

7. **Extend `TestSpanMatches` with codec-mismatch and ramp-gain adversarial cases**
   - Current synthetic bursts cover same-span pass and 300ms repeat fail; gap-and-insertion and non-constant-gain cases are untested

8. **Document `canon.py` contract formally**
   - Add a module-level docstring or companion spec file stating exactly which laws `canon.py` is responsible for satisfying, so future audits have a clear compliance boundary

**P3 — LOW (backlog, non-blocking)**

9. **Add `Security / Fail-Closed` score to Gemini's audit template**
   - Scoring gap noted in consensus; standardize the rubric across all three models for Cycle 3 consistency

10. **Review `try...except` scope in `edges_on_final` (line 211)**
    - The broad catch upholds M12 FAIL CLOSED correctly, but log verbosity on caught exceptions should be verified — silent swallowing of unexpected errors would obscure root-cause diagnosis in production