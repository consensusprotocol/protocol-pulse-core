# C3 CONSENSUS — pp-selectid audit 20261115_1129, cycle 3 (the real defect found at the first live run)

THE DEFECT: at its first live run (11:52 ET Nov 15), after cycle 2, the driver died at
`import proof_saved_runs as PS` in main()'s calibration block. That module is in tests/select_by_id, which is not on
this driver's sys.path. The tests never reached the line, because they call calibrate() directly. Nothing was paid:
the import fails before any router or call. The read-only parts (1), (3) and (4) ran at once, with --no-calibration.

THE FIX (C3_STEP.diff, 44 changed lines):
- registry() reads pipeline/channels.json directly; that file is proof_saved_runs.REG.
- A new end-to-end test runs main() with the calibration on. The router and the one paid call are stubbed; the
  outputs go to a temporary folder. It asserts every seed is asked, with no cache, and that all five files are
  written.
- Mutation H19 (the import restored) is killed: 19 of 19 after a control run. Suites: 701 pass.

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and glm-5.3-flash (P1_OR_WORSE: 0). Grok not asked. Cycle 3: $0.0030.
AUDIT TOTAL: $0.0557 vendor-reported (cap $1.00). Both production ready.

RECORDED FOR THE NEXT CHANGE (P2/P3; none changes an output):
- the end-to-end test could assert a known channel in the Context, and the outputs' content;
- registry() could raise a message naming the registry when the file is missing (today: FileNotFoundError naming
  the path);
- the cycle-2 items still stand: the dead regex alternative, a comment citing spotlight.build's "step A" writer,
  resolve()'s depth constant, and the borrowed test helper.

THE CODE LANDED: 044ab303 (cycles 1 and 2, FINAL.diff) plus C3_STEP.diff (cycle 3), as audited.
