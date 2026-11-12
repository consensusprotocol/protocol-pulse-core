# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
Yes for the functions changed. `_field` (lines 17-42) and `_str_list` (45-49) implement the exact type/enum/range/optional rules stated in their docstrings and the red-team comments. All `_v_*` validators (55-78, 85-94, 100-109, 116-121, 146-156, 170-184) now call them and enforce the documented invariants (e.g., positive verdict requires non-empty lists, integral floats become int, NaN/inf rejected). No silent exception paths; every failure raises `ValueError`. No audio/time/index logic, no clip movement, no gate thresholds appear in this diff.

**Q2: LAW COMPLIANCE**  
COMPLIANT (lines 55-78, 85-94, 100-109, 146-156, 170-184). The stricter validators directly support L-f, L-i, L-k and the “fail closed / red-team B” requirements by making missing or mistyped deciding fields a hard failure. No change to sentence_law, EDL locks, cut movement, edge-word rules, or any gate threshold. No path that recomputes first/last words after selection or loosens v2f behaviour.

**Q3: TESTS**  
Tests prove the claim. `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call` (267-313) enumerates one defect per case and asserts `ValueError`. `test_harmless_variations_are_accepted` (315-324) and the updated `FakeLLM._ok` (392-401) confirm that only validated replies are returned. All must-fail fixtures now supply complete objects that the new validators accept; the defect cases are rejected. No vacuous assertions.

**Q4: VERDICT**  
No defects.  
READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `_field` (lines 17-42):** 
   - The function checks the type of a field in a JSON object, ensuring it matches the expected type, is within allowed values, and is within a specified range if applicable. It correctly handles optional fields and raises a `ValueError` for violations. The use of `type()` instead of `isinstance()` for integers is correct to avoid accepting booleans as integers (line 31).
   - The function appears to do what its docstring claims, with no evident off-by-one errors or silent exceptions. It does not seem to allow a pass when data is missing, except for optional fields.

2. **Function `_str_list` (lines 45-49):**
   - This function ensures that a specified key in a JSON object is a list of strings, optionally non-empty. It raises a `ValueError` if the condition is not met.
   - The function behaves as described, with no evident issues.

3. **Function `_v_derive` (lines 55-78):**
   - This function validates various fields in a JSON object related to an event's metadata. It checks for correct types, non-empty strings, and valid date formats.
   - The function performs as expected, with no evident issues.

4. **Function `_v_adj` (lines 85-94):**
   - Validates a verdict and its supporting evidence. It ensures that a positive verdict has associated evidence and a quote.
   - The function appears to work correctly, with no evident issues.

5. **Function `_v_sup` (lines 100-109):**
   - Validates support fields, ensuring they are correctly typed and within allowed values.
   - The function performs as expected, with no evident issues.

6. **Function `_v_rate` (lines 170-184):**
   - Validates ratings for passages, ensuring scores are within 1-5, faults are known, and all passage IDs are rated.
   - The function behaves correctly, with no evident issues.

7. **Function `rate_passages` (lines 187-214):**
   - Rates passages using an LLM, ensuring all passages are rated and handling errors appropriately.
   - The function appears to work correctly, with no evident issues.

Overall, the functions seem to perform their intended tasks correctly, with no off-by-one errors or silent exceptions. There are no evident paths that would produce a pass when data is missing or a model failed.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT - The changes ensure that sentence boundaries are respected and validated (lines 170-184).

2. **SELECTION LOCK:** COMPLIANT - No changes allow recomputation of expected words after selection.

3. **SNAP LIMIT:** COMPLIANT - No changes allow cuts to move outside the locked sentence's silence.

4. **NEIGHBOUR:** COMPLIANT - No changes affect the handling of neighboring words.

5. **ONSET/TAIL:** COMPLIANT - No changes affect the onset or tail handling of clips.

6. **CREDITS:** COMPLIANT - No changes affect the handling of credits.

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT - No changes affect sign-off names.

8. **L-b EDGE WORDS WHOLE:** COMPLIANT - No changes affect edge word handling.

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT - No changes affect dissent handling.

10. **L-d PROTECTED PREVIEW:** COMPLIANT - No changes affect the protected preview.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT - No changes affect punctuation handling.

12. **L-f CHANNELS FIRST:** COMPLIANT - No changes affect channel handling.

13. **L-g WRITTEN FORMS:** COMPLIANT - No changes affect written form handling.

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT - No changes affect text reading.

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT - No changes affect event claims.

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT - No changes affect release authorization.

17. **L-k ONE CANONICAL FORM:** COMPLIANT - No changes affect canonical form handling.

18. **LAW 20 / M2:** COMPLIANT - No changes affect gate thresholds.

19. **M12 FAIL CLOSED:** COMPLIANT - No changes allow passing when data is missing.

20. **LAW 22:** COMPLIANT - No changes affect the v2f reference path.

### Q3: TESTS

- The tests appear to cover various scenarios, including edge cases and validation failures. 
- The test `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call` (lines 267-313) ensures that missing or incorrect fields result in a failure, which aligns with the compliance requirements.
- The test `test_harmless_variations_are_accepted` (lines 315-325) confirms that acceptable variations do not cause failures.
- The tests seem to prove the claims, with no assertions that could pass vacuously.

### Q4: VERDICT

- **SEVERITY:** None
- **Diff Line:** N/A
- **Issue:** N/A
- **Fix:** N/A

