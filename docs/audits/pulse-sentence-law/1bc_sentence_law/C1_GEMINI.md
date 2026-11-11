Excellent. This is a substantial and critical feature. I will now perform the requested code audit.

---

### Q1: CORRECTNESS

The changed functions appear to correctly implement their stated logic, with a strong emphasis on "fail closed" principles (Law M12).

*   **`pipeline/sentence_law.py`:** This new module forms the core of the feature and is well-designed.
    *   **Audio Processing (`SourceAudio`)**: The use of `subprocess.run` with `check=True` (L759) ensures that `ffmpeg` failures are not silent. The check for `n == 0` (L764) correctly raises an error if no audio is decoded, preventing downstream failures on empty data.
    *   **Boundary Adjudication**: The `Adjudicator` class (L838) is robust. It uses a content-addressed cache, makes cache writes atomic via `os.replace` (L890), and logs every decision (L892-898). The `allow_model=False` mode (L871) correctly raises a `LawError` for a cache miss, ensuring deterministic replays for gates.
    *   **Failure Propagation**: `boundary()` (L903) and `edge_plan()` (L951) correctly return records with `valid: False` and a reason, rather than raising exceptions for expected failures (like no pause). This descriptive failure is handled gracefully by `write_lock_cut_table()` (L1070) and `gate_g16()` (L1115), which record the reasons and fail the segment. This is excellent adherence to M12.
    *   **Cut Placement (`_accepted_cut_pair`)**: The logic correctly searches *only* within the legal windows (`pi["cut_lo"]`, `pi["cut_hi"]`, etc.) provided by the `edge_plan` (L1062-1063). This prevents cuts from moving outside the allowed silence, a key correctness requirement.
    *   **Units**: Time units appear consistently in seconds (e.g., `PAUSE_MIN_S = 0.080`), and conversions to milliseconds for reporting are explicit (e.g., `int(round((e - s) * 1000))`). No inconsistencies were found.

*   **`pipeline/run_fresh.py`:** The refactoring is a major correctness improvement.
    *   The complete removal of `_recompute_edge_words` and the complex, stateful `_snap_candidates` logic (L106-202, L238-259, L329-368) eliminates the entire class of bugs that caused D2/D3. The new flow is linear and stateless between segments.
    *   The introduction of the pre-render `stage_sentence_law` (L278, L452) is a good "fail fast" design, preventing wasted rendering time.
    *   The logic to handle `lead_in_pad_s` is correctly applied to clip duration checks (`check_clip`, L325) and G14 manifest generation (L390-399), preventing these pads from causing false-positive gate failures.

*   **`pipeline/select_passages.py`:**
    *   The replacement of `_find_word_boundaries` (which used time-based heuristics) with `sentence_law.anchor` and `sentence_law.edge_plan` (L540, L559, L567) is a fundamental fix. It ensures that segment selection is based on the *text* and its acoustic viability from the start, which is the core of the Sentence Law.

Overall, the code is of high quality. It correctly handles error conditions, avoids state leakage, uses consistent units, and the core logic appears sound and free of off-by-one errors.

### Q2: LAW COMPLIANCE

