**Q1: CORRECTNESS**  
From the diff, changed functions generally match their docstrings and the stated laws. Key verified points:  
- `gate_g18` (word_diff.py:2091) and `edges`/`diff` (2093-2073) correctly enforce first/last words against the selection_lock and source span (run_fresh.py:464-470).  
- Fail-closed paths exist (render_vertical.py:253 raises on reframe failure; face_scrfd.py:32-37, 37 on missing/wrong model).  
- `_transition_concat` (render16.py:147) returns None when TRANSITIONS.json is absent, preserving the hard-cut v2f path (render16.py:101, render_vertical.py:276).  
- `head_tail` calls and lead/tail bounding appear in transitions.py:1416 and run_fresh.py:359.  
- No obvious silent exceptions or cross-clip state leaks in the added/modified paths. Time/index handling uses explicit fps scaling (e.g., render_vertical.py:208, transitions.py:1569) with no detected off-by-one in the reviewed sections.  

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SELECTION LOCK / SNAP LIMIT: Compliant. G16 (run_fresh.py:455) and G18 (464) use the sealed `selection_lock` from edl.json; cuts are bounded by measured lead/tail (transitions.py:1416).  
- ONSET/TAIL: G17 checks added (run_fresh.py:458).  
- CREDITS: G12/G15 rows preserved and included in verify_pack (verify_pack.py:1691).  
- LAW 20/M2, M12 FAIL CLOSED, LAW 22: Compliant. Gates remain hard stops; missing data or exceptions reject (multiple `raise RuntimeError`); v2f frozen path is the explicit default when no TRANSITIONS.json (render16.py:101).  
- No evidence of loosened thresholds or post-selection recomputation of words.  

**Q3: TESTS**  
The new tests (test_word_diff.py, test_vertical_layout.py, test_transitions.py, test_telegram_delivery.py) target the must-fail fixtures from pulse_20261110 and assert the exact failure reasons (e.g., test_word_diff.py:1276-1288 checks clipped start + run-on on clip_01/02; test_vertical_layout.py:1054 checks mislabelled screen). Controls pass for the documented reasons. No vacuous assertions observed in the reviewed test bodies.  

**Q4: VERDICT**  
No defects found in the reviewed diff sections.  

**READY**