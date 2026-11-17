# heimdall_qwen (qwen/qwen3.8-27b, 21.8 s, $0.001, finish stop)

# PROTOCOL PULSE: CYCLE 2 CODE AUDIT (pp-ingest)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic and security posture but missed two specific nuances highlighted by **Heimdall_Muse**:

1.  **The `duration=0` Edge Case:** I noted that `any(j.get(k))` treats `0` as falsy, but I dismissed it as "highly unlikely" without verifying the downstream behavior. Muse correctly pointed out that `fetch.process` already has a guard for `duration <= 0` ("no duration measured"). This means that even if a video *did* have `duration=0` and all other facts `None`, it would be treated as a stub (UNAVAILABLE) rather than crashing or being mined. The outcome is identical, but the *reasoning* path is different. My Cycle 1 analysis was slightly less precise on this interaction.
2.  **Retry Cadence Comparison:** I stated the retry interval was 3600s, which is correct. Muse explicitly verified that this is *identical* to the previous `PROBE_RETRY_S` ceiling, confirming there is no regression in retry frequency. I implied this but didn't explicitly verify the "no more often than before" constraint against the old constant.

**Did I miss any critical bugs?** No. Both models agreed on the core correctness. My oversight was in the depth of edge-case verification regarding the interaction between the stub detection and the existing duration validation logic.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Position | Agreement |
| :--- | :--- | :--- |
| **Stub Detection Logic** | `not any(j.get(k) for k in FACT_KEYS)` is correct for the observed stubs. | **Agree.** All models concur. The risk of `duration=0` is mitigated by downstream checks. |
| **State Transition** | `UNAVAILABLE` with `next_at` logic is correct. | **Agree.** The `10**9` sentinel for terminal state is a standard pattern in this codebase. |
| **Stall Exclusion** | `UNAVAILABLE` is not in `stall.WAITING`. | **Agree.** Verified by test `test_a_stub_is_never_counted_as_waiting`. |
| **Security (SQLi)** | Parameterized queries used. | **Agree.** No raw SQL injection risk in the diff. |
| **Security (Command Injection)** | `video_id` used in URL. | **Agree.** `video_id` is internal (from DB/queue), not user input. Even if it were, `yt-dlp` is invoked via `subprocess` list args (implied by `gate.run`), not shell string interpolation, so shell metacharacters are safe. |
| **Law Compliance** | Compliant with BUILD, L-x, etc. | **Agree.** The change improves pipeline health by preventing infinite retries on dead videos. |

**Disagreement:** None. The consensus is strong.

## 3. NEW FINDINGS FROM THIS REVIEW

After synthesizing the Cycle 1 outputs and re-reading the diff with fresh eyes:

1.  **Idempotency of `tries` Increment:**
    The code does:
    ```python
    final = tries + 1 >= NO_METADATA_MAX_TRIES
    q.set_state(vid, Q.UNAVAILABLE, ..., tries=tries + 1, ...)
    ```
    If `q.set_state` is not atomic with respect to reading `tries` (i.e., if `tries` is read from the DB *before* the `set_state` call in a separate transaction), a race condition could occur where two workers both read `tries=5`, both calculate `final=True` (since `5+1 >= 6`), and both set `tries=6`. This is benign because the state is already terminal (`next_at` far future). However, if `tries` was read as `4`, both would set `tries=5` and schedule for `now+3600`. This is also benign. The system is self-correcting. **No action required.**

2.  **Log Verbosity:**
    Qwen noted in Cycle 1 that a log line is missing when a stub is given up. Muse noted that the queue's state event records it. I agree with Muse: the `reason` field in `q.set_state` (`"no metadata: {detail}"`) is sufficient for observability. Adding a separate `logger.info` is a P2 nice-to-have but not a blocker.

3.  **`FACT_KEYS` Maintenance:**
    The list `FACT_KEYS` is hardcoded. If `yt-dlp` changes its output schema (e.g., renames `upload_date` to `published`), this detection will break. This is a known risk in any `yt-dlp` integration. The current 5 keys are stable and orthogonal. **No action required** for this diff, but worth noting for future maintenance.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 9.5/10 | Confirmed edge case handling (`duration=0`) is safe due to downstream guards. |
| **Security** | 9/10 | 9/10 | No changes. Input is internal; queries are parameterized. |
| **Law Compliance** | 10/10 | 10/10 | No changes. Improves BUILD compliance. |
| **Maintainability** | 8/10 | 8/10 | `FACT_KEYS` is a magic list, but acceptable. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.
**P1 HIGH:** None.
**P2 MEDIUM:**
1.  **`fetch.py:141`**: Consider adding a comment explaining why `any(j.get(k))` is safe for `duration=0` (i.e., "downstream `process` rejects `duration<=0` anyway"). This prevents future developers from "fixing" it to `is not None` and breaking the stub detection for hypothetical 0-duration videos.
2.  **`fetch.py:273`**: Add a `logger.debug` or `logger.info` when `final` is `True` (i.e., when giving up on a video). This aids in debugging why a video is stuck in `UNAVAILABLE` with a far-future `next_at`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add a comment at `fetch.py:141` clarifying that the truthiness check is intentional and safe because `fetch.process` independently validates `duration > 0`, ensuring that even if a video had `duration=0` and no other facts, it would be correctly handled as unavailable rather than causing a crash or misclassification.**

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The test suite `tests/ingest` must pass (434 passed in Cycle 1).
2.  Mutations M44-M47 must be killed (verified in Cycle 1).
3.  No P0/P1 issues remain (none found).

The code is correct, secure, and compliant. The P2 items are optional improvements for maintainability and observability.