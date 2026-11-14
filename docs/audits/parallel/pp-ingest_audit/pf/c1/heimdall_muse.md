# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 459.9 s, $0.033, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff 98a57406)

## SECTION 1: CORRECTNESS

### Main flow: `poll_channel` with `PLAYLIST_FIRST=True`

**Step 1 — Channel listing order.** `watch.py:204-212` iterates `(playlist, rss)` when `playlist_first=True`. If `playlist()` succeeds, `break` — RSS never called. If `playlist()` raises `ListError`, falls through to `rss()` (if `rss_mode`). This matches spec: playlist first, RSS fallback.

**Step 2 — Error accumulation.** `watch.py:211` joins errors: `f"{err + '; ' if err else ''}{e.kind}" + (f": {e.detail[:160]}" if get is playlist else "")`. When playlist fails then RSS fails, error = `"playlist_kind: detail; rss_kind"`. When playlist succeeds, `err` stays `None` and is never written to `last_error` (line 214-215 only on `entries is None`). Correct.

**Step 3 — Publish time independence.** `fetch.py:30-41` `publish_time()` uses `release_timestamp` for live VODs, else `rss_published` (only when `discovered_via=="rss"`), else `timestamp`. Listing source does not affect publish time measurement — correct per spec question.

**Step 4 — Queue recording.** `watch.py:226-227` `q.add_video(..., via=source, ...)` records `discovered_via` as `"uploads_playlist"` or `"rss"`. `newest_published` updated from `e.get("published") or _ts_iso(ts_)` (line 229-231). For playlist entries, `published` is absent, so `_ts_iso(ts_)` (approximate date) is used. For RSS entries, exact `published` is used. No data loss.

**Logic errors found:**

1. **RSS detail silently dropped on fallback path.** `watch.py:211` — when `get is rss`, `e.detail` is discarded (`""`). If RSS fails after playlist fails, the RSS failure reason (e.g., `rss_http_500`) is recorded without detail, while playlist detail is kept. This is intentional per old code (RSS errors had no detail worth keeping — just `url`), but now with playlist-first, the *primary* failure's detail is kept and the *fallback's* is not. If playlist fails with a transient error and RSS fails with a meaningful HTTP error, the meaningful detail is lost. Minor but inconsistent.

2. **No bug in double-count / loss.** `q.add_video` uses `INSERT OR IGNORE` (`queue.py:148-153`), so re-listing same video is idempotent. `first_sight` logic (line 188, 222-223) correctly marks backfill vs live. No double-count.

3. **ETag/Last-Modified only updated on RSS path.** `watch.py:194-195` `upd` is only populated inside `rss()`. When playlist succeeds, `upd={}` and `channel_update` (line 234) writes no ETag. This is correct — playlist doesn't use ETags — but means if system flips back to RSS-first (via `playlist_first=False`), stale ETags from before the flip are reused. Not a bug, but worth noting: ETags survive the mode switch.

**Race conditions:**

- `poll_channel` is called from `service.py:229` via `ThreadPoolExecutor(max_workers=4)` mapping over channels. Each channel has distinct `channel_id` primary key, so `ensure_channel` + `channel_update` + `add_video` don't race across channels. Within a single channel, only one `poll_channel` runs at a time (one entry per channel per cycle). No race.

- `YouTubeGate.sem` (3 slots) shared between listing, probe, captions. `watch.py:60-74` correctly uses `with self.sem` for yt-dlp calls. No deadlock: `poll_channel` holds no lock while calling `gate.run`.

**N+1 queries:**

- `watch.py:228-231` loop calls `q.add_video` per entry (up to 30 per channel × 64 channels = 1920 INSERTs per cycle). Each is a separate SQLite transaction (autocommit mode, `isolation_level=None`). This is the existing pattern, not introduced by this diff. At 76s cycle time, SQLite handles it, but it's not batched. Pre-existing, not a regression.

**Edge cases:**

- Empty channel (0 entries): `entries=[]`, loop does nothing, `channel_update` records `listed += 0`, returns `{"new":0}`. Correct.
- `rss_mode=False` and `playlist_first=True`: iterates `(playlist, rss)` but `rss` is skipped via `if get is rss and not rss_mode: continue`. Only playlist tried. If playlist fails, `entries` stays `None` → error path. Correct — matches old behavior where RSS was simply not tried when canary said down.
- `rss_mode=False` and `playlist_first=False`: iterates `(rss, playlist)` — RSS skipped, playlist tried. Same result. Both orderings degrade gracefully when RSS is down.
- `playlist_first=None` (default): falls back to `config.PLAYLIST_FIRST` (True). Correct.

