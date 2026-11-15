# qwen3.8-27b (qwen/qwen3.8-27b) 77 s finish=stop usage in 14767 / out 2610 usd_reported=0.003900 usd~0.083 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 105 implementation). Below are my findings based on the Governing Laws and the specific code changes.

### Findings

**1. [P1] `ruling_105_fails` fails closed on valid numeric tokens with formatting (e.g., commas)**
The function `ruling_105_fails` (lines 65-94 in `pipeline/lock_precheck.py`) enforces strict string matching for the "truncation" logic.
- **The Issue:** The check `token.startswith(r)` and the definition of `_truncation` (lines 57-62) operate on raw strings. If the lock's token is a formatted number like `"86,000"` and the second recogniser reads it as `"86,00"` (a truncation of the visual string) or `"86000"` (a different format), the logic may behave unexpectedly or fail closed.
    - Specifically, if `token` is `"86,000"` and `r` is `"86,00"`, `token.startswith(r)` is True. `_truncation` checks if the suffix `token[len(r):]` contains digits. The suffix is `"00"`, which contains digits. So `_truncation` returns `False` (it is NOT a valid truncation because the dropped part has digits). This is correct for "86,00" vs "86,000" (dropping a digit).
    - However, consider the case where the token is `"1,000"` and the reading is `"1000"`. `token.startswith("1000")` is False. So it fails.
    - Consider the case where the token is `"401k"` and the reading is `"401"`. `token.startswith("401")` is True. Suffix is `"k"`. No digits in suffix. `_truncation` returns True. This is the intended "401k" case.
    - **The Critical Gap:** The law L-g (WRITTEN FORMS) and L-k (ONE CANONICAL FORM) state that text comparisons should use `pipeline/canon.py` to handle numbers, units, and formatting. `ruling_105_fails` performs **raw string comparison** (`x != tok`, `token.startswith(r)`). It does **not** use `canon.canon_tokens` or `canon.same`.
    - If the integrator's pre-check (which uses the decoder) normalizes numbers (e.g., via canon) before storing the `token` in the record, but this side's `ruling_105_fails` expects the raw string, there is a mismatch.
    - More importantly, if the `token` in the record is `"86,000"` (with comma) and the second reading is `"86000"` (no comma, same value), `token.startswith("86000")` is False. The check fails closed (Hold). This is **safe** (fail closed), but it might reject a valid pass if the integrator's logic considers them equivalent.
    - However, the prompt asks: *"Can it refuse a record the integrator rightly passes, such as a token with a comma or other formatting?"*
    - If the integrator's decoder outputs `"86,000"` and the second recogniser outputs `"86,000"` (stable), it passes.
    - If the integrator's decoder outputs `"86,000"` and the second recogniser outputs `"86000"` (unstable, but same value), the integrator might pass it (if it uses canon). This side's `ruling_105_fails` will see `token="86,000"`, `r="86000"`. `token.startswith(r)` is False. It returns a failure string. `decide()` turns the PASS into a HOLD.
    - **Verdict:** This is a **P1** because it creates a divergence between the integrator's pass and the builder's hold. While "fail closed" is a governing law (M12), the specific instruction for RULING 105 is that the builder's check is a "defence in depth" re-check of the *record*. If the record is valid per the integrator's rules (which likely use canon for number equivalence), the builder should not reject it based on raw string mismatch if the values are canonically equal. The code should use `canon.same` or similar to compare tokens, or at least normalize them, to ensure it doesn't reject valid canonical matches. Currently, it rejects any formatting difference, which may be overly strict and cause unnecessary holds on valid content.

**2. [P2] `_truncation` logic is brittle for multi-digit suffixes**
The `_truncation` function (lines 57-62) defines a truncation as a prefix that drops only a **non-digit** suffix.
- Example: Token `"1234"`. Reading `"123"`. Suffix `"4"` has a digit. `_truncation` returns False. Correct (dropping a digit is not a truncation of a "term" like '401k').
- Example: Token `"123k"`. Reading `"123"`. Suffix `"k"` has no digit. `_truncation` returns True. Correct.
- Example: Token `"123.45"`. Reading `"123"`. Suffix `".45"` has digits. `_truncation` returns False.
- This logic seems consistent with the "401k" example. However, it relies on the token being a single "term". If the token is a complex number like `"1,234.56"`, the logic might not handle it well, but since it fails closed, it's not a P0. It's a P2 because it's a heuristic that might not cover all "truncation" cases defined by the orchestrator, but it's safe.

