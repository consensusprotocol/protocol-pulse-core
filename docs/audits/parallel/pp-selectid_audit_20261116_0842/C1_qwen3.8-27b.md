# qwen3.8-27b (qwen/qwen3.8-27b) 66 s finish=stop usage in 9764 / out 2432 usd_reported=0.003126 usd~0.066 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 119 (1)) against the Governing Laws and the specific instructions.

### Analysis

**1. Compliance with Governing Laws**
*   **LAW 20 / M2 (Gate Thresholds):** The change introduces a "calibrated floor" of 3.0 for the *candidates path* (stand-alone scoring) while keeping the *render path* (validate) at 3.5. The code explicitly distinguishes between `affirmed_render` (the strict 3.5 rule) and `affirmed` (which can be true via the floor). The render's own validation logic (`stand_alone.check_edl`) is stated to be unchanged and is not touched in this diff. This complies with the law that gate thresholds are constants and failing gates are hard stops, provided the "floor" is a documented, calibrated exception for a specific sub-process (candidates) and does not weaken the final render gate. The prompt confirms "the render's own validate (3.5) is unchanged".
*   **L-j (Release Authorised on Bytes):** The `stand_alone_bar` mark is placed *outside* the seal in `to_pin`. This is correct because the seal (`package_sha256`) should reflect the core content, while metadata about *how* it was approved (the floor) is auxiliary. The test `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal` verifies that `package_sha256` remains identical whether the mark is present or not. This is a strong design choice for auditability without breaking byte-identity of the core package.
*   **M12 (Fail Closed):** The `affirmed_verdict` function in `package_pin.py` is strict. It requires `bar == "calibrated"`, `floor == STAND_ALONE_FLOOR`, `score >= STAND_ALONE_FLOOR`, and `scorer_sha` to match the specific measured code. If any of these are missing or wrong, it falls back to the standard `SCORER_MIN` (3.5) check. If the score is 2.9, it fails both. This is fail-closed.

**2. Specific Checks Requested**
*   **(1) Nothing under 3.0 or from another scorer code is ever affirmed:**
    *   In `package_pin.affirmed_verdict`: `on_floor` requires `v["score"] >= STAND_ALONE_FLOOR` (3.0) AND `str(v.get("scorer_sha") or "").startswith(STAND_ALONE_FLOOR_SCORER)`. If `scorer_sha` is different, `on_floor` is False. Then it checks `v["score"] >= SCORER_MIN` (3.5). So a score of 3.2 from a different scorer fails (3.2 < 3.5). A score of 2.9 from the correct scorer fails (2.9 < 3.0). Correct.
    *   In `package.scorer_verdicts`: The floor is only applied if `str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER)` and `v["score"] >= PPN.STAND_ALONE_FLOOR`. Correct.
*   **(2) The render's own bar and checks are untouched:**
    *   The diff modifies `scorer_verdicts` to *add* a floor affirmation, but it preserves `affirmed_render` which reflects the original rule (`rule`). The `rule` variable is computed based on the standard logic. The `affirmed` field is set to `rule or floor`. The downstream `stand_alone.check_edl` (render validate) is not in this diff and is stated to be unchanged. The `affirmed_verdict` in `package_pin` is used for pin validation. Does pin validation use the render bar or the candidate bar? The prompt says "the render's own validate (3.5) is unchanged and still checks every pin." However, `package_pin.affirmed_verdict` is the function being modified. If `affirmed_verdict` is used by the render's validate, then the render's bar *is* effectively lowered to 3.0 for pins that have the `bar: "calibrated"` mark.
    *   *Critical Check:* The prompt states: "the render's own validate (stand_alone.check_edl, all clips together, 3.5) still checks every pin at render". This implies `stand_alone.check_edl` does *not* use `package_pin.affirmed_verdict` or that `affirmed_verdict` is only used for the *candidates* path pinning. The diff shows `affirmed_verdict` in `package_pin.py`. If `package_pin` is used for the final release pin, and the final release pin allows 3.0, does that violate the "render's own bar is 3.5" constraint?
    *   The prompt clarifies: "the candidates path's calibrated floor... The render's own validate (3.5) is unchanged". This suggests two distinct paths. The `affirmed_verdict` in `package_pin` is likely used to verify that a *candidate* pin is valid for the *candidates* path. The final render gate is separate. The test `test_the_pin_check_accepts_a_floor_affirmation_only_whole` tests `package_pin.affirmed_verdict`. If this function is the *only* gate for pins, and it now accepts 3.0, is that a violation? The prompt says "the render's own validate... is unchanged". It does *not* say `package_pin.affirmed_verdict` is the render's validate. It says `stand_alone.check_edl` is. Therefore, as long as `stand_alone.check_edl` is not modified, the render bar is safe. The `package_pin` change is for the *candidates* path pinning. This seems consistent.
