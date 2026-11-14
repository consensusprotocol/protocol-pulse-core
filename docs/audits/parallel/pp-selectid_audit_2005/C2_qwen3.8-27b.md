# qwen3.8-27b (qwen/qwen3.8-27b) 44 s finish=stop usage in 13491 / out 2976 usd~0.085 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2005
# Reviewer: [Your Model]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the logic of the `while` loop and the `skip` set mechanics. I missed or under-weighted the following points raised by the other models, which are now confirmed by the fixed diff:

1.  **GLM-5.3-FLASH (P1-1):** The concern that `avoid_model` might not match `ra.backend` exactly. The Cycle 1 consensus noted this was verified against the real Router, but GLM correctly flagged that the *test* used fake IDs (`heimdall:glm`) that differed from production IDs (`heimdall:z-ai/glm-5.3-flash`). The fixed diff (lines 274-279) now uses `Fake("heimdall:glm", ...)` in the test, but the production JSON (line 66) defines `heimdall:z-ai/glm-5.3-flash`. **Wait**, looking closely at the test in the diff (line 276): `glm = Fake("heimdall:glm", ...)`. The test chain is `["xai:grok", "heimdall:deepseek", "heimdall:glm", "heimdall:qwen"]`. The production chain in `model_providers.json` (lines 82-88) is `["xai:grok-4.20-0309-reasoning", "anthropic:claude-opus-5-5", "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b", "local:gemma3:27b"]`.
    *   *Correction:* The test uses a *mock* router (`mk_router`) with a *mock* chain. The test verifies the *logic* of `step_a` (skip set, failover behavior) independent of the specific string keys, provided the mock router honors `avoid_model`. The consensus stated: "The failover test runs the REAL Router... with fake back-ends". If the test uses `mk_router` from `test_providers`, it is likely a mock. The critical verification is that `ra.backend` returned by the router matches the key used in `avoid_model`. Since `step_a` adds `ra.backend` to `skip` and passes `skip` as `avoid_model`, and the router is expected to filter based on `avoid_model`, the logic is self-consistent *if* the router's `call` method correctly filters the chain based on the `avoid_model` set. The diff does not show the router implementation, but the consensus confirms it was checked.

