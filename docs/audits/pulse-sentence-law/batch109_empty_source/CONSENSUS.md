# Batch 109 (a source window with no media is outcome error, never a hold; its broken file dropped): consensus

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (H1-H4) | PASS (0.92) | PASS (1.0) |
| 2 (break-it T1-T3) | PASS (0.82) | FAIL: F1, judged NOT a defect |

**gpt-oss c2 F1, NOT a defect.**
- The claim: _empty_source treats "real PinError range faults" as empty.
- Why not: inside _empty_source the only call is pinned._duration, whose PinError means only "ffprobe cannot read duration" (an unreadable file, no media to judge). A real range fault is raised by validate_range and reaches the empty check with a readable file, so its duration (>= 0.5 s) keeps it a hold. The test test_a_range_fault_on_a_file_with_media_still_holds shows it.

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: the empty-window test fails on f4d00826; the media control passes on both.
- MUTATIONS.log: 4 of 4 killed.
