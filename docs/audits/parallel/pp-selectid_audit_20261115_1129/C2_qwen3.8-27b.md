# qwen3.8-27b (qwen/qwen3.8-27b) 104 s finish=stop usage in 24007 / out 3422 usd_reported=0.005703 usd~0.123 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1129
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "consensus" voice) correctly identified that the P1s raised by GLM and Qwen were either non-defects or already fixed in the diff. However, looking at the *current* code provided in the prompt, I missed a subtle **P2** issue in `medley_trace` regarding the `went_on` logic that GLM hinted at but didn't fully resolve, and a **P3** issue in `hook_pass` regarding the `last_ts` initialization.

Specifically:
*   **GLM** correctly identified that the ordering of `elif` checks in `medley_trace` was the critical path. The fix in the diff (checking failures before ratings) is correct.
*   **Qwen** correctly verified the read-only compliance and the Heimdall-only constraint.
*   **I missed:** The interaction between `went_on` and the `pool` check in `medley_trace` (lines 153-155). If `went_on` is False, the code checks `mid in pool` and `pre.get("cleared") is not None`. This logic is fragile if `cleared` is `0` (falsy) vs `None`.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM [P1] (Cycle 1):** "medley_trace stage ordering... ratings beats second_pass".
    *   **Agree with the fix:** The diff now checks `second`, `trim_cut`, and `onset` failures *before* `ratings`. This is correct because `package.build` only writes ratings for moments that passed the previous gates. If a record is inconsistent (has both a failure and a rating), the failure is the true stop. The new test `test_a_failure_is_the_stop_even_beside_a_rating` (line 578) validates this.
*   **Qwen [P1] (Cycle 1):** "a moment that passed G17a but was not rated... should be stage 4".
    *   **Disagree with the defect, Agree with the fix:** The consensus correctly noted that "may open" (Stage 4) requires `can_open`, which includes more than just G17a. A moment that passes G17a but fails the opener rule stops at Stage 3 ("cannot open"). The code at line 151-152 handles this: `elif mid in onset: out[mid] = (3, "cannot open...")`. This is correct.
*   **GLM [P2] (Cycle 1):** "spotlight step-A detection matches the text of `out`".
    *   **Agree:** This is a P2. The code at line 177 uses `str(why).startswith("step A")`. This is brittle but acceptable for a diagnostic tool if the producer (`spotlight.build`) is stable. The consensus noted this is "code-written" and "the record's only encoding". I agree it's a P2, not a P1.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] F1 — `medley_trace`: `went_on` logic is fragile with `cleared=0`
