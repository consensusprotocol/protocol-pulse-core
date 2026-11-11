**Q1: CORRECTNESS**  
The changed functions (`_ends_statement`, `_n_sentences`, `_word_sentences`, `start_is_boundary`, `anchored_window`, `expanded_window`, `repair_window`, and the new fallback path in `select_passages.py`) match their docstrings and the sentence-boundary rules shown in the diff. All terminal checks now route through `sentence_law.is_terminal` (lines 22, 42, 52, 67, 97, 106, 124). No path in the diff produces a PASS or sealed window when data is missing; `_source_for` returns a rejection string and `_fill` skips the segment. No off-by-one in sentence indexing or duration math is visible. Imports inside functions (lines 21, 38, 51, 175) are present but do not alter control flow.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SNAP LIMIT / SELECTION LOCK: COMPLIANT (lines 60, 75, 87, 114, 166-168, 232-239). Windows are built only from whole sentences; selection_lock is written after verification; cuts are never moved.  
- ONSET/TAIL / CREDITS / M12 FAIL CLOSED: no changes in this diff, so unaffected.  
- LAW 20 / M2 (thresholds frozen): PARTIAL — `CLIP_MIN_S`/`CLIP_MAX_S` changed (line 10) and `MAX_WINDOW_SENTENCES` added (line 11). These are budget constants, not gate-acceptance thresholds, but the change alters what the editor will accept.  
- LAW 22 / v2f reference: no renderer changes visible.  
- No path recomputes first/last words after the lock or moves a cut outside the locked sentence's silence.

**Q3: TESTS**  
`test_sentence_windows.py` (new) and the updates to `test_window_review.py` exercise the exact claims: abbreviation/ellipsis handling (lines 271-284), budget enforcement (lines 293-306), next-ranked fallback (lines 336-378), and the three-sentence cap (lines 420-431). Assertions are specific (exact tuples, presence of rejection strings, `n_sentences <= 3`). No vacuous passes; the “must-fail” cases are rejected for the documented reasons (start boundary, sentence count, missing pause). Controls pass only after the legal replacement window is chosen.

**Q4: VERDICT**  
- MINOR | line 10 | CLIP_MIN_S lowered from 13.0 to 12.0 (and MAX_S to 20.0) | Document the change as an explicit, one-time budget adjustment required by sentence alignment; do not treat as precedent for future threshold edits.  
- MINOR | lines 21,38,51 | Repeated `import sentence_law` inside functions | Move to module level to avoid repeated import cost and potential circular-import surprises.  
- MINOR | line 29 | Reliance on `INTERJECTIONS` and `_lc_words` (pre-existing symbols) | Confirm they remain defined and unchanged outside this diff.  

No defects block the stated laws or produce false passes.  
**READY**