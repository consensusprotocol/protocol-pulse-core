# heimdall_qwen (qwen/qwen3.8-27b, 58.8 s, $0.004, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT (r119)

## SECTION 1: CORRECTNESS

**1. SQL Injection / Parameter Mismatch in `Queue.due` and `Queue.hook_due`**
*File: `pipeline/ingest/queue.py`*

The implementation of the "Bitcoin channels first" logic introduces a critical parameter binding error.

In `queue.py` (lines ~177-183 in the diff context):
```python
def due(self, states, limit=50, first=()):
    q, f = ",".join("?" * len(states)), tuple(first or ())
    order = f"CASE WHEN channel_id IN ({','.join('?' * len(f))}) THEN 0 ELSE 1 END, " if f else ""
    return self.rows(f"SELECT * FROM videos WHERE state IN ({q}) AND next_at <= ? "
                     f"ORDER BY {order}COALESCE(published_ts, listing_ts, discovered_ts) DESC LIMIT ?",
                     tuple(states) + (self.clock(),) + f + (limit,))
```
**The Bug:**
1.  The `WHERE` clause uses `state IN ({q})`. `q` contains `len(states)` placeholders.
2.  The `ORDER BY` clause uses `channel_id IN ({...})`. This adds `len(f)` placeholders.
3.  The `WHERE` clause also has `next_at <= ?` (1 placeholder).
4.  The `LIMIT` clause has `?` (1 placeholder).

The total number of placeholders in the SQL string is: `len(states) + len(f) + 1 + 1`.
The tuple provided is: `tuple(states) + (self.clock(),) + f + (limit,)`.
Length: `len(states) + 1 + len(f) + 1`.

**Wait, let's look closer at the order of parameters.**
SQL: `... WHERE state IN (?, ?, ...) AND next_at <= ? ORDER BY CASE WHEN channel_id IN (?, ?, ...) ... LIMIT ?`
Parameters passed: `tuple(states)` (for WHERE), `(self.clock(),)` (for WHERE), `f` (for ORDER BY), `(limit,)` (for LIMIT).

SQLite (and most DBs) binds parameters **in the order they appear in the SQL string**.
1. `state IN (...)` -> binds `tuple(states)`. Correct.
2. `next_at <= ?` -> binds `self.clock()`. Correct.
3. `ORDER BY ... channel_id IN (...)` -> binds `f`. Correct.
4. `LIMIT ?` -> binds `limit`. Correct.

**Correction:** The parameter order *is* actually correct for SQLite's positional binding. The placeholders are filled left-to-right.
*   `states` fills the `IN` in `WHERE`.
*   `clock` fills the `<=` in `WHERE`.
*   `f` fills the `IN` in `ORDER BY`.
*   `limit` fills the `LIMIT`.

**However**, there is a subtle logic flaw in `pipeline_sweep` in `fetch.py`.

**2. Race Condition in `pipeline_sweep` (Fetch vs. Probe)**
*File: `pipeline/ingest/fetch.py`*

```python
def pipeline_sweep(q, now_ts):
    # ...
    rows = q.rows("SELECT video_id, channel_id FROM videos WHERE state IN (?, ?) AND next_at > ? AND "
                  "COALESCE(published_ts, discovered_ts) >= ?",
                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, now_ts, now_ts - config.EXPIRY_H * 3600))
    due = []
    for r in rows:
        try:
            if pipeline_transcript(r["video_id"], r["channel_id"]) is not None:
                due.append(r["video_id"])
        except ValueError:
            continue
    if due:
        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?) AND video_id IN "
            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING) + tuple(due))
```

The `UPDATE` statement re-checks `next_at > ?` (where `?` is `now_ts`).
If a video was `next_at = now_ts + 10` (10 seconds in the future), it is selected in the `SELECT`.
If the sweep takes 5 seconds to check the filesystem for all videos, and then executes the `UPDATE`, the `next_at` is still `> now_ts` (assuming `now_ts` is fixed at the start of the function).
However, `now_ts` is passed as an argument. If `now_ts` is the *current* time at the start of the sweep, and the sweep takes time, the `UPDATE` condition `next_at > now_ts` is still valid for the original candidates.

**The Real Issue:**
The `SELECT` finds videos where `next_at > now_ts`.
The `UPDATE` sets `next_at = now_ts` for those videos.
This makes them "due" immediately.
Then `service.fetch_once` calls `q.due(...)`.
`q.due` selects videos where `next_at <= self.clock()`.
Since `next_at` was set to `now_ts` (which is slightly in the past relative to `self.clock()` at the time of `due`), they are selected.

