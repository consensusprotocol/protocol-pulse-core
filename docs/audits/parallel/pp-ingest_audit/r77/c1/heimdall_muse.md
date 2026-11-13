# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 554.1 s, $0.026, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (expiry + purge diff)

**Scope:** `git diff a462afda` — 7 files changed, 2 new files (`purge.json`, `purge.py`), ~500 LOC added. Review is of the *diff* plus its interaction with the existing `pp-ingest` package.

---

## SECTION 1: CORRECTNESS

### 1.1 Main flow: expiry

**Claim:** Every moment expires at `published_at + 12h`, adapter never returns expired.

**Walkthrough:**

1. `mine.py:258` — `build_line` writes `expires_at = config.expires_at(published_at)` at mining time. Correct.
2. `config.py:62-65` — `expires_at()` returns `aware(published_at) + 12h` or `None` if unparseable/naive. Correct.
3. `ledger.py:213-219` — `expiry(l)` computes `min(recorded expires_at, published_at+12h)`. This is the **fail-closed** design: a later `expires_at` cannot extend life, a missing field falls back to `published_at+12h`. Correct.
4. `ledger.py:269-270` — `if exp is not None and now >= exp: drop("expired")`. Checked **first**, before delivered/optout/hard-flags. Correct per spec.
5. `ledger.py:222-223` — `horizon_h` default changed from `72` to `config.EXPIRY_H (12)`. `cutoff = min(since, now-12h)-1day`. This is correct for the new 12h window but is a **semantic change** — see §1.3.

**Verdict on expiry: CORRECT.** No path returns a moment `>=12h` after publish. Verified:
- Row without `expires_at` → `expiry()` uses `published_at+12h` → still expires. ✓
- Row with `expires_at` in future (tampered/late) → `min()` picks `published_at+12h` → still expires. ✓
- Row with `published_at=None` → `expiry()=None` → falls through to `pub is None` check at `ledger.py:273` → dropped as "publish time not measured". ✓
- Re-mined row (partial retry) → new `expires_at` written, but `min()` still caps at `published_at+12h`. ✓

### 1.2 Main flow: purge

**Walkthrough of `purge.py:run_pass`:**

1. `delivered()` collects delivered video IDs from runs with delivery markers + scorer pins + references. Any unreadable delivered set → `problems` → entire pass refused (`rep["refused"]`, `freed_bytes=0`). **Fail-closed. Correct.**
2. `open_paths()` reads `/proc/*/fd`. If `/proc` unreadable → `problems` → refused. **Fail-closed. Correct.**
3. Per-target loop: `glob(units)` → per-unit `newest_mtime` → per-file checks in order:
   - `lstat` + `S_ISREG` → symlink never followed/deleted ✓
   - `realpath` inside `unit_real` + outside `protect` + outside `FORBIDDEN` ✓
   - `by_video`: `_vid_of` → delivered check → `published()` → `pub > cutoff` check ✓
   - `abandoned`: `newest > abandoned_after (12h)` → keep ✓
   - `newest > busy_after (2h)` → keep ✓
   - `rp in opened` → keep ✓
   - `os.unlink` ✓

**Verdict on purge: CORRECT with one minor concern** (see §1.4).

### 1.3 Horizon change — potential regression

`ledger.py:223` changes default `horizon_h` from `72` to `12`. The adapter's docstring previously said "72h window". Now:

```python
cutoff = min(since, now - 12h) - 1day
```

If a caller passes `since = now - 48h` (e.g., a packager that was down for 2 days), the old code would return moments from the last 72h. The new code returns only last 12h. **This is intentional per ruling 76** ("a moment is usable only within 12h"), but any caller that relied on `horizon_h=72` default without passing it explicitly will silently get fewer results. The `tools/ingest_watch.py:92` `cmd_moments` passes no `horizon_h`, so it now defaults to 12h — which is correct per the ruling, but is a **breaking API change** that should be called out in release notes.

**Severity: P2 — intentional but breaking.**

### 1.4 Purge: `newest_mtime` walks entire unit

`purge.py:215-223` — `newest_mtime()` does `os.walk(unit)` over every file in the unit to find the newest mtime. For a run with many files (sources + transcripts + qa + out), this is O(files) per unit, called once per unit per pass. With `every_s=600` and potentially dozens of runs, this is wasteful but not incorrect. The `busy_after` check (2h grace) means a recently-touched run is kept — correct.

