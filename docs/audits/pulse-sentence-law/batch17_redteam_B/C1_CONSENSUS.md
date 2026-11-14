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
This is architecturally correct reasoning. It should be noted in the Gospel or the feature's design doc so future auditors understand the coupling between LLM validation hardening and sentence-boundary safety.

---

## CONFLICTS (models disagree — your tiebreaker)

**None.** All three models reached identical conclusions on every dimension. There are no contradictory recommendations to adjudicate.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

1. **`_field` centralised validator** — Type check using `type(v) is not`, allowed-values check, non-emptiness check, and numeric range check are all implemented correctly and comprehensively. Do not refactor or loosen.

2. **`_v_sup` / `verify_support` logic** — The fix from `s.get("same_actor_action_object") is False` (which missed missing keys) to strict `_v_sup` validation + `is not True` downgrade logic is correct and complete. Do not revert or weaken.

3. **Elimination of `except Exception: pass`** — The silent swallow in `rate_passages` is gone. The `_v_rate` replacement is robust. Do not introduce any broad except clauses.

4. **`_v_rate` passage completeness check** — Requiring every expected passage ID to be rated exactly once, with valid scores and known fault codes, is the correct contract. Do not relax this to optional or partial ratings.

5. **`ScriptedLLM._ok` test helper** — Enforcing that `validate` must pass before a reply is returned is the right design for test scaffolding. Do not bypass this in future tests.

6. **`test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call`** — The malformed-data matrix (missing key, type mismatch, bool-for-int, string-for-list, out-of-range, bad enum, duplicate) is comprehensive and non-vacuous. Do not remove any cases.

7. **`test_supports_needs_both_deciding_fields_exactly`** — Correctly proves both the happy path and each individual downgrade branch. Do not merge or simplify these cases.

8. **Fail-closed posture throughout** — Every validation path raises `ValueError` on any deviation. This is the correct M12 implementation. Do not add defaults, fallbacks, or `.get()` calls anywhere in the validation chain.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence |
|---|---|---|
| SENTENCE LAW (D1/D2/D3) | COMPLIANT | Unanimous |
| SELECTION LOCK | COMPLIANT | Unanimous |
| SNAP LIMIT | COMPLIANT | Unanimous |
| NEIGHBOUR | COMPLIANT | Unanimous |
| ONSET/TAIL | COMPLIANT | Unanimous |
| CREDITS | COMPLIANT | Unanimous |
| L-a SIGN-OFF NAMES ALL | COMPLIANT | Unanimous |
| L-b EDGE WORDS WHOLE | COMPLIANT | Unanimous |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | COMPLIANT | Unanimous |
| L-d PROTECTED PREVIEW | COMPLIANT | Unanimous |
| L-e PUNCTUATED BEFORE READ | COMPLIANT | Unanimous |
| L-f CHANNELS FIRST | COMPLIANT | Unanimous |
| L-g WRITTEN FORMS | COMPLIANT | Unanimous |
| L-h TEXT READ AS SPOKEN | COMPLIANT | Unanimous |
| L-i THE CLAIM IS THE EVENT | COMPLIANT | Unanimous |
| L-j RELEASE IS AUTHORISED ON THESE BYTES | COMPLIANT | Unanimous |
| L-k ONE CANONICAL FORM | COMPLIANT | Unanimous |
| LAW 20 / M2 | COMPLIANT | Unanimous |
| **M12 FAIL CLOSED** | **COMPLIANT — primary focus of diff** | **Unanimous** |
| LAW 22 | COMPLIANT | Unanimous |

**Final determination:** Full compliance across all laws. M12 is the central achievement of this changeset and is robustly implemented.

---

## SECURITY CONSENSUS

No security issues were flagged by any model. The changeset moves in a strictly more secure direction:

