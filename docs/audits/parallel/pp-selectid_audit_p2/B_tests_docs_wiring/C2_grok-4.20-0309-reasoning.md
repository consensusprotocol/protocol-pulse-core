# grok-4.20-0309-reasoning (xAI, medley key) 28 s usage=52459

**CYCLE 2 REVIEW: pp-selectid-p2 (moments-first, after C1 consensus fixes)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I gave high Q1/Q3/Q5 scores (82/88/78) because the visible tests and design pinned hard failures to exact contracts, refused malformed replies, and kept model text out of the final VO/title/caption. I under-weighted the binding gap: self-reported booleans + copied sha256 could be edited post-gate (smoke_r7.py line 888 mutating checks). The Claude reviewers' P0-1/P1-1 on truthiness, unbound inventory, and silent plain-pin fallback for non-dict moments_package were sharper. I also missed that L-v 2 was optional in the original driver and that {"claims": []} was vacuously passing in the fidelity verdict before the fix. The consensus C1/C2 (sealed inventory + package.seal() + exact "PASS" rows) directly addressed what I treated as "uncertain but tested."

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Strong agreement on C1 (unbound self-reported gates) and C2 (blind fidelity on empty/partial claims):** Both are fixed. package_pin.to_pin now refuses anything not exactly in REQUIRED_GATES with status="PASS", replayed=false; seal() recomputes over canonical bytes of segments + edl_vo + title + caption + inventory (smoke_r7.py lines 1097-1099, test_angles.py lines 1273-1277). to_pin raises PinRefused on "NOT RUN", "FAIL", wrong case, replayed=true, or missing inventory. Fidelity verdict now treats missing claims or VERDICT_INCOMPLETE as failure (test_gates.py lines 1520-1527).  
- **Agreement on vendor separation (Q2):** The config test (test_providers.py lines 2060-2085) and avoid_vendor/avoid_family in every verdict role (design §2, Router.call) now cover all writers, failover, and Step A. Step A is explicitly package-independent and stored (design lines 92-93).  
- **Partial disagreement on remaining P1s:** Several "malformed package becomes plain pin" cases are now refused at to_pin or in pinned.build_edl (smoke_r7.py lines 1118-1122 refuses truthy-string "true"; lines 1124-1126 keep plain pin unchanged but never carries moments_checks). The original R7 patch flaws are gone.  
- **Agreement on deterministic rules coverage:** test_gates.py and test_angles.py now exercise PRICE_NOW, DUPLICATE, NAME skips, empty claims, cross-clip, and must-fail context cases (41/41 after rulings 3/5/6).  

**3. NEW FINDINGS FROM THIS REVIEW**  
- The sealed inventory (package.inventory + package_pin.REQUIRED_GATES) now includes all 10 hard gates (vo_fidelity_deterministic/verdict, duplicate, price_now, runtime, r4, context_a/b/c, exclusion, second_pass, coherence). This is a clean L-j pattern; replayed=false is enforced.  
- yield_table.py reveals ongoing oracle defects (L-n yield gap) but correctly notes rule differences (caption timing, missing L-s/L-u in oracle). Not a blocker but documents the gap.  
- run_given_package.py (the orchestrator verification path) still bypasses the full writer loop and uses hardcoded CHAINS; it is test-only but the "given" path must not be reachable in production.  
- Design §8 and lines 201-202 still list WPS=2.6 and FIXED_S as assumptions until a moments-first render measures them; runtime arithmetic (test_angles.py lines 1236-1239) uses them. This is the only remaining "by construction" claim not yet closed.  
- smoke_r7.py globally monkey-patches pinned.validate_range and L.make_lock (lines 1085-1091). Works for the smoke but is brittle if other tests import pinned in the same process.  
- No new P0 fail-open: edited title/caption after seal breaks the sha (lines 1114-1115), non-dict moments_package is refused before build_edl, and release_auth (R7 item 4) now reads the sealed moments_checks.

**4. REVISED SCORES**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Q1 fail-open | 82 | 94 | Sealed inventory + recomputed sha + exact "PASS" + PinRefused on malformed checks closes the self-reported boolean and unbound-bytes vectors I left uncertain. |
| Q2 vendor separation / L-x | 93 | 96 | Config now enforces >=2 back-ends per verdict role avoiding every possible writer family; Step A explicitly never on writer vendor. Minor deduction for local gemma3 lease test coverage. |
| Q3 verbatim / model text | 88 | 92 | Fidelity verdict + deterministic rules now explicitly block partial coverage and non-verbatim supports; title/caption/VO are sealed inside the package_sha256. |
| Q4 deterministic rules | 75 | 88 | Full test_gates.py coverage of empty claims, commentary tests, PRICE_NOW against current_levels, NAME/QUOTE/NUMBER edges, and 41/41 must-fail context cases. Still no full vo_fidelity.py in diff. |
| Q5 tests + R7 | 78 | 93 | smoke_r7, proof_*, ci_mustfail_check, and test_angles now verify the exact failure modes that were vacuous before. Monkey-patch in smoke is the only remaining test smell. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL:** None. The previous unbound self-reported checks and silent plain-pin fallback are fixed.  
**P1 HIGH:**  
- Measure actual WPS and FIXED_S on a rendered moments-first video (design lines 119-121, test_angles.py line 1238) before removing the assumption; runtime feeds R4 and line-up budgets (package.content_range).  
- Ensure run_given_package.py path cannot reach production integrator (it bypasses writer loop).  
**P2 MEDIUM:**  
- Replace global monkey-patches in smoke_r7.py lines 1085-1092 with proper test isolation.  
- Run the postponed yield sweep on the other 9 universes and full bidirectional exam on Heimdall/local (design §8).  
- Confirm coherence_verdict decision rule (design line 111) is blind to writer vendor/family in the unseen package.coherence().

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Close the last assumption by measuring real rendered WPS/FIXED_S on a sealed moments-first package; everything else (gates, sealing, vendor separation, deterministic rules) is now tightly bound and tested.

**7. PRODUCTION READY?**  
**Yes with conditions.** Conditions (must be satisfied before commit): (1) runtime constants measured on real render and WPS/FIXED_S updated, (2) full bidirectional exam run completes with Heimdall/local legs and zero new must-fail passes, (3) yield sweep on remaining universes shows no L-n regression, (4) smoke_r7 monkey-patches removed or isolated. After these, the sealed inventory, exact PASS enforcement, and L-x router make the system tighter than the pre-phase-2 baseline.