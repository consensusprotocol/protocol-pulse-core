# gpt-oss-20b (openai/gpt-oss-20b) 34 s finish=stop usage in 11204 / out 5373 usd_reported=0.000707 usd~0.114 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | P3 | `fallback_subject` skip set includes channel words | The skip set is built from all channel names (`{w.lower() for c in chans for w in re.findall(r"[A-Za-z]+", str(c))}`) plus `"i"` and `"bitcoin"`. If a channel name contains the word “Bitcoin” or “i”, that word will be skipped when searching for the subject. While unlikely, it could cause the subject to be incorrectly inferred as “Bitcoin” when the intended subject is a proper name that includes “Bitcoin”. |
| 2 | P3 | `fallback_fields` uses `budget is not None` check inside the generator expression | The generator expression `next((t for t in (f.format(subject=subject, names=names) for f in FALLBACK_CLOSING) if budget is not None and budget[0] <= len(t.split()) <= budget[1]), None)` will evaluate `budget` for every template, even if `budget` is `None`. This is harmless but slightly inefficient. |
| 3 | P3 | `fallback_fields` returns `None` when no template fits the budget | The function returns `None` if no closing template fits the word‑budget. The caller (`_build`) treats this as a failure and breaks the loop. This is intentional, but the code could be clearer by explicitly documenting that `None` signals “no fallback available”. |
| 4 | P3 | `inventory` adds a `fallback_line` flag only when `soft` and `fallback_line` are truthy | The flag is added with `**({"fallback_line": {"status": "FLAGGED", ...}} if soft and fallback_line else {})`. If `fallback_line` is an empty string (unlikely but possible if the fallback text is empty), the flag would not be added. The code assumes a non‑empty string, which is reasonable given the templates. |
| 5 | P3 | `LINE_ONLY_WRITES` increased from 2 to 3 but comments still refer to “4 writes a line” | The comment on line 98 mentions “up to 4 writes a line”, which is inconsistent with the code that allows 3 writes of the line alone plus the initial write (total 4). The comment could be clarified to avoid confusion. |

**P1_OR_WORSE**: 0 (no P0 or P1 findings)