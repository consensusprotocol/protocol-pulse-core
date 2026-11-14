# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 573.9 s, $0.031, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff ca17cb97)

## SECTION 1: CORRECTNESS

### Main Flow Walkthrough

**Watch → Fetch → Mine → Ledger → Coverage/Purge/Signal**

1. **Watch (`watch.py:176-228`, `service.py:190-208`)**: Lists channels via RSS or uploads playlist, queues new videos. Correctly handles backfill (`BACKFILL_H=72`), Shorts detection via `/shorts/` URL, per-channel backoff. **Defect**: `watch.py:216` — `"/shorts/" in url` is fragile; yt-dlp `media_type` is the canonical Shorts signal but is only available after `probe()`. A Shorts URL format change silently mines Shorts.

2. **Fetch (`fetch.py:120-251`, `service.py:212-241`)**: Probes each video, handles live/upcoming/captions_pending states. `fetch.py:150-151` — RSS publish time used only when `discovered_via=="rss"` — correct. `fetch.py:173-176` — `BACKFILL_H` re-checked at probe time using `pub_ts` — correct double-gate. **Defect**: `fetch.py:212-214` — if `meta.json` already exists from a prior run but `canonical_transcript` is `None` (e.g., transcript file deleted), it re-uses stale `meta` without re-validating `channel_id` match. Minor.

3. **Mine (`mine.py:442-507`, `service.py:245-346`)**: Windows → Router → validate → build lines → append. Overlap dedup with flag union (`mine.py:478-488`) is correct. **Defect**: `mine.py:481` — `rank_score` called with `{"scores": cand["scores"]}` but `rank_score` at `mine.py:387` reads `line.get("risk")` — `cand` has `risk` but the synthetic dict does not, so penalty for `price_prediction`/`doom`/`politics_non_btc` is silently 0 during overlap resolution. The better-ranked observation may be wrong.

4. **Ledger (`ledger.py:34-66`, `service.py:287-296`)**: Append under `wlock` with `carry_forward`, fsync, torn-tail seal. Correct. `ledger.py:55-56` — torn tail closed with `b"\n"` under lock — correct.

5. **Signal (`downsignal.py:98-326`, `service.py:658-684`)**: New in this diff. Detailed below.

### Race Conditions

- **Ledger append vs. read**: `service.py:294-296` — `video_lines()` + `carry_forward()` + `append()` are under `wlock`, but `ledger.read()` in `check_once` (`service.py:493`) and `best_unused_moments` (packager) are **not** under `wlock`. A concurrent append can interleave a torn write between `read` and `offset_before`. Mitigated by `seal()` on restart and `offset_before` margin, but a live packager read during an append can see a partial last line (counted as `bad_lines`, not returned — safe but noisy).

- **Signal `pending` vs. `probe_out`**: `downsignal.py:105-106` — `pending` and `probe_out` share `self.lock`, but `tick()` at `downsignal.py:148-167` reads `probe_thread.is_alive()` **outside** the lock. A probe thread finishing between `is_alive()` check and `_report_probe()` can leave `probe_out` unread for one tick (5s delay, not a correctness bug).

- **Queue `claim`**: `queue.py:167-172` — `UPDATE ... WHERE state IN (...)` is atomic under `self.lock` (single SQLite connection) — correct. No TOCTOU.

### N+1 Queries

- `service.py:266-267` — `SELECT SUM(cost_usd) FROM calls WHERE video_id=?` per mined video — 1 query per video, 3 videos concurrently = 3 queries per cycle. Acceptable at low volume.
- `purge.py:203-220` — `published()` called per file, each does `q.video(vid)` (1 SELECT) + possible `meta.json` read. For 1000 files = 1000 SELECTs. Acceptable for 10-min interval but will scale poorly. No batch query.

### Edge Cases

