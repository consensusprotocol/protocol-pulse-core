# qwen3.8-27b (qwen/qwen3.8-27b) 77 s finish=stop usage in 13224 / out 6999 usd_reported=0.005605 usd~0.145 (upper-bound price)

To perform this audit, I will analyze the provided diff against the "Governing Laws" and the specific "PLEASE CHECK" criteria.

### Analysis of the Code Change

**Context:** The change introduces a `refused` status for moments in the word-pass pipeline. Previously, moments that were not `sentence_ready` (either because they failed or were just not ready yet) were lumped into `waiting`. The integrator clarified that the worker *never* re-works a moment once it has a row. Therefore, a moment with a row that is not `sentence_ready` is permanently `refused`, not `waiting`.

**1. `pipeline/ledger_build.py` - `word_pass_index`**
*   **Change:** Adds `rep["refused"] = sorted(mid for mid in last if mid not in out)`.
*   **Logic Check:** `last` contains the moment IDs of the *last* row for each moment. `out` contains the moment IDs that are `sentence_ready` and have a valid `window_record` and `record_sha256`.
*   **Law Compliance (M12 Fail Closed):** If a row is unreadable or malformed, it won't be in `out`. If it's the last row, it will be in `last`. Thus, it goes into `refused`. This is correct. A failed moment is final.
*   **Check (1):** "The refused set is exactly what the worker will never re-work."
    *   The docstring states: "The worker never works a moment again once it has a row... so these are final, never 'waiting'."
    *   The code identifies moments where the *last* row is not in the `out` (ready) set. This aligns with the "last row wins" logic used for `out`.
    *   **Verdict:** Correct.

