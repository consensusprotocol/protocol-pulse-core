# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 237.0 s, $0.004, finish stop)

# PROTOCOL PULSE: CODE AUDIT — pp-ingest r125 (cfd3bb9a)

## SECTION 1: CORRECTNESS

**Claimed flow:** `pipeline_sweep` now selects `is_live` rows and makes them due ONCE when `acquired_at > state_at`. `fetch.process` then probes; if still `is_live` it re-queues with `LIVE_REPROBE_S` and rewrites `state_at`, preventing loop.

**Walkthrough:**

1. **Selection — CORRECT:** `fetch.py:242-245` expands WHERE to `(state=? AND live_status IN (?,?))` with `("post_live","is_live")`. This correctly adds `is_live` without touching other waits. The `UPDATE` at `fetch.py:258` uses `state IN (?,?,?,?)` covering all 4 states — consistent.

2. **Gating logic — CORRECT but fragile:** `fetch.py:253-256`:
   ```python
   if r["state"] == Q.LIVE and r["live_status"] == "is_live":
       got, probed = _zoned(found[1].get("acquired_at")), _zoned(r["state_at"])
       if got is None or probed is None or got <= probed: continue
   ```
   - `found[1].get("acquired_at")` — assumes `pipeline_transcript()` returns `(path, meta_dict)`. Verified by test helper `pipeline_record` tamper pattern. If contract changes, silent `None` → fail-closed (correct per L-j).
   - `got <= probed` — strict `>` required. Equal timestamps do NOT trigger. Correct: prevents re-trigger on same record if clocks align.
   - Other waits (`PROBE_RETRY`, `CAPTIONS_PENDING`, `post_live`, `UNAVAILABLE`) fall through to `due.append` unconditionally — preserves r118/r120/r122 invariants.

3. **`_zoned` — CORRECT:** `fetch.py:232-239` handles `Z` → `+00:00`, rejects naive datetimes (`tzinfo is None → None`), rejects unparseable → `None`. Caller treats `None` as fail-closed (`continue`). Matches `service.transcript_lag` reading of `acquired_at`.

4. **No-loop guarantee — CORRECT given unchanged code:** Relies on `queue.py:166` `state_at=config.iso()` on every `set_state` and `queue.py:171-177` `claim()` also setting `state_at`. After `fetch.process` probes `is_live`, it calls `q.set_state(vid, Q.LIVE, next_at=now+1200)` which rewrites `state_at` to now. Next sweep: `got (old record) <= probed (new now)` → skip. Verified by `test_r125.py:33-42`.

5. **Never-taken guarantee — CORRECT:** `fetch.py` `process()` unchanged: `if live=="is_live" ...: q.set_state(LIVE)` — never calls `take_pipeline_transcript`. Sweep only sets `next_at=now_ts`; actual take happens in `process` after probe.

**Logic errors / edge cases:**

- **N+1 query — PRESENT but pre-existing and bounded:** `fetch.py:248-256` calls `pipeline_transcript()` (glob + file read) inside loop over `rows`. `rows` is bounded by `EXPIRY_H` window and `next_at > now_ts` — typically small (live rows only). Not a production breaker, but worth noting. No DB N+1 (single SELECT, single UPDATE).
- **Race condition — LOW RISK:** `pipeline_sweep` does SELECT then UPDATE without transaction isolation. If two workers sweep concurrently, both could set `next_at=now_ts` for same vid, causing double probe. Mitigated by `claim()` semantics in `process` (not in diff) — second worker's claim should fail. Need to verify `claim()` uses atomic UPDATE WHERE state check. **Request to see `queue.py:171-177 claim()` implementation to confirm.**
- **Empty DB / bad input — HANDLED:** `rows` empty → `due=[]` → no UPDATE. `found is None` → skip. `ValueError` on bad vid → skip. `_zoned(None)` → `None` → skip. All fail-closed.
- **API timeout — NOT IN SCOPE:** Sweep does no YouTube request (comment at `fetch.py:240` correct). Probe happens in `process` — timeout handling there unchanged.
- **Wrong variable — NONE FOUND.**
- **Silent failure — ONE CONCERN:** `fetch.py:250` `except ValueError: continue` silently skips malformed vids. Correct per spec ("never a path, never due") but no logging. If `transcript_store` starts throwing `ValueError` broadly, sweep silently does nothing with no observability. Pre-existing.

