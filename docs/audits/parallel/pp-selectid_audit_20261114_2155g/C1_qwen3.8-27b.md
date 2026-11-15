# qwen3.8-27b (qwen/qwen3.8-27b) 92 s finish=stop usage in 13198 / out 3302 usd_reported=0.004237 usd~0.089 (upper-bound price)

I have reviewed the diff for `tests/package/proof_ledger.py` and the new test file `tests/package/test_ruling_107_guard.py` against the RULING 107 (1) requirements and the provided "Governing Laws".

### Analysis

**1. Logic of `fingerprint` and `nothing_new`**
The core logic implements a "skip if unchanged" mechanism.
- `fingerprint()` hashes: moments, delivered/pins/since, ET day, code content, registry state (including due candidates), spotlights, directives, pre-check results, and scorer verdicts.
- `nothing_new()` scans previous ledger directories in reverse chronological order. It returns the name of the *first* (newest) previous build that has a `FINGERPRINT.json` matching the current fingerprint AND has `open_work == 0`.
- If `nothing_new` returns a name, `main()` writes `NOTHING_NEW.json` and exits with 0, skipping the router/model call.

**2. Potential Issues**

*   **[P1] `nothing_new` logic flaw: "Newest" vs "Any Matching"**
    The docstring for `nothing_new` says: *"the NEWEST earlier FINISHED build ... when its fingerprint is this build's and it left nothing undone"*.
    However, the implementation iterates through *all* previous builds (newest to oldest) and returns the *first* one that matches.
    
    Consider this scenario:
    1.  Build A (10:00) runs. Fingerprint `F1`. `open_work=0`. Writes `FINGERPRINT.json`.
    2.  Build B (11:00) runs. Inputs change slightly (e.g., a new moment arrives). Fingerprint `F2`. `open_work=0`. Writes `FINGERPRINT.json`.
    3.  Build C (12:00) runs. Inputs revert to state `F1` (e.g., the new moment was removed or the state is identical to 10:00 for some reason, or more likely, the "newest" logic is intended to prevent re-judging if the *current* state matches a *recent* successful run).
    
    Actually, the standard "idempotency" check usually compares against the *immediately preceding* state or the *last successful* state. The current implementation compares against *any* previous build.
    
    Let's look closer at the requirement: *"a build that judges nothing new must cost $0.00"*.
    If Build B (11:00) had `F2` and `open_work=0`, and Build C (12:00) has `F1` (same as A), `nothing_new` will find A (10:00) because B (11:00) doesn't match `F1`. It will skip C.
    Is this correct? If the state is identical to a previous successful build, re-judging is indeed redundant. The "Newest" in the docstring is slightly misleading if it skips intermediate non-matching builds, but the *behavior* (skip if state matches *any* previous clean build) is a valid optimization for idempotency.
    
    **However**, there is a subtle bug in the iteration logic of `nothing_new`:
    ```python
    for d in sorted(glob.glob(...), reverse=True):
        # ...
        if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
            return os.path.basename(d)
        return None  # <--- THIS IS THE BUG
    return None
    ```
    The `return None` is inside the `for` loop, immediately after the `if` block. This means it only checks the **single newest** previous build. If the newest build doesn't match, it returns `None` immediately, ignoring older builds.
    
    Let's re-read the code carefully:
    ```python
    96 |     for d in sorted(glob.glob(os.path.join(proof_dir, "ledger_*")), reverse=True):
    97 |         if os.path.abspath(d) == os.path.abspath(out_dir):
    98 |             continue
    99 |         try:
   100 |             with open(os.path.join(d, FINGERPRINT)) as f:
   101 |                 prev = json.load(f)
   102 |         except (OSError, ValueError):
   103 |             continue
   104 |         if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
   105 |             return os.path.basename(d)
   106 |         return None
   107 |     return None
    ```
    Yes, line 106 `return None` is inside the loop. This means `nothing_new` **only checks the single most recent previous build**.
    
    **Scenario for Failure:**
    1.  Build 1 (10:00): Fingerprint `F1`, `open_work=0`.
    2.  Build 2 (11:00): Fingerprint `F2` (changed), `open_work=0`.
    3.  Build 3 (12:00): Fingerprint `F1` (reverted to state of Build 1).
    
    `nothing_new` for Build 3 checks Build 2 (newest). Build 2 has `F2`. `F2 != F1`. The loop hits `return None`. Build 3 proceeds to run the model.
    
    Is this a violation? The ruling says "a build that judges nothing new". If the state is identical to Build 1, it is "nothing new" relative to the history. However, usually, these guards are "Last Run" guards. If the intent is "Skip if identical to the *last* run", then the code is correct. If the intent is "Skip if identical to *any* previous run", the code is buggy.
    
    Given the context of "Pre-merge quality gate" and "RULING 107 (1) ... a build that judges nothing new", it is highly likely the intent is to prevent redundant work. If the state oscillates, re-running is arguably "new" work in the sense that the system state has changed since the last run. However, the docstring says *"the NEWEST earlier FINISHED build ... when its fingerprint is this build's"*. This phrasing supports the "only check the newest" interpretation.
    
    **BUT**, look at the test `test_only_the_newest_finished_build_counts`:
    ```python
    282 |            build("ledger_20261114_200000", "F")
    283 |            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")
    284 |            build("ledger_20261114_210000")                                  # no FINGERPRINT
    285 |            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")
    ```
    In this test, `ledger_20261114_210000` has **no** `FINGERPRINT.json`. The code does `continue` on `OSError/ValueError`. So it skips 210000 and checks 200000. This works.
    
    Now consider:
    1.  Build 200000: `F1`, `open_work=0`.
    2.  Build 210000: `F2`, `open_work=0`.
    3.  Build 220000: `F1`.
    
    `nothing_new` checks 210000. It has `FINGERPRINT.json` with `F2`. `F2 != F1`. It hits `return None`. It does **not** check 200000.
    
    If the requirement is strictly "Skip if identical to the *immediately preceding* valid build", this is correct. If the requirement is "Skip if identical to *any* previous build", this is a [P1] defect because it fails to skip a redundant build.
    
    Given the phrasing "a build that judges nothing new", and the fact that `F1` was already judged and passed, re-judging `F1` is redundant. The "Newest" in the docstring is ambiguous. However, in most CI/CD or pipeline contexts, "nothing new" implies "no change since the last run". If the state changed to `F2` and back to `F1`, the system *did* change. But the *judgment* for `F1` is already known.
    
    Let's look at the "Open Work" aspect. If Build 210000 (`F2`) had `open_work > 0`, it wouldn't be a "finished" build in the sense of being a clean reference. But it still has a `FINGERPRINT.json`.
    
    I will flag this as a [P2] because the behavior (only checking the immediate predecessor) is a defensible interpretation of "newest earlier build", but it might miss optimization opportunities if the intent was global idempotency. However, looking at the test `test_only_the_newest_finished_build_counts`, it explicitly tests that a build *without* a fingerprint is skipped, allowing it to find an older one. It does *not* test the case where the newest build *has* a different fingerprint.
    
    Actually, re-reading the docstring: *"the NEWEST earlier FINISHED build ... when its fingerprint is this build's"*. This strongly implies that if the newest build's fingerprint is *not* this build's, the condition is not met. So the code matches the docstring. I will downgrade this to [P3] or no finding, as it's consistent with the documentation.

