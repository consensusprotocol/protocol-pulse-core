# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 24739 / out 2088 usd~0.106 (upper-bound price)

I’ll walk through the diff against the five concrete checks, then reconcile with the Cycle 1 findings.

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1, I focused heavily on the `speaker_problems` validation gap (K1) and the unmeasured-record path (K2). Looking back at the other models' outputs and the *fixed* diff, I missed or under-weighted two things:

1.  **The `SEALED_LATER` backward-compatibility mechanism (glm P1-1 context / Consensus K1 note).** I noted that `to_pin` now requires speaker records, but I didn't explicitly verify that the *seal* function (`package_pin.seal`) correctly handles the transition from pins that *didn't* have speaker records to those that do. The diff shows `body_of(s)` only includes `SEALED_LATER` keys if they exist in the segment (`if k in s`). This is critical for the `test_every_earlier_pin_still_recomputes...` test. I missed verifying that this logic actually prevents the 6 existing pins from breaking.
2.  **The specific retry logic in `attribute_package` (grok P2 / Consensus K2).** I saw the `seed=8` retry, but I didn't explicitly trace whether a *successful* first call that returns "unknown" (measured=True) would be retried. The code says: `if not sp["measured"] and sp["why"].startswith("not measured")`. This means a *valid* "unknown" verdict (measured=True) is **not** retried. Only *failures* (measured=False) are retried. This is a subtle distinction I glossed over.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **K1 (speaker_problems validation):** **Agree.** The fixed diff implements the stricter validation. `speaker_problems` now checks that a named speaker is in `people`, has a matching `line`, and a matching `role`. This closes the "fabricated line" hole.
*   **K2 (unmeasured records):** **Agree.** The retry logic is present. A failed call (measured=False) is retried once with seed 8. If it fails again, it stays "unknown" with measured=False. This is acceptable because "unknown" claims no name, and the pin is still sealed with the evidence of the failure.
*   **K3 (people/roles):** **Agree.** The code checks that the name is in the line. The role is taken from the verdict. This is documented as a limitation (the role is the model's reading, not code-verified against a dictionary).
*   **glm P1-2 (markdown fences):** **Agree.** The `_json` function in `speakers.py` now strips ```json fences. This is a good fix.
*   **qwen P1 (basis false positives):** **Disagree on severity.** The `_norm` function strips punctuation and lowercases. The check is `nb in _norm(clip) or nb in _norm(around)`. This is a substring match on normalized text. While it *could* theoretically allow a re-ordered phrase to match if the words happen to be contiguous in the normalized string, the prompt explicitly asks for "exact words" and "verbatim". The risk is low because the model is instructed to copy, and the code checks the normalized substring. I downgrade this to P2.
*   **grok P2 (concurrent write):** **Disagree.** The `seal` function in `proof_batch.py` reads the package, attributes speakers, writes the package back, and *then* seals the pin. The pin is sealed from the in-memory `pk` object, not re-read from disk. The file write is for persistence/audit. A concurrent process reading the intermediate file would see a package without speakers, but that's a race condition in the *test harness*, not the production flow. The production flow (proof_ledger, proof_ly) attributes speakers *before* writing the pin. I consider this a P2 test-harness issue, not a production defect.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1: `attribute` does not retry on a *successful* "unknown" verdict.**
In `speakers.py` line 291: `if not sp["measured"] and sp["why"].startswith("not measured")`.
If the model successfully returns `{"name": "unknown", "measured": true, "why": "no evidence"}`, this is **not** retried. This is correct behavior (we don't want to waste money re-asking a model that already gave a valid "unknown"). However, if the model returns a *wrong* "unknown" (e.g., it missed a clear basis), there is no retry. This is acceptable given the cost constraints, but it means the "unknown" rate is entirely dependent on the first model's accuracy.

**P2: `source_lines` includes the channel name as a line.**
In `speakers.py` line 203-204: `out.append(f"channel: {meta['channel_name'].strip()}")`.
The `check` function then verifies that a person's `line` is a substring of one of these lines. If the model proposes a person with `line: "channel: Natalie Brunell"`, it will pass. This is correct. However, if the model proposes a person with `line: "Natalie Brunell"` (without the "channel:" prefix), it will **fail** the check because `"natalie brunell"` is not a substring of `"channel: natalie brunell"`? Wait, `_norm` strips non-alphanumeric. `_norm("channel: Natalie Brunell")` is `"channel natalie brunell"`. `_norm("Natalie Brunell")` is `"natalie brunell"`. `"natalie brunell" in "channel natalie brunell"` is **True**. So it passes. This is fine.

**P2: `context` function uses `E.spoken`.**
In `speakers.py` line 219: `return E.spoken(src.tokens[sents[i][0]:sents[j][1] + 1])`.
I cannot verify `E.spoken` from the diff. If `E.spoken` does not return the exact text of the tokens, the basis check might fail. However, the tests pass, so it likely works.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `speakers.py` | 7/10 | 8/10 | Fence stripping added; retry logic clarified. |
| `package_pin.py` | 6/10 | 9/10 | `speaker_problems` now enforces consistency with `check()`. `SEALED_LATER` handles backward compat. |
| `proof_batch.py` | 7/10 | 8/10 | Flow is clear: build -> attribute -> seal. |
| Tests | 6/10 | 9/10 | New tests cover the specific failure modes (fences, retries, seal integrity). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
None.

**P1 HIGH**
1.  **`pipeline/speakers.py:291`**: Verify that the retry logic does not accidentally skip a *valid* "unknown" that was a false negative. (Currently it doesn't, which is correct, but worth documenting).
2.  **`pipeline/package_pin.py:50-54`**: The `body_of` function relies on `if k in s`. If a segment *should* have a speaker but doesn't (due to a bug in `attribute_package`), `to_pin` will catch it via `speaker_problems`. This is good. No change needed.

**P2 MEDIUM**
1.  **`pipeline/speakers.py:186`**: `_norm` is aggressive. Consider if a basis like "I wrote a book" could match "i wrote a book" in a different context. (Low risk).
2.  **`tests/package/proof_batch.py:416-417`**: The package is written to disk *before* the pin is sealed. If the pin seal fails, the package on disk has speakers, but the pin doesn't exist. This is fine (fail closed), but the log should clearly indicate the pin was not written.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The implementation of `speaker_problems` in `package_pin.py` to enforce that a named speaker must be a member of the `people` list with a matching `line` and `role` is the highest-leverage change. It closes the gap between the model's verdict and the sealed pin, ensuring that no fabricated or inconsistent speaker data can reach the final artifact.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1.  Confirm that `E.spoken` in `eligibility.py` returns the exact text of the tokens (so the basis check is valid).
2.  Ensure that the `SEALED_LATER` mechanism is tested against all 6 existing pins (the test `test_every_earlier_pin_still_recomputes...` does this, but it must pass in CI).
3.  Monitor the "unknown" rate in production. If it is too high, consider adding a second model to the `speaker_verdict` chain or improving the prompt.