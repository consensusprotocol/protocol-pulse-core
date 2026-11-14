# heimdall_qwen (qwen/qwen3.8-27b, 191.0 s, $0.020, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic as sound and the fallback as safe, but I missed two specific edge-case nuances that the other reviewers (specifically GLM and Muse) highlighted:

1.  **Positional-Only Parameter Risk (GLM P3):** I stated the signature check was "sound for a plain Python function" but did not explicitly analyze what happens if the builder's future module defines `who` as a positional-only parameter (e.g., `def probe_due(path, now, who, /)`). In that case, `inspect.signature` would see the parameter, `takes_who` would be `True`, but the call `probe_due(now=..., who=...)` would raise a `TypeError` because `who` cannot be passed as a keyword. GLM correctly noted that this would be caught by `_call`'s broad `except Exception`, resulting in a "signal not read" state (fail-closed), but it is a subtle failure mode worth documenting.
2.  **Decorator/`__wrapped__` Behavior (Muse P3):** I noted that `inspect.signature` follows the `__wrapped__` chain but did not explicitly state the consequence: if the builder decorates `probe_due` without `@functools.wraps`, the signature would reflect the wrapper, not the inner function. If the wrapper doesn't expose `who`, `takes_who` would be `False`, silently disabling the claim. Muse correctly identified this as "fail-safe, not fail-dangerous" (we just don't claim, we don't crash), but I missed the explicit mechanism.
3.  **Stale `probe_kw` on Module Reload (GLM P3):** I noted `probe_kw` is set once in `__init__`. GLM explicitly pointed out that if the module were reloaded (which the deployment model says it isn't, but is a theoretical constraint), the kw would be stale. I missed explicitly linking this to the "loaded once per process" deployment constraint.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM (glm-5.3-flash):**
    *   **Agree** with the P3 on positional-only parameters. It is a valid theoretical edge case.
    *   **Agree** with the P3 on the check being done once at start. It is consistent with the deployment model.
    *   **Agree** with the P2 note on long probes. If a probe takes >120s and the report is dropped, the next `probe_due` is due immediately. This is correct behavior per the "claim-anchored" semantics.
    *   **Disagree** (slightly) on the severity of the "stale kw" issue. Since the module is loaded once per process and never reloaded, this is not a bug, just a documented constraint. I would not even call it P3, just a note.

*   **Muse (muse-spark-open-816b-a42b):**
    *   **Agree** with the exhaustive table of module versions. It is the clearest way to present the correctness argument.
    *   **Agree** with the P2 on `BaseException` in `_call`. I missed this in Cycle 1. If `probe_due` raises `SystemExit` or `KeyboardInterrupt`, `_call`'s `except Exception` will not catch it, and it will propagate up. However, as Muse notes, `KeyboardInterrupt` is only delivered to the main thread, and `SystemExit` from a builder module would be a bug in that module. So it is not a practical risk, but a valid code review point.
    *   **Agree** with the P3 on `__wrapped__`. It is a good catch.

*   **Qwen (myself, Cycle 1):**
    *   **Agree** with my own assessment that the change is correct and well-executed.
    *   **Disagree** with my own P3 on testing the `inspect.signature` fallback. While a test is good, the fallback is so simple (`takes_who = False`) that the risk of it failing is negligible. The more important test is the one already added: `test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name`.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **No New Bugs Found:** The combined analysis of all three reviewers in Cycle 1, plus my re-review, has not uncovered any new P0 or P1 issues. The change is minimal, well-isolated, and fail-closed.
2.  **Observability Improvement:** The addition of `probe_claimed_as` to the snapshot (downsignal.py:360) is a good addition for observability. It allows operators to see which prober claimed the last probe slot. This was not explicitly highlighted in Cycle 1 but is a positive aspect of the change.
3.  **Backward Compatibility:** The change is resilient to module version differences (older modules without `who` parameter). This is a good practice for backward compatibility.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Backend logic | 95/100 | 95/100 | No change. The logic is sound. |
| Frontend/UI | N/A | N/A | N/A |
| Error handling | 95/100 | 95/100 | No change. The fallback is safe. |
| Security | 100/100 | 100/100 | No change. No security issues. |
| Performance | 100/100 | 100/100 | No change. No performance impact. |
| Law compliance | 100/100 | 100/100 | No change. All laws are compliant. |
| World-class gap | 95/100 | 95/100 | No change. The service is already production-grade. |
| **OVERALL** | **95/100** | **95/100** | **No change.** |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    *   **downsignal.py:118-121:** Add a comment or docstring note about the positional-only parameter edge case (GLM P3). If a future module makes `who` positional-only, the call will fail with `TypeError`, which is caught by `_call` and read as "signal not read". This is fail-closed, but it is worth documenting.
    *   **downsignal.py:118-121:** Add a comment or docstring note about the `__wrapped__` behavior (Muse P3). If the builder decorates `probe_due` without `@functools.wraps`, the signature will be the wrapper's, and `takes_who` will be `False`, silently disabling the claim. This is fail-safe, but it is worth documenting.
*   **P3 LOW:**
    *   **downsignal.py:118-121:** Add a test for the case where `inspect.signature` fails (Qwen Cycle 1 P3). The fallback is safe, but a test would confirm it works as expected.
    *   **downsignal.py:118-121:** Add a comment or docstring note about the check being done once at start (GLM P3). The module is loaded once per process, so a restart takes up a new version. This is a documented constraint.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The change is correct and well-executed; the only improvement would be to add a test for the `inspect.signature` fallback to ensure it works as expected in edge cases.

## 7. PRODUCTION READY?

**Yes.**

The change is minimal, well-isolated, and fail-closed. It does not introduce any new risks. The service is already production-grade, and this change maintains that standard. The only conditions are:

1.  The builder's module must be version 11ed255f or later (with the `who` parameter).
2.  The watcher must be restarted to take up the new module version.

Both conditions are met by the deployment plan.