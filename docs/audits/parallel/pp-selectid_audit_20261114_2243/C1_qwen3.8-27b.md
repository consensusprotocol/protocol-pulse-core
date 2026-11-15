# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 11938 / out 2836 usd_reported=0.002577 usd~0.078 (upper-bound price)

I will analyze the provided code changes against the governing laws and the specific questions raised in the audit request.

### Analysis of `pipeline/providers.py` (Defect 2 Fix)

**1. Deadlock and Starvation Analysis**
The new `_reserve` logic introduces a wait loop.
*   **Locking:** The code acquires `self._lock()` (an `fcntl` flock on a file) to read the ledger and check limits. If the limit is not met, it releases the lock (exits the `with` block) and then calls `time.sleep()`.
*   **Deadlock:** Since the lock is released during the sleep, other threads can acquire the lock, read the ledger, and potentially reserve or settle. There is no circular dependency where a waiting thread holds a resource needed by a running thread. The running threads hold the lock only briefly to update the ledger.
*   **Starvation:** The wait is bounded by `reserve_wait_s` (600s). If a call cannot fit within this time, it raises `SpendLimit`. This prevents indefinite starvation. However, if the system is under heavy load where calls take longer than 600s to settle, new calls will fail. This is a "fail closed" behavior consistent with LAW 20/M12.
*   **Conclusion:** No deadlock. Starvation is bounded and results in a hard stop (SpendLimit), which is acceptable for a spend guard.

**2. Limit Integrity (Spent + Reserved > Limit)**
*   **Check:** The condition `if spent + held + upper <= self.limit_usd` is evaluated *inside* the lock.
*   **Race Condition:** Two threads could theoretically pass the check simultaneously if the lock wasn't held. However, `self._lock()` is a file lock (`fcntl.flock`). On Linux, `flock` is exclusive. Only one process/thread can hold the lock at a time.
*   **Atomicity:** The read of `spent` and `held`, the check, and the write of the new reservation (`d["reserved"][key] = ...`) and save (`self._save(d)`) all happen within the `with self._lock():` block.
*   **Conclusion:** The limit is never passed. The reservation is only saved if the check passes while holding the exclusive lock.

**3. Caller Time Budgets**
*   **Context:** The prompt notes that `_reserve` is called before the call's deadline (`_within`) starts.
*   **Impact:** If a caller has a strict time budget (e.g., 5 seconds) for the entire operation, and `_reserve` waits for 600 seconds, the caller will time out.
*   **Code Review:** The `Router.call` method likely wraps the backend call in a deadline context. If `_reserve` blocks for 600s, the thread is occupied. If the caller uses `concurrent.futures` with a timeout, the future will time out, but the thread running `_reserve` will continue to wait until `reserve_wait_s` expires or the limit is met. This could lead to thread pool exhaustion if many callers time out while the underlying threads are still waiting in `_reserve`.
*   **Severity:** This is a potential resource leak/thread exhaustion issue under high contention. However, the default `reserve_wait_s` is 600s. If the pipeline steps (like Step A) have timeouts shorter than 600s, this is a P1 defect. The prompt mentions "prescreen, ruling 101's wait estimate". If those estimates are < 600s, this is a problem.
*   **Mitigation:** The code does not check the caller's remaining time budget before waiting. It waits blindly up to `reserve_wait_s`.
*   **Finding:** [P1] The `_reserve` method does not respect the caller's remaining time budget. If a caller has a 10s timeout and `_reserve` waits 600s, the caller will time out, but the thread remains blocked in `_reserve` until the wait expires or the limit is met. This can exhaust the thread pool.

**4. "Best" Calculation for Abandoned Calls**
*   **Code:** `tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)`
*   **Logic:**
    *   If `rep` (reported USD) is a number, use it.
    *   Else, if `booked` (unreported keyword) is not None, use `booked`.
    *   Else, use `usd` (estimate).
*   **Context:** For an abandoned call, `Router._settle` is called with `unreported=booked` (the list price estimate). `usage` is `{"in": 0, "out": 0}`, so `rep` is likely `None` or 0.
    *   If `rep` is `None`, `P._num(None)` is False.
    *   `booked` is the list price.
    *   So `tot["best"]` adds the list price.
*   **Correctness:** The prompt states: "An abandoned call counts in 'best' at that booking, as the cap counts it". The cap (`_basis_total`) uses `usd_unreported_estimate` for abandoned calls. The meter now aligns with this.
*   **Conclusion:** Correct.

**5. Other Wrappers**
*   **Search:** The diff only modifies `proof_ly.py`'s `meter` function. Are there other wrappers?
*   **Code:** `router._settle = _settle`. This is the only wrapper shown.
*   **Conclusion:** No other wrappers are modified or shown to be broken.

### Analysis of `tests/package/test_meter.py`

*   **Test 1:** `test_a_missed_deadline_through_the_meter_fails_over_and_is_booked`
    *   Verifies failover works (no TypeError).
    *   Verifies ledger booking (`usd_unreported_estimate`).
    *   Verifies meter `est` and `best`.
    *   Looks correct.
*   **Test 2:** `test_the_meter_counts_an_abandoned_call_at_the_booking_the_cap_counts`
    *   Verifies `best` uses the reported rate for the abandoned call.
    *   Looks correct.

