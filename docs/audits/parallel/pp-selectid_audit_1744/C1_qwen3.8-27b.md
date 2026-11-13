# qwen3.8-27b (qwen/qwen3.8-27b) 76 s finish=stop usage in 23588 / out 1594 usd~0.095 (upper-bound price)

# Audit: pp-selectid-1744 (Lock Pre-check / Rulings 68 & 72)

## P0 Findings (Blockers)

**None found.** The implementation correctly implements the "fail-closed" requirements for the lock pre-check.

## P1 Findings (Major)

**None found.**

## P2 Findings (Minor / Observations)

### 1. `lock_precheck.py`: Potential `KeyError` in `decide()` for `adopt_spoken`
**File:** `pipeline/lock_precheck.py` (lines 140-143 in diff, approx line 140 in file)
**Scenario:** If the integrator returns `outcome: "adopt_spoken"` but the `spoken_text` field is missing or `None`, the code correctly returns an error. However, if `spoken_text` is present but `seg["approved_text"]` is missing (which shouldn't happen as `segments_of` always sets it, but defensive coding is good), `AT.diff` might behave unexpectedly.
**Verification:** The code checks `if not isinstance(spoken, str) or not spoken.strip(): return {"verdict": "error"...}`. This is safe. `seg["approved_text"]` is guaranteed by `segments_of`. No action needed.

### 2. `package.py`: `lock_check` invocation in No-Voice path
**File:** `pipeline/package.py` (lines 277-280 in diff)
**Scenario:** In the no-voice fallback path, `lock_check(order)` is called. If `lock_check` returns `ok: False` due to a `hold`, the code returns `None` (no package). This is correct. If it returns `ok: False` due to an `error` (no verdict), the code also returns `None`.
**Observation:** The comment says "no verdict is never a pass". The code `if nv_pre is not None and not nv_pre.get("ok"): return None` handles both `hold` and `error` by refusing the package. This aligns with Law L-m (Fail Closed).

### 3. `package.py`: `lock_stop` logic
**File:** `pipeline/package.py` (lines 321-324 in diff)
**Scenario:** When `pre.get("error")` is true (no verdict), `out["lock_stop"]` is set to `True`. This stops the search for *this angle*. The outer loop condition `not out.get("lock_stop")` ensures the angle loop breaks.
**Verification:** This prevents the system from trying other line-ups for the same angle if the lock service is down or timing out, which is a reasonable "fail fast" behavior to avoid wasting budget on a broken dependency. It does *not* stop the entire build, just the current angle's search. This seems correct.

### 4. `lock_precheck.py`: `answer()` matching logic
**File:** `pipeline/lock_precheck.py` (lines 85-92 in diff)
**Scenario:** The `_matches` function checks `e.get("rules") == RULES`. `RULES` is `"ruling 17 + ruling 72"`.
**Verification:** The contract states: "Take the newest entry with rules == 'ruling 17 + ruling 72'". The code does exactly this. It also checks `win == [seg["start"], seg["end"]]`. `seg["start"]` and `seg["end"]` are rounded to 3 decimal places in `segments_of`. The result file name uses `%.3f`. The JSON entry's `window` is expected to be a list of two floats. The code rounds the window values to 3 decimal places before comparison: `win = [round(float(w[0]), 3), round(float(w[1]), 3)]`. This ensures floating point precision issues don't cause mismatches. This is robust.

### 5. `lock_precheck.py`: `send()` atomicity
**File:** `pipeline/lock_precheck.py` (lines 112-125 in diff)
**Scenario:** The code writes to a `.tmp` file and then renames it to `.json`.
**Verification:** `os.rename` is atomic on POSIX systems (Linux). This ensures the integrator never sees a partially written request file. The code also checks `if os.path.exists(final) or os.path.exists(tmp): raise FileExistsError`. This prevents overwriting an existing request, which aligns with the contract "answers each name and content once".

### 6. `package_pin.py`: `attested` field in seal
**File:** `pipeline/package_pin.py` (lines 373-376 in diff)
**Scenario:** The `attested` field is added to the pin segment.
**Verification:** The `seal()` function is not modified. The `attested` field is part of the segment dictionary, so it will be included in the SHA256 hash calculation for the pin. This is correct: the "attested" record is part of the sealed state. If the text changes, the `attested` record changes, and the pin hash changes.

### 7. `test_medley.py`: `lock_stub`
**File:** `tests/package/test_medley.py` (lines 676-696 in diff)
**Scenario:** The test stub `lock_stub` simulates the `lock_check` function.
**Verification:** The stub correctly returns a dictionary with `ok`, `request_id`, `segments`, and `error`. The `segments` list contains dictionaries with `verdict`, `outcome`, `why`, and `entry`. This matches the expected return type of `lock_precheck.check`.

## SHIP: Yes

The code correctly implements the Rulings 68 and 72 requirements:
1.  **No pin sealed with unpassed text:** `lock_precheck.apply` refuses to apply if the pre-check didn't pass or if the segments don't match. `package.build` only calls `apply` if `lock_check` returned `ok: True`. The driver's `pin_problems` check adds a final layer of defense.
2.  **Adopted text within Ruling 67 class:** `lock_precheck.decide` uses `AT.carry_class` to verify that any differences between `spoken_text` and `approved_text` are in the allowed class (function words, immediate repetitions). If not, it returns `hold`.
3.  **No verdict is never a pass:** `lock_precheck.decide` returns `error` for `None` or unknown outcomes. `package.build` treats `error` as a stop condition (`lock_stop`), preventing any package from being created.
4.  **Matching rules:** The `answer` function correctly filters for `rules == "ruling 17 + ruling 72"`, matches the window (rounded to ms), role, approved text, and trim fields. It selects the newest entry by `at` timestamp.
5.  **Request writing:** Atomic write via `.tmp` + `rename`. Never overwrites existing requests.
6.  **No changes to other gates:** The changes are isolated to the lock pre-check logic and the `package.build` flow. No other gate thresholds or logic are modified. `seal()` is unchanged.