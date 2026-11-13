# qwen3.8-27b (qwen/qwen3.8-27b) 65 s finish=stop usage in 6218 / out 2428 usd~0.055 (upper-bound price)

# Audit: pp-selectid_audit_1138b / C1_STEP.diff

## Findings

### P1-1: `sc.get` on a non-dict `sc` raises `AttributeError` inside the `except` handler (File: `pipeline/package.py`, diff lines 26–30)

The `except` block is intended to be a fail-closed sink that *never* raises. However, the new diagnostic code calls `sc.get(...)` unconditionally inside the `except` handler:

```python
except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
    return {}, {"read": False, "why": f"{stage}: {type(e).__name__}: {str(e)[:160]}", "path": path,
                "render_scorer_sha": code_sha,
                **({k: sc.get(k) for k in ("kind", "event", "scorer_sha", "threshold")}
                   if isinstance(sc, dict) else {})}
```

The guard `if isinstance(sc, dict) else {}` protects the *dict comprehension*, but it does **not** protect the `sc.get` call itself if `sc` is a non-dict, non-None object that was successfully assigned before the exception.

**Concrete scenario:**
1. `json.load(f)` succeeds, so `stage = "parse"` is set.
2. `sc = d["scorer"]` succeeds, so `stage = "shape"` is set. Suppose `d["scorer"]` is a **string** (e.g., `"scorer": "moments"`). `sc` is now a `str`.
3. `vs = d["verdicts"]` raises `KeyError` (or any other exception in the tuple).
4. Control enters the `except` block.
5. `isinstance(sc, dict)` is `False`, so the dict comprehension is skipped. **However**, the code as written in the diff is:
   ```python
   **({k: sc.get(k) for k in ...} if isinstance(sc, dict) else {})
   ```
   Wait — re-reading the diff carefully: the `isinstance(sc, dict)` check *is* present. If `sc` is a `str`, `isinstance(sc, dict)` is `False`, so the comprehension is **not** evaluated, and `sc.get` is **not** called. The `else {}` branch is taken.

   Let me re-examine. The expression is:
   ```python
   **({k: sc.get(k) for k in ("kind", "event", "scorer_sha", "threshold")}
      if isinstance(sc, dict) else {})
   ```
   Python evaluates the condition `isinstance(sc, dict)` first. If `False`, it evaluates `{}` and never touches `sc.get`. So `sc.get` is **not** called when `sc` is not a dict.

   **Correction:** The `isinstance` guard *does* prevent `sc.get` from being called on a non-dict. The `AttributeError` risk I initially identified is **not present** in the code as written.

   However, there is a subtler issue: what if `sc` is a dict-like object that is *not* a `dict` (e.g., a `collections.defaultdict` or a custom mapping)? `isinstance(sc, dict)` would be `False` for a `defaultdict`? No — `defaultdict` is a subclass of `dict`, so `isinstance` returns `True`. A custom `Mapping` that is not a `dict` subclass would return `False`, and `sc.get` would not be called. This is safe.

   **Verdict on P1-1: Retracted.** The `isinstance(sc, dict)` guard correctly prevents `sc.get` from being called on non-dict values. No exception can escape the `except` handler due to `sc.get`.

### P2-1: `stage` variable is set to `"open"` before the `try` block, but the `open()` call is inside the `try` (File: `pipeline/package.py`, diff lines 9–12)

```python
stage, sc = "open", None
try:
    with open(path) as f:
        stage = "parse"
        d = json.load(f)
```

This is correct: if `open()` raises, `stage` is still `"open"`. If `json.load()` raises, `stage` is `"parse"`. If `d["scorer"]` or `d["verdicts"]` raises, `stage` is `"shape"`. The stage tracking is accurate. No issue.

### P2-2: The `why`-chain path (diff lines 31–33) does not include `path` or `render_scorer_sha` in the record

The `except` branch now records `path` and `render_scorer_sha`, but the `if why:` branch (lines 31–33) does not:

```python
if why:
    return {}, {"read": False, "why": why, "kind": sc.get("kind"), "event": sc.get("event"),
                "scorer_sha": sc.get("scorer_sha"), "render_scorer_sha": code_sha, "threshold": sc.get("threshold")}
```

