# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 570.9 s, $0.032, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff c1141fff vs af298eb9)

## SECTION 1: CORRECTNESS

### 1.1 The diff under review — does it do what it claims?

**Claim:** `is_conversation()` now implements "skip only a marked episode under 0.3 TPM".

**Walkthrough of `pipeline/ingest/mine.py:302-315`:**

```python
def is_conversation(episode):
    ep = episode or {}
    n, t = ep.get("speaker_markers"), ep.get("turns_per_min")
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        return True
    if isinstance(t, bool) or not isinstance(t, (int, float)):
        return True
    return t >= CONVERSATION_TPM
```

Logic table vs spec:

| Input | Spec says | Code returns | Verdict |
|-------|-----------|--------------|---------|
| `n=5, t=0.3` | asked (>=0.3) | `True` | ✅ |
| `n=5, t=0.29` | skipped (marked under 0.3) | `False` | ✅ |
| `n=0, t=0.0` | asked (no markers) | `True` (first guard `n<=0`) | ✅ |
| `n=0, t=None` | asked | `True` | ✅ |
| `n=5, t=None` | asked (unmeasurable) | `True` (second guard) | ✅ |
| `n=None, t=0.1` | asked (not an int count) | `True` | ✅ per A40 |
| `n=True, t=0.1` | asked (bool is not int count) | `True` | ✅ — `bool` is subclass of `int` in Python, explicitly excluded |
| `n=5, t=True` | asked (bool not numeric) | `True` | ✅ |
| `n=5, t="0.1"` | asked | `True` | ✅ |
| `episode=None` | asked | `True` (`{}`, `n=None`) | ✅ per A40 |
| `episode={}` | asked | `True` | ✅ |
| `n=5, t=0.0` | skipped | `False` | ✅ |
| `n=-1, t=0.0` | asked (negative markers nonsensical, treated as no markers) | `True` | ⚠️ debatable but harmless — negative never produced by `episode_measure()` |

**Verdict on core logic: CORRECT.** The `bool` exclusion is critical and correctly handled. Without `isinstance(n, bool)` check, `True` (which is `1` in Python) would be treated as 1 marker, and `False` as 0 markers — both wrong. Author got this right.

**Edge case — `n` is float `0.0` or `5.0`:** `isinstance(5.0, int)` is `False`, so returns `True` (asked). `episode_measure()` always produces `int` for `speaker_markers` (`sum(len(...))`), so this path is unreachable in production. Not a bug, but worth noting the type contract is implicit.

### 1.2 `stats.py:109-116` — spotlight_asked_videos

```python
hk = q.rows("SELECT ... SUM(spot_rows IS NOT NULL) AS asked ...")
out["hooks_12h"] = {"spotlight_asked_videos": hk["asked"] or 0, ...}
```

**Old:** `SUM(COALESCE(episode_tpm >= ?, 0))` — counted videos whose TPM met threshold. Required `from . import mine` to get `CONVERSATION_TPM`.

**New:** `SUM(spot_rows IS NOT NULL)` — counts videos where spotlight was actually asked (pass completed and wrote `spot_rows`, even if 0 rows).

**Correctness:** ✅ Superior. Old metric was a proxy (TPM threshold); new metric is ground truth (was the question asked?). Handles all edge cases: unmarked episodes, unmeasurable rates, future threshold changes. The `from . import mine` removal also eliminates a circular-import risk.

**One subtlety:** `spot_rows` is `NULL` for videos whose hook pass hasn't run yet OR for videos that were skipped (marked solo). `spot_rows = 0` means asked but found nothing. `spot_rows IS NOT NULL` correctly distinguishes these. Verified against `service.py:447`: `spot_rows=len(spot) if srep is not None else None`.

### 1.3 `service.py:427` — log text

```python
f"no spotlight question (a marked solo episode: {ep.get('speaker_markers')} markers, "
f"{ep.get('turns_per_min')} turns / min)")
```

Old: `f"no spotlight question ({ep.get('turns_per_min')} turns / min: not a conversation)"`

New adds `speaker_markers` count. ✅ More debuggable. No logic change.

### 1.4 Version bump `mine.py:126` — `mine-hook/3` → `mine-hook/4`

