# qwen3.8-27b (qwen/qwen3.8-27b) 31 s finish=stop usage in 13571 / out 1900 usd~0.069 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0310

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the consensus) focused heavily on the *correctness* of the `stand_alone_check` reproduction and the *fail-closed* nature of the new gate. The other models, particularly **GLM-5.3-FLASH** and **QWEN3.8-27B**, raised valid points about **semantic drift** and **test coverage gaps** that I under-weighted:

*   **GLM P1-3 (Test Coverage for FAIL Evidence):** I noted that `inventory` reads `r['opener']['why']` unguarded. I dismissed this as "fail-closed via exception" in C1. GLM correctly identified that this converts a measurable FAIL into a crash. **The C2 diff fixes this** by adding `test_inventory_writes_a_FAIL_row_with_its_evidence` (line 243). I missed that this specific test was the critical missing piece in C1.
*   **QWEN P1-1 (Hardcoded Subject):** I accepted the "byte-identical" argument for the subject. QWEN correctly flagged that hardcoding `"bitcoin"` is a latent bug if the package label ever changes. The C2 docstring (line 17-18) now explicitly justifies this by citing `package_pin.to_pin` behavior. I agree with QWEN that this is a P1 risk if the assumption breaks, but the C2 documentation mitigates it for the current scope.
*   **GLM P2-2 (`out["usable"]` Semantics):** I missed that `no_role` filtering *before* `prescreen` changed the meaning of `usable`. The C2 diff (line 64-66, 72) explicitly restores `n_usable` to the pre-filter count and adds `out["no_role"]`. This was a subtle but important state change I overlooked in C1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM P1-1 (EDL Fidelity):** The C2 diff confirms `stand_alone.py` is byte-identical. The EDL construction (lines 20-22) matches the render's expectation. The `rate=None` constraint is correctly applied.
*   **Agree with QWEN P1-2 (Over-strictness):** `no_role_on_screen` is stricter than the render. This is **intended** and **safe** (fail-closed). The docstring (line 27-29) explicitly states this. I agree this is not a bug but a feature.
*   **Disagree with Grok's "No P1" in C1:** Grok missed the `out["usable"]` semantic shift and the lack of FAIL-path test coverage in C1. These were P1s. The C2 diff addresses both.
*   **Agree with Consensus K1-K4:** The C2 diff implements all four consensus items.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `no_role_on_screen` uses `m.get("text")` but `stand_alone_check` uses `segs[0]["text"]` and `m["text"]`.**
*   `pipeline/package.py:31-32`: `no_role_on_screen` calls `SA.opener("clip", m.get("text"))`.
*   `pipeline/package.py:20-22`: `stand_alone_check` accesses `segs[0]["text"]` and `m["text"]` directly.
*   **Risk:** If a moment dict lacks a `"text"` key, `no_role_on_screen` will pass `None` to `SA.opener`, which may behave differently than a KeyError in `stand_alone_check`. However, `usable()` (line 63) likely guarantees `text` exists. **Verdict:** Low risk, but inconsistent access patterns.

**P2-NEW-1: `lineup_for` calls `stand_alone_check` inside the loop (line 55).**
*   `pipeline/package.py:55`: `if need_stand_alone and not stand_alone_check([h] + order)["ok"]:`
*   **Risk:** `stand_alone_check` imports `stand_alone` (line 19) and calls `SA.check_edl`. If `lineup_for` is called many times (e.g., in a retry loop), this could be a performance bottleneck. However, `import` is cached, and `check_edl` is likely fast (regex-based). **Verdict:** Acceptable, but worth monitoring.

**P2-NEW-2: `inventory` evidence rows use `r['segment']` (line 140).**
*   `pipeline/package.py:140`: `rows=[f"{r['segment']}: ..."`
*   **Risk:** If `check_edl` returns rows without a `"segment"` key, this will raise a KeyError. The test `test_inventory_writes_a_FAIL_row_with_its_evidence` (line 243) verifies this works for the FAIL case. **Verdict:** Verified by test.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `stand_alone_check` | 8/10 | 9/10 | C2 docstring clarifies subject hardcoding; EDL fidelity verified. |
| `no_role_on_screen` | 7/10 | 8/10 | C2 explicitly documents over-strictness as intended; `out["no_role"]` added. |
| `lineup_for` | 8/10 | 9/10 | `need_stand_alone` parameter added; fail-closed behavior verified. |
| `inventory` | 7/10 | 9/10 | C2 adds FAIL-path test; `stand` parameter documented. |
| `package_pin` | 9/10 | 9/10 | `MEDLEY_GATES` updated; comment clarified. |
| **Tests** | 6/10 | 9/10 | C2 adds `TestStandAloneAtThePinStage` with comprehensive coverage. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`pipeline/package.py:17-18` (Subject Hardcoding):** The docstring now justifies the hardcoded `"bitcoin"` subject by citing `package_pin.to_pin`. **Condition:** Verify that `package_pin.to_pin` *always* labels moments pins as `"bitcoin"`. If this is not true, the check will fail for non-bitcoin packages. *Action:* Add a test or assertion in `package_pin` to ensure this invariant.

**P2 MEDIUM:**
1.  **`pipeline/package.py:31-32` (Inconsistent Text Access):** `no_role_on_screen` uses `m.get("text")` while `stand_alone_check` uses `m["text"]`. *Action:* Standardize to `m["text"]` to fail fast if text is missing.
2.  **`pipeline/package.py:55` (Performance):** `stand_alone_check` is called inside the `lineup_for` loop. *Action:* Profile if this becomes a bottleneck.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The addition of `test_inventory_writes_a_FAIL_row_with_its_evidence` (line 243) is the highest-leverage change.** It closes the critical gap identified by GLM in C1, ensuring that the FAIL path is not only fail-closed but also produces well-formed evidence rows, preventing silent crashes and verifying the gate's integrity.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Verify Subject Invariant:** Confirm that `package_pin.to_pin` always labels moments pins as `"bitcoin"`. If this is not guaranteed, parameterize the subject in `stand_alone_check` or add a runtime check.
2.  **Standardize Text Access:** Change `m.get("text")` to `m["text"]` in `no_role_on_screen` (line 31-32) to fail fast if text is missing.

If these conditions are met, the code is production-ready. The C2 diff addresses all P1s from C1, and the new tests provide comprehensive coverage for the new gate.