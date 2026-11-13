# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 10893 / out 2978 usd~0.077 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0712
# Reviewer: GLM-5.3-FLASH (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Grok's P2 (hard-coded `True` vs. constant):** I missed this in Cycle 1. I noted that `scorer_pending: True` was written unconditionally inside the conditional spread, but I did not flag the divergence between the *emission* side (hard-coded `True`) and the *check* side (gated by `TRIM_SCORER_PENDING`). Grok correctly identified that if `TRIM_SCORER_PENDING` were toggled to `False` in-process, the package row would still emit `scorer_pending: True`, creating a mismatch where the pin claims pending but the render's `stand_alone_check` would fail closed. **The Cycle 1 consensus (F1) fixed this** by changing the emission to `bool(TRIM_SCORER_PENDING)`. I now verify this fix is present in the diff at `package.py:32`.

**Qwen's detailed re-reading of `trim_problems` control flow:** Qwen walked through the `has_w`/`has_s` logic more explicitly than I did, confirming that a segment with only one of the two trim keys still reaches the `scorer_pending` check (line 100) before the pairing refusal (line 103). I had noted this in P2-2 but was less explicit about the ordering. Qwen's analysis confirms the logic is robust: all issues are collected, not short-circuited.

**Grok's observation on the "integrator says when" clause:** Grok noted that the diff contains no code path that raises `TRIMMED_PER_*_MAX` after affirmation — it is purely a comment/STATE matter. I had assumed this was out of scope for the diff, but Grok is right to flag it as a condition for the integrator.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My Position |
|---|---|
| **Grok P2 (hard-coded True)** | **Agree.** This was a real P1-level issue in Cycle 1 (the pin could claim pending when the switch said strict). The fix in the current diff (`bool(TRIM_SCORER_PENDING)`) resolves it. I now verify the fix is correct. |
| **Qwen P2-1 (constant duplication)** | **Agree.** `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` are separate literals. The equality test (`test_medley.py:153`) catches drift, but a single source of truth would be cleaner. The consensus (A3) explains why they are kept separate: `package_pin` must not import `package` to avoid pulling heavy dependencies into the integrator's `check_pin_only` process. This is a valid architectural constraint. **P2, not P1.** |
| **Qwen P2-2 (trim_problems logic)** | **Agree.** The logic is correct. A segment with `trimmed_leading` but no `untrimmed_start` reaches the `scorer_pending` check (line 100) and the pairing check (line 103), collecting both errors. Fail-closed, all issues reported. |
| **Qwen P2-3 (test coverage for lineup_for refusal)** | **Partially agree.** The test at `test_medley.py:160-161` verifies that `lineup_for` returns a lineup with exactly 1 trimmed clip. It does not explicitly test that `lineup_for` returns `None` (or an empty list) when *all* candidates have 2+ trimmed clips. However, `lineup_ok` is tested to refuse 2 trimmed clips (`test_medley.py:159`), and `lineup_for` uses the same inline rule (`package.py:51-52`). The pin's `trim_problems` is also tested to refuse 2 trimmed clips (`test_medley.py:164`). The defense-in-depth is sufficient. **P2, not P1.** |
| **My Cycle 1 P1-1 (lineup_ok vs. trim_problems counting)** | **Downgrade to P2.** The consensus (A1, A2) confirms that `trimmed_leading` and `untrimmed_start` are always set together by `trim_variant` and the `_package` row literal. The only producer of trimmed rows is the `_package` function, which sets both keys and `scorer_pending` atomically. Therefore, `lineup_ok`'s count of `bool(m.get("trimmed_leading"))` and `trim_problems`'s count of `"trimmed_leading" in s or "untrimmed_start" in s` are equivalent on all valid inputs. The pin's `trim_problems` is a backstop that also refuses malformed rows (one key without the other). **No divergence in practice.** |
| **My Cycle 1 P1-2 (scorer_pending on untrimmed_start without trimmed_leading)** | **Downgrade to P2.** Same reasoning as P1-1: the only producer sets both keys together. A row with `untrimmed_start` but no `trimmed_leading` is malformed and would be refused by `trim_problems` with the pairing message (line 103-104). The `scorer_pending` check (line 100) would also fire if `scorer_pending` is missing, but the pairing refusal is the primary diagnostic. **Fail-closed, correct behavior.** |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-NEW-1 — `package.py:32`: The fix for Grok's P2 is correct, but the comment is slightly misleading.**
The comment says:
```python
"scorer_pending": bool(TRIM_SCORER_PENDING)}   # ruling 49 (a): the clip scorer's verdict
                                               # on the trimmed text is pending at the render
                                               # (strict: False, which the pin refuses)
```
The phrase "strict: False, which the pin refuses" is accurate: if `TRIM_SCORER_PENDING` is `False`, the row carries `scorer_pending: False`, and `trim_problems` (line 100) refuses it because `s.get("scorer_pending") is not True`. However, the comment could be clearer: it is not that the *pin* refuses the *strict* mode, but that the *pin* refuses any trimmed clip whose `scorer_pending` is not `True`. The current wording is acceptable but could be tightened. **P2, cosmetic.**

