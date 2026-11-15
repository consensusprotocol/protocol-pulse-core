# qwen3.8-27b (qwen/qwen3.8-27b) 32 s finish=stop usage in 14698 / out 1952 usd_reported=0.002075 usd~0.073 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2243
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic of the `_reserve` loop and the `meter` signature issue, but I **missed the critical architectural flaw regarding caller time budgets** (the P1 raised by GLM and Qwen). I focused on whether the *loop* was correct, but failed to trace the *call stack* to see that `_reserve` executes *before* the `Router.call` deadline machinery (`_within`) is initialized.

I also underestimated the severity of the `meter` wrapper's `TypeError` propagation. While I noted the signature mismatch, I did not fully trace the consequence: a `TypeError` inside `on_abandon` prevents the `box["abandoned"]` flag from being set, which in turn prevents the failover logic from triggering, leading to lost bookings and held moments. The other models correctly identified this as a "silent data loss" vector.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (F2 - Starvation/Time Budget):** **AGREE.** This was the most significant finding. The default `reserve_wait_s=0.0` fix in Cycle 2 directly addresses this. I agree that a 600s block before the deadline starts is a P1 defect for any caller with a strict timeout.
*   **QWEN3.8-27B (Item 3 - Thread Pool Exhaustion):** **AGREE.** Qwen correctly identified that if a caller times out while `_reserve` is waiting, the thread remains blocked, potentially exhausting the pool. The opt-in fix mitigates this for non-batch callers.
*   **GLM-5.3-FLASH (F1 - Loop Logic):** **PARTIALLY AGREE.** GLM initially flagged the `waited` flag logic but then downgraded it after tracing. I agree the final logic is correct: the fit-check happens inside the lock, and the deadline check happens before the sleep. The "spend alone" early exit is correct.
*   **QWEN3.8-27B (Item 4 - "Best" Calculation):** **AGREE.** The fix to pass `**kw` and use `unreported` for the `best` calculation is correct and aligns with the cap's basis.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] F1 — `test_ledger_router.py` relies on `mock.patch` for module-level constants
In `tests/package/test_ledger_router.py` (lines 224-231), the test uses `mock.patch.object` to replace `PL.SPEND`, `PL.REPLIES`, etc. This is fragile. If `proof_ledger.py` imports these values at module load time and stores them in local variables (rather than accessing `PL.SPEND` dynamically), the patch will not take effect. The code shows `build_router` passing `reserve_wait_s=PL.RESERVE_WAIT_S`. If `PL.RESERVE_WAIT_S` is read at import time, the test's patch of `PL.LY_LIMIT_USD` (line 226) might not affect the router's limit if the router was constructed with a hardcoded value. However, looking at `build_router`, it passes `limit_usd` from the config or defaults. The test patches `PL.LY_LIMIT_USD` but `build_router` does not explicitly use `PL.LY_LIMIT_USD` in the diff shown; it likely uses it internally. This is a potential source of flakiness if the patching doesn't intercept the right variable. **Severity: P2** (Test fragility).

### [P3] F2 — `RESERVE_POLL_S` is hardcoded in `Router.__init__`
In `pipeline/providers.py` (line 28), `self.reserve_poll_s = RESERVE_POLL_S`. This is a class-level constant. If a user wants to adjust the poll rate for a specific router instance without subclassing, they cannot. The test `test_ledger_router.py` (line 234) works around this by directly setting `r.reserve_poll_s = 0.02`. This is acceptable for tests but suggests the API could be more flexible. **Severity: P3** (Design nit).

### [P2] F3 — `meter` wrapper does not handle `unreported` if `backend` is `None`
In `proof_ly.py` (line 129-135), the `best` calculation is:
```python
tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)
```
If `backend` is `None`, the `if backend is not None:` block is skipped, so `tot["best"]` is not updated. This is correct for free backends. However, if a paid backend is abandoned, `backend` is not `None`, so it proceeds. The logic holds. No defect here.

### [P1] F4 — Potential race in `_reserve` wait loop with `time.sleep`
In `pipeline/providers.py` (line 78), `time.sleep(max(0.01, float(self.reserve_poll_s)))` is called *outside* the lock. This is correct to avoid holding the lock during sleep. However, if the process is killed or the thread is interrupted during sleep, the reservation might not be released. But `_ledger()` drops reservations of dead processes, so this is mitigated. **No defect.**

### [P2] F5 — `test_reserve_wait.py` `until` helper timeout
In `tests/providers/test_reserve_wait.py` (line 336-341), the `until` helper raises `AssertionError` if the condition is not met within `timeout` (default 5.0s). In `test_six_workers...` (line 353), `until(lambda: track["now"] == 4)` is called. If the system is slow, this might timeout. However, the test uses `reserve_poll_s = 0.02` (line 324), so the wait is short. The 5.0s timeout is generous. **No defect.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `providers.py` `_reserve` | 7/10 | 9/10 | Opt-in fix addresses the P1 time budget issue. Logic is sound. |
| `proof_ly.py` `meter` | 6/10 | 9/10 | Signature fix and `best` calculation are correct. |
| `test_ledger_router.py` | N/A | 7/10 | New test. Fragile mocking (P2), but covers the critical path. |
| `test_reserve_wait.py` | 8/10 | 9/10 | Polling-based assertions are robust. |

## 5. FINAL PRIORITY LIST

1.  **[P2] `tests/package/test_ledger_router.py` (lines 224-231):** Verify that `mock.patch.object` correctly intercepts the variables used by `build_router`. If `build_router` reads `PL.LY_LIMIT_USD` at call time, the patch works. If it reads it at import time, the patch fails. **Action:** Add a print or assertion in the test to confirm the limit is actually 1.5 * U.
2.  **[P3] `pipeline/providers.py` (line 28):** Consider allowing `reserve_poll_s` to be passed to `Router.__init__` for flexibility.
3.  **[P3] `docs/audits/.../C2_STEP.diff`:** The docstring for `_reserve` is very long. Consider moving the batch 3 narrative to a separate comment or doc.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The opt-in nature of `reserve_wait_s` (default 0.0) is the single most important change, as it preserves backward compatibility for all existing callers while enabling the batch build to wait for in-flight calls.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Confirm that `mock.patch` in `test_ledger_router.py` correctly affects the router's limit. If not, fix the test to patch the correct variable or pass the limit explicitly.
2.  Ensure that no other caller in the codebase inadvertently sets `reserve_wait_s > 0` without a corresponding time budget adjustment. (Grep for `reserve_wait_s` to confirm only `build_router` uses it).

P1_OR_WORSE: 0