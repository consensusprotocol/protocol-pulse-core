# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 419.4 s, $0.026, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff a9a5491a)

## SECTION 1: CORRECTNESS

### Main Flow: Watch → Fetch → Mine → Hook → Check → Ledger → Adapter

**Watch (`watch.py:175-228`):** Correct. RSS canary + fallback, backoff, `first_sight` backfill logic. `poll_channel` correctly handles `not_modified` as empty entries, not error. `BACKFILL_H=72` correctly marks old videos `SEEN_OLD`.

**Fetch (`fetch.py:120-251`):** Correct. `publish_time` correctly prioritizes `release_timestamp` for live VODs (INGEST-FAIL-03). `meta_record` parity checked by test. `_store_captions` correctly respects `gate.open_for()` before download and trips breaker on `throttled`. Duplicate detection via `title_canon` + `text_fp` is sound.

**Mine (`mine.py:336-443`):** Correct. `windows()` overlap logic prevents O(n) explosion. `screened_out` via `BTC_SCREEN` is pre-model filter. `validator` is strict (L-l). `mine_video` correctly unions flags on overlapping ranges (fail-closed). Hook duration filter `4-14s` correctly drops outside.

**Ledger (`ledger.py:34-66`):** Correct. `append` with `O_APPEND` + `flock` + `fsync` + torn-tail seal is durable. `stamp` under lock guarantees `mined.at` order. `line_problems` validates before write.

**Adapter (`ledger.py:289-371`):** Correct for this diff. `effective_risk` → `eff` → exclusion on `eff` is the P1 change. `expiry` uses `min(recorded, publish+12h)` fail-closed. `offset_before` bisection with 1-day margin is correct.

**Check Loop (`service.py:418-493`):** **Mostly correct, with 2 correctness issues:**

1. **Race on `check_next` vs `check_inflight` — `service.py:475-488`:** `check_once` holds `clock_lock` while building `todo` and adding to `check_inflight`, then releases lock and submits. `check_row` on completion does `self.check_next[key] = now+600` under `clock_lock` if `len(got) < len(flags)`, then `discard(key)` from `check_inflight`. This is correct — no lost wakeup. However, if `check_row` crashes before setting `check_next`, it sets `check_next` in the `except` block too, so retry is guaranteed. **No bug.**

2. **Stale `latest` read — `service.py:466-473`:** `ledger.read()` is done *outside* any lock, then `latest` is built. Between `read()` and `check_row`'s `_append`, another `check_row` or `hook_video` could have appended a newer line for same `moment_id`. `carry_forward` in `_append` handles this — it re-reads `video_lines` under `wlock` and merges. **Correct.**

3. **BUG: `miners` dict built from ledger, not queue — `service.py:469-472`:** `miners[video_id]` collects `(backend, model)` from *every* ledger line of that video. If a video was mined by `heimdall_qwen27b` then hook-pass also by same backend, `miners` correctly contains that backend. `checkers()` then excludes any backend in that set. This is correct per spec: "never a model or back-end that mined any line of the row's video." But if a video has 2 ledger lines from different miners (re-mine), the checker exclusion grows — potentially excluding both `heimdall_glm53flash` and `heimdall_muse` if either ever mined the video. In practice, mine chain is `heimdall_qwen27b` only, so no overlap with flagcheck chain. **No bug in current config, but fragile.**

4. **BUG: `published_at` sort key can be None — `service.py:483`:** `todo.sort(key=lambda x: (x[0], x[1]))` where `x[0]` is `l["published_at"]` (string or None). If `published_at` is None, sort will compare `None` vs `str` → `TypeError` in Python 3. However, `expiry(l)` check on line 477 already filters `exp is None` (which happens when `published_at` is unparseable), so `published_at=None` rows are excluded before sort. **No bug** — but only because `expiry` gate happens first. Fragile ordering dependency.

5. **N+1 Query — `service.py:466` + `flagcheck.py:574-576`:** `ledger.read()` reads entire ledger file (could be 100k lines) every 30s in `check_once`, plus `flagcheck.py` main loop does same. No DB query N+1, but file I/O every 30s is wasteful. Acceptable at current scale.

6. **Edge: Empty ledger — `service.py:467`:** `ledger.read()` returns `([],[])` on `FileNotFoundError`. `latest={}`, `todo=[]`, `started=[]`, returns 0. Correct.

7. **Edge: `q.video()` returns None in `check_row:435`:** Handled — fallback `{"video_id": ..., "discovered_ts": clock()}` ensures `_append` can compute `since`. Correct.

### Diff-Specific Correctness

