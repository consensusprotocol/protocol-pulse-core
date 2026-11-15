# qwen3.8-27b (qwen/qwen3.8-27b) 106 s finish=stop usage in 6329 / out 4867 usd_reported=0.003764 usd~0.092 (upper-bound price)

I will analyze the provided diff and context against the governing laws and the specific questions asked.

### Context Analysis
**Feature:** `pp-selectid` (Ruling 109).
**Goal:** Enforce "free gates first" in `pipeline/spotlight.py`. If a moment's `ALONE` score is *already known* to be below `ALONE_MIN` (4.0), it must be stopped *before* any paid verdicts (Step A, hook rating, etc.) are requested.
**Constraint:** Moments with *unknown* scores (None) must proceed to paid stages, where they will be evaluated later (Stage 7).
**Law Compliance:**
- **M12 FAIL CLOSED:** The code stops moments with known low scores. It does not pass them. It does not stop unknown scores (which is correct, as they are not "known low").
- **LAW 20:** Thresholds are constants (`ALONE_MIN`).
- **Smallest Diff:** The change is localized to `build()` in `spotlight.py` and tests.

### Code Review

#### 1. Logic in `pipeline/spotlight.py`

```python
ms = [P.with_verdict(m, idx) for m in ms]
low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}
for mid, sc in low.items():                  # RULING 109 ...
    stop(mid, f"the ALONE scorer: {sc} (needs {ALONE_MIN:g}), a free gate before any paid verdict (ruling 109)")
ms = [m for m in ms if m["moment_id"] not in low]   # verdict only for what every free gate passed...
out["ruling_109"] = {"alone_known_below_min": len(low)}
if not ms:
    out["why_none"] = "every moment's ALONE score is known below the minimum: no paid verdict (ruling 109)"
    return out
```

**Analysis:**
- `alone_score(m)` is called. The prompt states: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
- The filter `if alone_score(m) is not None and alone_score(m) < ALONE_MIN` correctly identifies moments with a *known* low score.
- Moments with `None` score are excluded from `low`, thus remain in `ms` and proceed to `P.prescreen` (paid step A).
- The `stop` function is called for each low moment. Assuming `stop` marks the moment as failed/stopped in the output structure (standard pattern in this codebase based on context), this prevents them from being processed further.
- The list comprehension `ms = [m for m in ms if m["moment_id"] not in low]` removes the stopped moments from the list passed to `P.prescreen`. This ensures no paid calls are made for them.
- The early return `if not ms` handles the case where *all* moments are stopped.

**Potential Issue 1: `stop` side effects.**
Does `stop(mid, ...)` modify `m` in place or just record the stop? If `stop` only records the reason in `out["moments"][mid]["out"]` or similar, the removal from `ms` is necessary to prevent `P.prescreen` from seeing them. The code does remove them from `ms`. This looks correct.

**Potential Issue 2: `alone_score` stability.**
The prompt asks: "Can the early stop drop a moment that could still seal (a score that changes within the build...)?".
The prompt states: "UNCHANGED GUARDS: stage 7 still requires ALONE >= ALONE_MIN ... so the earlier stop can never let through a moment the later stage would refuse".
It also states: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
If the text doesn't change, the score doesn't change. The "current text" is fixed at this point in the pipeline (post-transcription/selection). Therefore, a known low score will remain low. The early stop is safe.

**Potential Issue 3: Unscored moments.**
"Is an unscored moment ever stopped?"
The condition `alone_score(m) is not None` ensures that only moments with a score are considered for the `low` set. Unscored moments (`None`) are not in `low`, so they are not stopped by this block. They proceed to `P.prescreen`. This is the intended behavior ("a moment with NO score yet goes on, as before").

#### 2. Tests in `tests/package/test_spotlight.py`

