# qwen3.8-27b (qwen/qwen3.8-27b) 25 s finish=stop usage in 8092 / out 2114 usd_reported=0.001884 usd~0.056 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0910
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the logical soundness of the subset argument and the placement of the gate. I missed the specific **shape divergence risk** that GLM-5.3-FLASH identified regarding the `prescreen` dictionary. While I noted that the keys matched, I did not explicitly verify that the *values* (specifically the nested structure of `held_102` and the absence of `visual`) were safe for the downstream `open_work` and `CA.seed` readers without relying solely on the new test. GLM correctly flagged that the synthetic `prescreen` record in the early return is a hardcoded literal, and if the real `:2587` path ever adds keys to `prescreen` (e.g., via a future change to `parallel_101` or `last_resort_87`), the shape test would catch it, but the *runtime* behavior of `open_work` depends on the specific tolerance of `.get()` calls. The new test `test_the_guard_finds_no_open_work_and_the_registry_no_line_up` (added in the diff) directly addresses this by running the *real* `proof_ledger.open_work` and `candidates.seed` against the gate's record. This was a critical gap in my Cycle 1 analysis: I trusted the key-set equality but didn't explicitly trace the value-level safety for the guard functions.

QWEN3.8-27B provided a very clean confirmation of the subset argument and the "no paid calls" claim, which aligns with my view. However, QWEN also correctly identified that the pre-existing `KeyError` in `proof_ledger.py:484` for candidate builds is out of scope, which I also agreed with but perhaps less explicitly.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH [P2] Shape/Value Divergence:** **AGREE.** The risk is real. The early return hardcodes `prescreen` values. The new test `test_the_guard_finds_no_open_work...` mitigates this by verifying the *actual* reader functions handle the synthetic record correctly. This is a strong fix.
*   **GLM-5.3-FLASH [P2] `n_usable` vs `len(ms)` Log Inconsistency:** **AGREE (Downgraded to P3).** The log line says `{n_usable} usable, {len(ms)} in the pool`. In the test `test_the_channels_are_counted_after_the_free_stages`, `n_usable` is 5 (includes the no-role moment) and `len(ms)` is 4 (excludes it). This is consistent with the base code's semantics where `usable` is the count before the no-role filter, and `pool` is the count after. The log is slightly confusing but not incorrect. The base code at `:2573` likely has similar semantics. This is a nit.
*   **QWEN3.8-27B [P1/P0] Subset Argument:** **AGREE.** The argument holds. `cleared` is a subset of `ms`. If `ms` has < 3 channels, `cleared` cannot have >= 3. The gate is safe.
*   **QWEN3.8-27B [P1/P0] Paid Calls:** **AGREE.** The gate is before `step_a_plan` and `confirm_ahead`. No paid calls occur.
*   **Both [P3] Pre-existing Candidate KeyError:** **AGREE.** This is a pre-existing defect in `proof_ledger.py:484` that is not introduced or worsened by this change. The gate explicitly excludes candidate builds (`candidate is None`). It should be tracked separately.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] The `ruling_109` key is added to the record, but the shape test subtracts it.**
The test `test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns` asserts `set(gate) - {"ruling_109"} == set(late)`. This is correct because the `:2587` return does *not* have a `ruling_109` key. However, this means the gate's record is *not* strictly identical in shape to the `:2587` record; it has one extra key. This is intentional and documented in the finding ("and 'ruling_109': {...}"). No action needed, but worth noting that the "same keys" claim in the finding is slightly imprecise; it's "same keys plus `ruling_109`".

**[P3] The `why_none` string in the gate is different from the `:2587` string.**
Gate: `"the pool spans {n_ch} channel(s) after the free stages: a medley needs 3; no paid verdict (ruling 109)"`
`:2587`: `"2 moments cleared step A from fewer than 3 channels"` (example from test).
This is correct and intended. The gate fails *before* step A, so it cannot report "cleared" counts. The different wording is appropriate.

**[P2] Potential issue with `current_levels` in the early return.**
The early return includes `"current_levels": current_levels(sources.values(), ctx)`. This function is called *before* the gate. Is `current_levels` a paid call? The finding states "free stages: usable, reposted_once, scorer_pass, the no-role and trim rules, ad_read_out". It does *not* explicitly list `current_levels` as a free stage. However, `current_levels` is typically a local computation based on `sources` and `ctx`. If it were a paid call, the gate would be violating "free gates first". The test `test_one_or_two_channels_ask_nothing` asserts `rig.screens, rig.events, rig.hook_calls, rig.visual_calls, rig.medley_calls` are all empty. It does *not* assert that `current_levels` didn't make a call. If `current_levels` makes a model call, this is a P1. Given the context of "free stages", it is highly likely `current_levels` is free. **Assumption: `current_levels` is a free, local computation.** If this assumption is wrong, the gate is invalid.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Logic (Subset Arg)** | 9/10 | 10/10 | Confirmed by QWEN and GLM. No new risks found. |
| **Placement (Free Gates)** | 8/10 | 9/10 | Slight uncertainty about `current_levels` being free, but likely correct. |
| **Record Shape** | 7/10 | 9/10 | New test `test_the_guard_finds_no_open_work...` significantly reduces risk. |
| **Tests** | 8/10 | 9/10 | Comprehensive. The new guard test is a strong addition. |
| **Documentation** | 9/10 | 9/10 | Clear comments and finding. |

## 5. FINAL PRIORITY LIST

1.  **[P2] Verify `current_levels` is a free call.**
    *   File: `pipeline/package.py`
    *   Line: ~2540 (before the gate)
    *   Action: Confirm that `current_levels(sources.values(), ctx)` does not invoke any paid model calls. If it does, the gate must be moved before it, or `current_levels` must be refactored to be free. The test `test_one_or_two_channels_ask_nothing` should be extended to assert that no `current_levels`-related calls are made (if such a stub exists).
2.  **[P3] Clarify `n_usable` vs `len(ms)` in log.**
    *   File: `pipeline/package.py`
    *   Line: 18
    *   Action: Consider adding a comment explaining that `n_usable` includes moments removed by the no-role rule, while `len(ms)` does not. This prevents future confusion.
3.  **[P3] Track pre-existing Candidate KeyError.**
    *   File: `tests/package/proof_ledger.py`
    *   Line: 484
    *   Action: Ensure this is tracked in the handoff as a separate issue. No change needed in this PR.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the test `test_the_guard_finds_no_open_work_and_the_registry_no_line_up` is the highest-leverage change, as it directly verifies that the synthetic record produced by the early return is safe for the critical downstream readers (`open_work` and `CA.seed`), thereby closing the gap between "shape equality" and "runtime safety".

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** Verify that `current_levels(sources.values(), ctx)` is a free, local computation and does not trigger any paid model calls. If it is free, the code is production-ready. If it is paid, the gate must be moved or the function refactored.

P1_OR_WORSE: 0