### Analysis of `tests/providers/test_reserve_wait.py`

*   **Test 1:** `test_six_workers_with_room_for_four_all_answer_and_never_more_than_four_run`
    *   Simulates 6 workers, limit for 4.
    *   Verifies 4 run, 2 wait.
    *   Verifies all 6 eventually answer.
    *   Verifies max concurrent is 4.
    *   Looks correct.
*   **Test 2:** `test_a_call_kept_out_by_spend_alone_is_refused_at_once_even_with_a_call_in_flight`
    *   Verifies immediate refusal if `spent + upper > limit`.
    *   Looks correct.
*   **Test 3:** `test_a_call_still_kept_out_when_its_wait_ends_is_refused_and_the_limit_is_never_passed`
    *   Verifies refusal after wait timeout.
    *   Looks correct.

### Governing Laws Compliance

*   **LAW 20 / M2:** "A failed gate is a hard stop; never change what a check accepts to make a render pass".
    *   The `_reserve` change makes the spend guard *wait* instead of *refuse* immediately if the limit is met by in-flight calls. This changes the behavior of the guard.
    *   Is this a "gate"? The spend guard is a resource limit, not a quality gate.
    *   However, M12 says "missing data... rejects; it never produces a pass".
    *   The new logic *allows* a call to proceed if it fits within the limit after waiting. This is not a "pass" of a quality check, but a resource allocation decision.
    *   The key constraint is "never pass the limit". The code ensures this.
    *   The change is an optimization to reduce false refusals (starvation of valid calls due to temporary reservation spikes). It does not weaken the limit.
    *   **Verdict:** Compliant.

*   **M12 FAIL CLOSED:**
    *   If the wait expires, it raises `SpendLimit`. This is fail closed.
    *   If the limit is exceeded, it raises `SpendLimit`. Fail closed.
    *   **Verdict:** Compliant.

*   **L-j RELEASE IS AUTHORISED ON THESE BYTES:**
    *   This law applies to release gates. The spend guard is not a release gate.
    *   **Verdict:** N/A.

### Specific Findings

1.  **[P1] Thread Pool Exhaustion Risk in `_reserve`:**
    The `_reserve` method can block a thread for up to `reserve_wait_s` (600 seconds). If the calling code (e.g., `package.py` Step A) uses a `ThreadPoolExecutor` with a limited number of workers and a timeout shorter than 600s, the workers will be stuck in `_reserve` even after the caller has timed out and moved on. This can lead to a situation where all workers are blocked in `_reserve`, preventing any new work from starting, effectively halting the pipeline. The code does not check for cancellation or remaining time budget.

2.  **[P2] `reserve_wait_s` Default is High:**
    The default `RESERVE_WAIT_S` is 600.0 seconds. This is a long time to block a thread. If the pipeline has strict SLAs, this might be too long. However, it is configurable.

3.  **[P3] Test Timing Fragility:**
    The tests use `time.sleep` and `threading.Event`. These can be flaky on loaded systems. For example, `time.sleep(0.4)` in `test_six_workers...` assumes that 4 threads will start and reserve within 0.4s. If the system is slow, this might fail. However, this is a common pattern in unit tests.

4.  **[P3] `meter` Wrapper `**kw` Pass-through:**
    The `meter` function in `proof_ly.py` now passes `**kw` to `settle`. This is correct for the `unreported` keyword. However, if `Router._settle` signature changes in the future to add more keywords, the meter will automatically pass them, which is good. But if `Router._settle` removes a keyword, the meter might pass an unexpected one. This is low risk.

5.  **[P1] Potential Logic Error in `meter` "best" Calculation:**
    In `proof_ly.py`:
    ```python
    rep, booked = (usage or {}).get("usd_reported"), kw.get("unreported")
    # ...
    tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)
    ```
    If `rep` is `0.0` (a valid number), `P._num(0.0)` is True, so it adds `0.0`.
    If `rep` is `None`, it adds `booked` or `usd`.
    This seems correct.
    However, consider the case where `rep` is reported but `booked` is also provided. The code prefers `rep`. This is correct ("vendor's own figure where reported").

6.  **[P2] `_reserve` Wait Loop Efficiency:**
    The loop sleeps for `reserve_poll_s` (1.0s) between checks. This is reasonable.

7.  **[P1] Missing Check for `SpendLimit` in `_reserve` Wait Loop:**
    The wait loop checks `if spent + upper > self.limit_usd or time.time() >= t_end`.
    If `spent + upper > self.limit_usd`, it raises `SpendLimit`.
    This is correct. It fails immediately if the call *cannot* fit even if all reservations were cleared.

8.  **[P3] Documentation:**
    The docstring for `_reserve` is updated to explain the wait behavior. Good.

### Summary of Findings

*   **[P1] Thread Pool Exhaustion:** The `_reserve` method can block threads for up to 600s. If callers have shorter timeouts, this can exhaust the thread pool and halt the pipeline.
*   **[P2] High Default Wait Time:** 600s is a long time to block.
*   **[P3] Test Flakiness:** Use of `time.sleep` in tests.

The most critical issue is the P1 regarding thread pool exhaustion. The code does not coordinate with the caller's deadline.

P1_OR_WORSE: 1