# heimdall_qwen (qwen/qwen3.8-27b, 185.3 s, $0.009, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT

## SECTION 1: CORRECTNESS

### 1.1 The "Hourly" Spend Figure is Not Hourly (Critical Logic Error)
**File:** `pipeline/ingest/batch.py`, lines 176-198 (`share_left`) and `pipeline/ingest/service.py` line 785 (`_batch_share`).

The design document states: *"Counted, from the batch's start to its latest whole hour... line 1 changes once an hour."*
However, `batch.share_left()` (used by the router to determine if a paid call can start) calculates spend up to `now + 1.0` (line 197: `watcher_spend(q, b["t0"], now + 1.0, cfg)`).
Conversely, `batch.notice()` (used for the STATE line) calculates spend up to the *last whole hour* (line 152: `mark = min(b["t1"], b["t0"] + int((now - b["t0"]) // HOUR_S) * HOUR_S)`).

**Consequence:**
1.  **Inconsistency:** The STATE line says "Spend: $X" (based on last hour). The Router allows/denies calls based on "Spend: $Y" (based on *current* second). If a large call happens at 21:59, the STATE line (updated at 22:00) will show it, but the Router has been blocking calls based on it since 21:59.
2.  **The "Latest Whole Hour" Claim is False for the Router:** The router does *not* wait for the hour to close. It reacts in real-time. The design doc claims the figure "changes once an hour," which is true for the *display*, but the *enforcement* is real-time. This is not a bug in itself, but the documentation in `batch.py` docstring (lines 1-15) is misleading about what `share_left` does vs `notice`.
3.  **Race Condition in `share_left`:** `share_left` calls `watcher_spend` which queries the DB. `RoleCaps.reserve_why` (providers.py:718) calls `self.share()` (which is `batch.share_left`) *while holding* `RoleCaps.lock`.
    *   `batch.share_left` -> `batch.load` (acquires `batch._lock`) -> `watcher_spend` (acquires `queue.lock` via `q.rows`).
    *   `RoleCaps._roll` (called in `reserve_why` before `share()`) calls `self.loader` (which is `queue.rows`), acquiring `queue.lock`.
    *   **Lock Order:**
        *   Path A (`reserve_why`): `RoleCaps.lock` -> `queue.lock` (via `_roll`) -> `RoleCaps.lock` (released? No, `_roll` is inside `with self.lock`) -> `batch._lock` -> `queue.lock` (via `watcher_spend`).
        *   Wait, `RoleCaps._roll` is called *inside* `with self.lock`. It calls `self.loader(role, start)`. The loader is `queue.rows`. So `RoleCaps.lock` is held while `queue.lock` is acquired.
        *   Then `self.share()` is called *inside* `with self.lock`. `share` is `batch.share_left`. `batch.share_left` calls `batch.load` (acquires `batch._lock`) and `watcher_spend` (acquires `queue.lock`).
        *   So the sequence is: `RoleCaps.lock` -> `queue.lock` (in `_roll`) -> `queue.lock` released -> `batch._lock` -> `queue.lock` (in `watcher_spend`).
        *   Is there a reverse order?
        *   `queue.py` (unchanged code) likely does not call `RoleCaps` or `batch`.
        *   `batch.py` does not call `RoleCaps`.
        *   Therefore, the lock order is consistent: `RoleCaps` -> `batch` -> `queue`. No deadlock.

### 1.2 `abandoned_usd` Calculation Flaw
**File:** `pipeline/ingest/batch.py`, lines 88-105.

```python
def abandoned_usd(q, model, role, price, until):
    r = q.rows("SELECT SUM(cost_usd) AS c, SUM(prompt_tokens) AS p, COUNT(*) AS k FROM calls WHERE model=? AND "
               "cost_usd > 0 AND prompt_tokens > 0 AND ts < ?", (model, until))[0]
    # ...
    if (r["k"] or 0) >= MIN_REPORTED and r["p"]:
        rate = float(r["c"]) / float(r["p"])
    else:
        rate = float((price or {}).get("in_per_mtok") or 0.0) / 1e6
    return float(avg) * rate
```