**3. [P3] Test coverage for `unstable_of` with non-dict entries**
`unstable_of` (lines 97-101) handles `e` being `None` or not a dict. It returns `None` if `r` is not a dict. This is correct. The test `test_the_record_is_carried_as_it_stands_and_only_when_present` (line 334) checks `LP.unstable_of({"unstable_second_reading": ["401k"]})` returns `None`. This is good.

**4. [P3] `decide` function logic flow**
In `decide` (lines 30-42), the check for `ruling_105_fails` is only performed if `out in PASS`. If `out` is `"hold"`, it skips the RULING 105 check and returns hold. This is correct per the law: "a ruling-105 hold is 'hold'". If the outcome is already hold, we don't need to check the record. If the outcome is pass, we check the record. If the record fails, we turn it into hold. This is correct.

**5. [P1] Potential issue with `token` validation in `ruling_105_fails`**
Line 77: `if not (isinstance(tok, str) and tok and any(ch.isdigit() for ch in tok)):`
This requires the token to contain at least one digit.
- The law says: "a name (a token with no digit) never qualifies".
- This check correctly rejects names.
- However, what if the token is `"401k"`? It has digits. Passes.
- What if the token is `"k401"`? It has digits. Passes.
- This seems fine.

**6. [P2] `check` function row construction**
Line 48: `rows.append(dict(s, **d, relisten=relisten_of(e), unstable_second_reading=unstable_of(e), ...))`
This adds `unstable_second_reading` to the row.
Line 111-112 in `apply`: `if isinstance(r.get("unstable_second_reading"), dict): s["unstable_second_reading"] = ...`
This copies it to the segment.
This looks correct.

**7. [P1] Seal Compatibility and `SEALED_LATER`**
`package_pin.py` adds `"unstable_second_reading"` to `SEALED_LATER`.
`to_pin` (lines 130-138) includes it in the segment dict if present.
`pin_seal` (not shown, but implied) hashes the pin.
The test `test_the_record_is_sealed_and_a_pin_without_one_seals_as_before` (line 343) verifies that a pin without the record seals as before, and a pin with it seals differently.
The test `test_the_spotlight_now_rendering_still_recomputes_to_its_own_seal` (line 359) verifies that an existing pin (which presumably doesn't have the new field) still recomputes to its old seal.
This is correct. The field is optional. If not present, it's not added to the segment dict, so the hash doesn't change.

**8. [P2] `ruling_105_fails` does not use `canon` for comparison**
As noted in Finding 1, the use of raw string comparison (`x != tok`, `token.startswith(r)`) instead of `canon.same` or `canon.canon_tokens` is a deviation from Law L-k ("every text comparison in the pipeline uses pipeline/canon.py").
While this specific check is for "truncation" which is a structural string property, the comparison of the token itself (`x != tok`) should ideally be canonical.
If the integrator stores `"401k"` and the second reading is `"401K"` (case difference), `x != tok` is True. `token.startswith(r)` is False (case sensitive). It fails closed.
If the integrator normalizes case, this side might reject a valid pass.
Given Law L-k, this is a **P1** or **P2**. Since it leads to a Hold (fail closed), it's not a P0 (wrong result/data loss), but it is a "real defect" in that it doesn't comply with the canonical comparison law. I will rate it **P1** because it can cause unnecessary holds on valid content, which is a functional defect in the pipeline's ability to pass valid clips.

**9. [P3] Comment clarity**
The comments are very detailed and reference specific orchestrator messages. This is good for auditability.

**10. [P2] `test_ruling_105.py` imports**
The test file imports `test_angles as TA` and `from test_lock_precheck import ...`. This is standard for this repo's test structure.

### Summary of Findings

1.  **[P1]** `ruling_105_fails` uses raw string comparison instead of `canon` for token equality and truncation checks. This violates Law L-k and can cause valid passes (where tokens are canonically equal but string-different, e.g., case or formatting) to be rejected as holds.
2.  **[P2]** `_truncation` logic is a heuristic that may not cover all edge cases of "truncation" as defined by the orchestrator, but it fails closed, so it is safe.
3.  **[P3]** No other significant issues found. The seal compatibility is handled correctly. The fail-closed behavior is consistent with M12.

P1_OR_WORSE: 1