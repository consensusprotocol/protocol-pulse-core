# qwen3.8-27b (qwen/qwen3.8-27b) 45 s finish=stop usage in 6527 / out 1614 usd~0.044 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-1138b

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core safety mechanism (the `isinstance` guard) but failed to fully trace the **control flow** of the `why` chain relative to the `try` block.

*   **GLM-5.3-FLASH** correctly flagged the ambiguity in the diff regarding whether the `why` chain (lines 18–23) was inside or outside the `try`. It correctly deduced that for the new test case (`{"scorer": ["moments"], ...}`) to result in a `shape: AttributeError` record, the `sc.get` call *must* be inside the `try` block. If it were outside, the exception would crash the function rather than being caught.
*   **QWEN3.8-27B** initially raised a false positive (P1-1) about `sc.get` raising an error in the `except` block, then correctly retracted it after realizing the `isinstance` guard prevents evaluation. This was a good "sanity check" that the guard works as intended.
*   **GROK-4.20** was too brief; it missed the nuance of the *new* test case added in this increment (the non-dict scorer) and didn't explicitly verify that the `AttributeError` from `sc.get` on a list is caught by the `except` tuple.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM:** The `why` chain is inside the `try`. The new test at line 52–56 proves this: it writes a file where `scorer` is a list. `sc = d["scorer"]` succeeds (line 16). `vs = d["verdicts"]` succeeds (line 17). Then line 18 `sc.get("kind")` raises `AttributeError` because `sc` is a list. This is caught by the `except` at line 26. The record is generated with `stage="shape"` (set at line 15) and `why` starting with `shape: AttributeError`. The `isinstance(sc, dict)` guard at line 30 correctly evaluates to `False`, so the dict comprehension is skipped, and no `sc.get` is called in the `except` block.
*   **Agree with QWEN:** The `isinstance` guard is sufficient. There is no risk of `sc.get` escaping the `except` block.
*   **Disagree with GROK (implicitly):** "No findings" is too strong. While there are no *code* defects, there is a **test coverage gap** that was addressed in this increment. The previous cycle's consensus noted a missing test for non-dict scorers. This increment *adds* that test. Therefore, the "finding" is now resolved, but the audit must verify the resolution.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: Test Fragility on `self.file()`**
*   **File:** `tests/package/test_medley.py:46`
*   **Scenario:** The test calls `odd_shape = self.file()`. If `self.file()` requires arguments or has side effects that depend on prior state, this could fail. However, given this is a standard unittest pattern in this codebase (seen in other tests), it is likely safe. **Verdict:** Low risk, but worth noting if `self.file()` is not a simple temp-file generator.

**P2-2: `why` String Length Truncation**
*   **File:** `pipeline/package.py:27`
*   **Scenario:** `str(e)[:160]` truncates the exception message. If the `FileNotFoundError` path is very long, the end of the path might be cut off. However, the `path` is now recorded separately in the record (line 27), so the full path is available. The `why` string is for human-readable summary. **Verdict:** Acceptable. The separate `path` key mitigates the loss of information.

**P2-3: Non-ASCII Test Coverage**
*   **File:** `tests/package/test_medley.py:65-67`
*   **Scenario:** The test verifies that `PK.text_sha(t)` matches `hashlib.sha256(t.encode("utf-8")).hexdigest()` for a string with curly quotes, accents, and an emoji. This is a good regression test for encoding issues. It also checks `affirmed_verdict` accepts it. **Verdict:** Good addition. No issues.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Fail-Closed Logic** | 9/10 | 10/10 | Verified that the `except` block cannot raise. The `isinstance` guard is robust. The `why` chain is correctly inside the `try`. |
| **Diagnostic Quality** | 7/10 | 9/10 | The new `stage`, `path`, and `render_scorer_sha` fields significantly improve debuggability. The `why` string is now more informative. |
| **Test Coverage** | 6/10 | 9/10 | The missing test for non-dict `scorer` (the exact case the guard protects) has been added. The non-ASCII test is a nice bonus. |
| **Code Clarity** | 8/10 | 8/10 | The split of `sc, vs = ...` into two lines is slightly verbose but necessary for the `stage` tracking. Acceptable. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    1.  `tests/package/test_medley.py:46`: Verify `self.file()` is a no-arg temp file generator. (Likely safe, but confirm).
    2.  `pipeline/package.py:27`: The `why` string truncation is mitigated by the separate `path` key, but ensure downstream consumers don't rely on the `why` string containing the full path. (Unlikely, but check).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the `stage` variable and the split assignment of `sc` and `vs` is the highest-leverage change. It transforms the error handling from a "black box" (just the exception type) to a "white box" (exactly where and what failed), which is critical for debugging integrator issues in production.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  Confirm that `self.file()` in the test suite is a standard no-argument temporary file generator (standard in this codebase).
2.  Ensure that any downstream consumers of the `rec` dictionary are aware of the new keys (`stage`, `path`, `render_scorer_sha`) and do not break if they are present. (Since this is an additive change, it should be safe).

**SHIP: yes**