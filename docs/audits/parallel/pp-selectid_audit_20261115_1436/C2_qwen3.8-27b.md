# qwen3.8-27b (qwen/qwen3.8-27b) 64 s finish=stop usage in 13511 / out 2018 usd_reported=0.003281 usd~0.071 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1436
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the consensus synthesizer) correctly identified the P1 regarding model attribution (glm F5) and the P2 regarding the spend limit (qwen). However, looking back at the raw Cycle 1 outputs provided in the prompt:

*   **Grok-4.20** correctly identified that `partition("\n\n")` is fragile and suggested `split("\n\n", 1)`. I accepted the code's use of `partition` in the consensus because `partition` *is* functionally equivalent to `split(..., 1)` for the purpose of taking the first part, but I failed to explicitly validate that `partition` returns a 3-tuple `(head, sep, tail)` which is exactly what the code unpacks. Grok's concern was valid stylistically but the code is correct.
*   **GLM-5.3-Flash** raised a subtle point in F1 about the "stop" path producing a 5/5-looking report. It correctly noted that `verdict()` fails closed (returns `False`) when `own` is `None`, but the *report* might be ambiguous. The Cycle 1 consensus noted this was "acted on" by adding a "stopped at $x" marker in the report. I need to verify if the *current* code actually does this.
*   **Qwen3.8** correctly flagged that the router limit ($0.55) exceeded the ruling cap ($0.50). The consensus noted this was fixed to $0.50. I need to verify the current code.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM F1 (Stop path ambiguity):** **Agree.** The code now includes `"error": f"stopped at ${r.spent():.4f}"` in the row (line 139). The `report()` function (line 174) explicitly checks `if "error" not in r` and prints `NO RATING: {r['error']}`. This resolves the ambiguity. The verdict correctly fails closed.
*   **GLM F2 (Error path loses reason):** **Disagree with severity.** GLM said P2. I agree it's a minor opacity issue, but since `rate()` returns `{"error": err or "no rating"}` when `r` is falsy, and `r` is only falsy if the model didn't return a valid record, the error *is* captured. If `r` exists but is malformed, `H.own_rating(r)` might raise or return non-int, causing `verdict` to fail. The report will show `own: None`. This is acceptable for a "report before use" tool; it fails closed.
*   **Grok P2 (Fragile partition):** **Partially Agree.** `partition` is safe here because it guarantees the separator is found or returns empty strings. The code checks `if not sep: raise ValueError`. This is robust. `split(..., 1)` would also work but `partition` is more Pythonic for this specific "split once" use case. No change needed.
*   **Qwen P2 (Spend Limit):** **Agree.** The code now has `LIMIT_USD = 0.50` (line 46). This matches the ruling cap. The comment explains why it sits above `STOP_USD`. This is correct.
*   **Consensus P1 (Model Attribution):** **Agree.** The code now includes `backend` in the row (line 142-143 via `rate()` returning `dict(r, ...)` where `r` comes from `hook_ratings` which includes `backend`). The `verdict()` function (line 115) checks `r.get("backend") == model`. The report (line 173) prints `by {r.get('backend')}`. This is fully implemented.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] F1 — `rate()` does not explicitly propagate `backend` if `hook_ratings` doesn't include it
In `rate()` (line 102-109), the code does:
```python
r = got.get(m["moment_id"])
return dict(r, own=H.own_rating(r)) if r else {"error": err or "no rating"}
```
If `hook_ratings` returns a record `r` that does *not* contain a `backend` key, then `dict(r, own=...)` will not have `backend`. Later, `verdict()` checks `r.get("backend") == model`. If `backend` is missing, `r.get("backend")` is `None`, which is not equal to `model`, so the rating is ignored. This is fail-closed, which is good. However, the report will print `by None`. This is a minor cosmetic issue but could be confusing. **Recommendation:** Ensure `hook_ratings` always returns `backend`, or add a fallback in `rate()`.

### [P3] F2 — `main()` truncates the report to 3000 chars
Line 189: `print(open(os.path.join(OUT, "REPORT.md")).read()[:3000])`. This is a quick-and-dirty console dump. If the report is longer, the user won't see the full "every rating" section. This is acceptable for a CLI tool where the user can read the file, but it's a nit.

### [P3] F3 — `sys.path.insert` is done twice
Lines 35-36:
```python
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
```
This is standard for test scripts that need to import from both the repo root and the local directory. No issue.

### [P2] F4 — `negatives()` reads from proof builds, which may not be present in CI
The test `test_the_five_negatives_are_read_rated_2_with_their_text` (line 298-302) calls `X.negatives()`, which reads from `H.build_records(proof or H.PROOF, since="ledger_20261113_161500")`. If the proof builds are not present in the CI environment, this test will fail. The Cycle 1 consensus noted this was "deliberate" because the driver's whole input is those builds. However, for a unit test, this is a dependency on external data. **Recommendation:** Mock `H.build_records` and `H.all_ratings` in the unit test to make it hermetic.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Prompt Construction | P3 | P3 | No change. Braces are escaped correctly. |
| Cache Isolation | P2 | P2 | No change. `cache=None` is correct. |
| Model Routing | P1 | P2 | Fixed. `backend` is now checked in `verdict()`. |
| Spend Limits | P2 | P3 | Fixed. `LIMIT_USD` is now $0.50. |
| Verdict Logic | P2 | P3 | Fixed. Fails closed on missing `backend`. |
| Test Hermeticity | P2 | P2 | No change. `negatives()` still reads from proof builds. |

## 5. FINAL PRIORITY LIST

1.  **[P2]** `tests/package/test_hook115.py:298` — `test_the_five_negatives_are_read_rated_2_with_their_text` depends on external proof builds. Mock `H.build_records` and `H.all_ratings` to make the test hermetic.
2.  **[P2]** `tests/package/hook115.py:109` — `rate()` does not explicitly ensure `backend` is present in the returned record. If `hook_ratings` omits it, the report will show `by None`. Add a fallback or assert.
3.  **[P3]** `tests/package/hook115.py:189` — `main()` truncates the report to 3000 chars. Consider printing the full report or directing the user to the file.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Make the unit test for `negatives()` hermetic by mocking the proof build reads, so that the test suite can run in any environment without requiring the specific proof data from ruling 112.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1.  The unit test for `negatives()` must be made hermetic (mock the proof build reads).
2.  The `rate()` function should ensure `backend` is present in the returned record, or the report should handle `None` gracefully.

P1_OR_WORSE: 0