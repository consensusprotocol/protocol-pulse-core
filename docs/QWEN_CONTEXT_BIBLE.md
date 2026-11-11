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

### V-FAIL-006: VO visual leaks 16:9 chyron into vertical
**Versions affected:** segment_v2 pre-v2c
**Root cause:** `render_vo_visual_vert()` used the raw 16:9 source file as background for the blurred freeze frame. Channel chyrons and tickers (e.g. "GERLAND" name lower-third) remained visible under the Gaussian blur in the 9:16 output.
**Fix:** VO visuals now use the vertical's own composited clip as BG source (`reframed.get("hook")` or `reframed.get(preceding_clip_id)`). The composited clip has chyrons cropped out during reframe, so the blurred freeze is clean by construction. Law 23a codifies this rule.
**Detection:** Visual inspection of VO beats, or Grok vision critic checking for text artifacts under blur in VO segments.

### V-FAIL-007: Review-only renders must never add waiver switches to pipeline stages
**Versions affected:** combo-letterbox-quoteonly-v2, 2026-11-10 session
**Root cause:** To produce a REVIEW-ONLY render (pinned mode, editorial gates not passing), waiver switches were added to `stage_validate`, `stage_cut`, and `stage_prepare` in `run_fresh.py` that skipped `raise Hold` when `run.mode == "pinned"`. These switches sat in the production pipeline tree that the daily automated run uses, creating a bypass path with no `review_only` flag guard, no REPORT.md visibility, and no burn-in verification. Heimdall audit flagged as HIGH.
**Fix:** Waivers were reverted immediately. Review-only renders must be produced by: (a) post-processing a copy of the final output from a normal (gated) run, or (b) running in a throwaway branch that is never merged. Never add `if run.mode == "pinned": skip gate` switches to production pipeline code.
**Detection:** `git grep -n -i 'review.only\|REVIEW_ONLY\|waive' pipeline/` must return empty. Pre-commit hook or regression test can enforce this.

### D1-FIX-001: Same-day event dates wrongly discarded as hallucinated
**Versions affected:** All versions before f8d5c225
**Root cause:** `grounded_event_date()` in `story_semantics.py` compared `model_d < source_published` using datetime objects. `parse_event_date("2026-11-09")` returns midnight UTC, which is `<` than a source published at 14:30 UTC on the same day, causing same-day events to be discarded as "hallucinated" model dates.
**Fix:** Compare `.date()` objects instead of datetimes: `model_d.date() < source_published.date()`. Same calendar day is never discarded.
**Detection:** `pipeline/test_d1_sameday.py` — 7 tests covering same-day, previous-day, future-date, and edge cases.

---

## EDITORIAL CUT FAILURES (PBX review of pinned_20261110_150345, 2026-11-11)

### E-FAIL-001: A check that recomputes its own expectation from the thing it checks is a tautology
**Root cause:** ad7295ea/4cf5a31a recomputed `first/last_word_expected` from the SNAPPED cut window and synced them into edl.json; G3/edge-words then "verified" that the clip contained whatever it contained. clip_01 shipped "...this week. All right, you've probably seen people celebrating" (D2).
**Fix:** selection lock (sentence_law.make_lock): the editor's sentences are sealed with sha256 at selection; every later stage reads them; G16 fails if cuts_final's expected words differ from the lock.
**Detection:** `pipeline/test_pulse_20261110_mustfail.py::TestTautology`.

### E-FAIL-002: Window offset recorded != window offset requested
**Root cause:** `_download_window` asked yt-dlp for `*54-100` (`.0f`) but recorded 53.57; every canonical->file time was shifted 0.38-0.52 s, so windows chosen on sentence starts landed mid-word (D3: "81", "days").
**Fix:** record the requested whole-second start; never place cuts by offset arithmetic: the selected text is located in the downloaded file's own transcript (sentence_law.anchor).
**Detection:** `TestWindowOffset`.

### E-FAIL-003: Nearest-word heuristics pick fragments
**Root cause:** `select_passages._find_word_boundaries` took the word nearest the window start and the nearest sentence-ender (or the latest word) as the end. Removed.

