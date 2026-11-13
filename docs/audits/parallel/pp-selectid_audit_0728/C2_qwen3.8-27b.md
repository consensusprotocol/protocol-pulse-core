# qwen3.8-27b (qwen/qwen3.8-27b) 23 s finish=stop usage in 5134 / out 1692 usd~0.041 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0728

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the structural equivalence of the predicates. The other models (specifically GLM-5.3-FLASH) correctly identified **P2-2** and **P2-3**: the risk that the *error message text* change in `package_pin.py` could break golden fixtures or attestation seals if those seals include the problem strings. While the consensus notes that "reason's text is not part of the seal," the diff *does* change the string literal. If any downstream consumer (logging, UI, or a specific test not shown in the diff) asserts on the exact string `"is not one of"`, it will fail. I missed flagging the *test coverage gap* for the new message string (P2-3): the diff adds tests for the *rejection* of multi-token words, but does not explicitly assert that the *reason* returned is the new "must be ONE word" string.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (P2-1, P2-2, P2-3):** **Agree.**
    *   P2-1 is valid: The behavior for empty strings is consistent (`[]` -> `len != 1` -> refuse), but the lack of an explicit test for `""` or punctuation-only inputs is a minor coverage gap.
    *   P2-2 is valid: The message change is a potential source of brittleness in external tests.
    *   P2-3 is valid: The new message string is never asserted in the provided test diff.
*   **GROK-4.20 (No findings):** **Disagree (partially).** Grok missed the nuance of the message string change and the test coverage gap. It correctly identified the logic is sound, but "No P2" is too optimistic given the string literal change.
*   **QWEN3.8-27B (P2 on message):** **Agree.** Qwen correctly noted the message is cosmetic but potentially misleading if canon rules change, and flagged it as P2.
*   **CLAUDE CONSENSUS:** **Agree.** The consensus correctly downgrades GLM's P2s to "recorded, no change" because the core logic is sound and the seal *does not* include the problem text (per the background info: "only segment fields are sealed"). This resolves the P2-2 risk.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-4 — test_medley.py:850-855 (Implicit):** The test `test_only_one_word_and_only_the_ruled_words` adds `"And/or ..."` to the loop. This tests `trim_variant` (package.py). However, the corresponding test for `trim_problems` (package_pin.py) is in the `bad` tuple loop (line 850-855 in the diff context, actually lines 49-52 in the diff). The diff *does* add `{"trimmed_leading": "But so"}` and `{"trimmed_leading": "and/or"}` to the `bad` list. This confirms that the pin-side rejection is tested. **No new finding here; the coverage is actually better than I initially thought.**

**P2-5 — package_pin.py:129 (Message Clarity):** The new message is `f"segment {i}: trimmed_leading {w!r} must be ONE word, one of {'/'.join(TRIM_WORDS)}"`. If `w` is `"But so"`, the message reads: `segment 1: trimmed_leading 'But so' must be ONE word, one of but/and/so/well/now/yeah`. This is clear. If `w` is `"and/or"`, it reads: `segment 1: trimmed_leading 'and/or' must be ONE word...`. This is also clear. No issue.

**Re-evaluation of P2-2 (Seal Risk):** The background states: "glm's P2s are recorded... P2-2: the reason's text is not part of the seal; only segment fields are sealed." This is a **critical fact** provided in the consensus. Therefore, the message change **cannot** break the seal. The risk of breaking *other* tests (golden files) remains, but is low if the suite passes (as reported: "test_medley 81 OK; every other suite OK").

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Logic Correctness** | 9/10 | 10/10 | Confirmed equivalence with render's `validate_schema`. No edge cases missed. |
| **Test Coverage** | 8/10 | 9/10 | Added tests for "But so" and "and/or" on both sides. Minor gap: no explicit test for empty string `""` or punctuation-only `","`, but behavior is consistent with old code. |
| **Message/UX** | 7/10 | 8/10 | Message is clearer ("must be ONE word"). Risk of breaking external string assertions is low given suite pass. |
| **Seal Integrity** | 8/10 | 10/10 | Confirmed via consensus that problem text is *not* sealed. No risk. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **test_medley.py (Coverage Gap):** No explicit test case for `trimmed_leading = ""` or `trimmed_leading = ","` (punctuation only). While the logic handles these correctly (canon returns `[]` or `['']`? No, canon strips punctuation, so `","` -> `[]` -> `len != 1` -> refuse), the absence of a test means a regression in `canon.canon_tokens` handling of empty/punctuation strings would not be caught by *this* diff's tests. *Recommendation:* Add `{"trimmed_leading": ""}` and `{"trimmed_leading": ","}` to the `bad` tuple in `test_medley.py`.
2.  **package_pin.py:129 (String Assertion):** The new error message string is not asserted in the provided tests. If a future change alters the message, tests will still pass (since they only check for rejection, not the reason). *Recommendation:* Add an assertion in the `bad` loop to verify the specific reason string contains "must be ONE word".

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add test cases for empty string and punctuation-only inputs to `test_medley.py` to explicitly verify the `len(tok) != 1` guard handles the edge cases where `canon.canon_tokens` returns an empty list.**

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The reported test suite pass ("test_medley 81 OK; every other suite OK") is accurate.
2.  No external golden files or attestation fixtures outside the provided diff assert on the *old* error message string `"is not one of"`. (Given the consensus that the seal does not include problem text, this is a low-risk condition, but should be verified if such fixtures exist in the broader repo).

The logic is sound, the equivalence with the render is confirmed, and the tests cover the primary failure modes. The P2 items are minor coverage improvements, not blockers.