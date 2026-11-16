# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 195 s finish=stop usage in 10005 / out 18667 usd_reported=0.002055 usd~0.310 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-20261116_1126

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

Both Gemma and Qwen found zero defects, matching my Cycle 1 assessment. Nothing material was missed. Two details they surfaced that I want to explicitly confirm:

- **Qwen's check (2)** — that `upper_usd` is never read as a strict billing bound elsewhere — was the most valuable cross-check. I verified: `upper_usd` feeds only `Router._reserve` (providers.py:1366, unchanged); `prompt_usd` (ruling 83a) and `prompt_tokens_upper` (ruling 107 Q1 reported-rate estimate) remain separate paths. The separation is intact.
- **Claude's consensus** flagged the `test_visual_pin.py` ruling-70 test re-sizing (the ×1.25 now applies to the per-image delta) and the correction that the 4 over-cap calls were one Nov 12 + three Nov 13. I verified both in the diff (lines 77–84 and 198–200).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| Gemma: reserve arithmetic correct | **Agree** | `-(-a // b)` is exact ceiling division for positive ints; `ceil(chars/3) + 200 + 6000·n_img` matches the ruling verbatim. |
| Gemma: xAI cap reaches the request | **Agree** | `max_out` returns `min(n, 12000)`; `complete` sends `self.max_out(max_tokens)` (providers.py:475, unchanged); test asserts 12,000 in the body. |
| Qwen: nothing else reads `upper_usd` as strict bound | **Agree** | Only `_reserve` consumes it; `prompt_usd` and `prompt_tokens_upper` are separate. |
| Qwen: tests pass logic check | **Agree** | I hand-verified every arithmetic assertion (see §3). |
| Claude: `test_visual_pin.py` re-sized correctly | **Agree** | `1.25 × 6000 = 7500` matches the new `upper_usd` delta; the second assertion pins `prompt_tokens_reserve` delta at exactly 6,000. |
| Claude: 4 over-cap calls dated correctly | **Agree** | Test asserts `len(cut) == 4` and all `recorded_at < "2026-11-14"`. |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

I hand-verified every numeric assertion in the diff. All check out:

**Reserve arithmetic (test_providers.py:150–158):**
- `max_out(4000)` → `min(max(8000, 32000), 12000)` = 12,000 ✓
- `max_out(1200)` → `min(max(8000, 9600), 12000)` = 9,600 ✓
- `max_out(750)` → `min(max(8000, 6000), 12000)` = 8,000 ✓
- `upper_usd("p"×7800, 4000)` = `1.25 × (2800×5e-6 + 12000×25e-6)` = 0.3925 ✓
- `upper_usd("p"×7801, 4000, system="s")` = `1.25 × (2801×5e-6 + 12000×25e-6)` = 0.392506 ✓ (7802/3 = 2600.67 → ceil 2601)

**Guard test re-sizes:**
- Test 1 (line 96): `1.25 × (50200×10e-6 + 2000×100e-6)` = 0.8775; 39.5 + 0.8775 = 40.3775 > 40 ✓
- Test 2 (line 107): reserve for `"p"` = `1.25 × (201×10e-6 + 2000×100e-6)` = 0.2525; 0.95 + 0.2525 = 1.2025 > 1.00 ✓; limit raised to 1.25 → fits ✓
- Test 3 (line 119): `1.25 × (400200×10e-6 + 2000×100e-6)` = 5.2525; 8.00 + 5.2525 = 13.2525 > 10 ✓

**Vision test (test_visual_pin.py:78–84):**
- `upper_usd` delta = `1.25 × 6000` = 7500 ✓ (price $1/token)
- `prompt_tokens_reserve` delta = 6000 ✓

**Step-A fit test (line 202–218):**
- Capped: reserve = 0.3925; 0.5835 + 0.3925 = 0.976 < 1.00 → runs ✓
- Uncapped: reserve = 1.0175; 0.5835 + 1.0175 = 1.601 > 1.00 → refused ✓
- Ledger is shared across iterations, but the second iteration expects refusal regardless (reserve alone exceeds $1.00), so correctness holds.

**New P3 findings (none rise above nit):**

- **[P3]** `test_a_step_a_call_fits_what_the_day_has_left` (test_providers.py:205–218) shares the ledger file between the two loop iterations. After the first (successful) call, the ledger gains the mocked call's cost (~$0.02), so the second iteration's spent is $0.6035 rather than $0.5835. The test still passes for the right reason (reserve alone exceeds $1.00), but resetting the ledger between iterations would make the test's intent unambiguous.
- **[P3]** `prompt_tokens_upper` (providers.py:201) and `prompt_tokens_reserve` (providers.py:205) are near-identical names serving different purposes (abandoned-call booking vs. spend-guard reserve). A future reader could confuse them. Consider a comment on `prompt_tokens_upper` explicitly saying "NOT the reserve — see prompt_tokens_reserve."

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Reserve arithmetic (`prompt_tokens_reserve`, `upper_usd`) | Correct | Correct | Hand-verified every numeric assertion; no change. |
| xAI output cap (`max_out`, `model_providers.json`) | Correct | Correct | Confirmed cap reaches API body; no change. |
| `upper_usd` isolation (not read as strict bound) | Correct | Correct | Qwen's cross-check confirmed; no change. |
| Tests (4 new + 3 re-sized + 1 visual) | Correct | Correct | All arithmetic verified by hand; no change. |
| Docstrings / comments | Correct | Correct | `_reserve` docstring and constants' comments accurately describe the new behavior. |

No score changes.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 NIT:**
1. [P3] Reset the ledger between loop iterations in `test_a_step_a_call_fits_what_the_day_has_left` (tests/providers/test_providers.py:210) so the second iteration's refusal is unambiguously caused by the reserve, not by accumulated spend.
2. [P3] Add a clarifying comment on `prompt_tokens_upper` (pipeline/providers.py:201) distinguishing it from `prompt_tokens_reserve` to prevent future confusion.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

No change required — the implementation is correct as shipped; the two P3 nits are optional polish.

## 7. PRODUCTION READY?

**Yes.** The reserve arithmetic matches RULING 121 (1) exactly (characters/3 ceiling-divided, +200 frame, +6,000/image, ×1.25, rounded to 6 dp); the 12,000-token cap reaches the xAI API body and is verified by test; `upper_usd` is consumed only by `_reserve` (never as a billing bound); all 4 new tests and 3 re-sized guard tests pass with hand-verified arithmetic; the ruling's check against 438 recorded Grok step-A calls asserts the tightest margin ≥ $0.10 and correctly dates the 4 over-cap calls. No conditions.

P1_OR_WORSE: 0