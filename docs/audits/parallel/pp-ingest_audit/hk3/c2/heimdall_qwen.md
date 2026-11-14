# heimdall_qwen (qwen/qwen3.8-27b, 224.1 s, $0.023, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (Continuous Ingest + First-Pass Mining)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the internal consistency of the `max_n` propagation and the `carry_forward` logic, which were correct. However, I missed two significant operational and architectural concerns raised by the other models:

1.  **GLM's P2 on Crash Loss (service.py:399-406):** I noted that `episode_measure` is called twice (redundant) but failed to trace the **atomicity** of the `hook_video` pass. If the hook question succeeds (mining rows into memory) but the spotlight question raises an unhandled exception (e.g., a transient `KeyError` in `episode_measure` or a network glitch not caught by `AllBackendsFailed`), the `except Exception` block at `service.py:443` sets `hook_next_ts` for retry but **discards the hook rows** that were already mined in memory. They are never appended to the ledger. While the reply cache makes the re-ask free, this is a logic gap where "successful" work is lost. I missed this because I assumed the `mine_video` calls were atomic units of work, but they are not; the append happens only at the end.
2.  **MUSE's P1 on Starvation (service.py:401-408):** I noted that `hook_windows` is a shared executor but did not explicitly flag the **self-starvation** risk. The hook pass submits hook windows to `hook_windows` (4 slots). If it's a conversation, it *then* submits spotlight windows to the *same* `hook_windows` pool. Since `mine_video` waits for `as_completed`, the hook windows must finish before the spotlight windows even start. This is sequential, not parallel. However, if the hook windows are slow, they occupy the 4 slots. If another video's hook pass starts (2 videos at once via `HOOK_VIDEOS=2`), its hook windows compete for the same 4 slots. This is acceptable but worth noting that the "4 slots" are shared across *all* hook/spotlight work, not per-video. I missed the explicit "starvation" framing, though the code is safe due to the `as_completed` wait.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM (P2 Crash Loss):** **Agree.** This is a valid P2. The hook rows are lost if the spotlight pass crashes. The fix is to append hook rows immediately after the hook pass succeeds, or to wrap the spotlight pass in a try/except that still appends the hook rows if the spotlight fails.
*   **MUSE (P1 Starvation):** **Partially Agree.** It's not a bug, but it's a performance characteristic. The 4 slots are shared. With 2 videos, you have 2 hook passes running. Each hook pass has ~8 windows. That's 16 tasks on 4 threads. The spotlight windows add more. The `as_completed` ensures no deadlock, but latency for the second video's hook pass will increase if the first video's spotlight pass is running. This is acceptable for the current scale (2 videos at once) but should be monitored.
*   **QWEN (Myself, Cycle 1):** I was correct that `max_n` propagation is consistent. I was correct that `carry_forward` is correct. I was correct that the cost calculation is safe due to SQLite WAL.

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding 1: `spot_rows` NULL vs 0 Semantics (service.py:431)**
In `service.py:431`, `spot_rows=len(spot) if srep is not None else None`.
*   If the video is **not** a conversation, `srep` is `None`, so `spot_rows` is `NULL`.
*   If the video **is** a conversation, but the spotlight question **failed** (all windows failed), `srep` is a report dict (not `None`), but `spot` is an empty list `[]`. So `spot_rows` is `0`.
*   **Implication:** `stats.py:111` does `SUM(COALESCE(spot_rows,0))`. This correctly treats `NULL` as 0. However, the distinction between "not asked" (NULL) and "asked, none found" (0) is lost in the stats. This is fine for the current stats, but if we ever want to know "how many conversations had 0 spotlights," we can't distinguish it from "how many non-conversations had 0 spotlights." This is a minor observability gap, not a bug.

**Finding 2: `episode_measure` Redundancy (mine.py:564)**
`episode_measure` is called in `mine_video` (line 564) for both the hook and spotlight passes. This is redundant. The episode measure is deterministic from the record. It could be passed in from `hook_video` to avoid re-parsing the transcript segments. **Impact: Low.** It's a CPU waste, not a correctness issue.

**Finding 3: `check_roles` Missing `flagcheck` (service.py:88)**
In Cycle 1, I noted that `check_roles` was added. I verified that it now includes `flagcheck.ROLE`. This is correct. A missing `flagcheck` role would cause a crash-loop in the calibration, not a clean stop. The fix is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 8.5/10 | GLM's P2 (crash loss) is a real logic gap. It's not a P0, but it's a P2 that should be fixed. |
| **Law Compliance** | 10/10 | 10/10 | No changes. L-x, L-l, L-j/L-m are all compliant. |
| **Performance** | 8/10 | 7.5/10 | MUSE's starvation point is valid. The shared 4-slot executor is a bottleneck for conversations. |
| **Observability** | 9/10 | 8.5/10 | The `spot_rows` NULL vs 0 distinction is lost in stats. The crash loss (GLM P2) is not logged as a "partial success." |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **Fix Crash Loss in `hook_video` (service.py:399-406):** If the spotlight pass crashes, the hook rows are lost. **Fix:** Append hook rows immediately after the hook pass succeeds, or wrap the spotlight pass in a try/except that appends hook rows if the spotlight fails.
    *   *Code:* `service.py:401-408`
    *   *Test:* `test_service.py::test_the_hook_pass_of_a_conversation_asks_5_hooks_and_the_spotlight_question_a_solo_one_neither` (add a case where the spotlight pass raises an exception).

**P2 MEDIUM:**
1.  **Reduce `episode_measure` Redundancy (mine.py:564):** Pass the episode measure from `hook_video` to `mine_video` to avoid re-parsing.
    *   *Code:* `mine.py:564`, `service.py:401-408`
2.  **Clarify `spot_rows` Semantics (service.py:431):** Consider using a separate column or a JSON field to distinguish "not asked" from "asked, none found."
    *   *Code:* `service.py:431`, `stats.py:111`
3.  **Monitor Starvation (service.py:401-408):** Add logging to track the time spent in the hook pass vs. the spotlight pass. If the spotlight pass is slow, it will delay the next video's hook pass.
    *   *Code:* `service.py:401-408`

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the crash loss in `hook_video` by appending hook rows immediately after the hook pass succeeds, before starting the spotlight pass.** This ensures that even if the spotlight pass fails, the hook rows are not lost.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Fix P1-1 (Crash Loss):** The hook rows must be appended to the ledger immediately after the hook pass succeeds, before the spotlight pass starts. This is a small change but critical for data integrity.
2.  **Monitor P2-3 (Starvation):** Add logging to track the time spent in the hook pass vs. the spotlight pass. If the spotlight pass is slow, it will delay the next video's hook pass. This is not a blocker, but it should be monitored.

**Verdict:** The code is well-structured, compliant with the laws, and the logic is sound. The P1 crash loss is the only significant issue, and it is easy to fix. Once fixed, this is production-ready.