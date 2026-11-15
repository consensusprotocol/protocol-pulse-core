# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 7470 / out 3018 usd_reported=0.002499 usd~0.068 (upper-bound price)

**Audit Report: pp-selectid-20261115_1019 (C1_STEP.diff)**

**Context:** This diff addresses a variable name collision in `tests/package/proof_ledger.py` where `refused` (word pass IDs) was being overwritten by `start_refused()` (spend check result) before being passed to `spotlight.next_attempt`. The fix renames the variable to `wp_refused` and moves the `next_attempt` calculation earlier in the execution flow to ensure it uses the correct data.

### Findings

**1. [P3] Comment Clarity / Historical Context**
In `proof_ledger.py` (lines 11-13 of the diff), the comment explaining the rename is quite verbose and references specific build times ("build 6, 10:10 ET Nov 15"). While accurate for the audit trail, this level of detail in a code comment can become noise. However, given the "Governing Laws" emphasis on strict provenance and the fact that this is a test/proof ledger package, this is acceptable. No action required, but noted as a style nit.

**2. [P3] Exception Handling Scope**
The `try/except` block around `SPOT.next_attempt` (lines 20-23) catches `Exception`. The comment states "a report, never the build". This aligns with **M12 FAIL CLOSED** (missing data/exception rejects, never produces a pass) in the context of *reporting* metadata. Since `next_attempt` is purely informational (written to `inputs.json` and `res`), failing it should not block the build. The code correctly isolates this failure. No defect found.

