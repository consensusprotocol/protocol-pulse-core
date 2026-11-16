# gemma-4-31b-it (google/gemma-4-31b-it) 279 s finish=stop usage in 12500 / out 3338 usd_reported=0.000801 usd~0.088 (upper-bound price)

The code implements RULING 119 (3) by removing `heimdall:z-ai/glm-5.3-flash` from all decision chains in `model_providers.json` and updating the corresponding pinning tests in `test_ledger_build.py`.

### Analysis
1.  **Chain Removal**: I have verified that `heimdall:z-ai/glm-5.3-flash` was removed from all 16 lists in `model_providers.json`, including the default roles and the `heimdall_first` and `plan_b` routing lists.
2.  **Standing Rulings**:
    *   **RULING 06:12**: Qwen remains absent from all `context_verdict:step_a` lists.
    *   **RULING 115**: The `coherence_verdict:hook` remains exclusively `["xai:grok-4.20-0309-reasoning"]`.
    *   **RULING 96/102**: The remaining models shifted up to fill the gaps, maintaining the established priority order.
3.  **Test Verification**:
    *   `test_ruling_82_the_context_verdict_chain` correctly reflects the new `today` chain: `[X, DS, Q]`.
    *   `test_ruling_96s_lists_and_xai_answering_nothing` correctly validates the "closed up" lists.
    *   The "Grok down" scenario in the tests correctly identifies that `exclusion_verdict`, `context_verdict:step_c`, and `coherence_verdict:coherence` now fail closed (return `None`) because GLM (the last fallback) is gone and DeepSeek is skipped as the writer's family.
    *   The "Step A first screen" logic correctly identifies a `HOLD` state when DeepSeek is the writer and Grok is down/capped, as GLM is no longer available to provide a verdict.

The implementation is precise, follows the "fail closed" principle (M12), and adheres to all governing laws.

P1_OR_WORSE: 0