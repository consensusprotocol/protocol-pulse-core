# qwen3.8-27b (qwen/qwen3.8-27b) 22 s finish=stop usage in 6152 / out 1648 usd~0.043 (upper-bound price)

I have reviewed the diff against the stated defect, the governing laws, and the specific check criteria.

### Findings

**<medium> `pipeline/heimdall_health.py:26-27` — State mutation on read path**
The function `probe_due` is semantically a "check" (predicate), but the change makes it a "claim" (action) that mutates persistent state (`last_probe_utc`, `last_probe_by`) and writes to disk (`_save`).
*   **Scenario:** If a caller invokes `probe_due` to check eligibility but fails to subsequently call `probe_result` (e.g., due to an exception in the caller's logic before the probe executes, or a process crash between the claim and the execution), the slot is marked as "spent" (`last_probe_utc` is updated) but no probe result is recorded.
*   **Impact:** The next probe will not be due for another `PROBE_EVERY_S` (2 minutes). This effectively "eats" a probe cycle. While the prompt states "A claimer that never reports leaves the slot spent," this is a significant behavioral change for a function named `probe_due`. It reduces the frequency of health checks in failure scenarios. If the system is in `plan_b` and a prober crashes after claiming, the other prober cannot probe for 2 minutes. This is acceptable per the "one probe per slot" requirement but is a side-effect that should be documented more prominently or the function renamed to `claim_probe_slot` to reflect its imperative nature.

**<low> `pipeline/heimdall_health.py:11` — Default argument `who=""`**
The new parameter `who` defaults to an empty string.
*   **Scenario:** If a legacy caller or a new caller forgets to pass `who`, the state will record `last_probe_by: ""`.
*   **Impact:** This makes debugging "who claimed the slot" impossible for that instance. The test `test_two_probers_share_one_probe_per_slot` correctly passes `who`, but the production code in `providers.py:41` also passes it. However, `pp-ingest` (external repo) must be updated to pass `who`. If `pp-ingest` is not updated simultaneously, it will claim slots with `who=""`, potentially causing confusion in the state file. This is a coordination risk, not a code defect in this diff, but worth noting.

**<low> `tests/providers/test_heimdall_health.py:60` — Test relies on specific timing**
The test uses `T0 + timedelta(minutes=16)` for the first claim and `T0 + timedelta(minutes=17)` for the second check.
*   **Scenario:** `PROBE_EVERY_S` is 120 seconds (2 minutes).
    *   `note(False, **k(15))` sets `failing_since_utc` to T0+15m.
    *   `probe_due` at T0+16m: `now - lp` (where `lp` is likely None or old) >= 120s? Yes. Claims slot. `last_probe_utc` = T0+16m.
    *   `probe_due` at T0+17m: `now - lp` = 1 minute = 60s. 60s < 120s. Returns False. Correct.
    *   `probe_result` at T0+16m (simulating the probe finishing). Note: `probe_result` also updates `last_probe_utc`? The prompt says "probe_result (unchanged) still stamps last_probe_utc when the probe ends."
    *   Wait, if `probe_result` stamps `last_probe_utc` to T0+16m (or slightly later), and the next `probe_due` is at T0+18m:
        *   `now` = T0+18m. `lp` = T0+16m (from claim) or T0+16m+epsilon (from result).
        *   `now - lp` = 2 minutes = 120s.
        *   Condition: `if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S: return False`.
        *   120 < 120 is False. So it proceeds to claim.
    *   The test asserts `probe_due` at T0+18m returns True. This works if the timestamp is exactly T0+16m. If `probe_result` adds a small delay (e.g., T0+16m+1s), then at T0+18m, `now - lp` = 119s, which is < 120s, so it would return False.
    *   **Risk:** The test might be flaky if `probe_result` updates the timestamp to a value slightly later than the claim time, or if the system clock has any drift. The test uses `at(18)` which is exactly 2 minutes after `at(16)`. If `probe_result` sets `last_probe_utc` to the *current* time when it is called (which might be `at(16)` in the test's mocked time, or real time?), the test mocks `now` for `probe_due` but does it mock `now` for `probe_result`?
    *   Looking at the test: `HH.probe_result(True, **k(16))`. `k(16)` passes `now=T0+16m`. So `probe_result` sets `last_probe_utc` to T0+16m.
    *   Then `probe_due` at `at(18)` (T0+18m). `now - lp` = 120s. `120 < 120` is False. So it claims.
    *   This is correct but relies on exact equality. If `PROBE_EVERY_S` was 121s, it would fail. It is tight but correct for the defined constant.

**<info> Compliance with Governing Laws**
*   **LAW 20 / M2:** No gate thresholds changed. No reclassification.
*   **M12 FAIL CLOSED:** The change does not introduce a path where missing data leads to a pass. It leads to a "slot spent" (no probe), which is a conservative failure (less frequent probing) rather than a false positive (probing too often).
*   **Smallest diff:** The diff is minimal and focused.

### SHIP: yes with conditions

**Conditions:**
1.  **Coordinate with `pp-ingest`:** Ensure the `pp-ingest` watcher is updated to pass a non-empty `who` string to `probe_due`. If `pp-ingest` is not updated, it will claim slots with `who=""`, which is functionally correct but operationally opaque.
2.  **Verify `probe_result` timestamp logic:** Confirm that `probe_result` uses the `now` parameter passed to it (as mocked in the test) and not the system clock, to ensure the "2 minutes" window is consistent between the claim and the result. The test suggests it does, but this should be verified in the actual `probe_result` implementation (not in the diff, but implied by the test's success).
3.  **Documentation:** Add a comment to `probe_due` explicitly stating that it has side effects (claims the slot) and that a failed probe execution after a claim will delay the next probe by `PROBE_EVERY_S`.