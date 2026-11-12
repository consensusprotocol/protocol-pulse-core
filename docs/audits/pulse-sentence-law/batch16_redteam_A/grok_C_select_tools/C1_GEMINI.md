Excellent. This is a comprehensive set of changes aimed at hardening a complex media pipeline. I will now conduct my review as an independent AI model, focusing on the provided diff and the governing laws.

### **Q1: CORRECTNESS**

The changes appear to be of high quality and demonstrate a strong focus on robustness, testability, and maintainability.

*   **Centralized Normalization:** The replacement of ad-hoc regex-based text normalization (`_tok`, `_lc_words`, `_numbers`, `_norm`) with calls to a new `canon.py` module (e.g., lines 11-12, 36-37, 173-174) is a significant correctness improvement. It ensures that all text comparisons throughout the pipeline behave identically, eliminating a potential source of subtle bugs.
*   **Backtesting Framework:** The introduction of `backtest.py` and the corresponding hooks (`transcript_fn`, `words_fn`) in `editorial_select.py` (lines 54, 96) is a well-designed feature. It allows for regression testing of the selection logic on historical data with frozen inputs. The implementation correctly prioritizes different data sources (`offline_words` in `backtest.py`, lines 365-376) and prevents live, non-deterministic operations like downloading or transcribing during a backtest.
*   **Pre-flight Checks:** The new `preflight.py` script is a major operational improvement. It correctly checks for necessary conditions (GPU state, dependencies, API keys, git status) before committing to a potentially hour-long run. The exception handling (lines 665-667) correctly implements a fail-closed pattern, treating any error in a check as a failure.
*   **Robust Scripting:** The changes to `scripts/pulse_check_run.sh` are excellent.
    *   The inclusion of `preflight.py` before `run_fresh.py` (line 236) correctly implements the "fail fast" strategy.
    *   Using `9>&-` (lines 241, 250, 259) to prevent file descriptor inheritance for the lock is a sophisticated and correct way to prevent orphaned child processes from deadlocking the pipeline.
    *   Checking for the existence of final videos even after `run_fresh.py` exits 0 (lines 266-269) adds another layer of validation, correctly flagging a successful run that produced no output as a failure (`exit 70`).
*   **Path Portability:** Replacing hardcoded absolute paths like `/home/ultron/...` with dynamic, repository-relative paths (e.g., line 110, 115, 128) is a critical fix for ensuring the code can run in different environments without modification.

No obvious off-by-one errors, unit mismatches, or silent exceptions were identified in the diff. The new features seem well-isolated and correctly implemented.

### **Q2: LAW COMPLIANCE**

This diff introduces significant new code to better enforce and test the governing laws.

*   **SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / etc.:** These core laws governing the audio/video cutting logic are not directly modified. However, the introduction of `backtest.py` provides a powerful framework for ensuring that changes to selection logic do not violate text-level aspects of these laws. The new tests support this. **COMPLIANT**.
*   **L-k ONE CANONICAL FORM:** This law is the primary driver for many changes. The diff is fully **COMPLIANT**.
    *   `editorial_select.py` (lines 12, 23, 37, 45) and `story_semantics.py` (line 174) are updated to use the new `canon.py` module for all text processing, fulfilling the law's requirement.
*   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** The changes strongly support this law. **COMPLIANT**.
    *   `scripts/pulse_check_run.sh` is hardened. The new pre-flight check (line 236) adds a required gate before the main process begins. The updated exit code handling (line 269, `exit 70`) ensures that a run reporting success without producing the deliverable bytes is correctly stopped.
*   **L-e PUNCTUATED BEFORE READ:** The `backtest.py` script correctly respects this by checking for sentence-ready records (`ts.sentence_ready`, line 370) or using run transcripts that are already punctuated (`punctuation.needs_restoration`, line 358). **COMPLIANT**.
*   **M12 FAIL CLOSED:** The new code adheres strictly to this law. **COMPLIANT**.
    *   `preflight.py`'s main check runner explicitly treats any exception as a failure (line 666).
    *   `scripts/pulse_check_run.sh`'s new check for missing final files after a reported success (lines 266-269) is another example of failing closed.
*   **All Other Laws:** The diff does not introduce any visible violations of the other laws (`CREDITS`, `ONSET/TAIL`, `SIGN-OFF NAMES ALL`, `EDGE WORDS WHOLE`, `DISSENT IS RIGHT`, `PROTECTED PREVIEW`, `CHANNELS FIRST`, `WRITTEN FORMS`, `TEXT READ AS SPOKEN`, `THE CLAIM IS THE EVENT`, `LAW 20`, `LAW 22`, etc.). The changes are either orthogonal to these laws or provide infrastructure (like `backtest.py` and `canon.py`) that will make them easier to comply with and test in the future.

Overall, the law compliance of this diff is exemplary.

### **Q3: TESTS**

The new tests are comprehensive and well-written. They effectively prove the correctness of the new functionality.

*   **`test_preflight.py`:**
    *   The tests correctly use mocking to simulate various system states (e.g., a foreign process on the GPU in `test_a_foreign_job_on_gpu0_fails_and_our_ollama_runner_does_not`, a dirty git tree in `test_a_dirty_or_unpushed_tree_fails`).
    *   `test_an_exception_is_a_failed_check_and_any_failure_holds` correctly validates the "fail closed" principle.
    *   `test_secrets_never_reach_the_output` is an excellent and important test that proves sensitive information is used but not exposed in logs/output.
    *   `test_wrapper` is a clever integration test that verifies the shell script itself, ensuring the pre-flight check is actually wired in correctly. This is a very strong test.
*   **`test_backtest.py`:**
    *   The tests correctly isolate the functionality of `backtest.py`.
    *   `TestWordSources` effectively tests the data-sourcing priority logic, which is crucial for ensuring the backtest is hermetic.
    *   `TestHooks` is the most critical test. By patching `ts.acquire` to raise an `AssertionError`, it *proves* that the backtesting hooks prevent `select_story` from attempting any live transcription or GPU work. This is not a vacuous test; it would fail immediately if the hooks were implemented incorrectly.

The tests are of high quality and provide strong confidence in the new code.

### **Q4: VERDICT**

No defects were found. The changes are robust, well-tested, and significantly improve the pipeline's reliability, testability, and adherence to governing laws. The introduction of `preflight.py`, `backtest.py`, and the centralized `canon.py` module are all major architectural improvements.

**READY**