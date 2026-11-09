# CONSENSUS REPORT — TRACK-A-D1-D3 — CYCLE 1
Generated: 2026-11-09 01:33
Models: grok (+2 failed)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| D1 — Date Grounding | ❌ Failed | ❌ Failed | 98/100 | 98/100 (single-model) |
| D2 — Two Verified Windows | ❌ Failed | ❌ Failed | 98/100 | 98/100 (single-model) |
| D3 — Boundary Repair | ❌ Failed | ❌ Failed | 98/100 | 98/100 (single-model) |
| Fail-Closed Paths | ❌ Failed | ❌ Failed | 98/100 | 98/100 (single-model) |
| Test Coverage | ❌ Failed | ❌ Failed | 98/100 | 98/100 (single-model) |
| **Overall** | ❌ N/A | ❌ N/A | **98/100** | **98/100 ⚠️ LOW CONFIDENCE** |

> ⚠️ **CONFIDENCE ADVISORY:** Only 1 of 3 models returned a usable review. Gemini 2.5 Pro and GPT-4o both failed due to invalid/disabled API keys. This consensus carries **low statistical confidence** — findings below reflect a single-model opinion, not true multi-model consensus. A Cycle 2 re-run with valid API keys is **strongly recommended** before treating any section as "unanimous."

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

> With only one model completing review, "unanimous" means "uncontested by any model that reviewed the code." These findings carry Grok's full confidence but lack independent verification.

**None flagged as critical, high, medium, or low severity.** Grok's `<critical>`, `<high>`, `<medium>`, and `<low>` sections were all empty. No unconditional fixes are mandated by the available review.

---

## MAJORITY FINDINGS (2 of 1 models agree)

**Not applicable.** Majority threshold (2+ models) cannot be reached with only 1 successful reviewer. No items qualify.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

The following observation was made exclusively by Grok. It represents the only substantive finding from this cycle:

### UI-1 — Untested `_parse_ts` branch on non-ISO strings

**What it is:** In the D1 implementation, `_parse_ts` handles non-ISO strings that still happen to parse successfully under Python's `fromisoformat` after a `Z → +00:00` replacement. This code path is exercised in production but not covered by any test.

**File/location:** `story_semantics.py` — `_parse_ts` function (exact line not specified, inferred from context of lines 391–432).

**Grok's assessment:** "Harmless, does not affect D1 logic."

**Synthesizer's assessment:** → **INVESTIGATE FURTHER before dismissing.**

Grok calls it harmless, but the reasoning is worth scrutinizing:
- If `_parse_ts` silently accepts a malformed-but-accidentally-parseable timestamp, it could allow a date with incorrect semantics (e.g., a local-time string being treated as UTC after Z-replacement) to influence the `grounded_event_date()` authority chain.
- D1's correctness depends on timestamp authority being unambiguous. A timestamp that "accidentally" parses is not the same as a timestamp that is structurally valid.
- The fact that this branch is untested means no regression protection exists if `fromisoformat` behavior changes across Python versions (it has changed between 3.7, 3.10, and 3.11).

**Recommendation:** Add a targeted negative test: pass a string that contains no `Z` or timezone info, confirm `_parse_ts` either raises or returns `None` rather than silently accepting. If the function accepts it, add an explicit format guard. Low effort, eliminates ambiguity.

---

## CONFLICTS (models disagree — your tiebreaker)

**None.** Only one model reviewed; no contradictions are possible. If Gemini and GPT-4o had reviewed and disagreed with Grok's 98/100 verdict, a tiebreaker would be recorded here.

**Standing advisory:** A score of 98/100 from a single model should be treated with the same skepticism as a self-review. Historical patterns show that GPT-4o and Gemini frequently surface different classes of issues than Grok (GPT-4o tends toward API contract and interface concerns; Gemini tends toward edge-case reasoning and type safety). The absence of their input is a gap, not a confirmation.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> With only one reviewer, "validated" means "Grok found no issues here." Do NOT treat these as locked — they need independent verification in Cycle 2. That said, do not gratuitously refactor them before re-audit.

The following areas received explicit positive confirmation from Grok and **no negative findings**:

