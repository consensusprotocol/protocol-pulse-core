# C2 CONSENSUS — pp-selectid audit 20261116_2342 (RULING 130 (4): the coherence panel, ruling 118 (2))

Seats (Heimdall only): qwen3.8-27b (effort medium, 32,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3.
P1_OR_WORSE: qwen 0, gemma 0, mimo 1. The whole audit $0.0340 vendor-reported, Heimdall, not capped.
mimo's [P1] ("parse does not check that through_line is a string, so _line_ok's tl.strip() raises AttributeError,
uncaught"): NOT SO. _line_ok (UNCHANGED, dev53 package.py:1871) begins "tl = tl if isinstance(tl, str) else ''": a
non-string through-line reads as none and fails the bar, never raises. Run under pytest (the rigs' conftest bar), not
added to the audited files: qwen answering "through_line": 123 at both seeds: no exception, both its answers fail the
bar, the panel's other 4 of 6 pass: ok True; all six sound: ok True. mimo's [P2] (the hook's slot left out when the hook
has no own rating): the single rater's path does the same, and the verdict fails closed there (ruling 61). No change.
CLEARED. dev53: mutations P1-P8 8 of 8 killed after a control run; 40 suite files by exit code, 863 tests.
