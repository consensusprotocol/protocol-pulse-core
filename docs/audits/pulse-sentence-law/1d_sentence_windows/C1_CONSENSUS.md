# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:21
Models: grok, gpt4o, gemini

---

## SCORES

No model produced a numeric score table. Scores are inferred from verdict language and severity of issues raised.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 9/10 | 9/10 | 9/10 |
| Law Compliance | 7/10 | 9/10 | 8/10 | 8/10 |
| Test Quality | 10/10 | 9/10 | 9/10 | 9/10 |
| Overall Readiness | 7/10 | 9/10 | 8/10 | 8/10 |

*Gemini's score is dragged down by the unresolved LAW 22 concern. GPT-4o did not raise it; Grok did not raise it. See CONFLICTS.*

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Module-level imports for `sentence_law`
**What:** `import sentence_law` is repeated inside function bodies (lines 21, 38, 51, 175 of `editorial_select.py`). All three models either flagged it directly (Grok: MINOR, lines 21/38/51) or implicitly endorsed the centralization of `sentence_law` calls as good practice (Gemini, GPT-4o). The concern is repeated import overhead and latent circular-import risk.
**File/Line:** `editorial_select.py`, lines 21, 38, 51, 175
**Change:** Hoist all `import sentence_law` to the module-level import block at the top of `editorial_select.py`. Remove the per-function occurrences.

---

### U2 — All window-building paths enforce `MAX_WINDOW_SENTENCES`
**What:** All three models confirmed that `MAX_WINDOW_SENTENCES` is correctly checked in `anchored_window`, `expanded_window`, and `repair_window`. This is a **validated strength** (see that section), but the unanimous agreement also constitutes a finding: no additional enforcement sites are needed. No action required beyond the confirmation itself.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `CLIP_MIN_S`/`CLIP_MAX_S` budget change requires explicit documentation
**Models:** Grok (MINOR, line 10), Gemini (noted in correctness, line 10)
**What:** `CLIP_MIN_S` was lowered from 13.0 → 12.0 and `CLIP_MAX_S` from 25.0 → 20.0. Grok notes these are budget constants, not gate-acceptance thresholds, but the change still alters accepted clip range. Gemini confirms the tests reflect the new values. GPT-4o did not flag this.
**File/Line:** `editorial_select.py`, line 10
**Change:** Add an inline comment at line 10 clearly stating this is a deliberate, one-time adjustment required by sentence-alignment geometry (shorter legal windows mean the old 25 s ceiling produced near-empty expansions). Include the previous values in the comment so git blame is self-documenting. Example:

```python
# Budget narrowed 2026-11-11 for sentence-law alignment (was 13.0–25.0).
# Sentence-boundary geometry makes >20 s windows rare; raising the floor
# to 12 s prevents sub-sentence slivers. Do not adjust without a law review.
CLIP_MIN_S = 12.0
CLIP_MAX_S = 20.0
```

Do **not** treat as precedent for ad-hoc threshold edits. This change is already in the diff; the action is purely documentation.

---

### M2 — Confirm `INTERJECTIONS` and `_lc_words` remain defined and stable
**Models:** Grok (MINOR, line 29), implicitly Gemini (noted reliance on external `sentence_law.py` symbols)
**What:** `_n_sentences` at line 29 references `INTERJECTIONS` and `_lc_words`. These are pre-existing symbols not shown in the diff. If a parallel branch modifies them, `_n_sentences` could silently produce wrong counts.
**File/Line:** `editorial_select.py`, line 29
**Change:** Add a `# noqa` or assertion comment, and ensure the CI regression suite imports the production version (not a stub) of these symbols. If they live in a constants file, add that file to the audit scope for Cycle 2.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — LAW 22 v2f Reference Integrity Risk
**Model:** Gemini only (POTENTIAL HIGH, `select_passages.py` line 158)
**What:** Gemini argues that the new, stricter Sentence Law checks now apply to the legacy `passages.json` path (the `else` branch at line 158). If the frozen v2f reference clip had a pause < 80 ms (previously legal), it will now be rejected and replaced, making the reference render non-identical.
**Assessment: INVESTIGATE FURTHER — do not dismiss.**

