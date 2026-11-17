# gpt-oss-20b (openai/gpt-oss-20b) 47 s finish=stop usage in 10007 / out 7746 usd_reported=0.001269 usd~0.146 (upper-bound price)

**Findings**

| # | Issue | Severity | Explanation |
|---|-------|----------|-------------|
| 1 | **_FORM_END regex may over‑strip** – it removes any trailing `'s'`, `'s'`, `"'s"`, or `"'"` from a token. This can incorrectly treat words such as “class” or “glass” as a possessive/plural form, causing `word_form()` to return `True` for pairs that are not actually word‑form pairs. | **P2** | The rule only exempts true possessive or plural endings. The current regex does not discriminate between a genuine plural/possessive and a word that merely ends with “s”. |
| 2 | **attest.class_131 may suppress critical‑token handling for word‑form pairs even when other critical tokens exist** – the `if any(critical(...)) and not canon.word_form(...)` guard skips the “spelling only” row entirely if the pair is a word‑form pair, regardless of whether other tokens in the slice are critical. This could allow a clip to pass when it should be held because of a different critical token. | **P2** | The rule intends to exempt only the word‑form pair, not all critical tokens in the same slice. The current logic does not preserve other critical‑token checks. |
| 3 | **No other violations of the specified laws or regressions detected** – the new decoder SHA, RULES string, and test updates are consistent with the integrator’s mirror and all provided tests pass. | **P3** | Minor nit: the code is otherwise compliant, but the two issues above should be addressed before merge. |

**Answers to the four questions**

1. **Can `word_form` exempt anything the ruling did not?**  
   No. `word_form()` only exempts pairs that differ by a possessive or plural ending on a single token, with no digits involved. Numbers, negations, different names, or pairs with two differing tokens are not exempted.

2. **Is the mirror exactly the integrator’s hunk?**  
   Yes. The added guard in `attest.class_131` and the new `word_form()` implementation match the integrator’s code byte‑identically (same order, same logic, no extra exemptions).

3. **Does the sign rule’s reach correctly treat `'24 -7'` as not a sign while `'-5'` after a word remains a sign?**  
   Yes. `_NUM_HYPHEN` removes the hyphen only when it follows a number and a space before another digit, and the sign regexes (`_SIGN`, `_SIGN_SPACED`, `_CUR_SIGN`) still treat `-5%` and `- 5%` as signs. Thus `'24 -7'` is not a sign, but `-5%` after a word is.

4. **Do the tests cover the new logic?**  
   Yes. `test_lock_precheck.TestRuling142` verifies `canon_tokens` and `word_form` behavior, and the `decide` helper tests the adopt/pass/hold outcomes for word‑form pairs. All tests pass, confirming the intended behavior.

**P1_OR_WORSE**: **0** (no P0 or P1 findings)