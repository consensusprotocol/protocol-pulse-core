### Foreword
This is a well-executed set of changes that directly addresses the three test wall failures and the integrator's questions. The analysis is sharp, the test adaptations are precise, and the new documentation clarifies the interaction between this test suite and the new Law L-r. The developer has shown a deep understanding of both the production code's new failure modes and the test suite's purpose.

---
## YOUR REVIEW TASK

### SECTION 1: CORRECTNESS
The code under review consists of tests and documentation only. My analysis of correctness therefore applies to the logic of the tests themselves.

1.  **`test_f0_cpu_guard.py`:**
    *   The new `_resolve(name)` function (`test_f0_cpu_guard.py:217-227`) is a significant improvement in correctness. The previous file-based name matching was brittle and incorrectly identified `pipeline/conftest.py` as being imported by the test suite. The new logic correctly uses Python's own import resolution mechanisms (`sys.modules` and `importlib.util.find_spec`), which is the ground truth for what code is actually running. The added control assertion at line 239, which verifies `conftest` resolves to the suite's own file, is excellent defensive programming.
    *   The updated `test_every_whisper_load_is_refused_and_recorded` (`test_f0_cpu_guard.py:256-283`) is also correct. It now accurately models the two layers of protection: a direct `faster_whisper` import is caught by the test's stub, while a pipeline-mediated load via `word_diff.Transcriber` is caught earlier by `gpu0.LeaseMissing`. The test correctly asserts that the `Transcriber` is lazy-loaded and that the exception is raised on first *use* (`.span()`), not on construction. The assertions that the stub was not reached in the second case (line 282) and that the model is not marked as loaded (line 283) are precise and non-vacuous.

2.  **`test_f2_provenance.py`:**
    *   The change to `test_a_transcript_of_other_bytes_is_never_used` (R-10 pin) at `test_f2_provenance.py:303-327` is a correct adaptation to L-r. The proof that a re-transcription was *attempted* is no longer a call to the `faster_whisper` stub, but the `gpu0.LeaseMissing` exception raised by `gpu0.require`. This is a valid and robust way to detect the attempt in the new architecture.
    *   The change to `test_a_failed_transcription_stops_select_cleanly` (R-27 pin) at `test_f2_provenance.py:339-361` is a smart solution to the integrator's question. By mocking `_whisper_transcribe` to return `None`, the test now faithfully simulates an ordinary transcription failure (as documented in `select_passages.py`) without being intercepted by the `gpu0` lease guard. The control assertion at line 357 correctly ensures that the mocked failure was actually attempted before the test checks for the `KeyError` defect, preventing a false pass if the code were to crash for a different reason beforehand.
    *   The new test `test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing` (`test_f2_provenance.py:363-375`) is excellent. It directly answers the integrator's question, correctly asserts that a `BaseException` (`LeaseMissing`) propagates out of `_select`, and verifies the critical side-effect: no partial state (`edl.json`, transcript) is written to disk. This pins the expected "fail closed" behavior of L-r.

Overall, the logical flow of every modified test is sound, addresses the changes in the underlying production code, and strengthens the quality gate.

### SECTION 2: LAW COMPLIANCE
*   **`pp-tests` writes TESTS ONLY:** COMPLIANT. The diff only modifies files within `docs/` and `tests/adversarial/`.
*   **Never change what a check accepts to make something pass:** COMPLIANT. The checks were not loosened. They were adapted to detect a different, but equally valid, signal of the behavior being tested (e.g., `LeaseMissing` as proof of a transcription attempt). The R-27 pin still correctly fails on the `KeyError`.
*   **Nothing measured is never a pass (L-m):** COMPLIANT. All new and modified tests have specific, non-vacuous assertions. For example, `test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing` asserts not only the exception type, but also that specific files are *not* created.
*   **Fail closed (L-j):** COMPLIANT. The tests and the analysis (e.g., the new passing test for `Gpu0Stop`) are built around this principle.
*   **Pinned defects are `xfail`, preconditions are `pytest.fail`:** COMPLIANT. The modified `xfail`s remain `strict=True, raises=AssertionError`. The use of `H.control` for preconditions is consistent.
*   **CPU only, no network:** COMPLIANT. The changes reinforce this by explicitly testing the behavior of the `gpu0` lease mechanism in a CPU-only environment where `CUDA_VISIBLE_DEVICES` is empty. The `LeaseMissing` exceptions are the direct result of this law being enforced.

### SECTION 3: SECURITY
Not applicable. The diff contains only test code and documentation, with no production logic, user-facing endpoints, or data handling.

### SECTION 4: FRONTEND QUALITY
Not applicable. The diff contains no frontend code.

### SECTION 5: BACKEND QUALITY
Not applicable. The diff contains no backend service code. The analysis of the backend code for the purpose of writing tests is of high quality.

### SECTION 6: WORLD-CLASS GAP ANALYSIS
The feature under review is the test suite itself. In this context, the work is already at a world-class level. The practice of:
1.  Maintaining a "Bible" of learned lessons (`BIBLE_ADDITIONS`).
2.  Explicitly documenting test failures and their resolutions for institutional memory (PP-E26, E27).
3.  Proactively filing well-researched requests against other teams based on findings during test development (R-29).
4.  Adapting tests with surgical precision to changes in production architecture (the L-r adaptations).

This is a sign of a mature, high-functioning quality assurance process. Bloomberg's internal testing and QA processes are famously rigorous, and this work would not be out of place there. There is no significant gap to report; this is exemplary.

### SECTION 7: SCORES (0-100 each)
*Scores relate to the quality of the test suite modifications.*
- Backend logic:    100/100
- Frontend/UI:      N/A
- Error handling:   100/100
- Security:         N/A
- Performance:      N/A
- Law compliance:   100/100
- World-class gap:  100/100
- **OVERALL:          100/100**

### SECTION 8: PRIORITY ACTION PLAN
There are no defects in this diff. The purpose of this branch was to fix test failures and answer the integrator's questions, which it has done successfully. No action is required on this code.

**P0 CRITICAL** | None.
**P1 HIGH**     | None.
**P2 MEDIUM**   | None.
**P3 LOW**      | None.

### SECTION 9: THE ONE THING
The rigorous adaptation of the test suite to law L-r, especially the clear distinction and testing of different failure layers (lease refusal vs. stub refusal vs. ordinary error), is a model for maintaining test integrity against a changing production codebase.

### SECTION 10: FINAL VERDICT
This code is ready for production merge. The changes meticulously and correctly resolve all three test-wall failures, demonstrating a deep understanding of the new L-r architecture. The addition of a new passing test to pin the expected `Gpu0Stop` behavior and the detailed documentation updates make this an exemplary contribution that strengthens the project's quality gates.