*   **(3) The mark is outside the seal:**
    *   `to_pin` adds `stand_alone_bar` to the dict *after* the seal is calculated? No, `to_pin` constructs the pin. The test `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal` asserts `marked["package_sha256"] == plain["package_sha256"]`. This proves the mark is not part of the hashed content. Correct.
*   **(4) The tests:**
    *   `test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on`: Checks that 3.0 is affirmed on the correct scorer, 2.9 is not, and 3.0 is not affirmed on a wrong scorer. Correct.
    *   `test_the_pin_check_accepts_a_floor_affirmation_only_whole`: Checks that missing `bar`, wrong `floor`, low `score`, wrong `sha`, or wrong `threshold` all result in `False`. Correct.
    *   `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal`: Checks the mark structure and seal integrity. Correct.

**3. Potential Issues**

*   **[P2] Ambiguity in `affirmed_verdict` usage:** The function `package_pin.affirmed_verdict` is modified to accept the floor. If this function is *also* used by the final render validation (contrary to the prompt's statement that `stand_alone.check_edl` is the render validate), it would weaken the final gate. The prompt explicitly states "the render's own validate (stand_alone.check_edl, all clips together, 3.5) still checks every pin at render". This implies `affirmed_verdict` is *not* the final render gate, or that the final render gate bypasses it. Given the prompt's explicit assurance, I will trust that the separation is maintained. However, the code in `package_pin.py` is a shared library. If any other part of the pipeline uses `affirmed_verdict` for a final decision, it might inadvertently accept 3.0. The prompt says "the render's own validate... is unchanged". I will flag this as a P2 to ensure `affirmed_verdict` is not used in the final `stand_alone.check_edl` path.
*   **[P3] Magic String in `scorer_verdicts`:** The check `str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER)` uses a prefix match. `STAND_ALONE_FLOOR_SCORER` is `"edd54964a5ab"`. If a future scorer has a sha starting with this, it would incorrectly apply the floor. However, SHAs are 64 hex chars. A 12-char prefix is reasonably unique, but a full match is safer. The test uses `SHA = "edd54964a5ab" + "0" * 52`. The code uses `startswith`. This is a minor risk.
*   **[P3] `affirmed_render` field:** The new field `affirmed_render` is added to the verdict dict. This is good for clarity.

**Conclusion:**
The code implements the RULING 119 (1) correctly according to the prompt's constraints. The separation between the candidates path (floor 3.0) and the render path (bar 3.5) is maintained by the logic in `scorer_verdicts` and the explicit statement that `stand_alone.check_edl` is unchanged. The pin mark is correctly placed outside the seal. The tests are comprehensive for the new logic.

One subtle point: In `package.scorer_verdicts`, the `floor` variable is calculated as:
`floor = not rule and str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER) and v["score"] >= PPN.STAND_ALONE_FLOOR`
If `rule` is True (score >= 3.5), `floor` is False. `affirmed` becomes `True or False` = `True`. `bar` is not set (or set to None/empty).
If `rule` is False (score < 3.5), `floor` is True only if conditions met. `affirmed` becomes `False or True` = `True`. `bar` is set to "calibrated".
This logic is sound.

The `affirmed_verdict` in `package_pin.py`:
`on_floor = v.get("bar") == "calibrated" and ...`
If `bar` is not "calibrated" (i.e., it was affirmed by the render rule), `on_floor` is False.
Then it checks `v["score"] >= SCORER_MIN` (3.5).
So, a pin with `affirmed: True` but `bar: None` (affirmed by render rule) must have `score >= 3.5`.
A pin with `affirmed: True` and `bar: "calibrated"` must have `score >= 3.0` and correct sha.
This is consistent.

I see no P0 or P1 issues.

P1_OR_WORSE: 0