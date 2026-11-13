# qwen3.8-27b (qwen/qwen3.8-27b) 22 s finish=stop usage in 8380 / out 1433 usd~0.047 (upper-bound price)

# Audit: pp-selectid-1635 (C1_STEP.diff)

## Scope Verification
I reviewed the diff for `pipeline/package.py`, `pipeline/visual_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_medley.py`, and `tests/package/test_visual_pin.py`. The change is strictly a reporting/accounting fix for RULING 70 (separating vendor-reported cost from price-table estimates). It does not touch sentence law, selection locks, snap limits, credits, sign-off, edge words, dissent, protected preview, punctuation, channel-first, written forms, text-as-spoken, claim-is-event, release auth, canonical form, or model-reply validation. No gate thresholds, seal contents, or cache keys are modified.

## Findings

### P0 (Blocking)
None.

### P1 (Major)
None.

### P2 (Minor / Observations)

1. **`pipeline/visual_pin.py:44` — Bool guard is correct but worth noting**
   The check `isinstance(rep, (int, float)) and not isinstance(rep, bool)` correctly prevents `True`/`False` from being treated as a reported cost (since `bool` is a subclass of `int` in Python). This satisfies the requirement that "a bool ... never counts as reported." Verified correct.

2. **`pipeline/visual_pin.py:46` — Estimate fallback uses `Reply.usd`**
   When no vendor figure is present, the code falls back to `float(getattr(r, "usd", 0.0) or 0.0)`. This is the price-table estimate as documented. The `or 0.0` guard handles `None` or `0` gracefully. No issue.

3. **`pipeline/visual_pin.py:76` — Cache exclusion of `usd_basis`**
   The cache write excludes `"usd"` and `"usd_basis"` from the stored record. This is correct: cost is per-invocation, not a property of the visual judgment. The seal (`sealed()`) already excludes cost fields per the existing test at line 138–140. No change to seal or cache key.

4. **`pipeline/package.py:20–24` — Split accounting**
   `usd_reported` and `usd_estimate` are accumulated separately. `estimated_calls` counts only the estimate-basis calls. They are never summed under a single label. Correct.

5. **`tests/package/proof_ledger.py:88–93` — Log line**
   The driver prints `"$X vendor-reported"` and conditionally appends `"+ $Y price-table estimate for N call(s) with no vendor figure"` only when `estimated_calls > 0`. This matches the fix spec. No path labels an estimate as reported or vice versa.

6. **`tests/package/test_medley.py:106` — Test fixture**
   The mock visual record now includes `"usd_basis": "reported"`. The assertion at line 115 checks `(usd_reported, usd_estimate) == (0.006, 0.0)`, confirming the split. Three sheets at $0.002 each = $0.006 reported, $0.00 estimate. Correct.

7. **`tests/package/test_visual_pin.py:127–136` — Three bases covered**
   - `usd_reported` present → `{"usd": 0.041144, "usd_basis": "reported"}` ✓
   - `usd_reported` absent → `{"usd": 0.37, "usd_basis": "estimate"}` ✓
   - `cached=True` → `{"usd": 0.0, "usd_basis": "cached"}` ✓
   All three paths verified.

8. **No gate, seal, or cache-key changes**
   - Gates: No gate logic is touched. `MEDLEY_GATES` membership is unchanged (test line 116).
   - Seal: `sealed()` is not modified in this diff; the existing test confirms cost fields are excluded.
   - Cache key: The key `k` is computed before the cost logic and is unchanged. Only the *value* stored excludes `usd`/`usd_basis`.

9. **Smallest diff / no new renderer, compositor, or selector (M1)**
   The diff adds one small function (`cost`), modifies two accumulation sites, and updates tests. No new modules, no new rendering paths. Compliant.

10. **GPU0 only / no publishing**
    No GPU or publishing code is touched. Compliant.

## Specific Checks Requested

| Check | Result |
|---|---|
| No path labels an estimate as reported (or reverse) | **Pass.** `cost()` returns `"reported"` only when `usage["usd_reported"]` is a non-bool number. `package.build` routes to `usd_reported` only on `"reported"` basis, to `usd_estimate` only on `"estimate"` basis. Log line prints them separately. |
| Bool or missing figure never counts as reported | **Pass.** `isinstance(rep, bool)` is explicitly excluded. Missing `usd_reported` (KeyError → `None` via `.get()`) falls through to estimate. |
| Nothing changes a gate | **Pass.** No gate code modified. |
| Nothing changes the seal | **Pass.** `sealed()` untouched; cost fields already excluded. |
| Nothing changes the cache key | **Pass.** Key computation unchanged; only stored value excludes cost fields. |

## Uncertainties
- I cannot verify the actual runtime behavior of `providers.Router` or the xAI/Heimdall backends from this diff alone. The assumption that `Reply.usage["usd_reported"]` is the correct field for vendor-reported cost is taken from the background description and is consistent with the code.
- The diff does not show the full `sealed()` function, so I rely on the existing test (line 138–140) to confirm cost exclusion from the seal.

## SHIP: yes

The fix is minimal, correct, and fully tested. It resolves the RULING 70 defect (vendor-reported cost was being reported as a single "measured" figure that was actually the price-table upper bound). No gates, seals, cache keys, or other laws are affected. All three cost bases are covered by tests. The log line now accurately distinguishes vendor-reported from estimated cost.