# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 11:08
Models: gpt4o, gemini (+1 failed: grok — budget exceeded)

---

## SCORES

| Subsystem      | Gemini | GPT-4o | Grok        | Consensus |
|----------------|--------|--------|-------------|-----------|
| Correctness    | 8/10   | 9/10   | N/A (failed)| **8.5/10** |
| Law Compliance | 6/10   | 7/10   | N/A (failed)| **6.5/10** |
| Test Quality   | 9/10   | 8/10   | N/A (failed)| **8.5/10** |
| Security       | N/A    | 8/10   | N/A (failed)| **8/10**  |
| **Overall**    | 7.3/10 | 8/10   | N/A (failed)| **7.7/10** |

> **Note on Grok failure:** Grok-3 exceeded daily budget and produced no Cycle 2 output. Consensus is derived from 2 of 3 models. Confidence is moderate — findings that would typically require 3-of-3 agreement are classified as 2-of-2 (majority) rather than unanimous. All unanimous findings below represent 2/2 agreement.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — SENTENCE LAW: Acoustic 80ms pause rule silently relaxed to 0ms
- **What it is:** The core `PAUSE_MIN_S` constant governing the minimum acoustic pause required before a sentence cut has been reduced from 80ms to 0ms (or effectively nullified by the valley logic), allowing cuts at envelope minima where no actual silence exists. This is a **law re-baselining**, not a bug fix.
- **File/Line:** `pipeline/sentence_law.py`, lines 33–37 (constant definitions and boundary logic)
- **What to change:** This change must be formally ratified in `docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md`. The Gospel must state: (a) the old rule (80ms minimum acoustic pause), (b) the new rule (0ms, cuts permitted at envelope valley minima), (c) the rationale (calibration to `v2f` reference, handling of abutting sentences), and (d) the authorizing decision/ticket.
- **Why critical:** Without Gospel documentation, this change is indistinguishable from an unauthorized weakening of a quality gate. Any future audit or engineer will treat it as a defect.

### U2 — ONSET/TAIL: 80ms lead minimum removed for internal cuts
- **What it is:** The `LEAD_MIN_S`/`TAIL_MIN_S` enforcement has been removed for internal (non-head) cuts, introducing a two-tiered rule: 80ms enforced only for file heads and the hook clip; 0ms permitted for internal cuts. This is undocumented in the governing artifact.
- **File/Line:** `pipeline/sentence_law.py` line 266 (`gate_g17_prepared`); Gospel document
- **What to change:** Document the two-tiered rule explicitly in the Gospel. Additionally, add an inline comment at line 266 clarifying the tiering rationale (e.g., `# D1 fix: hook and file head require 80ms lead; internal sentence cuts exempt`).
- **Why critical:** Same class of issue as U1 — unreviewed law relaxation with no paper trail.

### U3 — `prerender_clips` / `run_isolated.py`: No docstring on modified function
- **What it is:** The `prerender_clips` function in `run_isolated.py` (lines 5–13) was modified to accept new dynamic fade parameters (`cut_in_fade_ms`, `cut_out_fade_ms`) sourced from `cuts_final.json`, but no docstring was added or updated to describe the new interface.
- **File/Line:** `pipeline/run_isolated.py`, lines 5–13
- **What to change:** Add a complete docstring describing all parameters, their units (milliseconds), their source (`cuts_final.json`), and the default values. Document that the defaults (20ms in / 30ms out) apply when no cut table entry is present.
- **Why critical:** Data-driven parameters with no documentation create a maintainability hazard; the next developer will not know the units or source without reverse-engineering call sites.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above also constitute majority findings given the 2-model pool. No additional items fall exclusively in this tier — all shared findings have been elevated to Unanimous.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UNIQUE-1 (Gemini only) — `VALLEY_FADE_S` unit confusion: video frames vs. audio frames
- **What it is:** `VALLEY_FADE_S = 2 / 24` (line 39, `sentence_law.py`) is commented as a "2-frame audio fade." The denominator `24` implies a 24fps **video** framerate, yielding ~83.3ms. However, in an audio context, a "2-frame fade" would logically use the audio hop size `HOP_S` (10ms), yielding 20ms. These are very different durations: 83ms is a long fade for a tight valley cut; 20ms is short and correct for abutting words.
- **Assessment: IMPLEMENT (P1 — investigate and correct)**
  - This is a credible and high-value finding. A factor-of-4 duration error on the valley fade would cause audible artifacts (overly long fades smearing adjacent words) or be inaudibly short depending on which interpretation is wrong. The ambiguity is real: `2 / 24` does not self-document its intent.
  - **Recommended action:** Determine the intended duration, then rewrite as either `VALLEY_FADE_S = 2 * HOP_S  # 2 audio frames at HOP_S=10ms → 20ms` or `VALLEY_FADE_S = 2 / 24  # 2 video frames at 24fps → ~83ms` and verify against the `v2f` reference output to confirm which produces the correct listening result. Do not leave the ambiguity in place.

