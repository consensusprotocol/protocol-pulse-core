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

### E-FAIL-013: A model asked one yes/no question per gap says yes to everything
**Evidence:** the 1b per-gap adjudicator (gemma3:27b, "does a sentence end at <GAP>?") called 19 of 19 Yahoo Finance gaps sentence ends, 'the | Wolf', 'of | all', 'is | up', 'pretty | massively' included. Every one had a real pause (90-770 ms), so G16 would have passed mid-sentence cuts in any unpunctuated source (docs/audits/pulse-sentence-law/1b_fix_punctuation/ADJUDICATOR_EVIDENCE_yahoo_sweep.jsonl). One of the two decisions cached for the Nov 10 fixture was such a false start ('course | of' inside "of course, of course").
**Fix:** no model decides a boundary. Root cause: whisper's no-punctuation mode. A second decode of the same audio with a neutral punctuated prompt supplies punctuation, transferred onto aligned verbatim words only (pipeline/punctuation.py; the words never change); an unpunctuated stretch has no boundary (fail closed). data/editorial/sentence_adjudication.json is no longer read. **Detection:** `test_pulse_20261110_mustfail.py::TestUnpunctuatedTranscript`, `TestPunctuationLayer`.

### E-FAIL-014: A layout default keyed on registry status letterboxes every new channel (D5)
**Root cause:** M21's `build_vertical_overrides` gave 'crop' only to channels with hand-approved crop tables ('approved'); all three Nov 10 channels were 'pending', so every machine-chosen clip was letterboxed. There was no machine reframe path, and a failed reframe silently used the 16:9 clip in the 9:16 timeline.
**Fix:** DEC-5 'auto' for every segment: a per-shot plan measured on the prepared clip (vertical_layout.classify: SCRFD faces every 0.5 s, fixed area rules) -> speaker-centred crop / stacked bands / flagged safe frame; a failed reframe raises STOP. **Detection:** G4s; `test_vertical_layout.py::TestSafeFrameTruth` (Yahoo's talking head shown as safe frame fails), `test_pinned.py::test_vertical_overrides_are_auto_for_every_channel_status`.

### E-FAIL-015: Measure the defining property, not a side effect
**Evidence:** the first safe-frame test inferred letterbox from a blurred top band; right on the Nov 10 and v2f frames, but the soft v2f hook read 5.0/6.2 (rule < 0.25) and a plain wall above a sharp face also reads as blur. A safe frame is defined by showing the WHOLE 16:9 picture: the centre band's correlation with the prepared frame is 0.998-1.000 (letterbox) vs <= 0.448 (v2f crops).

### E-FAIL-016: Choose a detector by measurement, then pin it
**Evidence:** BlazeFace short-range missed Yahoo Finance's standing host (1.6 % of frame); the Haar cascade counted 2-4 'faces' on one talking head. SCRFD-10G (insightface det_10g.onnx) measured 0.4 % / 1.6 % / 7.7-13 % correctly. Its sha256 is pinned (face_scrfd.MODEL_SHA256) and checked before use: another model would silently change every layout class.

### E-FAIL-017: Never place a crop at a fixed height
**Evidence:** the first stacked-band renderer read `band_cy` but classify never measured it, so every band sat at 45 % of frame height; a 379 px stack3 band would cut off a face at 28 % height. Bands are placed from each face's measured centre. **Detection:** `TestStackGeometry`.

### E-FAIL-018: A filter's documented parameter is not its measured behaviour (ffmpeg 4.4.2 xfade)
**Evidence:** `xfade=offset=t-dd` kept A through the frame at round(offset*fps) and started B one frame later: 211 frames instead of 210, and every dissolved-into clip's picture 41.7 ms behind its own sound (acrossfade places B's audio exactly at t-dd). A frame count alone can't prove alignment; a luma-ramp clip whose frames identify themselves did.
**Fix:** offset = t - dd - 1/fps (lands on a frame boundary, no rounding ambiguity). **Detection:** `test_transitions.py::TestConcat::test_dissolved_clip_picture_and_sound_start_together` (fails on the old offset: max luma error 4.0 = one ramp step).

### E-FAIL-019: A validator must speak its caller's contract (and so must the test double)
**Evidence:** Nov 11 recut HELD at the editorial gate: gemma3 judged the clips as index 0/1, the EDL numbers them 1/2, so LAW_1 found clip 2 unjudged. editorial_review._validator RETURNED its error string, but LocalLLM.chat_json only reacts to an exception, so it had never rejected a reply. The test double FakeReviewer implemented the same wrong contract, which is why no test noticed.
**Fix:** the validator raises; the schema says "index = the CLIP number shown"; chat_json's retry prompt names the validation error. Still wrong after retries = inconclusive = HOLD (the gate is unchanged). **Detection:** `test_window_review.py::TestReviewValidatorContract` (real chat_json loop, only the HTTP call faked; fails on the old validator).

