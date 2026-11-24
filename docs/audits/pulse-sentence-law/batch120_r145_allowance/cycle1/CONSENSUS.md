# Batch 120 (ruling 145's allowance, landed in the ruling 153 lockstep a94c182e4), follow-up audit, cycle 1

Seats: qwen27b and gptoss (Heimdall, effort medium).
- qwen27b: PASS, no findings (confidence 0.82).
- gptoss F1 (high): "utilisation() raises Gpu0Unreadable instead of Gpu0Stop". DISPROVED in the code: pipeline/gpu0.py:118
  `class Gpu0Unreadable(Gpu0Stop)`; _refuse_foreign's callers and every service catch Gpu0Stop (batch 102), so an
  unreadable utilisation line is a Gpu0Stop, failing closed (no tolerance), as intended.
- gptoss F2 (medium): "None memory values in the sum of this run's memory". DISPROVED: the sum is
  `sum(m for pid, _, m in processes() if pid in ours and m)`; `and m` already skips None (and 0), which is the fix it
  proposes.
No change.
