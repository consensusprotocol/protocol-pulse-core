# Batch 86 cycle 1: no defect. qwen27b PASS 0.95, glm PASS 0.72; panel $0.0032798. Three low notes were "agreed", and each one states "fix: none" and "no defect" itself. Grok not asked: no disagreement on the verdict (ruling 107 (2)).

- **F1, consistent.** The render and gate stages read the EDL's formats independently.
  - Any mismatch with the finals handed to the gates is a Hold: ('9x16' in formats) != bool(final9 and man9).
  - A 16x9 -> both flip gives final9 None with '9x16' in formats, which is a Hold. The note itself says so.
- **F2, fail-closed already.** verify_pack.run_formats raises a plain OSError / ValueError.
  - Run.stage (run_fresh.py:254, unchanged) turns ANY Exception into a Hold with the reason and the traceback (run_fresh.py:274-279). A raw exception in the verify stage is a HOLD verdict, never a pass.
  - The formats were validated at render and at gates before the pack runs.
- **F3, consistent.** A replay after render of a 16:9-only run passes final9 = man9 = None, so a stale 9:16 on disk is never read.
  - A mismatched pair is a Hold, as F1.
- No code change from cycle 1. Cycle 2 verifies the same diff.
