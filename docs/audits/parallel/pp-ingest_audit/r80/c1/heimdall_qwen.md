# heimdall_qwen (qwen/qwen3.8-27b, 705.7 s, $0.009, finish stop)

This is a highly sophisticated, defensive engineering package. The code demonstrates a deep understanding of distributed systems, fail-closed logic, and strict data integrity. It is not a "prototype"; it is a production-grade pipeline component.

However, the review task asks for a forensic audit. I will focus on the specific changes in the diff (Ruling 77 fixes and Ruling 80 Hook Pass) and the interaction between the new hook logic and the existing ledger/adapter logic.

### SECTION 1: CORRECTNESS

**1. Race Condition in `carry_forward` (Critical)**
In `pipeline/ingest/service.py`, the `_append` method (line 262) acquires `self.wlock` to perform `ledger.carry_forward` and `ledger.append`.
```python
def _append(self, v, lines):
    if not lines:
        return 0
    since = datetime.fromtimestamp(float(v.get("discovered_ts") or self.clock()) - 86400, timezone.utc)
    with self.wlock:
        ledger.carry_forward(lines, ledger.video_lines(self.p["ledger"], v["video_id"], since))
        return ledger.append(self.p["ledger"], lines, stamp=config.iso)
```
`ledger.video_lines` reads the ledger file. `ledger.append` writes to it.
The `wlock` is a `threading.Lock` local to the `Service` instance.
**The Problem:** The design doc states: *"One service per store... a second one is refused before it recovers anything."* (Section 7). This implies only one process writes to the ledger.
**However**, `ledger.append` uses `fcntl.flock` on the file descriptor. `ledger.video_lines` does **not** hold a lock while reading.
If the `Service` process is the *only* writer, `wlock` serializes the read-modify-write cycle within the process. This is correct for single-process concurrency.
**But**, consider the `hook` loop and `mine` loop. They both call `_append`. `wlock` protects them.
Is there a scenario where `video_lines` reads a stale state?
If `mine` appends a line, then `hook` appends a line for the *same* `moment_id` (same video, same span), `hook`'s `video_lines` read must see `mine`'s line.
Since `mine`'s `_append` releases `wlock` after `ledger.append` completes (fsync), and `hook`'s `_append` acquires `wlock` before `video_lines`, the read is consistent.
**Verdict:** Correct for single-process. The `fcntl` lock in `append` is redundant but safe.

**2. Hook Duration Calculation (Logic Error)**
In `pipeline/ingest/mine.py`, `build_line` (line 345) calculates `dur`:
```python
start, end = toks[w0].get("start"), toks[w1].get("end")
dur = round(max(0.0, float(end) - float(start)), 2) if isinstance(start, (int, float)) and \
    isinstance(end, (int, float)) else None
```
Then in `mine_video` (line 430):
```python
secs = KINDS[kind]["seconds"]
if secs:
    kept = []
    for l in lines:
        d = l["duration_s"] if l["duration_s"] is not None else l["duration_estimate_s"]
        why = ("duration not measured" if d is None else
               None if secs[0] <= d <= secs[1] else f"outside {secs[0]:g}-{secs[1]:g} s")
```
For `kind="hook"`, `secs` is `(4.0, 14.0)`.
The caption records have `timing: "segment"`.
In `contract.py` `sentences` (line 115), `start` and `end` come from `toks[w0].get("start")` and `toks[w1].get("end")`.
In `build_line` (line 364):
```python
"duration_s": dur if timing == "word" else None,
"duration_estimate_s": None if timing == "word" else dur,
```
So for segments, `duration_s` is `None`, `duration_estimate_s` is `dur`.
The check `d = l["duration_s"] if ... else l["duration_estimate_s"]` correctly picks `dur`.
**Verdict:** Correct.

**3. `hook_due` Query Logic**
In `pipeline/ingest/queue.py` (line 177):
```python
def hook_due(self, horizon_s, limit=50):
    now = self.clock()
    return self.rows(f"SELECT * FROM videos WHERE state IN (?, ?) AND hook_ts IS NULL AND COALESCE(hook_next_ts, 0) "
                     "<= ? AND published_ts >= ? ORDER BY published_ts DESC LIMIT ?",
                     (MINED, MINED_PARTIAL, now, now - horizon_s, limit))
```
This selects videos that are `MINED` or `MINED_PARTIAL`, have not had a hook pass (`hook_ts IS NULL`), are due for retry (`hook_next_ts <= now`), and were published within the last `horizon_s` (12h).
**Edge Case:** What if a video is `MINED` but `published_ts` is `NULL`?
`published_ts >= ?` will be `NULL >= X`, which is `NULL` (falsy) in SQL. So it won't be selected.
Is this correct?
Ruling 80 says: *"Videos published more than 12 h ago are never hook-mined: their moments are expired."*
If `published_ts` is unknown, we don't know if it's expired.
However, `fetch.py` (line 169) sets `PROBE_RETRY` if `pub_ts is None`. It never reaches `TRANSCRIBED`/`MINED` without a publish time.
So `MINED` videos always have `published_ts`.
**Verdict:** Correct.

