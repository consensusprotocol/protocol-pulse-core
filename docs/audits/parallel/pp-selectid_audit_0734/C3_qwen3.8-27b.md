# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 22108 / out 1355 usd~0.087 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0734

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the structural correctness of `nv_order` and the removal of `no_voice_fits`. The other models correctly identified the **state mutation risk** in `nv_order` (Attack d) and the **parameter passing nuance** in `fixed_caption_gates` (Attack b/c).

However, the most significant "miss" in a general audit is often the **interaction between the new `fixed_caption_gates` logic and the `lone_slot` guard**. While GLM flagged the `lone_slot` logic as "correct," it did not explicitly verify the **short-circuit evaluation order** in the new `no_voice` block (lines 239-244). Specifically, the condition `if cheap or not fid["ok"] or not cx["ok"]:` is evaluated *before* the `lone_slot` check. If `cheap` is non-empty but `cx` is also failing, the code enters the block, then checks `lone_slot(cheap + fid["violations"])`. If `cx` is failing, `lone_slot` might return `None` (if violations are mixed) or "caption" (if only caption violations exist in `cheap`/`fid`). The code correctly requires `cx["ok"]` to be True to proceed to the fixed caption path. This is subtle but correct.

What I missed: **The specific scenario where `cheap` is empty, `fid` is failing on caption, but `cx` is failing on a *different* segment.** In this case, `lone_slot(cheap + fid["violations"])` would return "caption" (since `cheap` is empty and `fid` only has caption violations). However, the guard `cx["ok"]` is False, so the code correctly rejects the fixed caption path. This is safe.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-Flash (d) `nv_order` state divergence:** **Agree.** The in-loop call to `nv_order` (line 274) and the post-loop call inside `no_voice` (line 176) use the same `dropped`, `doomed`, and `cleared` state *at the moment of the call*. Since `nv_order` is a pure function of its arguments and the closure variables (which are not mutated between the `break` and the `no_voice` call), the results are identical. The "risk" is theoretical if code were inserted between them, but the current diff shows a direct `break` followed by the loop exit and `no_voice` call. **Verdict: Not a bug, but a latent fragility.**
*   **Grok-4.20 (b) `fixed_caption_gates` extraction:** **Agree.** The extraction is behavior-preserving. `rewrite_alone` previously built `pk3` and ran gates; now it calls `fixed_caption_gates`. The inputs (`segs`, `by_id`, `ctx`, etc.) are the same. The `a_use(pk3)` vs `{sg["label"]: a_by[sg["moment_id"]]...}` change is equivalent because `a_use` is defined as that comprehension in the codebase (verified in Cycle 1 consensus).
*   **Qwen3.8-27B (d) `nv_order` determinism:** **Agree.** Qwen's initial "critical" was self-refuted. `nv_order` is deterministic. The key insight is that `nv_order` does *not* mutate state; it only reads. Therefore, the in-loop decision and the post-loop execution are consistent.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> (c) `fixed_caption_gates` re-runs `cheap_checks` on `pk3`, but `pk3` is built from `segs` which may include the *added* clip.**
In `no_voice`, if `added` is not None, `order` includes the new clip. `fixed_caption_gates` is called with `order` (line 247). Inside `fixed_caption_gates`, `pk3` is assembled from `segs` (which is `order`). The `cheap_checks` run on this new package. This is correct: the fixed caption must pass gates on the *final* line-up. However, note that `cheap_checks` includes `RUNTIME` and `R4`. If the added clip causes the total duration to exceed `RUNTIME_S[1]`, `cheap_checks` will fail. This is correct behavior: the fixed caption cannot save a line-up that is too long.

**<medium> (e) The removed test `test_a_value_loss_never_counts_toward_ruling_3s_two_failures` is correctly removed.**
Under Ruling (A), the "count" of failures is irrelevant because the *shape* is the same. Whether the takeaway was removed by two failed writes (Ruling 3) or one value loss (Ruling 91), the result is the same no-voice shape. The test asserted a specific count of `value_calls`, which is no longer a meaningful invariant. The new tests (`test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip`, etc.) correctly assert the *outcome* (package with added clip, no rewrite).

**<high> (c) Potential issue: `lone_slot` is called with `cheap + fid["violations"]`, but `cx["violations"]` is NOT included.**
Line 240: `lone_slot(cheap + fid["violations"]) == "caption"`.
If `cx` is failing (e.g., context integrity violation on the *title*), `cx["ok"]` is False, so the guard `cx["ok"]` prevents entry.
If `cx` is passing, `cx["violations"]` is empty.
So, `lone_slot` only sees `cheap` and `fid` violations. This is correct: Ruling 65 (b) applies when the *caption* fails its *own* gates (cheap/f