# qwen3.8-27b (qwen/qwen3.8-27b) 48 s finish=stop usage in 20029 / out 3358 usd_reported=0.003326 usd~0.110 (upper-bound price)

I will begin by analyzing the provided code diff against the "Governing Laws" and the specific instructions for RULING 117.

### Analysis of `pipeline/package.py`

**1. `join_table` Function (Lines 73-138)**
*   **Law L-l (Model Reply Counts Only Whole):** The `parse` function (lines 118-125) strictly validates the JSON structure. It checks that the top-level key is `pairs`, that the set of keys matches the expected `want` (the pairs in the current chunk), and that each value is a dict with exactly `followable` (bool) and `why` (str). If any check fails, it raises `ValueError`. This is caught in the `except` block (line 130), which records an error and continues to the next chunk. This complies with L-l: an out-of-contract reply is treated as a failure, not a pass.
*   **Law M12 (Fail Closed):** If `router.chain` fails or returns an empty list, `listed` becomes `set()`. The cache lookup (line 101) requires `name in listed`. If `listed` is empty, no cached entries are used, and new calls are made. If the call fails, `err` is set. The function returns `out` (which may be partial) and `err`. The caller (`build`) handles `err` by logging it. If the table is empty or partial, the search logic handles missing pairs as "flagged" (see below). This is fail-closed.
*   **Caching:** The cache key is `text_sha(a['text']):text_sha(b['text']):JOINS_VERSION`. This ensures that if the text of a clip changes, the old cache entry is not used. The `JOINS_VERSION` is a hash of the prompt, ensuring that if the prompt changes, the cache is invalidated. This is robust.
*   **Concurrency:** The function uses `ThreadPoolExecutor`? No, it iterates sequentially over chunks. This is fine for correctness, though potentially slow. However, the prompt says "batched in one call where the contract allows". The code batches 25 pairs per call. This is acceptable.

**2. `search_lineups` Function (Lines 141-173)**
*   **Law L-m (One Bridge):** The function enforces `LY_MAX_BRIDGES`. The prompt states "at most one flagged join". The code checks `if nf > LY_MAX_BRIDGES`. I need to verify `LY_MAX_BRIDGES` is 1. The diff doesn't show the definition, but the test `test_the_search_every_order_the_rules_and_at_most_one_flagged_join` asserts that lineups with 2 flagged joins are not offered. The logic `flagged = lambda a, b: (a, b) in bad_pairs or (table.get((a, b)) or {}).get("followable") is not True` correctly identifies a join as flagged if:
    1.  It was flagged by a previous verdict (`bad_pairs`).
    2.  The table says it is *not* followable (`followable` is `False`).
    3.  The table has *no answer* for it (`table.get((a, b))` is `None`, so `.get("followable")` is `None`, which is `not True`).
    This complies with the instruction: "a join is flagged when the table finds it unfollowable, when the table has no answer for it, or when a verdict of this build flagged it".
*   **Search Space:** It iterates over permutations of `others` of length `n` where `n` is in `range(LY_CLIPS[0], LY_CLIPS[1] + 1)`. The prompt says "2-4 clips". Assuming `LY_CLIPS` is `(2, 4)`, this is correct.
*   **Constraints:** It checks `lineup_ok(segs, repeat_ok=repeat_ok)[0]`. This ensures the standard rules (channel, duration, etc.) are applied.
*   **Sorting:** It sorts by `(nf, -min(rs), -sum(rs) / len(rs), moves)`.
    *   `nf`: Fewest flagged joins (primary).
    *   `-min(rs)`: Highest minimum rating (secondary). The prompt says "highest clip ratings first". Using the minimum rating as the primary sort key for quality is a conservative approach (bottleneck).
    *   `-sum(rs) / len(rs)`: Highest mean rating (tertiary).
    *   `moves`: Fewest moves from writer's order (quaternary).
    This ordering seems reasonable and aligns with "Best first: the fewest flagged joins, then the highest clip ratings... then the writer's play order kept".

