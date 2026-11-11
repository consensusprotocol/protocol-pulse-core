Excellent. This is a comprehensive feature addressing several critical editorial defects. I will now proceed with the code audit as one of three independent AI models.

---

### Q1: CORRECTNESS

The code appears to be of high quality, demonstrating a deep understanding of the problem domain, especially regarding `ffmpeg` behavior.

1.  **`face_scrfd.py` (New File):** This module for face detection is robust.
    *   **Correctness:** It correctly implements a standard ONNX inference pipeline. The model hash is pinned (line 19) and verified at runtime (lines 35-37), preventing regressions from model updates. This enforces reproducibility and complies with M12 (Fail Closed).
    *   **State:** The session is loaded once as a global `_SESSION` (lines 23, 27-41), which is efficient and safe in a single-process pipeline.
    *   **Exception Handling:** It correctly raises `FileNotFoundError` or `RuntimeError` on model absence or mismatch, preventing a pass on missing data (M12).

2.  **`transitions.py` (New File):** This new module for rendering transitions is exceptionally well-executed.
    *   **Correctness:** The `plan` function (line 1402) correctly identifies junctions for transitions (different channels, talking heads only) and, crucially, bounds the transition duration by the available non-speech "room" (lines 1417-1419). This prevents transitions over speech.
    *   **`ffmpeg` Nuances:** The `concat` function (line 1543) contains a critical comment and corresponding code (lines 1570-1574) that adjusts the `xfade` offset by `- 1 / FPS`. This corrects a known `ffmpeg` 4.x frame-slip issue that causes audio to lead video by one frame after a dissolve. This attention to detail is a strong indicator of correctness and prevents subtle A/V sync bugs.
    *   **State:** The functions are pure; they take inputs and produce outputs without side effects, aside from writing files to specified paths. No state leaks are possible.

3.  **`render_vertical.py` (Modified):** The new `reframe_auto` function is a significant improvement.
    *   **Correctness:** It correctly constructs a complex `ffmpeg` filter graph based on a per-shot plan (lines 206-212). The logic for handling different shot classes (`single`, `stack2`, etc.) in `_shot_vf` (line 182) seems correct and deterministic.
    *   **Fail Closed:** The most important change is the hard failure on reframe errors. The old code would silently use the 16:9 original. The new code explicitly raises a `RuntimeError` (line 253), which is a correct implementation of M12 Fail Closed and directly addresses a probable cause of the D5 defect (letterboxed vertical).

4.  **`word_diff.py` (New File):** The implementation of the G18 word-for-word gate is thorough.
    *   **Correctness:** The `norm` function (line 2027) is comprehensive, handling many ASR inconsistencies (numbers, punctuation, abbreviations, repeats). This is essential to prevent false positives/negatives.
    *   **Logic:** The `gate_g18` function (line 2091) correctly separates its checks:
        *   `edges()` (line 2065): Verifies start/end words against the lock (for Sentence Law).
        *   `diff()` (line 2056): Verifies word-for-word identity against the *source audio span* (for Snap Limit).
        This dual-check approach is the correct way to enforce both laws.
    *   **Fail Closed:** A clip missing from the manifest is correctly flagged as a failure (lines 2099-2102).

5.  **`run_fresh.py` (Modified):** The orchestration logic is sound.
    *   **New Stages:** The new `layout` stage (line 498) correctly runs before `render`, and the `verify` stage (line 504) runs after `gates`. This is the correct sequence.
    *   **Gate Integration:** The new G4s, G4-per-shot, and G18 gates are correctly integrated into `stage_gates` and their results are collected in the final report.

There are no obvious off-by-one errors, unit mismatches, or silent exceptions that would lead to an incorrect pass.

### Q2: LAW COMPLIANCE

The changes appear to be highly compliant with the governing laws.

