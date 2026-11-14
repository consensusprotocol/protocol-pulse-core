An audit of `pulse-sentence-law` / `combo-letterbox-quoteonly-v2`.

### Q1: CORRECTNESS

Yes, the changed functions appear to do what their docstrings and the governing laws state. The core of this change is a major refactoring to centralize and control GPU0 resource management, encapsulated in the new `pipeline/gpu0.py` module. This addresses a class of bugs where CUDA Out-of-Memory (OOM) errors were not being correctly identified, leading to silent failures or misclassified errors (e.g., an OOM during transcription being reported as 'transcription failed').

-   **OOM Handling:** The new module introduces a `Gpu0Stop` `BaseException` hierarchy, including `GpuOOM`. This is correctly used to prevent `except Exception` blocks from catching and misinterpreting these critical infrastructure failures. This is demonstrated and fixed in `transcript_store.py` (lines 1182-1184) and proven by the test change in `test_punct_word_pass.py` (lines 1067-1080). Similarly, OOMs during `nvenc` operations, which previously might have just caused a non-zero exit code, are now explicitly identified using `gpu0.raise_if_oom` (e.g., `render16.py:264`, `render_vertical.py:321`). This significantly improves correctness by ensuring the true cause of a failure is reported.

-   **State Management:** The `gpu0.py` module enforces a "one model at a time" policy via `swap_to` (line 1709). This function correctly unloads previously resident models (both Python objects and Ollama models) before loading a new one. The `Model` class (line 1841) uses a clever `__getattr__` implementation to prevent parts of a model object from being held by other code, which would prevent garbage collection and violate the one-model rule. This design prevents state from leaking between stages.

-   **Bounded Retries:** The `run_fresh.py:_attempts` function (lines 594-652) correctly implements the bounded retry logic from Law L-r. It specifically catches `GpuOOM`, attempts a full release of GPU resources, and retries the stage exactly once. A second OOM, or any other `Gpu0Stop` exception, correctly results in a `HOLD`. The logic to preserve the original OOM reason in the `HOLD` message, even if the retry fails for a different reason (lines 614-616), is robust.

-   **Fail Closed (M12):** The entire change strengthens the "Fail Closed" principle. By introducing a formal lease system (`gpu0.lease`) and checks for foreign processes (`gpu0.foreign`), the pipeline now stops with a clear `HOLD` if the GPU environment is not in a known-good state, rather than proceeding and risking a surprise failure. The pre-run check in `run_fresh.py:682` is a prime example.

One minor but important fix is in `render16.py:237`. The logic now correctly avoids forcing `CUDA_VISIBLE_DEVICES=0` during CPU-only test sessions, which previously could cause a test to unexpectedly acquire a GPU context, as noted in the `conftest.py` teardown docstring (line 2708).

### Q2: LAW COMPLIANCE

The changes are overwhelmingly focused on Law L-r, but they touch on others.

-   **SENTENCE LAW ... L-k:** **COMPLIANT.** The diff does not modify the logic of these laws. Changes in files like `sentence_law.py` are limited to adding `gpu0.swap_to("nvenc")` (line 802), which is an infrastructure change, not a logic change.
-   **L-n ... L-q, L-s ... L-x, AMENDMENTS:** **COMPLIANT.** These laws describe a future "moments-first" architecture and are noted as "Not yet built". This diff correctly does not attempt to implement them.
-   **L-r GPU0 NEVER SURPRISES A RUN:** **COMPLIANT.** This law is the primary driver for the entire diff.
    1.  **ONE OWNER:** **COMPLIANT.** Implemented via `flock` in `scripts/pulse_check_run.sh` (line 1217), the `gpu0.lease` context manager (`gpu0.py:1456`), and checks in `run_fresh.py` (line 681) and `preflight.py` (line 188).
    2.  **ONE MODEL AT A TIME:** **COMPLIANT.** Implemented by `gpu0.swap_to` (`gpu0.py:1709`) which unloads all other resident models. All model loading points (`cut_accept.py:82`, `story_semantics.py:859`, `qa_gates.py:1261`, etc.) are refactored to use this central path.
    3.  **BOUNDED SELF-HEAL:** **COMPLIANT.** Implemented exactly as specified in `run_fresh.py:_attempts` (lines 594-652).
    4.  **FOREIGN PROCESSES:** **COMPLIANT.** Implemented by `gpu0.foreign()` (`gpu0.py:1617`) and enforced at the start of runs (`run_fresh.py:682`) and before every swap (`gpu0.py:1716`).
    5.  **TESTS:** **COMPLIANT.** `test_gpu0.py` provides mocked unit tests. `test_gpu0_live.py` provides the required must-fail and back-to-back integration tests on a live GPU. The `PeakSampler` and reporting logic are implemented in `run_fresh.py` (lines 722, 707-714).
