# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: pulse-sentence-law

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

My Cycle 1 review correctly identified that the diff primarily contained a test suite and treated it as a Test-Driven Development (TDD) contract. However, reviewing the other models' outputs revealed nuances I had understated or missed:

*   **Grok's Methodological Stance:** I treated the absence of implementation code as an expected part of the TDD process. Grok took a stricter, more literal stance: "no implementation, no review." While I disagree with this as a blocker, Grok's position correctly highlights the inherent risk: this entire diff is a high-quality *promissory note*, and its value is zero until the implementation code is delivered and makes the tests pass.
*   **Gemini's Insight on `inspect.getsource`:** I noted the tests were comprehensive but did not call out the specific and powerful pattern used in `TestTautology` and `TestD4Credits` (lines 173-178, 235-240). Gemini correctly identified that using `inspect.getsource` to assert that buggy function names are *physically absent* from the source code is a much stronger guarantee against regression than merely testing behavior. It directly enforces laws like SELECTION LOCK by proving the code path that violated it has been excised.
*   **Gemini's Analysis of Fixture Setup:** I validated the tests' logic, but Gemini's analysis of `_G16Fixture.setUpClass` was more insightful. It correctly pointed out that the test doesn't use a static, pre-canned `selection_lock`; it programmatically *rebuilds* the lock from the editor's original selection JSON (`B3_chosen.json`). This is a critical detail, as it proves the test is validating against the true ground truth, making the SELECTION LOCK law enforcement much more robust.
*   **GPT-4o's Minor Polish:** GPT-4o suggested minor but valuable improvements to test clarity, such as adding more descriptive assertion messages and specifying the expected exception message in `assertRaises`. These are good hygiene points I overlooked.

### 2. WHERE DO YOU AGREE OR DISAGREE?

*   **U1: The diff contains no implementation.**
    *   **Agree.** This is a fact. The disagreement among models was methodological. I agree with the consensus view (Gemini, GPT-4o) that in a TDD workflow, the test suite itself is the primary artifact for review in the first pass. Grok's "NOT READY" verdict is too rigid for this context, but its caution is well-founded.

*   **M1: Test suite is correctly structured as TDD / "must-fail".**
    *   **Agree.** The file is explicitly named `mustfail.py`, and the docstring (lines 45-67) clearly lays out which defects (D1-D4) should cause test failures and which controls must pass. This is an exemplary use of a test suite as a specification for a bug fix.

*   **M2: `M12 FAIL CLOSED` is correctly enforced by `allow_model=False`.**
    *   **Strongly Agree.** Both Gemini and GPT-4o flagged this on line 118. Using a fixed, pre-populated cache and disabling live model calls is crucial for deterministic testing and directly upholds the M12 law by ensuring any unforeseen case (a cache miss) results in a hard failure, not a non-deterministic pass.

*   **M3: `inspect.getsource` assertions are a powerful enforcement pattern.**
    *   **Strongly Agree.** As noted above, Gemini's observation here was excellent. These tests (lines 173-178, 235-240) go beyond behavioral testing to enforce architectural constraints, ensuring that specific, problematic code is permanently removed, which is a powerful way to prevent regressions.

*   **GPT-4o's Minor Findings:**
    *   **Agree.** The suggestions to improve assertion messages (line 139) and make `assertRaises` more specific (line 232) are valid, low-priority improvements that would enhance test maintainability.

### 3. NEW FINDINGS FROM THIS REVIEW

After synthesizing the other models' feedback, my main new finding is not a defect but a higher-level observation on the quality of the diff:

*   **The test suite is not just a test; it's a nearly perfect "Request for Implementation".** It precisely specifies the bugs from the `GOSPEL` document, provides the exact data that triggers them, and even includes tests to prove that the eventual fix doesn't take forbidden shortcuts (like recomputing words or using thumbnail fallbacks). The test that rebuilds the `selection_lock` from the editor's choices is particularly strong. This level of specification in a test suite dramatically de-risks the subsequent implementation phase.

### 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Correctness | 8/10 | 9/10 | Increased confidence after a deeper look at the fixture setup and mocking strategies, prompted by Gemini's analysis. The test logic is more robust than I initially appreciated. |
| Law Compliance | 9/10 | 10/10 | The `inspect.getsource` tests, which I previously undervalued, are a direct and potent enforcement of multiple laws by ensuring the removal of non-compliant code. This warrants a perfect score for how the *tests* embody the laws. |
| Test Quality | 9/10 | 10/10 | For its explicit purpose as a "must-fail" regression suite to guide a fix, this is exemplary. It covers failures, controls, specific reasons for failure, and even source code structure. |

### 5. FINAL PRIORITY LIST

The primary "action item" is for the developer to deliver the implementation. The following are change requests for the *current diff*, although they are minor.

*   **P0 CRITICAL: The implementation code that satisfies this test suite must be delivered for review.** The files `pipeline/sentence_law.py`, `pipeline/run_fresh.py`, `pipeline/shoutout.py`, and `pipeline/select_passages.py` are currently missing from the feature branch.
*   **P2 MEDIUM:** `pipeline/test_pulse_20261110_mustfail.py`, line 232: Strengthen the `assertRaises` check to also validate the content of the error message using `assertRaisesRegex`. This ensures the function is failing for the intended reason (e.g., non-square avatar).
*   **P2 MEDIUM:** `pipeline/test_pulse_20261110_mustfail.py`, throughout: In tests that assert a gate failure (e.g., line 139, `self.assertFalse(r["pass"], r)`), consider adding a more specific `msg` to the assertion to improve debuggability, explaining *why* the failure is expected based on the defect (e.g., `msg="D1: Hook onset should fail due to insufficient genuine lead-in"`).

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The highest-leverage action is to **implement the required logic in the application code that makes this exacting, "must-fail" test suite pass without altering the tests' intent.**

### 7. PRODUCTION READY?

**Yes, with conditions.**

This diff, containing only the test contract, is ready to be merged *to the feature branch*. It is not ready for production. The conditions for this feature to be considered production-ready are:

1.  **Implementation Provided:** The developer must provide the implementation changes to `sentence_law.py`, `run_fresh.py`, `shoutout.py`, `select_passages.py`, and any other necessary files.
2.  **Tests Pass:** With the new implementation, the `test_pulse_20261110_mustfail.py` suite must run and pass. Specifically, all `must-fail` assertions (e.g., `self.assertFalse(gate_result)`) will need to be inverted (to `self.assertTrue(gate_result)`) by the developer to reflect the new, correct behavior, and the suite must be green.
3.  **No Regressions:** The control tests (`test_d3c_clip02_out_control_passes`, `test_v2f_finals_pass_g15_and_g12`) must continue to pass.
4.  **Full Review of Implementation:** The implementation code itself must undergo a full audit cycle.