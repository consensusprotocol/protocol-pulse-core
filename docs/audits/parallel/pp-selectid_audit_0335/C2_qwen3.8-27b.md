# qwen3.8-27b (qwen/qwen3.8-27b) 105 s finish=stop usage in 5565 / out 1652 usd~0.041 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0335

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the semantic shift from `R()` to `targets.append()`. The other models (specifically Qwen and the Consensus) correctly identified the **scope verification** of the `targets` variable as the primary risk. While I noted the change, I did not explicitly flag the dependency on `targets` being bound in the local scope prior to line 439 as a potential P0/P1 if the diff context was insufficient. The Consensus (K1) verified this via `eligibility.py:425`, confirming `targets = facts.setdefault("targets_missed", [])` exists. I missed explicitly calling out this verification step in my Cycle 1 output, relying instead on the test passing to imply correctness.

Additionally, GLM-5.3-FLASH correctly identified the **brittleness of the test assertion** (P1-1/P2-1). In Cycle 1, I may have viewed the test update as standard practice without noting that hard-coding the constant `3` in the expected string (even via f-string interpolation in the test, if not done carefully) or the specific wording creates a maintenance burden. The Cycle 2 diff shows the test *does* use `E.MAX_WINDOW_SENTENCES` in the f-string (line 37), which mitigates the constant duplication, but the string prefix `"4 sentences > ..."` still hard-codes the count `4`. This is acceptable for a specific fixture but worth noting.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (P2-1: `targets_missed` semantics):** **Agree.** The retired rule now shares the channel with live targets. The string explicitly says "retired by ruling 35," which is good for human readability, but programmatically, `targets_missed` is now a mixed bag of "live constraints" and "historical notes." Since the ruling states this is "information only" and nothing ranks on it, this is a P2 documentation/semantics issue, not a bug.
*   **GROK-4.20 (No P0/P1, SHIP: yes):** **Agree.** The change is minimal and correctly implements the ruling. The removal of `R("too_many_sentences")` and addition to `targets` is the exact intent.
*   **QWEN3.8-27B (P1: Unverified variable scope for `targets`):** **Partially Agree (Downgraded).** In Cycle 1, this was a valid concern because the diff didn't show the definition. However, the Consensus (K1) and the passing tests (which would crash if `targets` were undefined) verify that `targets` is in scope. Therefore, this is no longer a P1 risk for the *current* state of the code, but it was a valid audit point for the *diff* in isolation.
*   **Consensus (K3: Test brittleness):** **Agree.** The test now uses `E.MAX_WINDOW_SENTENCES` in the assertion string (line 37), which is the correct fix for the constant duplication. The new boundary test (line 39-40) for `n=3` (at the cap) is a valuable addition that was missing in Cycle 1.

## 3. NEW FINDINGS FROM THIS REVIEW

*   **P2-1: Test Fixture Hard-Coding (Line 37):** The test asserts `f"4 sentences > {E.MAX_WINDOW_SENTENCES} ..."`. The `4` is hard-coded. If the fixture `four` were ever changed to 5 sentences, the test would fail not because the logic is wrong, but because the string doesn't match. This is minor and standard for unit tests, but worth noting.
*   **P2-2: Boundary Test Coverage (Line 39-40):** The new test `three = E.eligible(E.Span(four, 0, 2), ...)` checks that a 3-sentence span (exactly at `MAX_WINDOW_SENTENCES`) does *not* record a T9 target. This is a critical negative test that was absent in Cycle 1. It confirms the `elif n > MAX_WINDOW_SENTENCES` logic is correct (strictly greater than). **This is a positive finding.**
*   **P2-3: String Length in `targets_missed`:** The new string is quite long: `"4 sentences > 3 (T9, retired by ruling 35: the 20 s clip limit and the per-source limit govern length)"`. If `targets_missed` is ever serialized to a database or log with a length limit, this could be an issue. However, given it's "information only" and likely for human review, this is low risk.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Logic Correctness** | 9/10 | 10/10 | Verified `targets` scope via Consensus/K1. Boundary test added. |
| **Test Coverage** | 7/10 | 9/10 | Added negative test for `n=3` (at cap). Still hard-codes `4` in string. |
| **Maintainability** | 8/10 | 8/10 | String is long and brittle, but uses constant for the limit. |
| **Compliance** | 9/10 | 10/10 | Fully aligns with Ruling 35. No other rules touched. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    *   `tests/eligibility/test_eligibility.py:37`: Hard-coded `4` in the expected string. Consider deriving the count from the fixture length if possible, or accept as minor brittleness.
    *   `pipeline/eligibility.py:440-441`: Long string in `targets_missed`. Ensure downstream consumers (e.g., `moments.py`) do not truncate or fail on long strings. (Likely safe, but verify).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the **boundary test for `n=3` (line 39-40)** is the highest-leverage change in this diff. It explicitly verifies that the retirement of T9 does not accidentally trigger at the limit, ensuring the `elif` logic is strictly `> MAX_WINDOW_SENTENCES` and not `>=`. This prevents a subtle regression where spans exactly at the cap would be incorrectly flagged.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  Confirm that `targets` is indeed bound in the local scope of `_span` prior to line 439 (verified by Consensus K1 and passing tests).
2.  Ensure that no downstream consumer of `facts["targets_missed"]` treats the new T9 string as a "live" rejection reason (verified by ruling: "information only").
3.  The test suite passes, including the new boundary assertion.

The change is minimal, compliant with Ruling 35, and correctly demotes the sentence count limit from a hard rejection to a recorded target. The addition of the boundary test strengthens the verification.