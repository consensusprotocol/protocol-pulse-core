**CYCLE 2 REVIEW — pulse-sentence-law**

### 1. WHAT DID THEY CATCH THAT YOU MISSED?
- **LAW 22 / legacy v2f path** (Gemini): The `else` branch in `select_passages.py:157-164` preserves old selection logic. Even though `_build_segment` now contains the new checks, the path that feeds it can still bypass the `kind`-based `MAX_WINDOW_SENTENCES` enforcement in certain legacy `passages.json` files.
- Stronger emphasis on the repeated `import sentence_law` inside functions (all three models converged on this as a latent risk).
- The budget-constant change (`CLIP_MIN_S`/`CLIP_MAX_S`) was already noted by me, but Gemini and the consensus correctly flagged that it still needs an explicit, non-precedent comment.

### 2. WHERE DO YOU AGREE OR DISAGREE?
**Agree**
- Imports must be hoisted (U1).
- `MAX_WINDOW_SENTENCES` enforcement across all three window builders is solid.
- Budget documentation is required.
- M12 fail-closed behavior is correct in the new `_fill` path.

**Partially agree**
- LAW 22 concern: valid for the legacy branch; overstated for the primary `kind`-aware path. The risk is real but narrow.

**Disagree**
- Severity of the budget change. It is already commented on line 10 and the tests were updated; the remaining action is purely a clearer git-blame comment, not a functional defect.

### 3. NEW FINDINGS FROM THIS REVIEW
- The legacy path (`select_passages.py:157-164`) still constructs `hook_candidates` using only `endswith("?")` instead of `_ends_statement`. While `_build_segment` will later reject illegal windows, this creates an unnecessary extra round-trip through the fallback machinery for legacy data.
- `_clip_quality` now unconditionally reads `p["kind"]` (line 133). Any legacy passage without the field will raise `KeyError` before reaching the `else` branch. This is a latent crash path not exercised by the new tests.

### 4. REVISED SCORES

| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| Correctness        | 9/10    | 8/10    | Legacy path + `_clip_quality` KeyError risk |
| Law Compliance     | 8/10    | 7/10    | LAW 22 legacy branch now confirmed as gap |
| Test Quality       | 9/10    | 9/10    | No change |
| Overall Readiness  | 8/10    | 7/10    | Two narrow but real edge-case holes |

### 5. FINAL PRIORITY LIST
**P0 CRITICAL**
- `select_passages.py:157-164` — legacy branch must call `_ends_statement` (or import and use the same rule) instead of raw `endswith("?")`.
- `editorial_select.py:133` — guard `p.get("kind")` or ensure every passage reaching `_clip_quality` has the field.

**P1 HIGH**
- Hoist all `import sentence_law` to module level (lines 21, 38, 51, 175).

**P2 MEDIUM**
- Add explicit one-time budget comment at line 10 (already partially present; make it self-documenting with old values).

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Make the legacy `else` branch in `select_passages.py` use the same `sentence_law.is_terminal` + `MAX_WINDOW_SENTENCES` rules as the primary path so that LAW 22 and SENTENCE LAW remain satisfied even for old `passages.json` files.

### 7. PRODUCTION READY?
**Yes with conditions** — fix the two P0 items above, hoist the imports, and add the budget comment. After those three changes the feature is ready to ship.