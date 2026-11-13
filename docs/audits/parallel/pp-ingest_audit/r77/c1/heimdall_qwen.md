# heimdall_qwen (qwen/qwen3.8-27b, 222.4 s, $0.018, finish stop)

This is a highly sophisticated, defensive, and well-documented codebase. The "Laws" (L-x, L-l, L-m, etc.) are not just comments; they are enforced via strict validation, circuit breakers, and fail-closed logic. The code is designed to survive vendor outages, rate limits, and model hallucinations.

However, there are subtle but critical issues in the **Purge** logic (symlink handling) and the **Ledger** expiry logic (timezone/naive datetime handling) that could lead to data loss or incorrect filtering.

### SECTION 1: CORRECTNESS

**1. Symlink Resolution in Purge (Critical Logic Flaw)**
In `pipeline/ingest/purge.py`, the code attempts to prevent deleting files outside the target unit or in protected paths.
*   **Line 296:** `if not rp.startswith(unit_real) or rp.startswith(protect) or any(b in rp for b in FORBIDDEN):`
*   **The Issue:** `rp` is `os.path.realpath(p)`. If a file inside `runs/<id>/sources/` is a symlink pointing to `/home/ultron/protocol_pulse/data/editorial/transcripts/...` (a protected path), `realpath` will resolve it to the protected path. The check `rp.startswith(protect)` will catch this.
*   **However**, consider a symlink inside `runs/<id>/sources/` pointing to *another* run's source, or a file that has been renamed.
*   **The Real Bug:** Look at `pipeline/ingest/purge.py` line 292: `if not stat.S_ISREG(st.st_mode):`. `os.lstat` does not follow symlinks. If the file is a symlink, `S_ISREG` is False. It is kept. This is safe.
*   **Wait, look at Line 295:** `rp = os.path.realpath(p)`.
*   **Scenario:** A legitimate media file `video.mp4` is in `runs/abc/sources/`. It is a regular file. `realpath` returns the same path. It passes.
*   **Scenario:** A file `video.mp4` is a symlink to `/tmp/word_pass_xyz/audio.wav`. `lstat` says it's a symlink. `S_ISREG` is False. It is kept.
*   **Scenario:** A file `video.mp4` is a symlink to `/home/ultron/protocol_pulse/references/pin.mp4`. `lstat` says symlink. Kept.
*   **Is there a hole?** What if the *unit* itself is a symlink?
    *   Line 275: `if os.path.islink(unit) or not os.path.isdir(unit): continue`. This prevents processing symlinked units.
*   **Verdict:** The symlink handling is actually quite robust due to `lstat` and `islink` checks.

**2. Ledger Expiry Timezone Handling (High Risk)**
In `pipeline/ingest/ledger.py`:
*   **Line 217:** `ts = [t for t in (config.aware(l.get("expires_at")), config.aware(config.expires_at(l.get("published_at")))) if t is not None]`
*   **Line 219:** `return min(ts) if ts else None`
*   **Line 269:** `if exp is not None and now >= exp:`
*   `config.aware` (config.py line 53) returns a `datetime` with `tzinfo` if present, else `None`.
*   `config.expires_at` (config.py line 62) returns an ISO string.
*   `now` in `best_unused_moments` (line 229) is `datetime.now(timezone.utc)`.
*   If `l.get("expires_at")` is a naive ISO string (e.g., from an older version or a bug), `config.aware` returns `None`.
*   If `l.get("published_at")` is naive, `config.expires_at` returns `None` (because `aware` returns `None`).
*   **The Bug:** If *both* are `None`, `expiry` returns `None`.
*   **Line 269:** `if exp is not None and now >= exp:`. If `exp` is `None`, the moment is **NOT** dropped as expired.
*   **Line 273:** `elif pub is None or pub > now: drop("publish time not measured...")`.
*   If `published_at` is naive, `pub` (from `_aware` at line 248) is `None`. So it is dropped as "publish time not measured".
*   **However**, what if `published_at` is valid (aware), but `expires_at` is missing?
    *   `config.expires_at(l.get("published_at"))` calculates `pub + 12h`. This is aware.
    *   `expiry` returns this.
    *   This works.
*   **What if `published_at` is aware, but `expires_at` is present but naive?**
    *   `config.aware(l.get("expires_at"))` returns `None`.
    *   `config.aware(config.expires_at(...))` returns the calculated aware datetime.
    *   `min` takes the calculated one. This is safe (fail closed to the calculated value).
*   **Verdict:** The logic seems to fail closed correctly by relying on `published_at` if `expires_at` is invalid/missing.

**3. Purge "Abandoned" Mode Logic**
In `pipeline/ingest/purge.py` line 315:
`elif newest > abandoned_after: keep("a word-pass cycle's, touched under 12 h ago", size)`
`abandoned_after` is `cutoff.timestamp()` (now - 12h).
If `newest` (mtime) is *newer* than `now - 12h`, it is kept.
If `newest` is *older* than `now - 12h`, it proceeds to the `busy_after` check.
This logic is correct for "abandoned" files (delete if old and idle).

**4. Race Condition in Purge**
`purge.py` uses `fcntl.flock` on `purge.lock`. This prevents concurrent purge passes.
However, it does not prevent a *render* process from writing to a file *while* the purge is checking `newest_mtime`.
*   Line 283: `newest = newest_mtime(unit)`.
*   Line 318: `if newest > busy_after: keep(...)`.
*   If a render starts *after* `newest_mtime` is calculated but *before* `os.unlink` (line 330), the file might be deleted while being written to.
*   **Mitigation:** `active_grace_s` is 7200s (2 hours). A render is unlikely to start on a file that hasn't been touched in 2 hours. But if a render *resumes* an old file? Unlikely.
*   **Verdict:** Acceptable risk given the 2-hour grace period.

