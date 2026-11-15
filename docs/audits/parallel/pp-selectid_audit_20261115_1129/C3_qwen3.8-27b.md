# qwen3.8-27b (qwen/qwen3.8-27b) 50 s finish=stop usage in 9065 / out 1814 usd_reported=0.002558 usd~0.054 (upper-bound price)

# PROTOCOL PULSE — CYCLE 3 CODE AUDIT
# Feature: pp-selectid-20261115_1129
# Reviewer: Claude (Cycle 3)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 2, I (and the other models) focused heavily on the internal logic of the traces, the read-only compliance, and the calibration guards. We all missed the **environmental dependency** of the calibration path.

Specifically:
*   **The `proof_saved_runs` import failure:** The Cycle 2 code imported `proof_saved_runs` (from `tests/select_by_id`) to get the channel registry (`PS.REG`). This module is not on the `sys.path` of `tests/package`. The first live run (11:52 ET Nov 15) died with `ModuleNotFoundError` before any router was built or any paid call was made. This was a P1 defect (the driver does not run) that was invisible to the offline unit tests because the tests mocked the router and did not exercise the `main()` import path for the registry.
*   **The fix:** The new `registry()` function reads `pipeline/channels.json` directly. This is the same file that `proof_saved_runs.REG` points to, but it removes the cross-test-folder dependency.
*   **The new test:** `TestTheDriverEndToEnd` runs `main()` with the calibration on. It stubs the router and the paid call (`hook_ratings`), but it exercises the *real* `main()` code path, including the `registry()` call and the file writing. This test would have caught the `ModuleNotFoundError` in Cycle 2.

What they caught that I missed: The fact that a "read-only" driver can still fail due to *import* side effects (path resolution) that are not covered by mocking the *logic* but not the *environment*.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Cycle 2 Consensus (P1_OR_WORSE: 0):** Disagree. The code was not production-ready because it crashed on import. The consensus missed the `sys.path` issue because the tests were too isolated.
*   **Grok's Cycle 2 Findings (P2s on regex, step-A prose):** Agree. These are still valid P2s. The fix for the import does not change the brittleness of the string matching or the dead regex alternative.
*   **GLM's Cycle 2 Findings (P3s on comments, magic numbers):** Agree. These remain P3s.
*   **The Fix Itself:** Agree. Reading `pipeline/channels.json` directly is the correct fix. It is the same data source, but it is local to the repository structure that `tests/package` can access without importing sibling test folders. The new test is well-constructed: it mocks the expensive/external parts (router, paid call) but lets the driver's own logic (file I/O, registry loading, JSON writing) run.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] F1 — `registry()` does not handle missing file
**File:** `tests/package/hook112.py`, lines 9-13.
```python
def registry(path=os.path.join(REPO, "pipeline", "channels.json")):
    with open(path) as f:
        return json.load(f)
```
If `pipeline/channels.json` is missing or malformed, `main()` will crash with a `FileNotFoundError` or `json.JSONDecodeError`. This is acceptable for a diagnostic tool (fail fast), but the error message will be cryptic. A `try/except` with a clear message ("Channel registry not found at ...") would be better. However, since this file is a core part of the pipeline, its absence is a critical environment error, so failing fast is arguably correct. **Verdict:** P3 (nit).

### [P2] F2 — `TestTheDriverEndToEnd` does not verify the *content* of the registry used
**File:** `tests/package/test_hook112.py`, lines 54-79.
The test asserts that `ctx.channel("no-such-channel") is None` (line 60), which proves that *a* context was created. It does not assert that the context contains the *expected* channels from `pipeline/channels.json`. If `registry()` returned an empty dict, the test would still pass (as long as `no-such-channel` is not in it). A stronger test would assert that a known channel (e.g., "qwen") is in the context. **Verdict:** P2.

### [P3] F3 — `registry()` is not mocked in the end-to-end test
**File:** `tests/package/test_hook112.py`, lines 69-72.
The test mocks `H.build_router`, `PK.hook_ratings`, etc., but not `H.registry`. This means the test *does* read the real `pipeline/channels.json`. This is good (it tests the real path), but it makes the test dependent on the file existing in the test environment. If the test is run in a minimal environment without `pipeline/`, it will fail. This is acceptable for a repo-local test, but worth noting. **Verdict:** P3.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Cycle 3 | Why changed |
| :--- | :--- | :--- | :--- | :--- |
| Funnel / trace logic | P1:2 | P2:2 | P2:2 | No change. |
| Read-only & isolation | P1:1 | P3:1 | P3:1 | No change. |
| Calibration / router | P2:2 | P3:2 | P2:1 | The import fix is correct, but the new test has a gap (F2). |
| Ledger / roll-up | P2:1 | P2:1 | P2:1 | No change. |
| **Overall** | P1:3 | P2:3 | **P2:2** | The P1 import defect is fixed. Residual issues are P2/P3. |

## 5. FINAL PRIORITY LIST

1.  **[P2]** `tests/package/test_hook112.py:60` — Strengthen the end-to-end test to assert that a known channel (e.g., "qwen") is present in the context, not just that a fake one is absent.
2.  **[P2]** `tests/package/hook112.py:75` — Remove the dead "STAND_ALONE with the clip scorer|" regex alternative (from Cycle 2, still present).
3.  **[P2]** `tests/package/hook112.py:177-178` — Add a comment citing the exact `spotlight.build` lines that produce the "step A" string, to justify the brittle match (from Cycle 2, still present).
4.  **[P3]** `tests/package/hook112.py:9-13` — Add a clear error message if `pipeline/channels.json` is missing.
5.  **[P3]** `tests/package/hook112.py:225` — Replace the magic depth limit of 4 in `resolve()` with a visited set or a named constant.

**P1_OR_WORSE: 0**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of `TestTheDriverEndToEnd` is the highest-leverage change in this cycle. It closes the gap between "unit tests pass" and "the driver actually runs," which is the class of bug that caused the 11:52 ET failure.

## 7. PRODUCTION READY?

**Yes with conditions:**
1.  Strengthen the end-to-end test to assert the presence of a known channel (P2 F2).
2.  Remove the dead regex alternative (P2 F1 from Cycle 2).
3.  Add the comment for the step-A string match (P2 F2 from Cycle 2).

The import defect is fixed. The driver will now run. The remaining issues are maintainability and test robustness, not correctness.