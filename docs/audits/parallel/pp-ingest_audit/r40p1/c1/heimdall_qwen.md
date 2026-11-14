# heimdall_qwen (qwen/qwen3.8-27b, 214.8 s, $0.008, finish stop)

This is a highly sophisticated, defensive engineering codebase. The "fail closed" philosophy is pervasive and correctly implemented. The separation of concerns (watch, fetch, mine, ledger, provider) is clean.

However, there are **critical race conditions** in the ledger append logic and the provider router that will cause data corruption or silent failures under concurrent load. There is also a **security vulnerability** in the runtime override mechanism.

### SECTION 1: CORRECTNESS

**1. Race Condition in Ledger Append (Data Corruption)**
`pipeline/ingest/ledger.py:34` (`append`) and `pipeline/ingest/service.py:276` (`_append`).
The service holds a Python-level lock (`self.wlock`) to serialize appends. However, `ledger.append` opens the file, acquires an `fcntl.flock`, checks for a torn tail, writes, and releases.
If two processes (or threads, if the lock is bypassed) attempt to write, the `fcntl.flock` protects the file descriptor. But look at `service.py:284`:
```python
ledger.carry_forward(lines, ledger.video_lines(self.p["ledger"], v["video_id"], since))
return ledger.append(self.p["ledger"], lines, stamp=config.iso)
```
`carry_forward` reads the ledger *before* `append` takes the lock. If another thread appends a line for the same `moment_id` between the read in `carry_forward` and the write in `append`, the new line will **not** carry the flags of the concurrent line. This violates the "fail closed" requirement for flag union. The read and write must be atomic under the same lock.

**2. Race Condition in Provider Router (Lost Updates)**
`pipeline/ingest/providers.py:855` (`_try`).
When a reply is valid, it is cached:
```python
if path:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "w") as f:
            json.dump(...)
        os.replace(tmp, path)
```
`os.replace` is atomic on POSIX. However, if two threads request the same prompt simultaneously (e.g., a retry storm), both will compute the same `path`. Both will write to their unique `tmp` files. Both will `os.replace`. The last one wins. This is generally safe for content, but if the first write fails (disk full) and the second succeeds, the state is inconsistent. More critically, `SpendBook.add` (line 838) is called *before* the cache write. If the cache write fails, spend is recorded but no reply is saved. This is acceptable (fail closed), but the lack of a lock around the "check cache -> call API -> write cache" sequence means duplicate API calls are frequent under concurrency, wasting budget.

**3. N+1 Query in Stats**
`pipeline/ingest/stats.py:115`.
```python
for e in q.rows("SELECT detail FROM events WHERE kind='flagcheck' AND ts >= ?", (h0,)):
```
This fetches all events in the last 12 hours. If the system is busy, this could be thousands of rows. It then parses JSON for each. This is acceptable for a 10-minute loop, but if `h0` is large or the system is very active, this becomes a bottleneck.

**4. Logic Error in `check_valid`**
`pipeline/ingest/ledger.py:223`.
```python
if c.get("prompt_version") != flagcheck.PROMPT_VERSION or not c.get("model") or \
        c.get("model") == (l.get("mined") or {}).get("model"):
    return None
```
This checks if the checker's model is the same as the miner's model. However, `l.get("mined")` might contain a `model` field that is a string like `qwen3.8-27b`. The checker's `c.get("model")` is also a string. This comparison is correct. **However**, if the miner used a local model (`gemma3:27b`) and the checker used a remote model, this passes. If the miner used `qwen` and the checker used `qwen` (different backend, same model), this fails. This is correct behavior (L-x: no single model).

### SECTION 2: LAW COMPLIANCE

*   **L-x (No Single Model, Ultron First):** **COMPLIANT.** `providers.json` defines chains. `Router` enforces order. `spend_freeze` prevents paid vendors. Local model is preferred if available.
*   **L-l (Reply Counts Only Whole):** **COMPLIANT.** `mine.py:272` (`validator`) is strict. `Invalid` exceptions are raised. No repair logic.
*   **L-j / L-m (Fail Closed):** **COMPLIANT.** `config.py:72` (`check_store`) refuses main tree. `ledger.py:337` refuses expired. `purge.py:298` refuses if `/proc` unreadable.
*   **L-h / L-k (Read As Spoken):** **COMPLIANT.** `contract.py:123` uses `eligibility.spoken`.
*   **L-u (Hard Exclusions):** **PARTIAL.** `ledger.py:229` (`effective_risk`) allows releasing `imperative` and `single_source_breaking` if the second model says "no". This is per Ruling 40 P1. However, `accusation` is never released. This is compliant with the ruling.
*   **L-v (Speaker Change):** **COMPLIANT.** `contract.py:129` (`turn_change_inside`) checks for `>>`. `ledger.py:351` excludes if `True`.
*   **Secrets:** **COMPLIANT.** `providers.py:147` (`Keyring`) reads from env file. `redact` method ensures keys are not logged.
*   **Spend Freeze:** **COMPLIANT.** `providers.py:692` (`frozen`) checks vendor. `Router.run` skips frozen backends.

