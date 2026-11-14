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
The diff is correct on what it changes. `_field` (lines 9-25) and `_str_list` (28-30) perform strict type/allowed/range/nonempty checks and raise `ValueError` on any failure. All validator functions (`_v_derive`, `_v_adj`, `_v_sup`, `_v_react`, `_v_label`, `_v_rate`) now route through them. `verify_support` (102-108) now requires `same_actor_action_object is True` and `presented_as == "current"` exactly; any deviation downgrades the verdict. `rate_passages` (175-178) only consumes data after `validate` succeeds and no longer clamps or silently drops bad entries. No time/index arithmetic, no audio/gate logic, and no silent exception swallowing paths are present in this diff.

**Q2: LAW COMPLIANCE**  
COMPLIANT with M12 (fail closed) and the red-team intent stated in the comments. The changes make malformed or incomplete LLM replies produce `ValueError` (caught as parse failure) rather than a partial or defaulted result. No changes touch sentence boundaries, selection locks, cut movement, edge-word rules, or any gate threshold. No path in this diff can move a cut outside a locked sentence or recompute first/last words.

**Q3: TESTS**  
Tests are updated to supply complete objects that pass the new validators (e.g., lines 190-196, 278-279, 282-283). The new test at 224-238 explicitly asserts that missing, mistyped, out-of-range, or duplicate fields raise `ValueError`. The `ScriptedLLM._ok` helper (294-299) enforces that `validate` must succeed before a reply is returned. No vacuous assertions observed.

**Q4: VERDICT**  
No defects found in the supplied diff.

**READY**

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `_field` (lines 9-25):** 
   - The function checks the type, allowed values, non-emptiness, and range of a field in a dictionary. The checks are strict, and exceptions are raised if conditions are not met. This aligns with the docstring and the laws, ensuring strict validation of model replies.
   - No silent exceptions or state leaks are present. The function will raise a `ValueError` if any condition fails, which prevents further processing of invalid data.

2. **Function `_str_list` (lines 28-30):**
   - This function ensures that a specified field is a list of strings. It uses `_field` for validation, ensuring compliance with expected types.

3. **Function `_v_derive` (lines 33-51):**
   - This function validates several fields in a dictionary, ensuring they meet specific criteria. It uses `_field` and `_str_list` for validation, which are strict and raise exceptions if conditions are not met. This prevents processing of invalid data.

4. **Function `_v_adj` (lines 58-65):**
   - Similar to `_v_derive`, this function validates fields related to verdicts. It uses `_field` and `_str_list` for validation, ensuring strict compliance with expected values.

5. **Function `_v_sup` (lines 71-79):**
   - Validates fields related to support decisions. It ensures that fields are present and of the correct type, raising exceptions if not. This prevents incorrect support decisions due to missing or invalid data.

6. **Function `_v_label` (lines 115-124):**
   - Validates fields related to event labeling. It ensures that required fields are present and valid if `is_specific_event` is true. This prevents incorrect labeling due to missing or invalid data.

7. **Function `_v_rate` (lines 138-150):**
   - Validates ratings, ensuring scores are within range, faults are known, and all passages are rated. It raises exceptions for invalid data, preventing incorrect ratings from being processed.

8. **Function `rate_passages` (lines 153-179):**
   - Uses `_v_rate` for validation, ensuring that all ratings are valid before processing. This prevents incorrect passage ratings due to invalid data.

Overall, the functions are correctly implemented according to their docstrings and the laws. They prevent processing of invalid data by raising exceptions, ensuring compliance with the laws.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT. The diff does not show any changes that would allow cuts to move outside locked sentence boundaries.

2. **SELECTION LOCK:** COMPLIANT. No changes in the diff suggest recomputation of expected words after selection.

3. **SNAP LIMIT:** COMPLIANT. No changes in the diff suggest cuts can move outside allowed boundaries.

4. **NEIGHBOUR:** COMPLIANT. No changes in the diff suggest that neighboring words can be included in clips.

5. **ONSET/TAIL:** COMPLIANT. The diff does not affect onset/tail handling.

6. **CREDITS:** COMPLIANT. The diff does not affect credit handling.

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT. The diff does not affect sign-off handling.

8. **L-b EDGE WORDS WHOLE:** COMPLIANT. The diff does not affect edge word handling.

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT. The diff does not affect dissent handling.

10. **L-d PROTECTED PREVIEW:** COMPLIANT. The diff does not affect the protected preview.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT. The diff does not affect punctuation handling.