**3. [P2] Potential Logic Shift in `next_attempt` Timing**
The diff moves the calculation of `next_try` from *after* the router/guard logic (line 38-41 in old code) to *before* `with_variants` and the `inputs.json` write (line 20-23 in new code).
*   **Old:** `next_attempt` was calculated late, potentially after some state changes in `rows` or `wp` if those objects were mutated in place by intermediate steps.
*   **New:** `next_attempt` is calculated immediately after `build_inputs`.
*   **Analysis:** The prompt asks to check if "nothing between the new computation and the build record could change what next_attempt reads".
    *   `rows`: Passed to `build_inputs`. If `build_inputs` mutates `rows` in place, the `next_attempt` call (which happens *after* `build_inputs` in the new code? No, wait. Let's look at the order).
    *   **Order in New Code:**
        1. `rows, rep = LB.rows(...)`
        2. `wp, wp_rep = LB.word_pass_index(...)`
        3. `wp_refused = ...`
        4. `inputs = LB.build_inputs(rows, ..., word_pass_refused=wp_refused)`
        5. `next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)`
        6. `moments = with_variants(...)`
    *   If `LB.build_inputs` mutates `rows` or `wp` in place, `SPOT.next_attempt` will see the mutated state. In the old code, `next_attempt` was called much later (line 39), so it would *also* see any mutations from `build_inputs` and `with_variants`.
    *   **Crucial Check:** Does `SPOT.next_attempt` depend on `moments` or `inputs`? The signature is `SPOT.next_attempt(rows, wp, now, refused=wp_refused)`. It does *not* take `inputs` or `moments`. It takes `rows` and `wp`.
    *   If `build_inputs` does not mutate `rows` or `wp`, the timing change is safe. If it *does* mutate them, the new code captures the state *after* `build_inputs` but *before* `with_variants`. The old code captured the state *after* `with_variants`.
    *   **Risk:** If `with_variants` mutates `rows` or `wp`, the new `next_attempt` value will differ from the old one. However, `next_attempt` is a "report" of when the *next* qualifying episode could arrive. It likely depends on the *input* rows, not the *processed* moments. Therefore, calculating it based on the raw `rows` (post-`build_inputs` if `build_inputs` cleans them, or pre-`build_inputs` if it doesn't) is likely more correct than calculating it after `with_variants` has potentially filtered or transformed the data.
    *   **Verdict:** This is likely an improvement in correctness (using input state for input-based reports), but it is a behavioral change. The test `test_ruling_95_counts_the_refused_from_the_inputs_alone` verifies the count logic. It does not explicitly verify that `rows`/`wp` are not mutated by `build_inputs` in a way that breaks `next_attempt`. Given `next_attempt` is a "report", this is low risk, but worth noting.

**4. [P1] Missing Verification of `rows`/`wp` Immutability**
The prompt asks: "(1) that nothing between the new computation and the build record could change what next_attempt reads".
The new computation is at line 21. The build record (`res`) is updated at line 42.
Between line 21 and 42, the code executes:
*   `moments = with_variants(...)` (Line 24)
*   `json.dump(...)` (Line 25-30)
*   `pool = ...` (Line 31)
*   `fp, fp_parts = fingerprint(...)` (Line 32)
*   `same = ...` (Line 33)
*   ... (Router logic, lines 34-41)

If `with_variants`, `fingerprint`, or the router logic mutates `rows` or `wp` in place, the `next_try` variable (already computed) is safe because it holds the *result* of the function call, not a reference to `rows`/`wp`. `SPOT.next_attempt` returns a dict (`next_try`). So, even if `rows` changes later, `next_try` is immutable (it's a dict of primitives/strings).
**Therefore, the value of `next_try` is fixed at line 21.** The question is whether the *inputs* to `next_attempt` at line 21 are the correct ones.
The inputs are `rows`, `wp`, `now`, `wp_refused`.
*   `rows`: From `LB.rows`.
*   `wp`: From `LB.word_pass_index`.
*   `wp_refused`: From `wp_rep`.
*   `now`: From `datetime.now` (presumably, though not shown in diff, likely defined earlier).

The old code called `next_attempt` with `refused` (which was `None` due to the bug). The new code calls it with `wp_refused` (the correct list).
The timing change (earlier vs later) only matters if `rows` or `wp` are mutated *between* the old call site and the new call site.
Old call site: After `with_variants` and router.
New call site: Before `with_variants`.
If `with_variants` mutates `rows`, the new code uses the *pre-mutation* rows. Is this correct?
`next_attempt` predicts the *next* episode. It should probably be based on the *current* ledger state (`rows`), not the *processed* moments. So using `rows` before `with_variants` is likely **more correct**.
**However**, if `LB.build_inputs` (line 15) mutates `rows`, then `next_attempt` (line 21) sees the mutated rows. In the old code, `next_attempt` (line 39) also saw the mutated rows (since `build_inputs` ran at line 15). So this part is consistent.
**Conclusion:** The change is safe regarding the *value* of `next_try` because it's a snapshot. The change in *timing* ensures it's calculated from the raw ledger rows, which is appropriate for a "next attempt" prediction. No P1 here, but it's a subtle logic shift.

**5. [P2] Test Coverage for `next_attempt` in `inputs.json`**
The new test `test_ruling_95_counts_the_refused_from_the_inputs_alone` checks `inputs.json` for `next_attempt`.
It asserts: `na["rows"] == 3`, `na["word_pass_ready"] == 0`, `na["word_pass_refused"] == 2`, `na["word_pass_waiting"] == 1`.
This verifies the *content* of the report.
It does *not* verify that `next_attempt` is present in `res` (the build record) when the build proceeds further. The diff shows `res["next_attempt"] = next_try` at line 42.
The test stops at "nothing new" (rc=0). It does not test the "router" path (rc="router") to ensure `next_attempt` is correctly propagated to `res` in that case.
**Recommendation:** Add a test case where `left > 0` (router path) and verify `res["next_attempt"]` matches the expected value.

**6. [P3] `default=str` in `json.dump`**
Line 26-30: `json.dump(..., default=str)`.
This is standard for handling non-serializable objects (like `datetime`). No issue.

**7. [P1] Name Collision Check**
The prompt asks: "(2) that no other name in main() collides (`wp_refused`, `next_try`)".
*   `wp_refused`: Defined at line 11. Used at line 18 (`build_inputs`) and line 21 (`next_attempt`).
*   `next_try`: Defined at line 21. Used at line 30 (`inputs.json`) and line 42 (`res`).
*   Are there other `wp_refused` or `next_try` in `main()`?
    *   The diff shows `refused` was the old name. It is now `wp_refused`.
    *   `start_refused` is a function call, not a variable assignment to `wp_refused`.
    *   No other `next_try` is visible in the diff.
    *   **Assumption:** The rest of `main()` (not shown) does not define `wp_refused` or `next_try`. Given the specific nature of the fix, this is likely true.
    *   **Risk:** If `next_try` is used elsewhere in `main()` (e.g., in a loop), this could be an issue. But `next_attempt` is a single report per build.
    *   **Verdict:** No collision found in the provided context.

**8. [P2] "A report, never the build" Behavior**
The prompt asks: "(3) that moving ruling 95 before the guard changes no build outcome and keeps the 'a report, never the build' behaviour".
*   **Build Outcome:** The build outcome is determined by `rc` (return code) and `res` (result dict).
    *   `rc` is determined by the router/guard logic (lines 34-41). `next_attempt` is not involved in `rc`.
    *   `res` includes `next_attempt`. This is metadata.
    *   Therefore, moving the calculation does not change the *decision* (pass/fail/hold) of the build.
*   **Report Behavior:** If `SPOT.next_attempt` raises an exception, `next_try` becomes `{"error": ...}`. This is written to `inputs.json` and `res`. The build continues. This preserves the "report, never build" behavior.
*   **Verdict:** Correct.

**9. [P3] Surviving Mutation**
The prompt asks: "(5) whether the surviving mutation matters".
The surviving mutation is: `res["next_attempt"] = {}` in the build record, past the router.
*   This means the test does *not* verify that `next_attempt` is correctly set in `res` when the build proceeds to the router.
*   It only verifies it in `inputs.json` (which is written before the router).
*   **Impact:** If `next_attempt` is missing or wrong in `res` (the final build record), downstream consumers of `res` might not see the "next attempt" info.
*   **Severity:** [P2] because `res` is the primary output of the build. `inputs.json` is an intermediate artifact. The final record should be complete.

### Summary of Findings

*   **[P1] None.** The fix correctly resolves the name collision and ensures `next_attempt` is calculated with the correct `refused` list. The timing change is logically sound for a report based on input rows.
*   **[P2] Test Gap:** The new test does not verify `next_attempt` in the final `res` dict for the "router" path (build proceeds). It only checks `inputs.json` for the "nothing new" path. The surviving mutation confirms this gap.
*   **[P3] Nit:** Comment verbosity.

### Final Answer

P1_OR_WORSE: 0