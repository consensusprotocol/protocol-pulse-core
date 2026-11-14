# qwen3.8-27b (qwen/qwen3.8-27b) 24 s finish=stop usage in 6103 / out 1798 usd~0.045 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0230

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the core logic of the lock and the claim. The other models highlighted several nuances I should have explicitly verified or flagged:

*   **GLM-5.3-FLASH** correctly identified the **streak semantics drift**. It noted that because `probe_result` re-stamps `last_probe_utc`, the "3 in a row" effectively spans 3 *slots* (approx 6+ minutes), not just 3 rapid checks. This is a crucial clarification of the *behavioral* change, even if the code logic is sound.
*   **QWEN3.8-27B** raised the **naming/semantic mismatch** (`probe_due` is now a mutation, not just a predicate). While I likely accepted this as "documented behavior," Qwen correctly flagged that this is a significant side-effect for a function named `probe_due`. It also correctly identified the **coordination risk** with `pp-ingest` regarding the `who` parameter.
*   **GROK-4.20** was the most concise, correctly identifying that the read+claim is atomic under the lock, which is the primary safety mechanism.

I missed explicitly articulating the **test coverage gap** regarding the intermediate state (mode still `plan_b` after 2 answers) that GLM noted.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH:**
    *   *Agree* on the drift/streak semantics. The docstring now explicitly states "3 in a row means that many slots," which aligns with the implementation.
    *   *Agree* that the `who=""` default is a cosmetic/audit risk, not a functional break.
    *   *Disagree* slightly on the "unverifiable" status of `_SEEN`. The diff shows `probe_result` is unchanged, and the test passes `now` explicitly. If `_SEEN` keys on `now` or `who`, the test's explicit `now` values ensure uniqueness. The test logic holds.
*   **GROK-4.20:**
    *   *Agree* completely. The atomicity of `with _Locked(path)` covering both the check and the stamp is the correct fix. No critical/high issues.
*   **QWEN3.8-27B:**
    *   *Agree* on the semantic shift of `probe_due`. It is now a "claim" operation.
    *   *Agree* on the coordination risk with `pp-ingest`.
    *   *Disagree* on the "flaky test" concern. The test uses mocked `now` values (`T0 + timedelta`). `probe_result` is called with `**k(16)` which passes `now=T0+16m`. The next `probe_due` is at `T0+18m`. The delta is exactly 120s. `120 < 120` is False, so it claims. This is deterministic, not flaky, because time is mocked.

## 3. NEW FINDINGS FROM THIS REVIEW

*   **<medium> `pipeline/heimdall_health.py:28-29` — State Mutation on Read Path (Semantic)**
    The function `probe_due` now mutates state (`last_probe_utc`, `last_probe_by`) and writes to disk. This is a **side-effect** in a function named `probe_due` (which implies a pure predicate).
    *   *Scenario:* A developer reading the code might assume `probe_due` is safe to call multiple times for logging/debugging without side effects. Calling it twice in quick succession (e.g., in a debug loop) would claim the slot on the first call and return `False` on the second, potentially confusing the developer into thinking the probe isn't due when it actually *was* due but was just claimed.
    *   *Mitigation:* The docstring (lines 12-18) explicitly warns: "A True CLAIMS the slot...". This is sufficient for production, but the naming remains a potential trap.

*   **<low> `tests/providers/test_heimdall_health.py:62-63` — Test Order Dependency**
    The test asserts `[True, False]` for `("pp-selectid", "pp-ingest")`. This relies on the list comprehension evaluating `probe_due` for `pp-selectid` *first*. If the order were reversed, `pp-ingest` would claim the slot, and `pp-selectid` would get `False`. The test is correct as written, but it implicitly tests the *order* of evaluation, not just the mutual exclusion. This is fine for a unit test but worth noting.

*   **<info> `pipeline/providers.py:43` — Comment Clarity**
    The comment `# claims the slot (one prober each)` is slightly ambiguous. It should clarify that *this* prober claims the slot, preventing *other* probers from claiming it in the same window.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Locking/Atomicity** | 9/10 | 10/10 | Confirmed atomic read+claim under `_Locked`. No race conditions. |
| **State Management** | 8/10 | 9/10 | `probe_due` mutation is a semantic shift, but well-documented. |
| **Test Coverage** | 8/10 | 9/10 | Tests cover the core mutual exclusion and streak logic. Minor gap on intermediate mode state, but acceptable. |
| **Documentation** | 7/10 | 9/10 | Docstring now explicitly explains the "claim" behavior and slot anchoring. |
| **Coordination** | 6/10 | 8/10 | `who` parameter is optional, allowing `pp-ingest` to adopt it gradually. Risk is low. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    1.  **`pipeline/heimdall_health.py:11`**: Consider renaming `probe_due` to `claim_probe_slot` or adding a `@side_effect` decorator/comment to emphasize it is not a pure predicate. (Low priority, docstring suffices).
    2.  **`tests/providers/test_heimdall_health.py:74`**: Add an assertion that `mode` is still `plan_b` after the *second* answer (minute 18) to ensure the streak logic doesn't flip early. (Minor test improvement).
*   **P3 LOW:**
    1.  **`pipeline/providers.py:43`**: Clarify comment to "claims the slot, preventing other probers from claiming in this window".

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the `who` parameter and the atomic claim under the lock is the highest-leverage change, as it directly resolves the R12 defect (double-probing) and provides an audit trail for future debugging.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **`pp-ingest` Coordination:** Ensure `pp-ingest` is updated to pass a non-empty `who` string (e.g., `"pp-ingest probe"`) in its next restart. Until then, `who=""` is acceptable but reduces auditability.
2.  **Monitoring:** Monitor the `last_probe_by` field in the state file to verify that both probers are correctly claiming slots and that the "3 in a row" logic is functioning as expected (i.e., taking ~6 minutes, not ~2 minutes).
3.  **Test Improvement (Optional but Recommended):** Add the intermediate mode assertion to the test to prevent future regressions in the streak logic.

**SHIP: yes**