12. **L-f CHANNELS FIRST:** COMPLIANT. The diff does not affect channel handling.

13. **L-g WRITTEN FORMS:** COMPLIANT. The diff does not affect written form handling.

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT. The diff does not affect text reading.

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT. The diff does not affect claim handling.

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT. The diff does not affect release authorization.

17. **L-k ONE CANONICAL FORM:** COMPLIANT. The diff does not affect canonical form handling.

18. **LAW 20 / M2:** COMPLIANT. No thresholds were loosened.

19. **M12 FAIL CLOSED:** COMPLIANT. Missing data or model failure results in exceptions, not passes.

20. **LAW 22:** COMPLIANT. The diff does not affect the v2f reference path.

### Q3: TESTS

1. **Test `test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged` (lines 198-199):** 
   - Ensures that a cluster claim is correctly identified as its event. The test passes for the correct reason.

2. **Test `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call` (lines 224-238):**
   - Ensures that missing or mistyped fields result in a failed call. The test passes for the correct reason.

3. **Test `test_supports_needs_both_deciding_fields_exactly` (lines 240-256):**
   - Ensures that support decisions require both deciding fields. The test passes for the correct reason.

4. **Other tests (lines 180-354):** 
   - Validate various aspects of the pipeline, ensuring compliance with laws and correct functionality. All tests pass for

## GEMINI — CYCLE 1 OUTPUT
Excellent. This is a comprehensive quality gate process. I will now perform my independent review as an AI model.

---

### Q1: CORRECTNESS

The changed functions appear to do what their docstrings and surrounding comments claim. The core theme of this changeset is to harden the validation of Large Language Model (LLM) responses, moving from a permissive "fail open" or "fail silent" posture to a strict "fail closed" one, in direct alignment with Law M12.

1.  **Centralized Validator (`_field`, lines 9-26):** This new helper function is the heart of the improvement. It correctly and strictly validates the type, allowed values, non-emptiness, and numeric range of fields from a dictionary (presumably a parsed JSON response from an LLM). Its use of `type(v) is int` instead of `isinstance(v, int)` (line 15) is notably strict, correctly preventing a boolean `True` from being accepted as the integer `1`. This is robust. The error messages are specific and helpful for debugging.

2.  **Strict Validation Application:** The new `_field` function is systematically applied to all validation functions (`_v_derive`, `_v_adj`, `_v_sup`, `_v_react`, `_v_label`, `_v_rate`). This replaces previous, weaker checks that often used `dict.get()`, which could silently return `None` and lead to downstream errors or incorrect logic. For example:
    *   In `verify_support`, the old logic at line 99 (`s.get("same_actor_action_object") is False`) would not trigger a downgrade if the key was missing entirely. The new code (lines 77, 103) is much safer: `_v_sup` ensures the key exists and is a boolean, and the logic `s["same_actor_action_object"] is not True` correctly downgrades on `False`. This is a significant correctness improvement.
    *   In `rate_passages`, the old code used a broad `except Exception: pass` (lines 173-174), which could silently drop ratings for passages if the LLM response was malformed for that rating. The new validator `_v_rate` (lines 138-150), when called with the set of expected passage IDs (line 161), guarantees that every passage is rated exactly once, with valid scores and fault codes. This prevents silent data loss and ensures a failed LLM call is properly caught and raised as an `LLMParseError`.

3.  **Fail-Closed Logic:** The changes demonstrate a strong commitment to the "fail closed" principle (M12). Any deviation from the expected LLM response format—a missing key, a mistyped value, an out-of-range number, an unrated item—will now raise a `ValueError`, which `llm.chat_json` is designed to catch and handle as a failed attempt. There are no obvious paths in the new code that would produce a PASS or a valid selection from missing or failed model data.

The code seems correct and free of the specific flaws mentioned (off-by-one, wrong units, etc.). State does not appear to leak between calls, as the validation is performed on a per-response basis.

### Q2: LAW COMPLIANCE

I will assess compliance for each law based on the provided diff.

