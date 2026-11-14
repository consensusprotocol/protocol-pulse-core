# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 680.2 s, $0.029, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (Ruling 80 + Ruling 77 fixes)

**Branch:** `pp-ingest` | **Diff:** `e416cbfd` working tree | **Reviewer:** Independent Model | **Date:** 2026-11-14

---

## SECTION 1: CORRECTNESS

### 1.1 Main Flow Walkthrough

**Watch → Fetch → Mine → Hook → Purge → Coverage**

| Step | Claim | Reality | Verdict |
|------|-------|---------|---------|
| Watch | RSS first, fallback to uploads playlist, 10min poll | `watch.py:187-204` correct. Canary logic `service.py:169-172` correct. | ✅ |
| Fetch | Probe → caption fetch via `transcript_store` | `fetch.py:120-251` correct. Age-gate terminal, rate-limit backoff correct. | ✅ |
| Mine | Windows → Router → validator → ledger append | `mine.py:382-442` correct. Overlap dedup with flag union correct. | ✅ |
| Hook | Second pass over same windows, 4-14s filter | `mine.py:430-441` + `service.py:322-396` — **has correctness bugs** (see below) | ⚠️ |
| Purge | Delete expired media, protect delivered | `purge.py:278-396` — **fixed from fail-open, now correct** | ✅ |
| Coverage | Independent listing, mined/eligible ratio | `coverage.py:43-95` correct. Unmeasured handling correct. | ✅ |

### 1.2 Logic Errors Found

**C1 — `carry_forward` altcoin logic is inverted (mine.py carry, ledger.py:200)**

```python
# ledger.py:200
fx["altcoin"] = bool(fx.get("altcoin") is not False or ex.get("altcoin") is not False)
```

This reads: "altcoin is True if EITHER observation said altcoin is not False". But `altcoin` defaults to `False` when absent. The expression `fx.get("altcoin") is not False` is `True` when the key is missing (`None is not False == True`), when it's `True`, but `False` only when explicitly `False`. So:

- If new line has `altcoin=False` and earlier has `altcoin=False` → `False or False = False` → `bool(False)=False` ✅
- If new line missing key (None) and earlier `False` → `True or False = True` → `True` ❌ — **creates a false altcoin flag from a missing key**
- If new line `True` and earlier `False` → `True or False = True` → `True` ✅

The intent is "either observation flagged altcoin" — should be `bool(fx.get("altcoin") or ex.get("altcoin"))`. The current code conflates "missing" with "true". In practice `build_line` always sets `flags_ext.altcoin` explicitly, so this only triggers on malformed/old ledger lines — but it's still wrong and violates the "fail closed" principle (a missing flag should not become a positive).

**C2 — `carry_forward` about_bitcoin conjunction is correct but fragile (ledger.py:201)**

```python
fx["about_bitcoin"] = bool(fx.get("about_bitcoin") is True and ex.get("about_bitcoin") is True)
```

This is correct: `about_bitcoin` is `True` only if BOTH observations said `True`. If either said `False`, result is `False`. If either is missing/None, result is `False` (fail closed — not about Bitcoin unless both agree). Correct.

**C3 — Hook pass cost query double-counts on retry (service.py:347-348)**

```python
cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role='hook'", (vid,))[0]["usd"] or 0.0
```

On retry (tries < HOOK_TRIES), `hook_cost_usd` is updated but `cost` accumulates ALL hook calls for that video across all passes. This is intentional (total cost), but `hook_cost_usd` on intermediate retries overwrites rather than accumulates correctly if the DB query includes previous passes' costs — actually it does accumulate correctly since it's SUM over all calls. No bug, but the intermediate `hook_cost_usd` values during retries are misleading in `live.json` until final.

**C4 — `hook_due` horizon check uses `published_ts` which may be NULL (queue.py:177-183)**

```python
"AND published_ts >= ?"  # now - horizon_s
```

Videos with `published_ts IS NULL` (probe never succeeded, or very old records) are excluded from hook_due. This is correct — they shouldn't be hook-mined without a publish time. But `mine_video` → `hook_video` path: a video that was `MINED` but has `published_ts=NULL` will never get hooks. This is correct per ruling 80 ("videos published in last 12h") — no publish time means can't determine if in window.

