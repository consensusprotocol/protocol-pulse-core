# gemma-4-31b-it (google/gemma-4-31b-it) 280 s finish=stop usage in 6955 / out 6200 usd_reported=0.000984 usd~0.114 (upper-bound price)

The code implements a "clock-shift" hack to bypass a 12-hour expiry rule in the ingest adapter. While the arithmetic correctly tricks the expiry logic, it introduces a critical failure in the data retrieval window.

### [P0] Upper Bound Blind Spot
In `tests/package/proof_ledger.py` (line 27), the code defines `a_now = now - timedelta(hours=a.hours - base_h)` and passes this as the `now` argument to `LB.rows(since, a_now, horizon_h=a.hours)`.

In standard pipeline patterns (and specifically within the `ledger_build` / `ledger` logic referenced), the `now` argument serves two purposes:
1.  **The Expiry Reference:** It is used to calculate if a moment is too old (`published_at + 12h < now`).
2.  **The Query Ceiling:** It is used as the upper bound for the database query (`WHERE timestamp <= now`).

By shifting `a_now` back by 14 hours (when `--hours 26` is used), the code successfully makes a 25-hour-old moment appear 11 hours old (avoiding expiry). However, it simultaneously tells the adapter that the "current time" is 14 hours ago. Consequently, **every moment published within the last 14 hours is excluded from the results** because they fall after the `a_now` ceiling.

This is a catastrophic failure for a "fresh" pipeline. The "Must-produce" requirement for "today's $74K-pullback statements" will fail if those statements were published within the shifted window, as the most recent and relevant data is explicitly filtered out.

### [P2] Tautological Testing
The test in `tests/package/test_ruling_137.py` (lines 65-84) mocks `LB.rows` and asserts that the arguments passed to it are shifted. This tests the *implementation* (that the subtraction happened) rather than the *behavior* (that the correct rows are returned). Because the mock does not simulate the actual filtering logic of the adapter, it fails to catch the [P0] blind spot described above.

P1_OR_WORSE: 1