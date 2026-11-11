**CYCLE 2 REVIEW — pulse-sentence-law**

### 1. WHAT DID THEY CATCH THAT YOU MISSED?
- The redundant `import sentence_law as L` inside `stage_cut` (run_fresh.py:221) and `build_edl`/`validate_range` (pinned.py:39,54). I noted the overall import hygiene but did not flag the repeated in-function imports.
- GPT-4o’s observation on `TestD4Credits` temp-dir management (test_pulse_20261110_mustfail.py:1530-1537) using per-test `mkdtemp` instead of class-level setup.
- Gemini’s note that credits-law compliance for `validate_avatar` is only indirectly verified via the test assertion rather than shown in the diff itself.

### 2. WHERE DO YOU AGREE OR DISAGREE?
- **Agree** with all three models on core correctness and law compliance (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, M12 fail-closed). The removal of `_snap_candidates` + `_recompute_edge_words` and the strict use of `selection_lock` + `edge_plan` is the decisive improvement.
- **Agree** with GPT-4o on the two low-severity issues; both are real (if cosmetic).
- **Partially agree** with Gemini on credits: the test update is sufficient evidence for this diff, but a direct source review of `shoutout.validate_avatar` would have been ideal.
- **Disagree** with any implication of deeper defects. No model found a path that could move a cut outside its locked pause or recompute expected words after selection.

### 3. NEW FINDINGS FROM THIS REVIEW
- The `stage_sentence_law` pre-render gate (run_fresh.py:278-294) + the second `gate_g16` call inside `stage_gates` (lines 417-422) together give defense-in-depth that none of us highlighted in Cycle 1.
- `write_lock_cut_table` + `_accepted_cut_pair` now make the old `compute_all_cuts` path unreachable in auto mode (test_pinned.py:1425-1435), which is a stronger guarantee than previously stated.
- No new correctness or law violations surfaced.

### 4. REVISED SCORES

| Subsystem       | Cycle 1 | Cycle 2 | Why changed                  |
|-----------------|---------|---------|------------------------------|
| Correctness     | 9.5     | 9.6     | Confirmed no hidden paths    |
| Law Compliance  | 10      | 10      | No change                    |
| Test Quality    | 9.3     | 9.4     | Minor hygiene notes only     |
| Overall         | READY   | READY   | —                            |

### 5. FINAL PRIORITY LIST
**P0 CRITICAL** — none.  
**P1 HIGH** — none.  
**P2 MEDIUM**  
- Remove redundant `import sentence_law as L` inside `stage_cut` (run_fresh.py:221) and the two occurrences in pinned.py (39,54).  
- Promote `TestD4Credits` temp-dir handling to `setUpClass`/`tearDownClass` (test_pulse_20261110_mustfail.py:1532-1537).

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The complete deletion of `_snap_candidates` + `_recompute_edge_words` combined with the mandatory `selection_lock` + `edge_plan` path (run_fresh.py:220-226, select_passages.py:559-567, sentence_law.py:1070-1109) is the one change that eliminates D1/D2/D3 at the root.

### 7. PRODUCTION READY?
**Yes with conditions.**  
Ship after the two P2 items above are addressed. The code already satisfies every stated law with fail-closed behavior and strong test coverage. No further functional changes are required.