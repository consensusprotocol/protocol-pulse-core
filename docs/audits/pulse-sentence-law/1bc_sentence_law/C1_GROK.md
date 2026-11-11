**Q1: CORRECTNESS**  
The changed functions match their docstrings and the governing laws as shown in the diff. `anchor` (lines 983-1012) locates selected text by token alignment and returns `(i0, i1, ratio)` only when first/last tokens match. `boundary`/`edge_plan` (903-978) enforce both lexical (punctuation or adjudicator) and acoustic (>=80 ms pause) conditions before declaring `cuttable`. `write_lock_cut_table` (1070-1109) and `_accepted_cut_pair` (1050-1067) restrict cuts to the legal pause ranges from the lock; no path allows movement outside those ranges. `gate_g16` (1115-1150) and the G17 gates reject on missing lock, mismatched expected words, or out-of-range cuts. M12 fail-closed behavior is present: missing transcript, failed adjudication, or no valid pause produces errors/rejections (e.g., lines 1131, 1144, 1093). No silent exceptions or state leakage between clips is visible. No off-by-one or unit errors in the arithmetic shown.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW: Compliant (boundary + acoustic checks in `boundary`, 903-948; constants at 694-697).  
- SELECTION LOCK: Compliant (`make_lock`/`verify_lock` at 1020-1039; `selection_lock` written to EDL at 79, 605; never recomputed).  
- SNAP LIMIT: Compliant (`_accepted_cut_pair` searches only inside `cut_lo`/`cut_hi` from the lock; old ` _snap_candidates` removed at 164-202).  
- ONSET/TAIL: Compliant (`edge_plan` lead/tail rules at 962-977; G17a/b at 1249-1309; declared `lead_in_pad_s` at 1106).  
- CREDITS: No change (unchanged per header).  
- LAW 20/M2, M12, LAW 22: Compliant (hard stops, fail-closed, no threshold loosening, v2f path untouched).  
No path allows a cut outside the locked sentence's silence or recomputation of expected words after selection.

**Q3: TESTS**  
Tests prove the claim. `test_pulse_20261110_mustfail.py` asserts the exact D1/D2/D3 failure reasons and expected words (e.g., lines 1463, 1473, 1482). Controls (D3c, faithful render) assert PASS for the right reason. `test_pinned.py` and `test_fresh.py` confirm the old snap path is unreachable and locks are sealed at selection. No vacuous assertions visible.

**Q4: VERDICT**  
No defects found in the diff.  

READY