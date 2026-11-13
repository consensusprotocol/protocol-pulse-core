# pp-selectid audit 0712 (RULING 49): final consensus after cycle 2

**Cycle 2:** no P0 or P1 from any reviewer.
- grok: "yes with conditions";
- qwen: "yes with conditions";
- glm: "yes with conditions": narrower than cycle 1, because F1 closed the one substantive gap.
All agree that:
- a trimmed clip is never sealed without scorer_pending: true, and no other clip carries it;
- the limit of one trimmed clip binds on the line-up and on the pin;
- pins without a trimmed clip seal as before (SEALED_LATER);
- nothing claims the scorer affirmed anything.

## The conditions, answered

| # | condition | answer |
|---|---|---|
| C1 | glm / qwen / grok: keep the two constants and the equality test, with the reason written down | Done: the reason (check_pin_only imports package_pin, which must never pull package.py into the integrator's process) is now a comment beside TRIMMED_PER_PIN_MAX. The equality test stays in the suite. |
| C2 | glm N4: do ruling 41's and item 44's swap paths go through lineup_ok? | Yes. swap_lineup returns a combination only `if lineup_ok(new, crange, repeat_ok)[0]`, and item 44 calls swap_lineup. lineup_for applies the same rule inline, and the no-voice path's added clip has it inline too. |
| C3 | grok / qwen / glm: when is the limit raised? | Only when the integrator reports the first trimmed clip affirmed at validate, and on the orchestrator's word: both constants together, and the tests extended. Stated in the constant's comment and in STATE. |
| C4 | grok: a test of the no-voice path's copy | Not added (P2): the same expression as lineup_for's tested rule, and the pin refuses two trimmed clips anyway (tested). |

## Verification

- test_medley 81 OK, every other suite OK; regression_test.sh is run on the worktree before the commit.
