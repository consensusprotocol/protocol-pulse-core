# qwen3.8-27b (qwen/qwen3.8-27b) 90 s finish=stop usage in 44698 / out 4128 usd~0.196 (upper-bound price)

# Code Audit: pp-selectid-2030 (L-y Medley)

## P0 Findings

### P0-1: `ly_shape` allows a bridge at an unflagged join when the clips-alone verdict is unmeasured
**File:** `pipeline/package.py`, `ly_shape()` (lines ~547-552 in diff)

**Scenario:**
1. `medley()` fails (e.g., provider error, out-of-contract JSON) → returns `ok=False, verdict={"measured": False, "flagged": None}`.
2. In `build()`, `if not ok_m:` is true. `med.get("measured")` is `False`, so `if not med.get("measured") or not weak:` → `rec["why"] = "..."` and `break`. **No package is assembled.**

This path is safe. **However**, consider the case where `medley()` *succeeds* but the writer is asked for a bridge at a join, and the writer returns a bridge. The `ly_shape` check compares `sorted(bridged) != sorted(med["flagged"])`. If `med["flagged"]` is `[]` (no joins flagged) but the writer still returns a non-null bridge (which `write_takeaway` should reject via `if join is None: raise ValueError`), this is caught.

**Re-examination:** The real risk is in `write_takeaway`: if `join is None` and the model returns a non-null bridge, it raises `ValueError`. If `join is not None` and the model returns `null`, `build()` drops the clip and re-lines. So the writer contract is enforced.

**Verdict on P0-1:** Not a P0. The fail-closed path in `build()` prevents unmeasured verdicts from reaching `ly_shape`. Downgrading.

---

### P0-2: `takeaway_budget` can return a range where the *lower* bound produces a runtime estimate below 60 s
**File:** `pipeline/package.py`, `takeaway_budget()` (lines ~111-124 in diff)

**Scenario:**
- `content_s = 33.0` (just above `medley_content_range()[0]` = 32.7).
- `fixed = 33.0 + 14.30 + 0 = 47.30` (no other VO lines).
- `words_at(61.5) = 2.5 * (61.5 - 47.30 - 1.0) = 2.5 * 13.2 = 33.0` → `lo = max(8, ceil(33.0 - 1e-9)) = 33`.
- `words_at(68.5) = 2.5 * (68.5 - 47.30 - 1.0) = 2.5 * 20.2 = 50.5` → `hi = min(30, floor(50.5 + 1e-9)) = 30`.
- `lo = 33 > hi = 30` → falls through to `RUNTIME_S` check:
  - `words_at(60.0) = 2.5 * (60.0 - 47.30 - 1.0) = 2.5 * 11.7 = 29.25` → `lo = max(8, 29) = 29`.
  - `words_at(70.0) = 2.5 * (70.0 - 47.30 - 1.0) = 2.5 * 21.7 = 54.25` → `hi = min(30, 54) = 30`.
  - `lo=29 <= hi=30` → returns `(29, 30)`.
- Writer produces 29-word takeaway. `runtime() = 33.0 + 29/2.5 + 1.0 + 14.30 = 33.0 + 11.6 + 1.0 + 14.30 = 59.9 s`.
- **59.9 < 60.0** → `rt_ok = False` → cheap gate fails.

The budget *should* have returned `None` or a range that guarantees ≥ 60 s. The `LY_AIM_S` check failed (correctly), but the `RUNTIME_S` fallback uses `math.ceil(words_at(a) - 1e-9)` which can round *down* to a word count that lands just below the target. The `-1e-9` epsilon is meant to handle floating-point noise, but here it causes `ceil(29.25 - 1e-9) = 29` when the true minimum to reach 60 s is `ceil(29.25) = 30`.

**Fix:** Use `math.ceil(words_at(a))` without the epsilon subtraction for the lower bound, or verify the resulting runtime after computing `lo`.

**Impact:** A package that should pass the runtime gate fails, wasting a write attempt. Not a security issue, but a correctness bug that can cause unnecessary re-writes or, if the writer is at its last attempt, a failed build.

---

### P0-3: `lineup_for` with `repeat_ok=True` can select two clips from the same channel *and* same video
**File:** `pipeline/package.py`, `lineup_for()` (lines ~378-380 in diff)

**Code:**
```python
if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
    continue
```

