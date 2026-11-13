# qwen3.8-27b (qwen/qwen3.8-27b) 41 s finish=stop usage in 17498 / out 2491 usd~0.090 (upper-bound price)

# Code Audit: pp-selectid-1420 (Ruling 66 Implementation)

## P0 Findings

**1. `pipeline/candidates.py:101` — Timezone Naive/Naive Comparison Crash**
The `due()` function compares `e["until"]` (an ISO string) against `now` (a `datetime` object).
```python
elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
```
`_at()` uses `datetime.fromisoformat`. If the registry was seeded by a process using naive datetimes (e.g., `datetime.utcnow()` or local time without tzinfo), `e["until"]` will be naive. If `now` is timezone-aware (as in `proof_ledger.py` where `now` is likely UTC-aware), this raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
*Scenario:* A candidate enters "resting" state. 6 hours later, the build runs. If the `now` passed to `run_due` is aware but the stored `until` is naive (or vice versa), the pipeline crashes with an unhandled exception, violating **M12 FAIL CLOSED** (it should reject/hold, not crash the driver).
*Fix:* Ensure `_at()` and the `now` parameter are consistently timezone-aware (e.g., force `tzinfo=timezone.utc` if missing).

**2. `tests/package/proof_ledger.py:296-299` — Silent "Clip" Classification for Infrastructure Errors**
```python
try:
    with open(os.path.join(REPO, e["source"], "package.json")) as f:
        c = PK.load_candidate(json.load(f), e["index"], source=e["source"])
except (OSError, ValueError, KeyError, TypeError) as ex:
    return None, "clip", f"it cannot be rebuilt from its record ({type(ex).__name__}: {ex})", 0
```
If the source file is missing (`OSError`) or the JSON is corrupt, the candidate is marked as `"clip"` (closed for good). Ruling 66 states a candidate is closed for good when a *clip* is delivered, ages out, or fails a gate. An infrastructure error (missing file) is not a clip failure.
*Scenario:* A transient disk I/O error or a race condition where the file is being written causes the candidate to be permanently closed. This violates the spirit of **LAW 20** (never change what a check accepts to make a render pass) and **M12** (missing data should reject/hold, not produce a definitive "closed" state that loses the candidate).
*Fix:* Distinguish between "clip no longer valid" (ValueError from `load_candidate` logic) and "infrastructure failure" (OSError). Infrastructure failures should likely raise or mark as "inconclusive" rather than "clip".

## P1 Findings

**3. `pipeline/candidates.py:103` — Sorting Logic Ambiguity with Mixed States**
```python
return sorted(out, key=lambda x: (str(x[1].get("found_at") or ""), x[1]["source"], x[1]["index"]), reverse=True)
```
The sort key is `(found_at, source, index)`.
*Issue:* `found_at` is a string. ISO 8601 strings sort lexicographically correctly *only if* they are in the same format and timezone. If `found_at` is missing (`None`), it becomes `""`, which sorts *before* any date string. With `reverse=True`, `""` (missing date) will be sorted *last* (oldest). This is likely correct (unknown age = try last), but if `found_at` is present in some records and missing in others, the "newest first" guarantee relies on string comparison.
*More Critical:* The `source` and `index` are used as tie-breakers. If two candidates have the exact same `found_at` (unlikely but possible if seeded in the same second), they are sorted by `source` (path) and `index`. This is deterministic but arbitrary. The ruling says "newest first". If "newest" is strictly by time, this is fine. However, if `found_at` is not set for legacy records (see `seed` function, line 70: `at = record.get("now")`), and `now` is missing, `found_at` is `None`.
*Scenario:* Legacy records without `now` get `found_at=None`. They sort last. This is acceptable, but the code should explicitly handle `None` to avoid `str(None)` = `"None"` which might sort unexpectedly against ISO dates (e.g., `"None"` > `"2026..."` because 'N' > '2').
*Fix:* Use a robust sort key that handles `None` explicitly, e.g., `key=lambda x: (x[1].get("found_at") or "0000-00-00T00:00:00", ...)`.