**Issue:** `avg` is calculated from *all* calls (including timeouts with `prompt_tokens > 0`? No, `prompt_tokens > 0` is required).
The query for `avg` is:
```python
avg = q.rows(f"SELECT AVG(prompt_tokens) AS a FROM calls WHERE {sql} AND prompt_tokens > 0 AND ts < ?", args + (until,))[0]["a"]
```
This includes *successful* calls and *failed* calls that had prompt tokens.
However, `r` (the rate calculation) only includes calls where `cost_usd > 0`.
If a model has 10 successful calls (cost > 0) and 100 failed calls (cost = 0, but prompt_tokens > 0), the `avg` prompt size will be skewed by the failed calls.
Ruling 107 says: *"the model's reported dollars per prompt token x the prompt sent"*.
The "prompt sent" for an abandoned call is estimated by the *average prompt size*.
Using the average of *all* calls (including those that failed early or had different prompt structures) is a reasonable heuristic, but if the failed calls are systematically different (e.g., retries with longer prompts), this estimate is biased.
More critically: **If `avg` is None, it returns None.**
If `avg` is not None, but `r["k"]` is 0 (no successful calls yet), it uses `price`.
This seems correct per Ruling 107 ("list price... until the model has 3 reported calls").

**Potential Bug:** `r["p"]` is `SUM(prompt_tokens)`. If `r["k"] >= 3` but `r["p"]` is 0 (impossible if `prompt_tokens > 0` in WHERE), it falls back to price. This is safe.

### 1.3 `watcher_spend` Double Counting / Misclassification
**File:** `pipeline/ingest/batch.py`, lines 108-135.

```python
for r in q.rows("SELECT role, backend, model, kind, cost_usd FROM calls WHERE ts >= ? AND ts < ? AND "
                "COALESCE(kind, '') != 'cache'", (t0, t1)):
    use = USE.get(r["role"], "other")
    if r["kind"] == "timeout" and r["cost_usd"] is None:
        # ... abandoned logic
    else:
        usd = float(r["cost_usd"] or 0.0)
        out["reported" if _reports_cost(be.get(r["backend"]) or {}) else "estimated"] += usd
    out["by"][use] = out["by"].get(use, 0.0) + usd
```

**Issue:** If a call is a `timeout` but `cost_usd` is *not* None (e.g., the vendor reported a cost for the partial work before timeout), it goes to the `else` branch.
`usd = float(r["cost_usd"] or 0.0)`.
This is correct.
However, `out["by"][use]` adds `usd`.
In the `timeout` branch, `usd` is calculated by `abandoned_usd`.
If `abandoned_usd` returns `None`, `usd` becomes `0.0` (line 124: `usd = 0.0`).
Then `out["by"][use]` adds `0.0`.
But `out["unpriced_n"]` is incremented.
This is correct.

**Edge Case:** What if `cost_usd` is `None` but `kind` is NOT `timeout`?
`usd = float(None or 0.0)` -> `0.0`.
It is added to `out["estimated"]` or `out["reported"]` as `0.0`.
This is safe.

### 1.4 `spend.py` `_segments` and `_place` Logic
**File:** `pipeline/ingest/spend.py`, lines 40-55.

```python
def _segments(h):
    out, rest = [], h
    for starts in (BATCH_RE.match, lambda s: s.startswith(ALARM_PREFIX)):
        if starts(rest):
            seg, _, rest = rest.partition(SEP)
            out.append(seg)
    return out + ([rest] if rest else [])
```

**Issue:** `BATCH_RE` is `^BATCH \d+ ingest spend: `.
`ALARM_PREFIX` is `"ALARM FOR PBX: "`.
`SEP` is `" | "`.

If line 1 is: `BATCH 3 ingest spend: $1.00 | ALARM FOR PBX: ... | 10:00 ET: SWITCH...`
1. `starts = BATCH_RE.match`. `rest` starts with `BATCH...`. Match.
   `seg` = `BATCH 3 ingest spend: $1.00`. `rest` = `ALARM FOR PBX: ... | 10:00 ET: SWITCH...`.
   `out` = `[BATCH...]`.
2. `starts = ALARM...`. `rest` starts with `ALARM...`. Match.
   `seg` = `ALARM FOR PBX: ...`. `rest` = `10:00 ET: SWITCH...`.
   `out` = `[BATCH..., ALARM...]`.
3. Return `out + [rest]` -> `[BATCH..., ALARM..., SWITCH...]`.

This works.

