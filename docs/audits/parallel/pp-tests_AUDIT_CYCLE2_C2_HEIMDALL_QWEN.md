<!-- qwen/qwen3.8-27b, 38 s, finish stop, $0.0024 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
**Reviewer:** Claude (Simulated Forensic Review)
**Target:** `pp-tests_cycle2`
**Context:** Final review. Cycle 1 consensus established.

---

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the *logic* of the new tests and the *compliance* with the laws. We largely missed the **operational fragility** introduced by the new test `test_every_whisper_load_is_refused_and_recorded`.

Specifically, **Heimdall_GLM** and **Heimdall_Qwen** implicitly validated the logic, but none of us explicitly flagged the **external dependency** introduced at `test_f0_cpu_guard.py:276-277`. The test now executes `subprocess.run(["ffmpeg", ...])` to generate a WAV file.
*   **Missed Risk:** The test suite is supposed to be "CPU only, no network." While `ffmpeg` is local, it is an **external binary dependency**. If `ffmpeg` is not installed in the CI environment, or if the `lavfi` sine source fails for any reason (permissions, missing libs), the test will fail with a `subprocess.CalledProcessError` or `FileNotFoundError`, not a test assertion error. This violates the "self-contained" spirit of the adversarial suite.
*   **Missed Nuance:** The `_resolve` function in `test_f0_cpu_guard.py:217-227` relies on `sys.modules` and `importlib.util.find_spec`. While correct, it assumes that the test suite's `conftest.py` is the *only* `conftest` module in `sys.modules` under that name. If pytest's internal machinery or a plugin registers a different `conftest` module object, the control assertion at line 240 could fail spuriously. This is a low-probability but high-impact edge case that was not stress-tested in Cycle 1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

### Agreement
*   **Gemini:** I agree with Gemini's assessment that the `_resolve` function is a "significant improvement in correctness." The shift from filename matching to interpreter resolution is the right architectural fix for PP-E26.
*   **Heimdall_Qwen:** I agree with Qwen's analysis of the R-27 pin. Mocking `_whisper_transcribe` to return `None` is the correct way to isolate the *logic* defect (KeyError) from the *infrastructure* constraint (GPU Lease).
*   **Heimdall_GLM:** I agree with GLM's detailed trace of the `LeaseMissing` exception path. The confirmation that `Model.__getattr__` re-enters `get()` on every access is crucial for understanding why the lazy load fails at `.span()` rather than `__init__`.

### Disagreement / Refinement
*   **On the "No Finding" Consensus:** The Cycle 1 consensus (driven by Gemini and Qwen) was "100/100, no finding." I **disagree** with the "no finding" status. The introduction of `ffmpeg` into `test_f0` is a **P1 finding** regarding test robustness and environment assumptions. It is not a logic error, but it is a fragility that will cause false failures in minimal CI environments.
*   **On the `_tree` Snapshot:** The new `_tree` function in `test_f2_provenance.py:304-313` is excellent for the "writes nothing" assertion. However, I note that `os.walk` order is not guaranteed to be stable across all filesystems, but since we are comparing dictionaries, order doesn't matter. I agree this is correct.

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding 1: External Binary Dependency in `test_f0` (P1)**
*   **File:** `tests/adversarial/test_f0_cpu_guard.py`
*   **Lines:** 276-277
*   **Issue:** The test `test_every_whisper_load_is_refused_and_recorded` now requires `ffmpeg` to be present and functional to generate a 1-second sine wave WAV file.
*   **Impact:** If `ffmpeg` is missing, the test fails with `subprocess.CalledProcessError` or `FileNotFoundError`. This is an environment failure, not a code defect. The adversarial suite should ideally be self-contained or use pure-Python audio generation (e.g., `wave` module + `struct`) to avoid this dependency.
*   **Recommendation:** Replace `subprocess.run(["ffmpeg", ...])` with a pure-Python WAV writer. A 1-second 16kHz sine wave is trivial to generate with `math.sin` and `wave`/`struct`. This removes the external dependency and makes the test more robust.