**`ledger.py:207-209` `carry_forward` for `risk_checks`:** Uses `setdefault(f,c)` — first writer wins per flag. New line's own answer wins because `carry_forward` is called with `earlier` = existing ledger lines, and new line already has its own `risk_checks` before `carry_forward` merges. `setdefault` won't overwrite existing keys. **Correct.**

**`ledger.py:214-227` `check_valid`:** Checks `flag in RELEASE_ON_CHECK`, `answer in ANSWERS`, `prompt_version == flagcheck.PROMPT_VERSION`, `model` exists and differs from `mined.model`. All 4 gates correct.

**`ledger.py:229-241` `effective_risk`:** Only moves flag to `notes` when `c["answer"] == "no"`. `yes`/`unsure`/`None` keep flag. **Correct — fail closed.**

**`flagcheck.py:305-311` `record()`:** Returns `None` for non-`yes/no/unsure` answers, so `check_row:428` `if rec is not None` correctly filters unmeasured. Correct.

**`flagcheck.py:314-318` `watcher_checkers`:** Requires `c["of"] == len(PROBES) and c["right"] == c["of"]` — 24/24. Strict. Correct per P1 spec.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag, queue, captions via store writer, ledger, coverage, A/B) | **COMPLIANT** | `watch.py:175-238`, `fetch.py:205-251`, `queue.py:73-239`, `ledger.py:34-66`, `coverage.py:43-95`, `ab.py:217-333` |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.py:667-774` Router with ≥2 backends per role, `providers.json:80-86` mine chain has 2, flagcheck has 2, `OllamaLocalBackend:441-499` checks `gpu0.held()` never acquires |
| **L-l strict schema, nothing repaired** | **COMPLIANT** | `mine.py:272-324` validator rejects on any deviation, `providers.py:845-852` re-asks with reason, never repairs, `flagcheck.py:173-200` same |
| **L-j/L-m fail closed** | **COMPLIANT** | `ledger.py:229-241` unsure/unmeasured keep flag, `flagcheck.py:314-318` failed calibration → no checking, `watch.py:160-173` unreadable optout pauses, `purge.py:298-302` unreadable delivered set stops pass |
| **L-h/L-k read as spoken, never rewrite** | **COMPLIANT** | `contract.py:115-126` `eligibility.spoken`, `fetch.py:237` `_store` via store writer, `ledger.py:162-181` verify_line checks text |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `timing: segment`, `mine.py:352-365` `duration_s: None` for segment, packager re-anchors |
| **L-u hard exclusions** | **COMPLIANT** | `ledger.py:347-348` `any(r in HARD_RISKS for r in eff)` — now on effective flags, `mine.py:23-24` HARD_RISKS defined, `ledger.py:229-241` only releases on counting "no" |
| **L-v speaker/re-upload/time** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`, `ledger.py:351-354` speaker+re-upload checks, `fetch.py:201-217` duplicate detection |
| **Secrets** | **COMPLIANT** | `providers.py:147-188` Keyring reads by name from env file, `providers.py:180-187` redact, `providers.py:289-291` no redirect |
| **SPEND FREEZE** | **COMPLIANT** | `providers.py:692-695` `frozen()` checks vendor, `providers.py:700-711` `effective()` excludes frozen, `providers.json:5-9` lists 4 vendors, `service.py:625-633` logs warning when <2 callable |
| **B1 90% tripwire NOTIFY never halt** | **COMPLIANT** | `spend.py:69-172` `CreditMeter.state()` → `write_state_notice` NOTIFY, `providers.py:700-706` `order()` moves metered last, never removes |
| **B2 nothing lost (outage vs rejected)** | **COMPLIANT** | `service.py:293-334` `_settle` distinguishes outage/rejected, `mine.py:404-405` `outage` flag, `queue.py:20-21` MINE_WAIT vs MINED_PARTIAL |
| **B3 GPU0 lease check not acquire** | **COMPLIANT** | `providers.py:461-465` `OllamaLocalBackend.enabled()` checks `g.held()`, `service.py:502-503` `release()` on idle |
| **B4 age-gate not rate-limit** | **COMPLIANT** | `watch.py:69-73` checks `AGE_GATE_MARKS` first, `fetch.py:133-136` terminal `UNAVAILABLE` |

**LAW COMPLIANCE: COMPLIANT — No violations in this diff.**

Specific to diff questions:
1. **Can adapter release without counting "no"? NO.** `ledger.py:232-233` requires `c is not None and c["answer"]=="no"`. `check_valid` requires `flag in RELEASE_ON_CHECK`, `answer in ANSWERS`, `prompt_version` match, `model` exists and differs. All gates must pass.
2. **Can it release accusation? NO.** `ledger.py:212` `RELEASE_ON_CHECK = ("imperative", "single_source_breaking")` — accusation not in tuple. `check_valid:220` returns None for accusation.
3. **Can it release non-P1 flags? NO.** Same gate — only 2 flags in `RELEASE_ON_CHECK`.

