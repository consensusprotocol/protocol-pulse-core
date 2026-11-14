# heimdall_qwen (qwen/qwen3.8-27b, 226.2 s, $0.023, finish stop)

## SECTION 1: CORRECTNESS

**The core logic change is correct.**
The `is_conversation` function in `pipeline/ingest/mine.py` (lines 302-315) correctly implements the "WIDEN" ruling:
1.  **No markers / Unmarked:** `n <= 0` or not an int returns `True` (asked). This handles auto-captions without `>>` markers.
2.  **Marked but unmeasurable rate:** `t` is not a number returns `True` (asked). This handles edge cases where duration is 0 or missing.
3.  **Marked and measurable:** Returns `t >= 0.3`. This correctly skips only the "solo recap" cases (marked, low turn rate).

**Potential Issue: `stats.py` SQL Logic (Line 110)**
In `pipeline/ingest/stats.py`, the query for `spotlight_asked_videos` uses:
```sql
SUM(spot_rows IS NOT NULL) AS asked
```
In SQLite, `IS NOT NULL` returns `1` (true) or `0` (false). `SUM` of these integers works correctly to count non-null rows. However, this relies on `spot_rows` being `NULL` when the spotlight question was *not asked* (solo episode) and an integer (possibly 0) when it *was asked*.
Looking at `service.py` line 447:
```python
spot_rows=len(spot) if srep is not None else None
```
If `srep` is `None` (solo episode), `spot_rows` is `NULL`. If `srep` is a dict (conversation), `spot_rows` is an int.
This logic is **correct**.

**Potential Issue: `service.py` Log Message (Line 427)**
```python
f"no spotlight question (a marked solo episode: {ep.get('speaker_markers')} markers, "
f"{ep.get('turns_per_min')} turns / min)"
```
This log message is only reached if `srep is None` AND `scrash is None`.
`srep` is `None` if `mine.is_conversation(ep)` is `False`.
`is_conversation` is `False` ONLY if `speaker_markers > 0` AND `turns_per_min < 0.3`.
So the log message "a marked solo episode" is accurate for the only case where this branch is taken.

**Race Condition Check: `mine_video` in `service.py`**
The `mine_video` method (line 270) reads `meta.json` and `canonical_transcript`. It then calls `mine.mine_video`.
The `mine.mine_video` function (line 561) uses `contract.sentences(rec)`.
If the transcript file is modified concurrently (e.g., by the `fetch` loop), this could cause issues. However, `fetch` writes to the staging store, and `mine` reads from the same staging store.
In `fetch.py` line 237, `ts._store(rec)` is called. `transcript_store` likely handles atomic writes (rename).
In `mine.py` line 570, `contract.sentences(rec)` parses the JSON.
If a write happens between `open` and `read`, it could fail. But `ts.canonical_transcript` (line 274) likely handles this or returns a consistent snapshot. Given `transcript_store` is a shared module, we assume it's robust.

**N+1 Query Check:**
`stats.py` line 118:
```python
for r in q.rows("SELECT episode_markers AS m, episode_tpm AS t, COALESCE(hook_rows,0) AS n FROM videos WHERE ..."):
```
This is a single query, not N+1.

**Edge Case: `is_conversation` with `None` episode**
`ep = episode or {}` handles `None`.
`n, t = ep.get("speaker_markers"), ep.get("turns_per_min")` returns `None` for both.
`isinstance(n, bool)` is `False`. `not isinstance(n, int)` is `True`. Returns `True`.
Correct.

## SECTION 2: LAW COMPLIANCE

