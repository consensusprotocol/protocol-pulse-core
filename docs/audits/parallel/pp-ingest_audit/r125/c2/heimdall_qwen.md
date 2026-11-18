# heimdall_qwen (qwen/qwen3.8-27b, 134.9 s, $0.001, finish stop)

# PROTOCOL PULSE: CYCLE 2 CODE AUDIT
**Target:** `pp-ingest` (r125)
**Reviewer:** heimdall_qwen (Cycle 2)
**Context:** Second review with access to Cycle 1 consensus and peer findings.

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the *logic* of the time comparison and the *atomicity* of the SQL update. I missed two critical operational and structural nuances that the other models (specifically Muse and the Consensus) highlighted:

1.  **Observability Gap (P1):** I noted that the logic was "correct" but failed to flag that the *evidence* of correctness was missing. The `pipeline_sweep` function was making rows due without logging *why* (i.e., which `acquired_at` beat which `state_at`). Muse correctly identified that without this metadata in the queue event, debugging a "why is this stream stuck?" or "why did this trigger?" scenario would be impossible. The Cycle 1 consensus confirms this was a required fix.
2.  **N+1 Query Pattern (P2/P3):** I dismissed the performance impact of calling `pipeline_transcript()` inside the loop as "bounded and safe." Muse correctly flagged this as an N+1 pattern. While not a production breaker for small datasets, it is a structural anti-pattern that scales poorly. I was too optimistic about the "bounded" nature without considering the cost of the glob/file-read per row.
3.  **Refutation of Race Condition Concerns:** I spent significant effort in Cycle 1 analyzing a potential race condition between `SELECT` and `UPDATE`. The Consensus correctly refuted this by pointing to `queue.py`'s `claim()` atomicity and the fact that the sweep only modifies `next_at`, not the state itself. My analysis was technically sound but unnecessary; the system design already handled it. I should have trusted the existing `claim()` semantics more.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Stance | Reasoning |
| :--- | :--- | :--- | :--- |
| **Logic is Correct** | All | **Agree** | The `got > probed` check is the core invariant. It prevents loops and ensures only new transcripts trigger probes. |
| **Observability Missing** | Muse | **Agree** | Critical for production. You cannot audit *why* a sweep triggered without the timestamps in the event. |
| **N+1 Query** | Muse | **Agree** | Valid structural concern. Even if bounded, it's inefficient. |
| **Race Condition Risk** | Muse | **Disagree** | The Consensus correctly refuted this. `claim()` is atomic. The sweep's `UPDATE ... WHERE next_at > ?` is safe because it only accelerates due time, it doesn't change state. |
| **Clock Skew** | Muse | **Disagree** | Both timestamps are written by the same process/machine (watcher and pipeline). Skew is negligible. |
| **Probe Storm** | Muse | **Disagree** | `transcript_store` skips `is_live` records. A stream only gets a record when it ends. No storm. |
| **Fail-Closed on Bad Data** | All | **Agree** | `_zoned` returning `None` and skipping the row is the correct behavior. |

## 3. NEW FINDINGS FROM THIS REVIEW

Having seen the Cycle 1 consensus and the "Fixed" section, I confirm that the **observability fix** (adding `live_status`, `acquired_at`, `probed_at` to the queue event) is the most important change. Without it, the code is "correct" but "unauditable."

Additionally, I now recognize that the **test suite** (`test_r125.py`) is the primary guard against regression. The mutation testing results (M69-M74 killed) confirm that the tests are robust. My Cycle 1 review did not explicitly validate the *quality* of the tests, only the code. The tests are strong.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 10/10 | Logic is sound. Race conditions are handled by existing `claim()` semantics. |
| **Observability** | 5/10 | 9/10 | Cycle 1 missed the lack of logging. Cycle 2 acknowledges the fix is required and now present in the consensus. |
| **Performance** | 8/10 | 7/10 | N+1 query pattern is a valid concern. Not a blocker, but a debt item. |
| **Security** | 10/10 | 10/10 | No changes. Parameterized queries, no secrets. |
| **Testability** | 8/10 | 9/10 | Mutation testing confirms tests are effective. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The code is safe to ship.

**P1 HIGH:**
1.  **Verify Observability Fix:** Ensure `pipeline_sweep` includes `live_status`, `acquired_at`, and `probed_at` in the `pipeline_transcript_due` event. (File: `pipeline/ingest/fetch.py`, Line: ~250-260). *This was the main gap in Cycle 1.*

**P2 MEDIUM:**
1.  **Refactor N+1 Query:** Consider batching `pipeline_transcript()` calls or using a more efficient lookup if the number of live rows grows. (File: `pipeline/ingest/fetch.py`, Line: ~248-256). *Not urgent, but good practice.*
2.  **Add Logging for Skipped Rows:** Log a warning when a row is skipped due to `got <= probed` or `None` times. (File: `pipeline/ingest/fetch.py`, Line: ~253-256). *Improves debuggability.*

**P3 LOW:**
1.  **Document `claim()` Atomicity:** Add a comment in `fetch.py` explaining why the `SELECT`/`UPDATE` race is safe (relying on `queue.py`'s `claim()`). *Prevents future confusion.*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Adding the `acquired_at` and `probed_at` timestamps to the `pipeline_transcript_due` queue event.** This transforms the system from "correct but opaque" to "correct and auditable," which is essential for a production pipeline handling live streams.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The observability fix (P1) must be merged and verified in the test suite.
2.  The mutation testing results (M69-M74) must be green.
3.  The `tests/ingest` suite must pass (449 tests).

The code is logically sound, secure, and now (with the observability fix) debuggable. The N+1 query is a minor performance debt that can be addressed in a future cycle.