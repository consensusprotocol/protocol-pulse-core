# gemma-4-31b-it (google/gemma-4-31b-it) 323 s finish=stop usage in 14859 / out 7044 usd_reported=0.001334 usd~0.150 (upper-bound price)

This audit focuses on the implementation of **RULING 118 (The Day Cap)**.

### Analysis of Findings

#### 1. Undefined Variable and Logic Error in `spent()` [P0]
In `pipeline/providers.py`, the `spent` method is defined as `def spent(self):` (line 49). However, line 55 introduces a conditional check:
`if not self.spend_path or b.free() or not self._capped(b.name): return None`
- **Undefined Variable:** The variable `b` is not passed as an argument, nor is it a member of the `Router` class. Calling `spent()` will immediately raise a `NameError: name 'b' is not defined`.
- **Type Mismatch:** Even if `b` were defined, the method returns `None` when a backend is free or uncapped. The `Router`'s internal logic (and the provided tests in `test_providers.py` and `test_ledger_router.py`) expects `spent()` to return a `float` representing the total expenditure. Returning `None` will cause a `TypeError` during any numeric comparison (e.g., `spent + reserved > limit`).
- **Misplaced Logic:** The check for whether a specific backend is "free" or "uncapped" belongs in the reservation logic (`_reserve`) or the summation logic (`_basis_total`), not in a method that reports the total spent amount for the entire router.

#### 2. Day Ledger Boundary and First Day Mapping [P2]
In `tests/package/proof_ly.py`, the `day_ledger` function correctly implements the 21:10 ET boundary. However, the mapping to `SPEND_B4.json` is hardcoded to the string `"20261115"`. While this satisfies the current requirement for the transition from Batch 4, it creates a fragile dependency on a specific date string for the "first day" of the new regime. This is a minor architectural nit but should be noted.

#### 3. Shadow Filtering Logic [P3]
In `tests/package/proof_ledger.py`, `build_shadow` now filters for `PL.UNCAPPED`. The use of `str(v).split(":", 1)[0]` is consistent with the `_capped` logic in `providers.py`, ensuring that only Heimdall-based shadows are retained. This is correct.

#### 4. Basis Total Calculation [P3]
The implementation of `_basis_total` in `pipeline/providers.py` correctly handles the "stricter reading" for the reported basis by summing only capped vendors' reported costs while adding the `usd_unreported_estimate` in full. The estimate basis is also correctly filtered.

### Summary of Compliance
- **Outside Vendor Cap:** The logic in `_basis_total` and `_capped` correctly isolates outside vendors for capping.
- **Heimdall Free/Recorded:** The `uncapped` parameter allows Heimdall to bypass the cap while still being processed by the ledger.
- **Day Boundary:** The `day_ledger` logic correctly handles the 21:10 ET shift.
- **Tests:** While the user claims tests pass, the code provided in the diff for `spent()` is mathematically and syntactically impossible to execute without a `NameError` or `TypeError`.

P1_OR_WORSE: 1