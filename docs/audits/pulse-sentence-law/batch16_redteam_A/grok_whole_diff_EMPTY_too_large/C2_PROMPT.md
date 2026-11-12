# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
No diff is present in the package. Nothing can be verified about function behavior, time/index handling, units, comparisons, exceptions, or state leakage.

**Q2: LAW COMPLIANCE**  
No diff lines exist, so every law (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-i, LAW 20/M2, M12, LAW 22) is marked UNCERTAIN. No evidence that cuts stay inside locked silence, that expected words are never recomputed, or that thresholds are unchanged.

**Q3: TESTS**  
No test files or diff lines are shown. Cannot confirm must-fail fixtures fail for the stated reason or that controls pass for the right reason. No assertions can be inspected for vacuous passes.

**Q4: VERDICT**  
- SEVERITY: BLOCKER | diff line: (none) | issue: no staged diff supplied | fix: provide the exact commit diff  
- SEVERITY: BLOCKER | diff line: (none) | issue: all laws and checks unverifiable | fix: supply the diff before review  

**NOT READY**

## GPT4O — CYCLE 1 OUTPUT
To provide a comprehensive review, I would need to see the actual code diff. However, since the code diff is not provided here, I will outline how to approach the review based on the questions you've asked and the laws specified.

### Q1: CORRECTNESS
- **Functionality**: Verify that each function performs as described in its docstring and adheres to the laws. Pay attention to:
  - **Time/Index Handling**: Ensure that time and index calculations are correct, especially in terms of units (seconds vs ms).
  - **Comparisons**: Check that comparisons are logical and correctly implemented.
  - **Exceptions**: Ensure that exceptions are handled properly and do not fail silently.
  - **State Management**: Verify that state does not leak between clips, which could affect subsequent operations.
  - **Data Handling**: Confirm that missing data or model failures do not result in a pass or incorrect operations.

### Q2: LAW COMPLIANCE
- **SENTENCE LAW**: Ensure clips start and end at sentence boundaries as defined, with no recomputation of expected words after selection.
- **SELECTION LOCK**: Verify that words in a clip are fixed at selection time and not altered later.
- **SNAP LIMIT**: Ensure cuts only move within allowed gaps and do not add/drop words.
- **NEIGHBOUR**: Confirm no audible part of neighboring words is included.
- **ONSET/TAIL**: Check that edge words retain at least 85% of their duration.
- **CREDITS**: Ensure avatars are correctly used and verified.
- **SIGN-OFF NAMES ALL**: Verify that all channels are named correctly in the sign-off.
- **EDGE WORDS WHOLE**: Ensure fades do not overlap edge words.
- **DISSENT IS RIGHT UNTIL DISPROVED**: Check that dissenting checks are appropriately handled.
- **PROTECTED PREVIEW**: Confirm the reference preview is reproduced accurately.
- **PUNCTUATED BEFORE READ**: Ensure transcripts are punctuated before being read.
- **CHANNELS FIRST**: Verify that story candidates are selected from channels first.
- **WRITTEN FORMS**: Ensure symbols are read as spoken words.
- **TEXT READ AS SPOKEN**: Confirm text is read as spoken before processing.
- **THE CLAIM IS THE EVENT**: Ensure the claim is used as the event for coverage judgment.
- **LAW 20 / M2**: Check that gate thresholds are constants and failures are hard stops.
- **M12 FAIL CLOSED**: Verify that missing data or failures result in rejection.
- **LAW 22**: Confirm that the v2f reference renders identically.
- **Smallest Diff**: Ensure no new renderers, compositors, or selectors are introduced.

### Q3: TESTS
- **Must-Fail Fixtures**: Ensure they fail for the correct reasons, demonstrating the issues they are meant to catch.
- **Control Tests**: Verify that they pass for the correct reasons, confirming the functionality works as intended.
- **Assertions**: Check for any assertions that could pass without actually verifying the intended condition.

### Q4: VERDICT
Without the actual code diff, I cannot provide specific defects or a final verdict. However, the process would involve listing each defect found during the review, categorizing them by severity, and suggesting fixes. The final verdict would be either "READY" if no critical issues are found, or "NOT READY" if there are significant problems that need addressing.

If you can provide the actual code diff, I can give a more detailed and specific review.

## GEMINI — CYCLE 1 OUTPUT
**PROTOCOL PULSE — CODE AUDIT**
**AI Model:** Gemini 2.5 Pro
**Feature:** pulse-sentence-law
**Review Start:** 2026-11-11 22:23:01 UTC

This review is based on the provided feature description, governing laws, and test plan. The code diff itself was not included in the review package. Therefore, this audit outlines the specific checks that must be performed on the code once it is provided. It cannot verify the implementation directly.

---

### Q1: CORRECTNESS

As the code is not available, I cannot verify the correctness of its implementation. However, based on the requirements, I have identified critical areas to inspect for common classes of defects:

*   **Time/Index Handling:** The code must be scrutinized for off-by-one errors in word/frame indices and for incorrect unit conversions (e.g., seconds from a library vs. milliseconds required by a law). For instance, SNAP LIMIT defines a window `previous word's offset .. the next word's onset`. The implementation must correctly handle floating-point timestamps and use inclusive/exclusive bounds as intended.
*   **State Management:** The pipeline processes multiple clips for multiple videos. I will verify that no state (e.g., audio levels, thresholds, transcript data) leaks from one clip to the next. Each gate's check must be performed on pristine data for the specific clip under review.
*   **Exception Handling & Fail-Closed (M12):** I will check every `try...except` block. A broad `except:` that returns a `PASS` or a default value that allows processing to continue would be a violation of M12. Any failure in a dependency (model call, file read, audio analysis) must propagate as a `FAIL` or `HOLD` for the item being processed. A function that can return `None` on failure must have its return value checked by the caller, and that check must lead to a non-passing state. For example, if punctuation restoration (L-e) fails, `transcript_store.acquire` must not return a passable record.

