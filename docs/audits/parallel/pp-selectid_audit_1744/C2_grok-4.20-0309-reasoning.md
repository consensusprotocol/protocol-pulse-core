# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 19 s finish=stop usage in 22374 / out 1079 usd~0.139 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1744 (Lock Pre-check for Rulings 68/72)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I (like Grok) asserted the four gating points were sufficient and missed the bare `lock_check(segs)` calls that could raise out of `build()` (leaving no ledger row or `tried` record). I also missed that `pin_problems()` did not compare the *sealed text* that the lock had actually passed. GLM caught both; the fixed diff (C1-a/C1-b) adds `try/except` → `LP.failed(e)`, `lock_stop` on no-verdict in the no-voice path, recording of the passed text inside `apply()`, and the `r.get("text") != s.get("text")` check in `pin_problems`. Those were real gaps. I also under-weighted the mixed-request-id reuse subtlety GLM raised (even though it was later refuted by contract).

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-2 (exceptions crashing build) & P1-3 (pin text check): fully agree — both were defects; the fixes are exactly what the audit required and are now verified by the new mutation tests.  
- GLM P1-1 (mixed request_ids on reuse): partially agree on the theoretical risk but ultimately disagree — `_matches()` keys on window/role/approved_text/trim fields exactly as the contract dictates (“newest entry whose window equals…” per-segment files). The integrator’s cache is per-segment; a wider-window lineup cannot match a narrower one. The test `test_a_missing_answer_asks_the_whole_line_up…` and the “any error → resend” condition close the practical hole.  
- Qwen’s P2 items (KeyError speculation, lock_stop logic, atomic send, attested field): agree they are verifications, not defects; the code is defensively written.  
- Grok’s “all four required checks hold exactly”: agree post-fix; the added wrappers and `pin_problems` comparison now make the statement true.  
- Claude consensus on implemented vs refuted: agree in full.

3. **NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. One P2 observation only: `lock_precheck.check:164` re-evaluates `any(... not in PASS | {"adopt_spoken", "hold"})` on *already-cached* answers; an ancient “error” entry forces a resend (good), but a stale “hold” from a different decoder version is reused forever because `answer()` only filters by request_id *after* the send path. The contract says the integrator caches per-segment content, so this is not a functional break, but it is the only place where “freshness” is not strictly enforced. Test coverage hits the error-resend path but not a mixed-version hold scenario. (Verified only from diff; integrator behavior outside scope.)

4. **REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Exception / fail-closed handling | P1 (missed) | P2 (now wrapped) | Fixes for bare calls and `LP.failed(e)` added |
| Pin-stage text verification | P1 (missed) | None | `pin_problems` now compares `r.get("text")` (C1-b) |
| Request-id / reuse coherence | P2 | P2 (minor) | Mixed-request reuse is contract-compliant but stale-hold edge remains |
| Overall gating (build/apply/pin) | Clean | Clean | All four gates now verified with tests |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** none.  
**P1 HIGH:** none.  
**P2 MEDIUM:**  
- `pipeline/lock_precheck.py:164` — stale “hold” from prior decoder version can be reused without re-validation against current request_id (add optional `max_at` filter or force resend on any non-PASS when request_id differs).  
- `tests/package/test_lock_precheck.py:568` — appearance callback only tested for success path; no mutation test that forces a second poll cycle after a transient error entry.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Wrapping every `lock_check()` call and making “no verdict” set `lock_stop` + `budget` ensures the entire medley search fails closed without ever sealing unapproved text or losing the build record.

7. **PRODUCTION READY?**  
Yes with conditions. Conditions: (a) confirm with the integrator that per-segment cache entries are truly context-free (no hidden line-up dependency), (b) add the optional `max_at` freshness guard to `answer()` before merge, (c) run the full proof ledger with live integrator results directory to validate end-to-end SHA256 seal stability on adopted texts.

**P0:** none verifiable from diff.  
**P1:** none verifiable from diff.  
**P2:** one (see #5 above).  

SHIP: yes with conditions