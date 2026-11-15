# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 9411 / out 3457 usd_reported=0.003875 usd~0.080 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 115 (1) follow-up). The change moves the hook calibration expiry from a hardcoded 24-hour constant to a file-driven `valid_h` field, allowing `null` for indefinite validity (specifically for the interim bar).

Here is my audit:

### Findings

**1. [P1] Type Check Vulnerability: `bool` is a subclass of `int`**
In `pipeline/hook_bar.py`, the validation for `valid_h` is:
```python
if type(vh) not in (int, float) or vh <= 0:
```
In Python, `bool` is a subclass of `int`. Therefore, `type(True)` is `bool`, which is **not** in `(int, float)`? Wait, `isinstance(True, int)` is `True`, but `type(True) is int` is `False`.
Let's check the code: `type(vh) not in (int, float)`.
If `vh` is `True`: `type(True)` is `bool`. `bool` is not `int` (it is a subclass, but `type()` returns the exact class). So `type(True) not in (int, float)` evaluates to `True`. The code **refuses** `True`.
If `vh` is `False`: `type(False)` is `bool`. Refused.
So the code correctly rejects booleans via the `type()` check.
*Correction*: The test suite explicitly tests `True` and expects it to be refused (line 138-140 in diff: `for bad in (0, -1, "24", True): ... self.assertIsNone(self.bar()[0], bad)`).
Since `type(True)` is `bool`, and `bool` is not in `(int, float)`, the condition `type(vh) not in (int, float)` is `True`, so it returns `None` (refused). This is correct behavior.
However, relying on `type()` exact match is brittle if someone passes a numpy integer or similar, but in this context (JSON load), it's safe.
**Wait**, let's look closer at the logic.
`if type(vh) not in (int, float) or vh <= 0:`
If `vh` is `True`: `type(True)` is `bool`. `bool` is not in `(int, float)`. Condition is True. Returns `None`. Correct.
If `vh` is `1`: `type(1)` is `int`. `int` is in `(int, float)`. Condition is False. Checks `1 <= 0` (False). Passes. Correct.
If `vh` is `1.0`: `type(1.0)` is `float`. Passes. Correct.
If `vh` is `"24"`: `type("24")` is `str`. Refused. Correct.

Is there a P1 here?
Actually, there is a subtle issue with `type(vh) not in (int, float)`.
If `vh` is a `numpy.int64` (unlikely from JSON, but possible if the file was manipulated or loaded via a different path), it would be refused. But `json.load` returns standard Python types.
The logic seems sound for the stated purpose.

**2. [P2] `valid_h` is not included in the SHA256 seal verification logic explicitly in the diff, but `load()` checks the whole file.**
The diff shows `hook_calibration.json` is re-sealed with a new SHA256 (`6978392...`). The `load()` function (not shown in diff, but referenced) checks the SHA256 of the file content. Since the file content changed (added `valid_h`), the SHA256 must match the new one. The diff updates the SHA256 in the JSON. This is consistent.

**3. [P2] Documentation/Comment Consistency**
The docstring in `hook_bar.py` line 35 says: `and is within its own "valid_h" (null: no expiry)`.
The code implements this.
The `hook_calibration.json` has `valid_h: null`.
The test `test_the_interim_bar_does_not_expire` verifies that `valid_h: null` allows the bar to be valid 30 days later.
This aligns with Ruling 115 (1).

**4. [P3] Nit: `valid_h_note` is not validated**
The `valid_h_note` field is added to the JSON. It is not used in the logic, only for documentation. This is fine.

**5. [P1] Potential Logic Gap: `valid_h` validation order**
In `bar()`:
```python
if "valid_h" not in cal:
    return None, "..."
vh = cal["valid_h"]
if vh is not None:
    if type(vh) not in (int, float) or vh <= 0:
        return None, "..."
    if age > timedelta(hours=vh):
        return None, "..."
```
If `vh` is `None`, it skips the type check and the age check. This is correct for "no expiry".
If `vh` is a number, it checks type and age.
This logic is correct.

