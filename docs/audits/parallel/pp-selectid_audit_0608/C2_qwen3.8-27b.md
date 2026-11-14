# qwen3.8-27b (qwen/qwen3.8-27b) 76 s finish=stop usage in 26617 / out 2292 usd~0.114 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0608

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the "stale verdict" risk (Qwen's `<high>`) and the backward compatibility of old pins (Grok's `<medium>`). I missed the specific interaction between the **Ruling 91 `break`** and the **Ruling 65 `lone_slot` rewrite** logic, which GLM-5.3-Flash and Grok-4.20 identified as the `(f)` edge. I also underestimated the severity of the `take_failed` counter interaction, which Grok flagged as `<high>`.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok-4.20 `<high>` (take_failed counter):** **AGREE.** This is a real behavioral regression. If a medley has short clips (requiring a clip addition for Ruling 3) and the takeaway fails the Value verdict twice, the line-up ends with `rec["why"] = "ruling 91..."` and **no package**. Under the old code, if the takeaway failed cheap gates twice, Ruling 3 would trigger, add a clip, and ship a no-voice package. Now, Value losses do not increment `take_failed`, so Ruling 3 is never triggered for Value-only failures. The orchestrator's "By design" note in the consensus claims this is intended ("Ruling 91... ONLY IF its clips meet the seconds"), but the code path for "clips do NOT meet seconds" (i.e., short clips) results in a hard stop rather than a fallback. This is a significant reduction in output volume for short-clip medleys with weak takeaways.
*   **GLM-5.3-Flash `<medium>` (Replay guarantee):** **DISAGREE (Partially).** GLM worried that `replayed=True` might pass the gate. However, `package_pin.py:429` (`takeaway_problems`) checks `row["text"] != t`. More importantly, `required_gates` includes `takeaway_value`, and `gate_problems` (not shown in diff but implied by `to_pin` logic) checks status. The test at `test_medley.py:767` explicitly asserts that `{"text": t, "replayed": True}` raises `PinRefused`. The `inventory` function at `package.py:359` passes `value.get("replayed")` to the row. If the router replays, `replayed` is True. The pin side *does* catch it. The build side seals it, but the pin side refuses it. This is fail-closed. Not a bug.
*   **Qwen3.8-27B `<high>` (Stale verdict):** **DISAGREE.** Qwen worried that a Ruling 65 rewrite (caption/title only) would leave a stale `val` for the takeaway. However, `lone_slot` (package.py:87) only returns "caption" or "title". The takeaway text is *not* changed by a Ruling 65 rewrite. The `val` variable holds the verdict for the *current* takeaway text. Since the takeaway text didn't change, the verdict is still valid. If the takeaway *is* changed (via a full rewrite or Ruling 91 rewrite), a new `val` is computed. The code is correct here.
*   **Grok-4.20 `<medium>` (Old pins):** **DISAGREE.** The consensus correctly refuted this. `seal()` is unchanged. `to_pin` is only called on new packages. Old pins are re-sealed via `seal()` directly in `reseal_attested.py`, which does not call `required_gates` or `takeaway_problems`. No backward compatibility break.

## 3. NEW FINDINGS FROM THIS REVIEW

