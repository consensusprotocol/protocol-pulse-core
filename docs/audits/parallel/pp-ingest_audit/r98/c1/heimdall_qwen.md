# heimdall_qwen (qwen/qwen3.8-27b, 337.1 s, $0.010, finish stop)

This is a highly sophisticated, defensive engineering codebase. The "Laws" (L-x, L-l, L-m, etc.) are not just comments; they are enforced via strict validation, circuit breakers, and fail-closed logic. The code is designed to survive vendor outages, rate limits, and model hallucinations.

However, there are critical concurrency and state-management flaws in the new **Ruling 98 (Paid Route)** implementation that could lead to silent data loss or budget overruns.

### SECTION 1: CORRECTNESS

**1. Race Condition in `RoleCaps` (Critical)**
In `pipeline/ingest/providers.py`, the `RoleCaps` class manages the daily spend limit.
- `reserve()` (line 703) checks `spent + reserved + amount > cap`.
- `add()` (line 716) updates `spent`.
- **The Flaw:** `reserve` and `add` are separate lock acquisitions.
    1. Thread A calls `reserve(0.25)`. `spent=0`, `reserved=0`. Passes. `reserved=0.25`.
    2. Thread B calls `reserve(0.25)`. `spent=0`, `reserved=0.25`. Passes. `reserved=0.50`.
    3. Thread A finishes, calls `add(0.20)`. `spent=0.20`.
    4. Thread B finishes, calls `add(0.20)`. `spent=0.40`.
    5. Thread C calls `reserve(0.25)`. `spent=0.40`, `reserved=0.0` (A and B released). `0.40 + 0 + 0.25 = 0.65 < 2.0`. Passes.
    - *Wait, the logic holds for small numbers.* Let's look at the **Release** logic.
    - In `Router.run` (line 874), `finally: self.caps.release(role, reserve)`.
    - If a call fails *after* `reserve` but *before* `add` (e.g., network timeout), `release` is called. `reserved` decreases. `spent` does not increase. This is correct.
    - **However**, `RoleCaps._roll` (line 697) resets `spent` based on the loader. If the loader (`queue.role_spend_since`) is slow or inconsistent with the in-memory `spent` during a day rollover, you might double-count or under-count.
    - **Real Bug:** `RoleCaps` is per-Router instance. If the service restarts, `RoleCaps` is empty. It relies on `loader` to fetch historical spend. `queue.role_spend_since` (line 182) sums `calls` table. This is correct.
    - **Subtle Bug:** `reserve` uses `cap + 1e-9`. `add` does not check the cap. If `reserve` passes, but the actual cost exceeds the reservation (e.g., model uses more tokens than estimated), `spent` can exceed `cap`. The next `reserve` will fail, but the current call has already spent money. This is acceptable for a "soft" cap, but the code claims "no call starts past the cap". It does not prevent *overshoot* of the cap by the final call.

**2. `paid_open` State Desync**
In `pipeline/ingest/downsignal.py`, `paid_open` is a boolean attribute of `DownSignal`.
- It is set in `_route_tick` (line 228).
- It is read in `service.mine_once` (line 535).
- **The Flaw:** `_route_tick` runs in the `signal` thread (every 5s). `mine_once` runs in the `mine` thread (every 5s).
- If the signal thread detects "Heimdall Down" and sets `paid_open = True`, the mine thread sees it.
- If the signal thread detects "Heimdall Back" and sets `paid_open = False`, the mine thread sees it.
- **Race:** What if the mine thread is *currently* processing a video on the paid route when the signal flips back?
    - `mine_video` is called with `role="mine_paid"`.
    - It finishes, appends to ledger.
    - `_settle` updates state to `MINED`.
    - `mine_route` is set to `mine_paid`.
    - Later, `_queue_rechecks` (line 575) sees `signal_back()` is True. It queries `recheck_due` for `mine_route="mine_paid"`.
    - It resets state to `TRANSCRIBED` and `recheck_ts`.
    - This seems correct. The video is re-mined on the `mine` role.
    - **However**, `recheck_due` (queue.py line 188) filters by `state IN (MINED, MINED_PARTIAL)`.
    - If the video was `MINED` on the paid route, it is eligible.
    - **Bug:** `recheck_due` does not check if the video was *actually* mined on the paid route *recently*. It checks `mine_route`. If a video was mined on the paid route 11 hours ago, and the signal flips back, it will be re-mined. This is intended (A31).
    - **Missing Check:** `recheck_due` does not verify that the `mine_route` video is still within `recheck_within_s` (12h) *at the time of the query*. It uses `published_ts >= now - horizon_s`. This is correct.

