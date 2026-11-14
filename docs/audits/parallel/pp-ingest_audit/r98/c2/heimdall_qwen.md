# heimdall_qwen (qwen/qwen3.8-27b, 310.7 s, $0.009, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest (Ruling 98)
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified a "Race Condition in `RoleCaps`" as a Critical flaw, but I failed to recognize that the codebase's design (specifically the `reserve`/`release` pattern under a single lock) actually prevents the specific race I described. I also missed the **timezone parsing vulnerability** in `downsignal.py` which GLM correctly identified as a P0.

**What I missed:**
1.  **The Timezone Trap (GLM P0):** I assumed `failing_since_utc` was always aware. GLM correctly noted that if the builder's module writes a naive ISO string, `datetime.fromisoformat(...).timestamp()` interprets it as *local* time (ET), causing the route to open 5 hours late. The code in `downsignal.py:213-217` (Cycle 1 version) did not enforce the `config.aware()` fail-closed convention.
2.  **The "Worst Case" Reservation Logic (Consensus C1-1):** I noted that `reserve` uses a flat amount and `add` doesn't check the cap, leading to potential overshoot. I called this "acceptable for a soft cap." However, the consensus (and the code's intent via `_worst_cost`) is that the reservation *must* be the priced worst case to ensure the cap is a hard ceiling for *starting* calls. My Cycle 1 analysis underestimated the severity of the flat `$0.25` reservation against a potential `$0.83` call cost.
3.  **State Desync on Restart (GLM/Muse):** I noted `RoleCaps` relies on the loader, but I didn't explicitly flag that if the service restarts *during* an open paid route, the `paid_route` KV state is persisted, but the in-memory `RoleCaps` is reset. The loader (`queue.role_spend_since`) fetches historical spend, which is correct, but I didn't verify that the `reserve` logic correctly handles the transition from "historical spend" to "new reservations" without double-counting or under-counting during the rollover.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **RoleCaps Race** | Qwen (C1) | **Refuted** | `reserve` and `release` are atomic under `self.lock`. The "race" I described in C1 (Thread A reserves, Thread B reserves, Thread A adds) is safe because `add` only increases `spent`, and `reserve` checks `spent + reserved`. The only risk is overshoot if `actual_cost > reserved_amount`, which is addressed by the `_worst_cost` fix. |
| **Timezone Parsing** | GLM (C1) | **Agree (P0)** | `downsignal.py` must use `config.aware()` or explicitly check `tzinfo`. A naive timestamp is a "no clock" and must fail closed (route does not open). |
| **Flat Reservation** | Consensus (C1-1) | **Agree (P0)** | The flat `$0.25` is insufficient. The reservation must be `max(cap_reserve_usd, _worst_cost(...))`. This ensures no call *starts* if its worst-case cost would exceed the cap. |
| **`paid_open` Desync** | Qwen (C1) | **Refuted** | `paid_open` is a simple bool. The mine thread reads it once per `mine_once` call. If it flips mid-batch, the current batch completes on the old route. This is acceptable and documented. The re-check logic handles the transition. |
| **`conv` Cache Leak** | Qwen (C1) | **Agree (P2)** | The `clear()` at 5000 is blunt but functional. An LRU would be better, but this is not a production blocker. |
| **Recheck Logic** | Muse (C1) | **Agree (P1)** | Muse correctly identified that `recheck_ts` must be cleared when a video is mined on the paid route *again* (e.g., second outage). The code in `service.py:318-320` (Cycle 1) did *not* do this. It only set `mine_route`. If a video was mined on paid, then signal back, then signal down again, and mined on paid again, `recheck_ts` would still be set from the first re-check, preventing the second re-check. **Wait**, looking at the code: `_settle` sets `recheck_ts=None` *only* if `route == paid_role`. So if it's mined on paid, `recheck_ts` is cleared. This is correct. Muse's concern was valid for the *initial* implementation if it didn't clear it, but the code *does* clear it. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1: `RoleCaps._roll` Loader Consistency (P1)**
In `providers.py:697-701`, `_roll` resets `spent` to `loader(role, start)`. The loader is `queue.role_spend_since`, which sums `calls` where `ts >= start`.
*   **Issue:** If the service restarts, `RoleCaps` is empty. `_roll` is called on the first `reserve` or `add`. It fetches historical spend. This is correct.
*   **Subtle Bug:** What if the ET day rolls over *while* a call is in flight?
    1.  Call A starts at 23:59 ET. `reserve` uses Day 1 cap.
    2.  Call A finishes at 00:01 ET. `add` is called. `_roll` detects Day 2. It resets `spent` to `loader(role, Day 2 start)`.
    3.  `loader` returns 0 (no calls on Day 2 yet).
    4.  `spent` becomes `0 + cost(A)`.
    5.  This is correct. The cost is attributed to the day it *ended*.
    6.  **However**, the `reserve` for Call A was against Day 1's cap. If Day 1's cap was nearly full, Call A was allowed. If Day 2's cap is also nearly full (due to other calls), Call A's cost is added to Day 2. This is acceptable.
    7.  **Real Issue:** The `reserve` check `spent + reserved + amount > cap` uses the *current* day's `spent`. If a call spans midnight, its reservation was against the *previous* day's cap, but its cost is added to the *current* day's cap. This could allow a slight overshoot of the *current* day's cap if many calls span midnight. Given the low volume and the "worst case" reservation, this is negligible.