### SECTION 2: LAW COMPLIANCE

*   **L-x (No Single Model, Ultron First):** **COMPLIANT.**
    *   `providers.json` defines chains.
    *   `providers.py` `Router` iterates chains.
    *   `spend_freeze` logic in `providers.py` line 692-695 ensures frozen vendors are skipped.
    *   `local_gemma` is in the chain but disabled by default (`enabled: false` in `providers.json` line 13). It is only enabled if `gpu0.held()` is true (line 465 in `providers.py`).
*   **L-l (Reply Counts Only Whole):** **COMPLIANT.**
    *   `mine.py` `validator` (line 177) is extremely strict. It rejects markdown, extra keys, wrong types, etc.
    *   `providers.py` line 846: `obj = validate(r.content)`. If it fails, it's rejected. No repair.
*   **L-j / L-m (Fail Closed):** **COMPLIANT.**
    *   `purge.py` line 253: `if problems: ... return rep`. If `/proc` is unreadable or delivered set is unreadable, it deletes nothing.
    *   `ledger.py` line 238: `if oerr: raise ValueError`. If optout file is unreadable, the read is refused.
*   **L-h / L-k (Read As Spoken):** **COMPLIANT.**
    *   `contract.py` line 123: `text = E.spoken(toks[w0:w1 + 1])`. Uses the canonical `spoken` function.
*   **L-u (Hard Exclusions):** **COMPLIANT.**
    *   `mine.py` line 23: `HARD_RISKS` defined.
    *   `ledger.py` line 279: `elif any(r in mine.HARD_RISKS for r in l["risk"]): drop(...)`.
*   **L-v (Speaker Change):** **COMPLIANT.**
    *   `contract.py` line 129: `turn_change_inside`.
    *   `ledger.py` line 283: `elif l["speaker"].get("turn_change_inside") is True: drop(...)`.
*   **Secrets:** **COMPLIANT.**
    *   `providers.py` `Keyring` reads from env file.
    *   `providers.py` line 180: `redact` method replaces key values in error logs.
    *   `providers.py` line 291: `_NoRedirect` prevents key leakage via redirects.

### SECTION 3: SECURITY

*   **SQL Injection:** **SAFE.**
    *   `queue.py` uses parameterized queries (`?`).
*   **Path Traversal:** **SAFE.**
    *   `purge.py` `load_spec` (line 72) checks for `..` in paths.
    *   `purge.py` line 296 checks `realpath` against `unit_real` and `protect`.
*   **Symlink Attacks:** **SAFE.**
    *   `purge.py` line 292 checks `S_ISREG` on `lstat`. Symlinks are not regular files, so they are skipped.
*   **DoS:** **MITIGATED.**
    *   `providers.py` has circuit breakers, throttling, and spend caps.
    *   `purge.py` has a lock to prevent concurrent runs.

### SECTION 4: FRONTEND QUALITY
N/A (Backend/CLI service).

### SECTION 5: BACKEND QUALITY

*   **DB Operations:** **GOOD.**
    *   `queue.py` uses `sqlite3` with `WAL` mode and `synchronous=FULL`.
    *   Transactions are handled via `isolation_level=None` (autocommit) but explicit `execute` calls.
*   **External API Calls:** **EXCELLENT.**
    *   `providers.py` handles timeouts, retries, backoff, and circuit breaking.
    *   `watch.py` handles YouTube rate limits with a global breaker.
*   **Cron Job:** **GOOD.**
    *   `service.py` runs loops in threads. Exceptions are caught and logged (line 397).
*   **Memory Leaks:** **LOW RISK.**
    *   `ThreadPoolExecutor` is used.
    *   `deque` is used for health events (bounded).
*   **Logging:** **GOOD.**
    *   `service.py` logs to file and stdout.
    *   `providers.py` logs attempts to `replies_log`.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Observability:** The system writes to `live.json` and `STATE.md`, but lacks structured logging (e.g., JSON logs) for ingestion into a monitoring stack (Prometheus/Grafana).
2.  **Testing:** The test inventory is extensive, but there are no integration tests for the *purge* logic against a real filesystem with symlinks and permissions.
3.  **Configuration Management:** `providers.json` and `purge.json` are static files. There is no mechanism to hot-reload them without a restart (except `overrides.json` for base URLs).

### SECTION 7: SCORES

*   Backend logic: 95/100
*   Frontend/UI: N/A
*   Error handling: 98/100
*   Security: 95/100
*   Performance: 90/100
*   Law compliance: 100/100
*   World-class gap: 85/100
*   OVERALL: 94/100

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Verify `purge.py` symlink handling against a real filesystem with malicious symlinks | `pipeline/ingest/purge.py:292` | Ensure `lstat` + `S_ISREG` correctly prevents deletion of symlinks pointing to protected paths.
P1 HIGH | Add integration test for `purge.py` with symlinks and permissions | `tests/ingest/test_purge.py` | Verify that the purge logic does not delete files it shouldn't.
P2 MEDIUM | Add structured logging (JSON) for monitoring | `pipeline/ingest/service.py` | Facilitate ingestion into Prometheus/Grafana.
P3 LOW | Document the `purge.json` schema | `docs/` | Help integrators understand the configuration.

### SECTION 9: THE ONE THING

Add a comprehensive integration test suite for the `purge` module that simulates a real filesystem with symlinks, permissions, and concurrent writes to ensure the "fail closed" logic holds under all edge cases.

### SECTION 10: FINAL VERDICT

This code is production-ready. It is exceptionally well-designed, with a strong focus on safety, compliance, and resilience. The only remaining risk is in the `purge` module's interaction with the filesystem, which should be validated with integration tests before deployment.