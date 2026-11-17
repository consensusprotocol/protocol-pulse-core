# gpt-oss-20b (openai/gpt-oss-20b) 56 s finish=stop usage in 10474 / out 8919 usd_reported=0.001430 usd~0.165 (upper-bound price)

**1. What did the other models catch that I missed?**  
- **Gemma & GPT‑OSS** flagged “hook flag never set” and “inventory flag logic wrong.” Both are false – the flag is set in `_build` before `hook_own` is called again in `can_open`, and inventory pulls the flag from the medley’s `hook_own`.  
- **Qwen** identified two non‑critical issues:  
  1. `hook_bar_under()` is called up to four times per flagged hook (once in the list‑comprehension, once in `hook_own`, once in the prescreen dict, once in the log).  
  2. The plain‑sentence flag depends on `CLIP_PLACE['hook']`, coupling the wording to a constant.  
  These are performance/coupling smells, not correctness bugs.  
- Qwen also noted an implicit ordering assertion and a stage‑label change; both are harmless.

**2. Where do I agree / disagree?**  
| Finding | Agreement | Reason |
|---------|-----------|--------|
| Hook flag never set (Gemma/GPT‑OSS) | ❌ | Flag is set in `_build` before `hook_own` is re‑invoked in `can_open`. |
| Inventory flag logic wrong (Gemma/GPT‑OSS) | ❌ | Inventory correctly reads `medley[1].get("hook_own")["flagged"]`. |
| `hook_bar_under()` called multiple times (Qwen) | ✅ (P3) | Redundant but harmless; could be memoised. |
| Flag sentence coupling to `CLIP_PLACE['hook']` (Qwen) | ✅ (P3) | Coupling is intentional; could be extracted to a constant. |
| Implicit ordering assertion (Qwen) | ✅ (P3) | Test could be more explicit but passes as‑is. |
| Stage‑label change (Qwen) | ✅ (P3) | No downstream impact; migration note not required. |

**3. New findings from this review**  
- **Redundant `hook_bar_under()` calls**: four per flagged hook.  
- **Coupling of flag sentence to `CLIP_PLACE['hook']`**: if the wording changes, the sentence changes automatically, which is fine but worth documenting.  
- **Potential for a small performance hit** if `HOOK_SOFT_MAX` is increased or `_live_bar()` becomes expensive.  

No functional defects were uncovered.

**4. Revised scores**  

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Hook flag logic | 0 | 0 | No bug; flag is set correctly. |
| Inventory flag logic | 0 | 0 | Correctly reads flag from medley. |
| Performance / coupling | 0 | 0 | Minor P3 issues noted. |

**P1_OR_WORSE: 0**

**5. Final priority list**  

| Severity | Item | File:Line | Why |
|----------|------|-----------|-----|
| **P3** | Memoise `hook_bar_under()` results to avoid 4 calls per flagged hook | `pipeline/package.py` lines 20‑33 & 66‑73 | Small perf improvement, no correctness impact. |
| **P3** | Extract flag‑sentence prefix into a dedicated constant (e.g., `HOOK_FLAG_PREFIX`) | `pipeline/package.py` line 100‑102 | Makes coupling explicit; easier to change wording. |
| **P3** | Make the ordering assertion in `test_at_most_the_best_two_under_the_bar_open` explicit (assert `["h", "x"]`) | `tests/package/test_ruling_137.py` line 222 | Improves test clarity, no functional change. |

**6. The single highest‑leverage change**  
Memoise the result of `hook_bar_under()` per moment so that the function is evaluated only once per flagged hook, eliminating the four redundant calls and making the code cleaner and slightly faster.

**7. Production ready?**  
Yes. All functional requirements are satisfied, tests pass, and the only remaining issues are minor performance/coupling concerns that do not affect correctness.