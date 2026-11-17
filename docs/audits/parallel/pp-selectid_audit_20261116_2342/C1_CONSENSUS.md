# C1 CONSENSUS — pp-selectid audit 20261116_2342 (RULING 130 (4): the coherence panel, ruling 118 (2))

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 1 of 3.
- gemma: P1_OR_WORSE 0.
- qwen: cut off at its 24,000 cap with no closing count: NO ANSWER. Its one tagged finding before the cut, [P2] "staging
  base_url in production model config": NOT SO: the two new back-ends copy qwen's spec, and the worktree's config gives
  that base_url to 5 of 5 Heimdall back-ends (the gateway's own address, every Heimdall call goes there).
- mimo: EMPTY at 32,000.
Cycle 2: qwen at effort medium with a 32,000 budget (this audit's driver only; the package is larger than earlier ones).
dev53: mutations P1-P8 8 of 8 killed after a control run; 40 suite files by exit code, 863 tests.