*   **SENTENCE LAW:** **COMPLIANT.** The diff does not modify `sentence_law.py` or the code that physically makes cuts. However, it improves compliance indirectly by hardening the `rate_passages` function (lines 153-179), which uses `BOUNDARY_FAULTS` (line 129) to have an LLM rate clips for "starts_mid_thought" or "ends_mid_thought". By ensuring these ratings are always received and valid, it improves the quality of the signal used to avoid D2/D3 errors.
*   **SELECTION LOCK:** **COMPLIANT.** No code related to recomputing or modifying the `selection_lock` is present.
*   **SNAP LIMIT:** **COMPLIANT.** No code related to audio-level cut placement is present.
*   **NEIGHBOUR:** **COMPLIANT.** No code related to audio-level analysis of neighbouring words is present.
*   **ONSET/TAIL:** **COMPLIANT.** No code related to this rule is present.
*   **CREDITS:** **COMPLIANT.** No code related to credit generation is present.
*   **L-a SIGN-OFF NAMES ALL:** **COMPLIANT.** No code related to sign-off voiceover is present.
*   **L-b EDGE WORDS WHOLE:** **COMPLIANT.** No code related to fade placement is present.
*   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** **COMPLIANT.** No code related to gate orchestration or cross-gate checks is present.
*   **L-d PROTECTED PREVIEW:** **COMPLIANT.** No code related to regression testing infrastructure is present.
*   **L-e PUNCTUATED BEFORE READ:** **COMPLIANT.** No code related to transcript acquisition or punctuation is present.
*   **L-f CHANNELS FIRST:** **COMPLIANT.** No code related to story candidate pooling is present.
*   **L-g WRITTEN FORMS:** **COMPLIANT.** No code for `_g3b_words` or word normalization for ASR is present.
*   **L-h TEXT READ AS SPOKEN:** **COMPLIANT.** No changes to `_norm` or `transcript_store.read_text`.
*   **L-i THE CLAIM IS THE EVENT:** **COMPLIANT.** No code in `derive_story_query` was changed.
*   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** **COMPLIANT.** No code from `release_auth.py` is present.
*   **

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 23:30
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 5/5 | 5/5 | 5/5 | 5/5 |
| Law Compliance | 5/5 | 5/5 | 5/5 | 5/5 |
| Test Quality | 5/5 | 5/5 | 5/5 | 5/5 |
| Defects Found | 0 | 0 | 0 | 0 |
| Overall | PASS | PASS | PASS | PASS |

*Note: No model used a numeric scoring rubric. Scores reflect each model's qualitative verdict (all three independently returned zero defects and READY). A 5/5 reflects unanimous clean bill of health.*

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models independently found zero defects. There are no issues that all three models flagged for correction.

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None.** No issue was flagged by two or more models. No corrective action is mandated by majority consensus.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — `type(v) is int` strictness over `isinstance(v, int)` (Gemini only)
**What:** Gemini specifically highlighted that `_field` uses `type(v) is int` rather than `isinstance(v, int)`, which correctly rejects boolean `True` as a substitute for integer `1`, since `bool` is a subclass of `int` in Python.
**Assessment: VALIDATE AND DOCUMENT, do not change.**
The implementation is already correct. This is a subtle Python footgun that the code already handles right. Add an explicit comment at the check site and add a test case that passes `True` where an `int` is expected and asserts `ValueError`. This tightens the regression net around a non-obvious Python behaviour that future developers might innocently "fix" by switching to `isinstance`.
**Action:** Add inline comment `# bool is a subclass of int; use `type()` to reject True/False` and add one test case to `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call`.

### U2 — `rate_passages` previously had a broad `except Exception: pass` (Gemini only)
**What:** Gemini called out that the old code contained a silent swallow at lines 173-174 that could silently drop malformed ratings. The new `_v_rate` fixes this.
**Assessment: ALREADY FIXED — no action needed.**
Gemini is correct that this was the most dangerous pre-existing defect, but the diff already remedies it. Worth preserving as a comment in the commit history / audit trail to explain why `_v_rate` was introduced.

