# gemma-4-31b-it (google/gemma-4-31b-it) 132 s finish=stop usage in 13317 / out 2702 usd_reported=0.000748 usd~0.080 (upper-bound price)

# PROTOCOL PULSE — CYCLE 3 CODE AUDIT
# Feature: pp-selectid-20261116_1126

## 1. WHAT DID THEY CATCH THAT I MISSED?
The Cycle 2 landing report identified a real defect in `tests/providers/test_reserve_wait.py`. The constant `U` was hardcoded to the pre-Ruling 121 bound ($0.10201). Because the new reserve logic applies a `RESERVE_MARGIN` of 1.25, the actual reserve became $0.12751, causing the "room" calculations in the concurrency tests to fail. I missed this because I focused on the new logic in `providers.py` and the new `TestRuling121Reserve` class, rather than the side effects on existing concurrency tests.

## 2. WHERE DO I AGREE OR DISAGREE?
*   **Qwen's P2 (USD vs Tokens in `test_visual_pin.py`):** I **disagree** that this is a bug. Qwen noted that line 82 compares USD to Tokens. However, the `Fake` backend is initialized with `price=(1e6, 0)`, which in the context of the `Fake` class means $1.00 per token. Therefore, the USD value is numerically identical to the token count. The assertion `one - b.upper_usd("t", 0) == 1.25 * 6000` is mathematically correct given the mock price.
*   **Mimo's P3 (Naming Confusion):** I **agree**. `prompt_tokens_upper` (used for abandoned calls) and `prompt_tokens_reserve` (used for the spend guard) are very similar. While not a bug, a comment distinguishing them would prevent future developer error.
*   **Gemma's Arithmetic:** I **agree**. The use of `-(-a // b)` for ceiling division is the correct Pythonic implementation of the ruling.

## 3. NEW FINDINGS FROM THIS REVIEW
The fix for `test_reserve_wait.py` (lines 231–233) is the correct architectural approach. By replacing the hardcoded float with `Fake("openai:u", "openai").upper_usd("p", 1000)`, the test now dynamically tracks the reserve logic. If the margin or the character-to-token divisor changes again, this test will not break.

## 4. REVISED SCORES
| Subsystem | Cycle 1 | Cycle 2 | Cycle 3 | Why changed |
| :--- | :--- | :--- | :--- | :--- |
| Reserve Logic | 10/10 | 10/10 | 10/10 | Implementation is mathematically precise. |
| xAI Cap | 10/10 | 10/10 | 10/10 | Cap is correctly applied in `max_out` and verified in tests. |
| Regression/Tests | 10/10 | 9/10 | 10/10 | Cycle 2 landing found a failure in `test_reserve_wait.py`; now fixed. |

## 5. FINAL PRIORITY LIST
No P0, P1, or P2 findings remain.

**[P3]** `pipeline/providers.py:201`: Add a comment to `prompt_tokens_upper` explicitly stating it is for abandoned call booking and NOT the spend guard reserve to avoid confusion with `prompt_tokens_reserve`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The implementation of `XAIBackend.max_out` capping at 12,000 tokens prevents the $8\times$ reasoning multiplier from creating reserves that would block almost all calls within a $1.00 daily budget.

## 7. PRODUCTION READY?
Yes.

P1_OR_WORSE: 0