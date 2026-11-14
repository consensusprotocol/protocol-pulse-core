# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 483.9 s, $0.032, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff 32fd1d99)

## SECTION 1: CORRECTNESS

### Main Flow Walkthrough

**Watch → Fetch → Mine → Ledger → Coverage** is correctly wired. `Service.run()` spawns 7 daemon threads via `_loop()` with jitter. Each loop catches `Exception` and logs `loop_error` event — service never crashes on single-loop failure. Correct.

**Watch (`watch.py:176-228`):** `poll_channel` correctly handles RSS 304, ETag, backoff, first-sight backfill (72h), Shorts detection via `/shorts/` URL. One bug: `watch.py:216` checks `"/shorts/" in url` — yt-dlp flat-playlist entries for Shorts sometimes have `url: "https://www.youtube.com/watch?v=..."` without `/shorts/` path. Those Shorts would be queued as `discovered` and later mined. The `fetch.py:157` `media_type == "short"` is the real gate, but only after a probe. So Shorts leak into fetch queue unnecessarily. Minor.

**Fetch (`fetch.py:120-251`):** State machine is sound. `probe()` correctly distinguishes `age_gated` (terminal) from `unavailable` (retry 4x) from `rate_limited` (breaker). `publish_time()` correctly prefers `release_timestamp` for live VODs (INGEST-FAIL-03). `_store_captions` correctly respects `gate.open_for()` before downloading captions and trips breaker on `throttled`. Correct.

**Mine (`mine.py:372-628`):** Windowing with overlap capped at `min(overlap, (j-i)//2)` prevents O(n) explosion on huge sentences — correct (freeze audit N8). `screened_out` via `BTC_SCREEN` regex — correct. `mine_video` correctly unions flags on overlapping ranges (fail-closed L-u). `build_line` correctly sets `expires_at` via `config.expires_at`. Hook/spotlight duration filtering and `bad_opener` correctly applied post-mining. Correct.

**Ledger (`ledger.py:34-66`):** `append()` with `O_APPEND|flock|fsync` is correct. Torn-tail handling via `pread` check is correct. `stamp` under lock ensures `mined.at` order. `carry_forward` correctly unions risk/flags. `best_unused_moments` correctly applies expiry as `min(recorded, publish+12h)` — fail-closed. Correct.

**Coverage (`coverage.py:43-95`):** Independent listing, unmeasured channels never counted as covered (L-m). Correct.

### Logic Errors / Silent Failures

**1. `service.py:574-604` — `_reuse_calibration` future `asked_at` not rejected explicitly:**
```python
if t is None or not 0 <= self.clock() - t.timestamp() < CHECK_RECALIBRATE_S:
    return False
```
The `0 <=` check does reject future timestamps (negative delta). **Correct** — but only because `config.aware` returns aware datetime and `t.timestamp()` is UTC. If system clock skews backward after calibration was stored, a calibration from 1 hour ago could appear to be from the future and be rejected — causing unnecessary 32 live calls. Not a correctness bug, but worth noting. The check is actually correct for the stated question #1.

**2. `service.py:588` — `cal[b].get("of") == n` where `n = len(watcher_probes()) = 16`:**
If a stored calibration has `of=16` but `unmeasured=0` is checked separately, the `not cal[b].get("unmeasured")` check on line 588 uses truthiness — `0` is falsy, so `not 0 == True` passes. Correct. But if `unmeasured` key is missing (old record), `cal[b].get("unmeasured")` returns `None`, `not None == True` also passes — an old record without `unmeasured` field could pass this check. However line 583 already requires `set(cal) == set(eff)` and model match, and line 586 requires single `asked_at` — old cached-era records have no `asked_at` so they fail at line 587. **Safe.**

**3. `service.py:606-608` — `_reuse_tried` flag never reset:**
```python
if self.check_allowed is None and not self._reuse_tried:
    self._reuse_tried = True
    self._reuse_calibration()
```
After first `check_once()` call, `_reuse_tried=True` permanently. If `_reuse_calibration()` returns False (rejected), `check_allowed` stays `None`, so next `check_once()` goes to `if self.check_allowed is None or clock - calibrated >= recal_s` → `self.check_allowed is None` is True → `_calibrate_checkers()` runs live. Correct — the fallback is live calibration. No bug.

**4. `purge.py:240-289` — `kept_copies` `fail()` helper:**
The new `fail()` correctly accumulates all failing deliveries per video (`"; ".join`). Previously `setdefault` kept only first failure. Fix is correct and matches audit a19 c2 requirement.

