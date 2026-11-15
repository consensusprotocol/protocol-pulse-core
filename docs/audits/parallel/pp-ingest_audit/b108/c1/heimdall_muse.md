# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 315.2 s, $0.010, finish stop)

# PROTOCOL PULSE: CODE AUDIT — pp-ingest DIFF (ruling 107(2))

**Branch:** `pp-ingest` @ `9b8a5136` | **Scope:** `pipeline/ingest/batch.*`, `spend.py`, `providers.py`, `downsignal.py`, `service.py`, `cycles.py`, `tests/ingest/xllm_audit.py` | **Cap:** $0.30 (<60 lines) / $1.00

---

### SECTION 1: CORRECTNESS

#### 1.1 Main Flow: `batch.notice()` → `spend.write_batch_notice()` → STATE line 1

**Claim:** Every hour, `service.health_once()` writes `BATCH <n> ingest spend: $x` FIRST on STATE line 1, to the latest whole hour.

**Walkthrough:**

1. `service.py:754` `health_once()` calls `_batch_notice(now)` every 60s.
2. `batch.py:155` `notice()` computes `mark = min(t1, t0 + floor((now-t0)/3600)*3600)` — correct hourly bucketing.
3. `batch.py:157-158` `watcher_spend(q, t0, mark)` + `audit_spend(path, t0, mark)` — both use `ts < mark` / `ts < until`, so hour is closed at its end.
4. `spend.py:96-108` `write_batch_notice()` validates `BATCH_RE` + no `|`/newline, then `_rewrite_top()` with `flock` + `os.replace`.

**Verdict: CORRECT** for the happy path. Three verified defects below.

#### 1.2 Defect C1 — `abandoned_usd()` N+1 Query Storm (HIGH)

`batch.py:82-88` `abandoned_usd()` executes **3 SQL queries per unique (model,role)** inside `watcher_spend()` loop:

```python
# batch.py:82-88
for sql, args in (("model=? AND role=?", ...), ("role=?", ...), ("model=?", ...)):
    avg = q.rows(f"SELECT AVG(prompt_tokens) ... WHERE {sql} AND prompt_tokens > 0 AND ts < ?", ...)
```

`watcher_spend()` at `batch.py:108-119` calls `abandoned_usd()` once per abandoned row, memoized by `(model,role)`. If there are 5 distinct abandoned (model,role) pairs, that's 15 queries. With 20, it's 60. Each query scans `calls` table.

**Impact:** `notice()` is called every 60s on health thread. `share_left()` is called on **every paid call reservation** (`providers.py:718` via `RoleCaps.reserve_why`). Under load with many abandoned calls, this blocks the health thread and the provider reservation path.

**Not a correctness bug, but a performance correctness issue** — the health loop at `service.py:740` runs every 60s; if `notice()` takes >60s due to N+1, health checks queue.

#### 1.3 Defect C2 — `batch.py:195` `now + 1.0` Off-by-One in `share_left()` (LOW)

```python
# batch.py:195
w = watcher_spend(q, b["t0"], now + 1.0, cfg)
```

`watcher_spend` uses `ts < t1` (exclusive upper bound). Adding 1.0 second means a call stamped at exactly `now` (or `now+0.5`) is counted. But `queue.py:239` stamps `ts = service clock at insert`. If clock advances between `share_left()` call and actual `q.call()` insert, the reservation check and the booking are inconsistent. This is intentional (count to NOW inclusive) but the `+1.0` is a magic number that should be documented as `now is inclusive`.

**Verdict: Not a bug, but fragile.**

#### 1.4 Defect C3 — `spend.py:77-84` `_segments` / `_place` Interaction with Empty `head[0]` (MEDIUM)

```python
# spend.py:77-84
head = [lines.pop(0)] if lines and (NOTICE_RE.match(lines[0]) or LINE1_RE.match(lines[0])) else []
while lines and NOTICE_RE.match(lines[0]):
    head.append(lines.pop(0))
head = _segments(head[0]) + head[1:] if head else []
```

If `STATE.md` starts with `BATCH 3 ingest spend: $0.1 (old) | ALARM ...` (one physical line), `_segments` splits it correctly. But if file starts with empty line or non-notice line, `head` is `[]`, and `_segments` is never called — correct.

**Edge case verified:** `test_batch.py:228-232` tests hand-edited `ALARM | BATCH` order — `_segments` handles any order via `while rest and (BATCH_RE.match(rest) or rest.startswith(ALARM_PREFIX))`. **CORRECT.**

#### 1.5 Defect C4 — `xllm_audit.py:170-175` `estimate()` Over-Counts When `only` Filters (LOW)