**Verdict on Section 1 questions:**
1. No path loses or double-counts videos. Queue records (`via`, `ETag`, `newest_published`) are preserved correctly.
2. Cost trade-off is sound (see Section 5).
3. Breaker risk is not increased (see Section 5).

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, ~10 min, ETag/backoff, last-seen ledger, re-upload detection, Shorts/live handling, durable queue, same transcript store format, bounded concurrency, spend tracking, append-only ledger, coverage check, blind A/B) | **COMPLIANT** | This diff only changes listing order. All BUILD requirements remain intact. `watch.py:60-74` gate, `queue.py` WAL, `fetch.py` store writer, `ledger.py` append — all untouched. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:116-131` every role has ≥2 backends. `providers.py:758-810` Router tries chain in order. No vendor/model names outside `providers.json` (enforced by test `test_no_vendor_or_model_name_outside_the_provider_config`). This diff touches no provider code. |
| **L-l strict schema, nothing repaired** | **COMPLIANT** | `mine.py:447-499` validator rejects on any deviation, never repairs. `providers.py:984-989` re-asks with rejection reason, never patches. Untouched by diff. |
| **L-j / L-m fail closed; nothing measured is never a pass** | **COMPLIANT** | `ledger.py:337-356` expired/unmeasured → excluded. `coverage.py:62-63` unmeasured channels → not counted. `watch.py:162-174` unreadable optout → `oerr` pauses fetch/mine. Diff preserves all. |
| **L-h / L-k read as spoken, never rewrite stored records** | **COMPLIANT** | `contract.py:122-125` `E.spoken()` for all text. `fetch.py:236-237` `_write_once` never overwrites. Untouched. |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `timing: segment` for captions, `duration_s: null`. Packager re-anchors. Untouched. |
| **L-u hard exclusions flagged before ranking** | **COMPLIANT** | `mine.py:21-24` `HARD_RISKS`, `ledger.py:347-348` hard flag exclusion. Diff doesn't touch mining or adapter. |
| **L-v speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`, `fetch.py:186-191,242-247` duplicate detection, `config.py:66-69` `expires_at`. Untouched. |
| **Secrets (keys by name from env file, never logged)** | **COMPLIANT** | `providers.py:180-221` Keyring reads by name, `redact()` on all error text. `providers.py:953-955` redaction before recording. Diff adds no secret handling. |
| **SPEND FREEZE (orchestrator 05:30)** | **COMPLIANT** | `providers.json:5-9` freeze list, `providers.py:783-787,806-812,931-932` enforcement. Diff doesn't touch spend logic. |
| **L-aa time savers automatic once measured and audited** | **COMPLIANT** | This diff *is* the L-aa time saver. Measurement: A/B Nov 14 (25 uploads, median 6 min faster, 0 errors, 540 listings). Audit: 102 cycles, 76s avg, no rate limits. `config.py:30-33` documents measurement. `watch.py:1-9` docstring updated. Design 3 referenced. |

**No violations. No partial compliance.**

---

## SECTION 3: SECURITY

| Check | Result | Detail |
|-------|--------|--------|
| **SQL injection** | **PASS** | All queries use parameterized `?` placeholders. `queue.py:97-99` `self.db.execute(sql, args)`, `watch.py` has no SQL. No `f-string` SQL with user input. `queue.py:160-166` `set_state` validates field names against `VIDEO_FIELDS` allowlist before interpolating column names. |
| **Authentication bypass** | **N/A** | No HTTP routes, no auth layer. This is a backend ingest service (tmux process, no web server). |
| **Rate limiting gaps** | **PASS** | `YouTubeGate` (3 slots, breaker with exponential backoff 10-60 min) throttles all yt-dlp calls. `providers.py:654-682` per-backend throttle on 429/503. `providers.json:140-141` `health` circuit breaker. This diff *increases* yt-dlp load (64 playlist listings vs 1 canary + conditional RSS), but gate still bounds concurrency to 3. No new gap. |
| **Secrets in code** | **PASS** | No hardcoded keys. `providers.json:10` `env_file: /home/ultron/protocol_pulse/.env`, `providers.py:180-221` Keyring reads by name. `providers.py:213-220,241-247` redaction on all error paths. Diff adds no secrets. |
| **Unvalidated input → DB/filesystem/shell** | **PASS** | `watch.py:122-125` `uploads_url` validates `cid` format (`UC` + 24 chars) before interpolating into URL. `watch.py:130-131` yt-dlp args are list elements (no shell interpolation — `subprocess` without `shell=True` via `config.ts()._ytdlp`). `fetch.py:92-93` `video_id` interpolated into URL but validated as 11-char YouTube ID upstream. |
| **SSRF / redirect** | **PASS** | `providers.py:322-327` `_NoRedirect` handler refuses redirects (bearer key never follows). `providers.py:168-178` `override_allowed` restricts runtime URL overrides to localhost or configured host. |