**Test manipulation in `test_r120.py:103-104` — CORRECT:** The tamper `lambda r: r.update(acquired_at="2026-01-01T00:00:00+00:00")` makes record older than probe, so r125 correctly leaves it. This preserves r120's invariant test while adding r125 coverage. Not a cheat — it's the exact edge case r125 defines.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest (~10min, ETag/backoff, ledger, Shorts/live handling, durable queue)** | **COMPLIANT** | Fix directly addresses 10-min ruling violation (462s → would have been 20min). `LIVE_REPROBE_S=1200` respected. `is_live` never taken, `post_live` taken — correct live handling. |
| **BUILD: captions into SAME store format via writer, staging copy** | **COMPLIANT** | No change to caption path. `take_pipeline_transcript` unchanged. |
| **BUILD: first-pass mining (bounded concurrency, 429/503 backoff, ≤20 in flight, $460 cap 90% tripwire NOTIFY not halt)** | **COMPLIANT** | No change to mining path. |
| **BUILD: append-only moment ledger + adapter** | **COMPLIANT** | No change. |
| **BUILD: daily coverage check** | **COMPLIANT** | No change. |
| **BUILD: blind A/B (generator/judge different models)** | **COMPLIANT** | No change. |
| **L-x NO SINGLE MODEL, ULTRON FIRST (provider interface ≥2 backends, local default, no GPU use here)** | **COMPLIANT** | `fetch.py` has no model calls, no GPU use. No vendor names. |
| **L-l strict schema, nothing repaired; failed call never default/pass** | **COMPLIANT** | `_zoned` returns `None` on failure, caller skips — fail-closed, no repair. |
| **L-j/L-m fail closed; nothing measured never pass** | **COMPLIANT** | Missing/zoneless time → `continue` (not due). `found is None` → skip. `ValueError` → skip. All fail-closed. |
| **L-h/L-k transcript as spoken, never rewritten** | **COMPLIANT** | No transcript rewrite. `take_pipeline_transcript` unchanged. |
| **L-e word timing at cut time** | **COMPLIANT** | No change to timing. |
| **L-u hard exclusions before ranking** | **COMPLIANT** | No change to ranking/exclusion. |
| **L-v moment never spans speaker change; re-uploads excluded; time-sensitive needs publish time** | **COMPLIANT** | No change. `COALESCE(published_ts, discovered_ts) >= ?` with `EXPIRY_H` preserved. |
| **Secrets: keys by name from env, never logged** | **COMPLIANT** | No secret handling in diff. |
| **SPEND FREEZE (no paid frontier vendors; Heimdall→local only; queue if both down; 90% NOTIFY not halt)** | **COMPLIANT** | No vendor calls in diff. No spend logic touched. |

**No violations found.** This is a narrow, well-scoped fix that touches only sweep timing.

---

## SECTION 3: SECURITY

- **SQL injection — PASS:** `fetch.py:242-245` uses parameterized `q.rows(..., (Q.PROBE_RETRY, ...))` and `fetch.py:258-259` uses `q.x(..., (now_ts, ...))` with `?` placeholders. `video_id IN (...)` clause builds `','.join('?' * len(due))` with placeholders, values passed separately. No string interpolation of user input. `Q.*` constants are internal enums, not user input.
- **Authentication bypass — N/A:** No routes in diff. Pipeline internal.
- **Rate limiting — PASS:** Sweep does zero YouTube requests (one glob + file read per row). Probe happens in `process` with existing backoff. No new external calls. No paid API exhaustion vector.
- **Secrets in code — PASS:** No keys, tokens, passwords in diff. No logging of secrets.
- **Unvalidated input → DB/filesystem/shell — PASS:** `video_id` from DB rows, not user input. `pipeline_transcript()` takes `video_id` validated by `transcript_store` (throws `ValueError` on bad id → caught). No shell execution. No filesystem write beyond queue UPDATE.

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend in diff.** This is `pipeline/ingest/fetch.py` + tests. No UI, no JS, no CSS.

Score: N/A (excluded from overall).

---

## SECTION 5: BACKEND QUALITY

- **DB operations try/except + rollback — PARTIAL:** `fetch.py:248-251` has `try/except ValueError` around `pipeline_transcript` but no explicit transaction/rollback. `q.rows` (SELECT) and `q.x` (UPDATE) appear to be auto-commit. If `q.x` UPDATE fails mid-way, no rollback needed (single statement). But if `pipeline_transcript` file read fails with `OSError`/`IOError` (not `ValueError`), it would crash the entire sweep — no catch. **Pre-existing, not introduced by r125.**
- **External API calls timeout+retry — PASS (N/A for sweep):** Sweep makes no external calls. `process` probe has existing retry via `LIVE_REPROBE_S`.
- **Cron/sweep failure handling — PASS:** Sweep is idempotent (sets `next_at=now_ts`, re-runnable). Failure doesn't crash service — caller handles. No state corruption on partial failure (UPDATE is atomic).
- **Memory leaks — PASS:** No large objects per-request. `rows` is bounded. `found` is small dict. No accumulation.
- **Logging — WEAK:** Zero log statements in `pipeline_sweep`. When `got is None` or `probed is None` or `got <= probed`, silent skip with no debug log. When sweep makes rows due, no info log of which vids or why. Production debugging of "why didn't my live video get picked up?" requires logs. Pre-existing weakness, not worsened.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