**Scenario:**
- `n = 2` (hook + 2 clips = 3 segments).
- `chans = ["A", "A", "B"]` → `len(set(chans)) = 2 ≠ 3`.
- `repeat_ok=True`, `len(set(chans)) == 2 == n` ✓.
- `video_ids = ["v1", "v1", "v2"]` → `len(set) = 2 ≠ 3` → **skipped**. Correct.
- `video_ids = ["v1", "v2", "v2"]` → `len(set) = 2 ≠ 3` → **skipped**. Correct.
- `video_ids = ["v1", "v2", "v3"]` → `len(set) = 3 == n+1` → **allowed**. But `chans = ["A", "A", "B"]` means two clips from channel A, from videos v1 and v2. This is the intended supply exception.

Wait — the condition `len({m["video_id"] for m in (h, *combo)}) == n + 1` requires *all* video IDs to be distinct. With 3 segments, it requires 3 distinct videos. If channel A provides two clips, they must be from two different videos. This is correct per L-y 4.

**Re-examination:** The logic is sound. Downgrading.

---

## P1 Findings

### P1-1: `medley()` prompt includes clip text up to 900 chars, but `CI._q` may truncate mid-word
**File:** `pipeline/package.py`, `medley()` (line ~433 in diff)

**Code:**
```python
clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
                  for lb, m in zip(labs, segs))
```

If `CI._q` truncates at 900 chars without word-boundary awareness, the model sees a clipped sentence. The through-line and join assessments may be degraded. This is a quality issue, not a gate failure, but it can cause false "unfollowable" flags or missed through-lines.

**Recommendation:** Ensure `CI._q` truncates at word boundaries and appends an ellipsis.

---

### P1-2: `write_takeaway` does not validate that the takeaway text is ≤ 30 words
**File:** `pipeline/package.py`, `write_takeaway()` (lines ~461-523 in diff)

The prompt asks for `{lo}-{hi} words`, and `takeaway_budget` caps `hi` at `MOMENTS_TAKEAWAY_WORD_CAP` (30). However, the *validation* of the model's reply only checks:
- Keys are exactly `{"takeaway", "bridge", "title", "caption"}`.
- `takeaway` has `text` and `cites`.
- Title ≤ 70 chars, caption ≤ 220 chars.

**There is no check that `len(obj["takeaway"]["text"].split()) <= MOMENTS_TAKEAWAY_WORD_CAP`.**

If the model returns a 35-word takeaway, it passes `write_takeaway` and proceeds to `assemble_medley` and `cheap_checks`. The runtime gate may catch it (if the estimate exceeds 70 s), but if the clips are short enough, a 35-word takeaway could land within 60-70 s and pass all gates, violating L-y 5's 30-word cap.

**Fix:** Add to `write_takeaway` validation:
```python
if len(obj["takeaway"]["text"].split()) > MOMENTS_TAKEAWAY_WORD_CAP:
    raise ValueError(f"takeaway is {len(obj['takeaway']['text'].split())} words (max {MOMENTS_TAKEAWAY_WORD_CAP})")
```

---

### P1-3: `ly_shape` does not verify the takeaway is *after* the last clip in the `lines` list
**File:** `pipeline/package.py`, `ly_shape()` (lines ~526-561 in diff)

`ly_shape` checks:
- `after[-1] == n_clips` (the last `bridges_after_clip` entry is the last clip index).
- `bridges[-1]` is non-empty (the takeaway text exists).

But it does not verify that the `lines` list has the takeaway slot *after* all clip segments. The `assemble_medley` function constructs `lines` in the correct order, but if a future refactor changes the order, `ly_shape` would not catch it.

**Recommendation:** Add a check that the `takeaway` slot appears after all `clip_*` slots in `pk["lines"]`.

---

### P1-4: `providers.py` `_reported` accepts `float` but `usd_reported` in the ledger is rounded to 8 places
**File:** `pipeline/providers.py` (lines ~943-950, ~982-988 in diff)

**Code:**
```python
def _reported(usd):
    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}
```

In `_settle`:
```python
if _num(usage.get("usd_reported")):
    rep = float(usage["usd_reported"])
    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8), ...)
    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
```

The per-backend and per-role accumulations are rounded to 8 places, but the *total* `d["usd_reported"]` is also rounded to 8 places. This is consistent. However, `usd_unreported_estimate` is rounded to 6 places, while `usd_estimate` is also 6 places. The mixed precision (8 for reported, 6 for estimate) is intentional but should be documented.

