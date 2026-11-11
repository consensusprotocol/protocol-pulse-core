# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 07:18
Models: gpt4o, gemini (+1 failed)

---

## SCORES
| Subsystem         | Gemini | GPT-4o | Grok        | Consensus |
|-------------------|--------|--------|-------------|-----------|
| Correctness       | 9/10   | 8/10   | N/A (failed)| **8.5/10** |
| Law Compliance    | 2/10   | 3/10   | N/A (failed)| **2.5/10** |
| Test Quality      | 9/10   | 7/10   | N/A (failed)| **8/10**  |
| Overall Readiness | 1/10   | 4/10   | N/A (failed)| **2/10**  |

> **Scoring note:** Grok-3 exceeded daily budget and produced no output. Consensus is derived from 2 of 3 models. Confidence is moderate; the two agreeing models converged on all major findings independently, which strengthens their signal despite the missing third voice.

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — Feature does not implement the laws it is named after
- **What:** The branch `pulse-sentence-law` contains zero code addressing `SENTENCE LAW`, `SNAP LIMIT`, `ONSET/TAIL`, or `CREDITS` law. It implements story deduplication (D6) and per-shot letterbox hardening (D5) only. Defects D1 (clipped words), D2/D3 (mid-sentence cuts), and D4 (warped avatars/credits) are entirely unaddressed.
- **File/line:** `editorial_select.py` (no sentence gate exists), `visual_check.py` (no onset/tail check exists), entire feature as a whole.
- **What to change:** This is both a governance and an implementation failure. See P0 items in the action plan. The feature must either (a) be renamed to accurately describe what was built, or (b) have the missing law implementations added before merge.

### U2 — Logging in `ask_letterbox` and `letterbox_check` is insufficient
- **What:** Neither `ask_letterbox` (lines 748–759) nor `letterbox_check` (lines 762–780) emit structured logs on retry attempts, per-frame results, per-model verdicts, or terminal failures. In production, a letterbox gate failure will be nearly impossible to triage without this data.
- **File/line:** `visual_check.py` lines 748–780.
- **What to change:** Add structured log entries — at minimum: (1) each retry attempt with exception type, (2) each per-frame, per-model verdict, (3) the final aggregated pass/fail decision with which frame/model triggered failure.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings by definition. No additional majority-only items emerged that were not already captured under unanimous findings. Both models are entirely aligned on the two issues above.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — Git/governance audit-trail poisoning (Gemini only)
- **What:** Gemini raised a meta-concern beyond the code itself: merging this branch under the name `pulse-sentence-law` permanently contaminates the git history. Future engineers reading `git log` or `git blame` will believe sentence law was implemented in this commit. This is a documentation and onboarding hazard that compounds over time.
- **Assessment:** **Implement.** This is not pedantry. Protocol Pulse's audit model depends on the commit history being a trustworthy record. A misleadingly named branch merged to main is a form of technical debt that costs more to unwind later than to correct now. Rename the branch before merge.
- **What to change:** Rename branch to `pulse-story-dedup-letterbox-v2` (or similar). Update all linked tickets to explicitly state D1–D4 remain open. Create a new feature branch stub `pulse-sentence-law` for the actual work.

### UI2 — No tests exist for Sentence Law, Snap Limit, or Onset/Tail (GPT-4o only)
- **What:** GPT-4o noted that given the feature's declared name, there is a complete absence of test fixtures or assertions verifying sentence boundary compliance.
- **Assessment:** **Implement when the actual law code is written.** This finding is correct but downstream of the larger problem: you cannot test law gates that do not exist. When the real `pulse-sentence-law` work begins, this finding becomes a P0 test requirement. File it now as a pre-condition for that future branch.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Severity of Test Quality score
- **Gemini:** 9/10 — the tests that *do* exist are excellent; story deduplication and letterbox tests are comprehensive.
- **GPT-4o:** 7/10 — penalizes the missing law-compliance tests.
- **Tiebreaker ruling:** **Both are correct from their frame of reference.** Gemini is right that the written tests are high quality. GPT-4o is right that the test suite is incomplete relative to the feature's stated scope. The consensus score of 8/10 reflects excellent execution on a partial scope. The action plan must track the missing tests separately.

