# pp-selectid audit 0815 (RULING 52: the hook rated on its own job): cycle 1 consensus

**Run.** No P0 from any reviewer. Verdicts:
- grok: "yes with conditions" (P1: an integral float);
- qwen: no P0 / P1, "SHIP: yes";
- glm: "yes with conditions" (confirmations only; it agrees that min is the right derivation).

## Answered (verified from the code; no change)

| # | finding | the code |
|---|---|---|
| A1 | grok P1: a part sent as 4.0 (an integral float) is out of contract | The clips' ratings had exactly the same check before this diff: `type(x) is not int`. The hook's parts follow the same contract, consistent, failing closed (not measured, rejected). Relaxing the existing contract is outside ruling 52. |
| A2 | glm P1-1: the unseen tail of `ok` | The line is unchanged: `ok = ... and min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES`. It runs AFTER the derivation, which wrote the hook's rating into v["clips"]["hook"]. So the hook's derived rating is inside the min; the tests show it (one part at 3 gives a FAIL). |
| A3 | glm P1-2: the verdict's two new top-level keys (hook, hook_rule) and strict-shape readers | No reader checks the verdict's shape. Every one takes keys with .get(): measured, flagged, clips, backend, replayed (package.py: ly_shape, the no-voice guard, the build loop's weak detection and log, inventory's medley row). The sealed medley row (inventory) records status, by, replayed, measured and flagged only, so the new keys never reach the seal. |
| A4 | glm P1-3 / P1-1: the derivation sits outside the try | By construction it runs only after the contract has checked the three parts as ints 1-5, so it cannot raise. glm withdraws it in its own text. |
| A5 | K1, the formula | All three reviewers keep min. glm: "a mean would let a 3 hide behind 5s, and would also break the int invariant of clips values". Recorded in HOOK_RULE, the code, and STATE. |

## Verification

- test_medley 82 OK; every other suite OK.
