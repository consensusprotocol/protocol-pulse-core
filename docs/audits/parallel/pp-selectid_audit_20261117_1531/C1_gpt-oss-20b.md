# gpt-oss-20b (openai/gpt-oss-20b) 91 s finish=stop usage in 7778 / out 14883 usd_reported=0.002085 usd~0.247 (upper-bound price)

**Findings**

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 1 | `canon.word_form` incorrectly accepts “it’s” ↔ “it has” | The new contraction rule matches any `t + "'s"` against `[t, "is" | "has"]`. It therefore treats “it’s” vs “it has” as a valid word‑form pair, allowing a run‑decode that says “it has” to pass a gate that should reject it. | **[P0]** |
| 2 | Potential breakage of `lock_precheck.DECODER` constant | The decoder SHA was changed from `fe809cb4e680` to `fc204e4a4385`. If any other module imports `pipeline.lock_precheck.DECODER` (outside the updated tests), it will now reference the wrong value, causing lock‑precheck failures or incorrect file naming. | **[P1]** |

**P1_OR_WORSE: 2**