```python
# xllm_audit.py:170-175 (estimate)
run, _ = chosen(only)
for rid in run:
    tokens, out = len(prompt_for(rid)) / 3.0, max_out(REVIEWERS[rid])
```

`prompt_for(rid)` is called per-reviewer. For cycle 2, `prompt_for` calls `tool.build_cycle2_prompt()` which reads `c1` files. If `only` filters to 1 reviewer, estimate is for 1 reviewer — correct. But `cap_check` at `xllm_audit.py:195` checks `spent + estimate > cap` where `spent` is total across all cycles. If cycle 1 spent $0.25 and cycle 2 with `--only heimdall_qwen` estimates $0.10, total $0.35 > $0.30 cap → refused. This is **correct per spec** (both cycles together capped).

#### 1.6 Race Condition Analysis (Question 1)

**Q: Can any sequence of writers lose/duplicate a notice or leave line 1 malformed?**

**Answer: NO, verified.**

- All writers (`write_batch_notice`, `write_alarm_notice`, `write_cycles_notice`, `write_switch_head`, etc.) go through `_rewrite_top()` at `spend.py:52-91`.
- `_rewrite_top` holds `fcntl.flock(LOCK_EX)` on `state_doc.lock` for the entire read-modify-write.
- `os.replace(tmp, doc)` is atomic on POSIX.
- `_segments` at `spend.py:38-46` splits only on `SEP = " | "` and only for `BATCH_RE`/`ALARM_PREFIX` prefixes. Both writers at `spend.py:99` and `spend.py:115` refuse `|` and `\n` — so split is exact.
- `_place` at `spend.py:49-51` is stable sort — within same `_place` value, original order preserved.
- `write_switch_head` at `spend.py:272-285` appends `" |"` to head and prepends to switch line — newest first, correct.

**One subtlety:** `spend.py:68` `lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock")` — if `notify_path` is `None`, falls back to `doc + ".lock"`. Two different lock files could be used if some callers pass `notify_path` and others don't. **Verified:** `service.py:786` passes `notify_path=self.p["notify"]`, `downsignal.py` also passes it. Consistent. **No race.**

#### 1.7 Paid Call Past Share (Question 2)

**Q: Can a paid call start past the batch's share?**

**Answer: NO, verified with one caveat.**

- `providers.py:710-730` `reserve_why()` checks `self.share()` under `self.lock`, sums `self.reserved.values()` (all in-flight held amounts), and refuses if `held + amount > left`.
- `providers.py:897` reservation released in `finally` after call — correct.
- `batch.py:188-196` `share_left()` returns `0.0` outside batch or on unreadable file — fail-closed.
- `providers.py:718-722` `share()` exception → `return "could not be read: no paid call starts"` — fail-closed.
- `providers.py:724` `float(left)` — if `left` is `NaN`, `held + amount <= NaN` is `False` (NaN never passes) — correct per `batch.py:196` comment.
- `batch.py:52-55` validates `share >= 0` and `math.isfinite(share)` — NaN/Infinity rejected at load.

**Caveat:** `batch.py:195` `now + 1.0` means `share_left()` counts calls up to 1 second in the future. If two `reserve_why()` calls happen concurrently, both see same `left`, both reserve, total held could exceed `left` by up to one call's cost. But `reserve_why` holds `self.lock` for the entire check+reserve — **serialized, no concurrent over-reservation.** Verified at `providers.py:711` `with self.lock`.

#### 1.8 Hourly Figure Finality (Question 3)

**Q: Is hourly figure final once hour is out? Is anything booked as $0 that is not known to be $0?**

**Answer: YES final, YES $0 is correct.**

- `batch.py:154` `mark = min(t1, t0 + floor((now-t0)/3600)*3600)` — mark only advances on hour boundary.
- `batch.py:82` `abandoned_usd(..., until)` queries `WHERE ts < until` where `until = mark` — only calls before hour end.
- `batch.py:108` `watcher_spend(..., t1=mark)` queries `WHERE ts >= t0 AND ts < t1` — same.
- `batch.py:130` `audit_spend(..., t1=mark)` checks `t0 <= ts < t1` — same.
- Late records (inserted after hour closed but with `ts < mark`) would change figure — but `queue.py:239` stamps `ts = clock()` at insert time, so late insert gets current `ts`, not retroactive. **Figure is final.**
- `batch.py:114-118` `if usd is None: out["unpriced_n"] += 1; usd = 0.0` — unpriced abandoned calls counted as $0 in `sum(w["by"].values())` but flagged as `NOT PRICED` in basis. `batch.py:168-169` says `f"{w['unpriced_n']} abandoned call(s) NOT PRICED"`. **Not silently $0 — explicitly flagged.** Correct per L-j/L-m (fail closed, nothing measured is never a pass — here, unpriced is said, not hidden).

