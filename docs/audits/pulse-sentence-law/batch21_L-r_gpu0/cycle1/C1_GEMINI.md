An audit of the `pulse-sentence-law` feature on branch `combo-letterbox-quoteonly-v2`.

### Q1: CORRECTNESS

The changed functions appear to do what their docstrings and the governing laws state. The core of this change is the introduction of a new, centralized GPU management module, `pipeline/gpu0.py`, and its integration across the pipeline. This module correctly implements a robust leasing and resource management system.

-   **GPU Resource Management (`gpu0.py`):** The implementation of the GPU lease using `fcntl.flock` (lines 959, 1101) is correct for ensuring single ownership at the process level, and the logic to handle inherited file descriptors for child processes (`run_fresh.py` from `pulse_check_run.sh`) is sound (lines 1043-1053, 1605-1614). The `swap_to` function (line 1294) correctly centralizes the logic for unloading other models (`_resident` and Ollama models), checking for foreign processes, and verifying available memory against a requirements dictionary (`REQUIREMENT_MIB`, line 977) before a load. The use of a `BaseException` for `Gpu0Stop` (line 990) is a crucial and correct design choice to prevent application-level `except Exception:` clauses from incorrectly handling infrastructure failures, as proven by the new test in `test_gpu0.py` (line 1671).

-   **Error Handling and Retries (`run_fresh.py`):** The new `_attempts` wrapper method (lines 390-426) correctly implements the bounded self-heal rule from L-r(3). It distinguishes CUDA out-of-memory errors from other exceptions using `gpu0.is_oom` (line 406), performs exactly one retry after a full resource release (`gpu0.release_all`, line 422), and turns a second failure into a `Hold`. Other `Gpu0Stop` exceptions are correctly converted to a `Hold` without a retry (line 403). This prevents silent failures and makes the cause of failure explicit.

-   **State Leakage:** The "one model at a time" architecture enforced by `gpu0.swap_to` actively prevents state leakage between stages in the form of multiple models consuming GPU memory. Each `Model` object (`gpu0.py`, line 1401) is lazily loaded and is unloaded by any subsequent `swap_to` call for a different model, as demonstrated in `test_gpu0.py` (line 1635).

-   **Fail-Closed on Missing Data/Model Failure:** The new architecture strengthens the "fail closed" principle (M12). For example, a CUDA out-of-memory during transcription, which previously could be caught and misinterpreted as a per-video 'transcription failed' status (E-FAIL-052), is now guaranteed to propagate as a `GpuOOM` exception. This is explicitly tested and fixed in `pipeline/test_punct_word_pass.py` (lines 726-740) and `pipeline/transcript_store.py` (lines 843-845). The system is now far less likely to produce a pass (or a simple failure status) when an underlying infrastructure problem occurs.

### Q2: LAW COMPLIANCE

The diff demonstrates a strong focus on complying with the new laws, particularly L-r.

-   **SENTENCE LAW ... L-k (and others not related to L-r):** **COMPLIANT.** The diff does not modify the logic related to sentence boundaries, selection locks, cut snapping, audio levels, credits, sign-offs, or text canonicalization. The primary changes are infrastructural, governing *how* and *when* the processes that execute these laws get access to the GPU.
-   **L-r GPU0 NEVER SURPRISES A RUN:** **COMPLIANT.** This law is the primary driver for the entire diff.
    -   **(1) ONE OWNER:** Compliant. `scripts/pulse_check_run.sh` (lines 874-881) acquires the lease. `pipeline/gpu0.py` implements the `lease()` context manager and `held()` check. Every relevant entry point (`run_fresh.py` line 455, `preflight.py` line 153, `backtest.py` line 10, `replay.py` line 334) now acquires this lease.
    -   **(2) ONE MODEL AT A TIME:** Compliant. `gpu0.swap_to` (line 1294) is now the sole entry point for loading models. It unloads other models before verifying memory, and all direct instantiations of `WhisperModel`, etc., have been replaced with calls to factories like `gpu0.whisper()` (e.g., `cut_accept.py` line 55, `word_diff.py` line 860).
    -   **(3) BOUNDED SELF-HEAL:** Compliant. Implemented by `run_fresh.py`'s `_attempts` method (lines 390-426). It correctly retries OOM errors once and ensures both attempts are recorded in `PROVENANCE`.
    -   **(4) FOREIGN PROCESSES:** Compliant. The `gpu0.foreign()` check is performed at the start of a run (`run_fresh.py` line 456) and before every swap (`gpu0.py` line 1301).
    -   **(5) TESTS:** Compliant. A comprehensive suite of tests is added. `test_gpu0.py` tests the logic with mocks. `test_gpu0_live.py` (lines 1807-1961) provides must-fail tests on a live GPU, including a foreign allocation test and a real OOM test. The reporting requirement is met by adding a GPU peak memory table to `REPORT.md` (`run_fresh.py` lines 483-486 and 1235-1237).
