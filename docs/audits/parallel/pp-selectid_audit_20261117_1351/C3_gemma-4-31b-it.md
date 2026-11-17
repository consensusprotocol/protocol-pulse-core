# gemma-4-31b-it (google/gemma-4-31b-it) 112 s finish=stop usage in 13393 / out 2093 usd_reported=0.000674 usd~0.072 (upper-bound price)

# PROTOCOL PULSE — CYCLE 3 CODE AUDIT
# Feature: pp-selectid-20261117_1351
# Review: Final confirmation of the Cycle 2 fix.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?
In the previous cycles, the consensus (led by GPT-OSS and Qwen) identified a **P1 defect**: `stand_plain` fell back to the raw string from `SA.opener`. Because `SA.opener` can return internal codes (e.g., `"fault starts_mid_thought"`), this violated Ruling 138 (3), which forbids codes in the final render/flags. I had initially viewed this as a safe fallback, but the other models correctly identified the contract violation.

## 2. WHERE DO I AGREE OR DISAGREE?
*   **`stand_plain` Fallback: Agree.** The fix implemented in Cycle 3 (Line 30) replaces the raw return with a fixed plain sentence: `"the clip scorer does not confirm it stands alone"`. This satisfies the "plain-words" requirement and eliminates the risk of leaking codes.
*   **E2E Hard-Failure Testing: Agree.** The new test suite `TestRuling141StandAloneSoft` now explicitly covers the "fail-closed" scenarios in `test_only_marked_clips_failing_only_the_opener_are_soft` (testing hook failure, topic failure, and unmarked clip failure) and the E2E flow in `test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass`.
*   **Positional Mapping: Agree.** As established in Cycle 2, the coupling between `labels()` and `segs` is a stable internal invariant of the `stand_alone_check` architecture.

## 3. NEW FINDINGS FROM THIS REVIEW
*   **[P3] Mutation Survivor (S3):** The `m["moment_id"] not in trims` guard in `stand_back` (Line 102) is not explicitly unit-tested. However, the logic is sound: if a moment has an affirmed trim, the trim is already added to the pool (Line 99). Bringing back the original as a flagged clip would be redundant. This is a low-risk survivor.
*   **Carry-in Prevention:** The addition of `m.pop("stand_soft", None)` (Line 94) correctly ensures that marks from previous failed builds do not leak into the current pass.

## 4. REVISED SCORES
The fix directly addresses the only remaining P1.

| Subsystem | Cycle 1 | Cycle 2 | Cycle 3 | Why changed |
| :--- | :--- | :--- | :--- | :--- |
| Logic | Pass | Pass | Pass | No change |
| Integration | Pass | Pass | Pass | No change |
| Tests | Pass | Pass | Pass | New tests cover the fix and hard-failure paths |

## 5. FINAL PRIORITY LIST
No P0, P1, or P2 findings.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The replacement of the raw `SA.opener` fallback in `stand_plain` with a fixed plain-word sentence ensures strict adherence to Ruling 138 (3) and prevents internal codes from reaching the integrator.

## 7. PRODUCTION READY?
Yes.

P1_OR_WORSE: 0