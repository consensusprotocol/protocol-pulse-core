An audit of the `pulse-sentence-law` feature branch.

### Q1: CORRECTNESS
The changes appear to be of high quality, demonstrating a deep understanding of the problems identified in the 2026-11-10 cut. The code correctly implements its documented intentions.

-   **`pipeline/sentence_law.py`:**
    -   The move to a centralized `canon.py` for tokenization (lines 11, 30, 36) is a significant correctness and maintainability improvement, removing ad-hoc text processing.
    -   The fix for potential `NaN` values from `np.median` on flat envelopes (line 22) is robust, preventing a class of silent failures.
    -   The new anchor check (lines 46-47) correctly tightens the `SELECTION LOCK` by ensuring the match begins on the first token of the first word and ends on the last token of the last word, preventing partial-word matches.
    -   `edge_word_fidelity` is substantially improved. The new check `keep[n:].any()` (line 89) correctly implements the "every frame must be compared" rule from GPT-cut F07, preventing an alignment from being accepted if it doesn't cover the entire audible part of the word. The `gain_invariant` logic (lines 73-77, 93) correctly isolates the comparison from loudness changes in the final render.
    -   The new functions `_gain_db` and `span_matches` (lines 115-174) are well-designed. `_gain_db` correctly measures gain on the interior of a clip to avoid fades and uses interquartile range (`spread`) to ensure the gain is constant, which is a robust method. `span_matches` correctly uses a "run of bad frames" (lines 137-141) to detect insertions/deletions, which is more robust than a simple percentage of mismatched frames.
    -   `edges_on_final` correctly orchestrates the new checks, with a solid `try...except` block (line 211) that ensures any failure during measurement results in a failed check, upholding M12 FAIL CLOSED.

-   **`pipeline/word_diff.py`:**
    -   The replacement of complex, local normalization logic (lines 395-479 deleted) with a call to the new `canon.py` (line 487) is a major correctness win.
    -   The new logic in `gate_g18` (lines 510-521) to handle repeat-only differences is sophisticated and correct. It correctly isolates these specific cases, keeps the original difference as evidence, and uses the new `span_matches` for an acoustic tie-breaker. The `try...except` block (line 517) correctly handles measurement failures.

No state appears to leak between clips. Units seem correct (e.g., `HOP_S` is used consistently). The code paths for handling missing data or exceptions correctly result in failures rather than passes.

### Q2: LAW COMPLIANCE

-   **SENTENCE LAW:** COMPLIANT. The core logic is unchanged, but its inputs are now governed by `canon.py` (L-k), improving consistency.
-   **SELECTION LOCK:** COMPLIANT. Strengthened by the new anchor checks at lines 46-47.
-   **SNAP LIMIT:** COMPLIANT. No changes to the relevant logic.
-   **NEIGHBOUR:** COMPLIANT. No changes to the relevant logic.
-   **ONSET/TAIL:** COMPLIANT. No changes to the relevant logic.
-   **CREDITS:** CANNOT VERIFY. No relevant code in diff.
-   **L-a SIGN-OFF NAMES ALL:** CANNOT VERIFY. No relevant code in diff.
-   **L-b EDGE WORDS WHOLE:** COMPLIANT. Directly addressed by the major changes to `edge_word_fidelity` (lines 55-106), which now performs a more rigorous acoustic comparison of the edge words against the source.
-   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT. This is a primary focus of the commit. It is implemented by:
    1.  The new function `edges_on_final` (lines 184-214), which runs checks on the final render.
    2.  `edge_word_fidelity`'s `gain_invariant` mode (line 57, 210).
    3.  The rule that every word frame must be compared (line 89).
    4.  The acoustic adjudication for G18 repeat-only differences in `word_diff.py` (lines 510-521).
-   **L-d PROTECTED PREVIEW:** CANNOT VERIFY. The diff does not contain the regression script or its output.
-   **L-e PUNCTUATED BEFORE READ:** CANNOT VERIFY. The diff shows code that consumes transcripts but not the `transcript_store` that implements this law.
-   **L-f CHANNELS FIRST:** CANNOT VERIFY. No relevant code in diff.
-   **L-g WRITTEN FORMS:** PARTIAL. The code is compliant by delegating to `canon.py` (lines 481, 487). Final compliance depends on the (unseen) implementation of `canon.py`. The test at `test_word_diff.py:293-296` suggests it works as specified.
-   **L-h TEXT READ AS SPOKEN:** PARTIAL. Compliance depends on the unseen `canon.py`.
-   **L-i THE CLAIM IS THE EVENT:** CANNOT VERIFY. No relevant code in diff.
-   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT. The test `test_verdict_rules` (lines 265-284) is rewritten to enforce the "exact inventory" rule, ensuring that old, permissive verdicts now correctly HOLD the run.
-   **L-k ONE CANONICAL FORM:** COMPLIANT. This is a core theme of the change. Ad-hoc normalization is removed from `word_diff.py` (lines 395-479 deleted) and both `sentence_law.py` and `word_diff.py` are modified to use `canon.py` (e.g., line 11, line 487).
-   **LAW 20 / M2:** COMPLIANT. New thresholds are added as constants at the top of `sentence_law.py` (lines 109-112). No existing gate thresholds appear to have been loosened.
-   **M12 FAIL CLOSED:** COMPLIANT. New functions with I/O or processing risk have `try...except` blocks that correctly treat an exception as a failure (e.g., lines 211-212, 517-518).
-   **LAW 22:** CANNOT VERIFY. The diff does not show the v2f regression test results.

### Q3: TESTS
The tests are comprehensive and well-targeted. They successfully prove the claims made in the feature description and docstrings.

-   `test_fresh.py:265-284`: The rewrite of `test_verdict_rules` is excellent. It directly proves that the verdict logic has been tightened according to Law L-j by confirming that various non-`PASS` strings now correctly cause a `VERDICT_HOLD`.
-   `test_word_diff.py:301-318`: The new tests `test_a_repeat_only_difference_is_kept_as_evidence` and `test_units_and_signs_are_not_erased` precisely validate the new behaviors related to GPT-cut F05 and F04. They are not vacuous.
-   `test_word_diff.py:339-382`: The new class `TestSpanMatches` is a high-quality test. By creating synthetic audio with known properties (pass case: gain+noise+codec; fail case: a 300ms repeat), it provides strong proof that the `span_matches` function correctly identifies acoustically identical vs. different content, which is the foundation of the new acoustic adjudication logic.
-   `test_dec1_calibration.py:241-245`: The new test `test_an_outro_that_is_not_hash_identical_fails_outro_locked` correctly adds coverage for a previously missed failure case (GPT-cut F09).

The tests give high confidence that the fixes are effective and do not introduce regressions in the tested areas.

### Q4: VERDICT
This is a well-engineered set of fixes that directly address the reported defects and strengthen the quality gates significantly. The code is clean, the new logic is robust, and the tests are thorough. The primary risk is the dependency on the unseen `canon.py` module, but the diff provides strong evidence (through tests and usage patterns) that it functions as specified by the laws.

-   **MINOR** | N/A | Dependency on unseen `canon.py`. Compliance with laws L-g, L-h, and L-k is contingent on the implementation of `pipeline/canon.py`. This is an informational finding, as the code under review correctly uses the new module, but full system verification requires auditing `canon.py` as well.

The code in this diff is of high quality and correctly implements its stated purpose and the governing laws.

**READY**