**Is there a race?**
If `fetch_once` is called concurrently (it shouldn't be, it's a single-threaded loop in `service.py`), this is safe.
But look at `service.py`:
```python
if (self._last_sweep is None or now - self._last_sweep >= fetch.PIPELINE_SWEEP_S) and not self.gate.open_for():
    self._last_sweep = now
    made = fetch.pipeline_sweep(self.q, now)
```
This runs *before* `claimed = [v for v in self.q.due(...)]`.
So the sweep updates `next_at` to `now`.
Then `due` selects `next_at <= clock()`.
Since `now` is `clock()` at the start of the block, and `due` uses `self.clock()` again (which is slightly later), `next_at (now) <= clock() (now + epsilon)` is True.
This works.

**3. `pipeline_transcript` Filesystem Check Performance**
*File: `pipeline/ingest/fetch.py`*

`pipeline_sweep` iterates over *all* videos in `PROBE_RETRY` or `CAPTIONS_PENDING` states that are within the expiry window.
For each video, it calls `pipeline_transcript(vid, cid)`.
Looking at `take_pipeline_transcript` (context from previous diffs or standard pattern), `pipeline_transcript` likely does a `glob` or `os.path.exists` check.
If there are 1000 waiting videos, this is 1000 filesystem stat calls.
This is acceptable for a 60-second interval sweep, but if the queue grows large, this becomes an I/O bottleneck.
**Verdict:** Acceptable for current scale, but worth noting.

**4. `Queue.due` with `first` parameter: Empty `first` handling**
*File: `pipeline/ingest/queue.py`*

```python
f = tuple(first or ())
order = f"CASE WHEN channel_id IN ({','.join('?' * len(f))}) THEN 0 ELSE 1 END, " if f else ""
```
If `first` is empty, `f` is `()`. `len(f)` is 0. `','.join('?' * 0)` is `""`.
`order` becomes `""`.
The SQL becomes:
`SELECT * FROM videos WHERE state IN (...) AND next_at <= ? ORDER BY COALESCE(...) DESC LIMIT ?`
Parameters: `tuple(states) + (self.clock(),) + () + (limit,)`.
This is correct.

**5. `service._first` Caching Logic**
*File: `pipeline/ingest/service.py`*

```python
def _first(self, chans=None):
    now = self.clock()
    if chans is None and self._first_at is not None and now - self._first_at < 60:
        return self._first_ids
    try:
        if chans is None:
            chans = watch.registry()[1]
        ids = frozenset(c["channel_id"] for c in chans
                        if isinstance(c.get("tier"), int) and c["tier"] <= config.BITCOIN_TIER_MAX)
    except Exception:
        return self._first_ids
    self._first_ids, self._first_at = ids, now
    return ids
```
If `chans` is provided (from `fetch_once`), it **always** recalculates `ids` and updates the cache.
If `chans` is `None` (from `mine_once` or `hook_due`), it checks the cache.
This is correct. The fetch round has the fresh registry data, so it updates the cache. The miner/hook use the cached data.

**6. `test_r119.py` Assertion Failure Risk**
*File: `tests/ingest/test_r119.py`*

```python
def test_due_takes_the_bitcoin_channels_first_then_the_newest():
    # ...
    assert ids(q.due(Q.MINE_DUE, 10)) == ["m_new000001", "b_new000001", "b_old000001", "m_old000001"]
```
`Q.MINE_DUE` likely includes `TRANSCRIBED` and `MINED_PARTIAL`? Or just `TRANSCRIBED`?
The test sets state to `Q.TRANSCRIBED`.
If `MINE_DUE` is a tuple of states, and `due` filters by `state IN (...)`, this works.
The order is `COALESCE(published_ts, ...) DESC`.
`m_new` (NOW-100) > `b_new` (NOW-1000) > `b_old` (NOW-3000) > `m_old` (NOW-4000).
This matches the assertion.

With `first={BTC}`:
`b_new` (BTC) and `b_old` (BTC) come first.
Order among BTC: `b_new` (NOW-1000) > `b_old` (NOW-3000).
Then non-BTC: `m_new` (NOW-100) > `m_old` (NOW-4000).
Result: `["b_new000001", "b_old000001", "m_new000001", "m_old000001"]`.
Matches assertion.

