# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 197.1 s, $0.004, finish stop)

# PROTOCOL PULSE: CODE AUDIT — pp-ingest r120 (49fec073)

## SECTION 1: CORRECTNESS

**Claimed flow:** `post_live` with pipeline record → pass through all probe checks → `take_pipeline_transcript` → `TRANSCRIBED`. `post_live` without record → `LIVE` re-probe. `is_live` → always `LIVE`. `post_live` with refused copy → `LIVE`. Sweep + stall cover `post_live` only.

**Walkthrough:**

1.  **Live gate `fetch.py:295`:** `if live == "is_live" or (live == "post_live" and pipeline_transcript(...) is None)` — Correct. `is_live` always trapped. `post_live` trapped only when no record. Falls through when record exists. Matches spec bullet 1.
2.  **Duration fallback `fetch.py:308-310`:** `if live == "post_live" and not (isinstance(dur, (int,float)) and dur>0): found = pipeline_transcript(...); dur = common["duration"] = found[1].get("duration")` — Correctly handles YouTube returning `None` duration while processing. Uses pipeline's recorded duration. Verified by `test_r120.py:57-62`.
3.  **Take path `fetch.py:324-331`:** `if take_pipeline_transcript(...): return _store_captions` then `if live == "post_live": set LIVE` — Correct ordering. Ensures no caption download on `post_live` refusal path. Caption download code at `fetch.py:332+` is unreachable for `post_live` on both success (early return) and failure (early LIVE return). Satisfies "No caption download for a post_live video on any path."
4.  **Sweep `fetch.py:227-244`:** SQL `WHERE (state IN (?,?) OR (state=? AND live_status=?))` with params `(PROBE_RETRY, CAPTIONS_PENDING, LIVE, "post_live")` — Correctly expands sweep to include `LIVE/post_live`. Update `WHERE state IN (?,?,?)` includes `LIVE` — Correct, otherwise `next_at` would not be updated for the newly selected rows. Returns `due` correctly.
5.  **Stall `stall.py:57-59`:** `WHERE (state IN (...) OR (state=? AND live_status=?))` — Correctly mirrors sweep. `WAITING` tuple unchanged, `RETRYABLE` adds `Q.LIVE` at `stall.py:28` — Required for `stall.act()` to make due. `why()` at `stall.py:52-53` adds correct label.
6.  **Edge: `pipeline_transcript()` called twice** — Once at line 295, once at 309, potentially third inside `take_pipeline_transcript` at 324. This is 2-3 filesystem reads (`glob` + `json.load`) per `post_live` probe. Not a correctness bug, but wasteful. See N+1 below.
7.  **Edge: `common["duration"]` mutation** — At line 310, `common["duration"]` is set from pipeline record. `common` is spread into `q.set_state(**common)` on all subsequent terminal states (`SEEN_OLD`, `TOO_LONG`, `DUPLICATE`, `LIVE`). This is intentional and correct — ensures DB row gets a duration even when probe gave none.
8.  **Edge: `take_pipeline_transcript` refusal** — At line 327-331, if copy differs, it sets `LIVE` with `title_canon=tc` and `**common` (which includes duration). Correctly preserves metadata. `made == []` assertion in test confirms no download.
9.  **Race condition:** `pipeline_sweep` does `SELECT` then loop `pipeline_transcript()` then `UPDATE ... WHERE video_id IN (...)`. Between SELECT and UPDATE, another worker could change state. However `UPDATE ... WHERE next_at > ? AND state IN (...)` is idempotent and guarded by `next_at > now_ts` — safe. No lost update that causes data corruption, at worst a redundant event.
10. **Empty DB / bad input:** `pipeline_transcript()` returns `None` on missing record — handled. `found[1].get("duration")` at line 310 — if `found` is `None`, `dur` becomes `None` via ternary, then falls through to `PROBE_RETRY` at line 311. Correct. `j.get("duration")` handles missing key. `live_status` missing → `live` is `None` → no special handling → normal VOD path. Correct.

