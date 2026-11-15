# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 11187 / out 3019 usd_reported=0.002673 usd~0.079 (upper-bound price)

I will review the code in `tests/package/hook115.py` and `tests/package/test_hook115.py` against the provided laws and the specific "PLEASE CHECK" items.

### Analysis

**1. Context & Scope**
The feature is a "report before use" measurement driver for Ruling 115(3). It tests a new prompt version (`prompt_v2`) that includes positive and negative examples for hook rating.
- **Constraint:** "Nothing in pipeline/ changes; the hook job keeps ruling 115 (1)'s question; nothing here is read by a build."
- **Constraint:** "Report only: nothing here is read by a build".
- **Law Compliance:** Since this is a test/measurement script and not part of the production render pipeline (`run_fresh.py`), the strict "Governing Laws" regarding video rendering (Sentence Law, Snap Limit, etc.) do not directly apply to the *logic* of this Python script, but the script must not violate the *integrity* of the system (e.g., corrupting caches, bypassing spend limits, or altering production state).

**2. Review of `hook115.py`**

*   **Spend Limits (Check 5):**
    *   `LIMIT_USD = 0.55`, `STOP_USD = 0.25`.
    *   The order states: "Ruling 115's cap: $0.50 in all."
    *   The code sets `limit_usd=0.55` in `build_router`.
    *   **Finding:** The hard limit in the router is $0.55, which exceeds the stated cap of $0.50. While `STOP_USD` is $0.25 (which is well under $0.50), the `Router`'s `limit_usd` is the hard stop for the vendor API. If the spend logic in `providers.Router` allows up to `limit_usd` before throwing an error, this could potentially exceed the $0.50 cap if the `STOP_USD` check is bypassed or if the "reported" spend lags. However, the loop explicitly checks `if r.spent() >= STOP_USD: ... continue`. This prevents *new* calls after $0.25. The total spend will be bounded by the cost of the calls made before $0.25.
    *   Let's estimate cost: ~40 calls. Grok ~$0.005, Qwen ~$0.0003. Total ~$0.20. This is under $0.25. So `STOP_USD` is the effective governor.
    *   Is $0.55 a violation? The order says "cap: $0.50". Setting the router limit to $0.55 is technically higher than the cap. If a bug caused `STOP_USD` to be ignored, the router would allow up to $0.55. This is a safety margin issue.
    *   **Severity:** [P2] The router limit ($0.55) exceeds the stated ruling cap ($0.50). It should be set to $0.50 or lower to strictly enforce the cap at the infrastructure level, relying on `STOP_USD` for the operational stop.

*   **Cache Isolation (Check 2):**
    *   `rate()` uses `cache=None`.
    *   `PK.hook_ratings` is called with `cache=None`.
    *   The docstring says: "No cache: nothing is read or written."
    *   `build_router` uses `spend_path=SPEND` which is `tests/package/proof/SPEND_H115.json`. This is isolated from production spend logs.
    *   `mock.patch.object(PK, "HOOKS_PROMPT", prompt)` ensures the production prompt variable is restored.
    *   **Finding:** The isolation looks correct. `cache=None` prevents reading/writing `HOOK_CACHE.json`.

*   **Model Routing (Check 3):**
    *   `build_router` sets `r.chains["coherence_verdict:hook"] = [model]`.
    *   This forces the specific model (Grok or Qwen) to handle the request.
    *   `routing="heimdall_first"` is set, but the explicit chain override should take precedence for that specific task type.
    *   **Finding:** Correct. No failover to other models for the hook rating task.

*   **Prompt Construction (Check 1):**
    *   `prompt_v2` inserts a block after the first paragraph of `PK.HOOKS_PROMPT`.
    *   It escapes braces `{` and `}` in the block to prevent `.format` errors.
    *   It uses `PK.HOOK_QUESTION` implicitly by keeping the rest of the prompt intact.
    *   **Finding:** The logic `head + sep + block... + "\n" + rest` preserves the original structure. The escaping `block.replace("{", "{{").replace("}", "}}")` is crucial because `HOOKS_PROMPT` likely uses `.format()`. If the examples contain `{` or `}`, this prevents `KeyError`.
    *   **Potential Issue:** What if the *original* `HOOKS_PROMPT` has placeholders that are *not* meant to be filled by the examples? The code assumes `HOOKS_PROMPT` is a template. The test `test_the_block_sits_after_the_first_paragraph...` verifies that `filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS")`. This implies the structure is preserved.

*   **Verdict Logic (Check 4):**
    *   `verdict(rows)` checks:
        *   `len(a) == 5` and `len(n) == 5`.
        *   All approved `own` ratings `>= 4`.
        *   All negative `own` ratings `<= 3`.
    *   `own` is defined as `H.own_rating(r)`. The docstring says `own` is `min(scroll, alone)`.
    *   The order says: "rates all five approved at 4 or more AND all five negatives at 3 or less".
    *   **Finding:** The logic matches the order.

*   **Data Integrity (Negatives):**
    *   `negatives()` reads from `H.build_records` and `H.all_ratings`.
    *   It filters for `H.own_rating(x) == 2`.
    *   It raises `ValueError` if a negative is not found.
    *   **Finding:** Fail-closed behavior is correct.

**3. Review of `test_hook115.py`**