**Finding 2: `sys.modules` Pollution Risk in `_resolve` (P2)**
*   **File:** `tests/adversarial/test_f0_cpu_guard.py`
*   **Lines:** 223-224
*   **Issue:** `_resolve` checks `sys.modules.get(name)`. If a previous test or plugin imported a module named `conftest` from a different path, `sys.modules["conftest"]` might point to the wrong file. The control assertion at line 240 mitigates this by checking the path, but it fails the test rather than falling back to `find_spec`.
*   **Impact:** Low. Pytest usually manages `conftest` modules carefully, but in complex plugin environments, this could be a source of flaky failures.
*   **Recommendation:** Acceptable as-is due to the control assertion, but worth noting.

**Finding 3: Documentation Clarity on `whisper_attempts` (P2)**
*   **File:** `tests/adversarial/conftest.py`
*   **Lines:** 192-193
*   **Issue:** The docstring for `whisper_attempts` was updated to clarify that pipeline loads stop at the GPU0 lease and are *not* listed here. This is good. However, the test `test_every_whisper_load_is_refused_and_recorded` asserts `len(whisper_attempts()) == 1` after the `LeaseMissing` exception. This is correct because the `LeaseMissing` happens *before* the `faster_whisper` stub is reached. The documentation and code are consistent. No change needed, but this confirms the logic is sound.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 10/10 | 9/10 | Deducted 1 point for the `ffmpeg` dependency in `test_f0`. The logic is correct, but the test is fragile due to external binary reliance. |
| **Law Compliance** | 10/10 | 10/10 | No changes. The tests still adhere to L-m, L-j, and the "CPU only" law (ffmpeg is CPU, but the dependency is a robustness issue, not a law violation). |
| **Security** | N/A | N/A | No changes. |
| **Robustness** | 8/10 | 7/10 | The `ffmpeg` call is a new point of failure. The `_resolve` function is robust, but the audio generation is not. |
| **Overall** | 9.5/10 | 9.0/10 | The code is logically sound and legally compliant, but the introduction of an external binary dependency in a core guard test is a significant robustness regression. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None. The code does not break production or violate core laws.

**P1 HIGH**
1.  **Remove `ffmpeg` dependency from `test_f0_cpu_guard.py:276-277`.**
    *   **Action:** Replace the `subprocess.run(["ffmpeg", ...])` call with a pure-Python WAV file generator.
    *   **Reason:** The adversarial test suite must be self-contained. Relying on `ffmpeg` introduces an environment-specific failure mode that is unrelated to the code under test.
    *   **Implementation:** Use `wave` and `struct` to write a 1-second 16kHz 16-bit PCM sine wave.

**P2 MEDIUM**
1.  **Add a comment in `_resolve` (`test_f0_cpu_guard.py:217`) about `sys.modules` pollution.**
    *   **Action:** Note that the control assertion at line 240 is the primary defense against `sys.modules` containing a stale `conftest` entry.
    *   **Reason:** Documentation for future maintainers.

2.  **Verify `ffmpeg` availability in CI.**
    *   **Action:** If the P1 fix is not implemented immediately, ensure `ffmpeg` is installed in all CI environments running this suite.
    *   **Reason:** Mitigation if the code change is delayed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Replace the `ffmpeg` subprocess call in `test_f0_cpu_guard.py` with a pure-Python WAV generator to eliminate the external binary dependency and ensure the test suite is fully self-contained and robust across all environments.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** The `ffmpeg` dependency in `test_f0_cpu_guard.py:276-277` must be removed and replaced with a pure-Python audio generation method. Until this is done, the test suite is at risk of false failures in minimal CI environments where `ffmpeg` is not installed.

**Rationale:** The logic of the tests is correct, the law compliance is solid, and the documentation is clear. The only issue is a robustness flaw in the test infrastructure itself. Once the `ffmpeg` call is replaced, this code is ready for production merge.