# Batch 10 (the 9:16 safe frame dropped the colour-matrix tag): dispositions

Why: the Nov 11 recut's 9:16 final (runs/pinned_20261111_172202) carried color_space=unknown; v2f's 9:16 and
both 16:9 finals carry bt709. The vertical parts that open on a safe-frame shot (vert_hook, vert_clip_01,
vert_clip_03) were unknown, vert_clip_02 (speaker crop) bt709; the concatenated final inherits the first
part's tags. LETTERBOX_VF's colorlevels runs in RGB: ffmpeg 4.4 converts the blurred background YUV -> RGB ->
YUV with the same BT.601 matrix both ways (values kept) and the overlay output loses the matrix tag. Decoders
then read the whole 9:16 as BT.601: G9 measured 14.4652 (decoded as bt709: 14.7418; v2f 14.7715).

Fix: reframe_auto probes its input's color_space once; a shot that uses the safe frame re-declares that
matrix (setparams=colorspace=<input's>), metadata only; an untagged input stays untagged; no pixel changes;
other shot classes unchanged. Law 22: every v2f 9:16 part is bt709 and none opens on a safe frame; re-proof
at this HEAD runs with 4b.

Audited: cross-LLM GPT-4o + Gemini (Grok blocked); Heimdall deepseek + qwen27b on render_vertical.py, on the
new test (heimdall_test/: the test file is matched by .gitignore's `test_*` and is force-added like the other
tests), and a second pass on the revised render_vertical.py (heimdall_r2/: no findings).

## Implemented
- Heimdall deepseek F1 [high, agree 1]: a hard bt709 tag would mislabel a non-709 source: the safe frame now
  re-declares the INPUT's own matrix, and nothing when the input declares none.
- Heimdall consensus [high] (test): the test now asserts the output is 1080x1920 (the 9:16 reframe and its
  safe frame really ran); verified to fail without the re-declared matrix.
- Heimdall qwen27b F2 [medium, agree 0]: the test skips without h264_nvenc / a GPU.

## Rejected, with evidence
- Cross-LLM P0 [both] "implement the core pulse-sentence-law feature": the audit feature name is the
  session's standing one for every Pulse Check batch; this batch is a render fix.
- Cross-LLM P0 [both] "Law 22": v2f's 9:16 parts are all bt709 and none opens on a safe frame (measured);
  the change only re-declares frame metadata; the byte-identity re-proof runs at this HEAD before 4b's runs.
- Cross-LLM P1 "no tests": the cross-LLM diff could not include the gitignored test file;
  pipeline/test_safe_frame_colour.py (2 tests) is in this commit.
- Cross-LLM P2 "separate branch", "stale pixel baselines": one working branch per session (the orchestrator's
  setup); no pixel value changes, so no baseline moves.

## Verification
pipeline/test_safe_frame_colour.py 2 passed; test_vertical_layout + test_transitions 25 passed;
regression_test.sh 26 PASS / 0 FAIL; pipeline/regression.sh PASS.
