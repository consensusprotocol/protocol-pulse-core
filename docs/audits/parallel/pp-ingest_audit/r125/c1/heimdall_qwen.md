# heimdall_qwen (qwen/qwen3.8-27b, 184.4 s, $0.002, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT
**Target:** `pp-ingest` (r125)
**Scope:** `pipeline/ingest/fetch.py`, `tests/ingest/test_r125.py`, `tests/ingest/test_r120.py`
**Context:** Continuous ingest pipeline, live stream handling, transcript mining.

## SECTION 1: CORRECTNESS

**Verdict: CORRECT**

The logic implements the "r125" requirement precisely: a live stream row is made due *only* if a transcript record exists that was acquired *after* the last probe (`state_at`).

1.  **Time Comparison Logic (`fetch.py:246-250`):**
    *   `_zoned` correctly parses ISO 8601 strings, handling `Z` as UTC.
    *   It returns `None` for naive datetimes (no timezone).
    *   The condition `if got is None or probed is None or got <= probed: continue` ensures that:
        *   If either time is missing/invalid, the row is skipped (Fail Closed).
        *   If the record is older than or equal to the probe, the row is skipped (Prevents loops).
        *   Only if `got > probed` is the row added to `due`.
    *   This correctly prevents the "probe loop" described in the spec: once `process` runs, it updates `state_at` to `now`. The next sweep will see `record_time <= new_state_at` and skip it.

2.  **SQL Query (`fetch.py:238-241`):**
    *   The query selects rows where `state = Q.LIVE` AND `live_status IN ('post_live', 'is_live')`.
    *   Previously, `is_live` was excluded from the sweep (r120 invariant). Now it is included.
    *   The `next_at > ?` filter ensures we only touch rows that are *not* already due for their normal retry. This is correct; we are *accelerating* the retry, not replacing it.

3.  **Race Conditions:**
    *   The sweep reads `state_at` and `acquired_at`.
    *   `process` writes `state_at`.
    *   If `process` runs between the `SELECT` and the `UPDATE` in `pipeline_sweep`, the `UPDATE` uses `WHERE next_at > ?`.
    *   *Scenario:* Sweep selects row (next_at=100, state_at=T1). Process runs, sets next_at=100 (due), state_at=T2. Sweep updates `SET next_at=NOW WHERE next_at > NOW`. Since `100` is likely `< NOW` (assuming NOW is current time and 100 is a past timestamp or small number), the update might fail or be a no-op if `next_at` was already set to a value `<= NOW`.
    *   *Correction:* `next_at` is a timestamp. If the row was already due (`next_at <= NOW`), the sweep's `WHERE next_at > NOW` would have excluded it in the `SELECT`. So the sweep only selects rows where `next_at > NOW`.
    *   If `process` runs and sets `next_at` to `NOW + LIVE_REPROBE_S` (future), the sweep's `UPDATE ... WHERE next_at > NOW` will still match (since `NOW + 1200 > NOW`). It will set `next_at = NOW`. This is the intended behavior: make it due *now*.
    *   If `process` runs and sets `next_at` to `NOW` (immediate retry), the sweep's `UPDATE ... WHERE next_at > NOW` will **not** match (since `NOW` is not `> NOW`). The row remains due at `NOW`. This is also correct.
    *   **Conclusion:** The atomic `UPDATE` with the `WHERE` clause prevents double-processing or stale updates.

4.  **Edge Cases:**
    *   **Empty DB:** `rows` is empty, `due` is empty, no update. Safe.
    *   **Bad Input:** `_zoned` catches `TypeError`/`ValueError`. Safe.
    *   **Naive Datetimes:** `_zoned` returns `None`. Row skipped. Safe.

## SECTION 2: LAW COMPLIANCE

| Law | Status | Notes |
| :--- | :--- | :--- |
| **BUILD** | **COMPLIANT** | The change supports the "continuous ingest" and "first-pass mining" by ensuring live streams are probed promptly when transcripts land, adhering to the 10-minute ruling. |
| **L-x (No Single Model)** | **N/A** | This diff does not touch model selection or provider interfaces. |
| **L-l (Strict Schema)** | **COMPLIANT** | `_zoned` enforces strict parsing. If the time is not valid ISO 8601 with a zone, it returns `None` and the row is skipped. No "repair" of bad data. |
| **L-j / L-m (Fail Closed)** | **COMPLIANT** | If `acquired_at` or `state_at` is missing or invalid, the row is *not* made due. It waits for the normal re-probe. This is fail-closed behavior. |
| **L-h / L-k (Canonical Form)** | **N/A** | This diff does not touch transcript text processing. |
| **L-e (Word Timing)** | **N/A** | This diff does not touch timing data. |
| **L-u / L-v (Exclusions)** | **N/A** | This diff does not touch content filtering. |
| **Secrets** | **COMPLIANT** | No secrets are introduced or logged. |
| **SPEND FREEZE** | **COMPLIANT** | The sweep only triggers `process`, which probes YouTube (free) and checks the local transcript store. It does *not* trigger paid model calls directly. The mining happens later in the pipeline. The change ensures we don't *miss* the window for mining, but doesn't violate the freeze. |

