# Ruling 110: Heimdall candidates on ruling 85.1's recorded Grok verdicts

Built 2026-11-15 01:29 EST from 638 (record, model) rows. dsv41unc = deepseek/deepseek-v4.1-flash-1017-uncensored; dsv4 = deepseek/deepseek-v4-flash-0731-abliterated. In time: answered within ruling 100's deadline for that (model, verdict role) today; late: answered after it (a MISSED deadline in production), before the 300 s cut; timeout: no answer by the cut. Stricter: the candidate fails what Grok passed.

| type | model | records | in time | late | timeouts | errors | out of contract | missed | units in time | agree | stricter | looser | different | agree % in time | agree % all answers | p50 s | p90 s | ruling-100 deadline s | usd reported |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| step_a | dsv41unc | 96 | 3 | 85 | 3 | 0 | 5 | 88 | 15 | 12 | 1 | 2 | 0 | 80 | 80 | 191 | 238 | 120 | 0.1691 |
| step_a | dsv4 | 96 | 6 | 0 | 0 | 0 | 90 | 0 | 42 | 31 | 4 | 7 | 0 | 74 | 74 | 21 | 29 | 120 | 0.0379 |
| step_c | dsv41unc | 33 | 10 | 21 | 2 | 0 | 0 | 23 | 30 | 29 | 0 | 1 | 0 | 97 | 95 | 140 | 242 | 120 | 0.0356 |
| step_c | dsv4 | 33 | 31 | 0 | 0 | 0 | 2 | 0 | 95 | 85 | 8 | 2 | 0 | 89 | 89 | 3 | 5 | 120 | 0.0020 |
| clips_alone | dsv41unc | 91 | 87 | 1 | 0 | 0 | 3 | 1 | 174 | 104 | 13 | 10 | 47 | 60 | 60 | 28 | 40 | 120 | 0.0193 |
| clips_alone | dsv4 | 91 | 56 | 0 | 0 | 0 | 35 | 0 | 112 | 59 | 6 | 7 | 40 | 53 | 53 | 3 | 5 | 120 | 0.0032 |
| coherence | dsv41unc | 18 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 15 | 3 | 0 | 0 | 83 | 83 | 10 | 13 | 120 | 0.0016 |
| coherence | dsv4 | 18 | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 12 | 5 | 1 | 0 | 67 | 67 | 2 | 3 | 120 | 0.0005 |
| hook | dsv41unc | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 23 | 22 | 0 | 1 | 0 | 96 | 96 | 22 | 36 | 120 | 0.0012 |
| hook | dsv4 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 23 | 20 | 3 | 0 | 0 | 87 | 87 | 4 | 6 | 120 | 0.0003 |
| fidelity | dsv41unc | 39 | 21 | 18 | 0 | 0 | 0 | 18 | 68 | 40 | 23 | 5 | 0 | 59 | 54 | 108 | 165 | 120 | 0.0352 |
| fidelity | dsv4 | 39 | 33 | 0 | 0 | 0 | 6 | 0 | 123 | 97 | 10 | 16 | 0 | 79 | 79 | 6 | 9 | 120 | 0.0037 |
| exclusion | dsv41unc | 27 | 27 | 0 | 0 | 0 | 0 | 0 | 27 | 24 | 3 | 0 | 0 | 89 | 89 | 6 | 12 | 120 | 0.0028 |
| exclusion | dsv4 | 27 | 25 | 0 | 0 | 0 | 2 | 0 | 25 | 25 | 0 | 0 | 0 | 100 | 100 | 2 | 4 | 120 | 0.0012 |
| speaker | dsv41unc | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 9 | 7 | 0 | 2 | 0 | 78 | 78 | 33 | 81 | 120 | 0.0035 |
| speaker | dsv4 | 9 | 8 | 0 | 0 | 0 | 1 | 0 | 8 | 8 | 0 | 0 | 0 | 100 | 100 | 3 | 4 | 120 | 0.0007 |

## The deepseek-v4.1-flash we run, on the same records (ruling 85.1's rows: 300 s cut, 01:06 ET Nov 14, under that night's 429 storms)

| type | records | agree % all answers | p50 s | p90 s | timeouts |
|---|---|---|---|---|---|
| step_a | 56 | 74 | 265 | 290 | 16 |
| step_c | 33 | 96 | 198 | 262 | 6 |
| clips_alone | 58 | 62 | 69 | 121 | 0 |
| coherence | 18 | 89 | 21 | 51 | 0 |
| hook | 6 | 96 | 43 | 53 | 0 |
| fidelity | 39 | 54 | 204 | 276 | 2 |
| exclusion | 27 | 93 | 7 | 18 | 0 |
| speaker | 9 | 88 | 86 | 119 | 0 |

## The bars of rulings 85/88/96 (replay85.passes; information only: a model moves into a verdict type only by a later ruling)

- step_a / dsv41unc: not: an anchor decision Grok passed is failed; 23 REFERENT_OUTSIDE refusal(s) let through; agreement 80% < the bar 85%; median 192 s > 120 s
- step_a / dsv4: not: 4 REFERENT_OUTSIDE refusal(s) let through; agreement 74% < the bar 85%; 90 of 96 answers out of contract
- step_c / dsv41unc: not: an anchor decision Grok passed is failed; median 143 s > 120 s
- step_c / dsv4: not: an anchor decision Grok passed is failed
- clips_alone / dsv41unc: not: an anchor decision Grok passed is failed; agreement 60% < the bar 79%
- clips_alone / dsv4: not: an anchor decision Grok passed is failed; agreement 53% < the bar 79%; 35 of 91 answers out of contract
- coherence / dsv41unc: not: an anchor decision Grok passed is failed
- coherence / dsv4: not: an anchor decision Grok passed is failed; agreement 67% < the bar 75%
- hook / dsv41unc: MEETS THE BARS
- hook / dsv4: MEETS THE BARS
- fidelity / dsv41unc: not: an anchor decision Grok passed is failed; agreement 54% < the bar 60%
- fidelity / dsv4: not: 6 of 39 answers out of contract
- exclusion / dsv41unc: MEETS THE BARS
- exclusion / dsv4: MEETS THE BARS
- speaker / dsv41unc: not: only 9 decisions (< 10)
- speaker / dsv4: not: only 8 decisions (< 10); 1 of 9 answers out of contract

## The baseline: Grok against Grok (replay85.grok_self, from every recorded Grok answer)

| type | unit pairs | agree % |
|---|---|---|
| step_a | 1084 | 85 |
| clips_alone | 14 | 79 |
| fidelity | 15 | 60 |
