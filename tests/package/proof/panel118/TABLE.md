# RULING 118 (2): THE FREE PANEL ON RULING 85.1'S RECORDED GROK VERDICTS

Answers: 2933; members qwen, deepseek, minimax, gptoss, gemma, mimo; seeds (7, 8); THE RULE as in panel118.py.

| type | composition | units | no verdict | agree % | Grok self % | stricter | looser | anchors passed | REFERENT_OUTSIDE refused | takes? |
|---|---|---|---|---|---|---|---|---|---|---|
| step_a | deepseek+gemma+mimo | 716 | 647 | 86 | 85 | 5 | 5 | 10/11 | 7/8 | no: 1 anchor decision(s) failed; 1 REFERENT_OUTSIDE refusal(s) let through; 647 of 716 units with no verdict |
| step_a | gptoss+gemma+mimo | 716 | 664 | 85 | 85 | 1 | 7 | 9/10 | 2/4 | no: 1 anchor decision(s) failed; 2 REFERENT_OUTSIDE refusal(s) let through; agreement 85% < Grok's own 85%; 664 of 716 units with no verdict |
| step_a | qwen+deepseek+minimax+gemma | 716 | 317 | 84 | 85 | 40 | 22 | 42/49 | 72/80 | no: 7 anchor decision(s) failed; 8 REFERENT_OUTSIDE refusal(s) let through; agreement 84% < Grok's own 85%; 317 of 716 units with no verdict |
| clips_alone | deepseek+minimax+gemma | 91 | 61 | 80 | 83 | 3 | 3 | 3/3 | 0/0 | no: agreement 80% < Grok's own 83%; 61 of 91 units with no verdict |
| clips_alone | minimax+gemma+mimo | 91 | 36 | 78 | 83 | 5 | 7 | 4/4 | 0/0 | no: agreement 78% < Grok's own 83%; 36 of 91 units with no verdict |
| clips_alone | deepseek+minimax+gptoss+gemma | 91 | 23 | 78 | 83 | 5 | 10 | 3/4 | 0/0 | no: 1 anchor decision(s) failed; agreement 78% < Grok's own 83%; 23 of 91 units with no verdict |
| coherence | qwen+minimax+gptoss | 18 | 0 | 94 | 83 | 0 | 1 | 5/5 | 0/0 | TAKES |
| coherence | qwen+deepseek+minimax+gptoss | 18 | 0 | 94 | 83 | 0 | 1 | 5/5 | 0/0 | TAKES |
| coherence | qwen+deepseek+minimax+gptoss+gemma | 18 | 0 | 94 | 83 | 0 | 1 | 5/5 | 0/0 | TAKES |
| hook | qwen+deepseek+gptoss | 23 | 16 | 100 | n/a | 0 | 0 | 0/0 | 0/0 | no: no Grok self-agreement baseline; 16 of 23 units with no verdict |
| hook | qwen+minimax+gptoss | 23 | 8 | 100 | n/a | 0 | 0 | 0/0 | 0/0 | no: no Grok self-agreement baseline; 8 of 23 units with no verdict |
| hook | qwen+minimax+gemma | 23 | 7 | 100 | n/a | 0 | 0 | 1/1 | 0/0 | no: no Grok self-agreement baseline; 7 of 23 units with no verdict |
| fidelity | qwen+gemma+mimo | 147 | 115 | 75 | 60 | 2 | 6 | 3/3 | 0/0 | no: 115 of 147 units with no verdict |
| fidelity | qwen+minimax+gemma | 147 | 115 | 72 | 60 | 5 | 4 | 3/3 | 0/0 | no: 115 of 147 units with no verdict |
| fidelity | minimax+gemma+mimo | 147 | 115 | 72 | 60 | 3 | 6 | 3/3 | 0/0 | no: 115 of 147 units with no verdict |
