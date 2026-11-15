# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 31 s finish=stop usage in 21471 / out 1198 usd_reported=0.036549 usd~0.137 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261115_1129 (hook112.py + test_hook112.py)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   GLM correctly flagged the original medley_trace elif ordering (ratings before failures) and the undocumented semantics of which prescreen dicts store only failures vs. all outcomes; I had only noted the 3-channel fallback path. Both GLM and Qwen highlighted the brittle string-matching for spotlight "step A" stops and the dead-first-alternative regex in reason_class; I missed both. Qwen's deep compliance check on the Heimdall-only chain construction and the calls-table read-only path in hook_pass surfaced subtleties I had treated as "obviously safe." The Cycle-1 consensus synthesis of the two P1s (now fixed) revealed an interaction between the inconsistent-record test and the best-per-moment roll-up that I had not exercised.

2. WHERE DO YOU AGREE OR DISAGREE?
   - GLM P1 (ordering) → fully agree; the fix (failures before ratings, new test at lines 578-581) eliminates the wrong-funnel risk.
   - GLM P2 (spotlight step-A prose match) → partially agree: still brittle (lines 177-178) but now explicitly justified by spotlight.build's stop() contract; the cited producer line makes it maintainable.
   - GLM regex redundancy (STAND_ALONE with…|STAND_ALONE) → agree it is dead code but harmless (same class); still present.
   - Qwen read-only / Heimdall-only analysis → agree on all points; the mode=ro URI, cache=None behavior, and heimdall_hook_chain filter are now rigorously tested.
   - Consensus "may open" clarification and mutation kills → agree; the STAGES comment and new inconsistent-record test close the loop.
   - Minor disagreement on heuristic fallback in hook_pass: the calls table path is definitive; the cost/seconds fallback is now correctly gated behind "has_calls" and tested.

3. NEW FINDINGS FROM THIS REVIEW
   [P2] reason_class still contains a dead left-alternative (hook112.py:75); re.search will always take the second branch for any STAND_ALONE string.  
   [P2] spotlight_trace stepa detection (lines 177-178) and reason_class step-A regex (lines 89-91) duplicate the exact strings produced by spotlight.build; a constant or structured flag would be safer.  
   [P3] resolve() depth limit of 4 (ledger_of:225) is arbitrary magic; a visited set would be clearer though functionally equivalent on current data.  
   [P3] report() and main() are long (70+ and 45+ LOC); the markdown generation mixes presentation with logic.  
   [P2] all_ratings folds spotlight hook_own entries with rater=None when no cache hit (lines 271-276); near_misses treats these as first-class but the test suite never asserts their rating parts match production own_rating logic.  
   [P3] SEEDS, LIMIT_USD, STOP_USD, and STAGES are module globals used both by production path and tests; a small dataclass would improve clarity.

4. REVISED SCORES
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | Funnel / trace logic   | P1:2    | P2:2    | Ordering and inconsistent-record bugs fixed; only documentation/brittle-match issues remain |
   | Read-only & isolation  | P1:1    | P3:1    | All mutation tests pass; calls table and mode=ro now verified |
   | Calibration / router   | P2:2    | P3:2    | Heimdall filter, stop guard, no-cache, and ref-id isolation all tested |
   | Ledger / roll-up       | P2:1    | P2:1    | Tie-breaking and variant folding solid; new resolve depth nit |
   | Overall                | P1:3    | P2:3    | Fixes addressed every P1; residual issues are maintainability |

5. FINAL PRIORITY LIST
   [P2] hook112.py:75 — remove dead "STAND_ALONE with the clip scorer|" alternative (or make it a comment).  
   [P2] hook112.py:177-178 & 89-91 — replace string matching for step A with a structured sentinel if spotlight.build ever adds one; otherwise add a prominent comment citing the exact producer lines.  
   [P2] hook112.py:271 — add test coverage for spotlight hook_own entries that have no cache hit (rater=None path).  
   [P3] hook112.py:225, 73-86, 436-467 — replace magic depth, extract reason_class patterns to a constant dict, and split report() into smaller pure functions.  
   [P3] test_hook112.py:755 — the FakeRouter rate spy should also assert wf (writers family) avoidance.

   P1_OR_WORSE: 0

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The single highest-leverage change is the unified 7-stage scale (STAGES + medley_trace/spotlight_trace) that forces every decision point in package.build and spotlight.build to map to one documented funnel bucket.

7. PRODUCTION READY?
   Yes with conditions: (a) remove or comment the dead regex alternative, (b) add the cited producer-line comment for step-A detection, (c) expand the near-misses test to cover a spotlight-only rating with no cache entry. Once those three edits land the driver is ready to ship.