# qwen3.8-27b (qwen/qwen3.8-27b) 60 s finish=stop usage in 15732 / out 1972 usd_reported=0.003528 usd~0.077 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2049
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (implicitly, as the "consensus" author) identified the raw-string comparison issue as the primary P1. Both GLM and Qwen independently flagged this. I did not miss it, but I want to be precise about the *depth* of the fix verification:

- **GLM** correctly noted that the fix must use `canon.canon` (the integrator's canon, byte-identical) and that non-string readings should fail closed. The implemented `_canon` helper (line 59-63) does exactly this: `C.canon(x) or None` for strings, `None` otherwise. This is correct.
- **Qwen** correctly traced the specific case where `"86,000"` vs `"86000"` would fail raw-string comparison but pass canonically. The test `test_formatting_is_read_through_canon_on_both_sides` (line 291-300) now pins this.
- **GLM** also flagged the `adopt_spoken` gap (the re-check only ran for PASS, not adopt_spoken). The fix at line 37 (`out in PASS or out == "adopt_spoken"`) addresses this, and `test_an_adoption_that_rests_on_the_record_is_checked_too` (line 302-309) pins it.

I did not miss these; they were in my Cycle 1 consensus. However, I want to verify the fix is *complete* by re-reading the code.

## 2. WHERE DO YOU AGREE OR DISAGREE?

**GLM's P1 (raw-string comparison):** AGREE. The fix is correct. `_canon` is applied to `tok`, every `dt` element, and every `st` element. The truncation test runs on canonical forms. The digit test runs on the canonical form. This is exactly what law L-k requires.

**GLM's P2 (non-string readings):** AGREE, and the fix handles it. `_canon` returns `None` for non-strings. A `None` in `dt` or `st` will fail the stability check (`any(x != tok for x in dt)` where `tok` is a string) or the truncation check (`_truncation(None, tok)` returns False). This fails closed.

**Qwen's P1 (same as GLM's P1):** AGREE. Same finding, same fix.

**Qwen's P2 (truncation brittleness):** AGREE. The truncation logic is a heuristic that fails closed on unusual suffixes. This is acceptable per law M12 (fail closed). No change needed.

**Qwen's P3 (test coverage for non-dict entries):** AGREE. The tests cover this. `test_the_records_own_tests_and_verdict_must_agree` (line 327-338) tests non-object records.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] The `_canon` helper does not validate that `C.canon` returns a string.**

Line 63: `return (C.canon(x) or None) if isinstance(x, str) else None`

If `C.canon(x)` returns a non-string (e.g., an int, a list, or some other type), `_canon` will return that non-string. Then in `ruling_105_fails`:
- Line 87: `tok = _canon(u.get("token"))` — if `tok` is an int, `any(ch.isdigit() for ch in tok)` will raise `TypeError: 'int' object is not iterable`.
- Line 93: `any(x != tok for x in dt)` — if `dt` contains non-strings, the comparison is fine, but the truncation check will fail.

This is a **P2** because:
1. The integrator's `canon.canon` is documented to return a string (or None). If it returns a non-string, that is a bug in the integrator's canon, not this side.
2. This side fails closed in the sense that the exception will propagate and the pre-check will error, which is a hold.
3. However, the error message will be cryptic (`TypeError` instead of a clear "the token is not a number" message).

**Fix:** Add a type check in `_canon`:
```python
def _canon(x):
    if not isinstance(x, str):
        return None
    c = C.canon(x)
    return c if isinstance(c, str) else None
```

**[P3] The test `test_formatting_is_read_through_canon_on_both_sides` does not test the case where `C.canon` returns a non-string.**

This is a minor gap in test coverage. The test assumes `C.canon` returns a string. If the integrator's canon changes to return a non-string, this test will not catch it.

**[P3] The comment on line 60-62 is slightly misleading.**

The comment says: `'68,000' -> '68000', '401K' and '401(k)' -> '401k', 'forty-five' -> '45'`. This is correct, but it does not mention that `None` is returned for non-strings. The docstring on line 62 does mention this, but the inline comment does not.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `ruling_105_fails` logic | 8/10 | 9/10 | The fix for raw-string comparison is correct and well-tested. The only remaining issue is the P2 about `C.canon` return type, which is a minor edge case. |
| `decide()` integration | 7/10 | 9/10 | The `adopt_spoken` gap is fixed. The re-check now runs for both PASS and adopt_spoken. |
| Seal compatibility | 9/10 | 9/10 | No change. The seal is backward compatible, and the frozen pin is tested to recompute. |
| Test coverage | 8/10 | 9/10 | The new tests pin the canon fix and the adopt_spoken fix. The only gap is the P3 about `C.canon` return type. |
| Overall | 8/10 | 9/10 | The code is production-ready with one minor P2 fix. |

## 5. FINAL PRIORITY LIST

**[P2] `pipeline/lock_precheck.py` line 63: `_canon` does not validate that `C.canon` returns a string.**

If `C.canon(x)` returns a non-string, `_canon` will return that non-string, which can cause a `TypeError` in `ruling_105_fails`. Fix: add a type check in `_canon` to ensure the return value is a string.

**[P3] `tests/package/test_ruling_105.py` line 291-300: `test_formatting_is_read_through_canon_on_both_sides` does not test the case where `C.canon` returns a non-string.**

This is a minor gap in test coverage. Add a test case where `C.canon` returns a non-string (e.g., by mocking `C.canon` to return an int) and verify that the pre-check fails closed with a clear error message.

**[P3] `pipeline/lock_precheck.py` line 60-62: The inline comment does not mention that `None` is returned for non-strings.**

The docstring on line 62 does mention this, but the inline comment does not. Add a note to the inline comment.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fix for the raw-string comparison (using `canon.canon` for all token comparisons) is the highest-leverage change. It ensures that this side's re-check is consistent with the integrator's logic, preventing unnecessary holds on valid content.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** Fix the P2 issue in `_canon` (line 63) to ensure that `C.canon` returns a string. This is a minor fix that can be done in one line.

**Rationale:** The code is well-tested, the logic is correct, and the seal is backward compatible. The only remaining issue is a minor edge case that can be fixed quickly.

P1_OR_WORSE: 0