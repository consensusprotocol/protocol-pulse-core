# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 491.4 s, $0.031, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (Ruling 98 / Paid Route)

**Branch:** `pp-ingest` @ `56f6eac7` + diff | **Reviewer:** Independent Model | **Date:** 2026-11-14

---

### SECTION 1: CORRECTNESS

#### 1.1 Main Flow Walkthrough

**Watch → Fetch → Mine → Ledger → Coverage** is correctly wired. The diff under review (Ruling 98) adds a conditional paid-route branch to the mine loop. Walkthrough of the new path:

1. `Service.__init__` loads `paid_route` from `providers.json:96-99`, creates `RoleCaps` with `queue.role_spend_since` as loader (`service.py:98-100`). Correct.
2. `DownSignal.__init__` captures `paid`, `roles`, computes `plan_b_tail`/`miner_plan_b` strings (`downsignal.py:104-113`). Correct.
3. Every 5s `DownSignal.tick()` → `_route_tick()` evaluates open/close/cap (`downsignal.py:193-236`). Every 5s `Service.mine_once()` reads `hsig.paid_open` to choose branch (`service.py:534-535`).
4. If `paid_open`: `_paid_due()` filters `MINE_DUE` to `published_ts >= now - 21600`, sorts conversations-first (`service.py:554-573`), dispatches `mine_video(v, role="mine_paid")`.
5. `mine_video` → `mine.mine_video(..., role="mine_paid")` → `build_line(..., route="mine_paid")` stamps `miner_route` (`mine.py:440`).
6. `_settle(..., route="mine_paid")` writes `mine_route` to DB (`service.py:317`).
7. When signal returns to `up`, `_queue_rechecks()` re-queues paid videos with `recheck_ts` (`service.py:575-585`), re-mined on `mine` role, `carry_forward` unions flags.

**Verdict: Flow is logically sound and matches spec A27-A32.**

#### 1.2 Logic Errors

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| C1 | `downsignal.py:210` | `self.paid_open = False` when `v is None` (signal unreadable). Correct per A27 ("A signal not read opens nothing"). But `mine_once:534` checks `paid_open` — if signal was open and then becomes unreadable, `paid_open` flips to `False` mid-outage, mine loop falls through to `_queue_rechecks` path which also returns early (`signal_back()` is False). Videos queue and wait — correct fail-closed. **No bug.** | — |
| C2 | `downsignal.py:216-222` | `failing_since_utc` parsed with `fromisoformat(str(fs).replace("Z","+00:00"))`. If builder writes `failing_since_utc` as `None` or missing, `fs_t = None`, route never opens. Correct — no answer clock means no 20-min measurement. | — |
| C3 | `providers.py:859-875` | `reserve`/`release` in `Router.run` uses `finally` — even on `AllBackendsFailed` or crash, reservation released. Correct. | — |
| C4 | `service.py:560` | `_paid_due` calls `q.due(MINE_DUE, 200)` then filters to `new_within_s`. If 200 oldest `MINE_DUE` rows are all old (>6h), new uploads beyond offset 200 are invisible. **Real bug under load.** During extended Heimdall outage, old `MINE_WAIT`/`MINED_PARTIAL` videos accumulate; `due()` orders by `published_ts DESC` so newest first — actually mitigated because `due()` returns newest first. New uploads *will* be in first 200. **Not a bug** given ordering. | — |
| C5 | `service.py:561-562` | `_conv` cache grows unbounded until 5000 then `clear()`. Between 0-5000, every new video triggers `canonical_transcript` read + `episode_measure`. Under sustained outage with many new uploads, this is bounded. Acceptable. | Low |
| C6 | `downsignal.py:230-236` | Cap check: `spent + reserve > cap` triggers `paid_cap_day` write + STATE head. But `spent` is `router.caps.today()` which is `RoleCaps.spent` — updated only via `caps.add()` on each call's cost. If Gemini cost is price-table estimate (upper bound), cap may trip early. Spec says this is intentional (A30: "an upper bound"). Correct. | — |

