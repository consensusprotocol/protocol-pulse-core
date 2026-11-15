# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 12000 / out 914 usd_reported=0.031323 usd~0.083 (upper-bound price)

**CODE AUDIT: pp-selectid-20261114_2043 (RULING 107 Q1)**

**Summary**  
The diff correctly implements the orchestrator ruling: abandoned calls are booked against the model's own reported rate (usd_reported / prompt tokens of calls that carried a vendor figure) once ≥3 such calls exist; otherwise list price (Backend.prompt_usd) is used. The $20 cap basis becomes the reported basis. `prompt_tokens_upper` (conservative) is used for the prompt size. Legacy ledgers without `in_reported` are handled by falling back to the `in` field. All call-site changes preserve prior behavior via defaults. The new test file exercises every branch, legacy paths, late-answer replacement, error paths, logging of `booked_basis`, and mutation coverage (12/12 killed). Existing provider tests remain green.

**Detailed Answers to PLEASE CHECK**
(1) Yes — `reported_rate` returns exactly `usd_reported / (in_reported or in)` and only once `reported_calls >= RATE_MIN_REPORTED` (3). Before that, or on zero tokens/unreadable ledger/no spend_path, it returns `None` → list price.  
(2) No — the cap cannot be under-booked. The rate is all-in (includes output cost from prior calls); the prompt is counted via `prompt_tokens_upper` (never under-count). This produces a conservatively high booking for an abandoned call.  
(3) No deadlock or nesting. `reported_rate` acquires the `fcntl` lock, reads, and releases before `booking_usd` returns. `_settle` then acquires it again in the same thread (sequential `with` blocks). The late-answer path runs in the worker thread; the shared lock serializes access. `SpendLimit` is caught in `reported_rate` (falls back to list) but still raised from `_settle` where the original code did.  
(4) Yes — `b["in"] - n_in` yields the prior count because the token-count update to `b["in"]` occurs earlier in the same locked section (verified by the two legacy-ledger tests). Both `_settle` and `_replace_booking` use identical logic.  
(5) Yes — new parameters default to `None`; the ternary `(usd if unreported is None else unreported)` and equivalent in `_replace_booking` restore exact prior arithmetic for all existing call sites.  
(6) Confirmed. The 9 new tests + 75 existing provider tests pass. All 12 mutations (rate never used, <3 calls, zero-token row, legacy carry-over in both sites, late replacement vs. late error, list-price fallback, etc.) are killed.

**Findings**
- **[P3]** `RATE_MIN_REPORTED = 3` and the full ruling text are duplicated in the module docstring and test file; a single constant + reference would be cleaner.  
- **[P3]** `reported_rate` and `booking_usd` lack type hints while surrounding methods in `providers.py` use them; minor consistency issue.  
- **[P3]** The `SpendLimit` catch in `reported_rate` (returning list price) is explicitly documented but slightly at odds with the strict M12 FAIL-CLOSED stance elsewhere in the codebase. Behavior matches the ruling, so acceptable.  
- **[P2]** No test case exercises an unreadable ledger *during* the abandon closure's `booking_usd` call (only the `except SpendLimit` path inside `reported_rate`). The happy-path coverage is otherwise exhaustive.  
- **[P3]** New test depends on `test_providers` helpers (`Fake`, `SlowFail`, `router`, `wait_for`); this is appropriate but increases coupling of the ruling test to the test harness.

All governing laws reviewed (SENTENCE LAW through L-l, LAW 20/M2, M12, LAW 22, smallest-diff rule, no new renderer/compositor/selector, GPU0-only, release authorization on exact bytes, model-reply validation, canon.py routing, etc.). This isolated spend-accounting change touches none of the editorial, clipping, transcription, credit, or release-auth paths. v2f reference, protected preview, and L-d/L-j gates are unaffected. No data loss, no gate that must fail can now pass, no mutable selection locks altered.

P1_OR_WORSE: 0