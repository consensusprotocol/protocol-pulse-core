<!-- qwen/qwen3.8-27b, 79 s, finish stop, $0.0047 (vendor usage.cost) -->

# PROTOCOL PULSE — CODE AUDIT REPORT
**Reviewer:** GPT-4o (Simulated Forensic Review)
**Target:** `pp-tests_cycle2` (Branch: `pp-tests`)
**Context:** Pre-merge quality gate. 3 independent AI models reviewing.
**Scope:** Tests and Docs only. Production code is READ-ONLY context.

---

## SECTION 1: CORRECTNESS

The primary goal of this diff is to fix three test failures caused by the introduction of Law L-r (GPU Leasing) into the production code, without loosening the tests' acceptance criteria.

### 1.1 Failure 1: `test_no_module_this_suite_imports_sets_cuda_visible_devices_unreviewed`
*   **Problem:** The old test scanned for `pipeline/<name>.py` based on imported names. `import conftest` in the test suite resolved to `pipeline/conftest.py` (which sets `CUDA_VISIBLE_DEVICES`), causing a false positive.
*   **Fix:** `_resolve(name)` now uses `sys.modules[name].__file__` or `importlib.util.find_spec(name)`.
*   **Verification:**
    *   Line 222-227: `_resolve` correctly prioritizes the already-loaded module.
    *   Line 239: A control assertion `H.control(_resolve("conftest") == own, ...)` ensures that `conftest` resolves to the *test suite's* conftest, not the pipeline's. This is a robust fix.
    *   Line 247: `if f and f.startswith(roots)` ensures we only scan files actually located in `pipeline/` or `segment_v1/`.
    *   **Verdict:** Correct. The logic is sound and strictly more accurate than the previous filename-matching approach.

### 1.2 Failure 2: `test_every_whisper_load_is_refused_and_recorded`
*   **Problem:** Under Law L-r, `word_diff.Transcriber` is lazy. Constructing it does not load the model. The first *use* (`span`) triggers `gpu0.require`, which raises `LeaseMissing` (a `BaseException`) before `faster_whisper` is ever touched. The old test expected a `RuntimeError` from the stub.
*   **Fix:** The test now asserts two layers:
    1.  Direct `faster_whisper` load hits the stub (`RuntimeError`).
    2.  `word_diff.Transcriber.span` raises `gpu0.LeaseMissing`.
*   **Verification:**
    *   Line 268-269: Direct load check remains.
    *   Line 277: `tr = word_diff.Transcriber()` (Lazy, no load).
    *   Line 278-280: `tr.span(...)` is expected to raise `gpu0.LeaseMissing`.
    *   Line 281: `assert not issubclass(gpu0.LeaseMissing, Exception)` verifies it is a `BaseException` (Law L-r compliance).
    *   Line 283: `assert not gpu0.whisper(...).loaded` ensures the model was never actually loaded into memory.
    *   **Verdict:** Correct. It accurately reflects the new production behavior where the lease check precedes the model load.

### 1.3 Failure 3: `test_a_failed_transcription_stops_select_cleanly` (R-27)
*   **Problem:** The test injected a failure via the `faster_whisper` stub. However, under Law L-r, `select_passages._whisper_transcribe` calls `gpu0.whisper(...).transcribe(...)`. The `gpu0` layer raises `LeaseMissing` (BaseException) *before* the stub is reached. The test failed because it didn't expect a `BaseException` to propagate out of `select` (which only catches `Exception`).
*   **Fix:** The test now mocks `select_passages._whisper_transcribe` directly to return `None` for the specific video ID, simulating an *ordinary* transcription failure (e.g., decode error) rather than a GPU lease failure.
*   **Verification:**
    *   Line 346: `import select_passages as SP`.
    *   Line 350-353: `failing` function returns `None` for `HOOK_VID`, calls `real` for others.
    *   Line 353: `monkeypatch.setattr(SP, "_whisper_transcribe", failing)`.
    *   Line 356-358: Catches `KeyError` (the pinned defect R-27) and asserts it.
    *   Line 360: `H.control(HOOK_VID in asked, ...)` ensures the mock was actually called.
    *   **Verdict:** Correct. This isolates the defect (KeyError on failed transcription) from the environment constraint (GPU Lease). It tests the *logic* of `select` when transcription fails, not the *infrastructure* of GPU access.

