# Batch 65 cycle 1: no consensus findings
Two single-vote low points, both about the tests, and both are answered by evidence, not a code change:
- glm F1 "the stack2 GPU test cannot itself prove the old code failed": it is run on GPU0 against the OLD
  render_vertical.py (6fd7c8fc) and against the fix, and both results are recorded in this batch's EVIDENCE.md. A
  must-fail test is shown to fail first.
- glm F2 "the CPU graph test checks the string, not that ffmpeg accepts it": the NVENC class encodes a real 9:16 part
  opening on stack2 (plus the safe-frame and single cases) through ffmpeg, so acceptance is tested there. The CPU test
  pins the structure (setparams after every shot) without a GPU.