---

## SECTION 3: SECURITY

| Check | Verdict | Detail |
|-------|---------|--------|
| **SQL Injection** | **PASS** | All queries use `?` placeholders. `queue.py:92-94` `x(sql, args)` always parameterized. `set_state:155-161` validates field names against `VIDEO_FIELDS` allowlist. `set_hook:186-191` validates against `HOOK_COLUMNS`. No string interpolation of user input into SQL. |
| **Auth Bypass** | **N/A** | No HTTP routes. CLI tool + background service. `config.py:72-79` StoreGuard prevents writing to main tree without explicit env var. |
| **Rate Limiting** | **PASS** | `providers.py:609-637` Throttle per backend (2s→60s backoff), `YouTubeGate:37-73` global breaker (10→60min), `Health:542-607` circuit breaker. `service.py:CHECK_INFLIGHT=4` + `CHECK_ROWS=8` bounds flagcheck concurrency. |
| **Secrets in Code** | **PASS** | No hardcoded keys. `providers.py:147-188` reads from env file by name. `providers.py:180-187,208-214` redacts before logging. `providers.json` contains no secrets, only `key_env` names. |
| **Unvalidated Input → DB/FS/Shell** | **PASS** | `watch.py:121-123` validates channel_id format. `ledger.py:27` VIDEO_ID regex. `purge.py:53-94` strict spec validation, FORBIDDEN paths, `os.path.realpath` checks. `yt-dlp` args are constructed, not user-supplied. `urllib` no shell. |
| **Prompt Injection** | **PASS** | `mine.py:234-237` `_untrusted` replaces `<` with `‹`, `flagcheck.py:167-170` same via `mine._untrusted`. `<sentences>` / `<quote>` blocks marked untrusted. |

**SECURITY: PASS — No issues.**

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend in this diff or feature.** This is a backend ingest service (tmux process, SQLite, JSONL ledger). No HTML/CSS/JS. The "UI" is `live.json`, `coverage/*.md`, and `tools/ingest_watch.py` CLI.

If scoring is required: **N/A** — not applicable. No frontend to evaluate.

---

## SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|------|---------|--------|
| **DB rollback** | **PARTIAL** | `queue.py:77` `isolation_level=None` (autocommit). Each `x()` is one statement, auto-committed. No explicit transactions spanning multiple writes. `set_state` + `event` are two separate autocommit statements — crash between them loses the event but not the state. Acceptable for this use case (events are audit log, not consistency-critical). No `try/except` with `rollback` because autocommit has no transaction to rollback. **Not a bug, but not textbook.** |
| **API timeout+retry** | **PASS** | `providers.py:196` per-backend `timeout_s`, `providers.py:797-836` retry on `RETRY` kinds with backoff, `Throttle.hit()` on 429/overloaded, `Health` circuit breaker. Every external call has timeout. |
| **Cron failure handling** | **PASS** | No cron — all loops are `service.py:608-617` `_loop` with `try/except Exception` + `q.event("loop_error")` + `log`. Loop never crashes service. `purge.py:298-302` fail-closed on unreadable state. |
| **Memory leaks** | **PASS** | `ThreadPoolExecutor` with bounded workers, `ledger.read()` loads file into memory but bounded by `offset_before` bisection (reads tail only). `attempts` list in `ab.py`/`flagcheck.py` grows unbounded for long runs but these are one-shot CLI tools, not the long-running service. Service's `q.call()` writes to SQLite, not memory. |
| **Logging** | **PASS** | `service.py:144-152` `_log` with timestamp to stdout + file, `service.py:440-443` flagcheck results logged, `service.py:458-463` calibration logged, `queue.py:102-105` every state change is an `events` row. Sufficient for production debug. |

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What is already excellent:**
- The durability story (WAL, fsync, torn-tail seal, `carry_forward`, `StoreGuard`) is production-grade. Better than most startups.
- The provider abstraction (L-x, spend freeze, circuit breaker, throttle, spend book) is sophisticated and well-tested (237 tests).
- The fail-closed philosophy is consistently applied. This is rare and valuable.

**What is genuinely missing:**

1. **No alerting beyond STATE file top-line.** Bloomberg would have PagerDuty/OpsGenie. If Heimdall is down for 6 hours at 3am, nobody knows until they check `live.json`. The `NOTIFY.txt` + STATE notice is polling-based. A webhook/Slack notification on `OUTAGE_NOTICE_S` and `PURGE_NOTICE_S` would be material.

2. **No ledger compaction.** `moment_ledger.jsonl` is append-only forever. At ~1k moments/day × 365 days = 365k lines. `offset_before` bisection helps reads, but `ledger.read()` still parses every line in the tail. No archival/rotation. At scale, this becomes slow. A monthly rotation or SQLite migration would matter.

