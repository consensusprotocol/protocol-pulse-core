# pp-selectid audit 1330 (RULING 66: a passed line-up is kept; --from-candidate): FINAL consensus (cycle 2)

- **Cycle 2:**
  - grok: "Yes ... Ship".
  - qwen: "SHIP: yes with conditions". Its conditions are P2s and "do not block the immediate use of --from-candidate
    on the 12:22 record". It now refutes its own cycle-1 P1, by R1 and the dry run.
  - glm: "SHIP: yes with conditions ... neither blocks the 12:22 seal ... Ship it".
- No P0 or P1 holds. R1 and R2 stand: no reviewer contests either in cycle 2.

## Applied (the one consensus item)

| # | finding | the change |
|---|---|---|
| C1 | glm P1-1, adopted by qwen C2 P2-1: load_candidate documents ValueError, but a malformed tried entry (a line-up that is not a list of ids, e.g. a string) raised TypeError, or was exploded into characters | load_candidate checks the entry's shape once (ids_ok): the line-up is a non-empty list of strings and the angle is an int. The scan skips a malformed entry, and an explicit index to one raises ValueError. Test: test_the_record_gives_the_first_passing_line_up_with_its_seeds now also refuses lineup="hxy" and angle="1". The real 12:22 record still loads: tried[0], ai 0, line-up 1. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm C2 P2-2: no Rig test of a ruling-41 swap before the passing entry | The mechanism is R2: one tried entry per loop iteration, and n_lineup is incremented exactly when its line-up is not None (package.py:2404-2412). The dry run proves the 12:22 record end to end. |
| G2 | glm C2 N-1 / N-2: a candidate closed before the loop has no "result" and no "search" block | `closed` carries the reason, and why_none is set. proof_ledger never reads res["search"]. The other early returns (no hook in the pool, fewer than 3 channels) have the same shape. |
| G3 | glm C2 N-3: angle_tried is per build, so it may not be the candidate angle's | Intended "as judged". The original build set writers_v / writers_f and writer_avoid from the FIRST angle call's reply (angle_reply) for every angle, follow-up angles included. The candidate takes exactly that back-end and its tried list. |
| G4 | glm C1 P1-2 / C2 P2-3: repeat_ok comes from the recorded supply exception | The candidate's clips are fixed. The build recomputes the exception's reason for its record. The 12:22 candidate has none. It goes to the standing registry change. |
| G5 | qwen C2 P2-2 / P2-3: a comment on `filled`; "not tried" is unreachable | Cosmetic. A2 (C1) records why `filled` is initialised. |

## Verification

- test_medley 131 OK on dev22 with the guard; all 11 suites OK on dev22 (before the guard; re-run in the worktree after
  the apply), plus regression_test.sh.
- The offline dry run on the real 12:22 record (C1_CONSENSUS.md):
  - SERVED from their recordings: the clips-alone verdict 4/4/4, the exclusion verdicts, write 1, and its fidelity,
    viewer and context verdicts;
  - the first new call: ruling 65's caption-only write.
