# qwen3.8-27b (qwen/qwen3.8-27b) 55 s finish=stop usage in 15163 / out 1817 usd~0.073 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0426

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (GLM-5.3-FLASH) correctly identified the structural risk of the "sealed vs. judged" screen divergence (P1-1) and the unverified `BITCOIN` definition (P1-2). However, I missed the **implementation details of the fix** that are now present in the C2 diff. Specifically:
*   I did not verify that `screen_problems` in `package_pin.py` now explicitly enforces the coupling between the sealed pattern and the judged pattern (line 162-163).
*   I did not verify that the `inventory` function in `package.py` now records the `screen` and `medley_names_bitcoin` into the gate row (lines 108-109), which is the mechanism that allows `screen_problems` to perform its check.
*   I did not verify that the `seal` function correctly handles the optional `btc_screen` argument to maintain backward compatibility for old pins (lines 138-139).

Grok-4.20 was overly optimistic ("SHIP: yes" with no findings), missing the subtle coupling risks that I flagged. Qwen3.8-27B was overly pessimistic, flagging a `NameError` for `BITCOIN` in `stand_alone.py` which was refuted by the consensus (the constant exists in the base file).

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (Me, C1):** **Agree with my own P1-1 and P1-2.** The C2 diff implements the mitigations I suggested. The `screen_problems` check now ties the sealed pattern to the judged pattern. The `BITCOIN` constant is confirmed to exist in `stand_alone.py` (base file) and is used correctly.
*   **GROK-4.20-0309-REASONING:** **Disagree with "no P1".** While the code is correct, the coupling between the judged screen and the sealed screen is a critical invariant that was previously only "by construction." The new `screen_problems` check makes it explicit, but this is a significant change that warrants a P1 note in the audit trail to ensure it is understood.
*   **QWEN3.8-27B:** **Disagree with P0-1 (NameError).** The `BITCOIN` constant is defined in `stand_alone.py` (base file, line 27 per consensus). The diff does not need to show it. The tests pass, which confirms it is defined.
*   **QWEN3.8-27B:** **Disagree with P0-3 (no_topic logic).** The consensus verified that `topical()`'s completion rule is maximal when the previous segment names Bitcoin. `no_topic` correctly drops only moments that cannot take any place.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1 — `package_pin.py:162-163` (`screen_problems`): The check `judged != pat` relies on the `stand_alone` gate row having a `screen` key.**
If a future change to `stand_alone_check` or `inventory` fails to record the `screen` in the gate row, `judged` will be `None`, and `screen_problems` will refuse the pin with a clear error. This is fail-closed behavior, which is good. However, the error message `f"btc_screen: the sealed pattern is not the one the stand_alone row judged with ({judged!r})"` will show `None` if the key is missing, which is slightly confusing but acceptable. No change needed.

**P2-2 — `package.py:108-109` (`inventory`): The `screen` and `medley_names_bitcoin` are added to the `stand_alone` gate row.**
This is a new field in the gate row. The `gate_problems` function in `package_pin.py` checks for required gates and their status, but does it validate the structure of the `stand_alone` row? The diff does not show `gate_problems` being modified to check for the presence of `screen` or `medley_names_bitcoin`. However, `screen_problems` is called separately in `to_pin` and checks the `pk` (package) directly, not the gate row. Wait, `screen_problems` reads `pk.get("gates")...get("stand_alone")...get("screen")`. So it does read from the gate row. If the gate row is missing the `screen` key, `judged` is `None`, and the pin is refused. This is correct.

**P2-3 — `stand_alone.py:247` (`check_edl`): The `medley_names_bitcoin` check uses `BITCOIN.search`.**
The `BITCOIN` constant is `\b(bitcoin|btc)\b`. The ruling says "bitcoin / btc". This matches. The test `test_the_screen_is_the_topic_and_the_medley_must_name_bitcoin` verifies that "Saylor keeps buying Bitcoin" passes and "Saylor keeps buying" fails. This is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `stand_alone.py` | P1 (unverified BITCOIN) | P2 | `BITCOIN` confirmed in base file. `topical_screen` and `check_edl` are byte-identical to render. |
| `eligibility.py` | P1 (hook rule) | P2 | Hook rule correctly uses `BTC_SCREEN`. Clip rule correctly removed. |
| `package.py` | P1 (no_topic logic) | P2 | `no_topic` logic verified as maximal. `stand_alone_check` correctly passes screen. |
| `package_pin.py` | P1 (seal/judge coupling) | P2 | `screen_problems` now explicitly enforces the coupling. `seal` handles optional screen. |
| Tests | P1 (missing hook case) | P2 | Hook case tested. Mirror test for miner's file included. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`package_pin.py:162-163`**: The `screen_problems` check is a new invariant. Ensure that any future changes to `stand_alone_check` or `inventory` continue to record the `screen` in the gate row. (No code change needed, just a note for future maintainers.)
2.  **`stand_alone.py:247`**: The `medley_names_bitcoin` check is a new rule. Ensure that the `BITCOIN` constant remains in sync with the ruling's definition of "bitcoin / btc". (No code change needed, just a note.)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of `screen_problems` in `package_pin.py` which explicitly verifies that the sealed `btc_screen.pattern` matches the pattern recorded in the `stand_alone` gate row, thereby preventing the "sealed vs. judged" divergence that was the primary risk in Cycle 1.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements Ruling 34:
1.  The pin stage's check (`stand_alone_check`) uses the same `BTC_SCREEN` as the render.
2.  The sealed screen is exactly the one the line-up was judged with (enforced by `screen_problems`).
3.  Old pins still recompute (the `seal` function handles the optional `btc_screen` argument).
4.  `no_topic` drops only moments that can take no place under the render's rule.
5.  The story path (no screen) is unchanged.

All tests pass, and the consensus from Cycle 1 has been addressed.