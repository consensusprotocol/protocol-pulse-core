# Heimdall audit

**Question:** 1d follow-up to the late Heimdall consensus on select_passages.py. Verify from the diff only: (1) the editor's own candidate for a slot is now subject to the same tried/overlap/per-video/per-channel checks as fallbacks, so a window a fallback already took is never cut twice; (2) the hook/clip duration budget is enforced on the span of the words actually locked from the file transcript, not only on the declared start/end; (3) the synthetic test fixtures declare windows exactly where their text is and each new test fails without the fix. If uncertain, say so; do not guess. (this chunk: pipeline/test_fresh.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0145
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_fresh.py:1** Diff only modifies test_fresh.py; no select_passages.py changes are present, so claims (1) and (2) cannot be verified from this diff.
  - evidence: `diff --git a/pipeline/test_fresh.py b/pipeline/test_fresh.py`
  - fix: Provide the select_passages.py diff or explicitly scope verification to the test file.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[low] pipeline/test_fresh.py:69** Claim (3) is only partially supported: window() declares start/end from the first/last word timestamps, but the diff shows only one modified test and no implementation fix, so 'each new test fails without the fix' cannot be verified.
  - evidence: `st, en = round(ws[0]["start"] + win_off[vid], 2), round(ws[-1]["end"] + win_off[vid], 2)`
  - fix: Include the new tests and the select_passages.py fix, or state that failure-without-fix was verified separately.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[medium] pipeline/test_fresh.py:62** The test test_edl_times_are_source_file_coords does not verify that the editor's own candidate is subject to the same tried/overlap/per-video/per-channel checks as fallbacks (audit Q1). It only asserts coordinate mapping (time_coords, source_window_offset_s, word_start/word_end bounds) and word-lock identity. No assertion exercises a scenario where a fallback has already claimed a window and the editor's candidate must be rejected or shifted.
  - evidence: `self.assertEqual(seg["time_coords"], "source_file")
                off = seg["source_window_offset_s"]
                self.assertIn(off, (95.0, 495.0))
                self.assertLess(seg["word_star`
  - fix: Add a test case where two passages (or a passage and a fallback) target overlapping windows on the same video/channel, and assert the second is rejected or re-windowed. Without this, Q1 is unverified from this file.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] pipeline/test_fresh.py:62** The test does not verify that the hook/clip duration budget is enforced on the span of words actually locked from the file transcript rather than on the declared start/end (audit Q2). The docstring mentions 'hook budget 8-12' and 'clip budget 12-20' but no assertion checks a duration-budget pass/fail boundary. The fixture's computed duration (e.g. ~8.8 s for 2 sentences) is never asserted against a budget threshold.
  - evidence: `"""Sentence-structured word timestamps: 0.30 s words, 0.05 s word gaps, 0.50 s sentence gaps.
    12 words a sentence, so 2 sentences = 8.8 s (hook budget 8-12) and 3 = 13.45 s (clip budget 12-20)."""`
  - fix: Add a test where the declared start/end span is within budget but the actual locked-word span exceeds it (or vice-versa), and assert the correct accept/reject outcome. This directly exercises Q2.
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[low] pipeline/test_fresh.py:65** Audit Q3 asks that 'each new test fails without the fix.' The fixture change (window() computing start/end from actual word timestamps, fake_dl returning win_off[vid]) makes the declared coordinates correct, but the test's assertions (coordinate bounds, word-lock names) would likely still pass against an unpatched select_passages.py because they do not assert on the overlap-rejection or duration-budget-on-actual-span behavior that constitutes the fix. The test validates fixture correctness, not the fix itself.
  - evidence: `return (path, win_off[vid])`
  - fix: This is a coverage observation rather than a code bug. To satisfy Q3, the test suite (possibly in a sibling file) must include a case that is green only when select_passages.py enforces the new logic. If no such case exists in the full diff, Q3 is not fully verified.
  - raised by qwen27b:F3; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
