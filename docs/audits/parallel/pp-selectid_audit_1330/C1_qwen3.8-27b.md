# qwen3.8-27b (qwen/qwen3.8-27b) 117 s finish=stop usage in 16179 / out 5682 usd~0.134 (upper-bound price)

**P0 Findings**

1.  **`pipeline/package.py`: `candidate_lineup` (approx. line 57 in diff context)**
    *   **Issue:** The function calls `lineup_for(..., clips=(len(ids) - 1, len(ids) - 1), ...)` to verify the candidate's clips still form a valid line-up. However, `lineup_for` is a *search* function that selects clips from the pool based on constraints. It does not verify that the *specific* clips in `candidate["lineup"]` are the ones selected, nor does it guarantee that the returned `segs` correspond to the exact `ids` provided in the candidate record.
    *   **Scenario:** If the pool has changed such that `lineup_for` selects a *different* set of clips (e.g., a different moment from the same channel, or a different duration) that satisfies the constraints, `candidate_lineup` returns `segs` that are **not** the candidate's original clips. The subsequent `build` call uses these `segs` (via `swapped = cand_segs`). The medley verdict is then calculated on the *new* clips, not the *recorded* candidate clips. This violates the core intent of Ruling 66 ("A PASSED LINE-UP IS KEPT... try ONLY that line-up... as it was judged"). The "seeds" logic relies on `n_lineup` and `ai` matching the recorded call, but if the underlying audio/video content (`segs`) differs, the "recorded verdict" served by the router (if bytes match) would be incorrect for the new content, or if bytes don't match, it pays for a new verdict on the wrong clips.
    *   **Fix:** `candidate_lineup` must verify that the `segs` returned by `lineup_for` (or a direct reconstruction) exactly match the `ids` in `candidate["lineup"]` in both identity and order. The current check `if segs is None or [m["moment_id"] for m in segs] != ids` is present in the diff (line 60), **BUT** `lineup_for` is called with `moments=ids` (line 57: `lineup_for(dict(candidate["angle"], moments=ids), ...)`). If `lineup_for` interprets `moments` as a *filter* or *pool* rather than a *fixed selection*, it might still reorder or drop clips if they don't fit the "stand-alone" or "seconds" rules in the *current* pool context. The diff shows `lineup_for` is passed `moments=ids`. If `lineup_for` respects this as a strict list of candidates to arrange, the check on line 60 is sufficient. However, if `lineup_for` performs a search that can *exclude* items from `ids` (e.g., if a clip is now too short or violates a new rule), it returns a subset or different set. The check `[m["moment_id"] for m in segs] != ids` catches this. **Wait**, looking closer at line 57: `lineup_for(dict(candidate["angle"], moments=ids), ...)`. If `lineup_for` uses `moments` as the *available pool*, and the candidate's `ids` are a subset of that pool, it might select a *different* subset if the original `ids` no longer satisfy the "best line-up" criteria (e.g., a different clip is now better). The check on line 60 ensures the *result* matches the *input* `ids`. If `lineup_for` returns a different set, it fails. If it returns the same set but in a different order, it fails. This seems correct *if* `lineup_for` is deterministic and respects the `moments` list as the only candidates. **However**, the risk is that `lineup_for` might *modify* the clips (e.g., trimming) based on current pool rules, changing the `moment_id` or duration, causing a mismatch with the recorded seeds/verdicts. The "seeds" are based on `ai` and `n_lineup`, not the clip content. If the clip content changes (e.g., a trim), the "recorded verdict" (which is keyed by prompt/bytes) will not match, forcing a new paid call. This is acceptable (fail-closed), but the *intent* of "using recorded verdicts" is lost if the clips are modified. The diff does not show `lineup_for` modifying clips, but `candidate_lineup` does not verify that the *durations* or *content* of `segs` match the recorded candidate's expectations. It only checks `moment_id`. If a clip's duration changed (e.g., due to a new trim rule), the medley prompt bytes would change, invalidating the cache. This is safe (pay for new call) but not "free". **More critically**: Does `lineup_for` guarantee it returns *exactly* the `ids` passed in `moments` if they form a valid line-up? If `lineup_for` is a search algorithm, it might find a *better* line-up using a subset of `ids` or a different combination. The check `!= ids` prevents this. So, if `lineup_for` returns `ids`, it's good. If it returns anything else, it's closed. This seems robust. **Re-evaluating P0**: The main risk is if `lineup_for` *fails* to return `ids` even though `ids` are valid, because it prefers a different valid line-up. The check `!= ids` would then close the candidate. This is correct behavior (the candidate is no longer the *best* line-up, or the rules changed). So, no P0 here.