### E-FAIL-020: A legal cut point can still sit on a click; the real gate is the oracle
**Evidence:** Nov 11 recut clip_02 (Natalie Brunell): the machine-placed cut_out 37.87 was inside the locked pause and passed cut_accept, but sat on a small tick (37.86-37.87). After two AAC encodes and the 30 ms fade the prepared clip's last 5 ms read -56.8 dB against a -71.8 dB reference: the unchanged clip contract held the run. Real prepare at 37.84 / 37.80 passes. A sample-level simulation of the fade did NOT reproduce the failure (codec smearing): do not model the codec.
**Fix:** stage_prepare, machine-placed cuts only: a fade-only contract failure moves that edge to the next legal point of the same pause (sentence_law.cut_candidates, nearest the target first), re-prepares and re-checks with the real contract; nothing passes = original restored, HOLD. Human cut tables never move. **Detection:** `test_prepare_retry.py`; the recut run itself.

### E-FAIL-021: A module name can be shadowed by a legacy folder that another module puts first on sys.path
**Evidence:** recut run 4 HELD at render: `module 'transitions' has no attribute 'plan'`. render16 inserts video_pipeline_v3/ at sys.path[0], and that folder has its own transitions.py; the unit tests imported pipeline/transitions.py BEFORE render16, so they never saw it.
**Fix:** renamed pipeline/pulse_transitions.py; every new pipeline module name checked against video_pipeline_v3/ and segment_v1/. **Detection:** `test_transitions.py::TestProductionImportOrder` (fresh interpreter, render16 imported first, the module render16 really uses must be ours).

