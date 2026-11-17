# qwen3.8-27b (qwen/qwen3.8-27b) 205 s finish=stop usage in 11263 / out 14978 usd_reported=0.011203 usd~0.258 (upper-bound price)



# Code Audit — RULING 142 (1) + (2), pp-selectid branch

## Scope reviewed
`pipeline/canon.py` (`_NUM_HYPHEN`, `word_form`), `pipeline/attest.py` (class_131 hunk), `pipeline/lock_precheck.py` (RULES/DECODER), and the four test files.

---

## Findings

### [P3] `_NUM_HYPHEN` does not cover "24 - 7" (space *after* the hyphen)

`_NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)")` requires the digit to follow the hyphen **immediately**. The ASR artefact the ruling targets is "24 -7, 365" (no space after the hyphen), and that is handled correctly. However, if a future ASR pass emits "24 - 7, 365" (space on both sides), neither `_NUM_HYPHEN` nor `_SIGN_SPACED` (whose lookbehind `[^\d\s.,%]` rejects a preceding digit) will strip the hyphen; it survives into tokenisation.

This is **outside the ruling's stated scope** ("a hyphen right after a number and a space, before a digit") and the file is byte-identical to the integrator's staged copy, so it is not a defect in this diff. Flagging for awareness: if the integrator's branch ever widens the pattern, the builder must re-mirror.

### [P3] `word_form` is a purely structural check — no lexicon guard

`_FORM_END = re.compile(r"(?:'s|s'|'|s)$")` will return `True` for any single-token pair that differs only by a trailing `s` / `'s` / `s'` / `'`, regardless of whether the result is a real English word. Examples that would pass the structural test:

| x | y | stripped | result |
|---|---|----------|--------|
| `["not"]` | `["nots"]` | `not` = `not` | True |
| `["so"]` | `["so's"]` | `so` = `so` | True |
| `["plus"]` | `["plus'"]` | `plus` = `plus` | True |

In practice ASR will not emit these forms, and the **two-of-three vote (ruling 131 A) is the actual decision point** — `word_form` only removes the L-v 2 *pre-hold*, it does not auto-pass. A spurious `True` still requires two of three recognisers to agree on the reading. No law is violated; noting for completeness.

### [P3] Bare `'` alternative in `_FORM_END` is wider than "possessive or plural"

The ruling's language is "a possessive or plural ending." The regex also matches a **trailing bare apostrophe** (`'`), which is neither. This appears to handle a transcription artefact where a closing curly quote fuses to the preceding word after `fold()`. It is the integrator's byte-identical code and the `bool(a)` guard prevents a token that *is* just `'` from matching. No action needed in this diff.

### [P3] Comment indentation on the new RULES line

```python
         "ruling 142")                         # RULING 142 … '24 -7' is no sign; a
#   possessive or plural ending is a word-form pair …
```

The continuation comment drops to column 0 while the preceding RULING 135 / 131 comments are also at column 0, so it is consistent with the file's existing style. Purely cosmetic.

---

## Answers to the four review questions

**(1) Can `word_form` exempt anything the ruling did not?**

- **A number:** No. `re.search(r"\d", diff[0][0] + diff[0][1])` returns `False` for any token containing a digit. `"1990"` vs `"1990s"` → rejected.
- **A negation:** Structurally possible (`"not"` vs `"nots"`) but practically unreachable (ASR will not emit `"nots"`), and the two-of-three vote still governs. No law violation.
- **A different name:** No. `"bitcoin"` vs `"ethereum"` → stripped forms differ → `False`.
- **Two words:** No. `len(diff) != 1` → `False`.

Verdict: the exemption is correctly scoped.

**(2) Is the mirror exactly the integrator's hunk?**

The integrator's `adjudicate_lock` hunk (per the description):
```python
crit = sorted({t for _, a, b, c, d in ops
               if not canon.word_form(r[a:b], p[c:d])
               for t in … if _lv2_critical(…)})
```

The builder's `attest.class_131` change:
```python
if any(critical(t, texts) for t in r[a:b] + p[c:d]) and not canon.word_form(r[a:b], p[c:d]):
```

Both express the same predicate per pair: *the pair contributes to the critical set only when it is NOT a word-form pair.* The builder's short-circuit (`any(…)` first) is an optimisation that does not change the result. The currency-pair pass (line 232) and the spelling-pair pass (line 235, ruling 135) are untouched, matching the integrator's ordering. `class_84` and `carry_class` are unchanged. **The mirror is faithful.**

**(3) The sign rule's reach**

| Input | Pattern that fires | Result | Correct? |
|-------|-------------------|--------|----------|
| `24 -7, 365` | `_NUM_HYPHEN` | `24 7, 365` → tokens `["24","7","365"]` | ✓ (ruling case) |
| `it fell -5% today` | `_SIGN` (lookbehind: space ∉ `[\w.,$%]`) | `it fell minus 5% today` | ✓ |
| `it is - 5% now` | `_SIGN_SPACED` | `it is minus 5% now` | ✓ |
| `24-7` (no space) | none (lookbehind in `_SIGN` rejects digit) | hyphen survives | P3 gap, outside ruling |
| `24 - 7` (space after) | none | hyphen survives | P3 gap, outside ruling |

The three tested cases all behave correctly. The two untested gaps are outside the ruling's stated scope.

**(4) The tests**

- `test_a_number_space_hyphen_digit_is_no_sign`: 3 assertions covering the positive case and two negative controls. ✓
- `test_a_word_form_pair_and_what_is_not_one`: 2 positive + 5 negative cases (digit, two diffs, different word, empty, unequal length). ✓
- `test_two_of_three_decides_a_word_form_pair_of_a_name`: pass / adopt / hold paths all exercised. ✓
- `test_a_name_that_is_no_word_form_still_holds`: confirms `"bitcoin"` vs `"ethereum's"` still holds. ✓
- RULES and DECODER pins updated in both `test_lock_precheck.py` and `test_ruling_105.py`. ✓
- 6-of-6 mutation kill rate reported. ✓

No missing test case rises above P3.

---

## Law compliance check

| Law | Status |
|-----|--------|
| SENTENCE LAW | Not touched by this diff. |
| SELECTION LOCK | Not touched. |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Not touched. |
| CREDITS / L-a / L-b / L-c / L-d | Not touched. L-d (protected preview): DECODER change follows the established lockstep pattern (131 → 135 → 142); old-decoder entries are never read. |
| L-e / L-f / L-g / L-h / L-i | Not touched. |
| L-j (release auth) | Not touched. |
| L-k (one canonical form) | `word_form` lives in `canon.py`; `attest.py` calls `canon.word_form`. ✓ |
| L-l (model reply) | Not touched. |
| LAW 20 / M2 | The word-form exemption is a **ruling-authorised change to what L-v 2 holds**, not a threshold tweak to make a render pass. The pair still goes to the two-of-three vote. ✓ |
| M12 (fail closed) | `word_form` returns `False` on empty, unequal-length, or digit-containing inputs. No exception path yields `True`. ✓ |
| LAW 22 (v2f byte-identical) | Not touched. |
| Smallest diff / M1 / GPU0 / no publishing | 5 files changed, no new renderer/compositor/selector. ✓ |

No law violations found.

---

P1_OR_WORSE: 0