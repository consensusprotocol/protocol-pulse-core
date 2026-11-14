# heimdall_qwen (qwen/qwen3.8-27b, 267.8 s, $0.024, finish stop)

## PROTOCOL PULSE — CODE AUDIT: pp-ingest (Continuous Ingest + First-Pass Mining)

### SECTION 1: CORRECTNESS

**1. The "Spotlight" Prompt Contradicts Its Own Definition (Critical Logic Error)**
In `pipeline/ingest/mine.py`, the `SPOT_PROMPT` (lines 228-297) explicitly instructs the model:
> "A SPOTLIGHT is ONE passage of ONE speaker... point to the **1 to {max_h} passages** in this window..."

However, `SPOT_MAX` is defined as `2` (line 135). The prompt tells the model it can return up to 2 spotlights. But the *definition* of a spotlight in the orchestrator's ruling (and the prompt's own "WHAT A SPOTLIGHT IS" section) emphasizes it is a **single** complete claim/number/question that stands alone. While the code allows 2, the prompt's phrasing "1 to 2 passages" is technically consistent with the code, but the *intent* of a "spotlight" (a single hero moment) is diluted. More critically, the **validator** (`mine.validator`) is called with `max_n=2` for spotlights. If the model returns 2 valid spotlights, they are both written. This is not a bug per se, but it deviates from the "ONE passage" spirit of Ruling 90 if interpreted strictly. However, the code is internally consistent: `SPOT_MAX=2`, prompt says "1 to 2", validator allows 2. **Verdict: Compliant, but potentially over-generating "spotlights" if the model is greedy.**

**2. Race Condition in `hook_video` Cost Calculation**
In `pipeline/ingest/service.py` (lines 407-408), the cost is calculated by querying the database for `SUM(cost_usd)` for the video's `hook` and `spotlight` roles.
```python
cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role IN "
                   "('hook', 'spotlight')", (vid,))[0]["usd"] or 0.0
```
This query runs **after** the mining is complete. However, `mine_video` (called for both hook and spotlight) submits tasks to `self.hook_windows` (a `ThreadPoolExecutor`). The `mine_video` function waits for all futures to complete (`as_completed`). So by the time `hook_video` reaches the cost query, all calls for this video's hook/spotlight pass should be recorded in the `calls` table via `on_attempt`.
**However**, `on_attempt` is called by the `Router` inside `mine_window`. The `Router` is shared. If another video's mining is happening concurrently, the `calls` table is being written to by other threads. The query is atomic (SQLite WAL mode), so it will see a consistent snapshot. The cost will include **only** the calls for this video because it filters by `video_id`. This is correct.

**3. `episode_measure` is Called Twice**
In `service.py` `hook_video`:
1. `mine.mine_video(..., kind="hook")` is called. Inside `mine_video` (line 564), `episode = episode_measure(rec)` is called.
2. If `is_conversation(ep)` is true, `mine.mine_video(..., kind="spotlight")` is called. Inside this second call, `episode_measure(rec)` is called **again** (line 564).
This is redundant but not incorrect. It just wastes CPU cycles parsing the transcript segments again. **Impact: Low.**

**4. `max_n` Propagation in `mine_window`**
In `mine.py` `mine_window` (line 504):
```python
n = max_n or k["max_n"]
```
If `max_n` is `None`, it uses the kind's default. In `mine_video` (line 565):
```python
max_n = HOOK_MAX_CONVERSATION if kind == "hook" and is_conversation(episode) else KINDS[kind]["max_n"]
```
For `kind="hook"`, if it's a conversation, `max_n=5`. If not, `max_n=3` (HOOK_MAX).
For `kind="spotlight"`, `max_n` is always `KINDS["spotlight"]["max_n"]` which is `2`.
This is passed to `mine_window`. Inside `mine_window`, the prompt is formatted with `max_h=n`. The validator is called with `max_n=n`. This is correct.

**5. `carry_forward` Logic for `role_hint`**
In `ledger.py` (lines 205-206):
```python
if e.get("role_hint") and not l.get("role_hint"):
    l["role_hint"] = e["role_hint"]
```
This ensures that if a later line (e.g., a spotlight row) is appended for a moment that already has a hook row, the hook's `role_hint` is preserved if the spotlight row doesn't have one? No, `l` is the **new** line, `e` is the **earlier** line.
If `l` (new) has no `role_hint` and `e` (old) has one, it copies it.
If `l` (new) has `role_hint="spotlight"` and `e` (old) has `role_hint="hook"`, `l` keeps "spotlight".
This is correct: the latest line's hint wins, but if the latest line *lacks* a hint, it inherits the previous one. This prevents loss of information.

**6. `stats.py` Conversation Count**
In `stats.py` (line 111):
```python
"SUM(COALESCE(episode_tpm >= ?, 0)) AS convs"
```
This counts videos where `episode_tpm` is not NULL and is >= `CONVERSATION_TPM`. This is correct.

**7. `purge.py` `delivered` Set Construction**
In `purge.py` `delivered` (line 184):
```python
why = [f"pin {p} (stand-alone scorer: delivered)" for p in sorted(pins) if p in joined]
```
This checks if the pin ID is in the text of the run records. This is a heuristic. If a pin ID appears in a log file but the video wasn't actually delivered, it might be protected. However, the spec says "a run that rendered a pin the stand-alone scorer records as delivered". The scorer results are in `delivered_*.json`. The code reads `run_records` (status.json, etc.) and checks for the pin ID. This is a reasonable approximation, but could be fragile if pin IDs are reused or mentioned in non-delivery contexts. **Risk: Low-Medium.**

