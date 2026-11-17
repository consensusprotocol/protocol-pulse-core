# gemma-4-31b-it (google/gemma-4-31b-it) 199 s finish=stop usage in 11788 / out 4364 usd_reported=0.000906 usd~0.101 (upper-bound price)

The code implements Ruling 142 (1) and (2) to mirror the integrator's batch 110, specifically addressing the handling of numeric hyphens and possessive/plural word forms in the selection lock and canonicalization process.

### Analysis

**1. Ruling 142 (1): Numeric Hyphens**
- **Implementation:** `canon.py` introduces `_NUM_HYPHEN` which targets a digit, followed by whitespace, followed by a hyphen, followed by a digit (`(\d\s+)-(?=\d)`).
- **Effect:** In `_prepare`, this is stripped of the hyphen. For example, `"24 -7"` becomes `"24 7"`.
- **Correctness:** This prevents the `_SIGN` regex (which allows a hyphen if the preceding character is not a word character—and a space is not a word character) from incorrectly identifying a date/time range as a "minus" sign. The tests verify that `"24 -7, 365"` is treated as numbers, while `"-5%"` and `"- 5%"` (where no digit precedes the space) remain signs.

**2. Ruling 142 (2): Word-Form Pairs**
- **Implementation:** `canon.word_form(x, y)` checks if two token lists are identical except for one token, which must not contain a digit and must be identical once trailing possessive/plural markers (`'s`, `s'`, `'`, `s`) are removed.
- **Integration:** In `attest.class_131`, the critical token check (`critical(t, texts)`) is now gated by `and not canon.word_form(r[a:b], p[c:d])`.
- **Effect:** If a difference is merely a possessive or plural (e.g., "bitcoin" vs "bitcoin's"), it is no longer a "critical" failure (Law L-v 2) and instead proceeds to the "two-of-three" voting logic of Ruling 131 (A).
- **Correctness:** 
    - The digit check `re.search(r"\d", ...)` correctly ensures that numbers (e.g., "1990" vs "1990s") remain critical.
    - The logic `bool(a) and a == b` prevents empty strings from matching.
    - The mirror in `attest.py` exactly matches the integrator's logic by exempting word-forms from the critical hold.

**3. Lock Precheck and Decoder**
- The `RULES` string is updated to include `"ruling 142"`.
- The `DECODER` hash is updated to `fe809cb4e680`, ensuring lockstep with the integrator's render.
- Tests in `test_lock_precheck.py` and `test_ruling_105.py` are updated to match these constants.

**4. Test Coverage**
- `TestRuling142` covers:
    - Positive/negative cases for the sign rule.
    - Positive/negative cases for `word_form` (including the digit restriction and length checks).
    - The decision flow for names (Pass/Adopt/Hold) based on the two-of-three rule.
    - Verification that non-word-form name differences still trigger a hold.

### Findings

No violations of the Governing Laws or the specific requirements of Ruling 142 were found. The implementation is a precise mirror of the integrator's logic.

P1_OR_WORSE: 0