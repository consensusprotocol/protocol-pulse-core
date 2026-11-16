# Batch 96, the ruling 120 delta (8ecd1c58..9e87a073): two cycles, PASS, no finding

Ruling 120 (09:40 ET Nov 16, the orchestrator's yes, relayed verbatim by the builder) gives the release caption's line its words: "a clip passed stand-alone on the calibrated bar". The builder and the integrator agreed it is also the mark's note.

The code delta (STEP.diff, 21 lines) changes `telegram.STAND_ALONE_BAR_NOTE` and the comment above it. The tests move with it:
- the two NOTE_119 constants;
- a new review-drop test showing that a pin marked on the floor reviews without the line, beside another mark or alone.

| Cycle | Question | gpt-oss (medium) | qwen27b (medium) |
|---|---|---|---|
| 1 | D1-D4: the exact words; one value for the note and the line; never in a review drop; nothing else changed | PASS, 4.5 s; its reasoning (1,515 characters) checks each of D1-D4 against the diff | PASS 0.95, 15.7 s; its reasoning (5,485 characters) traces D1-D4, including note() and mark() reading the same BAR_MARKS entry |
| 2 | E1-E4 (break it): print the line for another note; split the note from the line; reach a review drop; disturb the other two lines or their order | PASS, 8.0 s; its reasoning (6,652 characters) finds no successful attempt | PASS 0.95, 10.9 s; its reasoning (3,826 characters) takes E1-E4 in turn: one BAR_MARKS table, review_drop never calls bar_lines, the other lines and the order unchanged |

Consensus: no finding. No change. Delta cost $0.0021 (not capped).

Tests on the delta:
- the three floor suites and test_review_drop, run together on 9e87a073: 92 passed, 131 subtests passed (178.7 s);
- the 18 mutations, rerun on 9e87a073: 18 of 18 killed, the control and the restored run passing (../MUTATIONS_r120.log).
