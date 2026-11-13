# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 9775 / out 2120 usd~0.061 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0707
# Reviewer: GLM-5.3-FLASH (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I raised two P1 findings. The consensus (and the fixed diff) addressed both:

- **P1-1 (KeyError/TypeError on `res`):** I was wrong. As Claude's consensus notes, `res` is always a dict from `PK.build` (the line before the assignment already does `res.update(...)`). My concern about `PK.build` returning `None` was speculative and not supported by the code. **I concede this finding was invalid.**

- **P1-2 (silent 0.0 on legacy ledger):** This was a real concern, and the fix is now in the diff (lines 31–33 of `providers.py`): `_basis_total` raises `SpendLimit` when `d.get("calls", 0)` is truthy but neither `usd_reported` nor `usd_unreported_estimate` is present. This is a fail-closed guard. **I agree with the fix.**

- **Post-build `router.spent()` crash (F2):** I did not explicitly flag this in Cycle 1, though it was adjacent to my P1-1. The fix (lines 87–90 of `proof_ledger.py`) wraps `router.spent()` in a try/except and records `"unreadable: ..."` in `spend_ruling_48.after`. This ensures the record is always written. **Good fix; I should have caught this more explicitly.**

- **Grok and Qwen** both correctly identified the floating-point fragility in the test (`places=6` on `3.46 + 1.81`) and the `spent()` returning 0.0 when `spend_path` is None. I did not flag these. They are P2 at most, but worth noting.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Position |
|---|---|---|
| P1-1: `res` can be None | GLM (me, C1) | **Disagree (retracted).** `res` is always a dict. The consensus refuted this correctly. |
| P1-2: silent 0.0 on legacy ledger | GLM (me, C1) | **Agree.** The fix in the diff (fail-closed on missing keys) is correct and tested. |
| Post-build `spent()` crash | Consensus (F2) | **Agree.** The try/except fix is correct. I should have flagged this more explicitly in C1. |
| Floating-point fragility in test | Qwen (C1) | **Agree (P2).** `3.46 + 1.81` in IEEE 754 is `5.2700000000000005`. `assertAlmostEqual(..., places=6)` passes, but it's brittle. Not a blocker. |
| `spent()` returns 0.0 when `spend_path` is None | Qwen (C1) | **Agree (P2).** This is pre-existing behavior, not changed by the diff. Worth documenting but not a defect. |
| "At $10 stop" interpretation | Grok, Qwen (C1) | **Agree.** The ruling says "At $10 reported stop and tell me." The implementation refuses to *start* a build at ≥$10, while a running build may continue to the $12 hard cap. This is a reasonable reading: "stop" refers to initiating new work. The $12 cap is the absolute boundary. |
| No P0/P1 findings | Grok, Qwen (C1) | **Agree.** After the fixes, I see no P0 or P1 issues. |

## 3. NEW FINDINGS FROM THIS REVIEW

### P2-1 — `tests/providers/test_providers.py:161` — Floating-point assertion fragility (confirmed from Qwen)

```python
self.assertAlmostEqual(r.spent(), 5.27, places=6)
```

`3.46 + 1.81` in IEEE 754 double-precision is `5.2700000000000005`. The `places=6` tolerance (`5e-7`) passes, but if the ledger values are ever updated to slightly different decimals, the sum could drift just enough to fail. **Recommendation:** Use `places=4` or compare against the explicit sum `3.46 + 1.81`. Not a blocker.

### P2-2 — `pipeline/providers.py:39-40` — `spent()` silently returns 0.0 when `spend_path` is None (confirmed from Qwen)

This is pre-existing behavior, not changed by the diff. However, `spent()` is now a public API surface (used in `proof_ledger.py` lines 72, 88). If a caller mistakenly omits `spend_path` while expecting spend tracking, they will see `0.0` and no `SpendLimit` will ever be raised. **Recommendation:** Document this behavior in the docstring (it is already partially documented: "0.0 with no ledger"). Not a defect.

### P2-3 — `tests/package/proof_ledger.py:73` — Stop check uses `>=` on `spent0` (confirmed from Grok, Qwen)

The pre-build check is `if spent0 >= PL.LY_STOP_USD`. This correctly implements "at $10 reported stop" by refusing to *start* a build when the running total is at or above $10.00. A build that starts at $9.99 may spend up to the $12.00 hard cap. This matches the ruling's intent. **No issue.**

### P2-4 — `pipeline/providers.py:31` — The fail-closed guard checks `d.get("calls", 0)` but not `d.get("usd_estimate", 0)`

The guard raises `SpendLimit` when `d.get("calls", 0)` is truthy but neither `usd_reported` nor `usd_unreported_estimate` is present. However, a ledger could theoretically have `calls: 0` but non-zero `usd_estimate` (e.g., a corrupted or partially written ledger). In that case, the guard would not raise, and `_basis_total` would return `0.0 + 0.0 = 0.0`. This is an edge case that is unlikely in practice (the ledger is written atomically under a file lock), but it is worth noting. **Not a blocker.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `pipeline/providers.py` | P1 (P1-2) | P2 | P1-2 fixed with fail-closed guard. Remaining issues are P2 (floating-point, `spent()` 0.0). |
| `tests/package/proof_ledger.py` | P1 (P1-1) | P2 | P1-1 retracted (invalid). Post-build crash fixed with try/except. Remaining issues are P2 (stop check interpretation, which is correct). |
| `tests/package/proof_ly.py` | Clean | Clean | No changes needed. Constants and Router construction are correct. |
| `tests/providers/test_providers.py` | Clean | P2 | Floating-point fragility in assertion (P2-1). Not a blocker. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. `tests/providers/test_providers.py:161` — Floating-point assertion fragility. Use `places=4` or compare against explicit sum.
2. `pipeline/providers.py:39-40` — `spent()` returns 0.0 when `spend_path` is None. Document this behavior more explicitly.
3. `pipeline/providers.py:31` — Fail-closed guard does not check `usd_estimate` for consistency. Edge case, unlikely in practice.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fail-closed guard in `_basis_total` (lines 31–33 of `providers.py`) is the most important change: it prevents a silent fail-open on a legacy ledger, which would have allowed the spend guard to under-count and potentially exceed the $12 cap.

## 7. PRODUCTION READY?

**Yes.**

The diff correctly implements Ruling 48. The spend guard now counts vendor-reported dollars (plus estimates for unreported calls) against a $12.00 cap, with a $10.00 pre-build stop. The default behavior for other callers is unchanged. The test coverage is adequate, with one minor floating-point fragility (P2) that does not block shipping.

**Conditions:**
1. The floating-point assertion in `test_providers.py:161` should be tightened to `places=4` or compared against the explicit sum `3.46 + 1.81` to avoid future brittleness.
2. The `spent()` method's behavior when `spend_path` is None should be documented more explicitly in the docstring.

Neither condition is a blocker. The code is production-ready as-is.