3. **No end-to-end latency SLO dashboard.** `stats.py` computes `publish_to_mined_min` but there's no SLO definition (e.g., "95% of videos mined within 30 min of publish"). Without an SLO, you can't tell if the system is healthy. A single `live.json` number without a threshold is just data.

4. **Coverage check is daily, not continuous.** A video published at 07:00 ET won't appear in coverage until next day 06:00 ET. For "never miss the day's most relevant content," a 24h detection lag is significant. An hourly coverage check would be more appropriate.

5. **No dead-letter queue visibility.** Videos in `mine_waiting` (outage) and `mined_partial` are retried, but there's no CLI command to list them with their retry schedule. `tools/ingest_watch.py status` shows counts but not which videos are stuck. An operator can't triage without querying SQLite directly.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Correct, well-structured, handles edge cases. Minor fragility in sort-key ordering and miners dict. |
| **Frontend/UI** | **N/A** | No frontend in scope. CLI + JSON/Markdown reports are functional and clear. |
| **Error handling** | **94/100** | Every loop has try/except, every failure is fail-closed, every state change is event-logged. Exemplary. |
| **Security** | **96/100** | No injection, no secret leaks, prompt injection mitigated, path traversal prevented. Minor: no rate limiting on `tools/ingest_watch.py` CLI itself (not needed — local only). |
| **Performance** | **85/100** | Bounded concurrency, bisection reads, WAL mode. Deductions: ledger re-read every 30s, no compaction, `attempts` list in one-shot tools. |
| **Law compliance** | **98/100** | All laws compliant. This diff precisely implements Ruling 40 P1/P2 as specified. P1 releases only on counting "no" for 2 flags, P2 re-measures accusation separately. |
| **World-class gap** | **78/100** | Core ingest is excellent. Gaps are operational (alerting, SLOs, compaction, DLQ visibility) not architectural. |
| **OVERALL** | **91/100** | Production-ready backend with strong correctness and safety guarantees. Operational polish is the remaining gap. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No P0 issues in this diff. All fail-closed paths are correct.

P1 HIGH     | Add alerting webhook for outage/purge notices | service.py:582-604, spend.py:29-52 | STATE file polling means overnight outages go unnoticed for hours; no push notification exists
P1 HIGH     | Fix sort fragility: published_at None vs str comparison | service.py:483 | Currently safe only because expiry gate runs first; reordering those two blocks would crash with TypeError
P1 HIGH     | Add ledger rotation/compaction plan | ledger.py:122-149, purge.py | Append-only JSONL grows forever; at 100k+ lines, every check_once re-reads and re-parses the tail

P2 MEDIUM   | Add DLQ visibility CLI: list mine_waiting/mined_partial with retry schedule | tools/ingest_watch.py, queue.py:172-176 | Operator cannot triage stuck videos without raw SQL; status shows counts only
P2 MEDIUM   | Make coverage check hourly instead of daily | service.py:519-539, coverage.py | 24h lag on "never miss the day's content" — video published at 07:00 ET invisible until next day 06:00
P2 MEDIUM   | Define and track publish→mined SLO (e.g. p95 < 30min) in live.json | stats.py:76-82 | Without SLO threshold, live.json numbers are data without judgment
P2 MEDIUM   | Scope miners dict to mine-role backends only | service.py:469-472 | Currently collects all backends that ever wrote a line for the video; if flagcheck backends ever mine, checker exclusion breaks
P2 MEDIUM   | Add integration test for check_valid with stale prompt_version | ledger.py:214-227 | No test verifies that old prompt_version answers are rejected after definition change

P3 LOW      | Log check calibration result to structured JSON not just text | service.py:462-463 | Text log "calibration [(...)]" is hard to parse for monitoring
P3 LOW      | Consider caching ledger.read() tail in check_once | service.py:466 | Re-reads entire ledger tail every 30s; could cache with mtime check
P3 LOW      | Add --dry-run to flagcheck --rerun | flagcheck.py:483-530 | Remeasure has no dry-run; operator cannot preview cost before spending
```

---

## SECTION 9: THE ONE THING

**Add push alerting (Slack/webhook) for outage and purge failures — your fail-closed design is excellent but nobody will know it failed until they manually check.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff correctly implements Ruling 40 P1 (dual-model agreement for 2 flags, accusation stays hard) with proper fail-closed semantics, calibration gating, and audit trails. No law violations, no security issues, no correctness bugs that would break production. The remaining gaps are operational maturity (alerting, SLOs, DLQ visibility) — important for running at scale, but not blockers for merge. **Ship it, then add alerting.**
