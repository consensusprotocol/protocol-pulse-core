# qwen3.8-27b (qwen/qwen3.8-27b) 53 s finish=stop usage in 10421 / out 1843 usd_reported=0.002753 usd~0.059 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1750
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (implicitly, as the baseline) likely focused on the logical flow of the `--only` filter and the `--stop-usd` validation. I missed the **operational nuance** regarding the "one call from its seal" exception.

*   **Mimo** correctly identified that the Order's "unless a package is one call from its seal" clause is not implemented in the code. I initially dismissed this as a "Ruling 122" issue, but Mimo correctly pointed out it is part of the *Order* text. However, the **Consensus** clarified that this is handled *operationally* (by re-running with a higher cap), not *code-wise*. I missed the distinction between "code must implement the exception" vs "operator implements the exception via re-run."
*   **Gemma** raised a P1 about `main()` raising `ValueError` vs returning `2`. I missed verifying the exception handling block in `main()`. The Consensus confirmed that `main()` *does* catch `ValueError` and return `2`, so Gemma was wrong, but I failed to verify this myself in Cycle 1.
*   **Mimo** also flagged the empty pool scenario (`--only` with all IDs missing). I missed that this results in a "successful" build with 0 moments, which is misleading.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma's P1 (ValueError vs Return 2):** **DISAGREE.** The code in `main()` (lines 403-436 in the full file, implied by the diff context) wraps the argument parsing and initial validation in a `try/except ValueError` block that prints "REFUSED" and returns `2`. The tests pass because the exception is caught. Gemma was looking at the `read_only` function in isolation, not the `main` wrapper.
*   **Mimo's P1 (Missing "one call from seal" exception):** **PARTIALLY AGREE.** The code *does* implement a hard stop. The "exception" is not in the code. However, the Consensus states this is by design (operator re-runs with `--stop-usd 1.00`). Therefore, this is **not a code defect**, but a **documentation/operational gap**. I agree it's not a P1 code bug, but it is a P2 documentation issue.
*   **Mimo's P2 (Empty Pool):** **AGREE.** If `--only` specifies IDs that don't exist in the pool, `kept` is empty. The build proceeds, logs "0 of N listed moments," and produces no output. This is a "silent success" which is bad UX and potentially confusing for the orchestrator. It should refuse or warn loudly.
*   **Mimo's P3 (Boundary Test 1.25):** **AGREE.** The tests check `1.26` (fail) but not `1.25` (pass). This is a minor test gap.
*   **Qwen's Analysis:** **AGREE.** Qwen correctly identified that `--only` does not skip gates and that the wiring is sound. Qwen's "P1" headings were actually checks it answered itself, so its count of 0 P1s is correct.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `--only` with all IDs missing yields a "successful" empty build.**
In `only_moments` (line 30-33), if `kept` is empty, the function returns `([], record)`. In `main` (line 91), `moments` is set to `[]`. The build continues. The log says "0 of N listed moments." The build completes with no packages. This is misleading. It should either:
1.  Refuse with exit 2 if `kept` is empty (strict).
2.  Log a WARNING and continue (lenient).
Given the "Fail Closed" principle (M12), refusing is safer. If the operator made a typo in the IDs, they don't want a "successful" no-op build.

**[P3] `read_only` error message uses Python dict syntax.**
Line 22: `raise ValueError(f"--only {path}: needs {{'ids': [moment ids], 'why': text}}")`. The file is JSON. The error message should say `needs {"ids": [...], "why": "..."}`. This is a cosmetic issue but could confuse operators.

**[P3] No test for `--only` combined with `--from-candidate`.**
The diff does not show any interaction between `--only` and `--from-candidate`. If both are provided, `--only` filters the pool *after* `--from-candidate` selects the line-up? Or does `--from-candidate` select from the *original* pool? The code shows `only_moments` is called *after* `inputs` are built (which includes `from_candidate` logic). This means `--only` filters the *already selected* line-up. This is likely correct (you want to filter the specific line-up you're trying), but it's untested.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `--only` Logic | 9/10 | 8/10 | Downgraded for the "empty pool silent success" issue. |
| `--stop-usd` Logic | 9/10 | 9/10 | No change. Wiring is correct. |
| Tests | 8/10 | 8/10 | No change. Missing boundary test and empty pool test. |
| Error Handling | 9/10 | 9/10 | Confirmed `main()` catches `ValueError` correctly. |

## 5. FINAL PRIORITY LIST

**[P2] `--only` with all IDs missing should refuse or warn.**
*   **File:** `tests/package/proof_ledger.py`
*   **Line:** 91-93 (in `main`)
*   **Fix:** After `moments, inputs["only"] = only_moments(...)`, check `if not moments: raise ValueError(f"--only: none of the listed moments are in the pool")`. This will be caught by `main`'s `try/except` and result in exit 2.

**[P3] Add test for `--stop-usd 1.25` boundary.**
*   **File:** `tests/package/test_ledger_build.py`
*   **Line:** 174-175
*   **Fix:** Add `self.assertEqual(PLG.main(["--delivered", *self.pins(), "--stop-usd", "1.25"]), 0)` (or equivalent, ensuring it doesn't refuse).

**[P3] Fix `read_only` error message to use JSON syntax.**
*   **File:** `tests/package/proof_ledger.py`
*   **Line:** 22
*   **Fix:** Change `{{'ids': ...}}` to `{"ids": ...}`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a refusal in `main()` if `--only` results in an empty pool, to prevent "silent success" no-op builds that waste operator time and confuse the audit trail.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the P2: `--only` with all IDs missing must refuse (exit 2) or log a critical warning.
2.  Add the P3 test for `--stop-usd 1.25` boundary.

The core logic is sound. The `--only` filter correctly preserves pool order and does not skip gates. The `--stop-usd` wiring correctly updates the Router limit and start refusal threshold. The "one call from seal" exception is handled operationally, which is acceptable given the Consensus.

P1_OR_WORSE: 0