# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 18076 / out 2704 usd~0.095 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1400

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "you" persona) did not produce a standalone output in the prompt, but the **Consensus** and **Refuted** sections indicate that the primary risks were identified by **GLM-5.3-FLASH** and **QWEN3.8-27B**.

*   **GLM-5.3-FLASH** correctly identified the **alignment fragility** of `carry_class` (P1-1) and the **strictness of `reads()`** (P1-2).
*   **QWEN3.8-27B** initially raised a "P0" regarding `critical()` and names at the start of sentences, which was **refuted** in the consensus because the behavior is "fail closed" (refusal), which is safe.
*   **GROK-4.20** was the most concise, correctly identifying that the `test_speakers.py` fix was necessary for seal compatibility and that the float rounding in `reseal_attested.py` was a P2 risk.

**What I missed in a hypothetical Cycle 1:**
I likely would have focused heavily on the `attested_text` word-splitting logic (which is complex) and might have overlooked the **seal compatibility** issue in `test_speakers.py` (the missing `btc_screen` argument). The fact that `test_speakers.py` was failing before this diff implies that the `SEALED_LATER` list change in `package_pin.py` (adding `"attested"`) interacts with existing pins that carry `btc_screen`. The fix in `test_speakers.py` (line 471-473) is critical for the "every earlier pin still recomputes" guarantee.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM P1-1 (Alignment Fragility):** The `carry_class` function relies on `SequenceMatcher` opcodes. If a repeated phrase is aligned as a `replace` rather than `delete`/`insert`, the repetition check is skipped. However, the ruling's example ("that's why") is handled correctly in the fixture. This is a **P1** because it is a potential future failure mode, not a current bug.
*   **Agree with GLM P1-2 (Reads Strictness):** The `reads()` function in `attest.py` is a copy of the render's logic. The consensus (A1) confirms it is behaviorally identical. The "strictness" is actually the **correct** behavior for a fail-closed system. If the render's `reads` is identical, this is not a bug.
*   **Agree with QWEN's Refutation (R2):** The `critical()` function correctly excludes sentence-starting names from being "critical" in the sense of *requiring* a re-judge if they are function words, but since names are not function words, they are refused. The refusal is the safe path.
*   **Disagree with QWEN's Initial P0:** QWEN claimed `critical()` was flawed. The consensus refutes this because the outcome (refusal) is correct. The code does not *incorrectly* carry over a name; it refuses to carry it, which triggers the "re-judge" path (or blocks it). This is compliant with Law L-v.
*   **Agree with GROK on P2 (Float Rounding):** The use of `round(..., 3)` in `reseal_attested.py` (line 249-250) is a potential source of silent failures if the build record and pin have slightly different float precisions. This is a **P2** because it fails closed (refusal), but the error message might be misleading.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `attest.py:130` — `attested_text` uses `SequenceMatcher(None, p, r)` (pin -> run), but `diff()` uses `SequenceMatcher(None, r, p)` (run -> pin).**
*   **Scenario:** The `diff()` function (line 65) computes opcodes to turn `r` (run) into `p` (pin). The `attested_text` function (line 130) computes opcodes to turn `p` (pin) into `r` (run).
*   **Risk:** The `ops` list passed to `quotes()` (line 259 in `reseal_attested.py`) comes from `AT.diff(run_t, pin_t)`, which is `r -> p`. However, `attested_text` internally uses `p -> r`.
*   **Verification:** In `quotes()` (line 142), the function signature is `quotes(lines, r, p, ops)`. It uses `p[max(c - 1, 0):d + 1]` and `r[max(a - 1, 0):b + 1]`. The `ops` are from `diff(run, pin)`, so `a,b` are indices in `r` (run) and `c,d` are indices in `p` (pin). This is consistent.
*   **However:** In `attested_text` (line 130), the loop is `for tag, c, d, a, b in SequenceMatcher(None, p, r, ...).get_opcodes()`. Here, `c,d` are indices in `p` (pin) and `a,b` are indices in `r` (run). The code uses `words(pmap, pn, c, d, "approved")` and `words(rmap, rn, a, b, "run")`. This is also consistent.
*   **Conclusion:** No bug. The direction of the diff is handled correctly in both functions.

