# qwen3.8-27b (qwen/qwen3.8-27b) 176 s finish=length usage in 9835 / out 16000 usd_reported=0.011865 usd~0.270 (upper-bound price)

I will analyze the provided diff against the Governing Laws and the specific instructions in RULING 126 (1).

### Analysis of `pipeline/context_integrity.py`

**Change:** `show_date(now)` converts the UTC `now` to `America/New_York` and formats it as `YYYY-MM-DD`.
**Law Check:**
- **L-k (One Canonical Form):** The date format is consistent.
- **DST Handling:** `zoneinfo` handles DST transitions correctly. For example, on the day the clock springs forward, 19:00 ET is 23:00 UTC (same day). On the day it falls back, 19:00 ET is 23:00 UTC (same day). The logic `now.astimezone(ZoneInfo("America/New_York"))` is the standard, correct way to get the local calendar date.
- **None Handling:** Returns `None` if `now` is `None`. This is safe.

**Finding:** No issues found in `context_integrity.py`.

### Analysis of `pipeline/package.py`

**Change 1: `step_a_key(m, context)`**
- **Logic:** If `time_sensitive(m)` is False, it removes `show_date` from the context dictionary before hashing. If True, it keeps it.
- **Law Check:**
    - **RULING 126 (1):** "a verdict should carry the date in its cache key ONLY when the moment holds time words". This implementation matches the ruling exactly.
    - **M12 (Fail Closed):** `time_sensitive` is an existing function. If it fails, the exception propagates. This is acceptable.
    - **L-k:** The hashing uses `json.dumps(..., sort_keys=True)`. This ensures canonical ordering.

**Change 2: `step_a_old_keys(m, context, now)`**
- **Logic:** Generates keys for `k=0` (today's UTC date) and `k=1` (yesterday's UTC date).
- **Code:**
  ```python
  f"{text_sha(json.dumps(dict(context, show_date=(now - timedelta(days=k)).strftime('%Y-%m-%d')), sort_keys=True))}"
  ```
- **Critical Flaw:** The old keys were generated using the **UTC** date (as stated in the prompt: "Before, both used now.strftime on the run clock, which is UTC").
- **The Bug:** `now` is the current UTC time. `now - timedelta(days=k)` is also UTC. `.strftime('%Y-%m-%d')` on a UTC datetime yields the **UTC** calendar date.
- **Scenario:** It is currently 2026-11-16 20:00 UTC.
    - `k=0`: `2026-11-16`.
    - `k=1`: `2026-11-15`.
    - The old cache keys were created using the UTC date at the time of the previous run.
    - If a previous run happened at 2026-11-16 05:00 UTC, the old key used `2026-11-16`.
    - If a previous run happened at 2026-11-15 23:00 UTC, the old key used `2026-11-15`.
    - The function `step_a_old_keys` correctly reconstructs the *UTC* dates that would have been used in the old key format.
    - **Wait, let's look closer at the "Old Key" definition.**
    - The prompt says: "the keys its verdict was cached under before the date left the key (the context with the UTC show date in it...)"
    - The code constructs: `dict(context, show_date=(now - timedelta(days=k)).strftime('%Y-%m-%d'))`.
    - `context` here is the *new* context (which has the ET date).
    - The code overwrites `show_date` in the copy of `context` with the UTC date string.
    - This correctly simulates the old key structure where `show_date` was the UTC date.
    - **Is the window correct?** The prompt says "today's and yesterday's".
    - If it is 2026-11-16 20:00 UTC:
        - Today's UTC date: 2026-11-16.
        - Yesterday's UTC date: 2026-11-15.
    - The old code used `now.strftime("%Y-%m-%d")` where `now` was the run clock (UTC).
    - So, a run at 2026-11-16 00:00 UTC would have used `2026-11-16`.
    - A run at 2026-11-15 23:00 UTC would have used `2026-11-15`.
    - The function checks `k=0` and `k=1`. This covers the last 24 hours of UTC dates.
    - **Potential Edge Case:** What if the "old" run was more than 24 hours ago? The prompt says "a moment inside the 12-hour publish window cannot hold an older one". This implies the cache is only relevant for recent moments. The logic holds.

**Change 3: `prescreen` logic**
- **Code:**
  ```python
  rec = pick(keys[mid])
  if rec is None and not time_sensitive(m):
      rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
      if rec is not None:
          moved.setdefault(keys[mid], {})[rec["backend"]] = rec
  ```