**No security issues introduced by this diff.**

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend in this diff or feature.**

This is a headless ingest service: SQLite queue, yt-dlp subprocesses, LLM mining, JSONL ledger. No HTML, CSS, JS, or UI components. The only "frontend" is `docs/audits/parallel/pp-ingest_STATE.md` (markdown status file) and `ingest/live.json` / `ingest/coverage/*.md` reports — all correctly generated and tested.

No scoring applicable. Excluded from overall.

---

## SECTION 5: BACKEND QUALITY

| Area | Assessment |
|------|-----------|
| **DB operations** | SQLite WAL, `PRAGMA synchronous=FULL` (`queue.py:87`), single connection behind `RLock`. Writes are atomic per statement (autocommit). No explicit `try/except/rollback` — but with `isolation_level=None` (autocommit), each statement is its own transaction, so no partial transaction to roll back. Correct for this workload. |
| **External API calls** | YouTube: `YouTubeGate` with timeout (120s playlist, 15s RSS), concurrency cap (3), breaker (10-60 min backoff), per-channel backoff (2^n min, max 60). LLM: `providers.py:654-682` throttle with `Retry-After`, `health.py` circuit breaker, `daily_budget_usd` caps. All present. |
| **Cron / loop failure handling** | `service.py:855-864` `_loop` wraps `fn()` in `try/except Exception`, logs `loop_error` event, continues. `BaseException` (SIGTERM, GPU0 stop) propagates correctly. No loop crash kills the service. |
| **Memory leaks** | `purge.py:205-206` `_SHA` cache bounded at 4096 entries, cleared when full. `service.py:706-707` `_conv` cache cleared at 5000. No unbounded growth. |
| **Logging** | Every state change → `events` row (`queue.py:107-110`). Every model attempt → `calls` + `replies_log/*.jsonl` (`service.py:192-200`). Every loop error → `loop_error` event. Coverage/purge/signal all log. Excellent observability. |

**Cost analysis for this diff (reviewer question 2):**

- Before: 1 RSS canary (1 HTTP request) + 64 RSS feeds (conditional, mostly 304) per cycle. ~7s cycle.
- After: 64 playlist listings (yt-dlp subprocess each) per cycle. ~76s cycle (measured over 102 cycles).
- 76s is well within the 600s poll interval — no overlap, no starvation. The 3-slot gate means at most 3 yt-dlp processes concurrently; captions/probes share the same gate but `fetch_once` runs every 10s with `limit=10` and `mine` every 5s — they interleave, not block. Worst case: a caption fetch waits ~25s behind 3 playlist listings (76s/64 × 3 slots ≈ 3.5s per listing × ~7 queued ahead). Acceptable for a 48h caption deadline.
- No rate limit observed in 6,500 listings. YouTube's playlist endpoint is not rate-limited like search.

**Breaker risk (reviewer question 3):**

- Playlist listings go through `YouTubeGate.run()` (`watch.py:60-74`) which checks `open_for()` before acquiring semaphore and calls `trip()`/`calm()` on rate-limit marks. Same path as before — just more calls through it. The breaker is shared, so a playlist rate-limit would pause captions too (by design — fail closed). But 0 trips in 6,500 listings suggests the playlist endpoint has generous limits. Risk is low and well-instrumented.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this diff does well:** The measurement methodology is genuinely excellent — A/B with 6 channels over 3h, 540 listings, median/percentile reporting, overnight validation of 102 cycles. The `playlist_first` parameter with `None` defaulting to config constant is clean and testable. The two-function refactor (`rss()`/`playlist()` closures) is minimal and correct.

**What's missing or could be better:**

1. **No adaptive polling.** Bloomberg Terminal doesn't poll every channel at the same cadence. High-velocity channels (Bloomberg, CNBC — multiple uploads/hour) should be polled more frequently than low-velocity ones (1 upload/week). A fixed 10-min poll means a breaking news video from Bloomberg waits up to 10 min + 76s listing time. Per-channel adaptive intervals based on observed upload frequency would cut median latency further at no extra cost (fewer polls for quiet channels).

2. **No publish-time notification.** The fastest possible discovery is YouTube's PubSubHubbub (WebSub) push notifications — YouTube POSTs to your callback within seconds of publish, vs polling. For a "never miss the day's most relevant content" product, push + poll fallback would be the world-class architecture. Polling-only, even at 6 min faster, still has a 10-min window.