**P2-NEW-2 — `test_medley.py:153`: The equality test imports `package_pin` but does not verify that `package_pin` does not import `package`.**
The test asserts `PK.TRIMMED_PER_LINEUP_MAX == package_pin.TRIMMED_PER_PIN_MAX`. This is correct. However, the consensus (A3) states that `package_pin` must not import `package` to avoid pulling heavy dependencies into the integrator's process. The diff does not show any import of `package` in `package_pin.py`, so this constraint is respected. But there is no test that verifies `package_pin` does not import `package`. If a future change adds such an import, the equality test would still pass, but the architectural constraint would be violated. **P2, minor.**

**P2-NEW-3 — `package_pin.py:76`: `TRIMMED_PER_PIN_MAX` is defined after `SEALED_LATER` but before `TRIM_WORDS`.**
The ordering is fine, but the comment on `TRIMMED_PER_PIN_MAX` says "package.TRIMMED_PER_LINEUP_MAX" without a period or clarification that it is a *copy* of the value, not a reference. This could be misread as an import. **P2, cosmetic.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `package.py` (TRIM_SCORER_PENDING, TRIMMED_PER_LINEUP_MAX, _package row) | P1 (P1-1, P1-2) | **P2** | The consensus confirmed that the only producer of trimmed rows sets both keys and `scorer_pending` atomically. The hard-coded `True` issue (Grok P2) is fixed in the current diff. The remaining issues are constant duplication and comment clarity. |
| `package_pin.py` (trim_problems, SEALED_LATER, to_pin) | P1 (P1-1) | **P2** | The logic is correct and fail-closed. The only issues are constant duplication and the lack of a test verifying that `package_pin` does not import `package`. |
| `test_medley.py` | P2 (P2-1, P2-3) | **P2** | The tests are sufficient. The equality test catches constant drift. The `lineup_for` test verifies the happy path; the `lineup_ok` and `trim_problems` tests verify the refusal paths. No P1 issues. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **`package.py:19` / `package_pin.py:76`: Constant duplication.** `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` are separate literals. The equality test (`test_medley.py:153`) catches drift, but a single source of truth would be cleaner. The architectural constraint (no import of `package` in `package_pin`) is valid and documented in the consensus (A3). **Recommendation:** Keep as-is, but add a comment in `package_pin.py` explicitly stating that the value is a copy of `package.TRIMMED_PER_LINEUP_MAX` and that the equality is enforced by `test_medley.py:153`.
2. **`package.py:32`: Comment clarity.** The comment "strict: False, which the pin refuses" is accurate but could be clearer. **Recommendation:** Rephrase to "if TRIM_SCORER_PENDING is False, the row carries scorer_pending: False, which trim_problems refuses (line 100)."
3. **`test_medley.py`: No test verifies that `package_pin` does not import `package`.** **Recommendation:** Add a test that inspects `package_pin.__dict__` or `sys.modules` to verify that `package` is not imported by `package_pin`. This is a minor architectural guard.
4. **`package_pin.py:76`: Comment on `TRIMMED_PER_PIN_MAX`.** The comment "package.TRIMMED_PER_LINEUP_MAX" could be misread as an import. **Recommendation:** Rephrase to "copy of package.TRIMMED_PER_LINEUP_MAX (see test_medley.py:153 for equality)."

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The fix for Grok's P2 (changing `scorer_pending: True` to `scorer_pending: bool(TRIM_SCORER_PENDING)` in `package.py:32`) is the single highest-leverage change.** It ensures that the pin's claim of "pending" is always consistent with the render's `stand_alone_check` behavior. Without this fix, a toggle of `TRIM_SCORER_PENDING` to `False` in-process would create a mismatch where the pin claims pending but the render fails closed, leading to a confusing diagnostic. The fix is minimal, correct, and verified by the updated test (`test_medley.py:124-150`).

## 7. PRODUCTION READY?

**SHIP: yes with conditions.**

**Conditions:**
1. **Integrator documentation:** The integrator must document how and when `TRIMMED_PER_*_MAX` is raised after the first trimmed clip is affirmed at validate. This is stated in the constant's comment (`package.py:19-21`) and in STATE, but it is not enforced by code. The integrator must ensure that the limit is raised only on their explicit word, as per the ruling.
2. **No import of `package` in `package_pin`:** The architectural constraint that `package_pin` must not import `package` (to avoid pulling heavy dependencies into the integrator's `check_pin_only` process) must be maintained. The current diff respects this constraint, but a future change could violate it. The P2 recommendation to add a test verifying this constraint is optional but recommended.
3. **Constant equality:** The equality of `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` is enforced by `test_medley.py:153`. This test must be kept in the suite. If the constants are ever changed, the test must be updated to reflect the new values.

**Verification:**
- `test_medley` 81 OK; every other suite OK.
- The fix for Grok's P2 is present and correct.
- The logic in `trim_problems` is fail-closed and reports all issues.
- The SEALED_LATER contract is respected: pins without a trimmed clip seal exactly as before.
- Nothing claims the scorer affirmed anything: the `scorer_pending` key is only set to `True` when `TRIM_SCORER_PENDING` is `True`, and the render's `stand_alone_check` records the trimmed labels in `scorer_pending` without affirming them.