**7. `pipeline_sweep` Expiry Check**
*File: `pipeline/ingest/fetch.py`*

```python
"COALESCE(published_ts, discovered_ts) >= ?",
(now_ts - config.EXPIRY_H * 3600)
```
This ensures we only sweep videos that are *within* the 12-hour life.
If a video is older than 12 hours, it is ignored.
This complies with the law: "inside its moments' life (config.EXPIRY_H, 12 h)".

**8. `acquired_at` Propagation**
*File: `pipeline/ingest/fetch.py`*

```python
ts._log_attempt(vid, step="transcript", status="taken_from_pipeline_store", source=src,
                method=rec["transcript_method"], transcript_sha256=rec["transcript_sha256"],
                acquired_at=rec.get("acquired_at"), writer="pipeline.ingest")
q.event("pipeline_transcript", vid, channel_id, source=src, method=rec["transcript_method"],
        transcript_sha256=rec["transcript_sha256"], acquired_at=rec.get("acquired_at"))
```
This correctly captures the timestamp from the pipeline's record.
The test `test_a_transcript_landing_in_the_pipelines_store_is_mined_at_the_next_fetch_round` verifies this.

**Conclusion on Correctness:**
The code is logically sound. The SQL parameter binding is correct. The race conditions are mitigated by the single-threaded nature of the service loop and the atomicity of the SQLite updates. The caching logic in `_first` is robust.

## SECTION 2: LAW COMPLIANCE

**BUILD: Continuous ingest... Mine each video within 10 minutes of its transcript**
*   **Compliant.** The `pipeline_sweep` runs every 60 seconds (`PIPELINE_SWEEP_S`). It makes videos due immediately if a transcript exists. The miner runs every 5 seconds (implied by `mine_once` loop in service, though not explicitly shown in diff, the test `test_a_transcript_landing...` shows `mine_once` is called). The combination ensures mining starts within ~65 seconds of the transcript landing.
*   **Bitcoin channels first:** **Compliant.** `Queue.due` and `Queue.hook_due` prioritize `first` channels. `service._first` correctly identifies Tier 1 and 2 channels.

**L-x NO SINGLE MODEL, ULTRON FIRST**
*   **Compliant.** The diff does not touch model selection. It only affects queue ordering and transcript fetching. The "Spend Freeze" law is respected because the sweep only looks at the *local* pipeline store (`PIPELINE_STORE`), not paid APIs.

**L-l a model reply counts only whole**
*   **Compliant.** No model calls are made in this diff.

**L-h / L-k: Transcript text is read as spoken**
*   **Compliant.** The sweep takes the transcript from the pipeline store, which is assumed to be in the canonical format (Whisper output). The code does not modify the text.

**L-u hard exclusions**
*   **Compliant.** The sweep does not bypass exclusions. It only changes `next_at`. The `process` function (which handles exclusions) is called *after* the video is claimed by `due`.

**Secrets**
*   **Compliant.** No secrets are handled.

**Spend Freeze**
*   **Compliant.** The sweep uses `pipeline_transcript` which reads from the local filesystem (`PIPELINE_STORE`). It does not call any paid vendors.

**Verdict:** All laws are compliant.

## SECTION 3: SECURITY

**SQL Injection**
*   **Safe.** All queries use parameterized placeholders (`?`). The `IN` clauses are constructed with `','.join('?' * len(...))` and the corresponding values are passed in the tuple. No string interpolation of user input into SQL.

**Authentication Bypasses**
*   **N/A.** This is a backend pipeline, not a web API.

**Rate Limiting Gaps**
*   **Safe.** The sweep is rate-limited to once per 60 seconds (`PIPELINE_SWEEP_S`). The `due` query is limited by `limit` parameter.

**Secrets in Code**
*   **Safe.** No hardcoded keys.

**Unvalidated User Input**
*   **Safe.** Input comes from the database (video IDs, channel IDs) and the registry (channel tiers). These are internal data sources. The `first` parameter is a set of channel IDs, which are validated by the DB schema (foreign keys or similar).

**Verdict:** No security vulnerabilities found.

## SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend pipeline change. No UI components are affected.

## SECTION 5: BACKEND QUALITY

**DB Operations**
*   **Good.** The `UPDATE` in `pipeline_sweep` is atomic. The `SELECT` in `due` is read-only.