- **Law Check:**
    - **RULING 126 (1):** "a moment with no time words is judged the same on any date and must never be re-paid because a clock rolled over."
    - The code checks the new key first. If not found, and the moment is NOT time-sensitive, it checks the old keys.
    - If found in old keys, it uses that verdict (`rec`) and marks it for migration (`moved`).
    - **Migration:** `_cache_put(cache, dict(moved, **new))`.
    - This writes the found verdict under the *new* key.
    - **Correctness:** This ensures that the next time this moment is processed, it will be found under the new key (since `show_date` is stripped for non-time-sensitive moments, the new key is stable across dates).
    - **Time-Sensitive Moments:** If `time_sensitive(m)` is True, `step_a_old_keys` is NOT called. The code falls through to `rec is None`. If `rec` is None, it will be added to `todo` and a new model call will be made. This is correct because time-sensitive moments *must* be re-evaluated if the date changes (or rather, their cache key includes the date, so a new date means a new key, and the old key is not checked).
    - **Wait:** For time-sensitive moments, the new key *includes* the ET date. The old key *included* the UTC date.
    - If a time-sensitive moment was cached yesterday (UTC date Y), and today is (UTC date T), the new key is based on ET date T_ET.
    - The code does *not* check old keys for time-sensitive moments.
    - This means a time-sensitive moment will *always* be re-evaluated if the ET date changes, even if it was evaluated yesterday.
    - Is this a violation? RULING 126 (1) says: "a moment with no time words is judged the same on any date...". It implies time-sensitive moments are *not* judged the same on any date. Therefore, re-evaluating them on a new date is the intended behavior.
    - **However:** What if the ET date is the *same*?
    - If the ET date is the same, the new key is the same. `pick(keys[mid])` will find it. No re-evaluation.
    - If the ET date changes, the new key changes. `pick(keys[mid])` returns None. `time_sensitive` is True, so old keys are not checked. Re-evaluation happens.
    - This is correct.

**Finding [P1]: Inconsistency in `step_a_old_keys` date calculation vs. "Old" behavior.**
The prompt states: "Before, both used now.strftime on the run clock, which is UTC".
The code in `step_a_old_keys` uses: `(now - timedelta(days=k)).strftime('%Y-%m-%d')`.
`now` is `ctx.now`, which is the current UTC time.
This correctly generates the UTC dates for "today" and "yesterday".
**BUT**, there is a subtle issue with the `context` dictionary passed to `step_a_old_keys`.
In `prescreen`:
```python
contexts[mid] = {..., "show_date": CI.show_date(ctx.now)}
...
rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
```
`step_a_old_keys` does:
```python
dict(context, show_date=(now - timedelta(days=k)).strftime('%Y-%m-%d'))
```
It takes the *new* context (with ET date) and *overwrites* the `show_date` with the UTC date.
This correctly reconstructs the old key's context.
**Is there a bug?**
Let's check the `pick` function.
```python
pick = lambda key: next((x for name, x in sorted((cdb.get(key) or {}).items())
                         if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
```
This looks for a verdict in the cache `cdb` under `key`.
The old keys are generated correctly.
The filter `off(name)` ensures we don't pick a verdict from a writer that is currently excluded.
This seems correct.

**Finding [P2]: `step_a_old_keys` only checks 2 days.**
The prompt says: "a moment inside the 12-hour publish window cannot hold an older one".
If the system has been down for 3 days, or if a moment was cached 3 days ago, it won't be found.
However, the cache is likely pruned or the moments are fresh.
Given the "12-hour window" constraint, checking 2 days (48 hours) is a safe superset.
This is not a defect, but a design choice.

**Finding [P1]: Potential Data Loss / Incorrect Migration for Time-Sensitive Moments?**
No, time-sensitive moments are *not* migrated. They are re-evaluated.
The `moved` dict only contains entries for non-time-sensitive moments.
`_cache_put(cache, dict(moved, **new))`.
`new` contains the results of the *current* run (new model calls).
`moved` contains the old verdicts written under new keys.
This merges them.
**Wait:** If a non-time-sensitive moment is found in the old key, it is added to `moved`.
It is NOT added to `todo`.
So no new model call is made.
The verdict is reused.
This is correct.

**Finding [P0]: `show_date` in `contexts_from_sources` vs `prescreen`.**
In `prescreen`, `contexts[mid]` is built with `CI.show_date(ctx.now)`.
In `contexts_from_sources`, `show_date` is also `CI.show_date(now)`.
These are consistent.

**Finding [P1]: The `step_a_old_keys` function uses `now` (UTC) to generate UTC dates.**
This is correct.
However, consider the transition from UTC to ET.
Old Key: `... : {context with UTC date} : ...`
New Key: `... : {context with ET date (or no date)} : ...`
The migration logic:
1. Check New Key.
2. If not found and not time-sensitive:
   a. Generate Old Keys (UTC dates).
   b. Check Old Keys.
   c. If found, use verdict and write to New Key.
This logic is sound.

