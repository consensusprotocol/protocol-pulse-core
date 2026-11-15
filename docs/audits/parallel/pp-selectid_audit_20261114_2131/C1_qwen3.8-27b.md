# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 23346 / out 1879 usd_reported=0.004424 usd~0.098 (upper-bound price)

I have reviewed the code changes against the Governing Laws and the specific questions posed. Here is the audit.

### Findings

**1. [P1] `formats` Seal Integrity Violation (L-j / LAW 20)**
In `pipeline/package_pin.py`, the `seal` function includes `formats` in the hash body *only* if `formats is not None` (lines 43-44). However, `pin_seal` (lines 48-54) passes `formats=mp.get("formats")`.
*   **The Defect:** If a pin is created with `formats: ["16x9"]`, the seal includes it. If an attacker or a bug strips the `formats` key from the `moments_package` JSON before verification, `mp.get("formats")` returns `None`. The `seal` function then omits `formats` from the hash body. Because the rest of the body (segments, vo, etc.) is identical, the SHA256 hash will **match** the original seal.
*   **Consequence:** A 16:9-only pin can be mutated into a "both formats" pin (by deleting the key) without breaking the cryptographic seal. This violates **L-j** ("all release gates passed... on exactly the bytes that are sent") and **LAW 20** (gate thresholds/integrity). The test `test_formats.py` (line 411-413) claims to test this ("stripping it breaks the seal"), but based on the code logic provided, it would **fail** to detect the mutation because the hash would remain valid.
*   **Fix:** The `seal` function must always include the `formats` key in the hash body, defaulting to `None` or `[]` if absent, so that the presence/absence of the key changes the hash. Alternatively, `pin_seal` must verify that if `formats` is expected (based on segment visuals), it is present, and raise an error if missing, rather than relying on the hash to catch the omission.

**2. [P2] `ROLE_RE` False Positives on Common Verbs**
In `pipeline/vo_fidelity.py`, `ROLE_RE` includes `hosts?` and `anchors?` (line 338).
*   **The Defect:** The regex `\b((?:co-?)?hosts?|...|anchors?|...)\b` will match the verb "hosts" in sentences like "The event **hosts** 500 people" or "Bitcoin **anchors** the economy." It will also match "anchor" in "The **anchor** of the portfolio."
*   **Consequence:** The `ROLE` gate will flag these sentences as violations unless the cited clip explicitly contains the word "host" or "anchor" as a noun referring to a person. This creates a high false-positive rate for common financial/tech vocabulary, potentially blocking valid captions/titles.
*   **Fix:** The regex should be more specific to noun usage or context, or the check should verify that the role word is used as a noun (e.g., preceded by an article or determiner, or not followed by a verb object). Given the "Fail Closed" law, this is a P2 because it blocks valid content, but it doesn't let bad content through.

**3. [P3] `RENDER_16X9_ONLY` Hardcoded Flag**
In `pipeline/visual_pin.py`, `RENDER_16X9_ONLY = False` is a module-level constant (line 166).
*   **The Defect:** This flag controls whether 16:9-only clips are held or allowed. It is not configurable via environment variable or config file.
*   **Consequence:** When the integrator's format-aware release lands, a code change is required to flip this flag. This is acceptable for a "smallest diff" approach but should be documented clearly. The comment says "Flipped on its word... in one audited change," which is compliant.

**4. [P3] `times()` Edge Case**
In `pipeline/visual_pin.py`, `times()` (line 228) uses `while t < last - 0.01`.
*   **The Defect:** If `dur` is very small (e.g., 0.05s), `last` is 0.0. `t` starts at 1.0. The loop doesn't run. `ts` is `[0.0]`. Then `if last > 0` is false. Returns `[0.0]`. This is correct.
*   **Observation:** The change from `last - 0.25` to `last - 0.01` ensures the last frame is included if it's within 10ms of the end. This is correct for the "1 frame a second" requirement.

**5. [P3] `formats_of` Intersection Logic**
In `pipeline/package_pin.py`, `formats_of` (line 24) returns `["16x9"]` if *any* segment has `formats == ["16x9"]`.
*   **Observation:** The docstring says "a medley takes the intersection." If one clip is 16:9-only and another is both, the intersection is 16:9-only. The code returns `["16x9"]` if *any* is 16:9-only. This is correct for the intersection logic (if any clip *cannot* be 9:16, the medley cannot be 9:16).

### Answers to Specific Questions

1.  **Can a 16:9-only clip be sealed while `RENDER_16X9_ONLY` is False?**
    **No.** `layout_block` in `visual_pin.py` (line 307) checks `if formats(rec) and not RENDER_16X9_ONLY:` and returns a block reason. This prevents the clip from being eligible, so it cannot be sealed.

2.  **Can the ROLE rule pass a role no cited clip states, or refuse a sentence with no role word?**
    **No / No.**
    *   If a role is not in the cited clip's words, `bad` will be non-empty, and `V("ROLE", ...)` is called. It fails.
    *   If a sentence has no role word, `ROLE_RE.findall` returns empty, `roles` is empty, and the check is skipped. It passes.

3.  **Does "formats" change any existing pin's recompute?**
    **No.** `formats_of` returns `None` if no segment has `formats == ["16x9"]`. `seal` only adds `formats` to the body if it is not `None`. Existing pins do not have `formats` in their segments, so `formats` is `None`, and the hash body is unchanged.

4.  **Can a reseal directive create a second spotlight for a channel's day?**
    **No.** `tail_variant.py` (line 124) handles the `reseal` directive by setting `derived_from` and `continue`ing, so no variant is created. `spotlight.day_taken` (referenced in tests) is updated to allow the reseal to take the place of the *specific* `alternative_to` story, but not to create a second spotlight for the day. The test `test_ruling_104.py` (line 544-546) verifies this.

5.  **Do the tests pin each piece?**
    **Mostly, but the `formats` seal test is flawed.**
    *   `test_formats.py` (line 411-413) attempts to verify that stripping `formats` breaks the seal. However, due to the P1 finding, the seal does *not* break. The test would fail if run against the current code, or if it passes, it indicates the code is different from what is shown. Assuming the code is as shown, the test is incorrect or the code is buggy.
    *   Other tests (`test_role_claims`, `test_visual_pin`, `test_ruling_104`) appear to correctly pin the behavior.

### Summary

The most critical issue is the **P1** finding regarding the `formats` seal integrity. The current implementation allows a 16:9-only pin to be mutated into a both-formats pin without breaking the hash, which violates the core security and integrity laws (L-j, LAW 20). This must be fixed before merge.

P1_OR_WORSE: 1