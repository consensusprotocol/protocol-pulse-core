# Cycle 1 consensus (pp-selectid_audit_20261117_1556, the post_live fetch fallback on the builder's side)

SEATS ANSWERED: 2 of 3. gemma-4-31b-it: P0/P1 none. qwen3.8-27b: ONE P1, ACCEPTED AND FIXED. gpt-oss-20b: no answer.

## qwen [P1]: visual_pin.fetch's early return took a .cut.mp4 with no duration check (a cut interrupted by SIGKILL / OOM
## / a full disk would be returned partial) - FIXED, the only change from cycle 1 to cycle 2:
- Both cuts are now ATOMIC: ffmpeg writes <stem>.tmp.wav / <stem>.cut.tmp.mp4, and the file is renamed into place
  (os.replace) only after its duration passes MIN_SECTION_SHARE; an interrupted or empty cut never takes the final name.
- visual_pin.fetch's reuse path checks the cut's duration too (whole_cut: exists AND >= half the span), with the
  transcript_truth import hoisted above it.
- New test: a 0-second .cut.mp4 planted before the first call is never returned; the span is cut again, whole. The test
  stub follows renames. Mutation P10 (the reuse check reverted to a bare exists) is killed.
Suites after the fix: test_ruling_142_post_live 9, test_angles + test_visual_pin with it 50 passed; mutations 9 of 9.