- **Injection surface reduced:** Stricter LLM response validation means malformed or adversarially crafted LLM replies cannot propagate into downstream pipeline state.
- **Silent failure eliminated:** The `except Exception: pass` removal closes a path where a compromised or erratic LLM could cause data to be silently dropped rather than loudly failed.
- **Boolean-for-integer bypass closed:** The `type(v) is int` check prevents a type-confusion path that could have been exploited by a model returning `true` where a threshold integer was expected.

No new attack surface was introduced. No priority security actions required.

---

## WORLD-CLASS GAP CONSENSUS

*Only items mentioned by 2+ models are included. No item met this threshold.* All three models independently assessed the changeset as complete and high-quality. The only observations were either confirmations of correctness or documentation suggestions.

**Conclusion from combined model intelligence:** This changeset is already at or near world-class for its stated scope. The gap identified by the single-model unique insights (U1: document the `type()` strictness, U3: document the indirect SENTENCE LAW benefit) are documentation gaps, not implementation gaps.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P2 MEDIUM | Add inline comment explaining `type(v) is int` over `isinstance` to prevent future regression | `_field` validator, type-check line | gemini (unique) | Subtle Python footgun; future developer could "fix" this correctly-written code and reintroduce a bool-bypass bug |
| P2 MEDIUM | Add one test case: pass `True` where `int` expected, assert `ValueError` | `test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call` | gemini (unique) | Closes the regression net around U1; prevents silent reversion |
| P2 MEDIUM | Add a note to Gospel/design doc explaining that `_v_rate` hardening indirectly strengthens SENTENCE LAW D2/D3 signal | `PULSE_SENTENCE_LAW_GOSPEL.md` | gemini (unique) | Architectural coupling that future auditors need to understand; not obvious from diff alone |

**No P0 or P1 items exist.** All three models found zero defects. The only actions are documentation and one defensive test case addition, all at P2.

---

## CYCLE 1 VERDICT

**READY FOR SECOND PASS — no fundamental rework required.**

The code is correct, fully law-compliant, and well-tested. The three P2 items are documentation and one additional test case. The second pass is a polish pass, not a correction pass. `regression_test.sh` is expected to show zero FAILs before and after the second pass changes.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
No P0 or P1 defects were found. Implement all P2 items below.

PRIORITY ACTION PLAN:

P2 MEDIUM | Add inline comment at the `type(v) is int` check in `_field` | validator module, type-check line | models: gemini (unique) | Prevents future developer from "fixing" correctly strict code back to isinstance, which would allow bool True to pass as int 1
  Comment text: "# bool is a subclass of int in Python; use type() not isinstance() to reject True/False where an integer is required"

P2 MEDIUM | Add one test case to test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call | test file for editorial robustness | models: gemini (unique) | Close the regression net: pass True (bool) where an int score is expected and assert ValueError is raised

P2 MEDIUM | Add a paragraph to PULSE_SENTENCE_LAW_GOSPEL.md under a "Design Rationale" or "Indirect Compliance" section | PULSE_SENTENCE_LAW_GOSPEL.md | models: gemini (unique) | Document that hardening _v_rate / rate_passages with BOUNDARY_FAULTS improves D2/D3 sentence-boundary signal quality, so future auditors understand the coupling between LLM validation and sentence-law compliance

VALIDATED — do NOT touch these; all 3 models confirmed excellent:
- _field centralised validator (type/allowed/range/nonempty checks, type() strictness)
- _v_sup / verify_support logic (is not True downgrade, strict field presence)
- Elimination of except Exception: pass in rate_passages
- _v_rate passage completeness contract (every passage rated exactly once)
- ScriptedLLM._ok test helper (validate must pass before reply returned)
- test_a_reply_missing_or_mistyping_a_deciding_field_is_a_failed_call matrix
- test_supports_needs_both_deciding_fields_exactly (all downgrade branches)
- Fail-closed posture everywhere (no defaults, no .get() fallbacks in validation chain)

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (C1 P2 items: type() comment, bool-as-int test, gospel rationale note)"
git push origin combo-letterbox-quoteonly-v2
```