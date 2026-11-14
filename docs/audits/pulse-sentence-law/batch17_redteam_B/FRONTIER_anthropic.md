# claude-fable-5-2 (130 s) usage={'input_tokens': 9627, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 13365, 'output_tokens_details': {'thinking_tokens': 10349}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

Line numbers are computed from the hunk headers (±1). `LocalLLM.chat_json`, the cache code, the prompt bodies and the callers are not in the diff; where a finding depends on them I say so.

## F1 — HIGH (conditional): cached-reply re-validation is claimed but not in the diff, and the fallbacks that tolerated old replies are gone

- **Evidence:** the order says "Cached replies are re-validated on read". No hunk touches `chat_json` or any cache code, and no test covers it.
- **Removed safety net:**
  - `story_semantics.py:694` reads `s["same_actor_action_object"]` (was `.get`).
  - `:893` is `out[pid] = (float(x["score"]), str(x.get("reason", "")), x["fault"])`; the clamp, the `"unspecified"` fallback and the `try/except` are deleted.
- **Impact if a cache hit bypasses `validate`:**
  - A pre-batch cached `{"support": "SUPPORTS", "reason": ...}` raises KeyError in `verify_support`.
  - A cached rating without `fault` raises KeyError in `rate_passages`.
  - A cached `score: 9` becomes a counted 9.0 rating.
- **Uncertainty:** this may already hold in `chat_json`; I cannot confirm it from the diff.
- **Fix:** show the cache-read path calling `validate`. Add a test that seeds the cache with a pre-batch reply and asserts a re-ask.

## F2 — HIGH: `_v_rate` raises AttributeError, not ValueError, on a non-dict rating element

- **Evidence:** `story_semantics.py:867` `pid = str(_field(x, "id", "str") if isinstance((x or {}).get("id"), str) else _field(x, "id", "int"))`.
- **Failure:** for `{"ratings": ["p0"]}`, `{"ratings": [5]}` or `{"ratings": [["p0", 5]]}`, `(x or {}).get` raises AttributeError before `_field`'s dict guard runs.
- **Impact:** `rate_passages` catches only `LLMParseError` (`:886`). Unless `chat_json` converts every exception type from `validate` into a retry (not shown), this is a crash, not a failed call.
- **Fix:** put `if not isinstance(x, dict): raise ValueError(...)` first in the loop.
- **Related, same function:** `ids = {str(p["pid"]) ...}` (`:883`) but `valid = {p["pid"] ...}` (`:889`). With a non-str pid, validation passes, every rating is dropped at `:892`, and `{}, None` is returned with no error recorded. Use `ids` for both, or delete the now-redundant `if pid in valid`.

## F3 — MEDIUM: NaN passes every range check

- **Evidence:** `story_semantics.py:415` `if (lo is not None and v < lo) or (hi is not None and v > hi)`. Both comparisons are False for `float("nan")`, and `"num": type(v) in (int, float)` (`:408`) admits it.
- **Impact:** `{"score": NaN}` passes `lo=1, hi=5` and `:893` stores `float("nan")` as a rating; `confidence: NaN` passes `_v_adj` (`:628`). Any downstream mean, max or sort is then poisoned.
- **Uncertainty:** Python's `json.loads` accepts the bare `NaN` literal by default; whether `chat_json` parses that way is not shown.
- **Fix:** reject with `math.isfinite(v)` for `num`, or write the check as `not (lo <= v <= hi)`.

## F4 — MEDIUM: "must carry" validators accept empty or meaningless evidence