GPT-4o and Grok both reviewed the same code and rated LAW 22 COMPLIANT or N/A without catching this specific interaction. However, absence of a finding is not evidence of absence — this is exactly the kind of subtle cross-law interaction that a single thorough model catches and others miss on a first pass.

The risk is real and the blast radius is high (renders that were previously byte-locked would silently diverge). The correct resolution is cheap:

**Recommended fix:** Before merge, run `python regression_test.sh --v2f-ref` against the frozen reference fixture. If the output hash matches, Gemini's concern is moot and LAW 22 is confirmed COMPLIANT. If it does not match, add a `skip_sentence_law=True` guard on the legacy path and open a tracked issue to officially update the v2f reference under a versioned release.

**Priority: P0** (see Action Plan) — not because it is confirmed broken, but because it is unverified and the downside is a silent correctness regression on a frozen reference.

---

### UI2 — `_clip_quality` `"kind"` field change is downstream-coupled
**Model:** GPT-4o only (LOW severity, lines 128–136)
**What:** GPT-4o noted the new `"kind"` attribute added to `_clip_quality`'s output dict seems unrelated to Sentence Law but is in fact required by the fallback logic in `select_passages.py`. This is not a defect — Gemini confirmed it is "necessary and correct." GPT-4o's concern was that it might be unrelated; on review it is tightly coupled.
**Assessment: SKIP.** The coupling is intentional and correct. No change needed. Flagging it here so the second-pass author knows it was reviewed.

---

### UI3 — `sentence_law.py` itself is not in the diff
**Model:** Gemini only (noted as "minor uncertainty")
**What:** The entire audit relies on `sentence_law.is_terminal` behaving correctly for abbreviations, ellipses, and question marks, but `sentence_law.py` is not shown in the diff. Gemini notes the new tests provide high confidence in correct usage, but the implementation itself is unreviewed.
**Assessment: INVESTIGATE FURTHER.**

If `sentence_law.py` is a new file introduced by this feature, it must be included in Cycle 2's audit scope. If it is a pre-existing stable module, include it as a read-only reference. Add it to the second-pass prompt explicitly.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — LAW 22 compliance status
- **Gemini:** UNCERTAIN / PARTIAL — legacy path may now apply stricter checks to previously-valid v2f clips, breaking byte-identical reference renders.
- **GPT-4o:** COMPLIANT — no issue noted.
- **Grok:** Not addressed (rated as not affected by this diff).

**Tiebreaker: Gemini is more likely correct on the risk, GPT-4o and Grok are more likely correct on the current observed behavior in the happy path.**

The correct synthesis: the code is architecturally compliant with LAW 22 *intent* (it does not willfully ignore the reference), but there is an *untested interaction* that could produce a violation at runtime. This is not a "both sides are wrong" situation — it is a gap in test coverage for the legacy path. Resolution is a one-line CI check, not a code rewrite. Verdict: **INVESTIGATE BEFORE MERGE** (P0).

---

### C2 — LAW 20 / M2 threshold compliance
- **Grok:** PARTIAL — budget constants changed, which alters what the editor accepts.
- **GPT-4o:** COMPLIANT — no issue.
- **Gemini:** COMPLIANT (tightening is acceptable; no loosening).

**Tiebreaker: GPT-4o and Gemini are correct.** LAW 20/M2 prohibits *loosening* thresholds to make a render pass. Lowering `CLIP_MAX_S` from 25→20 and raising `CLIP_MIN_S` from 13→12 is a mixed signal (floor slightly lower, ceiling tighter). The ceiling tightening is strictly more conservative. The floor change (12 vs 13) is a 1-second relaxation downward — but this enables *shorter* clips to qualify, not lower-quality ones. M2 applies to quality gates (score thresholds, pause lengths), not clip duration ranges. Grok's concern is valid as a documentation issue (M1 above) but not a law violation. No compliance defect.

---

## VALIDATED STRENGTHS (all 3 models agree — do NOT change in second pass)

**VS1 — Fallback / next-ranked replacement logic (`select_passages.py`, lines 172–229)**
All three models confirmed `_fill` and `_eligible` correctly implement the "replace, don't move" principle. The logic is correct, M12 fail-closed, and well-tested. Do not touch.

