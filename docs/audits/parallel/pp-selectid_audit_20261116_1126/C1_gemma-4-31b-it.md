# gemma-4-31b-it (google/gemma-4-31b-it) 204 s finish=stop usage in 11322 / out 3102 usd_reported=0.000736 usd~0.080 (upper-bound price)

The code implements RULING 121 (1) exactly as specified. The spend guard's reserve logic has been shifted from a 1:1 character-to-token ratio to a `chars / 3` ratio (rounded up), incorporating a 1.25x margin and a strict output cap for the xAI reasoning model to ensure calls fit within the $1.00 daily limit.

### Analysis

1.  **Reserve Arithmetic**: `Backend.prompt_tokens_reserve` correctly implements the `ceil(chars / 3)` logic using the Python integer division trick `-(-a // b)`. It correctly handles both vision and text prompts, adding the 200-token frame and 6,000 tokens per image.
2.  **Spend Guard Integration**: `Backend.upper_usd` now uses this reserve and the `max_out` value, multiplied by `RESERVE_MARGIN` (1.25), and rounded to 6 decimal places. This value is passed to `Router._reserve`, ensuring the reservation is taken before the call is executed.
3.  **xAI Output Cap**: `XAIBackend.max_out` now respects the `max_out_cap` (12,000) defined in `model_providers.json`. This prevents the reasoning model's $8\times$ multiplier from reserving excessive funds (e.g., 32,000 tokens for a 4,000-token request), which previously blocked calls from running within a $1.00 budget.
4.  **Verification against History**: `TestRuling121Reserve.test_no_recorded_grok_step_a_call_cost_more_than_its_reserve` explicitly validates the new reserve against the 438 recorded Grok calls, confirming the tightest margin is $\ge \$0.10$, as required by the ruling.
5.  **Regression Testing**: Existing `SpendLimit` tests in `test_providers.py` were correctly updated to reflect the new reserve calculations (e.g., increasing prompt lengths to trigger the same limits).
6.  **Fail-Closed Behavior**: The implementation maintains the `SpendLimit` exception, which ensures that if a reserve cannot be secured, the call is refused before execution (M12).

### Findings

No defects found. The implementation is mathematically correct and adheres to all governing laws and the specific requirements of Ruling 121.

P1_OR_WORSE: 0