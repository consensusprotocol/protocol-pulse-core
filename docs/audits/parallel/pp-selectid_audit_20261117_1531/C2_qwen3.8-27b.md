# qwen3.8-27b (qwen/qwen3.8-27b) 188 s finish=stop usage in 8084 / out 6363 usd_reported=0.005959 usd~0.120 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## Feature: pp-selectid-20261117_1531 | RULING 142, batches 111 + 112 mirror

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma's P1 (test fails because `canon_spans` doesn't expand signs):** I initially shared the same mental model — that `canon_spans` is a pure token-grouping function and the spoken expansion (`-5%` → `minus 5 percent`) lives in `canon_tokens`. The consensus refutes this with the passing test suite (63 passed) and an explicit statement that sign expansion *is* part of `canon_spans`'s output. I was wrong to assume a clean separation that doesn't exist in this codebase. The test at line 93 (`self.assertIn("minus", ...)`) passes because `canon_spans` does perform the sign-to-word expansion as part of its canonical token production. **I concede this was a misread of the function's scope.**

**GPT-OSS's P0 (contraction lets a run decode pass a gate):** I initially flagged the same concern — that `word_form` returning `True` for `["it's"]` vs `["it", "has"]` could be a gate bypass. The consensus correctly explains that `word_form` is a *classification* consumed by `attest.class_131`, which only lifts a critical-token HOLD from one pair. The pair then proceeds to ruling 131 (A)'s two-of-three adjudication unchanged. Moreover, `"it"` is not a critical token (not a number, name, or negation), so the pair reaches the same vote with or without the `word_form` classification. The contraction in both directions (`is`/`has`) is the ruled design per ruling 142 (2) and the integrator's own case (feb4b72f). **I was conflating classification with adjudication.**

**GPT-OSS's P1 (stale DECODER in another module):** I didn't flag this, but I also don't see a real risk. `lock_precheck.DECODER` is the single source; its readers are `lock_precheck.result_file` and the two test files (both updated). The lockstep moves both sides atomically. Entries under a different decoder SHA are never read (fail-closed by construction). **No issue.**

**Qwen's P3 observations:** All three are valid and well-reasoned. The theoretical sign-drop edge (ASR emitting `["24", "-7"]` for "twenty-four minus seven" with no conjunction) is a ruling-sanctioned reading, not a bug. The possessive-vs-verb note is correct — `word_form` is classification only. The missing punctuation-boundary test is a good suggestion.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My position | Reasoning |
|---|---|---|---|
| Test `test_canon_spans_reads_the_hyphen_word_by_word` fails | Gemma [P1] | **Disagree** | The test passes (63 passed). `canon_spans` does perform sign expansion. The consensus is correct. |
| `word_form` accepts "it's" ↔ "it has", bypassing a gate | GPT-OSS [P0] | **Disagree** | `word_form` is a classification, not a pass. Two-of-three adjudication still gates. "it" is not a critical token. The contraction both ways is the ruled design. |
| Stale DECODER in another module | GPT-OSS [P1] | **Disagree** | Single source, two test readers, both updated. Lockstep is atomic. |
| Theoretical sign-drop in compound-ASR edge | Qwen [P3] | **Agree** | Valid observation. Ruling-sanctioned. A one-line comment would help future readers. |
| Possessive "X's" vs "X has" classified as word-form pair | Qwen [P3] | **Agree** | Correct. `word_form` is classification only; two-of-three still decides. No gate bypassed. |
| Missing punctuation-boundary test | Qwen [P3] | **Agree** | `["24.", "-7"]` → hyphen kept would pin the `re.search(r"\d$", …)` boundary. Low risk, good documentation. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

After reading the full diff line-by-line with the benefit of all three Cycle 1 analyses:

**[P3] `w.replace("-", "", 1)` does not strip leading whitespace, unlike the standalone-hyphen handler above it.**
Line 10: `w = w.replace("-", "", 1)`. If `w` is `" -7,"` (leading space, as the regex `^\s*-\d` permits), the result is `" 7,"` with a leading space. The standalone-hyphen handler at line 8 does `w.strip() + (words[j] or "").strip()`. This is a minor inconsistency. In practice, ASR tokens in this pipeline don't carry leading whitespace (the tokenizer strips it), so this is theoretical. But if a future change introduces whitespace-bearing tokens, the two hyphen handlers would behave differently. A `w = w.lstrip().replace("-", "", 1)` or a trailing `.strip()` would make them consistent.

