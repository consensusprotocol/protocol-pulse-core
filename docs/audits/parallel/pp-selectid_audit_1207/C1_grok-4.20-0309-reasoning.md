# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 64 s finish=stop usage in 24511 / out 693 usd~0.140 (upper-bound price)

**P0: pipeline/package.py:260 (reorder fn)**  
`itertools.permutations` is called but the diff adds no `import itertools` (nor `from itertools import permutations`). Concrete scenario: 4 clips after hook produces permutations call on first execution of ruling-63 path → NameError before any lineup_ok or judged check. (Test suite passes per summary, but that does not prove the runtime module imports it; uncertain from diff alone.)

**P1: pipeline/package.py:328 (follow-up angle_write call)**  
Call is `router.call("angle_write", ..., 3000, 9, deadline_s=...)` with no `avoid_vendor=writer_vendor, avoid_family=writer_family` (contrast with medley/coherence calls at lines 374 and 425 that do pass them, and with original coherence/medley prompts). Concrete scenario: first angle call uses "heimdall:deepseek"; follow-up for a missing hook re-uses it, violating the "never the vendor/family of the writer" rule that every other verdict path enforces. Main angle call in the same diff block also omits the kwargs, so the removal may be intentional but is not verifiable from diff.

**P1: pipeline/package.py:182 (coherence) / 235 (medley) + 121 (can_open)**  
New `own is not None` guard + `hook_own` (which returns None on missing/invalid cached rating) makes every hook path fail-closed. All shown call sites (build:425, tests) are updated to supply a hook or test the None case, but the coherence signature change to `hook=None` means any unshown caller outside this diff would now silently get own=None and fail where it previously derived a rating. Cannot verify absence of other callers from diff alone.

**P2: pipeline/package.py:399 (last_clip_only), 270 (reorder), 391 (bad_pairs accumulation)**  
Matches K2/K3 exactly on the concrete conditions given in the rulings (through-line stated, only last rating < min, join-into-last discounted; permutations of post-hook clips only, hook fixed first, ids tuple in judged, lineup_ok called on candidate, bad_pairs built from every verdict in build). Floor/placement/termination guard (`spins > 4 * lineups`) also present. No deviation verifiable from diff.

**P2: tests/package/test_medley.py:465, 559, 717 (new TestRulings6264Search + updated TestClipsAloneVerdict / TestCoherenceHookRatedOnce)**  
Covers all listed check points (contracts reject hook key, no re-rating, last-clip-only floor vs. swap, reorder best-by-fewest-bad-then-fewest-moved, follow-up prompt contains only missing hooks, budget counts judged not spins, hook without cached rating fails closed). 119 tests OK per summary; no counter-example to rulings verifiable.

No other unintentional caller changes or contract violations visible in the diff. The 61–64 logic, memoization, allot(), _line_ok(), and fail-closed paths match the orchestrator rulings and governing laws (L-m, M12, LAW 20) on every line examined.

**SHIP: yes with conditions** (add itertools import or qualify the call; restore avoid_vendor/family on follow-up angle_write if the original call had it).