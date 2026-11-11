Excellent. I will now review the code for the `pulse-sentence-law` feature.

---

### Q1: CORRECTNESS

The code appears to be of high quality and logically sound. The changed functions do what their docstrings and the feature description imply.

1.  **`pipeline/punctuation.py`:** This new module correctly implements the described strategy.
    *   `_key()` (line 30) correctly normalizes words for comparison, ignoring case and punctuation.
    *   `transfer()` (line 39) is the core of the logic. It correctly uses `difflib.SequenceMatcher` to find blocks of words that are identical (post-normalization) between the verbatim and reference transcripts. It only transfers trailing punctuation to words in these aligned blocks, and only if the verbatim word doesn't already have punctuation. This is a robust way to prevent corruption.
    *   The use of `out = [dict(w) for w in words]` (line 42) ensures the original word list is not mutated, which is good practice.
    *   The assertion `assert [_key(w["word"]) for w in words] == [_key(w["word"]) for w in record["words"]]` (line 67) is a critical correctness check. It programmatically guarantees that the process only adds punctuation and never changes the underlying words, which is essential for `SELECTION LOCK`.
    *   The `ensure()` function (line 61) correctly includes a fast path to skip processing for transcripts that are already punctuated, which is efficient.

2.  **`pipeline/sentence_law.py`:** The changes here are primarily removals and simplifications, which improve correctness by eliminating a faulty component.
    *   The `Adjudicator` class, identified as the source of errors, has been completely removed (lines 252-313).
    *   The `boundary()` function (line 318) is now simpler and more robust. The logic `if not is_punctuated(words, k): return {..., "valid": False, ...}` (lines 342-344) correctly implements the "fail closed" principle for unpunctuated sections. This removes the dependency on the unreliable LLM and replaces it with a deterministic, safer rule.

3.  **Error Handling & State:**
    *   The system upholds the **M12 FAIL CLOSED** law. If the ASR model in `punctuation.py` fails, it will raise an exception, halting the pipeline instead of producing a corrupt transcript and a false pass. Likewise, the new `boundary()` logic explicitly fails on missing data (i.e., missing punctuation).
    *   There is no apparent state leakage between clips. The removal of the `Adjudicator` instance, which was passed around, actually reduces the potential for such issues.

I find no issues with correctness in this diff. The logic is sound, well-tested, and includes strong internal assertions.

### Q2: LAW COMPLIANCE

The code appears to be fully compliant with all specified laws.

*   **SENTENCE LAW:** **COMPLIANT.** The diff directly implements a stricter and more reliable version of this law. The removal of the LLM adjudicator (diff lines 252-313) and the introduction of the "fail closed" rule for unpunctuated stretches (lines 222-225, 342-344) directly address the reported failures. Punctuation is now derived deterministically from a second ASR pass.
*   **SELECTION LOCK:** **COMPLIANT.** The lock is respected. Words are not recomputed. The new `punctuation.py` module is explicitly designed to preserve the original words, as proven by the assertion on line 67. This ensures that timings and word sequences from the original verbatim transcript remain unchanged.
*   **SNAP LIMIT:** **COMPLIANT.** The logic for placing cuts within a valid pause is unchanged. By making the definition of a "legal boundary" stricter, this law is now enforced more rigorously, as cuts can no longer be planned around the erroneous boundaries previously approved by the adjudicator.
*   **ONSET/TAIL:** **COMPLIANT.** The laws themselves are not modified, but the tests now correctly fail clips that violate them (e.g., test `TestD1HookOnset` on lines 439-449), demonstrating that the improved boundary detection allows these gates to function as intended.
*   **CREDITS:** **COMPLIANT.** This law is not relevant to the changes in this diff. The code does not touch avatar or credit generation.
*   **LAW 20 / M2:** **COMPLIANT.** No gate thresholds have been loosened. The criteria for a valid sentence boundary have been significantly tightened by removing the adjudicator and requiring explicit punctuation. This is the opposite of loosening a threshold.
*   **M12 FAIL CLOSED:** **COMPLIANT.** This is a core design principle of the change. Missing punctuation in a transcript stretch now results in a "fail" for any boundary check within it (line 343). An ASR or other model failure during punctuation restoration will raise an exception, which constitutes a rejection.
*   **LAW 22:** **COMPLIANT.** No rendering code is changed. The `v2f` reference path should re-render identically. This change affects clip selection and boundary validation, which happen *before* rendering. The reference asset, assuming it already complied with the stricter sentence law, would be processed identically.

### Q3: TESTS

The tests are comprehensive and effectively prove that the fix works and the original defects are caught.

1.  **Targeted Defect Tests:** The tests in `test_pulse_20261110_mustfail.py` are excellent. They don't just check for failure; they check for failure *for the right reason*.
    *   `TestD3Edges.test_d3b_clip02_in_fails` (lines 443-453) is a prime example. It correctly replaces a generic "outside the legal range" check with a much more specific assertion that the failure is because the word `"course"` does not end a sentence (`self.assertIn("does not end a sentence", r["why"], r)`). This proves the new lexical rule is the cause of the fix.
    *   The updated lock expectation (`"times."` instead of `"times"`, line 436) correctly verifies that the punctuation layer is active in the test fixture.

2.  **Testing the Core Flaw:** The new `TestUnpunctuatedTranscript` class (lines 463-512) is a direct and powerful demonstration of the fix.
    *   It explicitly tests and rejects the exact false positives the old adjudicator produced (e.g., `'the'|'wolf'`, `'of'|'all'`) on lines 502-507.
    *   It includes a control test (`test_true_sentence_ends...`, line 509) to ensure that valid boundaries are still accepted.
    *   `test_unpunctuated_gap_is_never_a_boundary` (line 495) directly verifies the new "fail closed" policy on the raw, unpunctuated transcript data.

3.  **Unit Testing the New Module:** The new `TestPunctuationLayer` class (line 528) provides strong unit tests for `punctuation.py`, validating its core claims: it doesn't change words (line 537), it preserves timings (line 538), it handles disfluencies correctly (line 540), and it uses the specified prompt (line 554).

4.  **Integration Test:** The GPU-dependent test `test_yahoo_fixture_is_reproduced_from_the_audio` (line 560) is a high-value integration test. It proves that the new punctuation pipeline can reproduce the expected (and now correct) punctuated transcript from the original audio that caused the problem, closing the loop entirely.

The tests are well-designed and leave no doubt that the problem is understood, fixed, and protected from regression.

### Q4: VERDICT

No defects were found in the provided diff. The changes are a significant improvement in quality and robustness, directly addressing the root cause of the reported editorial errors. The new system is more deterministic, less prone to error, and adheres strictly to the principle of "fail closed". The test suite is exemplary.

**READY**