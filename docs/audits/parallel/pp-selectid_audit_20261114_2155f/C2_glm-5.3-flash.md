# glm-5.3-flash (z-ai/glm-5.3-flash) 72 s finish=stop usage in 5764 / out 2080 usd_reported=0.000437 usd~0.048 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261114_2155f (final review)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest about the gaps:

- **Grok's P1 (end-to-end coverage through release_auth)** — I noted the residual risk of the "only when present" clause in `package_pin.seal` but did not elevate it to a finding. Grok correctly framed it as a missing *cross-boundary* assertion. The consensus refutation is sound: the integrator's landed `package_formats` returns `None` (both formats) when the key is absent, so absent-key ≠ rejected pin, and the release side was audited separately (batch 85, two cycles, no defect). I should have weighed that landed evidence more heavily before flagging.
- **Qwen's observation on the `whole` fixture** — the test asserts `VP.formats(whole) is None` (line 38), and I did not explicitly trace what `None` means at the integrator. The consensus answers it: absent = both formats, which is exactly the dual-format semantics. Qwen's question was the right question; the landed integrator code answers it. I missed asking it.
- **Grok's note that the diff doesn't touch L-e/L-h/L-k/D5 coverage** — I didn't mention scope-of-branch vs. scope-of-diff at all. It's a fair framing point, though I'd argue it's out of scope for *this* diff (see disagreement below).

What I caught that they largely confirmed rather than extended: the "only when present" clause, the both-directions pinning, and the fail-closed retention via the patched-False branch. Nobody found a defect I also missed — which, after three reviews, is itself evidence.

## 2. WHERE DO I AGREE OR DISAGREE?

**Grok P1 (no end-to-end test through release_auth) — PARTIALLY AGREE, downgrade to P3.**
Agree that a cross-boundary assertion would be stronger. Disagree that it's a defect *of this diff*: the release side is the integrator's landed, separately-audited change (c396c3c8, batch 85, two cycles, no defect, regressions green), and this side's half is pinned by `test_formats` (seal covers formats; stripping breaks the seal) plus this test's both-directions pin. An integration test would be nice-to-have, not a merge blocker. Grok's own P1_OR_WORSE=1 overstates it.

**Grok P3 (comment density, lines 13–15) — AGREE.** Three lines of provenance in runtime code. But the audit package *demands* provenance (who held, what changed, which commit, when), so this is the correct trade-off. Nit.

