# Batch 114 (ruling 146 (2)), cycle 1 consensus

Reviewers: qwen27b (effort medium, 325.8 s, 46,742 chars of reasoning) and gpt-oss-20b (effort medium, 12.2 s,
6,125 chars of reasoning). Both returned PASS with no findings. Both traced every check (a)-(f) in their reasoning or
notes: no hold for the hook's lead alone; no relaxation beyond the hook's lead; the soft path's cut equals
accepted_cut's pick; the G17 row fails on any other row; no reader of "refused"; no crash path.

Checked by hand as well (not in the diff): G16's `_edge_row` (sentence_law.py) applies 80 ms only at a source FILE
HEAD (the D1 pad rule, which edge_plan declares). A non-file-head IN edge only needs the cut inside cut_lo..cut_hi,
which accepted_cut's pick satisfies. So G16 never holds a short hook.

Tests: 89 passed in the four touched suites; 12 failures on the live code (b146/MUST_FAIL_OLD_CODE.log); 11 of 11
mutations killed after an unmutated control (b146/MUTATIONS.log).

Decision: no change. Cycle 2 audits the code downstream of the cut on the same diff.
