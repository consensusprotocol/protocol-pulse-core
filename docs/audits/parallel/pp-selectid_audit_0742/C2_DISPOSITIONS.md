# pp-selectid audit of the 07:42-08:40 diff: cycle 2 dispositions (synthesis by the pp-selectid session, 08:47 ET Nov 12)

**Run.** Cycle 2 ran on C2_STEP.diff: the FIXED diff, 58,302 bytes, with ruling 10 and the run-once-then-majority
helper. The prompt (85,479 bytes) carried the cycle-1 reviews and C1_CONSENSUS.md. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions;
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP yes with conditions;
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions.

No reviewer kept a P0. Grok's cycle-1 P0 is now P2 in its own words ("LAW 20 is satisfied because the factory itself now
refuses what the builder refuses").

**Spend** (each reply's usage at the config's upper-bound prices; direct HTTP, not on the router's ledger):
- cycle 1: $0.36;
- cycle 2: $0.41.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K3 | content_range's upper bound is untested; its units are questioned (qwen P1-2, glm N1 / P1-1) | IMPLEMENTED as a test, `test_content_range_is_in_seconds_and_meets_both_bounds`. VO_S is seconds (package.py:49, "the VO's seconds"): at the upper bound the least VO lands exactly 70 s, and the lower bound is feasible. The units were already right; the test pins them |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| qwen P1-1: once_then_majority does not check that the runs judged unchanged text | KEPT as a caller contract. The driver builds the segments, lines, contexts and package once, before any gate, and never mutates them. Each run is a closure over those same objects, and only the seed differs (07:42 item 3: "unchanged text") |
| glm P1-2: the 63-word package is now refused by the runtime gate, not by R4 | ALREADY ASSERTED: test_the_moments_r4_on_tonights_numbers asserts R4 passes at 38.9 % and the 60-70 s window fails at 72.41 s. Recorded in C1 |
| glm P2-1 / grok P2: replayed = any(run) | KEPT, fail closed: one replayed run marks the row replayed, and that refuses the pin (L-j). all() would let a replay hide in a majority |
| glm N2 / P2-2: fidelity's whole-reply `passed` is discarded | DOCUMENTED in the driver. It only decides whether seeds 8 and 9 run; the verdict is the per-line majority (VF.majority), as 07:42 item 3 ran it |
| qwen P2-NEW-2 / glm N3: with_votes shows one run's backend | KEPT: a pass vote requires a measured run, so the representative run is measured; every run is in `majority.runs` |
| grok P2: an exact 70.00 s case in the inversion test | KEPT: the factory computes on its own decode's spans. Rounding to 2 dp is below that difference |
| (found while writing K3) content_range counts n_clips VO lines, without the takeaway after the last clip that ruling 4 added | FLAGGED, not changed tonight (K2): it shapes only the angle-first build path's search space, not a given package's gates. An open item, noted in the test's docstring |

**Conditions met before the commit:**
- grok (a): pin_and_verify.py runs on the real sealed package against the deployed edl_rules.rule_r4.
- grok (b): the tests pass (56).
- grok (c): renderer_geometry stays outside the seal.
- qwen: covered by K3 and pin_and_verify.
- glm: (a) K3; (b) already asserted.
