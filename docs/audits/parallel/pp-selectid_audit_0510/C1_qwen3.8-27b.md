# qwen3.8-27b (qwen/qwen3.8-27b) 241 s finish=stop usage in 15267 / out 3742 usd~0.102 (upper-bound price)

# Audit: pp-selectid-0510 (Ruling 41: Line-up Search)

## P0 Findings

**1. `pipeline/package.py` (approx. line 158 in diff / `build` loop): Infinite Loop on Swap Failure**
The `while` loop condition is `while total < lineups ...`. Inside the loop, when `medley` fails (`ok_m` is False), the code calls `swap_lineup`.
- If `swap_lineup` returns `(None, None)` (no valid swap found), the code sets `rec["why"]` and executes `continue`.
- Crucially, `total` is **not** incremented in this path (it is only incremented at line 190, *after* a valid `segs` is established and before `medley` is called).
- The `dropped` set is updated with `weak`, but if `swap_lineup` fails, the code does **not** fall back to `lineup_for` to generate a *new* line-up from the remaining pool. It simply `continue`s.
- On the next iteration, `swapped` is `None`, so it calls `lineup_for(angle, cleared, frozenset(dropped | doomed), ...)`.
- **The Bug:** If `lineup_for` returns the **exact same** line-up as before (e.g., because the "weak" moments were not actually excluded from the pool in a way that changes the selection, or if `lineup_for`'s internal logic doesn't strictly respect `dropped` for the *hook* or if the pool is small), the loop will repeat the same `medley` call, fail again, and `continue` again.
- **Wait, let's look closer at `lineup_for` usage:**
  - Line 176: `segs, exception = lineup_for(..., frozenset(dropped | doomed), ...)`
  - If `swap_lineup` fails, `dropped` contains the `weak` moments.
  - If `lineup_for` respects `dropped`, it *should* pick different moments.
  - **However**, consider the case where `weak` contains the **Hook**.
  - `swap_lineup` tries to swap the hook. If it fails, `dropped` now contains the old Hook.
  - Next iteration: `lineup_for` is called with `dropped` containing the old Hook. It picks a new Hook.
  - If the new Hook also fails `medley`, `weak` contains the new Hook. `swap_lineup` tries to swap it.
  - If `swap_lineup` fails again, `dropped` contains both Hooks.
  - This seems safe *if* `lineup_for` always picks a different moment when the previous one is in `dropped`.
  - **BUT**, look at the `continue` path when `swap_lineup` returns `None`.
  - The code does:
    ```python
    swapped, swaps = swap_lineup(...)
    rec["why"] = ...
    continue
    ```
  - It does **not** increment `total`.
  - It does **not** break.
  - It relies on the next `lineup_for` call to produce a *different* line-up.
  - If `lineup_for` returns `None` (no line-up possible), the code breaks (line 187-188).
  - If `lineup_for` returns a line-up, `total` is incremented (line 190).
  - **Is there a scenario where `lineup_for` returns the same line-up?**
    - `lineup_for` takes `dropped` as a parameter. It should exclude those moments.
    - If the pool is exhausted, it returns `None`.
    - If the pool is not exhausted, it picks the best available.
    - So, it *should* pick a different line-up.
    - **However**, there is a subtle issue: `swap_lineup` uses `pool` (the `cleared` dict). `lineup_for` also uses `cleared`.
    - If `swap_lineup` fails because no *valid* swap exists (e.g., all other hooks are ineligible, or all other clips are ineligible), but `lineup_for` *can* still form a line-up (perhaps by changing the *order* or picking a different combination that `swap_lineup` didn't consider because it only swaps *weak* spots), then `lineup_for` will return a new line-up.
    - **The Risk:** If `lineup_for` returns a line-up that is *identical* to the one just failed, we loop.
    - Can `lineup_for` return the same line-up? Only if the `dropped` set does not effectively change the selection.
    - `dropped` is updated with `weak`. `weak` contains the moments that failed.
    - So the failed moments are now in `dropped`.
    - `lineup_for` excludes `dropped`.
    - Therefore, the new line-up *cannot* contain the failed moments.
    - So the line-up *must* be different.
    - **Conclusion:** The loop *should* terminate because the state space of possible line-ups is finite and we are strictly excluding failed moments from future consideration via `dropped`.
    - **Wait**, does `lineup_for` *always* exclude `dropped`?
      - Line 176: `lineup_for(angle, cleared, frozenset(dropped | doomed), ...)`
      - Yes.
    - **So, is it safe?**
      - If `lineup_for` returns `None`, we break.
      - If it returns a line-up, it's different from the last one (because the last one's weak moments are now in `dropped`).
      - So `total` will increment on the next successful `lineup_for` call.
      - **However**, what if `lineup_for` returns a line-up, but `medley` fails, and `swap_lineup` fails, and `lineup_for` returns *another* line-up, and `medley` fails...
      - This is the intended search.
      - **The P0 is actually a P1/P2 risk of inefficiency, not an infinite loop, UNLESS `lineup_for` has a bug where it ignores `dropped` for some moments.**
      - Let's assume `lineup_for` is correct.
      - **BUT**, there is a **P0** in the **Budget Check**.

