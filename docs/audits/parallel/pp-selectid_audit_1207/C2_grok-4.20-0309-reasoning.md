# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 31 s finish=stop usage in 25620 / out 1672 usd~0.170 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1207 (Rulings 61–64 + budget)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   I completely missed Qwen’s P0 surface on `can_open` + `hrank`/`hooks_txt` (lines 119–122, 296, 346 in the new diff): the path that lets an unrated moment reach the dict comprehension before `hook_own(m)` is guarded. I also did not notice GLM/Grok’s point on the new `hook=None` default in `coherence` (line 147) and its silent behaviour change for any positional caller. Grok’s itertools-permutations import flag was unnecessary (already present at module level) but I had not cross-checked the import block. The Claude consensus refutation using the exact build-site population of `"hook_rating"` (lines 1888–1890 area) was the key evidence I had not assembled.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - **Qwen P0 (hook_rating None/KeyError paths)**: Disagree. The diff shows `build()` populates `m["hook_rating"] = rated.get(mid) or {"rating": None, ...}` on *every* cleared moment *before* `passing`, `offered`, `hrank`, or `hooks_txt` are built (lines 1888–1895, 295–297). The `if "hook_rating" not in m: return True` branch in `can_open` is explicitly for non-build callers (tests, K5). No crash path exists in the executed build.  
   - **GLM P1-1 / Grok P1 (coherence hook=None default)**: Agree. The signature change (line 147) plus the single updated call site (lines 425–426) leaves any unshown caller (replay harness, other module) silently failing closed. The diff alone cannot prove absence of other callers; the suggested grep is still required.  
   - **GLM P1-2 (ruling 62 len(segs)-1 > LY_CLIPS[0] + repeat_ok)**: Partially agree. The clarified arithmetic (len(segs) includes hook → len(segs)-1 == clip count; dropping last leaves >= LY_CLIPS[0] clips) now matches the test at diff line 683 and `last_clip_only` + `lineup_ok`. The `repeat_ok=exception is not None` guard is unchanged from prior code and only relaxes STAND_ALONE, not the seconds floor (lineup_ok still checks dur bounds). However the name “exception” is opaque after the refactor.  
   - **Grok P0 (missing itertools import)**: Disagree — already imported at top of package.py (line 50, outside diff).  
   - **Grok P1 (avoid_vendor/family on follow-up angle_write, line 328)**: Agree on style but not on severity. The follow-up is still an angle writer call; the main call never passed those kwargs either. No verdict consumes the angle text, so vendor leakage is not a contract violation, but consistency would be cleaner.  
   - **All models on 63/64/budget mechanics, memoization, termination guard, test coverage**: Full agreement. The `judged` dict keyed by id tuple, `spins > 4 * lineups` guard, `allot()`, `reorder()` best-key logic, `last_clip_only` exact conditions, and rewritten tests match the orchestrator rulings and close all enumerated check points.

3. **NEW FINDINGS FROM THIS REVIEW**  
   **P1: pipeline/package.py:391 (`repeat_ok=exception is not None`)**  
   After the large refactor the identifier “exception” no longer appears in any enclosing scope visible in the diff (the old `if exception is not None` block was replaced by `last_clip_only` and the `if med.get("measured") and _line_ok...` reorder path). Concrete scenario: first angle, first line-up hits the ruling-62 `last_clip_only` true path → NameError on undefined name before `lineup_ok` runs or any swap occurs. The unit test (TestRulings6264Search) uses Rig which may mask it, but the production `build()` loop does not define “exception”. This is the only new verifiable error path the combined Cycle-1 analysis revealed.  
   **P2: pipeline/package.py:329 (`hooks_txt(missing)` in follow-up path)**: `hooks_txt` lambda calls `hook_own(m)["rating"]` unconditionally. The follow-up path can legally contain a hook that later fails `hook_own` (e.g. cache corruption after the first angle call). The error is caught and recorded but pollutes the angle_follow_up dict with a traceback instead of a clean “no rating” sentinel. Minor, but inconsistent with the “never the build” guarantee.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | Hook rating & fail-closed (61) | P1     | P0     | Consensus + diff lines 102–122, 179–181, 229–231 show every path now guarded; build always populates rating. |
   | Last-clip retry & floor (62)   | P2     | P1     | New NameError on “exception” variable surfaced only after seeing GLM’s conditional analysis. |
   | Reorder & bad-pairs (63)       | P2     | P2     | No change; termination guard, judged set, and test coverage are solid. |
   | Angle allotment & follow-up (64) | P2   | P2     | Minor P2 added on follow-up error handling; vendor avoidance still stylistic. |
   | Budget / memoization           | P2     | P1     | The `spins > 4 * lineups` guard + `judged` dict now verified to prevent infinite loops even with reorder permutations. |

5. **FINAL PRIORITY LIST**  
   **P1 CRITICAL**  
   - pipeline/package.py:391 — undefined “exception” name in `repeat_ok=...` (NameError on ruling-62 path).  
   **P2 MEDIUM**  
   - pipeline/package.py:329 — `hooks_txt(missing)` can still raise inside follow-up if a hook loses its rating after first angle call.  
   - pipeline/package.py:147 & 425 — coherence `hook=None` default; confirm no other callers (grep).  
   - pipeline/package.py:328 — restore `avoid_vendor=writer_vendor, avoid_family=writer_family` on follow-up angle_write for consistency (same as main call).  
   No P0s remain after the Cycle-1 fixes; all contracts now reject hook ratings, no hook opens without cached own-job >= 4, reorder terminates, budget cannot spin forever, tests cover every ruling clause.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Memoizing verdicts by exact `(moment_id)` tuple (`judged` dict at line 370) while letting ruling 63 generate cheap permutations makes the entire “joins before swaps” policy practical without exploding the judged-line-up budget.

7. **PRODUCTION READY?**  
   Yes with conditions: (a) rename or define the “exception” variable at line 391 (or replace with explicit `repeat_ok=True` if that is the intent), (b) add the vendor/family kwargs to the follow-up angle_write, (c) confirm via grep that no other module calls `coherence()` positionally. Once those three lines are adjusted the diff is ship-ready; the core logic for 61–64 and the budget is now correct, well-tested, and matches the orchestrator rulings.

**SHIP: yes with conditions** (fix undefined “exception”, restore avoid kwargs on follow-up, confirm no other coherence callers).