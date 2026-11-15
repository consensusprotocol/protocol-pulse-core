# C1 CONSENSUS — pp-selectid audit 20261115_1459 (ruling 115: the calibration's expiry is the file's own)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and deepseek-v4.1-flash (1; glm-5.3-flash's ruling-99 breaker is open, so
the driver took deepseek); they disagree on a P1, so Grok was asked (0). Cycle 1: $0.0278 vendor-reported.

THE P1 (deepseek): "valid_h NaN / Infinity / -Infinity / a huge number: type(vh) in (int, float) and vh <= 0 let them
through, and timedelta(hours=vh) then RAISES (ValueError / OverflowError): a corrupt calibration would crash a build
instead of refusing it". REAL (Python's json.load reads NaN and Infinity by default). FIXED: valid_h must be an
int / float with 0 < valid_h <= MAX_VALID_H (24 x 366 hours); every comparison with NaN is false and +-Infinity is
outside the range, so neither reaches timedelta. And the same class one line up, found while fixing it: a floor of
Infinity made int() raise OverflowError, which the floors' except did not catch; it is caught now (a NaN floor already
raised ValueError, caught). Tests: valid_h NaN, Infinity, -Infinity and 1e300 are refused without raising; a floor
of Infinity or NaN is refused without raising. Mutations (after a control run): no upper bound on valid_h, and
OverflowError not caught: both KILLED; with V1-V4: 6 of 6.

NOT CHANGED:
- qwen "bool is a subclass of int": type(vh) is compared exactly, so True (type bool) is refused; tested.
- qwen "VALID_H referenced elsewhere?": grep over pipeline/ and tests/: no other reference.
- deepseek P2 "the live bar carries a new key valid_h": its consumers read named keys (hook_own, hook_bar_mark, the
  build line); none compares the dict whole.
- Grok P3 "law L-m is not in the governing list": it is this project's law (no verdict is never a pass), cited
  across the package code; the audit package's list is the gospel excerpt.
- Grok P2 "the diff is 70 % tests and docstrings": kept together: the behaviour and its proof land as one change.