### UNIQUE-2 (GPT-4o only) — Test coverage for envelope minima edge cases
- **What it is:** GPT-4o noted that while tests appear comprehensive, explicit coverage of the new valley/envelope-minima logic edge cases (zero-duration pauses, inverted word gaps, valley cuts where `neighbour_clear` fails) should be verified.
- **Assessment: INVESTIGATE (P2)**
  - Gemini independently praised test quality (9/10), indicating the test suite is strong. However, GPT-4o's concern is directionally valid: new code paths always need targeted tests. This should be a spot-check rather than a blocking issue. If the tests already exercise `find_valley` failure modes and `accepted_cut` returning `None`, this is resolved. If not, add targeted parametric tests.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1 — Severity of missing docstring (U3)
- **GPT-4o:** Rates docstring absence as P1 HIGH
- **Gemini:** Rates it as P2 MEDIUM
- **Tiebreaker verdict: P2 MEDIUM.** The function's behavior is inferable from the call site and existing code context. It is a code hygiene issue, not a correctness or compliance risk. Gemini's classification is correct. It should be fixed but does not block production.

### CONFLICT-2 — Overall production readiness framing
- **GPT-4o:** "Yes with conditions" — implies the P0 governance gap alone blocks release, but tone is relatively optimistic.
- **Gemini:** "Yes with conditions" — explicitly requires P0 governance AND P1 `VALLEY_FADE_S` resolution before merge.
- **Tiebreaker verdict: Gemini is more precise and correct.** The `VALLEY_FADE_S` ambiguity is a genuine correctness risk (not just hygiene) and must be resolved before production. Both P0 and P1 items are hard blockers.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`find_valley` logic (line 75):** Correctly identifies envelope minimum and returns a zero-duration pause object. Clean, correct, and consistent with the stated design. Do not alter.

2. **`neighbour_clear` implementation (line 160):** The dB-space linear fade model using `20 * np.log10(...)` with `np.clip` to prevent domain errors is correct and robust. The final G16 gate re-verification using `neighbour_clear` on the rendered cut is an excellent defence-in-depth pattern. Do not alter.

3. **`cut_candidates` fallback (line 153):** The fallback to returning the single valley `point` when no acoustic candidates exist is the key fix for abutting sentences and is correctly implemented. Do not alter.

4. **`accepted_cut` orchestration (line 190):** The assignment of `VALLEY_FADE_S` specifically to valley cuts, followed by `neighbour_clear` validation, correctly prevents the more permissive timing from introducing audible artifacts. Architecture is sound. Do not alter.

5. **Test suite quality:** Both models independently rated tests at 8–9/10. The pattern of testing against the `v2f` reference and explicitly testing expected failure modes for documented reasons is exemplary. Do not reduce test coverage.

6. **Fail-closed error handling:** Consistent use of `None` returns from `accepted_cut` and `_accepted_cut_pair` correctly signals failure without raising exceptions. M12 FAIL CLOSED is upheld throughout. Do not alter.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Detail |
|-----|--------|--------|
| SENTENCE LAW — acoustic pause minimum | ⚠️ **NON-COMPLIANT (process)** | The 80ms rule has been functionally relaxed to 0ms. The code change may be *correct acoustically*, but it is **not ratified** in the Gospel. Technically non-compliant until documented. |
| SENTENCE LAW — no LLM involvement in boundary detection | ✅ COMPLIANT | Boundaries determined purely by transcript punctuation and acoustic envelope. |
| ONSET/TAIL — 80ms lead/tail minimum | ⚠️ **NON-COMPLIANT (process)** | Two-tiered rule introduced without Gospel documentation. Same class of issue. |
| SELECTION LOCK — no LLM selection | ✅ COMPLIANT | Cut selection is purely acoustic/algorithmic. |
| M12 FAIL CLOSED | ✅ COMPLIANT | All failure paths return None; no silent exception swallowing detected. |

**Final Law Determination:** The feature is **not fully law-compliant in its current state** due to two unratified law relaxations. The underlying acoustic logic is likely sound, but the governance process is broken. Compliance is restored the moment the Gospel is updated and approved.

---

## SECURITY CONSENSUS