*   **SENTENCE LAW**: **COMPLIANT**. Implemented in `pipeline/sentence_law.py`. The `boundary` function (L903) requires both a lexical condition (`is_terminal` or `Adjudicator`) and an acoustic pause (`find_pause`, L928) of at least `PAUSE_MIN_S` (L694, 80 ms).
*   **SELECTION LOCK**: **COMPLIANT**. `select_passages.py` and `pinned.py` now create a `selection_lock` (L565, L55). This lock is verified against the transcript's SHA256 at cut time (`write_lock_cut_table`, L1082) and during gating (`gate_g16`, L1128). `gate_g16` explicitly fails if the `expected` words in `cuts_final.json` do not match the lock (L1133), preventing re-computation. The old re-computation code is deleted.
*   **SNAP LIMIT**: **COMPLIANT**. The old snapping logic that could search up to 2.0s away is removed from `run_fresh.py`. The new `_accepted_cut_pair` function (L1050) is constrained to search only within the `cut_lo`/`cut_hi` ranges defined by the pause around the locked sentence, as determined by `edge_plan`. This strictly prevents adding or dropping words.
*   **ONSET/TAIL**: **COMPLIANT**. New gates G17a (`gate_g17_prepared`, L1249) and G17b (`gate_g17_output`, L1264) enforce this law. G17a checks for >= 80 ms of genuine lead-in/tail on prepared clips. The lead-in pad logic (`apply_lead_in_pad`, L1204) handles sources without sufficient lead-in. G17b verifies that rendered edge words keep >= 85% of their duration (`WORD_DURATION_RATIO_MIN`, L710).
*   **CREDITS**: **PARTIAL**. The diff does not contain the `shoutout` source code itself. However, the test in `test_pulse_20261110_mustfail.py` (L1545) is updated to assert that `validate_avatar` raises a `ValueError` with the message "square". This provides strong evidence that non-square avatars (like thumbnails) are now rejected, which would prevent warping. Assuming the test is accurate, this change is compliant.
*   **LAW 20 / M2**: **COMPLIANT**. All thresholds are defined as constants in `pipeline/sentence_law.py`. The new gates are hard stops (`raise Hold`). The code that previously attempted to "fix" a failing cut by snapping has been removed.
*   **M12 FAIL CLOSED**: **COMPLIANT**. As detailed in Q1, missing data (e.g., no pause, no transcript, cache miss in `allow_model=False` mode) or exceptions consistently lead to a rejection (`verified: False`, `pass: False`, or a `Hold`).
*   **LAW 22**: **COMPLIANT**. The v2f reference path is not modified. A `pinned` run with `machine_cuts=false` (L214) uses `write_pinned_cut_table`, which is unchanged. The new `sentence_law` logic is only invoked for machine cuts or `auto` mode runs.
*   **Smallest diff / M1**: **COMPLIANT**. While the diff is large, the changes are highly targeted at implementing the new laws and removing the old, faulty logic. No new renderers, compositors, or selectors are introduced. The core stages are maintained.

### Q3: TESTS

The tests are excellent and convincingly prove the feature's claims.

*   **`test_pulse_20261110_mustfail.py`**: This is the key "proof" file.
    *   The assertions have been made more specific and now include descriptive failure messages (e.g., L1449: `f"D1: G16 must reject..."`).
    *   `TestD1HookOnset` (L1444) correctly tests for failure on the clipped opening word (D1).
    *   `TestD2Clip01Out` (L1457) now verifies not just failure, but failure for the *right reason* (`after_word` is "week.", `why` contains "not cuttable"), proving the gate is correctly identifying the boundary issue (D2).
    *   `TestD3Edges` (L1467) does the same for mid-sentence cuts (D3), checking that the failure reason is "outside the legal range".
    *   The new `TestG17bRenderedEdges` (L1492) is a very strong addition. It synthetically creates a failing case (muting the first 160ms of audio) to prove that `gate_g17_output` correctly detects when a render clips the start of a word. The positive control (`test_standard_20ms_fade_passes`) ensures it doesn't fail on normal fades.

*   **`test_fresh.py`**: `TestSelectCoords` (L1347) has been significantly improved. By creating synthetic audio with known, precise pauses (`_synth_window`), it removes ambiguity and deterministically tests that `select_passages` correctly identifies and locks the intended sentences.

*   **`test_pinned.py`**: `test_auto_mode_places_cuts_from_the_selection_locks` (L1415) correctly mocks `sentence_law.write_lock_cut_table` to prove that `auto` mode runs now use the new Sentence Law path, and not the old `compute_all_cuts`.

The tests are not vacuous and provide strong evidence that the bugs are fixed and the new laws are enforced.

### Q4: VERDICT

The changes are extensive, well-engineered, and directly address the defects (D1, D2, D3, D4) identified in the problem description. The introduction of the Sentence Law, Selection Lock, and associated gates (G16, G17) is a significant improvement in quality and robustness. The code is clean, correct, and well-tested.

I have found no significant defects.

---
**VERDICT: READY**