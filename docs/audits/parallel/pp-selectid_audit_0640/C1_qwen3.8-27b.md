# qwen3.8-27b (qwen/qwen3.8-27b) 99 s finish=stop usage in 13481 / out 3341 usd~0.091 (upper-bound price)

# Audit: pp-selectid-0640 (Step-A Dual-Vendor Verdicts)

## P0 Findings

**None.** The core safety invariants (L-m fail-closed, L-x vendor separation, item 44/45 ordering) are correctly implemented. The critical fail-open bug (K2: stale verdict reused when re-screen returns nothing) is fixed. No clip can reach the angle prompt or a line-up without passing step A on both vendors.

## P1 Findings

### P1-1: `second_screen` — unhandled exception in `f.result()` aborts the entire build
**File:** `pipeline/package.py`, line 28 (in `second_screen`)

```python
res = [f.result() for f in futs]
```

If any `prescreen` call raises an uncaught exception (network timeout, provider crash, JSON parse error in the router), `f.result()` re-raises it. This propagates out of `second_screen` → out of `build()` → the entire build crashes with a traceback rather than failing closed with a structured `out["why_none"]` or `out["prescreen"]["second_vendor"]` entry.

**Scenario:** Heimdall's GPU node is under load; the second-screen batch for the `xai` group times out after 300 s. The `ThreadPoolExecutor` future holds a `TimeoutError`. `f.result()` raises it. The build dies. No package, no structured log, no `ATTESTATION.json`.

**Law violated:** M12 (fail closed — an exception should reject, not crash the process). The rest of `build()` handles provider failures gracefully (the `prescreen` function itself catches per-clip failures into `fails`), but the *orchestration* of parallel calls does not.

**Fix:** Wrap `f.result()` in a try/except per future; on exception, mark all clips in that chunk as `STEP_A_UNAVAILABLE: <exception>`.

---

### P1-2: `second_screen` — `a_by[mid]` is read without a guard for missing keys
**File:** `pipeline/package.py`, line 40 (in `second_screen`)

```python
two[mid] = [a_by[mid], a2]
```

The function iterates `cleared.items()` and looks up `a_by.get(mid)` on line 21 (safe, returns `None`), but on line 40 it does a direct `a_by[mid]` index. If `a_by` does not contain a key for a moment in `cleared` (e.g., the first `prescreen` call in `build()` failed to produce a verdict for that moment but it was still added to `cleared` by an earlier stage), this raises `KeyError`.

**Scenario:** A moment passes L-v 2 and CUTTABLE but the first `prescreen` batch had a transient error that was swallowed (the `prescreen` function returns it in `fails`, but `build()` may have added it to `cleared` before checking `fails` — this depends on code not in the diff). If `a_by` lacks the key, `second_screen` crashes.

**Mitigating factor:** The diff shows `a_by` is populated by the first `prescreen` call in `build()` (line 54 context: `a_by` is passed in). If the first screen always populates `a_by` for every moment in `cleared`, this is safe. But the code does not enforce this invariant.

**Fix:** Use `a_by.get(mid)` and treat `None` as `STEP_A_UNKNOWN_BACKEND`.

---

### P1-3: `off_writers` — `writers_f` is a set of families, but `b.family not in writers_f` may not match the intended semantics
**File:** `pipeline/package.py`, line 79 (in `off_writers`)

```python
if b is not None and b.vendor not in writers_v and b.family not in writers_f:
```

`writers_f` is built as `{angle_reply.family}` (line 72) and then `writers_f.add(wr.family)` after each write (line 90). The check `b.family not in writers_f` is correct *if* `writers_f` contains all families that have written. However, the initial `writers_f = {angle_reply.family}` only captures the angle writer's family. If the angle writer is `heimdall:deepseek` (family `deepseek`), and a later write is by `heimdall:qwen` (family `qwen`), then `writers_f = {"deepseek", "qwen"}`. A verdict from `xai:grok` (family `grok`) passes. This is correct.