No security vulnerabilities were identified by either model. GPT-4o gave Security 8/10; Gemini did not explicitly score it but raised no concerns. The following observations stand:

- No external inputs flow into the cut logic without prior JSON parsing and type validation.
- No file paths are constructed from user-controlled strings in the reviewed code.
- No network calls or authentication are involved in the pipeline functions.

**Security verdict: No blocking issues. No action required.**

---

## WORLD-CLASS GAP CONSENSUS (2+ models mentioned)

### WCG-1 — Governance artifact as source of truth (both models)
A truly world-class system treats its "Gospel" or law document as the **authoritative specification** that code implements, not the other way around. Currently, the code has outrun the documentation. The gap: any engineer reading the Gospel believes the 80ms rule is in force; any engineer reading the code sees it has been superseded. This creates a two-source-of-truth problem that compounds over time. World-class systems require law documents to be updated *before* or *atomically with* the code change that re-calibrates them.

### WCG-2 — Self-documenting constants (both models, via U3 and UNIQUE-1)
Constants like `VALLEY_FADE_S = 2 / 24` and parameters like `cut_in_fade_ms` with no docstring represent a pattern of implicit knowledge. World-class audio pipelines document every timing constant with its unit, its derivation, and the reference that validated it (e.g., `# validated against v2f reference, session 2026-11-01`). This makes the system auditable without requiring institutional memory.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Update `PULSE_SENTENCE_LAW_GOSPEL.md` to formally document: (1) relaxation of `PAUSE_MIN_S` from 80ms to 0ms with valley-cut rationale, (2) two-tiered ONSET/TAIL rule with 80ms preserved for file head/hook and 0ms for internal cuts, (3) authorizing decision/reference | `docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md` | both | Without this, the feature implements unratified law changes. Future audits will correctly flag this as a defect. Code cannot be in production while the governing document contradicts it. |
| **P1 HIGH** | Resolve `VALLEY_FADE_S` unit ambiguity: determine if intended duration is ~83ms (2 video frames at 24fps) or ~20ms (2 audio hops at 10ms). Rewrite as a self-documenting expression (e.g., `VALLEY_FADE_S = 2 * HOP_S` or `VALLEY_FADE_S = 2 / 24`) with an explicit comment. Validate against `v2f` reference audio output. | `pipeline/sentence_law.py:39` | gemini (unique, but high credibility) | A factor-of-4 error in valley fade duration will cause audible artifacts on every abutting-sentence cut. This is a correctness risk, not just hygiene. |
| **P2 MEDIUM** | Add docstring to `prerender_clips` documenting all parameters, units (ms), source (`cuts_final.json`), and defaults | `pipeline/run_isolated.py:5–13` | both | Maintainability: data-driven parameters with no documentation are a future defect waiting to happen. |
| **P2 MEDIUM** | Add inline comment to `gate_g17_prepared` at the `if cid == "hook":` branch explicitly stating the D1 fix rationale and the two-tiered rule | `pipeline/sentence_law.py:266` | both | Without this comment, future readers will not understand why the hook receives stricter treatment, creating a deletion risk during refactors. |
| **P2 MEDIUM** | Spot-check test coverage for `find_valley` failure modes and `accepted_cut` returning `None` from valley paths; add parametric tests if gaps exist | `tests/` | gpt4o (unique) | New code paths require explicit test coverage. Gemini's high test score suggests this may already be covered — verify before adding. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY in current state. Two hard blockers must be resolved.**

The core acoustic logic of this feature is sound and well-implemented. The `find_valley` / `neighbour_clear` / `accepted_cut` pipeline is a correct and carefully defended solution to the abutting-sentences problem. Test quality is high. Security is clean.

However, two blockers prevent merge:

1. **BLOCKER 1 (P0):** The Gospel document has not been updated to ratify the relaxation of the SENTENCE LAW 80ms acoustic pause rule and the ONSET/TAIL two-tiered lead rule. The code currently implements laws that are not written down anywhere authoritative. This is a governance failure that makes the feature non-compliant by definition, regardless of whether the acoustic logic is correct.

2. **BLOCKER 2 (P1):** The `VALLEY_FADE_S` constant contains a unit ambiguity (`2 / 24` — video frames or audio frames?) that could represent a 4× duration error on every valley cut. This must be verified against the `v2f` reference and corrected before the feature is trusted in production.

