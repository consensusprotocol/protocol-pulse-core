# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 20276 / out 1565 usd~0.141 (upper-bound price)

**CYCLE 2 — FINAL REVIEW (pp-selectid-0734)**

## 1. WHAT THEY CAUGHT THAT I MISSED
GLM's (d) on double `nv_order()` + closure mutation risk (pipeline/package.py:274 vs :176, with intervening `break` + `v_novoice = val` at :292) and the exact window where `dropped`/`doomed`/`held_map` could theoretically diverge; I had traced the calls but not the latent fragility if code were later inserted before the `no_voice(..., plan=...)` site. Grok's P1 on the original cheap+clip-gate + unbound-`cx` NameError at the combined guard (now restructured at :241-242) was also missed in my Cycle 1; the consensus test `test_a_lone_caption_failure_with_a_clip_failing_its_gate_ends_cleanly` (test_medley.py:392) pins the fix. Qwen's short-circuit order note on `lone_slot(cheap + fid["violations"])` (excluding `cx["violations"]` by construction when `cx["ok"]`) sharpened the (C) guard verification.

What I caught that others under-emphasized: the `rec["no_voice_plan"]` recording on the no-line-up path (:294) and the explicit `plan["registered_skipped"]` propagation into `note` (:179), which the new `test_a_value_loss_leaves_a_registered_line_up_to_the_registry` exercises.

## 2. WHERE DO I AGREE OR DISAGREE?
- **GLM (d) / Grok P1 on state divergence & unbound cx:** Fully agree post-fix. The added `plan=v_plan` parameter (:308, :178) and early `nv_plan = nv_order(...)` capture (:290) eliminate recomputation; `break` + identical args + new test make divergence impossible on all 15 killed mutations. The restructured guard (`if not (cx["ok"] and fid.get("measured") ...`) at :242 binds `cx` in all paths that reach it (every early return is inside the `with nv_pool` or before paid_gates).
- **GLM (b) / Grok on fixed_caption_gates extraction:** Agree. The helper (:37) reproduces the exact `assemble_medley`, `cheap_checks`, `merge_fid`, deterministic `one` dict, and context call that rewrite_alone used; `a_use(pk3)` vs dict-comp is equivalent per the visible code at :56. Voiced-path tests + M19 kill coverage confirm preservation. The cosmetic `why` string change is verifiable and non-gating.
- **Grok's new guard bug (cheap lone-caption + later clip failure):** Refuted by the fixed diff and added test (lines 392-405): clip gate returns None *before* the :241 check, so no NameError and no fixed-caption attempt — correct per (C) ("only the caption fails").
- **Qwen on lone_slot + cx short-circuit and removed test:** Agree. When `cx["ok"]` is False the outer `if` short-circuits to the failure path; `cx["violations"]` never reaches `lone_slot`. The removed `test_a_value_loss_never_counts_toward_ruling_3s_two_failures` is correctly obsolete under (A): both paths now produce the identical shape, so the old count invariant no longer holds. New tests assert outcome, not count.
- **Consensus on (A) implementation:** Agree. `nv_order` decides once (:290), `no_voice` reuses it (:178), added-clip line-up is re-judged on clips-alone (:209), failed no-voice ends without rewrite (:182, test at :365), and ruling-3 path gets (C) too (test at :546).

## 3. NEW FINDINGS FROM THIS REVIEW
<medium> **pipeline/package.py:242 (`fid.get("measured")` in the lone-caption guard):** The guard runs on the `fid` returned from `paid_gates` *before* any `fixed_caption_gates` call. `merge_fid` definition is outside the diff (only a 2-line snippet at :33-34 is visible), so I cannot verify whether a merged `fid` from a prior title verdict carries `measured=True` when the caption is the lone failure. Concrete input: no-voice path where title verdict is replayed (measured=False) but caption alone fails cheap gates — guard may skip fixed-caption path even though (C) requires it. Test `test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption` uses a fresh Rig and does not exercise a merged measured=False case.

<medium> **tests/package/test_medley.py:457 (contexts_pass stub):** Hard-coded `measured=True` and empty violations; the failing-context test (lines 529-531) overrides only for one suite. The ruling-3 + fixed-caption test (:546) uses the pass stub, leaving the measured=False replay path for a fixed caption unexercised on the ruling-91 branch. Not a behavioral break but a coverage gap vs the 15 mutations claimed.

No critical defects; both are narrow and testable.

## 4. REVISED SCORES
| Subsystem                  | Cycle 1     | Cycle 2          | Why changed |
|----------------------------|-------------|------------------|-------------|
| nv_order / plan passing    | 2 mediums   | 0                | v_plan capture + explicit param (:290, :178, :308) eliminates divergence; new tests kill all variants |
| fixed_caption_gates + (C) guard | 1 medium | 1 medium         | Restructured guard resolves NameError; new fid.get("measured") uncertainty is narrower |
| Test coverage & mutations  | 1 medium    | 1 medium         | 19 suites, 543 tests, 15 mutations killed but contexts_pass stub still leaves one measured=False edge |
| Overall risk               | medium      | low-medium       | Plan object is single source of truth; (A) and (C) now match orchestrator rulings exactly |

## 5. FINAL PRIORITY LIST
**P2 MEDIUM** — pipeline/package.py:242: ensure `merge_fid` always produces `fid` with `measured=True` when only caption fails (or change guard to inspect the caption-specific verdict); add Rig case with replayed title verdict.
**P2 MEDIUM** — tests/package/test_medley.py:457: extend `contexts_pass` (and the failing override) to also exercise measured=False on the fixed-caption path for both ruling-3 and ruling-91; confirm no regression on the lone-caption + clip-gate failure test.
**P3 LOW** — pipeline/package.py:294: `rec["no_voice_plan"]` is written only on the no-line-up path; consider moving inside `nv_order` return for uniformity (non-blocking).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Pass the pre-computed `nv_plan` object (now done) so decision and execution can never diverge and the (C) guard at :241 can stay simple.

## 7. PRODUCTION READY?
Yes with conditions: (a) resolve the `fid.get("measured")` merge behavior (or add explicit caption-measured check) at pipeline/package.py:242, (b) extend the contexts stub + one Rig case for measured=False replay on the fixed-caption path.

SHIP: yes with conditions