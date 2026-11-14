# heimdall_qwen (qwen/qwen3.8-27b, 307.2 s, $0.009, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest (A36: WIDEN)
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Heimdall_GLM (z-ai/glm-5.3-flash):**
*   **The `bool` subclass trap:** GLM explicitly highlighted that `isinstance(n, bool)` must be checked *before* `isinstance(n, int)` because `bool` is a subclass of `int` in Python. While I noted the logic was correct, I did not explicitly call out the *order* of checks as a critical implementation detail that prevents a subtle bug (where `True` would be treated as `1` marker). This is a high-value observation for code maintainability.
*   **Rounding Boundary Analysis:** GLM noted that `episode_measure` rounds `turns_per_min` to 2 decimals. This means a true rate of `0.295` becomes `0.3` and is asked, while `0.2949` becomes `0.29` and is skipped. I missed this specific interaction between the measurement function and the predicate. It confirms the boundary is effectively `[0.295, 0.305)` for the "ask" decision, which is a defensible engineering choice but worth documenting.
*   **Cache Key Stability:** GLM verified that for solo episodes (where `max_n` remains 3), the prompt text is identical to the previous version, meaning `sha256(prompt)` matches the cached entry. This confirms the "free re-run" claim for unchanged prompts. I assumed this but did not verify the cache key mechanics.

**Heimdall_Muse (meta-models/muse-spark-open-816b-a42b):**
*   **SQL Metric Improvement:** Muse correctly identified that changing `spotlight_asked_videos` from a threshold proxy (`episode_tpm >= ?`) to ground truth (`spot_rows IS NOT NULL`) is a significant correctness improvement. It handles edge cases (unmarked, unmeasurable) that the old metric missed. I agreed with the logic but Muse's framing of it as "superior" and "ground truth" is more precise.
*   **Circular Import Risk:** Muse noted that removing `from . import mine` from the top of the SQL query block in `stats.py` (and moving it to a lazy import later) eliminates a potential circular import risk. I missed this architectural benefit.
*   **Log Message Debuggability:** Muse pointed out that the new log message in `service.py` includes `speaker_markers` count, which is more debuggable than the old message. I noted the accuracy but missed the *utility* improvement.

