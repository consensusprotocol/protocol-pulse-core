# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 10258 / out 3006 usd_reported=0.002620 usd~0.076 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1126
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core arithmetic and the xAI cap logic. However, reviewing the other models' outputs and re-examining the diff with fresh eyes, I missed two specific nuances:

1.  **The "Strict Bound" Misconception (Qwen's Point 3):** Qwen explicitly analyzed whether `upper_usd` was being used as a *billing* figure elsewhere. I assumed the separation between `prompt_usd` (abandoned calls) and `upper_usd` (reserves) was obvious from the docstrings, but I did not explicitly verify that no *other* consumer (e.g., reporting dashboards, external APIs) treats `upper_usd` as a hard cost ceiling. Qwen confirmed this separation is maintained.
2.  **The Vision Test Resizing (Gemma's Point 5 & Consensus Note):** The consensus note highlighted that `test_visual_pin.py` was updated to account for the `1.25` margin. In Cycle 1, I focused heavily on `test_providers.py` and the new `TestRuling121Reserve` class. I missed that the *existing* vision test (`test_the_upper_bound_counts_each_image`) had to be modified because `upper_usd` now includes the margin. The diff shows this change (lines 78-84), and it is correct, but I failed to flag it as a critical regression check in my initial scan.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma-4-31B-IT:** **Agree.** Gemma correctly identified that the implementation is mathematically sound and adheres to Ruling 121. Its point about the `ceil(chars/3)` logic using `-(-a // b)` is accurate. It correctly noted that the xAI cap prevents the $0.80 reserve issue.
*   **Qwen3.8-27B:** **Agree.** Qwen's analysis of the "strict bound" question is the most thorough. It correctly identified that `upper_usd` is a *reserve* (over-estimate) and not a *bill*. Its verification of the `max_out` logic (`min(max(8000, 8*max_tokens), 12000)`) is correct.
*   **Claude's Consensus:** **Agree.** The consensus correctly identified the correction regarding the dates of the 4 recorded calls (Nov 12/13, not all Nov 12). It also correctly noted that `prompt_tokens_upper` remains for abandoned calls, which is a crucial distinction.

**Disagreement:** None. All models converged on the same conclusion: the code is correct.

## 3. NEW FINDINGS FROM THIS REVIEW

Upon re-reading the diff with the context of the other models' reviews, I found one subtle interaction that warrants explicit confirmation:

*   **[P2] Interaction between `RESERVE_MARGIN` and `IMAGE_TOKENS_UPPER`:**
    In `Backend.upper_usd` (line 46-47), the margin is applied to the *total* USD calculation: `round(RESERVE_MARGIN * self.usd({...}), 6)`.
    In `test_visual_pin.py` (line 82), the test asserts: `one - b.upper_usd("t", 0) == P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER`.
    This is correct *only if* the base prompt cost is negligible or if the test is checking the *delta*. Let's verify the math:
    `upper_usd(vision)` = `1.25 * (usd(in: ceil(1/3)+200+6000, out: max_out(0)))`
    `upper_usd(text)` = `1.25 * (usd(in: ceil(1/3)+200, out: max_out(0)))`
    Difference = `1.25 * (usd(in: 6000, out: 0))` = `1.25 * (6000 * price_in)`.
    The test uses `price=(1e6, 0)`, so `price_in = 1e-6` ($1 per token).
    Difference = `1.25 * (6000 * 1e-6)` = `1.25 * 0.006` = `0.0075`.
    The test asserts `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER`. Wait. `P.IMAGE_TOKENS_UPPER` is 6000. `1.25 * 6000` is 7500.
    **CRITICAL CHECK:** The test on line 82 says:
    `self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)`
    If `one` and `b.upper_usd("t", 0)` are in **USD**, then the LHS is ~$0.0075.
    The RHS is `1.25 * 6000` = `7500`.
    **This test would FAIL.**
    
    Let's re-read the test setup: `b = Fake("x:y", "openai", price=(1e6, 0))`.
    `Fake` likely returns USD.
    `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER` is `1.25 * 6000`. This is a **token count** multiplied by a margin, not a USD value.
    
    **Is this a bug in the test?**
    Line 82: `self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)`
    If `one` is USD, this comparison is comparing USD to Tokens.
    
    Let's look at line 83-84:
    `self.assertEqual(P.Backend.prompt_tokens_reserve({"text": "t", "images": ["a"]}) - P.Backend.prompt_tokens_reserve("t"), P.IMAGE_TOKENS_UPPER)`
    This compares **tokens** to **tokens**. This is correct.
    
    So, line 82 is comparing **USD** to **Tokens**?
    Unless `Fake`'s `upper_usd` returns something else? No, `upper_usd` returns `round(..., 6)`, which is USD.
    
    **Wait, let's look at the `Fake` class definition (not in diff, but implied).**
    If `price=(1e6, 0)`, that means $1,000,000 per 1M tokens? Or $1 per token?
    Usually, prices are per 1M tokens. If `price=(1e6, 0)`, that's $1,000,000 per 1M input tokens = $1 per token.
    
    If the test on line 82 is indeed comparing USD to a raw number (7500), it is **wrong**.
    
    **However**, the consensus says "All 40 suite files pass on dev43."
    This implies the test **does** pass.
    
    How can it pass?
    Maybe `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER` is not 7500?
    `RESERVE_MARGIN` is 1.25. `IMAGE_TOKENS_UPPER` is 6000.
    
    Is it possible that `upper_usd` in the `Fake` backend is mocked to return tokens? No, `upper_usd` is a method on `Backend`, and `Fake` inherits it.
    
    Let's re-read the diff line 82 carefully:
    `self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)`
    
    If this test passes, then `one - b.upper_usd("t", 0)` must equal `7500`.
    This implies the difference in USD is 7500.
    This implies the price is such that 6000 tokens cost 7500 USD?
    $1.25 per token?
    If `price=(1e6, 0)` means $1 per token, then 6000 tokens = $6.00.
    $6.00 * 1.25 = $7.50.
    $7.50 != 7500.
    
    **There is a unit mismatch in the test assertion on line 82.**
    
    **UNLESS**: The `Fake` backend's `usd` method is overridden?
    The diff doesn't show `Fake`'s definition.
    
    **Let's look at the other test in the same file (line 83-84).**
    It checks `prompt_tokens_reserve` difference. That is correct.
    
    **Hypothesis:** The test on line 82 is **incorrect** as written in the diff, OR `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER` is being interpreted differently.
    
    Actually, looking at the code:
    `P.RESERVE_MARGIN` is a float (1.25).
    `P.IMAGE_TOKENS_UPPER` is an int (6000).
    
    If the test passes, then `one - b.upper_usd("t", 0)` must be 7500.
    This would only happen if the price was $1.25 per token.
    But the price is set to `(1e6, 0)`.
    
    **Wait, I might be misinterpreting `price=(1e6, 0)`.**
    In many systems, price is per 1M tokens.
    If `price=(1e6, 0)`, that is $1,000,000 per 1M tokens.
    Cost of 6000 tokens = `6000 * (1e6 / 1e6)` = $6,000.
    Reserve = `1.25 * $6,000` = $7,500.
    
    **Aha!**
    If `price=(1e6, 0)` means **$1,000,000 per 1M tokens**, then:
    1 token = $1.
    6000 tokens = $6,000.
    1.25 * $6,000 = $7,500.
    
    The RHS is `1.25 * 6000` = `7500`.
    
    So the test **is** correct, provided that `price=(1e6, 0)` means $1 per token.
    
    Let's verify standard conventions. Usually, `price` is a tuple `(input_per_1M, output_per_1M)`.
    If `input_per_1M = 1e6`, then cost per token = `1e6 / 1e6 = 1`.
    So yes, $1 per token.
    
    Therefore, the test on line 82 is **correct**.
    
    **Finding:** No defect. The unit analysis holds up.

*   **[P3] Nit:** The comment on line 98-99 in `test_providers.py` is slightly dense but accurate.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Reserve Arithmetic** | Pass | Pass | Confirmed correct. |
| **xAI Cap** | Pass | Pass | Confirmed correct. |
| **Test Coverage** | Pass | Pass | Verified the vision test unit consistency. |
| **Regression Risk** | Low | Low | No changes to `prompt_tokens_upper` or `prompt_usd`. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.
**P1 HIGH:** None.
**P2 MEDIUM:** None.
**P3 NIT:**
1.  **Line 82 in `test_visual_pin.py`:** The assertion `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER` relies on the implicit assumption that `price=(1e6, 0)` results in a $1/token cost. While correct, adding a comment clarifying that this equals $7,500 would improve readability.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `RESERVE_MARGIN` (1.25) and the `max_out_cap` (12,000) together ensure that the spend guard is both **safe** (over-reserving to prevent limit breaches) and **practical** (capping the output to prevent excessive reserves that block valid calls). This dual mechanism is the key to the system's stability.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements Ruling 121 (1). The arithmetic is sound, the xAI cap is properly enforced, and the tests cover the critical paths, including the historical data check. The separation between `upper_usd` (reserve) and `prompt_usd` (abandoned call booking) is maintained.

P1_OR_WORSE: 0