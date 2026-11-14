<!-- qwen/qwen3.8-27b, 44 s, finish stop, $0.0028 (vendor usage.cost) -->

# PROTOCOL PULSE — CODE AUDIT REPORT
**Reviewer:** GPT-4o (Simulated Forensic Review)
**Target:** `pp-tests_batch78` (Pre-merge Quality Gate)
**Status:** **PASS** (with minor documentation/robustness notes)

This is a test-only diff. The "production" code is the test infrastructure itself. The review focuses on the correctness of the security guards, the compliance with the "House Laws" regarding secrets and network isolation, and the robustness of the new assertions.

---

## SECTION 1: CORRECTNESS

### 1.1 Key Loading (`frontier_blind.py`)
**Claim:** Keys are read by name via `relay.get_key`, loaded from the main tree's `relay.py` without modifying `sys.path` or writing bytecode.
**Analysis:**
- **Line 129-136:** The code uses `importlib.util.spec_from_file_location` to load `relay.py` from a hardcoded absolute path (`/home/ultron/protocol_pulse/video_pipeline_v3/relay.py`).
- **Thread Safety:** `_key` is called under `_TLOCK` (per docstring line 125). The lazy initialization `if not _GET_KEY:` is safe because the lock serializes access.
- **Bytecode:** `sys.dont_write_bytecode` is set to `True` before `exec_module` and restored in `finally`. This correctly prevents `__pycache__` creation in the main tree.
- **Shadowing Risk:** By loading via file path under a private name (`_pp_baseline_relay`), it avoids polluting `sys.modules` with a `relay` module that might shadow other imports. This is a superior approach to `sys.path.insert` for this specific constraint.
- **Verdict:** **Correct.** It strictly adheres to the "read by name" rule and avoids side effects on the global interpreter state.

### 1.2 Network Guard (`moments_exam.py`)
**Claim:** All forward and reverse lookups are blocked.
**Analysis:**
- **Line 250-251:** The loop now includes `gethostbyaddr` and `getnameinfo`.
- **Line 239-243:** The `no_resolve` factory creates distinct exception messages including the function name. This is crucial for the test assertions in `test_moments_gates.py`.
- **Coverage:** `socket.getaddrinfo`, `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr`, `getnameinfo` are all patched.
- **Verdict:** **Correct.** The previous gap (`gethostbyaddr`) is closed.

### 1.3 Child Guard (`sitecustomize.py`)
**Claim:** Child processes also block reverse lookups.
**Analysis:**
- **Line 170:** The tuple of names to patch now includes `getnameinfo`.
- **Line 156-161:** The docstring explicitly documents the limitation regarding `.pth` files binding socket functions before `sitecustomize` runs. It claims this was checked and is not an issue on the target interpreter.
- **Verdict:** **Correct.** The guard is symmetric with the parent guard.

### 1.4 Test Assertions (`test_moments_gates.py`)
**Claim:** The test proves the *Runner* refused the network, not the *Child Guard*.
**Analysis:**
- **Line 375:** `assert r["why"].startswith("NetworkRefused: moments_exam: network is disabled")`.
    - The Runner's exception is `NetworkRefused` (defined in `moments_exam.py` line 61).
    - The Child Guard's exception is `ChildNetworkBlocked` (implied by context, distinct from `NetworkRefused`).
    - By asserting the specific prefix `NetworkRefused: moments_exam:`, the test correctly isolates the Runner's behavior. If the Child Guard caught it first, the message would differ (or the exception type would be different if not caught).
- **Line 378-379:** For `network_reverse`, it asserts that *both* `gethostbyaddr` and `getnameinfo` appear in the refusal messages. This ensures the new patches are actually being hit.
- **Verdict:** **Correct.** This is a robust way to test layered guards.

### 1.5 Unscanned Modules Check (`test_f0_cpu_guard.py`)
**Claim:** Fails if a pipeline module exists on disk but isn't imported/scanned.
**Analysis:**
- **Line 315:** `unscanned = {n for n in names - set(found) if any(os.path.exists(os.path.join(r, n + ".py")) for r in roots)}`.
    - `names`: All imported module names.
    - `found`: Modules that resolved to a file in `pipeline/` or `segment_v1/`.
    - `unscanned`: Names that were imported, did *not* resolve to a file in those roots, BUT a file with that name *does* exist in those roots.
    - This catches cases where `sys.path` manipulation or shadowing causes the test to import a *different* `module.py` than the one in the repo, or where a module is missing from the scan list but present on disk.
- **Line 316:** `assert unscanned <= {"conftest"}`. Allows the suite's own `conftest` as an exception.
- **Verdict:** **Correct.** This is a strong integrity check for the test suite's visibility into the codebase.

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
| :--- | :--- | :--- |
| **L-m: Nothing measured is never a pass** | **COMPLIANT** | The tests measure specific behaviors (network refusal, key loading). They do not "pass" by default; they assert specific outcomes. |
| **L-j: Fail closed** | **COMPLIANT** | `relay.get_key` raises `KeyError` if missing. Network guards raise `BaseException` subclasses. The `unscanned` check fails if unexpected modules are found. |
| **Secrets: Read by NAME, never printed** | **COMPLIANT** | `frontier_blind.py` line 137 returns the key value, but the docstring (line 124) and usage context imply it's passed to the client, not printed. The diff removes the old `ENV_FILE` parsing which was a violation. No `print(key)` found. |
| **CPU only, no network** | **COMPLIANT** | The tests explicitly block network calls. `CUDA_VISIBLE_DEVICES` is hidden. |
| **No editing production code** | **COMPLIANT** | The diff only touches `tests/` and `docs/`. `relay.py` is read-only context. |
| **Pinned defects are xfail** | **COMPLIANT** | The diff mentions `XFAIL_EVIDENCE` regeneration. The new tests are standard `assert` based, not `xfail`, which is correct for *new* fixes. |