But consider: the angle writer is `xai:grok` (vendor `xai`, family `grok`). `writers_v = {"xai"}`, `writers_f = {"grok"}`. A verdict from `heimdall:deepseek` (vendor `heimdall`, family `deepseek`) passes both checks. Correct.

**No bug here.** Retracting this finding. The logic is sound.

---

### P1-4: Re-screen after write — `a_two.setdefault(mid, []).append(got_a[mid])` may append a verdict that is *on* a writer's vendor
**File:** `pipeline/package.py`, line 109 (in the re-screen block)

```python
a_two.setdefault(mid, []).append(got_a[mid])
```

The re-screen calls `prescreen(router, stale, sources, ctx, writers_v, writers_f, ...)`, which avoids `writers_v` and `writers_f`. So `got_a[mid]` should be off the writers. However, `a_two` is also used by `off_writers` (line 77), which iterates `a_two.get(mid, ())` and checks `b.vendor not in writers_v and b.family not in writers_f`. If a *later* write adds a new vendor/family to `writers_v`/`writers_f`, a verdict that was off the writers *at the time it was added* may now be *on* a writer. `off_writers` handles this correctly (it re-checks against the current `writers_v`/`writers_f`), so this is not a bug.

**No bug here.** Retracting.

---

### P1-5: `second_screen` — `PRESCREEN_BATCH` slicing may produce an empty chunk if `len(g)` is 0
**File:** `pipeline/package.py`, line 23-24

```python
jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
        for i in range(0, len(g), PRESCREEN_BATCH)]
```

If `g` is empty, `range(0, 0, PRESCREEN_BATCH)` is empty, so no job is created. This is safe. No bug.

---

### P1-6: `build()` — `cleared` is filtered *after* `second_screen`, but `a_by` still contains entries for filtered-out clips
**File:** `pipeline/package.py`, line 58

```python
cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
```

After this line, `cleared` no longer contains clips that failed the second screen. But `a_by` still has entries for them. Later, `off_writers` (line 77) iterates `a_two.get(mid, ())` for `mid in cleared` (line 82), so it only touches clips in `cleared`. The re-screen block (line 93) iterates `segs` (the line-up), which is built from `cleared`. So `a_by` entries for filtered-out clips are never read. This is safe but leaves stale data in `a_by`.

**Not a bug, but a minor inconsistency.** If any future code iterates `a_by` directly (rather than through `cleared` or `a_two`), it may see verdicts for clips that are no longer in the build.

---

## P2 Findings

### P2-1: `second_screen` — `max_workers=max(1, len(jobs))` may be excessive
**File:** `pipeline/package.py`, line 25

With 10-13 clips split into 2 groups (xai, heimdall), `len(jobs)` is at most 2 (one batch per group, since `PRESCREEN_BATCH = 8` and there are ≤ 13 clips). So `max_workers` is 2. This is fine. But if `PRESCREEN_BATCH` were smaller or there were more clips, the thread count could grow. Not a bug at current scale.

### P2-2: `second_screen` — the `log` parameter is passed to `prescreen` but the parallel calls' logs may interleave
**File:** `pipeline/package.py`, line 26

Multiple threads call `prescreen(..., log=log)` concurrently. If `log` is `print`, output may interleave. This is a cosmetic issue, not a correctness bug.

### P2-3: Test rig — `self.a_seen` is populated in `medley()` but the test `test_the_verdict_used_is_the_one_off_the_writers_vendor` asserts on it
**File:** `tests/package/test_medley.py`, line 191, 248, 252

The test asserts `set(rig.a_seen[0].values()) == {"xai:grok"}` or `{"heimdall:deepseek"}`. This verifies that the verdict *used* by the gates is off the writer's vendor. The test is correct and covers the L-x requirement.

