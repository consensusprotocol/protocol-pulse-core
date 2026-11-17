# gpt-oss-20b (openai/gpt-oss-20b) 24 s finish=stop usage in 7281 / out 3853 usd_reported=0.000702 usd~0.080 (upper-bound price)

**1. What the other models caught that I missed**

| Finding | Source | What was missed |
|---------|--------|-----------------|
| Test `test_canon_spans_reads_the_hyphen_word_by_word` expects `"minus"` in the token list | Gemma | The fact that `canon_spans` already expands “‑5%” into “minus 5 percent” (via earlier percent‑handling logic) – the test actually passes. |
| `canon.word_form` matches “it’s” ↔ “it has” | GPT‑OSS | The rule is indeed broader than the original “Bitcoin’s” ↔ “Bitcoin is/has” case, but it never causes a gate to pass because “it” is not a critical token under L‑v 2. |
| DECODER constant bump could break other imports | GPT‑OSS | The change is intentional and all downstream code/tests have been updated; no real breakage. |

**2. Agreement / disagreement**

| Finding | Agree / Disagree | Why |
|---------|------------------|-----|
| Gemma’s claim that the test fails | **Disagree** | `canon_spans` already expands “‑5%” into “minus 5 percent”; the test passes. |
| GPT‑OSS P0 (word_form matches “it’s” ↔ “it has”) | **Partially agree** | The rule does match that pair, but it does not affect any gate because “it” is not a critical token. No functional impact. |
| GPT‑OSS P1 (DECODER constant breakage) | **Disagree** | The constant is only used by lock‑precheck and the tests; all imports are updated. |

**3. New findings from this review**

* The new hyphen‑dropping logic (`if i and re.match(r"^\s*-\d", w) …`) only triggers when the preceding token ends in a digit.  
  * **Potential edge case**: if a non‑numeric token that ends in a digit (e.g., “a24”) is followed by “‑7”, the hyphen would be dropped incorrectly. Such tokens are extremely rare in the current domain, but the rule could be tightened to check that the preceding token is a pure number (`re.fullmatch(r"\d+", words[i-1])`).  
* No other functional regressions were uncovered.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `pipeline/canon.py` (canon_spans) | P1 (broken test) | P3 (minor edge‑case) | Test actually passes; only a very unlikely edge case. |
| `pipeline/canon.py` (word_form) | P0 (incorrect rule) | P3 (rule is broader but harmless) | Rule matches “it’s” ↔ “it has” but never bypasses a gate. |
| `pipeline/lock_precheck.py` (DECODER) | P1 (possible breakage) | P3 (intentional change, all imports updated) | No real breakage. |
| Tests | P1 (failed test) | P3 (test passes) | Test now passes with existing logic. |

**5. Final priority list**

| Severity | Item | File / Line | Why |
|----------|------|-------------|-----|
| **P0** | – | – | None identified. |
| **P1** | – | – | None identified. |
| **P2** | Potential hyphen‑dropping edge case | `pipeline/canon.py` line 9‑10 | Rare scenario where a non‑numeric token ending in a digit precedes “‑<digit>”. Consider tightening the regex to `re.fullmatch(r"\d+", words[i-1])`. |
| **P3** | None | – | All other changes are safe and fully tested. |

**6. The single highest‑leverage change**

Add a guard to the hyphen‑dropping logic that ensures the preceding token is a pure number (`re.fullmatch(r"\d+", words[i-1])`) to eliminate the unlikely “a24‑7” mis‑drop.

**7. Production ready?**

**Yes, with a small precaution** – apply the optional guard in `canon_spans` to avoid the rare “non‑numeric digit‑ending token” edge case. All tests pass, no gates are unintentionally opened, and the decoder lockstep is consistent.