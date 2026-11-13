# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 5700 / out 1048 usd~0.033 (upper-bound price)

# Code Audit: pp-selectid-0335 (C1_STEP.diff)

## Findings

### P1: `pipeline/eligibility.py:439-441` — Unverified variable scope for `targets`
The diff introduces `targets.append(...)` inside the `_span` function. However, the provided diff context (lines 14-25) does **not** show the definition or initialization of the `targets` variable.
- **Scenario:** If `targets` is not defined in the local scope of `_span` (e.g., if it was previously only used in a different branch or if the variable name is actually `facts["targets_missed"]`), this line will raise a `NameError` at runtime for any span with `n > 3`.
- **Verification Limit:** I cannot verify the existence of `targets` from the diff alone. The comment on line 23 mentions `facts["targets_missed"]`, and the test on line 37 checks `four_r.facts["targets_missed"]`. It is highly likely that `targets` is a local alias for `facts["targets_missed"]` defined earlier in the function (outside the diff hunk), but this is an assumption. If `targets` is not a valid local variable, this is a P0 crash. If it is an alias, it is correct. **Flagging as P1 due to inability to verify scope.**

### P2: `pipeline/eligibility.py:439` — String formatting consistency
The new target string is:
`f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and the per-source limit govern length)"`
- **Scenario:** This is a long, static string. While functionally correct, it embeds policy rationale into the data structure. This is acceptable per the "recorded only" instruction, but ensure downstream consumers (e.g., `moments.py`) do not parse this string for logic. The prompt states `facts["targets_missed"]` is "information only," so this is compliant.

### P2: `tests/eligibility/test_eligibility.py:37` — Test assertion fragility
The test asserts:
`self.assertTrue(any("4 sentences > 3 (T9, retired by ruling 35" in t for t in four_r.facts["targets_missed"]), ...)`
- **Scenario:** This is a substring match. If the wording of the target string in `eligibility.py` changes slightly (e.g., punctuation, capitalization), the test will fail. This is standard for such tests but worth noting for maintainability.

## Compliance Check

1.  **Nothing else in eligibility changes:**
    -   The diff only modifies the `elif n > MAX_WINDOW_SENTENCES` block.
    -   The `n == 0` case (`no_content`) is unchanged (line 16-17).
    -   The `MAX_WINDOW_SENTENCES` constant is unchanged (line 9-10).
    -   **Verdict:** Compliant.

2.  **No other hard length rule depends on this reason:**
    -   The prompt states: "The hard length rules stay elsewhere and are not touched: `package.usable()` refuses a moment over `SEG_MAX_S = 20 s`... the line-up's seconds must land the runtime inside 60-70 s."
    -   The diff removes the *rejection* reason `too_many_sentences`. It does not modify `SEG_MAX_S` or the runtime check.
    -   **Verdict:** Compliant. The change correctly shifts T9 from a hard gate to a soft target, as per Ruling 35.

3.  **`facts["targets_missed"]` is information only:**
    -   The prompt states: "Its only other readers: `moments.py` copies it into the moment's eligibility record, and `eligibility.py:621` appends to it."
    -   The diff appends to `targets` (assumed to be `facts["targets_missed"]`).
    -   **Verdict:** Compliant, assuming `targets` is indeed `facts["targets_missed"]`.

## SHIP: yes with conditions

**Condition:** Verify that the variable `targets` is defined in the local scope of `_span` in `pipeline/eligibility.py` (likely as `targets = facts["targets_missed"]` or similar) before line 439. If `targets` is not a valid local variable, this is a **P0** `NameError` and must be fixed before shipping.

If `targets` is correctly scoped, the change is minimal, compliant with Ruling 35, and correctly demotes the sentence count limit from a hard rejection to a recorded target.