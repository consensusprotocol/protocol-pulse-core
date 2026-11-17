# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 140.7 s, $0.004, finish stop)

# PROTOCOL PULSE: CODE AUDIT — pp-ingest r122 (9df2df43)

## SECTION 1: CORRECTNESS

**Claimed flow:** Stub (`no_metadata`) no longer given up on `tries` count; given up only past `EXPIRY_H` (12h) from `published_ts`/`discovered_ts`. Retry interval 900s. `pipeline_sweep` makes `UNAVAILABLE/no metadata` due early if pipeline store has record.

**Walkthrough:**

1.  **Stub give-up logic — `fetch.py:273-278`:** `seen = v.get("published_ts") or v.get("discovered_ts") or now_ts` then `final = now_ts - float(seen) > config.EXPIRY_H * 3600`. This is correct for the stated intent. However:
    *   **Logic error — `float(seen)` on `None`:** If `seen` falls through to `now_ts` (float), `float(now_ts)` is redundant but safe. If `seen` is `0` (falsy), it incorrectly falls through to `discovered_ts`/`now_ts`. DB default for `discovered_ts` is likely `now_ts` at insert, so `0` should not occur, but `published_ts=0` would be mis-handled. Minor.
    *   **Correct: `tries` no longer gates give-up.** Verified in `test_r121.py:28-29` — `tries=99` still retries at `+900`. This fixes the CoinDesk bug where 4 live re-probes + 2 stubs = 6 tries = premature give-up.
    *   **Correct: `NO_METADATA_RETRY_S=900`:** `fetch.py:38` — 15 min, 48 probes max in 12h. Matches spec.

2.  **Sweep new clause — `fetch.py:239-242`:** `OR (state=? AND reason LIKE ?)` with `Q.UNAVAILABLE, "no metadata:%"` and `COALESCE(published_ts, discovered_ts) >= now - EXPIRY_H*3600`. Correctly scopes to inside 12h. Correctly filters only `no metadata` rows.
    *   **Correct: Other UNAVAILABLE untouched.** `test_r122.py:40-44` proves `gone0000001` (`Private video`) with pipeline record is NOT made due. This satisfies "What to check" #1.
    *   **Correct: Outside 12h untouched.** `test_r122.py:35-38` — `stub0000003` (13h old) not made due. Satisfies #3.
    *   **Correct: No record untouched.** `stub0000002` not made due.

3.  **Sweep UPDATE — `fetch.py:251-253`:** `WHERE next_at > ? AND state IN (?,?,?,?) AND video_id IN (...)` with `Q.UNAVAILABLE` added. Correctly only moves `next_at` to `now_ts` if still in future. Prevents re-dueing already-due rows.

4.  **Process after sweep — `fetch.py:273-278` + `test_r122.py:47-56`:** After sweep makes due, `process` probes again. If `post_live` facts returned, takes `TRANSCRIBED` via whisper path. If stub again, re-enters `UNAVAILABLE` with `+900`. Correct.

**Edge cases / Production risks:**

*   **N+1 in `pipeline_sweep` — `fetch.py:243-247`:** `for r in rows: try: pipeline_record_exists()` — This is `one glob + N reads` per docstring `fetch.py:237`. If `rows` is large (e.g., 500 stubs inside 12h), this is 500 filesystem `stat`/`read` calls per sweep. Acceptable at this scale (sweep runs every 30 min per `PIPELINE_RECHECK_S`), but unbounded. No `LIMIT` on the SELECT. If partner adds 10k videos, this could stall the watcher loop. **P1.**
*   **Race: `pipeline_sweep` + `process` concurrent:** `sweep` sets `next_at=now_ts` then `process` is called by watcher loop. If two watcher threads call `sweep` concurrently, both could get same `due` list and both `UPDATE`. The `WHERE next_at > ?` guards second UPDATE (now `next_at == now_ts`, not `> now_ts`), so second is no-op. Safe.
*   **Empty DB / bad input:** `v.get("published_ts")` handles missing keys. `float(seen)` will throw `TypeError` if `seen` is e.g., string `"2024-..."` — but DB stores epoch float, so safe. `q.rows` with no rows returns `[]`, loop no-op.
*   **Silent failure — `except ValueError: continue` `fetch.py:247`:** If `transcript_store` refuses id, row is silently skipped. Correct per comment, but no log. Debugging why a video never becomes due would be hard. **P2.**
*   **Stall handling — `fetch.py:38` comment `never counted as waiting`:** Verified `UNAVAILABLE` is outside `stall.WAITING` per spec. No change to stall logic in diff, so preserved. Correct.

