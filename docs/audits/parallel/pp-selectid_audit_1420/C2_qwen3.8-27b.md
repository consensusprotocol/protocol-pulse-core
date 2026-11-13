# qwen3.8-27b (qwen/qwen3.8-27b) 64 s finish=stop usage in 18371 / out 2595 usd~0.094 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1420
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM-5.3-FLASH:**
- **P1-1 (sort key `str(found_at)`):** I missed this in Cycle 1. GLM correctly identified that `str(None)` = `"None"` sorts *before* ISO timestamps (since `"N" < "2"`), inverting "newest first" for records lacking `now`. **However**, the consensus refutation R3 is correct: the actual code uses `str(x[1].get("found_at") or "")`, so `None` becomes `""`, which sorts *last* with `reverse=True`. GLM's specific scenario is refuted by the code. But the *underlying concern* about format variance (naive vs. aware ISO strings) is valid and partially addressed by C1.
- **P1-2 (budget accounting):** GLM raised a legitimate concern about whether `total` in `out["search"]["lineups"]` correctly counts only the candidate's judged line-ups. The consensus refutation R2 is correct: `total += 0 if med.get("replayed") or med.get("cached") else 1` ensures recorded verdicts are free. I agree with R2.
- **P1-3 (seed legacy outcome):** GLM's analysis was incomplete (cut off at 24k tokens). The logic is sound: legacy records without `registry: True` apply their candidate outcome once. I agree with the implementation.

**GROK-4.20:**
- **P2 (class ternary verification):** Grok correctly noted that the "line" classification depends on `attempts` being non-empty. The consensus refutation R1 is correct: `rec["attempts"]` is always appended to on every write attempt, so a line-up that reached a write has a non-empty list. I agree with R1.
- **P2 (`--from-candidate` missing `registry: True`):** Grok claimed this was missing. The consensus refutation R5 is correct: `res["registry"] = True` is set after both branches. I agree with R5.
- **P2 (malformed `until` raises at `due()` time):** This was the basis for C1. I agree with the fix.

**QWEN3.8-27B:**
- **P0-1 (timezone naive/aware crash):** Qwen correctly identified that comparing naive and aware datetimes raises `TypeError`. This was the most significant finding and led to C1. I missed this in Cycle 1. **Agree.**
- **P0-2 (OSError → "clip" classification):** Qwen argued that infrastructure errors (missing file, corrupt JSON) should not close a candidate as "clip" (for good). The consensus recorded this as G1 (single-model, no change) because "the records are tracked files under test." I **partially agree**: in production, a transient I/O error closing a candidate permanently is a real risk. However, the diff is for a test driver, and the records are under version control. The risk is low but non-zero. I would elevate this to P1 if this code were used in production.
- **P1-3 (sort logic):** Qwen's analysis of `str(None)` was incorrect (same as GLM), but the concern about format variance is valid. The C1 fix addresses the timezone issue but not the format variance issue. I **partially agree**.
- **P1-4 (`attempts` undefined):** Refuted by R1. I **disagree** with Qwen here.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My Position | Reasoning |
|---|---|---|
| Qwen P0-1 (timezone crash) | **Agree** | Naive/aware comparison is a real crash risk. C1 fixes it. |
| Qwen P0-2 (OSError → clip) | **Partially agree** | Valid concern for production, but low risk in test driver. Records are tracked. |
| GLM P1-1 (sort key) | **Disagree** | `str(None or "")` = `""`, not `"None"`. R3 is correct. |
| GLM P1-2 (budget) | **Disagree** | R2 is correct: recorded verdicts are free. |
| Grok P2 (class ternary) | **Agree** | R1 is correct: `attempts` is always non-empty for writes. |
| Grok P2 (`registry: True`) | **Disagree** | R5 is correct: it's set after both branches. |
| C1 (timezone fix) | **Agree** | The fix is correct and necessary. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `due()` does not handle `found_at` format variance.**
`pipeline/candidates.py:106` sorts by `str(x[1].get("found_at") or "")`. If `found_at` is a naive ISO string (e.g., `"2026-11-13T19:00:00"`) and another is aware (e.g., `"2026-11-13T19:00:00+00:00"`), lexicographic comparison is not chronological. The C1 fix ensures `_at()` treats naive times as UTC, but `due()` does not use `_at()` for sorting—it uses raw string comparison. **Scenario:** Two candidates with `found_at` at the same second, one naive, one aware. The naive one sorts *after* the aware one (since `""` < `"+00:00"`), inverting "newest first" for that pair. **Fix:** Use `_at()` in the sort key, falling back to a sentinel for `None`.

