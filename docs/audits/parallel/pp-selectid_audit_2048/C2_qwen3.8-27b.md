# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 20358 / out 2032 usd~0.092 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2048

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified the `on_abandon` exception ordering issue (P2) and the `one` counter logic (P2). I missed the following:

*   **Qwen's P0-1 (Race Condition):** Qwen claimed a race condition where the worker finishes just before the main thread acquires the lock, leading to missed booking. **I disagree with this finding.** The code explicitly checks `if not done.is_set()` inside the lock. If the worker finished, `done.is_set()` is True, and the code proceeds to return the value or raise the error. This is the *intended* behavior: an answer at the deadline is used, not abandoned. The booking for an *abandoned* call only happens if `done` is *not* set. Qwen's scenario describes a successful (or error) completion, not an abandonment. Therefore, no booking is missed; the normal settlement path handles it.
*   **Qwen's P0-2 (Ledger Arithmetic):** Qwen worried about `_late` arithmetic depending on `abandon`. This is correct by design. `_late` only runs if `box["abandoned"]` exists. The arithmetic in `_replace_booking` correctly subtracts the initial `booked` amount and adds the new `usd`/`rep`.
*   **Grok's P2 (Ordering):** Grok correctly identified that if `on_abandon` raises, the `missed_deadline` log might be skipped. The Cycle 2 diff **fixes this** by moving the `_log_slow` call *before* the `_settle` call in `abandon()`. This was a valid catch in Cycle 1, and the fix is present here.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (SHIP: yes):** I **agree**. Grok correctly identified the P2s and verified the core logic. The fixes for the P2s are present in this diff.
*   **Qwen (SHIP: no):** I **disagree** with the P0s.
    *   **P0-1:** Refuted. The logic `if not done.is_set()` correctly distinguishes between "worker finished" (use result) and "worker still running" (abandon). There is no race that causes a missed booking for an abandoned call because the booking is triggered by the *timeout* event, not the worker's state at the moment of lock acquisition, but rather the state *under* the lock. If the worker finished, it's not abandoned.
    *   **P0-2:** Refuted. The arithmetic is sound. `_replace_booking` is atomic under `self._lock()`.
    *   **P0-3:** Qwen's analysis of `class_84` filler detection was largely correct but flagged `one += k is not None` as "buggy/obscure." It is not a bug; it is a valid Python idiom for incrementing a counter based on a boolean condition. It is slightly obscure, but functionally correct.
    *   **P1-4:** Qwen correctly identified that `on_late` exceptions were swallowed. The Cycle 2 diff **fixes this** by introducing `_replace_booking` and catching its failure in `_late`, recording `replaced: false` and `ledger_error`.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2: `pipeline/providers.py:273` (Potential Negative Ledger Value)**
In `_replace_booking`, line 273:
```python
d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
```
If `booked` (the prompt token estimate) is greater than the current `usd_unreported_estimate` (e.g., due to floating point drift, or if the ledger was manually edited, or if a previous error left it inconsistent), this value can become negative. While the subsequent addition of `usd` (line 279) or `rep` (line 277) will likely bring it back to a positive value, a transient negative value in the ledger could confuse downstream consumers or violate invariants if any exist.
*   **Scenario:** `usd_unreported_estimate` is 0.000001. `booked` is 0.000002. Result: -0.000001. Then `usd` (0.000005) is added. Result: 0.000004. The final value is correct, but the intermediate state is negative.
*   **Risk:** Low. The final state is correct. However, if any check runs between the subtraction and addition (unlikely, as it's under lock), it might see a negative value.
*   **Fix:** Clamp to 0.0: `max(0.0, d.get(...) - booked)`.

**P2: `pipeline/attest.py:58` (Obscure Counter Logic)**
`one += k is not None` is functionally correct but stylistically poor. It relies on `True` being `1`.
*   **Fix:** `if k is not None: one += 1`.

**P2: `pipeline/providers.py:202` (Silent Swallow of `on_late` Errors)**
The `except Exception: pass` in `_within`'s `run()` function swallows *all* exceptions from `on_late`. While the Cycle 2 fix ensures that *ledger* errors are recorded in the log line via `_late`'s internal try/except, if `on_late` itself (the `Router._late` method) raises an error *outside* of the `_replace_booking` call (e.g., in `_log_slow` or during the `rec` construction), it is silently dropped.
*   **Scenario:** `_log_slow` fails due to a disk error. The exception is caught by `except Exception: pass`. The late answer is not logged. The booking stands, but there is no record of the late answer.
*   **Risk:** Medium. Loss of audit trail.
*   **Fix:** Log the exception to a stderr or a separate error log before passing.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Ledger Arithmetic** | 8/10 | 9/10 | `_replace_booking` is atomic and correct. Minor risk of transient negative values. |
| **Threading/Ordering** | 7/10 | 9/10 | The `on_abandon` ordering fix (log before settle) resolves the P2. The race condition concern (Qwen P0-1) was refuted. |
| **Class 84 Logic** | 9/10 | 9/10 | Logic is correct. Style is slightly obscure (`one += k is not None`). |
| **Error Handling** | 6/10 | 8/10 | `on_late` errors are now recorded in the log line. Silent swallow of non-ledger errors remains. |
| **Tests** | 8/10 | 9/10 | New tests cover the ordering, the ledger breakage, and the class 84 cases. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/providers.py:273`**: Clamp `usd_unreported_estimate` to 0.0 to prevent transient negative values.
2.  **`pipeline/providers.py:202`**: Log exceptions from `on_late` that are not ledger-related (e.g., `_log_slow` failures) to avoid silent loss of audit trail.
3.  **`pipeline/attest.py:58`**: Refactor `one += k is not None` to `if k is not None: one += 1` for clarity.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `_replace_booking` as an atomic, all-or-nothing ledger write under the lock, combined with the explicit recording of `replaced: false` and `ledger_error` in the deadline log, is the highest-leverage change. It ensures that the ledger remains consistent even when the late answer processing fails, and it provides a clear audit trail for debugging spend discrepancies.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Apply the P2 fixes (clamp negative ledger values, log non-ledger `on_late` errors, refactor obscure counter logic).
2.  Verify that the `DECODER` constant in `pipeline/lock_precheck.py` matches the integrator's live value (not in diff, but critical for file naming).
3.  Confirm that the `missed_deadline` log line is written *before* the `_settle` call in `abandon()` (already done in this diff, but verify in the final merge).