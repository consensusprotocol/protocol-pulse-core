# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 8312 / out 1073 usd~0.068 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1006 (Ruling 57 Fresh-First Preference)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
I missed the all-unknown publish-times ranking inversion (Qwen P1 + GLM P1-2): when `known` was empty the old `max(default=0.0)+1.0` produced a mean of 1 h, making an all-None line-up appear *newer* than a 50–70 h line-up. That is directly visible in the original `fresh_key` arithmetic and is now fixed by the `UNKNOWN_AGE_H = 1.0e6` sentinel + explicit test at test_medley:120-121. I also under-weighted the hook-dilution effect on mean age (Qwen P2-3) and did not call out that `first_fresh` re-runs `lineup_for` with a slightly different signature than the later per-angle call (GLM P1-1), even though the consensus correctly notes dropped/doomed are still empty at that point.

2. WHERE DO YOU AGREE OR DISAGREE?
- Qwen/GLM on unknown-age handling: fully agree. The sentinel fix and new test eliminate the inversion; docstring now matches code.
- GLM P1-1 (first_fresh missing dropped/doomed): agree with consensus clarification — the call occurs before the main loop, so the sets are empty; the line-up computed is exactly the one the first iteration will see.
- GLM/Qwen on extra `lineup_for` cost per angle: partially agree. The calls are real (package.py:66, 1528 in diff) and `lineup_for` is O(n²) in moments, but with PRESCREEN_N=24 and at most 3 angles the added latency is milliseconds (verified by existing test suite timing). Remains P2.
- Qwen on hook inclusion in mean: agree — `fresh_key([h] + order, now)` matches K2 and the ruling; the test at line 118 exercises it.
- GLM P1-3 on `E.age_hours`: agree it was unverifiable in the original diff; the new test and `UNKNOWN_AGE_H` path now make None-safe behavior explicit.
- Grok’s “SHIP: yes” and lack of P1: I now concur after the sentinel fix; my Cycle 1 was too lenient on the unknown-age case.

3. NEW FINDINGS FROM THIS REVIEW
None that rise above P2. The stable sort `sorted(..., key=lambda a: not first_fresh(a))` (package.py:68) correctly places fresh angles first while preserving writer order within groups; `out["angles"]` records the tried order. `TIME_SENSITIVE_H` and the new `FRESH_H` both equal 24.0 but are distinct constants — a maintenance risk but not a behavioral change. No rule, gate, or `usable()` logic is altered; `now=None` paths are untouched.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| fresh_key / unknown-age| P1      | P2      | Sentinel + test at 120-121 fully resolves the inversion I missed in C1 |
| Angle re-order + first_fresh | P2 | P2 | Confirmed correct (dropped/doomed empty); extra calls acceptable |
| Test coverage          | P2      | P3      | New TestRuling57Fresh exercises fresh, newest, all-unknown, angle ordering, and now=None paths |
| Performance            | P2      | P2      | No material change; small N keeps cost negligible |

5. FINAL PRIORITY LIST
**P0 CRITICAL** — none  
**P1 HIGH** — none  
**P2 MEDIUM**  
- pipeline/package.py:8,10 — duplicate magic 24.0 (TIME_SENSITIVE_H vs FRESH_H); consider single source of truth if they must stay aligned.  
- pipeline/package.py:66 — extra `lineup_for` call per angle (up to 3×) solely for sorting; cost is acceptable but should be measured in production.  
- tests/package/test_medley.py:119 — hook-dilution scenario is exercised but not asserted; add explicit mean-age check for clarity.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The `fresh_key` tuple prepended to the existing key (package.py:55-57) plus the stable angle sort (line 68) applies the preference at both intra-angle selection and inter-angle ordering without touching any gate or rule.

7. PRODUCTION READY?
**Yes with conditions.**  
Conditions: (a) the two 24 h constants must remain synchronized or be unified; (b) production telemetry must confirm the extra `lineup_for` calls add < 50 ms end-to-end; (c) the new test class must be run in the full CI matrix (already passes per diff). With those satisfied the change matches K1-K3, preserves all prior behavior when `now=None`, and implements Ruling 57 correctly.