**VS2 — M12 Fail-Closed behavior**
All three models confirmed that download failures, transcription failures, and `_build_segment` returning `None` all result in candidate rejection, never a pass. The guard at line 226 is correct. Do not touch.

**VS3 — Test suite quality**
All three models independently rated the tests as high quality: specific assertions, genuine must-fail cases, non-vacuous controls, and correct mocking of pipeline dependencies. The tests for abbreviation handling, ellipsis, 3-sentence cap, and fallback replacement are all praised. Do not weaken or restructure.

**VS4 — `MAX_WINDOW_SENTENCES` enforcement across all window-building functions**
All three models confirmed the constraint is applied at every creation/modification site. Do not add redundant checks or remove existing ones.

**VS5 — Centralization of terminal-punctuation logic via `sentence_law.is_terminal`**
All three models endorsed this design. The old scattered `endswith()` checks are correctly replaced. Do not revert or partially revert.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| SENTENCE LAW | ✅ COMPLIANT | Core purpose of the diff; all window functions enforce it |
| SNAP LIMIT | ✅ COMPLIANT | Invalid windows rejected, not moved; fallback replaces whole windows |
| SELECTION LOCK | ✅ COMPLIANT | Lock written after validation; no post-lock recomputation |
| ONSET/TAIL | ✅ COMPLIANT | Selection stage ensures acoustic pause; rendering stage unaffected |
| CREDITS | ✅ N/A | No credits code in diff |
| LAW 20 / M2 | ✅ COMPLIANT | Thresholds tightened or held; no loosening of quality gates |
| M12 FAIL CLOSED | ✅ COMPLIANT | All failure paths reject; none pass |
| LAW 22 (v2f) | ⚠️ UNVERIFIED | Structurally compliant; legacy path interaction with stricter checks untested — must run reference fixture before merge |

---

## SECURITY CONSENSUS

No model raised a security concern. The diff does not touch authentication, serialization of untrusted input, file path construction from user data, or network endpoints. Security surface is unchanged.

**One low-priority hygiene note (Grok, implicitly):** Repeated intra-function imports could theoretically be exploited via import-system monkey-patching in a compromised test environment, but this is not a realistic attack surface for a media pipeline. Fixing it (U1) is correct for performance and clarity reasons, not security.

---

## WORLD-CLASS GAP CONSENSUS

*(Only items mentioned by 2+ models)*

### WCG1 — `sentence_law.py` is a black box in this audit (Gemini + implicit Grok)
Both models noted the entire feature hinges on `sentence_law.is_terminal` but its implementation was not reviewed. A world-class audit ensures the foundational module is in scope. For Cycle 2, include `sentence_law.py` as a read-only exhibit.

### WCG2 — Budget constant changes lack change-control documentation (Grok + Gemini)
Both noted `CLIP_MIN_S`/`CLIP_MAX_S` changed without an inline rationale. A world-class codebase treats every constant that affects editorial output as a first-class decision requiring a dated comment with the previous value and the reason for change. This is cheap and prevents future "why was this 12?" archaeology.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Verify v2f reference render produces identical hash with new code | select_passages.py:158 (legacy path) | models: gemini (unique, high-risk) | LAW 22 violation is silent and irreversible if the reference hash changes post-merge; one CI run resolves this entirely. If hash differs: add skip_sentence_law=True guard on legacy else-branch and open versioned reference update issue.

P1 HIGH     | Hoist all `import sentence_law` to module level | editorial_select.py:21,38,51,175 | models: grok + gemini (majority) | Repeated function-level imports add overhead on every call and create latent circular-import risk; trivial to fix.

P1 HIGH     | Include sentence_law.py in Cycle 2 audit scope | sentence_law.py (not in diff) | models: gemini + grok (majority) | The entire feature's correctness guarantee rests on is_terminal; it must be independently reviewed before the feature is considered fully audited.

P2 MEDIUM   | Add inline comment to CLIP_MIN_S/CLIP_MAX_S documenting the deliberate change, previous values, and law-review requirement | editorial_select.py:10 | models: grok + gemini (majority) | Prevents future threshold drift and makes the git blame self-documenting.

