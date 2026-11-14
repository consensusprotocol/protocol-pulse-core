# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 602.2 s, $0.031, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff 0abeb304 vs 159c6709)

## SECTION 1: CORRECTNESS

### 1.1 The diff's claimed fix — does it work?

**Yes, the core F1 fix is correct.** `flagcheck.calibrate(..., fresh=True)` now forces `use_cache=False` at `flagcheck.py:289`, which bypasses `providers.py:851-856` cache path. The old code used default `use_cache=True` and therefore replayed `replies/<backend>/<aa>/<sha>.json` without ever calling the gateway. The new test `test_f1_the_watchers_calibration_asks_the_model_live_never_a_stored_reply` proves it: 16 calls → 32 calls after model change, `allowed` flips from `["ca"]` to `[]`.

**Rounds loop is correctly aggregated:**

* `flagcheck.py:295-301` — `answers` dict keyed by `(bid,i)` is overwritten only when `todo` is re-asked. `todo` is filtered to `answers[j] is None` only. So a re-asked quote's final answer replaces `None`; a previously-answered quote is never re-asked. No duplicates, no order dependence.
* `flagcheck.py:302-317` — second pass iterates `jobs` (the canonical list) and reads `answers[(bid,i)]`. A backend with no effective entry simply never appears in `jobs` (because `jobs` is built from `router.effective(ROLE)`), so no phantom entry. Correct.
* Edge: `rounds` is clamped via `max(1, int(rounds))` — `rounds=0` still does 1 round. Intentional and documented.

**Schedule doubling is correct and bounded:**

* `service.py:493-502` — Three branches:
  1. `check_allowed` non-empty OR `could==[]` → `CHECK_RECALIBRATE_S` (86400). Correct: success or hopeless failure → daily.
  2. `check_recal_s >= 86400` → `CHECK_RETRY_S` (600). Correct: first failure after a daily interval resets to 600, not 172800.
  3. else → `min(86400, 2*check_recal_s)`. Correct: 600→1200→2400→4800→9600→19200→38400→76800→86400. Capped.
* After cap, next failure hits branch 2 again (since `check_recal_s==86400`), resetting to 600. This matches spec A34 "after the cap it starts again at 600". Verified.
* **No tight loop:** `service.py:489` gates on `clock() - check_calibrated >= check_recal_s`. Minimum `check_recal_s` is 600. `check_once` is called every `CHECK_EVERY_S=30` but returns immediately if not due. No tight loop possible. The `check_inflight`/`check_next` ledger-skip optimization at `service.py:512-520` further prevents busy-wait.

### 1.2 Pre-existing correctness issues (not introduced by diff, but must be flagged)

**P0 — `ledger.py:offset_before` bisection can return wrong offset when `mined.at` is missing or malformed:**
At `ledger.py:139-144`, unreadable lines are skipped via `while t is None: raw=f.readline()`. If a 64KB block contains only unreadable lines, `t` stays `None` and `hi=mid` is taken, which is conservative (reads more). Safe. But if the file has a long run of lines with missing `mined.at` (pre-stamp lines), the bisection degrades to linear scan of that region. Not a correctness bug, but a performance cliff at 100k+ lines.

**P1 — `service.py:305-308` `carry_forward` + `append` race window is correctly closed by `wlock`, but `hook_video` and `mine_video` share the same `wlock`:**
`service.py:299-308` holds `wlock` across `video_lines` read + `carry_forward` + `append`. This is correct for single-process. However `hook_video` at `service.py:402` also calls `_append` under same lock. With `HOOK_VIDEOS=2` and `mine` concurrency 3, contention is bounded. No deadlock (single lock, no nesting).

**P1 — `providers.py:851` cache check uses `cfg.get("enabled",True)` not `backend.enabled()`:**
```python
if use_cache and self.backends[bid].cfg.get("enabled", True):
```
This bypasses `OllamaLocalBackend.enabled()` which checks `gpu0.held()`. So a disabled local backend's stale cache could be returned even when GPU lease not held. For `fresh=True` path this is irrelevant (cache bypassed), but for normal mining it means a stale local reply could be reused when local is disabled. Low impact because `mine` chain's local is `enabled:false` in config, but the code path is technically wrong — should call `self.backends[bid].cfg.get("enabled")` is not equivalent to `enabled()` for local backend.

