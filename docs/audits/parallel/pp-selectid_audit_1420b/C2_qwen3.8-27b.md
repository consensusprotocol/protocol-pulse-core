# qwen3.8-27b (qwen/qwen3.8-27b) 36 s finish=stop usage in 9933 / out 2037 usd~0.060 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-1420b

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the mechanical correctness of the clamp (F2) and the sort key (F1), but I missed the **semantic integrity issue** flagged by GLM-5.3-Flash (P1-1) and the **exception surface** flagged by Grok (P1).

*   **GLM's P1-1 (The "Lying" Registry Flag):** I missed that `res["registry"] = True` is set *before* the guarded block. If the registry save fails, the `package.json` claims the registry was updated, but it wasn't. This creates a state divergence where a downstream driver trusting the flag will skip re-seeding, leading to silent loss of paid work.
*   **Grok's P1 (Exception Surface):** I missed verifying that the *entire* `main()` path is protected. While the diff shows a `try/except` around `PK.build` inside `try_one`, and a `try/except` around the registry save, I did not explicitly verify that a crash in `CA.run_due` (e.g., from a malformed `found_at` in `due()`) is caught by the driver's *refusal block* before any writes occur. The new test `test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written` (line 141) confirms this, but I didn't trace that specific path in Cycle 1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM P1-1 (Registry Flag):** **AGREE.** This is a valid P1. The flag `res["registry"] = True` (line 73) is unconditional. If the `os.replace` in the guarded block (line 89) fails, the record says "registry updated" but the disk says "registry unchanged." This violates the "record stands" guarantee in a subtle way: the record stands, but it lies about the side-effect.
*   **GLM P1-2 (F2 Clamp):** **DISAGREE (Downgrade to P2).** GLM worried about under-charging. The code (lines 21-24) clamps `judged` to `lineups` if it's out of range. `lineups` starts at 8. If `try_one` returns 99, `judged` becomes 8, `lineups` becomes 0. The next candidate sees `lineups=0`. The angle build sees `lineups=0`. Total charged = 8. It cannot exceed 8. It cannot under-charge the *budget* (it charges the max allowed). It might under-charge the *truth* (if the build actually used 10, we only record 8), but the system's invariant is "never exceed 8," which holds.
*   **Grok P1 (F3 Crash):** **AGREE (Resolved by Test).** The concern was valid, but the new test (line 141) proves that a malformed `found_at` causes an exit 2 *before* any writes. The `due()` function is called in the refusal block (implied by the test passing and the driver structure).
*   **Qwen P1 (Negative Lineups):** **DISAGREE (Self-Refuted).** Qwen correctly identified that the clamp prevents negative lineups. `judged` is capped at `lineups`, so `lineups -= judged` results in `lineups >= 0`.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: The `--from-candidate` path bypasses the F2 clamp for `candidate_tries` recording.**
*   **File:** `tests/package/proof_ledger.py:44-47`
*   **Scenario:** In the `--from-candidate` branch, `res["candidate_tries"]` is constructed manually. The `judged` field is set to `(res.get("search") or {}).get("lineups", 0)`. This value comes from the `PK.build` result. If `PK.build` reports a `lineups` count that is inconsistent with the actual budget (e.g., it reports 0 but consumed 3, or reports 10 when only 8 were available), this value is recorded *without* the F2 clamp logic that applies to the `run_due` path.
*   **Impact:** The audit trail (`candidate_tries`) may contain inaccurate `judged` counts for `--from-candidate` runs. However, since `--from-candidate` is a single-candidate run (not a loop over due candidates), the "8 lineups" budget is less critical here (it's a specific re-try). The registry state is still driven by `CA.outcome` (line 84), which uses `res["candidate"]["class"]`, not the `judged` count. So the *state* is correct, but the *record* is potentially misleading.
*   **Severity:** P2 (Informational inaccuracy in audit trail, not a state corruption or budget breach).

**P2-NEW-1: `res["registry"] = True` is set before the guarded block.**
*   **File:** `tests/package/proof_ledger.py:73`
*   **Scenario:** As noted by GLM. If the registry save fails (line 90-92), the `package.json` (written at line 77) contains `"registry": true`. A subsequent run reading this `package.json` might assume the registry is up-to-date and skip re-seeding or validation, leading to silent loss of the candidate's outcome.
*   **Severity:** P1 (State divergence).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **F1 (Sort)** | 9/10 | 10/10 | New test confirms malformed time refusal. Zoneless handling verified. |
| **F2 (Clamp)** | 8/10 | 9/10 | Logic is sound. Minor concern about `--from-candidate` bypassing clamp for *recording* only. |
| **F3 (Guard)** | 7/10 | 8/10 | Exception handling is robust. The `registry: true` flag issue is a semantic flaw, not a crash. |
| **F4 (Shape)** | 9/10 | 9/10 | `candidate_tries` shape is consistent. |
| **Tests** | 8/10 | 9/10 | New tests cover the critical failure modes (malformed time, out-of-range judged). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
1.  **`tests/package/proof_ledger.py:73`**: `res["registry"] = True` is set unconditionally before the guarded registry save. If the save fails, the record claims the registry was updated. **Fix:** Move `res["registry"] = True` *inside* the `try` block, after `os.replace` succeeds, or set it to `False` in the `except` block.

**P2 MEDIUM**
1.  **`tests/package/proof_ledger.py:44-47`**: The `--from-candidate` path records `judged` from `res["search"]["lineups"]` without clamping. **Fix:** Apply the same clamp logic as `run_due` to the `judged` value before recording it in `candidate_tries`, or document that `--from-candidate` does not enforce the 8-lineup budget in the same way.
2.  **`pipeline/candidates.py:10-12`**: `_at` behavior on malformed strings is now tested, but the driver's refusal block dependency is implicit. **Fix:** Add a comment in `proof_ledger.py` near the `CA.due` call in the refusal block, explicitly stating that a `ValueError` from `due()` is expected to trigger exit 2.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Move `res["registry"] = True` into the success path of the guarded registry block.** This single change ensures that the `package.json` record accurately reflects the state of the registry on disk, preventing silent data loss in subsequent runs that trust the flag.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Fix P1-1:** Ensure `res["registry"]` is only set to `True` if the registry save succeeds. If it fails, it should be `False` or omitted, so downstream consumers know the registry is stale.
2.  **Verify P2-1:** Confirm that the `--from-candidate` path's `judged` count inaccuracy is acceptable for the audit trail, or apply the clamp.

If P1-1 is fixed, the code is robust against the identified failure modes. The F2 clamp is mechanically sound, and F3's exception handling is verified by the new tests.