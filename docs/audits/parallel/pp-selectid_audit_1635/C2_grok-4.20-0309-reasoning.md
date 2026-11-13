# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 25 s finish=stop usage in 7802 / out 785 usd~0.059 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1635 (RULING 70 cost-basis split)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
GLM’s P1-4 (stale pre-change cache records lacking `usd_basis`) and the explicit cache-hit override paths (visual_pin.py:56–57, 62–63) that force `usd_basis="cached"`. I had noted the cache-exclusion line but did not trace the interaction with old persisted `vcache` entries. Qwen’s observation that `sealed()` is an *inclusion* list (not exclusion) was also missed in my Cycle 1 static scan.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 & cache-exclusion line: fully agree — it is the load-bearing invariant.  
- GLM P1-2 / all models on bool guard at visual_pin.py:44: agree; the guard is correct and necessary.  
- GLM P1-4 (stale records): partially agree — the concrete scenario exists for *old* cache but is neutralized by the hit-path overrides that always emit `usd_basis="cached"`; no money is lost.  
- GLM P2-1 (`or 0.0`): agree it is cosmetic.  
- Grok & Qwen “no P0/P1, all paths carry a basis, tests cover the three cases”: agree.  
- GLM P2 on estimate branch lacking bool guard: disagree it is even a latent defect — `Reply.usd` is a price-table float per background; no realistic path injects a bool.  
- All models on seal/cache-key unchanged: agree.

3. **NEW FINDINGS FROM THIS REVIEW**  
None. Combined Cycle 1 analysis plus re-reading the 141-line diff confirms every record `package.build.see()` can ever receive now carries a basis (fresh `cost()` path, cached-hit override, or test mocks). No path can label estimate as reported or vice-versa. `sealed()` inclusion list still omits both cost fields. Cache key computation is untouched. The updated ledger log prints truthful separate figures.

4. **REVISED SCORES**

| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| cost() decision    | P2:1    | P2:0    | GLM/Qwen clarified estimate-branch latency is non-realistic; bool guard only needed on reported path |
| Cache & stale data | P2:2    | P1:0    | Missed explicit `usd_basis="cached"` override on hit paths; now verified harmless |
| Ledger split & log | P2:1    | P2:0    | All models confirmed split is exact and log conditional matches `estimated_calls` |
| Seal / gate / key  | P2:0    | P2:0    | No change |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** none  
**P1 HIGH:** none  
**P2 MEDIUM:** none verifiable from diff (the three test cases + cache-hit overrides close all paths; old-cache scenario is mitigated exactly as Claude consensus stated).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The `cost(r)` helper plus explicit `usd_basis` tagging (never stored in cache or seal) that forces every downstream accumulation and log line to route reported vs. estimate correctly.

7. **PRODUCTION READY?**  
Yes. (All Cycle-1 conditions answered; tests pass; no gate/seal/cache-key mutation; every record carries a basis.)

**P0: none**  
**P1: none**  
**P2: none**  
**SHIP: yes**