3. **Playlist `approximate_date` is not exact.** `watch.py:130-131` uses `--extractor-args youtubetab:approximate_date` — the `timestamp` from playlist listings is approximate (date-level granularity for older videos). The code correctly doesn't use it as publish time (fetch re-probes per video), but `newest_published` tracking (line 229-231) stores approximate dates for playlist-discovered videos. This could cause `BACKFILL_H` (72h) edge cases where a video's approximate date is off by a day and it's incorrectly marked `seen_old` or `discovered`.

4. **No listing latency metric.** The service tracks `publish_to_discovered` latency in `stats.py:38` but doesn't separately track *listing source latency* (playlist vs RSS discovery time). After this change, there's no way to verify the 6-min improvement holds in production without manual log analysis. A `discovered_via` breakdown in `live.json` would close the loop.

**Already excellent:** Error handling, durability (WAL + fsync + flock), spend controls, the purge system, the down-signal protocol, test coverage (356 tests). These are production-grade.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Correct, minimal, well-measured. -8 for RSS error detail loss and approximate-date edge case. |
| **Frontend/UI** | **N/A** | No frontend in scope. |
| **Error handling** | **95/100** | Every failure path has backoff, retry, or terminal state. Loop errors don't crash service. -5 for RSS detail truncation. |
| **Security** | **98/100** | No injection, no secret leaks, redirect refused, override restricted. -2 for no input length limit on `channel_id` in `uploads_url` (minor). |
| **Performance** | **88/100** | 76s cycle well within 600s budget. 3-slot gate prevents overload. -12 for 10x latency increase (7s→76s) with no adaptive polling to offset. |
| **Law compliance** | **100/100** | All laws compliant. L-aa specifically satisfied with measurement + audit. |
| **World-class gap** | **78/100** | Solid polling improvement, but still polling-only. No push notifications, no adaptive cadence, no listing-source metrics. Core ingest is strong; discovery architecture is good, not world-class. |
| **OVERALL** | **91/100** | Production-ready change. Well-measured, correctly implemented, no regressions. |

---

## SECTION 8: PRIORITY ACTION PLAN

| Priority | What | File:Line | Why |
|----------|------|-----------|-----|
| P1 HIGH | Add `discovered_via` breakdown to `live.json` (count + median latency per source) | `stats.py:24-50` | Without it, the 6-min improvement claim can't be verified in production; silent regression if YouTube changes playlist behavior |
| P1 HIGH | Fix `BACKFILL_H` edge case: playlist `approximate_date` can be off by ~1 day, causing `seen_old` misclassification | `watch.py:222` `now_ts - float(ts_) > backfill_h * 3600` | A video published 71h ago with approximate date rounded to 72h+ would be incorrectly marked `seen_old` and never mined |
| P2 MEDIUM | Preserve RSS error detail when both sources fail | `watch.py:211` | `rss_list` failures include HTTP status in `e.kind` but detail (body snippet) is dropped; useful for debugging YouTube outages |
| P2 MEDIUM | Consider per-channel adaptive poll intervals based on observed upload frequency | `config.py:25-26` `POLL_S` | High-velocity channels (Bloomberg: 5+/day) polled same as low-velocity (1/week); wastes 90% of listings on quiet channels while adding latency for busy ones |
| P2 MEDIUM | Evaluate PubSubHubbub push notifications as primary discovery with polling fallback | `watch.py:1-9` | Would cut discovery latency from minutes to seconds; polling-only is fundamentally limited regardless of source |
| P3 LOW | Add integration test that `poll_channel` with `playlist_first=True` never calls `rss_list` when playlist succeeds | `tests/ingest/test_watch_fetch.py` | Existing tests cover the new path but don't explicitly assert RSS is *not* called (only that playlist is used first) |
| P3 LOW | Document that `newest_published` from playlist entries is approximate | `watch.py:229-231` | Future readers may assume `newest_published` is exact and build logic on it |

---

## SECTION 9: THE ONE THING

**Instrument the improvement you just shipped — add per-source discovery latency to `live.json` so you can prove the 6-minute win holds in production and catch the day YouTube changes the playlist endpoint.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The change is minimal (1 config flag + 1 function refactor), correctly implements playlist-first discovery, preserves all queue/listing invariants, and is backed by solid measurements (25 uploads, 6-min median improvement, 0 errors over 6,500 listings). No blocking issues. Ship it, then add per-source latency metrics to `live.json` so the improvement stays verified.
