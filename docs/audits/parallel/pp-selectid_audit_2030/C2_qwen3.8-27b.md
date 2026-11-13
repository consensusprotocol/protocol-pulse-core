# qwen3.8-27b (qwen/qwen3.8-27b) 102 s finish=stop usage in 50121 / out 2335 usd~0.185 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
# Feature: pp-selectid-2030

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the arithmetic of `takeaway_budget` and the structural integrity of `ly_shape`. I missed two critical operational and logical flaws that the other models (specifically Grok and GLM) identified or hinted at:

1.  **The "Null Bridge" Re-line Trap (Grok P2-1):** I assumed that if the writer returned `null` for a bridge, it was a valid "no bridge needed" state. Grok correctly identified that in `build()`, if the clips-alone verdict *flagged* a join, but the writer returns `null` (judging it followable), the code drops the clip and re-lines. This is a **logical contradiction** with L-y 2, which states the bridge is an exception *only* when the packager judges it necessary. If the blind verdict says "unfollowable" but the writer says "followable," the code currently treats the *writer* as the authority to drop the line-up, rather than trusting the blind verdict or forcing the bridge. This wastes a line-up attempt and potentially kills a valid angle.
2.  **The `bridge_slots` Mismatch for Hook Joins (Grok P2-2):** I verified that `ly_shape` handles the `intro` slot correctly, but I failed to trace `package_pin.py`'s `line_problems` and `bridge_slots` for the case where the bridge is at `k=0` (after the hook). Grok correctly noted that `bridge_slots` returns `["takeaway"]` for a medley with an intro bridge, but `line_problems` checks `by.get(s) != t` for `s` in `slots`. If the `intro` slot is populated, `bridge_slots` does *not* include "intro" in its return list for the medley shape (it only maps `bridges_after_clip`). This means the `intro` text is never checked against the `vo.intro` in `line_problems` for a medley, potentially allowing a mismatch between the pinned `vo.intro` and the `lines` array.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (P0-1/P0-3):** I **agree** with GLM's assessment that the `takeaway_budget` fallback is a P1, not a P0. The loop is bounded by `WRITES`, so it terminates. However, I **disagree** with GLM's claim that the retry "cannot succeed." If the bridge was written at 20 words (exceeding the 12-word assumption in `medley_content_range`), the `RUNTIME` gate fails. The `_redo` prompt now includes the *actual* bridge text in the budget calculation (via `other=written` in `write_takeaway` on retry). If the writer shortens the bridge or the takeaway, it *can* succeed. It is a waste of spend, but not a hard failure.
*   **GROK-4.20 (P2-1, P2-2, P2-3):** I **agree** with all three.
    *   P2-1 (Null Bridge): This is a significant logic bug. The blind verdict is the "source of truth" for L-y 3. If it flags a join, the line-up is *conditionally* valid. The writer's judgment should not override the blind verdict's structural requirement to drop the line-up; it should either force the bridge or flag a conflict. Currently, it silently drops the clip.
    *   P2-2 (Bridge Slots): This is a real pinning bug. The `intro` slot is not validated in `line_problems` for medleys.
    *   P2-3 (Inventory): I **disagree** with Grok here. The consensus in Cycle 1 (K3) correctly refuted this. `ly_shape` is a code check, not a model verdict. It does not have a "measured" state in the same way. If the medley verdict is `NOT RUN`, `build()` never assembles the package, so `ly_shape` is never called on a live package. The inventory rows are consistent.
