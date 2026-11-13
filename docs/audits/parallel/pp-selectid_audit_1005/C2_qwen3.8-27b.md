# qwen3.8-27b (qwen/qwen3.8-27b) 42 s finish=stop usage in 8123 / out 1542 usd~0.047 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1005

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "you" persona) likely focused on the logical flow of the derivation. The other models, specifically **GLM-5.3-FLASH**, correctly identified a subtle structural risk: the addition of the `hook_rule` key to the verdict dictionary (`package.py:85`). While I noted that downstream readers use key-lookup, GLM explicitly flagged the *possibility* of a strict schema consumer (like an attestation logger) that might reject the new key.

**Grok-4.20** and **Qwen3.8** were more decisive, confirming that the "clips-alone" verdict (`medley()`) was untouched and that the coherence contract was correctly tightened. They did not miss anything critical that I would have missed, but their brevity in Cycle 1 lacked the specific line-by-line verification of the `clip_keys` injection into the prompt that GLM provided.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (P1: `hook_rule` key):** **Agree with the finding, but disagree with the severity.**
    *   *Why:* The diff shows `v = dict(v, clips={...}, hook_rule=HOOK_RULE)`. This adds a key to the returned verdict. However, the Cycle 1 Consensus (Claude) explicitly verified that *no* consumer in `package.py` performs an exact key-set comparison on the coherence verdict. The readers use `.get("clips")`, `.get("vo_point")`, etc. The `inventory()` function records status/backend, not the raw verdict dict. Therefore, this is a **P2 (Observation)** at most, not a P1. It is safe to ship.
*   **Grok-4.20 (No P0/P1, SHIP: yes):** **Agree.**
    *   *Why:* The logic is sound. The contract is strict. The derivation is correct.
*   **Qwen3.8 (No P0/P1, SHIP: yes):** **Agree.**
    *   *Why:* Correctly identified that `labs[1:]` is used for the prompt keys and the contract check, ensuring the hook is excluded from the "through-line" rating but included in the final `min()` via the derived value.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2 — `package.py:69` — Prompt Injection Safety / Formatting Edge Case.**
The line `clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])` constructs the JSON template for the prompt.
*   *Scenario:* If a label in `pk["segments"]` contains a double quote `"` or a backslash `\`, the generated prompt will be malformed JSON, potentially confusing the LLM or causing a parse error in the model's response (which would then be caught by the contract check as `ValueError`).
*   *Mitigation:* The contract check (`set(v["clips"]) != set(labs[1:])`) will fail if the model returns keys that don't match the labels. If the prompt is malformed, the model might return garbage, which is caught. This is **fail-closed**.
*   *Verdict:* Low risk. Labels are typically generated internally (e.g., "hook", "clip_01"). If they are user-provided, this is a potential vector for prompt confusion, but not a security breach or logic error. **No change required** unless labels are user-controlled free-text.

**P2 — `package.py:85` — `hook_rule` Key Persistence.**
As noted by GLM, the `hook_rule` key is added to the verdict.
*   *Scenario:* If this verdict is serialized to a database or log file that has a strict schema validation (e.g., Pydantic model with `extra="forbid"`), it will fail.
*   *Mitigation:* The codebase style (seen in `medley()`) suggests that verdicts are often passed around as dicts. The Cycle 1 consensus confirmed no strict schema check exists *in the current codebase*.
*   *Verdict:* **Acceptable.** It provides useful metadata for debugging.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Contract Validation** | Pass | Pass | Strictly enforces `hook` parts and `clips` keys. Fail-closed behavior confirmed. |
| **Derivation Logic** | Pass | Pass | `min(v["hook"][k] for k in HOOK_PARTS)` correctly implements Ruling 52. |
| **Prompt Consistency** | Pass | Pass | `HOOK_QUESTION` is single-sourced. `MEDLEY_PROMPT` byte-identity verified by tests. |
| **Downstream Compatibility** | Pass | Pass | `hook_rule` key addition is benign for current consumers. |
| **Test Coverage** | Pass | Pass | `TestCoherenceHookRating` covers pass/fail, derivation, and malformed inputs. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`package.py:85`**: The `hook_rule` key is added to the verdict dict. Ensure that any external logging/attestation systems that consume this verdict do not have strict schema validation that rejects unknown keys. (Likely safe, but worth a manual check if such systems exist outside this repo).
2.  **`package.py:69`**: The `clip_keys` string interpolation assumes labels are safe for JSON embedding. If labels can contain quotes, the prompt will be malformed. (Low risk given internal label generation).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The extraction of `HOOK_QUESTION` into a single constant and its injection into both `MEDLEY_PROMPT` and `COHERENCE_PROMPT` is the highest-leverage change. It guarantees that the "job" of the hook is defined identically in both verdicts, preventing drift and ensuring that the derived rating in `coherence()` is based on the same criteria as `medley()`.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  Confirm that no external system (outside `package.py`) performs strict key-set validation on the coherence verdict dict that would reject the new `hook_rule` key. (Based on Cycle 1 consensus, this is likely not the case).
2.  Ensure that `pk["segments"]` labels are sanitized or generated internally to prevent JSON injection into the prompt via `clip_keys`. (Standard practice, likely already in place).

The code correctly implements Ruling 52 for the coherence verdict. The contract is strict, the derivation is correct, and the tests cover the critical paths. The clips-alone verdict is unchanged.