Correct. The question set changed for ~32/67 videos (those with 0.3-1.0 TPM or no markers). `hooks --rerun` (`tools/ingest_watch.py:166-172`) re-queues videos where `hook_version <> mine.HOOK_PROMPT_VERSION`, so old passes will be re-asked. Prompts that didn't change (solo episodes still get 3 hooks with same prompt text) will hit cache — verified: `mine.py:517` uses `PROMPTS[kind](meta, chan, win, max_h=n)` where `n=3` for solo, same as before, so `sha256(prompt)` matches cached entry.

### 1.5 Broader correctness issues (pre-existing, not introduced by diff)

**Race condition — `service.py:320-321` `carry_forward` + `append` under `wlock`:** ✅ Correctly handled. Single lock covers read-then-write. Other processes (if any) use `fcntl.flock` on the file itself (`ledger.py:47`). Within one process, `wlock` prevents interleaving of concurrent `hook_video` and `mine_video` for same video_id.

**N+1 in `purge.py:published()`:** Called per-file in `run_pass` loop, each does `q.video(vid)` (SQL query) + potential file read. For 1000 files this is 1000 queries. Mitigated by `cache = {}` dict, but only within one pass. Not critical at current volume.

**`queue.py:due()` ordering:** `ORDER BY COALESCE(published_ts, listing_ts, discovered_ts) DESC` — newest first. Correct per spec "newest uploads first".

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:107-122` every role has ≥2 backends. `providers.py:159-161` enforces at load. `mine.py:510-520` routes through `Router`. No vendor/model string outside `providers.json` (test `test_no_vendor_or_model_name_outside_the_provider_config` exists). |
| **L-l Strict validation, never repaired** | **COMPLIANT** | `mine.py:446-498` validator rejects on any deviation, raises `Invalid`. `providers.py:983-989` re-prompts with rejection reason, never patches JSON. Markdown fences, duplicate keys, float IDs all rejected. |
| **L-j/L-m Fail closed, nothing measured is never a pass** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside` returns `None` not `False` when unmeasured. `ledger.py:341-342` drops moments with `pub is None`. `flagcheck.py:346` unmeasured → `"unmeasured"` cell, never counted as agreement. `coverage.py:62-63` unmeasured channels → `measured=False`. |
| **L-h/L-k Read as spoken, never rewrite** | **COMPLIANT** | `contract.py:123` `E.spoken(toks[w0:w1+1])`. `fetch.py:237` `ts._store(rec)` — store's own writer, verbatim. `mine.py:396-399` `_untrusted` preserves `>>` markers. |
| **L-e Word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `timing` from record, `file_head=True, vod=True`. `mine.py:530-543` `duration_s=None` when `timing=="segment"`, `duration_estimate_s` flagged. Packager re-anchors. |
| **L-u Hard exclusions** | **COMPLIANT** | `mine.py:23-24` `HARD_RISKS` defined. `ledger.py:347-348` `any(r in HARD_RISKS for r in eff)` → dropped. `flagcheck` integration via `effective_risk()` correctly gates `imperative`/`single_source_breaking` on second model `no`. |
| **L-v Speaker change, re-uploads** | **COMPLIANT** | `contract.py:129-135` speaker marker detection. `ledger.py:351-352` `turn_change_inside is True` → dropped. `fetch.py:186-191,242-247` duplicate detection by title+duration and text fingerprint. |
| **L-q Moments first** | **COMPLIANT** | `mine.py:372-389` windows of sentences, `mine_video` produces moments before any ranking. |
| **L-r No GPU on this service** | **COMPLIANT** | `providers.json:13` `local_gemma.enabled=false`. `providers.py:494-498` `OllamaLocalBackend.enabled()` checks `gpu0.held()` — returns False without lease. No Whisper/NVENC imports. |
| **Spend freeze (05:30 ET Nov 12)** | **COMPLIANT** | `providers.json:5-8` lists 4 frozen vendors. `providers.py:783-786` `frozen()` check. `providers.py:803-804` `effective()` filters frozen unless `freeze_lifted`. Only `mine_paid` has `freeze_lifted` (`providers.json:116-119`). `service.py:625` paid route only when `hsig.paid_open`. |
| **Spend tripwire (90%, notify never halt)** | **COMPLIANT** | `spend.py:130-134` `tripped` vs `ok` vs `unmeasured`. `providers.py:792-797` `order()` moves metered backends last, never removes. `spend.py:182-183` 90% notice kept even if spend later drops. |
| **Ruling 76/77 Expiry 12h + purge** | **COMPLIANT** | `config.py:36` `EXPIRY_H=12`. `ledger.py:280-286` `expiry()` earliest of recorded and computed. `ledger.py:337-338` expired → dropped before all other checks. `purge.py` respects delivered set, idle grace, open files. |
| **Ruling 80 Hook pass** | **COMPLIANT** | `mine.py:160-224` `HOOK_PROMPT` with builder's `JUDGE_HOOK_QUESTION` verbatim. `service.py:375-468` hook loop. `ledger.py:187-209` `carry_forward` preserves flags. |
| **Ruling 87 Shared signal** | **COMPLIANT** | `downsignal.py` loaded by path, used via API only. `providers.py:935-937` probe role `breaker:false`. `spend.py:199-216` switch line handling. |
| **Ruling 98 Paid route** | **COMPLIANT** | `providers.json:96-99` `paid_route` with `after_down_s=1200`, `new_within_s=21600`, `conversation_tpm=1.0`. `service.py:644-677` `_paid_due` + `_queue_rechecks`. `providers.py:687-727` `RoleCaps` daily cap. |
| **Ruling 40 P1 Second-model flag check** | **COMPLIANT** | `flagcheck.py` calibration live (`fresh=True`), `ledger.py:212-241` `check_valid` + `effective_risk` only releases on `no` from different model/version. |
| **09:02 A36 WIDEN (this diff)** | **COMPLIANT** | `mine.py:302-315` correctly implements spec. See Section 1. |