**2. `pipeline/package.py` (approx. line 159 in diff): `over_budget` Check Placement**
- `over_budget(ai)` is called at the start of the `while` loop.
- If `over_budget` returns a stop record, it `break`s.
- This is correct for the Search Budget.
- **However**, `package_over(line)` is called *inside* the write loop (line 220).
- `line` is set at line 191: `line = (time.time(), _spent(spend))`.
- This is *after* `total += 1` and *before* `medley` is called.
- **The Issue:** The `package_over` check is only performed *if* the `medley` call passes (`ok_m` is True).
- If `medley` fails, we `continue` to the next line-up.
- The `package_over` check is *not* performed for the failed line-up.
- Is this a problem?
  - Ruling 41 says: "Ruling 5's budget... is per PACKAGE delivered".
  - A failed line-up is not a delivered package.
  - So, not checking `package_over` for a failed line-up is correct.
  - **However**, the *time* spent on the failed `medley` call *is* part of the search time.
  - The `over_budget` check (Search Budget) *is* performed at the start of the next iteration.
  - So the search time is accounted for.
  - **This seems correct.**

**3. `pipeline/package.py` (approx. line 190 in diff): `total` Increment Logic**
- `total` is incremented *only* when a line-up is actually judged by `medley`.
- If `lineup_for` returns `None`, we break.
- If `lineup_for` returns a line-up, `total` is incremented.
- If `medley` fails, and `swap_lineup` fails, we `continue`.
- On the next iteration, `lineup_for` is called again.
- If it returns a line-up, `total` is incremented again.
- **This is correct.** The limit is on *judged* line-ups.

**4. `pipeline/package.py` (approx. line 200 in diff): `weak` Set Construction**
- `weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items() if lb in by_lab and x < COHERENCE_MIN}`
- This includes the Hook if `lb` is "hook" and its rating is low.
- **Wait**, does `med.get("clips")` include the Hook?
  - The docstring for `medley` (not provided, but implied) says it rates "each segment".
  - The test `test_the_build_swaps_a_low_rated_hook...` uses `{"hook": 3}` in the `medley` return value.
  - So yes, the Hook is in `med["clips"]`.
  - **However**, the key is `lb`.
  - In the test, `med` is `(False, [], {"hook": 3}, Rig.LINE)`.
  - So `med["clips"]` is `{"hook": 3}`.
  - `by_lab` maps labels to segments.
  - If the Hook's label is "hook", then `by_lab["hook"]` is the Hook segment.
  - So `weak` will contain the Hook's `moment_id`.
  - **This is correct.**

