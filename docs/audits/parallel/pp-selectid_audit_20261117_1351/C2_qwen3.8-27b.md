# qwen3.8-27b (qwen/qwen3.8-27b) 149 s finish=stop usage in 11149 / out 12151 usd_reported=0.009182 usd~0.216 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261117_1351 — RULING 141 (2): STAND_ALONE SOFT

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Qwen's [P2] on the missing end-to-end hard-failure pin test:** I initially considered this covered by the unit tests on `stand_soft_rows` (every hard case returns `None`), and the consensus agrees. However, I now see the specific gap more clearly: there is no test that drives `PK.inventory(…, stand=stand_with_soft(segs_with_hook_failure), soft=True, …)` and asserts the row is `"FAIL"` with a non-empty `gate_problems`. The safety net is the `if soft and stand.get("soft_rows")` guard in inventory, but that guard is the *only* thing preventing a regression in `stand_with_soft` (e.g., always emitting `soft_rows={}`) from silently downgrading a hard FAIL to a FLAGGED with an empty flag list. I missed this in Cycle 1 because I focused on the logic of `stand_soft_rows` itself rather than the inventory's consumption of its output.

**Qwen's [P2] on positional coupling:** I noted this in Cycle 1 but didn't fully trace the invariant. The consensus correctly identifies that `stand_alone_check` builds its EDL from the same `segs` in the same order, and `check_edl` labels rows positionally. I agree this is by design and not a defect.

**Gemma's clean read:** I agree with Gemma's assessment that the implementation is precise and maintains clean-pass integrity. No disagreement.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My position |
|---------|-------------|
| Qwen [P2] `stand_plain` fallback | **Agree with consensus: BY DESIGN.** The two regexes parse `SA.opener`'s own clip wordings. Any other wording is the render's reason verbatim. The integrator matches the prefix, not the tail. No gate is bypassed. |
| Qwen [P2] No e2e hard-failure pin test | **Partially agree.** The unit tests on `stand_soft_rows` cover every hard case. But the inventory-level guard (`if soft and stand.get("soft_rows")`) is untested in the specific scenario where `stand_with_soft` might regress to always emit `soft_rows`. I'd call this [P2], not [P1], because the current code is correct and the unit tests kill the relevant mutations. |
| Qwen [P2] Positional `labels()` mapping | **Agree with consensus: BY DESIGN.** The EDL is built from the same `segs` in the same order. |
| Qwen [P3] Double period | **Agree: DECLINED.** Neither of `SA.opener`'s clip wordings ends with a period. |
| Qwen [P3] Dense comprehension | **Agree: DECLINED.** Cosmetic. |
| Gemma: No violations | **Agree.** The implementation is correct. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] No unit test for the `not in trims` guard (mutation S3 survivor)

**Location:** `package.py` line 101 (`stand_back` comprehension)

The condition `m["moment_id"] not in trims` ensures that a moment with an *affirmed* trim variant is not also brought back as a flagged clip. The trim is the preferred (clean) version; the original would be redundant and would carry a `stand_soft` flag unnecessarily.

No test exercises this path. The end-to-end rig uses moments "h", "x", "z", "w" — none have trim variants. If the `not in trims` condition were removed, a moment with an affirmed trim would appear in the pool *twice* (original with flag, trim without). The lineup rule "one video at most once" prevents both in the same lineup, but the picker could select the flagged original over the clean trim, producing an unnecessary flag.

**Suggestion:** Add a unit test: construct a moment that fails the opener, give it an affirmed trim variant, run `_build(soft=True)`, and assert the original is NOT in `stand_back` while the trim IS in the pool.

### [P3] No test for a non-conjunction moment (low clip score) carrying a `stand_soft` mark into the hook position

**Location:** `package.py` lines 46–48 (`stand_soft_rows`), line 57 (`stand_ok`)

A moment that opens on "Bitcoin" (not a conjunction) but receives a clip score of 2.0 would be brought back by `stand_back` with a `stand_soft` mark. If the lineup picker then selects it as the hook, the hook row in `stand_soft_rows` is checked: if it passes, the mark is irrelevant; if it fails, `stand_soft_rows` returns `None` and the lineup is rejected. The logic is sound, but no test drives this specific path (non-conjunction, low-score moment as hook).

This is low-risk because the hook opener rule (`SA.opener("hook", …)`) is a different check from the clip opener rule, and a moment that passes the hook opener but fails the clip opener is a narrow edge case.

### [P3] `soft_record` includes `"soft_stand": None` when no moments are brought back

**Location:** `package.py` line 145

```python
"soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}
```

When `stand_back` is empty, `soft` has no `"soft_stand"` key, so `soft.get("soft_stand")` is `None`. The record shows `"soft_stand": None`. This is harmless (it's a diagnostic record) but slightly inconsistent with the other keys which are always present. Nit.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_plain` (reason mapping) | Correct | Correct | No change. Fallback is by design. |
| `stand_soft_rows` (gate adjudication) | Correct | Correct | All hard cases properly return `None`. Positional mapping is by design. |
| `stand_ok` / `stand_with_soft` (integration) | Correct | Correct | Clean pass unchanged; soft pass properly gated. |
| `_build` (pool construction) | Correct | Correct | `stand_back` logic is sound. `not in trims` guard is correct but untested. |
| `lineup_ok` / `lineup_for` (picker) | Correct | Correct | `stand_ok` properly replaces bare check. Hook can never be soft. |
| `inventory` (pin row) | Correct | Correct | FLAGGED only when `soft and stand.get("soft_rows")`. Exact prefix verified. |
| `package_pin.SOFT_GATES` | Correct | Correct | `"stand_alone"` added; FAIL still blocks, FLAGGED passes. |
| Tests | Adequate | Adequate with one gap | S3 (`not in trims`) untested. All other paths covered. |

---

## 5. FINAL PRIORITY LIST

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | [P2] | `package.py:101`, `tests/package/test_ruling_137.py` | No unit test for the `not in trims` guard. A moment with an affirmed trim should not be brought back by `stand_back`. Mutation S3 survives. Add a test. |
| 2 | [P2] | `tests/package/test_ruling_137.py` | No test drives `PK.inventory(…, stand=stand_with_soft(hard_failure_segs), soft=True, …)` asserting the row is `"FAIL"` (not `"FLAGGED"`) and `gate_problems` is non-empty. The inventory guard `if soft and stand.get("soft_rows")` is the sole safety net against a `stand_with_soft` regression. |
| 3 | [P3] | `package.py:145` | `soft_record` shows `"soft_stand": None` when empty. Cosmetic inconsistency. |
| 4 | [P3] | `tests/package/test_ruling_137.py` | No test for a non-conjunction (low-score) moment carrying `stand_soft` into the hook position. Logic is sound; edge case untested. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a unit test that constructs a moment failing the opener rule *and* having an affirmed trim variant, runs `_build(soft=True)`, and asserts the original is absent from `stand_back` while the trim is present in the pool — this kills the S3 mutation and closes the only untested guard in the `stand_back` comprehension.

---

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. Add the [P2] test for the `not in trims` guard (S3 mutation). This is the only untested logic path that could produce a suboptimal (but not incorrect) result.
2. Add the [P2] inventory-level test for a hard failure in the soft pass, to protect the `if soft and stand.get("soft_rows")` guard against future regression in `stand_with_soft`.

Neither condition blocks correctness today — the code is right. Both are test-coverage gaps that protect against future mutations. If the team's bar is "all mutation survivors tested," these two must land before merge. If the bar is "no P0/P1 defects," this ships as-is.

---

P1_OR_WORSE: 0