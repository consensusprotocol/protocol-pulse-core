# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 507.0 s, $0.032, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (diff a6921162 vs 2ec81efc)

## SECTION 1: CORRECTNESS

### Main Flow Walkthrough

**Watch → Fetch → Mine → Ledger → Coverage** is correctly wired in `service.py:873-882`. The diff under review touches only `downsignal.py` + `providers.json` (the shared Heimdall-down signal). The rest of the pipeline is unchanged and not re-audited here except for interaction points.

**Diff correctness — step by step:**

1. **Pending state shape** `downsignal.py:134` — `pending` gains `families:{}`. Correct. Old shape `{"answer","fail","drills"}` would lose per-family timestamps.

2. **`noted()`** `downsignal.py:166-186` — On `ANSWERED` (`ok`/`invalid`), clears `fail` and `families`. On failure, records `fail` once (first failure time) and `families[family]=t` once per family (first failure per family). Correct per spec: "each family once, at its first failure after the latest answer, in time order."

3. **`_family()`** `downsignal.py:188-191` — Reads `family` from `cfg["backends"][bid]`. Returns `None` if missing/empty. Correct. Familyless backends still start clock via `pending["fail"]`.

4. **`_flush()`** `downsignal.py:316-341` — Builds `notes` list: answer first, then failures. When `note_family` and `families` present, sorts families by time, prepends familyless `fail` if it predates first family failure. This guarantees clock starts at earliest failure. Correct. Falls back to single `fail` note for older modules. Correct.

5. **`_start_probe()`** `downsignal.py:343-377` — Spawns one thread per probe backend, each does `router.run(only=bid, use_cache=False)`. Joins all. `answered = True if any True else False if any False else None`. `why` joins all. `at = max(ts for True)` — latest answer time. Correct per Q1: uses latest real answer, not slowest thread's end time. `None` (not called) excluded from `at`.

6. **`probe_due` families** `downsignal.py:150-155` — Only when `hh.probe_due` signature takes `families`. Correct backward compat.

7. **`providers.json`** — Adds `family` to all heimdall backends, new `heimdall_muse_probe`, probe chain 3 entries. Correct.

### Logic Errors / Silent Failures

**No logic error in the diff.** One subtlety worth noting (not a bug):

- `downsignal.py:328-329` — `if p["fail"] < fams[0][1]` — strict `<`. If familyless failure and first family failure have identical `clock()` timestamp (same millisecond, possible under lock), the familyless note is *not* prepended. The family's note still starts the clock at the same timestamp, so no time is lost. **Benign.**

### Race Conditions

- `downsignal.py:166-186` `noted()` holds `self.lock` only for pending mutation. `self.clock()` is called *outside* lock at `172` — intentional, avoids holding lock during time call. The `t` is captured before lock, so ordering is by call time, not lock acquisition time. Under contention, two failures from different router threads could have `t1 < t2` but `t2` acquires lock first. However `families` is keyed by family name, first-write-wins (`if fam not in`), so the earlier `t` for that family is kept regardless of lock order. For `pending["fail"]`, first-write-wins too (`if is None`). **Correct.**

- `_start_probe` `downsignal.py:360-377` — `outs` dict written by probe threads without lock. Each thread writes `outs[bid]` with unique `bid` key — no torn write (CPython dict assignment is atomic for distinct keys). `asks` threads are `daemon=True`, joined before reading `outs`. **Correct.**

- `_flush` swaps `pending` under lock, then iterates outside lock. No lost notes: new notes accumulate in fresh dict.

### N+1 / Performance

- `_flush` now does N `note()` calls (1 answer + up to F families) instead of 2. F ≤ 3 currently. Each `note()` is `mode()`-like: reads/writes JSON under flock. At most 4 flock acquisitions per 5s tick. **Acceptable.** Not N+1 in DB sense.

- `_start_probe` does 3 concurrent `router.run` — each holds `sems[bid]` (1 slot) + `gsem`. Probe backends have `max_inflight=1`, so no contention with mining (which uses different backends). **Correct.**

### Edge Cases

