# gpt-oss-20b (openai/gpt-oss-20b) 21 s finish=stop usage in 7417 / out 3371 usd_reported=0.000646 usd~0.073 (upper-bound price)

**1. What the other models caught that I missed**

| # | Finding | Why I missed it |
|---|---------|-----------------|
| 1 | **Unbounded retry loop when the spend limit never resets** (P2) | I focused on the correctness of the new bookkeeping but didn’t consider the *control‑flow* effect of `open_work > 0` when the ledger is permanently exhausted. |
| 2 | **Missing unit‑test for the `main()` wiring** (P3) | The change to `open_work(res, sp, money)` and the new `spend_refused` field in the fingerprint is not exercised by any test. |
| 3 | **Thread‑safety comment for `list.append`** (P3) | I assumed CPython’s GIL guarantees atomicity; the comment is a useful reminder for future free‑threaded runs. |
| 4 | **Fragile nested `.get()` chain for the soft‑pass record** (P3) | The code is correct but hard to read; a helper would improve maintainability. |
| 5 | **`spend_refused` records only backend names, not call identities** (P3) | I didn’t note that this is a design choice; the list is only used for the count, not for debugging. |

**2. Where I agree / disagree**

| Finding | Agreement | Reason |
|---------|-----------|--------|
| Unbounded retry loop | **Agree** (P2) | If the spend limit is permanently exhausted, every build will keep retrying, consuming CPU and potentially causing a livelock. The rule does not provide a hard stop for this edge case. |
| Missing unit‑test for `main()` wiring | **Agree** (P3) | The wiring is a single line; a tiny integration test would catch accidental changes. |
| Thread‑safety comment | **Agree** (P3) | The comment is harmless and useful; no code change needed. |
| Nested `.get()` chain | **Agree** (P3) | Readability could be improved; not a functional bug. |
| Backend names only | **Agree** (P3) | By design; no functional impact. |

**3. New findings from this review**

* The **retry‑loop** is a real, potentially catastrophic defect that was not flagged in Cycle 1.  
* The **integration test gap** for the `main()` wiring is a missing safety net that could let future refactors silently break the spend‑refusal accounting.  
* The code now **writes `spend_refused` into the fingerprint**; this is a new observable side‑effect that should be documented and tested.  
* The **soft‑pass set‑difference logic** is correct, but the deeply nested `.get()` chain is fragile and should be refactored for clarity.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Router (`spend_refused` bookkeeping) | 0 | 1 (P2) | Unbounded retry loop discovered |
| `open_work` function | 0 | 0 | No new functional defects |
| `main()` wiring & fingerprint | 0 | 0 | Missing test identified (P3) |
| Thread‑safety comment | 0 | 0 | Comment added (P3) |
| Soft‑pass `.get()` chain | 0 | 0 | Readability issue (P3) |

**P1_OR_WORSE:** 0 (no P0/P1 defects)

**5. Final priority list**

| Priority | Issue | File:Line | Why |
|----------|-------|-----------|-----|
| **P0** | *None* | | |
| **P1** | **Unbounded retry loop** – add a hard stop after N consecutive money‑refused builds or detect a permanently exhausted ledger. | `pipeline/providers.py` (around line 18‑22) and build driver logic (`tests/package/proof_ledger.py`) | Prevent infinite build churn and resource waste. |
| **P2** | **Missing integration test for `main()` wiring** – test that `spend_refused` is correctly passed to `open_work` and written to the fingerprint. | `tests/package/test_main_wiring.py` (new) | Catch accidental changes to the single‑line wiring. |
| **P3** | **Add thread‑safety comment** – document that `list.append` is atomic under CPython GIL. | `pipeline/providers.py` line 9 | Future‑proofing for free‑threaded runtimes. |
| **P3** | **Refactor nested `.get()` chain** – extract a helper to read the soft‑pass record. | `tests/package/proof_ledger.py` line 50‑52 | Improve maintainability. |
| **P3** | **Document that `spend_refused` records backend names only** – add comment or README note. | `pipeline/providers.py` line 9 | Clarify design intent. |

**6. The single highest‑leverage change**

Add a hard stop after a configurable number of consecutive money‑refused builds (or detect a permanently exhausted ledger) so that the system does not enter an infinite retry loop when the spend limit can never be satisfied.

**7. Production ready?**

**No** – the unbounded retry loop is a critical safety issue that must be addressed before shipping. Once the hard‑stop logic is in place and the missing integration test is added, the code can be considered production‑ready.