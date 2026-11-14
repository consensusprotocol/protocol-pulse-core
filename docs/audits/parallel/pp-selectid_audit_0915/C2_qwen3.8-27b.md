# qwen3.8-27b (qwen/qwen3.8-27b) 66 s finish=stop usage in 24616 / out 4147 usd~0.136 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0915

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok-4.20's `<high>` finding on `spotlight.py:245` (missing `import hashlib`) is the most significant miss from my Cycle 1 review.** I did not flag this. Let me verify it against the diff:

- The diff at line 104 shows `import hashlib` is **already present** in the file header (it's in the context lines of the `@@ -36,6 +36,7 @@` hunk, meaning it was there before this change). The new hunk adds `import math` (line 106). So `hashlib` is imported at module level.
- **However**, Grok's claim is that the *test file* `test_spotlight.py:573` does `import hashlib` locally, implying the production file might not have it. Re-reading the diff: line 104 is a context line (no `+` prefix), confirming `import hashlib` was already in `spotlight.py`. **Grok's finding is REFUTED** — `hashlib` is already imported at module scope. The test's local import is redundant but harmless.

**GLM-5.3-Flash's `<critical>` on `universe_levels` raising `ValueError` instead of `GateNotMeasured`:** This is the key finding I need to re-examine carefully. GLM traced the code path and concluded that `vo_fidelity` does NOT wrap `universe_levels()` in a try/except that converts `ValueError` to `GateNotMeasured`. Let me verify:

Looking at the diff lines 84–97:
```python
def vo_fidelity(case):
    ...
    if case.get("title") is not None:
        if not isinstance(case["title"], str) or not case["title"].strip():
            raise ValueError("the case's title is not a non-empty string")
        lines.append({"slot": "title", ...})
    levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
    if levels is None and case.get("universe") is not None:
        levels = universe_levels(case["universe"])
    try:
        res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
    except P.ReplayMiss as e:
```

The `try` block starts at line 95, **after** the `universe_levels()` call at line 94. So a `ValueError` from `universe_levels` (e.g., zoneless `built_at`) propagates as `ValueError`, not `GateNotMeasured`.

**But wait** — the test at line 448–455:
```python
def test_an_unreadable_case_is_the_harness_error_never_a_guess(self):
    for bad in (v11(title=""), v11(title=5), v11(universe=dict(UNIVERSE, built_at="2026-11-12")),
                v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")), v11(universe={"news": []}),
                v11(universe=dict(UNIVERSE, news="none"))):
        with self.assertRaises(A.GateNotMeasured, msg=str(bad.get("title"))):
            self.run_case(bad)
```

This test asserts `GateNotMeasured` for `v11(title="")` and `v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13"))`. But the code raises `ValueError` for both. **Unless the harness (`run_exam_record.py`) catches `ValueError` and converts it to `GateNotMeasured`.**

The diff shows `run_exam_record.py` lines 333–343:
```python
A._router = A.make_router(chains=chains or None)
os.makedirs(a.out, exist_ok=True)
log = []
for corpus, gate in GATES:
```

The diff does NOT show the loop body where `gate(case)` is called. The original code (pre-diff) presumably had a try/except around the gate call. The diff only changes the router construction. So the question is: **does the existing harness code (not shown in the diff) catch `ValueError` and re-raise as `GateNotMeasured`?**

The module docstring (lines 5–8) says: "A gate that could not MEASURE ... RAISES GateNotMeasured, which the harness counts as an ERROR." This implies the **gate functions** are responsible for raising `GateNotMeasured`, not the harness. The `vo_fidelity` function is the gate. If it raises `ValueError`, the harness would see an unhandled `ValueError`, not `GateNotMeasured`.

**This is a real bug.** The test `test_an_unreadable_case_is_the_harness_error_never_a_guess` will **fail** because `vo_fidelity` raises `ValueError` (from `universe_levels` or the title check) instead of `GateNotMeasured`. The fix is to wrap the title validation and `universe_levels` call in a try/except that converts `ValueError` to `GateNotMeasured`.

**Qwen3.8-27B's finding on `float(m["start"])` in `build`:** Qwen flagged that `m["start"]` could be `None` or non-numeric, causing an unhandled `ValueError`/`TypeError` in `build`. Looking at the diff line 320:
```python
ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
```
This is inside the `build` function's loop over `fine.items()`. If `m["start"]` is `None`, `float(None)` raises `TypeError`. This is **not caught** by any try/except in the shown diff. However, the `caption_evidence` function's own try/except (line 140–156) would catch it **if** the exception occurred inside `caption_evidence`. But `float(m["start"])` is evaluated **before** the call to `caption_evidence`, so the `TypeError` propagates out of `build`. **This is a real bug** — an unhandled exception in the build path.

**Qwen's finding on `E._parse_time` being private:** Calling `E._parse_time` from `moments_gate_adapter.py` is a code smell (using another module's private function), but it's not a functional bug. The function exists and works. This is a `<medium>` maintainability concern, not a correctness issue.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict |
|---|---|---|
| `universe_levels` raises `ValueError`, not `GateNotMeasured` | GLM-5.3-Flash | **AGREE — this is a real bug.** The test at line 448–455 will fail. `vo_fidelity` must convert `ValueError` to `GateNotMeasured`. |
| Missing `import hashlib` in `spotlight.py` | Grok-4.20 | **DISAGREE — refuted.** `import hashlib` is already at module scope (diff line 104, context line). |
| `float(m["start"])` unhandled in `build` | Qwen3.8-27B | **AGREE — real bug.** `TypeError`/`ValueError` propagates out of `build` uncaught. |
| `caption_evidence` counting after guard | GLM, Qwen | **AGREE with the fix.** The diff moves counting inside the try/except (lines 140–156), which is correct. |
| `next_attempt` filter for unmarked episodes | GLM (H66) | **AGREE with the fix.** The diff at lines 218–237 correctly handles unmarked episodes. |
| `SENTENCE_SPLIT` regex | Nobody flagged | **No issue.** The regex `(?<=[.!?])\s+|\n+` is standard sentence splitting. |
| `make_router` default limit $5.00 | Nobody flagged | **No issue.** Matches the orchestrator's ruling. |
| Cache key includes evidence hash | Qwen | **No issue.** Correctly prevents stale cache hits when evidence changes. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1. `universe_levels` line 64: `universe["built_at"]` uses subscript, but `universe` could be a dict without `built_at`.**
```python
now = E._parse_time(universe["built_at"])
```
If `universe` is `{"news": []}` (no `built_at` key), this raises `KeyError`, not `ValueError`. The test at line 450 includes `v11(universe={"news": []})` and expects `GateNotMeasured`. A `KeyError` is not a `ValueError`, so even if we fix the `ValueError`→`GateNotMeasured` conversion, the `KeyError` will still propagate unhandled. **The fix must catch both `ValueError` and `KeyError`** (or use `universe.get("built_at")` and check for `None`).