**READY** - The code changes are compliant with the laws, correctly implemented, and adequately tested.

## GEMINI — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

Yes, the changed functions appear to do what their docstrings and the governing laws describe. The primary change is the introduction of strict, centralized validation for all LLM responses, which significantly enhances the robustness of the data processing pipeline.

-   **`_field` function (lines 17-43):** This new helper function is a robust validator. It correctly uses `type(v) is int` (line 32) to distinguish integers from booleans, which `isinstance(True, int)` would incorrectly conflate. It also correctly handles floating-point numbers that are integers (e.g., `5.0` is converted to `5`), checks for finiteness to reject `NaN`/`inf` (line 33), and enforces ranges, allowed values, and non-empty constraints. This is a solid, well-designed utility.
-   **Removal of Silent Exceptions:** A critical correctness improvement is in `rate_passages`. The previous version contained a `try...except Exception: pass` block (old lines 207-208), which would silently discard any malformed rating from the LLM. The new implementation (lines 209-214) has no such dangerous pattern. Instead, it relies on a `validate` function passed to `llm.chat_json` (line 195) which fails loudly on any invalid data, preventing it from ever reaching the processing logic.
-   **Fail-Closed Logic:** The changes consistently enforce a "fail-closed" approach (Law M12). For example, in `verify_support`, the condition `s.get("same_actor_action_object") is False` is changed to `s["same_actor_action_object"] is not True` (line 134). This is a crucial fix: if the key was missing, the old logic would not downgrade the verdict, while the new logic correctly does, preventing a pass on incomplete data. Similarly, `_v_adj` (lines 88-92) now requires positive verdicts to be accompanied by non-empty evidence fields.

I did not find any off-by-one errors, incorrect units, or state leakage in the diff. The changes are focused on data validation and are self-contained within the functions.

### Q2: LAW COMPLIANCE

The code in this diff is compliant with all governing laws.

-   **SENTENCE LAW:** PARTIAL. The diff doesn't implement the core sentence-boundary logic. However, it hardens the `rate_passages` function, which processes the model's ratings on clip boundaries, including faults like `starts_mid_thought` and `ends_mid_thought` (line 161). By making the validation of these ratings strict (`_v_rate`, lines 170-184), it ensures that the model's editorial judgment is not lost or misinterpreted due to parsing errors, thus supporting the intent of the Sentence Law.
-   **SELECTION LOCK:** COMPLIANT. No code related to this law was modified.
-   **SNAP LIMIT:** COMPLIANT. No code related to this law was modified.
-   **NEIGHBOUR:** COMPLIANT. No code related to this law was modified.
-   **ONSET/TAIL:** COMPLIANT. No code related to this law was modified.
-   **CREDITS:** COMPLIANT. No code related to this law was modified.
-   **L-a SIGN-OFF NAMES ALL:** COMPLIANT. No code related to this law was modified.
-   **L-b EDGE WORDS WHOLE:** COMPLIANT. No code related to this law was modified.
-   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT. No code related to this law was modified.
-   **L-d PROTECTED PREVIEW:** COMPLIANT. No code related to this law was modified.
-   **L-e PUNCTUATED BEFORE READ:** COMPLIANT. No code related to this law was modified.
-   **L-f CHANNELS FIRST:** COMPLIANT. No code related to this law was modified.
-   **L-g WRITTEN FORMS:** COMPLIANT. No code related to this law was modified.
-   **L-h TEXT READ AS SPOKEN:** COMPLIANT. No code related to this law was modified.
-   **L-i THE CLAIM IS THE EVENT:** COMPLIANT. The changes in `story_semantics.py` and its tests (`test_caption_entities.py`) bolster the validation around story derivation, which aligns with this law. No violation is introduced.
-   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT. No code related to this law was modified.
-   **L-k ONE CANONICAL FORM:** COMPLIANT. No code related to this law was modified.
-   **LAW 20 / M2:** COMPLIANT. This law is strongly upheld. The diff systematically *tightens* gate thresholds by replacing lenient parsing with strict validation. For example, `rate_passages` no longer clamps scores (old line 206); an out-of-range score is now a hard failure. This is the opposite of loosening a check to make a render pass.
-   **M12 FAIL CLOSED:** COMPLIANT. This is the core principle embodied by the entire diff. The introduction of the `_field` validator, the rewrite of all `_v_*` validation functions, and the removal of silent error handling (e.g., `except: pass`) all serve to make the system fail safely and loudly when encountering unexpected, missing, or malformed data from the LLM.

### Q3: TESTS

The tests are high-quality and effectively prove the correctness of the changes.

-   **Comprehensive Failure Testing:** The new test `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call` (lines 267-314)

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 23:41
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| `_field` validator (lines 17-42) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `_str_list` validator (lines 45-49) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `_v_derive` (lines 55-78) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `_v_adj` (lines 85-94) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `_v_sup` (lines 100-109) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `_v_rate` (lines 170-184) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| `rate_passages` (lines 187-214) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Fail-closed / silent exception removal | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Sentence Law core boundary logic | ⚠️ PARTIAL | ✅ PASS | ✅ PASS | ⚠️ PARTIAL |
| Law M12 (Fail Closed) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Law M2 / LAW 20 gate thresholds | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Test coverage — failure modes | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Test coverage — control/happy path | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| Test integration (workflow-level) | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| FakeLLM mock realism | ✅ PASS | — | ✅ PASS | ✅ PASS |
| **Overall Verdict** | **READY** | **READY** | **READY** | **READY** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models agreed the code is correct, law-compliant, and adequately tested. No defects were identified unanimously. There are no mandatory fixes.

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None requiring a code change.** The two observations with majority agreement are informational, not defect-driven:

