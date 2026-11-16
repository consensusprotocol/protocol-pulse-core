# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 119.7 s, $0.003, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT — pp-ingest r120 (49fec073)
# Reviewer: heimdall_muse (Cycle 2 Final)

---

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Honest delta from my Cycle 1:**

1.  **Quantified the 3x read as fixable P1, not just "wasteful":** I noted at Cycle 1 §1.6 that `pipeline_transcript()` was called 2-3x per `post_live` probe (line 295, 309, inside `take_pipeline_transcript` at 324) and dismissed it as "Not a correctness bug, but wasteful. Acceptable for small N." Both other reviewers flagged it as P1 performance. Claude's consensus confirms it was **fixed**: read once into `found` and pass `found=` to `take_pipeline_transcript(found=)` which still re-reads/re-hashes the *copy* before `os.link` for integrity. I under-scored it. The fix is correct — the re-read of the copy is required (TOCTOU / hash verification), the re-read of the source is not. Test `test_a_stream_over_reads_the_pipelines_record_once` + M43 killed proves it.

2.  **Sweep atomicity proof:** I noted the sweep race as "safe, at worst redundant" but did not prove atomicity. Muse's P1 "q.x() could leave partial next_at updates with no rollback" was correctly **refuted** by Claude: `queue.py` opens SQLite with `isolation_level=None` — each statement is its own transaction, so the `UPDATE ... WHERE video_id IN (...)` is all-or-nothing. I should have cited that invariant in Cycle 1 instead of hand-waving.

3.  **Qwen's explicit race walkthrough (transcript appears between line 295 and 309):** I covered the concurrent `fetch.process` race but not the intra-probe race where the pipeline writes the record between the live-gate check and the duration fallback. Qwen correctly walked it: first call returns `None` → would stay `LIVE`, but second call would find it. With the Cycle 2 fix (single `found`), this race collapses to one read — behavior is now deterministic per probe, sweep picks it up next cycle. I missed stating this explicitly.

**What I caught that they initially under-weighted:** The `common["duration"]` mutation propagation to all terminal states (`SEEN_OLD`, `TOO_LONG`, `DUPLICATE`, `LIVE` refusal) — I documented this at §1.7 as intentional/correct. Neither other Cycle 1 summary highlighted it, but it's load-bearing for the `None` duration while processing case (test_r120.py:57-62).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Agree? | Why |
|---------|--------|-----|
| **Both: `is_live` never taken, `post_live` without record stays `LIVE`, no caption download on any `post_live` path** | **Agree** | Verified at `fetch.py:295` gate + `fetch.py:324-331` early returns. Caption download at 332+ unreachable for `post_live`. `is_live` trapped unconditionally. |
| **Both: `post_live` with record runs all probe checks before take** | **Agree** | Duration fallback at 308-310, then `SEEN_OLD`/`TOO_LONG`/`DUPLICATE` checks, *then* `take_pipeline_transcript`. Correct ordering — prevents ingesting too-long/duplicate streams just because pipeline has them. |
| **Both: Sweep + stall never touch `is_live`** | **Agree** | SQL `OR (state=? AND live_status=?)` with params `(LIVE, "post_live")` — `is_live` excluded by `live_status` predicate. `stall.py:28` `RETRYABLE` adds `Q.LIVE` only for `post_live` label at 52-53. |
| **Both P1: 3x read of pipeline record** | **Agree, now Fixed** | Was wasteful, now fixed to 1x source read. See §1.1. |
| **Muse P1: partial `next_at` updates with no rollback** | **Disagree — Refuted** | Claude correctly refuted. `isolation_level=None` → single-statement transaction → atomic. No partial update possible. My Cycle 1 "safe" was right for wrong reason; now proven. |
| **Qwen: duration fallback `found is None` → `PROBE_RETRY` is safe** | **Agree, now moot** | With single `found`, if `found is None` we never enter the `post_live` take path at all (we took the `LIVE` branch at 295). The `found[1].get("duration") if found else None` ternary is now dead code for that branch — cleaner. |
| **Qwen: sweep handles race where transcript appears between `process` and `sweep`** | **Agree** | `pipeline_sweep` at `fetch.py:233-240` re-checks `pipeline_transcript()` per row and `continue`s if `None`. Correctly makes due only when record exists. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Nothing new that is P0/P1.** Combined analysis + fix leaves one P2 and one observation:

1.  **P2 — `common` mutation still couples duration to `LIVE` refusal path:** At `fetch.py:310` `common["duration"] = found[1].get("duration")` mutates the dict that is later spread into `q.set_state(..., **common)` for the `LIVE` refusal at 327-331. This is *correct* (we want DB to have duration even on refusal), but it means a pipeline record with `duration: null` or missing key will write `duration=None` to DB, which then hits `PROBE_RETRY` on *next* probe (line 311). That's the right behavior — retry until YouTube reports duration or pipeline record is fixed — but worth a comment. Not a bug.

2.  **Observation — `pipeline_sweep` N filesystem reads remain, but now bounded and justified:** Sweep still loops `for r in rows: pipeline_transcript(vid, ...)` — N `glob+read` per sweep. This is *not* the same as the fixed per-probe 3x read. Sweep must check each candidate row individually because the pipeline store is filesystem-sharded by channel, not queryable by SQL. N < 50 per cycle, once per ingest cycle, not per video. Acceptable. No DB N+1.

3.  **No new Law violations:** No model/provider/GPU/cost code touched. `LIVE_REPROBE_S` backoff preserved. Staging copy via `os.link` + hash check preserved. Ledger untouched.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness (fetch live gate + duration fallback + take/refusal)** | 9/10 | **10/10** | Single-`found` fix removes redundant reads and intra-probe race; all 7 original mutations + M36-M43 (8/8) killed; 431 ingest tests pass |
| **Sweep / Stall (queue + expiry)** | 9/10 | **10/10** | Atomicity proven (`isolation_level=None`); `LIVE/post_live` predicate correct; `RETRYABLE` + `why()` label correct |
| **Performance** | 7/10 (P1 wasteful) | **9/10** | Per-probe 3x → 1x source read fixed; sweep N reads remain but justified/bounded |
| **Law Compliance (BUILD/L-x)** | 10/10 | **10/10** | No change — still compliant |
| **Test/Mutation Coverage** | 9/10 | **10/10** | New test `test_a_stream_over_reads_the_pipelines_record_once` + M43 killed closes gap |

**Overall: 9.8/10** (was 9.0/10)

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — Must fix before ship:**
* None. No silent failures, no wrong variable, no data corruption, no Law violation.

**P1 HIGH — Should fix before ship:**
* None remaining. The one P1 (3x read) is fixed and verified.

**P2 MEDIUM — Fix if time, or next cycle:**
* `fetch.py:308-310` — Add comment explaining `common["duration"]` mutation propagates to `LIVE` refusal and `PROBE_RETRY` paths. Prevents future regression where someone "cleans up" the mutation.
* `fetch.py:233-240` `pipeline_sweep` — Consider adding `LIMIT` or metric log for `len(rows)` to make N boundedness observable. Not blocking.

**P3 LOW — Nit:**
* None.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Already shipped:** read the pipeline's record once per probe and hand `found` to `take_pipeline_transcript(found=)` — it fixed the 53-minute `post_live` mining delay without breaking `is_live` isolation, probe checks, or the no-caption-download invariant.

## 7. PRODUCTION READY?

**Yes — with no conditions.**

* All 431 `tests/ingest` pass, M36-M43 8/8 killed, new single-read test passes.
* `is_live` never taken, `post_live` without record waits as before, `post_live` with record passes all probe checks then takes via staging copy + `os.link` + hash.
* Sweep and stall correctly cover `LIVE/post_live` only, atomic via `isolation_level=None`.
* No Law violations, no P0/P1 remaining.