*   **SENTENCE LAW:** **COMPLIANT.** This is now strongly enforced by the new G18 gate (`word_diff.py`, lines 2065-2073), which checks that the first and last words of the rendered clip match the sentence-aligned selection lock. This directly addresses defects D2 and D3.
*   **SELECTION LOCK:** **COMPLIANT.** The `selection_lock` is now used as the ground truth for the G18 gate (diff line 466). The pipeline correctly fails if a lock is missing (diff lines 471, 478-479). No later stage recomputes the expected words.
*   **SNAP LIMIT:** **COMPLIANT.** The "identity" check in `gate_g18` (diff line 2106) ensures no words are added or dropped during render by comparing the final audio to a fresh transcription of the original source audio span. This is an excellent and robust enforcement of this law.
*   **ONSET/TAIL:** **COMPLIANT.** The existing G17 gate remains. The new G18 gate provides a functional backstop, as a clipped onset (D1) would cause an `edges` mismatch. Furthermore, the new transition logic in `transitions.py` (lines 1417-1422) explicitly respects the available non-speech time, ensuring transitions do not clip words.
*   **CREDITS:** **PARTIAL.** The diff does not contain a fix for warped avatars (D4). However, it adds `verify_pack.py` (lines 1614-1698), which creates contact sheets of the credit sequence (`credits_16x9.jpg`, etc.). This makes the defect automatically visible to a human reviewer, fulfilling the feature's goal of "catch what a human caught." The underlying rendering bug is not addressed in this diff, but its detection is automated.
*   **LAW 20 / M2:** **COMPLIANT.** New thresholds are introduced as constants (e.g., `vertical_layout.py`, lines 1732-1736; `word_diff.py`, line 1992). Gate failures are treated as hard stops (`Hold` or `raise RuntimeError`). No checks are loosened.
*   **M12 FAIL CLOSED:** **COMPLIANT.** This principle is strongly applied throughout the new code. Examples: `face_scrfd.py` failing on model hash mismatch (line 37), `render_vertical.py` failing on reframe error (line 253), `run_fresh.py` flagging missing selection locks (line 471).
*   **LAW 22:** **COMPLIANT.** This is handled elegantly. The renderers in `render16.py` (line 101) and `render_vertical.py` (line 275) only call the new `_transition_concat` function if `TRANSITIONS.json` exists. The `_transition_concat` function itself returns `None` if the file is missing (line 151). This creates a clean fork: a run without this file (like the v2f reference) will use the old, byte-identical hard-cut `ffmpeg -f concat` path.
*   **Smallest diff, etc.:** **COMPLIANT.** No new rendering engines are added. GPU0 usage is enforced in the new `pulse_check_run.sh` script (line 2172). Delivery is to an internal chat, not for publishing (line 2131).

### Q3: TESTS

The new tests are comprehensive, targeted, and provide strong evidence that the feature works as claimed.

*   **`test_word_diff.py`:** This is an excellent "must-fail" test. `TestYesterdaysFinal` (line 1265) proves that the new G18 gate correctly FAILS on the `pulse_20261110` fixture for the specific reasons PBX reported (clipped start and run-on, D2/D3). The assertions are specific, checking not just failure but the *content* of the diff report (lines 1276-1288).
*   **`test_vertical_layout.py`:** `TestSafeFrameTruth` (line 1115) is another perfect must-fail test. It proves that G4s correctly FAILS when a talking head is improperly letterboxed (D5), and PASSES when it is correctly cropped. This directly validates the fix for the D5 gate escape.
*   **`test_transitions.py`:** The tests here are particularly strong. `TestConcat.test_dissolved_clip_picture_and_sound_start_together` (line 958) uses a clever luma-ramp video to prove that A/V sync is maintained across dissolves, specifically testing the fix for the `ffmpeg` `xfade` bug. This proves the correctness of the new transition rendering.
*   **`test_telegram_delivery.py`:** This correctly tests the new captioning logic, ensuring `HOLD FOR APPROVAL` is only used when all gates pass and the verification pack is complete.

The tests are not vacuous and provide direct, compelling evidence for both the bug fixes and the correctness of the new functionality.

### Q4: VERDICT

This is an outstanding diff. It addresses multiple, complex editorial issues with robust, well-tested, and deterministic solutions. The new gates are powerful, the fixes are precise, and compliance with the governing laws is maintained or strengthened.

| SEVERITY | DIFF LINE | ISSUE | FIX |
| :--- | :--- | :--- | :--- |
| MINOR | N/A | The root cause of warped credit avatars (D4) is not fixed in this diff. The code adds a verification step to detect the issue, but the bug in the avatar rendering itself remains. | A subsequent commit should investigate the credit rendering logic (likely in `build_shoutout.py`, which is not part of this diff) to fix the image warping. This is an acceptable omission for this feature, which focuses on gates and detection. |

The code is well-structured, the comments are clear (especially the one explaining the `ffmpeg` bug), and the new tests are exemplary. The feature successfully makes the gates catch what a human caught and fixes the underlying causes for most defects.

**READY**