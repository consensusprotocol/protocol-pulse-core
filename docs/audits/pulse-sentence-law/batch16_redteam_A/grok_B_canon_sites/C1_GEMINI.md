An audit of the `pulse-sentence-law` feature follows.

### Q1: CORRECTNESS

The code appears to be of high quality and systematically addresses the issues it sets out to solve.

1.  **Centralization of Logic:** The primary change is the introduction of `pipeline/canon.py` and the removal of ad-hoc text normalization logic from at least 7 other files. This is a massive improvement in correctness and maintainability. The old implementations were scattered, inconsistent, and, as evidenced by the feature's purpose, buggy (e.g., the original `_g3b_words` in `qa_gates.py`). The new `canon.py` provides a single, extensively tested source of truth for text comparison.

2.  **Robustness of `canon.py`:** The implementation in `canon.py` is thorough.
    *   It correctly handles a wide range of transformations: HTML entities, Unicode normalization (`NFKC`), case folding, and joining of split tokens from Whisper (e.g., `'$81' ' ,000'` -> `'$81,000'`).
    *   The number parsing is sophisticated, handling digits, spelled-out numbers (`_words_number`), suffixes (`k`, `M`, `B`), and spoken-order currency/percentages. The use of a state machine with `owed` (lines 538, 574) to correctly place the word "dollars" after a numeric amount is a good, robust design.
    *   The distinction between `canon_tokens(heads=True)` for `stand_alone.py` (line 144) and the default behavior shows careful consideration of different use cases.

3.  **Gate Logic Improvements:** The gates are made more reliable.
    *   In `segment_v1/qa_gates.py`, the `_says` helper function (line 360) replaces substring matching (`alias in t_lower`) with a contiguous token-run match. This is far more precise and less prone to false positives (e.g., matching "in" inside "binance").
    *   The change in `gate_g3b` (lines 331-333) to use the `selection_lock` text as context for the final word is a crucial and subtle correctness fix. It allows `canon.py` to correctly interpret multi-word phrases like "40 trillion", which it couldn't do if it only saw the last word, "trillion".
    *   The `word_overlap` function (line 213) is corrected to return `0.0` for an empty reference, fixing a potential "pass on missing data" bug and adhering to `M12 FAIL CLOSED`.

4.  **Configuration and Pathing:** The removal of hardcoded absolute paths like `/home/ultron/...` in `gates.py` (lines 73, 93) in favor of relative paths (`os.path.join`) makes the code more portable and robust.

I see no obvious off-by-one errors, state leakage, or pathways that would produce a `PASS` on failed models or missing data. The changes are systematic and well-reasoned.

### Q2: LAW COMPLIANCE

The diff shows a strong focus on complying with the new and existing laws.

*   **L-g WRITTEN FORMS:** COMPLIANT. This is a core focus of the change. The new `canon.py` module explicitly implements the required logic (e.g., '$40 trillion' -> '40 trillion dollars'), and the old, insufficient implementation in `qa_gates.py` (lines 290-322) is correctly removed. The test in `test_g3b_majority.py` (lines 161-178) directly verifies this.
*   **L-h TEXT READ AS SPOKEN:** COMPLIANT. `canon.py`'s `fold` function (line 478) handles HTML entity decoding. The `_SPLIT` regex (line 460) and `canon_aligned`'s logic (lines 615-618) handle joining split tokens.
*   **L-k ONE CANONICAL FORM:** COMPLIANT. This is the central principle of the entire diff. The creation of `pipeline/canon.py` and the systematic refactoring of `cut_accept.py`, `editorial_gate.py`, `gates.py`, `pinned.py`, `stand_alone.py`, and `segment_v1/qa_gates.py` to use it directly implements this law. The `TestSites` class in the new `test_canon.py` (line 825) even includes a "grep test" to enforce this law across the codebase, which is exemplary.
*   **L-a SIGN-OFF NAMES ALL:** COMPLIANT. The comparison logic for spoken channel names in G20 (`gates.py`, line 83) and G13 (`qa_gates.py`, line 406) is now routed through `canon.py`, making it more accurate and compliant with L-k. The G13 check is also improved from a substring search to a token-sequence match.
*   **M12 FAIL CLOSED:** COMPLIANT. In `qa_gates.py` (line 213), the `word_overlap` function is changed to return `0.0` (fail) when the reference text is empty, instead of `1.0` (pass).
*   **LAW 20 / M2:** COMPLIANT. No gate thresholds are loosened. The logic is made stricter.
*   **The following laws are supported by these changes but not fully implemented within this diff:**
    *   `SENTENCE LAW` & `L-e PUNCTUATED BEFORE READ`: The changes in `punctuation.py` (line 125) make the alignment process (which transfers punctuation) more robust by using a canonical key, but the core punctuation logic itself isn't in this diff. The use of `canon.py` in all word comparisons is a necessary prerequisite for reliable sentence boundary checks.