**Not a bug**, but a potential source of confusion in audit.

---

### P1-5: `proof_ly.py` hardcodes `SCRATCH` path with a specific UUID
**File:** `tests/package/proof_ly.py` (line ~1071 in diff)

```python
SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
```

This path is environment-specific and will not exist on other machines or after a reboot. The `--work-dir` argument defaults to this path, so running `proof_ly.py` without `--work-dir` will fail.

**Fix:** Use a temporary directory or a configurable path.

---

## P2 Findings

### P2-1: `medley_content_range` does not account for the bridge's pre-roll when `n_bridges > 0`
**File:** `pipeline/package.py`, `medley_content_range()` (lines ~102-108 in diff)

**Code:**
```python
def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
    return round(lo, 2), round(hi, 2)
```

This is correct: the bridge's seconds are subtracted from the available clip seconds. The takeaway's seconds are also subtracted. The test `test_the_medley_seconds_let_one_takeaway_land_60_to_70` verifies this.

**No issue.**

---

### P2-2: `lineup_for` sorts by `pos[m["moment_id"]]` but `pos` is built from `angle["moments"]`
**File:** `pipeline/package.py`, `lineup_for()` (lines ~364-392 in diff)

**Code:**
```python
pos = {m: i for i, m in enumerate(angle["moments"])}
...
order = sorted(combo, key=lambda m: pos[m["moment_id"]])
```

This preserves the proposer's play order. Correct.

**No issue.**

---

### P2-3: `assemble_medley` does not validate that `fields["takeaway"]` exists
**File:** `pipeline/package.py`, `assemble_medley()` (lines ~207-232 in diff)

If `fields` lacks a `"takeaway"` key, `fields["takeaway"]` will raise `KeyError`. However, `write_takeaway` always includes `"takeaway"` in the returned `fields` dict (it's part of the validated model reply). So this is safe in practice.

**No issue.**

---

### P2-4: `package_pin.bridge_slots` for a medley with no bridge
**File:** `pipeline/package_pin.py` (lines ~882-890 in diff)

**Code:**
```python
def bridge_slots(pk):
    vo = pk.get("vo") or {}
    after = list(vo.get("bridges_after_clip") or [])
    last = len(pk.get("segments") or []) - 1
    if pk.get("shape") == "medley":
        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]
```

For a medley with no bridge, `after = [n_clips]` (just the takeaway). `last = n_clips`. So `bridge_slots` returns `["takeaway"]`. Correct.

For a medley with a bridge after clip 1 and the takeaway after clip 3 (n_clips=3): `after = [1, 3]`. `last = 3`. Returns `["bridge_1", "takeaway"]`. Correct.

**No issue.**

---

### P2-5: `test_medley.py` does not test the P1-2 scenario (takeaway > 30 words)
**File:** `tests/package/test_medley.py`

The tests cover the arithmetic, lineup, clips-alone verdict, writer contract, `ly_shape`, and pin. But there is no test that verifies a >30-word takeaway is rejected. This is a test gap corresponding to P1-2.

---

## Summary of Verified Issues

| ID | Severity | File | Issue |
|----|----------|------|-------|
| P0-2 | P0 | `package.py:takeaway_budget` | Lower bound can produce runtime < 60 s due to `ceil(x - 1e-9)` |
| P1-2 | P1 | `package.py:write_takeaway` | No validation that takeaway ≤ 30 words |
| P1-1 | P1 | `package.py:medley` | Clip text truncation may be mid-word |
| P1-3 | P1 | `package.py:ly_shape` | Does not verify takeaway slot order in `lines` |
| P1-5 | P1 | `proof_ly.py` | Hardcoded scratch path |
| P2-5 | P2 | `test_medley.py` | Missing test for >30-word takeaway rejection |

## Verdict

**SHIP: no**

**Conditions for ship:**
1. Fix P0-2: Ensure `takeaway_budget` returns a range where the lower bound produces a runtime estimate ≥ 60 s.
2. Fix P1-2: Add a word-count check for the takeaway in `write_takeaway`.
3. Add a test for P1-2 in `test_medley.py`.
4. Fix P1-5: Make the scratch path configurable or use `tempfile`.
5. Address P1-1 and P1-3 as follow-ups (lower risk).