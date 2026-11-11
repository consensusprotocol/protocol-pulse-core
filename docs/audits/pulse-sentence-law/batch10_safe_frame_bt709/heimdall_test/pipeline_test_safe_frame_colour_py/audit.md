# Heimdall audit

**Question:** New test for a render fix: the 9:16 safe-frame filter now ends with setparams=colorspace=bt709 so a part opening on a safe frame keeps its source's bt709 tag (it came out color_space=unknown). The test renders a bt709-tagged synthetic clip through render_vertical.reframe_auto opening on a screen shot (must stay bt709; fails on the old filter) and on a speaker crop (unchanged). Report only real defects you can quote: vacuous assertions, a fixture that would pass on the old code, missing cleanup, GPU assumptions.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0102
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_safe_frame_colour.py:49** The test never asserts the output is actually 9:16 (e.g. 1080×1920). If reframe_auto with the given config does not trigger the 9:16 safe-frame path (e.g. the width/height params are interpreted as output dimensions, or the shot classes don't activate the vertical reframe), the colour tag is trivially preserved through a 16:9 passthrough and the assertion passes on the old code too, making the test vacuous for the bug it claims to guard.
  - evidence: `self.assertEqual(self._render("screen"), "bt709,bt709,bt709")`
  - fix: After rendering, probe the output width/height (e.g. ffprobe -show_entries stream=width,height) and assert the output is 9:16 (height > width, or specifically 1080×1920). This guarantees the safe-frame filter was actually exercised before the colour assertion is meaningful.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [medium] The docstring mandates CUDA_VISIBLE_DEVICES=0, implying reframe_auto (or its internal ffmpeg filtergraph) requires a GPU. The test has no @unittest.skipIf or pre-check for GPU availability, so on a CPU-only CI runner the test will hard-fail with an opaque ffmpeg error rather than being cleanly skipped. (agree: 0)

## Added in cross-examination (not voted on)
- deepseek: [medium] Bare assert in setUpClass can be disabled with python -O, making the source color-tag validation vacuous and allowing the test to run with an untagged source.
- deepseek: [high] The test passes width=1920 height=1080 to reframe_auto, which is 16:9, not 9:16. If reframe_auto uses these as output dimensions, the test does not exercise the 9:16 safe-frame path, so the color assertion may pass on the old code.
