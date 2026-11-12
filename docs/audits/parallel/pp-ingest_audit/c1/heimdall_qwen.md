# heimdall_qwen (qwen/qwen3.8-27b, 143.3 s, $0.007, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest

## SECTION 1: CORRECTNESS

**1. Critical Logic Error in `mine_video` (Race/State Loss)**
In `pipeline/ingest/mine.py` (lines 280-281), `mine_video` submits window mining jobs to an executor. However, in `pipeline/ingest/service.py` (line 214), `mine_video` is called via `self.videos.submit(self.mine_video, v)`.
Inside `mine_video` (service.py line 171), it calls `mine.mine_video(...)`.
Look at `mine.mine_video` (mine.py line 280):
```python
futs = {executor.submit(mine_window, ...): (i, w) for i, w in jobs}
```
It uses the `executor` passed in. In `service.py` line 171, `self.executor` is passed.
**The Bug:** `mine.mine_video` returns `lines` and `report`. It does *not* wait for the futures to complete before returning?
Wait, look at `mine.py` line 283: `for f in as_completed(futs):`. It **does** wait.
However, look at `service.py` line 214: `started.append(self.videos.submit(self.mine_video, v))`.
`self.videos` is a `ThreadPoolExecutor(max_workers=3)`.
`self.executor` is a `ThreadPoolExecutor(max_workers=20)` (global max inflight).
This is correct.

**2. `fetch_once` Claiming Logic**
In `service.py` line 144-145:
```python
claimed = [v for v in self.q.due(Q.FETCH_DUE, limit)
           if not self.stop.is_set() and self.q.claim(v["video_id"], (v["state"],), Q.PROBING)]
```
`self.q.due` returns rows. `self.q.claim` performs an atomic update. This is correct.

**3. `watch_once` Concurrency**
In `service.py` line 111-112:
```python
with ThreadPoolExecutor(max_workers=4, thread_name_prefix="list") as ex:
    for r in ex.map(lambda c: watch.poll_channel(self.q, self.gate, c, self.rss_mode), chans):
```
`watch.poll_channel` calls `q.ensure_channel` and `q.channel_update`.
`Queue` uses a `threading.RLock` (queue.py line 73).
SQLite connections are shared (`check_same_thread=False`).
**Risk:** `q.channel_update` (queue.py line 116-119) executes `UPDATE channels SET ...`.
If two threads update the same channel simultaneously (unlikely in `watch_once` as each channel is processed once, but possible if `poll_channel` is called from elsewhere), the RLock serializes them.
However, `watch.poll_channel` also calls `q.add_video` (queue.py line 127).
`add_video` uses `INSERT OR IGNORE`.
**Issue:** `poll_channel` (watch.py line 171) reads `row = q.channel(cid)` (line 175). Then later updates `q.channel_update(cid, ...)` (line 201, 219).
Between read and write, another thread *could* modify the channel row.
In `watch_once`, each channel is unique in the list `chans`. So no two threads touch the same `cid` in `watch_once`.
However, `fetch_once` (service.py line 124) also touches channels? No, it touches videos.
`coverage.check` (coverage.py line 37) calls `watch.rss_canary` and `watch.playlist_list`. It does not write to the queue.
So `watch_once` is the only writer to `channels` table concurrently. Since each channel is processed by exactly one thread in the map, there is no race on the same channel ID.

**4. `mine_video` State Transition**
In `service.py` line 183-187:
```python
ledger.append(self.p["ledger"], lines)
st = Q.MINED_PARTIAL if rep["failed"] else Q.MINED
self.q.set_state(vid, st, ...)
```
If `ledger.append` succeeds but `set_state` fails (e.g., DB lock timeout), the video remains in `MINING` state.
On restart, `recover()` (queue.py line 168) moves `MINING` -> `TRANSCRIBED`.
Then `mine_once` will pick it up again.
`mine_video` will re-mine.
`mine_window` uses `use_cache=True` (mine.py line 232).
The cache key is `sha256(prompt, schema, max_tokens)`.
If the prompt is identical, the cached reply is used.
So re-mining is cheap.
**However:** `ledger.append` is append-only. If the video was already partially appended (crash mid-append?), `seal()` handles torn lines.
But if `ledger.append` succeeded for *all* lines, and then `set_state` failed, the next run will append *again*?
No, `mine_video` builds `lines` fresh.
If the video is re-mined, `lines` will contain the same moments.
`ledger.append` will add duplicate lines.
`best_unused_moments` (ledger.py line 143) deduplicates by `moment_id` (line 157: `latest[l["moment_id"]] = l`).
So duplicates are handled by the reader.
**Verdict:** Correct, but inefficient (duplicate writes).