### P2-4: `build()` — the `off_writers` function is defined inside `build()` and closes over `a_two`, `router`, `writers_v`, `writers_f`
**File:** `pipeline/package.py`, lines 74-81

This is a closure. It is called at line 83 (after the angle call) and line 92 (after each write). The closure captures the *current* values of `writers_v` and `writers_f` at the time of the call, not at the time of definition. This is correct Python behavior (closures capture variables, not values). No bug.

### P2-5: `second_screen` — the `groups` dict uses `(b.vendor, b.family)` as key, but `b` may be `None`
**File:** `pipeline/package.py`, line 22

```python
groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
```

If `b` is `None`, the key is `None`. Later, `groups.get(None, [])` (line 41) handles these. Correct.

### P2-6: `build()` — `out["prescreen"]["second_vendor"]` is built with a dict comprehension over `cleared` (the *original* `cleared`, before filtering)
**File:** `pipeline/package.py`, lines 55-57

```python
out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
                                     "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
                                     for mid in cleared}
```

This iterates the *original* `cleared` (before the filter on line 58). So it records PASS/FAIL for every clip that entered `second_screen`, including those that will be filtered out. This is correct for audit purposes.

---

## Verification of Key Invariants

| Invariant | Status |
|---|---|
| No clip reaches angle prompt without passing step A on both vendors (item 45) | **PASS.** `cleared` is filtered to `a_two` keys (line 58) before the angle call. `a_two` only contains clips with two passing verdicts from different vendors. |
| No clip reaches a line-up without passing step A on both vendors (item 45) | **PASS.** Line-ups are built from `cleared`, which is filtered. |
| The verdict used by gates is off every writer's vendor and family (L-x) | **PASS.** `off_writers` (line 74-81) selects a verdict off all current writers. `a_by[mid]` is set to this verdict (line 83, 92). The re-screen (line 102) avoids all writers. |
| A failed/missing re-screen removes only that clip (item 44) | **PASS.** `bad` dict contains only the failed clips. `dropped |= set(bad)`, `doomed |= set(bad)`. `swap_lineup` replaces only those slots. |
| The swapped line-up is judged on clips alone before any write (item 44) | **PASS.** After the swap, `relined = True` and `break` (line 122-123). The loop re-enters the clips-alone verdict stage. |
| Fail closed: no verdict is never a pass (L-m) | **PASS.** `second_screen` returns `STEP_A_UNAVAILABLE` for missing verdicts. The re-screen block (line 110-112) marks clips with no verdict as `bad`. |
| No loop, double-count, or inconsistency in `cleared`/`a_by`/`a_two` | **PASS.** `cleared` is only shrunk. `a_by` is updated in place. `a_two` is append-only. No cycles. |
| Existing behaviour unchanged for Heimdall-in-time builds | **PASS.** If the angle comes from Heimdall, `writers_v = {"heimdall"}`, `writers_f = {"deepseek"}`. `off_writers` selects the xai verdict. The re-screen is not triggered (no stale clips). The build proceeds as before, with the addition of the second screen (which is a no-op for clips that already passed on both vendors). |

---

## SHIP: yes with conditions

**Conditions:**
1. **Fix P1-1:** Wrap `f.result()` in `second_screen` with a try/except per future. On exception, mark all clips in that chunk as `STEP_A_UNAVAILABLE: <exception>`. This is a P1 because a single provider timeout can crash the entire build.
2. **Fix P1-2:** Use `a_by.get(mid)` in `second_screen` line 40, and treat `None` as `STEP_A_UNKNOWN_BACKEND`. This is a P1 because a `KeyError` would crash the build.

Both fixes are small (a few lines each) and do not change the logic. The rest of the diff is correct and well-tested. The 78 tests (72 before + 6 new) cover the key scenarios: dual-vendor screening, fail-closed on missing verdicts, vendor-aware verdict selection, single-clip swap on re-screen failure, and fail-closed on unknown/same-vendor backends.