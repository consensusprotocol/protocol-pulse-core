# Ruling 85.1: the replay of Grok's recorded verdicts on Heimdall's families

Built 2026-11-14 01:06 EST from 884 (record, model) rows. A unit is one decision (a clip, a line-up, a hook, a line, a moment). Stricter: Heimdall fails what Grok passed. Looser: Heimdall passes what Grok failed. Different: another name, or other flagged joins with the same decision.

| type | model | records | answered | no verdict | units | agree | stricter | looser | different | agree % | median s | > 120 s | timeouts | errors | usd reported |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| step_a | deepseek | 56 | 40 | 0 | 295 | 219 | 55 | 21 | 0 | 74 | 277 | 56 | 16 | 0 | 0.0989 |
| step_a | glm | 96 | 47 | 8 | 348 | 267 | 30 | 51 | 0 | 77 | 45 | 27 | 27 | 14 | 0.0292 |
| step_a | qwen | 96 | 21 | 1 | 157 | 123 | 17 | 17 | 0 | 78 | 0 | 25 | 19 | 55 | 0.1148 |
| step_c | deepseek | 33 | 27 | 0 | 82 | 79 | 2 | 1 | 0 | 96 | 223 | 30 | 6 | 0 | 0.0439 |
| step_c | glm | 33 | 22 | 0 | 67 | 65 | 0 | 2 | 0 | 97 | 6 | 14 | 10 | 1 | 0.0047 |
| step_c | qwen | 33 | 27 | 0 | 83 | 81 | 1 | 1 | 0 | 98 | 69 | 10 | 6 | 0 | 0.0962 |
| clips_alone | deepseek | 58 | 57 | 1 | 114 | 71 | 1 | 11 | 31 | 62 | 69 | 7 | 0 | 0 | 0.0335 |
| clips_alone | glm | 91 | 31 | 49 | 62 | 32 | 0 | 7 | 23 | 52 | 4 | 7 | 0 | 11 | 0.0117 |
| clips_alone | qwen | 91 | 41 | 0 | 82 | 44 | 2 | 9 | 27 | 54 | 0 | 2 | 0 | 50 | 0.0586 |
| coherence | deepseek | 18 | 18 | 0 | 18 | 16 | 2 | 0 | 0 | 89 | 21 | 0 | 0 | 0 | 0.0033 |
| coherence | glm | 18 | 16 | 2 | 16 | 15 | 1 | 0 | 0 | 94 | 2 | 0 | 0 | 0 | 0.0009 |
| coherence | qwen | 18 | 18 | 0 | 18 | 16 | 2 | 0 | 0 | 89 | 20 | 0 | 0 | 0 | 0.0137 |
| hook | deepseek | 6 | 6 | 0 | 23 | 22 | 0 | 1 | 0 | 96 | 43 | 0 | 0 | 0 | 0.0020 |
| hook | glm | 6 | 4 | 2 | 11 | 11 | 0 | 0 | 0 | 100 | 30 | 0 | 0 | 0 | 0.0008 |
| hook | qwen | 6 | 5 | 1 | 15 | 15 | 0 | 0 | 0 | 100 | 22 | 0 | 0 | 0 | 0.0071 |
| fidelity | deepseek | 39 | 37 | 0 | 139 | 75 | 51 | 13 | 0 | 54 | 209 | 33 | 2 | 0 | 0.0615 |
| fidelity | glm | 39 | 24 | 0 | 91 | 71 | 7 | 13 | 0 | 78 | 15 | 15 | 14 | 1 | 0.0037 |
| fidelity | qwen | 39 | 27 | 0 | 97 | 78 | 16 | 3 | 0 | 80 | 89 | 17 | 12 | 0 | 0.1045 |
| exclusion | deepseek | 27 | 27 | 0 | 27 | 25 | 2 | 0 | 0 | 93 | 7 | 0 | 0 | 0 | 0.0031 |
| exclusion | glm | 27 | 27 | 0 | 27 | 27 | 0 | 0 | 0 | 100 | 3 | 0 | 0 | 0 | 0.0013 |
| exclusion | qwen | 27 | 27 | 0 | 27 | 25 | 2 | 0 | 0 | 93 | 8 | 0 | 0 | 0 | 0.0102 |
| speaker | deepseek | 9 | 8 | 0 | 8 | 7 | 0 | 1 | 0 | 88 | 86 | 1 | 0 | 1 | 0.0057 |
| speaker | glm | 9 | 9 | 0 | 9 | 7 | 0 | 2 | 0 | 78 | 5 | 1 | 0 | 0 | 0.0020 |
| speaker | qwen | 9 | 9 | 0 | 9 | 7 | 0 | 2 | 0 | 78 | 34 | 1 | 0 | 0 | 0.0201 |

## The baseline: Grok against Grok (the same prompt asked again: another seed or build)

| type | unit pairs | agree | agree % |
|---|---|---|---|
| step_a | 1082 | 916 | 85 |
| clips_alone | 14 | 11 | 79 |
| fidelity | 15 | 9 | 60 |
| step_a_excerpt | 1082 | 916 | 85 |

## Anchors: the delivered pins' own decisions that Grok passed must still pass