2.  **`pipeline/package.py`: `build` function, candidate mode (approx. line 133-139 in diff context)**
    *   **Issue:** The loop `for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):` sets `ai` to `candidate["ai"]`. Inside the loop, `n_lineup` is initialized to `candidate["n_lineup"] - 1`. The guard `if candidate is not None and n_lineup >= candidate["n_lineup"]: break` is placed *after* the `swapped` check and *before* the `lineup_for` call? No, looking at the diff:
        ```python
        while total < lineups and not out["packages"] and not out.get("budget_stop"):
            if candidate is not None and n_lineup >= candidate["n_lineup"]:
                break                                 # RULING 66: the candidate alone, never re-lined or swapped
            if over_budget(ai):
                break
            if swapped is not None:                   # ruling 41: the swapped line-up is judged next
                # ... uses swapped
            else:
                # ... calls lineup_for
        ```
        The `swapped` variable is set to `cand_segs` (line 136: `n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs`).
        In the first iteration, `swapped` is not None. The code enters the `if swapped is not None:` branch. It judges the `swapped` line-up.
        After the judgment, does `n_lineup` increment? In the normal flow, `n_lineup` is incremented after a line-up is tried. The diff does not show the increment logic for `n_lineup` in the candidate branch explicitly, but it relies on the existing loop structure.
        If the existing code increments `n_lineup` after each attempt, then after the first attempt (the candidate), `n_lineup` becomes `candidate["n_lineup"]`. The guard `if candidate is not None and n_lineup >= candidate["n_lineup"]: break` will then trigger, exiting the loop. This prevents a second line-up.
        **However**, what if the candidate line-up *fails* the clips-alone verdict? The code at line 157-159:
        ```python
        if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
            rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
            break
        ```
        This `break` exits the `while` loop. This is correct.
        **What if the candidate line-up *passes*?** The code proceeds to writes. After writes, the loop continues. `n_lineup` is incremented. The guard breaks the loop. This is correct.
        **Potential P1:** The `swapped` variable is reused. In normal builds, `swapped` is set to a new line-up if the current one fails. In candidate mode, `swapped` is preset to `cand_segs`. If the candidate fails, we break. If it passes, we break after the next increment. This seems fine.

3.  **`pipeline/package.py`: `load_candidate` (approx. line 37 in diff context)**
    *   **Issue:** `n = sum(1 for u in tried[:index + 1] if u.get("angle") == t["angle"] and u.get("lineup"))`.
    *   This calculates the 1-based index of the line-up within its angle.
    *   In `build`, `n_lineup` is initialized to `candidate["n_lineup"] - 1` (0-based).
    *   The seed for medley is `7 + n_lineup + 10 * ai`.
    *   If `load_candidate` calculates `n` correctly, the seeds will match.
    *   **Scenario:** If `tried` contains entries with `lineup: None` (failed line-ups), they are excluded from the count. This matches the behavior of the `build` loop, which only increments `n_lineup` for line-ups that are actually *tried* (i.e., have a `lineup`).
    *   **Verification:** The test `test_the_line_up_number_counts_only_this_angles_line_ups` verifies this. It seems correct.

4.  **`pipeline/package.py`: `candidate_lineup` (approx. line 50 in diff context)**
    *   **Issue:** `if router.backends.get(candidate.get("angle_backend")) is None:`.
    *   If the backend is missing, it returns `None, why`. This is correct.
    *   **Issue:** `if not can_open(cleared[ids[0]]):`.
    *   `ids[0]` is the hook. `cleared` is a dict of `moment_id -> moment`.
    *   If `ids[0]` is not in `cleared`, `cleared[ids[0]]` raises `KeyError`.
    *   The code checks `gone = [mid for mid in ids if mid not in cleared]` *before* this. If `ids[0]` is gone, `gone` is not empty, and it returns `None, why`. So `cleared[ids[0]]` is safe.

5.  **`tests/package/proof_ledger.py`: `--from-candidate` parsing (approx. line 207 in diff context)**
    *   **Issue:** `cdir, sep, idx = a.from_candidate.rpartition(":")`.
    *   If `a.from_candidate` is `"BUILD_DIR"`, `rpartition(":")` returns `("", "", "BUILD_DIR")`. `sep` is empty. `idx` is `"BUILD_DIR"`.
    *   `cdir, idx = (cdir, idx) if sep and idx.isdigit() else (a.from_candidate, "")`.
    *   If `sep` is empty, `cdir` becomes `a.from_candidate` (the whole string), and `idx` becomes `""`.
    *   `int(idx) if idx else None` -> `None`.
    *   This correctly handles the case where no index is provided.
    *   If `a.from_candidate` is `"BUILD_DIR:2"`, `rpartition` returns `("BUILD_DIR", ":", "2")`. `sep` is `":"`, `idx` is `"2"`. `idx.isdigit()` is True. `cdir` is `"BUILD_DIR"`, `idx` is `"2"`. `int(idx)` is `2`.
    *   This seems correct.

