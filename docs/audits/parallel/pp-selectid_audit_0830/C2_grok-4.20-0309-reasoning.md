# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 35 s finish=stop usage in 9217 / out 1286 usd~0.078 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0830 (RULING 54 / PROPOSAL 1)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
In my Cycle 1 I focused on the combinatorial risk of appending the entire cleared pool and on whether `filled` could contain ids that `lineup_for` later dropped. I completely missed GLM's P1-4 (a fill that is mostly pool clips violates "completing" the angle) and the elegant `accept=half` callback solution that enforces the invariant *inside* the search. I also missed that the prompt change (lines 11-12, 21-22) now gives the model the exact same LAST/hook rules that `placement()` and `lineup_for` use, which is the highest-leverage upstream fix. GLM's latent-contract warning on `dropped` (P1-1) was also sharper than my own note.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 (dropped/doomed contract): fully agree — the original version was a trap; the fixed diff (lines 52-53) explicitly filters `not in dropped` before the SWAP_TOP cap, eliminating the trap.  
- GLM P1-2 (`filled` calculation): agree it was subtle; the C2 version uses `mine = set(own)` *after* building `rest`, then `[m["moment_id"] for m in segs if m["moment_id"] not in mine]`, which is now correct even if `lineup_for` drops some own moments.  
- GLM P1-3 (placement truthiness): agree the `is True` vs truthy check looks asymmetric but exactly reproduces the condition already inside `lineup_for` (verified by test_medley:149-150).  
- GLM P1-4 / P1-5 (half-own rule, unbounded pool): agree both were real issues; both are fixed (SWAP_TOP + `accept=half` lambda at 58 + call at 82-83).  
- Grok/Qwen "no P0/P1, SHIP yes": partially agree — they correctly saw that rules are unchanged and first-lineup-only is guarded, but underestimated the value of the half-check and prompt changes that GLM surfaced. Consensus table correctly marks all GLM items as answered or fixed.

3. **NEW FINDINGS FROM THIS REVIEW**  
P2 (pipeline/package.py:60): `pool_fill` hard-codes `need_onset=True, need_stand_alone=True` on both `lineup_for` calls. This matches the call site at 98 but is a duplicated magic value; a future change to defaults would silently diverge for filled angles (unverifiable from diff alone whether the orchestrator ever wants different flags for fills).  
P2 (pipeline/package.py:51): `own = [mid for mid in angle["moments"] if mid in pool]` silently drops any moment the angle proposed that is no longer in the cleared pool. The test never hits this; behavior is therefore only verified for the 07:14 shape.  
No new P0 or P1. The `accept` callback, SWAP_TOP cap, and explicit `dropped` filter close the loops and explosion risks that all three Cycle-1 reviewers worried about.

4. **REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| pool_fill + accept rule| P2      | P2      | Half-check is elegant but still an extra path that only the new test exercises; no regression but not zero-risk. |
| placement() + prompt   | P1      | P2      | GLM's asymmetry concern resolved; prompt now perfectly mirrors rules. |
| dropped/doomed handling| P1      | None    | Explicit filter in rest list + pass-through to lineup_for removes the latent trap. |
| build integration & first-lineup guard | P1 | None | n_lineup==0 guard + comment at 102-104 now bullet-proof. |
| test coverage          | P2      | P2      | Added tests hit the exact 07:14 failure, half-rule edge, and prompt text; still no test for SWAP_TOP truncation. |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** None.  
**P1 HIGH:** None.  
**P2 MEDIUM:**  
- pipeline/package.py:60 — remove duplicated `need_onset=True, need_stand_alone=True` by making them default in the function signature or by passing the same variables used at the original call site.  
- pipeline/package.py:51 — document or assert that every id in `angle["moments"]` must be present in the pool passed to `pool_fill`.  
- tests/package/test_medley.py:141 — add explicit case exercising SWAP_TOP truncation (currently only 5-moment test).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The `accept=half` callback injected into `lineup_for` (lines 82-83) plus the prompt that tells the model the exact same LAST/hook limits together guarantee both "the angle's play order kept" and "fewer unformable angles arrive," which is the entire purpose of Ruling 54.

7. **PRODUCTION READY?**  
Yes with conditions: (a) the two P2 items above must be addressed or explicitly accepted as non-blocking, (b) SHORT_CLIP_S value must be confirmed to be exactly 8 so the prompt text "under 8 s" never drifts, (c) the orchestrator must consume the new "pool_filled" key without crashing on older replay data. After those three items the change is safe to ship; every line-up rule remains enforced, dropped moments stay dropped, and the 07:14 failure mode is fixed while preserving the proposer's intent.

**P0: None**  
**P1: None**  
**P2: 3 items (package.py:51, :60; test_medley.py:141 — see list above)**  
**SHIP: yes with conditions**