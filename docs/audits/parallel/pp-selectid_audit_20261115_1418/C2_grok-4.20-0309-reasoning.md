# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 45 s finish=stop usage in 13247 / out 1399 usd_reported=0.031842 usd~0.101 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-20261115_1418 (replay114)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
I missed the dict-equality collapse in the original `pick()` (GLM F1): two records with identical content but different `"record"` paths would deduplicate incorrectly under `r not in first`. I also missed the full retry-diagnosis requirement (GLM F18): only the last attempt's headers were kept, losing the first 429's `x-bf-instance`. The non-JSON `body_head` guard (GLM F3), the corrupted-ledger fail-closed behavior (qwen), and the exact `usd_reported` vs `cost` key drift between the test `Gateway` and driver were not called out in my Cycle 1 review. The alternating-leg order and header-capture tests were areas I focused on, but the usage-contract mismatch was overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
- GLM F1 (`pick` dict equality, spread arithmetic, named-count guard): fully agree. The fix (`{r["record"]: r for r in reversed(rows)}`, explicit `taken` set, `k = min(...)`) is correct and the new test with a duplicated record proves 30 distinct records.
- GLM F2 / qwen P1 (spend read-modify-write + check-before-add): partially agree. Single-threaded design + $0.0003/call vs $0.14 cap bounds overshoot to one call; the atomic replace is acceptable. However the usage-key drift they both flagged is still present (see new P1 below). The corrupted-ledger `RuntimeError` (qwen) is a clear improvement.
- GLM F18 / F10 / F10b / F3 (retry headers, case-sensitivity, x-bf values, non-JSON body): agree. All fixed cleanly; `attempts` list, lowercasing, value reporting, and `body_head` slice are exactly what was needed.
- qwen on `pick` k=0 / shape_of: disagree on severity. Post-fix logic is sound; `str(text or "")` guard is sufficient.
- Consensus items 7-9 (ledger, unreadable record, shape_of): agree they are now correctly handled.

3. NEW FINDINGS FROM THIS REVIEW
[P1] Usage-contract drift between test `Gateway` and driver remains: `Gateway` emits `"cost": 0.0001` (line 312); `ask()` does `text, usage, secs = backend.complete(...)` then `u, usage = cap.seen.get("usage") or {}, usage or {}` followed by `usd_reported=usage.get("usd_reported")` (lines 143-145). If the returned usage dict never contains `"usd_reported"`, `add_spend` always adds 0.0, the ledger stays at 0, the cap never triggers, and the test assertion `assertAlmostEqual(..., 0.0006)` cannot hold. This is the exact drift GLM flagged in Cycle 1; it was not resolved. (tests/package/replay114.py:143-145, test_replay114.py:312, 416)
[P2] No explicit contract or helper from `replay111` for extracting `out_tokens`/`usd` from the backend response (the two different usage shapes are still consulted in one function). Future backend change silently breaks cap or reporting. (replay114.py:144-145)
[P2] `report()` assumes every row has a `"record"` key when building `pairs`; a malformed RESULTS.jsonl row (e.g. from a very early crash before line 198) would KeyError. Not hit today but brittle. (line 212)
[P3] Docstring says "cap $0.15" but `STOP_USD = 0.14`; comment says "$0.14 of the order's $0.15". Minor but should be consistent. (lines 20, 46)
[P3] `pick()` with `--n 3` (smaller than NAMED=5) returns only 3 records (k<0 → else branch `first[:n]`); the order's "the same 5 I sent the team among them" cannot be satisfied. Edge case but undocumented. (line 67)

4. REVISED SCORES
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| pick / selection   | P1      | P3      | GLM F1 fixed by record-key deduplication + test coverage |
| spend ledger / cap | P1      | P1      | Usage-key drift (new P1) was missed in Cycle 1; still present |
| header / retry capture | P2   | P2      | GLM F18/F10 fixed but usage-contract P1 dominates |
| error handling / reporting | P2 | P2      | Unreadable-ledger and non-JSON guards added; new brittleness found |
| test completeness  | P2      | P1      | Test asserts 0.0006 spend but code adds 0 → test is misleading |

5. FINAL PRIORITY LIST
[P1] replay114.py:143-145 — unify usage extraction (`usd_reported=usage.get("usd_reported") or usage.get("cost")` or import helper from replay111); update `Gateway` or backend.complete so test and production agree on the key. Must fix before any paid run.
[P1] test_replay114.py:312,416 — make the spend-accumulation test actually verify the key that `add_spend` uses.
[P2] replay114.py:212 — guard `pairs` construction with `if "record" not in r: continue`.
[P2] replay114.py:67 — document `--n < len(NAMED)` behavior or enforce `n >= len(named)`.
[P3] Lines 20/46 — make cap constant and docstring match.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Introduce a single `extract_usage(backend_response_or_usage_dict)` helper (shared with replay111) that normalizes `out_tokens`, `usd_reported` (or `cost`), and shape; call it once in `ask()` so the test, driver, cap logic, and report all use the identical contract.

7. PRODUCTION READY?
No — the [P1] usage-key drift must be resolved (and the corresponding test made honest) before any paid run; the cap cannot be trusted while `add_spend` accumulates 0.0 on real responses that only contain `"cost"`.

P1_OR_WORSE: 2