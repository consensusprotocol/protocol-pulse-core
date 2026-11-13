# pp-selectid audit 0510 (ruling 41: the line-up search): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers package.py and test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: "yes with conditions";
- qwen: "Yes with Conditions". It lists a "P0" (an infinite loop on a swap failure) and then resolves it in its own text.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | After a failed swap, can the re-line re-judge a dropped moment, or loop (qwen "P0"-1 and condition 1, glm P1-1 and condition 2)? | VERIFIED: no. lineup_for begins with `ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]`, and both of build()'s calls (one per channel, and repeat_ok) pass `frozenset(dropped \| doomed)`. The weak moments join `dropped` before the swap, so neither the swap nor the re-line can pick them again. `total` grows before EVERY clips-alone verdict, so the loop is bounded by `lineups` (8). A None line-up ends the angle. |
| K2 | Is the hook in the verdict's ratings, and is the label map right (qwen conditions 2 and 3)? | VERIFIED. medley() rates the labels of labels(n) = ["hook", "clip_01", ...], and the old code's `lb != "hook"` filter on the same dict is the proof that "hook" is a key. by_lab = dict(zip(labs, segs)) maps the same labels to the line-up in order. The tests swap a hook rated 3. |
| K3 | SWAP_TOP truncated the candidates BEFORE the place's own rule, so a fitting deeper candidate could be missed (glm P1-3 and condition 3) | IMPLEMENTED: a clip candidate for a non-last place must be at least SHORT_CLIP_S long BEFORE the cap, and SWAP_TOP is 10. Tested: 12 short clips ranked above a full clip; the full clip fills a middle place. |
| K4 | The package_over docstring says the clock starts "from its clips-alone verdict", while the code takes it just before the call (glm P1-2 and condition 1) | ALIGNED: "counted from the moment its own line-up's clips-alone verdict is asked". It is checked before every write. A line-up that never writes (its verdict failed) spends only the verdict call, which counts toward the search budget. |

## Kept

- **glm P1-2 (the 15-minute wall is enforced at write boundaries):** KEPT. The checks sit before every write, as ruling 5's did ("checked before every line-up and every write", audit 2240). One write plus its gates (about 3-5 min) is the most that can run past.
- **qwen P1s (scope, break conditions):** each verified in its own text.

## Verification

- test_medley 67 OK (the budget test rewritten; 6 search tests; the K3 test). All 11 suites and regression are run before the commit.