**Test 1: `test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict`**
```python
ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
      moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
out, calls = self.run_build(ms, {"a": 5, "b": 5, "c": 5}, alone=[3.0, 4.0, None])
self.assertEqual(calls.get("prescreen"), ["b", "c"])                       # "a" was never asked
self.assertIn("ruling 109", out["moments"]["a"]["out"])
self.assertEqual(out["ruling_109"], {"alone_known_below_min": 1})
```
- `alone=[3.0, 4.0, None]` maps to `a`, `b`, `c`.
- `a` (3.0) is `< 4.0` and `not None`. It should be stopped.
- `b` (4.0) is `not < 4.0`. It should proceed.
- `c` (None) is `None`. It should proceed.
- `calls.get("prescreen")` should be `["b", "c"]`.
- The test asserts this.
- The test also checks `out["moments"]["a"]["out"]` contains "ruling 109". This depends on how `stop` writes to the output. Given the diff shows `stop(mid, f"... (ruling 109)")`, and standard patterns, this is likely correct.
- The second part of the test:
```python
out, calls = self.run_build([moment(mid="a", channel="A")], {"a": 5}, alone=[2.0])
self.assertNotIn("prescreen", calls)                                        # nothing paid at all
self.assertIn("ruling 109", out["why_none"])
```
- Single moment `a` with score 2.0.
- `low` will contain `a`.
- `ms` becomes empty.
- `out["why_none"]` is set.
- `P.prescreen` is not called.
- This logic holds.

**Test 2: Modified `TestRuling94And95`**
```python
for alone, sealed, why in ((3.0, False, "ruling 109"),              # a verdict below 4: refused by the free
                           (None, False, "ALONE scorer: no rating"),  # gate before any paid verdict (ruling
                           (4.0, True, None)):                          # 109); none yet: deferred, then refused
```
- Previously, `3.0` might have been refused by a different rule (opener rule or stage 7). Now it is refused by "ruling 109".
- The test updates the expected `why` string. This is consistent with the code change.

**Test 3: `TestBuild` helper modification**
```python
def prescreen(router, ms_, *a, **k):
    calls.setdefault("prescreen", []).extend(m["moment_id"] for m in ms_)      # ruling 109: who reaches step A
    return ...
```
- This records which moments reach the paid stage. Essential for verifying the "free gates first" logic.

### Findings

**[P2] Potential Ambiguity in `stop` Output Location**
The test asserts `self.assertIn("ruling 109", out["moments"]["a"]["out"])`.
The code calls `stop(mid, f"... (ruling 109)")`.
If `stop` writes to `out["moments"][mid]["out"]`, this is fine. If `stop` writes to a different key (e.g., `out["moments"][mid]["reason"]` or `out["stops"]`), the test will fail.
However, looking at the existing test `TestRuling94And95`, it checks `why` which is likely derived from the stop reason. The new test explicitly checks `out["moments"]["a"]["out"]`.
Given that `stop` is a standard utility in this pipeline (implied by its use in other contexts like "no verdicts file given"), it is highly probable that it appends to the moment's output/reason field.
*Self-Correction:* The prompt says "stop(mid, ...)". In many Python pipelines, `stop` might just mark the item as failed. The test `self.assertIn("ruling 109", out["moments"]["a"]["out"])` suggests the reason string is stored in `out`. If `stop` does *not* write to `out["moments"][mid]["out"]`, this is a bug.
Let's look at the diff again.
`stop(mid, f"the ALONE scorer: {sc} (needs {ALONE_MIN:g}), a free gate before any paid verdict (ruling 109)")`
If `stop` is a function that modifies the global `out` dictionary or returns a modified moment, the test relies on that behavior.
Since I cannot see the definition of `stop`, I must assume it behaves as expected by the test. If `stop` is a no-op or writes elsewhere, the test fails.
*Assumption:* `stop` writes the reason to the moment's record in `out`. This is a standard pattern.
*Severity:* If `stop` doesn't do this, it's a P1. But given the test is part of the PR, the author likely verified this. I will flag it as a P2 "Verify `stop` implementation writes to `out['moments'][mid]['out']`" just to be safe, but it's likely correct.

**[P3] Nit: `ALONE_MIN:g` formatting**
`f"... (needs {ALONE_MIN:g}) ..."`
If `ALONE_MIN` is `4.0`, `:g` formats it as `4`.
The test expects `"ruling 109"` in the string. It does not check the number format.
This is fine.