**C5 — Race: `hook_due` + `hook_inflight` check is not atomic (service.py:380-396)**

```python
for v in self.q.hook_due(HOOK_HORIZON_S, HOOK_VIDEOS * 2):
    with self.hlock:
        if v["video_id"] in self.hook_inflight or len(self.hook_inflight) >= HOOK_VIDEOS:
            continue
        self.hook_inflight.add(v["video_id"])
    started.append(self.hooks.submit(self.hook_video, v))
```

Between `hook_due` returning and `hook_inflight` check, another `hook_once` call (from the 5s loop) could claim the same video. The `hlock` protects `hook_inflight` but `hook_due` is called outside the lock. Two concurrent `hook_once` invocations could both get the same video from `hook_due` and both try to add it. The second would be caught by the `in` check — so no double-processing. But there's a TOCTOU where both read `hook_due` simultaneously, both see video X as due, both try to claim it. The lock serializes the `inflight` check, so only one wins. **Not a bug** — the lock is correctly placed.

**C6 — `wlock` does NOT protect against crash between `carry_forward` read and `append` write (service.py:262-271)**

```python
with self.wlock:
    ledger.carry_forward(lines, ledger.video_lines(self.p["ledger"], v["video_id"], since))
    return ledger.append(self.p["ledger"], lines, stamp=config.iso)
```

`wlock` is a `threading.Lock` — it protects against concurrent threads within ONE process. It does NOT protect against:
- A crash between `video_lines` read and `append` write (power loss, OOM kill)
- Two separate processes writing to the same ledger (but `service.lock` prevents two services on same store)

Within single-process, this is correct. The `ledger.append` itself uses `fcntl.flock` for file-level locking. However, `video_lines` reads WITHOUT holding the file lock — it calls `ledger.read()` which does `offset_before` + file read without `flock`. So:

1. Thread A: `video_lines` reads ledger (no flock)
2. Thread B: `append` writes new lines for same video_id (acquires flock, writes, releases)
3. Thread A: `carry_forward` uses stale `earlier` (missing Thread B's lines), then `append` overwrites

This is a **real race condition** — `video_lines` should be read under the same `flock` as `append`. The `wlock` (threading.Lock) prevents this within one process since both operations are under `wlock`. But `video_lines` itself doesn't hold `flock` during read — it just does a plain file read. If another process (e.g., `ab.py` or manual tool) appends concurrently, the read could be torn. Low severity since single-service invariant holds, but the file-level read is not atomic.

**C7 — `contract.eligibility_at_mining` role parameter not validated (contract.py:148-159)**

```python
def eligibility_at_mining(src, registry, k0, k1, now, role="clip"):
```

`role` is passed directly to `E.Context(role=role)` without validation. If `role` is anything other than `"clip"` or `"hook"`, behavior depends on `eligibility.py` — could silently produce wrong eligibility. Currently only called with `"clip"` and `"hook"` via `KINDS[k]["eligibility_role"]`, so safe. But no guard against future misuse.

### 1.3 N+1 Query Problems

**N1 — `hook_due` + per-video `hook_video` does N queries per video (service.py:322-378)**

Each `hook_video` call does:
1. `ts.canonical_transcript(vid)` — file I/O
2. `open(meta.json)` — file I/O  
3. `watch.registry()` — reads `channels.json` from disk
4. `watch.optouts()` — reads `optout.json` from disk
5. `mine.mine_video()` — N window API calls
6. `q.rows("SELECT SUM(cost) ...")` — DB query
7. `q.set_hook()` — DB write

Steps 3-4 are repeated for every video in the batch. With `HOOK_VIDEOS=2` this is 2x redundant file reads per cycle. Not a performance problem at this scale (2 videos per 5s), but wasteful. Same pattern exists in `mine_video` path.

**N2 — `purge.run_pass` calls `published()` per file which may hit DB + file per video (purge.py:356)**

For each media file, `published()` checks `q.video(vid)` (DB query) and potentially `main_store_meta` file. With many files, this is N queries. Mitigated by `cache={}` dict, so each unique `video_id` is queried once. Acceptable.

### 1.4 Edge Cases

| Edge Case | Handling | Verdict |
|-----------|----------|---------|
| Empty DB, no videos | `hook_due` returns `[]`, `mine_due` returns `[]`, loops idle correctly | ✅ |
| API timeout (Heimdall down) | `BackendError("timeout")` → `AllBackendsFailed(outage=True)` → `MINE_WAIT` retry in 10min | ✅ |
| Bad transcript (no sentences) | `windows([])` → `[]` → `jobs=[]` → `lines=[]`, `report windows=0` → `_settle` with `not failed` → `MINED` with 0 moments | ✅ |
| Ledger file doesn't exist | `ledger.read()` returns `([],[])`, `video_lines` returns `[]`, `carry_forward` no-ops | ✅ |
| `published_at` is None/naive | `config.aware()` returns None, `expiry()` returns None, `best_unused_moments` drops with "publish time not measured" | ✅ |
| Hook window has no Bitcoin term | `screened_out` → job not created → no API call, `screened` count incremented | ✅ |
| Duration is None (no timing) | `d = None` → `why = "duration not measured"` → dropped, counted in `report["dropped"]` | ✅ |
| Concurrent hook + mine for same video | Different thread pools (`self.hooks` vs `self.videos`), different `inflight` sets, but same ledger file. `wlock` serializes appends. | ✅ |

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|-----|--------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, re-upload, Shorts/live, durable queue, same store format, bounded concurrency, spend cap, append-only ledger, adapter, daily coverage, blind A/B) | **COMPLIANT** | All components present. `watch.py:175-227` polling, `queue.py:28-61` durable queue, `ledger.py:34-66` append-only, `coverage.py:43-95` daily check, `ab.py:217-333` blind A/B. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** (every role ≥2 back-ends, one interface, no vendor name outside config, local first where it meets bar) | **COMPLIANT** | `providers.json:80-86` all roles have ≥2 back-ends. `providers.py:103-118` validates. `test_providers.py: no_vendor_name_in_code` enforces. `OllamaLocalBackend:441-499` checks `gpu0.held()` never acquires. |
| **L-l Strict schema, nothing repaired** | **COMPLIANT** | `mine.py:272-324` validator rejects extra/missing/duplicate keys, wrong types, out-of-range. `providers.py:845-852` re-asks with rejection reason, never repairs. |
| **L-j/L-m Fail closed, unmeasured ≠ pass** | **COMPLIANT** | `ledger.py:294-323` expired/unmeasured publish time → excluded. `spend.py:118-122` unmeasured spend → `unmeasured` state, never `ok`. `purge.py:298-302` unreadable delivered set → `refused`, nothing deleted. |
| **L-h/L-k Read as spoken, never rewrite** | **COMPLIANT** | `contract.py:115-126` uses `eligibility.spoken()` (entities decoded, split tokens joined). `fetch.py:237` stores via `transcript_store._store()` verbatim. No record rewrite. |
| **L-e Word timing at cut time** | **COMPLIANT** | `contract.py:138-145` caption records have `timing: "segment"`, `duration_s: null`. `mine.py:352-365` sets `duration_s` only for `timing=="word"`. Packager re-anchors at cut time. |
| **L-u Hard exclusions flagged before ranking** | **COMPLIANT** | `mine.py:21-24` HARD_RISKS defined. `ledger.py:304-305` adapter pre-applies hard exclusions. Hook prompt `mine.py:168-172` carries same flag list. `carry_forward` preserves flags. |
| **L-v Speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside` measured (True or None, never False). `fetch.py:186-191,242-247` re-upload detection (title+duration, text fingerprint). `ledger.py:310` re-upload excluded. |
| **L-q Moments first** | **COMPLIANT** | `mine.py:209-227` windows are sentence-id based. `contract.py:106-107` moment_id is `sha256(video_id\|transcript_sha256\|w0\|w1)[:20]`. |
| **L-r GPU0 no GPU use** | **COMPLIANT** | `providers.py:441-499` local backend only when `gpu0.held()` (check, never acquire). `service.py:405-406` releases on idle. No Whisper/Ollama in fetch path. |
| **L-w/L-e Laws applied** | **COMPLIANT** | Per design doc, laws applied as specified. |
| **SPEND FREEZE** (OpenAI/Anthropic/xAI/Google never called, Heimdall→local only, queue on outage, 90% notify never halt) | **COMPLIANT** | `providers.json:5-9` freeze list. `providers.py:692-695` `frozen()` check. `providers.py:758-761` frozen back-ends skipped. `service.py:312-320` outage → `MINE_WAIT` retry, never frontier fallback. `spend.py:151-172` 90% is notify-only. |
| **Secrets (keys by name from env file, never logged)** | **COMPLIANT** | `providers.py:147-188` Keyring reads by name. `providers.py:180-187,208-214` redact in errors. `providers.py:289-291` redirect refused (key never follows). No hardcoded keys. |
| **Ruling 76/77 Expiry 12h, purge** | **COMPLIANT** | `config.py:36-37` EXPIRY_H=12. `ledger.py:238-244` expiry is earlier of recorded + computed. `purge.py:278-396` rolling purge with delivered protection. `purge.json:4-7` targets correct. |
| **Ruling 80 Hook pass** | **PARTIAL** | See detailed analysis below. |

### Ruling 80 Detailed Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Second mining question over same windows | ✅ | `mine.py:249-254` `hook_prompt()` uses same `windows()` + `BTC_SCREEN` |
| Heimdall, cheap | ✅ | `providers.json:83` hook chain is `["heimdall_qwen27b", "local_gemma"]` — same as mine under freeze |
| 1-3 lines per window | ✅ | `mine.py:127` `HOOK_MAX=3`, `HOOK_MAX_SENTENCES=3`, schema enforces `count 1-3` |
| 4-14 seconds | ✅ | `mine.py:128` `HOOK_S=(4.0,14.0)`, `mine.py:430-441` duration filter |
| Sentence start to end, one speaker | ✅ | Prompt says it `mine.py:152-156`, validator enforces sentence ids, `turn_change_inside` measured |
| Understandable alone, concrete/surprising claim | ✅ | Prompt `mine.py:157-159` |
| NOT: greeting, date, ad read, price prediction, accusation | ✅ | Prompt `mine.py:161-166` |
| Judge's 3-part question verbatim | ✅ | `mine.py:129-133` `JUDGE_HOOK_QUESTION`, test `test_mine.py: test_the_hook_question_is_the_builders_judge_question_verbatim` compares with `pp-selectid` source |
| Rows as moments with role_hint hook, same flags | ✅ | `mine.py:345-378` `build_line(kind="hook")` sets `role_hint`, same `RISKS`/`AXES` |
| Adapter returns them like any row | ✅ | `ledger.py:247-326` no role_hint filter — hook rows pass same gates |
| Backfill current 12h window, then watcher loop | ✅ | `service.py:380-396` `hook_once` queries `hook_due(HOOK_HORIZON_S)` newest first, `service.py:540` loop every 5s |
| Report: rows per video, cost | ✅ | `stats.py:108-113` `hooks_12h`, `tools/ingest_watch.py:151-164` `cmd_hooks` |

**PARTIAL reason:** One gap — the hook prompt says "a hook never contains [speaker marker] after its first sentence" (`mine.py:155`) but this is only a prompt instruction, not a validator enforcement. The moment prompt has the same pattern — speaker markers are measured (`turn_change_inside`) but not validated at mining time. The adapter excludes `turn_change_inside==True` (`ledger.py:308-309`), so a hook spanning a speaker change would be mined but never returned. This is by design (measurement, not exclusion at mining time — diarisation is phase 2). Not a violation, but worth noting the hook prompt's "never" is aspirational, not enforced.

---

## SECTION 3: SECURITY

### 3.1 SQL Injection

**All queries use parameterized statements.** Every `self.x()`, `self.rows()`, `self.db.execute()` call uses `?` placeholders:

```python
# queue.py:128 — SAFE
self.x(f"UPDATE channels SET {cols} WHERE channel_id=?", tuple(f.values()) + (cid,))

