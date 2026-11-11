**Q1: CORRECTNESS**  
The avatar_onboard.py functions match their docstrings (fetch square YouTube avatars via yt-dlp + PIL, write ONBOARD_REPORT + CONTACT_SHEET, then register only after manual verification). The new _find_avatar + validate_avatar in shoutout.py (lines 970-987, 863-873) correctly rejects non-square images and enforces channels.json-only lookup with SHA prefix check. No silent exceptions or state leakage between clips. No sentence/onset code present, so no off-by-one or unit errors to evaluate.

**Q2: LAW COMPLIANCE**  
- CREDITS: COMPLIANT (lines 970-987, 863-873, 58-71). Real square channel avatars only; no thumbnails, placeholders, or on-demand generation.  
- SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / ONSET/TAIL / LAW 20 / M12 / LAW 22: No changes in this diff, so no violations introduced.  
- No path allows cut movement outside locked silence or recomputation of words.

**Q3: TESTS**  
No test files or assertions appear in the diff. The must-fail fixtures and pulse_20261110 tests referenced in the header are not present, so vacuous-pass risk cannot be assessed from this diff.

**Q4: VERDICT**  
Defects:  
- SEVERITY: Low | diff lines 126-134 | regex-based in-place edit of channels.json is brittle (edge-case JSON structure changes could corrupt file) | replace with proper JSON load/dump or jq.  
- SEVERITY: Low | diff line 575 | Saylor entry set to enabled:false with no avatar (intentional but undocumented) | add comment.  
- SEVERITY: None | duplicate SHA prefix check in fetch (lines 108-111) works but is only advisory.  

No defects affect sentence law, onset, or gate thresholds. The diff is narrowly scoped to the D4 avatar fix and is correct for that scope.  
**READY**