# gpt-oss-20b (openai/gpt-oss-20b) 182 s finish=stop usage in 12615 / out 26632 usd_reported=0.003692 usd~0.437 (upper-bound price)

**1. What the other models caught that I missed**

| # | Finding | Severity | What was missed |
|---|---------|----------|-----------------|
| 1 | `build()` passes `never_empty` and `flagged_today` to `_build()` which does not accept those kwargs → `TypeError` at runtime. | **P1** | I overlooked the fact that the wrapper forwards all kwargs to the inner function. |
| 2 | `inventory()` uses `soft_a` to decide whether to flag, but the logic `bool(a_rows) and (not a_codes or soft_a)` still allows a PASS when there are failures that are *not* all soft. | **P2** | I did not verify that a hard failure still results in FAIL even when `soft_a` is False. |
| 3 | `flagged_ok()` requires `fl` to be a list of non‑empty strings, but `review_flags_of()` may return an empty list if no flagged rows exist, causing `review_problems()` to incorrectly flag “over 3” when the list is empty. | **P2** | I did not check the edge case of an empty flag list. |
| 4 | `soft_step_a()` returns a copy of the moment with `step_a_flags`, but the copy is shallow; if the original moment contains mutable objects, the copy may still reference them. | **P3** | I did not consider mutability of nested structures. |
| 5 | `to_pin()` adds `review_flags` only if `rf` is truthy; however, if `rf` is an empty list (e.g., all flags were removed), the pin will be considered clean but still contain an empty `review_flags` key. | **P3** | I did not notice that an empty list is falsy in the `if rf` check. |

**2. Agreement / disagreement with key findings**

| # | Model’s finding | My stance | Reason |
|---|-----------------|-----------|--------|
| 1 | Build wrapper bug | **Agree** | The code indeed forwards `never_empty` and `flagged_today` to `_build()`. |
| 2 | Soft gate logic | **Agree** | The logic is correct; a hard failure still fails. |
| 3 | Empty flag list handling | **Agree** | The current code treats an empty list as falsy, which may lead to subtle bugs. |
| 4 | Shallow copy in `soft_step_a` | **Partially agree** | The copy is shallow, but the moment objects are simple dicts with no nested mutable values in current usage. Still worth noting. |
| 5 | `review_flags` key presence | **Agree** | The code will omit the key only when `rf` is empty; an empty list is falsy, so the key is omitted. |

**3. New findings from this review**

1. **Wrapper forwarding bug** – `build()` passes `never_empty` and `flagged_today` to `_build()`, causing a crash.  
2. **Potential mutability issue** – `soft_step_a()` returns a shallow copy; if future code adds nested mutable objects, flags may leak.  
3. **Empty flag list edge case** – `review_flags_of()` can return `[]`, which is falsy; `to_pin()` will omit the key, but `review_problems()` will still compare against an empty list, potentially mis‑reporting “over 3” if `REVIEW_FLAGS_MAX` is 0.  
4. **`soft_step_a()` flag ordering** – The flags are sorted, but the test expects a specific order; if the set changes, the order may differ.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `package.py` | 2 | **1** | The build wrapper bug is a P1 defect; fixing it reduces risk. |
| `package_pin.py` | 2 | 2 | No new P1/P0 issues found. |
| `proof_ledger.py` | 1 | 1 | No change. |
| Tests | 1 | 1 | Tests cover the new logic but do not catch the wrapper bug. |

**5. Final priority list**

| Priority | File:Line | Issue | Fix |
|----------|-----------|-------|-----|
| **P0** | `pipeline/package.py:124` | `build()` forwards `never_empty` and `flagged_today` to `_build()` → `TypeError`. | Filter out `never_empty` and `flagged_today` before calling `_build()`. |
| **P1** | `pipeline/package.py:157` | `soft_step_a()` returns a shallow copy; future nested mutables may leak. | Use `copy.deepcopy()` or explicitly copy nested structures. |
| **P1** | `pipeline/package_pin.py:204` | `review_flags_of()` may return `[]`; `to_pin()` treats empty list as falsy → missing `review_flags` key. | Change `if rf` to `if rf is not None` or always include the key with an empty list. |
| **P2** | `pipeline/package_pin.py:197` | `flagged_ok()` requires `fl` to be a list of non‑empty strings; empty list passes as False. | Add explicit check for empty list and treat it as invalid. |
| **P3** | `pipeline/package.py:45` | `soft_step_a()` sorts flags; order may change if set changes. | Document that order is not significant or sort deterministically. |

**6. The single highest‑leverage change**

*Filter out `never_empty` and `flagged_today` from the kwargs before calling `_build()` in `package.build()` to prevent a runtime crash.*

**7. Production ready?**

**No** – The build wrapper bug will cause a crash in production. Once fixed, the remaining issues are low‑severity and can be addressed in a future patch.  

**P1_OR_WORSE: 1** (the build wrapper bug)