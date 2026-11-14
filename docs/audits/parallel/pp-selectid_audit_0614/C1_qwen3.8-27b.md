# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 8910 / out 3203 usd~0.075 (upper-bound price)

To audit the configuration change in `pipeline/model_providers.json` and `tests/package/test_ledger_build.py`, I will verify the changes against the Orchestrator's Rulings (06:12 ET Nov 14) and the governing laws (specifically L-l: Fail Closed, and the specific routing constraints).

### Analysis

**1. Verification of Ruling (1): The Coherence Gap**
*   **Ruling:** "glm IS coherence's last fallback, after Grok... Clips-alone has NO Heimdall fallback... with Grok down it goes to Plan B's other outside family... else fails closed."
*   **Diff (`coherence_verdict:coherence`):** Changed from `[Grok, Deepseek]` to `[Grok, Deepseek, Glm]`.
    *   *Check:* Does this match "glm last, after Grok"? The ruling says "after Grok". It does not explicitly say "replace Deepseek". Ruling 96 established Deepseek as the second choice. The 06:12 ruling addresses the *gap* (no family left if Grok and Deepseek fail/are writers). Adding Glm as the *last* fallback preserves the Ruling 96 order while closing the gap.
    *   *Scenario:* If Grok is down and Deepseek wrote the text (so it is skipped due to L-x/vendor conflict), the router moves to Glm. If Glm is also down or fails, the list is spent -> Fail Closed. This matches the ruling.
*   **Diff (`coherence_verdict:clips_alone`):** Changed from `[Grok, Qwen, Deepseek]` to `[Grok, Gemini]`.
    *   *Check:* "NO Heimdall fallback". Qwen and Deepseek are Heimdall. They are removed.
    *   *Check:* "Plan B's other outside family". The background states Plan B's coherence list is `Grok -> Gemini -> OpenAI -> Anthropic`. Under `heimdall_first`, OpenAI/Anthropic are frozen legs (dropped by `proof_ly.chains()`). Therefore, the only available "outside family" after Grok is Gemini.
    *   *Result:* `[Grok, Gemini]` is the correct implementation.

**2. Verification of Ruling (2): Qwen Struck from Step A**
*   **Ruling:** "QWEN ON STEP A: STRUCK... qwen... is out of step A entirely."
*   **Diff (`context_verdict:step_a_first`):** Changed from `[Glm, Deepseek, Qwen, Grok]` to `[Glm, Deepseek, Grok]`.
    *   *Result:* Qwen removed. Correct.
*   **Diff (`context_verdict:step_a_second`):** Changed from `[Grok, Qwen, Glm, Deepseek]` to `[Grok, Glm, Deepseek]`.
    *   *Result:* Qwen removed. Correct.
*   **Diff (`context_verdict` default):** Changed from `[Glm, Deepseek, Qwen, Grok]` (implied by context of removal) to `[Glm, Deepseek, Grok]`.
    *   *Result:* Qwen removed. Correct.
*   **Test Verification:** `test_ledger_build.py` line 89 asserts `assertNotIn(Q, ...)` for all `context_verdict:step_a*` keys. This confirms no Qwen remains on any Step A path.

**3. Attack (a): Is "glm last, after Grok" right as Grok -> deepseek -> glm?**
*   The ruling says "glm IS coherence's last fallback, after Grok".
*   Ruling 96 (previous) set `coherence` to `Grok -> Deepseek`.
*   The 06:12 ruling identifies a *gap* where coherence had no family if Grok and Deepseek were unavailable/conflicted.
*   By appending Glm to the end (`Grok -> Deepseek -> Glm`), we maintain the Ruling 96 priority (Grok first, Deepseek second) while satisfying the 06:12 requirement that Glm is the *last* fallback.
*   If Glm were to *replace* Deepseek, it would violate Ruling 96's established order unless explicitly revoked, which it was not. The ruling specifically addresses the *exhaustion* of the list.
*   **Verdict:** The order `Grok -> Deepseek -> Glm` is correct.

