# qwen3.8-27b (qwen/qwen3.8-27b) 30 s finish=stop usage in 11244 / out 2022 usd_reported=0.001965 usd~0.064 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0842
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the logic of the floor gate itself (score >= 3.0, SHA match). We all missed the **critical architectural flaw** identified by the integrator and highlighted in the C1 Consensus: the assumption that `package_pin.affirmed_verdict` was the *only* gate, or that the render's validate (`stand_alone.check_edl`) would automatically respect the pin's state.

The C1 Consensus correction is the most important finding: **The render's validate re-asks the scorer.** It does not read the pin's `scorer_verdict` or the `stand_alone_bar` mark. Therefore, a pin sealed with a 3.0 floor affirmation would be **HOLDed** (refused) by the render's validate because the render asks the scorer again at 3.5, and the scorer (being deterministic or near-deterministic) would likely return the same low score or a different one, failing the 3.5 bar.

My Cycle 1 output stated: *"The render's standard bar (SCORER_MIN = 3.5) remains the primary check... The floor is an additive exception."* This was **incorrect** in the context of the full system. The floor is *not* an additive exception to the render's validate; it is an exception to the *candidates path* pinning. If the render's validate is not also patched to accept the floor (the "integrator's half"), the system is broken: it will seal pins that it then refuses to render.

Mimo and Qwen also missed this in Cycle 1, but Qwen raised a P2 question about it ("If affirmed_verdict is also used by the final render validation..."). The C1 Consensus confirmed this was a real risk, not just a theoretical one.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma-4-31B-IT (Cycle 1):** Agreed with the logic checks (floor threshold, SHA restriction, seal integrity). **Disagree** with the conclusion that the render bar is "untouched" in a way that implies safety. The render bar is untouched in code, but the *system* is unsafe because the render validate doesn't know about the floor.
*   **Mimo-V2.6-Flash-RL (Cycle 1):** Agreed with the P3 findings on prefix matching (now fixed in Cycle 2 diff) and dead code. **Disagree** with the "PASS" on check (2) "The render's own bar and checks are untouched." While the code is untouched, the *behavior* is compromised because the render validate will reject floor-affirmed pins.
*   **Qwen3.8-27B (Cycle 1):** **Agree** with the P2 finding. Qwen correctly identified the ambiguity: "If package_pin is used for the final release pin... does that violate the 'render's own bar is 3.5' constraint?" This was the right question. The C1 Consensus answered it: Yes, it violates the system's integrity unless the integrator's half is landed.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P1] The "Integrator's Half" is Missing from this Diff.**
The C1 Consensus states: *"THE LANDING THEREFORE: both ends together or not at all... the integrator adds each verdict's full digest to its verdicts file in its half, and its validate compares the running gemma3:27b's digest exactly too."*
The current diff (`C2_STEP.diff`) only contains the **candidates path** changes (`package.py`, `package_pin.py`). It does **not** contain the changes to `stand_alone.check_edl` (the render validate).
*   If this diff is merged alone, the system will seal pins with `stand_alone_bar` marks.
*   When the render runs `stand_alone.check_edl`, it will re-ask the scorer for the clips that need asking (e.g., trimmed clips, conjunctions).
*   The render validate will apply the 3.5 bar.
*   The scorer will return the same low scores (e.g., 3.0).
*   The render validate will **refuse** the pin.
*   **Result:** A sealed package that cannot be rendered. This is a **P1** defect if the integrator's half is not landed simultaneously. The C1 Consensus explicitly says "both ends together or not at all." This diff is only one end.

**[P2] Digest Comparison Logic in `scorer_verdicts`.**
In `package.py` line 19: `v.get("digest") == PPN.STAND_ALONE_FLOOR_DIGEST`.
The test `test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on` (line 151) checks `for digest in (None, "f" * 64, "a418f5838eaf")`.
The constant `STAND_ALONE_FLOOR_DIGEST` is a full 64-char hex string.
The test uses `"a418f5838eaf"` (12 chars) as a "bare prefix" and expects it to fail.
The code uses `==`, so a prefix will fail. This is correct.
However, the comment in `package_pin.py` line 80 says `# gemma3:27b's digest`. The test file line 131 defines `DIGEST = "a418f5838eaf..."`.
The logic is sound: exact match required.

**[P3] `affirmed_render` Field.**
In `package.py` line 24, `affirmed_render` is set to `rule`.
In `package_pin.py` line 102, `affirmed_verdict` does **not** check `affirmed_render`. It only checks `v.get("affirmed") is True`.
This is correct because `affirmed` is `rule or floor`. If `floor` is true, `affirmed` is true. `affirmed_render` is just for audit.
Mimo's P3 in Cycle 1 about `affirmed_render` being dead code is still valid. It is written but not read by the pin check. It is likely read by the integrator's Telegram note. This is acceptable but should be documented.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Floor Logic** | Pass | Pass | Logic is correct: score >= 3.0, exact SHA, exact Digest. |
| **Render Bar Integrity** | Pass | **Fail** | The render validate (`stand_alone.check_edl`) is not updated in this diff. It will reject floor-affirmed pins. The system is broken if this diff is merged alone. |
| **Seal Integrity** | Pass | Pass | Mark is outside the seal. `package_sha256` unchanged. |
| **Tests** | Pass | Pass | Tests cover the candidates path logic correctly. They do **not** test the render validate path (because it's not in the diff). |

## 5. FINAL PRIORITY LIST

1.  **[P1] Missing Integrator's Half:** The diff only updates the candidates path. The render validate (`stand_alone.check_edl`) must also be updated to accept the `stand_alone_bar` mark or the floor logic, otherwise, sealed pins will be refused at render time. **This diff cannot be merged alone.** It must be landed with the integrator's changes to `stand_alone.py` (or wherever `check_edl` lives).
2.  **[P2] Documentation of `affirmed_render`:** Add a comment in `package_pin.py` or `package.py` explaining that `affirmed_render` is for audit/Telegram notes and is not used by the pin check.
3.  **[P3] Test Coverage for Render Validate:** Once the integrator's half is added, tests must verify that `stand_alone.check_edl` accepts a floor-affirmed pin.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Land the integrator's half (render validate update) simultaneously with this diff, or do not land this diff at all.**

## 7. PRODUCTION READY?

**No.**

**Condition:** This diff is only half of the required change. The render's validate function (`stand_alone.check_edl`) currently re-asks the scorer at 3.5 and does not read the pin's `stand_alone_bar` mark. If this diff is merged without the corresponding change to the render validate, the system will seal packages that it then refuses to render, causing a hard stop in the production pipeline. The C1 Consensus explicitly states "both ends together or not at all." This diff is only one end.

P1_OR_WORSE: 1