**P1 Findings**

1.  **`pipeline/package.py`: `build` function, candidate mode (approx. line 111 in diff context)**
    *   **Issue:** `missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}] if candidate is None else []`.
    *   In candidate mode, `missing` is forced to `[]`. This prevents the "RULING 64" follow-up angle call. This is correct per the order ("no angle is asked for").

2.  **`pipeline/package.py`: `build` function, candidate mode (approx. line 117-118 in diff context)**
    *   **Issue:** `writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - {angle_reply.vendor}`.
    *   `angle_reply` is a `SimpleNamespace` created in candidate mode (line 100). It has a `vendor` attribute.
    *   `router.chain("angle_write")` returns the chain of backends for the `angle_write` role.
    *   This logic calculates which vendors to *avoid* for the *writer* (takeaway/title/caption). It avoids the vendor that wrote the angle.
    *   In candidate mode, the angle was *not* written in this build. It was recorded. The `angle_reply.vendor` is the vendor that *originally* wrote the angle.
    *   The order says: "the writers' vendor and family come from the recorded angle back-end (L-x)".
    *   L-x (Law of Writers) typically requires that the writer of the takeaway is *different* from the writer of the angle.
    *   If the candidate's angle was written by Vendor A, `angle_reply.vendor` is A. `writer_avoid` will include A. The writer for the takeaway will be chosen from the chain, avoiding A. This is correct.

3.  **`pipeline/package.py`: `build` function, candidate mode (approx. line 136 in diff context)**
    *   **Issue:** `n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs`.
    *   `cand_segs` is the result of `candidate_lineup`. It is a list of segments.
    *   In the `while` loop, `if swapped is not None:` uses `swapped` as the line-up to judge.
    *   The code then calls `medley(...)` with `swapped`.
    *   The seed for `medley` is `7 + n_lineup + 10 * ai`.
    *   `n_lineup` is `candidate["n_lineup"] - 1`. `ai` is `candidate["ai"]`.
    *   This matches the seed used in the original build.
    *   **However**, the `medley` function signature in the diff (line 262) is `def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):`.
    *   The call in `build` (not shown in diff, but implied) likely passes `seed`.
    *   The test `test_a_build_from_the_candidate_asks_no_angle_and_judges_it_with_its_own_seeds` verifies `rig.seeds` is `[("medley", 8), ("write", 108)]`.
    *   `ai=0`, `n_lineup=0` (1st line-up). Seed = `7 + 0 + 10*0 = 7`? No, the test says `8`.
    *   Wait, the test record has `tried[0]` with `angle: 1`. `ai = 1 - 1 = 0`.
    *   `n_lineup` calculation: `sum(1 for u in tried[:1] if u.get("angle") == 1 and u.get("lineup"))`. `tried[0]` has `lineup`. So `n = 1`.
    *   `candidate["n_lineup"]` is `1`.
    *   In `build`, `n_lineup` is initialized to `1 - 1 = 0`.
    *   Seed = `7 + 0 + 10 * 0 = 7`.
    *   But the test expects `8`.
    *   Let's check the test `test_the_line_up_number_counts_only_this_angles_line_ups`.
    *   `tried` has 4 entries. `tried[3]` is the passing one. `angle: 2`. `ai = 1`.
    *   `n_lineup` for `tried[3]`: `sum(1 for u in tried[:4] if u.get("angle") == 2 and u.get("lineup"))`.
    *   `tried[0]`: angle 1.
    *   `tried[1]`: angle 1, lineup None.
    *   `tried[2]`: angle 2, lineup `["x", "h", "y"]`.
    *   `tried[3]`: angle 2, lineup `["x", "h", "z"]`.
    *   Count for angle 2: `tried[2]` and `tried[3]`. So `n = 2`.
    *   `candidate["n_lineup"]` is `2`.
    *   In `build`, `n_lineup` is initialized to `2 - 1 = 1`.
    *   Seed = `7 + 1 + 10 * 1 = 18`.
    *   The test expects `rig.seeds` to be `[("medley", 7 + 2 + 10), ...]`? No, the test says `self.assertEqual(rig.seeds, [("medley", 7 + 2 + 10), ("write", 7 + 1 + 10 + 200)])`.
    *   `7 + 2 + 10 = 19`.
    *   My calculation: `ai = 1` (angle 2). `n_lineup = 1` (2nd line-up). Seed = `7 + 1 + 10*1 = 18`.
    *   Discrepancy: Test expects 19.
    *   Let's re-read the seed formula in the background: "medley(), seed 7 + n_lineup + 10 * ai".
    *   If `n_lineup` is 1-based in the formula?
    *   If `n_lineup` in the formula is the *count* (1-based), then for the 2nd line-up, `n_lineup=2`. Seed = `7 + 2 + 10*1 = 19`.
    *   In `load_candidate`, `n` is calculated as a 1-based count.
    *   In `build`, `n_lineup` is initialized to `candidate["n_lineup"] - 1` (0-based).
    *   If the `medley` call uses `n_lineup` (0-based) in the seed formula `7 + n_lineup + 10 * ai`, the seed would be 18.
    *   If the `medley` call uses `n_lineup + 1` (1-based) in the seed formula, the seed would be 19.
    *   The diff does not show the `medley` call site in `build`. It only shows the initialization of `n_lineup`.
    *   The test `test_a_build_from_the_candidate_asks_no_angle_and_judges_it_with_its_own_seeds` expects `("medley", 8)`.
    *   For `ai=0`, `n_lineup=0` (1st line-up).
    *   If formula is `7 + n_lineup + 10*ai` (0-based), seed = 7.
    *   If formula is `7 + (n_lineup+1) + 10*ai` (1-based), seed = 8.
    *   The test expects 8. So the seed formula in `build` must use the 1-based line-up number.
    *   Does `build` pass `n_lineup + 1` to `medley`? Or does `medley` add 1?
    *   The background says: "seed 7 + n_lineup + 10 * ai". It doesn't specify if `n_lineup` is 0 or 1 based.
    *   However, the test `test_the_line_up_number_counts_only_this_angles_line_ups` expects `("medley", 19)`.
    *   `ai=1`, `n_lineup` (1-based) = 2. `7 + 2 + 10 = 19`.
    *   So the seed formula uses the 1-based line-up number.
    *   In `build`, `n_lineup` is initialized to `candidate["n_lineup"] - 1` (0-based).
    *   If `build` passes `n_lineup` (0-based) to the seed calculation, it will be off by 1.
    *   **P1:** The `build` function must ensure that the seed passed to `medley` and `write_takeaway` uses the 1-based line-up number. If the existing code in `build` (not shown in diff) uses `n_lineup` (0-based) in the seed formula, the candidate mode will use the wrong seeds, causing cache misses and incorrect verdicts.
    *   **Verification:** The diff shows `n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs`. If the rest of the `build` loop (unchanged) uses `n_lineup` in the seed formula `7 + n_lineup + 10 * ai`, it will produce `7 + (n-1) + 10*ai`, which is 1 less than the recorded seed.
    *   **Impact:** The router will not find the recorded verdict (bytes/seed mismatch). It will pay for a new verdict. This is safe (fail-closed) but violates the "use recorded verdicts" requirement.
    *   **Fix:** Either `load_candidate` should return `n_lineup` as 0-based (and the seed formula in `build` is 0-based), or `build` should use `n_lineup + 1` in the seed formula. Given the tests expect 1-based seeds, `build` likely uses 1-based. The diff initializes `n_lineup` to 0-based. This is a mismatch.

