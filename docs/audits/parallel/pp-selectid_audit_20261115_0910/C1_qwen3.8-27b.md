# qwen3.8-27b (qwen/qwen3.8-27b) 68 s finish=stop usage in 7772 / out 2251 usd_reported=0.002732 usd~0.057 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the provided context, laws, and specific check requests.

### Analysis

**1. Subset Argument (Can the gate refuse a valid medley?)**
The gate checks `n_ch < 3` on `ms` (the pool after free stages). The later check at `:2587` checks `len({m["channel_id"] for m in cleared.values()}) < 3`.
*   `cleared` is a subset of `ms` (moments that passed Step A).
*   If `ms` has < 3 channels, `cleared` (being a subset) cannot have > 2 channels. Thus, if the gate triggers (`n_ch < 3`), the later check *would* also trigger (`cleared_channels < 3`).
*   Therefore, the gate does not refuse a pool that *could* seat a medley (i.e., a pool with >= 3 channels). It only refuses pools that are guaranteed to fail the later check.
*   **Verdict:** Correct. No P0/P1.

**2. Paid Calls Before Gate**
The gate is placed after `ad_read_out`, `scorer_pass`, `trim_variant`, `current_levels`, and `no_role` calculations.
*   `ad_read_out`: Free exclusion screen.
*   `scorer_pass`: Scoring is typically local/computational (unless it calls a model, but the context implies "free stages" precede this). The prompt states "free gates first... paid verdict only for what every free gate passed". The gate is *before* `step_a_plan` (which triggers Step A paid calls) and `confirm_ahead` (Ruling 101 paid calls).
*   The prompt explicitly states: "It ends here, before any paid verdict".
*   **Verdict:** Correct. No P0/P1.

**3. Record Shape and Readers**
The gate returns a dict with keys: `shape`, `packages`, `tried`, `unusable`, `usable`, `current_levels`, `no_role`, `ad_read`, `trimmed`, `reposted`, `scorer`, `prescreen`, `angles`, `takeaways`, `package`, `why_none`, `ruling_109`.
*   **`proof_ledger.py` readers:**
    *   `res["usable"]`: Present.
    *   `res["prescreen"].get("cleared")`: Present (value 0).
    *   `open_work`: Reads `prescreen.held_102` (present, empty) and `visual.unmeasured` (absent, but `open_work` likely handles missing keys or the prompt confirms "leaves no open work"). The prompt states: "The gate's record has held_102 empty and no 'visual', so it leaves no open work".
    *   `CA.seed`: Reads `record.get("tried") or []`. Present (empty list).
*   **Comparison to `:2587` return:** The prompt states the gate returns "the record the rule at :2587 returns". The test `test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns` verifies `set(gate) - {"ruling_109"} == set(late)`. This confirms structural equivalence.
*   **Verdict:** Correct. No P0/P1.

**4. Candidate Exclusion**
The gate condition is `if candidate is None and n_ch < 3:`.
*   If `candidate` is not None, the gate is skipped.
*   The prompt explains: "A build from a ruling-66 candidate returns its outcome in out['candidate']... The gate's record has no 'candidate', so a candidate build keeps its path, unchanged."
*   Test `test_a_build_from_a_candidate_keeps_its_own_path` verifies this.
*   **Verdict:** Correct. No P0/P1.

**5. Tests**
*   `test_one_or_two_channels_ask_nothing`: Verifies no paid calls (`screens`, `events`, etc. are empty) and correct `why_none`.
*   `test_the_channels_are_counted_after_the_free_stages`: Verifies that a moment failing a free stage (topic rule) is not counted in `n_ch`. The test adds a moment from channel "C" that fails the topic rule (implied by `no_role` check). The gate counts `n_ch` from `ms` (after free stages). If the "C" moment is removed by a free stage, it won't be in `ms`, so `n_ch` remains 2. The test asserts `ruling_109` channels is 2. This is correct behavior.
*   `test_the_record_has_the_shape...`: Verifies key parity with the late return.
*   `test_three_channels_are_screened_and_packaged_as_before`: Verifies the gate does *not* trigger for 3 channels.
*   `test_a_build_from_a_candidate_keeps_its_own_path`: Verifies candidate exclusion.
*   **Verdict:** Tests are comprehensive and correct. No P0/P1.

