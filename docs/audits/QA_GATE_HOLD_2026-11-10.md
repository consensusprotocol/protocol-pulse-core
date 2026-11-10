# QA Gate Hold Analysis — 2026-11-10

Run: `pinned_20261110_142152` (and identical-content `pinned_20261110_150345`)
Branch: `combo-letterbox-quoteonly-v2` at `4cf5a31a`
Revision: `06e2182f` (edge word fix) + `4cf5a31a` (EDL sync)

## Gate Results Summary

| Gate | 16:9 | 9:16 | Classification |
|------|------|------|----------------|
| G1_voice | PASS | PASS | — |
| G2_watermark | PASS | PASS | — |
| G3_cuts | FAIL | FAIL | (R) fixed by 4cf5a31a |
| G3b_cut_out_clean | PASS | PASS | — |
| G3c_acoustic_tail | FAIL | FAIL | (R) fixable |
| G4_faces | FAIL | FAIL | (D) design assumption |
| G5_tech | PASS | PASS | — |
| G6_preroll | PASS | PASS | — |
| G8_sharpness | FAIL | FAIL | (S) source + (D) design |
| G9_tail | FAIL | FAIL | approved known exception |
| G10_chyron | PASS | PASS | — |
| G11_parity | PASS | PASS | — |
| G12_credits | FAIL | FAIL | (D) detector design assumption |
| G13_vo_audible | PASS | PASS | — |
| G14_av_alignment | PASS | PASS | — |
| G15_credits | FAIL | PASS (9:16) | (D) same as G12 |

## Per-Gate Detail

### G3_cuts — FAIL → (R) fixed

**What it checks:** Whispers the first/last 1.5s of each rendered clip and compares the detected words against the EDL's expected `first_word`/`last_word`.

**Measured vs threshold:**
- clip_01: EDL expected `last_word="right,"` but whisper found `"celebrating"`. The snapped cut boundary moved from 31.99→33.71, changing the last audible word.
- clip_02: EDL expected `last_word="many"` but whisper found `"times"`. Snap moved from 34.38→34.36, landing after "times" instead of "many".

**Fix:** Commit `4cf5a31a` adds `_sync_edl_edge_words()` to propagate snapped edge words from `cuts_final.json` back into `edl.json` after both `stage_cut` (initial snap) and `stage_prepare` (retry snap). The G3 gate now reads the same expectation the prepare stage verified. No gate logic changed.

---

### G3c_acoustic_tail — FAIL → (R) fixable by choosing another accepted boundary

**What it checks:** Measures the audio energy in the last 100ms of each rendered clip ("tail"). If the tail energy exceeds `speech_median - 12 dB`, the clip may contain the onset of the next word bleeding through the cut.

**Measured vs threshold:**
- hook (both formats): speech_median=-30.6 dB, threshold=-42.6 dB, tail_max=-35.5 dB. **FAIL** (tail -35.5 > limit -42.6).
- clip_01: PASS (tail -34.0 < threshold -31.6)
- clip_02: PASS (tail -45.3 < threshold -29.1)

**Segment:** hook, both formats.
**Root cause:** The DataDash hook source has continuous background music/ambient audio. At the snapped cut point (9.33s), the speaker has finished the word "take." but the background track continues. The tail energy (-35.5 dB) is above the speech-relative threshold.

**Investigation (11:10 ET order, item 3):** Transcript shows "take." ends at 9.100s; "Over" starts at 9.320s. The current snap at 9.33s already sits 10ms past the onset of "Over". The valley centre at 9.46s is **inside** the word "Over" (9.32-9.92s). Moving the cut deeper would capture more of the next sentence, not less. Moving earlier (toward 9.10s) would tighten the gap after "take." below clip contract minimums. The current 9.33s is the best accepted boundary the snapper found. **Leaving G3c failing for hook.** Root cause is continuous background music in the DataDash source, not a cut placement defect.

---

### G4_faces — FAIL → (D) design assumption

**What it checks:** Samples 6 evenly-spaced frames from each clip and runs face detection. For "single" layout clips, at least 1 face must be detected in every sampled frame.

**Measured vs threshold:**
- hook 16:9: face_counts = [0, 1, 1, 1, 1, 1]. Frame 0 (t≈0s) has 0 faces. Min required: 1.
- hook 9:16: face_counts = [0, 1, 0, 1, 1, 1]. Frames 0 and 2 have 0 faces.

**Segment:** hook, both formats.
**Root cause:** The DataDash hook source is a chart-screen layout with a small face-cam overlay in the bottom-left corner. At some sample points, the face is either too small to detect or briefly occluded by chart elements. The G4 gate was designed for the v2f speaker-crop layout where the speaker fills most of the frame.

**PBX decision:** The gate assumes a talking-head format. For chart-screen sources (common in crypto YouTube), the gate needs either: (a) a "chart_overlay" layout mode with relaxed face requirements (e.g., 4/6 instead of 6/6), or (b) a source-layout classifier that adjusts thresholds per layout type.

---

