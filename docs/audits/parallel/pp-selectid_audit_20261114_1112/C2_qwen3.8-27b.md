# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 10769 / out 1956 usd~0.062 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: pp-selectid-20261114_1112

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok-4.20's `<critical>` finding was a false positive, but it forced a necessary verification.** Grok claimed the change violated "LAW 20/M2" by reclassifying a failing gate. The orchestrator's consensus correctly refuted this: the change *is* the ruling. However, Grok's `<medium>` finding about `SNAP_MAX_S` being hardcoded rather than imported from `spotlight.SPOT_S[1]` is valid and was missed in my Cycle 1 review. The test at `test_ledger_build.py:139` asserts equality, but the production code at `ledger_build.py:10` hardcodes `35.0`. If `spotlight.SPOT_S` changes, the test fails but the production code silently retains the old value. This is a maintainability risk, not a correctness bug, but it violates the single-source-of-truth principle.

**Qwen3.8-27B's regex analysis was thorough and correct.** Its verification of the `(?![\w.]?\d)` lookahead for "November 120" and the ISO lookbehind/lookahead for "2026-11-120" matches my own analysis. Its `<high>` finding about `SNAP_MAX_S` decoupling is the same as Grok's `<medium>`.

**GLM-5.3-FLASH's H1 finding about `TypeError` not being caught is partially valid.** The code at `vo_fidelity.py:50` does `str((manifest or {}).get("date") or "")`. If `manifest` is a non-dict truthy object (e.g., a list), `.get` raises `AttributeError`. This exception propagates out of `without_manifest_date` and into `check_deterministic`. Whether this is a violation depends on the caller's exception handling. The background states that `check_deterministic` is code, not a model call, so an unhandled exception would crash the deterministic layer. This is a real edge case, but the orchestrator's consensus notes that "a date that `date.fromisoformat` cannot read leaves the text as it is, which is the stricter old behaviour." The `AttributeError` case is not covered by the `ValueError` catch.

## 2. WHERE DO YOU AGREE OR DISAGREE?

**Grok-4.20 `<critical>`: DISAGREE.** The change implements the orchestrator's ruling (3) verbatim. The ruling explicitly states that NUMBER should accept the manifest's own show date. This is not a reclassification of a failing gate; it is a new rule. The 16 must-pass cases that previously failed now pass because the ruling changed the specification.

**Grok-4.20 `<medium>`: AGREE.** The hardcoded `SNAP_MAX_S = 35.0` should be `SNAP_MAX_S = spotlight.SPOT_S[1]` to ensure single-source-of-truth. The test catches drift, but the production code is fragile.

**Qwen3.8-27B `<high>`: AGREE.** Same as Grok's `<medium>`. The `SNAP_MAX_S` decoupling is a real maintainability risk.

**Qwen3.8-27B `<medium>` (regex): AGREE.** The regex logic is sound for the provided tests. The lookahead/lookbehind correctly prevent partial matches.

**GLM-5.3-FLASH H1: PARTIALLY AGREE.** The `TypeError`/`AttributeError` edge case is real but low-probability. The manifest is expected to be a dict. The `ValueError` catch handles malformed date strings. The `AttributeError` case would require a non-dict manifest, which is outside the expected input domain.

**GLM-5.3-FLASH H2: AGREE (withdrawn).** The regex mechanism works correctly. "November 120" is not stripped, and NUMBER reads "120". The test passes.

**GLM-5.3-FLASH H3: INCOMPLETE.** The analysis was cut off. The concern about chunk boundaries is valid but not fully explored.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> `without_manifest_date` does not catch `AttributeError` from non-dict manifests.** `vo_fidelity.py:50`. If `manifest` is a non-dict truthy object (e.g., a list), `(manifest or {}).get("date")` raises `AttributeError`. This exception propagates out of `without_manifest_date` and into `check_deterministic`, potentially crashing the deterministic layer. Concrete input: `manifest = [("date", "2026-11-12")]`, `text = "Pulse Check for 2026-11-12."`. The `ValueError` catch at line 51 does not cover `AttributeError`. The fix is to wrap the entire expression in a `try/except (ValueError, AttributeError, TypeError)` or to validate that `manifest` is a dict before calling `.get`.

**<low> The `MONTHS` tuple is defined at module level but only used in `without_manifest_date`.** `vo_fidelity.py:39-40`. This is fine, but if other functions need month names, they should use this tuple to avoid locale issues. The current code is correct.

**<low> The test at `test_gates.py:114` uses a manifest without a `date` key.** `{"show": "Pulse Check"}`. This correctly tests the "no manifest date" case. The function returns the text unchanged, and NUMBER reads "2026-11-12" as a number. This is the expected behavior.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `ledger_build.py` | 8/10 | 7/10 | Hardcoded `SNAP_MAX_S` is a maintainability risk. The test catches drift, but the production code should import from `spotlight`. |
| `vo_fidelity.py` | 9/10 | 8/10 | The `AttributeError` edge case is a real but low-probability bug. The regex logic is sound. |
| `test_gates.py` | 9/10 | 9/10 | The tests are comprehensive and correctly verify the ruling. |
| `test_ledger_build.py` | 8/10 | 8/10 | The tests correctly verify the new ceiling and the medley's 20 s limit. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. `ledger_build.py:10`: Change `SNAP_MAX_S = 35.0` to `SNAP_MAX_S = spotlight.SPOT_S[1]` to ensure single-source-of-truth. Import `spotlight` at the top of the file. Verify no circular dependencies.
2. `vo_fidelity.py:50`: Wrap the manifest date extraction in a `try/except (ValueError, AttributeError, TypeError)` to handle non-dict manifests gracefully. Return `text or ""` on any exception.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Import `spotlight.SPOT_S[1]` into `ledger_build.py` and set `SNAP_MAX_S` to that value, ensuring the snap ceiling is always synchronized with the spotlight's ceiling and preventing silent drift if `SPOT_S` changes.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Refactor `SNAP_MAX_S`:** Change `pipeline/ledger_build.py:10` to import `spotlight` and set `SNAP_MAX_S = spotlight.SPOT_S[1]` instead of hardcoding `35.0`. This ensures the "spotlight's ceiling" is truly dynamic and prevents drift if `SPOT_S` changes.
2. **Handle non-dict manifests:** Change `pipeline/vo_fidelity.py:50` to catch `AttributeError` and `TypeError` in addition to `ValueError`, returning `text or ""` on any exception. This prevents crashes if a non-dict manifest is passed.
3. **Verify `spotlight` import:** Ensure `spotlight` is importable in `ledger_build.py` without circular dependencies. If `spotlight` imports `ledger_build`, use a lazy import inside the function or a module-level `__getattr__`.

These conditions are low-risk and can be implemented quickly. The core logic of the change is correct and implements the orchestrator's rulings verbatim.