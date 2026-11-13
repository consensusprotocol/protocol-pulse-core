# qwen3.8-27b (qwen/qwen3.8-27b) 101 s finish=stop usage in 28278 / out 3101 usd~0.131 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1207

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the *absence* of imports and the *presence* of `None` values in `hook_rating`. The consensus refutation (R2) correctly identified that `build()` populates `hook_rating` for every cleared moment before `passing` is computed, neutralizing the `TypeError` risks in `hrank` and `hooks_txt`.

However, **Grok** and **Qwen** both flagged the `coherence()` signature change (`hook=None` default) as a potential silent behavior change for external callers. While the consensus noted that the *only* call site in the diff passes `hook=segs[0]`, they did not fully verify if `coherence` is a public API used by replay/attestation tools outside the `build()` flow. I missed the nuance that while `build()` is safe, the *function contract* has changed from "derive rating from prompt" to "require external rating," which is a breaking change for any hypothetical external caller that doesn't pass `hook`.

**GLM** correctly identified that `reorder()` uses `itertools.permutations` and questioned the import. The consensus refuted this (R1) by pointing to `package.py:50`. I missed verifying the import location in Cycle 1, relying on the assumption that standard library imports are always present.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Model | Finding | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **Grok** | P0: Missing `import itertools` | **Disagree** | Refuted by Consensus R1. `package.py:50` has `import itertools`. The diff does not remove it. |
| **Grok** | P1: `coherence()` `hook=None` default | **Agree (P2)** | It is a behavior change. If any external tool calls `coherence()` without `hook`, it now fails closed (`ok=False`) instead of deriving a rating. This is M12-compliant (fail-closed) but a breaking API change. |
| **Qwen** | P0: `can_open` allows unrated hooks, crashing `hrank` | **Disagree** | Refuted by Consensus R2. `build()` sets `hook_rating` on all cleared moments before `passing` is computed. `can_open` returning `True` for unrated hooks is only relevant for *pre-build* checks (e.g., unit tests or initial screening), not the `hrank` construction which happens post-rating. |
| **Qwen** | P0: `hooks_txt` lambda crashes on missing `hook_rating` | **Disagree** | Same as above. `offered` is a subset of `passing`, which is a subset of `cleared`. All have `hook_rating` set. |
| **GLM** | P1: `reorder()` `itertools` import | **Disagree** | Refuted by Consensus R1. |
| **GLM** | P1: `coherence()` other callers | **Agree (P2)** | Same as Grok. |
| **GLM** | P1: `lineup_ok` `repeat_ok` semantics | **Disagree** | Refuted by Consensus R4. `repeat_ok` only relaxes the "one repeated channel" rule, not the seconds floor. |

## 3. NEW FINDINGS FROM THIS REVIEW

### P1-1: `reorder()` does not check `lineup_ok` for the *original* line-up before permuting
**File:** `pipeline/package.py`, `reorder()` (diff lines 253–272)
**Scenario:** `reorder()` is called when `medley()` fails due to flagged joins, but *all ratings pass*. The code assumes the current line-up is valid except for adjacency. However, `reorder()` iterates over *all* permutations of the clips after the hook. It checks `lineup_ok(new, repeat_ok=repeat_ok)` for each candidate. This is correct. **However**, the *original* line-up that failed is not re-checked for `lineup_ok` in this path. It was already checked when it was formed by `lineup_for`. So this is safe. **No finding.**

### P1-2: `last_clip_only` does not verify the *new* line-up (without last clip) is valid before `continue`
**File:** `pipeline/package.py`, diff lines 391–397
**Scenario:**
```python
if last_clip_only(segs, med) and len(segs) - 1 > LY_CLIPS[0] and \
        lineup_ok(segs[:-1], repeat_ok=exception is not None)[0]:   # RULING 62
    dropped.add(segs[-1]["moment_id"])
    swapped = segs[:-1]
    ...
    continue
```
The code checks `lineup_ok(segs[:-1], ...)` before `continue`. This is correct. The new line-up is validated. **No finding.**

### P1-3: `bad_pairs` accumulation uses `labs_.index(a)` which is O(N) and potentially fragile
**File:** `pipeline/package.py`, diff lines 380–381
**Scenario:**
```python
bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
              for a, b in (j.split(" -> ") for j in med.get("flagged") or [])}
```
`labs_` is a list of labels like `["hook", "clip_01", "clip_02"]`. `a` and `b` are strings like `"hook"` and `"clip_01"`. `labs_.index(a)` finds the index. This is correct but inefficient. More importantly, if `a` or `b` is not in `labs_`, it raises `ValueError`. The `medley()` contract guarantees that `flagged` joins are between valid labels. So this is safe. **No finding.**

### P1-4: `allot()` does not preserve the *order* of angles within a hook
**File:** `pipeline/package.py`, `allot()` (diff lines 275–282)
**Scenario:**
```python
def allot(angles, per):
    seen, out = {}, []
    for a in angles:
        seen[a["hook"]] = seen.get(a["hook"], 0) + 1
        if seen[a["hook"]] <= per:
            out.append(a)
    return out
```
This preserves the order of `angles` as given by the writer. The writer is asked to provide angles "best hook first". The `allot` function keeps the first `per` angles for each hook. This is correct. **No finding.**

