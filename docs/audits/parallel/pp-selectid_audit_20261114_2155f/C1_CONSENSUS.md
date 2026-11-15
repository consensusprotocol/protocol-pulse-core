# Cycle 1 consensus: pp-selectid audit 20261114_2155f (the flip of RENDER_16X9_ONLY)

The reviewers disagreed (qwen P1_OR_WORSE 1, glm 0), so Grok was asked as the third (1). Cost: $0.0166 vendor-reported.

BOTH P1s ARE REFUTED, with evidence:
- qwen P1, "a pin WITHOUT formats may be rejected". The integrator's landed code (main c396c3c8,
  pipeline/release_auth.py package_formats) returns None, meaning both formats, when "formats" is absent. It raises
  only for a present value other than ['16x9'] or ['16x9', '9x16']: "None when absent (both) ... (absent = both)".
  So every dual-format pin, absent the key, renders both as before. This side seals the key only for a 16:9-only clip.
- Grok P1, "no end-to-end test through release_auth". The release side is the integrator's own landed change, which
  covers release_auth, run_fresh's verdict, the drops and check_pin_only: audits batch 85, two cycles, no defect,
  both regressions green. This side's half is pinned by test_formats (the seal covers formats; stripping it breaks
  the seal) and by test_visual_pin (the flip, both directions).
glm: no P0/P1, and it confirms the flip is the minimal change.

Nothing to implement. The test already pins both directions.
