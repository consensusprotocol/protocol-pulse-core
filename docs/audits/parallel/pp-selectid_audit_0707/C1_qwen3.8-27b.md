# qwen3.8-27b (qwen/qwen3.8-27b) 19 s finish=stop usage in 9491 / out 1170 usd~0.046 (upper-bound price)

# Audit: pp-selectid-0707 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings
None.

## P2 Findings

**1. `tests/providers/test_providers.py:154` — Fragile floating-point assertion**
The test asserts `self.assertAlmostEqual(r.spent(), 5.27, places=6)`. The ledger is seeded with `usd_reported: 3.46` and `usd_unreported_estimate: 1.81`. In IEEE 754 double-precision, `3.46 + 1.81` evaluates to `5.2700000000000005`. While `assertAlmostEqual` with `places=6` (tolerance `5e-7`) will pass, this is brittle. If the ledger values are ever updated to slightly different decimals (e.g., `3.461` and `1.809`), the sum might drift just enough to fail a strict `places=6` check if the error exceeds `5e-7`. It is safer to use `places=4` or compare against the explicit sum `3.46 + 1.81`.

**2. `pipeline/providers.py:34-39` — `spent()` returns 0.0 when `spend_path` is None**
The `spent()` method returns `0.0` if `self.spend_path` is not set. This is consistent with `_reserve` (which skips reservation if `spend_path` is None), but it means that a Router constructed without a `spend_path` will report `spent() == 0.0` regardless of actual usage. This is likely intentional (no ledger = no tracking), but it is a subtle behavior: if a caller mistakenly omits `spend_path` while expecting spend tracking, they will see `0.0` and no `SpendLimit` will ever be raised. The diff does not change this behavior, but it is worth noting that `spent()` is now a public API surface that silently returns zero when unconfigured.

**3. `tests/package/proof_ledger.py:70-74` — Stop check uses `>=` on `spent0`**
The pre-build check is `if spent0 >= PL.LY_STOP_USD`. This correctly implements "at $10 reported stop" by refusing to *start* a build when the running total is at or above $10.00. A build that starts at $9.99 may spend up to the $12.00 hard cap (bounded by its own per-build budget). This matches the ruling's intent: the $10 threshold is a *start* gate, not a mid-build abort. No issue, but the distinction is critical and correctly implemented.

## Verification of Key Requirements

1. **Reported basis counts every call exactly once:**
   - `_basis_total` returns `usd_reported + usd_unreported_estimate`.
   - Per the background, `usd_reported` covers calls where the vendor reports a cost, and `usd_unreported_estimate` covers calls where it does not (STT, abandoned calls). These are disjoint sets maintained by `Router._settle`.
   - A paid call is never counted in both, and never in neither. **Verified.**

2. **Lock and reservation logic unchanged:**
   - `_reserve` still acquires `self._lock()`, reads the ledger, sums `reserved`, and compares `spent + held + upper > limit_usd`.
   - The only change is that `spent` is now `self._basis_total(d)` instead of `d["usd_estimate"]`.
   - Reservations remain price-table upper bounds. **Verified.**

3. **Nothing else changes for callers that do not pass `limit_basis`:**
   - The default is `limit_basis="estimate"`, which returns `d["usd_estimate"]` from `_basis_total` — identical to the old behavior.
   - The `ValueError` guard only triggers for invalid strings, not for the default. **Verified.**

4. **Build can never start at or over $10; hard cap is $12:**
   - `proof_ledger.py` exits with code 3 if `spent0 >= LY_STOP_USD` ($10.00).
   - `Router` raises `SpendLimit` if `spent + reserved + upper > limit_usd` ($12.00).
   - **Verified.**

5. **"At $10 reported stop" interpretation:**
   - The ruling says "At $10 reported stop and tell me." The implementation stops *starting* new builds at $10, but allows a running build to continue to the $12 hard cap. This is a reasonable reading: "stop" refers to initiating new work, not aborting in-flight work. The $12 cap is the absolute boundary. **No issue.**

## SHIP: yes

The diff correctly implements Ruling 48. The spend guard now counts vendor-reported dollars (plus estimates for unreported calls) against a $12.00 cap, with a $10.00 pre-build stop. The default behavior for other callers is unchanged. The test coverage is adequate, with one minor floating-point fragility (P2) that does not block shipping.