# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 13:49
Models: gpt4o, gemini (+1 failed — Grok-3 budget exceeded)

---

## SCORES

| Subsystem                   | Gemini | GPT-4o | Grok   | Consensus |
|-----------------------------|--------|--------|--------|-----------|
| Correctness                 | 9/10   | 8/10   | N/A    | **8.5/10** |
| Law Compliance              | 2/10   | 6/10   | N/A    | **4/10**  |
| Test Coverage               | 2/10   | 3/10   | N/A    | **2/10**  |
| Implementation Completeness | 1/10   | 3/10   | N/A    | **2/10**  |

> **Scoring note:** Gemini's Cycle 2 scores are used (not Cycle 1), as they incorporated cross-model consensus. GPT-4o's Law Compliance score (6/10) is notably higher than Gemini's (2/10) due to scope disagreement resolved below. Grok-3 non-participation is logged — consensus is computed on 2 models only and confidence is accordingly reduced on split findings.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — `setparams=colorspace=bt709` fix is technically correct
- **File:** `pipeline/render_vertical.py`, line 14
- **What:** Adding `setparams=colorspace=bt709` to the `LETTERBOX_VF` filter chain correctly re-tags the video stream after `colorlevels` strips the colorspace metadata. This is the standard ffmpeg pattern for this known behavior.
- **Action:** Retain the fix. It is correct. Do not revert it.

### U2 — Tests are absent
- **File:** No test files were submitted with this diff
- **What:** Neither model could locate test files covering the color-space fix, the sentence law logic, or the v2f reference invariant. The feature description referenced test fixtures that were not provided.
- **Action:** A complete test suite is required before merge. See P1 in the action plan.

### U3 — Feature implementation is incomplete
- **File:** Entire feature scope (`pulse-sentence-law`)
- **What:** Both models independently concluded that the submitted diff — a single color-space tag fix — does not deliver the feature named `pulse-sentence-law`. Defects D1, D2, D3, D4, and D6 have no corresponding code in the diff. The submission addresses at most a partial aspect of D5.
- **Action:** The core feature must be implemented before this branch can be reviewed for merge.

---

## MAJORITY FINDINGS (2 of 2 models — implement unless compelling reason not to)

All findings above are unanimous with only 2 models available. The following are findings where both models converged but with differing severity assessments:

### M1 — LAW 22 potential violation (byte-identical re-rendering)
- **File:** `pipeline/render_vertical.py`, line 14
- **What:** Both models flagged this, though with differing confidence. Gemini rated it P0 CRITICAL. GPT-4o rated it P1 HIGH. The concern: if the frozen v2f reference asset was produced using the pre-fix `LETTERBOX_VF` (without `setparams`), re-rendering it after this change will produce a visually corrected but non-byte-identical output, violating LAW 22.
- **Severity determination:** Gemini's framing is correct. This is a system invariant ("MUST"), not a guideline. The severity is **P0** until it is confirmed that the v2f reference render path does not exercise `LETTERBOX_VF`, or until the reference asset is regenerated under controlled conditions and the law is explicitly re-satisfied.
- **Action:** Audit whether the v2f reference path calls `LETTERBOX_VF`. If yes, either (a) gate the `setparams` addition behind a flag that is off for reference renders, or (b) regenerate the v2f reference under the new filter and lock it, with an explicit LAW 22 re-attestation.

---

## UNIQUE INSIGHTS (only 1 model — evaluate carefully)

### G1 — Process failure / misleading scope (Gemini only)
- **What:** Gemini identified that committing a tangential rendering fix onto a branch named `pulse-sentence-law` indicates source control hygiene failure — either unrelated work was mixed into the branch, or the wrong commit was submitted for review.
- **Assessment:** **Implement (process action, not code action).** This is a valid and sharp observation. The color-space fix is legitimate work but belongs on a dedicated branch (e.g., `fix/letterbox-colorspace-bt709`). Mixing it into a feature branch with an unrelated name creates audit confusion, corrupts git history semantics, and makes future bisects unreliable. The fix should be cherry-picked to its own PR. This is not blocking for correctness but is blocking for process compliance.
- **Priority:** P2 MEDIUM

