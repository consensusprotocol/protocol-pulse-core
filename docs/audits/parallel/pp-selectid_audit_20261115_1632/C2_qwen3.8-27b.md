# qwen3.8-27b (qwen/qwen3.8-27b) 55 s finish=stop usage in 20324 / out 2649 usd_reported=0.002834 usd~0.101 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1632
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok's P1 (M1 violation):** I missed this in Cycle 1. Grok correctly identified that `search_lineups` + `join_table` constitute a new combinatorial selector, which the governing laws (M1: "no new selector") explicitly prohibit. However, the Cycle 1 consensus refuted this: the search is the orchestrator's own order (ruling 117(2): "choose the order BY SEARCH over the table"), it lives inside the existing lineup stage, adds no pipeline stage/module/render path, and the verdicts still decide every lineup. **I now agree with the consensus: this is NOT a defect.** The ruling explicitly orders this search; M1 prohibits *unauthorized* new selectors, not orchestrator-ordered ones.

**Grok's P2 (missing import):** I missed this. Grok claimed `itertools.permutations` is used without an import. The consensus refuted this: `pipeline/package.py:54` has `import itertools` at module top (used by `reorder()` since ruling 63). **I agree with the consensus: REFUTED.** The import exists.

**Grok's P2 (300-400 model calls):** I missed this. Grok claimed worst-case 300-400 calls per package. The consensus refuted this with arithmetic: 8 moments = 49 ordered pairs (hook never second), 25 pairs/call = 2 calls/angle, MAX_ANGLES=3 = at most 6 calls/build, all cached. **I agree with the consensus: REFUTED.** The spend is bounded and cached.

**Qwen's analysis:** Qwen provided a thorough but incomplete analysis (cut off mid-sentence). It correctly identified the fail-closed behavior, the cache key robustness, and the search constraints. It did not flag the M1 concern or the import issue. **No unique findings I missed.**

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Position | Reasoning |
|---------|--------|-------------|-----------|
| M1 violation (new selector) | Grok P1 | **DISAGREE** | Ruling 117(2) explicitly orders "choose the order BY SEARCH over the table." The search is inside the existing lineup stage, adds no new pipeline stage/module/render path, and verdicts still decide. This is an orchestrator-ordered change, not an unauthorized new selector. |
| Missing `itertools` import | Grok P2 | **DISAGREE** | `import itertools` exists at `pipeline/package.py:54` (module top). Used by `reorder()` since ruling 63. |
| 300-400 model calls | Grok P2 | **DISAGREE** | Arithmetic: 8 moments = 49 pairs, 25/call = 2 calls/angle, 3 angles = 6 calls/build max. All cached by `text_sha(a):text_sha(b):JOINS_VERSION`. |
| Cache key omits speaker/channel | Grok P3 | **AGREE (P3)** | The key uses only the two texts' SHA and `JOINS_VERSION`. If a channel is renamed but the text is unchanged, a stale cache hit could occur. However, this matches the existing pattern for `step_a_cache` and `hook_cache`, and the ruling specifies "cached by the two texts." |
| Docstrings duplicate ruling text | Grok P3 | **AGREE (P3)** | The embedded ruling text and docstrings are verbose. This is a style issue, not a functional defect. |
| Coherence-only failure not pruned | Grok P3 | **AGREE (P3)** | `a_ratings` and `dropped` are updated only on measured clips-alone failures. A coherence-only failure that returns clip ratings is ignored for search pruning. The ruling does not specify this corner case. |
| Fail-closed behavior | Qwen | **AGREE** | Out-of-contract replies raise `ValueError`, caught, and leave pairs unanswered (counted as flagged). Provider errors are caught. Empty tables fall back to `lineup_for`. |
| Search constraints | Qwen | **AGREE** | `lineup_ok` is applied, `LY_MAX_BRIDGES` is enforced, unanswered pairs count as flagged, ratings-aware ordering is correct. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] The `ext` angle construction may include moments not in `by_id`.**
In `build()` (line 212), `ext = dict(angle, moments=jids)` where `jids` includes the hook, the writer's other moments, and the rest of the cleared pool. However, `search_lineups` (line 156) does `others = [by_id[m] for m in angle["moments"] if m != angle["hook"] and m in by_id and m not in dropped]`. If a moment in `jids` is not in `by_id` (e.g., it was cleared but not in the angle's original moments), it is silently skipped. This is correct behavior, but the docstring for `search_lineups` does not explicitly state that moments not in `by_id` are ignored. **Recommendation:** Add a comment in `search_lineups` clarifying that `by_id` membership is required.