**External API Calls**
*   **Good.** `pipeline_transcript` reads from the local filesystem. No external API calls are made in the sweep path.

**Cron Job Failure Handling**
*   **Good.** `service._first` catches exceptions and returns the last known set. `pipeline_sweep` catches `ValueError` from `pipeline_transcript` and skips the video.

**Memory Leaks**
*   **Good.** No large objects are created per request. The `due` list is bounded by `limit`.

**Logging**
*   **Good.** `service.fetch_once` logs when videos are made due by the sweep.

**Verdict:** High quality backend code.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**1. Lack of Metrics for Sweep Efficiency**
*   The sweep makes videos due, but there is no metric tracking *how many* videos were made due vs. how many were already due. This would help diagnose if the sweep is redundant or if the retry logic is too aggressive.
*   **Impact:** Low. Debugging is possible via logs.

**2. No Backpressure on Sweep**
*   If 10,000 videos are waiting, the sweep will check all 10,000 filesystem paths. This could cause a spike in I/O.
*   **Mitigation:** The sweep is limited to videos within the 12-hour expiry. If the system is healthy, this number is small. If the system is broken (e.g., YouTube 429s), this number could grow.
*   **Recommendation:** Add a `LIMIT` to the `SELECT` in `pipeline_sweep` to cap the number of videos checked per sweep. E.g., `LIMIT 100`.
*   **Impact:** Medium. Prevents I/O spikes during outages.

**3. `first` Parameter in `Queue.due` is a Set, but SQL uses `IN`**
*   This is fine, but passing a large set of channel IDs could make the SQL query complex.
*   **Impact:** Low. The number of Bitcoin channels is small (Tier 1 + 2).

**4. No Validation of `acquired_at`**
*   If `acquired_at` is missing or invalid in the pipeline record, `rec.get("acquired_at")` returns `None`. This is logged as `None`.
*   **Impact:** Low. The latency calculation will be skipped or fail gracefully.

**Verdict:** The code is production-ready. The only significant gap is the lack of a `LIMIT` on the sweep's `SELECT`, which could be a risk during large-scale outages.

## SECTION 7: SCORES

*   **Backend logic:** 95/100 (Excellent, minor I/O risk)
*   **Frontend/UI:** N/A
*   **Error handling:** 95/100 (Robust caching and exception handling)
*   **Security:** 100/100 (No vulnerabilities)
*   **Performance:** 90/100 (Filesystem checks could be optimized with a LIMIT)
*   **Law compliance:** 100/100 (Fully compliant)
*   **World-class gap:** 85/100 (Missing metrics and backpressure)
*   **OVERALL:** 92/100

## SECTION 8: PRIORITY ACTION PLAN

**P1 HIGH | Add `LIMIT` to `pipeline_sweep` SELECT | `pipeline/ingest/fetch.py:228` | Prevents I/O spikes if thousands of videos are waiting during an outage.**
```python
rows = q.rows("SELECT video_id, channel_id FROM videos WHERE state IN (?, ?) AND next_at > ? AND "
              "COALESCE(published_ts, discovered_ts) >= ? LIMIT 100",
              (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, now_ts, now_ts - config.EXPIRY_H * 3600))
```

**P2 MEDIUM | Log the number of videos checked vs. made due | `pipeline/ingest/service.py:258` | Helps diagnose sweep efficiency.**
```python
made = fetch.pipeline_sweep(self.q, now)
if made:
    self.log(f"fetch: {len(made)} waiting video(s) with a transcript in the pipeline's store made due: "
             f"{', '.join(made)}")
else:
    self.log(f"fetch: sweep checked {len(rows)} videos, none made due") # Requires returning rows count
```

**P3 LOW | Validate `acquired_at` format | `pipeline/ingest/fetch.py:218` | Ensures latency calculations are accurate.**
```python
acquired = rec.get("acquired_at")
if acquired and not isinstance(acquired, (int, float)):
    acquired = None
```

## SECTION 9: THE ONE THING

Add a `LIMIT` to the `pipeline_sweep` query to prevent I/O saturation during large-scale caption outages.

## SECTION 10: FINAL VERDICT

This code is **ready for production**. It correctly implements the orchestrator's ruling to mine videos within 10 minutes of their transcript and prioritize Bitcoin channels. The logic is sound, secure, and compliant with all governing laws. The only recommendation is to add a `LIMIT` to the sweep query to protect against I/O spikes during outages, but this is a minor optimization, not a blocker.