**Verdict: Logic is correct. No silent failures, no wrong variable names. All 7 mutations killed corroborates.**

**N+1 Query:** `pipeline_sweep` at `fetch.py:233-237` loops `for r in rows: pipeline_transcript(vid, ...)` — This is a filesystem glob+read per row inside a loop. For N waiting videos, N disk I/Os. Acceptable for small N (sweep runs once per ingest cycle, N < ~50), but is technically N+1. Not a DB N+1 (the DB query is single). **Not production-breaking.**

**Race: Concurrent `fetch.process` on same `vid`** — `q.set_state` is presumably atomic (single UPDATE). No transaction wrapping `pipeline_transcript` + `take_pipeline_transcript` + `set_state`. If two workers probe same `post_live` video simultaneously, both could `take_pipeline_transcript` and both write staging copy. `take_pipeline_transcript` does `shutil.copyfile` — last writer wins, but content is identical (same source record), so harmless. No corruption.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest, ETag/backoff, ledger, Shorts/live handling, durable queue** | **COMPLIANT** | `fetch.py:295` explicitly handles `is_live` vs `post_live` per spec. `LIVE_REPROBE_S` backoff preserved. `pipeline_sweep` respects `EXPIRY_H`. No change to RSS/ETag/ledger logic. |
| **BUILD: captions into SAME store format via writer, staging copy, never main tree** | **COMPLIANT** | `take_pipeline_transcript` (unchanged, called at 324) handles staging copy. `test_r120.py:32` asserts `staged(v)` exists and `meta.json` written via `pipeline.ingest.fetch`. No main tree write. |
| **BUILD: first-pass mining sentence ids, bounded concurrency, 429/503 backoff, $460 cap 90% tripwire NOTIFY never halt** | **COMPLIANT** | No change to mining path. This diff is fetch/sweep/stall only. |
| **BUILD: append-only moment ledger matching pp.moment/1, adapter best unused since T** | **COMPLIANT** | No change to ledger. |
| **BUILD: daily coverage check; blind A/B generator/judge different models** | **COMPLIANT** | No change. |
| **L-x NO SINGLE MODEL, ULTRON FIRST, >=2 back-ends, provider interface, no vendor name outside config, no GPU use** | **COMPLIANT** | No model/provider code touched. No GPU code. No vendor strings in diff. |
| **L-l strict schema, ids validated, NOTHING REPAIRED; failed call never default/pass** | **COMPLIANT** | No model reply handling in diff. |
| **L-j/L-m fail closed; nothing measured never pass** | **COMPLIANT** | `fetch.py:298-302` — `pub_ts is None` → `PROBE_RETRY`, not pass. `dur` check at 311 → `PROBE_RETRY`. `post_live` still runs these checks (test `test_a_stream_over_still_meets_every_other_check` verifies `SEEN_OLD`/`TOO_LONG`). Fail-closed preserved. |
| **L-h/L-k transcript text as spoken, entities decoded, split tokens joined, canonical form, never rewritten** | **COMPLIANT** | `take_pipeline_transcript` copies verbatim; `test_r120.py:44-48` verifies refusal when copy differs (integrity check). No rewriting. |
| **L-e word timing at cut time** | **COMPLIANT** | Design note explicitly states word timing stays pipeline's job at cut time. This diff does not touch timing. |
| **L-u hard exclusions flagged before ranking** | **COMPLIANT** | No change to ranking/exclusion. |
| **L-v moment never spans speaker change; re-uploads excluded; time-sensitive needs publish time** | **COMPLIANT** | `fetch.py:298-302` publish time check still runs for `post_live`. Re-upload duplicate check at 320-323 still runs. |
| **Secrets: keys by name from env file, never printed/logged/written** | **COMPLIANT** | No secret handling in diff. |
| **SPEND FREEZE: no paid frontier vendors, Heimdall→local only, queue if both down, 90% NOTIFY never halt** | **COMPLIANT** | No vendor calls in diff. |

**Overall Law Compliance: COMPLIANT — No violations detected in this diff.**

---

## SECTION 3: SECURITY