*   **QWEN3.8-27B (P0-2):** I **agree** with the refutation of Qwen's P0-2. The math `ceil(29.25 - 1e-9)` is indeed 30. The test `test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps` proves this.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `write_takeaway` Budget Mismatch on First Write with Bridge**
In `build()`, when a join is flagged, `write_takeaway` is called with `other=()` (empty) on the *first* attempt. Inside `write_takeaway`, if `join is not None and not other`, it sets `other = [" ".join(["word"] * LY_BRIDGE_WORDS)]` (12 words). This assumes the bridge will be 12 words. However, the writer is asked to write a bridge "as short as it can be" (up to 20 words). If the writer writes a 20-word bridge, the `takeaway_budget` calculated for the *takeaway* was based on a 12-word bridge. The resulting package will have a runtime estimate that is `(20-12)/2.5 = 3.2s` higher than the budget intended. This will likely fail the `RUNTIME` gate. The `_redo` prompt will then ask to shorten the takeaway or bridge. This is a **predictable failure** on the first write for any flagged join where the writer uses more than 12 words for the bridge. It is not a crash, but it is a guaranteed waste of the first write attempt for every flagged join.

**P2-NEW-1: `ly_shape` Does Not Validate `bridge.cites`**
`ly_shape` checks that `bridge.why` exists and that the bridge is at the flagged join. It does *not* check that `bridge.cites` references the clips involved in the join. A bridge could cite an unrelated clip and still pass `ly_shape`. This is a minor fidelity issue, as the `vo_fidelity` gate might catch it, but `ly_shape` is the specific L-y gate.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `package.py` (Logic) | 8/10 | 7/10 | Null bridge re-line logic is flawed (P2-1). Budget mismatch on first write (P1-NEW-1). |
| `package.py` (Arithmetic) | 9/10 | 9/10 | Arithmetic is sound, but the interaction with the bridge length is fragile. |
| `package_pin.py` | 8/10 | 7/10 | `bridge_slots` misses `intro` validation for medleys (P2-2). |
| `providers.py` | 9/10 | 9/10 | Ledger changes are safe and well-tested. |
| `tests` | 9/10 | 8/10 | Tests cover the happy path and most must-fails, but miss the `intro` slot pinning mismatch and the null-bridge re-line behavior. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None. The code does not crash, leak secrets, or allow unmeasured passes.

**P1 HIGH**
1.  **`package.py:743-748` (Null Bridge Re-line):** When the writer returns `null` for a flagged join, the code drops the clip and re-lines. This contradicts L-y 2's intent that the blind verdict drives the structure. If the blind verdict says "unfollowable," the line-up is *structurally* valid only with a bridge. The writer's disagreement should not silently drop the line-up; it should either force the bridge (if the writer is wrong) or flag a conflict. Currently, it wastes a line-up.
2.  **`package.py:473-475` (First Write Budget Mismatch):** The first write for a flagged join assumes a 12-word bridge. If the writer writes a longer bridge, the runtime gate fails. The budget should be calculated *after* the bridge is written, or the prompt should strictly enforce the 12-word limit (which it does not; it says "as short as it can be").

**P2 MEDIUM**
1.  **`package_pin.py:897-905` (Bridge Slots):** `bridge_slots` does not include `intro` for medleys. `line_problems` does not validate the `intro` slot text against `vo.intro` for medleys. This allows a mismatch between the pinned `vo.intro` and the `lines` array.
2.  **`package.py:529-564` (ly_shape Cites):** `ly_shape` does not validate that `bridge.cites` references the clips in the flagged join.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `bridge_slots` function in `package_pin.py` to include the `intro` slot for medleys, and update `line_problems` to validate it.** This ensures that the pinned package's `vo.intro` (which holds the bridge for hook joins) is actually checked against the `lines` array, preventing a silent mismatch that would violate L-j (exact bytes).

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix `bridge_slots` in `package_pin.py` to return `["intro", "takeaway"]` (or similar) for medleys with an intro bridge, and ensure `line_problems` validates the `intro` slot.
2.  Address the null-bridge re-line logic in `build()`. If the writer declines a bridge for a flagged join, the code should not silently drop the clip. It should either force the bridge (if the blind verdict is authoritative) or log a conflict and fail the line-up explicitly.
3.  Add a test for the `intro` slot pinning mismatch.
4.  Add a test for the null-bridge re-line behavior to document the current (flawed) behavior or the fixed behavior.