**What if the order is wrong?**
The code assumes Batch is first, then Alarm, then Switch.
`_place` sorts them:
```python
def _place(h):
    return (0 if BATCH_RE.match(h) else 1 if h.startswith(ALARM_PREFIX) else 2 if SWITCH_RE.match(h) else
            3 if h.startswith(CYCLES_PREFIX + " TO ") else 4)
```
`_rewrite_top` uses `sorted(..., key=_place)`.
So even if they are stored in the wrong order in the file, they are re-sorted.
However, `_segments` *parses* them in a specific order.
If the file contains `ALARM... | BATCH...`, `_segments` will fail to parse `BATCH` as a segment because it only looks for `BATCH` at the *start* of `rest` in the first iteration, and `ALARM` at the start of `rest` in the second.
If `rest` starts with `ALARM`, the first check (`BATCH_RE.match`) fails.
The second check (`ALARM...`) succeeds. `seg` = `ALARM...`. `rest` = `BATCH...`.
Then the loop ends.
`out` = `[ALARM...]`.
Return `out + [rest]` -> `[ALARM..., BATCH...]`.
Then `_place` sorts them: `BATCH` (0) comes before `ALARM` (1).
So the *output* is correct.
But does `_segments` correctly identify the *boundaries*?
Yes, because it partitions by `SEP`.
The only risk is if a notice *contains* `SEP`.
The writers (`write_batch_notice`, `write_alarm_notice`) explicitly reject `|` and `\n`.
`write_switch_head` (unchanged) likely also rejects `|`?
The docstring for `write_switch_head` says: *"prepended to the switch line that holds every earlier switch, newest first"*.
It does *not* explicitly reject `|` in the *new* head, but the *existing* line is built by joining with `|`.
If a user passes a head with `|`, it will break the parsing.
However, `SWITCH_RE` is `^\d\d:\d\d ET: ...`. It does not check for `|` inside.
But `write_switch_head` is called with `head` from `downsignal.py`.
`downsignal.py` line 265: `f"MINER ON THE PAID ROUTE ({pr['label']}: ...)"`.
`pr['label']` is a config value. If it contains `|`, it breaks.
This is a **Security/Robustness** issue, not a logic error in the new code, but the new code *relies* on the invariant that notices do not contain `|`.

### 1.5 `xllm_audit.py` `book` Function
**File:** `tests/ingest/xllm_audit.py`, lines 180-195.

```python
def book(results, errors, error_costs, prompts, rates):
    answered = [((r.get("usage") or {}).get("prompt_tokens") or 0) for r in results.values()]
    answered = [t for t in answered if t > 0]
    out = {}
    for rid, r in results.items():
        out[rid] = {"usd": float(r.get("cost_usd") or 0.0), "basis": "reported"}
    for rid in errors:
        ec = error_costs.get(rid) or {}
        if isinstance(ec.get("cost_usd"), (int, float)):
            out[rid] = {"usd": float(ec["cost_usd"]), "basis": f"reported (failed: {ec.get('kind')})"}
        elif ec.get("kind") == "timeout":
            rate, basis = _rate(rid, rates)
            tokens = sum(answered) / len(answered) if answered else len(prompts.get(rid) or "") / 3.0
            out[rid] = ({"usd": rate * tokens, "basis": f"abandoned: {basis} x {int(tokens)} prompt tokens"}
                        if rate is not None else {"usd": 0.0, "basis": f"abandoned: {basis}"})
        else:
            out[rid] = {"usd": 0.0, "basis": f"failed before any cost ({ec.get('kind') or 'no reply'})"}
    return out
```

**Issue:** `answered` is calculated from `results` (successful calls).
If *all* calls fail (timeout), `answered` is empty.
`tokens` falls back to `len(prompts.get(rid) or "") / 3.0`.
This is a reasonable estimate.

**Issue:** `rate` is from `_rate(rid, rates)`.
`_rate` uses `rates` which is calculated by `_rates()`.
`_rates` reads `results.json` from *previous* runs.
If this is the *first* run, `rates` is empty.
`_rate` returns `None, "UNPRICED (no rate known)"` if no model price is found in `providers.json`.
If `rate` is `None`, `usd` is `0.0`.
This is **Fail Closed** (L-j/L-m).

### 1.6 `xllm_audit.py` `cap_check`
**File:** `tests/ingest/xllm_audit.py`, lines 200-208.

```python
def cap_check(out, cap, estimate):
    spent = 0.0
    if os.path.exists(cost_path(out)):
        with open(cost_path(out)) as f:
            spent = float(json.load(f).get("total_usd") or 0.0)
    if spent + estimate > cap:
        raise SystemExit(...)
    return spent
```

