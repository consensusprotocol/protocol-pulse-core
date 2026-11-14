# Batch 65 evidence: the must-fail tests fail on the old code and pass on the fix
CPU (2026-11-13 15:01 ET), test_safe_frame_colour.py -k TestEveryShot:
- render_vertical.py at 6fd7c8fc (OLD): 2 failed (test_every_shot_ends_on_the_inputs_colour,
  test_the_probe_keeps_known_values_only)
- the fix (55048351): 2 passed
GPU0 (NVENC, under the lease): see below, run when the render in flight (pinned_20261113_191409) has left GPU0.
GPU0 (2026-11-13 15:29 ET, CUDA_VISIBLE_DEVICES=0, NVENC under the session's GPU0 lease), test_safe_frame_colour.py:
- render_vertical.py at 6fd7c8fc (OLD), -k TestSafeFrame: 1 failed, 2 passed.
  test_a_part_opening_on_a_stack2_keeps_bt709_and_its_range FAILED: 'unknown,unknown,unknown' != 'bt709,bt709,bt709'.
  The safe-frame and single cases pass (the Nov 11 fix and the untouched crop).
- the fix (55048351), the whole file: 5 passed (3 NVENC + 2 CPU).
WHAT THE FIX BUYS, measured on the held finals (DoD 15:28): the 9:16 final's Y plane is the reference's (27.800-27.809).
Re-tagged bt709 with the same bytes, G9 reads 14.7737 (0c68b589) / 14.7712 (41f29b1f) against the floor 14.7315.