### E-FAIL-004: A rule that never runs is not a rule
**Root cause:** R9/R10 (sentence end/start) skip when no transcripts are passed; `run_fresh.stage_validate` never passed them, and R10 always returns True ("advisory"). Both read PASS in reports. G16 now enforces the law in its own stage and in the final gate table.
**Detection:** DEFINITION_OF_DONE_PULSE_CHECK.md lists every rule with the check that runs it in production.

### E-FAIL-005: Whisper word timestamps are not boundaries
**Evidence:** 'Over' whisper 9.32 vs acoustic onset 9.65; 'I' 33.92 vs 34.44; 'what' 33.22 vs 33.93. Whisper starts the next word inside the pause.
**Rule:** word identity from the transcript, boundary position from the audio (pause >= 80 ms between the two words), lexical sentence end from punctuation or a cached, logged model adjudication when the transcript is unpunctuated (Yahoo Finance's large-v3 window transcript had none).

### E-FAIL-006: Digital zero is not room tone (D1)
**Evidence:** DataDash's file starts with 33 ms of codec zero then ~50 ms of room tone before 'Bitcoin'. The render was faithful; the source had no lead-in. Counting zeros as lead-in passes it.
**Fix:** genuine lead-in excludes frames below -100 dBFS; a file-head sentence with < 80 ms genuine lead-in needs the declared 0.25 s room-tone pad (held first frame).

### E-FAIL-007: Never fall back to a video thumbnail for an avatar (D4)
**Root cause:** `shoutout._fetch_avatar_on_demand` used `meta.get("thumbnail")` (1280x720) and the frozen renderer resized it to a square: squashed faces/text. G12/G15 FAILED correctly; QA_GATE_HOLD then reclassified them as detector false positives. A gate that fails is evidence first.
**Fix:** real square channel avatars onboarded once (pipeline/avatar_onboard.py, contact sheet looked at), registry-only lookup with sha256 prefix + square check; no on-demand fetch, no placeholder.

### E-FAIL-008: Removing a check's input to get past it
**Evidence:** 2026-11-10 R2: "approved_text mismatch (0.66 < 0.8) -> removed approved_text from PIN". The mismatch was the offset bug (E-FAIL-002) showing itself. Machine PINs now must carry approved_text.

### E-FAIL-009: Fixed quiet lines read a music bed as speech
**Evidence:** cut_accept's speech-25 dB line (-54.2 dB) sits inside DataDash's music bed (~-53 dB, 24 dB under speech): its "pause" after 'take.' ends at 9.39 where only music rises. The Nov 10 hook's out edge cannot meet both the 80 ms tail rule and cut_accept -> the window is rejected, never forced. Re-specifying cut_accept is a gate change (needs authority + audit).

### E-FAIL-010: Registry identity must be verified, not assumed
**Evidence:** registry "Michael Saylor" -> @Saylor = "旗-Saylor" (956 followers), not his channel. Disabled 2026-11-11. Avatar onboarding prints channel title/followers; look before registering.

### E-FAIL-011: A fallback must never take a window another slot owns
**Evidence:** 1d first version: the editor's own pick for a slot skipped the overlap / per-video / per-channel / already-tried checks that fallbacks pass; when slot 1's fallback was slot 2's own window, slot 2 cut the same window again (duplicate clip). Late Heimdall consensus, 2026-11-11.
**Fix:** the conflict checks run on every candidate, the editor's included. **Detection:** `test_sentence_windows.py::test_a_window_taken_by_a_fallback_is_never_used_twice`.

### E-FAIL-012: A budget holds for the words actually cut, not the declared window
**Evidence:** a passage declared 13.5 s whose text is two sentences (8.8 s) passed the 12-20 s clip budget on its declared times. Two synthetic test fixtures had the same flaw (windows declared 11-14 s around 4.6-7.2 s of text) and passed only because the locked span was never checked.
**Fix:** after locking, the locked words' span must fit the hook/clip budget, else the next-ranked window. Fixtures declare windows exactly where their text is. **Detection:** `test_budget_holds_for_the_locked_words_not_the_declared_window`.