**N2: `signal_back()` Race (P2)**
In `downsignal.py:465-469`, `signal_back()` checks `v.get("mode") == self.up and not self.paid_open`.
*   `self.paid_open` is set in `_route_tick`.
*   `signal_back()` is called in `_queue_rechecks` (service.py:584).
*   If the signal thread is in the middle of `_route_tick` and has just set `paid_open = False` but hasn't yet updated `self.view` (or vice versa), `signal_back()` might see a stale `view` or `paid_open`.
*   **Impact:** Low. `_queue_rechecks` is idempotent. If it runs slightly early or late, it just queues re-checks. The `recheck_ts` prevents double-queueing.

**N3: `SWITCH_PATTERN` Regex (P2)**
In `spend.py:23-24`, the regex for `SWITCH_PATTERN` includes `MINER (?:ON|OFF) THE PAID ROUTE`.
*   The head written in `downsignal.py:231` is `MINER ON THE PAID ROUTE (...)`.
*   The head written in `downsignal.py:237` is `MINER OFF THE PAID ROUTE (...)`.
*   The regex matches these.
*   **Issue:** The regex is anchored with `^`. The head is prepended to the STATE file. This is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 6/10 | 8/10 | The "Critical" race condition was refuted. The timezone and reservation issues are real but fixable. The core logic is sound. |
| **Law Compliance** | 9/10 | 9/10 | L-x, L-l, L-m are strictly enforced. The paid route lift is correctly scoped. |
| **Concurrency** | 5/10 | 7/10 | `RoleCaps` is safe. `paid_open` is safe. The main risk is the timezone parsing, which is a data integrity issue, not a concurrency one. |
| **Maintainability** | 8/10 | 8/10 | Code is well-documented and modular. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
1.  **Timezone Parsing in `downsignal.py`:** Use `config.aware()` to parse `failing_since_utc`. If it returns `None` (naive or invalid), the route must **not** open. (GLM C1-2)
2.  **Reservation Amount in `providers.py`:** The `reserve` call in `Router.run` must use `max(cap_reserve_usd, _worst_cost(...))` instead of just `cap_reserve_usd`. This ensures the cap is a hard ceiling for *starting* calls. (Consensus C1-1)

**P1 HIGH**
3.  **Recheck Logic in `service.py`:** Verify that `recheck_ts` is cleared when a video is mined on the paid route. (Code does this in `_settle`, but it's a critical path for A31).
4.  **`RoleCaps` Loader:** Ensure `queue.role_spend_since` is efficient and correct. It sums `calls` where `ts >= start`. This is O(N) if not indexed. `calls_ts` index exists, so it's fine.

**P2 MEDIUM**
5.  **`conv` Cache:** Replace `clear()` with an LRU cache or timestamp-based eviction to avoid I/O spikes.
6.  **`signal_back()` Race:** Add a comment or lock if the race becomes an issue. Currently low impact.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the timezone parsing in `downsignal.py` to fail closed on naive timestamps, and ensure the `RoleCaps` reservation uses the priced worst-case cost.** These two changes prevent the route from opening at the wrong time and prevent budget overruns, respectively.

## 7. PRODUCTION READY?

**No.**

**Conditions:**
1.  Apply P0 fixes (timezone parsing, worst-case reservation).
2.  Run the test suite (`tests/ingest/test_paid_route.py`) to verify the fixes.
3.  Monitor the first few days of production for any unexpected route openings or budget overruns.