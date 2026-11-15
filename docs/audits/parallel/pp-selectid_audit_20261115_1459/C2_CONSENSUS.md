# C2 CONSENSUS — pp-selectid audit 20261115_1459 (ruling 115: the calibration's expiry is the file's own)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of its 16,000 output tokens with no answer
(finish=length), so the driver asked Grok (0). Cycle 2: $0.0246; the audit $0.0524 vendor-reported. No P1; no third
cycle.

Both answering reviewers checked cycle 1's fix: valid_h must be a number in (0, 24 x 366] hours, which NaN and
+-Infinity fail (every comparison with NaN is false), so neither reaches timedelta; a floor of Infinity no longer
raises (OverflowError caught); bool is refused (type compared exactly). Mutations: 6 of 6 killed after a control run.

P2s noted, not changed: the non-finite floor test exercises the parse's except path (a finite floor under 3 is the
separate "a floor under 3" test); the live bar's valid_h key is read by name only.

FINAL DIFF: FINAL.diff (written at landing).