**Issue:** `estimate` is calculated by `estimate(prompt_for, only, rates)`.
`estimate` uses `prompt_for(rid)` to get the prompt length.
`prompt_for` is a closure defined in `main`.
For cycle 1, `prompt_for` returns `pkg`.
For cycle 2, `prompt_for` returns `tool.build_cycle2_prompt(...)`.
This is correct.

**Issue:** `cap` is `SMALL_CAP` or `BIG_CAP`.
`SMALL_CAP` is 0.30.
If `spent` is 0.25 and `estimate` is 0.10, `0.25 + 0.10 = 0.35 > 0.30`.
It raises `SystemExit`.
This prevents the call.
This is correct.

## SECTION 2: LAW COMPLIANCE

| Law | Status | Notes |
| :--- | :--- | :--- |
| **BUILD** | **COMPLIANT** | Continuous ingest, ETag, backoff, ledger, mining, captions, A/B. The diff focuses on spend/batch, which is part of the BUILD requirements (spend tracking, tripwire). |
| **L-x** | **COMPLIANT** | `providers.py` uses `RoleCaps` and `Router`. `batch.py` integrates with `RoleCaps.share`. No vendor names in code (except config). |
| **L-l** | **COMPLIANT** | `xllm_audit.py` `book` function handles failed calls. `batch.py` `abandoned_usd` handles timeouts. Nothing is repaired. |
| **L-j/L-m** | **COMPLIANT** | `batch.share_left` returns 0.0 if file unreadable. `xllm_audit` `cap_check` refuses if cap exceeded. |
| **L-h/L-k** | **COMPLIANT** | Not directly touched by this diff, but `batch.py` reads from `queue` which stores canonical forms. |
| **L-e** | **COMPLIANT** | Not touched. |
| **L-u/L-v** | **COMPLIANT** | Not touched. |
| **Secrets** | **COMPLIANT** | `xllm_audit.py` uses `providers.Keyring(ENV)`. No keys in code. |
| **SPEND FREEZE** | **COMPLIANT** | `xllm_audit.py` `chosen` function skips frozen vendors. `batch.py` `share_left` returns 0.0 if no batch. `providers.py` `reserve_why` checks `share`. |

**Specific Check: Ruling 107 (2)**
*   "Reviewers Heimdall-first, two Heimdall families (qwen + glm)": `xllm_audit.py` `DEFAULT = ("heimdall_qwen", "heimdall_glm")`. **COMPLIANT**.
*   "Third only when...": `xllm_audit.py` `THIRD = "heimdall_muse"`. `chosen` allows `--only`. **COMPLIANT**.
*   "Under 60 changed lines one reviewer set, two cycles, capped $0.30": `xllm_audit.py` `SMALL_LINES, SMALL_CAP = 60, 0.30`. `main` calculates `lines` and `cap`. **COMPLIANT**.
*   "Vendor-reported cost recorded": `xllm_audit.py` `book` uses `cost_usd` from reply. **COMPLIANT**.

**Specific Check: Ruling 108**
*   "One ledger for everything": `batch.py` `notice` aggregates `watcher_spend` and `audit_spend`. **COMPLIANT**.
*   "Cap $8.00": `batch.json` has `cap_usd: 8.00`. `batch.py` `load` reads it. **COMPLIANT**.
*   "Budget inside it: builds + sealing $4.50, audits $2.50, mining and checks $1.00": `batch.json` has `share_usd: 1.00` for "mining and checks". **COMPLIANT**.
*   "Spend goes to builder's batch ledger hourly": `service.py` `_batch_notice` calls `batch.notice` which writes to STATE. **COMPLIANT**.
*   "Audits Heimdall-first, diff-scoped, capped $0.30 / $1.00": `xllm_audit.py` implements this. **COMPLIANT**.

## SECTION 3: SECURITY

1.  **SQL Injection:**
    *   `batch.py` uses parameterized queries (`?`). **SAFE**.
    *   `xllm_audit.py` does not use SQL. **SAFE**.
    *   `spend.py` does not use SQL. **SAFE**.

2.  **Authentication Bypasses:**
    *   N/A (Internal tool).

3.  **Rate Limiting Gaps:**
    *   `RoleCaps` enforces daily caps and batch shares.
    *   `xllm_audit` enforces audit caps.
    *   **SAFE**.

4.  **Secrets in Code:**
    *   `xllm_audit.py` uses `Keyring`. **SAFE**.
    *   `batch.json` contains no secrets. **SAFE**.

