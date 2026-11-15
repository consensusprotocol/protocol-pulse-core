# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 6434 / out 3936 usd_reported=0.003106 usd~0.078 (upper-bound price)

I will review the provided diff against the governing laws and the specific questions asked.

### Analysis

**1. Context and Scope**
The diff modifies `tests/package/proof_ly.py` and `tests/package/test_ruling_102.py`.
- `proof_ly.py` defines constants for a "Proof of Work" or audit ledger system (likely related to the "LY" or "Local Judge" mentioned in the laws, specifically RULING 87/102/108).
- The change updates the budget limits from a previous "$20 order" to a new "Batch 3" with an $8.00 total cap, specifically allocating $4.50 for builds/sealing and setting a stop threshold at $4.00.
- The ledger file path changes from `SPEND_LY.json` to `SPEND_B3.json`.

**2. Review of Specific Questions**

*   **(1) Can any build path still write the closed SPEND_LY.json?**
    *   The diff shows `SPEND = os.path.join(OUT, "SPEND_B3.json")`.
    *   The comment states: "The $20 order's SPEND_LY.json is CLOSED... never written again."
    *   The test `test_no_build_starts_at_the_stop_and_one_starts_below` asserts `self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))`.
    *   *Assumption:* `PLG.PL` refers to the `proof_ly` module imported in the test. If `proof_ledger` (or the router) uses `PL.SPEND` as the target path for writing, then no, it will not write to the old file. The diff does not show the *writer* code, but it shows the *configuration* of the writer. The configuration is updated. The risk is if there is hardcoded logic elsewhere, but based on the provided code, the source of truth for the path is updated.
    *   *Verdict:* No, based on the provided diff, the path is updated.

*   **(2) Are the stop and the limit consistent with "never start a build that would end over the cap"?**
    *   **Cap (Limit):** `LY_LIMIT_USD = 4.50`.
    *   **Stop:** `LY_STOP_USD = 4.00`.
    *   **Build Cost Range:** The comment states: "A build runs $0.15-0.50".
    *   **Logic:**
        *   If current spend is $3.99, `start_refused(3.99)` returns `None` (allows start).
        *   Max cost of a build is $0.50.
        *   $3.99 + $0.50 = $4.49.
        *   $4.49 < $4.50 (Limit).
        *   If current spend is $4.00, `start_refused(4.00)` returns a refusal string (stops start).
        *   Why stop at $4.00? Because if you start at $4.00, and the build costs $0.50, you end at $4.50. This is *at* the limit. The law/comment says "none ends over $4.50". Ending *at* $4.50 is allowed.
        *   However, the stop is at $4.00. This means you cannot start a build if you have already spent $4.00.
        *   Let's check the boundary:
            *   Spend = $3.99. Start allowed. Max end = $4.49. OK.
            *   Spend = $4.00. Start refused.
            *   Is there a gap? What if Spend = $3.995? The code uses floats. `3.995 >= 4.00` is False. Start allowed. Max end = $4.495. OK.
            *   What if Spend = $4.00? `4.00 >= 4.00` is True. Start refused.
            *   The comment says: "No build starts at or over $4.00... none ends over $4.50".
            *   If a build starts at $3.99 and costs $0.50, it ends at $4.49.
            *   If a build starts at $3.99 and costs $0.51 (hypothetically, though comment says max 0.50), it ends at $4.50.
            *   The constraint is "never start a build that would end over the cap".
            *   Cap = 4.50.
            *   Max Build Cost = 0.50.
            *   Therefore, Max Start Spend = Cap - Max Build Cost = 4.50 - 0.50 = 4.00.
            *   So, you can start if Spend < 4.00? Or Spend <= 4.00?
            *   If Spend = 4.00, and Build = 0.50, End = 4.50. This is *not* over the cap.
            *   The code refuses if `spent0 >= PL.LY_STOP_USD` (4.00).
            *   So it refuses at 4.00.
            *   This is **conservative**. It prevents starting at 4.00, even though starting at 4.00 would result in exactly 4.50 (which is allowed by "not over").
            *   Is this a defect? The comment says "No build starts at or over $4.00". This matches the code.
            *   Does it violate "never start a build that would end over the cap"? No, it's stricter. It prevents builds that would end *at* the cap if the cost is exactly max.
            *   Wait, if I start at 3.99, I end at 4.49.
            *   If I start at 4.00, I end at 4.50.
            *   The code blocks 4.00.
            *   This is safe. It might block a valid build (one that ends exactly at the limit), but it does not allow an invalid one.
            *   *Verdict:* Consistent and safe (fail-closed).