### E-FAIL-022: A vision model's checklist needs the defect described in pixels, and silence is a "no"
**Evidence:** on yesterday's 9:16 contact sheet qwen3.8-27b answered "credits: no" (headline text inside the circles) but "letterbox: yes, they fill the frame", though the full-resolution clip_02 panel plainly shows a band with blurred areas above and below; a second pass returned EMPTY content from both models (reasoning used the token budget). 
**Fix:** each question describes what the defect looks like and where to look (the full-resolution panels); two vision models, any "no" holds; an empty or unparseable reply is retried once, then every line is "missing" = HOLD (never a crash, never a pass). Supervised sessions also read the sheet themselves. **Detection:** `test_visual_check.py` (verdict rules; live must-fail on yesterday's sheet).
**Still open (06:40 ET re-ask, sharpened question, both models):** both hold yesterday's sheet on the credits (D4), and BOTH still answer "every talking head fills the frame" for the letterboxed Melker / Brunell panels (D5). The vision panel is NOT a letterbox detector today; the deterministic G4s safe-frame gate is. Never cite a vision "yes" on letterbox as evidence.
**Resolved for letterbox (per-shot question):** asked about ONE frame ("is the sharp picture only a band with a blurred copy above and below?"), both models answer yesterday's Melker frame "yes" and the same speaker reframed to fill the frame "no". The 9:16 check now grabs one full-resolution frame per shot of every talking-head segment (VERTICAL_LAYOUT.json classes); any non-screen shot called letterboxed, or unanswered, fails V1. A whole-sheet "yes" on letterbox is still never evidence. **Detection:** `test_visual_check.py` TestLetterboxPerShot + live must-fail on the fixture's Melker panel.

### E-FAIL-023: The story engine splits one event into several candidates, and each falls short alone
**Evidence:** Nov 10 fresh run (runs/fresh_20261110_093150/TOPIC_SELECTION.json): "Bitcoin ETFs shed $1.3B" (#13) and "Bitcoin Falls Amid Tech Selloff" (#20) both counted Yahoo Finance's "Bitcoin dropped pretty massively over the weekend alongside the tech selloff"; #20 reached one channel ("coverage 1 < 2"), #13 failed on hook quality; the hand fix re-judged against ONE merged event and DataDash counted.
**Fix:** editorial_select step 5b: candidates whose counted evidence includes the SAME STATEMENT (same video, shared supporting chunk, >= 5 consecutive shared words in the evidence quotes) are merged deterministically (no model asked "same event?"); one derived query; verdicts pooled one per video; the not-counted ones re-judged against the merged query (budget by retrieval score); the usual coverage decision. A shared chunk alone is not enough (a roundup show states two events in one chunk). The same identity drives the DEC-9 story ledger. **Detection:** `test_same_event_merge.py` (real Nov 10 counted evidence groups exactly #13 + #20), `test_story_ledger.py`.

### E-FAIL-024: Moving code out of a function drops its function-local imports; a default argument freezes a module constant
**Evidence:** 4b: `_decide_coverage`, moved out of `_select_story`, used `sm` (a local import inside `_select_story`) -> NameError on the first coverage decision of a real auto run; `story_ledger.entries(path=LEDGER)` kept the import-time path, so patching `story_ledger.LEDGER` in a test changed nothing.
**Fix:** each moved function imports what it uses; constants are read at call time (`path = path or LEDGER`). **Detection:** a test that EXECUTES the moved path (not only imports the module); a test that patches the constant and checks the effect.


### E-FAIL-025: ffmpeg xfade refuses inputs on different timebases; a concat filter output is 1/1000000
**Evidence:** recut run 5 (runs/pinned_20261111_120910) HELD at render: hook->clip_01 had no room for a dissolve (hard cut = concat filter), clip_01->clip_02 dissolved; the xfade's first input was the concat output: "First input link main timebase (1/1000000) do not match the corresponding second input link xfade timebase (1/24)". Phase 3's tests only dissolved at the first junction (a raw 1/24 input), so they never built this graph.
**Fix:** `settb=1/FPS` on xfade's running input (no-op on 1/FPS, exact on frame times). **Detection:** `test_transitions.py` TestConcat test_dissolve_after_a_hard_cut_renders_frame_locked (channels A, A, B; fails on the old graph with the production message).

### E-FAIL-026: A canonicaliser that splits a decimal hides the decimal ('5.5 %' == '5 %')
**Evidence:** recut run 6 G18 failed on '5 .5%' vs 'five and a half percent' (same audio). Writing the must-fail half of the fix showed worse: norm('dropping 5.5%') was ['dropping', '5']: the decimal split into '5 5' and the 1-word repeat-collapser merged it, so 5.5 % and 5 % compared EQUAL (a comparator that could pass a dropped '.5').
**Fix:** a decimal stays ONE token ('5p5'); 'one point three' and 'N and a half' map to it; tests in both directions (equal spellings pass, a missing or added half fails). **Detection:** `test_word_diff.py` test_a_half_written_or_spoken_is_the_same_number.

### E-FAIL-027: A sentence-law-legal lineup can still fail as a video: no referent, off topic, the next shot in the pause
**Evidence:** recut run 6: hook "But I don't check it on an hourly basis..." (no referent), clip_02 "And the NASDAQ fell even harder ... concentrated in AI." (no Bitcoin), and clip_02's last 3 frames = Natalie's next shot (an NVIDIA/AMD/MICRON graphic cut in the pause before "Nvidia").
**Fix:** pipeline/stand_alone.py at validate (every run) and at auto selection on final windows: a hook may not open on a pronoun / conjunction / reply fragment; a clip may open on a conjunction only if the clip scorer affirms it stands alone; every segment names the story subject or completes the previous claim (back-reference + figure). pipeline/shot_snap.py: a hard shot change after the last word (before the first) is held on the speaker's shot; audio and frame count unchanged. **Detection:** `test_stand_alone.py` (run 6's hook and clip_02 must fail), `test_shot_snap.py`.

### E-FAIL-028: Before calling a gate failure a render defect, look at what the gate measured
**Evidence:** run 6: G15's only "squished ring" was the capital N of "Natalie Brunell" (31 x 36 px contour, fitted ellipse 122 x 212 passed the size filter); G9 missed by 0.03 luma on the hash-identical outro (floor 0.006 under the reference); G17a counted DataDash's noise-gated digital silence (< -100 dBFS) as not genuine; G14's one scored miss was a 0.5 s window matched 4.6 s away at xcorr 0.42 in DataDash's quiet passage, while the "0.00-0.04 frame_sim" rows were the 9:16 crop the gate itself marks LIMITED.
**Fix:** none to the gates (orchestrator: do not change what a check accepts): each one is written up with its measured object as an open decision (OD-1 G15, G9 margin, G17a gated silence); render defects are fixed. **Detection:** draw / print the measured object (docs/audits/pulse-sentence-law/od1_g15_evidence/).

### E-FAIL-029: A silence quota rejects what a listener accepts; measure the approved reference before setting a minimum
**Evidence:** Nov 10 lineup: Yahoo "Of course, Bitcoin dropped ..." (the words 'days.' | 'Of' abut, no quiet frame) and Natalie's edge after 'rally.' were "not cuttable" under the 80 ms pause / lead / tail and 60 ms guard minimums, so the machine chose weaker windows, although PBX's approved v2f has edges at 0 ms itself (clip_02 in: 'approximately.' | 'One' abut; clip_03 prepared tail 0 ms; DoD DEC-10a table). Writing the valley fixture also showed that a boundary's quiet-run search over the two words' FULL extents can pick the junction with the word before or after (a tie).
**Fix:** DEC-10: timing minimums = v2f's measured worst (0 ms; the D1 head rule stays 80 ms); legality is what a listener hears: neighbour_clear (no frame of the neighbour word above speech - 12 dB after the fade), G17b 85 %, the sentence lock, G18; a short gap is cut at its envelope minimum with a 2-frame (83 ms) fade; the quiet run is searched between the two words' midpoints. **Detection:** `test_dec10_edges.py` (every v2f edge passes; a cut inside a word fails), `test_pulse_20261110_mustfail.py` (yesterday's half "Bitcoin", Natalie's run-in and the clip starting on "81" still fail).

### E-FAIL-030: A record written outside the pipeline's writer poisons every later run that reads the store
**Evidence:** 4b run 1 (2026-11-11 14:03, runs/fresh_20261111_190259 at 36e769d0) HELD in editorial: story_semantics.emergent_clusters crashed on `sorted({None, ...})`. Four `transcript.whisper_words.json` records (Simply Bitcoin, Bitcoin Magazine, Marty Bent, DataDash), hand-made 2026-11-10 ~05:28 ET outside transcript_store's writer, carry channel_id / channel_name / exact_title None while each video's meta.json has them; the write-once store kept them and the chunker copied the empty identity into every chunk. Earlier runs survived only because no cluster happened to include them.
**Fix:** transcript_store.chunks takes missing identity from the video's meta.json (its identity record) and yields no chunks when no channel identity exists anywhere (fail closed); _make_record refuses a meta without channel identity. **Detection:** `test_editorial.py` TestChunkProvenance (planted identity-less record takes meta.json's identity; none anywhere = no chunks; the writer refuses). Never write into data/editorial by hand: use transcript_store.acquire.

### E-FAIL-031: The sign-off listed the clips' channels and left out the hook's
**Evidence:** the PBX-approved preview of 2026-11-11 (references/pulse_preview_2026-11-11): credits card DataDash, Natalie Brunell, Yahoo Finance, Bitcoin Magazine; sign-off "Clips today from Natalie Brunell, Yahoo Finance, and Bitcoin Magazine. Go follow them for more. Links are below." vo.generate_vo built the name list from edl["clips"] only; DataDash's only segment was the hook. No gate listened to the sign-off.
**Fix:** law L-a. The sign-off gets the card's list (credit_rings.credit_channels: hook first, then clips); stage_voice HOLDs before render unless the script names exactly that set; G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off; VO stems are keyed by hash(text, voice, model), never reused for another list. **Detection:** `test_g20_signoff.py` (the preview fails, v2f passes, the generator names the hook's channel).