| Edge | Handling | Verdict |
|------|----------|---------|
| Empty probe chain | `why = "" or "no back-end"` → `answered=None` → `probes_not_made` | Correct |
| All probe backends under override | `tick:209-213` skips probe entirely | Correct |
| Module missing `family` param | `_takes` returns False → `note_family=False` → old path | Correct |
| `clock()` goes backwards | `pending["fail"] < fams[0][1]` still works; module's `failing_since_utc` is wall time, not monotonic | Relies on module — acceptable |
| Probe thread exception | Caught as `None` (not asked) | Correct |
| `families` empty dict but `fail` set | Falls to `else: notes.append((False, fail, None))` | Correct |

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest) | **COMPLIANT** | Diff doesn't touch ingest; probe change improves availability. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:129` probe chain has 3 backends (qwen/glm/muse), each different family. `downsignal.py:150-155` families check ensures probe covers all families. |
| **L-l strict schema, never repaired** | **COMPLIANT** | Probe uses `_any_text` validator `downsignal.py:87-90` — still strict (empty → Invalid). |
| **L-j/L-m fail closed** | **COMPLIANT** | `downsignal.py:369-375` — `answered=None` → `probes_not_made`, never counted as answer. `downsignal.py:328` familyless failure still starts clock. |
| **L-h/L-k read as spoken** | **COMPLIANT** | Not touched. |
| **L-e word timing** | **COMPLIANT** | Not touched. |
| **L-u hard exclusions** | **COMPLIANT** | Not touched. |
| **L-v speaker/re-uploads** | **COMPLIANT** | Not touched. |
| **L-r GPU0** | **COMPLIANT** | Not touched. |
| **L-q moments first** | **COMPLIANT** | Not touched. |
| **Secrets** | **COMPLIANT** | No keys in diff. `providers.json` uses `key_env_prefix` only. |
| **SPEND FREEZE** | **COMPLIANT** | Probe backends are `heimdall` vendor, not frozen. `providers.json:6` freeze list unchanged. |
| **Ruling 87 AMENDED** | **COMPLIANT** | Implements verbatim: parallel probe, latest answer time, per-family notes, families on probe_due. |

**No violations.**

---

## SECTION 3: SECURITY

| Check | Result | Detail |
|-------|--------|--------|
| **SQL injection** | PASS | Diff has no SQL. Existing `queue.py` uses parameterized queries throughout. |
| **Auth bypass** | PASS | No HTTP routes in diff. Service is tmux-only, no exposed endpoint. |
| **Rate limiting** | PASS | Probe backends `max_inflight=1`, `timeout_s=60`, `transport_retries=0`. Three concurrent probes share `gsem` (20 global) — negligible. |
| **Secrets in code** | PASS | No secrets. `providers.json` contains only `key_env_prefix`, `base_url`, no values. |
| **Unvalidated input → DB/FS/shell** | PASS | `bid` comes from `router.chain()` (config-controlled). `family` is string from config, passed as kwarg to `note()` — no shell/FS. |
| **SSRF / redirect** | PASS | `providers.py:322-324` `_NoRedirect` still in place. `override_allowed` still gates `base_url` overrides. |
| **New attack surface** | PASS | No new network listeners. Probe threads are outbound only. |

---

## SECTION 4: FRONTEND QUALITY

**N/A — This is a backend-only change.** No UI, no HTML, no JS. `pp-ingest` is a headless ingest service (tmux, SQLite, JSONL ledger). Frontend quality is not applicable to this diff.

If scoring is required: **N/A** (no frontend in scope).

---

## SECTION 5: BACKEND QUALITY

| Area | Assessment |
|------|------------|
| **DB rollback** | PASS — `queue.py` uses `isolation_level=None` (autocommit) + `WAL` + `synchronous=FULL`. Each `x()` is atomic. No multi-statement transaction to rollback. Correct for SQLite. |
| **External API: timeout+retry+degradation** | **EXCELLENT** — Probe: `timeout_s=60`, `transport_retries=0` (fail fast, don't retry same backend), `breaker=false` (probe is breaker's evidence). Mining: `Throttle` with `Retry-After`, `Health` circuit breaker, `AllBackendsFailed.outage` vs `rejected` distinction. |
| **Cron failure handling** | PASS — No cron. `service.py:839-848` `_loop` catches `Exception`, logs, sleeps, continues. `BaseException` (SIGTERM) propagates correctly. |
| **Memory leaks** | PASS — Probe threads are `daemon=True`, joined, not leaked. `outs` dict is local to `run()`, GC'd. `pending["families"]` is bounded (≤ distinct families, ≤ 4). `_SHA` cache in `purge.py` bounded at 4096. |
| **Logging** | **EXCELLENT** — Every probe outcome logged with `why` (truncated 300 chars). `noted()` increments counters. `snapshot()` exposes `probe_families`, `failures_noted_with_family`, `counts`. Evidence file gets every `note` + `probe` + `seen` switch. |
| **Thread safety** | PASS — See race analysis above. One lock for `pending`, one for `probe_out`. No deadlock (no nested locks). |

**One minor observation (not a bug):**

- `downsignal.py:360-377` — `outs` dict is written without lock. Under CPython GIL, distinct-key assignment is safe. Under free-threaded Python (3.13t), this would need a lock. **Not actionable** — project pins 3.10.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a **narrow, high-quality fix** for a specific outage-detection bug. Judged on its own scope, it is excellent. Broader product gaps are out of scope for this diff, but for the record:

**What this diff does world-class:**
- Parallel probe with per-family tracking is exactly what Bloomberg/Coinbase would do for multi-region health checks. The "latest answer time" semantics and familyless fallback show deep understanding of distributed clock problems.
- Backward compatibility via `_takes()` introspection is textbook graceful degradation.
- Evidence file + `snapshot()` observability is production-grade.

**What would make the *overall* pp-ingest more world-class (not this diff's fault):**
- No metric emission (Prometheus/Datadog) — `live.json` polling is the only observability. A Bloomberg Terminal would have real-time alerting on `failing_since_utc` age.
- No integration test that actually runs the amended `heimdall_health.py` module end-to-end with real file locking (the tests use fakes). The two false outages that motivated this fix would have been caught by such a test.
- `providers.json` hardcodes `https://api-staging.heimdallm.com` — staging URL in production config is a risk.

**For this diff specifically: nothing material is missing.**

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **96/100** | Parallel probe, per-family notes, latest-answer clock, backward compat — all correct. -4 for no lock on `outs` dict (theoretical, not practical). |
| **Frontend/UI** | **N/A** | No frontend in scope. Headless service. |
| **Error handling** | **95/100** | Every exception path handled: `AllBackendsFailed` → `False`/`None`, generic `Exception` → `None`, `OSError` on state file → `_fail()`. Probe never crashes service. |
| **Security** | **98/100** | No new attack surface. Secrets not exposed. `override_allowed` still enforced. -2 for staging URL in production config (pre-existing). |
| **Performance** | **94/100** | 3 concurrent probes vs 1 sequential — faster detection. Bounded concurrency. Extra `note()` calls per flush are minimal. |
| **Law compliance** | **100/100** | Fully implements Ruling 87 Amended. No law violated. |
| **World-class gap** | **92/100** | For its scope, excellent. Overall product lacks metrics/alerting, but that's not this diff. |
| **OVERALL** | **96/100** | |

---

## SECTION 8: PRIORITY ACTION PLAN

| Priority | What | File:Line | Why |
|----------|------|-----------|-----|
| **P0 CRITICAL** | *None* | — | No production-breaking issue in this diff. |
| **P1 HIGH** | Add integration test with real `heimdall_health.py` file locking | `tests/ingest/test_signal.py` | The two false outages (09:16, 10:12) were caused by module/watcher interaction that fake-based unit tests didn't catch. A real-file test would prevent recurrence. |
| **P1 HIGH** | Change staging URL to production or make env-configurable | `pipeline/ingest/providers.json:19,29,38,79,88,96` | `https://api-staging.heimdallm.com` in production config — if staging goes down, production ingest stops. Pre-existing, not introduced by diff. |
| **P2 MEDIUM** | Add `threading.Lock` around `outs` dict in `_start_probe` | `pipeline/ingest/downsignal.py:360` | Distinct-key dict writes are GIL-safe on 3.10 but not on free-threaded Python. One-line fix for future-proofing. |
| **P2 MEDIUM** | Emit metric on `failing_since_utc` age | `pipeline/ingest/downsignal.py:227-273` | Currently only visible via `live.json` polling. A gauge metric would enable alerting before 15-min threshold. |
| **P3 LOW** | Log `families` in `_flush` evidence | `pipeline/ingest/downsignal.py:334` | `note()` evidence currently logs `family` per call, but no summary of which families were noted in this flush. Would aid debugging. |
| **P3 LOW** | Consider `<=` instead of `<` in familyless check | `pipeline/ingest/downsignal.py:328` | `p["fail"] < fams[0][1]` with strict `<` means equal-timestamp familyless failure is not separately noted. Benign (same time), but `<=` would be more explicit. |

---

## SECTION 9: THE ONE THING

**This is the most careful outage-detection fix I've reviewed — the parallel probe with per-family clocks and latest-answer semantics is exactly right; now add a real-file integration test so the next module/watcher interaction bug is caught before it causes a false outage in production.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff correctly implements Ruling 87 Amended: parallel per-family probes, latest-answer clock reset, backward compatibility with older modules, and no lock/thread leaks. It directly fixes the two false outages (09:16 and 10:12 ET) that motivated it. No blocking issues. Ship it.

**Before merging:** Verify the amended `heimdall_health.py` (3cf4c42f) is deployed to the builder's worktree — this watcher's fix depends on the module's `probe_result` clearing `failing_since_utc` on answered probes. Without it, the watcher's parallel probe still improves coverage but the clock won't reset on probe answers alone.