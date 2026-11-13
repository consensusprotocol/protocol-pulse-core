# pp-selectid audit 1541 (RULING 70: the pin-stage visual check): FINAL consensus (cycle 2)

- **Cycle 2:**
  - grok: "Yes with conditions", P2s only.
  - qwen: "Yes with conditions", one P1 (video_id in the cache key).
  - glm: "Yes ... Ship it".
- No P0 in either cycle. C1 (the cache key and the sheet-sha check) and C2 (the accounting) are endorsed by all three.

## Applied (cycle-2 consensus)

| # | finding | the change |
|---|---|---|
| C3 | A failure's why should show what failed (grok P2 "narrow the excepts", qwen P2-1, glm P2-1 / P2-2) | The catch stays broad: fail closed, never a crash, as the ruling says. Each try's reason is now kept and names its kind: "seed 7: out of contract: ValueError: ...; then seed 8: no back-end answered: ProviderError: ...". Test: both tries' reasons are in why. |
| C4 | on_screen_text is unbounded, so a verbose reply bloats the sealed pin (grok P2, glm P2-3) | check() keeps at most TEXTS_MAX = 12 entries, the asserting ones first, each string <= 200 characters, and records on_screen_text_truncated. Test: 20 entries give 12, with the asserting one kept first. |
| C5 | A blocked hook's reason is static, so the hook pool does not show what the sheet showed (glm, its highest-leverage change; grok's related "log why") | hook_block() appends the finding's text and any on-screen name. Test: the finding's text is in the block reason. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P1-1: add video_id to the cache key | A moment id names one span of one video, and a hit is used only on the judged sheet's sha256 (C1). qwen calls it hardening. |
| G2 | glm: sealed() could seal an unmeasured record | Only measured records reach assemble_medley: unmeasured clips are re-lined before any write, and the no-voice fallback checks its line-up. The required "visual" row is PASS only when every clip is measured, so the pin refuses otherwise. |
| G3 | glm: an integration test of see()'s 4 workers with the real visual_for | Distinct moments per call (C1 R3); the cache file is written under CACHE_LOCK. |
| G4 | glm P2-6: the row's "by" reads "None" when no clip is measured | That row is FAIL then, and the pin refuses. |

## Verification

- All 14 suites OK on dev26 (base 096a86ed); test_visual_pin 10, test_medley 138. They are re-run in the worktree with
  regression_test.sh before commit.
