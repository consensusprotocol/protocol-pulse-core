# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 331.5 s, $0.025, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (Ruling 80 + Ruling 77 fixes)

**Branch:** `pp-ingest` | **Diff:** `e416cbfd` working tree | **Reviewer:** heimdall_muse (Cycle 2) | **Date:** 2026-11-14

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM caught the starvation risk (P1) that I under-weighted.** I noted the hook pass existed and flagged its correctness bugs, but I did not explicitly call out that `mine.py:mine_video` sharing a single `ThreadPoolExecutor` between moment and hook passes meant a long VOD's backfill could starve new uploads. GLM framed it as a resource-contention bug. The fix — `service.py:HOOK_WINDOWS=4` + `self.hook_windows` separate pool — is correct and I should have proposed it.

**GLM caught the missing `videos_hook` index.** I reviewed `queue.py:hook_due` for correctness (NULL handling, horizon) but did not check index coverage. A `SELECT ... WHERE state IN (...) AND hook_ts IS NULL AND published_ts >= ?` without an index on `(state, published_ts)` is a table scan on every 5s poll. Minor at current scale, real at 10k videos.

**GLM caught the `STATE` file write raising out of purge bookkeeping.** I reviewed `purge.py` for fail-open vs fail-closed but missed that `spend.write_purge_notice` inside `service._purge_blocked` could raise `OSError` and abort the purge's accounting. The fix (guard + log) is correct.

**Qwen's deep read of `carry_forward` single-process correctness was more thorough than mine.** I flagged C1 (altcoin inversion) correctly, but Qwen correctly noted the `wlock` + `fcntl.flock` interaction is sound for single-process and that the `fcntl` in `append` is redundant-but-safe. I left C6 truncated mid-sentence — sloppy.

**What I caught that they missed or under-weighted:** The `altcoin` inversion (C1) was mine alone at P0 — GLM and Qwen both missed it in Cycle 1. The consensus table confirms it was fixed. My C5 race analysis (TOCTOU on `hook_due` + `hook_inflight`) was more precise than GLM's BUG 1 (which misidentified the `submit` exception path as the issue).

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Reviewer | My Verdict | Why |
|---------|----------|------------|-----|
| **C1: `carry_forward` altcoin `is not False` inversion** | me P0 | **Agree with myself, fix confirmed** | `None is not False == True` conflates missing with true. Fix: `True in (a_new, a_old)` / `False if a_new is False else None` — earlier missing adds nothing, new missing stays missing (adapter refuses via L-m). Test `test_an_earlier_missing_value_adds_nothing...` proves it. |
| **GLM BUG 5: 4-14s gate systematically overruns on segment timing** | glm P0 | **Disagree — correctly refuted** | GLM assumed segment `end` trails spoken words. Measured on 2,588 ledger rows: caption estimate is median 2.3s *shorter* than 2.6 w/s estimate (p10 -6.9s, p90 +1.3s). No systematic overrun. The gate uses best available measure; builder re-judges with word timing. Dropped lengths now recorded (`dropped_s`). |
| **GLM BUG 3: hook cost double-counts** | glm P1 | **Partially agree — cosmetic, now documented** | `SUM(cost_usd) WHERE role='hook'` is cumulative by design. The log now says "for the video's hook passes so far" and column is documented as cumulative. Not a correctness bug. |
| **GLM BUG 1: `hook_inflight` leak on `submit` raise** | glm minor | **Agree it's benign** | `submit` only raises after `shutdown()`. At process exit, `hook_inflight` lifetime is irrelevant. |
| **GLM BUG 4: `role` param latent trap** | glm latent | **Agree — latent, not a bug today** | No caller passes `role` with `kind="hook"` today. Worth a comment or assert, not a fix. |
| **Qwen: `hook_due` NULL `published_ts` exclusion** | qwen | **Agree — correct by design** | `NULL >= ?` is NULL → excluded. `MINED` videos always have `published_ts` (fetch never reaches `TRANSCRIBED` without one). Ruling 80: no publish time → can't determine 12h window → don't hook-mine. |
| **Qwen: `role_hint` inheritance** | qwen | **Agree — by design** | Hook hint records that hook pass picked the span. A later re-mine should not un-pick it; dropping it would hide hook candidate from builder. |
| **Consensus: hook windows starvation** | glm P1 | **Agree — fixed correctly** | Separate `HOOK_WINDOWS=4` pool, moment passes keep rest. Newest uploads first preserved. |
| **Consensus: `videos_hook` index** | glm | **Agree — fixed** | `CREATE INDEX IF NOT EXISTS videos_hook ON videos(state, published_ts)` added. |
| **Consensus: purge STATE notice guard** | glm | **Agree — fixed** | `try/except OSError` around `write_purge_notice` in `_purge_blocked`. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 — `carry_forward` iterates ALL earlier lines for same `moment_id`, not just the latest (ledger.py:196).** If a video was mined 3 times (partial → partial → mined), `earlier` contains 3 lines for the same `moment_id`. The loop `for e in by.get(l["moment_id"], [])` unions flags from *all* of them. This is correct (fail-closed: union of all observations), but it means a single `altcoin=True` in any earlier pass permanently taints the moment — even if two later passes said `False`. This is intentional per the docstring ("either" for altcoin) but worth noting: there is no way to *clear* a flag once set. This matches the "fail closed" principle but could accumulate false positives over many re-mines.