**[P3] The contraction check is placed before the `len(x) != len(y)` guard — correct but non-obvious.**
Lines 23–26 run before line 27 (`if len(x) != len(y) or not x: return False`). This is *required* because the contraction case has `len(x) == 1` and `len(y) == 2`, which would be rejected by the length check. A reader who reorders the code would break the contraction. A brief comment (`# must precede the length check: 1-token vs 2-token`) would prevent a future refactor from silently removing the contraction path.

**[P3] No test for `word_form` with `x` or `y` being `None` or empty list.**
The code handles this (`list(x or [])` → `[]`, then `len(a) == 1` is False, falls through to `not x` → `False`). But there's no explicit test pinning this. Extremely low risk since the callers always pass non-empty lists, but a one-line `self.assertFalse(C.word_form(None, ["bitcoin", "is"]))` would be cheap insurance.

**No P0, P1, or P2 findings.** The code is correct, the tests are comprehensive, the decoder lockstep is verified, and the ruling's constraints are respected.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `canon.canon_spans` hyphen rule | P3 (theoretical sign-drop) | P3 | Unchanged. Ruling-sanctioned. Qwen's comment suggestion still valid. |
| `canon.word_form` contraction | P3 (possessive note) | P3 | Unchanged. Classification only, not a gate. GPT-OSS's P0 refuted. |
| `lock_precheck.DECODER` lockstep | Clean | Clean | Verified. Single source, two test readers, both updated. Full SHA in comment matches 12-char prefix. |
| Tests (`test_lock_precheck.py`) | P1 (Gemma claimed broken test) | Clean | Test passes (63 passed). Gemma's P1 refuted. Sign expansion is part of `canon_spans`. |
| Tests (`test_ruling_105.py`) | Clean | Clean | Decoder pin updated correctly. |
| Law compliance (L-k, L-l, LAW 20/M2, M12, LAW 22) | Compliant | Compliant | Unchanged. No gate threshold changed. No reclassification. Fail-closed by construction. |
| Smallest diff / no new renderer | Compliant | Compliant | 4 files, ~30 lines of logic change. No renderer touched. |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 (nits, non-blocking):**

| # | File / Line | Finding |
|---|---|---|
| 1 | `pipeline/canon.py` line 10 | `w.replace("-", "", 1)` doesn't strip leading whitespace, unlike the standalone-hyphen handler at line 8. Theoretical inconsistency; add a comment or a `.lstrip()` for symmetry. |
| 2 | `pipeline/canon.py` lines 23–26 | The contraction check must precede the `len(x) != len(y)` guard. Add a one-line comment so a future refactor doesn't reorder and silently break it. |
| 3 | `tests/package/test_lock_precheck.py` line 93 | Add a third assertion: `["24.", "-7"]` → hyphen kept (previous word ends in `.`, not a bare digit). Pins the `re.search(r"\d$", …)` boundary. |
| 4 | `tests/package/test_lock_precheck.py` | Add `self.assertFalse(C.word_form(None, ["bitcoin", "is"]))` to pin the empty/None guard. |
| 5 | `pipeline/canon.py` line 10 | Add a one-line comment noting the assumption: "hyphen-attached-to-digit after a bare digit = tokenisation artifact, not a sign" (Qwen's suggestion). |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The code is correct and the tests are sufficient; the single highest-leverage change is **adding the two one-line comments** (the "must precede the length check" note on the contraction, and the "tokenisation artifact, not a sign" note on the hyphen rule) because they are the two places where a future reader is most likely to "fix" working code and introduce a regression.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all P3, none blocking):
- The five P3 nits above are recommended for a follow-up commit but do not block this merge.
- The decoder lockstep is verified: `fc204e4a4385` in `lock_precheck.py`, both test files, and the full SHA in the comment.
- The integrator's branch `r142-postlive 70e78551` is audited on its side; this mirror is byte-identical for `canon.py` (sha256 `90f23312…`).
- All 63 tests pass. 6 of 6 mutations killed.
- No gate threshold changed. No reclassification. Fail-closed by construction.

---

P1_OR_WORSE: 0