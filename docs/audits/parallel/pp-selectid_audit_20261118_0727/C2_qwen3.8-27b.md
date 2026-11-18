# qwen3.8-27b (qwen/qwen3.8-27b) 259 s finish=stop usage in 5757 / out 7087 usd_reported=0.005321 usd~0.124 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261118_0727 | Ruling 144 Part 2

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma's P0 (upper-bound blind spot):** I initially flagged this in Cycle 1 as a concern. After seeing the consensus and re-reading the ruling context, I confirm it is **by design, not a defect**. The six target moments are 18–22 h old; the query window `[now−26h, now−14h]` captures them precisely. Today's moments are explicitly out of scope for this one-exception build. I was right to flag the mechanism but wrong to rate it P0.

**GPT-OSS P2 #2 (`a.hours < base_h` → future `a_now`):** I did not explicitly call this out in Cycle 1. It is a valid gap: the code permits `--hours 1` through `--hours 30` under the exception, but the arithmetic `a.hours - base_h` goes negative below 12, producing a *future* adapter clock. In practice the build fails closed (the target moments are older than the narrowed window, so zero rows → M12), but the code is semantically wrong and would confuse a future maintainer.

**Qwen's `seen[-1]` fragility:** Valid P3 I under-weighted. If a retry path ever calls `LB.rows` twice, the test silently validates only the second call.

**GPT-OSS P3 #4 (mock.patch without context manager):** **Incorrect finding.** Line 76 of the diff clearly shows `with mock.patch("sys.stdout"):` — it *is* a context manager. I agree with the code, not with GPT-OSS here.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Model / Finding | Verdict | Reasoning |
|---|---|---|
| Gemma [P0] upper-bound excludes last 14 h | **Disagree on severity → P3 (by design)** | The ruling targets yesterday's batch (18–22 h old). The window `[now−26h, now−14h]` is correct. No-flag builds are unaffected (test iteration 1 proves it). |
| Gemma [P2] tautological test | **Partially agree → P3** | The test mocks `LB.rows` and checks the *arguments*, not the *returned rows*. This is appropriate for a clock-shift unit test; the adapter's filtering logic is tested in its own suite. Not tautological, just narrow in scope. |
| GPT-OSS P2 #1 `WINDOW_H` never restored | **Downgrade → P3** | `main()` is a single-invocation script entry point. The process exits. The test correctly saves/restores. No multi-call path exists in production. |
| GPT-OSS P2 #2 `a.hours < base_h` → future clock | **Agree → P2** | Valid. No guard prevents `--hours 6 --pbx-exception`. Fails closed but is semantically wrong. |
| GPT-OSS P3 #3 `ledger_entries` patch | **Agree → P3** | Fragile to future changes but harmless now. |
| GPT-OSS P3 #4 `mock.patch` without CM | **Disagree** | It *is* a context manager (line 76). |
| GPT-OSS P3 #5 tolerance 0.05 h | **Agree → P3** | Generous but fine for a clock test. |
| GPT-OSS P3 #6 `Past` exception stops early | **Agree → P3** | Intentional; the test only validates the clock argument. |
| Qwen P3 redundant `import tempfile` | **Agree → P3** | Line 56 duplicates module-level line 42. |
| Qwen P3 `seen[-1]` without length check | **Agree → P3** | Add `assertEqual(len(seen), 1)` for explicitness. |
| Qwen P3 `a_now` naming | **Agree → P3** | Cosmetic. |
| Qwen boundary arithmetic verification | **Agree** | Correct. Moment at exactly `--hours` old is dropped; 25.999 h is admitted. |
| Qwen "no leak without flag" | **Agree** | Ternary returns `now`; `WINDOW_H` untouched. |
| Claude consensus (Gemma P0 is by design) | **Agree** | The ruling is explicit: one video, yesterday's batch, six named moments. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] `seen` list accumulates across loop iterations without clearing.**
`tests/package/test_ruling_137.py`, line 60: `seen = []` is defined once before the `for` loop. After iteration 1, `len(seen) == 1`; after iteration 2, `len(seen) == 2`. The test uses `seen[-1]` which is correct, but a `seen.clear()` at the top of each iteration (or a fresh list per iteration) would make the intent unambiguous and protect against a future third iteration.

**[P3] The log line (lines 30–32) interpolates `a.pbx_exception` (the free-text reason) into the build log.**
This is correct for auditability, but if the reason string contains newlines or very long text, it could break log parsing. A `repr()` or length cap would be defensive. Extremely low risk given the PBX-controlled input.

**No new P0 or P1 findings.** The combined analysis confirms the code is correct for its stated purpose.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Clock-shift arithmetic (`a_now`) | P0 concern (upper bound) | **P3 (by design)** | Consensus + ruling context confirm the window is intentional. |
| Guard against `a.hours < base_h` | Not flagged | **P2** | GPT-OSS caught it; I confirm. No guard exists. |
| `WINDOW_H` persistence | P2 (GPT-OSS) | **P3** | Single-process script; no multi-call path. |
| Test scope (mocks args, not rows) | P2 (Gemma) | **P3** | Appropriate for a unit test of the clock argument. |
| `seen[-1]` fragility | Not flagged | **P3** | Qwen caught it; valid but low-risk. |
| Redundant `import tempfile` | Not flagged | **P3** | Qwen caught it. |
| `mock.patch("sys.stdout")` usage | P3 (GPT-OSS, incorrect) | **N/A** | It *is* a context manager. Finding retracted. |

---

## 5. FINAL PRIORITY LIST

| # | Severity | File / Line | Finding |
|---|---|---|---|
| 1 | **[P2]** | `proof_ledger.py` line 27 | No guard against `a.hours < base_h`. If `--hours 6 --pbx-exception` is passed, `a_now` becomes a future time. Add `if a.hours < base_h: return 2` (or clamp) inside the `a.pbx_exception` branch. Fails closed today, but the code is semantically wrong. |
| 2 | **[P3]** | `test_ruling_137.py` line 80 | `seen[-1]` without `assertEqual(len(seen), 1)`. Add a length check before the assertions. |
| 3 | **[P3]** | `test_ruling_137.py` line 56 | Redundant `import tempfile` (already at module level, line 42). Remove. |
| 4 | **[P3]** | `test_ruling_137.py` line 60 | `seen` list not cleared between loop iterations. Add `seen.clear()` at top of each iteration. |
| 5 | **[P3]** | `proof_ledger.py` line 27 | `a_now` is a confusing name (reads as "argparse-namespace-now"). Consider `adapter_clock` or `shifted_now`. |
| 6 | **[P3]** | `proof_ledger.py` line 20 | `package_pin.WINDOW_H` is widened but never restored in `main()`. Acceptable for a single-run script; add a comment noting the process-exit assumption. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a one-line guard — `if a.pbx_exception and a.hours < base_h: return 2` — immediately after the `base_h` assignment (line 18), so the clock-shift arithmetic can never produce a future time, even if a future caller passes a sub-12-hour value with the exception flag.

---

## 7. PRODUCTION READY?

**Yes, with one condition.**

The code is correct for its stated purpose (one exception build, `--hours 26`, six named moments 18–22 h old). The no-flag path is provably unchanged. The boundary arithmetic is exact. The test kills both stated mutations.

**Condition:** Add the P2 guard against `a.hours < base_h` (one line, line 18–19 area) before merge. This is not a data-safety issue (the build fails closed), but it is a semantic correctness issue that will confuse the next person who reads the code or extends the exception.

All P3 items are optional and can be addressed in a follow-up cleanup pass.

---

P1_OR_WORSE: 0