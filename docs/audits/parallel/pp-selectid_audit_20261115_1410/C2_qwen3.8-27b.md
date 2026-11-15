# qwen3.8-27b (qwen/qwen3.8-27b) 94 s finish=stop usage in 50247 / out 1832 usd_reported=0.007806 usd~0.178 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1410
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the structural integrity of the new `hook_bar.py` module and the routing changes. I missed or under-weighted three specific issues that the other models (Grok, Qwen, and the consensus) identified:

1.  **The "Future Time" Staleness Bug (Qwen/Grok):** I noted that `bar()` checks age, but I failed to trace the logic for a `measured_at` timestamp that is *ahead* of `now`. If `measured_at` is in the future, `now - at` is negative. A negative age is less than `24h`, so the check `age > timedelta(hours=VALID_H)` passes, allowing a "future" calibration to remain valid indefinitely until the clock catches up. This is a fail-open scenario for a security gate.
2.  **The Naive Timezone Crash (Glm/Consensus):** I assumed `datetime.fromisoformat` would handle the string, but I did not verify that a naive datetime (no timezone) would raise a `TypeError` during subtraction with `datetime.now(timezone.utc)`. This would crash the build rather than failing closed.
3.  **The Cache/Rater Mismatch (Glm):** I verified that the cache key includes the question version, but I missed the subtle issue that a cached rating from a *different* model (e.g., if the hook list changed from Grok to Qwen, or vice versa) would still be served from the cache if the question version didn't change. The fix (checking `router.chain` against the cached backend) was not in my Cycle 1 analysis.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok [P1] "Nothing else changes" semantic diff:** **AGREE.** The change to exclude the hook from the `min(...) >= COHERENCE_MIN` check in `medley` and `coherence` is a necessary consequence of the new floors (scroll=3), but it is a semantic change to the verdict logic. It is correctly implemented, but it should have been explicitly flagged to PBX as a deviation from the literal "nothing else changes" instruction. The code comments acknowledge this, which is good, but it remains a P1 for audit clarity.
*   **Qwen [P1] Future time staleness:** **AGREE.** This is a real defect. A calibration measured "in the future" (due to clock skew or error) would bypass the 24h expiry. The fix in the diff (refusing if `age < -SKEW_MIN`) is correct.
*   **Glm [P1] Cache/Rater mismatch:** **AGREE.** If the hook list changes, old cached ratings from the old rater must not be used. The fix in `hook_ratings` (checking `name in listed`) is correct and necessary.
*   **Grok [P2] Asymmetric rater check in `bar()`:** **PARTIALLY AGREE.** `bar(rater=None)` skips the rater check, but `passes()` enforces it. This is by design: `bar()` validates the *calibration file's* metadata, while `passes()` validates the *rating record's* backend against the live bar. The asymmetry is safe because `passes()` is the final gate. However, adding a comment clarifying this is a good P2.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `hook_bar.py` line 82: `int(cal["floors"][p])` can raise `ValueError` if the floor is a string.**
The `try` block catches `ValueError`, so this is handled, but the error message "no readable measured_at or floors" is slightly misleading if the issue is specifically a non-integer floor. It's a minor nit, but the error message could be more precise.

**[P2] `package.py` line 348: `cache = cache if seed == HOOK_SEED else None`.**
This correctly prevents non-production seeds from reading/writing the cache. However, if `HOOK_SEED` is changed in the future, all existing caches become invalid. This is intended behavior (fail closed), but it means a seed change requires a full re-rating of all hooks. This is a significant cost but is the correct security posture. No change needed, but worth noting in the changelog.

**[P3] `tests/package/conftest.py` line 801: `rig_bar()` uses a hardcoded `measured_at`.**
The rig bar uses a fixed timestamp. If the test suite runs across a 24-hour boundary, the rig bar might become stale. However, since `_live_bar` is mocked in most tests, this is only an issue for tests that use `real_hook_bar = True`. Those tests should ideally use a dynamic timestamp or mock `datetime.now`. This is a P3 because the live tests are few and controlled.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `hook_bar.py` | 8/10 | 9/10 | The future-time and naive-timezone bugs were fixed in the diff. The module is now robust. |
| `package.py` | 7/10 | 9/10 | The cache/rater mismatch fix and the "alone" asking change are well-implemented. The semantic diff in verdicts is acknowledged. |
| `providers.py` | 8/10 | 9/10 | The shadow chain logic for `kind` is clean and tested. |
| `model_providers.json` | 9/10 | 10/10 | Correctly restricts hook rating to Grok alone. |
| Tests | 8/10 | 9/10 | New tests cover the specific bugs found in Cycle 1 (future time, naive time, cache mismatch). |

## 5. FINAL PRIORITY LIST

*   **[P1] `package.py` / `medley` / `coherence`:** The exclusion of the hook from the `COHERENCE_MIN` check is a semantic change. Ensure PBX has explicitly approved this reading of "nothing else changes." If not, this is a P0. (Assuming approval, it is a P1 for documentation).
*   **[P2] `hook_bar.py` line 88:** The `SKEW_MIN` check is good, but consider logging a warning if the skew is close to the limit, to help debug clock issues.
*   **[P2] `package.py` line 344-347:** The `try/except` around `router.chain` is good, but the fallback `listed = None` means the cache check is skipped. This is safe (fail closed on the rater check in `passes`), but it might be better to fail the build if the router doesn't support `chain`, to avoid silent misconfiguration.
*   **[P3] `tests/package/conftest.py`:** Use dynamic timestamps in `rig_bar()` to avoid potential staleness in long-running test suites.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The most critical change is the **cache/rater mismatch fix** in `hook_ratings`. Without it, a change in the hook rater (e.g., from Grok to Qwen) would silently use old, invalid ratings, breaking the "calibrated bar" guarantee. This fix ensures that the bar is always enforced by the current rater.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  PBX must explicitly confirm that the exclusion of the hook from the `COHERENCE_MIN` check in `medley` and `coherence` is the intended reading of "nothing else changes."
2.  The `SKEW_MIN` value (5 minutes) should be reviewed to ensure it is appropriate for the production environment's clock synchronization.
3.  The `hook_calibration.json` file must be re-sealed with the correct `measured_at` timestamp before deployment.

P1_OR_WORSE: 1