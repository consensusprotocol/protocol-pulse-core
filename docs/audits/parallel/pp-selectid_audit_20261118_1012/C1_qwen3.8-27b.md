# qwen3.8-27b (qwen/qwen3.8-27b) 249 s finish=stop usage in 10567 / out 9710 usd_reported=0.008868 usd~0.177 (upper-bound price)



# Code Audit — pp-selectid (RULINGS 148(1)/149: 30 s floor + "runs short" flag)

## Findings

### [P2] `_FLOOR` global is not safe under concurrent `build()` calls

`pipeline/package.py` introduces a module-level mutable `_FLOOR` that is set and cleared around the never-empty pass:

```python
global _FLOOR
_FLOOR = LY_FLOOR_S
try:
    soft = _build(*args, soft=True, **kw)
finally:
    _FLOOR = None
```

The tech-stack section states **~1000 concurrent users at peak — every route must handle load**. If `build()` (or any code path that calls `ly_lo`, `takeaway_budget`, `runtime_short`, or `lineup_ok`) can be entered from more than one thread or greenlet while another `build()` is mid-never-empty-pass, the clean pass of the second caller will see `_FLOOR = 30.0` and accept 30–36.7 s line-ups it should refuse, or `runtime_short` will emit a flag for a package that was never in the never-empty pass.

The `finally` block guarantees cleanup for a single sequential call, but it does not protect against interleaving. The pipeline is described as a sequential batch (`run_fresh.py`, GPU0 only), so this may never fire in practice, but the pattern is a latent data-corruption bug the moment a Flask route, a retry, or a test harness calls `build()` concurrently.

**Suggested fix:** pass the floor as an explicit parameter through `_build` → `lineup_ok` / `lineup_for` / `takeaway_budget` / `runtime_short` (or use a `contextvars.ContextVar` if the call depth makes threading a parameter impractical). This also removes the need for the `global` statement and makes the state visible in every function signature.

---

### [P3] `int(round(est))` can display "60 seconds, shorter than usual"

In `runtime_short`:

```python
return RUNTIME_SHORT.format(n=int(round(est)))
```

If `est = 59.999` (just under `RUNTIME_S[0] = 60.0`), the guard `est >= RUNTIME_S[0]` is False, so the function proceeds, but `int(round(59.999))` is `60`. The sealed flag reads *"This video runs 60 seconds, shorter than usual."* — a listener (or a downstream text check under L-k) hears "60 seconds" and "shorter than usual" in the same sentence, which is self-contradictory.

The probability is low (the R4 estimate is a computed float, not a measured one), but the fix is trivial: use `int(est)` (floor) instead of `int(round(est))`, or guard with `est < RUNTIME_S[0] - 0.5` so the displayed integer is unambiguously below 60.

---

### [P3] Dangling comment line in `package_pin.py`

```python
                        "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
#   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
```

The second line of the comment starts at column 0, outside the `frozenset(...)` call. It is syntactically harmless (it's a module-level comment), but it breaks the visual grouping of the `SOFT_GATES` block and will confuse a reader scanning the set's entries. Move it inside the parenthesised block or attach it to the `"runtime"` line.

---

### [P3] Re-entrancy: a nested `build()` would corrupt the outer pass

If `_build` (or any helper it calls) ever re-enters `build()` — e.g., a future "try a different angle" retry that calls `build` recursively — the inner `build`'s `finally` clears `_FLOOR` to `None` while the outer never-empty pass is still running. The outer pass would then continue with `_FLOOR = None`, silently reverting to the clean-pass floor (36.7 s) for the remainder of its line-up search.

This is extremely unlikely in the current call graph, but the global-state pattern makes it a one-line refactor away from a real bug. The same fix as the [P2] finding (explicit parameter) eliminates this class of issue entirely.

---

## Items verified clean

| Question asked | Verdict |
|---|---|
| Can the floor leak into the clean pass? | No. `_FLOOR` is `None` during the clean pass; it is set only after the clean pass returns `None`. The `finally` clears it. (Subject to the [P2] concurrency caveat.) |
| Can a package under 30 s seal? | No. `lineup_ok` rejects `dur < ly_lo(lo) = 30.0`; `runtime_short` returns `None` when `sum(durations) < _FLOOR`. |
| Can a package over 70 s seal? | No. The upper bound `hi` in `lineup_ok` / `lineup_for` is unchanged. |
| Can a non-medley shape get the flag? | No. `runtime_short` requires `pk.get("shape") == "medley"`. |
| Can a bool sneak past the `isinstance(est, (int, float))` check? | No. `isinstance(est, bool)` is explicitly excluded. |
| Does the takeaway-budget fallback produce a valid (lo ≤ hi) range? | Yes. The guard `LY_TAKEAWAY_MIN_WORDS <= cap` ensures `max(MIN, cap−4) ≤ cap`. |
| Does `bridge_budget` inherit the fallback correctly? | Yes — it calls `takeaway_budget`, which now returns the shortened range in the pass. |
| Is the `SOFT_GATES` addition consistent with L-j (release auth)? | Yes. "runtime" is not in the REQUIRED set; a FLAGGED status on a SOFT gate does not block `release_auth.authorise()`. The flag counts toward `REVIEW_FLAGS_MAX = 3` as ruled. |
| Do the tests cover the stated must-fail / must-pass cases? | Yes. 33.9 s seals flagged in never-empty only; 27.9 s seals nothing; budget at 33.9 / 29.0 / 40.0 s; sentence refusals for 60 s, non-medley, and under-floor segments; `_FLOOR` cleared after the pass. |
| Smallest-diff / no new renderer / GPU0 / no publishing (M1, LAW 22)? | Complied. The diff touches only `package.py`, `package_pin.py`, and one test file. No renderer, compositor, or selector changes. |

---

P1_OR_WORSE: 0