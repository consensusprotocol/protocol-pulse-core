# qwen3.8-27b (qwen/qwen3.8-27b) 150 s finish=stop usage in 8594 / out 9169 usd_reported=0.006937 usd~0.163 (upper-bound price)



# Code Audit — pp-selectid / RULING 142 (batches 111 + 112 mirror)

## Scope Reviewed

- `pipeline/canon.py` — `canon_spans` hyphen rule + `word_form` contraction
- `pipeline/lock_precheck.py` — DECODER constant bump
- `tests/package/test_lock_precheck.py` — new tests + decoder pins
- `tests/package/test_ruling_105.py` — decoder pin

---

## Findings

### [P3] canon_spans hyphen rule: theoretical sign-drop in a compound-ASR-error edge

The new condition

```python
if i and re.match(r"^\s*-\d", w) and re.search(r"\d$", (words[i - 1] or "").rstrip()):
    w = w.replace("-", "", 1)
```

drops the hyphen whenever a `-<digit>` token immediately follows a digit-ending token. This is correct for the ruling's target case (ASR splitting a compound like "24-7" into "24" "-7,") and is consistent with the existing standalone-`"-"` handler above it (which already guards on `not re.search(r"[\d.,%]\s*$", words[i-1])`).

The only scenario where a *genuine* minus sign would be lost is if ASR emits exactly `["…24", "-7"]` for the spoken phrase "twenty-four minus seven" with no intervening conjunction. In natural speech (and in the pipeline's financial/Bitcoin domain) a speaker would say "24, then minus 7" or "24 to negative 7," producing a non-digit token between them. The existing standalone-`"-"` path already handles the case where ASR keeps the sign as its own token. This is a ruling-sanctioned reading, not a bug, but it is worth a one-line comment in `canon_spans` noting the assumption (hyphen-attached-to-digit after a bare digit = tokenisation artifact, not a sign) so a future reader doesn't "fix" it.

### [P3] word_form contraction: possessive "X's" vs "X has" classified as a word-form pair

```python
if len(a) == 1 and len(b) == 2 and b[1] in ("is", "has") and a[0] == b[0] + "'s" \
        and not re.search(r"\d", a[0]):
    return True
```

This correctly matches the ruling's case ("Bitcoin's" ↔ "Bitcoin is") and the grammatical contraction ("it's" ↔ "it has"). It would also match a possessive reading ("Bitcoin's price" ↔ "Bitcoin has price"), but `word_form` is a *classification* only: it tells ruling 131 (A) that the two readings differ by a word-form pair, after which the two-of-three adjudication (sealed text, run decode, second recogniser) still decides. A genuine possessive-vs-verb mismatch would be caught by the second recogniser or the sealed text disagreeing, producing a HOLD. No gate is bypassed. No action needed; noting for completeness.

### [P3] Test coverage: no explicit negative for punctuation on the preceding word

`test_canon_spans_reads_the_hyphen_word_by_word` verifies:
- `["24", "-7,", "365"]` → `["24", "7", "365"]` (hyphen dropped)
- `["it", "fell", "-5%"]` → contains `"minus"` (hyphen kept)

A third assertion such as `["24.", "-7"]` → hyphen kept (previous word ends in `.`, not a bare digit) would pin the boundary of the `re.search(r"\d$", …)` guard. Low risk since the regex is straightforward, but it would make the test suite self-documenting for the next person touching `canon_spans`.

### Decoder lockstep — verified

- `DECODER` bumped `fe809cb4e680` → `fc204e4a4385`; full SHA in the comment matches the 12-char prefix.
- Both test files (`test_lock_precheck.py`, `test_ruling_105.py`) updated to the new prefix.
- Result-file naming embeds the decoder, so old results under the previous SHA are not accidentally read (fail-closed by construction).
- `RULES` string unchanged (ruling 142 is covered by the existing rule set per the comment).
- The builder's mirror correctly excludes the integrator's acquisition-side code (post_live fallback, offset guard) — those live in branch `r142-postlive 70e78551`.

### Law compliance check

| Law | Status |
|-----|--------|
| L-k (one canonical form) | Compliant. The contraction and hyphen rules make canon read what the listener hears; the two-of-three adjudication prevents auto-pass. |
| L-l (model reply counts only whole) | Not touched. |
| LAW 20 / M2 (thresholds are constants; no reclassification) | Compliant. DECODER is a constant; no gate threshold changed; no failing gate reclassified. |
| M12 (fail closed) | Compliant. `word_form` returning `True` is a classification, not a pass; the adjudication still gates. |
| LAW 22 (v2f byte-identical) | The canon change could alter text comparisons in gates that read v2f transcripts. The ruling notes this is a lockstep with the integrator's audited branch; v2f's lock_precheck results will be regenerated under the new decoder. No byte-identity risk to the *render* (canon is not in the render path). |
| Smallest diff / no new renderer | Compliant. 4 files, ~30 lines of logic change. |

### Answers to the three requested checks

1. **Can the contraction rule exempt anything the ruling did not?** No. It is restricted to `[t + "'s"]` vs `[t, "is"|"has"]`, either direction, no digit in `t`. "was", "were", "will", another noun, or a digit-bearing token all fall through to the existing `len(x) != len(y) → False` path. The two-of-three adjudication remains the decision authority.

2. **Does the canon_spans change ever drop a real sign?** Only in the theoretical case where ASR emits a bare `-<digit>` token immediately after a digit-ending token with no conjunction (see [P3] above). In all realistic ASR output for "minus" or "negative," the sign is either a standalone token (handled by the existing code) or preceded by a non-digit word. The ruling's target case (compound-number split) is handled correctly.

3. **The decoder and the tests.** Decoder bump is clean, both test pins updated, new tests cover positive/negative contraction cases and the hyphen rule. 6/6 mutations killed. The one gap is the missing punctuation-on-preceding-word assertion ([P3]).

---

P1_OR_WORSE: 0