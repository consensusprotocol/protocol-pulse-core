# gpt-oss-20b (openai/gpt-oss-20b) 165 s finish=stop usage in 16550 / out 22891 usd_reported=0.003350 usd~0.393 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | `inventory` uses undefined variable `med` | **P0** | In `inventory` the line `med_fl = ([f"..."] if hook_fl and medley is not None and med[0] else [])` references `med`, which is not defined in the function scope. This will raise a `NameError` and cause all tests that hit `inventory` to fail. |
| 2 | `inventory` checks `med[0]` instead of `medley[0]` | **P0** | The intended check is whether the medley was successful (`medley[0]`). Using `med[0]` is a logic error that can produce wrong flagging and further test failures. |
| 3 | `inventory` does not include join‑sentences for soft candidates when `medley[0]` is `False` | **P0** | For soft‑only failures (e.g., `J2` in the tests) `chain` is `None` because `medley[0]` is `False`. Consequently `med_fl` is empty, so the medley gate never reports the expected join‑sentence flag. |
| 4 | `lineup_soft` treats a question‑hook flagged join as a soft failure when it is the only flagged join | **P1** | If `question_hook(segs)` is `True` and the only flagged join is the first one (`js[0]`), the current logic sets `bridge = None` and includes that join in `soft_joins`. This incorrectly allows a hard failure (no bridge after a question) to be considered soft and potentially kept. |
| 5 | `lineup_soft` may incorrectly flag a hard failure as soft when `question_hook` is `True` and only the first join is flagged | **P1** | See issue #4 – this can let a hard failure slip through the soft‑pass logic and be retried, violating the hard‑gate rule. |
| 6 | `inventory` incorrectly uses `med_fl` for the `ly_shape` gate in the diff comment, but the actual code uses `join_sentences` correctly – no bug here. | **P3** | Minor documentation mismatch; no impact on functionality. |
| 7 | No other functional bugs detected that affect the current test suite. | **P3** | Minor style or documentation issues that do not break tests. |

**P1_OR_WORSE**: 2 (issues #4 and #5)