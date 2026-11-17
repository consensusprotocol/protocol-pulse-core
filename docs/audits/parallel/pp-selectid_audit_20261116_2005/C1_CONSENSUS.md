# C1 CONSENSUS — pp-selectid audit 20261116_2005 (RULING 126 (1): the ET show date; the time-word cache key)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 1 of 3.
- gemma: P1_OR_WORSE 0 ("No [P0], [P1], or [P2] defects found").
- qwen: cut off at its 16,000-token cap with no closing count: NO ANSWER. Its tagged fragments each end in its own
  "correct" / "consistent" / "sound" (the old-key context reconstruction; no migration for time-sensitive moments; the
  two show_date sites agree; a run at 23:00 UTC found again at 01:00 UTC under yesterday's UTC date; the test's old-key
  format): none is a defect, checked against the diff.
- mimo: EMPTY at 32,000.
On dev49: mutations R1-R9 after a control run, 9 of 9 killed; 40 suite files by exit code, 849 tests (847 + the 2 new).
Cycle 2: qwen re-seated at reasoning effort MEDIUM with a 24,000 budget (this audit's driver only; audit 0924's
measure: qwen answered at medium where it loops at none), gemma and mimo as before.
