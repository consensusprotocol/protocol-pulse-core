# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 468.5 s, $0.028, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff a2a9386d → working tree)

**Scope:** Single diff in `pipeline/ingest/downsignal.py` — adoption of builder's `probe_due(..., who=)` claim. All other files are context (270 tests, full package). Review is forensic on the diff, with law-compliance on the whole package as required.

---

### SECTION 1: CORRECTNESS

#### 1.1 The diff itself — step-by-step walk

**Flow claimed:** On restart, detect if loaded `heimdall_health.probe_due` accepts `who`; if yes, pass `who="pp-ingest probe"` on every `probe_due` call so the slot is claimed under the shared flock. If no (old module 125e7381), call without `who` so no `TypeError`.

**Code:**

```python
# downsignal.py:114-118
try:
    takes_who = "who" in inspect.signature(self.hh.probe_due).parameters
except (TypeError, ValueError):
    takes_who = False
self.probe_kw = {"who": WHO + " probe"} if takes_who else {}
```

```python
# downsignal.py:170
if self._call("probe_due", now=_utc(now), **self.probe_kw):
    self._start_probe()
```

**Verdict: CORRECT.** Logic matches builder's contract exactly. Three questions asked:

**Q1: Is the signature check sound?**

Yes. `load_module()` at `downsignal.py:48-60` loads via `importlib.util.spec_from_file_location` + `exec_module` — result is a plain module-level function, not a bound method, not a C extension, not a `functools.wraps` proxy. `inspect.signature()` on a plain Python function never raises `TypeError`/`ValueError` in CPython 3.10 — but the `except` is correct defense-in-depth for:
- A future builder module that replaces `probe_due` with a `functools.partial` or C-accelerated wrapper (raises `ValueError: no signature found`).
- A broken module where `probe_due` is not callable (raises `TypeError`).

The check ` "who" in ...parameters` is exact — it tests parameter *name*, not position. Builder's diff adds `who=""` as a keyword-only-or-positional param with default, so it will appear in `parameters`. No false positive possible (no other param named `who`).

One subtlety: `inspect.signature` follows `__wrapped__` chain. If builder ever decorates `probe_due` with a decorator that doesn't use `@functools.wraps`, the signature would be the wrapper's, not the inner's. Current builder diff shows no decorator — safe. If they add one without `wraps`, `takes_who` would be `False` and we'd silently fall back to old behavior (no claim, two probes per slot). That's fail-safe, not fail-dangerous.

**Q2: Does the claim change the probe lifecycle?**

No — and this is the critical correctness claim. Walk the lifecycle:

1. **Report-first ordering (audit r87 C1-3):** `tick()` at `downsignal.py:151-176` does `_flush()` → `_report_probe()` → `mode()`/`probe_due()` → `_start_probe()` → `_seen()`. The diff does not reorder anything. `_report_probe()` still runs before `probe_due()`, so a finished probe's `probe_result` is always reported before the next slot can be claimed. Correct.

2. **`_probing()` guard:** `downsignal.py:177-182` checks `probe_thread.is_alive()` OR `probe_out is not None`. After the claim, `probe_due()` stamps `last_probe_utc` immediately under the flock. If this watcher claims but then `_start_probe()` fails to actually make the call (every probe backend skipped/frozen), no `probe_result` is ever sent. The slot is still spent — `last_probe_utc` is already stamped. Next `probe_due()` (by either prober) will return `False` until `PROBE_EVERY_S` elapses. This is **intentional per builder's spec**: "a claimer that never reports leaves the slot spent from its claim (claim-anchored)". The diff's comment at `downsignal.py:114` says this explicitly. Correct.

3. **Kept report (C2-1):** `downsignal.py:230-259` — if `probe_result` fails (shared state unreadable), the outcome is kept in `self.probe_out` while fresh (`< PROBE_EVERY_S`), then dropped. With the claim, the slot is already stamped, so the kept report will be retried within the *same* slot's window. If it succeeds, `probe_result` re-stamps `last_probe_utc` (answer-anchored, per builder). If it's dropped as stale, the slot was already spent from the claim — no double-probe. Correct.