Once these two items are resolved and `regression_test.sh` shows zero FAILs, the feature is ready for production merge.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The feature was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Update PULSE_SENTENCE_LAW_GOSPEL.md to formally document:
  (1) Relaxation of PAUSE_MIN_S from 80ms to 0ms — acoustic envelope minima
      ("valleys") are now valid cut points when no silent pause exists;
      rationale: enables clean cuts on abutting sentences (v2f calibration).
  (2) Two-tiered ONSET/TAIL rule: LEAD_MIN_S/TAIL_MIN_S = 80ms for file heads
      and the hook clip; 0ms permitted for internal sentence cuts (D1 fix).
  (3) Authorizing decision reference (ticket/session date).
  | docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md | models: both |
  | Unratified law change — Gospel contradicts code until this is done.

P1 HIGH | Resolve VALLEY_FADE_S unit ambiguity at pipeline/sentence_law.py:39.
  Current value: VALLEY_FADE_S = 2 / 24  (comment says "2-frame audio fade")
  Problem: denominator 24 implies 24fps VIDEO frames (~83ms), but audio hop
  HOP_S = 10ms makes "2 audio frames" = 20ms — a 4x difference.
  Action: listen-test against v2f reference. Rewrite as self-documenting:
    Option A (if 20ms): VALLEY_FADE_S = 2 * HOP_S  # 2 audio hops → 20ms
    Option B (if 83ms): VALLEY_FADE_S = 2 / 24  # 2 video frames at 24fps → ~83ms
  Add inline comment citing the reference that validated the chosen value.
  | pipeline/sentence_law.py:39 | models: gemini | correctness risk.

P2 MEDIUM | Add complete docstring to prerender_clips() explaining:
  - cut_in_fade_ms (float, milliseconds, source: cuts_final.json, default 20ms)
  - cut_out_fade_ms (float, milliseconds, source: cuts_final.json, default 30ms)
  - Behaviour when no cut table entry exists (defaults apply)
  | pipeline/run_isolated.py:5-13 | models: both | maintainability.

P2 MEDIUM | Add inline comment at gate_g17_prepared line 266 on the
  `if cid == "hook":` branch:
  # D1 fix: hook and file head begin playback; apply strict 80ms head-lead rule.
  # Internal sentence cuts are exempt (two-tiered ONSET/TAIL rule, see Gospel).
  | pipeline/sentence_law.py:266 | models: both | deletion-risk during refactors.

P2 MEDIUM | Spot-check test coverage: verify tests exist for find_valley()
  failure modes and accepted_cut() returning None from valley paths.
  If gaps exist, add targeted parametric tests. If already covered, skip.
  | tests/ | models: gpt4o | new code paths require explicit coverage.

VALIDATED — do NOT touch (all models confirmed excellent):
  - find_valley() logic (sentence_law.py:75) — correct zero-duration pause return
  - neighbour_clear() dB-space fade model with np.clip (sentence_law.py:160)
  - cut_candidates() fallback to valley point (sentence_law.py:153)
  - accepted_cut() VALLEY_FADE_S assignment + neighbour_clear validation (sentence_law.py:190)
  - G16 gate re-verification using neighbour_clear on rendered cut (sentence_law.py:444)
  - gate_g17_prepared two-tiered enforcement structure (sentence_law.py:266)
  - Fail-closed None-return pattern throughout (M12 COMPLIANT — do not alter)
  - Test suite overall structure and v2f reference regression approach

After implementing all P0 and P1 items, and any P2 items deemed appropriate:

bash regression_test.sh

Confirm zero FAILs before committing.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements

- Ratify SENTENCE LAW 80ms→0ms valley relaxation in Gospel
- Ratify two-tiered ONSET/TAIL rule in Gospel
- Resolve VALLEY_FADE_S unit ambiguity (P1)
- Add prerender_clips docstring
- Add gate_g17_prepared D1-fix comment"

git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Gemini — 2-Sentence Justification

Gemini delivered the highest-quality analysis across both cycles: in Cycle 1 it correctly identified the precise mechanism of the valley fallback, the dB-space fade model in `neighbour_clear`, and the semantic significance of `VALLEY_FADE_S` as a distinct fade regime — depth that GPT-4o did not match. In Cycle 2 Gemini demonstrated superior self-correction by explicitly articulating *why* its own Cycle 1 review was insufficient (conflating code implementation with law re-baselining), producing the clearest and most actionable statement of the governance gap that became the audit's central finding.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: risk severity → breadth of impact → implementation effort (ascending).

---

### P0 — BLOCKING (must resolve before merge)