**P2 — `flagcheck.py:254` `checkers()` returns `[]` when miner is `None`:**
If `mined.backend` or `mined.model` is missing (old ledger lines), `checkers` returns `[]` and `ask` returns `unmeasured: no checker`. This is fail-closed and correct per L-j, but means old ledger lines can never be second-checked. Acceptable.

**P2 — `service.py:584-597` `_paid_due` caches `tpm` in `self._conv` without invalidation on transcript update:**
If a video's transcript is re-fetched (caption update), `episode_measure` could change but `_conv` cache persists until 5000 entries. Minor; paid route is rare.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, dedup, Shorts/live, durable queue, staging store, bounded concurrency, spend cap, ledger, coverage, A/B) | **COMPLIANT** | `watch.py:176-228` poll_channel, `queue.py:77-95` WAL+recover, `providers.py:769-770` global 20 cap, `spend.py:81-161` meter, `ledger.py:34-66` append, `coverage.py:43-95` independent listing |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:106-121` every role ≥2 backends, `providers.py:777-804` chain/order/effective, `providers.py:474-532` OllamaLocalBackend with `gpu0.held()` check, `providers.py:154-161` validates ≥2 |
| **L-l strict schema, never repaired** | **COMPLIANT** | `mine.py:332-384` validator raises `Invalid` on any deviation, `providers.py:983-989` re-prompts with reason but never repairs JSON, `flagcheck.py:174-202` same |
| **L-j/L-m fail closed, nothing measured is never a pass** | **COMPLIANT (fixed by this diff)** | **Before diff: VIOLATION** — calibration replayed cache, `providers.py:852` comment "calls nobody, proves nothing about health" — a stale pass released flags. **After diff: COMPLIANT** — `flagcheck.py:289` `use_cache=False`, `flagcheck.py:341` requires `of==len(probes) and right==of`, `service.py:493-502` unanswered→retry not pass |
| **L-h/L-k read as spoken, never rewrite** | **COMPLIANT** | `contract.py:123` `E.spoken(toks[w0:w1+1])`, `fetch.py:237` `ts._store(rec)` verbatim, `mine.py:294-297` `<`→`‹` preserves `>>` markers |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `timing` from record, `mine.py:412-425` `duration_s: None` when `timing=="segment"`, `ledger.py:15` comment |
| **L-u hard exclusions** | **COMPLIANT** | `mine.py:23-24` HARD_RISKS, `ledger.py:347-348` `any(r in HARD_RISKS for r in eff)` drops, `ledger.py:212-241` second-model release only on `no` |
| **L-v speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`, `ledger.py:351-353` speaker/re-upload checks, `fetch.py:218-234` title+duration and text_fp dedup |
| **Secrets** | **COMPLIANT** | `providers.py:180-220` Keyring from env file, `providers.py:213-220` redact, `providers.py:953-955` redact before record, `providers.py:322-324` no redirect |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:5-9` freeze list, `providers.py:783-786` `frozen()`, `providers.py:806-818` `available()` refuses frozen unless `freeze_lifted`, `providers.py:931-932` double-lock in `_try`, `service.py:735-748` warning names ruling 98 |
| **L-q moments first** | **COMPLIANT** | `mine.py:269-287` windows of sentences, `mine.py:444-508` mine_video, `service.py:257-361` mine loop |
| **L-r GPU0 no GPU** | **COMPLIANT** | `providers.py:474-532` local only under `gpu0.held()`, `service.py:114-118` executors, no Whisper/NVENC |
| **Ruling 76/77 expiry 12h + purge** | **COMPLIANT** | `config.py:36-37` EXPIRY_H=12, `ledger.py:280-286` expiry(), `ledger.py:337-338` expired drop, `purge.py:278-392` targets+delivered guard |
| **Ruling 80 hook pass** | **COMPLIANT** | `mine.py:121-213` HOOK_PROMPT with builder verbatim, `service.py:362-445` hook loop, `ledger.py:187-209` carry_forward |
| **Ruling 87 shared Heimdall-down signal** | **COMPLIANT** | `downsignal.py:99-487` note/tick/probe/seen, `providers.py:133-142` down_signal validation, `spend.py:199-231` switch/signal notices |
| **Ruling 98 paid route** | **COMPLIANT** | `providers.json:96-99` paid_route, `providers.py:125-132` freeze_lifted+cap validation, `providers.py:687-727` RoleCaps, `downsignal.py:198-267` _route_tick, `service.py:552-611` _paid_due/_queue_rechecks |
| **Ruling 40 P1 second-model flag check** | **COMPLIANT (after diff)** | `flagcheck.py:333-341` watcher_checkers, `ledger.py:212-241` effective_risk, `service.py:447-550` check loop. **Before diff: PARTIAL** — calibration not live |

