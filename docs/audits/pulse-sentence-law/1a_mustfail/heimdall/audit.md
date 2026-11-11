# Heimdall audit

**Question:** Commit 1a adds must-fail tests + fixtures for PBX's D1-D4 defects (clipped opening word, non-sentence clip edges, recomputed expected words, warped credit avatars). Do the tests fail/pass for the right reason, can any assertion pass vacuously, is the fixture copy-only, and is the audit-tool registration correct?

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0243
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [high] pulse-sentence-law is added to EXPLICIT_FILES, which the comment says is for features already merged to main, but this feature is not merged and the actual diff is STEP.diff, not CURRENT.diff. This can make the audit tool review the wrong or missing file. (agree: 1)
- deepseek:F2 [medium] assertIn on source text can pass vacuously if the strings appear in comments or docstrings rather than actual gate calls. (agree: 1)
- deepseek:F3 [medium] assertNotIn on exact function definitions can pass vacuously if recompute logic is renamed, imported, or implemented differently. (agree: 1)
- deepseek:F4 [medium] Source-text absence checks can pass vacuously if fallback is implemented with different strings, and can fail if the word appears in a comment. (agree: 1)
- deepseek:F5 [medium] No positive control: validate_avatar could always raise ValueError and the test would still pass. (agree: 1)
- deepseek:F6 [medium] Only asserts gates return False, not that they fail for the avatar defect; could pass for unrelated failures. (agree: 1)
- deepseek:F7 [low] Class-level tempdir is never cleaned up. (agree: 1)
- qwen27b:F1 [medium] Control test test_d3c_clip02_out_control_passes is in TestD3Edges(_G16Fixture) whose setUpClass calls L.gate_g16(...). Pre-fix (when gate_g16 does not yet exist), setUpClass raises AttributeError/ImportError, causing the control to ERROR rather than PASS. The module docstring states controls 'document what must keep passing' but the control cannot pass if the gate function it depends on is absent. The control is structurally coupled to the very check it is meant to verify independently. (agree: 0)
- qwen27b:F2 [medium] test_gate_fails_overall asserts self.ok is False, but self.ok (the overall G16 result) would be False due to D1, D2, D3a, or D3b regardless of whether the tautology/recomputed-words defect is present. The test does not isolate the tautology-specific failure; it passes for the wrong reason if any other defect triggers the overall gate failure. (agree: 1)
- qwen27b:F3 [medium] In TestWindowOffset, fake_run unconditionally executes cmd.index('--download-sections'). If _download_window makes any subprocess.run call that does not include that flag (e.g., ffprobe to read duration, or a second yt-dlp invocation with different args), fake_run raises ValueError and the test ERRORS rather than failing cleanly. The mock is not defensive against non-download subprocess calls. (agree: 1)
- qwen27b:F4 [low] test_g16_out_fails (D2) asserts only that pass is False without a secondary assertion verifying the specific failure reason (e.g., that the out-edge word is not a sentence-final word, or that the boundary falls mid-sentence). If gate_g16 fails for an unrelated reason (I/O error, missing transcript, exception caught internally), the test still passes, masking a false-positive gate failure. (agree: 1)
- qwen27b:F5 [low] TestD4Credits.S is a class-level tempfile.mkdtemp created at class-definition time with no corresponding tearDownClass to remove it. Every test run leaks a directory under /tmp. (agree: 1)
- qwen27b:F6 [low] EXPLICIT_FILES for pulse-sentence-law lists only 'docs/audits/pulse-sentence-law/CURRENT.diff', but the diff under review is at 'docs/audits/pulse-sentence-law/1a_mustfail/STEP.diff'. If CURRENT.diff is not a symlink or copy updated to the current step before the audit runs, the tool reviews a stale or missing file. Unlike track-a-d1-d3 (which lists all concrete files), this entry relies on an implicit CURRENT.diff convention that is not visible in the diff. (agree: 1)

## Added in cross-examination (not voted on)
- qwen27b: [medium] The 'no recompute' test only inspects run_fresh.py source. If the recompute/sync/snap logic is implemented in sentence_law.py, a utility module, or inlined as a lambda, the assertNotIn passes vacuously while the defect persists.
- qwen27b: [medium] test_recomputed_expected_words_fail_the_lock couples to the exact substring 'recomputed' in the errors list. If the gate reports the tautology as 'lock_mismatch', 'expected_words_changed', or 'selection_lock_violation', the assertion fails even though the gate correctly caught the defect.
- qwen27b: [low] _dur() uses subprocess.run(..., check=True) to call ffprobe. If a fixture video file is missing or corrupt, this raises CalledProcessError, causing the test to ERROR (not FAIL). For a must-fail test, an ERROR in setup obscures whether the assertion logic is correct.
