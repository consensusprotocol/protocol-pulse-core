# gpt-oss-20b (openai/gpt-oss-20b) 133 s finish=stop usage in 6172 / out 21608 usd_reported=0.002869 usd~0.343 (upper-bound price)

**Findings**

| # | Issue | Severity | Explanation |
|---|-------|----------|-------------|
| 1 | `package_pin.WINDOW_H` is widened in `main()` but never restored | **P2** | If `main()` is invoked more than once in the same process (e.g., during a long‑running service or a test suite that re‑uses the same interpreter), the widened window will persist and affect subsequent runs. The code currently relies on the caller to reset the value, which is fragile. |
| 2 | `a_now = now - timedelta(hours=a.hours - base_h)` can produce a future time when `a.hours < base_h` | **P2** | The logic assumes `a.hours` is always ≥ `base_h`. If a caller passes a smaller value (e.g., due to a bug or a future change in defaults), the subtraction becomes negative, causing `a_now` to be later than `now`. This would incorrectly advance the ingest adapter’s clock and could allow moments that should be excluded. |
| 3 | Test patches `PLG.PS.ledger_entries` to a lambda that returns `[]` | **P3** | While `main()` currently does not call `ledger_entries`, the patch could hide side‑effects if the implementation changes. The test is therefore fragile to future code changes. |
| 4 | Test uses `mock.patch('sys.stdout')` without a context manager | **P3** | The patch suppresses output but does not restore it automatically. In a larger test suite this could affect other tests that rely on `stdout`. |
| 5 | Test compares `back` with a tolerance of `0.05` h (~3 min) | **P3** | The tolerance is generous but acceptable; tightening it would make the test more precise without affecting correctness. |
| 6 | Test’s custom `rows` function raises `Past` to stop `main()` early | **P3** | The test verifies only the clock calculation; it does not assert that the rest of `main()` behaves correctly. This is acceptable for the current intent but could miss regressions in other parts of the function. |
| 7 | Test calculates `back = (t0 - now).total_seconds() / 3600` where `now` is `a_now` | **P3** | The calculation is correct but could be confusing because `now` is not the same as the `now` inside `main()`. Clarifying variable names would improve readability. |

**P1_OR_WORSE: 0**