4. **No new race:** `probe_kw` is set once in `__init__` (single-threaded construction) and only read in `tick()` (single signal thread). No concurrent mutation. `self.probe_kw` is a plain dict, never mutated after init. Correct.

**Q3: Any path where `who` makes a call fail?**

No. Exhaustive enumeration:

| Module version | `takes_who` | `probe_kw` | Call | Result |
|---|---|---|---|---|
| 11ed255f (new) | `True` | `{"who": "pp-ingest probe"}` | `probe_due(path, now, who="pp-ingest probe")` | Claims slot, stamps `last_probe_by` |
| 125e7381 (old) | `False` | `{}` | `probe_due(path, now)` | Old behavior, no claim |
| Broken (no sig) | `False` (except) | `{}` | `probe_due(path, now)` | Old behavior, safe fallback |
| Missing module | N/A (`self.hh is None`) | `{}` | `tick()` returns at line 153-154 | No call at all |

No path raises `TypeError: got an unexpected keyword argument 'who'`. The `except (TypeError, ValueError)` covers the only way `inspect.signature` itself could fail. The `_call` wrapper at `downsignal.py:184-194` catches any exception from the actual `probe_due` invocation and routes to `_fail()` — so even an unforeseen `TypeError` would be caught and reported as "not read", never crash the signal loop.

#### 1.2 Whole-package correctness (pre-existing, not introduced by diff)

No new issues introduced. Pre-existing items noted for completeness (not caused by this diff):

- `downsignal.py:184-194` `_call` catches `Exception` but not `BaseException` — a `KeyboardInterrupt`/`SystemExit` inside `probe_due` would propagate and kill the signal thread. Pre-existing, low risk (module is simple file I/O).
- `providers.py:839` `transport_retries` default comes from `cfg["throttle"]["transport_retries"]` — if `throttle` key missing, `KeyError`. Pre-existing, covered by `validate_config`.
- `queue.py:177` `due()` orders by `COALESCE(published_ts, listing_ts, discovered_ts) DESC` — newest first. Correct per spec "newest uploads first".

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|---|---|---|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, re-upload, Shorts/live, durable queue, captions via store writer, staging copy, bounded concurrency, spend cap, ledger, adapter, coverage, blind A/B) | **COMPLIANT** | Full implementation across `watch.py`, `fetch.py`, `queue.py`, `mine.py`, `ledger.py`, `coverage.py`, `ab.py`, `service.py`. This diff does not touch any BUILD path. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:101-111` every role has ≥2 backends; `providers.py:136-143` enforces at load; `providers.py:146-148` `frozen_vendors` + `available()` ensures no single vendor is required. Diff preserves this — probe role still has 2 backends (`heimdall_qwen27b_probe`, `heimdall_glm53flash_probe`), both `heimdall` vendor. |
| **L-l strict schema, nothing repaired** | **COMPLIANT** | `mine.py:332-384` `validator()` raises `Invalid` on any deviation; `providers.py:879-886` re-prompts with rejection reason, never repairs. `flagcheck.py:173-200` same. Diff does not touch validation. |
| **L-j / L-m fail closed** | **COMPLIANT** | `ledger.py:289-371` `best_unused_moments` drops on any unmeasured field; `coverage.py:62` unmeasured channels never counted; `purge.py:298-302` any `problems` stops deletion. Diff's `except (TypeError, ValueError): takes_who=False` is fail-closed (falls back to old behavior, never claims incorrectly). |
| **L-h / L-k read as spoken, never rewrite** | **COMPLIANT** | `contract.py:115-126` `sentences()` uses `eligibility.spoken`; `fetch.py:205-251` `_store_captions` uses `transcript_store` writer, never rewrites. Diff untouched. |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `source_for` sets `timing` correctly; `mine.py:412-413` `duration_s` null for `segment` timing. Diff untouched. |
| **L-u hard exclusions** | **COMPLIANT** | `ledger.py:347-348` `HARD_RISKS` check in adapter; `mine.py:23-24` `HARD_RISKS` defined. Diff untouched. |
| **L-v speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`; `fetch.py:186-191,242-247` duplicate detection; `ledger.py:353-354` re-upload exclusion. Diff untouched. |
| **Secrets (keys by name from env file, never logged)** | **COMPLIANT** | `providers.py:162-203` `Keyring` reads by name; `providers.py:195-202,223-229,854-856` redaction on every error path; `providers.py:304-306` `_NoRedirect` prevents key following redirect. Diff does not handle secrets. |
| **SPEND FREEZE (05:30 ET Nov 12)** | **COMPLIANT** | `providers.json:5-9` freeze list; `providers.py:719-722` `frozen()` check in `available()` and `_try()`; `providers.py:832-833` double-lock in `_try`. Diff's probe backends are `heimdall` vendor — not frozen. No bypass. |
| **B1-B4 integrator findings** | **COMPLIANT** | B1 (tripwire notifies, never halts): `spend.py:162-183` + `providers.py:727-733`. B2 (outage vs rejected): `service.py:304-345`. B3 (GPU0 lease check not acquisition): `providers.py:476-487`. B4 (age-gate not rate-limit): `watch.py:25-27,69-73` + `fetch.py:132-136`. Diff does not regress any. |