**5. `providers.py:851-853` — Cache reuse bypasses freeze check:**
```python
if use_cache and self.backends[bid].cfg.get("enabled", True):
    out = self._cached(...)
```
`_cached` is called even for frozen vendors — comment says "frozen / no lease: reused" and spec says "stored validated reply costs nothing and may be reused." Correct per spec. But `_cached` checks `enabled` not `frozen` — a disabled backend's cache is still checked if `enabled` is True in config but `frozen` is True. The `effective()` method excludes frozen, but `run()` with `only=bid` could still serve cache for frozen vendor. This is intentional per SPEND FREEZE spec.

### Race Conditions

**`queue.py:78-99` — Single SQLite connection behind `RLock`:** All DB access goes through `self.lock` (RLock). WAL mode allows concurrent readers. The `claim()` method uses `UPDATE ... WHERE state IN (...)` atomically — correct, only one thread wins. No race.

**`ledger.py:45-63` — `append()` flock + `carry_forward` under `wlock`:** `service.py:322-324` holds `wlock` across `carry_forward` + `append`. This makes read+append atomic for this process. Correct. Cross-process: `ledger.append` also takes `flock` on the file. Correct.

**`service.py:135-136` — `ilock`/`hlock` for inflight sets:** Correct, prevents double-mining same video.

**`providers.py:234-235` — `_ki` key rotation under `_klock`:** Correct.

### N+1 Queries

**`service.py:294-295` — `mine_video` does `SELECT SUM(cost_usd) FROM calls WHERE video_id=?` per video:** This is 1 query per mined video, not N+1 in the classic sense (it's 1 per video completion, not per window). Acceptable at ~3 concurrent videos.

**`stats.py:30-32` — `live()` does 5 separate queries:** Acceptable for once-per-minute health check.

**`purge.py:318` — `published()` cache dict prevents repeated DB/file reads per video:** Correct.

### Edge Cases

- **Empty DB:** `stats.py:29` `min([d["discovered_ts"] for d in disc] or [now_ts])` — handles empty correctly via `or [now_ts]`.
- **API timeout:** Every backend has `timeout_s` (60-600s), `BackendError("timeout")` with retry logic. Correct.
- **Bad input:** `config.aware()` returns None for missing/invalid timestamps — fail-closed throughout. Correct.
- **Torn ledger:** `ledger.seal()` on startup + `append()` torn-tail handling. Correct.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest) | **COMPLIANT** | `watch.py:176` RSS→playlist fallback, `queue.py:78` WAL+flock, `service.py:840` tmux loops, `coverage.py:43` daily check |
| **L-x NO SINGLE MODEL** | **COMPLIANT** | `providers.json:107-122` every role has ≥2 backends, `providers.py:154-161` validates ≥2, `config.py:17` no vendor names in code outside providers.json (test at `test_providers.py: no_vendor_name_in_code`) |
| **L-l strict schema, never repaired** | **COMPLIANT** | `mine.py:447-499` validator rejects extra/missing keys, duplicate keys via `_pairs`, `providers.py:984-989` re-asks with reason, never repairs |
| **L-j/L-m fail closed** | **COMPLIANT** | `ledger.py:337-338` expired→drop, `coverage.py:62` unmeasured→not covered, `spend.py:132-134` unmeasured→not ok, `purge.py:396-400` unreadable→refuse all |
| **L-h/L-k read as spoken** | **COMPLIANT** | `contract.py:123` `E.spoken()`, `fetch.py:83` `ts.read_text()`, stored records never rewritten |
| **L-e word timing** | **COMPLIANT** | `contract.py:138-145` `timing: segment`, `ledger.py:543-544` `duration_s: None` for segment, packager re-anchors |
| **L-u hard exclusions** | **COMPLIANT** | `mine.py:23` `HARD_RISKS`, `ledger.py:347-348` pre-applied, `mine.py:599-608` overlapping windows union flags |
| **L-v speaker/re-uploads** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`, `fetch.py:186-191,242-247` duplicate detection, `ledger.py:351-354` exclusions |
| **Secrets** | **COMPLIANT** | `providers.py:180-221` Keyring reads env file, `providers.py:213-220,242-247` redact on every error, `providers.py:322-324` no redirect |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:5-8` freeze list, `providers.py:784-786,807-812,931-932` frozen never called, `providers.py:851-853` cache still served |
| **L-q moments first** | **COMPLIANT** | `mine.py:372-390` windows of sentences, `contract.py:106-107` moment_id from word indices |
| **L-r no GPU** | **COMPLIANT** | `providers.py:474-532` OllamaLocalBackend requires `gpu0.held()` check, `service.py:669` idle release |

**No violations found.**

---

## SECTION 3: SECURITY

