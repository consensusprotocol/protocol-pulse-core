# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 292.4 s, $0.005, finish stop)

# PROTOCOL PULSE CODE AUDIT — pp-ingest DIFF (r119 / 87b3efeb)

## SECTION 1: CORRECTNESS

### 1.1 Main Flow: `pipeline_sweep` → `fetch_once` → `process` → `mine`

**Step 1 — Sweep identifies candidates (`fetch.py:218-248`)**

```python
rows = q.rows("SELECT video_id, channel_id FROM videos WHERE state IN (?, ?) AND next_at > ? AND "
              "COALESCE(published_ts, discovered_ts) >= ?",
              (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, now_ts, now_ts - config.EXPIRY_H * 3600))
```

Correctly filters: only two transcript-wait states, only `next_at > now` (not yet due), only inside 12h expiry window. `COALESCE(published_ts, discovered_ts)` handles unpublished/discovered-only rows. **Correct.**

**Step 2 — Per-row pipeline check (`fetch.py:230-236`)**

```python
for r in rows:
    try:
        if pipeline_transcript(r["video_id"], r["channel_id"]) is not None:
            due.append(r["video_id"])
    except ValueError:
        continue
```

Calls `pipeline_transcript()` which does a `glob` + JSON read per waiting video. This is the claimed "one glob per waiting video" — accurate. `ValueError` skip for IDs `transcript_store` refuses is correct per spec.

**Step 3 — Bulk UPDATE + events (`fetch.py:238-243`)**

```python
q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?) AND video_id IN "
    f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING) + tuple(due))
```

Re-checks `next_at > ?` and `state IN` in the UPDATE — prevents racing with a concurrent state transition that happened between SELECT and UPDATE. **Correct race handling.** However see N+1 and SQL injection notes below.

**Step 4 — `service.fetch_once` integration (`service.py:255-260`)**

```python
if (self._last_sweep is None or now - self._last_sweep >= fetch.PIPELINE_SWEEP_S) and not self.gate.open_for():
    self._last_sweep = now
    made = fetch.pipeline_sweep(self.q, now)
```

Gate check prevents sweep when no probe can run — correct per spec. Throttle at 60s prevents busy loop. Sets `_last_sweep = now` *before* calling sweep — if sweep throws, the 60s window still advances. This is intentional (prevents tight retry loop on persistent failure) but means a transient I/O error delays next sweep by 60s. Acceptable.

**Step 5 — Probe still runs (`service.py:267-280`)**

```python
claimed = [v for v in self.q.due(Q.FETCH_DUE, limit, first=first)
           if not self.stop.is_set() and self.q.claim(v["video_id"], (v["state"],), Q.PROBING)]
```

Sweep only moved `next_at`; `fetch.process()` still does Short/live/upcoming/age/length/duplicate checks. **No bypass — correct.**

**Step 6 — Bitcoin-first ordering (`queue.py:177-188`, `queue.py:199-207`, `service.py:817-830`)**

`Queue.due()` and `Queue.hook_due()` add `CASE WHEN channel_id IN (...) THEN 0 ELSE 1 END` prefix to ORDER BY. When `first` is empty, `order = ""` and SQL is identical to old query. **Correct.**

`Service._first()` caches for 60s, reads from `watch.registry()`, filters `tier <= BITCOIN_TIER_MAX(2)`. On exception returns last known set. **Correct.**

### 1.2 Logic Errors

**None critical.** One minor logic issue:

- **`fetch.py:238` — Empty `due` guard is correct** (`if due:` on line 237 prevents `IN ()` syntax error). Good.

### 1.3 Race Conditions

