# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 16729 / out 1347 usd~0.117 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1420 (Ruling 66 standing part)**

1. WHAT DID THEY CATCH THAT YOU MISSED?  
Qwen's P0-1 (naive/aware `_at()` vs `now` comparison crash) and GLM's P1-1 (sort-key `None`/`found_at` formatting) were missed in my Cycle 1; both could have produced non-deterministic due() ordering or mid-build exceptions before the C1 consensus fix. I also overlooked Qwen's P0-2 infrastructure-error-as-"clip" (try_one OSError path) and the subtle dependency of the "line" class on `t_.get("attempts")` being truthy only after a write (refuted but still delicate).

2. WHERE DO YOU AGREE OR DISAGREE?  
- Fully agree with Qwen P0-1 / GLM P1-8 / Grok P2 on time handling: the C1 `_at()` standardization + driver refusal block is the correct minimal fix; test_a_stored_time_without_a_zone_is_utc_and_a_malformed_one_raises now proves it.  
- Disagree with Qwen P0-2 ("clip" on OSError): records live under proof/ledger_* and are part of the reproducible test surface; treating absence/corruption as permanent clip matches K2 ("fails a gate" or "cannot be rebuilt").  
- Partially agree with GLM P1-1 / Qwen P1-3 on sort key: `str(... or "")` with reverse=True does put unknown-last (conservative), but a sentinel datetime or explicit `_at()`-based key would be clearer.  
- Agree with all consensus refutations (R1–R5): attempts list is always populated on write, registry=True is written after both branches, budget accounting is protected by the test_medley cached-verdict case, etc.  
- Grok's P2 on --from-candidate registry flag was correctly refuted.

3. NEW FINDINGS FROM THIS REVIEW  
P2-1 — pipeline/candidates.py:120 (`lineups -= int(judged or 0)`): when a candidate returns judged=0 (cached verdict or pre-judgement clip) the shared budget is not decremented, yet the driver still treats the 8-lineup quota as consumed for the angle build. Concrete scenario: 8 consecutive cached candidates each report judged=0; angle build still receives left=8 and can judge 8 more, exceeding the "inside the 8" guarantee of K4. (Unverifiable from diff alone whether total in package.build counts the free ones.)  
P2-2 — tests/package/proof_ledger.py:330 (atomic registry save): os.replace() after json dump is good, but there is a window between package.json write (line 328) and registry write where a crash leaves the registry unseeded for this build. The glob-seed on next run would re-apply it, but duplicate "records" entries are possible.  
P2-3 — pipeline/package.py:202 (`"line" if ... and t_.get("attempts") ...`): the guard prevents "line" on pure clip failures (good), yet "attempts" is an opaque list whose population site is outside this diff; a future medley change that clears attempts could silently turn line failures into permanent clips.

4. REVISED SCORES  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| State machine (outcome, due, resting) | P2:1 | P2:0 | Comprehensive new test_candidates.py + C1 time fix eliminated all concerns |
| Budget & judged-lineup accounting | P2:1 | P1:1 | New finding P2-1 above shows the free-verdict path can still let angle build exceed 8; previously thought fully covered by test_medley |
| Driver (read-before-write, seed, atomicity) | None | P2:2 | Missed the post-write seed race and glob cost; still not ship-blocking |
| Classification & fresh-write seed | P2:1 | P2:1 | "attempts" and write_seed=1000 logic now verified by test_the_outcome_class_and_the_fresh_writes but remains brittle |
| Overall                  | SHIP: yes | SHIP: yes with conditions | No P0s remain; new P1 is narrow |

5. FINAL PRIORITY LIST  
**P0 CRITICAL** — none.  
**P1 HIGH**  
- pipeline/candidates.py:120 + tests/package/proof_ledger.py:311 (run_due budget decrement): must guarantee total judged line-ups (candidates + angle build) never exceeds PK.LINEUPS_PER_BUILD=8 even when some are free/cached. Concrete scenario: 8 cached candidates → angle build still gets left=8. Add explicit assertion or change to lineups -= 1 for every candidate tried.  
**P2 MEDIUM**  
- pipeline/candidates.py:106 (due() sort key): replace str-or-"" with explicit datetime sentinel or _at() to eliminate any future ISO variance.  
- tests/package/proof_ledger.py:330 (registry write after package.json): document the crash-window behavior and add a recovery test that re-seeds on partial ledger.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE  
Enforce the shared 8-judged-lineup budget with an explicit counter that always charges 1 per candidate tried (even cached ones) and passes the true remainder to the angle build; everything else (state machine, seeding, atomic save) already works.

7. PRODUCTION READY?  
Yes with conditions: (a) fix the P1 budget accounting so the "inside the 8" rule of K4 is mechanically enforced rather than emergent, (b) add the recovery test for the package.json → registry write window, (c) run the full proof_ledger suite against the 38 existing records after the budget change to confirm no candidate is tried twice and real-data hook-closed candidates are still clipped cleanly. Once those three items land this is ship-ready.

**P0: none**  
**P1: pipeline/candidates.py:120 (budget accounting can exceed 8 judged line-ups on cached candidates)**  
**P2: pipeline/candidates.py:106 (sort key), tests/package/proof_ledger.py:330 (write ordering)**  
**SHIP: yes with conditions** (see #7 above)