For a premium Bitcoin intelligence product, this fix is **excellent engineering** — the kind Bloomberg would do:

**Already excellent:**
- Root cause analysis with real production data (462s, 229 videos, 4 over 300s) — this is institutional-grade observability (r119's `transcript_lag_s` measure).
- Mutation testing (M69-M73, 5/5 killed) — exceeds industry standard.
- Fail-closed design on time parsing — correct for financial data pipeline.

**Material gaps (not padding):**

1. **No metric for the fix itself:** r119 measured `transcript_lag_s` which found this bug. r125 should add a counter `sweep_live_wakeup_total` or log when `is_live` row is made due via new path. Without it, you can't verify the fix works in production or detect regression. Bloomberg would have a dashboard.

2. **Wall-clock dependency is fragile:** `state_at=config.iso()` uses wall time (`datetime.now(timezone.utc)`), while `acquired_at` comes from pipeline's wall time. If clocks skew between pipeline host and ingest host (different machines/containers), `got <= probed` could misfire. World-class would use monotonic or DB `now` for comparison, or add clock-skew tolerance (e.g., `got <= probed - 5s`). Current code has zero tolerance.

3. **No alert on repeated live probes:** If a stream stays `is_live` for hours (e.g., 24/7 live channel misclassified), this code will probe it every time a new pipeline record lands (could be frequent if pipeline re-transcribes). No circuit breaker. Should cap probes per video per hour.

**If already excellent, say so:** The core logic, test coverage, and fail-closed design are excellent. The fix is minimal, correct, and well-tested. These gaps are operational polish, not correctness issues.

---

## SECTION 7: SCORES

- **Backend logic:** 92/100 — Correct, minimal, well-reasoned. -8 for N+1 file reads in loop and wall-clock fragility.
- **Frontend/UI:** N/A — No frontend in scope.
- **Error handling:** 85/100 — Fail-closed throughout. -15 for no catch on `OSError` from file reads and zero logging on skip paths.
- **Security:** 98/100 — Parameterized queries, no secrets, no injection. -2 for no input length validation on `video_id` (relies on downstream).
- **Performance:** 88/100 — Single SELECT + single UPDATE, no YouTube calls in sweep. -12 for N+1 `pipeline_transcript` file I/O in loop (could batch).
- **Law compliance:** 100/100 — Full compliance, no violations.
- **World-class gap:** 82/100 — Strong engineering with mutation testing and production metrics. Gaps are observability and clock-skew resilience.
- **OVERALL:** 91/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | None | — | No P0 issues. Code is safe to ship.

P1 HIGH     | Add OSError catch in sweep loop | `fetch.py:248` | `pipeline_transcript()` file read can throw `OSError`/`FileNotFoundError` on corrupt staging copy, crashing entire sweep and blocking all videos — not just the bad one. Add `except (ValueError, OSError): continue` with error log.

P1 HIGH     | Add observability for r125 path | `fetch.py:253-256` | No log/metric when `is_live` row is made due via new path. Production verification impossible. Add `logger.info("sweep: live_wakeup vid=%s acquired=%s probed=%s", vid, got, probed)` before `due.append`.

P2 MEDIUM   | Add clock-skew tolerance | `fetch.py:255` | Wall clocks on different hosts can skew seconds. `got <= probed` with zero tolerance could miss valid wakeups or cause flapping. Consider `got <= probed + timedelta(seconds=2)` or use DB time for both.

P2 MEDIUM   | Batch pipeline_transcript checks | `fetch.py:248` | N+1 file reads (glob+open per row). If many live rows accumulate, sweep does sequential I/O. Could pre-list pipeline store directory once and check membership via set lookup. Low urgency given small row count.

P2 MEDIUM   | Verify claim() atomicity | `queue.py:171` | Sweep race: two workers could both set `next_at=now` for same vid. Need to confirm `claim()` does `UPDATE ... WHERE state=? AND video_id=?` atomically. Not in diff — request to verify.

P3 LOW      | Log ValueError skips | `fetch.py:250` | Silent `continue` on `ValueError` hides data quality issues. Add `logger.warning` with vid.

P3 LOW      | Consider capping live probes per vid | `fetch.py:253` | 24/7 live streams could cause probe storm if pipeline frequently re-transcribes. Add per-vid probe rate limit.

---

## SECTION 9: THE ONE THING

Add logging to every skip and wakeup path in `pipeline_sweep` — without it, this correct code is undebuggable in production when the next live-stream timing anomaly hits.

---

## SECTION 10: FINAL VERDICT

This code is **ready for production**. It correctly fixes the 20-minute live-stream delay with a minimal, fail-closed, well-tested change that preserves all existing invariants. Ship it, but add logging on the new code path before the next incident makes you wish you had.

**Required before ship:** Nothing blocking. Recommended: add `OSError` catch and wakeup logging (P1s above) in a follow-up commit within 24h.