2.  **GROK-4.20 (P2):** The observation that the defensive `raise` on line 50-52 (in the fixed diff) now correctly raises `ProviderError` instead of the original `ValueError`. This was a P1/P0 concern in Cycle 1 (Qwen #2). The fixed diff explicitly implements this: `raise P.ProviderError(...) from e`. This is a **fix** from Cycle 1.

3.  **QWEN3.8 (P1 #3/#4):** The confirmation that `failover` is correctly derived from `deadline_s is not None` in `prescreen`. The fixed diff (line 123) shows `failover=deadline_s is not None`. This is correct and matches the ruling.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM-5.3-FLASH (P1-1):** The keying of `avoid_model` is critical. The code relies on `ra.backend` being the exact string the router uses to identify the model. The test uses a mock, so it doesn't prove the production router's behavior, but the consensus states the real router was checked. I agree this is a high-risk area if the router normalizes keys, but the consensus mitigates this.
*   **Agree with GROK-4.20 (P2):** The change to raise `ProviderError` in the defensive branch is correct and necessary for contract compliance.
*   **Agree with QWEN3.8 (P1 #3/#4):** The coupling of `failover` to `deadline_s` is implicit but correct for the current scope. The first verdict path passes `deadline_s=None`, so `failover=False`. The second screen passes `deadline_s=120.0`, so `failover=True`. This is verified in the test `test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain` (line 283-288).
*   **Disagree with GLM-5.3-FLASH (P1-3):** GLM argued the "all three failing" test doesn't prove the loop terminates via `skip`. However, the test at line 290-291 asserts `ProviderError` is raised when `qw.answer = "still not JSON"`. In this scenario:
    1.  xAI is avoided (writer vendor).
    2.  Deepseek fails (503) -> Router moves to GLM.
    3.  GLM answers "not one JSON object" -> `ValueError` -> `skip.add("heimdall:glm")`.
    4.  Router called with `avoid_model={"heimdall:glm"}`. Router skips GLM, moves to Qwen.
    5.  Qwen answers "still not JSON" -> `ValueError` -> `skip.add("heimdall:qwen")`.
    6.  Router called with `avoid_model={"heimdall:glm", "heimdall:qwen"}`. Router skips both. Chain is spent (only xAI, deepseek, glm, qwen in mock chain; xAI avoided by vendor, deepseek failed by router, glm/qwen in skip). Router raises `ProviderError`.
    *   The loop *does* terminate via the router raising `ProviderError`. The `if ra.backend in skip` branch is a defensive guard against a router bug (returning a skipped model). The test verifies the *happy path* of termination (router raises). It does *not* verify the defensive branch. This is acceptable because the defensive branch is unreachable in correct router operation.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: Test uses Mock Router, not Real Router, for Failover Logic**
*   **File:** `tests/package/test_medley.py` (lines 263-291)
*   **Scenario:** The test `test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain` uses `mk_router` from `test_providers`. This is a mock router. The consensus states the *real* router was checked in Cycle 1, but the diff provided *only* shows the mock test. If the real router's `avoid_model` handling differs from the mock (e.g., if it doesn't strictly filter the chain but instead retries or logs differently), the test passes but production fails.
*   **Impact:** High. The core failover logic depends on the router correctly honoring `avoid_model` to advance the chain.
*   **Mitigation:** The consensus explicitly states: "The failover test runs the REAL Router... with fake back-ends". I must trust this statement as I cannot see the real router code in the diff. However, I flag this as a dependency on external verification.

**P2-NEW-1: `import providers as P` inside Exception Handler**
*   **File:** `pipeline/context_integrity.py` (line 51)
*   **Scenario:** `import providers as P` is executed inside the `except` block. This is a local import. While Python caches imports, this is a style violation and could mask import errors if `providers` is not available at runtime (unlikely, but possible in edge cases).
*   **Impact:** Low.
*   **Recommendation:** Move `import providers as P` to the top of the file.

**P2-NEW-2: `SECOND_VERDICT_BATCH` is Hardcoded in `second_screen` but Passed in `build`**
*   **File:** `pipeline/package.py` (lines 133-134, 148-149)
*   **Scenario:** `second_screen` uses `SECOND_VERDICT_BATCH` to chunk jobs. `build` passes `batch=SECOND_VERDICT_BATCH` to `prescreen`. This is consistent. However, `prescreen` also accepts a `batch` parameter. If a future caller passes a different `batch` to `prescreen` for the second screen, it would override the chunking in `second_screen`? No, `second_screen` calls `prescreen` with `batch=SECOND_VERDICT_BATCH`. The chunking in `second_screen` (line 133) determines the *jobs*. The `batch` passed to `prescreen` determines the *chunks* within each job? No, `prescreen` takes `ms` (moments) and chunks them by `batch`. `second_screen` already chunks `g` by `SECOND_VERDICT_BATCH` into `jobs`. Then it calls `prescreen` with `chunk` (which is already size 2) and `batch=SECOND_VERDICT_BATCH` (2). So `prescreen` will chunk the size-2 list into one chunk of size 2. This is redundant but correct.
*   **Impact:** Low. Code clarity issue.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Failover Logic** | P1 | P2 | The defensive `raise` now correctly raises `ProviderError` (Grok's P2 fix). The loop termination is verified by the router raising `ProviderError` when the chain is spent. The `skip` set logic is sound. |
| **Router Integration** | P1 | P1 | Still depends on the real router honoring `avoid_model`. The test uses a mock. The consensus claims the real router was checked, but I cannot verify this from the diff. |
| **First Verdict Path** | P2 | P2 | Unchanged. `deadline_s=None` -> `failover=False`. Verified in tests. |
| **Caching** | P2 | P2 | Unchanged. Failed calls are not cached. Verified in consensus. |
| **Batch/Deadline Wiring** | P2 | P2 | Correctly wired in `second_screen` and `build`. Verified in tests. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
*   **P1-1: Router `avoid_model` Contract Verification (External Dependency)**
    *   **File:** `pipeline/context_integrity.py` (lines 36-38, 50-53)
    *   **Scenario:** The failover loop relies on `router.call` honoring `avoid_model` to skip previously failed models. The test uses a mock router. If the production router does not strictly filter the chain based on `avoid_model` (e.g., if it retries the same model or ignores the set), the loop may not terminate or may waste calls.
    *   **Action:** Confirm that the production `providers.Router.call` implementation strictly filters the chain based on `avoid_model` and raises `ProviderError` when the chain is exhausted. The consensus states this was checked, but it is a critical external dependency.

**P2 MEDIUM**
*   **P2-1: Local Import in Exception Handler**
    *   **File:** `pipeline/context_integrity.py` (line 51)
    *   **Scenario:** `import providers as P` is inside the `except` block.
    *   **Action:** Move to top of file for style and clarity.
*   **P2-2: Redundant Batch Chunking**
    *   **File:** `pipeline/package.py` (lines 133-140)
    *   **Scenario:** `second_screen` chunks jobs by `SECOND_VERDICT_BATCH`, then passes `batch=SECOND_VERDICT_BATCH` to `prescreen`, which chunks again.
    *   **Action:** Consider passing `batch=len(chunk)` or removing the chunking in `second_screen` and letting `prescreen` handle it. Low priority.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify that the production `providers.Router.call` strictly honors the `avoid_model` set to ensure the failover loop terminates correctly and does not retry skipped models.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Router Contract:** Confirm that the production `providers.Router.call` implementation strictly filters the chain based on `avoid_model` and raises `ProviderError` when the chain is exhausted. The test uses a mock router, so this is a critical external dependency.
2.  **Style Fix:** Move `import providers as P` to the top of `pipeline/context_integrity.py`.

If these conditions are met, the code is ready for production. The failover logic is sound, the first verdict path is unchanged, and the batch/deadline wiring is correct.