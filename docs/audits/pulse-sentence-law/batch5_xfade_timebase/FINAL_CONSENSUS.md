# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 07:29
Models: gpt4o, gemini (+1 failed — grok budget exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 8/10 | 9/10 | N/A | 8.5/10 |
| LAW 22 Compliance | 2/10 | 3/10 | N/A | **2/10** |
| SENTENCE LAW | Unverifiable | Unverifiable | N/A | Unverifiable |
| SELECTION LOCK | Unverifiable | Unverifiable | N/A | Unverifiable |
| SNAP LIMIT | Unverifiable | Unverifiable | N/A | Unverifiable |
| ONSET/TAIL | Compliant | Compliant | N/A | Compliant |
| CREDITS | Unverifiable | Unverifiable | N/A | Unverifiable |
| LAW 20 / M2 | Compliant | Compliant | N/A | Compliant |
| M12 FAIL CLOSED | Compliant | Compliant | N/A | Compliant |
| Test Quality | 9/10 | 9/10 | N/A | 9/10 |
| Overall Readiness | NOT READY | NOT READY | N/A | **NOT READY** |

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U-1: Potential LAW 22 Violation — v2f Reference Render Unverified
**Both models agree. This is the single highest-confidence finding.**

- **What it is:** LAW 22 mandates that the frozen `v2f_2026-11-06` reference render must be byte-identical across re-renders. The `settb=1/{FPS}` insertion modifies the core `ffmpeg` filtergraph for every dissolve transition, not just the failing edge case. Any change to the filtergraph can alter the encoded bitstream — even if perceptually invisible — causing a byte-identity violation.
- **File/Line:** `pipeline/pulse_transitions.py`, lines 13–14
- **What to change:** Before merging, re-render the `v2f_2026-11-06` reference case with this code applied and compute a SHA256 hash of the output. Compare against the hash of the previously frozen reference. If they match: document the hash in the audit trail and proceed. If they differ: this change cannot be merged without a formal LAW 22 exemption from the designated authority. The diff must be reverted or redesigned (e.g., conditionally apply `settb` only when a timebase mismatch is detected, not unconditionally).

### U-2: Scope Mismatch — Feature Name Does Not Match Diff Content
**Both models agree.**

- **What it is:** The branch is named `pulse-sentence-law` and the feature is tagged `pulse-sentence-law`, but the diff exclusively addresses a video transition renderer bug (`xfade` timebase mismatch). No code in the diff touches sentence detection, punctuation boundaries, audio pause logic, clip selection, or any of defects D1–D5 referenced in the feature description.
- **File/Line:** Branch name, commit message, feature description metadata
- **What to change:** Either (a) rename the branch/commit to accurately describe the fix (e.g., `fix/xfade-timebase-mismatch` or `fix/dissolve-after-hard-cut`), or (b) document explicitly that D6 is the only defect addressed in this commit and open tracked issues for D1–D5. This is a process and maintainability issue, not a code defect, but it will cause confusion in git archaeology and release notes.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All findings at this confidence tier are already captured under UNANIMOUS FINDINGS above. With only two functioning models, majority and unanimous are equivalent in this cycle.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1: Missing Automated LAW 22 Regression in CI/CD — Gemini Only
- **What Gemini observed:** The fact that this change reached a Cycle 2 audit without anyone having run the `v2f` reference regression points to a structural gap in the CI/CD pipeline. There is no automated, non-skippable gate that re-renders the frozen reference and fails the build if the output hash changes. Relying on human auditors or developers to remember LAW 22 manually is fragile.
- **Assessment: IMPLEMENT.** This is the most valuable systemic finding of the entire two-cycle review. The LAW 22 violation risk in this diff is a symptom; the disease is the absence of an automated enforcement mechanism. A single test fixture that (1) renders the `v2f_2026-11-06` case, (2) computes SHA256 of the output, and (3) asserts equality against a pinned hash would have caught this before it reached audit. This should be treated as a P1 infrastructure requirement immediately following resolution of the P0 blocker.
- **File to create:** `tests/regression/test_v2f_reference_render.py` (or equivalent in the project's test harness)

---

## CONFLICTS (models disagree — your tiebreaker)

### C-1: Cycle 1 Correctness Score — GPT-4o (9/10) vs. Gemini (8/10)
- **GPT-4o position:** The local fix is correct; score 9/10.
- **Gemini position:** Local correctness is high, but system-level correctness (adherence to invariants including LAW 22) is unproven; score 8/10.
- **Tiebreaker:** Gemini is right. A score of correctness that ignores system-level invariants is incomplete. The fix is locally sound but its correctness in context is unverified. **Consensus: 8.5/10**, leaning toward Gemini's framing. Code that may violate a frozen-output invariant cannot be scored 9/10 for correctness.

### C-2: Initial Cycle 1 Verdict — GPT-4o (READY) vs. Gemini (NOT READY)
- **GPT-4o position:** READY (Cycle 1 only; reversed in Cycle 2).
- **Gemini position:** NOT READY (both cycles).
- **Tiebreaker:** Gemini was correct from the start. GPT-4o's self-correction in Cycle 2 is noted and appropriate. The LAW 22 risk was present in Cycle 1 and should have been caught then. No conflict remains in Cycle 2 — both models agree NOT READY.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

### VS-1: The `settb=1/{FPS}` Fix Is Technically Correct
Both models independently confirmed that inserting `settb=1/{FPS}` before the `xfade` filter is the standard, correct `ffmpeg` solution for a timebase mismatch between a raw input stream and the output of a prior `concat` filter. The logic is sound, the units are correct, and the change addresses a real and reproducible `ffmpeg` error.

### VS-2: The New Test `test_dissolve_after_a_hard_cut_renders_frame_locked` Is Excellent
Both models scored this test 9/10. It correctly isolates the failure condition (dissolve after a hard cut), makes strong and specific assertions (frame count, audio duration, luma values), and is non-vacuous. The audio onset check in the test (lines 46–47) also verifies that ONSET/TAIL compliance is maintained. **Do not modify this test.**

### VS-3: M12 FAIL CLOSED Compliance Is Intact
Both models confirmed that the change fixes a bug causing an unintended render failure (a hard `ffmpeg` crash) rather than introducing a silent pass on missing data. The fail-closed principle is preserved.

### VS-4: LAW 20 / M2 Compliance Is Intact
Both models confirmed that no gate thresholds are altered. The change is scoped to the `ffmpeg` filtergraph construction only.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence | Notes |
|---|---|---|---|
| SENTENCE LAW | Unverifiable | Low | Diff does not touch sentence boundary logic. Neither compliant nor violated — simply out of scope. |
| SELECTION LOCK | Unverifiable | Low | Diff does not touch clip selection. Out of scope. |
| SNAP LIMIT | Unverifiable | Low | Diff does not touch cut point adjustment. Out of scope. |
| ONSET/TAIL | **Compliant** | High | Test lines 46–47 verify audio sync is maintained. Both models agree. |
| CREDITS | Unverifiable | Low | Diff does not touch avatar/credit generation. Out of scope. |
| LAW 20 / M2 | **Compliant** | High | No gate thresholds altered. Both models agree. |
| M12 FAIL CLOSED | **Compliant** | High | Fix prevents unintended crash; does not mask legitimate failures. Both models agree. |
| **LAW 22** | **VIOLATION (UNMITIGATED RISK)** | High | Core filtergraph modified; v2f reference render not re-verified. Both models agree this is a P0 blocker. |

**Final LAW determination:** One law has an unmitigated violation risk (LAW 22). Five laws are unverifiable due to scope (the diff simply does not address those subsystems). Three laws are confirmed compliant. The single LAW 22 risk is sufficient to block merge.

---

## SECURITY CONSENSUS

No security issues were identified by either model. The change is scoped to `ffmpeg` filtergraph string construction. There is no user input reaching the filtergraph template that could introduce injection risk in the modified lines. This section is **CLEAR** for the reviewed diff.

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

### WCG-1: Automated LAW 22 Reference Render Gate in CI/CD
Both models converged on this gap — Gemini explicitly, GPT-4o implicitly (by agreeing that LAW 22 proof must be provided before merge, implying no automated mechanism exists to enforce it). A world-class rendering pipeline does not rely on auditors to remember to check frozen-reference compliance. It enforces it automatically at every build. The absence of this gate is the root cause of why this change reached a Cycle 2 audit with an unresolved P0.

**Gap:** No automated, non-skippable CI test re-renders `v2f_2026-11-06` and asserts byte-identical SHA256 output.
**Remedy:** Add `tests/regression/test_v2f_reference_render.py` with a pinned hash assertion. Run in the main CI gate, not as an optional job.

### WCG-2: Scope Clarity Between Feature Name and Actual Diff Content
Both models flagged that the branch/feature name `pulse-sentence-law` does not match what the code actually changes. A world-class codebase maintains a clean, accurate mapping between feature names, branch names, commit messages, and diff content. Misleading feature names degrade git archaeology, release note accuracy, and incident retrospectives.

**Gap:** Branch/feature name implies sentence law work; diff contains only a renderer fix.
**Remedy:** Accurate naming convention enforced at PR creation (e.g., a PR template that requires the author to list which defect IDs are addressed and what subsystems are touched).

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Prove LAW 22 compliance for v2f_2026-11-06 reference render
            | pipeline/pulse_transitions.py, lines 13–14
            | Models: all (2/2)
            | Re-render v2f_2026-11-06 with this code applied. Compute SHA256
            | of output. If hash matches frozen reference: document hash in
            | audit trail, proceed to merge. If hash differs: REVERT this
            | change and redesign (consider conditional settb application only
            | when timebase mismatch is detected, to avoid touching renders
            | that currently pass). No merge permitted without this proof.

P1 HIGH     | Add automated LAW 22 regression test to CI/CD pipeline
            | tests/regression/test_v2f_reference_render.py (new file)
            | Models: gemini (unique, but unanimously endorsed after review)
            | Create a non-skippable CI test that renders v2f_2026-11-06,
            | computes SHA256 of output, and asserts equality against the
            | pinned hash. Fails the build on any deviation. This closes the
            | systemic gap that allowed a potential LAW 22 violation to reach
            | a multi-cycle audit undetected.

P2 MEDIUM   | Correct feature/branch name to accurately describe diff content
            | Branch name, commit message, PR description
            | Models: all (2/2)
            | Rename branch to fix/xfade-timebase-mismatch or equivalent.
            | Update commit message to reference D6 specifically. Open
            | separate tracked issues for D1–D5 if they remain unaddressed.
            | This is a process/maintainability fix, not a code defect.
```

---

## CYCLE 2 VERDICT

**NOT READY FOR PRODUCTION.**

After two full cycles of multi-model review, the absolute final blocker is:

> **LAW 22 compliance has not been proven.** The `settb=1/{FPS}` insertion modifies the `ffmpeg` filtergraph for all dissolve transitions unconditionally. The frozen `v2f_2026-11-06` reference render has not been re-executed and hash-verified against this code. Until the developer provides SHA256 proof that the reference output is byte-identical, this change cannot be merged under any LAW 22-governed deployment process.

The fix itself is technically sound. The test is excellent. Everything else is clean. This is a one-step blocker: **run the reference render, check the hash, provide the proof.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Prove LAW 22 compliance for v2f_2026-11-06 reference render
            | pipeline/pulse_transitions.py, lines 13–14 | models: 2/2
            | Re-render v2f_2026-11-06 with the current code. Compute SHA256
            | of the output file. Compare against the hash stored in
            | docs/frozen_refs/v2f_2026-11-06.sha256 (or equivalent registry).
            | If hashes match: append the verified hash + timestamp to the
            | audit trail and continue. If hashes differ: revert lines 13–14,
            | redesign settb insertion to be CONDITIONAL on a detected
            | timebase mismatch (do not apply unconditionally), re-render, and
            | re-verify before proceeding.

P1 HIGH     | Add automated LAW 22 regression test to CI/CD pipeline
            | tests/regression/test_v2f_reference_render.py (new file)
            | models: gemini-unique, endorsed 2/2
            | Implement a test that:
            |   1. Renders the v2f_2026-11-06 reference case end-to-end
            |   2. Computes SHA256 of the rendered output
            |   3. Asserts equality against the pinned hash in
            |      docs/frozen_refs/v2f_2026-11-06.sha256
            |   4. Fails the build — not warns, FAILS — on any deviation
            | Register this test in the main CI gate (not optional/slow lane).

P2 MEDIUM   | Correct feature/branch name and commit message
            | Branch name + commit message | models: 2/2
            | Rename to fix/xfade-timebase-mismatch or similar.
            | Commit message should cite D6 explicitly.
            | Open issues for D1–D5 if unaddressed.

VALIDATED (do NOT touch — all models confirmed excellent):
- pipeline/pulse_transitions.py lines 13–14: the settb fix itself is
  technically correct. Do not alter the fix logic, only verify its
  system-level impact via the P0 hash check.
- tests/test_dissolve_after_a_hard_cut_renders_frame_locked: this test
  is excellent (9/10 consensus). Do not modify it.
- M12 FAIL CLOSED, LAW 20/M2, ONSET/TAIL: all confirmed compliant.
  Do not touch any code in those paths.

After implementing:
- regression_test.sh must show zero FAILs
- docs/frozen_refs/v2f_2026-11-06.sha256 must exist and match
- CI pipeline must include test_v2f_reference_render in the blocking gate

git add -A && git commit -m "fix(xfade-timebase): post-audit pass — LAW 22 verified, CI regression gate added"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

# WINNER: Gemini — 2-Sentence Justification

Gemini delivered the highest-quality analysis across both cycles by proactively identifying the LAW 22 violation and scope mismatch in Cycle 1 — findings that GPT-4o only acknowledged *after* reading Gemini's output, and that Grok never produced at all. Gemini's analysis was deeper, more complete, and immediately actionable: it named the specific risk, explained the mechanism (filtergraph alteration → bitstream change → byte-identity violation), and issued a clear merge-blocking verdict before any other model reached that conclusion.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × confidence × actionability. Items marked **BLOCKER** must resolve before merge. Items marked **REQUIRED** must resolve before ship. Items marked **RECOMMENDED** are non-blocking but expected.

---

## PRIORITY 1 — BLOCKER (Hard stops on merge)

### P1-1: Verify LAW 22 Byte-Identity on v2f Reference Render
- **Source:** Gemini (Cycle 1, confirmed by GPT-4o Cycle 2, elevated to consensus U-1)
- **File:** `pipeline/pulse_transitions.py`, lines 13–14
- **Risk:** `settb=1/{FPS}` modifies the filtergraph for every dissolve, not only the failing edge case. Any filtergraph change can alter the encoded bitstream even when perceptually invisible, breaking the frozen reference contract.
- **Exact steps:**
  1. Checkout the commit under review on a clean build.
  2. Re-render the `v2f_2026-11-06` reference scene end-to-end.
  3. Compute `sha256sum` of the output file.
  4. Compare against the SHA-256 hash stored in the frozen reference manifest.
  5. **If match:** append the confirmed hash to the audit trail and proceed to P1-2.
  6. **If mismatch:** revert the diff OR redesign to apply `settb` conditionally (only when the prior segment was the output of a `concat` filter, not a raw input stream) OR obtain a formal written LAW 22 exemption from the designated authority before reopening merge.

---

### P1-2: Resolve Scope Mismatch — Branch Name vs. Actual Change
- **Source:** Gemini (Cycle 1), confirmed GPT-4o (Cycle 2)
- **File:** Commit message / branch `pulse-sentence-law`
- **Risk:** The branch claims to fix SENTENCE LAW, D1–D5 (sentence boundaries, clipped audio, warped avatars). The diff touches only the dissolve filtergraph (D6-adjacent). Merging under this branch name leaves D1–D5 unfixed but marked as addressed, creating a false compliance record.
- **Exact steps:**
  1. Update the PR description to explicitly state: *"This commit addresses only the xfade timebase crash (D6). D1–D5 remain open."*
  2. Create separate tracked issues for each of D1–D5 before closing this PR.
  3. Rename the branch or add a scoping note to the commit message so the audit trail is unambiguous.

---

## PRIORITY 2 — REQUIRED (Must resolve before ship)

### P2-1: Add a Conditional Guard to Limit `settb` Application Scope
- **Source:** Derived from P1-1 remediation path; both models implied this design
- **File:** `pipeline/pulse_transitions.py`, lines 10–17
- **Risk:** Applying `settb` unconditionally to every dissolve increases blast radius. If LAW 22 is currently passing only because the reference scene has no dissolve-after-concat pattern, a future scene could still regress.
- **Exact steps:**
  1. Introspect the prior segment's filter chain before inserting `settb`.
  2. Apply `settb=1/{FPS}` only when the prior segment's timebase is detectably not `1/{FPS}` (i.e., when it is the output of a prior `concat` or `amix` filter).
  3. Add a comment citing this audit finding and LAW 22 by name.
  4. Update the existing test to assert the conditional path is taken, not the unconditional one.

---

### P2-2: Extend Test Coverage to the Byte-Identity Case
- **Source:** Consensus gap — both models praised the existing test but neither noted the missing regression anchor
- **File:** Test suite, adjacent to `test_dissolve_after_a_hard_cut_renders_frame_locked`
- **Risk:** The existing test validates frame count, audio duration, and luma. It does not validate that re-rendering the same inputs produces a bit-identical file, which is what LAW 22 requires.
- **Exact steps:**
  1. Add `test_v2f_reference_renders_byte_identical` that renders the `v2f_2026-11-06` fixture twice in sequence and asserts `sha256(render_1) == sha256(render_2)`.
  2. Store the expected hash as a test constant, fail loudly if it changes.
  3. Gate this test in CI so it runs on every PR touching `pipeline/pulse_transitions.py`.

---

### P2-3: Verify SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, and CREDITS Compliance
- **Source:** Both models returned "Unverifiable" on these subsystems — consensus table confirms
- **Risk:** "Unverifiable" is not "Compliant." The diff does not touch these subsystems, but the branch name implies it should. If the PR is merged as a SENTENCE LAW fix, these subsystems inherit an unearned compliance stamp.
- **Exact steps:**
  1. For each subsystem (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, CREDITS): add an explicit note in the PR that this commit makes **no change** to those subsystems and their compliance status is unchanged from the prior audit.
  2. Do not mark these as newly verified in any compliance dashboard.

---

## PRIORITY 3 — RECOMMENDED (Non-blocking, expected before next audit cycle)

### P3-1: Document the `settb` Fix in the Filtergraph Architecture Notes
- **Source:** Actionability gap across both models
- **File:** `docs/filtergraph_architecture.md` (or equivalent)
- **Why:** Future engineers altering the `concat`/`xfade` pipeline will not know why `settb` is present and may remove it as apparently redundant. One paragraph citing the timebase mismatch root cause and linking to this audit prevents regression.

---

### P3-2: Track Grok Budget Failure as an Infrastructure Issue
- **Source:** Consensus report header — "1 failed — grok budget exceeded"
- **Risk:** A three-model quorum with one absent reduces audit confidence. The LAW 22 finding achieved consensus with only two models; a third might have caught something neither did.
- **Exact steps:**
  1. File an infra ticket to increase Grok's token budget for audit tasks or pre-summarize inputs before routing to Grok.
  2. Flag this audit cycle in the compliance log as "reduced quorum" so it cannot be cited as a full three-model sign-off.

---

## SUMMARY TABLE

| Priority | ID | Description | Blocker? | Owner Signal |
|---|---|---|---|---|
| 1 | P1-1 | LAW 22 SHA-256 verification | **YES** | Rendering infra |
| 1 | P1-2 | Scope mismatch — PR description + issue tracking | **YES** | PR author |
| 2 | P2-1 | Conditional `settb` guard | No | Pipeline engineer |
| 2 | P2-2 | Byte-identity regression test | No | Test author |
| 2 | P2-3 | Explicit "no change" stamps for unverifiable subsystems | No | Compliance lead |
| 3 | P3-1 | Filtergraph architecture documentation | No | Any |
| 3 | P3-2 | Grok budget infra ticket | No | Infra team |

**Current merge status: NOT READY. P1-1 and P1-2 must both close before the merge gate opens.**