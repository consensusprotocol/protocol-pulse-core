# heimdall_qwen (qwen/qwen3.8-27b, 384.7 s, $0.023, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I gave this code a 95/100 and called it "production-ready" with only minor P2/P3 suggestions. I was **significantly too lenient**. Here is what the other models caught that I missed or under-weighted:

**Heimdall_GLM (the most thorough reviewer):**
- **C1-1 (P0, verified):** A calibration that *raises* (any exception out of `watcher_checkers`) left `check_calibrated` unchanged, so the check loop would re-run it every 30 seconds. With the old cached path this was free; with the new live path, it would hammer the gateway with 16 live calls every 30 seconds. This is a **real production incident waiting to happen**. I completely missed this.
- **C1-2 (P1, verified):** Wrong answers were discarded after calibration. The stored calibration now carries per-backend `wrong` details. I noted the aggregation was correct but didn't flag the observability gap.
- **C1-3/C1-4 (P2/P3):** Duration and `asked_at` semantics. I missed these entirely.
- **The `cal is None` edge case in `could`:** GLM correctly noted that when `cal` is `None` (crash), `could` is `True`, which is correct behavior (treat crash like unanswered). I didn't trace this path.

**Heimdall_Muse:**
- **P1 — `providers.py:851` cache check uses `cfg.get("enabled",True)` not `backend.enabled()`:** This is a **real bug** I completely missed. For `OllamaLocalBackend`, `enabled()` checks `gpu0.held()`, but the cache path only checks the config's `enabled` flag. This means a disabled local backend's stale cache could be returned even when the GPU lease is not held. While the `fresh=True` path bypasses the cache entirely (so F1 is not affected), this is a latent bug in the normal mining path.
- **P0 — `ledger.py:offset_before` bisection performance cliff:** I noted "No N+1 query problems" but missed the bisection degradation on long runs of unreadable lines.
- **P2 — `service.py:584-597` `_paid_due` caches `tpm` without invalidation:** I missed this.

**What I got right in Cycle 1:**
- The core F1 fix is correct: `use_cache=not fresh` bypasses the cache.
- The rounds loop aggregation is correct.
- The schedule doubling is bounded and correct.
- Fail-closed behavior is correct.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
|---------|--------|------------|-----------|
| C1-1: Crash path re-runs every 30s | GLM P0 | **AGREE** | This is a real P0. The fix in the current code (`_calibrate_checkers` catching the exception) addresses it, but I need to verify the fix is complete. |
| C1-2: Wrong answers discarded | GLM P1 | **AGREE** | The current code now stores `wrong` details. Verified in `service.py:513-516`. |
| `providers.py:851` cache check bug | Muse P1 | **AGREE** | This is a real bug, but it is **pre-existing** (not introduced by this diff). It does not affect F1 because `fresh=True` bypasses the cache. It should be fixed separately. |
| `ledger.py` bisection performance | Muse P0 | **PARTIALLY AGREE** | It is a performance concern, not a correctness bug. The bisection is conservative (reads more, never less). At 100k+ lines it could be slow, but the ledger is append-only and the read is bounded by `from_time`. Low priority. |
| `_paid_due` cache invalidation | Muse P2 | **AGREE** | Minor. The cache is bounded at 5000 entries and the paid route is rare. |
| Early termination in `calibrate` | My P2 | **AGREE** | Still valid. If all backends have passed, the remaining rounds are wasted. |
| `rounds=0` edge case | My P3 | **AGREE** | `max(1, int(rounds))` handles it. A test would be good. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding 1: The crash fix is correct but the `could` logic has a subtle edge case.**

In `service.py:501`:
```python
could = cal is None or [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]
```