**5. `pipeline/package.py` (approx. line 208 in diff): `swap_lineup` Call**
- `swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed))`
- `avoid` is `frozenset(dropped | doomed)`.
- **The Issue:** `dropped` has *just* been updated with `weak` (line 206: `dropped |= weak`).
- So `avoid` contains the `weak` moments.
- `swap_lineup` excludes `avoid` from the `free` pool.
- This is correct: we don't want to swap a weak moment for *itself* or for another moment that was already dropped.
- **However**, `swap_lineup` also excludes `used` (the current line-up's moments).
- So it swaps the weak moments for *new* moments from the pool.
- **This is correct.**

**6. `pipeline/package.py` (approx. line 213 in diff): `continue` after Swap Failure**
- If `swapped` is `None`, we `continue`.
- As analyzed in P0-1, this relies on `lineup_for` picking a different line-up next time.
- **Is there a case where `lineup_for` picks the *same* line-up?**
  - Only if `dropped` does not change the selection.
  - But `dropped` *does* change (it now contains `weak`).
  - So `lineup_for` *must* pick a different line-up (or `None`).
  - **So, no infinite loop.**

**7. `pipeline/package.py` (approx. line 231 in diff): `rec["why"]` for Failed Writes**
- `if not out["packages"] and not rec.get("why") and not rec.get("result"):`
- This sets `rec["why"]` if the line-up passed `medley` but all writes failed.
- **This is correct.**

## P1 Findings

**1. `pipeline/package.py` (approx. line 158 in diff): `total` vs `lineups` Scope**
- `lineups` is the parameter (default `LINEUPS_PER_BUILD = 8`).
- `total` is the counter.
- The loop is `while total < lineups ...`.
- **The Issue:** `total` is incremented *only* when a line-up is judged.
- If `lineup_for` returns `None`, we break.
- If `lineup_for` returns a line-up, `total` is incremented.
- **This is correct.**

**2. `pipeline/package.py` (approx. line 191 in diff): `line` Variable Scope**
- `line = (time.time(), _spent(spend))` is set inside the `while` loop.
- It is used in `package_over(line)` inside the write loop.
- **The Issue:** If the write loop is entered, `line` is defined.
- If the write loop is *not* entered (e.g., `medley` failed), `line` is not used.
- **This is correct.**

**3. `pipeline/package.py` (approx. line 220 in diff): `package_over` Check**
- `w_over = package_over(line)`
- If `w_over` is not `None`, we `break` the write loop.
- **The Issue:** We `break` the write loop, but we do *not* `break` the `while` loop.
- We `continue` to the next line-up.
- **Is this correct?**
  - Ruling 41: "Ruling 5's budget... is per PACKAGE delivered".
  - If the package budget is exceeded, we stop *this* line-up's writes.
  - But we can try the *next* line-up (which has its own package budget).
  - **This is correct.**

**4. `pipeline/package.py` (approx. line 237 in diff): `break` Conditions**
- `if out["packages"] or out.get("budget_stop") or over_budget(ai): break`
- This breaks the `while` loop if a package is found, or the search budget is exceeded.
- **This is correct.**

## P2 Findings

**1. `pipeline/package.py` (approx. line 240 in diff): `out["search"]` Reporting**
- `out["search"]` is set *after* the `while` loop.
- It reports `total`, `lineups`, `usd_reported`, `usd_estimate`, `seconds`.
- **This is correct.**

**2. `tests/package/test_medley.py` (approx. line 281 in diff): Test for Package Budget**
- `rig.spend = lambda: (0.0, 1.6) if rig.medley_calls else (0.0, 0.0)`
- This simulates a spend of $1.60 *after* the first `medley` call.
- The test expects `out["tried"][0]["why"]` to contain "per package delivered".
- **This is correct.**

## SHIP: Yes with Conditions

**Conditions:**
1. **Verify `lineup_for` Respects `dropped`:** Ensure that `lineup_for` strictly excludes all moments in the `dropped` set from its selection. If it does not, the `continue` path after a failed `swap_lineup` could lead to an infinite loop (re-judging the same line-up).
2. **Verify `medley` Includes Hook in `clips`:** Ensure that the `medley` function returns the Hook's rating in the `clips` dict with the key "hook" (or whatever label is used in `by_lab`). If the Hook is not in `med["clips"]`, it will never be added to `weak`, and the "swap the hook" logic will never trigger.
3. **Verify `by_lab` Mapping:** Ensure that `by_lab` correctly maps the labels in `med["clips"]` to the segments in `segs`. If the labels do not match, `weak` will be empty or incorrect.

**Summary:**
The diff implements Ruling 41 correctly in terms of logic flow. The separation of Search Budget (build-wide) and Package Budget (per-line-up) is clear. The swap logic is sound. The main risk is an infinite loop if `lineup_for` does not strictly respect the `dropped` set, but this is a pre-existing dependency, not a new bug introduced by this diff. The tests cover the key scenarios.