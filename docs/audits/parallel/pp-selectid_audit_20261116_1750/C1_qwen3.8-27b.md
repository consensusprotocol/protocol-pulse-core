# qwen3.8-27b (qwen/qwen3.8-27b) 64 s finish=stop usage in 10218 / out 5157 usd_reported=0.004152 usd~0.108 (upper-bound price)

I will analyze the provided diff for `tests/package/proof_ledger.py` and `tests/package/test_ledger_build.py` against the "Governing Laws" and the specific "PLEASE CHECK" instructions.

### Analysis of `--only` Implementation

1.  **Logic Verification**:
    *   `read_only` parses the JSON file. It validates that `ids` is a list of non-empty strings and `why` is a non-empty string. It deduplicates `ids` using `dict.fromkeys`.
    *   `only_moments` filters the `moments` list. It iterates through the original `moments` list and keeps those whose `moment_id` is in the `want` set. This preserves the original pool order. It correctly identifies `missing` ids.
    *   In `main`, `only_moments` is called *before* `with_variants`. This means the pool is reduced before any variant generation or downstream processing.
    *   **Check (1): Can `--only` add a moment or skip a gate?**
        *   It cannot add a moment because it only filters the existing `moments` list.
        *   It does not skip gates. The code comment states: "Every stage and gate of the build is unchanged: it simply sees a smaller pool". The filtering happens on the input data (`moments`), not on the control flow of the gates. The gates (eligibility, step A, etc.) will run on the reduced set. This complies with the intent of "spend the fresh dollar on ONE line-up at a time".

2.  **Error Handling**:
    *   If the file is missing or invalid, `read_only` raises `ValueError`.
    *   In `main`, `read_only` is called inside a block that likely handles exceptions or is wrapped in a try/except that leads to `exit 2`. The test `test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written` verifies that `PLG.main` returns `2` for bad inputs and that no `ledger_` directories are created. This confirms fail-closed behavior (M12).

### Analysis of `--stop-usd` Implementation

1.  **Logic Verification**:
    *   `STOP_CEILING_USD` is set to `1.25`.
    *   In `main`, `a.stop_usd` is validated: `if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD: raise ValueError`. This enforces the range $(0, 1.25]$.
    *   `limit` and `stop` variables are determined:
        *   If `a.stop_usd` is provided, `limit = a.stop_usd` and `stop = a.stop_usd`.
        *   Otherwise, `limit = PL.LY_LIMIT_USD` and `stop = PL.LY_STOP_USD`.
    *   `build_router` is called with `limit=limit`.
    *   `start_refused` is called with `stop=stop`.
    *   **Check (2): The stop's ceiling and its wiring.**
        *   The ceiling is enforced in `main` before any state is written.
        *   The wiring passes the custom limit to the `Router` (which controls spend reservation) and the custom stop to `start_refused` (which prevents the build from starting if current spend >= stop).
        *   The `spend_ruling_48` record includes `cap: limit` and `stop: stop`, and conditionally `order_17_50_stop: a.stop_usd`. This ensures the audit trail reflects the specific constraints of this run.

2.  **Potential Issue**:
    *   The `Router` is initialized with `limit_usd=limit`. The `start_refused` check uses `stop`.
    *   If `--stop-usd` is provided, both `limit` and `stop` are set to the same value.
    *   Is it possible for `limit` and `stop` to diverge? The order says "Stop outside calls at $0.80... day cap of $1.25".
    *   The implementation sets `limit` (router cap) and `stop` (start refusal threshold) to the *same* value provided by `--stop-usd`.
    *   Let's re-read the order: "Stop outside calls at $0.80 unless a package is one call from its seal." and "ADD 25 CENTS: then start at once with the same plan and a day cap of $1.25."
    *   The `--stop-usd` argument description says: "this build's outside-dollar limit (no build starts at it; the router stops outside calls at it)".
    *   So, `--stop-usd` serves as *both* the start-refusal threshold and the router's spend limit. This matches the implementation.
    *   However, the order mentions a specific "day cap of $1.25" if "ADD 25 CENTS" is received. The `STOP_CEILING_USD` is 1.25. The user can pass `--stop-usd 1.25`.
    *   The default behavior (no `--stop-usd`) uses `PL.LY_LIMIT_USD` and `PL.LY_STOP_USD`.
    *   The logic seems sound for the specific "ORDER 17:50" context where a single parameter controls the budget for this specific run.