**4. `carry_forward` Flag Union Logic**
In `pipeline/ingest/ledger.py` (line 187):
```python
def carry_forward(lines, earlier):
    by = {}
    for e in earlier:
        by.setdefault(e.get("moment_id"), []).append(e)
    for l in lines:
        for e in by.get(l["moment_id"], []):
            l["risk"] = sorted(set(l["risk"]) | set(e.get("risk") or []))
            l["names_person"] = bool(l["names_person"] or e.get("names_person"))
            fx, ex = l.setdefault("flags_ext", {}), e.get("flags_ext") or {}
            fx["altcoin"] = bool(fx.get("altcoin") is not False or ex.get("altcoin") is not False)
            fx["about_bitcoin"] = bool(fx.get("about_bitcoin") is True and ex.get("about_bitcoin") is True)
            if e.get("role_hint") == "hook":
                l["role_hint"] = "hook"
    return lines
```
**Logic Check:**
- `risk`: Union. Correct (fail closed).
- `names_person`: OR. Correct.
- `altcoin`: `fx.get("altcoin") is not False or ex.get("altcoin") is not False`.
  - If `fx` is `True` or `None` (not False), result is `True`.
  - If `fx` is `False` and `ex` is `True` or `None`, result is `True`.
  - If both are `False`, result is `False`.
  - This is effectively `OR` with `None` treated as `True` (fail closed). Correct.
- `about_bitcoin`: `fx.get("about_bitcoin") is True and ex.get("about_bitcoin") is True`.
  - If either is `False` or `None`, result is `False`.
  - This is effectively `AND` with `None` treated as `False` (fail closed). Correct.
- `role_hint`: If *any* earlier line was a hook, the new line becomes a hook.
  - **Issue:** If a `moment` pass runs first, then a `hook` pass runs, the hook line gets `role_hint: "hook"`.
  - If a `hook` pass runs first, then a `moment` pass runs, the moment line gets `role_hint: "hook"`.
  - The adapter (`best_unused_moments`) returns the *latest* line.
  - If the latest line is a `moment` but it carries `role_hint: "hook"` from an earlier pass, does the packager treat it as a hook?
  - The design doc says: *"A hook row is a moment line... with `role_hint: "hook"`... The adapter returns the latest line, which must never lose a flag."*
  - It does *not* say the latest line *must* be a hook if an earlier one was. It says it must carry the *flags*.
  - However, `role_hint` is a semantic tag. If the latest line is a "moment" (general statement) but tagged "hook", the packager might use it as an opener.
  - Is this desired? Ruling 80: *"The 12 h pool had no moment rated 4 as a HOOK... The miner finds good statements, not openers."*
  - If a video has a good statement (moment) and a good opener (hook) for the *same* span, and the hook pass runs last, the latest line is the hook.
  - If the moment pass runs last, the latest line is the moment, but it carries `role_hint: "hook"`.
  - This seems **incorrect**. A moment should not be tagged as a hook just because an earlier pass thought it was a hook. The `role_hint` should reflect the *current* line's nature, or the *strongest* nature.
  - Actually, `carry_forward` is meant to preserve *exclusions* (flags). `role_hint` is not an exclusion.
  - **Bug:** `role_hint` should probably be `l["role_hint"] = l.get("role_hint") or e.get("role_hint")`? No, that's what it does.
  - If `l` is a moment (`role_hint` is `None` or missing), and `e` is a hook (`role_hint` is `"hook"`), `l` becomes `"hook"`.
  - This means a general moment can be mislabeled as a hook.
  - **Impact:** The packager might use a non-opener as an opener.
  - **Fix:** `role_hint` should only be carried forward if the *new* line is also a hook, or if we want to mark the span as "hook-capable". But the prompt says "A hook row is a moment line... with role_hint 'hook'". It implies the *row* is a hook.
  - If the latest row is a moment, it should be a moment.
  - **Verdict:** **VIOLATION** of Ruling 80 intent. A moment pass overwriting a hook pass should not inherit the `role_hint`.

**5. `hook_video` Cost Calculation**
In `service.py` (line 347):
```python
cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role='hook'",
                   (vid,))[0]["usd"] or 0.0
```
This sums *all* hook calls for the video, including previous retries.
`hook_cost_usd` in the queue is updated to this total.
This is correct for "total cost spent on this video's hooks".