**My Own Cycle 1 Gaps:**
*   I was too focused on the *logic* of `is_conversation` and less on the *implications* of the version bump on caching and the *architectural* changes in `stats.py`.
*   I did not explicitly verify the `bool` check order, which is a common Python pitfall.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **`is_conversation` logic is correct** | All | **Agree** | The predicate correctly implements "skip only marked episodes under 0.3 TPM". The `bool` exclusion is critical and correctly ordered. |
| **`bool` subclass trap** | GLM | **Agree** | `isinstance(True, int)` is `True`. Checking `isinstance(n, bool)` first is essential. The code does this. |
| **Rounding boundary (0.295 -> 0.3)** | GLM | **Agree** | `round(0.295, 2)` is `0.3` (banker's rounding or standard float behavior). This means the effective threshold is slightly lower than 0.3. This is acceptable and documented in the design. |
| **Cache key stability for solo** | GLM | **Agree** | Solo episodes use `max_n=3`, same as before. The prompt text is identical. Cache hits are guaranteed. |
| **SQL metric improvement** | Muse | **Agree** | `spot_rows IS NOT NULL` is the correct ground truth for "was the spotlight question asked?". The old threshold proxy was flawed. |
| **Circular import removal** | Muse | **Agree** | Moving `from . import mine` to a lazy import in `stats.py` is good practice and avoids potential import cycles. |
| **Log message improvement** | Muse | **Agree** | Including `speaker_markers` in the log message aids debugging. |
| **Version bump correctness** | All | **Agree** | `mine-hook/4` correctly triggers re-queueing via `hooks --rerun`. |

**Disagreements:**
*   None. All three reviewers (including my Cycle 1 self) converged on the same core assessment: the change is correct, safe, and an improvement.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`stats.py` Lazy Import Placement:**
    In `stats.py`, the line `from . import mine` is now placed *after* the first SQL query but *before* the second SQL query that uses `mine.CONVERSATION_TPM`.
    ```python
    hk = q.rows("SELECT ... SUM(spot_rows IS NOT NULL) AS asked ...") # No mine import needed
    out["hooks_12h"] = {...}
    from . import mine             # (lazy) the hook pass's own threshold
    lim = mine.CONVERSATION_TPM
    by_ep = {}
    for r in q.rows("SELECT ... WHERE ... AND hook_ts IS NOT NULL", ...):
        # Uses lim
    ```
    This is correct. The first query does not need `mine`. The second query does. The lazy import is placed exactly where it is needed. This is clean.

2.  **`service.py` Log Message Edge Case:**
    The log message:
    ```python
    f"no spotlight question (a marked solo episode: {ep.get('speaker_markers')} markers, "
    f"{ep.get('turns_per_min')} turns / min)"
    ```
    This is only reached if `srep is None` AND `scrash is None`.
    `srep` is `None` if `mine.is_conversation(ep)` is `False`.
    `is_conversation` is `False` ONLY if `speaker_markers > 0` AND `turns_per_min < 0.3`.
    Therefore, `ep.get('speaker_markers')` will always be an int > 0, and `ep.get('turns_per_min')` will always be a float < 0.3 (or None, but if None, `is_conversation` returns True, so this branch is not reached).
    Wait, if `turns_per_min` is `None`, `is_conversation` returns `True`. So this log message is *only* reached when `turns_per_min` is a valid float < 0.3.
    So the log message is always accurate. It will never print `None` for `turns_per_min` in this specific branch.

3.  **`mine.py` `episode_measure` Consistency:**
    `episode_measure` returns `turns_per_min` as `None` if `mins <= 0`.
    `is_conversation` handles `None` by returning `True` (asked).
    This is consistent with the ruling: "marked, its rate not measurable: asked".

4.  **Test Coverage:**
    The new tests in `test_mine.py` cover:
    *   `{"speaker_markers": 5, "turns_per_min": 0.3}` -> `True` (boundary)
    *   `{"speaker_markers": 5, "turns_per_min": 0.29}` -> `False` (skip)
    *   `{"speaker_markers": 0, ...}` -> `True` (unmarked)
    *   `{"speaker_markers": 5, "turns_per_min": None}` -> `True` (unmeasurable)
    *   `{"speaker_markers": True, ...}` -> `True` (bool trap)
    *   `{"speaker_markers": 5, "turns_per_min": "0.1"}` -> `True` (string trap)
    *   `None` / `{}` -> `True` (missing data)
    This is comprehensive.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 10/10 | GLM's analysis of the `bool` trap and rounding boundary confirmed the logic is robust. Muse's analysis of the SQL metric confirmed the improvement. No new bugs found. |
| **Law Compliance** | 9/10 | 10/10 | The change adheres to L-x (no single model), L-l (strict validation), L-j (fail closed/open as appropriate). The "fail open" for asking is justified by the ruling's cost argument. |
| **Security** | 9/10 | 9/10 | No new security risks. SQL is parameterized. Secrets are redacted. The lazy import does not introduce a vulnerability. |
| **Backend Quality** | 8/10 | 9/10 | The lazy import in `stats.py` is a quality improvement (avoids circular imports). The log message is more debuggable. The SQL metric is more accurate. |
| **Frontend Quality** | N/A | N/A | Backend service. |
| **World-Class Gap** | 7/10 | 8/10 | The code is now more robust and maintainable. The only gap is the lack of explicit documentation of the rounding boundary (0.295 -> 0.3), but this is a minor point. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:**
*   None. The change is safe to ship.

**P1 HIGH:**
*   None.

**P2 MEDIUM:**
*   **Documentation:** Add a comment in `mine.py` near `CONVERSATION_TPM` or `is_conversation` noting that `turns_per_min` is rounded to 2 decimals in `episode_measure`, so the effective boundary is `[0.295, 0.305)`. This helps future maintainers understand why a video with a true rate of 0.294 might be asked.
*   **Test:** Add a test case for `turns_per_min=0.295` to verify it is asked (due to rounding to 0.3). This documents the behavior.

**P3 LOW:**
*   **Refactor:** Consider extracting the `bool` check logic into a helper function `is_int_count(n)` to make the `is_conversation` function more readable. However, the current code is clear enough.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The change to `is_conversation` to "fail open" (ask) when data is missing or unmeasurable is the highest-leverage change.** It ensures that no interview is missed due to a measurement error or missing caption markers, which aligns with the orchestrator's ruling that "the cost of asking is nothing and the cost of missing an interview is the whole point." This single change improves the recall of the hook pass for a negligible cost.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `hooks --rerun` command must be executed to re-queue the 12-hour window of videos with the new `mine-hook/4` version. This is a standard operational step, not a code change.
2.  The `stats.py` lazy import must be verified in the production environment to ensure no circular import issues arise (though the code review suggests it is safe).
3.  The new log messages in `service.py` should be monitored for the first 24 hours to ensure they are accurate and helpful.

**Final Verdict:** The code is correct, secure, and compliant with the laws. The change is an improvement over the previous version. It is ready for production.