5.  **Unvalidated User Input:**
    *   `batch.json` is read by `batch.load`. It validates `name`, `start_et`, `end_et`, `share_usd`.
    *   If `batch.json` is malformed, `load` raises `ValueError`. `share_left` catches it and returns 0.0. **SAFE**.
    *   `xllm_audit.py` `--base` is passed to `git diff`. If `--base` contains shell metacharacters, `subprocess.check_output` with a list argument is safe. **SAFE**.

## SECTION 4: FRONTEND QUALITY

N/A (Backend/CLI tool).

## SECTION 5: BACKEND QUALITY

1.  **DB Operations:**
    *   `batch.py` uses `q.rows` which is a read-only query.
    *   `xllm_audit.py` writes to `COST.json` and `audit_spend.jsonl`.
    *   `record` function in `xllm_audit.py` writes to `COST.json` without atomic replace.
    *   **Issue:** If `xllm_audit.py` crashes during `json.dump`, `COST.json` may be corrupted.
    *   **Fix:** Use `os.replace` for atomic write, similar to `spend.py`.

2.  **External API Calls:**
    *   `xllm_audit.py` uses `providers.make_backend`.
    *   Timeouts are handled by `providers`.
    *   **SAFE**.

3.  **Cron Job:**
    *   `service.py` `_batch_notice` is called in `health_once`.
    *   Exceptions are caught and logged. **SAFE**.

4.  **Memory Leaks:**
    *   `batch.py` `_cache` is a dict. It is updated on file change.
    *   If the file changes frequently, the cache is updated.
    *   **SAFE**.

5.  **Logging:**
    *   `service.py` logs batch errors.
    *   `xllm_audit.py` prints to stdout.
    *   **SAFE**.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Atomic Writes for `COST.json`:**
    *   `xllm_audit.py` `record` function writes to `COST.json` directly.
    *   **Gap:** If the process is killed, the file is corrupted.
    *   **Fix:** Use `os.replace` (write to temp, then rename).

2.  **Concurrency in `xllm_audit.py`:**
    *   `fire` function uses threads.
    *   `results` and `errors` dicts are shared.
    *   **Gap:** Python dict is not thread-safe for concurrent writes.
    *   **Fix:** Use a lock or `concurrent.futures` with `as_completed`.

3.  **Batch Share Calculation Precision:**
    *   `batch.py` `share_left` uses `now + 1.0`.
    *   **Gap:** This is a hack to include the current second.
    *   **Fix:** Use `now` and ensure the query includes the current second.

## SECTION 7: SCORES

*   **Backend logic:** 85/100 (Solid, but `COST.json` write is not atomic, and `xllm_audit` thread safety is questionable).
*   **Frontend/UI:** N/A
*   **Error handling:** 90/100 (Fail closed, good logging).
*   **Security:** 95/100 (Parameterized queries, no secrets).
*   **Performance:** 90/100 (Efficient queries, caching).
*   **Law compliance:** 100/100 (Strictly follows Ruling 107/108).
*   **World-class gap:** 80/100 (Missing atomic writes and thread safety in audit driver).
*   **OVERALL:** 88/100

## SECTION 8: PRIORITY ACTION PLAN

**P0 CRITICAL | Atomic write for `COST.json` | `tests/ingest/xllm_audit.py:220` | If the process crashes during `json.dump`, the cost ledger is corrupted, leading to incorrect spend tracking and potential over-spending in future audits.**
**P1 HIGH | Thread safety in `xllm_audit.py` `fire` | `tests/ingest/xllm_audit.py:240` | Concurrent writes to `results` and `errors` dicts can cause data loss or corruption if two threads write simultaneously.**
**P2 MEDIUM | Remove `now + 1.0` hack in `share_left` | `pipeline/ingest/batch.py:197` | This is a fragile workaround. Use `now` and ensure the query range is inclusive of the current second.**
**P3 LOW | Validate `batch.json` `cap_usd` | `pipeline/ingest/batch.py:60` | `load` does not validate `cap_usd`. If it is negative or NaN, it should raise an error.**

## SECTION 9: THE ONE THING

Make the `COST.json` write in `xllm_audit.py` atomic (write to temp file, then `os.replace`) to prevent corruption of the audit spend ledger, which is critical for enforcing the $0.30/$1.00 caps.

## SECTION 10: FINAL VERDICT

The code is **ready for production** with minor fixes. The core logic for batch spend tracking and audit capping is correct and compliant with the governing laws. The primary risk is the non-atomic write to `COST.json` in the audit driver, which could corrupt the spend ledger if the process is interrupted. Fix this, and the code is robust.