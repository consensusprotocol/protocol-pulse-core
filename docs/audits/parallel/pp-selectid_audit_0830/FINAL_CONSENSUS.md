# pp-selectid audit 0830 (RULING 54): final consensus after cycle 2

**Cycle 2:** no P0 or P1 from grok, qwen or glm. qwen's "P1 HIGH" list is three verifications, each "no change
needed". All three agree that:
- F1 (at least half from the angle, checked inside the search) and F2 (the SWAP_TOP cap) are right;
- every line-up rule still applies: lineup_for's only change is a default-None parameter;
- the placement limits match the search's own conditions verbatim.

## The conditions

| # | condition | disposition |
|---|---|---|
| C1 | qwen P2-1: a test that the cap keeps only the best SWAP_TOP candidates | Added: a clip ranked 11th is never considered; ranked into the top 10, it completes the angle. |
| C2 | qwen P2-2: say that "first line-up only" is the caller's rule | Added to pool_fill's docstring. |
| C3 | grok (b): "under 8 s" must not drift from SHORT_CLIP_S | It cannot: placement() writes f"under {SHORT_CLIP_S:.0f} s". |
| C4 | grok (c): readers of the new "pool_filled" key | It is a record key on the tried line-up. Nothing requires it, and older records simply lack it. |
| C5 | glm N6: the comprehension that builds `rest` runs before the cap | Bounded by the cleared pool, which is ~5-13 moments after both step-A screens. Negligible. |

## Verification

- test_medley 90 OK; every other suite OK; regression_test.sh is run on the worktree before the commit.