### C2 — Overall Readiness score
- **Gemini:** 1/10.
- **GPT-4o:** 4/10.
- **Tiebreaker ruling:** **Gemini's framing is more correct.** A branch named `pulse-sentence-law` that does not implement any sentence law is not a minor gap — it is a fundamental scope failure. The consensus of 2/10 reflects that the implemented code is functional but the feature as declared is not deliverable. The higher GPT-4o score likely reflects that the implemented sub-features (deduplication, letterbox) are individually production-quality, which is true but does not change the verdict on the branch as a whole.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT touch)

1. **`_same_event_groups` union-find implementation** (`editorial_select.py` line 117): Deterministic, evidence-based grouping using shared video IDs, intersecting chunk IDs, and sequence-matched quotes. Both models praised this as the correct design choice over using an LLM for a critical grouping decision.

2. **`letterbox_check` fail-closed logic** (`visual_check.py` line 762–780): The pass condition `all(a == "no" for a in ans.values())` is a textbook `M12 FAIL CLOSED` implementation. Any "yes," `None`, or exception correctly triggers failure. Do not loosen this condition.

3. **`story_ledger.record_if_approved` conditions** (`story_ledger.py` line 256): The guard conditions ensuring only fully-passed, non-option, `auto`-mode runs are recorded in the ledger are precise and correct. This prevents manual curation or failed runs from poisoning the deduplication ledger.

4. **`_merge_event` exception handling** (`editorial_select.py` lines 144–191): Pooling verdicts, re-judging non-counted ones, and updating member decisions is handled robustly with appropriate exception boundaries.

5. **`shot_frames` midpoint + dissolve-avoidance logic** (`visual_check.py` line 727): The boundary calculation using `lo`/`hi` from adjacent segment times correctly avoids dissolve frames during letterbox sampling.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| **SENTENCE LAW** | ❌ NOT IMPLEMENTED | Zero code addresses sentence boundary enforcement. Named as the feature's primary purpose. |
| **SNAP LIMIT** | ❌ NOT IMPLEMENTED | No cut-snap boundary checking exists in the diff. |
| **ONSET / TAIL** | ❌ NOT IMPLEMENTED | No onset or tail padding enforcement added. |
| **CREDITS** | ❌ NOT IMPLEMENTED | No credits handling logic modified or added. |
| **SELECTION LOCK** | ✅ COMPLIANT | Evidence/verdicts used consistently; no recomputation of expected words post-lock. |
| **M12 FAIL CLOSED** | ✅ COMPLIANT (for implemented features) | Letterbox check and story ledger both fail closed on ambiguity or error. |
| **LAW 20 / M2** | ✅ COMPLIANT | Gate thresholds are constants; no loosening detected. |
| **LAW 22** | ✅ COMPLIANT | v2f reference path unaltered. |

**Determination:** Four of the eight tracked laws are unimplemented within the scope of this branch. This is not a compliance gap — it is a compliance void. The feature cannot claim sentence-law compliance.

---

## SECURITY CONSENSUS

Both models flagged no active security vulnerabilities in the implemented code. No secrets exposure, no injection paths, no privilege escalation. The fail-closed design of the letterbox check is specifically security-positive (errs toward rejection, not acceptance).

**One latent concern** (neither model named it explicitly but it follows from the architecture): the `story_ledger` deduplication database, if writable by an untrusted process, could be used to block legitimate stories by pre-registering their event IDs. This is worth a threat-model review before the ledger storage path is finalized. **Priority: P3 / investigate before scaling.**

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

1. **The feature does not implement what it is named after.** Both models identified this as the central failure. A world-class product has a governance layer that prevents features from reaching multi-model audit with a 100% scope mismatch between declared and actual work. The gap is not just in the code — it is in the planning and ticket-to-branch mapping process upstream.

2. **Production observability is absent for the letterbox gate.** Both models noted that `ask_letterbox` and `letterbox_check` produce no actionable logs. A world-class system would emit structured telemetry allowing an on-call engineer to answer within 60 seconds: "Which frame? Which model said yes? How many retries?" The current implementation requires re-running the pipeline with breakpoints to answer those questions.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Rename branch; do NOT merge as pulse-sentence-law          | Entire repo / git  | models: gemini+gpt4o | Merging this branch under its current name permanently falsifies the git history. The implemented code is story deduplication + letterbox hardening. Rename to pulse-story-dedup-letterbox-v2 or equivalent before merge.

P0 CRITICAL | Mark D1, D2/D3, D4 tickets as STILL OPEN; do not close     | Project tracker    | models: gemini+gpt4o | Clipped words, mid-sentence cuts, warped avatars/credits defects are unaddressed. Closing them against this branch would be a false remediation.