**6. [P1] Missing Check: `valid_h` must be finite?**
If `valid_h` is `float('inf')`, `type(vh)` is `float`. `vh <= 0` is False. `age > timedelta(hours=inf)` is False. So it would be treated as "no expiry".
Is `inf` a valid JSON value? No, standard JSON does not support `Infinity`. `json.load` will raise an error or return `None`/`NaN` depending on `parse_constant`. By default, `json.load` raises `ValueError` for `Infinity`/`NaN` unless `parse_constant` is set.
If the file contains `Infinity`, `json.load` will fail, and `load()` will likely return `None` (fail closed).
So this is not a vulnerability.

**7. [P2] Test Coverage for `valid_h` in `bar()` return value**
The test `test_a_calibration_lasts_as_long_as_its_own_valid_h_says` checks `live["valid_h"]` is `None` when `valid_h` is `None`.
It does not explicitly check that `live["valid_h"]` is `24` when `valid_h` is `24`.
However, the code returns `"valid_h": vh`. This is a minor test gap, not a code defect.

**8. [P1] Critical: `type(vh) not in (int, float)` rejects `bool` correctly, but what about `numpy` types?**
As stated, JSON doesn't produce numpy types.

**9. [P1] Critical: The `VALID_H` constant is removed, but is it referenced elsewhere?**
The diff removes `VALID_H = 24.0` from `hook_bar.py`.
It updates `package.py` docstring.
It updates `test_hook_bar.py`.
Are there other references to `VALID_H` in the codebase?
The prompt says "Every new and modified file" is provided.
If `VALID_H` was imported elsewhere, it would break.
The diff shows `hook_bar.py` is the only place defining it.
`package.py` imports `hook_bar as HB` and calls `HB.bar()`. It does not reference `HB.VALID_H` directly in the diff.
The docstring in `package.py` is updated to say "its own valid_h".
So it seems safe.

**10. [P1] Critical: `valid_h` is not checked for being a number in the `load()` function?**
`load()` checks SHA256. It does not validate the schema of `valid_h`.
`bar()` validates `valid_h`.
This is consistent with the "fail closed" approach in `bar()`.

**11. [P2] Nit: `valid_h` can be a float like `24.5`.**
The code allows `float`. `timedelta(hours=24.5)` is valid.
This is fine.

**12. [P1] Critical: The `valid_h` field is not part of the "sealed" data in the same way?**
The SHA256 covers the whole file. So `valid_h` is sealed.
If someone modifies `valid_h` to `null` in a file that was sealed with `valid_h: 24`, the SHA256 will mismatch, and `load()` will refuse it.
This is correct.

**13. [P1] Critical: What if `valid_h` is `0`?**
`vh <= 0` is True. Refused.
Correct.

**14. [P1] Critical: What if `valid_h` is negative?**
`vh <= 0` is True. Refused.
Correct.

**15. [P1] Critical: What if `valid_h` is a string `"24"`?**
`type("24")` is `str`. Refused.
Correct.

**16. [P1] Critical: What if `valid_h` is `True`?**
`type(True)` is `bool`. Refused.
Correct.

**17. [P1] Critical: What if `valid_h` is `False`?**
`type(False)` is `bool`. Refused.
Correct.

**18. [P1] Critical: What if `valid_h` is missing?**
`"valid_h" not in cal` is True. Refused.
Correct.

**19. [P1] Critical: What if `valid_h` is `None`?**
`vh is not None` is False. Skips type/age check. Valid.
Correct.

**20. [P1] Critical: Is there any path where a calibration is valid forever by omission?**
No, missing key is refused.

**21. [P1] Critical: Is there any path where a calibration is valid forever by a bad value?**
No, bad values are refused.

