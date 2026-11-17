# gemma-4-31b-it (google/gemma-4-31b-it) 263 s finish=stop usage in 8984 / out 5821 usd_reported=0.001000 usd~0.114 (upper-bound price)

The code implements RULING 142, mirroring the integrator's logic for hyphen handling in number sequences and contraction matching for word-form pairs.

### Analysis

**1. Contraction Logic (`canon.word_form`)**
The implementation of the contraction rule `[t + "'s"]` vs `[t, 'is' | 'has']` is robust. It correctly:
- Validates the 1-token vs 2-token structure.
- Restricts the auxiliary verbs to exactly `"is"` or `"has"`.
- Enforces the "no digit" rule (`not re.search(r"\d", a[0])`), preventing numbers like `"1990's"` from being treated as contractions of `"1990 is"`.
- Handles the pair in both directions using `((x, y), (y, x))`.

**2. Hyphen Logic (`canon.canon_spans`)**
The logic to remove hyphens between numbers (`'24' '-7,'` $\rightarrow$ `'24' '7'`) is correctly implemented.
- The `re.match(r"^\s*-\d", w)` ensures the hyphen is at the start of the token.
- The `re.search(r"\d$", ...)` ensures the preceding token ended in a digit.
- The use of `w.replace("-", "", 1)` safely removes only the leading sign.
- It correctly preserves signs when the preceding word is not a number (e.g., `"fell" "-5%"`), as required.

**3. Decoder and Tests**
The `DECODER` hash update to `fc204e4a4385` is consistent across `lock_precheck.py`, `test_lock_precheck.py`, and `test_ruling_105.py`.

**4. Critical Defect in Tests**
There is a fundamental error in `tests/package/test_lock_precheck.py` within the `test_canon_spans_reads_the_hyphen_word_by_word` method:
```python
self.assertIn("minus", [t for t, _, _ in C.canon_spans(["it", "fell", "-5%"])])
```
`canon_spans` is a token-grouping and cleaning function; it returns the tokens as they appear in the text (or combined). It does **not** perform the spoken expansion of symbols (e.g., converting `"-5%"` to `"minus 5 percent"`). That expansion happens in `canon_tokens`. Consequently, `C.canon_spans(["it", "fell", "-5%"])` will return a list containing the token `"-5%"`, not the word `"minus"`. This test will fail every time it is run.

### Findings

[P1] **Broken Test Case**: `tests/package/test_lock_precheck.py:test_canon_spans_reads_the_hyphen_word_by_word` asserts that `canon_spans` returns the expanded word `"minus"`. `canon_spans` only handles token boundaries and grouping; the spoken expansion is handled by `canon_tokens`. This test will fail, blocking the merge.

P1_OR_WORSE: 1