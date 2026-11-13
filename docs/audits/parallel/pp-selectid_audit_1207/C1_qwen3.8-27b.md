# qwen3.8-27b (qwen/qwen3.8-27b) 153 s finish=stop usage in 27147 / out 7095 usd~0.188 (upper-bound price)

# Protocol Pulse — Code Audit: pp-selectid-1207 (Rulings 61–64)

## P0 Findings (Blockers)

**1. `pipeline/package.py` (approx. line 380-381): `IndexError` on `medley` failure**
In the main build loop, `bad_pairs` is updated immediately after `medley()` returns, regardless of whether the verdict was `measured`.
```python
bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
              for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}
```
If `medley()` fails (e.g., out-of-contract JSON, model error), `med.get("flagged")` is `None` (per the error return path: `return False, {"error": ..., "measured": False, "flagged": None}`). The loop iterates over `[]`, so this specific line is safe. **However**, look at the logic flow:
If `ok_m` is `False` and `med.get("measured")` is `False`, the code proceeds to the `if not ok_m:` block. Inside that block, it checks `if not med.get("measured") or not weak: ... break`. This is safe.
**Wait**, let's look closer at `last_clip_only` and `reorder`.
`last_clip_only` checks `if not med.get("measured") ... return False`. Safe.
`reorder` is only called if `med.get("measured")` is true. Safe.

**Re-evaluating P0 candidates:**