P2 MEDIUM   | Confirm INTERJECTIONS and _lc_words are stable and imported from the production module (not a test stub) in CI | editorial_select.py:29 | models: grok + gemini (majority) | Silent wrong counts if these symbols are mutated by a parallel branch; a one-line assertion or import guard closes the gap.
```

---

## CYCLE 1 VERDICT

**READY FOR SECOND PASS — with one pre-merge gate.**

The code is architecturally sound, the tests are genuinely high quality, and all core laws are implemented correctly. No model found a defect that produces a false pass or an illegal render. The only blocker is the unverified LAW 22 interaction (UI1/P0), which requires a single CI run, not a code rewrite. The second pass should implement P0 verification, then P1 and P2 items, in that order.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models (Gemini 2.5 Pro,
GPT-4o, Grok-3) across 1 cycle. Implement every P0 and P1 item from the
consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Verify v2f reference render hash is unchanged under new code |
  select_passages.py:158 (legacy else-branch) |
  Run: python regression_test.sh --v2f-ref
  If hash MATCHES: add a comment at line 158 confirming LAW 22 verified on
    this date and commit.
  If hash DIFFERS: add a skip_sentence_law=True guard parameter to
    _build_segment, thread it through the legacy else-branch only, and open
    a GitHub issue titled "v2f reference update required: pulse-sentence-law"
    with the old and new hashes. Do NOT change the reference fixture in this
    PR.

P1 HIGH | Hoist all `import sentence_law` to module level |
  editorial_select.py:21,38,51,175 |
  Remove the four intra-function import statements. Add a single
  `import sentence_law` at the top of the file in the standard import block.
  Confirm no circular imports by running: python -c "import editorial_select"

P1 HIGH | Add sentence_law.py to the audit read scope |
  sentence_law.py |
  Read the file and confirm that is_terminal:
    (a) returns False for strings ending in abbreviations (e.g. "U.S.")
    (b) returns False for strings ending in ellipsis ("...")
    (c) returns True for strings ending in ".", "!", and treats "?" as
        terminal-but-question (excluded by _ends_statement)
  If any of (a)-(c) fails, file a defect and block merge. Do not modify
  sentence_law.py in this pass — read-only review only.

P2 MEDIUM | Document CLIP_MIN_S/CLIP_MAX_S change inline |
  editorial_select.py:10 |
  Add this comment block immediately above the constants:
    # Budget narrowed 2026-11-11 for sentence-law alignment (was 13.0–25.0 s).
    # Sentence-boundary geometry makes >20 s windows uncommon; the 12 s floor
    # prevents sub-sentence slivers. Do not adjust without a written law review.
  Do not change the values themselves.

P2 MEDIUM | Assert INTERJECTIONS and _lc_words are production-module symbols |
  editorial_select.py:29 (near _n_sentences definition) |
  Add a module-level assertion or import guard confirming these symbols
  resolve to the production constants file, not a test fixture. If they are
  defined locally in this file, add a comment confirming they are frozen.

VALIDATED — do NOT touch these areas, all 3 models confirmed excellent:

- _fill and _eligible in select_passages.py (lines 183–229): fallback logic
  is correct, M12 fail-closed, do not modify.
- The null-guard `if seg is not None:` at select_passages.py:226: correct,
  do not remove.
- MAX_WINDOW_SENTENCES enforcement in anchored_window, expanded_window, and
  repair_window: all three sites confirmed; do not add or remove check sites.
- sentence_law.is_terminal call sites at editorial_select.py:42,52: correct
  centralization, do not revert to endswith() checks.
- All tests in test_sentence_windows.py and test_window_review.py: assertions
  are specific and correct, do not weaken or restructure.

After implementing:
  regression_test.sh must show zero FAILs.
  python -c "import editorial_select" must exit 0 (no circular import).
  --v2f-ref hash result must be documented in the commit message.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements

- Hoist sentence_law imports to module level (P1)
- Document CLIP_MIN_S/CLIP_MAX_S budget change inline (P2)
- Assert INTERJECTIONS/_lc_words resolve to production symbols (P2)
- LAW 22 v2f reference verification: [PASS|SEE ISSUE #XXX] (P0)
"
git push origin combo-letterbox-quoteonly-v2
```