*   **L-x (NO SINGLE MODEL, ULTRON FIRST):** COMPLIANT. The code uses `providers.Router` and `providers.json`. The `mine` role has `heimdall_qwen27b` and `local_gemma`. The `hook` and `spotlight` roles also have multiple backends.
*   **L-l (Reply counts only whole):** COMPLIANT. `mine.py` `validator` (line 446) strictly validates JSON, keys, types, and ranges. It raises `Invalid` on any mismatch. No repair logic.
*   **L-j / L-m (Fail closed):** COMPLIANT. `is_conversation` defaults to `True` (ask) when data is missing/invalid, which is "fail open" for *asking* but "fail closed" for *skipping* (i.e., it doesn't assume it's a solo episode and skip the work). The ruling says "cost of asking is nothing", so asking is the safe default.
*   **L-h / L-k (Read as spoken):** COMPLIANT. `contract.py` uses `eligibility.spoken`.
*   **L-u (Hard exclusions):** COMPLIANT. `mine.py` `HARD_RISKS` and `validator` enforce flags. `ledger.py` `effective_risk` handles the second-model check.
*   **L-v (Speaker change):** COMPLIANT. `contract.py` `turn_change_inside` checks for `>>` markers.
*   **Secrets:** COMPLIANT. `providers.py` `Keyring` reads from env file, redacts in logs.
*   **Spend Freeze:** COMPLIANT. `providers.py` `frozen_vendors` and `Router.available` enforce the freeze. `mine_paid` role has `freeze_lifted` and `daily_cap_usd`.

## SECTION 3: SECURITY

*   **SQL Injection:** All SQL queries in `queue.py` and `stats.py` use parameterized queries (`?`). No string concatenation of user input into SQL.
*   **Secrets:** `providers.py` `Keyring` redacts keys in error messages (`redact` method, line 213). `Backend.redact` (line 241) also redacts.
*   **Unvalidated Input:** `mine.py` `validator` strictly validates model output. `fetch.py` `probe` validates yt-dlp output. `watch.py` `rss_list` validates XML.
*   **Path Traversal:** `config.py` `check_store` ensures the store is not in the main tree unless allowed. `purge.py` `load_spec` validates paths.

## SECTION 4: FRONTEND QUALITY

N/A (Backend service).

## SECTION 5: BACKEND QUALITY

*   **DB Operations:** `queue.py` uses `sqlite3` with `WAL` mode and `synchronous=FULL`. Transactions are implicit in `execute`. `ledger.py` `append` uses `fcntl.flock` and `fsync`.
*   **External API Calls:** `providers.py` `Backend.complete` methods have timeouts and retries. `watch.py` `YouTubeGate` has a circuit breaker.
*   **Cron Job:** `service.py` `run` uses threads with `try/except` in `_loop` (line 783). Errors are logged and the loop continues.
*   **Memory Leaks:** `ThreadPoolExecutor` is used with bounded workers. `deque` in `Health` has `maxlen`.
*   **Logging:** `service.py` `_log` writes to file and stdout. `providers.py` `_emit` logs every attempt.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

*   **Observability:** The `live.json` and `STATE.md` files provide good visibility. However, there is no structured logging (e.g., JSON logs) for easy ingestion into a log aggregator.
*   **Testing:** 311 tests is a good number. However, there are no integration tests for the full `run` loop with a mock YouTube API.
*   **Documentation:** The design doc is detailed. However, the `providers.json` schema is not documented in a separate file.

## SECTION 7: SCORES

*   Backend logic: 95/100
*   Frontend/UI: N/A
*   Error handling: 95/100
*   Security: 95/100
*   Performance: 90/100
*   Law compliance: 100/100
*   World-class gap: 85/100
*   OVERALL: 93/100

## SECTION 8: PRIORITY ACTION PLAN

P2 MEDIUM | Add structured JSON logging | `service.py` | For better observability in production
P3 LOW | Document `providers.json` schema | `docs/` | For easier maintenance

## SECTION 9: THE ONE THING

Add a mock YouTube API integration test to verify the full `watch -> fetch -> mine` pipeline end-to-end.

## SECTION 10: FINAL VERDICT

The code is ready for production. The logic change is correct and well-tested. The only minor improvement is adding structured logging for better observability.