**[P3] The `join_table` function's `off` lambda is complex and hard to verify.**
Line 86: `off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))`. This checks that a backend is not the writer's vendor or family. The logic is correct but the nested lambda is obscure. **Recommendation:** Extract to a named function for clarity.

**[P3] The `search_lineups` function's `flagged` lambda does not handle the case where `table.get((a, b))` returns a dict without a `"followable"` key.**
Line 158: `flagged = lambda a, b: (a, b) in bad_pairs or (table.get((a, b)) or {}).get("followable") is not True`. If `table.get((a, b))` returns a dict that does not have a `"followable"` key, `.get("followable")` returns `None`, which is `not True`, so the join is flagged. This is correct fail-closed behavior, but it is not explicitly documented. **Recommendation:** Add a comment: "A join is flagged if the table has no answer, the answer is not `followable: true`, or a verdict flagged it."

**[P2] The `build()` function's `a_ratings` update logic may not handle all verdict formats.**
Lines 267-272: `for lb_, mm in zip(labs[1:], segs[1:]): x = (med.get("clips") or {}).get(lb_); if type(x) is int: a_ratings[mm["moment_id"]] = max(x, a_ratings.get(mm["moment_id"], 0))`. This assumes `med["clips"]` is a dict mapping labels to integer ratings. If the verdict format changes (e.g., ratings are floats or nested), this will silently skip the update. **Recommendation:** Add a type check or a more robust extraction.

**[P3] The test `test_the_tables_moments_are_the_hook_its_writers_picks_then_the_cleared_pool` does not verify the rank score ordering.**
Lines 530-540: The test verifies that the table's moments are the hook, the writer's picks, then the pool, capped at 8. However, it does not verify that the pool is ordered by rank score (descending). **Recommendation:** Add a test case with multiple pool moments with different rank scores and verify the ordering.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Join table construction | 8/10 | 9/10 | The M1 concern is refuted; the implementation is correct and fail-closed. Minor clarity issues remain. |
| Search logic | 8/10 | 9/10 | The search correctly applies `lineup_ok`, enforces `LY_MAX_BRIDGES`, and handles unanswered pairs. The `ext` angle construction is correct but could be more explicit. |
| Build integration | 7/10 | 8/10 | The fallback logic is correct, but the `a_ratings` update logic is fragile. The `ext` angle construction is correct but not fully documented. |
| Caching | 8/10 | 8/10 | The cache key is robust for the specified use case (two texts + version). The omission of speaker/channel is a known limitation matching existing patterns. |
| Tests | 9/10 | 9/10 | The tests are thorough (12 cases, 14/14 mutations killed). Minor gaps in rank score ordering and verdict format robustness. |
| Compliance with ruling | 8/10 | 9/10 | The implementation matches the ruling's order. The M1 concern is refuted. The search is orchestrator-ordered, not unauthorized. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **`pipeline/package.py:156`** — `search_lineups` silently skips moments not in `by_id`. Add a comment clarifying that `by_id` membership is required.
2. **`pipeline/package.py:267-272`** — The `a_ratings` update logic assumes `med["clips"]` is a dict of integer ratings. Add a type check or more robust extraction to handle format changes.
3. **`pipeline/package.py:86`** — The `off` lambda in `join_table` is complex. Extract to a named function for clarity.

**P3 NIT:**
1. **`pipeline/package.py:158`** — The `flagged` lambda's fail-closed behavior for missing `"followable"` keys is not documented. Add a comment.
2. **`tests/package/test_medley.py:530-540`** — The test for table moments does not verify rank score ordering. Add a test case.
3. **`pipeline/package.py:47-65`** — The docstrings and embedded ruling text are verbose. Consider trimming for "smallest diff."

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add a type check or more robust extraction in the `a_ratings` update logic (`pipeline/package.py:267-272`) to handle verdict format changes, ensuring that clip ratings are correctly propagated to the search even if the verdict format evolves.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. Add a comment in `search_lineups` clarifying that moments not in `by_id` are silently skipped (P2).
2. Add a type check or more robust extraction in the `a_ratings` update logic to handle verdict format changes (P2).
3. Extract the `off` lambda in `join_table` to a named function for clarity (P2).
4. Add a test case verifying rank score ordering in the table moments (P3).

These are minor clarity and robustness improvements. The core logic is correct, fail-closed, and compliant with the ruling. The M1 concern is refuted: the search is orchestrator-ordered, not an unauthorized new selector. The missing import and excessive model call concerns are refuted by the code and arithmetic.

P1_OR_WORSE: 0