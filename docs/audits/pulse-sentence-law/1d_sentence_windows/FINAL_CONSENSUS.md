# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 03:24
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem          | Gemini | GPT-4o | Grok | Consensus |
|--------------------|--------|--------|------|-----------|
| Correctness        | 7/10   | 9/10   | 8/10 | **8/10**  |
| Law Compliance     | 5/10   | 8/10   | 7/10 | **6/10**  |
| Test Quality       | 8/10   | 9/10   | 9/10 | **8/10**  |
| Overall Readiness  | 4/10   | 8/10   | 7/10 | **6/10**  |

> **Scoring note:** GPT-4o's scores are optimistic because it did not independently discover the legacy-path and KeyError defects that Grok and Gemini uncovered. Consensus scores are weighted toward the lower, more evidence-grounded assessments from Grok and Gemini on the disputed subsystems.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Repeated `import sentence_law` inside functions
- **What:** `sentence_law` is imported locally inside function bodies rather than at module level.
- **File/Lines:** `editorial_select.py` lines 21, 38, 51; `select_passages.py` line 175 (approximate per diff).
- **What to change:** Delete all four local import statements. Add `import sentence_law` to the top-level import block of each file. This eliminates repeated import overhead on every call, removes the risk of Python's circular-import resolver seeing an inconsistent module state, and makes the dependency explicit to readers.

### U2 — Document the `CLIP_MIN_S` / `CLIP_MAX_S` budget change
- **What:** Constants changed from `CLIP_MIN_S=13.0, CLIP_MAX_S=25.0` to `12.0` and `20.0` respectively, with no inline explanation.
- **File/Line:** `editorial_select.py` line 10.
- **What to change:** Add a comment directly above or on the same line, e.g.:
  ```python
  # ONE-TIME BUDGET ADJUSTMENT (2026-11): tightened to match sentence-alignment
  # geometry; whole-sentence windows rarely exceed 20 s. Prior values: min=13.0, max=25.0.
  # Do NOT treat as precedent for future threshold edits without a full M2 review.
  CLIP_MIN_S = 12.0
  CLIP_MAX_S = 20.0
  ```

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Legacy `else` path in `select_passages.py` uses different selection logic (Grok + Gemini)
- **What:** The `else` branch (lines 157–164) that handles legacy `passages.json` files lacking the `kind` field constructs `hook_candidates` using a different rule — raw `endswith("?")` rather than `_ends_statement` / `sentence_law.is_terminal`. Because `_build_segment` applies the new checks downstream, any illegal window is eventually rejected and pushed into the fallback machinery, but the selection algorithm diverges before that point.
- **Impact:** Any legacy file processed through this branch produces different intermediate candidates than the new primary path, breaking the byte-identical re-render requirement.
- **File/Lines:** `select_passages.py` lines 157–164.
- **What to change:** Grok recommends patching the branch to use `_ends_statement`; Gemini recommends removing it entirely and requiring all inputs to carry the `kind` field. See **Conflicts** below for the tiebreaker.

### M2 — `_clip_quality` will `KeyError` on legacy passages without `kind` (Grok + Gemini)
- **What:** `_clip_quality` now reads `p["kind"]` unconditionally (line 133). Any passage dict reaching this function without a `kind` field raises `KeyError` and crashes — before the legacy `else` branch has a chance to handle it.
- **File/Line:** `editorial_select.py` line 133.
- **What to change:**
  ```python
  kind = p.get("kind", "unknown")
  ```
  or, if the removal of the legacy path (M1) guarantees `kind` is always present, add an assertion: `assert "kind" in p, f"passage missing 'kind': {p}"`. Choose based on the M1 resolution.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — Reused clip labels in boundary reports (Gemini only)
- **What:** In the `select_and_build_edl` loop, the label is generated as `f"clip_{len(clip_segs) + 1:02d}"` *before* calling `_fill`. If `_fill` returns nothing, `clip_segs` stays the same length, and the next loop iteration generates the identical label string. Boundary reports will log two distinct clip attempts under the same `clip_01` identifier.
- **File/Line:** `select_passages.py` lines 238–239 (approximate).
- **Assessment: IMPLEMENT.** This is a real, low-effort fix. Clip labels appear in audit logs and boundary reports; duplicates would corrupt any downstream tooling that keys on those labels (e.g., the v2f reference renderer). Fix by switching the loop to `enumerate`:
  ```python
  for i, clip in enumerate(clips):
      label = f"clip_{i + 1:02d}"
      seg = _fill(clip, label, ...)
  ```
  The fact that only one model caught it does not lower its validity — it is a straightforward logic defect.