### G2 — GPT-4o raised "potential impact on existing workflows" (GPT-4o only)
- **What:** GPT-4o noted that workflows relying on the previous (buggy) color rendering behavior might be affected and that users should be notified.
- **Assessment:** **Investigate further.** This is worth checking but is unlikely to be a real concern — the previous behavior was a bug (incorrect BT.601 decoding of BT.709 content). No downstream system should be relying on incorrect color decoding as a feature. However, if any downstream QA automation does pixel-level comparison against previously rendered outputs, those baselines will need to be regenerated. Flag for QA lead.
- **Priority:** P2 MEDIUM (downstream QA baseline regeneration check)

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT 1 — LAW 22 severity: P0 (Gemini) vs. P1 (GPT-4o)

**Gemini:** P0 CRITICAL — byte-identical re-rendering is a MUST, violation is immediate blocker.  
**GPT-4o:** P1 HIGH — requires investigation, not necessarily a blocker until confirmed.

**Tiebreaker — Gemini is correct.** When a law uses mandatory language ("MUST") and the violation is *plausible* rather than merely hypothetical, the conservative posture is to treat it as blocking until it is affirmatively cleared. The cost of shipping a LAW 22 violation into production (silent reference drift, corrupted QA baseline, undetected regression) is far higher than the cost of an extra investigation step. Treat as P0 until cleared.

### CONFLICT 2 — Implementation Completeness score: 1/10 (Gemini) vs. 3/10 (GPT-4o)

**Gemini:** 1/10 — The submission fails to deliver on its core premise.  
**GPT-4o:** 3/10 — Partial credit for the D5 color-space partial fix.

**Tiebreaker — Gemini's framing is more useful for action.** A score of 3/10 implies meaningful partial completion. A score of 1/10 more accurately signals to the developer that this submission should not advance. For consensus scoring, 2/10 is used (midpoint), but the action posture matches Gemini: this is a near-total rework, not a gap-fill.

---

## VALIDATED STRENGTHS (all models confirm — do NOT change)

### V1 — `setparams=colorspace=bt709` line is technically correct
The specific ffmpeg filter syntax is correct, well-placed in the filter chain, and solves the documented colorspace-tag-drop behavior of `colorlevels`. Do not revert or alter this line during the second pass. The only action needed is conditional gating for the v2f path (see P0 M1).

### V2 — Explanatory comments on lines 11–13 are well-written
Both models noted the comments accurately describe the problem and the fix. Retain them verbatim.

### V3 — M12 FAIL CLOSED is not violated by this change
All models agreed: if the `setparams` syntax is malformed, ffmpeg will error, which correctly propagates as a render failure. No silent pass-on-failure path was introduced.

---

## LAW COMPLIANCE CONSENSUS

| Law              | Status                  | Determination |
|------------------|-------------------------|---------------|
| SENTENCE LAW     | **VIOLATED**            | Feature is named for this law; zero implementation exists in the diff. D1–D4, D6 unaddressed. |
| SELECTION LOCK   | Compliant               | No clip selection or word boundary logic touched. |
| SNAP LIMIT       | Compliant               | No cut points or timing logic touched. |
| NEIGHBOUR        | Compliant               | No audio boundary logic touched. |
| ONSET/TAIL       | Compliant               | No audio onset/tail logic touched. |
| CREDITS          | Compliant               | No credit rendering logic touched. |
| LAW 20 / M2      | Compliant               | No gate thresholds altered. |
| M12 FAIL CLOSED  | Compliant               | No silent failure path introduced. |
| LAW 22           | **POTENTIALLY VIOLATED** | `LETTERBOX_VF` change may break byte-identical re-render of v2f reference. Must be cleared before merge. |
| M1 (smallest diff) | Compliant             | Change is minimal; no new renderer introduced. |

**Net LAW compliance verdict: BLOCKED** on SENTENCE LAW (feature absent) and LAW 22 (potential violation uncleared).

