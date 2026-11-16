# gemma-4-31b-it (google/gemma-4-31b-it) 438 s finish=stop usage in 9322 / out 4812 usd_reported=0.000886 usd~0.100 (upper-bound price)

The code implements RULING 123 (2) to allow a hook to open a package as 16:9-only if its only refusal is the 9:16 crop. However, there is a critical logic contradiction between the selection seal and the validation check.

### [P0] Logic Contradiction: Seal Disables Exception
The feature is designed to seal a package as 16:9-only and then excuse that hook from the final layout block. However, the implementation of the excuse is disabled by the seal itself.

1.  **The Seal**: In `pipeline/package.py` (line 32), when a 16:9-only hook is identified, the code seals the record: `m["visual"] = dict(m["visual"], formats=["16x9"])`.
2.  **The Excuse**: Later in `build()`, the layout check (lines 54 and 64) calls `opens_16x9(m)` to determine if the hook should be excused from Ruling 93.
3.  **The Failure**: `opens_16x9(m)` (line 15) requires `bool(VP.crop_only(v))` to be `True`.
4.  **The Block**: In `pipeline/visual_pin.py` (line 84), `crop_only(rec)` explicitly returns `None` if the record already has formats assigned: `if ... or (formats(rec) and not RENDER_16X9_ONLY): return None`.

**Result**: Because the record is sealed with `formats=["16x9"]` at line 32, `VP.crop_only` will always return `None` during the final layout check. This makes `opens_16x9` return `False`, which causes the layout check to see the Ruling 93 refusal and return `None` for the entire `build()` call. The feature will not work; any package attempting to use a 16:9-only hook will fail the final quality gate and produce no output.

### [P2] Redundant Check in `opens_16x9`
In `pipeline/package.py` (line 15), `opens_16x9` checks `v.get("formats") == ["16x9"]`. This is redundant because the `sixteen_nine_only` flag is only set in `build()` at the exact same time the `formats` list is set to `["16x9"]`. While not a bug, it adds unnecessary complexity to a critical path.

### [P3] Test Coverage Gap
The tests in `tests/package/test_medley.py` may pass if the `Rig` mock does not fully execute the final `vbad` layout check in `package.build()` or if it uses a different version of `visual_pin.py`. The test `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only` should be verified against the actual `pipeline/package.py` logic to ensure it catches the [P0] failure.

P1_OR_WORSE: 1