# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 46 s finish=stop usage in 15542 / out 1312 usd~0.111 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-1300 (RULING 65)**

1. WHAT DID THEY CATCH THAT YOU MISSED?  
GLM caught the merge_fid "ok" derivation ignoring a pre-existing non-violations failure marker on v0/d0 (lines 93/99) and the literal cx record on title-hold (line 152). Qwen caught the att["violations"] staleness after rewrite and the hardcoded verdict ok=True on fallback. I had flagged the prompt contract and lone_slot guard in Cycle 1 but missed the exact cheap_t unpack order (line 209) vs. the post-rewrite "if not (fid["ok"] and cx["ok"]) or cheap" check, and I under-weighted how comprehensively the new TestRuling65Caption cases (especially the out-of-contract reply → fallback path) close the loops.

2. WHERE DO YOU AGREE OR DISAGREE?  
- GLM P1-1 (merge_fid stale ok): Partially agree — the `det["ok"] = not det["violations"]` and `ver["ok"] = measured and not ver["violations"]` pattern can theoretically mask a non-violation failure, but VF.check shapes + test fixtures (OK dict, unmeasured test at 395) make it impossible; downgraded.  
- GLM P1-2 (title-hold cx literal): Agree on shape thinness but agree with consensus (G1) that hold aborts before inventory, so non-blocking.  
- GLM P1-3 (rewrite success cheap/why=None): Disagree — refuted R3 is correct; success path raises on cheap2 before return, so "passed" always implies empty cheap.  
- Grok's P2s (lone_slot guard at 202, WRITE_LINE replay safety at 126, fixed_caption format at 158, merge_fid at 90, budget cached flag at 176/400): Fully agree; all match ruling + K1–K5 exactly.  
- Qwen P0 (fixed-caption can seal with failing cheap3 because att["violations"] stale): Disagree — refuted R1/R2; unpack to cheap_t, updated fid3, and the explicit post-rewrite check at 213 plus break prevent any seal. Qwen's own text self-refutes.  
- Qwen on hardcoded fallback verdict: Partially agree on surface but K3 + merge_fid + deterministic run on pk3 make it correct (deterministic violations still surface in fid3["ok"]).

3. NEW FINDINGS FROM THIS REVIEW  
Combined Cycle 1 analysis + full diff + test rig changes reveal no new P0/P1. The only fresh observation is that the fixed_caption path (lines 153–165) runs cheap3, deterministic, and cx3 on the final pk3 bytes (satisfies L-j/L-t), and the test at 360–361 explicitly asserts HS.lint PASS, but the ruling's "states no fact" is only recorded in the verdict class — never asserted at runtime. This is verification hygiene, not a defect.

4. REVISED SCORES  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| merge_fid / fidelity merge | P1     | P2     | Tests + VF contract eliminate stale-ok scenario |
| Title-hold record shape | P1     | P2     | Hold aborts inventory build (G1) |
| Fixed-caption fallback path | P2   | P2     | No change; gates + break logic confirmed |
| Lone-slot guard + redo path | P2   | P2     | No change |
| Budget (replayed/cached) | P2    | P2     | No change |
| Overall ruling compliance | 82    | 96     | Refutations, test coverage (6 new cases), and L-x/L-j verification raised confidence |

5. FINAL PRIORITY LIST  
**P0 CRITICAL:** None. No path seals an ungated caption/title; fixed line matches ruling format exactly; takeaway or mixed violations never take lone path (test 381–384); title hold works; old redo path only changed by the lone_slot guard (line 185); budget fix correct.  
**P1 HIGH:** None.  
**P2 MEDIUM:**  
- pipeline/package.py:93 & 99 (`det["ok"] = not det["violations"]`; `ver["ok"] = measured and not ver["violations"]` — derive from original d0/v0["ok"] for robustness even if VF never produces non-violation failures).  
- pipeline/package.py:152 (title-hold returns synthetic cx with no "measured"; add for consistency with other records even though never sealed).  
- pipeline/package.py:214 (why construction for fallback uses post-merge fid but concatenates old-style cheap + fid["violations"]; harmless but brittle).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE  
merge_fid (lines 86–102) is the linchpin: it alone guarantees the other two lines remain gated while the lone slot's new deterministic/verdict results are integrated without losing measured/replayed status or double-counting violations.

7. PRODUCTION READY?  
Yes with conditions: (1) add the two P2 derivations above before merge to master (trivial), (2) confirm downstream inventory builder never persists the synthetic cx from title-hold (already true per consensus), (3) the existing TestRuling65Caption suite plus full medley regression is sufficient.

**P0 findings**  
None. No scenario seals an ungated or ungated-fixed caption/title; all final bytes pass every required gate (cheap3, deterministic, cx3, HS.lint).

**P1 findings**  
None. All Cycle 1 P1s are either refuted or downgraded.

**P2 findings**  
**P2-1: pipeline/package.py:93,99** — ok derivation ignores original record's "ok" (as GLM noted); concrete: a hypothetical deterministic record with price_now_measured=False but empty violations would flip to ok=True (test at 395 only covers top-level measured).  
**P2-2: pipeline/package.py:152** — title-hold cx is minimal literal (as GLM noted); harmless because hold aborts before seal.

SHIP: yes