# gpt-oss-20b (openai/gpt-oss-20b) 53 s finish=stop usage in 9715 / out 8443 usd_reported=0.001347 usd~0.156 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | Global `_FLOOR` can leak between concurrent builds | **P1** | `_FLOOR` is a module‑level variable that is set to `LY_FLOOR_S` before the soft pass and cleared in a `finally` block. If two `build()` invocations run concurrently, the second may see the `_FLOOR` value set by the first, causing the soft‑pass logic (e.g., `ly_lo`, `runtime_short`, `takeaway_budget`) to behave incorrectly for the first build or to leak into the clean pass. This race condition can lead to false positives/negatives in the runtime gate and other floor‑dependent checks. |
| 2 | None | **P0** | No other defects that would cause a gate to incorrectly pass or fail were identified. All logic paths in the new code satisfy the specified rules and tests. |

**P1_OR_WORSE:** 1