- **SQL Injection:** `fetch.py:230-231` and `243-244` use parameterized queries (`?` placeholders) for all values. `f"({','.join('?' * len(due))})"` interpolates only `?` placeholders, not user input — `due` values are bound as parameters in `tuple(due)`. `stall.py:57-60` same pattern. **No injection.**
- **ORM filter() injection:** Not applicable — raw `q.rows`/`q.x` with parameterization.
- **Authentication bypass:** Not applicable — this is a backend ingest pipeline, no HTTP routes in diff.
- **Rate limiting gaps:** No change to rate limiting. `LIVE_REPROBE_S` (20 min) and `pipeline_sweep` (no YouTube request) preserve existing limits. No new external API calls added.
- **Secrets in code:** No secrets, keys, tokens, or passwords in diff. No hardcoded credentials.
- **Unvalidated input → DB/filesystem/shell:** `vid` comes from `q.rows` (DB-sourced, not user input). `pipeline_transcript(vid, channel_id)` uses `vid` to glob filesystem — `vid` is YouTube ID format (11 chars, validated by `transcript_store` which raises `ValueError` caught at `fetch.py:238`). No shell execution. No path traversal — `vid` is not user-controlled free text.
- **Filesystem:** `shutil.copyfile` inside `take_pipeline_transcript` — source is pipeline store (trusted), dest is staging copy (controlled). No user-controlled paths.

**Security: No issues found.**

---

## SECTION 4: FRONTEND QUALITY

**Not applicable.** This diff touches `pipeline/ingest/fetch.py`, `pipeline/ingest/stall.py`, and `tests/ingest/test_r120.py` only. No frontend code, no UI, no JS, no CSS, no HTML. No spec layout to match.

**Score: N/A — No frontend in scope.**

---

## SECTION 5: BACKEND QUALITY

- **DB operations try/except + rollback:** `pipeline_sweep` at `fetch.py:233-238` wraps `pipeline_transcript()` in `try/except ValueError: continue` — Correct, prevents one bad ID from aborting sweep. However, `q.x(UPDATE ...)` at line 243 has no explicit try/except/rollback. If `q` is a wrapper with autocommit, this is fine. If it uses transactions, a failure mid-update could leave partial state. **Need to verify `queue.py` transaction handling** — request `pipeline/ingest/queue.py: x(), rows(), set_state()` to confirm rollback behavior. Not a violation visible in diff alone.
- **External API calls timeout+retry+graceful degradation:** No new external API calls. `fetch.process` probe data `j` is already fetched by caller with gate. `pipeline_transcript()` is local filesystem read — no timeout needed. Existing `LIVE_REPROBE_S` retry preserved.
- **Cron job failure handling:** `pipeline_sweep` and `stall.check` are called from cron/watcher. Both handle empty results gracefully (`if not rows: return`, `if not due: skip update`). No crash on empty DB.
- **Memory leaks:** No large objects per-request. `rows` is a small list of dicts. No leak.
- **Logging:** `q.set_state(..., reason=...)` at lines 296, 328 provides structured reason strings. `q.event("pipeline_transcript_due", ...)` at line 246 logs sweep actions. Adequate for debugging. No `print` or `logger` calls that leak secrets.
- **Idempotency:** `pipeline_sweep` UPDATE is `WHERE next_at > ?` — safe to run repeatedly. `take_pipeline_transcript` is idempotent (same source → same dest). Good.

**One concern:** `pipeline_transcript()` called up to 3x per `post_live` video in `fetch.process` (line 295, 309, inside `take_pipeline_transcript`). Each call does filesystem I/O. Should cache result in local variable. Minor performance issue, not correctness.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

For a premium Bitcoin intelligence product, this diff is **narrowly scoped and well-executed** for its purpose (fixing a 53-minute mining delay on post_live streams). What matters:

- **Already excellent:** The forensic timeline in the diff header (kh3U_15pFZc, 3,205s late, 12:26-14:26 post_live window) is exactly what Bloomberg/Coinbase would demand — measurable, reproducible, root-caused. The mutation testing (M36-M42, 7/7 killed) is above industry standard. The test suite covers all branches (with record, without, is_live, no duration, too old, too long, refused copy, sweep, stall).

