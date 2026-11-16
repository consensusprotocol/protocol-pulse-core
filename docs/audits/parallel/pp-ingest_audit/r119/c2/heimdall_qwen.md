# heimdall_qwen (qwen/qwen3.8-27b, 27.2 s, $0.002, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT (r119) — CYCLE 2

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I spent significant effort analyzing the parameter binding order in `Queue.due` and `pipeline_sweep`, ultimately concluding it was correct but flagging a potential race condition that turned out to be non-existent due to single-threaded execution. I also flagged the N+1 filesystem check as a performance concern.

**Heimdall_Muse** caught two specific issues I missed or under-weighted:
1.  **The `_first()` data race:** Muse correctly identified that `self._first_ids` and `self._first_at` are read/written without a lock. While I noted the GIL makes individual assignments atomic, I failed to explicitly flag the *check-then-act* race condition where two threads could both see `chans is None` and both call `watch.registry()`. Muse correctly classified this as "benign but technically a data race."
2.  **The "Empty `due` guard" verification:** Muse explicitly verified that `if due:` prevents the `IN ()` SQL syntax error. I assumed this was handled but did not explicitly verify the guard's presence in the diff context as rigorously.

**Heimdall_Qwen (Myself):** I was overly verbose in Cycle 1, spending tokens re-deriving the SQL parameter order. I missed the subtle point that `pipeline_transcript` *already* handles `OSError` internally, which refutes the "widen except" suggestion. I also failed to explicitly confirm that the `UPDATE` statement's re-check of `state IN` and `next_at >` is the *primary* race mitigation, not just a side effect.

**Claude's Consensus:** Correctly refuted my Cycle 1 P1 about adding a `LIMIT` to the sweep's `SELECT`. The consensus notes that the queue size is bounded by the 12-hour expiry window and the low volume of uploads (60-100/day), making a `LIMIT` unnecessary and potentially harmful (starving older items). I accept this refutation.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Position | Reasoning |
| :--- | :--- | :--- | :--- |
| **SQL Parameter Order in `Queue.due`** | Qwen (C1) | **Agree (Correct)** | My C1 analysis was correct: SQLite binds positionally. `states` -> `clock` -> `first` -> `limit`. No bug. |
| **Race Condition in `pipeline_sweep`** | Qwen (C1) | **Disagree (No Bug)** | The `UPDATE` re-checks `state` and `next_at`. Since `fetch_once` is single-threaded, there is no concurrent `claim` to race against. The sweep is safe. |
| **N+1 Filesystem Check** | Qwen (C1), Muse (C1) | **Agree (Acceptable)** | 200 globs every 60s is negligible for local FS. The 12h window bounds the queue size. Not a production blocker. |
| **`_first()` Data Race** | Muse (C1) | **Agree (Low Severity)** | Two threads calling `watch.registry()` is redundant but harmless. Last write wins. No corruption. |
| **`except ValueError` Scope** | Muse (C1) | **Agree (Correct)** | `pipeline_transcript` handles `OSError` internally. The sweep's `except ValueError` is specifically for `transcript_store` ID validation. Correct scope. |
| **`LIMIT` on Sweep SELECT** | Qwen (C1) | **Disagree (Refuted)** | Consensus is correct. Bounded queue size makes `LIMIT` unnecessary. |

## 3. NEW FINDINGS FROM THIS REVIEW

**3.1. `transcript_lag_s` Calculation Edge Case**
*File: `pipeline/ingest/queue.py` / `service.py`*

The new `transcript_lag_s` column is calculated as `now_ts - acquired_at`. If `acquired_at` is `NULL` (e.g., a video that was discovered but never had a transcript stored, or a legacy row), `COALESCE(acquired_at, 0)` or similar handling is critical. If `acquired_at` is `NULL`, `now_ts - NULL` is `NULL` in SQL. If the code does `row["acquired_at"]` in Python and it's `None`, `now_ts - None` raises `TypeError`.

*Check:* The diff shows `transcript_lag_s` is added to the queue row. I need to verify if `acquired_at` is guaranteed non-null for rows in `TRANSCRIBED` state. If a video is in `TRANSCRIBED` state, it *must* have a transcript record, so `acquired_at` should be set. However, if a row is manually inserted or corrupted, this could crash the mining loop. **Recommendation:** Ensure `acquired_at` is `COALESCE`d to `discovered_ts` or `0` in the SQL or Python layer to prevent `TypeError`.

**3.2. `watch.registry()` Exception Handling in `_first()`**
*File: `service.py`*

Muse noted that `_first()` returns the last known set on exception. This is good. However, if `watch.registry()` raises an exception *and* `self._first_ids` is `None` (first call), the code must handle the `None` case gracefully. If it returns `None`, `Queue.due` will receive `first=None`, which is handled by `tuple(first or ())`. This is safe.

**3.3. `PIPELINE_SWEEP_S` Throttle Logic**
*File: `service.py`*

The throttle is `if (self._last_sweep is None or now - self._last_sweep >= fetch.PIPELINE_SWEEP_S)`. If `pipeline_sweep` raises an exception, `_last_sweep` is *not* updated (it's set *before* the call in the diff? No, the diff shows `self._last_sweep = now` *before* `made = fetch.pipeline_sweep(...)`). Wait, let me re-read the diff context from Muse:

```python
if (self._last_sweep is None or now - self._last_sweep >= fetch.PIPELINE_SWEEP_S) and not self.gate.open_for():
    self._last_sweep = now
    made = fetch.pipeline_sweep(self.q, now)
```

If `pipeline_sweep` raises, `_last_sweep` is already set to `now`. The next sweep will be delayed by `PIPELINE_SWEEP_S` (60s). This is intentional to prevent tight retry loops on persistent failures. **Agree with Muse's assessment.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 9/10 | Confirmed no SQL injection, no race conditions in sweep. `_first()` race is benign. `transcript_lag_s` edge case is minor. |
| **Performance** | 7/10 | 8/10 | N+1 glob is acceptable. `_first()` cache is effective. No new performance bottlenecks. |
| **Security** | 9/10 | 9/10 | SQL is parameterized. No new vulnerabilities. |
| **Maintainability** | 8/10 | 8/10 | Code is clear. `_first()` logic is slightly complex but well-documented. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`transcript_lag_s` NULL Handling:** Ensure `acquired_at` is never `NULL` when calculating `transcript_lag_s` for rows in `TRANSCRIBED` state. If `acquired_at` is `NULL`, use `COALESCE(acquired_at, discovered_ts)` in the SQL or handle `None` in Python to prevent `TypeError` in the mining loop. *File: `pipeline/ingest/queue.py` or `service.py`.*

**P2 MEDIUM:**
1.  **`_first()` Data Race:** Add a lock around the read/write of `self._first_ids` and `self._first_at` to eliminate the technical data race, even if benign. *File: `service.py`.*
2.  **`pipeline_sweep` Exception Logging:** If `pipeline_sweep` raises, log the exception with context (video_id, channel_id) to aid debugging. Currently, it may be silently swallowed or logged generically. *File: `pipeline/ingest/fetch.py`.*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ensure `acquired_at` is non-NULL for all rows in `TRANSCRIBED` state before calculating `transcript_lag_s`, to prevent a `TypeError` crash in the mining loop.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Verify that `acquired_at` is always set for rows in `TRANSCRIBED` state. If not, add a `COALESCE` or default value to prevent `TypeError` in `transcript_lag_s` calculation.
2.  (Optional) Add a lock to `_first()` to eliminate the benign data race.

If condition 1 is met, the code is safe, correct, and performant for production.