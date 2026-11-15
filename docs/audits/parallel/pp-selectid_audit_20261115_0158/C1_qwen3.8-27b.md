# qwen3.8-27b (qwen/qwen3.8-27b) 27 s finish=stop usage in 17488 / out 1321 usd_reported=0.001755 usd~0.072 (upper-bound price)

To: Protocol Pulse Audit Team
Re: Code Audit — `pp-selectid-20261115_0158` (Ruling 111)

I have reviewed the diff for `tests/package/replay110.py`, `tests/package/replay111.py`, and `tests/package/test_replay111.py` against the Governing Laws and the specific "PLEASE CHECK" items.

### Findings

**1. [P1] `FormatBackend` System Prompt Mutation**
In `replay111.py`, the `FormatBackend.complete` method constructs the system message as:
```python
"messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."}, ...]
```
The test `test_the_json_mode_and_the_effort_are_the_only_fields_added_to_productions_body` asserts that `bodies[1]` (the new backend) equals `bodies[0]` (the production backend) *after* popping `response_format` and `reasoning_effort`. However, the production backend (`P.HeimdallBackend`) does **not** append `" Reply with one JSON object only."` to the system prompt.
*   **Violation:** The test will fail because the `messages` field in the body will differ.
*   **Law Impact:** This violates the intent of "exactly as production asks" (L-l / Ruling 111 Order). If the test is fixed to ignore the system prompt, the code is still altering the prompt, which may steer the model (contrary to the note that "a schema... could steer the answer," though a system prompt suffix is less risky, it is still a deviation from the "unchanged" baseline). If the test is not fixed, the code is broken.
*   **Fix:** Remove the suffix from the system prompt in `FormatBackend` to match production exactly, or update the test to explicitly allow this specific suffix (but the former is preferred for "smallest diff" and "no steering").

**2. [P2] `shape()` Truncation Logic Edge Case**
In `replay111.py`, the `shape` function checks for truncation:
```python
if (cap and out_tokens and out_tokens >= cap) or t.count("{") > t.count("}") or \
        (pos is not None and pos >= len(t) - 1):
    return "truncated"
```
The condition `pos >= len(t) - 1` relies on `json.JSONDecodeError.pos`. If the JSON is invalid due to a syntax error at the very end (e.g., missing closing brace), `pos` is often `len(t)`. However, if the error is "Expecting value" at the end, `pos` might be `len(t)`.
*   **Issue:** The test case `('{"a": "an answer cut mid-wor', "truncated")` passes because `pos` will be near the end. However, the logic `t.count("{") > t.count("}")` is a heuristic. If a valid JSON string contains unbalanced braces inside a string value (e.g., `{"a": "}"}`), this heuristic fails.
*   **Law Impact:** Low risk for "diagnosis only" (Ruling 111), but it may misclassify "invalid JSON" as "truncated" or vice versa, affecting the "3 commonest failure shapes" report.
*   **Fix:** The heuristic is acceptable for a diagnostic tool, but the `pos` check should be `pos == len(t)` or `pos > len(t) - 2` to be more robust against off-by-one errors in different JSON parsers.

**3. [P3] `choose()` Tie-Breaking with `None` p50**
In `replay111.py`, `choose` uses:
```python
-(sc[v]["p50_s"] if sc[v]["p50_s"] is not None else float("inf"))
```
If both variants have `None` p50 (no valid answers), they tie on p50. The logic is sound. However, if one has `None` and the other has a value, the one with `None` gets `-inf` (lowest priority), which is correct (we prefer lower p50, so `None` is worst).
*   **Note:** This is correct. No change needed.

**4. [P3] Spend Stop Logic**
`ask_one` uses `stop_usd=STOP_USD` ($0.38). `replay_one` checks `if router.spent() >= stop_usd: return "stopped"`.
*   **Law Impact:** Complies with "No call starts once the ledger holds STOP_USD".
*   **Note:** The test `test_this_orders_stop_not_ruling_110s` verifies this. Correct.

**5. [P3] Ruling 110 Backwards Compatibility**
`replay_one` defaults: `keep_raw=False`, `names=None`, `prefix="replay110"`.
*   **Law Impact:** Complies with "ruling 110's behaviour is unchanged by the defaults".
*   **Note:** The test `test_an_out_of_contract_answers_text_is_kept_only_when_asked` verifies `raw_text` is absent when `keep_raw=False`. Correct.

**6. [P3] Table Arithmetic**
`valid-answer rate = (in_time + late) / (in_time + late + out_of_contract)`.
`agreement on valid answers = agree / total_units_in_valid_answers`.
*   **Law Impact:** Complies with the order's definition.
*   **Note:** The code in `scores` and `table` implements this correctly.

### Summary of Critical Issues

The primary blocker is the **System Prompt Mutation** in `FormatBackend`. The test asserts equality with production, but the code modifies the system prompt. This will cause the test suite to fail immediately.

P1_OR_WORSE: 1