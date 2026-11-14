# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 14301 / out 1406 usd~0.064 (upper-bound price)

I have reviewed the diff, the governing laws, and the background facts. Here is the audit.

### Findings

**<critical> None**

**<high> None**

**<medium> None**

**<low> (Informational / Verification Notes)**

1.  **Landing Order & Decoder Mismatch (Attack d):**
    The background states: *"The builder commits this change and says READY with no build running. The integrator merges to main and pushes. Only then does the builder push, so no pre-check of the builder's waits on a sha it cannot read."*
    *   **Verification:** The code in `lock_precheck.py` updates `DECODER` to `d1e155c642a6`. If a build were to run *before* the integrator's merge, the builder would look for files named `*.d1e155c642a6.json`. The integrator's service (still on the old code) would produce files named `*.c705b20ed800.json` (or whatever the previous decoder was).
    *   **Result:** `lock_precheck.answer()` would return `None` for all segments because the file names wouldn't match. `check()` would then raise a `ValueError` or return a failure state (depending on `check`'s error handling for missing answers, which is described as "waits for its own" in tests, implying a retry or hold).
    *   **Conclusion:** This is a **fail-closed** behavior. It blocks the build rather than sealing a wrong pin. This complies with **M12 FAIL CLOSED**. The landing order described in the background prevents this state from occurring in practice, but even if it did, the system would not produce an incorrect output; it would simply halt.

2.  **Relisten Record Sealing (Attack b):**
    *   **Code:** `lock_precheck.apply()` copies `r["relisten"]` to `s["relisten"]` only if `isinstance(r.get("relisten"), dict)`.
    *   **Code:** `package_pin.to_pin()` includes `"relisten"` in the `SEALED_LATER` loop: `**{k: s[k] for k in ... "relisten" if k in s}`.
    *   **Verification:** The record is passed "as it stands" (no re-shaping). If the integrator provides a valid dict, it is sealed. If it provides `null` or a non-dict, it is excluded from the segment dict, and thus excluded from the seal.
    *   **Tampering:** `test_ruling_103.py` verifies that tampering with `second_reading` changes the `pin_seal`. This confirms the record is part of the cryptographic integrity check.
    *   **Conclusion:** Compliant. A pin delivered before this change (without `relisten`) will recompute correctly because `relisten` is not in `s`, so it is not added to the body.

3.  **Canon Changes (Attack c):**
    *   **Code:** `canon.py` adds `_PLANS = ("401k", "403b", "457b")`.
    *   **Logic:** In `_canon_seq`, if a token is in `_PLANS` (or a split form like `401` + `k`), it is treated as a single name token, *unless* `owed` is not `None` (i.e., a currency symbol `$` was seen).
    *   **Verification:**
        *   `C.canon_tokens("$401k")` -> `["401000", "dollars"]` (Amount preserved).
        *   `C.canon_tokens("a 401k")` -> `["a", "401k"]` (Name preserved).
        *   `C.same("a 401k", "a 401,000")` -> `False` (Correctly distinguishes name from number).
    *   **Impact on Gates:** Law **L-k** states "a different number... never does [compare equal]". Previously, `401k` might have been parsed as `401000` (if the suffix logic applied) or `401` + `k` (if not). The fix ensures `401k` is a distinct token from `401000`. This aligns with the "Written Forms" law (L-g) and the specific ruling. It does not change comparisons for non-plan names or amounts with `$`.
    *   **Conclusion:** Compliant. The change is scoped to retirement plan names.

4.  **Old Decoder/Rules Reuse (Attack a):**
    *   **Code:** `lock_precheck._matches()` checks `rules == RULES` and file name contains `DECODER`.
    *   **Verification:** `RULES` is updated to include `ruling 103`. `DECODER` is updated to `d1e155c642a6`.
    *   **Test:** `test_an_answer_in_the_old_decoders_file_is_never_read` explicitly tests that files with old decoder hashes (`c705b20ed800`, etc.) are ignored.
    *   **Conclusion:** Compliant. Old answers are fail-closed (ignored).

5.  **Laws Compliance:**
    *   **M12 FAIL CLOSED:** Missing data (no matching decoder file) results in no answer, which blocks the pre-check.
    *   **L-k ONE CANONICAL FORM:** The canon fix ensures `401k` is treated consistently as a name, not a number, across both builder and render sides (byte-identical files).
    *   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** The `relisten` record is sealed into the pin. Any tampering with the record invalidates the pin seal.

### SHIP: yes

The change is minimal, fail-closed, and correctly implements Ruling 103 and the Canon fix. The landing order ensures that the builder's code (expecting the new decoder) is only deployed after the integrator's service (producing the new decoder) is live. The sealing logic correctly includes the new `relisten` field when present and excludes it when absent, maintaining backward compatibility for existing pins.