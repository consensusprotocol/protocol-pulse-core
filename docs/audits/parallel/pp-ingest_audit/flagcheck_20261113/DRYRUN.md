Re-mined by heimdall_qwen27b: 178 checked rows from 123 windows (not re-mined: {'mined by claude-opus-5-5 (not callable now)': 22}); control prompts rebuilt vs the recorded hash: {'same as recorded': 101}; failed windows: 0; rows returned again: control 146, A 127; scored on the 119 rows both arms returned.

| flag | arm | flagged | checker yes / no / unsure / unmeasured | precision | checker yes, not flagged | differs from the original |
|---|---|---|---|---|---|---|
| imperative | original | 31 | 27 / 4 / 0 / 0 | 87 % | 1 | - |
| imperative | control | 30 | 26 / 4 / 0 / 0 | 87 % | 2 | 1 |
| imperative | A | 28 | 25 / 3 / 0 / 0 | 89 % | 3 | 3 |
| accusation | original | 77 | 46 / 31 / 0 / 0 | 60 % | 1 | - |
| accusation | control | 76 | 45 / 31 / 0 / 0 | 59 % | 2 | 1 |
| accusation | A | 70 | 41 / 29 / 0 / 0 | 59 % | 6 | 11 |
| single_source_breaking | original | 18 | 11 / 7 / 0 / 0 | 61 % | 38 | - |
| single_source_breaking | control | 18 | 12 / 6 / 0 / 0 | 67 % | 37 | 4 |
| single_source_breaking | A | 26 | 19 / 7 / 0 / 0 | 73 % | 30 | 12 |

Every moment the two arms returned from these windows (not only the checked rows):

| arm | moments | imperative | accusation | single_source_breaking | any hard flag |
|---|---|---|---|---|---|
| control | 456 | 42 | 119 | 26 | 190 |
| A | 439 | 42 | 117 | 38 | 192 |

Spend $0.1773 ({'ok': 246, 'invalid': 7}), 607 s.
