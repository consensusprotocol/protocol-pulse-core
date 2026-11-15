# qwen3.8-27b (qwen/qwen3.8-27b) 113 s finish=stop usage in 22600 / out 8042 usd_reported=0.006785 usd~0.188 (upper-bound price)

I will begin by analyzing the provided code against the governing laws and the specific instructions in the "PLEASE CHECK" section.

### Analysis of `tests/package/hook112.py`

**1. Read-Only Compliance (Law M12 / Instruction 5)**
The code claims to be read-only on build records, hook cache, and pp-ingest databases.
- `build_records`: Uses `json.load(open(...))`. Read-only.
- `hook_pass`: Connects to SQLite with `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`. This enforces read-only mode at the driver level.
- `calibrate`: Uses `router.spent()` and `rate(...)`. The `rate` function is `package.hook_ratings`. The instruction states `cache=None` is passed.
    - *Check*: Does `package.hook_ratings` write to disk if `cache=None`? The prompt says: "`_load_cache(None)` is `{}` ... and `_cache_put(None, ...)` returns at once ... so the production HOOK_CACHE.json is neither read nor written." This relies on the behavior of `package.py` (not provided, but described). Assuming the description is accurate, this is safe.
    - *Spend Ledger*: `build_router` creates a `Router` with `spend_path=SPEND` (`tests/package/proof/SPEND_H112.json`). This is a *new* file in the test/proof directory, not the production spend ledger. This is acceptable for a diagnostic tool that needs to track its own cost.
    - *Record Dir*: `record_dir=os.path.join(OUT, "replies")`. This writes model replies to `tests/package/proof/hook112/replies`. This is a write operation, but it is within the test/proof output directory, which is standard for capturing evidence. It does not modify source code or production data.