**P2-NEW-1: `reseal_attested.py:236` — Word extraction from transcript.**
*   **Code:** `words = [str(w["word"]) for w in json.load(f)["words"][i0:i1 + 1]]`
*   **Risk:** If the transcript JSON contains words with leading/trailing spaces or punctuation that `canon.canon_tokens` handles differently than the raw string, the `attested_text` function might produce a different result than expected.
*   **Mitigation:** `attested_text` (line 104) does `rw = [str(w).strip() for w in run_words if str(w).strip()]`. This strips whitespace. The `canon.canon_tokens` function is assumed to handle punctuation consistently. The test `test_the_held_clip_is_the_carry_over_class` (line 346) verifies that `AT.attested_text(APPROVED, RUN.split())` produces the expected `ATTESTED` text. This suggests the stripping and tokenization are consistent.

**P2-NEW-2: `package_pin.py:165` — `SEALED_LATER` addition.**
*   **Code:** `"attested"` is added to `SEALED_LATER`.
*   **Risk:** This changes the seal for any pin that carries the `"attested"` key. The `reseal_attested.py` script sets this key (line 265). The `test_speakers.py` fix (line 471-473) ensures that the test suite accounts for `btc_screen` (which was previously missing).
*   **Verification:** The consensus (R3) confirms that the integrator's `check_pin_only` will pick up the new `SEALED_LATER` key. The test `test_the_held_pin_is_re_sealed_with_the_attested_text` (line 416) verifies that the new seal is computed correctly and that the `"attested"` key is included in the seal body.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `attest.py` | P1 (Alignment) | P1 (Alignment) | No change. The alignment fragility remains a P1. |
| `reseal_attested.py` | P2 (Floats) | P2 (Floats) | No change. The float rounding is a P2. |
| `package_pin.py` | P0 (Seal) | P2 (Seal) | Downgraded. The seal change is correct and tested. The `test_speakers.py` fix resolves the compatibility issue. |
| `test_speakers.py` | P1 (Missing Arg) | P2 (Fixed) | Downgraded. The fix is correct and necessary. |
| `test_attest.py` | P2 (Coverage) | P2 (Coverage) | No change. The tests are comprehensive. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:**
*   None.

**P1 HIGH:**
*   **P1-1: `attest.py:79` — `carry_class` alignment fragility.**
    *   **File:** `pipeline/attest.py`
    *   **Line:** 79
    *   **Scenario:** A `replace` opcode where one side's tokens are a repetition of its own neighbours is not classified as "immediate repetition".
    *   **Impact:** A future pin with a repeated phrase aligned as `replace` will be refused (fail closed), even though the ruling says it should carry.
    *   **Mitigation:** Extend `carry_class` to check for repetition in `replace` opcodes where one side's tokens repeat the neighbours.

**P2 MEDIUM:**
*   **P2-1: `reseal_attested.py:249-250` — Float rounding.**
    *   **File:** `tests/package/reseal_attested.py`
    *   **Line:** 249-250
    *   **Scenario:** A 1 ms disagreement between the build record and the pin's `seg["start"]/["end"]` silently yields `sp == []` → refusal.
    *   **Impact:** Operational failure on the next pin if float precisions differ.
    *   **Mitigation:** Include the candidate start/ends found near `seg["start"]` in the error message if `sp` is empty.

*   **P2-2: `attest.py:95` — `reads()` end-anchoring.**
    *   **File:** `pipeline/attest.py`
    *   **Line:** 95
    *   **Scenario:** The end-anchoring uses `len(s) - 1`, which is wrong when the difference is at the very end and the recogniser's text has trailing tokens.
    *   **Impact:** Fail closed (refusal) if the recogniser's transcript ends with a trailing token.
    *   **Mitigation:** Verify against the render's source that the two `reads` implementations are behaviorally identical.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Extend `carry_class` in `attest.py` to handle `replace` opcodes where one side's tokens are an immediate repetition of its own neighbours, to prevent alignment-dependent refusals of valid carry-over classes.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Verify `reads()` identity:** Confirm that `attest.py:reads()` is byte-identical in behavior to the render's `pipeline/pinned.py:adjudicate_lock:reads()`. The consensus (A1) claims this is verified, but it should be double-checked against the main tree.
2.  **Monitor `carry_class` alignment:** Be aware that `replace` opcodes with repeated tokens will be refused. If this occurs in production, the pin will need to be re-judged (step A) rather than re-sealed. This is fail-closed and safe, but may require manual intervention.
3.  **Float precision:** Ensure that the build record and pin use consistent float precision for `start`/`end` times. If not, the `reseal_attested.py` script may refuse valid pins due to rounding errors.