**[P1] Logic Gap: `alone_score` Calculation Cost**
The code calls `alone_score(m)` for *every* moment in the list comprehension to build `low`.
`low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}`
This calls `alone_score(m)` **twice** for each moment that is not None (once for the `if` check, once for the value).
If `alone_score` is expensive (e.g., involves a model call or complex calculation), this is inefficient.
However, the prompt says "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
If `P.verdict_of` is a simple dictionary lookup or attribute access, the cost is negligible.
If it involves re-computation, it's a P2.
Given "free gates", it's likely a cheap check.
*Refinement:* The double call is a code smell.
`scores = {m["moment_id"]: alone_score(m) for m in ms}`
`low = {mid: sc for mid, sc in scores.items() if sc is not None and sc < ALONE_MIN}`
This is cleaner and avoids double evaluation.
*Severity:* P2 (Efficiency/Code Quality).

**[P0] Check: Does `stop` actually prevent `P.prescreen` from seeing the moment?**
The code does:
1. `low` = set of IDs to stop.
2. `stop(mid, ...)` for each in `low`.
3. `ms = [m for m in ms if m["moment_id"] not in low]`.
4. `P.prescreen(router, ms, ...)` is called with the filtered `ms`.
So, `P.prescreen` never sees the stopped moments. This is correct.

**[P1] Check: What if `alone_score` returns a value that is *exactly* `ALONE_MIN`?**
Condition: `alone_score(m) < ALONE_MIN`.
If score is 4.0 and `ALONE_MIN` is 4.0, `4.0 < 4.0` is False.
The moment is NOT stopped.
It proceeds to `P.prescreen`.
Later, Stage 7 requires `ALONE >= ALONE_MIN`.
So a 4.0 passes Stage 7.
This is consistent. The "free gate" stops *below* the minimum. The "paid gate" (Stage 7) enforces *at or above*.
Wait, the prompt says: "stage 7 still requires ALONE >= ALONE_MIN".
So 4.0 is valid.
The early stop is for `< 4.0`.
This logic is sound.

**[P1] Check: What if `alone_score` is `None`?**
Condition: `alone_score(m) is not None`.
If `None`, it is not in `low`.
It proceeds to `P.prescreen`.
Stage 7 will handle it (likely waiting for the scorer or failing if no score is available by then).
The prompt says: "a moment with NO score yet goes on, as before: stage 7 waits for the scorer."
This is consistent.

**[P2] Test Coverage: `out["ruling_109"]` count**
The test checks `out["ruling_109"] == {"alone_known_below_min": 1}`.
The code sets `out["ruling_109"] = {"alone_known_below_min": len(low)}`.
This is correct.

**[P3] Nit: Variable Name `low`**
`low` is a dictionary of `moment_id: score`.
The name is slightly ambiguous (is it the list of low moments, or the scores?).
`low_scores` or `stopped_moments` might be clearer.
Minor.

**[P1] Critical Check: `stop` function behavior**
If `stop` raises an exception or modifies `ms` in place, the subsequent list comprehension `ms = [m for m in ms if ...]` might behave unexpectedly.
However, `stop` is called *before* the list comprehension.
If `stop` modifies the moment object `m` in `ms` (e.g., sets `m["status"] = "stopped"`), the list comprehension filters by `moment_id not in low`.
This relies on `low` containing the correct IDs.
`low` is built from `ms` *before* `stop` is called.
So `low` is stable.
The filtering is based on `low`, not on the state of `m`.
So even if `stop` modifies `m`, the filtering works correctly.

**[P2] Potential Issue: `P.with_verdict`**
`ms = [P.with_verdict(m, idx) for m in ms]`
This attaches the verdict.
Then `alone_score(m)` is called.
Does `alone_score` depend on the verdict attached by `P.with_verdict`?
The prompt says: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
If `P.with_verdict` is what makes `P.verdict_of` available, then the order is correct.
If `alone_score` reads from a different source that is *not* updated by `P.with_verdict`, it might read stale data.
But `P.with_verdict` is standard for attaching the current state.
Assuming `alone_score` uses the attached verdict, this is correct.