**P0-1 | Gospel ratification of SENTENCE LAW re-baselining**
*Finding U1 — unanimous 2/2*
- File: `docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md`
- Action: Add a versioned section stating explicitly: (a) old rule — 80 ms minimum acoustic pause required; (b) new rule — 0 ms permitted at envelope valley minima; (c) rationale — `v2f` calibration, abutting-sentence coverage; (d) authorizing ticket/decision reference (`DEC-10`).
- Acceptance criterion: PR cannot land until this document change is in the same commit and a second reviewer has signed off on the Gospel section specifically.

**P0-2 | Gospel ratification of ONSET/TAIL 80 ms → 0 ms relaxation**
*Finding U2 — unanimous 2/2*
- File: `docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md`
- Action: Document the ONSET/TAIL lead/tail minimum change with the same four-part structure as P0-1 (old rule, new rule, rationale, ticket). This is a separate law clause and must be a separate paragraph.
- Acceptance criterion: Same as P0-1 — co-located commit, explicit second-reviewer sign-off.

---

### P1 — HIGH (resolve before release, non-blocking to merge if P0 satisfied)

**P1-1 | Missing docstring on modified `prerender_clips`**
*Finding U3 — unanimous 2/2*
- File: `run_isolated.py`, function `prerender_clips` (lines 5–13)
- Action: Add a docstring that documents: purpose, all parameters including the new `cut_in_fade_ms` and `cut_out_fade_ms` with units and defaults (20 ms / 30 ms), return value, and a note that defaults are data-driven from the Gospel.
- Acceptance criterion: `pydocstyle` or equivalent linter passes on this function; docstring reviewed by a second engineer.

**P1-2 | Edge-case test coverage for valley cuts at true zero-gap boundaries**
*Finding — Gemini Cycle 1, confirmed GPT-4o Cycle 2*
- File: `tests/test_sentence_law.py`
- Action: Add at minimum two parameterized test cases: (a) two words with no silent frames between them — assert `accepted_cut` selects the envelope minimum and assigns exactly `VALLEY_FADE_S`; (b) a word pair where `neighbour_clear` should veto the valley cut — assert return is `None` and no audible artefact threshold is breached.
- Acceptance criterion: Both cases in CI; coverage report shows `neighbour_clear` veto branch is exercised.

---

### P2 — MEDIUM (schedule within sprint)

**P2-1 | Inline comment clarifying `VALLEY_FADE_S` as a distinct fade regime**
*Finding — Gemini Cycle 1*
- File: `pipeline/sentence_law.py`, near `VALLEY_FADE_S` definition
- Action: Add a comment explaining that this constant (2-frame fade) is intentionally shorter than the standard `cut_in_fade_ms` default, that it applies only to valley cuts where `neighbour_clear` has already validated audibility, and that changing it requires Gospel approval.
- Acceptance criterion: Comment present and survives code review without objection.

**P2-2 | `boundary_geometry` inversion fallback — add assertion or log**
*Finding — Gemini Cycle 1*
- File: `pipeline/sentence_law.py`, lines 70–71
- Action: When the `word_gap` is inverted and falls back to `point`, emit a `logging.warning` with the word identifiers and the inverted gap magnitude. This makes the silent fallback observable in production logs without changing behavior.
- Acceptance criterion: Warning appears in test log output when an inverted-gap fixture is exercised.

**P2-3 | Law Compliance score remediation tracking**
*Process finding — consensus score 6.5/10*
- Action: Open a tracked ticket (linked to this audit) targeting a re-score of Law Compliance to ≥ 8/10 after P0-1 and P0-2 land. Schedule a follow-up audit of `PULSE_SENTENCE_LAW_GOSPEL.md` completeness within 2 sprints of merge.
- Acceptance criterion: Ticket exists, is assigned, has a due date no later than 2 sprints post-merge.

---

### P3 — LOW (backlog, do not block sprint)

**P3-1 | Security/input validation audit of new data-driven fade parameters**
*Finding — GPT-4o Cycle 1 (scored 8/10, no specific issue found)*
- Action: Confirm that `cut_in_fade_ms` and `cut_out_fade_ms` are validated against sane bounds (e.g., 1 ms ≤ value ≤ 500 ms) before being passed to `prerender_clips`. Add a `ValueError` guard if not present.
- Acceptance criterion: Bounds check present and unit-tested with an out-of-range value.

**P3-2 | Grok re-audit on next cycle**
*Process finding — Grok failed due to budget exhaustion*
- Action: Re-include Grok-3 in the next audit cycle for this feature area. If budget constraints recur, downgrade Grok to Cycle 1 only and use its output as a tiebreaker rather than a primary auditor.
- Acceptance criterion: Audit plan for the next cycle documents Grok's role and budget allocation explicitly.