### P1-5: The follow-up angle call does not pass `avoid_vendor` / `avoid_family`
**File:** `pipeline/package.py`, diff lines 328–331
**Scenario:**
```python
r = router.call("angle_write", ANGLE_PROMPT.format(...), 3000, 9, deadline_s=WRITER_DEADLINE_S)
```
The first angle call (diff lines 304–308) also does not pass `avoid_vendor` / `avoid_family`. This is consistent. The `angle_write` role is a *writer*, not a *verdict*. The writer's vendor is not avoided in the writer's own call. The *verdicts* (medley, coherence) avoid the writer's vendor. So this is correct. **No finding.**

### P1-6: `hook_own` returns `None` if `hook_rating` is missing, but `can_open` returns `True` if `hook_rating` is missing
**File:** `pipeline/package.py`, `can_open()` (diff lines 119–122)
**Scenario:**
```python
if "hook_rating" not in m:
    return True                                      # not rated yet: judged as before ruling 59
own = hook_own(m)
return own is not None and own["rating"] >= HOOK_MIN
```
If `hook_rating` is missing, `can_open` returns `True`. This is intended for *pre-build* checks. In `build()`, `hook_rating` is always set. So this is safe. **No finding.**

### P1-7: The `judged` dict is keyed by `tuple(m["moment_id"] for m in segs)`, but `segs` is a list of dicts
**File:** `pipeline/package.py`, diff lines 369–376
**Scenario:**
```python
key = tuple(m["moment_id"] for m in segs)
if key in judged:
    ok_m, med = judged[key]
    ...
else:
    ok_m, med = medley(...)
    judged[key] = (ok_m, med)
```
This is correct. The key is a tuple of moment IDs, which is hashable. **No finding.**

### P1-8: The `spins` guard is `spins > 4 * lineups`, but `lineups` is not defined in the diff
**File:** `pipeline/package.py`, diff lines 364–366
**Scenario:**
```python
spins += 1
if spins > 4 * lineups:                   # a guard: free (cached) line-ups never turn forever
    rec["why"] = "the search kept meeting line-ups already judged: stopped"
    break
```
`lineups` is not defined in the diff. It must be defined earlier in `build()`. The consensus does not refute this. I cannot verify from the diff alone. **Condition: confirm `lineups` is defined and equals the budget (8).**

### P1-9: `reorder()` does not check if the *original* line-up is in `judged`
**File:** `pipeline/package.py`, `reorder()` (diff lines 253–272)
**Scenario:**
```python
for perm in itertools.permutations(clips):
    new = [h, *perm]
    ids = tuple(m["moment_id"] for m in new)
    n_bad = sum((a, b) in bad_pairs for a, b in zip(ids, ids[1:]))
    if ids in judged or n_bad > LY_MAX_BRIDGES:
        continue
```
The original line-up is in `judged` (it was just judged). So `reorder()` will skip it. This is correct. **No finding.**

### P1-10: The `missing` calculation in `build()` uses `offered`, but `offered` is a list of moments, not IDs
**File:** `pipeline/package.py`, diff lines 324–325
**Scenario:**
```python
missing = [m for m in offered if m["moment_id"] not in {a["hook"] for a in angles}]
```
This is correct. `offered` is a list of moments. `a["hook"]` is a moment ID. **No finding.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Ruling 61 (Hook Rated Once)** | P1 | P2 | The `coherence()` signature change is a P2 (behavior change, but fail-closed). The `can_open` / `hrank` crash risks are refuted. |
| **Ruling 62 (Last Clip)** | P1 | P2 | The `lineup_ok` check is present. The `LY_CLIPS[0]` condition is correct. |
| **Ruling 63 (Joins Before Swaps)** | P1 | P2 | The `reorder()` function is correct. The `itertools` import is present. |
| **Ruling 64 (Angle Per Hook)** | P1 | P2 | The `allot()` and follow-up logic is correct. |
| **Budget** | P1 | P2 | The `judged` dict and `spins` guard are correct. The `lineups` variable is not defined in the diff, but is likely defined earlier. |

## 5. FINAL PRIORITY LIST

### P0 CRITICAL
None.

### P1 HIGH
1. **`pipeline/package.py` (diff line 364):** `lineups` is not defined in the diff. Confirm it is defined earlier in `build()` and equals the budget (8). If it is not defined, this is a `NameError`.

### P2 MEDIUM
1. **`pipeline/package.py` (diff line 147):** `coherence()` signature change (`hook=None` default) is a breaking change for any external caller that does not pass `hook`. Grep for other callers before merge.
2. **`pipeline/package.py` (diff line 364):** The `spins` guard uses `lineups`, which is not defined in the diff. Confirm it is defined.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Confirm that `lineups` is defined in `build()` before the `spins` guard is used.** If it is not defined, the build will crash with a `NameError` on the first iteration of the search loop.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. Confirm that `lineups` is defined in `build()` before the `spins` guard is used (diff line 364).
2. Grep for other callers of `coherence()` to ensure they pass `hook=` (diff line 147).