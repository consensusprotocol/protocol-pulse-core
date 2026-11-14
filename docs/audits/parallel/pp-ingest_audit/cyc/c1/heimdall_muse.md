# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 396.5 s, $0.032, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest `cycles.py` diff (47c7939b vs 81f46b3c)

> Scope: Only the 3-file diff is under review (`pipeline/ingest/cycles.py` new, `pipeline/ingest/spend.py` + `pipeline/ingest/service.py` delta). All other files are context. Citations are `file:line` in the diff unless noted.

---

### SECTION 1: CORRECTNESS

**Main flow:** `Service.health_once()` (every 60s) → `cycles.compose(q, now)` → `spend.write_cycles_notice(line)` → `_rewrite_top()` under `state_doc.lock`.

**1.1 Clock leak — FIXED correctly.**
`compose()` never uses `now_ts` in output text except as window bound `t0`. Display time is `newest` (max of `watch_cycle.ts` or `video.mined_ts/hook_ts`) at `cycles.py:89,100`. When `out` empty but `quiet` present, `when = cycles[0][0]` (newest cycle) — not `now`. This satisfies Q1: no per-minute rewrite. Verified by `spend.py:60` `if new != text` guard.

**1.2 Wrong count / time — TWO bugs:**

**Bug A — `n` vs `vids` mismatch (cycles.py:73-84):** `n = d.get("new")` is trusted from `watch_cycle` event, but `vids` is derived by time-window heuristic `start <= e.ts <= ts+2` (cycles.py:78-79). If events are delayed, clock skew, or `seconds` missing (defaults 0), `len(vids) != n`. Output says `"3 new: (1) ...; (2) ..."` with only 2 entries — count is wrong. No validation `len(vids) == n`. The fallback `"its discoveries not found"` (cycles.py:84) masks the bug but leaves `n` wrong.

**Bug B — `start` heuristic is fragile (cycles.py:78):** `start = ts - seconds - 2`. `seconds` is wall time of `watch_once()` (includes thread pool). If `watch_cycle` event `ts` is taken at cycle end but `discovered` events are written during `poll_channel` (before cycle end), the window is correct. But if `seconds` is 0/None (event write failure), `start = ts -2` — misses discoveries from a 30s cycle. Conversely, overlapping cycles (if `watch_once` ever runs concurrently — it doesn't today, but `health_once` is single-threaded) could double-count.

**1.3 N+1 query (cycles.py:81):** `q.video(e.video_id)` inside `for e in vids` loop. Each is `SELECT * FROM videos WHERE video_id=?`. For 3h window with ~10 cycles × ~5 videos = 50 queries per minute. Not catastrophic (SQLite, local), but violates the spec's own concern. Should be single `WHERE video_id IN (...)`.

**1.4 Empty DB / edge cases:**
- `cycles.py:86-87`: `if not cycles: return None` — correct, no line when watcher stopped. But `quiet` is never computed in this branch, so 09:02 note is suppressed when watcher is down. Spec says "say so when a cycle finds nothing Bitcoin in 3 hours" — if no cycles ran, arguably should not say it. Current behavior is defensible, but undocumented.
- `cycles.py:89`: `if not out and not quiet: return None` — when cycles exist but all had `n==0` and `quiet==""` (some mined video had Bitcoin), returns None and removes line. Correct per spec: "after each cycle that finds something".
- `cycles.py:44-45`: `v["hook_ts"]` may be 0/None; `max(t for t in (mined, hook_ts) if t)` correctly skips falsy. But `v["mined_ts"]` could be None for `MINED_PARTIAL` with no `mined_ts` yet — then `newest` stays `ts`, not None. OK.
- `cycles.py:38`: `v["reason"][:120]` — if `reason` is None, `(v["reason"] or "")` handles it. OK.

**1.5 Race condition — NONE in this diff.** `compose()` is read-only; `write_cycles_notice()` holds `state_doc.lock` via `_rewrite_top`. `health_once` is single-threaded (one `health` loop thread). No concurrent writer for cycles line.

**1.6 Silent failure — PARTIAL:** `service.py:768-773` catches `Exception` and logs once per `why`. Good. But `cycles.compose` can raise `sqlite3.OperationalError` (DB locked) — caught and logged, health loop continues. Correct.

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, ~10min, ETag/backoff, ledger, coverage, A/B) | **COMPLIANT** | Diff does not touch ingest logic; `cycles.py` is additive reporting. No regression. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | No vendor/model names in diff. `cycles.py` has zero provider references. |
| **L-l strict schema, never repaired** | **COMPLIANT** | Not applicable to this diff (no model reply handling). |
| **L-j / L-m fail closed, nothing measured is never a pass** | **COMPLIANT** | `cycles.py:92-98` `_quiet()` correctly counts `queued` (WAITING) apart: `"none of the {len(known)} mined with Bitcoin term"` — does not claim "nothing Bitcoin" while uploads are unmined. Q3 answered: NO, it does not lie. |
| **L-h / L-k read as spoken** | **COMPLIANT** | Not touched. |
| **L-e word timing** | **COMPLIANT** | Not touched. |
| **L-u hard exclusions** | **COMPLIANT** | Not touched. |
| **L-v speaker/re-uploads** | **COMPLIANT** | Not touched. |
| **L-q moments first** | **COMPLIANT** | Not touched. |
| **L-r GPU0** | **COMPLIANT** | No GPU use. |
| **L-w / L-u exclusions** | **COMPLIANT** | Not touched. |
| **Spend freeze (05:30 ET Nov 12)** | **COMPLIANT** | No provider calls in diff. |
| **Secrets** | **COMPLIANT** | No secrets in diff. |

