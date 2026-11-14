# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 573.7 s, $0.033, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest (purge A19 diff)

## SECTION 1: CORRECTNESS

### Main flow: `purge.run_pass()` step-by-step

**1. Collect delivered set** — `purge.py:381-382` calls `delivered()` which returns `vids_delivered, druns, problems, units`. Correct. `units` is new in this diff and carries `[(dir, {vids})]` needed for per-delivery logic.

**2. Fail-closed gate** — `purge.py:388-393` if `problems` (unreadable delivered set or `/proc`) → `refused`, return 0 freed. Correct, unchanged, runs before any deletion.

**3. Collect copies** — `purge.py:406-415` iterates `spec["targets"]` with `mode=="by_video"` and globs `t["units"]` + `t["files"]`, filters to `v in vids_delivered` and media ext. Builds `copies: {vid: [paths]}`. **Logic error: this scan is done BEFORE the main deletion loop but uses the same glob patterns. It will include files that later fail the `protect`/`FORBIDDEN`/`islink` checks, but that's harmless — they just become candidates for hash matching that will never be deleted anyway. Not a bug, but wasteful.**

**4. Compute kept set** — `purge.py:416` `kept_copies(units, copies, exts)` → `kept_paths: {realpath: why}`, `unresolved: {vid: why}`. Walkthrough of `kept_copies` at `purge.py:234-282`:

- For each delivery unit, reads `PROVENANCE.json`. If unreadable → `prov=None`, `srcs=[]`, falls through to `vids - listed` path. **Correct** — `unit_videos` already flagged unreadable PROVENANCE as a `problem` that would have aborted the pass, but `kept_copies` is only called after that gate, so this branch only fires for deliveries where PROVENANCE was readable during `delivered()` but became unreadable by now (TOCTOU). Handling it as "no sources" is defensible.
- For each `src` in PROVENANCE: validates `video_id` via `VIDEO_ID`, validates `sha256` via `SHA256_RE`. If no valid sha → `unresolved.setdefault(v, ...)`. **Correct — fail closed.**
- `own` construction at `purge.py:267-268`: `os.path.join(unit, sub, fn)` where `fn` is `s["file"]` and must be a plain basename (`os.path.basename(fn)==fn`). **Correct — prevents `../../etc/passwd` traversal via PROVENANCE.**
- `found` at `purge.py:269-270`: tries `own` first (delivery's own file with matching hash), else sorted `copies[v]` with matching hash. **Correct priority: own copy preferred.**
- `same()` at `purge.py:244-248`: `isfile && !islink && sha256_of(p)==h`, catches `OSError` → `False`. **Correct — unreadable candidate never taken.**
- For `vids - listed` (videos cut but not in PROVENANCE): `purge.py:275-281` keeps `_own_media(unit, v, exts)` by name, else `unresolved`. **Correct per A44.**

**5. Main deletion loop** — `purge.py:418-505`:

- For each target, each unit, each file matching `t["files"]` with media ext:
  - `lstat` check, `S_ISREG`, `realpath` inside `unit_real` and outside `protect`/`FORBIDDEN` — **correct, unchanged.**
  - `vid = _vid_of(basename)` — extracts 11-char YouTube ID from filename stem. **Correct.**
  - **Delivered handling at `purge.py:458-466`:**
    ```python
    if vid in vids_delivered:
        if rp in kept_paths: keep(...)
        if vid in unresolved: keep(...)
        other = True
    ```
    **BUG (logic): The two `if` blocks are not `elif`. If `rp in kept_paths` is True, it `continue`s — correct. But if `rp in kept_paths` is False and `vid in unresolved` is True, it also `continue`s — correct. However, the structure means a file that IS in `kept_paths` but whose vid is ALSO in `unresolved` (possible when one delivery resolved but another didn't for same vid) will hit the first `continue` and never check `unresolved`. This is actually correct behavior — the kept copy should be kept regardless. But the converse: a file NOT in `kept_paths` whose vid IS in `unresolved` correctly keeps every copy. The logic is correct but fragile — an `elif` would be clearer and prevent future misreading.**

  - Falls through to `published()` check, `cutoff` (12h), `newest > busy_after` (2h idle), `rp in opened` — **all correct, unchanged.**
  - `kept_of` at `purge.py:483`: `sorted(k for k in kept_paths if other and _vid_of(basename(k))==vid)` — **BUG: `kept_paths` keys are `realpath`s, but `_vid_of(os.path.basename(k))` extracts vid from the realpath's basename. If the kept copy is a reference's file (e.g., `/references/pulse_ref/sources/KKKKKKKKKKK.mp4`), its basename IS `KKKKKKKKKKK.mp4`, so `_vid_of` works. But if the kept copy was found via `copies` (a run's file), its realpath basename also works. So this is actually correct. However, it does a linear scan of ALL kept_paths for every deletion — O(n*m) where n=deletions, m=kept copies. At 46 kept, 121 deletions, trivial. Not a bug.**

  - Dry-run vs real delete, logging with `other_copy_of_delivered` and `kept_copies` — **correct.**

**6. Summary** — `purge.py:541-550` reports `kept_copies`, `other_copies`, `unresolved` count. **Correct.**

### Race conditions

- **TOCTOU on `sha256_of` cache `purge.py:205-219`**: `_SHA` is a module-global dict keyed by `(realpath, size, mtime_ns)`. If a file is replaced between `os.stat` (cache key) and `open` (hash), the hash will be of the new content but cached under old key's size/mtime. However, `os.stat` is called INSIDE `sha256_of`, and the file is opened immediately after — window is microseconds. More importantly, if a file is being written concurrently (render in progress), `newest_mtime` check (`purge.py:433-435`) should have caught it via `active_grace_s` (2h). **Low risk, acceptable.**
- **TOCTOU on `copies` collection vs deletion**: Files are globbed at `purge.py:406` then deleted at `purge.py:491`. A file created between these two scans won't be in `copies` but could be deleted. If it's a delivered video's new copy, it won't be in `kept_paths` either, so it would be treated as `other=True` and deleted if expired/idle. **This is actually correct per spec — new copies of delivered videos ARE other copies and should be deleted. No bug.**
- **Concurrent purge passes**: `purge.py:376-377` takes `fcntl.flock` on `purge.lock` — **correct, prevents overlap.**
- **N+1 query**: `published()` at `purge.py:294-311` is called per-file inside the deletion loop, with a `cache` dict. First call per vid hits `q.video()` (SQLite) or reads `meta.json` from disk. Subsequent files of same vid hit cache. **Not N+1 — it's cached. Correct.**

### Edge cases

- **Empty DB / no deliveries**: `delivered()` returns `vids=set(), units=[]`, `kept_copies` returns `keep={}, unresolved={}`, main loop treats no vid as delivered → deletes expired idle media normally. **Correct.**
- **PROVENANCE with `file: null` or missing**: `purge.py:261` checks `isinstance(fn, str) and fn and basename==fn` → `own=[]`, falls through to `copies` search. If no copy has the hash → `unresolved`. **Correct.**
- **Symlink attack**: `purge.py:445` checks `S_ISREG` (symlinks fail), `purge.py:448` checks `realpath.startswith(unit_real)` — symlink inside unit pointing outside would have realpath outside unit → kept. **Correct.**
- **Reference as both delivery and target**: References are under `/references/` which is in `FORBIDDEN` (`purge.py:46`). Even if a reference's `sources/` matched a target glob, `purge.py:448` `any(b in rp for b in FORBIDDEN)` would keep it. **Correct — references never deleted.**
- **Hash cache staleness**: `_SHA` key includes `size` and `mtime_ns`. If file content changes but size+mtime stay same (extremely unlikely — mtime changes on write), stale hash returned. **Theoretical but not practical — any write updates mtime.**

### Verdict on correctness: **No logic errors that break the claimed behavior. One minor structural fragility (if/continue vs elif) but functionally correct.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD** (continuous ingest, RSS→playlist, ~10min, ETag/backoff, last-seen, re-upload, Shorts/live, durable queue, captions via store writer, staging copy, bounded concurrency, spend cap, ledger, coverage, A/B) | **COMPLIANT** | Unchanged by this diff. Purge is ruling 77, not BUILD core. |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | `providers.json:107-122` every role has ≥2 backends. `providers.py:806-818` `available()` respects freeze. This diff doesn't touch providers. |
| **L-l strict schema, never repaired** | **COMPLIANT** | `mine.py:447-499` validator rejects on any deviation. `providers.py:983-989` re-prompts with reason, never repairs. Untouched. |
| **L-j / L-m fail closed; nothing measured is never a pass** | **COMPLIANT** | `purge.py:388-393` unreadable delivered set → `refused`, 0 deleted. `purge.py:264-266` no sha → unresolved → every copy kept. `purge.py:281` no own section → unresolved. `ledger.py:337-338` expired → dropped. All fail-closed. |
| **L-h / L-k read as spoken, never rewrite records** | **COMPLIANT** | `contract.py:122-125` `E.spoken()`, `fetch.py:237` `_store()` via store writer. Untouched. |
| **L-e word timing at cut time** | **COMPLIANT** | `contract.py:138-145` `timing: segment`, packager re-anchors. Untouched. |
| **L-u hard exclusions** | **COMPLIANT** | `mine.py:23-24` `HARD_RISKS`, `ledger.py:347-348` pre-applied. Untouched. |
| **L-v speaker change, re-uploads, time-sensitive** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside`, `fetch.py:186-191,242-247` duplicate detection. Untouched. |
| **Secrets (keys by name from env, never logged)** | **COMPLIANT** | `providers.py:180-220` `Keyring`, `providers.py:213-220` `redact()`, `providers.py:953-955` redaction before recording. No secrets in this diff. |
| **SPEND FREEZE** | **COMPLIANT** | `providers.json:5-9` freeze list, `providers.py:783-786` `frozen()`, `providers.py:807-812` `available()` blocks frozen. Untouched. |
| **Ruling 76/77 expiry + purge** | **COMPLIANT** | `config.py:36-37` `EXPIRY_H=12`, `ledger.py:280-286` `expiry()`, `purge.py:395` `cutoff = now - 12h`. This diff correctly implements A19 refinement. |
| **Ruling 80 hook pass** | **COMPLIANT** | `mine.py:126-137` `HOOK_PROMPT_VERSION=mine-hook/4`, `service.py:375-469` `hook_video()`. Untouched. |
| **Ruling 87 shared signal** | **COMPLIANT** | `downsignal.py` entire module, `service.py:121-122` wiring. Untouched. |
| **Ruling 98 paid route** | **COMPLIANT** | `providers.json:96-99` `paid_route`, `downsignal.py:198-256` `_route_tick`, `service.py:625-678` `_paid_due`/`_queue_rechecks`. Untouched. |
| **Ruling 40 P1 second-model check** | **COMPLIANT** | `flagcheck.py`, `ledger.py:212-241` `check_valid`/`effective_risk`, `service.py:494-617` check loop. Untouched. |
| **A19 ONE COPY PER DELIVERY** | **COMPLIANT** | This diff IS the implementation. `purge.py:234-282` `kept_copies()`, `purge.py:406-416` collection, `purge.py:458-466` enforcement. Matches spec readings A43-A45. |

**No violations. No partial compliance.**

---

## SECTION 3: SECURITY

- **SQL injection**: All queries use parameterized `?` placeholders. `queue.py:97-99` `x(sql, args)` → `db.execute(sql, args)`. No string interpolation of user input into SQL. **Clean.**
- **Authentication bypass**: No HTTP routes in this codebase — it's a tmux daemon + CLI tools. No auth surface. **N/A.**
- **Rate limiting gaps**: `watch.py:37-73` `YouTubeGate` with `BoundedSemaphore(3)`, exponential backoff on 429/bot-check, global breaker. `providers.py:654-682` `Throttle` per backend with `Retry-After` honoring. `providers.py:575-640` `Health` circuit breaker. **Adequate.**
- **Secrets in code**: `providers.json` contains no keys — only `key_env`/`key_env_prefix` names. `providers.py:180-220` reads from `env_file` by name. `grep` for `sk-`, `api_key`, `secret` in code would find nothing. **Clean.**
- **Unvalidated input → DB/filesystem/shell**:
  - `purge.py:267-268` validates `fn` is plain basename before joining — **prevents path traversal.**
  - `purge.py:448` validates `realpath` inside `unit_real` and outside `protect`/`FORBIDDEN` — **defense in depth.**
  - `watch.py:59-73` `gate.run()` passes args to `config.ts()._ytdlp()` which is `subprocess` with list args (no shell) — **safe.**
  - `ledger.py:88-112` `line_problems()` validates all fields before use — **safe.**
- **One concern**: `purge.py:205-219` `sha256_of` does `open(path, "rb")` on paths from glob + PROVENANCE. If PROVENANCE contained `file: "/etc/shadow"` it would be blocked by `basename` check. If glob returned unexpected paths, `FORBIDDEN`/`protect` checks happen AFTER hash computation in `kept_copies` — meaning `sha256_of` could hash a file outside the intended targets during the `copies` scan. However, `copies` only collects from `spec["targets"]` globs, which are validated by `load_spec()` to be absolute paths outside protected dirs. **Acceptable.**

**Security score: Strong. No issues introduced by this diff.**

---

## SECTION 4: FRONTEND QUALITY

**N/A — This is a backend daemon with no frontend.** No HTML, CSS, JS, or UI components. The "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` markdown reports.

- CLI at `tools/ingest_watch.py:185-202` `cmd_purge` correctly handles `--apply`/`--measure`/`--json` flags.
- `purge.py:537-550` `summary()` produces human-readable output with GB formatting.

**No frontend to evaluate.**

---

## SECTION 5: BACKEND QUALITY

- **DB operations — try/except with rollback**: `queue.py:82-86` uses `isolation_level=None` (autocommit) with `WAL` + `synchronous=FULL`. Each `x()` is a single statement — no multi-statement transactions to rollback. `service.py:246-258` `fetch_once` wraps `fetch.process` in try/except and sets `PROBE_RETRY` on crash. `service.py:272-310` `mine_video` catches `ContractUnavailable`, `Exception`, `BaseException` separately. **Adequate for SQLite autocommit model.**
- **External API calls — timeout + retry + graceful degradation**: `providers.py:229-232` per-backend `timeout_s`, `providers.py:938-939` `transport_retries`, `providers.py:654-682` `Throttle` with backoff, `providers.py:575-640` `Health` breaker. Every call path has all three. **Excellent.**
- **Cron/purge loop — failure without crash**: `service.py:784-793` `_loop` wraps `fn()` in try/except, logs `loop_error` event, continues. `purge.py:388-393` problems → `refused` return, no exception. `service.py:733-752` `purge_once` handles `purge_spec is None` and `rep.get("refused")`. **Robust.**
- **Memory leaks**: `purge.py:205` `_SHA` is a module-global dict that grows unbounded — every unique `(realpath, size, mtime_ns)` ever hashed stays forever. At ~15 deliveries × ~10 videos × ~10 copies = ~150 files per pass, every 600s, with new runs appearing daily, this grows slowly but never shrinks. **Minor leak — should have LRU or periodic clear.** `service.py:651-652` `_conv` cache has a `>5000` clear. `_SHA` has no such bound.
- **Logging**: `service.py:179-186` `_log` with timestamp + file, `queue.py:107-110` `event()` for every state change, `purge.py:495-500` per-deletion JSONL, `purge.py:508` per-pass JSONL. **Excellent context for debugging.**

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this does well (genuinely excellent):**
- The provider abstraction (`providers.py` 1011 lines) with spend freeze, circuit breaker, throttle, spend meter, and local GPU fallback is **best-in-class** for a multi-model pipeline. Bloomberg would not do it better.
- Fail-closed design throughout (every `None`/unreadable → keep/refuse) is **exactly right** for a system that deletes files.
- The `PROVENANCE.json` by-hash identity for delivered copies is **the correct solution** — content-addressable, not name-based.

**What's missing or could be better:**

1. **No dry-run diff in CI**: The purge's `would_delete` output is only visible via manual `purge --measure` or `service.purge_once(dry_run=True)`. A world-class system would have a CI check that runs `purge --dry-run` on every PR and posts the `would_delete` count as a PR comment, so reviewers see "this PR would free X GB / delete Y files" before merge.

2. **No alerting on `unresolved` growth**: If `unresolved` count goes from 0 to 5, it means 5 delivered videos lost their attested copies — a serious data integrity issue. Currently only in `passes.jsonl` and `live.json:purge`. No threshold alert.

3. **No verification that kept copies are actually playable**: `sha256_of` verifies hash but not that the file is a valid MP4. A truncated download that happens to have been the delivered copy would be kept forever while valid re-downloads are deleted. A `ffprobe` duration check on kept copies would be more robust.

4. **Hash cache has no eviction** (noted above) — minor but un-world-class.

5. **No compaction of `deleted.jsonl`/`passes.jsonl`**: These grow forever. At 1 pass/600s = 144/day, each with ~10 deletions, that's ~50K lines/year. Not urgent but should have rotation.

**Overall: This is already excellent backend engineering. The gaps are operational polish, not architectural flaws.**

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Backend logic | **92/100** | Correct, well-structured, handles all edge cases. -8 for `if`/`continue` fragility and hash cache leak. |
| Frontend/UI | **N/A** | No frontend. CLI is functional. |
| Error handling | **95/100** | Every failure path is handled, fail-closed, logged. Exemplary. |
| Security | **93/100** | No injection, no secret leaks, path traversal blocked, symlink safe. -7 for hashing files before authorization check (minor). |
| Performance | **88/100** | Bounded concurrency, WAL, caching, bisection reads. -12 for unbounded `_SHA` cache and O(n*m) kept_of scan (trivial at current scale). |
| Law compliance | **100/100** | Every law verified compliant. No violations. |
| World-class gap | **85/100** | Excellent engineering, missing only operational polish (CI dry-run, unresolved alerting, log rotation). |
| **OVERALL** | **92/100** | Production-ready. One P2 fix recommended before merge. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No critical issues. Nothing will break production.
P1 HIGH     | (none) | — | No high-severity issues.
P2 MEDIUM   | Add LRU eviction to _SHA hash cache | purge.py:205 | Module-global dict grows forever; at scale (1000s of files over months) wastes memory. Add: if len(_SHA) > 1000: _SHA.clear() or use functools.lru_cache
P2 MEDIUM   | Change if/continue to if/elif in delivered-file handling | purge.py:458-466 | Two sequential if+continue blocks for kept_paths/unresolved are functionally correct but fragile — a future edit adding code between them could break fail-closed guarantee. Use elif.
P2 MEDIUM   | Add unresolved alert threshold | purge.py:416-418 + service.py:733-752 | If unresolved > 0, log at WARNING level and surface in live.json prominently. Currently silent in logs unless you read passes.jsonl.
P3 LOW      | Hash files only after authorization checks | purge.py:406-416 vs 269-270 | copies scan hashes files that may be outside authorized paths (defense-in-depth: hash after FORBIDDEN check)
P3 LOW      | Add CI dry-run check for purge | tools/ingest_watch.py:185-202 | Run purge --dry-run in CI and post would_delete summary as PR comment
P3 LOW      | Rotate deleted.jsonl/passes.jsonl | purge.py:361-367,495-508 | Append-only logs grow forever; add monthly rotation or size cap
P3 LOW      | Validate kept copies are playable media | purge.py:244-248 same() | sha256 match doesn't guarantee valid MP4; consider ffprobe check for kept copies
```

---

## SECTION 9: THE ONE THING

**The `_SHA` hash cache at `purge.py:205` needs an eviction policy — it's the only unbounded growth in an otherwise meticulously bounded system.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The A19 "one copy per delivery" implementation is correct, fail-closed, and well-tested — every delivered video's attested copy is preserved by hash, unresolved videos keep every copy, and all other cached copies are properly expired. The 5 new tests cover the critical cases (happy path, re-acquired file, unreadable hash, reference delivery, unlisted video). Ship it after addressing the P2 `if`→`elif` clarity fix — it takes 30 seconds and prevents a future regression.