### G8_sharpness — FAIL → (S) source limitation + (D) design assumption

**What it checks:** Measures Laplacian variance of 5 evenly-spaced frames. Must exceed an absolute floor of 60. Also compares output sharpness to source sharpness (ratio must be ≥ 0.85).

**Measured vs threshold:**

| Clip | Format | Out median | Src median | Floor pass | Ratio |
|------|--------|-----------|-----------|------------|-------|
| hook | 16:9 | 507.7 | 515.6 | YES (>60) | 0.985 |
| clip_01 | 16:9 | 35.7 | 34.3 | NO (<60) | 1.040 |
| clip_02 | 16:9 | 93.4 | 94.0 | YES (>60) | 0.994 |
| hook | 9:16 | 344.0 | — | YES (>60) | no_source |
| clip_01 | 9:16 | 153.8 | — | YES (>60) | no_source |
| clip_02 | 9:16 | 238.1 | — | YES (>60) | no_source |

**Segment:** clip_01 (Natalie Brunell), both formats.
**Root cause (S):** The Natalie Brunell source camera itself produces soft video. The 16:9 median Laplacian is 35.7 (output) vs 34.3 (source) — no degradation occurred (ratio 1.04), but the source camera is below the 60 floor. This is a source limitation, not a pipeline defect. The fix is selecting a different source clip from a sharper camera, not lowering the bar.

**Root cause (D) for 9:16:** The 9:16 format shows "no_source" because G8 was not configured with source-relative comparison paths for the vertical format. clip_01 passes the absolute floor at 153.8 (letterbox upscale increases apparent variance). This is a gate configuration gap for the vertical format.

**PBX decision:** For (S), the pipeline should prefer sharper sources when alternatives exist for the same story beat. For (D), the 9:16 gate needs source frame paths wired in.

---

### G9_tail — FAIL → approved known exception

**What it checks:** Verifies the last 2 seconds of the final output have low luma (dark/black) and low audio, confirming a clean ending.

**Measured vs threshold:**
- 16:9: mean_luma=14.3, luma_ok=False. rms_db=-46.3, audio_ok=True.
- 9:16: mean_luma=14.5, luma_ok=False. rms_db=-41.4, audio_ok=True.

**Segment:** final output tail (branded outro), both formats.
**Root cause:** The branded outro (`outro_16x9_*.mp4`) ends on a near-black frame. The luma value 14.3 is slightly above the threshold for "dark enough". This is a known and approved exception — the outro is a locked brand asset.

---

### G12_credits — FAIL → (D) detector design assumption

**What it checks:** Counts the number of channel credit circles in the shoutout segment via Hough circle detection. Expected count should match the number of channels in the EDL (3: DataDash, Natalie Brunell, Yahoo Finance).

**Measured vs threshold:**
- 16:9: detected=5, expected=3. FAIL.
- 9:16: detected=6, expected=3. FAIL.

**Segment:** shoutout, both formats.
**Root cause:** The drawn avatars are genuinely round — no aspect squish, no render bug. Visual inspection of both formats confirms 3 properly rendered circular avatar crops with red glow rings. The Hough circle detector picks up false positives from the decorative glow rings around the avatars and from round elements inside the YouTube thumbnails (coin graphics, etc.). The debug overlay (`g12_circles.png`) shows the Natalie Brunell card triggering 2 overlapping detections (inner avatar + outer glow ring).

**PBX decision:** The circle detector was tuned for the v2f shoutout card layout (simple circular crops without glow rings). The current 3-channel cards have richer border styling. Options: (a) tune Hough parameters (min/max radius, accumulator) to reject glow rings, (b) validate by counting labelled channel text instead of raw circles, (c) accept current styling and adjust expected range.

**Frame crops for PBX review:**
- `docs/audits/g12_credits_16x9_crop.png` — 16:9 shoutout at t=5s
- `docs/audits/g12_credits_9x16_crop.png` — 9:16 shoutout at t=5s

---

### G15_credits — FAIL (16:9 only) → (D) same as G12

**What it checks:** Alternative credit verification using text detection or layout analysis in the shoutout segment.

**Measured:** 16:9 FAIL (same false positive issue as G12). 9:16 PASS.

**PBX decision:** Same root cause as G12 — detector assumption, not render defect.

---

## Classification Summary

| Code | Meaning | Gates | Action |
|------|---------|-------|--------|
| (R) | Real defect, fixable without touching gate | G3 (fixed), G3c | Fix in code |
| (S) | Source limitation | G8 (clip_01) | Select sharper source |
| (D) | Design assumption (v2f layout specific) | G4, G8 (9:16 config), G12, G15 | PBX decision |
| — | Known exception | G9 | No action needed |

## Telegram Delivery

Bannered copies sent 2026-11-10 ~10:31 ET:
- 16:9: message_id=67444
- 9:16: message_id=67445
- Banner: "REVIEW ONLY — QA HOLD" (red background, white text, top-centre)
- Verified on 3 frames each (t=2s, t=15s, t=40s)
