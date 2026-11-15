# qwen3.8-27b (qwen/qwen3.8-27b) 52 s finish=stop usage in 15019 / out 1682 usd_reported=0.003212 usd~0.070 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2339
# Reviewer: [Your AI]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the string-matching brittleness of the timeout detection and the non-atomic nature of the spend stop. However, I missed two specific nuances that the other models (specifically Qwen and the Consensus) highlighted or clarified:

1.  **The "In-Flight" Spend Bound:** I noted the spend stop wasn't atomic, but I didn't explicitly calculate or articulate *why* it is safe. The Consensus and Qwen correctly identified that because the limit is low ($0.75) and the per-call cost is tiny (cents), the "overshoot" from in-flight calls is negligible and bounded by the number of workers. I treated it as a "potential race condition" rather than a "designed, bounded tolerance."
2.  **The `None` Deadline Semantics:** I flagged `dl is None` as a potential logic gap. Qwen explored this and concluded it is logically sound (no deadline = always in time). I should have been more decisive in Cycle 1 that `None` implies "no constraint" rather than "unknown error state."

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (P1_OR_WORSE: 0):** **AGREE.** Grok correctly identified that the string match for "abandoned at the deadline" is pinned by the test `test_no_answer_by_the_cap_is_a_timeout_with_no_decision`. Since the test runs the *actual* Router logic, if the string changes, the test fails. This makes the "brittleness" a non-issue for a test-only script.
*   **Qwen (P1: Spend Stop Not Atomic):** **PARTIALLY AGREE.** It is technically true that it's not atomic. However, labeling it P1 is an overstatement for a *test driver* with a $0.75 cap. The risk of "data loss" or "wrong result" is zero; the risk is only "spending $0.76 instead of $0.75." This is a P3/P2 at most.
*   **Qwen (P1: Timeout String Match):** **DISAGREE.** As noted above, the test pins the behavior. It is not a defect.
*   **Consensus:** **AGREE.** The consensus that "No real defect" exists is correct. The "fixes" were purely documentary (clarifying the docstring about the spend bound and the timeout string).

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the code with the context of the other models' reviews, I found **one new P2** that was overlooked in Cycle 1:

*   **[P2] `summary()` arithmetic on empty sets:**
    In `replay110.py`, line 244:
    ```python
    "agree_in_time_pct": 100 * cin.count("agree") / len(cin) if cin else None,
    ```
    This is safe. However, look at line 248:
    ```python
    "usd_reported": round(sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported")) and not r.get("cached")), 6)
    ```
    If `rs` is empty, `sum()` returns `0`. This is fine.
    However, look at `incumbent()` (line 268):
    ```python
    "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
    ```
    This is also safe.
    
    *Wait, let me look closer at `table()` line 321:*
    ```python
    lines.append(f"| {k} | {b['pairs']} | {100 * b['agree'] / b['pairs']:.0f} |")
    ```
    If `b['pairs']` is 0, this raises a `ZeroDivisionError`.
    `R.grok_self()` returns a dict. If a verdict type has no recorded Grok answers (unlikely, but possible if the source data is filtered), `b['pairs']` could be 0.
    **Finding:** [P2] Potential `ZeroDivisionError` in `table()` if `R.grok_self()` returns a type with 0 pairs.

*   **[P3] `source_records` deduplication logic:**
    Line 76: `if not rel or rel in seen: continue`.
    Line 78: `seen.add(rel)`.
    This is correct. It ensures each record is processed once.

*   **[P3] `build_router` mutation:**
    Line 101: `r.backends[name(m)] = ...`.
    This mutates the Router instance. Since `build_router` creates a *new* Router instance (line 96), this is safe. It does not touch the global production Router.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Classification Logic** | P2 (String match) | P3 (Nit) | Test pins the string; behavior is correct. |
| **Spend Control** | P2 (Non-atomic) | P3 (Nit) | Bounded overshoot is acceptable for test driver. |
| **Data Integrity** | P3 (Re-parse) | P3 (Nit) | No change. |
| **Table Arithmetic** | P3 (Minor) | P2 (ZeroDiv) | Found potential ZeroDivisionError in `table()`. |
| **Production Safety** | P0 (None) | P0 (None) | No change. No production state touched. |

## 5. FINAL PRIORITY LIST

1.  **[P2] `tests/package/replay110.py:321`**: Guard against `ZeroDivisionError` in `table()` when `b['pairs']` is 0.
    *   *Fix:* `pct = 100 * b['agree'] / b['pairs'] if b['pairs'] else 0`
2.  **[P3] `tests/package/replay110.py:144`**: The string match for timeout is brittle but pinned by tests. No change needed, but a comment is already present (line 140-142).
3.  **[P3] `tests/package/replay110.py:118`**: Spend stop check is not atomic. Acceptable for this use case.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a guard against `ZeroDivisionError` in the `table()` function's baseline Grok section to prevent a crash if a verdict type has no recorded pairs.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** Fix the potential `ZeroDivisionError` in `table()` (line 321). This is a low-probability crash but a trivial fix.

**Rationale:**
*   The code is a test driver, not production pipeline code.
*   It does not modify production state, routing, or config.
*   It reuses existing, tested logic (`replay85`).
*   The spend limits are safe and bounded.
*   The classification logic is correct and pinned by tests.

P1_OR_WORSE: 0