**Overall Law compliance for this diff: COMPLIANT.** No violations.

---

### SECTION 3: SECURITY

- **SQL injection:** `cycles.py:68,70,92,96` — all queries use `?` placeholders. `q.video()` uses placeholder. **No injection.**
- **Auth bypass:** No routes. `service.lock` flock still enforced. **N/A.**
- **Rate limiting:** Not applicable to this diff (read-only reporting).
- **Secrets in code:** None. `cycles.py` has no keys. **Clean.**
- **Unvalidated input → DB/filesystem/shell:** `cycles.py:68` `window_h` is caller-controlled (`health_once` passes `now` only, default 3.0). No user input reaches DB. `spend.py:67` `doc` defaults to `config.STATE_DOC`, `notify_path` to `p["notify"]` — both internal. **No vector.**
- **Filesystem:** `spend.py:70` `os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)` — `lock_path` is `notify_path + "/state_doc.lock"` where `notify_path` is `p["notify"]` (store-controlled). No traversal. **Safe.**
- **One concern:** `cycles.py:38` `v["reason"][:120]` is rendered into STATE.md without sanitization. `reason` comes from `yt-dlp` stderr or internal strings. If `reason` contained `"\n"` it could inject a fake NOTICE line. However `write_cycles_notice` validates `"\n" not in line` (spend.py:67) — so a newline in reason would cause `ValueError`, caught by `service.py:768`, logged, line not written. **Fail-closed, correct.** But the error would suppress the cycles line entirely until reason changes — minor DoS of the notice.

---

### SECTION 4: FRONTEND QUALITY

**N/A — No frontend in this diff.** This is a backend service writing a markdown file. No UI, no JS, no viewport.

If evaluating STATE.md as "UI": The line is one physical line (enforced `spend.py:67`), newest-first, human-readable. Format is consistent with existing NOTICE lines. No rendering bug.

---

### SECTION 5: BACKEND QUALITY

- **DB operations — try/except with rollback:** `cycles.py` is read-only, no writes, no transaction needed. `spend.py:36-64` `_rewrite_top` does `os.replace(tmp, doc)` atomically under flock. No DB write in this diff. **OK.**
- **External API calls — timeout+retry:** None in this diff. **N/A.**
- **Cron/health loop — failure without crash:** `service.py:768-773` `except Exception` with `self.cycles_error` dedup ensures one log per cause, loop continues. `health_once` caller `_loop` (service.py:855-864) also has outer `except Exception` + `q.event("loop_error")`. **Double-guarded, excellent.**
- **Memory leaks:** `compose()` allocates `cycles`, `disc`, `names`, `out` — all bounded by 3h window (max ~18 cycles × ~30 videos). Freed per call. No leak.
- **Logging:** `service.py:772` `self.log(f"the cycles line could not be written: {why}")` — includes exception type + 200 chars. `cycles_error` dedup prevents log spam. **Good.**
- **One gap:** `cycles.py:68` `SELECT ... FROM events WHERE kind='watch_cycle' AND ts >= ? ORDER BY ts DESC` — no index on `(kind, ts)`. `events` has `events_ts` index on `ts` only. For large `events` table (months of data), this is a full scan filtered by `kind`. Should add `CREATE INDEX events_kind_ts ON events(kind, ts)`. Existing tests won't catch this at scale.

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this diff does well:** The "clock never leaks" invariant (`newest` not `now`) is subtle and correctly implemented. The `_quiet` logic correctly separates "not yet mined" from "mined with no Bitcoin" — a nuance many would get wrong. The `NOTICE_RE` integration keeps switch line first (spend.py:58).