**No bug, but inefficient. P3.**

### 1.5 Purge: `abandoned` mode has no per-file age check

`purge.py:315-317`:
```python
elif newest > abandoned_after:
    keep("a word-pass cycle's, touched under 12 h ago", size)
    continue
```

For `word_pass_temp` (`mode=abandoned`), the check is on `newest_mtime(unit)` — the directory's newest file — not the individual file's mtime. If `/tmp/word_pass_abc/` has one file touched 1h ago and another untouched for 20h, **both are kept** because `newest` is 1h ago. This is conservative (keeps too much, never deletes too much) — **fail-closed, correct**, but means abandoned temp dirs with one active file retain all files longer than necessary.

**Not a bug. P3.**

### 1.6 Race: `os.unlink` after `lstat` (TOCTOU)

`purge.py:287-330` — `lstat` checks `S_ISREG`, then `realpath` checks, then `os.unlink(p)`. Between `lstat` and `unlink`, an attacker (or concurrent process) could replace the file with a symlink. However:
- `os.unlink` on a symlink unlinks the symlink itself, not its target (POSIX). So no deletion outside target.
- The `realpath` check already passed, but TOCTOU could theoretically bypass it if the file is swapped after `realpath` but before `unlink`. In practice, `os.unlink(p)` with path `p` (not `rp`) unlinks whatever `p` now points to — if `p` was replaced with a symlink, it unlinks the symlink entry, not the target.

**Not exploitable. Correct.**

### 1.7 `config.aware` vs `ledger._aware` duplication

`config.py:53-59` defines `aware()`, `ledger.py:205-210` defines `_aware()` with identical logic. `ledger.expiry()` calls `config.aware()` while `ledger.best_unused_moments` uses `ledger._aware()`. Both handle `Z` suffix and naive datetimes identically. Duplication is harmless but should be consolidated.

**P3.**

### 1.8 `service.py:purge_once` — `every_s` from spec

`service.py:425`:
```python
("purge", self.purge_once, float((self.purge_spec or {}).get("every_s", 600)))
```

If `purge_spec is None` (refused spec), `every_s` defaults to 600, so `purge_once` is called every 600s even though it immediately returns `None` with a log line. This is intentional ("says so every pass" per `service.py:91-92` comment) but generates a log line every 10 minutes forever for a bad spec. Minor noise.

**P3.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, re-upload, Shorts/live, durable queue, same store format, bounded concurrency, spend cap, append-only ledger, adapter, coverage, A/B) | **COMPLIANT** | Diff does not touch ingest/watch/fetch/mine/coverage paths. Purge is additive. No BUILD requirement weakened. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `purge.py` has no model calls. `ledger.py` expiry is deterministic (no model). No vendor/model names added outside `purge.json` (which names no models). |
| **L-l strict schema, nothing repaired** | **COMPLIANT** | `purge.py:load_spec` is strict — any bad field raises `SpecError`, entire pass refused. `ledger.py:expiry` never repairs a bad timestamp, returns `None` → fail-closed. |
| **L-j / L-m fail closed; unmeasured ≠ pass** | **COMPLIANT** | `purge.py:253-257` — any `problems` (unreadable delivered set, unreadable `/proc`) → `refused`, `freed_bytes=0`, nothing deleted. `ledger.py:273` — `pub is None` → dropped. `config.py:53-59` — naive datetime → `None` → not usable. |
| **L-h / L-k read as spoken, never rewrite** | **COMPLIANT** | Diff does not touch `transcript_store` or `eligibility.spoken`. `purge.py` never touches transcript files (only `media_ext` files). |
| **L-e word timing at cut time** | **COMPLIANT** | No change to timing logic. |
| **L-u hard exclusions** | **COMPLIANT** | `ledger.py:279-280` — `HARD_RISKS` check unchanged, still before `return`. Purge does not touch ledger. |
| **L-v speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `ledger.py:283-286` — speaker/re-upload checks unchanged. Expiry adds a *new* time-sensitive exclusion (12h) — strengthens L-v, does not weaken. |
| **Secrets (keys by name from env file, never logged)** | **COMPLIANT** | No new key handling. `purge.py` reads no secrets. |
| **SPEND FREEZE** | **COMPLIANT** | No new provider calls. `purge.py` and `ledger.py` expiry are free (no API). |
| **B1-B4 integrator findings** | **COMPLIANT** | B1 (tripwire notifies, never halts) — untouched. B2 (partial/outage handling) — `ledger.py` still counts partial correctly; purge does not touch queue states. B3 (GPU0 lease) — untouched. B4 (age-gate vs rate-limit) — untouched. |