**Verdict: Logic is correct for claimed fix. No wrong variable names. No silent data loss.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest, ETag/backoff, ledger, Shorts/live, durable queue, captions via store writer in staging, Heimdall bounded concurrency, queue-aware backoff, spend cap 90% notify, append-only ledger, coverage check, blind A/B** | **COMPLIANT** (within diff scope) | Diff does not touch ingest loop, queue, captions writer, Heimdall, ledger, or A/B. Changes are narrowly scoped to `NO_METADATA` retry/give-up and `pipeline_sweep`. No violation introduced. `fetch.py:38` 900s retry respects backoff principle (stub costs 1 probe/15min). `fetch.py:239-242` respects `EXPIRY_H` (moments' life). |
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | No model/provider code in diff. No vendor name, no GPU use. `fetch.py` is pure ingest. |
| **L-l strict schema, nothing repaired; L-j/L-m fail closed** | **COMPLIANT** | No model reply handling in diff. `fetch.py:273` `no_metadata` is a probe failure path, correctly `UNAVAILABLE` not a pass. |
| **L-h/L-k canonical transcript form, never rewritten** | **COMPLIANT** | `fetch.py:251` `pipeline_sweep` only reads pipeline store, never writes transcript. `test_r122.py:55` `transcript_method=="whisper"` via canonical store writer. |
| **L-e word timing at cut time** | **COMPLIANT** | Not in scope. |
| **L-u hard exclusions before ranking; L-v no span speaker change, re-uploads excluded, time-sensitive needs publish time** | **COMPLIANT** | Not in scope. `fetch.py:273` `no_metadata` handling does not affect exclusions. |
| **Secrets: keys by name from env, never logged** | **COMPLIANT** | No secrets in diff. `reason=f"no metadata: {detail}"` `fetch.py:277` — `detail` is yt-dlp output, not a key. |
| **SPEND FREEZE: no paid frontier, Heimdall then local only, queue if both down, 90% NOTIFY never halt** | **COMPLIANT** | No vendor calls in diff. `fetch.py` does not call any model. |

**No law violations in this diff.**

---

## SECTION 3: SECURITY

*   **SQL injection — `fetch.py:239-242`:** `q.rows("SELECT ... WHERE (state IN (?,?) OR ... reason LIKE ?) AND ...", (Q.PROBE_RETRY, ..., "no metadata:%", ...))` — All user-influenced values are parameterized via `?`. `reason LIKE "no metadata:%"` is a hardcoded literal, not user input. **PASS.**
*   **SQL injection — `fetch.py:251-253`:** `f"UPDATE ... video_id IN ({','.join('?'*len(due))})", (..., *due)` — `due` ids are from DB `video_id` column, not user input, and are parameterized as `?` placeholders. Dynamic placeholder count is safe pattern. **PASS.** Note: `due` could be empty, but guarded by `if due:` `fetch.py:250`.
*   **Authentication bypass:** No routes in diff. `pipeline/ingest/fetch.py` is backend worker, not HTTP handler. **N/A.**
*   **Rate limiting gaps:** `NO_METADATA_RETRY_S` reduced from 3600 to 900 — 4x more probes for stubs. At 48 probes/12h per dead video, with 100 dead videos = 4800 probes/12h = ~6.6/min. yt-dlp is local, not paid API, but YouTube could throttle. However `UNAVAILABLE_RETRY_S=6h` for real UNAVAILABLE still protects. Stub path is the only increased load, and it's bounded by `EXPIRY_H`. **Acceptable.**
*   **Secrets in code:** None. `fetch.py:38-42` constants, no keys. **PASS.**
*   **Unvalidated input to DB/filesystem/shell:** `video_id` in `pipeline_record(v)` `test_r122.py:50` — validated via `except ValueError` `fetch.py:247`. `detail[-200:]` `fetch.py:277` truncated, safe.

**Security: No issues.**

---

## SECTION 4: FRONTEND QUALITY

**N/A — No frontend code in diff.** `pipeline/ingest/fetch.py` and `tests/ingest/*` are pure backend. No UI to evaluate.

Score reflects absence, not failure.

---

## SECTION 5: BACKEND QUALITY

*   **DB operations — try/except with rollback:** `fetch.py:243-247` `try: pipeline_record_exists() except ValueError: continue` — No DB write in try, so no rollback needed. `q.x(UPDATE)` `fetch.py:251` — No explicit try/except. If `q.x` fails (DB locked), exception propagates to caller. Need to verify caller (`ingest_watch.py` not in diff) handles it. **P2 — caller must wrap `pipeline_sweep` in try/except.**
*   **External API calls — timeout/retry/graceful degradation:** `fetch.process` probe via `gate` (yt-dlp) — `kind=="no_metadata"` is graceful degradation (retry 900s, not crash). `pipeline_sweep` does `one glob + reads` — no YouTube request per docstring `fetch.py:237`. Correct.
*   **Cron/job failure handling:** `pipeline_sweep` returns `due` list; if `pipeline_record` read throws unexpected exception (not `ValueError`), loop would crash and sweep would abort, losing remaining `due` candidates. Should be `except Exception` with log. **P2.**
*   **Memory leaks:** `rows = q.rows(...)` loads all matching rows into memory. No `LIMIT`. If 10k rows match, memory spike. Should paginate or `LIMIT 500`. **P1.**
*   **Logging:** `q.event("pipeline_transcript_due", vid, None)` `fetch.py:254` — Good, queue event for observability. But `except ValueError: continue` has no log. `final` give-up (`next_at=10**9`) has no distinct log vs retry. Hard to debug why video was given up. **P2.**

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What Bloomberg/Coinbase/Blockworks would do differently:**

*   **Already excellent:** The fix is surgically precise. Using `EXPIRY_H` as give-up horizon instead of `tries` count is the correct abstraction — moments' life is the business invariant, not probe count. The `pipeline_sweep` clause that promotes a stub to due when pipeline has the record is elegant — it reuses existing transcript without extra YouTube cost. Tests are exemplary: `test_r122.py` reproduces the exact CoinDesk timeline (4 live probes + 2 stubs) and proves the fix.
*   **Missing — Observability for stub vs real UNAVAILABLE:** No metric distinguishes `no metadata` retry (transient stub) from `Private video` (permanent). A dashboard showing `UNAVAILABLE by reason` over time would have caught the CoinDesk incident before manual report. **Material.**
*   **Missing — Alert on pipeline/ingest divergence:** The bug was "watcher gave up, pipeline transcribed." There is no automated check that `pipeline_transcript exists AND watcher state==UNAVAILABLE/no metadata` — exactly what `pipeline_sweep` now fixes, but no alert if sweep finds such rows. Should emit `STATE` warning.
*   **Missing — `published_ts` fallback correctness:** `seen = published_ts or discovered_ts or now_ts` — If `published_ts` is `None` (common for stubs — yt-dlp gave no timestamp), `discovered_ts` is used. But `discovered_ts` is when *we* first saw it via RSS, which could be hours after publish. This extends the 12h window incorrectly. Should use `discovered_ts` only if `published_ts` is truly unknown, which is correct, but worth documenting that stub videos get longer life.
*   **Not missing — Performance:** 900s retry is correct tradeoff. 48 probes max is trivial.

---

## SECTION 7: SCORES

*   **Backend logic:** 92/100 — Correct fix, well-tested, minor N+1 and missing LIMIT.
*   **Frontend/UI:** N/A (no frontend in diff) — 0/100 if forced, but not applicable.
*   **Error handling:** 78/100 — `ValueError` swallowed without log; no `LIMIT`; no try/except around `q.x`.
*   **Security:** 98/100 — Parameterized queries, no secrets, no injection. -2 for increased probe rate without explicit throttle.
*   **Performance:** 85/100 — 4x probe increase bounded, but unbounded SELECT and N+1 reads.
*   **Law compliance:** 100/100 — No violations.
*   **World-class gap:** 82/100 — Fix is excellent, but missing observability/alerting for divergence.
*   **OVERALL:** 88/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | None | — | No P0. Diff is safe to ship.

P1 HIGH     | Add LIMIT to pipeline_sweep SELECT | `pipeline/ingest/fetch.py:239` | Unbounded SELECT + N+1 reads could stall watcher loop if partner ingests 10k videos; add `LIMIT 500` and paginate.

P1 HIGH     | Wrap pipeline_sweep loop body in try/except Exception with log | `pipeline/ingest/fetch.py:243-247` | Unexpected exception (e.g., filesystem error reading pipeline store) aborts entire sweep, losing all due candidates for that cycle.

P2 MEDIUM   | Log ValueError skip and final give-up distinctly | `pipeline/ingest/fetch.py:247,273-278` | Silent `continue` and `next_at=10**9` without log makes debugging why video never mined impossible; add `q.event` or logger.

P2 MEDIUM   | Add try/except around q.x UPDATE in pipeline_sweep | `pipeline/ingest/fetch.py:251` | DB locked error would crash sweep without rollback; caller should handle but sweep should be defensive.

P2 MEDIUM   | Document discovered_ts fallback extends window for stubs | `pipeline/ingest/fetch.py:274` | Stub has no published_ts, so discovered_ts (RSS time) is used; if RSS lagged, video gets extra life — correct but should be explicit in comment.

P3 LOW      | Consider metric for pipeline_sweep promotions | `pipeline/ingest/fetch.py:254` | Emitting `pipeline_transcript_due` event is good, but a counter `sweep_promoted_total` would enable alerting on divergence.

P3 LOW      | Truncate reason LIKE pattern to avoid false match | `pipeline/ingest/fetch.py:241` | `"no metadata:%"` could theoretically match a future reason starting with same prefix; use exact prefix check or store `unavailable_kind` column.

---

## SECTION 9: THE ONE THING

Stop counting tries and start counting time — you did, and it fixes the CoinDesk bug; now add a `LIMIT` and a log line so the next divergence is visible before a human reports it.

---

## SECTION 10: FINAL VERDICT

This code is ready for production. It correctly fixes the premature give-up of real streams that transiently return stubs, and the `pipeline_sweep` promotion is narrowly scoped to `no metadata` rows with pipeline records inside 12h. Ship it, then add a `LIMIT` to the sweep query and logging for the `ValueError` skip path.