### SECTION 3: SECURITY

**1. Runtime Override Bypass (Critical)**
`pipeline/ingest/providers.py:135` (`override_allowed`).
```python
return u.hostname in ("127.0.0.1", "localhost", "::1") or (u.hostname == c.hostname and u.scheme == c.scheme)
```
This allows overriding the base URL to `localhost` or the *configured* host. If the configured host is `api.heimdallm.com`, an attacker with write access to `overrides.json` can point the service to `api.heimdallm.com` (no change) or `localhost`.
**Vulnerability:** If the service is running in a container or VM, `localhost` might resolve to a different service (e.g., a malicious proxy) that intercepts the API key. The check `u.hostname == c.hostname` is weak if DNS is spoofed.
**Fix:** Require the override to be an IP address or a specific trusted domain, and verify the TLS certificate if possible. Or, restrict overrides to `127.0.0.1` only for drills, and require a separate flag for production overrides.

**2. SQL Injection**
`pipeline/ingest/queue.py:155` (`set_state`).
```python
cols = ", ".join(f"{k}=?" for k in f)
self.x(f"UPDATE videos SET {cols} WHERE video_id=?", tuple(f.values()) + (vid,))
```
`f` is a dict of field names. If `f` contains a key like `1=1; DROP TABLE videos; --`, it would be injected.
**Mitigation:** `VIDEO_FIELDS` (line 63) is a tuple of allowed fields. `set_state` checks `if k not in VIDEO_FIELDS`. This prevents injection. **COMPLIANT.**

**3. Path Traversal**
`pipeline/ingest/ledger.py:254` (`record_by_sha`).
```python
d = os.path.join(store_root, "transcripts", video_id)
```
`video_id` is validated by `VIDEO_ID` regex (`^[A-Za-z0-9_-]{11}$`) in `line_problems` (line 100). This prevents path traversal. **COMPLIANT.**

### SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend service. No UI.

### SECTION 5: BACKEND QUALITY

**1. DB Operations**
`pipeline/ingest/queue.py:77`.
`sqlite3.connect` with `isolation_level=None` (autocommit). `PRAGMA synchronous=FULL`. This is safe for durability but slow. `WAL` mode is enabled. **COMPLIANT.**

**2. External API Calls**
`pipeline/ingest/providers.py:311` (`_request`).
`urllib.request` with timeout. `BackendError` handling. **COMPLIANT.**

**3. Cron Job**
`pipeline/ingest/service.py:608` (`_loop`).
`try/except` around `fn()`. Errors are logged and the loop continues. **COMPLIANT.**

**4. Memory Leaks**
`pipeline/ingest/providers.py:548` (`Health`).
`deque(maxlen=50)`. Bounded. **COMPLIANT.**

**5. Logging**
`pipeline/ingest/service.py:145` (`_log`).
Logs to file and stdout. **COMPLIANT.**

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Observability:** No metrics endpoint (Prometheus). The `live.json` file is a good start, but a `/metrics` endpoint would be standard for a service of this complexity.
2.  **Configuration Management:** `providers.json` is static. Changes require a restart. A hot-reload mechanism for provider config (with validation) would be better.
3.  **Testing:** The test suite is extensive (237 tests). However, there are no integration tests for the full pipeline (watch -> fetch -> mine -> ledger) under load. The race conditions identified in Section 1 would be caught by such tests.

### SECTION 7: SCORES

*   Backend logic: 85/100 (Race conditions in ledger append)
*   Frontend/UI: N/A
*   Error handling: 95/100 (Excellent fail-closed design)
*   Security: 80/100 (Override bypass risk)
*   Performance: 85/100 (N+1 in stats, duplicate API calls)
*   Law compliance: 100/100 (Strict adherence)
*   World-class gap: 70/100 (Missing observability and hot-reload)
*   OVERALL: 85/100

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Fix race condition in ledger append | `pipeline/ingest/service.py:276` | `carry_forward` reads ledger before `append` writes. Concurrent appends can lose flags. Move `carry_forward` inside the `fcntl.flock` in `ledger.append` or use a single atomic operation.
P1 HIGH | Restrict runtime overrides | `pipeline/ingest/providers.py:135` | `override_allowed` permits `localhost` which can be spoofed. Restrict to `127.0.0.1` only for drills, and require a separate flag for production.
P2 MEDIUM | Add metrics endpoint | `pipeline/ingest/service.py` | Expose Prometheus metrics for spend, latency, and queue depth.
P3 LOW | Optimize stats query | `pipeline/ingest/stats.py:115` | Use a subquery to aggregate events instead of fetching all rows.

### SECTION 9: THE ONE THING

Make the ledger append atomic by moving the `carry_forward` logic inside the file lock, ensuring that concurrent writes to the same moment ID always result in the union of flags.

### SECTION 10: FINAL VERDICT

This code is production-ready in terms of logic and law compliance, but it has a critical race condition in the ledger append that will cause data corruption under concurrent load. Fix the race condition and restrict the runtime override mechanism before deploying.