# queue.py:165-168 — SAFE (from_states are internal constants, not user input)
q = ",".join("?" * len(from_states))
self.db.execute(f"UPDATE videos SET state=?, state_at=? WHERE video_id=? AND state IN ({q})", ...)
```

One dynamic column name construction: `queue.py:127` `f"{k}=?"` where `k` comes from `**f` kwargs — but `set_state` validates against `VIDEO_FIELDS` allowlist (`queue.py:155-157`), and `set_hook` validates against `HOOK_COLUMNS` (`queue.py:186-188`). **No injection possible** — column names are allowlisted.

`coverage.py`, `stats.py`, `purge.py` — all parameterized. No raw string interpolation with user input.

**Verdict: No SQL injection.**

### 3.2 Authentication / Authorization

This is a backend service, not a web app. No HTTP routes, no user sessions. Access control is:
- `config.py:72-79` StoreGuard prevents writing to main tree without explicit env var
- `service.py:104-118` `service.lock` with `flock` prevents two services on same store
- `providers.py:289-291` Redirect refused to prevent key exfiltration

No auth bypass applicable. No user-facing routes to protect.

### 3.3 Rate Limiting

| Resource | Protection | Gap? |
|----------|-----------|------|
| YouTube (yt-dlp) | `YouTubeGate` semaphore (3 concurrent), breaker (10-60min backoff), per-channel backoff | ✅ |
| Heimdall API | `Throttle` per back-end (2s→60s backoff), `Health` circuit breaker, `max_inflight` caps, `SpendBook` daily budget | ✅ |
| Frontier APIs | `daily_budget_usd` per back-end, `SpendBook` | ✅ (frozen anyway) |

**One gap:** No rate limiting on `tools/ingest_watch.py` CLI commands — but these are local operator tools, not user-facing. Acceptable.

**Potential exhaustion:** One operator running `ab.py` + `flagcheck.py` + live watcher simultaneously could exceed `max_inflight=20` on Heimdall. Mitigated: `ab.py:252` and `flagcheck.py:449` set their own `max_inflight` lower (8 and 6), documented as "with the live watcher's own cap: never above ~20 on a shared gateway". Acceptable.

### 3.4 Secrets in Code

- No hardcoded API keys, tokens, or passwords found in any file
- `providers.json` contains only `key_env` / `key_env_prefix` references (names, not values)
- `providers.py:147-188` Keyring reads from env file by name
- `providers.py:180-187,208-214` Redaction in `__repr__` and error messages
- `providers.py:289-291` Redirect handler prevents key following redirect

**One minor concern:** `providers.py:314` sends `Authorization: Bearer <key>` header — the key is in memory during request. No logging of headers. Correct.

**Verdict: No secrets in code.**

### 3.5 Unvalidated Input

| Input | Validation | Verdict |
|-------|-----------|---------|
| YouTube API responses | `fetch.py:96-107` checks `j.get("id") == video_id`, validates duration, live_status | ✅ |
| RSS feed XML | `watch.py:106-118` validates videoId, published date parsing | ✅ |
| Model replies | `mine.py:272-324` strict validator, `flagcheck.py:146-173` strict validator | ✅ |
| `purge.json` spec | `purge.py:53-94` strict validation, refuses bad spec | ✅ |
| `providers.json` | `providers.py:103-128` strict validation | ✅ |
| File paths (purge) | `purge.py:343-345` checks `realpath` inside unit, outside protected, not symlink | ✅ |
| `overrides.json` | `providers.py:135-144` `override_allowed` checks hostname | ✅ |

**No unvalidated input reaching DB/filesystem/shell.**

---

## SECTION 4: FRONTEND QUALITY

**Not applicable.** This is a backend ingest service with no frontend. No HTML, CSS, JS, or UI components. Reports are JSON/Markdown files and CLI output.

The closest to "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` status file — both functional and adequate for an operator tool.

