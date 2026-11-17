# qwen3.8-27b (qwen/qwen3.8-27b) 85 s finish=stop usage in 11034 / out 6853 usd_reported=0.005399 usd~0.136 (upper-bound price)



# Code Audit — RULING 130 (2): Lock Pre-Check Before Paid Vision

## Scope

I reviewed the 224-line diff implementing RULING 130 (2): reordering the render's lock pre-check (rulings 68/72) to execute **before** any paid check (vision `see()`, exclusion `exclusion_for`, truth `truth_for`), in both the main line-up loop and the no-voice line-up, plus the `--lock-precheck on|off` driver flag and its tests.

---

## Findings

### [P2] `bg = {}` orphan-future invariant is comment-only

In the main loop, when the lock passes but `vbad` subsequently triggers a re-line, the pool futures already submitted into `bg` are never collected (the writes loop is skipped via `w_used = writes`). This is **pre-existing** behaviour (the original code had the same pattern), but the new code makes the invariant more load-bearing: `bg` is now conditionally populated (`bg = {}` vs. the full dict), and the only thing preventing a silent no-op is that the writes loop's first test breaks on `w_used`. A future refactor of the writes loop that moves the `w_used` check later, or adds a second reader of `bg`, would silently discard submitted work.

Suggestion: add a one-line assertion or a `# INVARIANT: bg is read only at package.py:3878 inside the writes loop; w_used=writes guarantees we never reach it when bg=={}` comment at the `bg = {}` site, or better, gate the pool submissions behind a flag that the writes loop also checks.

Not a merge-blocker because the current code is correct and the pattern is unchanged from the original.

---

### [P3] `lock_for` iterator is per-call, not per-build

```python
def lock_for(mode, out_dir, say):
    if mode != "on":
        return lock_off
    n = iter(range(1, 10 ** 6))
    return lambda segs: LP.check(segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say)
```

Each invocation of `lock_for` creates a fresh counter. This matches the original (which used a default-argument iterator `n=iter(range(1, 10**6))` on the lambda), so numbering restarts if the build is re-entered. In practice the build is single-shot per process, so this is cosmetic. No action needed.

---

### [P3] No defensive `isinstance(pre, dict)` guard

If `lock_check(segs)` ever returned `None` (contract violation), `pre.get("error")` would raise `AttributeError` outside the `try/except` (the `except` only wraps the call, not the subsequent attribute access). The contract of `lock_precheck.check` and `LP.failed` guarantees a dict, and the original code had the same exposure, so this is not a regression. Noting for completeness.

---

## Verification of the five requested checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | No paid check runs for a line-up the lock holds or gives no verdict on | **PASS.** Main loop: `bg` and `see(segs)` are inside `if not relined and not no_verdict:`. No-voice: `see(order)` is after the `return None` on lock failure. Tests `test_ruling_130_a_clip_the_lock_holds_is_never_seen` and the no-verdict assertion confirm `visual_calls` excludes held/never-seen clips. |
| 2 | A passing line-up is unchanged in every other respect | **PASS.** When the lock passes (no error, segments present, no held), `relined` and `no_verdict` stay `False`, so `bg` is populated identically to the original, `see(segs)` runs, `vbad` is computed, and the writes loop reads `bg` at the same site. The lock_check body itself is unchanged. |
| 3 | The no-voice path | **PASS.** `lock_check(order)` runs first; on error/no-segments it returns `None` before `see(order)`. On pass, `see(order)` and `vbad` proceed as before. The test asserts the held clip `"z"` is never in `visual_calls`. |
| 4 | `lock_off` can never be a pass | **PASS.** It returns `{"ok": False, "segments": [], "error": "not asked …"}`. Both the main loop (`pre.get("error")` truthy → no-verdict path) and the no-voice path (`nv_pre.get("error")` truthy → `return None`) treat it as a stop. `ok: False` + empty `segments` cannot satisfy any pass condition. |
| 5 | The tests | **PASS.** Three new/modified tests in `test_medley.py` (held-clip-never-seen, no-verdict-clip-never-seen, no-voice-held-clip-never-seen) and three in `test_ledger_build.py` (lock_off writes nothing, lock_for numbers requests, bad value refuses). The `lock_stub` with `calls` list correctly records lock invocations and the assertions on `visual_calls` verify the ordering. The 6/6 mutation kill rate is reported. |

---

## Law compliance

- **M12 (fail closed):** `lock_off` and any lock exception produce a no-verdict (budget class, search stops), never a pass. ✓
- **LAW 20 / M2:** No gate threshold is modified; the lock_check body is unchanged. ✓
- **Smallest diff / no new renderer:** The change is a reordering plus a conditional guard; no new module, renderer, or selector. ✓
- **L-d (protected preview):** Not touched by this diff. ✓

---

## Verdict

The diff correctly implements RULING 130 (2). The lock pre-check gates all paid work in both the main and no-voice paths, `lock_off` is a strict no-verdict, and the tests pin the ordering. The one structural fragility (the `bg = {}` / writes-loop invariant) is pre-existing and adequately documented in the inline comment.

**P1_OR_WORSE: 0**