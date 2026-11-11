# Heimdall audit

**Question:** 1d follow-up to the late Heimdall consensus on select_passages.py. Verify from the diff only: (1) the editor's own candidate for a slot is now subject to the same tried/overlap/per-video/per-channel checks as fallbacks, so a window a fallback already took is never cut twice; (2) the hook/clip duration budget is enforced on the span of the words actually locked from the file transcript, not only on the declared start/end; (3) the synthetic test fixtures declare windows exactly where their text is and each new test fails without the fix. If uncertain, say so; do not guess. (this chunk: pipeline/test_sentence_windows.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0227
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_sentence_windows.py:0** The test expects the EDL clip's `word_start` to be the local transcript time, but the `window()` helper defines the window's start as the full video time by adding `self.OFF[vid]`. This inconsistency means the test will fail if the implementation correctly stores full video times, or it will pass while checking an incorrect value.
  - evidence: `self.assertEqual(keys, [("BBB", self.words["BBB"][6 * 12]["start"])], report)  // window() helper: st, en = ws[0]["start"] + self.OFF[vid], ws[-1]["end"] + self.OFF[vid]`
  - fix: Add the offset to the expected value: self.assertEqual(keys, [("BBB", self.words["BBB"][6 * 12]["start"] + self.OFF["BBB"])], report)
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[low] pipeline/test_sentence_windows.py:97** Temp directory created with tempfile.mkdtemp is never cleaned up. The pre-diff code used tempfile.TemporaryDirectory() as a context manager which auto-removes the directory. Every call to run_select leaks a directory under /tmp.
  - evidence: `rd = tempfile.mkdtemp(prefix="fb_")`
  - fix: Use `with tempfile.TemporaryDirectory(prefix="fb_") as rd:` (wrapping the body of run_select) or add `shutil.rmtree(rd, ignore_errors=True)` in a finally block after the select_and_build_edl call.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [low] Multiple file handles opened via bare open() are never explicitly closed (passages.json write, transcript json write, edl.json read, SELECT_BOUNDARIES.json read). In CPython the GC will close them, but under PyPy or with many test runs this can exhaust file descriptors. (agree: 1)
- qwen27b:F3 [low] run_select unconditionally reads SELECT_BOUNDARIES.json even when select_and_build_edl returns False. If the implementation does not write the report file on the failure path, this raises FileNotFoundError before the caller's assertTrue(ok) can produce a clean test failure. (agree: 1)

## Added in cross-examination (not voted on)
- none
