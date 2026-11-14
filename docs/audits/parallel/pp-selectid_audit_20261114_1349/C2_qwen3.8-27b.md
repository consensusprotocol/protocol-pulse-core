# qwen3.8-27b (qwen/qwen3.8-27b) 98 s finish=stop usage in 33018 / out 2336 usd~0.134 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1349

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "you" persona) did not produce a visible output in the prompt, but looking at the other models:
*   **Grok-4.20** correctly identified that the `confirm_ahead` logic was sound and that the "critical" bug claimed by Qwen was a misreading of the code.
*   **Qwen3.8-27B** raised a `<critical>` finding that `confirm_ahead` would exclude *all* families because `hf` (families to exclude) was computed as `{b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}`. Qwen argued that since no backend has `vendor == "xai"` *and* `family == "xai"` (Grok's family is "grok"), the set `hf` would contain all families, thus excluding Grok.
    *   *Correction:* Qwen was **wrong**. The code computes `hf` based on `b.vendor != CONFIRM_VENDOR`. Grok's vendor *is* `CONFIRM_VENDOR` ("xai"). Therefore, Grok's family ("grok") is **not** added to `hf`. The other backends (DeepSeek, GLM, Gemini, Judge) have vendors != "xai", so their families *are* added to `hf`. Thus, `hf` = {deepseek, glm, gemini, gemma}. Grok is **not** excluded. The test `test_every_vendor_but_grok_s_is_avoided_ahead` (line 891) explicitly verifies this: `got["wf"]` is `{"deepseek", "glm", "gemini", "gemma"}`.
*   **GLM-5.3-Flash** raised M1 (mock-only coverage of refusal vs held) and M2 (mixed reasons). These are valid concerns about test coverage and edge-case data integrity, but not functional bugs in the current diff.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Qwen's Critical (confirm_ahead exclusion):** **DISAGREE.** The code is correct. `hf` excludes families of non-xAI vendors. Grok (xai) is kept. The test proves it.
*   **Grok's "SHIP yes":** **AGREE.** The logic holds. The chain order is correct. The held/refusal distinction is correct.
*   **GLM's M1 (Mock-only refusal test):** **AGREE (Medium).** The test `test_a_verdict_that_fails_the_clip_is_a_refusal_not_held` mocks `CI.a_failures`. It does not test the real path where `step_a` raises a `ValueError` that is *not* `CONTEXT_TOO_LONG` but is a genuine logic error. However, `held_why` treats *all* non-`CONTEXT_TOO_LONG` errors as HELD. If `step_a` raises a `RuntimeError` due to a bug, it will be HELD and retried forever. This is a "fail-open" for logic errors. The ruling says "unavailable leg moves on... never a refusal". A logic error is not "unavailable". This is a potential infinite retry loop for deterministic bugs.
*   **GLM's M2 (Mixed reasons):** **AGREE (Medium).** `is_held` uses `all(...)`. If a moment has both a HELD reason and a REFUSAL reason, it is classified as REFUSED (because `all` returns False). This is correct behavior (a refusal overrides a hold). However, the code paths that generate reasons currently replace the list, so mixed lists are unlikely. But if they occur, the behavior is correct (refusal wins).

## 3. NEW FINDINGS FROM THIS REVIEW

### <medium> M1 — Deterministic Logic Errors in `step_a` Cause Infinite HELD Retries
**Where:** `package.py:57-64` (`held_why`), `context_integrity.py` (unchanged, but relied upon).
**Sequence:**
1.  `context_integrity.step_a` has a bug that causes it to raise a `RuntimeError` (e.g., `KeyError` in parsing) for a specific moment's context.
2.  `prescreen` catches the exception and calls `held_why(e)`.
3.  `held_why` checks `isinstance(e, ValueError) and str(e).startswith("CONTEXT_TOO_LONG")`. This is False for `RuntimeError`.
4.  `held_why` returns `STEP_A_HELD...`.
5.  The moment is marked HELD. It is not cached.
6.  Next build, the same moment is processed. The same bug raises the same `RuntimeError`.
7.  The moment is HELD again.
8.  This repeats forever. The orchestrator sees "HELD" on STATE line 1, but the ruling says "retried next build". It does not say "escalate after N retries".
**Impact:** A deterministic bug in `step_a` will silently starve the build of that moment forever, with no escalation.
**Mitigation:** The ruling says "unavailable leg moves on". A logic error is not "unavailable". Ideally, `held_why` should distinguish between transient errors (Unavailable, DeadlineExceeded) and permanent logic errors (RuntimeError, KeyError). However, the ruling explicitly says "STEP_A_UNAVAILABLE MUST NEVER END A CLIP". It does not address logic errors. Given the ruling's intent to prevent clips from dying, treating logic errors as HELD is a safe default (fail-open), but it masks bugs.

### <medium> M2 — `confirm_ahead` Spend is Not Reconciled with `second_screen`
**Where:** `package.py:165-176` (`confirm_ahead`), `package.py:177-198` (`second_screen`).
**Sequence:**
1.  `step_a_plan` decides to run in parallel.
2.  `confirm_ahead` asks Grok for a second verdict for all new moments.
3.  `prescreen` (first screen) runs in parallel.
4.  `second_screen` runs. It asks for a second verdict *off the first verdict's vendor/family*.
5.  If the first verdict was from Grok, `second_screen` excludes Grok. It asks DeepSeek, GLM, etc.
6.  The verdict from `confirm_ahead` (Grok) is **not used** by `second_screen` because `second_screen` excludes Grok.
7.  The spend from `confirm_ahead` is wasted.
**Impact:** Extra cost. The ruling 101 says "Grok's confirm beside the Heimdall filter". The intent is to have Grok's verdict ready. But if the first verdict is Grok's, the second verdict must be off Grok. So Grok's confirm is useless.
**Mitigation:** The code already handles this: `confirm_ahead` is only run if `plan["parallel"]` is True. `plan["parallel"]` is True only if the first screen's leading leg is Heimdall (not Grok). If the first screen's leading leg is Grok, `plan["parallel"]` is False, and `confirm_ahead` is not run. So this is not a bug. The spend is only wasted if the first screen's leading leg is Heimdall, but the *actual* first verdict for a specific moment comes from Grok (because Heimdall failed). In that case, `confirm_ahead` asked Grok, but `second_screen` excludes Grok. The spend is wasted.
**Severity:** Medium (cost only, no functional impact).

### <low> L1 — `last_resort_note` is Not Included in `spotlight.py` Pin Seal
**Where:** `spotlight.py:342-349`.
**Sequence:**
1.  `spotlight.inventory` adds `last_resort` to the `step_a_two_families` row.
2.  `package_pin.seal` hashes the gates dict.
3.  If the `last_resort` key is added, the seal changes.
4.  Existing pins do not have this key.
5.  New pins have this key.
6.  This is expected. The ruling says "recorded as such on the pin".
**Impact:** None. This is the intended behavior.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Chain Order | Pass | Pass | Verified against ruling 102. |
| Held/Refusal | Pass | Pass | `held_why` correctly distinguishes `CONTEXT_TOO_LONG` (refusal) from others (held). |
| Confirm Ahead | Pass | Pass | Qwen's critical was a misreading. Code is correct. |
| Local Judge | Pass | Pass | Recorded on pin and STATE line 1. |
| $19 Stop | Pass | Pass | `start_refused` checks `spent0 >= 19.0`. |
| Test Coverage | Medium | Medium | Mock-only refusal test (M1). |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    1.  **M1:** `held_why` treats deterministic logic errors as HELD, causing infinite retries. Consider adding a counter or escalation for repeated HELD moments. (File: `package.py:57-64`)
    2.  **M2:** `confirm_ahead` spend may be wasted if the first verdict is Grok's (despite Heimdall leading the plan). (File: `package.py:165-176`)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a retry counter for HELD moments to prevent infinite retries of deterministic logic errors.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Monitor for repeated HELD moments on STATE line 1. If a moment is HELD more than 3 times, escalate to the orchestrator.
2.  Verify that the `confirm_ahead` spend is within budget. If the parallel plan is used frequently, the wasted spend on Grok's confirm (when the first verdict is Grok's) should be monitored.