#### 1.9 Audit Driver Cap/Cost (Question 4)

**Q: Can a cycle spend past cap, or can review cost be lost/double-counted?**

**Answer: NO past cap, NO lost/double-counted.**

- `xllm_audit.py:195-197` `cap_check()` called BEFORE `fire()` — `if spent + estimate > cap: raise SystemExit("REFUSED")`. No calls made.
- `xllm_audit.py:170-183` `estimate()` uses worst-case: `1.5 * (prompt_tokens * in_price + max_out * out_price)` — over-estimates, never under-estimates. Verified: `test_audit_driver.py:128-133` asserts `est >= floor` and `est >= 0.009 + 0.001`.
- `xllm_audit.py:200-230` `record()` writes `COST.json` atomically via `os.replace(tmp, path)` — no torn file.
- `xllm_audit.py:220-224` Re-runs: `while key in cyc["reviews"]: key = f"{rid} (run {k})"` — each run kept separately, costs summed. `test_audit_driver.py:108-112` verifies 3rd run adds correctly.
- `xllm_audit.py:140-165` `book()` handles all cases: reported cost, abandoned at own rate, cut-off after CUT_S, quick failure as $0 with basis "not booked".
- `xllm_audit.py:232-235` Ledger: one JSON line per review to `audit_spend.jsonl`, append-only.

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest** | **COMPLIANT** | Unchanged code, not in diff. Diff only adds spend tracking. |
| **L-x: NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.py:687-730` `RoleCaps` is provider-agnostic. `xllm_audit.py:14-16` `REVIEWERS` has 2 Heimdall families, no vendor name outside config. `providers.json:66` `cost_reported` is generic. |
| **L-l: strict schema, nothing repaired** | **COMPLIANT** | `xllm_audit.py:148` `b.complete(prompt, None, max_out(cfg))` — schema=None for audit (freeform review), correct. No repair logic. |
| **L-j/L-m: fail closed** | **COMPLIANT** | `batch.py:188-196` unreadable batch → `0.0` left, no paid calls. `providers.py:718-722` unreadable share → no paid calls. `batch.py:114-118` unpriced → flagged, not hidden. |
| **L-h/L-k: transcript canonical form** | **COMPLIANT** | Not in diff scope. |
| **L-e: word timing** | **COMPLIANT** | Not in diff scope. |
| **L-u: hard exclusions** | **COMPLIANT** | Not in diff scope. |
| **L-v: moment never spans speaker change** | **COMPLIANT** | Not in diff scope. |
| **Secrets: keys from env, never logged** | **COMPLIANT** | `xllm_audit.py:14` `ENV = "/home/ultron/protocol_pulse/.env"` + `providers.Keyring(ENV)` — reads by name. No `print(key)` or `log(key)`. `providers.py` key handling unchanged. |
| **SPEND FREEZE** | **COMPLIANT** | `xllm_audit.py:22-24` `frozen()` + `chosen()` skips frozen vendors. `test_audit_driver.py:52-54` verifies `grok` skipped with "spend freeze". `providers.json` frontier vendors remain `enabled:true` but never called via audit path. |
| **Ruling 108: $8 cap, $1 share** | **COMPLIANT** | `batch.json:6-7` `share_usd: 1.00, cap_usd: 8.00`. `batch.py:195` `share_left()` enforces share. `downsignal.py:299-304` announces share cap. |
| **Ruling 107(2): Heimdall-first, 2 families, $0.30/$1.00** | **COMPLIANT** | `xllm_audit.py:72-74` `DEFAULT = (qwen, glm)`, `THIRD = muse`, `SMALL_CAP=0.30`. `xllm_audit.py:195` `cap_check` before any call. `xllm_audit.py:200-230` `record()` books every review. |
| **Ruling 87: switch on STATE line 1** | **COMPLIANT** | `spend.py:272-285` `write_switch_head` still writes to line 1 via `_rewrite_top`. `spend.py:49-51` `_place` keeps switches on line 1 (place=2). |
| **Ruling 106(d): alarm on line 1** | **COMPLIANT** | `spend.py:106-120` `write_alarm_notice` writes to line 1, place=1 (after batch, before switches). |
| **Ruling 98: paid route capped $2/ET day** | **COMPLIANT** | `providers.py:687-730` daily cap still enforced. `batch.py:195` share is additional constraint, not replacement. `downsignal.py:286-304` both caps announced. |
| **Ruling 106(b): stricter reading** | **COMPLIANT** | `batch.py:78-80` abandoned = `timeout OR (no http_status AND latency >= CUT_S)` — stricter (more calls booked). `batch.py:188-196` unreadable → 0 left — stricter. |

**Overall Law Compliance: COMPLIANT** — no violations found.

---

### SECTION 3: SECURITY

| Check | Verdict | Detail |
|-------|---------|--------|
| **SQL Injection** | **PASS** | All queries use parameterized `q.rows("... WHERE model=? AND ts < ?", (model, until))` at `batch.py:82-88,108,130`. One f-string at `batch.py:86` interpolates `sql` variable — but `sql` is hardcoded from 3-element tuple `("model=? AND role=?", ...)`, never user input. **Safe.** |
| **Auth Bypass** | **N/A** | No HTTP routes in diff. Internal pipeline only. |
| **Rate Limiting** | **PASS** | `providers.py:710-730` `RoleCaps` enforces daily cap + share cap with reservation. `xllm_audit.py:195` cap check before any call. No bypass. |
| **Secrets in Code** | **PASS** | `xllm_audit.py:14` `ENV = "/home/ultron/protocol_pulse/.env"` — path only, not key material. `providers.Keyring` reads by env var name. No hardcoded keys. `batch.json` contains no secrets. |
| **Unvalidated Input → DB/FS/Shell** | **PASS with note** | `batch.py:42-55` `load()` validates `name` against `NAME_RE`, `share_usd` finite, `t1 > t0`. `batch.json` is trusted (repo file, not user input). `xllm_audit.py:42-55` `subprocess.check_output(["git", "diff", ...])` — `base` is git rev, not shell-interpolated (list form). `os.path.join(REPO, ...)` — no traversal. |
| **Filesystem** | **PASS** | `spend.py:68` `os.path.join(os.path.dirname(notify_path), "state_doc.lock")` — `notify_path` from `config.paths()`, trusted. `xllm_audit.py:232` `config.paths()["audit_spend"]` — trusted. No user-controlled paths. |

**Security Score: No issues found.**

---

### SECTION 4: FRONTEND QUALITY

**N/A — This diff has no frontend.** It's a backend pipeline (`pipeline/ingest/`) + CLI audit driver (`tests/ingest/xllm_audit.py`). No HTML, CSS, JS, or UI components changed.

The only "UI" is `STATE.md` line 1 formatting — verified correct at `test_batch.py:228-250`.

---

### SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|------|---------|--------|
| **DB try/except + rollback** | **PASS** | `batch.py:188-196` `share_left()` catches all exceptions, returns fail-closed. `batch.py:42-55` `load()` raises on bad file, caller handles. `queue.py` (unchanged) uses sqlite with proper transactions. |
| **External API: timeout+retry+degradation** | **PASS** | `providers.py:860-900` `Router.run()` has retry loop with `attempts`, timeout via `timeout_s`, fallback across backends. `xllm_audit.py:148-165` `call()` catches `BackendError`, records cost, continues. |
| **Cron/health loop failure handling** | **PASS** | `service.py:782-795` `_batch_notice()` catches all exceptions, logs once (`self.batch_error` dedup), keeps last figure, never stops health loop. Same pattern as `_cycles_notice` at `service.py:770-783`. |
| **Memory leaks** | **PASS** | No large objects per-request. `batch.py:30-35` `_cache` is bounded (one entry, keyed by mtime+size). `xllm_audit.py` threads are joined. No accumulation. |
| **Logging** | **PASS** | `service.py:791-793` logs `f"ruling 108: the batch line could not be written: {type(e).__name__}: {str(e)[:200]}"` — includes cause. `batch.py:168-172` basis includes abandoned/unpriced/unreadable counts. `downsignal.py:299-304` announces both caps. |
| **Concurrency** | **PASS** | `batch.py:30` `_lock` protects `_cache`. `providers.py:711` `self.lock` protects `reserved`+`share()` check atomically. `spend.py:52-91` `flock` protects STATE file. All lock ordering documented and followed. |

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a **spend-tracking and audit infrastructure** change, not a user-facing feature. Judged as infrastructure:

**What's excellent (explicitly):**
- The fail-closed design is genuinely world-class. Every money path defaults to $0/spend-nothing on error. Bloomberg would approve.
- The `N+1` → `memo` pattern in `watcher_spend()` shows awareness of query cost.
- Atomic file writes (`os.replace`) and `flock` discipline throughout — production-grade.
- Test coverage is exceptional: `test_batch.py` (262 lines), `test_audit_driver.py` (149 lines), `test_paid_route.py` share tests — all with real assertions, not just smoke tests.

**What's missing (material impact only):**

1. **No alerting on share exhaustion.** `downsignal.py:299-304` writes to STATE line 1, but if nobody reads STATE for hours, paid mining silently queues. A Bloomberg-grade system would have a webhook/PagerDuty alert when share hits 90% (like the Heimdall 90% tripwire). Currently only `STATE.md` — which requires polling.

2. **No spend dashboard.** The data exists (`calls` table + `audit_spend.jsonl` + `COST.json`) but there's no query to answer "how much did we spend today across all roles?" without reading STATE line 1. A `batch.summary()` CLI or endpoint would help the builder reconcile the $8 cap.

3. **Abandoned call rate estimation is fragile.** `batch.py:82-88` uses `AVG(prompt_tokens)` as proxy for abandoned call's prompt size. If the abandoned call had a much larger prompt (e.g., long video transcript) than average, cost is under-estimated. World-class would store `prompt_tokens` at call start (before failure) rather than inferring after.

---

### SECTION 7: SCORES

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **Backend logic** | **88/100** | Correct, well-tested, minor N+1 and magic number issues |
| **Frontend/UI** | **N/A** | No frontend in scope |
| **Error handling** | **92/100** | Fail-closed everywhere, deduped logging, atomic writes |
| **Security** | **95/100** | Parameterized queries, no secrets, no injection vectors |
| **Performance** | **78/100** | N+1 in `abandoned_usd()` called on hot path (`share_left` per paid call) |
| **Law compliance** | **98/100** | All laws verified compliant, stricter readings applied |
| **World-class gap** | **82/100** | Solid infra, missing alerting + dashboard for $8 cap |
| **OVERALL** | **88/100** | Production-ready infra with minor performance caveat |

---

### SECTION 8: PRIORITY ACTION PLAN

```
P1 HIGH     | Batch N+1 query on hot path | batch.py:82-88,108-119 | share_left() called per paid-call reservation; each abandoned (model,role) triggers 3 SQL queries. Under load with many abandoned calls, blocks provider reservation. Pre-compute AVG(prompt_tokens) once or cache per (model,role,until).
P1 HIGH     | No alerting on share exhaustion | downsignal.py:299-304 | Share cap only written to STATE.md line 1. If builder doesn't poll STATE, paid mining silently queues for hours with no notification. Add 90% tripwire notification (like Heimdall tripwire).
P2 MEDIUM   | Magic number now+1.0 undocumented | batch.py:195 | Inclusive upper bound via +1.0 second is fragile. If clock granularity changes or calls batch-inserted, could double-count or miss. Use explicit inclusive flag or document invariant.
P2 MEDIUM   | Abandoned prompt size is average, not actual | batch.py:82-88 | AVG(prompt_tokens) under-estimates cost for large-prompt abandoned calls (long transcripts). Store prompt_tokens at call dispatch time, not inferred post-failure.
P2 MEDIUM   | No spend reconciliation CLI | batch.py:155-180 | Builder must read STATE.md line 1 to check $8 cap. No way to query "total spend today" programmatically. Add batch.summary() or CLI for cap monitoring.
P3 LOW      | _cache key uses mtime_ns+size, not content hash | batch.py:42-48 | Two different batch.json contents with same mtime+size (e.g., share 1.00→2.00, same length) could return stale cache. Use content hash or always re-read on share_left hot path.
P3 LOW      | xllm_audit estimate() calls prompt_for() per reviewer | xllm_audit.py:170-183 | For cycle 2, prompt_for() rebuilds cycle2 prompt (reads files) per reviewer. Minor inefficiency; cache prompt_for result.
P3 LOW      | No test for concurrent reserve_why() over-reservation | providers.py:710-730 | Lock serializes correctly, but no test proves two threads can't both reserve past share. Add concurrency test like test_batch.py:260 does for single-thread.
```

---

### SECTION 9: THE ONE THING

**Fix the N+1 query in `abandoned_usd()` — it's called on every paid-call reservation and will be the first thing to degrade under production load with abandoned calls.**

---

### SECTION 10: FINAL VERDICT

**This code is ready for production.** All four review questions pass verification, all laws are compliant, fail-closed behavior is correct, and test coverage is thorough. The one thing to fix before scaling is the `abandoned_usd()` N+1 query pattern on the `share_left()` hot path — it's correct but will become a bottleneck as abandoned call volume grows. Ship it, then optimize.
