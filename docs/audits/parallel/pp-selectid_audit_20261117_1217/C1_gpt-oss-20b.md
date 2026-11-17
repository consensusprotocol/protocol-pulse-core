# gpt-oss-20b (openai/gpt-oss-20b) 115 s finish=stop usage in 12763 / out 17538 usd_reported=0.002569 usd~0.301 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | `soft_second` does not add flags to the cleared moments | **P0** | The test `TestStage2a.test_soft_codes_and_the_second_family` expects `cleared["b"].get("step_a_flags")` to be set, but `soft_second` only returns a dict and never mutates `cleared`. |
| 2 | `inventory` uses the wrong condition for the `context_a` gate | **P0** | The status of `context_a` is computed with `all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t)) for t in truth.values())`, which makes the gate PASS for the test data. It should be based on `soft_a` (all step‑A codes are soft). |
| 3 | `inventory` builds `lab_codes` using the keys of `a_by` (moment IDs) instead of clip labels | **P1** | In the real pipeline `a_by` keys are moment IDs, while `seg_flags` and `who` are keyed by clip labels. This mismatch means the second‑family soft codes are never merged into the context‑A flags. |
| 4 | `inventory` constructs `context_a` flags with the wrong label (`mid` instead of the clip label) | **P1** | The flag sentence uses `lb` (moment ID) as the clip label, producing incorrect wording and wrong channel names. |
| 5 | `inventory` passes the wrong key to `who` when building `context_a` flags | **P1** | Because `lb` is a moment ID, `(who or {}).get(lb)` returns `None`, so the channel name is omitted from the flag sentence. |
| 6 | `inventory` uses `lab_codes[lb]` where `lb` may be a moment ID, not a label | **P1** | The flag list is empty or wrong when `a_by` keys are moment IDs, leading to missing or incorrect flags. |
| 7 | `soft_step_a` is defined but never used in `_build` | **P2** | While not currently exercised, the function is dead code and could cause confusion or future regressions. |
| 8 | `soft_step_a` uses `fails.get(m["moment_id"])` but `fails` may be `None` | **P2** | If `fails` is `None`, the function will raise an exception. |
| 9 | `soft_step_a` returns a new dict but does not preserve other keys of the moment | **P2** | The returned moment loses any existing data that might be needed downstream. |
| 10 | `soft_edges` requires `t.get("ok") is True` but the test data sometimes has `ok` missing | **P2** | This could silently drop valid soft‑edge cases. |

**P1_OR_WORSE: 6**