- **Sweep vs. concurrent `claim`**: The UPDATE re-checks `state IN (?, ?)` and `next_at > ?`, so if a video was claimed to `PROBING` between SELECT and UPDATE, it won't be updated. **Safe.**
- **Sweep vs. `mine` loop**: Sweep only touches `PROBE_RETRY`/`CAPTIONS_PENDING`; mining touches `TRANSCRIBED`→`MINING`. No overlap. **Safe.**
- **`_first_ids` / `_first_at` without lock**: `fetch_once` and `mine_once`/`hook_once` may run on different threads. `_first()` reads/writes `self._first_ids` and `self._first_at` without holding any lock. In CPython, assignment to these is atomic due to GIL, but the read-then-write sequence is not atomic — two threads could both enter the `chans is None` path and both call `watch.registry()`. This is benign (redundant registry read, last write wins, both produce same result) but is technically a data race. **Low severity.**

### 1.4 N+1 Query Problem — **CONFIRMED**

`fetch.py:230-236` executes **one `pipeline_transcript()` call per waiting video**, each of which does:
1. `glob(os.path.join(PIPELINE_STORE, vid, "transcript.*.json"))` — filesystem syscall
2. `open()` + `json.load()` + validation — if file exists

If 200 videos are in `CAPTIONS_PENDING`/`PROBE_RETRY` (plausible during extended 429), that's 200 globs + up to 200 JSON reads per sweep, every 60 seconds. The spec says "a glob per waiting video" so this is *by design and disclosed*, but it is still an N+1 pattern that will scale linearly with queue depth.

**Mitigating factors**: `PIPELINE_STORE` is local filesystem (not network), globs are cheap, and the 60s throttle bounds frequency. For the expected queue depth (<50 waiting videos during 429), this is acceptable. At 500+ waiting videos it would become measurable.

**Verdict**: N+1 exists but is bounded and disclosed. Not a production breaker at current scale.

### 1.5 Edge Cases

| Edge Case | Handled? | Location |
|-----------|----------|----------|
| Empty DB (no waiting videos) | Yes — `rows` empty, `due` empty, no UPDATE | `fetch.py:225-237` |
| `due` empty → no UPDATE | Yes — `if due:` guard | `fetch.py:237` |
| `first` empty → old ORDER BY | Yes — `if f else ""` | `queue.py:180,204` |
| `published_ts` NULL | Yes — `COALESCE(published_ts, discovered_ts)` | `fetch.py:226` |
| Both timestamps NULL | Video excluded (`NULL >= ?` is false in SQLite) — correct, no publish time means can't verify expiry | `fetch.py:226` |
| `transcript_store` rejects ID | Yes — `except ValueError: continue` | `fetch.py:234` |
| Registry unreadable | Yes — `except Exception: return self._first_ids` | `service.py:828` |
| Gate open | Yes — sweep skipped entirely | `service.py:257` |
| Video already `next_at <= now` | Excluded by `next_at > ?` — correct, already due via normal path | `fetch.py:225` |
| Expired video (12h+) | Excluded by `COALESCE(...) >= ?` — correct | `fetch.py:226` |
| `PIPELINE_STORE` missing/corrupt JSON | `pipeline_transcript()` returns `None` (no file / validation fail) — video stays on original retry schedule | `fetch.py:231` |

