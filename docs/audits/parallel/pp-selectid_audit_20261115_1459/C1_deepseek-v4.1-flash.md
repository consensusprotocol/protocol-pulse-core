# deepseek-v4.1-flash (deepseek/deepseek-v4.1-flash) 267 s finish=stop usage in 8737 / out 15028 usd_reported=0.003337 usd~0.252 (upper-bound price)

[P1] `hook_bar.bar()` accepts non-finite floats for `valid_h` (e.g. `NaN`, `Infinity`, `-Infinity`) and arbitrarily large numbers. `type(vh) in (int, float)` and `vh <= 0` do not reject `float('nan')` or `float('inf')`; `timedelta(hours=vh)` then raises `ValueError`/`OverflowError` instead of returning a clean refusal. This violates M12 fail-closed (an exception should reject, but it must not crash the build) and can take down a build from a corrupt calibration file. Fix: require `math.isfinite(vh)` and bound `vh` to a safe maximum (e.g. `timedelta.max` in hours). Add tests for `NaN`, `inf`, `-inf`, and `1e308`.

[P2] Test coverage for `valid_h` is incomplete. The new test checks `0`, `-1`, `"24"`, and `True`, but not non-finite floats or huge numbers. Add the cases above to `test_a_calibration_lasts_as_long_as_its_own_valid_h_says`.

[P3] The `valid_h` type check `type(vh) not in (int, float)` correctly rejects `bool` (since `type(True) is bool`), but the intent is non-obvious. A comment or `isinstance(vh, bool) or not isinstance(vh, (int, float))` would be clearer.

[P3] The `valid_h_note` string in `hook_calibration.json` is long and duplicates the module docstring. Consider moving it to a comment or a separate doc to keep the sealed JSON minimal.

[P2] The live bar now carries an extra `"valid_h"` key. If any consumer of `_live_bar()` performs a strict schema check or equality comparison on the returned dict, this could break. No such consumer is shown in the diff, but it is worth confirming.

[P3] The `bar()` docstring says “and is within its own ‘valid_h’ (null: no expiry)”, but the function also refuses a missing `valid_h`. The docstring could mention that a missing key is refused.

P1_OR_WORSE: 1