**4. Attack (b): Is any qwen left on a step-A path?**
*   Checked `step_a_first`, `step_a_second`, and the default `context_verdict`.
*   All Qwen entries are removed.
*   **Verdict:** No Qwen remains.

**5. Attack (c): Clips-alone and other lists**
*   **Clips-alone:** `Grok -> Gemini`.
    *   Is Gemini the right reading? Yes, it is the next non-frozen, non-Heimdall model in the Plan B coherence chain.
    *   Does anything else need the change?
        *   `coherence_verdict` (default): The diff does *not* show a change to the default `coherence_verdict` list in the JSON block provided (lines 34-39 only show `clips_alone` and `coherence` kinds).
        *   *Wait, let's look closer at the diff.*
        *   Lines 34-39:
            ```json
            "coherence_verdict:clips_alone": [
             "xai:grok-4.20-0309-reasoning",
            -    "heimdall:qwen/qwen3.8-27b",
            -    "heimdall:deepseek/deepseek-v4.1-flash"
            +    "google:gemini-2.5-pro"
            ],
            "coherence_verdict:coherence": [
             "xai:grok-4.20-0309-reasoning",
            -    "heimdall:deepseek/deepseek-v4.1-flash"
            +    "heimdall:deepseek/deepseek-v4.1-flash",
            +    "heimdall:z-ai/glm-5.3-flash"
            ]
            ```
        *   The default `coherence_verdict` (used by spotlight/medley value verdicts) is **not** modified in this diff.
        *   The prompt states: "The value verdicts are deliberately left on the default list (Grok -> deepseek): no replay data."
        *   However, the 06:12 ruling (1) says: "glm IS coherence's last fallback...". It does not explicitly limit this to the `coherence` kind. It refers to "The Coherence Gap".
        *   If the default `coherence_verdict` list is still `Grok -> Deepseek`, and Deepseek wrote the text, and Grok is down, the default list fails closed.
        *   Does the ruling apply to the default? The ruling mentions "clips-alone" specifically for the Gemini change. For the Glm change, it says "glm IS coherence's last fallback".
        *   *Crucial Detail:* The test `test_ledger_build.py` line 98 checks:
            `self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))`
            This line checks the `today` routing (which might be different from `heimdall_first` or might reflect the default).
            But line 95 checks `heimdall_first`'s `coherence_verdict:coherence` is `[X, DS, G]`.
            The test does **not** assert that the default `coherence_verdict` (without kind) includes Glm.
        *   *Risk:* If the "Coherence Gap" ruling applies to *all* coherence verdicts, the default list is missing the Glm fallback. If it only applies to the specific `coherence` kind (which seems likely given the specific mention of "clips-alone" and the gap analysis usually targeting specific failing paths), then it's fine.
        *   *Re-reading Ruling 96:* "STEP C, CLIPS-ALONE, COHERENCE... Grok first."
        *   *Re-reading 06:12:* "(1) THE COHERENCE GAP: glm IS coherence's last fallback... Clips-alone has NO Heimdall fallback..."
        *   The term "coherence" in the ruling likely refers to the verdict type `coherence_verdict`. The `coherence` *kind* is one instance. The default is another.
        *   If the default `coherence_verdict` is used for "value verdicts" (as stated in the prompt), and those value verdicts suffer from the same "gap" (Grok down, Deepseek writer), they will fail closed.
        *   *However*, the prompt says: "The value verdicts are deliberately left on the default list... no replay data." This implies the orchestrator *decided* not to change the default list because there is no data proving the gap exists for those specific verdicts, or they are lower risk.
        *   *Conclusion:* The diff matches the *explicit* instructions for `clips_alone` and `coherence` kinds. The exclusion of the default list is a deliberate choice documented in the prompt ("deliberately left"). I will flag this as a potential inconsistency if the "Gap" is systemic, but based on the "no replay data" note, it is likely intentional.

