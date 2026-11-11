# Heimdall audit

**Question:** DEC-1 commit: per-format named constants calibrated to the approved v2f reference's measured worst value for exactly the four gates it failed (G3c valley depth, G5 9:16 true peak, G8 sharpness floor, G9 tail luma), with tests that the reference passes and a fixture just beyond fails; G8 now receives its source clips in production (it never did and always failed no_source); DEC-3: a source already below the floor is judged by the render/source ratio >= 0.85 alone; G8/G9 waiver rows removed. Find: any threshold changed beyond the stated values, any gate other than these four changed, a comparison that lets the reference fail its own value, a test that passes vacuously, a wiring error in source_clips. (this chunk: pipeline/test_dec1_calibration.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0196
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/test_dec1_calibration.py:112** The G9 failure assertion is too weak and can pass vacuously. It only rejects True and the string "True"; any other value (None, "False", 0, etc.) makes the assertion pass, so the test does not actually verify that luma_ok is False.
  - evidence: `self.assertFalse(d["luma_ok"] in (True, "True"), d)`
  - fix: Assert the boolean directly, e.g. self.assertFalse(d["luma_ok"], d) or self.assertIs(d["luma_ok"], False).
  - raised by deepseek:F2; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [high] g8_sources uses the wrong filename prefixes for source clips, contradicting the production wiring described in its own docstring. The docstring says 16:9 uses 'prepared' clips and 9:16 uses 'vertical' clips, but the code builds paths with 'final' and 'vert'. This makes source_clips point to non-existent files, so G8 will fail with no_source instead of testing the calibrated sharpness floor. (agree: 1)

## Added in cross-examination (not voted on)
- none