### X2 — `INTERJECTIONS` and `_lc_words` as external dependencies (Grok only)
- **What:** `_n_sentences` relies on `INTERJECTIONS` and `_lc_words`, which are defined outside the diff.
- **Assessment: INVESTIGATE, do not block.** These are pre-existing symbols, almost certainly stable. Confirm they remain unchanged and add a brief in-code reference to where they are defined. This is a documentation concern, not a functional defect. Do not hold the release for it.

---

## CONFLICTS (models disagree — your tiebreaker)

### Conflict 1 — Whether the legacy path should be patched or deleted

| Model  | Recommendation |
|--------|----------------|
| Grok   | Patch the `else` branch to call `_ends_statement` and `MAX_WINDOW_SENTENCES`, keeping backward compatibility with old `passages.json` files. |
| Gemini | Delete the `else` branch entirely; require all inputs to carry `kind`. |
| GPT-4o | Did not independently flag the branch; deferred to others. |

**Tiebreaker — Delete the branch (Gemini's position is correct):**

Patching the branch (Grok's approach) keeps two independent selection paths alive. Any future change to the primary path must then also be mirrored to the legacy branch, which is precisely the kind of maintenance hazard that creates divergence over time and repeatedly re-opens LAW 22. The only lasting fix is a single, canonical path. The correct migration strategy is:

1. Remove the `else` branch.
2. Add a startup validation that rejects any `passages.json` lacking `kind` with a clear error message pointing to the migration guide.
3. Provide a one-time migration script (or document the manual step) to backfill `kind` into existing files.

If a hard requirement exists to process old files without migration, the `else` branch should backfill `kind` with a default value and then fall through to the primary path — not implement its own selection logic.

### Conflict 2 — Severity of the budget constant change

| Model  | Severity |
|--------|----------|
| Grok   | MINOR — already partially commented; a cleaner comment is all that's needed. |
| GPT-4o | P1 HIGH — documentation is required. |
| Gemini | P2 MEDIUM — not a blocker. |

**Tiebreaker — P2 MEDIUM (Gemini/Grok are right):** The constants are budget parameters, not gate thresholds. The existing tests already validate the new values. The required action is a better comment, not a code change. P2 is the correct priority; this does not block shipping.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`sentence_law.is_terminal` centralization.** All three models affirmed this as the correct architectural choice. Replacing scattered `endswith()` checks with a single authoritative function correctly handles abbreviations ("U.S."), trailing ellipses, and future edge cases in one place.

2. **`MAX_WINDOW_SENTENCES` enforcement across all three window builders.** `anchored_window`, `expanded_window`, and `repair_window` all check this constraint. No gap exists in the enforcement surface.

3. **M12 fail-closed behavior in `_fill`.** If `_source_for` returns an error string or `_build_segment` returns `None`, the candidate is skipped and the loop continues. No false pass on missing data or model failure. This is correctly implemented.

4. **Test suite specificity.** `test_sentence_windows.py` and the updated `test_window_review.py` use exact tuples, specific rejection strings, and genuine must-fail cases. No vacuous passes. The abbreviation and ellipsis edge cases are well-covered.

5. **Selection lock integrity.** No path in the diff recomputes first/last words after the lock or moves a cut outside the locked sentence's silence. SELECTION LOCK and SNAP LIMIT are correctly preserved.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| SENTENCE LAW | **COMPLIANT** (primary path) / **VIOLATED** (legacy path) | The primary path correctly enforces whole-sentence windows via `_ends_statement`, `_n_sentences`, and `MAX_WINDOW_SENTENCES`. The legacy `else` branch uses raw `endswith("?")` and violates this law for old inputs. |
| SELECTION LOCK | **COMPLIANT** | `selection_lock` is written only after verification; cuts are never moved. Unanimous agreement. |
| SNAP LIMIT | **COMPLIANT** | No cut moves outside the locked silence. Unanimous agreement. |
| LAW 22 (v2f byte-identical re-render) | **VIOLATED** | The legacy path produces a divergent candidate set, breaking determinism. Removing the branch resolves this completely. |
| LAW 20 / M2 (thresholds frozen) | **COMPLIANT** (gate thresholds) / **NOTED** (budget constants) | `CLIP_MIN_S`/`CLIP_MAX_S` are budget constants, not gate-acceptance thresholds. The change is legitimate but requires documentation. All models agree the gate thresholds themselves are untouched. |
| M12 (fail closed) | **COMPLIANT** | `_fill` correctly skips on download failure, transcription failure, and `_build_segment` returning `None`. |
| ONSET/TAIL / CREDITS | **UNAFFECTED** | No changes to these subsystems in this diff. |

---

## SECURITY CONSENSUS

No security issues were flagged by any model. The diff does not introduce new I/O paths, deserialization, authentication, or privilege escalation surfaces. The `_source_for` download path is pre-existing and unchanged. No action required.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Migration path for legacy `passages.json` files (Grok + Gemini).** The removal of the legacy path (which is the correct fix) will break any operator who has not migrated their data. A world-class feature ships with a documented migration path: a one-time script, a clear error message, and a note in the changelog. Currently none of this exists.

2. **Test coverage of the legacy/fallback boundary (Grok + Gemini).** The test suite does not exercise the `else` branch or the scenario where every primary and fallback candidate fails. If that branch is patched rather than deleted, it needs its own tests. Even after deletion, a test that deliberately submits a `passages.json` without `kind` and asserts a clean rejection error would prevent future regressions.

3. **Self-documenting budget constants (all 3 models, different framings).** A comment explaining not just the new values but the *reasoning* (sentence-alignment geometry, the old values, the review process required to change them) is the difference between a comment and documentation. World-class codebases make budget constants auditable.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Remove legacy else-branch OR enforce kind field at entry point
            | select_passages.py lines 157–164
            | Models: Grok + Gemini (GPT-4o deferred)
            | Why: Two divergent selection algorithms in the same function break
            |      LAW 22's byte-identical re-render requirement and silently
            |      produce different candidates for old inputs. Only one path
            |      must exist. Preferred resolution: delete the branch, add a
            |      startup assertion that rejects inputs missing 'kind', and
            |      ship a migration note.

P0 CRITICAL | Guard p.get("kind") or assert kind present in _clip_quality
            | editorial_select.py line 133
            | Models: Grok + Gemini
            | Why: p["kind"] raises KeyError on any legacy passage dict,
            |      crashing the pipeline before the legacy branch can run.
            |      If P0 above removes the legacy branch, replace with an
            |      assertion. If the branch is kept, use p.get("kind", "unknown").

P1 HIGH     | Fix reused clip labels — switch loop to enumerate
            | select_passages.py lines 238–239
            | Models: Gemini (unique, but defect is unambiguous)
            | Why: When _fill returns nothing, len(clip_segs) does not advance,
            |      so the next iteration generates the same label (clip_01).
            |      Duplicate labels corrupt boundary reports and any downstream
            |      tooling that keys on them, including v2f reference renders.

P1 HIGH     | Hoist all import sentence_law to module level
            | editorial_select.py lines 21, 38, 51; select_passages.py line 175
            | Models: all 3
            | Why: Repeated local imports add overhead on every call and can
            |      trigger circular-import resolver inconsistencies. Module-level
            |      imports are the unambiguous standard.

P2 MEDIUM   | Add inline comment explaining CLIP_MIN_S / CLIP_MAX_S change
            | editorial_select.py line 10
            | Models: all 3
            | Why: Budget constants changing without explanation are a future
            |      maintenance trap. Record old values, rationale, and the
            |      M2-review requirement for future changes.

P2 MEDIUM   | Confirm INTERJECTIONS and _lc_words are defined and stable
            | editorial_select.py (dependency check, no specific line)
            | Models: Grok
            | Why: _n_sentences silently misbehaves if these symbols are
            |      redefined or absent. A one-line assert or a brief comment
            |      pointing to their definition is sufficient.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY. Two P0 blockers must be resolved before shipping.**

The sentence-law enforcement on the primary code path is well-designed, correctly implemented, and thoroughly tested. The centralization of `sentence_law.is_terminal`, the three-window-builder enforcement of `MAX_WINDOW_SENTENCES`, and the fail-closed behavior of `_fill` are all genuinely solid.

However, two defects block the release:

1. **The legacy `else` branch** (P0) causes LAW 22 to be violated for any `passages.json` file that predates the `kind` field. This is not a theoretical risk — it is a guaranteed divergence for the documented data format.

2. **The `KeyError` on `p["kind"]`** (P0) is a crash path that is not exercised by any existing test and will surface in production the first time a legacy passage reaches `_clip_quality`.

The P1 clip-label bug is a correctness defect in audit logging that will corrupt boundary reports and must be fixed before shipping, though it does not cause silent data corruption in the final output.

After the two P0 fixes, the P1 label fix, and the P1 import hoisting, this feature is ready to ship. The P2 items are strongly recommended for code health and long-term maintainability but are not blockers.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | select_passages.py lines 157–164
  Remove the legacy else-branch that handles passages.json files without a
  'kind' field. Add a startup/entry-point assertion that rejects any passage
  dict missing 'kind' with a clear error message (e.g., "passage missing
  required 'kind' field — run migration script"). Add a migration note to
  CHANGELOG.md pointing operators to the backfill procedure.

P0 CRITICAL | editorial_select.py line 133
  After confirming the legacy branch is removed (above), replace p["kind"]
  with: assert "kind" in p, f"passage missing 'kind': {p.get('id', p)}"
  This converts a silent crash into a loud, diagnosable failure at the
  earliest possible point.

P1 HIGH | select_passages.py lines 238–239
  Switch the clip-building loop to use enumerate so labels never collide:
    for i, clip in enumerate(clips):
        label = f"clip_{i + 1:02d}"
        seg = _fill(clip, label, ...)
  This prevents duplicate clip_01 labels in boundary reports when _fill
  returns nothing for the first candidate.

P1 HIGH | editorial_select.py lines 21, 38, 51; select_passages.py line 175
  Remove all function-level `import sentence_law` statements.
  Add `import sentence_law` to the top-level import block of each file.

P2 MEDIUM | editorial_select.py line 10
  Add an inline comment above CLIP_MIN_S / CLIP_MAX_S:
  # ONE-TIME BUDGET ADJUSTMENT (2026-11): tightened to match sentence-alignment
  # geometry; whole-sentence windows rarely exceed 20 s.
  # Prior values: CLIP_MIN_S=13.0, CLIP_MAX_S=25.0.
  # Do NOT change without a full M2 review.

P2 MEDIUM | editorial_select.py (_n_sentences dependency check)
  Add a brief comment near _n_sentences referencing where INTERJECTIONS and
  _lc_words are defined, or add: assert INTERJECTIONS is not None at import
  time. This makes the external dependency explicit and diagnosable.

VALIDATED (do NOT touch — all 3 models confirmed excellent):
  - sentence_law.is_terminal centralization: correct, do not refactor.
  - MAX_WINDOW_SENTENCES enforcement in anchored_window, expanded_window,
    repair_window: all three builders are correctly covered, do not change.
  - _fill fail-closed behavior: skip on _source_for error or _build_segment
    returning None is correct, do not change.
  - Test assertions in test_sentence_windows.py and test_window_review.py:
    exact tuples, specific rejection strings, genuine must-fail cases.
    Do not weaken any assertion.
  - selection_lock write timing and SNAP_LIMIT enforcement: do not touch.

After implementing:
  regression_test.sh must show zero FAILs.
  Manually verify that submitting a passages.json without 'kind' produces
  the new assertion error (not a KeyError).
  Manually verify that boundary reports for a two-clip run where the first
  candidate fails show clip_01 and clip_02, not two clip_01 entries.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: **Grok** — Grok delivered the highest-quality analysis across both cycles by independently discovering two concrete, actionable defects that others missed (the legacy `endswith("?")` path bypassing `_ends_statement`, and the latent `KeyError` crash in `_clip_quality` when `p["kind"]` is absent from legacy passage data), while also providing the most precise law-compliance assessment including the nuanced LAW 20 partial-compliance flag. Its Cycle 2 self-correction was honest and specific rather than deferential, and its findings were directly grounded in line-level evidence rather than structural observation alone.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by severity (crash risk → compliance risk → correctness risk → maintainability).

---

### P1 — CRITICAL: `KeyError` crash on legacy passages missing `"kind"` field
- **File:** `editorial_select.py`, line 133 (`_clip_quality`)
- **Finding:** `p["kind"]` is now read unconditionally. Any `passages.json` entry produced before the `"kind"` field was introduced will raise `KeyError` before reaching the legacy `else` branch — crashing the pipeline silently on real data.
- **Fix:** Replace the bare key access with `p.get("kind", "unknown")` or add an explicit guard:
  ```python
  kind = p.get("kind")
  if kind is None:
      raise ValueError(f"Passage {p.get('id')} missing required 'kind' field — re-run indexer.")
  ```
  Choose the defensive raise if legacy data should be rejected; use `.get` with a fallback if silent downgrade is acceptable. Document the decision.
- **Test required:** Add a test case with a passage dict lacking `"kind"` and assert the correct behavior (crash with message, or fallback value).

---

### P2 — CRITICAL: Legacy path uses `endswith("?")` instead of `_ends_statement`
- **File:** `select_passages.py`, lines 157–164
- **Finding:** The `else` branch (triggered by `passages.json` files without the `"kind"` field) still builds `hook_candidates` using raw `endswith("?")` logic rather than `_ends_statement`. Although `_build_segment` will ultimately reject illegal windows, this forces every legacy-data clip through the full fallback machinery unnecessarily and means the new abbreviation/ellipsis-aware terminal logic is not applied at the candidate-selection stage for legacy data.
- **Fix:** Replace the inline `endswith("?")` check in that branch with a call to `_ends_statement`. If the branch is intended to be deprecated, add a `# TODO: remove after all passages.json files are re-indexed` comment and a logged warning.
- **Test required:** Add a test with a legacy-format passage (no `"kind"`) containing an abbreviation mid-passage (e.g., "Dr. Smith said so.") and assert that it is not incorrectly split at the abbreviation boundary.

---

### P3 — HIGH: LAW 22 violation risk — legacy `else` branch produces divergent output
- **File:** `select_passages.py`, lines 157–164
- **Finding:** The legacy selection path produces different window selections than the new `kind`-aware path for identical source material, meaning a v2f reference render of a legacy-processed clip will not be byte-identical. This is a direct LAW 22 compliance failure for any clip processed before the re-index.
- **Fix:** Either (a) gate the entire PR on a completed re-index of all `passages.json` files so the legacy branch is unreachable in production, or (b) add an explicit compliance note documenting that LAW 22 applies only to clips processed after re-index, with a hard version boundary logged at runtime.
- **Test required:** Integration test asserting that processing the same source through both paths produces identical `selection_lock` output after re-index.

---

### P4 — HIGH: LAW 20 partial compliance — budget constants changed without threshold audit
- **File:** `editorial_select.py`, line 10–11
- **Finding:** `CLIP_MIN_S` and `CLIP_MAX_S` were changed (13→12, 25→20) and `MAX_WINDOW_SENTENCES=3` was added. These are not gate-acceptance thresholds, but they materially alter what the editor accepts. LAW 20 requires frozen thresholds unless a formal review is logged.
- **Fix:** Add to the PR description or an inline audit comment: explicit confirmation that these values were reviewed under LAW 20, the rationale (sentence-alignment geometry), and that this is a one-time adjustment not a precedent. The inline comment prescribed in U2 below is necessary but not sufficient — the formal review record must exist.

---

### P5 — MEDIUM: Module-level imports (unanimous U1)
- **Files:** `editorial_select.py` lines 21, 38, 51; `select_passages.py` line 175
- **Fix:** Remove all four local `import sentence_law` statements. Add one `import sentence_law` to the top-level import block of each file. No behavior change; eliminates repeated import overhead and circular-import risk.
- **Test required:** None beyond existing suite passing.

---

### P6 — MEDIUM: Undocumented budget constant change (unanimous U2)
- **File:** `editorial_select.py`, line 10
- **Fix:**
  ```python
  # ONE-TIME BUDGET ADJUSTMENT (2026-11): tightened to match sentence-alignment
  # geometry; whole-sentence windows rarely exceed 20 s.
  # Prior values: CLIP_MIN_S=13.0, CLIP_MAX_S=25.0.
  # Reviewed under LAW 20 — see PR #[number]. Not a precedent for ad-hoc changes.
  CLIP_MIN_S = 12.0
  CLIP_MAX_S = 20.0
  ```

---

### P7 — LOW: `INTERJECTIONS` external dependency not audited
- **File:** `editorial_select.py`, `_n_sentences`
- **Finding:** `_n_sentences` skips words present in `INTERJECTIONS` when counting sentences. The contents of that list are not visible in the diff and were not tested for edge cases (e.g., interjections that also appear as sentence-initial words in legitimate speech).
- **Fix:** Add at minimum one test asserting that a word appearing in `INTERJECTIONS` mid-sentence does not cause an undercount of sentence boundaries. Document the source and freeze policy of the `INTERJECTIONS` list.