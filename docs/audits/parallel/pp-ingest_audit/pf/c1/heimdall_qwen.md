# heimdall_qwen (qwen/qwen3.8-27b, 417.2 s, $0.011, finish stop)

This is a review of the `pp-ingest` feature branch, specifically focusing on the diff introduced in commit `98a57406` (the "Playlist First" change) and the surrounding context of the ingest pipeline.

### SECTION 1: CORRECTNESS

**1. The "Playlist First" Logic is Sound but Subtly Changes Error Semantics**
In `pipeline/ingest/watch.py`, the `poll_channel` function was refactored to try sources in a specific order.
*   **Old Logic:** If `rss_mode` was true, it tried RSS. If that failed or wasn't in mode, it tried Playlist.
*   **New Logic:** It iterates over a tuple of functions `(playlist, rss)` or `(rss, playlist)`.
    *   `watch.py:204`: `for get in ((playlist, rss) if playlist_first else (rss, playlist)):`
    *   `watch.py:205`: `if get is rss and not rss_mode: continue`
    *   `watch.py:208`: `entries, source = get()`
    *   `watch.py:210`: `except ListError as e:`

**Issue:** The error accumulation logic at `watch.py:211` is:
```python
err = f"{err + '; ' if err else ''}{e.kind}" + (f": {e.detail[:160]}" if get is playlist else "")
```
If `playlist_first` is True (the default), and the playlist fails, `err` becomes `"playlist_unreadable: <detail>"`. If it then falls back to RSS (and `rss_mode` is true), and RSS *also* fails, `err` becomes `"playlist_unreadable: <detail>; rss_http_404"`.
However, if the playlist succeeds, the loop breaks. This is correct.
**Critical Edge Case:** What if the playlist returns *empty* entries? `playlist_list` returns `[]`. The loop breaks. `entries` is `[]`. The code proceeds to `watch.py:218`. `new` remains 0. This is correct behavior (no new videos).

**2. Race Condition in `YouTubeGate`**
`watch.py:38-74` implements a global rate limit breaker.
*   `watch.py:65`: `if self.open_for() > 0: raise ListError("rate_limited", ...)`
*   `watch.py:67`: `with self.sem:` (acquires semaphore)
*   `watch.py:68`: `r = config.ts()._ytdlp(args, timeout=timeout)`

If a request triggers a rate limit (`watch.py:70-72`), it calls `self.trip()`. This sets `self.until` to a future time.
**Potential Issue:** The `calm()` method (`watch.py:56-58`) decrements `self.trips` on *any* successful call. If one channel hits a rate limit, the breaker opens. If *another* channel's request was already in-flight (holding the semaphore) and succeeds, it calls `calm()`. This reduces the backoff duration. This is likely intended behavior (exponential backoff with decay on success), but it means a single rate limit event might not pause the *entire* system for the full duration if other requests are succeeding concurrently. Given `YTDLP_CONCURRENCY = 3`, this is a minor risk but acceptable for a scraper.

**3. `fetch.py` State Machine Integrity**
`fetch.py:120-251` handles the state machine.
*   `fetch.py:130`: `j, err = probe(gate, vid)`
*   If `err` is `rate_limited`, it sets state to `PROBE_RETRY` with `next_at` based on `gate.open_for()`.
*   `fetch.py:142`: `next_at=now_ts + (gate.open_for() or 0) + PROBE_RETRY_S[0]`
This correctly waits for the global breaker to close before retrying.