**Score: N/A — no frontend to evaluate.**

---

## SECTION 5: BACKEND QUALITY

### 5.1 DB Operations

| Pattern | Present? | Evidence |
|---------|----------|----------|
| WAL mode | ✅ | `queue.py:81` `PRAGMA journal_mode=WAL` |
| Synchronous FULL | ✅ | `queue.py:82` `PRAGMA synchronous=FULL` |
| Transaction rollback on failure | ⚠️ | `sqlite3` with `isolation_level=None` (autocommit) — each statement is its own transaction. No explicit `BEGIN`/`ROLLBACK`. If `set_state` succeeds but subsequent `event` fails, state is committed without event. Acceptable for this use case (events are audit log, not critical). |
| Connection timeout | ✅ | `queue.py:77` `timeout=30` |
| Thread safety | ✅ | `queue.py:79` `threading.RLock` around all DB access, `check_same_thread=False` |
| Indexes | ✅ | `queue.py:45-48,53-60` indexes on `videos_due`, `videos_channel`, `calls_ts`, etc. |

**Gap:** No `try/except` with rollback around multi-statement operations. E.g., `service.py:294-296` does `_append` (file I/O) then `set_state` (DB write) — if DB write fails after file append, ledger has orphaned lines. Mitigated: `best_unused_moments` deduplicates by `moment_id` (latest wins), and orphaned lines for a video that never reaches `MINED` are simply never returned (no `MINED` state). But they do pollute the ledger file.

