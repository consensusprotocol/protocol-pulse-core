# pp-selectid audit 1112 (RULINGS 58 + 59): final consensus after cycle 2

- **Cycle 2:**
  - grok: no P0 or P1, "SHIP: yes with conditions" (P2 items, below).
  - glm: no P0 or P1 ("No score dropped. Nothing changed my overall assessment").
  - qwen: one P1 (P1-NEW-1), refuted below; it retracted its P1-NEW-2 in its own text.
- No P0 or P1 holds in either cycle. The code is unchanged from cycle 1, and cycle 2 reviewed the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R5 | qwen P1-NEW-1 / glm N4 (P2): the second screen's cache read can serve the first screen's verdict, or the first screen's vendor, as the "second" verdict, so both screens come from one vendor | The second screen avoids the FIRST VERDICT's vendor and family, not the writer's. second_screen groups each clip by the back-end of its first verdict (pipeline/package.py:467 in HEAD). It calls prescreen(..., {k[0]}, {k[1]}, ...) with that vendor and family (:472). prescreen's cache read takes only an entry off them (`off(name)`). Then any second verdict whose vendor or family is the first's fails as STEP_A_SAME_VENDOR (:485). qwen's scenario ("second screen avoids Heimdall, finds XAI in cache; both screens are XAI") takes the avoid set to be the writer's; it is the first verdict's. Tested: test_a_moment_is_paid_for_once_across_builds asks again, rather than reusing, when the cached verdicts are xai and xai must be avoided, and its verdicts come from heimdall. test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor covers the same-vendor refusal. |
| R6 | grok P2: rebuild hrank from the passing hooks after the second screen | It is built from them. `passing` is recomputed from `cleared` after the second screen's filter and the three-channel check, and hrank reads that list. |

## Recorded (P2, no change; with cycle 1's G1-G11)

| # | finding | why no change |
|---|---|---|
| G12 | glm N3: lineup_for(hook_only=True) without need_onset does not apply the rating gate | Latent. Every build() call passes need_onset=True (with it the gate holds: can_open), and the rating gate lives where the onset gate lives. No caller uses hook_only without need_onset. |
| G13 | glm N5 (= cycle 1 G8): the dangling "the best: " when nothing was rated | Cosmetic; the why carries "(N not rated: <error>)". |
| G14 | glm N8: the reply example in the hook prompt names the three parts by hand, while the validator derives them from HOOK_PARTS | Recorded for the next ruling that changes HOOK_PARTS. |
| G15 | grok: a most-recent tie-break among several eligible cached back-ends; an assertion that no writer-vendor verdict is ever written | The pick is deterministic (sorted by back-end) and always off the vendors that screen must avoid. Which vendor writes is known per build, so the cache stores both vendors' verdicts and each read filters them. |

## Verification

- test_medley 105 OK; all 11 suites OK on the scratch copy (base 635bc4f9).
- regression_test.sh is run on the worktree before the commit.