*   **The following laws are not violated and appear unaffected by this diff:**
    *   `SELECTION LOCK`, `SNAP LIMIT`, `NEIGHBOUR`, `ONSET/TAIL`, `CREDITS`, `L-b`, `L-c`, `L-d`, `L-f`, `L-i`, `L-j`, `LAW 22`.

### Q3: TESTS

The tests are comprehensive and of very high quality.

1.  **`test_canon.py`:** This new test suite is excellent.
    *   **Equivalence Testing:** `TestEquivalence` (line 711) uses a property-based approach, applying various mutations (HTML entities, Unicode, split tokens, number formats) to 200 real sentences and asserting they all resolve to the same canonical form. This provides high confidence in the normalization logic.
    *   **Difference Testing:** `TestDifferences` (line 786) provides the critical negative case, ensuring that genuinely different text (a different number, a dropped word, "it's" vs "its") does *not* compare equal. This prevents the normalization from being over-aggressive.
    *   **Alignment Testing:** `TestAligned` (line 807) correctly verifies that `canon_aligned` produces tokens consistent with `canon_tokens` and that the word ownership indices are valid. The specific test for `["$81", ",000"]` (line 821) is a perfect, targeted unit test.
    *   **Architectural Enforcement:** `TestSites` (line 825) is an outstanding piece of testing. It programmatically enforces Law L-k by scanning the codebase for forbidden ad-hoc normalization patterns. This goes beyond testing the module; it tests the module's *correct integration* across the entire pipeline.

2.  **`test_g3b_majority.py`:** The refactoring of the tests (lines 161-178) to check for canonical equivalence (`same(a, b)`) rather than an exact list representation is a significant improvement. It makes the tests more robust to implementation changes in `canon.py` while still correctly verifying the behavior required by Law L-g.

The tests are not vacuous and provide strong proof that the new code is correct and the old bugs are fixed.

### Q4: VERDICT

This is a high-quality, systematic, and well-tested refactoring that addresses multiple systemic issues related to text comparison. It directly implements several new laws and strengthens compliance with others.

| SEVERITY | DIFF LINE | ISSUE | FIX |
| :--- | :--- | :--- | :--- |
| **MAJOR** | 414-629 | Widespread, inconsistent, and buggy ad-hoc text normalization across the pipeline, violating L-k and causing gate failures (e.g., misreading currency). | A single, canonical text representation module (`pipeline/canon.py`) was created and all comparison sites were refactored to use it. |
| **MAJOR** | 406, 1506 | Inaccurate substring matching was used for checking channel names and keywords in gates G13/G20, leading to potential false positives. | Replaced with a robust token-sequence matching function (`_says` in `qa_gates.py`) that operates on canonical tokens. |
| **MEDIUM** | 213 | Gate `word_overlap` could produce a false pass (100% match) if the expected reference text was empty, violating `M12 FAIL CLOSED`. | The function now returns `0.0` (failure) for an empty reference set. |
| **MEDIUM** | 330-333 | Gate G3b's check on the last word could fail if that word was part of a multi-word number or currency expression (e.g., "trillion" in "$40 trillion"). | The gate now reads the last few words from the `selection_lock` text to provide context for canonicalization. |
| **LOW** | 73, 93 | Hardcoded absolute paths (`/home/ultron/...`) were used, making the code non-portable. | Paths were replaced with dynamic, relative paths using `os.path.join`. |

The changes are exemplary. The code is clean, the centralization of logic is a huge architectural win, and the quality of the tests—particularly the meta-test to enforce coding standards—is outstanding.

**READY**