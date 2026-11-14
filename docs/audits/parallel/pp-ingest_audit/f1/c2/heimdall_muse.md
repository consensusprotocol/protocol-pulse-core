# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 359.9 s, $0.028, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (F1)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting vs my Cycle 1:**

My Cycle 1 was the longest (602s) and covered the most ground — I was the only reviewer to flag the `providers.py:851` `cfg.get("enabled")` vs `backend.enabled()` divergence, the `ledger.py:offset_before` bisection degradation, and the `service.py:584` `_conv` cache staleness. But I missed or under-weighted what GLM caught:

1. **Crash-path tight loop (GLM P0 → C1-1):** I verified `check_calibrated` is set *after* calibration returns and concluded "no tight loop" — but I only considered the happy path. I did not consider `watcher_checkers` *raising*. If it raises, `check_calibrated` is never updated, so `check_once` (every 30s) would re-enter calibration every tick. With the old cached calibration this was free; with live calibration it's 32 model calls every 30s — a spend and load bomb. GLM was right to call this P0. I should have caught it.

2. **Wrong answers discarded (GLM P1 → C1-2):** I noted the schedule logic was correct but did not flag that `service.py`'s old `kv_set` only stored `model/right/of/unmeasured` — the `wrong` list was computed in `calibrate()` but thrown away before persistence. An operator seeing `allowed=[]` had no way to distinguish "all wrong" (wait a day, correct) from "all unanswered" (retry in 600s). This is an observability gap with operational consequences.

3. **Calibration duration and `asked_at` semantics (GLM P2/P3 → C1-3/C1-4):** I did not flag that the old code stored no `seconds` or `asked_at`. Minor, but the `asked_at` being per-calibration-start vs per-backend matters for auditability, and the design doc was wrong about it.

4. **Test arithmetic depending on unseen fixture constant (GLM P1 → C1-5):** I asserted the rounds test was correct without noting it hard-coded `3` transport retries. GLM correctly demanded it derive `per_run` from `router.cfg`. Fixed in Cycle 1.