*   **(3) Does the test pin the behaviour?**
    *   The test `test_no_build_starts_at_the_stop_and_one_starts_below` checks:
        1.  `PLG.PL.LY_STOP_USD` is 4.00.
        2.  `PLG.PL.LY_LIMIT_USD` is 4.50.
        3.  `PLG.PL.SPEND` ends with `SPEND_B3.json`.
        4.  `PLG.start_refused(3.99)` is `None` (allowed).
        5.  `PLG.start_refused(4.0)` contains the refusal message.
    *   This pins the constants and the boundary logic.
    *   *Verdict:* Yes.

**3. Governing Laws Compliance Check**

*   **LAW 20 / M2 (Fail Closed):** The logic `spent0 >= LY_STOP_USD` refuses the build. This is fail-closed. If the spend is unknown or high, it refuses.
*   **M12 (Fail Closed):** Missing ledger file is treated as empty ($0.00). This is standard for a new batch.
*   **Smallest Diff:** The diff is small and focused.
*   **No New Renderer/Compositor:** N/A (this is test/ledger logic).
*   **L-j (Release Authorised on Bytes):** This code is part of the audit/proof system. It doesn't directly handle the video release gates, but it handles the "Local Judge" spend. The change is to the budget limits.
*   **L-k (Canonical Form):** N/A for numeric limits.

**4. Potential Issues**

*   **Floating Point Precision:**
    *   `LY_STOP_USD = 4.00`
    *   `LY_LIMIT_USD = 4.50`
    *   `start_refused(3.99)` -> `3.99 >= 4.00` is False.
    *   `start_refused(4.0)` -> `4.0 >= 4.00` is True.
    *   In Python, `4.0 == 4.00` is True.
    *   However, if `spent0` is calculated via floating point addition (e.g., `0.1 + 0.2`), it might be `0.30000000000000004`.
    *   If the ledger accumulates spend, and the sum of many small builds approaches 4.00, floating point errors could cause `spent0` to be `3.999999999` or `4.000000001`.
    *   If it's `4.000000001`, `>= 4.00` is True -> Refused. (Safe).
    *   If it's `3.999999999`, `>= 4.00` is False -> Allowed.
    *   If allowed, and the build costs $0.50, the new spend is `3.999999999 + 0.50 = 4.499999999`.
    *   Is `4.499999999 > 4.50`? No.
    *   So it stays under the limit.
    *   What if the build cost is also floating point?
    *   The comment says "A build runs $0.15-0.50".
    *   If the system uses integer cents (ticks) internally, this is not an issue. The comment mentions `cost_in_usd_ticks` in the context of the ledger.
    *   Line 13: "vendors' own figures (xAI cost_in_usd_ticks...".
    *   If the ledger stores ticks (integers), then `spent0` is likely converted to USD for the check, or the check is done in ticks.
    *   The code shows `PLG.start_refused(3.99)`. This implies `start_refused` takes a float USD value.
    *   If `start_refused` converts ticks to USD, there is a risk of precision loss.
    *   However, `4.00` is exactly representable in binary floating point? No, `0.1` is not. `4.0` is. `0.5` is.
    *   `3.99` is not exactly representable.
    *   But the comparison `spent0 >= 4.00` is robust enough for a budget guard if the underlying data is integer ticks.
    *   *Finding:* [P3] Potential floating point precision issue if `spent0` is derived from float arithmetic rather than integer ticks. However, given the context of "ticks" in the ledger, this is likely handled correctly in the unshown `start_refused` implementation.

