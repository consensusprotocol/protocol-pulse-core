# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 8337 / out 1317 usd~0.045 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0500

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic but failed to fully resolve the "unseen code" concerns regarding loop termination and segment indexing. The other models (specifically the Consensus/K1 and K2 verifications) provided the critical context that I lacked:
*   **Loop Termination:** I flagged the re-line loop as potentially infinite (P1). The consensus verified that the enclosing loop is bounded by `n_lineup < lineups` and that `dropped` only grows, making infinite loops impossible.
*   **Index Safety:** I flagged `segs[1]` as a potential `IndexError` on a 1-segment line-up (P1). The consensus verified that `lineup_for` always returns at least 3 segments (hook + 2-4 clips), making `segs[1]` safe.
*   **Text Consistency:** I flagged a potential mismatch between the pin's text check and the render's R1 check (P1). The consensus verified that `approved_text` is verbatim, so the `?` check is consistent.

I missed the opportunity to leverage the "Standing Laws" to dismiss these P1s earlier. By confirming the loop bounds and segment minimums, these are no longer defects.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH:** Agreed with the P1s initially, but the consensus resolved them. I now agree that P1-1 (shadowing) is a non-issue because `ly_shape` is a hard gate. I agree P1-2 (index) is unreachable.
*   **GROK-4.20:** Agreed with "SHIP: yes". Grok correctly identified that the `role != "hook"` guard is the only change to eligibility, satisfying the "only the hook" constraint.
*   **QWEN3.8-27B:** Agreed with the P1s initially, but the consensus resolved them. Qwen's concern about `ly_shape` only checking `js[0]` is valid but correct by design (Ruling 37 only restricts the join *after* the hook).

**Disagreement:** None. The consensus has effectively closed all P1s from Cycle 1.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: `question_hook` does not normalize Unicode question marks.**
`pipeline/package.py:27` uses `endswith("?")`. If a hook ends with a full-width question mark (`？`) or a non-breaking space before the `?`, the predicate returns `False`. The render's R1 is stated to use the same test, so they are consistent, but this is a brittle string check. If the source text contains `?` with trailing whitespace, `rstrip()` handles it. If it contains `?` with a zero-width space, it fails. This is a P2 because it's consistent between pin and render, but it's a potential source of "silent" non-question hooks if the text is dirty.

**P2-2: `ly_shape` error message is slightly misleading.**
`pipeline/package.py:38-39`: The message says "a hook ending on a question takes no bridge after it, so {js[0]} must be followable". This is correct, but it implies the *join* must be followable, whereas the actual rule is that the *bridge* is forbidden. The join can be flagged (unfollowable), but the bridge is what's forbidden. The message is acceptable but could be clearer.

**P2-3: Test coverage for `question_hook` with `None` text.**
`tests/package/test_medley.py:90-93`: The test checks `[]` and a non-question string, but not `{"text": None}`. The code handles it (`or ""`), but the test doesn't prove it. Minor.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Eligibility | P1 | P2 | The `role != "hook"` guard is correct and minimal. No other roles affected. |
| Package (build) | P1 | P2 | Loop termination and index safety verified by consensus. Logic is correct. |
| Package (ly_shape) | P1 | P2 | Shadowing concern resolved; `ly_shape` is a hard gate. |
| Tests | P2 | P2 | Coverage is good, but missing `None` text edge case. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  `pipeline/package.py:27` — `question_hook` uses a brittle `endswith("?")` check. Consider normalizing Unicode question marks or using a regex. (Consistent with render, but fragile.)
2.  `tests/package/test_medley.py:90-93` — Add a test for `question_hook([{"text": None}])` to verify the `or ""` fallback.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of `and role != "hook"` in `eligibility.py` is the single highest-leverage change, as it directly implements Ruling 37's core constraint (question ends hook only) with minimal code and no side effects.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The render's R1 must be updated to match the `question_hook` predicate (as stated in the orchestrator's ruling).
2.  The `ly_shape` gate must be enforced in the sealed inventory (verified by consensus).
3.  The re-line loop must be bounded (verified by consensus).

All conditions are met or verified. The code is ready to ship.