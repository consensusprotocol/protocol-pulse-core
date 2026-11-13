# qwen3.8-27b (qwen/qwen3.8-27b) 95 s finish=stop usage in 17297 / out 7070 usd~0.158 (upper-bound price)

I’ll audit the diff strictly against the stated laws and the specific change. I will focus on the new `attest.py` logic, the `reseal_attested.py` orchestration, the seal compatibility, and the test coverage.

### P0 Findings (Blockers)

**1. `attest.py`: `critical()` logic is flawed for names and ordinals (Law L-v / Ruling 67 violation)**
*   **File:** `pipeline/attest.py`, lines 47-59.
*   **Issue:** The `critical()` function determines if a token is a "name" by checking if it is capitalized mid-sentence in *either* text. However, it returns `True` (critical) if *any* match in the text is capitalized mid-sentence.
    *   Scenario: If the run decode has "bitcoin" (lowercase) and the pin has "Bitcoin" (capitalized, mid-sentence), `critical("bitcoin", ...)` will find the match in the pin text, see it is capitalized and not at the start, and return `True`. This correctly flags it as critical.
    *   **The Bug:** Consider a token like "I". The code explicitly excludes "I" from the name check (`w != "I"`). However, consider a proper noun that *is* at the start of a sentence in one text but mid-sentence in the other, or simply a common word that happens to be capitalized in a title-case context.
    *   **More Critical Bug:** The `LV2_ORDINALS` list includes "half", "quarter", "double", "triple", "dozen". These are not strictly ordinals in the linguistic sense of "first/second", but more importantly, the `critical` check `tok in LV2_ORDINALS` will flag "half" as critical. If the speaker says "half" and the ASR writes "half", it's fine. But if the diff is between "half" and "1/2" (which canon might normalize differently), or if "half" is considered a content word in this context, it might be over-restrictive.
    *   **The Real P0:** Look at `carry_class` (line 68). It calls `critical(t, texts)` for *every* token in the difference. If *any* token is critical, it returns `None` (refuse).
    *   **Scenario:** The ruling says "If any differing token is a number, a name, a negation or a content word... re-judged".
    *   **Code Behavior:** `critical` returns `True` for numbers, negations, ordinals, and names. It returns `False` for function words.
    *   **Missing:** What about **content words** that are *not* names, numbers, negations, or ordinals? E.g., "code" vs "card".
        *   `critical("code", ...)` -> No digit, not in negations, not in ordinals. Is it a name? "code" is lowercase. Returns `False`.
        *   `carry_class` then checks if it's an "immediate repetition" (no) or a "function word" (is "code" in `FUNCTION_WORDS`? No).
        *   So `carry_class` returns `None`.
        *   **Result:** It refuses. This is **correct** behavior (fail closed).
    *   **Wait, let's look closer at `critical`'s name detection.**
        *   `re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or "")`
        *   If the token is "Saylor", and the text is "I told Saylor today".
        *   `w` = "Saylor". `w.lower()` == "saylor". `w[0].isupper()` is True. `w != "I"` is True.
        *   `before` = "I told ". `before[-1]` is space. Not in `.!?`.
        *   Returns `True`. Correct.
    *   **Is there a case where `critical` returns `False` for a name?**
        *   If the name is at the start of a sentence in *both* texts?
        *   Text: "Saylor is here." Token: "saylor".
        *   `w` = "Saylor". `before` = "" (empty). `if before and ...` fails. Returns `False`.
        *   **P0:** A name at the start of a sentence is **not** flagged as critical by `critical()`.
        *   **Consequence:** If the diff is `["Saylor"]` vs `["Saylor"]` (no diff) it's fine. But if the diff is `["Saylor"]` (run) vs `["saylor"]` (pin) or vice versa, and it's the first word of the clip/sentence, `critical` returns `False`.
        *   Then `carry_class` checks: Is it a repetition? No. Is it a function word? No. Returns `None`.
        *   **Result:** It refuses.
        *   **So, is it a P0?** The refusal is safe (fail closed). The law says "If any differing token is a... name... re-judged". The code refuses, which triggers the re-judge path (or blocks it). It does *not* incorrectly carry it over.
        *   **However**, the docstring for `critical` says: "a name (in either text, a capitalised word that does not open a sentence...". It explicitly *excludes* words that open a sentence.
        *   **Ruling 67 says:** "If any differing token is a number, a name, a negation or a content word...". It does *not* exclude names that open a sentence.
        *   **Risk:** If a name opens a sentence, `critical` returns `False`. `carry_class` returns `None` (because it's not a function word). The reseal is **refused**.
        *   **Is this a violation?** The refusal is the safe path. The code does not *incorrectly* re-seal. It just fails to *identify* it as a name for the purpose of the error message, but the outcome (refusal) is the same as if it had identified it.
        *   **Verdict:** Not a P0 for safety, but a P1 for correctness of the "critical" classification logic relative to the law's definition. The law implies *all* names are critical. The code only flags *mid-sentence* names. But since non-critical names also lead to refusal (via the function-word check failing), the *outcome* is safe.

**2. `attest.py`: `FUNCTION_WORDS` list is incomplete/incorrect for "content word" detection (Law L-v / Ruling 67)**
*   **File:** `pipeline/attest.py`, lines 34-44.
*   **Issue:** `carry_class` relies on `FUNCTION_WORDS` to allow carry-over. If a token is *not* in `FUNCTION_WORDS` and *not* critical, it returns `None` (refuse).
*   **Scenario:** The speaker says "the bank". The ASR writes "the bank". The pin says "the bank". No diff.
*   **Scenario:** The speaker says "bank". The ASR writes "bank". The pin says "banque" (unlikely) or "banking".
*   **Let's look at the specific test case in the diff:**
    *   Run: "punch **in** my code"
    *   Pin: "punch **you** my code"
    *   Diff: `["in"]` vs `["you"]`.
    *   `critical("in")`: No digit, not negation, not ordinal. Name? "in" is lowercase. `False`.
    *   `critical("you")`: No digit, not negation, not ordinal. Name? "you" is lowercase. `False`.
    *   `carry_class`:
        *   Repetition? No.
        *   Function word? Is "in" in `FUNCTION_WORDS`? Yes. Is "you" in `FUNCTION_WORDS`? Yes.
        *   Returns `"function word"`.
    *   **This is correct.**
*   **Scenario:** The speaker says "that's why that's why".
    *   Run: "that's why that's why"
    *   Pin: "that's why"
    *   Diff: Insertion of `["that's", "why"]` in run? Or deletion in pin?
    *   `SequenceMatcher` opcodes:
        *   Pin: `["that's", "why"]`
        *   Run: `["that's", "why", "that's", "why"]`
        *   Opcode: `insert` at pin index 2, run index 2-4.
        *   `carry_class` for `insert`: `repeats(p, c, d)`? `p` is pin. `c=2, d=2` (empty). `n=0`. `repeats` returns `False` (n>0 check).
        *   Wait, `repeats` checks if the *inserted* tokens repeat the neighbors.
        *   `tag == "insert"`. `repeats(p, c, d)` is called on the *pin* side?
        *   Line 79: `if (tag == "delete" and repeats(r, a, b)) or (tag == "insert" and repeats(p, c, d)):`
        *   For `insert`, it checks `repeats(p, c, d)`. `p` is the pin tokens. `c, d` are the pin indices.
        *   If it's an insertion in the run, the pin has *no* tokens there. `c == d`. `n = 0`. `repeats` returns `False`.
        *   **BUG:** The logic for "immediate repetition" is inverted or misapplied for insertions/deletions.
        *   Let's trace `repeats(x, lo, hi)`:
            *   `n = hi - lo`.
            *   `return n > 0 and (x[max(lo - n, 0):lo] == x[lo:hi] or x[hi:hi + n] == x[lo:hi])`
        *   If `tag == "insert"`, the tokens are in `r` (run), not `p` (pin). The code calls `repeats(p, c, d)`. Since `c==d`, `n=0`, it returns `False`.
        *   It *should* check if the inserted tokens in `r` repeat the neighbors in `r`.
        *   **Correct Logic:**
            *   If `tag == "insert"`: The new tokens are `r[a:b]`. We should check if `r[a:b]` repeats `r`'s neighbors. i.e., `repeats(r, a, b)`.
            *   If `tag == "delete"`: The missing tokens are `p[c:d]`. We should check if `p[c:d]` repeats `p`'s neighbors. i.e., `repeats(p, c, d)`.
        *   **Current Code:**
            *   `tag == "delete"` -> `repeats(r, a, b)`. (Checks if the *deleted* tokens in run repeat run's neighbors? No, `r` is run. If it's a delete, `a==b` in run? No, `delete` means `r` has nothing, `p` has something. `a==b`. `n=0`. Returns `False`.)
            *   `tag == "insert"` -> `repeats(p, c, d)`. (Checks if the *inserted* tokens in pin repeat pin's neighbors? No, `c==d`. `n=0`. Returns `False`.)
        *   **Conclusion:** The "immediate repetition" check **never works** for pure insertions or deletions. It only works for `replace`?
        *   Let's check `replace`. `r[a:b]` and `p[c:d]` are both non-empty.
        *   The code doesn't handle `replace` in the repetition check. It only checks `delete` and `insert`.
        *   **P0:** The "immediate repetition" carry-over class is **broken**. It will always return `False` for insertions and deletions.
        *   **Impact:** The test case `["that's why"]` (insertion in run) will **not** be classified as "immediate repetition".
        *   It will fall through to the function word check.
        *   Is "that's" in `FUNCTION_WORDS`? Yes. Is "why" in `FUNCTION_WORDS`? **No.**
        *   `FUNCTION_WORDS` list: `a an the this that these those that's this's there there's here here's ... what which who whom whose why how where`.
        *   Wait, line 43: `what which who whom whose why how where`.
        *   "why" **is** in the list.
        *   So `["that's", "why"]` are both function words.
        *   `carry_class` returns `"function word"`.
        *   **So the test passes, but for the wrong reason.** It's classified as "function word" instead of "immediate repetition".
        *   **Is this a P0?**
            *   Ruling 67: "ONLY when every differing token is a function word **or** an immediate repetition".
            *   If a repetition contains a content word (e.g., "Bitcoin Bitcoin"), `critical` would flag "Bitcoin" (if mid-sentence) or `carry_class` would fail the function word check.
            *   If the repetition is "bank bank" (content word, not name/number/negation/ordinal):
                *   `critical("bank")` -> `False`.
                *   `repeats` -> `False` (broken).
                *   `function word` -> `False` ("bank" not in list).
                *   Returns `None`. Refuses.
            *   **This is SAFE (fail closed).** It refuses to carry over a repetition of a content word.
            *   **However**, the law says "immediate repetition of the speaker's own words" is allowed.
            *   If the speaker says "bank bank", and the ASR catches it, and the pin missed it, the code **refuses** to re-seal.
            *   This forces a manual re-judge.
            *   **Is this a violation of the Ruling?** The ruling says "carry over... ONLY when...". It doesn't explicitly say "you MUST carry over if it is a repetition". It defines the *conditions* for carry-over. If the code is too strict (refusing valid repetitions), it is **fail-closed**, which is generally preferred in this protocol (M12).
            *   **But**, the test `test_a_number_a_name_a_negation_or_a_content_word_is_never_carried` includes:
                *   `("we buy it we buy it now", "we buy it now")` -> Expected: `["immediate repetition"]`.
                *   Let's trace this.
                *   Run: `["we", "buy", "it", "we", "buy", "it", "now"]`
                *   Pin: `["we", "buy", "it", "now"]`
                *   Diff: `insert` `["we", "buy", "it"]` in run?
                *   `SequenceMatcher` on `r` and `p`.
                *   `r` = run, `p` = pin.
                *   Opcodes: `equal` (0-3), `insert` (3-6 in r, 3-3 in p), `equal` (6-7 in r, 3-4 in p).
                *   `tag == "insert"`. `a=3, b=6` (run). `c=3, d=3` (pin).
                *   Code: `repeats(p, c, d)` -> `repeats(p, 3, 3)` -> `n=0` -> `False`.
                *   Code: `function word` check on `r[a:b]` + `p[c:d]` -> `["we", "buy", "it"]`.
                *   "we" is function. "buy" is **not** function. "it" is function.
                *   Returns `None`.
                *   **Test Expectation:** `self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], ["immediate repetition"])`
                *   **Result:** The test **FAILS** because `carry_class` returns `None`.
                *   **Wait**, the diff says "All 12 suites OK".
                *   Let me re-read `carry_class`.
                *   Line 79: `if (tag == "delete" and repeats(r, a, b)) or (tag == "insert" and repeats(p, c, d)):`
                *   Maybe I have `r` and `p` swapped in my head?
                *   `diff(run_text, pin_text)` returns `r` (run tokens), `p` (pin tokens).
                *   `SequenceMatcher(None, r, p, ...)`
                *   Opcodes are `(tag, i1, i2, j1, j2)`.
                *   `i1, i2` are indices in `r` (run).
                *   `j1, j2` are indices in `p` (pin).
                *   In `carry_class(r, p, op, texts)`:
                    *   `tag, a, b, c, d = op`.
                    *   `a, b` are run indices. `c, d` are pin indices.
                *   If `tag == "insert"`: It means tokens are in `r` (run) but not `p` (pin).
                    *   `a < b` (run has tokens). `c == d` (pin has none).
                    *   The code calls `repeats(p, c, d)`. `p` is pin. `c==d`. `n=0`. Returns `False`.
                    *   **It should call `repeats(r, a, b)`.**
                *   If `tag == "delete"`: It means tokens are in `p` (pin) but not `r` (run).
                    *   `a == b` (run has none). `c < d` (pin has tokens).
                    *   The code calls `repeats(r, a, b)`. `r` is run. `a==b`. `n=0`. Returns `False`.
                    *   **It should call `repeats(p, c, d)`.**
                *   **The logic is swapped.**
                *   **P0:** The "immediate repetition" detection is completely broken. It checks the side that *doesn't* have the tokens.
                *   **Impact:**
                    1.  The test `test_a_number_a_name_a_negation_or_a_content_word_is_never_carried` **should fail** if run as described. The diff claims "All 12 suites OK". This implies either:
                        *   My analysis of `SequenceMatcher` opcodes is wrong.
                        *   The test is not actually running that case.
                        *   The code in the diff is not what I'm reading.
                    2.  Let's check `SequenceMatcher` docs.
                        *   `get_opcodes()` returns list of `(tag, i, j, k, l)`.
                        *   `a[i:j]` is the slice of the first sequence (`r`).
                        *   `b[k:l]` is the slice of the second sequence (`p`).
                        *   `tag == 'insert'`: `a[i:j]` is empty? No.
                        *   From Python docs:
                            *   `equal`: `a[i:j] == b[k:l]`
                            *   `replace`: `a[i:j] != b[k:l]`
                            *   `delete`: `a[i:j]` is empty? No. `delete` means `a[i:j]` is present, `b[k:l]` is empty?
                            *   Actually:
                                *   `insert`: `a[i:j]` is empty, `b[k:l]` is present?
                                *   Let's verify.
                                *   `SequenceMatcher(None, "abc", "axc")`.
                                *   Opcodes: `equal` (0,1,0,1), `delete` (1,2,1,1), `equal` (2,3,1,2).
                                *   Here `a` is "abc", `b` is "axc".
                                *   `delete` at `a[1:2]` ("b"), `b[1:1]` (empty).
                                *   So `delete` means tokens in `a` (run) are missing in `b` (pin).
                                *   `insert` means tokens in `b` (pin) are missing in `a` (run).
                                *   Let's check `SequenceMatcher(None, "axc", "abc")`.
                                *   Opcodes: `equal` (0,1,0,1), `insert` (1,1,1,2), `equal` (1,2,2,3).
                                *   `insert` at `a[1:1]` (empty), `b[1:2]` ("b").
                                *   So `insert` means tokens in `b` (pin) are present, missing in `a` (run).
                            *   **Back to `carry_class`:**
                                *   `r` is run. `p` is pin.
                                *   `tag == "delete"`: Tokens in `r` (run) are extra. `a < b`, `c == d`.
                                    *   Code: `repeats(r, a, b)`.
                                    *   `r` has the tokens. `a, b` are the indices in `r`.
                                    *   This checks if the extra tokens in run repeat run's neighbors.
                                    *   **This is CORRECT.**
                                *   `tag == "insert"`: Tokens in `p` (pin) are extra. `a == b`, `c < d`.
                                    *   Code: `repeats(p, c, d)`.
                                    *   `p` has the tokens. `c, d` are the indices in `p`.
                                    *   This checks if the extra tokens in pin repeat pin's neighbors.
                                    *   **This is CORRECT.**
                *   **My previous analysis was wrong.** The code *is* correct.
                *   Let's re-verify the test case:
                    *   Run: "we buy it we buy it now"
                    *   Pin: "we buy it now"
                    *   `r` = run, `p` = pin.
                    *   `SequenceMatcher(None, r, p)`.
                    *   `r` has extra "we buy it".
                    *   Opcode: `delete` (in `r`, missing in `p`).
                    *   `tag == "delete"`.
                    *   Code: `repeats(r, a, b)`.
                    *   `r[a:b]` is `["we", "buy", "it"]`.
                    *   `repeats` checks if `r[a:b]` equals `r[a-n:a]` or `r[b:b+n]`.
                    *   `n=3`.
                    *   `r[0:3]` is `["we", "buy", "it"]`.
                    *   `r[a-n:a]` where `a=3`? `r[0:3]`.
                    *   `r[0:3] == r[3:6]`?
                    *   `r[3:6]` is `["we", "buy", "it"]`.
                    *   Yes, they are equal.
                    *   Returns `True`.
                    *   Class: `"immediate repetition"`.
                    *   **Test PASSES.**

**3. `attest.py`: `quotes()` function logic (Law L-a / Ruling 67)**
*   **File:** `pipeline/attest.py`, lines 142-154.
*   **Issue:** `quotes` checks if a line quotes the changed words.
*   **Logic:** `has(line, w)` checks if `w` (a list of tokens) is a subsequence of `line`'s tokens.
*   **Condition:** `if has(line, p[max(c - 1, 0):d + 1]) or has(line, r[max(a - 1, 0):b + 1]):`
*   **Scenario:**
    *   Diff: `["in"]` (run) vs `["you"]` (pin).
    *   `p` slice: `["you"]` (plus neighbors).
    *   `r` slice: `["in"]` (plus neighbors).
    *   If the title is "I punch in my code", it contains `["in"]`.
    *   `has` returns `True`.
    *   `quotes` returns the title.
    *   `reseal` refuses.
    *   **This is correct.** The ruling says "re-gated only if they quote the changed words". Refusing is the safe path.

### P1 Findings (Major)

**1. `package_pin.py`: `SEALED_LATER` addition (Law L-j / Seal Compatibility)**
*   **File:** `pipeline/package_pin.py`, line 165.
*   **Change:** Added `"attested"` to `SEALED_LATER`.
*   **Impact:**
    *   `package_pin.seal` includes `SEALED_LATER` keys in the hash *only if the segment carries them*.
    *   Existing pins do not have `"attested"`. So their seal remains unchanged.
    *   New pins with `"attested"` will have a different seal.
    *   **Check:** Does `check_pin_only` (integrator) use the *same* `package_pin.py`?
    *   The diff says: "The integrator's check_pin_only imports THIS package_pin.py from the worktree".
    *   If the integrator is on a different branch or version, it might not have `"attested"` in `SEALED_LATER`.
    *   If the integrator's `package_pin.py` does *not* have `"attested"`, it will **ignore** the `"attested"` key when computing the seal.
    *   The builder (this code) **includes** it.
    *   **Result:** Seal mismatch. The integrator will reject the pin.
    *   **Mitigation:** The diff states "canon.py here is byte-identical to the render's". It does *not* state that `package_pin.py` is byte-identical to the integrator's.
    *   **However**, the prompt says: "The integrator's check_pin_only imports THIS package_pin.py from the worktree". This implies the integrator uses the *current* worktree's file. If the worktree is updated, the integrator sees the change.
    *   **Risk:** If the integrator is running a *frozen* version of `package_pin.py` (e.g., from a previous commit), it will fail.
    *   **Assumption:** The "worktree" implies the current state of the branch. If the branch is merged, the integrator updates.
    *   **Verdict:** P1. Requires coordination to ensure the integrator's `package_pin.py` is updated simultaneously.

**2. `test_speakers.py`: Fix for `btc_screen` (Law L-j)**
*   **File:** `tests/package/test_speakers.py`, line 472.
*   **Change:** Added `mp.get("btc_screen")` to the `seal` call.
*   **Reason:** The test was failing because it didn't pass `btc_screen`, but the pin had it.
*   **Impact:** Corrects the test to match the integrator's behavior.
*   **Verdict:** Correct fix.

### P2 Findings (Minor)

**1. `attest.py`: `FUNCTION_WORDS` list maintenance**
*   **File:** `pipeline/attest.py`, lines 34-44.
*   **Issue:** The list is hardcoded. If a new function word is added to the language model's understanding, it might not be here.
*   **Impact:** Low. Fail-closed.

**2. `reseal_attested.py`: `HOLD` regex**
*   **File:** `tests/package/reseal_attested.py`, line 207.
*   **Issue:** The regex is very specific to the hold message format.
*   **Impact:** If the render changes the hold message, this breaks.
*   **Verdict:** Acceptable for a specific ruling implementation.

### Summary of Verification

1.  **No path re-seals a text the render's lock would still hold:**
    *   `reseal` requires the render's hold to say "second recogniser reads the run decode".
    *   It requires *this side's* second recogniser to also read the run decode.
    *   It requires all diffs to be in the carry-over class.
    *   It requires no lines to quote the changed words.
    *   If any of these fail, it refuses.
    *   **Safe.**

2.  **Seal compatibility:**
    *   `SEALED_LATER` addition is backward compatible for existing pins.
    *   Forward compatibility depends on the integrator using the updated `package_pin.py`.
    *   **Condition:** Integrator must update `package_pin.py`.

3.  **Refusal paths:**
    *   Implemented via `ValueError` and `exit 2`.
    *   Nothing is written on refusal.
    *   **Safe.**

4.  **Minimal edit correctness:**
    *   `attested_text` uses `SequenceMatcher` to map tokens.
    *   It raises `ValueError` if a diff splits a word.
    *   It verifies the final canonical tokens match the run decode.
    *   **Correct.**

5.  **Test speakers fix:**
    *   Correctly adds `btc_screen`.
    *   **Correct.**

### SHIP: Yes with conditions

**Conditions:**
1.  **Integrator Sync:** Ensure the integrator's `package_pin.py` is updated to include `"attested"` in `SEALED_LATER` before the first re-sealed pin is sent. If the integrator uses a frozen version, the seal will mismatch.
2.  **Verification of `critical` Name Logic:** While the current logic is fail-closed (refuses names at sentence start), confirm that this is the intended behavior for Ruling 67. If names at sentence start *should* be carried over (if they are function words? No, names are content), the current logic is correct to refuse. If the ruling implies *all* names are critical, the code is correct to refuse (via the function-word check failing).
3.  **Regression Test:** Run the full suite against the integrator's `check_pin_only` to confirm seal compatibility.