**22. [P1] Critical: Does the change break the "once a day" law for the *standing* law?**
The standing law (Ruling 113 (2)) is measured against Ruling 115 (3)'s question version.
The current file is for Ruling 115 (1)'s interim bar.
The file has `valid_h: null`.
The standing law's calibration will have `valid_h: 24` (or similar).
The code supports both.
This is correct.

**23. [P1] Critical: Does the change break the `package._live_bar` cache?**
`package._live_bar` caches based on `mtime` and `minute`.
If the file changes, `mtime` changes, cache is invalidated.
If the file is the same, but time passes, the cache is invalidated every minute.
`bar()` is called with `now=datetime.now()`.
If `valid_h` is `null`, `bar()` returns valid regardless of age.
If `valid_h` is `24`, `bar()` returns invalid after 24h.
The cache in `package.py` stores the result of `bar()`.
If the result is `None` (invalid), it stores `None`.
If the result is valid, it stores the dict.
The cache key includes `int(time.time() // 60)`.
So every minute, it re-evaluates.
This is correct.

**24. [P1] Critical: Is there a race condition?**
`load()` reads the file. `bar()` uses the loaded dict.
If the file changes between `load()` and `bar()`, the `mtime` check in `package._live_bar` would have caught it if it was a new minute or mtime change.
But `bar()` is called directly in tests.
In production, `package._live_bar` is the entry point.
It checks `mtime` and `minute`.
If the file changes, `mtime` changes, cache is bypassed, `load()` is called again.
This is safe.

**25. [P1] Critical: Does the code handle `valid_h` being a very large number?**
`timedelta(hours=1e10)` is valid.
`age > timedelta(hours=1e10)` is False.
Valid.
This is fine.

**26. [P1] Critical: Does the code handle `valid_h` being a very small number?**
`timedelta(hours=0.0001)` is valid.
`age > timedelta(hours=0.0001)` is likely True.
Refused.
This is fine.

**27. [P1] Critical: Is the `valid_h` field documented in the JSON schema?**
The JSON has `valid_h_note`.
This is fine.

**28. [P1] Critical: Are the tests sufficient?**
The tests cover:
- `valid_h: 24` (valid at 23:59, invalid at 24:01)
- `valid_h: null` (valid at 30 days)
- `valid_h` missing (refused)
- `valid_h: 0, -1, "24", True` (refused)
- Live file `valid_h: null` (valid at 30 days)
This is sufficient.

**29. [P1] Critical: Is there any violation of the Governing Laws?**
- **SENTENCE LAW**: Not affected.
- **SELECTION LOCK**: Not affected.
- **SNAP LIMIT**: Not affected.
- **NEIGHBOUR**: Not affected.
- **ONSET/TAIL**: Not affected.
- **CREDITS**: Not affected.
- **L-a to L-l**: Not affected.
- **LAW 20 / M2**: Gate thresholds are constants. `valid_h` is a file field, not a gate threshold. The gate is `bar()`. The threshold is `valid_h`. This is allowed.
- **M12 FAIL CLOSED**: Missing data (`valid_h` missing) rejects. Model failure (N/A). Exception (N/A).
- **LAW 22**: Not affected.
- **Smallest diff**: The diff is small and focused.

**30. [P1] Critical: Is there any data loss?**
No.

**31. [P1] Critical: Is there any wrong result?**
No.

**32. [P1] Critical: Is there any gate passing what it must refuse?**
No.

**33. [P1] Critical: Is there any real defect that must be fixed before merge?**
I don't see any.

**34. [P2] Should fix:**
- The test `test_a_calibration_lasts_as_long_as_its_own_valid_h_says` could explicitly check that `live["valid_h"]` is `24` when `valid_h` is `24`.
- The docstring in `hook_bar.py` could be more explicit about `valid_h` being a file field.

**35. [P3] Nit:**
- The `valid_h_note` is long.

**Conclusion:**
The code is correct and compliant with the laws. The change is well-tested and fail-closed.

P1_OR_WORSE: 0