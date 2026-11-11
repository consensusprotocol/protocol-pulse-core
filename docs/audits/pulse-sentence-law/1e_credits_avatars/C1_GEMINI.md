An audit of the `pulse-sentence-law` feature follows.

### Q1: CORRECTNESS

The provided diff focuses exclusively on fixing defect D4 (warped credit avatars) by overhauling the avatar management system. The code related to this goal is largely correct, but there are areas of concern.

-   **`pipeline/avatar_onboard.py`**: This new script provides a robust, two-step process for fetching and registering channel avatars.
    -   `avatar_url()` (lines 42-57) correctly uses `yt-dlp` to find the highest-resolution *square* channel avatar, and correctly raises an exception if none is found. This correctly prevents non-square images (like video thumbnails) from entering the pipeline at the source.
    -   `fetch_one()` (lines 59-71) includes a secondary check for squareness (`SQUARE_TOL`, line 65) before resizing and saving the image. This is a good redundant check.
    -   `cmd_register()` (lines 117-141) modifies `channels.json` using regular expressions. While the code is clever (e.g., iterating in reverse to keep string indices valid), this is a brittle approach. It is dependent on the specific formatting of the JSON file and could fail in unexpected ways. The final `json.loads(text)` check (line 136) is a necessary safety net but does not make the method robust.
-   **`pipeline/shoutout.py`**: The changes here correctly harden the rendering pipeline against incorrect avatars.
    -   The old, permissive `_find_avatar` function, which included on-demand fetching and placeholder generation (the likely cause of D4), has been completely removed.
    -   The new `_find_avatar` (lines 970-987) is strict. It only accepts avatars registered in `channels.json`, verifies the file exists, checks its hash against a stored prefix (line 984), and validates its dimensions.
    -   The new `validate_avatar` gate (lines 863-873) correctly enforces that avatars are square and meet a minimum size, raising a `ValueError` (a hard stop) if they do not.
-   **Fail-Closed Behavior**: The new logic is a strong example of the M12 FAIL CLOSED law. Any issue—missing registry entry, missing file, hash mismatch, or invalid image dimensions—results in a raised exception, stopping the pipeline. This correctly prevents a render with bad data.

### Q2: LAW COMPLIANCE

-   **SENTENCE LAW**: NOT ADDRESSED. The diff contains no code related to sentence boundaries, acoustics, or transcripts.
-   **SELECTION LOCK**: NOT ADDRESSED.
-   **SNAP LIMIT**: NOT ADDRESSED.
-   **ONSET/TAIL**: NOT ADDRESSED.
-   **CREDITS**: **COMPLIANT**. The new system is designed to comply with this law. `avatar_onboard.py` fetches real, square channel avatars, and the new gates in `shoutout.py` (lines 863-873, 970-987) ensure only these verified avatars are used, explicitly rejecting non-square images that could be video thumbnails.
-   **LAW 20 / M2**: **COMPLIANT**. The new avatar validation gate (`validate_avatar`) uses constants for its thresholds (`AVATAR_SQUARE_TOL`, `AVATAR_MIN_PX` on lines 852-853) and constitutes a hard stop by raising exceptions on failure.
-   **M12 FAIL CLOSED**: **COMPLIANT**. The new `_find_avatar` implementation (lines 970-987) is a textbook case of failing closed. It raises exceptions for missing data, missing files, and integrity check failures, preventing a pass.
-   **LAW 22**: **UNCERTAIN**. This law requires a frozen reference file (`v2f_2026-11-06`) to re-render byte-identically. The avatar fix will change the visual output of the credits scene. If the reference video includes channels whose avatars were previously warped (or missing), this fix will alter the render, likely violating this law. Without understanding how this law is handled during bug fixes that change output, compliance cannot be confirmed.
-   **Other Laws**: The changes appear to comply with "Smallest diff" (for the logic change) and "no new renderer".

### Q3: TESTS

The diff does not contain any test files. The feature description explicitly mentions `pipeline/test_pulse_20261110_mustfail.py`, which is intended to prove that the new gates catch the errors from the problematic run. Without this file, it is impossible to verify the central claim that the fix is proven on the faulty fixtures.

### Q4: VERDICT

The code in this diff successfully and robustly fixes the avatar-warping defect (D4). The new avatar pipeline is well-designed, secure, and adheres to the fail-closed principle. However, several significant issues prevent a "READY" verdict.

-   **HIGH** | N/A | Incomplete Scope | The feature is named `pulse-sentence-law` and its description covers a range of defects (D1-D6). This diff exclusively addresses the avatar issue (D4). There is a major disconnect between the stated scope and the provided code, and the most prominent part of the feature name ("sentence-law") is not implemented.
-   **HIGH** | N/A | Missing Tests | The test file (`test_pulse_20261110_mustfail.py`) that allegedly proves the fix works is not included in the diff. This is a critical omission, as proof of the fix is a stated requirement of the feature.
-   **MEDIUM** | `pipeline/avatar_onboard.py:117-141` | Brittle File Modification | `cmd_register` modifies `channels.json` with regular expressions. This is fragile and risks corrupting the file if its formatting changes. **Fix**: Refactor to parse the JSON into a Python object, modify the object, and serialize it back to the file.
-   **MEDIUM** | `pipeline/channels.json` | Hardcoded Absolute Paths | The `avatar_path` entries use absolute filesystem paths (e.g., `/home/ultron/...`). This hurts portability. **Fix**: Use paths relative to the project root or resolve them at runtime from a configured base path.
-   **LOW** | Law Compliance | Potential LAW 22 Violation | The fix will alter rendering output, which may conflict with the byte-identical requirement for the frozen reference. This needs clarification.

The core logic to fix the avatar problem is sound, but the review package is incomplete and contains architectural risks.

**VERDICT: NOT READY**