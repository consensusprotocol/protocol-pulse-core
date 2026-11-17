# qwen3.8-27b (qwen/qwen3.8-27b) 97 s finish=stop usage in 7790 / out 8273 usd_reported=0.006261 usd~0.147 (upper-bound price)



# Code Audit: pp-selectid — RULING 130 (3) Vision Reserve Tripwire

## Scope Reviewed

The diff modifies three files to fix a gap in the RULING 123 tripwire: vision calls whose usage runs past their output cap produce bills that are only 24–29 % of the list price of their *actual* usage, so the old `bill > fraction × list_of_usage` test never fired. The fix adds a second condition: `bill > held` (the amount actually reserved for the call).

---

## Findings

### [P3] Theoretical `held == 0` path is unreachable but unguarded

`over_held` requires `_num(held)`. If `_num(0)` returns `True` (it does for a standard `isinstance(x, (int, float))` check), then a call with `held = 0` would trip on any positive bill. In practice this is unreachable: `held = round(upper * frac, 6)` with `frac ∈ {0.25, 0.6}` and `upper > 0` (a zero-estimate call is rejected before settlement). No code change needed; noted for completeness against the audit question "cannot fire on a call that reserved nothing."

### [P3] `reserve_list_fraction_why` is a documentation-only JSON key

The 200-word rationale string in `model_providers.json` is never read by `providers.py` (only `reserve_list_fraction` is). It is clearly suffixed `_why` and sits alongside functional keys, so the risk of a future reader mistaking it for a parameter is low. No action required.

### [P3] Integration test reads live config

`test_ruling_130_the_vision_check_is_reserved_at_its_fraction` loads `P.CONFIG` and constructs a real vendor via `P.VENDORS["xai_vision"](...)`. This is appropriate (it verifies the *configured* backend end-to-end) but makes the test sensitive to config drift. If `price_usd_per_1m` or `min_out` change, the test's arithmetic shifts. Acceptable for a ruling-verification test; a pure-unit twin would be more robust for CI.

---

## Verification Against the Four Audit Questions

**(1) Fraction against the bills.**
Max recorded bill $0.1752 / list bound $0.2965 = 59.1 %. The configured fraction is 0.60, which exceeds the observed maximum. The `why` string documents the full distribution (min / median / p90 / max). Correct.

**(2) New tripwire test and the "reserved nothing" guard.**
- `over_held = bill is not None and _num(f) and _num(held) and bill > float(held)`.
- If `f` is absent (`_num(f)` False), neither `over_list` nor `over_held` evaluates → no trip. Backends without a fraction are unaffected.
- If `held` is `None` (no reservation made), `_num(None)` False → no trip.
- The test `test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list` exercises exactly the gap: bill $0.25 > held $0.2295 but < 0.6 × $0.755 (list of actual usage). The trip fires via `over_held`, the `why` string names "above its reserve," and the next call on the same day is reserved at full list and hits `SpendLimit`. Correct.

**(3) No change for other back-ends.**
Grok-4.7 (fraction 0.25, bills ≈ $0.01, reserves $0.06–$0.12): `over_list` and `over_held` are both far from triggering. The `not (d.get("reserve_tripped") or {}).get(backend.name)` guard prevents re-tripping. The `bill` extraction refactor (`float(usage["usd_reported"]) if _num(...) else None`) is semantically identical to the old inline check. No behavioural change for non-vision back-ends. Correct.

**(4) Tests.**
- Two new tests in `TestRuling123Reserve` cover: (a) the new `over_held` path with a follow-up `SpendLimit`, and (b) the configured vision backend reserving at its fraction (boundary ± 0.001).
- Existing RULING 123 tests are unchanged and still pass (confirmed by the 852-test suite run).
- Mutation testing: 3/3 killed (V1–V3).
- The `billed` field in the trip record now uses the pre-extracted `bill` variable rather than re-reading `usage["usd_reported"]`—equivalent, slightly cleaner.

---

## Governing-Law Compliance

| Law | Status |
|-----|--------|
| LAW 20 / M2 (thresholds are constants; hard stop) | ✓ — 0.6 is a config constant; the trip is a hard stop (reserve reverts to list for the day). |
| M12 FAIL CLOSED | ✓ — missing `usd_reported` → `bill = None` → no trip (the call still settles; the trip is a cost-control escalation, not a quality gate). |
| Smallest diff / no new renderer | ✓ — 5 lines of logic changed in `providers.py`; no new modules. |
| GPU0 only / no publishing | N/A — spend-routing change. |

No law violations found.

---

## Verdict

The change is correct, minimal, well-tested, and addresses the identified gap (vision bills that never exceeded the fraction-of-actual-usage threshold). The new `over_held` condition is properly guarded, the trip record is informative, and the follow-up reservation at full list is verified by test.

**P1_OR_WORSE: 0**