**One unhandled edge**: `fetch.py:238` — if `due` contains 1000+ IDs, the `IN (?, ?, ...)` clause with 1000+ placeholders may hit SQLite's `SQLITE_MAX_VARIABLE_NUMBER` (default 999). At current scale this is unreachable, but worth noting for correctness.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest** (RSS→yt-dlp, ETag/backoff, ledger, Shorts/live handling, durable queue) | **COMPLIANT** | Sweep does not alter ingest discovery path. `fetch.process` still handles Shorts/live/duplicate checks (`fetch.py:249` comment, `service.py:267`). No YouTube request in sweep. |
| **BUILD: captions via store's writer, staging copy, never main tree** | **COMPLIANT** | `take_pipeline_transcript` writes via `ts.put()` through store's writer (`fetch.py:195-210` existing code, unchanged). Sweep only reads. |
| **BUILD: first-pass mining (bounded concurrency, 429/503 backoff, ≤20 in flight, $460 cap/90% tripwire)** | **COMPLIANT** | No change to mining concurrency or spend tracking. Sweep only affects fetch scheduling. |
| **BUILD: append-only moment ledger + adapter** | **COMPLIANT** | No change to ledger. |
| **BUILD: daily coverage check** | **COMPLIANT** | No change. |
| **BUILD: blind A/B (generator≠judge)** | **COMPLIANT** | No change to provider routing. |
| **L-x: NO SINGLE MODEL, ULTRON FIRST** (provider interface ≥2 back-ends, local default, no GPU use here) | **COMPLIANT** | No model/provider code touched. No GPU code. `config.py:39-40` comment correctly notes tier ordering. |
| **L-l: strict schema, nothing repaired, failed call ≠ default/pass** | **COMPLIANT** | No change to mining validation. |
| **L-j/L-m: fail closed, nothing measured ≠ pass** | **COMPLIANT** | Sweep does not create measurements. Expired videos excluded. |
| **L-h/L-k: transcript as spoken, canonical form, never rewritten** | **COMPLIANT** | `pipeline_transcript()` reads through `transcript_store` canonical validation. Sweep never writes transcripts. `take_pipeline_transcript` uses `ts.put()` (store's writer). |
| **L-e: word timing at cut time** | **COMPLIANT** | No change. |
| **L-u: hard exclusions before ranking** | **COMPLIANT** | No change to ranking/exclusion. |
| **L-v: moment never spans speaker change, re-uploads excluded, time-sensitive needs publish time** | **COMPLIANT** | No change. `COALESCE(published_ts, discovered_ts) >= ?` correctly enforces time window. |
| **Secrets: keys by name from env file, never logged** | **COMPLIANT** | No secret handling in diff. |
| **SPEND FREEZE (no paid frontier calls, Heimdall→local only, 90% notify never halt)** | **COMPLIANT** | No provider calls added. Sweep is local filesystem only. |
| **Ruling 107(2) / Ruling 13:05 Nov 16 (mine within 10 min, Bitcoin first)** | **COMPLIANT** | Sweep at 60s interval + miner at 5s interval = ~65s worst case from transcript landing to mining start. Well within 10 min. Bitcoin-first ordering implemented in all three paths (fetch/mine/hook). |

**Overall Law Compliance: COMPLIANT — no violations detected.**

---

## SECTION 3: SECURITY

### 3.1 SQL Injection

**`queue.py:177-188` and `queue.py:199-207` — SAFE.**

```python
order = f"CASE WHEN channel_id IN ({','.join('?' * len(f))}) THEN 0 ELSE 1 END, " if f else ""
# ...
tuple(states) + (self.clock(),) + f + (limit,)
```

The `IN (...)` clause uses `?` placeholders for every element of `f` (channel IDs). Values are bound via parameter tuple, not interpolated. `states` similarly parameterized. **No injection.**

**`fetch.py:238` — SAFE.**

```python
q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?) AND video_id IN "
    f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING) + tuple(due))
```

Same pattern — `due` values are `video_id`s from DB rows, bound as parameters. **No injection.** (Note: `video_id` values originated from DB, not user input, further reducing risk.)

**`fetch.py:225` — SAFE.** All parameters bound.

### 3.2 Authentication / Authorization

Not applicable — this is a backend ingest pipeline with no HTTP routes. No auth surface in diff.

### 3.3 Rate Limiting

- Sweep makes **zero YouTube requests** — confirmed (`fetch.py:218` docstring, no `yt-dlp`/`requests` calls in `pipeline_sweep`).
- Sweep does `glob` + `read` on local filesystem only — no external API to exhaust.
- `_first()` calls `watch.registry()` at most once per 60s — bounded.
- No paid model calls added.

**No rate limiting gaps introduced.**

### 3.4 Secrets in Code

No secrets, keys, tokens, or credentials in diff. Clean.

### 3.5 Unvalidated Input

- `video_id` in sweep comes from DB (`q.rows`), not user input. Validated by `transcript_store` (`ValueError` catch).
- `channel_id` in `first` comes from registry (operator-controlled config), not user input.
- `PIPELINE_STORE` path uses `os.path.join` with `video_id` — but `video_id` is validated by `transcript_store` before any path construction in `pipeline_transcript()`. The sweep itself does not construct paths directly.

**No unvalidated input reaching DB/filesystem/shell.**

---

## SECTION 4: FRONTEND QUALITY

**Not applicable.** This diff touches `pipeline/ingest/*` and `tests/ingest/*` only. No frontend code, no UI, no JS, no CSS. No assessment possible or needed.

---

## SECTION 5: BACKEND QUALITY

### 5.1 DB Operations

| Check | Status | Detail |
|-------|--------|--------|
| Parameterized queries | ✅ | All queries use `?` placeholders |
| Transaction handling | ✅ | `q.x()` wraps in transaction (existing Queue impl) |
| Rollback on failure | ✅ | Queue's `x()` handles rollback (existing) |
| Bulk vs N+1 writes | ✅ | Single UPDATE for all due videos, single loop for events |

One concern: `fetch.py:240-243` does one UPDATE + N `q.event()` inserts. If there are 50 due videos, that's 51 writes. The events could be batched, but at expected volumes this is negligible.

### 5.2 External API Calls

No external API calls in sweep. Existing `fetch.process` retains its timeout/retry/gate logic unchanged.

### 5.3 Cron / Service Loop Resilience

- `service.py:257` — `self.gate.open_for()` check prevents sweep during circuit-breaker open. Correct.
- `service.py:828` — `except Exception: return self._first_ids` — registry failure never crashes the loop. Correct.
- `fetch.py:234` — `except ValueError: continue` — bad video ID never crashes sweep. Correct.
- **Missing**: `fetch.py:230-236` — `pipeline_transcript()` could raise `OSError`/`json.JSONDecodeError` beyond `ValueError` (e.g., permission error, disk full, corrupt JSON that passes glob but fails parse differently). The `except ValueError` would not catch these, and the exception would propagate up through `fetch_once`, potentially killing the fetch round. In practice `pipeline_transcript()` likely wraps these, but the sweep's narrow `except ValueError` is fragile.

### 5.4 Memory Leaks

No large objects created per-request. `rows` and `due` are bounded by waiting video count. No leak.

### 5.5 Logging

- `service.py:259-260` — sweep result logged with count and IDs. Good.
- `fetch.py:218-219` — docstring documents behavior. Good.
- `queue.py:178-179` — docstring documents ordering contract. Good.
- Missing: no log when sweep finds 0 due videos (silent) — intentional to avoid log spam at 60s interval. Correct choice.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

For a premium Bitcoin intelligence product, this change is **narrowly scoped and well-executed for what it does**. Honest assessment:

**What this does excellently:**
- The sweep mechanism is elegant — minimal code, no new dependencies, no YouTube quota cost, correct race handling. This is the right solution for the 429 problem.
- Bitcoin-first ordering is implemented consistently across all three queue paths (fetch/mine/hook). Many teams would miss one.
- Test coverage is strong — 6 new tests covering sweep filtering, ordering, integration, and throttle behavior. Mutation testing at 10/10 killed.

**What is genuinely missing (material impact):**

1. **No observability on sweep latency** — The `acquired_at` is now carried on the attempt line (`fetch.py:218`), but there is no metric/alert tracking `acquired_at → mined_at` latency. For a "within 10 minutes" SLA, you need a histogram and an alert when p95 exceeds threshold. Without it, you won't know if the SLA is actually met in production.

2. **No second caption source (acknowledged as "design, do not build yet")** — The ruling explicitly asks for a design. This diff doesn't include it, which is per instructions, but it means the system remains single-point-of-failure on YouTube quota. A world-class system would have the design doc alongside the code.

3. **Tier 2 as "Bitcoin channel" is debatable** — `BITCOIN_TIER_MAX=2` includes DataDash, CoinDesk, Yahoo Finance-adjacent crypto media. During high-volume news events, these channels may crowd out tier 1 (WBD, TFTC) which are the highest-signal Bitcoin sources. A weighted priority (tier 1 before tier 2 before tier 3) would be more precise than the current binary Bitcoin/non-Bitcoin split. The current implementation treats Scott Melker and What Bitcoin Did identically.

4. **No backpressure signal** — If the miner falls behind (Heimdall 429/503), the sweep keeps making videos due, growing the `TRANSCRIBED` queue. There's no mechanism to slow the sweep or surface queue depth. Bloomberg would have queue depth dashboards and backpressure.

**What is already excellent (explicitly):**
- Queue ordering with SQL `CASE WHEN` is clean and performant — no application-level sorting.
- The `PIPELINE_SWEEP_S=60` throttle + gate check is the right granularity.
- `transcript_store` validation as gatekeeper (refusing bad IDs) is correct defense-in-depth.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **92/100** | Correct, race-safe, handles edge cases. -8 for narrow `except ValueError` and N+1 at scale. |
| **Frontend/UI** | **N/A** | No frontend in scope. |
| **Error handling** | **84/100** | Good for happy path and known failures. -16 for unhandled `OSError`/`JSONDecodeError` in sweep loop and no handling of `SQLITE_MAX_VARIABLE_NUMBER`. |
| **Security** | **98/100** | All queries parameterized, no secrets, no injection. -2 for theoretical `IN` clause overflow. |
| **Performance** | **88/100** | 60s throttle bounds cost. -12 for N+1 glob pattern that scales linearly with queue depth. |
| **Law compliance** | **100/100** | No violations. All governing laws satisfied. Ruling 13:05 correctly implemented. |
| **World-class gap** | **78/100** | Solid engineering, missing SLA observability, tier granularity, and backpressure for premium product standard. |
| **OVERALL** | **90/100** | Production-ready with minor hardening. High-quality, well-tested, law-compliant change. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No production breakers found.

P1 HIGH     | Widen except in pipeline_sweep loop to catch OSError/IOError | fetch.py:234 | A single corrupt transcript file or permission error on one video's directory will throw outside ValueError, abort the entire sweep, and leave all other waiting videos stuck on their original 10-30 min retry — violating the 10-min SLA for every video, not just the corrupt one.
P1 HIGH     | Add acquired_at→mined_at latency metric and alert | service.py:259 (after sweep log) + mine path | Without it the "within 10 minutes" SLA is unmonitored — you will not know if it is met or violated in production until a user reports stale moments.

P2 MEDIUM   | Guard IN clause against SQLITE_MAX_VARIABLE_NUMBER | fetch.py:238 | At 1000+ waiting videos the UPDATE will fail with "too many SQL variables" — chunk `due` into batches of 900 if it exceeds threshold.
P2 MEDIUM   | Consider tier-weighted ordering (tier 1 before tier 2 before tier 3) | queue.py:180, config.py:39 | Binary Bitcoin/non-Bitcoin treats TFTC and CoinDesk identically — during high-volume periods tier 1 signal gets diluted by tier 2 volume.
P2 MEDIUM   | Add thread lock or atomic update for _first_ids/_first_at | service.py:817-830 | Concurrent fetch/mine threads can redundantly call watch.registry() and race on cache update — benign now but fragile under higher concurrency.

P3 LOW      | Log sweep skip reason at DEBUG when gate is open | service.py:257 | Aids debugging when investigating why a transcript was not picked up promptly during circuit-breaker events.
P3 LOW      | Batch q.event() inserts in pipeline_sweep | fetch.py:241-242 | N individual event inserts could be a single executemany — minor efficiency at current scale.
```

---

## SECTION 9: THE ONE THING

**Instrument the `acquired_at → mined_at` latency as a monitored SLA metric — without it you have built a 10-minute guarantee you cannot prove you are meeting.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** It correctly implements the 13:05 ruling with minimal, well-tested, race-safe changes that introduce no law violations or security issues. Before deploying, widen the `except ValueError` to `except (ValueError, OSError)` in the sweep loop (one-line fix) and add latency observability — everything else can follow in the next iteration.