- **Empty DB**: `stats.py:29` — `min([...] or [now_ts])` handles empty `disc` — correct. `coverage.py:93` — `rep["coverage"] = None` when no eligible — correct.
- **API timeout**: `providers.py:337-341` — `socket.timeout` → `BackendError("timeout")` → retryable — correct. `downsignal.py:202` — probe uses `router.run` with `transport_retries=0` — a single timeout fails the probe immediately (intended: 60s deadline is the probe).
- **Bad input**: `config.py:53-59` — `aware()` returns `None` for timezone-naive strings — fail-closed — correct. `ledger.py:88-112` — `line_problems` validates all required fields — correct.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, dedup, Shorts/live, durable queue, staging store, bounded concurrency, spend cap, ledger, coverage, A/B) | **COMPLIANT** | All components present. `watch.py:176-228` (RSS+playlist), `queue.py:28-61` (SQLite WAL), `config.py:25-28` (poll 600s, concurrency 3), `providers.py:706-708` (global 20 cap), `spend.py:77-157` (meter), `ledger.py:34-66` (append-only), `coverage.py:43-95` (independent listing) |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.py:136-143` enforces ≥2 backends per role. `providers.json:102-111` — `mine` has 2 (heimdall+local), `flagcheck` has 2, `probe` has 2. `providers.py:146-147` — `frozen_vendors` check. `OllamaLocalBackend:476-480` — `gpu0.held()` check, never acquisition. `config.ts():107-123` — StoreGuard |
| **L-l strict schema, never repaired** | **COMPLIANT** | `mine.py:332-384` — `validator()` raises `Invalid` on any deviation, `_pairs` rejects duplicate keys. `providers.py:879-886` — invalid reply re-asked with reason, never repaired. `flagcheck.py:173-200` — same pattern |
| **L-j/L-m fail closed** | **COMPLIANT** | `config.py:53-59` — no timezone = `None` = excluded. `ledger.py:342` — `pub is None` → dropped. `purge.py:298-302` — unreadable delivered set → `refused`, nothing deleted. `downsignal.py:272-278` — unreadable state → `HealthUnreadable`, never guessed |
| **L-h/L-k read as spoken** | **COMPLIANT** | `contract.py:115-126` — `eligibility.spoken()` via `tokens_from_record`. `fetch.py:77-86` — `ts.read_text()` for fingerprint. `mine.py:294-298` — `_untrusted` preserves `>>` markers |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` — `timing` from record, `file_head=True, vod=True`. `mine.py:412-425` — `duration_s=None` when `timing=="segment"`, `duration_estimate_s` set. Packager re-anchors |
| **L-u hard exclusions** | **COMPLIANT** | `mine.py:23-24` — `HARD_RISKS` defined. `ledger.py:347-348` — `any(r in HARD_RISKS for r in eff)` → dropped. `ledger.py:212-241` — `effective_risk` with ruling 40 P1 (imperative/SSB need both models) |
| **L-v speaker/re-uploads/time-sensitive** | **COMPLIANT** | `contract.py:129-135` — `turn_change_inside` measured, `None` if no marker. `ledger.py:351-352` — `turn_change_inside is True` → dropped. `fetch.py:186-191,242-247` — title+duration and text fingerprint dedup. `contract.py:148-159` — `eligibility_at_mining` with `published_at` |
| **Secrets** | **COMPLIANT** | `providers.py:162-203` — `Keyring` reads env file by name, `redact()` replaces values. `providers.py:854-856` — error text redacted before recording. `providers.py:304-309` — `_NoRedirect` prevents key leak on redirect |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:5-9` — `spend_freeze.vendors` lists 4. `providers.py:719-722` — `frozen()` checks vendor, `available()` refuses frozen. `providers.py:782-783` — cached replies still reused when frozen. `service.py:659-672` — logs freeze, warns if <2 callable |
| **B1 90% tripwire NOTIFY never halt** | **COMPLIANT** | `spend.py:126-130` — `state()` returns `tripped`/`unmeasured`/`ok`. `providers.py:727-733` — `order()` moves metered backends last, never removes. `spend.py:159-180` — `write_state_notice` with `keep` for 90% line |
| **B2 nothing lost (outage vs rejected)** | **COMPLIANT** | `service.py:304-345` — `outage` (all backends down/skipped) → `MINE_WAIT` no try used; `rejected` → try counted; 3 passes → `MINED_PARTIAL` with ledger append. `queue.py:25` — `MINE_DUE` includes `MINED_PARTIAL` for retry |
| **B3 GPU0 lease check not acquisition** | **COMPLIANT** | `providers.py:476-480` — `OllamaLocalBackend.enabled()` checks `g.held()`, never `require()`. `providers.py:488-492` — `LocalLLM._post` does `gpu0.require()` internally (main 4867a74a). `service.py:530-531` — `IDLE_RELEASE_S` releases after idle |
| **B4 age-gate ≠ rate-limit** | **COMPLIANT** | `watch.py:24-27` — `AGE_GATE_MARKS` checked first, `RATE_LIMIT_MARKS` only if no age gate. `fetch.py:133-136` — `age_gated` → terminal `UNAVAILABLE` |

---

## SECTION 3: SECURITY

| Check | Result | Detail |
|-------|--------|--------|
| **SQL injection** | **PASS** | All queries use `?` placeholders (`queue.py:94-96,105-106,130-131,157-164,226-234`). No string interpolation of user input into SQL. `queue.py:157-164` — `set_state` validates field names against `VIDEO_FIELDS` allowlist before interpolating column names. `queue.py:189-193` — `set_hook` validates against `HOOK_COLUMNS`. |
| **Auth bypass** | **N/A** | No HTTP routes. CLI tool + background service. `config.py:72-79` — `StoreGuard` prevents writing to main tree without explicit env var. |
| **Rate limiting** | **PASS** | `providers.py:636-664` — `Throttle` with `first_s=2, max_s=60`, `Retry-After` honoured, jitter. `watch.py:37-73` — `YouTubeGate` with breaker (10/20/40/60 min). `providers.py:666-690` — `SpendBook` daily budget per backend. `providers.py:557-622` — `Health` circuit breaker (5 consecutive or 50% in window or slow median). |
| **Secrets in code** | **PASS** | No hardcoded keys. `providers.json:10` — `env_file` points to `.env`. `providers.py:162-203` — `Keyring` reads by name. `providers.py:192-203,223-229` — `__repr__` and `redact()` never expose values. `providers.py:854-856` — errors redacted. |
| **Unvalidated input → DB/filesystem/shell** | **PASS with note** | `watch.py:59-67` — `config.ts()._ytdlp(args)` — `args` are constructed internally, never from user input. `fetch.py:92-93` — `video_id` interpolated into URL but validated as 11-char YouTube ID upstream. `purge.py:76-77` — `FORBIDDEN` paths + `realpath` check prevent directory traversal. `providers.py:150-159` — `override_allowed` restricts base_url to localhost or configured host. **Note**: `purge.py:320` — `glob.glob(t["units"])` with spec-controlled patterns — safe since spec is validated (`load_spec:70-77`). |
| **Shell injection** | **PASS** | No `shell=True`. `transcript_store._ytdlp` uses `subprocess.Popen` with list args. |

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend.** This is a backend ingest service (tmux process, SQLite, JSONL ledger). No HTML/CSS/JS. The "UI" is `live.json`, `coverage/*.md`, and `STATE.md` notices.

- `stats.py:151-158` — `write_live` atomically replaces `live.json` via `os.replace` — correct.
- `coverage.py:105-125` — Markdown report with tables — functional.
- `spend.py:33-59` — `STATE.md` notice block management under `flock` — correct.

**Score: N/A** (no frontend to evaluate; backend reporting is adequate).

---

## SECTION 5: BACKEND QUALITY

| Area | Assessment |
|------|------------|
| **DB writes + rollback** | **GOOD** — `queue.py:79-84` — `isolation_level=None` (autocommit) + `WAL` + `synchronous=FULL`. Each `x()` is one autocommit statement. No explicit transactions, but SQLite autocommit means each statement is atomic. `claim()` at `queue.py:167-172` is a single `UPDATE ... WHERE state IN (...)` — atomic. **Gap**: No `try/except` with rollback around multi-statement sequences (e.g., `add_video` at `queue.py:139-155` does `INSERT OR IGNORE` + `UPDATE` as two autocommit statements — a crash between them leaves channel row stale but video row correct. Acceptable. |
| **External API: timeout+retry+degradation** | **EXCELLENT** — Every HTTP call has timeout (`providers.py:211,324,382,430,460`), retry with backoff (`providers.py:636-664`), circuit breaker (`557-622`), and fallback chain (`694-806`). `watch.py:37-73` — YouTube gate with breaker. Degradation: outage → queue and wait, never crash. |
| **Cron failure handling** | **EXCELLENT** — No cron. Long-running loops with `_loop` at `service.py:642-651` — `try/except Exception` per iteration, `loop_error` event, `delay` with jitter, `stop.wait(max(1.0, delay))` — never crashes service. Each loop (watch/fetch/mine/hook/check/health/purge/signal) is independent. |
| **Memory leaks** | **GOOD** — `ThreadPoolExecutor` with bounded workers (20 global, 3 videos, 2 hooks, 4 checks). `Health.events` capped at 50 (`558: maxlen=50`). `calls` table grows unbounded — at ~1000 calls/day, ~365K rows/year. No cleanup. Will need rotation eventually but not urgent. |
| **Logging** | **GOOD** — `service.py:153-162` — every state change is an `events` row + `service.log` file + stdout. `service.py:648-649` — loop errors logged with `traceback.format_exc()[-2000:]`. **Gap**: No structured log levels (all `print`); no log rotation for `service.log`. |

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What is already excellent:**
- The durability model (WAL SQLite + fsync ledger + torn-tail seal + `carry_forward` flag union) is production-grade. Few startups do this well.
- The provider abstraction (frozen vendors, circuit breaker, throttle, spend book, cache, redaction) is genuinely impressive — rivals enterprise API gateway patterns.
- The contract fingerprinting (`contract.py:88-103`) — hashing function source + probe output — is a sophisticated defense against silent definition drift.

**What is genuinely missing:**

1. **No observability beyond `live.json`**: No metrics endpoint (Prometheus), no alerting on coverage drop, no latency histogram. Bloomberg would have real-time dashboards. A `coverage < 80%` should page someone, not just write a markdown file.

2. **No backpressure on queue growth**: If Heimdall is down for hours, `MINE_WAIT` videos accumulate. `mine_once` at `service.py:523-543` processes 3 at a time every 5s — but `fetch` keeps adding new videos. No queue depth metric or alert. At 64 channels × ~5 videos/day × 12h outage = ~160 videos queued. Manageable now, but no guard.

3. **Single SQLite file is a SPOF**: All state (channels, videos, calls, events, kv) in one `queue.sqlite`. No backup, no replication. A disk-full or corruption loses everything. World-class would have periodic `VACUUM INTO` backup or WAL archiving.

4. **No idempotency key on ledger append**: `ledger.py:34-66` relies on `moment_id` dedup at read time, but concurrent `mine` + `hook` appends for the same video (different `wlock` acquisitions) could interleave. The `wlock` serializes them within one process, but a second process (if `service.lock` fails) would corrupt the ledger. The `flock` on `service.lock` is the only guard — no ledger-level lock file.

5. **Coverage check is best-effort, not authoritative**: `coverage.py:43-95` re-lists channels independently but uses the same `watch.registry()` and `watch.rss_list`/`playlist_list` — if YouTube is down, coverage itself is `unmeasured`. No external validation (e.g., comparing against YouTube API directly).

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **88/100** | Correct state machine, proper windowing, flag union, expiry. Minor: `rank_score` bug in overlap dedup, Shorts detection fragility |
| **Frontend/UI** | **N/A** | No frontend. Reporting (live.json, coverage.md, STATE notices) is functional |
| **Error handling** | **92/100** | Every external call has timeout/retry/circuit-breaker. Every loop catches exceptions. Fail-closed throughout. Missing: log rotation, queue depth alert |
| **Security** | **95/100** | No injection vectors, secrets properly handled, redirect refused, override restricted. Minor: no ledger-level lock beyond service.lock |
| **Performance** | **82/100** | Bounded concurrency (20 global), bisection read for ledger, WAL mode. Gaps: N+1 in purge `published()`, unbounded `calls` table, no connection pooling needed (single connection is correct for SQLite) |
| **Law compliance** | **98/100** | All 12+ laws verified compliant. Spend freeze, tripwire, B1-B4 all correctly implemented. Only deduction: `rank_score` penalty gap is a minor L-u-adjacent issue |
| **World-class gap** | **72/100** | Durability and provider abstraction are world-class. Missing: metrics/alerting, queue backpressure, DB backup, external coverage validation |
| **OVERALL** | **87/100** | Production-ready backend with excellent durability and law compliance. Fix the `rank_score` bug and add queue-depth alerting before scaling |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | Fix rank_score penalty in overlap dedup | mine.py:481 | Overlap resolution ignores risk penalties (price_prediction/doom/politics_non_btc), so the wrong observation's scores/reason can win when the same range appears in two windows
P1 HIGH     | Add queue depth metric and alert | service.py:523, stats.py:68-91 | Heimdall outage queues videos unboundedly; no metric tracks depth, no alert fires — silent data loss risk if outage exceeds 72h horizon
P1 HIGH     | Fix Shorts detection to use media_type | watch.py:216, fetch.py:157-159 | URL-based Shorts check misses Shorts with non-/shorts/ URLs; media_type from probe is canonical but only checked in fetch, not watch — Shorts can enter mining queue
P1 HIGH     | Add ledger file lock independent of service.lock | ledger.py:45-46 | If service.lock fails (NFS, stale lock), concurrent ledger appends corrupt the file — ledger should have its own flock
P2 MEDIUM   | Batch published() lookups in purge | purge.py:203-220,278-392 | Per-file SELECT + meta.json read for 1000s of files — add batch query or cache warming
P2 MEDIUM   | Add calls table rotation | queue.py:49-55, stats.py:86-87 | calls grows forever (~365K rows/year); add monthly DELETE or archive for rows older than 90 days
P2 MEDIUM   | Validate downsignal probe vendor isolation | downsignal.py:198-213, providers.json:96-111 | Probe backends share keys/gateway with miner — under load, probe calls queue behind mining calls despite max_inflight=1 (global cap is 20, probe competes)
P2 MEDIUM   | Add log rotation for service.log | service.py:83-84,153-162 | service.log grows unbounded in long-running tmux — add RotatingFileHandler or logrotate
P3 LOW      | Tighten VIDEO_ID regex in handoff | tools/ingest_watch.py:108-109 | handoff iterates all transcript dirs without validating video_id format first — minor, only affects manual handoff
P3 LOW      | Add structured log levels | service.py:153-162 | All logs are print() — add level filtering for production debugging
```

---

## SECTION 9: THE ONE THING

**Fix the `rank_score` bug at `mine.py:481` — it silently picks the wrong observation when overlapping windows disagree on risk penalties, undermining the entire flag-union safety net you carefully built.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production** — the durability model, provider abstraction, and law compliance are genuinely excellent and exceed typical startup quality. Before scaling beyond 64 channels, fix the `rank_score` overlap bug (P0), add queue-depth alerting for Heimdall outages (P1), and harden Shorts detection to use `media_type` (P1) — all are small, surgical fixes.

---

## ADDENDUM: Review Questions (ruling 87 diff)

**1. Ordering — pending answer flushed ~5s late clearing a builder failure:**
Not a real defect. `downsignal.py:132-135` — `pending["answer"]` overwrites `pending["fail"]` (answer clears failure), and `_flush` at `downsignal.py:188-196` writes answer before failure. If builder noted `False` at T+2s and watcher flushes `True` at T+5s with `now=T+0s`, the module sees `note(True, now=T+0s)` then `note(False, now=T+2s)` — failure still recorded. The 30s `HEARTBEAT_S` in the module (`heimdall_health.py:40`) means answers within 30s of each other are deduplicated anyway. The 15-minute `DOWN_AFTER_S` dwarfs any 5s ordering jitter.

**2. Two processes probing — 3 answers from 2 rounds:**
Module's responsibility. `downsignal.py:162-163` — `probe_due()` does not claim/lock the probe; both processes can start probes concurrently. `heimdall_health.py:probe_result` increments `probe_streak` per call — 2 concurrent probes both answering = streak 2, not 3. Need 3 sequential `probe_result(True)` calls. With `PROBE_EVERY_S=120s`, two processes probing every 5s will each call `probe_due` → both get `True` → both probe → both report → streak goes 0→1→2 in one round, then 2→3 next round. So 3 answers still requires ~2 probe intervals (4 min), not 1. Correct behavior — the module's `probe_streak` is the single source of truth.

**3. http_4xx as "not answered":**
Correct per contract. `downsignal.py:40` — `ANSWERED = {"ok", "invalid"}` — only gateway-answered calls count. `http_4xx` (400 Bad Request) means the gateway rejected the request — it did not answer with model output. Per `heimdall_health.py:note` docstring: "down, refused, empty or late" = not answered. A 400 caused by our bad request is still "not answered" from the signal's perspective — the gateway did not produce a verdict. The `http_4xx` will also trip the circuit breaker (`providers.py:604-607`), so repeated 400s open the circuit and the video goes to `MINE_WAIT` (outage) — correct, as the gateway is not serving us.

**4. Signal changing miner calls / blocking / raising:**
No path exists. `downsignal.py:122-137` — `noted()` is O(1) under local lock, never touches shared file, never raises (bare `except: pass`). `tick()` runs in its own `signal` thread (`service.py:682-684`), never in miner threads. `router.run()` at `downsignal.py:202` for probes uses `use_cache=False` but goes through normal `Router` — it can block the `signal` thread on throttle/breaker, but never miner threads. No exception from `DownSignal` propagates to `Router` or `Service._on_attempt`.

**5. _seen() kv count across restarts / replaced state file:**
Correct. `downsignal.py:244-252` — `signal_switches_seen` stored in `queue.sqlite` kv (durable). On first sight or when `seen > len(sw)` (state file replaced/truncated), it records `len(sw)` without announcing history — correct. `downsignal.py:253-270` — per-switch loop increments `seen` one at a time with `kv_set` after each — crash between switches re-announces from last committed count. `STATE write failure` at `downsignal.py:257-263` — `return` without incrementing `seen` → retried next tick — correct.

**6. Thread safety of DownSignal:**
Safe. `pending`/`probe_out` under `self.lock` (`downsignal.py:105,130,182,215`). Module calls (`note`/`mode`/`probe_due`/`probe_result`) only in `tick()` which runs in single `signal` thread. `health` thread reads `self.error`/`self.busy_since`/`self.mode` without lock — these are set only in `signal` thread, read in `health` thread. In CPython, simple attribute reads/writes are atomic under GIL, but `self.error` + `self.error_since` should ideally be read under lock for consistency (e.g., `check_notice` at `downsignal.py:301-302` reads both — a `tick()` setting them between reads could see `error` set but `error_since` still old value). **Minor race, not a correctness bug** — at most one extra/missed notice cycle.

**7. Probe starvation:**
Low risk but real. `providers.json:78-94` — probe backends have `max_inflight=1` each, `timeout_s=60`. Mining backends have `max_inflight=12` (qwen) + `max_inflight=1` (local). Global cap is 20 (`providers.json:4`). Probe competes for global slots: `providers.py:846` — `with self.sems[bid], self.gsem` — probe needs both its backend semaphore (1 slot, dedicated) and global semaphore (20 slots). Under full mining load (12 qwen + 1 local + 8 glm + 4 muse = 25 requested, capped at 20 global), probe waits for a global slot. Mitigated by: probe has `breaker: false` (never circuit-open), `transport_retries: 0` (fast fail), and mining windows are short (~20s each). Worst case: probe waits ~20s for a global slot, then 60s timeout = 80s probe latency. Acceptable for 2-minute probe interval. **No starvation, but probe latency degrades under load.**
