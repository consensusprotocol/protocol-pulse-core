<!-- qwen/qwen3.8-27b, 61 s, finish stop, $0.0038 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-tests_batch78
# Reviewer: GPT-4o (Simulated Forensic Review)
# Status: **PASS** (with minor robustness notes)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the *correctness* of the network guard logic and the key loading mechanism. I missed two subtle but important points raised by the other models:

1.  **The "Proof Outside the Diff" Issue (GLM):** GLM correctly noted that the test assertion `r["why"].startswith("NetworkRefused: moments_exam: ...")` relies on the runner's error formatting logic (`moments_exam._judge`), which is **not** in the diff. I assumed the formatting was stable or obvious, but GLM rightly pointed out that if the runner changed how it formats exceptions (e.g., using `repr(e)` vs `f"{type(e).__name__}: {e}"`), this test would break silently or fail unexpectedly. This is a valid fragility, even if the current code works.
2.  **The "Corpus Size" Fragility (GLM):** GLM noted that the `network_reverse` test asserts that *both* `gethostbyaddr` and `getnameinfo` appear in the failure rows. This requires the "exclusions" corpus to have at least 2 cases (since the toy gate alternates between the two calls). If the corpus had only 1 case, the test would fail. I missed this dependency on external data (the corpus size) in my Cycle 1 review.
3.  **The "Unscanned Modules" Logic (Qwen/GLM):** Both Qwen and GLM provided a deeper analysis of the `test_f0_cpu_guard.py` change. I noted it was a "strong integrity check," but they correctly identified the specific logic: it catches modules that exist on disk in `pipeline/` or `segment_v1/` but are *not* resolved by the test's import mechanism (e.g., due to `sys.path` shadowing). This is a more precise description of *why* it's valuable.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemini (P2: Consolidate Network Guard Logic):** **AGREE.** The introduction of `netguard_names.py` is a significant improvement. It eliminates the risk of drift between the three guards (conftest, child_guard, moments_exam). This was the root cause of the original bug (missing `gethostbyaddr` in one guard but not others).
*   **Qwen (P2: Derive KEY_LOADER Relatively):** **DISAGREE (Refuted).** As noted in the consensus, `relay.py` finds the key file *beside itself*. The worktree copy of `relay.py` does not have the key file next to it; only the main tree's copy does. Therefore, hard-coding the absolute path to the main tree's `relay.py` is the *only* correct way to ensure the key file is found. Using a relative path or environment variable would either point to the wrong `relay.py` (worktree) or introduce a security risk (arbitrary file execution). The current approach is correct.
*   **GLM (P1: Automate PP-E31 Detection):** **AGREE.** The new test `test_keys_are_read_only_by_name_through_the_pipelines_loader` is a crucial addition. It ensures that no test file hard-codes a key file path, enforcing the "keys by name" law. This was a gap in the previous audit.
*   **GLM (P3: Thread Safety of `_GET_KEY`):** **PARTIALLY AGREE.** The use of a list `_GET_KEY` as a cache is slightly awkward, but the docstring explicitly states it is called under `_TLOCK`. Since the lock serializes access, the race condition is benign (worst case: double load, one discarded). This is acceptable for a test utility.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`netguard_names.py` Import Path in `conftest.py`:**
    In `conftest.py` (line 227), the code loads `netguard_names.py` using `os.path.join(CHILD_GUARD, "netguard_names.py")`. `CHILD_GUARD` is defined earlier in `conftest.py` (not shown in diff, but implied). This is correct. However, in `moments_exam.py` (line 277), it uses `os.path.join(HERE, "child_guard", "netguard_names.py")`. This is also correct. The consistency is good.

2.  **`test_the_runner_refuses_every_call_of_the_suites_list` Probe Complexity:**
    The new test in `test_moments_gates.py` (line 496) runs a complex Python probe in a child process. The probe imports `moments_exam.py` by file path, calls `refuse_network()`, and then checks the `__name__` of the patched socket functions. This is a robust way to test the runner's guard in isolation. However, it relies on `moments_exam.py` being importable without side effects (other than the network refusal). Since `moments_exam.py` is a script, importing it might execute top-level code. The diff shows `moments_exam.py` has top-level imports and function definitions, but no top-level execution (like `if __name__ == "__main__":`). So this should be safe.

3.  **`network_reverse.py` Toy Gate Alternation:**
    The toy gate `network_reverse.py` uses `_calls[0] % 2` to alternate between `gethostbyaddr` and `getnameinfo`. This is a clever way to ensure both are tested. However, it relies on the runner calling the gate function exactly once per case. If the runner were to call it multiple times per case (e.g., for retries), the alternation would break. The docstring says "no THREAD_SAFE: the runner calls it one case at a time," which mitigates this.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Network Guard** | 9/10 | 10/10 | The consolidation into `netguard_names.py` eliminates the drift risk. The new tests are comprehensive. |
| **Key Loading** | 9/10 | 10/10 | The refactoring to use `relay.get_key` is correct and secure. The new test enforces the law. |
| **Test Specificity** | 8/10 | 9/10 | The new assertions are precise. The only remaining fragility is the dependency on the corpus size for the `network_reverse` test, which is acceptable (fail-closed). |
| **Documentation** | 9/10 | 10/10 | The docstrings are excellent, explaining the "why" and the constraints. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    1.  **`test_moments_gates.py:492`**: The assertion that both `gethostbyaddr` and `getnameinfo` appear in the rows depends on the "exclusions" corpus having at least 2 cases. If the corpus is trimmed to 1 case, this test will fail. This is a visible failure, not a silent pass, so it is acceptable, but it is a fragile coupling. **Recommendation:** Add a comment in the test or the corpus file noting this dependency.
    2.  **`moments_exam.py:277`**: The path to `netguard_names.py` is constructed using `os.path.join(HERE, "child_guard", "netguard_names.py")`. If the directory structure changes, this will break. This is a minor risk, as the structure is stable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `netguard_names.py` as a single source of truth for the network guard's list of refused calls is the highest-leverage change. It eliminates the class of bugs where one guard is updated but others are not, which was the root cause of the original defect.

## 7. PRODUCTION READY?

**Yes.**

The code is correct, compliant with all laws, and well-tested. The minor fragilities (corpus size dependency, path construction) are acceptable and do not pose a risk of silent failure. The new tests are robust and provide strong evidence that the fixes are working as intended.