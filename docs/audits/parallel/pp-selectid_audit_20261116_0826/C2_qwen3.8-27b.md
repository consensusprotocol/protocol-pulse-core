# qwen3.8-27b (qwen/qwen3.8-27b) 80 s finish=stop usage in 10968 / out 2933 usd_reported=0.003667 usd~0.077 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0826
# Reviewer: [Model Name] (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the removal of `glm-5.3-flash` from the 16 lists and the general compliance with RULING 119. However, I missed a specific **test logic inconsistency** in `test_ledger_build.py` regarding the "Grok Down" scenario.

Specifically, in the test `test_ruling_96s_lists_and_xai_answering_nothing`, the Cycle 1 code (and the diff) asserts that when Grok is down and DeepSeek is the writer (skipped), the `exclusion_verdict` and `coherence_verdict:coherence` should return `None` (fail closed).

Gemma and Qwen both noted this, but I failed to explicitly verify if the *test assertions* in the diff actually match the *new chain definitions*.
- **New Chain `exclusion_verdict` (heimdall_first):** `[DeepSeek, Grok]`.
- **Scenario:** Grok is down. DeepSeek is the writer (skipped by L-x).
- **Result:** No legs available. Returns `None`.
- **Test Assertion (Line 202):** `("exclusion_verdict", None): None`.
- **My Cycle 1 Oversight:** I assumed the tests were updated correctly because the JSON was correct, but I did not trace the *router logic* against the *new shortened lists* to confirm that the `None` assertions were still valid. They are valid, but it was a close call. If `Qwen` had been added to `exclusion_verdict` (which it wasn't, but hypothetically), the test would have failed. The fact that `Qwen` is *not* in `exclusion_verdict` (per Ruling 96/06:12) is what makes the `None` assertion correct. I missed explicitly verifying that `Qwen` is *absent* from `exclusion_verdict` in the new config, which is why the fail-closed behavior holds.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma-4-31B-IT:**
    *   **Agree:** "glm removed from all 16 lists." Verified.
    *   **Agree:** "Qwen remains absent from all `context_verdict:step_a` lists." Verified.
    *   **Agree:** "The 'Grok down' scenario... correctly identifies that `exclusion_verdict`... now fail closed." Verified.
    *   **Disagree (Minor):** Gemma stated "P1_OR_WORSE: 0". I agree with the count, but I want to highlight a P3 nit regarding the trailing comma in the JSON note, which Gemma also noted but dismissed.

*   **Qwen3.8-27B:**
    *   **Agree:** "16 distinct lists... removed." Verified.
    *   **Agree:** "Qwen is struck from Step A." Verified.
    *   **Agree:** "Hook is Grok alone." Verified.
    *   **Disagree (Minor):** Qwen's analysis of the diff lines was slightly messy ("Let's trace carefully"), but the conclusion was correct. I agree with the final state of the lists.

*   **Claude's Consensus:**
    *   **Agree:** "No P1."
    *   **Agree:** "P3 noted... trailing comma."

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] Nit: Trailing Comma in JSON Note**
In `pipeline/model_providers.json`, line 129 (in the diff), the `ruling_102` string ends with a comma:
```json
"ruling_102": "...retried next build.",
"ruling_119": "..."
```
This is valid JSON. However, in the *previous* version (implied by the diff context), `ruling_102` was the last key in the `notes` object (or similar structure) and likely did *not* have a trailing comma. The diff adds `ruling_119` after it. This is syntactically correct. No issue.

**[P2] Potential Ambiguity in "Next Healthy Member" Logic**
RULING 119 states: "the next healthy member takes its place."
The implementation simply *removes* GLM from the list. It does not *promote* the next member to the *front* of the list; it just closes the gap.
- **Old `step_a_first`:** `[GLM, DeepSeek, Grok]`
- **New `step_a_first`:** `[DeepSeek, Grok]`
This is the correct interpretation of "closes up." The "next healthy member" (DeepSeek) is now first.
However, consider `fidelity_verdict`:
- **Old:** `[GLM, Qwen, Grok]`
- **New:** `[Qwen, Grok]`
Qwen is now first. Is Qwen "healthy"? Ruling 06:12 struck Qwen from *Step A* due to errors/refusals. It did *not* strike Qwen from *Fidelity*. Ruling 96 explicitly ordered `FIDELITY glm -> qwen -> Grok`. So Qwen is the intended next member. This is correct.

