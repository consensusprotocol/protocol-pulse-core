# gemma-4-31b-it (google/gemma-4-31b-it) 136 s finish=stop usage in 10245 / out 2863 usd_reported=0.000673 usd~0.074 (upper-bound price)

The code implements RULING 127 (2) with high precision. The objective is to ensure that any verdict (PASS or REFUSE) from the local judge (`gemma3:27b`) is treated as provisional, never cached, and never used to seal a package, forcing a retry with a "Heimdall family" (external high-tier models) in subsequent builds.

### Analysis of Implementation

1.  **Prevention of Finality (HELD status):**
    *   In `prescreen`, the logic `if str(backend).startswith(LAST_RESORT):` immediately diverts all results from the local judge into the `fails` dictionary using `local_held()`. The `continue` statement ensures these results never enter `a_by` (the set of successful first-screen verdicts).
    *   In `second_screen`, the `elif str(a2.get("backend") or "").startswith(LAST_RESORT):` block ensures that if the second-screen verdict comes from the local judge, it is marked as `HELD` rather than `PASS`.
    *   The `local_held` helper correctly wraps both passes and refusals in the `HELD` prefix, satisfying the requirement that a local REFUSE is not final.

2.  **Cache and Store Avoidance:**
    *   **Reading:** The `pick` lambda in `prescreen` now includes `and not name.startswith(LAST_RESORT)`, and the DB record check includes `and not str(rec.get("backend")).startswith(LAST_RESORT)`. This ensures that any legacy or accidentally cached local verdicts are ignored, forcing a fresh call to the router.
    *   **Writing:** Because the `prescreen` loop `continue`s when the backend is the local judge, the results are never added to the successful `a_by` collection, which is the source for subsequent caching/storage operations.

3.  **Sealing Protection:**
    *   The `second_screen` modification prevents the local judge from satisfying the "second family" requirement. Since `second_screen` is the final gate for `STEP_A` clearance, no package can be sealed based on a local judge's second verdict.

4.  **Test Coverage:**
    *   `test_every_faster_leg_unavailable_the_local_judges_answer_is_provisional_never_a_pass_never_cached` verifies the full lifecycle: Local Judge answers $\rightarrow$ Result is HELD $\rightarrow$ Not cached $\rightarrow$ Retried when DeepSeek returns.
    *   `test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read` confirms that REFUSE is treated as HELD and that the cache/store is bypassed.
    *   `test_a_second_verdict_from_the_local_judge_never_seals_a_package` confirms the build-level failure to seal.

### Verdict
The implementation is minimal, targeted, and strictly adheres to the ruling. No regressions were introduced to the logic of other backends.

P1_OR_WORSE: 0