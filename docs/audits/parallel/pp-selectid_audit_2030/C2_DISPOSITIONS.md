# pp-selectid audit of the L-y diff: cycle 2 dispositions (synthesis by the pp-selectid session, 21:00 ET Nov 12, completed 21:14)

**Run.** Cycle 2 ran on C2_STEP.diff, the FIXED diff (114,464 bytes; prompt 149,924 bytes). The prompt carried the
cycle-1 reviews and C1_CONSENSUS.md. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions; no P0, no P1 ("All Cycle 1 P0/P1 items are resolved").
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions; no P0, no P1 ("Nothing rises to P0 in the
  fixed diff").
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP yes with conditions; no P0; two P1, evaluated below.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K5 | the first write for a flagged join budgets the takeaway for a 12-word bridge; a different bridge length moves the estimate (qwen P1-NEW-1, grok P2) | IMPLEMENTED: until the bridge is written, the takeaway's budget holds for ANY bridge of LY_BRIDGE_MIN_WORDS (3) to LY_BRIDGE_WORDS (12) words where the clips allow it (the intersection of both budgets), else for a 12-word bridge. The writer is asked for at most 12 words, and the hard cap of 20 stays in R4. Test: test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_of_3_to_12_words, over 77 clip lengths, 51 of them exercised. qwen's "up to 20 words" misreads BRIDGE_ASK ("as short as it can be (at most 12 words)") |

## Unique findings and P2s, evaluated

| finding (reviewers) | disposition |
|---|---|
| qwen P1-1: when the writer declines a flagged join's bridge, the code "silently" drops the clip; it should force the bridge or fail the line-up explicitly (grok cycle 1 wanted the opposite: ship without the bridge; glm cycle 2: the code's choice is a legitimate reading) | KEPT and NOT silent: the line-up fails explicitly. rec["why"] states the conflict ("the clips-alone verdict flagged X; the writer judged it followable without a bridge: these clips do not sit together (L-y 2): re-lined"), and test_a_declined_bridge_drops_the_clip_after_the_flagged_join pins it. Forcing a bridge the packager judged unnecessary breaks L-y 2 (both must agree). Shipping a join the blind check says a viewer cannot follow breaks L-y 3. The three reviewers disagree, so this is named in STATE for the orchestrator |
| qwen P2-1: line_problems does not check the intro of a medley | REFUTED: line_problems checks `by.get("intro") != vo.get("intro")` FIRST, for every shape. The hook-join test pins a medley whose intro is the bridge (edl_vo intro = the bridge) |

## New findings, evaluated (all P2)

| finding (reviewers) | disposition |
|---|---|
| a redo whose real bridge leaves no takeaway length that lands 60-70 s says "shorten the bridge" (grok P2; glm P2-3) | KEPT, and the message is actionable: the redo asks for the WHOLE object again, the bridge included, so the writer can shorten it. A second failure ends the line-up (WRITES bounds it) |
| a line-up at the top of the medley's seconds plus an offered bridge of more than 12 words fails the first write's runtime (grok P2) | IMPLEMENTED as K5 above (with qwen's P1); the redo still budgets with the bridge as written |
| the redo's hint covers RUNTIME only, not an R4-share failure (glm P2-2) | KEPT: with one takeaway (<= 30 words) and one bridge (<= 20), the VO is at most 22 s against a runtime estimate of at least 60, so under 37 %. R4's 45 % cannot fail on share; its word caps carry their own message |
| a bridge's cites are not tied to the flagged join's clips (glm P2-1, also cycle 1; qwen P2-2) | RECORDED as a known gap. The fidelity verdict judges every line's cites, and ly_shape checks where the bridge sits |
| the table's "best known" dollars could be mistaken for the guard's figure (glm P2-4) | IMPLEMENTED: the table now states both columns' basis (the estimate is the guard's figure; best known = the vendor's own figure where the reply carries one, else that call's estimate) |
| the ledger's reported vs estimate split (glm, closing cycle 1's loop) | VERIFIED by glm: no path lets a reported figure relax the guard |

**Conditions met before the commit:**
- grok (a): proof_ly.py ran on the newest universe and the saved ones; the table is at the top of STATE.
- grok (b): the two redo diagnostics are kept, as evaluated above.
- glm (a): the cites gap is recorded.
- glm (b): the R4-share hint is not reachable, as evaluated above.
- glm (c): the table was regenerated after the fixes.

## After cycle 2: aligned with the consumer (no relaxation)

The integrator's render-side contract for L-y (R11, branch ly-shape a93cfbfe, message 21:0x ET) accepts the one
bridge in either slot only with moments_package.bridge recording:
- text: equal to the line;
- why: non-empty;
- confirmed_by: a non-empty string, list or dict.

It also fails a record with no bridge line. package.ly_shape now refuses exactly those cases too (the morning's
principle: the gate refuses what the consumer refuses). build() already wrote that record, so no package it makes
changes. Four must-fail tests were added (text differs; confirmed_by None / True / {}; a record without a line).
These checks only tighten the gate.

## Found by the live run, after cycle 2 (each one only tightens a gate)

- **build() accepted a package with CUTTABLE FAIL** (found 21:12 ET on fresh_20261112_050611, angle 3).
  - The defect predates tonight's diff: the loop dropped a clip only on exclusion or the L-v 2 text check, never on the
    independent recogniser's edges, a REQUIRED gate since ruling C / 7.
  - The pin writer refused the package (fail closed, as designed), but the exception stopped that worker.
  - Fixes:
    - a clip whose edges are not cuttable is now dropped and the line-up re-picked (rec["lost_why"] names why);
    - build() never returns a package unless package_pin.gate_problems(required_gates) is empty;
    - the driver records a refused pin and goes on to the next universe.
  - Test: test_a_clip_the_second_recogniser_cannot_cut_is_dropped_and_never_pinned.
- **The per-package spend stop read the shared ledger** (proof_ly.py), so one worker was charged for the others' calls:
  fresh_20261112_013452 stopped after angle 1 on spend that was not its own.
  - Each worker now meters its own calls at Router._settle.
  - The stop message names which limit stopped it, with the seconds and dollars (out["budget_stop"]).
- Every universe was then re-run from the start on the fixed code. Recorded replies to unchanged prompts are reused
  (cached, not replayed: the router's live-run rule).