---

## SECTION 3: SECURITY

**SQL injection: PASS.** All queries use parameterized `?` placeholders. No string interpolation of user input into SQL. `queue.py:96-98` `x(sql,args)` always uses `db.execute(sql,args)`. `queue.py:160-165` `set_state` validates keys against `VIDEO_FIELDS` allowlist before building `SET` clause. `queue.py:203-208` `set_hook` validates against `HOOK_COLUMNS`. No ORM `filter()` with user input.

**Authentication bypass: N/A — no HTTP routes.** This is a backend ingest service, not a web app. No auth surface.

**Rate limiting gaps: PASS with notes.**
* `watch.py:37-73` YouTubeGate: global breaker 10→20→40→60 min on 429/bot-check, per-channel backoff `2^n` min max 60, `YTDLP_CONCURRENCY=3`.
* `providers.py:654-682` Throttle: per-backend queue-aware backoff, `Retry-After` honoured, `first_s=2.0 max_s=60.0`.
* `providers.py:575-640` Health: circuit breaker 5 consecutive or 50% of 10 in 600s or median >150s, open 300s.
* **Gap:** No per-IP or per-user rate limiting because there are no users. Gateway-level spend caps (`daily_budget_usd`, `daily_cap_usd` $2.00 for paid route) are the effective rate limit. Adequate.

**Secrets in code: PASS.**
* No hardcoded keys. `providers.py:180-208` Keyring reads from `env_file` (`/home/ultron/protocol_pulse/.env`). `providers.py:213-220` `redact()` replaces values ≥8 chars. `providers.py:953-955` redacts `detail` and `raw` before recording. `providers.py:322-324` refuses redirects to prevent bearer leak. Verified no `sk-`, `xai-`, `AIza` literals in code.

**Unvalidated input reaching DB/filesystem/shell: PASS with one flag.**
* `fetch.py:92-93` `gate.run(["-J", ..., f"https://www.youtube.com/watch?v={video_id}"])` — `video_id` comes from `watch.py` listing (YouTube API) or `queue.py` DB, both constrained to `VIDEO_ID` regex `^[A-Za-z0-9_-]{11}$` at `ledger.py:27`. No shell injection (args list, not shell string).
* `purge.py:76-77` validates `units` is absolute, no `..`, not in `FORBIDDEN`. `purge.py:344` checks `rp.startswith(unit_real)` and `not rp.startswith(protect)`.
* `providers.py:168-177` `override_allowed` restricts `base_url` override to `127.0.0.1`/`localhost`/`::1` or same host+scheme.
* **Flag:** `config.py:68-69` `store_root()` uses `os.environ.get("PP_INGEST_STORE")` with `os.path.realpath` but no allowlist. An attacker with env control could point store to arbitrary path. Mitigated by `check_store()` guard at `config.py:72-79` which refuses `MAIN_TREE` unless `PP_INGEST_ALLOW_MAIN_STORE=1`. Acceptable for single-tenant.

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend.** This is a headless ingest service. No HTML, CSS, JS, or UI components. The "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` markdown reports. All async operations (watch/fetch/mine/hook/check/purge/signal) have structured logging via `service.py:166-173` and `live.json`/`coverage/*.md` outputs. No loading/error/empty states to evaluate in a UI sense.

If this were to be scored: the CLI is well-structured with `argparse` subcommands, `--dry-run` defaults, and human-readable summaries. But there is no user-facing product UI in this package.

---

## SECTION 5: BACKEND QUALITY

**DB operations — STRONG:**
* `queue.py:81-86` WAL + `synchronous=FULL`, single connection behind `RLock`, `timeout=30`.
* `queue.py:168-174` `claim()` is atomic `UPDATE ... WHERE state IN (...)` with `rowcount` check — correct for concurrent workers.
* `ledger.py:45-66` `append()` uses `O_APPEND|O_CREAT` + `flock(LOCK_EX)` + `fsync` + torn-tail repair. Crash-safe.
* **Missing:** No explicit `try/except` with `rollback` on writes. SQLite with `isolation_level=None` (autocommit) means each `execute` is its own transaction. A failed multi-statement operation (e.g., `set_state` + `event`) could leave partial state. In practice `set_state` does `UPDATE` then `INSERT INTO events` as two autocommit statements — if the second fails, the state change persists without an event. Low risk but technically not atomic.

