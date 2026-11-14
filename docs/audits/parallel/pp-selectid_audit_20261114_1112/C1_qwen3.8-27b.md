# qwen3.8-27b (qwen/qwen3.8-27b) 26 s finish=stop usage in 9743 / out 1821 usd~0.057 (upper-bound price)

I have reviewed the diff against the governing laws, the orchestrator's rulings, and the provided background facts. Here are the findings.

### Findings

**<high> Ruling (2) Implementation: `SNAP_MAX_S` Decoupling Risk**
*   **File:** `pipeline/ledger_build.py:9-11`
*   **Issue:** The change hardcodes `SNAP_MAX_S = 35.0` with a comment referencing `spotlight.SPOT_S[1]`. However, the code does not import or reference `spotlight.SPOT_S`. If `spotlight.SPOT_S` is ever changed (e.g., to 40s), `ledger_build.py` will silently retain the 35s ceiling, violating the intent of "the read's snap ceiling is the spotlight's".
*   **Verification:** The test `test_the_snap_ceiling_is_the_spotlights_and_the_medley_keeps_its_own_20_s` (line 134) asserts `LB.SNAP_MAX_S == SPOT.SPOT_S[1]`. This test will catch a drift, but the production code itself is fragile.
*   **Recommendation:** Import `spotlight` and set `SNAP_MAX_S = spotlight.SPOT_S[1]` to ensure single-source-of-truth.

**<medium> Ruling (3) Regex Edge Case: `without_manifest_date`**
*   **File:** `pipeline/vo_fidelity.py:50`
*   **Issue:** The regex for written dates is:
    `rf"\b{month}\s+0?{d.day}(?:st|nd|rd|th)?(?:,?\s+{d.year})?(?![\w.]?\d)"`
    The negative lookahead `(?![\w.]?\d)` is intended to prevent matching "November 12" inside "November 120". However, `\w` includes digits. If the text is "November 12.5" (a decimal), the lookahead `(?![\w.]?\d)` sees `.` (which matches `[\w.]?`) and then `5` (which matches `\d`), so it fails to match. This is correct.
    But consider "November 12, 2026". The regex allows `,?\s+{d.year}`. If the manifest date is `2026-11-12`, `d.year` is `2026`. The regex will match "November 12, 2026".
    What if the text is "November 12, 20261"? The lookahead `(?![\w.]?\d)` after the optional year group. If the year group matches `2026`, the next char is `1`. `[\w.]?` can match empty, then `\d` matches `1`. Lookahead fails. Correct.
    **Potential Bug:** The ISO date regex is `re.escape(d.isoformat())`. `d.isoformat()` is `2026-11-12`. The regex is `(?<![\w-])2026\-11\-12(?![\w-])`.
    If the text is "2026-11-120", the lookahead `(?![\w-])` sees `0`. `0` is `\w`. Lookahead fails. Correct.
    If the text is "12026-11-12", the lookbehind `(?<![\w-])` sees `2`. `2` is `\w`. Lookbehind fails. Correct.
    **However**, the test case `test_number_takes_the_manifests_own_show_date_whole_and_nothing_else` (line 105) includes `"Pulse Check for 2026-11-120."` as a `bad` case (expecting NUMBER violation). The regex correctly fails to match `2026-11-12` in `2026-11-120` because of the trailing `0`. So `fact_numbers` will see `2026-11-120` as a number. This is correct behavior.
    **Wait**, look at line 111: `self.assertEqual([x["detail"].split()[0] for x in v["violations"] if x["rule"] == "NUMBER"], ["120"])`.
    The input is `"We stopped at November 120."`. The manifest date is `2026-11-12`.
    The regex for written date: `\b(November|Nov)\s+0?12(?:st|nd|rd|th)?(?:,?\s+2026)?(?![\w.]?\d)`.
    In "November 120", it tries to match "November 12". The next char is `0`. The lookahead `(?![\w.]?\d)` checks if the next char is a digit. `0` is a digit. So the match fails.
    Therefore, "November 120" is NOT removed. `fact_numbers` sees "120". The violation detail is "120". This matches the test expectation.
    **Conclusion:** The regex logic appears sound for the provided tests.

**<medium> Ruling (3) `strict_features` Consistency**
*   **File:** `pipeline/vo_fidelity.py:81`
*   **Issue:** `strict_features` now uses `without_manifest_date`. The test (line 112-114) verifies that `strict_features` returns `[]` for the manifest date and `["a number"]` for a different date. This is consistent with the `NUMBER` rule.
*   **Verification:** The background states: "a 'production' claim must cite the manifest and carry no strict feature". If the VO line is "Pulse Check for 2026-11-12." and it is a production claim, `strict_features` returns `[]`, so it passes the "no strict feature" check. This is the intended behavior.

**<low> Test Coverage for `without_manifest_date`**
*   **File:** `tests/package/test_gates.py:93-114`
*   **Issue:** The tests cover ISO, written, ordinal, year, and negative cases. They do not explicitly test a missing manifest date (line 109 covers `{"show": "Pulse Check"}` which has no `date` key). The function handles this by returning the text unchanged (line 48). This is correct.

### SHIP: yes with conditions

**Conditions:**
1.  **Refactor `SNAP_MAX_S`:** Change `pipeline/ledger_build.py` to import `spotlight` and set `SNAP_MAX_S = spotlight.SPOT_S[1]` instead of hardcoding `35.0`. This ensures the "spotlight's ceiling" is truly dynamic and prevents drift if `SPOT_S` changes.
2.  **Verify `spotlight` Import:** Ensure `spotlight` is importable in `ledger_build.py` without circular dependencies. If `spotlight` imports `ledger_build`, this will fail. If so, consider moving `SPOT_S` to a shared constants module.

**Rationale:**
*   **Ruling (2):** The change correctly decouples the read ceiling (35s) from the medley usable ceiling (20s). The test `test_a_snap_of_21_to_35_s_is_read_and_one_longer_than_35_s_stays_out` confirms that 22.5s snaps are read, and `package.usable` (unchanged) will still drop them for the medley. This satisfies the ruling.
*   **Ruling (3):** The change correctly allows the manifest's own date to be stated without citation. The regex is robust against partial matches (e.g., "120", "2026-11-120"). The application to `NUMBER`, `NEEDS_SOURCE`, and `strict_features` is consistent.
*   **Laws:** No violations of SENTENCE LAW, SELECTION LOCK, etc., are introduced by this diff. The changes are confined to ledger building and VO fidelity checks.