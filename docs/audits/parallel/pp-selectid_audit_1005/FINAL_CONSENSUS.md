# pp-selectid audit 1005 (ruling 52's hook rating in the coherence verdict): final consensus after cycle 2

## CORRECTION (10:31 ET Nov 13): the first version of this file was wrong about qwen

- The first version (committed with ddfe1dc9 at 10:03) said "no P0 or P1 from grok, qwen or glm".
- At that moment qwen's cycle-2 review had NOT arrived. I committed the change before it returned, so the claim about
  qwen was not true.
- The call never answered. Heimdall's qwen/qwen3.8-27b timed out at the audit runner's 1800 s read deadline (10:28:33 ET).
  - That record is kept as C2_qwen3.8-27b_FAILED_1028.md.
  - The miss is logged in pp-selectid_HEIMDALL_DEADLINES.jsonl (item 55).
- Re-run at 10:29 with the byte-identical cycle-2 prompt (C2_PROMPT.md compared, unchanged; the same C2_STEP.diff):
  qwen answered in 42 s (C2_qwen3.8-27b.md).
  - It found no P0 and no P1, and its verdict is "Yes".
  - Its two P2s are below; neither changes the code.

## Cycle 2, all three reviewers

- No P0 or P1 from grok, glm or qwen (qwen from the re-run).
- glm's cycle-1 P1 is resolved: no consumer compares the coherence verdict's keys exactly, and hook_rule is inert, as
  it is in the clips-alone verdict.
- All three confirm:
  - HOOK_QUESTION is defined once and used by both verdicts;
  - MEDLEY_PROMPT is byte-identical;
  - the coherence verdict's clips after the hook and vo_point are judged as before;
  - a malformed reply is never a pass.

## qwen's cycle-2 P2s: recorded, with the evidence

| # | finding | disposition |
|---|---|---|
| Q1 | An external consumer with a strict schema might reject the new hook_rule key. | Checked, no change. The pin's "checks" is a fixed dict of booleans (pipeline/package_pin.py:270), not the verdict. The coherence gate goes into the pin as an inventory row (status, backend, replayed, measured). No file in the render's pipeline (/home/ultron/protocol_pulse/pipeline/, read only) mentions hook_rule. |
| Q2 | clip_keys interpolates the labels into the prompt's JSON template. | Checked, no change. Every label comes from labels(n) (pipeline/package.py:296): "hook", then "clip_01" onwards. No label is free text. A reply whose keys differ from the labels fails the contract and is never a pass. |

## Verification

- test_medley 92 OK at the commit; every other suite OK; regression_test.sh 0 FAIL on the worktree before the commit.
- The code is unchanged by this correction: only this record changes, and the re-run review is added.