### 5.2 External API Calls

| Call | Timeout | Retry | Degradation |
|------|---------|-------|-------------|
| yt-dlp (RSS) | 15s `watch.py:88` | Per-channel backoff `watch.py:205-207` | Falls back to playlist |
| yt-dlp (playlist) | 120s `watch.py:127` | Same | Rate-limit breaker |
| yt-dlp (probe) | 120s `fetch.py:92` | `PROBE_RETRY_S` schedule | `PROBE_RETRY` state |
| yt-dlp (captions) | Via `transcript_store` | `_caption_retry_at` | `CAPTIONS_PENDING` |
| Heimdall API | 240s/300s per back-end | `Throttle` + `Health` breaker + `transport_retries=3` | Outage → `MINE_WAIT`, retry 10min |
| Spend meter | 30s `providers.py:328` | Next cycle (10min) | `unmeasured` state, notify |

All external calls have timeout + retry + graceful degradation. **Excellent.**

### 5.3 Cron / Loop Failure Handling

```python
# service.py:508-517
def _loop(self, name, fn, every, jitter=0.0):
    while not self.stop.is_set():
        t0 = self.clock()
        try:
            fn()
        except Exception as e:
            self.q.event("loop_error", None, None, loop=name, error=traceback.format_exc()[-2000:])
            self.log(f"{name} loop error: {type(e).__name__}: {e}")
        delay = every + (random.uniform(-jitter, jitter) if jitter else 0.0) - (self.clock() - t0)
        self.stop.wait(max(1.0, delay))
```

Every loop catches `Exception`, logs with traceback, and continues. `BaseException` (including `KeyboardInterrupt`, `SystemExit`, GPU0 stop) propagates to allow clean shutdown. **Correct.**

