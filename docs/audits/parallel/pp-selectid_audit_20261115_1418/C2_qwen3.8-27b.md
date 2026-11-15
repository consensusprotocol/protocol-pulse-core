# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 14885 / out 1884 usd_reported=0.003352 usd~0.073 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1418
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "consensus" synthesizer) correctly identified the `pick()` dict-equality bug (glm F1) and the `usage` None-guard (qwen). However, I **missed** two specific issues that the other models raised or that are now visible in the fixed code:

1.  **The `usd_reported` key mismatch (glm F2, partially):** GLM noted that the driver reads `usage.get("usd_reported")` but the fake gateway/test uses `cost`. While the consensus noted this was "guarded," it didn't explicitly flag that **the real Heimdall gateway returns `cost` in the usage block, not `usd_reported`**. If the real API returns `{"cost": 0.0001}` and the code looks for `usd_reported`, the spend ledger will **never increment**, and the cap will never trigger. This is a critical integration bug.
2.  **The `pick()` spread arithmetic edge case (glm F1, point 2):** GLM correctly identified that `int(i * len(rest) / k)` can produce duplicate indices if `len(rest)` and `k` are not coprime in a specific way, or more importantly, that the "spread" logic is fragile. The fix in the code uses `rest[int(i * len(rest) / k)]`, which is a standard "evenly spaced" selection, but it **does not guarantee distinct records** if `rest` contains duplicates (which it shouldn't after the dedup fix, but the logic is still brittle). More critically, if `k` is large relative to `len(rest)`, it picks all of them, which is fine, but the "spread" claim in the report is only true if the input is sorted and distinct.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM F1 (pick dict equality):** **Agree.** The fix `rows = sorted({r["record"]: r for r in reversed(rows)}.values(), ...)` correctly deduplicates by `record` key. This is the right fix.
*   **GLM F2 (Spend ledger race/key mismatch):** **Partially Agree.** The race condition is acceptable for a single-threaded script. However, the **key mismatch** is a **P1** bug. The code at line 145 reads `usage.get("usd_reported")`. The test fake returns `{"cost": 0.0001}`. The real Heimdall API (per replay111 context) returns `cost`. If the real API does not return `usd_reported`, the spend is always 0.0, and the cap is never hit. **This must be fixed to read `cost` or `usd_reported` with a fallback.**
*   **QWEN P1 (usage None):** **Agree.** The code now uses `usage or {}` at line 143. This is correct.
*   **GLM F18 (Retried headers):** **Agree.** The `Capture` class now keeps `attempts` in order. The test `test_every_attempt_of_a_retried_call_keeps_its_headers` verifies this. This is a good fix.
*   **GLM F10 (Header case sensitivity):** **Agree.** `headers_of` lowercases keys. This is correct.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P1] F1 — Spend ledger reads the wrong key (`usd_reported` vs `cost`)
`replay114.py:145`

```python
row.update(..., usd_reported=usage.get("usd_reported"), ...)
```

The test fake gateway returns `{"cost": 0.0001}` in the `usage` block. The real Heimdall API (as seen in replay111) returns `cost`. If the real API does not include a `usd_reported` field, `usage.get("usd_reported")` returns `None`, which is treated as `0.0` in `add_spend`. The spend ledger will **never increment**, and the run will **never stop** at the cap. This is a critical integration bug.

**Fix:** Change line 145 to:
```python
usd = usage.get("usd_reported") or usage.get("cost") or 0.0
row.update(..., usd_reported=usd, ...)
```
And update the test fake to return `usd_reported` or ensure the code handles `cost`.

### [P2] F2 — `pick()` spread logic can still produce non-distinct records if `rest` has duplicates
`replay114.py:68`

The fix deduplicates `rows` by `record` key, so `rest` should not have duplicates. However, the spread logic `rest[int(i * len(rest) / k)]` is a standard "evenly spaced" selection. If `len(rest)` is small and `k` is large, it picks all of them. If `len(rest)` is large, it picks a subset. The logic is correct for distinct records, but the "spread evenly" claim in the report is only true if the input is sorted by `out_tokens`. The code does sort by `out_tokens`, so this is fine. **No change needed**, but the comment should clarify that "spread" means "evenly spaced in the sorted order."

### [P2] F3 — `report()` does not handle the case where `attempts` is missing
`replay114.py:219`

```python
for at in (r.get("attempts") or [r])
```

This is correct. If `attempts` is missing, it uses the row itself. This is a good defensive fix.

### [P3] F4 — `shape_of` does not handle `text` being `None`
`replay114.py:124`

```python
t = str(text or "").strip()
```

This is correct. `str(None or "")` is `""`. This is a good defensive fix.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `pick()` | P1 | P3 | Fixed by dedup by `record` key. |
| Spend Ledger | P2 | P1 | **Key mismatch** (`usd_reported` vs `cost`) means the cap never triggers. |
| `Capture` | P2 | P3 | Fixed by keeping `attempts` in order. |
| `report()` | P3 | P3 | No change. |
| Tests | P2 | P2 | Tests pass, but they do not catch the `usd_reported` vs `cost` mismatch because the fake gateway returns `cost` and the code reads `usd_reported` (which is `None` in the fake, so the test passes with `0.0` spend, which is not the intended behavior). |

## 5. FINAL PRIORITY LIST

1.  **[P1] F1 — Spend ledger reads the wrong key.** `replay114.py:145`. Change `usage.get("usd_reported")` to `usage.get("usd_reported") or usage.get("cost") or 0.0`. Update the test to verify that the spend ledger increments when `cost` is returned.
2.  **[P2] F2 — `pick()` spread logic.** `replay114.py:68`. No change needed, but add a comment clarifying that "spread" means "evenly spaced in the sorted order."
3.  **[P3] F4 — `shape_of` handles `None`.** `replay114.py:124`. No change needed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the spend ledger key mismatch** so that the cap actually triggers when the real API returns `cost` instead of `usd_reported`.

## 7. PRODUCTION READY?

**No.** The spend ledger key mismatch is a P1 bug that will cause the run to exceed the cap. Fix it before shipping.

P1_OR_WORSE: 1