- **`_v_label`:** `:793` `_str_list(o, "member_chunk_ids")` accepts `[]` and `[""]`. The docstring and order say a specific event "must carry ... member ids".
- **`_v_adj`:** `:626-627` accept `{"verdict": "CURRENT_EVENT", "supporting_chunk_ids": [], "evidence_quote": ""}`. Nothing is conditional on a positive verdict, unlike `_v_label`.
- **`event_date`:** `:431` and `:790` accept any non-empty string (`"unknown"`, `"n/a"`), though the docstring says this field feeds currentness.
- **Uncertainty:** whether callers fail closed on these is not visible.
- **Fix:**
  - Require a non-empty list of non-empty strings for `member_chunk_ids`.
  - Require the same for `supporting_chunk_ids`, plus a non-empty `evidence_quote`, when the verdict is positive.
  - Parse `event_date`, or enumerate the allowed sentinel.

## F5 — MEDIUM: strictness beyond the decision fields creates needless failed calls

Each of these fails the whole call; for ratings that means the whole story.

- **Case-sensitive enum:** `:640` `allowed=SUPPORT_PRESENTED` is exact-case. The deleted code was `str(s.get("presented_as", "")).lower() == "past"`, so `"Current"` or `"Past"` now fails. The same applies to `event_recency` (`:432`) and `fault` (`:869`).
- **Integral floats:** `:429-430` use `"int"` (`type(v) is int`), so `5.0` is rejected. The old `int(o[...])` accepted it, and the order only excludes bool and string.
- **Null aliases:** `:436` `isinstance(e.get("aliases", []), list)` allows a missing `aliases` but rejects `"aliases": null`.
- **`reason` required:** `:629`, `:641` and `:677` require a `reason` string, though no decision reads it. Omitting it turns a correct TOPIC_ONLY or NEW_SUBJECT into a failed call.
- **One bad `fault`:** `:869` now discards every rating for the story on a single off-list `fault`. It was previously mapped to `"unspecified"` for that passage only.
- **Uncertainty:** the prompt enumerations are not in the diff (CLIP_PROMPT is truncated at `"fault": one o`), so I cannot confirm that the three hard-coded tuples match the prompts.
- **Fix:**
  - Strip and lowercase enum strings before checking.
  - Accept floats where `v == int(v)`.
  - Treat a null `aliases` as `[]`.
  - Make `reason` optional (`str` or absent).

## F6 — MEDIUM: tests do not test what they claim

- **Bool case not isolated:** `test_editorial_robust.py:296` `(sm._v_derive, {"underlying_event": "x", "bitcoin_relevance": True, "importance": 3})  # bool int`. The dict also lacks `event_date` and the rest. If `type(v) is int` regressed to `isinstance`, it would still raise, so the test cannot detect the regression.
- **Label case not isolated:** `:297` `{"is_specific_event": True, "headline": "h"}  # quote / ids missing` raises on `event_date` first. The quote and ids checks are never reached.
- **Fakes that ignore `validate`:** the order says fakes "validate them like the real call", but three do not:
  - `Rater.chat_json` (`test_editorial_robust.py:232`);
  - the rater in `test_window_review.py:139`;
  - `RoutedLLM` (`test_window_review.py:334-344`).
- **Wrong exception type:** `FakeLLM._ok` (`~:408`) and `One.chat_json` raise bare `ValueError`, not `LLMParseError`, despite the docstring "The real chat_json contract". No test drives a schema-invalid reply through a caller to INCONCLUSIVE, not counted or not producible.
- **Missing-field path untested:** `test_supports_needs_both_deciding_fields_exactly` never sends a missing field through `verify_support`. With the validator in place, the `is not True` branch is only reachable with `False`, which the old `is False` code already handled.
- **No coverage** for a non-dict rating item, a duplicate id, NaN, or cache re-validation.
- **Fix:**
  - Use one-defect-per-case fixtures built from a valid base.
  - Run the invalid replies through `ScriptedLLM` and the real callers.
  - Make every fake call `validate`.

## Not verifiable from the diff

- Whether `"INCONCLUSIVE"` (`:699`) is a value every `verify_support` caller handles as a non-pass.
- Whether 1200 `max_tokens` (`:885`) is enough now that one truncated rating fails the whole set.
- Whether any existing test sets `FakeLLM.model_date` or `model_recency` to a value `_v_derive` now rejects.