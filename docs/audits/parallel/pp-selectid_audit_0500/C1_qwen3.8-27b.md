# qwen3.8-27b (qwen/qwen3.8-27b) 46 s finish=stop usage in 7523 / out 1652 usd~0.047 (upper-bound price)

# Audit: pp-selectid-0500 / C1_STEP.diff (Ruling 37)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/package.py:1285-1290` — Re-line loop termination is not guaranteed by the diff (L-m / fail-closed risk)**
The new block drops `segs[1]["moment_id"]` and `continue`s. The diff does not show the enclosing `while`/`for` loop, the `dropped` set's initial state, or the loop's exit condition.
- **Scenario:** If the loop iterates over a fixed list of candidate angles and `dropped` is not checked to prevent re-processing, or if the loop condition does not account for `len(segs)` shrinking, a pathological input (e.g., all clips flagged in the clips-alone verdict) could either:
  - (a) loop indefinitely if the loop is `while True` without a `len(segs) < MIN` break, or
  - (b) silently produce a package with fewer than the required 3-5 segments, which `ly_shape` would then catch—but only if `ly_shape` is called *after* the loop. If `ly_shape` is not called on the final package before sealing, a malformed package could be sealed.
- **Verification needed:** Confirm the loop has a hard bound (e.g., `while len(segs) >= 3 and attempts < MAX`) and that `ly_shape` is invoked on the final `pk` before `write_takeaway` seals it. The diff shows `ly_shape` exists but not that it is called in the `build()` path after the re-line loop.

**2. `pipeline/package.py:868-870` — `ly_shape` only checks `js[0]` (the first join)**
The check is:
```python
elif question_hook(segs) and js and js[0] in med["flagged"]:
```
This only inspects the *first* join (`hook -> clip_01`). If a question hook is followed by multiple clips, and a *later* join (e.g., `clip_01 -> clip_02`) is flagged, `ly_shape` does not refuse it. However, the Ruling 37 text says "the clips-alone verdict judges the join after it as usual," and the render's R1 only cares about the join *immediately after the hook*. So this is likely correct by design. **But:** the `build()` re-line logic at line 1285 also only checks `joins(labs)[0]`. If the clips-alone verdict flags *only* a later join (not the first), the re-line does not trigger, and the bridge logic at line 1292-1294 will attempt to bridge the flagged later join. This is correct per the ruling (bridges are allowed between clips, just not after a question hook). **No issue here**, but the asymmetry between `ly_shape` (only checks `js[0]`) and the general bridge rule (checks all flagged joins) is worth noting.

## P2 Findings

**3. `pipeline/eligibility.py:411` — Comment references "RULING 37 (03:12 ET Nov 13)" but the diff header says "Generated: 2026-11-13 04:57 UTC"**
Minor timestamp inconsistency. The ruling is cited as 03:12 ET, which is 07:12 UTC (Nov 13), not 04:57 UTC. This is a documentation nit, not a code defect.

**4. `pipeline/package.py:24-27` — `question_hook` uses `str(segs[0].get("text") or "").rstrip().endswith("?")`**
This is a string-level check. If the hook's text is stored with a trailing newline or other whitespace, `rstrip()` handles it. However, if the text is `None` or missing, `or ""` handles it. **Edge case:** If the text is `"Why does Bitcoin keep falling every time Nvidia does? "` (trailing space), `rstrip()` removes it and `endswith("?")` is `True`. This matches the render's R1 test as described. **No issue.**

**5. `tests/package/test_medley.py:95-102` — Test `test_a_flagged_join_after_a_question_hook_re_lines_without_that_clip`**
The test asserts `rig.medley_calls == [["h", "x", "y"], ["h", "y", "z"]]`. This implies the re-line loop tried two line-ups: first with `x` (dropped), then with `y` and `z`. The test does not verify that the loop *terminated* or that `dropped` was checked. This is a test coverage gap, not a code defect, but it means the test does not prove the loop cannot loop forever.

**6. `pipeline/package.py:1285-1290` — `dropped.add(segs[1]["moment_id"])`**
If `segs[1]` does not have a `"moment_id"` key, this raises `KeyError`. The diff does not show how `segs` is constructed, but the test at line 88 uses `pm("h", "A", 12.0)`, which likely includes a `moment_id`. **Assume safe**, but if `segs` can contain dicts without `moment_id`, this is a crash risk.

## Verification of Specific Checks

- **Question can end ONLY the hook, never a middle or last clip:** ✅ Verified. `eligibility.py:411` adds `and role != "hook"` to the `not_statement` check. The test at `test_eligibility.py:67-68` confirms a clip still gets `not_statement`.
- **The join after a question hook can never carry a bridge in a sealed pin:** ✅ Verified. `build()` drops `clip_01` if the first join is flagged (line 1285-1290), so no bridge is placed. `ly_shape` refuses a package where the first join is flagged (line 868-870). The render's R1 (not in this diff) is stated to refuse a bridge after a question hook.
- **The re-line cannot loop forever:** ⚠️ **Not verifiable from the diff.** The loop structure is not shown. See P1-1.
- **Nothing else changes:** ✅ Verified. The diff is minimal and focused. No other files are modified.

## SHIP: **yes with conditions**

**Conditions:**
1. **Confirm the re-line loop in `build()` has a hard termination bound** (e.g., `while len(segs) >= 3 and attempts < MAX_RELINE`). If the loop is unbounded, this is a P0.
2. **Confirm `ly_shape` is called on the final package before sealing.** If it is not, a malformed package (e.g., too few segments after re-line) could be sealed.
3. **Add a test that verifies the re-line loop terminates** when all clips are flagged (e.g., a test where the clips-alone verdict flags every join, and the loop exits with a "no valid line-up" error rather than looping forever).

If conditions 1 and 2 are confirmed by the integrator, this is a clean, minimal, well-tested implementation of Ruling 37.