**Verdict:** Fully compliant with the governing laws.

---

## SECTION 3: SECURITY

1.  **Secrets Exposure:**
    *   **Risk:** `frontier_blind.py` loads `relay.py` from an absolute path.
    *   **Mitigation:** The path is hardcoded to the main tree. The key is read into memory. It is not logged. The `sys.dont_write_bytecode` flag prevents leaking the source of `relay.py` into `__pycache__` in the main tree (which might be world-readable or version-controlled).
    *   **Assessment:** **Secure.**

2.  **Network Isolation:**
    *   **Risk:** A test might accidentally make a network call.
    *   **Mitigation:** Layered guards (Parent `conftest`, Runner `moments_exam`, Child `sitecustomize`). All patch `socket` functions.
    *   **Assessment:** **Robust.** The addition of `getnameinfo` closes a significant gap.

3.  **Path Traversal:**
    *   **Risk:** `importlib` loading from a hardcoded path.
    *   **Mitigation:** The path is static. No user input influences it.
    *   **Assessment:** **Safe.**

4.  **Race Conditions:**
    *   **Risk:** Concurrent access to `_GET_KEY` in `frontier_blind.py`.
    *   **Mitigation:** `_TLOCK` is used.
    *   **Assessment:** **Safe.**

---

## SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend/test infrastructure diff. No UI changes.

---

## SECTION 5: BACKEND QUALITY

1.  **Error Handling:**
    *   `relay.get_key` raises `KeyError` with a helpful message.
    *   Network guards raise `BaseException` subclasses to prevent `except Exception` from swallowing them. This is a high-quality pattern for security guards.
    *   `test_f0` uses `H.control` for preconditions, ensuring clear failure messages.

2.  **Logging:**
    *   The code does not log sensitive data.
    *   Error messages in tests are descriptive (e.g., listing unscanned modules).

3.  **Performance:**
    *   Lazy loading of `relay.py` ensures no overhead if keys aren't needed.
    *   The `unscanned` check iterates over imported names and checks file existence. This is O(N) where N is the number of imports. Acceptable for a test suite.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Hardcoded Absolute Path:**
    *   `KEY_LOADER = "/home/ultron/protocol_pulse/video_pipeline_v3/relay.py"` (Line 92).
    *   **Gap:** This is brittle. If the repo is moved, or run in a container with a different mount point, this breaks.
    *   **Recommendation:** Derive the path relative to the test file or use an environment variable with a fallback. However, given the "House Law" context (specific server setup), this might be acceptable. Still, a relative path calculation would be more robust.

2.  **Documentation of `.pth` Limitation:**
    *   The `sitecustomize.py` docstring mentions the `.pth` limitation but relies on a manual check ("Checked 2026-11-14").
    *   **Gap:** There is no automated test to verify that no `.pth` file in the environment binds socket functions.
    *   **Recommendation:** Add a test in `test_f0` that scans `site.getsitepackages()` for `.pth` files and verifies they don't import `socket` functions directly.

3.  **Test Isolation:**
    *   The `network_reverse` toy gate uses a global `_calls` list.
    *   **Gap:** If tests run in parallel or in a specific order, this state could leak.
    *   **Recommendation:** Ensure the toy gate is instantiated fresh per test or reset state. The diff says "no THREAD_SAFE: the runner calls it one case at a time," which mitigates this, but it's a fragile assumption.

---

## SECTION 7: SCORES

*   **Backend logic:** 95/100 (Robust, minor path brittleness)
*   **Frontend/UI:** N/A
*   **Error handling:** 98/100 (Excellent use of BaseException for guards)
*   **Security:** 95/100 (Strong isolation, hardcoded path is a minor risk)
*   **Performance:** 90/100 (Lazy loading, efficient checks)
*   **Law compliance:** 100/100 (Strictly follows all rules)
*   **World-class gap:** 85/100 (Could be more portable/automated in checks)
*   **OVERALL:** **94/100**

---

## SECTION 8: PRIORITY ACTION PLAN

| Priority | Action | File:Line | Reason |
| :--- | :--- | :--- | :--- |
| **P2** | Replace hardcoded `KEY_LOADER` path with relative derivation or env var | `frontier_blind.py:92` | Improves portability and reduces brittleness if the repo structure changes. |
| **P3** | Add automated check for `.pth` socket bindings | `test_f0_cpu_guard.py` | Validates the assumption in `sitecustomize.py` docstring, preventing future silent failures. |
| **P3** | Reset `_calls` state in `network_reverse` toy gate | `network_reverse.py:267` | Ensures test isolation if the runner behavior changes or tests are reordered. |

---

## SECTION 9: THE ONE THING

**Replace the hardcoded absolute path for `relay.py` with a path derived from the test file's location or an environment variable, to ensure the test suite remains portable and resilient to changes in the deployment directory structure.**

---

## SECTION 10: FINAL VERDICT

This code is **ready for merge**. It successfully addresses the two consensus findings from the previous audit cycle (hardcoded key file parsing and missing reverse DNS lookup guards) with high-quality, fail-closed implementations. The new tests are robust, correctly isolate the runner's behavior from the child guard's, and include valuable integrity checks for the test suite itself. The only minor improvement would be to make the key loader path less brittle, but this does not block the merge.