**Grok P3 (L-e/L-h/L-k/D5 coverage absent) — DISAGREE as a finding against this diff.** The diff is one constant, its comment, and its test. Those subsystems were audited in prior packages (20261114_2131 and the integrator's). Holding this diff hostage to branch-level coverage would violate M1 (smallest diff). It's a branch-level note, not a diff-level finding.

**GLM's withdrawn P2 (test no longer exercises the flip as a transition) — AGREE with the withdrawal.** I independently verified: the held-assertions (lines 33–34) are inside the patched-False block; the eligible-assertions (lines 35–36) are outside it, reading the shipped constant. A revert of the constant alone fails lines 35–36; a change to eligibility logic alone fails lines 33–34. Both directions pinned. GLM's self-correction is correct.

**GLM P3 (`assertNotIn("ticker", ...)` moved inside the patch, line 34) — AGREE, cosmetic.** The ticker exclusion doesn't depend on the flag; only the "16:9-only" hold assertion needs the patched-False context. Harmless.

**GLM P3 (duplicate `formats == ["16x9"]` assertion, lines 24 and 36) — AGREE, cosmetic.** The second occurrence documents that *eligibility* (not just the hold's absence) carries the 16:9-only formats — which is the point of the flip. Keep it.

**Qwen's LAW 20/M2 analysis — AGREE.** The flip implements RULING 93 AMENDED (orchestrator 21:10); it does not reclassify a gate to make a render pass. The hold was a HOLD, not a FAIL; the gates themselves are untouched. Compliant.

**Qwen's dependency-on-landed-commits note — AGREE, and it's the strongest residual risk.** The flip's correctness is contingent on c396c3c8 and 1e4fb5a9 being present. The audit package asserts they're landed; the comment (line 13) cites the commit. If they were ever reverted, this diff's default path fails visibly (release_auth rejects), which is fail-closed. Acceptable.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] `tests/package/test_visual_pin.py` line 35 comment placement.** The comment `# the integrator's release landed` sits on the `assertIsNone` line and `# (c396c3c8): eligible, 16:9 only` on the `assertEqual` line — splitting one provenance note across two assertions. Reads as if "the release landed" explains the *assertion* rather than the *behaviour*. Nit; the module-level comment (visual_pin.py:13–15) carries the full provenance anyway.

**[P3] Asymmetric fixture coverage.** The test exercises the 16:9-only burned-caption clip (both directions) and the `whole` clip (default only, lines 37–39). The `whole` clip's *held* direction is never exercised under patched-False — but since `layout_block(whole)` returns `None` regardless of the flag (a whole-clip was never held), there's nothing to pin. Not a defect; noting it so nobody "fixes" it.

**[P3] No assertion that the patched-False block's `formats` is absent/None.** Under patched-False, the test asserts the hold message but not that `VP.formats(blockware)` behaves differently (if it does). If `formats_of`'s sealing is unconditional, this is moot; if it's flag-gated, the old-direction formats behaviour is unpinned. Given `formats_of` landed in 1e4fb5a9 (outside this diff) and the consensus confirms the seal is unconditional for 16:9-only clips, this is a documentation gap, not a defect. Nobody caught this explicitly; it's the only genuinely new observation, and it's a P3.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `pipeline/visual_pin.py` (constant + comment) | PASS | PASS | Unchanged. Flip implements the amended ruling; provenance cited; fail-closed hold retained. |
| `tests/package/test_visual_pin.py` (contract test) | PASS | PASS | Both directions verified pinned (lines 33–36). New P3s are documentation-level only. |
| Cross-boundary (seal → pin_seal → release_auth) | PASS (with noted residual) | PASS | Grok's P1 refuted by landed integrator evidence; residual risk is fail-closed. Downgraded. |
| Law compliance (LAW 20/M2, M12, M1, L-j) | PASS | PASS | Unchanged. No gate reclassified; hold path retained; smallest diff; release bytes unchanged by this diff. |

No score changes. Three reviews, zero P0/P1 surviving.

## 5. FINAL PRIORITY LIST

Nothing must change before this ships. For completeness:

- **[P3]** `tests/package/test_visual_pin.py:35–36` — split provenance comment; consider one comment above the pair.
- **[P3]** `tests/package/test_visual_pin.py:32–34` — optionally assert `VP.formats(blockware)` behaviour under patched-False, if flag-gated, to fully pin the old direction's formats semantics.
- **[P3]** `pipeline/visual_pin.py:13–15` — comment density; acceptable as-is given audit-package provenance requirements.

No P0, no P1, no P2.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add one integration assertion — a 16:9-only burned-caption clip sealed through `package_pin.seal` and recomputed through the integrator's `check_pin_only` — to convert the currently *documented* (landed-commit) cross-boundary guarantee into a *tested* one; everything else in this diff is already correct.

## 7. PRODUCTION READY?

**Yes.** Conditions (none blocking, all P3):
1. Optionally consolidate the split comment at test lines 35–36.
2. Optionally add the patched-False formats assertion if `formats_of` is flag-gated.
3. Track the cross-boundary integration test as branch-level follow-up, not a gate on this diff.

The flip is minimal, implements the amended ruling, pins both directions, retains the fail-closed hold, and its one residual risk (absent `formats` key) is guarded by the integrator's landed, separately-audited fail-closed behaviour.

P1_OR_WORSE: 0