### Analysis of Tests

1.  **`test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written`**:
    *   Tests invalid `--only` files (empty ids, no why, not list, blank id, missing file).
    *   Tests invalid `--stop-usd` values (0, -1, 1.26, 2).
    *   Asserts exit code 2.
    *   Asserts no `ledger_` directories are created (fail-closed).
    *   This is a strong test for M12 (Fail Closed).

2.  **`test_only_keeps_the_named_moments_in_the_pools_order_and_names_the_missing`**:
    *   Tests `read_only` deduplication and validation.
    *   Tests `only_moments` filtering logic:
        *   Input moments: `a, b, c`.
        *   Only ids: `c, a, gone, a` (deduped to `c, a, gone`).
        *   Expected kept: `a, c` (in pool order).
        *   Expected missing: `gone`.
    *   This verifies the "pool order" requirement and "missing" reporting.

3.  **`test_the_stop_holds_the_start_and_the_router`**:
    *   Tests `start_refused` with custom stop.
    *   Tests `build_router` with custom limit.
    *   Verifies that the custom values are passed through correctly.

### Governing Laws Compliance Check

*   **M12 FAIL CLOSED**: The code raises `ValueError` for bad inputs, which is caught and results in exit 2 without writing state. Tests confirm this.
*   **LAW 20 / M2**: Thresholds are constants (`STOP_CEILING_USD`). The code does not change gate logic, only input data.
*   **Smallest diff**: The changes are localized to `proof_ledger.py` and its tests. No new modules.
*   **No new renderer/compositor/selector**: Correct, this is a driver/test package change.

### Potential Findings

1.  **[P2] Ambiguity in `--stop-usd` vs `--only` interaction**:
    *   The order says "spend the fresh dollar on ONE line-up at a time... Stop outside calls at $0.80".
    *   If `--only` is used, the pool is small. If `--stop-usd` is used, the budget is capped.
    *   The implementation allows both. This seems correct.
    *   However, `read_only` is called *before* `start_refused`. If `--only` is invalid, it exits 2. If `--stop-usd` is invalid, it exits 2.
    *   The order of validation: `--only` is read in the "refusal block" (lines 80-82 in diff context, actually lines 80-82 of the new code block). `--stop-usd` is validated in the same block.
    *   Wait, looking at the diff:
        ```python
        only = read_only(a.only) if a.only else None     # ORDER 17:50 ET Nov 16: read before anything is written
        if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD:
            raise ValueError(f"--stop-usd {a.stop_usd} is outside (0, {STOP_CEILING_USD}]")
        ```
    *   Both are validated early. This is good.

2.  **[P3] `read_only` deduplication order**:
    *   `list(dict.fromkeys(ids))` preserves the order of *first occurrence*.
    *   The test `test_only_keeps_the_named_moments_in_the_pools_order_and_names_the_missing` uses `["c", "a", "gone", "a"]`.
    *   `dict.fromkeys` -> `{'c': None, 'a': None, 'gone': None}`.
    *   `list` -> `['c', 'a', 'gone']`.
    *   `only_moments` filters `moments` (`a, b, c`) by `want` (`c, a, gone`).
    *   Result: `a, c`.
    *   The "asked" count is `len(only["ids"])` which is 3 (after dedup).
    *   The "missing" list is `[x for x in only["ids"] if x not in have]`. `have` is `{a, c}`. `only["ids"]` is `['c', 'a', 'gone']`. `gone` is missing.
    *   This logic is consistent.

3.  **[P1] Missing Check: Does `--only` respect the "Selection Lock" or "Sentence Law"?**
    *   The laws apply to the *content* of the clips (transcripts, cuts).
    *   `--only` filters *which moments* (videos/clips) are considered.
    *   The laws state: "No later stage may recompute expected first/last words from a moved cut."
    *   Filtering the pool does not move cuts or recompute words. It just excludes some candidates.
    *   Therefore, it does not violate Selection Lock or Sentence Law.

4.  **[P2] `start_refused` logic with `stop`**:
    *   `start_refused(spent0, stop)`:
        *   `stop = PL.LY_STOP_USD if stop is None else stop`
        *   `if spent0 >= stop: return refusal`
    *   If `--stop-usd 0.80` is passed, `stop` is 0.80.
    *   If `spent0` is 0.80, it refuses.
    *   If `spent0` is 0.79, it allows.
    *   This matches "no build starts at or over the stop".