**All laws: COMPLIANT. No violations.**

---

## SECTION 3: SECURITY

### 3.1 SQL injection

No new SQL. `purge.py` has zero DB queries. `ledger.py` expiry adds no queries. Existing `queue.py` uses parameterized queries throughout (`?` placeholders). **No issue.**

### 3.2 Authentication / authorization

No new routes or endpoints. `purge.py` is called only from `service.py:purge_once` (internal loop) and `tools/ingest_watch.py:cmd_purge` (CLI, requires local filesystem access). No auth bypass.

### 3.3 Rate limiting

Not applicable to purge/ledger. Existing `YouTubeGate` and `providers.Router` rate limiting untouched.

### 3.4 Secrets in code

`purge.json` contains only filesystem paths and timing constants. No keys, tokens, or credentials. `purge.py` reads no env vars. **Clean.**

### 3.5 Unvalidated input → filesystem/shell

**`purge.json` → filesystem deletion — the critical attack surface:**

| Check | Status | Line |
|-------|--------|------|
| Schema must be `pp.purge/1` | ✓ | `purge.py:57-58` |
| `expiry_h` must equal `config.EXPIRY_H` | ✓ | `purge.py:59-60` |
| `every_s`/`active_grace_s` positive | ✓ | `purge.py:61-63` |
| `media_ext` must be `.lowercase` | ✓ | `purge.py:64-67` |
| `mode` must be `by_video` or `abandoned` | ✓ | `purge.py:69-70` |
| `units` must be absolute, no `..`, no `FORBIDDEN` | ✓ | `purge.py:71-73` |
| `delivered` must have all 7 keys | ✓ | `purge.py:74-79` |
| `FORBIDDEN` covers `/references/`, `/tests/`, `/.git/`, `/data/editorial/`, `/data/moments_pins/`, `/out/`, `/qa/`, `/VERIFY/`, `/vo_audio/`, `/transcripts/` | ✓ | `purge.py:41-42` |
| Symlink units skipped | ✓ | `purge.py:275` |
| Non-regular files skipped | ✓ | `purge.py:292-294` |
| `realpath` inside `unit_real` | ✓ | `purge.py:296` |
| `realpath` outside `protect` (pp-ingest store) | ✓ | `purge.py:296` |
| `realpath` outside `FORBIDDEN` | ✓ | `purge.py:296` |
| `glob` injection via `..` in `units`/`files` | ✓ blocked | `purge.py:72` |
| Shell injection | N/A | No `subprocess`/`os.system` in purge |

**One gap:** `purge.py:72` checks `any(b in where + "/" for b in FORBIDDEN)` where `where = f"{units}/{files}"`. This is a substring check. A path like `/home/ultron/protocol_pulse/runs_evil/data/editorial/` would contain `/data/editorial/` as substring and be correctly blocked. But a path like `/home/ultron/protocol_pulse/runs/*` with `files=sources/*` gives `where="/home/ultron/protocol_pulse/runs/*/sources/*"` — no FORBIDDEN substring, correctly allowed. **The check is sound for the current spec but is substring-based rather than path-component-based.** A crafted `units` like `/tmp/foo/references/bar` would be blocked (contains `/references/`), which is correct. No bypass found.

**Verdict: No security vulnerabilities in the diff.**

### 3.6 One minor concern: `spec["publish_time"]["main_store_meta"]` format string

`purge.py:187`:
```python
spec["publish_time"]["main_store_meta"].format(video_id=vid)
```

`vid` is validated by `VIDEO_ID` regex (`^[A-Za-z0-9_-]{11}$`), so no path traversal via `vid`. The format string itself comes from `purge.json` — if an attacker can write `purge.json`, they already have filesystem write access and don't need this vector. **Not a vulnerability**, but worth noting that `purge.json` is a trusted config file (same trust level as `providers.json`).

---

## SECTION 4: FRONTEND QUALITY

**Not applicable.** This is a backend-only change (ingest pipeline, no UI). No HTML, CSS, JS, or frontend components modified.

