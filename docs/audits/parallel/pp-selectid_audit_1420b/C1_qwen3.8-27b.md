# qwen3.8-27b (qwen/qwen3.8-27b) 48 s finish=stop usage in 7910 / out 2182 usd~0.056 (upper-bound price)

# Audit: pp-selectid-1420b (C1_STEP.diff)

## Findings

### P1: `run_due` can return a negative `lineups` count, breaking the driver's "no line-ups left" logic
**File:** `pipeline/candidates.py` (diff lines 21–24)

The F2 fix clamps `judged` to `lineups` when it is out of range, but it does **not** clamp the *result* of the subtraction. If `try_one` returns a negative `judged` (e.g., `-1`), the code executes:
```python
if not 0 <= judged <= lineups:
    why, judged = f"{why} (...)", lineups
lineups -= judged
```
Wait, looking closer at the diff:
```python
judged = int(judged or 0)
if not 0 <= judged <= lineups:                            # audit 1420 C2: never past the judged line-ups
    why, judged = f"{why} (it reported {judged} judged line-ups of {lineups} left: all are charged)", lineups
lineups -= judged
```
If `judged` is negative (e.g., `-5`), the condition `0 <= -5` is `False`, so it enters the `if` block. It sets `judged = lineups` (which is positive, e.g., 8). Then `lineups -= 8`. This is safe.

However, consider the case where `lineups` is already 0.
If `lineups` is 0, and `try_one` returns `judged=0`.
`0 <= 0 <= 0` is True. `lineups -= 0` -> 0. Safe.

What if `try_one` returns `judged=1` when `lineups=0`?
`0 <= 1 <= 0` is False.
`judged` becomes `lineups` (0).
`lineups -= 0` -> 0. Safe.

The logic `judged = lineups` effectively caps the charge at the remaining budget. This seems robust against negative or excessive `judged` values from `try_one`.

**Re-evaluating P1:** Is there a scenario where `lineups` becomes negative?
Only if `judged` > `lineups` AND the clamp didn't happen. But the clamp *is* the assignment `judged = lineups`. So `lineups` can never decrease by more than its current value. `lineups` remains non-negative.

**Correction:** The P1 finding is invalid. The clamp logic is sound.

### P2: `proof_ledger.py` `--from-candidate` path does not update the registry state for the candidate
**File:** `tests/package/proof_ledger.py` (diff lines 44–47 vs 83–85)

In the `--from-candidate` branch (lines 39–47), the code constructs `res["candidate_tries"]` manually. It does **not** call `CA.outcome` on the registry entry *before* the final guarded block.
However, in the final guarded block (lines 82–92), it *does* call `CA.outcome` if `cand is not None` and the key exists in `reg["candidates"]`.
```python
if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:
    CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
               res["candidate"].get("result"))
```
This looks correct. The state is updated in the guarded block.

**Potential Issue:** The `res["candidate_tries"]` entry in the `--from-candidate` path (line 47) uses:
```python
"judged": (res.get("search") or {}).get("lineups", 0)
```
In the normal `run_due` path, `judged` comes from the `try_one` return value, which is validated/clamped. Here, it comes from `res["search"]["lineups"]`. If `package.build` returns a `search` dict with a `lineups` value that is inconsistent with the actual budget spent (e.g., it reports 0 but actually consumed 3), the `candidate_tries` record will be inaccurate. However, this is a *record* of what the build *reported*, not the registry state. The registry state is driven by `CA.outcome` which uses `res["candidate"]["class"]`. The `judged` count in `candidate_tries` is informational for the audit trail. This is acceptable, but worth noting that the `judged` field in `candidate_tries` for `--from-candidate` is not subject to the F2 clamp logic.

### P2: `due()` raises on malformed `found_at`, but `run_due` does not catch it
**File:** `pipeline/candidates.py` (diff lines 10–12)

The F1 fix states: "A malformed `found_at` now raises in `due()`".
`due()` is called by `run_due()`.
`run_due()` is called by `proof_ledger.main()`.
In `proof_ledger.main()`, the call to `CA.run_due` is **not** inside a `try/except` block.
```python
res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
```
If `due()` raises a `ValueError` (or similar) due to a malformed timestamp in the registry, the driver will crash *before* writing `package.json`.
The prompt says: "the driver already evaluates in its refusal block (exit 2, nothing written)".
Does the driver have a refusal block that catches exceptions from `run_due`?
Looking at the diff, `run_due` is called at line 64. There is no `try/except` around it in the provided diff.
If the registry contains a malformed `found_at` (e.g., from a previous bug or manual edit), `due()` will raise, `run_due` will propagate it, and `main()` will crash.
This violates M12 (Fail Closed: missing data... rejects; it never produces a pass) in the sense that it crashes rather than producing a controlled failure record. However, crashing *before* writing is safer than writing a corrupt record.
But the prompt says "the driver already evaluates in its refusal block". I cannot see this refusal block in the diff. If it exists in the unchanged code, it might catch `Exception`. If it only catches specific exceptions, a `ValueError` from `_at()` might slip through.
**Assumption:** The existing driver code has a broad `try/except` around the main logic that handles crashes by exiting 2. If so, this is acceptable. If not, this is a P1. Given the instruction "Only state what you can verify from the diff", I cannot verify the existence of the refusal block. I will flag this as a P2 risk.

### P2: `test_due_sorts_by_time_not_by_text` uses `T0` for all seeds
**File:** `tests/package/test_candidates.py` (diff lines 104–109)

```python
CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "utc")                              # 19:00Z
CA.seed(reg, dict(record(T0, [t(["d", "e", "f"])]), now="2026-11-13T14:30:00-05:00"), "et")   # 19:30Z
CA.seed(reg, dict(record(T0, [t(["g", "h", "i"])]), now=None), "none")             # no time: the oldest
```
The `record` function likely sets `found_at` to `T0` by default.
The second seed overrides `now` with a specific ISO string.
The third seed sets `now=None`.
The test asserts the order: `["d+e+f", "a+b+c", "g+h+i"]`.
`d+e+f` has `found_at` = 19:30Z (from the override).
`a+b+c` has `found_at` = T0 (19:00Z).
`g+h+i` has `found_at` = None (oldest).
This correctly tests the F1 logic.

### P2: `run_due` `why` string truncation
**File:** `pipeline/candidates.py` (diff line 23)

```python
why, judged = f"{why} (it reported {judged} judged line-ups of {lineups} left: all are charged)", lineups
```
The original `why` is appended to. If `why` is very long, the new string will be longer.
Later, in `tries.append`:
```python
"why": str(why or "")[:300]
```
It is truncated to 300 chars. This is consistent with existing behavior.

## SHIP: yes with conditions

**Conditions:**
1. Verify that the existing `proof_ledger.main()` driver has a top-level exception handler that catches `ValueError` (or `Exception`) from `CA.run_due` and exits with code 2 without writing files. If it does not, the malformed `found_at` case will crash the process ungracefully (P1).
2. Confirm that `res["search"]["lineups"]` in the `--from-candidate` path is a reliable indicator of the budget consumed. If `package.build` can return a `search` dict with an incorrect `lineups` count, the `candidate_tries` audit trail will be misleading (P2).