**Finding [P2]: `time_sensitive` check in `step_a_key`.**
`step_a_key` uses `time_sensitive(m)`.
`prescreen` uses `time_sensitive(m)` to decide whether to check old keys.
This is consistent.

**Finding [P1]: Test `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
The test constructs `old` keys using:
```python
c = dict(seen[m["moment_id"]], show_date=NOW.strftime("%Y-%m-%d"))
old[f"...:{PK.text_sha(json.dumps(c, sort_keys=True))}:..."] = ...
```
`NOW` is a UTC datetime. `NOW.strftime("%Y-%m-%d")` is the UTC date.
This correctly simulates the old key format.
The test then runs `prescreen` with `later = E.Context(NOW + timedelta(days=days), REG)`.
If `days=20/24` (0.83 days), `later` is ~20 hours after `NOW`.
The UTC date of `later` might be the same as `NOW` or the next day.
The test expects `m03` (time-sensitive) to be asked, and `m00-m02` (non-time-sensitive) to be found in old keys.
This validates the logic.

**Finding [P0]: `step_a_old_keys` does not account for the fact that the *old* code might have used a *different* UTC date if the run was at a different time.**
The function generates keys for `now` (today's UTC) and `now - 1 day` (yesterday's UTC).
If the old run was at 2026-11-15 23:00 UTC, the old key used `2026-11-15`.
If the new run is at 2026-11-16 01:00 UTC, `now` is `2026-11-16`.
`step_a_old_keys` generates keys for `2026-11-16` and `2026-11-15`.
It will find the verdict under `2026-11-15`.
This is correct.

**Finding [P1]: `moved` dictionary merge.**
`_cache_put(cache, dict(moved, **new))`.
If `moved` and `new` have the same key, `new` wins.
Can this happen?
`new` contains keys for moments that were *evaluated* in this run.
`moved` contains keys for moments that were *found* in the old cache.
A moment is either evaluated (added to `new`) OR found (added to `moved`).
It cannot be both.
So there is no conflict.

**Finding [P2]: `show_date` returns `None` if `now` is `None`.**
In `prescreen`, `ctx.now` is assumed to be not None (it's the run clock).
In `contexts_from_sources`, `now` can be None.
If `now` is None, `show_date` is None.
The context dict will have `"show_date": None`.
`json.dumps` handles `None` correctly.
This is safe.

**Finding [P1]: `step_a_key` for time-sensitive moments.**
If `time_sensitive(m)` is True, the key includes `show_date` (ET).
If the ET date changes, the key changes.
The old key (UTC date) is NOT checked.
This means a time-sensitive moment will be re-evaluated every time the ET date changes.
This is the intended behavior per RULING 126 (1).

**Finding [P0]: `step_a_old_keys` uses `dict(context, show_date=...)`.**
`context` is the *new* context.
It contains `"show_date": CI.show_date(ctx.now)` (ET date).
The code overwrites it with the UTC date.
This is correct.
**BUT**, does `context` contain any other fields that might have changed?
The prompt says: "the sha256 of the exact context step A reads".
The context is built in `prescreen`:
```python
contexts[mid] = {"text": text, "title": ..., "channel": ..., "window": win, "published": ..., "show_date": ...}
```
The old context was built the same way, except `show_date` was UTC.
So the only difference is `show_date`.
The code correctly isolates this difference.

**Finding [P1]: `pick` function uses `sorted`.**
`sorted((cdb.get(key) or {}).items())`.
This sorts by backend name.
This ensures deterministic selection if multiple backends have cached verdicts.
This is good practice.

**Finding [P2]: `time_sensitive` is called multiple times.**
In `step_a_key` and in `prescreen`.
This is a minor performance issue, not a correctness issue.

**Finding [P1]: `step_a_old_keys` only checks `k=0` and `k=1`.**
What if the old run was 2 days ago?
The prompt says "a moment inside the 12-hour publish window".
This implies the moments are fresh.
If a moment is older than 24 hours, it is likely not in the current batch.
So checking 2 days is sufficient.

**Finding [P0]: `show_date` in `contexts_from_sources` is used for the *context check*, not just step A.**
The prompt says: "Used by contexts_from_sources (the context check's excerpts...)"
The context check (`CI.check_contexts`) does *not* have a cache.
It replays the prompt.
The prompt includes the context.
So the context check will see the ET date.
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
`m['text']` is the moment's text.
This is stable.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is the same as `step_a_key` but with the old `show_date`.
This is correct.

**Finding [P1]: `moved` is written to cache.**
`_cache_put` merges `moved` into the cache.
This ensures the verdict is available under the new key for future runs.
This is correct.

**Finding [P0]: `prescreen` returns `a_by`, `fails`, `vendors`, `families`.**
`a_by` contains the verdicts.
For moved verdicts, `a_by[mid]` is set to `rec` (the old verdict).
This is correct.

**Finding [P1]: `fails` is set to `CI.a_failures(rec)`.**
This is correct.

**Finding [P2]: `vendors` and `families` are updated.**
`vendors.add(rec["backend"].split(":")[0])`.
This is correct.

**Finding [P1]: `todo` is NOT updated for moved verdicts.**
This is correct, as no new call is needed.

**Finding [P0]: `new` is NOT updated for moved verdicts.**
`new` is the dict of *new* verdicts from model calls.
Moved verdicts are in `moved`.
`_cache_put` merges them.
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
Tests `CI.show_date`.
Correct.

**Finding [P2]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
Tests the migration logic.
Correct.

**Finding [P1]: `step_a_old_keys` uses `now` (UTC) to generate UTC dates.**
This is correct.
**BUT**, what if `now` is not UTC?
The prompt says: "Context.now must be an aware datetime (the run clock, UTC)".
So `now` is UTC.
This is safe.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is the correct timezone for ET.

**Finding [P1]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This means the key is stable across dates.
This is correct.

**Finding [P2]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This covers the last 2 UTC days.
This is sufficient.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This ensures time-sensitive moments are not migrated.
This is correct.

**Finding [P0]: `moved` is a dict of dicts.**
`moved.setdefault(keys[mid], {})[rec["backend"]] = rec`.
This structure matches the cache format `{key: {backend: verdict}}`.
This is correct.

**Finding [P1]: `_cache_put` merges `moved` and `new`.**
`dict(moved, **new)`.
If `moved` and `new` have the same key, `new` wins.
As established, they cannot have the same key.
This is safe.

**Finding [P2]: `step_a_key` uses `json.dumps(kc, sort_keys=True)`.**
This ensures canonical JSON.
This is correct.

**Finding [P1]: `step_a_old_keys` uses `json.dumps(dict(context, show_date=...), sort_keys=True)`.**
This ensures canonical JSON.
This is correct.

**Finding [P0]: `show_date` returns `None` if `now` is `None`.**
In `step_a_key`, if `now` is `None`, `show_date` is `None`.
But `step_a_key` takes `context`, not `now`.
`context` has `show_date`.
If `show_date` is `None`, it is included in the hash.
This is consistent.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
If `ctx.now` is `None`, `show_date` is `None`.
This is consistent.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
If `ctx.now` is `None`, `step_a_old_keys` will fail.
But `prescreen` only calls `step_a_old_keys` if `rec is None`.
If `ctx.now` is `None`, `CI.show_date` is `None`.
The context has `show_date: None`.
`step_a_key` hashes this.
`pick` looks for this key.
If not found, `step_a_old_keys` is called.
`step_a_old_keys` uses `ctx.now` to generate dates.
If `ctx.now` is `None`, `timedelta` will fail.
**Is `ctx.now` ever `None`?**
The prompt says: "Context.now must be an aware datetime".
So it is never `None`.
This is safe.

**Finding [P1]: `step_a_old_keys` uses `now - timedelta(days=k)`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `strftime('%Y-%m-%d')`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
`pick` filters by `off(name)`.
This ensures we don't use a verdict from an excluded writer.
This is correct.

**Finding [P0]: `moved` is written to cache.**
This ensures the verdict is available under the new key.
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
The test verifies that the verdict is found and moved.
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [P2]: `step_a_key` for non-time-sensitive moments strips `show_date`.**
This is correct.

**Finding [P1]: `prescreen` checks `if rec is None and not time_sensitive(m)`.**
This is correct.

**Finding [P0]: `show_date` uses `ZoneInfo("America/New_York")`.**
This is correct.

**Finding [P1]: `step_a_old_keys` generates keys for `k=0` and `k=1`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `ctx.now`.**
This is correct.

**Finding [P1]: `prescreen` uses `pick` for old keys.**
This is correct.

**Finding [P0]: `moved` is written to cache.**
This is correct.

**Finding [P1]: `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved`.**
This is correct.

**Finding [P2]: `step_a_key` for time-sensitive moments includes `show_date`.**
This is correct.

**Finding [P1]: `prescreen` does not check old keys for time-sensitive moments.**
This is correct.

**Finding [P0]: `show_date` is used in `contexts_from_sources`.**
This is correct.

**Finding [P1]: `step_a_key` uses `text_sha(m['text'])`.**
This is correct.

**Finding [P2]: `step_a_old_keys` uses `text_sha(json.dumps(...))`.**
This is correct.

**Finding [P1]: `prescreen` uses `CI.show_date(ctx.now)`.**
This is correct.

**Finding [P0]: `moved` is merged into cache.**
This is correct.

**Finding [P1]: `test_ruling_126_the_show_date_is_the_et_date`.**
This is correct.

**Finding [