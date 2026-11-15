# qwen3.8-27b (qwen/qwen3.8-27b) 46 s finish=stop usage in 23930 / out 2514 usd_reported=0.002905 usd~0.110 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2131
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "consensus" voice) correctly identified that the `formats` seal integrity was sound and that the `version` guard did not break protected previews. However, I missed two specific edge-case behaviors that the other models surfaced or that the fixed code now reveals:

1.  **The `ROLE_RE` false-positive risk (Qwen P2):** I did not explicitly flag that `hosts?` and `anchors?` in `vo_fidelity.py` could match common verbs/nouns in financial contexts (e.g., "The event hosts 500 people"). The fixed code uses `canon_tokens` for comparison, which helps, but the *detection* regex is still broad. The test `test_words_that_only_contain_a_role_are_not_roles` covers "hosting" (gerund) but not "hosts" as a verb. This is a residual P2 risk.
2.  **The `formats_of` intersection logic nuance (Qwen P3):** I accepted the logic as correct but did not explicitly verify that `formats_of` returns `None` (both formats) if *no* segment is 16:9-only, which is the correct "intersection" behavior for a medley. The test `test_formats_of` confirms this, but my Cycle 1 analysis was less explicit about the "absent means both" invariant being preserved for old pins.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok P1 (Version Guard breaks LAW 22/Preview):** **DISAGREE.** As established in Cycle 1 consensus, `layout_block` and `clean_visual` are only called during the *new pin creation* path (`visual_for` -> `sealed` -> `to_pin`). They are not called during `check_preview_reference` or `regression.sh` re-validation of old pins. Old pins with `visual-1`/`visual-2` records are not re-run through the visual gate; their seals are recomputed via `pin_seal`, which does not invoke `layout_block`. The version guard is a *new pin* eligibility check, not a *re-validation* check. This is safe.
*   **Qwen P1 (Formats Seal Integrity):** **DISAGREE.** The `seal` function includes `formats` in the hash body *only if* `formats is not None`. If a pin is created with `formats: ["16x9"]`, the key is present in the body. If an attacker strips the key, `mp.get("formats")` returns `None`, and the key is *omitted* from the body. The resulting SHA256 will differ from the original (which included the key). The test `test_a_16x9_only_clip_seals_its_format_and_a_pin_without_one_as_before` explicitly verifies that `del dropped["moments_package"]["formats"]` breaks the seal. This is correct.
*   **Grok P2 (Hardcoded `RENDER_16X9_ONLY`):** **AGREE (P2).** It is a module-level constant. While the comment explains the intent, it is not configurable via env var. This is acceptable for a "smallest diff" but should be documented as a one-time flip.
*   **Grok P2 (In-place mutation in `tail_variant.py`):** **DISAGREE (Fixed).** The Cycle 1 code mutated `m["derived_from"]` in-place. The *fixed* code (line 126-129) uses `out.append(dict(m, derived_from={...}))`, creating a copy. The test `test_the_moment_itself_takes_its_earlier_storys_place` verifies `self.assertNotIn("derived_from", m)` (caller's record untouched). This is resolved.
*   **Qwen P2 (ROLE_RE False Positives):** **PARTIALLY AGREE (P2).** The regex is broad. The use of `canon_tokens` for comparison reduces false *negatives* (i.e., it correctly identifies when a role is stated), but false *positives* (flagging a verb as a role claim) remain possible. The test `test_words_that_only_contain_a_role_are_not_roles` covers "hosting" but not "hosts" as a verb. This is a minor residual risk.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **[P2] `ROLE_RE` does not exclude verb forms like "hosts" or "anchors" in common financial sentences.**
    *   *File:* `pipeline/vo_fidelity.py`, line 344-345.
    *   *Issue:* The regex `\b((?:co-?)?hosts?|...|anchors?|...)\b` will match "hosts" in "The event hosts 500 people" or "anchors" in "Bitcoin anchors the economy." The `canon_tokens` comparison will then check if the cited clip contains the canonical token "host" or "anchor." If the clip does not, it flags a `ROLE` violation. This is a false positive for common verbs.
    *   *Mitigation:* The test `test_words_that_only_contain_a_role_are_not_roles` covers "hosting" (gerund) but not "hosts" (verb). The orchestrator's ruling is about *nouns* (roles), not verbs. The regex should ideally be context-aware or exclude common verb usages, but this is hard with a simple regex.
    *   *Severity:* P2 (blocks valid content, but does not let bad content through).

2.  **[P3] `formats_of` returns `None` for empty segments, which is correct, but the docstring could be clearer.**
    *   *File:* `pipeline/package_pin.py`, line 24-31.
    *   *Issue:* The docstring says "a medley takes the intersection." The code returns `["16x9"]` if *any* segment is 16:9-only. This is correct for intersection (if any clip cannot be 9:16, the medley cannot be 9:16). The test `test_formats_of` confirms this. No change needed, but the docstring could explicitly state "if any segment is 16:9-only, the medley is 16:9-only."

3.  **[P3] `times()` edge case for very short clips.**
    *   *File:* `pipeline/visual_pin.py`, line 229-241.
    *   *Issue:* If `dur` is very small (e.g., 0.05s), `last` is 0.0. `t` starts at 1.0. The loop doesn't run. `ts` is `[0.0]`. Then `if last > 0` is false. Returns `[0.0]`. This is correct. The change from `last - 0.25` to `last - 0.01` ensures the last frame is included if it's within 10ms of the end. This is correct for the "1 frame a second" requirement.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `visual_pin.py` | P1 (Version Guard) | P2 (Hardcoded Flag) | Version guard is safe for new pins only. Hardcoded flag is a minor auditability issue. |
| `package_pin.py` | P1 (Formats Seal) | P3 (Docstring) | Formats seal integrity is correct. Stripping the key breaks the seal. |
| `vo_fidelity.py` | P3 (Ad-hoc Normalizer) | P2 (ROLE_RE False Positives) | The use of `canon_tokens` is good, but the regex is still broad for verbs. |
| `tail_variant.py` | P2 (In-place Mutation) | P3 (Resolved) | The fixed code uses a copy. The test verifies the caller's record is untouched. |
| `spotlight.py` | P3 (Prompt Complexity) | P3 (Prompt Complexity) | The prompt is complex but matches the ruling. LLM variance is a known risk. |
| `tests/` | P3 (Example-driven) | P3 (Example-driven) | The tests are thorough but not exhaustive on all role words/verb forms. |

## 5. FINAL PRIORITY LIST

1.  **[P2] `ROLE_RE` False Positives on Common Verbs**
    *   *File:* `pipeline/vo_fidelity.py`, line 344-345.
    *   *Action:* Consider adding a negative lookahead or a list of common verb contexts to exclude "hosts" and "anchors" when used as verbs. Alternatively, document this as a known limitation and rely on the orchestrator's review to catch false positives.

2.  **[P2] Hardcoded `RENDER_16X9_ONLY`**
    *   *File:* `pipeline/visual_pin.py`, line 167.
    *   *Action:* Add a comment or a config file entry to make it clear that this is a one-time flip. Consider using an environment variable for easier auditing.

3.  **[P3] `formats_of` Docstring Clarity**
    *   *File:* `pipeline/package_pin.py`, line 24-31.
    *   *Action:* Clarify the docstring to explicitly state the intersection logic.

4.  **[P3] Test Exhaustiveness for `ROLE_RE`**
    *   *File:* `tests/package/test_role_claims.py`.
    *   *Action:* Add tests for common verb forms like "hosts" and "anchors" to document the current behavior (false positive) or to verify the fix if implemented.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The most critical change is the **`formats` seal integrity** in `package_pin.py`. Ensuring that the presence/absence of the `formats` key changes the SHA256 hash is essential for the cryptographic integrity of the pin. The test `test_a_16x9_only_clip_seals_its_format_and_a_pin_without_one_as_before` correctly verifies this, and the code logic is sound. This change prevents a 16:9-only pin from being mutated into a "both formats" pin without breaking the seal.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1.  The `ROLE_RE` false positive risk on common verbs ("hosts", "anchors") must be documented or mitigated. If not mitigated, the orchestrator must be aware that valid financial sentences may be flagged as `ROLE` violations.
2.  The `RENDER_16X9_ONLY` flag must be flipped to `True` when the integrator's format-aware release lands. This is a one-time change and must be audited.
3.  The `version` guard in `layout_block` must be verified to not affect re-validation of old pins. The Cycle 1 consensus and the fixed code confirm this is safe, but a final check of `check_preview_reference` and `regression.sh` is recommended.

P1_OR_WORSE: 0