**4. `mine.py` Windowing Logic**
`mine.py:372-390` generates windows.
*   `mine.py:389`: `i = max(j - min(overlap, (j - i) // 2), i + 1)`
This ensures forward progress. If `j == i` (empty window, shouldn't happen due to `rows` filter), `i` increments by 1.
The logic `min(overlap, (j - i) // 2)` prevents the overlap from being larger than half the window, ensuring coverage. This is correct.

**5. `ledger.py` Append Atomicity**
`ledger.py:34-66` uses `fcntl.flock` and `os.O_APPEND`.
*   `ledger.py:55`: `if size and os.pread(fd, 1, size - 1) != b"\n":`
This checks for a torn tail. If the last byte isn't a newline, it prepends a newline. This is a robust way to handle crashes mid-write.
*   `ledger.py:58-60`: Writes in a loop until all bytes are written. `os.write` can do partial writes. This is correct.

**6. `providers.py` Router Logic**
`providers.py:837-885` `Router.run`.
*   It iterates through the chain.
*   `providers.py:851`: `if use_cache and self.backends[bid].cfg.get("enabled", True):`
    *   It checks the cache *before* checking `available()`.
    *   `providers.py:857`: `ok, why = self.available(bid, breaker, lifted)`
    *   If the backend is frozen/disabled, `available` returns `False`.
    *   **Bug:** If a backend is **frozen** (spend freeze), `available` returns `False`. However, the cache check happens *before* `available`.
    *   `providers.py:851-856`: If `use_cache` is True and the backend is enabled in config, it tries to load from cache.
    *   **Scenario:** A video was mined by `heimdall_qwen27b` yesterday. Today, `heimdall_qwen27b` is frozen (spend freeze). The router tries to mine a *new* window. It checks the cache for this specific prompt. If the prompt is identical (unlikely for new windows, but possible for retries), it returns the cached result.
    *   **Is this a violation?** The design says: "A frozen vendor's back-end is never called by any role... its stored validated replies cost nothing and may be re-read."
    *   So, using the cache for a frozen backend is **compliant** with the design. The code correctly allows cache hits for frozen backends.

**7. `downsignal.py` Probe Logic**
`downsignal.py:344-388` `_start_probe`.
*   It spawns threads for each backend in the probe chain.
*   `downsignal.py:375`: `a.join(max(0.0, end - time.monotonic()))`
*   This waits for the probe to finish or timeout.
*   `downsignal.py:376-379`: It collects results. If a thread is still alive, it marks it as "no answer by deadline".
*   This is correct.

### SECTION 2: LAW COMPLIANCE

*   **L-x (No Single Model, Ultron First):**
    *   `providers.json` defines chains with multiple backends.
    *   `providers.py:158-160` enforces `len(r["chain"]) < 2` raises an error.
    *   **COMPLIANT.**
*   **L-l (Reply Counts Only Whole):**
    *   `mine.py:447-499` `validator` is strict. It rejects non-JSON, missing keys, wrong types, out-of-range scores.
    *   `providers.py:982-989` If validation fails, it retries with the error message. If it fails 3 times, it moves to the next backend.
    *   **COMPLIANT.**
*   **L-j / L-m (Fail Closed):**
    *   `config.py:76-83` `check_store` raises `StoreGuard` if writing to main tree without env var.
    *   `ledger.py:337-338` Expired moments are dropped.
    *   `downsignal.py:477-485` If the shared signal is unreadable, it logs an error and does *not* guess the state.
    *   **COMPLIANT.**
*   **L-h / L-k (Read As Spoken):**
    *   `contract.py:123` `text = E.spoken(toks[w0:w1 + 1])`.
    *   `mine.py:405` `prompt` uses `_untrusted(s['text'])` which comes from `contract.sentences` -> `E.spoken`.
    *   **COMPLIANT.**
*   **L-u (Hard Exclusions):**
    *   `mine.py:21-24` `HARD_RISKS` defined.
    *   `ledger.py:347-348` `best_unused_moments` drops moments with hard risk flags.
    *   `flagcheck.py` measures precision but does not clear flags (as per design).
    *   **COMPLIANT.**
*   **Spend Freeze:**
    *   `providers.py:783-786` `frozen` checks `spend_freeze.vendors`.
    *   `providers.py:811-812` `available` returns `False` if frozen.
    *   **COMPLIANT.**

### SECTION 3: SECURITY

*   **SQL Injection:**
    *   `queue.py` uses `sqlite3` with parameterized queries (`?`).
    *   `queue.py:133-134`: `cols = ", ".join(f"{k}=?" for k in f)` ... `tuple(f.values()) + (cid,)`.
    *   The keys `k` come from `VIDEO_FIELDS` (a static tuple) or `HOOK_COLUMNS`/`ROUTE_COLUMNS` (static tuples). They are not user input.
    *   **SAFE.**
*   **Secrets:**
    *   `providers.py:180-220` `Keyring` reads from an env file.
    *   `providers.py:213-220` `redact` replaces key values in error messages.
    *   `providers.py:346` `Authorization: Bearer <key>`.
    *   Keys are never logged directly.
    *   **SAFE.**
*   **Path Traversal:**
    *   `config.py:72-73` `store_root` uses `os.path.realpath`.
    *   `ledger.py:254-269` `record_by_sha` joins `video_id` into a path. `video_id` is validated by `VIDEO_ID` regex (`^[A-Za-z0-9_-]{11}$`) in `ledger.py:27` and `line_problems` in `ledger.py:100`.
    *   **SAFE.**
*   **SSRF:**
    *   `providers.py:168-177` `override_allowed` restricts base URL overrides to localhost or the configured host.
    *   `watch.py:92` RSS URL is hardcoded to `youtube.com`.
    *   **SAFE.**

### SECTION 4: FRONTEND QUALITY

*   **N/A:** This is a backend service. There is no UI. The "frontend" is the JSON output of `live.json` and the Markdown reports.
*   **Report Quality:**
    *   `coverage.py:111-124` Generates a Markdown table.
    *   `flagcheck.py:467-524` Generates a detailed Markdown report with confusion matrices.
    *   These are well-structured and informative.

### SECTION 5: BACKEND QUALITY

*   **DB Operations:**
    *   `queue.py:82` `isolation_level=None` (autocommit).
    *   `queue.py:86` `PRAGMA journal_mode=WAL`.
    *   `queue.py:87` `PRAGMA synchronous=FULL`.
    *   This is a robust configuration for a high-write, low-read latency service.
*   **External API Calls:**
    *   `providers.py` handles timeouts, retries, and circuit breakers.
    *   `watch.py` handles yt-dlp subprocess timeouts.
*   **Cron Job:**
    *   The service runs as a long-lived process (`service.py:871-913`).
    *   It uses `threading` for concurrent loops.
    *   `service.py:855-864` `_loop` catches exceptions and logs them, preventing the thread from dying.
*   **Memory Leaks:**
    *   `providers.py:581` `Health` uses a `deque(maxlen=50)`.
    *   `purge.py:205` `_SHA` cache is bounded by `SHA_CACHE_MAX = 4096`.
    *   `downsignal.py:136` `pending` dict is reset on every flush.
    *   **No obvious leaks.**
*   **Logging:**
    *   `service.py:183-190` `_log` writes to stdout and a file.
    *   Errors are logged with context (e.g., `mine.py:304` logs traceback).

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Observability:** The service writes to `live.json` and logs. However, it lacks structured metrics (e.g., Prometheus format) for alerting on specific KPIs like "mining latency p95" or "spend rate". A professional setup would expose `/metrics`.
2.  **Configuration Management:** `providers.json` is static. Changing the spend freeze or backend chain requires a restart. A hot-reload mechanism for `providers.json` (like `overrides.json` for URLs) would be more robust.
3.  **Testing:** The test suite is extensive (356 tests). However, there are no integration tests that simulate a full end-to-end flow with mocked external services (yt-dlp, Heimdall API). The unit tests are good, but an integration test would catch wiring issues.
4.  **Documentation:** The code is heavily commented, which is excellent. However, a `README.md` explaining how to run the service, configure the environment, and interpret the outputs would be helpful for operators.

### SECTION 7: SCORES

*   **Backend logic:** 95/100 (Robust state machine, good error handling)
*   **Frontend/UI:** N/A (100/100 for report quality)
*   **Error handling:** 95/100 (Comprehensive try/except, fail-closed design)
*   **Security:** 95/100 (Parameterized queries, secret redaction, path validation)
*   **Performance:** 90/100 (WAL mode, bounded caches, concurrent threads)
*   **Law compliance:** 100/100 (Strictly follows the defined laws)
*   **World-class gap:** 85/100 (Missing metrics endpoint and hot-reload for config)
*   **OVERALL:** 93/100

### SECTION 8: PRIORITY ACTION PLAN

*   **P1 HIGH** | Add a `/metrics` endpoint exposing Prometheus-style metrics for mining latency, spend, and queue depth | `service.py` | Enables professional monitoring and alerting.
*   **P2 MEDIUM** | Implement hot-reload for `providers.json` | `providers.py` | Allows changing spend freeze or backend chain without restarting the service.
*   **P3 LOW** | Add an integration test with mocked external services | `tests/ingest/` | Validates the full pipeline wiring.

### SECTION 9: THE ONE THING

Add a Prometheus metrics endpoint to expose real-time KPIs (mining latency, spend, queue depth) for professional monitoring and alerting.

### SECTION 10: FINAL VERDICT

This code is production-ready. It is robust, secure, and strictly compliant with the defined laws. The "Playlist First" change is correctly implemented and improves discovery latency. The only gap is the lack of a standard metrics endpoint for observability, which is a common requirement in professional backend services.