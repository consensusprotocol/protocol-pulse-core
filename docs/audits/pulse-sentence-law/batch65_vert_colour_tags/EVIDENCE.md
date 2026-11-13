# Batch 65 evidence: the must-fail tests fail on the old code and pass on the fix
CPU (2026-11-13 15:01 ET), test_safe_frame_colour.py -k TestEveryShot:
- render_vertical.py at 6fd7c8fc (OLD): 2 failed (test_every_shot_ends_on_the_inputs_colour,
  test_the_probe_keeps_known_values_only)
- the fix (55048351): 2 passed
GPU0 (NVENC, under the lease): see below, run when the render in flight (pinned_20261113_191409) has left GPU0.
