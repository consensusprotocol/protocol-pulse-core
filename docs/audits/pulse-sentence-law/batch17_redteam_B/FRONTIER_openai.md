# gpt-6.1-sol (97 s) usage={'prompt_tokens': 6211, 'completion_tokens': 3960, 'total_tokens': 10171, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 6208, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 3072, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

### 1. Medium — `NaN` passes numeric validation and becomes a rating

**Evidence:** `pipeline/story_semantics.py:407–408` accepts every `float`; the bounds check at **415** only tests:
> `(lo is not None and v < lo) or (hi is not None and v > hi)`

Both comparisons are false for `float("nan")`. Consequently, `_v_rate` accepts a NaN score at **868**, and `rate_passages` stores it at **893**:
> `out[pid] = (float(x["score"]), str(x.get("reason", "")), x["fault"])`

The confidence validator at **628** has the same hole.

**Impact:** A non-finite value survives the schema boundary and becomes a returned rating. Whether the JSON decoder admits `NaN` is not shown in this diff; the validator demonstrably accepts an already-decoded NaN.

**Fix:** Reject non-finite floats before checking bounds. Add regression cases for NaN scores and confidence, including the actual decoding/retry path.

### 2. Medium — Malformed rating entries raise `AttributeError`, not the promised validation failure

**Evidence:** `pipeline/story_semantics.py:867` accesses an entry before validating that it is an object:
> `isinstance((x or {}).get("id"), str)`

For `{"ratings": [1]}` or `{"ratings": ["bad"]}`, this raises `AttributeError`. It bypasses `_field`’s object check at **404–405**, which would raise `ValueError`.

The visible caller catches only `LLMParseError` at **886–887**.

**Impact:** This validator does not consistently deliver its documented failure type for mistyped model data. Whether `LocalLLM.chat_json` catches and converts `AttributeError` is not visible, so a caller crash versus a retried failure cannot be established from this diff.

**Fix:** Check that every rating entry is a dictionary before calling `.get`; raise `ValueError` otherwise. Test these cases through `ScriptedLLM.chat_json`, asserting retries and final `LLMParseError`.

### 3. Medium — ID normalization disagrees between validation and output

**Evidence:** `pipeline/story_semantics.py:883` normalizes passage IDs:
> `ids = {str(p["pid"]) for p in passages}`

But **889** builds the output filter without normalization:
> `valid = {p["pid"] for p in passages}`

Then **891–892** compares a normalized string against that unnormalized set:
> `pid = str(x["id"])`  
> `if pid in valid:`

**Impact:** With passage ID `1`, a reply rating ID `1` or `"1"` passes validation but is silently discarded; the function returns no rating and no error. This is a verified function-level inconsistency. Whether production passage generation can produce integer IDs is not shown.

**Fix:** Normalize IDs consistently—preferably reuse `ids` as the output membership set. Add a test covering integer passage IDs and a validated reply.

### 4. Low — Two rating fakes still bypass validation

**Evidence:** Both methods accept `validate` but immediately return their reply without invoking it:

- `pipeline/test_editorial_robust.py:231–233`
- `pipeline/test_window_review.py:138–140`

For example:
> `return {"ratings": [{"id": i, "score": self.score, "fault": "none", ...`

**Impact:** These tests still do not exercise the real schema boundary. Adding `"fault": "none"` fixes the fixtures’ shape but does not make their behavior match the validating fake introduced elsewhere in this diff. They can pass even when their returned replies would fail real validation.

**Fix:** Build the reply, invoke `validate(reply)` when supplied, then return it. Separately test retry/exhaustion with the real `chat_json` implementation.

The cache-read implementation, complete prompts, and downstream counting/production gates are absent from the supplied diff; their claimed behavior cannot be verified here.