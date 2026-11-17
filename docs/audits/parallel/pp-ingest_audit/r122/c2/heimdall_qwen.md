# heimdall_qwen (qwen/qwen3.8-27b, 20.7 s, $0.001, finish stop)

# PROTOCOL PULSE: CYCLE 2 CODE AUDIT (pp-ingest)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I flagged a "Critical Logic Gap" regarding the missing pipeline record check in `pipeline_sweep`. I correctly identified that the *visible* SQL diff did not contain the check, but I failed to definitively resolve whether the check existed in the *unchanged* context lines or if the test was passing due to a mock artifact.

**Heimdall_Muse** and the **Consensus** clarified this:
1.  **The Check Exists:** The consensus explicitly cites `pipeline/ingest/fetch.py:246` (unchanged code) where `if pipeline_transcript(...) is not None` gates the `due.append`. My Cycle 1 output wavered between "code is likely correct" and "diff is incomplete," but I did not explicitly confirm the existence of the gate in the final verdict. Muse confirmed it.
2.  **Scale Context:** Muse correctly identified that the "N+1" concern (checking transcript store for every row) is negligible because the row count is bounded by "transcript waits inside 12h" (a few dozen), not 10k. I raised the N+1 concern but didn't sufficiently weight the business logic constraint (12h window + specific state) that keeps the dataset small.
3.  **Edge Case `float(seen)`:** Muse caught a minor edge case where `published_ts=0` (falsy) would fall through to `discovered_ts`. While unlikely in production (DB defaults), it is a valid logical nuance I missed.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **Pipeline Record Check Missing in Diff** | Qwen (Me, C1) | **AGREE (Refuted by Context)** | I was right that the *diff* didn't show it, but wrong to imply it might be missing from the *code*. The consensus proves it's in the unchanged context. The test `stub0000002` not being due confirms the gate works. |
| **N+1 Query Risk** | Muse (C1) | **PARTIALLY AGREE** | Technically true (loop + I/O), but practically irrelevant due to the 12h/UNAVAILABLE filter limiting rows to <100. Not a P1. |
| **`float(seen)` Falsy Zero** | Muse (C1) | **AGREE** | `0` is a valid epoch (1970), but if `published_ts` is explicitly `0` in the DB, `v.get("published_ts")` returns `0`, which is falsy. It falls to `discovered_ts`. If `discovered_ts` is also `0`, it falls to `now_ts`. This is safe behavior (defaults to current time), so it's not a bug, just a nuance. |
| **Give-up Logic Change** | Both | **AGREE** | The shift from `tries` count to `EXPIRY_H` time-based is correct and fixes the CoinDesk premature give-up bug. |
| **Sweep UPDATE Safety** | Both | **AGREE** | The `WHERE next_at > ?` guard prevents double-processing in concurrent scenarios. |

## 3. NEW FINDINGS FROM THIS REVIEW

**No new critical bugs found.** The combined analysis has resolved the ambiguity in Cycle 1.

*   **Clarification on `pipeline_transcript` Cost:** The consensus notes that `pipeline_transcript` catches `OSError, ValueError, KeyError, TypeError, AttributeError`. This means the "silent failure" I flagged in Cycle 1 (P2) is actually *intended* robustness. If the file is missing or corrupt, it returns `None` (or raises a caught exception), and the video is *not* made due. This is the correct "fail closed" behavior for a sweep that should only promote videos with *valid* pipeline records.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 10/10 | The "missing check" concern was resolved by context evidence. The logic is sound. |
| **Robustness** | 7/10 | 9/10 | The `except ValueError: continue` is now understood as a deliberate fail-closed mechanism for invalid IDs, not a silent bug. |
| **Performance** | 8/10 | 9/10 | N+1 concern mitigated by business logic constraints (small row count). |
| **Maintainability** | 9/10 | 9/10 | No change. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.
**P1 HIGH:** None.
**P2 MEDIUM:**
1.  **Logging in `pipeline_sweep` loop:** `fetch.py:247` (`except ValueError: continue`). While fail-closed is correct, a `debug` log would aid in diagnosing why a specific video is *not* being promoted. *Low priority, but good practice.*
2.  **Explicit `None` check for `seen`:** `fetch.py:273`. While `float(seen)` handles `0` via fallback, explicitly checking `if seen is None` before `float()` would be clearer. *Cosmetic.*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The change from **count-based give-up** (`NO_METADATA_MAX_TRIES`) to **time-based give-up** (`EXPIRY_H`) is the highest-leverage fix. It directly addresses the production bug where transient network issues or API rate limits caused real videos to be permanently marked `UNAVAILABLE` after a fixed number of retries, regardless of how recent the video was.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `pipeline_transcript` function must correctly return `None` for missing/invalid records (verified by consensus and test `stub0000002`).
2.  The `EXPIRY_H` configuration value must be appropriate for the business domain (12h is reasonable for "moments").
3.  The test suite `tests/ingest` must pass (437 passed in Cycle 1).

**Final Verdict:** Ship it. The code correctly implements the design intent, handles edge cases via fail-closed logic, and resolves the premature give-up bug.