# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 8949 / out 205 usd~0.050 (upper-bound price)

<critical> vo_fidelity.py:39 (without_manifest_date) + :62/:72/:81 (fact_numbers calls): concrete input "Pulse Check for 2026-11-12." (manifest={"date": "2026-11-12", ...}) now yields no NUMBER/NEEDS_SOURCE after date removal (see added test lines 102-103, 112); previously triggered per background. Violates LAW 20/M2 ("never change what a check accepts to make a render pass; never reclassify a failing gate as a false positive").
<medium> ledger_build.py:24 (b - a > SNAP_MAX_S): with new 35.0 ceiling + test input of 75-word / 22.5 s snap (test_ledger_build.py:143), reanchor now returns non-None (line 144); facts confirm medley usable() still drops at 20 s but cannot verify downstream hook/clip/scorer assumptions from diff+facts alone.

SHIP: no