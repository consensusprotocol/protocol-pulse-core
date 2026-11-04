# QWEN CONTEXT BIBLE — Protocol Pulse

Known failure patterns and their root causes. Load into every Qwen/audit session.

---

## VERTICAL RENDER FAILURES (v8-v13)

### V-FAIL-001: Debug boxes baked into rendered frames
**Versions affected:** v8, v9, v10, v11, v12, v13
**Root cause:** cv2.rectangle(), cv2.putText(), and ImageDraw.Draw() calls were inline in the render functions (reframe_1face, reframe_2face, etc.), not isolated. When debug_mode was not properly gated, colored rectangles and coordinate labels appeared in the final output.
**Fix:** All debug drawing moved to vertical/debug.py. Unit test T2 scans the AST of compositor.py and reframe.py and FAILS if any cv2.rectangle/putText/circle or ImageDraw.Draw call is found outside debug.py. The render path never imports debug.py.
**Detection:** Frame-level visual inspection or Grok vision critic (question: "are debug rectangles or text artifacts present?").

### V-FAIL-002: Grid column dropped (3-band from 5-tile source)
**Versions affected:** v10, v12
**Root cause:** A 5-tile Riverside source had 5 visible faces, but the compositor used a hardcoded 3-band layout and selected only the 3 largest face clusters, dropping 2 faces. This violated Law 18 ("never a subset of visible faces").
**Fix:** Shotmap now reports total_faces per shot. Compositor composes ALL visible faces. For 4+ faces, the grid layout (full 16:9 top + guest column below) is used. Gate G4 verifies face_count in rendered output matches source face_count. Unit test T1 checks every output frame.
**Detection:** G4 gate with 6 sampled frames, or T1 unit test with 3 frames per shot.

### V-FAIL-003: Mid-clip layout switch undetected
**Versions affected:** v11, v12, v13
**Root cause:** A Riverside source switched from 3-up to 5-up mid-clip without a video hard cut. The previous compositor classified the entire clip as one layout (3-up) and dropped the extra faces when the source switched to 5-up.
**Fix:** Shotmap's split_runs() function detects soft layout changes by monitoring seam signature changes across consecutive keyframes. When the seam pattern changes for >= 2 consecutive keyframes, a sub-shot boundary is created. The compositor re-classifies layout at each sub-shot boundary.
**Detection:** Shotmap's shot_map.json lists soft_layout_changes with frame numbers. T3 test verifies layout ID is constant within each shot boundary.

### V-FAIL-004: Speaker off-screen
**Versions affected:** v8, v9
**Root cause:** Face-centered crop used per-frame face detection with aggressive panning. When the speaking face moved near the edge of the source tile, the crop window would sometimes miss it entirely for a few frames.
**Fix:** Law 18a: ONE fixed crop per shot. Face position is the median over all sampled frames. No continuous panning, no animated crop motion. Re-center only at shotmap hard cuts.
**Detection:** T1 face count test catches frames with fewer faces than expected.

### V-FAIL-005: Riverside seam measurement failure on YouTube re-encodes
**Versions affected:** v12, v13
**Root cause:** The hardcoded SEAM_ROWS=(120,900) from the boomers shotmap assumed a specific active picture area. YouTube re-encodes add letterbox bars and burned-in lower-thirds that shift the actual gutter positions. The seam measurement returned no seams, causing the compositor to treat a 3-up source as single.
**Fix (pending calibration):** Law 21 mandates shotmap hardening: detect letterbox bars and crop before measurement, derive SEAM_ROWS from active picture area, mask bottom 18% for lower-third bands.
**Detection:** Shotmap logs seam counts per shot. Zero seams on a known multi-tile source = measurement failure.