**2. `pipeline/ledger_build.py` - `build_inputs`**
*   **Change:** Accepts `word_pass_refused`.
*   **Logic Check:**
    *   `refused = set(word_pass_refused or ())`.
    *   Inside the loop for rows `irs` of a video `vid`:
        *   `wp = word_pass.get(r["moment_id"])`.
        *   If `wp is None`:
            *   If `r["moment_id"] in refused`: `n_ref += 1`.
            *   Else: `waiting += 1`.
    *   **Check (2):** "No row can be counted twice."
        *   A row either has a `wp` (window pass record) or it doesn't.
        *   If it has a `wp`, it goes through `window_source`. If that fails, it's `window_failed` or passed over. It is *not* counted in `n_ref` or `waiting` in the `wp is None` branch.
        *   If it has *no* `wp`, it is either in `refused` or `waiting`. These are mutually exclusive sets for a given moment ID in this context (a moment is either in the `refused` list or it isn't).
        *   **Verdict:** Correct.
    *   **Check (3):** "The no-window branch: no_word_record, its why counts and its per-video rows."
        *   Code:
            ```python
            if not windows and len(rs) > n_ref:
                # ...
                report["no_word_record"] += len(rs) - n_ref
                report["no_word_record_why"][why] = ... + len(rs) - n_ref
                report["no_word_record_videos"][vid] = {"rows": len(rs) - n_ref, "why": why}
            elif windows:
                report["window_waiting"] += waiting
            ```
        *   **Scenario A: Video has NO windows (`windows` is empty/0).**
            *   If `len(rs) > n_ref` (there are some rows that are *not* refused, i.e., they are waiting):
                *   `no_word_record` increases by `len(rs) - n_ref`.
                *   `no_word_record_videos` records `len(rs) - n_ref`.
                *   This is correct. The refused rows are accounted for in `report["window_refused"] += n_ref` (line 77).
            *   If `len(rs) == n_ref` (ALL rows are refused):
                *   The `if` condition `len(rs) > n_ref` is False.
                *   The `elif windows` is False (windows is 0).
                *   So, `no_word_record` is NOT incremented. `no_word_record_videos` is NOT updated.
                *   `report["window_refused"]` IS incremented by `n_ref`.
                *   **Verdict:** Correct. A video where all rows are refused should not appear in `no_word_record_videos` as "waiting for a word record" because it isn't waiting; it's dead.
        *   **Scenario B: Video HAS windows (`windows` > 0).**
            *   `report["window_refused"] += n_ref` (line 77).
            *   `report["window_waiting"] += waiting` (line 89).
            *   `no_word_record` is NOT touched.
            *   **Verdict:** Correct. Refused and waiting are distinct counts.

**3. `pipeline/spotlight.py` - `next_attempt`**
*   **Change:** Accepts `refused`.
*   **Logic Check:**
    *   `n_ref = sum(1 for r in rs if r.get("moment_id") in refused and r.get("moment_id") not in word_pass)`
    *   `word_pass_waiting = len(rs) - ready - n_ref`
    *   **Check (2):** "No row can be counted twice."
        *   `ready` counts rows where `word_pass.get(mid)` exists and is `sentence_ready`.
        *   `n_ref` counts rows where `mid` is in `refused` AND `mid` is NOT in `word_pass`.
        *   Can a row be both `ready` and `n_ref`?
            *   If it's `ready`, it is in `word_pass`.
            *   `n_ref` requires `mid not in word_pass`.
            *   Therefore, `ready` and `n_ref` are disjoint.
        *   Can a row be `waiting` and `n_ref`?
            *   `waiting` is calculated as `len(rs) - ready - n_ref`.
            *   By definition, `waiting` is the remainder. It cannot overlap with `n_ref` or `ready`.
        *   **Verdict:** Correct.

**4. `tests/package/proof_ledger.py`**
*   **Change:** Passes `refused` to `build_inputs` and `next_attempt`.
*   **Logic Check:**
    *   `refused = wp_rep.get("refused") or []`
    *   `LB.build_inputs(..., word_pass_refused=refused)`
    *   `SPOT.next_attempt(..., refused=refused)`
    *   **Verdict:** Correct wiring.

**5. `tests/package/test_ledger_build.py`**
*   **Test 1:** `test_the_refused_are_the_moments_whose_last_row_gives_no_window`
    *   Checks that `refused` contains IDs where the last row is not ready.
    *   **Verdict:** Passes logic.
*   **Test 2:** `test_a_row_the_word_pass_refused_is_counted_apart_from_the_waiting`
    *   Verifies counts in `build_inputs`.
    *   **Verdict:** Passes logic.

**6. `tests/package/test_ruling_107_guard.py`**
*   **Test:** `test_the_word_pass_refused_reach_the_inputs_and_the_log_gives_their_count`
    *   Verifies that `word_pass_refused` is passed to `build_inputs`.
    *   Verifies that the log contains the count but not the IDs.
    *   **Verdict:** Passes logic.

**7. `tests/package/test_spotlight.py`**
*   **Test:** `test_ruling_95_a_moment_the_word_pass_refused_is_not_waiting`
    *   Verifies `word_pass_refused` and `word_pass_waiting` calculations.
    *   **Verdict:** Passes logic.

### Potential Issues / Findings

**Finding 1: [P2] Ambiguity in `spotlight.py` `n_ref` calculation regarding `word_pass` presence.**
In `spotlight.py`, `n_ref` is calculated as:
```python
n_ref = sum(1 for r in rs if r.get("moment_id") in refused and r.get("moment_id") not in word_pass)
```
In `ledger_build.py`, `refused` is defined as moments whose *last row* is not in `out` (ready). `out` is built from `word_pass` rows that are `sentence_ready`.
If a moment is in `refused`, it means its last row was NOT `sentence_ready`.
Does this imply it is NOT in `word_pass`?
`word_pass` (the dict passed to `next_attempt`) is the return value of `word_pass_index`, which is `{moment_id: row}` for *ready* rows only.
So, if a moment is in `refused`, it is *not* in `word_pass` (the dict).
Therefore, the condition `r.get("moment_id") not in word_pass` is always True for any moment in `refused`.
The check is redundant but safe. It ensures that if the logic of `word_pass_index` changes to include non-ready rows in the dict (which it currently doesn't), `spotlight` wouldn't double count.
However, strictly speaking, `refused` and `word_pass` (the dict) are disjoint sets of keys.
Is there a case where a moment is in `refused` but *also* in `word_pass`?
`word_pass_index` returns `out` (ready) and `refused` (not ready). They are disjoint.
So `n_ref` is simply `sum(1 for r in rs if r.get("moment_id") in refused)`.
The extra check `and r.get("moment_id") not in word_pass` is defensive. It is not a bug.

**Finding 2: [P3] Log message in `proof_ledger.py` might be slightly misleading.**
```python
say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(refused)))}")
```
`wp_rep` already contains `refused` as a list of IDs.
`dict(wp_rep, refused=len(refused))` overwrites the `refused` key with the *count*.
This is intentional to keep the log line short (IDs are in `inputs.json`).
The test `test_the_word_pass_refused_reach_the_inputs_and_the_log_gives_their_count` verifies this:
```python
self.assertIn('"refused": 2', log)
self.assertNotIn("Xa1", log)
```
This is correct behavior.

**Finding 3: [P1] Missing Index for `moment_id` in `word_pass.jsonl` processing?**
The code reads `word_pass.jsonl` line by line.
```python
with open(path) as f:
    for line in f:
        ...
        mid = row.get("moment_id")
        if mid:
            last[mid] = row
```
This is an O(N) operation where N is the number of lines.
The "Technology Stack" section says: "Every DB query on a sort/filter column MUST have an index".
This is a file read, not a DB query. However, if `word_pass.jsonl` is large, this is fine.
But wait, `word_pass_index` is called in `proof_ledger.py` and `run_fresh.py` (implied).
Is there a performance concern?
The file is JSONL. It's likely small (one line per moment).
No P1 here.

**Finding 4: [P2] `build_inputs` logic for `no_word_record_videos` when `windows` is 0 and `n_ref` is 0.**
If `windows` is 0 and `n_ref` is 0, then `len(rs) > n_ref` is `len(rs) > 0`.
If `len(rs) > 0`, it adds to `no_word_record`.
This is the "waiting" case.
If `len(rs) == 0`, it does nothing.
This is correct.

**Finding 5: [P1] `spotlight.py` `next_attempt` `word_pass_waiting` calculation.**
```python
"word_pass_waiting": len(rs) - ready - n_ref
```
If `ready` + `n_ref` > `len(rs)`, this becomes negative.
Can `ready` + `n_ref` > `len(rs)`?
`ready` counts rows where `mid` is in `word_pass` (ready dict).
`n_ref` counts rows where `mid` is in `refused` (list) AND `mid` NOT in `word_pass`.
Since `word_pass` (ready) and `refused` are disjoint sets of moment IDs (from `word_pass_index`), a row cannot be both `ready` and `refused`.
Therefore, `ready` + `n_ref` <= `len(rs)`.
The result is non-negative.
**Verdict:** Safe.

**Finding 6: [P2] `ledger_build.py` `word_pass_index` `refused` list sorting.**
```python
rep["refused"] = sorted(mid for mid in last if mid not in out)
```
`last` is a dict `{mid: row}`. Iterating over `last` gives keys.
`out` is a dict `{mid: row}`.
`mid not in out` checks keys.
This is correct.

**Finding 7: [P1] `tests/package/test_ruling_107_guard.py` `run_driver` stubbing.**
```python
def inputs(*a, **k):
    (seen if seen is not None else {}).update(k)
    return copy.deepcopy(POOL), {}, {}
```
The stub returns `POOL` (moments), `{}` (sources), `{}` (report).
The test checks `seen.get("word_pass_refused")`.
This verifies the *call* signature.
It does not verify the *logic* of `build_inputs` with refused IDs, but `test_ledger_build.py` does that.
This is acceptable separation of concerns.

**Finding 8: [P2] `funnel.py` change.**
```python
s0 += [("refused by the word pass (its row is not sentence-ready or failed; never re-worked)", None)] * \
    int(rep.get("window_refused") or 0)
```
This adds a supply line for refused moments.
This is a reporting change.
**Verdict:** Correct.

**Finding 9: [P1] `spotlight.py` `next_attempt` `refused` parameter default.**
```python
def next_attempt(rows, word_pass, now, captions_for=None, refused=()):
```
`refused` defaults to empty tuple.
`refused = set(refused or ())`
This is safe.

**Finding 10: [P2] `ledger_build.py` `build_inputs` `word_pass_refused` parameter default.**
```python
def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None, ledger_store=None, word_pass_refused=()):
```
`refused = set(word_pass_refused or ())`
This is safe.

**Finding 11: [P1] `word_pass_index` `refused` logic vs `last` dict.**
`last` is built by iterating lines.
```python
for line in f:
    ...
    mid = row.get("moment_id")
    if mid:
        last[mid] = row
```
If a moment has multiple rows, the *last* one in the file wins.
`out` is built similarly:
```python
if row.get("sentence_ready") and row.get("window_record") and row.get("record_sha256"):
    out[mid] = row
```
Wait. `out` is built in the *same* loop?
Let's check the diff for `word_pass_index`.
The diff shows:
```python
   20 | @@ -193,6 +195,7 @@ def word_pass_index(path=WORD_PASS):
   21 |              rep["ready"] += 1
   22 |          else:
   23 |              rep["unreadable"] += 1
   24 | +    rep["refused"] = sorted(mid for mid in last if mid not in out)
   25 |      return out, rep
```
The context lines 21-23 suggest `out` is populated in the loop.
Let's look at the full function structure implied.
Usually, `word_pass_index` iterates, updates `last[mid]`, and if the row is ready, updates `out[mid]`.
If `out` is updated *only* when a row is ready, and `last` is updated *always*, then:
- If the last row is ready, `mid` is in `out` and `last`. `mid not in out` is False. Not refused.
- If the last row is NOT ready, `mid` is in `last`. Is it in `out`?
    - If a *previous* row was ready, `out[mid]` would have been set.
    - But `last[mid]` is overwritten by the non-ready row.
    - Does `out` get cleared? No.
    - So if a moment has Row 1 (Ready) and Row 2 (Not Ready), `last[mid]` = Row 2. `out[mid]` = Row 1.
    - `mid not in out` is False.
    - So it is NOT refused.
    - But the worker "never re-works a moment it has a row for".
    - If the last row is Not Ready, is the moment "Refused"?
    - The docstring says: "The worker never works a moment again once it has a row... so a moment whose last row is failed, not sentence-ready or unreadable is refused for good".
    - This implies that if the *last* row is not ready, it is refused.
    - But the code `mid not in out` checks if the moment is in the `out` dict.
    - If `out` retains the *first* ready row, then a moment with a later non-ready row would still be in `out`, and thus NOT refused.
    - **This is a potential bug.**

Let's re-read the `word_pass_index` implementation details from the diff context.
The diff only shows the addition of `rep["refused"]`.
It does *not* show how `out` is populated.
However, the test `test_the_refused_are_the_moments_whose_last_row_gives_no_window` provides insight:
```python
rows = [dict(ok, moment_id="R"), dict(boom, moment_id="F"),
        dict(ok, moment_id="N", sentence_ready=False), dict(ok, moment_id="U", record_sha256=None),
        dict(boom, moment_id="L"), dict(ok, moment_id="L"),                # the last row wins, both ways
        dict(ok, moment_id="T"), dict(ok, moment_id="T", sentence_ready=False)]
...
self.assertEqual((sorted(idx), rep["refused"]), (["L", "R"], ["F", "N", "T", "U"]))
```
- `L`: Row 1 `boom` (not ready), Row 2 `ok` (ready). Last is `ok`. `L` is in `idx` (out). `L` is NOT in `refused`.
- `T`: Row 1 `ok` (ready), Row 2 `ok` (not ready). Last is `not ready`. `T` is NOT in `idx` (out). `T` IS in `refused`.
- `R`: Row 1 `ok` (ready). Last is `ok`. `R` is in `idx`. `R` is NOT in `refused`.
- `F`: Row 1 `boom`. Last is `boom`. `F` is NOT in `idx`. `F` IS in `refused`.
- `N`: Row 1 `ok` (not ready). Last is `not ready`. `N` is NOT in `idx`. `N` IS in `refused`.
- `U`: Row 1 `ok` (no sha). Last is `no sha`. `U` is NOT in `idx`. `U` IS in `refused`.

The test expects `T` to be refused.
This implies that `out` (idx) does NOT contain `T`.
This means `out` is populated based on the *last* row's status, or `out` is cleared/overwritten such that if the last row is not ready, the moment is not in `out`.
Given the test passes (implied by "12 of 14 killed... control run passes"), the logic `mid not in out` correctly identifies moments where the *last* row is not ready.
This suggests `out` is built such that `mid` is in `out` **if and only if** the last row for `mid` is ready.
Or, `out` is built by iterating, and if a later row is not ready, it removes `mid` from `out`?
Or, `out` is built from `last`?
If `out` is built from `last`, then `out` would only contain moments whose last row is ready.
Then `mid not in out` would be True for all moments whose last row is not ready.
This matches the test expectation.

So, the logic holds **IF** `out` is derived from the last row's readiness.
The diff doesn't show the construction of `out`, but the test confirms the behavior.
**Verdict:** No bug, assuming the existing `out` construction logic aligns with the "last row wins" principle for readiness. The test confirms this.

**Finding 12: [P2] `spotlight.py` `n_ref` calculation relies on `refused` list.**
`refused` is a list of IDs.
`n_ref` counts rows where `mid` is in `refused`.
This is O(N*M) if `refused` is a list and `rs` is a list.
`refused` is converted to a set in `next_attempt`: `refused = set(refused or ())`.
So it is O(N).
**Verdict:** Correct.

**Finding 13: [P3] `ledger_build.py` `build_inputs` `n_ref` variable scope.**
`n_ref` is initialized to 0 inside the `for vid, rs in by_vid.items():` loop?
No, looking at the diff:
```python
   59 |          caps, why_w, waiting, windows, kept = {}, [], 0, 0, []     # kept: (start, end, moment id) of window moments
   60 | +        n_ref = 0                                    # rows the word pass refused: final, never waiting
   61 |          for i, r in irs:                             # ONE WINDOW PER MOMENT
```
It is inside the video loop.
`report["window_refused"] += n_ref` is also inside the video loop (line 77).
This is correct.

**Finding 14: [P1] `tests/package/test_ledger_build.py` `test_a_row_the_word_pass_refused_is_counted_apart_from_the_waiting`**
```python
rows = [r, mk("W2", "vidW", 100.0), mk("W3", "vidW", 200.0),      # vidW: W1 ready, W2 refused, W3 waits
        mk("X1", "vidX", 10.0), mk("X2", "vidX", 20.0),           # vidX: every row refused
        mk("Y1", "vidY", 10.0),                                    # vidY: no row yet
        mk("Z1", "vidZ", 10.0), mk("Z2", "vidZ", 20.0)]           # vidZ: no window; Z1 refused, Z2 waits
```
`word_pass={"W1": wp}`.
`word_pass_refused=["W2", "X1", "X2", "Z1"]`.

- **vidW**:
    - W1: `wp` exists. `window_source` succeeds (assumed). `windows` = 1.
    - W2: `wp` is None. `W2` in `refused`. `n_ref` = 1.
    - W3: `wp` is None. `W3` NOT in `refused`. `waiting` = 1.
    - `windows` = 1.
    - `report["window_refused"] += 1`.
    - `report["window_waiting"] += 1`.
    - `no_word_record` is NOT incremented (because `windows` > 0).
- **vidX**:
    - X1: `wp` is None. `X1` in `refused`. `n_ref` = 1.
    - X2: `wp` is None. `X2` in `refused`. `n_ref` = 2.
    - `windows` = 0.
    - `report["window_refused"] += 2`.
    - `if not windows and len(rs) > n_ref`: `len(rs)` is 2. `n_ref` is 2. `2 > 2` is False.
    - `no_word_record` is NOT incremented.
    - `no_word_record_videos` is NOT updated.
- **vidY**:
    - Y1: `wp` is None. `Y1` NOT in `refused`. `waiting` = 1.
    - `windows` = 0.
    - `report["window_refused"] += 0`.
    - `if not windows and len(rs) > n_ref`: `1 > 0` is True.
    - `no_word_record` += 1.
    - `no_word_record_videos["vidY"]` = 1.
- **vidZ**:
    - Z1: `wp` is None. `Z1` in `refused`. `n_ref` = 1.
    - Z2: `wp` is None. `Z2` NOT in `refused`. `waiting` = 1.
    - `windows` = 0.
    - `report["window_refused"] += 1`.
    - `if not windows and len(rs) > n_ref`: `2 > 1` is True.
    - `no_word_record` += `2 - 1` = 1.
    - `no_word_record_videos["vidZ"]` = 1.

Total `window_refused` = 1 (W) + 2 (X) + 0 (Y) + 1 (Z) = 4.
Total `window_waiting` = 1 (W) + 0 (X) + 0 (Y) + 1 (Z) = 2.
Total `no_word_record` = 0 (W) + 0 (X) + 1 (Y) + 1 (Z) = 2.

Test assertions:
```python
self.assertEqual((rep["window_waiting"], rep["window_refused"], rep["no_word_record"]), (1, 4, 2))
```
Wait. My calculation for `window_waiting` was 2 (W3 and Z2).
The test expects `window_waiting` to be 1.
Let's re-read the test setup.
`word_pass={"W1": wp}`.
`wp` is a valid window record.
In `build_inputs`, `window_source` is called for W1.
If `window_source` succeeds, `windows` becomes 1 for vidW.
For vidW:
- W1: `wp` exists. `window_source` succeeds. `windows` = 1.
- W2: `wp` is None. `refused`. `n_ref` = 1.
- W3: `wp` is None. `waiting` = 1.
`report["window_waiting"] += waiting` (1).

For vidZ:
- Z1: `wp` is None. `refused`. `n_ref` = 1.
- Z2: `wp` is None. `waiting` = 1.
`windows` = 0.
`if not windows and len(rs) > n_ref`: `2 > 1` True.
`no_word_record` += 1.
`report["window_waiting"]` is NOT incremented in the `if not windows` branch.
It is only incremented in the `elif windows` branch.
So for vidZ, `waiting` (1) is NOT added to `report["window_waiting"]`. It is added to `no_word_record` (as `len(rs) - n_ref`).

So:
- vidW: `window_waiting` += 1.
- vidX: `window_waiting` += 0.
- vidY: `window_waiting` += 0.
- vidZ: `window_waiting` += 0.
Total `window_waiting` = 1.

My previous calculation for vidZ was wrong. I assumed `waiting` is always added to `window_waiting`. But the code says:
```python
if not windows and len(rs) > n_ref:
    # ... no_word_record ...
elif windows:
    report["window_waiting"] += waiting
```
If `windows` is 0, `waiting` is NOT added to `window_waiting`. It is effectively converted to `no_word_record` (minus refused).
This is consistent with the "no window" logic: if a video has no windows, its rows are "waiting for a word record" (no_word_record), not "waiting for their own window" (window_waiting).
`window_waiting` is specifically for rows in a video that *does* have windows, but the row itself doesn't have a window record yet.

So the test expectation `(1, 4, 2)` is correct.
- `window_waiting`: 1 (W3).
- `window_refused`: 4 (W2, X1, X2, Z1).
- `no_word_record`: 2 (Y1, Z2).

**Verdict:** Correct.

### Conclusion

The code changes are logically sound, correctly implement the "refused" status, and pass the provided tests. The separation of `refused` from `waiting` is handled correctly in both `build_inputs` and `next_attempt`. The "no window" branch correctly excludes refused rows from `no_word_record` counts.

No P0 or P1 findings.

P1_OR_WORSE: 0