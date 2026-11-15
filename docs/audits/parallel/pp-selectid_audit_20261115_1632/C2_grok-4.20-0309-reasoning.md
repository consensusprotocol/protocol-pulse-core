# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 18413 / out 1384 usd_reported=0.032059 usd~0.127 (upper-bound price)

**CYCLE 2 CODE AUDIT: pp-selectid-20261115_1632 (RULING 117 join-table + search)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In my Cycle 1 I focused on contract parsing, fallback paths, and test coverage but completely missed (a) the post-Cycle-1 expansion of the join pool to the full CLEARED set (hook + writer's moments + ranked rest of step-A/CUTTABLE pool, capped at 8), (b) that `a_ratings` / `dropped` pruning now runs on *any* measured failure that supplies clip ratings (not just clips-alone), and (c) the exact cache-lookup predicate that sorts back-ends and requires both `off(name)` *and* presence on today's "joins" list. Grok caught the combinatorial-selector concern and the spend-budget gap; Claude correctly refuted the selector violation and the import bug. I also under-weighted how strictly the new test suite locks the "hook never B", "unanswered = flagged", and "writer-order tie-breaker" rules.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Grok P1 ("new selector violates M1 / Smallest diff"): Disagree. The search lives inside the existing `build()` lineup stage beside `lineup_for`, `reorder`, and `swap_lineup`; no new pipeline stage, no model call inside search, verdicts still decide. Matches ruling 117 verbatim.  
- Grok P2 (missing itertools import): Disagree — `import itertools` is present at module level (used by `reorder` since ruling 63).  
- Grok P2 (300-400 calls): Disagree — arithmetic shows ≤49 pairs × 2 calls/angle × MAX_ANGLES=3 = ≤6 calls/build, all routed through the existing spend ledger and cached forever by text+JOINS_VERSION.  
- Grok P3 (cache key omits metadata): Partially agree — key is minimal (text_sha + version) but *consistent* with hook_cache and step_a_cache; a renamed speaker would invalidate correctly via text change.  
- Grok P3 (duplicate ruling text): Agree — docstrings repeat orchestrator comments; inflates diff.  
- Qwen's analysis: Agree on strict parse, fail-closed behavior, flagged-join lambda, rating sort keys, and fallback logic. Qwen missed the pool-expansion side effect on call volume.  
- Claude consensus: Fully agree on all three refuted points and on the post-Cycle-1 CLEARED-pool change.

**3. NEW FINDINGS FROM THIS REVIEW**  
[P2] pipeline/package.py:230-235 (and 273-278): `search_lineups` is called *twice* on every iteration (once with `repeat_ok=False`, once with `True`) when the first returns nothing. This doubles search CPU for every angle that hits the supply-exception path; the second call can return lineups that `lineup_ok(..., repeat_ok=False)` would have rejected. The ruling never contemplated the double invocation.  
[P2] pipeline/package.py:209-211: `rest_` sort key `(-cleared[x].get("rank_score", 0), x)` assumes every cleared moment has a rank_score; if a second-pass moment lacks it, stable ordering is not guaranteed across runs, violating "writer's play order kept" tie-breaker in spirit.  
[P3] pipeline/package.py:156: `others = others[:JOIN_MOMENTS_MAX - 1]` after listcomp from `angle["moments"]`; when `ext` expands to 8 moments this silently drops the lowest-ranked ones *before* search, but `join_table` already used the full 8. Minor inconsistency in comment vs. code.  
[P3] tests/package/test_medley.py:530-540: New test `test_the_tables_moments_are_the_hook_its_writers_picks_then_the_cleared_pool` hard-codes expected join_calls but does not assert that dropped/doomed moments are excluded from the table (only from search). Coverage gap.  
[P3] pipeline/package.py:101: Cache lookup does `sorted((cdb.get(...) or {}).items())` on every pair; with many cache entries this is quadratic and unnecessary — existing `_load_cache` already materializes the dict.

**4. REVISED SCORES**  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| Ruling compliance  | P2      | P3      | Pool expansion and agreement recording now exactly match updated ruling text; double-search call is the only remaining deviation. |
| Cache / contract   | P3      | P2      | Missed that listed=set() on ProviderError makes *all* pairs unanswered (flagged); strict parse is perfect but error path now clearer. |
| Search / ordering  | P2      | P2      | Double `search_lineups` call and rank_score assumption were invisible in Cycle 1 diff. |
| Test coverage      | P3      | P3      | 13 tests now; still misses doomed-moment exclusion and repeat_ok interaction. |
| Performance / spend| P3      | P3      | Bounded at 6 calls; no new spend callback needed. |

**5. FINAL PRIORITY LIST**  
P0 CRITICAL: none.  
P1 HIGH: none.  
P2 MEDIUM:  
- pipeline/package.py:230 (`if jt: found = search_lineups(...) or search_lineups(...)`) — remove the unconditional second call or guard with a comment that repeat_ok path is intentional.  
- pipeline/package.py:209 (`rest_ = sorted(...)`) — add explicit fallback key or guarantee rank_score in cleared dict.  
- pipeline/package.py:101 and 93 — replace per-pair sorted cache lookup with a single pre-filtered dict built once per angle (reduces quadratic work).  

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Make the double-search call conditional on whether the first invocation exhausted all non-repeating candidates; that single guard eliminates the only remaining deviation from "search exactly once per verdict" while preserving supply-exception behavior.

**7. PRODUCTION READY?**  
Yes with conditions: (1) eliminate or document the unconditional double `search_lineups` call, (2) guarantee rank_score on every cleared moment or add a stable secondary key, (3) hoist the cache pre-filter outside the pair loop. After those three targeted edits the change is mergeable, fully compliant, and an unambiguous improvement on join quality without touching any guarded law.

P1_OR_WORSE: 0