**4. `pipeline/package.py:197-200` — "Line" vs "Clip" Classification Edge Case**
```python
out["candidate"]["class"] = (
    "package" if out["packages"] else
    "budget" if not t_ or out.get("budget_stop") or t_.get("budget") else
    "line" if t_.get("medley_ok") and t_.get("attempts") and not t_.get("relined") else "clip")
```
*Issue:* The condition for `"line"` requires `t_.get("attempts")`. What is `attempts`? It is not defined in the diff. If `attempts` is 0 or missing, a candidate that passed the medley (`medley_ok=True`) but failed the write gates (no package) will be classified as `"clip"` instead of `"line"`.
*Scenario:* A candidate's clips pass the medley. The write fails. If `attempts` is not set to a truthy value in the `tried` record, the candidate is closed for good (`"clip"`) instead of resting for 6 hours (`"line"`). This violates Ruling 66 (14:02): "a candidate whose clips still pass but whose LINE fails again... is CLOSED for 6 hours".
*Fix:* Verify that `attempts` is always set to a truthy value when a write is attempted. If not, the condition should be `t_.get("medley_ok") and not t_.get("relined")` (assuming `medley_ok` implies the clips passed, and the failure is in the line/write stage).

**5. `tests/package/proof_ledger.py:304` — Budget Accounting in `try_one`**
```python
o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
```
`left` is the number of judged line-ups remaining. `PK.build` is called with `lineups=left`.
*Issue:* Inside `PK.build`, the `lineups` parameter controls the budget for *judging* line-ups. If the candidate fails, does it consume a "judged line-up" slot? The `try_one` function returns `judged` from `o.get("search").get("lineups", 0)`.
*Scenario:* If a candidate fails its clips-alone verdict (which is free, per ruling), does it consume a slot from the 8? The ruling says "recorded verdicts free". If `load_candidate` replays the recorded verdict, `search.lineups` should be 0. If it re-judges, it should be 1. The code passes `lineups=left` to `build`. If `build` consumes 1 slot for the candidate, `left` decreases. This seems correct. However, if the candidate fails *before* judging (e.g., clip missing), `judged` is 0. This is also correct.
*Potential Bug:* If `PK.build` with `candidate=c` *always* consumes 1 slot from the `lineups` budget even if the verdict is served from cache, the accounting might be off. The diff does not show `PK.build`'s internal handling of `lineups` for candidates. **Uncertain.**

## P2 Findings

**6. `pipeline/candidates.py:48` — History Entry Truncation**
```python
"why": str(why or "")[:300]
```
Truncating the reason to 300 chars is fine for storage, but if the reason is critical for debugging (e.g., a long stack trace), it might be lost. Not a functional bug.

**7. `tests/package/proof_ledger.py:325` — Registry Seeding After Write**
```python
CA.seed(reg, json.loads(json.dumps(res, default=str)), name)
```
The registry is seeded with the *current* build's record. This ensures new candidates from this build are added.
*Issue:* `json.loads(json.dumps(res, default=str))` is a deep copy. This is necessary to avoid mutating `res`. However, `res` contains `datetime` objects? `default=str` converts them to strings. `CA.seed` expects `record.get("now")` to be an ISO string. If `res["now"]` is a `datetime` object, `default=str` converts it to a string like `"2026-11-13 19:00:00+00:00"`. `CA._at` uses `fromisoformat`, which handles this.
*Scenario:* If `res["now"]` is `None`, `default=str` makes it `"None"`. `CA._at("None")` raises `ValueError`. This would crash the driver *after* the package is written, leaving the registry unsaved.
*Fix:* Ensure `res["now"]` is always a valid ISO string or `None` is handled in `CA.seed`.

**8. `pipeline/candidates.py:57` — `until` Calculation**
```python
entry["state"], entry["until"] = "resting", (_at(at) + timedelta(hours=RESTING_H)).isoformat()
```
`at` is an ISO string. `_at(at)` parses it. If `at` is naive, `until` is naive. If `at` is aware, `until` is aware. Consistency depends on the input `at`. See P0-1.

## SHIP: NO

**Conditions for Ship:**
1.  **Fix P0-1:** Ensure timezone consistency in `candidates.py` (`_at` and `now` must be both aware or both naive).
2.  **Fix P0-2:** Distinguish infrastructure errors (OSError) from clip failures in `proof_ledger.py` `try_one`. Infrastructure errors should not close the candidate for good.
3.  **Verify P1-4:** Confirm that `t_.get("attempts")` is always truthy when a write is attempted. If not, adjust the classification logic in `package.py`.
4.  **Verify P1-5:** Confirm that `PK.build` with `candidate=c` does not consume a judged line-up slot if the verdict is served from cache.