**6. Attack (d): Can the change make a verdict LOOSER?**
*   **Looser** means a weaker model decides where a stronger one did, or a model that should be skipped is now used.
*   **Step A:** Qwen (weak/error-prone) is removed. This makes it **stricter** (fewer bad models).
*   **Coherence (kind):** Glm is added *last*. It only decides if Grok and Deepseek are unavailable/conflicted. This does not make it looser; it prevents a "Fail Closed" in a scenario where a verdict *could* be obtained from a trusted (though last-resort) model. It does not replace a stronger model.
*   **Clips-Alone:** Qwen and Deepseek (Heimdall) are removed. Gemini (Outside) is added.
    *   Ruling 96 said Clips-Alone was `Grok -> Qwen -> Deepseek`.
    *   06:12 says "NO Heimdall fallback".
    *   Is Gemini "weaker" than Qwen/Deepseek? The ruling explicitly bans Heimdall for this path due to low agreement (52-62%). It mandates an "outside family". Gemini is the designated outside family.
    *   This change is **compliant** with the ruling. It is not "looser" in the sense of violating the hierarchy; it is a *different* hierarchy mandated by the orchestrator to avoid Heimdall bias/errors.

### Findings

<critical>
None. The changes strictly implement the 06:12 rulings.

<high>
**File:** `pipeline/model_providers.json`
**Line:** 34-39 (Context: `coherence_verdict` default)
**Issue:** The ruling states "glm IS coherence's last fallback". The diff applies this only to `coherence_verdict:coherence` and `coherence_verdict:clips_alone`. The default `coherence_verdict` list (used for value verdicts) remains `Grok -> Deepseek` (implied, as it is not changed).
**Scenario:** If a "value verdict" coherence check runs, and Grok is down, and Deepseek wrote the text, the router will fail closed. If the "Coherence Gap" ruling is intended to apply to *all* coherence verdicts, this is a violation.
**Mitigation:** The prompt explicitly states: "The value verdicts are deliberately left on the default list... no replay data." This suggests the orchestrator intentionally excluded the default list from the Glm fallback addition. **However**, if the "Gap" is a systemic property of the `coherence_verdict` type, this is a risk. Given the explicit "deliberately left" note, this is likely **Intentional**, but worth confirming with the orchestrator if "Coherence" in the ruling implies the *type* or the *kind*.

<medium>
**File:** `tests/package/test_ledger_build.py`
**Line:** 98
**Issue:** The test asserts `today["coherence_verdict:coherence"]` is `[X, DS]` (Grok, Deepseek).
**Scenario:** The `today` routing might be different from `heimdall_first`. If `today` is the active routing for some builds, and it lacks the Glm fallback, it might not comply with the 06:12 ruling if that ruling applies to all routings.
**Mitigation:** The prompt says "Under routing 'heimdall_first' (the routing every build uses)". The test checks `heimdall_first` at line 95 (`ch["coherence_verdict:coherence"]` is `[X, DS, G]`). The `today` check at line 98 is likely a regression check for a different, perhaps legacy or specific, routing profile. Since `heimdall_first` is the primary build routing, the compliance is met there.

### SHIP: yes

**Conditions:**
1.  Confirm that the "Coherence Gap" ruling (06:12) applies specifically to the `coherence` and `clips_alone` kinds, and *not* the default `coherence_verdict` list, consistent with the "deliberately left" note in the prompt.
2.  Ensure `google:gemini-2.5-pro` is correctly configured in the `plan_b` section of `model_providers.json` (not shown in diff, but implied by "Plan B's other outside family") so that the router can actually resolve the backend. If `gemini` is not in `plan_b` or `backends`, the router will fail to instantiate it, leading to an unexpected Fail Closed (which is safe, but might not be the intended "Gemini fallback" behavior). *Assuming standard config, this is likely fine.*