### E-FAIL-032: An edge fade clipped the last word, and the one check that heard it was overruled
**Evidence:** same preview, Natalie Brunell "...Bitcoin really hasn't participated in the Monday rally.": the 83 ms DEC-12b fade ending at the envelope minimum 80.84 started at 80.757, inside the decay of 'rally'. A context-free G3b decode heard 'route' and was treated as a flaky decode (DEC-12f); PBX heard the clipped word.
**Fix:** laws L-b and L-c. A fade never overlaps an edge word: it sits in the gap next to the cut (2 frames, down to 10 ms), measured from the cut point's own level; G17c compares both edge words with the unfaded source (1 dB); a dissenting G3b reading or a G3c edge failure stands unless G17c and G16's neighbour_clear prove the edge. **Detection:** `test_edge_words.py` (the preview's tail fails; the L-b re-cut passes; v2f's edges pass except its two recorded legacy edges).

### E-FAIL-033: The editorial word pass read sentences from an unpunctuated decode
**Evidence:** fresh run 2026-11-11 21:39 UTC (runs/fresh_20261111_213954, 4ca4b426): Altcoin Daily Ov5jg52HqIY's stored whisper_words record (distil-large-v3 batched) has 373 words with no sentence mark, so the verified quote "there's been a scare after the blue wave of the midterms" sat in one 35.28 s 'sentence' (134.80-170.08) and the US-midterms candidate had no window from it. 29 of the store's 44 word records had such stretches. pipeline/punctuation.py (the gospel's restoration) ran only in select_passages, never in transcript_store's word pass. A prompted distil reference decode did not restore that stretch; a prompted large-v3 batched decode did (22.8 s).
**Fix:** law L-e. acquire(prefer_words) returns only a sentence_ready record; a verbatim record that needs restoration gets a whisper_words_punct record (large-v3 batched reference + punctuation.PROMPT, marks onto aligned words only; the verbatim record kept, immutable). A sentence-initial capital is transferred too where both decodes end a sentence right before the word (audit batch13 U-1): with marks only, the quote's restored sentence 'even thinking about the seasonality, ...' was still rejected as a lower-case start; select_passages (PIN path) transfers marks only. One Whisper model on GPU0 at a time (the arbitration proves 7 GB free). **Detection:** `test_punct_word_pass.py`.