**External API calls — EXCELLENT:**
* Every yt-dlp call through `YouTubeGate.run()` with timeout, concurrency cap, breaker.
* Every LLM call through `Router._try()` with per-backend throttle, health breaker, transport retries (3), `Retry-After` honoured, spend tracking.
* `spend.py:101-120` `CreditMeter.measure()` handles `GET /credits` failure gracefully, sets `last_error`, transitions to `unmeasured`.

**Cron job (long-running loops) — STRONG:**
* `service.py:717-726` `_loop` wraps `fn()` in `try/except Exception`, logs `loop_error` event, never crashes service. `BaseException` (SIGTERM, GPU0 stop) propagates correctly.
* `service.py:764-775` SIGINT/SIGTERM handler sets `stop` event, joins threads with 30s timeout.
* `service.py:131-133` `ledger.seal()` on start handles torn tail from crash.

**Memory leaks — PASS:**
* `queue.py:81` single SQLite connection, not per-request.
* `service.py:114-118` bounded thread pools (20 global, 3 videos, 2 hooks, 4 checks).
* `providers.py:581` `Health.events` deque maxlen 50.
* `service.py:584-585` `_conv` cache cleared at 5000 entries.
* No unbounded growth detected.

**Logging — STRONG:**
* `service.py:166-173` `_log` with ISO timestamp, stdout + file.
* `queue.py:106-109` every state change → `events` row with `detail` JSON.
* `providers.py:830-835` `_emit` → `on_attempt` → `queue.call()` + `replies_log/YYYY-MM-DD.jsonl`.
* `downsignal.py:418-423` evidence file for every signal interaction.
* `purge.py:270-276` `deleted.jsonl` + `passes.jsonl`.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What is already excellent (explicitly):**
* The durability story is best-in-class for a Python ingest service: WAL SQLite, `O_APPEND`+`flock`+`fsync` ledger, torn-tail repair, single-service lock, crash recovery. This is more careful than most production ingest pipelines.
* The provider abstraction (`providers.py` 1011 lines) with health/breaker/throttle/spend/cap/cache/override is genuinely impressive — it handles more failure modes than most gateway wrappers.
* The contract fingerprinting (`contract.py:88-103`) — hashing function source + probe output to detect drift — is a sophisticated correctness mechanism rarely seen outside formal verification.
* The purge safety model (`purge.py` 429 lines) with delivered-set protection, `/proc` open-file check, and `FORBIDDEN` paths is exceptionally thorough.

**What is genuinely missing:**

1. **No observability beyond log files.** No metrics endpoint (Prometheus `/metrics`), no structured alerting, no dashboard. Bloomberg/Coinbase would have latency histograms, error rate SLOs, and PagerDuty integration. Currently you `tail service.log` and read `live.json`. For a 24/7 ingest service, this is the biggest gap.

2. **No integration test that runs the full pipeline against a real (or recorded) YouTube channel.** 286 unit tests with `FakeBackend` are excellent for logic, but no test exercises `watch.poll_channel` → `fetch.process` → `mine.mine_video` → `ledger.append` → `ledger.best_unused_moments` end-to-end with a realistic transcript. The `test_service.py::test_watch_fetch_mine_end_to_end` exists but uses fakes throughout.

3. **Coverage check is best-effort, not authoritative.** `coverage.py:43-95` re-lists channels at check time, but if YouTube's listing is eventually consistent (RSS cache 15 min, playlist approximate dates), the coverage number has inherent uncertainty. No reconciliation against YouTube Data API v3 (which would be authoritative but costs quota). For a "never miss" guarantee, this is a soft spot.

4. **No backpressure on the mining queue.** If Heimdall is down for hours, `MINE_WAIT` videos accumulate. When it returns, all become due simultaneously and `mine_once` claims 3 at a time, but each video's windows fan out to `executor` (20 slots). A burst of 100 queued videos could take hours to drain with no priority beyond publish time. No queue depth alert.

