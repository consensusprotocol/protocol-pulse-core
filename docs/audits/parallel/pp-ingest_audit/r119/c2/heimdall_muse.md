# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 118.1 s, $0.003, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT — pp-ingest r119 / 87b3efeb

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest delta vs my Cycle 1:**

1. **Qwen's initial SQL-injection scare -> self-correction:** Qwen flagged `queue.py:due()/hook_due()` parameter mismatch, then correctly walked it back. I correctly called it safe in Cycle 1 (parameter order `states + clock + f + limit` matches placeholder order `states + clock + f + limit`), but I under-documented *why* — I should have explicitly enumerated the 4 binding groups as Qwen did. No miss on verdict, miss on proof rigor.

2. **Consensus "Fixed" C1-1 transcript_lag_s:** I listed the sweep/probe/mine flow as correct but did not flag the *unmonitored 10-minute guarantee* as a P1. Muse did (Section 9). The Cycle 1 consensus correctly records this as now fixed: `transcript_lag_s` column + service log + cycles line 2, with zone-aware `acquired_at`, tests `test_transcript_lag_reads_only_a_time_with_its_zone` and `test_a_video_mined_past_10_minutes_from_its_transcript` (700s LATE / 42s not). I treated correctness as "does it move next_at correctly" and missed observability as correctness for a ruling with an SLA. That was my miss.

3. **Qwen's LIMIT concern and Muse's SQLITE_MAX_VARIABLE_NUMBER / tier-ordering P2s:** I noted N+1 is bounded/disclosed but did not quantify the SQLite variable limit (32,766 on 3.37.2) or the tier 1-before-2 ordering nuance. Both are valid P2s I should have recorded. I dismissed scale concerns too quickly with "expected <50" without citing watcher rate (60-100/day => few dozen in 12h window, 12 at 12:02 stall).

**What I caught that they initially missed/misframed:**
- Qwen's P1 "add LIMIT to sweep SELECT" is correctly refuted in consensus: `WHERE state IN (PROBE_RETRY,CAPTIONS_PENDING) AND next_at > now AND COALESCE(...) >= now-12h` already bounds to ~dozens; `LIMIT` without `ORDER BY` starves tail. I had this right.
- Muse's P1 "widen sweep except to OSError" is correctly refuted: `pipeline_transcript()` already catches `OSError, ValueError, KeyError, TypeError, AttributeError` per file around `open/json.load/hash`; `glob` on unreadable dir returns `[]`; sweep's `except ValueError` is only for `transcript_store` ID validation pre-path. I had this right — a corrupt file costs one video, not the sweep (`test_the_sweep...w4`).

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **Muse: P0 none, ready for production** | **Agree** | No bypass of `fetch.process()` checks (Short/live/upcoming/age/length/duplicate), no YouTube call in sweep, gate-aware, race-safe UPDATE re-check. |
| **Muse P1: 10-min guarantee unmonitored** | **Agree — now Fixed** | Was a real gap. Fix verified: new column, log `"N s from its transcript" / "(LATE: past 600s)"`, cycles line 2, zone-aware time. |
| **Muse P1: OSError aborts sweep** | **Disagree — Refuted** | Evidence in `fetch.py:pipeline_transcript` inner try/except + `glob` semantics. Test with broken record proves isolation. |
| **Qwen P1: SQL injection / param mismatch in `queue.py:177-188,199-207`** | **Disagree — No bug** | Qwen self-corrected. Binding order is correct. I verified: `q=f"state IN ({q}) AND next_at <= ? ORDER BY {order}...LIMIT ?"` with `tuple(states)+(clock,)+f+(limit,)` is left-to-right correct. Parameterised, no injection. |
| **Qwen P1: Add LIMIT to sweep SELECT** | **Disagree — Recorded not Fixed** | Consensus reasoning is correct: natural bound is 12h * 2 states; LIMIT would need deterministic ORDER BY to avoid starvation. Current N+1 is bounded. |
| **Muse P2: SQLITE_MAX_VARIABLE_NUMBER** | **Agree — Recorded** | `fetch.py:238` builds `IN (?,?,...)` with `len(due)` placeholders. Limit 32,766 >> realistic `due` (dozens). Not actionable, but worth recording. |
| **Muse P2: tier 1 before tier 2** | **Partially Agree — Recorded** | Ruling says "Bitcoin channels first" — tiers 1-2 both qualify per `BITCOIN_TIER_MAX=2`. Strict tier-1-first would be `ORDER BY tier ASC, CASE...` but spec does not require it. Current `CASE WHEN channel_id IN (...) THEN 0 ELSE 1 END` satisfies ruling. Enhancement, not bug. |
| **My Cycle 1: `_first_ids` data race** | **Maintain — Low** | `service.py:817-830` `_first()` unsynchronized read/write. Benign (GIL atomic assign, redundant `watch.registry()` call, last-write-wins same result) but technically a race. No change needed. |
| **My Cycle 1: N+1 confirmed but bounded** | **Maintain** | `fetch.py:230-236` one glob+optional json.load per waiting video, throttled 60s. At 60-100 uploads/day, <50 globs/sweep is trivial. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Nothing P0/P1 new.** Combined analysis closes the loop. Two low-severity observations not raised in Cycle 1:

1. **`service.py:255-260` — `_last_sweep = now` before `pipeline_sweep()`:** If sweep throws (e.g., DB locked), next sweep delayed 60s. Intentional anti-spin, but masks transient failures. Mitigated by new `transcript_lag_s` LATE logging — operator will see lag grow. No code change needed; ensure `pipeline_sweep` never lets `OSError` escape (it doesn't — see refutation above).

2. **`fetch.py:238` — `IN` clause size vs. `UPDATE` atomicity:** Bulk `UPDATE ... WHERE video_id IN (...)` is single statement, atomic in SQLite. No partial-update risk. If `due` ever approached thousands, chunking would be needed for `SQLITE_MAX_VARIABLE_NUMBER`, but with 12h window this cannot happen. Documented as P2.

3. **`queue.py:180,204` — `first` empty string handling:** `order = f"CASE ... , " if f else ""` leaves `ORDER BY COALESCE(...)` identical to pre-r119. Verified no trailing comma bug. Correct.

No new security, correctness, or liveness issues.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness (sweep → due → probe)** | 9/10 | 9.5/10 | Race-safe UPDATE, no bypass confirmed by both reviewers + consensus; +0.5 for verified `transcript_lag_s` observability closing SLA gap |
| **Security (SQLi, injection)** | 9/10 | 10/10 | Qwen scare refuted with proof; all queries parameterised |
| **Performance / Scale** | 7/10 | 8/10 | N+1 bounded by 12h window + 60s throttle; watcher rate quantifies bound; SQLITE limit recorded |
| **Reliability / Fault isolation** | 8/10 | 9/10 | Per-file exception isolation proven; `glob` semantics verified; gate check prevents sweep when blocked |
| **Observability** | 6/10 | 9/10 | C1-1 fixed: `transcript_lag_s` column + log + cycles line 2 with zone-aware time |
| **Overall Ship Risk** | Medium-Low | **Low** | Two Cycle 1 P1s resolved (one fixed, one refuted); remaining P2s are record-only |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — Must fix before ship:**
*None.* No data loss, no bypass, no injection, no liveness break.

**P1 HIGH — Should fix before ship:**
*None remaining.* C1-1 (transcript_lag_s monitoring) is **Fixed** with tests. Qwen/Muse P1s are **Refuted** with evidence.

**P2 MEDIUM — Record / Nice-to-have (do not block ship):**
- `fetch.py:238` — Document `SQLITE_MAX_VARIABLE_NUMBER=32766` assumption; if `due` ever >1000, chunk `IN` clause. Current bound makes this theoretical. *Recorded.*
- `service.py:817-830` — Optional: make `_first()` tier-ordered (`ORDER BY tier ASC`) if product wants tier 1 strictly before tier 2. Current `IN (...)` satisfies "Bitcoin first" ruling. *Recorded.*
- `service.py:255` — Optional: move `_last_sweep = now` to after successful sweep, or log sweep exception, to avoid 60s blind window on transient DB error. Low value given new LATE alerting. *Recorded.*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Already shipped:** adding `transcript_lag_s` (zone-aware `acquired_at` → `rows` → log → cycles line 2) — it turns the 13:05 ET 10-minute ruling from an unmonitored hope into a measured SLA.

## 7. PRODUCTION READY?

**Yes — with conditions met (they are).**

Conditions:
1. `transcript_lag_s` column, log, and cycles line 2 present with zone-aware `acquired_at` — **Verified Fixed** (tests pass).
2. Sweep remains gate-aware (`not self.gate.open_for()`) and throttled (`PIPELINE_SWEEP_S=60`) — **Verified** `service.py:255`.
3. No change to `fetch.process()` gate — probe still runs all r118 checks — **Verified** `service.py:267-280`.

All conditions satisfied on r119. Ship it.