**[P1] CRITICAL CHECK: Did we break the "Writer's Family" Skip Logic?**
The prompt states: "deepseek is the writer's family (skipped by L-x)".
In the test `test_ruling_96s_lists_and_xai_answering_nothing`:
- `w` is the writer.
- `w.vendor` and `w.family` are passed to `self.pick`.
- The test asserts `("exclusion_verdict", None): None`.
- This implies that when DeepSeek (writer) is skipped, and Grok is down, there are *no other* models in `exclusion_verdict`.
- **New `exclusion_verdict` (heimdall_first):** `[DeepSeek, Grok]`.
- If DeepSeek is skipped, and Grok is down, the list is exhausted. `None` is returned.
- **Is this a defect?** No, it is the intended "fail closed" behavior.
- **However**, look at `fidelity_verdict`:
    - **New `fidelity_verdict`:** `[Qwen, Grok]`.
    - Test asserts `("fidelity_verdict", None): Q`.
    - If DeepSeek is the writer, is Qwen skipped? No, Qwen is a different family.
    - So Qwen is picked. This is correct.

**[P2] Test Coverage Gap: `today` Routing**
The test `test_ruling_96s_lists_and_xai_answering_nothing` checks `today` routing for `coherence_verdict:coherence` and `context_verdict:step_c`.
- **New `today` `step_c`:** `[Grok, DeepSeek]` (GLM removed).
- **Test Assertion (Line 190):** `today["context_verdict:step_c"] == [X, DS]`.
- This is correct.
- But does the test verify that `today`'s `exclusion_verdict` or `fidelity_verdict` are also updated?
- The diff shows changes to `today`'s `context_verdict` (lines 13-20 in diff, which correspond to `today` routing in the JSON).
- The test `test_ruling_82_the_context_verdict_chain` checks `PL.chains()["context_verdict"]` (default) and `PL.chains("today")`?
- Line 148: `PL.chains()["context_verdict"]` is checked.
- Line 179: `assertNotIn(G, [b for v in list(ch.values()) + list(PL.chains("today").values()) for b in v])`.
- This line checks that GLM is NOT in *any* list in `heimdall_first` OR `today`. This is a strong check. It covers all lists.

**[P1] POTENTIAL ISSUE: `local_judge:gemma3:27b` vs `local:gemma3:27b`**
In the diff, line 96: `"local_judge:gemma3:27b"`.
In the diff, line 11: `"local:gemma3:27b"`.
Are these the same backend?
- Line 11 is in the default `context_verdict` list.
- Line 96 is in `heimdall_first.context_verdict:step_a_second`.
- The test at line 176 asserts `ch["context_verdict:step_a_second"]` contains `"local_judge:gemma3:27b"`.
- The test at line 148 asserts `PL.chains()["context_verdict"]` contains `"local:gemma3:27b"`.
- This suggests there are two different backends or aliases.
- **Check:** Does `local_judge:gemma3:27b` exist in `model_providers.json`?
- The diff does not show the `backends` definition for `local_judge`.
- If `local_judge:gemma3:27b` is not defined, the router will fail to resolve it.
- **However**, this was likely present before the change (Ruling 102 mentions "local gemma3:27b... through the integrator's judge service").
- The diff does *not* modify the `backends` section, only the `chains`.
- So, if it worked before, it works now.
- **But**, did the removal of GLM change the *order* such that `local_judge` is now reached in a scenario where it wasn't before?
- In `step_a_second`, GLM was 3rd. Now it's gone.
- Old: `[Grok, DeepSeek, GLM, Gemini, LocalJudge]`.
- New: `[Grok, DeepSeek, Gemini, LocalJudge]`.
- If Grok, DeepSeek, and Gemini are all down, LocalJudge is now the 4th choice instead of 5th.
- This is the intended "closes up" behavior.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Config Integrity | 9/10 | 10/10 | Verified all 16 lists. No GLM. No additions. |
| Test Accuracy | 8/10 | 9/10 | Verified test assertions match new chains. The `assertNotIn` check for GLM in all lists is robust. |
| Ruling Compliance | 9/10 | 10/10 | 06:12, 96, 102, 115 all respected. |
| Fail-Closed Logic | 8/10 | 9/10 | Verified that removing GLM leads to `None` (fail closed) in the specific "Grok Down + DeepSeek Writer" scenario. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **[P2] Verify `local_judge:gemma3:27b` Backend Definition:** Ensure that `local_judge:gemma3:27b` is defined in the `backends` section of `model_providers.json`. The diff only shows chain changes. If this backend was added recently and not defined, the `step_a_second` chain will fail to resolve the last leg. *Action:* Check `model_providers.json` `backends` key. (Likely already defined, but worth a 5-second check).

**P3 NIT:**
1.  **[P3] Trailing Comma:** The JSON is valid. No action needed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the `assertNotIn(G, ...)` check in `test_ruling_96s_lists_and_xai_answering_nothing` (Line 179) is the highest-leverage change. It ensures that GLM is not accidentally left in *any* list in *any* routing, preventing future regressions where a new list might be added with GLM by mistake.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  Confirm that `local_judge:gemma3:27b` is a valid backend key in `model_providers.json` (P2 check).
2.  Run the full test suite to ensure no other tests depend on GLM being present in the chains (e.g., integration tests that mock GLM responses).

P1_OR_WORSE: 0