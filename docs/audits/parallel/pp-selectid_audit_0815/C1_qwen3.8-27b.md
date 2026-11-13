# qwen3.8-27b (qwen/qwen3.8-27b) 29 s finish=stop usage in 9654 / out 1126 usd~0.046 (upper-bound price)

# Code Audit: pp-selectid-0815 (Ruling 52 Implementation)

## Findings

### P0: None
The implementation correctly enforces the "fail closed" requirement for malformed inputs. The contract validation in `pipeline/package.py` (lines 67-73 of the diff) ensures that any deviation from the expected JSON structure (missing keys, wrong types, out-of-range values) results in `ok=False` and `measured=False`. The derived hook rating is strictly computed as `min(v["hook"][k] for k in HOOK_PARTS)` (line 78), preventing free-form or missing ratings.

### P1: None
The logic for the hook's derived rating and the pass/fail condition is sound.
1.  **Hook Rating:** The hook is no longer rated on the through-line. It is rated on `scroll`, `alone`, and `setup`. The final rating is the minimum of these three. This matches the "derived, not free-form" instruction and the stated choice K1 (min formula).
2.  **Pass Condition:** The `ok` variable (line 81) checks `min(v["clips"].values()) >= COHERENCE_MIN`. Since `v["clips"]` now includes the derived hook rating (injected at line 78), the hook must meet the bar (4) via its derived score. The clips after the hook are rated on the through-line as before.
3.  **Joins:** The join logic is unchanged. `flagged` is computed from `v["joins"]` (line 80), and the pass condition still limits flagged joins to `LY_MAX_BRIDGES` (1).

### P2: Observations / Minor Notes

1.  **Prompt Clarity (Line 24):** The prompt explicitly states "For each clip AFTER the hook, rate 1-5...". This is clear. The JSON template (line 30) uses `clip_keys` which is generated from `labs[1:]` (line 61). This correctly excludes the hook from the through-line rating keys in the expected output.
2.  **Test Coverage (Lines 132-149):** The new test `test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts` thoroughly verifies:
    *   A low part score (3) leads to a derived hook score of 3 and a FAIL.
    *   All parts at 4 lead to a derived hook score of 4 and a PASS.
    *   The prompt contains the specific new instructions.
    *   The prompt does *not* ask for a through-line rating for the hook.
    *   A low clip score (3) still leads to a FAIL.
3.  **Out-of-Contract Tests (Lines 151-166):** The tests correctly verify that:
    *   Missing hook parts fail.
    *   Out-of-range hook parts (6) fail.
    *   String hook parts ("5") fail.
    *   Including the hook in the `clips` dict (which should only contain `labs[1:]`) fails.
    *   Missing the `hook` key entirely fails.
4.  **Downstream Compatibility:** The verdict structure `v["clips"]` still contains the key `"hook"` (injected at line 78). This ensures that any downstream code reading `verdict["clips"]["hook"]` for weak-segment detection or ruling 41's swap logic will continue to work without modification, as stated in the background.

## Verification of Specific Checks

*   **Hook can no longer pass/fail on through-line rating:** Verified. The through-line rating is only requested for `labs[1:]`. The hook's rating is derived from `scroll/alone/setup`.
*   **Clips rated exactly as before:** Verified. The prompt and validation for `labs[1:]` remain consistent with the previous behavior (1-5 int, through-line relevance).
*   **Derived rating cannot be free-form/missing:** Verified. The code explicitly calculates `min(...)` and validates the input parts are ints 1-5.
*   **Malformed reply is never a pass:** Verified. The `try/except` block and the strict `if not isinstance...` checks ensure any malformed input returns `False, {..., "measured": False}`.
*   **Joins unchanged:** Verified. The join validation and `flagged` logic are identical to the previous version.
*   **Build loop sees hook rating under "hook":** Verified. `v["clips"]` is updated to include `labs[0]` (the hook) with the derived value.

## SHIP: yes

The diff correctly implements Ruling 52. The hook is now evaluated on its specific job (scroll, alone, setup) with a derived minimum score, while the rest of the medley logic (through-line for clips, joins, pass/fail thresholds) remains intact. The tests are comprehensive and cover the new behavior and edge cases. No violations of the Governing Laws are apparent in this specific diff (which focuses on the editorial/selection logic rather than the audio/video rendering gates).