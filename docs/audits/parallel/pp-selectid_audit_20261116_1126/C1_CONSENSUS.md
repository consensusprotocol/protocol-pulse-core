# C1 CONSENSUS — pp-selectid audit 20261116_1126 (RULING 121 (1): the reserve and the xAI output cap)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo cut off at 32,000
tokens, no answer). P1_OR_WORSE: qwen 0, gemma 0. Cycle 1 $0.0077 of Heimdall, not capped.

qwen's headings tagged [P0]/[P1] are checks it states and answers itself, each "Correct", with its count at 0:
- Router.call takes every paid call's reserve from upper_usd: yes, providers.py:1366 (unchanged): "upper =
  b.upper_usd(prompt, max_tokens, system)", then _reserve; so the new reserve reaches every paid call.
- The cap reaches the request: XAIBackend.complete sends "max_tokens": self.max_out(max_tokens) (providers.py:475,
  unchanged); test_grok_is_sent_the_capped_output asserts 12,000 in the body sent.
- max_tokens 0 or negative: max(min_out 8000, ...) then min(cap): never under 8,000, never over 12,000.
P2s noted, not changed: prompt_tokens_reserve beside prompt_tokens_upper (the latter still books an abandoned call and
the reported-rate estimate, by design: an abandoned call is never under-booked); the constant's comment.

ADDED AFTER CYCLE 1 (in cycle 2's diff): tests/package/test_visual_pin.py's ruling-70 test "the upper bound counts each
image" asserted the reserve grows by exactly IMAGE_TOKENS_UPPER per image; with ruling 121's x 1.25 it grows by 1.25 x
6,000 (each image is still 6,000 tokens: asserted directly on prompt_tokens_reserve). Re-sized like the three guard
tests in test_providers. All 40 suite files pass on dev43. Mutations R1-R7 after a control run: 7 of 7 killed.
A CORRECTION OF MY STATE LINE (the question is right): the 4 recorded calls with over 12,000 output tokens were one on Nov 12 and three on Nov 13
(none since), as the question says; my STATE line of 11:21 wrongly said "all Nov 12". The test asserts it (4, all before Nov 14).