P0 CRITICAL | Create new feature branch stub: pulse-sentence-law (real)   | git                | models: gemini+gpt4o | The actual SENTENCE LAW, SNAP LIMIT, ONSET/TAIL, and CREDITS gate implementations must be tracked under a correctly-scoped branch. This branch should be opened immediately so the work is visible in the backlog.

P0 CRITICAL | Implement SENTENCE LAW gate                                 | editorial_select.py | models: gemini+gpt4o | If the intent is to merge this work as pulse-sentence-law, the gate must be built. If the intent is to rename, this moves to the new branch as a P0 there.

P0 CRITICAL | Implement SNAP LIMIT enforcement                            | editorial_select.py | models: gemini+gpt4o | Same scope note as above.

P0 CRITICAL | Implement ONSET / TAIL padding checks                       | editorial_select.py or visual_check.py | models: gemini+gpt4o | Same scope note as above.

P1 HIGH     | Add structured logging to ask_letterbox and letterbox_check | visual_check.py lines 748–780 | models: gemini+gpt4o | Log each retry with exception type, each per-frame per-model verdict, and the final pass/fail decision with the triggering frame/model identified.

P2 MEDIUM   | Add tests for SENTENCE LAW, SNAP LIMIT, ONSET/TAIL gates    | tests/             | models: gpt4o        | Once gate code exists, must-fail and control fixtures are required. Use the Nov 10 fixture pattern already established for story merging.

P3 LOW      | Threat-model the story_ledger write path                    | story_ledger.py line 256 | models: synthesizer  | Confirm the ledger file/DB is not writable by untrusted processes; a poisoned ledger could block legitimate stories.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The implemented code — story deduplication via union-find and per-shot letterbox hardening — is functionally correct, robustly tested, and architecturally sound for what it does. If this were a branch named `pulse-story-dedup-letterbox-v2`, it would be close to mergeable pending only the P1 logging improvement.

However, as `pulse-sentence-law`, this branch is blocked by a fundamental scope failure. It does not implement any of the four laws it is named after. Merging it would:
1. Falsify the git audit trail for the Protocol Pulse codebase.
2. Leave D1–D4 defects silently unaddressed while appearing resolved.
3. Prevent the actual sentence law work from being tracked correctly.

**Absolute final blocker:** The branch name and scope mismatch. This is a governance block, not a code block. The code that exists is good. The claim that it is `pulse-sentence-law` is not supportable.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Rename branch to pulse-story-dedup-letterbox-v2 before any merge.
  Action: git branch -m pulse-sentence-law pulse-story-dedup-letterbox-v2
  Then create a new tracking branch: git checkout -b pulse-sentence-law main

P0 CRITICAL | Update project tracker: mark D1, D2, D3, D4 as STILL OPEN.
  Do NOT close any sentence-law, onset/tail, or credits-related tickets
  against the renamed branch. Add a comment: "Addressed by: NOT THIS BRANCH."

P0 CRITICAL | In the new pulse-sentence-law branch, implement the SENTENCE LAW gate.
  File: editorial_select.py
  Gate must: verify no cut falls outside the locked sentence boundary,
  verify sentence boundaries are NOT recomputed after selection,
  fail closed (reject the candidate) if boundary data is missing or ambiguous.
  Reference PULSE_SENTENCE_LAW_GOSPEL.md for the exact boundary contract.

P0 CRITICAL | Implement SNAP LIMIT enforcement.
  File: editorial_select.py
  Gate must: verify no cut snaps beyond the allowed silence window.
  Fail closed on missing or ambiguous silence data.

P0 CRITICAL | Implement ONSET / TAIL padding checks.
  File: editorial_select.py or visual_check.py (per gospel guidance)
  Gate must: verify onset and tail padding meet minimum requirements.
  Fail closed if audio metadata is unavailable.

P1 HIGH | Add structured logging to ask_letterbox and letterbox_check.
  File: visual_check.py lines 748–780
  Add at minimum:
    - Log each retry attempt: include attempt number and exception type/message.
    - Log each per-frame, per-model verdict: frame index, model name, answer.
    - Log the final pass/fail: include which frame and model triggered failure
      if applicable, or confirm all-clear with count of frames checked.
  Use the existing project logger (do not introduce a new dependency).