| Criterion | Assessment |
|-----------|-----------|
| UI matches spec | N/A — no UI |
| Hardcoded values | N/A |
| Mobile viewport | N/A |
| JS errors | N/A |
| Loading/error/empty states | N/A |
| World-class look | N/A |

---

## SECTION 5: BACKEND QUALITY

### 5.1 DB operations: try/except with rollback

`purge.py` does not use the DB directly except via `q.video()` (read-only) and `q.kv_get`/`kv_set` in `service.py:purge_once`. The `queue.py` uses `isolation_level=None` (autocommit) with `WAL` mode — each statement is atomic. No explicit transactions to rollback, which is correct for SQLite autocommit. No new write patterns that need rollback.

**No issue.**

### 5.2 External API calls: timeout + retry + graceful degradation

No new external API calls. `purge.py` is entirely local filesystem + `/proc`. `ledger.py` expiry is pure computation. Existing API call patterns (yt-dlp, providers) untouched.

### 5.3 Cron job / recurring purge

The purge runs as `service.py:425` — a thread in the existing watcher loop, every `every_s=600s`, via `Service._loop` which has:

```python
try: fn()
except Exception as e:
    self.q.event("loop_error", ...)
    self.log(f"{name} loop error: ...")
delay = every + jitter - elapsed
self.stop.wait(max(1.0, delay))
```

This means:
- A crash in `purge_once` is caught, logged, and the loop continues. ✓
- `purge.py:run_pass` itself has `try/finally` for the `purge.lock` flock. ✓
- `load_spec` failure at startup sets `purge_spec=None`, and every subsequent `purge_once` logs and returns `None` without crashing. ✓
- No cron — runs in watcher's own loop as required by ruling 77. ✓

**Excellent. Handles failure without crashing the service.**

### 5.4 Memory leaks

`purge.py:run_pass` allocates `cache={}` (video_id → publish time), `vids_delivered` set, `opened` set (all open file paths). All are local to `run_pass` and freed on return. `glob.glob` results are iterated, not retained. No per-request accumulation.

`ledger.py:expiry` is called once per moment in `best_unused_moments` — O(1) per moment, no accumulation.

**No leaks.**

### 5.5 Logging

| Event | Logged | Line |
|-------|--------|------|
| Purge spec refused at startup | `purge_error` stored, logged every pass | `service.py:91-92,350` |
| Every deletion | `deleted.jsonl` with path, bytes, video_id, age | `purge.py:334-338` |
| Every pass | `passes.jsonl` with deleted/kept/problems | `purge.py:343` |
| Pass summary | `service.py` log when `freed_bytes` or `refused` | `service.py:361-362` |
| `purge_last` + `purge_freed_total` in `live.json` | `service.py:353-357`, `stats.py:102-108` | ✓ |
| Expiry exclusions | `report["excluded"]["expired ..."]` count | `ledger.py:270` |
| `expiry_h` in report | `report["expiry_h"]` | `ledger.py:245` |

**Logging is thorough. Every deletion is auditable, every pass is recorded, live.json exposes last pass.**

One gap: `purge.py:open_paths` silently skips unreadable `/proc/<pid>/fd` directories (line 204-205: `continue`). If many PIDs have unreadable fd dirs (e.g., permission change), `opened` will be incomplete but no warning is logged — files held open by those processes could be deleted. However, the `newest_mtime > busy_after` check (2h grace) provides a second layer of protection for active units. **P2 — should log when fd dirs are skipped.**

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

### What is already excellent

- **Fail-closed purge design** — every uncertainty (unreadable delivered set, unreadable `/proc`, unknown publish time, active unit, open file) keeps the file. This is the correct posture for a deletion system. Bloomberg would do the same.
- **Append-only ledger with expiry as filter, not deletion** — expired rows stay as receipts for dedup. This is the right data architecture. Coinbase's event sourcing works identically.
- **`min(expires_at, published_at+12h)` — tamper-proof expiry** — a later `expires_at` cannot extend life. This is a subtle but important correctness property.
- **Audit trail** — every deletion in `deleted.jsonl`, every pass in `passes.jsonl`, live.json integration. Production-grade observability.

### What is genuinely missing

