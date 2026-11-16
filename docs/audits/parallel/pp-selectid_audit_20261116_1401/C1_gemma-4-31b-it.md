# gemma-4-31b-it (google/gemma-4-31b-it) 266 s finish=stop usage in 9204 / out 4247 usd_reported=0.000812 usd~0.091 (upper-bound price)

The code implements RULING 123 (1) to reduce the budget reservation for the Grok backend to 25% of its list price, with a "tripwire" that reverts the reservation to 100% for the remainder of the day if any single call's reported cost exceeds that 25% threshold.

### Analysis

1.  **Tripwire Logic**: In `Router._settle`, the condition `float(usage["usd_reported"]) > float(f) * usd` correctly compares the actual billed amount against the fraction of the list price (`usd` is the list-price estimate passed into `_settle`). The check `not (d.get("reserve_tripped") or {}).get(backend.name)` ensures the trip is recorded only once per ledger day.
2.  **Persistence**: The trip state is stored in the ledger (`d["reserve_tripped"]`), which is the canonical source of truth for the day's spend. `Router._reserve_fraction` correctly reads this state to determine whether to apply the fraction or revert to `None` (which triggers the full list-price reservation in `Router.call`).
3.  **Specificity**: The logic is gated by the presence of `reserve_list_fraction` in the backend's spec. This ensures that only the xAI reasoning backend (as configured in `model_providers.json`) is affected, leaving other backends at 100% reservation.
4.  **Safety/Fail-Closed**: If `spend_path` is missing or the spec is malformed, `_reserve_fraction` returns `None`, and `Router.call` defaults to the full `upper` (list price) reservation. This prevents under-reserving budget in ambiguous states.
5.  **Tests**: `TestRuling123Reserve` comprehensively covers:
    *   Successful calls staying under the threshold.
    *   A call exceeding the threshold triggering the tripwire.
    *   Subsequent calls being refused due to the reverted (higher) reservation.
    *   The reset of the tripwire upon starting a new day's ledger.
    *   Isolation (ensuring non-fractional backends remain at list price).

### Findings

No defects found. The implementation strictly adheres to the orchestrator's order and the governing laws of the system.

P1_OR_WORSE: 0