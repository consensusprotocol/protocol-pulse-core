**PROTOCOL PULSE — CODE AUDIT**
**AI Model:** Gemini 2.5 Pro
**Feature:** pulse-sentence-law
**Review Start:** 2026-11-11 22:23:01 UTC

This review is based on the provided feature description, governing laws, and test plan. The code diff itself was not included in the review package. Therefore, this audit outlines the specific checks that must be performed on the code once it is provided. It cannot verify the implementation directly.

---

### Q1: CORRECTNESS

As the code is not available, I cannot verify the correctness of its implementation. However, based on the requirements, I have identified critical areas to inspect for common classes of defects:

*   **Time/Index Handling:** The code must be scrutinized for off-by-one errors in word/frame indices and for incorrect unit conversions (e.g., seconds from a library vs. milliseconds required by a law). For instance, SNAP LIMIT defines a window `previous word's offset .. the next word's onset`. The implementation must correctly handle floating-point timestamps and use inclusive/exclusive bounds as intended.
*   **State Management:** The pipeline processes multiple clips for multiple videos. I will verify that no state (e.g., audio levels, thresholds, transcript data) leaks from one clip to the next. Each gate's check must be performed on pristine data for the specific clip under review.
*   **Exception Handling & Fail-Closed (M12):** I will check every `try...except` block. A broad `except:` that returns a `PASS` or a default value that allows processing to continue would be a violation of M12. Any failure in a dependency (model call, file read, audio analysis) must propagate as a `FAIL` or `HOLD` for the item being processed. A function that can return `None` on failure must have its return value checked by the caller, and that check must lead to a non-passing state. For example, if punctuation restoration (L-e) fails, `transcript_store.acquire` must not return a passable record.

### Q2: LAW COMPLIANCE

This is a prospective compliance check. The code, when supplied, will be checked against these points:

*   **SENTENCE LAW:** **COMPLIANT (pending code)**. I will verify that the code identifies sentence boundaries *only* from punctuation present in the transcript record and does not infer them. The logic for finding the cut point must not have a minimum gap duration, as per DEC-10.
*   **SELECTION LOCK:** **COMPLIANT (pending code)**. I will trace the `selection_lock` data from `edl.json`. The code that verifies the first/last words of a cut clip must compare against these locked-in values, not against values re-computed from the final cut points.
*   **SNAP LIMIT:** **COMPLIANT (pending code)**. The code must define the cutting window precisely as `[word_before.end_time, word_after.start_time]`. I will confirm that the final cut point is mathematically guaranteed to be within this window and that no code path allows it to move outside this boundary.
*   **NEIGHBOUR:** **COMPLIANT (pending code)**. This is a complex check. I will need to see the audio processing code that: 1) calculates the "valley threshold" (`local speech - 12 dB`), 2) applies the fade, and 3) analyzes the post-fade audio to ensure it remains below the threshold. This check must happen on the final rendered audio frames corresponding to the neighbor's side of the cut.
*   **ONSET/TAIL:** **COMPLIANT (pending code)**. I will verify two distinct code paths: one that checks for `>= 80 ms` of sub-speech audio for file-initial and hook-initial onsets, and a separate one that checks the `>= 85 %` duration rule for all other edge words. The logic must not conflate these two rules.
*   **CREDITS:** **COMPLIANT (pending code)**. I will check the data source for the avatar images. It must be a direct link to the channel's registered avatar, not a thumbnail or other image. Gate G15's implementation will be reviewed to ensure it's comparing against the correct channel registry.
*   **L-a SIGN-OFF NAMES ALL:** **COMPLIANT (pending code)**. I will inspect `run_fresh.stage_voice` to ensure the check `spoken_channels == credit_rings.credit_channels(edl)` is strict and order-sensitive (hook first). The `G20` gate must use the same canonical channel names/aliases as the credit generation logic.
*   **L-b EDGE WORDS WHOLE:** **COMPLIANT (pending code)**. The implementation of `sentence_law.edge_fades` is critical. It must calculate the available gap and place the fade entirely within it, even if shortened. The `gate_g17_edges` implementation must compare the level of the edge word audio in the final render against the source, and the comparison must show a delta of less than 1 dB for every frame of the word itself.
*   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** **COMPLIANT (pending code)**. I will examine the control flow in `run_fresh.stage_gates`. There must be a specific conditional block that implements this override: `if G3_fail and G17c_pass and G16_pass: override_fail()`. The default path must be to honor the G3 dissent.
*   **L-d PROTECTED PREVIEW:** **COMPLIANT (pending code)**. The existence and execution of `pipeline/check_preview_reference.py` within `pipeline/regression.sh` will be verified. The check must perform a hash comparison on the generated artifacts against the reference checksums.
*   **L-e PUNCTUATED BEFORE READ:** **COMPLIANT (pending code)**. I will review `transcript_store.acquire` to ensure it rejects or fails on any transcript record that is not of type `sentence_ready` or `whisper_words_punct`. There should be no path for an unpunctuated verbatim record to be passed to `editorial_select`.
*   **L-f CHANNELS FIRST:** **COMPLIANT (pending code)**. I will check the main loop in `editorial_select`. It must be structured as three sequential, mutually exclusive steps: process 48h clusters, then (if no results) 72h clusters, then (if still no results) wire headlines. The logic for `cluster_entry` must explicitly count the number of unique channels and enforce `MIN_COVERAGE_CHANNELS`.
*   **L-g WRITTEN FORMS:** **COMPLIANT (pending code)**. I will inspect the normalization function used by `segment_v1/qa_gates._g3b_words`. It must contain a mapping for symbols like `$` and `%` to their spoken word equivalents (e.g., `dollars`, `percent`). This function must be applied identically to both the expected text from the EDL and the text from the ASR gate.
*   **L-h TEXT READ AS SPOKEN:** **COMPLIANT (pending code)**. The implementation of `transcript_store.read_text` will be checked for calls to an HTML entity decoder and a token-joining routine. The versioning of the embedding cache will also be verified.
*   **L-i THE CLAIM IS THE EVENT:** **COMPLIANT (pending code)**. I will check the assignment in `story_semantics.derive_story_query`. The line of code must look like `item.underlying_event = item.claim` for cluster-derived items.
*   **LAW 20 / M2, M12, LAW 22:** **COMPLIANT (pending code)**. I will scan for hardcoded constants for thresholds, confirm exceptions lead to failure states per M12 (see Q1), and verify the existence of a byte-identical comparison test for the `v2f` reference.