### <high> Ruling 91 Value Loss on Short Clips Prevents Ruling 3 Fallback
**File:** `pipeline/package.py` (lines 277-284, 323-330)
**Scenario:**
1.  Medley with short clips (e.g., 39s, needs a 4th clip to reach 60s).
2.  Takeaway 1 fails Value verdict (`val["ok"] = False`).
3.  `no_voice_fits` is False (clips too short).
4.  `v_redo = True`. Loop continues.
5.  Takeaway 2 (rewrite) fails Value verdict.
6.  `len(v_lost) > 1` is True.
7.  `break` at line 284.
8.  After loop: `v_novoice` is None (because `no_voice_fits` was False in step 3). `take_failed` is 0 (Value losses don't count).
9.  Condition at line 323: `(v_novoice is not None or take_failed >= NO_VOICE_AFTER)` is False.
10. No `no_voice` call. No package. `rec["why"]` is set to "ruling 91...".
**Impact:** A medley that *could* have shipped as a no-voice package (by adding a clip, per Ruling 3) is now dropped entirely because the takeaway failed Value twice. Ruling 3's "add a clip" mechanism is bypassed for Value failures. This is a significant behavioral change that reduces output.

### <medium> Ruling 91 `break` Skips Ruling 65 `lone_slot` Rewrite
**File:** `pipeline/package.py` (lines 277-279)
**Scenario:**
1.  Medley with FITS clips (e.g., 48s, no clip needed).
2.  Takeaway 1 fails Value verdict.
3.  `no_voice_fits` is True.
4.  `v_novoice = val`. `break` at line 279.
5.  `no_voice` is called with `value=val`.
6.  Inside `no_voice`, the title/caption from `last_fields` are re-gated.
7.  If the caption has a lone VO-fidelity failure (e.g., "Ultimately" opener), `no_voice` fails closed (`note["why_not"] = "the title / caption fail VO fidelity..."`).
8.  No package.
**Impact:** Under the old code, if the takeaway failed cheap gates, the loop would continue, potentially triggering a Ruling 65 `lone_slot` rewrite for the caption, which might have fixed the caption and allowed a no-voice package. Now, the Value loss `break`s immediately, skipping the Ruling 65 rewrite opportunity. This is the `(f)` edge. It is fail-closed, but it may prevent valid no-voice packages.

### <low> `takeaway_value` Prompt Injection Surface
**File:** `pipeline/package.py` (lines 59-62)
**Scenario:**
Clip text or takeaway line contains prompt injection.
**Mitigation:** `quote_data(t, n).replace('"', "'")` neutralizes double quotes. `UNTRUSTED` marker is injected. `spotlight.parse_value` strictly validates JSON. Fail-closed on exception.
**Assessment:** Acceptable. The risk is low due to strict parsing and neutralization.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Value Verdict Logic** | 8/10 | 9/10 | Confirmed fail-closed. Replay handled by pin side. |
| **Loop Control** | 7/10 | 6/10 | Identified `<high>` regression: Value losses bypass Ruling 3 fallback for short clips. |
| **Pin Compatibility** | 8/10 | 9/10 | Confirmed no backward compat break. |
| **Edge Cases** | 7/10 | 6/10 | Identified `<medium>` regression: Ruling 91 `break` skips Ruling 65 rewrite. |

## 5. FINAL PRIORITY LIST

*   **P1 HIGH:** `pipeline/package.py:277-284` — Decide if Value losses on short clips should trigger Ruling 3 (add clip) or hard stop. Current code hard stops, which is a regression in output volume. If hard stop is intended, document it clearly. If not, increment `take_failed` on Value loss *only if* `no_voice_fits` is False, or allow Ruling 3 to trigger after two Value losses.
*   **P2 MEDIUM:** `pipeline/package.py:277-279` — The `break` on `no_voice_fits` skips Ruling 65 `lone_slot` rewrites. Consider allowing the loop to continue to the paid gates (where Ruling 65 might fix a caption) before falling back to no-voice, or ensure `no_voice` can trigger a Ruling 65 rewrite internally.
*   **P2 MEDIUM:** `pipeline/package.py:261` — Ensure `takeaway_value` is not called if the takeaway text is empty or None (defensive check, though `write_line` should prevent this).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Clarify the interaction between Ruling 91 Value losses and Ruling 3's "add a clip" fallback for short clips.** The current code drops packages that Ruling 3 would have saved, which is a significant behavioral regression.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Orchestrator Confirmation:** Confirm that dropping packages on two Value losses for short clips (where Ruling 3 would have added a clip) is the intended behavior. If not, fix the `take_failed` counter or the `break` logic.
2.  **Acceptance of `(f)` Edge:** Accept that a Value loss on FITS clips with a lone caption failure will result in no package (no Ruling 65 rewrite). This is fail-closed but may reduce output.
3.  **No Backward Compat Break:** Confirmed. Old pins are safe.