**N2. `universe_levels` line 67: `universe["news"]` uses subscript.**
```python
if not isinstance(universe["news"], list):
```
Same issue: if `universe` has no `news` key, `KeyError`. The test at line 450 includes `v11(universe={"news": []})` which has `news`, but a universe with only `built_at` and no `news` would crash. Use `universe.get("news")`.

**N3. `caption_evidence` line 148: `u[2]` assumes 3-tuple.**
```python
opens = [t for t, u in zip(times, units) if u[2]]
```
If a unit is a 2-tuple `(time, text)`, `u[2]` raises `IndexError`. This is **inside** the try/except (line 140–156), so it's caught and returns `{"measured": False, ...}`. **This is correct fail-closed behavior.** No bug.

**N4. `build` line 320: `float(m["start"])` and `float(m["end"])` are evaluated before `caption_evidence` is called.**
As noted above, if `m["start"]` is `None` or a non-numeric string, the exception is not caught. The fix: wrap the `float()` calls in a try/except, or pass `m["start"]` and `m["end"]` as-is and let `caption_evidence` handle the conversion (it already does `float(u[0])` for caption times, but the `start`/`end` parameters are used directly in the `changes_near` calculation at line 152).

**N5. `layout_for` line 273: `evidence_text(evidence)` is called with `evidence=None` by default.**
```python
def layout_for(router, m, vrec, cache_path=None, seed=7, evidence=None):
    ...
    ev_text = evidence_text(evidence)
```
`evidence_text(None)` returns `"the captions could not be read (no evidence either way)."` (line 169–170). This is correct — if no evidence is provided, the judge sees "no evidence." No bug.

**N6. `source_test` line 185: `markers_refuse(evidence)` is called with `evidence` that could be `None`.**
```python
def source_test(evidence, layout):
    if markers_refuse(evidence):
```
`markers_refuse(None)` → `ev = None or {}` → `ev.get("measured") is True` → `False`. Correct. No bug.