-   **M12 FAIL CLOSED:** **COMPLIANT.** The changes significantly harden this principle. By making GPU errors explicit `Hold`s via `BaseException` subclasses, the risk of misinterpreting an infrastructure failure as a content-level failure is eliminated.
-   **LAW 22 (v2f reference):** **COMPLIANT.** The changes should not alter the byte-identical output of the v2f reference. In fact, compliance is strengthened. Where a previous run might have silently fallen back on a fallback outro due to an NVENC OOM (e.g., `render16.py`), the new code will raise a `GpuOOM` (`render16.py` line 225), correctly preventing a deviation from the expected render path.

The feature's purpose statement mentions fixing defects D1-D6. The code in this diff primarily implements Law L-r, which addresses GPU stability and OOM errors (related to a crash mentioned by PBX). It fixes the *cause* of errors being masked, but does not appear to directly change the editorial logic for D1 (clipped word), D2/D3 (mid-sentence cuts), D4 (warped avatars), D5 (letterboxing), or D6 (abrupt changes). This is not a violation, but a clarification of scope: this commit is the foundational infrastructure fix.

### Q3: TESTS

The added tests are comprehensive and directly prove the claims made by the new laws and code.

-   **`pipeline/test_gpu0.py`:** This new file provides excellent unit test coverage for the `gpu0.py` module using stubs for `nvidia-smi` and Ollama. It correctly tests the lease mechanism (re-entrance, busy state), swap logic (unloading, memory checks), and OOM detection. The assertions are specific and robust.
-   **`pipeline/test_gpu0_live.py`:** This is a critical addition, providing live "must-fail" tests on the actual GPU. `TestForeignAllocationIsRefused` (line 1867) is a very well-designed test that proves the foreign process check works by forking a separate process to hold GPU memory. `TestRealOutOfMemory` (line 1910) proves the bounded-retry logic by intentionally trying to allocate more memory than available. These tests prove the system behaves as designed under real-world failure conditions.
-   **`pipeline/test_punct_word_pass.py`:** The modification in `test_an_out_of_memory_is_never_a_failure_status` (lines 726-740) is a perfect example of a test proving a specific defect fix (E-FAIL-052). It shows that an OOM now raises `gpu0.GpuOOM` and does not result in a `'punctuation_failed'` status.
-   **`pipeline/test_pinned.py`:** The assertion is hardened by anchoring the regex (`^`) and adding an `assertNotIn` (lines 688-690), making it less likely to pass for the wrong reason.

The tests are not vacuous and provide strong evidence that the new GPU management system is correct and compliant with Law L-r.

### Q4: VERDICT

No defects found. The changes represent a significant and well-executed architectural improvement to GPU resource management, directly and thoroughly implementing the complex requirements of Law L-r. The test suite is extensive, with both mocked unit tests and live GPU integration tests that prove the system's correctness and resilience. This commit successfully hardens the pipeline against a class of infrastructure failures that were previously causing silent errors or misdiagnosed holds.

**READY**