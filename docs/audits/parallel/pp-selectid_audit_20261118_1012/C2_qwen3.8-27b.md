# qwen3.8-27b (qwen/qwen3.8-27b) 263 s finish=stop usage in 9840 / out 8534 usd_reported=0.007865 usd~0.158 (upper-bound price)



# CYCLE 2 CODE AUDIT — pp-selectid-20261118_1012 (RULINGS 148 (1) / 149)

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I flagged the rounding in `runtime_short` as P3 and verified the core logic. What I under-weighted:

- **Qwen's re-entrancy observation** (nested `build()` clearing `_FLOOR` mid-pass). I dismissed it too quickly. While the current call graph has no recursion, the `global _FLOOR` + `try/finally` pattern makes the invariant "floor is set for the entire soft pass" depend on the call graph staying flat. A future retry loop that calls `build()` from within `_build()` would silently revert the floor to `None` for the remainder of the outer pass. This is a latent structural fragility, not a live bug, but it's worth noting as the reason the explicit-parameter refactor (Qwen's suggested fix) is the right long-term move.
- **Qwen's dangling-comment observation** in `package_pin.py` line 146. I missed this in Cycle 1. It's syntactically harmless but visually breaks the `SOFT_GATES` block.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My verdict |
|---|---|---|
| `_FLOOR` concurrent leak (P1) | GPT-OSS-20B | **Disagree / Refuted.** The consensus is correct: no process calls `build()` concurrently. The sole driver (`proof_ledger.py`) calls `PK.build` sequentially (lines 607, 626, 638), then `SPOT.build` (648). Each build is its own process (`build_and_record.sh`). No thread pool, no greenlet, no Flask route touches `package.build`. The module global is per-process. |
| `_FLOOR` concurrent leak (P2) | Qwen3.8-27B | **Disagree for this codebase, agree as a general pattern concern.** Same refutation as above. The `~1000 concurrent users` tech-stack note applies to the *serving* layer, not the batch pipeline. The pipeline is GPU0-only, sequential. |
| Re-entrancy (P3) | Qwen3.8-27B | **Partially agree.** No current code path re-enters `build()`. But the global-state pattern makes the invariant fragile. Not a defect today; a maintenance hazard. |
| Rounding `int(round(est))` (P3) | Gemma, Qwen | **Agree.** `est = 59.6` → `round` → 60 → "This video runs 60 seconds, shorter than usual." Self-contradictory. Low probability (estimate is a discrete sum of word-count × wps + constants), but the fix is one character: `int(est)` instead of `int(round(est))`. |
| Dangling comment (P3) | Qwen | **Agree.** Line 146 of `package_pin.py` starts at column 0, outside the `frozenset(...)`. Syntactically valid, visually confusing. |
| Floor leakage into clean pass | All models | **Agree: no leak.** `_FLOOR` is `None` during the clean pass. It is set *after* the clean pass returns `None`, and cleared in `finally`. The test asserts `PK._FLOOR is None` after the pass. |
| Under-30s / over-70s / non-medley sealing | All models | **Agree: all correctly refused.** `lineup_ok` uses `ly_lo(lo)` for the lower bound (30.0 in soft pass) and unchanged `hi` (70.0) for the upper. `runtime_short` requires `shape == "medley"`, `est < 60`, and `sum(durations) >= _FLOOR`. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] `takeaway_budget` fallback: the `cap < words_at(RUNTIME_S[0])` guard is correct but the boundary is tight.**

At line 47 of the diff:
```python
if _FLOOR is not None and content_s >= _FLOOR and LY_TAKEAWAY_MIN_WORDS <= cap < words_at(RUNTIME_S[0]):
```

If `cap == words_at(RUNTIME_S[0])` exactly (the content is *just* long enough to land 60 s with the maximum takeaway), the standard 60–70 s range would produce `lo <= hi` and return before reaching the fallback. So the `<` is correct — the fallback only fires when the standard range is genuinely empty. No bug, but the boundary is worth a comment for the next reader.

