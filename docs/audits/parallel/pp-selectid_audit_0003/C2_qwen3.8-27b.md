# qwen3.8-27b (qwen/qwen3.8-27b) 60 s finish=stop usage in 19911 / out 1830 usd~0.087 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: pp-selectid-0003 (RULING 93)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the `burned_in` truncation fail-open (the ticker listed 13th) and the `text: null` contract issue. However, I missed the **precedence logic error in `spotlight.py`** that GLM-5.3-Flash identified (and then partially retracted).

GLM noted that in `spotlight.py:118-120` (now lines 120-122 in the fixed diff), the `stop()` message construction uses a ternary/`or` chain:
```python
stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
                                  VP.layout_block(v) or
                                  f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
```
If a record is **measured**, has a **ruling-70 flag** (e.g., `on_screen_text` asserting beyond words), AND has a **ticker** (ruling-93 block), `VP.layout_block(v)` returns a truthy string. The `or` short-circuits, so the user sees the Ruling 93 reason, not the Ruling 70 flag details. While the clip is correctly *blocked* (fail-closed), the *diagnostic message* is misleading. It hides the Ruling 70 violation. This is a **Medium** severity diagnostic defect, not a correctness break, but it violates the "every blocking reason, named" spirit of the audit.

I also missed the **redundant local import** in `spotlight.py:91` (`import visual_pin as VP` inside `clean_visual`), which Grok-4.20 flagged. While harmless, it deviates from the module's existing pattern (where `VP` is likely bound at module level or imported once).

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-Flash (Truncation Fail-Open):** **Agree.** This was the most critical finding. The fix in `visual_pin.py:209` (`sorted(items, key=lambda x: burned_block(x) is None)`) correctly ensures blocking items (tickers/crawls) are sorted to the front before the `TEXTS_MAX` cut. The test `test_ruling_93_burned_in_text_per_clip` (line 499-502) verifies this.
*   **GLM-5.3-Flash (Spotlight Precedence):** **Agree.** The `or` chain in `spotlight.py:121` suppresses the Ruling 70 flag message when a Ruling 93 block is present.
*   **Grok-4.20 (No Critical/High Findings):** **Disagree.** Grok missed the truncation fail-open entirely. It is a **High** severity issue because it allows a ticker to pass eligibility if it is listed after 12 other items. The fix addresses it, but Grok's "SHIP: yes" in Cycle 1 was premature.
*   **Qwen3.8-27B (Pre-Ruling-93 Records Blocked):** **Disagree.** Qwen argued that `layout_block` would block old `visual-1` records, breaking existing pins. This is **incorrect**. `visual_pin.key()` includes `VERSION`. Since `VERSION` is bumped to `visual-2`, the cache key changes, forcing a re-measure. Old records are never served to `layout_block` in a new build. Sealed pins are read via `sealed()`, which only copies `burned_in` if present, so old pins remain byte-identical. Qwen's "Critical" findings are refuted by the cache invalidation mechanism.
*   **Qwen3.8-27B (Eligibility Doesn't Read Visual Verdict):** **Disagree.** The Ruling explicitly states eligibility drops the *channel-name* hold. The *per-clip* visual verdict is read at the pin stage (`package.py`, `spotlight.py`). Eligibility runs before frames are fetched. This is by design.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> `spotlight.py:121` — Diagnostic Message Precedence**
As noted above, the `or` chain in the `stop()` message hides Ruling 70 flags when a Ruling 93 block is present.
*   **Scenario:** A clip has a ticker (Ruling 93 block) and an `on_screen_text` flag asserting beyond words (Ruling 70).
*   **Current Behavior:** `stop()` prints "ruling 93: a ticker...". The Ruling 70 flag is invisible in the log.
*   **Impact:** Orchestrator cannot see the Ruling 70 violation, potentially leading to incorrect re-measure decisions or missed context.
*   **Fix:** Change the `or` to a list join, similar to `package.py:48`.

**<low> `visual_pin.py:258` — 300-char Truncation of `layout_block` Reason**
`layout_block` returns `("ruling 93: " + "; ".join(why))[:300]`. If there are many blocking items (e.g., 5 tickers), the reason string is cut mid-sentence. This is cosmetic but can make debugging difficult. The `package.py:48` join does not truncate, so the full reason is available in the hook pool, but the `spotlight.py` and `eligibility` paths might see the truncated version.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **visual_pin.py** | 8/10 | 9/10 | Truncation fail-open fixed. Sorting logic is correct. |
| **package.py** | 9/10 | 9/10 | Hook block now includes both reasons. Line-up drop logic is correct. |
| **spotlight.py** | 7/10 | 8/10 | `clean_visual` is correct. Diagnostic message precedence is a minor flaw. |
| **eligibility.py** | 9/10 | 9/10 | Channel hold correctly removed. |
| **Tests** | 8/10 | 9/10 | New tests cover the truncation and ticker cases. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None. The truncation fail-open is fixed.
*   **P1 HIGH:** None.
*   **P2 MEDIUM:**
    1.  `spotlight.py:121`: Fix the `or` chain in the `stop()` message to report *all* blocking reasons (Ruling 70 flags AND Ruling 93 blocks), not just the first truthy one.
    2.  `spotlight.py:91`: Remove the redundant local `import visual_pin as VP` if `VP` is already bound at module level (verify with `grep`).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The **sorting of `burned_in` items before truncation** in `visual_pin.py:209` is the most critical change. Without it, a ticker listed 13th would silently pass eligibility, violating Ruling 93's "fail-closed" law. This single line prevents a catastrophic fail-open.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the diagnostic message precedence in `spotlight.py:121` to ensure Ruling 70 flags are not hidden when a Ruling 93 block is present.
2.  Verify that `VP` is not redundantly imported in `spotlight.py:91`.

The core logic is sound, the fail-open is closed, and the tests are comprehensive. The remaining issues are diagnostic and stylistic.