**File:** `tests/package/hook112.py`, lines 125, 153-155.
```python
went_on = "second_pass" in pre                     # line 125
# ...
elif not went_on and mid in pool and pre.get("cleared") is not None and mid not in failed and \
        (pre.get("screened") or 0) > 0:            # line 153-154
    out[mid] = (2, "the medley ended at its 3-channel rule...", None)
```
If `pre["cleared"]` is `0` (an integer), `pre.get("cleared") is not None` is `True`. However, if the medley ended *before* any moments were cleared, `cleared` might be `0`. The condition `mid in pool` and `mid not in failed` would be true for moments that were screened but not cleared. The message says "fewer than 3 channels cleared step A". If `cleared` is 0, this is accurate. But if `cleared` is `None` (key missing), the condition fails, and the moment falls through to `elif mid in pool: out[mid] = (1, ...)`. This is correct behavior (it didn't even reach the 3-channel rule).
**However**, the variable name `went_on` is misleading. It checks for the *presence* of the `second_pass` key, not whether the medley actually *went on* to the second pass. If `second_pass` is an empty dict `{}`, `went_on` is `True`, but no moments passed. This is fine because the `elif mid in second` checks would fail for all moments, and they would fall through to the `pool` check.
**Verdict:** The logic is correct but the variable name `went_on` is a P3 nit. The condition `pre.get("cleared") is not None` is safe.

### [P2] F2 — `hook_pass`: `last_ts` initialization for the first event
**File:** `tests/package/hook112.py`, lines 340-349.
```python
last_ts = {}
for r in ev:
    # ...
    if has_calls:
        called = bool(db.execute("SELECT 1 FROM calls WHERE video_id = ? AND role IN ('hook', 'spotlight') "
                                 "AND ts > ? AND ts <= ? LIMIT 1",
                                 (r["video_id"], last_ts.get(r["video_id"], 0.0), r["ts"])).fetchone())
    # ...
    last_ts[r["video_id"]] = r["ts"]
```
For the first event of a given `video_id`, `last_ts.get(r["video_id"], 0.0)` returns `0.0`. The query checks for calls with `ts > 0.0 AND ts <= r["ts"]`. This is correct. It finds any call for that video up to the current event's timestamp.
**However**, if the `calls` table has a call with `ts = 0.0` (unlikely, but possible), it would be excluded. This is a P3 nit.

### [P1] F3 — `all_ratings`: `rsplit(":", 2)` on cache keys
**File:** `tests/package/hook112.py`, line 259.
```python
by_id[key.rsplit(":", 2)[0]].append((rater, rec))       # "<moment id>:<text sha>:<version>"
```
The comment says the key format is `<moment id>:<text sha>:<version>`. `rsplit(":", 2)` splits from the right, max 2 splits.
Example: `"abc123:sha456:v1"` -> `["abc123", "sha456", "v1"]`. `[0]` is `"abc123"`. Correct.
Example: `"abc:123:sha456:v1"` (if moment id contains a colon) -> `["abc:123", "sha456", "v1"]`. `[0]` is `"abc:123"`. Correct.
**However**, what if the moment id *does not* contain a colon, but the text sha or version does? The format is fixed by the producer. If the producer changes the format, this breaks. This is a P2 (brittle parsing), but the consensus noted it was fixed from `split(":")` to `rsplit(":", 2)`. I agree this is an improvement.

### [P1] F4 — `calibrate`: `router.spent()` check before each seed
**File:** `tests/package/hook112.py`, lines 425-429.
```python
for s in seeds:
    if router.spent() >= stop_usd:
        runs.append({"seed": s, "ratings": {}, "error": f"stopped: ${router.spent():.4f} spent (stop "
                                                        f"${stop_usd:.2f})"})
        continue
    got, err = rate(router, refs, ctx, wv, wf, cache=None, seed=s)
```
The check is `>= stop_usd`. If `spent` is exactly `0.25`, it stops. This is correct ("no call starts at or over the stop").
**However**, `rate` is called *after* the check. If `rate` makes a call that pushes `spent` over `stop_usd`, the next seed will stop. This is correct.
**But**, what if `rate` makes *multiple* calls? The `router` has its own `limit_usd` (0.30). The `stop_usd` is 0.25. If a single `rate` call costs 0.10, and `spent` was 0.20, it becomes 0.30. The next seed stops. This is correct.
**Verdict:** No defect.

### [P2] F5 — `ref_moments`: `seg.get("approved_text") or seg.get("text") or ""`
**File:** `tests/package/hook112.py`, line 390.
If `approved_text` is an empty string `""`, `or` moves to `text`. If `text` is also `""`, it becomes `""`. This is correct.
**However**, if `approved_text` is `None`, `or` moves to `text`. This is correct.
**Verdict:** No defect.

### [P1] F6 — `main`: `recs[-1][2].get("moments")`
**File:** `tests/package/hook112.py`, line 489.
```python
today = sorted({m.get("video_id") for m in (recs[-1][2].get("moments") or [])} if recs else set())
```
If `recs` is empty, `today` is `set()`. Correct.
If `recs` is not empty, it takes the *last* build's moments. This is used for `hook_pass`'s `videos` parameter. The docstring says "the given videos' events". Using the last build's moments is a heuristic for "today's videos". This is acceptable for a diagnostic tool.

### [P2] F7 — `test_hook112.py`: `test_the_hook_pass_own_calls_decide_whether_a_model_was_called`
**File:** `tests/package/test_hook112.py`, lines 683-694.
The test creates a `calls` table with:
1. `bl` (video_id) at `ts=90.0`, role `hook`.
2. `v2` (video_id) at `ts=205.0`, role `mine`.
The events are:
1. `bl` at `ts=100.0`.
2. `v1` at `ts=200.0`.
3. `v2` at `ts=210.0`.
4. `old` at `ts=1.0` (outside window).

For `bl` (event ts=100.0): `last_ts` is 0.0. Query: `ts > 0.0 AND ts <= 100.0`. Call at 90.0 matches. `called=True`.
For `v1` (event ts=200.0): `last_ts` is 0.0. Query: `ts > 0.0 AND ts <= 200.0`. No calls for `v1`. `called=False`.
For `v2` (event ts=210.0): `last_ts` is 0.0. Query: `ts > 0.0 AND ts <= 210.0`. Call at 205.0 matches, but role is `mine`, not `hook` or `spotlight`. `called=False`.

The test asserts:
```python
self.assertEqual(hp["classes"], {"0 rows, a model called": 1, "wrote rows, no model call": 1,
                                 "0 rows, no model call": 1})
```
- `bl`: 0 rows, called -> "0 rows, a model called" (1)
- `v1`: 2 rows, not called -> "wrote rows, no model call" (1)
- `v2`: 0 rows, not called -> "0 rows, no model call" (1)
This matches. The test is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `medley_trace` | P1 (ordering) | P2 (naming) | Ordering fixed. `went_on` name is misleading but logic is correct. |
| `spotlight_trace` | P2 (string match) | P2 (string match) | No change. Brittle but acceptable. |
| `hook_pass` | P2 (heuristic) | P2 (heuristic) | No change. `calls` table logic is correct. |
| `calibrate` | P1 (stop) | P3 (nit) | Stop logic is correct. |
| `all_ratings` | P2 (rsplit) | P2 (rsplit) | No change. Brittle but correct for current format. |
| `tests` | P1 (coverage) | P2 (coverage) | Tests cover the fixed issues. |

## 5. FINAL PRIORITY LIST

1.  **[P2]** `tests/package/hook112.py:125` — Rename `went_on` to `has_second_pass` or similar to avoid confusion.
2.  **[P2]** `tests/package/hook112.py:177` — Add a comment citing the exact line in `spotlight.build` that writes "step A: ..." to make the string match less brittle.
3.  **[P3]** `tests/package/hook112.py:259` — Add a comment that the cache key format is `<moment id>:<text sha>:<version>` and that `rsplit` is used because moment ids may contain colons.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fix to `medley_trace` to check failures before ratings is the most critical change, as it ensures the funnel counts are accurate even if the build records are inconsistent.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1.  The `spotlight.build` producer must not change the wording of "step A: ..." without updating `hook112.py`.
2.  The cache key format in `HOOK_CACHE.json` must remain `<moment id>:<text sha>:<version>`.

P1_OR_WORSE: 0