**No violations found.**

---

## SECTION 3: SECURITY

| Check | Verdict | Detail |
|-------|---------|--------|
| **SQL injection** | ✅ PASS | All queries use parameterized `?` placeholders. `queue.py:97-99` `self.db.execute(sql, args)`. No string interpolation of user input into SQL. `purge.py` uses `glob` not SQL. `ledger.py` reads JSON lines, no SQL. |
| **Authentication bypass** | ✅ PASS | No HTTP routes — this is a backend ingest service (tmux process, no web server). `tools/ingest_watch.py` is CLI-only. No auth surface. |
| **Rate limiting** | ✅ PASS | `providers.py:654-682` `Throttle` per-backend with `first_s=2.0, max_s=60.0`, honors `Retry-After`. `watch.py:37-73` `YouTubeGate` with `YTDLP_CONCURRENCY=3`, global breaker on 429/bot-check. `providers.py:769-771` `BoundedSemaphore` per-backend + global `max_inflight=20`. |
| **Secrets in code** | ✅ PASS | No hardcoded keys. `providers.py:180-221` `Keyring` reads from `env_file` (`/home/ultron/protocol_pulse/.env`). `providers.py:213-220` `redact()` replaces key values in error text. `providers.py:241-247` `Backend.redact()` per-backend. No `sk-`, `xai-`, `AIza` literals in code. |
| **Unvalidated input → DB/filesystem/shell** | ⚠️ LOW | `fetch.py:92-93` `gate.run(["-J", ..., f"https://www.youtube.com/watch?v={video_id}"])` — `video_id` comes from YouTube listing (not user input), validated as 11-char YouTube ID pattern in `ledger.py:27`. `yt-dlp` args are list (no shell). `purge.py:76-77` validates `units` starts with `/`, no `..`, not in `FORBIDDEN`. `config.py:72-78` `StoreGuard` prevents writing inside main tree. |
| **SSRF / redirect** | ✅ PASS | `providers.py:322-324` `_NoRedirect` refuses redirects (bearer key never follows). `providers.py:168-177` `override_allowed` only permits `127.0.0.1`/`localhost`/`::1` or same host+scheme. |
| **Prompt injection** | ✅ PASS | `mine.py:396-399` `_untrusted()` replaces `<` with `‹` to prevent closing `<sentences>` block. Channel/title/text all passed through `_untrusted` + `_q` truncation. |

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend in this package.** This is a pure backend ingest service: SQLite queue, yt-dlp subprocesses, LLM API calls, JSONL ledger. No HTML, CSS, JS, or UI components. The "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` markdown reports.

CLI quality assessment:
- `tools/ingest_watch.py` has 8 subcommands with `--help` descriptions ✅
- `coverage.py:105-125` generates both `.json` and `.md` reports ✅
- `stats.py:write_live` produces `live.json` for monitoring ✅
- No loading/error/empty states needed — CLI prints to stdout/stderr

**Score: N/A (no frontend to evaluate)**

---

## SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|------|---------|--------|
| **DB transactions** | ⚠️ PARTIAL | `queue.py:82` `isolation_level=None` (autocommit). Each `self.x()` is one statement, auto-committed. No explicit `BEGIN`/`COMMIT`/`ROLLBACK` wrapping multi-statement operations. `set_state()` + `event()` are two separate autocommit writes — crash between them leaves state changed without event (or vice versa). In practice low-risk (events are audit trail, not consistency-critical), but `claim()` (`queue.py:169-175`) correctly uses single atomic `UPDATE ... WHERE state IN (...)` with `rowcount` check. `WAL` + `synchronous=FULL` is correct for durability. |
| **External API calls** | ✅ EXCELLENT | Every LLM call: timeout (`timeout_s` per backend, 60s-600s), retry (`transport_retries=3`, `attempts` per role), backoff (`Throttle` with jitter), circuit breaker (`Health` with 3 open conditions), graceful degradation (next backend in chain, outage vs rejection distinction). yt-dlp: `YouTubeGate` with concurrency limit, global breaker, per-channel backoff. RSS: `timeout=15`, fallback to playlist. |
| **Cron/long-running loops** | ✅ EXCELLENT | `service.py:783-792` `_loop()` wraps `fn()` in `try/except Exception`, logs `loop_error` event, never crashes service. `stop` event for graceful shutdown. Each loop has independent `every` + `jitter`. `signal.py` tick handles unreadable state without crashing. |
| **Memory leaks** | ✅ PASS | `ThreadPoolExecutor` with bounded `max_workers`. `queue.py:82` single SQLite connection (not per-request). `providers.py:581` `deque(maxlen=50)` for health events. `service.py:650-651` `_conv` cache cleared at 5000 entries. No unbounded growth. |
| **Logging** | ✅ EXCELLENT | Every state change → `events` table. Every LLM attempt → `calls` table + `replies_log/*.jsonl`. Every override change, spend trip, outage, purge pass, signal switch → event + log line. `service.log` file + stdout. Error context includes `traceback.format_exc()[-2000:]` where relevant. |

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this already does at world-class level:**
- The provider abstraction (`Router` + `Health` + `Throttle` + `SpendBook` + `RoleCaps`) is genuinely excellent — rivals any production LLM gateway. Bounded concurrency, per-backend throttling, circuit breaking on 3 signals, spend metering, daily caps with reservation, cache with validation. This is better than most startups' LLM infrastructure.
- The durability story (WAL SQLite, `fsync` ledger appends, torn-tail sealing, `flock` for single-writer, crash recovery via `recover()`) is thorough and well-tested.
- The prompt-injection defense (`_untrusted` + `<sentences>` block) and secret redaction are thoughtful.

**Genuine gaps:**

1. **No dead-letter queue / alerting for `mined_partial` videos.** Videos that hit `MINE_CONTENT_PASSES=3` with rejected windows become `mined_partial` and retry every 6h for 72h. If the model consistently rejects certain content (e.g., non-English segments that pass caption check but confuse the model), these silently accumulate. No alert fires. Bloomberg would have a dashboard counting partials by failure reason.

2. **No end-to-end latency SLO tracking.** `stats.py` reports `publish_to_mined_min` p50/p90, but there's no SLO definition (e.g., "95% of videos mined within 30 min of publish") and no alert when breached. The 25-min discovery window (poll + RSS cache) is documented but not monitored as an SLO.

3. **yt-dlp as subprocess is fragile.** Every listing, probe, and caption fetch shells out to `yt-dlp`. YouTube changes break this silently (as happened Nov 7: RSS 404 for all channels). No structured health check for "yt-dlp itself is broken" vs "one channel failed". A single `yt-dlp --version` check or canary video probe would catch this faster.

4. **No backpressure on queue growth.** If Heimdall is down for hours, `MINE_WAIT` videos accumulate. `mine_once` processes 3 at a time every 5s. No prioritization beyond "newest first" — a burst of 100 uploads during outage means oldest videos wait longest, potentially expiring (12h) before being mined. The paid route handles this for new uploads, but the general case has no queue-depth alert.