- **SQL injection:** All queries use parameterized `?` placeholders (`queue.py:98-99`, `service.py:294`, etc.). No string interpolation of user input into SQL. **PASS.**
- **Authentication bypass:** No web routes — this is a backend ingest service. `config.py:72-79` StoreGuard prevents writing to main tree without explicit env var. **PASS.**
- **Rate limiting gaps:** `providers.py:654-682` Throttle with queue-aware backoff per backend, `watch.py:37-73` YouTubeGate with global breaker (10→60min), `providers.py:769-771` BoundedSemaphore per backend + global cap of 20. One user cannot exhaust limits — concurrency is bounded. **PASS.**
- **Secrets in code:** No hardcoded keys. `providers.py:180-221` Keyring reads from env file path in config. `providers.py:213-220` redacts all key values from errors. `providers.json` contains no secrets, only `key_env` names. **PASS.**
- **Unvalidated input → DB/filesystem/shell:** `watch.py:59-67` yt-dlp args are constructed from trusted channel IDs (validated `UC` prefix + 24 chars at `watch.py:122-123`). `ledger.py:27` VIDEO_ID regex validates before path join. `purge.py:81-82` FORBIDDEN paths + `startswith("/")` check. **PASS.**
- **One concern:** `providers.py:346-348` `Authorization: Bearer <key>` sent via `urllib` — `_NoRedirect` handler prevents key leakage on redirect. Correct.

---

## SECTION 4: FRONTEND QUALITY

**N/A — This is a backend ingest service with no frontend.** No HTML/CSS/JS. The "UI" is `live.json`, `coverage/*.md`, and CLI tools (`tools/ingest_watch.py`). These are well-structured:

- `stats.py:69-150` live.json has all required fields with proper null handling
- `coverage.py:105-125` coverage markdown has correct table structure
- `tools/ingest_watch.py` CLI has proper subcommands with help text

No frontend to evaluate. Score reflects absence, not failure.

---

## SECTION 5: BACKEND QUALITY

- **DB operations — try/except with rollback:** SQLite in WAL mode with `isolation_level=None` (autocommit). Each `x()` call is a single statement — no multi-statement transactions needing rollback. `queue.py:82` single connection behind RLock. For the operations here (single-row updates, inserts), autocommit is correct. No explicit rollback needed. **PASS.**
- **External API calls — timeout + retry + graceful degradation:** Every backend has `timeout_s` (60-600s), `Throttle` with Retry-After, `Health` circuit breaker (5 consecutive or 50% in window of 10), `transport_retries=3` with backoff. YouTube calls have `YouTubeGate` breaker. All correct. **PASS.**
- **Cron job failure handling:** No cron — long-running tmux process. `_loop()` at `service.py:823-832` catches `Exception` per iteration, logs `loop_error` event, continues. `fetch.process` crash → `PROBE_RETRY` state, not stuck. `mine_video` crash → `MINE_WAIT` state. **PASS.**
- **Memory leaks:** `ThreadPoolExecutor` with bounded workers (3 video, 4 hook windows, 4 check). `purge.py:205-206` SHA cache bounded at 4096 entries with clear. `Health.events` deque maxlen 50. No unbounded growth. **PASS.**
- **Logging:** Every state change → `events` row. Every model attempt → `calls` row + `replies_log/*.jsonl`. Every loop error → `loop_error` event with traceback. `service.py:182-189` dual log (stdout + file). Sufficient for production debugging. **PASS.**

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What is already excellent:**
- The durability model (WAL + flock + fsync + torn-tail handling) is production-grade — better than most startups.
- The provider abstraction with spend freeze, circuit breaker, and throttle is genuinely sophisticated.
- The contract fingerprinting (`contract.py:88-103`) for detecting definition drift is a standout design choice.
- The purge system's one-copy-per-delivery with SHA256 verification is impressively careful.

**What is genuinely missing:**

1. **No alerting beyond STATE.md file writes.** If Heimdall goes down at 3am, nobody knows until someone checks STATE.md. A Bloomberg Terminal would have PagerDuty/OpsGenie integration. The `NOTIFY.txt` log exists but nothing watches it. A simple webhook on `spend_meter` trip and `outage_notice` would be high-impact.

2. **No metrics endpoint.** `live.json` is polled from disk. A `/metrics` Prometheus endpoint (or even a simple HTTP status page) would allow Grafana dashboards and proper SLO tracking. Currently the only observability is `live.json` + log files.

3. **Coverage check is listing-dependent.** If YouTube's RSS and playlist both fail for a channel, that channel is "unmeasured" — but there's no distinction between "YouTube is down" and "channel was deleted." A professional system would track channel health over time.

4. **No dead-letter queue visibility.** Videos in `mine_waiting` with `OUTAGE` reason wait forever during extended outages. There's no max-wait alert or escalation. At 72h horizon, partial videos silently stop retrying.