### E-FAIL-034: Headline-shaped candidates split the channels' one conversation; the real development never reached the model
**Evidence:** same run: 24 candidates, none producible. 13 wire headlines (MARA, Canaan, HIVE, BitGo, Deutsche Bank...) ended 'currentness missing' because no channel read them aloud; the conversation the channels were having (Bitcoin pinned near $74K, ETF money leaving, midterms) fell short as separate headlines (BlackRock outflows coverage 1, $74K coverage 1). The emergent-cluster step kept only clusters of >= 3 channels and the 8 widest, all evergreen or off-brand topic clusters; the $74K-pullback cluster (Coin Bureau, Altcoin Daily, Bitcoin Magazine, Marty Bent) and the ETF-outflow cluster (Coin Bureau, Bitcoin Magazine) were in no cluster at all. The same-event merge did run (zero groups: no two candidates shared a counted statement). Selection took 3,282 s with no reply cache.
**Fix:** law L-f (DEC-13): clusters of >= 2 channels first (Bitcoin screen before any model call, 48 h then 72 h tiers), the claim from the shared statements, coverage from the cluster's own statements, wire headlines only after every cluster is exhausted, a ledger entry per cluster, a validated-reply cache. **Detection:** `test_dec13_clusters.py`.

### L-d: the PBX-approved preview of 2026-11-11 is a protected reference
Tag ref-pulse-preview-2026-11-11, references/pulse_preview_2026-11-11 (read-only), docs/references/REFERENCE_PULSE_PREVIEW_2026-11-11.md; pipeline/regression.sh step 6 re-derives its locks, cuts and layout. What PBX approved in it: one story told by a numbers hook and three clips from other channels, whole-sentence clips, the four-avatar credits card, speaker-centred vertical, dissolves between channels.

### L-e PUNCTUATED BEFORE READ: every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read
Check: transcript_store.acquire(prefer_words) returns only a sentence_ready record (verbatim where no stretch reads unpunctuated, else whisper_words_punct from a large-v3 batched reference decode, marks, and a sentence-initial capital where both decodes end a sentence, onto aligned words only); editorial_select's word pass treats any other record as failed. Test: test_punct_word_pass.py (E-FAIL-033).

### L-f CHANNELS FIRST (DEC-13): story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted
Check: editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines; cluster_entry screen; a cluster's coverage adjudicates its own statements; a ledger entry per cluster with the gate that stopped it; validated model replies cached by sha256(model, its Ollama digest, context, max_tokens, prompt). Test: test_dec13_clusters.py (E-FAIL-034).

### E-FAIL-035: G3b failed the approved v2f because the ASR wrote 'dollars' as '$'
**Evidence:** the Law 22 re-render of 2026-11-11 23:27 UTC (runs/v2f_20261111_232758; the first since DEC-12f's three-reading majority) was byte-identical to the reference but G3b failed its 9:16 clip_02, whose last word is 'dollars' ('... above 40 trillion dollars.'): readings 'above $40 trillion | above $40 trillion | above $40 trillion dollars', 1 of 3 votes. The word was heard; Whisper wrote it as a currency symbol. Any clip ending on an amount ('$1.66 billion.', '50 percent.') was exposed to a false HOLD.
**Fix:** law L-g: qa_gates._g3b_words reads symbols as the spoken words in spoken order ('$40 trillion' -> '40 trillion dollars', '50%' -> '50 percent', thousands separators and trailing stops dropped, decimals kept) for the readings, the EDL's last word and its next word alike. **Detection:** `test_g3b_majority.py` (v2f's 9:16 clip_02 must pass; the Natalie 'week.' run-on and a cut 250 ms into 'rally' still fail).

### L-g WRITTEN FORMS: a check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way
Check: segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order; thousands separators and trailing full stops dropped; decimals kept); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py.