**3. `build` Function Integration (Lines 200-280)**
*   **Table Construction:** The table is built *before* the lineup selection loop. `jms` is constructed from `cleared` moments. `cleared` is defined in the prompt as "moments that passed step A... and CUTTABLE". The code uses `cleared[m]`. This matches.
*   **Fallback Logic:**
    *   If `jt` (join table) is empty or `search_lineups` returns nothing, it falls back to `lineup_for` (the old behavior).
    *   Code: `if swapped is None and segs is None: ... segs, exception = lineup_for(...)`.
    *   This complies with "With no table... or no line-up left in the search, the line-up is chosen as before".
*   **Verdict Handling:**
    *   After a verdict, if `not ok_m` (failed), it updates `a_ratings` and `dropped`.
    *   It then calls `search_lineups` again to find the next best lineup.
    *   If found, it sets `swapped` and `continue`s the loop.
    *   This complies with "after a failed verdict, the search's next line-up is asked".
*   **Agreement Reporting:**
    *   It records `join_table_vs_verdict` for each judged lineup.
    *   It aggregates into `out["join_agreement"]`.
    *   This complies with "Report how often the table's joins and the full verdict's joins agree".

### Analysis of `tests/package/test_medley.py`

*   **Test Coverage:**
    *   `test_the_question_is_the_clips_alone_verdicts_own`: Checks that `JOIN_QUESTION` is in `MEDLEY_PROMPT`. This ensures the join question is consistent with the main verdict.
    *   `test_once_per_ordered_pair_the_hook_never_second_batched_and_cached`: Verifies the pair generation logic (hook never B), batching (25 per call), and caching.
    *   `test_a_chunk_out_of_contract_has_no_entries_and_the_others_are_still_asked`: Verifies fail-closed behavior for bad chunks.
    *   `test_the_search_every_order_the_rules_and_at_most_one_flagged_join`: Verifies the search constraints (flagged joins, lineup_ok, short clips).
    *   `test_an_unanswered_pair_and_a_verdicts_flag_each_count_as_flagged`: Verifies that missing table entries are treated as flagged.
    *   `test_the_search_prefers_higher_known_ratings`: Verifies the sorting logic.
    *   `test_a_build_asks_the_searchs_line_up_first_and_records_the_agreement`: Verifies the integration in `build`.
    *   `test_after_a_failed_verdict_the_search_gives_the_next_line_up`: Verifies the retry logic.
    *   `test_the_cache_answers_only_for_todays_joins_list`: Verifies cache invalidation based on the provider list.
    *   `test_a_clip_under_the_verdicts_floor_leaves_the_search`: Verifies that clips failing the floor are dropped from future searches.
    *   `test_clips_under_a_verdicts_floor_never_come_back_when_the_search_runs_out`: Verifies that dropped clips are not re-introduced.
    *   `test_no_table_or_an_empty_one_is_the_build_as_before`: Verifies the fallback to old behavior.

### Potential Issues