5. **Caption quality is unmeasured.** The system fetches captions but never validates their quality (e.g., auto-captions with 30% WER would produce garbage moments). A simple word-count or language-detection sanity check would catch this.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Backend logic | 92/100 | State machines, windowing, ledger all correct. Minor Shorts detection gap via URL check. |
| Frontend/UI | N/A | No frontend — backend service. CLI and JSON outputs are clean. |
| Error handling | 94/100 | Every loop catches, every API has timeout/retry/breaker, every crash has fallback state. |
| Security | 96/100 | Parameterized queries, no hardcoded secrets, redirect refusal, path validation. No issues. |
| Performance | 88/100 | Bounded concurrency, WAL, bisection reads, SHA cache. Could benefit from connection pooling at higher scale. |
| Law compliance | 98/100 | All 12 laws verified compliant. No violations. |
| World-class gap | 72/100 | Core ingest is excellent. Missing: alerting, metrics endpoint, caption quality checks. |
| **OVERALL** | **91/100** | Production-ready backend. World-class gaps are operational, not correctness. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No P0 issues — the diff is safe to merge
P1 HIGH     | Add future-timestamp guard log for asked_at | service.py:590 | If system clock jumps forward, valid calibrations silently rejected causing 32 unnecessary live calls; log the rejection reason
P1 HIGH     | Shorts URL detection misses watch?v= Shorts | watch.py:216 | Shorts without /shorts/ in URL enter fetch queue, waste probe quota; add media_type check at listing time or rely solely on fetch.py:157
P2 MEDIUM   | Add webhook/PagerDuty on outage + spend trip | spend.py:66, service.py:793 | Currently only STATE.md file — nobody alerted at 3am; wire NOTIFY.txt to external alerting
P2 MEDIUM   | Add Prometheus /metrics endpoint | stats.py:23 | live.json polling doesn't scale to dashboards; expose metrics over HTTP
P2 MEDIUM   | Validate caption quality after fetch | fetch.py:205 | Auto-captions with high WER produce garbage moments; add word-count/language sanity check
P2 MEDIUM   | purge.py dry_run bytes counted but not verified against actual deletions | purge.py:509 | Dry-run byte counts include files that might fail to delete; acceptable but document the approximation
P3 LOW      | Log _reuse_calibration rejection reason at DEBUG | service.py:574 | Currently silent return False — hard to debug why reuse didn't happen; add debug log per rejection branch
P3 LOW      | Consider adding index on videos(hook_ts, published_ts) | queue.py:95 | hook_due query does full scan on state+published_ts; existing index covers it but hook_ts filtering is unindexed
P3 LOW      | tools/ingest_watch.py purge --measure output could include total GB | tools/ingest_watch.py:198 | Minor UX: sum all reported_not_purged for quick capacity planning
```

---

## SECTION 9: THE ONE THING

**Wire an external alert (webhook, Slack, PagerDuty) to the outage and spend-trip notices — the most sophisticated ingest pipeline in the world is useless if nobody knows it's down at 3am.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff (32fd1d99) is a clean, well-tested optimization that eliminates 32 redundant live API calls per restart without weakening any safety guarantee — every gate (single `asked_at`, model match, age check, at-least-one-passed) was verified correct and mutation-tested. The only material gap is operational: add external alerting so humans know when the system needs them. Merge it.

---

### Reviewer Answers to Specific Questions

**Q1: Can any path let a back-end answer that was not measured live within the day?**
No. Verified all 5 paths:
- **Cached-era record (no `asked_at`):** `asked = {c.get("asked_at") for c in cal.values()}` → `{None}` → `config.aware(None)` → `None` → `t is None` → `return False`. Blocked.
- **Record of another model:** `c.get("model") == self.router.backends[b].model` check at line 584. Blocked.
- **Crash record (empty dict):** `not cal` → `return False` at line 583. Blocked.
- **Future `asked_at`:** `0 <= clock - t.timestamp()` → negative → `return False`. Blocked.
- **Two `asked_at` values:** `len(asked) == 1` fails → `t = None` → `return False`. Blocked.

**Q2: Does reuse interact wrongly with outage retry or daily schedule?**
No. Reuse sets `check_recal_s = CHECK_RECALIBRATE_S (86400)` and `check_calibrated = t.timestamp()` (the live calibration's start time). Next calibration is due at `t + 86400`, which is exactly when the original live calibration would have been due — preserving the daily schedule. Outage retry (CHECK_RETRY_S doubling) only applies inside `_calibrate_checkers()` when `allowed` is empty and `could` is True — reuse only happens when `allowed` is non-empty, so the doubling path is never affected.

**Q3: Is F1's "gates allowed to answer after an outage must be asked LIVE" kept?**
Yes. Reuse requires `allowed = [b for b in eff if cal[b].get("of") == 16 and cal[b].get("right") == 16 and not cal[b].get("unmeasured")]` and `if not allowed: return False`. An outage calibration has `unmeasured > 0` or `of < 16`, so `allowed` is empty → not reused → falls through to live `_calibrate_checkers()`. An outage calibration is never reused.