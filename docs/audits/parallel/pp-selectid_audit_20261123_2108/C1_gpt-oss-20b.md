# gpt-oss-20b (openai/gpt-oss-20b) 30 s finish=stop usage in 8700 / out 4796 usd_reported=0.000605 usd~0.098 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | **P1** | `content_flags` can count more than the allowed 3 kinds of review flag | `content_flags` now counts distinct *kinds* (via `flag_kind`) for every flagged row. If a package contains more than three distinct kinds (e.g., many different soft codes or edge codes), the cap check in `review_problems` will still allow the package to pass because the cap is only enforced on the number of kinds, not on the number of distinct soft codes. This violates the “at most 3 KINDS per package” rule. |
| 2 | **P2** | `flag_kind` may collapse distinct flags that share the same gate string but have different sentences | For non‑PER_CLIP_KIND gates, `flag_kind` returns `f"{gate}: {sentence}"`. If two different flags share the same gate string but have identical sentences, they will be counted as a single kind. While this is unlikely, it could hide a distinct flag if the sentence is accidentally identical. |
| 3 | **P3** | `kind_sentences` may raise a `KeyError` if an unexpected code is encountered | `kind_sentences` uses `STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]`. If a new soft or edge code is introduced that is not present in either mapping, the function will raise a `KeyError`. This is a defensive‑coding issue that could surface in future extensions. |
| 4 | **P3** | `seg_marks` counts the hook flag via `hook_own(segs[0])` without checking that the first segment actually represents the hook | If the first segment in a line‑up is not the hook (e.g., a mis‑ordered list), `seg_marks` will incorrectly count a hook flag. The current logic assumes the first segment is always the hook, which may not hold in all pipeline paths. |

**P1_OR_WORSE**: **1** (only the cap‑violation issue is a P1; the others are P2/P3).