# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 789.8 s, $0.026, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest

**Auditor stance:** No ego, no padding. Every claim cites `file:line` from the diff provided. Where the spec says "all new files" I treat the working-tree content as the source of truth.

---

### SECTION 1: CORRECTNESS

#### 1.1 Main flow walk-through

**Watch → Fetch → Mine → Ledger → Coverage** is coherent and the state machine is well-designed. The happy path works. The failure paths are where it breaks.

**WATCH (`watch.py:176-228`):**
- `poll_channel` correctly handles RSS→playlist fallback, backoff, `first_sight` backfill, Short detection via `/shorts/` URL. Logic is sound.
- **BUG — `watch.py:216`:** `"/shorts/" in (e.get("url") or "")` is the *only* Short detector in the watcher. YouTube playlist entries for Shorts do not always contain `/shorts/` in `url` — they often appear as `https://www.youtube.com/watch?v=...` with `duration < 60` and `live_status=None`. The `fetch.py:157` check `media == "short"` is the authoritative one, but `watch.py` will misclassify Shorts as `DISCOVERED` and waste a probe cycle. Not fatal, but wasteful and the coverage report will briefly miscount them.
- **BUG — `watch.py:221-223`:** `newest_published` tracking uses `p > newest` string comparison on ISO timestamps. This works only if all timestamps are in the same format (they are, but it's fragile — a `Z` vs `+00:00` suffix would break ordering).

**FETCH (`fetch.py:120-244`):**
- `process()` correctly handles opt-out, channel mismatch, upcoming/live, duration, duplicate, captions. The `_store_captions` path correctly uses `transcript_store`'s own writer.
- **BUG — `fetch.py:150-151`:** `rss_pub` is derived from `v.get("listing_ts")` only when `discovered_via == "rss"`. But `listing_ts` for RSS entries is set from `watch.py:194` as `_parse_iso(e["published"]).timestamp()` — correct. For playlist entries, `listing_ts` is `e.get("ts")` which is `approximate_date` — explicitly documented as approximate. `publish_time()` then prefers `rss_published` over `timestamp`, which is correct for RSS. No bug here, but the `approximate_date` path means `published_at` for playlist-discovered videos can be off by hours. This is documented as `INGEST-FAIL-02` tradeoff, acceptable.
- **BUG — `fetch.py:173-176`:** `BACKFILL_H * 3600` check uses `now_ts - pub_ts > BACKFILL_H * 3600`. If `pub_ts` is in the future (clock skew, YouTube scheduling quirk), `now_ts - pub_ts` is negative, so the check passes and the video is *not* marked `SEEN_OLD`. It proceeds to mining. A future-dated video should be handled explicitly. Minor.
- **CORRECT FIX — `fetch.py:103-104`:** Age-gate detection now correctly checks `AGE_GATE_MARKS` before `UNAVAILABLE_MARKS`, fixing B4. Verified: `watch.py:24` `AGE_GATE_MARKS` no longer overlaps with `RATE_LIMIT_MARKS`.

**MINE (`mine.py:275-320`):**
- Windowing, screening, parallel execution, flag union logic all correct.
- **BUG — `mine.py:304-315`:** When a range appears in two overlapping windows, the second observation's `scores` and `reason` are silently discarded (only `risk`, `names_person`, `flags_ext` are merged). The docstring says "scores and reason are the first's" — this is intentional but means the *better* scoring observation could be lost. If window 1 scores a moment 2/5 and window 2 scores it 5/5, the 2/5 is kept. This is a quality bug, not a correctness bug, but it should use `max` or `rank_score` to pick the better observation.
- **BUG — `mine.py:160-164`:** `prompt()` uses `mine._untrusted()` to escape `<` → `‹`. This prevents `</sentences>` injection. **But** `watch.py` channel names and `fetch.py` titles are also passed through `_untrusted` — good. However, `mine.py:153-156` notes "0 of 410,156 caption segments contain `<`" — this is an empirical claim that could silently break if YouTube captions ever contain `<` (e.g., math content: `a < b`). The replacement is lossy but safe. Acceptable tradeoff.

**LEDGER (`ledger.py:29-75`):**
- `append()` now validates every line before writing (fixing the audit's "no validation" finding). Torn-tail handling is correct: `os.pread` check + `b"\n"` prepend under `flock`.
- **BUG — `ledger.py:44-45`:** The torn-tail fix prepends `b"\n"` to `data` (the *new* data), not to the file. This means if the file ends with `...{"foo": "bar` (no newline, torn), the new write becomes `\n{"new": "line"}\n` — the torn line `{"foo": "bar` remains torn (no trailing newline) and the new line starts correctly on the next line. On the *next* read, the torn line is still unparseable and counted as `bad`. This is actually correct behavior per the docstring ("a torn line stays one unreadable line"). But the comment says "closed, so the first new line stays whole" — the torn line itself is never repaired, just isolated. This is fine but the comment is slightly misleading.
- **BUG — `ledger.py:66-74`:** `seal()` opens with `O_WRONLY | O_APPEND` but does NOT use `O_RDWR`, so `os.pread` is not available. It uses `open(path, "rb")` + `seek(-1)` instead — correct for `seal()`. No bug.
- **BUG — `ledger.py:110-135`:** `offset_before()` bisection assumes `mined.at` ordering. The docstring correctly notes concurrent videos interleave by "at most one pass (minutes)" and callers pass "a day of margin." The `cutoff` in `best_unused_moments` is `min(since, now - 72h) - 1 day` — so 1 day margin. If the system was down for >1 day and then catches up with many videos, interleaving could exceed 1 day. Extremely unlikely in practice. Acceptable.

**SERVICE (`service.py:45-362`):**
- **CORRECT FIX — `service.py:85-99`:** `ServiceBusy` + `flock` on `service.lock` fixes the "no single-instance guard" finding. Verified: `_hold_store()` is called before `q.recover()`, so `once` beside `run` is correctly refused.
- **CORRECT FIX — `service.py:237-275`:** `_settle()` correctly distinguishes `OUTAGE` (no try used, `MINE_RETRY_S`) vs `REJECTED` (try used, `MINE_CONTENT_PASSES=3` then `MINED_PARTIAL`). This fixes B2.
- **BUG — `service.py:257-258`:** `if not was_partial or len(failed) < int(v.get("windows_failed") or 10 ** 6)` — when `was_partial` is True and `windows_failed` is 0 (all windows now succeed on retry), `len(failed)` is 0, `v.get("windows_failed")` is the *previous* failure count (e.g., 2), so `0 < 2` is True and `ledger.append` is called. Correct — it appends the now-complete lines. But if `was_partial` is True and the retry *also* has failures (e.g., 1 failed window, previously 2 failed), `1 < 2` is True, so it appends again. The "latest line wins" dedup in `best_unused_moments` handles this, but it means the ledger accumulates duplicate `moment_id` lines with different `mined.at` — the adapter correctly keeps the latest. No data loss, but ledger grows with duplicates. Acceptable per spec.
- **BUG — `service.py:260`:** `nxt = now + MINE_PARTIAL_RETRY_S if now < float(pub) + MINE_HORIZON_S else now + 10 ** 9` — if `pub` is None (no `published_ts`), it falls back to `discovered_ts`, then `now`. If all are None, `pub = now`, so `now < now + 72h` is True, so it retries every 6h forever. A video with no publish time should not be retried forever. Minor — `fetch.py:169-172` already handles `pub_ts is None` as `PROBE_RETRY`, so this path should rarely have `pub is None`.
- **BUG — `service.py:277-295`:** `mine_once()` checks `free == 3 and not self.q.due(Q.MINE_DUE, 1)` to decide to `release()` the local model. But `due()` checks `next_at <= clock()`. If a `MINE_WAIT` video has `next_at` in the future (10 min retry), `due()` returns empty, so `release()` is called even though there's a video waiting to be retried. The local model is unloaded and will need to be reloaded when the retry fires. This is wasteful but not incorrect — `LocalLLM.start()` will reload it. The `release()` is an optimization, not a correctness issue.

**COVERAGE (`coverage.py:42-94`):**
- **CORRECT FIX — `coverage.py:78`:** Now `if state == Q.MINED` (not `Q.MINED_PARTIAL`), fixing B2's "counts partial as mined." Verified.
- **BUG — `coverage.py:67`:** `pts = (v or {}).get("published_ts") or e.get("ts")` — for RSS listings, `e.get("ts")` is the parsed `published` timestamp (correct). For playlist listings, it's `approximate_date` (approximate). The `now_ts - hours * 3600 <= float(pts) <= now_ts + 600` window check uses this approximate time, so a video published 25h ago but with `approximate_date` off by 2h could be incorrectly included/excluded from the 24h coverage window. Acceptable given the `approximate_date` limitation.

**PROVIDERS (`providers.py:1-848`):**
- **CORRECT FIX — `providers.py:671-673`:** `frozen()` correctly checks `spend_freeze.vendors` and fail-closes on `None` vendor. `available()` checks `frozen()` first. `run()` uses `order()` which moves metered backends last. This fixes B1 (tripwire no longer halts Heimdall — it deprioritizes it).
- **CORRECT FIX — `providers.py:279-284`:** `_NoRedirect` handler prevents bearer key following redirects. `override_allowed()` restricts override URLs to localhost or configured host. Fixes the "any URL" finding.
- **CORRECT FIX — `providers.py:175-182`:** `Keyring.redact()` + `providers.py:794-796` redaction of error text before recording. Fixes key-in-error-text finding.
- **BUG — `providers.py:740-743`:** `except BaseException: self.health[bid].record(False, None, "crash"); raise` — this catches `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` in addition to GPU0 stops. If the process receives SIGINT during a provider call, it will record a health failure before propagating the interrupt. This is slightly wrong — `KeyboardInterrupt` should not count as a backend failure. Should be `except BaseException as e: if isinstance(e, (KeyboardInterrupt, SystemExit)): raise; self.health[bid].record(...); raise`.
- **BUG — `providers.py:818-825`:** `except Exception as e` catches validator crashes and treats them as `Invalid` (rejected). But `json.loads` can raise `RecursionError` (a `RecursionError` is an `Exception` subclass in Python 3.10+ — actually it's a `RuntimeError` subclass... let me check: `RecursionError` inherits from `RuntimeError` which inherits from `Exception` — yes, it IS caught). So deeply nested JSON that causes `RecursionError` would be treated as "invalid" and retried with the rejection prompt, rather than being treated as a system error. This is actually fine — the retry will also fail, and after 3 attempts it's marked `rejected`. Not a real bug.
- **BUG — `providers.py:804-807`:** `transport_left` retries on `RETRY` kinds with `self.sleep(min(2.0 * (4 - transport_left), 10.0))`. But `transport_left` starts at `throttle["transport_retries"]` (3) and decrements. First retry: `min(2.0 * 1, 10.0) = 2.0s`. Second: `min(2.0 * 2, 10.0) = 4.0s`. Third: `min(2.0 * 3, 10.0) = 6.0s`. This is linear backoff, not exponential. The `Throttle.hit()` does exponential backoff for 429/overloaded, but transport retries use linear. Not a bug, just inconsistent with the docstring's "2^n" claim for channel backoff (which is in `watch.py`, not here).

#### 1.2 Race conditions

- **FIXED:** `queue.py:154-160` `claim()` uses atomic `UPDATE ... WHERE state IN (...)` with `rowcount == 1` check. Two concurrent `fetch_once` or `mine_once` callers cannot claim the same video. Correct.
- **FIXED:** `service.py:85-99` file lock prevents two `Service` instances on the same store. Correct.
- **REMAINING — `queue.py:71-77`:** `Queue.__init__` sets `check_same_thread=False` with a single `self.db` connection behind `self.lock` (RLock). This is correct for multi-threaded access — all callers go through `self.lock`. However, `sqlite3` with `check_same_thread=False` and WAL mode can still hit `SQLITE_BUSY` if a long-running `SELECT` holds a read lock while another thread tries to `INSERT`. The `timeout=30` handles this with retries. Acceptable.
- **REMAINING — `ledger.py:39-55`:** `append()` uses `fcntl.flock(LOCK_EX)` + `os.fsync`. This is correct for inter-process exclusion. But `service.py` runs `mine_video` in `self.videos` (3 threads) and each calls `ledger.append` — the `flock` serializes them. Correct. However, `coverage.py:write()` and `stats.py:write_live()` write to different files, no conflict.

#### 1.3 N+1 queries

- **FOUND — `service.py:217`:** `self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=?", (vid,))` is executed once per `mine_video` call. With 3 concurrent videos, this is 3 queries — not N+1 in the classic sense, but it queries `calls` without an index on `video_id`. Check `queue.py:49-52`: `calls` has `CREATE INDEX calls_ts ON calls(ts)` but NO index on `video_id`. As `calls` grows (thousands of rows per day), this `SUM WHERE video_id=?` will do a full table scan. **Add `CREATE INDEX calls_video ON calls(video_id)`.**
- **FOUND — `stats.py:82-83`:** `SELECT backend, SUM(COALESCE(cost_usd,0)) AS usd FROM calls GROUP BY backend` — full table scan on `calls` every 60s (health loop). With no index on `backend`, this scans all rows. Acceptable for now (calls table is small — ~100 rows/day), but will degrade over months. Should add index or use a materialized daily summary.
- **FOUND — `coverage.py:65`:** `q.video(e["video_id"])` inside `for e in ents` loop — one `SELECT * FROM videos WHERE video_id=?` per video in the coverage listing. With 64 channels × 30 videos = ~1920 lookups per coverage check. Each is a primary key lookup (indexed), so it's fast. Not a real N+1 problem.

#### 1.4 Edge cases

| Edge case | Handled? | Location |
|-----------|----------|----------|
| Empty DB (no videos) | Yes | `stats.py:25` `min([...] or [now_ts])`, `coverage.py:92` `None if not rep["eligible"]` |
| API timeout | Yes | `providers.py:312-313` `BackendError("timeout")`, `watch.py:59-73` `YouTubeGate` breaker |
| Bad input (malformed JSON from yt-dlp) | Yes | `watch.py:132-136` `ListError("playlist_unreadable")`, `fetch.py:96-107` fallback |
| No English captions | Yes | `fetch.py:192-201` `CAPTIONS_PENDING` → `NO_CAPTIONS` after 48h |
| Channel deleted / renamed | Yes | `fetch.py:146-149` channel mismatch → `UNAVAILABLE` |
| Disk full (ENOSPC) | Partial | `ledger.py:39-55` torn-tail handling; but `queue.py` SQLite writes have no ENOSPC handling — will raise `sqlite3.OperationalError` and crash the loop (caught by `service.py:324-326` `loop_error` event, loop continues) |
| `transcript_store` missing | Yes | `config.py:93-95` `StoreGuard` |
| `channels.json` missing | No | `watch.py:151` `open(config.REGISTRY_PATH)` — unhandled `FileNotFoundError` crashes `watch_once` (caught by `service.py:324` loop_error, but watch cycle is lost) |

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest** | **COMPLIANT** | `watch.py:176-228` RSS first + playlist fallback, `config.py:25-26` 600s±60s poll, `queue.py:29-33` last-seen ledger, `fetch.py:176-191` re-upload detection, `watch.py:216-217` Shorts handling, `fetch.py:160-168` live/upcoming, `queue.py:68-77` durable SQLite WAL |
| **L-x: NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:60-63` two roles with ≥2 backends each, `providers.py:645-748` `Router` with chain fallback, `providers.py:431-483` `OllamaLocalBackend` with `gpu0.held()` check (not env string), `providers.py:103-118` `validate_config` enforces vendor names, `ab.py:217-333` blind A/B harness |
| **L-l: reply counts only whole** | **COMPLIANT** | `mine.py:174-223` strict `validator()` — rejects extra/missing/duplicate keys, non-integer ids, unoffered ids, count outside 1-5, duplicate ranges, bad scores, unknown risks, over-long reasons, >6 moments, markdown fences. `providers.py:818-826` never repairs, re-asks with quoted reason. `ledger.py:29-36` validates before writing |
| **L-j/L-m: fail closed** | **COMPLIANT** | `ledger.py:194-211` unreadable optout → `ValueError` refuses read, `spend.py:73-77` unmeasured → `tripped` (never below threshold), `coverage.py:60-62` unmeasured channels never counted as covered, `providers.py:671-673` `frozen()` fail-closes on `None` vendor |
| **L-h/L-k: read as spoken** | **COMPLIANT** | `contract.py:115-126` `sentences()` uses `eligibility.spoken` + `select_by_id.tokens_from_record`, `fetch.py:77-86` `text_fingerprint` uses `canon.canon_tokens(ts.read_text(...))`, `contract.py:88-103` fingerprint includes `ts.read_text` source |
| **L-e: word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `source_for()` passes `timing` through, `mine.py:242-272` `build_line` sets `duration_s: None` when `timing != "word"`, `duration_estimate_s` flagged, packager re-anchors at cut time per spec |
| **L-u: hard exclusions** | **COMPLIANT** | `mine.py:23-24` `HARD_RISKS` defined, `ledger.py:247-248` `any(r in HARD_RISKS for r in l["risk"])` → excluded, `mine.py:304-314` overlapping window flag union (fail closed — union of risks) |
| **L-v: speaker/re-upload/time** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside` measured (True/null, never false without measurement), `ledger.py:251-252` `turn_change_inside is True` → excluded, `fetch.py:186-191,234-240` re-upload detection (title+duration, text fingerprint), `mine.py:242-272` `published_at` carried in moment |
| **L-r: GPU0 no GPU here** | **COMPLIANT** | `providers.py:431-483` local backend requires `gpu0.held()` (real lease check, not env string), `service.py:284` `release()` unloads on idle, `ab.py:325` `release()` at end of A/B run. No Whisper/Ollama/NVENC in ingest path |
| **L-w/L-q: moments first** | **COMPLIANT** | `mine.py:29-31` `BTC_SCREEN` pre-filter, `mine.py:275-320` moments mined before any ranking, `ledger.py:194-269` adapter serves moments |
| **Secrets** | **COMPLIANT** | `providers.py:142-182` `Keyring` reads by name from env file, `providers.py:175-182,794-796` redaction before recording, `providers.py:279-284` redirect refusal, no hardcoded keys found |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:5-9` `spend_freeze.vendors` lists 4 vendors, `providers.py:671-673` `frozen()` blocks all roles, `providers.py:678-684` `order()` deprioritizes (never halts), `ab.py:262-264,287-291` A/B respects freeze, `service.py:336-340` logs freeze status |

**All laws: COMPLIANT.** No violations. The B1-B4 blocking findings from the integrator audit are all addressed.

---

### SECTION 3: SECURITY

#### SQL injection — **PASS (no vulnerability)**

All queries use parameterized `?` placeholders:
- `queue.py:82-83` `self.db.execute(sql, args)` — callers pass `?` + tuple
- `queue.py:118-119` `f"UPDATE channels SET {cols} WHERE channel_id=?"` — `cols` is built from `f.keys()` where `f` is `**f` kwargs from internal callers (`channel_update`, `set_state`). `VIDEO_FIELDS` whitelist at `queue.py:61-64` validates `set_state` keys. `channel_update` at `queue.py:116-119` has NO whitelist — but it's only called from `watch.py:206,224` with hardcoded column names (`last_poll_at`, `consecutive_errors`, etc.), never user input. **No injection vector.**
- `queue.py:156-159` `",".join("?" * len(from_states))` — parameterized, safe.

#### Authentication bypasses — **N/A (no auth layer)**

This is a backend ingest service with no HTTP routes. No auth to bypass. The `service.lock` file lock is the access control — one service per store.

#### Rate limiting gaps — **PASS with notes**

- `providers.py:587-615` `Throttle` with queue-aware backoff on 429/overloaded, `Retry-After` honoured, shared across threads. Correct.
- `watch.py:37-73` `YouTubeGate` with global breaker (10→20→40→60 min) and per-channel backoff. Correct.
- `providers.py:657-659` per-backend `max_inflight` + global `max_inflight=20` via semaphores. Correct.
- **GAP — `providers.py:697-699`:** `daily_budget_usd` is checked in `available()` but there's no cross-process budget sharing. If two `Service` instances somehow run on different stores sharing the same API key, they each track spend independently and could double-spend. Mitigated by `ServiceBusy` lock (one service per store), but different stores with same key would still double-spend. Low risk.

#### Secrets in code — **PASS**

- No hardcoded API keys, tokens, or passwords found in any file.
- `providers.json:10` `env_file` points to `/home/ultron/protocol_pulse/.env` — keys read by name at runtime.
- `providers.py:175-182` `redact()` replaces key values in error text before persistence. Verified: `providers.py:794-796` calls `redact` on `r.detail` and `r.raw`.
- **NOTE:** `providers.json` itself contains no secrets — only `key_env` names and `base_url` values. Correct.

#### Unvalidated input reaching DB/filesystem/shell — **PASS with one flag**

- **DB:** All user-influenced data (video titles, channel names) goes through parameterized queries. Safe.
- **Filesystem:** `config.py:50-51` `store_root()` from `PP_INGEST_STORE` env var → `os.path.realpath` → `check_store()` guard. `fetch.py:209` `ts._vdir(vid)` — `vid` is YouTube video ID (alphanumeric, 11 chars), safe. `ledger.py:38` `os.path.dirname(path)` — `path` from `config.paths()["ledger"]`, safe.
- **Shell:** `watch.py:67` `config.ts()._ytdlp(args, timeout=timeout)` — `args` are hardcoded lists like `["-J", "--flat-playlist", ...]` plus `uploads_url(cid)` where `cid` is validated at `watch.py:122-123` (`startswith("UC") and len==24`). No shell injection — `subprocess` is called without `shell=True` (verified via `transcript_store._ytdlp` pattern).
- **FLAG — `tools/ingest_watch.py:99`:** `a.main` is `os.path.realpath(a.main)` from CLI `--main` arg, then `os.path.join(main, "transcripts", vid, name)` — `vid` from `os.listdir(p["transcripts"])` (filesystem listing, not user input). Safe. But `a.main` itself is not validated to be inside expected bounds — an operator could pass `--main /` and `handoff --apply` would write to `//transcripts/...`. This is an operator tool, not a user-facing endpoint. Acceptable.

---

### SECTION 4: FRONTEND QUALITY

**This is a backend ingest service. There is no frontend.**

No HTML, CSS, JS, or UI components exist in this diff. The "frontend" is:
- `tools/ingest_watch.py` CLI (7 subcommands)
- `docs/audits/parallel/pp-ingest_STATE.md` STATE file (first-line notice)
- `data/editorial/ingest/live.json` live numbers JSON
- `data/editorial/ingest/coverage/YYYY-MM-DD.md` coverage report markdown

**CLI quality:** Good. `tools/ingest_watch.py:1-17` docstring clearly describes all subcommands. `--help` works via `argparse`. `status` and `coverage` print JSON + file path. `moments --since` outputs JSON lines (pipe-friendly). `handoff` dry-run by default, `--apply` to execute. Well-designed operator UX.

**Scores for this section reflect "no frontend to evaluate" — not a failure, just N/A.**

---

### SECTION 5: BACKEND QUALITY

#### DB operations — **GOOD, one gap**

- `queue.py:71-77` WAL mode + `synchronous=FULL` — correct for durability.
- `queue.py:82-83` `x()` and `rows()` use `self.lock` (RLock) for thread safety. Correct.
- **GAP — No rollback on failure:** `queue.py` uses `isolation_level=None` (autocommit). Each `self.db.execute()` is its own transaction. If `service.py:237-275` `_settle()` does `ledger.append()` (filesystem) then `q.set_state()` (DB) and the DB write fails, the ledger has the moments but the video state doesn't advance — on restart, `q.recover()` resets `MINING→TRANSCRIBED` and the video is re-mined, appending duplicate lines (handled by "latest wins" dedup). No data loss, but no atomicity between ledger and DB. This is a known tradeoff documented in spec section 7: "A crash between the two re-appends identical lines on restart: readers keep the latest line per moment_id." Acceptable.
- **GAP — `queue.py:78-80`:** Schema migration for `first_sight` column uses `ALTER TABLE ... ADD COLUMN` without checking if it already exists beyond the `if "first_sight" not in cols` guard. Correct, but if the DB is corrupted and `PRAGMA table_info` fails, the exception is unhandled and `Queue.__init__` crashes. Minor.

#### External API calls — **EXCELLENT**

- Every HTTP call has timeout: `watch.py:88,98` (15s RSS, 120s playlist), `providers.py:191` per-backend `timeout_s`, `fetch.py:92-93` (120s probe).
- Every call has retry with backoff: `providers.py:587-615` Throttle (2s→60s exponential), `watch.py:37-58` YouTubeGate breaker, `fetch.py:110-118` caption retry schedule.
- Graceful degradation: `providers.py:645-748` Router falls through chain, `watch.py:197-204` RSS→playlist fallback, `service.py:237-275` outage vs rejection distinction.
- **One gap:** `spend.py:44-57` `CreditMeter.measure()` calls `self.backend.get_json("/credits")` with `timeout=30` (default in `providers.py:318`). If Heimdall's `/credits` endpoint is slow (30s timeout), the `health` loop thread blocks for 30s. The health loop runs every 60s, so this could cause the health thread to fall behind. Should use a shorter timeout (10s) for the meter probe.

#### Cron job — **EXCELLENT (no cron, tmux loops)**

- `service.py:319-328` `_loop()` catches `Exception`, logs `loop_error` event, continues. One loop crashing doesn't kill others.
- `service.py:351-362` `SIGINT`/`SIGTERM` handling with `stop.set()` + `join(timeout=30)` — graceful shutdown.
- `service.py:83` `q.recover()` on restart resets `probing→discovered` and `mining→transcribed` — no stuck videos.
- **Gap:** `service.py:348-349` health loop runs `coverage.check()` which does live YouTube listings. If YouTube is down during the coverage hour (06:00 ET), `coverage.check()` will mark all channels as `unmeasured` and the report will show `measured: false`. This is correct per L-m, but the `kv_set("coverage_day", day)` at `service.py:310` still marks coverage as done for the day — so a transient YouTube outage at 06:00 ET means no coverage report until tomorrow. Should retry coverage later in the day if `measured == false`.

#### Memory leaks — **PASS**

- `service.py:72-74` Two `ThreadPoolExecutor`s with bounded `max_workers` (20 global, 3 video). No unbounded growth.
- `providers.py:531-532` `Health.events = deque(maxlen=50)` — bounded.
- `ab.py:253-259` `attempts` list grows with every attempt in A/B run — for 30 videos × 8 windows × 3 attempts = ~720 entries. Small, bounded by `--max-windows` and `--videos`. Fine.
- **One concern:** `service.py:62` `self._rlog_lock` + `service.py:121-127` `_on_attempt` appends to `replies_log/YYYY-MM-DD.jsonl` on every attempt. This file grows without rotation. At ~100 videos/day × ~5 windows × 1 attempt = 500 lines/day × ~500 bytes = 250KB/day. Manageable, but no rotation or cleanup policy. Should add log rotation.

#### Logging — **GOOD**

- `service.py:112-119` `_log()` prints + appends to `service.log` with ISO timestamp. Every state change goes to `events` table (`queue.py:92-95`).
- `service.py:121-127` every attempt (ok/invalid/error) goes to `calls` table + `replies_log` JSONL with full context (backend, model, latency, tokens, cost, error).
- `service.py:129-134` override changes logged with refused list.
- **Gap:** `service.py:324-326` `loop_error` event captures `traceback.format_exc()[-2000:]` — last 2000 chars of traceback. If the traceback is longer (deep call stack), the *cause* (first frames) is truncated, keeping only the last frames. Should be `[:2000]` or include both head and tail.

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this code does excellently (explicitly calling out):**
- The provider abstraction (`Router` + `Health` + `Throttle` + `SpendBook`) is genuinely impressive — it would not look out of place at a top-tier infra team. Bounded concurrency, circuit breaking, spend tracking, and graceful fallback are all correctly implemented.
- The ledger design (append-only, fsync, torn-tail handling, bisection read, contract fingerprinting) is thoughtful and correct.
- The state machine (`queue.py` STATES + `claim()` atomicity + `recover()`) is robust.
- Law compliance is thorough — every law has a concrete enforcement point, not just a comment.

**What Bloomberg/Coinbase/Blockworks would do differently:**

1. **No observability beyond log files.** There's no metrics endpoint (Prometheus `/metrics`), no alerting integration (PagerDuty/OpsGenie), no dashboard. `live.json` and `coverage/*.md` are polling-based — an operator must manually check them. A world-class system would expose `queue depth`, `error rate by backend`, `spend burn rate`, and `coverage %` as scrape-able metrics with alert thresholds. **Impact: HIGH** — without alerting, a silent outage (Heimdall down, all videos in `MINE_WAIT`) goes unnoticed until someone checks `live.json`.

2. **No dead-letter queue or manual retry for `MINED_PARTIAL` videos.** After 72h, a `MINED_PARTIAL` video goes to `next_at = now + 10^9` (effectively never retried). Its partial moments are in the ledger, but the failed windows are permanently lost. There's no operator command to force-retry a specific video or to list all `MINED_PARTIAL` videos. `tools/ingest_watch.py` has no `retry --video-id` command. **Impact: MEDIUM** — rare (only when a model consistently rejects a window), but when it happens, there's no recovery path.

3. **Coverage check is point-in-time, not continuous.** `coverage.py:check()` lists channels *at check time* and compares to the queue. If a video was published and deleted within the same polling interval (~10 min), it's never discovered and never appears in coverage. A world-class system would use YouTube's PubSubHubbub (WebSub) for push notifications to catch deletions. **Impact: LOW** — YouTube deletions within 10 min are rare for partner channels.

4. **No transcript quality signal.** `fetch.py` stores captions verbatim but never checks if they're garbage (auto-captions for music-heavy videos, wrong language detected as English, empty segments). A world-class system would score transcript quality (word count, language confidence, segment density) and flag low-quality transcripts before mining. **Impact: MEDIUM** — mining garbage transcripts wastes Heimdall credits and produces bad moments.

5. **The A/B harness (`ab.py`) is excellent but not automated.** It requires manual invocation with `--backends` and `--video-list` juggling. A world-class system would run the A/B automatically on a schedule (weekly), compare the local model against Heimdall, and auto-promote the local model when it meets the bar (updating `providers.json` chain order). Currently this is a manual integrator step. **Impact: LOW** — correct for pre-merge, but should be automated post-merge.

6. **No cost attribution per video/channel.** `stats.py` reports `usd_24h_by_vendor` but not `usd per channel` or `usd per video`. An operator cannot tell which channel's videos are most expensive to mine (long videos with many windows). **Impact: LOW** — useful for optimization, not critical.

---

### SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **88/100** | State machine, provider routing, and ledger are excellent. Deductions for: Short detection fragility, `mine_once` release logic, missing `calls.video_id` index, future-dated publish edge case |
| **Frontend/UI** | **N/A** | No frontend exists — this is a backend ingest service. CLI tooling is well-designed for its purpose |
| **Error handling** | **85/100** | Every external call has timeout+retry+fallback. Every loop catches and continues. Deductions for: no ENOSPC handling on SQLite, coverage not retried on unmeasured, traceback truncation direction |
| **Security** | **92/100** | No injection vectors, no hardcoded secrets, redirect blocked, keys redacted, override allowlisted. Deductions for: `channel_update` no column whitelist (low risk), no cross-process budget sharing |
| **Performance** | **82/100** | Bounded concurrency, WAL mode, bisection reads, atomic claims. Deductions for: missing `calls.video_id` index (full scan on `SUM WHERE video_id`), `GROUP BY backend` full scan every 60s, no log rotation |
| **Law compliance** | **98/100** | All 12 laws verified compliant with specific line citations. 2-point deduction for `mine.py:304-315` discarding better-scoring observation on overlapping windows (minor L-q quality issue) |
| **World-class gap** | **78/100** | Core ingest+mining is production-grade. Gaps are observability (no metrics/alerting), no dead-letter retry, no transcript quality gate, manual A/B promotion |
| **OVERALL** | **87/100** | Strong production candidate. One P0 must be fixed, three P1s should be fixed before merge |

---

### SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | Add index on calls.video_id | queue.py:49-52 SCHEMA | Every mine_video does SUM WHERE video_id without an index — full table scan that degrades linearly. At 500 calls/day, 30-day table = 15K rows scanned per video mined. Will cause visible latency within weeks.

P1 HIGH     | Fix mine_once local model release condition | service.py:283-284 | Releases GPU0 model when no MINE_DUE videos are currently due, but MINE_WAIT videos with future next_at still need it. Causes unnecessary unload/reload cycles every 5s when videos are in outage retry.

P1 HIGH     | Add retry for unmeasured coverage reports | service.py:307-314 | If YouTube is down at 06:00 ET, coverage is marked done for the day with measured=false. No report until tomorrow. Should retry every 2h if measured==false and hour != COVERAGE_HOUR_UTC.

P1 HIGH     | Add Prometheus/metrics endpoint or structured health check | service.py:299-315 health_once | No alerting on outage — operator must poll live.json manually. A 80-min Heimdall outage silently queues all videos with no notification beyond log lines.

P2 MEDIUM   | Keep better-scoring observation on overlapping windows | mine.py:304-315 | Currently keeps first observation's scores/reason, discards second. Should compare rank_score and keep the better one. Affects moment quality, not correctness.

P2 MEDIUM   | Add dead-letter retry command for MINED_PARTIAL videos | tools/ingest_watch.py | No way to force-retry a MINED_PARTIAL video or list them. After 72h horizon they are permanently incomplete with no operator recourse.

P2 MEDIUM   | Add transcript quality gate before mining | fetch.py:205-244 _store_captions | Auto-captions for music/intro-heavy videos can be garbage. Mining them wastes credits. Add word-count and language-confidence check.

P2 MEDIUM   | Fix traceback truncation direction | service.py:183,225,230 | traceback.format_exc()[-2000:] keeps tail (last frames), truncates cause (first frames). Should keep head or head+tail.

P2 MEDIUM   | Add log rotation for replies_log and service.log | service.py:55-56,121-127 | Both grow without bound. At 500 lines/day for replies_log + continuous service.log, disk fills over months. Add daily rotation or size cap.

P3 LOW      | Shorten CreditMeter probe timeout | spend.py:44-46 | Uses default 30s timeout for /credits probe in health loop (every 60s). Blocks health thread for 30s if Heimdall is slow. Use 10s.

P3 LOW      | Validate --main path in handoff command | tools/ingest_watch.py:99 | No validation that --main is a plausible editorial store path. Operator typo could write to wrong location. Add existence + structure check.

P3 LOW      | Handle future-dated publish timestamps | fetch.py:173-176 | now_ts - pub_ts negative when pub_ts is in future — video not marked SEEN_OLD, proceeds to mining. Add explicit future check.

P3 LOW      | Automate A/B promotion of local model | ab.py:217-333 | Currently manual: integrator must run A/B, compare, edit providers.json chain order. Should auto-promote when local meets bar.
```

---

### SECTION 9: THE ONE THING

**Add `CREATE INDEX calls_video ON calls(video_id)` to `queue.py:49-52` — without it, every video mined does a full table scan on `calls` that will silently degrade from milliseconds to seconds as the table grows, and it's a one-line fix.**

---

### SECTION 10: FINAL VERDICT

**This code is ready for production after one fix.** The P0 (missing DB index on `calls.video_id`) must be added before merge — it's a one-line schema change with no risk. The four blocking audit findings (B1-B4) are all correctly resolved, law compliance is verified at 98%, and the provider/ledger/state-machine architecture is genuinely well-engineered. The remaining P1s (metrics/alerting, coverage retry, GPU0 release logic) should be addressed within the first sprint post-merge but do not block deployment.