5.  **[P3] Test Coverage for `--only` + `--stop-usd` combined**:
    *   The tests check them separately.
    *   `test_a_bad_only_file_or_stop_refuses...` checks bad `--only` and bad `--stop-usd` separately.
    *   There is no test for *valid* `--only` and *valid* `--stop-usd` together in a full run, but the unit tests for the components (`read_only`, `only_moments`, `start_refused`, `build_router`) cover the logic.
    *   Given the "smallest diff" and "no full driver run" constraint mentioned in the prompt ("the two pieces of main()'s wiring... are not reachable without a full driver run"), this is acceptable.

6.  **[P1] Potential Issue: `limit` vs `stop` in `build_router`**:
    *   `build_router` takes `limit`.
    *   `start_refused` takes `stop`.
    *   In `main`:
        ```python
        limit = PL.LY_LIMIT_USD if a.stop_usd is None else a.stop_usd
        stop = PL.LY_STOP_USD if a.stop_usd is None else a.stop_usd
        router = build_router(..., limit=limit)
        ...
        refused = start_refused(spent0, stop)
        ```
    *   If `--stop-usd` is provided, `limit == stop`.
    *   The `Router` uses `limit_usd` to stop *outside calls* (spend reservation).
    *   `start_refused` uses `stop` to prevent the *build from starting*.
    *   This is consistent with the order: "Stop outside calls at $0.80... no build starts at it".

7.  **[P2] `read_only` file path security**:
    *   `open(path)` is used.
    *   The path comes from `a.only` (CLI argument).
    *   Is there a risk of path traversal?
    *   The function is in `tests/package/proof_ledger.py`.
    *   The prompt says "GPU0 only; no publishing".
    *   The `--only` file is a local JSON file provided by the operator.
    *   Standard `open` is fine for a local tool. No sandboxing required by the laws.

8.  **[P3] `only_moments` return type**:
    *   Returns `(kept, record)`.
    *   `record` is a dict.
    *   `inputs["only"] = record`.
    *   This is stored in the build record.
    *   The log line uses `inputs['only']['kept']`, `inputs['only']['asked']`, `inputs['only']['missing']`.
    *   This is consistent.

### Conclusion

The code implements the "ORDER 17:50" requirements correctly:
1.  `--only` filters the moment pool, preserving order, and fails closed on invalid input.
2.  `--stop-usd` caps the router limit and start-refusal threshold, failing closed on out-of-range input.
3.  Tests cover the validation, filtering logic, and wiring.
4.  No governing laws are violated. The changes are minimal and focused.

One minor observation:
In `test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written`, the test uses `mock.patch("sys.stderr", new=io.StringIO())`. This suppresses error output. This is good for test stability.

The `read_only` function raises `ValueError`. The `main` function likely catches this (or the `argparse`/wrapper does) to return exit code 2. The test asserts `PLG.main(...) == 2`. This implies `main` handles the exception. The diff doesn't show the `try/except` in `main` for `read_only`, but it shows `read_only` being called. If `read_only` raises, and `main` doesn't catch it, the exit code would be 1 (unhandled exception) or the traceback would be printed.
However, the test *passes* (implied by the request to audit, and the structure of the test asserting exit 2).
Let's look at the diff again.
Lines 80-82:
```python
only = read_only(a.only) if a.only else None     # ORDER 17:50 ET Nov 16: read before anything is written
if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD:
    raise ValueError(f"--stop-usd {a.stop_usd} is outside (0, {STOP_CEILING_USD}]")
```
If `read_only` raises `ValueError`, and `main` does *not* catch it, the process crashes with a traceback.
The test asserts `PLG.main(...) == 2`.
This implies `main` *must* catch `ValueError` from `read_only` and return 2.
The diff does *not* show the `try/except` block in `main` that wraps `read_only`.
It shows `read_only` being called.
It shows `start_refused` being called later.
If the `try/except` is not present in the diff, it might be in the existing code (not shown) or it might be missing.
Given that `test_ledger_build.py` is modified to include these tests, and the tests assert exit 2, it is highly likely that the `main` function *already* has a broad `try/except` for `ValueError` or `Exception` that returns 2, OR the diff is incomplete regarding the error handling in `main`.
However, looking at line 76-78 in the diff:
```python
if since > now:
    raise ValueError(f"since {since.isoformat()} is after now")
```
This `ValueError` is raised in `main`. If `main` didn't catch it, the test for `--since` would also fail to return 2.
Assuming the existing `main` structure handles `ValueError` by returning 2 (a common pattern in such CLI tools), the new `ValueError`s from `read_only` and `--stop-usd` validation will be handled similarly.
Therefore, no P1 finding for missing exception handling, assuming the existing pattern holds.