### Q3: TESTS

The test plan appears sound, but its effectiveness depends entirely on the implementation.

*   **`test_pulse_20261110_mustfail.py`**: I will verify that this test fails due to specific gate violations corresponding to the documented defects (D1-D6). For example, the clipped opening word (D1) should fail the ONSET/TAIL check or G17c (L-b). The mid-sentence cuts (D2/D3) should fail the SENTENCE LAW check. The test should assert the *reason* for failure, not just that a failure occurred.
*   **`test_punct_word_pass.py`**: I will verify this test correctly loads the unpunctuated verbatim record for Altcoin Daily, runs it through the new punctuation restoration path, and asserts that the resulting hook window (`161.14-170.08`) is now identified as valid, whereas the verbatim record would produce no valid windows.
*   **`test_dec13_clusters.py`**: I will check that the test creates mock data representing the channel statements and asserts that the `editorial_select` function produces clusters for the "$74K-pullback" and "ETF-outflow" topics, and that they are passed to the model stage.
*   **`test_g3b_majority.py`**: This test must check that `_g3b_words` with the input `'above $40 trillion'` correctly normalizes it to `'above 40 trillion dollars'` for both the expected and actual readings before comparison, resulting in a pass.
*   **`test_caption_entities.py`**: This test must prove that a transcript containing `S&amp;P 500` is read as `S&P 500` for semantic checks, and that a Whisper output of `'$81', ',000'` is correctly joined to `'$81,000'` before processing.
*   **Vacuous Passes**: I will ensure that tests assert not only the correctness of the result but also that a non-zero amount of work was done. For example, a test for gate passes should also assert that `N` clips were processed, preventing a pass that occurs because no clips were found to test.

### Q4: VERDICT

A definitive verdict is not possible without the source code diff. The detailed laws and must-fail/must-pass criteria provide a strong framework for a review, but the implementation is paramount.

*   **BLOCKER** | N/A (No code provided) | The code diff, which is the subject of the audit, is missing from the review package. | Provide the complete and exact staged diff of the single commit for this feature.

**NOT READY**