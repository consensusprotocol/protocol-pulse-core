# qwen3.8-27b (qwen/qwen3.8-27b) 54 s finish=stop usage in 10869 / out 1898 usd_reported=0.002852 usd~0.061 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0842
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic of the floor (3.0 threshold, SHA restriction) and the seal integrity. However, I missed the **critical architectural risk** that Qwen3.8-27B and the Integrator's Correction highlighted: the potential for `package_pin.affirmed_verdict` to be used in a context where it bypasses the render's strict 3.5 bar.

While the prompt states the render's `check_edl` is unchanged, the `affirmed_verdict` function in `package_pin.py` is the gatekeeper for *pins*. If a pin is created with a floor-affirmed verdict, and that pin is later validated by a system that relies *only* on `affirmed_verdict` (without re-running the full `check_edl`), the 3.0 floor would effectively lower the integrity gate for that specific pin. The Cycle 1 consensus clarified that the "landing" requires the integrator's half to also affirm at validate, but from a *code audit* perspective, `affirmed_verdict` now accepts a lower bar. This is a **design dependency** on the integrator's behavior, not a self-contained safety guarantee in this repo. I missed flagging this as a [P2] "Coupling Risk" in Cycle 1.

Mimo-V2.6-Flash-RL correctly identified the **prefix vs. exact match** issue for the scorer SHA. In Cycle 1, I noted the SHA restriction but did not explicitly flag that `startswith` on a 12-char prefix is weaker than `==` on a 64-char hash, even if collision risk is low. The Cycle 2 diff fixes this by using the full SHA in `STAND_ALONE_FLOOR_SCORER` and `==` comparison.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma-4-31B-IT:** Agrees with the core compliance. I agree with their assessment that the floor is additive and the render bar is untouched *in this diff*. However, I agree with Qwen's caution that "untouched" in the diff does not mean "untouched" in the system if `affirmed_verdict` is the sole gate.
*   **Mimo-V2.6-Flash-RL:** Agrees with the P3 findings on prefix matching and dead code (`affirmed_render`). I agree that `affirmed_render` is currently only read by tests, but it is valuable for audit trails, so I do not agree it should be removed, only documented.
*   **Qwen3.8-27B:** Agrees with the critical check on `affirmed_verdict` usage. I agree that if `affirmed_verdict` is used for final release validation, the floor lowers the bar. The prompt clarifies that `stand_alone.check_edl` is the final gate, but the code change in `package_pin` is a significant relaxation of the pin's internal consistency check.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] Digest Prefix Match Weakness:**
In `package_pin.py` (line 98) and `package.py` (line 19), the weights digest is checked with `str(v.get("digest") or "").startswith(PPN.STAND_ALONE_FLOOR_DIGEST)`. `STAND_ALONE_FLOOR_DIGEST` is `"a418f5838eaf"` (12 hex chars). This is a 48-bit prefix match. While the consensus notes the integrator provided no more of the digest, this is a weaker check than the scorer SHA (which is now exact). If the integrator's "digest" field is not a full Ollama digest but a truncated one, this is fine. If it is a full digest, a 12-char prefix is sufficient for uniqueness in practice, but `==` would be strictly safer if the full digest were available. Since the integrator only provided 12 chars, this is acceptable but worth noting.

**[P3] `affirmed_render` Field Visibility:**
The `affirmed_render` field is added to the verdict dict in `package.py` (line 24). It is not included in the `stand_alone_mark` output. This is correct, as the mark is for the *floor* affirmation. However, if a consumer of the pin wants to know *why* a clip was affirmed (render bar vs. floor), they must look at the `scorer_verdict` inside the segment, not the `stand_alone_bar` mark. This is consistent with the design but could be confusing.

**[P3] Test Coverage for `affirmed_render`:**
The test `test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on` asserts `idx["a"]["affirmed_render"]` is `False` and `idx["d"]["affirmed_render"]` is `True`. This is good. However, there is no test asserting that `affirmed_render` is *absent* or `None` for clips that are not floor-affirmed and not render-affirmed (e.g., score 2.9). In `package.py`, `affirmed_render` is always set to `rule` (the render's verdict). So for a 2.9 clip, `affirmed_render` is `False`. This is consistent.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Floor Logic** | Compliant | Compliant | Logic is sound. |
| **Scorer SHA Check** | Compliant | Improved | Changed from `startswith` to `==` with full SHA. |
| **Digest Check** | Not Assessed | [P2] | 12-char prefix match is weaker than exact, but constrained by integrator data. |
| **Render Bar Integrity** | Compliant | [P2] | `affirmed_verdict` now accepts 3.0. Relies on `check_edl` being the final gate. |
| **Seal Integrity** | Compliant | Compliant | Mark is outside seal. |
| **Tests** | Thorough | Thorough | Covers mutations and edge cases. |

## 5. FINAL PRIORITY LIST

*   **[P2] Coupling Risk in `affirmed_verdict`:** `package_pin.affirmed_verdict` now accepts scores >= 3.0 if floor conditions are met. If this function is ever used as the *sole* validation gate for a release (bypassing `stand_alone.check_edl`), the integrity bar is lowered. **Action:** Ensure documentation explicitly states that `affirmed_verdict` is a *pin consistency* check, not a *release integrity* check, and that `stand_alone.check_edl` remains the final gate.
*   **[P3] Digest Prefix Match:** `STAND_ALONE_FLOOR_DIGEST` is a 12-char prefix. If the integrator can provide the full Ollama digest, switch to `==`. If not, document that 12 chars is the agreed-upon uniqueness boundary.
*   **[P3] `affirmed_render` Documentation:** Add a comment in `package.py` explaining that `affirmed_render` is the render's own verdict, preserved for audit, and is *not* the final affirmation status (which is `affirmed`).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Ensure that the **render's `check_edl` is the only gate that can reject a pin at release time**, and that `package_pin.affirmed_verdict` is strictly a *pre-release consistency check* that does not override the render's 3.5 bar in the final validation pipeline.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  The integrator's "half" (the validate step) must **re-run** `stand_alone.check_edl` (or equivalent) at 3.5 for all clips, ignoring the `stand_alone_bar` mark, to ensure the render's bar is enforced.
2.  The `affirmed_verdict` function in `package_pin.py` must not be used as the *final* release gate without the render's `check_edl` also passing.
3.  The 12-char digest prefix must be confirmed as sufficient for uniqueness by the integrator.

P1_OR_WORSE: 0