### SECTION 2: LAW COMPLIANCE

*   **L-x (No Single Model, Ultron First):** **COMPLIANT.** `providers.json` defines chains with multiple backends. `Router` tries them in order. Local model is first in `mine` chain (though disabled).
*   **L-l (Reply Counts Only Whole):** **COMPLIANT.** `validator` in `mine.py` is strict. It rejects any deviation from the schema. No repair logic.
*   **L-j/L-m (Fail Closed):** **COMPLIANT.** `config.check_store` raises `StoreGuard` if store is in main tree. `ledger.best_unused_moments` excludes lines with contract drift. `purge` refuses to run if delivered set is unreadable.
*   **L-h/L-k (Read As Spoken):** **COMPLIANT.** `contract.sentences` uses `eligibility.spoken`.
*   **L-u (Hard Exclusions):** **COMPLIANT.** `mine.HARD_RISKS` are flagged. `ledger.best_unused_moments` excludes them.
*   **L-v (Speaker Change):** **COMPLIANT.** `contract.turn_change_inside` checks for `>>` markers. `ledger` excludes moments with `turn_change_inside=True`.
*   **Spend Freeze:** **COMPLIANT.** `providers.Router.frozen` checks `spend_freeze.vendors`. `mine_paid` role has `freeze_lifted` and `daily_cap_usd`.
*   **Ruling 76/77 (Expiry/Purge):** **COMPLIANT.** `config.EXPIRY_H=12`. `ledger.expiry` calculates expiry. `purge.py` deletes media older than 12h.
*   **Ruling 80 (Hook Pass):** **COMPLIANT.** `mine.HOOK_PROMPT` exists. `service.hook_video` runs it.
*   **Ruling 92 (Conversations):** **COMPLIANT.** `mine.is_conversation` checks `turns_per_min >= 1.0`.
*   **Ruling 98 (Paid Route):** **COMPLIANT.** `downsignal._route_tick` opens paid route after 20 min down. `mine_paid` role is used.

### SECTION 3: SECURITY

*   **SQL Injection:** **SAFE.** All SQL queries use parameterized queries (`?` placeholders). No string concatenation of user input into SQL.
*   **Secrets:** **SAFE.** API keys are read from env file via `Keyring`. `Keyring.redact` is used to redact keys from error messages.
*   **Path Traversal:** **SAFE.** `config.check_store` ensures the store is not in the main tree. `purge.py` checks `FORBIDDEN` paths.
*   **Command Injection:** **SAFE.** `yt-dlp` is called via `subprocess` with a list of arguments, not a shell string.
*   **Unvalidated Input:** **SAFE.** `watch.rss_list` parses XML with `ElementTree`. `fetch.probe` parses JSON. `mine.validator` strictly validates model output.

### SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend service. There is no UI.

### SECTION 5: BACKEND QUALITY

*   **DB Operations:** **GOOD.** SQLite WAL mode is used. Transactions are implicit in `Queue.x` (autocommit). `ledger.append` uses `fsync` for durability.
*   **External API Calls:** **GOOD.** `providers.py` has timeouts, retries, and circuit breakers. `yt-dlp` has a rate-limit breaker.
*   **Cron Job:** **N/A.** It's a long-running process, not a cron job.
*   **Memory Leaks:** **GOOD.** `ThreadPoolExecutor` is used for concurrency. `deque` is used for health events with `maxlen`.
*   **Logging:** **GOOD.** `service._log` writes to a file and stdout. Errors are logged with context.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Observability:** The service writes to `live.json` and `STATE.md`, but there is no structured logging (e.g., JSON logs) for ingestion into a log aggregator (ELK, Datadog). For a production system, this would be expected.
2.  **Testing:** The test suite is extensive (304 tests), but there are no integration tests that simulate a full end-to-end flow with a mock YouTube API and a mock LLM. The unit tests are good, but integration tests would catch more issues.
3.  **Documentation:** The code is well-commented, but there is no API documentation for the `ledger.best_unused_moments` function, which is the main interface for the packager.
4.  **Performance:** The `ledger.best_unused_moments` function reads the entire ledger file and filters it in Python. For a large ledger (millions of lines), this could be slow. A database index on `mined_at` and `video_id` would be more efficient. However, the ledger is append-only and JSONL, so a database would require a migration.

### SECTION 7: SCORES

*   **Backend logic:** 95/100
*   **Frontend/UI:** N/A
*   **Error handling:** 95/100
*   **Security:** 95/100
*   **Performance:** 85/100
*   **Law compliance:** 100/100
*   **World-class gap:** 80/100
*   **OVERALL:** 92/100

### SECTION 8: PRIORITY ACTION PLAN

*   **P1 HIGH** | Add structured logging (JSON) for ingestion into a log aggregator | `pipeline/ingest/service.py` | For production observability.
*   **P2 MEDIUM** | Optimize `ledger.best_unused_moments` to use a database index or a more efficient filtering strategy | `pipeline/ingest/ledger.py` | For performance with large ledgers.
*   **P3 LOW** | Add integration tests with mock YouTube API and LLM | `tests/ingest/` | For end-to-end validation.

### SECTION 9: THE ONE THING

Add structured logging (JSON) to the service for production observability.

### SECTION 10: FINAL VERDICT

This code is ready for production. It is well-designed, secure, and compliant with all governing laws. The only significant gap is the lack of structured logging for production observability.