**6. Pre-existing Defect (KeyError in proof_ledger for candidate builds)**
The prompt flags a pre-existing defect: "The early returns before :2703 ... give a CANDIDATE build no out['candidate'], so proof_ledger.py:484 would raise KeyError outside its try."
*   The prompt asks: "Say whether you think it must be fixed in this change."
*   **Analysis:** This is a pre-existing bug in `proof_ledger.py` or `package.py`'s early returns for candidate builds. The current change *adds* another early return (the gate) but explicitly excludes candidate builds (`candidate is None`). Therefore, this change does *not* introduce the bug, nor does it fix it.
*   However, the prompt states: "No candidate is due today... Say whether you think it must be fixed in this change."
*   Since the change is specifically about the "free gates first" optimization for non-candidate builds, and the candidate path is explicitly untouched, fixing an unrelated pre-existing bug in the candidate path is out of scope for this specific "smallest diff" change (Law: Smallest diff). It should be tracked separately. It is not a P0/P1 *for this change* because this change does not make it worse, and it is not triggered by the new code path.
*   **Verdict:** P3 (Nit/Out of Scope). It is a real defect, but not introduced by this diff, and fixing it would violate "smallest diff" if unrelated.

**7. Law Compliance**
*   **LAW 20 / M2:** No gate thresholds changed. No reclassification.
*   **M12 FAIL CLOSED:** The gate returns a specific "no package" state, which is a valid "fail closed" for the medley path (it refuses to build). It does not produce a false pass.
*   **Smallest diff:** The change is minimal (18 lines in `package.py`, 54 lines in tests).

### Findings

[P3] The pre-existing `KeyError` in `proof_ledger.py:484` for candidate builds that hit early returns (like the new gate, though the gate excludes candidates, other early returns like `:2587` do not) is a real defect. However, it is pre-existing, not introduced by this diff, and fixing it is out of scope for this "smallest diff" change. It should be addressed in a separate ticket.

[P3] The variable `n_usable` is used in the log message `log(f"  {n_usable} usable, ...")` inside the gate. I need to verify `n_usable` is defined in scope. Looking at the context: `build()` likely calculates `n_usable` before the gate (as part of the "free stages"). The diff shows `n_ch = len(...)` and then the `if`. The log uses `n_usable`. If `n_usable` is not defined before this point, it will be a `NameError`.
*   *Check:* The prompt says "after the free stages: usable, reposted_once, scorer_pass...". It is highly likely `n_usable` is defined. However, the diff does *not* show the definition of `n_usable`. In the return dict, it uses `"usable": n_usable`. If `n_usable` is not defined, this is a P0.
*   *Re-reading the prompt:* "The build driver... always runs the medley first... The medley pays step A... BEFORE its 3-channel rule". The gate is inserted *before* step A. The prompt says "after the free stages: usable...". It is standard in this codebase (implied) that `n_usable` is calculated early.
*   *Risk:* If `n_usable` is *not* defined at this point, it's a P0. Given the prompt's description "after the free stages: usable...", it implies `usable` (and thus `n_usable`) is available. I will assume it is defined based on the prompt's context "after the free stages: usable...". If it were not, the prompt would likely have flagged it or the tests would fail with NameError. The tests pass (per prompt: "10 of 10 mutations are killed... all pass"). Therefore, `n_usable` is defined.

[P3] The log message `log(f"  {n_usable} usable, {len(ms)} in the pool after the free stages: {why_none}")` is slightly verbose but acceptable.

[P3] The key `"ruling_109"` is added to the output. This is a new key. Readers must handle it. The prompt states `proof_ledger` and `CA.seed` are checked. `CA.seed` reads `tried`. `proof_ledger` reads `usable`, `prescreen`. It does not seem to read `ruling_109`. This is safe.

### Conclusion

The change is correct, minimal, and compliant with the laws. The pre-existing defect is out of scope.

P1_OR_WORSE: 0