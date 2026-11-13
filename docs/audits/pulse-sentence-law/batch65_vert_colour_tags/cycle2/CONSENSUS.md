# Batch 65 cycle 2: no consensus findings
Single-vote points, checked:
- glm F1 [medium] "the test mocks subprocess.run, so the old code would also pass". It conflates the two classes.
  TestSafeFrameKeepsBt709 is NOT mocked: it encodes real 9:16 parts with NVENC on GPU0. TestEveryShotRedeclaresTheColour
  is the mocked CPU class, and it FAILS on the old code: run against render_vertical.py at 6fd7c8fc it fails 2 of 2 (the
  stack2 shot's chain has no setparams, and there is no _input_colour). On the fix it passes 2 of 2 (EVIDENCE.md).
- glm F2 [low] "the probe test hard-codes the option order": the order is _KNOWN's, deterministic, and part of the
  output string. No change.
- glm cross-examination [low] "an ffprobe failure leaves the part untagged silently": G9 still measures the final, so
  such a part fails closed at the gate, as before. No change.