#### 1.3 Race Conditions

| # | Location | Analysis |
|---|----------|----------|
| R1 | `downsignal.py:105` `paid_open` | Written by signal thread (`_route_tick`), read by mine thread (`mine_once:535`). Plain bool assignment — atomic in CPython (GIL). No torn read. Correct. |
| R2 | `providers.py:684-725` `RoleCaps` | All methods hold `self.lock`. `reserve`+`release` called from `Router.run` which may be called concurrently from 3 mine threads. Lock protects `spent`/`reserved`/`day`. Correct. |
| R3 | `service.py:534-548` `mine_once` | `paid_open` read once per invocation, then `_paid_due` or `q.due` + `claim` loop. If signal flips mid-loop, current batch completes on old route, next `mine_once` (5s later) picks new route. No atomicity violation — videos are claimed atomically via `q.claim()`. Correct. |
| R4 | `queue.py:179-193` `recheck_due` | No `claim` — `_queue_rechecks` does `set_state(TRANSCRIBED)` directly. If two service instances ran (violates single-service lock), double-queue possible. But `service.lock` prevents second instance. Single-process: `_queue_rechecks` runs only from mine thread, no concurrent caller. Safe. |

#### 1.4 N+1 Queries

| # | Location | Issue |
|---|----------|-------|
| N1 | `service.py:564-571` `_paid_due.conv()` | For each of up to 200 videos, does `config.ts().canonical_transcript(vid)` — a filesystem read + JSON parse. Called inside sort key, so up to 200 reads per `mine_once` tick (every 5s). Cached in `_conv` dict after first call, so amortized. But first tick after outage: 200 file reads in sort comparator — could be ~200ms. Acceptable for 5s interval. **P2: could pre-filter without reading transcripts.** |
| N2 | `service.py:582` `_queue_rechecks` | `recheck_due` is one query, then `set_state` per video (1 write each, up to 20). Fine. |

#### 1.5 Edge Cases

| # | Scenario | Handling |
|---|----------|----------|
| E1 | Empty DB, no videos | `q.due()` returns `[]`, `mine_once` returns 0, `release()` after idle. Correct. |
| E2 | `published_ts` is NULL | `_paid_due:560` → `(v.get("published_ts") or 0) >= now - 21600` → `0 >= ...` → False → excluded. Old videos with no publish time correctly wait for Heimdall. Correct per spec. |
| E3 | `failing_since_utc` is stale (builder bug) | `now - fs_t` could be huge, route opens immediately on next tick even if Heimdall just recovered but builder hasn't cleared `failing_since_utc`. However builder clears it on any answer (`note(True,...)`). If builder is correct, not an issue. If builder has bug, paid route opens spuriously — but cap limits damage to $2. |
| E4 | ET day rollover mid-reservation | `RoleCaps._roll()` checks date on every `reserve`/`add`/`today`. If day rolls between `reserve` and `add`, `add` will roll to new day and add to new day's `spent`, while `reserved` was on old day. `reserved` dict is keyed by role, not day — stale reservation leaks. **Minor bug.** Impact: one $0.25 reservation leaked across midnight ET, cap slightly under-counted for one tick. Self-heals on next `_roll`. |
| E5 | `paid_route` missing from config | `downsignal.py:104` → `self.paid = None`, `_route_tick` returns immediately. `service.py:534` → `pr = None`, `paid = False`. No paid path. Correct — backward compatible. |

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, dedup, Shorts/live, durable queue, captions via store writer, staging copy, bounded concurrency, spend cap, ledger, coverage, A/B) | **COMPLIANT** | All BUILD requirements are in prior commits; this diff does not weaken any. `watch.py`, `fetch.py`, `queue.py` unchanged. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:114` `mine_paid` has 2 back-ends (xai, gemini). `providers.py:143-150` validates `paid_route` needs capped role. `Router.effective()` still enforces ≥2 back-ends per role via `load_config:159`. No vendor/model outside `providers.json` (test `test_no_vendor_or_model_name_outside_the_provider_config` passes). |
| **L-l Strict schema, nothing repaired** | **COMPLIANT** | `mine.py:validator()` unchanged. `providers.py:959-965` rejects invalid, re-asks with reason, never repairs. |
| **L-j / L-m Fail closed** | **COMPLIANT** | `downsignal.py:210-212` signal unreadable → `paid_open=False`, no spend. `providers.py:859-862` cap reached → skip, don't exceed. `purge.py` unchanged. |
| **L-h / L-k Read as spoken, never rewrite** | **COMPLIANT** | `contract.py:spoken` unchanged. `ledger.py:carry_forward` only unions flags, never rewrites text. |
| **L-e Word timing at cut time** | **COMPLIANT** | `mine.py:412-413` `duration_s` null for segment timing, `duration_estimate_s` set. Unchanged. |
| **L-u Hard exclusions** | **COMPLIANT** | `ledger.py:347-348` hard flags still exclude. `mine.py:carry_forward` unions flags — paid route's flags + Heimdall re-mine flags both stand. No flag cleared. |
| **L-v Speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:turn_change_inside` unchanged. `fetch.py:find_duplicate` unchanged. `config.expires_at` unchanged. |
| **Secrets** | **COMPLIANT** | `providers.py:180-221` `Keyring` reads by name from env file. `providers.py:930-931` redacts before recording. No hardcoded keys. |
| **SPEND FREEZE** | **COMPLIANT** | `providers.py:907-908` frozen vendor blocked unless `freeze_lifted` role. `providers.json:115` `mine_paid.freeze_lifted` names ruling 98 with cap. Only `mine_paid` lifts freeze. `test_only_the_freeze_lifted_role_calls_a_frozen_vendor` verifies. |
| **L-q Moments first** | **COMPLIANT** | Mining still happens before selection. Paid route mines same windows, same prompt. |
| **L-r GPU0 no GPU** | **COMPLIANT** | No GPU code in diff. `OllamaLocalBackend` unchanged, still requires `gpu0.held()`. |