**N7. `next_attempt` line 236: the filter logic.**
```python
conv = [x for x in sts if x["unmarked"] or not (isinstance(x["turns_per_min"], (int, float)) and
                                                x["turns_per_min"] <= 0)]
```
This keeps an episode if it's unmarked OR if it's not (a number ≤ 0). So a marked episode with `turns_per_min=0.0` is excluded (correct: marked with zero turns is out). A marked episode with `turns_per_min=0.4` is kept (correct: the layout decides). An unmarked episode with `turns_per_min=0.0` is kept (correct: unknown, not solo). **This is correct.**

**N8. `universe_levels` line 71: `E.age_hours(item.get("published_at"), now)`.**
If `item` is not a dict (e.g., a string), `item.get` raises `AttributeError`. This is **not caught** by any try/except in `universe_levels`. The test at line 441–442 includes `unreadable = dict(fresh, published_at="yesterday")` which is a dict, so `item.get` works. But a malformed news list with non-dict items would crash. **This is a `<medium>` robustness issue** — the function should guard against non-dict items.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `moments_gate_adapter.py` (R-29) | 7/10 | **5/10** | `ValueError`/`KeyError` not converted to `GateNotMeasured`; test will fail. `universe["built_at"]` and `universe["news"]` use subscript instead of `.get()`. |
| `spotlight.py` (Ruling 92 amended) | 8/10 | **7/10** | `float(m["start"])` in `build` is unhandled. Otherwise the evidence/refusal logic is sound. |
| `make_router` / exam config | 9/10 | **9/10** | No issues. Correctly implements the orchestrator's ruling. |
| `next_attempt` (Ruling 95) | 8/10 | **8/10** | The unmarked-episode fix is correct. No new issues. |
| Tests | 8/10 | **6/10** | `test_an_unreadable_case_is_the_harness_error_never_a_guess` will fail due to the `ValueError`/`KeyError` issue. Other tests are well-constructed. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:**
1. **`moments_gate_adapter.py:89–94`** — `vo_fidelity` raises `ValueError` (from title check) and `KeyError`/`ValueError` (from `universe_levels`) instead of `GateNotMeasured`. The test `test_an_unreadable_case_is_the_harness_error_never_a_guess` (line 448–455) will **fail**. Fix: wrap the title validation and `universe_levels` call in a try/except that catches `ValueError` and `KeyError` and re-raises as `GateNotMeasured`.
2. **`moments_gate_adapter.py:64,67`** — `universe["built_at"]` and `universe["news"]` use subscript. If the key is missing, `KeyError` is raised. Fix: use `universe.get("built_at")` and `universe.get("news")`, and raise `ValueError` (or `GateNotMeasured`) if they are `None`.

**P1 HIGH:**
3. **`spotlight.py:320`** — `float(m["start"])` and `float(m["end"])` in `build` are evaluated before `caption_evidence` is called. If `m["start"]` is `None` or non-numeric, `TypeError`/`ValueError` propagates out of `build` unhandled. Fix: wrap in try/except, or pass raw values and let `caption_evidence` handle conversion.

**P2 MEDIUM:**
4. **`moments_gate_adapter.py:70–71`** — `universe_levels` does not guard against non-dict items in `universe["news"]`. `item.get("published_at")` will raise `AttributeError` if `item` is a string. Fix: add `if not isinstance(item, dict): continue`.
5. **`moments_gate_adapter.py:64`** — `E._parse_time` is a private function. Using it from another module is a maintainability risk. Consider adding a public wrapper in `eligibility.py`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Wrap the title validation and `universe_levels` call in `vo_fidelity` with a try/except that converts `ValueError` and `KeyError` to `GateNotMeasured`** — this is the one change that makes the R-29 test suite pass and ensures the harness correctly counts unreadable cases as ERRORs rather than letting them crash the exam.

## 7. PRODUCTION READY?

**No.**

**Conditions for shipping:**
1. Fix P0 items 1 and 2: `vo_fidelity` must raise `GateNotMeasured` (not `ValueError`/`KeyError`) for unreadable titles and universes. The test `test_an_unreadable_case_is_the_harness_error_never_a_guess` must pass.
2. Fix P1 item 3: `build` must not crash on `None` or non-numeric `m["start"]`/`m["end"]`.
3. Re-run the full test suite (20 suites, 559+ tests) and confirm all pass, including the new `test_exam_adapter.py` tests.
4. Verify that the harness (`run_exam_record.py`) does not have its own `ValueError`→`GateNotMeasured` conversion that would mask the bug (if it does, the P0 fix is still needed for correctness, but the test might pass by accident).