- **Missing with material impact:**
  1. **No metric/alert on post_live delay itself.** The fix prevents future delays, but there's no ongoing histogram of `transcript_record_ts → mined_ts` latency. A Bloomberg Terminal would have a p50/p95 latency dashboard with alerting at >600s. Currently relies on r119's manual sweep.
  2. **No YouTube API quota accounting for the extra `pipeline_transcript` reads.** Trivial now (local FS), but if pipeline store moves to remote (S3/GCS), the 2-3x reads per post_live probe become billable. A `found` cache variable would future-proof this.
  3. **Stall message is generic.** `"STREAM OVER, ITS VIDEO STILL PROCESSING"` doesn't include how long it's been post_live or when pipeline record arrived. An operator seeing this at 02:00 ET needs to know if it's 5 min or 50 min old to triage.

- **Not missing:** Real-time UI, mobile, or pricing — irrelevant to ingest pipeline.

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **94/100** | Correct, all branches covered, mutations killed. -6 for redundant `pipeline_transcript()` calls (3x I/O where 1 suffices). |
| **Frontend/UI** | **N/A** | No frontend in diff. |
| **Error handling** | **92/100** | Fail-closed preserved, ValueError caught, refused copy handled, empty DB safe. -8 for no explicit DB rollback on UPDATE failure (needs verification). |
| **Security** | **98/100** | Parameterized queries, no secrets, no injection, no auth bypass. -2 for no explicit validation that `live_status` value is from allowlist (relies on YouTube API contract). |
| **Performance** | **88/100** | No new external calls, sweep is single glob+read. -12 for 2-3x redundant filesystem reads per post_live probe; no caching. |
| **Law compliance** | **100/100** | All governing laws compliant. No violations. |
| **World-class gap** | **82/100** | Fix is precise and well-tested. Gap is observability (no latency histogram/alert) and minor operator UX (stall message lacks duration). |
| **OVERALL** | **92/100** | Production-ready. Minor performance polish only. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No P0 issues. Code is safe to ship.
P1 HIGH     | Cache pipeline_transcript result in fetch.process | pipeline/ingest/fetch.py:295,308,324 | 3 filesystem reads per post_live probe where 1 suffices; will become billable if store moves remote and adds ~200ms/probe under load
P1 HIGH     | Verify queue.py transaction rollback on UPDATE failure | pipeline/ingest/queue.py: x() | If q.x() fails mid-sweep, partial next_at updates with no rollback could leave inconsistent due states
P2 MEDIUM   | Add post_live age to stall message | pipeline/ingest/stall.py:52-53 | Operator cannot triage "STREAM OVER" without knowing if it's 5 min or 50 min old; include now_ts - published_ts or discovered_ts delta
P2 MEDIUM   | Add latency histogram metric (transcript_ts → mined_ts) | pipeline/ingest/fetch.py:246 or mining completion | r119's manual sweep is the only latency detector; p95 alert at >600s would catch next post_live-class bug automatically
P3 LOW      | Deduplicate live_status string literal "post_live" to constant | pipeline/ingest/fetch.py:230,295,308,327 + stall.py:59 | 5 occurrences of magic string; typo risk, should be config.LIVE_POST or Q.POST_LIVE
P3 LOW      | Add comment explaining why caption download is skipped for post_live | pipeline/ingest/fetch.py:327-331 | Future reader may not understand why LIVE return skips captions; one-line comment prevents accidental "fix"
```

---

## SECTION 9: THE ONE THING

**Cache the `pipeline_transcript()` result in a local variable instead of calling it 3 times per `post_live` probe — it's the only flaw in an otherwise exemplary fix.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** It correctly fixes the 53-minute post_live mining delay with minimal, well-tested changes that preserve all existing invariants (no caption download for post_live, is_live never taken, all probe checks still run). Ship it now; address the redundant filesystem reads (P1) in the next cleanup pass — it will not break production as-is.