**Overall Law Compliance: COMPLIANT — no violations.**

---

### SECTION 3: SECURITY

| Check | Verdict | Detail |
|-------|---------|--------|
| **SQL Injection** | **PASS** | All queries use `?` placeholders (`queue.py:182-193`, `service.py:272`). No string interpolation of user input into SQL. `VIDEO_FIELDS` allowlist on `set_state` (`queue.py:160-162`). |
| **Authentication bypass** | **PASS** | No HTTP routes — this is a backend ingest service. No auth surface. |
| **Rate limiting gaps** | **PASS** | `Throttle` per back-end (`providers.py:654-682`), `Health` circuit breaker, `RoleCaps` daily cap, `SpendBook` daily budget. Paid route adds $2 cap with $0.25 reservation. No single user can exhaust — service is single-tenant. |
| **Secrets in code** | **PASS** | No API keys, tokens, passwords in diff or in `providers.json` (only `key_env` names). `Keyring.redact()` on all error paths. |
| **Unvalidated input → DB/filesystem/shell** | **PASS** | `video_id` validated by `VIDEO_ID` regex (`ledger.py:27`, `purge.py:99`). `yt-dlp` args are fixed strings + video_id in URL (`fetch.py:92-93`). No shell injection — `subprocess` via `transcript_store._ytdlp` with list args. `purge.py:76-77` validates target paths against `FORBIDDEN`. |
| **Filesystem traversal** | **PASS** | `purge.py:344` checks `rp.startswith(unit_real)` and `not rp.startswith(protect)`. `tools/ingest_watch.py:118-119` validates video_id regex before path join. |
| **Cap bypass via direct DB write** | **PASS** | Cap is enforced in `Router.run` before `_try`, not just in DB. Even if queue is manipulated, `RoleCaps.reserve()` is the gate. |

**Security Score: No issues found.**

---

### SECTION 4: FRONTEND QUALITY

**N/A — This is a backend ingest service with no frontend.** No UI, no HTML, no JS, no CSS. The only user-facing surfaces are:

- `tools/ingest_watch.py` CLI — correctly formatted, help text present
- `docs/audits/parallel/pp-ingest_STATE.md` STATE file — line 1 protocol followed
- `data/editorial/ingest/live.json` — consumed by monitoring

No frontend to evaluate. Scores below reflect N/A.

---

### SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|------|---------|--------|
| **DB try/except + rollback** | **GOOD** | `queue.py:81` uses `isolation_level=None` (autocommit) + `WAL` + `synchronous=FULL`. Each `x()` is one statement, auto-committed. No multi-statement transactions that need rollback. `service.py:230-238` catches fetch crashes and resets state to `PROBE_RETRY`. `mine_video:277-287` catches all exceptions, resets to `MINE_WAIT`. |
| **External API: timeout+retry+degradation** | **EXCELLENT** | `providers.py:229` per-backend `timeout_s`, `Throttle` with `Retry-After`, `Health` breaker (5 consecutive / 50% window / slow median), `transport_retries` (3 default, 0 for probe). Every call has bounded retry, never infinite. Degradation: outage → `MINE_WAIT` retry in 10min, never dropped. |
| **Cron failure handling** | **EXCELLENT** | No cron — long-running tmux with 7 loops, each wrapped in `try/except` (`service.py:693-698`), logs `loop_error` event, continues. `purge` spec refusal → logs, deletes nothing. Signal unreadable → `paid_open=False`, no crash. |
| **Memory leaks** | **GOOD** | `ThreadPoolExecutor` with bounded workers (3 video, 4 hook, 20 global). `_conv` cache capped at 5000 then cleared. `attempts` list in `ab.py` grows per run but A/B is one-shot. No per-request large objects without cleanup. `RoleCaps.reserved` could leak one entry across ET midnight (E4) — negligible. |
| **Logging** | **EXCELLENT** | Every state change → `events` row. Every attempt → `calls` + `replies_log`. Every route switch → STATE line 1 + evidence file + event + log line. `log()` writes to stdout + `service.log` file. Cap reached, outage, purge blocked all produce STATE notices. |

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this already does at world-class level:**
- Durable queue with WAL, crash recovery, exactly-once ledger append with `carry_forward`, spend tracking with vendor-reported costs, circuit breakers, and a shared health signal — this is production-grade distributed systems engineering for a single-binary service. The Bloomberg Terminal comparison is apt: this is the data ingestion layer, and it is excellent.

**Genuinely missing (material impact only):**

1. **No alerting beyond STATE file.** If Heimdall is down 20min and paid route opens, the only notification is STATE line 1. No PagerDuty/webhook/Telegram alert. For a premium product where "never miss the day's most relevant content" is the promise, silent failover to a $2-capped paid route that may itself fail needs an out-of-band alert. **Impact: High.**

2. **No observability on paid route cost attribution.** `live.json` has `usd_24h_by_vendor` but no `usd_24h_by_route` or `paid_route_spent_today`. Operator cannot distinguish Heimdall spend from paid-route spend without querying `calls` table. `downsignal.snapshot()` now has `paid_route.spent_today_usd` but `stats.live()` does not surface it. **Impact: Medium.**

3. **Gemini cost is price-table estimate, not vendor-reported.** `providers.json:74-76` notes Gemini reports no cost. Cap enforcement uses estimate which may be 2-7x over actual (as seen with xAI A/B judge 7x over-estimate noted in `providers.json:67`). Cap trips early, leaving budget unused. Needs calibration or Gemini cost API integration. **Impact: Medium.**

4. **No backpressure on paid route queue depth.** If 50 videos publish in 6h during outage, all 50 are `MINE_DUE`, `_paid_due` takes 3 per tick. At ~20s per video (2 windows × 10s each), 50 videos = ~6 minutes. Acceptable. But if outage lasts hours and hundreds accumulate, no prioritization beyond conversations-first. Already handles this via `newest first` within groups. **Not a gap — already good.**