**1. `pipeline/package.py` (approx. line 346): `KeyError` in `hrank` construction**
```python
hrank = {m["moment_id"]: (-hook_own(m)["rating"], -sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS))
          for m in passing}
```
`passing` is defined earlier as moments that satisfy `can_open(m)`.
`can_open(m)` returns `True` if `"hook_rating" not in m` (line 120: `if "hook_rating" not in m: return True`).
If a moment is in `passing` but does **not** have a `hook_rating` key (because it wasn't rated yet, or the rating failed), `hook_own(m)` returns `None` (line 102-105: `r = (m or {}).get("hook_rating") or {}` ... `if not all(...): return None`).
Then `hook_own(m)["rating"]` raises `TypeError: 'NoneType' object is not subscriptable`.
**Scenario:** A moment passes `can_open` because it has no `hook_rating` yet (e.g., the batched hook rating call failed or was skipped for this specific moment, but it still has `eligibility.hook.ok` and `hook_onset.pass`). It enters `passing`. The `hrank` dict comprehension crashes the build.
**Fix:** `can_open` should probably require a valid `hook_own` rating if the build has already attempted to rate hooks, or `hrank` must handle `None`. Given Ruling 61 says "a hook without one fails closed", `can_open` returning `True` for unrated hooks contradicts the "fail closed" requirement for the *verdict*, but the *opening* eligibility (Ruling 59) previously allowed unrated hooks to be judged "as before". However, Ruling 61 changes the gate to `hook_own`. If `hook_own` is `None`, `can_open` should likely return `False` to prevent it from being an "offered" hook, OR the code must handle the `None` in `hrank`.
Actually, looking at `can_open` (line 119-122):
```python
if "hook_rating" not in m:
    return True                                      # not rated yet: judged as before ruling 59
own = hook_own(m)
return own is not None and own["rating"] >= HOOK_MIN
```
If `hook_rating` is present but invalid (e.g., missing keys), `hook_own` returns `None`, and `can_open` returns `False`.
If `hook_rating` is **absent**, `can_open` returns `True`.
Then in `build`, `passing` includes this moment.
`hrank` calls `hook_own(m)["rating"]`. `hook_own` returns `None`. Crash.
**Verdict:** **P0**. A moment with no `hook_rating` key can enter `passing` and crash the build.

**2. `pipeline/package.py` (approx. line 296): `KeyError`/`TypeError` in `hooks_txt` lambda**
```python
hooks_txt = lambda hs: "\n".join(f'id={m["moment_id"]} | rated {hook_own(m)["rating"]} on its own job: '
                                 f'"{quote_data(m["hook_rating"].get("why") or "", 200)}"' for m in hs)
```
This lambda is called with `offered` (line 307) and `missing` (line 329).
`offered` comes from `passing`. As established in P0-1, `passing` can contain moments without `hook_rating`.
If `m` has no `hook_rating`, `hook_own(m)` is `None`. `None["rating"]` crashes.
Also `m["hook_rating"].get("why")` crashes if `hook_rating` is missing.
**Verdict:** **P0**. Same root cause as P0-1.

**3. `pipeline/package.py` (approx. line 324): `KeyError` in `missing` calculation**
```python
missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}]
```
This is safe. But the subsequent `hooks_txt(missing)` call (line 329) is unsafe if `missing` contains unrated hooks.

**4. `pipeline/package.py` (approx. line 346): `hrank` uses `m["hook_rating"]` directly**
```python
-sum(m["hook_rating"].get(k) or 0 for k in HOOK_PARTS)
```
If `m` has no `hook_rating`, this crashes.

**Summary of P0-1/2/4:** The `can_open` function allows moments without `hook_rating` to pass. The downstream code (`hooks_txt`, `hrank`) assumes all moments in `passing`/`offered` have a valid `hook_rating` dict. This will crash the build if any hook-eligible moment lacks a rating.

**5. `pipeline/package.py` (approx. line 364): Infinite Loop Guard Logic**
```python
spins += 1
if spins > 4 * lineups:
    rec["why"] = "the search kept meeting line-ups already judged: stopped"
    break
```
`lineups` is the budget (8). `4 * lineups` is 32.
The loop `while True:` (implied by the structure, actually it's a `for` or `while`? The diff shows `for ai, angle in enumerate(angles):` then inside `while True:`? No, the diff shows a `while` loop structure in the original code, modified here.
Let's check the loop structure.
Line 358: `while True:` (implied by `break` and `continue`).
If `spins` exceeds 32, it breaks. This prevents infinite loops.
However, `spins` is incremented *before* the check.
If `lineups` is 0? `max_angles` is likely > 0.
This seems safe.

**6. `pipeline/package.py` (approx. line 370-377): `judged` Cache Key**
```python
key = tuple(m["moment_id"] for m in segs)
if key in judged:
    ok_m, med = judged[key]
    rec["verdict_again"] = True
else:
    ok_m, med = medley(...)
    judged[key] = (ok_m, med)
    total += 0 if med.get("replayed") else 1
```
`total` counts "JUDGED line-ups".
If `med.get("replayed")` is True, `total` does not increment.
If `key` is in `judged`, `total` does not increment.
This matches the ruling: "cached verdicts for an identical line-up are free".
**Issue:** `medley()` returns `(ok, verdict)`. `verdict` contains `replayed`.
If the *first* call to `medley` for a specific `key` returns `replayed=True` (from the router's cache), `total` is not incremented.
If the *second* call (via `judged` dict) happens, `total` is not incremented.
This seems correct.

**7. `pipeline/package.py` (approx. line 391-397): Ruling 62 Logic**
```python
if last_clip_only(segs, med) and len(segs) - 1 > LY_CLIPS[0] and \
        lineup_ok(segs[:-1], repeat_ok=exception is not None)[0]:
    dropped.add(segs[-1]["moment_id"])
    swapped = segs[:-1]
    rec["why"] = ...
    continue
```
`LY_CLIPS[0]` is the minimum number of clips (likely 2).
`len(segs) - 1 > LY_CLIPS[0]` means `len(segs) > LY_CLIPS[0] + 1`.
If `LY_CLIPS` is `(2, 4)`, then `len(segs) > 3`, so `len(segs)` must be 4.
If `len(segs)` is 3, `3-1=2`, `2 > 2` is False. So it won't drop the last clip if it would leave only 2 clips?
Wait, `LY_CLIPS[0]` is the *minimum* clips allowed in a line-up.
If we drop the last clip, the new line-up has `len(segs)-1` clips.
The condition `len(segs) - 1 > LY_CLIPS[0]` ensures the new line-up has *more* than the minimum?
No, `lineup_ok` checks the seconds and placement.
If `LY_CLIPS[0]` is 2, and we have 3 clips, dropping one leaves 2. `2 > 2` is False.
So Ruling 62 only applies if we have 4 clips (dropping one leaves 3, `3 > 2` is True).
Is this intended? "retried WITHOUT that clip when the remaining hook + clips still meet the medley's seconds floor".
If the floor is met with 2 clips, it should be allowed.
The condition `len(segs) - 1 > LY_CLIPS[0]` seems to *prevent* dropping the last clip if it results in the minimum number of clips.
Why? Maybe to avoid a 2-clip line-up if a 3-clip one failed?
But `lineup_ok` would validate the 2-clip line-up.
If `LY_CLIPS[0]` is 2, a 2-clip line-up is valid.
The condition `len(segs) - 1 > LY_CLIPS[0]` means `len(segs) >= LY_CLIPS[0] + 2`.
If `LY_CLIPS[0]=2`, `len(segs) >= 4`.
So Ruling 62 only triggers for 4-clip line-ups.
If a 3-clip line-up fails on the last clip, it goes to the swap path.
This might be a **P1** (logic error) if the intent was to allow dropping to the minimum. The ruling says "when the remaining hook + clips still meet the medley's seconds floor". It doesn't explicitly forbid dropping to the minimum clip count.
However, `lineup_ok` enforces the minimum clip count. If `lineup_ok` passes, the clip count is valid.
The extra condition `len(segs) - 1 > LY_CLIPS[0]` is redundant if `lineup_ok` checks it, or restrictive if it's stricter.
If `lineup_ok` allows 2 clips, and `len(segs)=3`, `len(segs)-1=2`. `2 > 2` is False. So it skips Ruling 62.
This forces a swap instead of a drop.
Is this a bug? The ruling says "retried WITHOUT that clip... before any swap is spent".
If the drop is valid (seconds floor met), it should be tried.
The condition `len(segs) - 1 > LY_CLIPS[0]` seems to incorrectly block valid drops to the minimum clip count.
**Verdict:** **P1**.

**8. `pipeline/package.py` (approx. line 398-405): Ruling 63 Logic**
```python
if med.get("measured") and _line_ok(med.get("through_line")) and labs[0] in cl and \
        min(cl.values()) >= COHERENCE_MIN and len(med.get("flagged") or []) > LY_MAX_BRIDGES:
    order = reorder(segs, bad_pairs, judged, repeat_ok=exception is not None)
    if order is not None:
        swapped = order
        rec["why"] = ...
        continue
```
`min(cl.values()) >= COHERENCE_MIN`.
`cl` is `med.get("clips")`.
`med["clips"]` contains the hook's cached rating and the other clips' ratings.
If the hook's rating is low, `min` will be low, and this block is skipped.
This is correct: Ruling 63 applies when "every rating passes".
`reorder` is called.
`reorder` returns a new line-up or `None`.
If `order` is not `None`, it `continue`s the loop.
The new line-up is judged in the next iteration.
This seems correct.

**9. `pipeline/package.py` (approx. line 406-409): Weak Clip Calculation**
```python
weak = {by_lab[lb]["moment_id"] for lb, x in cl.items()
        if lb in by_lab and x < COHERENCE_MIN}
if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
    weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
```
`cl` includes the hook.
If the hook's rating is low, it is in `weak`.
Then `hook_weak = segs[0]["moment_id"] in weak`.
`weak.discard(segs[0]["moment_id"])`.
This removes the hook from `weak` for the swap logic.
This is correct: "the line-up is built AROUND its hook".

**10. `pipeline/package.py` (approx. line 412-418): Break Condition**
```python
if not med.get("measured") or not weak:
    rec["why"] = ...
    break
```
If `weak` is empty (all clips pass, but maybe joins failed and reorder failed?), it breaks.
If `reorder` returned `None`, we fall through to this.
If `weak` is empty, it means no clip is under the bar.
But we are in the `if not ok_m:` block.
If `ok_m` is False, either:
- Through-line bad.
- Some rating < 4.
- Too many flagged joins.
If Ruling 62 and 63 didn't trigger, and `weak` is empty, it means:
- Through-line is bad? No, `_line_ok` is checked in 63.
- If through-line is bad, `ok_m` is False. `weak` might be empty if all ratings are high.
- In this case, `break` is correct.

**11. `pipeline/package.py` (approx. line 159-160): `hook_own` in `coherence`**
```python
own = hook_own(hook)
```
`hook` is passed as `segs[0]`.
If `segs[0]` has no `hook_rating`, `own` is `None`.
`ok = own is not None and ...`
So `coherence` fails closed.
This is correct.

**12. `pipeline/package.py` (approx. line 179-181): `verdict` construction in `coherence`**
```python
v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
         hook_own=own or {"rating": None, "why": ...})
```
If `own` is `None`, `v["clips"]` does not contain `labs[0]` (the hook).
`v["hook_own"]` is the fail-closed dict.
This is correct.

**13. `pipeline/package.py` (approx. line 229-231): `verdict` construction in `medley`**
Same as above. Correct.

**14. `pipeline/package.py` (approx. line 54-56): `hook_ratings` cache read**
```python
if rec is not None and all(isinstance(rec.get(k), int) for k in HOOK_PARTS):
    out[m["moment_id"]] = dict(rec, rating=min(rec[k] for k in HOOK_OWN), rule=HOOK_OWN_RULE,
                               cached=True)
```
`HOOK_PARTS` is `("scroll", "alone", "setup")`.
`HOOK_OWN` is `("scroll", "alone")`.
It checks if `scroll`, `alone`, `setup` are all ints.
Then it calculates `rating` as `min(scroll, alone)`.
This is correct.

**15. `pipeline/package.py` (approx. line 66-67): `hook_ratings` new record**
```python
rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
       "backend": r.backend, "rule": HOOK_OWN_RULE}
```
Correct.

**16. `pipeline/package.py` (approx. line 104): `hook_own` type check**
```python
if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
```
`parts` is `{k: r.get(k) for k in HOOK_OWN}`.
If `r.get(k)` is `None`, `isinstance(None, int)` is False.
So it returns `None`.
Correct.

**17. `pipeline/package.py` (approx. line 119-122): `can_open`**
```python
if "hook_rating" not in m:
    return True
own = hook_own(m)
return own is not None and own["rating"] >= HOOK_MIN
```
As identified in P0-1, this allows unrated hooks to pass.
**Verdict:** **P0**.

**18. `pipeline/package.py` (approx. line 131-132): `hook_order`**
```python
return sorted(ms, key=lambda m: (-((hook_own(m) or {}).get("rating") or 0), ...))
```
If `hook_own(m)` is `None`, `(None or {})` is `{}`. `{}.get("rating")` is `None`. `None or 0` is `0`.
So unrated hooks sort to the end (rating 0).
This is safe.

**19. `pipeline/package.py` (approx. line 295): `offered`**
```python
offered = passing[:max_angles]
```
`passing` is sorted by `hook_order`.
Unrated hooks are at the end.
If there are enough rated hooks, `offered` contains only rated hooks.
If there are not enough rated hooks, `offered` contains unrated hooks.
Then `hooks_txt(offered)` crashes (P0-2).

**20. `pipeline/package.py` (approx. line 346): `hrank`**
Crashes on unrated hooks (P0-4).

**Conclusion on P0:** The primary issue is that `can_open` returns `True` for moments without `hook_rating`, but downstream code assumes `hook_rating` exists and is valid. This will crash the build if any hook-eligible moment is unrated.

## P1 Findings (Major)

**1. `pipeline/package.py` (approx. line 391): Ruling 62 Clip Count Condition**
`len(segs) - 1 > LY_CLIPS[0]` prevents dropping the last clip if it results in the minimum allowed clip count.
If `LY_CLIPS[0]` is 2, and `len(segs)` is 3, `2 > 2` is False.
The drop is skipped, and the code proceeds to swap.
The ruling says "retried WITHOUT that clip when the remaining hook + clips still meet the medley's seconds floor".
It does not mention a clip count restriction beyond the floor.
`lineup_ok` enforces the minimum clip count.
If `lineup_ok` passes for `segs[:-1]`, the clip count is valid.
The extra condition is redundant and potentially incorrect.
**Verdict:** **P1**.

**2. `pipeline/package.py` (approx. line 364): Infinite Loop Guard**
`if spins > 4 * lineups:`
`lineups` is the budget (8).
`4 * 8 = 32`.
If the search oscillates between two line-ups, `spins` will exceed 32 and break.
This is safe.

**3. `pipeline/package.py` (approx. line 377): Budget Counting**
`total += 0 if med.get("replayed") else 1`
If `medley` returns a replayed verdict, `total` is not incremented.
This matches the ruling.

**4. `pipeline/package.py` (approx. line 324-341): Ruling 64 Follow-up**
```python
missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}]
if missing and len(angles) < max_angles:
    k2, r = max_angles - len(angles), None
    try:
        r = router.call(...)
        more = allot(check_angles(...), max(1, k2 // len(missing)))
        angles = angles + more
        ...
    except Exception as e:
        ...
```
If `missing` is not empty, it calls the model again.
`k2` is the remaining angle budget.
`per` for the follow-up is `max(1, k2 // len(missing))`.
This seems correct.
The follow-up call uses `seed=9`.
The main call uses `seed=7` and `seed=8`.
This is safe.

**5. `pipeline/package.py` (approx. line 314): `allot`**
```python
angles, angle_reply = allot(got, per), r
```
`allot` keeps at most `per` angles per hook.
This is correct.

**6. `pipeline/package.py` (approx. line 315-316): `angle_allotment`**
```python
if len(angles) < len(got):
    out["angle_allotment"] = {"dropped": [a["angle"] for a in got if a not in angles], "per": per}
```
`a not in angles` uses list equality.
`angles` is a list of dicts.
`a` is a dict.
Dict equality is value-based.
This is safe.

**7. `pipeline/package.py` (approx. line 348): `angles` Sorting**
```python
angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))
```
`hrank[a["hook"]]` is a tuple `(-rating, -sum)`.
`first_fresh(a)` is a bool.
`not first_fresh(a)` is a bool.
Sorting by `(tuple, bool)` is safe.

**8. `pipeline/package.py` (approx. line 358-360): `while True` Loop**
The loop structure is not fully visible in the diff, but the `break` and `continue` statements imply a `while` loop.
The guard `spins > 4 * lineups` prevents infinite loops.

**9. `pipeline/package.py` (approx. line 380-381): `bad_pairs` Update**
```python
bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
              for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}
```
`labs_` is `labels(len(segs))`.
`labs_.index(a)` finds the index of the label `a` in `labs_`.
`a` is a label like `"hook"`, `"clip_01"`, etc.
`j` is a join like `"hook -> clip_01"`.
`j.split(" -> ")` gives `["hook", "clip_01"]`.
`a` is `"hook"`, `b` is `"clip_01"`.
`labs_.index("hook")` is 0.
`segs[0]["moment_id"]` is the hook's id.
This is correct.

**10. `pipeline/package.py` (approx. line 398): `labs[0] in cl`**
`cl` is `med.get("clips")`.
`med["clips"]` contains the hook's label (`labs[0]`) and the other clips' labels.
So `labs[0] in cl` is True.
This is correct.

## P2 Findings (Minor)

**1. `pipeline/package.py` (approx. line 42): `HOOK_OWN_RULE` String**
The string is long and wraps. This is fine.

**2. `pipeline/package.py` (approx. line 101): `hook_own` Docstring**
The docstring is clear.

**3. `pipeline/package.py` (approx. line 147): `coherence` Signature**
`hook=None` is added.
If `hook` is `None`, `hook_own(None)` returns `None`.
`ok` becomes `False`.
This is fail-closed.
However, the call site (line 426) passes `hook=segs[0]`.
If `segs` is empty, `segs[0]` crashes.
But `coherence` is only called if `pk` is built, which implies `segs` is not empty.
This is safe.

**4. `pipeline/package.py` (approx. line 208): `medley` Signature**
`own = hook_own(segs[0]) if segs else None`.
If `segs` is empty, `own` is `None`.
`ok` becomes `False`.
This is fail-closed.
Safe.

**5. `tests/package/test_medley.py` (approx. line 455): `SEGS` Definition**
```python
SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2}), ...]
```
The test data includes `hook_rating`.
This is correct.

**6. `tests/package/test_medley.py` (approx. line 492-497): `test_ruling_61`**
```python
low = [dict(self.SEGS[0], hook_rating={"scroll": 3, "alone": 5, "setup": 5}), *self.SEGS[1:]]
ok, v = PK.medley(..., low, ...)
self.assertFalse(ok)
```
This tests the fail-closed behavior for low ratings.
```python
ok, v = PK.medley(..., [pm("h", "A", 12.0), *self.SEGS[1:]], ...)
self.assertFalse(ok)
```
This tests the fail-closed behavior for missing ratings.
Correct.

**7. `tests/package/test_medley.py` (approx. line 621-623): `test_only_a_hook_rated_4_or_more_opens`**
```python
for (sc, al, se), ok in (((4, 4, 1), True), ((5, 4, 5), True), ((3, 5, 5), False), ((5, 3, 5), False)):
    r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se})
    self.assertEqual(PK.can_open(r), ok, (sc, al, se))
```
This tests `can_open` with valid ratings.
It does not test `can_open` with missing ratings.
This is a gap in the tests, but the code bug is in `package.py`.

**8. `tests/package/test_medley.py` (approx. line 627-628): `can_open` Bad Ratings**
```python
for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5}, {"scroll": 5.0, "alone": 5}):
    self.assertFalse(PK.can_open(dict(m, hook_rating=bad)), bad)
```
This tests `can_open` with invalid ratings.
It does not test `can_open` with `hook_rating` missing.
Again, a gap in the tests.

## SHIP: No

**Reasons:**
1.  **P0 Crash:** `can_open` returns `True` for moments without `hook_rating`, but `hooks_txt` and `hrank` crash when processing such moments. This will fail the build if any hook-eligible moment is unrated.
2.  **P1 Logic Error:** Ruling 62's condition `len(segs) - 1 > LY_CLIPS[0]` incorrectly prevents dropping the last clip if it results in the minimum allowed clip count, contradicting the ruling's intent to retry without the last clip if the seconds floor is met.

**Conditions for Ship:**
1.  Fix `can_open` to return `False` if `hook_rating` is missing or invalid, OR ensure that `passing` only contains moments with valid `hook_rating`.
2.  Fix `hooks_txt` and `hrank` to handle moments without `hook_rating` (e.g., skip them or use a default).
3.  Fix Ruling 62's condition to allow dropping the last clip if `lineup_ok` passes, regardless of the clip count (as long as it's >= minimum).