Qwen caught nothing I missed — its review was correct but shallow (95/100 across the board, no P0/P1).

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **Core F1 fix correct** (all three) | **Agree** | `fresh=True → use_cache=False` bypasses `providers.py:851` cache branch. Verified independently. Live reply still writes cache at `providers.py:992-1001` — correct. |
| **Rounds loop aggregation correct** (all three) | **Agree** | `answers[(bid,i)]` overwritten only for `todo` entries; final pass iterates canonical `jobs`. No double-count, no phantom backend. `max(1, int(rounds))` guard correct. |
| **Schedule doubling bounded** (all three) | **Agree** | 600→1200→...→86400→600 cycle verified. `check_calibrated` set after return prevents tight loop on success. |
| **Fail-closed** (all three) | **Agree** | `of==len(probes) and right==of` gate; `unmeasured` never counts as right; `checkers()` returns `[]` on missing miner → `unmeasured: no checker`. |
| **Crash-path fix C1-1** (GLM) | **Agree — was P0** | My Cycle 1 missed this. Fix is correct: `except Exception`, `check_allowed=[]`, `check_calibrated=clock()`, `check_recal_s` via same doubling logic, `check_calibration_crash` event. |
| **Wrong persistence C1-2** (GLM) | **Agree — was P1** | Correct fix. `wrong` now stored with `flag/gold/answer/text[:80]` and logged. |
| **Duration/asked_at C1-3/C1-4** (GLM) | **Agree — P2/P3** | Correct. `seconds` and `asked_at` (calibration start, shared across backends) now stored. Design doc updated. |
| **Test fixture constant C1-5** (GLM) | **Agree** | Fixed: `per_run = 1 + r.cfg["throttle"]["transport_retries"]`. |
| **My P0: `offset_before` bisection** | **Partially agree with myself** | Still a real performance cliff, but not a correctness bug. Conservative fallback (`hi=mid`) is safe. Downgrade to P2. |
| **My P1: `cfg.get("enabled")` vs `enabled()`** | **Agree with myself** | Still valid. Low impact (mine's local is `enabled:false` anyway) but technically wrong. Stale local cache could be returned when GPU lease not held. |
| **My P1: `wlock` contention** | **Agree with myself** | Correctly closed, bounded contention. Not a bug. Informational. |
| **Qwen: "production-ready 95/100"** | **Disagree — too generous for Cycle 0** | Cycle 0 had the crash-path tight loop. That was not 95/100. Cycle 1 (post-fix) is. |

## 3. NEW FINDINGS FROM THIS REVIEW (Cycle 2)

### P1 — `service.py:501` `could` computation on crash path is subtly wrong in one edge case

```python
could = cal is None or [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]
```

When `cal is None` (crash), `could` is `True` (truthy) → `elif` branch → `CHECK_RETRY_S` with doubling. Correct.

When `cal == {}` (empty dict — `router.effective(ROLE)` returned no backends), `cal is not None` so second branch: `[b for b,c in {}.items() ...]` → `[]` → falsy → `if allowed or not could` → `not []` → `True` → `CHECK_RECALIBRATE_S` (daily). This means: if no backend is effective (all frozen/disabled/budget-exhausted), we wait a full day before retrying. But `effective()` can change within minutes (spend meter trips, budget resets at UTC midnight, override removed). **This is the same minor issue GLM noted in 1.2 edge case** — now it applies to the new `could` logic too. Impact: low — this state is rare and the 30s `check_once` loop still runs, it just won't recalibrate. But if Heimdall recovers 5 minutes after a transient freeze, we wait 24h to notice.

**Fix:** When `cal == {}` (no effective backends), treat as `could=True` (retry soon). One-line fix: `could = cal is None or not cal or [...]`.

### P2 — `flagcheck.py:295` `max(1, int(rounds))` can raise on non-numeric input

If `rounds` is `None` (caller bug), `int(None)` raises `TypeError` — uncaught, propagates as crash, handled by C1-1's crash path. So fail-closed, but the error message is confusing. Should be `int(rounds or 1)` or explicit validation. Very low impact — only `watcher_checkers` calls it with `CALIBRATION_ROUNDS=3`.

### P2 — `service.py:514-516` `asked_at` is `config.iso()` (wall clock) but `seconds` is `clock()` (monotonic or mocked)

In tests, `clock` is a fake monotonic; `config.iso()` is real wall time. `asked_at` and `seconds` can disagree in test fixtures. Not a production bug — in production both advance together — but worth noting for test determinism. No fix needed.

### P2 — `providers.py:851` cache bypass still uses `cfg.get("enabled")` check (my Cycle 1 P1, still unfixed)

Carried forward. For `fresh=True` path it's irrelevant (cache bypassed entirely). For normal mining, a disabled local backend's stale cache could be returned when GPU lease not held. Should be `self.backends[bid].enabled()`.

### P3 — `service.py:488-496` calibration holds `check_once`'s thread for 16×2×~5-74s

`_calibrate_checkers` is synchronous inside `check_once`, which runs on the `check` loop thread. With 2 backends × 16 probes × p90 74s (per `providers.json` note on `heimdall_muse`), worst case is ~20 minutes blocking the check loop. During this time, no `check_row` work is started (though in-flight `check_row` threads continue). This is by design ("the loop waits for it") and acceptable — calibration is daily — but operators should know the `check` loop appears hung during calibration. No fix needed, but worth documenting.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Backend logic | 92 | 96 | Crash path fixed (C1-1), wrong persistence fixed (C1-2). Remaining P1 (empty-calibration daily wait) is minor. |
| Error handling | 88 | 95 | Crash path was the gap; now caught with event + doubling wait + fail-closed. |
| Security | 95 | 95 | No change. No secrets in code, prompt injection mitigated via `<quote>` + `‹` escaping. |
| Performance | 90 | 90 | No change. Live calibration adds ~$0.003/day, acceptable per A33. |
| Law compliance | 98 | 100 | L-m violation (stale calibration) fixed; L-j fail-closed preserved including crash path. |
| World-class gap | 88 | 92 | Observability improved (wrong/duration/asked_at). Empty-calibration edge case is the remaining gap. |
| **OVERALL** | **92** | **96** | Cycle 1 fixes resolved all P0/P1. Remaining items are P1/P2 polish. |

## 5. FINAL PRIORITY LIST

| Priority | File:Line | Issue | Fix |
|----------|-----------|-------|-----|
| **P1 HIGH** | `service.py:501` | Empty calibration (`cal=={}`) waits daily instead of retrying soon; transient freeze/budget recovery takes 24h to notice | Change `could = cal is None or ...` to `could = cal is None or not cal or ...` |
| **P2 MEDIUM** | `providers.py:851` | Cache check uses `cfg.get("enabled",True)` not `backend.enabled()` — stale local cache returned when GPU lease not held | Change to `self.backends[bid].enabled()` |
| **P2 MEDIUM** | `ledger.py:139-144` | `offset_before` bisection degrades to linear scan on long runs of unreadable/missing-`mined.at` lines | Add early-exit or skip counter; low priority (conservative fallback is safe) |
| **P2 MEDIUM** | `flagcheck.py:295` | `int(rounds)` raises `TypeError` on `None` | Validate or use `int(rounds or 1)` |
| **P3 LOW** | `service.py:488` | Calibration blocks check loop thread for minutes (up to ~20min worst case) | Document; or move to background thread with `check_inflight` guard |

No P0 remains. The P1 is a narrow edge case (no effective backends) with a one-line fix.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Fix the empty-calibration daily-wait at `service.py:501` (`not cal` check) — it's the last path where a transient outage can silently bar the checkers for 24 hours.

## 7. PRODUCTION READY?

**Yes, with one condition.**

**Condition:** Apply the P1 fix at `service.py:501` before shipping — add `not cal` to the `could` computation so an empty calibration (no effective backends) retries in 600s with doubling, not 86400s. This is a one-line, zero-risk change with an existing test pattern to verify it.

Without that fix: **Yes, with known limitation** — document that if all flagcheck backends become simultaneously non-effective (frozen/budget/circuit), recovery takes up to 24h. In practice this requires both Heimdall backends to be down simultaneously, which the shared down-signal already handles via the paid route.

All four new tests are correct and would fail on the old code (verified: `test_f1_the_watchers_calibration_asks_the_model_live_never_a_stored_reply` asserts 32 calls vs old 16; `test_f1_a_quote_not_answered_is_asked_again_up_to_the_rounds` derives `per_run` from config; crash test asserts `check_calibration_crash` event; wrong-answer test asserts `wrong` persistence). No must-fail case is missing.
