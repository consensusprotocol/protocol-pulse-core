# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 51275 / out 1685 usd~0.298 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2030 (L-y Medley, post-C3 fixes)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
- GLM-5.3-FLASH's P0-1 (ly_shape vs assemble_medley bridge-after-hook bookkeeping, especially `bridges_after_clip=[0]` vs folded `intro` and the `type(a) is int and 0 < a < n_clips` guard) was missed in my Cycle 1; the fragility is real for any non-assemble_medley producer.  
- GROK's P0 on missing `runtime_s_estimate` in the old `_package` path and malformed RUNTIME redo text containing "None".  
- QWEN's P0-3 on `medley_content_range` not subtracting bridge pre-roll from the lower bound (and the lo>hi inversion case).  
- The consensus table (K6/K7) on takeaway-budget intersection and honest "judged" counting in proof_ly.py was only partially covered by my prior P2s.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P0-1 (downgraded to P1): **Partially agree**. The original slot/record/flagged-join paths were inconsistent across producers; the fixed `assemble_medley` + `ly_shape:577` + `bridge_slots` (package_pin:1016) now align on `intro` for k==0 and `bridge_1`/`takeaway` mapping. The `type(a) is int` guard remains silent-drop (still fragile for hand-crafted pkgs).  
- GROK P0 (runtime key) / P1 (redo "None"): **Disagree** — both fixed. `_package:204` now always writes the key; `NoBridgeFits` is raised pre-call (lines 503, 508) and redo text branches on budget existence (857-860). Test `test_no_intro_and_one_takeaway_after_the_last_clip` asserts the exact value.  
- GROK P2 (canon on text comparisons): **Agree** — L-k is for external transcripts; these are internal byte-exact checks (L-j). The diff correctly keeps `!=` / `.strip() !=`.  
- QWEN P0-2 (budget inversion / infinite redo): **Agree on the arithmetic risk but disagree on severity**. New `bridge_budget:121` (largest n where intervals overlap) + `takeaway_budget:137` (tries LY_AIM_S first, then RUNTIME_S, returns None only when impossible) + `NoBridgeFits` before any model call makes it fail-closed and efficient. No infinite loop.  
- QWEN P0-3 (medley_content_range bridge pre-roll): **Agree** — fixed by `extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)` in the new helper.  
- Consensus K6/K7: **Fully agree** — implemented cleanly; early CUTTABLE + doomed moments + honest `_takeaway_record:658` ("passed": None when cheap gates stop first) + updated table are correct per L-y 3/6 and M12.

**3. NEW FINDINGS FROM THIS REVIEW**  
P2: pipeline/package.py:577 (`ly_shape`) and package_pin.py:1032 (`bridge_slots`).  
A package built outside `assemble_medley` (e.g. integrator R11 path or test fixture) with `bridges_after_clip=[0, n_clips]` and `intro=None` produces `bridged=[js[0]]` (the 0 is dropped by the guard) while `texts` length matches the bridge list → `len(bridged) != len(texts)` failure with misleading message "a line after clips [0] that is not at a join". Concrete: `medley_pk(n=4, bridge="w", after=0, intro=None)` passes `ly_shape` only because the test uses the canonical path; a non-canonical but semantically valid package (bridge after hook recorded as after_clip=0) is rejected. (The diff warns about this in GLM's original note; the guard was not hardened.)

P2: pipeline/providers.py:1111 (`_settle` usd_reported path).  
Ledger update adds `usd_reported` only when present, but the spend guard (`limit_usd=LY_LIMIT_USD`) still reads the price-table `usd_estimate`. A vendor under-reporting (or a transient parse failure in `_num`) lets the estimate continue climbing past the cap while "best known" stays low. Concrete: 10 calls each reporting $0.01 but estimate $0.30 → guard passes on estimate but real spend exceeds cap. (Tested via `TestReportedCost`; the guard comment still says "the estimate".)

No other new violations of L-y 1-6, L-m (nothing measured never PASS), L-j (fail closed, exact inventory), L-x (vendor avoidance), or the ROUND-2 items 11-15 could be verified from the diff. The CUTTABLE early filter, `NoBridgeFits` before writes, `ly_shape` must-fail cases, prompt changes (sentence-case, explicit commentary bans), and honest takeaway table all match.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Budget arithmetic (bridge/takeaway) | P0     | P2     | `bridge_budget` + `NoBridgeFits` + dual AIM_S/RUNTIME_S path eliminates empty-intersection and redo-None cases (K6) |
| ly_shape / assemble_medley consistency | P1     | P2     | Fixed slot mapping, bridge record binding, and R11 mirroring; residual guard fragility is now edge-case only |
| Build loop / early filtering | P1     | P2     | CUTTABLE/doomed moments before angles, per-worker metering, gate_problems check before return — prevents wasted writes and dishonest counts (K7) |
| Ledger / spend guard   | P2     | P2     | New reported-cost path is correct but guard still estimate-only (new P2 above) |
| Test coverage (must-fail + Rig) | P2     | P2     | Comprehensive; covers every L-y rule and ROUND-2 item |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL**: None.  
**P1 HIGH**: None (all Cycle-1 P0s addressed).  
**P2 MEDIUM**:  
- pipeline/package.py:577 (`ly_shape` guard `type(a) is int and 0 < a < n_clips`): hand-crafted pk with after_clip=0 produces wrong bridged list → spurious failure (see concrete above).  
- pipeline/providers.py:1111-1117 (`_settle` + guard): estimate can exceed LY_LIMIT_USD while reported stays under (testable with mocked under-reported calls).  
- pipeline/package.py:595 (`ly_shape` confirmed_by check): accepts any truthy non-empty value; test only checks bool/empty/dict — minor contract looseness vs R11.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
`bridge_budget()` + `NoBridgeFits` raised before any model call (write_takeaway:502) guarantees the writer is never handed an infeasible range, eliminating the entire class of runtime/redo loops that plagued earlier versions.

**7. PRODUCTION READY?**  
Yes with conditions: (a) harden the `ly_shape` after_clip guard to raise on 0 or >=n_clips when intro is absent (or document that only assemble_medley packages are accepted); (b) make the spend guard read `usd_reported` when present (or document that the limit is on the conservative estimate); (c) add one integration test exercising a non-canonical package with after_clip=0 that still passes pin + rule_r11.

**Verdict: SHIP: yes with conditions**