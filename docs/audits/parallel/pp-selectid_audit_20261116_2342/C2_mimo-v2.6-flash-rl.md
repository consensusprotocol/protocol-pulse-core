# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 207 s finish=stop usage in 8770 / out 20504 usd_reported=0.002160 usd~0.334 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-20261116_2342

---

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

Gemma's Cycle 1 review was thorough on all five audit dimensions and correctly identified the replay rule compliance, writer exclusion, contract/parsing, integration/fallbacks, and test coverage as sound. The Claude consensus correctly dismissed qwen's [P2] staging base_url finding and confirmed the mutation testing results (8/8 killed, 863 tests).

**What neither caught:** The `parse` function validates the *structure* of the verdict dict but never checks that `through_line` is a `str`. This is a real crash path I missed in Cycle 1 as well — I was focused on the panel logic and didn't scrutinize the type validation inside `parse` closely enough.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| Gemma: Replay rule correct (majority, no-verdict, standard bar) | **Agree** | `sum(passes)*2 > len(answers)` is strictly-more-than-half; `len(votes) < min_members` returns `False, measured:False`; `lineup_floors("coherence", ...)` gives the standard bar. |
| Gemma: Writer exclusion correct | **Agree** | `names` filter + `avoid_family=others` (which unions `wf`) correctly isolates. |
| Gemma: Contract/parsing correct | **Partially agree** | Brace rule is correct, but `parse` misses `through_line` type check — see new P1 below. |
| Gemma: Integration/fallback correct | **Agree** | `coherence_panel_spec` returns `None` → single-rater path preserved. |
| Gemma: Test coverage comprehensive | **Mostly agree** | Missing writer *vendor* exclusion test (only family is tested). |
| Claude: qwen base_url P2 dismissed | **Agree** | All 5 Heimdall back-ends share that base_url; it's the gateway address. |
| Claude: 8/8 mutations killed, 863 tests | **Agree** | Consistent with the test file shown. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P1] `parse` does not validate `through_line` is a string → unhandled `AttributeError`

**File:** `pipeline/package.py`, lines ~144–149 (the `parse` closure inside `coherence`)

```python
def parse(text, braces=False):
    v = hook_answer(text)[0] if braces else json.loads(text.strip())
    if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
            not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
            any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
        raise ValueError("coherence verdict out of contract")
    return v
```

The validation checks keys, `clips` dict shape, and integer ranges for clip values and `vo_point` — but **never checks `isinstance(v["through_line"], str)`**. If a model returns `"through_line": 123` or `null`, `parse` passes it through. Later in `coherence_by_panel`:

```python
passes = lambda v: _line_ok(v["through_line"]) and ...
```

`_line_ok` calls `tl.strip()` → `AttributeError` on a non-string. The `except` clause in `coherence_by_panel` catches only `(P.ProviderError, P.SpendLimit, ValueError, TypeError)` — **`AttributeError` is not caught**. This crashes the panel evaluation with an unhandled exception.

**Fix:** Add `or not isinstance(v["through_line"], str)` to the validation condition.

---

### [P2] Clips dict omits `labs[0]` when `own` is None

**File:** `pipeline/package.py`, line ~124

```python
"clips": {**({labs[0]: own["rating"]} if own else {}),
          **{lb: statistics.median_low(...) for lb in labs[1:]}},
```

When `own` is `None` (no cached hook rating), `labs[0]` is absent from the clips dict. Downstream code at `:4069` (the redo/re-line reader) may expect `labs[0]` to exist and raise `KeyError`. The `ok` verdict is `False` in this case, but the verdict dict is still returned and read.

---

### [P2] `others` set can include current member's family if two members share a family

**File:** `pipeline/package.py`, line ~96

```python
others = {fams[o] for o in names if o != n} | wf
```

If members A and B both have family `"qwen"`, then for member A: `others` includes `fams[B] = "qwen"`, which is A's own family. The call would then avoid A's family, potentially routing to a different backend or failing. Current config has three distinct families so this doesn't trigger, but it's a latent bug.

---

### [P2] `lineup_floors` uses first sorted member without verifying Heimdall

**File:** `pipeline/package.py`, line ~115

```python
fl, which, csha = lineup_floors("coherence", sorted(votes)[0])
```

Comment says "a Heimdall member: the standard bar" but the code doesn't verify this. If a non-Heimdall member were added to the panel, the floors could be wrong. Latent bug.

---

### [P2] Missing test for writer vendor exclusion

**File:** `tests/package/test_medley.py`

`test_the_writers_family_is_never_asked` covers family exclusion, but no test verifies that a panel member with the writer's *vendor* is excluded. The code handles it (`router.backends[n].vendor not in wv`), but it's untested.

---

### [P3] `avoid_vendor` passed as raw parameter, not `wv`

**File:** `pipeline/package.py`, line ~101

`avoid_vendor=writer_vendor` passes the raw value while `wv = P._as_set(writer_vendor)` is computed but only used for the `names` filter. Functionally equivalent if `call_parsed` handles both types, but inconsistent.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Replay Rule Compliance | 9/10 | 9/10 | No change; rule correctly implemented |
| Writer Exclusion | 9/10 | 8/10 | Missing vendor exclusion test |
| Contract and Parsing | 9/10 | **7/10** | Missing `through_line` type check (P1) |
| Integration and Fallbacks | 9/10 | 9/10 | No change |
| Test Coverage | 9/10 | 8/10 | Missing vendor exclusion test |

---

## 5. FINAL PRIORITY LIST

**P1 HIGH:**
1. [P1] `pipeline/package.py`, line ~144: Add `isinstance(v["through_line"], str)` to `parse` validation to prevent unhandled `AttributeError`.

**P2 MEDIUM:**
1. [P2] `pipeline/package.py`, line ~124: Ensure `labs[0]` is always present in clips dict when `own` is None.
2. [P2] `pipeline/package.py`, line ~96: Guard against two panel members sharing a family in `others`.
3. [P2] `pipeline/package.py`, line ~115: Verify `sorted(votes)[0]` is a Heimdall member before `lineup_floors`.
4. [P2] `tests/package/test_medley.py`: Add writer vendor exclusion test.

**P3 NIT:**
1. [P3] `pipeline/package.py`, line ~101: Use `wv` instead of raw `writer_vendor` for `avoid_vendor`.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add `isinstance(v["through_line"], str)` to the `parse` function's validation to prevent an unhandled `AttributeError` crash when a model returns a non-string through-line.

---

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. Fix the P1: add `through_line` type validation in `parse` (one-line change).
2. Address or explicitly document the P2 findings — especially the missing `labs[0]` when `own` is None, which could cause a `KeyError` in downstream readers.

---

P1_OR_WORSE: 1