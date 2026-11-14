# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 35 s finish=stop usage in 18648 / out 1521 usd~0.131 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1057 (Circuit Breaker, post-C1 fixes)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   - GLM-5.3-FLASH caught the precise interaction at circuit_breaker.py:146 vs :135-140 (miss count reset on open + ordering of runaway vs miss when until==None), plus the 15 min hold vs "one real call after 30 min" tension that the dynamic hold_s=deadline_s+60 fix directly addresses. I had only noted the trial claim race in general terms.
   - Qwen3.8-27b caught the production/tests/ coupling (STATE at :29-30) and the broad except in proof_ledger.py:364 that swallows BreakerUnreadable. I had not flagged the hardcoded path under tests/package/proof from inside pipeline/.
   - Grok-4.20 noted the providers.py:256 fall-through when every leg in a fidelity chain is open (tried list only). I missed that the new breaker check moves before the recorded/replay guards, changing the exact point a chain can go empty.

2. WHERE DO YOU AGREE OR DISAGREE?
   - Agree with Claude consensus and GLM on the trial hold fix (lines 232, 113-114, test at :463-469): using caller deadline+60 s eliminates both the arbitrary TRIAL_HOLD_S=15 min and the "dead trial blocks forever" case. Mutations B18/B20/B21 killed — solid.
   - Partially agree with Qwen <critical> on BreakerUnreadable → None (providers.py:233, circuit_breaker.py:233-237): it is technically fail-open for the *breaker*, but the ruling and background facts are clear that the breaker never decides verdicts (only whether a live leg is attempted). M12 applies to gates that can produce a pass; an unreadable breaker leaves the chain exactly as pre-ruling-99. The notice mechanism is correct. The "tests/ path" criticism is valid for LAW22 cleanliness but not critical.
   - Disagree with Qwen on "two <critical>": the malformed-record path (allow returns True/None at :491 test) matches the module docstring and ruling ("a malformed record skips nothing").
   - Agree with all three on the late-runaway path (providers.py:204-207 + 305-307) and healthy-model cap using sent max_out (Backend.max_out, FACT on 1,252 answers).

3. NEW FINDINGS FROM THIS REVIEW
   - <medium> circuit_breaker.py:110-114 (allow): trial_until is written under lock, but if two processes call allow() at the exact expiry instant, the first wins the lock, writes trial_until, returns (True,"trial"); the second sees the just-written trial_until and correctly returns (False,"in flight"). However, if the first process crashes *after* _save but *before* the actual complete() call, the second process will be blocked for the full (deadline+60 s). The test at :536-540 only checks the happy path. This is the "one trial" guarantee, but the ruling's "ONE real call may try it again" is now gated by the first claimer's lifetime. Acceptable per updated docstring, but tighter than the original 30 min window.
   - <medium> providers.py:264 + 288: for LocalJudgeBackend the early return dict now includes "max_out" (used by the miss path at :297), but HeimdallBackend and normal paths compute b.max_out(max_tokens) again at :305. Duplicate call; harmless but the dict key is only present on the local-judge early-return path. Test at :558-561 exercises the healthy cap but not this exact key.
   - <low> circuit_breaker.py:86 + _Locked.__exit__: the .lock file is created and never removed (as GLM noted in C1). os.replace is atomic on same filesystem, lock is released, but stray BREAKERS.json.lock accumulates. No functional defect.

4. REVISED SCORES
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | Trial claim / hold     | <high>  | <medium>| Dynamic hold_s=deadline_s+60 (Router passes local-judge floor) resolves the conflicting 15 min vs 30 min observations; tests now cover Heimdall/local-judge durations. |
   | Unreadable state / M12 | <critical> | <medium> | Consensus that breaker is not a verdict gate; unreadable → notice + allow matches "skips nothing" and pre-ruling-99 behaviour. |
   | Concurrency / lock     | <medium>| <low>   | 10 breaker tests + 17 mutations killed; cross-process trial test added; only remaining lock-file litter is cosmetic. |
   | Evidence / STATE line 1| <medium>| <low>   | EVENTS_KEPT=5000, garbage-time filtering (:171-172), summary outside lock — all verified in test_circuit_breaker.py:478-482. |
   | Replay / probe / shadow| <low>   | <low>   | Unchanged guards at _breaker_live:217 and recorded path before breaker check (:1211, :1219) still hold. |

5. FINAL PRIORITY LIST
   P0 CRITICAL: none verifiable from diff+facts.
   P1 HIGH: none.
   P2 MEDIUM:
   - circuit_breaker.py:29-30 — STATE path construction reaches into tests/package/proof from pipeline/ code. Production ledger build (proof_ledger.build_router:334) will write state into the source tree's tests/ dir. If tests/ is absent or the build runs from installed package, OSError → BreakerUnreadable → notice (acceptable) but violates LAW22 "Smallest Diff" and clean separation.
   - providers.py:256-269 — when every model in a fidelity/exclusion chain has an open breaker, call() falls through with only tried entries and no successful leg (Grok C1). M12 fail-closed is allowed, but the ruling assumes at least one family leads; add explicit INCONCLUSIVE or final fallback.
   - circuit_breaker.py:92 — _Locked.__exit__ never cleans the .lock file (harmless but accumulates forever).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The shift from fixed TRIAL_HOLD_S=15*60 to per-call hold_s=deadline_s+60 (passed by Router after applying local-judge floor) simultaneously guarantees "one trial at a time" and prevents healthy models from being skipped longer than the ruling's 30 min window.

7. PRODUCTION READY?
   Yes with conditions: (1) move STATE path out of tests/package/proof/ into a configurable location beside HEIMDALL_HEALTH.json (or document that the proof/ dir is the canonical state home); (2) add one cross-process test that kills a trial holder after claim but before record() to confirm the second process re-claims after the dynamic trial_until; (3) confirm in a real heimdall_first build that breaker_events reach proof_ledger STATE line 1 without slowing the ledger write.

**SHIP: yes with conditions**