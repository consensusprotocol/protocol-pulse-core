# qwen3.8-27b (qwen/qwen3.8-27b) 48 s finish=stop usage in 6387 / out 1776 usd_reported=0.002188 usd~0.046 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2114
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic but missed two specific test-pinning gaps that GLM-5.3-FLASH and Qwen3.8-27B highlighted:

1.  **`LY_LIMIT_BASIS` Pinning:** I noted the basis was "reported" but did not explicitly flag that the *test* failed to pin this constant. GLM correctly identified that if the basis flipped to `"estimate"`, the $4.50 cap would have a different semantic meaning (counting estimates for all calls vs. only where vendors report none), yet the test would remain green. This is a significant semantic gap.
2.  **Headroom Invariant Pinning:** I verified the math ($4.50 - $4.00 = $0.50) but did not flag that the test only pinned the *constants* (4.00, 4.50) and not the *relationship* between them. If a future ruling changed the stop to $4.40, the test would pass, but the "one build headroom" invariant (max build cost $0.50) would be violated, potentially allowing a build to start that ends over the cap if the max build cost assumption changed. GLM caught this.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH:**
    *   **Agree:** On the `LY_LIMIT_BASIS` pinning gap. This is a [P2] that should be fixed to ensure semantic stability.
    *   **Agree:** On the headroom invariant pinning. Adding `assertGreaterEqual(LY_LIMIT_USD - LY_STOP_USD, 0.50)` is a robust way to enforce the "never start a build that ends over the cap" logic against future constant drift.
    *   **Disagree (Minor):** GLM suggested checking `SPEND_LY.json` mtime. While valid, the consensus notes that `replay85.py` is the only other reference and is not part of the build path. The test pinning `SPEND_B3.json` is sufficient for the *build* path. The mtime check is a [P3] nice-to-have, not a [P2] must-fix.

*   **QWEN3.8-27B:**
    *   **Agree:** On the boundary analysis. Qwen correctly identified that stopping at $4.00 is "conservative" (fail-closed) because starting at $4.00 with a $0.50 build would end exactly at $4.50 (the cap). The code refuses at `>= 4.00`, which is safe.
    *   **Agree:** On the verdict that the path change is correct based on the diff.

## 3. NEW FINDINGS FROM THIS REVIEW

*   **[P3] Comment Clarity on "Closed" Ledger:** The comment in `proof_ly.py` (line 27) states `SPEND_LY.json is CLOSED at $11.47`. This is a static comment. If the ledger file is ever accidentally modified, the comment becomes a lie. However, since the code no longer writes to it, this is a documentation nit, not a code defect.
*   **[P3] Test Name vs. Docstring:** The test name `test_no_build_starts_at_the_stop_and_one_starts_below` is generic. The docstring correctly cites RULING 108. This is fine, but future maintainers might not realize the test is specifically for Batch 3. A more specific name like `test_batch3_stop_and_limit_invariants` would be clearer. [P3]

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Logic Correctness** | 9/10 | 10/10 | Confirmed by Qwen's boundary analysis. The fail-closed behavior at $4.00 is correct. |
| **Test Coverage** | 7/10 | 9/10 | The Cycle 1 diff *already included* the fixes for `LY_LIMIT_BASIS` and headroom (lines 53-54 in the provided diff). My Cycle 1 review was of the *pre-fix* state or I missed that the diff provided *is* the fixed version. Re-reading the prompt: "THE CODE NOW: the FIXED diff". The diff *includes* the assertions for `LY_LIMIT_BASIS` and headroom. Therefore, the test coverage is now strong. |
| **Documentation** | 8/10 | 8/10 | Comments are clear. The "closed" ledger note is sufficient. |

*Correction:* I initially thought the diff was the *original* code, but the prompt says "THE CODE NOW: the FIXED diff". Looking at lines 53-54 of the diff:
```python
self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)   # one build's headroom (C1, glm)
```
These lines **are present** in the provided diff. This means the Cycle 1 findings from GLM were **already implemented** in the code I am reviewing in Cycle 2. My Cycle 1 review (which I am simulating as "what I said before") likely missed that these were already there or I was reviewing a pre-fix version. In this Cycle 2 review, I confirm these fixes are present and correct.

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:** None. (The P2s from Cycle 1 are already fixed in the provided diff).
*   **P3 NIT:**
    *   `tests/package/proof_ly.py` line 27: Consider adding a code comment or a separate constant `SPEND_LY_CLOSED = True` to programmatically mark the old ledger as closed, rather than relying on a comment. [P3]
    *   `tests/package/test_ruling_102.py` line 49: Test name could be more specific to Batch 3. [P3]

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The inclusion of the `assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)` assertion in the test is the highest-leverage change, as it enforces the core safety invariant (headroom for one build) against future constant drift, ensuring the "never start a build that ends over the cap" rule remains mathematically sound even if the specific dollar amounts change.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements RULING 108:
1.  **Ledger Path:** `SPEND_B3.json` is used, and the test pins this. The old `SPEND_LY.json` is not written by the build path.
2.  **Stop/Limit Consistency:** Stop at $4.00, Limit at $4.50. Max build cost $0.50. A build starting at $3.99 ends at $4.49 (under cap). A build starting at $4.00 is refused. This is fail-closed and consistent.
3.  **Test Pinning:** The test pins the constants, the basis ("reported"), the headroom invariant, and the ledger path. The Cycle 1 P2 findings are already addressed in the provided diff.

P1_OR_WORSE: 0