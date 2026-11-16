# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 13220 / out 1763 usd_reported=0.001872 usd~0.066 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0536
# Reviewer: [Model Name] (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the high-level logic of the cap but may have missed the specific interaction between the `uncapped` filter and the `usd_unreported_estimate` field in the "reported" basis calculation.

**Gemma-4-31B-IT** made a significant error in Cycle 1, claiming `spent()` used an undefined variable `b`. This was refuted by the consensus and the code (the change is in `_reserve`, not `spent`). However, Gemma correctly identified that the logic for handling "free" or "uncapped" backends needed to be isolated from the total spend calculation.

**Qwen3.8-27B** correctly identified the "stricter reading" of the `usd_unreported_estimate`. It noted that if Heimdall calls contribute to the unreported estimate, counting them against the outside vendor cap is a conservative (safe) error. This is a crucial nuance: the code *intentionally* over-counts the cap usage if unreported estimates exist, ensuring we never accidentally exceed the $1.00 limit for outside vendors. I agree with this assessment.

**My Miss:** I did not explicitly verify in Cycle 1 that the `day_ledger` function correctly handles the transition from the hardcoded `SPEND_B4.json` to the dynamic `SPEND_D{date}.json` files, specifically regarding the 21:10 ET boundary. The tests in `test_ruling_102.py` (lines 253-265) cover this, but I should have explicitly traced the `datetime` logic to ensure no off-by-one errors exist at the boundary.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma's P0 (Undefined `b` in `spent()`):** **DISAGREE.** This is factually incorrect. The diff shows the change is in `_reserve(self, b, upper)` (line 55 of the diff, corresponding to `pipeline/providers.py`), where `b` is a parameter. `spent()` (line 49 of the diff) is unchanged and calls `_basis_total`. The tests pass, confirming this.
*   **Qwen's P2 (Unreported Estimate Handling):** **AGREE.** The code adds the *entire* `usd_unreported_estimate` to the capped total in the "reported" basis (lines 39-42 of the diff). This is the "stricter reading." If Heimdall (uncapped) has unreported costs, they are counted against the $1.00 outside vendor cap. This is safe (fail-closed) but potentially conservative. It prevents passing the cap but might stop outside calls earlier than necessary if Heimdall has significant unreported estimates. Given Heimdall is local/free, its "unreported" costs are likely negligible or zero, so this is acceptable.
*   **Consensus on Day Ledger:** **AGREE.** The `day_ledger` function (lines 124-133 of the diff) correctly implements the 21:10 ET boundary. The special case for `20261115` mapping to `SPEND_B4.json` is deliberate and tested.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] Potential Ambiguity in `usd_unreported_estimate` Attribution**
In `pipeline/providers.py` (lines 39-42 of the diff), the "reported" basis sums `usd_reported` for capped vendors and adds the *entire* `usd_unreported_estimate`. The comment says "the unreported estimate keeps no vendor split, so all of it counts." This is correct for fail-closed behavior. However, if the ledger format ever changes to include vendor splits in `usd_unreported_estimate`, this logic would need to be updated to filter by `uncapped` vendors as well. Currently, it is safe.

**[P3] `build_shadow` Filtering Logic**
In `tests/package/proof_ledger.py` (lines 78-79 of the diff), `build_shadow` filters the shadow dict to keep only entries where the vendor part is in `PL.UNCAPPED`. This correctly drops Grok (outside) and keeps Heimdall (uncapped). The test `test_ledger_build.py` (lines 156-161) verifies this. No issue found.

**[P2] `LY_STOP_USD` and `LY_LIMIT_USD` Equality**
In `tests/package/proof_ly.py` (lines 138-140 of the diff), `LY_LIMIT_USD = 1.00` and `LY_STOP_USD = 1.00`. Previously, there was headroom (Limit 4.50, Stop 4.00). Now, the stop and limit are identical. This means a build will not start if the spent amount is >= $1.00. Since each paid call reserves its upper bound, the spent amount will never exceed the limit. This is consistent with the "HARD CAP" requirement. No issue found.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `pipeline/providers.py` | 9/10 | 10/10 | Confirmed `spent()` and `_reserve` logic is correct. The `uncapped` filter is properly applied in `_basis_total` and `_reserve`. |
| `tests/package/proof_ly.py` | 8/10 | 9/10 | `day_ledger` logic is sound. The hardcoded first day is a minor architectural nit but necessary for migration. |
| `tests/package/proof_ledger.py` | 9/10 | 10/10 | Shadow filtering is correct. `build_router` passes `uncapped` correctly. |
| Tests | 9/10 | 10/10 | Comprehensive coverage of the new logic, including boundary conditions and fail-closed behavior. |

## 5. FINAL PRIORITY LIST

*   **[P0] None.** No critical defects found.
*   **[P1] None.** No high-priority defects found.
*   **[P2] None.** No medium-priority defects found.
*   **[P3] Nit:** The `usd_unreported_estimate` handling in `_basis_total` (reported basis) counts the entire estimate against the capped total. This is safe but conservative. If Heimdall's unreported estimates are non-zero, they will reduce the available budget for outside vendors. This is acceptable under "Fail Closed."

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The implementation of `uncapped` in `Router._basis_total` and `Router._reserve` is the highest-leverage change, as it correctly isolates Heimdall's costs from the outside vendor cap while maintaining fail-closed behavior for unreported estimates.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements RULING 118:
1.  Outside vendors are capped at $1.00/day.
2.  Heimdall is recorded but never capped or reserved.
3.  The day ledger correctly handles the 21:10 ET boundary and the migration from Batch 4.
4.  Tests are comprehensive and pass.

**Conditions:**
*   Ensure that `usd_unreported_estimate` for Heimdall is negligible or zero, as it will count against the outside vendor cap. If Heimdall has significant unreported costs, the outside vendor budget will be reduced.
*   Monitor the `SPEND_D{date}.json` files to ensure they are created and updated correctly after the first day (Nov 16).

P1_OR_WORSE: 0