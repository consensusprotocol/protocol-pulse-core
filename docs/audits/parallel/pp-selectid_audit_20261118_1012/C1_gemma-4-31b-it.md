# gemma-4-31b-it (google/gemma-4-31b-it) 176 s finish=stop usage in 11258 / out 3541 usd_reported=0.000788 usd~0.087 (upper-bound price)

The code implements Rulings 148 (1) and 149, introducing a "never-empty" pass floor for medley runtimes.

### Analysis

1.  **Floor Leakage & Scope**: The use of the global `_FLOOR` is safely encapsulated within `build()` using a `try...finally` block. This ensures that the floor is only active during the `_build(soft=True)` call and is guaranteed to be reset to `None` regardless of whether the build succeeds or raises an exception. It cannot leak into the clean pass or subsequent builds.
2.  **Boundary Enforcement**:
    *   **Under 30s**: `ly_lo(lo)` returns `min(lo, 30.0)`. If a lineup's duration is $< 30.0\text{s}$, `lineup_ok` and `lineup_for` will correctly reject it.
    *   **Over 70s**: The upper bound `hi` (from `RUNTIME_S[1]`) remains unchanged in `lineup_ok`, ensuring videos over 70s are still rejected.
    *   **Non-Medleys**: `runtime_short(pk)` explicitly checks `pk.get("shape") != "medley"`. If the shape is not a medley, the function returns `None`, and `rt_ok` reverts to the standard `RUNTIME_S` range check.
3.  **Takeaway Budget Fallback**: The logic in `takeaway_budget` correctly handles the case where the standard range `lo..hi` is empty (meaning the content is too short to hit the 60s target). It allows a fallback range `(max(MIN, cap - 4), cap)` only when `_FLOOR` is active and the content meets the 30s minimum. This enables the "soft" pass to seal packages that the "clean" pass would have rejected.
4.  **Gate Integration**:
    *   `cheap_checks` now treats a package as `rt_ok` if it is either in the standard range OR has a valid `runtime_short` string.
    *   `inventory` correctly overrides the `status` of the "runtime" gate to `FLAGGED` when `short` is provided and `rt_ok` is True.
    *   `package_pin.SOFT_GATES` now includes `"runtime"`, allowing the integrator to authorize these flagged packages.
5.  **Tests**: The new test suite `TestRuling148RuntimeFloor` comprehensively covers the clean pass vs. soft pass distinction, the 30s hard floor, the 36.7s soft floor, and the takeaway budget logic.

### Findings

*   **[P3] Rounding in `runtime_short`**: `int(round(est))` may round a value like $59.6$ up to $60$. Since the function only executes if `est < 60`, it is possible to produce the string `"This video runs 60 seconds, shorter than usual."` for a video that is technically $59.6\text{s}$. This is a minor cosmetic discrepancy.

P1_OR_WORSE: 0