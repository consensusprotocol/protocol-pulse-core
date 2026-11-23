# gpt-oss-20b (openai/gpt-oss-20b) 41 s finish=stop usage in 6931 / out 6910 usd_reported=0.000760 usd~0.124 (upper-bound price)

**Answers to the four questions**

1. **Can the clean pass, or a verdict that was never measured, get a line through?**  
   No. In the clean pass `soft` is `False`, so the first `if` block that would set `soft=True` is never executed. The second guard (`if not val["ok"] and not val.get("soft")`) then triggers, appending the line to `value_lost` and preventing the package from being built. Likewise, if a verdict is never measured (`val.get("measured") is False` or `None`), the soft block is skipped and the line is lost. Thus a line cannot slip through in either of those scenarios.

2. **Do fidelity, context, length and the banned‑words checks stay HARD for a soft‑value line?**  
   Yes. The soft flag is added only to the `value` gate. The subsequent gates (`takeaway_fidelity`, `takeaway_context`, `takeaway_length`, `takeaway_banned`, etc.) are still evaluated as hard gates. The log message in the soft block explicitly states that “fidelity, length and the banned words stay HARD.” Therefore a soft‑value line is still subject to the hard‑gate checks.

3. **Is the FLAGGED row consistent with what the render reads (its text = the shipped closing line)?**  
   Yes. The inventory code adds `status: "FLAGGED"` and a `flags` list containing the exact line text (`VALUE_FLAG.format(line=value.get("text"))`). The test `TestRuling150ValueSoft` asserts that `row["text"]` equals `TM.Rig.LINE`, which is the line that the render will use. Hence the FLAGGED row is consistent with the rendered closing line.

4. **Is there any path where the never‑empty pass now seals a closing line with no value verdict at all?**  
   No. If a value verdict is not present (`val.get("measured") is not True`), the soft block is bypassed and the line is treated as a loss (`value_lost`). Therefore the never‑empty pass cannot seal a line that has no value verdict.

---

### Findings (severity tags)

| # | Finding | Severity |
|---|---------|----------|
| 1 | The code checks `val.get("measured") is True`. If `measured` is ever stored as a non‑boolean (e.g., string `"True"` or integer `1`), the soft flag will never be set. | P2 |
| 2 | The inventory logic adds `status: "FLAGGED"` only when `value.get("soft")` and `value.get("ok") is not True`. If `value.get("ok")` were `None` (unlikely but possible if the gate logic changes), the row would not be flagged. | P3 |
| 3 | There is a theoretical path where a line could pass the value gate with `ok=True` but without a value verdict (`measured` missing). The current code would treat it as a clear‑yes line, potentially violating the intent that a line must have a value verdict. | P2 |
| 4 | No other critical issues were identified. |  |

**P1_OR_WORSE:** 0 (no P0 or P1 findings)