1.  **`LY_MAX_BRIDGES` Value:** The code relies on `LY_MAX_BRIDGES` being 1. The prompt says "at most one flagged join". If `LY_MAX_BRIDGES` is defined elsewhere as something else, this would be a violation. However, the test `test_the_search_every_order_the_rules_and_at_most_one_flagged_join` explicitly checks that a lineup with 2 flagged joins is *not* in the results. This implies the test is verifying the behavior against the constant. If the constant were 2, the test would fail. Since the prompt says "All 40 suite files pass", I assume `LY_MAX_BRIDGES` is 1.
2.  **`lineup_ok` Signature:** The code calls `lineup_ok(segs, repeat_ok=repeat_ok)`. The prompt says "applies exactly lineup_for's rules (via lineup_ok)". I need to ensure `lineup_ok` is the correct function to validate a lineup. The prompt mentions `lineup_for` as the fallback. It is likely that `lineup_ok` is the validation function used by `lineup_for` or similar. The test `test_the_search_every_order_the_rules_and_at_most_one_flagged_join` calls `PK.lineup_ok([by[i] for i in s])[0]` and asserts it is `True` for valid lineups. This suggests `lineup_ok` returns a tuple `(bool, reason)`. The code uses `[0]` to get the bool. This is consistent.
3.  **`ratings` Dictionary:** In `search_lineups`, `ratings` is a dict mapping `moment_id` to a rating. The code uses `ratings.get(m["moment_id"], floor)`. If a clip has not been rated yet, it uses `floor`. This is consistent with "a clip not rated yet counts at `floor`".
4.  **`bad_pairs` Update:** In `build`, `bad_pairs` is updated with pairs flagged by the verdict. The code: `bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"]) for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}`. This correctly adds the flagged pairs to the set of "bad" pairs, which are then treated as flagged in subsequent searches.
5.  **`dropped` Update:** In `build`, if a clip's rating is below the floor, it is added to `dropped`. The code: `if x < floor_: dropped.add(mm["moment_id"])`. This ensures that clips that fail the floor are not considered in future searches. This is consistent with "a clip under THAT verdict's floor leaves the angle (dropped)".
6.  **`join_table` Error Handling:** If `join_table` returns an error, `jt` might be empty or partial. The code logs the error. If `jt` is empty, `search_lineups` will treat all pairs as "unanswered" (flagged). If all pairs are flagged, `nf` will be high, and `search_lineups` might return no candidates if `nf > LY_MAX_BRIDGES`. In that case, it falls back to `lineup_for`. This is fail-closed.
7.  **`search_lineups` Empty Result:** If `search_lineups` returns an empty list, `found` is `[]`, `segs` is `None`. The code then falls back to `lineup_for`. This is correct.
8.  **`build` Loop Condition:** The loop continues while `total < lineups` and `not out["packages"]`. If the search runs out of candidates, `swapped` remains `None` (or is set to a candidate that fails, leading to `break` or `continue`?).
    *   If `search_lineups` returns `[]`, `found` is `[]`, `segs` is `None`.
    *   The code: `if swapped is None and segs is None: ... segs, exception = lineup_for(...)`.
    *   If `lineup_for` also returns `None`, then `segs` is `None`.
    *   The code then checks `if segs is None: ... break`? No, the diff doesn't show the `break` for `segs is None` in the fallback path.
    *   Let's look at the original code structure. The `while` loop has a `break` condition.
    *   In the diff, after the fallback `lineup_for`, if `segs` is `None`, what happens?
    *   The diff shows:
        ```python
        if swapped is None and segs is None:      # no table, or the search has nothing: as before
            segs, exception = lineup_for(...)
            if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
                # ... (code not shown in diff, but likely handles the None case)
        ```
    *   Actually, the diff cuts off. But the prompt says "With no table... or no line-up left in the search, the line-up is chosen as before". This implies the existing logic for handling `None` from `lineup_for` is preserved.
    *   The test `test_clips_under_a_verdicts_floor_never_come_back_when_the_search_runs_out` verifies that if the search runs out, no third verdict is asked. This implies the loop terminates or moves to the next angle.

### Conclusion

The code appears to correctly implement RULING 117.
1.  **Join Law:** Enforced via `LY_MAX_BRIDGES` and `flagged` logic.
2.  **Verdicts Decide:** The search only picks candidates; the verdicts (`medley`, `coherence`) still run and can fail.
3.  **Search Rules:** `lineup_ok` is used. Unanswered pairs are flagged.
4.  **Fallbacks:** If search fails or table is empty, `lineup_for` is used.
5.  **Cache:** Correctly keyed and invalidated.
6.  **Tests:** Comprehensive and passing.

I do not see any P0 or P1 issues.

One minor point: The `join_table` function uses `router.chain("coherence_verdict", "joins")`. If this chain is empty, `listed` is `set()`. The cache lookup requires `name in listed`. If `listed` is empty, no cache hits. The call `P.call_parsed` will use the default chain for `coherence_verdict`? No, `call_parsed` takes `kind="joins"`. It likely uses the chain for that kind. If the chain is empty, it might fail. The code catches `ProviderError`. This is fail-closed.

Another point: `search_lineups` uses `itertools.permutations`. For 8 moments, the number of permutations of 2-4 clips is manageable.

The code is well-structured and compliant.

P1_OR_WORSE: 0