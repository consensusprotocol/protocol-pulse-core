# gemma-4-31b-it (google/gemma-4-31b-it) 219 s finish=stop usage in 9634 / out 4432 usd_reported=0.000848 usd~0.095 (upper-bound price)

The code correctly addresses the two identified gaps in the "nothing new" guard (RULING 107 (1)).

### Analysis

1.  **Gap 1: Money Refusals (pipeline/providers.py & tests/package/proof_ledger.py)**
    *   **Mechanism**: The `Router` now tracks `spend_refused` as a list of backend names. The `_reserve` method (the central gate for all paid calls) now wraps the reservation logic in a `try...except SpendLimit` block.
    *   **Correctness**: Any call refused due to spend limits (including ledger read failures that raise `SpendLimit`) is recorded. Since `list.append` is atomic in CPython, this is thread-safe for the worker pools used in the pipeline.
    *   **Integration**: `proof_ledger.py:main` captures this list at the end of a build and passes it to `open_work`. This ensures that if a build was stopped by money, `open_work` will be $> 0$, forcing the next build to retry even if inputs are identical.

2.  **Gap 2: Soft Pass Holds (tests/package/proof_ledger.py)**
    *   **Mechanism**: `open_work` now accesses the `never_empty` (soft pass) record.
    *   **Correctness**: It uses a set difference: `set(soft_holds) - set(clean_holds)`. This correctly identifies unique IDs that were held during the soft pass but missed by the clean pass, preventing double-counting while ensuring all "undone" work is captured.

3.  **Safety and Regression**
    *   **Looping/Payment**: A build stopped by money costs nothing (the call is refused *before* the API hit) and does not produce a reply. The next build will attempt the call again. If the budget is still $0$, it will refuse again and mark `open_work > 0`. This is the intended behavior for budget-constrained resumes.
    *   **Laws**: The changes are confined to the build orchestration and spend tracking. They do not modify the Sentence Law, Selection Lock, or any rendering/selection logic (M1). They adhere to M12 (Fail Closed) by ensuring refusals are treated as undone work.
    *   **Tests**: The new tests in `test_ledger_router.py` and `test_ruling_107_guard.py` specifically target the edge cases: free calls not being counted, ledger failures being counted, and the set logic for soft pass holds.

### Findings

No [P0], [P1], or [P2] defects found. The implementation is precise and follows the provided specifications.

P1_OR_WORSE: 0