### SECTION 2: LAW COMPLIANCE

- **L-x (No Single Model):** COMPLIANT. `providers.json` defines `hook` role with `heimdall_qwen27b` and `local_gemma`.
- **L-l (Strict Validation):** COMPLIANT. `validator` in `mine.py` is parameterized and strict.
- **L-u (Hard Exclusions):** PARTIAL. `carry_forward` unions risks, which is good. But the `role_hint` bug (Section 1.4) might allow a non-hook to be treated as a hook, potentially bypassing the "hook" specific eligibility checks if the packager relies on `role_hint` to apply hook-specific rules (e.g., 4-14s duration check is done in `mine_video`, but eligibility is re-judged by packager). If the packager sees `role_hint: "hook"` on a moment line, it might apply hook eligibility. If the moment line was already filtered by `mine_video` for duration, it's safe. But if the packager re-judges, it might be fine.
- **L-m (Fail Closed):** COMPLIANT. `carry_forward` treats `None` flags as "unsafe" (e.g., `about_bitcoin` must be `True` in both).
- **Ruling 77 (Purge):** COMPLIANT. `purge.py` changes look solid. `unit_videos` now fails closed on unreadable records. `open_paths` reports unreadable PIDs.
- **Ruling 80 (Hook Pass):** VIOLATION. The `role_hint` carry-forward logic is flawed (see Section 1.4).

### SECTION 3: SECURITY

- **SQL Injection:** No raw user input in SQL. `queue.py` uses parameterized queries.
- **Secrets:** `providers.py` uses `Keyring` to read env vars. `redact` is applied to errors.
- **Path Traversal:** `purge.py` checks `FORBIDDEN` paths and `realpath`. `config.py` checks store root.
- **ReDoS:** `BTC_SCREEN` regex is simple. `NOTICE_RE` is simple.

### SECTION 4: FRONTEND QUALITY

N/A (Backend service).

### SECTION 5: BACKEND QUALITY

- **DB Operations:** `queue.py` uses `sqlite3` with `WAL` and `synchronous=FULL`. `RLock` for thread safety.
- **External API:** `providers.py` has robust retry, backoff, circuit breaker.
- **Memory:** `ledger.read` streams lines. `offset_before` bisects.
- **Logging:** `service.py` logs state changes.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

1.  **Hook/Moment Role Confusion:** The `role_hint` carry-forward is a semantic error. A "moment" should not become a "hook" just because an earlier pass labeled it so. The packager needs to know *what* the latest line is. If the latest line is a moment, it should be treated as a moment. If the latest line is a hook, it should be treated as a hook. The current logic forces the latest line to be a hook if *any* earlier line was a hook. This is wrong.
2.  **Hook Duration Re-check:** The `mine_video` function filters hooks by duration (4-14s). But the packager re-judges eligibility. Does the packager re-check duration? The design doc says: *"eligibility is recorded as judged at mining time (role clip) and is re-judged by the packager."* If the packager re-judges with `role="hook"`, it might apply different rules. But the duration filter is a *mining* constraint. If the packager doesn't enforce 4-14s, a hook line that was 15s (and thus dropped by `mine_video`) would never be in the ledger. So it's safe.
3.  **Concurrency of Hook and Mine:** They share the `executor`. This is fine.

### SECTION 7: SCORES

- Backend logic: 90/100 (The `role_hint` bug is a significant logic error)
- Frontend/UI: N/A
- Error handling: 95/100 (Excellent fail-closed design)
- Security: 95/100
- Performance: 90/100
- Law compliance: 85/100 (Ruling 80 violation)
- World-class gap: 85/100
- OVERALL: 90/100

### SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Fix `role_hint` carry-forward logic | `pipeline/ingest/ledger.py:202` | A moment line should not inherit `role_hint: "hook"` from an earlier hook line. This mislabels the content for the packager.
P1 HIGH | Verify packager behavior with `role_hint` | `docs/audits/parallel/pp-selectid_STATE.md` | Ensure the packager uses `role_hint` to apply the correct eligibility rules. If it does, the P0 fix is critical.
P2 MEDIUM | Add test for `role_hint` carry-forward | `tests/ingest/test_ledger_coverage.py` | Test that a moment line does not become a hook line.

### SECTION 9: THE ONE THING

Stop carrying forward `role_hint` in `ledger.carry_forward`; the latest line's role must reflect its own mining pass, not the history of the span.

### SECTION 10: FINAL VERDICT

This code is production-ready in terms of robustness, security, and fail-closed logic. However, the `role_hint` carry-forward logic in `ledger.py` is a semantic bug that will mislabel moments as hooks, violating the intent of Ruling 80. Fix this before merging.