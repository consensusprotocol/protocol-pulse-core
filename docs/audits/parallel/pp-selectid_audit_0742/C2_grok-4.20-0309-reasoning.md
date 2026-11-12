# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 25865 / out 1257 usd~0.161 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0829 (FIXED diff)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok's concrete before/after on the 63-word package (runtime 68 s → 72.41 s, R4 41.0 % → 38.9 %) and the exact test_the_moments_r4_on_tonights_numbers that proves the new gate still rejects it via the hard 70 s runtime floor. GLM's dimensional/unit concern on content_range (VO_S[0] subtracted from seconds) and the unknown-slot violation drop in the old majority path. Qwen's observation that self_repair's span rebuild + compare() could theoretically leak a mismatch if the primary transcript itself contained the repair token. The consensus synthesis (K1/K2) and the new pin_and_verify.py + exhaustive inversion test were not in my Cycle 1 mental model.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Grok P0 (R4 share change accepting previously rejected packages): Partially agree. The algebra change + share bump to 0.45 does widen the R4 region, but the added runtime() mirror + test_the_moments_r4_on_tonights_numbers + pin_and_verify against deployed edl_rules._r4_moments make the net gate stricter on the concrete example (fails runtime). Consensus correctly kept/disclosed it; LAW 20 is satisfied because the factory itself now refuses what the builder refuses.  
- GLM P0-1/P1 (majority dropping violations on slot mismatch): Agree on the original risk. The fixed majority() hardens it (whole() treats unknown slot or "-" as failing every slot, C1 H1) and the new test_a_flipping_verdict_is_decided_by_the_majority_of_three exercises 2-1, unmeasured, and even-run refusal. No longer a P0.  
- GLM/Qwen/Grok on self_repair 4-letter heuristic: Fully agree. The new self_repair() (exact _w(fw) == _w(first), same-speaker, proper prefix, dash-terminated, leading-only) plus the test_a_leading_self_repair_is_part_of_the_sentence_and_nothing_else_is closes the hole. K1 implemented.  
- All on runtime algebra fidelity: Agree the new test_the_r4_word_bounds_invert_runtime_and_the_share_exactly (15-50 s, 1-4 VO lines) resolves the P1 uncertainty I and others flagged. No dimensional error remains; FINAL_TAIL_S == 14.30 matches deployed.  
- Grok P2 on duplicate violations in inventory: Disagree — the seen set + per-slot collection in majority() plus votes_of() in inventory() produces deterministic shape; release_auth.py only cares about final "ok" and the seal.

**3. NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. The once_then_majority + with_votes + majority pipeline is tight: first-run PASS short-circuits, unmeasured = fail vote (L-m), even run count refused, splits recorded, replayed tri-state honest (None if any non-bool). The --precheck and renderer_geometry (outside seal) are audit-only. pin_and_verify.py is excellent smoke against the real deployed factory. The only residual P2 is that replayed=True on the aggregate when only one of three runs was replayed (any(reps)) can make inventory rows slightly less precise than the per-run list, but this matches the Cycle 1 consensus and does not affect the gate decision.

**4. REVISED SCORES**  
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| package.py (runtime/R4/share) | P1     | P2     | Inversion test, pin_and_verify, and concrete 72.41 s rejection close the algebraic and acceptance-region worries. Share bump is ruled. |
| vo_fidelity.majority + once_then_majority | P1 | P2     | Hardening for whole-reply/unknown slots + comprehensive test_gates.py coverage; no violation can now be dropped. |
| transcript_truth.self_repair/edges/verify_segment | P2 | None   | Exact-match + leading-only + test that proves "nothing else slips through" implements ruling 8 perfectly. |
| inventory / gates recording | P2     | P2     | Votes/splits now carried; minor replayed tri-state remains but is documented. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL:** none.  
**P1 HIGH:** none.  
**P2 MEDIUM:**  
- pipeline/vo_fidelity.py:325 (whole()) and :351 (splits list) — confirm in CI that an unknown-slot violation still produces exactly one VERDICT_MAJORITY entry per failed slot and does not duplicate across runs (already exercised but worth pinning).  
- pipeline/package.py:160 (replayed = any(reps)) and inventory:171 (rep() helper) — the tri-state is honest but could be a per-run list for full transparency; not a gate decision.  
- tests/package/test_angles.py:817 (the inversion test) — add one borderline float case at exactly 70.00 s to prove rounding cannot flip the runtime gate.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The combination of runtime() now being the factory's exact arithmetic, the once_then_majority wrapper that limits expensive model calls, and the tightened self_repair that eliminates the 4-letter heuristic while preserving L-v 2 integrity.

**7. PRODUCTION READY?**  
Yes with conditions: (a) pin_and_verify.py must be run on at least one real sealed package before merge and must report rule_r4 PASS on the deployed edl_rules; (b) the new majority test in test_gates.py and the R4 inversion test must pass in CI; (c) the renderer_geometry evidence must remain outside the seal (already true).

SHIP: yes with conditions