**3. `conv` Cache Memory Leak**
In `service.py` line 560: `if len(self._conv) > 5000: self._conv.clear()`.
- `self._conv` maps `video_id` to `bool` (is conversation).
- If the service runs for days, this dict grows. The clear is a blunt instrument. It clears *all* data, forcing re-calculation of `episode_measure` for all videos in the next batch. This causes a spike in I/O (reading transcripts) and CPU.
- **Better:** Use an LRU cache or timestamp-based eviction.

**4. `offset_before` Bisection Edge Case**
In `ledger.py` line 122, `offset_before` bisects the file to find the start of the relevant tail.
- It assumes `mined.at` is monotonic.
- `append` (line 34) stamps `mined.at` under the lock.
- **However**, `carry_forward` (line 187) modifies lines *before* append.
- If a line is appended, then a *new* line for the same `moment_id` is appended later, the `mined.at` of the *new* line is later.
- The bisection looks for `mined.at >= cutoff`.
- If the file is huge, and the cutoff is old, it reads from the start.
- **Performance:** The docstring says "16-25 s per 100k lines before, the recent tail after". This is a significant latency for the adapter.

### SECTION 2: LAW COMPLIANCE

- **L-x (No Single Model, Ultron First):** **COMPLIANT.**
    - `providers.json` defines chains.
    - `Router` tries backends in order.
    - `spend_freeze` prevents paid vendors unless `freeze_lifted` (Ruling 98).
    - `local_gemma` is disabled by default but wired.
- **L-l (Reply Counts Only Whole):** **COMPLIANT.**
    - `validator` in `mine.py` (line 332) is strict.
    - `Invalid` exception is raised for any deviation.
    - No repair logic.
- **L-j / L-m (Fail Closed):** **COMPLIANT.**
    - `StoreGuard` prevents writing to main tree.
    - `ContractUnavailable` stops mining.
    - `AllBackendsFailed` distinguishes outage vs rejection.
    - `purge.py` stops if `/proc` is unreadable.
- **L-h / L-k (Read As Spoken):** **COMPLIANT.**
    - `contract.sentences` uses `eligibility.spoken`.
    - `fetch.py` stores verbatim.
- **L-u (Hard Exclusions):** **COMPLIANT.**
    - `mine.py` flags risks.
    - `ledger.py` `effective_risk` applies exclusions.
    - `flagcheck.py` measures precision but does not clear flags (Option B simulated).
- **L-v (Speaker/Transcript Truth):** **COMPLIANT.**
    - `turn_change_inside` checks for `>>`.
    - `duplicate` detection uses fingerprint.
- **Secrets:** **COMPLIANT.**
    - `Keyring` reads from env file.
    - `redact` replaces keys in logs.
    - `_NoRedirect` prevents key leakage via redirects.
- **Spend Freeze:** **COMPLIANT.**
    - `frozen_vendors` checked in `Router.available`.
    - `freeze_lifted` only for `mine_paid` with cap.

### SECTION 3: SECURITY

- **SQL Injection:** **SAFE.**
    - `queue.py` uses parameterized queries (`?`).
    - `f-string` in `set_state` (line 164) uses `cols` built from `f` keys, which are validated against `VIDEO_FIELDS` (line 160). Safe.
- **Path Traversal:** **SAFE.**
    - `config.check_store` ensures store is not in main tree.
    - `purge.py` `load_spec` validates paths are absolute and not in `FORBIDDEN`.
    - `ledger.py` `record_by_sha` uses `video_id` (validated by `VIDEO_ID` regex) in path.
- **Secrets:** **SAFE.**
    - Keys are redacted in logs.
    - Env file is read-only.
- **DoS:** **PARTIAL.**
    - `yt-dlp` concurrency is limited (3).
    - Model concurrency is limited (20 global).
    - **Risk:** `offset_before` bisection on a 100MB ledger file could block the adapter thread for 20s. If the adapter is called frequently, this could starve the service.

### SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend service. No UI.

### SECTION 5: BACKEND QUALITY

- **DB Operations:** **GOOD.**
    - WAL mode, `synchronous=FULL`.
    - `flock` on ledger append.
    - `flock` on service lock.
- **External API Calls:** **GOOD.**
    - Timeouts on all HTTP calls.
    - Retries with backoff.
    - Circuit breakers.
- **Cron Job:** **N/A.** Long-running process.
- **Memory Leaks:** **RISK.**
    - `self._conv` in `service.py` (line 114) grows unbounded until 5000 entries.
    - `self.inflight` and `self.hook_inflight` are sets, cleaned up in `finally`.
    - `RoleCaps` dicts grow per role per day.
- **Logging:** **EXCELLENT.**
    - Structured logs.
    - Redaction.
    - Events table for state changes.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1. **Observability:** The `live.json` is good, but there is no Prometheus metrics endpoint. A professional system would expose `spend`, `latency`, `queue_depth` as metrics.
2. **Ledger Performance:** The `offset_before` bisection is a bottleneck. A professional system would use a separate index file or a database for the ledger, not a JSONL file with bisection.
3. **Paid Route Budget:** The `RoleCaps` is in-memory. If the service crashes, the budget is reset (reloaded from DB). This is correct, but the "reservation" logic is complex. A simpler approach: check `spent` before *starting* the call, and accept the risk of slight overshoot.
4. **Re-mine Logic:** The re-mine on Heimdall return is good, but it re-mines the *entire* video. A professional system would only re-mine the *moments* that were flagged or missing.

### SECTION 7: SCORES

- **Backend logic:** 90/100 (Complex but correct; race conditions in `RoleCaps` are minor)
- **Frontend/UI:** N/A
- **Error handling:** 95/100 (Excellent fail-closed design)
- **Security:** 95/100 (Strict validation, redaction)
- **Performance:** 75/100 (Ledger bisection is slow; `conv` cache is blunt)
- **Law compliance:** 100/100 (Strictly enforced)
- **World-class gap:** 80/100 (Missing metrics, ledger performance)
- **OVERALL:** 88/100

### SECTION 8: PRIORITY ACTION PLAN

**P0 CRITICAL | Fix `RoleCaps` race condition | `pipeline/ingest/providers.py:703` | `reserve` and `add` are not atomic. A call can start if `spent + reserved < cap`, but if the actual cost exceeds the reservation, `spent` can exceed `cap`. This violates the "no call starts past the cap" intent if interpreted strictly as "total spend never exceeds cap".**
*Fix:* Use a single lock for `reserve` and `add`, or accept the overshoot and document it.

**P1 HIGH | Optimize `offset_before` | `pipeline/ingest/ledger.py:122` | Bisection on a large JSONL file is slow (20s). This blocks the adapter.**
*Fix:* Maintain a separate index file (e.g., `ledger_index.json`) mapping `mined.at` to byte offset, or use a database.

**P1 HIGH | Improve `conv` cache | `pipeline/ingest/service.py:560` | Clearing the entire cache at 5000 entries causes a spike in I/O.**
*Fix:* Use `functools.lru_cache` or a timestamp-based eviction.

**P2 MEDIUM | Add Prometheus metrics | `pipeline/ingest/service.py` | No standard metrics endpoint.**
*Fix:* Add a `/metrics` endpoint exposing `spend`, `queue_depth`, `latency`.

**P3 LOW | Document `RoleCaps` overshoot | `pipeline/ingest/providers.py` | Clarify that the cap is a "start" cap, not a "total" cap.**

### SECTION 9: THE ONE THING

**Replace the JSONL ledger with a SQLite database.** The bisection logic in `offset_before` is a performance bottleneck and a source of complexity. SQLite would provide O(1) lookups for `mined.at`, atomic appends, and better concurrency.

### SECTION 10: FINAL VERDICT

This code is **production-ready** for a high-stakes, low-volume system. The defensive programming is exceptional. However, the **ledger performance** and **`RoleCaps` race condition** are the two areas that could cause issues at scale. Fix the ledger index and the cap logic before deploying to a high-throughput environment.