---

## SECURITY CONSENSUS

Neither model flagged security issues specific to this diff. The change is confined to an ffmpeg filter string constant. No user input is interpolated into the filter string in this diff. No new network calls, file paths, or authentication paths are introduced.

**Security verdict: No new attack surface introduced. No action required.**

---

## WORLD-CLASS GAP CONSENSUS

Both models flagged these gaps as the distance between this submission and a production-quality feature delivery:

### WCG-1 — The feature is missing (both models)
A world-class delivery of `pulse-sentence-law` would include complete implementation of SENTENCE LAW enforcement across D1–D6, not a single rendering tag fix. The gap is not incremental — it is fundamental.

### WCG-2 — Tests are absent (both models)
A world-class delivery includes: (a) must-fail fixtures that fail for the right reason, (b) regression controls that pass, (c) specific coverage of the sentence boundary logic, (d) a v2f byte-identity verification test, and (e) three consecutive clean renders as specified in the feature description's own acceptance criteria.

### WCG-3 — LAW 22 reference asset lifecycle is unmanaged (both models)
A world-class system has an explicit, documented process for when the v2f reference is regenerated, who approves it, and how it is re-locked. This submission exposes that the process is either absent or was not consulted.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Implement the core `pulse-sentence-law` feature: sentence boundary detection and enforcement logic covering defects D1, D2, D3, D4, D6 | New/modified files TBD per gospel spec | Both | The diff contains none of the named feature. Zero sentence law logic exists. This is the entire point of the branch. |
| **P0 CRITICAL** | Audit v2f reference render path for `LETTERBOX_VF` usage; either gate `setparams` addition behind a reference-render flag, or regenerate v2f reference and re-attest LAW 22 compliance | `pipeline/render_vertical.py:14` + reference render path | Both | LAW 22 is a MUST. Plausible violation is treated as confirmed until cleared. Shipping this uncleared risks silent reference drift. |
| **P1 HIGH** | Provide complete test suite: must-fail fixtures, regression controls, sentence law unit tests, v2f byte-identity verification, three-consecutive-clean-render acceptance check | `pipeline/test_pulse_*.py` (per feature spec) | Both | Acceptance criteria in the feature's own description require this. No tests = no confidence in the fix or the feature. |
| **P2 MEDIUM** | Isolate the color-space fix into a separate branch and PR (`fix/letterbox-colorspace-bt709`), independent of `pulse-sentence-law` | Git history / branch management | Gemini | Mixing unrelated fixes into a feature branch corrupts history, complicates bisects, and obscures scope in future audits. Cherry-pick the fix to its own PR. |
| **P2 MEDIUM** | Audit downstream QA baselines for pixel-level comparison tests that may have been computed against pre-fix renders; regenerate any stale baselines | QA baseline assets / CI configuration | GPT-4o | The color behavior change, while a bug fix, may invalidate pixel-diff baselines silently. Confirm or rule out before merge. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY. Immediate rejection.**

This submission fails on two independent axes, either of which alone would be sufficient to block:

1. **The feature is not implemented.** A diff that fixes a color-space tag in a video filter string does not deliver `pulse-sentence-law`. Defects D1–D4 and D6 have no corresponding code. The submission cannot be approved against the feature's own acceptance criteria.

2. **A core protocol law is potentially violated.** LAW 22 (byte-identical v2f re-rendering) is a MUST. The submitted change modifies rendered output without evidence that the v2f reference path was considered or the reference asset was updated. This is uncleared at time of review.

**The color-space fix itself (line 14) is technically correct and should be retained.** The fix is not the problem. The problem is what surrounds it: a missing feature, a missing test suite, an uncleared law violation, and a branch scope that does not match its contents.

**Absolute final blocker:** Implement the SENTENCE LAW feature (D1–D6) and clear LAW 22 before requesting re-review.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement the core pulse-sentence-law feature: sentence boundary
              detection and enforcement logic covering defects D1, D2, D3, D4,
              D6 as specified in PULSE_SENTENCE_LAW_GOSPEL.md. The current diff
              contains none of this logic. This is the primary deliverable.
              | Files per gospel spec | models: both | The branch delivers zero
              of its named feature.

