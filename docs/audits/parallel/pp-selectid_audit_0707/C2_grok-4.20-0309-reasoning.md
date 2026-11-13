# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 8913 / out 1096 usd~0.072 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0707 (Ruling 48 spend guard on vendor-reported basis)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In my Cycle 1 I focused on reservation-upper-bound invariance, the stop-at-$10 start-gate semantics, and default="estimate" caller preservation but completely missed the legacy-ledger fail-open (glm P1-2: .get() returning 0.0 when both reported keys absent). I also did not surface the post-build router.spent() call that could swallow the required spend_ruling_48 record on any ledger error (glm P1-1). Qwen's floating-point test brittleness and spent()==0.0-when-no-spend_path observation were likewise outside my original scope.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Fully agree with glm P1-2 and the implemented fix (explicit "calls but neither key" → SpendLimit). The new check + test case at lines 173-176 verifies fail-closed.  
- Fully agree with glm P1-1 and the implemented try/except; the record is now written on every path (including "unreadable: SpendLimit..."). R1 (res=None) is refuted by the diff: res is always a dict when the assignment is reached.  
- Agree with grok/qwen/claude consensus that the $10 start-gate (proof_ledger:73) satisfies "At $10 reported stop and tell me" while still allowing an in-flight build to hit the $12 hard cap; I do not read the ruling as requiring mid-build aborts.  
- Partially agree with qwen on spent() returning 0.0 with no spend_path: behavior is unchanged and intentional (diff lines 39-40, 49), but the new public-API docstring makes the subtlety more visible.  
- Disagree with qwen on the assertAlmostEqual(..., places=6) being a defect: test values are fixed literals (3.46+1.81) and the tolerance is deliberately loose; it is not fragile under the diff's own data.

**3. NEW FINDINGS FROM THIS REVIEW**  
None that rise above P2. The combined Cycle 1 analysis plus the fixed diff reveal no new P0/P1 defects. The legacy-ledger guard, post-build try/except, updated docstrings, and test coverage for both bases are verifiable from the diff text. The ruling's "keep running total on STATE line 1" requirement cannot be literally verified from the diff alone (it relies on unshown say() → STATE machinery) but the added say() calls at proof_ledger:78-79 and :93-94 match the intent.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| providers.py (_basis_total / spent / _reserve) | P1 | P2 | Legacy-ledger check and exception path now present and tested; fail-closed behavior verified. |
| proof_ledger.py integration & accounting | P1 | None | try/except around router.spent() guarantees spend_ruling_48 record is written on every path. |
| Test coverage & assertions | P2 | P2 | Floating-point test still present but acceptable; new test case for unreadable ledger added. |
| Ruling semantics ($10 stop vs $12 cap) | None | None | Consensus reading confirmed; no change. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL** — none verifiable from diff.  
**P1 HIGH** — none.  
**P2 MEDIUM** —  
- tests/providers/test_providers.py:161,163,165 — assertAlmostEqual(..., places=6) on summed floats (3.46+1.81 etc.); representation can yield 5.2700000000000005. Not blocking but should be places=4 or explicit sum.  
- tests/package/proof_ledger.py:89 — bare `except Exception` (noqa BLE001); acceptable for audit record but could be narrowed to (SpendLimit, KeyError, TypeError, json.JSONDecodeError).  
- pipeline/providers.py:31 — "calls" check uses d.get("calls", 0) while estimate path does not; consistent with background but unverifiable that _settle always emits "calls" (minor).

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The paired changes (providers.py:31-33 legacy-ledger SpendLimit + proof_ledger.py:87-90 try/except around post-build spent()) ensure the guard never silently under-counts and the required spend_ruling_48 record is never lost.

**7. PRODUCTION READY?**  
Yes with conditions: tighten the three P2 items above (or accept them explicitly), confirm that the new say() lines appear on STATE line 1 exactly as the ruling requires (unverifiable from diff), and run the full test suite (test_providers + proof_ly + proof_ledger) to confirm no side-effect ordering issues in the single TemporaryDirectory test.

**P0** none  
**P1** none  
**P2** (see list above)  

**SHIP: yes with conditions**