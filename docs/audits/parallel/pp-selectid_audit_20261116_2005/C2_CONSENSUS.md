# C2 CONSENSUS — pp-selectid audit 20261116_2005 (RULING 126 (1): the ET show date; the time-word cache key)

Seats (Heimdall only): qwen3.8-27b (re-seated at reasoning effort medium, 24,000 budget, this audit's driver only),
gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0, gemma 0, mimo 0. The whole audit
$0.0268 vendor-reported, Heimdall, not capped. CLEARED.
P3 notes only (qwen): the zoneinfo / timedelta imports inside show_date / step_a_old_keys (this codebase's own pattern,
spotlight.et_day imports zoneinfo the same way), the pick lambda's closure over prescreen's cdb and off (intended). No
change. On dev49: 9 of 9 mutations killed after a control run; 40 suite files by exit code, 849 tests.
RULING 126 (1): "LAND THEM AFTER TONIGHT'S BUILDS, not before": FINAL.diff is dev49's diff against the worktree's HEAD
f1d71a0e of these files; it is landed (copied, suites run again, committed, pushed) only after tonight's reset builds.