P2 MEDIUM | Add must-fail and control test fixtures for SENTENCE LAW, SNAP LIMIT,
  and ONSET/TAIL gates once gate code is written.
  File: tests/ (follow the Nov 10 fixture pattern used for story merging)
  Must-fail: a candidate that violates each law individually must be rejected.
  Control: a clean candidate must pass all gates.

VALIDATED — do NOT touch these (all models confirmed excellent):
  - _same_event_groups union-find logic (editorial_select.py line 117):
    deterministic, evidence-based, correct. Do not introduce LLM calls here.
  - letterbox_check fail-closed condition (visual_check.py line 777):
    all(a == "no" for a in ans.values()) — do NOT loosen this.
  - story_ledger.record_if_approved guard conditions (story_ledger.py line 256):
    precise and correct — do not add new conditions that weaken the filter.
  - _merge_event exception handling (editorial_select.py lines 144–191):
    robust — do not remove exception boundaries.
  - shot_frames midpoint + dissolve-avoidance logic (visual_check.py line 727):
    correct — do not alter the lo/hi boundary calculation.

After implementing all P0 and P1 items:
  bash regression_test.sh   # must show zero FAILs

Then commit and push:
  git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — sentence/snap/onset gates + letterbox logging [consensus C2]"
  git push origin pulse-sentence-law
```

---

# WINNER DETERMINATION

WINNER: Gemini — Gemini identified the critical disconnect between the feature branch name (`pulse-sentence-law`) and its actual implementation in Cycle 1, catching the highest-severity finding (D1–D4 entirely unaddressed) before the cross-audit forced the issue. Its analysis was deeper, more structurally complete, and more actionable than GPT-4o's, which initially scored law compliance at 9/10 and only revised downward after Gemini's findings surfaced in Cycle 2.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — Blocking: Do not merge without these**

1. **Implement or rename the feature branch.** The branch `pulse-sentence-law` must either (a) add enforcement gates for `SENTENCE LAW`, `SNAP LIMIT`, `ONSET/TAIL`, and `CREDITS` law addressing defects D1–D4, or (b) be renamed to reflect what was actually built (story deduplication + letterbox hardening). Merging under the current name creates a false compliance record.

2. **Add `SENTENCE LAW` gate.** No code prevents cuts that cross sentence boundaries. Add a pre-selection gate in `editorial_select.py` that rejects any candidate whose cut points fall mid-sentence per the locked sentence index.

3. **Add `SNAP LIMIT` and `ONSET/TAIL` enforcement.** No code validates that audio onset and tail are within allowed silence margins. Add checks in `visual_check.py` or a dedicated module before a candidate is passed to editorial selection.

4. **Add `CREDITS` / warped-avatar guard (D4).** No gate detects letterboxed or aspect-ratio-distorted frames in credit sequences. Extend the per-shot letterbox logic already built in `visual_check.py` to also cover credit-roll frames explicitly.

---

**P1 — High: Implement in this sprint**

5. **Structured logging in `ask_letterbox` and `letterbox_check`.** Add per-retry, per-frame, and per-model structured log lines (file `visual_check.py`, lines 748–780). Without these, production failures are undebuggable. Log: model name, frame index, raw response, retry count, terminal verdict.

6. **Add tests for `SENTENCE LAW`, `SNAP LIMIT`, and `ONSET/TAIL` compliance.** The test suite covers story merging and letterbox failure (using Nov 10 fixture data) but contains zero tests verifying the laws the branch is named after. Add at least one positive and one negative fixture per law.

---

**P2 — Medium: Implement before next sprint closes**

7. **Test coverage for `ask_letterbox` retry exhaustion path.** The `None` return on retry exhaustion is untested. Add a fixture that simulates all retries failing and assert the caller treats it as a failure (fail-closed per M12).

8. **Validate `story_ledger.py` deduplication across run boundaries with an integration test.** Unit tests cover in-memory merging; no test verifies that a previously delivered event in a prior `auto` run is correctly suppressed in a subsequent run against a persistent ledger state.

---

**P3 — Low: Backlog**

9. **Document the gap between D1–D4 and this diff explicitly in the PR description.** Even if the rename or implementation happens, add a section to the PR body stating which defects remain open and in which future branch they will be addressed. This prevents future auditors from assuming all six defects were resolved.

10. **Consider consolidating the per-shot frame extraction and the contact-sheet path** into a single visual QA entry point to reduce divergence risk as `visual_check.py` grows.