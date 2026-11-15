# RULING 113 (6): CLIPS-ALONE, A SECOND ASKING (report only)

Measured 2026-11-15T18:25:29+00:00 (UTC). 14 builds that the clips-alone verdict ended after a hook had passed; 61 distinct failing line-ups; 34 asked a second time (Grok, the same prompt and seed, unrecorded: no cached verdict answered); 2 of them passed. The other 27 were not asked: the cap ($0.30; our stop at $0.27 on reported spend). Spent $0.2747 (vendor-reported).

A line-up passes when every clip after the hook rates >= 4, a through-line is stated and at most one join needs a bridge (package.medley as it stood then: the hook's rating was inside the min).

| build | failing line-ups | asked again | passed on the second asking |
|---|---|---|---|
| ledger_20261113_163106 | 8 | 6 | none |
| ledger_20261113_172217 | 7 | 5 | none |
| ledger_20261113_180515 | 8 | 3 | f29c27fb / 9c146121 / c7646b4e |
| ledger_20261113_210211 | 7 | 6 | none |
| ledger_20261113_212949 | 15 | 10 | 82473bb0 / c083afe2 / c7646b4e |
| ledger_20261114_011253 | 2 | 1 | none |
| ledger_20261114_021501 | 7 | 5 | none |
| ledger_20261114_023757 | 7 | 5 | none |
| ledger_20261114_025021 | 7 | 5 | none |
| ledger_20261114_031425 | 2 | 0 | none |
| ledger_20261114_051151 | 2 | 1 | none |
| ledger_20261114_183413 | 6 | 2 | none |
| ledger_20261114_192056 | 4 | 1 | none |
| ledger_20261114_230148 | 1 | 0 | none |

## Every failing line-up (first asking -> second asking)

- ledger_20261113_163106: f29c27fb / c3be6f1c / c083afe2 / 2e77a0a7: hook 4, clip_01 4, clip_02 4, clip_03 2; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_163106: f29c27fb / c3be6f1c / c8827879 / 68372751: hook 3, clip_01 5, clip_02 3, clip_03 2; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03'] -> fails: clip_01 5, clip_02 3, clip_03 2; flagged ['clip_02 -> clip_03']
- ledger_20261113_163106: f29c27fb / c3be6f1c / e70dcc2b / 45c3bb5f: hook 4, clip_01 5, clip_02 4, clip_03 3; flagged ['clip_02 -> clip_03'] -> fails: clip_01 5, clip_02 4, clip_03 3; flagged ['clip_02 -> clip_03']
- ledger_20261113_163106: f29c27fb / c3be6f1c / e70dcc2b / 5f40984b: hook 3, clip_01 5, clip_02 4, clip_03 3; flagged ['clip_02 -> clip_03'] -> fails: clip_01 4, clip_02 3, clip_03 4; flagged none
- ledger_20261113_163106: f29c27fb / c3be6f1c / e70dcc2b / 7376e34f: hook 4, clip_01 5, clip_02 4, clip_03 3; flagged ['clip_02 -> clip_03'] -> fails: clip_01 5, clip_02 4, clip_03 3; flagged ['clip_02 -> clip_03']
- ledger_20261113_163106: f29c27fb / c3be6f1c / e70dcc2b / cbd78db0: hook 3, clip_01 5, clip_02 4, clip_03 5; flagged ['clip_02 -> clip_03'] -> fails: clip_01 5, clip_02 2, clip_03 4; flagged ['clip_02 -> clip_03']
- ledger_20261113_163106: f29c27fb / 8072c7bc / 2e77a0a7: hook 2, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_163106: f29c27fb / a5f5a1d5 / c3be6f1c: hook 4, clip_01 4, clip_02 5; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 3, clip_02 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_172217: 82473bb0 / a45d26b8 / c3be6f1c / c8827879: hook 4, clip_01 4, clip_02 5, clip_03 3; flagged ['hook -> clip_01'] -> fails: clip_01 4, clip_02 4, clip_03 3; flagged none
- ledger_20261113_172217: 82473bb0 / a45d26b8 / c3be6f1c / 95d20143: hook 4, clip_01 4, clip_02 5, clip_03 3; flagged none -> fails: clip_01 4, clip_02 5, clip_03 3; flagged none
- ledger_20261113_172217: 82473bb0 / a45d26b8 / c3be6f1c / c7646b4e: hook 4, clip_01 4, clip_02 5, clip_03 3; flagged none -> fails: clip_01 4, clip_02 5, clip_03 3; flagged none
- ledger_20261113_172217: 82473bb0 / a45d26b8 / c3be6f1c / 06f73bef: hook 4, clip_01 3, clip_02 5, clip_03 1; flagged none -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_172217: 82473bb0 / a5f5a1d5 / c3be6f1c / 2e77a0a7: hook 4, clip_01 4, clip_02 5, clip_03 2; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_172217: 82473bb0 / a5f5a1d5 / f5f005b9 / d6a09337: hook 4, clip_01 5, clip_02 2, clip_03 4; flagged ['hook -> clip_01', 'clip_02 -> clip_03'] -> fails: clip_01 4, clip_02 2, clip_03 3; flagged ['clip_02 -> clip_03', 'hook -> clip_01']
- ledger_20261113_172217: 82473bb0 / a5f5a1d5 / e70dcc2b / 5f40984b: hook 4, clip_01 4, clip_02 3, clip_03 5; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 3, clip_02 4, clip_03 4; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03', 'hook -> clip_01']
- ledger_20261113_180515: f29c27fb / 6058ee58 / a45d26b8: hook 4, clip_01 3, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 3, clip_02 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_180515: f29c27fb / 95d20143 / a5f5a1d5: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_180515: f29c27fb / 9c146121 / c7646b4e: hook 4, clip_01 4, clip_02 3; flagged none -> PASSES: clip_01 4, clip_02 4; flagged none
- ledger_20261113_180515: f29c27fb / 9c146121 / 06f73bef: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_180515: f29c27fb / f5f005b9 / c3be6f1c: hook 4, clip_01 2, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 1, clip_02 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_180515: f29c27fb / da116d5d / c8827879: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_180515: f29c27fb / afe8101a / 2e77a0a7: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_180515: f29c27fb / 68372751 / d6a09337: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / a5f5a1d5 / 2e77a0a7: hook 4, clip_01 4, clip_02 2; flagged ['hook -> clip_01'] -> fails: clip_01 4, clip_02 3; flagged ['hook -> clip_01']
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / a5f5a1d5 / 95d20143: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / f5f005b9 / 6058ee58: hook 4, clip_01 2, clip_02 4; flagged ['clip_01 -> clip_02'] -> fails: clip_01 2, clip_02 4; flagged ['clip_01 -> clip_02']
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / da116d5d / 6058ee58: hook 4, clip_01 3, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 3, clip_02 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / afe8101a / c8827879: hook 4, clip_01 4, clip_02 3; flagged none -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / 6058ee58 / a5f5a1d5 / 2e77a0a7: hook 4, clip_01 3, clip_02 4, clip_03 2; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_210211, ledger_20261113_212949: 82473bb0 / 95d20143 / c8827879 / c7646b4e: hook 4, clip_01 3, clip_02 4, clip_03 5; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> fails: clip_01 2, clip_02 5, clip_03 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261113_212949: 82473bb0 / 9c146121 / f5f005b9 / 06f73bef: hook 4, clip_01 5, clip_02 2, clip_03 1; flagged none -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_212949: 82473bb0 / 9c146121 / afe8101a / c6e96bc6: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_212949: 82473bb0 / da116d5d / e70dcc2b / d6a09337: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_212949: 82473bb0 / 68372751 / 45c3bb5f / a693c226: hook 4, clip_01 3, clip_02 4, clip_03 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03', 'hook -> clip_01']
- ledger_20261113_212949: 82473bb0 / cbd78db0 / c083afe2 / a693c226: hook 4, clip_01 3, clip_02 4, clip_03 2; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261113_212949: 82473bb0 / c083afe2 / c7646b4e: hook 4, clip_01 4, clip_02 3; flagged none -> PASSES: clip_01 4, clip_02 4; flagged none
- ledger_20261113_212949: 82473bb0 / c083afe2 / 95d20143: hook 4, clip_01 4, clip_02 2; flagged ['clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02']
- ledger_20261113_212949: 82473bb0 / c083afe2 / 6058ee58: hook 4, clip_01 4, clip_02 3; flagged none -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_011253: f063cce3 / 7d8a34d1 / e05b34a6: hook 4, clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02']
- ledger_20261114_011253: f063cce3 / b8271826 / e05b34a6: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / a5f5a1d5 / 7004b98d: hook 4, clip_01 4, clip_02 3; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / a5f5a1d5 / 6058ee58: hook 4, clip_01 4, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 4; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / 6058ee58 / a5f5a1d5: hook 4, clip_01 4, clip_02 3; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02']
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / 6058ee58 / 7004b98d / d6a09337: hook 4, clip_01 5, clip_02 4, clip_03 3; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> fails: clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03', 'hook -> clip_01']
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / 6058ee58 / b8271826 / a5f5a1d5: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / 7d8a34d1 / 30b3768c / 9f9457fd: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_021501, ledger_20261114_023757, ledger_20261114_025021: f063cce3 / a5f5a1d5 / 7d8a34d1: hook 4, clip_01 3, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 5; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_031425: f063cce3 / 7004b98d / 7a033059 / 9f9457fd: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_031425: f063cce3 / 7004b98d / e05b34a6: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_051151: f063cce3 / 11df638c / 7004b98d / 1ddf18ce: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_051151: f063cce3 / 11df638c / 7004b98d / 7e3e474c: hook 4, clip_01 2, clip_02 4, clip_03 5; flagged ['clip_01 -> clip_02'] -> fails: clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03']
- ledger_20261114_183413, ledger_20261114_192056: 22018cf6 / b3ad2b83 / ec4c0ff4 / 704fa6e1: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_183413: 704fa6e1 / eb402a21 / 30075b15 / cb80340f: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_183413: 704fa6e1 / b3ad2b83 / ec4c0ff4 / 22018cf6: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_183413: 933f9d33 / eb402a21 / a49592a9: hook 4, clip_01 5, clip_02 4; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_183413: 933f9d33 / eb402a21 / 30075b15: hook 4, clip_01 4, clip_02 3; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 4, clip_02 3; flagged ['clip_01 -> clip_02', 'hook -> clip_01']
- ledger_20261114_183413: 933f9d33 / eb402a21 / 704fa6e1: hook 4, clip_01 1, clip_02 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_192056: 704fa6e1 / b3ad2b83 / 30075b15 / cb80340f: hook 4, clip_01 4, clip_02 3, clip_03 5; flagged ['hook -> clip_01', 'clip_01 -> clip_02'] -> fails: clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03', 'hook -> clip_01']
- ledger_20261114_192056: 704fa6e1 / b3ad2b83 / ec4c0ff4 / cb80340f: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_192056: 704fa6e1 / eb402a21 / 5725aeda / a49592a9: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['hook -> clip_01', 'clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))
- ledger_20261114_230148: 22018cf6 / 408ef969 / b3ad2b83 / ec4c0ff4: hook 4, clip_01 1, clip_02 1, clip_03 1; flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03'] -> not asked (the cap: $0.2747 spent (stop $0.27))

## Reading

- A second asking turned 2 of 34 failing line-ups into a pass (6 %). Of the 32 that failed again, 25 failed on a clip that had failed the first time too, 5 on other clips only, and 2 on joins or the through-line only: mostly the same clip, not one unlucky answer.
- 1 of the 61 failed ONLY on the hook's slot (the hook's own rating under 4 inside the min; every later clip >= 4; at most one flagged join): ledger_20261113_163106 f29c27fb / c3be6f1c / e70dcc2b / cbd78db0 (hook 3, clip_01 5, clip_02 4, clip_03 5). Ruling 115 judges that slot by the calibrated bar instead; it would not have rescued the others.
- No routing or bar change follows from this report (report only).