*   **Test Coverage:**
    *   `TestPrompt`: Verifies block placement, escaping, and leave-one-out logic.
    *   `TestRate`: Verifies `cache=None`, `seed=7`, prompt restoration, and verdict logic.
    *   `TestNegatives`: Verifies that the 5 negatives are correctly identified from the proof builds.
*   **Mocking:**
    *   `fake` function in `test_alone_no_cache...` mocks `PK.hook_ratings`.
    *   It asserts `seen == [(1, None, 7, "THE V2 PROMPT")]`. This confirms `cache=None` and `seed=7` are passed.
    *   It asserts `PK.HOOKS_PROMPT` is restored.
*   **Finding:** The tests are robust and cover the critical isolation and logic points.

**4. Specific Law Checks**

*   **LAW 20 / M2:** "Gate thresholds are constants... never change what a check accepts to make a render pass."
    *   This script is a *measurement* tool, not a gate. It does not modify production gates.
*   **M12 FAIL CLOSED:**
    *   `negatives()` raises `ValueError` if data is missing.
    *   `run()` raises `ValueError` if `len(pos) != 5`.
    *   This is fail-closed.
*   **Smallest Diff:**
    *   The diff adds two new files. It does not modify existing pipeline code. This adheres to the "Smallest diff" and "no new renderer... (M1)" constraints (it's a test script, not a renderer).

**5. Potential Pitfalls**

*   **`H.own_rating` Definition:** The code relies on `hook112.own_rating`. If `own_rating` is not `min(scroll, alone)`, the verdict logic might be wrong. The docstring in `hook115.py` says: "own-job rating (min(scroll, alone), ruling 61)". I must assume `hook112.own_rating` implements this. If it doesn't, the test `test_alone_no_cache...` mocks the return value, so it won't catch a mismatch in the *definition* of `own_rating` in `hook112.py`. However, the prompt says "hook112... UNCHANGED". So we trust `hook112.own_rating` is correct.
*   **`STOP_USD` vs `LIMIT_USD`:** As noted, `LIMIT_USD` is $0.55. The cap is $0.50. This is a minor discrepancy.
*   **`seed=7`:** The order says "at production's seed 7". The code uses `SEED = 7`. Correct.
*   **`report-only` flag:** `main` handles `--report-only`. If set, it skips `run()` and just calls `report()`. This is safe.

**6. Conclusion on Findings**

1.  **[P2] Spend Limit Mismatch:** `LIMIT_USD` is set to `0.55`, but the ruling cap is `$0.50`. While `STOP_USD` ($0.25) prevents most overspend, the hard limit in the router should not exceed the ruling cap.
2.  **[P3] Nit:** The `negatives` function uses `sorted(ra.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))`. The key `kv[0]` is a tuple `(m, rater)`. Sorting by `kv[0][0]` (moment id) and then `str(kv[0][1])` (rater) is fine, but `ra` is a dict of `{(moment_id, rater): rating}`. The iteration `for (m, rater), x in sorted(...)` unpacks the key. This is correct.
3.  **[P3] Nit:** In `test_hook115.py`, `POS` and `NEG` are hardcoded lists. The test `test_the_five_negatives_are_read_rated_2_with_their_text` calls `X.negatives()` which reads from the *actual* proof files. If the proof files are missing or corrupted, this test will fail. This is expected behavior for an integration-style test, but it makes the unit test dependent on external state (`tests/package/proof/...`). The docstring says "Offline: the rating call is a stub; the negatives are read from the proof builds (read only)." So this is by design.

**Refining the P2:**
Is $0.55 a "real defect that must be fixed before merge"?
The order says "Ruling 115's cap: $0.50 in all."
If the script runs and spends $0.52, it violates the ruling.
The `STOP_USD` is $0.25. The loop stops *before* making a call if `spent() >= 0.25`.
So the maximum spend is the sum of calls made while `spent() < 0.25`.
If each call is ~$0.005, you can make ~50 calls before hitting $0.25.
The script makes ~40 calls.
So the spend will be ~$0.20.
The `LIMIT_USD` of $0.55 is a safety net for the *vendor API* or the *router's internal accounting*. If the router's `spent()` is accurate, the $0.55 limit will never be hit.
However, if `spent()` is lagging or inaccurate, the router *could* allow up to $0.55.
Given the strictness of "Governing Laws" and "Fail Closed", setting the limit to the exact cap ($0.50) is the correct defensive programming practice. It ensures that even if the `STOP_USD` check fails, the hard limit enforces the ruling.
Therefore, [P2] is appropriate. It's not a P1 because the operational stop (`STOP_USD`) is well below the cap, making an actual violation unlikely in normal operation. But it's a defect in the configuration relative to the stated law.

**One more check:**
`build_router` uses `limit_basis="reported"`.
`r.spent()` returns the reported spend.
The check `if r.spent() >= STOP_USD` uses the same basis.
This is consistent.

**Final List:**
1.  [P2] `LIMIT_USD` (0.55) exceeds the ruling cap ($0.50). Should be 0.50.
2.  [P3] The test `test_the_five_negatives_are_read_rated_2_with_their_text` depends on external proof files. If these files are not present in the CI environment, the test will fail. This is noted in the docstring ("read from the proof builds"), but it's a fragility.

P1_OR_WORSE: 0