# pp-selectid audit 0530 (ruling 33 part 2 at the pin stage, item 42): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the diff against the cycle-1 reviews and C1_CONSENSUS.md. No P0 from any reviewer.
- grok: "Yes with conditions". (1) The orchestrator must explicitly accept "pending at the render". (2) The ~trim ids
  must resolve downstream.
- qwen: "Yes with conditions". Grok's cycle-1 P0 was a misreading; "pending" is a defensible reading of item 42.
- glm: "Yes with conditions". K5 is defensible. (1) The sealed row must STATE the divergence. (2) Verify that ~trim ids
  resolve in every id-keyed map.

## Implemented after cycle 2

| # | condition | disposition |
|---|---|---|
| F5 | grok (1): the orchestrator must explicitly accept "pending at the render" | IMPLEMENTED AS A SWITCH, strict by default. package.TRIM_SCORER_PENDING = False. The pin stage judges a trimmed segment exactly as the render does with no scorer: the EDL carries the render's own marker (selection_lock.trimmed_leading), so check_edl fails it closed and it is never sealed. Variants are still built and measured ((c) step A, L-v 2 with the trimmed word, (a) the acoustic onset at the trimmed cut), so a build reports how many come back up to that point. The switch is set True only on the orchestrator's explicit yes (asked in STATE, 05:44 ET). Tested both ways. |
| F6 | glm (1): the sealed row must STATE the divergence | IMPLEMENTED for the switch's True case. Each pending segment's opener "why" ends "the clip scorer's verdict on the trimmed text is PENDING AT THE RENDER (GPU0; ruling 33 part 2)". Tested. |
| F7 | grok (2), glm (2): ~trim ids in the id-keyed maps | VERIFIED. prescreen ranks by rank_score (the variant carries its parent's), so step A screens variants in order, not last. a_by, fails, exc, tru and hk all key on the variant's own moment_id. optout is by channel. Delivery overlap was judged on the parent (usable()), whose span contains the variant's. |

## Kept

- **glm N6 (out["usable"] counts before the variants):** documented. out["usable"] is the count after usable(), and the variants are recorded in out["trimmed"] (parent -> variant).
- **qwen P1s (topic beyond no_topic; untrimmed_start vs the original start):** no_topic and no_role_on_screen are the render's own place rules. untrimmed_start is set from the parent's start by construction, and trim_problems checks it against the segment's start.

## Verification

- All 11 offline suites OK (test_medley 72, test_angles 28); regression_test.sh 26 PASS | 0 FAIL | 5 WARN; py_compile.
- Old pins still recompute: the trim keys are SEALED_LATER, entered only when present.
