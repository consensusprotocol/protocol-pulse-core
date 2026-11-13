# Batch 46 cycle 2: consensus and what was done

Implemented:
- C1 [medium], the moved-cut test edits only the reference side.
  - test_a_moved_selection_lock_fails now asserts the INPUT-side failure as well: when the EDL's selection lock
    moves, the recomputed cut table refuses the lock ("clip_01: cut_in / cut_out selection lock modified after
    selection"). That is a changed decision produced by the current code, not by an edited expected value.
  - test_a_moved_cut_fails still proves that the comparison catches a 50 ms difference. Its message direction is
    correct: the recomputed value is 31.56 and the edited reference is 31.61.
- glm F2 [medium, 1 vote], the style was taken from the reference. The check now compares TRANSITIONS.json's style
  with run_fresh.TRANSITION_STYLE, the style every run writes, and plans and matches the log line with the CURRENT
  code's style. Test: test_a_transition_style_the_code_does_not_write_fails.
- glm, added in cross-examination (medium): regression step 8 re-runs the manifest check AFTER the reproduction, so
  anything written into the reference during it fails the same run.
- glm, cross-examination (low): the CLI path regression.sh calls is tested (test_the_command_line_reproduces_without_layout).

Not implemented, with reasons:
- qwen F1 [high], "the render log is ground truth". That is intended. The fixture's question is whether the current
  code reproduces the decisions this reference was rendered with, and the junctions the render used are those
  decisions. R11 checks the EDL's structure separately.
- qwen F2 [medium], "write_lock_cut_table may read cuts_final.json". It does not. It reads <dir>/edl.json,
  <dir>/transcripts and <dir>/sources and WRITES <dir>/cuts_final.json. The scratch dir holds no cuts_final.json
  before the call.
- glm F1 [high, 0 votes], positional pairing. Every pair whose video_ids differ is CHANGED and skipped, never compared
  (the reordered-PIN test asserts it).
- glm, cross-examination (low), "the 'dropped' half of the layout test is not exercised". It is: the test's layout
  reference holds only the hook and asserts "layout reference covers ['hook']".