**2. Heimdall-Only Compliance (Instruction 4)**
- `heimdall_hook_chain`: Filters `router.chain("coherence_verdict", "hook")` to keep only backends where `vendor.split("/")[0] == "heimdall"`.
- `build_router`: Sets `r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)`.
- *Potential Issue*: Does `providers.Router` allow other chains to be used? The calibration only calls `rate(router, refs, ctx, wv, wf, cache=None, seed=s)`. `rate` is `package.hook_ratings`. If `hook_ratings` internally uses other chains (e.g., for fallback or different roles), it might bypass the Heimdall-only restriction. However, the prompt states: "The hook job as it stands today (package.hook_ratings ... unchanged) ... runs on Heimdall only: the hook chain of ruling 88 ... with every non-Heimdall back-end removed". This implies `hook_ratings` specifically uses the `coherence_verdict:hook` chain. If `hook_ratings` uses other chains (e.g., `angle_write`), those are not restricted by `heimdall_hook_chain`.
    - *Check*: `calibrate` passes `wv, wf` (writers' vendor/family) to `rate`. `package._writers(router)` is used to avoid the writers. This is a standard production pattern.
    - *Risk*: If `hook_ratings` falls back to a non-Heimdall model for *other* reasons (e.g., if the Heimdall model fails), does it respect the "Heimdall only" constraint? The code removes non-Heimdall backends from the *chain*. If the chain is empty, it raises `RuntimeError`. If the chain has only Heimdall backends, and one fails, does the router try the next in the chain (which is also Heimdall) or fall back to a default? `providers.Router` behavior is not fully visible, but typically it iterates the chain. Since the chain is filtered to Heimdall only, it should stay within Heimdall.

**3. Funnel Logic (Instruction 1 & 2)**
- `medley_trace`: Maps moments to stages 0-6.
    - Stage 0: `unusable`, `no_role`, `ad_read`, `reposted`.
    - Stage 1: `prescreen.failed`.
    - Stage 2: `prescreen.second_pass` != "PASS".
    - Stage 3: `prescreen.trim_cut` or `prescreen.hook_onset` != "PASS".
    - Stage 4: `prescreen.hook_onset` == "PASS" but `hook_pool.error` exists.
    - Stage 5: `hook_pool.ratings` exists but `own_rating` < 4.
    - Stage 6: `hook_pool.ratings` exists and `own_rating` >= 4.
    - *Logic Check*:
        - `elif mid in onset and onset[mid] != "PASS":` -> Stage 3.
        - `elif mid in onset and hp.get("error"):` -> Stage 4.
        - `elif mid in onset:` -> Stage 3 ("cannot open"). Wait, if `onset[mid]` is "PASS", it goes to the next `elif`.
        - The order of `elif`s matters.
            1. `mid in unusable`...
            2. `mid in failed`...
            3. `mid in ratings`... (Stage 5/6)
            4. `mid in second and second[mid] != "PASS"`... (Stage 2)
            5. `mid in trim_cut`... (Stage 3)
            6. `mid in onset and onset[mid] != "PASS"`... (Stage 3)
            7. `mid in onset and hp.get("error")`... (Stage 4)
            8. `mid in onset`... (Stage 3, "cannot open")
        - *Issue*: If a moment is in `ratings`, it is caught at step 3. It does not matter if it also failed `onset` or `second_pass`. This is correct because `ratings` implies it passed the previous gates.
        - *Issue*: If a moment is in `onset` and `onset[mid] == "PASS"`, but `hp.get("error")` is true, it goes to step 7 (Stage 4). If `hp.get("error")` is false, it goes to step 8 (Stage 3, "cannot open").
        - *Wait*: Step 8 says `out[mid] = (3, "cannot open ...")`. But if `onset[mid] == "PASS"`, it *can* open. Why is it Stage 3?
        - Let's re-read `STAGES`:
            `("in a pool", "passed the free screens", "cleared step A", "passed the second pass and CUTTABLE", "may open", "rated by the hook job", "rated >= 4")`
            Indices: 0, 1, 2, 3, 4, 5, 6.
        - `medley_trace` returns `(stage_index, reason, rating)`.
        - Step 8: `out[mid] = (3, "cannot open ...")`. Stage 3 is "passed the second pass and CUTTABLE".
        - If `onset[mid] == "PASS"`, it has passed G17a (onset). It should be at least Stage 4 ("may open").
        - However, if it is not in `ratings`, it means the hook job didn't rate it. Why?
        - The code says: `elif mid in onset and hp.get("error"):` -> Stage 4.
        - `elif mid in onset:` -> Stage 3.
        - This implies that if `onset` is PASS, but there is no `error` and no `rating`, it is stuck at Stage 3?
        - Let's look at `hook_pool`. `hp = pk.get("hook_pool") or {}`. `ratings = hp.get("ratings") or {}`.
        - If a moment is in `onset` (PASS) but not in `ratings`, and `hp` has no `error`, it falls to the last `elif`.
        - Is it possible for a moment to pass `onset` but not be rated, with no error?
        - In `package.build`, `hook_pool` is populated. If a moment is eligible, it is rated. If not eligible, it might be excluded.
        - The reason "cannot open (hook eligibility or the render's opener rule)" suggests it failed a check *after* onset but *before* rating.
        - But Stage 3 is "passed the second pass and CUTTABLE". Stage 4 is "may open".
        - If it passed `onset` (G17a), it "may open". So it should be Stage 4.
        - Assigning it to Stage 3 seems incorrect if it passed `onset`.
        - *Correction*: `onset` is `prescreen.hook_onset`. If `onset[mid] == "PASS"`, it passed G17a.
        - The next gate is the hook job itself.
        - If it didn't get a rating, and there's no error, maybe it was filtered out by `can_open`?
        - `can_open` is checked in `package.build` before `hook_pool`?
        - The prompt says: "`openers = {... if can_open(m)}` at :2643, hook_pool at :2666".
        - So `can_open` happens *before* `hook_pool`.
        - If `can_open` fails, the moment is not in `hook_pool.ratings`.
        - Does `can_open` failure correspond to a specific stage?
        - `STAGES[4]` is "may open".
        - If it fails `can_open`, it does *not* "may open". So it should be Stage 3 or lower?
        - But it passed `onset` (G17a).
        - Let's look at the stages again.
            0: in a pool
            1: passed free screens (unusable, no_role, ad, reposted)
            2: cleared step A (failed)
            3: passed second pass and CUTTABLE (second_pass, trim_cut, onset FAIL)
            4: may open (onset PASS, but not rated? or rated < 4?)
            5: rated by hook job
            6: rated >= 4
        - If `onset` is PASS, it is at least Stage 4 ("may open").
        - If it is not in `ratings`, it wasn't rated.
        - The code assigns Stage 3 to `mid in onset` (PASS) with no error and no rating.
        - This contradicts the stage definition. If it passed `onset`, it "may open" (Stage 4).
        - *Finding*: [P1] `medley_trace` assigns Stage 3 to moments that passed `onset` (G17a) but were not rated and had no error. According to `STAGES`, passing `onset` implies "may open" (Stage 4). If it wasn't rated, it stopped at "may open" (Stage 4) due to eligibility (`can_open`), not at "CUTTABLE" (Stage 3). The reason string "cannot open" is correct, but the stage index 3 is too low. It should be 4.

**4. Spotlight Trace (Instruction 1)**
- `spotlight_trace`:
    - `pool.out`: Stage 0.
    - `moments[*].stage`:
        - `st == 0`: `stepa` check. If `why` starts with "step A", Stage 1. Else Stage 0.
        - `st == 1`: Stage 2.
        - `st == 2`: Stage 3.
        - `st == 3`: Stage 4.
        - `st == 4`: Stage 5? No, `c = {0: ..., 1: ..., 2: ...}.get(st, (4, why, None))`.
        - If `st` is 3, 4, 5, it defaults to Stage 4.
        - But `hook_own` is checked first.
        - If `hook_own` is not None:
            - `own >= 4`: Stage 6.
            - `own < 4`: Stage 5.
        - This seems correct.
        - *Issue*: What if `st` is 3 (which maps to Stage 4 in the dict default) but `hook_own` is None?
        - The dict is `{0: ..., 1: ..., 2: ...}`.
        - If `st` is 3, `c` becomes `(4, why, None)`.
        - Stage 4 is "may open".
        - If `st` is 4, `c` becomes `(4, why, None)`.
        - If `st` is 5, `c` becomes `(4, why, None)`.
        - This lumps stages 3, 4, 5 of the spotlight into Stage 4 of the common scale.
        - Is this correct?
        - Spotlight stages:
            0: Free screens / Step A
            1: L-v 2 / CUTTABLE
            2: Cannot open cold (G17a)
            3: Hook's own job rates
            4: Visual check?
            5: ?
        - The prompt says: "spotlight.build :813 ... stage / out / hook_own".
        - If `hook_own` is present, it overrides.
        - If `hook_own` is absent, and `st` is 3, it means it reached the hook job but didn't get a rating? Or `hook_own` is only set if rated?
        - If `st` is 3 and `hook_own` is None, it likely failed the hook job or wasn't rated.
        - Mapping to Stage 4 ("may open") seems reasonable if it passed G17a (Stage 2 in spotlight -> Stage 3 in common? No, Spotlight Stage 2 is "cannot open cold", which is G17a. If it passes G17a, it is Spotlight Stage 3).
        - Common Stage 3 is "passed second pass and CUTTABLE".
        - Common Stage 4 is "may open".
        - If Spotlight Stage 2 (G17a) fails, it is Common Stage 3.
        - If Spotlight Stage 2 passes, it is Common Stage 4.
        - The code maps Spotlight `st=2` to Common Stage 3. Correct.
        - The code maps Spotlight `st=3` (default) to Common Stage 4. Correct.

**5. Near Misses (Instruction 3)**
- `near_misses`:
    - `own_rating`: `min(scroll, alone)`.
    - `held`: Counts parts that are 3.
    - `setup` is excluded from `held` count in the "held back by" logic?
    - `if r.get(p) == 3: held[p] += 1` for `p in ("scroll", "alone")`.
    - `if isinstance(r.get("setup"), int) and r["setup"] <= 3: held["setup ..."] += 1`.
    - This matches the instruction: "which part most often holds a 3 back from a 4 ... setup is shown apart".

**6. Calibration (Instruction 4)**
- `calibrate`:
    - `rate(router, refs, ctx, wv, wf, cache=None, seed=s)`.
    - `wv, wf = PK._writers(router)`.
    - `refs` have `moment_id` starting with `ref-`.
    - `router` is built with `heimdall_first` and filtered chain.
    - *Check*: `build_router` uses `P.Router(env_path=R.ENV, ...)`. `R.ENV` is from `replay85`. This might load a specific environment.
    - *Check*: `DT.load(DT.STATE, None)`.
    - *Check*: `r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)`.
    - This modifies the router's chain *after* construction.
    - Does `hook_ratings` use `router.chain("coherence_verdict", "hook")`?
    - If `hook_ratings` uses a different chain name, this filter won't apply.
    - The prompt says: "The hook job as it stands today (package.hook_ratings ... unchanged) ... runs on Heimdall only: the hook chain of ruling 88 ... with every non-Heimdall back-end removed".
    - This implies `hook_ratings` *does* use the `coherence_verdict:hook` chain.
    - *Risk*: If `hook_ratings` uses fallbacks or other chains, they are not filtered.
    - However, `heimdall_hook_chain` raises `RuntimeError` if no Heimdall backend is left.
    - If the chain is empty, it fails.
    - If the chain has Heimdall backends, it uses them.
    - *Finding*: [P2] The code only filters the `coherence_verdict:hook` chain. If `package.hook_ratings` uses other chains (e.g., for retry or different roles), those are not restricted to Heimdall. The instruction says "Heimdall only", which might imply *all* model calls in the calibration should be Heimdall. If `hook_ratings` calls other models, this is a violation.

**7. Tests (Instruction 6)**
- `test_hook112.py`:
    - `TestTheMedleyTrace`: Checks stage assignments.
    - `TestTheSpotlightTrace`: Checks stage assignments.
    - `TestTheRollUp`: Checks furthest stage.
    - `TestTheNearMisses`: Checks ranking.
    - `TestTheHookPass`: Checks DB read.
    - `TestTheLedgerIds`: Checks ID resolution.
    - `TestTheCalibration`: Checks router chain.
        - `test_the_drivers_router_asks_the_hook_job_on_heimdall_only`:
            - `r = H.build_router(...)`.
            - `chain = r.chain("coherence_verdict", "hook")`.
            - Asserts all are Heimdall.
            - Asserts `chain[0]` is `heimdall:qwen/qwen3.8-27b`.
        - `test_heimdall_only_and_refused_without_one`:
            - Uses `FakeRouter`.
        - `test_production_writers_no_cache_every_seed_and_the_stop`:
            - Mocks `rate`.
            - Checks `cache=None`.
            - Checks `stop_usd`.
    - *Missing Test*: There is no test for the `medley_trace` Stage 3 vs 4 issue found above.
    - *Missing Test*: There is no test ensuring that *other* chains in the router are not used by `hook_ratings` (if they are).

**8. Data Integrity**
- `ledger_of`: Resolves IDs.
- `hook_pass`: Reads `queue.sqlite` and `moment_ledger.jsonl`.
- `ref_moments`: Reads `PIN.json` files.
- All reads are safe.

**9. Specific Law Checks**
- **SENTENCE LAW**: Not directly tested here, as this is a diagnostic tool for hook scarcity, not a cut/render tool.
- **SELECTION LOCK**: Not applicable.
- **SNAP LIMIT**: Not applicable.
- **NEIGHBOUR**: Not applicable.
- **ONSET/TAIL**: `medley_trace` uses `hook_onset` (G17a). This is consistent.
- **CREDITS**: Not applicable.
- **L-a to L-l**: Not directly applicable to this diagnostic script, except for the "Heimdall only" constraint which is a routing rule.

**10. Code Quality**
- `reason_class`: Uses regex to classify reasons.
- `build_records`: Globs `ledger_*`.
- `funnel`: Aggregates.
- `hook_pass`: SQL query.
    - `SELECT e.at, e.ts, e.video_id, e.detail, c.display_name AS channel, v.title, v.moments FROM events e LEFT JOIN videos v ON v.video_id = e.video_id LEFT JOIN channels c ON c.channel_id = e.channel_id WHERE e.kind = 'hooks' AND e.ts >= ? ORDER BY e.ts`
    - This looks correct.
    - `db.row_factory = sqlite3.Row`.
    - `json.loads(r["detail"] or "{}")`.
    - `classes[cls] += 1`.
    - `per_channel[r["channel"] or "?"][cls] += 1`.
    - `mine.append(...)`.
    - `hook_rows`: Reads `moment_ledger.jsonl`.
    - `reached`: Intersects `hook_rows` with `rated_ids`.
    - `how_far`: Maps `hook_rows` to `furthest` or `never_in_pool`.

**11. Potential Bug in `medley_trace`**
- Line 148: `out[mid] = (3, "cannot open (hook eligibility or the render's opener rule)", None)`.
- As analyzed, if `onset[mid] == "PASS"`, the moment has passed G17a.
- `STAGES[3]` is "passed the second pass and CUTTABLE".
- `STAGES[4]` is "may open".
- Passing G17a means it "may open".
- If it is not in `ratings`, it was not rated.
- Why? `can_open` failed.
- `can_open` is a check for "may open".
- So it stopped at "may open".
- Therefore, it should be Stage 4.
- The code assigns Stage 3.
- This is a [P1] defect. It misclassifies the stage, which affects the funnel counts.

**12. Potential Bug in `spotlight_trace`**
- Line 174: `c = {0: (1 if stepa else 0, why, None), 1: (2, why, None), 2: (3, why, None)}.get(st, (4, why, None))`.
- If `st` is 3, 4, 5, it defaults to Stage 4.
- Spotlight Stage 3 is "the hook's own job rates".
- If `hook_own` is None, it wasn't rated.
- So it stopped at "may open" (Stage 4).
- This seems correct.

**13. `own_rating`**
- `min(scroll, alone)`.
- If `scroll` or `alone` is missing, `isinstance` check fails, returns `r.get("rating")`.
- This is consistent with "the recorded one when the parts are missing".

**14. `calibrate`**
- `rate(router, refs, ctx, wv, wf, cache=None, seed=s)`.
- `wv, wf` are writers' vendor/family.
- `refs` are the approved hooks.
- `ctx` is `E.Context(now, PS.REG)`.
- `PS.REG` is from `proof_saved_runs`.
- This looks correct.

**15. `build_router`**
- `P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD, limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))`.
- `r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)`.
- This overrides the chain.
- *Issue*: `heimdall_hook_chain(r)` calls `router.chain("coherence_verdict", "hook")`.
- If the router's initial chain is empty or doesn't have Heimdall, it raises `RuntimeError`.
- This is a fail-closed behavior. Good.

**16. `hook_pass`**
- `db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`.
- This is read-only.
- `ev = db.execute(...)`.
- `hook_rows`: Reads `ledger` file.
- `reached`: `set(ids) & set(rated_ids)`.
- `how_far`: `furthest.get(i) or {"stage": "never in a build's pool", "why": never_in_pool(i, inputs_report)}`.
- `never_in_pool`: Checks `inputs_report`.
- This looks correct.

**17. `ref_moments`**
- Reads `PIN.json`.
- `seg = json.load(open(path))["segments"][0]`.
- `out.append({"moment_id": f"ref-{key}", ...})`.
- This ensures unique IDs.

**18. `main`**
- `recs = build_records(PROOF, since)`.
- `fun = funnel(recs)`.
- `cache = json.load(open(os.path.join(PROOF, "HOOK_CACHE.json")))`.
- `rts = all_ratings(recs, cache)`.
- `nm = near_misses(rts, fold=snapped_map(recs))`.
- `today = sorted({m.get("video_id") for m in (recs[-1][2].get("moments") or [])} if recs else set())`.
- `lmap = ledger_of(recs)`.
- `rated_ids = {ledger_id(k[0], lmap) for k in rts}`.
- `by_ledger = {}`.
- `hp = hook_pass(QUEUE_DB, ..., today, LEDGER, rated_ids, by_ledger, ...)`.
- `cal = ...`.
- Writes JSON files.
- Writes REPORT.md.
- Prints summary.

**19. `all_ratings`**
- `texts`: Maps `moment_id` to `text`.
- `by_id`: Maps `moment_id` to list of `(rater, rec)` from cache.
- `out`: Maps `(mid, rater)` to rating record.
- Iterates `records`.
- `hook_pool.ratings`: Adds to `out`.
- `spotlight.moments`: Adds to `out` if `hook_own` is not None.
    - `for rater, rec in by_id.get(mid, []) or [(None, {})]:`
    - `k = (mid, rater)`.
    - `out.setdefault(k, ...)`.
    - `out[k]["builds"].append(name)`.
- This merges medley and spotlight ratings.
- *Issue*: If a moment is in both medley and spotlight, it might have multiple entries in `out` with different `rater` keys.
- `near_misses` iterates `ratings.values()`.
- `k = base(fold.get(r["moment_id"], r["moment_id"]))`.
- `key = (r["rating"], sum(...))`.
- `if k not in best or key > best[k][0]: best[k] = (key, r)`.
- This keeps the best rating per moment.
- This seems correct.

**20. `snapped_map`**
- Returns `{span_id: moment_id}`.
- Used in `near_misses` to fold spans into moments.

**21. `ledger_of`**
- Returns `{build_moment_id: ledger_id}`.
- `resolve`: Recursively resolves variants and spans.
- `depth < 4` prevents infinite loops.
- This seems correct.

**22. `funnel`**
- `per_build`: Counts stages per build.
- `best`: Furthest stage per distinct moment.
- `stops`: Reasons for never-rated.
- `distinct_by_stage`: Counts distinct moments at each stage.
- `furthest`: Details for each moment.
- This seems correct.

**23. `report`**
- Generates Markdown.
- Uses `fun`, `cal`, `nm`, `hp`.
- This seems correct.

### Findings

1.  **[P1] `medley_trace` Stage Assignment Error**: Moments that pass `onset` (G17a) but are not rated and have no error are assigned Stage 3 ("passed the second pass and CUTTABLE"). They should be assigned Stage 4 ("may open") because passing G17a means they "may open". The failure to be rated implies they failed `can_open` (eligibility), which is a check at the "may open" stage. This misclassification affects the funnel counts.
    *   *Location*: `hook112.py`, line 148.
    *   *Fix*: Change `out[mid] = (3, ...)` to `out[mid] = (4, ...)`.

2.  **[P2] Calibration Chain Restriction Scope**: The code only filters the `coherence_verdict:hook` chain to Heimdall backends. If `package.hook_ratings` uses other chains (e.g., for fallback, retry, or different roles), those are not restricted to Heimdall. The instruction "Heimdall only" might imply all model calls in the calibration should be Heimdall.
    *   *Location*: `hook112.py`, `build_router` and `heimdall_hook_chain`.
    *   *Fix*: Verify if `hook_ratings` uses other chains. If so, filter those as well or ensure `hook_ratings` is configured to use only the filtered chain.

3.  **[P3] Missing Test for Stage 3/4 Boundary**: The tests do not cover the specific case where a moment passes `onset` but is not rated and has no error. This is the case that triggers the P1 bug.
    *   *Location*: `test_hook112.py`.
    *   *Fix*: Add a test case for `medley_trace` with a moment in `onset` (PASS) but not in `ratings` and no `hook_pool.error`.

4.  **[P3] `reason_class` Regex Fragility**: The `reason_class` function uses regex to classify free-text reasons. If the reason text changes slightly, the classification might fail or be incorrect.
    *   *Location*: `hook112.py`, `reason_class`.
    *   *Fix*: Consider using structured data for reasons if possible, or make the regex more robust.

5.  **[P3] `hook_pass` SQL Injection Risk**: The `db_path` is used in a URI string. If `db_path` contains special characters, it might break the URI. However, `db_path` is a constant `QUEUE_DB` or passed from `main`, so it's low risk.
    *   *Location*: `hook112.py`, `hook_pass`.
    *   *Fix*: Use `sqlite3.connect` with `uri=True` and proper escaping if `db_path` is dynamic.

6.  **[P3] `calibrate` Spend Check**: The spend check `if router.spent() >= stop_usd:` is done before each seed. If the first seed exceeds the stop, the second seed is skipped. This is correct. However, if the first seed *approaches* the stop but doesn't exceed it, the second seed might exceed it. The code doesn't check *after* the call.
    *   *Location*: `hook112.py`, `calibrate`.
    *   *Fix*: Check spend after each call and stop if exceeded.

7.  **[P3] `ref_moments` File Access**: `json.load(open(path))` is used without context manager. This is a minor resource leak.
    *   *Location*: `hook112.py`, `ref_moments`.
    *   *Fix*: Use `with open(path) as f: json.load(f)`.

8.  **[P3] `build_records` File Access**: `json.load(open(...))` is used without context manager.
    *   *Location*: `hook112.py`, `build_records`.
    *   *Fix*: Use `with open(...) as f: json.load(f)`.

9.  **[P3] `all_ratings` Cache Access**: `json.load(open(os.path.join(PROOF, "HOOK_CACHE.json")))` is used in `main` without context manager.
    *   *Location*: `hook112.py`, `main`.
    *   *Fix*: Use `with open(...) as f: json.load(f)`.

10. **[P3] `hook_pass` Ledger Access**: `with open(ledger) as f:` is used correctly.

11. **[P3] `funnel` `best` Update**: `if k not in best or c[0] >= best[k][0]:`. This keeps the latest build's reason on a tie. This is correct per instruction.

12. **[P3] `near_misses` `held` Count**: `if r.get(p) == 3: held[p] += 1`. This counts parts that are exactly 3. If a part is 2, it is not counted. This is correct per instruction ("which part most often holds a 3 back from a 4").

13. **[P3] `spotlight_trace` `stepa` Check**: `stepa = st == 0 and (str(why).startswith("step A") or "no verdict (law L-m)" in str(why))`. This checks if the stop is due to Step A. If so, Stage 1. Else Stage 0. This is correct.

14. **[P3] `medley_trace` `went_on` Check**: `went_on = "second_pass" in pre`. This checks if the medley passed the 3-channel rule. If not, moments in `pool` but not in `failed` are assigned Stage 2 with reason "the medley ended at its 3-channel rule". This is correct.

15. **[P3] `medley_trace` `pool` Check**: `elif mid in pool:`. If a moment is in `pool` but not in any other category, it is assigned Stage 1 with reason `pk.get("why_none")`. This is correct.

16. **[P3] `hook_pass` `classes` Count**: `classes[cls] += 1`. `cls` is a string like "wrote rows, a model called". This is correct.

17. **[P3] `hook_pass` `per_channel` Count**: `per_channel[r["channel"] or "?"][cls] += 1`. This is correct.

18. **[P3] `hook_pass` `mine` List**: `mine.append(...)`. This collects events for the given videos. This is correct.

19. **[P3] `hook_pass` `hook_rows` Dict**: `hook_rows[row["video_id"]].append(row.get("moment_id"))`. This collects hook rows from the ledger. This is correct.

20. **[P3] `hook_pass` `reached` Dict**: `reached = {v: sorted(set(ids) & set(rated_ids)) for v, ids in hook_rows.items()}`. This finds which hook rows were rated. This is correct.

21. **[P3] `hook_pass` `how_far` Dict**: `how_far = {v: {i: (furthest or {}).get(i) or {"stage": "never in a build's pool", "why": never_in_pool(i, inputs_report)} for i in ids} for v, ids in hook_rows.items()}`. This finds how far each hook row got. This is correct.

### Conclusion

The code is generally well-structured and follows the instructions. The main issue is the Stage 3 vs 4 assignment in `medley_trace`. This is a [P1] defect because it misclassifies the funnel stage, which is the primary output of the diagnostic.

P1_OR_WORSE: 1