1. **`same_actor_action_object` fail-closed fix** (Gemini + implicitly Grok, via "fail closed" framing): The change from `s.get("same_actor_action_object") is False` to `s["same_actor_action_object"] is not True` (line ~134) was noted as a critical correctness improvement. Both models confirmed the new logic is correct. GPT-4o did not specifically call this out but marked the section COMPLIANT. **Status: Already implemented correctly — no action needed.**

2. **Removal of `try...except Exception: pass`** in `rate_passages` (Gemini + Grok explicitly, GPT-4o implicitly via M12 compliance): The old silent discard pattern was dangerous. Its removal is confirmed correct by all three models. **Status: Already implemented correctly — no action needed.**

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### 1. Sentence Law Core Boundary Logic — Not In Diff (Gemini only)
**Model:** Gemini  
**Observation:** Gemini flagged the Sentence Law assessment as "PARTIAL" because the diff hardens validation *around* sentence-boundary logic (specifically `starts_mid_thought` / `ends_mid_thought` fault handling in `_v_rate`) but does not implement or modify the core sentence-boundary enforcement logic itself.  
**Assessment:** This is a legitimate ar

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (473 lines)
```
   1 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
   2 | index f6cbdc63..d5efaf8b 100644
   3 | --- a/pipeline/story_semantics.py
   4 | +++ b/pipeline/story_semantics.py
   5 | @@ -23,6 +23,7 @@ Identity rules (nothing lexical stands in for semantics):
   6 |  import gc
   7 |  import hashlib
   8 |  import json
   9 | +import math
  10 |  import os
  11 |  import re
  12 |  import subprocess
  13 | @@ -398,11 +399,64 @@ Return ONLY JSON with keys:
  14 |  "rationale": one sentence}}"""
  15 |  
  16 |  
  17 | +def _field(o, key, kind, allowed=None, nonempty=False, lo=None, hi=None, optional=False):
  18 | +    """One field of a model reply, strictly (red-team B): exact type (an int is never a bool or a string; an
  19 | +    integral float such as 5.0 counts as an int), an enumerated value (compared, and written back, stripped and
  20 | +    lower-case: 'Current' is 'current'), a non-empty string, a finite number in range. optional: an absent / null
  21 | +    field is accepted (a reason no decision reads). Raises ValueError: the call failed."""
  22 | +    if not isinstance(o, dict):
  23 | +        raise ValueError("reply is not a JSON object")
  24 | +    v = o.get(key)
  25 | +    if optional and v is None:
  26 | +        return None
  27 | +    if kind == "int" and type(v) is float and math.isfinite(v) and v == int(v):
  28 | +        v = o[key] = int(v)
  29 | +    if allowed is not None and isinstance(v, str):
  30 | +        v = o[key] = v.strip().lower()
  31 | +    # type(), not isinstance(): bool is a subclass of int, so isinstance(True, int) would accept True as 1
  32 | +    ok = {"int": type(v) is int, "bool": type(v) is bool, "str": isinstance(v, str), "list": isinstance(v, list),
  33 | +          "num": type(v) in (int, float) and math.isfinite(v)}[kind]      # NaN / inf never pass (batch 17 audit #1)
  34 | +    if not ok:
  35 | +        raise ValueError(f"{key} must be {kind}, got {type(v).__name__}")
  36 | +    if allowed is not None and v not in allowed:
  37 | +        raise ValueError(f"{key} {v!r} not in {allowed}")
  38 | +    if nonempty and not (v.strip() if isinstance(v, str) else v):
  39 | +        raise ValueError(f"{key} is empty")
  40 | +    if (lo is not None and v < lo) or (hi is not None and v > hi):
  41 | +        raise ValueError(f"{key} {v!r} outside [{lo}, {hi}]")
  42 | +    return v
  43 | +
  44 | +
  45 | +def _str_list(o, key, nonempty=False):
  46 | +    """A list of strings; nonempty: at least one, and no empty string in it."""
  47 | +    v = _field(o, key, "list")
  48 | +    if not all(isinstance(x, str) and (x.strip() or not nonempty) for x in v) or (nonempty and not v):
  49 | +        raise ValueError(f"{key} must be a list of {'non-empty ' if nonempty else ''}strings")
  50 | +
  51 | +
  52 | +EVENT_DATE = re.compile(r"unknown|(19|20)\d{2}(-\d{2}(-\d{2})?)?")   # the forms the prompts ask for
  53 | +
  54 | +
  55 |  def _v_derive(o):
  56 | -    for k in ("underlying_event", "bitcoin_relevance", "importance"):
  57 | -        if k not in o:
  58 | -            raise ValueError(f"missing {k}")
  59 | -    int(o["bitcoin_relevance"]), int(o["importance"])
  60 | +    """Every field a decision reads: the event, its Bitcoin relevance and importance (the screen and the ranking),
  61 | +    its date and recency (currentness), the entities / action / object / confusables (adjudication context)."""
  62 | +    _field(o, "underlying_event", "str", nonempty=True)
  63 | +    _field(o, "bitcoin_relevance", "int", lo=0, hi=5)
  64 | +    _field(o, "importance", "int", lo=0, hi=5)
  65 | +    if not EVENT_DATE.fullmatch(_field(o, "event_date", "str", nonempty=True).strip()):
  66 | +        raise ValueError(f"event_date {o['event_date']!r} is not YYYY-MM-DD / YYYY-MM / YYYY / unknown")
  67 | +    _field(o, "event_recency", "str", allowed=("current", "recent", "historical"))
  68 | +    _field(o, "action", "str")
  69 | +    _field(o, "affected_object", "str")
  70 | +    ents = _field(o, "entities", "list")
  71 | +    for e in ents:
  72 | +        if isinstance(e, dict) and e.get("aliases") is None:
  73 | +            e["aliases"] = []                       # a null aliases list is an empty one
  74 | +    if not all(isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()
  75 | +               and isinstance(e["aliases"], list) for e in ents):
  76 | +        raise ValueError("entities must be objects with a name and an aliases list")
  77 | +    _str_list(o, "must_not_confuse_with")
  78 | +    _str_list(o, "concepts")
  79 |  
  80 |  
  81 |  CLUSTER_NOTE = ("This item is a development several Bitcoin channels state in common (DEC-13): underlying_event "
  82 | @@ -588,13 +642,26 @@ Return ONLY JSON: {{"quote_actor": who acts in the quote ("unstated" if nobody i
  83 |  
  84 |  
  85 |  def _v_adj(o):
  86 | -    if o.get("verdict") not in VERDICTS:
  87 | -        raise ValueError(f"verdict {o.get('verdict')!r} not in {VERDICTS}")
  88 | +    """A positive verdict must carry its evidence: supporting chunk ids and a quote (claude-fable B #4)."""
  89 | +    positive = _field(o, "verdict", "str", allowed=tuple(v.lower() for v in VERDICTS)) == "current_event"
  90 | +    o["verdict"] = o["verdict"].upper()           # the canonical label form
  91 | +    _str_list(o, "supporting_chunk_ids", nonempty=positive)
  92 | +    _field(o, "evidence_quote", "str", nonempty=positive)
  93 | +    _field(o, "confidence", "num", lo=0, hi=1)
  94 | +    _field(o, "reason", "str", optional=True)
  95 | +
  96 | +
  97 | +SUPPORT_PRESENTED = ("current", "past", "unclear")
  98 |  
  99 |  
 100 |  def _v_sup(o):
 101 | -    if o.get("support") not in SUPPORT:
 102 | -        raise ValueError(f"support {o.get('support')!r} not in {SUPPORT}")
 103 | +    """GPT-select F01: the fields that decide SUPPORTS are required and typed (a missing same_actor_action_object
 104 | +    or presented_as was read as agreement)."""
 105 | +    _field(o, "support", "str", allowed=tuple(x.lower() for x in SUPPORT))
 106 | +    o["support"] = o["support"].upper()            # the canonical label form
 107 | +    _field(o, "same_actor_action_object", "bool")
 108 | +    _field(o, "presented_as", "str", allowed=SUPPORT_PRESENTED)
 109 | +    _field(o, "reason", "str", optional=True)
 110 |  
 111 |  
 112 |  def _entities_str(q):
 113 | @@ -629,8 +696,9 @@ Return ONLY JSON: {{"label": one of the three, "reason": one sentence}}"""
 114 |  
 115 |  
 116 |  def _v_react(o):
 117 | -    if o.get("label") not in REACTION_LABELS:
 118 | -        raise ValueError(f"label {o.get('label')!r} not in {REACTION_LABELS}")
 119 | +    _field(o, "label", "str", allowed=tuple(x.lower() for x in REACTION_LABELS))
 120 | +    o["label"] = o["label"].upper()
 121 | +    _field(o, "reason", "str", optional=True)
 122 |  
 123 |  
 124 |  def verify_reaction(llm, q, anchor, sentence):
 125 | @@ -646,11 +714,13 @@ def verify_support(llm, q, quote):
 126 |                                obj=q.get("affected_object", "-"), entities=_entities_str(q),
 127 |                                note=UNTRUSTED_NOTE, quote=quote_data(quote, 600))
 128 |      s = llm.chat_json(p, max_tokens=350, validate=_v_sup)
 129 | -    if s["support"] == "SUPPORTS":       # the structured fields must agree with the label
 130 | -        if s.get("same_actor_action_object") is False:
 131 | -            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is false"
 132 | -        elif str(s.get("presented_as", "")).lower() == "past":
 133 | +    if s["support"] == "SUPPORTS":       # the structured fields must AGREE with the label (fail closed: GPT-select F01)
 134 | +        if s["same_actor_action_object"] is not True:
 135 | +            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is not true"
 136 | +        elif s["presented_as"] == "past":
 137 |              s["support"], s["downgraded"] = "BACKGROUND", "presented_as past"
 138 | +        elif s["presented_as"] != "current":
 139 | +            s["support"], s["downgraded"] = "INCONCLUSIVE", f"presented_as {s['presented_as']}"
 140 |      return s
 141 |  
 142 |  
 143 | @@ -738,8 +808,14 @@ def emergent_clusters(chunks, vecs, min_channels=3, threshold=0.22, max_clusters
 144 |  
 145 |  
 146 |  def _v_label(o):
 147 | -    if not isinstance(o.get("is_specific_event"), bool):
 148 | -        raise ValueError("is_specific_event must be boolean")
 149 | +    """A specific event must come with everything the current-development check reads."""
 150 | +    if _field(o, "is_specific_event", "bool"):
 151 | +        _field(o, "headline", "str", nonempty=True)
 152 | +        if not EVENT_DATE.fullmatch(_field(o, "event_date", "str", nonempty=True).strip()):
 153 | +            raise ValueError(f"event_date {o['event_date']!r} is not YYYY-MM-DD / YYYY-MM / YYYY / unknown")
 154 | +        _field(o, "current_development_quote", "str", nonempty=True)
 155 | +        _field(o, "current_development_chunk_id", "str", nonempty=True)
 156 | +        _str_list(o, "member_chunk_ids", nonempty=True)
 157 |  
 158 |  
 159 |  def label_cluster(llm, chunks, vecs, group, today, k=8):
 160 | @@ -805,9 +881,24 @@ Return ONLY JSON: {{"ratings": [{{"id": passage id, "score": 1-5, "fault": one o
 161 |  BOUNDARY_FAULTS = ("starts_mid_thought", "ends_mid_thought")   # D3: the only faults a repair may address
 162 |  
 163 |  
 164 | -def _v_rate(o):
 165 | -    if not isinstance(o.get("ratings"), list):
 166 | -        raise ValueError("ratings must be a list")
 167 | +RATE_FAULTS = BOUNDARY_FAULTS + ("none", "off_topic", "other")
 168 | +
 169 | +
 170 | +def _v_rate(o, ids=None):
 171 | +    """GPT-select F12: a score outside 1-5 or not a number, an unknown fault, a duplicate or unknown passage id, or
 172 | +    (with ids) a passage left unrated is a failed call; it is never clamped into a perfect score."""
 173 | +    seen = set()
 174 | +    for x in _field(o, "ratings", "list"):
 175 | +        if not isinstance(x, dict):                   # an entry that is not an object is a failed call (audit #2)
 176 | +            raise ValueError("a rating is not an object")
 177 | +        pid = str(_field(x, "id", "str") if isinstance(x.get("id"), str) else _field(x, "id", "int"))
 178 | +        _field(x, "score", "num", lo=1, hi=5)
 179 | +        _field(x, "fault", "str", allowed=RATE_FAULTS)              # stripped / lower-cased before the check
 180 | +        if pid in seen or (ids is not None and pid not in ids):
 181 | +            raise ValueError(f"rating id {pid!r} duplicate or unknown")
 182 | +        seen.add(pid)
 183 | +    if ids is not None and seen != set(ids):
 184 | +        raise ValueError(f"unrated passages: {sorted(set(ids) - seen)[:5]}")
 185 |  
 186 |  
 187 |  def rate_passages(llm, q, passages):
 188 | @@ -816,19 +907,15 @@ def rate_passages(llm, q, passages):
 189 |      ex = "\n".join(f'<excerpt id="{p["pid"]}" channel="{p["channel"]}" seconds="{p["duration"]:.0f}">'
 190 |                     f'{quote_data(p["text"], 700)}</excerpt>' for p in passages)
 191 |      try:
 192 | +        ids = {str(p["pid"]) for p in passages}
 193 |          r = llm.chat_json(CLIP_PROMPT.format(event=q.get("underlying_event", ""), note=UNTRUSTED_NOTE,
 194 | -                                             passages=ex), max_tokens=1200, validate=_v_rate)
 195 | +                                             passages=ex), max_tokens=1200, validate=lambda o: _v_rate(o, ids))
 196 |      except LLMParseError as e:
 197 |          return {}, {"error": str(e), "llm_attempts": e.attempts}
 198 |      out = {}
 199 | -    valid = {p["pid"] for p in passages}
 200 | -    for x in r.get("ratings", []) or []:
 201 | -        try:
 202 | -            pid = str(x["id"])
 203 | -            if pid in valid:
 204 | -                fault = x.get("fault") if x.get("fault") in BOUNDARY_FAULTS + ("none", "off_topic", "other") \
 205 | -                    else "unspecified"
 206 | -                out[pid] = (max(1.0, min(5.0, float(x["score"]))), x.get("reason", ""), fault)
 207 | -        except Exception:
 208 | -            pass
 209 | +    by_id = {str(p["pid"]): p["pid"] for p in passages}   # one normalisation for validation and output (audit #3)
 210 | +    for x in r["ratings"]:                          # validated: every passage once, score 1-5, a known fault
 211 | +        pid = str(x["id"])
 212 | +        if pid in by_id:
 213 | +            out[by_id[pid]] = (float(x["score"]), str(x.get("reason", "")), x["fault"])
 214 |      return out, None
 215 | diff --git a/pipeline/test_caption_entities.py b/pipeline/test_caption_entities.py
 216 | index 09b15c3f..cdf2f9e5 100644
 217 | --- a/pipeline/test_caption_entities.py
 218 | +++ b/pipeline/test_caption_entities.py
 219 | @@ -105,8 +105,13 @@ class TestClusterClaimIsTheEvent(unittest.TestCase):
 220 |  
 221 |          def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 222 |              self.prompts.append(prompt)
 223 | -            return {"underlying_event": "The US held its general elections on November 8th, 2026.",
 224 | -                    "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin"}
 225 | +            obj = {"underlying_event": "The US held its general elections on November 8th, 2026.",
 226 | +                   "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin",
 227 | +                   "event_date": "2026-11-08", "event_recency": "current", "entities": [], "concepts": [],
 228 | +                   "must_not_confuse_with": []}
 229 | +            if validate:
 230 | +                validate(obj)
 231 | +            return obj
 232 |  
 233 |      def test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged(self):
 234 |          claim = "Following the US elections, Bitcoin experienced a sell-off and net outflows from US Bitcoin ETFs."
 235 | diff --git a/pipeline/test_editorial_robust.py b/pipeline/test_editorial_robust.py
 236 | index 59a1c282..5c8506cf 100644
 237 | --- a/pipeline/test_editorial_robust.py
 238 | +++ b/pipeline/test_editorial_robust.py
 239 | @@ -229,8 +229,14 @@ class TestQuoteAnchoredWindows(unittest.TestCase):
 240 |                  self.score = score
 241 |  
 242 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 243 | -                return {"ratings": [{"id": i, "score": self.score, "reason": "start at 0.0 instead"}
 244 | -                                    for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 245 | +                if prompt.startswith("You check ONE SENTENCE"):        # the adjacent-sentence verifier: a new subject
 246 | +                    reply = {"label": "NEW_SUBJECT", "reason": "fake"}
 247 | +                else:
 248 | +                    reply = {"ratings": [{"id": i, "score": self.score, "fault": "none", "reason": "start at 0.0 instead"}
 249 | +                                         for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 250 | +                if validate:
 251 | +                    validate(reply)
 252 | +                return reply
 253 |          c = {"query": RUN3["binance"]["query"], "headline": RUN3["binance"]["headline"]}
 254 |          cq = es._clip_quality(c, same, FakeEmbedder(), Rater(5), reg, words, log=lambda s: None)
 255 |          self.assertTrue(any("deduped" in str(x) for a in cq["anchors"] for x in a.get("windows", {}).values()), cq["anchors"])
 256 | @@ -279,10 +285,100 @@ class ScriptedLLM(sm.LocalLLM):
 257 |  
 258 |  class TestMalformedLLM(unittest.TestCase):
 259 |      def test_retry_then_valid(self):
 260 | -        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}', '```json\n{"support": "SUPPORTS",}\n```'])
 261 | +        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}',
 262 | +                           '```json\n{"support": "SUPPORTS", "same_actor_action_object": true, "presented_as": "current", '
 263 | +                           '"reason": "r",}\n```'])
 264 |          self.assertEqual(llm.chat_json("p", validate=sm._v_sup)["support"], "SUPPORTS")
 265 |          self.assertEqual(llm.calls, 2)
 266 |  
 267 | +    def test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call(self):
 268 | +        """Red-team B (GPT-select F01 / F11 / F12; batch 17 audits): ONE defect per case on an otherwise valid reply,
 269 | +        so each case proves its own rule; the valid bases themselves pass."""
 270 | +        import copy
 271 | +        bases = {
 272 | +            "sup": (sm._v_sup, {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current",
 273 | +                                "reason": "r"}),
 274 | +            "adj": (sm._v_adj, {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["AAA:0-1"], "evidence_quote": "q q q",
 275 | +                                "confidence": 0.9, "reason": "r"}),
 276 | +            "derive": (sm._v_derive, {"underlying_event": "x", "bitcoin_relevance": 5, "importance": 3,
 277 | +                                      "event_date": "2026-11-10", "event_recency": "current", "action": "a",
 278 | +                                      "affected_object": "b", "entities": [{"name": "n", "aliases": []}],
 279 | +                                      "must_not_confuse_with": [], "concepts": []}),
 280 | +            "label": (sm._v_label, {"is_specific_event": True, "headline": "h", "event_date": "2026-11",
 281 | +                                    "current_development_quote": "q", "current_development_chunk_id": "c",
 282 | +                                    "member_chunk_ids": ["c"]}),
 283 | +            "rate": (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 4, "fault": "none"},
 284 | +                                                                       {"id": "p1", "score": 2.5, "fault": "off_topic"}]}),
 285 | +        }
 286 | +        for name, (v, base) in bases.items():
 287 | +            v(copy.deepcopy(base))                                                     # the base is valid
 288 | +        defects = [
 289 | +            ("sup", lambda o: o.pop("same_actor_action_object")), ("sup", lambda o: o.pop("presented_as")),
 290 | +            ("sup", lambda o: o.__setitem__("same_actor_action_object", "true")),
 291 | +            ("adj", lambda o: o.__setitem__("supporting_chunk_ids", "AAA:0-1")),
 292 | +            ("adj", lambda o: o.__setitem__("supporting_chunk_ids", [])),             # positive without evidence
 293 | +            ("adj", lambda o: o.__setitem__("evidence_quote", "")),
 294 | +            ("adj", lambda o: o.__setitem__("confidence", float("nan"))),
 295 | +            ("derive", lambda o: o.__setitem__("bitcoin_relevance", True)),           # a bool is not an int
 296 | +            ("derive", lambda o: o.__setitem__("importance", 7)),
 297 | +            ("derive", lambda o: o.__setitem__("event_date", "n/a")),
 298 | +            ("label", lambda o: o.pop("current_development_quote")),
 299 | +            ("label", lambda o: o.__setitem__("member_chunk_ids", [])),
 300 | +            ("label", lambda o: o.__setitem__("member_chunk_ids", [""])),
 301 | +            ("rate", lambda o: o["ratings"][0].__setitem__("score", 9)),
 302 | +            ("rate", lambda o: o["ratings"][0].__setitem__("score", float("nan"))),
 303 | +            ("rate", lambda o: o["ratings"].pop()),                                   # a passage left unrated
 304 | +            ("rate", lambda o: o["ratings"].append(dict(o["ratings"][0]))),           # a duplicate id
 305 | +            ("rate", lambda o: o["ratings"].__setitem__(0, "p0")),                    # an entry that is not an object
 306 | +            ("rate", lambda o: o["ratings"][0].__setitem__("fault", "great")),
 307 | +        ]
 308 | +        for name, fn in defects:
 309 | +            v, base = bases[name]
 310 | +            o = copy.deepcopy(base)
 311 | +            fn(o)
 312 | +            with self.assertRaises(ValueError, msg=f"{name}: {o}"):
 313 | +                v(o)
 314 | +
 315 | +    def test_harmless_variations_are_accepted(self):
 316 | +        """claude-fable B #5: case, an integral float, a null aliases list or a missing reason are not failures."""
 317 | +        o = {"support": "Supports", "same_actor_action_object": True, "presented_as": "Current"}
 318 | +        sm._v_sup(o)
 319 | +        self.assertEqual((o["support"], o["presented_as"]), ("SUPPORTS", "current"))
 320 | +        d = {"underlying_event": "x", "bitcoin_relevance": 5.0, "importance": 3, "event_date": "unknown",
 321 | +             "event_recency": "Current", "action": "a", "affected_object": "b", "entities": [{"name": "n", "aliases": None}],
 322 | +             "must_not_confuse_with": [], "concepts": []}
 323 | +        sm._v_derive(d)
 324 | +        self.assertEqual((d["bitcoin_relevance"], d["entities"][0]["aliases"]), (5, []))
 325 | +
 326 | +    def test_an_invalid_reply_through_the_real_call_is_inconclusive_never_counted(self):
 327 | +        """The whole path: a support reply without its deciding fields, every attempt, through the REAL chat_json
 328 | +        (ScriptedLLM) and adjudicate: not counted, INCONCLUSIVE with the attempts recorded."""
 329 | +        adj = json.dumps({"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["AAAAAAAAAAA:0-1000"],
 330 | +                          "evidence_quote": "some text here and more words", "confidence": 0.9, "reason": "r"})
 331 | +        llm = ScriptedLLM([adj] + ['{"support": "SUPPORTS", "reason": "r"}'] * 3)
 332 | +        v = sm.adjudicate(llm, {"underlying_event": "x"}, {"title": "t", "channel": "c"},
 333 | +                          [{"chunk_id": "AAAAAAAAAAA:0-1000", "text": "some text here and more words"}])
 334 | +        self.assertFalse(v["counted_as_same_event"])
 335 | +        self.assertEqual(v["support"], "INCONCLUSIVE")
 336 | +        self.assertEqual(len(v["support_error"]["llm_attempts"]), 3)
 337 | +
 338 | +    def test_supports_needs_both_deciding_fields_exactly(self):
 339 | +        class One:
 340 | +            model, calls = "fake", 0
 341 | +
 342 | +            def __init__(self, reply):
 343 | +                self.reply = reply
 344 | +
 345 | +            def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 346 | +                if validate:
 347 | +                    validate(self.reply)
 348 | +                return dict(self.reply)
 349 | +        base = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "r"}
 350 | +        self.assertEqual(sm.verify_support(One(base), {"underlying_event": "x"}, "q")["support"], "SUPPORTS")
 351 | +        for change, want in (({"same_actor_action_object": False}, "TOPIC_ONLY"), ({"presented_as": "past"}, "BACKGROUND"),
 352 | +                             ({"presented_as": "unclear"}, "INCONCLUSIVE")):
 353 | +            self.assertEqual(sm.verify_support(One({**base, **change}), {"underlying_event": "x"}, "q")["support"], want)
 354 | +
 355 |      def test_bounded_and_recorded(self):
 356 |          llm = ScriptedLLM(["not json", '{"verdict": "MAYBE"}', '{"verdict": '])
 357 |          with self.assertRaises(sm.LLMParseError) as cm:
 358 | @@ -348,27 +444,39 @@ class FakeLLM:
 359 |              if "PARSEFAIL" in h:
 360 |                  raise sm.LLMParseError("no valid JSON after 3 attempts",
 361 |                                         [{"attempt": i + 1, "error": "bad", "raw": "{oops"} for i in range(3)])
 362 | -            return {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 363 | +            return self._ok(validate, {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 364 |                      "event_recency": self.model_recency, "entities": [{"name": "Congress", "aliases": ["midterms", "Senate"]}],
 365 |                      "action": "flip", "affected_object": "Congress", "concepts": ["midterms", "Congress"],
 366 | -                    "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True}
 367 | +                    "must_not_confuse_with": [], "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True})
 368 |          if prompt.startswith("You verify whether"):
 369 |              self.adj += 1
 370 |              if self.crash and self.adj == self.crash:
 371 |                  raise RuntimeError("boom (simulated crash)")
 372 |              m = re.search(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 373 |              words = m.group(2).split()[:10]
 374 | -            return {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 375 | -                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"}
 376 | +            return self._ok(validate, {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 377 | +                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"})
 378 |          if prompt.startswith("Decide whether a QUOTE"):
 379 | -            return {"support": "SUPPORTS", "reason": "fake"}
 380 | +            return self._ok(validate, {"support": "SUPPORTS", "same_actor_action_object": True,
 381 | +                                       "presented_as": "current", "reason": "fake"})
 382 |          if prompt.startswith("These transcript excerpts"):
 383 | -            return {"is_specific_event": False}
 384 | +            return self._ok(validate, {"is_specific_event": False})
 385 |          if prompt.startswith("You pick clips"):
 386 | -            return {"ratings": [{"id": i, "score": 5, "reason": "fake"}
 387 | -                                for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 388 | +            return self._ok(validate, {"ratings": [{"id": i, "score": 5, "fault": "none", "reason": "fake"}
 389 | +                                                   for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]})
 390 |          raise AssertionError("unexpected prompt")
 391 |  
 392 | +    @staticmethod
 393 | +    def _ok(validate, obj):
 394 | +        """The real chat_json contract: a reply the validator rejects is a failed call (LLMParseError), never
 395 | +        returned."""
 396 | +        if validate:
 397 | +            try:
 398 | +                validate(obj)
 399 | +            except ValueError as e:
 400 | +                raise sm.LLMParseError(f"no valid JSON after 3 attempts: {e}", [{"attempt": 1, "error": str(e)}])
 401 | +        return obj
 402 | +
 403 |  
 404 |  TXT = ("Democrats took the House and the Senate in the midterms this week and Congress flips, "
 405 |         "which changes the outlook for Bitcoin policy and crypto legislation next year. ")
 406 | diff --git a/pipeline/test_same_event_merge.py b/pipeline/test_same_event_merge.py
 407 | index 966ebae6..0853841b 100644
 408 | --- a/pipeline/test_same_event_merge.py
 409 | +++ b/pipeline/test_same_event_merge.py
 410 | @@ -47,8 +47,13 @@ class MergeLLM(RoutedLLM):
 411 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 412 |          if prompt.startswith(sm.DERIVE_PROMPT.split("{")[0][:40]):
 413 |              self.prompts.append(prompt)
 414 | -            return {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 415 | -                    "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current"}
 416 | +            obj = {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 417 | +                   "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current",
 418 | +                   "event_date": "2026-11-09", "action": "fell", "affected_object": "Bitcoin price", "entities": [],
 419 | +                   "concepts": [], "must_not_confuse_with": []}
 420 | +            if validate:
 421 | +                validate(obj)
 422 | +            return obj
 423 |          return super().chat_json(prompt, max_tokens, validate, attempts)
 424 |  
 425 |  
 426 | diff --git a/pipeline/test_window_review.py b/pipeline/test_window_review.py
 427 | index 3e14b898..a7fd40eb 100644
 428 | --- a/pipeline/test_window_review.py
 429 | +++ b/pipeline/test_window_review.py
 430 | @@ -136,8 +136,11 @@ class TestHooksUseVerifiedExpansion(unittest.TestCase):
 431 |              model = "fake"
 432 |  
 433 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 434 | -                return {"ratings": [{"id": i, "score": 3, "reason": "x"}
 435 | +                reply = {"ratings": [{"id": i, "score": 3, "fault": "none", "reason": "x"}
 436 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 437 | +                if validate:
 438 | +                    validate(reply)
 439 | +                return reply
 440 |          seen = []
 441 |          orig_e, orig_a = es.expanded_window, es.anchored_window
 442 |  
 443 | @@ -325,18 +328,27 @@ class RoutedLLM:
 444 |          self.second_quote, self.rate, self.prompts = second_quote, rate or (lambda t: (5, "none")), []
 445 |  
 446 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 447 | +        """Every reply is validated like the real call (batch 17 audit: fakes that skip the validator test nothing)."""
 448 | +        reply = self._reply(prompt)
 449 | +        if validate:
 450 | +            validate(reply)
 451 | +        return reply
 452 | +
 453 | +    def _reply(self, prompt):
 454 |          sm = self.sm
 455 |          self.prompts.append(prompt)
 456 |          if prompt.startswith("You verify whether"):
 457 |              hit = [i for i, t in re.findall(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 458 |                     if self.second_quote and sm._norm(self.second_quote) in sm._norm(t)]
 459 |              if not hit:
 460 | -                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "reason": "fake"}
 461 | +                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "confidence": 0.9,
 462 | +                        "reason": "fake"}
 463 |              return {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": hit[:1],
 464 |                      "evidence_quote": self.second_quote, "confidence": 0.9, "reason": "fake"}
 465 |          if prompt.startswith("Decide whether a QUOTE"):
 466 |              q = re.search(r'<excerpt id="quote">(.*?)</excerpt>', prompt, re.S).group(1)
 467 | -            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY", "reason": "fake"}
 468 | +            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY",
 469 | +                    "same_actor_action_object": sm._norm(q) in self.on_event, "presented_as": "current", "reason": "fake"}
 470 |          if prompt.startswith("You check ONE SENTENCE"):                 # D4 reaction / consequence verifier
 471 |              t = re.search(r'<excerpt id="sentence">(.*?)</excerpt>', prompt, re.S).group(1)
 472 |              return {"label": sm.REACTION_OK if sm._norm(t) in self.reactions else "NEW_SUBJECT", "reason": "fake"}
 473 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
