# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 19 s finish=stop usage in 37658 / out 1391 usd~0.223 (upper-bound price)

**CYCLE 2 AUDIT — PACKAGE A (pp-selectid-0108A)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I focused on the routing re-keying, the 15-minute down-rule, probe streak reset ordering, and the coherence gap under ruling 88(d). I completely missed (a) the torn-answer-file race in LocalJudgeBackend.complete (glm P0-3 — now fixed by retry-until-deadline + explicit torn flag), (b) the announce() line-1 prepend race between probe thread and build thread (glm P1 — now fixed by _Locked + per-thread tmp), and (c) that _SEEN heartbeat throttle was read outside the lock (qwen P0-2 — now guarded by _SEEN_LOCK). I also under-weighted the main-thread blocking duration of the 40-minute local-judge poll when it is the sole remaining backend for step-A-second (qwen P0-1); the ruling explicitly accepts it, but I did not surface the interaction with Router._within.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P0-1 (StopIteration + unnamed roles keeping Heimdall chain): partially agree — the test at 1222 and ruling 87 text (“switch the whole pin stage”) are in tension, but the implemented design (plan_b_chains only for named roles, else fail-closed) matches the shipped test and the miner’s separate Plan B contract. Not a bug.  
- GLM on HealthUnreadable escape: agree — fixed to ProviderError (law L-m).  
- Qwen P0-1 (LocalJudge blocks 40 min): disagree on severity. Ruling 87 names exactly this case; deadline_floor_s=2400 is deliberate; the integrator’s render latency is expected; _within + on_abandon still books the prompt cost. The test at 1365-1374 verifies the floor is applied and announcement appears once.  
- Qwen P0-2 (_SEEN race): agree — the added _SEEN_LOCK (lines 38, 148, 164) eliminates the pre-lock read.  
- Qwen P0-3 (chain not filtering avoid_* for Plan B): agree on inefficiency but not on criticality; _skip still runs in call(), and the “all avoided → ProviderError” path is the correct fail-closed behavior per law L-s.  
- Grok’s “no P0/P1, SHIP yes”: I now agree after seeing the fixes; my Cycle 1 had two P1s that are resolved.  
- Consensus on refuted items (hard-coded avoid_vendor, coherence gap, Heimdall-only roles): fully agree — evidence in diff and tests matches rulings 85-88.

**3. NEW FINDINGS FROM THIS REVIEW**  
- P2: providers.py:837 (Router.call). When dl is overridden by deadline_floor_s for LocalJudgeBackend the on_abandon closure captures the original caller deadline_s via default argument (deadline_s=dl). If the closure later logs “missed_deadline” it reports the floored value (2400) even though the original verdict deadline was 120. Harmless for ledger but misleading in deadline_log.  
- P2: heimdall_health.py:129 (_prepend). It reads the entire STATE.md into memory, prepends, and rewrites. On a very long build log this is O(n); not a correctness issue but unnecessary given the one-line contract.  
- P2: test_heimdall_health.py:1357-1370 (spy on _within). The test mutates a global P._within; if run in parallel with other tests that import providers it could interfere. (Test is otherwise excellent.)  
- Uncertainty (not a finding): shadow86.pin_texts integration with spotlight pins (addendum) is asserted but the spotlight code itself is outside this package diff; I cannot verify the “first pin sealed under Heimdall-first” clause holds for spotlight.kind.

All other checked items (today routing unchanged except listed 20:33 chains + 120 s, no writer-family verdicts under either routing, xAI-down path still completes except documented coherence gap, HealthUnreadable never guessed, shadow thread never decides or raises into build, probe lifts down-mark only on success, every call on same ledger, flock-protected state, switches recorded in three places) pass.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Health state & probe   | P1      | P2      | _SEEN_LOCK + torn-file retry + HealthUnreadable→ProviderError eliminated races and escape bugs |
| Router re-keying & chain | P1    | none    | Re-key only under heimdall_first; gateway() preserves L-s; tests at 1445-1456 verify |
| LocalJudgeBackend      | P2      | P2      | Blocking duration accepted by ruling; torn-file fix added; still logs misleading deadline |
| Shadow & spend ledger  | none    | none    | Confirmed never decides, own recordings, waited at end, spend captured |
| Overall                | SHIP no (P1s) | SHIP yes with conditions | Fixes address every Cycle 1 blocker |

**5. FINAL PRIORITY LIST**  
**P0** — none.  
**P1** — none.  
**P2** (must fix before next parallel change but not blockers):  
- providers.py:837 — capture and log the original (non-floored) deadline in on_abandon closure for clarity in deadline_log.  
- heimdall_health.py:129 — replace full read/rewrite of STATE.md with a proper prepend that only rewrites the first line (still under flock).  
- test_heimdall_health.py:1357 — use a monkey-patch or pytest fixture instead of mutating the imported module global.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The shared flock-protected health state plus the probe thread that can restore Heimdall-first without restarting the builder is the single mechanism that makes the entire fail-safe (ruling 87) safe across builder, miner, and writer.

**7. PRODUCTION READY?**  
Yes with conditions: the two P2 items above must be addressed (deadline logging and STATE.md prepend), the spotlight merge points must be re-verified in Package B’s audit, and a production dry-run under --routing=heimdall_first with a simulated 16-minute Heimdall outage must be performed to confirm the probe restores mode without losing any verdict. After those three items, SHIP.