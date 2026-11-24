# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder): the never-empty pass's by-hand fixes pushed in 71d3d0363 and hardened in 11e0aacb4, plus RULING 159 (3)(a)'s two removals (uncommitted). Context you cannot see in the hunks: package.py soft_edges(t) (line 174) is true only for a CUTTABLE failure that is a sentence running on at a word boundary; STEP_A_SOFT (line 91) holds exactly NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN; add_flags (line 610) adds soft codes to a moment's flags; package_pin.gate_problems (line 458) refuses any FLAGGED row on a gate outside SOFT_GATES (flagged_ok, line 403); package_pin.WINDOW_H = 12.0 (line 196) is read by package.expired (package.py line 263) and window_problems (package_pin line 200).
THE CHANGES: (1) the line-up stage's `lost` set keeps, in the never-empty pass only, a clip whose CUTTABLE failure is only a soft sentence edge; any other cut failure, an exclusion or an L-v 2 (second word check) failure still drops it. (2) context_soft (line 633): a context-integrity failure whose EVERY violation is a STEP_A_SOFT code on a CLIP segment (no 'slot', i.e. not our lines) becomes step A's flag on that clip; anything else (our lines, a VO-caused code, a hard code, a verdict not measured exactly True) stays a failure. (3) step_a_sentence (line 122): ONE flag sentence for all of step A's soft codes; the step A row never carries a None flag. (4) REMOVED: ruling 144's --pbx-exception switch in the driver (tests/package/proof_ledger.py: --hours is now at most WINDOW_H; the ingest adapter is asked on the render clock) and the pbx_exception soft gate, its cap of 5 and its first-place ordering in package_pin.py. (5) REMOVED: the per-package kinds_cap row (package.KINDS_CAP, the inventory row, package_pin.CAP_GATE): flags_cap is REVIEW_FLAGS_MAX for every pin; package.chain_cap returns package_pin.flags_cap.
CHECK, quoting the code: can (1)-(3) let a HARD failure through (a cut mid-word, an L-v 2 failure, an exclusion, a code on our lines, a VO-caused code, an unmeasured verdict); can any path still widen the 12 h window or let a build read the adapter on an earlier clock; can any row or argument still raise the cap above 3 or let a pbx_exception row stand on a pin; did a removal leave a dangling name (NameError) or change a behaviour it should not. Report only what the code shows.

**Panel:** qwen27b, gptoss, glm  |  **Cost:** $0.0310
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