### Q2: LAW COMPLIANCE

This is a prospective compliance check. The code, when supplied, will be checked against these points:

*   **SENTENCE LAW:** **COMPLIANT (pending code)**. I will verify that the code identifies sentence boundaries *only* from punctuation present in the transcript record and does not infer them. The logic for finding the cut point must not have a minimum gap duration, as per DEC-10.
*   **SELECTION LOCK:** **COMPLIANT (pending code)**. I will trace the `selection_lock` data from `edl.json`. The code that verifies the first/last words of a cut clip must compare against these locked-in values, not against values re-computed from the final cut points.
*   **SNAP LIMIT:** **COMPLIANT (pending code)**. The code must define the cutting window precisely as `[word_before.end_time, word_after.start_time]`. I will confirm that the final cut point is mathematically guaranteed to be within this window and that no code path allows it to move outside this boundary.
*   **NEIGHBOUR:** **COMPLIANT (pending code)**. This is a complex check. I will need to see the audio processing code that: 1) calculates the "valley threshold" (`local speech - 12 dB`), 2) applies the fade, and 3) analyzes the post-fade audio to ensure it remains below the threshold. This check must happen on the final rendered audio frames corresponding to the neighbor's side of the cut.
*   **ONSET/TAIL:** **COMPLIANT (pending code)**. I will verify two distinct code paths: one that checks for `>= 80 ms` of sub-speech audio for file-initial and hook-initial onsets, and a separate one that checks the `>= 85 %` duration rule for all other edge words. The logic must not conflate these two rules.
*   **CREDITS:** **COMPLIANT (pending code)**. I will check the data source for the avatar images. It must be a direct link to the channel's registered avatar, not a thumbnail or other image. Gate G15's implementation will be reviewed to ensure it's comparing against the correct channel registry.
*   **L-a SIGN-OFF NAMES ALL:** **COMPLIANT (pending code)**. I will inspect `run_fresh.stage_voice` to ensure the check `spoken_channels == credit_rings.credit_channels(edl)` is strict and order-sensitive (hook first). The `G20` gate must use the same canonical channel names/aliases as the credit generation logic.
*   **L-b EDGE WORDS WHOLE:** **COMPLIANT (pending code)**. The implementation of `sentence_law.edge_fades` is critical. It must calculate the available gap and place the fade entirely within it, even if shortened. The `gate_g17_edges` implementation must compare the level of the edge word audio in the final render against the source, and the comparison must show a delta of less than 1 dB for every frame of the word itself.
*   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** **COMPLIANT (pending code)**. I will examine the control flow in `run_fresh.stage_gates`. There must be a specific conditional block that implements this override: `if G3_fail and G17c_pass and G16_pass: override_fail()`. The default path must be t

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:23
Models: grok, gpt4o, gemini

---

## SCORES

All three models received the same review package, which contained **no code diff**. Scores cannot be meaningfully extracted from functional analysis because no functional analysis was possible. The table below reflects each model's assessment of the review's own completability.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 Correctness | N/A (no diff) | N/A (no diff) | N/A (no diff) | **UNSCORED** |
| Q2 Law Compliance | N/A (no diff) | N/A (no diff) | N/A (no diff) | **UNSCORED** |
| Q3 Tests | N/A (no diff) | N/A (no diff) | N/A (no diff) | **UNSCORED** |
| Q4 Verdict | NOT READY | NOT READY | NOT READY | **NOT READY** |
| Review Usefulness | Prospective checklist (medium) | Generic outline (low) | Hard block (high precision) | **BLOCKER** |

> **Scoring note:** Numeric scores (1–10) are suppressed because all three models were reviewing an empty diff. Assigning scores would create false confidence. The only meaningful metric is the unanimous verdict: the review cannot proceed.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — NO CODE DIFF WAS SUPPLIED
**What it is:** The review package for `pulse-sentence-law` Cycle 1 was delivered without the actual commit diff. All three models independently identified this as the foundational blocker preventing any substantive audit.

**Which file/line:** The review package itself — the diff attachment or inline diff block.

**What to change:** Before any second pass or further synthesis is meaningful, the **exact staged commit diff** (`git diff --cached` or equivalent) must be included in the review package. The diff must show:
- Every modified file with full context lines
- New files in their entirety
- Deleted files clearly marked
- No diff-within-diff truncation

**Why unanimous:** Grok issued a hard BLOCKER. GPT-4o stated it could not provide specific defects. Gemini explicitly noted "The code diff itself was not included in the review package." Zero disagreement.

---

### U2 — ALL LAW COMPLIANCE CHECKS ARE UNVERIFIABLE
**What it is:** Because there is no diff, every law (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-i, LAW 20/M2, M12, LAW 22) is in an indeterminate state. No model could confirm or deny compliance.

**Which file/line:** Every file in the feature branch — unverifiable.

**What to change:** Supply the diff. Law compliance must be re-audited in Cycle 2 with real code present.

**Why unanimous:** Grok explicitly marked every law UNCERTAIN. GPT-4o listed each law as requiring verification. Gemini prefaced every law with "COMPLIANT (pending code)." All three reached the same conclusion through different language.

---

### U3 — ALL TESTS ARE UNVERIFIABLE
**What it is:** No test files, no test diff lines, and no test assertions were visible. No model could conf

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)
(No code files found — run after Claude Code session completes)

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