**Overall Law Compliance: COMPLIANT — no violations introduced.**

---

### SECTION 3: SECURITY

| Check | Verdict | Detail |
|---|---|---|
| **SQL injection** | **PASS** | All queries use parameterized `?` placeholders. `queue.py:94-96` `x(sql, args)` passes `args` to `sqlite3.execute`. No string interpolation of user input into SQL. `queue.py:168-171` `claim()` builds `IN (?,...)` with `",".join("?" * len(from_states))` — count is parameterized, values are parameterized. No ORM `filter()` with raw input. |
| **Authentication bypass** | **N/A** | No HTTP routes, no auth layer — this is a backend ingest service (tmux process, no web server). `config.py:72-79` `StoreGuard` prevents writing to main tree without explicit env flag. |
| **Rate limiting gaps** | **PASS** | `providers.py:636-664` `Throttle` with `first_s`/`max_s` + `Retry-After` honoring; `watch.py:37-73` `YouTubeGate` with breaker (10/20/40/60 min) + `YTDLP_CONCURRENCY=3`; `providers.py:704-707` global `max_inflight=20`. Diff's probe has `max_inflight=1` per backend, `timeout_s=60` — minimal blast radius. |
| **Secrets in code** | **PASS** | No hardcoded keys. `providers.json:10` `env_file` points to `/home/ultron/protocol_pulse/.env` (gitignored). `providers.py:162-203` `Keyring` reads by name/prefix. `providers.py:195-202` `redact()` replaces all key values ≥8 chars. `providers.py:854-856` redacts `BackendError.detail` and `raw` before recording. Diff introduces no secret handling. |
| **Unvalidated input → DB/filesystem/shell** | **PASS** | `watch.py:121-124` `uploads_url` validates `cid` format (`UC` + 24 chars) before interpolating into URL. `fetch.py:92-93` `gate.run` uses `subprocess` via `transcript_store._ytdlp` with argument list (no shell). `ledger.py:27` `VIDEO_ID` regex validates before path join. `purge.py:53-77` `load_spec` strictly validates all paths are absolute and outside `FORBIDDEN`. Diff's `who` value is a constant string `"pp-ingest probe"` — no user input. |
| **New attack surface from diff** | **NONE** | `inspect.signature` reads function metadata only — no I/O, no code execution. `who` is a hardcoded constant. No new filesystem, network, or DB access. |

---

### SECTION 4: FRONTEND QUALITY

**N/A — No frontend.** This is a pure backend ingest service. No HTML, CSS, JS, or UI components. The "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` markdown reports. Both are functional and correct for their purpose.

If this section must be scored: the CLI help text at `tools/ingest_watch.py:2-23` is clear, `status`/`coverage`/`moments`/`handoff`/`ab`/`flagcheck`/`hooks`/`purge` subcommands are well-documented. No issues.

---

### SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|---|---|---|
| **DB operations: try/except + rollback** | **GOOD** | `queue.py:79-92` uses `isolation_level=None` (autocommit) + `WAL` + `synchronous=FULL`. Each `x()` is a single statement — no multi-statement transactions needing rollback. `claim()` at `queue.py:167-172` is atomic single `UPDATE ... WHERE state IN (...)` with `rowcount` check — correct for concurrent claims. No explicit rollback needed by design. |
| **External API calls: timeout + retry + degradation** | **EXCELLENT** | `providers.py:211-212` per-backend `timeout_s`; `providers.py:636-664` `Throttle` with backoff; `providers.py:839-868` `transport_retries` with `Retry-After`; `providers.py:557-622` `Health` circuit breaker (consecutive, fraction, slow median). `watch.py:37-73` `YouTubeGate` breaker. Diff's probe has `timeout_s=60`, `transport_retries=0`, `breaker=false` — correct for a lightweight probe that must not queue or learn. |
| **Cron/long-running: failure without crash** | **EXCELLENT** | `service.py:649-658` `_loop` wraps `fn()` in `try/except Exception`, logs `loop_error` event, continues. `service.py:695-706` signal handling for `SIGINT`/`SIGTERM`. Diff's `_call` at `downsignal.py:184-194` catches `Exception` from `probe_due` and routes to `_fail()` — signal loop never crashes from a probe_due failure. |
| **Memory leaks** | **PASS** | `service.py:104-108` bounded `ThreadPoolExecutor`s (20/3/2/4/4 workers). `queue.py:79` single SQLite connection. `providers.py:563` `Health.events` capped at 50. No per-request large allocations without cleanup. Diff adds one small dict `probe_kw` (2 keys) — negligible. |
| **Logging** | **EXCELLENT** | `service.py:154-162` `_log` with timestamp + file; `service.py:163-171` `_on_attempt` logs every attempt to `replies_log/YYYY-MM-DD.jsonl`; `service.py:104-107` `events` table for every state change. Diff's `snapshot()` at `downsignal.py:353-361` now reports `probe_claimed_as` — improves debuggability (visible in `live.json` whether claim is active). |

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a **backend ingest pipeline**, not a user-facing product. "World-class" here means: would this pass review at a top-tier infra team?

**What is already excellent (explicitly):**

- **Provider abstraction** (`providers.py` 908 lines): The `Router`/`Backend`/`Health`/`Throttle`/`SpendBook` design is genuinely impressive. Bounded concurrency, queue-aware backoff, circuit breaker with three open conditions, spend freeze, runtime URL overrides, reply caching — this is production-grade multi-vendor LLM orchestration. Most teams would have a single `openai.ChatCompletion.create()` call.
- **Ledger durability** (`ledger.py`): `O_APPEND` + `flock` + `fsync` + torn-tail sealing + `stamp()` under lock for ordering + bisection read. This is careful systems programming.
- **Purge safety** (`purge.py`): The delivered-set protection, `/proc` open-file check, idle grace period, and fail-closed on any unreadable state is paranoid in the right way.
- **Test coverage**: 270 tests across 8 test files, including property-based ledger ordering tests, outage drill tests, and signal integration tests. Rare for a pipeline service.

**What would make this materially better:**

1. **No metrics/observability beyond log files.** Bloomberg/Coinbase would have Prometheus metrics or at minimum structured JSON logs with trace IDs. Currently `service.log` is plaintext with `print()`. A `videos_mined` counter that resets on restart is not the same as a monotonic counter. **Impact: MEDIUM** — debugging production requires `grep`, not dashboards.

2. **No alerting on data quality.** The coverage check (`coverage.py`) runs daily and writes a markdown file. Nobody is paged if coverage drops below 80%. A world-class pipeline would have a dead-man's switch: "if no videos mined in 2 hours during market hours, alert". **Impact: MEDIUM** — silent failures are the most dangerous.

3. **yt-dlp as subprocess is fragile.** Every YouTube interaction shells to `yt-dlp` via `transcript_store._ytdlp`. Version skew, cookie expiry, and YouTube HTML changes break this silently. A world-class system would have a fallback or at minimum version pinning with CI that tests against live YouTube weekly. **Impact: LOW** — mitigated by RSS-first + playlist fallback + breaker, but still a single point of failure.

