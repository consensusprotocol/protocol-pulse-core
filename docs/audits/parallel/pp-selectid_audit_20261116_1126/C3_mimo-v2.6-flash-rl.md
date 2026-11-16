# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 54 s finish=stop usage in 12382 / out 3728 usd_reported=0.000861 usd~0.093 (upper-bound price)

# PROTOCOL PULSE — CYCLE 3 CODE AUDIT
# Feature: pp-selectid-20261116_1126
# Reviewer: Cycle 3 — checking the fix of Cycle 2's real defect

---

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Gemma (Cycle 1):** Found zero defects, all 10/10. Correct — the core arithmetic and cap logic were sound. Nothing to add.

**Mimo (Cycle 1):** Two P3 nits I should have surfaced:
- **Shared ledger in `test_a_step_a_call_fits_what_the_day_has_left`** (test_providers.py:205–218): the two loop iterations share one `SPEND.json`, so after the first successful call the ledger gains ~$0.02, making the second iteration's spent $0.6035 rather than $0.5835. The test still passes for the right reason (reserve alone exceeds $1.00), but resetting the ledger between iterations would make intent unambiguous. I missed this.
- **Naming confusion between `prompt_tokens_upper` and `prompt_tokens_reserve`** (providers.py:201 vs 205): near-identical names serving different purposes (abandoned-call booking vs spend-guard reserve). A comment on `prompt_tokens_upper` saying "NOT the reserve" would help. I missed this.

**Qwen (Cycle 1):** Raised a potential P2 about the vision test comparing USD to tokens, then worked through the math and confirmed it checks out (price=(1e6, 0) means $1/token, so the USD delta equals the token delta × 1.25). The concern was valid to raise but resolved correctly — no defect.

**Claude's Consensus:** The critical catch — **`test_reserve_wait.U` was stale** ($0.10201, the pre-Ruling-121 bound), causing 4 tests to fail at landing. This was found *after* Cycle 2, at landing, and is the defect this Cycle 3 checks. All three Cycle 1 models missed it because the diff shown to them didn't include `test_reserve_wait.py` changes (the file wasn't modified in the original diff — it was only modified in the fix).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| Gemma: all correct, no defects | **Agree** | Core arithmetic, cap, and tests were sound. |
| Mimo: shared ledger P3 in step-A fit test | **Agree** | Test passes for the right reason, but resetting the ledger between iterations would be cleaner. Still P3. |
| Mimo: naming confusion P3 | **Agree** | `prompt_tokens_upper` vs `prompt_tokens_reserve` is a real readability hazard. Still P3. |
| Qwen: vision test USD-vs-tokens concern | **Agree (resolved)** | Math checks out; price=(1e6,0) makes the units consistent. No defect. |
| Claude: stale `U` in test_reserve_wait | **Agree — this was the real defect** | Found at landing, now fixed. |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

I verified the fix itself:

**The fix (test_reserve_wait.py:232–233):**
```python
U = Fake("openai:u", "openai").upper_usd("p", 1000)   # Fake's reserve for prompt "p" and max_tokens 1000: since
#   ruling 121 (1) 1.25 x $0.10201 = $0.12751 (it was the bare $0.10201)
```

- **Correctness:** `Fake("openai:u", "openai")` is an openai backend (not xai), so `max_out(1000)` returns the base value (not the xai cap path). `prompt_tokens_reserve("p")` = `ceil(1/3) + 200` = `1 + 200` = 201. The old formula gave `(1 + 200) * 10e-6 + 1000 * 100e-6` = $0.10201. The new reserve is `1.25 × (201 × 10e-6 + 1000 × 100e-6)` = `1.25 × 0.10201` = $0.1275125 ≈ $0.12751. ✓
- **Architectural quality:** Deriving `U` from the code rather than hardcoding is the right fix — it makes the test resilient to future reserve formula changes. This is strictly better than the original hardcoded value.
- **Import availability:** `Fake` is already imported at line 229 (`from test_providers import Fake, router`). ✓
- **Module-level execution:** `U` is computed at import time. `Fake` is a simple test class with no side effects. Safe. ✓

**No new defects found.** The fix is minimal, correct, and architecturally sound.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Cycle 3 | Why changed |
|---|---|---|---|---|
| Reserve arithmetic (`prompt_tokens_reserve`, `upper_usd`) | Correct | Correct | Correct | No change; hand-verified. |
| xAI output cap (`max_out`, `model_providers.json`) | Correct | Correct | Correct | No change; cap reaches API body. |
| `upper_usd` isolation (not read as strict bound) | Correct | Correct | Correct | No change; only `_reserve` consumes it. |
| Tests (4 new + 3 re-sized + 1 visual) | Correct | Correct | Correct | All arithmetic verified; no change. |
| **`test_reserve_wait.U` fix** | N/A (not in diff) | **DEFECT** (found at landing) | **FIXED** | Now derived from code; correct. |
| Docstrings / comments | Correct | Correct | Correct | No change. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 NIT:**
- [P3] `test_a_step_a_call_fits_what_the_day_has_left` (test_providers.py:205–218): shared ledger between loop iterations; reset between iterations would make intent unambiguous. Test passes for the right reason regardless.
- [P3] `prompt_tokens_upper` (providers.py:201): add a comment "NOT the reserve — see prompt_tokens_reserve" to prevent confusion with the near-identical `prompt_tokens_reserve` (providers.py:205).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Deriving `test_reserve_wait.U` from `Fake(...).upper_usd(...)` instead of hardcoding it — this fix eliminates the class of defect where a test's expected value silently goes stale when the production formula changes.

## 7. PRODUCTION READY?

**Yes.** The fix is correct, the reserve arithmetic is verified, the cap reaches the API, the isolation of `upper_usd` from billing paths is intact, and all tests pass. The two P3 nits are optional polish.

P1_OR_WORSE: 0