*   **Consistency of "Stop" vs "Limit":**
    *   The stop is 4.00. The limit is 4.50.
    *   The max build cost is 0.50.
    *   This leaves a buffer of 0.00.
    *   If a build costs *more* than 0.50 (e.g., due to a price change or error), and you start at 3.99, you could exceed 4.50.
    *   The comment says "A build runs $0.15-0.50". This is an assumption.
    *   If the assumption is wrong, the guard fails.
    *   However, the guard is based on the *known* max cost.
    *   *Finding:* [P2] The safety margin depends on the accuracy of the "max build cost $0.50" assumption. If a build costs $0.51, starting at $3.99 results in $4.50 (OK), but starting at $4.00 is blocked. If a build costs $0.60, starting at $3.99 results in $4.59 (Over Limit). The code does not check the *actual* cost of the specific build being started, only the current spend.
    *   Wait, the comment says: "each paid call still RESERVES its price-table upper bound while in flight".
    *   This implies the reservation logic handles the specific cost.
    *   `start_refused` is just the *gate* to start.
    *   If the reservation logic is correct, then `start_refused` only needs to ensure there is *room* for the max possible cost.
    *   If the max possible cost is 0.50, then stopping at 4.00 is correct.
    *   If the max possible cost is higher, the stop should be lower.
    *   The diff updates the stop to 4.00 based on the new budget.
    *   *Verdict:* The logic is consistent *if* the max build cost is indeed 0.50.

*   **Test Coverage:**
    *   The test checks `3.99` (allowed) and `4.0` (refused).
    *   It does not check `4.01` (refused).
    *   It does not check `0.0` (allowed).
    *   *Finding:* [P3] Test could be more comprehensive (e.g., check 0.0, 4.01).

*   **Law L-j (Release Authorised on Bytes):**
    *   This change affects the "Local Judge" spend ledger.
    *   Does this affect the release of the video?
    *   The laws state: "L-j ... 'all release gates passed' means every REQUIRED gate ran...".
    *   The "Local Judge" is likely a QA gate.
    *   If the spend limit is hit, the judge might stop working.
    *   The change ensures the judge has a new budget.
    *   This is compliant.

*   **Law M12 (Fail Closed):**
    *   If the ledger file is missing, it starts at $0.00.
    *   If the spend is unknown, `start_refused` should fail closed.
    *   The diff doesn't show `start_refused` implementation, but the test implies it works.
    *   *Verdict:* Compliant.

### Findings

1.  **[P2] Reliance on Assumed Max Build Cost:** The stop threshold ($4.00) is calculated as `Limit ($4.50) - Max Build Cost ($0.50)`. If the actual max build cost exceeds $0.50 (e.g., due to API price changes or unexpected token usage), a build starting at $3.99 could exceed the $4.50 limit. The code does not dynamically adjust the stop based on the *actual* cost of the pending build, but rather a static assumption. While the comment mentions "RESERVES its price-table upper bound", the `start_refused` gate itself is static. If the reservation logic is separate and correct, this is mitigated. However, the gate `start_refused` is the first line of defense.
    *   *Mitigation:* Ensure the "price-table upper bound" used for reservation is the same $0.50 used to calculate the stop. If the price table changes, both must update.

2.  **[P3] Floating Point Precision:** The use of floats for currency (`4.00`, `3.99`) can lead to precision issues. If `spent0` is derived from summing floats, it might be `3.9999999999999996`. This is `< 4.00`, so it would be allowed. If the build costs `0.50`, the result is `4.4999999999999996`, which is `< 4.50`. This is safe. However, if the build cost is also imprecise, it could drift. Using integer cents (ticks) for the comparison would be more robust. The ledger uses ticks, but the interface uses floats.

3.  **[P3] Test Completeness:** The test only checks the boundary at $4.00 and just below ($3.99). It does not check significantly lower values (e.g., $0.00) or significantly higher values (e.g., $4.50).

4.  **[P1] No Findings of P1 Severity:** The code changes are consistent with the stated intent (RULING 108). The fail-closed behavior is maintained. The ledger path is updated. The test pins the new behavior.

### Conclusion

The diff correctly implements RULING 108. The budget limits are updated, the ledger path is changed to the new batch file, and the test is updated to reflect the new stop/limit values. The logic is fail-closed. The primary risk is the static assumption of the max build cost, but this is likely managed by the reservation logic mentioned in the comments.

P1_OR_WORSE: 0