*   **[P1] `open_work` calculation is fragile**
    ```python
    86 |     no_verdict = json.dumps(res, default=str).count('"verdict": "error"') + \
    87 |         json.dumps(sp, default=str).count('"verdict": "error"')
    ```
    This uses string counting on JSON dumps. This is extremely fragile.
    1.  If a string value in the JSON contains `"verdict": "error"` (e.g., in a log message or a quoted text field), it will be counted as an error.
    2.  If the JSON structure changes slightly (e.g., whitespace, key order), the string match might fail or succeed incorrectly.
    3.  `json.dumps` with `default=str` might serialize objects in a way that doesn't match the literal string `"verdict": "error"` if there are spaces or different quoting.
    
    This is a [P1] defect. It should traverse the JSON structure to count actual verdict fields.

*   **[P2] `code_content` includes `tests/package` driver modules**
    ```python
    50 | +                   + [f for f in glob.glob(os.path.join(here, "*.py")) if not os.path.basename(f).startswith("test_")])
    ```
    This includes `proof_ledger.py` itself. If `proof_ledger.py` is modified, the fingerprint changes. This is correct.
    However, it also includes *any* other `.py` file in `tests/package` that doesn't start with `test_`. If there are other utility modules there, they are included. This seems intentional ("driver modules").

*   **[P2] `fingerprint` uses `os.path.getmtime` for pre-check results**
    ```python
    67 |         res = sorted((n, os.path.getsize(...), os.path.getmtime(...))
    ```
    `mtime` is time-varying. If a file is touched (e.g., by a backup process, or a re-write with identical content), the `mtime` changes, the fingerprint changes, and the build runs. This violates the "nothing new" goal if the content is identical.
    The ruling says "a build that judges nothing new". If the *content* of the pre-check results is the same, but the file was touched, is it "new"? Probably not.
    Using `mtime` makes the fingerprint sensitive to file system metadata, not just content. This is a [P2] defect. It should hash the file content, not the mtime.

*   **[P3] `nothing_new` returns `None` if the newest build is the current one**
    The code skips `out_dir`. This is correct.

*   **[P3] Test coverage for `open_work`**
    The test `test_open_work_counts_what_a_build_left_undone` uses simple dicts. It doesn't test the string-counting fragility.

### Findings

1.  **[P1] Fragile `open_work` calculation**: `open_work` uses `json.dumps(...).count('"verdict": "error"')`. This is susceptible to false positives if the string `"verdict": "error"` appears in any string value within the JSON (e.g., in a log message, a quoted transcript, or a nested string). It is also susceptible to formatting changes in `json.dumps`. This should be replaced with a recursive traversal of the JSON structure to count actual `verdict` fields with value `"error"`.

2.  **[P2] `fingerprint` uses `mtime` for pre-check results**: The `fingerprint` function includes `os.path.getmtime` for pre-check result files. This makes the fingerprint change if a file is touched or rewritten with identical content, causing unnecessary model calls. It should hash the file content instead.

3.  **[P3] `nothing_new` only checks the single newest previous build**: The implementation returns `None` if the single newest previous build's fingerprint doesn't match. This is consistent with the docstring ("the NEWEST earlier FINISHED build"), but if the intent was to skip any build that matches *any* previous clean build, this is a limitation. Given the docstring, this is likely intended behavior, but it's worth noting that it doesn't provide global idempotency, only local (last-run) idempotency.

4.  **[P3] `code_content` includes `proof_ledger.py`**: The fingerprint includes the content of `proof_ledger.py` itself. This is correct for ensuring that changes to the guard logic trigger a re-run, but it means that any change to the guard (even a comment) will invalidate the cache. This is acceptable.

P1_OR_WORSE: 1