# qwen3.8-27b (qwen/qwen3.8-27b) 83 s finish=stop usage in 6460 / out 7245 usd_reported=0.005466 usd~0.128 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## pp-selectid-20261116_2319 — RULING 130 (3): Vision Reserve Tripwire

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Qwen's three P3s** are all valid observations I under-weighted in Cycle 1:

- **`held == 0` unguarded path** (P3): I verified the logic is correct but didn't explicitly trace the `_num(0)` → `True` → `bill > 0.0` path. Qwen correctly notes it's unreachable (a zero-estimate call is rejected before settlement; `held = round(upper * frac, 6)` with `upper > 0` and `frac > 0`), but the absence of an explicit `held > 0` guard is a one-line hardening that costs nothing. I should have flagged it.

- **`reserve_list_fraction_why` is documentation-only** (P3): I read it as context but didn't note that `providers.py` never parses it. The `_why` suffix makes the intent clear, but a future contributor could mistake it for a parameter. Minor.

- **Integration test reads live config** (P3): I focused on the test's *correctness* (it is correct) but didn't flag the *fragility*: if `price_usd_per_1m` or `min_out` change in `model_providers.json`, the test's arithmetic shifts. Qwen's point that a pure-unit twin would be more CI-robust is fair.

**Gemma** found nothing I missed; its analysis was a clean confirmation.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My position |
|---|---|---|
| Fraction 0.6 > observed max 59.1% | All three | **Agree.** 0.1752 / 0.2965 = 0.5909. The 0.60 ceiling has ~1.7% headroom above the worst recorded bill. Correct. |
| `over_held` properly guarded by `_num(f)` and `_num(held)` | All three | **Agree.** No fraction → no trip. No reservation → no trip. Backends without a fraction are untouched. |
| No behavioural change for Grok (frac 0.25) | All three | **Agree.** Grok bills (~$0.01) are far below both `f × usd` and `held` ($0.06–$0.12). The `over_held` condition is inert. |
| `bill` extraction refactor is semantically identical | Qwen, Gemma | **Agree.** Old: `_num(usage.get("usd_reported"))` guard then `float(usage["usd_reported"])`. New: same guard, same float, stored in `bill`. The trip record's `billed` field uses `round(bill, 6)` instead of `round(float(usage["usd_reported"]), 6)` — identical value. |
| `held == 0` unreachable but unguarded | Qwen | **Agree (P3).** Not a defect; a theoretical hardening opportunity. |
| `_why` key is documentation-only | Qwen | **Agree (P3).** No action needed. |
| Vision test reads live config | Qwen | **Agree (P3).** Acceptable for a ruling-verification test; a unit twin would be more robust. |
| `why` string correctly differentiates which test fired | All three | **Agree.** Ternary picks `over_list` reason when both fire (the "primary" RULING 123 path), `over_held` reason otherwise. Informative and correct. |
| Mutation testing 3/3 killed | Consensus | **Agree.** V1–V3 (presumably: remove `over_held`, remove `_num(held)` guard, swap `>` to `>=`) all killed. |

**No disagreements.** All Cycle 1 models converged on P1_OR_WORSE: 0, and I concur.

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P3] `over_held` is mathematically redundant for non-vision backends

For any backend where actual usage ≤ output cap (all non-vision backends), `usd ≤ upper`, so `f × usd ≤ f × upper = held`. In that regime, `bill > held` implies `bill > f × usd`, meaning `over_list` already fires. The `over_held` condition is **only** additive when `usd > upper` (vision: usage runs past the output cap, so list-of-actual-usage exceeds the list-of-capped-usage). This is by design and the comment on lines 27–28 explains it, but it's worth noting explicitly: the new condition is a no-op for every non-vision backend, not just "far from triggering."

### [P3] The `why` string omits the `over_list` value when `over_held` fires

When only `over_held` fires (the vision gap case), the `why` string says `"billed above its reserve ($0.2295)"` but doesn't mention the `f × usd` threshold ($0.453 in the test). An operator reading the trip record sees the fraction and the reserved amount in the structured fields, so the information is present — but the human-readable `why` could be slightly more complete. Not a defect; a readability nit.

### [P3] Test line 66: `round(0.3825 * 0.6, 6)` is computed in the test, not read from the router

The assertion `self.assertEqual((trip["billed"], trip["reserved"]), (0.25, round(0.3825 * 0.6, 6)))` hard-codes the expected `reserved` value via arithmetic in the test. If the router's reservation formula changes (e.g., a different multiplier), the test would need updating. This is standard practice for a ruling-verification test (it pins the *expected* behaviour), so it's fine, but it's a coupling worth being aware of.

### No P0, P1, or P2 findings.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Fraction derivation (0.6 vs. bills) | Correct | Correct | No change. 59.1% max, 0.60 ceiling. |
| Tripwire logic (`over_list` / `over_held`) | Correct | Correct | No change. Guards are sound; `over_held` is additive only for vision. |
| Non-vision backend isolation | Correct | Correct | No change. `_num(f)` gate ensures no fraction → no trip. `over_held` is mathematically subsumed by `over_list` when `usd ≤ upper`. |
| Trip record & `why` string | Correct | Correct | No change. Slightly more informative than before. |
| Test coverage | Sufficient | Sufficient | Two new tests cover the gap and the configured backend. Existing RULING 123 tests unchanged. |
| Governing-law compliance | Compliant | Compliant | No change. LAW 20/M2, M12 FAIL CLOSED, smallest-diff all satisfied. |

No score changes. The code is correct.

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 NITS (no action required before ship):**

| # | File / Line | Note |
|---|---|---|
| 1 | `providers.py` L26 | `over_held` could add `and float(held) > 0` for theoretical hardening against a `held == 0` path that is currently unreachable. |
| 2 | `model_providers.json` L10 | `reserve_list_fraction_why` is never read by code. The `_why` suffix makes this clear; no action needed. |
| 3 | `test_providers.py` L77 | The vision test reads live config. A pure-unit twin (hard-coded price, fraction, min_out) would be more CI-robust. Acceptable as-is for a ruling-verification test. |
| 4 | `providers.py` L36–38 | The `why` string when `over_held` fires could include the `f × usd` threshold for operator clarity. Readability only. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `over_held` condition on line 26 is the entire fix: one boolean expression that closes the gap where a vision bill (24–29% of its usage's list price) could never exceed `fraction × list_of_usage`, by instead comparing the bill to the amount actually reserved for the call — the number that was *supposed* to be the ceiling.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all already satisfied by the diff):
- The 852-test suite passes (40 files by exit code).
- Mutations V1–V3 are killed (3/3).
- No governing-law violations (LAW 20/M2, M12, smallest-diff, GPU0).
- The fraction (0.6) exceeds the worst recorded bill ratio (59.1%) with documented headroom.
- The trip is a hard stop: once `reserve_tripped` is set for a backend on a day's ledger, all subsequent calls that day reserve at full list, and the `SpendLimit` check enforces the budget.
- The worst-case overrun is one call's bill above its reserve, once per day, before the trip fires. Bounded.

No changes required before merge.

---

P1_OR_WORSE: 0