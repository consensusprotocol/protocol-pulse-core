# heimdall_qwen (qwen/qwen3.8-27b, 63.0 s, $0.003, finish stop)

# PROTOCOL PULSE: CYCLE 2 CODE AUDIT REPORT

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the `batch.py` logic (hourly vs. real-time spend) and lock ordering. I missed two significant issues in the `xllm_audit.py` (driver) code that the other models (specifically Muse) identified or implied:

1.  **The N+1 Query Storm in `abandoned_usd` (Muse C1-2):** I noted the calculation logic but failed to flag the performance impact. `abandoned_usd` is called inside `watcher_spend`, which is called by `share_left` on *every* paid call reservation. If there are many distinct `(model, role)` pairs with abandoned calls, this triggers a cascade of SQL queries (`SELECT AVG...`) per pair, per reservation. This is a critical performance bottleneck under load that I overlooked.
2.  **The `estimate()` Over-Counting Logic (Muse C1-4):** I did not scrutinize the `estimate` function in `xllm_audit.py` closely enough. Muse correctly noted that while the logic is "correct per spec" (capping total spend), the estimation method (using `len(prompt)/3.0` and full `max_out` budget) is extremely conservative. While not a bug, it's a design choice that could lead to frequent `REFUSED` errors if the cap is tight, which I should have flagged as a usability/operational risk.
3.  **The `now + 1.0` Magic Number (Muse C1-3):** I identified the inconsistency between `notice()` and `share_left()` but dismissed the `+1.0` as a minor detail. Muse correctly identified it as a "fragile" magic number that should be documented or replaced with a clear constant, as it directly affects the race condition window for call reservations.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with Muse (C1-2, N+1 Queries):** This is a valid P1 performance issue. The health thread and reservation path will degrade significantly if the `calls` table grows and contains many abandoned calls.
*   **Agree with Muse (C1-3, `now + 1.0`):** I agree this is fragile. It creates a 1-second window where a call might be allowed by the router but not yet counted in the "current" spend if the DB insert is delayed, or conversely, counted in the "next" second's bucket. It should be `now` (inclusive) or a clearly defined `RESERVATION_LOOKAHEAD`.
*   **Disagree with Qwen (Self) on "Critical Logic Error" for Hourly Spend:** In Cycle 1, I labeled the difference between `notice()` (hourly) and `share_left()` (real-time) as a "Critical Logic Error." Upon reflection, this is **by design**. The STATE line is a *report* (hourly granularity), while the Router is an *enforcement* mechanism (real-time granularity). The documentation is misleading, but the code behavior is correct for its respective purposes. I downgrade this from P0 to P2 (Documentation).
*   **Agree with Consensus on Lock Ordering:** Both Muse and I confirmed no deadlock. The lock order `RoleCaps -> batch -> queue` is consistent.

## 3. NEW FINDINGS FROM THIS REVIEW

### 3.1 `xllm_audit.py`: `record()` Ledger Append is Not Atomic (P1)
**File:** `xllm_audit.py`, `record()` function.
```python
    with open(ledger, "a") as f:
        for rid, b in booked.items():
            f.write(json.dumps(...) + "\n")
```
The `COST.json` write is atomic (`os.replace`), but the **ledger append** is not. If the process crashes between writing the first line and the second line of a multi-reviewer cycle, the ledger will be corrupted (partial JSON line). While `COST.json` is the source of truth for the cap, the ledger is used for auditing and debugging. A partial line will break any downstream parser that reads the ledger.
**Fix:** Write the entire ledger block to a temp file and `os.replace` it, or use a transactional append mechanism (e.g., write to a temp file, then `cat` append, or use a database). Given the simplicity, writing the whole block to a temp file and replacing the ledger file (if it's small) or using a lock + atomic rename for the ledger file is safer.

### 3.2 `xllm_audit.py`: `estimate()` Uses `max_out` for All Reviewers (P2)
**File:** `xllm_audit.py`, `estimate()`.
```python
    for rid in run:
        tokens, out = len(prompt_for(rid)) / 3.0, max_out(REVIEWERS[rid])
```
`max_out` is the *maximum* tokens the model *can* generate. The estimate assumes every reviewer will generate a full `max_out` response. This is a very high over-estimate. If `max_out` is 16,000 tokens, and the actual response is 2,000 tokens, the estimate is 8x too high. This will cause the `cap_check` to refuse cycles that would actually fit within the cap.
**Fix:** Use a more realistic average output length (e.g., 50% of `max_out` or a historical average) for the estimate, or document that this is a "worst-case" estimate.

### 3.3 `batch.py`: `abandoned_usd` Memoization Scope (P1)
**File:** `batch.py`, `watcher_spend()`.
The memoization of `abandoned_usd` is likely local to the `watcher_spend` call. However, `watcher_spend` is called frequently. If the memoization is not global or cached across calls, the N+1 problem is even worse. If it is global, it needs to be invalidated when new calls are added. The current code likely recalculates every time.
**Fix:** Implement a proper cache (e.g., `functools.lru_cache` with a TTL or manual invalidation) for `abandoned_usd` results, keyed by `(model, role, until)`.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 8/10 | No new correctness bugs found. The "hourly" issue is design, not bug. |
| **Performance** | 6/10 | 5/10 | N+1 query storm in `abandoned_usd` is a significant performance risk under load. |
| **Robustness** | 7/10 | 6/10 | Ledger append is not atomic. `now + 1.0` is fragile. |
| **Maintainability** | 7/10 | 7/10 | Documentation is misleading, but code is readable. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None. (The "Critical Logic Error" from Cycle 1 is downgraded to P2).
*   **P1 HIGH:**
    1.  **N+1 Query Storm in `abandoned_usd`** (`batch.py`): Optimize or cache the `AVG(prompt_tokens)` queries. This will block the reservation path under load.
    2.  **Non-Atomic Ledger Append** (`xllm_audit.py`): The ledger file can be corrupted by a crash. Use atomic write or transactional append.
*   **P2 MEDIUM:**
    1.  **Misleading Documentation** (`batch.py`): Clarify that `notice()` is hourly (report) and `share_left()` is real-time (enforcement).
    2.  **Magic Number `now + 1.0`** (`batch.py`): Replace with a named constant `RESERVATION_LOOKAHEAD_S` and document its purpose.
    3.  **Over-Conservative Estimate** (`xllm_audit.py`): The `estimate()` function uses `max_out` for all reviewers, leading to frequent `REFUSED` errors. Use a more realistic average.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Optimize `abandoned_usd` to avoid N+1 queries.** This is the only change that will prevent the system from degrading under load. The other issues are either documentation, minor robustness, or usability.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Fix the N+1 query storm** in `abandoned_usd` (P1). This is a performance blocker.
2.  **Make the ledger append atomic** (P1). This is a robustness blocker.
3.  **Update documentation** to clarify the hourly vs. real-time spend logic (P2). This is a usability blocker.

If these three conditions are met, the code is production-ready. The core logic is sound, and the lock ordering is correct.