When `cal is None` (crash), `could` is `True`. This is correct: a crash is treated like an unanswered calibration, so the wait doubles. But consider this scenario:
- Backend A: 16/16 right (passed)
- Backend B: 15/16 right, 1 wrong (failed)
- `allowed = ["A"]`
- `could = [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]` → `[]` (B has `wrong`, so it's not in `could`)
- `if allowed or not could:` → `True` (allowed is non-empty)
- `check_recal_s = CHECK_RECALIBRATE_S` (daily)

This is correct: A passed, so we wait a day. B's wrong answer is recorded, and B will be re-calibrated daily. Good.

But consider:
- Backend A: 15/16 right, 1 unanswered (outage)
- Backend B: 15/16 right, 1 wrong
- `allowed = []`
- `could = [A]` (A has `unmeasured` and no `wrong`)
- `if allowed or not could:` → `False`
- `elif self.check_recal_s >= CHECK_RECALIBRATE_S:` → depends on previous state
- If first calibration: `check_recal_s = CHECK_RETRY_S` (600s)

This is correct: A could pass if the outage clears, so we retry in 600s. B's wrong answer is recorded, but B is not in `could` because it has `wrong`. Good.

**Finding 2: The `check_allowed` is set to `[]` on crash, which is correct, but the previous allowance is not kept.**

In `service.py:492`:
```python
allowed, cal = [], None
```

This is correct: a crash means nothing was measured, so nobody is allowed. The previous allowance is discarded. This is fail-closed. Good.

**Finding 3: The `asked_at` is the calibration's start, not per-backend.**

In `service.py:516`:
```python
asked_at=asked
```

Where `asked = config.iso()` is set at the start of `_calibrate_checkers`. This is correct: all backends are asked in the same calibration, so they share the same start time. The design document now says this explicitly (C1-4). Good.

**Finding 4: The `seconds` is the calibration's duration, not per-backend.**

In `service.py:515`:
```python
seconds=round(secs, 1)
```

Where `secs = self.clock() - t0`. This is correct: the duration of the entire calibration. Good.

**Finding 5: The `wrong` list is per-backend, which is correct.**

In `service.py:515-516`:
```python
wrong=[{"flag": w["flag"], "gold": w["gold"], "answer": w["answer"], "text": w["text"][:80]}
       for w in c["wrong"]]
```

This is correct: each backend's wrong answers are recorded separately. Good.

**Finding 6: The `check_calibration` kv is set to `{}` on crash, which is correct.**

In `service.py:510`:
```python
self.q.kv_set("check_calibration", json.dumps({}))
```

This is correct: a crash means no calibration data, so the kv is emptied. Good.

**Finding 7: The log line on crash is correct.**

In `service.py:511`:
```python
self.log(f"check: calibration crashed after {secs:.0f} s: {crash}; every flag stands; {nxt}")
```

This is correct: it logs the crash, the duration, and the next wait. Good.

**Finding 8: The `check_calibration_crash` event is recorded, which is correct.**

In `service.py:493`:
```python
self.q.event("check_calibration_crash", None, None, error=traceback.format_exc()[-2000:])
```

This is correct: the crash is recorded as an event. Good.

**Finding 9: The `check_recal_s` is set to `CHECK_RETRY_S` on crash, which is correct.**

In `service.py:504-505`:
```python
elif self.check_recal_s >= CHECK_RECALIBRATE_S:
    self.check_recal_s = CHECK_RETRY_S
```

Wait, this is not quite right. Let me re-read the code:

```python
could = cal is None or [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]
if allowed or not could:
    self.check_recal_s = CHECK_RECALIBRATE_S
elif self.check_recal_s >= CHECK_RECALIBRATE_S:
    self.check_recal_s = CHECK_RETRY_S
else:
    self.check_recal_s = min(CHECK_RECALIBRATE_S, 2 * self.check_recal_s)
```

On crash:
- `cal is None` → `could = True`
- `allowed = []` → `if allowed or not could:` → `False`
- `elif self.check_recal_s >= CHECK_RECALIBRATE_S:` → depends on previous state
  - If first calibration: `check_recal_s = CHECK_RECALIBRATE_S` (initialized at `service.py:126`)
  - So `check_recal_s >= CHECK_RECALIBRATE_S` → `True`
  - `check_recal_s = CHECK_RETRY_S` (600s)

This is correct: a crash is treated like an unanswered calibration, so the wait is 600s. Good.

**Finding 10: The `check_recal_s` doubling is correct.**

On consecutive crashes:
- First crash: `check_recal_s = 600`
- Second crash: `check_recal_s = 600 < 86400` → `check_recal_s = min(86400, 2*600) = 1200`
- Third crash: `check_recal_s = 1200 < 86400` → `check_recal_s = min(86400, 2*1200) = 2400`
- ...
- After 8 crashes: `check_recal_s = 76800`
- Ninth crash: `check_recal_s = 76800 < 86400` → `check_recal_s = min(86400, 2*76800) = 86400`
- Tenth crash: `check_recal_s = 86400 >= 86400` → `check_recal_s = 600`

This is correct: the wait doubles until it hits the cap, then resets to 600s. Good.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Backend logic | 95/100 | 92/100 | The crash path was a P0 that I missed. The fix is correct, but the initial code was not production-ready. |
| Frontend/UI | N/A | N/A | No change. |
| Error handling | 95/100 | 90/100 | The crash path was not handled in the initial code. The fix is correct, but the initial code was not production-ready. |
| Security | 95/100 | 95/100 | No change. |
| Performance | 90/100 | 88/100 | The `providers.py:851` cache check bug is a latent performance/correctness issue. The `ledger.py` bisection is a performance concern. |
| Law compliance | 100/100 | 100/100 | No change. |
| World-class gap | 90/100 | 88/100 | The crash path and the cache check bug are gaps. |
| **OVERALL** | **95/100** | **91/100** | The crash path was a P0 that I missed. The fix is correct, but the initial code was not production-ready. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:**
1. **Verify the crash fix is complete.** The current code catches the exception in `_calibrate_checkers` and sets `check_allowed = []`, `check_recal_s = CHECK_RETRY_S`, and records the event. This is correct. **No action needed.**

**P1 HIGH:**
1. **Fix `providers.py:851` cache check bug.** The cache path uses `cfg.get("enabled",True)` instead of `backend.enabled()`. For `OllamaLocalBackend`, this means a disabled local backend's stale cache could be returned even when the GPU lease is not held. **Action:** Change `providers.py:851` to use `self.backends[bid].enabled()` instead of `self.backends[bid].cfg.get("enabled", True)`.

**P2 MEDIUM:**
1. **Add early termination to `calibrate` if all backends have passed.** If all backends have passed, the remaining rounds are wasted. **Action:** Add a check in the rounds loop to break early if all backends have passed.
2. **Add a test for `calibrate` with `rounds=0`.** **Action:** Add a test in `tests/ingest/test_flagcheck.py`.
3. **Fix `_paid_due` cache invalidation.** The `tpm` cache is not invalidated when the transcript is updated. **Action:** Add a check in `_paid_due` to invalidate the cache when the transcript is updated.

**P3 LOW:**
1. **Optimize `ledger.py:offset_before` bisection.** The bisection degrades to linear scan on long runs of unreadable lines. **Action:** Add a fast path for the common case where the file is in order.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `providers.py:851` cache check bug.** This is a latent bug that could cause a disabled local backend's stale cache to be returned even when the GPU lease is not held. While it does not affect F1 (because `fresh=True` bypasses the cache), it is a real bug in the normal mining path. Fixing it will prevent a class of subtle bugs where a disabled backend's stale cache is used.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Fix the `providers.py:851` cache check bug** (P1). This is a latent bug that could cause a disabled local backend's stale cache to be returned even when the GPU lease is not held.
2. **Add early termination to `calibrate`** (P2). This is a minor performance improvement, but it is a good practice.
3. **Add a test for `calibrate` with `rounds=0`** (P2). This is a good practice.

**The crash fix is correct and complete.** The current code catches the exception in `_calibrate_checkers` and sets `check_allowed = []`, `check_recal_s = CHECK_RETRY_S`, and records the event. This is correct.

**The core F1 fix is correct.** The `use_cache=not fresh` bypasses the cache, and the rounds loop aggregation is correct.

**The schedule doubling is bounded and correct.** The wait doubles until it hits the cap, then resets to 600s.

**Fail-closed behavior is correct.** A crash means nothing was measured, so nobody is allowed. The previous allowance is discarded.

**The code is production-ready after fixing the P1 bug.**