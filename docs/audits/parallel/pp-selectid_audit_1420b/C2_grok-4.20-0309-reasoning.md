# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 42 s finish=stop usage in 9352 / out 1343 usd~0.080 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1420b**

1. WHAT DID THEY CATCH THAT YOU MISSED?  
In my Cycle 1 I focused on the mechanical shape of the clamp, the try/except placement around PK.build, and that the guarded block followed the json.dump in the visible diff. I completely missed GLM's P1-1 (res["registry"]=True written unconditionally before the guarded registry block, so a later save failure leaves a lying flag) and the precise interaction between last.get("out") or minimal-dict and the candidate_tries shape for the no-package path. I also did not notice Qwen's observation that the --from-candidate candidate_tries["judged"] bypasses the F2 clamp (it pulls from res["search"] directly). Those were visible in the diff; I overlooked them.

2. WHERE DO YOU AGREE OR DISAGREE?  
- GLM P1-1 (registry flag before guard): Partially agree. The unconditional res["registry"]=True at proof_ledger.py:73 is still present and the guard (now lines 82-92) can still fail after it. The recorded consensus (G1) that "it only matters for --from-candidate and failure is logged" is verifiable from the diff, but the claim in F3 ("a failure there is logged and the record stands") is slightly weakened when the written record lies about registry state.  
- GLM P1-2 / Grok P2 on F2 (under-charge / clamp): Agree. The new clamp at candidates.py:22-24 plus the test at test_candidates.py:127-129 mechanically prevents total judged > initial lineups=8; the "all are charged" why is written and the subtraction can never push lineups negative. The residual "under-credit" is only informational.  
- GLM P1-3 / Grok P2 / Qwen P2 on F1 (malformed found_at): Agree. The due() change (candidates.py:11) now calls _at() (or falls back to old); the new test (test_candidates.py:116-118) shows it raises ValueError. The driver test (test_ledger_build.py:159) confirms due() is exercised inside the refusal block before any out_dir or write occurs. Verifiable from diff only; _at() implementation itself is outside diff.  
- Grok P1 on F3 (all new paths non-crashing): Agree. The nested try/except in try_one (proof_ledger.py:58-61), the last.get("out") or minimal dict (line 70), the post-json guarded block (82-92), and the refusal test cover the surfaces visible in the diff.  
- Qwen's original P1 on negative lineups: Agree it was correctly self-refuted; the clamp forces judged into [0, lineups] before subtraction.  
- Consensus applied changes (C1/C2 tests): Agree; both new tests are present and match the described behavior.

3. NEW FINDINGS FROM THIS REVIEW  
P2: proof_ledger.py:86 (inside guarded block) — CA.seed(reg, json.loads(json.dumps(res, default=str)), name) performs a deep copy via JSON round-trip after package.json has already been written with the same default=str. If res ever contains an object that survives json.dump but not the second round-trip, the registry would diverge from the written record. No such object is visible in the diff, but the double serialization is now on the error path only and was not called out in Cycle 1.  
P2: test_ledger_build.py:152-155 — the malformed-registry test only exercises the --delivered refusal path. No test in the diff shows the exception path inside run_due's try_one (the "build raised" case) actually reaching the minimal-dict branch and still producing a valid package.json with candidate_tries. Verifiable that the code supports it, but coverage is partial.  
(No P0 or P1; both are test-gap / edge-case only.)

4. REVISED SCORES  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| F1 (due() ordering + refusal) | P2     | P2     | No change; malformed test now present and refusal path confirmed before any write. |
| F2 (judged clamp)  | P2     | P2     | No change; clamp and test prevent >8, under-charge is only informational. |
| F3 (registry guard, exception path, minimal dict) | P1 | P2 | Downgraded because guarded block is after package.json, exception path returns "budget" (no state change), and minimal dict supplies required keys (per consensus A1/A3). GLM's flag-lying concern remains but is mitigated by G1. |
| F4 (--from-candidate record) | P2 | P2 | No change; candidate_tries entry now present. |
| Tests              | P2     | P2     | New driver test added; still no direct test of registry-save failure path. |

5. FINAL PRIORITY LIST  
P2 MEDIUM  
- proof_ledger.py:73 — res["registry"] = True is set before the guarded block (GLM P1-1).  
- proof_ledger.py:86 — double JSON round-trip in seed() after package.json already written.  
- test_ledger_build.py:165 — add explicit test exercising the build-raise → "budget" → minimal-dict path to confirm package.json is never lost.  

(No P0, no P1.)

6. THE SINGLE HIGHEST-LEVERAGE CHANGE  
Moving the entire outcome/seed/save sequence after the package.json write inside one guarded try/except (proof_ledger.py:82-92) ensures a paid record can never be lost even if the registry update fails.

7. PRODUCTION READY?  
Yes with conditions: (a) add the P2 test for the build-raise → minimal-dict path (verifiable from diff that the code supports it, but not exercised), (b) document that res["registry"]=True can be written even if the subsequent guarded save fails (the log line already says the record stands). All four F1-F4 claims are now verifiable from the diff alone; the new tests confirm ordering, clamp, refusal-before-write, and exception handling. SHIP once the two P2 test gaps are closed.