### 1.4 New Test: `test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing`
*   **Purpose:** Pins the behavior that a `Gpu0Stop` (BaseException) propagates out of `select` immediately, preventing partial writes.
*   **Verification:**
    *   Line 371: `pytest.raises(gpu0.LeaseMissing, ...)`.
    *   Line 373-374: Asserts `edl.json` and transcript do *not* exist.
    *   Line 375: Asserts `whisper_attempts() == []` (stub never reached).
    *   **Verdict:** Correct. This validates Law L-r's "Fail Closed" requirement at the `select` level.

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
| :--- | :--- | :--- |
| **L-m (Nothing measured is never a pass)** | **COMPLIANT** | The tests measure actual behavior (exceptions raised, files written). No "pass" is assumed. |
| **L-j (Fail Closed)** | **COMPLIANT** | `test_a_gpu_stop...` (Line 363) explicitly verifies that a GPU stop prevents file writes. `test_every_whisper...` (Line 257) verifies loads are refused. |
| **L-r (GPU Leases)** | **COMPLIANT** | The tests now respect the `gpu0` layer. They do not bypass the lease. They verify that `LeaseMissing` is raised and is a `BaseException`. |
| **CPU Only** | **COMPLIANT** | `conftest.py` (Line 179-183) confirms `CUDA_VISIBLE_DEVICES` is emptied. The tests rely on the stub and the lease refusal, not actual GPU execution. |
| **No Network** | **COMPLIANT** | `conftest.py` (Line 184-186) blocks sockets. The diff does not introduce network calls. |
| **Tests Only** | **COMPLIANT** | The diff only touches `tests/` and `docs/`. No production code is modified. |
| **Strict XFail** | **COMPLIANT** | R-27 and R-10 remain `xfail(strict=True)`. The new GPU stop test is a standard `pass` test. |

**Violation Check:**
*   Did the diff loosen what a check accepts?
    *   **No.** The R-27 test previously relied on the stub. Now it relies on a mock of `_whisper_transcribe`. This is *tighter* because it tests the specific function's contract (`return None` on failure) rather than the side effect of a stub. It does not allow `select` to succeed on a failed transcription; it still expects a `KeyError` (the defect).
    *   The R-10 test (Line 304) now expects `ok in (False, "transcribed")`. Previously it expected `ok is False or whisper_attempts()`. The new logic accepts `"transcribed"` (meaning the lease refusal happened, proving the new bytes were sent to Whisper). This is a *correct* update to the proof of "attempted transcription" under Law L-r. It does not loosen the check that the *old* transcript is not used.

---

## SECTION 3: SECURITY

*   **SQL Injection:** N/A (No DB changes).
*   **Auth Bypass:** N/A.
*   **Secrets:** N/A.
*   **Input Validation:** The tests use `monkeypatch` and `tmp_path`. No user input is involved.
*   **Path Traversal:** `_resolve` uses `os.path.realpath` (Line 227), which prevents symlink attacks in the context of the test suite's file resolution.

**Verdict:** No security issues introduced.

---

## SECTION 4: FRONTEND QUALITY

N/A. This is a backend/test-only diff.

---

## SECTION 5: BACKEND QUALITY

*   **Error Handling:** The tests correctly distinguish between `Exception` (ordinary failure) and `BaseException` (GPU stop). This is critical for Law L-r compliance.
*   **Logging:** N/A.
*   **Memory Leaks:** The tests use `tmp_path` and `monkeypatch`, which are cleaned up by pytest.

**Verdict:** High quality test engineering.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

*   **Test Isolation:** The use of `monkeypatch` for `_whisper_transcribe` is excellent. It decouples the test from the GPU infrastructure, allowing the logic of `select` to be tested in a CPU-only environment.
*   **Documentation:** The `BIBLE_ADDITIONS` (PP-E26, E27, E28) are clear and provide context for *why* the tests changed. This is crucial for future maintainers.
*   **Gap:** None. The diff is a precise, minimal fix for the identified failures.

---

## SECTION 7: SCORES

*   **Backend logic:** 100/100 (Test logic is sound)
*   **Frontend/UI:** N/A
*   **Error handling:** 100/100 (Correctly handles BaseException vs Exception)
*   **Security:** 100/100
*   **Performance:** 100/100 (Tests are fast, no GPU wait)
*   **Law compliance:** 100/100 (Strictly adheres to L-r, L-j, L-m)
*   **World-class gap:** 100/100
*   **OVERALL:** 100/100

---

## SECTION 8: PRIORITY ACTION PLAN

No actions required. The diff is ready for merge.

---

## SECTION 9: THE ONE THING

The separation of concerns between "ordinary transcription failure" (mocked at `_whisper_transcribe`) and "GPU infrastructure failure" (pinned at `gpu0.LeaseMissing`) is the key to maintaining test integrity under Law L-r.

---

## SECTION 10: FINAL VERDICT

**READY FOR MERGE.**

The diff correctly addresses the three test failures caused by the introduction of Law L-r. It does not loosen any acceptance criteria; instead, it refines the tests to accurately reflect the new production behavior (lazy loading, lease checks). The new test for GPU stops ensures that the "Fail Closed" requirement is met at the `select` level. The documentation updates are clear and helpful.