-   **LAW 20 / M2 (thresholds):** **COMPLIANT.** No gate thresholds are changed.
-   **M12 FAIL CLOSED:** **COMPLIANT.** This law is significantly strengthened. Previously, an OOM could be misinterpreted as a data-level failure (e.g., `punctuation_failed`). Now, it is correctly identified as an infrastructure failure, leading to a retry or a `HOLD`, which is a much safer "fail closed" behavior. See `transcript_store.py:1182`.
-   **LAW 22 (v2f reference):** **COMPLIANT.** The changes are infrastructural and should not affect the deterministic rendering of v2f.

### Q3: TESTS

The tests are extensive and directly prove the claims of the new architecture.

-   **`pipeline/conftest.py`:** This new file is excellent test infrastructure. It correctly isolates CPU vs. GPU test sessions, preventing test interference and bugs where a CPU test might accidentally touch the GPU. The `pytest_runtest_teardown` hook (line 2708) which checks for lingering GPU contexts in CPU sessions is a particularly strong piece of hardening.
-   **`pipeline/test_gpu0.py`:** Provides comprehensive unit tests for the new `gpu0` module using mocks. It validates the lease mechanism (`TestLease`), swap logic (`TestSwap`), OOM detection (`TestOutOfMemory`), and the `run_fresh` retry logic (`TestStageRunner`). The `test_e_fail_052...` test (line 2315) is a perfect example of a regression test, proving that a specific past failure (OOM misreported as "transcription failed") is now correctly handled.
-   **`pipeline/test_gpu0_live.py`:** This file provides the "must-fail" tests required by Law L-r on a real GPU. `TestForeignAllocationIsRefused` proves that stages will `HOLD` if a foreign process is on GPU0. `TestRealOutOfMemory` proves the retry mechanism works under a genuine, engineered OOM condition. `TestBackToBack` implements the required test of running the pipeline twice in a row and generating the peak memory table.
-   **Test Modifications:** Existing tests are updated to use the new `gpu0` API (e.g., `test_pulse_20261110_mustfail.py:1046`) or to assert the new, correct exception types (e.g., `test_punct_word_pass.py:1077`). The assertions are specific and not vacuous.

The test suite for this feature is exemplary. It not only tests the new code but also hardens the entire test environment against GPU-related side effects.

### Q4: VERDICT

No defects found. This is a comprehensive and high-quality implementation of a critical infrastructure hardening law (L-r). The code is well-structured, robustly designed, and thoroughly tested. It directly addresses the instability caused by unmanaged GPU resources and misidentified OOM errors, which was a likely root cause of the editorial defects that prompted this work.

-   **LOW** | `render16.py:237` | This is not a defect but an observation of a good fix. The change to `os.environ["CUDA_VISIBLE_DEVICES"]` logic prevents a CPU test session from being contaminated by GPU context, a subtle but important correctness fix.
-   **LOW** | `test_pinned.py:966` | This is another minor but good fix, anchoring a regex in a test assertion for more precision.

The changes fulfill all requirements of the feature description and associated laws. The introduction of `gpu0.py` is a major architectural improvement that will increase pipeline stability and reliability.

**VERDICT: READY**