# gemma-4-31b-it (google/gemma-4-31b-it) 100 s finish=stop usage in 8105 / out 1927 usd_reported=0.000490 usd~0.053 (upper-bound price)

The code implements RULING 130 (3) to ensure that vision model billing—which often exceeds output caps and thus results in bills that are a small fraction of the total usage list price—still triggers the "reserve tripwire" if the actual bill exceeds the specific amount reserved for that call.

### Analysis

1.  **Fraction vs. Bills**: The `reserve_list_fraction` of `0.6` for `xai_vision:grok-4.7` is correctly derived from the provided data (max bill $0.1752 / list bound $0.2965 $\approx$ 59.1%). This provides a safe ceiling based on historical evidence.
2.  **Tripwire Logic**: 
    *   The modification to `providers.py` introduces `over_held`. This correctly identifies cases where the bill exceeds the `held` reservation, regardless of whether it exceeds the `fraction * list_price`.
    *   The check `_num(f)` and `_num(held)` prevents the tripwire from firing on models without a configured fraction or calls where no reservation was made.
    *   The logic is additive; it does not remove the existing `over_list` check, ensuring that standard models (like Grok) continue to behave as expected.
3.  **Governing Laws**: 
    *   The changes are confined to the infrastructure/billing layer. They do not touch the editorial pipeline, rendering logic, or QA gates.
    *   There are no violations of the Sentence Law, Selection Lock, or any of the L-series laws.
    *   Law 20/M2 is respected as no quality gate thresholds were modified to force a pass.
4.  **Tests**:
    *   `test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list` specifically validates the new `over_held` path.
    *   `test_ruling_130_the_vision_check_is_reserved_at_its_fraction` validates that the `reserve_list_fraction` is correctly applied during the reservation phase.

### Findings

No defects found. The implementation is precise and the tests are comprehensive.

P1_OR_WORSE: 0