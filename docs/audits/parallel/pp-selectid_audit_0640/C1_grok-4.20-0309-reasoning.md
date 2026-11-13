# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 12428 / out 652 usd~0.078 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:54 (build): second_screen is called on all CUTTABLE moments after hook-onset but before the 3-channel check and angle_write. The subsequent `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}` filter guarantees no moment reaches the angle prompt (or any later lineup) without two passing verdicts; the test at test_medley.py:226-235 verifies this both in the prompt content and in medley_calls.
- pipeline/package.py:74 (off_writers): after angle_write and after every write (lines 82, 91), a_by[mid] is overwritten with the first verdict from a_two whose backend is outside the accumulating writers_v/writers_f sets. When the writer is xai:grok the Heimdall verdict is selected (and vice-versa); the rig test at test_medley.py:249-253 confirms no re-screen occurs in the Heimdall-in-time case and that the final a_seen backends match the off-writer choice.
- pipeline/package.py:110 (re-screen block): if prescreen returns no verdict or any failure for a stale clip, it is added to `bad`, recorded in out["prescreen"]["rescreen_failed"], added to both `dropped` and `doomed`, and excluded from every subsequent angle/line-up. swap_lineup is called on exactly those bad mids only; the test at test_medley.py:262-270 exercises the exact 05:48 failure mode (one clip fails re-screen → single swap → new lineup re-judged on clips-alone before next write) and confirms the final package contains only the surviving clips.
- pipeline/package.py:34 (second_screen): explicit fail-closed paths for no a2, fails.get(mid), same-vendor/family backend, or unknown first backend produce STEP_A_UNAVAILABLE / STEP_A_SAME_VENDOR / STEP_A_UNKNOWN_BACKEND entries; test at test_medley.py:282-304 verifies the grouping, the same-vendor detection, and that these never become passes.
- pipeline/package.py:25 (ThreadPoolExecutor): jobs are independent (per first-verdict vendor/family group), submitted with store=None, results collected sequentially via .result() after all futures complete; no mutable state (two/fail/a_by/cleared) is written inside the worker threads. No infinite loop, double-counting of moments, or inconsistent a_two/a_by mutation is present in the diff.
- tests/package/test_medley.py:209 (Rig.prescreen): the canned prescreen respects the avoid-vendor/family contract, can simulate a third vendor for the “both real vendors are writers” case, and drives all new test methods; the existing 78 tests remain green and the other test suites are stated unchanged.

All checked laws (L-m, L-x, L-j, item 44, item 45, fail-closed on missing verdict, dynamic off-writer selection after writes) are satisfied by the diff. No behaviour change for the Heimdall-in-time angle path is introduced beyond the guaranteed off-vendor verdict.

**SHIP: yes**