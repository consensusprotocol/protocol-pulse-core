# CONSENSUS REPORT — TRACK-A-D1-D3 — CYCLE 2
Generated: 2026-11-09 01:35
Models: Grok (+2 failed — GPT-4o: invalid API key, Gemini: invalid API key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| D1 — Date Grounding | N/A | N/A | 95 | 95 |
| D2 — Two Verified Windows | N/A | N/A | 98 | 98 |
| D3 — Boundary Repair | N/A | N/A | 98 | 98 |
| Fail-Closed Paths | N/A | N/A | 98 | 98 |
| Test Coverage | N/A | N/A | 92 | 92 |
| **Overall** | **N/A** | **N/A** | **95** | **95** |

> ⚠️ **Quorum Warning:** Only 1 of 3 models returned valid output. GPT-4o and Gemini 2.5 Pro failed due to invalid API keys. All consensus classifications below reflect single-model findings — confidence bands are wider than a full 3-model quorum would provide. Treat "unanimous" and "majority" labels as artifacts of the available data, not genuine multi-model agreement. Human reviewer should weight findings accordingly.

---

## UNANIMOUS FINDINGS (all 1 available models agree — implement unconditionally)

### U1 — Untested `_parse_ts` helper branch
**What it is:** The `_parse_ts` helper (and by extension `_story_published`) contains a code path where a non-ISO string containing `Z` is transformed via `Z → +00:00` replacement and then passed to `fromisoformat`. If that replacement produces a string that `fromisoformat` accepts (but whose timezone semantics are ambiguous — local time mis-labeled as UTC), the result is silently accepted rather than rejected. This path is exercised in production but has no unit test coverage.

**Files/lines:**
- `pipeline/editorial_select.py:71` — `_parse_ts` helper
- `pipeline/story_semantics.py:399` — caller in `grounded_event_date`

**What to change:** Add a parametrized unit test for `_parse_ts` covering four cases:
1. Valid ISO with `Z` suffix → parses correctly as UTC
2. Valid ISO with explicit offset (e.g. `+05:30`) → parses correctly
3. Non-ISO string that still passes `fromisoformat` after `Z → +00:00` replacement → verify behavior is intentional (either assert it returns `None` with a stricter guard, or assert it is accepted and document why)
4. Completely invalid/garbage input → assert returns `None`

**Risk if skipped:** Low in isolation (D1 authority chain has layered `None` guards), but represents a gap in the coverage promise made by the test suite and would mask a future regression if `_parse_ts` is modified.

---

## MAJORITY FINDINGS (2 of 1 available models agree)

*Not applicable — only one model returned output. No majority threshold can be computed. All findings originate from Grok's Cycle 1 and Cycle 2 combined analysis.*

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `fromisoformat` + Z-replacement may accept ambiguous timestamps
**Source:** Grok Cycle 2, new finding
**Observation:** A timestamp string like `2026-11-09T01:35:00Z` becomes `2026-11-09T01:35:00+00:00` after replacement — correct. But a malformed string like `2026-11-09 01:35:00Z` becomes `2026-11-09 01:35:00+00:00`, which Python 3.11+ `fromisoformat` will accept (Python 3.11 expanded the set of formats accepted). The resulting datetime object has UTC timezone attached, but the original string was arguably malformed. If the caller expected `None` on malformed input, it gets a datetime instead.

**Assessment: Investigate further.**
- Check which Python version the production runtime uses. If Python ≥ 3.11, the broader `fromisoformat` acceptance is real and the test case is non-trivial.
- If the intent is "only accept strict ISO 8601 with Z or offset," add a stricter regex pre-check before calling `fromisoformat`, and add the test case.
- If the intent is "accept anything `fromisoformat` accepts after Z-replacement," document that explicitly and add a test asserting the datetime is UTC-aware.

**Priority:** P2 MEDIUM (no functional bug demonstrated, but behavior is undocumented and could become a bug on Python version change).

### UI2 — Cycle 1's untested `_parse_ts` branch was self-identified but not escalated
**Source:** Grok Cycle 1 (noted as "minor untested branch"), Grok Cycle 2 (escalated to P2)
**Observation:** Grok correctly escalated this from a footnote to a named finding in Cycle 2. This is the same as U1/UI1 — no additional action needed beyond what is described there.

**Assessment: Covered by U1.**

---

## CONFLICTS (models disagree — your tiebreaker)

**No conflicts.** Only one model returned output across Cycle 2. Grok's Cycle 1 and Cycle 2 outputs are internally consistent. No tiebreaker required.

The only intra-Grok nuance: Cycle 1 called the `_parse_ts` gap "harmless" and left it unscored; Cycle 2 downgraded Test Coverage from 95 → 92 and Overall from 98 → 95. This is not a conflict — it is appropriate escalation based on closer analysis.

**Tiebreaker ruling (for the record):** The Cycle 2 position is correct. Uncovered production branches in a date-authority helper are not harmless by definition; they are a gap in the safety net. P2 is the right priority.

---

## VALIDATED STRENGTHS (all available models agree — do NOT touch in second pass)

The following have been confirmed correct across both cycles by the available model:

**VS1 — D1 Date Authority Chain**
`grounded_event_date()` (story_semantics.py:391-432) correctly prioritizes `source_published` metadata over model date, marks `model_date_discarded=True` when model date is older, and treats missing/unparseable `source_published` as `None` (never fresh). The 72h + 7d window and `STALE_GRACE_DAYS=7` constant are correct. Do not modify this logic.

**VS2 — D2 Two-Window Enforcement**
`second_verified_quote()` (editorial_select.py:291-311) runs independent `adjudicate()` on non-overlapping excerpts, enforces `MAX_VERIFIED_QUOTES_PER_VIDEO=2` via passage exclusion + overlap dedupe (lines 349-351, 770-773), and returns `(None, reason)` on any failure. Never produces more than two windows per video. Do not modify this logic.

**VS3 — D3 Boundary Repair Gate**
`repair_window()` (editorial_select.py:314-362) is correctly gated on `clip_fault in BOUNDARY_FAULTS` only. Floor constants (4.0/3.5 s), duration ranges (8-12 s / 13-25 s), per-sentence `on_event` verification, and final re-rating before acceptance are all correct. Off-topic/other/unspecified faults are never repaired. Do not modify this logic.

**VS4 — Fail-Closed Exception Handling**
All exception paths (LLMParseError, missing data, `None` verdicts, malformed LLM output) produce recorded rejections and never produce a window, count, or pass-through. No regressions outside D1-D3 were found. Do not change exception handling patterns.

**VS5 — Core Test Suite**
TestD2TwoVerifiedWindowsPerVideo, TestD3BoundaryRepair, TestE9TranscriptCurrentness, TestE9Orchestration all cover positive and negative cases and would fail on reversion. Do not remove or weaken these tests.

**VS6 — `transcript_currentness()` Requirement**
Still requires verified `CURRENT_EVENT` evidence (story_semantics.py:435-457). No path bypasses this. Do not relax.

---

## LAW COMPLIANCE CONSENSUS

Based on the single available model's analysis across two cycles:

| Law / Rule | Status | Notes |
|---|---|---|
| D1 — Source-published date takes authority | ✅ COMPLIANT | `authority="source publish metadata"` set correctly; model date is tiebreaker only |
| D1 — Stale stories never pass | ✅ COMPLIANT | `_story_published()` returns `None` on missing/unparseable; 72h+7d window unchanged |
| D2 — Max 2 verified windows per video | ✅ COMPLIANT | `MAX_VERIFIED_QUOTES_PER_VIDEO=2` enforced at two points |
| D2 — Windows must be independently adjudicated | ✅ COMPLIANT | Non-overlapping excerpts, separate `adjudicate()` calls |
| D3 — Repair only on BOUNDARY_FAULTS | ✅ COMPLIANT | Gate is strictly `clip_fault in BOUNDARY_FAULTS` |
| D3 — Repaired window must re-rate above floor | ✅ COMPLIANT | Re-rating enforced; rejected if still below floor |
| Fail-closed on all error paths | ✅ COMPLIANT | No silent pass-throughs found |
| `transcript_currentness()` requires CURRENT_EVENT | ✅ COMPLIANT | Unchanged from pre-D1-D3 gospel |

**No law violations identified.** One compliance gap risk: the `_parse_ts` ambiguous-acceptance behavior (UI1) is not a current violation but could become one if Python version changes make `fromisoformat` more permissive or if `_parse_ts` is reused in a context without the downstream `None` guards.

---

## SECURITY CONSENSUS

No security issues were flagged by the available model. The following are confirmed non-issues:

- **LLM injection via transcript content:** Fail-closed adjudication means malformed LLM output never produces a window. ✅
- **Timestamp manipulation via `source_published`:** `_story_published` treats missing/unparseable as `None`; a crafted timestamp that makes `fromisoformat` succeed could advance a stale story — this is the UI1 risk and is mitigated by the downstream `None` guards and the fact that `source_published` is derived from trusted internal fields (`generated_at`, `freshness_minutes`, video `published_at`), not from untrusted user input. **Low security risk, but document the trust assumption.**
- **Window boundary manipulation:** `repair_window()` only extends by sentence-verified content; floor and duration checks are enforced by constants. ✅

**Security priority order (for the record):**
1. Document trust assumption for `source_published` data origin (informational, not a code change)
2. `_parse_ts` stricter validation (P2 — see action plan)

---

## WORLD-CLASS GAP CONSENSUS

*Threshold: 2+ models must have mentioned the item. With only 1 model available, this section reflects single-model findings that represent genuine product quality gaps, clearly labeled.*

> ⚠️ No item in this section meets the 2-model threshold due to API failures. Items below are single-model observations included for completeness.

**WCG1 — `_parse_ts` coverage (Grok, both cycles)**
A world-class editorial pipeline's date-authority helper should be fully unit-tested with deterministic inputs, including edge cases around format acceptance. The current gap is small but inconsistent with the otherwise comprehensive test suite.

**WCG2 — Python version runtime assumption undocumented (Grok Cycle 2)**
The `fromisoformat` behavior difference between Python 3.10 and 3.11 is a silent runtime dependency. World-class codebases either pin this in CI or add an explicit format validator. Neither is present.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | None identified | — | — | No critical issues found across 2 cycles
```

```
P1 HIGH | None identified | — | — | No high issues found across 2 cycles
```

```
P2 MEDIUM | Add unit tests for _parse_ts helper | pipeline/editorial_select.py:71, pipeline/story_semantics.py:399 | models: Grok (both cycles) | Uncovered production branch in date-authority helper; covers 4 cases: Z-suffix ISO, offset ISO, non-ISO-but-accepted-after-Z-replacement, garbage input
```

```
P2 MEDIUM | Investigate + document fromisoformat Python-version behavior | pipeline/editorial_select.py:71 | models: Grok Cycle 2 | fromisoformat acceptance set differs between Python 3.10 and 3.11; either add strict pre-check regex or document the accepted format set and add a CI Python-version pin assertion
```

```
P3 LOW | Document trust assumption for source_published data origin | pipeline/story_semantics.py:391-432 | models: Grok (implied) | Add inline comment that source_published is derived from internal trusted fields only, not user input; clarifies security posture for future maintainers
```

---

## CYCLE 2 VERDICT

**Production-ready: YES, with one recommended condition before merge.**

**Summary:** After two full cycles of review (Cycle 1: Grok, Claude synthesis; Cycle 2: Grok — GPT-4o and Gemini unavailable due to API key failures), the core functional changes for D1, D2, and D3 are confirmed correct. All fail-closed guarantees hold. The test suite is comprehensive for the new rules. No P0 or P1 issues exist.

**The single absolute condition before merge:**
Add the `_parse_ts` unit test (P2 MEDIUM, U1 above). This is a 10-20 line addition to an existing test file and takes under 30 minutes. It is not a blocker for a hotfix deploy but should be completed before the next sprint closes.

**Confidence caveat:** This verdict is based on 1 of 3 intended models. The 2-model API failures mean the consensus confidence is lower than a full quorum would provide. If the team has access to a manual human review or a third model, a 15-minute spot-check of the `_parse_ts` behavior on the production Python version would eliminate the remaining uncertainty entirely.

**Recommended merge path:** Merge after `_parse_ts` test is added and `regression_test.sh` shows zero FAILs.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/TRACK_A_EDITORIAL_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/track-a-d1-d3_CONSENSUS_C2.md.

This is the FINAL PASS for track-a-d1-d3.
The first build was reviewed by 1 independent AI model across 2 cycle(s).
(GPT-4o and Gemini 2.5 Pro were unavailable due to API key failures.)
Implement every P0 and P1 item from the consensus (none exist).
Implement P2 items as described below.

PRIORITY ACTION PLAN:

P2 MEDIUM | Add unit tests for _parse_ts helper
  Files: pipeline/editorial_select.py:71, pipeline/story_semantics.py:399
  Add a parametrized test covering exactly four cases:
    1. Valid ISO string with Z suffix (e.g. "2026-11-09T01:35:00Z") → assert returns UTC-aware datetime
    2. Valid ISO string with explicit offset (e.g. "2026-11-09T01:35:00+05:30") → assert returns offset-aware datetime
    3. Non-ISO string that passes fromisoformat after Z→+00:00 replacement
       (e.g. "2026-11-09 01:35:00Z") → assert the returned value is UTC-aware AND
       add a comment documenting whether this is intentionally accepted or should be rejected;
       if the intent is strict ISO 8601 only, add a pre-check regex and assert this case returns None
    4. Completely invalid input (e.g. "not-a-date") → assert returns None
  Place test in the existing test file alongside TestE9TranscriptCurrentness or equivalent.

P2 MEDIUM | Document fromisoformat Python-version behavior
  File: pipeline/editorial_select.py:71
  Add an inline comment on the fromisoformat call noting:
    - Python 3.11+ accepts a broader set of ISO 8601 formats than 3.10
    - The function relies on this behavior intentionally [OR] add a strict pre-check if not intentional
    - The production runtime Python version should be pinned in CI (add to .python-version or pyproject.toml)
  If a strict format is desired, add: import re; guard with r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}' before fromisoformat

P3 LOW | Document source_published trust assumption
  File: pipeline/story_semantics.py:391-432
  Add a one-line inline comment near the top of grounded_event_date() stating:
    # source_published is derived exclusively from internal trusted fields
    # (generated_at, freshness_minutes, video published_at) — never from raw user input.
  This clarifies the security posture for future maintainers.

VALIDATED (do NOT touch — confirmed excellent across all available model reviews):
- grounded_event_date() logic (story_semantics.py:391-432): D1 authority chain is correct
- second_verified_quote() logic (editorial_select.py:291-311): D2 enforcement is correct
- repair_window() logic (editorial_select.py:314-362): D3 gate and floor checks are correct
- All exception/fail-closed paths: no silent pass-throughs exist
- TestD2TwoVerifiedWindowsPerVideo, TestD3BoundaryRepair, TestE9TranscriptCurrentness,
  TestE9Orchestration: do not remove or weaken these tests
- transcript_currentness() CURRENT_EVENT requirement (story_semantics.py:435-457): do not relax
- MAX_VERIFIED_QUOTES_PER_VIDEO=2 constant and enforcement points: do not change
- BOUNDARY_FAULTS gate in repair_window(): do not expand the fault set
- STALE_GRACE_DAYS=7 and 72h window: do not modify

After implementing:
  regression_test.sh must show zero FAILs.
  Verify the new _parse_ts test runs and passes (or, if case 3 is determined to be
  invalid input, verify it now returns None with the stricter guard in place).

git add -A && git commit -m "feat(track-a-d1-d3): post-audit pass — _parse_ts coverage + docs"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Grok

Grok provided the only valid, substantively complete analysis across both cycles, delivering accurate findings on D1-D3 that held up under self-review in Cycle 2, with specific line-number citations, concrete failure-mode descriptions, and a disciplined self-correction (downgrading D1 from 98→95 upon identifying the untested `_parse_ts` branch). GPT-4o and Gemini failed entirely due to API key errors, making Grok the sole model whose output can be evaluated — but notably, Grok's work was methodologically sound: it found issues others would have missed, grounded every claim in file/line evidence, and maintained fail-closed reasoning throughout.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by risk × likelihood of production impact. All items have file/line anchors.

---

### P1 — IMPLEMENT IMMEDIATELY
**Untested `_parse_ts` branch (U1)**
- **Risk:** A non-ISO timestamp containing `Z` survives `fromisoformat` after `Z → +00:00` substitution with ambiguous UTC semantics, silently polluting the D1 authority chain.
- **Files:** `pipeline/editorial_select.py:71` (`_parse_ts`), `pipeline/story_semantics.py:399` (caller)
- **Action:** Add a parametrized unit test covering all four cases enumerated in the consensus report:
  1. Valid ISO + `Z` suffix → UTC confirmed
  2. Valid ISO + explicit offset (e.g. `+05:30`) → parses correctly
  3. Non-ISO string that passes `fromisoformat` post-substitution → assert this returns `None`, not a live timestamp
  4. Completely unparseable string → assert `None`
- If case 3 currently returns a non-`None` value, harden `_parse_ts` with an explicit UTC-offset validation check before returning.

---

### P2 — IMPLEMENT BEFORE NEXT RELEASE
**D1 Date Grounding — confidence band widened (single-model quorum)**
- **Risk:** Consensus score of 95 reflects one model; no cross-model challenge occurred. The `model_date_discarded=True` logic (story_semantics.py:399-402) and 72h+7d window (`STALE_GRACE_DAYS=7`) are correct per Grok's analysis, but the tiebreaker path (lines 408, 422) has not been adversarially tested by a second model.
- **Action:** When API keys are restored, re-run Gemini and GPT-4o specifically against the `grounded_event_date()` tiebreaker path and the `_story_published()` None-on-missing-fields path. Do not treat the 95 score as hardened until quorum is achieved.

---

### P3 — IMPLEMENT IN CURRENT SPRINT
**Test coverage gap — `_story_published` None-return paths**
- **Risk:** `_story_published()` (editorial_select.py:84-86) returns `None` on missing or unparseable fields; this is the safety net for the `_parse_ts` vulnerability above. The None-path is described in Grok's analysis but its test coverage is implicit, not explicit.
- **Action:** Add explicit unit tests asserting `_story_published()` returns `None` for: (a) missing `source_published` key, (b) `source_published: null`, (c) unparseable date string, (d) empty string. These are fast, zero-dependency tests.

---

### P4 — IMPLEMENT BEFORE QUORUM RESTORED
**Restore 3-model quorum for all subsystems**
- **Risk:** All "unanimous" and "majority" labels in this report are artifacts of a 1-of-3 quorum. D2, D3, and Fail-Closed scores (all 98) have no cross-model challenge. High scores under single-model conditions are not reliable signals of hardened correctness.
- **Action:** Rotate or restore valid API keys for GPT-4o and Gemini 2.5 Pro. Re-run the full audit panel against D2 (`second_verified_quote`, MAX_VERIFIED_QUOTES_PER_VIDEO enforcement, editorial_select.py:349-351/770-773) and D3 (`repair_window` BOUNDARY_FAULTS gate, editorial_select.py:822, floor constants). Do not ship D2/D3 as "consensus-verified" until genuine multi-model agreement is recorded.

---

### P5 — BACKLOG / MONITOR
**Ambiguous UTC semantics in `source_published` derivation**
- **Risk:** Grok's Cycle 2 self-review noted that `source_published` is derived from trusted `generated_at`/`freshness_minutes` or video `published_at` fields, keeping the D1 authority chain safe even if `_parse_ts` misbehaves. This is a valid mitigation — but it is an architectural assumption, not an enforced invariant.
- **Action:** Add a code comment at `grounded_event_date()` (story_semantics.py:391) explicitly documenting that `source_published` is only ever populated from these two trusted sources, so reviewers do not inadvertently add a third source that bypasses the UTC-labeling assumption. No code change required unless the derivation path expands.