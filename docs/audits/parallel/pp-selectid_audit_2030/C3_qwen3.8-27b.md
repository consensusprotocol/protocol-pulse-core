# qwen3.8-27b (qwen/qwen3.8-27b) 127 s finish=stop usage in 54420 / out 5099 usd~0.240 (upper-bound price)

# Code Audit: pp-selectid-2030 (L-y Medley)

## P0 Findings

### P0-1: `ly_shape` allows a bridge at an unflagged join when the verdict is unmeasured
**File:** `pipeline/package.py`, `ly_shape()` (lines ~560-565 in diff)

**Scenario:**
1. `medley()` fails (e.g., provider error), returning `{"measured": False, "flagged": None}`.
2. `build()` correctly refuses to write for this line-up (`if not ok_m: ... break`).
3. **However**, if a package is constructed via `assemble_medley()` with a bridge (e.g., from a retry path or manual construction) and `pk["medley"]` is `{"measured": False, "flagged": None}`:
   - `ly_shape` checks `med.get("measured") is not True` → adds failure `"the clips-alone verdict was not measured (L-y 3)"`.
   - **But** it does NOT check whether the bridge is at a flagged join when `flagged` is `None`. The `elif sorted(bridged) != sorted(med["flagged"])` branch is skipped because `measured` is not `True`.
   - Result: A package with a bridge at an arbitrary join passes the "bridge at flagged join" check (it's not evaluated) but fails on "not measured". This is correct behavior (fail closed), **BUT** the failure message is misleading: it says "not measured" when the real issue is also that the bridge placement is unverifiable. More critically, if `measured` is `True` but `flagged` is an empty list `[]`, and a bridge exists, `sorted(bridged) != sorted([])` correctly fails. **No actual P0 here** — the fail-closed behavior is correct.

**Revised:** This is not a P0. The fail-closed behavior is correct. Downgrading to P2 (misleading error message).

---

### P0-2: `takeaway_budget` can return a budget where the lower bound exceeds the upper bound after R4 cap
**File:** `pipeline/package.py`, `takeaway_budget()` (lines ~112-125 in diff)

**Scenario:**
1. `content_s = 50.0` (clips total 50s).
2. `FINAL_TAIL_S = 14.30`, `R4_WPS = 2.5`, `R4_PREROLL_S = 1.0`.
3. `fixed = 50.0 + 14.30 + 0 = 64.30`.
4. `words_at(61.5) = 2.5 * (61.5 - 64.30 - 1.0) = 2.5 * (-3.8) = -9.5` → `lo = max(8, ceil(-9.5)) = 8`.
5. `words_at(68.5) = 2.5 * (68.5 - 64.30 - 1.0) = 2.5 * 3.2 = 8.0` → `hi = min(cap, floor(8.0))`.
6. `cap = min(30, r4_max_vo_words(50.0, 1) - 0)`.
   - `r4_max_vo_words(50.0, 1)`: The R4 share is 45% of runtime. Runtime estimate = `50.0 + (words/2.5 + 1.0) + 14.30`. R4 requires `VO_seconds <= 0.45 * runtime`. This is a circular dependency resolved by the formula in `r4_max_vo_words`.
   - If `cap < 8`, then `hi = min(cap, 8) < 8 = lo` → `lo > hi` → returns `None`.
7. **But** `write_takeaway` does `budget = budget or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)` → falls back to `(8, 30)`.
8. The writer is asked for 8-30 words. If it writes 30 words, `runtime()` = `50.0 + (30/2.5 + 1.0) + 14.30 = 50.0 + 13.0 + 14.30 = 77.3s` → **exceeds 70s**.
9. `cheap_checks` fails on `RUNTIME`. The writer is asked to redo. But the redo uses the same fallback budget `(8, 30)` because `takeaway_budget` still returns `None` for `content_s=50.0`.
10. **Result:** Infinite loop of rewrites, or the angle is abandoned. This is a **fail-closed** behavior (no bad package is produced), but it wastes budget and may prevent a valid package from being produced when a shorter takeaway (e.g., 8 words) would have fit.

**Concrete failure:**
- Input: `content_s = 50.0`, no bridge.
- `takeaway_budget(50.0)` returns `None` (because even 8 words pushes the estimate over 70s? Let's verify: `50.0 + (8/2.5 + 1.0) + 14.30 = 50.0 + 4.2 + 14.30 = 68.5s` → **fits**).
- Wait, `words_at(68.5) = 8.0`, so `hi = 8`. `lo = 8`. `cap >= 8`. So `budget = (8, 8)`. This is valid.
- Let's try `content_s = 52.0`: `fixed = 52.0 + 14.30 = 66.30`. `words_at(61.5) = 2.5*(61.5-66.30-1.0) = 2.5*(-5.8) = -14.5` → `lo = 8`. `words_at(68.5) = 2.5*(68.5-66.30-1.0) = 2.5*1.2 = 3.0` → `hi = min(cap, 3)`. If `cap >= 3`, `hi = 3`. `lo=8 > hi=3` → `None`.
- Fallback: `(8, 30)`. Writer writes 8 words. `runtime = 52.0 + (8/2.5+1.0) + 14.30 = 52.0 + 4.2 + 14.30 = 70.5s` → **fails** (exceeds 70s).
- Writer writes 30 words. `runtime = 52.0 + 13.0 + 14.30 = 79.3s` → **fails**.
- **No takeaway length lands 60-70s.** The angle is correctly abandoned. This is **fail-closed** and correct.

**Revised:** Not a P0. The behavior is correct (fail closed). Downgrading to P2 (could be more efficient, but no incorrect output).

---

### P0-3: `medley_content_range` does not account for the bridge's pre-roll in the lower bound
**File:** `pipeline/package.py`, `medley_content_range()` (lines ~103-109 in diff)

**Scenario:**
1. `n_bridges=1`, `bridge_words=12`.
2. `extra = 1 * (12/2.5 + 1.0) = 5.8`.
3. `lo = 60 - 14.30 - 5.8 - (30/2.5 + 1.0) = 60 - 14.30 - 5.8 - 13.0 = 26.9`.
4. `hi = 70 - 14.30 - 5.8 - (8/2.5 + 1.0) = 70 - 14.30 - 5.8 - 4.2 = 45.7`.
5. A line-up with clips totaling 26.9s and a 12-word bridge and a 30-word takeaway: `runtime = 26.9 + (12/2.5+1.0) + (30/2.5+1.0) + 14.30 = 26.9 + 5.8 + 13.0 + 14.30 = 60.0s` → **fits**.
6. A line-up with clips totaling 45.7s and a 12-word bridge and an 8-word takeaway: `runtime = 45.7 + 5.8 + 4.2 + 14.30 = 70.0s` → **fits**.
7. **Correct.** The formula is sound.

**Revised:** Not a P0.

---

### P0-4: `lineup_for` with `repeat_ok=True` may allow two clips from the same channel and same video
**File:** `pipeline/package.py`, `lineup_for()` (lines ~383-385 in diff)

**Code:**
```python
if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
    continue
```

**Scenario:**
1. `n=2` (hook + 2 clips). `chans = [A, A, B]`. `len(set(chans)) = 2 != 3`.
2. `repeat_ok=True`, `len(set(chans)) == 2 == n`? No, `n=2`, `len(set(chans))=2`, so `2 == 2` is true.
3. `len({m["video_id"] for m in (h, *combo)}) == n + 1`? `n+1 = 3`. If the two A clips are from different videos, and the B clip is from a third video, then `len = 3` → **allowed**.
4. If the two A clips are from the **same** video, `len = 2 != 3` → **rejected**.
5. **Correct.** The code enforces different videos.

**Revised:** Not a P0.

---

### P0-5: `build()` does not check `package_pin.gate_problems` before returning a package
**File:** `pipeline/package.py`, `build()` (lines ~888-893 in diff)

**Code:**
```python
import package_pin
problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
if problems:
    rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
    w_used = writes
    break
```

**Scenario:**
1. This check is performed **after** `pk["gates"]` is set (line ~867-870).
2. If `problems` is non-empty, the loop breaks and the package is **not** added to `out["packages"]`.
3. **Correct.** The package is only returned if all required gates pass.

**Revised:** Not a P0.

---

### P0-6: `providers.py` ledger corruption via concurrent writes
**File:** `pipeline/providers.py`, `Router._settle()` (lines ~1077-1088 in diff)

**Scenario:**
1. `Router._settle` is called from multiple threads (via `ThreadPoolExecutor` in `build()`).
2. The code does `d = json.load(open(self.spend_path))` ... `self._save(d)`.
3. **Race condition:** Two threads read the same `d`, both increment, both write. One increment is lost.
4. **Impact:** The spend ledger undercounts. The `limit_usd` guard may not trigger when it should.
5. **However**, the `meter()` function in `proof_ly.py` wraps `_settle` with a `threading.Lock()`. But `build()` itself does not use `meter()`. It uses the raw `Router`.
6. **In `build()`:** `spend=lambda: own["est"]` is passed, but `own` is from `meter(router)` in `proof_ly.py`. In the main pipeline, `spend` is likely a different callable.
7. **If the main pipeline uses `Router` directly without `meter()`, the ledger is racy.**

**Concrete failure:**
- Input: Two concurrent calls to `Router._settle` with `usd=0.10`.
- Expected: `usd_estimate` increases by `0.20`.
- Actual: `usd_estimate` increases by `0.10` (one write lost).
- Result: Spend guard triggers late, potentially exceeding budget.

**Severity:** P0 (financial integrity, fail-open on spend).

---

### P0-7: `medley()` prompt does not include the hook's label in the joins
**File:** `pipeline/package.py`, `medley()` (lines ~437-444 in diff)

**Code:**
```python
js = joins(labs)
# ...
r = router.call("coherence_verdict",
                MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
                    f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
                ...)
```

**Scenario:**
1. `labs = ["hook", "clip_01", "clip_02"]`.
2. `js = ["hook -> clip_01", "clip_01 -> clip_02"]`.
3. The prompt asks for a verdict on **every** join, including `hook -> clip_01`.
4. **Correct.** The hook is a segment, and the join after it is a valid join.

**Revised:** Not a P0.

---

### P0-8: `write_takeaway` does not validate that the bridge's `cites` are from the line-up
**File:** `pipeline/package.py`, `write_takeaway()` (lines ~520-528 in diff)

**Code:**
```python
for slot, ln, want in lines:
    if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
            not ln["text"].strip() or not isinstance(ln["cites"], list) or \
            any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
            ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
        raise ValueError(...)
```

**Scenario:**
1. `ids = [m["moment_id"] for m in segs]`.
2. The bridge's `cites` are checked against `ids`.
3. **Correct.**

**Revised:** Not a P0.

---

## P1 Findings

### P1-1: `ly_shape` does not check that the takeaway is non-empty
**File:** `pipeline/package.py`, `ly_shape()` (lines ~551-552 in diff)

**Code:**
```python
if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
    fails.append("no takeaway after the last clip (L-y 1)")
```

**Scenario:**
1. `bridges = [""]` (empty string). `after = [2]`. `n_clips = 2`.
2. `after[-1] == n_clips` → `2 == 2` → true.
3. `not (bridges[-1] or "").strip()` → `not "".strip()` → `not ""` → `True`.
4. **Fails correctly.**

**Revised:** Not a P1.

---

### P1-2: `medley()` does not check that the through-line is not a restatement of a clip
**File:** `pipeline/package.py`, `medley()` (lines ~458-461 in diff)

**Scenario:**
1. The through-line is "Bitcoin is up." and a clip says "Bitcoin is up."
2. `medley()` only checks `len(tl.split()) >= 4` and `not NO_LINE.search(tl)`.
3. **It does not check for restatement.** But L-y 3 says the through-line is a viewer's state, not a restatement. The **coherence** verdict (with the takeaway) checks for restatement.
4. **Correct.** The clips-alone verdict is blind; it does not judge the takeaway.

**Revised:** Not a P1.

---

### P1-3: `build()` does not record the `medley` verdict in the package if the line-up fails
**File:** `pipeline/package.py`, `build()` (lines ~738-739 in diff)

**Code:**
```python
ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
rec["medley"], rec["medley_ok"] = med, ok_m
```

**Scenario:**
1. If `ok_m` is `False`, the line-up is dropped. `rec` is added to `out["tried"]`.
2. The `medley` verdict is recorded in `rec`.
3. **Correct.**

**Revised:** Not a P1.

---

### P1-4: `package_pin.bridge_slots` does not handle the case where `vo["intro"]` is present in a medley
**File:** `pipeline/package_pin.py`, `bridge_slots()` (lines ~981-989 in diff)

**Code:**
```python
if pk.get("shape") == "medley":
    return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
```

**Scenario:**
1. In a medley, `vo["intro"]` is `None` (no intro). The bridge after the hook is stored in `vo["intro"]` **only if** `k=0` in `assemble_medley`.
2. But `bridge_slots` does not account for `vo["intro"]` in a medley. It only looks at `vo["bridges_after_clip"]`.
3. In `assemble_medley`, if `k=0`, the bridge is stored in `vo["intro"]`, and `vo["bridges_after_clip"]` does **not** include `0`.
4. **Result:** `bridge_slots` returns `["takeaway"]` for a medley with a bridge after the hook, but the bridge is in `vo["intro"]`, not in `vo["bridges"]`.
5. `line_problems` checks `by.get("intro") != vo.get("intro")`. If the bridge is in `vo["intro"]`, and the line is in `pk["lines"]` with slot `"intro"`, this check passes.
6. **But** `bridge_slots` is used to map `vo["bridges"]` to slots. If the bridge is in `vo["intro"]`, it is not in `vo["bridges"]`, so `bridge_slots` does not include it.
7. **Correct.** The intro is handled separately in `line_problems`.

**Revised:** Not a P1.

---

### P1-5: `proof_ly.py` does not handle the case where `Router` is not available
**File:** `tests/package/proof_ly.py`, `main()` (lines ~1362-1363 in diff)

**Scenario:**
1. `router = P.Router(env_path=PM.PS.ENV, ...)`.
2. If `PM.PS.ENV` does not exist, `Router` may fail.
3. **Not a code issue.** The environment is assumed to be set up.

**Revised:** Not a P1.

---

## P2 Findings

### P2-1: `ly_shape` error message is misleading when the verdict is unmeasured
**File:** `pipeline/package.py`, `ly_shape()` (lines ~561-562 in diff)

**Scenario:**
1. `medley` is `{"measured": False, "flagged": None}`.
2. `ly_shape` adds `"the clips-alone verdict was not measured (L-y 3)"`.
3. It does not check the bridge placement.
4. **Correct behavior**, but the error message could be more specific.

**Severity:** P2 (cosmetic).

---

### P2-2: `takeaway_budget` fallback may cause unnecessary rewrites
**File:** `pipeline/package.py`, `write_takeaway()` (lines ~485 in diff)

**Scenario:**
1. `takeaway_budget` returns `None`.
2. Fallback: `(8, 30)`.
3. Writer writes 30 words. `runtime` fails.
4. Writer is asked to redo with the same fallback.
5. **Wastes budget.**

**Severity:** P2 (efficiency).

---

### P2-3: `providers.py` ledger is racy (see P0-6)
**Severity:** P0 (already listed).

---

## Verdict

**SHIP: no**

**Reasons:**
1. **P0-6:** The spend ledger in `providers.py` is racy under concurrent writes. This can lead to undercounting spend and exceeding the budget. This is a financial integrity issue and violates the fail-closed principle (L-j).
2. **P0-1 to P0-5:** After re-evaluation, none of these are actual P0s. The code is fail-closed in all cases.

**Conditions for shipping:**
1. Fix the race condition in `providers.py` by adding a lock around the read-modify-write cycle in `Router._settle`.
2. Add a test for concurrent spend ledger updates.