1. **D1 — Authority hierarchy in `grounded_event_date()`** (`story_semantics.py:391–432`)
   Source publish metadata correctly takes precedence over model date. Model date is only a tiebreaker. `model_date_discarded=True` is set appropriately. 72h + 7d window unchanged and correct.

2. **D1 — `_story_published()` null safety** (`editorial_select.py:84–86`)
   Returns `None` on missing or unparseable fields. Never treats missing data as fresh. No path lets a stale story through.

3. **D1 — `transcript_currentness()` strictness** (`story_semantics.py:435–457`)
   Requires verified `CURRENT_EVENT` evidence. No shortcut paths.

4. **D2 — `second_verified_quote()` isolation** (`editorial_select.py:291–311`)
   Independent `adjudicate()` calls on non-overlapping excerpts. `counted_as_same_event` enforced. Malformed output returns `(None, reason)` — no window produced.

5. **D2 — `MAX_VERIFIED_QUOTES_PER_VIDEO=2` hard cap** (`editorial_select.py:349–351, 770–773`)
   Passage exclusion, overlap deduplication, and the constant together guarantee no more than two windows per video under any input.

6. **D3 — `repair_window()` gate** (`editorial_select.py:314–362, 822`)
   Only `BOUNDARY_FAULTS` trigger repair. Floor constants (4.0/3.5 s) and duration ranges (8–12 s / 13–25 s) are fixed. Per-sentence `on_event` verification closes direction on failure. Post-repair re-rating rejects anything still below floor.

7. **Fail-closed exception handling**
   All exception paths produce recorded rejections (`LLMParseError`, missing data, `None` verdicts). No silent pass-throughs.

8. **Test suite structure** (`TestD2TwoVerifiedWindowsPerVideo`, `TestD3BoundaryRepair`, `TestE9TranscriptCurrentness`, `TestE9Orchestration`)
   Positive and negative cases exist for each rule. Reversion would cause test failures.

---

## LAW COMPLIANCE CONSENSUS

**Available from 1 model only. Treat as preliminary.**

| Law / Rule | Status | Confidence |
|---|---|---|
| Stale story law (72h + 7d window) | ✅ Compliant | Single-model |
| Source authority primacy (D1) | ✅ Compliant | Single-model |
| Two-window cap per video (D2) | ✅ Compliant | Single-model |
| Non-overlapping excerpt isolation (D2) | ✅ Compliant | Single-model |
| Repair-only-on-boundary-faults (D3) | ✅ Compliant | Single-model |
| Floor/duration constant enforcement (D3) | ✅ Compliant | Single-model |
| Fail-closed on all exception paths | ✅ Compliant | Single-model |

**Final determination (provisional):** No law violations identified by the available reviewer. Requires independent confirmation from Gemini and GPT-4o before this determination is considered final.

---

## SECURITY CONSENSUS

**Available from 1 model only.**

No security issues were flagged by Grok. The fail-closed architecture (all malformed LLM output produces rejection, never a pass) is the primary security-relevant property and was confirmed correct.

**Unverified gaps** (Gemini and GPT-4o not available to assess):
- Prompt injection resilience in `adjudicate()` calls was not specifically assessed by any model in this cycle.
- API key management for the LLM calls within the audited code was not evaluated (separately, the audit infrastructure itself had two invalid API keys — this should be treated as an operational security concern).

**Priority order:**
1. ⚠️ Fix audit infrastructure API keys before Cycle 2 (operational, not code security)
2. 🔍 Consider adding prompt injection test cases to `adjudicate()` in a future cycle (not flagged as present risk, but unassessed)

---

## WORLD-CLASS GAP CONSENSUS

**Threshold: 2+ models must have mentioned an item. With only 1 model, nothing qualifies.**

> This section is intentionally empty. Grok mentioned no world-class gaps. Without corroboration from at least one other model, no gap can be listed here with intellectual honesty.

