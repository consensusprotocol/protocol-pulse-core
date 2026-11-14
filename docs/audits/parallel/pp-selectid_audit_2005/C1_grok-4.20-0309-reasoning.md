# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 43 s finish=stop usage in 11306 / out 582 usd~0.071 (upper-bound price)

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: pipeline/context_integrity.py:48 (post-`router.reject(ra)`)**  
Concrete scenario visible in diff: when `failover=True`, `_strict` (or label check) raises `ValueError`/`TypeError`, `ra.backend` has already been seen in `skip`, the `if not failover or ra.backend in skip` short-circuits to `raise` (no infinite loop, no verdict produced). Matches "failover loop terminates" and "no answer out of contract can ever be a verdict".  

**P2: pipeline/package.py:136 and tests/package/test_medley.py:234**  
Concrete scenario visible in diff: every `second_screen` job and every off-writer re-screen in `build` now passes `batch=SECOND_VERDICT_BATCH` (==2) + `deadline_s=SECOND_VERDICT_DEADLINE_S` (==120.0) all the way to `prescreen` → `step_a(failover=True)`. First-verdict calls (no `deadline_s`) remain at defaults (`failover=False`, no deadline). Test expectations updated for chunking and call counts.  

**P2: pipeline/context_integrity.py:35-50 + test_medley.py:268**  
Concrete scenario visible in diff: `while True` + `skip` set + `avoid_model` only activates on parse failure when `failover=True`; successful parse breaks loop and all items receive that `ra.backend`. Without `failover` (first-verdict path) any bad parse still raises exactly as before. Test `test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain` verifies: deepseek (503) → glm (non-JSON) → qwen (good) yields qwen verdict; all three failing yields `ProviderError` (no verdict, no cache).  

**P2: pipeline/model_providers.json:82 + tests/package/test_ledger_build.py:163**  
Concrete scenario visible in diff: `context_verdict` chain becomes xai → deepseek → glm-5.3-flash → qwen (frozen legs removed). `second_screen` groups by first-verdict `(vendor, family)` and calls `prescreen(avoid=that)`, so second verdict cannot be xAI; re-screen avoids writer's family for quoted clips. `glm` entry declares `vendor=heimdall`, `family=glm` (distinct from deepseek). No diff shows any path caching a failed/out-of-contract reply.  

All five audit points listed in the query are satisfied by code+tests present in the diff. No violations of L-j, L-l, M12 or RULING 82 observable.  

**SHIP: yes**