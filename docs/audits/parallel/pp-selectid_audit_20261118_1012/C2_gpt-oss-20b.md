# gpt-oss-20b (openai/gpt-oss-20b) 18 s finish=stop usage in 9069 / out 2790 usd_reported=0.000626 usd~0.069 (upper-bound price)

**1. What the other models caught that I missed**

| Finding | Source | What was missed |
|---------|--------|-----------------|
| Global `_FLOOR` can leak between concurrent `build()` calls | GPT‑OSS‑20B, Qwen3.8‑27B | I only flagged the rounding issue; I did not note the race‑condition risk. |
| Re‑entrancy: a nested `build()` would corrupt the outer pass | Qwen3.8‑27B | I did not consider the possibility of a recursive call to `build()` (e.g., a retry helper). |
| Dangling comment line in `package_pin.py` | Qwen3.8‑27B | I overlooked the stray comment that breaks the visual grouping of `SOFT_GATES`. |
| Rounding in `runtime_short` can produce “60 seconds, shorter than usual” | Gemma‑4‑31B‑IT, Qwen3.8‑27B | I noted the rounding but did not explicitly list it as a separate finding. |

**2. Agreement / disagreement**

| Finding | Agreement | Why |
|---------|-----------|-----|
| Global `_FLOOR` race‑condition | **Agree** | The code uses a module‑level mutable variable that is set and cleared in a `try…finally`. If two `build()` calls interleave, the second may see the first’s `_FLOOR` value, causing incorrect gate logic. Even if the current deployment is single‑threaded, the risk exists if the code is reused elsewhere. |
| Re‑entrancy | **Agree** | A recursive `build()` would clear `_FLOOR` for the outer call, corrupting its soft‑pass logic. This is a realistic edge case if a future helper calls `build()` again. |
| Dangling comment | **Agree** | It is purely cosmetic but can confuse readers and break automated formatting. |
| Rounding in `runtime_short` | **Agree** | `int(round(est))` can round a value just under 60 to 60, producing a contradictory sentence. It is a cosmetic bug but worth fixing. |

**3. New findings from this review**

* The `runtime_short` function returns a string even when the estimate is exactly 60 s (because the guard is `est >= RUNTIME_S[0]`), but the rounding can still produce “60 seconds”.  
* The `takeaway_budget` fallback uses `_FLOOR` but does not guard against `_FLOOR` being `None` in a nested call; however, the guard `if _FLOOR is not None` already protects it.  
* The `inventory` function’s `runtime` gate row uses `dict(row(...), **{…})`. If `short` is `None`, the extra keys are omitted; if `short` is a string, the row gets `status: "FLAGGED"` and `flags: [short]`. This is correct but relies on the caller to pass `short` consistently.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Global `_FLOOR` race‑condition | P1 | **P2** | The risk is real but unlikely in current deployment; still a defect that should be mitigated. |
| Re‑entrancy | P2 | **P2** | Same reasoning as above. |
| Rounding in `runtime_short` | P3 | **P3** | Cosmetic but still a bug. |
| Dangling comment | P3 | **P3** | Cosmetic formatting issue. |
| Other logic (runtime gate, budget, etc.) | P0 | P0 | No new defects. |

**P1_OR_WORSE: 0**

**5. Final priority list**

| Priority | Issue | File:Line | Suggested fix |
|----------|-------|-----------|---------------|
| **P2** | Global `_FLOOR` race‑condition & re‑entrancy | `pipeline/package.py` lines 104‑110, 22‑26, 28‑36 | Replace the module‑level `_FLOOR` with a context‑aware parameter or `contextvars.ContextVar`. Pass the floor explicitly through `_build`, `lineup_ok`, `takeaway_budget`, `runtime_short`, etc. |
| **P2** | Re‑entrancy (nested `build()`) | Same as above | Same refactor as above; a context‑aware approach automatically protects against recursion. |
| **P3** | Rounding in `runtime_short` | `pipeline/package.py` line 36 | Use `int(est)` (floor) or guard against `est >= RUNTIME_S[0] - 0.5`. |
| **P3** | Dangling comment in `package_pin.py` | `pipeline/package_pin.py` lines 143‑146 | Move the comment inside the `SOFT_GATES` block or delete the stray line. |
| **P3** | Minor style: unused imports, long lines | Various | Clean up imports and line length. |

**6. Single highest‑leverage change**

Replace the global `_FLOOR` with a context‑aware mechanism (e.g., a `contextvars.ContextVar` or explicit parameter passing) so that the never‑empty pass’s floor cannot leak or be corrupted by concurrent or recursive `build()` invocations.

**7. Production ready?**

**Yes, with conditions.**  
The current deployment runs `build()` sequentially in a single process, so the race‑condition is unlikely to manifest. However, the code is fragile: any future change that introduces concurrency or recursion will break the runtime gate logic. The recommended refactor (context‑aware floor) should be applied before shipping to a production environment that may evolve.