**P2 Findings**

1.  **`pipeline/package.py`: `load_candidate` (approx. line 30 in diff context)**
    *   **Issue:** `if not 0 <= ai < len(angles) or angles[ai].get("angle") != t.get("text"):`.
    *   This checks if the angle text matches. It does not check if the `moments` or `hook` in `angles[ai]` match the candidate's expectations.
    *   The candidate's `angle` is constructed as `a = {k: angles[ai][k] for k in ("angle", "moments", "hook")}`.
    *   So `candidate["angle"]` *is* `angles[ai]`.
    *   The check `angles[ai].get("angle") != t.get("text")` ensures the text matches.
    *   This is sufficient.

2.  **`tests/package/proof_ledger.py`: `--from-candidate` (approx. line 209 in diff context)**
    *   **Issue:** `with open(os.path.join(cdir, "package.json")) as f:`.
    *   If `cdir` is a relative path, it is resolved relative to the current working directory.
    *   `source=os.path.relpath(os.path.abspath(cdir), REPO)`.
    *   This ensures the source is relative to the repo root.
    *   This is good for logging.

**SHIP: No**

**Reason:** P1 finding regarding seed calculation. The `build` function initializes `n_lineup` to `candidate["n_lineup"] - 1` (0-based), but the tests and background imply the seed formula uses the 1-based line-up number. If the unchanged `build` code uses `n_lineup` directly in the seed formula, the seeds will be incorrect, leading to cache misses and paid calls for verdicts that should be free. This violates the "use recorded verdicts" requirement of Ruling 66.

**Condition for Ship:** Verify that the `medley` and `write_takeaway` calls in `build` use `n_lineup + 1` (or equivalent 1-based logic) for the seed calculation. If they use `n_lineup` (0-based), the initialization in `candidate` mode must be `candidate["n_lineup"]` (not minus 1), or the seed formula must be adjusted.