**N2 — `hook_due` does not exclude `MINED_PARTIAL` videos whose `hook_ts` was set on a previous partial hook pass (queue.py:182).** `hook_ts IS NULL` means a video that completed a hook pass (even with `hook_rows=0` due to all windows failing after 3 tries) will never be retried. This is correct — `HOOK_TRIES=3` is the limit. But a `MINED_PARTIAL` video that later gets more moments (via `MINE_PARTIAL_RETRY_S`) will not get hooks for its new moments until... actually it will never, because `hook_ts` is already set. **This is a minor gap:** new moments from a later partial mining pass won't get hook evaluation. In practice low-impact (partial videos are rare, and their new moments are few), but it's a semantic gap worth documenting.

**N3 — `service._append` `since` calculation uses `discovered_ts - 86400` (service.py:271).** This is a 24h lookback for `video_lines`. If a video was discovered more than 24h ago and is being re-mined (partial retry at 72h horizon), its earlier lines fall outside `since` and won't be found for `carry_forward`. However, `MINE_HORIZON_S=72h` and `HOOK_HORIZON_S=12h` — a video discovered 72h ago being re-mined would miss its own earlier flags. **Mitigated:** `video_lines` is called with `since = discovered_ts - 86400`, so for a video discovered at T, it reads lines from T-24h onward. Since the video's own lines were all mined *after* T (discovery → probe → transcribe → mine), they are all within [T-24h, now]. So this is actually correct — the 24h margin is before discovery, not after. No bug.

**N4 — `mine.py:430-441` duration filter runs AFTER dedup but BEFORE `carry_forward`.** A hook candidate that is 15s (outside 4-14s) is dropped and never reaches `ledger.append` → never gets `carry_forward`. If the same span was previously mined as a moment (6-25s, no duration filter), its moment line exists in the ledger. The hook pass dropping it does not delete the moment line — correct. No bug, but worth confirming: the duration gate is a *write* gate, not a *delete* gate.

**N5 — No new P0/P1 findings.** The combined Cycle 1 analysis was thorough. The remaining issues are P2 or by-design.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Watch** | 9/10 | 9/10 | No change. RSS→playlist fallback, canary, backoff correct. |
| **Fetch** | 9/10 | 9/10 | No change. Age-gate terminal, rate-limit backoff, caption fetch correct. |
| **Mine (moments)** | 9/10 | 9/10 | No change. Windows, router, validator, overlap dedup correct. |
| **Mine (hooks)** | 6/10 | 8/10 | **Up.** C1 fixed, starvation fixed, index added, dropped lengths recorded. Remaining: N2 (partial re-mine hook gap) is P2. |
| **Ledger / Adapter** | 7/10 | 9/10 | **Up.** `carry_forward` altcoin fix verified, `wlock` + `carry_forward` + `flock` design validated. No gate waived. |
| **Purge** | 8/10 | 9/10 | **Up.** Fail-open closed, corrupt-record path fixed, STATE notice guarded, spec validation tightened. |
| **Coverage** | 9/10 | 9/10 | No change. Independent listing, unmeasured handling correct. |
| **Providers / Router** | 9/10 | 9/10 | No change. Spend freeze, circuit breaker, throttle, cache correct. |
| **Overall** | 7.5/10 | **8.5/10** | All P0/P1 from Cycle 1 fixed and cross-validated. |

---

## 5. FINAL PRIORITY LIST

| Priority | File:Line | Issue | Status |
|----------|-----------|-------|--------|
| **P0** | `ledger.py:200` | `carry_forward` altcoin `is not False` inversion — missing key becomes `True` | **FIXED** — `True in (a_new, a_old)` / `False if a_new is False else None` |
| **P1** | `service.py:50-51` | Hook windows shared back-end slots with moment passes — starvation | **FIXED** — `HOOK_WINDOWS=4` separate pool |
| **P1** | `queue.py:90` | `hook_due` had no index — table scan every 5s | **FIXED** — `videos_hook(state, published_ts)` |
| **P1** | `service.py:461-465` | `write_purge_notice` could raise out of purge bookkeeping | **FIXED** — guarded + logged |
| **P1** | `mine.py:438-439` | Dropped hook lengths not recorded — edges unmeasurable | **FIXED** — `dropped_s` in report + log |
| **P2** | `queue.py:182` | `MINED_PARTIAL` video that completes hook pass then gets new moments via partial retry never gets hooks for new moments (`hook_ts IS NOT NULL` blocks retry) | Open — document or reset `hook_ts` on partial re-mine |
| **P2** | `mine.py:381` | `role` param can override `kind`'s role — latent trap if caller passes `role="mine"` with `kind="hook"` | Open — add `assert role is None or role == KINDS[kind]["role"]` |
| **P2** | `service.py:380-396` | `hook_once` reads `hook_due` outside `hlock` — TOCTOU where two concurrent `hook_once` calls both see same video | Benign — `hlock` serializes `inflight` check, second caller skips. No fix needed. |

**No open P0 or P1.**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `carry_forward` altcoin fix was the highest-leverage change — a single boolean inversion that could silently taint moments as altcoin (or fail to propagate a real altcoin flag) across every hook and re-mine pass for the lifetime of the ledger — and it is now fixed and tested.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

**Conditions:**
1. The backfill over the current 12h window must run on this audited code (per ruling 80: "the backfill over the current window may run on the audited code only") — do not backfill on a later un-audited commit.
2. Monitor `dropped_s` in the first 24h of hook passes — if the 4-14s gate drops >50% of hook candidates, revisit the duration estimate (segment timing vs word timing).
3. P2 `MINED_PARTIAL` hook gap should be documented in `INGEST_DESIGN.md` or fixed before the next release — it will not affect the initial backfill but will affect long-running operation.

**No blocking issues remain.** The fail-closed discipline, concurrency design (`wlock` + `carry_forward` + `flock`), and purge safety are production-grade.
