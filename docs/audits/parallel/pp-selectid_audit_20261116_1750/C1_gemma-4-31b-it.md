# gemma-4-31b-it (google/gemma-4-31b-it) 273 s finish=stop usage in 10767 / out 6114 usd_reported=0.001092 usd~0.124 (upper-bound price)

The code implements the requested `--only` and `--stop-usd` options for the build driver to restrict the moment pool and control spending.

### Analysis

1.  **`--only` Logic**: The implementation of `read_only` and `only_moments` correctly validates the JSON input (requiring non-empty `ids` and `why`), deduplicates the requested IDs while preserving order, and filters the `moments` pool before it reaches the variant generator. This ensures that only the specified moments are processed through the pipeline gates, satisfying the "one line-up at a time" requirement without skipping any quality gates.
2.  **`--stop-usd` Logic**: The `STOP_CEILING_USD` constant (1.25) is correctly enforced. The `limit` and `stop` values are properly propagated to the `Router` (to cap paid calls) and `start_refused` (to block the build from starting if the threshold is met). The `res["spend_ruling_48"]` record is updated to include these custom values for auditability.
3.  **Governing Laws**: The changes are confined to the build driver's orchestration layer. They do not modify the renderer, the selector, the canon, or any of the QA gates. Therefore, they do not violate any of the Governing Laws (Sentence Law, Selection Lock, etc.).
4.  **Test Coverage**: The new test class `TestOrder1750OneLineUpAtATime` covers the critical paths: invalid input handling, pool filtering/deduplication, and the spending stop mechanism.

### Findings

**[P1] Test-Code Mismatch on Validation Errors**
In `tests/package/proof_ledger.py`, the `main()` function raises a `ValueError` when `--only` or `--stop-usd` validation fails (lines 22, 82). However, the corresponding tests in `tests/package/test_ledger_build.py` (lines 172-175) assert that `PLG.main(...)` returns the integer `2`. 
Because `main()` raises an unhandled exception rather than returning `2`, these tests will crash with a `ValueError` instead of passing. The `main()` function needs to catch these validation errors and return `2`, or the tests must be updated to use `assertRaises`.

P1_OR_WORSE: 1