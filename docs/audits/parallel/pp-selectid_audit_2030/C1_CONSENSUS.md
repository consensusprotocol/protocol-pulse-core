# pp-selectid audit of the L-y diff (orchestrator 20:30 ET Nov 12): cycle 1 consensus (synthesis by the pp-selectid session, 21:05 ET)

**Run.** Cycle 1 ran on C1_STEP.diff (103,655 bytes; prompt 135,833 bytes). Reviewers, each SHIP verdict and its
time:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions, 85 s.
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no, 90 s.
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions, 84 s.

**Spend:** about $0.60 at the config's upper-bound prices; direct HTTP, not on the router's ledger.

**The rule:** consensus (two or more reviewers) is implemented; a unique finding is evaluated on its evidence.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the takeaway's length vs the runtime gate (qwen P0-2 on the rounding; glm P0-3 on a bridge's seconds) | glm's case IMPLEMENTED. write_takeaway budgeted the takeaway without the bridge, so a flagged join's bridge could push the estimate past 70 s, and the redo prompt kept the same budget. Now: a write offered a bridge budgets with a bridge of LY_BRIDGE_WORDS (12) words; every redo budgets with the bridge actually written; a RUNTIME redo carries the exact word range ("a takeaway of N-M words lands it", or "shorten the bridge"). qwen's case is REFUTED on the numbers: ceil(29.25 - 1e-9) is 30, not 29, and test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps sweeps 30.0-55.9 s in 0.1 s steps, asserting runtime() of both bounds inside 60-70 |
| K2 | test gaps (qwen P2-5: a takeaway over 30 words; glm P2-6: build()'s loop control untested) | IMPLEMENTED: test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins; TestBuildLoop with every model stubbed (nothing written when the clips alone fail; a weak clip dropped and the line-up re-picked; a declined bridge drops the clip after the flagged join; a given bridge sits at the flagged join with its reason and pins; the supply exception recorded). 30 tests in test_medley.py |
| K3 | the inventory's medley / ly_shape rows (grok P2-3; glm P2-8) | REFUTED. ly_shape's row comes from row(), so it has status, by, replayed (False) and n (1). When the clips-alone verdict is not measured, the medley row is NOT RUN and ly_shape is FAIL: both are not PASS, so required_gates refuses the pin (L-m, L-j). build() also never assembles a package after an unmeasured clips-alone verdict |
| K4 | the bridge after the hook (grok P2-2 says line_problems refuses it; glm P1-7 traced it and found it consistent) | REFUTED by a test. For k == 0, assemble_medley puts the bridge in vo.intro and the slot "intro"; bridges = [takeaway] with after [n_clips]. bridge_slots gives ["takeaway"], and line_problems checks the intro separately. Grok's scenario (after_clip [0, 2]) is a shape the code never builds. The test pins a hook-join bridge: edl_vo {"intro": bridge, "bridges": [takeaway after the last clip]} |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| grok P2-1: when the writer declines an offered bridge, the line-up is dropped; L-y 2 lets the writer judge the jump followable | KEPT strict. A bridge needs both the packager's judgment AND the blind check's confirmation (L-y 2). When they disagree, the blind check has said a viewer cannot follow that jump; shipping it unbridged breaks L-y 3 ("each clip's opening must make sense after the previous clip's ending"). Dropping the clip after the join and re-picking is the fail-closed reading. The orchestrator may rule otherwise; STATE names it |
| qwen P1-2: no 30-word check in write_takeaway | REFUTED: r4() caps the line after the last clip at MOMENTS_TAKEAWAY_WORD_CAP (30); cheap_checks fails it with R4. The new test proves it on a medley |
| qwen P1-1: CI._q may cut a clip mid-word at 900 characters | REFUTED: a clip is at most 20 s (SEG_MAX_S, L-u), about 60 words, under 400 characters |
| qwen P1-3: ly_shape does not check the lines' order | KEPT: the play order is vo.bridges_after_clip (checked); lines are the gated texts, matched to the VO by line_problems |
| qwen P1-5: the scratch path in proof_ly.py | KEPT: --work-dir sets it, and the driver creates it (os.makedirs) |
| glm P1-4: repeat_ok lets two channels repeat | REFUTED: n + 1 segments with exactly n distinct channels means exactly one channel twice; two channels repeating gives n - 1 distinct, which the check refuses |
| glm P1-6: the redo says "rewrite ONLY them" while the contract needs all four keys | IMPLEMENTED (cheap and right): "Return the WHOLE JSON object again, every key; rewrite ONLY the lines below and keep the others exactly as they were" |
| glm P1-8: context-integrity failures caused by the VO's framing are not in the takeaway's record | IMPLEMENTED as a separate field, context_framing. Those violations are per clip and can come from the title or caption too, so they are recorded beside "passed" (the line's own gates), not folded into it. The table reports them |
| glm P2-3: the table counted a line-up with only writer errors as a clips-alone pass | IMPLEMENTED: build() records medley_ok per line-up; the table counts it |
| glm P1-3: chains with Heimdall as the only verdict leg | KEPT: the router skips the writer's vendor and raises when nothing is left, so the verdict is not measured and the package fails closed (L-j) |
| glm P1-1 (P2): a bridge's cites are not checked against the flagged join | KEPT: the fidelity verdict judges every line's cites; ly_shape checks where the bridge sits |