One concern: `fetch.py:204-208` catches `BaseException` in `fetch_once.one()` and re-raises — this would propagate out of `ThreadPoolExecutor.map()` and crash the fetch loop. But `_loop` catches `Exception` only, not `BaseException` — so a `BaseException` in fetch would crash the fetch thread. However, `fetch.process` only raises `BaseException` if `gate.run` does (which it doesn't — it raises `ListError`). And `BaseException` from GPU0 stop only happens in mining path. Low risk.

### 5.4 Memory Leaks

- `ThreadPoolExecutor` with bounded workers (3 video, 2 hook, N window) — no unbounded growth
- `Health.events` deque with `maxlen=50` — bounded
- `SpendBook` — one entry per back-end per day, bounded
- `ledger.read()` — reads entire file into memory. At 100k lines × ~2KB = 200MB. Could be large but `offset_before` bisection mitigates (only reads tail). Acceptable.
- `purge.run_pass` — `glob.glob` could return many files, but bounded by filesystem

**No memory leaks detected.**

### 5.5 Logging

| Context | Logged? | Evidence |
|---------|---------|----------|
| Watch cycle | ✅ | `service.py:182` cycle + channels + new + errors + sources |
| Fetch per video | ✅ | `service.py:210` video_id + channel + state |
| Mine per video | ✅ | `service.py:297,310,320` moments + windows + miners + cost + seconds |
| Hook per video | ✅ | `service.py:359,367` hook rows + windows + cost |
| Purge | ✅ | `service.py:478` freed + kept + delivered |
| Spend meter | ✅ | `service.py:161` state + snapshot |
| Overrides | ✅ | `service.py:153` old→new + refused |
| Outage | ✅ | `service.py:494,500` waiting count + duration |
| Errors | ✅ | `service.py:202,250,374` crash with traceback in events table |

**Excellent logging coverage.** Every state change is also an `events` row in SQLite for post-hoc debugging.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

### What This Gets Right (Genuinely Excellent)

1. **Durability model is exceptional.** WAL SQLite + fsync ledger + flock + crash recovery + idempotent re-mining via reply cache. This is production-grade for a single-node ingest pipeline. Most startups would use Redis + hope.

2. **Spend safety is best-in-class.** Per-vendor freeze, per-back-end daily budgets, gateway spend meter with tripwire, cost tracking per call, reply cache for free retries. The Bloomberg Terminal comparison: Bloomberg would have a similar multi-provider fallback with cost circuit breakers.

3. **Law compliance as code.** Every law has a corresponding test that would fail if violated. `test_no_vendor_name_outside_config`, `test_the_hook_question_is_the_builders_judge_question_verbatim` — this is how you enforce invariants.

4. **Purge safety.** The delivered-set protection with fail-closed on unreadable records is exactly what a professional system needs. The `FORBIDDEN` path list + `realpath` checks prevent catastrophic deletion.

### What's Missing (Material Impact Only)

**G1 — No observability beyond log files.**
Bloomberg/Coinbase would have: structured metrics (Prometheus/Datadog), alerting on coverage drop, p50/p90 latency dashboards, error rate tracking. Currently: `live.json` + `STATE.md` + log files. An operator must manually check these. A coverage drop from 95% to 60% would go unnoticed until someone runs `coverage --hours 24`.

**Impact:** High. Silent degradation in production.

**G2 — No dead-letter queue / manual review for persistently failed videos.**
After `MINE_CONTENT_PASSES=3` rejected passes, a video becomes `mined_partial` and is retried every 6h until 72h. But there's no escalation — no notification that "video X has been failing for 48h, needs human attention." Coinbase would have an alert queue.

**Impact:** Medium. Failed videos silently accumulate as `mined_partial`.

**G3 — Hook quality has no automated validation.**
The hook pass mines hooks but there's no automated check that hooks are actually good openers. The builder's judge scores them, but the miner has no feedback loop. A world-class system would A/B test hook selection and measure downstream engagement (even if just judge scores trending over time).

**Impact:** Medium. Hook quality could degrade without detection.

**G4 — No backpressure on ingest rate.**
If 64 channels each publish 5 videos/hour = 320 videos/hour, the mine path (3 concurrent videos, ~20 windows each, ~5s per window) could fall behind. There's no queue depth monitoring or autoscaling. Bloomberg would have horizontal scaling or priority queuing.

**Impact:** Low at current scale (64 channels, ~10 videos/hour typical). Would matter at 500+ channels.

**G5 — Transcript quality not validated.**
Caption records are stored verbatim with no quality check. Auto-captions with 30% WER would produce garbage moments that waste API spend. A professional system would score transcript quality (e.g., word count vs duration ratio, repetition detection) and skip low-quality transcripts.

**Impact:** Low. YouTube auto-captions are generally good for English. But worth a cheap heuristic.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **82/100** | Core flow is correct. Hook pass well-designed. One real bug (altcoin carry_forward inversion), one race condition (file-level read without flock), N+1 queries minor. Purge fixes are solid. |
| **Frontend/UI** | **N/A** | No frontend. CLI tools are functional. |
| **Error handling** | **88/100** | Every external call has timeout+retry+degradation. Every loop catches and continues. Crash recovery via queue state machine. One gap: multi-statement DB operations without transaction. |
| **Security** | **92/100** | No injection, no hardcoded secrets, proper redaction, redirect refusal, path traversal protection. Minor: no rate limiting on CLI (acceptable for local tool). |
| **Performance** | **78/100** | Bounded concurrency, bisection for ledger reads, overlap optimization for windows. Gaps: N+1 registry reads per video, no backpressure, ledger full-read fallback. Adequate for current scale. |
| **Law compliance** | **94/100** | All laws compliant with test enforcement. Ruling 80 hook pass correctly implements all requirements. One partial: hook speaker-change is prompt-only, not validator-enforced (by design, acceptable). |
| **World-class gap** | **72/100** | Durability and spend safety are world-class. Missing: observability/alerting, dead-letter escalation, hook quality feedback loop. Would impress an engineer, not yet a Bloomberg PM. |
| **OVERALL** | **84/100** | Strong production-ready backend with excellent durability and safety properties. One bug to fix, observability to add, then ship. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | Fix altcoin carry_forward inversion | ledger.py:200 | Missing altcoin flag (None) becomes True via `is not False` check — a hook/moment row could gain a false altcoin exclusion flag, causing valid moments to be incorrectly excluded by adapter
P1 HIGH     | Add flock to video_lines read path | ledger.py:182-184 + service.py:268-271 | File-level race: video_lines reads without flock, concurrent append could cause stale carry_forward — hook row could lose earlier flags if mine+hook race on same video
P1 HIGH     | Add observability: coverage/latency/error alerts | service.py:health_once + new module | Silent degradation — coverage drop, sustained outage, or hook quality regression goes undetected without alerting
P2 MEDIUM   | Cache registry/optout reads per cycle | service.py:mine_video:227-229 + hook_video:333-335 | Redundant file I/O: registry + optout read from disk for every video in batch — cache per watch/mine cycle
P2 MEDIUM   | Add dead-letter notification for persistently failed videos | service.py:_settle:300-310 | Videos stuck as mined_partial for 72h silently — operator has no visibility into chronic failures
P2 MEDIUM   | Validate eligibility role parameter | contract.py:148 | Unvalidated role string passed to eligibility engine — future misuse could silently produce wrong eligibility
P2 MEDIUM   | Wrap multi-statement DB+file operations in transaction | service.py:292-296,301-306 | Ledger append + DB state change not atomic — DB failure after file write leaves orphaned ledger lines
P3 LOW      | Add transcript quality heuristic | fetch.py:_store_captions:205-251 | Low-quality auto-captions waste API spend on garbage moments — cheap WER proxy (words/sec ratio) could skip them
P3 LOW      | Document hook speaker-change as measurement not enforcement | mine.py:155 | Prompt says "never" but validator doesn't enforce — add comment clarifying this is intentional (adapter excludes, not miner)
P3 LOW      | Consider horizontal scaling plan | service.py:85-88 | Single-node with 3+2 concurrency is fine for 64 channels but document scaling strategy for 500+
```

---

## SECTION 9: THE ONE THING

**Fix the `carry_forward` altcoin logic at `ledger.py:200` — a missing flag becoming a false positive exclusion is the kind of silent data corruption that erodes trust in the entire pipeline without anyone noticing.**

---

## SECTION 10: FINAL VERDICT

This code is **ready for production after one fix** (the `ledger.py:200` altcoin inversion — a one-line change from `is not False` to `or`). The architecture is sound, durability is excellent, law compliance is thorough and test-enforced, and the Ruling 80 hook pass is well-designed with proper flag preservation, duration filtering, and retry semantics. The Ruling 77 purge fixes correctly close the fail-open paths. Ship it after the P0 fix, then add observability — that's what will save you at 3 AM when Heimdall goes down and nobody notices for 6 hours.
