<!-- qwen/qwen3.8-27b, 33 s, finish stop, $0.0021 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
**Feature:** `pp-tests_b78c3`
**Reviewer:** Claude (Cycle 2)
**Context:** Reviewing the updated diff which includes the mutation evidence file (`pp-tests_AUDIT_B78C3_MUTATIONS.md`) and the refined test logic in `test_f0_cpu_guard.py`.

---

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the *logic* of the patching mechanism. The other models, specifically **GLM** and **QWEN**, raised critical points regarding *verifiability* and *boundary conditions* that I under-weighted:

1.  **The "Missing Evidence" Gap (GLM P1):** GLM correctly identified that in Cycle 1, the claim that "mutations M6-M8 now fail" was not verifiable from the diff alone because the mutation code and results were in the session scratchpad. The Cycle 2 diff *fixes* this by including `pp-tests_AUDIT_B78C3_MUTATIONS.md`. I missed the procedural requirement that audit evidence must be self-contained in the diff for reproducibility.
2.  **The `io.open_code` Boundary (QWEN/GLM):** Both models explicitly traced the CPython import machinery to confirm that patching `io.open` (Python level) does *not* break `io.open_code` (C level `_io.open`). While I noted the `try/finally` safety, I did not explicitly verify the *feasibility* of the patching strategy against the import system. Their confirmation that the stub *can* load despite the patch is a crucial correctness check.
3.  **Thread Safety Warning (QWEN P3):** QWEN noted that the patches are process-global and not thread-safe. The Cycle 2 diff adds a comment acknowledging this ("process-wide patches... not thread-safe"). I missed the need to explicitly document this limitation in the code.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Stance | Reasoning |
| :--- | :--- | :--- | :--- |
| **Mutation Evidence Included** | GLM (P1) | **AGREE** | The new file `pp-tests_AUDIT_B78C3_MUTATIONS.md` provides the exact `_key` implementations and verbatim test results. This resolves the "cannot verify from diff" objection. The evidence shows M6-M8 (side reads) now FAIL, while M0 (real) PASSES. |
| **`io.open_code` Safety** | QWEN/GLM | **AGREE** | The test patches `io.open` but relies on `importlib` using `_io.open_code`. The mutation results confirm the stub loads successfully (M0 passes), proving the boundary is correct. |
| **Denial Record Format** | Gemini/GLM (P3) | **AGREE** | The format was changed from `f"{what}{a[:1]!r}"` (which produced ugly trailing commas) to `f"{what}({a[0]!r})"`. This is cleaner and more readable in failure messages. |
| **`os.popen` Coverage** | GLM | **AGREE** | GLM noted `os.popen` is in the list *and* covered by `subprocess.Popen`. This is redundant but safe. The list `_OS_PROCESS_STARTERS` is comprehensive. |
| **Thread Safety** | QWEN (P3) | **AGREE** | The added comment is accurate. The test is single-threaded by design (pytest default), so this is a documentation improvement, not a bug fix. |
| **`sys.addaudithook` Suggestion** | QWEN (P2) | **DISAGREE (as a blocker)** | QWEN suggested using `sys.addaudithook` to catch C-level calls. The integrator correctly rejected this for this cycle ("Nothing else changes"). The current scope is to close the *subprocess* gap. `addaudithook` is a valid *future* enhancement but out of scope for this specific fix. |

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **Mutation M8 (`os.posix_spawn`) Verification:**
    *   The mutation file shows M8 uses `os.posix_spawn("/bin/cat", ...)`.
    *   The test patches `os.posix_spawn` (line 246 in diff: `"posix_spawn"` is in `_OS_PROCESS_STARTERS`).
    *   The result shows M8 FAILS with `os.posix_spawn('/bin/cat')`.
    *   **Verdict:** Correct. The patching list covers the specific vector used in the mutation.

2.  **Mutation M7 (`os.system`) Verification:**
    *   M7 uses `os.system(f"cat {KEY_LOADER} > /dev/null")`.
    *   The test patches `os.system` (line 246: `"system"` is in `_OS_PROCESS_STARTERS`).
    *   The result shows M7 FAILS with `os.system('cat <tmp>/relay_stub.py > /dev/null')`.
    *   **Verdict:** Correct.

3.  **Mutation M6 (`subprocess.run`) Verification:**
    *   M6 uses `_sp.run([...])`.
    *   The test patches `subprocess.Popen` (line 276: `(subprocess, "Popen")`).
    *   Since `subprocess.run` instantiates `Popen`, it is caught.
    *   The result shows M6 FAILS with `subprocess.Popen(['/usr/bin/python3', ...])`.
    *   **Verdict:** Correct.

4.  **Restoration Logic Robustness:**
    *   The `finally` block (lines 306-311) iterates over `real` (list of `(module, name, original_value)`).
    *   It uses `setattr(m, n, v)`.
    *   This is robust against exceptions in the test body.
    *   **Verdict:** Correct.

5.  **Secret Leakage Check:**
    *   The assertion message (line 313) prints `denied`.
    *   `denied` contains strings like `subprocess.Popen(['/usr/bin/python3', '-c', 'import sys; open(sys.argv[1]).read()', '<tmp>/relay_stub.py'])`.
    *   This reveals the *command* and the *path* to the stub, but **not** the key value.
    *   The key value is only accessed via `fb._key(name)`, which returns the stub's sentinel.
    *   **Verdict:** Compliant with "Secrets are read only by NAME and never printed".

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | **10/10** | The inclusion of mutation evidence resolves the "unverifiable" concern. The logic is sound, and the edge cases (import machinery, thread safety) are documented. |
| **Law Compliance** | 9/10 | **10/10** | All laws are met. The "fail closed" and "nothing measured is never a pass" laws are explicitly demonstrated by the mutation results. |
| **Security** | 8/10 | **9/10** | The test now prevents a significant exfiltration vector (subprocess side-reads). The remaining gap (C-level `ctypes`/`_io.open`) is documented as a known limitation, which is acceptable for this scope. |
| **Code Quality** | 8/10 | **9/10** | The denial record format is cleaner. The comments are more precise. The code is well-structured. |

**Overall Score: 9.5/10** (Up from 8.5/10)

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The code is correct and safe.

**P1 HIGH:** None. The mutation evidence is present and verifiable.

**P2 MEDIUM:**
1.  **Documentation of `io.FileIO` Gap:** The test docstring (lines 321-327) mentions `io.FileIO` is not denied. It would be slightly clearer to explicitly state *why* (it's a C-level wrapper that doesn't go through `io.open` or `subprocess`). However, the current text is sufficient for an expert reader.
2.  **`sys.addaudithook` Follow-up:** The integrator should create a ticket for a future cycle to implement `sys.addaudithook` to catch `open` and `exec` events at the C level, closing the remaining gap. This is not a blocker for this merge.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The inclusion of `pp-tests_AUDIT_B78C3_MUTATIONS.md` in the diff.** This transforms the audit from a "trust me" exercise into a verifiable proof that the new test actually catches the specific vulnerabilities (M6-M8) that the old test missed.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The mutation evidence file must be committed alongside the test changes (it is in the diff).
2.  The test must pass in the CI environment (Linux/Ubuntu 24.04, Python 3.12). The mutation results confirm it passes on the local environment.
3.  No other changes to `frontier_blind.py` or `relay.py` are required for this test to function.

**Recommendation:** Merge.