It does include `render_scorer_sha` (as `code_sha`), but not `path`. This is a minor inconsistency in diagnostic completeness between the two failure paths. The `except` branch records `path`; the `why`-chain branch does not. This is a P2 (cosmetic/diagnostic completeness), not a correctness issue.

### P2-3: Test at diff line 45 asserts `rec["why"].startswith("open: FileNotFoundError")`

This is correct for a missing file. The `open()` call raises `FileNotFoundError`, `stage` is `"open"`, and the `why` string is `"open: FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/latest.json'"`. The `startswith` check is valid.

### P2-4: Test at diff lines 46–51 (missing `"verdicts"` key)

```python
odd_shape = self.file()
with open(odd_shape, "w") as f:
    json.dump({"scorer": {"kind": "moments", "event": None, "scorer_sha": "s" * 64, "threshold": 3.5}}, f)
idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)
self.assertEqual((idx, rec["kind"], rec["scorer_sha"]), ({}, "moments", "s" * 64))
self.assertTrue(rec["why"].startswith("shape: KeyError"))
```

This tests the `except` branch when `d["verdicts"]` raises `KeyError`. `stage` is `"shape"`, `sc` is a dict, so the scorer fields are included. The test asserts `rec["kind"]` and `rec["scorer_sha"]` are present. This is correct and verifies the new diagnostic fields.

However, note that the test does **not** assert `rec["path"]` or `rec["render_scorer_sha"]` for this case. The missing-file test (line 43–44) does assert those. Minor test coverage gap, but not a defect.

### P2-5: Unicode test at diff lines 59–62

```python
import hashlib
t = "And Bitcoin\u2019s caf\u00e9 \u2014 na\u00efve \u201choldlers\u201d win \U0001F680"
self.assertTrue(package_pin.affirmed_verdict({"approved_text": t, "scorer_verdict": sv(t, 4.0)}))
self.assertEqual(PK.text_sha(t), hashlib.sha256(t.encode("utf-8")).hexdigest())
```

This verifies that `PK.text_sha` produces the same SHA-256 as a direct `hashlib.sha256(t.encode("utf-8")).hexdigest()` for a string with curly quotes, accents, an em dash, and an emoji. This is a valid test for the glm P2-2 concern. The `affirmed_verdict` call confirms the pin accepts the verdict for this text. No issue.

### P2-6: No test for the `except` branch when `sc` is a non-dict (e.g., a string)

The tests cover:
- Missing file (`stage = "open"`)
- Missing `"verdicts"` key with valid `scorer` dict (`stage = "shape"`)
- Malformed JSON (`stage = "parse"`, implied by the existing test at line 52–54)

But there is no test for the case where `d["scorer"]` is a non-dict (e.g., a string) and `d["verdicts"]` is missing. This would exercise the `isinstance(sc, dict) else {}` branch. While the code is correct (as analyzed in P1-1), the lack of a test for this edge case is a minor gap.

## Summary

| Severity | File:Line | Finding |
|----------|-----------|---------|
| P2 | `pipeline/package.py:31-33` | `why`-chain path does not record `path` in the diagnostic record, unlike the `except` branch. Minor inconsistency. |
| P2 | `tests/package/test_medley.py:46-51` | Test for missing `"verdicts"` key does not assert `rec["path"]` or `rec["render_scorer_sha"]`. Minor coverage gap. |
| P2 | `tests/package/test_medley.py` | No test for `except` branch when `sc` is a non-dict (e.g., string). The code is correct, but the edge case is untested. |

**No P0 or P1 findings.** The fail-closed property is preserved: the `except` branch returns `{}` as the first element of the tuple in all cases. No exception can escape the `except` handler. The `isinstance(sc, dict)` guard correctly prevents `sc.get` from being called on non-dict values.

## SHIP: yes with conditions

Conditions:
1. Add `path` to the `why`-chain diagnostic record (line 31–33) for consistency with the `except` branch.
2. Add a test for the `except` branch when `d["scorer"]` is a non-dict (e.g., a string) to verify the `isinstance` guard works as intended.
3. Optionally, assert `rec["path"]` and `rec["render_scorer_sha"]` in the missing-`"verdicts"` test for completeness.

These are minor diagnostic/test improvements, not correctness blockers. The core fail-closed behavior is sound.