### U3 — Indirect compliance benefit of hardened `rate_passages` for SENTENCE LAW (Gemini only)
**What:** Gemini observed that hardening `rate_passages` with `BOUNDARY_FAULTS` improves the quality of D2/D3 signal, indirectly strengthening SENTENCE LAW compliance even though no sentence-law code changed.
**Assessment: DOCUMENT, no code change needed.**
This is architecturally correct reasoning. It should be noted in the Gospel or the feature's design doc so future auditors understand the coupling betw

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (354 lines)
```
   1 | diff --git a/pipeline/story_semantics.py b/pipeline/story_semantics.py
   2 | index f6cbdc63..e85f7ff2 100644
   3 | --- a/pipeline/story_semantics.py
   4 | +++ b/pipeline/story_semantics.py
   5 | @@ -398,11 +398,45 @@ Return ONLY JSON with keys:
   6 |  "rationale": one sentence}}"""
   7 |  
   8 |  
   9 | +def _field(o, key, kind, allowed=None, nonempty=False, lo=None, hi=None):
  10 | +    """One field of a model reply, strictly (red-team B): exact type (an int is never a bool or a string, a list
  11 | +    is a list), an enumerated value, a non-empty string, a number in range. Raises ValueError: the call failed."""
  12 | +    if not isinstance(o, dict):
  13 | +        raise ValueError("reply is not a JSON object")
  14 | +    v = o.get(key)
  15 | +    ok = {"int": type(v) is int, "bool": type(v) is bool, "str": isinstance(v, str), "list": isinstance(v, list),
  16 | +          "num": type(v) in (int, float)}[kind]
  17 | +    if not ok:
  18 | +        raise ValueError(f"{key} must be {kind}, got {type(v).__name__}")
  19 | +    if allowed is not None and v not in allowed:
  20 | +        raise ValueError(f"{key} {v!r} not in {allowed}")
  21 | +    if nonempty and not (v.strip() if isinstance(v, str) else v):
  22 | +        raise ValueError(f"{key} is empty")
  23 | +    if (lo is not None and v < lo) or (hi is not None and v > hi):
  24 | +        raise ValueError(f"{key} {v!r} outside [{lo}, {hi}]")
  25 | +    return v
  26 | +
  27 | +
  28 | +def _str_list(o, key):
  29 | +    if not all(isinstance(x, str) for x in _field(o, key, "list")):
  30 | +        raise ValueError(f"{key} must be a list of strings")
  31 | +
  32 | +
  33 |  def _v_derive(o):
  34 | -    for k in ("underlying_event", "bitcoin_relevance", "importance"):
  35 | -        if k not in o:
  36 | -            raise ValueError(f"missing {k}")
  37 | -    int(o["bitcoin_relevance"]), int(o["importance"])
  38 | +    """Every field a decision reads: the event, its Bitcoin relevance and importance (the screen and the ranking),
  39 | +    its date and recency (currentness), the entities / action / object / confusables (adjudication context)."""
  40 | +    _field(o, "underlying_event", "str", nonempty=True)
  41 | +    _field(o, "bitcoin_relevance", "int", lo=0, hi=5)
  42 | +    _field(o, "importance", "int", lo=0, hi=5)
  43 | +    _field(o, "event_date", "str", nonempty=True)
  44 | +    _field(o, "event_recency", "str", allowed=("current", "recent", "historical"))
  45 | +    _field(o, "action", "str")
  46 | +    _field(o, "affected_object", "str")
  47 | +    if not all(isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()
  48 | +               and isinstance(e.get("aliases", []), list) for e in _field(o, "entities", "list")):
  49 | +        raise ValueError("entities must be objects with a name and an aliases list")
  50 | +    _str_list(o, "must_not_confuse_with")
  51 | +    _str_list(o, "concepts")
  52 |  
  53 |  
  54 |  CLUSTER_NOTE = ("This item is a development several Bitcoin channels state in common (DEC-13): underlying_event "
  55 | @@ -588,13 +622,23 @@ Return ONLY JSON: {{"quote_actor": who acts in the quote ("unstated" if nobody i
  56 |  
  57 |  
  58 |  def _v_adj(o):
  59 | -    if o.get("verdict") not in VERDICTS:
  60 | -        raise ValueError(f"verdict {o.get('verdict')!r} not in {VERDICTS}")
  61 | +    _field(o, "verdict", "str", allowed=VERDICTS)
  62 | +    _str_list(o, "supporting_chunk_ids")
  63 | +    _field(o, "evidence_quote", "str")
  64 | +    _field(o, "confidence", "num", lo=0, hi=1)
  65 | +    _field(o, "reason", "str")
  66 | +
  67 | +
  68 | +SUPPORT_PRESENTED = ("current", "past", "unclear")
  69 |  
  70 |  
  71 |  def _v_sup(o):
  72 | -    if o.get("support") not in SUPPORT:
  73 | -        raise ValueError(f"support {o.get('support')!r} not in {SUPPORT}")
  74 | +    """GPT-select F01: the fields that decide SUPPORTS are required and typed (a missing same_actor_action_object
  75 | +    or presented_as was read as agreement)."""
  76 | +    _field(o, "support", "str", allowed=SUPPORT)
  77 | +    _field(o, "same_actor_action_object", "bool")
  78 | +    _field(o, "presented_as", "str", allowed=SUPPORT_PRESENTED)
  79 | +    _field(o, "reason", "str")
  80 |  
  81 |  
  82 |  def _entities_str(q):
  83 | @@ -629,8 +673,8 @@ Return ONLY JSON: {{"label": one of the three, "reason": one sentence}}"""
  84 |  
  85 |  
  86 |  def _v_react(o):
  87 | -    if o.get("label") not in REACTION_LABELS:
  88 | -        raise ValueError(f"label {o.get('label')!r} not in {REACTION_LABELS}")
  89 | +    _field(o, "label", "str", allowed=REACTION_LABELS)
  90 | +    _field(o, "reason", "str")
  91 |  
  92 |  
  93 |  def verify_reaction(llm, q, anchor, sentence):
  94 | @@ -646,11 +690,13 @@ def verify_support(llm, q, quote):
  95 |                                obj=q.get("affected_object", "-"), entities=_entities_str(q),
  96 |                                note=UNTRUSTED_NOTE, quote=quote_data(quote, 600))
  97 |      s = llm.chat_json(p, max_tokens=350, validate=_v_sup)
  98 | -    if s["support"] == "SUPPORTS":       # the structured fields must agree with the label
  99 | -        if s.get("same_actor_action_object") is False:
 100 | -            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is false"
 101 | -        elif str(s.get("presented_as", "")).lower() == "past":
 102 | +    if s["support"] == "SUPPORTS":       # the structured fields must AGREE with the label (fail closed: GPT-select F01)
 103 | +        if s["same_actor_action_object"] is not True:
 104 | +            s["support"], s["downgraded"] = "TOPIC_ONLY", "same_actor_action_object is not true"
 105 | +        elif s["presented_as"] == "past":
 106 |              s["support"], s["downgraded"] = "BACKGROUND", "presented_as past"
 107 | +        elif s["presented_as"] != "current":
 108 | +            s["support"], s["downgraded"] = "INCONCLUSIVE", f"presented_as {s['presented_as']}"
 109 |      return s
 110 |  
 111 |  
 112 | @@ -738,8 +784,13 @@ def emergent_clusters(chunks, vecs, min_channels=3, threshold=0.22, max_clusters
 113 |  
 114 |  
 115 |  def _v_label(o):
 116 | -    if not isinstance(o.get("is_specific_event"), bool):
 117 | -        raise ValueError("is_specific_event must be boolean")
 118 | +    """A specific event must come with everything the current-development check reads."""
 119 | +    if _field(o, "is_specific_event", "bool"):
 120 | +        _field(o, "headline", "str", nonempty=True)
 121 | +        _field(o, "event_date", "str", nonempty=True)
 122 | +        _field(o, "current_development_quote", "str", nonempty=True)
 123 | +        _field(o, "current_development_chunk_id", "str", nonempty=True)
 124 | +        _str_list(o, "member_chunk_ids")
 125 |  
 126 |  
 127 |  def label_cluster(llm, chunks, vecs, group, today, k=8):
 128 | @@ -805,9 +856,22 @@ Return ONLY JSON: {{"ratings": [{{"id": passage id, "score": 1-5, "fault": one o
 129 |  BOUNDARY_FAULTS = ("starts_mid_thought", "ends_mid_thought")   # D3: the only faults a repair may address
 130 |  
 131 |  
 132 | -def _v_rate(o):
 133 | -    if not isinstance(o.get("ratings"), list):
 134 | -        raise ValueError("ratings must be a list")
 135 | +RATE_FAULTS = BOUNDARY_FAULTS + ("none", "off_topic", "other")
 136 | +
 137 | +
 138 | +def _v_rate(o, ids=None):
 139 | +    """GPT-select F12: a score outside 1-5 or not a number, an unknown fault, a duplicate or unknown passage id, or
 140 | +    (with ids) a passage left unrated is a failed call; it is never clamped into a perfect score."""
 141 | +    seen = set()
 142 | +    for x in _field(o, "ratings", "list"):
 143 | +        pid = str(_field(x, "id", "str") if isinstance((x or {}).get("id"), str) else _field(x, "id", "int"))
 144 | +        _field(x, "score", "num", lo=1, hi=5)
 145 | +        _field(x, "fault", "str", allowed=RATE_FAULTS)
 146 | +        if pid in seen or (ids is not None and pid not in ids):
 147 | +            raise ValueError(f"rating id {pid!r} duplicate or unknown")
 148 | +        seen.add(pid)
 149 | +    if ids is not None and seen != set(ids):
 150 | +        raise ValueError(f"unrated passages: {sorted(set(ids) - seen)[:5]}")
 151 |  
 152 |  
 153 |  def rate_passages(llm, q, passages):
 154 | @@ -816,19 +880,15 @@ def rate_passages(llm, q, passages):
 155 |      ex = "\n".join(f'<excerpt id="{p["pid"]}" channel="{p["channel"]}" seconds="{p["duration"]:.0f}">'
 156 |                     f'{quote_data(p["text"], 700)}</excerpt>' for p in passages)
 157 |      try:
 158 | +        ids = {str(p["pid"]) for p in passages}
 159 |          r = llm.chat_json(CLIP_PROMPT.format(event=q.get("underlying_event", ""), note=UNTRUSTED_NOTE,
 160 | -                                             passages=ex), max_tokens=1200, validate=_v_rate)
 161 | +                                             passages=ex), max_tokens=1200, validate=lambda o: _v_rate(o, ids))
 162 |      except LLMParseError as e:
 163 |          return {}, {"error": str(e), "llm_attempts": e.attempts}
 164 |      out = {}
 165 |      valid = {p["pid"] for p in passages}
 166 | -    for x in r.get("ratings", []) or []:
 167 | -        try:
 168 | -            pid = str(x["id"])
 169 | -            if pid in valid:
 170 | -                fault = x.get("fault") if x.get("fault") in BOUNDARY_FAULTS + ("none", "off_topic", "other") \
 171 | -                    else "unspecified"
 172 | -                out[pid] = (max(1.0, min(5.0, float(x["score"]))), x.get("reason", ""), fault)
 173 | -        except Exception:
 174 | -            pass
 175 | +    for x in r["ratings"]:                          # validated: every passage once, score 1-5, a known fault
 176 | +        pid = str(x["id"])
 177 | +        if pid in valid:
 178 | +            out[pid] = (float(x["score"]), str(x.get("reason", "")), x["fault"])
 179 |      return out, None
 180 | diff --git a/pipeline/test_caption_entities.py b/pipeline/test_caption_entities.py
 181 | index 09b15c3f..cdf2f9e5 100644
 182 | --- a/pipeline/test_caption_entities.py
 183 | +++ b/pipeline/test_caption_entities.py
 184 | @@ -105,8 +105,13 @@ class TestClusterClaimIsTheEvent(unittest.TestCase):
 185 |  
 186 |          def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 187 |              self.prompts.append(prompt)
 188 | -            return {"underlying_event": "The US held its general elections on November 8th, 2026.",
 189 | -                    "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin"}
 190 | +            obj = {"underlying_event": "The US held its general elections on November 8th, 2026.",
 191 | +                   "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin",
 192 | +                   "event_date": "2026-11-08", "event_recency": "current", "entities": [], "concepts": [],
 193 | +                   "must_not_confuse_with": []}
 194 | +            if validate:
 195 | +                validate(obj)
 196 | +            return obj
 197 |  
 198 |      def test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged(self):
 199 |          claim = "Following the US elections, Bitcoin experienced a sell-off and net outflows from US Bitcoin ETFs."
 200 | diff --git a/pipeline/test_editorial_robust.py b/pipeline/test_editorial_robust.py
 201 | index 59a1c282..498884d2 100644
 202 | --- a/pipeline/test_editorial_robust.py
 203 | +++ b/pipeline/test_editorial_robust.py
 204 | @@ -229,7 +229,7 @@ class TestQuoteAnchoredWindows(unittest.TestCase):
 205 |                  self.score = score
 206 |  
 207 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 208 | -                return {"ratings": [{"id": i, "score": self.score, "reason": "start at 0.0 instead"}
 209 | +                return {"ratings": [{"id": i, "score": self.score, "fault": "none", "reason": "start at 0.0 instead"}
 210 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 211 |          c = {"query": RUN3["binance"]["query"], "headline": RUN3["binance"]["headline"]}
 212 |          cq = es._clip_quality(c, same, FakeEmbedder(), Rater(5), reg, words, log=lambda s: None)
 213 | @@ -279,10 +279,45 @@ class ScriptedLLM(sm.LocalLLM):
 214 |  
 215 |  class TestMalformedLLM(unittest.TestCase):
 216 |      def test_retry_then_valid(self):
 217 | -        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}', '```json\n{"support": "SUPPORTS",}\n```'])
 218 | +        llm = ScriptedLLM(['{"verdict": "CURRENT_EVENT" "x": 1}',
 219 | +                           '```json\n{"support": "SUPPORTS", "same_actor_action_object": true, "presented_as": "current", '
 220 | +                           '"reason": "r",}\n```'])
 221 |          self.assertEqual(llm.chat_json("p", validate=sm._v_sup)["support"], "SUPPORTS")
 222 |          self.assertEqual(llm.calls, 2)
 223 |  
 224 | +    def test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call(self):
 225 | +        """Red-team B (GPT-select F01 / F11 / F12): missing / mistyped / out-of-range fields are never accepted."""
 226 | +        for v, bad in ((sm._v_sup, {"support": "SUPPORTS", "reason": "r"}),                       # fields missing
 227 | +                       (sm._v_sup, {"support": "SUPPORTS", "same_actor_action_object": "true", "presented_as": "current",
 228 | +                                    "reason": "r"}),                                              # a string bool
 229 | +                       (sm._v_adj, {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": "AAA:0-1", "evidence_quote": "q",
 230 | +                                    "confidence": 0.9, "reason": "r"}),                           # ids not a list
 231 | +                       (sm._v_derive, {"underlying_event": "x", "bitcoin_relevance": True, "importance": 3}),  # bool int
 232 | +                       (sm._v_label, {"is_specific_event": True, "headline": "h"}),             # quote / ids missing
 233 | +                       (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 9, "fault": "none"},
 234 | +                                                                          {"id": "p1", "score": 4, "fault": "none"}]}),
 235 | +                       (lambda o: sm._v_rate(o, {"p0", "p1"}), {"ratings": [{"id": "p0", "score": 4, "fault": "none"}]}),
 236 | +                       (lambda o: sm._v_rate(o, {"p0"}), {"ratings": [{"id": "p0", "score": 4, "fault": "great"}]})):
 237 | +            with self.assertRaises(ValueError, msg=str(bad)):
 238 | +                v(bad)
 239 | +
 240 | +    def test_supports_needs_both_deciding_fields_exactly(self):
 241 | +        class One:
 242 | +            model, calls = "fake", 0
 243 | +
 244 | +            def __init__(self, reply):
 245 | +                self.reply = reply
 246 | +
 247 | +            def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 248 | +                if validate:
 249 | +                    validate(self.reply)
 250 | +                return dict(self.reply)
 251 | +        base = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "r"}
 252 | +        self.assertEqual(sm.verify_support(One(base), {"underlying_event": "x"}, "q")["support"], "SUPPORTS")
 253 | +        for change, want in (({"same_actor_action_object": False}, "TOPIC_ONLY"), ({"presented_as": "past"}, "BACKGROUND"),
 254 | +                             ({"presented_as": "unclear"}, "INCONCLUSIVE")):
 255 | +            self.assertEqual(sm.verify_support(One({**base, **change}), {"underlying_event": "x"}, "q")["support"], want)
 256 | +
 257 |      def test_bounded_and_recorded(self):
 258 |          llm = ScriptedLLM(["not json", '{"verdict": "MAYBE"}', '{"verdict": '])
 259 |          with self.assertRaises(sm.LLMParseError) as cm:
 260 | @@ -348,27 +383,35 @@ class FakeLLM:
 261 |              if "PARSEFAIL" in h:
 262 |                  raise sm.LLMParseError("no valid JSON after 3 attempts",
 263 |                                         [{"attempt": i + 1, "error": "bad", "raw": "{oops"} for i in range(3)])
 264 | -            return {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 265 | +            return self._ok(validate, {"short_label": "midterms", "underlying_event": h, "event_date": self.model_date,
 266 |                      "event_recency": self.model_recency, "entities": [{"name": "Congress", "aliases": ["midterms", "Senate"]}],
 267 |                      "action": "flip", "affected_object": "Congress", "concepts": ["midterms", "Congress"],
 268 | -                    "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True}
 269 | +                    "must_not_confuse_with": [], "bitcoin_relevance": 5, "importance": 5, "is_specific_event": True})
 270 |          if prompt.startswith("You verify whether"):
 271 |              self.adj += 1
 272 |              if self.crash and self.adj == self.crash:
 273 |                  raise RuntimeError("boom (simulated crash)")
 274 |              m = re.search(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 275 |              words = m.group(2).split()[:10]
 276 | -            return {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 277 | -                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"}
 278 | +            return self._ok(validate, {"verdict": self.adj_verdict, "supporting_chunk_ids": [m.group(1)],
 279 | +                    "evidence_quote": " ".join(words), "confidence": 0.9, "reason": "fake"})
 280 |          if prompt.startswith("Decide whether a QUOTE"):
 281 | -            return {"support": "SUPPORTS", "reason": "fake"}
 282 | +            return self._ok(validate, {"support": "SUPPORTS", "same_actor_action_object": True,
 283 | +                                       "presented_as": "current", "reason": "fake"})
 284 |          if prompt.startswith("These transcript excerpts"):
 285 | -            return {"is_specific_event": False}
 286 | +            return self._ok(validate, {"is_specific_event": False})
 287 |          if prompt.startswith("You pick clips"):
 288 | -            return {"ratings": [{"id": i, "score": 5, "reason": "fake"}
 289 | -                                for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 290 | +            return self._ok(validate, {"ratings": [{"id": i, "score": 5, "fault": "none", "reason": "fake"}
 291 | +                                                   for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]})
 292 |          raise AssertionError("unexpected prompt")
 293 |  
 294 | +    @staticmethod
 295 | +    def _ok(validate, obj):
 296 | +        """The real chat_json contract: a reply the validator rejects is a failed call, never returned."""
 297 | +        if validate:
 298 | +            validate(obj)
 299 | +        return obj
 300 | +
 301 |  
 302 |  TXT = ("Democrats took the House and the Senate in the midterms this week and Congress flips, "
 303 |         "which changes the outlook for Bitcoin policy and crypto legislation next year. ")
 304 | diff --git a/pipeline/test_same_event_merge.py b/pipeline/test_same_event_merge.py
 305 | index 966ebae6..0853841b 100644
 306 | --- a/pipeline/test_same_event_merge.py
 307 | +++ b/pipeline/test_same_event_merge.py
 308 | @@ -47,8 +47,13 @@ class MergeLLM(RoutedLLM):
 309 |      def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 310 |          if prompt.startswith(sm.DERIVE_PROMPT.split("{")[0][:40]):
 311 |              self.prompts.append(prompt)
 312 | -            return {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 313 | -                    "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current"}
 314 | +            obj = {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
 315 | +                   "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current",
 316 | +                   "event_date": "2026-11-09", "action": "fell", "affected_object": "Bitcoin price", "entities": [],
 317 | +                   "concepts": [], "must_not_confuse_with": []}
 318 | +            if validate:
 319 | +                validate(obj)
 320 | +            return obj
 321 |          return super().chat_json(prompt, max_tokens, validate, attempts)
 322 |  
 323 |  
 324 | diff --git a/pipeline/test_window_review.py b/pipeline/test_window_review.py
 325 | index 3e14b898..7cbc5183 100644
 326 | --- a/pipeline/test_window_review.py
 327 | +++ b/pipeline/test_window_review.py
 328 | @@ -136,7 +136,7 @@ class TestHooksUseVerifiedExpansion(unittest.TestCase):
 329 |              model = "fake"
 330 |  
 331 |              def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
 332 | -                return {"ratings": [{"id": i, "score": 3, "reason": "x"}
 333 | +                return {"ratings": [{"id": i, "score": 3, "fault": "none", "reason": "x"}
 334 |                                      for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
 335 |          seen = []
 336 |          orig_e, orig_a = es.expanded_window, es.anchored_window
 337 | @@ -331,12 +331,14 @@ class RoutedLLM:
 338 |              hit = [i for i, t in re.findall(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
 339 |                     if self.second_quote and sm._norm(self.second_quote) in sm._norm(t)]
 340 |              if not hit:
 341 | -                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "reason": "fake"}
 342 | +                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "confidence": 0.9,
 343 | +                        "reason": "fake"}
 344 |              return {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": hit[:1],
 345 |                      "evidence_quote": self.second_quote, "confidence": 0.9, "reason": "fake"}
 346 |          if prompt.startswith("Decide whether a QUOTE"):
 347 |              q = re.search(r'<excerpt id="quote">(.*?)</excerpt>', prompt, re.S).group(1)
 348 | -            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY", "reason": "fake"}
 349 | +            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY",
 350 | +                    "same_actor_action_object": sm._norm(q) in self.on_event, "presented_as": "current", "reason": "fake"}
 351 |          if prompt.startswith("You check ONE SENTENCE"):                 # D4 reaction / consequence verifier
 352 |              t = re.search(r'<excerpt id="sentence">(.*?)</excerpt>', prompt, re.S).group(1)
 353 |              return {"label": sm.REACTION_OK if sm._norm(t) in self.reactions else "NEW_SUBJECT", "reason": "fake"}
 354 | 
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