5. **Re-mine is fire-and-forget with no verification.** `_queue_rechecks` sets `TRANSCRIBED` and relies on normal mine loop. If Heimdall is still flaky when re-mine runs, re-mine may itself outage and go to `MINE_WAIT` — then `recheck_ts` is already set, so it won't be re-queued again. One shot. For $2/day of paid labels, losing the Heimdall verification on flaky recovery is a data quality risk. **Impact: Low-Medium.**

---

### SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Correct flow, proper concurrency, fail-closed everywhere. -8 for E4 (ET midnight reservation leak) and N1 (transcript reads in sort). |
| **Frontend/UI** | **N/A** | No frontend. CLI and STATE file are well-formed. |
| **Error handling** | **95/100** | Every external call has timeout+retry+breaker. Every loop has try/except. Every failure has a retry path. Nothing dropped. -5 for re-mine one-shot (gap #5). |
| **Security** | **98/100** | No injection, no secret leaks, no auth bypass, path traversal protected. -2 for `os.path.realpath` TOCTOU on purge (pre-existing, not this diff). |
| **Performance** | **88/100** | Bounded concurrency (20 global, 3 video, 4 hook), WAL, bisection reads. -12 for N1 (200 transcript reads in sort comparator on every tick during outage). |
| **Law compliance** | **100/100** | All laws compliant. Freeze lift is narrowly scoped with cap. No violations. |
| **World-class gap** | **82/100** | Ingest pipeline is excellent. Gaps are observability/alerting, not core logic. Needs out-of-band alerting and paid-route cost visibility. |
| **OVERALL** | **91/100** | Production-ready. One P2 fix recommended before merge, no blockers. |

---

### SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No critical issues. Code is safe to ship.

P1 HIGH     | Add paid_route spend to live.json | stats.py:84-87 | Operator cannot distinguish Heimdall vs paid-route spend without DB query; during outage the $2 cap is invisible in monitoring
P1 HIGH     | Add out-of-band alert on paid route open | downsignal.py:218-222 | STATE line 1 is only visible via file polling; 20-min Heimdall outage + paid failover should notify Telegram/PagerDuty

P2 MEDIUM   | Fix ET midnight reservation leak | providers.py:695-710 | RoleCaps.reserved keyed by role not day; reservation leaks across ET midnight, cap under-counted by $0.25 for one tick
P2 MEDIUM   | Avoid transcript reads in _paid_due sort | service.py:564-571 | 200 file reads in sort comparator every 5s during outage; cache helps after first tick but first tick is slow; consider storing tpm in queue at fetch time
P2 MEDIUM   | Re-mine retry on outage | service.py:575-585 | If Heimdall re-mine outages, recheck_ts already set so never retried; paid labels stay unverified; add recheck_ts reset on MINE_WAIT with mine_route=mine_paid
P2 MEDIUM   | Validate failing_since_utc staleness | downsignal.py:216-222 | If builder's failing_since_utc is stale/wrong, paid route opens spuriously; add sanity check: fs_t must be within last 24h

P3 LOW      | SWITCH_PATTERN regex could match false positives | spend.py:23-24 | "MINER ON THE PAID ROUTE" pattern is broad; unlikely collision but could match future unrelated STATE lines
P3 LOW      | _conv cache clear is abrupt | service.py:561-562 | Clearing entire 5000-entry cache at once causes next tick to re-read 200 transcripts; consider LRU eviction
P3 LOW      | Add integration test for cap + ET rollover | tests/ingest/test_paid_route.py | No test covers midnight ET day boundary for RoleCaps
```

---

### SECTION 9: THE ONE THING

**Surface the paid route's spend and state in `live.json` and add an out-of-band alert when it opens — because a $2/day silent failover that nobody monitors is a $2/day silent failure mode.**

---

### SECTION 10: FINAL VERDICT

**This code is ready for production.** The paid route implementation is correct, narrowly scoped, fail-closed, and well-tested (6 new tests, 277 total). No P0 issues. Ship it after addressing the two P1 observability gaps (paid spend in `live.json` + alert on route open), which are operational — not correctness — concerns and can follow in a fast-follow commit.
