# gemma-4-31b-it (google/gemma-4-31b-it) 64 s finish=stop usage in 6023 / out 881 usd_reported=0.000296 usd~0.031 (upper-bound price)

The code change is a minimal string update to align the `STAND_ALONE_NOTE` constant with RULING 120.

1.  **Ruling Compliance**: The string in `pipeline/package_pin.py` is updated from `"stand-alone affirmed on the calibrated floor (3.0)"` to `"a clip passed stand-alone on the calibrated bar"`. This matches the verbatim requirement of RULING 120 (no leading capital, no trailing full stop).
2.  **Scope**: The diff is limited strictly to this constant and the corresponding assertions in `tests/package/test_medley.py`. No logic, thresholds (the 3.0 floor remains), or seals were modified.
3.  **Test Coverage**: `TestRuling119StandAloneFloor` is updated to ensure the new string is correctly applied to the `moments_package` and the resulting pin.

P1_OR_WORSE: 0