**What Grok implicitly confirmed is NOT a gap:** The core architecture — authority-based date grounding, hard-capped quote windows, fault-gated repair, and fail-closed exceptions — was reviewed and found complete. If GPT-4o or Gemini had reviewed, they might have surfaced gaps in areas Grok tends not to emphasize (type contract enforcement, async safety, observability/logging completeness). These remain unknown.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | *(none)* | — | — | No critical issues found |
| **P1 HIGH** | Re-run Cycle 1 with valid Gemini and GPT-4o API keys before treating this audit as complete | Infra / `.env` / key management | Synthesizer | 2 of 3 models failed; single-model 98/100 is unverified and cannot support a production merge decision alone |
| **P2 MEDIUM** | Add negative test for `_parse_ts` on non-ISO strings that accidentally parse after Z-replacement | `story_semantics.py` — `_parse_ts` | Grok (unique) | Eliminates untested branch; guards against Python version behavior changes in `fromisoformat`; ensures D1 timestamp authority chain has no silent ambiguity |

---

## CYCLE 1 VERDICT

**⚠️ CONDITIONAL — NOT READY FOR MERGE WITHOUT CYCLE 2**

The code quality as assessed by Grok is excellent (98/100, no issues above "low" severity). The implementation of D1, D2, and D3 appears correct, well-tested, and fail-closed. Under normal multi-model conditions, this would likely be a straightforward MERGE recommendation.

**However:** Two of three independent auditors were unavailable due to API key failures. A consensus audit with 33% participation is not a consensus audit — it is a single-model review wearing consensus framing. Protocol Pulse's editorial standards demand higher confidence than this for a production merge.

**Required before merge:**
1. Fix Gemini and GPT-4o API credentials.
2. Run Cycle 2 (which becomes the true Cycle 1 for GPT-4o and Gemini, and a confirmation pass for Grok).
3. If Cycle 2 is also unanimous MERGE with no P0/P1 items, proceed.

**If timeline pressure is absolute and Cycle 2 is not feasible:** The Grok 98/100 MERGE verdict can be used as a qualified approval with the explicit acknowledgment that independent verification was unavailable. Document this in the merge commit.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/TRACK_A_EDITORIAL_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/track-a-d1-d3_CONSENSUS_C1.md.

This is the SECOND PASS for track-a-d1-d3.
The first build was reviewed by 1 of 3 independent AI models across 1 cycle
(Gemini 2.5 Pro and GPT-4o were unavailable due to API key failures;
Grok-3 completed review at 98/100 with MERGE verdict).

NOTE: This pass carries LOW CONFIDENCE due to single-model audit.
A Cycle 2 re-audit with all three models is recommended after this pass.

Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | None — no critical issues found.

P1 HIGH | Re-run Cycle 1 with valid Gemini and GPT-4o API keys.
         This is an infrastructure action, not a code change.
         Ensure .env / key management is corrected before treating
         this audit as complete for production merge purposes.

P2 MEDIUM | Add negative test for `_parse_ts` on non-ISO strings that
            accidentally parse after Z-replacement.
            File: story_semantics.py — _parse_ts function.
            Test: pass a string with no timezone info and no Z suffix;
            confirm _parse_ts returns None or raises, NOT a silently
            accepted datetime. If function accepts it, add an explicit
            format guard before the fromisoformat call.
            Rationale: untested branch; Python fromisoformat behavior
            has changed across 3.7/3.10/3.11; D1 date authority chain
            must have zero ambiguity.

VALIDATED (do NOT touch — Grok confirmed excellent, pending verification):
- grounded_event_date() authority hierarchy (story_semantics.py:391-432)
- _story_published() null safety (editorial_select.py:84-86)
- transcript_currentness() strictness (story_semantics.py:435-457)
- second_verified_quote() isolation and adjudicate() independence (editorial_select.py:291-311)
- MAX_VERIFIED_QUOTES_PER_VIDEO=2 hard cap (editorial_select.py:349-351, 770-773)
- repair_window() BOUNDARY_FAULTS gate and floor/duration constants (editorial_select.py:314-362, 822)
- Fail-closed exception handling on all paths
- TestD2TwoVerifiedWindowsPerVideo, TestD3BoundaryRepair, TestE9TranscriptCurrentness, TestE9Orchestration test structure

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(track-a-d1-d3): post-audit pass — P2 _parse_ts branch coverage + consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

*Synthesizer note: The two API key failures are recorded as audit infrastructure incidents. Before the next cycle, validate all three model credentials in a dry-run call before submitting the full codebase for review. The cost of a failed audit cycle (delayed merge, reduced confidence, incomplete findings) substantially exceeds the cost of a 5-second credential check.*