Wait, looking at the test `test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written`:
```python
self.assertEqual(PLG.main(["--delivered", *self.pins(), "--only", os.path.join(d, name)]), 2, name)
```
If `main` didn't catch the error, this test would fail. Since this is a "Pre-merge quality gate" and the code is presented as "The Code", I must assume the code *works* as tested. The audit is to find *defects*. If the exception handling is missing, the tests would fail. If the tests pass, the handling is there.
The prompt asks me to audit the *provided* code. The provided code *includes* the tests. It does *not* include the full `main` function body, only the diff.
The diff shows the *addition* of the `read_only` call and the `--stop-usd` check.
It does *not* show the `try/except` block.
If the `try/except` block is *not* in the diff, it means it was *already there* or is *missing*.
If it was already there, it likely catches `ValueError`.
If it is missing, the code is broken.
However, `start_refused` returns a string, it doesn't raise.
The `--stop-usd` check *raises* `ValueError`.
The `read_only` check *raises* `ValueError`.
If `main` does not catch these, the exit code is not 2.
Given the test asserts 2, and the test is part of the "Code" package, I will assume the `main` function *does* catch these errors.
Is there a risk that the *new* errors are not caught by an *old* try/except?
If the old try/except was specific to certain arguments, it might not cover `--only` or `--stop-usd`.
But `ValueError` is a standard exception. A broad `except ValueError` would cover it.
I will flag this as a [P2] "Verify Exception Handling" because the diff doesn't show the catch block, but the tests imply it exists. If it doesn't, it's a P0. But usually, in these audits, if the test is provided and asserts a specific exit code, the implementation is expected to support it.

Let's look for other issues.
`STOP_CEILING_USD = 1.25`.
`--stop-usd` range: `(0, 1.25]`.
Order: "day cap of $1.25".
This matches.

`read_only` deduplication:
`list(dict.fromkeys(ids))`.
If `ids` is `["a", "a", "b"]`, result is `["a", "b"]`.
`only_moments` uses `want = set(only["ids"])`.
`kept = [m for m in moments if m["moment_id"] in want]`.
This is correct.

One subtle point:
`inputs["only"]` is set to `record`.
`record` contains `missing`.
The log line:
```python
say(f"  ORDER 17:50: --only: {inputs['only']['kept']} of {inputs['only']['asked']} listed moments in this pool "
    f"({only['why']})" + (f"; not in it: {inputs['only']['missing']}" if inputs['only']['missing'] else ""))
```
`only` is the dict returned by `read_only`.
`inputs['only']` is the `record` returned by `only_moments`.
`only['why']` is valid.
`inputs['only']['missing']` is valid.
This looks correct.

Final check on "Governing Laws":
- **SENTENCE LAW**: Not affected.
- **SELECTION LOCK**: Not affected.
- **SNAP LIMIT**: Not affected.
- **NEIGHBOUR**: Not affected.
- **ONSET/TAIL**: Not affected.
- **CREDITS**: Not affected.
- **L-a to L-l**: Not affected.
- **LAW 20 / M2**: Thresholds are constants.
- **M12**: Fail closed.
- **LAW 22**: Not affected.
- **Smallest diff**: Yes.

I see no P0 or P1 defects. The implementation is clean, the tests are thorough, and the logic aligns with the order.

One [P3] nit:
In `read_only`, `d.get("ids")` is checked. If `d` is not a dict, `isinstance(d, dict)` is False, so `ids` becomes `None`.
`if not (isinstance(ids, list) ...)` -> `not (False ...)` -> `True`.
`raise ValueError`.
This is correct.

In `only_moments`, `want = set(only["ids"])`.
If `only["ids"]` is empty, `want` is empty.
`kept` is empty.
`missing` is empty.
`read_only` prevents empty `ids` (`ids and all(...)`). So `only["ids"]` is never empty.

The code is robust.

P1_OR_WORSE: 0