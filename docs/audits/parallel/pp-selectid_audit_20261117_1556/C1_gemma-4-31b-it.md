# gemma-4-31b-it (google/gemma-4-31b-it) 207 s finish=stop usage in 11390 / out 3647 usd_reported=0.000805 usd~0.089 (upper-bound price)

The code implements a robust fallback mechanism for fetching media from YouTube "post_live" streams, which are known to return empty files when using `yt-dlp --download-sections`. By downloading the whole stream once and cutting locally via `ffmpeg`, it ensures that QA gates (word checks and frame sheets) have the necessary data to operate without violating the "fail closed" principle.

### Analysis

1.  **Fail-Closed Integrity**: The implementation strictly adheres to the requirement that missing or corrupt media must not result in a "PASS". Both `audio_window` and `visual_pin.fetch` verify the duration of the resulting file against `MIN_SECTION_SHARE` (50% of the expected window). If the file is too short, it is deleted and an `OSError` is raised, which the pipeline interprets as a failure to measure.
2.  **Efficiency and Caching**: 
    *   It prioritizes the integrator's read-only cache (`POST_LIVE_CACHE`), reducing redundant downloads.
    *   It downloads the whole stream only once per video/tag per run, reusing the local file for subsequent windows.
    *   In `visual_pin.fetch`, it checks for the existence and validity of a previously created `.cut.mp4` before attempting a new whole-stream download.
3.  **Technical Correctness**:
    *   **FFmpeg**: The use of `-ss` before `-i` in `audio_window` ensures fast seeking on large files. The video scaling `scale=-2:'min(480,ih)'` correctly ensures the height is capped at 480p and the width remains even (required for `libx264`).
    *   **yt-dlp**: The format selection for audio (`bestaudio[acodec^=mp4a]/bestaudio`) is appropriate for the target `.m4a` extension.
    *   **Concurrency**: Since `out_dir` is typically unique per run in this pipeline, the local caching of whole streams is safe. The global `POST_LIVE_CACHE` is read-only.
4.  **Test Coverage**: The new test suite `test_ruling_142_post_live.py` is comprehensive. It stubs the external binaries and verifies all critical paths: empty sections triggering whole-stream downloads, cache priority, normal section preservation, and the deletion of invalid cuts.

### Findings

No [P0], [P1], or [P2] defects were found. The logic is sound and complies with all governing laws.

[P3] **Inline Import**: In `visual_pin.py`, `import transcript_truth as TT` is performed inside the `fetch` function. While this avoids potential circular dependencies and is functional, it is generally preferred to place imports at the top of the file. Given the architecture, this is a minor stylistic point.

P1_OR_WORSE: 0