**P1-NEW-2: `run_due` does not verify that `try_one` returns a valid `judged` count.**
`pipeline/candidates.py:120` does `lineups -= int(judged or 0)`. If `try_one` returns a negative `judged` (e.g., due to a bug in `package.build`), `lineups` increases, potentially allowing more candidates to be tried than the budget allows. **Scenario:** A bug in `package.build` returns `judged = -1`. `lineups` becomes `9` instead of `7`, and the next candidate is tried with `9` line-ups left, exceeding the 8-judged-line-up budget. **Fix:** Assert `0 <= judged <= lineups` in `run_due`.

**P2-NEW-1: `seed()` does not validate that `record.get("now")` is a valid ISO string.**
`pipeline/candidates.py:73` does `at = record.get("now")`. If `now` is `None` or a malformed string, `found_at` is `None` or the malformed string. The C1 fix ensures `_at()` raises on malformed strings, but `seed()` does not call `_at()`—it just stores the raw value. **Scenario:** A record with `now = "tomorrow"` is seeded. `found_at = "tomorrow"`. Later, `due()` sorts by `str("tomorrow")`, which is fine, but if `outcome()` is called with `at = "tomorrow"`, `_at("tomorrow")` raises `ValueError`. **Fix:** Validate `now` in `seed()` or ensure `outcome()` is only called with valid times.

**P2-NEW-2: The driver's `try_one` does not handle the case where `load_candidate` succeeds but `package.build` raises an unexpected exception.**
`tests/package/proof_ledger.py:300-303` catches `(OSError, ValueError, KeyError, TypeError)` from `load_candidate`, but `package.build` (line 308) is not wrapped in a try/except. If `package.build` raises an unexpected exception (e.g., `RuntimeError`), the driver crashes without saving the registry. **Scenario:** A bug in `package.build` raises `RuntimeError`. The driver crashes, the registry is not saved, and the candidate's state is lost. **Fix:** Wrap `package.build` in a try/except and handle the error gracefully (e.g., mark the candidate as "clip" with the error reason).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| State machine (6h/fresh/closed) | 9/10 | 9/10 | No changes. The logic is correct. |
| Budget accounting | 8/10 | 7/10 | P1-NEW-2: `run_due` does not validate `judged` count. |
| Timezone handling | 5/10 | 9/10 | C1 fixes the naive/aware crash. P1-NEW-1 remains (format variance in sort). |
| Driver robustness | 7/10 | 6/10 | P2-NEW-2: `package.build` is not wrapped in try/except. |
| Test coverage | 8/10 | 8/10 | No changes. Tests are comprehensive. |
| Atomicity | 9/10 | 9/10 | No changes. `os.replace` is correct. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:**
- None. The C1 fix addresses the only P0 from Cycle 1.

**P1 HIGH:**
1. **`pipeline/candidates.py:106` — `due()` sort key does not handle `found_at` format variance.** Use `_at()` in the sort key, falling back to a sentinel for `None`.
2. **`pipeline/candidates.py:120` — `run_due` does not validate `judged` count.** Assert `0 <= judged <= lineups`.

**P2 MEDIUM:**
1. **`pipeline/candidates.py:73` — `seed()` does not validate `record.get("now")`.** Ensure `now` is a valid ISO string or handle `None` explicitly.
2. **`tests/package/proof_ledger.py:308` — `package.build` is not wrapped in try/except.** Handle unexpected exceptions gracefully.
3. **`tests/package/proof_ledger.py:300-303` — OSError → "clip" classification.** In production, distinguish between infrastructure errors and gate failures. Low risk in test driver.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `due()` sort key to use `_at()` instead of raw string comparison.** This ensures that "newest first" is chronological, not lexicographic, and prevents subtle ordering bugs that could cause candidates to be tried in the wrong order.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. Fix P1-1: `due()` sort key must use `_at()` to handle `found_at` format variance.
2. Fix P1-2: `run_due` must validate that `judged` is non-negative and does not exceed `lineups`.
3. Fix P2-2: `package.build` in the driver must be wrapped in try/except to handle unexpected exceptions.

If these three fixes are applied, the code is production-ready. The state machine, budget accounting, and atomicity are correct. The test coverage is comprehensive. The C1 fix addresses the most critical issue from Cycle 1.