5. **Coverage check is listing-dependent.** `coverage.py:check()` re-lists every channel to determine "what was published". If listing itself is broken (yt-dlp breaker open), coverage reports `unmeasured` — which is correct per L-m, but means you can't distinguish "we missed videos" from "we can't measure". No independent source (e.g., PubSubHubbub callback count) to cross-reference.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Core diff is correct. Broader codebase is well-structured with clear separation of concerns. Minor: no explicit DB transactions for multi-write ops. |
| **Frontend/UI** | **N/A** | No frontend in this package. CLI tooling is clean and well-documented. |
| **Error handling** | **94/100** | Exceptional. Every external call has timeout+retry+fallback. Every loop catches and logs without crashing. Crash recovery via `recover()`. One deduction: `queue.py` multi-statement ops aren't transactional. |
| **Security** | **93/100** | No secrets in code, parameterized queries, redirect refusal, SSRF protection via `override_allowed`, prompt injection defense. One deduction: `video_id` in yt-dlp URL not strictly validated at call site (validated elsewhere, but defense-in-depth would validate at use). |
| **Performance** | **88/100** | Bounded concurrency everywhere, bisection for ledger reads, WAL mode, overlap-capped windows. Deductions: N+1 in purge `published()` lookups, no connection pooling needed (single connection is correct for SQLite). |
| **Law compliance** | **98/100** | All 12+ laws verified compliant with line citations. No violations. 2-point deduction reserved for untestable claims (e.g., "every model role behind ONE interface" — verified structurally but runtime bypass can't be proven statically). |
| **World-class gap** | **82/100** | Core ingest+mining is production-grade. Gaps are observability/SLO related, not correctness. Would need alerting, SLO tracking, and queue-depth monitoring to match Bloomberg/Coinbase ops maturity. |
| **OVERALL** | **91/100** | |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No P0 issues in this diff. The change is safe to merge.
```

```
P1 HIGH     | Add DB transaction wrapping for set_state()+event() pairs | queue.py:160-167 | Crash between state update and event insert leaves inconsistent audit trail; wrap in explicit BEGIN/COMMIT with rollback on failure
P1 HIGH     | Validate video_id format before yt-dlp subprocess call | fetch.py:92, watch.py:130 | A malformed video_id from a compromised/compromised listing could inject yt-dlp flags (e.g., "--exec"); validate against VIDEO_ID regex at call site
```

```
P2 MEDIUM   | Add queue-depth alert for MINE_WAIT accumulation | service.py:753-779 | During extended Heimdall outage, videos queue without bound and may expire before mining; alert when MINE_WAIT count exceeds threshold or oldest wait exceeds 1h
P2 MEDIUM   | Add SLO definition and breach alert for publish_to_mined latency | stats.py:76-82 | Currently measured but not alerted; define e.g. p95 < 45 min and notify when breached
P2 MEDIUM   | Batch published() lookups in purge run_pass | purge.py:347-362 | N+1 queries (one per file) — batch into single SELECT WHERE video_id IN (...) for the unit's video_ids
P2 MEDIUM   | Add yt-dlp health canary independent of channel listing | watch.py:37-73 | RSS broke for all channels Nov 7 with no fast detection; a periodic probe of a known video would distinguish "yt-dlp broken" from "channel has no new uploads"
```

```
P3 LOW      | Remove stale comment about CONVERSATION_TPM=1.0 origin | mine.py:126-133 | Comment says "was 1.0, ruling 92's caption measure" — accurate now but will confuse future readers after further changes; link to ruling doc instead
P3 LOW      | Consider extracting is_conversation threshold to providers.json or config | mine.py:133, providers.json:98 | CONVERSATION_TPM is now 0.3 for hook pass but 1.0 for paid route — two thresholds for same concept in different files; centralize if they should stay independent (A42) or unify if orchestrator aligns them
P3 LOW      | stats.py rows_by_episode bucket boundary uses 1.0 not CONVERSATION_TPM | stats.py:121 | Feedback metric buckets at ">= 1 turn/min" but actual threshold is now 0.3 — bucket label is misleading for the new semantics; update to reflect 0.3 boundary
```

---

## SECTION 9: THE ONE THING

**Your LLM gateway (`Router`/`Health`/`Throttle`/`RoleCaps`) is the best code in this repo — now give the same engineering rigor to observability: define SLOs for discovery latency and mining latency, alert when they're breached, and make queue depth visible before videos silently expire.**

---

## SECTION 10: FINAL VERDICT

**This diff is ready to merge.** The `is_conversation` predicate correctly implements the 09:02 A36 ruling with proper handling of every edge case including Python's `bool`-is-`int` trap, the version bump and re-run mechanism are correct and cache-efficient, and no other code paths are broken. The broader codebase is production-grade with only observability gaps remaining — no correctness or security blocker exists.