5. **Hook pass has no quality gate.** `mine.py:494-507` drops hooks outside 4-14s or with bad openers, but there's no minimum quality threshold — a hook with all scores 0 still gets written to the ledger. The packager must filter, but the ledger accumulates low-quality hook rows.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Diff fix is correct, well-tested, bounded. Pre-existing logic is exceptionally thorough. -8 for cache/enabled inconsistency and no atomic multi-statement transactions. |
| **Frontend/UI** | **N/A** | No frontend in this package. CLI tooling is solid but not a UI. |
| **Error handling** | **94/100** | Every external call has timeout+retry+breaker+fallback. Every loop has try/except. Fail-closed throughout. -6 for autocommit non-atomicity on state+event writes. |
| **Security** | **96/100** | No injection, no hardcoded secrets, proper redaction, redirect refusal, override allowlist, path traversal guards. -4 for env-controlled store path (mitigated by guard). |
| **Performance** | **88/100** | Bounded concurrency, WAL, bisection read, overlap-capped windows. -12 for no queue depth backpressure, bisection degradation on malformed lines, no metrics to observe bottlenecks. |
| **Law compliance** | **98/100** | All 12+ laws compliant after diff. Before diff, L-j/L-m was violated by stale calibration. Diff fixes it completely. -2 for `OllamaLocalBackend` cache bypass minor. |
| **World-class gap** | **78/100** | Durability and provider abstraction are world-class. Missing: observability/metrics, E2E integration test, authoritative coverage, backpressure, hook quality gate. |
| **OVERALL** | **91/100** | Production-ready backend service with exceptional attention to correctness and failure modes. The diff is a precise, well-tested fix for a real L-m violation. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | Fix stale calibration releasing hard flags | flagcheck.py:285-289, service.py:489-502 | Before this diff, a model change behind same gateway name kept releasing L-u flags on stale cached answers — wrong clips could reach packager. THIS DIFF FIXES IT. Verify deployed.
P1 HIGH     | Cache check bypasses OllamaLocalBackend.enabled() | providers.py:851 | `cfg.get("enabled",True)` ignores gpu0.held() check — stale local reply could be returned when GPU lease not held. Change to `self.backends[bid].enabled()` or add explicit local-backend guard.
P1 HIGH     | No atomicity on state+event multi-writes | queue.py:159-166, service.py:316-360 | `set_state` does UPDATE then INSERT events as two autocommit statements — crash between them leaves state without audit trail. Wrap in explicit transaction.
P1 HIGH     | Add Prometheus metrics endpoint | service.py:625-642 health_once | No way to alert on queue depth, error rate, or coverage drop without polling live.json. Add /metrics with queue_states, backend error rates, coverage.
P2 MEDIUM   | Bisection degrades on malformed mined.at | ledger.py:122-149 offset_before | Long runs of lines with missing/bad mined.at cause linear scan within 64KB blocks. Add fallback: if >N consecutive unreadable, skip block.
P2 MEDIUM   | No E2E test with realistic transcript | tests/ingest/test_service.py | 286 tests all use FakeBackend — no test runs watch→fetch→mine→ledger→adapter with a real transcript fixture. Add one golden-path test with a recorded transcript.
P2 MEDIUM   | Hook rows with all-zero scores written to ledger | mine.py:494-507 | No minimum quality threshold — ledger accumulates low-quality hooks. Add rank_score floor or require at least one score >=3.
P2 MEDIUM   | _conv cache not invalidated on transcript update | service.py:584-597 | Paid route conversation detection caches tpm forever (until 5000 clear). If transcript re-fetched, stale tpm used. Invalidate on re-transcribe.
P3 LOW      | Store path from env without allowlist | config.py:68-69 store_root() | PP_INGEST_STORE could point anywhere (mitigated by check_store guard). Add allowlist or log warning when outside expected parent.
P3 LOW      | Coverage uses approximate playlist dates | coverage.py:58-68 | When RSS unavailable, playlist approximate_date has inherent uncertainty at 24h boundary. Document confidence interval or use Data API for coverage check.
P3 LOW      | Log line "asked live" could include calibration latency | service.py:506-509 | Useful for detecting slow calibration blocking check loop. Add duration to log line.
```

---

## SECTION 9: THE ONE THING

**Add a Prometheus `/metrics` endpoint and alert on queue depth, backend error rate, and coverage — you have 286 tests proving correctness but zero observability proving liveness.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff is a surgical, well-tested fix for a genuine L-m violation (stale calibration releasing hard flags) — it correctly forces live measurement, retries transient failures without blocking on permanent ones, and bounds retry cost. The broader codebase is among the most carefully engineered ingest services reviewed, with exceptional durability, failure handling, and law compliance. Deploy the diff, add metrics/alerting, and add one E2E test with a real transcript fixture.