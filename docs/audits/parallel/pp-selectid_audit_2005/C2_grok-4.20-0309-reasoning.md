# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 25 s finish=stop usage in 12298 / out 1123 usd~0.090 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2005 (RULING 82 second-vendor step-A failover)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I focused on the while-loop structure and the unreachable defensive guard but missed GLM's P1-1 (avoid_model keyed by ra.backend vs. possible router normalisation) and P1-2 (implicit coupling of deadline_s to failover=True). I also did not flag that the original diff left the "ra.backend in skip" termination path exercised only by the non-failover test. The fixed diff directly addresses these with a real-router test (test_medley.py:278 using mk_router + exact chain), the explicit ProviderError raise on line 52, and the screen_deadlines assertion (test_medley.py:236).

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1: fully agree on the original risk; disagree it remains — the new test_ruling_82_the_context_verdict_chain (ledger_build.py:166) and the failover test (medley.py:278) both use the real Router with matching backend strings ("heimdall:z-ai/glm-5.3-flash", "heimdall:glm" in Fake), so ra.backend == key used in avoid_model is now verified.  
- GLM P1-2 / P1-4: agree on the coupling and cost-accounting note; the diff and consensus confirm first-verdict calls still pass deadline_s=None (screen_deadlines=[None, 120...]), second-vendor paths derive failover=True, and abandoned calls book upper-bound per existing ruling 48.  
- GLM P1-3: partially agree — the all-three-failing case now exercises both router-level exhaustion and the skip guard (qw.answer = "still not JSON" triggers ProviderError after glm and qwen both fail contract).  
- Qwen's original P0s: agree they were correctly downgraded; the fixed diff makes the defensive raise explicitly ProviderError (lines 51-52), matching the docstring.  
- Grok's P2 confirmations: agree on all — no verdict from out-of-contract, first path unchanged, no caching of failures, family/vendor avoidance intact.  
- Consensus items: all "Implemented" and "Confirmed from the code" sections match observable changes in the fixed diff.

3. **NEW FINDINGS FROM THIS REVIEW**  
P2-1 — pipeline/context_integrity.py:51 (`import providers as P` inside while/except). Verifiable from diff; the defensive path now raises the documented ProviderError but performs a repeated import on every contract failure after the first. Style only; no functional defect.  
P2-2 — tests/package/test_medley.py:294 (`def P_ProviderError(): import providers`). Verifiable; the helper avoids a top-level import but adds an extra indirection for a test that already imports context_integrity and test_providers. Minor.  
No new P0 or P1 findings; every audit point listed in the query is now exercised by the updated tests.

4. **REVISED SCORES**  
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| Failover loop & termination | P1     | P2     | Fixed diff adds explicit ProviderError on "ra.backend in skip", real-router test, and comment referencing audit 2005 C1. |
| avoid_model key matching   | P1 (missed) | None | New chain test and Fake back-ends use exact production names; router contract now verified from diff. |
| deadline_s / failover wiring | P1    | None   | screen_deadlines list assertion pins exact call sites (first=None, all others=120); prescreen derivation visible. |
| Test coverage of spent chain | P1   | P2     | All-three-failing case now reaches ProviderError with failover=True; mutation tests mentioned. |
| First-verdict invariance   | None   | None   | Confirmed unchanged (no deadline, no failover). |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** none verifiable from diff.  
**P1 HIGH:** none.  
**P2 MEDIUM:**  
- pipeline/context_integrity.py:51 — import providers as P inside the loop (style; move to top).  
- tests/package/test_medley.py:294-296 — P_ProviderError helper (could be direct import now that test_providers is already pulled in).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The while-loop + skip set + avoid_model= + "if ra.backend in skip: raise P.ProviderError" (context_integrity.py:35-52) plus the SECOND_VERDICT_BATCH=2 / deadline_s=120 wiring guarantees the second-vendor path traverses the full chain without ever caching or promoting an out-of-contract answer, exactly closing the 19:23 outage while leaving the first-verdict path untouched.

7. **PRODUCTION READY?**  
Yes. All Cycle-1 conditions (ProviderError on defensive path, exact backend-key matching, deadline passing to every second-screen/off-writer call, first-verdict invariance, no caching of failures) are satisfied by observable code and tests in the fixed diff. The 15 suites pass and mutation tests would catch removal of any piece. SHIP.