**What's missing / would be world-class:**

1. **No observability of the cycles line itself.** `live.json` does not include `cycles_line` or `cycles_line_age_s`. If the line goes stale (DB locked, compose crash), the only signal is a log line. Bloomberg would expose it as a metric. **Add `cycles` to `stats.live()` output.**

2. **The `n` vs `vids` mismatch (Bug A) would be caught by a single assertion.** A world-class pipeline would `assert len(vids) == n` or log a warning when they diverge, rather than silently showing wrong count.

3. **No integration test that the line actually appears in STATE.md after `health_once`.** `test_cycles.py` tests `compose()` in isolation; `test_service.py::test_the_health_loop_writes_the_cycles_line` exists but only checks it doesn't crash. No test asserts the file content matches `compose()` output.

4. **The 3h window is hardcoded in two places** (`cycles.py:WINDOW_H` and `spend.py` NOTICE_RE is generic). If orchestrator changes window to 6h, two files must change. Minor.

**If already excellent:** Error handling (deduped logging, fail-closed on unreadable STATE, lock discipline) is excellent. Law compliance is perfect for this diff.

---

### SECTION 7: SCORES (0-100 each)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **78/100** | Core invariant (clock isolation) correct; N+1 and `n` vs `vids` mismatch are real bugs; heuristic window is fragile. |
| **Frontend/UI** | **N/A** | No frontend in diff. If scoring STATE.md as UI: 85/100 — clean, one-line, human-readable. |
| **Error handling** | **92/100** | Double-guarded (inner + outer), deduped logging, fail-closed on unreadable file, never crashes health loop. |
| **Security** | **95/100** | No injection, no secrets, newline injection fail-closed. Minor: reason field could suppress line. |
| **Performance** | **75/100** | N+1 queries + missing composite index on `events(kind, ts)` will hurt at scale; otherwise trivial cost. |
| **Law compliance** | **100/100** | Zero violations in this diff. |
| **World-class gap** | **70/100** | Solid but missing observability, assertion on count mismatch, and file-content integration test. |
| **OVERALL** | **82/100** | Production-ready with two P1 fixes. No P0. |

---

### SECTION 8: PRIORITY ACTION PLAN

```
P1 HIGH     | Fix n vs vids count mismatch: validate len(vids)==n or derive n from len(vids) | cycles.py:73-84 | Wrong count shown in STATE line 1 (orchestrator's primary view); erodes trust in coverage reporting
P1 HIGH     | Fix N+1 query: batch q.video() calls into single SELECT WHERE video_id IN (...) | cycles.py:81 | 50 queries/min today, 500/min at 10x scale; will cause DB lock contention with fetch/mine writers
P2 MEDIUM   | Add composite index CREATE INDEX events_kind_ts ON events(kind, ts) | queue.py:SCHEMA | Full table scan on events every 60s; degrades linearly with retention
P2 MEDIUM   | Add cycles line to live.json (cycles_line, cycles_line_age_s) for observability | stats.py:live() + service.py:_cycles_notice | Stale line is invisible except in logs; on-call cannot alert on it
P2 MEDIUM   | Harden start heuristic: use event IDs or explicit cycle_id FK instead of ts±2s window | cycles.py:78 | Clock skew or slow poll_channel can misattribute videos to wrong cycle
P3 LOW      | Sanitize reason newlines before rendering (replace \n with space) instead of failing entire line | cycles.py:38 | One yt-dlp error with newline suppresses cycles line until video state changes
P3 LOW      | Extract WINDOW_H to single source of truth (config.py) | cycles.py:9 + service.py | Two places to change if orchestrator adjusts window
P3 LOW      | Add file-content integration test: health_once writes expected compose() output to temp STATE.md | tests/ingest/test_service.py | Current test only checks no-crash, not correctness of file content
```

---

### SECTION 9: THE ONE THING

**Derive the video count from the actual `vids` list instead of trusting the `watch_cycle` event's `n` field — a single source of truth eliminates the only way the orchestrator's line can show a wrong number.**

---

### SECTION 10: FINAL VERDICT

**This code is ready for production after two P1 fixes (count mismatch + N+1 query).** The core design is sound — the clock isolation invariant is correctly implemented, the NOTICE_RE integration preserves the switch-line-first guarantee, and error handling is double-guarded. The bugs are quality issues, not safety issues: no data loss, no security hole, no law violation. Ship the P1s, add the index, and it's solid.
