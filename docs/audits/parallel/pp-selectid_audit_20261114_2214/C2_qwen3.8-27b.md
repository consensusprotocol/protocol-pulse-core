# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 7170 / out 2095 usd_reported=0.001827 usd~0.053 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2214
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the consensus anchor) correctly identified that the "text mutation" P1 raised by GLM and Grok was a false positive, based on the architectural fact that `spotlight.pool` (Stage 1) runs *before* `build()`, and `m["text"]` is immutable within `build()`.

However, I missed two specific nuances that the other models highlighted, which I now validate:

1.  **GLM-5.3-FLASH** correctly noted that `alone_score(m)` is called **twice** per moment in the dictionary comprehension (line 9 of the diff). While functionally harmless if `alone_score` is a pure lookup, it is a code smell that suggests the implementation should cache the score or use a helper to ensure consistency and performance.
2.  **Grok-4.20** raised a valid [P2] concern regarding the **shape of the output** (`out["ruling_109"]` and modified stop reasons). While I dismissed this in the Cycle 1 consensus as "builder's record only," Grok correctly pointed out that if any downstream consumer (like `release_auth.py` or telemetry) performs strict schema validation or exact-match string comparisons on stop reasons, this change could break them. The Cycle 1 consensus assumed "no change" to gate rows, but the *reason strings* did change (from "cannot open cold" to "ruling 109"). This is a behavioral change in the *metadata*, even if the *gate logic* is sound.

## 2. WHERE DO YOU AGREE OR DISAGREE?

### GLM-5.3-FLASH
*   **[P1] Text Mutation / Score Change:** **DISAGREE.** GLM argued that a snapped span might change the text, invalidating the early score. This is **incorrect**. As established in Cycle 1, `spotlight.pool` (Stage 1) performs all snapping/trimming *before* `build()` is called. By the time `P.with_verdict` is called in `build()`, the text is final. The scorer's verdict is keyed to this final text. Therefore, the early check is safe.
*   **[P2] Double Call to `alone_score`:** **AGREE.** This is a valid [P3] nit. It works, but it's inefficient and slightly confusing.
*   **[P2] Malformed Rating:** **PARTIALLY AGREE.** GLM suggested adding a test for string/None ratings. The code `alone_score(m) < ALONE_MIN` would raise a `TypeError` if `alone_score` returned a string. However, `P.verdict_of` and the scorer contract (L-l) guarantee numeric or None. A `TypeError` would trigger M12 (Fail Closed), which is acceptable. No test is strictly *required* for this edge case if the upstream invariant is trusted, but it's good hygiene.

### GROK-4.20
*   **[P1] Early Stop Drops Sealable Moment:** **DISAGREE.** Grok repeated the "text mutation" fallacy. The text does not change. The score is fixed per text/scorer version. The early stop is a pure optimization that does not alter the final set of sealed moments.
*   **[P2] Output Shape / Release Auth:** **AGREE.** This is a legitimate [P2]. The change in stop reason strings ("ruling 109" vs. previous reasons) and the new `out["ruling_109"]` key could impact downstream systems that parse these fields. The Cycle 1 consensus was too hasty in dismissing this. It needs verification that `release_auth.py` and any logging/telemetry pipelines are agnostic to these specific string changes.
*   **[P2] No Regression Test for Low-Then-High:** **DISAGREE.** This scenario is impossible within a single `build()` call. The text is immutable. A "low-then-high" transition would require a new scorer version or a new build, which is handled by the next cycle.

### QWEN3.8-27B
*   **Logic Analysis:** **AGREE.** Qwen correctly identified that the logic is sound and that unscored moments proceed. It missed the output shape concern but correctly validated the core logic.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] Stop Reason String Change May Break Downstream Parsers
The diff changes the stop reason for low-ALONE moments from `"cannot open cold"` (or similar opener-rule reasons) to `"the ALONE scorer: {sc} (needs {ALONE_MIN:g}), a free gate before any paid verdict (ruling 109)"`.
*   **Risk:** If any external system (e.g., a dashboard, a log parser, or `release_auth.py`) matches on the *exact* string `"cannot open cold"` or checks for the absence of `"ruling 109"`, this change will break it.
*   **Mitigation:** Verify that all consumers of `out["moments"][mid]["out"]` are pattern-agnostic or updated to expect the new string. The Cycle 1 consensus stated "pin's gate rows are unchanged," but the *reason* is part of the row's metadata.

### [P3] Inefficient Double Evaluation of `alone_score`
Line 9: `low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}`
*   `alone_score(m)` is called twice for each moment in the condition and once for the value.
*   **Fix:** Use a helper or a list comprehension to compute the score once:
    ```python
    scored = [(m, alone_score(m)) for m in ms]
    low = {mid: sc for mid, sc in scored if sc is not None and sc < ALONE_MIN}
    ```
    This is a minor performance/clarity improvement.

### [P3] Test Name Clarity
The test `test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict` is descriptive but long. It correctly pins the behavior. No change needed, but note that the test relies on `calls.get("prescreen")` being populated by the mock. This is a valid test design.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Core Logic** | PASS | PASS | Confirmed safe. Text is immutable in `build()`. Early stop is a valid optimization. |
| **Output Contract** | PASS | **CONDITIONAL** | Cycle 1 dismissed the output shape change. Cycle 2 recognizes that stop reason strings and new keys are part of the contract. Needs downstream verification. |
| **Tests** | PASS | PASS | Tests correctly pin the new behavior. No regression risk identified. |
| **Performance** | N/A | **MINOR** | Double call to `alone_score` is inefficient but not critical. |

## 5. FINAL PRIORITY LIST

1.  **[P2] Verify Downstream Compatibility with New Stop Reasons and `out["ruling_109"]` Key.**
    *   **Action:** Check `release_auth.py`, `ATTESTATION.json` generation, and any logging/telemetry code to ensure they do not hard-code the old stop reason strings or fail on the new `ruling_109` key.
    *   **File:** `pipeline/spotlight.py` (lines 10-15), `tests/package/test_spotlight.py` (lines 31-33).

2.  **[P3] Optimize `alone_score` Evaluation.**
    *   **Action:** Refactor line 9 to avoid calling `alone_score(m)` multiple times.
    *   **File:** `pipeline/spotlight.py` (line 9).

3.  **[P3] Add Comment Clarifying Text Immutability.**
    *   **Action:** Add a comment in `build()` stating that `m["text"]` is final at this stage (post-`spotlight.pool`), justifying the safety of the early stop.
    *   **File:** `pipeline/spotlight.py` (near line 8).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify that no downstream system (release auth, telemetry, dashboards) depends on the exact string of the stop reason or the absence of the `ruling_109` key, as this change alters the metadata contract even if the gate logic is sound.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Downstream Verification:** Confirm that `release_auth.py` and any log parsers are agnostic to the new stop reason string `"ruling 109"` and the new `out["ruling_109"]` key. If they are not, update them or revert the reason string to a stable identifier.
2.  **Code Hygiene:** Refactor the double call to `alone_score` (optional but recommended).

If these conditions are met, the change is safe, correct, and a valid optimization. The core logic is sound, and the tests adequately pin the behavior.

P1_OR_WORSE: 0