**[P3] `runtime_short` is called twice per package in the soft pass.**

At both `inventory` call sites (diff lines 87 and 96), `runtime_short(pk)` is called. Additionally, `cheap_checks` calls it (diff line 78). That's three calls per package. Each call re-sums `pk["segments"]` durations. For a package with ~5 segments this is negligible, but it's redundant. A local variable in `_build` would avoid the repeated work. Not a correctness issue.

**No new P0, P1, or P2 findings.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Floor scoping (`_FLOOR` global, `ly_lo`, `build` try/finally) | Clean | Clean | Confirmed by consensus refutation. Sequential, per-process. No change. |
| Acceptance bounds (`lineup_ok`, `lineup_for`) | Clean | Clean | `ly_lo(lo)` correctly lowers the floor to 30.0 in soft pass; `hi` unchanged at 70.0. Preference key still uses calibrated middle. |
| `runtime_short` gate | P3 (rounding) | P3 (rounding) | Unchanged. `int(round(est))` can display 60 for est ∈ [59.5, 60.0). Cosmetic. |
| `takeaway_budget` fallback | Clean | Clean | Guard conditions verified. `lo ≤ hi` always holds. `bridge_budget` inherits correctly. |
| `cheap_checks` / `inventory` integration | Clean | Clean | `rt_ok` OR-logic correct. FLAGGED override only when `short and rt_ok`. Clean pass unaffected (`_FLOOR` is None → `runtime_short` returns None). |
| `package_pin.SOFT_GATES` | Clean | P3 (dangling comment) | "runtime" correctly added. Comment on line 146 is at column 0, outside the frozenset. Style only. |
| Tests | Clean | Clean | Three tests cover: clean-pass-unchanged, soft-pass-seals-flagged, under-floor-refused, budget fallback, sentence refusals. `_FLOOR` cleared assertion present. 7/7 mutations killed. |

## 5. FINAL PRIORITY LIST

| # | Severity | File / Line | Issue |
|---|---|---|---|
| 1 | [P3] | `pipeline/package.py`, `runtime_short` (diff line 36) | `int(round(est))` can produce "60 seconds, shorter than usual" for `est ∈ [59.5, 60.0)`. Fix: `int(est)` (floor) or guard `est < RUNTIME_S[0] - 0.5`. |
| 2 | [P3] | `pipeline/package_pin.py`, line 146 | Comment `#   package.LY_FLOOR_S (30 s) or more…` starts at column 0, outside the `frozenset(...)`. Move inside the parenthesised block or attach to the `"runtime"` line. |
| 3 | [P3] | `pipeline/package.py`, `build()` (diff lines 105–110) | The `global _FLOOR` + `try/finally` pattern is correct for the current sequential, single-process pipeline but fragile against future re-entrancy. Consider threading the floor as an explicit parameter through `_build` → `lineup_ok` / `lineup_for` / `takeaway_budget` / `runtime_short`, or using a `contextvars.ContextVar`. Not a blocker; a maintenance improvement. |

**No P0, P1, or P2 findings.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Replace `int(round(est))` with `int(est)` in `runtime_short` — it eliminates the only user-visible contradiction ("60 seconds, shorter than usual") and is a one-character fix that costs nothing.

## 7. PRODUCTION READY?

**Yes.**

The code is correct for its deployment context: a sequential, single-process GPU batch pipeline where `build()` is never called concurrently or recursively. The floor is properly scoped to the never-empty pass, the clean pass is provably unchanged, all boundary conditions (under 30 s, over 70 s, non-medley, non-numeric estimate, bool estimate) are correctly refused, the takeaway-budget fallback produces a valid range, the gate integration (FLAGGED status, SOFT_GATES, `gate_problems`) is consistent, and the test suite covers the critical paths with 7/7 mutation kills.

The three P3 items (rounding, dangling comment, global-state fragility) are cosmetic or maintenance-hygiene issues that do not affect correctness in the current or near-term call graph. They can be addressed in a follow-up cleanup commit.

P1_OR_WORSE: 0