P0 CRITICAL | Audit the v2f reference render path for LETTERBOX_VF usage.
              If the path exercises LETTERBOX_VF, either:
              (a) gate the setparams=colorspace=bt709 addition behind a
                  reference-render flag so the reference path is unaffected, OR
              (b) regenerate the v2f reference asset under the new filter,
                  re-lock it, and add an explicit LAW 22 re-attestation comment.
              Do not leave this unresolved.
              | pipeline/render_vertical.py:14 + v2f reference render path
              | models: both | LAW 22 is a MUST; uncleared violation blocks merge.

P1 HIGH     | Provide a complete test suite including:
              - Must-fail fixtures that fail for the right reason (sentence law)
              - Regression controls that pass
              - Unit tests for all sentence boundary logic (D1–D6)
              - v2f byte-identity verification test
              - Three consecutive clean renders with no code edits between them
                (per feature acceptance criteria)
              | pipeline/test_pulse_*.py | models: both | No tests = no merge.

P2 MEDIUM   | Isolate the color-space fix into a separate branch
              fix/letterbox-colorspace-bt709 via cherry-pick. The fix is correct
              but belongs on its own PR with its own history entry.
              | Git / branch hygiene | model: gemini | Clean history requirement.

P2 MEDIUM   | Audit downstream QA pixel-diff baselines for renders computed
              before the colorspace fix. Regenerate any stale baselines and
              document which assets were updated.
              | QA baseline assets / CI config | model: gpt4o | Silent baseline
              drift risk from rendering behavior change.

VALIDATED (do NOT touch — both models confirmed excellent):
- pipeline/render_vertical.py line 14: setparams=colorspace=bt709 — the filter
  syntax is correct. Do not revert or alter this line, only gate it for the
  v2f path as described in P0 above.
- pipeline/render_vertical.py lines 11–13: explanatory comments are accurate
  and well-written. Retain verbatim.
- M12 FAIL CLOSED compliance: no silent pass-on-failure path exists in the
  current diff. Do not introduce one.

After implementing: regression_test.sh must show zero FAILs.
Verify three consecutive clean renders with no code edits between runs.
Confirm LAW 22 is explicitly cleared in a comment or attestation document.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini delivered the highest-quality analysis across both cycles by identifying the two most critical systemic failures (incomplete implementation scope and LAW 22 byte-identical re-rendering violation) that GPT-4o missed entirely in Cycle 1 and only acknowledged after Gemini surfaced them. Its findings were deeper, more actionable, and proved correct in Cycle 2 — earning higher consensus scores in every contested category.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list of what to implement, ranked by risk × impact.

---

## P0 — BLOCKING (Do not merge without resolving)

### P0-A: Implement the missing sentence law core logic
- **Why P0:** The feature is named `pulse-sentence-law` and targets defects D1–D6. The submitted diff addresses exactly one rendering side-effect (D5-adjacent color space issue) and contains **zero** sentence boundary enforcement logic. The feature is structurally absent.
- **Action:** Implement SENTENCE LAW enforcement across all affected subsystems. Audit D1–D6 individually and produce a code change for each. Do not close the feature branch until all six defects have corresponding implementation and test coverage.

### P0-B: Resolve LAW 22 byte-identical re-rendering violation
- **Why P0:** The `setparams=colorspace=bt709` fix is correct for forward renders but **breaks the frozen v2f reference invariant**. Any downstream system that re-renders a v2f asset will now produce a different byte sequence than the archived reference, silently corrupting integrity checks.
- **Action:** Before deploying the color-space fix to production, either (a) re-generate and re-freeze all v2f reference assets under the new filter chain, or (b) gate the new filter behind a version flag so the v2f path continues to use the old chain. Document whichever path is chosen in the LAW 22 compliance log.

---

## P1 — HIGH (Required before merge, non-blocking on each other)