## SECTION 3: SECURITY

1.  **SQL Injection:**
    *   `fetch.py:238-241`: Uses parameterized queries (`?`). Safe.
    *   `fetch.py:252-254`: `f"UPDATE ... WHERE video_id IN ({','.join('?' * len(due))})"`.
    *   `due` contains `video_id`s from the database. These are passed as parameters in the tuple `(now_ts, now_ts, ..., *due)`.
    *   **Safe.** The `IN` clause is constructed with placeholders, and the values are bound. No string interpolation of user input into the SQL string itself.

2.  **Authentication Bypasses:**
    *   N/A. This is a backend pipeline function, not an API route.

3.  **Rate Limiting:**
    *   The sweep runs every 60s. It makes at most one YouTube probe per row made due.
    *   The `WHERE next_at > ?` condition ensures we don't probe rows that are already due.
    *   The `got > probed` condition ensures we don't probe the same row repeatedly for the same record.
    *   **Compliant.**

4.  **Secrets in Code:**
    *   None found.

5.  **Unvalidated User Input:**
    *   `video_id` comes from the DB. `acquired_at` comes from the DB.
    *   `_zoned` validates the format.
    *   **Safe.**

## SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend pipeline change. No UI components are affected.

## SECTION 5: BACKEND QUALITY

1.  **DB Operations:**
    *   The `UPDATE` is a single statement. It is atomic.
    *   No explicit transaction is shown in the diff, but `q.x` likely handles the commit. Given the single-statement nature, this is acceptable.

2.  **External API Calls:**
    *   `pipeline_sweep` does *not* call external APIs. It only reads the DB and the local transcript store (`pipeline_transcript`).
    *   `process` (called later) handles the YouTube probe. The diff does not change `process`.

3.  **Cron Job Failure:**
    *   If `pipeline_sweep` throws an exception, it will propagate to the caller.
    *   The `try/except` around `pipeline_transcript` catches `ValueError`.
    *   Other exceptions (e.g., DB connection error) will crash the sweep. This is standard behavior for a pipeline step; the orchestrator should handle retries.

4.  **Memory Leaks:**
    *   `rows` is a list of DB records. It is bounded by the number of live streams.
    *   `due` is a list of IDs. Bounded.
    *   No large objects are created.

5.  **Logging:**
    *   The diff does not add logging.
    *   **Recommendation:** Add a log line when a row is made due by r125 logic. This will help debug why a stream was probed early.
    *   *Current State:* Silent. This is a minor gap.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Observability:**
    *   The r125 logic is subtle. A professional system would log: `r125: making {vid} due, record acquired at {got}, probed at {probed}`.
    *   Without this, debugging "why did this stream get probed at 09:32 instead of 09:40?" requires reading the code.

2.  **Resilience:**
    *   If `pipeline_transcript` is slow (e.g., disk I/O), the sweep will block.
    *   The spec mentions "bounded concurrency" for mining, but the sweep is sequential.
    *   For a small number of live streams, this is fine. If there are hundreds, it could be a bottleneck.
    *   *Gap:* No concurrency in the sweep.

3.  **Data Integrity:**
    *   The `state_at` field is critical. If it is ever `NULL` or invalid, the row is skipped.
    *   The code assumes `state_at` is always set by `Queue.set_state`.
    *   *Gap:* No validation that `state_at` is not `NULL` in the DB schema. If it is `NULL`, `_zoned` returns `None`, and the row is skipped. This is fail-closed, but might hide bugs.

## SECTION 7: SCORES

*   **Backend logic:** 95/100 (Correct, but lacks logging)
*   **Frontend/UI:** N/A
*   **Error handling:** 90/100 (Fail-closed, but silent)
*   **Security:** 100/100 (No vulnerabilities)
*   **Performance:** 85/100 (Sequential sweep, but acceptable for scale)
*   **Law compliance:** 100/100 (Strict adherence)
*   **World-class gap:** 80/100 (Missing observability)
*   **OVERALL:** 90/100

## SECTION 8: PRIORITY ACTION PLAN

**P1 HIGH** | Add logging for r125 triggers | `fetch.py:249` | Without logs, it is impossible to audit why a stream was probed early. Add `log.info(f"r125: {vid} due, acquired={got}, probed={probed}")`.

**P2 MEDIUM** | Validate `state_at` is not NULL | `fetch.py:246` | If `state_at` is NULL, `_zoned` returns None. This is fail-closed, but might indicate a bug in `Queue.set_state`. Add a warning log if `probed` is None.

**P3 LOW** | Consider concurrency for sweep | `fetch.py:238` | If the number of live streams grows, the sequential sweep could become a bottleneck. Use `concurrent.futures` to process rows in parallel.

## SECTION 9: THE ONE THING

**Add structured logging for every r125 trigger to make the "why" of early probes auditable.**

## SECTION 10: FINAL VERDICT

This code is **ready for production**. It correctly implements the r125 requirement with fail-closed behavior and no security vulnerabilities. The only gap is observability: add logging to make the r125 triggers auditable.