**5. `fetch.process` Duplicate Detection**
In `fetch.py` line 179: `dup, why = q.find_duplicate(vid, title_canon=tc, duration=dur)`.
`find_duplicate` (queue.py line 176) checks `text_fp` first, then `title_canon` + `duration`.
In `fetch.py` line 179, `text_fp` is not passed (it's `None`).
So it only checks title/duration.
Later, in `_store_captions` (fetch.py line 227), `text_fp` is calculated and `find_duplicate` is called again with `text_fp`.
This is correct: title/duration is a cheap pre-check; text fingerprint is the definitive check.

**6. `providers.Router.run` Cache Logic**
In `providers.py` line 599-603:
```python
if use_cache and self.backends[bid].enabled():
    out = self._cached(...)
    if out is not None:
        return out
```
If the cache hit is invalid (validator fails), `_cached` returns `None` (line 628).
Then it proceeds to `self.available(bid)` and `self._try`.
This is correct.

**7. `spend.HeimdallMeter.measure`**
In `spend.py` line 35-52.
It calls `self.backend.get_json("/credits")`.
`OpenAICompatBackend.get_json` (providers.py line 243) calls `self._request(path, timeout=timeout)`.
`_request` (providers.py line 226) uses `urllib.request.urlopen`.
If the network fails, it raises `BackendError`.
`measure` catches `Exception` (line 42) and sets `last_error`.
This is correct.

**8. `watch.rss_list`**
In `watch.py` line 83-113.
It uses `urllib.request.urlopen`.
If `e.code == 304`, it returns `not_modified`.
If `e.code == 404`, it raises `ListError`.
This is correct.

**9. `contract.fingerprint`**
In `contract.py` line 84-99.
It imports `sentence_law` and `config.ts()`.
`config.ts()` binds `transcript_store`.
If `transcript_store` is not available, it raises `StoreGuard`.
`fingerprint` is called in `mine.build_line` (mine.py line 261).
If `fingerprint` fails, `build_line` fails, `mine_video` fails, video goes to `MINE_WAIT`.
This is fail-closed. Correct.

**10. `ledger.best_unused_moments`**
In `ledger.py` line 143-205.
It reads the ledger file.
It filters by `mined_at >= since` or `published_at >= now - 72h`.
It deduplicates by `moment_id`.
It applies exclusions.
It sorts by `rank_score`.
This is correct.

**11. `coverage.check`**
In `coverage.py` line 37-85.
It lists channels independently.
It matches videos to the queue.
It reports mined/missed.
This is correct.

**12. `ab.main`**
In `ab.py` line 201-292.
It selects videos, runs mining on each backend, then runs the judge.
It uses `router.run` with `only=b` for generation.
It uses `router.run` with `only=judge` for judging.
This is correct.

**13. `tools/ingest_watch.py`**
`cmd_run` starts the service.
`cmd_once` runs one pass.
`cmd_status` prints stats.
`cmd_coverage` runs coverage.
`cmd_moments` prints best unused moments.
`cmd_handoff` copies files.
`cmd_ab` runs A/B.
This is correct.

**14. Potential Issue: `mine_video` in `service.py`**
Line 171: `lines, rep = mine.mine_video(self.router, self.executor, rec, meta, chan, reg, datetime.now(timezone.utc), self.cycle, extra_source=src)`
`mine.mine_video` (mine.py line 268) takes `now_dt`.
It uses `now_dt` in `build_line` (mine.py line 257: `contract.eligibility_at_mining(src, registry, a, b, now_dt)`).
`eligibility_at_mining` (contract.py line 144) uses `now` in `E.Context(now=now, ...)`.
This is correct.

**15. Potential Issue: `fetch.process`**
Line 144: `pub, pub_src = publish_time(j, rss_published=rss_pub)`
`publish_time` (fetch.py line 30) returns `(iso, source)`.
Line 145: `pub_ts = datetime.fromisoformat(pub).timestamp() if pub else None`
If `pub` is `None`, `pub_ts` is `None`.
Line 161: `if pub_ts is None:` -> `PROBE_RETRY`.
This is correct.

**16. Potential Issue: `watch.poll_channel`**
Line 209: `old = first_sight and ts_ is not None and now_ts - float(ts_) > backfill_h * 3600`
If `ts_` is `None` (e.g., from RSS where `published` is parsed but `ts` is not set? No, RSS sets `ts` in `poll_channel` line 189).
In `playlist_list`, `ts` is `e.get("timestamp")`.
If `ts` is `None`, `old` is `False`.
This is correct.

**17. Potential Issue: `providers.Throttle.wait`**
Line 495-501.
It loops while `left > 0`.
It sleeps `min(left, 5.0)`.
This is correct.

**18. Potential Issue: `providers.Health.record`**
Line 449-473.
It updates `consec`, `events`.
It checks failure rules.
This is correct.

**19. Potential Issue: `queue.Queue.due`**
Line 162-166.
It queries `videos` where `state IN (...)` and `next_at <= ?`.
It orders by `published_ts` DESC.
This is correct.

**20. Potential Issue: `stats.live`**
Line 19-88.
It queries `videos` and `calls`.
It calculates metrics.
This is correct.

**Conclusion on Correctness:**
The code is largely correct. The main concern is the **duplicate ledger writes** if `set_state` fails after `ledger.append`. This is mitigated by the deduplication in `best_unused_moments`, but it is not ideal.
Another concern is the **lack of a transaction** around `ledger.append` and `set_state`. If the process crashes between them, the video is re-mined and re-appended. This is acceptable given the deduplication.

## SECTION 2: LAW COMPLIANCE

**L-x NO SINGLE MODEL, ULTRON FIRST:**
- `providers.json` defines roles with chains of >= 2 backends.
- `local_gemma` is first in the `mine` chain but `enabled: false`.
- `Router.run` tries the chain in order.
- **Compliant.**

**L-l a model reply counts only whole:**
- `mine.validator` (mine.py line 167) strictly validates the JSON.
- `Invalid` is raised for any defect.
- `Router._try` (providers.py line 636) catches `Invalid` and retries with the reason.
- **Compliant.**

**L-j / L-m: fail closed; nothing measured is never a pass:**
- `spend.HeimdallMeter.state` (spend.py line 62) returns `unmeasured` if no recent reading.
- `Router.available` (providers.py line 565) checks `meter.state()`. If `unmeasured`, it returns `False` (skips the backend).
- `coverage.check` (coverage.py line 55) marks channels as `unmeasured` if listing fails.
- **Compliant.**

**L-h / L-k: transcript text is read as spoken:**
- `contract.sentences` (contract.py line 111) uses `eligibility.spoken`.
- `mine.prompt` (mine.py line 153) uses `s['text']` which is from `contract.sentences`.
- **Compliant.**

**L-e: word timing for anything heard:**
- `contract.source_for` (contract.py line 134) sets `timing` from `record_tokens`.
- `mine.build_line` (mine.py line 249) sets `timing` in the moment line.
- **Compliant.**

**L-u hard exclusions:**
- `mine.HARD_RISKS` (mine.py line 23) defines the risks.
- `ledger.best_unused_moments` (ledger.py line 183) drops moments with hard risks.
- **Compliant.**

**L-v: a moment never spans a speaker change:**
- `contract.turn_change_inside` (contract.py line 125) checks for `>>` markers.
- `mine.build_line` (mine.py line 253) sets `speaker.turn_change_inside`.
- `ledger.best_unused_moments` (ledger.py line 187) drops moments with `turn_change_inside == True`.
- **Compliant.**

**Secrets:**
- `providers.Keyring` (providers.py line 98) reads keys from an env file.
- Keys are never logged.
- **Compliant.**

**Verdict:** All laws are compliant.

## SECTION 3: SECURITY

**SQL Injection:**
- `queue.Queue` uses parameterized queries (`?`).
- No raw SQL string concatenation with user input.
- **Safe.**

**Authentication Bypasses:**
- No web server.
- **N/A.**

**Rate Limiting Gaps:**
- `YouTubeGate` (watch.py line 35) limits yt-dlp processes.
- `Router` (providers.py line 543) limits in-flight requests per backend and globally.
- **Safe.**

**Secrets in Code:**
- `providers.json` contains `key_env` names, not values.
- `Keyring` reads values from a file.
- **Safe.**

**Unvalidated User Input:**
- `tools/ingest_watch.py` accepts arguments.
- `ab.main` accepts `--backends`, `--judge`, etc.
- These are used to select backends from `providers.json`.
- If an invalid backend is specified, `Router.run` will raise `AllBackendsFailed` or skip it.
- **Safe.**

**Verdict:** No security issues found.

## SECTION 4: FRONTEND QUALITY

**N/A:** This is a backend service. No UI.

## SECTION 5: BACKEND QUALITY

**DB Operations:**
- `queue.Queue` uses `sqlite3` with `WAL` mode.
- `isolation_level=None` (autocommit).
- `PRAGMA synchronous=FULL`.
- **Good.**

**External API Calls:**
- `urllib.request` with timeouts.
- `yt-dlp` subprocess with timeouts.
- **Good.**

**Cron Job:**
- Not a cron job. Long-running process.
- **N/A.**

**Memory Leaks:**
- `ThreadPoolExecutor` is used.
- `deque` for health events.
- **Good.**

**Logging:**
- `service._log` writes to stdout and a file.
- `queue.event` records state changes.
- **Good.**

**Verdict:** High quality backend.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

1. **Duplicate Ledger Writes:** As noted, if `set_state` fails after `ledger.append`, the video is re-mined and re-appended. This is mitigated by deduplication, but it is not ideal. A transaction or a "pending" state would be better.
2. **Lack of Metrics Export:** The service writes `live.json`, but does not export metrics to Prometheus or similar. This is a gap for observability.
3. **No Health Check Endpoint:** The service does not expose a health check endpoint. This is a gap for container orchestration.
4. **No Graceful Shutdown of yt-dlp:** `YouTubeGate.run` (watch.py line 57) does not kill the yt-dlp process if it hangs. It relies on the timeout. This is acceptable, but a kill switch would be better.
5. **No Retry for `ledger.append`:** If `ledger.append` fails (e.g., disk full), the video is not marked as mined. It will be re-mined. This is acceptable, but a retry with backoff would be better.

**Verdict:** The code is production-ready, but lacks some observability and resilience features.

## SECTION 7: SCORES

- Backend logic: 95/100
- Frontend/UI: N/A
- Error handling: 90/100
- Security: 95/100
- Performance: 90/100
- Law compliance: 100/100
- World-class gap: 85/100
- OVERALL: 92/100

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | Add a "pending" state for videos that have been appended to the ledger but not yet marked as mined | `pipeline/ingest/service.py:183` | Prevents duplicate ledger writes if `set_state` fails.
P2 MEDIUM | Export metrics to Prometheus | `pipeline/ingest/stats.py` | Improves observability.
P2 MEDIUM | Add a health check endpoint | `pipeline/ingest/service.py` | Improves container orchestration.
P3 LOW | Kill yt-dlp process if it hangs | `pipeline/ingest/watch.py:57` | Improves resilience.

## SECTION 9: THE ONE THING

Add a "pending" state for videos that have been appended to the ledger but not yet marked as mined, to prevent duplicate ledger writes.

## SECTION 10: FINAL VERDICT

This code is ready for production. It is well-structured, compliant with all laws, and secure. The main gap is the lack of a "pending" state for videos that have been appended to the ledger but not yet marked as mined, which can lead to duplicate ledger writes. This should be fixed before deployment.