**1. No alerting on purge failures (P1)**
If `purge.json` is malformed or `/proc` becomes unreadable, every pass logs `refused` but no alert fires. The `STATE` file notice system (`spend.py:write_state_notice`) exists for spend/outage — purge should use it too. An operator could miss that 7GB of expired media is accumulating because the purge silently stopped.

**2. No dry-run diff in live.json (P2)**
`live.json` reports `purge.last_pass` and `freed_total_bytes`, but not `would_delete` count from the last dry-run or `kept` breakdown. An operator checking `live.json` cannot tell if the purge is keeping files for the right reasons without reading `passes.jsonl`.

**3. No integration test for the 12h boundary (P2)**
The test inventory shows `test_ledger_coverage.py::TestAdapter::test_a_moment_expires_12_h_after_its_video_was_published_and_its_row_stays` — so the happy path is tested. But there is no test for: moment at exactly `published_at + 12h` (boundary: `now >= exp` means expired at exactly 12h — is that intended? The spec says "more than 12h old" for purge but "within 12h" for ledger. At exactly 12h, `now >= exp` is `True` → expired. This is correct per "within 12h" but the purge uses `pub > cutoff` where `cutoff = now - 12h`, so at exactly 12h `pub == cutoff` → `pub > cutoff` is `False` → deleted. Consistent, but the boundary semantics should be explicitly tested and documented.

**4. Purge does not handle clock skew (P3)**
If the system clock jumps backward (NTP correction), `now - 12h` could be in the future relative to `published_at` values written with the old clock. Moments could appear unexpired when they should be expired, or purge could delete files it shouldn't. This is inherent to wall-clock expiry and acceptable for this use case, but worth a comment.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Expiry and purge are correct, fail-closed, well-structured. -8 for horizon default change (breaking), `newest_mtime` inefficiency, and `aware` duplication. |
| **Frontend/UI** | **N/A** | No frontend in this diff. No score applicable. |
| **Error handling** | **94/100** | Every failure mode handled: bad spec → refused, unreadable delivered set → refused, unreadable `/proc` → refused, unknown publish time → kept, active unit → kept, open file → kept. -6 for silent skip of unreadable fd dirs without logging. |
| **Security** | **96/100** | Purge spec validation is strict, FORBIDDEN paths enforced, symlinks never followed, realpath containment checked, no secrets, no injection. -4 for substring-based FORBIDDEN check (should be path-component-based for defense in depth). |
| **Performance** | **88/100** | `newest_mtime` walks entire unit per pass (O(files) per unit, every 10min). `open_paths` reads all of `/proc/*/fd` every pass. Both are acceptable at current scale but will not scale to 1000s of runs. Ledger bisection (`offset_before`) is efficient. |
| **Law compliance** | **100/100** | All laws compliant. No violations. Expiry strengthens L-v. Purge respects delivered/attribution law. Spend freeze untouched. |
| **World-class gap** | **85/100** | Core design is production-grade (fail-closed, auditable, append-only). Missing: purge failure alerting, boundary tests, live.json kept-breakdown. |
| **OVERALL** | **91/100** | Excellent diff. Correct, secure, fail-closed, well-logged. Minor polish needed but nothing blocking. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No critical issues found. The diff is safe to merge.

P1 HIGH     | Add purge failure to STATE notice or alerting | purge.py:253-257, service.py:350 | If purge spec is refused or /proc unreadable, every pass silently logs "refused" but no operator alert fires. Expired media accumulates unbounded. Wire purge failures into the existing STATE notice system (like spend/outage notices) or add a metric.

P1 HIGH     | Log when /proc fd dirs are skipped | purge.py:203-205 | If many PIDs have unreadable fd dirs, `opened` is incomplete and files held open could be deleted. The 2h grace is a second defense but not sufficient for long-running renders. At minimum log a warning with count of skipped PIDs.

P2 MEDIUM   | Document horizon_h breaking change | ledger.py:223 | Default changed from 72 to 12. Any caller relying on the old default (e.g., external packager integration) silently gets fewer results. Add to CHANGELOG/release notes and consider a deprecation warning if horizon_h=72 was ever documented as the default.

P2 MEDIUM   | Add boundary test for exactly-12h expiry | ledger.py:269, purge.py:312 | At exactly published_at+12h: ledger expires (now>=exp → True), purge deletes (pub>cutoff → False → not kept). Consistent but untested. Add test with published_at = now-12h exactly.

P2 MEDIUM   | Expose kept breakdown in live.json | stats.py:102-108 | live.json shows last_pass but operators need kept-reason breakdown without reading passes.jsonl. Add kept summary to live.json purge section.

P3 LOW      | Consolidate aware() duplication | config.py:53, ledger.py:205 | Two identical aware() functions. Make ledger import from config.

P3 LOW      | Optimize newest_mtime | purge.py:215-223 | Walks entire unit tree every pass. Cache or use unit mtime only (already checked via lstat on unit dir). At scale with many runs, this is the hottest path in purge.

P3 LOW      | Make FORBIDDEN check path-component-based | purge.py:72,296 | Substring check works but is fragile. Use path component splitting: check if any FORBIDDEN component appears as a path segment.

P3 LOW      | Reduce log noise for refused spec | service.py:350,425 | When purge_spec is None, purge_once logs every 600s forever. Log once at startup + once per hour, or only on state change.
```

---

## SECTION 9: THE ONE THING

**Wire purge failures into the existing STATE notice / alerting system — a silent purge failure means expired media accumulates forever with no operator visibility, and that is the only scenario where this otherwise excellent fail-closed design fails open in practice.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff is correct, secure, and fail-closed — every uncertainty keeps the file, every deletion is audited, and no existing check is weakened. Before merging, add alerting for purge failures (P1) and document the `horizon_h` default change from 72→12h. Everything else is polish.

---

### Reviewer Q&A (from prompt)

**Q1: Can the purge delete anything the ruling says to keep?**
No. Verified line by line:
- Delivered video's source → `purge.py:305-307` keeps if `vid in vids_delivered` (checked before any deletion)
- Provenance record / transcript / pin → `purge.py:278` only matches `media_ext` (`.mp4`, `.wav`, etc.), never `.json`; `FORBIDDEN` blocks `/transcripts/` and `/references/` paths
- Render (`out/`, `qa/`, `VERIFY/`) → `FORBIDDEN` blocks `/out/`, `/qa/`, `/VERIFY/`; `reported_not_purged` measures but never deletes
- Media under 12h → `purge.py:312-314` keeps if `pub > cutoff` (i.e., published within 12h)

**Q2: Can malformed spec / symlink / race / rename / unreadable file cause deletion outside targets or of kept content? Is every uncertainty fail-closed?**
No. Every uncertainty is fail-closed:
- Malformed `purge.json` → `load_spec` raises `SpecError` → `service.py:91-92` sets `purge_spec=None` → every pass returns `None`, nothing deleted
- Symlink unit → `purge.py:275` skipped; symlink file → `purge.py:292-294` kept (not regular file)
- Race (file replaced between `lstat` and `unlink`) → `os.unlink(p)` unlinks the directory entry, not a symlink target (POSIX)
- Unreadable delivered set → `purge.py:253-257` entire pass refused
- Unreadable `/proc` → `purge.py:250-251` entire pass refused
- Unknown publish time → `purge.py:309-311` kept
- Active unit (touched <2h ago) → `purge.py:318-320` kept
- Open file → `purge.py:321-323` kept

**Q3: Can the adapter return a moment ≥12h after publish, by any path?**
No. Verified all paths:
- Normal row with `expires_at` → `expiry()` = `min(expires_at, published_at+12h)` → `now >= exp` → dropped (`ledger.py:269-270`)
- Row without `expires_at` (mined before field existed) → `expiry()` = `published_at+12h` → still dropped
- Row with tampered future `expires_at` → `min()` picks `published_at+12h` → still dropped
- Row without `published_at` → `expiry()=None` → falls to `pub is None` check → dropped as "publish time not measured"
- `since` far in past → `cutoff = min(since, now-12h)-1day` still reads the line, but `now >= exp` still drops it
- `horizon_h` override → caller could pass `horizon_h=72` to widen the read window, but `now >= exp` still drops expired moments regardless of horizon
- Re-mined row → new `expires_at` written but `min()` still caps at `published_at+12h`

**Q4: Does anything weaken an earlier check?**
No. `L-u` hard flags (`ledger.py:279-280`), delivered exclusion, opt-out check, contract drift re-derivation (`ledger.py:288-296`), and spend freeze are all untouched. The diff only adds a new exclusion (expiry) checked *before* all existing ones, and a new subsystem (purge) that is fully isolated from the ingest/mine/ledger paths.