**[P1] Law 20 / M12 Compliance**
The change enforces a hard stop for known low scores.
It does not change the threshold.
It does not allow a low score to pass.
It fails closed (stops the moment).
Compliant.

**[P2] Question 1: "Can the early stop drop a moment that could still seal?"**
Answer: No.
Reason: The score is based on the "current text". The text does not change after this point in the pipeline (selection is locked). The score is deterministic for the given text. If it is low now, it will be low in Stage 7.
The only exception is if `alone_score` is non-deterministic (e.g., random), which is unlikely for a "scorer".
Or if the text *does* change (e.g., snapping).
The prompt mentions "snapped span rated differently".
If snapping changes the text, does `alone_score` re-evaluate?
The prompt says: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
If the text changes due to snapping *after* this check, the score might be different.
However, `P.with_verdict` is called *before* the check.
Does snapping happen *before* or *after* `build()`?
In the pipeline, `build()` is likely the selection/assembly phase.
Snapping (cutting) usually happens *after* selection, during rendering or pre-rendering.
If snapping happens *after* `build()`, then the text used for `alone_score` is the pre-snap text.
If the snap changes the words, the score might change.
BUT, the prompt says: "SELECTION LOCK: the words a clip must contain are fixed at selection time".
And "SNAP LIMIT: a cut may move only inside the heard gap... it may never add or drop a word."
So the *words* are the same. The *timing* changes.
Does `alone_score` depend on timing?
"ALONE scorer" likely evaluates the *content* (stand-alone-ness) of the text.
If the words are the same, the score should be the same.
Therefore, the early stop is safe.

**[P2] Question 2: "Is an unscored moment ever stopped?"**
Answer: No.
Reason: The condition `alone_score(m) is not None` explicitly excludes unscored moments from the `low` set.

**[P2] Question 3: "Do the tests pin it?"**
Answer: Yes.
`test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict` pins the behavior for known low, known high, and unscored moments.
It verifies that `prescreen` is only called for the high/unscored ones.

### Final Findings List

1.  **[P2] Double Evaluation of `alone_score`**: The list comprehension for `low` calls `alone_score(m)` twice for each moment that has a score. While likely cheap, it is inefficient and poor style.
    *   *Fix:* Compute scores once into a dict, then filter.
2.  **[P3] Nit: Variable Naming**: `low` is a dict of scores, not a list of moments. `low_scores` is clearer.
3.  **[P2] Verification of `stop` Output**: The test asserts the reason is in `out["moments"]["a"]["out"]`. This relies on the implementation of `stop`. If `stop` writes to a different field, the test fails. This is a standard pattern, but worth noting as a dependency.
4.  **[P1] No Critical Defects Found**: The logic correctly implements Ruling 109. It stops known low scores before paid calls. It allows unknown scores to proceed. It handles the empty list case. It complies with the laws.

Wait, let me double check the "P1" severity.
Is there any scenario where a moment with a known low score *should* proceed?
No, Ruling 109 says "free gates first... a paid verdict is asked only of a moment every free gate has passed".
ALONE >= 4 is a free gate.
So stopping it is correct.

Is there any scenario where a moment with an unknown score is *incorrectly* stopped?
No, the condition `is not None` prevents this.

Is there any scenario where a moment with a known high score is *incorrectly* stopped?
No, the condition `< ALONE_MIN` prevents this.

The logic is sound.

One subtle point:
`ms = [P.with_verdict(m, idx) for m in ms]`
`low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}`

If `P.with_verdict` modifies `m` in place, and `alone_score` reads from `m`, this is fine.
If `P.with_verdict` returns a *new* object, and `ms` is updated to contain the new objects, this is fine.
The code uses `ms = [ ... ]`, so `ms` is reassigned to the list of new/modified objects.
Then `low` is built from the new `ms`.
Then `stop` is called on the IDs in `low`.
Then `ms` is filtered.
This sequence is correct.

**Conclusion:**
The code is correct.
The only issues are minor efficiency/style (P2/P3).

P1_OR_WORSE: 0