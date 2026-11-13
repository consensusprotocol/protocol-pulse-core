# pp-selectid audit 1138 (RULING 56 under RULING 60, re-based onto 58 + 59): final consensus after cycle 2

- **Cycle 2:**
  - grok: no P0 or P1, "SHIP: yes with conditions".
  - qwen: no P0. Its own table downgrades its cycle-1 "P0" (the pin does not re-compare the scorer sha) to "P2 (by
    design)". One P1, the same as glm's.
  - glm: no P0. One P1, "the only P1 anyone has sustained across both cycles", plus P2s.
- The ONE consensus item (qwen P1-NEW-1 = glm P1-1): scorer_verdicts' exception path returned only {"read": False,
  "why": "<exception>"}. It lost the diagnostics the why-chain path records. Fail closed either way: observability
  only.
  - **Implemented** after cycle 2, as its own increment.
  - Reviewed in two cycles of its own: audit 1138b. That review sees only the increment, diffed against this audit's
    cycle-2 state, so no unreviewed line goes in.
  - The record now carries the stage that failed (open / parse / shape), the path, the render's recomputed sha, and,
    when "scorer" was read as an object, its kind / event / scorer_sha / threshold.
  - The two reads of "scorer" and "verdicts" are split so that "scorer" stays readable when "verdicts" is missing.
  - glm's P2-2 is implemented with it: one test that the build's text_sha and the pin's sha256 agree on a non-ASCII
    text.
- No P0 or P1 holds in either cycle.

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P1-NEW-2 (by its own table, P2 by design): the pin's affirmed_verdict checks that a scorer_sha is present, not that it equals the render's code now | Cycle 1 R1. The build checks equality where a verdict enters (scorer_verdicts). The render's validate re-asks its own scorer on its current code. package_pin stays free of reads of the render's files (the integrator imports it). |
| G2 | glm P2-3: the sealed verdict's provenance fields (model, rubric, rule, prompt_sha256, rated_at) are not gated | Within the contract. The gate is the kind, the event, the threshold, the score, the sha and the text binding. The rest is the record. |
| G3 | glm P2-4: trims_affirmed lists the original moment ids while the variants are "<id>~trim" | The same id space as out["trimmed"] (original -> variant), which this build record has always used. |
| G4 | glm P2-5: a trimmed opener with a present but refused verdict is reported by trim_problems' message rather than scorer_problems' | Both refuse it; the message differs. |
| G5 | grok: its conditions are the P2s above | Recorded above. |

## Verification

- test_medley 113 OK; all 11 suites OK on the scratch copy (dev19, base 4b047332), with the increment applied.
- Dry run on the real verdicts file, read only: 145 read, 9 affirmed, 0 disagree; the scorer_sha = the render's code
  now.
- regression_test.sh is run on the worktree before the commit.
