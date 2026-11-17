# gpt-oss-20b (openai/gpt-oss-20b) 101 s finish=stop usage in 10469 / out 15857 usd_reported=0.002289 usd~0.269 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | **P0** | **Hook flag never set** | `hook_own()` uses `m.get("hook_bar_soft")` to decide whether to flag a hook. In `_build()` the `hook_bar_soft` flag is added **after** `hook_ratings()` runs, so when `hook_own()` is called the flag is still missing. Consequently `hook_own()` always returns `flag=None`, causing the medley row to never be flagged and the tests that expect a flag to fail. |
| 2 | **P0** | **Inventory flag logic wrong** | `inventory()` pulls the flag from `medley[1].get("hook_own")`. Because `hook_own()` never set `flag`, the flag string is `None`, so the medley row is never marked `FLAGGED` even when the soft pass passes. |
| 3 | **P1** | **Soft‑pass hook ordering may be incorrect** | The current code calculates the “under‑bar” hooks **after** the ratings are attached, but it uses `hook_order()` which depends on the hook ratings. Since the soft‑pass flag is added after the ratings, the ordering may not reflect the intended “best” hooks, potentially allowing a non‑under‑bar hook to be flagged. |
| 4 | **P1** | **Potential performance hit** | The soft‑pass logic still calls `hook_ratings()` for all openers before marking the soft‑pass hooks. This means the vision check is performed for every opener even if it will later be marked as soft‑pass and not actually used. The spec says the soft‑pass should limit vision calls to the best `HOOK_SOFT_MAX` hooks. |
| 5 | **P2** | **`hook_bar_under()` may return `None` for valid under‑bar hooks** | The function returns `None` if any part is unmeasured, the backend mismatches, or the live bar is missing. While this is correct, the logic is duplicated in `hook_own()` and could be simplified by centralising the check. |
| 6 | **P3** | **Redundant `hook_rating` pop** | `_build()` pops `hook_rating` from each moment twice (once before rating, once after). The second pop is unnecessary and could be removed for clarity. |
| 7 | **P3** | **Hard‑coded `HOOK_SOFT_MAX` in tests** | The tests hard‑code `HOOK_SOFT_MAX` to 2. If the constant changes, the tests will break. They should reference the constant directly. |

**P1_OR_WORSE**: **2** (issues 1 and 2)