### P1-A: Write tests for the `setparams` color-space fix
- **Why P1:** U2 was unanimous. No test file was submitted. Without a regression test, any future filter chain edit can silently re-introduce the BT.601 misinterpretation.
- **Action:** Add an integration test that renders a known clip through `reframe_letterbox`, extracts stream metadata via `ffprobe`, and asserts `color_space == bt709`. Test must run in CI.

### P1-B: Write tests for each D1–D6 sentence law defect
- **Why P1:** Once P0-A is implemented, each defect fix needs a corresponding test. Without these, the law compliance score (currently 4/10 consensus) cannot improve and regressions are undetectable.
- **Action:** One test per defect. Tests must assert law-compliant behavior at the boundary condition that originally caused the defect, not just the happy path.

### P1-C: Audit SELECTION LOCK and SNAP LIMIT interactions with new sentence boundaries
- **Why P1:** Sentence boundary changes propagate upstream into clip selection and cut-point snapping. Neither model fully traced this interaction chain. It was flagged as requiring further investigation.
- **Action:** Trace every callsite that consumes sentence boundary data and verify that SELECTION LOCK word-boundary invariants and SNAP LIMIT cut-point constraints are still satisfied under the new logic. Document findings in the PR.

---

## P2 — MEDIUM (Implement in same sprint, not merge-blocking)

### P2-A: Communicate workflow impact of color-space change to downstream consumers
- **Why P2:** GPT-4o raised this in Cycle 2 and it was not disputed. Any pipeline or player configured to expect the previous (implicit BT.601) behavior may render incorrectly after the fix.
- **Action:** Publish a migration note. Identify all downstream consumers of `reframe_letterbox` output. Confirm each one handles explicit `bt709` tagging correctly, or flag for remediation.

### P2-B: Add a LAW compliance checklist to the PR template
- **Why P2:** Both models had to manually reason through each law against the diff. This is error-prone and caused GPT-4o to miss the LAW 22 implication entirely in Cycle 1.
- **Action:** Add a mandatory PR checklist section: for each active law, the author must explicitly mark it as COMPLIANT, NOT APPLICABLE, or NEEDS REVIEW with a one-line justification. This converts implicit reasoning into auditable state.

---

## P3 — LOW (Backlog, track but do not block current sprint)

### P3-A: Document the `colorlevels` → colorspace tag stripping behavior
- **Why P3:** The root cause (ffmpeg drops colorspace metadata after `colorlevels`) is not documented anywhere in the codebase. The next engineer to touch the filter chain will not know this invariant exists.
- **Action:** Add a code comment block in `render_vertical.py` near `LETTERBOX_VF` explaining the ffmpeg behavior, the fix, and a link to the relevant ffmpeg issue or documentation. The comments added in the diff are a start but are insufficient for future maintainability.

### P3-B: Establish a Grok participation fallback protocol
- **Why P3:** Grok-3 exceeded budget and produced no output. The consensus was computed on 2 models with explicitly reduced confidence. Split findings (e.g., Law Compliance scored 2/10 vs. 6/10) could not be fully resolved.
- **Action:** Define a minimum-model-count threshold for consensus validity. If fewer than 3 models participate, either extend the audit window or escalate the split findings to a human reviewer before scores are finalized.

---

## SUMMARY TABLE

| Priority | Item | Owner | Merge Gate? |
|----------|------|-------|-------------|
| P0-A | Implement D1–D6 sentence law logic | Engineering | YES |
| P0-B | Resolve LAW 22 v2f byte-identity violation | Engineering | YES |
| P1-A | Test: `setparams` color-space regression | QA/Engineering | YES |
| P1-B | Tests: D1–D6 defect coverage | QA/Engineering | YES |
| P1-C | Audit SELECTION LOCK + SNAP LIMIT interactions | Engineering | YES |
| P2-A | Downstream consumer migration note | Engineering/PM | NO |
| P2-B | LAW compliance checklist in PR template | Engineering | NO |
| P3-A | Document `colorlevels` tag-stripping behavior | Engineering | NO |
| P3-B | Grok fallback protocol for future audits | Process | NO |