4. **No schema migration for SQLite.** `queue.py:86-92` does `ALTER TABLE ADD COLUMN` for new columns but has no version tracking. If a column type needs to change, there's no migration path. At current scale (64 channels, ~100 videos/day) this is fine. **Impact: LOW.**

**This diff specifically:** The probe claim is a textbook example of cross-team coordination done right — builder commits, watcher adopts, both handle the old version gracefully, tests pin the contract. Nothing missing.

---

### SECTION 7: SCORES

| Dimension | Score | Rationale |
|---|---|---|
| **Backend logic** | **96/100** | Diff is correct, minimal, well-tested. Whole package is strong. -4 for no `BaseException` handling in `_call` (pre-existing). |
| **Frontend/UI** | **N/A** | No frontend. CLI is functional. Not scored. |
| **Error handling** | **94/100** | Diff handles all failure modes (missing module, old module, broken signature, TypeError on call). Whole package has excellent fail-closed design. -6 for `_call` not catching `BaseException` (signal thread could die on `KeyboardInterrupt` inside module). |
| **Security** | **98/100** | No injection, no secret leakage, no new attack surface. -2 for `providers.py:328-330` building `Authorization: Bearer <key>` header as a string that could appear in a traceback if `urllib` raises before redaction (mitigated by `redact()` on `BackendError` but not on raw `urllib` exceptions that bypass `BackendError`). |
| **Performance** | **97/100** | Diff adds one `inspect.signature` call at init (microseconds, once) and one dict unpack per 30s tick. Zero hot-path cost. Whole package has bounded concurrency, bisection reads, WAL mode. -3 for `stats.py:86-87` `SELECT SUM(COALESCE(cost_usd,0)) FROM calls GROUP BY backend` on every `live()` call (every 60s) — full table scan, will degrade at high volume. |
| **Law compliance** | **100/100** | No violations. All laws verified with line citations. |
| **World-class gap** | **88/100** | Core engineering is excellent. Gaps are observability and alerting, not correctness. |
| **OVERALL** | **96/100** | |

---

### SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | This diff introduces no P0 issues. No production breakage possible.
P1 HIGH     | (none) | — | No P1 issues in this diff. Whole package has no P1 open items from this change.
P2 MEDIUM   | Add BaseException guard in DownSignal._call | downsignal.py:184 | _call catches Exception but not BaseException; a KeyboardInterrupt/SystemExit inside heimdall_health.py would kill the signal thread silently, leaving mode stale until restart. Fix: catch BaseException, re-raise only KeyboardInterrupt/SystemExit after cleanup, or at minimum log and set _fail().
P2 MEDIUM   | Pin yt-dlp version + CI smoke test | pipeline/transcript_store.py + CI | yt-dlp breaks on YouTube HTML changes with no warning; RSS 404→200 flip on 2026-11-07 shows YouTube behavior is non-stationary. Pin version, add weekly live smoke test against 1-2 channels.
P3 LOW      | Cache stats.py all-time spend query | stats.py:86-87 | SELECT SUM over entire calls table every 60s is O(n) with no index on cost_usd; add daily accumulator or materialized view when calls exceeds ~100k rows. Currently ~1k/day, so not urgent.
P3 LOW      | Structured JSON logging for service.log | service.py:154-162 | Plaintext log requires grep; structured JSON with level/trace_id would enable log aggregation. Low priority for single-process service.
P3 LOW      | Consider @functools.wraps audit for builder module | (builder side) | If builder ever decorates probe_due without wraps, inspect.signature will see wrapper's params, not inner's — takes_who would be False, silently disabling claims. Builder should ensure probe_due is never wrapped without wraps, or expose a HAS_WHO constant.
```

---

### SECTION 9: THE ONE THING

**This is a model cross-team contract adoption — the diff is 10 lines, handles both module versions, is fully tested, and changes nothing it shouldn't; ship it.**

---

### SECTION 10: FINAL VERDICT

**Ready for production. Deploy on next restart.** The diff is minimal, correct, and fail-safe in every path — old module, new module, broken module, and missing module all handled. No law violations, no security issues, no performance impact. The only pre-existing improvement worth scheduling is a `BaseException` guard in `_call`, but it is not a blocker for this change.
