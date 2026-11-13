# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 41 s finish=stop usage in 15140 / out 1366 usd~0.110 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I focused on the seed-reproduction path, the `filled` initialisation, the candidate guard that prevents re-lining/swaps, and the offline dry-run evidence. I completely missed GLM's P1-1 (the `index=None` scan's loose `t.get("lineup")` truthiness allowing a malformed entry to reach `int(t["angle"])` / `t["lineup"][0]` before the later `ValueError` guards) and P1-3 (potential `n_lineup` mismatch after a ruling-41 swap that the original loop counter would have treated differently). I also did not surface Qwen's exact-match concern for `lineup_for(..., moments=ids, clips=(n,n))` even though the diff already contained the `!= ids` guard and the new test at 369-378. The dry-run proof (served recordings with exact seeds 8/108) was decisive but I had not explicitly tied it back to the `n_lineup = candidate["n_lineup"]-1` pre-adjustment plus post-append increment timing.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 (malformed entry): Agree on the original risk; the fixed diff (lines 17-28, 29-34) adds strict `is True`, `med.get("measured") is True`, `replayed is False`, angle-text match, and hook match *before* any `int()` or indexing. The `index=None` scan is now followed by an immediate re-check that raises the documented `ValueError`. The proof_ledger `try/except` path is unchanged but no longer the only protection. Risk closed.  
- GLM P1-2 (stale `supply_exception`): Partially agree. The recorded flag is still passed verbatim to `repeat_ok=...`. However `candidate_lineup` then runs `lineup_for(..., moments=ids, clips=(n,n), need_stand_alone=True, hook_only=True)` *and* asserts exact ID order. If the current pool would produce a different segmentation the candidate is closed before any verdict call. This matches K2/K4 ("until one of its clips fails a gate" and "try ONLY that line-up"). The closure reason distinguishes pool vs. verdict failure. Not a P1.  
- GLM P1-3 (n_lineup after swap): Disagree. The new test (323-335) plus the offline dry-run on the real 12:22 ledger prove the reconstructed `sum(...)` + `n_lineup = recorded-1` + loop timing yields the exact seeds the router served (8 for angle-1 line-up-1, 19/218 for angle-2 line-up-2). The refutation R1 in the prompt is correct.  
- Qwen's `lineup_for` non-determinism: Disagree. The added `clips=(len(ids)-1,len(ids)-1)`, `moments=ids`, `need_stand_alone=True` and the explicit list equality guard (line 60) plus the dedicated test that forces a 4-clip candidate where plain search would have taken a 3-clip subset demonstrate exact reproduction. No P0.  
- Consensus dry-run: Fully agree; it is the strongest evidence that seeds, L-x routing, recorded verdicts, and "only missing calls are paid" all hold.

**3. NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. One P2 observation (verifiable from diff only): `load_candidate:36` does `if not record.get("angle_backend"):` but the later `router.backends[candidate["angle_backend"]]` lookup (line 50) and `SimpleNamespace` construction (99-101) assume the backend string is valid. A record with an unknown backend string produces a clear "its angle's back-end ... is not in the router" closure before any call (tested indirectly by the Rig). Not a law violation; fail-closed. The `filled` per-angle initialisation (line 134) is now correct for the candidate's swapped-branch first iteration and leaves normal builds untouched. No other new issues.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| load_candidate validation | P1     | P2     | Added strict checks and early `ValueError` paths close the malformed-entry surface. |
| n_lineup / seed reproduction | P1-uncertain | P2     | Dry-run + new test + loop timing explanation resolve the swap/interleave concern. |
| candidate_lineup exact-match | P2     | P2     | No change; guard and test coverage already sufficient. |
| candidate guard / no extra calls | None   | None   | Confirmed: angle loop bypassed, `for seed in ()`, early break at recorded n_lineup, failing verdict closes immediately. |
| Overall risk           | Low    | Very low | Fixed diff + dry-run evidence eliminate the P1s I missed. |

**5. FINAL PRIORITY LIST**  
P0 CRITICAL: none verifiable from diff.  
P1 HIGH: none.  
P2 MEDIUM:  
- pipeline/package.py:36 — `angle_backend` presence check could be tightened to also validate it exists in `router.backends` *before* constructing `angles` (minor, fail-closed).  
- tests/package/test_medley.py:331,344 — seed assertions are correct for the tested cases but do not exercise a ruling-41 swap record (the original GLM concern); add one synthetic record if swap semantics change later.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The combination of `n_lineup` reconstruction + preset `swapped=cand_segs` + `if n_lineup >= candidate["n_lineup"]: break` + exact `segs` ID list check guarantees the candidate is judged with byte-identical prompts/seeds, so the router serves the recorded verdicts while still running every current pool gate—exactly the "as it was judged" contract of Ruling 66.

**7. PRODUCTION READY?**  
Yes. The offline dry-run on the real 12:22 ledger already demonstrated correct seed reproduction, recorded-verdict serving, L-x preservation, no extraneous angle/write calls, and proper closure on pool changes. All Cycle-1 P1 concerns are addressed by the validation, guards, and tests in the fixed diff. Ship.