- deepseek: 99 anchor decisions Grok passed; 11 failed by deepseek; 14 without a verdict: step_c clip_01 ['0c68b589']: FAILED (80ff1fabf7cb9467326.json); step_c clip_01 ['0c68b589']: FAILED (e7425715bd3e64d8aee.json); step_c hook ['37c5b5f5', '41f29b1f']: no Heimdall verdict; step_c clip_02 ['37c5b5f5']: no Heimdall verdict; step_c clip_03 ['37c5b5f5', '41f29b1f']: no Heimdall verdict; fidelity intro ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity bridge_1 ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity title ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity caption ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity title ['41f29b1f']: FAILED (139ef7fecdaf52db5d6.json)
- glm: 164 anchor decisions Grok passed; 1 failed by glm; 73 without a verdict: hook f29c27fb49bdc3fd050e ['0c68b589']: no Heimdall verdict; coherence package ['37c5b5f5']: no Heimdall verdict; step_c hook ['37c5b5f5', '41f29b1f']: no Heimdall verdict; step_c clip_02 ['37c5b5f5']: no Heimdall verdict; step_c clip_03 ['37c5b5f5', '41f29b1f']: no Heimdall verdict; step_c hook ['37c5b5f5']: no Heimdall verdict; step_c clip_01 ['37c5b5f5', '41f29b1f']: no Heimdall verdict; fidelity takeaway ['41f29b1f']: no Heimdall verdict; fidelity title ['41f29b1f']: no Heimdall verdict; fidelity caption ['41f29b1f']: no Heimdall verdict
- qwen: 164 anchor decisions Grok passed; 6 failed by qwen; 92 without a verdict: hook f29c27fb49bdc3fd050e ['0c68b589']: no Heimdall verdict; coherence package ['37c5b5f5']: FAILED (89d672154f0741536c8.json); step_c clip_01 ['0c68b589']: FAILED (80ff1fabf7cb9467326.json); step_c hook ['0c68b589']: no Heimdall verdict; step_c clip_01 ['0c68b589']: no Heimdall verdict; fidelity intro ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity title ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); fidelity caption ['37c5b5f5']: FAILED (68cd3b84cff5ad1f059.json); step_a 3a6cb29a4d904118192c ['0c68b589']: no Heimdall verdict; step_c hook ['37c5b5f5']: no Heimdall verdict

## Step A's REFERENT_OUTSIDE refusals (Grok's) must still be refused

- deepseek: Grok refused 88 clips for REFERENT_OUTSIDE; Heimdall refuses 76 of them (70 for REFERENT_OUTSIDE itself)
- glm: Grok refused 69 clips for REFERENT_OUTSIDE; Heimdall refuses 40 of them (34 for REFERENT_OUTSIDE itself)
- qwen: Grok refused 43 clips for REFERENT_OUTSIDE; Heimdall refuses 34 of them (30 for REFERENT_OUTSIDE itself)

## The visual sheets (nemotron and qwen against Grok's flags)

| model | sheets | answered | agree | stricter | looser | different | median s | usd reported |
|---|---|---|---|---|---|---|---|---|
| nemotron | 9 | 9 | 9 | 0 | 0 | 0 | 24 | 0.0034 |
| qwen | 9 | 8 | 8 | 0 | 0 | 0 | 14 | 0.0149 |
- Grok flagged 0 of the 9 sheets compared; agreement on unflagged sheets says little about a model's eye for a flag.

## The proposed routing (the rule is the orchestrator's to rule)

- context_verdict (step_a, step_c): none; Grok as the second family (fewer than two Heimdall families pass)
  - deepseek: step_a: an anchor decision Grok passed is failed, 12 REFERENT_OUTSIDE refusal(s) let through, agreement 74% < the bar 85%, median 277 s > 120 s; step_c: an anchor decision Grok passed is failed, median 223 s > 120 s
  - glm: step_a: an anchor decision Grok passed is failed, 29 REFERENT_OUTSIDE refusal(s) let through, agreement 77% < the bar 85%, 8 of 55 answers out of contract
  - qwen: step_a: 9 REFERENT_OUTSIDE refusal(s) let through, agreement 78% < the bar 85%; step_c: an anchor decision Grok passed is failed
- coherence_verdict (clips_alone, coherence, hook): none; Grok as the second family (fewer than two Heimdall families pass)
  - deepseek: clips_alone: agreement 62% < the bar 79%
  - glm: clips_alone: agreement 52% < the bar 79%, 49 of 80 answers out of contract; coherence: 2 of 18 answers out of contract; hook: 2 of 6 answers out of contract
  - qwen: clips_alone: agreement 54% < the bar 79%; coherence: an anchor decision Grok passed is failed; hook: 1 of 6 answers out of contract
- fidelity_verdict (fidelity): glm; Grok as the second family (fewer than two Heimdall families pass)
  - deepseek: fidelity: an anchor decision Grok passed is failed, agreement 54% < the bar 60%, median 209 s > 120 s
  - glm: PASSES
  - qwen: fidelity: an anchor decision Grok passed is failed
- exclusion_verdict (exclusion): glm -> deepseek -> qwen; Grok last
  - deepseek: PASSES
  - glm: PASSES
  - qwen: PASSES
- speaker_verdict (speaker): none; Grok as the second family (fewer than two Heimdall families pass)
  - deepseek: speaker: only 8 decisions (< 10)
  - glm: speaker: only 9 decisions (< 10)
  - qwen: speaker: only 9 decisions (< 10)
