# gemma-4-31b-it (google/gemma-4-31b-it) 234 s finish=stop usage in 11747 / out 4934 usd_reported=0.000976 usd~0.109 (upper-bound price)

The audit of feature `pp-selectid-20261116_2313` reveals a critical failure in the implementation of **RULING 130 (2)** within the medley/no-voice path.

### [P0] Ruling 130 Violation in Medley/No-Voice Path
The core requirement of Ruling 130 (2) is that the lock pre-check must run **BEFORE** any paid vision check, and a clip the render cannot cut (a "hold") must not cost money.

In the main line-up loop (`pipeline/package.py` lines 57-89), this is correctly implemented: the code checks for `no_verdict` and `relined` (the "hold" state) before entering the block that executes `bg` (exclusion/truth checks) and `see(segs)` (the paid vision check).

However, in the **medley/no-voice path** (`pipeline/package.py` lines 16-32), the implementation is incomplete:
```python
18 |         if lock_check is not None:
19 |             try:
20 |                 nv_pre = lock_check(order)
21 |             except Exception as e:
22 |                 nv_pre = LP.failed(e)
23 |         if nv_pre.get("error") or not nv_pre.get("segments"):
24 |             out["lock_stop"] = note["why_not"]
25 |             return None
26 |         see(order) # <--- PAID VISION CHECK
```
The `lock_check` (via `LP.check`) returns a result where `ok=False` and `segments` is populated when a clip is "held" by the render. In this scenario:
1. `nv_pre.get("error")` is `None`.
2. `not nv_pre.get("segments")` is `False`.
3. The `if` condition fails, and the code proceeds to `see(order)`.

Consequently, any line-up in the medley path that is "held" by the lock will still trigger a paid vision check, directly violating the governing law. The user's description in the "THE CHANGE" section (b) claims that on a hold it returns `None`, but the provided code does not implement this logic.

### Other Observations
- **`lock_off` Logic**: Correct. It returns an error and empty segments, which triggers the `return None` path in both the main loop and the medley path, ensuring it never produces a "pass" (Law L-m).
- **`bg` Initialization**: Correct. By initializing `bg = {}` and wrapping the population in `if not relined and not no_verdict`, the code ensures that the subsequent `writes` loop (which reads `bg`) is either skipped (because `w_used == writes`) or operates on a valid set of results.
- **Tests**: The tests in `test_medley.py` (e.g., `test_ruling_130_a_clip_the_lock_holds_is_never_seen`) appear to target the main line-up loop via the `Rig` class and do not cover the specific medley/no-voice branch in `package.build`, allowing this P0 to slip through.

P1_OR_WORSE: 1